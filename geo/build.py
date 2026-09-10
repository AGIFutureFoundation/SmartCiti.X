#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the geo pack builder.

Real geography for the three-campus network: WGS84 coordinates, great-circle
distances, and true bearings, emitted both as a registry and as standard
GeoJSON (the interchange format every Mapbox/MapLibre-compatible stack
consumes directly).

PROVENANCE, per point, in the record itself — the discipline is adopted from
Locator.X's rooms module (RECORDED / DERIVED / SCHEMATIC; Apache-2.0, the
same foundation), where nothing is stated that the source does not support:

  - Oakland's coordinates are RECORDED: copied verbatim from Locator.X's
    city table (src/app.js, CITIES), which is real committed data.
  - Treasure Island and New Orleans are DERIVED: well-known place centroids
    authored here, since neither appears in that table.
  - Everything downstream of the coordinates (distances, bearings) is
    computed, and the suite recomputes it rather than trusting it.

What this is NOT: siting. The campuses remain PLANNED locations (the union
registry's honesty note stands); a coordinate here anchors a map, it does
not claim a parcel. When Locator.X's checkout is present beside this repo,
the build cross-checks the RECORDED pair against the table it cites and
fails on drift.
"""
import hashlib
import json
import math
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

PACK_VERSION = "3.2.0"
BUILT = "2026-09-10"

# slug: (lat, lng, provenance, source)
GEO = {
    'treasure-island': (37.8235, -122.3705, 'DERIVED',
                        'Treasure Island centroid, authored (WGS84)'),
    'oakland':         (37.8044, -122.2712, 'RECORDED',
                        'Locator.X city table (src/app.js CITIES), Apache-2.0'),
    'new-orleans':     (29.9511, -90.0715, 'DERIVED',
                        'New Orleans centroid, authored (WGS84)'),
}

# Cross-check the RECORDED value against the table it cites, when the
# Locator.X checkout is reachable. A citation that can drift silently is a
# second copy of a truth; this one fails the build instead.
locx = ROOT.parent / 'locator.x' / 'src' / 'app.js'
if locx.exists():
    m = re.search(r"\['Oakland',([0-9.]+),(-[0-9.]+),", locx.read_text())
    assert m, 'Locator.X city table no longer lists Oakland'
    assert (float(m.group(1)), float(m.group(2))) == GEO['oakland'][:2], \
        'RECORDED Oakland coordinates drifted from the Locator.X table'
    checked = 'cross-checked against the Locator.X checkout'
else:
    checked = 'Locator.X checkout not present; citation not re-checked this build'

# City and institution anchors near each campus — ALL RECORDED, copied
# verbatim from Locator.X's committed tables (Apache-2.0, this foundation):
# the Bay Area city table (src/app.js CITIES) and the New Orleans POI table
# (build_data_nola.py). Cross-checked against the cited files when the
# checkout is present, like the Oakland campus pair above.
ANCHORS = {
    'treasure-island': [
        ('San Francisco', 37.7749, -122.4194, 'src/app.js CITIES'),
        ('Sausalito', 37.859, -122.4853, 'src/app.js CITIES'),
        ('Alameda', 37.7652, -122.2416, 'src/app.js CITIES'),
        ('Daly City', 37.6879, -122.4702, 'src/app.js CITIES'),
    ],
    'oakland': [
        ('Berkeley', 37.8716, -122.2727, 'src/app.js CITIES'),
        ('Emeryville', 37.8313, -122.2852, 'src/app.js CITIES'),
        ('Alameda', 37.7652, -122.2416, 'src/app.js CITIES'),
        ('San Leandro', 37.7249, -122.1561, 'src/app.js CITIES'),
    ],
    'new-orleans': [
        ('Tulane University', 29.9404, -90.1207, 'build_data_nola.py pois'),
        ('Xavier University', 29.9649, -90.1073, 'build_data_nola.py pois'),
        ('University of New Orleans', 30.0288, -90.0664, 'build_data_nola.py pois'),
        ('Delgado Community College', 29.9814, -90.1050, 'build_data_nola.py pois'),
    ],
}

if locx.exists():
    _lx = locx.read_text()
    _nola = (ROOT.parent / 'locator.x' / 'build_data_nola.py').read_text()
    for _ck, _list in ANCHORS.items():
        for _name, _lat, _lng, _src in _list:
            if 'CITIES' in _src:
                _pat = f"['{_name}',{_lat}"
                assert _pat in _lx, f'anchor drifted from CITIES: {_name}'
            else:
                _pairs = {(float(a), float(b)) for a, b in
                          re.findall(r'\((-9\d\.\d+),(\d\d\.\d+)\)', _nola)}
                assert (_lng, _lat) in _pairs, \
                    f'anchor drifted from the NOLA POI table: {_name}'

campuses = json.load(open(ROOT / 'unions/registry/campuses.json'))['campuses']
assert set(GEO) == set(campuses), 'a coordinate per campus, exactly'


def haversine_km(a, b):
    R = 6371.0088
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = math.radians(b[0] - a[0])
    dl = math.radians(b[1] - a[1])
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(h))


def bearing_deg(a, b):
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1)*math.sin(p2) - math.sin(p1)*math.cos(p2)*math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


keys = list(GEO)
routes = []
for i, a in enumerate(keys):
    for b in keys[i+1:]:
        pa, pb = GEO[a][:2], GEO[b][:2]
        routes.append({
            'from': a, 'to': b,
            'km': round(haversine_km(pa, pb), 1),
            'bearing_deg': round(bearing_deg(pa, pb), 1),
        })

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

doc = {
    'pack': 'smartcitix-trade-craft-academy-geo-registry',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'crs': 'WGS84 (EPSG:4326)',
    'recorded_check': checked,
    'honesty': {
        'siting': 'a coordinate anchors a map; it does not claim a parcel. '
                  'The campuses remain planned locations per the union '
                  'registry, and no address is recorded.',
        'provenance': 'RECORDED / DERIVED / SCHEMATIC discipline after the '
                      'Locator.X rooms module (Apache-2.0): nothing is '
                      'stated that the source does not support.',
    },
    'campuses': {
        k: {'lat': lat, 'lng': lng, 'provenance': prov, 'source': src,
            'city': campuses[k]['city'], 'region': campuses[k]['region']}
        for k, (lat, lng, prov, src) in GEO.items()
    },
    'routes_km': routes,
    'anchors': {
        ck: [{'name': n, 'lat': lat, 'lng': lng, 'provenance': 'RECORDED',
              'source': f'Locator.X {src}, Apache-2.0',
              'km': round(haversine_km(GEO[ck][:2], (lat, lng)), 1),
              'bearing_deg': round(bearing_deg(GEO[ck][:2], (lat, lng)), 1)}
             for n, lat, lng, src in lst]
        for ck, lst in ANCHORS.items()
    },
}

geojson = {
    'type': 'FeatureCollection',
    'features': [
        {'type': 'Feature',
         'geometry': {'type': 'Point', 'coordinates': [lng, lat]},
         'properties': {
             'slug': k, 'name': campuses[k]['name'],
             'city': campuses[k]['city'], 'region': campuses[k]['region'],
             'districts': len(campuses[k]['districts']),
             'halls': len(campuses[k]['halls']),
             'provenance': prov, 'source': src,
         }}
        for k, (lat, lng, prov, src) in GEO.items()
    ] + [
        {'type': 'Feature',
         'geometry': {'type': 'Point', 'coordinates': [lng, lat]},
         'properties': {'kind': 'anchor', 'name': n, 'near': ck,
                        'provenance': 'RECORDED',
                        'source': f'Locator.X {src}, Apache-2.0'}}
        for ck, lst in ANCHORS.items() for n, lat, lng, src in lst
    ],
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'campuses_geo.json').write_text(json.dumps(doc, indent=1) + '\n')
(OUT / 'campuses.geojson').write_text(json.dumps(geojson, indent=1) + '\n')
route_txt = ', '.join('{}-{} {} km'.format(r['from'], r['to'], r['km'])
                      for r in routes)
n_anchor = sum(len(v) for v in ANCHORS.values())
print(f"geo registry: {len(GEO)} campuses, {len(routes)} routes "
      f"({route_txt}), {n_anchor} RECORDED anchors; {checked} "
      f"(source stamp {stamp})")
