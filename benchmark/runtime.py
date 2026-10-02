"""Runner-owned request lifecycle: credentials, retries, timing and usage."""
import json
import os
import threading
import time
from typing import Callable

from langchain.chat_models import init_chat_model
from typesafe_sdk import RetryPolicy, TypeSafeClient

from benchmark.pricing import BudgetExceeded, cost
from benchmark.methods.common import validate_probabilities


KEYS = {"vercel": "AI_GATEWAY_API_KEY", "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY", "typesafe": "TYPESAFE_API_KEY"}


def require_key(provider):
    if provider not in KEYS:
        raise ValueError(f"Unsupported provider: {provider}")
    value = os.environ.get(KEYS[provider])
    if not value:
        raise ValueError(f"Required credential is empty: {KEYS[provider]}")
    return value


def jev_client(config):
    kwargs = {"api_key": require_key(config["provider"]), "retry": RetryPolicy(max_retries=0),
              "timeout": config.get("timeout_seconds", 120)}
    if config.get("base_url"):
        kwargs["base_url"] = config["base_url"]
    return TypeSafeClient(**kwargs)


def chat_client(config):
    provider = config["provider"]
    kwargs = {"api_key": require_key(provider), "timeout": config.get("timeout_seconds", 120),
              "max_retries": 0, "max_tokens": config.get("max_tokens", 4096)}
    if config.get("temperature") is not None:
        kwargs["temperature"] = config["temperature"]
    if config.get("reasoning_effort"):
        kwargs["reasoning_effort"] = config["reasoning_effort"]
    if provider == "vercel":
        kwargs["base_url"] = "https://ai-gateway.vercel.sh/v1"
    return init_chat_model(config["model"], model_provider="openai" if provider == "vercel" else provider, **kwargs)


class CallFailed(RuntimeError):
    pass


def retryable(error):
    # Retry transport/rate-limit/server/schema failures, never configuration or auth.
    status = getattr(error, "status_code", getattr(error, "status", None))
    if status is not None:
        return status in (408, 409, 429) or status >= 500
    name = type(error).__name__.lower()
    return isinstance(error, (ValueError, KeyError, TimeoutError, ConnectionError)) or any(
        term in name for term in ("connection", "timeout", "validation", "ratelimit", "parsing"))


class Runtime:
    def __init__(self, config, price, budget, chat=None, jev=None):
        self.config, self.price, self.budget = config, price, budget
        self.chat = chat
        self.jev_api = jev
        self.calls = []
        self.lock = threading.Lock()

    def _call(self, execute, bound):
        for attempt in range(self.config.get("attempts", 3)):
            self.budget.reserve(bound)
            start = time.perf_counter()
            entry = {"attempt": attempt + 1, "input_tokens": None, "output_tokens": None,
                     "raw": None, "cost_usd": None}
            try:
                result, raw, usage = execute()
                entry.update(usage)
                entry["raw"] = raw
                entry["cost_usd"] = cost(usage, self.price)
                entry["success"] = True
                return result
            except Exception as error:
                # Structured parsing can fail after a billable completion.
                if hasattr(error, "call_evidence"):
                    raw, usage = error.call_evidence
                    entry.update(usage)
                    entry["raw"] = raw
                    entry["cost_usd"] = cost(usage, self.price)
                entry["success"] = False
                # Provider exception messages may contain headers; retain type/status only.
                entry["error_type"] = type(error).__name__
                entry["status_code"] = getattr(error, "status_code", getattr(error, "status", None))
                if not retryable(error) or attempt == self.config.get("attempts", 3) - 1:
                    raise CallFailed(f"Provider call failed: {type(error).__name__}") from error
            finally:
                entry["latency_ms"] = (time.perf_counter() - start) * 1000
                self.budget.settle(bound, entry["cost_usd"])
                with self.lock:
                    self.calls.append(entry)
            time.sleep(min(2 ** attempt, 4))

    def llm(self, system, payload, schema):
        if self.chat is None:
            self.chat = chat_client(self.config)
        schema_bytes = len(json.dumps(schema.model_json_schema()).encode())
        input_bound = len((system + json.dumps(payload)).encode()) + schema_bytes + 2048
        bound = cost({"input_tokens": input_bound, "output_tokens": self.config.get("max_tokens", 4096)}, self.price)

        def execute():
            response = self.chat.with_structured_output(schema, include_raw=True).invoke(
                [("system", system), ("user", json.dumps(payload, sort_keys=True))])
            raw = response["raw"].model_dump(mode="json")
            usage = response["raw"].usage_metadata or {}
            evidence = (raw, {"input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
                              "usage_details": usage})
            try:
                if response.get("parsing_error") or response.get("parsed") is None:
                    raise ValueError("Structured output failed validation")
                parsed = schema.model_validate(response["parsed"])
            except Exception as error:
                error.call_evidence = evidence
                raise
            return parsed, *evidence
        return self._call(execute, bound)

    def jev(self, payload, questions):
        if self.jev_api is None:
            self.jev_api = jev_client(self.config)
        bound = cost({"input_tokens": 64000, "output_tokens": 0}, self.price)

        def execute():
            response = self.jev_api.system_one(state=payload, questions=questions, model=self.config["model"])
            raw = response.model_dump(mode="json")
            usage = response.usage.model_dump(mode="json")
            try:
                if set(response.answers) != set(questions):
                    raise ValueError("Response question set differs")
                for key, question in questions.items():
                    answer = response.answers[key]
                    if question.type == "choice":
                        validate_probabilities(answer.probabilities, question.criteria)
                        if answer.choice not in question.criteria:
                            raise ValueError("Unexpected choice")
                    else:
                        validate_probabilities(answer.probabilities, range(len(question.criteria)))
            except Exception as error:
                error.call_evidence = (raw, usage)
                raise
            return response, raw, usage
        return self._call(execute, bound)

    def evidence(self):
        calls = list(self.calls)
        known = all(c.get("input_tokens") is not None and c.get("output_tokens") is not None for c in calls)
        return {"calls": calls, "request_count": len(calls), "usage_complete": known,
                "input_tokens": sum(c["input_tokens"] for c in calls) if known else None,
                "output_tokens": sum(c["output_tokens"] for c in calls) if known else None,
                "cost_usd": sum(c["cost_usd"] for c in calls) if known else None}

    def close(self):
        if self.jev_api is not None:
            self.jev_api.close()
        if self.chat is not None:
            client = getattr(self.chat, "root_client", None)
            if client is not None and hasattr(client, "close"):
                client.close()
