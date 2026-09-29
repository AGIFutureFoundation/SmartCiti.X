#!/usr/bin/env python3
"""elevation/build.py -> elevation/registry/elevation.json (ELEV_CONTRACT v1).

Reads ONLY what elevation/fetch_dem.py vendored (vendor/manifest.json and the
grids it pins) plus the registries whose outlines the grids were clipped to,
and publishes: per region, the grid's geometry and encoding, stats recomputed
from the bytes, per member (parish / county) stats over its bbox_wgs84, and
pins - heights sampled by elevation/sample.py (the one sampler) at every
member's frame origin and at the two world-frame origins. Provenance of every
height is RECORDED (USGS 3DEP, public domain); the points they are sampled at
keep their own registry's provenance (frame origins are DERIVED centroids).

The Unspoken Smiles district is AUTHORED with no real anchor: it gets no grid
and the registry says why, from smiles/registry/smiles.json's own place_note.

Deterministic: no clock, no randomness. Fail closed: a missing key raises.
  python3 elevation/build.py           # write the registry
  python3 elevation/build.py --check   # rebuild in memory, compare, exit 1 on drift
"""
import gzip
import hashlib
import json
import math
import pathlib
import sys
from array import array

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from elevation.sample import cell_m, height_m  # noqa: E402

OUT = HERE / 'registry' / 'elevation.json'
MANIFEST = HERE / 'vendor' / 'manifest.json'
R_M = 6371008.8
MEMBERS = {'parishes': ('parishes/registry/parishes.json', 'parishes'),
           'bayarea': ('bayarea/registry/bayarea.json', 'counties')}


def need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise SystemExit(f'elevation/build.py: {where} is missing {k!r}')
    return d[k]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load(rel):
    return json.loads((ROOT / rel).read_text())


def grid_of(name, g, enc):
    raw = gzip.decompress((HERE / 'vendor' / need(g, 'file', name)).read_bytes())
    rows, cols = need(g, 'rows', name), need(g, 'cols', name)
    if len(raw) != rows * cols * 2:
        raise SystemExit(f'elevation/build.py: {name} grid is {len(raw)} bytes, want {rows * cols * 2}')
    return {'region': name, 'rows': rows, 'cols': cols, 'raw': raw,
            'n': need(g, 'n_arcsec', name), 'w': need(g, 'w_arcsec', name), 'c': need(g, 'cell_arcsec', name),
            'nodata': need(enc, 'nodata_value', 'encoding'), 'offset': need(enc, 'offset_m', 'encoding'),
            'scale': need(enc, 'scale_m', 'encoding')}


def stats(G, r0, r1, c0, c1):
    v = array('H'); v.frombytes(G['raw'])
    if sys.byteorder != 'little':
        v.byteswap()
    lo = hi = None; s = 0; n = 0; nd = 0; at_lo = at_hi = None
    for r in range(r0, r1):
        base = r * G['cols']
        for c in range(c0, c1):
            x = v[base + c]
            if x == G['nodata']:
                nd += 1; continue
            n += 1; s += x
            if lo is None or x < lo:
                lo, at_lo = x, (r, c)
            if hi is None or x > hi:
                hi, at_hi = x, (r, c)
    if n == 0:
        raise SystemExit(f'elevation/build.py: {G["region"]} window {r0}:{r1},{c0}:{c1} has no valid cell')
    m = lambda x: round(x * G['scale'] - G['offset'], 1)  # noqa: E731
    centre = lambda rc: {'lat': round((G['n'] - (rc[0] + 0.5) * G['c']) / 3600, 6),  # noqa: E731
                         'lng': round((G['w'] + (rc[1] + 0.5) * G['c']) / 3600, 6), 'row': rc[0], 'col': rc[1]}
    return {'min_m': m(lo), 'max_m': m(hi), 'mean_m': round(s / n * G['scale'] - G['offset'], 2),
            'valid_cells': n, 'nodata_cells': nd, 'min_at': centre(at_lo), 'max_at': centre(at_hi)}


def window(G, bbox):
    """Rows/cols whose cell centre lies inside a [w, s, e, n] degree box."""
    w, s, e, n = (x * 3600 for x in bbox)
    c = G['c']
    r0 = max(0, math.ceil((G['n'] - n) / c - 0.5)); r1 = min(G['rows'], math.floor((G['n'] - s) / c - 0.5) + 1)
    c0 = max(0, math.ceil((w - G['w']) / c - 0.5)); c1 = min(G['cols'], math.floor((e - G['w']) / c - 0.5) + 1)
    return r0, r1, c0, c1


def build():
    man_bytes = MANIFEST.read_bytes()
    man = json.loads(man_bytes)
    enc = need(man, 'encoding', 'manifest')
    files = need(man, 'files', 'manifest')
    grids, members, pins = {}, {}, []
    for name, (rel, key) in MEMBERS.items():
        g = need(need(man, 'regions', 'manifest'), name, 'manifest.regions')
        fn = need(g, 'file', name)
        blob = (HERE / 'vendor' / fn).read_bytes()
        if sha(blob) != need(need(files, fn, 'manifest.files'), 'sha256', fn):
            raise SystemExit(f'elevation/build.py: vendor/{fn} does not match its manifest sha256 - run fetch_dem.py --check')
        G = grid_of(name, g, enc)
        c = G['c']
        b = {'w': g['w_arcsec'], 's': need(g, 's_arcsec', name), 'e': need(g, 'e_arcsec', name), 'n': g['n_arcsec']}
        lat_mid = math.radians((b['n'] + b['s']) / 2 / 3600)
        tiles = need(g, 'tiles', name)
        grids[name] = {
            'what': need(g, 'what', name), 'file': fn, 'bytes': len(blob), 'sha256': sha(blob),
            'rows': G['rows'], 'cols': G['cols'], 'cell_arcsec': c, 'cell_deg': round(c / 3600, 9),
            'cell_size_m': {'north_south': round(R_M * math.radians(c / 3600), 1),
                            'east_west_at_mid_lat': round(R_M * math.cos(lat_mid) * math.radians(c / 3600), 1)},
            'bounds_arcsec': b, 'bounds_deg': {k: round(v / 3600, 6) for k, v in b.items()},
            'origin_nw': {'lat': round(b['n'] / 3600, 6), 'lng': round(b['w'] / 3600, 6),
                          'what': 'outer north-west corner of cell (0, 0); rows run south, cols run east'},
            'bounds_from': need(g, 'bounds_from', name),
            'encoding': {k: need(enc, k, 'encoding') for k in ('dtype', 'order', 'compression', 'nodata_value',
                                                               'height_m', 'offset_m', 'scale_m', 'cell_value')},
            'units': 'm', 'vertical_datum': 'NAVD88', 'horizontal_datum': 'NAD83 (used as WGS84; ~1-2 m apart here)',
            'tiles_published': [t['tile'] for t in tiles if need(t, 'published', 'tile')],
            'tiles_absent': [t['tile'] for t in tiles if not t['published']],
            'tile_pubdates': sorted({need(t, 'pubdate', t['tile']) for t in tiles if t['published']}),
            'stats': stats(G, 0, G['rows'], 0, G['cols']),
        }
        reg = load(rel)
        items = need(reg, key, rel)
        items = list(items.values()) if isinstance(items, dict) else list(items)
        members[name] = {}
        for it in items:
            fips = need(it, 'fips', rel)
            bbox = need(it, 'bbox_wgs84', f'{rel}#{fips}')
            origin = need(need(it, 'frame', fips), 'origin', fips)
            h = height_m(G, need(origin, 'lat', fips), need(origin, 'lng', fips))
            members[name][fips] = {'name': need(it, 'name', fips), 'bbox_wgs84': bbox,
                                   'stats_over_bbox': stats(G, *window(G, bbox)),
                                   'frame_origin': {'lat': origin['lat'], 'lng': origin['lng']},
                                   'frame_origin_height_m': h}
            pins.append({'region': name, 'id': f'{fips}.frame_origin', 'lat': origin['lat'], 'lng': origin['lng'],
                         'height_m': h, 'point_provenance': f'DERIVED - {rel}#{fips}.frame.origin (area-weighted centroid)'})
        wo = need(need(need(reg, 'frames', rel), 'world', rel), 'origin', rel)
        pins.append({'region': name, 'id': 'world.origin', 'lat': need(wo, 'lat', rel), 'lng': need(wo, 'lng', rel),
                     'height_m': height_m(G, wo['lat'], wo['lng']),
                     'point_provenance': f'{rel}#frames.world.origin (the shared scene frame of every world file)'})
    smiles = load('smiles/registry/smiles.json')
    stamp = sha((HERE / 'build.py').read_bytes())[:16]
    return {
        'pack': 'elevation', 'pack_version': need(load('pack/manifest.json'), 'pack_version', 'pack/manifest.json'),
        'contract': 'ELEV_CONTRACT v1',
        'source_stamp': stamp, 'sampler_stamp': sha((HERE / 'sample.py').read_bytes())[:16],
        'manifest_sha256': sha(man_bytes),
        'provenance': 'RECORDED',
        'provenance_note': 'every height is RECORDED from the vendored USGS 3DEP grids; the point it is sampled at keeps '
                           'its own registry provenance; anything drawn where a grid says None is AUTHORED and labelled',
        'source': need(man, 'source', 'manifest'), 'source_url': need(man, 'base_url', 'manifest'),
        'licence': need(man, 'licence', 'manifest'),
        'licence_file': 'elevation/vendor/USGS_3DEP_USE_CONSTRAINTS.txt',
        'attribution': {'text': 'Elevation: USGS 3D Elevation Program (3DEP), 1 arc-second DEM; resampled by this bundle',
                        'author': 'U.S. Geological Survey', 'title': need(man, 'source', 'manifest'),
                        'source_url': need(man, 'base_url', 'manifest'),
                        'license_id': 'LicenseRef-US-Government-Public-Domain',
                        'license_file': 'elevation/vendor/USGS_3DEP_USE_CONSTRAINTS.txt'},
        'modifications': 'block mean of the 1 arc-second pixels to cell_arcsec, cells under half valid are nodata, '
                         'rounded to 0.1 m, clipped to the union of the registry bboxes (elevation/fetch_dem.py)',
        'honesty': ['bare-earth DEM cell means at about 150-185 m: a levee, a street grade, a building pad or a '
                    'ravine narrower than a cell is NOT resolved and must not be drawn as if measured',
                    'water bodies carry whatever the source publishes for them - mostly flat water surfaces, in '
                    'places below-zero values (see grids.*.stats.min_at) - they are not a depth survey; ground '
                    'placement must use the water masks, not a height threshold; underwater/ bathymetry stays AUTHORED',
                    'cells the USGS publishes no tile for (open Gulf of Mexico, open Pacific) are nodata, never filled',
                    'NAVD88 metres; sea level is not 0 m NAVD88 exactly and this pack does not claim a shoreline'],
        'sampler': {'module': 'elevation/sample.py', 'functions': ['load_grid(region)', 'height_m(grid, lat, lng)',
                                                                    'height_world_m(grid, origin, x, z)'],
                    'rule': 'bilinear between the 4 cell centres around the point (edges clamp); if any of the 4 is '
                            'nodata, the containing cell\'s own value; None when that is nodata or the point is '
                            'outside the grid; never 0 or a default',
                    'js_twin': 'elevation/test.mjs heightM() - must agree with every pin'},
        'grids': grids,
        'members': members,
        'pins': pins,
        'not_gridded': {'smiles': {'provenance': need(smiles, 'provenance', 'smiles.json'),
                                   'why': 'no real anchor to sample: ' + need(smiles, 'place_note', 'smiles.json'),
                                   'relief': 'AUTHORED only, labelled AUTHORED on the page legend'}},
    }


def dump(reg):
    return json.dumps(reg, indent=1, sort_keys=True, ensure_ascii=False) + '\n'


def main():
    reg = dump(build())
    if '--check' in sys.argv[1:]:
        have = OUT.read_text() if OUT.exists() else ''
        if have != reg:
            raise SystemExit('elevation/build.py --check: registry/elevation.json is stale - rebuild')
        print('elevation/build.py --check: registry/elevation.json is current')
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(reg)
    r = json.loads(reg)
    for k, g in r['grids'].items():
        print(f'  {k}: {g["cols"]}x{g["rows"]} @ {g["cell_arcsec"]}" {g["stats"]["min_m"]}..{g["stats"]["max_m"]} m, '
              f'{len(r["members"][k])} members')
    print(f'wrote {OUT.relative_to(ROOT)} ({len(r["pins"])} pins)')


if __name__ == '__main__':
    main()
