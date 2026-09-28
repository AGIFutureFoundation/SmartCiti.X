#!/usr/bin/env python3
"""The wilds: large exterior worlds to walk, each with trade work sites.

Every world here is AUTHORED. Its ground is seeded gradient noise shaped by
the biome parameters below and generated at runtime by wilds/core.mjs; no
height is read from any real place, and no world is a survey of one. A world
names a real region only as the general geography it EVOKES, and names the
campus in geo/registry/campuses_geo.json nearest in spirit - inspiration,
nothing more.

What this build DERIVES, and fails closed on:
  - every hall id resolves in pack/registry/halls.json (names copied by id);
  - every lesson id resolves in lessons/registry/lessons.json (titles copied
    by id), and a lesson is only tied to a site whose halls include the
    lesson's own hall - a site cannot borrow a lesson from a trade that is
    not working there;
  - every site, cache and trailhead lies inside the world, clear of the rim;
  - the trail network is the minimum spanning tree over the trailhead and
    the sites (straight legs, lengths in metres DERIVED here);
  - every off-trail cache and hidden hollow lies at least OFF_TRAIL_M from
    every trail leg, so "off-trail" is a measured fact, not a hint;
  - the inspiration campus id resolves in geo/registry/campuses_geo.json.

A quest, a cache, a badge is play. Nothing here enters a completion record.
"""
import hashlib
import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OFF_TRAIL_M = 120      # an off-trail cache sits at least this far from every trail leg
RIM_CLEAR_M = 300      # nothing authored stands in the rim band at the edge of the world


def load(rel):
    return json.load(open(ROOT / rel))


HALLS = {h['slug']: h for h in load('pack/registry/halls.json')['halls']}
LESSONS_DOC = load('lessons/registry/lessons.json')
LESSONS = LESSONS_DOC['lessons']
# LEARN writes one site walk per wilds site (lessons.json spread.site_walks:
# site id -> lesson id). Every site's walk is DERIVED from that map, never
# typed here, and a site without one stops the build.
if 'spread' not in LESSONS_DOC or 'site_walks' not in LESSONS_DOC['spread']:
    raise SystemExit('wilds/build.py: lessons/registry/lessons.json has no spread.site_walks')
SITE_WALKS = LESSONS_DOC['spread']['site_walks']
CAMPUSES = load('geo/registry/campuses_geo.json')['campuses']

PROVENANCE = {
    'terrain': 'AUTHORED',
    'sites': 'AUTHORED',
    'caches': 'AUTHORED',
    'trails': 'DERIVED',
    'hall_names': 'DERIVED',
    'lesson_titles': 'DERIVED',
    'site_walks': 'DERIVED',
    'summit_register': 'DERIVED',
}
HONESTY = {
    'landscape': ('Every world is an authored landscape generated from a seed. '
                  'It is not a survey, no height is a real elevation, and the '
                  'region named is inspiration for its general geography only.'),
    'sites': ('A work site is a schematic place to stand and think about a '
              'trade. It links to real halls and lessons in this bundle; it '
              'is not a real job site and shows no real crew.'),
    'play': ('Caches, side quests and badges are play. They never enter a '
             'completion record and never certify anything.'),
    'lessons': ('Lessons stay unverified general practice, exactly as the '
                'lessons pack states.'),
}

# ------------------------------------------------------------- authored --
# Coordinates are metres from the world's centre: x east, z south.
WORLDS = [
    {
        'id': 'mountain',
        'name': 'High Country',
        'evokes': 'the general geography of the Colorado Front Range: high ridges, a tree line, snow on the tops',
        'campus': 'denver',
        'seed': 81321,
        'extent_m': 12288,
        'chunk_m': 512,
        'sky': '#9CC3E4', 'fog': '#B9CFE0',
        'biome': {
            'model': 'ridged', 'relief_m': 1250, 'feature_m': 2600, 'octaves': 6,
            'water_level_m': 290, 'tree_line_m': 760, 'snow_line_m': 900,
            'max_tree_slope': 0.85, 'tree_density': 0.55, 'deciduous_share': 0.12,
            'rock_density': 0.35, 'stand_m': 900, 'clearing': 0.25,
            'rim_m': 500, 'rim_width_m': 500,
            'palette': {'low': '#5E7A3E', 'mid': '#3F5A31', 'rock': '#7A736A', 'snow': '#F2F5F7', 'shore': '#9C8F6A'},
        },
        'trailhead': {'x': 0, 'z': 1800, 'name': 'Pass trailhead', 'pad_m': 24},
        'sites': [
            {'id': 'm-adit-portal', 'kind': 'portal', 'x': -1900, 'z': 900, 'pad_m': 38,
             'title': 'Adit portal and ground support',
             'work': 'A mine adit driven into the hillside: ground support, ventilation and a portal that has to stay open.',
             'halls': ['miners', 'blasters', 'shoring'],
             'lessons': ['shoring-read-the-ground-again']},
            {'id': 'm-hv-corridor', 'kind': 'tower', 'x': 1500, 'z': -600, 'pad_m': 34,
             'title': 'High-voltage line corridor',
             'work': 'A transmission line crossing the valley on lattice towers; stringing, clearances and fault finding.',
             'halls': ['transmission', 'line-workers'],
             'lessons': ['line-workers-find-the-fault']},
            {'id': 'm-rockfall-netting', 'kind': 'netting', 'x': -700, 'z': -1500, 'pad_m': 30,
             'title': 'Rockfall netting on a road cut',
             'work': 'Mesh and anchors hung on a cut slope above the road; rope access and lifted panels.',
             'halls': ['high-angle', 'riggers', 'blasters'],
             'lessons': ['riggers-first-card']},
            {'id': 'm-snow-road', 'kind': 'grader', 'x': 2600, 'z': 1400, 'pad_m': 40,
             'title': 'Snow-road grading on the pass',
             'work': 'Graders and plough trucks keeping a mountain road open; machines checked before they climb.',
             'halls': ['operating-eng', 'teamsters', 'heavy-equip'],
             'lessons': ['heavy-equip-listen-to-the-dash', 'teamsters-check-the-truck-before-the-load']},
            {'id': 'm-wind-ridge', 'kind': 'turbine', 'x': -3000, 'z': -2600, 'pad_m': 42,
             'title': 'Ridge-top turbine pad',
             'work': 'A crane pad on a ridge for a wind turbine; the lift chart decides what goes up in the wind.',
             'halls': ['wind', 'crane-ops'],
             'lessons': ['crane-ops-read-the-chart']},
            {'id': 'm-survey-control', 'kind': 'survey', 'x': 3400, 'z': -3100, 'pad_m': 26,
             'title': 'Survey control on the high ground',
             'work': 'A control point and a drone landing square; everything below is laid out from here.',
             'halls': ['surveyors', 'survey-drone'],
             'lessons': ['surveyors-trust-the-control']},
        ],
        'caches': [
            {'id': 'm-cache-talus', 'kind': 'cache', 'x': -2350, 'z': -500, 'riddle': 'Below the portal, where the loose stone rests.'},
            {'id': 'm-cache-tarn', 'kind': 'cache', 'x': 3350, 'z': 250, 'riddle': 'East of the plough road, a stone that does not match its neighbours.'},
            {'id': 'm-hollow', 'kind': 'hollow', 'x': 400, 'z': -3300, 'hollow_m': 70, 'hollow_depth_m': 14, 'riddle': 'North of the towers the ground folds in on itself.'},
            {'id': 'm-summit-register', 'kind': 'summit', 'riddle': 'The highest ground in the High Country keeps a book.'},
        ],
    },
    {
        'id': 'forest',
        'name': 'Deep Timber',
        'evokes': 'the general geography of the Puget Sound lowlands: rolling timber, lakes and river flats',
        'campus': 'seattle',
        'seed': 44017,
        'extent_m': 10240,
        'chunk_m': 512,
        'sky': '#A8C4D2', 'fog': '#B7C9C9',
        'biome': {
            'model': 'rolling', 'relief_m': 420, 'feature_m': 1500, 'octaves': 5,
            'water_level_m': -45, 'tree_line_m': 5000, 'snow_line_m': 99999,
            'max_tree_slope': 1.1, 'tree_density': 0.92, 'deciduous_share': 0.3,
            'rock_density': 0.08, 'stand_m': 600, 'clearing': 0.12,
            'rim_m': 260, 'rim_width_m': 450,
            'palette': {'low': '#4F6B35', 'mid': '#2F4A2A', 'rock': '#6E6B5E', 'snow': '#F2F5F7', 'shore': '#8B7F5A'},
        },
        'trailhead': {'x': 0, 'z': 0, 'name': 'Ranger station trailhead', 'pad_m': 24},
        'sites': [
            {'id': 'f-line-clearance', 'kind': 'lineclear', 'x': 1700, 'z': 1100, 'pad_m': 30,
             'title': 'Utility line clearance',
             'work': 'A distribution line through the timber: the right-of-way cut back and the line walked for faults.',
             'halls': ['line-workers', 'grounds'],
             'lessons': ['line-workers-find-the-fault']},
            {'id': 'f-trail-bridge', 'kind': 'bridge', 'x': -1400, 'z': 1500, 'pad_m': 30,
             'title': 'Trail bridge crew',
             'work': 'A timber footbridge over a creek; carpenters framing, labourers packing material in.',
             'halls': ['carpenters', 'laborers', 'bridge-inspect'],
             'lessons': ['carpenters-return-it-the-same']},
            {'id': 'f-fuel-break', 'kind': 'fuelbreak', 'x': 2600, 'z': -1700, 'pad_m': 44,
             'title': 'Wildfire fuel break',
             'work': 'A strip thinned and cleared along a ridge; machines and hand crews working the same ground.',
             'halls': ['grounds', 'operating-eng', 'laborers'],
             'lessons': ['laborers-stand-where-the-cab-can-see']},
            {'id': 'f-timber-frame', 'kind': 'frame', 'x': -2200, 'z': -900, 'pad_m': 32,
             'title': 'Timber-frame shelter raising',
             'work': 'A post-and-beam shelter raised in a clearing; bents lifted and pinned.',
             'halls': ['carpenters', 'riggers'],
             'lessons': ['riggers-first-card']},
            {'id': 'f-water-intake', 'kind': 'intake', 'x': 600, 'z': 2900, 'pad_m': 28,
             'title': 'Lake intake and main',
             'work': 'A raw-water intake at the lake edge feeding a main down the valley.',
             'halls': ['water-distrib'],
             'lessons': ['water-distrib-safety-first-walk']},
            {'id': 'f-fire-lookout', 'kind': 'lookout', 'x': -600, 'z': -2900, 'pad_m': 26,
             'title': 'Fire lookout tower',
             'work': 'A steel lookout on the highest knoll; the frame erected and the access scaffold tagged.',
             'halls': ['steel-erectors', 'scaffold'],
             'lessons': ['steel-erectors-land-it-on-the-bolts', 'scaffold-read-the-tag']},
        ],
        'caches': [
            {'id': 'f-cache-nurse-log', 'kind': 'cache', 'x': -500, 'z': 1100, 'riddle': 'Between the ranger station and the creek, off the path, under old timber.'},
            {'id': 'f-cache-lakeshore', 'kind': 'cache', 'x': 2100, 'z': 2600, 'riddle': 'Where the line cut meets the far shore.'},
            {'id': 'f-hollow', 'kind': 'hollow', 'x': 1300, 'z': -3200, 'hollow_m': 60, 'hollow_depth_m': 10, 'riddle': 'A bowl the fuel crew never reached.'},
            {'id': 'f-summit-register', 'kind': 'summit', 'riddle': 'Deep Timber has one highest knoll; the book is there.'},
        ],
    },
    {
        'id': 'canyon',
        'name': 'Red Rock Canyon',
        'evokes': 'the general geography of western river canyons: stepped mesas and a river cut deep between them',
        'campus': 'denver',
        'seed': 70913,
        'extent_m': 8192,
        'chunk_m': 512,
        'sky': '#B6CDE0', 'fog': '#D9C7AE',
        'biome': {
            'model': 'canyon', 'relief_m': 420, 'feature_m': 1800, 'octaves': 5,
            'terrace_m': 36, 'river_amp_m': 700, 'river_wavelength_m': 900,
            'river_half_m': 60, 'canyon_half_m': 420,
            'water_level_m': 40, 'tree_line_m': 5000, 'snow_line_m': 99999,
            'max_tree_slope': 0.45, 'tree_density': 0.14, 'deciduous_share': 0.35,
            'rock_density': 0.55, 'stand_m': 400, 'clearing': 0.45,
            'rim_m': 220, 'rim_width_m': 400,
            'palette': {'low': '#A86B45', 'mid': '#8E5A3C', 'rock': '#B5794E', 'snow': '#E9D7B8', 'shore': '#C9B38A'},
        },
        'trailhead': {'x': 1300, 'z': 300, 'name': 'Mesa trailhead', 'pad_m': 24},
        'sites': [
            {'id': 'c-river-intake', 'kind': 'dam', 'x': -625, 'z': -1400, 'pad_m': 30,
             'title': 'Run-of-river intake and penstock',
             'work': 'A low weir and an intake feeding a penstock down to a small powerhouse; divers work the screens.',
             'halls': ['hydro', 'divers'],
             'lessons': ['hydro-inspection-first-walk', 'divers-layout-first-walk']},
            {'id': 'c-pipeline-crossing', 'kind': 'pipeline', 'x': 785, 'z': 1600, 'pad_m': 34,
             'title': 'Pipeline river crossing',
             'work': 'A pipeline crossing the canyon; tie-in digs on each side and a permit closed the way it opened.',
             'halls': ['pipeline'],
             'lessons': ['pipeline-close-the-permit-properly']},
            {'id': 'c-valve-vault', 'kind': 'vault', 'x': 1900, 'z': -2300, 'pad_m': 24,
             'title': 'Valve vault rescue drill',
             'work': 'A buried valve vault on the mesa used for a confined-space entry and retrieval drill.',
             'halls': ['confined-space', 'water-distrib', 'boilermakers'],
             'lessons': ['boilermakers-get-them-out']},
            {'id': 'c-mesa-solar', 'kind': 'solar', 'x': -2400, 'z': 2200, 'pad_m': 50,
             'title': 'Mesa-top solar array',
             'work': 'Racking and strings laid out across a flat mesa top.',
             'halls': ['solar', 'electricians'],
             'lessons': ['solar-documentation-first-walk', 'electricians-clip-in-first']},
            {'id': 'c-quarry-bench', 'kind': 'quarry', 'x': -2000, 'z': -1900, 'pad_m': 40,
             'title': 'Quarry bench and blast pattern',
             'work': 'A stepped quarry face with a drill pattern marked out; everybody knows where not to stand.',
             'halls': ['blasters', 'demolition'],
             'lessons': ['demolition-stand-back']},
        ],
        'caches': [
            {'id': 'c-cache-overhang', 'kind': 'cache', 'x': -1100, 'z': 400, 'riddle': 'Under the west rim, halfway between the solar mesa and the quarry.'},
            {'id': 'c-hollow', 'kind': 'hollow', 'x': 2700, 'z': 1200, 'hollow_m': 55, 'hollow_depth_m': 12, 'riddle': 'East of the trailhead, a pothole the rain made.'},
            {'id': 'c-summit-register', 'kind': 'summit', 'riddle': 'The highest step of the highest mesa.'},
        ],
    },
    {
        'id': 'delta',
        'name': 'Salt Marsh Delta',
        'evokes': 'the general geography of a Gulf river delta: low ridges of old shoreline, marsh and braided channels running to open water',
        'campus': 'new-orleans',
        'seed': 40427,
        'extent_m': 10240,
        'chunk_m': 512,
        'sky': '#C4D8E4', 'fog': '#D6DDD8',
        'biome': {
            'model': 'rolling', 'relief_m': 70, 'feature_m': 1500, 'octaves': 5,
            'water_level_m': 2, 'tree_line_m': 5000, 'snow_line_m': 99999,
            'max_tree_slope': 0.3, 'tree_density': 0.3, 'deciduous_share': 0.85,
            'rock_density': 0.05, 'stand_m': 260, 'clearing': 0.4,
            'rim_m': 90, 'rim_width_m': 500,
            'palette': {'low': '#6F8A4E', 'mid': '#5E7A45', 'rock': '#8C8467', 'snow': '#D9D6C4', 'shore': '#CDBF8F'},
        },
        'trailhead': {'x': -500, 'z': 1000, 'name': 'Levee trailhead', 'pad_m': 24},
        'sites': [
            {'id': 'd-levee-pump', 'kind': 'pumpstation', 'x': -2400, 'z': -2000, 'pad_m': 34,
             'title': 'Levee pump station',
             'work': 'A drainage pump station set into the levee; wastewater crews keep the pumps, screens and wet well working.',
             'halls': ['wastewater', 'electricians'],
             'lessons': ['wastewater-tools-first-walk', 'electricians-clip-in-first']},
            {'id': 'd-terminal-berth', 'kind': 'berth', 'x': 2800, 'z': 2400, 'pad_m': 50,
             'title': 'River terminal berth',
             'work': 'A barge berth with a crane working cargo; the lane is briefed before anything swings.',
             'halls': ['marine-terminal', 'port-crane'],
             'lessons': ['marine-terminal-brief-the-lane', 'port-crane-read-the-rope']},
            {'id': 'd-pile-trestle', 'kind': 'bridge', 'x': -3300, 'z': 3000, 'pad_m': 30,
             'title': 'Timber pile trestle over a bayou',
             'work': 'A pile-supported trestle across a channel: new piles driven from a rig on firm footing, old bents inspected.',
             'halls': ['piling', 'bridge-inspect'],
             'lessons': ['piling-stand-the-rig-on-something', 'bridge-inspect-inspection-first-walk']},
            {'id': 'd-outfall-dive', 'kind': 'intake', 'x': -600, 'z': 2900, 'pad_m': 28,
             'title': 'Outfall line and dive station',
             'work': 'An outfall pipe running into the channel; a dive team inspects it from a station on the bank.',
             'halls': ['divers', 'marine-pipe'],
             'lessons': ['divers-layout-first-walk', 'marine-pipe-know-when-to-come-out']},
            {'id': 'd-spill-boom', 'kind': 'boom', 'x': 900, 'z': -3200, 'pad_m': 30,
             'title': 'Spill boom staging',
             'work': 'Containment boom and a skimmer staged on the bank, ready to deploy across a channel mouth.',
             'halls': ['spill-response', 'hazmat'],
             'lessons': ['spill-response-tools-first-walk', 'hazmat-wash-and-decon']},
            {'id': 'd-wind-staging', 'kind': 'turbine', 'x': 2600, 'z': -2600, 'pad_m': 40,
             'title': 'Wind turbine staging yard',
             'work': 'A turbine erected on the ridge beside a laydown yard where blades and tower sections wait for the crane.',
             'halls': ['wind', 'crane-ops'],
             'lessons': ['wind-safety-first-walk', 'crane-ops-read-the-chart']},
        ],
        'caches': [
            {'id': 'd-cache-shell-midden', 'kind': 'cache', 'x': -2200, 'z': 400, 'riddle': 'On an old shell ridge, well off the trail, between the trailhead and the pump station.'},
            {'id': 'd-hollow', 'kind': 'hollow', 'x': -300, 'z': -1600, 'hollow_m': 50, 'hollow_depth_m': 3, 'riddle': 'A dry scour hole the last flood left, off the trail between the trailhead and the boom yard.'},
            {'id': 'd-summit-register', 'kind': 'summit', 'riddle': 'The delta has one highest ridge; the book is on its crown.'},
        ],
    },
]

REQUIRED_WORLD = ('id', 'name', 'evokes', 'campus', 'seed', 'extent_m', 'chunk_m', 'sky', 'fog',
                  'biome', 'trailhead', 'sites', 'caches')
REQUIRED_BIOME = ('model', 'relief_m', 'feature_m', 'octaves', 'water_level_m', 'tree_line_m',
                  'snow_line_m', 'max_tree_slope', 'tree_density', 'deciduous_share',
                  'rock_density', 'stand_m', 'clearing', 'rim_m', 'rim_width_m', 'palette')
MODEL_FIELDS = {'ridged': (), 'rolling': (),
                'canyon': ('terrace_m', 'river_amp_m', 'river_wavelength_m', 'river_half_m', 'canyon_half_m')}
REQUIRED_SITE = ('id', 'kind', 'x', 'z', 'pad_m', 'title', 'work', 'halls', 'lessons')
CACHE_FIELDS = {'cache': ('id', 'kind', 'x', 'z', 'riddle'),
                'hollow': ('id', 'kind', 'x', 'z', 'hollow_m', 'hollow_depth_m', 'riddle'),
                'summit': ('id', 'kind', 'riddle')}


def die(msg):
    raise SystemExit(f'wilds/build.py: {msg}')


def need(obj, fields, where):
    for f in fields:
        if f not in obj:
            die(f'{where} lacks required field {f!r}')


def seg_dist(p, a, b):
    ax, az, bx, bz, px, pz = a[0], a[1], b[0], b[1], p[0], p[1]
    dx, dz = bx - ax, bz - az
    L2 = dx * dx + dz * dz
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (pz - az) * dz) / L2))
    return math.hypot(px - (ax + t * dx), pz - (az + t * dz))


def mst(nodes):
    """Prim's tree over named points; ties broken by id so it is stable."""
    ids = [n['id'] for n in nodes]
    pos = {n['id']: (n['x'], n['z']) for n in nodes}
    inside, legs = {ids[0]}, []
    while len(inside) < len(ids):
        best = None
        for a in sorted(inside):
            for b in ids:
                if b in inside:
                    continue
                d = math.dist(pos[a], pos[b])
                if best is None or (d, a, b) < best:
                    best = (d, a, b)
        d, a, b = best
        inside.add(b)
        legs.append({'from': a, 'to': b, 'length_m': round(d)})
    return legs


def build_world(w):
    need(w, ('id',), 'a world')
    wid = w['id']
    need(w, REQUIRED_WORLD, f'world {wid}')
    need(w['biome'], REQUIRED_BIOME + MODEL_FIELDS[w['biome']['model']], f'world {wid} biome')
    if w['campus'] not in CAMPUSES:
        die(f'world {wid}: campus {w["campus"]!r} is not in geo/registry/campuses_geo.json')
    half = w['extent_m'] / 2
    lim = half - w['biome']['rim_width_m'] - RIM_CLEAR_M

    def inside(obj, where):
        if not (abs(obj['x']) <= lim and abs(obj['z']) <= lim):
            die(f'{where} at ({obj["x"]}, {obj["z"]}) is outside the walkable extent (|x|,|z| <= {lim})')

    th = dict(w['trailhead'])
    need(th, ('x', 'z', 'name', 'pad_m'), f'world {wid} trailhead')
    inside(th, f'world {wid} trailhead')
    sites = []
    seen = set()
    for i, s in enumerate(w['sites']):
        need(s, REQUIRED_SITE, f'world {wid} sites[{i}]')
        if s['id'] in seen:
            die(f'world {wid}: site id {s["id"]} twice')
        seen.add(s['id'])
        inside(s, f'site {s["id"]}')
        if not s['halls']:
            die(f'site {s["id"]} names no hall')
        halls = []
        for h in s['halls']:
            if h not in HALLS:
                die(f'site {s["id"]}: hall {h!r} is not in pack/registry/halls.json')
            halls.append({'id': h, 'name': HALLS[h]['name']})
        if s['id'] not in SITE_WALKS:
            die(f'site {s["id"]} has no walk in lessons/registry/lessons.json spread.site_walks')
        walk = SITE_WALKS[s['id']]
        if walk in s['lessons']:
            die(f'site {s["id"]}: walk {walk} is typed in its lessons; it is DERIVED from spread.site_walks')
        lessons = []
        for lid in s['lessons'] + [walk]:
            if lid not in LESSONS:
                die(f'site {s["id"]}: lesson {lid!r} is not in lessons/registry/lessons.json')
            L = LESSONS[lid]
            if L['hall'] not in s['halls']:
                die(f'site {s["id"]}: lesson {lid} belongs to hall {L["hall"]}, which does not work at this site')
            lessons.append({'id': lid, 'title': L['title'], 'hall': L['hall']})
        sites.append({**{k: s[k] for k in ('id', 'kind', 'x', 'z', 'pad_m', 'title', 'work')},
                      'halls': halls, 'lessons': lessons, 'provenance': 'AUTHORED'})
    nodes = [{'id': 'trailhead', 'x': th['x'], 'z': th['z']}] + [{'id': s['id'], 'x': s['x'], 'z': s['z']} for s in sites]
    legs = mst(nodes)
    pos = {n['id']: (n['x'], n['z']) for n in nodes}
    caches = []
    for i, c in enumerate(w['caches']):
        if 'kind' not in c or c['kind'] not in CACHE_FIELDS:
            die(f'world {wid} caches[{i}] has no known kind')
        need(c, CACHE_FIELDS[c['kind']], f'world {wid} caches[{i}]')
        if c['id'] in seen:
            die(f'world {wid}: cache id {c["id"]} reuses an id')
        seen.add(c['id'])
        out = {k: c[k] for k in CACHE_FIELDS[c['kind']]}
        if c['kind'] == 'summit':
            out['position'] = 'DERIVED at runtime: the highest ground wildsTerrain(world).summit() finds from the seed'
            out['provenance'] = 'DERIVED'
        else:
            inside(c, f'cache {c["id"]}')
            d = min(seg_dist((c['x'], c['z']), pos[l['from']], pos[l['to']]) for l in legs)
            if d < OFF_TRAIL_M:
                die(f'cache {c["id"]} is {d:.0f} m from a trail leg; off-trail means at least {OFF_TRAIL_M} m')
            out['off_trail_m'] = round(d)
            out['provenance'] = 'AUTHORED'
        caches.append(out)
    kinds = {c['kind'] for c in caches}
    for k in ('cache', 'hollow', 'summit'):
        if k not in kinds:
            die(f'world {wid} has no {k} treasure')
    area_km2 = round((w['extent_m'] / 1000) ** 2, 1)
    return {
        'id': wid, 'name': w['name'],
        'inspiration': {'evokes': w['evokes'], 'campus': w['campus'],
                        'campus_city': CAMPUSES[w['campus']]['city'],
                        'standing': 'inspiration only; the terrain is AUTHORED, not real elevation'},
        'seed': w['seed'], 'extent_m': w['extent_m'], 'chunk_m': w['chunk_m'],
        'area_km2': area_km2, 'chunks_across': w['extent_m'] // w['chunk_m'],
        'sky': w['sky'], 'fog': w['fog'], 'biome': w['biome'],
        'trailhead': th, 'sites': sites, 'trails': legs,
        'trail_length_m': sum(l['length_m'] for l in legs),
        'caches': caches, 'provenance': 'AUTHORED',
    }


def main():
    worlds = [build_world(w) for w in WORLDS]
    site_ids = {s['id'] for w in worlds for s in w['sites']}
    stray = sorted(set(SITE_WALKS) - site_ids)
    if stray:
        die(f'lessons spread.site_walks names sites that are not in the wilds: {stray}')
    ids = [w['id'] for w in worlds]
    for must in ('mountain', 'forest'):
        if must not in ids:
            die(f'world {must} is required')
    core = (HERE / 'core.mjs').read_bytes()
    doc = {
        'pack': 'wilds',
        'product': 'SmartCiti.X : Trade Craft Academy',
        'source_stamp': hashlib.sha256((HERE / 'build.py').read_bytes()).hexdigest()[:16],
        'core_stamp': hashlib.sha256(core).hexdigest()[:16],
        'provenance': PROVENANCE,
        'honesty': HONESTY,
        'off_trail_m': OFF_TRAIL_M,
        'counts': {
            'worlds': len(worlds),
            'sites': sum(len(w['sites']) for w in worlds),
            'caches': sum(len(w['caches']) for w in worlds),
            'halls_linked': len({h['id'] for w in worlds for s in w['sites'] for h in s['halls']}),
            'lessons_linked': len({l['id'] for w in worlds for s in w['sites'] for l in s['lessons']}),
            'area_km2': round(sum(w['area_km2'] for w in worlds), 1),
        },
        'worlds': worlds,
    }
    out = HERE / 'registry' / 'wilds.json'
    out.parent.mkdir(exist_ok=True)
    text = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
    if '--check' in sys.argv:
        if not out.exists() or out.read_text() != text:
            print('STALE: wilds/registry/wilds.json\n       run: python3 wilds/build.py')
            sys.exit(1)
        print('wilds: registry current')
        return
    out.write_text(text)
    c = doc['counts']
    print(f'wilds: {c["worlds"]} worlds | {c["sites"]} sites | {c["caches"]} caches | '
          f'{c["area_km2"]} km2 | stamp {doc["source_stamp"]}')


main()
