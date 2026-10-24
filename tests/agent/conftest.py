"""Offline model transport with the real SDK and durable agent state."""

import pytest

from agent.execution import AgentExecution
from agent.state import AgentState
from server.state import StateStore


@pytest.fixture
def agent_state(tmp_path):
    store = StateStore(tmp_path / 'agent-state')
    store.initialize()
    state = AgentState(store)
    state.initialize()
    return state


@pytest.fixture
def execution_factory(agent_state):
    def build(registry, session_provider=None):
        provider = session_provider or (lambda _: {'role': 'admin', 'position': {'space_id': 'lobby'}, 'profile': 'walk', 'constraints': {}})
        return AgentExecution(registry, provider, agent_state)
    return build
