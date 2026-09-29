#!/usr/bin/env python3
"""bayarea/page_view.py - a PARISH-SHAPED VIEW of the Bay registries, for the walkable page machinery.

web/build_parishes.py (owner WILDS) reads parishes/registry/parishes.json + world.json by fixed keys ('parishes',
full_name, landmarks[kind], satellite.mapbox{tiles, attribution, refusal_text}, ...). parish_shaped() maps the Bay
registries onto exactly those keys IN MEMORY (no file is written): counties -> 'parishes', campus points -> landmarks
(kind 'campus', note = their geo-registry provenance) and restoration sites -> landmarks (kind 'restoration site', RECORDED coordinates), RECORDED city points stay anchors (kind 'city'). The Mapbox
endpoint/attribution strings are copied from the parish registry (same deploy-time rule, never configured here).
Nothing is upgraded: provenance strings are carried as they are.

    python3 bayarea/page_view.py --check     # prints a JSON summary; exits 1 naming any missing key
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_TOP = ['frames', 'selection', 'parishes', 'satellite', 'provenance', 'water', 'elevation',
                'landmarks_method', 'source_stamp']
REQUIRED_PARISH = ['outline', 'frame', 'map', 'landmarks', 'anchors', 'borders', 'full_name', 'area_km2']
REQUIRED_WORLD = ['version', 'roads', 'water_levels', 'water_note', 'water_source', 'source_stamp', 'parishes']


def fail(msg):
    raise SystemExit('bayarea page_view: ' + msg)


def parish_shaped(bay, world, parish_reg):
    reg = {k: v for k, v in bay.items() if k != 'counties'}
    reg['parishes'] = {}
    for fips, c in bay['counties'].items():
        p = {k: v for k, v in c.items() if k not in ('campuses',)}
        p['landmarks'] = [{'name': x['name'], 'kind': 'campus', 'lat': x['lat'], 'lng': x['lng'],
                           'world_m': x['world_m'], 'local_m': x['local_m'], 'provenance': x['provenance'],
                           'note': x['source']} for x in c['campuses']] + [
            {'name': x['name'], 'kind': 'restoration site', 'lat': x['lat'], 'lng': x['lng'], 'world_m': x['world_m'],
             'local_m': x['local_m'], 'provenance': x['provenance'], 'note': x['source']} for x in c['restoration_sites']]
        reg['parishes'][fips] = p
    mb = parish_reg['satellite']['mapbox']
    reg['satellite'] = dict(bay['satellite'])
    reg['satellite']['mapbox'] = dict(bay['satellite']['mapbox'], tiles=mb['tiles'], attribution=mb['attribution'])
    w = {k: v for k, v in world.items() if k != 'counties'}
    w['parishes'] = world['counties']
    return reg, w


def load():
    J = lambda p: json.loads((ROOT / p).read_text())  # noqa: E731
    return parish_shaped(J('bayarea/registry/bayarea.json'), J('bayarea/registry/world.json'),
                         J('parishes/registry/parishes.json'))


def check(reg, w):
    miss = [k for k in REQUIRED_TOP if k not in reg] + [f'world.{k}' for k in REQUIRED_WORLD if k not in w]
    for f, p in reg['parishes'].items():
        miss += [f'{f}.{k}' for k in REQUIRED_PARISH if k not in p]
    for k in ('tiles', 'attribution', 'refusal_text'):
        if k not in reg['satellite']['mapbox']:
            miss.append('satellite.mapbox.' + k)
    if sorted(reg['parishes']) != sorted(reg['selection']['selected']) or sorted(w['parishes']) != sorted(reg['parishes']):
        miss.append('selection/world ids differ')
    if miss:
        fail('missing ' + ', '.join(miss))
    return {'ids': sorted(reg['parishes']), 'kinds': sorted({x['kind'] for p in reg['parishes'].values()
                                                               for x in p['landmarks'] + p['anchors']}),
            'names': [reg['parishes'][f]['full_name'] for f in sorted(reg['parishes'])],
            'stamp': reg['source_stamp'], 'world_version': w['version']}


if __name__ == '__main__':
    if sys.argv[1:] != ['--check']:
        fail('usage: python3 bayarea/page_view.py --check')
    print(json.dumps(check(*load())))
