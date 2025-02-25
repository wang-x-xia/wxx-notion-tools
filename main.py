import os

from notion_client import Client

from config import get_configs
from position import update_position

if __name__ == '__main__':
    notion = Client(auth=os.environ["NOTION_INTERATION_SECRET"])
    for config in get_configs():
        update_position(notion, config)
