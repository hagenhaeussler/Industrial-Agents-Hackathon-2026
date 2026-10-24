"""Conservative allocations for explicitly budgeted model calls."""

import math
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

# Prices are the first-party rates recorded in MASTER_PLAN §4.2.
PRICES = {
    "claude-haiku-5-5": {"input_tokens": 0.10, "output_tokens": 0.50, "cache_read_input_tokens": 0.01, "cache_creation_input_tokens": 0.125},
    "claude-sonnet-5-5": {"input_tokens": 2.0, "output_tokens": 10.0, "cache_read_input_tokens": 0.20, "cache_creation_input_tokens": 2.50},
}


class BudgetExceeded(ValueError):
    pass


@contextmanager
def paid_run_guard(path: Path, dollars: float | None):
    """An interrupted paid batch needs reconciliation before another allocation."""
    if dollars is None:
        yield
        return
    Budget(dollars)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(f"Allocated USD {dollars}. Incomplete paid batch.\n")
    except FileExistsError as error:
        raise ValueError(f"Paid run is active or was interrupted: {path}. Reconcile its spend before using a new written allocation and run name/output.") from error
    yield
    path.unlink()


def cost(model: str, usage: dict[str, int]) -> float:
    return sum(usage.get(key, 0) * price / 1_000_000 for key, price in PRICES[model].items())


def usage_counts(usage: object) -> dict[str, int]:
    return {key: getattr(usage, key, 0) or 0 for key in PRICES["claude-sonnet-5-5"]}


@dataclass(frozen=True)
class RequestSize:
    model: str
    input_bytes: int
    max_output_tokens: int


def reservation_cost(request: RequestSize) -> float:
    prices = PRICES[request.model]
    return (request.input_bytes * prices["cache_creation_input_tokens"] + request.max_output_tokens * prices["output_tokens"]) / 1_000_000


class BudgetAccount(Protocol):
    def reserve(self, request: RequestSize) -> float: ...
    def settle(self, reserved: float, actual: float) -> None: ...


class Budget:
    def __init__(self, dollars: float):
        if not math.isfinite(dollars) or dollars <= 0:
            raise ValueError("A paid run budget must be a positive finite dollar amount.")
        self.limit = dollars
        self.spent = 0.0
        self.lock = threading.Lock()

    def reserve(self, request: RequestSize) -> float:
        # UTF-8 byte length bounds input tokens. Charge cache writes at the higher rate.
        amount = reservation_cost(request)
        with self.lock:
            if self.spent + amount > self.limit:
                raise BudgetExceeded("The remaining run budget is too small for another model request.")
            self.spent += amount
        return amount

    def settle(self, reserved: float, actual: float) -> None:
        with self.lock:
            self.spent += actual - reserved


class PersistentBudget:
    """Keep an allocation and uncertain reservations across process restarts."""

    def __init__(self, state, allocation: tuple[str, float]):
        allocation_id, dollars = allocation
        Budget(dollars)
        self.state = state
        self.allocation_id = allocation_id
        self.limit = dollars
        with state.store.connect(write=True) as db:
            row = db.execute("SELECT dollar_limit FROM agent_budgets WHERE allocation_id=?", (allocation_id,)).fetchone()
            if row is not None and row[0] != dollars:
                raise ValueError("This budget allocation already has a different limit. Use its original limit or a new approved allocation ID.")
            db.execute("INSERT OR IGNORE INTO agent_budgets(allocation_id,dollar_limit) VALUES(?,?)", (allocation_id, dollars))

    def reserve(self, request: RequestSize) -> float:
        amount = reservation_cost(request)
        with self.state.store.connect(write=True) as db:
            changed = db.execute("UPDATE agent_budgets SET spent=spent+? WHERE allocation_id=? AND spent+?<=dollar_limit",
                                 (amount, self.allocation_id, amount)).rowcount
            if not changed:
                raise BudgetExceeded("The remaining run budget is too small for another model request.")
        return amount

    def settle(self, reserved: float, actual: float) -> None:
        with self.state.store.connect(write=True) as db:
            db.execute("UPDATE agent_budgets SET spent=spent+? WHERE allocation_id=?", (actual - reserved, self.allocation_id))

    @property
    def spent(self) -> float:
        with self.state.store.connect() as db:
            return db.execute("SELECT spent FROM agent_budgets WHERE allocation_id=?", (self.allocation_id,)).fetchone()[0]
