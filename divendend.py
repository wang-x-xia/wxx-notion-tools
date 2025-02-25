from datetime import date, timedelta

from notion_client import Client
from typing_extensions import Literal, TypedDict

from config import Config
from notion_utils import get_text_prop, get_number_prop, get_date_prop, query_all_by_database, build_rich_text, \
    build_date, build_select, build_number, assert_database_properties, percent_property, date_property, text_property, \
    number_property, select_property
from stock import ticker


def update_stock_database(notion: Client, config: Config):
    def price_property():
        return number_property(config["currencyFormat"])

    assert_database_properties(notion, config["positionDatabaseID"], {
        "Code": text_property(),
        "Price": price_property(),
        "Quantity": number_property(),
        "Dividend/Y": price_property(),
        "Dividend%": percent_property(),
        "Cost": price_property(),
        "Cost Date": date_property(),
        "Cost Dividend%": percent_property(),
        "Low": price_property(),
        "Low Dividend%": percent_property(),
        "High": price_property(),
        "High Dividend%": percent_property(),
    })
    assert_database_properties(notion, config["activityDatabaseID"], {
        "Code": text_property(),
        "Date": date_property(),
        "Price": price_property(),
        "Quantity": number_property(),
        "Action": select_property({
            "name": "Buy",
            "color": "green"
        }, {
            "name": "Sell",
            "color": "red"
        }, {
            "name": "Dividend",
            "color": "blue"
        }),
        "Fee": price_property(),
    })
    pages = query_all_by_database(notion, config["positionDatabaseID"])
    print("Total", len(pages), "Stocks")
    codes = []
    for page in pages:
        code = get_text_prop(page, "Code")
        print("Update stock", code)
        update_stock(notion, page, config, code)
        codes.append(code)


def update_stock(notion: Client, page, config: Config, code: str):
    update_cost(notion, page, config, code)
    update_dividend(notion, page, config, code)


def update_dividend(notion: Client, page, config: Config, code: str):
    data = ticker(config, code)
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
    dividends_tax_rate = config["taxRate"]

    def dividend_percent(cost_):
        return round(dividends / cost_ * (1 - dividends_tax_rate), 4)

    updated_properties["Dividend%"] = {"number": dividend_percent(price)}

    # Dividend % of cost
    cost = get_number_prop(page, "Cost")
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


def load_operations(notion: Client, config: Config, code: str, start: date = None) -> dict[date, list[Operation]]:
    db_filter = {"property": "Code", "rich_text": {"equals": code}}
    if start is not None:
        db_filter = {"and": [db_filter, {"property": "Date", "date": {"after": start.strftime("%Y-%m-%d")}}]}
    pages = query_all_by_database(notion, config["activityDatabaseID"], db_filter=db_filter)
    result: dict[date, list[Operation]] = {}
    for page in pages:
        result.setdefault(get_date_prop(page, "Date"), []).append({
            "action": get_text_prop(page, "Action"),
            "quantity": get_number_prop(page, "Quantity"),
            "price": get_number_prop(page, "Price"),
            "fee": get_number_prop(page, "Fee"),
        })
    return result


def create_operation(notion: Client, config: Config, code: str, op_date: date,
                     action: Literal["Buy", "Sell", "Dividend"],
                     quantity: int | float, price: int | float, fee: int | float):
    notion.pages.create(parent={"database_id": config["activityDatabaseID"]}, properties={
        "Code": build_rich_text(code),
        "Date": build_date(op_date),
        "Action": build_select(action),
        "Quantity": build_number(quantity),
        "Price": build_number(price),
        "Fee": build_number(fee),
    })


def update_cost(notion: Client, page, config: Config, code: str):
    """
    Based on operations to update cost.

    The Cost Date
    """
    start = get_date_prop(page, "Cost Date")
    if start is None:
        print("Code", code, "load all operations to get cost")
        # Try to load all operations
        operations = load_operations(notion, config, code)
        if len(operations) == 0:
            print("Code", code, "has no operation")
            return
        start = min(operations.keys())
        quantity = 0
        cost_total = 0
    elif start == date.today() - timedelta(days=1):
        print("Skip to update yesterday's cost")
        return
    else:
        quantity = get_number_prop(page, "Quantity")
        cost_total = get_number_prop(page, "Cost") * quantity
        operations = load_operations(notion, config, code, start=start)

    print("Start from", start)
    current = start
    while current < date.today() - timedelta(days=1):
        if current in operations:
            for op in operations[current]:
                if op["action"] == "Buy":
                    quantity += op["quantity"]
                    cost_total += op["quantity"] * op["price"] + op["fee"]
                elif op["action"] == "Sell":
                    quantity -= op["quantity"]
                    cost_total += -op["quantity"] * op["price"] + op["fee"]
                else:
                    # Remove Dividend from the cost
                    cost_total += -op["quantity"] * op["price"] + op["fee"]

        current = current + timedelta(days=1)

    print("Update Cost to page")
    notion.pages.update(page["id"], properties={
        "Cost": build_number(cost_total / quantity),
        "Quantity": build_number(quantity),
        "Cost Date": build_date(current),
    })
