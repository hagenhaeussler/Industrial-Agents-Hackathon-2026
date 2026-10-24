"""Durable state checks, including independent objects sharing one SQLite file."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from agent.budget import BudgetExceeded, PersistentBudget, RequestSize
from agent.state import AgentState, HISTORY_BYTES
from server.errors import ServiceError
from server.state import StateStore


def reopen(state):
    restored = AgentState(StateStore(state.store.directory))
    restored.initialize()
    return restored


def test_budget_reservations_survive_restart_and_settle(agent_state):
    budget = PersistentBudget(agent_state, ('approved-run', 1))
    reserved = budget.reserve(RequestSize('claude-sonnet-5-5', 1000, 4096))
    restarted = PersistentBudget(reopen(agent_state), ('approved-run', 1))
    assert restarted.spent == pytest.approx(reserved)
    restarted.settle(reserved, .002)
    assert budget.spent == pytest.approx(.002)


def test_budget_limit_cannot_change_under_same_allocation(agent_state):
    PersistentBudget(agent_state, ('run', 1))
    with pytest.raises(ValueError, match='different limit'):
        PersistentBudget(reopen(agent_state), ('run', 2))


def test_concurrent_budget_accounts_cannot_reserve_past_limit(agent_state):
    request = RequestSize('claude-sonnet-5-5', 1000, 4096)
    accounts = [PersistentBudget(reopen(agent_state), ('shared', .06)) for _ in range(4)]

    def reserve(account):
        try:
            account.reserve(request)
            return True
        except BudgetExceeded:
            return False

    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(reserve, accounts))
    assert sum(outcomes) == 1
    assert accounts[0].spent <= accounts[0].limit


def test_preview_confirmation_survives_new_database_connection(agent_state):
    preview = agent_state.begin('session', 'Close the lift', 'text')
    agent_state.remember_proposal(preview, 'proposal')
    restored = reopen(agent_state)
    confirmation = restored.begin('session', 'yes', 'voice')
    assert restored.require_current('session', confirmation.turn_id).authorized_proposal == 'proposal'
    with pytest.raises(ServiceError, match='superseded'):
        agent_state.require_current('session', preview.turn_id)


def test_new_preview_needs_its_own_confirmation(agent_state):
    first = agent_state.begin('session', 'Close lift', 'text')
    agent_state.remember_proposal(first, 'old-proposal')
    confirmation = agent_state.begin('session', 'yes', 'voice')
    agent_state.remember_proposal(confirmation, 'new-proposal')
    assert agent_state.require_current('session', confirmation.turn_id).authorized_proposal is None


def test_history_keeps_whole_tool_pairs(agent_state):
    first = agent_state.begin('session', 'Find the printer', 'text')
    messages = [
        {'role': 'user', 'content': 'Find the printer'},
        {'role': 'assistant', 'content': [{'type': 'tool_use', 'id': 'lookup', 'name': 'find', 'input': {'query': 'printer'}}]},
        {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': 'lookup', 'content': '{"ok":true}'}]},
        {'role': 'assistant', 'content': 'The printer is downstairs.'},
    ]
    agent_state.save_messages(first.turn_id, messages)
    next_turn = reopen(agent_state).begin('session', 'Which floor?', 'text')
    assert agent_state.history(next_turn) == messages


def test_oversized_history_uses_whole_observations(agent_state):
    first = agent_state.begin('session', 'Find printers', 'voice')
    agent_state.record_observation(first, {'ok': True, 'total': 107})
    agent_state.save_messages(first.turn_id, [{'role': 'user', 'content': 'x' * HISTORY_BYTES}])
    next_turn = agent_state.begin('session', 'How many?', 'text')
    history = agent_state.history(next_turn)
    assert history[0]['content'] == 'Find printers'
    assert '107' in history[1]['content']
    assert len(str(history)) < HISTORY_BYTES
