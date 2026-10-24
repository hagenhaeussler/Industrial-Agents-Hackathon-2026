"""A completed HTTP chat turn retains its answer and tool display at the budget edge."""

import json

import anthropic
import httpx2
import pytest
from fastapi.testclient import TestClient

from agent.budget import Budget, BudgetExceeded
from agent.chat import ChatAgent, MODEL
from server.app import create_app
from server.config import Settings


@pytest.mark.parametrize('tool_first', [False, True])
def test_completed_chat_turn_survives_budget_boundary(tmp_path, tool_first):
    requests = []
    expected_requests = 2 if tool_first else 1

    class RequestBudget(Budget):
        def __init__(self):
            super().__init__(1)
            self.reservations = 0

        def reserve(self, request):
            self.reservations += 1
            if self.reservations > expected_requests:
                raise BudgetExceeded('No budget remains after the completed answer.')
            return super().reserve(request)

    def respond(request):
        requests.append(json.loads(request.content))
        content = ([{'type': 'tool_use', 'id': 'find-one', 'name': 'find', 'input': {'query': 'CNC mill H-A1-A'}}]
                   if tool_first and len(requests) == 1 else [{'type': 'text', 'text': 'Which item do you need?'}])
        return httpx2.Response(200, json={'id': f'msg-{len(requests)}', 'type': 'message', 'role': 'assistant',
            'model': MODEL, 'content': content, 'stop_reason': 'tool_use' if content[0]['type'] == 'tool_use' else 'end_turn',
            'stop_sequence': None, 'usage': {'input_tokens': 100, 'output_tokens': 10}})

    settings = Settings(state_dir=tmp_path / 'state', static_dir=tmp_path / 'web')
    with TestClient(create_app(settings)) as client, httpx2.Client(transport=httpx2.MockTransport(respond)) as transport:
        session = client.post('/api/sessions', json={'building_id': 'proc-factory-dev-003', 'role': 'navigator'}).json()
        sdk = anthropic.Anthropic(api_key='offline-test-only', max_retries=0, http_client=transport)
        agent = ChatAgent(client.app.state.agent_execution, client=sdk)
        agent.budget = RequestBudget()
        client.app.state.chat_agent = agent
        response = client.post('/api/chat', json={'session_id': session['session_id'], 'message': 'Find an item'})
        body = response.json()
        assert response.status_code == 200
        assert len(requests) == agent.budget.reservations == expected_requests
        assert body['reply'] == 'Which item do you need?'
        assert body['status'] == 'completed'
        if tool_first:
            assert body['display']['kind'] == 'highlight'
