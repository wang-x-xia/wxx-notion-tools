from typing_extensions import TypedDict


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
        get_cn_hk_config(),
    ]


def get_cn_config() -> Config:
    return {
        "name": "CN",
        "positionDatabaseID": "19a53f8b429a802e82eef937a9ed2350",
        "planDatabaseID": "",
        "currencyFormat": "yuan",
        "taxRate": 0,
        "dataFolder": "cn",
    }


def get_cn_hk_config() -> Config:
    return {
        "name": "HK_CN",
        "positionDatabaseID": "1a553f8b429a8028ab38e528860503d9",
        "planDatabaseID": "",
        "currencyFormat": "hong_kong_dollar",
        "taxRate": 0,
        "dataFolder": "hk_cn",
    }
