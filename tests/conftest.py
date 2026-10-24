"""Offline provider transport shared by chat and submission integration tests."""

import json

import anthropic
import httpx2
import pytest


@pytest.fixture
def model():
    clients = []

    def build(scripts):
        scripts = iter(scripts)
        requests = []

        def respond(request):
            payload = json.loads(request.content)
            requests.append(payload)
            step = next(scripts)
            if callable(step):
                step = step(payload)
            content = step.get('content')
            if content is None:
                content = [{'type': 'tool_use', 'id': f'call-{len(requests)}-{index}', 'name': name, 'input': args}
                           for index, (name, args) in enumerate(step.get('calls', []))]
                if step.get('text'):
                    content.append({'type': 'text', 'text': step['text']})
            stop = step.get('stop_reason', 'tool_use' if any(block['type'] == 'tool_use' for block in content) else 'end_turn')
            return httpx2.Response(step.get('http_status', 200), json={
                'id': f'msg-{len(requests)}', 'type': 'message', 'role': 'assistant', 'model': payload['model'],
                'content': content, 'stop_reason': stop, 'stop_sequence': None,
                'usage': {'input_tokens': 100, 'output_tokens': 10},
            })

        transport = httpx2.Client(transport=httpx2.MockTransport(respond))
        sdk = anthropic.Anthropic(api_key='offline-test-only', max_retries=0, http_client=transport)
        clients.append(sdk)
        return sdk, requests

    yield build
    for client in clients:
        client.close()
