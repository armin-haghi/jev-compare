import json
import pytest
import yaml
from benchmark.config import file_hash, read_yaml
from benchmark.report import publish
from benchmark.runner import run
from tests.fixtures.fake_runtime import FakeRuntime
from tests.fixtures.toy_case import prepare


@pytest.fixture
def folder(tmp_path):
    config = read_yaml("tests/fixtures/experiment.yaml")
    case_config = tmp_path / "case.yaml"
    case_config.write_text(yaml.safe_dump({"processed_dir": str(tmp_path / "data")}))
    config["case_config"] = str(case_config)
    prepare(read_yaml(case_config))
    return run(config, budget_usd=1, results_root=tmp_path / "results", runtime_factory=FakeRuntime)


def test_publish_fills_only_generated_blocks(folder, tmp_path):
    destination = tmp_path / "study"
    destination.mkdir()
    text = ("# Written by hand\n\nKeep this sentence.\n\n<!-- begin results -->\nstale\n<!-- end -->\n\n"
            "<!-- begin pairs label_only -->\n<!-- end -->\n\n<!-- begin chart-cutoffs -->\n<!-- end -->\n")
    (destination / "report.md").write_text(text)
    hashes = file_hash(folder / "predictions.parquet")
    evidence = publish(folder, destination)
    rendered = (destination / "report.md").read_text()
    assert rendered.startswith("# Written by hand\n\nKeep this sentence.")
    assert "stale" not in rendered and "| Model | Correct |" in rendered
    assert "Jev and GPT-5 mini" in rendered
    assert (destination / "charts" / "confidence-cutoffs.svg").read_text().startswith("<svg")
    assert set(evidence["tables"]) == {"results", "pairs label_only"}
    assert json.loads((destination / "evidence.json").read_text())["tables"]["results"]["rows"]
    publish(folder, destination)
    assert (destination / "report.md").read_text() == rendered
    assert file_hash(folder / "predictions.parquet") == hashes
    assert {p.name for p in destination.iterdir()} == {"report.md", "charts", "evidence.json"}


def test_unknown_block_is_rejected(folder, tmp_path):
    (tmp_path / "doc.md").write_text("<!-- begin nonsense -->\n<!-- end -->\n")
    with pytest.raises(ValueError, match="Unknown generated block"):
        publish(folder, tmp_path)


def test_a_later_run_can_add_a_model(tmp_path):
    config = read_yaml("tests/fixtures/experiment.yaml")
    case_config = tmp_path / "case.yaml"
    case_config.write_text(yaml.safe_dump({"processed_dir": str(tmp_path / "data")}))
    config["case_config"] = str(case_config)
    prepare(read_yaml(case_config))
    config["chat_models"] = [{"model": "openai/gpt-5-mini"}]
    first = run(config, budget_usd=1, results_root=tmp_path / "results", runtime_factory=FakeRuntime, run_id="first")
    added = dict(config, rules=False, decision_models=[], chat_models=[{"model": "anthropic/claude-sonnet-4.6"}])
    later = run(added, budget_usd=1, results_root=tmp_path / "results", runtime_factory=FakeRuntime, run_id="later")
    evidence = publish([first, later], tmp_path / "study")
    assert evidence["regimes"]["with_context"]["models"] == [
        "decision:typesafe-ai/jev", "chat:anthropic/claude-sonnet-4.6", "chat:openai/gpt-5-mini"]
    assert [r["id"] for r in evidence["runs"]] == ["first", "later"]
    again = run(added, budget_usd=1, results_root=tmp_path / "results", runtime_factory=FakeRuntime, run_id="again")
    with pytest.raises(ValueError, match="appears in both"):
        publish([first, later, again], tmp_path / "study")
    other = run(added, "full", budget_usd=1, results_root=tmp_path / "results", runtime_factory=FakeRuntime, run_id="other")
    with pytest.raises(ValueError, match="tested different records"):
        publish([first, other], tmp_path / "study")
