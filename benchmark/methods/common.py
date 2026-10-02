import json
import math
from benchmark.schemas import MethodResult


def public_candidates(candidates):
    return [{k: c[k] for k in ("id", "label", "description")} for c in candidates]


def state(payload, candidates):
    return {"record": payload, "candidates": public_candidates(candidates)}


def combine(candidates, wording, position, metadata, diagnostics=None):
    ids = {c["id"] for c in candidates}
    for scores in (wording, position, metadata):
        if set(scores) != ids or any(not math.isfinite(v) or not 0 <= v <= 4 for v in scores.values()):
            raise ValueError("Component scores must cover every candidate on the 0–4 scale")
    scores = {key: (wording[key] + position[key] + metadata[key]) / 12 for key in ids}
    ordered = sorted(candidates, key=lambda c: (-scores[c["id"]], c["template_order"]))
    prediction = ordered[0]["id"]
    top = scores[prediction]
    second = scores[ordered[1]["id"]] if len(ordered) > 1 else 0
    ties = [c["id"] for c in ordered if math.isclose(scores[c["id"]], top, rel_tol=0, abs_tol=1e-12)]
    total = sum(scores.values())
    distribution = {key: value / total if total else 1 / len(ids) for key, value in scores.items()}
    return MethodResult(prediction=prediction, confidence=0 if len(ties) > 1 else top - second,
                        confidence_kind="composite_margin",
                        diagnostics=(diagnostics or {}) | {"wording": wording, "position": position,
                        "metadata": metadata, "scores": scores, "distribution": distribution,
                        "ties": ties if len(ties) > 1 else []})


def validate_probabilities(probabilities, ids):
    if set(probabilities) != set(ids):
        raise ValueError("Probability map must cover exactly the offered options")
    if any(not math.isfinite(v) or not 0 <= v <= 1 for v in probabilities.values()):
        raise ValueError("Invalid probability")
    if not math.isclose(sum(probabilities.values()), 1, abs_tol=1e-3):
        raise ValueError("Probabilities must sum to one")
