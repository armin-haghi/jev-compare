from types import SimpleNamespace
import pytest
from pydantic import BaseModel
from benchmark.runtime import Runtime, CallFailed
from benchmark.pricing import Budget


class Parsed(BaseModel):
    category: str


class Message:
    usage_metadata = {"input_tokens": 12, "output_tokens": 3}
    def model_dump(self, **kwargs):
        return {"content": "fixture completion", "usage_metadata": self.usage_metadata}


class Chat:
    def __init__(self, failures=0, error=None):
        self.count, self.failures, self.error = 0, failures, error
    def with_structured_output(self, *args, **kwargs):
        return self
    def invoke(self, messages):
        self.count += 1
        if self.error:
            raise self.error
        return {"raw": Message(), "parsed": Parsed(category="yes") if self.count > self.failures else None,
                "parsing_error": ValueError("Invalid") if self.count <= self.failures else None}


def runtime(chat):
    return Runtime({"attempts": 3, "max_tokens": 100}, {"input_per_million": 1, "output_per_million": 2},
                   Budget(1), chat=chat)


def test_retries_retain_billable_parse_failures(monkeypatch):
    monkeypatch.setattr("benchmark.runtime.time.sleep", lambda _: None)
    chat = Chat(failures=2)
    r = runtime(chat)
    assert r.llm("system", {}, Parsed).category == "yes"
    evidence = r.evidence()
    assert chat.count == 3
    assert evidence["input_tokens"] == 36
    assert evidence["output_tokens"] == 9
    assert evidence["cost_usd"] == pytest.approx(.000054)


def test_retries_stop_at_three(monkeypatch):
    monkeypatch.setattr("benchmark.runtime.time.sleep", lambda _: None)
    chat = Chat(failures=10)
    r = runtime(chat)
    with pytest.raises(CallFailed):
        r.llm("system", {}, Parsed)
    assert chat.count == 3
    assert len(r.evidence()["calls"]) == 3


def test_auth_failure_does_not_retry():
    error = RuntimeError("Do not copy secret-bearing provider exception text")
    error.status_code = 401
    chat = Chat(error=error)
    r = runtime(chat)
    with pytest.raises(CallFailed):
        r.llm("system", {}, Parsed)
    assert chat.count == 1
    assert r.evidence()["cost_usd"] is None
    assert "Do not copy" not in str(r.evidence())


def test_closed_transport_is_nonbillable_and_fatal():
    chat = Chat(error=RuntimeError("Cannot send a request, as the client has been closed."))
    r = runtime(chat)
    with pytest.raises(CallFailed) as failure:
        r.llm("system", {}, Parsed)
    assert failure.value.fatal
    assert r.evidence()["cost_usd"] == 0
    assert r.budget.spent == 0
