"""Check local G3/G4 APIs without providers or deployment.

Run `uv run python scripts/check_live_integration.py [--output report.json]`.
Starts and stops its own loopback uvicorn process and temporary SQLite state.
JSON reports API-only timing/recovery evidence; it does not certify physical
phones, rendered UI, automatic browser reconnect, QR scanning or voice/chat.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

import httpx
from websockets.sync.client import connect


parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, help='Also save the JSON report to this local path.')
args = parser.parse_args()
source = Path(__file__).resolve().parents[1]


def git(*parts):
    return subprocess.check_output(['git', '-C', str(source), *parts], text=True).strip()


expected_sha = git('rev-parse', 'HEAD')
initial_diff = subprocess.check_output(['git', '-C', str(source), 'diff', 'HEAD'])
security_paths = ['server/config.py', 'server/app.py', 'server/state.py', 'server/routes_live.py',
                  'server/ws.py', 'server/public.py', 'server/tools.py']
security_hashes = {path: hashlib.sha256((source / path).read_bytes()).hexdigest()
                   for path in security_paths if (source / path).is_file()}
url = None
state = None
report = {
    'status': 'RUNNING', 'commit': expected_sha, 'source': str(source),
    'started_at': datetime.now(timezone.utc).isoformat(),
    'source_tracked_changes': bool(initial_diff),
    'source_diff_sha256': hashlib.sha256(initial_diff).hexdigest(),
    'security_source_sha256': security_hashes,
    'verification_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'method': 'Actual uvicorn subprocess, real HTTP and WebSocket clients, isolated SQLite state, actual core and kit building data.',
    'limits': ['Local laptop only; phone is an API session, not a physical device.',
               'No rendered browser, QR scan, voice/chat provider, external deployment or camera test.',
               'Socket recovery below is an explicit client reconnect/refetch, not proof of UI automatic reconnect.'],
    'provider_calls': 0, 'external_deployments': 0, 'trials': [], 'checks': {},
    'provider_safety': {'supported_provider_keys': 'explicitly blank',
                        'dotenv_disabled': True, 'chat_budget_usd': 0,
                        'http_and_websocket_proxies_disabled': True},
}
server = None
server_log = None
environment = {key: value for key, value in os.environ.items()
               if not key.startswith(('ANTHROPIC', 'ELEVENLABS', 'OPENAI'))
               and key not in {'RAILWAY_GIT_COMMIT_SHA', 'PYTHONPATH'}}
admin_code = secrets.token_urlsafe(32)
environment.update(ANTHROPIC_API_KEY='', ELEVENLABS_API_KEY='',
                   ELEVENLABS_AGENT_ID_NAVIGATOR='', ELEVENLABS_AGENT_ID_ADMIN='',
                   OPENAI_API_KEY='', TYB_CHAT_BUDGET_USD='0',
                   PYTHON_DOTENV_DISABLED='1', DATA_DIR=str(source / 'data'),
                   PYTHONDONTWRITEBYTECODE='1', TYB_PROFILE='kit_1_1_0',
                   TYB_ADMIN_TOKEN=admin_code, TYB_ADMIN_OPEN_INSECURE='',
                   TYB_DEMO_MODE='0', TYB_ALLOW_UNAUTHENTICATED_DEMO_ADMIN='0')


def interrupted(signum, frame):
    raise KeyboardInterrupt(f'Interrupted by signal {signum}.')


signal.signal(signal.SIGTERM, interrupted)


def launch():
    return subprocess.Popen([sys.executable, '-m', 'uvicorn', 'server.app:app',
                             '--host', '127.0.0.1', '--port', str(port)],
                            cwd=source, env=environment, stdout=server_log, stderr=subprocess.STDOUT)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


try:
    with socket.socket() as bound:
        bound.bind(('127.0.0.1', 0))
        port = bound.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    state = Path(tempfile.mkdtemp(prefix='tyb-live-check-'))
    server_log = (state / 'server.log').open('w')
    environment.update(STATE_DIR=str(state / 'database'), PUBLIC_BASE_URL=url)
    server = launch()
    with httpx.Client(base_url=url, timeout=15, trust_env=False) as client:
        credentials = set()

        def check_public(payload):
            def check_keys(value):
                if isinstance(value, dict):
                    assert 'session_id' not in value, 'Public payload contains a session bearer field.'
                    for item in value.values():
                        check_keys(item)
                elif isinstance(value, (list, tuple)):
                    for item in value:
                        check_keys(item)
            check_keys(payload)
            rendered = json.dumps(payload)
            assert not any(credential in rendered for credential in credentials), 'Public payload contains a session bearer value.'

        def request(method, path, body=None, headers=None):
            response = client.request(method, path, json=body, headers=headers)
            assert response.status_code == 200, (path, response.status_code, response.text)
            payload = response.json()
            if path.startswith('/api/tours') or path.split('?')[0].endswith('/events'):
                check_public(payload)
            return payload

        def get(path): return request('GET', path)
        def post(path, body, headers=None): return request('POST', path, body, headers)
        def patch(path, body): return request('PATCH', path, body)

        def tool(sid, name, values, ok=True):
            result = post('/api/tools/' + name, {'session_id': sid, 'args': values})
            assert result['ok'] is ok, (name, result)
            check_public(result)
            return result

        def ready():
            for _ in range(100):
                if server.poll() is not None:
                    raise AssertionError('Server stopped before readiness; see server.log.')
                try:
                    health = get('/health')
                    assert health['ok'] and health['commit'] == expected_sha, health
                    return health
                except httpx.HTTPError:
                    time.sleep(.1)
            raise AssertionError('Server readiness timed out.')

        report['health'] = ready()
        bid = 'proc-factory-dev-003'
        snapshot = get('/api/buildings/' + bid)
        raw = snapshot['building']
        assert snapshot['building_version'] == 0 and len(raw['assets']) == 505
        lift = next(v for v in raw['vertical_connectors'] if v['kind'] == 'lift')
        printer = next(v for v in raw['assets'] if v['id'].endswith('A00021'))
        cnc = next(v for v in raw['assets'] if v['name'] == 'CNC mill H-A1-A')
        ups = next(v for v in raw['assets'] if v['id'].endswith('A00325'))

        def session(role='navigator', device='desk', profile='walk'):
            created = post('/api/sessions', {'building_id': bid, 'role': role,
                                            'device': device, 'profile': profile},
                           {'X-Admin-Token': admin_code} if role == 'admin' else None)
            credentials.add(created['session_id'])
            return created['session_id']

        desk = session(profile='wheelchair')
        phone = session(device='phone')
        admin_body = {'building_id': bid, 'role': 'admin', 'device': 'desk', 'profile': 'walk'}
        missing_code = client.post('/api/sessions', json=admin_body)
        wrong_code = client.post('/api/sessions', json=admin_body, headers={'X-Admin-Token': 'incorrect-admin-token'})
        assert missing_code.status_code == wrong_code.status_code == 403
        assert missing_code.json()['error']['code'] == wrong_code.json()['error']['code'] == 'forbidden'
        admin = session(role='admin')
        report['checks']['admin_auth'] = {
            'missing_header_status': missing_code.status_code, 'wrong_header_status': wrong_code.status_code,
            'authenticated_status': 200, 'navigator_status': 200,
            'ephemeral_code_configured': bool(admin_code),
            'inherited_insecure_opt_in_cleared': environment['TYB_ADMIN_OPEN_INSECURE'] == '',
            'inherited_token_replaced': environment['TYB_ADMIN_TOKEN'] != os.environ.get('TYB_ADMIN_TOKEN', ''),
        }
        patch('/api/sessions/' + desk, {'position': {'space_id': printer['space_id'], 'source': 'desk'},
              'constraints': {'step_free': True, 'min_door_width_m': .6, 'no_transit_room_types': ['toilet']}})
        found = tool(desk, 'find', {'query': cnc['name']})
        assert found['result']['id'] == cnc['id']
        plan_started = time.perf_counter()
        plan = tool(desk, 'plan_tour', {'items': ', '.join([printer['id'], cnc['id'], ups['id']]), 'keep_order': True})
        plan_ms = round((time.perf_counter() - plan_started) * 1000, 2)
        tour = plan['result']
        tid = tour['tour_id']
        tour_path = '/api/tours/' + tid
        assert len(tour['stops']) == 3 and not tour['unreachable_stops']
        assert tour.get('geometry') != 'provisional'
        assert all(leg['reachable'] for leg in tour['legs'])
        assert any(segment['kind'] == 'walk' and len(segment['points']) >= 2
                   for leg in tour['legs'] for segment in leg['segments'])
        report['checks']['three_part_api_plan'] = {
            'asset_ids': [printer['id'], cnc['id'], ups['id']], 'stops': len(tour['stops']),
            'plan_ms': plan_ms, 'geometry': tour.get('geometry', 'actual core route segments'),
            'length_m': tour['length_m'], 'exact_find_id': found['result']['id']}

        def until(ws, kind, field=None, value=None):
            for _ in range(30):
                message = json.loads(ws.recv(timeout=5))
                check_public(message)
                if message['type'] == kind and (field is None or message.get(field) == value):
                    return message
            raise AssertionError('Missing matching WebSocket message: ' + kind)

        def replan():
            position = get('/api/sessions/' + phone)['position']
            return post(tour_path + '/replan', {'session_id': phone, 'from': position,
                                              'reason': 'Local G3/G4 API acceptance recheck'})

        def check_progress(current):
            assert {s['stop_id'] for s in current['stops']} == original_ids
            assert all(next(s for s in current['stops'] if s['stop_id'] == sid)['status'] == 'collected'
                       for sid in collected)
            assert all(sid not in current['order'] for sid in collected)
            assert current['constraints']['step_free'] is True
            assert current['order_policy'] == 'fixed'

        socket_url = url.replace('http', 'ws') + '/ws/buildings/' + bid
        with connect(socket_url, open_timeout=5, proxy=None) as ws:
            assert until(ws, 'hello')['building_version'] == 0
            handoff = patch('/api/sessions/' + phone, {'active_tour_id': tid})
            assert until(ws, 'tour_opened')['tour_id'] == tid
            same_tour = get(tour_path)
            assert same_tour['stops'] == tour['stops'] and handoff['active_tour_id'] == tid
            assert handoff['position']['source'] == 'tour_start' and handoff['profile'] == 'wheelchair'
            qr = client.get('/go/' + tid)
            if qr.status_code == 200:
                assert 'text/html' in qr.headers['content-type']
            report['checks']['handoff_api'] = {'same_tour_id': tid, 'same_stops': True,
                'go_route_status': qr.status_code, 'start_confirmation_source': handoff['position']['source'],
                'wheelchair_inherited': True, 'physical_qr_scan': False}
            original_ids = {s['stop_id'] for s in tour['stops']}
            collected = tour['order'][:2]
            for sid in collected:
                tour = post(tour_path + '/progress', {'stop_id': sid, 'status': 'collected'}, {'X-Session-ID': phone})
                assert until(ws, 'tour_updated')['revision'] == tour['revision']
            pending_order = tour['order']
            assert len(pending_order) == 1
            check_progress(tour)

            for trial in range(1, 4):
                version = get('/api/buildings/' + bid)['building_version']
                preview = tool(admin, 'propose_edit', {'action': 'close', 'target': lift['id']})['result']
                stale = tool(admin, 'propose_edit', {'action': 'close', 'target': lift['id']})['result']
                started = time.perf_counter()
                commit = tool(admin, 'commit_edit', {'proposal_id': preview['proposal_id'], 'op_id': f'g34-close-{trial}'})['result']
                check_public(commit)
                committed = time.perf_counter()
                changed = until(ws, 'building_changed')
                notified = time.perf_counter()
                assert changed['event']['event_id'] == commit['event_id']
                assert changed['building_version'] == version + 1
                snap = get('/api/buildings/' + bid)
                get(tour_path)  # Recovery contract: refetch both snapshot and tour.
                assert snap['building_version'] == version + 1 and lift['id'] in snap['closed']
                blocked = replan()
                replanned = time.perf_counter()
                assert until(ws, 'tour_updated')['revision'] == blocked['revision']
                updated = time.perf_counter()
                assert blocked['status'] == 'blocked' and not blocked['order'] and blocked['unreachable_stops']
                assert all(stop.get('reason') for stop in blocked['unreachable_stops'])
                check_progress(blocked)
                blocked_route = tool(phone, 'route', {'destination': ups['id']}, ok=False)
                assert blocked_route['error']['code'] == 'no_route' and blocked_route['error']['message']
                next_step = tool(phone, 'next_step', {}, ok=False)
                assert next_step['error']['code'] == 'no_route'
                duplicate = tool(admin, 'commit_edit', {'proposal_id': preview['proposal_id'], 'op_id': f'g34-close-{trial}'})['result']
                assert duplicate == commit
                assert len(get('/api/buildings/' + bid + '/events')) == version + 1
                conflict = tool(admin, 'commit_edit', {'proposal_id': stale['proposal_id']}, ok=False)
                assert conflict['error']['code'] == 'version_conflict'
                assert get('/api/buildings/' + bid)['building_version'] == version + 1
                undo = tool(admin, 'undo', {'event_id': commit['event_id'], 'op_id': f'g34-undo-{trial}'})['result']
                assert until(ws, 'building_changed')['event']['event_id'] == undo['event_id']
                duplicate_undo = tool(admin, 'undo', {'event_id': commit['event_id'], 'op_id': f'g34-undo-{trial}'})['result']
                assert duplicate_undo == undo
                assert len(get('/api/buildings/' + bid + '/events')) == version + 2
                assert lift['id'] not in get('/api/buildings/' + bid)['closed']
                restored = replan()
                assert until(ws, 'tour_updated')['revision'] == restored['revision']
                assert restored['order'] == pending_order and not restored['unreachable_stops']
                check_progress(restored)
                duration = round((replanned - started) * 1000, 2)
                assert duration <= 2000
                report['trials'].append({'trial': trial, 'base_version': version,
                    'commit_event': commit['event_id'], 'undo_event': undo['event_id'],
                    'commit_http_ms': round((committed - started) * 1000, 2),
                    'commit_to_ws_ms': round((notified - started) * 1000, 2),
                    'commit_ws_refetch_replan_ms': duration,
                    'through_tour_updated_ws_ms': round((updated - started) * 1000, 2),
                    'collected_stop_ids_preserved': collected,
                    'blocked_reason': blocked['unreachable_stops'][0]['reason'],
                    'route_error': blocked_route['error'], 'next_step_error': next_step['error'],
                    'duplicate_commit_one_event': True, 'duplicate_undo_one_event': True,
                    'stale_preview_error': conflict['error']['code'], 'undo_restores_order': True})

        # No subscriber is connected while this change happens.
        preview = tool(admin, 'propose_edit', {'action': 'close', 'target': lift['id']})['result']
        disconnected_event = tool(admin, 'commit_edit', {'proposal_id': preview['proposal_id'], 'op_id': 'g34-offline-close'})['result']
        with connect(socket_url, open_timeout=5, proxy=None) as ws:
            hello = until(ws, 'hello')
            assert hello['building_version'] == 7
            snap = get('/api/buildings/' + bid)
            previous_tour = get(tour_path)
            assert previous_tour['building_version'] == 6 and snap['building_version'] == 7
            events = get('/api/buildings/' + bid + '/events?since=6')
            check_public(disconnected_event)
            assert events == [disconnected_event]
            caught_up = replan()
            assert until(ws, 'tour_updated')['revision'] == caught_up['revision']
            assert caught_up['building_version'] == 7 and caught_up['unreachable_stops']
            check_progress(caught_up)
            report['checks']['disconnected_socket_catchup'] = {'hello_version': 7,
                'refetched_snapshot': True, 'refetched_tour': True, 'events_since_6': events,
                'replanned_version': 7, 'collected_preserved': True,
                'automatic_ui_reconnect_verified': False}
        report['checks']['public_credentials'] = {
            'public_events_tours_and_ws_omit_session_fields_and_values': True,
            'tool_results_and_displays_omit_session_fields_and_values': True,
        }

        expected = {'tour': get(tour_path), 'session': get('/api/sessions/' + phone),
                    'events': get('/api/buildings/' + bid + '/events')}
        server.kill()  # Only this script's own isolated subprocess; no graceful shutdown.
        server.wait(timeout=10)
        killed_returncode = server.returncode
        server = launch()
        report['restart_health'] = ready()
        actual = {'tour': get(tour_path), 'session': get('/api/sessions/' + phone),
                  'events': get('/api/buildings/' + bid + '/events')}
        assert actual == expected
        assert tool(admin, 'commit_edit', {'proposal_id': preview['proposal_id'], 'op_id': 'g34-offline-close'})['result'] == disconnected_event
        assert get('/api/buildings/' + bid)['building_version'] == 7
        with connect(socket_url, open_timeout=5, proxy=None) as ws:
            assert until(ws, 'hello')['building_version'] == 7
            ws.send('ping')
            assert until(ws, 'pong')['type'] == 'pong'
            resumed = replan()
            assert until(ws, 'tour_updated')['revision'] == resumed['revision']
            check_progress(resumed)
            assert resumed['unreachable_stops']
            undone = tool(admin, 'undo', {'event_id': disconnected_event['event_id'], 'op_id': 'g34-post-restart-undo'})['result']
            assert until(ws, 'building_changed')['event']['event_id'] == undone['event_id']
            recovered = replan()
            assert until(ws, 'tour_updated')['revision'] == recovered['revision']
            assert recovered['order'] == pending_order and not recovered['unreachable_stops']
            check_progress(recovered)
        report['checks']['hard_restart'] = {'terminated_returncode': killed_returncode,
            'exact_state_equal': True, 'before_sha256': digest(expected), 'after_sha256': digest(actual),
            'persisted_events': len(actual['events']), 'persisted_building_version': 7,
            'commit_retry_after_restart_idempotent': True, 'websocket_hello_and_ping': True,
            'blocked_pending_survives': True, 'collected_stop_ids': collected,
            'post_restart_undo_restores_route': True, 'restored_pending_order': recovered['order']}
        assert git('rev-parse', 'HEAD') == expected_sha
        final_diff = subprocess.check_output(['git', '-C', str(source), 'diff', 'HEAD'])
        report['source_after_diff_sha256'] = hashlib.sha256(final_diff).hexdigest()
        assert final_diff == initial_diff
        assert {path: hashlib.sha256((source / path).read_bytes()).hexdigest()
                for path in security_hashes} == security_hashes
        report['source_unchanged_after_run'] = True
        report['status'] = 'PASS'
except (Exception, KeyboardInterrupt) as error:
    report['status'] = 'FAIL'
    report['error'] = repr(error)
finally:
    # Finish this bounded cleanup even if another cancellation signal arrives.
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    if server is not None and server.poll() is None:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
    if server_log is not None:
        server_log.close()
        if report['status'] == 'FAIL':
            report['server_log_tail'] = (state / 'server.log').read_text()[-6000:]
    if state is not None:
        shutil.rmtree(state)
    report['own_server_stopped'] = True
    report['isolated_state_removed'] = True
    report['finished_at'] = datetime.now(timezone.utc).isoformat()
    rendered = json.dumps(report, indent=2) + '\n'
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end='')

sys.exit(0 if report['status'] == 'PASS' else 1)
