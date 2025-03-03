import os

from notion_client import Client

from config import Config
from data import load_buys, load_dividends, load_sells, Buy, Sell, Dividend
from notion_utils import get_number_prop, assert_database_properties, text_property, number_property, \
    query_all_by_database, match_all, match_full_text, build_rich_text, build_number, percent_property, date_property, \
    build_date, formula_property
from stock import ticker


def update_position(notion: Client, config: Config):
    def price_property():
        return number_property(config["currencyFormat"])

    assert_database_properties(notion, config["positionDatabaseID"], {
        "Code": text_property(),
        "BuyId": text_property(),
        "Date": date_property(),
        "Price": price_property(),
        "Quantity": number_property(),
        "Market Value": price_property(),
        ">Avg%": percent_property(),
        "Target%": percent_property(),
        "Sell Price": formula_property('prop("Price") * (1 + prop("Target%"))'),
    })
    folder = config["dataFolder"]
    for code in os.listdir(f"data/{folder}"):
        update_code_position(notion, config, code)


def load_current_position(buy: Buy, sells: list[Sell], dividends: list[Dividend], config: Config):
    new_buy = buy.model_dump()
    for sell in sells:
        if buy.id in sell.quantityOfBuys:
            new_buy["quantity"] -= sell.quantityOfBuys[buy.id]
    for dividend in dividends:
        if buy.id in dividend.quantityOfBuys:
            new_buy["price"] -= dividend.dividend * (1 - config["taxRate"])
    return Buy.model_validate(new_buy)


def update_code_position(notion: Client, config: Config, code: str):
    print("Process position", code)
    buys = load_buys(config, code)
    dividends = load_dividends(config, code, buys=buys)
    sells = load_sells(config, code, buys=buys)
    buys = [load_current_position(buy, sells, dividends, config) for buy in buys]
    buys = [buy for buy in buys if buy.quantity != 0]
    if len(buys) == 0:
        return
    average_price = sum(buy.quantity * buy.price for buy in buys) / sum(buy.quantity for buy in buys)
    for buy in buys:
        pages = query_all_by_database(
            notion, config["positionDatabaseID"],
            match_all(match_full_text("Code", code), match_full_text("BuyId", buy.id)))
        if len(pages) > 1:
            print("Found pages with same code and buy id", pages)
            raise Exception("Too many pages of buy id")
        update_properties = {
            "Date": build_date(buy.date),
            "Price": build_number(buy.price),
            "Quantity": build_number(buy.quantity),
            "Market Value": build_number(buy.quantity * buy.price),
            ">Avg%": build_number(round(buy.price / average_price - 1, 4)),
        }
        if len(pages) == 0:
            page = notion.pages.create(
                parent={"database_id": config["positionDatabaseID"]},
                properties=dict(**{
                    "Code": build_rich_text(code),
                    "BuyId": build_rich_text(buy.id),
                    "Target%": build_number(0.05),
                }, **update_properties))
        else:
            page = pages[0]
            notion.pages.update(page["id"], properties=update_properties)


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
