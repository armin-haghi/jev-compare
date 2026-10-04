"""Runner-owned request lifecycle: credentials, retries, timing and usage."""
import json
import os
import threading
import time

import requests
from typesafe_sdk import RetryPolicy, TypeSafeClient

from benchmark.pricing import cost
from benchmark.methods.common import validate_probabilities


KEYS = {"vercel": "AI_GATEWAY_API_KEY"}
GATEWAY = "https://ai-gateway.vercel.sh/v1"
SYSTEM_ONE = "https://ai-gateway.vercel.sh/typesafe"  # decision models such as Jev


def require_key(provider):
    if provider not in KEYS:
        raise ValueError(f"Unsupported provider: {provider}")
    value = os.environ.get(KEYS[provider])
    if not value:
        raise ValueError(f"Required credential is empty: {KEYS[provider]}")
    return value


def jev_client(config):
    return TypeSafeClient(api_key=require_key("vercel"), base_url=SYSTEM_ONE, retry=RetryPolicy(max_retries=0),
                          timeout=config.get("timeout_seconds", 120))


class GatewayError(RuntimeError):
    """An HTTP error status from the gateway; the status decides whether to retry."""
    def __init__(self, status_code):
        super().__init__(f"Gateway returned HTTP {status_code}")
        self.status_code = status_code


class CallFailed(RuntimeError):
    def __init__(self, message, fatal=False):
        super().__init__(message)
        self.fatal = fatal


def retryable(error):
    # Retry transport/rate-limit/server/schema failures, never configuration or auth.
    status = getattr(error, "status_code", getattr(error, "status", None))
    if status is not None:
        return status in (408, 409, 429) or status >= 500
    name = type(error).__name__.lower()
    return isinstance(error, (ValueError, KeyError, TimeoutError, ConnectionError)) or any(
        term in name for term in ("connection", "timeout", "validation", "ratelimit", "parsing"))


class Runtime:
    def __init__(self, config, price, budget, post=requests.post, jev=None):
        self.config, self.price, self.budget = config, price, budget
        self.post = post
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
                    raise CallFailed(f"Provider call failed: {type(error).__name__}", fatal=not retryable(error)) from error
            finally:
                entry["latency_ms"] = (time.perf_counter() - start) * 1000
                self.budget.settle(bound, entry["cost_usd"])
                with self.lock:
                    self.calls.append(entry)
            time.sleep(min(2 ** attempt, 4))

    def llm(self, system, payload, schema):
        """One chat completion through the Vercel AI Gateway; any gateway model works by name."""
        key = require_key("vercel")
        schema_bytes = len(json.dumps(schema.model_json_schema()).encode())
        input_bound = len((system + json.dumps(payload)).encode()) + schema_bytes + 2048
        bound = cost({"input_tokens": input_bound, "output_tokens": self.config.get("max_tokens", 4096)}, self.price)
        request = {"model": self.config["model"], "max_completion_tokens": self.config.get("max_tokens", 4096),
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": json.dumps(payload, sort_keys=True)}],
                   "response_format": {"type": "json_schema", "json_schema": {
                       "name": schema.__name__, "schema": schema.model_json_schema(), "strict": True}}}
        request |= {key: self.config[key] for key in ("temperature", "reasoning_effort") if self.config.get(key) is not None}

        def execute():
            response = self.post(f"{GATEWAY}/chat/completions", json=request, timeout=self.config.get("timeout_seconds", 120),
                                 headers={"Authorization": f"Bearer {key}"})
            if response.status_code >= 400:
                raise GatewayError(response.status_code)
            body = response.json()
            usage = body.get("usage") or {}
            evidence = (body, {"input_tokens": usage.get("prompt_tokens"), "output_tokens": usage.get("completion_tokens")})
            try:
                parsed = schema.model_validate_json(body["choices"][0]["message"]["content"] or "")
            except Exception as error:
                error.call_evidence = evidence
                raise
            return parsed, *evidence
        return self._call(execute, bound)

    def jev(self, payload, questions):
        with self.lock:
            if self.jev_api is None:
                self.jev_api = jev_client(self.config)
        bound = cost({"input_tokens": 64000, "output_tokens": 0}, self.price)

        def execute():
            response = self.jev_api.system_one(state=payload, questions=questions,
                                              model=self.config.get("request_model", self.config["model"]))
            # The typed SDK drops provider extension fields; preserve the raw body too.
            raw = response.raw_http_response.json()
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
                "known_cost_usd": sum(c["cost_usd"] for c in calls if c["cost_usd"] is not None),
                "input_tokens": sum(c["input_tokens"] for c in calls) if known else None,
                "output_tokens": sum(c["output_tokens"] for c in calls) if known else None,
                "cost_usd": sum(c["cost_usd"] for c in calls) if known else None}

    def close(self):
        if self.jev_api is not None:
            self.jev_api.close()
