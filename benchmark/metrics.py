"""Every number the reports use, computed from saved results of one or more runs. No provider calls or case imports."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from benchmark.config import file_hash, json_write, read_yaml

CUTOFFS = (.99, .95, .9, .8, 0.)


JEV = ("typesafe-ai/jev", "jev")
LEGACY = ("jev_direct", "direct_llm_small", "direct_llm_frontier")  # method names of runs before models were listed by name


def is_model(method):
    return method.startswith(("decision:", "chat:")) or method in LEGACY


def ordered(methods):
    """Model methods with Jev first, then decision models, then chat models."""
    return sorted((m for m in methods if is_model(m)),
                  key=lambda m: (methods[m]["model"] not in JEV, not m.startswith(("decision:", "jev")), m))


def first_answers(rows):
    return rows[(rows.repeat_index == 0) & ~rows.shuffled]


def consistency(rows):
    """Answers that changed when a record was asked again, or with its options reordered."""
    repeats = [g for _, g in rows[~rows.shuffled].groupby("record_id") if len(g) > 1]
    reorders = rows[rows.shuffled].merge(first_answers(rows), on="record_id", suffixes=("", "_first"))
    return {"repeats": {"records": len(repeats), "failed": sum(bool(g.failed.any()) for g in repeats),
                        "changed": sum(g.prediction.nunique() > 1 for g in repeats if not g.failed.any())},
            "reorders": {"records": len(reorders), "failed": int((reorders.failed | reorders.failed_first).sum()),
                         "changed": int(((reorders.prediction != reorders.prediction_first)
                                         & ~reorders.failed & ~reorders.failed_first).sum())}}


def results(rows):
    first = first_answers(rows)
    answered = first.prediction != "ABSTAIN"
    known = bool(first.usage_complete.all() and first.cost_usd.notna().all())
    calls = int(first.request_count.sum())
    per_call = lambda column: float(first[column].sum() / calls) if known and calls else None
    return {"model": first.iloc[0].model, "records": len(first), "correct": int(first.correct.sum()),
            "failed": int(first.failed.sum()), "answered": int(answered.sum()),
            "answered_correct": int(first.correct[answered].sum()), "requests": calls,
            "cost_per_1000_usd": float(first.cost_usd.sum() / len(first) * 1000) if known else None,
            "input_tokens_per_call": per_call("input_tokens"), "output_tokens_per_call": per_call("output_tokens"),
            "median_seconds": float(first.latency_ms.median() / 1000),
            "p95_seconds": float(first.latency_ms.quantile(.95) / 1000), **consistency(rows)}


def confidence(first):
    c, ok = first.confidence.to_numpy(float), first.correct.to_numpy(bool)
    band = np.minimum((c * 10).astype(int), 9)
    bands = [{"from": b / 10, "to": (b + 1) / 10, "answers": int((band == b).sum()),
              "mean_confidence": float(c[band == b].mean()), "correct": int(ok[band == b].sum())}
             for b in range(10) if (band == b).any()]
    return {"cutoffs": [{"cutoff": t, "answers": int((c >= t).sum()), "incorrect": int(((c >= t) & ~ok).sum())}
                        for t in CUTOFFS],
            "bands": bands,
            "calibration_gap": sum(b["answers"] * abs(b["mean_confidence"] - b["correct"] / b["answers"])
                                   for b in bands) / len(c)}


def pair(left, right):
    joined = left.merge(right, on="record_id", suffixes=("_left", "_right"), validate="one_to_one")
    a, b = joined.correct_left.astype(bool), joined.correct_right.astype(bool)
    return {"records": len(joined), "both_correct": int((a & b).sum()), "both_incorrect": int((~a & ~b).sum()),
            "left_only_correct": int((a & ~b).sum()), "right_only_correct": int((~a & b).sum())}


def routing(jev, other):
    joined = jev.merge(other, on="record_id", suffixes=("_jev", "_other"))
    return [{"cutoff": t, "records": int(below.sum()), "jev_correct": int(joined.correct_jev[below].sum()),
             "other_correct": int(joined.correct_other[below].sum())}
            for t in CUTOFFS[1:-1] for below in [joined.confidence_jev < t]]


def wording_groups(first, splits):
    """Whether each record's answer key is the usual choice of other companies using the same wording."""
    counts = {key: dict(zip(g.reference, g.filers)) for key, g in splits.groupby(["statement", "normalized_label"])}
    groups, agreement = {}, []
    for row in first.itertuples():
        g = json.loads(row.groups_json)
        others = dict(counts.get((g.get("statement"), g.get("normalized_label")), {}))
        others[row.reference] = others.get(row.reference, 0) - 1
        total = sum(others.values())
        if total <= 0:
            groups[row.record_id] = "new"
            continue
        usual = max(others.items(), key=lambda kv: (kv[1], kv[0]))[0]
        groups[row.record_id] = "usual" if usual == row.reference else "unusual"
        agreement.append(others.get(row.reference, 0) / total)
    return groups, agreement


def regime(rows, splits):
    first = first_answers(rows)
    methods = {m: results(g) for m, g in rows.groupby("method")}
    models = ordered(methods)
    answers = {m: first[first.method == m] for m in models + ["rules_baseline"] if m in methods}
    primary = next((m for m in models if methods[m]["model"] in JEV), None)
    out = {"methods": methods, "models": models, "primary": primary,
           "confidence": {m: confidence(answers[m]) for m in models},
           "categories": {m: {c: [len(g), int(g.correct.sum())] for c, g in a.groupby("reference")} for m, a in answers.items()},
           "pairs": {}, "routing": {}}
    if primary is None:
        return out
    jev = answers[primary]
    for m in models:
        if m == primary:
            continue
        out["pairs"][m] = pair(jev, answers[m])
        out["routing"][m] = routing(jev, answers[m])
    if splits is not None and "normalized_label" in json.loads(first.iloc[0].groups_json):
        groups, agreement = wording_groups(jev, splits)
        counts = lambda a: {k: [int((g == k).sum()), int((g[a.correct.to_numpy()] == k).sum())] for k in ("usual", "unusual", "new")
                            for g in [a.record_id.map(groups)]}
        out["wording"] = {"other_company_agreement": float(np.mean(agreement)), "records_with_other_companies": len(agreement),
                          "groups": {m: counts(answers[m]) for m in models}}
    return out


def combine(folders):
    """Load runs that tested the same records on the same data; each method may come from one run only."""
    runs = []
    for folder in map(Path, folders):
        runs.append({"folder": folder, "rows": pd.read_parquet(folder / "predictions.parquet"),
                     "status": json.loads((folder / "status.json").read_text()),
                     "manifest": json.loads((folder / "dataset_manifest.json").read_text()),
                     "sample": json.loads((folder / "sample_manifest.json").read_text()),
                     "prices": read_yaml(folder / "pricing.yaml")["prices"],
                     "config": read_yaml(folder / "resolved_config.yaml")})
    first, seen = runs[0], {}
    for run in runs:
        if run["manifest"]["dataset_sha256"] != first["manifest"]["dataset_sha256"]:
            raise ValueError(f"{run['folder'].name} used a different dataset from {first['folder'].name}")
        if run["sample"]["main"] != first["sample"]["main"]:
            raise ValueError(f"{run['folder'].name} tested different records from {first['folder'].name}")
        for method in run["rows"].method.unique():
            if method == "rules_baseline" and method in seen:  # deterministic and free: keep the first run's answers
                run["rows"] = run["rows"][run["rows"].method != method]
            elif method in seen:
                raise ValueError(f"{method} appears in both {seen[method]} and {run['folder'].name}")
            seen[method] = run["folder"].name
    return runs, pd.concat([run["rows"] for run in runs], ignore_index=True)


def compute(folders):
    runs, rows = combine([folders] if isinstance(folders, (str, Path)) else folders)
    first_run = runs[0]
    split_file = first_run["folder"] / "label_splits.parquet"
    splits = pd.read_parquet(split_file) if split_file.exists() else None
    manifest, sample = first_run["manifest"], first_run["sample"]
    first = first_answers(rows).drop_duplicates("record_id")
    sources = [json.loads(s) for s in first.source_json]
    groups = [json.loads(g) for g in first.groups_json]
    excluded = manifest.get("exclusion_counts", {})
    prices = {p["model"]: p for run in reversed(runs) for p in run["prices"]}
    return {
        "runs": [{"id": run["folder"].name, "date": f"{run['folder'].name[:4]}-{run['folder'].name[4:6]}-{run['folder'].name[6:8]}",
                  "dataset": run["status"].get("dataset"), "mode": run["status"]["mode"], "complete": run["status"]["complete"],
                  "methods": sorted(run["rows"].method.unique()), "outputs": len(run["rows"]),
                  "requests": int(run["rows"].request_count.sum()), "failed_outputs": int(run["rows"].failed.sum()),
                  "unknown_usage_outputs": int((~run["rows"].usage_complete).sum()),
                  "record_concurrency": run["config"].get("record_concurrency", 1),
                  "predictions_sha256": file_hash(run["folder"] / "predictions.parquet")} for run in runs],
        "dataset": {"scope": {"all_lines": manifest.get("records", 0) + manifest.get("excluded", 0),
                              "in_scope_before_repeats": manifest.get("records", 0) + excluded.get("duplicate_filer_label", 0),
                              "in_scope": manifest.get("records"), "sampled": len(sample["main"])},
                    "repeat_records": len(sample["repeat"]), "reorder_records": len(sample["shuffle"]),
                    "companies": len({str(s["cik"]) for s in sources if s.get("cik")}),
                    "fiscal_years": sorted({g["fiscal_year"] for g in groups if g.get("fiscal_year")}),
                    "statements": {k: sum(g.get("statement") == k for g in groups) for k in sorted({g.get("statement") for g in groups})},
                    "answer_key_consistency": manifest.get("answer_key_consistency")},
        "prices": [prices[m] for m in sorted(set(rows.model)) if m in prices],
        "regimes": {r: regime(g, splits) for r, g in rows.groupby("context_regime")},
    }


def write_evidence(folder):
    evidence = compute(folder)
    json_write(Path(folder) / "evidence.json", evidence)
    return evidence
