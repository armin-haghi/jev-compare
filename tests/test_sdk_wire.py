"""Exercise the real pinned SDK over local HTTP transports, without credentials."""
import json
import httpx2
import httpx
from typesafe_sdk import TypeSafeClient, Choice, Score, RetryPolicy
from langchain.chat_models import init_chat_model
from pydantic import BaseModel
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


def test_langchain_gateway_uses_structured_output_and_keeps_usage():
    seen = []
    class Answer(BaseModel):
        category: str
        confidence: float
    def handle(request):
        body = json.loads(request.content)
        seen.append(body)
        return httpx.Response(200, json={
            "id": "fixture", "object": "chat.completion", "created": 0, "model": "openai/gpt-5-mini",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": '{"category":"yes","confidence":0.9}'},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 30, "completion_tokens": 8, "total_tokens": 38}})
    client = init_chat_model("openai/gpt-5-mini", model_provider="openai", api_key="fixture",
                             base_url="https://ai-gateway.vercel.sh/v1",
                             http_client=httpx.Client(transport=httpx.MockTransport(handle)), max_retries=0)
    runtime = Runtime({"max_tokens": 100}, {"input_per_million": .25, "output_per_million": 2},
                      Budget(1), chat=client)
    assert runtime.llm("Choose one", {"label": "yes"}, Answer).category == "yes"
    assert seen[0]["response_format"]["type"] == "json_schema"
    assert runtime.evidence()["input_tokens"] == 30
    assert runtime.evidence()["output_tokens"] == 8
    runtime.close()
    second = Runtime({"max_tokens": 100}, {"input_per_million": .25, "output_per_million": 2},
                     Budget(1), chat=client)
    assert second.llm("Choose one", {"label": "yes"}, Answer).category == "yes"
