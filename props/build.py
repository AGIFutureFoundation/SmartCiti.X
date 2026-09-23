#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the props registry builder.

WHAT IS MISSING FROM THE BUNDLE. There are 111 halls of 11 rooms, which is
1,221 walkable rooms. Every one of them already has a label, a purpose, a
floor finish, a wall finish, an illuminance record and a luminaire tuned to
it. None of them has anything STANDING IN IT. A learner walks into
"Inspection Bench — Acceptance criteria and sign-off" and finds a well-lit
empty box. This pack declares the vocabulary of small things that turns a
lit box into a room somebody works in.

WHAT THE MEASUREMENT SAID. Six reference interiors were measured before any
of this was drawn (assets/REFERENCE.md carries the table). The finding that
mattered is not about polygons: the blocks that read as real places have a
MEDIAN MESH OF 46 AND 104 TRIANGLES over 70 and 93 meshes respectively, at
128x128 textures. One modern character in the same set is 222,507 triangles
in a single mesh and reads as one object. A place is made of many small
distinct pieces, not of dense ones. Nothing from those files is vendored,
copied or named here — two of them are somebody else's copyrighted assets.
What was taken is a technique and a number.

AND WHAT THE SCENE SAID. web/eval_scene.mjs measures a hall interior in a
browser and states what it may cost; both numbers are READ at the top of
this file and neither is typed anywhere in it. What the measurement says is
that the view is DRAW-CALL BOUND with a large unused triangle budget, and
the design follows: props are 40-250 triangles each because that is the
size at which a piece reads as a thing, they name one of seven materials
because a material is a draw call, and they POOL into a handful of merged
meshes for the whole hall because that is the currency that is actually
scarce. One draw call per prop across eleven rooms is the anti-pattern, and
the budget block below refuses it.

AND WHAT THE ROOM SAID. The catalogue is three hundred pieces of furniture
and a room's two partitions hold about three of them. That is not a
rounding error, it is the governing fact of this pack: what a hall costs is
set by the metres of wall a room has, not by how many pieces are on offer,
which is why growing the vocabulary tenfold costs no new material and no
new draw call. The fit-out below is simulated against those metres rather
than assumed, so the budget is the wall's answer and not the catalogue's.

ONE TRUTH PER FACT. No room label, purpose or footprint is typed in this
file. `web/interiors.py` owns that table and it is imported. No hazard, PPE
item or illuminance figure is typed either: `surfaces/registry/finishes.json`
owns those and they are read. The page's own body radius, eye height, grid
unit, floor thickness, partition height and bench setback are parsed out of
`web/build_3d.py` rather than restated, because a prop that is 5 cm taller
than the wall it hangs on is a bug nobody sees in a diff.

DERIVED, NOT PLACED. A prop lands in a strand because a token it declares
appears in THAT STRAND'S OWN purpose string — the same technique
interiors.py already uses to place a trade's fixtures from its own focus
line. A hazard prop lands in a room because THAT ROOM'S OWN conditions
record asks for the protective equipment the prop holds. Neither list is
hand-assigned, and the build fails if a room that requires PPE gets no PPE
prop.

WHAT THIS IS NOT. These are schematic shapes for a training environment.
The eyewash stand is a cylinder and a bowl standing where a room's record
says corrosives are handled; it is not a fixture specification, not a
compliance artefact and not evidence that anything has been provided.
Nothing in this pack should be read as a safety-equipment specification.
"""
import hashlib
import json
import math
import pathlib
import re
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'web'))
from interiors import ROOMS, min_units, GRID  # noqa: E402

# One bundle version, read from the manifest rather than typed here.
PACK_VERSION = json.load(open(ROOT / 'pack/manifest.json'))['pack_version']
BUILT = "2026-09-22"

FINISHES = json.load(open(ROOT / 'surfaces/registry/finishes.json'))
STATIONS = json.load(open(ROOT / 'stations/registry/stations.json'))
CRIBS = json.load(open(ROOT / 'tools/registry/toolcribs.json'))
HALLS = json.load(open(ROOT / 'pack/registry/halls.json'))['halls']
LEDGER = json.load(open(ROOT / 'pack/manifest.json'))['ledger']

for name, reg in (('surfaces', FINISHES), ('stations', STATIONS),
                  ('tools', CRIBS)):
    assert reg['pack_version'] == PACK_VERSION, \
        f'one bundle version: the {name} registry is a different build'

PAGE = (ROOT / 'web/build_3d.py').read_text()
EVAL = (ROOT / 'web/eval_scene.mjs').read_text()


def page_num(pattern, what):
    """Read one number out of the page, or stop.

    A default here would be the whole defect this pack is trying to avoid:
    a prop sized against a constant the page does not actually use looks
    right in the registry and wrong in the room. If the page stops saying
    it, this build stops.
    """
    m = re.search(pattern, PAGE)
    assert m, f'web/build_3d.py no longer states {what} (/{pattern}/)'
    return float(m.group(1))


# ---------------------------------------------------------------------------
# The page's own numbers. Every one of these is READ, and the comment says
# what it is so the next person does not have to find it again.
# ---------------------------------------------------------------------------
BODY_R = page_num(r'const BODY_R = ([\d.]+);', 'the walker body radius')
EYE_H = page_num(r'EYE_H = ([\d.]+)', 'the walker eye height')
U_M = page_num(r'const U = (\d+);', 'metres per grid unit')
FLOOR_INSET = page_num(r'boxGeo\(rw - ([\d.]+), [\d.]+, rd - [\d.]+\), fmat\)',
                       'the room floor inset')
FLOOR_T = page_num(r'boxGeo\(rw - [\d.]+, ([\d.]+), rd - [\d.]+\), fmat\)',
                   'the room floor thickness')
FLOOR_Y = page_num(r'floor\.position\.set\(rx, ([\d.]+), rz\)',
                   'the room floor height')
PART_H = page_num(r'push\(pmat, slab\(len, ([\d.]+), [\d.]+, c, [\d.]+, zz\)\)',
                  'the room partition height')
PART_Y = page_num(r'push\(pmat, slab\(len, [\d.]+, [\d.]+, c, ([\d.]+), zz\)\)',
                  'the room partition centre height')
LABEL_Y = page_num(r'lab\.position\.set\(rx, ([\d.]+), rz\);',
                   'the room label height')
BENCH_SETBACK = page_num(r'const bz = rz \+ rd/2 - ([\d.]+);',
                         'the fixture bench setback from the back wall')
BENCH_HD = page_num(r'wallRect\(bx, bz, [\d.]+, ([\d.]+)\);',
                    'the fixture bench half-depth')

FLOOR_TOP = FLOOR_Y + FLOOR_T / 2      # a prop stands on this, not on y=0
PART_TOP = PART_Y + PART_H / 2         # a wall-mounted prop may not pass this
GAP_M = 0.25                           # POLICY: air between two pieces
# POLICY, and derived: the doorway side of a room stays clear by a whole
# body width, and the back band belongs to the fixture benches the page
# already draws there. Neither number is invented.
FRONT_CLEAR_M = 2 * BODY_R
BACK_RESERVE_M = BENCH_SETBACK + BENCH_HD + GAP_M

# The materials the page already builds. A prop may name one of these and
# nothing else — a new material is a new draw call and a new decision.
_matblock = re.search(r'const mat = \{(.*?)\n\};', PAGE, re.S)
assert _matblock, 'web/build_3d.py no longer declares the shared material table'
PAGE_MATERIALS = set(re.findall(r'^\s{2}(\w+):', _matblock.group(1), re.M))
assert len(PAGE_MATERIALS) > 10, 'the material table came back suspiciously small'

# The page ALREADY has a `PROPS` const: the outdoor yard dressing in front
# of a hall. This pack is the indoor vocabulary and must not collide with
# it, so the identifier the contract asks for is namespaced and the ids are
# checked against the yard's.
_yardblock = re.search(r'const PROPS = \{(.*?)\n\};', PAGE, re.S)
assert _yardblock, 'web/build_3d.py no longer declares the yard prop table'
YARD_PROPS = set(re.findall(r'^\s{2}(\w+):', _yardblock.group(1), re.M))
# This used to RESERVE the name `ROOM_PROPS` for a table the page had not
# written yet, and assert the page did not already use it. The page draws
# these props now, and it does not do it with a table: placeRoomProps()
# lays each room's props against the partitions buildHall() just cut, into
# one hall-wide pool. So the reservation is gone and what replaces it is an
# assertion about the functions that really exist. A reserved name for
# work that has since been done differently is a contract nobody is party
# to any more.
for _sym in ('function placeRoomProps(', 'function flushProps('):
    assert _sym in PAGE, (
        'web/build_3d.py no longer has %s, which is what stands these props. '
        'This pack describes a page that draws it; if the page stopped, the '
        'description is false and this build refuses to write it.' % _sym)
assert 'function flushParts(pool, g)' in PAGE, \
    'the page no longer has the pooled-merge helper this pack is drawn through'
assert 'function wallRect(' in PAGE, \
    'the page no longer has the solid-rectangle helper that makes a prop solid'

# The repo's own measured baseline and its own ceiling for this view.
# web/eval_scene.mjs is the only file in this bundle that states what a
# rendered hall actually costs and what it may cost, and it states both with
# a reason, so those are the numbers this pack is held to. They are READ —
# including the headroom multipliers, so that a change to the eval's policy
# moves this pack's ceiling with it instead of leaving a stale copy behind.
def eval_num(pattern, what):
    m = re.search(pattern, EVAL)
    assert m, f'web/eval_scene.mjs no longer states {what} (/{pattern}/)'
    return m.group(1)


_hall = re.search(r'hall:\s*\{ calls: ([\d_]+), tris: ([\d_]+), '
                  r'meshes: ([\d_]+) \}', EVAL)
assert _hall, 'web/eval_scene.mjs no longer states the measured hall baseline'
BASE_CALLS = int(_hall.group(1).replace('_', ''))
BASE_TRIS = int(_hall.group(2).replace('_', ''))
BASE_MESHES = int(_hall.group(3).replace('_', ''))
CALL_HEADROOM = float(eval_num(r'const CALL_HEADROOM = ([\d.]+);',
                               'the draw-call headroom'))
TRI_HEADROOM = float(eval_num(r'const TRI_HEADROOM = ([\d.]+);',
                              'the triangle headroom'))
MESH_FLOOR = float(eval_num(r'const MESH_FLOOR = ([\d.]+);',
                            'the visible-mesh floor'))

# the eval's own arithmetic, reproduced exactly (JS Math.round, not Python's
# banker's rounding — they disagree on .5 and that is how a ceiling drifts)
def jsround(x):
    return math.floor(x + 0.5)


HALL_MAX_CALLS = jsround(BASE_CALLS * CALL_HEADROOM)
HALL_MAX_TRIS = int(BASE_TRIS * TRI_HEADROOM)
HALL_MIN_MESHES = jsround(BASE_MESHES * MESH_FLOOR)
CALL_HEADROOM_LEFT = HALL_MAX_CALLS - BASE_CALLS
TRI_HEADROOM_LEFT = HALL_MAX_TRIS - BASE_TRIS
assert CALL_HEADROOM_LEFT > 0 and TRI_HEADROOM_LEFT > 0, \
    'the hall view is already at its own ceiling; props cannot be added'

MEASURED_BASELINE = {
    'view': 'hall',
    'draw_calls': BASE_CALLS,
    'triangles': BASE_TRIS,
    'visible_meshes': BASE_MESHES,
    'provenance': 'MEASURED-ELSEWHERE',
    'source': 'web/eval_scene.mjs BASE',
    'how': 'measured 2026-09-22 in Chromium/SwiftShader at 1280x800 on '
           'quality rung high, by the eval this builder reads but does not '
           'run — verify_all.sh opens no browser and neither does this file',
    'why_it_is_here': 'it says which currency is scarce. A hall spends '
                      f'{BASE_CALLS} of {HALL_MAX_CALLS} permitted draw calls '
                      f'and {BASE_TRIS:,} of {HALL_MAX_TRIS:,} permitted '
                      'triangles, so the draw call is the expensive one and '
                      'the triangle is not.',
}

# ---------------------------------------------------------------------------
# The room table, imported. Nothing below retypes a label, a purpose or a
# footprint: `interiors.ROOMS` owns all three and this is the only shape
# this file keeps of them.
# ---------------------------------------------------------------------------
STRANDS = [r[0] for r in ROOMS]
ROOM_OF = {r[0]: {'label': r[1], 'w': r[2], 'h': r[3], 'purpose': r[4]}
           for r in ROOMS}
assert len(ROOM_OF) == 11, 'the interiors module no longer declares 11 rooms'

# The real plans, built by the module that owns the packing, so the SMALLEST
# room that a prop has to fit into is the smallest one that actually gets
# built — not the nominal footprint, which interiors.py widens for long
# labels, for a trade's fixtures and to square off a row.
from interiors import build as build_interiors  # noqa: E402


def _hall_states(slug):
    doc = json.load(open(ROOT / f'pack/registry/halls/{slug}.json'))
    c = {'live': 0, 'calibrating': 0, 'schema_ok': 0, 'draft': 0}
    for lv in doc['levels']:
        c[lv['state']] += 1
    return c


_census = {h['slug']: _hall_states(h['slug']) for h in HALLS}
_per_level = LEDGER['slots_per_level'] * LEDGER['variants_per_lesson']
PLANS = build_interiors(HALLS, lambda i: {
    k: v * _per_level for k, v in _census[HALLS[i]['slug']].items()})
assert len(PLANS) == len(HALLS)

# every built room, as (hall slug, strand, w units, h units)
BUILT_ROOMS = [(slug, r['strand'], r['w'], r['h'])
               for slug, p in PLANS.items() for r in p['rooms']]
assert len(BUILT_ROOMS) == len(HALLS) * 11

# A room is never built NARROWER than the table says, because interiors.py
# only ever widens. If that stops being true, every fit computed below is
# computed against the wrong room.
for slug, strand, w, h in BUILT_ROOMS:
    nominal = ROOM_OF[strand]
    assert w >= max(nominal['w'], min_units(nominal['label'])), \
        f'{slug}/{strand}: built {w} units, narrower than the table allows'
    assert h == nominal['h'], f'{slug}/{strand}: depth drifted from the table'
    assert w <= GRID, f'{slug}/{strand}: wider than the envelope'

SMALLEST = {}
for slug, strand, w, h in BUILT_ROOMS:
    cur = SMALLEST.get(strand)
    if cur is None or (w, h) < cur:
        SMALLEST[strand] = (w, h)
assert set(SMALLEST) == set(STRANDS)

# ---------------------------------------------------------------------------
# The conditions record, read. This is the only source of a hazard, a PPE
# item or an illuminance figure anywhere in this pack.
# ---------------------------------------------------------------------------
COND = {slug: h['conditions'] for slug, h in FINISHES['halls'].items()}
assert set(COND) == {h['slug'] for h in HALLS}, \
    'the surfaces registry and the hall roster disagree about which halls exist'
for slug, rooms in COND.items():
    assert set(rooms) == set(STRANDS), f'{slug}: conditions are not per strand'

PPE_VOCAB = set()
HAZARD_VOCAB = set()
for rooms in COND.values():
    for c in rooms.values():
        PPE_VOCAB.update(c['ppe'])
        HAZARD_VOCAB.update(c['hazards'])
assert PPE_VOCAB and HAZARD_VOCAB


# ---------------------------------------------------------------------------
# Primitives. This bundle loads no meshes — it builds from boxGeo() and
# THREE.CylinderGeometry and nothing else — so the triangle count of a prop
# is arithmetic, not an estimate.
#
#   a box                      : 12 triangles   (2 per face, 6 faces)
#   a capped cylinder, N sides : 4N triangles   (2N side + N + N caps)
#   an open cylinder, N sides  : 2N triangles   (side only)
#
# Verified against the VENDORED three.js in web/vendor by props/test.mjs,
# which builds the real geometries and counts their indices, so the formula
# cannot quietly drift from the library the page actually runs.
# ---------------------------------------------------------------------------
TRI_BOX = 12


def B(part, size, at, count=1):
    return {'part': part, 'prim': 'box', 'size': [round(v, 3) for v in size],
            'at': [round(v, 3) for v in at], 'count': count}


def C(part, r, h, seg, at, capped=True, count=1):
    return {'part': part, 'prim': 'cylinder', 'r': r, 'h': h,
            'radial_segments': seg, 'capped': capped,
            'at': [round(v, 3) for v in at], 'count': count}


def tris_of(parts):
    n = 0
    for p in parts:
        if p['prim'] == 'box':
            n += TRI_BOX * p['count']
        elif p['prim'] == 'cylinder':
            per = 4 * p['radial_segments'] if p['capped'] \
                else 2 * p['radial_segments']
            n += per * p['count']
        else:
            raise AssertionError(f'{p["part"]}: this bundle has no {p["prim"]}')
    return n


# The measured band. 46 and 104 are the median mesh sizes of the two
# reference interiors that read as places; they are the FLOOR at which a
# piece still reads as a thing, not a ceiling to undercut, because the eval
# leaves this view thousands of unused triangles and the arithmetic for how
# many is done above rather than written here. 250 is this pack's own upper
# bound: past it a prop is a model, and a model wants an artist rather than
# a recipe.
TRI_FLOOR, TRI_CEIL = 40, 250
TRI_WHY = (f'{TRI_FLOOR}-{TRI_CEIL} tri. The two reference interiors that '
           f'read as places have a median mesh of 46 and 104 triangles, so '
           f'46-104 is the size at which a piece reads as a thing; this '
           f'prop is built to sit in or above that band rather than under '
           f'it, because the hall the eval measured spends {BASE_TRIS:,} of '
           f'{HALL_MAX_TRIS:,} permitted triangles and triangles are the '
           f'currency that is not scarce here.')


# ---------------------------------------------------------------------------
# THE TOOL CRIB, READ. tools/registry/toolcribs.json owns the eight district
# cribs and every tool in them: an id, a name, a use sentence. Nothing about
# a tool is retyped here. A piece of furniture that says it holds a tool
# names the tool BY ID, and the build stops on an id no crib carries.
# ---------------------------------------------------------------------------
UNIONS = json.load(open(ROOT / 'unions/registry/unions.json'))
assert UNIONS['pack_version'] == PACK_VERSION, \
    'one bundle version: the unions registry is a different build'

CRIB_TOOL = {}
for _d, _crib in CRIBS['cribs'].items():
    for _t in _crib['tools']:
        assert _t['id'] not in CRIB_TOOL, \
            f'{_t["id"]} is carried by two cribs; a tool id is one truth'
        CRIB_TOOL[_t['id']] = {'id': _t['id'], 'name': _t['name'],
                               'use': _t['use'], 'district': _d,
                               'crib': _crib['name']}
DISTRICTS = sorted(CRIBS['cribs'])
HALL_DISTRICT = {u['slug']: u['district'] for u in UNIONS['unions']}
assert set(HALL_DISTRICT.values()) == set(DISTRICTS), \
    'the unions roster and the tool cribs disagree about which districts exist'
assert set(HALL_DISTRICT) == {h['slug'] for h in HALLS}, \
    'the unions roster and the hall roster disagree about which halls exist'

FAMILIES = {
    'bench':          'a horizontal surface work happens on top of',
    'storage':        'something that holds what a room keeps between sessions',
    'board':          'a vertical surface a room reads from',
    'seat':           'something a person is off their feet on',
    'vessel':         'an open container things go into and come out of',
    'stand':          'a freestanding upright a piece of apparatus lives on',
    'stock':          'the material a trade works on, held the way that trade '
                      'holds it before it is cut, bent, spliced or set',
    'waste':          'what the work leaves behind, kept where the trade keeps '
                      'it rather than swept out of the render',
    'machine':        'a schematic device the work is driven through — a shape '
                      'with a bed, a head and a control, not a machine '
                      'specification and not any manufacturer\'s model',
    'screen':         'a vertical barrier that stops an arc, a spark, a splash '
                      'or a line of sight',
    'trolley':        'something the work is moved on rather than carried',
    'safety-fixture': 'a schematic shape standing where a room record asks '
                      'for protective equipment — not a specification',
}

ANCHORS = {
    'side-wall':    'stands on the floor along a left or right partition',
    'back-corner':  'stands on the floor in one back corner, clear of the '
                    'fixture bench band',
    'wall-mounted': 'hangs on a left or right partition, its top no higher '
                    'than the partition itself',
}

MERGES = {
    'pooled':    'its geometry is translated into hall space and merged by '
                 'material with every other pooled prop in the hall, one mesh '
                 'per material for all eleven rooms',
    'instanced': 'the same geometry repeats in many rooms of a hall, so it '
                 'draws once as an InstancedMesh however many rooms have it',
    'own-mesh':  'RESERVED. Only for a prop the hover/click raycast reads or '
                 'one that moves; a prop that claims it must name the list it '
                 'joins, because an unpooled prop is a whole draw call',
}

# The seven materials the props already merge into. THE VOCABULARY MAY NOT
# GROW PAST THIS SET, and that is the whole draw-call argument: a pooled
# prop costs no draw call of its own, but the FIRST prop to name an eighth
# material costs one mesh per hall for ever after. Three hundred pieces of
# furniture that share these seven are seven merged meshes; three hundred
# that each wanted their own colour would be three hundred draw calls
# against a ceiling of thirty-nine.
MATERIALS = ('wood', 'steel', 'metal', 'paint', 'part', 'post', 'cone')
for _m in MATERIALS:
    assert _m in PAGE_MATERIALS, \
        f'mat.{_m} is not a material web/build_3d.py builds'
MATERIALS_WHY = (
    'every prop in this pack names one of seven keys of the page\'s own '
    'shared material table. A pooled prop of a material the pack already '
    'uses is free at the draw call; the first prop to name an eighth '
    'material would add one merged mesh to every hall in the bundle. The '
    'vocabulary grew from twenty-nine pieces to three hundred without '
    'naming one.')


def B(part, size, at, count=1):
    return {'part': part, 'prim': 'box', 'size': [round(v, 3) for v in size],
            'at': [round(v, 3) for v in at], 'count': count}


def C(part, r, h, seg, at, capped=True, count=1):
    return {'part': part, 'prim': 'cylinder', 'r': r, 'h': h,
            'radial_segments': seg, 'capped': capped,
            'at': [round(v, 3) for v in at], 'count': count}


def tris_of(parts):
    n = 0
    for p in parts:
        if p['prim'] == 'box':
            n += TRI_BOX * p['count']
        elif p['prim'] == 'cylinder':
            per = 4 * p['radial_segments'] if p['capped'] \
                else 2 * p['radial_segments']
            n += per * p['count']
        else:
            raise AssertionError(f'{p["part"]}: this bundle has no {p["prim"]}')
    return n


def prop(pid, name, family, tokens, hazard_trigger, size_m, parts, material,
         merges, merges_why, anchor, walls, base_y, max_per_room, approach,
         why, crib_tools=(), district=None, catalogue='hall', form=None):
    """One prop. Everything derivable is derived here rather than typed."""
    tris = tris_of(parts)
    boxes = sum(p['count'] for p in parts if p['prim'] == 'box')
    cyls = [p for p in parts if p['prim'] == 'cylinder']
    formula = f'12 x {boxes} box'
    for c in cyls:
        formula += (f' + {4 if c["capped"] else 2} x {c["radial_segments"]} '
                    f'x {c["count"]} {"capped" if c["capped"] else "open"} '
                    f'cylinder')
    formula += f' = {tris}'
    # POLICY, both derived from the page's own body radius: a walker gets a
    # whole body width to pass anything, and a prop you have to stand AT
    # gets another half body on top so the person using it is not in the way.
    clearance = round(2 * BODY_R + (BODY_R if approach else 0.0), 3)
    for t in crib_tools:
        assert t in CRIB_TOOL, (
            f'{pid} says it holds "{t}" and no district tool crib carries a '
            f'tool of that id. tools/registry/toolcribs.json is the only '
            f'roster of tools in this bundle and furniture may not invent one')
    rec = {
        'id': pid, 'name': name, 'family': family,
        'why': why,
        'catalogue': catalogue,
        'form': form,
        'provenance': {'geometry': 'SCHEMATIC', 'vocabulary': 'AUTHORED',
                       'placement': 'DERIVED'},
        'tri_budget': {'tris': tris, 'floor': TRI_FLOOR, 'ceiling': TRI_CEIL,
                       'why': TRI_WHY},
        'size_m': [round(v, 3) for v in size_m],
        'recipe': {'primitives_only': ['box', 'cylinder'],
                   'loads_no_mesh': True,
                   'parts': parts,
                   'box_count': boxes,
                   'cylinder_count': sum(c['count'] for c in cyls),
                   'formula': formula, 'tris': tris},
        'material': material,
        'merges': merges, 'merges_why': merges_why,
        'clearance_m': clearance,
        'approach': approach,
        'derive': ({'from': 'room.purpose', 'tokens': tokens}
                   if tokens is not None
                   else {'from': 'room.conditions.ppe',
                         'ppe_any': hazard_trigger}),
        'layout': {
            'anchor': anchor, 'anchor_is': ANCHORS[anchor],
            'walls': walls,
            'base_y_m': round(base_y, 3),
            'gap_m': GAP_M,
            'front_clear_m': round(FRONT_CLEAR_M, 3),
            'back_reserve_m': round(BACK_RESERVE_M, 3),
            'max_per_room': max_per_room,
            'count_rule': 'min(max_per_room, walls x floor((run_m + gap_m) / '
                          '(size_m[0] + gap_m))), run_m = room depth in metres '
                          '- floor inset - front_clear_m - back_reserve_m',
        },
    }
    if crib_tools:
        rec['crib'] = {
            'source': 'tools/registry/toolcribs.json',
            'tools': [{'id': t, 'name': CRIB_TOOL[t]['name'],
                       'district': CRIB_TOOL[t]['district'],
                       'crib': CRIB_TOOL[t]['crib'],
                       'use': CRIB_TOOL[t]['use']} for t in crib_tools],
        }
    if district is not None:
        assert district in DISTRICTS, f'{pid}: {district} is not a district'
        rec['district'] = district
    return rec


F = FLOOR_TOP    # everything that stands on the floor starts here

# ---------------------------------------------------------------------------
# THE FORMS. Three hundred pieces of furniture are not three hundred
# hand-placed part lists, and they are not one box recoloured three hundred
# times either. They are built from the shapes below: a bench is a top, four
# legs and a shelf; a rack is two uprights and N shelves; a vice bench is a
# bench with a screw and a jaw on it; a spool stand is a frame with a drum
# through it. Each form takes its own dimensions and its own part counts, so
# two pieces sharing a form differ in silhouette, in footprint and in
# triangles, and the registry publishes which form every piece was cut from
# so a reader can count them.
#
# Every position obeys the page's own propPartAt() spreading rule, which is
# written once in web/build_3d.py and never restated here: count 2 off the x
# axis mirrors across it, count 4 off both axes goes to the corners, a run
# that starts left of centre spreads to the right, and anything else stacks
# up the piece's own height. A form that ignored it would build a rack whose
# shelves were all in the same place.
# ---------------------------------------------------------------------------
def fm_bench(w, d, h=.86, shelf=True, kick=False):
    t, lg = .07, .08
    p = [B('top', [w, t, d], [0, F + h - t / 2, 0]),
         B('leg', [lg, h - t, lg], [w / 2 - lg, F + (h - t) / 2, d / 2 - lg], 4)]
    if shelf:
        p.append(B('under shelf', [w - .12, .04, d - .12], [0, F + .26, 0]))
    if kick:
        p.append(B('kick rail', [w - .12, .10, .05], [0, F + .06, -(d / 2 - .04)]))
    return [w, h, d], p


def fm_vice_bench(w, d, h=.90):
    _, p = fm_bench(w, d, h, shelf=True, kick=True)
    x = w / 2 - .32
    p += [B('vice body', [.16, .18, .22], [x, F + h + .09, 0]),
          B('vice jaw', [.22, .10, .05], [x, F + h + .16, .12]),
          B('vice slide', [.10, .06, .30], [x, F + h + .06, -.06]),
          C('vice handle', .02, .30, 6, [x, F + h + .15, .02])]
    return [w, h + .30, d], p


def fm_rack(w, h, d, shelves):
    return [w, h, d], [
        B('upright', [.09, h, .09], [w / 2 - .045, F + h / 2, 0], 2),
        B('shelf', [w, .06, d - .10], [0, F + .34, 0], shelves),
        B('brace', [w, .05, .05], [0, F + h - .06, d / 2 - .04], 2),
        B('foot', [w, .06, d], [0, F + .03, 0])]


def fm_cantilever(w, h, d, arms):
    return [w, h, d], [
        B('column', [.12, h, .12], [0, F + h / 2, 0]),
        B('arm', [w, .07, d - .08], [0, F + .45, 0], arms),
        B('back plate', [w * .6, .10, .05], [0, F + h - .08, -(d / 2 - .03)]),
        B('base plate', [w * .5, .06, d], [0, F + .03, 0])]


def fm_cabinet(w, h, d, doors=2, label=False):
    p = [B('carcass', [w - .04, h - .06, d - .04], [0, F + h / 2, 0]),
         B('plinth', [w - .04, .08, d - .08], [0, F + .04, 0]),
         B('top cap', [w, .04, d], [0, F + h - .02, 0])]
    if doors == 2:
        p += [B('door', [(w - .10) / 2, h - .18, .03], [w / 4 - .02, F + h / 2, d / 2 - .01], 2),
              B('handle', [.03, .18, .03], [.03, F + h / 2, d / 2 + .01], 2)]
    else:
        p += [B('door', [w - .10, h - .18, .03], [0, F + h / 2, d / 2 - .01]),
              B('handle', [.03, .18, .03], [w / 2 - .12, F + h / 2, d / 2 + .01])]
    if label:
        p.append(B('label plate', [w * .45, .10, .01], [0, F + h - .18, d / 2 + .01]))
    return [w, h, d], p


def fm_drawers(w, h, d, n):
    assert n >= 3, 'a drawer stack spreads up its own height and needs three'
    return [w, h, d], [
        B('carcass', [w, h - .04, d], [0, F + h / 2, 0]),
        B('drawer front', [w - .06, (h - .26) / n, .03], [0, F + .22, d / 2 + .01], n),
        B('pull', [w * .3, .03, .02], [0, F + .24, d / 2 + .03], n),
        B('plinth', [w, .08, d - .04], [0, F + .04, 0]),
        B('top cap', [w, .04, d], [0, F + h - .02, 0])]


def fm_bin(w, h, d, lid=False):
    p = [B('side', [w, h - .06, .03], [0, F + h / 2, d / 2 - .015], 2),
         B('end', [.03, h - .06, d], [w / 2 - .015, F + h / 2, 0], 2),
         B('base', [w, .04, d], [0, F + .02, 0]),
         B('lip rail', [w, .04, .04], [0, F + h - .02, d / 2 - .02], 2)]
    if lid:
        p.append(B('lid', [w - .04, .03, d - .04], [0, F + h + .02, 0]))
    return [w, h + (.05 if lid else 0), d], p


def fm_drum(r, h, seg=12):
    return [2 * r, h, 2 * r], [
        C('body', r, h - .08, seg, [0, F + h / 2, 0], capped=False),
        C('rim', r + .02, .05, seg, [0, F + h - .03, 0]),
        B('base tray', [2 * r - .06, .05, 2 * r - .06], [0, F + .025, 0])]


def fm_stool(r, h):
    return [2 * r, h, 2 * r], [
        C('seat pad', r * .8, .07, 10, [0, F + h - .04, 0]),
        C('column', .045, h - .12, 8, [0, F + h / 2, 0], capped=False),
        C('base', r, .05, 10, [0, F + .03, 0])]


def fm_pedestal(r, h, head, readout=True):
    p = [C('column', .05, h - .30, 8, [0, F + (h - .30) / 2, 0]),
         C('foot', r, .06, 10, [0, F + .03, 0]),
         B('head', head, [0, F + h - head[1] / 2, 0])]
    if readout:
        p.append(B('readout', [head[0] * .6, .09, .02],
                   [0, F + h - head[1] / 2, head[2] / 2 + .01]))
    return [max(2 * r, head[0]), h, max(2 * r, head[2])], p


def fm_screen(w, h, panels):
    assert panels >= 2
    return [w, h, .22], [
        C('post', .05, h - .06, 8, [w / 2 - .05, F + h / 2, 0], count=2),
        B('panel', [w / panels - .04, h - .30, .02],
          [-(w / 2 - w / (2 * panels)), F + h / 2 + .06, 0], panels),
        B('foot', [.22, .04, .26], [w / 2 - .05, F + .02, 0], 2)]


def fm_trestle(w, h, d):
    return [w, h, d], [
        B('top rail', [w, .12, d * .4], [0, F + h - .06, 0]),
        B('leg', [.09, h - .12, .09], [w / 2 - .12, F + (h - .12) / 2, d / 2 - .06], 4),
        B('brace', [w - .25, .06, .06], [0, F + .28, d / 2 - .06], 2)]


def fm_spool(w, h, r):
    return [max(w, 2 * r), h, max(.34, 2 * r)], [
        B('upright', [.08, h, .12], [w / 2 - .04, F + h / 2, 0], 2),
        B('cross rail', [w, .06, .10], [0, F + h - .04, 0]),
        C('drum', r, h * .55, 10, [0, F + h * .34, 0], capped=False),
        C('flange', r + .04, .03, 10, [0, F + h * .06, 0]),
        B('foot', [w, .06, max(.34, 2 * r)], [0, F + .03, 0])]


def fm_pipe_rack(w, h, d, bays):
    assert bays >= 2
    return [w, h, d], [
        B('upright', [.09, h, .09], [w / 2 - .045, F + h / 2, 0], 2),
        B('divider', [.05, h * .6, d - .08], [-(w / 2 - .12), F + h * .32, 0], bays),
        C('stock length', .05, h * .85, 8, [-(w / 2 - .14), F + h * .45, 0], count=bays),
        B('kerb', [w, .10, d], [0, F + .05, 0])]


def fm_gang_box(w, h, d):
    return [w, h, d], [
        B('body', [w, h - .12, d], [0, F + (h - .12) / 2 + .06, 0]),
        B('lid', [w + .02, .06, d + .02], [0, F + h - .03, 0]),
        B('hasp', [.10, .12, .03], [0, F + h - .16, d / 2 + .01]),
        B('skid', [w, .06, .10], [0, F + .03, d / 2 - .08], 2),
        B('end handle', [.04, .10, .16], [w / 2 - .02, F + h - .22, 0], 2)]


def fm_drying_rack(w, h, bars):
    return [w, h, .40], [
        B('upright', [.07, h, .07], [w / 2 - .035, F + h / 2, 0], 2),
        B('bar', [w - .08, .05, .05], [0, F + .55, 0], bars),
        B('foot', [.10, .05, .40], [w / 2 - .05, F + .025, 0], 2),
        B('drip tray', [w, .04, .34], [0, F + .06, 0])]


def fm_oven(w, h, d):
    bh = h - .50
    return [w, h, d], [
        B('body', [w, bh, d], [0, F + .28 + bh / 2, 0]),
        B('door', [w - .12, bh - .16, .03], [0, F + .28 + bh / 2, d / 2 + .01]),
        C('dial', .05, .03, 10, [w / 2 - .12, F + .28 + bh - .10, d / 2 + .02]),
        B('leg', [.07, .28, .07], [w / 2 - .07, F + .14, d / 2 - .07], 4),
        C('flue', .04, .20, 8, [0, F + h - .10, -(d / 2 - .08)])]


def fm_cart(w, h, d):
    return [w, h, d], [
        B('deck', [w, .05, d], [0, F + .30, 0]),
        B('lower shelf', [w - .08, .04, d - .08], [0, F + .16, 0]),
        B('post', [.05, h - .30, .05], [w / 2 - .04, F + .30 + (h - .30) / 2, -(d / 2 - .04)], 2),
        B('push bar', [w, .05, .05], [0, F + h - .03, -(d / 2 - .04)]),
        C('caster', .05, .05, 8, [w / 2 - .09, F + .05, d / 2 - .09], count=4)]


def fm_cradle(w, h, d):
    return [w, h, d], [
        B('base', [w, .08, d], [0, F + .04, 0]),
        B('vee arm', [.06, h - .10, d * .8], [w / 2 - .10, F + h / 2, 0], 2),
        B('stop', [w, .05, .05], [0, F + h - .06, d / 2 - .04], 2),
        B('held stock', [w - .14, .10, .10], [0, F + h - .16, 0])]


def fm_press(w, h, d):
    return [w, h, d], [
        B('bed', [w, .10, d], [0, F + .74, 0]),
        B('frame upright', [.12, h - .10, .18], [w / 2 - .08, F + (h - .10) / 2, -(d / 2 - .10)], 2),
        B('crown', [w, .12, .20], [0, F + h - .06, -(d / 2 - .10)]),
        B('ram', [w - .30, .12, .10], [0, F + .92, 0]),
        B('control box', [.16, .22, .10], [w / 2 - .14, F + 1.05, d / 2 - .08]),
        B('leg', [.12, .74, .16], [w / 2 - .08, F + .37, d / 2 - .12], 4)]


def fm_sink(w, h, d):
    return [w, h + .39, d], [
        B('basin', [w, .22, d], [0, F + h - .11, 0]),
        B('leg', [.07, h - .22, .07], [w / 2 - .08, F + (h - .22) / 2, d / 2 - .08], 4),
        B('splash back', [w, .26, .03], [0, F + h + .13, -(d / 2 - .02)]),
        C('tap', .02, .26, 6, [0, F + h + .13, -(d / 2 - .06)]),
        C('waste', .05, .10, 8, [0, F + h - .26, 0])]


def fm_locker(w, h, d, bays):
    assert bays >= 2
    return [w, h, d], [
        B('carcass', [w, h - .10, d], [0, F + .10 + (h - .10) / 2, 0]),
        B('door', [w / bays - .04, h - .26, .03], [-(w / 2 - w / (2 * bays)), F + h / 2 + .04, d / 2 + .01], bays),
        B('vent slot', [w / bays - .16, .04, .01], [-(w / 2 - w / (2 * bays)), F + h - .14, d / 2 + .03], bays),
        B('plinth', [w, .10, d - .04], [0, F + .05, 0])]


def fm_tree(h, arms, r=.30):
    return [2 * r, h, 2 * r], [
        C('base', r, .06, 10, [0, F + .03, 0]),
        C('column', .06, h - .14, 8, [0, F + (h - .14) / 2 + .06, 0]),
        B('arm', [2 * r, .05, .05], [0, F + .55, 0], arms),
        C('cap', .08, .04, 8, [0, F + h - .02, 0])]


def fm_table(w, d, h=.78, rail=True):
    p = [B('top', [w, .06, d], [0, F + h - .03, 0]),
         B('leg', [.07, h - .06, .07], [w / 2 - .09, F + (h - .06) / 2, d / 2 - .09], 4)]
    if rail:
        p.append(B('rail', [w - .18, .05, .05], [0, F + .22, d / 2 - .09], 2))
    return [w, h, d], p


def fm_reel(w, h, r):
    return [max(w, 2 * r), h, max(.34, 2 * r)], [
        B('frame side', [.07, h, .12], [w / 2 - .035, F + h / 2, 0], 2),
        B('frame rail', [w, .06, .10], [0, F + h * .20, 0], 2),
        C('drum', r * .5, h * .5, 8, [0, F + h * .42, 0], capped=False),
        C('flange', r, .03, 10, [0, F + h * .20, 0], count=2),
        C('crank knob', .04, .10, 6, [0, F + h * .66, 0])]


def fm_crates(w, h, d, n):
    return [w, h, d], [
        B('skid', [w, .08, d], [0, F + .04, 0]),
        B('crate', [w - .04, (h - .08) / n - .02, d - .04], [0, F + .08 + ((h - .08) / n) / 2, 0], n),
        B('band', [w - .02, .02, d - .02], [0, F + .14, 0], n)]


def fm_tank(r, h, seg=10):
    return [2 * r, h, 2 * r], [
        C('shell', r, h - .30, seg, [0, F + .30 + (h - .30) / 2, 0]),
        C('dome', r * .8, .10, seg, [0, F + h - .02, 0]),
        B('leg', [.08, .30, .08], [r - .08, F + .15, r - .08], 4),
        B('valve block', [.12, .12, .10], [0, F + .44, r - .02])]


def fm_easel(w, h):
    return [w, h, .44], [
        B('leg', [.06, h, .06], [w / 2 - .06, F + h / 2, .18], 4),
        B('panel', [w - .10, h * .55, .03], [0, F + h - h * .30, -.02]),
        B('tray', [w - .10, .05, .12], [0, F + h - h * .58, .04]),
        B('brace', [w - .16, .05, .05], [0, F + .24, .18], 2)]


def fm_pallet(w, h, d, n):
    return [w, h, d], [
        B('bearer', [w, .07, .10], [0, F + .035, d / 2 - .08], 2),
        B('deck board', [w, .05, d], [0, F + .10, 0], n),
        B('corner block', [.10, .07, .10], [w / 2 - .06, F + .035, d / 2 - .06], 4)]


def fm_hopper(w, h, d):
    return [w, h, d], [
        B('chute side', [w, h * .5, .03], [0, F + h * .72, d / 2 - .02], 2),
        B('chute end', [.03, h * .5, d], [w / 2 - .02, F + h * .72, 0], 2),
        B('body', [w - .06, h * .45, d - .06], [0, F + h * .24, 0]),
        B('leg', [.06, h * .45, .06], [w / 2 - .08, F + h * .22, d / 2 - .08], 4)]


# ---- wall forms. These hang, so every position is measured from the piece's
# ---- own centre and the base_y the layout declares is where that centre sits.
def fw_board(w, h, cards=0, tray=False):
    p = [B('panel', [w - .04, h - .06, .04], [0, 0, 0]),
         B('frame rail', [w, .05, .06], [0, -(h / 2 - .025), 0], 2),
         B('stile', [.05, h - .06, .06], [(w - .05) / 2, 0, 0], 2)]
    if cards:
        p.append(B('card', [w * .22, h * .22, .01], [-(w * .3), h * .08, .03], cards))
    if tray:
        p.append(B('marker tray', [w - .12, .05, .08], [0, -(h / 2 - .02), .05]))
    return [w, h, .08 if tray else .06], p


def fw_shelf(w, h, d, shelves):
    return [w, h, d], [
        B('back panel', [w, h, .03], [0, 0, -(d / 2 - .015)]),
        B('shelf', [w - .06, .04, d - .04], [0, -(h / 2 - .10), 0], shelves),
        B('end', [.03, h, d], [(w - .03) / 2, 0, 0], 2),
        B('top cap', [w, .03, d], [0, h / 2 - .015, 0])]


def fw_pegboard(w, h, hooks):
    return [w, h, .12], [
        B('panel', [w, h, .03], [0, 0, 0]),
        B('batten', [w, .05, .04], [0, -(h / 2 - .025), .01], 2),
        B('hook', [.03, .09, .06], [-(w / 2 - .12), h * .12, .05], hooks),
        B('hung tool', [.05, h * .30, .03], [-(w / 2 - .12), -(h * .10), .07], hooks)]


def fw_cradle(w, h):
    return [w, h, .22], [
        B('back plate', [w, h, .03], [0, 0, 0]),
        B('bracket', [.06, h - .08, .18], [w / 2 - .08, 0, .10], 2),
        B('retaining bar', [w, .04, .04], [0, -(h / 2 - .06), .18]),
        B('held stock', [w - .16, .08, .08], [0, .02, .12])]


def fw_cabinet(w, h, d):
    return [w, h, d], [
        B('carcass', [w, h, d - .03], [0, 0, 0]),
        B('door', [w - .05, h - .06, .03], [0, 0, d / 2 - .01]),
        B('handle', [.03, .12, .03], [w / 2 - .09, 0, d / 2 + .01]),
        B('label plate', [w * .5, .10, .01], [0, h / 2 - .10, d / 2 + .01]),
        B('hinge', [.03, .07, .03], [-(w / 2 - .03), h * .26, d / 2 - .02], 2)]


def fw_reel(w, h, r):
    return [w, h, 2 * r + .1], [
        B('back plate', [w, h, .03], [0, 0, 0]),
        B('bracket arm', [.05, .10, 2 * r], [w / 2 - .06, 0, r], 2),
        C('drum', r * .55, h * .6, 8, [0, 0, r], capped=False),
        C('flange', r, .03, 10, [0, -(h * .22), r], count=2),
        B('nozzle clip', [.07, .10, .05], [0, -(h / 2 - .06), .06])]


FORMS = {
    'bench': fm_bench, 'vice-bench': fm_vice_bench, 'rack': fm_rack,
    'cantilever': fm_cantilever, 'cabinet': fm_cabinet, 'drawers': fm_drawers,
    'bin': fm_bin, 'drum': fm_drum, 'stool': fm_stool, 'pedestal': fm_pedestal,
    'screen': fm_screen, 'trestle': fm_trestle, 'spool': fm_spool,
    'pipe-rack': fm_pipe_rack, 'gang-box': fm_gang_box,
    'drying-rack': fm_drying_rack, 'oven': fm_oven, 'cart': fm_cart,
    'cradle': fm_cradle, 'press': fm_press, 'sink': fm_sink,
    'locker': fm_locker, 'tree': fm_tree, 'table': fm_table, 'reel': fm_reel,
    'crates': fm_crates, 'tank': fm_tank, 'easel': fm_easel,
    'pallet': fm_pallet, 'hopper': fm_hopper,
    'wall-board': fw_board, 'wall-shelf': fw_shelf, 'wall-peg': fw_pegboard,
    'wall-cradle': fw_cradle, 'wall-cabinet': fw_cabinet,
    'wall-reel': fw_reel,
}
WALL_FORMS = {k for k in FORMS if k.startswith('wall-')}

# The height a wall-mounted piece hangs at: the midpoint between the floor
# the page draws and the top of the partition it hangs on. Both numbers are
# read from web/build_3d.py at the top of this file, so nothing here picks a
# hanging height by eye.
HANG_Y = (FLOOR_TOP + PART_TOP) / 2
WALL_MAX_H = 2 * min(HANG_Y - FLOOR_TOP, PART_TOP - HANG_Y)

_SEEN = set()
FORM_USED = set()


def piece(pid, name, family, form, args, material, why, *,
          tokens=None, ppe=None, anchor='side-wall', walls=('left',),
          max_per_room=1, approach=True, merges='pooled', crib_tools=(),
          district=None, catalogue='hall'):
    """A piece of furniture, cut from a form and sized here.

    The merge reason is COMPUTED from the recipe rather than written: it is
    the same sentence for every pooled piece because it is the same fact —
    n primitives of one material joining a mesh that already exists.
    """
    assert pid not in _SEEN, f'{pid} is declared twice'
    _SEEN.add(pid)
    assert form in FORMS, f'{pid}: {form} is not a form this pack cuts'
    size, parts = FORMS[form](*args)
    FORM_USED.add(form)
    wall = anchor == 'wall-mounted'
    assert wall == (form in WALL_FORMS), \
        (f'{pid}: {form} is a {"wall" if form in WALL_FORMS else "floor"} form '
         f'and the piece anchors as {anchor}')
    if wall:
        assert size[1] <= WALL_MAX_H + 1e-9, \
            (f'{pid}: {size[1]:.2f} m tall hanging at {HANG_Y:.2f} m would '
             f'pass the partition or the floor')
    boxes = sum(p['count'] for p in parts if p['prim'] == 'box')
    cyls = sum(p['count'] for p in parts if p['prim'] == 'cylinder')
    if merges == 'pooled':
        mw = (f'{boxes} boxes and {cyls} cylinders of mat.{material}, cut from '
              f'the {form} form; it is translated into hall space and merged '
              f'into the one {material} mesh this hall already builds for its '
              f'props, so it adds no draw call of its own')
    else:
        mw = (f'the same {boxes} boxes and {cyls} cylinders of mat.{material} '
              f'stand in many rooms of every hall, so one InstancedMesh draws '
              f'every copy in the hall in a single call')
    # WALLS ARE A PREFERENCE, NOT A RESERVATION. A room has two partitions
    # and the pieces standing against them are filled from the doorway end in
    # one order, so the fifth piece into a room finds the wall it would have
    # liked already full. Every piece therefore names the partition it would
    # rather have FIRST and the other one second, which is the difference
    # between a catalogue whose later entries never stand anywhere and one
    # whose later entries stand on the other side of the room.
    both = list(walls) + [w for w in ('left', 'right') if w not in walls]
    return prop(pid, name, family, list(tokens) if tokens else None,
                list(ppe) if ppe else None, size, parts, material, merges, mw,
                anchor, both, HANG_Y if wall else F, max_per_room,
                approach, why, crib_tools=tuple(crib_tools),
                district=district, catalogue=catalogue, form=form)


SCHEM = ('schematic — a shape standing where a room record asks for it, not '
         'a fixture specification and not evidence that anything has been '
         'provided')

# ---------------------------------------------------------------------------
# THE CONDITION FURNITURE. None of these declares a strand. Each one stands
# in a room because THAT ROOM'S OWN conditions record in
# surfaces/registry/finishes.json names the protective equipment it is keyed
# to, and the surfaces registry's own hazard table says which kind of work
# adds that equipment. That chain is computed below and published per piece,
# so "welding hood" is not a costume: it is the record's marker for hot work,
# and a room marked for hot work gets a rod oven and a screen.
#
# THIS IS WHERE ONE HALL STOPS LOOKING LIKE THE NEXT. The room table is the
# same eleven rooms in all 111 halls, so furniture placed from a room's
# PURPOSE is identical everywhere; the conditions record is per hall and per
# room, and 28 distinct hall-wide protective-equipment profiles fall out of
# it. These pieces are the ones that differ.
# ---------------------------------------------------------------------------
COND_PROPS = [
    piece('ppe-station', 'PPE station', 'safety-fixture', 'wall-peg',
          (1.0, 1.0, 4), 'paint',
          'the room record already says what this room requires of you and '
          'the page already hangs that list on the door; this is a '
          + SCHEM + '. It issues nothing and holds nothing',
          ppe=['*any*'], anchor='wall-mounted', walls=['right'],
          merges='instanced'),
    piece('eyewash-stand', 'Eyewash stand', 'safety-fixture', 'pedestal',
          (.16, 1.22, [.30, .16, .24]), 'post',
          'a shape standing where a room record says something can get in '
          'your eyes: ' + SCHEM,
          ppe=['chemical gloves', 'apron', 'face shield'],
          anchor='back-corner', walls=['right'], merges='instanced'),
    piece('extinguisher-bracket', 'Extinguisher bracket', 'safety-fixture',
          'wall-cradle', (.24, .62), 'cone',
          'a shape standing where a room record asks for flame-resistant or '
          'anti-static clothing: ' + SCHEM + ', and not a rated appliance',
          ppe=['flame-resistant clothing', 'anti-static clothing',
               'welding hood'],
          anchor='wall-mounted', walls=['left'], approach=False,
          merges='instanced'),
    piece('spill-kit-cabinet', 'Spill kit cabinet', 'safety-fixture',
          'cabinet', (.62, .88, .38, 1, True), 'cone',
          'a shape standing where a room record says something can be '
          'spilled: ' + SCHEM + '. It contains nothing',
          ppe=['chemical gloves', 'waterproof boots', 'coveralls'],
          anchor='back-corner', walls=['left'], merges='instanced'),
    piece('gas-monitor-dock', 'Gas monitor dock', 'safety-fixture',
          'wall-shelf', (.42, .46, .14, 2), 'metal',
          'a shape standing where a room record asks the person to carry a '
          'gas monitor: ' + SCHEM + '. It docks nothing and measures nothing',
          ppe=['gas monitor'], anchor='wall-mounted', walls=['right'],
          approach=False, merges='instanced'),

    # ---- hot work: the record asks for a welding hood ---------------------
    piece('rod-oven', 'Electrode rod oven', 'machine', 'oven',
          (.52, 1.10, .46), 'steel',
          'electrodes that have drunk the air do not run, so a room where '
          'arcs are struck keeps them warm and dry in a cabinet by the bay',
          ppe=['welding hood']),
    piece('weld-screen', 'Welding screen', 'screen', 'screen',
          (1.50, 1.75, 3), 'part',
          'the flash off an arc burns the eyes of somebody who never looked '
          'at it, so the bay is screened from the rest of the room',
          ppe=['welding hood'], walls=['right'], approach=False),
    piece('stub-bin', 'Electrode stub bin', 'waste', 'drum', (.24, .70),
          'metal',
          'a welder drops a stub every ninety seconds and they land hot; the '
          'bin for them is metal and it stands at the bay, not by the door',
          ppe=['welding hood'], anchor='back-corner', walls=['left']),

    # ---- hot work and molten metal: flame-resistant clothing --------------
    piece('fire-blanket-cabinet', 'Fire blanket cabinet', 'safety-fixture',
          'wall-cabinet', (.42, .48, .18), 'cone',
          'a shape hanging where a room record asks for flame-resistant '
          'clothing: ' + SCHEM,
          ppe=['flame-resistant clothing'], anchor='wall-mounted',
          walls=['right'], approach=False),
    piece('quench-tank', 'Quench tank', 'vessel', 'tank', (.34, .95), 'steel',
          'hot metal has to go somewhere between the torch and the hand, and '
          'in a shop that somewhere is a tank of water on legs',
          ppe=['flame-resistant clothing'], anchor='back-corner',
          walls=['right']),
    piece('fire-watch-post', 'Fire watch post', 'stand', 'pedestal',
          (.18, 1.30, [.26, .30, .18]), 'post',
          'hot work is watched while it is done and for a while after it '
          'stops, and the watch stands at a post with the clock on it',
          ppe=['flame-resistant clothing'], walls=['right'], approach=False),

    # ---- molten metal, corrosive, stored energy, wet: face shield ---------
    piece('splash-screen', 'Splash screen', 'screen', 'screen',
          (1.20, 1.60, 2), 'part',
          'what comes off the work at face height comes off it sideways too, '
          'and the person at the next bench did not put a shield on',
          ppe=['face shield'], walls=['right'], approach=False),
    piece('shield-shelf', 'Face shield shelf', 'storage', 'wall-shelf',
          (.90, .55, .26, 2), 'wood',
          'a shield kept in a locker is a shield nobody fetches; it lives on '
          'an open shelf at the door of the room that calls for it',
          ppe=['face shield'], anchor='wall-mounted', walls=['left']),

    # ---- live electrical --------------------------------------------------
    piece('rubber-goods-rack', 'Rubber goods rack', 'storage', 'rack',
          (1.00, 1.55, .45, 4), 'metal',
          'insulating gloves and sleeves are stored flat, unfolded and out '
          'of the light, and they are re-tested on a date somebody can read',
          ppe=['dielectric gloves']),
    piece('mat-roll-stand', 'Insulating mat roll stand', 'stock', 'spool',
          (1.10, 1.05, .26), 'part',
          'the mat that goes down in front of a live panel is kept rolled on '
          'a stand, because a folded one keeps the fold',
          ppe=['dielectric gloves'], walls=['right']),
    piece('hot-stick-cradle', 'Hot stick cradle', 'storage', 'wall-cradle',
          (1.30, .40), 'wood',
          'a live-line stick is only as good as its surface, so it hangs '
          'straight on brackets and never leans in a corner',
          ppe=['dielectric gloves'], anchor='wall-mounted', walls=['right'],
          crib_tools=['hot-stick']),
    piece('lockout-station', 'Lockout station', 'safety-fixture',
          'wall-board', (1.00, .80, 4, False), 'paint',
          'a shape hanging where a room record asks for arc-rated protection: '
          + SCHEM + '. It locks nothing out',
          ppe=['arc-flash face shield'], anchor='wall-mounted',
          walls=['left']),
    piece('arc-rated-locker', 'Arc-rated garment locker', 'storage', 'locker',
          (1.05, 1.70, .50, 3), 'steel',
          'arc-rated clothing is issued by size and returned to the same '
          'hook, and a heap on a bench is nobody\'s size',
          ppe=['arc-flash face shield']),

    # ---- corrosive ---------------------------------------------------------
    piece('decant-stand', 'Decant stand', 'bench', 'table',
          (1.10, .60, .80, True), 'part',
          'pouring from a drum into a jug is done on a low bench with a lip, '
          'over a tray, at a height where the pour can be watched',
          ppe=['chemical gloves']),
    piece('drip-tray-stand', 'Drip tray stand', 'vessel', 'bin',
          (1.00, .32, .70, False), 'part',
          'a container that has been decanted from drips for an hour '
          'afterwards, and the floor is not where that is caught',
          ppe=['chemical gloves'], walls=['right']),
    piece('apron-rail', 'Apron rail', 'storage', 'drying-rack',
          (1.00, 1.60, 3), 'metal',
          'an apron worn against a splash is hung wet, outside the locker, '
          'where the next person can see whether it is dry',
          ppe=['apron'], walls=['right']),
    piece('wash-trough', 'Wash trough', 'vessel', 'sink', (1.20, .90, .55),
          'part',
          'the first thing done after chemical work is done at a trough, and '
          'a trough is a basin on legs with a tap over it',
          ppe=['apron']),

    # ---- wet process -------------------------------------------------------
    piece('boot-wash', 'Boot wash trough', 'vessel', 'sink', (.95, .55, .60),
          'part',
          'wet-process work walks out of the room on the boots unless there '
          'is somewhere low to wash them at the threshold',
          ppe=['waterproof boots'], walls=['left']),
    piece('duckboard-stack', 'Duckboard stack', 'stock', 'pallet',
          (1.20, .42, .70, 4), 'wood',
          'standing all day on a wet floor is what duckboards are for, and '
          'the spares stack flat by the door',
          ppe=['waterproof boots'], walls=['right']),

    # ---- immersion ---------------------------------------------------------
    piece('suit-drying-rack', 'Immersion suit rack', 'storage', 'drying-rack',
          (1.30, 1.70, 4), 'metal',
          'a suit put away damp is a suit nobody will wear next week, so it '
          'hangs open on bars with a tray under it',
          ppe=['immersion suit']),
    piece('tender-post', 'Tender line post', 'stand', 'pedestal',
          (.20, 1.35, [.30, .26, .22]), 'post',
          'somebody on the surface holds the line and writes the time down, '
          'and that person stands at a post rather than in the way',
          ppe=['immersion suit'], walls=['right'], approach=False),

    # ---- contaminant, particulate, radiation -------------------------------
    piece('coverall-hamper', 'Coverall hamper', 'waste', 'bin',
          (.90, .95, .60, True), 'part',
          'what came off the dirty side does not go back in the locker; it '
          'goes in a lidded hamper on the line between the two sides',
          ppe=['coveralls'], walls=['left']),
    piece('dirty-side-bench', 'Dirty side bench', 'bench', 'bench',
          (1.60, .70, .86, True, True), 'part',
          'a room with a clean side and a dirty side needs a bench on the '
          'dirty one, or the line is a line nobody can keep',
          ppe=['coveralls'], walls=['right']),
    piece('filter-cabinet', 'Filter cabinet', 'storage', 'cabinet',
          (.90, 1.45, .45, 2, True), 'steel',
          'cartridges are dated, sized and issued as a pair, and a cabinet '
          'is what keeps them out of the air they are meant to filter',
          ppe=['respirator']),
    piece('fit-test-bench', 'Fit test bench', 'bench', 'bench',
          (1.40, .65, .88, True, False), 'wood',
          'a mask that has not been fitted to the face in front of it is '
          'jewellery, and fitting one is a seated job at a bench',
          ppe=['respirator']),
    piece('cartridge-bin', 'Spent cartridge bin', 'waste', 'drum', (.22, .66),
          'metal',
          'a used cartridge is contaminated waste and it is kept apart from '
          'the general bin in the room it came off in',
          ppe=['respirator'], anchor='back-corner', walls=['right']),
    piece('survey-meter-bench', 'Survey meter bench', 'bench', 'bench',
          (1.30, .65, .88, True, False), 'part',
          'a reading taken and written down is the whole of radiological '
          'work, and it is taken at a bench with the log on it',
          ppe=['dosimeter'], walls=['left']),
    piece('glove-dispenser', 'Glove and mask dispenser', 'storage',
          'wall-shelf', (.84, .55, .22, 2), 'paint',
          'the last thing put on before the clean side is taken from a box '
          'on the wall, one pair at a time, by somebody already gowned',
          ppe=['gowning'], anchor='wall-mounted', walls=['left'],
          approach=False),
    piece('dosimeter-rack', 'Dosimeter rack', 'storage', 'wall-shelf',
          (.80, .50, .18, 2), 'metal',
          'badges are issued to a name, read on a date and hung back in the '
          'same slot, which is why the rack is on the wall by the door',
          ppe=['dosimeter'], anchor='wall-mounted', walls=['right']),
    piece('gowning-locker', 'Gowning locker', 'storage', 'locker',
          (1.20, 1.70, .48, 4), 'paint',
          'the point of a gowning room is that what you walked in wearing '
          'stays on one side of it',
          ppe=['gowning']),
    piece('tack-mat-stand', 'Tack mat stand', 'stand', 'pallet',
          (.90, .30, .70, 2), 'part',
          'the last thing between a corridor and a clean room is a mat that '
          'takes the floor off your boots, and it lies at the threshold',
          ppe=['gowning'], anchor='back-corner', walls=['right']),

    # ---- timber and dust ---------------------------------------------------
    piece('extraction-stand', 'Extraction trunk stand', 'machine', 'pedestal',
          (.22, 1.45, [.34, .34, .30]), 'metal',
          'dust taken off at the cut never reaches the lungs across the room, '
          'and the trunk that takes it stands beside the bench',
          ppe=['dust mask'], walls=['right']),
    piece('sweep-cart', 'Sweep-up cart', 'trolley', 'cart', (.80, .95, .52),
          'wood',
          'shavings are swept up at the end of every session rather than at '
          'the end of the week, and the cart for it lives in the room',
          ppe=['dust mask'], anchor='back-corner', walls=['left']),

    # ---- noise --------------------------------------------------------------
    piece('plug-dispenser', 'Ear plug dispenser', 'safety-fixture',
          'wall-shelf', (.50, .40, .16, 2), 'paint',
          'a shape hanging where a room record asks for hearing protection: '
          + SCHEM + '. It dispenses nothing',
          ppe=['hearing protection'], anchor='wall-mounted', walls=['right'],
          approach=False),
    piece('acoustic-screen', 'Acoustic screen', 'screen', 'screen',
          (1.60, 1.70, 4), 'part',
          'noise is cut at the machine or it is not cut at all, and a screen '
          'around the loud corner is what lets the rest of the room talk',
          ppe=['hearing protection'], walls=['right'], approach=False),

    # ---- static and flammable atmosphere ------------------------------------
    piece('bonding-reel', 'Bonding lead reel', 'storage', 'reel',
          (.55, 1.05, .26), 'metal',
          'two vessels at different potentials are what makes the spark, and '
          'the lead that ties them together is kept on a reel, not coiled',
          ppe=['anti-static clothing'], walls=['right']),
    piece('earth-post', 'Earth point post', 'stand', 'pedestal',
          (.18, 1.15, [.22, .24, .20]), 'post',
          'an earth point is a place, not a wire; it is marked, it is fixed '
          'and it is where every lead in the room comes back to',
          ppe=['anti-static clothing'], anchor='back-corner',
          walls=['right'], approach=False),
    piece('cal-gas-rack', 'Calibration gas rack', 'storage', 'rack',
          (.90, 1.40, .40, 3), 'metal',
          'a monitor that has not been bumped against a known gas is a '
          'monitor nobody should trust, and the cylinders for it are racked',
          ppe=['gas monitor']),
    piece('purge-fan-stand', 'Purge fan stand', 'machine', 'pedestal',
          (.26, 1.30, [.40, .40, .36]), 'metal',
          'a space is ventilated before it is entered and while it is '
          'occupied, and the fan that does it stands by the opening',
          ppe=['gas monitor'], anchor='back-corner', walls=['left']),

    # ---- confined space and height ------------------------------------------
    piece('entry-tripod', 'Entry tripod', 'stand', 'tree', (1.70, 3, .34),
          'metal',
          'nobody goes into a hole without a way of being pulled out of it, '
          'and the frame that does the pulling stands over the opening',
          ppe=['rescue harness'], anchor='back-corner', walls=['right']),
    piece('winch-post', 'Retrieval winch post', 'machine', 'pedestal',
          (.20, 1.25, [.32, .28, .26]), 'steel',
          'the line from the tripod goes somewhere, and where it goes is a '
          'winch on a post that somebody can crank without letting go',
          ppe=['rescue harness'], walls=['right'], approach=False),
    piece('harness-rail', 'Harness inspection rail', 'storage', 'drying-rack',
          (1.40, 1.65, 3), 'metal',
          'a harness is looked at stitch by stitch before it is worn, and '
          'that is done hanging at eye height, not out of a bag',
          ppe=['full-body harness']),
    piece('lanyard-locker', 'Lanyard locker', 'storage', 'locker',
          (1.00, 1.60, .45, 2), 'steel',
          'lanyards are issued in pairs, logged against a serial and taken '
          'out of service on a date; the locker is where that happens',
          ppe=['full-body harness'], walls=['right']),
    piece('helmet-shelf', 'Helmet shelf', 'storage', 'wall-shelf',
          (1.00, .60, .30, 2), 'wood',
          'a helmet with a chinstrap is a different helmet, and it is kept '
          'where the people who need one can see there are enough',
          ppe=['chinstrap helmet'], anchor='wall-mounted', walls=['left']),
    piece('edge-stack', 'Edge protection stack', 'stock', 'crates',
          (1.20, .85, .55, 3), 'part',
          'the boards and clips that make an edge safe are stacked in the '
          'room that teaches working at one, ready to be carried out',
          ppe=['chinstrap helmet'], anchor='back-corner', walls=['left']),

    # ---- rotating machinery --------------------------------------------------
    piece('guard-store', 'Machine guard store', 'storage', 'rack',
          (1.40, 1.55, .50, 3), 'steel',
          'a guard taken off for a job is a guard that has to go back on, '
          'and it waits on a rack with the machine\'s number on it',
          ppe=['close-fitting clothing']),
    piece('swarf-bin', 'Swarf bin', 'waste', 'drum', (.30, .74), 'metal',
          'turnings come off sharp, hot and in a long ribbon, and they are '
          'not swept up with a brush into a cardboard box',
          ppe=['close-fitting clothing'], anchor='back-corner',
          walls=['right']),
]

# ---------------------------------------------------------------------------
# THE SHOP FURNITURE. Each piece names the words it answers to; those words
# are matched against the room strand's OWN purpose string, which lives in
# web/interiors.py and is never retyped here. A token that matches nothing is
# a defect and the build says so.
#
# These are the pieces every trade's hall has, because every trade's hall has
# the same eleven rooms. What makes one hall different from the next is the
# conditions furniture above and the district furniture below — not this.
# ---------------------------------------------------------------------------
SHOP_PROPS = [
    # ---- safety : "Gowning, atmospheric checks, permit board" -------------
    piece('gowning-bench', 'Gowning bench', 'seat', 'bench',
          (1.60, .50, .48, True, False), 'wood',
          'you change at it before you cross the stripe the page already '
          'paints across a safety room doorway',
          tokens=['gowning'], max_per_room=2, approach=False),
    piece('permit-board', 'Permit board', 'board', 'wall-board',
          (1.14, .80, 3, False), 'paint',
          'the board the safety room is named after, and the one the records '
          'room files afterwards',
          tokens=['permit'], anchor='wall-mounted'),
    piece('boot-step', 'Boot change step', 'seat', 'crates',
          (1.00, .46, .50, 2), 'wood',
          'boots come off sitting down and go on standing up, and the step '
          'that makes both possible is the width of two people',
          tokens=['gowning'], walls=['right'], approach=False),
    piece('atmosphere-post', 'Atmospheric check post', 'stand', 'pedestal',
          (.16, 1.36, [.22, .30, .16]), 'metal',
          'the room says atmospheric checks happen here, so the thing they '
          'are made on stands in it',
          tokens=['atmospheric'], walls=['right'], approach=False),
    piece('induction-lectern', 'Induction lectern', 'stand', 'easel',
          (.70, 1.20), 'wood',
          'nobody crosses the stripe without being told what is on the other '
          'side of it, and that is said standing at something',
          tokens=['checks'], anchor='back-corner', walls=['left']),

    # ---- procedure : "The floor the trade is actually learned on" ---------
    piece('work-trestle', 'Work trestle', 'stand', 'trestle',
          (1.80, .90, .50), 'wood',
          'the bay is the floor a trade is learned on, and a trestle is what '
          'the work is held at height on while it is',
          tokens=['floor'], walls=['left', 'right'], max_per_room=2),
    piece('learner-stool', 'Learner stool', 'seat', 'stool', (.22, .62),
          'metal',
          'nobody stands for six hours; a bay with no seat in it is a '
          'rendering of a bay',
          tokens=['learned'], walls=['right'], max_per_room=2, approach=False),
    piece('practice-bench', 'Practice bench', 'bench', 'vice-bench',
          (1.70, .70, .90), 'steel',
          'the first thing a trade puts in a bay is a bench with a vice on '
          'it, because that is where a hand learns to hold something still',
          tokens=['floor'], walls=['right'], max_per_room=2),
    piece('task-board', 'Task board', 'board', 'wall-board',
          (1.30, .85, 4, True), 'paint',
          'a bay runs to a task list that changes every session, and the list '
          'hangs where the person doing it can reach a marker',
          tokens=['learned'], anchor='wall-mounted'),
    piece('bay-tool-tree', 'Bay tool tree', 'stand', 'tree', (1.55, 3, .32),
          'metal',
          'what is in use this session hangs in the middle of the bay where '
          'four people can reach it, not in a crib down the corridor',
          tokens=['floor'], anchor='back-corner', walls=['right']),
    piece('demo-table', 'Demonstration table', 'bench', 'table',
          (1.35, .85, .84, True), 'wood',
          'an instructor does it once slowly at a table everybody can stand '
          'around before anybody does it fast at a bench',
          tokens=['learned'], walls=['left']),
    piece('checkout-board', 'Plant checkout board', 'board', 'wall-board',
          (1.34, .90, 6, False), 'paint',
          'plant is CHECKED OUT to this room, and a checkout that is not '
          'written down anywhere did not happen',
          tokens=['checked out'], anchor='wall-mounted'),
    piece('bay-guard-rail', 'Bay guard rail', 'screen', 'screen',
          (2.00, 1.10, 2), 'post',
          'a training AREA is an area because something marks where it stops',
          tokens=['training area'], walls=['right'], max_per_room=2,
          approach=False),
    piece('plant-service-bench', 'Plant service bench', 'bench', 'bench',
          (1.80, .75, .90, True, True), 'steel',
          'the machine is not the only thing in an equipment bay; the greasy '
          'end of looking after it happens at a bench beside it',
          tokens=['plant'], walls=['right']),
    piece('lube-store', 'Lubricant store', 'storage', 'cabinet',
          (.95, 1.30, .50, 2, True), 'cone',
          'oils, greases and the pump that moves them are kept together, '
          'bunded and closed, and not on the floor by the machine',
          tokens=['plant'], anchor='back-corner', walls=['left']),
    piece('chock-bin', 'Chock and block bin', 'vessel', 'bin',
          (.90, .60, .60, False), 'wood',
          'nothing heavy is left standing on its own weight alone, and what '
          'stops it rolling lives in a bin at the bay mouth',
          tokens=['plant'], anchor='back-corner', walls=['right'],
          crib_tools=['wheel-chock']),
    piece('machine-log-desk', 'Machine log desk', 'bench', 'table',
          (1.10, .60, .80, True), 'wood',
          'hours, faults and the last service are written down at the '
          'machine, in the room, by the person who ran it',
          tokens=['checked out'], walls=['left']),

    # ---- tools : "Issue, calibration and return" --------------------------
    piece('issue-counter', 'Issue counter', 'bench', 'bench',
          (1.80, .60, .86, True, True), 'wood',
          'the crib the page already builds hands tools ACROSS something, and '
          'until now it handed them across nothing',
          tokens=['issue']),
    piece('calibration-cabinet', 'Calibration cabinet', 'storage', 'cabinet',
          (.94, 1.36, .54, 2, True), 'steel',
          'calibration is the middle word of this room\'s purpose and it is '
          'the one that needs a locked box',
          tokens=['calibration'], walls=['right']),
    piece('return-bin', 'Return bin', 'vessel', 'drum', (.30, .78), 'part',
          'things come BACK to a crib, and a crib with nowhere to put them '
          'back is a counter with a queue',
          tokens=['return'], anchor='back-corner', walls=['right']),
    piece('tool-pegboard', 'Tool pegboard', 'board', 'wall-peg',
          (1.20, .95, 5), 'paint',
          'a crib is read at a glance: a shadow board says what is out by '
          'the shape of the hole it left',
          tokens=['issue'], anchor='wall-mounted', walls=['left']),
    piece('battery-shelf', 'Battery charge shelf', 'storage', 'wall-shelf',
          (1.00, .70, .28, 3), 'metal',
          'cordless plant is only issued charged, so the shelf that charges '
          'it is inside the crib rather than behind it',
          tokens=['issue'], anchor='wall-mounted', walls=['right']),
    piece('gauge-drawers', 'Gauge drawers', 'storage', 'drawers',
          (.90, 1.10, .50, 4), 'steel',
          'measuring kit is kept flat, apart and in a drawer with its own '
          'name on it, because a gauge in a heap is a gauge out of true',
          tokens=['calibration', 'acceptance'], walls=['left']),

    # ---- materials : "Stock, offcuts and consumables" ---------------------
    piece('stock-rack', 'Stock rack', 'storage', 'rack',
          (1.80, 1.70, .70, 3), 'metal',
          'STOCK is the first word of this room\'s purpose and stock is kept '
          'on something',
          tokens=['stock'], max_per_room=1),
    piece('sheet-rack', 'Sheet stock rack', 'stock', 'cantilever',
          (1.40, 1.60, .60, 3), 'steel',
          'flat stock leans; it does not stack, and a rack that lets it lean '
          'against something is what stops it bowing',
          tokens=['stock', 'plant'], walls=['left']),
    piece('bar-stock-cradle', 'Bar stock cradle', 'stock', 'cradle',
          (1.25, .80, .48), 'metal',
          'long stock is stored where it can be pulled out by one person '
          'without pulling the rest of the rack down with it',
          tokens=['stock', 'floor'], walls=['right']),
    piece('offcut-bin', 'Offcut bin', 'waste', 'bin', (.90, .66, .60, False),
          'wood',
          'OFFCUTS is the second word, and the difference between a trade '
          'shop and a warehouse is that the offcuts are kept',
          tokens=['offcuts'], anchor='back-corner', walls=['left']),
    piece('consumables-shelf', 'Consumables shelf', 'storage', 'wall-shelf',
          (.86, .90, .30, 3), 'wood',
          'CONSUMABLES is the third word; they are small, they go at hand '
          'height, and they do not belong on the stock rack',
          tokens=['consumables'], anchor='wall-mounted', walls=['right'],
          max_per_room=2),
    piece('consumable-drums', 'Consumable drum stand', 'vessel', 'drum',
          (.32, .90), 'part',
          'what is bought by the drum is drawn off by the litre, and the '
          'drum stands where the spillage can be seen',
          tokens=['consumables'], anchor='back-corner', walls=['right']),
    piece('layout-table', 'Layout table', 'bench', 'table',
          (2.00, .90, .80, True), 'steel',
          'setting out and marking are done flat, at waist height, on '
          'something that does not move',
          tokens=['setting', 'marking'], max_per_room=1),
    piece('control-pillar', 'Control point pillar', 'stand', 'pedestal',
          (.20, 1.28, [.24, .30, .22]), 'metal',
          'a CONTROL POINT is a thing you can put an instrument over twice '
          'and get the same answer; a painted cross is not one',
          tokens=['control point'], anchor='back-corner',
          walls=['left', 'right'], approach=False),
    piece('marking-shelf', 'Marking media shelf', 'storage', 'wall-shelf',
          (.86, .65, .26, 2), 'wood',
          'chalk, soapstone, paint and a wet rag are the whole of marking '
          'out, and they live at the table rather than in the crib',
          tokens=['marking'], anchor='wall-mounted', walls=['right']),
    piece('template-rack', 'Template rack', 'storage', 'rack',
          (1.20, 1.45, .45, 4), 'wood',
          'a template that has been cut once is worth more than the drawing '
          'it came off, so it is hung flat and kept',
          tokens=['marking'], walls=['left']),
    piece('setting-out-reel', 'Setting-out line reel', 'storage', 'reel',
          (.60, 1.00, .26), 'metal',
          'a line pulled off a reel is straight; a line pulled out of a '
          'pocket has a memory of the pocket',
          tokens=['setting'], walls=['right'], crib_tools=['string-line']),

    # ---- inspection : "Acceptance criteria and sign-off" ------------------
    piece('gauge-stand', 'Acceptance gauge stand', 'stand', 'pedestal',
          (.18, 1.26, [.30, .25, .20]), 'metal',
          'ACCEPTANCE CRITERIA is a number somebody reads off something',
          tokens=['acceptance', 'criteria'], walls=['right']),
    piece('signoff-desk', 'Sign-off desk', 'bench', 'table',
          (1.40, .70, .80, True), 'wood',
          'SIGN-OFF is a person writing on paper at a desk, and the second '
          'half of what this room is for',
          tokens=['sign-off']),
    piece('sample-cabinet', 'Sample cabinet', 'storage', 'cabinet',
          (1.00, 1.40, .45, 2, True), 'wood',
          'an acceptance standard that can be held in the hand settles an '
          'argument a written one starts',
          tokens=['acceptance'], walls=['right']),

    # ---- troubleshooting : "Fault-finding against live rigs" -------------
    piece('surface-plate', 'Surface plate table', 'bench', 'bench',
          (1.10, .75, .88, True, True), 'steel',
          'a flat reference is the one thing in an inspection room that '
          'everything else is measured against, and it is heavy on purpose',
          tokens=['acceptance'], walls=['left']),
    piece('rig-frame', 'Live rig frame', 'stand', 'cantilever',
          (1.50, 1.66, .35, 3), 'metal',
          'a LIVE RIG is a frame with something wired to it that can be made '
          'to fail on purpose',
          tokens=['rigs'], max_per_room=1),
    piece('test-bench', 'Fault-finding bench', 'bench', 'bench',
          (1.50, .70, .88, True, False), 'steel',
          'FAULT-FINDING happens with instruments on a surface, facing the rig',
          tokens=['fault-finding'], walls=['right']),
    piece('instrument-cabinet', 'Instrument cabinet', 'storage', 'cabinet',
          (.85, 1.30, .45, 1, True), 'steel',
          'test kit is the most stolen and most dropped thing in a shop, and '
          'it goes back in a case in a cupboard every time',
          tokens=['fault-finding'], walls=['left']),
    piece('fault-log-board', 'Fault log board', 'board', 'wall-board',
          (.86, .80, 5, True), 'paint',
          'the same fault gets found twice unless the first person wrote on '
          'the board what it turned out to be',
          tokens=['rigs'], anchor='wall-mounted'),
    piece('isolation-post', 'Isolation post', 'stand', 'pedestal',
          (.18, 1.20, [.26, .26, .20]), 'post',
          'a rig that can be made live has to be made dead from one place '
          'that everybody in the room can see is dead',
          tokens=['live'], anchor='back-corner', walls=['left'],
          approach=False),

    # ---- coordination : "Shift start, hand-offs, cross-trade" -------------
    piece('shift-board', 'Shift board', 'board', 'wall-board',
          (1.64, .95, 4, True), 'paint',
          'a SHIFT START is people standing in front of a board that says who '
          'is doing what',
          tokens=['shift'], anchor='wall-mounted'),
    piece('handoff-table', 'Hand-off table', 'bench', 'table',
          (1.60, .80, .78, True), 'wood',
          'a HAND-OFF is two crews around one table with the drawing on it',
          tokens=['hand-offs'], max_per_room=1),
    piece('crew-bench', 'Crew bench', 'seat', 'bench',
          (1.70, .45, .46, False, False), 'wood',
          'a shift start is fifteen people in a room, and half of them have '
          'been on their feet since six',
          tokens=['shift'], walls=['right'], approach=False),
    piece('drawing-easel', 'Drawing easel', 'board', 'easel', (.90, 1.35),
          'wood',
          'cross-trade means two trades looking at the same sheet, which '
          'means the sheet has to stand up where both can reach it',
          tokens=['cross-trade'], anchor='back-corner', walls=['right']),
    piece('plan-rack', 'Plan rack', 'storage', 'rack',
          (1.10, 1.40, .40, 3), 'metal',
          'drawings roll, and a roll on a table is a roll on the floor; the '
          'rack is what keeps the set in order between hand-offs',
          tokens=['hand-offs'], walls=['left']),

    # ---- documentation : "Permits, certificates, as-builts" --------------
    piece('records-cabinet', 'Records cabinet', 'storage', 'drawers',
          (1.00, 1.39, .57, 4), 'steel',
          'CERTIFICATES and AS-BUILTS are paper, and paper that matters lives '
          'in a drawer somebody can find',
          tokens=['certificates', 'as-builts'], max_per_room=1),
    piece('drawing-chest', 'As-built drawing chest', 'storage', 'drawers',
          (1.20, .95, .70, 3), 'wood',
          'an as-built is a big sheet and it is kept flat, because a folded '
          'one is read wrong for the next thirty years',
          tokens=['as-builts'], walls=['right']),
    piece('permit-file-rack', 'Permit file rack', 'storage', 'rack',
          (1.00, 1.50, .38, 4), 'metal',
          'a permit is only evidence while it can be found, and it is found '
          'by date on a shelf rather than by memory',
          tokens=['permits'], walls=['left']),
    piece('exam-desk', 'Exam desk', 'bench', 'table',
          (1.20, .60, .76, True), 'wood',
          'LEVEL TESTS are sat at a desk, and a classroom with no desks is a '
          'corridor',
          tokens=['tests'], walls=['left', 'right'], max_per_room=2),
    piece('instructor-lectern', 'Instructor lectern', 'stand', 'easel',
          (.75, 1.25), 'wood',
          'the INSTRUCTOR TRACK has an instructor in it and the instructor '
          'stands somewhere',
          tokens=['instructor'], anchor='back-corner', walls=['left']),
    piece('classroom-stool', 'Classroom stool', 'seat', 'stool', (.20, .58),
          'wood',
          'a desk without a stool is a shelf, and a level test takes two '
          'hours',
          tokens=['tests'], walls=['right'], max_per_room=3, approach=False),
    piece('progress-board', 'Progress board', 'board', 'wall-board',
          (.86, .90, 6, True), 'paint',
          'a TRACK is something you can see yourself moving along, which '
          'means it is drawn on a wall where the cohort can read it',
          tokens=['track'], anchor='wall-mounted'),
    piece('reference-shelf', 'Reference shelf', 'storage', 'wall-shelf',
          (.86, .80, .28, 3), 'wood',
          'a level test is against a standard, and the standard is a book '
          'somebody has to be able to take down and open',
          tokens=['level'], anchor='wall-mounted', walls=['right']),
]

# ---------------------------------------------------------------------------
# THE DISTRICT FURNITURE. Two pieces for every one of the 96 tools in
# tools/registry/toolcribs.json: the thing the tool is worked at, and the
# thing it lives on. Each piece names its tool BY ID and the build stops on
# an id no crib carries, so this catalogue cannot drift away from the crib it
# describes. The district is not typed on a piece either — it is READ from
# whichever of the eight cribs carries that tool.
#
# The sentence each piece gives for itself is DERIVED, not written: it is the
# family's own definition joined to the crib's own use line for the tool. A
# hand-written paragraph per piece would be 192 opinions about facts two
# registries already state.
#
# Rows are (tool, suffix, name, family, form, args, material, token, spot).
# `spot` is where it stands: L/R a side wall, CL/CR a back corner, WL/WR
# hung on a partition. `token` may name a SECOND room after a pipe — the one
# the piece stands in when the first room's walls are already full. Both are
# matched against those rooms' own purpose lines like any other token, so a
# fallback no room's purpose supports fails the build.
# ---------------------------------------------------------------------------
# A district piece names the partition it would rather have, and takes the
# other one when that run is already full. The shop furniture above is
# pinned to one wall because the room is laid out around it; the district
# catalogue is what is left to fit around that, so it fits where it can.
SPOTS = {'L': ('side-wall', ['left', 'right'], True),
         'R': ('side-wall', ['right', 'left'], True),
         'CL': ('back-corner', ['left', 'right'], True),
         'CR': ('back-corner', ['right', 'left'], True),
         'WL': ('wall-mounted', ['left', 'right'], True),
         'WR': ('wall-mounted', ['right', 'left'], True)}

CRIB_ROWS = [
    # ------------------------------------------------- structural ---------
    ('spud-wrench', 'bench', 'Connection bolt-up bench', 'bench', 'vice-bench', (1.45, .70, .90), 'steel', 'floor', 'L'),
    ('spud-wrench', 'bin', 'Bolt and drift bin', 'stock', 'bin', (.85, .55, .55, False), 'metal', 'stock', 'CR'),
    ('sleever-bar', 'trestle', 'Beam alignment trestle', 'stand', 'trestle', (1.45, .95, .55), 'steel', 'floor', 'R'),
    ('sleever-bar', 'cradle', 'Sleever bar cradle', 'storage', 'wall-cradle', (1.35, .38), 'metal', 'issue', 'WL'),
    ('bull-pin', 'jig', 'Hole alignment jig table', 'bench', 'table', (1.40, .80, .80, True), 'steel', 'setting', 'L'),
    ('bull-pin', 'drawers', 'Pin and wedge drawers', 'storage', 'drawers', (.80, 1.05, .50, 4), 'steel', 'issue', 'R'),
    ('torque-wrench', 'bench', 'Torque check bench', 'bench', 'bench', (1.40, .65, .88, True, False), 'wood', 'calibration', 'L'),
    ('torque-wrench', 'cradle', 'Torque wrench cradle', 'storage', 'wall-cradle', (1.00, .34), 'wood', 'return', 'WR'),
    ('shackle', 'table', 'Rigging lay-down table', 'bench', 'table', (1.45, 1.00, .70, True), 'wood', 'plant', 'R'),
    ('shackle', 'bin', 'Shackle and pin bin', 'stock', 'bin', (.75, .50, .55, False), 'metal', 'stock', 'CL'),
    ('wire-sling', 'rail', 'Sling inspection rail', 'storage', 'drying-rack', (1.40, 1.65, 4), 'metal', 'acceptance', 'R'),
    ('wire-sling', 'tree', 'Sling storage tree', 'storage', 'tree', (1.60, 4, .34), 'metal', 'issue', 'CR'),
    ('lever-hoist', 'frame', 'Hoist proof frame', 'stand', 'cantilever', (1.40, 1.70, .40, 3), 'steel', 'rigs', 'L'),
    ('lever-hoist', 'rack', 'Chain hoist rack', 'storage', 'rack', (1.20, 1.55, .50, 3), 'metal', 'issue|plant', 'L'),
    ('beam-clamp', 'beam', 'Trial flange beam', 'stand', 'cradle', (1.45, .85, .50), 'steel', 'floor', 'R'),
    ('beam-clamp', 'drawers', 'Beam clamp drawers', 'storage', 'drawers', (.85, 1.00, .48, 3), 'steel', 'calibration', 'R'),
    ('plumb-bob', 'post', 'Plumbing-up post', 'stand', 'pedestal', (.18, 1.30, [.22, .28, .18]), 'metal', 'control point', 'CL'),
    ('plumb-bob', 'shelf', 'Line and bob shelf', 'storage', 'wall-shelf', (.80, .60, .24, 2), 'wood', 'marking', 'WR'),
    ('center-punch', 'bench', 'Layout punch bench', 'bench', 'bench', (1.45, .70, .90, True, True), 'steel', 'marking', 'L'),
    ('center-punch', 'board', 'Punch and chisel board', 'board', 'wall-peg', (1.10, .90, 5), 'paint', 'issue|marking', 'WL'),
    ('bolt-gauge', 'station', 'Bolt gauge station', 'bench', 'table', (1.20, .70, .82, True), 'steel', 'acceptance', 'L'),
    ('bolt-gauge', 'cabinet', 'Fastener sample cabinet', 'storage', 'cabinet', (.95, 1.35, .42, 2, True), 'wood', 'criteria', 'R'),
    ('impact-wrench', 'bench', 'Impact wrench service bench', 'bench', 'bench', (1.45, .70, .90, True, True), 'steel', 'plant', 'L'),
    ('impact-wrench', 'drawers', 'Socket and anvil drawers', 'storage', 'drawers', (.90, 1.00, .52, 4), 'metal', 'consumables', 'R'),

    # ------------------------------------------------- envelope -----------
    ('utility-knife', 'bench', 'Board trimming bench', 'bench', 'bench', (1.45, .80, .88, True, True), 'wood', 'floor', 'L'),
    ('utility-knife', 'bin', 'Spent blade bin', 'waste', 'drum', (.20, .60), 'metal', 'offcuts', 'CR'),
    ('taping-knife', 'trestle', 'Taping trestle', 'stand', 'trestle', (1.45, .95, .50), 'wood', 'floor', 'R'),
    ('taping-knife', 'shelf', 'Knife and hawk shelf', 'storage', 'wall-shelf', (1.00, .70, .26, 3), 'wood', 'issue', 'WR'),
    ('brick-trowel', 'bench', 'Mortar board bench', 'bench', 'bench', (1.45, .75, .84, True, False), 'part', 'learned', 'L'),
    ('brick-trowel', 'tank', 'Trowel wash tank', 'vessel', 'tank', (.32, .95), 'part', 'return', 'CR'),
    ('jointer', 'table', 'Pointing practice table', 'bench', 'table', (1.40, .80, .80, True), 'wood', 'learned', 'R'),
    ('jointer', 'rack', 'Jointer and raker rack', 'storage', 'rack', (1.00, 1.35, .38, 4), 'metal', 'issue', 'R'),
    ('grout-float', 'bench', 'Tile setting bench', 'bench', 'bench', (1.45, .75, .86, True, True), 'wood', 'floor', 'R'),
    ('grout-float', 'bin', 'Grout mixing bin', 'vessel', 'bin', (.80, .60, .60, False), 'part', 'consumables', 'CL'),
    ('suction-cup', 'stand', 'Glass handling stand', 'stand', 'cantilever', (1.30, 1.55, .50, 3), 'part', 'plant', 'L'),
    ('suction-cup', 'rack', 'Glazing cup rack', 'storage', 'rack', (1.00, 1.30, .40, 3), 'metal', 'issue', 'L'),
    ('caulk-gun', 'bench', 'Sealant run bench', 'bench', 'bench', (1.40, .65, .88, True, False), 'part', 'learned', 'L'),
    ('caulk-gun', 'shelf', 'Cartridge shelf', 'storage', 'wall-shelf', (1.10, .80, .28, 3), 'wood', 'consumables', 'WR'),
    ('chalk-line', 'table', 'Snap line layout table', 'bench', 'table', (1.45, .95, .80, True), 'wood', 'setting', 'R'),
    ('chalk-line', 'reel', 'Chalk line reel stand', 'storage', 'reel', (.55, .95, .24), 'metal', 'marking', 'R'),
    ('framing-square', 'bench', 'Squaring bench', 'bench', 'bench', (1.45, .80, .88, True, True), 'wood', 'setting', 'L'),
    ('framing-square', 'board', 'Square and bevel board', 'board', 'wall-peg', (1.20, .95, 4), 'paint', 'issue', 'WL'),
    ('block-plane', 'bench', 'Trimming and planing bench', 'bench', 'vice-bench', (1.45, .75, .90), 'wood', 'floor|stock', 'R'),
    ('block-plane', 'hopper', 'Shaving hopper', 'waste', 'hopper', (.90, 1.00, .60), 'wood', 'offcuts', 'R'),
    ('putty-knife', 'bench', 'Bedding and glazing bench', 'bench', 'bench', (1.45, .70, .86, True, False), 'wood', 'learned|stock', 'R'),
    ('putty-knife', 'crates', 'Putty and pane crates', 'stock', 'crates', (1.10, .80, .55, 3), 'wood', 'stock|floor', 'CL'),
    ('seam-roller', 'table', 'Membrane seam table', 'bench', 'table', (1.45, 1.00, .78, True), 'part', 'floor|plant', 'L'),
    ('seam-roller', 'spool', 'Membrane roll stand', 'stock', 'spool', (1.20, 1.10, .28), 'part', 'stock|floor', 'L'),

    # ------------------------------------------------- systems ------------
    ('multimeter', 'bench', 'Meter test bench', 'bench', 'bench', (1.45, .70, .88, True, False), 'steel', 'fault-finding', 'L'),
    ('multimeter', 'cabinet', 'Meter and lead cabinet', 'storage', 'cabinet', (.85, 1.30, .42, 1, True), 'steel', 'calibration', 'R'),
    ('wire-strippers', 'bench', 'Termination bench', 'bench', 'bench', (1.45, .65, .90, True, True), 'part', 'floor', 'R'),
    ('wire-strippers', 'bin', 'Copper offcut bin', 'waste', 'bin', (.70, .50, .50, False), 'metal', 'offcuts', 'CR'),
    ('fish-tape', 'reel', 'Fish tape reel stand', 'storage', 'reel', (.60, 1.05, .30), 'metal', 'issue', 'R'),
    ('fish-tape', 'frame', 'Conduit pull frame', 'stand', 'cantilever', (1.45, 1.65, .40, 3), 'metal', 'rigs', 'L'),
    ('conduit-bender', 'bench', 'Conduit bending bench', 'bench', 'vice-bench', (1.45, .70, .90), 'steel', 'floor', 'L'),
    ('conduit-bender', 'rack', 'Conduit stock rack', 'stock', 'pipe-rack', (1.30, 1.70, .45, 4), 'metal', 'stock', 'L'),
    ('tubing-cutter', 'bench', 'Tube cutting bench', 'bench', 'vice-bench', (1.45, .65, .90), 'steel', 'learned', 'R'),
    ('tubing-cutter', 'hopper', 'Tube offcut hopper', 'waste', 'hopper', (.85, 1.00, .55), 'metal', 'offcuts', 'R'),
    ('pipe-wrench', 'stand', 'Pipe vice stand', 'machine', 'pedestal', (.26, 1.20, [.40, .34, .34]), 'steel', 'floor', 'R'),
    ('pipe-wrench', 'rack', 'Wrench size rack', 'storage', 'rack', (1.20, 1.40, .40, 4), 'metal', 'issue', 'R'),
    ('crimper', 'bench', 'Lug crimping bench', 'bench', 'bench', (1.40, .65, .88, True, False), 'part', 'learned', 'L'),
    ('crimper', 'drawers', 'Die and lug drawers', 'storage', 'drawers', (.85, 1.00, .48, 4), 'steel', 'consumables', 'L'),
    ('manifold-gauge', 'rig', 'Refrigerant charging rig', 'machine', 'cantilever', (1.20, 1.60, .45, 3), 'metal', 'rigs', 'R'),
    ('manifold-gauge', 'cabinet', 'Gauge set cabinet', 'storage', 'cabinet', (.80, 1.20, .40, 1, True), 'steel', 'calibration', 'L'),
    ('torpedo-level', 'table', 'Grade setting table', 'bench', 'table', (1.45, .80, .80, True), 'wood', 'setting', 'L'),
    ('torpedo-level', 'shelf', 'Level and plumb shelf', 'storage', 'wall-shelf', (.90, .65, .24, 2), 'wood', 'marking', 'WR'),
    ('voltage-tester', 'post', 'Prove-dead post', 'stand', 'pedestal', (.18, 1.22, [.26, .28, .20]), 'post', 'live', 'CL'),
    ('voltage-tester', 'board', 'Tester issue board', 'board', 'wall-peg', (1.00, .85, 4), 'paint', 'issue', 'WL'),
    ('channel-locks', 'bench', 'Service fitting bench', 'bench', 'vice-bench', (1.45, .70, .90), 'steel', 'plant', 'L'),
    ('channel-locks', 'board', 'Plier wall board', 'board', 'wall-peg', (1.20, .90, 6), 'paint', 'return|plant', 'WR'),
    ('nut-driver', 'bench', 'Panel build bench', 'bench', 'bench', (1.45, .70, .88, True, True), 'steel', 'floor', 'R'),
    ('nut-driver', 'drawers', 'Driver and screw drawers', 'storage', 'drawers', (.90, 1.05, .45, 4), 'metal', 'consumables', 'R'),

    # ------------------------------------------------- energy -------------
    ('lineman-pliers', 'bench', 'Overhead framing bench', 'bench', 'vice-bench', (1.45, .75, .90), 'steel', 'floor', 'L'),
    ('lineman-pliers', 'board', 'Hand tool board', 'board', 'wall-peg', (1.20, .95, 6), 'paint', 'issue', 'WL'),
    ('hot-stick', 'rack', 'Live-line stick rack', 'storage', 'pipe-rack', (1.20, 1.70, .45, 3), 'wood', 'issue', 'R'),
    ('hot-stick', 'frame', 'Live-line practice frame', 'stand', 'cantilever', (1.45, 1.70, .40, 3), 'wood', 'rigs', 'L'),
    ('cable-cutter', 'bench', 'Cable cutting bench', 'bench', 'vice-bench', (1.45, .80, .90), 'steel', 'floor', 'R'),
    ('cable-cutter', 'bin', 'Cable offcut bin', 'waste', 'bin', (.90, .60, .60, False), 'metal', 'offcuts', 'CR'),
    ('clamp-meter', 'bench', 'Load reading bench', 'bench', 'bench', (1.40, .65, .88, True, False), 'part', 'fault-finding', 'R'),
    ('clamp-meter', 'cabinet', 'Meter calibration cabinet', 'storage', 'cabinet', (.85, 1.30, .42, 1, True), 'steel', 'calibration', 'L'),
    ('megohmmeter', 'rig', 'Insulation test rig', 'machine', 'cantilever', (1.30, 1.60, .45, 3), 'metal', 'rigs', 'R'),
    ('megohmmeter', 'drawers', 'Test set drawers', 'storage', 'drawers', (.85, 1.00, .50, 3), 'steel', 'issue', 'L'),
    ('gas-detector', 'post', 'Leak survey post', 'stand', 'pedestal', (.18, 1.25, [.28, .28, .22]), 'post', 'checks', 'CL'),
    ('gas-detector', 'shelf', 'Detector charge shelf', 'storage', 'wall-shelf', (.90, .60, .24, 2), 'metal', 'calibration', 'WR'),
    ('valve-key', 'stand', 'Valve operating stand', 'machine', 'pedestal', (.24, 1.15, [.34, .30, .30]), 'steel', 'plant', 'R'),
    ('valve-key', 'cradle', 'Valve key cradle', 'storage', 'wall-cradle', (1.30, .36), 'metal', 'return|plant', 'WL'),
    ('pipe-locator', 'table', 'Trace and mark table', 'bench', 'table', (1.45, .85, .80, True), 'wood', 'setting', 'L'),
    ('pipe-locator', 'cabinet', 'Locator set cabinet', 'storage', 'cabinet', (.80, 1.25, .42, 1, True), 'steel', 'issue|setting', 'R'),
    ('torque-screwdriver', 'bench', 'Terminal torque bench', 'bench', 'bench', (1.30, .60, .88, True, False), 'part', 'acceptance', 'R'),
    ('torque-screwdriver', 'drawers', 'Bit and driver drawers', 'storage', 'drawers', (.80, .95, .45, 3), 'metal', 'consumables', 'L'),
    ('splice-shell', 'bench', 'Splice build bench', 'bench', 'bench', (1.45, .70, .90, True, True), 'steel', 'learned', 'L'),
    ('splice-shell', 'crates', 'Splice shell crates', 'stock', 'crates', (1.00, .80, .55, 3), 'part', 'stock', 'CL'),
    ('sharpshooter', 'rack', 'Long handle tool rack', 'storage', 'pipe-rack', (1.30, 1.70, .45, 4), 'wood', 'issue|plant', 'L'),
    ('sharpshooter', 'crates', 'Backfill sample crates', 'stock', 'crates', (1.10, .75, .55, 3), 'part', 'stock|floor', 'CR'),
    ('grounding-set', 'frame', 'Earthing practice frame', 'stand', 'cantilever', (1.40, 1.65, .40, 3), 'metal', 'live', 'R'),
    ('grounding-set', 'reel', 'Earth lead reel', 'storage', 'reel', (.60, 1.05, .28), 'metal', 'issue', 'R'),

    # ------------------------------------------------- earthworks ---------
    ('grade-rod', 'rack', 'Grade rod rack', 'storage', 'pipe-rack', (1.20, 1.70, .40, 3), 'wood', 'issue', 'L'),
    ('grade-rod', 'table', 'Level book table', 'bench', 'table', (1.20, .70, .80, True), 'wood', 'setting', 'L'),
    ('laser-level', 'tripod', 'Instrument tripod stand', 'stand', 'tree', (1.50, 3, .36), 'metal', 'control point', 'CR'),
    ('laser-level', 'cabinet', 'Instrument case cabinet', 'storage', 'cabinet', (.90, 1.30, .50, 2, True), 'steel', 'calibration', 'R'),
    ('mattock', 'rack', 'Hand digging tool rack', 'storage', 'pipe-rack', (1.30, 1.65, .45, 4), 'wood', 'issue', 'R'),
    ('mattock', 'crates', 'Ground condition crates', 'stock', 'crates', (1.10, .80, .55, 3), 'part', 'stock', 'CL'),
    ('round-shovel', 'bin', 'Spoil bin', 'waste', 'bin', (1.00, .70, .65, False), 'metal', 'offcuts', 'CR'),
    ('round-shovel', 'pallet', 'Bedding material stack', 'stock', 'pallet', (1.30, .50, .75, 4), 'wood', 'stock', 'R'),
    ('grease-gun', 'bench', 'Greasing bench', 'bench', 'bench', (1.45, .70, .88, True, True), 'part', 'plant', 'R'),
    ('grease-gun', 'cabinet', 'Grease and nipple cabinet', 'storage', 'cabinet', (.85, 1.25, .45, 2, False), 'cone', 'consumables', 'L'),
    ('pry-bar', 'cradle', 'Pry bar cradle', 'storage', 'wall-cradle', (1.40, .38), 'metal', 'return', 'WR'),
    ('pry-bar', 'trestle', 'Pipe laying trestle', 'stand', 'trestle', (1.45, .90, .55), 'wood', 'floor', 'L'),
    ('plate-tamper', 'stand', 'Compaction plate stand', 'machine', 'pedestal', (.26, 1.10, [.44, .36, .40]), 'metal', 'plant', 'R'),
    ('plate-tamper', 'crates', 'Compaction test crates', 'stock', 'crates', (1.00, .75, .55, 3), 'part', 'acceptance', 'CR'),
    ('string-line', 'reel', 'Line and peg reel', 'storage', 'reel', (.55, .95, .24), 'metal', 'marking', 'R'),
    ('string-line', 'post', 'Offset peg post', 'stand', 'pedestal', (.18, 1.20, [.22, .26, .18]), 'post', 'control point', 'CL'),
    ('marking-wand', 'cart', 'Service marking cart', 'trolley', 'cart', (.90, 1.00, .55), 'part', 'marking|plant', 'CR'),
    ('marking-wand', 'shelf', 'Marking paint shelf', 'storage', 'wall-shelf', (1.00, .70, .26, 3), 'cone', 'consumables', 'WR'),
    ('socket-set', 'bench', 'Plant fitting bench', 'bench', 'vice-bench', (1.45, .75, .90), 'steel', 'plant', 'L'),
    ('socket-set', 'gangbox', 'Socket gang box', 'storage', 'gang-box', (1.20, .85, .60), 'steel', 'issue', 'CL'),
    ('pin-punch', 'bench', 'Pin and bush bench', 'bench', 'bench', (1.45, .70, .90, True, True), 'steel', 'learned', 'R'),
    ('pin-punch', 'drawers', 'Punch and pin drawers', 'storage', 'drawers', (.85, 1.00, .45, 4), 'metal', 'consumables', 'R'),
    ('tire-gauge', 'stand', 'Tyre inflation stand', 'machine', 'pedestal', (.22, 1.15, [.30, .30, .26]), 'metal', 'checked out', 'R'),
    ('tire-gauge', 'board', 'Pressure chart board', 'board', 'wall-board', (1.10, .80, 4, False), 'paint', 'checked out', 'WL'),

    # ------------------------------------------------- industry -----------
    ('chipping-hammer', 'bench', 'Weld dressing bench', 'bench', 'vice-bench', (1.45, .75, .90), 'steel', 'floor', 'L'),
    ('chipping-hammer', 'bin', 'Slag and scale bin', 'waste', 'drum', (.28, .70), 'metal', 'offcuts', 'CR'),
    ('flange-spreader', 'rig', 'Flange break rig', 'machine', 'cantilever', (1.40, 1.55, .50, 2), 'steel', 'rigs', 'R'),
    ('flange-spreader', 'crates', 'Gasket and stud crates', 'stock', 'crates', (1.00, .80, .55, 3), 'part', 'consumables', 'CL'),
    ('alignment-pins', 'table', 'Flange alignment table', 'bench', 'table', (1.45, .90, .80, True), 'steel', 'setting', 'L'),
    ('alignment-pins', 'drawers', 'Alignment pin drawers', 'storage', 'drawers', (.80, .95, .45, 3), 'steel', 'issue', 'R'),
    ('feeler-gauge', 'bench', 'Clearance check bench', 'bench', 'bench', (1.30, .65, .88, True, False), 'part', 'acceptance', 'R'),
    ('feeler-gauge', 'shelf', 'Feeler and shim shelf', 'storage', 'wall-shelf', (.85, .60, .22, 2), 'metal', 'calibration', 'WR'),
    ('micrometer', 'plate', 'Metrology bench', 'bench', 'bench', (1.40, .80, .90, True, True), 'steel', 'criteria', 'L'),
    ('micrometer', 'cabinet', 'Micrometer set cabinet', 'storage', 'cabinet', (.80, 1.25, .40, 1, True), 'wood', 'calibration', 'L'),
    ('file-set', 'bench', 'Filing and fitting bench', 'bench', 'vice-bench', (1.45, .70, .90), 'wood', 'learned', 'R'),
    ('file-set', 'board', 'File and rasp board', 'board', 'wall-peg', (1.10, .90, 6), 'paint', 'issue', 'WL'),
    ('deburring-tool', 'bench', 'Deburring bench', 'bench', 'bench', (1.40, .65, .88, True, True), 'part', 'floor', 'R'),
    ('deburring-tool', 'hopper', 'Swarf and burr hopper', 'waste', 'hopper', (.85, 1.00, .55), 'metal', 'offcuts', 'R'),
    ('dial-indicator', 'stand', 'Shaft runout stand', 'stand', 'pedestal', (.20, 1.25, [.30, .26, .24]), 'metal', 'acceptance', 'R'),
    ('dial-indicator', 'drawers', 'Indicator and base drawers', 'storage', 'drawers', (.80, .95, .45, 3), 'steel', 'calibration', 'R'),
    ('bearing-puller', 'press', 'Bearing press', 'machine', 'press', (1.20, 1.70, .60), 'steel', 'plant', 'L'),
    ('bearing-puller', 'rack', 'Puller and leg rack', 'storage', 'rack', (1.10, 1.35, .45, 3), 'steel', 'issue|plant', 'L'),
    ('soapstone', 'table', 'Plate marking table', 'bench', 'table', (1.45, .95, .80, True), 'steel', 'marking', 'R'),
    ('soapstone', 'shelf', 'Soapstone and scribe shelf', 'storage', 'wall-shelf', (.80, .60, .22, 2), 'wood', 'consumables', 'WR'),
    ('weld-gauge', 'bench', 'Weld profile bench', 'bench', 'bench', (1.30, .70, .88, True, False), 'steel', 'criteria', 'L'),
    ('weld-gauge', 'cabinet', 'Weld sample cabinet', 'storage', 'cabinet', (.95, 1.35, .42, 2, True), 'wood', 'acceptance|level', 'R'),
    ('pipe-stand-wrench', 'stand', 'Roller pipe stand', 'stand', 'pedestal', (.26, 1.05, [.42, .28, .36]), 'metal', 'floor', 'CL'),
    ('pipe-stand-wrench', 'rack', 'Pipe stock rack', 'stock', 'pipe-rack', (1.40, 1.70, .50, 4), 'metal', 'stock', 'L'),

    # ------------------------------------------------- transport ----------
    ('track-wrench', 'bench', 'Rail fastening bench', 'bench', 'vice-bench', (1.45, .75, .90), 'steel', 'floor', 'L'),
    ('track-wrench', 'cradle', 'Track wrench cradle', 'storage', 'wall-cradle', (1.40, .38), 'metal', 'issue', 'WL'),
    ('spike-puller', 'trestle', 'Sleeper work trestle', 'stand', 'trestle', (1.45, .80, .60), 'wood', 'floor', 'R'),
    ('spike-puller', 'bin', 'Spike and clip bin', 'stock', 'bin', (.85, .55, .55, False), 'metal', 'stock', 'CR'),
    ('rail-gauge', 'table', 'Gauge and cant table', 'bench', 'table', (1.45, .90, .80, True), 'steel', 'setting', 'L'),
    ('rail-gauge', 'cabinet', 'Track gauge cabinet', 'storage', 'cabinet', (.90, 1.30, .42, 2, True), 'steel', 'calibration', 'R'),
    ('torque-multiplier', 'bench', 'High torque bench', 'bench', 'bench', (1.45, .75, .90, True, True), 'steel', 'plant', 'R'),
    ('torque-multiplier', 'drawers', 'Multiplier and socket drawers', 'storage', 'drawers', (.90, 1.05, .50, 4), 'steel', 'issue', 'R'),
    ('compression-tester', 'rig', 'Engine test rig', 'machine', 'cantilever', (1.40, 1.60, .50, 3), 'metal', 'rigs', 'L'),
    ('compression-tester', 'cabinet', 'Tester adaptor cabinet', 'storage', 'cabinet', (.80, 1.20, .40, 1, True), 'steel', 'calibration', 'L'),
    ('brake-tool', 'bench', 'Brake overhaul bench', 'bench', 'bench', (1.45, .75, .90, True, True), 'part', 'plant', 'L'),
    ('brake-tool', 'crates', 'Brake shoe crates', 'stock', 'crates', (1.00, .80, .55, 3), 'part', 'stock', 'CL'),
    ('wheel-chock', 'stack', 'Chock stack', 'stock', 'crates', (.90, .70, .55, 3), 'wood', 'plant', 'CR'),
    ('wheel-chock', 'board', 'Securing chart board', 'board', 'wall-board', (1.10, .80, 4, False), 'paint', 'checked out', 'WL'),
    ('signal-tester', 'frame', 'Signal circuit frame', 'stand', 'cantilever', (1.40, 1.65, .40, 3), 'metal', 'rigs', 'R'),
    ('signal-tester', 'bench', 'Relay test bench', 'bench', 'bench', (1.45, .70, .88, True, False), 'steel', 'fault-finding', 'R'),
    ('alignment-bar', 'cradle', 'Alignment bar cradle', 'storage', 'cradle', (1.45, .80, .45), 'steel', 'issue', 'L'),
    ('alignment-bar', 'table', 'Coupling alignment table', 'bench', 'table', (1.45, .85, .80, True), 'steel', 'setting', 'R'),
    ('impact-gun', 'bench', 'Wheel service bench', 'bench', 'bench', (1.45, .75, .90, True, True), 'steel', 'plant', 'R'),
    ('impact-gun', 'reel', 'Air hose reel', 'storage', 'wall-reel', (.42, .60, .22), 'metal', 'consumables', 'WR'),
    ('creeper-light', 'rack', 'Creeper and light rack', 'storage', 'rack', (1.20, 1.30, .50, 3), 'metal', 'issue|plant', 'R'),
    ('creeper-light', 'cart', 'Under-vehicle cart', 'trolley', 'cart', (.95, .95, .55), 'part', 'plant', 'CR'),
    ('cable-height-stick', 'rack', 'Height stick rack', 'storage', 'pipe-rack', (1.20, 1.70, .40, 3), 'wood', 'issue|stock', 'L'),
    ('cable-height-stick', 'post', 'Contact wire height post', 'stand', 'pedestal', (.18, 1.30, [.24, .28, .20]), 'post', 'control point', 'CL'),

    # ------------------------------------------------- control ------------
    ('prism-pole', 'rack', 'Prism pole rack', 'storage', 'pipe-rack', (1.10, 1.70, .40, 3), 'metal', 'issue', 'R'),
    ('prism-pole', 'post', 'Backsight target post', 'stand', 'pedestal', (.18, 1.30, [.22, .30, .18]), 'post', 'control point', 'CR'),
    ('auto-level', 'table', 'Booking and reduction table', 'bench', 'table', (1.40, .80, .80, True), 'wood', 'setting', 'L'),
    ('auto-level', 'cabinet', 'Level instrument cabinet', 'storage', 'cabinet', (.90, 1.30, .50, 2, True), 'steel', 'calibration', 'L'),
    ('field-tripod', 'stand', 'Tripod stand', 'stand', 'tree', (1.45, 3, .36), 'wood', 'control point', 'CL'),
    ('field-tripod', 'rack', 'Tripod and staff rack', 'storage', 'rack', (1.20, 1.45, .45, 3), 'wood', 'issue', 'L'),
    ('gas-monitor', 'bench', 'Bump test bench', 'bench', 'bench', (1.30, .65, .88, True, False), 'part', 'calibration', 'R'),
    ('gas-monitor', 'crates', 'Entry equipment crates', 'stock', 'crates', (1.00, .80, .55, 3), 'part', 'issue', 'CR'),
    ('sampling-pump', 'bench', 'Air sampling bench', 'bench', 'bench', (1.40, .70, .88, True, True), 'part', 'acceptance', 'L'),
    ('sampling-pump', 'cabinet', 'Sample media cabinet', 'storage', 'cabinet', (.85, 1.30, .40, 2, True), 'cone', 'consumables', 'R'),
    ('decon-sprayer', 'tank', 'Decontamination tank', 'vessel', 'tank', (.34, 1.00), 'part', 'return', 'CR'),
    ('decon-sprayer', 'shelf', 'Decon solution shelf', 'storage', 'wall-shelf', (1.00, .70, .26, 3), 'cone', 'consumables', 'WR'),
    ('hepa-vac', 'stand', 'Filtered vacuum stand', 'machine', 'pedestal', (.26, 1.20, [.40, .40, .36]), 'metal', 'plant', 'R'),
    ('hepa-vac', 'crates', 'Filter stock crates', 'stock', 'crates', (.95, .75, .50, 3), 'part', 'stock', 'CL'),
    ('anemometer', 'post', 'Air flow survey post', 'stand', 'pedestal', (.18, 1.28, [.26, .28, .20]), 'metal', 'checks', 'R'),
    ('anemometer', 'shelf', 'Flow instrument shelf', 'storage', 'wall-shelf', (.90, .65, .24, 2), 'metal', 'calibration', 'WL'),
    ('sound-meter', 'bench', 'Noise survey bench', 'bench', 'bench', (1.30, .65, .88, True, False), 'part', 'fault-finding', 'L'),
    ('sound-meter', 'cabinet', 'Acoustic calibrator cabinet', 'storage', 'cabinet', (.75, 1.20, .40, 1, True), 'steel', 'calibration|acceptance', 'R'),
    ('lux-meter', 'table', 'Illuminance survey table', 'bench', 'table', (1.20, .70, .80, True), 'wood', 'criteria', 'R'),
    ('lux-meter', 'shelf', 'Photometry shelf', 'storage', 'wall-shelf', (.85, .60, .22, 2), 'metal', 'acceptance', 'WR'),
    ('moisture-meter', 'bench', 'Moisture survey bench', 'bench', 'bench', (1.30, .70, .88, True, True), 'wood', 'acceptance', 'R'),
    ('moisture-meter', 'crates', 'Reference sample crates', 'stock', 'crates', (1.00, .75, .50, 3), 'wood', 'criteria', 'CL'),
    ('rope-grab', 'frame', 'Fall arrest practice frame', 'stand', 'cantilever', (1.40, 1.70, .40, 3), 'metal', 'rigs', 'L'),
    ('rope-grab', 'rack', 'Rope and grab rack', 'storage', 'rack', (1.10, 1.45, .45, 3), 'metal', 'issue|training area', 'R'),
]

CRIB_PROPS = []
for _tool, _sfx, _name, _fam, _form, _args, _mat, _tok, _spot in CRIB_ROWS:
    _t = CRIB_TOOL[_tool]
    _anchor, _walls, _approach = SPOTS[_spot]
    CRIB_PROPS.append(piece(
        f'{_tool}-{_sfx}', _name, _fam, _form, _args, _mat,
        f'{FAMILIES[_fam]}, in a hall whose crib issues the '
        f'{_t["name"].lower()} — which {_t["use"]}',
        tokens=_tok.split('|'), anchor=_anchor, walls=_walls,
        approach=_approach,
        crib_tools=[_tool], district=_t['district'], catalogue='district'))

# ---------------------------------------------------------------------------
# THE TWO CATALOGUES.
#
#   `props`           — what web/build_3d.py stands today. A piece is here
#                       because the page has exactly two ways of choosing
#                       furniture for a room: the room's STRAND, which is the
#                       same eleven rooms in all 111 halls, and the room's own
#                       CONDITIONS record, which is per hall and per room.
#   `crib_furniture`  — the district catalogue. A piece is here because it
#                       belongs to ONE district's tool crib, and the page has
#                       no hall dimension to select it with: placeRoomProps()
#                       reads D.props.by_strand[r.strand] and nothing else, so
#                       listing a suction-cup rack under `envelope` furniture
#                       would stand it in every ironworkers' hall too. The
#                       fit-out is computed, checked and published; it is not
#                       drawn, and this pack says so rather than pretending.
# ---------------------------------------------------------------------------
PROPS = COND_PROPS + SHOP_PROPS
ALL_FURNITURE = PROPS + CRIB_PROPS
BY_ID = {p['id']: p for p in ALL_FURNITURE}
assert len(BY_ID) == len(ALL_FURNITURE), 'two pieces share an id'

for p in ALL_FURNITURE:
    assert p['family'] in FAMILIES, f'{p["id"]}: {p["family"]} is not a family'
    assert p['material'] in MATERIALS, \
        (f'{p["id"]}: mat.{p["material"]} is outside the seven materials this '
         f'pack merges into; an eighth is a draw call in every hall')
    assert p['material'] in PAGE_MATERIALS, \
        f'{p["id"]}: mat.{p["material"]} is not a material the page has'
    assert p['merges'] in MERGES, f'{p["id"]}: {p["merges"]} is not a merge mode'
    assert p['id'] not in YARD_PROPS, \
        f'{p["id"]} collides with the page\'s existing yard prop table'
    assert TRI_FLOOR <= p['tri_budget']['tris'] <= TRI_CEIL, \
        (f'{p["id"]}: {p["tri_budget"]["tris"]} tri is outside the measured '
         f'band {TRI_FLOOR}-{TRI_CEIL}')
    assert p['recipe']['tris'] == tris_of(p['recipe']['parts']), \
        f'{p["id"]}: the stated triangle count is not the one the recipe adds up to'
    assert len(p['why']) > 30, f'{p["id"]}: say what it is for'
    assert len(p['merges_why']) > 30, f'{p["id"]}: say why it merges that way'
    assert p['merges'] != 'own-mesh' or 'raycast' in p['merges_why'], \
        (f'{p["id"]}: own-mesh needs a raycast or motion reason — an unpooled '
         f'prop is a whole draw call')

for f in FAMILIES:
    assert any(p['family'] == f for p in PROPS), \
        f'the family "{f}" is declared and nothing the page stands belongs to it'
assert FORM_USED == set(FORMS), \
    ('a form is declared and nothing is cut from it: '
     + ', '.join(sorted(set(FORMS) - FORM_USED)))

# No piece may reuse a room label or a station name as its own name, and no
# two pieces of furniture may share a name either — three hundred of them is
# exactly the scale at which a duplicate stops being obvious.
_labels = {r['label'].lower() for r in ROOM_OF.values()}
_stations = {s['name'].lower() for s in STATIONS['stations']}
_names = {}
for p in ALL_FURNITURE:
    low = p['name'].lower()
    assert low not in _labels, \
        f'{p["id"]}: "{p["name"]}" is a room label; read it, do not copy it'
    assert low not in _stations, \
        f'{p["id"]}: "{p["name"]}" is a station name owned by stations/'
    assert low not in _names, \
        f'{p["id"]} and {_names[low]} are both called "{p["name"]}"'
    _names[low] = p['id']

# ---------------------------------------------------------------------------
# THE CRIB CROSS-LINK. Every tool a piece of furniture names is a tool one of
# the eight cribs carries, and a district piece's district is the district of
# the crib that carries its tool — not a field somebody typed twice.
# ---------------------------------------------------------------------------
LINKED = [p for p in ALL_FURNITURE if 'crib' in p]
for p in LINKED:
    for t in p['crib']['tools']:
        assert t['id'] in CRIB_TOOL, f'{p["id"]}: no crib carries {t["id"]}'
        assert t['name'] == CRIB_TOOL[t['id']]['name'], \
            f'{p["id"]}: the name it prints for {t["id"]} is not the crib\'s'
        assert t['use'] == CRIB_TOOL[t['id']]['use'], \
            f'{p["id"]}: the use it prints for {t["id"]} is not the crib\'s'
    if 'district' in p:
        assert {t['district'] for t in p['crib']['tools']} == {p['district']}, \
            (f'{p["id"]}: it stands in the {p["district"]} district and names '
             f'a tool another district\'s crib carries')
TOOLS_COVERED = sorted({t['id'] for p in LINKED for t in p['crib']['tools']})

# ---------------------------------------------------------------------------
# BY STRAND. A prop stands in a strand because one of its tokens appears in
# that strand's own purpose line. Nothing is assigned.
# ---------------------------------------------------------------------------
STRAND_PROPS = [p for p in PROPS if p['derive']['from'] == 'room.purpose']
HAZARD_PROPS = [p for p in PROPS if p['derive']['from'] != 'room.purpose']
assert STRAND_PROPS and HAZARD_PROPS


def strands_for(p):
    out = []
    for s in STRANDS:
        text = ROOM_OF[s]['purpose'].lower()
        for tok in p['derive']['tokens']:
            if tok in text:
                out.append((s, tok))
                break
    return out


BY_STRAND = {s: [] for s in STRANDS}
MATCHES = []
for p in STRAND_PROPS:
    hits = strands_for(p)
    assert hits, (f'{p["id"]}: none of its tokens {p["derive"]["tokens"]} '
                  f'appears in any room purpose — a prop that stands nowhere')
    for s, tok in hits:
        BY_STRAND[s].append({'prop': p['id'], 'matched': tok, 'in': 'purpose'})
        MATCHES.append((p['id'], s, tok))

for pid, s, tok in MATCHES:
    assert tok in ROOM_OF[s]['purpose'].lower(), \
        f'{pid} landed in {s}, whose purpose does not contain "{tok}"'
    assert tok in BY_ID[pid]['derive']['tokens'], \
        f'{pid} matched "{tok}", which it never declared'

for s in STRANDS:
    assert BY_STRAND[s], \
        (f'{s} ("{ROOM_OF[s]["label"]}") gets no prop: every strand must have '
         f'something standing in it or the room is still an empty box')

for p in STRAND_PROPS + CRIB_PROPS:
    for tok in p['derive']['tokens']:
        assert any(tok in ROOM_OF[s]['purpose'].lower() for s in STRANDS), \
            f'{p["id"]}: the token "{tok}" matches no room purpose'

# ---- and the district catalogue, by district and strand -------------------
BY_DISTRICT = {d: {s: [] for s in STRANDS} for d in DISTRICTS}
for p in CRIB_PROPS:
    hits = strands_for(p)
    assert hits, f'{p["id"]}: it answers to no room purpose'
    for s, tok in hits:
        BY_DISTRICT[p['district']][s].append({'prop': p['id'], 'matched': tok,
                                              'in': 'purpose'})
for d in DISTRICTS:
    assert any(BY_DISTRICT[d][s] for s in STRANDS), f'{d} fits out no room'

# ---------------------------------------------------------------------------
# HAZARD PROPS. Derived from the room's own conditions record and nothing
# else. The trigger is a set of PPE items; a room gets the prop when its own
# record asks for one of them.
# ---------------------------------------------------------------------------
for p in HAZARD_PROPS:
    for tok in p['derive']['ppe_any']:
        assert tok == '*any*' or tok in PPE_VOCAB, \
            (f'{p["id"]}: "{tok}" is not protective equipment the surfaces '
             f'registry ever asks for')


def hazard_props_for(ppe):
    """Which hazard props this room's OWN record asks for."""
    out = []
    for p in HAZARD_PROPS:
        want = p['derive']['ppe_any']
        if want == ['*any*']:
            if ppe:
                out.append(p['id'])
        elif set(want) & set(ppe):
            out.append(p['id'])
    return out


HZ = FINISHES['hazard_conditions']
for p in HAZARD_PROPS:
    want = set(p['derive']['ppe_any'])
    p['derive']['triggered_by_hazards'] = sorted(
        h for h in HAZARD_VOCAB if h in HZ and set(HZ[h]['ppe']) & want)
    p['derive']['rule'] = (
        'a room gets this when its own conditions.ppe is non-empty'
        if want == {'*any*'} else
        'a room gets this when its own conditions.ppe names any of '
        + ', '.join(sorted(want)))
    assert want == {'*any*'} or p['derive']['triggered_by_hazards'], \
        (f'{p["id"]}: no hazard in the surfaces registry adds the equipment '
         f'it is keyed to, so nothing about the room explains why it is there')

PLACED = {}       # (slug, strand) -> {'strand': [...], 'hazard': [...]}
for slug, rooms in COND.items():
    for strand, c in rooms.items():
        PLACED[(slug, strand)] = {
            'strand': [m['prop'] for m in BY_STRAND[strand]],
            'hazard': hazard_props_for(c['ppe']),
        }

_ppe_rooms = 0
for (slug, strand), got in PLACED.items():
    ppe = COND[slug][strand]['ppe']
    if ppe:
        _ppe_rooms += 1
        assert 'ppe-station' in got['hazard'], \
            (f'{slug}/{strand} requires {ppe} and got no PPE prop — a room '
             f'that asks for equipment and shows none is the bug')
    else:
        assert 'ppe-station' not in got['hazard'], \
            f'{slug}/{strand} requires no PPE and got a PPE station anyway'
    for pid in got['hazard']:
        want = BY_ID[pid]['derive']['ppe_any']
        assert want == ['*any*'] or set(want) & set(ppe), \
            f'{slug}/{strand}: {pid} stands there on no record at all'
assert _ppe_rooms == sum(1 for c in COND.values() for r in c.values() if r['ppe'])

# ---------------------------------------------------------------------------
# LAYOUT. How many fit, and whether the smallest room that admits a piece can
# actually hold the layout it declares.
# ---------------------------------------------------------------------------
def room_metres(w_units, h_units):
    """The floor the page actually draws, which is inset from the grid."""
    return (w_units * U_M - FLOOR_INSET, h_units * U_M - FLOOR_INSET)


def count_in(p, w_units, h_units):
    lay = p['layout']
    _, d_m = room_metres(w_units, h_units)
    if lay['anchor'] == 'back-corner':
        per_wall = 1
    else:
        run = d_m - FRONT_CLEAR_M - BACK_RESERVE_M
        along = p['size_m'][0]
        per_wall = max(0, math.floor((run + GAP_M) / (along + GAP_M)))
    return min(lay['max_per_room'], per_wall * len(lay['walls']))


for p in ALL_FURNITURE:
    if p['derive']['from'] == 'room.purpose':
        admits = [s for s, _ in strands_for(p)]
    else:
        admits = sorted({strand for (slug, strand), got in PLACED.items()
                         if p['id'] in got['hazard']})
    assert admits, f'{p["id"]}: admitted by no strand at all'
    small = (min(SMALLEST[s][0] for s in admits),
             min(SMALLEST[s][1] for s in admits))
    w_m, d_m = room_metres(*small)
    n = count_in(p, *small)
    p['layout']['admitted_by'] = admits
    p['layout']['smallest_room'] = {
        'units': list(small), 'floor_m': [round(w_m, 2), round(d_m, 2)],
        'fits': n}

    assert n >= 1, (f'{p["id"]}: does not fit its own smallest room '
                    f'({w_m:.2f} x {d_m:.2f} m)')
    if p['layout']['anchor'] != 'back-corner':
        per_wall = math.ceil(n / len(p['layout']['walls']))
        need = per_wall * p['size_m'][0] + (per_wall - 1) * GAP_M
        have = d_m - FRONT_CLEAR_M - BACK_RESERVE_M
        assert need <= have + 1e-9, \
            (f'{p["id"]}: {per_wall} of them need {need:.2f} m of wall and the '
             f'smallest room has {have:.2f} m')
    depth = p['size_m'][2] + p['clearance_m']
    left = w_m - 2 * depth
    assert left >= 2 * BODY_R, \
        (f'{p["id"]}: leaves {left:.2f} m between opposite walls and a walker '
         f'needs {2 * BODY_R:.2f} m')
    top = p['layout']['base_y_m'] + (p['size_m'][1] / 2
                                     if p['layout']['anchor'] == 'wall-mounted'
                                     else p['size_m'][1])
    p['layout']['top_m'] = round(top, 3)
    if p['layout']['anchor'] == 'wall-mounted':
        assert top <= PART_TOP + 1e-9, \
            (f'{p["id"]}: hangs to {top:.2f} m on a partition that stops at '
             f'{PART_TOP:.2f} m')
        assert p['layout']['base_y_m'] - p['size_m'][1] / 2 >= FLOOR_TOP, \
            f'{p["id"]}: hangs through the floor'
    else:
        assert abs(p['layout']['base_y_m'] - FLOOR_TOP) < 1e-9, \
            f'{p["id"]}: stands on {p["layout"]["base_y_m"]} m, not on the floor'
        assert top <= LABEL_Y, \
            (f'{p["id"]}: rises to {top:.2f} m and the room sign hangs at '
             f'{LABEL_Y:.2f} m')
    for w in p['layout']['walls']:
        assert w in ('left', 'right'), f'{p["id"]}: {w} is not a wall'

# ---------------------------------------------------------------------------
# THE FIT-OUT, SIMULATED. The old arithmetic here asked each prop on its own
# whether it fitted the room, which is the question the page never asks: the
# page fills a wall from one end, and the piece that gets there first takes
# the metres. Twenty-nine props could be counted either way and the answer
# was close. Three hundred cannot: counted independently they would ask the
# hall for triangles no wall in it has room to stand.
#
# So the run is SHARED here exactly as the page shares it — one interval list
# per partition, floor pieces starting a body width in from the doorway end,
# wall-hung pieces starting at the wall, back corners one per side — and the
# budget below is what the walls answer, not what the catalogue asks for.
# This is still an UPPER BOUND: the page cuts doorways out of these runs and
# reserves the tools room's right wall for the district crib it already
# draws, and it reports the difference itself through window.__tc3dProps().
# ---------------------------------------------------------------------------
def stand_room(want_ids, w_units, h_units):
    rd = h_units * U_M
    inset = FLOOR_INSET / 2
    lo_floor = inset + FRONT_CLEAR_M
    lo_wall = inset
    hi = rd - inset - BACK_RESERVE_M
    used = {'left': [], 'right': []}
    corner = {'left': False, 'right': False}
    out = {}
    for pid in want_ids:
        p = BY_ID[pid]
        lay = p['layout']
        sw = p['size_m'][0]
        n = count_in(p, w_units, h_units)
        placed = 0
        if lay['anchor'] == 'back-corner':
            for wall in lay['walls']:
                if placed >= n:
                    break
                if not corner[wall]:
                    corner[wall] = True
                    placed += 1
        else:
            lo = lo_wall if lay['anchor'] == 'wall-mounted' else lo_floor
            for wall in lay['walls']:
                if placed >= n:
                    break
                cur = lo
                while placed < n and cur + sw <= hi:
                    clash = next((b for a, b in sorted(used[wall])
                                  if cur < b and cur + sw > a), None)
                    if clash is not None:
                        cur = clash + GAP_M
                        continue
                    used[wall].append((cur, cur + sw))
                    placed += 1
                    cur += sw + GAP_M
        if placed:
            out[pid] = placed
    return out


def want_for(slug, strand, with_district):
    got = PLACED[(slug, strand)]
    ids = list(got['hazard'])
    if with_district:
        ids += [m['prop'] for m in BY_DISTRICT[HALL_DISTRICT[slug]][strand]]
    ids += got['strand']
    return ids


def hall_cost(slug, with_district=False):
    plan = PLANS[slug]
    instances = tris = wanted = 0
    pooled_mats, instanced_types = set(), set()
    per_room, stood, rooms = {}, {}, {}
    for r in plan['rooms']:
        ids = want_for(slug, r['strand'], with_district)
        wanted += len(ids)
        got = stand_room(ids, r['w'], r['h'])
        here = 0
        for pid, n in got.items():
            p = BY_ID[pid]
            instances += n
            here += n
            tris += n * p['recipe']['tris']
            stood[pid] = stood.get(pid, 0) + n
            rooms[pid] = rooms.get(pid, 0) + 1
            if p['merges'] == 'pooled':
                pooled_mats.add(p['material'])
            elif p['merges'] == 'instanced':
                instanced_types.add(pid)
            else:
                instanced_types.add(pid + '#own')
        per_room[r['strand']] = here
    return {'props': instances, 'tris': tris,
            'calls': len(pooled_mats) + len(instanced_types),
            'pooled_materials': len(pooled_mats),
            'instanced_types': len(instanced_types),
            'offered': wanted, 'per_room': per_room, 'stood': stood,
            'rooms': rooms}


COSTS = {h['slug']: hall_cost(h['slug']) for h in HALLS}
PLAN_COSTS = {h['slug']: hall_cost(h['slug'], True) for h in HALLS}
props_per = [c['props'] for c in COSTS.values()]
tris_per = [c['tris'] for c in COSTS.values()]
calls_per = [c['calls'] for c in COSTS.values()]
offer_per = [c['offered'] for c in COSTS.values()]

for slug, c in COSTS.items():
    for strand, n in c['per_room'].items():
        assert n >= 1, f'{slug}/{strand} is still an empty box'

# NO DEAD FURNITURE. A piece the walls never find room for is a piece nobody
# will ever see, and a catalogue entry nobody will ever see is padding. Every
# prop must stand in at least one room of at least one hall under the fit-out
# the page actually runs, and every district piece must stand in at least one
# room of its own district under the plan.
_stood_anywhere = set()
for c in COSTS.values():
    _stood_anywhere |= set(c['stood'])
# and what the fit-out actually did with each piece, published on the piece
for p in ALL_FURNITURE:
    src = COSTS if p['catalogue'] == 'hall' else PLAN_COSTS
    p['fit_out'] = {
        'from': ('the fit-out the page runs today'
                 if p['catalogue'] == 'hall'
                 else 'the district plan, which the page cannot run yet'),
        'rooms': sum(c['rooms'].get(p['id'], 0) for c in src.values()),
        'instances': sum(c['stood'].get(p['id'], 0) for c in src.values())}
_never = [p['id'] for p in PROPS if p['id'] not in _stood_anywhere]
assert not _never, (
    'these props are offered to a room and the wall never has room for them, '
    'so nobody will ever see one: ' + ', '.join(_never))
_plan_stood = set()
for c in PLAN_COSTS.values():
    _plan_stood |= set(c['stood'])
_never_d = [p['id'] for p in CRIB_PROPS if p['id'] not in _plan_stood]
assert not _never_d, (
    'these district pieces never find a wall in their own district under the '
    'plan: ' + ', '.join(_never_d))

# ---------------------------------------------------------------------------
# THE CEILING, and where it comes from. web/eval_scene.mjs measures what a
# hall costs and states what it may cost; the difference is the headroom.
#
# THIS PACK USED TO TAKE HALF OF IT AND LEAVE HALF, because the eval's own
# comment names two packs expected to spend that headroom — "the kit and
# props packs". That split was wrong, and the sibling pack's own registry
# says so: kit/registry/kit.json budgets against the CAMPUS view, and its
# ceilings are the campus's headroom to the digit. The arithmetic is redone
# here rather than trusted: if the kit ever starts budgeting against the
# hall, these two assertions fail and the split has to come back.
KIT = json.load(open(ROOT / 'kit/registry/kit.json'))
assert KIT['pack_version'] == PACK_VERSION, \
    'one bundle version: the kit registry is a different build'
_campus = re.search(r'campus:\s*\{ calls: ([\d_]+), tris: ([\d_]+), '
                    r'meshes: ([\d_]+) \}', EVAL)
assert _campus, 'web/eval_scene.mjs no longer states the campus baseline'
CAMPUS_CALLS = int(_campus.group(1).replace('_', ''))
CAMPUS_TRIS = int(_campus.group(2).replace('_', ''))
KIT_BUDGETS = {
    'view': 'campus',
    'its_call_ceiling': KIT['budget']['draw_call_ceiling'],
    'campus_call_headroom': jsround(CAMPUS_CALLS * CALL_HEADROOM) - CAMPUS_CALLS,
    'its_tri_headroom': KIT['budget']['triangle_headroom_total'],
    'campus_tri_headroom': int(CAMPUS_TRIS * TRI_HEADROOM) - CAMPUS_TRIS,
    'why_it_matters': 'the hall headroom is not shared with it, so this pack '
                      'takes the hall headroom and keeps a tenth of it free '
                      'rather than taking half of it for no reason',
}
assert KIT_BUDGETS['its_call_ceiling'] == KIT_BUDGETS['campus_call_headroom'], \
    ('the kit\'s draw-call ceiling is no longer the campus headroom, so it '
     'may be budgeting against the hall after all and this pack may not take '
     'the whole hall headroom')
assert KIT_BUDGETS['its_tri_headroom'] == KIT_BUDGETS['campus_tri_headroom'], \
    'the kit\'s triangle headroom is no longer the campus headroom'
assert set(KIT['budget']['campuses']) and 'halls' not in KIT['budget'], \
    'the kit budgets per campus; if that changed, this split must be redone'
# ---------------------------------------------------------------------------
CALL_CEIL = CALL_HEADROOM_LEFT
TRI_HALL_CEIL = TRI_HEADROOM_LEFT
assert max(calls_per) <= CALL_CEIL, \
    (f'props add {max(calls_per)} draw calls to a hall. The eval measures '
     f'{BASE_CALLS} and permits {HALL_MAX_CALLS}, so {CALL_HEADROOM_LEFT} are '
     f'left for everything unbuilt and this pack may take {CALL_CEIL} of them')
assert max(tris_per) <= TRI_HALL_CEIL, \
    (f'props add {max(tris_per):,} triangles to a hall. The eval measures '
     f'{BASE_TRIS:,} and permits {HALL_MAX_TRIS:,}, so {TRI_HEADROOM_LEFT:,} '
     f'are left and this pack may take {TRI_HALL_CEIL:,} of them')
MARGIN = 0.10
for spent, ceil_, what in ((max(tris_per), TRI_HALL_CEIL, 'triangles'),
                           (max(calls_per), CALL_CEIL, 'draw calls')):
    assert spent <= ceil_ * (1 - MARGIN), \
        (f'props spend {spent:,} of {ceil_:,} {what} in the worst hall, which '
         f'leaves {(1 - spent / ceil_) * 100:.1f}% free and the policy is '
         f'{MARGIN * 100:.0f}%')
assert max(calls_per) < min(props_per), \
    ('props must cost fewer draw calls than there are props — one draw per '
     'prop across eleven rooms is the shape this check exists to refuse')
# and the district plan, priced against the same ceiling, so that the one
# page change it waits on is a known quantity rather than a hope
PLAN_CALLS = max(c['calls'] for c in PLAN_COSTS.values())
PLAN_TRIS = max(c['tris'] for c in PLAN_COSTS.values())
PLAN_PROPS = max(c['props'] for c in PLAN_COSTS.values())
assert PLAN_CALLS <= CALL_CEIL and PLAN_TRIS <= TRI_HALL_CEIL, \
    (f'the district fit-out would cost {PLAN_CALLS} calls and {PLAN_TRIS:,} '
     f'triangles, past what this pack may take')
# the whole argument of this pack, asserted rather than asserted in prose:
# ten times the vocabulary costs the same seven merged meshes
assert len({p['material'] for p in ALL_FURNITURE}) == len(MATERIALS), \
    'the catalogue grew past the seven materials it is allowed'
assert PLAN_CALLS == max(calls_per), \
    ('adding the district catalogue must not add a draw call: every piece in '
     'it pools into a material the hall already merges')

_mesh_after = BASE_MESHES + max(c['pooled_materials'] + c['instanced_types']
                                for c in COSTS.values())
assert _mesh_after > BASE_MESHES >= HALL_MIN_MESHES, \
    'props must add visible pieces to the hall, never remove them'

# ---------------------------------------------------------------------------
HONESTY = {
    'status': 'SCHEMATIC: every piece in this pack is a handful of boxes and '
              'cylinders built in the browser from the recipe printed here. '
              'No mesh is loaded, no model is vendored, no texture is '
              'fetched, and nothing is generated at view time.',
    'not_a_specification': 'These are shapes in a training environment. The '
                           'eyewash stand is a cylinder and a bowl standing '
                           'where a room record says corrosives are handled; '
                           'the extinguisher is a cylinder on a plate; the '
                           'press is a bed, a ram and a box with a dial on '
                           'it. They are not fixture specifications, not '
                           'rated appliances, not machine specifications, '
                           'not compliance artefacts, and not evidence that '
                           'any equipment has been provided anywhere. '
                           'Nothing in this pack should be read as a '
                           'safety-equipment specification, and a learner '
                           'who has walked past one has not been trained on '
                           'it.',
    'placement_is_derived': 'No piece is placed by hand. A shop piece stands '
                            'in a strand because a word it declares appears '
                            'in that strand\'s own purpose line in '
                            'web/interiors.py; a conditions piece stands in a '
                            'room because that room\'s own record in '
                            'surfaces/registry/finishes.json asks for the '
                            'protective equipment it is keyed to, and the '
                            'same registry\'s hazard table says which kind of '
                            'work adds that equipment; a district piece '
                            'belongs to the district whose crib carries the '
                            'tool it names, read from '
                            'tools/registry/toolcribs.json. The build fails '
                            'if a room requiring PPE gets no PPE prop.',
    'one_truth': 'No room label, purpose, footprint, illuminance figure, '
                 'hazard, PPE item, tool name or tool use sentence is typed '
                 'in this pack. The room table is imported from '
                 'web/interiors.py, the conditions are read from '
                 'surfaces/registry/finishes.json, the tools are read from '
                 'tools/registry/toolcribs.json and the district of a hall '
                 'from unions/registry/unions.json. The page\'s body radius, '
                 'eye height, grid unit, floor height, partition height, '
                 'room-label height and bench setback are parsed out of '
                 'web/build_3d.py, so a piece cannot be sized against a '
                 'constant the page does not use.',
    'measured_not_guessed': 'The triangle band is taken from a measurement of '
                            'six reference models made before anything here '
                            'was drawn: the blocks that read as real places '
                            'have a median mesh of 46 and 104 triangles. '
                            'Nothing from those files is vendored, copied or '
                            'named — what was taken is the finding that a '
                            'place is made of many small distinct pieces '
                            'rather than of dense ones.',
    'the_scarce_currency': 'A hall interior is draw-call bound, not triangle '
                           'bound. Every piece here pools or instances, none '
                           'takes a mesh of its own, and every one of the '
                           'three hundred names one of seven materials the '
                           'page already builds — so the catalogue grew more '
                           'than tenfold for no new material and no new draw '
                           'call at all. The budget block refuses a design '
                           'that would change that.',
    'the_wall_is_the_budget': 'A room has two partitions and about three '
                              'metres of usable run on each, and that — not '
                              'the GPU — is what decides how much furniture '
                              'stands in it. The fit-out below is simulated '
                              'against those metres with the run SHARED '
                              'between pieces, the way the page shares it, so '
                              'the triangle figure is what the walls hold '
                              'rather than what the catalogue offers.',
    'built': 'BUILT. web/build_3d.py reads this registry and stands '
             'its props: placeRoomProps() lays them against the '
             'partitions buildHall() has just cut, pooled into one '
             'mesh per material for the whole hall and one '
             'InstancedMesh per safety fixture, and '
             'window.__tc3dProps() reports what was drawn beside '
             'what the count rule here wanted. The count rule knows '
             'nothing of doorways or of the tool crib, so a room '
             'stands fewer than it predicts; the probe names each '
             'prop that found no wall and why.',
    'district_catalogue_is_not_drawn': 'The 192 district pieces are NOT '
        'standing in any hall. placeRoomProps() chooses a room\'s furniture '
        'from D.props.by_strand[r.strand] and from that room\'s own PPE list, '
        'and neither of those has a hall in it — the eleven rooms are the '
        'same eleven rooms in all 111 halls. Putting a glazier\'s suction-cup '
        'rack in the strand table would stand it in every ironworkers\' hall '
        'too, so it is not there. What is published instead is the fit-out '
        'computed per district and per room, its geometry, and its cost '
        'priced against the same ceiling as the drawn set. It waits on one '
        'change this pack does not own: a hall dimension on the furniture '
        'lookup in web/build_3d.py.',
    'unreviewed': 'The vocabulary is AUTHORED — a judgement about what a '
                  'trade-training room contains — and no journey-level '
                  'practitioner has reviewed it. The sentence each district '
                  'piece gives for itself is DERIVED from the crib\'s own use '
                  'line for the tool it names, which makes it accurate about '
                  'the tool and no more authoritative about the furniture.',
}

PAGE_CONTRACT = {
    'symbol': 'The page builds these with placeRoomProps(), called per '
              'room inside buildHall(), into one hall-wide pool flushed '
              'once by flushProps(). There is no ROOM_PROPS table: this '
              'pack reserved that name while the work was unbuilt, and the '
              'work was then done another way. The page does still have a '
              '`PROPS` const and it is the OUTDOOR yard dressing in front '
              'of a hall, which is a different thing and is left alone.',
    'where': 'Inside buildHall(), in the existing `for (const r of h.rooms)` '
             'loop, after the partitions are merged and before the room '
             'label is added. The rectangle a prop is placed against is the '
             'one already computed as rx, rz, rw, rd in that loop.',
    'pooling': 'Props accumulate into ONE Map for the whole hall, declared '
               'beside the existing wallPool pattern but hoisted out of the '
               'room loop, and flushed once after the loop through the '
               'page\'s own flushParts(pool, hallGroup). Pooling per room '
               'instead of per hall would multiply the draw calls in this '
               'budget by eleven.',
    'instancing': 'The safety-fixture family draws through the same '
                  'InstancedMesh shape the page already uses in '
                  'flushBeacons(): one instanced draw per prop type per hall, '
                  'however many rooms hold it.',
    'geometry': 'Boxes come from the page\'s own boxGeo(w, h, d) and are '
                'translated into hall space before being pushed to the pool, '
                'exactly as the partition slab() helper already does. '
                'Cylinders are THREE.CylinderGeometry with the radial segment '
                'count stated in each recipe. No loader is involved.',
    'materials': 'A piece names one of seven keys of the page\'s existing '
                 '`mat` table and nothing else. This build fails on an '
                 'eighth, because a material is one more merged mesh in every '
                 'hall and the draw call is the currency this view is short '
                 'of.',
    'solidity': 'Every floor-standing prop registers with the page\'s own '
                'wallRect(x, z, hw, hd) so the walker cannot pass through it, '
                'the same call the fixture benches already make. Wall-mounted '
                'props do not: they hang above nothing a walker occupies.',
    'clearance': 'clearance_m is derived from the page\'s own BODY_R and is '
                 'the floor a walker needs beside a prop. The page\'s existing '
                 'reachability probe is what proves it after the wiring '
                 'lands; this registry only guarantees the arithmetic fits.',
    'read_not_copied': 'The room label, its purpose and its w x h come from '
                       'h.rooms, which the page already inflates from '
                       'ROOM_DEFS and LAYOUTS. A prop carries no label() of '
                       'its own naming the room, because the room already has '
                       'one hanging at its centre. The hazard trigger is the '
                       'room\'s own condOf(hallSlug, strand).ppe — the same '
                       'record the door placard is already drawn from — and '
                       'never a second copy of it.',
    'quality_ladder': 'Props belong to the hall group and are freed by the '
                      'existing disposeOf() traverse, which is why none of '
                      'their materials may be marked userData.shared.',
    'what_the_district_catalogue_needs': 'One lookup. placeRoomProps() '
        'already receives the hall `h`, so the furniture line would read from '
        'a by_district table keyed on h.district beside the by_strand table '
        'it reads now, inserted into `want` between the conditions fixtures '
        'and the shop furniture. Nothing else changes: same pool, same seven '
        'materials, same flush, and the cost is published under '
        'budget.district_plan.',
}

_payload = json.dumps([ALL_FURNITURE, BY_STRAND, BY_DISTRICT, HONESTY,
                       PAGE_CONTRACT, FAMILIES])
assert 'http://' not in _payload and 'https://' not in _payload, \
    'this pack reaches no network and links nowhere'
assert 'AI-SYNTHESIZED' not in _payload, \
    'AI-SYNTHESIZED is orbis\'s word and describes nothing in this pack'

# ---------------------------------------------------------------------------
stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
_all_tris = [p['recipe']['tris'] for p in PROPS]
_cat_tris = [p['recipe']['tris'] for p in ALL_FURNITURE]
_trigger_rooms = {p['id']: sum(1 for got in PLACED.values()
                               if p['id'] in got['hazard'])
                  for p in HAZARD_PROPS}
_forms_used = {}
for p in ALL_FURNITURE:
    _forms_used[p['recipe']['formula']] = 1
_sil = len({(p['recipe']['formula'], tuple(p['size_m']))
            for p in ALL_FURNITURE})
plan_props = [c['props'] for c in PLAN_COSTS.values()]
plan_tris = [c['tris'] for c in PLAN_COSTS.values()]

doc = {
    'pack': 'smartcitix-trade-craft-academy-props',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'honesty': HONESTY,
    'counts': {
        'furniture': len(ALL_FURNITURE),
        'props': len(PROPS),
        'crib_furniture': len(CRIB_PROPS),
        'families': len(FAMILIES),
        'forms': len(FORMS),
        'distinct_silhouettes': _sil,
        'strand_props': len(STRAND_PROPS),
        'hazard_props': len(HAZARD_PROPS),
        'placements': len(MATCHES),
        'strands': len(STRANDS),
        'strands_covered': sum(1 for s in STRANDS if BY_STRAND[s]),
        'anchors': len(ANCHORS),
        'merge_modes': len(MERGES),
        'pooled': sum(1 for p in PROPS if p['merges'] == 'pooled'),
        'instanced': sum(1 for p in PROPS if p['merges'] == 'instanced'),
        'own_mesh': sum(1 for p in PROPS if p['merges'] == 'own-mesh'),
        'materials_used': len({p['material'] for p in PROPS}),
        'materials_allowed': len(MATERIALS),
        'materials_in_catalogue': len({p['material'] for p in ALL_FURNITURE}),
        'box_parts': sum(p['recipe']['box_count'] for p in PROPS),
        'cylinder_parts': sum(p['recipe']['cylinder_count'] for p in PROPS),
        'vocabulary_tris': sum(_all_tris),
        'catalogue_tris': sum(_cat_tris),
        'tris_min': min(_all_tris),
        'tris_median': int(statistics.median(_all_tris)),
        'tris_max': max(_all_tris),
        'catalogue_tris_median': int(statistics.median(_cat_tris)),
        'districts': len(DISTRICTS),
        'crib_tools': len(CRIB_TOOL),
        'crib_tools_referenced': len(TOOLS_COVERED),
        'furniture_with_crib_link': len(LINKED),
        'halls': len(HALLS),
        'rooms': len(BUILT_ROOMS),
        'rooms_requiring_ppe': _ppe_rooms,
        'ppe_vocabulary': len(PPE_VOCAB),
        'hazard_vocabulary': len(HAZARD_VOCAB),
        'prop_instances': sum(props_per),
    },
    'families': FAMILIES,
    'anchors': ANCHORS,
    'merge_modes': MERGES,
    'materials': {
        'allowed': list(MATERIALS),
        'source': 'web/build_3d.py const mat',
        'why': MATERIALS_WHY,
        'used_by_props': sorted({p['material'] for p in PROPS}),
        'used_by_catalogue': sorted({p['material'] for p in ALL_FURNITURE}),
        'new_materials': 0,
        'new_draw_calls': 0,
    },
    'forms': {
        'source': 'props/build.py',
        'count': len(FORMS),
        'used': len(FORM_USED),
        'why': 'three hundred hand-placed part lists would be three hundred '
               'chances to put a shelf through a leg. Every piece is cut from '
               'one of these forms at its own dimensions and its own part '
               'counts, and the form it was cut from is published with it.',
        'names': sorted(FORMS),
        'wall_forms': sorted(WALL_FORMS),
    },
    'measured': {
        'reference_median_tris': [46, 104],
        'reference_texture': '128x128',
        'what_was_taken': 'the finding that a place reads as real from many '
                          'small distinct pieces rather than from dense ones',
        'what_was_not_taken': 'no geometry, no texture, no material, no name '
                              'and no shape; two of the reference files are '
                              'somebody else\'s copyrighted assets and nothing '
                              'from any of them is vendored here',
        'page_constants_read': {
            'body_radius_m': BODY_R, 'eye_height_m': EYE_H,
            'grid_unit_m': U_M, 'floor_top_m': round(FLOOR_TOP, 3),
            'floor_inset_m': FLOOR_INSET,
            'partition_top_m': round(PART_TOP, 3),
            'room_label_m': LABEL_Y,
            'hang_height_m': round(HANG_Y, 3),
            'bench_setback_m': BENCH_SETBACK, 'bench_half_depth_m': BENCH_HD,
            'source': 'web/build_3d.py',
        },
    },
    'props': PROPS,
    'crib_furniture': {
        'source': 'tools/registry/toolcribs.json cribs[*].tools',
        'drawn': False,
        'why_not_drawn': HONESTY['district_catalogue_is_not_drawn'],
        'rule': 'one piece for the work the tool is done at and one for where '
                'the tool lives, for every tool in every district crib. A '
                'piece\'s district is the district of the crib that carries '
                'its tool and is never typed on the piece.',
        'count': len(CRIB_PROPS),
        'tools': len(CRIB_TOOL),
        'pieces_per_tool': len(CRIB_PROPS) // len(CRIB_TOOL),
        'districts': {d: {'crib': CRIBS['cribs'][d]['name'],
                          'halls': sum(1 for v in HALL_DISTRICT.values()
                                       if v == d),
                          'pieces': sum(1 for p in CRIB_PROPS
                                        if p['district'] == d),
                          'by_strand': {s: [m['prop'] for m in
                                            BY_DISTRICT[d][s]]
                                        for s in STRANDS}}
                      for d in DISTRICTS},
        'pieces': CRIB_PROPS,
    },
    'by_strand': {s: {'label': ROOM_OF[s]['label'],
                      'source': 'web/interiors.py ROOMS',
                      'props': BY_STRAND[s]} for s in STRANDS},
    'hazard_props': {
        'source': 'surfaces/registry/finishes.json halls[*].conditions',
        'rule': 'a hazard prop stands in a room when THAT ROOM\'S own '
                'conditions record names protective equipment the prop is '
                'keyed to, and the same registry\'s hazard table says which '
                'kind of work adds that equipment. No hazard prop is placed '
                'by hand anywhere.',
        'ppe_vocabulary': sorted(PPE_VOCAB),
        'hazard_vocabulary': sorted(HAZARD_VOCAB),
        'rooms_requiring_ppe': _ppe_rooms,
        'props': {p['id']: {'ppe_any': p['derive']['ppe_any'],
                            'rule': p['derive']['rule'],
                            'triggered_by_hazards':
                                p['derive']['triggered_by_hazards'],
                            'rooms': _trigger_rooms[p['id']]}
                  for p in HAZARD_PROPS},
    },
    'fit_out': {
        'how': 'the room\'s two partitions are filled from the doorway end in '
               'the order the page fills them — the room\'s own conditions '
               'fixtures first, then its shop furniture — with the run SHARED '
               'between pieces, one interval list per partition and one back '
               'corner per side.',
        'why': 'counted independently a piece always fits, because nothing '
               'else is standing there. Counted together they run out of '
               'wall, and the wall is what the hall actually costs.',
        'is_an_upper_bound': 'the page cuts doorways out of these runs and '
                             'reserves the tools room\'s right partition for '
                             'the district crib it already draws, so it '
                             'stands fewer than this. window.__tc3dProps() '
                             'reports the difference per prop.',
        'offered_pieces_per_hall_median': int(statistics.median(offer_per)),
        'stood_instances_per_hall_median': int(statistics.median(props_per)),
        'stood_instances_per_room_median': int(statistics.median(
            [n for c in COSTS.values() for n in c['per_room'].values()])),
        'offered_pieces_per_room_median': int(statistics.median(
            [len(want_for(slug, r['strand'], False))
             for slug in COSTS for r in PLANS[slug]['rooms']])),
    },
    'budget': {
        'ceiling_source': {
            'file': 'web/eval_scene.mjs',
            'view': 'hall',
            'measured_calls': BASE_CALLS,
            'measured_tris': BASE_TRIS,
            'measured_meshes': BASE_MESHES,
            'call_headroom_x': CALL_HEADROOM,
            'tri_headroom_x': TRI_HEADROOM,
            'mesh_floor_x': MESH_FLOOR,
            'max_calls': HALL_MAX_CALLS,
            'max_tris': HALL_MAX_TRIS,
            'min_meshes': HALL_MIN_MESHES,
            'headroom_calls': CALL_HEADROOM_LEFT,
            'headroom_tris': TRI_HEADROOM_LEFT,
            'why': 'it is the only file in this repo that states what a '
                   'rendered hall costs and what it may cost, and it states '
                   'both with a reason; the multipliers are read from it too, '
                   'so its policy moving moves this ceiling with it',
        },
        'self_imposed': {
            'calls_per_hall': CALL_CEIL,
            'calls_rationale': f'the {CALL_HEADROOM_LEFT} draw calls the eval '
                               f'leaves unspent on this view, less the tenth '
                               f'of them the margin below keeps free. The '
                               f'eval names a second pack for this headroom '
                               f'and this pack used to leave it half; the '
                               f'kit\'s own registry budgets against the '
                               f'campus view instead, which is checked here '
                               f'against the eval\'s campus baseline rather '
                               f'than taken on trust',
            'tris_per_hall': TRI_HALL_CEIL,
            'tris_rationale': f'the {TRI_HEADROOM_LEFT:,} triangles the eval '
                              f'leaves unspent on this view, on the same '
                              f'reasoning and the same tenth kept free',
            'kit_budgets': KIT_BUDGETS,
            'margin': MARGIN,
        },
        'baseline': MEASURED_BASELINE,
        'per_hall': {
            'props_min': min(props_per),
            'props_median': int(statistics.median(props_per)),
            'props_max': max(props_per),
            'tris_min': min(tris_per),
            'tris_median': int(statistics.median(tris_per)),
            'tris_max': max(tris_per),
            'calls_min': min(calls_per), 'calls_max': max(calls_per),
            'calls_are': 'one per pooled material for the whole hall plus one '
                         'per instanced prop type; never one per prop',
        },
        'delta': {
            'draw_calls': max(calls_per),
            'draw_calls_after': MEASURED_BASELINE['draw_calls'] + max(calls_per),
            'draw_calls_headroom': HALL_MAX_CALLS - (
                MEASURED_BASELINE['draw_calls'] + max(calls_per)),
            'triangles': max(tris_per),
            'triangles_after': MEASURED_BASELINE['triangles'] + max(tris_per),
            'triangles_headroom': HALL_MAX_TRIS - (
                MEASURED_BASELINE['triangles'] + max(tris_per)),
            'props_per_draw_call': round(max(props_per) / max(calls_per), 1),
            'reading': f'the worst hall stands {max(props_per)} props in '
                       f'eleven rooms and pays {max(calls_per)} draw calls for '
                       f'all of them — '
                       f'{max(calls_per) / BASE_CALLS * 100:.0f}% on top of '
                       f'what the hall already draws, for '
                       f'{max(tris_per) / BASE_TRIS * 100:.0f}% more triangles',
        },
        'district_plan': {
            'what': 'what a hall would cost if the district catalogue were '
                    'drawn too — the same rooms, the same walls, the same '
                    'pool, with each hall offered its own district\'s pieces '
                    'between its conditions fixtures and its shop furniture.',
            'props_max': max(plan_props),
            'props_median': int(statistics.median(plan_props)),
            'tris_max': max(plan_tris),
            'tris_median': int(statistics.median(plan_tris)),
            'calls_max': PLAN_CALLS,
            'new_draw_calls_over_drawn': PLAN_CALLS - max(calls_per),
            'new_materials_over_drawn': 0,
            'triangles_after': MEASURED_BASELINE['triangles'] + max(plan_tris),
            'draw_calls_after': MEASURED_BASELINE['draw_calls'] + PLAN_CALLS,
            'reading': f'the whole catalogue in every hall costs '
                       f'{PLAN_CALLS - max(calls_per)} more draw calls than '
                       f'the drawn set, because the pieces share its seven '
                       f'materials and a room\'s walls hold what they hold',
        },
        'bundle': {
            'halls': len(HALLS), 'rooms': len(BUILT_ROOMS),
            'prop_instances': sum(props_per), 'triangles': sum(tris_per),
        },
    },
    'page_contract': PAGE_CONTRACT,
}

assert doc['counts']['props'] == (doc['counts']['strand_props']
                                  + doc['counts']['hazard_props'])
assert doc['counts']['furniture'] == (doc['counts']['props']
                                      + doc['counts']['crib_furniture'])
assert doc['counts']['strands_covered'] == doc['counts']['strands'] == 11
assert doc['counts']['placements'] == sum(len(v) for v in BY_STRAND.values())
assert doc['counts']['pooled'] + doc['counts']['instanced'] \
    + doc['counts']['own_mesh'] == doc['counts']['props']
assert doc['counts']['prop_instances'] == sum(props_per)
assert doc['counts']['crib_tools_referenced'] == doc['counts']['crib_tools']

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'props.json').write_text(json.dumps(doc, indent=1) + '\n')
c = doc['counts']
b = doc['budget']
print(f"props: {c['furniture']} pieces of furniture — {c['props']} the page "
      f"stands ({c['strand_props']} from room purposes, {c['hazard_props']} "
      f"from room conditions) and {c['crib_furniture']} district pieces "
      f"cross-linked to {c['crib_tools_referenced']}/{c['crib_tools']} real "
      f"crib tools, in {c['families']} families cut from {c['forms']} forms; "
      f"{c['tris_min']}-{c['tris_max']} tri each (median {c['tris_median']}, "
      f"measured band 46-104); {c['prop_instances']:,} instances standing in "
      f"{c['rooms']:,} rooms of {c['halls']} halls; a room is offered "
      f"{doc['fit_out']['offered_pieces_per_room_median']} pieces and its "
      f"walls hold {doc['fit_out']['stood_instances_per_room_median']}, for "
      f"{b['per_hall']['calls_min']}-{b['per_hall']['calls_max']} draw calls "
      f"and {b['per_hall']['tris_median']:,} triangles against a self-imposed "
      f"{CALL_CEIL}-call ceiling read from web/eval_scene.mjs "
      f"(source stamp {stamp})")
