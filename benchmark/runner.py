"""Apply models to a dataset. Every answer, its usage and cost are saved as they arrive."""
import importlib
import json
import random
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
from itertools import islice
from pathlib import Path
from uuid import uuid4

import pandas as pd
import requests
import yaml

from benchmark import datasets
from benchmark.config import digest, file_hash, json_write, load_case, read_yaml, resolve
from benchmark.metrics import write_evidence
from benchmark.pricing import Budget, BudgetExceeded, lookup
from benchmark.runtime import GATEWAY, Runtime, CallFailed, require_key, jev_client
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


def check_config(config):
    if not 1 <= config.get("attempts", 3) <= 3:
        raise ValueError("attempts must be between one and three")
    if not config["context_regimes"]:
        raise ValueError("Context regimes cannot be empty")
    concurrency = config.get("record_concurrency", 1)
    if not isinstance(concurrency, int) or not 1 <= concurrency <= 16:
        raise ValueError("record_concurrency must be an integer between 1 and 16")


def jobs(record, dataset, regimes):
    """Every answer asked for one record: each input version, plus a repeat and a reordered version where sampled."""
    extra = [(1, False)] * (record.record_id in dataset["asked_twice"]) + [(0, True)] * (record.record_id in dataset["reordered_options"])
    return [(regime, repeat, reordered) for regime in regimes for repeat, reordered in [(0, False), *extra]]


def workload(config, dataset_id, root=datasets.ROOT):
    _, dataset, records = datasets.load(dataset_id, root)
    per_model = sum(len(jobs(r, dataset, config["context_regimes"])) for r in records)
    methods = [{"method": m["method"], "requests": per_model * (m["provider"] != "rules")} for m in expand_methods(config)]
    return {"dataset": dataset_id, "records": len(records), "methods": methods, "requests": sum(m["requests"] for m in methods)}


def write_inputs(folder, config, case_config, prompts, prices, metadata, dataset, dataset_folder, records):
    folder.mkdir(parents=True, exist_ok=False)
    for name, value in (("resolved_config", config), ("case_config", case_config), ("pricing", {"prices": prices}), ("prompts", prompts)):
        (folder / f"{name}.yaml").write_text(yaml.safe_dump(value, sort_keys=False))
    json_write(folder / "freeze.json", freeze(config))
    json_write(folder / "provider_metadata.json", metadata)
    json_write(folder / "dataset.json", {k: v for k, v in dataset.items() if k != "source"})
    json_write(folder / "dataset_manifest.json", dataset["source"])
    json_write(folder / "sample_manifest.json", {"main": [r.record_id for r in records], "repeat": dataset["asked_twice"],
                                                 "shuffle": dataset["reordered_options"]})
    if (dataset_folder / "label_splits.parquet").exists():
        shutil.copyfile(dataset_folder / "label_splits.parquet", folder / "label_splits.parquet")


class Execution:
    """Asks every method for every job of every record, journalling each answer."""

    def __init__(self, folder, config, case, case_config, prompts, prices, budget, dataset, runtime_factory):
        self.folder, self.config, self.case, self.case_config = folder, config, case, case_config
        self.prompts, self.prices, self.budget, self.dataset = prompts, prices, budget, dataset
        self.runtime_factory = runtime_factory or Runtime
        self.rows, self.lock, self.stop = [], threading.Lock(), threading.Event()

    def answer(self, method, record, regime, repeat, reordered):
        payload = self.case.build_payload(record, regime, self.case_config)
        candidates = self.case.candidates(record, self.case_config)
        ids = {c["id"] for c in candidates}
        if len(ids) != len(candidates) or record.reference not in ids:
            raise ValueError("Candidates must be unique and include the answer key")
        if reordered:
            random.Random(f"{self.dataset['seed']}|{record.record_id}").shuffle(candidates)
        call_config = {**method, "case": self.config["case"], "prompts": self.prompts, "attempts": self.config.get("attempts", 3),
                       "timeout_seconds": self.config.get("timeout_seconds", 120)}
        runtime = None if method["provider"] == "rules" else self.runtime_factory(call_config, lookup(self.prices, method["model"]), self.budget)
        call_config["_runtime"] = runtime
        before, failed, error_type, stop_error = time.perf_counter(), False, None, None
        try:
            module = importlib.import_module(f"benchmark.methods.{method['module']}")
            result = MethodResult.model_validate(module.predict(payload, candidates, self.case_config, call_config))
            if result.prediction not in ids and not (method["provider"] == "rules" and result.prediction == "ABSTAIN"):
                raise ValueError("Prediction is outside the candidate set")
        except BudgetExceeded as error:
            failed, error_type, stop_error = True, "BudgetExceeded", BudgetExceeded(f"Run stopped at its budget; evidence preserved in {self.folder}")
            result = MethodResult(prediction="FAILED", confidence=0, confidence_kind="failure")
        except Exception as error:
            failed, error_type = True, type(error).__name__
            stop_error = error if isinstance(error, CallFailed) and error.fatal else None
            result = MethodResult(prediction="FAILED", confidence=0, confidence_kind="failure")
        elapsed = (time.perf_counter() - before) * 1000
        usage = runtime.evidence() if runtime else {"calls": [], "request_count": 0, "usage_complete": True,
                                                    "input_tokens": 0, "output_tokens": 0, "cost_usd": 0}
        usage.setdefault("known_cost_usd", usage["cost_usd"] or 0)
        if runtime and hasattr(runtime, "close"):
            runtime.close()
        row = {"record_id": record.record_id, "case_id": record.case_id, "dataset": self.dataset["id"],
               "context_regime": regime, "method": method["method"], "model": method["model"],
               "repeat_index": repeat, "shuffled": reordered, "prediction": result.prediction,
               "confidence": result.confidence, "confidence_kind": result.confidence_kind,
               "probability_of_prediction": result.probability_of_prediction, "reference": record.reference,
               "correct": not failed and self.case.is_correct(result.prediction, record.reference, self.case_config),
               "failed": failed, "latency_ms": elapsed, **usage,
               "diagnostics_json": json.dumps(result.diagnostics | {"calls": usage.pop("calls"), "error_type": error_type},
                                              sort_keys=True, allow_nan=False),
               "groups_json": json.dumps(record.groups, sort_keys=True), "source_json": json.dumps(record.source, sort_keys=True),
               "input_json": json.dumps(record.input, sort_keys=True)}
        with self.lock:
            self.rows.append(row)
            self.journal.write(json.dumps(row, allow_nan=False) + "\n")
            self.journal.flush()
        if stop_error:
            self.stop.set()
            raise stop_error

    def method(self, method, records):
        def one(record):
            for job in jobs(record, self.dataset, self.config["context_regimes"]):
                if self.stop.is_set():
                    return
                self.answer(method, record, *job)
            print(f"{method['method']}: {record.record_id[:12]} ({len(self.rows)} outputs)", flush=True)
        execute_records(one, records, self.config.get("record_concurrency", 1))

    def all(self, methods, records):
        with (self.folder / "predictions.jsonl").open("a") as self.journal:
            for method in methods:
                self.method(method, records)


def execute_records(predict, records, concurrency):
    """Keep at most concurrency records in flight and drain them on failure."""
    iterator = iter(records)
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        pending = {pool.submit(predict, record) for record in islice(iterator, concurrency)}
        try:
            while pending:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    future.result()
                pending.update(pool.submit(predict, record) for record in islice(iterator, len(done)))
        except BaseException:
            for future in pending:
                future.cancel()
            raise


def finish(folder, status, execution, started, metadata):
    rows = execution.rows
    status |= {"wall_time_seconds": time.perf_counter() - started, "output_rows": len(rows),
               "conservative_budget_used_usd": execution.budget.spent,
               "known_list_price_cost_usd": sum(r.get("known_cost_usd", 0) for r in rows),
               "budget_note": "Conservative budget use includes unknown-call reservations; it is not a billed-charge measurement."}
    json_write(folder / "status.json", status)
    if not rows:
        return
    pd.DataFrame(rows).to_parquet(folder / "predictions.parquet", index=False)
    returned = {}
    for row in rows:
        for call in json.loads(row["diagnostics_json"])["calls"]:
            name = (call.get("raw") or {}).get("model")
            if name:
                returned.setdefault(row["method"], set()).add(name)
    metadata["returned_model_ids"] = {key: sorted(names) for key, names in returned.items()}
    json_write(folder / "provider_metadata.json", metadata)


def run(config, dataset_id, budget_usd=None, results_root="results", datasets_root=datasets.ROOT,
        runtime_factory=None, run_id=None):
    """One run applies the configured models to one dataset; results go to results/DATASET/RUN."""
    config = resolve(config)
    check_config(config)
    dataset_folder, dataset, records = datasets.load(dataset_id, datasets_root)
    if dataset["case"] != config["case"]:
        raise ValueError(f"Dataset {dataset_id} belongs to case {dataset['case']}, not {config['case']}")
    case, case_config = load_case(config["case"]), read_yaml(config["case_config"])
    methods = expand_methods(config)
    if budget_usd is None and any(m["provider"] != "rules" for m in methods):
        raise ValueError("Paid execution requires --budget-usd")
    if runtime_factory:
        metadata, prices = {"fixture": True}, read_yaml(config["pricing"])["prices"]
    else:
        metadata, prices = preflight(config, methods)
    names = "+".join(m["model"].split("/")[-1] for m in methods if m["provider"] != "rules") or "rules"
    run_id = run_id or f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{names}-{uuid4().hex[:4]}"
    folder = Path(results_root) / dataset_id / run_id
    write_inputs(folder, config, case_config, read_yaml(config["prompts"]), prices, metadata, dataset, dataset_folder, records)
    execution = Execution(folder, config, case, case_config, read_yaml(config["prompts"]), prices,
                          Budget(budget_usd or 1), dataset, runtime_factory)
    status = {"run_id": run_id, "dataset": dataset_id, "mode": "fixture" if runtime_factory else "benchmark", "complete": False}
    json_write(folder / "status.json", status)
    started = time.perf_counter()
    try:
        execution.all(methods, records)
        status["complete"] = True
    finally:
        finish(folder, status, execution, started, metadata)
    write_evidence(folder)
    return folder
