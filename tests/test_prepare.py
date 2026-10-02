import json
import zipfile
from pathlib import Path
import pandas as pd
from benchmark.config import file_hash
from cases.sec_lines import dataset
from tests.test_case_contract import tables


def test_prepare_builds_evidence_from_sec_format_archive(tmp_path, monkeypatch):
    archive_path = tmp_path / "2025q1.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for name, frame in zip(["sub", "pre", "num", "tag"], tables()):
            archive.writestr(name + ".txt", frame.to_csv(sep="\t", index=False))
    monkeypatch.setattr(dataset, "download", lambda *args: archive_path)
    industry = tmp_path / "sic.json"
    industry.write_text(json.dumps({"3576": "Computer communications equipment"}))
    config = {"raw_dir": str(tmp_path / "raw"), "processed_dir": str(tmp_path / "processed"),
              "quarter_start": "2025q1", "quarter_end": "2025q1", "fiscal_years": [2024], "sic_file": str(industry)}
    result = dataset.prepare(config)
    records = dataset.load_records(config)
    assert len(records) == 3
    assert all(r.input["sic_description"] == "Computer communications equipment" for r in records)
    manifest = json.loads((result.parent / "dataset_manifest.json").read_text())
    assert manifest["dataset_sha256"] == file_hash(result)
    assert manifest["sources"][0]["sha256"] == file_hash(archive_path)
    assert len(pd.read_csv(result.parent / "sec_lines_summary.csv")) == 29
    assert (result.parent / "model_inputs.parquet").exists()
    assert (result.parent / "excluded_records.parquet").exists()
    assert (result.parent / "mapping_review.json").exists()
