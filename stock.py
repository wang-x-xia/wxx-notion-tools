import os

from yfinance import Ticker


def proxy():
    return os.environ.get("STOCK_PROXY")


def ticker(code: str):
    return Ticker(code, proxy=proxy())


def load_history(t: Ticker, period: str):
    return t.history(period=period, proxy=proxy())
