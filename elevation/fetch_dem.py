"""Vendor real ground elevation, once, clipped to the parish and Bay worlds.

Until this pack the parish and Bay worlds were flat - AUTHORED at exactly
0 m - because no elevation source was reachable from the build machine and
the registries said so. The USGS publishes its 3D Elevation Program (3DEP)
1 arc-second DEM as staged GeoTIFF files on prd-tnm.s3.amazonaws.com, and
that host answers from here. 3DEP is a work of the U.S. federal government
(17 U.S.C. 105, U.S. public domain); each tile's own metadata adds use
constraints (acknowledge the USGS, describe any modification, never imply
USGS endorsement), which are vendored verbatim beside the grids.

WHAT IS VENDORED. Not the tiles (about 50 MB each): per region, one grid of
block means at CELL_ARCSEC, clipped to the union of the region's own
registry bounding boxes (parishes/registry/parishes.json bbox_wgs84 of the
13 parishes; bayarea/registry/bayarea.json bbox_wgs84 of the 9 counties),
snapped outward to whole cells. Unspoken Smiles is an AUTHORED district with
no real anchor, so it gets no grid: its relief stays AUTHORED.

MODIFICATIONS (the metadata asks every user to describe them): each output
cell is the arithmetic mean of the source 1-arc-second pixels that fall in
it, ignoring the source nodata value; a cell with fewer than half its pixels
valid is nodata. Heights are rounded to 0.1 m and stored as uint16
v = round((h + 100) * 10), v = 0 meaning nodata. Rows run north to south,
columns west to east, little-endian, gzip-compressed with mtime 0 so the
bytes are reproducible. Horizontal datum NAD83 (treated as WGS84: the two
differ by about 1-2 m here, far below one cell); vertical datum NAVD88.
A 1 arc-second tile that the USGS does not publish (open Gulf or Pacific)
is recorded as absent and its cells are nodata - never filled in.

This is NOT part of the build. It runs once, by hand, over the network, and
its output is committed. `--check` re-verifies the committed files against
the manifest offline, which is what verify_all.sh runs.

  python3 elevation/fetch_dem.py            # fetch, clip, write vendor/
  python3 elevation/fetch_dem.py --check    # offline sha256 verification
  ELEV_CACHE=/some/dir python3 elevation/fetch_dem.py   # reuse downloaded tiles
"""
import gzip
import hashlib
import json
import math
import os
import pathlib
import re
import sys
import tempfile
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
VENDOR = HERE / 'vendor'
MANIFEST = VENDOR / 'manifest.json'
CONSTRAINTS = VENDOR / 'USGS_3DEP_USE_CONSTRAINTS.txt'

BASE = 'https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1/TIFF/current/'
SOURCE = 'USGS 3D Elevation Program (3DEP), 1 arc-second DEM, staged GeoTIFF tiles'
LICENCE = ('U.S. public domain (work of the U.S. federal government, 17 U.S.C. 105); '
           'use constraints from the USGS tile metadata vendored verbatim in USGS_3DEP_USE_CONSTRAINTS.txt')
SRC_ARCSEC = 1
SRC_NODATA = -999999.0
OFFSET_M = 100.0
SCALE_M = 0.1

# 6 arc-seconds: 185 m north-south, 160 m east-west at 30N, 146 m at 38N.
# The whole 13-parish union and the whole 9-county union fit in about 4 MB
# at this size; at 3 arc-seconds they would be about four times that, for
# detail a walk view at these extents cannot use.
REGIONS = {
    'parishes': {'registry': 'parishes/registry/parishes.json', 'key': 'parishes', 'cell_arcsec': 6,
                 'what': 'the 13 parishes of the parish worlds, Louisiana'},
    'bayarea': {'registry': 'bayarea/registry/bayarea.json', 'key': 'counties', 'cell_arcsec': 6,
                'what': 'the 9 San Francisco Bay Area counties of the Bay world, California'},
}


def need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise SystemExit(f'fetch_dem: {where} is missing {k!r}')
    return d[k]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def region_bounds(name):
    """Union of the registry's own bbox_wgs84 values, snapped outward to whole cells."""
    R = REGIONS[name]
    reg = json.loads((ROOT / R['registry']).read_text())
    items = need(reg, R['key'], R['registry'])
    items = list(items.values()) if isinstance(items, dict) else list(items)
    if not items:
        raise SystemExit(f'fetch_dem: {R["registry"]} has no {R["key"]}')
    boxes = [need(it, 'bbox_wgs84', f'{R["registry"]}#{R["key"]}') for it in items]
    w = min(b[0] for b in boxes); s = min(b[1] for b in boxes)
    e = max(b[2] for b in boxes); n = max(b[3] for b in boxes)
    c = R['cell_arcsec']
    # work in integer arc-seconds so every edge is exact
    W = math.floor(w * 3600 / c) * c; S = math.floor(s * 3600 / c) * c
    E = math.ceil(e * 3600 / c) * c; N = math.ceil(n * 3600 / c) * c
    return {'w_arcsec': W, 's_arcsec': S, 'e_arcsec': E, 'n_arcsec': N, 'cell_arcsec': c,
            'cols': (E - W) // c, 'rows': (N - S) // c, 'members': len(boxes)}


def tiles_for(b):
    """USGS 1-degree tile names (NW corner naming: nYYwXXX covers lat YY-1..YY, lng -XXX..-XXX+1)."""
    out = []
    for lat_top in range(math.floor(b['s_arcsec'] / 3600) + 1, math.ceil(b['n_arcsec'] / 3600) + 1):
        for lng_left in range(math.floor(b['w_arcsec'] / 3600), math.ceil(b['e_arcsec'] / 3600)):
            if lng_left >= 0 or lat_top <= 0:
                raise SystemExit('fetch_dem: only the N/W hemisphere quadrant is handled')
            out.append(f'n{lat_top:02d}w{-lng_left:03d}')
    return out


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'smartcitix-elevation/1'})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def get_tile(name, cache):
    """(tif bytes, xml bytes) or (None, None) when the USGS publishes no such tile (HTTP 404)."""
    tif_p = cache / f'USGS_1_{name}.tif'
    xml_p = cache / f'USGS_1_{name}.xml'
    miss_p = cache / f'USGS_1_{name}.absent'
    if miss_p.exists():
        return None, None
    if not tif_p.exists():
        try:
            tif_p.write_bytes(fetch(f'{BASE}{name}/USGS_1_{name}.tif'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                miss_p.write_text('404\n')
                return None, None
            raise
    if not xml_p.exists():
        xml_p.write_bytes(fetch(f'{BASE}{name}/USGS_1_{name}.xml'))
    return tif_p.read_bytes(), xml_p.read_bytes()


def xml_field(xml, tag):
    m = re.search(rf'<{tag}>(.*?)</{tag}>', xml, re.S)
    if not m:
        raise SystemExit(f'fetch_dem: tile metadata has no <{tag}>')
    return ' '.join(m.group(1).split())


def read_tile(tif_path):
    """float32 array + (west, north) of pixel (0,0)'s outer corner, in integer arc-seconds."""
    import numpy as np
    from PIL import Image
    im = Image.open(tif_path)
    scale = need(dict(im.tag_v2), 33550, f'{tif_path} ModelPixelScale')
    tie = need(dict(im.tag_v2), 33922, f'{tif_path} ModelTiepoint')
    if abs(scale[0] * 3600 - SRC_ARCSEC) > 1e-6 or abs(scale[1] * 3600 - SRC_ARCSEC) > 1e-6:
        raise SystemExit(f'fetch_dem: {tif_path} is not {SRC_ARCSEC} arc-second')
    w = tie[3] * 3600; n = tie[4] * 3600
    if abs(w - round(w)) > 1e-3 or abs(n - round(n)) > 1e-3:
        raise SystemExit(f'fetch_dem: {tif_path} pixel edges are not on whole arc-seconds')
    nd = float(need(dict(im.tag_v2), 42113, f'{tif_path} GDAL_NODATA'))
    if nd != SRC_NODATA:
        raise SystemExit(f'fetch_dem: {tif_path} nodata {nd} is not {SRC_NODATA}')
    a = np.array(im, dtype=np.float32)
    a[a <= SRC_NODATA + 1] = np.nan
    return a, int(round(w)), int(round(n))


def build_region(name, cache):
    import numpy as np
    b = region_bounds(name)
    # a 1-arc-second mosaic of the region, NaN where no tile or nodata
    W, N = b['w_arcsec'], b['n_arcsec']
    H = b['n_arcsec'] - b['s_arcsec']; Wd = b['e_arcsec'] - b['w_arcsec']
    mos = np.full((H, Wd), np.nan, dtype=np.float32)
    tiles = []
    for t in tiles_for(b):
        tif, xml = get_tile(t, cache)
        if tif is None:
            tiles.append({'tile': t, 'published': False,
                          'note': 'HTTP 404 - the USGS publishes no 1 arc-second tile here (open water); cells stay nodata'})
            continue
        x = xml.decode('utf-8', 'replace')
        a, tw, tn = read_tile(cache / f'USGS_1_{t}.tif')
        # paste the overlap
        r0 = N - tn; c0 = tw - W                    # tile origin in mosaic pixels (row down, col right)
        rs, cs = max(0, -r0), max(0, -c0)
        re_, ce = min(a.shape[0], H - r0), min(a.shape[1], Wd - c0)
        if rs < re_ and cs < ce:
            src = a[rs:re_, cs:ce]
            dst = mos[r0 + rs:r0 + re_, c0 + cs:c0 + ce]
            take = ~np.isnan(src)
            dst[take] = src[take]                   # tiles overlap by their buffer; values agree
        tiles.append({'tile': t, 'published': True, 'url': f'{BASE}{t}/USGS_1_{t}.tif',
                      'bytes': len(tif), 'sha256': sha(tif),
                      'metadata_url': f'{BASE}{t}/USGS_1_{t}.xml', 'metadata_sha256': sha(xml),
                      'title': xml_field(x, 'title'), 'pubdate': xml_field(x, 'pubdate'),
                      'horizontal_datum': xml_field(x, 'horizdn'), 'vertical_datum': xml_field(x, 'altdatum')})
    c = b['cell_arcsec']
    blk = mos.reshape(b['rows'], c, b['cols'], c)
    valid = (~np.isnan(blk)).sum(axis=(1, 3))
    with np.errstate(invalid='ignore'):
        mean = np.nansum(blk, axis=(1, 3), dtype=np.float64) / np.maximum(valid, 1)
    keep = valid * 2 >= c * c
    v = np.zeros((b['rows'], b['cols']), dtype='<u2')
    q = np.round((mean + OFFSET_M) / SCALE_M)
    if keep.any() and (q[keep].min() < 1 or q[keep].max() > 65535):
        raise SystemExit(f'fetch_dem: {name} heights fall outside the uint16 encoding')
    v[keep] = q[keep].astype('<u2')
    raw = v.tobytes()
    gz = gzip.compress(raw, compresslevel=9, mtime=0)
    return b, tiles, gz


def constraints_text(xml):
    parts = ['USGS 3D Elevation Program (3DEP) 1 arc-second DEM - use constraints, copied verbatim',
             'from the USGS FGDC metadata published beside every tile (USGS_1_<tile>.xml).',
             'Status: a work of the U.S. federal government, U.S. public domain (17 U.S.C. 105).',
             'Modifications made by this bundle: described in elevation/fetch_dem.py (block mean to',
             'the cell size in manifest.json, 0.1 m rounding, uint16 encoding, clip to registry bounds).',
             'The USGS has not approved or endorsed these modifications or this bundle.', '']
    for tag, label in (('accconst', 'Access constraints'), ('useconst', 'Use constraints'),
                       ('datacred', 'Data set credit'), ('distliab', 'Distribution liability')):
        parts.append(f'{label}:')
        parts.append(xml_field(xml, tag))
        parts.append('')
    return '\n'.join(parts)


def check():
    if not MANIFEST.exists():
        raise SystemExit('fetch_dem --check: elevation/vendor/manifest.json is missing')
    m = json.loads(MANIFEST.read_text())
    bad = 0
    files = need(m, 'files', 'manifest')
    for fn, rec in sorted(files.items()):
        p = VENDOR / fn
        if not p.exists():
            print(f'FAIL  elevation/vendor/{fn} missing'); bad += 1; continue
        h = sha(p.read_bytes())
        if h != need(rec, 'sha256', fn):
            print(f'FAIL  elevation/vendor/{fn} sha256 {h[:16]} != manifest {rec["sha256"][:16]}'); bad += 1
        else:
            print(f'  ok  elevation/vendor/{fn} {h[:16]}')
    on_disk = sorted(p.name for p in VENDOR.iterdir() if p.name != 'manifest.json')
    extra = [f for f in on_disk if f not in files]
    if extra:
        print(f'FAIL  elevation/vendor has files the manifest does not pin: {extra}'); bad += 1
    if bad:
        raise SystemExit(f'fetch_dem --check: {bad} failure(s)')
    print(f'fetch_dem --check: {len(files)} vendored files match their sha256 pins')


def main():
    if '--check' in sys.argv[1:]:
        return check()
    cache = pathlib.Path(os.environ['ELEV_CACHE']) if 'ELEV_CACHE' in os.environ else \
        pathlib.Path(tempfile.mkdtemp(prefix='smartcitix-dem-'))
    cache.mkdir(parents=True, exist_ok=True)
    VENDOR.mkdir(parents=True, exist_ok=True)
    files, regions, xml_any = {}, {}, None
    for name, R in REGIONS.items():
        b, tiles, gz = build_region(name, cache)
        fn = f'{name}.u16.gz'
        (VENDOR / fn).write_bytes(gz)
        files[fn] = {'region': name, 'bytes': len(gz), 'sha256': sha(gz)}
        regions[name] = dict(b, what=R['what'], bounds_from=f'{R["registry"]}#{R["key"]}[*].bbox_wgs84 (union, snapped outward)',
                             file=fn, tiles=tiles)
        for t in tiles:
            if t['published'] and xml_any is None:
                xml_any = (cache / f'USGS_1_{t["tile"]}.xml').read_text('utf-8', 'replace')
        print(f'  {name}: {b["cols"]}x{b["rows"]} cells at {b["cell_arcsec"]}", '
              f'{sum(t["published"] for t in tiles)}/{len(tiles)} tiles published, {len(gz)} bytes')
    txt = constraints_text(xml_any).encode()
    CONSTRAINTS.write_bytes(txt)
    files[CONSTRAINTS.name] = {'region': None, 'bytes': len(txt), 'sha256': sha(txt)}
    manifest = {'source': SOURCE, 'base_url': BASE, 'licence': LICENCE, 'provenance': 'RECORDED',
                'src_arcsec': SRC_ARCSEC, 'src_nodata': SRC_NODATA,
                'encoding': {'dtype': 'uint16 little-endian', 'order': 'row-major, rows north->south, cols west->east',
                             'compression': 'gzip (mtime 0)', 'nodata_value': 0,
                             'height_m': 'v * 0.1 - 100.0', 'offset_m': OFFSET_M, 'scale_m': SCALE_M,
                             'cell_value': 'mean of the valid 1-arc-second source pixels in the cell; nodata when fewer than half are valid'},
                'regions': regions, 'files': files}
    MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True) + '\n')
    print(f'wrote {MANIFEST.relative_to(ROOT)} ({len(files)} files)')


if __name__ == '__main__':
    main()
