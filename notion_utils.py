from datetime import datetime, date

from notion_client import Client


def get_text_prop(page, key, default_value=None):
    if key not in page["properties"]:
        return default_value
    prop = page["properties"][key]
    if prop["type"] == "rich_text":
        return merge_rich_text(prop["rich_text"])
    elif prop["type"] == "select":
        return prop["select"]["name"]
    else:
        print(prop)
        raise RuntimeError("Invalid text type in property")


def merge_rich_text(rich_text) -> str:
    result = ""
    for item in rich_text:
        if item["type"] == "text":
            result += item["text"]["content"]
        else:
            print(item)
            raise RuntimeError("Invalid Type in rich text")
    return result


def get_number_prop(page, key, default_value=None) -> int | float | None:
    if key not in page["properties"]:
        return default_value
    prop = page["properties"][key]
    if prop["type"] == "number":
        return prop["number"]
    else:
        print(prop)
        raise RuntimeError("Invalid number type in property")


def get_date_prop(page, key, default_value=None) -> date | None:
    if key not in page["properties"]:
        return default_value
    prop = page["properties"][key]
    if prop["type"] == "date":
        if prop["date"] is None:
            return default_value
        return datetime.fromisoformat(prop["date"]["start"]).date()
    else:
        print(prop)
        raise RuntimeError("Invalid number type in property")


def query_all_by_database(notion: Client, db_id: str, db_filter=None):
    args = {}
    if db_filter is not None:
        args["filter"] = db_filter
    cursor = None
    pages = []
    while True:
        result = notion.databases.query(db_id, start_cursor=cursor, **args)
        pages += result["results"]
        if result["has_more"]:
            cursor = result["next_cursor"]
            continue
        return pages


def build_date(input_date: date):
    return {"date": {"start": input_date.strftime("%Y-%m-%d"), }}


def build_number(number: float | int):
    return {"number": number}


def build_rich_text(value: str):
    return {"rich_text": [{
        "type": "text",
        "text": {"content": value}
    }]}


def build_select(option: str):
    return {"select": {"name": option, }}
