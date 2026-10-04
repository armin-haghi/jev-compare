import builtins
import json
import pandas as pd
import pytest
import yaml
from benchmark.config import file_hash, read_yaml
from benchmark.runner import run, expand_methods
from benchmark.metrics import write_evidence
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
    assert frame.method.nunique() == 4
    assert frame.shuffled.any()
    assert set(frame.repeat_index) == {0, 1}
    before = json.loads((path / "evidence.json").read_text())
    assert write_evidence(path) == before
    assert before["run"]["mode"] == "fixture"
    for method, group in frame.groupby("method"):
        assert len(group[group.shuffled]) == 4


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
    assert ids(small["repeat"]) <= ids(small["main"])


def test_small_only_configuration_omits_frontier():
    config = read_yaml("tests/fixtures/experiment.yaml")
    config["llm_tiers"] = ["small"]
    methods = expand_methods(config)
    assert len(methods) == 3
    assert not any(m.get("tier") == "frontier" for m in methods)
    assert sum(m.get("tier") == "small" for m in methods) == 1


def test_frontier_requires_explicit_authorization(experiment, tmp_path):
    with pytest.raises(ValueError, match="Frontier inference requires explicit authorization"):
        run(experiment, budget_usd=1, results_root=tmp_path / "results")


def test_budget_interruption_keeps_partial_evidence(experiment, tmp_path):
    from benchmark.pricing import BudgetExceeded
    class Stopped(FakeRuntime):
        def llm(self, *args):
            raise BudgetExceeded("Injected spending stop")
    with pytest.raises(BudgetExceeded):
        run(experiment, budget_usd=1, results_root=tmp_path / "results", runtime_factory=Stopped)
    folder = next((tmp_path / "results").iterdir())
    status = json.loads((folder / "status.json").read_text())
    assert not status["complete"]
    rows = pd.read_parquet(folder / "predictions.parquet")
    assert rows.iloc[-1].failed
    assert json.loads(rows.iloc[-1].diagnostics_json)["error_type"] == "BudgetExceeded"
    assert not write_evidence(folder)["run"]["complete"]


def test_concurrent_runner_preserves_every_output(experiment, tmp_path):
    experiment['record_concurrency'] = 3
    path = run(experiment, budget_usd=1, results_root=tmp_path / 'results', runtime_factory=FakeRuntime)
    frame = pd.read_parquet(path / 'predictions.parquet')
    journal = [json.loads(line) for line in (path / 'predictions.jsonl').read_text().splitlines()]
    assert len(frame) == len(journal) == 64
    assert not frame.duplicated(['method', 'record_id', 'context_regime', 'repeat_index', 'shuffled']).any()
    assert frame.correct.all()


def test_concurrent_stop_keeps_inflight_usage(experiment, tmp_path):
    from benchmark.pricing import BudgetExceeded
    import threading
    experiment['record_concurrency'] = 2
    experiment['methods'] = ['direct_llm']
    experiment['llm_tiers'] = ['small']
    barrier = threading.Barrier(2)
    class Stopped(FakeRuntime):
        def llm(self, *args):
            barrier.wait(timeout=5)
            raise BudgetExceeded('Injected spending stop')
    with pytest.raises(BudgetExceeded):
        run(experiment, budget_usd=1, results_root=tmp_path / 'results', runtime_factory=Stopped)
    folder = next((tmp_path / 'results').iterdir())
    rows = pd.read_parquet(folder / 'predictions.parquet')
    assert len(rows) == 2
    assert rows.failed.all()
    assert not json.loads((folder / 'status.json').read_text())['complete']
