import json
import os
import shutil
from pathlib import Path
import pandas as pd
from benchmark.config import file_hash, json_write, read_yaml
from benchmark.metrics import compute
from benchmark.summary import dataset_summary, make_verdict
from benchmark.analysis import build_analysis
from benchmark.narrative import render_report


def report(folder):
    folder = Path(folder)
    methodology = folder / 'methodology.md'
    if not methodology.exists():
        shutil.copyfile(Path(__file__).resolve().parents[1] / 'docs' / 'methodology.md', methodology)
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
    summary.update(verdict=verdict, tested_dataset=dataset, analysis=analysis,
                   methodology={'file': 'methodology.md', 'sha256': file_hash(methodology)})
    json_write(folder / "analysis.json", analysis)
    json_write(folder / "verdict.json", verdict)
    json_write(folder / "management_summary.json", summary)
    (folder / "factsheet.md").write_text(render_report(summary, analysis, config))
    write_evidence(folder, folder / 'evidence.json')
    return metrics


def write_evidence(folder, evidence):
    """Consolidate shareable evidence and preserve the same run's cost ledger."""
    folder, evidence = Path(folder), Path(evidence)
    summary = json.loads((folder / 'management_summary.json').read_text())
    metrics = json.loads((folder / 'metrics.json').read_text())
    previous = json.loads(evidence.read_text()) if evidence.exists() else {}
    snapshot = previous if previous.get('run_id') == folder.name else {}
    artifacts = ['predictions.parquet', 'metrics.json', 'analysis.json', 'factsheet.md', 'methodology.md',
                 'freeze.json', 'resolved_config.yaml', 'case_config.yaml', 'prompts.yaml', 'pricing.yaml',
                 'dataset_manifest.json', 'sample_manifest.json']
    snapshot.update(run_id=folder.name, status=summary['run'], configuration=read_yaml(folder / 'resolved_config.yaml'),
                    case_configuration=read_yaml(folder / 'case_config.yaml'), prompts=read_yaml(folder / 'prompts.yaml'),
                    pricing=read_yaml(folder / 'pricing.yaml'), dataset_manifest=summary['dataset'],
                    sample_manifest=summary['sample_manifest'], tested_dataset=summary['tested_dataset'],
                    methods=metrics['methods'], pairwise=metrics['pairwise'], pass_rule=metrics['pass_rule'],
                    jev_execution_comparison=metrics.get('jev_execution_comparison', []),
                    verdict=summary['verdict'], analysis=summary['analysis'], limitations=summary['limitations'],
                    methodology=summary['methodology'] | {'text': (folder / 'methodology.md').read_text()},
                    source_artifact_hashes={name: file_hash(folder / name) for name in artifacts if (folder / name).exists()},
                    report_generator_hashes={f'benchmark/{name}': file_hash(Path(__file__).parent / name)
                                            for name in ['reporting.py', 'summary.py', 'analysis.py', 'narrative.py']})
    json_write(evidence, snapshot)


def publish_report(folder, destination):
    """Publish a factsheet and evidence file; raw predictions stay local."""
    folder, destination = Path(folder), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    repository = Path(__file__).resolve().parents[1]
    methodology = (os.path.relpath(repository / 'docs' / 'methodology.md', destination.resolve())
                   if destination.resolve().is_relative_to(repository) else
                   'https://github.com/armin-haghi/jev-compare/blob/main/docs/methodology.md')
    text = (folder / 'factsheet.md').read_text().replace('](methodology.md)', f']({methodology})')
    factsheet = destination / 'factsheet.md'
    factsheet.write_text(text)
    write_evidence(folder, destination / 'evidence.json')
    return factsheet
