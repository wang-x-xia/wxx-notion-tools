from typing_extensions import TypedDict


class Config(TypedDict):
    name: str
    positionDatabaseID: str
    activityDatabaseID: str
    guideDatabaseID: str
    # The type of https://developers.notion.com/reference/property-object#number
    currencyFormat: str
    taxRate: float


def get_configs() -> list[Config]:
    return [{
        "name": "CN",
        "positionDatabaseID": "19a53f8b429a802e82eef937a9ed2350",
        "activityDatabaseID": "1a453f8b429a8042b0edd4c0b832ea21",
        "guideDatabaseID": "",
        "currencyFormat": "yuan",
        "taxRate": 0,
    }]
