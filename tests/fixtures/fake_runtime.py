"""Deterministic local protocol fixture. Never presented as model evidence."""
from types import SimpleNamespace
from benchmark.pricing import cost


class FakeRuntime:
    def __init__(self, config, price, budget):
        self.config, self.price = config, price
        self.count = 0

    def llm(self, system, payload, schema):
        self.count += 1
        label = payload["record"]["label"]
        return schema(category=label, confidence=.9)

    def jev(self, payload, questions):
        self.count += 1
        label = payload["record"]["label"]
        answers = {}
        for key, question in questions.items():
            answers[key] = SimpleNamespace(choice=label, confidence=.8,
                probabilities={c: .9 if c == label else .1 for c in question.criteria})
        return SimpleNamespace(answers=answers, choices=answers)

    def evidence(self):
        usage = {"input_tokens": 100 * self.count, "output_tokens": 10 * self.count}
        return {"calls": [{"fixture": True}], "request_count": self.count, "usage_complete": True,
                **usage, "cost_usd": cost(usage, self.price)}
