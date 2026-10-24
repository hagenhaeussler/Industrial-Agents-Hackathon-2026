"""One model configuration for interactive and submission runs."""

import os

from .budget import PRICES
from .runtime import LoopOptions

MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 4096


def configured_options() -> LoopOptions:
    options = LoopOptions(
        model=os.environ.get("TYB_AGENT_MODEL", os.environ.get("TYB_CHAT_MODEL", MODEL)),
        max_tokens=MAX_TOKENS,
        max_steps=int(os.environ.get("TYB_AGENT_MAX_STEPS", "24")),
        max_tool_calls=int(os.environ.get("TYB_AGENT_MAX_TOOL_CALLS", "128")),
        max_seconds=float(os.environ.get("TYB_AGENT_TURN_SECONDS", "90")),
    )
    if options.model not in PRICES:
        raise ValueError("The selected agent model has no configured cost rates.")
    return options
