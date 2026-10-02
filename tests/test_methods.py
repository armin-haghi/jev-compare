import pytest
from benchmark.methods.common import combine, validate_probabilities
from benchmark.methods import direct_llm, decomposed_llm, jev_direct, jev_composite
from benchmark.config import read_yaml
from benchmark.pricing import Budget, BudgetExceeded
from tests.fixtures.fake_runtime import FakeRuntime
from tests.fixtures.toy_case import candidates, load_records, prepare


def test_composite_ties_use_template_order():
    offered = [{"id": "b", "template_order": 1}, {"id": "a", "template_order": 0}]
    scores = {"a": 2, "b": 2}
    result = combine(offered, scores, scores, scores)
    assert result.prediction == "a"
    assert result.confidence == 0
    assert set(result.diagnostics["ties"]) == {"a", "b"}


@pytest.mark.parametrize("module,strategy", [(direct_llm, "direct"), (decomposed_llm, "matrix"),
    (decomposed_llm, "parallel"), (jev_direct, "direct"), (jev_composite, "concurrent"), (jev_composite, "fanout")])
def test_every_method_obeys_contract(module, strategy):
    config = {"case": "tests.fixtures.toy_case", "prompts": read_yaml("cases/sec_lines/prompts.yaml"),
              "strategy": strategy, "question_concurrency": 2}
    config["_runtime"] = FakeRuntime(config, {}, None)
    result = module.predict({"label": "yes", "statement": "toy"}, candidates(None, {}), {}, config)
    assert result.prediction == "yes"
    assert 0 <= result.confidence <= 1


def test_probability_validation():
    with pytest.raises(ValueError):
        validate_probabilities({"a": .9, "b": .9}, ["a", "b"])
    with pytest.raises(ValueError):
        validate_probabilities({"a": float("nan"), "b": 0}, ["a", "b"])


def test_budget_reserves_concurrent_requests():
    budget = Budget(1)
    budget.reserve(.6)
    with pytest.raises(BudgetExceeded):
        budget.reserve(.5)
    budget.settle(.6, .1)
    budget.reserve(.8)
    budget.settle(.8, None)
    assert budget.spent == pytest.approx(.9)
