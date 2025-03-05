import json
from datetime import date

from pydantic import BaseModel, TypeAdapter

from config import Config


class Buy(BaseModel):
    """
    Buy operation
    """
    id: str = ""
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
    # Key is the buy id
    quantityOfBuys: dict[str, float]


def load_buys(config: Config, code: str) -> list[Buy]:
    with open(f"data/{config['dataFolder']}/{code}/buy.json", "r") as f:
        buys = TypeAdapter(list[Buy]).validate_python(json.load(f))
    for buy in buys:
        if buy.id == "":
            buy.id = buy.date.strftime("%Y-%m-%d")
    return buys


def load_sells(config: Config, code: str, buys: list[Buy] = None) -> list[Sell]:
    if buys is None:
        buys = load_buys(config, code)
    by_id_buys = {buy.id: buy.quantity for buy in buys}
    with open(f"data/{config['dataFolder']}/{code}/sell.json", "r") as f:
        sells = TypeAdapter(list[Sell]).validate_python(json.load(f))
    for sell in sells:
        if sell.quantity != sum(sell.quantityOfBuys.values()):
            print("Sell quantity is not matched", sell)
            raise RuntimeError("Invalid Sell")
        for buyId in sell.quantityOfBuys:
            if buyId not in by_id_buys:
                print("Invalid buy id in sell", sell, buyId)
                raise RuntimeError("Invalid BuyId in Sell")
            by_id_buys[buyId] -= sell.quantityOfBuys[buyId]
            if by_id_buys[buyId] < 0:
                print("Got negative position", sell, buyId)
                raise RuntimeError("Invalid BuyId in Sell")
    return sells


def load_dividends(config: Config, code: str, buys: list[Buy] = None) -> list[Dividend]:
    if buys is None:
        buys = load_buys(config, code)
    by_id_buys = {buy.id: buy for buy in buys}
    with open(f"data/{config['dataFolder']}/{code}/dividend.json", "r") as f:
        dividends = TypeAdapter(list[Dividend]).validate_python(json.load(f))
    for dividend in dividends:
        if dividend.quantity != sum(dividend.quantityOfBuys.values()):
            print("Dividend quantity is not matched", dividend)
            raise RuntimeError("Invalid Dividend")
        for buyId in dividend.quantityOfBuys:
            if buyId not in by_id_buys:
                print("Invalid buy id in dividend", dividend, buyId)
                raise RuntimeError("Invalid BuyId in Dividend")
    return dividends


class Stock(BaseModel):
    positions: list[Buy]
    buys: list[Buy]
    sells: list[Sell]
    dividends: list[Dividend]


def load_stock(config: Config, code: str) -> Stock:
    buys = load_buys(config, code)
    sells = load_sells(config, code, buys)
    dividends = load_dividends(config, code, buys)
    positions = [load_current_position(buy, sells, dividends, config) for buy in buys]
    return Stock(positions=positions, buys=buys, sells=sells, dividends=dividends)


def load_current_position(buy: Buy, sells: list[Sell], dividends: list[Dividend], config: Config):
    new_buy = buy.model_dump()
    for sell in sells:
        if buy.id in sell.quantityOfBuys:
            new_buy["quantity"] -= sell.quantityOfBuys[buy.id]
    for d in dividends:
        if buy.id in d.quantityOfBuys:
            new_buy["price"] -= d.dividend * (1 - config["taxRate"])
    return Buy.model_validate(new_buy)
