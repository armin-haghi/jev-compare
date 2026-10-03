import builtins
import json
from pathlib import Path
import pandas as pd
import pytest
import yaml
from benchmark.config import file_hash, read_yaml
from benchmark.runner import run, check_small_gate, expand_methods
from benchmark.reporting import report, publish_report
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
    assert (path / "factsheet.md").exists()
    assert (path / "evidence.json").exists()
    assert not (path / "details.md").exists()


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


def test_verdict_and_total_cost_lead_the_automatic_factsheet(experiment, tmp_path, capsys):
    from benchmark.summary import print_summary
    path = run(experiment, budget_usd=1, results_root=tmp_path / "results", runtime_factory=FakeRuntime)
    evidence_hash = file_hash(path / "predictions.parquet")
    verdict = json.loads((path / "verdict.json").read_text())
    assert verdict["headline"] == "The fixture verifies execution"
    assert verdict["predictions_sha256"] == evidence_hash
    factsheet = (path / "factsheet.md").read_text()
    assert factsheet.startswith("# The fixture verifies execution")
    assert factsheet.index("Total run cost") < factsheet.index("The test covers 4 records")
    assert json.loads((path / "management_summary.json").read_text())["tested_dataset"]["category_counts"] == {"no": 2, "yes": 2}
    (path / "verdict.json").write_text('{"headline": "stale interpretation"}')
    report(path)
    assert json.loads((path / "management_summary.json").read_text())["verdict"] == verdict
    assert file_hash(path / "predictions.parquet") == evidence_hash
    print_summary(path)
    output = capsys.readouterr().out
    assert "Dataset: 4/4 records, 2 categories" in output
    assert "These results do not measure model quality." in output
    assert 'Task:' in output and 'Recommendation:' in output
    assert output.index('Total run cost') < output.index('Dataset:')
    assert 'Original brief criterion' not in output
    assert 'does not support a deployment recommendation' in output


def test_shared_report_preserves_local_evidence_and_scope(experiment, tmp_path):
    import hashlib
    path = run(experiment, budget_usd=1, results_root=tmp_path / 'results', runtime_factory=FakeRuntime)
    destination = tmp_path / 'shared'
    destination.mkdir()
    (destination / 'evidence.json').write_text('{"run_id":"old", "cost_ledger":"stale"}')
    frozen_files = ['predictions.parquet', 'metrics.json', 'freeze.json', 'resolved_config.yaml']
    hashes = {name: file_hash(path / name) for name in frozen_files}
    output = publish_report(path, destination)
    text = output.read_text()
    snapshot = json.loads((destination / 'evidence.json').read_text())
    assert {p.name for p in destination.iterdir()} == {'factsheet.md', 'evidence.json'}
    assert snapshot['analysis'] == json.loads((path / 'analysis.json').read_text())
    assert snapshot['source_artifact_hashes']['predictions.parquet'] == hashes['predictions.parquet']
    assert 'cost_ledger' not in snapshot
    assert text.startswith('# The fixture verifies execution')
    assert 'does not support a deployment recommendation' in text
    assert text.index('Total run cost') < text.index('The test covers 4 records')
    assert '](evidence.json)' in text
    assert 'main/docs/methodology.md)' in text
    methodology = snapshot['methodology']['text']
    assert 'Direct models versus programmed rules' in methodology
    assert snapshot['methodology']['sha256'] == hashlib.sha256(methodology.encode()).hexdigest()
    assert 'Scores use a five-level scale' not in text
    assert 'does a model improve coverage' not in text
    snapshot['cost_ledger'] = [{'run_id': path.name, 'note': 'Retain audit entries on regeneration'}]
    (destination / 'evidence.json').write_text(json.dumps(snapshot))
    (path / 'methodology.md').write_text(methodology + '\nArchived documentation version.\n')
    report(path)
    publish_report(path, destination)
    updated = json.loads((destination / 'evidence.json').read_text())
    assert updated['cost_ledger'] == snapshot['cost_ledger']
    assert updated['methodology']['text'].endswith('Archived documentation version.\n')
    assert updated['methodology']['sha256'] == file_hash(path / 'methodology.md')
    assert {name: file_hash(path / name) for name in frozen_files} == hashes


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


def test_small_only_configuration_omits_frontier():
    config = read_yaml("tests/fixtures/experiment.yaml")
    config["llm_tiers"] = ["small"]
    methods = expand_methods(config)
    assert len(methods) == 7
    assert not any(m.get("tier") == "frontier" for m in methods)
    assert sum(m.get("tier") == "small" for m in methods) == 3


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
    assert not status["mechanism_verified"]
    rows = pd.read_parquet(folder / "predictions.parquet")
    assert rows.iloc[-1].failed
    assert json.loads(rows.iloc[-1].diagnostics_json)["error_type"] == "BudgetExceeded"
    report(folder)
    assert json.loads((folder / "metrics.json").read_text())["pass_rule"]["label_only"]["outcome"] == "not_evaluated"


def test_concurrent_runner_preserves_every_output(experiment, tmp_path):
    experiment['record_concurrency'] = 3
    path = run(experiment, budget_usd=1, results_root=tmp_path / 'results', runtime_factory=FakeRuntime)
    frame = pd.read_parquet(path / 'predictions.parquet')
    journal = [json.loads(line) for line in (path / 'predictions.jsonl').read_text().splitlines()]
    assert len(frame) == len(journal) == 160
    assert not frame.duplicated(['method', 'record_id', 'context_regime', 'repeat_index', 'shuffled']).any()
    assert frame.correct.all()
    assert json.loads((path / 'status.json').read_text())['mechanism_verified']


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
