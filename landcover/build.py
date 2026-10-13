#!/usr/bin/env python3
"""landcover/build.py -> landcover/registry/landcover.json (LANDCOVER_CONTRACT v1).

Reads ONLY what landcover/fetch_landcover.py vendored (vendor/manifest.json and the grids it pins)
plus the registries the grids were clipped to, and publishes per region the grid geometry, class
shares recomputed from the bytes, per member (parish / county) class shares over its bbox_wgs84, and
pins - the class at every member frame origin and each world-frame origin, sampled by
landcover/sample.py (the one sampler). Class data is RECORDED (ESA WorldCover 2021, CC BY 4.0); the
points keep their own registry provenance. Unspoken Smiles is AUTHORED with no real anchor: no grid.

Deterministic, fail closed.  python3 landcover/build.py [--check]
"""
import gzip
import hashlib
import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from landcover.sample import class_at  # noqa: E402

OUT = HERE / 'registry' / 'landcover.json'
MANIFEST = HERE / 'vendor' / 'manifest.json'
R_M = 6371008.8
MEMBERS = {'parishes': ('parishes/registry/parishes.json', 'parishes'),
           'bayarea': ('bayarea/registry/bayarea.json', 'counties')}
CITATION_AUTHORS = ('Zanaga, D., Van De Kerchove, R., Daems, D., De Keersmaecker, W., Brockmann, C., Kirches, G., '
                    'Wevers, J., Cartus, O., Santoro, M., Fritz, S., Lesiv, M., Herold, M., Tsendbazar, N.E., Xu, P., '
                    'Ramoino, F., Arino, O.')


def need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise SystemExit(f'landcover/build.py: {where} is missing {k!r}')
    return d[k]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load(rel):
    return json.loads((ROOT / rel).read_text())


def shares(raw, cols, r0, r1, c0, c1, codes):
    cnt = {k: 0 for k in codes}; nd = 0
    for r in range(r0, r1):
        row = raw[r * cols + c0: r * cols + c1]
        for k in codes:
            cnt[k] += row.count(k)
        nd += row.count(0)
    tot = sum(cnt.values())
    if tot == 0:
        raise SystemExit('landcover/build.py: a window has no classified cell')
    return {'cells': {str(k): v for k, v in cnt.items() if v}, 'nodata_cells': nd, 'classified_cells': tot,
            'share': {str(k): round(v / tot, 4) for k, v in cnt.items() if v}}


def window(G, bbox):
    w, s, e, n = (x * 3600 for x in bbox)
    c = G['c']
    r0 = max(0, math.ceil((G['n'] - n) / c - 0.5)); r1 = min(G['rows'], math.floor((G['n'] - s) / c - 0.5) + 1)
    c0 = max(0, math.ceil((w - G['w']) / c - 0.5)); c1 = min(G['cols'], math.floor((e - G['w']) / c - 0.5) + 1)
    return r0, r1, c0, c1


def build():
    man_bytes = MANIFEST.read_bytes()
    man = json.loads(man_bytes)
    files = need(man, 'files', 'manifest')
    classes = need(man, 'classes', 'manifest')
    codes = sorted(int(k) for k in classes)
    enc = need(man, 'encoding', 'manifest')
    grids, members, pins = {}, {}, []
    for name, (rel, key) in MEMBERS.items():
        g = need(need(man, 'regions', 'manifest'), name, 'manifest.regions')
        fn = need(g, 'file', name)
        blob = (HERE / 'vendor' / fn).read_bytes()
        if sha(blob) != need(need(files, fn, 'manifest.files'), 'sha256', fn):
            raise SystemExit(f'landcover/build.py: vendor/{fn} does not match its manifest sha256')
        raw = gzip.decompress(blob)
        rows, cols, c = need(g, 'rows', name), need(g, 'cols', name), need(g, 'cell_arcsec', name)
        if len(raw) != rows * cols:
            raise SystemExit(f'landcover/build.py: {name} grid is {len(raw)} bytes, want {rows * cols}')
        b = {'w': need(g, 'w_arcsec', name), 's': need(g, 's_arcsec', name),
             'e': need(g, 'e_arcsec', name), 'n': need(g, 'n_arcsec', name)}
        G = {'region': name, 'rows': rows, 'cols': cols, 'raw': raw, 'n': b['n'], 'w': b['w'], 'c': c,
             'nodata': need(enc, 'nodata_value', 'encoding')}
        lat_mid = math.radians((b['n'] + b['s']) / 2 / 3600)
        grids[name] = {
            'what': need(g, 'what', name), 'file': fn, 'bytes': len(blob), 'sha256': sha(blob),
            'rows': rows, 'cols': cols, 'cell_arcsec': c, 'cell_deg': round(c / 3600, 9),
            'cell_size_m': {'north_south': round(R_M * math.radians(c / 3600), 1),
                            'east_west_at_mid_lat': round(R_M * math.cos(lat_mid) * math.radians(c / 3600), 1)},
            'bounds_arcsec': b, 'bounds_deg': {k: round(v / 3600, 6) for k, v in b.items()},
            'bounds_from': need(g, 'bounds_from', name),
            'encoding': {k: need(enc, k, 'encoding') for k in ('dtype', 'order', 'compression', 'nodata_value', 'cell_value')},
            'tiles': [need(t, 'tile', name) for t in need(g, 'tiles', name)],
            'classes_over_grid': shares(raw, cols, 0, rows, 0, cols, codes),
        }
        src = load(rel)
        items = need(src, key, rel)
        items = list(items.values()) if isinstance(items, dict) else list(items)
        members[name] = {}
        for it in items:
            fips = need(it, 'fips', rel)
            bbox = need(it, 'bbox_wgs84', f'{rel}#{fips}')
            o = need(need(it, 'frame', fips), 'origin', fips)
            k = class_at(G, need(o, 'lat', fips), need(o, 'lng', fips))
            members[name][fips] = {'name': need(it, 'name', fips), 'bbox_wgs84': bbox,
                                   'classes_over_bbox': shares(raw, cols, *window(G, bbox), codes),
                                   'frame_origin': {'lat': o['lat'], 'lng': o['lng']}, 'frame_origin_class': k}
            pins.append({'region': name, 'id': f'{fips}.frame_origin', 'lat': o['lat'], 'lng': o['lng'], 'class': k,
                         'point_provenance': f'DERIVED - {rel}#{fips}.frame.origin (area-weighted centroid)'})
        wo = need(need(need(src, 'frames', rel), 'world', rel), 'origin', rel)
        pins.append({'region': name, 'id': 'world.origin', 'lat': need(wo, 'lat', rel), 'lng': need(wo, 'lng', rel),
                     'class': class_at(G, wo['lat'], wo['lng']),
                     'point_provenance': f'{rel}#frames.world.origin (the shared scene frame of every world file)'})
    smiles = load('smiles/registry/smiles.json')
    return {
        'pack': 'landcover', 'pack_version': need(load('pack/manifest.json'), 'pack_version', 'pack/manifest.json'),
        'contract': 'LANDCOVER_CONTRACT v1',
        'source_stamp': sha((HERE / 'build.py').read_bytes())[:16],
        'sampler_stamp': sha((HERE / 'sample.py').read_bytes())[:16],
        'manifest_sha256': sha(man_bytes),
        'provenance': 'RECORDED',
        'provenance_note': 'every class is RECORDED from the vendored ESA WorldCover 2021 grids; the point it is sampled '
                           'at keeps its own registry provenance; anything placed where a grid says None is AUTHORED',
        'source': need(man, 'source', 'manifest'), 'source_url': need(man, 'bucket', 'manifest'),
        'licence': 'CC BY 4.0 - legal code vendored in landcover/vendor/LICENSE_CC-BY-4.0.txt; attribution and '
                   'citation verbatim in landcover/vendor/WORLDCOVER_ATTRIBUTION.txt',
        'attribution': {
            'text': '© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by '
                    'ESA WorldCover consortium',
            'author': CITATION_AUTHORS, 'title': 'ESA WorldCover 10 m 2021 v200',
            'source_url': 'https://doi.org/10.5281/zenodo.7254221',
            'license_id': 'CC-BY-4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
            'modified': True,
            'changes': 'majority class per 3 arc-second cell (9 x 9 source pixels), under-half-classified cells '
                       'set to nodata, clipped to the parish and Bay registry bounds (landcover/fetch_landcover.py)'},
        'classes': {str(k): classes[str(k)] for k in codes},
        'honesty': ['a cell is the MAJORITY class of about 80 x 90 m of 10 m pixels: a street tree, a single '
                    'yard or a narrow levee strip inside another class is not represented',
                    'WorldCover is a 2021 satellite classification, not a survey or a species map: it says tree '
                    'cover, never which trees; species stay AUTHORED (named generally) on this RECORDED class',
                    'open ocean beyond the product coverage is nodata (None), never filled'],
        'sampler': {'module': 'landcover/sample.py',
                    'functions': ['load_grid(region)', 'class_at(grid, lat, lng)', 'landcover_at(grid, origin, x, z)',
                                  'resample_world(grid, origin, x0, z0, dx, dz, cols, rows)'],
                    'rule': 'the class of the cell containing the point (no interpolation); None for nodata or '
                            'outside the grid; never a default class',
                    'js_twin': 'landcover/test.mjs classAt() - must agree with every pin'},
        'grids': grids, 'members': members, 'pins': pins,
        'not_gridded': {'smiles': {'provenance': need(smiles, 'provenance', 'smiles.json'),
                                   'why': 'no real anchor to sample: ' + need(smiles, 'place_note', 'smiles.json'),
                                   'vegetation': 'AUTHORED rules only, labelled AUTHORED'}},
    }


def dump(reg):
    return json.dumps(reg, indent=1, sort_keys=True, ensure_ascii=False) + '\n'


def main():
    reg = dump(build())
    if '--check' in sys.argv[1:]:
        if (OUT.read_text() if OUT.exists() else '') != reg:
            raise SystemExit('landcover/build.py --check: registry/landcover.json is stale - rebuild')
        print('landcover/build.py --check: registry/landcover.json is current')
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(reg)
    r = json.loads(reg)
    for k, g in r['grids'].items():
        print(f'  {k}: {g["cols"]}x{g["rows"]} @ {g["cell_arcsec"]}" shares {g["classes_over_grid"]["share"]}')
    print(f'wrote {OUT.relative_to(ROOT)} ({len(r["pins"])} pins)')


if __name__ == '__main__':
    main()
