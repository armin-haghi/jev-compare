"""Independent yes/no case proving that the framework has no finance dependency."""
import json
from pathlib import Path
import pandas as pd
from benchmark.config import file_hash, json_write
from benchmark.schemas import BenchmarkRecord, MethodResult


def prepare(config):
    directory = Path(config["processed_dir"])
    directory.mkdir(parents=True, exist_ok=True)
    records = []
    for i in range(24):
        answer = "yes" if i % 2 else "no"
        records.append(BenchmarkRecord(record_id=f"toy-{i:03}", case_id="toy", source={"cik": str(i // 2)},
                                       input={"label": answer, "statement": "toy"}, reference=answer,
                                       groups={"template_line": answer, "statement": "toy", "fiscal_year": "2024"}))
    path = directory / "eligible_records.parquet"
    pd.DataFrame([{"record_json": r.model_dump_json()} for r in records]).to_parquet(path, index=False)
    pd.DataFrame([{"template_line": key, "eligible_records": 12} for key in ["yes", "no"]]).to_csv(directory / "sec_lines_summary.csv", index=False)
    json_write(directory / "dataset_manifest.json", {"dataset_sha256": file_hash(path), "records": len(records),
                                                    "limitations": ["Synthetic fixture data; no study evidence."]})
    return path


def load_records(config):
    return [BenchmarkRecord.model_validate_json(s) for s in pd.read_parquet(
        Path(config["processed_dir"]) / "eligible_records.parquet").record_json]


def build_payload(record, context_regime, case_config):
    return {key: record.input[key] for key in ("label", "statement")}


def candidates(record, case_config):
    return [{"id": key, "label": key.title(), "description": f"The answer is {key}.", "template_order": i}
            for i, key in enumerate(["yes", "no"])]


def is_correct(prediction, reference, case_config):
    return prediction == reference


def rules(payload, candidates, case_config):
    return MethodResult(prediction=payload["label"], confidence=1, confidence_kind="rule_fired")
