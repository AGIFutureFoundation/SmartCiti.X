"""terrain/ - the real shape of the ground under each of the ten campuses.

Every map in this bundle has drawn true coordinates over a generated
graticule. The anchors were right and the world around them was a grid: a
campus on a bay and a campus on a prairie were the same flat plane with
different labels. This pack turns the vendored Natural Earth outlines into
something the pages can draw, so Oakland gets the estuary it actually sits
on and Denver gets the fact that it has no coast at all.

Three products, because three surfaces need different things:

  ll      degrees, for the 2D WGS84 geomap, which is already in degrees
  local   metres east/north of the campus anchor, for the 3D city layer
  mask    a land/water bit grid, which is the custom ground texture

The mask is the part worth explaining. "Use custom textures to make the
maps realistic" has an obvious wrong answer - fetch a satellite tile - and
this bundle cannot take it: nothing here fetches at run time, and an aerial
tile carries a licence that a public-domain vector does not. So the texture
is DERIVED instead of downloaded. Each campus gets a grid of bits over its
local window, each bit answering "is this square metre of ground land?",
computed by point-in-polygon against the real coastline. The page builds a
texture from it at load. The shoreline in the 3D world is then the true
shoreline, at the resolution the grid can carry, and the resolution is
published here rather than implied.

What this is NOT: elevation. Natural Earth is a vector outline set; there
is no height in it. The bundle's existing elevation lookups are a separate,
recorded thing and this pack does not touch or restate them.

Nothing here fetches. terrain/fetch_terrain.py did that once, by hand, and
its output is committed with a hash manifest. This reads those files and
fails closed if any byte has moved.
"""
import hashlib
import json
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
VENDOR = HERE / 'vendor'
OUT = HERE / 'registry' / 'terrain.json'

# One bundle version, read from the manifest rather than typed here.
PACK_VERSION = json.loads(
    (ROOT / 'pack' / 'manifest.json').read_text())['pack_version']

# The local window the 3D city layer can see. Half-width, metres. A campus
# is about 600 m across; the sky ring sits far beyond that, and a shoreline
# 6 km out is the thing that reads as "this place is on a bay" from inside
# the campus. Beyond 6 km the 10m source has less to say than the drawing
# would imply.
LOCAL_HALF_M = 6000.0

# The mask grid. 96 across the 12 km window is 125 m per cell: enough for a
# bay's shape, not enough for a pier, and the pack says so rather than
# letting a reader assume otherwise.
MASK_N = 96

# Douglas-Peucker tolerance, metres. The 10m source's own vertex spacing in
# these windows runs to hundreds of metres, so 40 m removes collinear runs
# without inventing or destroying a headland.
SIMPLIFY_M = 40.0

M_PER_DEG_LAT = 111_320.0

LAYERS = ('coastline', 'land', 'lakes', 'rivers')


def need(d, key, what):
    """Read a key that must be there. A missing one names itself and says
    what was actually present - a default here would be a policy decision
    about someone's coastline."""
    if key not in d:
        raise KeyError('terrain: %s: no key %r (it holds %r)'
                       % (what, key, sorted(d)[:12]))
    return d[key]


# ---------------------------------------------------------------------------
# inputs, verified

manifest = json.loads((VENDOR / 'manifest.json').read_text())
files = need(manifest, 'files', 'vendor/manifest.json')
campus_keys = need(manifest, 'campuses', 'vendor/manifest.json')

raw = {}
for layer in LAYERS:
    name = 'ne_%s.json' % layer
    body = (VENDOR / name).read_bytes()
    got = hashlib.sha256(body).hexdigest()
    want = need(need(files, name, 'vendor/manifest.json#files'), 'sha256',
                'vendor/manifest.json#files[%s]' % name)
    if got != want:
        raise SystemExit('terrain: %s has changed since it was vendored\n'
                         '  manifest %s\n  on disk  %s\n'
                         '  re-run terrain/fetch_terrain.py --check'
                         % (name, want, got))
    raw[layer] = json.loads(body)

geo = json.loads((ROOT / 'geo' / 'registry' / 'campuses_geo.json').read_text())
# campuses[] is the campus centroid; anchors[] is the list of recorded
# nearby cities, which is a different question and belongs to geo/.
sites = need(geo, 'campuses', 'geo/registry/campuses_geo.json')


# ---------------------------------------------------------------------------
# geometry

def to_local(lng, lat, lat0, lng0):
    """Equirectangular about the anchor. Over a 12 km window the error
    against a proper projection is under a metre, which is well inside the
    125 m the mask can resolve."""
    return ((lng - lng0) * M_PER_DEG_LAT * math.cos(math.radians(lat0)),
            (lat - lat0) * M_PER_DEG_LAT)


def seg_dist(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    den = dx * dx + dy * dy
    if den == 0.0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / den))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def simplify(pts, tol):
    """Douglas-Peucker, iterative so a 200-point ring cannot recurse into a
    stack limit on someone else's machine."""
    if len(pts) < 3:
        return list(pts)
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        if j - i < 2:
            continue
        worst, at = -1.0, -1
        for k in range(i + 1, j):
            d = seg_dist(pts[k], pts[i], pts[j])
            if d > worst:
                worst, at = d, k
        if worst > tol:
            keep[at] = True
            stack.append((i, at))
            stack.append((at, j))
    return [p for p, k in zip(pts, keep) if k]


def clip_to_window(pts, half):
    """Cut a polyline into the runs that fall inside the local window. A
    line that leaves and comes back returns as two runs, not one chord
    across the middle of the map."""
    runs, cur = [], []
    for p in pts:
        if abs(p[0]) <= half and abs(p[1]) <= half:
            cur.append(p)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return [r for r in runs if len(r) >= 2]


def rings_of(feature):
    """Every closed ring in a feature, whatever its geometry type. Holes
    come through as rings too, which is correct for an even-odd test."""
    g = need(feature, 'geometry', 'a vendored feature')
    t = need(g, 'type', 'a vendored geometry')
    c = need(g, 'coordinates', 'a vendored geometry')
    if t == 'Polygon':
        return list(c)
    if t == 'MultiPolygon':
        return [r for poly in c for r in poly]
    raise ValueError('terrain: land layer carried a %s, which this pack '
                     'does not know how to fill' % t)


def lines_of(feature):
    g = need(feature, 'geometry', 'a vendored feature')
    t = need(g, 'type', 'a vendored geometry')
    c = need(g, 'coordinates', 'a vendored geometry')
    if t == 'LineString':
        return [c]
    if t == 'MultiLineString':
        return list(c)
    if t == 'Polygon':
        return list(c)
    if t == 'MultiPolygon':
        return [r for poly in c for r in poly]
    raise ValueError('terrain: line layer carried a %s' % t)


def inside(x, y, rings):
    """Even-odd ray cast. Holes reverse it by construction, so a lake
    inside an island inside a lake comes out right without a special case."""
    hit = False
    for ring in rings:
        n = len(ring)
        j = n - 1
        for i in range(n):
            xi, yi = ring[i]
            xj, yj = ring[j]
            if (yi > y) != (yj > y):
                if x < xi + (xj - xi) * (y - yi) / (yj - yi):
                    hit = not hit
            j = i
    return hit


def campus_features(layer, ck):
    cs = need(raw[layer], 'campuses', 'vendor/ne_%s.json' % layer)
    return need(need(cs, ck, 'vendor/ne_%s.json#campuses' % layer),
                'features', 'vendor/ne_%s.json#campuses[%s]' % (layer, ck))


# ---------------------------------------------------------------------------
# per campus

campuses = {}
for ck in campus_keys:
    a = need(sites, ck, 'geo/registry/campuses_geo.json#campuses')
    lat0 = float(need(a, 'lat', 'campus centroid %s' % ck))
    lng0 = float(need(a, 'lng', 'campus centroid %s' % ck))

    def proj(ring):
        return [to_local(p[0], p[1], lat0, lng0) for p in ring]

    # Land rings in local metres. These drive both the fill and the mask,
    # so they are NOT clipped to the window - a ring clipped to the window
    # is open, and an open ring cannot answer "is this point inside".
    land_rings = [proj(r) for f in campus_features('land', ck)
                  for r in rings_of(f)]
    lake_rings = [proj(r) for f in campus_features('lakes', ck)
                  for r in rings_of(f)]

    coast = []
    for f in campus_features('coastline', ck):
        for ln in lines_of(f):
            for run in clip_to_window(proj(ln), LOCAL_HALF_M):
                s = simplify(run, SIMPLIFY_M)
                if len(s) >= 2:
                    coast.append([[round(x, 1), round(y, 1)] for x, y in s])

    rivers = []
    for f in campus_features('rivers', ck):
        for ln in lines_of(f):
            for run in clip_to_window(proj(ln), LOCAL_HALF_M):
                s = simplify(run, SIMPLIFY_M)
                if len(s) >= 2:
                    rivers.append([[round(x, 1), round(y, 1)] for x, y in s])

    lakes = []
    for r in lake_rings:
        for run in clip_to_window(r, LOCAL_HALF_M):
            s = simplify(run, SIMPLIFY_M)
            if len(s) >= 3:
                lakes.append([[round(x, 1), round(y, 1)] for x, y in s])

    # The mask. Cell centres, so no cell is decided by a point on its own
    # edge. A cell is land when it is inside a land ring and not inside a
    # lake - which is what makes an inland campus beside a lake read
    # correctly rather than as solid ground.
    step = 2.0 * LOCAL_HALF_M / MASK_N
    rows, land_cells = [], 0
    for j in range(MASK_N):
        y = -LOCAL_HALF_M + (j + 0.5) * step
        bits = 0
        for i in range(MASK_N):
            x = -LOCAL_HALF_M + (i + 0.5) * step
            if inside(x, y, land_rings) and not inside(x, y, lake_rings):
                bits |= 1 << i
                land_cells += 1
        rows.append('%0*x' % (MASK_N // 4, bits))

    # Distance and bearing to the nearest drawn water edge, from the anchor.
    # Measured to the nearest point ON a segment, not to the nearest
    # VERTEX. The first draft measured vertices and put Treasure Island -
    # an island - 3,195 m from water, because the 10m source's vertices in
    # that window are kilometres apart and the campus sits beside the middle
    # of a long edge, not beside a corner of it. A vertex distance is an
    # upper bound on the real one and reads like a measurement.
    edges = coast + lakes + rivers
    near_m, near_bearing = None, None
    for line in edges:
        for a2, b in zip(line, line[1:]):
            (ax, ay), (bx, by) = a2, b
            dx, dy = bx - ax, by - ay
            den = dx * dx + dy * dy
            t = 0.0 if den == 0.0 else max(0.0, min(
                1.0, (-ax * dx - ay * dy) / den))
            cx, cy = ax + t * dx, ay + t * dy
            d = math.hypot(cx, cy)
            if near_m is None or d < near_m:
                near_m = d
                near_bearing = (math.degrees(math.atan2(cx, cy)) + 360.0) % 360.0

    # The same question asked of the MASK, which is a different question
    # and gets a different answer. A drawn line and a filled cell disagree
    # in both directions, so both are published:
    #
    #   Chicago has no coastline feature and no lake feature in its window,
    #   yet 40% of its mask is water - Lake Michigan is the ABSENCE of a
    #   land polygon there, not the presence of a water one. Asking only
    #   the lines would have this campus report no water at all.
    #
    #   New Orleans has the Mississippi 1.1 km away and a mask that is 100%
    #   land - a river is a LINE in this source and has no width, so it can
    #   never darken a cell. Asking only the mask would have this campus
    #   report no water at all.
    #
    # One pack publishing one number here would have been wrong for one of
    # the two, and confidently.
    # Is the campus itself standing on land, according to the mask? At
    # 1:10,000,000 this is not rhetorical: downtown Miami and downtown
    # Detroit both fall on the water side of the source's own line. Any
    # page that cut a hole in the ground wherever the mask says water
    # would drop two of the ten campuses into a bay. The pack measures it
    # and says which, rather than leaving a renderer to discover it.
    mid = MASK_N // 2
    anchor_land = bool(int(rows[mid], 16) >> mid & 1)

    # And how far the anchor is from the nearest cell that DISAGREES with
    # it - the radius inside which the mask is saying one uniform thing.
    # A renderer that wants the mask should stay outside this.
    boundary_m = None
    for j in range(MASK_N):
        bits = int(rows[j], 16)
        y = -LOCAL_HALF_M + (j + 0.5) * step
        for i in range(MASK_N):
            if bool(bits >> i & 1) is anchor_land:
                continue
            x = -LOCAL_HALF_M + (i + 0.5) * step
            d = math.hypot(x, y)
            if boundary_m is None or d < boundary_m:
                boundary_m = d

    near_cell_m, near_cell_bearing, water_cells = None, None, 0
    for j in range(MASK_N):
        bits = int(rows[j], 16)
        y = -LOCAL_HALF_M + (j + 0.5) * step
        for i in range(MASK_N):
            if bits >> i & 1:
                continue
            water_cells += 1
            x = -LOCAL_HALF_M + (i + 0.5) * step
            d = math.hypot(x, y)
            if near_cell_m is None or d < near_cell_m:
                near_cell_m = d
                near_cell_bearing = (math.degrees(math.atan2(x, y))
                                     + 360.0) % 360.0

    coast_km = sum(
        math.hypot(b[0] - a2[0], b[1] - a2[1])
        for line in coast for a2, b in zip(line, line[1:])) / 1000.0

    campuses[ck] = {
        'anchor': {'lat': lat0, 'lng': lng0},
        'local': {
            'half_m': LOCAL_HALF_M,
            'coast': coast,
            'lakes': lakes,
            'rivers': rivers,
        },
        'mask': {
            'n': MASK_N,
            'cell_m': round(step, 2),
            'rows': rows,
            'land_share': round(land_cells / float(MASK_N * MASK_N), 4),
        },
        'facts': {
            'coast_km_in_window': round(coast_km, 2),
            'coast_runs': len(coast),
            'river_runs': len(rivers),
            'lake_rings': len(lakes),
            'nearest_water_edge_m': (None if near_m is None
                                     else round(near_m, 1)),
            'nearest_water_edge_bearing_deg': (None if near_bearing is None
                                               else round(near_bearing, 1)),
            'nearest_water_cell_m': (None if near_cell_m is None
                                     else round(near_cell_m, 1)),
            'nearest_water_cell_bearing_deg': (
                None if near_cell_bearing is None
                else round(near_cell_bearing, 1)),
            'water_cells': water_cells,
            'anchor_on_land': anchor_land,
            'anchor_to_mask_boundary_m': (None if boundary_m is None
                                          else round(boundary_m, 1)),
            # Either signal counts. Neither alone is enough - see the two
            # worked cases above the computation.
            'waterfront': bool(near_m is not None or near_cell_m is not None),
        },
    }

# ---------------------------------------------------------------------------

_stamp_src = pathlib.Path(__file__).read_bytes()
_stamp_src += (VENDOR / 'manifest.json').read_bytes()
stamp = hashlib.sha256(_stamp_src).hexdigest()[:16]

_wet_anchor = sorted(k for k, c in campuses.items()
                     if not c['facts']['anchor_on_land'])
_water = [k for k, c in campuses.items() if c['facts']['waterfront']]
_dry = [k for k, c in campuses.items() if not c['facts']['waterfront']]

HONESTY = {
    'status': 'DERIVED: every line and every bit here is computed from the '
              'Natural Earth 10m vectors vendored in terrain/vendor, whose '
              'licence is one sentence and whose hash is checked on every '
              'build. Nothing is drawn from imagination and nothing is '
              'fetched at run time.',
    'resolution': 'The source is 1:10,000,000. Its vertices in these '
                  'windows are hundreds of metres apart, so a shoreline '
                  'here is the shape of a bay and not the shape of a pier. '
                  'The mask resolves %d m per cell. A map that zoomed past '
                  'that would be drawing confidence this data does not '
                  'have.' % round(2.0 * LOCAL_HALF_M / MASK_N),
    'two_water_signals': 'Every campus reports water twice: the distance '
                         'to a drawn line, and the distance to a water '
                         'cell in the mask. They disagree by design. '
                         'Chicago has no water LINE in its window and a '
                         'mask that is 40% water, because Lake Michigan is '
                         'where the land polygon stops. New Orleans has the '
                         'Mississippi 1.1 km away and a mask that is 100% '
                         'land, because a river in this source is a line '
                         'with no width. A pack that published one figure '
                         'would have been confidently wrong about one of '
                         'them.',
    'the_anchors_in_water': 'The mask puts %d of the ten campus anchors on '
                            'a water cell (%s). Neither is a mistake in the '
                            'data or in this build - both cities meet their '
                            'water within one 125 m cell of downtown, and a '
                            '1:10,000,000 line drawn through them lands on '
                            'the wrong side. The consequence is concrete: a '
                            'renderer that cut the ground away wherever this '
                            'mask says water would drop those two campuses '
                            'into a bay. Every campus publishes '
                            'anchor_on_land and the radius out to the first '
                            'cell that disagrees with it, so a page can use '
                            'the mask for the far ground and leave the '
                            'campus alone.'
                            % (len(_wet_anchor), ', '.join(_wet_anchor)),
    'no_elevation': 'There is no height in this pack. Natural Earth is an '
                    'outline set. The ground is still flat; what changed '
                    'is where it stops being ground.',
    'no_addresses': 'No street, address or parcel is in here. The Locator.X '
                    'checkout that carries per-address Bay records keeps '
                    'them out of git on purpose - its own data/README.md '
                    'says several upstream feeds carry owner PII that a '
                    'committed mirror would preserve forever. This pack '
                    'takes the public-domain outlines instead and says so.',
    'dry_campuses': 'Of the ten, %d have water inside the %d km window and '
                    '%d do not (%s). The dry ones get no shoreline rather '
                    'than a decorative one.'
                    % (len(_water), int(LOCAL_HALF_M / 1000), len(_dry),
                       ', '.join(sorted(_dry)) if _dry else 'none'),
}

payload = {
    'pack': 'terrain',
    'product': 'real land and water outlines around the ten campuses, in '
               'local metres, with a derived land/water mask per campus',
    'pack_version': PACK_VERSION,
    'source_stamp': stamp,
    'source': need(manifest, 'source', 'vendor/manifest.json'),
    'licence': need(manifest, 'licence', 'vendor/manifest.json'),
    'licence_sha256': need(manifest, 'licence_sha256',
                           'vendor/manifest.json'),
    'honesty': HONESTY,
    'counts': {
        'campuses': len(campuses),
        'waterfront': len(_water),
        'inland': len(_dry),
        'coast_runs': sum(c['facts']['coast_runs'] for c in campuses.values()),
        'river_runs': sum(c['facts']['river_runs'] for c in campuses.values()),
        'lake_rings': sum(c['facts']['lake_rings'] for c in campuses.values()),
        'coast_points': sum(len(l) for c in campuses.values()
                            for l in c['local']['coast']),
        'anchors_in_water': len(_wet_anchor),
        'mask_cells': len(campuses) * MASK_N * MASK_N,
        'mask_water_cells': sum(c['facts']['water_cells']
                                for c in campuses.values()),
        'mask_n': MASK_N,
        'cell_m': round(2.0 * LOCAL_HALF_M / MASK_N, 2),
        'simplify_m': SIMPLIFY_M,
        'local_half_m': LOCAL_HALF_M,
    },
    'campuses': campuses,
}

assert 'AI-SYNTH' not in json.dumps(payload).upper().replace('-', '-'), \
    'terrain: that word belongs to orbis/'
assert 'http://' not in json.dumps(payload), 'terrain: no run-time fetch'

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, indent=1, sort_keys=True) + '\n')
assert len(_wet_anchor) == 2, (
    'terrain: the honesty note says two anchors fall in the water and names '
    'them; it is written from this list, so if the count moved the note has '
    'to be re-read rather than re-rendered')

print('terrain: %d campuses, %d waterfront, %d inland; %d coast runs '
      '(%d points), %d river runs, %d lake rings; mask %dx%d at %.0f m/cell; '
      '%d bytes'
      % (len(campuses), len(_water), len(_dry),
         payload['counts']['coast_runs'], payload['counts']['coast_points'],
         payload['counts']['river_runs'], payload['counts']['lake_rings'],
         MASK_N, MASK_N, payload['counts']['cell_m'],
         OUT.stat().st_size),
      end='')
print('; %d of %d mask cells are water; %d campus anchors fall on water (%s)'
      % (payload['counts']['mask_water_cells'], payload['counts']['mask_cells'],
         len(_wet_anchor), ', '.join(_wet_anchor)))
