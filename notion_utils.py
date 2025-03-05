from datetime import datetime, date
from typing import TypedDict, Literal, NotRequired

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
    elif prop["type"] == "formula":
        if prop["formula"]["type"] == "number":
            return prop["formula"]["number"]
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


def update_or_create_in_database(notion: Client, db_id: str, *, db_filter, creates, updates):
    pages = query_all_by_database(notion, db_id, db_filter=db_filter)
    if len(pages) > 1:
        print("Found pages with filter", db_id)
        raise Exception("Too many pages")
    if len(pages) == 0:
        return notion.pages.create(parent={"database_id": db_id}, properties=dict(**creates, **updates))
    else:
        page = pages[0]
        return notion.pages.update(page["id"], properties=updates)


def match_all(*args):
    return {"and": args}


def match_full_text(key, text):
    return {"property": key, "rich_text": {"equals": text}}


class InputPropertyObject(TypedDict):
    type: Literal["rich_text", "number", "date", "select", "formula"]
    number: NotRequired[dict]
    options: NotRequired[list]
    date: NotRequired[dict]
    rich_text: NotRequired[dict]
    select: NotRequired[dict]
    formula: NotRequired[dict]


def text_property() -> InputPropertyObject:
    return {"type": "rich_text", "rich_text": {}}


def percent_property() -> InputPropertyObject:
    return number_property("percent")


def number_property(number_format: str = "number") -> InputPropertyObject:
    return {"type": "number", "number": {"format": number_format}}


def date_property() -> InputPropertyObject:
    return {"type": "date", "date": {}}


def select_property(*options: dict) -> InputPropertyObject:
    return {"type": "select", "select": {"options": options}}


def formula_property(expression: str) -> InputPropertyObject:
    return {"type": "formula", "formula": {"expression": expression}}


def assert_database_properties(notion: Client, db_id: str, inputs: dict[str, InputPropertyObject]):
    db_def = notion.databases.retrieve(db_id)
    title = merge_rich_text(db_def["title"])
    properties = db_def["properties"]

    updates = {}
    for key in inputs:
        required = inputs[key]
        if key not in properties:
            updates[key] = required
            continue
        existed = properties[key]
        if existed["type"] != required["type"]:
            print("Found unmatched type", title, key, existed, required)
            raise RuntimeError("Invalid type")
        if required["type"] == "number":
            if "number" in required and required["number"] != existed["number"]:
                updates[key] = required
        if required["type"] == "formula":
            if required["formula"]["expression"] != required["formula"]["expression"]:
                updates[key] = required

    if len(updates):
        print("Modify properties", title, updates)
        notion.databases.update(db_id, properties=updates)


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
