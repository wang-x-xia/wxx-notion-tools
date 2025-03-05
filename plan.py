from notion_client import Client

from config import Config, price_property
from notion_utils import number_property, text_property, assert_database_properties, formula_property, \
    match_full_text, build_number, build_rich_text, update_or_create_in_database, percent_property, build_title
from position import Position


def update_plan(notion: Client, config: Config, positions: dict[str, Position]):
    assert_database_properties(notion, config["planDatabaseID"], {
        "Code": text_property(),
        "Base Price": price_property(config),
        "Quantity": number_property(),
        "Lowest Buy Price": price_property(config),
        "Lowest Buy Id": text_property(),
        "-Buy%": percent_property(),
        "Next Buy Price": formula_property('prop("Lowest Buy Price") * (1 - prop("-Buy%"))'),
        "Next Sell Price": price_property(config),
        "Next Sell Id": text_property(),
    })

    for code in positions:
        position = positions[code]
        if len(position.items) == 0:
            print("Skip to update plan", code)
            continue
        lowest_buy = min(position.items, key=lambda i: i.buy.price)
        next_sell = min(position.items, key=lambda i: i.sellPrice)
        update_or_create_in_database(
            notion, config["planDatabaseID"],
            db_filter=match_full_text("Code", code),
            creates={
                "Name": build_title(position.name),
                "Code": build_rich_text(code),
                "-Buy%": build_number(0.03),
            },
            updates={
                "Base Price": build_number(position.avgPrice),
                "Quantity": build_number(position.quantity),
                "Lowest Buy Price": build_number(lowest_buy.buy.price),
                "Lowest Buy Id": build_rich_text(lowest_buy.buy.id),
                "Next Sell Price": build_number(next_sell.sellPrice),
                "Next Sell Id": build_rich_text(next_sell.buy.id),
            })
