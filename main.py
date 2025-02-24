import os

from notion_client import Client

from config import get_configs
from divendend import update_stock_database

if __name__ == '__main__':
    notion = Client(auth=os.environ["NOTION_INTERATION_SECRET"])
    for config in get_configs():
        update_stock_database(notion, config)
