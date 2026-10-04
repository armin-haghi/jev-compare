"""Prepare data, draw a dataset, run models on it, and report — runs on one dataset combine in one report."""
import argparse
import json
import tempfile
from pathlib import Path
from benchmark import datasets
from benchmark.config import load_case, load_env, read_yaml, resolve
from benchmark.metrics import compute, write_evidence


def print_summary(evidence):
    for run in evidence["runs"]:
        note = "" if run["mode"] == "benchmark" and run["complete"] else " Not study evidence."
        print(f"Run {run['id']}: {run['mode']}, {'complete' if run['complete'] else 'incomplete'}.{note}")
        print(f"{run['outputs']:,} outputs, {run['requests']:,} requests, {run['failed_outputs']:,} failed.")
    for regime, r in evidence["regimes"].items():
        for method, x in sorted(r["methods"].items()):
            cost = f"${x['cost_per_1000_usd']:.3f} per 1,000 records" if x["cost_per_1000_usd"] is not None else "cost unknown"
            print(f"  {regime} {method}: {x['correct']:,} of {x['records']:,} correct; {cost}")


def run_folders(results_root, dataset=None, run_ids=()):
    """All complete runs on a dataset, or the named runs (paths below the results folder)."""
    root = Path(results_root)
    if dataset:
        return sorted(f.parent for f in (root / dataset).glob("*/status.json") if json.loads(f.read_text())["complete"])
    if any(".." in Path(r).parts or Path(r).is_absolute() for r in run_ids):
        raise ValueError("--run-id must be a path below the results folder")
    return [root / r for r in run_ids]


def main():
    load_env()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "inspect", "sample"):
        child = commands.add_parser(name)
        child.add_argument("--case", default="sec_lines")
        child.add_argument("--case-config")
        if name == "sample":
            child.add_argument("--size", type=int, required=True, help="Number of records drawn at random")
            child.add_argument("--seed", type=int, default=20261001)
    for name in ("run", "plan", "check"):
        child = commands.add_parser(name)
        child.add_argument("--experiment", default="config/experiments/sec_lines.yaml")
        if name != "check":
            child.add_argument("--dataset", required=True, help="Dataset ID from the sample command")
        if name == "run":
            child.add_argument("--budget-usd", type=float)
            child.add_argument("--results-root", default="results")
    child = commands.add_parser("report")
    source = child.add_mutually_exclusive_group(required=True)
    source.add_argument("--dataset", help="Combine every complete run on this dataset")
    source.add_argument("--run-id", action="append", help="A run folder below the results folder; repeat to combine runs")
    child.add_argument("--results-root", default="results")
    child.add_argument("--publish-dir", help="Refresh the generated blocks of the documents in this directory")
    commands.add_parser("demo", help="Run every method on a synthetic dataset with fixture responses; no paid calls")
    args = parser.parse_args()

    if args.command in ("prepare", "inspect", "sample"):
        case_config = args.case_config or f"cases/{args.case}/case.yaml"
        module, config = load_case(args.case), read_yaml(case_config)
        if args.command == "prepare":
            print(module.prepare(config))
        elif args.command == "sample":
            print(datasets.create(args.case, case_config, args.size, args.seed))
        else:
            directory = Path(config["processed_dir"])
            print((directory / "sec_lines_summary.csv").read_text())
            print((directory / "dataset_manifest.json").read_text())
    elif args.command == "run":
        from benchmark.runner import run
        folder = run(read_yaml(args.experiment), args.dataset, args.budget_usd, args.results_root)
        print_summary(json.loads((folder / "evidence.json").read_text()))
        print(f"Results: {folder}")
    elif args.command == "plan":
        from benchmark.runner import workload
        print(json.dumps(workload(resolve(read_yaml(args.experiment)), args.dataset), indent=2))
    elif args.command == "check":
        from benchmark.runner import preflight, expand_methods
        config = resolve(read_yaml(args.experiment))
        metadata, prices = preflight(config, expand_methods(config))
        print(json.dumps({"metadata": metadata, "prices": prices}, indent=2))
    elif args.command == "report":
        from benchmark.report import publish
        folders = run_folders(args.results_root, args.dataset, args.run_id or ())
        if not folders:
            parser.error("No complete runs found")
        for folder in folders:
            write_evidence(folder)
        print_summary(compute(folders))
        if args.publish_dir:
            publish(folders, args.publish_dir)
            print(f"Documents refreshed in {args.publish_dir}")
    elif args.command == "demo":
        from tests.fixtures.toy_case import prepare
        from tests.fixtures.fake_runtime import FakeRuntime
        from benchmark.runner import run
        work = Path(tempfile.mkdtemp(prefix="jev-demo-"))
        case_config = work / "case.yaml"
        case_config.write_text(f"processed_dir: {work / 'data'}\n")
        prepare(read_yaml(case_config))
        config = read_yaml("tests/fixtures/experiment.yaml") | {"case_config": str(case_config)}
        dataset = datasets.create(config["case"], case_config, 8, root=work / "samples")
        folder = run(config, dataset, budget_usd=1, results_root=work / "results", datasets_root=work / "samples",
                     runtime_factory=FakeRuntime)
        print_summary(json.loads((folder / "evidence.json").read_text()))
        print(f"Demo output: {folder}")


if __name__ == "__main__":
    main()
