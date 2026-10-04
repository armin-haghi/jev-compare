import json
import pytest
from pydantic import BaseModel
from benchmark.runtime import Runtime, CallFailed
from benchmark.pricing import Budget


class Parsed(BaseModel):
    category: str


class Reply:
    def __init__(self, status, content):
        self.status_code, self.content = status, content

    def json(self):
        return {"choices": [{"message": {"content": self.content}}], "usage": {"prompt_tokens": 12, "completion_tokens": 3}}


class Post:
    """Stands in for requests.post; the first `failures` replies are not valid JSON answers."""
    def __init__(self, failures=0, status=200):
        self.count, self.failures, self.status, self.bodies = 0, failures, status, []

    def __call__(self, url, json, headers, timeout):
        self.count += 1
        self.bodies.append(json)
        return Reply(self.status, '{"category": "yes"}' if self.count > self.failures else "not an answer")


@pytest.fixture(autouse=True)
def gateway_key(monkeypatch):
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "fixture")
    monkeypatch.setattr("benchmark.runtime.time.sleep", lambda _: None)


def runtime(post):
    return Runtime({"attempts": 3, "max_tokens": 100, "model": "openai/gpt-5-mini"},
                   {"input_per_million": 1, "output_per_million": 2}, Budget(1), post=post)


def test_retries_retain_billable_parse_failures():
    post = Post(failures=2)
    r = runtime(post)
    assert r.llm("system", {}, Parsed).category == "yes"
    evidence = r.evidence()
    assert post.count == 3
    assert evidence["input_tokens"] == 36
    assert evidence["output_tokens"] == 9
    assert evidence["cost_usd"] == pytest.approx(.000054)


def test_retries_stop_at_three():
    post = Post(failures=10)
    r = runtime(post)
    with pytest.raises(CallFailed):
        r.llm("system", {}, Parsed)
    assert post.count == 3
    assert len(r.evidence()["calls"]) == 3


def test_auth_failure_does_not_retry():
    post = Post(status=401)
    r = runtime(post)
    with pytest.raises(CallFailed) as failure:
        r.llm("system", {}, Parsed)
    assert failure.value.fatal
    assert post.count == 1
    assert r.evidence()["cost_usd"] is None


def test_request_switches_model_by_name_only():
    post = Post()
    for model in ("openai/gpt-5-mini", "anthropic/claude-sonnet-4.6", "google/gemini-2.5-flash"):
        Runtime({"model": model, "max_tokens": 100}, {"input_per_million": 1, "output_per_million": 2},
                Budget(1), post=post).llm("system", {}, Parsed)
    first, *others = post.bodies
    assert [b["model"] for b in post.bodies] == ["openai/gpt-5-mini", "anthropic/claude-sonnet-4.6", "google/gemini-2.5-flash"]
    assert all({k: v for k, v in b.items() if k != "model"} == {k: v for k, v in first.items() if k != "model"} for b in others)
    assert json.loads(first["messages"][1]["content"]) == {}
