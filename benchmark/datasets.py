"""Datasets: a fixed random sample of a case's records, saved once and reused by every run.

A run applies models to one dataset (data x models = run). Runs on the same dataset can be
combined in one report, so a model can be added later without repeating the others.
"""
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from benchmark.config import file_hash, json_write, load_case, read_yaml
from benchmark.schemas import BenchmarkRecord

ROOT = Path("data/samples")


def rank(record_id, seed, salt):
    """A stable random order that does not depend on file order."""
    return hashlib.sha256(f"{seed}|{salt}|{record_id}".encode()).hexdigest()


def create(case_name, case_config_path, size, seed=20261001, checked_share=.1, root=ROOT):
    """Draw `size` records at random; a share of them is also asked twice and with reordered options."""
    case_config = read_yaml(case_config_path)
    records = load_case(case_name).load_records(case_config)
    if not 0 < size <= len(records):
        raise ValueError(f"Size must be between 1 and {len(records)}")
    chosen = sorted(sorted(records, key=lambda r: rank(r.record_id, seed, "sample"))[:size], key=lambda r: r.record_id)
    checked = max(1, round(size * checked_share))
    pick = lambda salt: sorted(r.record_id for r in sorted(chosen, key=lambda r: rank(r.record_id, seed, salt))[:checked])
    processed = Path(case_config["processed_dir"])
    source = json.loads((processed / "dataset_manifest.json").read_text())
    digest = hashlib.sha256((source["dataset_sha256"] + "".join(r.record_id for r in chosen)).encode()).hexdigest()[:8]
    dataset_id = f"{case_name.replace('.', '_')}-{size}-{digest}"
    folder = Path(root) / dataset_id
    if folder.exists():
        return dataset_id
    folder.mkdir(parents=True)
    pd.DataFrame([{"record_json": r.model_dump_json()} for r in chosen]).to_parquet(folder / "records.parquet", index=False)
    if (processed / "label_splits.parquet").exists():
        shutil.copyfile(processed / "label_splits.parquet", folder / "label_splits.parquet")
    json_write(folder / "dataset.json", {
        "id": dataset_id, "case": case_name, "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed, "size": size, "records_sha256": file_hash(folder / "records.parquet"),
        "categories": dict(sorted(Counter(r.reference for r in chosen).items())),
        "asked_twice": pick("repeat"), "reordered_options": pick("reorder"), "source": source})
    return dataset_id


def load(dataset_id, root=ROOT):
    folder = Path(root) / dataset_id
    manifest = json.loads((folder / "dataset.json").read_text())
    if file_hash(folder / "records.parquet") != manifest["records_sha256"]:
        raise ValueError(f"Records of dataset {dataset_id} changed after it was created")
    records = [BenchmarkRecord.model_validate_json(s) for s in pd.read_parquet(folder / "records.parquet").record_json]
    return folder, manifest, records
