import json
from datetime import date

from pydantic import BaseModel, TypeAdapter

from config import Config


class Buy(BaseModel):
    """
    Buy operation
    """
    id: str
    date: date
    quantity: float
    price: float
    fee: float


class Sell(BaseModel):
    """
    Sell operation
    """
    date: date
    quantity: float
    price: float
    fee: float
    # Key is the buy id
    quantityOfBuys: dict[str, float]


class Dividend(BaseModel):
    """
    Dividend operation
    """
    date: date
    quantity: float
    dividend: float
    fee: float
    # Key is the buy id
    quantityOfBuys: dict[str, float]


def load_buys(config: Config, code: str) -> list[Buy]:
    with open(f"data/{config['dataFolder']}/{code}/buy.json", "r") as f:
        return TypeAdapter(list[Buy]).validate_python(json.load(f))


def load_sells(config: Config, code: str) -> list[Sell]:
    with open(f"data/{config['dataFolder']}/{code}/sell.json", "r") as f:
        return TypeAdapter(list[Sell]).validate_python(json.load(f))


def load_dividends(config: Config, code: str) -> list[Dividend]:
    with open(f"data/{config['dataFolder']}/{code}/dividend.json", "r") as f:
        return TypeAdapter(list[Dividend]).validate_python(json.load(f))
