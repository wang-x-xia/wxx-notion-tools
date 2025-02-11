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
        raise RuntimeError("Invalid Type in property")


def merge_rich_text(rich_text) -> str:
    result = ""
    for item in rich_text:
        if item["type"] == "text":
            result += item["text"]["content"]
        else:
            print(item)
            raise RuntimeError("Invalid Type in rich text")
    return result
