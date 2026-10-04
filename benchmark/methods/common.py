import math


def public_candidates(candidates):
    return [{k: c[k] for k in ("id", "label", "description")} for c in candidates]


def state(payload, candidates):
    return {"record": payload, "candidates": public_candidates(candidates)}


def validate_probabilities(probabilities, ids):
    if set(probabilities) != set(ids):
        raise ValueError("Probability map must cover exactly the offered options")
    if any(not math.isfinite(v) or not 0 <= v <= 1 for v in probabilities.values()):
        raise ValueError("Invalid probability")
    # Jev's live API rounds some vectors to hundredths. For k rounded
    # entries the total can differ from one by up to k * 0.005.
    rounded_hundredths = all(math.isclose(v * 100, round(v * 100), rel_tol=0, abs_tol=1e-8)
                            for v in probabilities.values())
    tolerance = len(probabilities) * .005 + 1e-9 if rounded_hundredths else 1e-3
    if not math.isclose(sum(probabilities.values()), 1, rel_tol=0, abs_tol=tolerance):
        raise ValueError("Probabilities must sum to one")
