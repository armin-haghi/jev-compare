import importlib
import json
import random
import shutil
import time
import threading
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd
import requests
import yaml

from benchmark.config import digest, file_hash, json_write, load_case, read_yaml, resolve
from benchmark.metrics import write_evidence
from benchmark.pricing import Budget, BudgetExceeded, lookup
from benchmark.runtime import GATEWAY, Runtime, CallFailed, require_key, jev_client
from benchmark.sampling import samples
from benchmark.schemas import MethodResult


def expand_methods(config):
    """Rules, then each decision model and chat model listed by name in the settings."""
    methods = [{"method": "rules_baseline", "module": "rules_baseline", "provider": "rules", "model": "rules-v1"}] if config.get("rules", True) else []
    methods += [m | {"method": f"decision:{m['model']}", "module": "decision_model", "provider": "vercel"} for m in config.get("decision_models", [])]
    methods += [m | {"method": f"chat:{m['model']}", "module": "chat_model", "provider": "vercel"} for m in config.get("chat_models", [])]
    names = [m["method"] for m in methods]
    if not names or len(set(names)) != len(names):
        raise ValueError("Configure at least one method, each model once")
    return methods


def frozen_files(config):
    paths = [*Path("benchmark").rglob("*.py"), Path("pyproject.toml"), Path("uv.lock")]
    case_module = load_case(config["case"])
    root = Path(case_module.__file__).parent
    paths.extend(p for p in root.rglob("*") if p.suffix in (".py", ".yaml", ".json"))
    paths.extend(Path(config[k]) for k in ("case_config", "prompts", "pricing") if config.get(k))
    return {str(p): file_hash(p) for p in sorted(set(paths)) if p.is_file()}


def freeze(config):
    data = {"config": config, "files": frozen_files(config)}
    return data | {"sha256": digest(data)}


def preflight(config, methods):
    """Check credentials and model names, and take prices from the gateway catalog."""
    models = [m for m in methods if m["provider"] != "rules"]
    if not models:
        return {}, []
    require_key("vercel")
    response = requests.get(f"{GATEWAY}/models", timeout=60)
    response.raise_for_status()
    catalog = {m["id"]: m for m in response.json()["data"]}
    missing = sorted({m["model"] for m in models} - catalog.keys())
    if missing:
        raise ValueError(f"Models absent from the Vercel AI Gateway catalog: {missing}")
    today = datetime.now(timezone.utc).date().isoformat()
    prices = [{"model": key, "input_per_million": round(float(catalog[key]["pricing"]["input"]) * 1e6, 6),
               "output_per_million": round(float(catalog[key]["pricing"].get("output", 0)) * 1e6, 6),
               "currency": "USD", "effective_date": today, "source_url": f"{GATEWAY}/models"}
              for key in sorted({m["model"] for m in models})]
    metadata = {"gateway_models": {key: {f: catalog[key].get(f) for f in ("id", "name", "pricing", "type")}
                                   for key in sorted({m["model"] for m in models})}}
    decision = [m.get("request_model", m["model"]) for m in models if m["module"] == "decision_model"]
    if decision:
        client = jev_client(config)
        try:
            available = {m.name for m in client.models.list().models}
        finally:
            client.close()
        if set(decision) - available:
            raise ValueError(f"Decision models absent from the System One API: {sorted(set(decision) - available)}; available: {sorted(available)}")
        metadata["decision_models_available"] = sorted(available)
    return metadata, prices


def workload(config, profile="small", smoke_per_line=None):
    case = load_case(config["case"])
    case_config = read_yaml(config["case_config"])
    records = case.load_records(case_config)
    chosen = samples(records, config, profile, smoke_per_line)
    repeats = {r.record_id for r in chosen["repeat"]}
    shuffles = {r.record_id for r in chosen["shuffle"]}
    evaluations = sum((1 + (config["profiles"][profile]["repeat_count"]-1 if r.record_id in repeats else 0)
                       + int(r.record_id in shuffles)) * len(config["context_regimes"]) for r in chosen["main"])
    output = []
    for method in expand_methods(config):
        calls = evaluations if method["provider"] != "rules" else 0
        output.append({"method": method["method"], "evaluations": evaluations, "requests_before_retries": calls,
                       "maximum_requests": calls * config.get("attempts", 3)})
    return {"profile": profile, "main_records": len(chosen["main"]),
            "methods": output, "requests_before_retries": sum(m["requests_before_retries"] for m in output)}


def execute_records(predict, records, concurrency):
    """Keep at most concurrency records in flight and drain them on failure."""
    iterator = iter(records)
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        pending = {pool.submit(predict, record) for record in list_next(iterator, concurrency)}
        try:
            while pending:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    future.result()
                pending.update(pool.submit(predict, record) for record in list_next(iterator, len(done)))
        except BaseException:
            for future in pending:
                future.cancel()
            raise


def list_next(iterator, count):
    from itertools import islice
    return list(islice(iterator, count))


def run(config, profile="small", budget_usd=None, smoke_per_line=None, results_root="results",
        runtime_factory=None, run_id=None):
    config = resolve(config)
    if not 1 <= config.get("attempts", 3) <= 3:
        raise ValueError("attempts must be between one and three")
    if not config["context_regimes"]:
        raise ValueError("Context regimes cannot be empty")
    for name, settings in config["profiles"].items():
        if any(not isinstance(settings[k], int) or settings[k] < 1 for k in
               ("records_per_line", "repeat_records", "repeat_count", "shuffle_records")):
            raise ValueError(f"Profile sizes must be positive integers: {name}")
    if not isinstance(config.get("record_concurrency", 1), int) or not 1 <= config.get("record_concurrency", 1) <= 16:
        raise ValueError("record_concurrency must be an integer between 1 and 16")
    case = load_case(config["case"])
    case_config = read_yaml(config["case_config"])
    records = case.load_records(case_config)
    if not records:
        raise ValueError("Dataset has no eligible records")
    if len({r.record_id for r in records}) != len(records):
        raise ValueError("Dataset record IDs are not unique")
    chosen = samples(records, config, profile, smoke_per_line)
    methods = expand_methods(config)
    prompts = read_yaml(config["prompts"])
    frozen = freeze(config)
    dataset_dir = Path(case_config["processed_dir"])
    dataset_manifest = json.loads((dataset_dir / "dataset_manifest.json").read_text())
    actual_hash = file_hash(dataset_dir / "eligible_records.parquet")
    if actual_hash != dataset_manifest["dataset_sha256"]:
        raise ValueError("Processed dataset differs from its manifest")
    case_root = Path(case.__file__).parent
    for key, filename in (("template_sha256", "template.yaml"), ("sic_sha256", "sic_codes.json")):
        artifact = Path(case_config.get("sic_file", case_root / filename)) if key == "sic_sha256" else case_root / filename
        if key in dataset_manifest and file_hash(artifact) != dataset_manifest[key]:
            raise ValueError(f"{filename} changed after dataset preparation")
    root = Path(results_root)
    mode = "fixture" if runtime_factory else "smoke" if smoke_per_line is not None else "benchmark"
    paid = any(m["provider"] != "rules" for m in methods)
    if paid and budget_usd is None:
        raise ValueError("Paid execution requires --budget-usd")
    if runtime_factory:
        provider_metadata, prices = {"fixture": True}, read_yaml(config["pricing"])["prices"]
    else:
        provider_metadata, prices = preflight(config, methods)
    budget = Budget(budget_usd or 1)
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    if Path(run_id).name != run_id or run_id in (".", ".."):
        raise ValueError("Run ID must be a directory name")
    folder = root / run_id
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "resolved_config.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
    (folder / "case_config.yaml").write_text(yaml.safe_dump(case_config, sort_keys=False))
    (folder / "pricing.yaml").write_text(yaml.safe_dump({"prices": prices}, sort_keys=False))
    (folder / "prompts.yaml").write_text(yaml.safe_dump(prompts, sort_keys=False))
    json_write(folder / "freeze.json", frozen)
    json_write(folder / "dataset_manifest.json", dataset_manifest)
    json_write(folder / "provider_metadata.json", provider_metadata)
    json_write(folder / "sample_manifest.json", {k: [r.record_id for r in v] if k != "dropped" else v for k, v in chosen.items()})
    json_write(folder / "workload.json", workload(config, profile, smoke_per_line))
    for source, target in (("label_splits.parquet", "label_splits.parquet"), ("sec_lines_summary.csv", "dataset_summary.csv")):
        if (dataset_dir / source).exists():
            shutil.copyfile(dataset_dir / source, folder / target)
    json_write(folder / "payload_examples.json", {regime: case.build_payload(chosen["main"][0], regime, case_config)
                                                  for regime in config["context_regimes"]})
    start = time.perf_counter()
    rows = []
    journal_lock = threading.Lock()
    stop = threading.Event()
    status = {"profile": profile, "mode": mode, "complete": False, "run_id": run_id, "dataset_sha256": actual_hash}
    json_write(folder / "status.json", status)
    repeat_ids = {r.record_id for r in chosen["repeat"]}
    shuffle_ids = {r.record_id for r in chosen["shuffle"]}
    try:
        with (folder / "predictions.jsonl").open("a") as journal:
            for method in methods:
                def predict_record(record):
                    for regime in config["context_regimes"]:
                        jobs = [(0, False)]
                        if record.record_id in repeat_ids:
                            jobs += [(i, False) for i in range(1, config["profiles"][profile]["repeat_count"])]
                        if record.record_id in shuffle_ids:
                            jobs.append((0, True))
                        for repeat, shuffled in jobs:
                            if stop.is_set():
                                return
                            payload = case.build_payload(record, regime, case_config)
                            candidates = case.candidates(record, case_config)
                            if len({c["id"] for c in candidates}) != len(candidates) or not candidates:
                                raise ValueError("Candidates must be unique and nonempty")
                            if record.reference not in {c["id"] for c in candidates}:
                                raise ValueError("Reference is not a candidate")
                            if shuffled:
                                random.Random(f"{config['seed']}|{record.record_id}").shuffle(candidates)
                            call_config = {**method, "case": config["case"], "prompts": prompts,
                                           "attempts": config.get("attempts", 3),
                                           "timeout_seconds": config.get("timeout_seconds", 120)}
                            runtime = None
                            if method["provider"] != "rules":
                                price = lookup(prices, method["model"])
                                runtime = (runtime_factory or Runtime)(call_config, price, budget)
                            call_config["_runtime"] = runtime
                            before = time.perf_counter()
                            failed, error_type, exhausted, fatal_error = False, None, False, None
                            try:
                                module = importlib.import_module(f"benchmark.methods.{method['module']}")
                                result = MethodResult.model_validate(module.predict(payload, candidates, case_config, call_config))
                                if result.prediction not in {c["id"] for c in candidates} and not (method["provider"] == "rules" and result.prediction == "ABSTAIN"):
                                    raise ValueError("Prediction is outside the candidate set")
                            except BudgetExceeded:
                                failed, error_type, exhausted = True, "BudgetExceeded", True
                                result = MethodResult(prediction="FAILED", confidence=0, confidence_kind="failure")
                            except Exception as error:
                                failed, error_type = True, type(error).__name__
                                if isinstance(error, CallFailed) and error.fatal:
                                    fatal_error = error
                                result = MethodResult(prediction="FAILED", confidence=0, confidence_kind="failure")
                            elapsed = (time.perf_counter() - before) * 1000
                            usage = runtime.evidence() if runtime else {"calls": [], "request_count": 0, "usage_complete": True,
                                                                       "input_tokens": 0, "output_tokens": 0, "cost_usd": 0, "known_cost_usd": 0}
                            usage.setdefault("known_cost_usd", usage["cost_usd"] or 0)
                            if runtime and hasattr(runtime, "close"):
                                runtime.close()
                            diagnostics = result.diagnostics | {"calls": usage.pop("calls"), "error_type": error_type}
                            row = {"record_id": record.record_id, "case_id": record.case_id, "profile": profile,
                                   "context_regime": regime, "method": method["method"],
                                   "model": method["model"], "repeat_index": repeat, "shuffled": shuffled,
                                   "prediction": result.prediction, "confidence": result.confidence,
                                   "confidence_kind": result.confidence_kind,
                                   "probability_of_prediction": result.probability_of_prediction,
                                   "reference": record.reference,
                                   "correct": not failed and case.is_correct(result.prediction, record.reference, case_config),
                                   "failed": failed, "latency_ms": elapsed, **usage,
                                   "diagnostics_json": json.dumps(diagnostics, sort_keys=True, allow_nan=False),
                                   "groups_json": json.dumps(record.groups, sort_keys=True),
                                   "source_json": json.dumps(record.source, sort_keys=True),
                                   "input_json": json.dumps(record.input, sort_keys=True)}
                            with journal_lock:
                                rows.append(row)
                                journal.write(json.dumps(row, allow_nan=False) + "\n")
                                journal.flush()
                            if exhausted:
                                stop.set()
                                raise BudgetExceeded(f"Run stopped at its budget; evidence preserved in {folder}")
                            if fatal_error:
                                stop.set()
                                raise fatal_error
                    print(f"{method['method']}: {record.record_id[:12]} ({len(rows)} outputs)", flush=True)
                execute_records(predict_record, chosen["main"], config.get("record_concurrency", 1))
        status["complete"] = True
    finally:
        status["wall_time_seconds"] = time.perf_counter() - start
        status["conservative_budget_used_usd"] = budget.spent
        status["known_list_price_cost_usd"] = sum(row.get("known_cost_usd", 0) for row in rows)
        status["budget_note"] = "Conservative budget use includes unknown-call reservations; it is not a billed-charge measurement."
        status["output_rows"] = len(rows)
        json_write(folder / "status.json", status)
        if rows:
            pd.DataFrame(rows).to_parquet(folder / "predictions.parquet", index=False)
            returned = {}
            for row in rows:
                for call in json.loads(row["diagnostics_json"])["calls"]:
                    raw = call.get("raw") or {}
                    name = raw.get("model") or raw.get("response_metadata", {}).get("model_name")
                    if name:
                        returned.setdefault(row["method"], set()).add(name)
            provider_metadata["returned_model_ids"] = {key: sorted(names) for key, names in returned.items()}
            provider_metadata["version_limit"] = "Gateway aliases may echo the requested name without exposing immutable underlying weights."
            json_write(folder / "provider_metadata.json", provider_metadata)
    write_evidence(folder)
    return folder
