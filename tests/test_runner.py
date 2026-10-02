import builtins
import json
from pathlib import Path
import pandas as pd
import pytest
import yaml
from benchmark.config import read_yaml
from benchmark.runner import run, check_small_gate
from benchmark.reporting import report
from benchmark.sampling import samples
from tests.fixtures.fake_runtime import FakeRuntime
from tests.fixtures.toy_case import prepare, load_records


@pytest.fixture
def experiment(tmp_path):
    config = read_yaml("tests/fixtures/experiment.yaml")
    case_config = tmp_path / "case.yaml"
    case_config.write_text(yaml.safe_dump({"processed_dir": str(tmp_path / "data"), "description": "Synthetic fixture."}))
    config["case_config"] = str(case_config)
    prepare(read_yaml(case_config))
    return config


def test_generic_runner_persists_and_regenerates(experiment, tmp_path, monkeypatch):
    original = builtins.__import__
    def guard(name, *args, **kwargs):
        assert not name.startswith("cases.sec_lines")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guard)
    path = run(experiment, budget_usd=1, results_root=tmp_path / "results", runtime_factory=FakeRuntime)
    frame = pd.read_parquet(path / "predictions.parquet")
    assert not frame.failed.any()
    assert frame.correct.all()
    assert frame.method.nunique() == 10
    assert frame.shuffled.any()
    assert set(frame.repeat_index) == {0, 1}
    before = json.loads((path / "metrics.json").read_text())
    report(path)
    assert json.loads((path / "metrics.json").read_text()) == before
    assert before["pass_rule"]["label_only"]["outcome"] == "not_evaluated"
    for method, group in frame.groupby("method"):
        assert len(group[group.shuffled]) == 4
    assert (path / "coverage-with_context.svg").exists()


def test_failure_is_kept(experiment, tmp_path):
    class Broken(FakeRuntime):
        def llm(self, *args):
            raise ValueError("Injected failure")
    path = run(experiment, budget_usd=1, results_root=tmp_path / "results", runtime_factory=Broken)
    frame = pd.read_parquet(path / "predictions.parquet")
    llm = frame[frame.method.str.contains("llm")]
    assert llm.failed.all()
    assert not llm.correct.any()
    assert len(llm) > 0


def test_smoke_is_disjoint_from_small_and_full(experiment):
    records = load_records(read_yaml(experiment["case_config"]))
    full = samples(records, experiment, "full")
    small = samples(records, experiment, "small")
    smoke = samples(records, experiment, "small", 2)
    ids = lambda group: {r.record_id for r in group}
    assert ids(small["main"]) <= ids(full["main"])
    assert not ids(smoke["main"]) & ids(full["main"])
    assert ids(small["repeat"]) <= ids(small["composite"])


def test_full_gate_rejects_fixtures(tmp_path):
    path = tmp_path / "fixture"
    path.mkdir()
    (path / "status.json").write_text(json.dumps({"profile": "small", "mode": "fixture", "complete": True, "fingerprint": "abc"}))
    with pytest.raises(ValueError, match="completed small"):
        check_small_gate(tmp_path, "abc")
