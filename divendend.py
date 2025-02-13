from datetime import date, timedelta

from notion_client import Client
from typing_extensions import Literal, TypedDict

from notion_utils import get_text_prop, get_number_prop, get_date_prop, query_all_by_database, build_rich_text, \
    build_date, build_select, build_number
from stock import ticker, load_dividends, load_dividends_tax_rate

POSITION_DB_ID = "19153f8b429a80978f64c832aacaa56f"
OPERATION_DB_ID = "19453f8b429a80c1a3cce3ebd8a79831"


def update_stock_database(notion: Client):
    pages = query_all_by_database(notion, POSITION_DB_ID)
    print("Total", len(pages), "Stocks")
    for page in pages:
        update_stock(notion, page)


def update_stock(notion: Client, page):
    code = get_text_prop(page, "Code")
    print("Update stock", code)
    data = ticker(code)
    # load data
    data.history(period="1y")
    his_meta = data.get_history_metadata()
    updated_properties = {}

    # price
    price = his_meta["regularMarketPrice"]
    updated_properties["Price"] = {"number": price}

    # dividends
    dividends = data.dividends.sum()
    # Dividend of year
    updated_properties["Dividend/Y"] = {"number": dividends}
    # Dividend %
    dividends_tax_rate = load_dividends_tax_rate(code)

    def dividend_percent(cost_):
        return round(dividends / cost_ * (1 - dividends_tax_rate), 4)

    updated_properties["Dividend%"] = {"number": dividend_percent(price)}

    # Dividend % of cost
    cost = update_and_cost(notion, page, code)
    if cost is not None:
        updated_properties["Cost Dividend%"] = {"number": dividend_percent(cost)}

    # T value
    low = his_meta["fiftyTwoWeekLow"]
    high = his_meta["fiftyTwoWeekHigh"]
    updated_properties["Low"] = {"number": low}
    updated_properties["High"] = {"number": high}
    updated_properties["Low Dividend%"] = {"number": dividend_percent(low)}
    updated_properties["High Dividend%"] = {"number": dividend_percent(high)}

    notion.pages.update(page["id"], properties=updated_properties)


class Operation(TypedDict):
    action: Literal["Buy", "Sell", "Dividend"]
    quantity: int | float
    price: int | float
    fee: int | float


def load_operations(notion: Client, code: str, start: date = None) -> dict[date, list[Operation]]:
    db_filter = {"property": "Code", "rich_text": {"equals": code}}
    if start is not None:
        db_filter = {"and": [db_filter, {"property": "Date", "date": {"after": start.strftime("%Y-%m-%d")}}]}
    pages = query_all_by_database(notion, OPERATION_DB_ID, db_filter=db_filter)
    result: dict[date, list[Operation]] = {}
    for page in pages:
        result.setdefault(get_date_prop(page, "Date"), []).append({
            "action": get_text_prop(page, "Action"),
            "quantity": get_number_prop(page, "Quantity"),
            "price": get_number_prop(page, "Price"),
            "fee": get_number_prop(page, "Fee"),
        })
    return result


def create_operation(notion: Client, code: str, op_date: date,
                     action: Literal["Buy", "Sell", "Dividend"],
                     quantity: int | float, price: int | float, fee: int | float):
    notion.pages.create(parent={"database_id": OPERATION_DB_ID}, properties={
        "Code": build_rich_text(code),
        "Date": build_date(op_date),
        "Action": build_select(action),
        "Quantity": build_number(quantity),
        "Price": build_number(price),
        "Fee": build_number(fee),
    })


def update_and_cost(notion: Client, page, code):
    start = get_date_prop(page, "Cost Date")
    if start is None:
        print("Code", code, "load all operations to get cost")
        # Try to load all operations
        operations = load_operations(notion, code)
        if len(operations) == 0:
            print("Code", code, "has no operation")
            return None
        start = min(operations.keys())
        quantity = 0
        cost_total = 0
    elif start == date.today() - timedelta(days=1):
        print("Skip to update yesterday's cost")
        return get_number_prop(page, "Cost")
    else:
        quantity = get_number_prop(page, "Quantity")
        cost_total = get_number_prop(page, "Cost") * quantity
        operations = load_operations(notion, code, start=start)

    print("Start from", start)
    # Load Dividends
    dividends = load_dividends(code, start=start)
    print("Found dividends", len(dividends))
    tax_rate = 1
    if len(dividends) > 0:
        # lazy load
        tax_rate = load_dividends_tax_rate(code)

    current = start
    while current < date.today() - timedelta(days=1):
        found_dividend = False

        if current in operations:
            for op in operations[current]:
                if op["action"] in ["Buy", "Sell"]:
                    quantity += op["quantity"]
                    cost_total += op["quantity"] * op["price"] - op["fee"]
                else:
                    found_dividend = True
                    # Remove Dividend from the cost
                    cost_total += -op["quantity"] * op["price"] - op["fee"]

        if not found_dividend and current in dividends:
            dividend = dividends[current]
            # Use 20% as default tax
            print("Update dividend to db", current, quantity, dividend)
            create_operation(notion, code, current, "Dividend", quantity, dividend, quantity * dividend * tax_rate)
            cost_total -= quantity * dividend * 0.8

        current = current + timedelta(days=1)

    print("Update Cost to page")
    notion.pages.update(page["id"], properties={
        "Cost": build_number(cost_total / quantity),
        "Quantity": build_number(quantity),
        "Cost Date": build_date(current),
    })
    return cost_total / quantity
