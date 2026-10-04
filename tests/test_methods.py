import pytest
from benchmark.methods.common import validate_probabilities
from benchmark.methods import chat_model, decision_model
from benchmark.config import read_yaml
from benchmark.pricing import Budget, BudgetExceeded
from tests.fixtures.fake_runtime import FakeRuntime
from tests.fixtures.toy_case import candidates


@pytest.mark.parametrize("module", [chat_model, decision_model])
def test_every_method_obeys_contract(module):
    config = {"case": "tests.fixtures.toy_case", "prompts": read_yaml("cases/sec_lines/prompts.yaml")}
    config["_runtime"] = FakeRuntime(config, {}, None)
    result = module.predict({"label": "yes", "statement": "toy"}, candidates(None, {}), {}, config)
    assert result.prediction == "yes"
    assert 0 <= result.confidence <= 1


def test_probability_validation():
    validate_probabilities({0: .33, 1: .33, 2: .33, 3: 0, 4: 0}, range(5))
    validate_probabilities({0: .34, 1: .34, 2: .33, 3: 0, 4: 0}, range(5))
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
