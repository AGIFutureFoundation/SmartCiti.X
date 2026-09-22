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

AND WHAT THE SCENE SAID. A hall interior as it stands costs 157 draw calls
and 3,806 triangles per frame; the repo's own opt-in browser eval
(web/eval_scene.mjs) holds the hall view to 700 calls and 2,400,000
triangles. So this scene is DRAW-CALL BOUND with an enormous unused
triangle budget, and the design follows: props are 40-250 triangles each
because that is the size at which a piece reads as a thing, and they POOL
into a handful of merged meshes for the whole hall because that is the
currency that is actually scarce. One draw call per prop across eleven
rooms is the anti-pattern, and the budget block below refuses it.

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
PAGE_SYMBOL = 'ROOM_PROPS'
assert PAGE_SYMBOL not in PAGE, \
    f'{PAGE_SYMBOL} is already taken in the page; pick a free identifier'
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
# piece still reads as a thing, not a ceiling to undercut, because the scene
# has 2,396,194 unused triangles and 543 unused draw calls. 250 is this
# pack's own upper bound: past it a prop is a model, and a model wants an
# artist rather than a recipe.
TRI_FLOOR, TRI_CEIL = 40, 250
TRI_WHY = ('40-250 tri. The two reference interiors that read as places have '
           'a median mesh of 46 and 104 triangles, so 46-104 is the size at '
           'which a piece reads as a thing; this prop is built to sit in or '
           'above that band rather than under it, because the hall spends '
           '3,806 of 2,400,000 permitted triangles and triangles are the '
           'currency that is not scarce here.')

FAMILIES = {
    'bench':          'a horizontal surface work happens on top of',
    'storage':        'something that holds what a room keeps between sessions',
    'board':          'a vertical surface a room reads from',
    'seat':           'something a person is off their feet on',
    'vessel':         'an open container things go into and come out of',
    'stand':          'a freestanding upright a piece of apparatus lives on',
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


def prop(pid, name, family, tokens, hazard_trigger, size_m, parts, material,
         merges, merges_why, anchor, walls, base_y, max_per_room, approach,
         why):
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
    return {
        'id': pid, 'name': name, 'family': family,
        'why': why,
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


F = FLOOR_TOP    # everything that stands on the floor starts here

# ---------------------------------------------------------------------------
# THE VOCABULARY. Each prop names the words it answers to; those words are
# matched against the room strand's OWN purpose string, which lives in
# web/interiors.py and is never retyped here. A token that matches nothing
# is a defect and the build says so.
# ---------------------------------------------------------------------------
PROPS = [
    # ---- safety : "Gowning, atmospheric checks, permit board" -------------
    prop('gowning-bench', 'Gowning bench', 'seat', ['gowning'], None,
         [1.6, 0.95, 0.55],
         [B('seat', [1.6, .08, .45], [0, F + .45, 0]),
          B('leg', [.08, .45, .45], [.72, F + .22, 0], 2),
          B('back rail', [1.6, .10, .06], [0, F + .90, -.2]),
          B('back post', [.06, .50, .06], [.72, F + .70, -.2], 2),
          B('boot shelf', [1.5, .05, .40], [0, F + .14, 0])],
         'wood', 'pooled',
         'seven boxes of one material in eleven halls; nothing about it is '
         'read by a raycast and nothing about it moves',
         'side-wall', ['left'], F, 2, False,
         'you change at it before you cross the stripe the page already '
         'paints across a safety room doorway'),

    prop('permit-board', 'Permit board', 'board', ['permit'], None,
         [1.14, 0.80, 0.06],
         [B('panel', [1.10, .70, .04], [0, 0, 0]),
          B('frame rail', [1.14, .05, .06], [0, .375, 0], 2),
          B('stile', [.05, .70, .06], [.545, 0, 0], 2),
          B('permit card', [.30, .22, .01], [-.35, .10, .03], 3)],
         'paint', 'pooled',
         'a flat panel is four square metres of nothing; pooling it with the '
         'other painted props costs no extra draw at all',
         'wall-mounted', ['left'], 0.93, 1, True,
         'the board the safety room is named after, and the one the records '
         'room files afterwards'),

    prop('atmosphere-post', 'Atmospheric check post', 'stand',
         ['atmospheric'], None, [0.32, 1.36, 0.32],
         [C('column', .05, 1.00, 8, [0, F + .50, 0]),
          C('foot', .16, .06, 10, [0, F + .03, 0]),
          B('head', [.22, .30, .14], [0, F + 1.15, 0]),
          B('readout', [.16, .10, .02], [0, F + 1.18, .08])],
         'metal', 'pooled',
         'one of these per safety room, 111 in the bundle, and none of them '
         'is interactive; merged it is a share of one mesh',
         'side-wall', ['right'], F, 1, False,
         'the room says atmospheric checks happen here, so the thing they '
         'are made on stands in it'),

    # ---- procedure : "The floor the trade is actually learned on" ---------
    prop('work-trestle', 'Work trestle', 'stand', ['floor'], None,
         [1.8, 0.90, 0.5],
         [B('top rail', [1.80, .12, .18], [0, F + .84, 0]),
          B('leg', [.09, .78, .09], [.78, F + .39, .18], 4),
          B('brace', [1.50, .06, .06], [0, F + .30, .18], 2)],
         'wood', 'pooled',
         'the practice bay gets several and every hall has one bay; seven '
         'boxes each merged into the hall-wide wood mesh',
         'side-wall', ['left', 'right'], F, 3, True,
         'the bay is the floor a trade is learned on, and a trestle is what '
         'the work is held at height on while it is'),

    prop('learner-stool', 'Learner stool', 'seat', ['learned'], None,
         [0.44, 0.62, 0.44],
         [C('seat pad', .17, .07, 10, [0, F + .58, 0]),
          C('column', .045, .50, 8, [0, F + .28, 0], capped=False),
          C('base', .22, .05, 10, [0, F + .03, 0])],
         'metal', 'pooled',
         'round things in the reference blocks are the cheapest pieces on the '
         'sheet; three cylinders pooled is a fraction of one draw',
         'side-wall', ['right'], F, 2, False,
         'nobody stands for six hours; a bay with no seat in it is a '
         'rendering of a bay'),

    # ---- machines : "Plant checked out to a training area" ----------------
    prop('checkout-board', 'Plant checkout board', 'board', ['checked out'],
         None, [1.34, 0.90, 0.06],
         [B('panel', [1.30, .80, .04], [0, 0, 0]),
          B('frame rail', [1.34, .05, .06], [0, .425, 0], 2),
          B('tag hook', [.03, .06, .03], [-.5, .25, .03], 6)],
         'paint', 'pooled',
         'one per equipment bay, flat, static and never raycast',
         'wall-mounted', ['left'], 0.93, 1, True,
         'plant is CHECKED OUT to this room, and a checkout that is not '
         'written down anywhere did not happen'),

    prop('bay-guard-rail', 'Bay guard rail', 'stand', ['training area'], None,
         [2.0, 1.06, 0.2],
         [C('post', .06, 1.00, 8, [.95, F + .50, 0], count=2),
          B('rail', [2.00, .08, .06], [0, F + .95, 0], 2),
          B('base plate', [.20, .03, .20], [.95, F + .015, 0], 2)],
         'post', 'pooled',
         'the page already keeps one high-visibility material; every rail in '
         'the bundle merges into that one mesh per hall',
         'side-wall', ['right'], F, 2, False,
         'a training AREA is an area because something marks where it stops'),

    # ---- tools : "Issue, calibration and return" --------------------------
    prop('issue-counter', 'Issue counter', 'bench', ['issue'], None,
         [1.8, 0.86, 0.6],
         [B('top', [1.80, .07, .60], [0, F + .82, 0]),
          B('front panel', [1.80, .75, .05], [0, F + .42, -.27]),
          B('end panel', [.05, .75, .60], [.87, F + .42, 0], 2),
          B('under shelf', [1.70, .04, .50], [0, F + .30, .02]),
          B('kick', [1.70, .10, .05], [0, F + .05, -.27])],
         'wood', 'pooled',
         'six boxes, one material, one per tool crib; it is furniture, not '
         'an object the page listens to',
         'side-wall', ['left'], F, 1, True,
         'the crib the page already builds hands tools ACROSS something, and '
         'until now it handed them across nothing'),

    prop('calibration-cabinet', 'Calibration cabinet', 'storage',
         ['calibration'], None, [0.94, 1.36, 0.54],
         [B('carcass', [.90, 1.30, .50], [0, F + .65, 0]),
          B('door', [.43, 1.20, .03], [.22, F + .68, .265], 2),
          B('plinth', [.90, .10, .48], [0, F + .05, 0]),
          B('top cap', [.94, .04, .54], [0, F + 1.32, 0]),
          B('handle', [.03, .20, .03], [.02, F + .70, .29], 2)],
         'steel', 'pooled',
         'static, closed, and the same seven boxes in every hall',
         'side-wall', ['right'], F, 1, True,
         'calibration is the middle word of this room\'s purpose and it is '
         'the one that needs a locked box'),

    prop('return-bin', 'Return bin', 'vessel', ['return'], None,
         [0.6, 0.78, 0.6],
         [C('body', .28, .70, 12, [0, F + .38, 0], capped=False),
          C('rim', .30, .05, 12, [0, F + .74, 0]),
          B('base tray', [.50, .05, .50], [0, F + .025, 0])],
         'part', 'pooled',
         'an open cylinder is 24 triangles; there is no argument for giving '
         'it a draw call of its own',
         'back-corner', ['right'], F, 1, True,
         'things come BACK to a crib, and a crib with nowhere to put them '
         'back is a counter with a queue'),

    # ---- materials : "Stock, offcuts and consumables" ---------------------
    prop('stock-rack', 'Stock rack', 'storage', ['stock'], None,
         [1.8, 1.70, 0.7],
         [B('upright', [.09, 1.70, .09], [.855, F + .85, 0], 2),
          B('shelf', [1.80, .06, .60], [0, F + .55, 0], 3),
          B('brace', [1.80, .05, .05], [0, F + 1.60, -.28], 2),
          B('foot', [1.80, .06, .70], [0, F + .03, 0])],
         'metal', 'pooled',
         'eight boxes, one material; a store gets two or three of them and '
         'they all land in the same merged mesh',
         'side-wall', ['left', 'right'], F, 2, True,
         'STOCK is the first word of this room\'s purpose and stock is kept '
         'on something'),

    prop('offcut-bin', 'Offcut bin', 'vessel', ['offcuts'], None,
         [0.9, 0.66, 0.6],
         [B('side', [.90, .60, .03], [0, F + .32, .285], 2),
          B('end', [.03, .60, .60], [.435, F + .32, 0], 2),
          B('base', [.90, .04, .60], [0, F + .04, 0]),
          B('lip rail', [.90, .04, .04], [0, F + .64, .285], 2)],
         'wood', 'pooled',
         'seven boxes and nothing that reacts to anything',
         'back-corner', ['left'], F, 1, True,
         'OFFCUTS is the second word, and the difference between a trade '
         'shop and a warehouse is that the offcuts are kept'),

    prop('consumables-shelf', 'Consumables shelf', 'storage', ['consumables'],
         None, [1.2, 0.90, 0.3],
         [B('back panel', [1.20, .90, .03], [0, 0, 0]),
          B('shelf', [1.20, .04, .28], [0, -.25, .14], 3),
          B('end', [.03, .90, .30], [.585, 0, .14], 2)],
         'wood', 'pooled',
         'a wall shelf with no moving part and nothing to click',
         'wall-mounted', ['right'], 0.93, 2, True,
         'CONSUMABLES is the third word; they are small, they go at hand '
         'height, and they do not belong on the stock rack'),

    # ---- layout : "Setting out, control points, marking" ------------------
    prop('layout-table', 'Layout table', 'bench', ['setting', 'marking'], None,
         [2.0, 0.80, 0.9],
         [B('top', [2.00, .06, .90], [0, F + .77, 0]),
          B('leg', [.08, .72, .08], [.92, F + .36, .38], 4),
          B('rail', [1.80, .06, .06], [0, F + .20, .38], 2),
          B('marking strip', [2.00, .01, .05], [0, F + .805, .40])],
         'steel', 'pooled',
         'eight boxes; the marking strip is a triangle cost of twelve and a '
         'draw cost of zero',
         'side-wall', ['left', 'right'], F, 2, True,
         'setting out and marking are done flat, at waist height, on '
         'something that does not move'),

    prop('control-pillar', 'Control point pillar', 'stand', ['control point'],
         None, [0.4, 1.28, 0.4],
         [C('shaft', .08, 1.10, 10, [0, F + .55, 0]),
          C('cap', .09, .04, 10, [0, F + 1.12, 0]),
          B('base plate', [.40, .08, .40], [0, F + .04, 0]),
          B('target plate', [.18, .18, .02], [0, F + .95, .09])],
         'metal', 'pooled',
         'one or two per layout floor and completely static',
         'back-corner', ['left', 'right'], F, 1, False,
         'a CONTROL POINT is a thing you can put an instrument over twice '
         'and get the same answer; a painted cross is not one'),

    # ---- inspection : "Acceptance criteria and sign-off" ------------------
    prop('gauge-stand', 'Acceptance gauge stand', 'stand',
         ['acceptance', 'criteria'], None, [0.4, 1.28, 0.4],
         [C('column', .06, .90, 8, [0, F + .45, 0]),
          C('dial', .07, .03, 10, [0, F + 1.05, .18]),
          B('base', [.35, .06, .35], [0, F + .03, 0]),
          B('head', [.30, .25, .20], [0, F + 1.02, 0]),
          B('arm', [.40, .05, .05], [.15, F + 1.02, .10])],
         'metal', 'pooled',
         'static apparatus; the inspection bench of every hall gets one and '
         'they merge into a single metal mesh with everything else',
         'side-wall', ['right'], F, 1, True,
         'ACCEPTANCE CRITERIA is a number somebody reads off something'),

    prop('signoff-desk', 'Sign-off desk', 'bench', ['sign-off'], None,
         [1.4, 0.80, 0.7],
         [B('top', [1.40, .06, .70], [0, F + .77, 0]),
          B('leg', [.07, .72, .07], [.63, F + .36, .28], 4),
          B('modesty panel', [1.30, .40, .03], [0, F + .52, -.32]),
          B('paper tray', [.50, .03, .35], [-.35, F + .81, 0]),
          B('stamp block', [.12, .10, .12], [.45, F + .85, 0])],
         'wood', 'pooled',
         'eight boxes of the same wood the benches use',
         'side-wall', ['left'], F, 1, True,
         'SIGN-OFF is a person writing on paper at a desk, and the second '
         'half of what this room is for'),

    # ---- troubleshooting : "Fault-finding against live rigs" -------------
    prop('rig-frame', 'Live rig frame', 'stand', ['rigs'], None,
         [1.5, 1.66, 0.25],
         [B('upright', [.08, 1.60, .08], [.71, F + .80, 0], 2),
          B('crossbar', [1.40, .08, .08], [0, F + 1.56, 0], 2),
          B('back panel', [1.30, 1.00, .03], [0, F + .95, -.06]),
          B('mount block', [.15, .15, .08], [-.45, F + 1.10, .05], 4)],
         'metal', 'pooled',
         'nine boxes, vertical, static; the rig is scenery the learner works '
         'in front of rather than an object the page tracks',
         'side-wall', ['left', 'right'], F, 2, True,
         'a LIVE RIG is a frame with something wired to it that can be made '
         'to fail on purpose'),

    prop('test-bench', 'Fault-finding bench', 'bench', ['fault-finding'], None,
         [1.5, 1.10, 0.7],
         [B('top', [1.50, .07, .70], [0, F + .82, 0]),
          B('leg', [.08, .75, .08], [.68, F + .38, .28], 4),
          B('under shelf', [1.40, .05, .60], [0, F + .25, 0]),
          B('instrument case', [.45, .25, .30], [-.45, F + .98, -.15]),
          B('dial', [.08, .08, .02], [-.45, F + .98, .01], 2)],
         'steel', 'pooled',
         'nine boxes of a material the page already builds for its own '
         'benches',
         'side-wall', ['right'], F, 1, True,
         'FAULT-FINDING happens with instruments on a surface, facing the rig'),

    # ---- coordination : "Shift start, hand-offs, cross-trade" -------------
    prop('shift-board', 'Shift board', 'board', ['shift'], None,
         [1.64, 0.95, 0.08],
         [B('panel', [1.60, .90, .04], [0, 0, 0]),
          B('frame rail', [1.64, .05, .06], [0, .475, 0], 2),
          B('column divider', [.02, .85, .01], [-.4, 0, .025], 4),
          B('marker tray', [1.50, .05, .08], [0, -.48, .05])],
         'paint', 'pooled',
         'the largest flat thing in the pack and still eight boxes',
         'wall-mounted', ['left'], 0.93, 1, True,
         'a SHIFT START is people standing in front of a board that says who '
         'is doing what'),

    prop('handoff-table', 'Hand-off table', 'bench', ['hand-offs'], None,
         [1.6, 0.78, 0.8],
         [B('top', [1.60, .06, .80], [0, F + .75, 0]),
          B('leg', [.07, .70, .07], [.73, F + .35, .33], 4),
          B('rail', [1.50, .05, .05], [0, F + .22, .33])],
         'wood', 'pooled',
         'six boxes; the cheapest prop in the pack after the lectern',
         'side-wall', ['left', 'right'], F, 2, True,
         'a HAND-OFF is two crews around one table with the drawing on it'),

    # ---- documentation : "Permits, certificates, as-builts" --------------
    prop('records-cabinet', 'Records cabinet', 'storage',
         ['certificates', 'as-builts'], None, [1.0, 1.39, 0.57],
         [B('carcass', [1.00, 1.35, .55], [0, F + .68, 0]),
          B('drawer front', [.94, .30, .03], [0, F + .30, .29], 4),
          B('pull', [.20, .03, .02], [0, F + .40, .31], 4),
          B('plinth', [1.00, .08, .53], [0, F + .04, 0]),
          B('top cap', [1.00, .04, .57], [0, F + 1.37, 0])],
         'steel', 'pooled',
         'ten boxes, one material, two or three per records room, all in the '
         'hall-wide steel mesh',
         'side-wall', ['left', 'right'], F, 2, True,
         'CERTIFICATES and AS-BUILTS are paper, and paper that matters lives '
         'in a drawer somebody can find'),

    # ---- leadership : "Level tests and the instructor track" -------------
    prop('exam-desk', 'Exam desk', 'bench', ['tests'], None,
         [1.2, 0.76, 0.6],
         [B('top', [1.20, .05, .60], [0, F + .73, 0]),
          B('leg', [.06, .70, .06], [.54, F + .35, .24], 4),
          B('book rail', [1.10, .04, .04], [0, F + .20, .24])],
         'wood', 'pooled',
         'six boxes; the classroom takes four of them and they are still one '
         'share of one mesh',
         'side-wall', ['left', 'right'], F, 3, True,
         'LEVEL TESTS are sat at a desk, and a classroom with no desks is a '
         'corridor'),

    prop('instructor-lectern', 'Instructor lectern', 'stand', ['instructor'],
         None, [0.7, 1.16, 0.5],
         [B('slope top', [.60, .05, .45], [0, F + 1.12, 0]),
          B('body', [.55, 1.05, .40], [0, F + .53, 0]),
          B('base', [.70, .06, .50], [0, F + .03, 0]),
          B('shelf', [.50, .03, .35], [0, F + .70, 0])],
         'wood', 'pooled',
         'four boxes, 48 triangles, two off the reference median — and it '
         'still reads as a lectern because it is the right shape, not '
         'because it is dense',
         'back-corner', ['left'], F, 1, True,
         'the INSTRUCTOR TRACK has an instructor in it and the instructor '
         'stands somewhere'),

    # ---- hazard props. No token, no strand: these are placed by the room's
    # ---- OWN conditions record and by nothing else.
    prop('ppe-station', 'PPE station', 'safety-fixture', None,
         ['*any*'], [1.0, 1.0, 0.24],
         [B('back panel', [1.00, 1.00, .04], [0, 0, 0]),
          B('bin', [.28, .22, .20], [-.34, -.25, .12], 3),
          B('hook rail', [1.00, .05, .06], [0, .38, .05]),
          B('hook', [.03, .10, .03], [-.36, .32, .08], 4)],
         'paint', 'instanced',
         'the same nine boxes stand in eight rooms of every hall — 888 rooms '
         'in the bundle. One InstancedMesh draws all eight copies in a hall '
         'in one call; pooling them would cost the same and instancing says '
         'plainly that they are the same object',
         'wall-mounted', ['right'], 0.93, 1, True,
         'the room record already says what this room requires of you, and '
         'the page already hangs that list on the door as a placard; this is '
         'a schematic rack standing where the placard points — it issues '
         'nothing and holds nothing'),

    prop('eyewash-stand', 'Eyewash stand', 'safety-fixture', None,
         ['chemical gloves', 'apron', 'face shield'], [0.4, 1.24, 0.4],
         [C('column', .05, 1.10, 8, [0, F + .55, 0]),
          C('bowl', .17, .08, 12, [0, F + 1.14, 0]),
          B('base', [.30, .05, .30], [0, F + .025, 0]),
          B('nozzle', [.06, .06, .12], [-.06, F + 1.16, 0], 2),
          B('paddle', [.20, .04, .10], [0, F + 1.00, .14])],
         'post', 'instanced',
         'repeats across every room whose record asks for chemical-contact '
         'protection; identical geometry, so one draw per hall',
         'back-corner', ['right'], F, 1, True,
         'a shape standing where a room record says something can get in '
         'your eyes — NOT a fixture specification and not evidence that '
         'anything has been installed'),

    prop('extinguisher-bracket', 'Extinguisher bracket', 'safety-fixture',
         None, ['flame-resistant clothing', 'anti-static clothing',
                'welding hood'], [0.22, 0.7, 0.2],
         [C('body', .09, .50, 10, [0, .0, 0]),
          C('neck', .03, .10, 8, [0, .30, 0]),
          B('back plate', [.20, .50, .02], [0, 0, -.11]),
          B('bracket', [.14, .20, .10], [0, -.10, -.05]),
          B('handle', [.10, .03, .06], [0, .33, .02])],
         'cone', 'instanced',
         'small, identical and in every hot-work room of every hall',
         'wall-mounted', ['left'], 0.95, 1, False,
         'a shape standing where a room record asks for flame-resistant or '
         'anti-static clothing — schematic, not a rated appliance'),

    prop('spill-kit-cabinet', 'Spill kit cabinet', 'safety-fixture', None,
         ['chemical gloves', 'waterproof boots', 'coveralls'],
         [0.6, 0.88, 0.37],
         [B('carcass', [.60, .80, .35], [0, F + .42, 0]),
          B('door', [.56, .74, .03], [0, F + .44, .19]),
          B('handle', [.03, .12, .03], [.22, F + .44, .21]),
          B('label', [.30, .12, .01], [0, F + .68, .21]),
          B('plinth', [.60, .08, .33], [0, F + .04, 0])],
         'cone', 'instanced',
         'five boxes; it appears wherever a record asks for chemical, wet or '
         'contaminated-work protection, which is many rooms and one draw',
         'back-corner', ['left'], F, 1, True,
         'a shape standing where a room record says something can be spilled '
         '— schematic, and it contains nothing'),

    prop('gas-monitor-dock', 'Gas monitor dock', 'safety-fixture', None,
         ['gas monitor'], [0.35, 0.45, 0.12],
         [B('back plate', [.35, .45, .03], [0, 0, 0]),
          B('cradle', [.12, .14, .10], [-.09, -.05, .06], 2),
          B('unit', [.08, .12, .05], [-.09, .00, .08], 2),
          B('charge strip', [.30, .03, .01], [0, -.20, .03])],
         'metal', 'instanced',
         'the smallest prop in the pack and it repeats; instancing is the '
         'only shape that makes sense for it',
         'wall-mounted', ['right'], 1.00, 1, False,
         'a shape standing where a room record asks the person to carry a '
         'gas monitor — it docks nothing and measures nothing'),
]

BY_ID = {p['id']: p for p in PROPS}
assert len(BY_ID) == len(PROPS), 'two props share an id'
for p in PROPS:
    assert p['family'] in FAMILIES, f'{p["id"]}: {p["family"]} is not a family'
    assert p['material'] in PAGE_MATERIALS, \
        f'{p["id"]}: mat.{p["material"]} is not a material the page already has'
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

# own-mesh is declared and deliberately unused. A prop may only claim it by
# naming the raycast list it joins, and none does, so props add no unpooled
# draw calls at all.
for p in PROPS:
    assert p['merges'] != 'own-mesh' or 'raycast' in p['merges_why'], \
        (f'{p["id"]}: own-mesh needs a raycast or motion reason — an unpooled '
         f'prop is a whole draw call')

# No prop may reuse a room label or a station name as its own name. The room
# table is owned by web/interiors.py and the station names by stations/; a
# third copy under a different key is the defect this bundle lints for.
_labels = {r['label'].lower() for r in ROOM_OF.values()}
_stations = {s['name'].lower() for s in STATIONS['stations']}
for p in PROPS:
    assert p['name'].lower() not in _labels, \
        f'{p["id"]}: "{p["name"]}" is a room label; read it, do not copy it'
    assert p['name'].lower() not in _stations, \
        f'{p["id"]}: "{p["name"]}" is a station name owned by stations/'

# ---------------------------------------------------------------------------
# BY STRAND. A prop stands in a strand because one of its tokens appears in
# that strand's own purpose line. Nothing is assigned.
# ---------------------------------------------------------------------------
STRAND_PROPS = [p for p in PROPS if p['derive']['from'] == 'room.purpose']
HAZARD_PROPS = [p for p in PROPS if p['derive']['from'] != 'room.purpose']
assert STRAND_PROPS and HAZARD_PROPS

BY_STRAND = {s: [] for s in STRANDS}
MATCHES = []
for p in STRAND_PROPS:
    hit = False
    for s in STRANDS:
        text = ROOM_OF[s]['purpose'].lower()
        for tok in p['derive']['tokens']:
            if tok in text:
                BY_STRAND[s].append({'prop': p['id'], 'matched': tok,
                                     'in': 'purpose'})
                MATCHES.append((p['id'], s, tok))
                hit = True
                break
    assert hit, (f'{p["id"]}: none of its tokens {p["derive"]["tokens"]} '
                 f'appears in any room purpose — a prop that stands nowhere')

# every landing is supported by the strand's OWN words, re-checked here
# against the imported table rather than against the loop above
for pid, s, tok in MATCHES:
    assert tok in ROOM_OF[s]['purpose'].lower(), \
        f'{pid} landed in {s}, whose purpose does not contain "{tok}"'
    assert tok in BY_ID[pid]['derive']['tokens'], \
        f'{pid} matched "{tok}", which it never declared'

# every one of the eleven strands gets something
for s in STRANDS:
    assert BY_STRAND[s], \
        (f'{s} ("{ROOM_OF[s]["label"]}") gets no prop: every strand must have '
         f'something standing in it or the room is still an empty box')

# a token that matches nothing is dead vocabulary
for p in STRAND_PROPS:
    for tok in p['derive']['tokens']:
        assert any(tok in ROOM_OF[s]['purpose'].lower() for s in STRANDS), \
            f'{p["id"]}: the token "{tok}" matches no room purpose'

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


# the derivation chain, computed: which declared hazards end up producing
# each prop, through the PPE those hazards add
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

PLACED = {}       # (slug, strand) -> {'strand': [...], 'hazard': [...]}
for slug, rooms in COND.items():
    for strand, c in rooms.items():
        PLACED[(slug, strand)] = {
            'strand': [m['prop'] for m in BY_STRAND[strand]],
            'hazard': hazard_props_for(c['ppe']),
        }

# the build refuses a room that requires PPE and gets no PPE prop
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
    # and no hazard prop lands anywhere its trigger is not in the record
    for pid in got['hazard']:
        want = BY_ID[pid]['derive']['ppe_any']
        assert want == ['*any*'] or set(want) & set(ppe), \
            f'{slug}/{strand}: {pid} stands there on no record at all'
assert _ppe_rooms == sum(1 for c in COND.values() for r in c.values() if r['ppe'])

# ---------------------------------------------------------------------------
# LAYOUT. How many fit, and whether the smallest room that admits a prop can
# actually hold the layout the prop declares.
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


# A prop's own layout, checked against the SMALLEST room in the whole bundle
# that admits it.
for p in PROPS:
    if p['derive']['from'] == 'room.purpose':
        admits = [s for s in STRANDS
                  if any(m['prop'] == p['id'] for m in BY_STRAND[s])]
    else:
        admits = sorted({strand for (slug, strand), got in PLACED.items()
                         if p['id'] in got['hazard']})
    assert admits, f'{p["id"]}: admitted by no strand at all'
    # The worst case on BOTH axes, not the smallest room on one of them: the
    # narrowest room a prop meets and the shallowest room it meets need not
    # be the same room, and the across-room check reads the width while the
    # along-wall check reads the depth. Taking one room's pair let a prop be
    # fitted to a 5x3 bay and then stood in a 6x2 store.
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
    # along the wall: the run it needs must be inside the run it has
    if p['layout']['anchor'] != 'back-corner':
        per_wall = math.ceil(n / len(p['layout']['walls']))
        need = per_wall * p['size_m'][0] + (per_wall - 1) * GAP_M
        have = d_m - FRONT_CLEAR_M - BACK_RESERVE_M
        assert need <= have + 1e-9, \
            (f'{p["id"]}: {per_wall} of them need {need:.2f} m of wall and the '
             f'smallest room has {have:.2f} m')
    # across the room: two walls of props plus their clearance must still
    # leave a body width of floor between them
    depth = p['size_m'][2] + p['clearance_m']
    left = w_m - 2 * depth
    assert left >= 2 * BODY_R, \
        (f'{p["id"]}: leaves {left:.2f} m between opposite walls and a walker '
         f'needs {2 * BODY_R:.2f} m')
    # up the wall: nothing hangs above the partition it hangs on, and
    # nothing standing on the floor rises past the room label
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
# BUDGET. Computed over the 111 real plans, in both currencies.
# ---------------------------------------------------------------------------
def hall_cost(slug):
    plan = PLANS[slug]
    instances = tris = 0
    pooled_mats, instanced_types = set(), set()
    per_room = {}
    for r in plan['rooms']:
        strand = r['strand']
        got = PLACED[(slug, strand)]
        here = 0
        for pid in got['strand'] + got['hazard']:
            p = BY_ID[pid]
            n = count_in(p, r['w'], r['h'])
            if n == 0:
                continue
            instances += n
            here += n
            tris += n * p['recipe']['tris']
            if p['merges'] == 'pooled':
                pooled_mats.add(p['material'])
            elif p['merges'] == 'instanced':
                instanced_types.add(pid)
            else:
                instanced_types.add(pid + '#own')
        per_room[strand] = here
    calls = len(pooled_mats) + len(instanced_types)
    return {'props': instances, 'tris': tris, 'calls': calls,
            'pooled_materials': len(pooled_mats),
            'instanced_types': len(instanced_types),
            'per_room': per_room}


COSTS = {h['slug']: hall_cost(h['slug']) for h in HALLS}
props_per = [c['props'] for c in COSTS.values()]
tris_per = [c['tris'] for c in COSTS.values()]
calls_per = [c['calls'] for c in COSTS.values()]

# every room in the bundle gets something standing in it
for slug, c in COSTS.items():
    for strand, n in c['per_room'].items():
        assert n >= 1, f'{slug}/{strand} is still an empty box'

# THE CEILING, and where it comes from. web/eval_scene.mjs measures what a
# hall costs now and states what it may cost; the difference is the whole
# headroom this bundle has left for everything that is still to be added.
# Its own comment names TWO packs expected to spend it — "the kit and props
# packs" — so this pack takes HALF of each headroom and leaves the other
# half for its sibling. A pack that spends the whole headroom has not
# budgeted, it has just gone first.
CALL_CEIL = CALL_HEADROOM_LEFT // 2
TRI_HALL_CEIL = TRI_HEADROOM_LEFT // 2
assert max(calls_per) <= CALL_CEIL, \
    (f'props add {max(calls_per)} draw calls to a hall. The eval measures '
     f'{BASE_CALLS} and permits {HALL_MAX_CALLS}, so {CALL_HEADROOM_LEFT} are '
     f'left for everything unbuilt and this pack may take {CALL_CEIL} of them')
assert max(tris_per) <= TRI_HALL_CEIL, \
    (f'props add {max(tris_per):,} triangles to a hall. The eval measures '
     f'{BASE_TRIS:,} and permits {HALL_MAX_TRIS:,}, so {TRI_HEADROOM_LEFT:,} '
     f'are left and this pack may take {TRI_HALL_CEIL:,} of them')
# A budget spent to the last triangle is not a budget, it is a coincidence:
# the next prop added here would break the build rather than fit in it. Both
# ceilings keep a tenth of themselves free.
MARGIN = 0.10
for spent, ceil_, what in ((max(tris_per), TRI_HALL_CEIL, 'triangles'),
                           (max(calls_per), CALL_CEIL, 'draw calls')):
    assert spent <= ceil_ * (1 - MARGIN), \
        (f'props spend {spent:,} of {ceil_:,} {what} in the worst hall, which '
         f'leaves {(1 - spent / ceil_) * 100:.1f}% free and the policy is '
         f'{MARGIN * 100:.0f}%')
# and the anti-pattern: one draw call per prop. A hall holds dozens of props
# and must pay for them in a handful of merged draws.
assert max(calls_per) < min(props_per), \
    ('props must cost fewer draw calls than there are props — one draw per '
     'prop across eleven rooms is the shape this check exists to refuse')
# the eval also holds the view to a FLOOR of visible meshes, because a place
# is made of distinct pieces. Props may only add to that count.
_mesh_after = BASE_MESHES + max(c['pooled_materials'] + c['instanced_types']
                                for c in COSTS.values())
assert _mesh_after > BASE_MESHES >= HALL_MIN_MESHES, \
    'props must add visible pieces to the hall, never remove them'

# ---------------------------------------------------------------------------
HONESTY = {
    'status': 'SCHEMATIC: every prop in this pack is a handful of boxes and '
              'cylinders built in the browser from the recipe printed here. '
              'No mesh is loaded, no model is vendored, no texture is '
              'fetched, and nothing is generated at view time.',
    'not_a_specification': 'These are shapes in a training environment. The '
                           'eyewash stand is a cylinder and a bowl standing '
                           'where a room record says corrosives are handled; '
                           'the extinguisher is a cylinder on a plate. They '
                           'are not fixture specifications, not rated '
                           'appliances, not compliance artefacts, and not '
                           'evidence that any equipment has been provided '
                           'anywhere. Nothing in this pack should be read as '
                           'a safety-equipment specification, and a learner '
                           'who has walked past one has not been trained on '
                           'it.',
    'placement_is_derived': 'No prop is placed by hand. A prop stands in a '
                            'strand because a word it declares appears in that '
                            'strand\'s own purpose line in web/interiors.py, '
                            'and a hazard prop stands in a room because that '
                            'room\'s own conditions record in '
                            'surfaces/registry/finishes.json asks for the '
                            'protective equipment it holds. The build fails if '
                            'a room requiring PPE gets no PPE prop.',
    'one_truth': 'No room label, purpose, footprint, illuminance figure, '
                 'hazard or PPE item is typed in this pack. The room table is '
                 'imported from web/interiors.py and the conditions are read '
                 'from surfaces/registry/finishes.json. The page\'s body '
                 'radius, eye height, grid unit, floor height, partition '
                 'height, room-label height and bench setback are parsed out '
                 'of web/build_3d.py, so a prop cannot be sized against a '
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
                           'bound. Every prop here pools or instances; none '
                           'takes a mesh of its own, and the budget block '
                           'refuses a design that would.',
    'not_built_yet': 'This registry is a declaration. web/build_3d.py does '
                     'not read it yet: no prop declared here is standing in '
                     'any room in the shipped page. The page_contract block '
                     'states exactly what wiring is outstanding.',
    'unreviewed': 'The vocabulary is AUTHORED — a judgement about what a '
                  'trade-training room contains — and no journey-level '
                  'practitioner has reviewed it.',
}

PAGE_CONTRACT = {
    'symbol': f'The page builds these under a new `{PAGE_SYMBOL}` table. It '
              f'already has a `PROPS` const and that one is the OUTDOOR yard '
              f'dressing in front of a hall; the two must not collide, and '
              f'this build fails if `{PAGE_SYMBOL}` is ever taken.',
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
    'materials': 'A prop names a key of the page\'s existing `mat` table and '
                 'nothing else. This build fails if a prop names a material '
                 'the page does not already build, because a new material is '
                 'a new draw call.',
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
}

# no URL anywhere in what ships
_payload = json.dumps([PROPS, BY_STRAND, HONESTY, PAGE_CONTRACT, FAMILIES])
assert 'http://' not in _payload and 'https://' not in _payload, \
    'this pack reaches no network and links nowhere'
assert 'AI-SYNTHESIZED' not in _payload, \
    'AI-SYNTHESIZED is orbis\'s word and describes nothing in this pack'

# ---------------------------------------------------------------------------
stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
_all_tris = [p['recipe']['tris'] for p in PROPS]
_trigger_rooms = {p['id']: sum(1 for got in PLACED.values()
                               if p['id'] in got['hazard'])
                  for p in HAZARD_PROPS}

doc = {
    'pack': 'smartcitix-trade-craft-academy-props',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'honesty': HONESTY,
    'counts': {
        'props': len(PROPS),
        'families': len(FAMILIES),
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
        'box_parts': sum(p['recipe']['box_count'] for p in PROPS),
        'cylinder_parts': sum(p['recipe']['cylinder_count'] for p in PROPS),
        'vocabulary_tris': sum(_all_tris),
        'tris_min': min(_all_tris),
        'tris_median': int(statistics.median(_all_tris)),
        'tris_max': max(_all_tris),
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
            'bench_setback_m': BENCH_SETBACK, 'bench_half_depth_m': BENCH_HD,
            'source': 'web/build_3d.py',
        },
    },
    'props': PROPS,
    'by_strand': {s: {'label': ROOM_OF[s]['label'],
                      'source': 'web/interiors.py ROOMS',
                      'props': BY_STRAND[s]} for s in STRANDS},
    'hazard_props': {
        'source': 'surfaces/registry/finishes.json halls[*].conditions',
        'rule': 'a hazard prop stands in a room when THAT ROOM\'S own '
                'conditions record names protective equipment the prop holds. '
                'No hazard prop is placed by hand anywhere.',
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
            'calls_rationale': f'half of the {CALL_HEADROOM_LEFT} draw calls '
                               f'the eval leaves unspent. Its own comment '
                               f'names two packs expected to spend that '
                               f'headroom, so this one takes half and leaves '
                               f'half',
            'tris_per_hall': TRI_HALL_CEIL,
            'tris_rationale': f'half of the {TRI_HEADROOM_LEFT:,} triangles '
                              f'the eval leaves unspent, on the same split',
        },
        'baseline': MEASURED_BASELINE,
        'per_hall': {
            'props_min': min(props_per), 'props_median': int(statistics.median(props_per)),
            'props_max': max(props_per),
            'tris_min': min(tris_per), 'tris_median': int(statistics.median(tris_per)),
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
        'bundle': {
            'halls': len(HALLS), 'rooms': len(BUILT_ROOMS),
            'prop_instances': sum(props_per), 'triangles': sum(tris_per),
        },
    },
    'page_contract': PAGE_CONTRACT,
}

# the counts are computed above and checked here against the things they
# were computed from, so a count and its subject cannot drift
assert doc['counts']['props'] == (doc['counts']['strand_props']
                                  + doc['counts']['hazard_props'])
assert doc['counts']['strands_covered'] == doc['counts']['strands'] == 11
assert doc['counts']['placements'] == sum(len(v) for v in BY_STRAND.values())
assert doc['counts']['pooled'] + doc['counts']['instanced'] \
    + doc['counts']['own_mesh'] == doc['counts']['props']
assert doc['counts']['prop_instances'] == sum(props_per)

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'props.json').write_text(json.dumps(doc, indent=1) + '\n')
c = doc['counts']
b = doc['budget']
print(f"props: {c['props']} props in {c['families']} families "
      f"({c['strand_props']} placed from room purposes, {c['hazard_props']} "
      f"from room conditions), {c['placements']} strand placements over "
      f"{c['strands_covered']}/{c['strands']} strands; "
      f"{c['tris_min']}-{c['tris_max']} tri each (median {c['tris_median']}, "
      f"measured band 46-104); {c['prop_instances']:,} instances standing in "
      f"{c['rooms']:,} rooms of {c['halls']} halls; a hall pays "
      f"{b['per_hall']['calls_min']}-{b['per_hall']['calls_max']} draw calls "
      f"and {b['per_hall']['tris_median']:,} triangles for "
      f"{b['per_hall']['props_median']} props, against a self-imposed "
      f"{CALL_CEIL}-call ceiling read from web/eval_scene.mjs "
      f"(source stamp {stamp})")
