#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy - the exterior kit registry builder.

WHY THIS PACK EXISTS. Five reference models were measured with a glTF
inspector before a line of this file was written. The one that mattered was
a whole residential city block - a place that reads convincingly as a place
- and the measurement said something the eye does not: the entire block is
21,893 triangles over 93 meshes. The median mesh in it is 104 triangles.
The smallest is 2. Its commonest texture is 128x128, thirty-nine times over.
A second reference, one house, is 26,411 triangles over 70 meshes with a
median of 46. Against those, one modern character model measured 222,507
triangles in three meshes behind four 2048-square maps, 12.3 MB of texture
for one figure.

So a place does not read as a place because its geometry is dense. It reads
as a place because there are MANY SMALL DISTINCT PIECES standing on it: a
stoop, a downpipe, a meter box, a vent, a kerb, a length of conduit. That
is the whole finding, and this pack is its consequence. Every piece
declared here is a handful of primitives. The largest is 72 triangles. The
median is smaller than the residential block's.

AND THE ANTI-PATTERN IS IN THE SAME DATA. That block pays 93 materials for
93 meshes: 93 draw calls for one street. It is an export artefact rather
than a design, and copying it is how a page that renders one campus ends up
unable to render two. This bundle already fixed that for its own buildings
- decoration is pooled into ONE MESH PER MATERIAL PER DISTRICT by
`flushParts`, and the station beacons are one `InstancedMesh` per campus by
`flushBeacons` - and this kit is required to go through those same two
doors and open no third one. Seventeen of the eighteen pieces here are
pooled or instanced. `own-mesh` is a value the schema admits and nothing
uses, because the only reason this page gives a piece its own mesh is that
something raycasts it, and the page already has exactly one such mesh per
hall: the wall box carrying `userData.slug`.

WHICH CURRENCY IS SCARCE, MEASURED RATHER THAN ASSUMED. `web/eval_scene.mjs`
scored the live page in Chromium. The campus view costs 273 draw calls and
15,850 triangles. The whole fifty-one-hall campus - roads, yard, beacons,
city layer and all - is SMALLER IN TRIANGLES THAN ONE REFERENCE STREET
BLOCK, while sitting at 273 draw calls. This page is draw-call bound with
an enormous unused triangle budget. Every number in the `budget` block
below is therefore stated in BOTH currencies, the ceilings are READ from
that harness rather than typed here, and the draw-call ceiling is the one
that governs.

NOTHING IS VENDORED AND NOTHING IS COPIED. No file from that measurement is
in this repo, no shape, name, layout or texture from any of them is
reproduced here, and two of the measured files are somebody else's
copyrighted work which this bundle neither ships nor imitates. What was
taken is a NUMBER - a median mesh size - and a technique that the number
justifies. The reference figures are restated in REFERENCE below with their
provenance and their limit: they were measured elsewhere, on files this
repo does not contain, and this build cannot re-run that measurement.

PLACEMENT IS DERIVED, NOT TYPED. No hall is named anywhere in this file.
A family declares which wall it attaches to, which rooflines and which
facade patterns admit it, and how many of it a metre of that wall earns.
The roofline of a district is not decided here: it is READ out of the
page's own `STYLE_OF` table, and the facade vocabulary is READ out of the
world registry's `fabric` block, whose patterns must already exist in the
surfaces registry. The envelope the pieces hang on - 12 metres wide, as
deep as the hall's own room plan makes it, as tall as the page's own height
formula says - is read from `web/build_3d.py` too. Change the page's
envelope and this build fails rather than quietly describing a building
that no longer exists.

WHAT THESE ARE NOT. They are SCHEMATIC: the shape of a thing, not a
measurement of one. A downpipe here is a cylinder and two brackets at a
plausible size; it is not a surveyed rainwater goods component, it carries
no gauge, no fixing centres, no material specification and no standard. No
part of this registry is a construction detail and nobody should build
anything from it. It is stage dressing sized so that a campus reads as a
built place rather than as a diagram of one.
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

BUILT = "2026-09-22"


def req(d, k, who):
    """A missing key raises and names itself. There is no `.get(k, default)`
    in this file and no bare `??`: a default is a policy decision, and a
    policy decision made silently at read time is the defect this bundle
    lints for."""
    if k not in d:
        raise KeyError(f'{who}: required key {k!r} is missing')
    return d[k]


def one(pattern, text, who, flags=0):
    """Exactly one match, or the build stops. Reading a fact out of the page
    is only one-truth-per-fact if the read is unambiguous."""
    hits = re.findall(pattern, text, flags)
    if len(hits) != 1:
        raise AssertionError(
            f'{who}: expected exactly one match for {pattern!r}, found {len(hits)}')
    return hits[0]


# One bundle version, read from the manifest rather than typed here.
PACK_VERSION = req(json.load(open(ROOT / 'pack/manifest.json')),
                   'pack_version', 'pack/manifest.json')

# ------------------------------------------------------- what is READ in ---
# The page. Read, never written, by this pack. Every fact below that
# belongs to the page - the envelope, the roofline table, which materials
# the district pool already carries - comes out of this text, so the kit
# cannot describe a building the page stopped drawing.
PAGE_SRC = (ROOT / 'web/build_3d.py').read_text()

# The scene harness. The measured cost of the live page and the ceilings it
# holds that cost to. Both the baseline and the headroom are read here, so
# this pack's budget cannot drift from the numbers the harness enforces.
EVAL_SRC = (ROOT / 'web/eval_scene.mjs').read_text()

WORLD = json.load(open(ROOT / 'world/registry/world.json'))
DISTRICTS = req(json.load(open(ROOT / 'unions/registry/districts.json')),
                'districts', 'unions/registry/districts.json')
CAMPUSES = req(json.load(open(ROOT / 'unions/registry/campuses.json')),
               'campuses', 'unions/registry/campuses.json')
FINISHES = json.load(open(ROOT / 'surfaces/registry/finishes.json'))
UNIONS = req(json.load(open(ROOT / 'unions/registry/unions.json')),
             'unions', 'unions/registry/unions.json')

# The hall envelope depth is not a registry field: it falls out of the room
# programme, exactly as the page computes it. The page calls
# interiors.build(); this reads the same plan through the same module, so
# there is one room-plan truth and this pack holds no copy of it.
sys.path.insert(0, str(ROOT / 'web'))
import interiors  # noqa: E402

HALL_DEPTH = {req(h, 'slug', 'unions[]'):
              req(req(interiors.plan_for(h, {}), 'envelope', 'plan'),
                  'd', 'plan.envelope')
              for h in UNIONS}

# ------------------------------------------- the envelope, read from the page ---
# `function building(h, style, g, pool, ox = 0, oz = 0)` draws every hall on
# the board. Three constants in it decide how much wall there is to hang a
# piece on, and all three are read rather than restated.
_env = one(r'const dep = Math\.max\(h\.depth, ([\d.]+)\), wid = ([\d.]+);',
           PAGE_SRC, 'page envelope')
DEPTH_FLOOR, HALL_W = float(_env[0]), float(_env[1])
_hgt = one(r'const hgt = ([\d.]+) \+ \(h\.depth % (\d+)\) \* (\.[\d]+);',
           PAGE_SRC, 'page height formula')
HGT_BASE, HGT_MOD, HGT_STEP = float(_hgt[0]), int(_hgt[1]), float('0' + _hgt[2])


def hall_dep(slug):
    return max(HALL_DEPTH[slug], DEPTH_FLOOR)


def hall_hgt(slug):
    return HGT_BASE + (HALL_DEPTH[slug] % HGT_MOD) * HGT_STEP


# The shortest hall on the board. Nothing mounted on a wall may reach over
# the top of the shortest wall it can be mounted on.
MIN_HGT = min(hall_hgt(s) for s in HALL_DEPTH)

# ------------------------------------ the roofline table, read from the page ---
# `STYLE_OF` is the page's, and it stays the page's. A district's roofline
# is an opinion the district holds; where it holds none the CITY decides,
# through the world registry's fabric. Both halves are read.
_style_block = one(r'const STYLE_OF = \{(.*?)\};', PAGE_SRC,
                   'page STYLE_OF', re.S)
STYLE_OF = dict(re.findall(r"(\w[\w-]*):\s*'([a-z]+)'", _style_block))
assert STYLE_OF, 'the page no longer declares a STYLE_OF table'

FABRIC = req(WORLD, 'fabric', 'world/registry/world.json')
ROOFLINES = sorted(set(STYLE_OF.values())
                   | {req(f, 'roof', f'fabric[{k}]') for k, f in FABRIC.items()})
FACADES = sorted({req(f, 'facade', f'fabric[{k}]') for k, f in FABRIC.items()})

# a facade pattern the surfaces registry has never heard of is a second
# vocabulary, which is the defect this bundle lints for
PATTERNS = req(FINISHES, 'patterns', 'surfaces/registry/finishes.json')
for f in FACADES:
    assert f in PATTERNS, \
        f'fabric facade {f!r} is not a pattern surfaces/registry/finishes.json declares'

# Two things about the page, COMPUTED here rather than asserted, because
# they are web/build_3d.py's to fix and this pack must not hold its build
# hostage to somebody else's file. Both are published in `page_findings`.
#
# One: `buildCampus()` resolves a district's roofline as
# STYLE_OF[k] ?? fabric[campus].roof ?? 'flat'. If STYLE_OF names every
# district the union registry declares, neither fallback can ever fire, and
# a comment describing what unopinionated districts do is describing
# nothing.
_unopinionated = sorted(set(DISTRICTS) - set(STYLE_OF))
#
# Two: `FABRIC_FALLBACK` in the page is a literal facade, trim and roof
# spec. If it equals a campus's own fabric row, it is a SECOND COPY of that
# campus's colours living in the page - which is the exact defect this
# bundle lints for everywhere else.
_fb = re.search(r'const FABRIC_FALLBACK = \{(.*?)\};', PAGE_SRC, re.S)
_fb_spec = (dict(re.findall(r"(\w+):\s*'([^']+)'", _fb.group(1))) if _fb else None)
_fb_twin = sorted(k for k, f in FABRIC.items()
                  if _fb_spec is not None
                  and all(f.get(fk) == fv for fk, fv in _fb_spec.items()))


def roofline_of(district, campus):
    """Exactly the page's own expression, in Python:
       STYLE_OF[k] ?? D.world.fabric?.[campusKey]?.roof ?? 'flat'"""
    if district in STYLE_OF:
        return STYLE_OF[district]
    return req(req(FABRIC, campus, 'world.fabric'), 'roof', f'fabric[{campus}]')


# ---------------------------------- which materials the district pool holds ---
# `building()` pushes its decoration into the district pool through one
# closure, `add(m2, ...)`. The materials it already puts there are the ones
# this kit can use for free: a pooled piece costs a draw call only if it
# brings a material the pool did not already have. Read, not listed.
_bld = one(r'function building\(h, style, g, pool, ox = 0, oz = 0\) \{(.*?)\n\}\n',
           PAGE_SRC, 'page building()', re.S)
_raw_pooled = set(re.findall(r'\badd\(([A-Za-z_][\w.]*),', _bld))
assert _raw_pooled, 'building() no longer pools anything through add()'
# the page's local names for the two fabric materials and for the district
# hue, mapped onto this registry's own material vocabulary
_PAGE_ALIAS = {'hueMat': 'district-hue', 'fab.trim': 'fabric.trim',
               'fab.roof': 'fabric.roof', 'fab.wall': 'fabric.wall'}
ALREADY_POOLED = sorted(_PAGE_ALIAS[m] if m in _PAGE_ALIAS else m
                        for m in _raw_pooled)

# the material vocabulary: every `mat.*` singleton the page declares, and
# every material `fabricOf()` returns
_mat_block = one(r'\nconst mat = \{(.*?)\n\};', PAGE_SRC, 'page mat table', re.S)
MAT_KEYS = sorted(set(re.findall(r'^\s{2}(\w+):', _mat_block, re.M)))
assert len(MAT_KEYS) > 10, 'the page mat table did not parse'
_fab_block = one(r'\n  fabMats = \{(.*?)\n  \};', PAGE_SRC, 'page fabMats', re.S)
FAB_KEYS = sorted(set(re.findall(r'^\s{4}(\w+)[:,]', _fab_block, re.M)))
assert {'wall', 'trim', 'roof'} <= set(FAB_KEYS), 'the page fabric materials did not parse'

MATERIAL_VOCAB = sorted([f'mat.{k}' for k in MAT_KEYS]
                        + [f'fabric.{k}' for k in FAB_KEYS]
                        + ['district-hue'])

# the functions this pack's contract names must all still exist
PAGE_FUNCS = ['flushParts', 'flushBeacons', 'hueMatOf', 'fabricOf',
              'buildCampus', 'building', 'spinBeacons', 'disposeOf']
for fn in PAGE_FUNCS:
    assert f'function {fn}(' in PAGE_SRC, \
        f'the page no longer declares {fn}(); this pack\'s contract names it'

# ------------------------------- the measured cost of the page, read from the harness ---
_base_block = one(r'const BASE = \{(.*?)\n\};', EVAL_SRC, 'eval BASE', re.S)
SCENE_BASE = {m[0]: {'calls': int(m[1].replace('_', '')),
                     'tris': int(m[2].replace('_', '')),
                     'meshes': int(m[3].replace('_', ''))}
              for m in re.findall(
                  r'(\w+):\s*\{\s*calls:\s*([\d_]+),\s*tris:\s*([\d_]+),'
                  r'\s*meshes:\s*([\d_]+)\s*\}', _base_block)}
for v in ('region', 'campus', 'hall'):
    assert v in SCENE_BASE, f'the scene harness no longer measures the {v} view'
CALL_HEADROOM = float(one(r'const CALL_HEADROOM = ([\d.]+);', EVAL_SRC,
                          'eval CALL_HEADROOM'))
TRI_HEADROOM = float(one(r'const TRI_HEADROOM = ([\d.]+);', EVAL_SRC,
                         'eval TRI_HEADROOM'))

# The campus view is the one this kit lands in, and it is the one the
# harness drives to `campus:treasure-island`. That campus is therefore the
# campus this pack budgets, and it is READ out of the harness rather than
# picked: budgeting a campus the harness never measured would be arithmetic
# about nowhere.
BUDGET_CAMPUS = one(r"__tc3dDo\('view', 'campus:([a-z-]+)'\)", EVAL_SRC,
                    'eval campus target')
assert BUDGET_CAMPUS in CAMPUSES, \
    f'the harness drives to {BUDGET_CAMPUS}, which is not a campus'

CAMPUS_CALLS = SCENE_BASE['campus']['calls']
CAMPUS_TRIS = SCENE_BASE['campus']['tris']
CALL_CEILING = round(CAMPUS_CALLS * CALL_HEADROOM) - CAMPUS_CALLS
TRI_CEILING = int(CAMPUS_TRIS * TRI_HEADROOM) - CAMPUS_TRIS

# The harness's own comment names TWO packs expected to spend the triangle
# headroom: this kit and a props pack. Taking all of it would leave the
# other with none, so this pack declares the share it may take and is held
# to it. The larger share is this kit's because it clothes fifty-one
# buildings, where props furnish the ground between them - and the split is
# stated here so that it is a decision somebody made rather than whatever
# the arithmetic happened to come to.
TRI_SHARE = 0.70
TRI_SHARE_WHY = (
    'web/eval_scene.mjs allows the campus view four times its measured '
    '15,850 triangles and says in its own comment that the kit and props '
    'packs are expected to spend it. Two packs cannot each spend all of it. '
    'This kit takes 70 per cent of the headroom because it clothes every '
    'one of the fifty-one building envelopes on the campus, and leaves 30 '
    'per cent for the props that stand on the ground between them.')
KIT_TRI_CEILING = int(TRI_CEILING * TRI_SHARE)

# ------------------------------------------- the measurement this pack rests on ---
# Restated here with its provenance and its limit. Nothing was vendored:
# these are numbers from an inspection run outside this repo, on files this
# repo does not contain and this build cannot open.
REFERENCE = {
    'provenance': 'MEASURED-ELSEWHERE',
    'how': ('a glTF 2.0 inspection of six downloaded reference models, run '
            'outside this repository on files it does not contain. This '
            'build cannot re-run it and does not try to: the figures below '
            'are quoted, not verified here.'),
    'not_vendored': ('No mesh, texture, name, shape or layout from any '
                     'measured file is reproduced in this pack or anywhere '
                     'in this bundle. Two of the five are third-party '
                     'copyrighted work. What was taken is a distribution.'),
    'block_median_tris': 104,
    'block_total_tris': 21893,
    'block_meshes': 93,
    'block_materials': 93,
    'block_note': ('one residential city block that reads convincingly as a '
                   'place: 21,893 triangles over 93 meshes, median mesh 104 '
                   'triangles, smallest 2, commonest texture 128x128'),
    'house_median_tris': 46,
    'house_meshes': 70,
    'house_note': ('one house from the same era: 26,411 triangles over 70 '
                   'meshes, median 46, forty of its textures 128x128'),
    'character_tris': 222507,
    'character_meshes': 3,
    'character_tex_mb': 12.3,
    'character_note': ('one modern character model: 222,507 triangles in 3 '
                       'meshes behind four 2048-square maps, 12.3 MB of '
                       'texture for one figure - ten times this whole page'),
    'anti_pattern': ('the block pays 93 materials for 93 meshes, which is '
                     '93 draw calls for one street. That is an export '
                     'artefact, not a design, and this kit is held to the '
                     'opposite arrangement by its own draw-call check.'),
}

# -------------------------------------------------------- the tri formulas ---
# Stated, then applied. Every tri_budget in this file is typed by hand and
# then asserted against what its own primitive recipe actually costs, so a
# budget cannot be aspirational.
TRI_FORMULA = {
    'box': ('a THREE.BoxGeometry with one segment per axis is six quads, '
            'so 12 triangles, whatever its dimensions'),
    'cylinder_capped': ('a THREE.CylinderGeometry with N radial segments and '
                        'one height segment is 2N on the side plus N per cap: '
                        '4N triangles'),
    'cylinder_open': ('the same cylinder with openEnded true is the side '
                      'only: 2N triangles'),
}


def tri_cost(prims, who):
    """The declared formula, applied. Nothing else may appear in a recipe:
    a shape this function does not know is a shape whose cost nobody stated."""
    total = 0
    for p in prims:
        shape = req(p, 'shape', who)
        n = req(p, 'n', who)
        assert isinstance(n, int) and n > 0, f'{who}: a recipe entry of {n}'
        if shape == 'box':
            total += 12 * n
        elif shape == 'cylinder':
            seg = req(p, 'segments', who)
            assert 4 <= seg <= 12, \
                f'{who}: {seg} radial segments is not a schematic prop'
            capped = req(p, 'capped', who)
            total += n * ((4 * seg) if capped else (2 * seg))
        else:
            raise AssertionError(
                f'{who}: {shape!r} is not a primitive this bundle builds from')
    return total


# ------------------------------------------------------------ the families ---
# A closed set. Every piece names one of these and nothing else, every one
# of them carries a placement rule, and every one of them has at least one
# piece - a family with no piece is a vocabulary word nothing says.
WALLS = ['front', 'back', 'side', 'roofline', 'ground']
RUNS = {
    'frontage':       lambda w, d: w,
    'front_width':    lambda w, d: w,
    'back_width':     lambda w, d: w,
    'both_sides':     lambda w, d: 2 * d,
    'roof_perimeter': lambda w, d: 2 * (w + d),
    'eaves_run':      lambda w, d: 2 * d,
}
RUN_OF_WALL = {
    'front': ['front_width', 'frontage'],
    'back': ['back_width'],
    'side': ['both_sides'],
    'roofline': ['roof_perimeter', 'eaves_run'],
    'ground': ['frontage'],
}
DATUMS = ['grade', 'wall', 'eaves']

_ALL_FACADES = list(FACADES)          # derived, never typed
_ALL_ROOFS = list(ROOFLINES)          # derived, never typed

PLACEMENT = {
    'stoop': {
        'wall': 'front', 'run': 'frontage', 'datum': 'grade', 'offset_m': 0.0,
        'rooflines': _ALL_ROOFS, 'facades': _ALL_FACADES,
        'why': ('the page builds every hall with its door toward local -z, so '
                'the front is the one wall whose position is guaranteed; a '
                'threshold sits on the ground in front of it whatever the '
                'city is built of'),
    },
    'step': {
        'wall': 'front', 'run': 'frontage', 'datum': 'grade', 'offset_m': 0.0,
        'rooflines': _ALL_ROOFS, 'facades': _ALL_FACADES,
        'why': ('a tread in front of the threshold, for the same reason and '
                'at the same wall'),
    },
    'kerb': {
        'wall': 'ground', 'run': 'frontage', 'datum': 'grade', 'offset_m': 0.0,
        'rooflines': _ALL_ROOFS, 'facades': _ALL_FACADES,
        'why': ('buildCampus() already lays a driveway to every door; a kerb '
                'is the edge that driveway meets, and it belongs to the '
                'ground rather than to any wall'),
    },
    'parapet': {
        'wall': 'roofline', 'run': 'roof_perimeter', 'datum': 'eaves',
        'offset_m': 0.10, 'rooflines': ['flat'], 'facades': _ALL_FACADES,
        'why': ('a parapet is what a flat roof has instead of an eaves. The '
                'page draws the flat roofline as a rooftop unit and nothing '
                'else, so the top of a flat hall is the one edge with '
                'nothing on it'),
    },
    'gutter': {
        'wall': 'roofline', 'run': 'eaves_run', 'datum': 'eaves',
        'offset_m': -0.15, 'rooflines': ['gable'], 'facades': _ALL_FACADES,
        'why': ('a gutter needs an eaves to hang off, and the page gives an '
                'eaves only to the gable roofline - its two pitched slabs '
                'run along the depth, so the gutter does too'),
    },
    'downpipe': {
        'wall': 'side', 'run': 'both_sides', 'datum': 'wall', 'offset_m': 0.0,
        'rooflines': _ALL_ROOFS, 'facades': _ALL_FACADES,
        'why': ('water comes off every roofline this page draws, and it comes '
                'down a side wall rather than across the door'),
    },
    'vent': {
        'wall': 'side', 'run': 'both_sides', 'datum': 'wall', 'offset_m': 3.2,
        'rooflines': _ALL_ROOFS, 'facades': _ALL_FACADES,
        'why': ('every hall in this bundle has plant in it; the side wall is '
                'where a hall puts what it does not want on its front'),
    },
    'awning': {
        'wall': 'front', 'run': 'front_width', 'datum': 'wall',
        'offset_m': 2.7, 'rooflines': ['flat', 'gable'], 'facades': _ALL_FACADES,
        'why': ('shade over the entrance. A sawtooth hall\'s front is a goods '
                'opening rather than a door people gather at, so it is not '
                'given one'),
    },
    'bollard': {
        'wall': 'ground', 'run': 'frontage', 'datum': 'grade', 'offset_m': 0.0,
        'rooflines': _ALL_ROOFS, 'facades': _ALL_FACADES,
        'why': ('the driveway runs to the door; something has to stop it '
                'running through the door'),
    },
    'rail': {
        'wall': 'front', 'run': 'front_width', 'datum': 'wall',
        'offset_m': 0.95, 'rooflines': _ALL_ROOFS, 'facades': _ALL_FACADES,
        'why': ('a hand hold beside the threshold, on the wall the door is '
                'in. Every hall has a stoop and a tread, so every hall has '
                'the small change of level a rail exists for'),
    },
    'sign-bracket': {
        'wall': 'front', 'run': 'front_width', 'datum': 'wall',
        'offset_m': 3.6, 'rooflines': _ALL_ROOFS, 'facades': _ALL_FACADES,
        'why': ('the page already hangs a district-hued fascia on the hall; '
                'the bracket is the ironwork that arm would need, and it '
                'carries nothing itself - the label sprite is the page\'s'),
    },
    'conduit': {
        'wall': 'back', 'run': 'back_width', 'datum': 'wall', 'offset_m': 1.2,
        'rooflines': ['flat', 'saw'], 'facades': _ALL_FACADES,
        'why': ('surface conduit runs up the back of a building to the roof '
                'plant. On a gable there is no roof deck to run to, so the '
                'gable rooflines do not admit it'),
    },
    'meter-box': {
        'wall': 'back', 'run': 'back_width', 'datum': 'wall', 'offset_m': 1.5,
        'rooflines': _ALL_ROOFS, 'facades': _ALL_FACADES,
        'why': ('the service entry goes on the wall nobody arrives at, which '
                'on this page is the wall away from the plaza - the page '
                'points every door at local -z, so the back is knowable'),
    },
    'planter': {
        'wall': 'ground', 'run': 'frontage', 'datum': 'grade', 'offset_m': 0.0,
        'rooflines': _ALL_ROOFS, 'facades': _ALL_FACADES,
        'why': ('the campus already has a green ring and a walkway; a tub at '
                'the frontage is the same idea at building scale'),
    },
    'cage-ladder': {
        'wall': 'back', 'run': 'back_width', 'datum': 'wall', 'offset_m': 0.9,
        'rooflines': ['flat', 'saw'],
        'facades': ['block', 'brick', 'panel'],
        'why': ('roof access reaches a flat deck or a sawtooth valley, never '
                'a pitch. It also needs a facade that takes a fixing: the '
                'plywood and smooth-stucco cities do not get one'),
    },
}
FAMILIES = sorted(PLACEMENT)

# ------------------------------------------------------------- the pieces ---
# Each one: a family, a typed triangle budget with the reason it is that
# size, a size in metres, the primitive recipe it is actually built from,
# the material it wears - which must be one the page ALREADY has - and how
# it reaches the screen.
_WHY_MEDIAN = ('the measured residential-block reference has a median mesh '
               'of 104 triangles and this sits under it')
_WHY_SMALL = ('the same reference\'s smallest meshes are 2 to 9 triangles and '
              'its median is 104; a single box at 12 is that size of thing, '
              'and the place reads off how MANY of them there are')

PIECES = {
    'entry-stoop': {
        'name': 'Entrance stoop', 'family': 'stoop',
        'tri_budget': 36, 'size_m': [2.6, 0.45, 1.4],
        'primitives': [{'shape': 'box', 'n': 3,
                        'note': 'the pad, the riser below it, one cheek wall'}],
        'material': 'mat.slab', 'merges': 'pooled',
        'merge_why': ('one box set per hall in the district\'s slab pool; '
                      'nothing raycasts a stoop and nothing moves it'),
        'tri_why': f'three boxes at 12 triangles each. {_WHY_MEDIAN}.',
    },
    'entry-step': {
        'name': 'Entrance tread', 'family': 'step',
        'tri_budget': 12, 'size_m': [2.4, 0.15, 0.34],
        'primitives': [{'shape': 'box', 'n': 1, 'note': 'one tread'}],
        'material': 'mat.slab', 'merges': 'pooled',
        'merge_why': 'a single box, pooled with every other slab piece in the district',
        'tri_why': f'one box. {_WHY_SMALL}.',
    },
    'kerb-run': {
        'name': 'Kerb run', 'family': 'kerb',
        'tri_budget': 12, 'size_m': [4.0, 0.14, 0.30],
        'primitives': [{'shape': 'box', 'n': 1, 'note': 'four metres of kerb'}],
        'material': 'mat.slab', 'merges': 'pooled',
        'merge_why': 'a run of kerb is a box; pooled, a whole district\'s kerbs are one mesh',
        'tri_why': f'one box. {_WHY_SMALL}.',
    },
    'parapet-coping': {
        'name': 'Parapet coping run', 'family': 'parapet',
        'tri_budget': 12, 'size_m': [6.0, 0.18, 0.60],
        'primitives': [{'shape': 'box', 'n': 1, 'note': 'six metres of coping'}],
        'material': 'fabric.roof', 'merges': 'pooled',
        'merge_why': ('fabric.roof is ALREADY in the district pool - '
                      'building() puts the roofline there - so this costs no '
                      'draw call at all'),
        'tri_why': f'one box. {_WHY_SMALL}.',
    },
    'parapet-corner': {
        'name': 'Parapet corner block', 'family': 'parapet',
        'tri_budget': 12, 'size_m': [0.70, 0.26, 0.70],
        'primitives': [{'shape': 'box', 'n': 1, 'note': 'the returned corner'}],
        'material': 'fabric.roof', 'merges': 'pooled',
        'merge_why': 'same pool, same material, same zero cost in draw calls',
        'tri_why': f'one box. {_WHY_SMALL}.',
    },
    'eaves-gutter': {
        'name': 'Eaves gutter', 'family': 'gutter',
        'tri_budget': 24, 'size_m': [4.0, 0.16, 0.18],
        'primitives': [{'shape': 'box', 'n': 1, 'note': 'the trough'},
                       {'shape': 'cylinder', 'n': 1, 'segments': 6,
                        'capped': False, 'note': 'the rolled front bead'}],
        'material': 'mat.metal', 'merges': 'pooled',
        'merge_why': 'every metal piece in the district merges into one mesh',
        'tri_why': ('one box at 12 plus a six-sided open cylinder at 2x6=12. '
                    f'{_WHY_MEDIAN}.'),
    },
    'downpipe-run': {
        'name': 'Downpipe run', 'family': 'downpipe',
        'tri_budget': 40, 'size_m': [0.14, 5.4, 0.14],
        'primitives': [{'shape': 'cylinder', 'n': 1, 'segments': 8,
                        'capped': False, 'note': 'the pipe, open at both ends'},
                       {'shape': 'box', 'n': 2, 'note': 'two wall brackets'}],
        'material': 'mat.metal', 'merges': 'pooled',
        'merge_why': 'pooled with the district\'s other metal',
        'tri_why': ('an eight-sided open cylinder at 2x8=16 plus two boxes at '
                    f'24. {_WHY_MEDIAN}.'),
    },
    'downpipe-shoe': {
        'name': 'Downpipe shoe', 'family': 'downpipe',
        'tri_budget': 24, 'size_m': [0.20, 0.30, 0.40],
        'primitives': [{'shape': 'cylinder', 'n': 1, 'segments': 6,
                        'capped': True, 'note': 'the spill at the bottom'}],
        'material': 'mat.metal', 'merges': 'pooled',
        'merge_why': 'pooled with the district\'s other metal',
        'tri_why': f'a six-sided capped cylinder at 4x6=24. {_WHY_MEDIAN}.',
    },
    'wall-vent': {
        'name': 'Wall vent hood', 'family': 'vent',
        'tri_budget': 40, 'size_m': [0.50, 0.50, 0.36],
        'primitives': [{'shape': 'box', 'n': 2,
                        'note': 'the back plate and the hood'},
                       {'shape': 'cylinder', 'n': 1, 'segments': 8,
                        'capped': False, 'note': 'the spigot through the wall'}],
        'material': 'mat.metal', 'merges': 'pooled',
        'merge_why': 'pooled with the district\'s other metal',
        'tri_why': f'two boxes at 24 plus 2x8=16. {_WHY_MEDIAN}.',
    },
    'louvre-vent': {
        'name': 'Louvred vent panel', 'family': 'vent',
        'tri_budget': 24, 'size_m': [0.90, 0.60, 0.12],
        'primitives': [{'shape': 'box', 'n': 2,
                        'note': 'the frame and the blade face'}],
        'material': 'mat.metal', 'merges': 'pooled',
        'merge_why': 'pooled with the district\'s other metal',
        'tri_why': ('two boxes. The blades are a texture\'s job, not a '
                    f'geometry\'s. {_WHY_MEDIAN}.'),
    },
    'door-awning': {
        'name': 'Door awning', 'family': 'awning',
        'tri_budget': 36, 'size_m': [2.4, 0.34, 1.1],
        'primitives': [{'shape': 'box', 'n': 3,
                        'note': 'the canopy and two struts'}],
        'material': 'fabric.trim', 'merges': 'pooled',
        'merge_why': ('fabric.trim is ALREADY in the district pool - '
                      'building() puts the door surround and the pilasters '
                      'there - so the awning is free in draw calls and wears '
                      'the city\'s own trim colour without holding a copy of it'),
        'tri_why': f'three boxes. {_WHY_MEDIAN}.',
    },
    'bollard': {
        'name': 'Bollard', 'family': 'bollard',
        'tri_budget': 32, 'size_m': [0.22, 0.95, 0.22],
        'primitives': [{'shape': 'cylinder', 'n': 1, 'segments': 8,
                        'capped': True, 'note': 'the post, capped'}],
        'material': 'mat.post', 'merges': 'instanced',
        'merge_why': ('identical at every hall and there are hundreds of them, '
                      'which is exactly the case flushBeacons() already '
                      'solves: one InstancedMesh for the whole campus, one '
                      'draw call, no merge and no per-hall geometry'),
        'tri_why': f'an eight-sided capped cylinder at 4x8=32. {_WHY_MEDIAN}.',
    },
    'wall-rail': {
        'name': 'Wall-mounted hand rail', 'family': 'rail',
        'tri_budget': 36, 'size_m': [2.4, 0.08, 0.14],
        'primitives': [{'shape': 'cylinder', 'n': 1, 'segments': 6,
                        'capped': False, 'note': 'the rail itself'},
                       {'shape': 'box', 'n': 2, 'note': 'two brackets'}],
        'material': 'mat.metal', 'merges': 'pooled',
        'merge_why': 'pooled with the district\'s other metal',
        'tri_why': f'2x6=12 plus two boxes at 24. {_WHY_MEDIAN}.',
    },
    'sign-bracket': {
        'name': 'Sign bracket', 'family': 'sign-bracket',
        'tri_budget': 36, 'size_m': [0.95, 0.70, 0.14],
        'primitives': [{'shape': 'box', 'n': 3,
                        'note': 'the arm, the stay and the wall plate'}],
        'material': 'mat.metal', 'merges': 'pooled',
        'merge_why': 'pooled with the district\'s other metal',
        'tri_why': f'three boxes. {_WHY_MEDIAN}.',
    },
    'conduit-run': {
        'name': 'Surface conduit run', 'family': 'conduit',
        'tri_budget': 36, 'size_m': [0.08, 4.2, 0.08],
        'primitives': [{'shape': 'cylinder', 'n': 1, 'segments': 6,
                        'capped': False, 'note': 'the conduit'},
                       {'shape': 'box', 'n': 2, 'note': 'two saddles'}],
        'material': 'mat.metal', 'merges': 'pooled',
        'merge_why': 'pooled with the district\'s other metal',
        'tri_why': f'2x6=12 plus two boxes at 24. {_WHY_MEDIAN}.',
    },
    'meter-box': {
        'name': 'Meter box', 'family': 'meter-box',
        'tri_budget': 24, 'size_m': [0.55, 0.75, 0.26],
        'primitives': [{'shape': 'box', 'n': 2,
                        'note': 'the enclosure and its door'}],
        'material': 'mat.metal', 'merges': 'pooled',
        'merge_why': 'pooled with the district\'s other metal',
        'tri_why': f'two boxes. {_WHY_MEDIAN}.',
    },
    'planter-tub': {
        'name': 'Planter tub', 'family': 'planter',
        'tri_budget': 48, 'size_m': [1.2, 0.55, 1.2],
        'primitives': [{'shape': 'box', 'n': 4,
                        'note': 'the tub as four sides; no soil box, the '
                                'top is never seen from a walker\'s eye'}],
        'material': 'mat.slab', 'merges': 'instanced',
        'merge_why': ('identical everywhere, like the bollard, so it takes '
                      'the same InstancedMesh treatment rather than growing '
                      'the merged slab geometry on every district'),
        'tri_why': f'four boxes. {_WHY_MEDIAN}.',
    },
    'cage-ladder': {
        'name': 'Caged roof ladder', 'family': 'cage-ladder',
        'tri_budget': 72, 'size_m': [0.52, 5.0, 0.16],
        'primitives': [{'shape': 'box', 'n': 6,
                        'note': 'two stiles and four rungs; the cage hoops '
                                'are the one thing here a texture cannot fake '
                                'and are still left out, because six boxes '
                                'reads as a ladder and eighteen does not'}],
        'material': 'mat.metal', 'merges': 'pooled',
        'merge_why': 'pooled with the district\'s other metal',
        'tri_why': ('six boxes at 72 - the largest piece in this kit, and '
                    'still under the 104-triangle median of the measured '
                    'reference block'),
    },
}

# ------------------------------------------------------------ how many ------
# Per piece, either a fixed count per hall or a rate along the run its
# family attaches to. A rate is resolved with ceil, so a wall that exists at
# all gets at least one: that is the policy, stated once, rather than a
# minimum bolted on somewhere else.
COUNTS = {
    'entry-stoop':    {'mode': 'per_hall', 'n': 1},
    'entry-step':     {'mode': 'per_hall', 'n': 1},
    'kerb-run':       {'mode': 'per_run_m', 'every_m': 6.0},
    'parapet-coping': {'mode': 'per_run_m', 'every_m': 16.0},
    'parapet-corner': {'mode': 'per_hall', 'n': 2},
    'eaves-gutter':   {'mode': 'per_run_m', 'every_m': 6.0},
    'downpipe-run':   {'mode': 'per_hall', 'n': 2},
    'downpipe-shoe':  {'mode': 'per_hall', 'n': 1},
    'wall-vent':      {'mode': 'per_run_m', 'every_m': 26.0},
    'louvre-vent':    {'mode': 'per_hall', 'n': 1},
    'door-awning':    {'mode': 'per_hall', 'n': 1},
    'bollard':        {'mode': 'per_run_m', 'every_m': 12.0},
    'wall-rail':      {'mode': 'per_hall', 'n': 1},
    'sign-bracket':   {'mode': 'per_hall', 'n': 1},
    'conduit-run':    {'mode': 'per_run_m', 'every_m': 12.0},
    'meter-box':      {'mode': 'per_hall', 'n': 1},
    'planter-tub':    {'mode': 'per_hall', 'n': 1},
    'cage-ladder':    {'mode': 'per_hall', 'n': 1},
}
COUNT_POLICY = ('a per_run_m rate is resolved with ceil against the metres '
                'that run actually has, so a wall that exists gets at least '
                'one piece and a deeper hall earns more of them; a per_hall '
                'count is a fixed number of that piece per building. There '
                'is no third mode and no implicit minimum.')

# ------------------------------------------------------------- the checks ---
for pid, p in PIECES.items():
    who = f'pieces[{pid}]'
    fam = req(p, 'family', who)
    assert fam in PLACEMENT, f'{who}: {fam!r} is not a family this pack declares'
    assert len(req(p, 'name', who)) > 3, f'{who}: no name'
    size = req(p, 'size_m', who)
    assert len(size) == 3 and all(isinstance(v, float) for v in size), \
        f'{who}: size_m is [w, h, d] in metres'
    assert all(0.05 <= v <= 16.0 for v in size), \
        f'{who}: {size} is not the size of a prop on a building'
    # the budget is typed and then held to the recipe
    actual = tri_cost(req(p, 'primitives', who), who)
    assert req(p, 'tri_budget', who) == actual, \
        (f'{who}: declares {p["tri_budget"]} triangles, its recipe costs '
         f'{actual}')
    assert actual <= REFERENCE['block_median_tris'], \
        (f'{who}: {actual} triangles is over the {REFERENCE["block_median_tris"]}'
         '-triangle median of the measured reference block')
    assert len(req(p, 'tri_why', who)) > 40, f'{who}: say why that budget'
    assert str(REFERENCE['block_median_tris']) in p['tri_why'] \
        or 'median' in p['tri_why'], \
        f'{who}: the tri_why must cite the measured median'
    # the material must be one the page already has
    m = req(p, 'material', who)
    assert m in MATERIAL_VOCAB, \
        (f'{who}: {m!r} is not a material web/build_3d.py declares - this '
         'pack invents no materials')
    assert m != 'district-hue', \
        (f'{who}: the district hue belongs to the hall envelope band, not to '
         'a prop hanging off it')
    # and how it reaches the screen
    mg = req(p, 'merges', who)
    assert mg in ('pooled', 'instanced', 'own-mesh'), \
        f'{who}: {mg!r} is not a merge strategy'
    assert len(req(p, 'merge_why', who)) > 30, f'{who}: say why that merge'
    assert pid in COUNTS, f'{who}: no count rule'

for pid, c in COUNTS.items():
    assert pid in PIECES, f'counts[{pid}]: no such piece'
    mode = req(c, 'mode', f'counts[{pid}]')
    if mode == 'per_hall':
        n = req(c, 'n', f'counts[{pid}]')
        assert 1 <= n <= 8, f'counts[{pid}]: {n} of one piece per hall'
    elif mode == 'per_run_m':
        e = req(c, 'every_m', f'counts[{pid}]')
        assert 1.0 <= e <= 40.0, f'counts[{pid}]: a rate of one per {e} m'
    else:
        raise AssertionError(f'counts[{pid}]: {mode!r} is not a count mode')

# every family carries a rule, every rule is spent on at least one piece
_fam_used = {p['family'] for p in PIECES.values()}
assert _fam_used == set(PLACEMENT), \
    ('a family with no piece is a vocabulary word nothing says: '
     f'{sorted(set(PLACEMENT) - _fam_used)}')

for fam, r in PLACEMENT.items():
    who = f'placement[{fam}]'
    w = req(r, 'wall', who)
    assert w in WALLS, f'{who}: {w!r} is not a wall'
    run = req(r, 'run', who)
    assert run in RUNS, f'{who}: {run!r} is not a run measure'
    assert run in RUN_OF_WALL[w], \
        f'{who}: the {w} wall is not measured by {run}'
    d = req(r, 'datum', who)
    assert d in DATUMS, f'{who}: {d!r} is not a datum'
    off = req(r, 'offset_m', who)
    if d == 'grade':
        assert off == 0.0, f'{who}: a grade-datum piece sits on the ground'
    elif d == 'eaves':
        assert -0.5 <= off <= 0.5, f'{who}: {off} m off the eaves is not a detail'
    else:
        assert 0.0 <= off <= MIN_HGT, f'{who}: mounted at {off} m'
    rls = req(r, 'rooflines', who)
    assert rls and set(rls) <= set(ROOFLINES), \
        f'{who}: {sorted(set(rls) - set(ROOFLINES))} is not a roofline this world has'
    fcs = req(r, 'facades', who)
    assert fcs and set(fcs) <= set(FACADES), \
        f'{who}: {sorted(set(fcs) - set(FACADES))} is not a facade this world has'
    assert len(req(r, 'why', who)) > 60, f'{who}: say why it goes there'

# nothing mounted on a wall may reach over the top of the shortest wall it
# can be mounted on - the page's own height formula decides what that is
for pid, p in PIECES.items():
    r = PLACEMENT[p['family']]
    if r['datum'] == 'wall':
        top = r['offset_m'] + p['size_m'][1]
        assert top <= MIN_HGT, \
            (f'pieces[{pid}]: mounted at {r["offset_m"]} m and {p["size_m"][1]} m '
             f'tall reaches {top:.2f} m, over the {MIN_HGT:.2f} m of the '
             'shortest hall the page builds')

# every roofline and every facade this world can produce must be admitted by
# something: a roofline no family accepts is a city with bare buildings
for rl in ROOFLINES:
    assert any(rl in r['rooflines'] for r in PLACEMENT.values()), \
        f'no family admits the {rl!r} roofline'
for fc in FACADES:
    assert any(fc in r['facades'] for r in PLACEMENT.values()), \
        f'no family admits the {fc!r} facade'

# ------------------------------------------------------------ the budget ----


def admits(fam, roofline, facade):
    r = PLACEMENT[fam]
    return roofline in r['rooflines'] and facade in r['facades']


def count_for(pid, wid, dep):
    c = COUNTS[pid]
    if c['mode'] == 'per_hall':
        return c['n']
    run = PLACEMENT[PIECES[pid]['family']]['run']
    return math.ceil(RUNS[run](wid, dep) / c['every_m'])


def budget_campus(ck):
    """The whole arithmetic for one campus, computed from the registries."""
    camp = req(CAMPUSES, ck, 'campuses')
    facade = req(req(FABRIC, ck, 'world.fabric'), 'facade', f'fabric[{ck}]')
    per_district, pieces, tris, halls = {}, 0, 0, 0
    pooled_new, instanced_fams, per_hall_counts = set(), set(), {}
    by_family = {f: 0 for f in FAMILIES}
    for k in req(camp, 'districts', f'campuses[{ck}]'):
        rl = roofline_of(k, ck)
        dmats, dp, dt = set(), 0, 0
        for slug in req(req(DISTRICTS, k, 'districts'), 'halls', f'districts[{k}]'):
            dep, hp = hall_dep(slug), 0
            for pid, p in PIECES.items():
                if not admits(p['family'], rl, facade):
                    continue
                n = count_for(pid, HALL_W, dep)
                dp += n
                hp += n
                dt += n * p['tri_budget']
                by_family[p['family']] += n
                if p['merges'] == 'pooled':
                    dmats.add(p['material'])
                elif p['merges'] == 'instanced':
                    instanced_fams.add(p['family'])
            per_hall_counts[slug] = hp
            halls += 1
        new = sorted(m for m in dmats if m not in ALREADY_POOLED)
        pooled_new |= set(new)
        per_district[k] = {'roofline': rl, 'halls': len(DISTRICTS[k]['halls']),
                           'pieces': dp, 'triangles': dt,
                           'pooled_materials': sorted(dmats),
                           'new_draw_calls': len(new),
                           'free_materials': sorted(m for m in dmats
                                                    if m in ALREADY_POOLED)}
        pieces += dp
        tris += dt
    draws = sum(d['new_draw_calls'] for d in per_district.values()) \
        + len(instanced_fams)
    return {
        'campus': ck, 'facade': facade,
        'halls': halls, 'districts': len(camp['districts']),
        'pieces': pieces, 'triangles': tris, 'draw_calls': draws,
        'pooled_draw_calls': draws - len(instanced_fams),
        'instanced_draw_calls': len(instanced_fams),
        'own_mesh_draw_calls': 0,
        'new_pooled_materials': sorted(pooled_new),
        'instanced_families': sorted(instanced_fams),
        'per_district': per_district,
        'by_family': by_family,
        'pieces_per_hall_min': (min(per_hall_counts.values())
                                if per_hall_counts else 0),
        'pieces_per_hall_max': (max(per_hall_counts.values())
                                if per_hall_counts else 0),
        'distinct_hall_loadouts': len(set(per_hall_counts.values())),
    }


BUDGETS = {ck: budget_campus(ck) for ck in CAMPUSES
           if CAMPUSES[ck]['districts']}
MAIN = BUDGETS[BUDGET_CAMPUS]

# a piece that never lands anywhere is a piece nobody asked for
_placed = {f for b in BUDGETS.values() for f, n in b['by_family'].items() if n}
assert _placed == set(FAMILIES), \
    f'families that never place anywhere: {sorted(set(FAMILIES) - _placed)}'

# the identity claim, checked: halls must not all get the same loadout, or
# the kit is a uniform coat of paint rather than a way of telling halls apart
assert MAIN['distinct_hall_loadouts'] > 1, \
    ('every hall on the budgeted campus gets an identical piece count - the '
     'kit would add detail without adding identity')
assert len({d['roofline'] for d in MAIN['per_district'].values()}) > 1, \
    'every district on the budgeted campus has the same roofline'

# THE CEILING. Draw calls are the scarce currency, and the ceiling is the
# harness's own: the campus view is held to its measured cost times the
# headroom that file declares, so the kit may spend what is left and no more.
WORST_CALLS = max(b['draw_calls'] for b in BUDGETS.values())
assert WORST_CALLS <= CALL_CEILING, \
    (f'the kit adds {WORST_CALLS} draw calls at its worst campus; '
     f'web/eval_scene.mjs allows {CALL_CEILING} over the measured '
     f'{CAMPUS_CALLS} before the campus view fails its own harness')
# and the anti-pattern, named and refused by arithmetic rather than by intent
assert WORST_CALLS < MAIN['pieces'], \
    'a draw call per piece is the export artefact this kit exists to avoid'
PIECES_PER_DRAW = MAIN['pieces'] / MAIN['draw_calls']
assert PIECES_PER_DRAW >= 50, \
    (f'{PIECES_PER_DRAW:.1f} pieces per draw call is not pooling; the '
     'measured reference block managed 1.0 and that is the thing being avoided')

assert MAIN['triangles'] <= KIT_TRI_CEILING, \
    (f'the kit adds {MAIN["triangles"]:,} triangles at {BUDGET_CAMPUS}; its '
     f'declared {TRI_SHARE:.0%} share of the harness headroom is '
     f'{KIT_TRI_CEILING:,}')
assert CAMPUS_TRIS + MAIN['triangles'] <= CAMPUS_TRIS * TRI_HEADROOM, \
    'the kit would take the campus view over the harness triangle ceiling'
assert MAIN['own_mesh_draw_calls'] == 0, \
    'an own-mesh piece would cost a draw call per instance and the budget does not count one'

# no own-mesh piece, and the reason is declared rather than incidental
OWN_MESH_POLICY = (
    'own-mesh is admitted by the schema and used by nothing. The only reason '
    'this page gives a piece its own mesh is that something raycasts it, and '
    'the page already has exactly one such mesh per hall - the envelope box '
    'carrying userData.slug, which buildings[] holds and the hover and click '
    'handlers read. Nothing in this kit is clickable, so nothing in this kit '
    'earns a mesh. A future piece that MOVES independently would earn one, '
    'and would have to say so here.')
assert not any(p['merges'] == 'own-mesh' for p in PIECES.values()), \
    ('own-mesh is declared and used: ' + repr(sorted(
        k for k, p in PIECES.items() if p['merges'] == 'own-mesh'))
     + ' - only a raycast target or a piece that moves earns its own mesh, '
       'and the budget above counts none')

# ---------------------------------------------------------- page contract ---
PAGE_CONTRACT = {
    'data': (
        'web/build_3d.py already assembles one DATA payload from the '
        'registries. This pack joins it as `kit`, read the same way `world`, '
        '`districts` and `wallCat` are. Ship the `pieces`, `placement`, '
        '`counts` and `budget` blocks; the `honesty` and `reference` blocks '
        'are for the reader of the registry and do not need to reach the '
        'browser.'),
    'pools': (
        'Kit pieces go through the SAME closure the hall decoration already '
        'uses: the `add(m2, w, h, d, x, y, z, rz)` inside `building()`, '
        'which pushes a transformed BoxGeometry into the district `pool` Map '
        'that `buildCampus()` hands it. `flushParts(pool, cg)` then merges '
        'one mesh per material per district exactly as it does today. Do not '
        'write a second merge helper and do not call mergeGeometries '
        'directly: flushParts is the only door.'),
    'cylinders': (
        'The recipes here name cylinders, and `add()` builds boxes only. '
        'Extend `add()` to take a geometry rather than six dimensions, or '
        'give it a sibling that does - either way the geometry still lands '
        'in the same `pool` Map keyed by the same material, so the district '
        'still flushes one mesh per material. A cylinder that bypasses the '
        'pool is a new draw call per piece, which is the whole failure this '
        'pack is arithmetic against.'),
    'instances': (
        'The two `instanced` families follow `flushBeacons()`: one '
        'THREE.InstancedMesh per campus, added to campusGroup, its matrices '
        'written once at build. They must NOT reuse `beaconInst`, '
        '`beaconAt` or `spinBeacons()` - those belong to the station '
        'beacons, which spin every frame, and a bollard that rotates is a '
        'bug the beacon code would hand you for free.'),
    'materials': (
        'Every `material` value here names something the page ALREADY holds: '
        'a `mat.*` singleton or a key of what `fabricOf(campusKey)` returns. '
        'Resolve them by name at build time. Do not construct a material '
        'from a colour in this registry, because this registry publishes no '
        'colours - the envelope, trim and roof colours are the world '
        'registry\'s and `fabricOf()` is the one place they are turned into '
        'materials.'),
    'roofline': (
        'A piece is admitted by roofline, and the roofline is the one '
        '`buildCampus()` already computes for the district: '
        "STYLE_OF[k] ?? D.world.fabric?.[campusKey]?.roof. Read that same "
        '`style` variable through to the kit. Do not add a second roofline '
        'table and do not re-derive it per hall: it is a district fact and '
        'the page already holds it.'),
    'facade': (
        'A piece is also admitted by facade pattern, which is '
        '`fabricOf(campusKey).spec.facade` - already carried on the fabric '
        'object as `spec`. Read it there rather than reaching back into '
        'D.world.fabric a second time.'),
    'geometry': (
        'The envelope this kit hangs on is `building()`\'s own: wid = 12, '
        'dep = Math.max(h.depth, 5), hgt = 6 + (h.depth % 3) * .7, door '
        'toward local -z. This pack reads all three out of the page source '
        'and its arithmetic fails if they change, so the page may change '
        'them - it just has to rebuild this registry afterwards.'),
    'never_duplicate': (
        'Do not add a second STYLE_OF, a second fabric material factory, a '
        'second merge helper, or a second raycast target. `buildings[]` stays '
        'one entry per hall and `ray.intersectObjects(buildings, false)` '
        'stays the hover and click path: a kit piece must never be hoverable, '
        'because a stoop that opens a hall page is a bug wearing a feature\'s '
        'clothes.'),
    'teardown': (
        '`disposeOf(campusGroup)` already frees everything a campus built. '
        'The merged kit geometry is per-district and freed with it. The two '
        'InstancedMeshes are freed the same way - but their materials are '
        '`mat.post` and `mat.slab`, page-wide singletons, and disposeOf() '
        'must not free those, exactly as it must not free `mat.post` today '
        'for the beacons.'),
    'not_the_page': (
        'This registry decides nothing about lighting, shadows, level of '
        'detail, culling or the quality rungs. Those are the page\'s and it '
        'already has them.'),
}

# ------------------------------------------------------------- honesty ------
HONESTY = {
    'status': (
        'SCHEMATIC: every piece here is the SHAPE of a thing, not a '
        'measurement of one. A downpipe is a cylinder and two brackets at a '
        'plausible size; a meter box is two boxes. No dimension was taken '
        'off a real component, no product was consulted, and no standard is '
        'referenced.'),
    'not_a_construction_detail': (
        'Nothing in this registry is a construction detail and nobody should '
        'build anything from it. There are no gauges, no fixing centres, no '
        'material specifications, no loads, no falls and no clearances. A '
        'size here is the size something reads as from across a campus '
        'green, chosen so a fifty-one-building campus looks built rather '
        'than diagrammed.'),
    'provenance': (
        'SCHEMATIC for the shapes and sizes; AUTHORED for the placement '
        'rates, which are somebody\'s judgement about how often a thing '
        'appears on a wall. MEASURED-ELSEWHERE for the nine reference '
        'figures in `reference`, and for the scene costs read out of '
        'web/eval_scene.mjs. AI-SYNTHESIZED is orbis/\'s word for generated '
        'video and is not this pack\'s to borrow.'),
    'no_assets': (
        'This kit loads no mesh, no texture, no model and no file. Every '
        'piece is built in the browser from THREE.BoxGeometry and '
        'THREE.CylinderGeometry, which is why a triangle budget can be '
        'checked against a recipe at all. Nothing was vendored from the '
        'reference measurement and nothing from it is reproduced here.'),
    'derived_not_typed': (
        'No hall is named in this pack. A piece is admitted by roofline and '
        'facade pattern, both of which are read from the registries that own '
        'them - web/build_3d.py\'s STYLE_OF for the district roofline, '
        'world/registry/world.json\'s fabric for the city\'s, and '
        'surfaces/registry/finishes.json for the pattern vocabulary those '
        'facades must already belong to.'),
    'measurement_limit': (
        'The reference figures were measured outside this repository on '
        'files it does not contain, and this build cannot re-run that '
        'inspection. They are quoted, not verified here. The scene costs are '
        'different: they come from web/eval_scene.mjs, which does run '
        'against this page, and they are read out of that file rather than '
        'restated.'),
    'budget_limit': (
        'The whole-campus arithmetic is a PREDICTION, not a measurement. It '
        'counts what the placement rules would place and what those pieces '
        'would cost if they merge as declared. Nothing here has been drawn '
        'yet. Only running web/eval_scene.mjs against a page that actually '
        'places them can say whether the prediction held - and the campus '
        'baseline it is measured against is one campus, treasure-island, so '
        'the other nine are unmeasured ground.'),
    'not_a_kit_of_parts': (
        'The word kit is the modelling sense: a small set of repeated pieces '
        'that assemble into variety. It is not a construction kit of parts, '
        'not a specification, not a schedule and not a takeoff.'),
}

# no URL anywhere in the payload: this pack fetches nothing and links nowhere
# ---------------------------------------------------------------- build ----
stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

budgets_tris = [p['tri_budget'] for p in PIECES.values()]
prim_boxes = sum(q['n'] for p in PIECES.values() for q in p['primitives']
                 if q['shape'] == 'box')
prim_cyls = sum(q['n'] for p in PIECES.values() for q in p['primitives']
                if q['shape'] == 'cylinder')

doc = {
    'pack': 'smartcitix-trade-craft-academy-kit',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'honesty': HONESTY,
    'reference': REFERENCE,
    'counts': {
        'families': len(FAMILIES),
        'pieces': len(PIECES),
        'pooled_pieces': sum(1 for p in PIECES.values() if p['merges'] == 'pooled'),
        'instanced_pieces': sum(1 for p in PIECES.values()
                                if p['merges'] == 'instanced'),
        'own_mesh_pieces': sum(1 for p in PIECES.values()
                               if p['merges'] == 'own-mesh'),
        'primitives': prim_boxes + prim_cyls,
        'boxes': prim_boxes,
        'cylinders': prim_cyls,
        'tri_budget_min': min(budgets_tris),
        'tri_budget_median': statistics.median(budgets_tris),
        'tri_budget_max': max(budgets_tris),
        'tri_budget_sum': sum(budgets_tris),
        'materials_used': len({p['material'] for p in PIECES.values()}),
        'materials_free': len({p['material'] for p in PIECES.values()
                               if p['material'] in ALREADY_POOLED}),
        'material_vocabulary': len(MATERIAL_VOCAB),
        'walls': len({r['wall'] for r in PLACEMENT.values()}),
        'runs': len({r['run'] for r in PLACEMENT.values()}),
        'rooflines': len(ROOFLINES),
        'facades': len(FACADES),
        'districts': len(DISTRICTS),
        'campuses_budgeted': len(BUDGETS),
        'halls_budgeted': sum(b['halls'] for b in BUDGETS.values()),
        'per_hall_count_rules': sum(1 for c in COUNTS.values()
                                    if c['mode'] == 'per_hall'),
        'per_metre_count_rules': sum(1 for c in COUNTS.values()
                                     if c['mode'] == 'per_run_m'),
        'campus_pieces': MAIN['pieces'],
        'campus_triangles': MAIN['triangles'],
        'campus_draw_calls': MAIN['draw_calls'],
        'campus_halls': MAIN['halls'],
        'pieces_per_draw_call': round(PIECES_PER_DRAW, 1),
    },
    'tri_formula': TRI_FORMULA,
    'vocabulary': {
        'families': FAMILIES,
        'walls': WALLS,
        'runs': {k: n for k, n in
                 [('frontage', 'the hall width, along the front'),
                  ('front_width', 'the hall width'),
                  ('back_width', 'the hall width, at the back'),
                  ('both_sides', 'twice the hall depth'),
                  ('roof_perimeter', 'twice the width plus twice the depth'),
                  ('eaves_run', 'twice the hall depth, along the two eaves')]},
        'run_of_wall': RUN_OF_WALL,
        'datums': DATUMS,
        'merges': ['pooled', 'instanced', 'own-mesh'],
        'rooflines': ROOFLINES,
        'facades': FACADES,
        'materials': MATERIAL_VOCAB,
        'already_pooled': ALREADY_POOLED,
        'own_mesh_policy': OWN_MESH_POLICY,
        'count_policy': COUNT_POLICY,
    },
    'envelope': {
        'source': 'web/build_3d.py building()',
        'width_m': HALL_W,
        'depth_floor_m': DEPTH_FLOOR,
        'height_formula': f'{HGT_BASE:g} + (depth % {HGT_MOD}) * {HGT_STEP:g}',
        'shortest_hall_m': MIN_HGT,
        'door_faces': 'local -z',
        'note': ('read out of the page, not restated: change the page and '
                 'this build fails rather than describing a building that '
                 'is no longer drawn'),
    },
    'page_findings': {
        'note': ('computed against web/build_3d.py while reading it, and '
                 'reported rather than enforced: these belong to that file '
                 'and this pack does not fail on them.'),
        'unopinionated_districts': _unopinionated,
        'roofline_fallback_reachable': bool(_unopinionated),
        'roofline_fallback': (
            'buildCampus() resolves a roofline as STYLE_OF[k] ?? '
            'fabric[campus].roof ?? \'flat\'. STYLE_OF names '
            f'{len(STYLE_OF)} districts and the union registry declares '
            f'{len(DISTRICTS)}, so '
            + ('the fallback is live for: ' + ', '.join(_unopinionated)
               if _unopinionated else
               'NEITHER fallback can fire today - both arms are unreachable '
               'and the comment beside them describes a case that does not '
               'occur')),
        'fabric_fallback_duplicates': _fb_twin,
        'fabric_fallback_present': _fb_spec is not None,
        'fabric_fallback': (
            ('FABRIC_FALLBACK in the page is a literal facade, trim and roof '
             'spec. '
             + ('It is byte-for-byte the fabric row of: ' + ', '.join(_fb_twin)
                + ' - a second copy of colours the world registry already '
                  'owns, which is the defect this bundle lints for. It could '
                  'read that row instead, or fail closed and say the registry '
                  'shipped no fabric.'
                if _fb_twin else
                'It matches no campus row, so it is at least not a duplicate.'))
            if _fb_spec is not None else
            'FIXED. The page carries no fabric fallback constant any more. '
            'fabricOf() reads world.fabric[campus] and throws when there is '
            'no row, and the build gates every campus on having one - so a '
            'campus whose fabric went missing now breaks the build instead '
            'of quietly wearing the flagship\'s livery and looking fine.'),
    },
    'pieces': PIECES,
    'placement': PLACEMENT,
    'counts_rules': COUNTS,
    'budget': {
        'measured_baseline': {
            'source': 'web/eval_scene.mjs',
            'views': SCENE_BASE,
            'call_headroom': CALL_HEADROOM,
            'tri_headroom': TRI_HEADROOM,
            'note': ('the campus view costs 273 draw calls and 15,850 '
                     'triangles: the whole fifty-one-hall campus is smaller '
                     'in triangles than one reference street block. This '
                     'page is draw-call bound with an unused triangle '
                     'budget, so the draw-call ceiling is the one that '
                     'governs and the triangle ceiling is a courtesy to the '
                     'pack that spends next.'),
        },
        'draw_call_ceiling': CALL_CEILING,
        'draw_call_ceiling_why': (
            f'web/eval_scene.mjs measured the campus view at {CAMPUS_CALLS} '
            f'draw calls and holds it to {CALL_HEADROOM:g}x that, so '
            f'{CALL_CEILING} is what is left for everything added after the '
            'measurement. It is read from that file, not typed here.'),
        'triangle_ceiling': KIT_TRI_CEILING,
        'triangle_headroom_total': TRI_CEILING,
        'triangle_share': TRI_SHARE,
        'triangle_ceiling_why': TRI_SHARE_WHY,
        'budgeted_campus': BUDGET_CAMPUS,
        'budgeted_campus_why': (
            'the campus the scene harness actually drives to, so the baseline '
            'the arithmetic is added to is a measurement of this campus and '
            'not of a campus nobody scored'),
        'campuses': BUDGETS,
        'worst_campus_draw_calls': WORST_CALLS,
        'result': {
            'campus': BUDGET_CAMPUS,
            'halls': MAIN['halls'],
            'pieces': MAIN['pieces'],
            'triangles': MAIN['triangles'],
            'draw_calls': MAIN['draw_calls'],
            'pieces_per_draw_call': round(PIECES_PER_DRAW, 1),
            'campus_calls_after': CAMPUS_CALLS + MAIN['draw_calls'],
            'campus_tris_after': CAMPUS_TRIS + MAIN['triangles'],
            'against_reference_block': (
                f'{MAIN["triangles"]:,} triangles is '
                f'{MAIN["triangles"] / REFERENCE["block_total_tris"]:.1f} times '
                'the measured reference block, spread over 51 buildings, for '
                f'{MAIN["draw_calls"]} draw calls against that block\'s 93'),
        },
    },
    'page_contract': PAGE_CONTRACT,
}

_payload = json.dumps(doc)
assert 'http://' not in _payload and 'https://' not in _payload, \
    'the kit names no URL: it loads nothing and links nowhere'
# AI-SYNTHESIZED is orbis/'s word for generated video. The only place it may
# appear in this payload is the one sentence that says so.
_ai = [k for k, v in HONESTY.items() if 'AI-SYNTHESIZED' in v]
assert _ai == ['provenance'] and _payload.count('AI-SYNTHESIZED') == 1, \
    ('AI-SYNTHESIZED is orbis/\'s word and describes nothing this pack '
     f'declares; it appears in {_ai} and {_payload.count("AI-SYNTHESIZED")} times')
for bad in ('Grove Street', 'GTA', 'Rockstar', 'San Andreas', 'Sketchfab'):
    assert bad.lower() not in _payload.lower(), \
        f'{bad!r} names somebody else\'s work; this kit is original'

# the counts are computed above and held against the same things here
assert doc['counts']['pieces'] == (doc['counts']['pooled_pieces']
                                   + doc['counts']['instanced_pieces']
                                   + doc['counts']['own_mesh_pieces'])
assert doc['counts']['primitives'] == doc['counts']['boxes'] + doc['counts']['cylinders']
assert doc['counts']['tri_budget_sum'] == sum(
    tri_cost(p['primitives'], k) for k, p in PIECES.items())

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'kit.json').write_text(json.dumps(doc, indent=1) + '\n')
print(f"kit: {doc['counts']['pieces']} pieces over "
      f"{doc['counts']['families']} families, "
      f"{doc['counts']['boxes']} boxes and {doc['counts']['cylinders']} "
      f"cylinders, median {doc['counts']['tri_budget_median']:g} triangles "
      f"(reference median {REFERENCE['block_median_tris']}); "
      f"at {BUDGET_CAMPUS} ({MAIN['halls']} halls): {MAIN['pieces']:,} pieces, "
      f"{MAIN['triangles']:,} triangles, {MAIN['draw_calls']} draw calls "
      f"({PIECES_PER_DRAW:.0f} pieces per call) - ceilings {CALL_CEILING} "
      f"calls and {KIT_TRI_CEILING:,} triangles, both read from "
      f"web/eval_scene.mjs (source stamp {stamp})")
