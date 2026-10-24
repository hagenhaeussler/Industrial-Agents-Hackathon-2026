"""Conservative per-process limits for explicitly budgeted model calls."""

import math
import threading
from dataclasses import dataclass

# Prices are the first-party rates recorded in MASTER_PLAN §4.2.
PRICES = {
    "claude-haiku-5-5": {"input_tokens": 0.10, "output_tokens": 0.50, "cache_read_input_tokens": 0.01, "cache_creation_input_tokens": 0.125},
    "claude-sonnet-5-5": {"input_tokens": 2.0, "output_tokens": 10.0, "cache_read_input_tokens": 0.20, "cache_creation_input_tokens": 2.50},
}


class BudgetExceeded(ValueError):
    pass


def cost(model: str, usage: dict[str, int]) -> float:
    return sum(usage.get(key, 0) * price / 1_000_000 for key, price in PRICES[model].items())


def usage_counts(usage: object) -> dict[str, int]:
    return {key: getattr(usage, key, 0) or 0 for key in PRICES["claude-sonnet-5-5"]}


@dataclass(frozen=True)
class RequestSize:
    model: str
    input_bytes: int
    max_output_tokens: int


class Budget:
    def __init__(self, dollars: float):
        if not math.isfinite(dollars) or dollars <= 0:
            raise ValueError("A paid run budget must be a positive finite dollar amount.")
        self.limit = dollars
        self.spent = 0.0
        self.lock = threading.Lock()

    def reserve(self, request: RequestSize) -> float:
        prices = PRICES[request.model]
        # UTF-8 byte length bounds input tokens. Charge cache writes at the higher rate.
        amount = (request.input_bytes * prices["cache_creation_input_tokens"] + request.max_output_tokens * prices["output_tokens"]) / 1_000_000
        with self.lock:
            if self.spent + amount > self.limit:
                raise BudgetExceeded("The remaining run budget is too small for another model request.")
            self.spent += amount
        return amount

    def settle(self, reserved: float, actual: float) -> None:
        with self.lock:
            self.spent += actual - reserved
