from functools import lru_cache
from pathlib import Path
from benchmark.config import read_yaml

ROOT = Path(__file__).parent


@lru_cache
def template():
    data = read_yaml(ROOT / "template.yaml")
    ids, tags = set(), set()
    for line in data["lines"]:
        if line["id"] in ids:
            raise ValueError("Duplicate template id")
        ids.add(line["id"])
        for tag in line["tags"]:
            if tag in tags:
                raise ValueError(f"Tag maps to multiple lines: {tag}")
            tags.add(tag)
    if tags & {r["tag"] for r in data["excluded_tags"]}:
        raise ValueError("Excluded tag appears in template")
    return data


def mapping():
    return {tag: line["id"] for line in template()["lines"] for tag in line["tags"]}


@lru_cache(maxsize=1)
def descriptions():
    return read_yaml(ROOT / "case.yaml")["descriptions"]


def candidates(record, case_config):
    return [
        {"id": line["id"], "label": line["label"], "description": descriptions()[line["id"]],
         "template_order": index}
        for index, line in enumerate(template()["lines"])
        if line["statement"] == record.input["statement"]
    ]
