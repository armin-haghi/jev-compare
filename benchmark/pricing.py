import math
import threading
from benchmark.config import read_yaml


def lookup(prices, provider, model):
    matches = [p for p in prices if p["provider"] == provider and p["model"] == model]
    if len(matches) != 1:
        raise ValueError(f"Exactly one price required for {provider}/{model}")
    price = matches[0]
    for key in ("input_per_million", "output_per_million"):
        if not isinstance(price[key], (int, float)) or not math.isfinite(price[key]) or price[key] < 0:
            raise ValueError(f"Invalid price: {key}")
    if price["currency"] != "USD" or not price.get("source_url") or not price.get("effective_date"):
        raise ValueError("Pricing requires USD, effective date and source URL")
    return price


def cost(usage, price):
    if usage.get("input_tokens") is None or usage.get("output_tokens") is None:
        return None
    return (usage["input_tokens"] * price["input_per_million"] +
            usage["output_tokens"] * price["output_per_million"]) / 1_000_000


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    """Reserve a per-call upper bound before concurrent work starts."""
    def __init__(self, limit):
        if not math.isfinite(limit) or limit <= 0:
            raise ValueError("Budget must be a positive dollar amount")
        self.limit, self.spent, self.reserved = limit, 0.0, 0.0
        self.lock = threading.Lock()

    def reserve(self, amount):
        with self.lock:
            if self.spent + self.reserved + amount > self.limit:
                raise BudgetExceeded("Budget cannot cover the next request's conservative upper bound")
            self.reserved += amount

    def settle(self, reserved, actual):
        with self.lock:
            self.reserved -= reserved
            # Transport failures may have incurred usage; retain their full reservation.
            self.spent += reserved if actual is None else actual
