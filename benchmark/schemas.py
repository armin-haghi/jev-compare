"""Case-independent contracts. Provenance never travels to methods."""
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class BenchmarkRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record_id: str
    case_id: str
    source: dict
    input: dict
    reference: str
    groups: dict[str, str]


class MethodResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prediction: str
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    confidence_kind: str
    probability_of_prediction: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    diagnostics: dict[str, Any] = Field(default_factory=dict)

