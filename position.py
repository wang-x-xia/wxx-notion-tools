import json
import os

from notion_client import Client

from config import Config
from data import Buy
from notion_utils import get_number_prop, assert_database_properties, \
    percent_property, text_property, \
    number_property, query_all_by_database, match_all, match_full_text, build_rich_text, build_number
from stock import ticker


def update_position(notion: Client, config: Config):
    def price_property():
        return number_property(config["currencyFormat"])

    assert_database_properties(notion, config["positionDatabaseID"], {
        "Code": text_property(),
        "BuyId": text_property(),
        "Price": price_property(),
        "Quantity": number_property(),
        "Dividend/Y": price_property(),
        "Dividend%": percent_property(),
        "Cost": price_property(),
        "Cost Dividend%": percent_property(),
        "Low": price_property(),
        "Low Dividend%": percent_property(),
        "High": price_property(),
        "High Dividend%": percent_property(),
    })
    folder = config["dataFolder"]
    for code in os.listdir(f"data/{folder}"):
        update_code_position(notion, config, code)


def update_code_position(notion: Client, config: Config, code: str):
    with open(f"data/{config['dataFolder']}/{code}/buy.json", "r") as f:
        for buy in json.load(f):
            buy = Buy.model_validate_json(json.dumps(buy))
            pages = query_all_by_database(
                notion, config["positionDatabaseID"],
                match_all(match_full_text("Code", code), match_full_text("BuyId", buy.id)))
            if len(pages) > 1:
                print("Found pages with same code and buy id", pages)
                raise Exception("Too many pages of buy id")
            if len(pages) == 0:
                page = notion.pages.create(
                    parent={"database_id": config["positionDatabaseID"]},
                    properties={
                        "Code": build_rich_text(code),
                        "BuyId": build_rich_text(buy.id),
                        "Cost": build_number(buy.price),
                        "Quantity": build_number(buy.quantity),
                    })
            else:
                page = pages[0]
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
