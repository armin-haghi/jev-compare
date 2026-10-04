import builtins
import json
import pandas as pd
import pytest
from benchmark import datasets
from benchmark.config import read_yaml
from benchmark.metrics import write_evidence
from benchmark.pricing import BudgetExceeded
from benchmark.runner import expand_methods
from tests.fixtures.fake_runtime import FakeRuntime


def test_generic_runner_persists_and_regenerates(toy, monkeypatch):
    original = builtins.__import__
    def guard(name, *args, **kwargs):
        assert not name.startswith("cases.sec_lines")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guard)
    path = toy["run"]()
    assert path.parent.name == toy["dataset"]
    frame = pd.read_parquet(path / "predictions.parquet")
    assert not frame.failed.any() and frame.correct.all()
    assert frame.method.nunique() == 4
    assert set(frame.repeat_index) == {0, 1}
    before = json.loads((path / "evidence.json").read_text())
    assert write_evidence(path) == before
    assert before["runs"][0]["mode"] == "fixture" and before["runs"][0]["dataset"] == toy["dataset"]
    for method, group in frame.groupby("method"):
        assert len(group[group.shuffled]) == 2  # one reordered record, two input versions


def test_dataset_is_random_fixed_and_checked(toy):
    root = toy["root"] / "samples"
    assert datasets.create(toy["config"]["case"], toy["case_config"], 8, root=root) == toy["dataset"]
    folder, manifest, records = datasets.load(toy["dataset"], root)
    assert len(records) == 8 and len(manifest["asked_twice"]) == len(manifest["reordered_options"]) == 1
    assert sum(manifest["categories"].values()) == 8
    (folder / "records.parquet").write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed after it was created"):
        datasets.load(toy["dataset"], root)


def test_failure_is_kept(toy):
    class Broken(FakeRuntime):
        def llm(self, *args):
            raise ValueError("Injected failure")
    frame = pd.read_parquet(toy["run"](runtime=Broken) / "predictions.parquet")
    chat = frame[frame.method.str.startswith("chat:")]
    assert len(chat) > 0 and chat.failed.all() and not chat.correct.any()


def test_methods_follow_the_model_lists():
    config = read_yaml("tests/fixtures/experiment.yaml")
    assert [m["method"] for m in expand_methods(config)] == [
        "rules_baseline", "decision:typesafe-ai/jev", "chat:openai/gpt-5-mini", "chat:anthropic/claude-sonnet-4.6"]
    config["rules"], config["decision_models"] = False, []
    assert [m["method"] for m in expand_methods(config)] == ["chat:openai/gpt-5-mini", "chat:anthropic/claude-sonnet-4.6"]
    config["chat_models"].append({"model": "openai/gpt-5-mini"})
    with pytest.raises(ValueError, match="each model once"):
        expand_methods(config)


def test_budget_interruption_keeps_partial_evidence(toy):
    class Stopped(FakeRuntime):
        def llm(self, *args):
            raise BudgetExceeded("Injected spending stop")
    with pytest.raises(BudgetExceeded):
        toy["run"](runtime=Stopped)
    folder = next((toy["root"] / "results" / toy["dataset"]).iterdir())
    assert not json.loads((folder / "status.json").read_text())["complete"]
    rows = pd.read_parquet(folder / "predictions.parquet")
    assert rows.iloc[-1].failed
    assert json.loads(rows.iloc[-1].diagnostics_json)["error_type"] == "BudgetExceeded"
    assert not write_evidence(folder)["runs"][0]["complete"]


def test_concurrent_runner_preserves_every_output(toy):
    settings = dict(toy["config"], record_concurrency=3)
    path = toy["run"](settings)
    frame = pd.read_parquet(path / "predictions.parquet")
    journal = [json.loads(line) for line in (path / "predictions.jsonl").read_text().splitlines()]
    assert len(frame) == len(journal) == 4 * (8 * 2 + 2 + 2)
    assert not frame.duplicated(["method", "record_id", "context_regime", "repeat_index", "shuffled"]).any()
    assert frame.correct.all()


def test_concurrent_stop_keeps_inflight_usage(toy):
    import threading
    settings = dict(toy["config"], record_concurrency=2, rules=False, decision_models=[],
                    chat_models=[{"model": "openai/gpt-5-mini"}])
    barrier = threading.Barrier(2)
    class Stopped(FakeRuntime):
        def llm(self, *args):
            barrier.wait(timeout=5)
            raise BudgetExceeded("Injected spending stop")
    with pytest.raises(BudgetExceeded):
        toy["run"](settings, runtime=Stopped)
    folder = next((toy["root"] / "results" / toy["dataset"]).iterdir())
    rows = pd.read_parquet(folder / "predictions.parquet")
    assert len(rows) == 2 and rows.failed.all()
    assert not json.loads((folder / "status.json").read_text())["complete"]


def test_one_model_can_run_alone():
    from benchmark.cli import select
    config = read_yaml("tests/fixtures/experiment.yaml")
    assert [m["method"] for m in expand_methods(select(config, ["openai/gpt-5-mini"]))] == ["chat:openai/gpt-5-mini"]
    assert [m["method"] for m in expand_methods(select(config, ["rules", "typesafe-ai/jev"]))] == [
        "rules_baseline", "decision:typesafe-ai/jev"]
    with pytest.raises(ValueError, match="Not in the settings file"):
        select(config, ["google/unknown"])
