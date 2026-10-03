import html
import json
import re
import shutil
from pathlib import Path
import pandas as pd
from benchmark.config import file_hash, json_write, read_yaml
from benchmark.metrics import compute
from benchmark.summary import dataset_summary, make_verdict, criterion_lines
from benchmark.analysis import build_analysis, method_name, is_direct
from benchmark.narrative import render_report, render_details


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
        parts.append(f'<text x="695" y="{55+i*22}" style="fill:{color}">{html.escape(method_name(method["method"], method["model"]))}</text>')
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
        summary["limitations"].insert(0, "This is a fixture, smoke, or incomplete run; it cannot support a deployment recommendation.")
        for rule in summary["pass_rule"].values():
            rule["outcome"] = "not_evaluated"
        metrics["pass_rule"] = summary["pass_rule"]
        json_write(folder / "metrics.json", metrics)
    verdict = make_verdict(rows, metrics, status) | {"run_id": folder.name, "predictions_sha256": file_hash(folder / "predictions.parquet")}
    dataset = dataset_summary(rows, manifest, summary["sample_manifest"])
    analysis = build_analysis(rows, metrics, config, verdict)
    summary.update(verdict=verdict, tested_dataset=dataset, analysis=analysis)
    json_write(folder / "analysis.json", analysis)
    json_write(folder / "verdict.json", verdict)
    json_write(folder / "management_summary.json", summary)
    audit = ['# The original criterion remains archived', ''] + criterion_lines(verdict)
    if not verdict.get('criterion_audit'):
        audit += ['This run does not evaluate the original criterion. See the run status and metrics.']
    (folder / 'criterion-audit.md').write_text('\n'.join(audit) + '\n')
    for regime in sorted(rows.context_regime.unique()):
        filename = f"coverage-{regime}.svg"
        (folder / filename).write_text(coverage_svg([m for m in metrics["methods"] if m["context_regime"] == regime
                                                   and (is_direct(m['method']) or m['method'] == 'rules_baseline')]))
    (folder / "report.md").write_text(render_report(summary, analysis, config))
    (folder / "details.md").write_text(render_details(summary, analysis, config))
    return metrics


def publish_report(folder, destination, prefix):
    """Package an offline report for sharing; no hand-written summary diverges."""
    if not re.fullmatch(r'[A-Za-z0-9_-]+', prefix):
        raise ValueError('Report prefix must contain letters, digits, underscores or hyphens')
    folder, destination = Path(folder), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    summary = json.loads((folder / 'management_summary.json').read_text())
    metrics = json.loads((folder / 'metrics.json').read_text())
    evidence = destination / f'{prefix}-validation.json'
    previous = json.loads(evidence.read_text()) if evidence.exists() else {}
    snapshot = previous if previous.get('run_id') == folder.name else {}
    artifacts = ['predictions.parquet', 'metrics.json', 'analysis.json', 'report.md', 'details.md', 'criterion-audit.md',
                 'freeze.json', 'resolved_config.yaml', 'case_config.yaml', 'prompts.yaml', 'pricing.yaml',
                 'dataset_manifest.json', 'sample_manifest.json']
    snapshot.update(run_id=folder.name, status=summary['run'], configuration=read_yaml(folder / 'resolved_config.yaml'),
                    case_configuration=read_yaml(folder / 'case_config.yaml'), prompts=read_yaml(folder / 'prompts.yaml'),
                    pricing=read_yaml(folder / 'pricing.yaml'), dataset_manifest=summary['dataset'],
                    sample_manifest=summary['sample_manifest'], tested_dataset=summary['tested_dataset'],
                    methods=metrics['methods'], pairwise=metrics['pairwise'], pass_rule=metrics['pass_rule'],
                    jev_execution_comparison=metrics.get('jev_execution_comparison', []),
                    verdict=summary['verdict'], analysis=summary['analysis'], limitations=summary['limitations'],
                    source_artifact_hashes={name: file_hash(folder / name) for name in artifacts if (folder / name).exists()},
                    report_generator_hashes={f'benchmark/{name}': file_hash(Path(__file__).parent / name)
                                            for name in ['reporting.py', 'summary.py', 'analysis.py', 'narrative.py']})
    json_write(evidence, snapshot)
    for path in sorted(folder.glob('coverage-*.svg')):
        shutil.copyfile(path, destination / f'{prefix}-{path.name}')
    for document in ['report.md', 'details.md']:
        text = (folder / document).read_text()
        for filename in ['analysis.json', 'metrics.json', 'dataset_manifest.json', 'sample_manifest.json',
                         'resolved_config.yaml', 'prompts.yaml']:
            text = text.replace(f']({filename})', f']({evidence.name})')
        for filename in ['details.md', 'criterion-audit.md'] + [path.name for path in folder.glob('coverage-*.svg')]:
            text = text.replace(f']({filename})', f']({prefix}-{filename})')
        (destination / f'{prefix}-{document}').write_text(text)
    shutil.copyfile(folder / 'criterion-audit.md', destination / f'{prefix}-criterion-audit.md')
    return destination / f'{prefix}-report.md'
