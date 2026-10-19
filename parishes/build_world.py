#!/usr/bin/env python3
"""parishes/build_world.py - the v1.4 WORLD LAYER of the parish pack (wave 7).

Writes parishes/maps/world/<fips>.json (one per parish) and parishes/registry/world.json:
  - water: AUTHORED lake stand-ins (only where registry water.labels names a lake inside the outline), bayous,
    canals, streams (centre polyline + ribbon polygon, clipped to the outline) and ponds (placed in street gaps).
    No public-domain Natural Earth lakes/rivers package verified on npm, so NOTHING here is RECORDED.
  - roads: AUTHORED cross-section per street class for the v1.3 street polylines (unchanged files).
  - buildings: the page's deterministic rule + seed (buildings are generated in web/build_parishes.py),
    so physkit can compute the same solid boxes.
Deterministic (seeded by FIPS), integer local metres, fail closed on any missing field. Run AFTER parishes/build.py.
"""
import hashlib
import json
import math
import random
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from render import _pip  # noqa: E402  (even-odd point-in-polygon, holes honoured - same rule as the streets)

VERSION = '1.4'
MAX_BYTES = 600_000
REG = ROOT / 'parishes/registry/parishes.json'
OUT_DIR = ROOT / 'parishes/maps/world'
OUT_REG = ROOT / 'parishes/registry/world.json'

WATER_SOURCE = ('npm registry searched 2026-09-29 01:20 UTC for a PUBLIC-DOMAIN Natural Earth 10m lakes / '
                'rivers_lake_centerlines package: none verified (earth-shapefiles 2.0.0 MIT, countries only; '
                '@fireflysemantics/geojson 1.0.1 Public Domain, countries only; sane-topojson MIT, 50m/110m only; '
                'world-atlas land/countries only; @geo-maps/* excluded, ODbL decision still open). Nothing is '
                'vendored and NO water feature is RECORDED: every feature below is AUTHORED.')
WATER_NOTE = 'AUTHORED water - procedural, NOT the real lakes, rivers or bayous'
PROVENANCE_RULE = ('water AUTHORED (procedural, seeded by FIPS); lake stand-ins sit on the APPROXIMATE label points '
                   'of registry water.labels (general public record) but their shape and size are AUTHORED; '
                   'road profiles AUTHORED; building rule = the page\'s AUTHORED kit; open water on the Gulf side '
                   'stays DERIVED = outside every land outline (no geometry here)')
SURFACE_Y_M = -0.4                    # AUTHORED: water surface this far below street level (y=0)
DEPTH_M = {'lake': 3.0, 'bayou': 1.6, 'canal': 2.4, 'stream': 0.6, 'pond': 1.2}   # AUTHORED; wade < 1.0 <= swim
WADE_MAX_M = 1.0
WIDTH_M = {'bayou': (14, 30), 'canal': (18, 24), 'stream': (4, 8)}                  # AUTHORED ranges
N_CHANNELS = {'bayou': 3, 'canal': 2, 'stream': 5}
LAKE_RADIUS_M = 3000                  # AUTHORED stand-in disc, NOT the shoreline
N_PONDS, POND_R = 8, (20, 60)
CELL_M = 20                           # street raster for pond gaps and crossing counts
R_EARTH = 6371008.8

ROADS = {
    'profile_version': 1,
    'note': 'AUTHORED cross-sections for the AUTHORED street polylines - generic, NOT a real street survey or standard',
    'classes': {
        'arterial': {'lanes': 4, 'lane_width_m': 3.5, 'parking_lanes': 0, 'parking_width_m': 0.0,
                     'curb_height_m': 0.15, 'sidewalk_m': [3.0, 3.0]},
        'collector': {'lanes': 2, 'lane_width_m': 3.3, 'parking_lanes': 2, 'parking_width_m': 2.4,
                      'curb_height_m': 0.15, 'sidewalk_m': [2.4, 2.4]},
        'local': {'lanes': 2, 'lane_width_m': 3.0, 'parking_lanes': 1, 'parking_width_m': 2.2,
                  'curb_height_m': 0.15, 'sidewalk_m': [1.8, 1.8]},
    },
}
for _c in ROADS['classes'].values():
    _c['carriageway_m'] = round(_c['lanes'] * _c['lane_width_m'] + _c['parking_lanes'] * _c['parking_width_m'], 2)
    _c['corridor_m'] = round(_c['carriageway_m'] + _c['sidewalk_m'][0] + _c['sidewalk_m'][1], 2)
    _c['provenance'] = 'AUTHORED'

BUILDINGS = {
    'mode': 'page-rule',
    'why': 'buildings are generated in the page (web/build_parishes.py buildChunk + kitLot, owner WILDS), not stored '
           'by PARISH; this is the rule so physkit computes the SAME boxes',
    'source': {'page_builder': 'web/build_parishes.py', 'functions': ['buildChunk', 'kitLot', 'landUse', 'parishAt'],
               'hash': 'wilds/core.mjs wildsHash(ix, iz, seed, k)'},
    'constants': {'CELL': 25, 'CHUNK_M': 250, 'DISTRICT_M': 400, 'SEED': 20260928},
    'box': '[x, z, w, h, d, family, yaw, colour]: SCENE WORLD metres (x east, z = -north), base at y=0, footprint w '
           'along x by d along z rotated by yaw radians about +y, height h; family house|midrise',
    'rule': 'for each cell (ix, iz) of CELL m: x=(ix+0.2+0.6*jx)*CELL, z=(iz+0.2+0.6*jz)*CELL with jx=H(ix,iz,SEED,2), '
            'jz=H(ix,iz,SEED,3), h=H(ix,iz,SEED,1); skip if outside every parish ring or within 45 m of a loaded '
            'landmark; skip street cells ((ix mod 4)==0 or (iz mod 4)==0, positive modulo); land use = '
            'landUse(x,z) from H(floor(x/DISTRICT_M), floor(z/DISTRICT_M), SEED, 7): <0.5 residential, <0.76 '
            'commercial, <0.88 industrial, else park; park -> no building; a building when h < 0.55: '
            'kitLot(use, ix, iz, x, z, jx, jz, H(ix,iz,SEED,4))',
    'land_use': 'AUTHORED (page hash districts), NOT the real land use',
    'provenance': 'AUTHORED',
}


def wilds_hash(ix, iz, seed, k):
    """Python port of wilds/core.mjs wildsHash (32-bit Math.imul arithmetic)."""
    M = 0xFFFFFFFF

    def imul(a, b):
        return ((a & M) * (b & M)) & M
    h = imul(ix, 374761393) ^ imul(iz, 668265263) ^ imul(seed, 2246822519) ^ imul(k, 3266489917)
    h = imul(h ^ (h >> 13), 1274126177)
    return ((h ^ (h >> 16)) & M) / 4294967296


HASH_CASES = [(0, 0, 20260928, 1), (3, -7, 20260928, 2), (-12, 40, 20260928, 3), (123, 456, 20260928, 4),
              (-1, -1, 20260928, 7), (5000, -9000, 1, 5)]


def need(d, k, where):
    if k not in d:
        raise SystemExit(f'build_world: missing {where}.{k}')
    return d[k]


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def ltp(lat, lng, o):
    lat0, lng0 = need(o, 'lat', 'frame.origin'), need(o, 'lng', 'frame.origin')
    return (R_EARTH * math.cos(math.radians(lat0)) * math.radians(lng - lng0), R_EARTH * math.radians(lat - lat0))


def street_cells(classes):
    cells = set()
    for lines in classes.values():
        for pl in lines:
            a = np.array(pl, dtype=np.float64)
            for (x1, y1), (x2, y2) in zip(a[:-1], a[1:]):
                n = max(2, int(math.hypot(x2 - x1, y2 - y1) / (CELL_M / 2)) + 1)
                t = np.linspace(0, 1, n)
                ex = np.floor((x1 + (x2 - x1) * t) / CELL_M).astype(int)
                ny = np.floor((y1 + (y2 - y1) * t) / CELL_M).astype(int)
                cells.update(zip(ex.tolist(), ny.tolist()))
    return cells


def ribbon(pts, w):
    a = np.array(pts, dtype=np.float64)
    L, R = [], []
    for i in range(len(a)):
        p0, p1 = a[max(0, i - 1)], a[min(len(a) - 1, i + 1)]
        dx, dy = p1 - p0
        n = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / n * w / 2, dx / n * w / 2
        L.append([int(round(a[i][0] + nx)), int(round(a[i][1] + ny))])
        R.append([int(round(a[i][0] - nx)), int(round(a[i][1] - ny))])
    return L + R[::-1]


def channel_path(rng, kind, bbox, outline):
    x0, y0, x1, y1 = bbox
    span = min(x1 - x0, y1 - y0)
    for _ in range(200):                               # start inside the outline
        sx, sy = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if _pip(outline, np.array([sx]), np.array([sy]))[0]:
            break
    else:
        raise SystemExit('build_world: no inside start point')
    th0 = rng.uniform(0, 2 * math.pi)
    if kind == 'canal':
        th0 = round(th0 / (math.pi / 2)) * (math.pi / 2) + rng.uniform(-0.15, 0.15)
    length = {'bayou': 0.55, 'canal': 0.45, 'stream': 0.18}[kind] * span
    step = {'bayou': 40.0, 'canal': 120.0, 'stream': 20.0}[kind]
    amp = {'bayou': 0.7, 'canal': 0.0, 'stream': 0.9}[kind]
    wl1, wl2 = rng.uniform(600, 1600), rng.uniform(150, 400)
    ph1, ph2 = rng.uniform(0, 6.3), rng.uniform(0, 6.3)
    n = int(length / step)
    ts = np.arange(-n // 2, n - n // 2) * step
    th = th0 + amp * (np.sin(ts / wl1 * 2 * math.pi + ph1) + 0.35 * np.sin(ts / wl2 * 2 * math.pi + ph2))
    dx, dy = np.cos(th) * step, np.sin(th) * step
    k0 = n // 2
    xs, ys = np.cumsum(dx), np.cumsum(dy)
    xs, ys = xs - xs[k0] + sx, ys - ys[k0] + sy
    return xs, ys


def runs(xs, ys, keep, min_pts=3):
    out, cur = [], []
    for x, y, k in zip(xs, ys, keep):
        if k:
            cur.append([int(round(x)), int(round(y))])
        else:
            if len(cur) >= min_pts:
                out.append(cur)
            cur = []
    if len(cur) >= min_pts:
        out.append(cur)
    return out


def disc(c, r, n=40):
    return [[int(round(c[0] + r * math.cos(2 * math.pi * i / n))), int(round(c[1] + r * math.sin(2 * math.pi * i / n)))]
            for i in range(n)]


def build_parish(fips, P, labels, streets_rel):
    outline = need(P, 'outline_local_m', fips)
    origin = need(need(P, 'frame', fips), 'origin', fips + '.frame')
    ring_pts = np.array([q for poly in outline for q in poly[0]], dtype=np.float64)
    bbox = (ring_pts[:, 0].min(), ring_pts[:, 1].min(), ring_pts[:, 0].max(), ring_pts[:, 1].max())
    sbytes = (ROOT / streets_rel).read_bytes()
    streets = json.loads(sbytes)
    classes = need(streets, 'classes', streets_rel)
    cells = street_cells(classes)

    lakes = []
    for L in labels:
        if fips not in need(L, 'inside_outline_of', 'water.labels'):
            continue
        c = ltp(need(L, 'lat', 'water.labels'), need(L, 'lng', 'water.labels'), origin)
        c = [int(round(c[0])), int(round(c[1]))]
        lakes.append({'id': f'{fips}-lake-{len(lakes)}', 'name': need(L, 'name', 'water.labels'),
                      'provenance': 'AUTHORED',
                      'basis': 'approximate label point from registry water.labels (general public record); '
                               'the disc shape and size are AUTHORED, NOT the shoreline',
                      'centre': c, 'radius_m': LAKE_RADIUS_M, 'depth_m': DEPTH_M['lake'],
                      'polygon': disc(c, LAKE_RADIUS_M, 64)})

    channels, crossings = [], 0
    for kind in ('bayou', 'canal', 'stream'):
        for i in range(N_CHANNELS[kind]):
            rng = random.Random(f'parishes-world:{fips}:{kind}:{i}')
            w = round(rng.uniform(*WIDTH_M[kind]), 1)
            xs, ys = channel_path(rng, kind, bbox, outline)
            keep = _pip(outline, xs, ys)
            for run in runs(xs, ys, keep):
                hit = [(math.floor(x / CELL_M), math.floor(y / CELL_M)) in cells for x, y in run]
                crossings += sum(1 for j, h in enumerate(hit) if h and (j == 0 or not hit[j - 1]))
                channels.append({'id': f'{fips}-{kind}-{i}-{len(channels)}', 'kind': kind, 'provenance': 'AUTHORED',
                                 'width_m': w, 'depth_m': DEPTH_M[kind], 'centre': run,
                                 'polygon': ribbon(run, w)})

    ponds = []
    rng = random.Random(f'parishes-world:{fips}:ponds')
    for _ in range(4000):
        if len(ponds) >= N_PONDS:
            break
        x, y = rng.uniform(bbox[0], bbox[2]), rng.uniform(bbox[1], bbox[3])
        r = round(rng.uniform(*POND_R), 1)
        if not _pip(outline, np.array([x]), np.array([y]))[0]:
            continue
        if any(math.hypot(x - lk['centre'][0], y - lk['centre'][1]) < LAKE_RADIUS_M + r for lk in lakes):
            continue
        g = int(math.ceil((r + 15) / CELL_M)) + 1
        cx, cy = math.floor(x / CELL_M), math.floor(y / CELL_M)
        if any((cx + a, cy + b) in cells for a in range(-g, g + 1) for b in range(-g, g + 1)):
            continue
        c = [int(round(x)), int(round(y))]
        ponds.append({'id': f'{fips}-pond-{len(ponds)}', 'provenance': 'AUTHORED', 'centre': c, 'radius_m': r,
                      'depth_m': DEPTH_M['pond'], 'polygon': disc(c, r, 20)})

    counts = {'lakes': len(lakes), 'bayou': sum(c['kind'] == 'bayou' for c in channels),
              'canal': sum(c['kind'] == 'canal' for c in channels),
              'stream': sum(c['kind'] == 'stream' for c in channels), 'ponds': len(ponds),
              'crossings': crossings, 'channel_vertices': sum(len(c['centre']) for c in channels)}
    doc = {'pack': 'parishes', 'version': VERSION, 'fips': fips,
           'crs': 'parish LOCAL metres [east_m, north_m], integers; origin = registry parishes[fips].frame.origin',
           'frame_origin': origin, 'provenance_rule': PROVENANCE_RULE,
           'water': {'provenance': 'AUTHORED', 'note': WATER_NOTE, 'surface_y_m': SURFACE_Y_M,
                     'wade_max_depth_m': WADE_MAX_M,
                     'crossing_rule': f'streets are NOT cut by channels: a crossing (channel centre entering a '
                                      f'{CELL_M} m cell a street passes through, once per run) is an AUTHORED '
                                      f'bridge/culvert - the road stays at y=0',
                     'lakes': lakes, 'channels': channels, 'ponds': ponds},
           'roads': {'profile_version': ROADS['profile_version'], 'streets_path': streets_rel,
                     'streets_sha256': sha256_bytes(sbytes), 'classes': ROADS['classes']},
           'buildings': {'mode': 'page-rule', 'see': 'parishes/registry/world.json#buildings'},
           'counts': counts}
    return doc


def main():
    rb = REG.read_bytes()
    R = json.loads(rb)
    parishes = need(R, 'parishes', 'registry')
    labels = need(need(R, 'water', 'registry'), 'labels', 'registry.water')
    h = hashlib.sha256()
    h.update(rb)
    srcs = {}
    for fips in sorted(parishes):
        st = need(need(parishes[fips], 'map', fips), 'streets', fips + '.map')
        rel = need(st, 'path', fips + '.map.streets')
        srcs[fips] = rel
        h.update((ROOT / rel).read_bytes())
    h.update(Path(__file__).read_bytes())
    stamp = h.hexdigest()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    entries = {}
    for fips in sorted(parishes):
        doc = build_parish(fips, parishes[fips], labels, srcs[fips])
        doc['source_stamp'] = stamp[:16]
        f = OUT_DIR / f'{fips}.json'
        f.write_text(json.dumps(doc, separators=(',', ':')) + '\n')
        size = f.stat().st_size
        if size > MAX_BYTES:
            raise SystemExit(f'build_world: {f.name} {size} bytes over the declared budget {MAX_BYTES}')
        entries[fips] = {'path': f'parishes/maps/world/{fips}.json', 'bytes': size, 'max_bytes': MAX_BYTES,
                         'sha256': sha256_bytes(f.read_bytes()), 'counts': doc['counts']}
    B = dict(BUILDINGS)
    B['hash_vectors'] = [{'args': list(a), 'value': wilds_hash(*a)} for a in HASH_CASES]
    reg = {'pack': 'parishes', 'layer': 'world', 'version': VERSION,
           'source_stamp': stamp, 'source_stamp_sha256': 'sha256 over parishes/registry/parishes.json + every '
           'parishes/maps/streets/<fips>.json (sorted by fips) + parishes/build_world.py',
           'water_source': WATER_SOURCE, 'water_note': WATER_NOTE, 'provenance_rule': PROVENANCE_RULE,
           'water_levels': {'surface_y_m': SURFACE_Y_M, 'wade_max_depth_m': WADE_MAX_M, 'depth_m': DEPTH_M,
                            'provenance': 'AUTHORED'},
           'roads': ROADS, 'buildings': B, 'parishes': entries}
    OUT_REG.write_text(json.dumps(reg, indent=1) + '\n')
    tot = sum(e['bytes'] for e in entries.values())
    print(f'build_world: {len(entries)} parishes, {tot} bytes, stamp {stamp[:16]}, '
          f'channels {sum(e["counts"]["bayou"] + e["counts"]["canal"] + e["counts"]["stream"] for e in entries.values())}, '
          f'ponds {sum(e["counts"]["ponds"] for e in entries.values())}, lakes {sum(e["counts"]["lakes"] for e in entries.values())}')


if __name__ == '__main__':
    main()
