"""Explicit preparation, smoke, benchmark and artifact-only reporting commands."""
import argparse
import json
from pathlib import Path
from benchmark.config import load_case, load_env, read_yaml, resolve


def main():
    load_env()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "inspect"):
        child = commands.add_parser(name)
        child.add_argument("--case", default="sec_lines")
        child.add_argument("--case-config")
    for name in ("run", "smoke", "plan"):
        child = commands.add_parser(name)
        child.add_argument("--experiment", default="config/experiments/sec_lines.yaml")
        child.add_argument("--profile", choices=["small", "full"], default="small")
        child.add_argument("--budget-usd", type=float)
        child.add_argument("--results-root", default="results")
        child.add_argument("--allow-frontier", action="store_true",
                           help="Explicitly authorize frontier-model inference; omit until approved")
        if name == "smoke":
            child.add_argument("--records-per-line", type=int, default=5)
    child = commands.add_parser("report")
    child.add_argument("--run-id", required=True)
    child.add_argument("--results-root", default="results")
    commands.add_parser("demo", help="Run every method against deterministic local fixture responses; no paid calls")
    child = commands.add_parser("check", help="Validate credentials, pricing and model discovery without inference")
    child.add_argument("--experiment", default="config/experiments/sec_lines.yaml")
    args = parser.parse_args()
    if args.command in ("prepare", "inspect"):
        module = load_case(args.case)
        config = read_yaml(args.case_config or f"cases/{args.case}/case.yaml")
        if args.command == "prepare":
            print(module.prepare(config))
        else:
            directory = Path(config["processed_dir"])
            print((directory / "sec_lines_summary.csv").read_text())
            print((directory / "dataset_manifest.json").read_text())
            if (directory / "label_splits.parquet").exists():
                import pandas as pd
                splits = pd.read_parquet(directory / "label_splits.parquet")
                ambiguous = splits[splits.filer_split]
                print(f"Observed disagreement rows: {len(ambiguous)}; showing the first 20")
                print(ambiguous.head(20).to_string(index=False))
            records = module.load_records(config)
            for reference in sorted({r.reference for r in records}):
                for record in [r for r in records if r.reference == reference][:5]:
                    print(record.model_dump_json())
    elif args.command in ("run", "smoke"):
        from benchmark.runner import run
        print(run(read_yaml(args.experiment), args.profile, args.budget_usd,
                  args.records_per_line if args.command == "smoke" else None, args.results_root,
                  allow_frontier=args.allow_frontier))
    elif args.command == "plan":
        from benchmark.runner import workload
        print(json.dumps(workload(resolve(read_yaml(args.experiment)), args.profile), indent=2))
    elif args.command == "report":
        from benchmark.reporting import report
        if Path(args.run_id).name != args.run_id or args.run_id in (".", ".."):
            parser.error("--run-id must be a directory name")
        report(Path(args.results_root) / args.run_id)
        print(Path(args.results_root) / args.run_id / "report.md")
    elif args.command == "demo":
        from tests.fixtures.toy_case import prepare
        from tests.fixtures.fake_runtime import FakeRuntime
        from benchmark.runner import run
        config = read_yaml("tests/fixtures/experiment.yaml")
        prepare(read_yaml(config["case_config"]))
        print(run(config, budget_usd=1, runtime_factory=FakeRuntime))
    elif args.command == "check":
        from benchmark.runner import preflight, expand_methods
        config = resolve(read_yaml(args.experiment))
        metadata = preflight(config, expand_methods(config), read_yaml(config["pricing"])["prices"])
        print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
