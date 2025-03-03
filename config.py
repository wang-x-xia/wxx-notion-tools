from typing_extensions import TypedDict

from notion_utils import number_property


class Config(TypedDict):
    name: str
    positionDatabaseID: str
    planDatabaseID: str
    # The type of https://developers.notion.com/reference/property-object#number
    currencyFormat: str
    taxRate: float
    dataFolder: str


def get_configs() -> list[Config]:
    return [
        get_cn_config(),
        get_cn_hk_config(),
    ]


def get_cn_config() -> Config:
    return {
        "name": "CN",
        "positionDatabaseID": "19a53f8b429a802e82eef937a9ed2350",
        "planDatabaseID": "1ab53f8b429a80d69e02e65c68dbc280",
        "currencyFormat": "yuan",
        "taxRate": 0,
        "dataFolder": "cn",
    }


def get_cn_hk_config() -> Config:
    return {
        "name": "HK_CN",
        "positionDatabaseID": "1a553f8b429a8028ab38e528860503d9",
        "planDatabaseID": "1a553f8b429a80d1ac88fa4efba68d6a",
        "currencyFormat": "hong_kong_dollar",
        "taxRate": 0.2,
        "dataFolder": "hk_cn",
    }


def price_property(config: Config):
    return number_property(config["currencyFormat"])
