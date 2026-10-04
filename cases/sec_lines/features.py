import re
from functools import lru_cache
from benchmark.schemas import MethodResult
from benchmark.config import read_yaml
from .template import ROOT

ALLOWLIST = {"label", "statement", "lines_above", "lines_below", "sign", "scale_ratio", "sic_description"}


@lru_cache(maxsize=1)
def rules_config():
    return read_yaml(ROOT / "rules.yaml")


def normalize(text):
    return " ".join(re.sub(r"[^\w\s]", " ", str(text).lower()).split())


def build_payload(record, context_regime, case_config):
    if context_regime not in ("label_only", "with_context"):
        raise ValueError(f"Unknown context regime: {context_regime}")
    keys = {"label", "statement"} if context_regime == "label_only" else ALLOWLIST
    return {key: record.input[key] for key in sorted(keys) if key in record.input}


def rules(payload, candidates, case_config):
    config = rules_config()
    label = normalize(payload["label"])
    available = {c["id"] for c in candidates}
    above = [normalize(x) for x in payload.get("lines_above", [])]
    below = [normalize(x) for x in payload.get("lines_below", [])]
    hit = None
    if config["position"]["enabled"] and "other income" in label:
        if above and re.search("operating (income|loss)|from operations", above[-1]) and below and re.search("before.*tax", below[0]):
            hit = "total_nonoperating"
        elif above and re.search("^revenues?( from operations)?$", above[-1]):
            hit = "revenue"
    hits = [key for key, patterns in config["keywords"].items()
            if key in available and any(re.search(pattern, label) for pattern in patterns)]
    prediction = hit if hit in available else hits[0] if len(hits) == 1 else "ABSTAIN"
    return MethodResult(prediction=prediction, confidence=1.0 if prediction != "ABSTAIN" else 0,
                        confidence_kind="rule_fired", diagnostics={"rule_hits": hits, "position_rule": hit})
