from notion_client import Client

from notion_utils import get_text_prop
from stock import ticker, load_history

DB_ID = "19153f8b429a80978f64c832aacaa56f"


def update_stock_database(notion: Client):
    result = notion.databases.query(DB_ID)
    pages = []
    while True:
        pages += result["results"]
        if result["has_more"]:
            result = notion.databases.query(DB_ID, start_cursor=result["next_cursor"])
            continue
        break
    print("Total", len(pages), "Stocks")
    for page in pages:
        update_stock(notion, page)


def update_stock(notion: Client, page):
    code = get_text_prop(page, "Code")
    print("Update stock", code)
    data = ticker(code)
    # load data
    load_history(data, "1y")
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
    dividends_tax_rate = {
        "HKG": 0.2
    }[his_meta["exchangeName"]]

    def dividend_percent(cost_):
        return round(dividends / cost_ * (1 - dividends_tax_rate), 4)

    updated_properties["Dividend%"] = {"number": dividend_percent(price)}

    # Dividend % of cost
    cost = page["properties"]["Cost"]["number"]
    if isinstance(cost, (int, float)):
        updated_properties["Cost Dividend%"] = {"number": dividend_percent(cost)}

    # T value
    low = his_meta["fiftyTwoWeekLow"]
    high = his_meta["fiftyTwoWeekHigh"]
    updated_properties["Low"] = {"number": low}
    updated_properties["High"] = {"number": high}
    updated_properties["Low Dividend%"] = {"number": dividend_percent(low)}
    updated_properties["High Dividend%"] = {"number": dividend_percent(high)}

    notion.pages.update(page["id"], properties=updated_properties)
