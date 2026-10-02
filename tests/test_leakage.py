import json
from cases.sec_lines.features import ALLOWLIST, build_payload
from tests.test_case_contract import tables
from cases.sec_lines.dataset import records_from_tables


def test_payload_allowlist_prevents_provenance_leakage():
    records, _, _ = records_from_tables(*tables(), {"fiscal_years": [2024]})
    for record in records:
        record.input["reference"] = record.reference
        record.input["tag"] = record.source["tag"]
        for regime in ("label_only", "with_context"):
            payload = build_payload(record, regime, {})
            assert set(payload) <= ALLOWLIST
            assert record.source["tag"] not in json.dumps(payload)
            assert record.source["standard_label"] not in json.dumps(payload)
    # Natural printed wording can equal a taxonomy label without provenance leakage.
    records[0].input["label"] = records[0].source["standard_label"]
    assert build_payload(records[0], "label_only", {})["label"] == records[0].input["label"]
