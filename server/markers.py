"""Known standing points, printable 12 cm QR markers, and safe sheet HTML."""
from html import escape
from io import BytesIO
import json

import qrcode
from qrcode.image.svg import SvgPathImage
from shapely.geometry import Point
from starter_agent.building_map import outline

from .errors import ServiceError
from .state import identifier
from .schemas import MarkerInput
from pydantic import ValidationError


class MarkerService:
    def __init__(self, service, public_base_url):
        self.service = service
        self.store = service.store
        self.base_url = public_base_url.rstrip('/')

    def create(self, building_id, entries):
        building = self.service.snapshot(building_id)
        if hasattr(building, 'model_dump'):
            building = building.model_dump()
        raw = building['building']
        spaces = {space['id']: space for space in raw['spaces']}
        validated = []
        for item in entries:
            try:
                item = MarkerInput.model_validate(item.model_dump() if hasattr(item, 'model_dump') else item).model_dump()
            except ValidationError as exc:
                raise ServiceError('invalid_args', 'Marker fields are invalid.', status=422) from exc
            space = spaces.get(item['space_id'])
            if not space:
                raise ServiceError('invalid_args', 'Marker space is not in this building.', status=422)
            if not outline(space['polygon']).buffer(0.02).covers(Point(item['point'])):
                raise ServiceError('invalid_args', 'Marker standing point must lie in its space.', status=422)
            validated.append({'marker_id': identifier('marker'), 'building_id': building_id,
                              'floor_id': space['floor_id'], **item})
        return [self.store.put_marker(marker) for marker in validated]

    def generate(self, session_id):
        session = self.store.get_session(session_id)
        self.store._require_admin(session)
        building_id = session['building_id']
        record = self.service.catalog.get(building_id)
        marker_file = record.path.parent / 'markers.json'
        if marker_file.is_file() and record.path.is_relative_to(self.service.catalog.settings.hero_dir):
            definitions = json.loads(marker_file.read_text())
            entries = definitions if isinstance(definitions, list) else definitions['markers']
            entries = [{key: value for key, value in item.items() if key in MarkerInput.model_fields} for item in entries]
        else:
            snapshot = self.service.snapshot(building_id)
            if hasattr(snapshot, 'model_dump'):
                snapshot = snapshot.model_dump()
            raw = snapshot['building']
            spaces = {s['id']: s for s in raw['spaces']}
            used = set()
            entries = []
            for opening in raw['openings']:
                for sid in opening['space_ids']:
                    if sid not in spaces or sid in used:
                        continue
                    used.add(sid)
                    space = spaces[sid]
                    anchor = outline(space['polygon']).representative_point()
                    entries.append({'space_id': sid, 'point': [anchor.x, anchor.y], 'heading_deg': 0,
                                    'label': space['name']})
        markers = self.store.markers(building_id) or self.create(building_id, entries)
        return {'markers': markers, 'sheet_url': f'/api/buildings/{building_id}/markers/sheet'}

    def sheet(self, building_id):
        try:
            self.service.catalog.get(building_id)
        except KeyError as exc:
            raise ServiceError('not_found', 'Building not found.', status=404) from exc
        cards = []
        for marker in self.store.markers(building_id):
            image = qrcode.make(f"{self.base_url}/m/{marker['marker_id']}", image_factory=SvgPathImage)
            buffer = BytesIO()
            image.save(buffer)
            svg = buffer.getvalue().decode()
            label = escape(marker['label'])
            cards.append(f'<article><h2>{label}</h2><div class="qr">{svg}</div>'
                         f'<p>Floor: {escape(marker["floor_id"])}</p><p>Stand on the footprint and face the code.</p>'
                         f'<p>Building heading: {float(marker["heading_deg"]):g}°</p>'
                         '<p class="footprint">↑<br>STAND HERE</p></article>')
        return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Building position markers</title>'
                '<style>@page{margin:15mm}body{font:16px sans-serif}article{break-after:page;text-align:center}'
                '.qr svg{width:12cm;height:12cm}.footprint{font-size:30px;border:2px dashed;padding:12mm;display:inline-block}'
                '</style><body><h1>Position markers</h1>' + ''.join(cards) + '</body></html>')
