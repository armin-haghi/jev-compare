"""Exercise the real pinned SDK over local HTTP transports, without credentials."""
import json
import httpx2
from typesafe_sdk import TypeSafeClient, Choice, Score, RetryPolicy
from benchmark.runtime import Runtime
from benchmark.pricing import Budget


def test_typesafe_gateway_preserves_native_probabilities_and_extensions():
    requests = []
    def handle(request):
        requests.append(request)
        body = json.loads(request.content)
        answers = {}
        for key, question in body["questions"].items():
            if question["type"] == "choice":
                answers[key] = {"type": "choice", "choice": "yes", "confidence": .8,
                                "probabilities": {"yes": .9, "no": .1}}
            else:
                answers[key] = {"type": "score", "score": 2.0, "confidence": .9,
                                "legend": {str(i): str(i) for i in range(5)},
                                "probabilities": {str(i): float(i == 2) for i in range(5)}}
        return httpx2.Response(200, json={"model": "typesafe-ai/jev", "answers": answers,
            "usage": {"input_tokens": 99, "output_tokens": 0}, "provider_metadata": {"gateway": {"fixture": True}}})
    client = TypeSafeClient(api_key="fixture", base_url="https://ai-gateway.vercel.sh/typesafe",
                           transport=httpx2.MockTransport(handle), retry=RetryPolicy(max_retries=0))
    runtime = Runtime({"model": "typesafe-ai/jev"}, {"input_per_million": .042, "output_per_million": 0},
                      Budget(1), jev=client)
    result = runtime.jev({"label": "yes"}, {"line": Choice(criteria={"yes": "Yes", "no": "No"}),
                                         "score": Score(criteria=[str(i) for i in range(5)])})
    assert requests[0].url.path == "/typesafe/v1/systemone"
    assert result.choices["line"].probabilities["yes"] == .9
    assert result.scores["score"].probabilities[2] == 1
    assert runtime.evidence()["calls"][0]["raw"]["provider_metadata"]["gateway"]["fixture"]
    runtime.close()


def test_gateway_request_matches_the_structured_output_format(monkeypatch):
    """The body the 2026-10-02 run sent through LangChain, now sent as a plain request."""
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "fixture")
    from typing import Literal
    from pydantic import Field, create_model
    seen = []
    class Reply:
        status_code = 200
        def json(self):
            return {"choices": [{"message": {"content": '{"category":"a","confidence":0.9}'}}],
                    "usage": {"prompt_tokens": 30, "completion_tokens": 8}}
    def post(url, json, headers, timeout):
        seen.append((url, json, headers, timeout))
        return Reply()
    schema = create_model("DirectChoice", __config__={"extra": "forbid"}, category=(Literal[("a", "b")], ...),
                          confidence=(float, Field(ge=0, le=1, allow_inf_nan=False)))
    runtime = Runtime({"model": "openai/gpt-5-mini", "max_tokens": 1024, "reasoning_effort": "minimal", "temperature": None},
                      {"input_per_million": .25, "output_per_million": 2}, Budget(1), post=post)
    assert runtime.llm("S", {"u": 1}, schema).category == "a"
    url, body, headers, timeout = seen[0]
    assert url == "https://ai-gateway.vercel.sh/v1/chat/completions"
    assert headers == {"Authorization": "Bearer fixture"} and timeout == 120
    assert body == {"model": "openai/gpt-5-mini", "max_completion_tokens": 1024, "reasoning_effort": "minimal",
                    "messages": [{"role": "system", "content": "S"}, {"role": "user", "content": '{"u": 1}'}],
                    "response_format": {"type": "json_schema", "json_schema": {
                        "name": "DirectChoice", "strict": True, "schema": {
                            "additionalProperties": False, "required": ["category", "confidence"], "title": "DirectChoice",
                            "type": "object", "properties": {
                                "category": {"enum": ["a", "b"], "title": "Category", "type": "string"},
                                "confidence": {"maximum": 1, "minimum": 0, "title": "Confidence", "type": "number"}}}}}}
    assert runtime.evidence()["input_tokens"] == 30 and runtime.evidence()["output_tokens"] == 8
