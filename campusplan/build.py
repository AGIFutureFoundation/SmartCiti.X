#!/usr/bin/env python3
"""Campus site plans: every union hall on its OWN building lot.

Until now the 3D campus drew each district as one strip of 12 m schematic
sheds. This pack authors, for all ten campuses, a site plan in which every
hall of the union registry stands on its own lot at the SAME size as the
walkable hall interior - so the outside of a hall and its inside agree:

  - footprint: the hall's own envelope (web/interiors.py plan_for ->
    envelope w x d grid units x unit_m), imported, never restated;
  - height: the clear height web/build_3d.py derives from the trade's own
    fixtures (clear_height, CLEAR_BASE_M, HEADROOM_M), read out of the
    builder's source with ast and executed - never restated;
  - roof style: the builder's STYLE_OF table, read out of its source;
  - everything else (setbacks, streets, walkways, parking, yards, gate,
    commons, where the district blocks sit) is AUTHORED from
    campusplan/authored/rules.json and legended AUTHORED.

It also records where each campus sits in the larger maps: the geo
registry's coordinate with the registry's OWN provenance tag (copied, never
upgraded), the 3D page's city-layer frame, and for New Orleans the Orleans
Parish local frame of parishes/registry/parishes.json.

Fail closed: a missing field raises; no defaults on registry data.
Deterministic: no clock, no randomness; the same inputs give the same bytes.
"""
import ast
import hashlib
import json
import math
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'web'))
from interiors import plan_for, FIXTURES as ROOM_FIXTURES  # noqa: E402  (read only)

INPUTS = ['web/interiors.py', 'web/build_3d.py', 'pack/registry/halls.json',
          'unions/registry/campuses.json', 'unions/registry/districts.json',
          'geo/registry/campuses_geo.json', 'parishes/registry/parishes.json',
          'campusplan/authored/rules.json', 'campusplan/build.py']
OUT = HERE / 'registry' / 'campusplan.json'
EPS = 1e-6


def load(rel):
    return json.load(open(ROOT / rel))


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


halls_json = load('pack/registry/halls.json')['halls']
hall_by = {h['slug']: h for h in halls_json}
campuses_reg = load('unions/registry/campuses.json')['campuses']
districts_reg = load('unions/registry/districts.json')['districts']
geo = load('geo/registry/campuses_geo.json')
parishes = load('parishes/registry/parishes.json')
rules = load('campusplan/authored/rules.json')

# ------------------------------------------------ the builder's own numbers --
B3D_SRC = (ROOT / 'web/build_3d.py').read_text()
_ns = {'ROOM_FIXTURES': ROOM_FIXTURES}
# only the builder text read here is stamped, so an unrelated edit to the
# 800 KB builder does not stale this registry (the test's fresh-build check
# re-reads these same parts)
READ_PARTS = []
_want = {'CLEAR_BASE_M', 'HEADROOM_M', 'clear_height'}
for node in ast.parse(B3D_SRC).body:
    name = None
    if isinstance(node, ast.Assign) and len(node.targets) == 1 \
            and isinstance(node.targets[0], ast.Name):
        name = node.targets[0].id
    elif isinstance(node, ast.FunctionDef):
        name = node.name
    if name in _want:
        exec(compile(ast.Module([node], []), 'web/build_3d.py', 'exec'), _ns)
        READ_PARTS.append(ast.get_source_segment(B3D_SRC, node))
        _want.discard(name)
if _want:
    raise SystemExit(f'web/build_3d.py no longer defines {sorted(_want)}; '
                     'campusplan reads the clear height from it')
clear_height = _ns['clear_height']


def js_const(pattern, what):
    m = re.search(pattern, B3D_SRC, re.S)
    if not m:
        raise SystemExit(f'web/build_3d.py: cannot read {what} ({pattern})')
    READ_PARTS.append(m.group(0))
    return m


STYLE_OF = dict(re.findall(r"(\w+):\s*'(\w+)'", js_const(
    r'const STYLE_OF = \{(.*?)\};', 'STYLE_OF').group(1)))
CITY_S = float(js_const(r'const CITY_S = ([\d.]+);', 'CITY_S').group(1))
CAMPUS_R = js_const(r'const R = dk\.length === 2 \? (\d+) : (\d+);',
                    'campus R')
CAMPUS_R2, CAMPUS_R3 = float(CAMPUS_R.group(1)), float(CAMPUS_R.group(2))
WALK_PAD = float(js_const(r'walkLim = cityPois \? \(cityLog \? \d+ : \d+\) : campusR \+ (\d+);',
                          'walkLim pad').group(1))
KM_E = float(js_const(r"\* ([\d.]+) \* math\.cos\(math\.radians\(", 'km per degree east').group(1))
KM_N = float(js_const(r"\* ([\d.]+), 2\)", 'km per degree north').group(1))
_lg = js_const(r'const r = (\d+) \+ (\d+) \* Math\.log10\(1 \+ p\.km\);', 'city log radius')
LOG_R0, LOG_K = float(_lg.group(1)), float(_lg.group(2))
YR_MAX = float(js_const(r'const YR = Math\.min\((\d+), Math\.max',
                        'sims yard radius').group(1))

# --------------------------------------------------------- per-hall facts --
PLANS = {h['slug']: plan_for(h, {'live': 0, 'calibrating': 0,
                                 'schema_ok': 0, 'draft': 0})
         for h in halls_json}
# the envelope depends on the trade's fixtures only; the commissioning
# census the builder passes changes nothing read here


def hall_facts(slug):
    p = PLANS[slug]
    env = p['envelope']
    fx = {r['strand']: r['fixtures'] for r in p['rooms'] if r['fixtures']}
    words = ' | '.join([f for lst in fx.values() for f in lst]
                       + [hall_by[slug]['name'], hall_by[slug]['focus']]).lower()
    yard_word = None
    for w in rules['yard_words']:
        if w.lower() in words:
            yard_word = w
            break
    return {'w_m': env['w'] * env['unit_m'], 'd_m': env['d'] * env['unit_m'],
            'env': env, 'clear': clear_height(fx), 'yard_word': yard_word,
            'text': words}


FACTS = {s: hall_facts(s) for s in hall_by}
for w in rules['yard_words']:
    if not any(w.lower() in f['text'] for f in FACTS.values()):
        raise SystemExit(f'rules.json yard word {w!r} matches no hall')

# ----------------------------------------------------------------- rects --
R3 = lambda v: round(v + 0.0, 3)  # noqa: E731


def rect(x0, z0, x1, z1, **kw):
    xa, xb = sorted((x0, x1))
    za, zb = sorted((z0, z1))
    r = {'x': R3((xa + xb) / 2), 'z': R3((za + zb) / 2),
         'w': R3(xb - xa), 'd': R3(zb - za)}
    r.update(kw)
    return r


def bounds(r):
    return (r['x'] - r['w'] / 2, r['z'] - r['d'] / 2,
            r['x'] + r['w'] / 2, r['z'] + r['d'] / 2)


def overlap(a, b):
    ax0, az0, ax1, az1 = bounds(a)
    bx0, bz0, bx1, bz1 = bounds(b)
    return min(ax1, bx1) - max(ax0, bx0) > EPS and min(az1, bz1) - max(az0, bz0) > EPS


def touch(a, b):
    ax0, az0, ax1, az1 = bounds(a)
    bx0, bz0, bx1, bz1 = bounds(b)
    ox = min(ax1, bx1) - max(ax0, bx0)
    oz = min(az1, bz1) - max(az0, bz0)
    return ox >= -EPS and oz >= -EPS and max(ox, oz) > EPS


def inside(inner, outer):
    ix0, iz0, ix1, iz1 = bounds(inner)
    ox0, oz0, ox1, oz1 = bounds(outer)
    return ix0 >= ox0 - EPS and iz0 >= oz0 - EPS and ix1 <= ox1 + EPS and iz1 <= oz1 + EPS


# slot transforms: block-local (u along the frontage, v outward from the
# commons, v = 0 at the block's inner edge) -> campus (x east, z south)
SLOT = {
    'N': (lambda u, v, G: (u, -(G + v)), {'+u': 'E', '-u': 'W', '-v': 'S'}),
    'S': (lambda u, v, G: (-u, G + v), {'+u': 'W', '-u': 'E', '-v': 'N'}),
    'E': (lambda u, v, G: (G + v, u), {'+u': 'S', '-u': 'N', '-v': 'W'}),
    'W': (lambda u, v, G: (-(G + v), -u), {'+u': 'N', '-u': 'S', '-v': 'E'}),
}
ROT_Y = {'N': 0.0, 'S': math.pi, 'E': -math.pi / 2, 'W': math.pi / 2}


def stalls(w, d):
    st = rules['stall']
    module = 2 * st['d_m'] + st['aisle_m']
    return int(w // st['w_m']) * 2 * int(d // module)


def plan_block(key):
    """A district block in block-local metres: double-loaded spines off one
    collector street, lots flush to the spine walkways, doors to the spine."""
    sb = rules['setbacks_m']
    wk, sp, cw = rules['walkway_w_m'], rules['spine_w_m'], rules['collector_w_m']
    yd = rules['yard']
    lots = []
    for slug in districts_reg[key]['halls']:
        f = FACTS[slug]
        depth = sb['front'] + f['d_m'] + sb['rear']
        if f['yard_word']:
            depth += yd['gap_m'] + yd['d_m']
        lots.append({'slug': slug, 'front': f['w_m'] + 2 * sb['side'],
                     'depth': depth})
    n = len(lots)
    best = None
    for k in range(1, 7):
        m = math.ceil(n / (2 * k))
        if 2 * k * m - n >= 2 * m:        # a whole empty side: too many spines
            continue
        sides = [lots[i * m:(i + 1) * m] for i in range(2 * k)]
        width = sum(max([l['depth'] for l in s], default=0) for s in sides) \
            + k * (sp + 2 * wk)
        depth = cw + max(sum(l['front'] for l in s) for s in sides)
        score = max(width, depth)
        if best is None or score < best[0] - EPS:
            best = (score, k, m, sides, width, depth)
    _, k, m, sides, width, depth = best
    out = {'k': k, 'lots': [], 'streets': [], 'walkways': [],
           'width': width, 'depth': depth}
    u = -width / 2
    out['streets'].append(('collector', rect(-width / 2, 0, width / 2, cw)))
    for j in range(k):
        left, right = sides[2 * j], sides[2 * j + 1]
        dl = max([l['depth'] for l in left], default=0)
        dr = max([l['depth'] for l in right], default=0)
        walk_l = u + dl                  # the left walkway's outer (lot) edge
        spine_u0 = walk_l + wk
        spine_u1 = spine_u0 + sp
        walk_r = spine_u1 + wk           # the right walkway's outer edge
        run = max(sum(l['front'] for l in left), sum(l['front'] for l in right))
        out['streets'].append((f'spine{j}', rect(spine_u0, cw, spine_u1, cw + run)))
        out['walkways'].append((f'spine{j}-a', rect(walk_l, cw, spine_u0, cw + run)))
        out['walkways'].append((f'spine{j}-b', rect(spine_u1, cw, walk_r, cw + run)))
        for side, lst, edge, sgn in (('a', left, walk_l, -1), ('b', right, walk_r, 1)):
            v = cw
            for l in lst:
                f = FACTS[l['slug']]
                lu0, lu1 = sorted((edge, edge + sgn * l['depth']))
                b0 = edge + sgn * sb['front']
                b1 = b0 + sgn * f['d_m']
                yard = None
                if f['yard_word']:
                    y0 = b1 + sgn * yd['gap_m']
                    yard = rect(y0, v + sb['side'], y0 + sgn * yd['d_m'],
                                v + sb['side'] + f['w_m'])
                out['lots'].append({
                    'slug': l['slug'], 'walk': f'spine{j}-{side}',
                    'street': f'spine{j}',
                    'lot': rect(lu0, v, lu1, v + l['front']),
                    'bld': rect(b0, v + sb['side'], b1, v + sb['side'] + f['w_m']),
                    'door': (b0, v + l['front'] / 2),
                    'faces': '+u' if sgn < 0 else '-u',   # toward the spine
                    'yard': yard})
                v += l['front']
        u = walk_r + dr
    return out


def to_campus(r, slot, G, **kw):
    f = SLOT[slot][0]
    x0, z0 = f(r['x'] - r['w'] / 2, r['z'] - r['d'] / 2, G)
    x1, z1 = f(r['x'] + r['w'] / 2, r['z'] + r['d'] / 2, G)
    return rect(x0, z0, x1, z1, **kw)


def ltp(lat, lng, lat0, lng0, R):
    """parishes registry frames.ltp_formula, as the registry states it."""
    return (R * math.cos(math.radians(lat0)) * math.radians(lng - lng0),
            R * math.radians(lat - lat0))


def point_in_rings(px, py, polys):
    hit = False
    for poly in polys:
        for ring in poly:
            for i in range(len(ring)):
                (x1, y1), (x2, y2) = ring[i - 1], ring[i]
                if (y1 > py) != (y2 > py) and \
                        px < (x2 - x1) * (py - y1) / (y2 - y1) + x1:
                    hit = not hit
    return hit


def placement(key):
    g = geo['campuses'][key]
    city = geo['city'][key]
    out = {
        'geo': {'lat': g['lat'], 'lng': g['lng'], 'provenance': g['provenance'],
                'source': g['source'],
                'prov': 'copied verbatim from geo/registry/campuses_geo.json '
                        f'campuses.{key}; the tag is the registry\'s own'},
        'city_layer': {
            'frame': 'the 3D page city layer (web/build_3d.py cityPos): origin = '
                     'this campus point, x = east, z = -north; linear at '
                     'units_per_km, or log-radial when any anchor is past 15 km',
            'x': 0, 'z': 0, 'rot_y': 0,
            'units_per_km': CITY_S,
            'log_radial': any(a['km'] > 15 for a in geo['anchors'][key]),
            'city_center': city['center'],
            'prov': 'DERIVED - web/build_3d.py CITY_S and cityPos, read at build '
                    'time; rot_y 0 is AUTHORED (north-up: no heading is recorded)'},
        'parish': None,
    }
    # where the page's city layer would draw each anchor (cityPos), in the
    # same scene units as this plan - and which fall inside the site
    lg = out['city_layer']['log_radial']
    inside_site = []
    for a in geo['anchors'][key]:
        e = (a['lng'] - g['lng']) * KM_E * math.cos(math.radians(g['lat']))
        n = (a['lat'] - g['lat']) * KM_N
        if lg:
            km = math.hypot(e, n) or .001
            r = LOG_R0 + LOG_K * math.log10(1 + a['km'])
            x, z = e / km * r, -n / km * r
        else:
            x, z = e * CITY_S, -n * CITY_S
        inside_site.append({'name': a['name'], 'x': R3(x), 'z': R3(z)})
    out['city_layer']['anchors'] = inside_site
    if key == 'new-orleans':
        fr = parishes['frames']
        R = fr['R_m']
        orl = parishes['parishes']['22071']
        o = orl['frame']['origin']
        wo = fr['world']['origin']
        le, ln = ltp(g['lat'], g['lng'], o['lat'], o['lng'], R)
        we, wn = ltp(g['lat'], g['lng'], wo['lat'], wo['lng'], R)
        out['parish'] = {
            'fips': orl['fips'], 'name': orl['full_name'],
            'frame': 'parish-local (parishes/registry/parishes.json '
                     'parishes.22071.frame.origin, frames.ltp_formula)',
            'origin': {'lat': o['lat'], 'lng': o['lng']},
            'local_m': [R3(le), R3(ln)],
            'scene': {'x': R3(le), 'z': R3(-ln)},
            'world_m': [R3(we), R3(wn)],
            'world_scene': {'x': R3(we), 'z': R3(-wn)},
            'rot_y': 0,
            'inside_outline': point_in_rings(g['lng'], g['lat'],
                                             orl['outline']['polygons']),
            'prov': 'DERIVED - the geo registry point through the parishes '
                    'registry ltp_formula (R_m ' + str(R) + '); rot_y 0 AUTHORED '
                    '(north-up: no heading recorded); scene x = east, z = -north'}
    return out


def plan_campus(key):
    camp = campuses_reg[key]
    dks = camp['districts']
    slots = rules['slots'][str(len(dks))]
    C = rules['commons_side_m']
    RW = rules['ring_street_w_m']
    H = C / 2 + RW
    wk = rules['walkway_w_m']
    AW = rules['avenue_w_m']
    blocks = {k: plan_block(k) for k in dks}
    dp = rules['district_parking']
    # the south strip (avenue, its walks, the sims yard and main parking)
    # must clear an east/west block, and every block must clear its
    # neighbours: one inner distance G for all slots
    south_half = AW / 2 + wk + max(2 * YR_MAX, rules['main_parking']['w_m'])
    G = max([H + dp['d_m'] + rules['block_gap_m'],
             south_half + rules['block_gap_m']]
            + [b['width'] / 2 + rules['block_gap_m'] for b in blocks.values()])

    streets, walkways, parking, lots, dist_out = [], [], [], [], []
    commons = rect(-C / 2, -C / 2, C / 2, C / 2, id='commons',
                   holds='the chapter hall pavilion the builder already '
                         'places at the origin (buildChapterHall)')
    for sid, r in (('ring-n', rect(-H, -H, H, -C / 2)), ('ring-s', rect(-H, C / 2, H, H)),
                   ('ring-e', rect(C / 2, -H, H, H)), ('ring-w', rect(-H, -H, -C / 2, H))):
        streets.append(dict(r, id=sid, kind='ring'))

    for di, k in enumerate(dks):
        slot = slots[di]
        b = blocks[k]
        cwid = rules['connector_w_m']
        conn = to_campus(rect(-cwid / 2, -(G - H), cwid / 2, 0), slot, G)
        streets.append(dict(conn, id=f'{k}-connector', kind='connector'))
        park = to_campus(rect(cwid / 2, -dp['d_m'], cwid / 2 + dp['w_m'], 0), slot, G)
        parking.append(dict(park, id=f'{k}-parking', district=k,
                            stalls=stalls(dp['w_m'], dp['d_m'])))
        for sid, r in b['streets']:
            streets.append(dict(to_campus(r, slot, G), id=f'{k}-{sid}',
                                kind='collector' if sid == 'collector' else 'spine'))
        for wid, r in b['walkways']:
            walkways.append(dict(to_campus(r, slot, G), id=f'{k}-{wid}'))
        block_r = to_campus(rect(-b['width'] / 2, 0, b['width'] / 2, b['depth']), slot, G)
        dist_out.append({'key': k, 'slot': slot, 'spines': b['k'],
                         'block': block_r, 'faces_commons': SLOT[slot][1]['-v'],
                         'prov': 'AUTHORED - campusplan/authored/rules.json slots; '
                                 'district key and order from unions/registry'})
        for L in b['lots']:
            f = FACTS[L['slug']]
            facing = SLOT[slot][1][L['faces']]
            bld = to_campus(L['bld'], slot, G)
            dx, dz = SLOT[slot][0](L['door'][0], L['door'][1], G)
            lot = to_campus(L['lot'], slot, G)
            lots.append({
                'id': 'lot:' + L['slug'], 'hall': L['slug'], 'district': k,
                'x': lot['x'], 'z': lot['z'], 'w': lot['w'], 'd': lot['d'],
                'setbacks': rules['setbacks_m'],
                'building': {
                    'x': bld['x'], 'z': bld['z'],
                    'w_m': f['w_m'], 'd_m': f['d_m'],
                    'height_m': f['clear'],
                    'rot_y': ROT_Y[facing], 'facing': facing,
                    'aabb': {kk: bld[kk] for kk in ('x', 'z', 'w', 'd')},
                    'door': {'x': R3(dx), 'z': R3(dz)}},
                'envelope': f['env'],
                'clear_height_m': f['clear'],
                'roof_style': STYLE_OF[k],
                'yard': None if not L['yard'] else dict(
                    to_campus(L['yard'], slot, G), kind='outdoor training yard',
                    because=f['yard_word']),
                'street': f"{k}-{L['street']}", 'walkway': f"{k}-{L['walk']}",
                'prov': {
                    'footprint': 'DERIVED - web/interiors.py plan_for envelope '
                                 '(w, d grid units x unit_m), imported',
                    'height': 'DERIVED - web/build_3d.py clear_height() over the '
                              "hall's own fixtures, read from the builder source; "
                              'eaves clear height, the slab is the builder\'s own',
                    'roof_style': 'DERIVED - web/build_3d.py STYLE_OF',
                    'position': 'AUTHORED - campusplan/authored/rules.json',
                    'setbacks': 'AUTHORED - campusplan/authored/rules.json',
                    'yard': 'AUTHORED - rules.json yard_words matched against '
                            'DERIVED fixtures / registry name and focus'}})

    # the south: avenue from the ring to the gate, the reserved sims yard
    # parcel and the main parking both sides of it
    sy = 2 * YR_MAX
    gap = rules['sims_yard_gap_m']
    mp = rules['main_parking']
    extent_s = max([bounds(r)[3] for r in streets + walkways + parking]
                   + [bounds(l)[3] for l in lots])
    zg = max(H + rules['avenue_min_len_m'], H + gap + sy + gap + mp['d_m'], extent_s)
    streets.append(dict(rect(-AW / 2, H, AW / 2, zg), id='avenue', kind='avenue'))
    walkways.append(dict(rect(-AW / 2 - wk, H, -AW / 2, zg), id='avenue-walk-w'))
    walkways.append(dict(rect(AW / 2, H, AW / 2 + wk, zg), id='avenue-walk-e'))
    ge = rules['gate']
    gate = rect(-ge['w_m'] / 2, zg, ge['w_m'] / 2, zg + ge['d_m'], id='gate',
                facing=ge['facing'])
    e0 = AW / 2 + wk
    parking.append(dict(rect(e0, zg - mp['d_m'], e0 + mp['w_m'], zg), id='main-parking-e',
                        district=None, stalls=stalls(mp['w_m'], mp['d_m'])))
    parking.append(dict(rect(-e0 - mp['w_m'], zg - mp['d_m'], -e0, zg), id='main-parking-w',
                        district=None, stalls=stalls(mp['w_m'], mp['d_m'])))
    # each main parking lot's driveway crosses the avenue walk to the avenue
    for side, sg in (('e', 1), ('w', -1)):
        zc = zg - mp['d_m'] / 2
        streets.append(dict(rect(sg * AW / 2, zc - 3, sg * e0, zc + 3),
                            id=f'main-parking-{side}-drive', kind='drive'))
    sims_yard = rect(-e0 - sy, H + gap, -e0, H + gap + sy, id='sims-yard',
                     note='reserved for the builder\'s existing sims training yard '
                          '(side = 2 x its maximum radius)')

    allr = streets + walkways + parking + [commons, gate, sims_yard] + lots
    x0 = min(bounds(r)[0] for r in allr)
    z0 = min(bounds(r)[1] for r in allr)
    x1 = max(bounds(r)[2] for r in allr)
    z1 = max(bounds(r)[3] for r in allr)
    radius = max(math.hypot(x, z) for x in (x0, x1) for z in (z0, z1))
    # the farthest corner of anything actually laid out: the walk/cull
    # radius a consumer wants (the bbox corner above is usually empty green)
    reach = max(math.hypot(b[i], b[j]) for b in map(bounds, allr)
                for i in (0, 2) for j in (1, 3))
    bR = (CAMPUS_R2 if len(dks) == 2 else CAMPUS_R3) if dks else CAMPUS_R3
    pl = placement(key)
    for a in pl['city_layer']['anchors']:
        a['inside_site'] = math.hypot(a['x'], a['z']) <= radius
    plan = {
        'name': camp['name'], 'kind': 'halls' if dks else 'hub',
        'districts': dks,
        'site': {'x0': R3(x0), 'z0': R3(z0), 'x1': R3(x1), 'z1': R3(z1),
                 'w': R3(x1 - x0), 'd': R3(z1 - z0),
                 'area_m2': R3((x1 - x0) * (z1 - z0)), 'radius_m': R3(radius),
                 'reach_m': R3(reach),
                 'builder': {'campus_R_m': bR, 'walk_limit_m': bR + WALK_PAD},
                 'fits_builder_radius': radius <= bR + WALK_PAD,
                 'note': 'REAL envelope scale (the walkable interior\'s own '
                         'metres); the builder\'s campus R and walk limit are '
                         'for its 12 m schematic sheds and are reported, not '
                         'changed here'},
        'placement': pl,
        'gate': gate, 'commons': commons, 'sims_yard': sims_yard,
        'districts_plan': dist_out,
        'lots': lots, 'streets': streets, 'walkways': walkways, 'parking': parking,
        'prov': {'layout': 'AUTHORED - campusplan/authored/rules.json',
                 'gate': 'AUTHORED', 'commons': 'AUTHORED', 'parking': 'AUTHORED',
                 'streets': 'AUTHORED', 'walkways': 'AUTHORED',
                 'sims_yard': 'DERIVED size (builder YR max) at an AUTHORED place'},
    }
    check(key, plan)
    return plan


def check(key, p):
    """The invariants, asserted at build time (the test repeats them)."""
    want = [s for k in p['districts'] for s in districts_reg[k]['halls']]
    got = [l['hall'] for l in p['lots']]
    assert got == want, f'{key}: lots {len(got)} != halls {len(want)}'
    parcels = p['lots'] + p['parking'] + [p['commons'], p['gate'], p['sims_yard']]
    circ = p['streets'] + p['walkways']
    for i, a in enumerate(parcels):
        for b in parcels[i + 1:]:
            assert not overlap(a, b), f"{key}: {a.get('id')} overlaps {b.get('id')}"
        for c in circ:
            assert not overlap(a, c), f"{key}: {a.get('id')} overlaps {c['id']}"
    for l in p['lots']:
        assert inside(l['building']['aabb'], l), f"{key}: {l['id']} building leaves its lot"
        if l['yard']:
            assert inside(l['yard'], l), f"{key}: {l['id']} yard leaves its lot"
            assert not overlap(l['yard'], l['building']['aabb']), f"{key}: {l['id']} yard under building"
        w = next(x for x in p['walkways'] if x['id'] == l['walkway'])
        assert touch(l, w), f"{key}: {l['id']} does not touch its walkway"
    # reachability: gate -> circulation -> lot
    nodes = [p['gate'], p['commons']] + circ
    seen, todo = {0}, [0]
    while todo:
        i = todo.pop()
        for j, n in enumerate(nodes):
            if j not in seen and (touch(nodes[i], n) or overlap(nodes[i], n)):
                seen.add(j)
                todo.append(j)
    reach = [nodes[i] for i in seen]
    for l in p['lots']:
        assert any(touch(l, w) for w in reach if w in p['walkways']), \
            f"{key}: {l['id']} unreachable from the gate"


def main():
    plans = {k: plan_campus(k) for k in campuses_reg}
    inputs = [{'path': r, 'sha256_16': sha(r)[:16]} for r in INPUTS
              if r != 'web/build_3d.py']
    inputs.append({'path': 'web/build_3d.py', 'part': 'only the text campusplan reads: '
                   'CLEAR_BASE_M, HEADROOM_M, clear_height, STYLE_OF, CITY_S, the campus R, '
                   'the walk pad, the sims-yard YR max, km per degree, the city log radius',
                   'sha256_16': hashlib.sha256('\n'.join(READ_PARTS).encode()).hexdigest()[:16]})
    stamp = hashlib.sha256(''.join(i['path'] + i['sha256_16'] for i in inputs)
                           .encode()).hexdigest()
    doc = {
        'pack': 'campusplan', 'pack_version': json.loads((ROOT / 'pack' / 'manifest.json').read_text(encoding='utf-8'))['pack_version'],
        'contract': 'CAMPUSPLAN_CONTRACT v1',
        'source_stamp': stamp[:16], 'source_stamp_sha256': stamp,
        'inputs': inputs,
        'units': 'm',
        'frame': {'name': 'campus-site',
                  'origin': 'commons centre = the 3D page plaza centre (campusGroup origin)',
                  'x': 'east', 'z': 'south (three.js: north = -Z)', 'y': 'up, ground 0',
                  'rects': 'axis-aligned {x, z, w, d}: centre x, centre z, extent along x, extent along z',
                  'rot_y': 'three.js rotation.y of a hall group whose door is at local -z '
                           '(N 0, S pi, E -pi/2, W pi/2)'},
        'provenance_tiers': ['RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED', 'SCRIPTED'],
        'honesty': 'Site plans are AUTHORED: no real site, parcel, address, survey, '
                   'zoning or partner is represented. Hall footprints and heights are '
                   'DERIVED from the bundle\'s own interior plans. Campus coordinates '
                   'carry the geo registry\'s own provenance tag, copied.',
        'builder': {'CITY_S': CITY_S, 'campus_R': [CAMPUS_R2, CAMPUS_R3],
                    'walk_pad_m': WALK_PAD, 'sims_yard_radius_max_m': YR_MAX,
                    'STYLE_OF': STYLE_OF,
                    'prov': 'DERIVED - read from web/build_3d.py source at build time'},
        'rules': rules,
        'counts': {k: len(p['lots']) for k, p in plans.items()},
        'campuses': plans,
    }
    text = json.dumps(doc, indent=1, sort_keys=True) + '\n'
    if '--stdout' in sys.argv:          # the test's determinism check
        sys.stdout.write(text)
        return
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(text)
    h = hashlib.sha256(OUT.read_bytes()).hexdigest()[:16]
    for k, p in plans.items():
        s = p['site']
        print(f"  {k:16s} lots {len(p['lots']):3d}  site {s['w']:.0f} x {s['d']:.0f} m  "
              f"r {s['radius_m']:.0f} m reach {s['reach_m']:.0f} m  fits builder {s['fits_builder_radius']}")
    print(f'wrote {OUT.relative_to(ROOT)} sha256[:16] {h}')


if __name__ == '__main__':
    main()
