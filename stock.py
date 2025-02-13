import os
from datetime import date

import requests
from yfinance import Ticker


def proxy():
    return os.environ.get("STOCK_PROXY")


def ticker(code: str):
    session = requests.Session()
    if proxy() is not None:
        session.proxies = {"https": proxy()}
    return Ticker(code, session=session)


def load_dividends(code: str, start: date) -> dict[date, float | int]:
    token = start
    result = {}
    while token <= date.today():
        t = ticker(code)
        t.history(period="1y", start=token.strftime("%Y-%m-%d"))
        for time, value in t.dividends.to_dict().items():
            result[time.date()] = value
        token = token.replace(year=token.year + 1)
    return result


def load_dividends_tax_rate(code: str) -> float:
    t = ticker(code)
    t.history(period="1d")
    return {
        "HKD": 0.2,
        "USD": 0.1,
    }.get(t.get_history_metadata()["currency"], 0.2)
