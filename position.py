import os

from notion_client import Client
from pydantic import BaseModel

from config import Config
from data import load_stock, Buy
from notion_utils import get_number_prop, assert_database_properties, text_property, number_property, \
    match_all, match_full_text, build_rich_text, build_number, percent_property, date_property, \
    build_date, formula_property, update_or_create_in_database
from stock import ticker


class Position(BaseModel):
    quantity: float
    avgPrice: float
    items: list["PositionItem"]


class PositionItem(BaseModel):
    buy: Buy
    sellPrice: float


def update_position(notion: Client, config: Config) -> dict[str, Position]:
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

    positions: dict[str, Position] = {}
    for code in os.listdir(f"data/{folder}"):
        positions[code] = update_and_get_code_position(notion, config, code)
    return positions


def update_and_get_code_position(notion: Client, config: Config, code: str) -> Position:
    print("Process position", code)
    stock = load_stock(config, code)
    total_quantity = sum(buy.quantity for buy in stock.positions)
    average_price = (sum(buy.quantity * buy.price for buy in stock.positions) / total_quantity) \
        if total_quantity != 0 else 0

    positions: list[PositionItem] = []
    for position in stock.positions:
        page = update_or_create_in_database(
            notion, config["positionDatabaseID"],
            db_filter=match_all(match_full_text("Code", code), match_full_text("BuyId", position.id)),
            creates={
                "Code": build_rich_text(code),
                "BuyId": build_rich_text(position.id),
                "Target%": build_number(0.05),
            },
            updates={
                "Date": build_date(position.date),
                "Price": build_number(position.price),
                "Quantity": build_number(position.quantity),
                "Market Value": build_number(position.quantity * position.price),
                ">Avg%": build_number(round(position.price / average_price - 1, 4) if average_price != 0 else 0),
            })
        # Only return valid position
        if position.quantity != 0:
            positions.append(PositionItem(buy=position, sellPrice=get_number_prop(page, "Sell Price", 0)))

    return Position(quantity=total_quantity, avgPrice=average_price, items=positions)


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
