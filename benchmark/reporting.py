import html
import json
from pathlib import Path
import pandas as pd
from benchmark.config import file_hash, json_write, read_yaml
from benchmark.metrics import compute
from benchmark.summary import dataset_summary, dataset_lines, make_verdict, verdict_lines, criterion_lines


def coverage_svg(metrics):
    """Standalone vector chart; no plotting or browser dependency."""
    width, height, left, top = 960, 600, 70, 40
    plot_w, plot_h = 600, 480
    colors = ["#2563eb", "#b91c1c", "#047857", "#7c3aed", "#b45309", "#0e7490", "#be185d", "#4d7c0f", "#4338ca", "#374151"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Retained coverage versus error rate">',
             '<rect width="100%" height="100%" fill="white"/>',
             '<style>text { font: 12px sans-serif; fill: #172033; }</style>']
    for i in range(6):
        x, y = left + plot_w * i/5, top + plot_h * i/5
        parts += [f'<path d="M {left} {y} H {left+plot_w}" stroke="#e5e7eb"/>',
                  f'<text x="{left-35}" y="{y+4}">{100-i*20}%</text>',
                  f'<text x="{x-12}" y="{top+plot_h+20}">{i*20}%</text>']
    for i, method in enumerate(metrics):
        points = sorted(method["confidence_coverage"], key=lambda r: r["coverage"])
        coords = " ".join(f'{left+r["coverage"]*plot_w:.1f},{top+(r["accuracy"] or 0)*plot_h:.1f}' for r in points)
        color = colors[i % len(colors)]
        parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2"/>')
        parts.append(f'<text x="695" y="{55+i*22}" fill="{color}">{html.escape(method["method"])}</text>')
    parts += [f'<text x="250" y="{height-25}">Share of records retained</text>',
              '<text x="16" y="300" transform="rotate(-90 16 300)">Error rate on retained records</text>', '</svg>']
    return "\n".join(parts)


def report(folder):
    folder = Path(folder)
    rows = pd.read_parquet(folder / "predictions.parquet")
    config = read_yaml(folder / "resolved_config.yaml")
    splits = pd.read_parquet(folder / "label_splits.parquet") if (folder / "label_splits.parquet").exists() else None
    status = json.loads((folder / "status.json").read_text())
    metrics = compute(rows, config, splits)
    metrics["run"] = status
    json_write(folder / "metrics.json", metrics)
    flat = [{"method": m["method"], "context_regime": m["context_regime"], "model": m["model"],
             "records": m["records"], "accuracy": m["accuracy"], "failure_rate": m["failure_rate"],
             "median_latency_ms": m["latency_ms"]["median"], "p95_latency_ms": m["latency_ms"]["p95"],
             "cost_per_1000_usd": m["cost"]["base_cost_per_1000"]} for m in metrics["methods"]]
    pd.DataFrame(flat).to_csv(folder / "metrics.csv", index=False)
    examples = {}
    base = rows[(rows.repeat_index == 0) & ~rows.shuffled]
    for (method, regime), group in base.groupby(["method", "context_regime"]):
        examples[f"{method}/{regime}"] = {}
        for label, correct in [("correct", True), ("incorrect", False)]:
            selected = group[group.correct == correct].sort_values(["confidence", "record_id"], ascending=[False, True]).head(3)
            examples[f"{method}/{regime}"][label] = [
                {"record_id": r.record_id, "prediction": r.prediction, "reference": r.reference,
                 "confidence": r.confidence, "failed": r.failed, "input": json.loads(r.input_json)}
                for r in selected.itertuples()]
    manifest = json.loads((folder / "dataset_manifest.json").read_text())
    summary = {"case": read_yaml(folder / "case_config.yaml").get("description", config["case"]),
               "run": status, "dataset": manifest, "methods": metrics["methods"], "pass_rule": metrics["pass_rule"],
               "provider_metadata": json.loads((folder / "provider_metadata.json").read_text()),
               "sample_manifest": json.loads((folder / "sample_manifest.json").read_text()),
               "pairwise": metrics["pairwise"], "examples": examples,
               "limitations": manifest.get("limitations", []) + [
                   "Costs use uncached list prices; billed invoice costs may differ.",
                   "Composite scores are not correctness probabilities.",
                   f"Record concurrency: {config.get('record_concurrency', 1)}; question concurrency: {config.get('question_concurrency', 8)}. Latency is measured under this load."]}
    if status["mode"] != "benchmark" or not status["complete"]:
        summary["limitations"].insert(0, "This is a fixture, smoke, or incomplete run; it cannot establish the study pass rule.")
        for rule in summary["pass_rule"].values():
            rule["outcome"] = "not_evaluated"
        metrics["pass_rule"] = summary["pass_rule"]
        json_write(folder / "metrics.json", metrics)
    verdict = make_verdict(rows, metrics, status) | {"run_id": folder.name, "predictions_sha256": file_hash(folder / "predictions.parquet")}
    dataset = dataset_summary(rows, manifest, summary["sample_manifest"])
    summary.update(verdict=verdict, tested_dataset=dataset)
    json_write(folder / "verdict.json", verdict)
    json_write(folder / "management_summary.json", summary)
    lines = dataset_lines(dataset, summary["case"], manifest) + verdict_lines(verdict) + [
             f"Run: {folder.name}. Mode: {status['mode']}. Complete: {status['complete']}.",
             f"Known list-price cost: ${rows.known_cost_usd.sum():.4f}; provider requests: {int(rows.request_count.sum()):,}.",
             "Accuracy counts failed calls and abstentions as wrong. Composite and direct sample sizes can differ.", "",
             "| Method | Context | Records | Accuracy | Failures | Cost per 1,000 |",
             "| --- | --- | ---: | ---: | ---: | ---: |"]
    for row in flat:
        price = f"$ {row['cost_per_1000_usd']:.4f}" if row["cost_per_1000_usd"] is not None else "unknown"
        lines.append(f"| {row['method']} | {row['context_regime']} | {row['records']} | {row['accuracy']:.2%} | {row['failure_rate']:.2%} | {price} |")
    lines += [""] + criterion_lines(verdict)
    lines += ["## Confidence ranks retained answers", ""]
    for regime in sorted(rows.context_regime.unique()):
        filename = f"coverage-{regime}.svg"
        (folder / filename).write_text(coverage_svg([m for m in metrics["methods"] if m["context_regime"] == regime]))
        lines += [f"![Coverage and error rate for {regime}]({filename})", ""]
    lines += ["## Limits bound these measurements", ""]
    lines.extend(f"- {text}" for text in summary["limitations"])
    lines += ["", "Source configuration, freeze hashes, dataset manifest and record-level outputs are stored beside this report.",
              "See metrics.json for matched comparisons, calibration, repeatability and option-order sensitivity."]
    (folder / "report.md").write_text("\n".join(lines) + "\n")
    return metrics
