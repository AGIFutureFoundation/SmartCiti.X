#!/usr/bin/env python3
"""parishes: the geographic base of the walkable New Orleans parish world.

READS (never fetches):
  parishes/vendor/us-atlas/counties-10m.json  RECORDED Census 2017 cartographic
      boundary outlines at 1:10,000,000, packaged by us-atlas 3.0.1 (ISC) and
      vendored by parishes/fetch_usatlas.py after a sha512 integrity check.
  geo/registry/campuses_geo.json   the RECORDED NOLA frame (city.new-orleans.bounds)
      and the 7 RECORDED university anchors (anchors.new-orleans).
  parcels/registry/parcels.json    the USGS orthoimagery view-time layer (declared).
  parishes/authored/landmarks.json AUTHORED civic/public landmarks (typed, approximate).

SELECTS every Louisiana parish (state FIPS 22) whose outline intersects the
RECORDED NOLA frame - computed here and printed, never a typed list. Counties
of other states that also meet the frame are printed and recorded as
excluded (they are not parishes).

WRITES parishes/registry/parishes.json and, through parishes/render.py, the
4096x4096 maps parishes/maps/<fips>-4k.webp + <fips>-512.webp.

Fail closed: registry fields are read by subscript through need(); a missing
field stops the build with a named error. No default-taking lookups.

    python3 parishes/build.py
"""
import hashlib
import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import render  # noqa: E402

TOPO = 'parishes/vendor/us-atlas/counties-10m.json'
MANIFEST = 'parishes/vendor/us-atlas/manifest.json'
GEO = 'geo/registry/campuses_geo.json'
PARCELS = 'parcels/registry/parcels.json'
LANDMARKS = 'parishes/authored/landmarks.json'
INPUTS = ['parishes/build.py', 'parishes/render.py', TOPO, MANIFEST, GEO, PARCELS, LANDMARKS]

# the same sphere geo3d/build.py uses (EARTH_R_M): IUGG mean Earth radius
EARTH_R_M = 6371008.8
LTP_FORMULA = ('equirectangular local tangent plane about an origin (lat0, lng0): '
               'east_m = R * cos(radians(lat0)) * radians(lng - lng0); north_m = R * radians(lat - lat0); '
               'inverse: lat = lat0 + degrees(north_m / R); lng = lng0 + degrees(east_m / (R * cos(radians(lat0)))); '
               'R = 6371008.8 m (IUGG mean radius, the R of geo3d/build.py). Scene convention (geo3d): '
               'x = east_m, z = -north_m, y up. Distortion grows with distance from the origin: the east-west '
               'scale error at a point is cos(lat)/cos(lat0) - 1, computed per parish as frame.max_ew_scale_error_pct '
               '(north-south scale is exact on the sphere).')
WATER = ('The Census cartographic boundary outline is clipped to the COASTLINE only: open water on the Gulf side '
         '(Lake Borgne, Breton and Chandeleur sounds, the Gulf of Mexico, open bays) lies OUTSIDE every land outline and '
         'is drawn as water. INLAND water is NOT cut out at 1:10m: Lake Pontchartrain, Lake Maurepas, the Mississippi '
         'River and marsh open water lie INSIDE the parish outlines (parish lines run through Lake Pontchartrain, so '
         'Orleans, Jefferson and St. Tammany share borders across open water). This pack holds no inland-water polygon: '
         'inside an outline is NOT proof of land. Water is stated, not surveyed; no shoreline here is navigational.')
WATER_RULE = ('open water = inside the map but outside every land outline (Gulf side only); inland water inside the '
              'outline is unknown to this pack - label it, never pave or build on it as if it were known land')
ELEVATION = 'no real elevation: New Orleans elevation is not held by this pack; the ground is flat AUTHORED at 0 m'
PROVENANCE = {
    'outline': 'RECORDED - U.S. Census Bureau 2017 cartographic boundary file via us-atlas 3.0.1 counties-10m '
               '(1:10,000,000, quantized; coarse: expect vertex error of hundreds of metres)',
    'frame': 'RECORDED - geo/registry/campuses_geo.json city.new-orleans.bounds (Locator.X region)',
    'selection': 'DERIVED - computed outline/frame intersection, printed by the build',
    'adjacency': 'DERIVED - two parishes connect when their outlines share a TopoJSON arc',
    'area': 'DERIVED - shoelace area of the coarse land outline in the parish local metre frame',
    'landmarks': 'AUTHORED - typed from public record, approximate, not surveyed',
    'anchors': 'RECORDED - geo/registry/campuses_geo.json anchors.new-orleans',
    'maps': 'DERIVED + AUTHORED - drawn from the RECORDED outline; street fabric is AUTHORED procedural',
}


def fail(msg):
    raise SystemExit(f'parishes/build.py: {msg}')


def need(obj, key, where):
    if not isinstance(obj, dict) or key not in obj:
        fail(f'missing field {where}.{key}')
    return obj[key]


def load(p):
    f = ROOT / p
    if not f.exists():
        fail(f'missing input {p}')
    return json.loads(f.read_text())


def source_stamp():
    h = hashlib.sha256()
    for p in INPUTS:
        h.update(p.encode() + b'\0' + (ROOT / p).read_bytes() + b'\0')
    return h.hexdigest()


# ---------------------------------------------------------------- topology
def decode_arcs(topo):
    tr = need(topo, 'transform', 'topology')
    sx, sy = need(tr, 'scale', 'transform')
    tx, ty = need(tr, 'translate', 'transform')
    arcs = []
    for arc in need(topo, 'arcs', 'topology'):
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((round(x * sx + tx, 6), round(y * sy + ty, 6)))
        arcs.append(pts)
    return arcs


def arc_pts(arcs, i):
    return arcs[i] if i >= 0 else arcs[~i][::-1]


def ring_of(arcs, idxs):
    ring = []
    for i in idxs:
        pts = arc_pts(arcs, i)
        ring.extend(pts if not ring else pts[1:])
    return ring


def polygons_of(geom, arcs):
    t = need(geom, 'type', 'geometry')
    a = need(geom, 'arcs', 'geometry')
    if t == 'Polygon':
        polys = [a]
    elif t == 'MultiPolygon':
        polys = a
    else:
        fail(f'geometry type {t} not handled')
    return [[ring_of(arcs, r) for r in poly] for poly in polys]


def arc_ids(geom):
    t = need(geom, 'type', 'geometry')
    a = need(geom, 'arcs', 'geometry')
    polys = [a] if t == 'Polygon' else a
    return {(i if i >= 0 else ~i) for poly in polys for r in poly for i in r}


# ---------------------------------------------------------------- geometry
def pip(pt, ring):
    x, y = pt
    inside = False
    n = len(ring)
    for k in range(n):
        x1, y1 = ring[k]
        x2, y2 = ring[(k + 1) % n]
        if (y1 > y) != (y2 > y):
            xc = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xc > x:
                inside = not inside
    return inside


def in_polys(pt, polys):
    for poly in polys:
        if pip(pt, poly[0]) and not any(pip(pt, h) for h in poly[1:]):
            return True
    return False


def seg_cross(p1, p2, q1, q2):
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2 = orient(q1, q2, p1), orient(q1, q2, p2)
    d3, d4 = orient(p1, p2, q1), orient(p1, p2, q2)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def intersects_frame(polys, fr):
    w, s, e, n = fr['w'], fr['s'], fr['e'], fr['n']
    corners = [(w, s), (e, s), (e, n), (w, n)]
    edges = list(zip(corners, corners[1:] + corners[:1]))
    for poly in polys:
        outer = poly[0]
        if any(w <= x <= e and s <= y <= n for x, y in outer):
            return 'vertex-inside-frame'
        if any(pip(c, outer) for c in corners):
            return 'frame-corner-inside-outline'
        for a, b in zip(outer, outer[1:] + outer[:1]):
            if any(seg_cross(a, b, c, d) for c, d in edges):
                return 'edge-crossing'
    return None


def ltp(lat0, lng0):
    k = math.radians(1) * EARTH_R_M
    c = math.cos(math.radians(lat0))

    def fwd(lng, lat):
        return (round((lng - lng0) * k * c, 2), round((lat - lat0) * k, 2))
    return fwd


def ring_area_m2(ring_m):
    s = 0.0
    for (x1, y1), (x2, y2) in zip(ring_m, ring_m[1:] + ring_m[:1]):
        s += x1 * y2 - x2 * y1
    return s / 2


def centroid_ll(polys):
    """area-weighted centroid of the outer rings (holes subtracted), in degrees,
    computed in a plane about the bbox centre then taken back to degrees"""
    xs = [p[0] for poly in polys for p in poly[0]]
    ys = [p[1] for poly in polys for p in poly[0]]
    lat0, lng0 = (min(ys) + max(ys)) / 2, (min(xs) + max(xs)) / 2
    c = math.cos(math.radians(lat0))
    A = cx = cy = 0.0
    for poly in polys:
        for j, ring in enumerate(poly):
            r = [((x - lng0) * c, y - lat0) for x, y in ring]
            for (x1, y1), (x2, y2) in zip(r, r[1:] + r[:1]):
                cr = x1 * y2 - x2 * y1
                A += cr
                cx += (x1 + x2) * cr
                cy += (y1 + y2) * cr
    A /= 2
    return (round(lat0 + cy / (6 * A), 6), round(lng0 + cx / (6 * A) / c, 6))


# ---------------------------------------------------------------- build
def main():
    topo = load(TOPO)
    man = load(MANIFEST)
    geo = load(GEO)
    parcels = load(PARCELS)
    lmk = load(LANDMARKS)
    arcs = decode_arcs(topo)
    geoms = need(need(topo, 'objects', 'topology'), 'counties', 'objects')
    geoms = need(geoms, 'geometries', 'counties')
    city = need(need(geo, 'city', 'campuses_geo'), 'new-orleans', 'city')
    frame = need(city, 'bounds', 'city.new-orleans')
    for k in ('w', 's', 'e', 'n'):
        need(frame, k, 'city.new-orleans.bounds')
    if need(city, 'provenance', 'city.new-orleans') != 'RECORDED':
        fail('city.new-orleans.bounds is not RECORDED')
    center = need(city, 'center', 'city.new-orleans')
    world_origin = (need(center, 'lat', 'center'), need(center, 'lng', 'center'))

    by_id = {}
    for g in geoms:
        gid = need(g, 'id', 'geometry')
        by_id[gid] = g
    selected, excluded = [], []
    print(f'NOLA frame (RECORDED) w={frame["w"]} s={frame["s"]} e={frame["e"]} n={frame["n"]}')
    for gid, g in sorted(by_id.items()):
        polys = polygons_of(g, arcs)
        how = intersects_frame(polys, frame)
        if how is None:
            continue
        name = need(need(g, 'properties', gid), 'name', gid)
        if gid.startswith('22'):
            selected.append((gid, name, how))
        else:
            excluded.append({'fips': gid, 'name': name, 'why': 'not a Louisiana parish (state FIPS '
                             + gid[:2] + '); intersects the frame by ' + how})
    for gid, name, how in selected:
        print(f'  selected {gid} {name} Parish ({how})')
    for x in excluded:
        print(f'  excluded {x["fips"]} {x["name"]} - {x["why"]}')
    sel_ids = [s[0] for s in selected]

    # arc -> owners (every county in the atlas), for adjacency and neighbours
    owners = {}
    for gid, g in by_id.items():
        for a in arc_ids(g):
            owners.setdefault(a, set()).add(gid)

    wfwd = ltp(*world_origin)
    parishes = {}
    for gid, name, how in selected:
        g = by_id[gid]
        polys = polygons_of(g, arcs)
        lat0, lng0 = centroid_ll(polys)
        fwd = ltp(lat0, lng0)
        outline_m = [[[fwd(x, y) for x, y in ring] for ring in poly] for poly in polys]
        area = 0.0
        for poly in outline_m:
            area += abs(ring_area_m2(poly[0])) - sum(abs(ring_area_m2(h)) for h in poly[1:])
        mine = arc_ids(g)
        adj, outside, borders = [], [], []
        nbrs = sorted({o for a in mine for o in owners[a] if o != gid})
        for nb in nbrs:
            shared = sorted(a for a in mine if nb in owners[a])
            nbname = need(need(by_id[nb], 'properties', nb), 'name', nb)
            if nb in sel_ids:
                adj.append(nb)
                segs = []
                for a in shared:
                    pts = arcs[a]
                    segs.append({'arc': a, 'wgs84': [[x, y] for x, y in pts],
                                 'world_m': [list(wfwd(x, y)) for x, y in pts],
                                 'local_m': [list(fwd(x, y)) for x, y in pts]})
                borders.append({'with': nb, 'segments': segs,
                                'length_m': round(sum(math.dist(p, q) for s in segs
                                                      for p, q in zip(s['local_m'], s['local_m'][1:])), 1)})
            else:
                outside.append({'fips': nb, 'name': nbname, 'shared_arcs': len(shared),
                                'selected': False})
        parishes[gid] = {
            'fips': gid, 'name': name, 'full_name': f'{name} Parish',
            'selected_because': how,
            'outline': {'crs': 'WGS84 (EPSG:4326), [lng, lat]', 'provenance': PROVENANCE['outline'],
                        'polygons': [[[[x, y] for x, y in ring] for ring in poly] for poly in polys],
                        'rings': sum(len(p) for p in polys), 'vertices': sum(len(r) for p in polys for r in p)},
            'frame': {'origin': {'lat': lat0, 'lng': lng0, 'what': 'area-weighted centroid of the coarse outline'},
                      'formula': 'see registry.frames.ltp_formula', 'R_m': EARTH_R_M,
                      'max_ew_scale_error_pct': round(100 * max(abs(math.cos(math.radians(y)) / math.cos(math.radians(lat0)) - 1)
                                                               for poly in polys for r in poly for x, y in r), 3),
                      'origin_in_world_m': list(wfwd(lng0, lat0))},
            'outline_local_m': [[[list(p) for p in ring] for ring in poly] for poly in outline_m],
            'outline_world_m': [[[list(wfwd(x, y)) for x, y in ring] for ring in poly] for poly in polys],
            'bbox_wgs84': [min(p[0] for q in polys for p in q[0]), min(p[1] for q in polys for p in q[0]),
                           max(p[0] for q in polys for p in q[0]), max(p[1] for q in polys for p in q[0])],
            'area_km2': round(area / 1e6, 1),
            'area_note': 'area inside the coarse 1:10m cartographic outline (coastline-clipped; INCLUDES inland water such as '
                         'Lake Pontchartrain where the outline runs through it); not the official Census land or total area',
            'adjacent': adj, 'borders': borders, 'neighbours_not_selected': outside,
            'water': 'see registry.water',
            'landmarks': [], 'anchors': [],
        }

    # landmarks (AUTHORED) and anchors (RECORDED): kept only when inside the outline
    dropped = []
    lnote = need(lmk, 'note', 'landmarks')
    if need(lmk, 'provenance', 'landmarks') != 'AUTHORED':
        fail('landmarks.json must be AUTHORED')
    for L in need(lmk, 'landmarks', 'landmarks'):
        p = need(L, 'parish', 'landmark')
        nm = need(L, 'name', 'landmark')
        pt = (need(L, 'lng', nm), need(L, 'lat', nm))
        if p not in parishes:
            dropped.append({'name': nm, 'parish': p, 'why': 'its parish is not in the selected set'})
            continue
        polys = parishes[p]['outline']['polygons']
        if not in_polys(pt, polys):
            dropped.append({'name': nm, 'parish': p, 'why': 'its approximate point falls outside the coarse '
                            '1:10m outline (dropped, not moved)'})
            continue
        fr = parishes[p]['frame']['origin']
        e, n = ltp(fr['lat'], fr['lng'])(*pt)
        parishes[p]['landmarks'].append({
            'name': nm, 'kind': need(L, 'kind', nm), 'lat': pt[1], 'lng': pt[0],
            'local_m': [e, n], 'world_m': list(wfwd(*pt)),
            'provenance': 'AUTHORED', 'note': lnote})
    for A in need(need(geo, 'anchors', 'campuses_geo'), 'new-orleans', 'anchors'):
        nm = need(A, 'name', 'anchor')
        pt = (need(A, 'lng', nm), need(A, 'lat', nm))
        home = [p for p in parishes if in_polys(pt, parishes[p]['outline']['polygons'])]
        if len(home) != 1:
            fail(f'anchor {nm} lies in {len(home)} selected outlines')
        p = home[0]
        fr = parishes[p]['frame']['origin']
        parishes[p]['anchors'].append({
            'name': nm, 'kind': 'university', 'lat': pt[1], 'lng': pt[0],
            'local_m': list(ltp(fr['lat'], fr['lng'])(*pt)), 'world_m': list(wfwd(*pt)),
            'provenance': need(A, 'provenance', nm), 'source': need(A, 'source', nm)})
    for d in dropped:
        print(f'  dropped landmark {d["name"]} ({d["parish"]}): {d["why"]}')

    # view-time satellite layers: declared, never fetched here
    img = need(parcels, 'imagery', 'parcels')
    sat = {
        'fetched_at_build': False, 'stored': False,
        'rule': 'view-time only, in the learner\'s browser; never fetched, stored or baked by any build; '
                'the 4k maps contain no imagery',
        'usgs': {'id': need(img, 'id', 'imagery'), 'tiles': need(img, 'tiles', 'imagery'),
                 'scheme': need(img, 'scheme', 'imagery'), 'zoom': need(img, 'zoom', 'imagery'),
                 'tile_size': need(img, 'tile_size', 'imagery'),
                 'attribution': need(img, 'attribution', 'imagery'), 'licence': need(img, 'licence', 'imagery'),
                 'source': 'parcels/registry/parcels.json#imagery', 'token': None,
                 'when_unavailable': 'fall back to the drawn 4k map; say "USGS imagery did not answer"'},
        'mapbox': {'tiles': 'https://api.mapbox.com/v4/mapbox.satellite/{z}/{x}/{y}@2x.jpg90?access_token={token}',
                   'scheme': 'xyz', 'tile_size': 512, 'zoom': {'min': 0, 'max': 19},
                   'token_from': 'deploy-time runtime config: GET ./config/runtime.json -> {"mapbox_token": "pk..."}, '
                                 'written at deploy from the operator env var MAPBOX_PUBLIC_TOKEN; never committed',
                   'token_rules': ['public pk. token only (never an sk. secret token)',
                                   'URL-restricted to the deployment origin by the operator',
                                   'absent, empty, unreadable or not starting "pk." => layer OFF'],
                   'attribution': '© Mapbox and its imagery providers - show Mapbox\'s required attribution '
                                  'when the layer is on (operator: verify against Mapbox\'s current terms)',
                   'refusal_text': 'Mapbox satellite: off - no token configured',
                   'configured_here': False,
                   'verified_from_build': False,
                   'verification_note': 'api.mapbox.com is blocked from the build environment and no token exists '
                                        'here, so this endpoint is declared, not probed'},
    }

    water_labels = []
    for W in need(lmk, 'water_labels', 'landmarks'):
        nm = need(W, 'name', 'water_label')
        pt = (need(W, 'lng', nm), need(W, 'lat', nm))
        water_labels.append({'name': nm, 'lat': pt[1], 'lng': pt[0], 'world_m': list(wfwd(*pt)),
                             'inside_outline_of': [p for p in parishes if in_polys(pt, parishes[p]['outline']['polygons'])],
                             'provenance': 'AUTHORED', 'note': need(W, 'note', nm)})

    stamp = source_stamp()
    maps = render.render_all(ROOT, parishes, by_id, arcs, polygons_of, ltp, frame, water_labels, stamp)
    for gid in parishes:
        mp = maps[gid]
        ex = mp['extent_wgs84']
        mp['corners_world_m'] = {'nw': list(wfwd(ex[0], ex[3])), 'ne': list(wfwd(ex[2], ex[3])),
                                 'se': list(wfwd(ex[2], ex[1])), 'sw': list(wfwd(ex[0], ex[1])),
                                 'note': 'the map is square in its LOCAL frame; in the world frame its corners are '
                                         'these (a slight trapezoid, the cos(lat0) difference) - place by corners'}
        parishes[gid]['map'] = mp
    reg = {
        'pack': 'parishes', 'pack_version': need(load('pack/manifest.json'), 'pack_version', 'manifest'),
        'source_stamp': stamp[:16], 'source_stamp_sha256': stamp, 'inputs': INPUTS,
        'provenance_tiers': ['RECORDED', 'DERIVED', 'AUTHORED'],
        'provenance': PROVENANCE,
        'source': {'package': need(man, 'package', 'manifest'), 'version': need(man, 'version', 'manifest'),
                   'integrity': need(man, 'integrity', 'manifest'), 'license': need(man, 'license', 'manifest'),
                   'data_origin': need(man, 'data_origin', 'manifest'),
                   'file': TOPO, 'file_sha256': need(need(need(man, 'files', 'manifest'), 'counties-10m.json',
                                                           'files'), 'sha256', 'counties-10m.json')},
        'nola_frame': {'bounds': frame, 'source': GEO + '#city.new-orleans.bounds',
                       'provenance': PROVENANCE['frame']},
        'selection': {'rule': 'every Louisiana parish (state FIPS 22) whose RECORDED outline intersects the '
                              'RECORDED NOLA frame (any vertex inside, any frame corner inside, or any edge crossing)',
                      'selected': sel_ids, 'excluded_non_parish': excluded,
                      'provenance': PROVENANCE['selection']},
        'frames': {'ltp_formula': LTP_FORMULA, 'R_m': EARTH_R_M,
                   'world': {'origin': {'lat': world_origin[0], 'lng': world_origin[1]},
                             'source': GEO + '#city.new-orleans.center',
                             'what': 'one shared metre frame for every parish so maps and borders connect; '
                                     'world_m values are [east_m, north_m] in it'},
                   'local': 'per parish: origin = parish.frame.origin; local_m values are [east_m, north_m]'},
        'water': {'statement': WATER, 'rule': WATER_RULE, 'inland_water_cut_out': False,
                  'labels': water_labels},
        'elevation': ELEVATION,
        'landmarks_rules': need(lmk, 'rules', 'landmarks'), 'landmarks_method': need(lmk, 'method', 'landmarks'),
        'landmarks_dropped': dropped,
        'satellite': sat,
        'counts': {'parishes': len(parishes), 'excluded_non_parish': len(excluded),
                   'adjacency_pairs': sum(len(p['adjacent']) for p in parishes.values()) // 2,
                   'landmarks': sum(len(p['landmarks']) for p in parishes.values()),
                   'landmarks_dropped': len(dropped),
                   'anchors': sum(len(p['anchors']) for p in parishes.values()),
                   'maps_4k': len(maps)},
        'parishes': parishes,
    }
    out = ROOT / 'parishes' / 'registry' / 'parishes.json'
    out.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + '\n')
    print(f'wrote {out.relative_to(ROOT)}: {reg["counts"]} stamp {stamp[:16]}')
    # v1.4 (wave 7): the world layer is derived from the registry + streets just written, so rebuild it here
    import build_world
    build_world.main()


if __name__ == '__main__':
    main()
