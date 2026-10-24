"""Shared preview team workspaces and validated two-file building creation.

Teams organize the shared preview catalog; they are not authentication boundaries.
Creating buildings preserves the application's existing private admin-code gate.
"""
import copy
import csv
import io
import json
import math

from fastapi import APIRouter, Header, Request
from pydantic import BaseModel, Field
from shapely.geometry import Point
from starter_agent.building_map import outline

from .buildings import BuildingSummary
from .errors import ServiceError
from .routes_live import admin_allowed, save_uploaded_building
from .schemas import Input

router = APIRouter(prefix='/api/teams', tags=['teams'])
TEAM_NAMES = {
    'production': 'Production & Assembly',
    'engineering': 'Research & Engineering',
    'facilities': 'Facilities & Maintenance',
    'property': 'Property Operations',
    'projects': 'New Projects',
}


class TeamSummary(BaseModel):
    id: str
    name: str
    building_count: int


class TeamBuildingUpload(Input):
    floor_plan: dict
    equipment_csv: str = Field(min_length=1, max_length=2_000_000)


class TeamValidationNote(BaseModel):
    code: str
    path: str
    message: str


class TeamValidation(BaseModel):
    ok: bool
    errors: list[TeamValidationNote]
    warnings: list[TeamValidationNote]
    stats: dict[str, int]


class TeamBuildingResult(BaseModel):
    building_id: str
    team_id: str
    validation: TeamValidation


def require_team(team_id):
    if team_id not in TEAM_NAMES:
        raise ServiceError('not_found', 'That team was not found.', status=404)


def grouped_catalog(request):
    state = request.app.state
    with state.store.connect() as db:
        assigned = dict(db.execute('SELECT building_id, team_id FROM building_teams').fetchall())
    grouped = {key: [] for key in TEAM_NAMES}
    for bid, record in state.catalog.records().items():
        team = assigned.get(bid)
        if team not in grouped:
            source = record.summary.source
            if source in {'swiss_dwellings', 'resplan'}:
                team = 'property'
            elif source == 'osm_indoor':
                team = 'facilities'
            elif source == 'procedural':
                info = json.loads(record.path.read_text(encoding='utf-8')).get('building', {})
                reference = info.get('source_ref')
                team = 'production' if isinstance(reference, dict) and reference.get('generator') == 'factory' else 'engineering'
            else:
                team = 'projects'
        grouped[team].append(record.summary)
    for buildings in grouped.values():
        buildings.sort(key=lambda item: (item.name.casefold(), item.id))
    return grouped


@router.get('', response_model=list[TeamSummary])
def teams(request: Request):
    groups = grouped_catalog(request)
    return [TeamSummary(id=key, name=name, building_count=len(groups[key])) for key, name in TEAM_NAMES.items()]


@router.get('/{team_id}/buildings', response_model=list[BuildingSummary])
def team_buildings(team_id: str, request: Request):
    require_team(team_id)
    return grouped_catalog(request)[team_id]


def equipment_assets(raw, source):
    """Read the kit-compatible equipment CSV. All positions remain measured input."""
    reader = csv.DictReader(io.StringIO(source.lstrip('\ufeff'), newline=''))
    required = {'asset_id', 'name', 'type', 'space_id', 'x_m', 'y_m'}
    fields = reader.fieldnames or []
    if len(fields) != len(set(fields)) or not required.issubset(fields):
        raise ServiceError('invalid_args', 'The equipment CSV needs asset_id, name, type, space_id, x_m and y_m columns.', status=422)
    spaces = {space['id']: space for space in raw.get('spaces', []) if isinstance(space, dict) and isinstance(space.get('id'), str)}
    polygons = {sid: outline(space['polygon']) for sid, space in spaces.items()}
    assets, seen = [], set()
    number = 1
    try:
        for number, row in enumerate(reader, 2):
            if number > 10_001:
                raise ServiceError('invalid_args', 'Upload at most 10,000 equipment rows.', status=422)
            if None in row or any(not (row.get(key) or '').strip() for key in required):
                raise ValueError('A required value is missing or the row has extra columns.')
            row = {key: (value or '').strip() for key, value in row.items()}
            sid, aid = row['space_id'], row['asset_id']
            if sid not in spaces:
                raise ValueError('space_id must match a room in the floor plan.')
            if aid in seen:
                raise ValueError('Each asset_id must be unique.')
            seen.add(aid)
            floor_id = spaces[sid]['floor_id']
            if row.get('floor_id') and row['floor_id'] != floor_id:
                raise ValueError('The equipment floor does not match its room.')
            point = [float(row['x_m']), float(row['y_m'])]
            width, depth = float(row.get('width_m') or 0.4), float(row.get('depth_m') or 0.4)
            rotation = float(row.get('rotation_deg') or 0)
            if not all(math.isfinite(value) for value in [*point, width, depth, rotation]) or min(width, depth) <= 0:
                raise ValueError('Coordinates and dimensions must be finite; dimensions must be positive.')
            if not polygons[sid].buffer(0.02).covers(Point(point)):
                raise ValueError('Equipment coordinates must be inside their room.')
            assets.append({'id': aid, 'name': row['name'], 'type': row['type'], 'category': row.get('category') or 'equipment',
                           'space_id': sid, 'floor_id': floor_id, 'position': point,
                           'footprint': {'width_m': width, 'depth_m': depth, 'rotation_deg': rotation}, 'source': 'upload'})
    except (ValueError, TypeError, csv.Error) as exc:
        raise ServiceError('invalid_args', f'Equipment row {number}: {exc}', status=422) from None
    if not assets:
        raise ServiceError('invalid_args', 'The equipment list needs at least one item.', status=422)
    return assets


@router.post('/{team_id}/buildings', response_model=TeamBuildingResult)
def create_team_building(team_id: str, body: TeamBuildingUpload, request: Request,
                         admin_token: str | None = Header(default=None, alias='X-Admin-Token')):
    require_team(team_id)
    if not admin_allowed(request, admin_token):
        raise ServiceError('forbidden', 'Building creation requires the private team access code.', status=403)
    try:
        if len(json.dumps(body.floor_plan, allow_nan=False)) > 5_000_000:
            raise ServiceError('invalid_args', 'The floor plan must be smaller than 5 MB.', status=413)
    except (ValueError, RecursionError):
        raise ServiceError('invalid_args', 'The floor plan contains invalid data.', status=422) from None
    from core.validate import validate_building
    raw = copy.deepcopy(body.floor_plan)
    raw['assets'] = []
    validation = validate_building(raw)
    if not validation['ok']:
        raise ServiceError('invalid_args', 'Check the floor plan before uploading.', status=422, validation=validation)
    raw['assets'] = equipment_assets(raw, body.equipment_csv)
    result = save_uploaded_building(request, raw, team_id=team_id)
    return {**result, 'team_id': team_id}
