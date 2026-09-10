#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the surfaces pack builder (spec §24).

Resolves a floor finish for every room of every hall: the trade's hazard
first, then the room's function, and the record says which rule placed it.
Per §24.1 a hazard is only recorded as hazard-driven when it changed
something — where the hazard's choice equals the function default, the
function decided, and the record says so.

Emits surfaces/registry/finishes.json: 111 halls × 11 rooms, each entry
carrying the surface id and the placing rule, plus the full catalogue with
its renderer-ready parameters and the reason each finish exists.
"""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'web'))
from surfaces import (SURFACES, FUNCTION_DEFAULT, HAZARDS, hazard_of,  # noqa: E402
                      BASE_CONDITIONS, HAZARD_CONDITIONS, hazards_of,
                      merge_conditions)
from interiors import ROOMS  # noqa: E402

PACK_VERSION = "3.2.0"
BUILT = "2026-09-10"

unions = json.load(open(ROOT / 'unions/registry/unions.json'))['unions']
room_strands = [r[0] for r in ROOMS]
assert set(FUNCTION_DEFAULT) == set(room_strands), 'a default per room, exactly'

halls = {}
hazard_count = 0
for u in unions:
    hz, hz_rooms = hazard_of(u['name'], u['focus'])
    all_hz = hazards_of(u['name'], u['focus'])
    rooms = {}
    conditions = {}
    for strand in room_strands:
        func = FUNCTION_DEFAULT[strand]
        want = hz_rooms.get(strand)
        if want and want != func:
            rooms[strand] = {'surface': want, 'placed_by': 'hazard', 'hazard': hz}
            hazard_count += 1
        else:
            # the function choice — which the hazard, where present, happens
            # to confirm rather than change (§24.1)
            rooms[strand] = {'surface': func, 'placed_by': 'function'}
        # §24.2: every governing hazard has its say, more demanding wins
        governing = [k for k, hrooms in all_hz if strand in hrooms]
        conditions[strand] = merge_conditions(strand, governing)
    halls[u['slug']] = {'hazard': hz, 'hazards': [k for k, _ in all_hz],
                        'rooms': rooms, 'conditions': conditions}

stamp = hashlib.sha256((HERE / 'surfaces.py').read_bytes()).hexdigest()[:16]

doc = {
    'pack': 'smartcitix-trade-craft-academy-surface-registry',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'spec': 'section 24 of the ACP suite',
    'honesty': {
        'status': 'general good practice, not a code reference; no figure '
                  'is read from any jurisdiction\'s standard and no surface '
                  'names a product, brand, fire rating or specification '
                  'number. A real deployment replaces these with the local '
                  'standard.',
    },
    'catalogue': {
        sid: {'name': n, 'color': c, 'roughness': r, 'metalness': m,
              'pattern': pat, 'tile_m': tile, 'why': why}
        for sid, (n, c, r, m, pat, tile, why) in SURFACES.items()
    },
    'hazards_in_use': sorted({h['hazard'] for h in halls.values() if h['hazard']}),
    # Halls whose trade names no hazard that would CHANGE a floor finish.
    # That is a narrower statement than "no hazard at all" (a suspended
    # load is a hazard, but not one a floor answers), and the field says
    # exactly what was tested rather than more.
    'no_finish_driving_hazard': sorted(s for s, h in halls.items() if not h['hazard']),
    'hazard_placed_finishes': hazard_count,
    # RECORDED / DERIVED / SCHEMATIC, after the Locator.X rooms module
    # (Apache-2.0, the same foundation): nothing is stated that the source
    # does not support. No room here is RECORDED - nothing was surveyed.
    'provenance': {
        'geometry': 'SCHEMATIC',
        'finish': 'DERIVED',
        'conditions': 'DERIVED',
        'discipline': 'RECORDED/DERIVED/SCHEMATIC tagging after the '
                      'Locator.X rooms module (Apache-2.0)',
    },
    'base_conditions': {k: {'lux': v[0], 'ach': v[1], 'noise_db': v[2],
                            'temp_c': list(v[3]), 'ppe': list(v[4])}
                        for k, v in BASE_CONDITIONS.items()},
    'hazard_conditions': {k: {'lux': v[0], 'ach': v[1], 'noise_db': v[2],
                              'temp_c': list(v[3]), 'ppe': list(v[4])}
                          for k, v in HAZARD_CONDITIONS.items()},
    'halls': halls,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'finishes.json').write_text(json.dumps(doc, indent=1) + '\n')
n_none = len(doc['no_finish_driving_hazard'])
print(f"surfaces registry: {len(SURFACES)} finishes over {len(halls)} halls "
      f"x {len(room_strands)} rooms; {len(doc['hazards_in_use'])} hazard "
      f"classes in use, {hazard_count} hazard-placed finishes, "
      f"{n_none} halls with no finish-driving hazard (source stamp {stamp})")
