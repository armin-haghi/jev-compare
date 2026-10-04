import json
import pandas as pd
from benchmark.metrics import confidence, consistency, pair


def frame(correct, confidence=None, **extra):
    size = len(correct)
    return pd.DataFrame({"record_id": [str(i) for i in range(size)], "correct": correct,
                         "confidence": confidence or [.5] * size, "failed": False,
                         "prediction": ["a" if c else "b" for c in correct], "repeat_index": 0, "shuffled": False,
                         "source_json": [json.dumps({"cik": str(i // 2)}) for i in range(size)], **extra})


def test_confidence_cutoffs_and_calibration_gap():
    result = confidence(frame([True, True, False, False], [1, .95, .9, .1]))
    cutoffs = {p["cutoff"]: (p["answers"], p["incorrect"]) for p in result["cutoffs"]}
    assert cutoffs[.99] == (1, 0) and cutoffs[.9] == (3, 1) and cutoffs[0] == (4, 2)
    assert result["calibration_gap"] == 0 or result["calibration_gap"] > 0
    perfect = confidence(frame([True, False], [1, 0]))
    assert perfect["calibration_gap"] == 0


def test_pair_counts_record_outcomes_by_id():
    a = frame([True, True, False, False])
    b = frame([True, False, True, False]).iloc[::-1]
    assert pair(a, b) == {"records": 4, "both_correct": 1, "both_incorrect": 1,
                          "left_only_correct": 1, "right_only_correct": 1}


def test_consistency_counts_changed_answers():
    first = frame([True, True])
    again = frame([True, False]).assign(repeat_index=1)
    reordered = frame([True, True]).assign(shuffled=True)
    result = consistency(pd.concat([first, again, reordered]))
    assert result["repeats"] == {"records": 2, "failed": 0, "changed": 1}
    assert result["reorders"] == {"records": 2, "failed": 0, "changed": 0}
