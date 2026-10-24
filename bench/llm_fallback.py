"""Submission adapter for the product building agent."""

import anthropic

from agent.budget import Budget
from agent.config import configured_options
from agent.core import AgentRequest, BuildingAgent
from agent.prompts import PROMPT_VERSION as AGENT_PROMPT_VERSION
from agent.runtime import AgentLoop
from core.building import Building

from .agent import Prediction, unanswered
from .session import submission_session
from .submission import Submission

PROMPT_VERSION = AGENT_PROMPT_VERSION + "+submission-v1"


def interpret(building: Building, question: str, settings: tuple[Budget, object | None], *, constraints: dict | None = None) -> Prediction:
    """Run the original question through the same model, tools and policy as chat."""
    budget, supplied_client = settings
    options = configured_options()
    client = supplied_client or anthropic.Anthropic(max_retries=0)
    try:
        with submission_session(building, constraints) as (execution, session_id):
            submission = Submission(building)
            result = BuildingAgent(execution, AgentLoop(client.beta.messages, budget), options).run(
                AgentRequest(session_id, question, submission)).run
            prediction = submission.prediction or unanswered("No validated tool submission: " + result.reason + (": " + result.error if result.error else ""))
            prediction.tokens = dict(result.tokens)
            prediction.cost = result.cost
            prediction.model = options.model
            prediction.tool_calls = len(result.calls)
            return prediction
    finally:
        if supplied_client is None:
            client.close()
