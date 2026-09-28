#!/usr/bin/env python3
"""geo3d: the 3D campus layout, placed on the Earth (SCHEMATIC).

The 3D environment (web/trade_craft_3d.html) lays every campus out in scene
metres: districts on a ring about the plaza, halls on a grid inside each
district. That layout is computed in the page's JavaScript (web/build_3d.py
buildCampus() and building()). This pack MIRRORS it in Python from the same
registries - never from the page - and projects every hall and district onto
WGS84 about the campus centroid geo/registry/campuses_geo.json records, so the
network globe (web/trade_craft_geomap.html) can stand the halls up where the
3D campus draws them.

WHAT THIS IS NOT. No heading, scale or site survey is recorded for any
campus: the placement is north-up about the centroid, at the scale the 3D
campus draws, and is SCHEMATIC. A campus with no halls in
unions/registry/campuses.json gets no building here - it is listed with zero
halls and a sentence saying so, never an invented footprint.

Fail closed: every registry field is read with need(); a missing one stops
the build with a named error. No default-taking lookups.

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
          'web/interiors.py', 'web/mapdata.py']

# The local tangent plane: a sphere of the IUGG mean Earth radius (the same
# 6371.0088 km geo/test.mjs measures routes with), tangent at the centroid.
EARTH_R_M = 6371008.8
LTP = ('east_m = x, north_m = -z (the 3D scene: north = -Z, east = +X); '
       'lat = lat0 + degrees(north_m / R); lng = lng0 + degrees(east_m / (R * cos(radians(lat0)))); '
       'R = 6371008.8 m (IUGG mean radius); lat0/lng0 = the campus centroid in geo/registry/campuses_geo.json')
PLACEMENT = ('SCHEMATIC: north-up about the campus centroid; no heading or site survey is recorded; '
             'scale as drawn in the 3D campus')

# the 3D page's own constants (web/build_3d.py buildCampus / building)
HALL_W = 12            # building(): wid = 12
COL_PITCH = 16         # buildCampus(): gx * 16
ROW_GAP = 8            # buildCampus(): pitch = maxDep + 8
DEP_FLOOR = 5          # building(): dep = max(h.depth, 5)
DISTRICT_PAD_M = 2     # the district outline stands this far clear of its halls
# the highest envelope piece above the wall, per roofline (LAYOUT_CONTRACT v1):
# flat = rooftop unit 1.6x0.8x1.2 at y = h + .4; gable = 7.2 x .5 slab at
# y = h + 1.1 rotated .48 rad; saw = 3.2 x 1.5 tooth at y = h + .55 rotated .42 rad
ROOF_TOP = {'flat': lambda h: h + .8,
            'gable': lambda h: h + 1.1 + 3.6 * math.sin(.48) + .25 * math.cos(.48),
            'saw': lambda h: h + .55 + 1.6 * math.sin(.42) + .75 * math.cos(.42)}


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
        if v not in ROOF_TOP:
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


def rect(cx, cz, psi, u, v, hw, hd):
    """A local (u, v) rectangle in a district group rotated psi about +Y and
    set at (cx, cz): THREE's rotation.y maps local (u, v) to world
    x = cx + u cos psi + v sin psi, z = cz - u sin psi + v cos psi."""
    c, s = math.cos(psi), math.sin(psi)
    out = []
    for du, dv in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)):
        uu, vv = u + du, v + dv
        out.append((cx + uu * c + vv * s, cz - uu * s + vv * c))
    return out


def main():
    campuses = need(load('unions/registry/campuses.json'), 'campuses', 'unions/registry/campuses.json')
    districts = need(load('unions/registry/districts.json'), 'districts', 'unions/registry/districts.json')
    halls_json = need(load('pack/registry/halls.json'), 'halls', 'pack/registry/halls.json')
    geo = need(load('geo/registry/campuses_geo.json'), 'campuses', 'geo/registry/campuses_geo.json')
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
        n = len(dk)
        R = 124 if n == 2 else 168
        entry['R_m'] = R
        entry['ring_road_r_m'] = R - 24
        listed = []
        for di, k in enumerate(dk):
            d = need(districts, k, f'unions/registry/districts.json#districts.{k}')
            dh = need(d, 'halls', f'districts.{k}')
            ang = di / n * math.pi * 2 - math.pi / 2
            rx, rz = math.cos(ang), math.sin(ang)
            psi = math.atan2(rx, rz)
            cx, cz = rx * R, rz * R
            cols = math.ceil(math.sqrt(len(dh) * 1.7))
            max_dep = max(max(depth[sg], DEP_FLOOR) for sg in dh)
            pitch = max_dep + ROW_GAP
            if k not in HUES:
                fail(f'web/mapdata.py HUES has no hue for district {k}')
            if k not in styles:
                fail(f'web/build_3d.py STYLE_OF has no roofline for district {k}')
            roof = styles[k]
            hall_rows = []
            for i, sg in enumerate(dh):
                if sg not in hall_by:
                    fail(f'district {k} lists hall {sg!r} that pack/registry/halls.json does not carry')
                dval = depth[sg]
                dep = max(dval, DEP_FLOOR)
                hgt = 6 + (dval % 3) * .7
                gx = (i % cols) - (cols - 1) / 2
                gz = i // cols
                u, v = gx * COL_PITCH, gz * pitch
                c, s = math.cos(psi), math.sin(psi)
                x, z = cx + u * c + v * s, cz - u * s + v * c
                corners = rect(cx, cz, psi, u, v, HALL_W / 2, dep / 2)
                ring = [to_ll(px, pz, lat0, lng0) for px, pz in corners]
                ring.append(list(ring[0]))
                hall_rows.append({
                    'slug': sg, 'name': need(hall_by[sg], 'name', f'halls.json#{sg}'),
                    'district': k, 'grid': {'gx': gx, 'gz': gz, 'cols': cols},
                    'x': round(x, 4), 'z': round(z, 4), 'w': HALL_W, 'd': dep,
                    'h': round(hgt, 4), 'roof': roof, 'top': round(ROOF_TOP[roof](hgt), 4), 'psi': round(psi, 9), 'depth_units': dval,
                    'corners_m': [[round(px, 4), round(pz, 4)] for px, pz in corners],
                    'polygon': ring, 'center_ll': to_ll(x, z, lat0, lng0),
                })
                listed.append(sg)
            us = [r['grid']['gx'] * COL_PITCH for r in hall_rows]
            vs = [r['grid']['gz'] * pitch for r in hall_rows]
            u0 = min(us) - HALL_W / 2 - DISTRICT_PAD_M
            u1 = max(us) + HALL_W / 2 + DISTRICT_PAD_M
            v0 = min(vv - r['d'] / 2 for vv, r in zip(vs, hall_rows)) - DISTRICT_PAD_M
            v1 = max(vv + r['d'] / 2 for vv, r in zip(vs, hall_rows)) + DISTRICT_PAD_M
            dc = rect(cx, cz, psi, (u0 + u1) / 2, (v0 + v1) / 2, (u1 - u0) / 2, (v1 - v0) / 2)
            dring = [to_ll(px, pz, lat0, lng0) for px, pz in dc]
            dring.append(list(dring[0]))
            entry['districts'].append({
                'key': k, 'name': need(d, 'name', f'districts.{k}'), 'hue': HUES[k], 'roof': roof,
                'cx': round(cx, 4), 'cz': round(cz, 4), 'psi': round(psi, 9),
                'cols': cols, 'pitch': pitch, 'halls': list(dh),
                'corners_m': [[round(px, 4), round(pz, 4)] for px, pz in dc],
                'polygon': dring, 'center_ll': to_ll(cx, cz, lat0, lng0),
            })
            entry['halls'].extend(hall_rows)
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
        'frame': 'scene metres of web/trade_craft_3d.html: north = -Z, east = +X; psi is the district group rotation about +Y',
        'mirrors': 'web/build_3d.py buildCampus() (district ring, hall grid) and building() (footprint 12 x max(depth,5), wall height h = 6 + (depth % 3) * 0.7; top = the roofline\'s highest piece per LAYOUT_CONTRACT v1)',
        'honesty': {
            'schematic': PLACEMENT,
            'no_invention': 'only campuses whose halls unions/registry/campuses.json lists get buildings; the others show zero halls and no footprint',
            'not_a_survey': 'a footprint here is the 3D campus drawing of a functional programme (web/interiors.py), not a building anyone surveyed or built',
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
