from notion_client import Client

from config import Config, price_property
from notion_utils import number_property, text_property, assert_database_properties


def update_plan(notion: Client, config: Config):
    assert_database_properties(notion, config["planDatabaseID"], {
        "Code": text_property(),
        "Base Price": price_property(config),
        "Quantity": number_property(),
    })
