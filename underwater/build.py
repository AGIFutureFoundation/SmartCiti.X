#!/usr/bin/env python3
"""underwater/build.py -> underwater/registry/underwater.json

Per water body of the parish world files (parishes/maps/world/*.json) and the Bay world files
(bayarea/maps/world/*.json), plus the Bay's open water, an AUTHORED bathymetry grid (depth in
decimetres below the water surface), a substrate class per cell, generic habitat set dressing
(eelgrass, oyster reef, riprap patches; mudflat is a substrate) and visibility/light parameters.

Honesty: NO real bathymetry is held in this repo, so every depth is AUTHORED (procedural, legended).
Shorelines are RECORDED only where the vendored Natural Earth 10m clip (terrain/vendor, public domain,
1:10,000,000, coarse) covers them: ne_lakes (new-orleans clip) for the two NE lake polygons that contain
the parish world files' Lake Pontchartrain / Lake Maurepas stand-in centres, and ne_land (oakland clip)
whose complement inside BAY's DERIVED bay frame is the Bay open water mask. Everything else is AUTHORED.

Deterministic: no clock, no randomness beyond a sha256 hash of ids. Fail closed: a missing key raises.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'underwater.json'
MAX_BYTES = 1_500_000
R_M = 6371008.8   # the LTP R of parishes/registry/parishes.json frames.ltp_formula

HONESTY = ("Underwater depths, substrates and habitats are AUTHORED: no real bathymetry is held, so this is not a "
           "chart and not for navigation. Shorelines are RECORDED only where the Natural Earth 10m vendor clip covers "
           "them (1:10,000,000, coarse). Eelgrass, oyster reef, mudflat and riprap are generic set dressing at "
           "AUTHORED places, not surveyed beds. Dive and ROV here are a game camera for monitoring practice - not "
           "dive training and not dive-safety instruction. Animals are never harmed.")
LEGEND = {
    'depth': 'AUTHORED - procedural depth grid, decimetres below the water surface; no real bathymetry is held',
    'substrate': 'AUTHORED - class per cell from AUTHORED depth + a hash of the body id',
    'habitat': 'AUTHORED - generic set dressing placements, not surveyed beds',
    'shoreline_recorded': 'RECORDED - Natural Earth 10m (public domain), 1:10,000,000 scale, vendored clip terrain/vendor',
    'shoreline_authored': 'AUTHORED - the world file polygon (procedural stand-in)',
}
SUBSTRATES = ['mudflat', 'mud', 'sand', 'shell', 'riprap']   # index = code in the grids
HABITATS = {
    'eelgrass': {'substrates': ['sand', 'mud'], 'depth_dm': [8, 40], 'note': 'generic seagrass bed set dressing'},
    'oyster': {'substrates': ['shell'], 'depth_dm': [10, 60], 'note': 'generic oyster reef set dressing'},
    'riprap': {'substrates': ['riprap'], 'depth_dm': [0, 30], 'note': 'generic rock revetment set dressing'},
}
VIS = {   # AUTHORED look per body kind (the kit reads these fields directly)
    'bay': {'visibility_m': 6.0, 'fog_density': 0.16, 'tint': '#3d6b63', 'light_falloff_per_m': 0.09, 'caustic': 0.35},
    'lake': {'visibility_m': 3.5, 'fog_density': 0.26, 'tint': '#5a6a3c', 'light_falloff_per_m': 0.14, 'caustic': 0.25},
    'channel': {'visibility_m': 2.5, 'fog_density': 0.34, 'tint': '#4f5a36', 'light_falloff_per_m': 0.18, 'caustic': 0.2},
    'pond': {'visibility_m': 2.0, 'fog_density': 0.4, 'tint': '#46603a', 'light_falloff_per_m': 0.2, 'caustic': 0.2},
}


def req(d, k, where):
    if k not in d:
        raise KeyError(f'underwater: missing {k!r} in {where}')
    return d[k]


def h01(*parts):
    """deterministic 0..1 from a hash of the parts"""
    s = '|'.join(str(p) for p in parts).encode()
    return int.from_bytes(hashlib.sha256(s).digest()[:4], 'big') / 2 ** 32


def sha16(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def ltp(lat0, lng0):
    k = math.radians(1) * R_M
    c = math.cos(math.radians(lat0))
    return lambda lng, lat: ((lng - lng0) * k * c, (lat - lat0) * k)


def in_ring(ring, x, y):
    ins = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            ins = not ins
        j = i
    return ins


def in_polys(polys, x, y):
    """even-odd over every ring of every polygon"""
    return sum(in_ring(r, x, y) for p in polys for r in p) % 2 == 1


def bowl(depth_max_dm, t):
    """t = 0 at the edge .. 1 in the middle -> AUTHORED depth profile (never 0 inside the body)"""
    t = max(0.0, min(1.0, t))
    return max(3, round(depth_max_dm * (0.25 + 0.75 * (3 * t * t - 2 * t * t * t))))


def substrate(body_id, i, j, d_dm, edge):
    if edge and h01(body_id, 'rip', i, j) < 0.35:
        return 4
    if d_dm < 8:
        return 0
    u = h01(body_id, 'sub', i // 3, j // 3)   # patches of 3x3 cells
    if 10 <= d_dm <= 60 and u < 0.12:
        return 3
    return 2 if u < 0.55 else 1


def grid_body(body_id, bbox, cell_m, inside, depth_max_dm, dist_cells_full, seed=None):
    """bbox [w,s,e,n] world m; inside(e,n) -> bool; depth from the distance (in cells) to the nearest dry cell.
    seed (e, n): keep only the wet cells 4-connected to the seed's cell (one water body, not the whole window)"""
    w, s, e, n = bbox
    nx = max(2, math.ceil((e - w) / cell_m) + 1)
    ny = max(2, math.ceil((n - s) / cell_m) + 1)
    wet = [[inside(w + i * cell_m, s + j * cell_m) for i in range(nx)] for j in range(ny)]
    if seed is not None:
        si, sj = round((seed[0] - w) / cell_m), round((seed[1] - s) / cell_m)
        if not wet[sj][si]:
            raise ValueError(f'underwater: {body_id} seed cell is dry')
        keep = [[False] * nx for _ in range(ny)]
        stack = [(si, sj)]
        keep[sj][si] = True
        while stack:
            i, j = stack.pop()
            for ii, jj in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if 0 <= ii < nx and 0 <= jj < ny and wet[jj][ii] and not keep[jj][ii]:
                    keep[jj][ii] = True
                    stack.append((ii, jj))
        wet = keep
    # chamfer distance (cells) to the nearest dry cell or the grid edge
    INF = 10 ** 6
    dist = [[(INF if wet[j][i] else 0) for i in range(nx)] for j in range(ny)]
    for j in range(ny):
        for i in range(nx):
            if not wet[j][i]:
                continue
            if i in (0, nx - 1) or j in (0, ny - 1):
                dist[j][i] = 1
    for _ in range(2):
        for j in range(ny):
            for i in range(nx):
                if dist[j][i]:
                    for dj, di in ((-1, 0), (0, -1), (-1, -1), (-1, 1)):
                        jj, ii = j + dj, i + di
                        if 0 <= jj < ny and 0 <= ii < nx:
                            dist[j][i] = min(dist[j][i], dist[jj][ii] + 1)
        for j in range(ny - 1, -1, -1):
            for i in range(nx - 1, -1, -1):
                if dist[j][i]:
                    for dj, di in ((1, 0), (0, 1), (1, 1), (1, -1)):
                        jj, ii = j + dj, i + di
                        if 0 <= jj < ny and 0 <= ii < nx:
                            dist[j][i] = min(dist[j][i], dist[jj][ii] + 1)
    depth, sub = [], []
    for j in range(ny):
        drow, srow = [], []
        for i in range(nx):
            if not wet[j][i]:
                drow.append(0)
                srow.append(-1)
                continue
            t = dist[j][i] / dist_cells_full
            d = bowl(depth_max_dm, t)
            d = max(3, min(depth_max_dm, round(d * (0.9 + 0.2 * h01(body_id, 'n', i, j)))))
            drow.append(d)
            srow.append(substrate(body_id, i, j, d, dist[j][i] <= 1))
        depth.append(drow)
        sub.append(srow)
    return {'origin_world_m': [round(w, 1), round(s, 1)], 'cell_m': cell_m, 'nx': nx, 'ny': ny,
            'depth_dm': depth, 'substrate': sub}


def habitats_from_grid(body_id, g, cap):
    """AUTHORED patches: cells whose substrate + depth suit a habitat, thinned by a hash, capped per kind"""
    out = []
    for kind, rule in HABITATS.items():
        codes = {SUBSTRATES.index(s) for s in rule['substrates']}
        lo, hi = rule['depth_dm']
        cand = []
        for j in range(g['ny']):
            for i in range(g['nx']):
                d, c = g['depth_dm'][j][i], g['substrate'][j][i]
                if c in codes and lo <= d <= hi:
                    cand.append((h01(body_id, kind, i, j), i, j))
        cand.sort()
        for u, i, j in cand[:cap]:
            e = g['origin_world_m'][0] + i * g['cell_m']
            n = g['origin_world_m'][1] + j * g['cell_m']
            # a compact cluster (r = 12 % of a cell, at most 40 m) so a patch reads as a bed at underwater visibility
            out.append({'kind': kind, 'world_m': [round(e, 1), round(n, 1)], 'r_m': round(min(40.0, g['cell_m'] * 0.12), 1),
                        'count': 24 + int(u * 1000) % 24, 'provenance': 'AUTHORED'})
    return out


def channel_body(body_id, ch, origin, depth_dm_max):
    """a channel's grid is along x across: stations along the centre polyline x 5 samples across the width"""
    pts = [(p[0] + origin[0], p[1] + origin[1]) for p in req(ch, 'centre', body_id)]
    if len(pts) < 2:
        raise ValueError(f'underwater: channel {body_id} has < 2 centre points')
    seg = [math.dist(pts[k], pts[k + 1]) for k in range(len(pts) - 1)]
    L = sum(seg)
    ns = max(2, min(24, int(L // 100) + 2))
    stations = []
    for s_i in range(ns):
        tgt = L * s_i / (ns - 1)
        acc = 0.0
        for k, sl in enumerate(seg):
            if acc + sl >= tgt or k == len(seg) - 1:
                f = 0 if sl == 0 else min(1.0, (tgt - acc) / sl)
                a, b = pts[k], pts[k + 1]
                stations.append([round(a[0] + (b[0] - a[0]) * f, 1), round(a[1] + (b[1] - a[1]) * f, 1)])
                break
            acc += sl
    prof = [0.3, 0.75, 1.0, 0.75, 0.3]
    kind = req(ch, 'kind', body_id)
    depth, sub = [], []
    for s_i in range(ns):
        row, srow = [], []
        for a_i, p in enumerate(prof):
            d = max(2, min(depth_dm_max, round(depth_dm_max * p * (0.85 + 0.3 * h01(body_id, s_i, a_i)))))
            row.append(d)
            edge = a_i in (0, 4)
            srow.append(4 if (edge and kind == 'canal') else (0 if d < 8 else (1 if kind != 'stream' else 2)))
        depth.append(row)
        sub.append(srow)
    return {'stations_world_m': stations, 'width_m': req(ch, 'width_m', body_id), 'across': len(prof),
            'depth_dm': depth, 'substrate': sub}


def main():
    src = {}
    ne = ROOT / 'terrain/vendor'
    man = json.loads((ne / 'manifest.json').read_text())
    lakes_ne = json.loads((ne / 'ne_lakes.json').read_text())
    land_ne = json.loads((ne / 'ne_land.json').read_text())
    for f in ('manifest.json', 'ne_lakes.json', 'ne_land.json'):
        src['terrain/vendor/' + f] = sha16(ne / f)
    preg = json.loads((ROOT / 'parishes/registry/parishes.json').read_text())
    breg = json.loads((ROOT / 'bayarea/registry/bayarea.json').read_text())
    src['parishes/registry/parishes.json'] = sha16(ROOT / 'parishes/registry/parishes.json')
    src['bayarea/registry/bayarea.json'] = sha16(ROOT / 'bayarea/registry/bayarea.json')
    worlds = [('parishes', preg, 'parishes', ROOT / 'parishes/maps/world'),
              ('bay', breg, 'counties', ROOT / 'bayarea/maps/world')]
    bodies = []
    ne_used = []
    for world, reg, key, wdir in worlds:
        wo = req(req(reg, 'frames', world), 'world', world)['origin']
        fwd = ltp(req(wo, 'lat', world), req(wo, 'lng', world))
        # NE lake polygons of the new-orleans clip, in this world's metres (only the parish world uses them)
        ne_polys, ne_land_no = [], []
        if world == 'parishes':
            for ft in req(land_ne, 'campuses', 'ne_land')['new-orleans']['features']:
                g = ft['geometry']
                for poly in (g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]):
                    ne_land_no.append([[fwd(x, y) for x, y in ring] for ring in poly])
            for ft in req(lakes_ne, 'campuses', 'ne_lakes')['new-orleans']['features']:
                g = ft['geometry']
                polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
                ne_polys.append([[[fwd(x, y) for x, y in ring] for ring in poly] for poly in polys])
        for fips in sorted(req(reg, key, world)):
            wf = wdir / f'{fips}.json'
            src[str(wf.relative_to(ROOT))] = sha16(wf)
            wj = json.loads(wf.read_text())
            water = req(wj, 'water', str(wf))
            origin = req(req(reg[key][fips], 'frame', fips), 'origin_in_world_m', fips)
            surface = req(water, 'surface_y_m', str(wf))
            for lk in req(water, 'lakes', str(wf)):
                bid = req(lk, 'id', str(wf))
                c = req(lk, 'centre', bid)
                ce, cn = c[0] + origin[0], c[1] + origin[1]
                r = req(lk, 'radius_m', bid)
                hit = [p for p in ne_polys if in_polys(p, ce, cn)]
                if hit:
                    poly = hit[0]
                    xs = [x for pg in poly for ring in pg for x, _ in ring] + [ce - r, ce + r]
                    ys = [y for pg in poly for ring in pg for _, y in ring] + [cn - r, cn + r]
                    bbox = [min(xs), min(ys), max(xs), max(ys)]
                    inside = (lambda poly, ce, cn, r: lambda e, n: in_polys(poly, e, n) or math.hypot(e - ce, n - cn) <= r)(poly, ce, cn, r)
                    shore = {'provenance': 'RECORDED', 'layer': 'ne_lakes', 'file': 'terrain/vendor/ne_lakes.json',
                             'clip': 'new-orleans', 'scale': '1:10,000,000 (Natural Earth 10m)',
                             'licence': req(man, 'licence', 'manifest'),
                             'rule': 'the NE lake polygon that contains this stand-in centre + the AUTHORED stand-in disc the page draws',
                             'ring_world_m': [[round(x, 1), round(y, 1)] for x, y in poly[0][0]]}
                    ne_used.append(bid)
                    cell = 500
                    seed = None
                elif world == 'parishes' and not any(in_polys([p], ce, cn) for p in ne_land_no):
                    # the stand-in centre lies OUTSIDE NE land (tidal lakes are not in ne_lakes): water = the
                    # connected non-land cells of an AUTHORED window (+-30 km E-W, +-20 km N-S) around the centre
                    bbox = [ce - 30000, cn - 20000, ce + 30000, cn + 20000]
                    inside = (lambda ce, cn, r: lambda e, n: (not any(in_polys([p], e, n) for p in ne_land_no)) or math.hypot(e - ce, n - cn) <= r)(ce, cn, r)
                    shore = {'provenance': 'RECORDED', 'layer': 'ne_land', 'file': 'terrain/vendor/ne_land.json',
                             'clip': 'new-orleans', 'scale': '1:10,000,000 (Natural Earth 10m)',
                             'licence': req(man, 'licence', 'manifest'),
                             'rule': 'water = cells outside every NE land polygon (new-orleans clip), 4-connected to the '
                                     'stand-in centre, inside an AUTHORED +-30 km x +-20 km window; plus the AUTHORED stand-in disc'}
                    ne_used.append(bid)
                    cell = 500
                    seed = (ce, cn)
                else:
                    bbox = [ce - r, cn - r, ce + r, cn + r]
                    inside = (lambda ce, cn, r: lambda e, n: math.hypot(e - ce, n - cn) <= r)(ce, cn, r)
                    shore = {'provenance': 'AUTHORED', 'rule': 'the world file stand-in disc'}
                    cell = 200
                    seed = None
                dmax = round(req(lk, 'depth_m', bid) * 10)
                g = grid_body(bid, bbox, cell, inside, dmax, 4, seed)
                bodies.append({'id': bid, 'world': world, 'region': fips, 'kind': 'lake', 'name': req(lk, 'name', bid),
                               'surface_y_m': surface, 'depth_max_dm': dmax, 'shoreline': shore, 'grid': g,
                               'habitats': habitats_from_grid(bid, g, 14), 'look': VIS['lake']})
            for ch in req(water, 'channels', str(wf)):
                bid = req(ch, 'id', str(wf))
                dmax = round(req(ch, 'depth_m', bid) * 10)
                cg = channel_body(bid, ch, origin, dmax)
                hab = []
                for s_i in range(0, len(cg['stations_world_m']), 6):
                    kinds = [('riprap' if 4 in cg['substrate'][s_i] else 'eelgrass')]
                    for k in kinds:
                        if k == 'eelgrass' and dmax < 8:
                            continue
                        hab.append({'kind': k, 'world_m': cg['stations_world_m'][s_i], 'r_m': round(cg['width_m'] * 0.4, 1),
                                    'count': 4 + int(h01(bid, 'hc', s_i) * 6), 'provenance': 'AUTHORED'})
                bodies.append({'id': bid, 'world': world, 'region': fips, 'kind': 'channel', 'channel_kind': req(ch, 'kind', bid),
                               'surface_y_m': surface, 'depth_max_dm': dmax,
                               'shoreline': {'provenance': 'AUTHORED', 'rule': 'the world file channel ribbon'},
                               'channel_grid': cg, 'habitats': hab, 'look': VIS['channel']})
            for pd in req(water, 'ponds', str(wf)):
                bid = req(pd, 'id', str(wf))
                c = req(pd, 'centre', bid)
                ce, cn, r = c[0] + origin[0], c[1] + origin[1], req(pd, 'radius_m', bid)
                dmax = round(req(pd, 'depth_m', bid) * 10)
                cell = max(4.0, round(2 * r / 7, 1))
                g = grid_body(bid, [ce - r, cn - r, ce + r, cn + r], cell,
                              (lambda ce, cn, r: lambda e, n: math.hypot(e - ce, n - cn) <= r)(ce, cn, r), dmax, 3)
                bodies.append({'id': bid, 'world': world, 'region': fips, 'kind': 'pond', 'surface_y_m': surface,
                               'depth_max_dm': dmax, 'shoreline': {'provenance': 'AUTHORED', 'rule': 'the world file pond disc'},
                               'grid': g, 'habitats': habitats_from_grid(bid, g, 2), 'look': VIS['pond']})
    # Bay open water: inside BAY's DERIVED bay frame, NOT inside NE land (oakland clip) -> RECORDED shoreline at 1:10m
    bf = req(req(breg, 'bay_frame', 'bayarea'), 'bounds', 'bay_frame')
    wo = breg['frames']['world']['origin']
    fwd = ltp(wo['lat'], wo['lng'])
    land = []
    for ft in req(land_ne, 'campuses', 'ne_land')['oakland']['features']:
        g = ft['geometry']
        polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        for poly in polys:
            land.append([[fwd(x, y) for x, y in ring] for ring in poly])
    w, s = fwd(bf['w'], bf['s'])
    e, n = fwd(bf['e'], bf['n'])
    bid = 'bay-open-0'
    g = grid_body(bid, [w, s, e, n], 500, lambda x, y: not any(in_polys([p], x, y) for p in land), 120, 12)
    surface_bay = json.loads((ROOT / 'bayarea/maps/world/06001.json').read_text())['water']['surface_y_m']
    bodies.append({'id': bid, 'world': 'bay', 'region': 'bay-frame', 'kind': 'bay',
                   'name': 'open water inside the Bay frame (San Francisco Bay and its margins)',
                   'surface_y_m': surface_bay, 'depth_max_dm': 120,
                   'shoreline': {'provenance': 'RECORDED', 'layer': 'ne_land', 'file': 'terrain/vendor/ne_land.json',
                                 'clip': 'oakland', 'scale': '1:10,000,000 (Natural Earth 10m)', 'licence': req(man, 'licence', 'manifest'),
                                 'rule': 'water = inside bayarea bay_frame (DERIVED) and outside every NE land polygon of the oakland clip; '
                                         'islands and piers below 1:10m are absent'},
                   'grid': g, 'habitats': habitats_from_grid(bid, g, 40), 'look': VIS['bay']})
    counts = {}
    for b in bodies:
        k = b['world'] + '.' + b['kind']
        counts[k] = counts.get(k, 0) + 1
    cells = sum(b['grid']['nx'] * b['grid']['ny'] for b in bodies if 'grid' in b)
    stations = sum(len(b['channel_grid']['stations_world_m']) for b in bodies if 'channel_grid' in b)
    doc = {
        'pack': 'underwater',
        'source_stamp': sha16(Path(__file__)),
        'sources': src,
        'honesty': HONESTY,
        'legend': LEGEND,
        'frames': 'grid origin_world_m and world_m are [east_m, north_m] in each world\'s shared frame '
                  '(parishes: parishes.json frames.world; bay: bayarea.json frames.world); scene x = east, z = -north',
        'units': {'depth': 'decimetres below surface_y_m (0 = dry cell)', 'cell_m': 'metres'},
        'substrates': SUBSTRATES,
        'habitat_rules': HABITATS,
        'looks': VIS,
        'ne_shorelines_used': sorted(ne_used) + [bid],
        'restore_hooks': {'status': 'PENDING', 'note': 'RESTORE scenarios mount via deepkit TCDeep.setTargets(); no scenario data is held here',
                          'funded_projects': []},
        'counts': {'bodies': len(bodies), 'by_world_kind': dict(sorted(counts.items())), 'grid_cells': cells,
                   'channel_stations': stations, 'habitats': sum(len(b['habitats']) for b in bodies)},
        'bodies': bodies,
    }
    txt = json.dumps(doc, separators=(',', ':'), ensure_ascii=False)
    if len(txt.encode()) > MAX_BYTES:
        raise SystemExit(f'underwater: registry {len(txt.encode())} B > budget {MAX_BYTES}')
    out = Path(next((a[6:] for a in sys.argv[1:] if a.startswith('--out=')), OUT))
    out.write_text(txt + '\n')
    print(f'underwater: {len(bodies)} bodies {doc["counts"]["by_world_kind"]} cells {cells} stations {stations} '
          f'habitats {doc["counts"]["habitats"]} NE {doc["ne_shorelines_used"]} {len(txt.encode())} B')


if __name__ == '__main__':
    main()
