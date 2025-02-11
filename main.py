import os

from notion_client import Client

from divendend import update_stock_database

if __name__ == '__main__':
    notion = Client(auth=os.environ["NOTION_INTERATION_SECRET"])
    update_stock_database(notion)
