#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the surfaces pack builder (spec §24).

Resolves a floor finish and a wall for every room of every hall: the
trade's hazard first, then the trade's craft, then the room's function, and
the record says which rule placed it. Per §24.1 a rule is only recorded as
the placer when it changed something — where its choice equals the function
default, the function decided, and the record says so.

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
from surfaces import (SURFACES, FUNCTION_DEFAULT, HAZARD_KEYS, hazard_of,  # noqa: E402
                      BASE_CONDITIONS, HAZARD_CONDITIONS, hazards_of,
                      merge_conditions, WALLS, WALL_DEFAULT, wall_of,
                      PATTERNS, CRAFT_KEYS, crafts_of, finish_of,
                      HAZARD_ROOMS, CRAFT_ROOMS, WALL_HAZARD, CRAFT_WALL)
from interiors import ROOMS  # noqa: E402

# One bundle version, read from the manifest rather than typed here.
PACK_VERSION = json.load(open(ROOT / 'pack/manifest.json'))['pack_version']
BUILT = "2026-09-10"

unions = json.load(open(ROOT / 'unions/registry/unions.json'))['unions']
room_strands = [r[0] for r in ROOMS]
assert set(FUNCTION_DEFAULT) == set(room_strands), 'a default per room, exactly'

halls = {}
for u in unions:
    hz, hz_rooms = hazard_of(u['name'], u['focus'])
    all_hz = hazards_of(u['name'], u['focus'])
    all_cr = crafts_of(u['name'], u['focus'])
    craft_keys = [k for k, _ in all_cr]
    rooms = {}
    walls = {}
    conditions = {}
    for strand in room_strands:
        # §24.1: hazard, then craft, then function — and the rule lives in
        # the catalogue module, which the wall resolver reads too, so the
        # two cannot drift into resolving their tiers differently.
        rooms[strand] = finish_of(strand, hz, hz_rooms, craft_keys)
        # §24.4: the wall resolves against EVERY hazard the trade carries,
        # not only the finish-driving one — a trade can weld in a bay whose
        # floor was placed by a different hazard entirely, and the bay walls
        # are still the thing that stops the flash.
        walls[strand] = wall_of(strand, [k for k, _ in all_hz], craft_keys)
        # §24.2: every governing hazard has its say, more demanding wins.
        # Crafts are absent on purpose — a craft is what the trade does, not
        # what the work can do to the person, so it has nothing to say about
        # lighting, air changes or PPE.
        governing = [k for k, hrooms in all_hz if strand in hrooms]
        conditions[strand] = merge_conditions(strand, governing)
    halls[u['slug']] = {'hazard': hz, 'hazards': [k for k, _ in all_hz],
                        'craft': craft_keys[0] if craft_keys else None,
                        'crafts': craft_keys,
                        'rooms': rooms, 'walls': walls,
                        'conditions': conditions}

# One truth per fact: every count below is counted off the rows that were
# just written, never carried along in a variable that could fall out of
# step with them.
def _tally(records, key):
    return sum(1 for h in halls.values() for r in h[records].values()
               if r['placed_by'] == key)


hazard_count = _tally('rooms', 'hazard')
craft_count = _tally('rooms', 'craft')
wall_hazard_count = _tally('walls', 'hazard')
wall_craft_count = _tally('walls', 'craft')

# A finish or a wall nobody stands in front of is a preference, and §24.1
# says this catalogue holds none. The build fails rather than shipping a
# catalogue entry no rule can reach.
placed_fin = {r['surface'] for h in halls.values() for r in h['rooms'].values()}
placed_wal = {w['wall'] for h in halls.values() for w in h['walls'].values()}
unplaced_fin = sorted(set(SURFACES) - placed_fin)
unplaced_wal = sorted(set(WALLS) - placed_wal)
assert not unplaced_fin, f'finishes no rule ever places: {unplaced_fin}'
assert not unplaced_wal, f'walls no rule ever places: {unplaced_wal}'

# Every rule the record names must be a rule that exists. A placement that
# named a tier nothing declares would read as authoritative and be nothing.
for _h in halls.values():
    for _r in _h['rooms'].values():
        assert _r['placed_by'] in ('hazard', 'craft', 'function'), _r
        assert _r.get('hazard', None) in (None, *HAZARD_KEYS), _r
        assert _r.get('craft', None) in (None, *CRAFT_KEYS), _r
    for _w in _h['walls'].values():
        assert _w['placed_by'] in ('hazard', 'craft', 'function'), _w

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
    'wall_catalogue': {
        wid: {'name': n, 'color': c, 'roughness': r, 'metalness': m,
              'pattern': pat, 'tile_m': tile, 'wainscot': wc,
              'wainscot_m': wm, 'why': why}
        for wid, (n, c, r, m, pat, tile, wc, wm, why) in WALLS.items()
    },
    'wall_defaults': dict(WALL_DEFAULT),
    'function_defaults': dict(FUNCTION_DEFAULT),
    # The pattern vocabulary, declared once and closed in both directions by
    # the catalogue module: a renderer that meets a pattern it has no recipe
    # for can say which one it was rather than silently drawing something
    # else.
    'patterns': dict(PATTERNS),
    # The rules themselves, emitted once. Every placement in `halls` below
    # is these four tables applied to a hall's hazard and craft lists, and
    # the suite re-derives all of them from here rather than spot-checking a
    # handful - which is only possible because the rules are published
    # instead of being locked inside the builder that ran.
    'rules': {
        'hazard_rooms': {k: dict(v) for k, v in HAZARD_ROOMS.items()},
        'craft_rooms': {k: dict(v) for k, v in CRAFT_ROOMS.items()},
        'hazard_walls': {k: dict(v) for k, v in WALL_HAZARD.items()},
        'craft_walls': {k: dict(v) for k, v in CRAFT_WALL.items()},
    },
    'hazards_in_use': sorted({h['hazard'] for h in halls.values() if h['hazard']}),
    'crafts_in_use': sorted({c for h in halls.values() for c in h['crafts']}),
    # Halls whose trade names no hazard that would CHANGE a floor finish.
    # That is a narrower statement than "no hazard at all" (a suspended
    # load is a hazard, but not one a floor answers), and the field says
    # exactly what was tested rather than more.
    'no_finish_driving_hazard': sorted(s for s, h in halls.items() if not h['hazard']),
    'hazard_placed_finishes': hazard_count,
    'craft_placed_finishes': craft_count,
    'hazard_placed_walls': wall_hazard_count,
    'craft_placed_walls': wall_craft_count,
    # Empty by construction, and asserted above. The field is emitted rather
    # than assumed so the suite can hold the next catalogue to it too.
    'unplaced_finishes': unplaced_fin,
    'unplaced_walls': unplaced_wal,
    # Halls whose trade names no craft. Narrower than "nothing is known
    # about this trade": these halls are placed by hazard and function, and
    # the field says exactly which halls that is.
    'no_craft': sorted(s2 for s2, h in halls.items() if not h['crafts']),
    # Walls a hazard never moved. Stated the same narrow way the floor
    # field above is: these trades carry hazards, several of them, and
    # none of those hazards is answered at shoulder height.
    'no_wall_driving_hazard': sorted(
        s2 for s2, h in halls.items()
        if all(w['placed_by'] != 'hazard' for w in h['walls'].values())),
    # RECORDED / DERIVED / SCHEMATIC, after the Locator.X rooms module
    # (Apache-2.0, the same foundation): nothing is stated that the source
    # does not support. No room here is RECORDED - nothing was surveyed.
    'provenance': {
        'geometry': 'SCHEMATIC',
        'finish': 'DERIVED',
        'wall': 'DERIVED',
        # The catalogue entries themselves are AUTHORED: someone wrote each
        # colour, roughness and reason. What is DERIVED is the placement -
        # which hall gets which entry, read from the trade's own words.
        'catalogue': 'AUTHORED',
        'placement': 'DERIVED',
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
n_wall_none = len(doc['no_wall_driving_hazard'])
print(f"surfaces registry: {len(SURFACES)} finishes and {len(WALLS)} walls over "
      f"{len(halls)} halls x {len(room_strands)} rooms in "
      f"{len(PATTERNS)} patterns; "
      f"{len(doc['hazards_in_use'])} hazard classes and "
      f"{len(doc['crafts_in_use'])} crafts in use, "
      f"{hazard_count} hazard-placed and {craft_count} craft-placed finishes, "
      f"{wall_hazard_count} hazard-placed and {wall_craft_count} craft-placed "
      f"walls, {n_none} halls with no finish-driving hazard, "
      f"{n_wall_none} with no wall-driving hazard (source stamp {stamp})")
