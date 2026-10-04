import json
import pytest
from benchmark import datasets
from benchmark.cli import run_folders
from benchmark.config import file_hash
from benchmark.report import publish


def test_publish_fills_only_generated_blocks(toy):
    folder, destination = toy["run"](), toy["root"] / "study"
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


def test_unknown_block_is_rejected(toy):
    folder = toy["run"]()
    (toy["root"] / "doc.md").write_text("<!-- begin nonsense -->\n<!-- end -->\n")
    with pytest.raises(ValueError, match="Unknown generated block"):
        publish(folder, toy["root"])


def test_a_later_run_on_the_same_dataset_adds_a_model(toy):
    config = dict(toy["config"], chat_models=[{"model": "openai/gpt-5-mini"}])
    first = toy["run"](config, run_id="first")
    added = dict(config, rules=False, decision_models=[], chat_models=[{"model": "anthropic/claude-sonnet-4.6"}])
    later = toy["run"](added, run_id="later")
    assert run_folders(toy["root"] / "results", toy["dataset"]) == [first, later]
    evidence = publish([first, later], toy["root"] / "study")
    assert evidence["regimes"]["with_context"]["models"] == [
        "decision:typesafe-ai/jev", "chat:anthropic/claude-sonnet-4.6", "chat:openai/gpt-5-mini"]
    assert [r["id"] for r in evidence["runs"]] == ["first", "later"]
    again = toy["run"](added, run_id="again")
    with pytest.raises(ValueError, match="appears in both"):
        publish([first, later, again], toy["root"] / "study")
    smaller = datasets.create(config["case"], toy["case_config"], 6, root=toy["root"] / "samples")
    other = toy["run"](added, dataset_id=smaller, run_id="other")
    with pytest.raises(ValueError, match="tested different records"):
        publish([first, other], toy["root"] / "study")
