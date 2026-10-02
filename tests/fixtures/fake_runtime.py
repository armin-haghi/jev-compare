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
        if "category" in schema.model_fields:
            return schema(category=label, confidence=.9)
        if "score" in schema.model_fields:
            return schema(score=4 if f"candidate {label}," in payload["question"] else 0)
        return schema(**{key: {"wording": 4 if key == label else 0, "position": 2} for key in schema.model_fields})

    def jev(self, payload, questions):
        self.count += 1
        label = payload["record"]["label"]
        answers = {}
        for key, question in questions.items():
            if question.type == "choice":
                answers[key] = SimpleNamespace(choice=label, confidence=.8,
                    probabilities={c: .9 if c == label else .1 for c in question.criteria})
            else:
                level = 4 if f"candidate {label}," in question.instructions else 0
                answers[key] = SimpleNamespace(score=float(level), probabilities={i: float(i == level) for i in range(5)})
        return SimpleNamespace(answers=answers, choices=answers, scores=answers)

    def evidence(self):
        usage = {"input_tokens": 100 * self.count, "output_tokens": 10 * self.count}
        return {"calls": [{"fixture": True}], "request_count": self.count, "usage_complete": True,
                **usage, "cost_usd": cost(usage, self.price)}
