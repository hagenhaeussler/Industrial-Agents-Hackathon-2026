"""Generate real building, route and tool fixtures without reading questions."""

import argparse
import json
from pathlib import Path

from .building import load_building
from .resolve import resolve
from .tour import plan_tour
from .schemas import TourResult


def export(output=Path('fixtures')):
    b = load_building('data/dev/proc-factory-dev-003')
    header = {'producer':"Hagen's codex",'contract':'C3','generated_by':'uv run python -m core.export_fixtures'}
    snapshot = {'_fixture':{**header,'replace_by':f'/api/buildings/{b.id}'},
                'building':b.data,'building_version':b.version,'content_hash':b.content_hash,'closed':[],
                'derived':{'anchors':{sid:list(b.anchor(sid)) for sid in b.spaces},
                           'areas_m2':{sid:p.area for sid,p in b.polygons.items()}}}
    start = next(sid for o in b.openings.values() if 'outside' in o['space_ids'] for sid in o['space_ids'] if sid!='outside')
    selected, spaces = [], set()
    # Deliberately span floors when possible, choosing only from the building.
    for floor in sorted(b.floors.values(), key=lambda f:f['level'], reverse=True):
        for a in b.assets.values():
            if a['floor_id']==floor['id'] and a['space_id'] not in spaces:
                selected.append(a['id']); spaces.add(a['space_id'])
                break
    for a in b.assets.values():
        if len(selected)>=3: break
        if a['space_id'] not in spaces:
            selected.append(a['id']); spaces.add(a['space_id'])
    tour = plan_tour(b,start,selected)
    tour['tour_id']='aaaaaaaaaa'
    TourResult.model_validate(tour)
    tour['_fixture']={**header,'replace_by':'/api/tours/{id}','geometry':'reconstructed_kit_walks'}
    asset=next(iter(b.assets.values()))
    def tool(name,result,speech,display):
        return {'ok':True,'tool':name,'request_id':'req_aaaaaaaaaaaa','building_id':b.id,'building_version':b.version,
                'result':result,'speech':speech,'display':display,'trace':[]}
    def failed_find(query,code,speech):
        found=resolve(b,query,'asset')
        return {'ok':False,'tool':'find','request_id':'req_aaaaaaaaaaaa','building_id':b.id,'building_version':b.version,
                'error':{'code':code,'message':speech,'candidates':found['candidates']},'speech':speech}
    samples = {'_fixture':{**header,'replace_by':'/api/tools/{name}'},
               'find_unique':tool('find',resolve(b,asset['id']),'Part located.',{'kind':'highlight','asset_ids':[asset['id']]}),
               'find_ambiguous':failed_find('desk','ambiguous','Which desk do you mean?'),
               'find_not_found':failed_find('nonexistent object xyz','not_found','That part is not in this building.'),
               'plan_tour':tool('plan_tour',{k:v for k,v in tour.items() if k!='_fixture'},'Your collection tour is ready.',{'kind':'tour','tour_id':tour['tour_id']})}
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    for name,value in [(f'building_{b.id}.json',snapshot),(f'tour_{b.id}.json',tour),('tool_responses.json',samples)]:
        (output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(output/name)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('fixtures'))
    export(parser.parse_args().output)


if __name__=='__main__': main()
