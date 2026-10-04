from functools import lru_cache
from pathlib import Path
from benchmark.config import read_yaml

ROOT = Path(__file__).parent
NOT_MAPPED = "not_mapped"  # the answer for totals and subtotals the template does not hold


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
    if set(data["not_mapped_tags"]) & (tags | {r["tag"] for r in data["excluded_tags"]}):
        raise ValueError("A not-mapped tag also maps to a category or is excluded")
    return data


def mapping():
    return {tag: line["id"] for line in template()["lines"] for tag in line["tags"]} | \
        {tag: NOT_MAPPED for tag in template()["not_mapped_tags"]}


@lru_cache(maxsize=1)
def descriptions():
    return read_yaml(ROOT / "case.yaml")["descriptions"]


def candidates(record, case_config):
    return [
        {"id": line["id"], "label": line["label"], "description": descriptions()[line["id"]],
         "template_order": index}
        for index, line in enumerate(template()["lines"])
        if line["statement"] == record.input["statement"]
    ] + [{"id": NOT_MAPPED, "label": "Not mapped", "description": descriptions()[NOT_MAPPED],
          "template_order": len(template()["lines"])}]


def labels():
    return {line["id"]: line["label"] for line in template()["lines"]} | {NOT_MAPPED: "Not mapped"}


def is_correct(prediction, reference, case_config):
    return prediction == reference
