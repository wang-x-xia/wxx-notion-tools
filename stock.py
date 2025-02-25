import os
from datetime import date

import requests
from yfinance import Ticker

from config import Config


def proxy():
    return os.environ.get("STOCK_PROXY")


def ticker(config: Config, code: str):
    if config["name"] == "CN":
        code = code + {
            "60": ".SS",
            "50": ".SS",
            "18": ".SZ",
        }[code[0:2]]
    elif config["name"] == "CN_HK":
        code = f"{code}.HK"
    session = requests.Session()
    if proxy() is not None:
        session.proxies = {"https": proxy()}
    return Ticker(code, session=session)


def load_dividends(config: Config, code: str, start: date) -> dict[date, float | int]:
    token = start
    result = {}
    while token <= date.today():
        t = ticker(config, code)
        t.history(period="1y", start=token.strftime("%Y-%m-%d"))
        for time, value in t.dividends.to_dict().items():
            result[time.date()] = value
        token = token.replace(year=token.year + 1)
    return result


def load_dividends_tax_rate():
    # TODO Remove after all separation
    return {
        "CNY": 0,
        "HKD": 0.2,
        "USD": 0.1,
    }
