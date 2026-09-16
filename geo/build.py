#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the geo pack builder.

Real geography for the campus network: WGS84 coordinates, great-circle
distances, and true bearings, emitted both as a registry and as standard
GeoJSON (the interchange format every Mapbox/MapLibre-compatible stack
consumes directly).

PROVENANCE, per point, in the record itself — the discipline is adopted from
Locator.X's rooms module (RECORDED / DERIVED / SCHEMATIC; Apache-2.0, the
same foundation), where nothing is stated that the source does not support.
A fourth tier, AUTHORED, was added for the roadmap pack's candidate cities
and is used here for the same reason: it is a materially weaker claim than
RECORDED, and it is labelled as one rather than dressed up as one of the
three tiers this build can actually check itself against.

  - Oakland's coordinates are RECORDED: copied verbatim from Locator.X's
    city table (src/app.js, CITIES), which is real committed data.
  - Treasure Island and New Orleans are DERIVED: well-known place centroids
    authored here, since neither appears in that table.
  - Houston, Chicago, Seattle, Pittsburgh and Denver are AUTHORED:
    widely-published public geography (the kind a city's own Wikipedia
    infobox states), typed here from general knowledge. No sibling source
    cross-checks any of the five, unlike the other three - the same
    honesty this pack's roadmap already states for every candidate city,
    carried through now that each is built rather than proposed.
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
    'houston':         (29.7604, -95.3698, 'AUTHORED',
                        'widely-published public geography (city-center), '
                        'typed from general knowledge - not cross-checked '
                        'against any file this build can verify'),
    'chicago':         (41.8781, -87.6298, 'AUTHORED',
                        'widely-published public geography (city-center), '
                        'typed from general knowledge - not cross-checked '
                        'against any file this build can verify'),
    'seattle':         (47.6062, -122.3321, 'AUTHORED',
                        'widely-published public geography (city-center), '
                        'typed from general knowledge - not cross-checked '
                        'against any file this build can verify'),
    'pittsburgh':      (40.4406, -79.9959, 'AUTHORED',
                        'widely-published public geography (city-center), '
                        'typed from general knowledge - not cross-checked '
                        'against any file this build can verify'),
    'denver':          (39.7392, -104.9903, 'AUTHORED',
                        'widely-published public geography (city-center), '
                        'typed from general knowledge - not cross-checked '
                        'against any file this build can verify'),
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
        ('Richmond', 37.9358, -122.3477, 'src/app.js CITIES'),
        ('San Rafael', 37.9735, -122.5311, 'src/app.js CITIES'),
        ('South San Francisco', 37.6547, -122.4077, 'src/app.js CITIES'),
        ('San Mateo', 37.5630, -122.3255, 'src/app.js CITIES'),
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
        ('Loyola University', 29.9351, -90.1223, 'build_data_nola.py pois'),
        ('Dillard University', 29.9903, -90.0517, 'build_data_nola.py pois'),
        ('SUNO', 30.0421, -90.0330, 'build_data_nola.py pois'),
    ],
}

# Institution anchors near the five HUB campuses (Houston, Chicago,
# Seattle, Pittsburgh, Denver) — a different, weaker tier than ANCHORS
# above, and kept in a separate table so the two are never confused. Every
# anchor above is RECORDED, copied verbatim from a sibling Locator.X table
# this build can cross-check against. No such table lists a single real
# place near any hub campus, so nothing here could ever be RECORDED — each one is
# AUTHORED, the same tier this pack already uses for the hub campuses'
# own centres (GEO, above) and for the Bay Restoration sites: real,
# named, well-known institutions only, never invented, each typed from
# general public knowledge and not cross-checked against any file this
# build can verify. Coordinates are each institution's approximate,
# widely-published location, not a surveyed pin.
AUTHORED_ANCHORS = {
    'houston': [
        ('Port of Houston Authority', 29.7350, -95.2700,
         "the Houston Ship Channel port authority's Turning Basin district"),
        ('University of Houston', 29.7199, -95.3422,
         'the public research university’s main campus'),
        ('San Jacinto College', 29.6910, -95.1830,
         'the Central campus in Pasadena, TX, known for its maritime and '
         'process-technology trades programs'),
        ('Houston Community College', 29.7241, -95.3775,
         'the community-college system’s Central campus'),
    ],
    'chicago': [
        ('Chicago Union Station', 41.8789, -87.6359,
         'the city’s major intercity and commuter rail terminal'),
        ('Navy Pier', 41.8917, -87.6086,
         'the Lake Michigan pier and public landmark'),
        ('University of Illinois Chicago', 41.8708, -87.6505,
         'the public research university’s campus'),
        ('Richard J. Daley College', 41.7648, -87.7270,
         'City Colleges of Chicago’s construction-trades campus'),
    ],
    'seattle': [
        ('Port of Seattle', 47.6087, -122.3428,
         "the public port authority's Pier 69 headquarters on the "
         'central waterfront'),
        ('University of Washington', 47.6553, -122.3035,
         'the public research university’s Seattle campus'),
        ('Museum of Flight', 47.5185, -122.2971,
         'the aerospace museum at Boeing Field (King County '
         'International Airport)'),
        ('South Seattle College', 47.5495, -122.3576,
         'the Seattle Colleges system’s West Seattle campus'),
    ],
    'pittsburgh': [
        ('Port of Pittsburgh Commission', 40.4380, -79.9958,
         'the regional port authority for the Pittsburgh-area inland '
         'waterway system, headquartered near the three-rivers '
         'confluence'),
        ('Carnegie Mellon University', 40.4443, -79.9436,
         'the private research university’s Oakland (Pittsburgh) campus'),
        ('Carrie Blast Furnaces National Historic Landmark', 40.4062,
         -79.8631, 'a former U.S. Steel blast-furnace plant on the '
         'Monongahela, part of the Rivers of Steel National Heritage '
         'Area'),
        ('Community College of Allegheny County', 40.4530, -80.0090,
         'CCAC’s Allegheny Campus on the North Side, with career-'
         'technical and trades programs'),
    ],
    'denver': [
        ('Colorado School of Mines', 39.7503, -105.2211,
         'the public mining and earth-sciences research university in '
         'Golden, just west of Denver'),
        ('National Renewable Energy Laboratory', 39.7407, -105.1686,
         "the U.S. Department of Energy's national laboratory for "
         'renewable-energy research, on its South Table Mountain campus '
         'in Golden'),
        ('Denver Union Station', 39.7539, -105.0011,
         "the city's historic downtown transit hub for rail, bus and "
         'light rail'),
        ('Community College of Denver', 39.7444, -105.0064,
         'the public community college on the Auraria Campus downtown, '
         'with career-technical and trades programs'),
    ],
}

# One-line descriptions for the New Orleans institutions — AUTHORED from
# public record, and labelled so: the coordinate is RECORDED from
# Locator.X, the sentence about the place is not from that table and does
# not claim to be. Kept to widely-verifiable identity facts only.
BLURBS = {
    'San Francisco':
        'The peninsula city at the Golden Gate - the Bay Area’s '
        'historic urban core, west across the bay from the campus island.',
    'Sausalito':
        'Waterfront town just inside the Golden Gate, on Richardson Bay '
        'under the Marin Headlands.',
    'Alameda':
        'Island city in San Francisco Bay beside Oakland, on the grounds '
        'of the former naval air station.',
    'Daly City':
        'The gateway city where the San Francisco peninsula meets '
        'San Mateo County.',
    'Richmond':
        'East Bay port city on San Pablo Bay, home of the wartime '
        'Kaiser shipyards.',
    'San Rafael':
        'Marin County’s seat, north of the bay along the 101 corridor.',
    'South San Francisco':
        'The industrial city - its hillside sign says so - between '
        'San Francisco and the airport.',
    'San Mateo':
        'Peninsula city midway between San Francisco and Silicon Valley.',
    'Berkeley':
        'East Bay city, home of the University of California’s '
        'founding campus.',
    'Emeryville':
        'Compact industrial-turned-tech city at the foot of the '
        'Bay Bridge approach.',
    'San Leandro':
        'East Bay manufacturing city directly south of Oakland.',
    'Tulane University':
        'Private research university Uptown on St. Charles Avenue, '
        'founded 1834; engineering and architecture among its schools.',
    'Xavier University':
        'Xavier University of Louisiana - the nation’s only '
        'historically Black and Catholic university.',
    'University of New Orleans':
        'Public research university on the Lake Pontchartrain shore; '
        'home to naval architecture and marine engineering.',
    'Delgado Community College':
        'Louisiana’s largest community college, City Park campus - '
        'the region’s major technical and trades educator.',
    'Loyola University':
        'Jesuit university on St. Charles Avenue, directly beside '
        'Tulane at Audubon Park.',
    'Dillard University':
        'Historically Black university on Gentilly Boulevard, known '
        'for its oak-lined Avenue of the Oaks.',
    'SUNO':
        'Southern University at New Orleans - public historically Black '
        'university in Pontchartrain Park.',
    'Port of Houston Authority':
        'One of the busiest ports in the United States by tonnage, on the '
        'Houston Ship Channel connecting the city to the Gulf of Mexico.',
    'University of Houston':
        'Public research university southeast of downtown, Texas’s '
        'third-largest by enrollment.',
    'San Jacinto College':
        'Community college serving the Houston Ship Channel-area workforce, '
        'with real maritime, process-technology and trades programs.',
    'Houston Community College':
        'One of the largest community college systems in the country, '
        'central to the city’s technical and workforce education.',
    'Chicago Union Station':
        'The city’s grand 1925 rail terminal on the west bank of the '
        'Chicago River, still Amtrak’s hub for the entire Midwest.',
    'Navy Pier':
        'A 1916 municipal pier on Lake Michigan, now one of the '
        'Midwest’s most-visited public landmarks.',
    'University of Illinois Chicago':
        'Public research university just west of the Loop, one of the '
        'city’s largest employers and enrollments.',
    'Richard J. Daley College':
        'City Colleges of Chicago’s Southwest Side campus, home to its '
        'construction and manufacturing trades programs.',
    'Port of Seattle':
        'The public port authority that runs the Seattle waterfront’s '
        'seaport and Seattle–Tacoma International Airport.',
    'University of Washington':
        'Public research university on the Montlake cut, one of the '
        'largest and oldest on the West Coast.',
    'Museum of Flight':
        'The independent, non-profit air and space museum at Boeing '
        'Field, tracing the region’s aerospace-manufacturing history.',
    'South Seattle College':
        'One of the three Seattle Colleges system campuses, with '
        'career-technical and apprenticeship-adjacent programs.',
    'Port of Pittsburgh Commission':
        'The state-chartered regional authority for the Pittsburgh '
        'district’s inland waterways, the busiest inland port system '
        'in the country by tonnage.',
    'Carnegie Mellon University':
        'Private research university in Pittsburgh’s Oakland '
        'neighborhood, known for engineering, computer science and '
        'the arts.',
    'Carrie Blast Furnaces National Historic Landmark':
        'A former U.S. Steel ironmaking plant on the Monongahela River, '
        'preserved as part of the Rivers of Steel National Heritage Area.',
    'Community College of Allegheny County':
        'A public community-college system with real career-technical '
        'and trades programs across the Pittsburgh region.',
    'Colorado School of Mines':
        'Public research university in Golden, Colorado, internationally '
        'known for mining, earth sciences and engineering.',
    'National Renewable Energy Laboratory':
        "The U.S. Department of Energy's primary national laboratory for "
        'renewable energy and energy efficiency research, based in '
        'Golden, Colorado.',
    'Denver Union Station':
        "Denver's historic 1881 rail depot, restored as the downtown "
        'hub for Amtrak, commuter rail, light rail and bus.',
    'Community College of Denver':
        'A public community college on the Auraria Campus, with real '
        'career-technical and trades programs.',
}

# CITY records - the region frames Locator.X's own maps ship, RECORDED
# verbatim: the NOLA map's region record, and the Bay Area map's committed
# frame (src/app.js), which covers both Bay campuses. A city layer may
# claim only a real frame, never an invented one; the streets, bridges and
# water drawn inside it stay SCHEMATIC and are labelled so wherever they
# render.
BAY_FRAME = {
    'center': {'lat': 37.72, 'lng': -122.27},
    'bounds': {'w': -124.2, 's': 36.2, 'e': -120.2, 'n': 39.2},
    'provenance': 'RECORDED',
    'source': 'Locator.X src/app.js map frame, Apache-2.0',
}
CITY = {
    'new-orleans': {
        'center': {'lat': 29.975, 'lng': -90.09},
        'bounds': {'w': -90.65, 's': 29.5, 'e': -89.45, 'n': 30.35},
        'provenance': 'RECORDED',
        'source': 'Locator.X build_data_nola.py region, Apache-2.0',
    },
    'treasure-island': dict(BAY_FRAME),
    'oakland': dict(BAY_FRAME),
    # the five hub campuses' own frames: AUTHORED, like their anchors and
    # their own campus-centre coordinates above - no sibling table ships a
    # committed frame for any of the five metros, so none can honestly
    # claim more
    'houston': {
        'center': {'lat': 29.76, 'lng': -95.37},
        'bounds': {'w': -95.9, 's': 29.45, 'e': -94.95, 'n': 30.15},
        'provenance': 'AUTHORED',
        'source': 'widely-published public geography (metro-area extent), '
                  'typed from general knowledge - not cross-checked '
                  'against any file this build can verify',
    },
    'chicago': {
        'center': {'lat': 41.88, 'lng': -87.63},
        'bounds': {'w': -88.05, 's': 41.62, 'e': -87.35, 'n': 42.05},
        'provenance': 'AUTHORED',
        'source': 'widely-published public geography (metro-area extent), '
                  'typed from general knowledge - not cross-checked '
                  'against any file this build can verify',
    },
    'seattle': {
        'center': {'lat': 47.60, 'lng': -122.33},
        'bounds': {'w': -122.55, 's': 47.35, 'e': -121.95, 'n': 47.85},
        'provenance': 'AUTHORED',
        'source': 'widely-published public geography (metro-area extent), '
                  'typed from general knowledge - not cross-checked '
                  'against any file this build can verify',
    },
    'pittsburgh': {
        'center': {'lat': 40.44, 'lng': -79.99},
        'bounds': {'w': -80.40, 's': 40.15, 'e': -79.60, 'n': 40.75},
        'provenance': 'AUTHORED',
        'source': 'widely-published public geography (metro-area extent), '
                  'typed from general knowledge - not cross-checked '
                  'against any file this build can verify',
    },
    'denver': {
        'center': {'lat': 39.74, 'lng': -104.99},
        'bounds': {'w': -105.35, 's': 39.45, 'e': -104.60, 'n': 40.05},
        'provenance': 'AUTHORED',
        'source': 'widely-published public geography (metro-area extent), '
                  'typed from general knowledge - not cross-checked '
                  'against any file this build can verify',
    },
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
    _c = CITY['new-orleans']
    assert f"center=[{_c['center']['lng']},{_c['center']['lat']}]" in _nola, \
        'NOLA city centre drifted from the region record'
    _b = _c['bounds']
    assert (f"maxBounds=[[{_b['w']},{_b['s']}],[{_b['e']},{_b['n']}]]"
            in _nola), 'NOLA city bounds drifted from the region record'
    _bf = CITY['treasure-island']
    assert (f"center:[{_bf['center']['lng']},{_bf['center']['lat']}]" in _lx), \
        'Bay frame centre drifted from the app source'
    _bb = _bf['bounds']
    assert (f"maxBounds:[[{_bb['w']},{_bb['s']}],[{_bb['e']},{_bb['n']}]]"
            in _lx), 'Bay frame bounds drifted from the app source'

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

# --------------------------------------------------------------- on foot ---
# A distance is only meaningful against a human pace, so the walk bands and
# the destination classes below are RECORDED from Locator.X's walk module
# (src/walk.js, Apache-2.0) rather than invented here, and cross-checked
# against that checkout when it is present. The caveat travels with them:
# this is straight-line distance, not a street-network walk, so a freeway, a
# rail cut, a canal or a gated block makes the real walk longer - sometimes
# impossibly longer.
WALK = {
    'bands_m': {'ten_minute': 800, 'fifteen_minute': 1200},
    'pace_note': 'a ten-minute walk at a normal pace is about 800 m; '
                 'fifteen minutes about 1.2 km',
    'classes': [
        {'id': 'shop', 'name': 'Shops & everyday errands'},
        {'id': 'eat', 'name': 'Eating & drinking'},
        {'id': 'work', 'name': 'Workplaces'},
        {'id': 'care', 'name': 'Health & care'},
        {'id': 'learn', 'name': 'Learning'},
        {'id': 'stay', 'name': 'Lodging & mixed use'},
    ],
    'provenance': 'RECORDED - Locator.X src/walk.js, Apache-2.0',
    'cite_file': 'src/walk.js',
    'honesty': {
        'not_a_score': 'this is not Walk Score(R) and no relationship with '
                       'it is claimed or implied.',
        'straight_line': 'distance here is straight-line between '
                         'coordinates, not a street-network walk: a '
                         'freeway, a rail cut, a canal or a gated block '
                         'makes the real walk longer, sometimes impossibly '
                         'longer. Walk the block before you believe the '
                         'number.',
        'what_it_counts': 'the Academy draws the bands around a campus and '
                          'reports which real anchors - RECORDED where a '
                          'sibling source exists to cross-check against, '
                          'AUTHORED where none does - fall inside them. '
                          'It counts no shops, because this bundle '
                          'holds no shop records - the classes above are '
                          'carried so the map can say what a walkable '
                          'measure would have to count.',
    },
}
if locx.exists():
    _w = (ROOT.parent / 'locator.x' / 'src' / 'walk.js').read_text()
    assert (f"R10={WALK['bands_m']['ten_minute']}, "
            f"R15={WALK['bands_m']['fifteen_minute']}") in _w, \
        'the walk bands drifted from the Locator.X walk module'
    for _c in WALK['classes']:
        assert f"id:'{_c['id']}'" in _w, f"walk class {_c['id']} is not in the source"
        assert f"name:'{_c['name']}'" in _w, \
            f"walk class name drifted: {_c['name']}"
    assert 'not Walk Score' in _w, 'the Walk Score disclaimer left the source'

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
    'city': CITY,
    'anchors': {},
    'walk': WALK,
}

# One real per-anchor provenance, threaded everywhere an anchor is emitted
# below - never hardcoded again the way an earlier version of this file did.
# RECORDED anchors (ANCHORS) cite the sibling Locator.X table verbatim;
# AUTHORED anchors (AUTHORED_ANCHORS) name themselves plainly as a weaker,
# uncross-checked claim - the same distinction GEO already draws between
# the three original campus centres and the five hub ones.
def anchor_source(prov, src):
    return f'Locator.X {src}, Apache-2.0' if prov == 'RECORDED' else src


def anchor_entries():
    for ck, lst in ANCHORS.items():
        for n, lat, lng, src in lst:
            yield ck, n, lat, lng, 'RECORDED', src
    for ck, lst in AUTHORED_ANCHORS.items():
        for n, lat, lng, src in lst:
            yield ck, n, lat, lng, 'AUTHORED', src


for ck, n, lat, lng, prov, src in anchor_entries():
    entry = {
        'name': n, 'lat': lat, 'lng': lng, 'provenance': prov,
        'source': anchor_source(prov, src),
        'km': round(haversine_km(GEO[ck][:2], (lat, lng)), 1),
        'bearing_deg': round(bearing_deg(GEO[ck][:2], (lat, lng)), 1),
    }
    if n in BLURBS:
        entry['blurb'] = BLURBS[n]
        entry['blurb_provenance'] = ('authored from public record' if prov == 'RECORDED'
            else 'authored from public record, the same tier as the coordinate itself')
    doc['anchors'].setdefault(ck, []).append(entry)

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
                        'provenance': prov, 'source': anchor_source(prov, src)}}
        for ck, n, lat, lng, prov, src in anchor_entries()
    ],
}

# The EXPANDED network GeoJSON - everything a Mapbox/MapLibre style needs
# in one FeatureCollection: campuses and anchors as points with their full
# provenance and blurbs, the inter-campus routes as great-circle
# LineStrings (DERIVED - sampled from the same haversine math the route
# table uses), and the RECORDED city frames as polygons. The web/geomap
# page renders exactly this file over a graticule - no third-party tiles,
# so nothing on that map exists that this registry does not state.


def great_circle(a, b, n=33):
    """Sample n points along the great circle from a to b (lat,lng)."""
    p1, l1 = math.radians(a[0]), math.radians(a[1])
    p2, l2 = math.radians(b[0]), math.radians(b[1])
    d = 2 * math.asin(math.sqrt(
        math.sin((p2 - p1) / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin((l2 - l1) / 2) ** 2))
    pts = []
    for i in range(n):
        f = i / (n - 1)
        A = math.sin((1 - f) * d) / math.sin(d)
        B = math.sin(f * d) / math.sin(d)
        x = A * math.cos(p1) * math.cos(l1) + B * math.cos(p2) * math.cos(l2)
        y = A * math.cos(p1) * math.sin(l1) + B * math.cos(p2) * math.sin(l2)
        z = A * math.sin(p1) + B * math.sin(p2)
        pts.append([round(math.degrees(math.atan2(y, x)), 4),
                    round(math.degrees(math.atan2(z, math.hypot(x, y))), 4)])
    return pts


network = {
    'type': 'FeatureCollection',
    'features': geojson['features'] + [
        {'type': 'Feature',
         'geometry': {'type': 'LineString',
                      'coordinates': great_circle(GEO[r['from']][:2],
                                                  GEO[r['to']][:2])},
         'properties': {'kind': 'route', 'from': r['from'], 'to': r['to'],
                        'km': r['km'], 'bearing_deg': r['bearing_deg'],
                        'provenance': 'DERIVED',
                        'source': 'great-circle between the campus records'}}
        for r in routes
    ] + [
        {'type': 'Feature',
         'geometry': {'type': 'Polygon', 'coordinates': [[
             [c['bounds']['w'], c['bounds']['s']],
             [c['bounds']['e'], c['bounds']['s']],
             [c['bounds']['e'], c['bounds']['n']],
             [c['bounds']['w'], c['bounds']['n']],
             [c['bounds']['w'], c['bounds']['s']]]]},
         'properties': {'kind': 'frame', 'campus': ck,
                        'provenance': c['provenance'], 'source': c['source']}}
        for ck, c in CITY.items() if ck != 'oakland'  # the Bay frame once
    ],
}
# anchors in the network file also carry their blurbs and distances
for f in network['features']:
    p = f['properties']
    if p.get('kind') == 'anchor' and p['name'] in BLURBS:
        a = next(x for x in doc['anchors'][p['near']] if x['name'] == p['name'])
        p.update({'blurb': BLURBS[p['name']], 'km': a['km'],
                  'bearing_deg': a['bearing_deg'],
                  'blurb_provenance': a['blurb_provenance']})

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'campuses_geo.json').write_text(json.dumps(doc, indent=1) + '\n')
(OUT / 'campuses.geojson').write_text(json.dumps(geojson, indent=1) + '\n')
(OUT / 'network.geojson').write_text(json.dumps(network, indent=1) + '\n')
route_txt = ', '.join('{}-{} {} km'.format(r['from'], r['to'], r['km'])
                      for r in routes)
n_recorded = sum(len(v) for v in ANCHORS.values())
n_authored = sum(len(v) for v in AUTHORED_ANCHORS.values())
print(f"geo registry: {len(GEO)} campuses, {len(routes)} routes "
      f"({route_txt}), {n_recorded} RECORDED + {n_authored} AUTHORED "
      f"anchors; {checked} (source stamp {stamp})")
