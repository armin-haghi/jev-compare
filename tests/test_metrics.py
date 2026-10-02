import json
import pandas as pd
import pytest
from benchmark.metrics import calibration, coverage, pairwise


def frame(correct, confidence=None):
    return pd.DataFrame({"record_id": [str(i) for i in range(len(correct))],
                         "correct": correct, "confidence": confidence or [.5]*len(correct),
                         "probability_of_prediction": confidence or [.5]*len(correct),
                         "source_json": [json.dumps({"cik": str(i//2)}) for i in range(len(correct))],
                         "failed": False})


def test_calibration_has_known_values():
    values = calibration(frame([True, False], [1, 0]))
    assert values["selected_answer_brier"] == 0
    assert values["expected_calibration_error"] == 0
    values = calibration(frame([True, False], [.5, .5]))
    assert values["selected_answer_brier"] == .25
    assert values["expected_calibration_error"] == 0


def test_coverage_ties_use_record_id():
    rows = frame([True, False, False, True])
    result = coverage(rows, [.5])[0]
    assert result["records"] == 2
    assert result["accuracy"] == .5


def test_pairing_uses_ids_and_clusters():
    a = frame([True, True, True, True])
    b = frame([False, False, False, False]).iloc[::-1]
    result = pairwise(a, b, draws=50)
    assert result["accuracy_difference"] == 1
    assert result["filer_cluster_bootstrap_95"] == [1, 1]
    assert result["mcnemar_exact_p"] == pytest.approx(.125)
