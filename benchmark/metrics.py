"""Metrics consume stored predictions; no provider calls or case imports."""
import json
import math
from collections import defaultdict

import numpy as np
import pandas as pd


def fraction(values):
    return float(np.mean(values)) if len(values) else None


def coverage(rows, levels=(1, .9, .8, .7, .5)):
    ordered = rows.sort_values(["confidence", "record_id"], ascending=[False, True], kind="stable")
    output = []
    for level in levels:
        count = max(1, math.ceil(len(rows) * level)) if len(rows) else 0
        retained = ordered.head(count)
        output.append({"target_coverage": level, "coverage": count / len(rows) if len(rows) else 0,
                       "accuracy": fraction(retained.correct), "records": count})
    return output


def calibration(rows, bins=10):
    eligible = rows[rows.probability_of_prediction.notna() & ~rows.failed]
    if eligible.empty:
        return {"available": False, "records": 0}
    p = eligible.probability_of_prediction.to_numpy(dtype=float)
    y = eligible.correct.to_numpy(dtype=float)
    assigned = np.minimum((p * bins).astype(int), bins - 1)
    ece, bucket_rows = 0., []
    for bucket in range(bins):
        mask = assigned == bucket
        if not mask.any():
            continue
        confidence, accuracy = float(p[mask].mean()), float(y[mask].mean())
        ece += float(mask.mean()) * abs(confidence - accuracy)
        bucket_rows.append({"lower": bucket / bins, "upper": (bucket + 1) / bins,
                            "records": int(mask.sum()), "mean_probability": confidence, "accuracy": accuracy})
    return {"available": True, "records": len(eligible), "excluded_records": len(rows) - len(eligible),
            "selected_answer_brier": float(np.mean((p-y)**2)), "expected_calibration_error": ece,
            "bins": bucket_rows}


def pairwise(left, right, seed=20261001, draws=2000):
    joined = left.merge(right, on="record_id", suffixes=("_left", "_right"), validate="one_to_one")
    if joined.empty:
        return {"records": 0, "available": False}
    delta = joined.correct_left.to_numpy(dtype=float) - joined.correct_right.to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    # Bounded batches avoid an O(draws * corpus size) allocation.
    row_samples = [float(delta[rng.integers(0, len(delta), len(delta))].mean()) for _ in range(draws)]
    clusters = defaultdict(list)
    for i, source in enumerate(joined.source_json_left):
        clusters[str(json.loads(source).get("cik", joined.iloc[i].record_id))].append(delta[i])
    totals = np.array([sum(v) for v in clusters.values()])
    counts = np.array([len(v) for v in clusters.values()])
    cluster_samples = []
    for _ in range(draws):
        indices = rng.integers(0, len(totals), len(totals))
        cluster_samples.append(float(totals[indices].sum() / counts[indices].sum()))
    a, b = int(np.sum(delta == 1)), int(np.sum(delta == -1))
    discordant = a+b
    if discordant:
        k = min(a, b)
        logs = [math.lgamma(discordant+1) - math.lgamma(i+1) - math.lgamma(discordant-i+1)
                - discordant * math.log(2) for i in range(k+1)]
        maximum = max(logs)
        p_value = min(1., 2 * math.exp(maximum) * sum(math.exp(x-maximum) for x in logs))
    else:
        p_value = 1.
    return {"available": True, "records": len(delta), "filers": len(clusters),
            "accuracy_difference": float(delta.mean()),
            "paired_bootstrap_95": [float(x) for x in np.quantile(row_samples, [.025, .975])],
            "filer_cluster_bootstrap_95": [float(x) for x in np.quantile(cluster_samples, [.025, .975])],
            "mcnemar_exact_p": p_value, "left_only_correct": a, "right_only_correct": b}


def distribution_agreement(rows, splits):
    if splits is None or splits.empty:
        return {"available": False, "reason": "No label-distribution artifact", "records": 0}
    targets = {}
    for (statement, label), group in splits.groupby(["statement", "normalized_label"]):
        targets[(statement, label)] = dict(zip(group.reference, group.share))
    differences = []
    for row in rows.itertuples():
        groups = json.loads(row.groups_json)
        if groups.get("filer_split") != "true" or row.failed:
            continue
        observed = targets.get((groups.get("statement"), groups.get("normalized_label")))
        predicted = json.loads(row.diagnostics_json).get("distribution")
        if observed is None or predicted is None:
            continue
        ids = set(observed) | set(predicted)
        differences.append(sum(abs(observed.get(k, 0) - predicted.get(k, 0)) for k in ids) / len(ids))
    return {"available": bool(differences), "records": len(differences),
            "mean_absolute_difference": fraction(differences),
            "interpretation": "Descriptive agreement with population label shares, not individual probability calibration"}


def metric_group(all_rows, splits, expected_repeats):
    rows = all_rows[(all_rows.repeat_index == 0) & ~all_rows.shuffled]
    groups = defaultdict(list)
    for row in rows.itertuples():
        for dimension, value in json.loads(row.groups_json).items():
            if dimension != "normalized_label":
                groups[(dimension, value)].append(bool(row.correct))
    confusion = rows.groupby(["reference", "prediction"]).size().reset_index(name="records").to_dict("records")
    repeated = all_rows[~all_rows.shuffled].groupby("record_id")
    changes, ranges, incomplete = [], [], 0
    for _, group in repeated:
        if len(group) < 2:
            continue
        if len(group) != expected_repeats or group.failed.any():
            incomplete += 1
            continue
        changes.append(group.prediction.nunique() > 1)
        ranges.append(float(group.confidence.max() - group.confidence.min()))
    shuffled = all_rows[all_rows.shuffled].merge(rows, on="record_id", suffixes=("_shuffle", "_original"), validate="one_to_one")
    valid_shuffles = shuffled[~shuffled.failed_shuffle & ~shuffled.failed_original] if len(shuffled) else shuffled
    diagnostics = [json.loads(s) for s in rows.diagnostics_json]
    known_cost = bool(all_rows.usage_complete.all()) and bool(all_rows.cost_usd.notna().all())
    base_cost_known = bool(rows.usage_complete.all()) and bool(rows.cost_usd.notna().all())
    expected = [d["expected_variant"] for d in diagnostics if "expected_variant" in d]
    expected_correct = [d["expected_variant"]["prediction"] == row.reference
                        for d, row in zip(diagnostics, rows.itertuples()) if "expected_variant" in d]
    return {
        "records": len(rows), "accuracy": fraction(rows.correct), "failure_rate": fraction(rows.failed),
        "baseline_coverage": fraction(rows.prediction != "ABSTAIN"),
        "tie_rate": fraction([bool(d.get("ties")) for d in diagnostics]),
        "by_group": [{"dimension": key[0], "value": key[1], "records": len(values), "accuracy": fraction(values)}
                     for key, values in sorted(groups.items())],
        "confusion_matrix": confusion, "confidence_coverage": coverage(rows),
        "calibration": calibration(rows), "distribution_agreement": distribution_agreement(rows, splits),
        "repeatability": {"records": len(changes), "incomplete_or_failed": incomplete,
                          "all_predictions_same": 1 - fraction(changes) if changes else None,
                          "at_least_one_change": fraction(changes), "mean_confidence_range": fraction(ranges)},
        "option_order": {"records": len(valid_shuffles), "attempted_records": len(shuffled),
                         "failed_pairs": len(shuffled) - len(valid_shuffles),
                         "prediction_change_rate": fraction(valid_shuffles.prediction_shuffle != valid_shuffles.prediction_original) if len(valid_shuffles) else None},
        "latency_ms": {"median": float(rows.latency_ms.median()), "p95": float(rows.latency_ms.quantile(.95))},
        "usage": {"request_count": int(all_rows.request_count.sum()), "complete": known_cost,
                  "input_tokens": int(all_rows.input_tokens.sum()) if known_cost else None,
                  "output_tokens": int(all_rows.output_tokens.sum()) if known_cost else None},
        "cost": {"basis": "uncached list-price estimate; failed unknown usage remains unknown",
                 "total_usd": float(all_rows.cost_usd.sum()) if known_cost else None,
                 "known_usd_lower_bound": float(all_rows.cost_usd.sum()),
                 "base_cost_per_record": float(rows.cost_usd.sum() / len(rows)) if base_cost_known and len(rows) else None,
                 "base_cost_per_1000": float(rows.cost_usd.sum() / len(rows) * 1000) if base_cost_known and len(rows) else None},
        "expected_score_variant": {"records": len(expected), "accuracy": fraction(expected_correct)}
    }


def pass_rule(base, seed, draws):
    jev = base[base.method == "jev_direct"]
    llm_names = sorted(m for m in base.method.unique() if "llm" in m)
    if jev.empty or not llm_names:
        return {"outcome": "unavailable", "reason": "Jev direct and language model results are required"}
    common = set(jev.record_id)
    for method in llm_names:
        common &= set(base[base.method == method].record_id)
    if not common:
        return {"outcome": "unavailable", "reason": "No common evaluated records"}
    matched = base[base.record_id.isin(common)]
    comparator = sorted(llm_names, key=lambda name: (-matched[matched.method == name].correct.mean(), name))[0]
    left, right = matched[matched.method == "jev_direct"], matched[matched.method == comparator]
    test = pairwise(left, right, seed, draws)
    noninferior = test["filer_cluster_bootstrap_95"][0] >= -.02
    higher_retained = coverage(left, [.8])[0]["accuracy"] > coverage(right, [.8])[0]["accuracy"]
    price_known = left.usage_complete.all() and right.usage_complete.all() and left.cost_usd.notna().all() and right.cost_usd.notna().all()
    ratio = float(left.cost_usd.sum() / right.cost_usd.sum()) if price_known and right.cost_usd.sum() > 0 else None
    cheap = ratio <= .2 if ratio is not None else None
    outcome = "pass" if noninferior and (cheap is True or higher_retained) else "fail"
    if noninferior and not higher_retained and cheap is None:
        outcome = "inconclusive"
    return {"outcome": outcome, "records": len(common), "best_llm": comparator, "comparison": test,
            "noninferior": noninferior, "cost_ratio": ratio, "at_most_one_fifth_cost": cheap,
            "higher_accuracy_at_80_coverage": bool(higher_retained),
            "limitations": ["Best comparator is selected on this sample; this is exploratory.",
                            "Pass rule uses filer-cluster bootstrap on the common method intersection."]}


def compute(rows, config, splits=None):
    if rows.empty:
        return {"methods": [], "pairwise": [], "pass_rule": {}}
    repeats = config["profiles"][rows.iloc[0].profile]["repeat_count"]
    methods = []
    for (method, regime), group in rows.groupby(["method", "context_regime"]):
        methods.append({"method": method, "context_regime": regime, "model": group.iloc[0].model,
                        **metric_group(group, splits, repeats)})
    base = rows[(rows.repeat_index == 0) & ~rows.shuffled]
    pairs, rules, execution = [], {}, []
    for regime, group in base.groupby("context_regime"):
        jev = group[group.method == "jev_direct"]
        for method in sorted(group.method.unique()):
            if "llm" in method and not jev.empty:
                pairs.append({"left": "jev_direct", "right": method, "context_regime": regime,
                              **pairwise(jev, group[group.method == method], config["seed"], config.get("bootstrap_samples", 2000))})
        rules[regime] = pass_rule(group, config["seed"], config.get("bootstrap_samples", 2000))
        a = group[group.method == "jev_composite_concurrent"]
        b = group[group.method == "jev_composite_fanout"]
        matched = a.merge(b, on="record_id", suffixes=("_concurrent", "_fanout"))
        if len(matched):
            valid = matched[~matched.failed_concurrent & ~matched.failed_fanout]
            components_same = []
            for row in valid.itertuples():
                x, y = json.loads(row.diagnostics_json_concurrent), json.loads(row.diagnostics_json_fanout)
                components_same.append(all(x.get(k) == y.get(k) for k in ("wording", "position", "metadata")))
            execution.append({"context_regime": regime, "records": len(valid), "failed_pairs": len(matched)-len(valid),
                              "prediction_agreement": fraction(valid.prediction_concurrent == valid.prediction_fanout),
                              "component_agreement": fraction(components_same)})
    return {"methods": methods, "pairwise": pairs, "pass_rule": rules, "jev_execution_comparison": execution}
