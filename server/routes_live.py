"""C1 session, tour, tool, edit-event and marker HTTP transports."""
import importlib
import inspect
import json
import logging
import os
import re
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Body, Header, Query, Request
from fastapi.responses import HTMLResponse
from shapely.geometry import Point
from starter_agent.building_map import outline

from .errors import ServiceError
from . import schemas
from .state import now
from .public import public_payload

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api')


def components(request):
    return request.app.state.service, request.app.state.store


def admin_session(request, session_id, building_id=None):
    if not session_id:
        raise ServiceError('forbidden', 'An admin session is required in X-Session-ID.', status=403)
    session = request.app.state.store.get_session(session_id)
    request.app.state.store._require_admin(session)
    if building_id and session['building_id'] != building_id:
        raise ServiceError('forbidden', 'This admin session belongs to another building.', status=403)
    return session


def checked_position(service, store, building_id, position):
    position = position.model_dump(exclude_none=True) if hasattr(position, 'model_dump') else dict(position)
    if position.get('source') == 'marker':
        if not position.get('marker_id'):
            raise ServiceError('invalid_args', 'A position code is required for a marker fix.', status=422)
        marker = store.get_marker(position['marker_id'])
        if marker['building_id'] != building_id:
            raise ServiceError('invalid_args', 'This position marker belongs to another building.', status=422)
        position = {**marker, 'source': 'marker', 'confidence': 'high'}
        position.pop('building_id', None)
        position.pop('label', None)
    building = service.current(building_id)
    space = building.kit.spaces.get(position['space_id'])
    if not space:
        raise ServiceError('invalid_args', 'Choose a room in the current building.', status=422)
    if position.get('floor_id') and position['floor_id'] != space['floor_id']:
        raise ServiceError('invalid_args', 'Position floor does not match the room.', status=422)
    position['floor_id'] = space['floor_id']
    if position.get('point') is None:
        position['point'] = list(building.kit.anchor(space['id']))
    if not outline(space['polygon']).buffer(0.02).covers(Point(position['point'])):
        raise ServiceError('invalid_args', 'Position must be inside the selected room.', status=422)
    position.setdefault('source', 'manual')
    position.setdefault('heading_deg', None)
    position.setdefault('marker_id', None)
    position['confidence'] = 'high' if position['source'] == 'marker' else ('low' if position['source'] == 'tour_start' else 'medium')
    position['updated_at'] = now()
    return position


@router.post('/sessions', response_model=schemas.Session, tags=['sessions'])
def create_session(body: schemas.SessionCreate, request: Request,
                   admin_token: str | None = Header(default=None, alias='X-Admin-Token',
                       description='Required for admin sessions when TYB_ADMIN_TOKEN is configured. Never returned.')):
    """Create a navigator session, or authenticate an admin with its private code."""
    service, store = components(request)
    if body.role == 'admin':
        store._authorize_admin_creation(admin_token)
    service.current(body.building_id)
    return store.create_session(body.building_id, body.device, body.role, body.profile, admin_token=admin_token)


@router.get('/sessions/{session_id}', response_model=schemas.Session, tags=['sessions'])
def get_session(session_id: str, request: Request):
    return request.app.state.store.get_session(session_id)


@router.patch('/sessions/{session_id}', response_model=schemas.Session, tags=['sessions'])
def update_session(session_id: str, body: schemas.SessionPatch, request: Request):
    service, store = components(request)
    session = store.get_session(session_id)
    patch = body.model_dump(exclude_unset=True)
    for field in ('profile', 'constraints'):
        if field in patch and patch[field] is None:
            raise ServiceError('invalid_args', f'{field} cannot be null.', status=422)
    if patch.get('active_tour_id'):
        tour = store.get_tour(patch['active_tour_id'])
        if tour['building_id'] != session['building_id']:
            raise ServiceError('forbidden', 'This tour belongs to another building.', status=403)
        if session['device'] == 'phone':
            patch['profile'] = tour.get('mobility_profile', 'wheelchair' if tour.get('constraints', {}).get('step_free') else 'walk')
            patch['constraints'] = tour.get('constraints', {})
            if not session['position'] and not patch.get('position'):
                patch['position'] = {**tour['start'], 'source': 'tour_start', 'confidence': 'low', 'marker_id': None}
    if patch.get('position') is not None:
        patch['position'] = checked_position(service, store, session['building_id'], patch['position'])
    result = store.update_session(session_id, patch)
    if session['device'] == 'phone' and patch.get('active_tour_id') and patch['active_tour_id'] != session['active_tour_id']:
        service.notify(session['building_id'], {'type': 'tour_opened', 'tour_id': patch['active_tour_id'], 'session_id': session_id, 'device': 'phone'})
    return result


@router.post('/tools/{name}', response_model=schemas.ToolResponse, response_model_exclude_none=True, tags=['tools'])
def call_tool(name: str, body: schemas.ToolCall, request: Request):
    return request.app.state.registry.call(name, body.session_id, body.args)


@router.get('/buildings/{building_id}/events', tags=['events'])
def get_events(building_id: str, request: Request, since: int = Query(default=0, ge=0)) -> list[dict]:
    service, store = components(request)
    service.current(building_id)
    return public_payload(store.events(building_id, since))


@router.post('/tours', response_model=schemas.TourResult, response_model_exclude_none=True, tags=['tours'])
def create_tour(body: schemas.TourCreate, request: Request) -> dict:
    return public_payload(request.app.state.service.create_tour(body.session_id, body.items, body.start, body.keep_order, body.end))


@router.get('/tours/{tour_id}', response_model=schemas.TourResult, response_model_exclude_none=True, tags=['tours'])
def get_tour(tour_id: str, request: Request) -> dict:
    return public_payload(request.app.state.store.get_tour(tour_id))


@router.post('/tours/{tour_id}/progress', response_model=schemas.TourResult, response_model_exclude_none=True, tags=['tours'])
def progress_tour(tour_id: str, body: schemas.TourProgress, request: Request,
                  session_id: str | None = Header(default=None, alias='X-Session-ID')) -> dict:
    return public_payload(request.app.state.service.progress_tour(tour_id, body.stop_id, body.status, session_id=session_id))


@router.post('/tours/{tour_id}/replan', response_model=schemas.TourResult, response_model_exclude_none=True, tags=['tours'])
def replan_tour(tour_id: str, body: schemas.TourReplan, request: Request) -> dict:
    service, store = components(request)
    session = store.get_session(body.session_id)
    position = checked_position(service, store, session['building_id'], body.position)
    constraints = body.constraints.model_dump(exclude_unset=True) if body.constraints is not None else None
    result = service.replan_tour(tour_id, body.session_id, position, body.reason, constraints=constraints)
    store.update_session(body.session_id, {'position': position, 'active_tour_id': tour_id})
    return public_payload(result)


@router.get('/markers/{marker_id}', tags=['markers'])
def get_marker(marker_id: str, request: Request) -> dict:
    return request.app.state.store.get_marker(marker_id)


@router.post('/buildings/{building_id}/markers', tags=['markers'])
def create_markers(building_id: str, body: schemas.MarkerCreate, request: Request,
                   session_id: str | None = Header(default=None, alias='X-Session-ID')) -> list[dict]:
    admin_session(request, session_id, building_id)
    return request.app.state.markers.create(building_id, body.markers)


@router.get('/buildings/{building_id}/markers/sheet', response_class=HTMLResponse, tags=['markers'])
def marker_sheet(building_id: str, request: Request):
    return HTMLResponse(request.app.state.markers.sheet(building_id))


@router.post('/buildings', tags=['buildings'])
def upload_building(request: Request, raw: dict = Body(...),
                    session_id: str | None = Header(default=None, alias='X-Session-ID')) -> dict:
    admin_session(request, session_id)
    try:
        validate = importlib.import_module('core.validate').validate_building
    except ModuleNotFoundError as exc:
        if exc.name not in ('core', 'core.validate'):
            raise
        raise ServiceError('not_available', 'Building validation is not available yet.', status=503) from exc
    import copy
    raw = copy.deepcopy(raw)
    info = raw.get('building')
    if not isinstance(info, dict):
        raise ServiceError('invalid_args', 'A building object is required.', status=422)
    name = info.get('name', 'building')
    slug = re.sub(r'[^a-z0-9]+', '-', str(name).lower()).strip('-')[:60] or 'building'
    building_id = f'upl-{slug}-{uuid4().hex[:6]}'
    if isinstance(raw.get('building'), dict):
        raw['building']['id'] = building_id
    validation = validate(raw)
    if not validation.get('ok'):
        raise ServiceError('invalid_args', 'Building validation failed.', status=422, validation=validation)
    if not isinstance(building_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', building_id) or '..' in building_id:
        raise ServiceError('invalid_args', 'Building ID is invalid.', status=422)
    state = request.app.state
    if building_id in state.catalog.records():
        raise ServiceError('invalid_args', 'A building with this ID already exists.', status=409)
    # Exclusive create prevents concurrent uploads from overwriting one another.
    path = state.settings.state_dir / 'uploads' / f'{building_id}.json'
    try:
        with path.open('x', encoding='utf-8') as stream:
            json.dump(raw, stream, allow_nan=False)
    except FileExistsError as exc:
        raise ServiceError('invalid_args', 'A building with this ID already exists.', status=409) from exc
    snapshot = state.service.snapshot(building_id)
    with state.store.connect(write=True) as db:
        db.execute('INSERT INTO buildings VALUES(?,?,?,?,?,?)', (building_id, 'upload', str(path), snapshot.content_hash, raw['building']['name'], now()))
    return {'building_id': building_id, 'validation': validation}


@router.post('/buildings/{building_id}/plan-import', tags=['buildings'])
def plan_import(building_id: str, request: Request,
                session_id: str | None = Header(default=None, alias='X-Session-ID')) -> dict:
    admin_session(request, session_id, building_id)
    raise ServiceError('not_available', 'Plan import is not available. Upload a validated building JSON instead.', status=503)


@router.post('/demo/reset', tags=['demo'])
def demo_reset(body: schemas.DemoReset, request: Request,
               session_id: str | None = Header(default=None, alias='X-Session-ID')) -> dict:
    if not request.app.state.settings.demo_mode:
        raise ServiceError('not_available', 'Demo reset is disabled.', status=404)
    admin_session(request, session_id, body.building_id)
    service, store = components(request)
    service.current(body.building_id)
    store.reset(body.building_id)
    # Tours retain collected progress; the reset message tells clients to refetch/replan.
    service.notify(body.building_id, {'type': 'building_reset', 'building_id': body.building_id, 'building_version': 0})
    return {'building_id': body.building_id, 'building_version': 0}


@router.post('/chat', response_model=schemas.ChatResponse, tags=['chat'])
async def chat(body: schemas.ChatInput, request: Request):
    import anyio
    state = request.app.state
    await anyio.to_thread.run_sync(state.store.get_session, body.session_id)
    if not os.environ.get('ANTHROPIC_API_KEY'):
        raise ServiceError('not_available', 'Text chat is not configured. Use the building controls.', status=503)
    if state.chat_agent is None:
        try:
            ChatAgent = importlib.import_module('agent.chat').ChatAgent
        except ModuleNotFoundError as exc:
            if exc.name not in ('agent', 'agent.chat'):
                raise
            raise ServiceError('not_available', 'Text chat is not available yet. Use the building controls.', status=503) from exc
        state.chat_agent = ChatAgent(state.registry, state.store.get_session)
    reply = state.chat_agent.reply
    if inspect.iscoroutinefunction(reply):
        return await reply(body.session_id, body.message)
    return await anyio.to_thread.run_sync(reply, body.session_id, body.message)
