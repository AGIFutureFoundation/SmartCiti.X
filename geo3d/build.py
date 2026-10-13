#!/usr/bin/env python3
"""geo3d: the 3D campus layout, placed on the Earth (SCHEMATIC).

The 3D environment (web/trade_craft_3d.html) lays every hall out on its own
lot of the AUTHORED campus site plan (campusplan/registry/campusplan.json,
CAMPUSPLAN_CONTRACT v1; LAYOUT_CONTRACT v2): one building per lot, at the
walkable interior's own size (36 x 3*depth m), turned to face its walkway.
This pack reads those SAME lots - never the page - and projects every hall
footprint (the lot building's rotated footprint, building.aabb) and every
district block (districts_plan[].block) onto WGS84 about the campus centroid
geo/registry/campuses_geo.json records, so the network globe
(web/trade_craft_geomap.html) stands the halls up where the 3D campus draws
them. (Until wave 10 it mirrored the retired ring-of-sheds formula.)

WHAT THIS IS NOT. No heading, scale or site survey is recorded for any
campus: the placement is north-up about the centroid, at the scale the 3D
campus draws, and is SCHEMATIC; the site plan itself is AUTHORED. A campus
with no halls in unions/registry/campuses.json gets no building here - it
is listed with zero halls and a sentence saying so, never an invented
footprint.

Fail closed: every registry field is read with need(); a missing one (or a
missing campusplan registry, or lots that are not the campus's halls in
registry order) stops the build with a named error. No default-taking lookups.

    python3 geo3d/build.py            # writes geo3d/registry/geo3d.json
"""
import hashlib
import json
import math
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'web'))
from interiors import build as build_interiors  # noqa: E402  the same plan_for build_3d.py reads
from mapdata import HUES  # noqa: E402  the district hues the 3D page paints

INPUTS = ['unions/registry/campuses.json', 'unions/registry/districts.json',
          'pack/registry/halls.json', 'geo/registry/campuses_geo.json',
          'web/interiors.py', 'web/mapdata.py', 'campusplan/registry/campusplan.json']

# The local tangent plane: a sphere of the IUGG mean Earth radius (the same
# 6371.0088 km geo/test.mjs measures routes with), tangent at the centroid.
EARTH_R_M = 6371008.8
LTP = ('east_m = x, north_m = -z (the 3D scene: north = -Z, east = +X); '
       'lat = lat0 + degrees(north_m / R); lng = lng0 + degrees(east_m / (R * cos(radians(lat0)))); '
       'R = 6371008.8 m (IUGG mean radius); lat0/lng0 = the campus centroid in geo/registry/campuses_geo.json')
PLACEMENT = ('SCHEMATIC: north-up about the campus centroid; no heading or site survey is recorded; '
             'scale as drawn in the 3D campus')

# The wall box the 3D page stands on each lot (LAYOUT_CONTRACT v2): the plan's
# eaves clear height plus the builder's .35 m slab. The hall's archetype roof
# (web/hallkit.py) rises above it and has no closed form, so it is NOT mirrored:
# `top` here is the wall-box top, a lower bound on what the page draws.
SLAB_M = .35


def style_of():
    """The district -> roofline table, read from web/build_3d.py's own
    `const STYLE_OF = {...};` (the same regex build_3d.py gates itself with).
    Returns the table and the literal block text (stamped)."""
    src = (ROOT / 'web/build_3d.py').read_text()
    mt = re.search(r'const STYLE_OF = \{(.*?)\};', src, re.S)
    if mt is None:
        fail('web/build_3d.py has no `const STYLE_OF = {...};` block')
    table = dict(re.findall(r"(\w+):\s*'(\w+)'", mt.group(1)))
    for k, v in table.items():
        if v not in ('flat', 'gable', 'saw'):
            fail(f'STYLE_OF gives district {k} an unknown roofline {v!r}')
    return table, mt.group(0)


def fail(msg):
    raise SystemExit(f'geo3d/build.py: {msg}')


def need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        fail(f'{where} has no field {k!r}')
    return d[k]


def load(rel):
    p = ROOT / rel
    if not p.exists():
        fail(f'missing input {rel}')
    return json.loads(p.read_text())


def hall_depths(halls_json):
    """envelope.d per hall, from web/interiors.py exactly as web/build_3d.py
    reads it (plans[slug]['envelope']['d']). The depth does not depend on
    the commissioning states, so an empty census is passed."""
    plans = build_interiors(halls_json, lambda i: {'live': 0})
    return {s: need(need(p, 'envelope', f'plan {s}'), 'd', f'plan {s}.envelope') for s, p in plans.items()}


def to_ll(x, z, lat0, lng0):
    east, north = x, -z
    lat = lat0 + math.degrees(north / EARTH_R_M)
    lng = lng0 + math.degrees(east / (EARTH_R_M * math.cos(math.radians(lat0))))
    return [round(lng, 9), round(lat, 9)]


def aarect(r):
    """The four corners of an axis-aligned plan rect {x, z, w, d} (campus-site
    frame: x east, z south), in ring order."""
    x, z, hw, hd = r['x'], r['z'], r['w'] / 2, r['d'] / 2
    return [(x - hw, z - hd), (x + hw, z - hd), (x + hw, z + hd), (x - hw, z + hd)]


def main():
    campuses = need(load('unions/registry/campuses.json'), 'campuses', 'unions/registry/campuses.json')
    districts = need(load('unions/registry/districts.json'), 'districts', 'unions/registry/districts.json')
    halls_json = need(load('pack/registry/halls.json'), 'halls', 'pack/registry/halls.json')
    geo = need(load('geo/registry/campuses_geo.json'), 'campuses', 'geo/registry/campuses_geo.json')
    cplan = load('campusplan/registry/campusplan.json')   # SITES' AUTHORED site plans; missing -> named stop
    hall_by = {need(h, 'slug', 'halls.json#halls[]'): h for h in halls_json}
    depth = hall_depths(halls_json)
    styles, style_block = style_of()

    out_campuses = {}
    placed = []
    for key, camp in campuses.items():
        where = f'unions/registry/campuses.json#campuses.{key}'
        dk = need(camp, 'districts', where)
        halls = need(camp, 'halls', where)
        g = need(geo, key, f'geo/registry/campuses_geo.json#campuses.{key}')
        lat0, lng0 = need(g, 'lat', f'campuses_geo.{key}'), need(g, 'lng', f'campuses_geo.{key}')
        entry = {'name': need(camp, 'name', where), 'centroid': {'lat': lat0, 'lng': lng0,
                 'provenance': need(g, 'provenance', f'campuses_geo.{key}')},
                 'halls_count': len(halls), 'districts': [], 'halls': []}
        if not halls:
            if dk:
                fail(f'{key} has districts {dk} but no halls')
            entry['note'] = ('no halls are listed for this campus in unions/registry/campuses.json, '
                             'so nothing is stood up here - no building is invented')
            out_campuses[key] = entry
            continue
        plan = need(need(cplan, 'campuses', 'campusplan.json'), key, f'campusplan.json#campuses.{key}')
        lots = need(plan, 'lots', f'campusplan {key}')
        want = [sg for k in dk for sg in need(need(districts, k, f'districts.{k}'), 'halls', f'districts.{k}')]
        if [need(l, 'hall', f'campusplan {key} lot') for l in lots] != want:
            fail(f'campusplan/registry/campusplan.json lots for {key} are not its halls in registry order')
        blocks = {need(dp, 'key', f'campusplan {key}.districts_plan'): need(dp, 'block', f'campusplan {key}.districts_plan')
                  for dp in need(plan, 'districts_plan', f'campusplan {key}')}
        site = need(plan, 'site', f'campusplan {key}')
        entry['site_radius_m'] = need(site, 'radius_m', f'campusplan {key}.site')
        entry['plan_stamp'] = need(cplan, 'source_stamp', 'campusplan.json')
        listed = []
        for k in dk:
            d = need(districts, k, f'unions/registry/districts.json#districts.{k}')
            if k not in HUES:
                fail(f'web/mapdata.py HUES has no hue for district {k}')
            if k not in styles:
                fail(f'web/build_3d.py STYLE_OF has no roofline for district {k}')
            if k not in blocks:
                fail(f'campusplan {key} has no districts_plan block for {k}')
            roof = styles[k]
            blk = blocks[k]
            dc = aarect(blk)
            dring = [to_ll(px, pz, lat0, lng0) for px, pz in dc]
            dring.append(list(dring[0]))
            entry['districts'].append({
                'key': k, 'name': need(d, 'name', f'districts.{k}'), 'hue': HUES[k], 'roof': roof,
                'cx': need(blk, 'x', f'{key}/{k}.block'), 'cz': need(blk, 'z', f'{key}/{k}.block'), 'psi': 0,
                'halls': list(need(d, 'halls', f'districts.{k}')),
                'corners_m': [[round(px, 4), round(pz, 4)] for px, pz in dc],
                'polygon': dring, 'center_ll': to_ll(blk['x'], blk['z'], lat0, lng0),
            })
        for lot in lots:
            sg = need(lot, 'hall', f'campusplan {key} lot')
            if sg not in hall_by:
                fail(f'campusplan {key} lot {sg!r} is not a hall pack/registry/halls.json carries')
            b = need(lot, 'building', f'campusplan lot {sg}')
            ab = need(b, 'aabb', f'campusplan lot {sg}.building')
            dval = depth[sg]
            if need(b, 'w_m', f'lot {sg}.building') != 36 or need(b, 'd_m', f'lot {sg}.building') != dval * 3:
                fail(f'campusplan lot {sg}: footprint is not the walkable interior\'s own 36 x 3*depth m')
            k = need(lot, 'district', f'campusplan lot {sg}')
            hgt = need(b, 'height_m', f'lot {sg}.building') + SLAB_M
            corners = aarect(ab)
            ring = [to_ll(px, pz, lat0, lng0) for px, pz in corners]
            ring.append(list(ring[0]))
            door = need(b, 'door', f'lot {sg}.building')
            entry['halls'].append({
                'slug': sg, 'name': need(hall_by[sg], 'name', f'halls.json#{sg}'),
                'district': k, 'lot': need(lot, 'id', f'campusplan lot {sg}'),
                'x': need(b, 'x', f'lot {sg}.building'), 'z': need(b, 'z', f'lot {sg}.building'),
                'w': b['w_m'], 'd': b['d_m'], 'rot': need(b, 'rot_y', f'lot {sg}.building'),
                'facing': need(b, 'facing', f'lot {sg}.building'),
                'door': {'x': need(door, 'x', f'lot {sg}.door'), 'z': need(door, 'z', f'lot {sg}.door')},
                'h': round(hgt, 4), 'roof': styles[k], 'top': round(hgt, 4), 'psi': 0, 'depth_units': dval,
                'corners_m': [[round(px, 4), round(pz, 4)] for px, pz in corners],
                'polygon': ring, 'center_ll': to_ll(b['x'], b['z'], lat0, lng0),
            })
            listed.append(sg)
        if sorted(listed) != sorted(halls):
            fail(f'{key}: halls drawn from its districts {sorted(set(listed) ^ set(halls))} differ from the campus hall list')
        placed.extend(listed)
        out_campuses[key] = entry

    if len(placed) != len(set(placed)):
        fail('a hall is placed on more than one campus')
    stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
    inputs_stamp = hashlib.sha256(b''.join((ROOT / p).read_bytes() for p in INPUTS)
                                  + style_block.encode('utf8')).hexdigest()[:16]
    with_halls = [k for k, c in out_campuses.items() if c['halls']]
    reg = {
        'pack': 'smartcitix-trade-craft-academy-geo3d',
        'source_stamp': stamp,
        'inputs': INPUTS,
        'inputs_stamp': inputs_stamp,
        'inputs_also': 'the literal `const STYLE_OF = {...};` block of web/build_3d.py (roofline per district), appended to the inputs_stamp',
        'provenance': 'SCHEMATIC',
        'placement': PLACEMENT,
        'projection': LTP,
        'frame': 'scene metres of web/trade_craft_3d.html = campusplan frame campus-site: north = -Z, east = +X, origin = the commons centre; districts sit at the origin (psi 0), each hall turned by rot (door at local -z)',
        'mirrors': 'campusplan/registry/campusplan.json lots (LAYOUT_CONTRACT v2): hall footprint = lots[].building.aabb (36 x 3*depth m, rotated by rot_y), centre building.x/z, h = height_m + 0.35 slab; district outline = districts_plan[].block. top = the wall-box top only: the archetype roof (web/hallkit.py) rises above it and is not mirrored',
        'honesty': {
            'schematic': PLACEMENT,
            'no_invention': 'only campuses whose halls unions/registry/campuses.json lists get buildings; the others show zero halls and no footprint',
            'not_a_survey': 'a footprint here is the 3D campus drawing of a functional programme (web/interiors.py), not a building anyone surveyed or built',
            'site_plan': 'positions, facings, streets and district blocks are the AUTHORED campus site plan (campusplan/authored/rules.json), not a real site',
        },
        'counts': {'campuses': len(out_campuses), 'campuses_with_halls': len(with_halls),
                   'campuses_without_halls': len(out_campuses) - len(with_halls),
                   'districts': sum(len(c['districts']) for c in out_campuses.values()),
                   'halls': len(placed)},
        'campuses': out_campuses,
    }
    dst = HERE / 'registry' / 'geo3d.json'
    dst.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + '\n')
    print(f'geo3d: {len(placed)} halls in {reg["counts"]["districts"]} districts on '
          f'{len(with_halls)} campuses placed SCHEMATIC; {reg["counts"]["campuses_without_halls"]} campuses have no halls')


if __name__ == '__main__':
    main()
