"""A chat model chooses one category and states its confidence in one call."""
from typing import Literal
from pydantic import Field, create_model
from benchmark.schemas import MethodResult
from .common import state


def predict(payload, candidates, case_config, method_config):
    ids = tuple(c["id"] for c in candidates)
    schema = create_model("DirectChoice", __config__={"extra": "forbid"},
                          category=(Literal[ids], ...),
                          confidence=(float, Field(ge=0, le=1, allow_inf_nan=False)))
    result = method_config["_runtime"].llm(
        method_config["prompts"]["chat_model"]["system"], state(payload, candidates), schema)
    return MethodResult(prediction=result.category, confidence=result.confidence,
                        probability_of_prediction=result.confidence, confidence_kind="self_reported")
