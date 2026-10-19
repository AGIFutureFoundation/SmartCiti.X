"""Vendor RECORDED land cover, once, clipped to the parish and Bay worlds.

Source: ESA WorldCover 10 m 2021 v200 (Cloud Optimized GeoTIFF tiles, 3x3 degrees, EPSG:4326) on
esa-worldcover.s3.eu-central-1.amazonaws.com, which answers from the build machine. Licence: CC BY 4.0
(the tile metadata's own `license` item). Attribution and citation are copied verbatim from the tiles'
`copyright` item and from section 5 of the product user manual (WorldCover_PUM_V2.0.pdf, same bucket)
into vendor/WORLDCOVER_ATTRIBUTION.txt; the full CC BY 4.0 legal code is vendored as
vendor/LICENSE_CC-BY-4.0.txt, taken from the npm package spdx-license-list (itself CC0-1.0), because
creativecommons.org does not answer from here.

WHAT IS VENDORED. Per region (the same union of registry bbox_wgs84 as elevation/fetch_dem.py uses:
13 parishes; 9 Bay counties), one grid at CELL_ARCSEC. MODIFICATIONS (CC BY 4.0 requires saying so):
each cell holds the MAJORITY WorldCover class of the 10 m pixels inside it (ties -> the lower class
code); a cell with fewer than half its pixels carrying a class is nodata (0). Stored as uint8 class
codes (WorldCover's own: 10 tree cover ... 100 moss and lichen), row-major, rows north->south, cols
west->east, gzip-compressed with mtime 0. Unspoken Smiles is AUTHORED with no real anchor: no grid.

Not part of the build: run once by hand over the network; output committed. `--check` re-verifies the
committed files against the manifest offline (verify_all). Needs numpy + PIL (+ pdftotext) only to fetch.

  LC_CACHE=/dir python3 landcover/fetch_landcover.py     # fetch (reusing downloaded tiles in /dir)
  python3 landcover/fetch_landcover.py --check          # offline sha256 verification
"""
import gzip
import hashlib
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import tarfile
import io
import tempfile
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
VENDOR = HERE / 'vendor'
MANIFEST = VENDOR / 'manifest.json'
ATTRIB = VENDOR / 'WORLDCOVER_ATTRIBUTION.txt'
LICENCE = VENDOR / 'LICENSE_CC-BY-4.0.txt'

BUCKET = 'https://esa-worldcover.s3.eu-central-1.amazonaws.com/'
TILE_URL = BUCKET + 'v200/2021/map/ESA_WorldCover_10m_2021_v200_{t}_Map.tif'
PUM_URL = BUCKET + 'v200/2021/docs/WorldCover_PUM_V2.0.pdf'
SPDX_META = 'https://registry.npmjs.org/spdx-license-list/latest'
SRC_PX_PER_DEG = 12000                       # 10 m product: 1/12000 degree pixels
CELL_ARCSEC = 3                              # 92.6 m north-south; 9 x 9 source pixels per cell
CLASSES = {10: 'tree cover', 20: 'shrubland', 30: 'grassland', 40: 'cropland', 50: 'built-up',
           60: 'bare / sparse vegetation', 70: 'snow and ice', 80: 'permanent water bodies',
           90: 'herbaceous wetland', 95: 'mangroves', 100: 'moss and lichen'}
REGIONS = {
    'parishes': ('parishes/registry/parishes.json', 'parishes', 'the 13 parishes of the parish worlds, Louisiana'),
    'bayarea': ('bayarea/registry/bayarea.json', 'counties', 'the 9 San Francisco Bay Area counties of the Bay world, California'),
}


def need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise SystemExit(f'fetch_landcover: {where} is missing {k!r}')
    return d[k]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'smartcitix-landcover/1'})
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.read()


def region_bounds(name):
    rel, key, _ = REGIONS[name]
    items = need(json.loads((ROOT / rel).read_text()), key, rel)
    items = list(items.values()) if isinstance(items, dict) else list(items)
    boxes = [need(it, 'bbox_wgs84', f'{rel}#{key}') for it in items]
    if not boxes:
        raise SystemExit(f'fetch_landcover: {rel} has no {key}')
    c = CELL_ARCSEC
    W = math.floor(min(b[0] for b in boxes) * 3600 / c) * c
    S = math.floor(min(b[1] for b in boxes) * 3600 / c) * c
    E = math.ceil(max(b[2] for b in boxes) * 3600 / c) * c
    N = math.ceil(max(b[3] for b in boxes) * 3600 / c) * c
    return {'w_arcsec': W, 's_arcsec': S, 'e_arcsec': E, 'n_arcsec': N, 'cell_arcsec': c,
            'cols': (E - W) // c, 'rows': (N - S) // c, 'members': len(boxes)}


def tiles_for(b):
    """WorldCover tiles are named by their SW corner on a 3-degree grid."""
    out = []
    for lat in range(math.floor(b['s_arcsec'] / 3600 / 3) * 3, math.ceil(b['n_arcsec'] / 3600 / 3) * 3, 3):
        for lng in range(math.floor(b['w_arcsec'] / 3600 / 3) * 3, math.ceil(b['e_arcsec'] / 3600 / 3) * 3, 3):
            if lat < 0 or lng >= 0:
                raise SystemExit('fetch_landcover: only the N/W quadrant is handled')
            out.append((f'N{lat:02d}W{-lng:03d}', lat, lng))
    return out


def gdal_meta(im):
    xml = need(dict(im.tag_v2), 42112, 'GDAL metadata')
    return {m.group(1): m.group(2).strip() for m in re.finditer(r'<Item name="([^"]+)">(.*?)</Item>', xml, re.S)}


def build_region(name, cache):
    import numpy as np
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    b = region_bounds(name)
    c = CELL_ARCSEC
    k = SRC_PX_PER_DEG * c // 3600                    # source pixels per cell side (9)
    out = np.zeros((b['rows'], b['cols']), dtype=np.uint8)
    codes = np.array(sorted(CLASSES), dtype=np.uint8)
    tiles, meta_any = [], None
    for t, lat, lng in tiles_for(b):
        p = cache / f'{t}.tif'
        if not p.exists():
            p.write_bytes(fetch(TILE_URL.format(t=t)))
        blob = p.read_bytes()
        im = Image.open(p)
        md = gdal_meta(im)
        scale, tie = im.tag_v2[33550], im.tag_v2[33922]
        if abs(scale[0] * SRC_PX_PER_DEG - 1) > 1e-9 or tie[3] != lng or tie[4] != lat + 3:
            raise SystemExit(f'fetch_landcover: {t} geometry is not the 3-degree 10 m grid')
        a = np.asarray(im)
        # the part of the region inside this tile, in whole cells
        tw, tn = lng * 3600, (lat + 3) * 3600
        c0 = max(0, (tw - b['w_arcsec']) // c); c1 = min(b['cols'], (tw + 10800 - b['w_arcsec']) // c)
        r0 = max(0, (b['n_arcsec'] - tn) // c); r1 = min(b['rows'], (b['n_arcsec'] - (tn - 10800)) // c)
        if r0 < r1 and c0 < c1:
            py = (tn - (b['n_arcsec'] - r0 * c)) * SRC_PX_PER_DEG // 3600
            px = (b['w_arcsec'] + c0 * c - tw) * SRC_PX_PER_DEG // 3600
            crop = a[py:py + (r1 - r0) * k, px:px + (c1 - c0) * k]
            blk = crop.reshape(r1 - r0, k, c1 - c0, k).transpose(0, 2, 1, 3).reshape(r1 - r0, c1 - c0, k * k)
            counts = np.stack([(blk == v).sum(axis=2) for v in codes], axis=-1)
            best = codes[counts.argmax(axis=-1)]
            valid = counts.sum(axis=-1)
            best[valid * 2 < k * k] = 0
            out[r0:r1, c0:c1] = best
        tiles.append({'tile': t, 'url': TILE_URL.format(t=t), 'bytes': len(blob), 'sha256': sha(blob),
                      'product_version': need(md, 'product_version', t), 'license': need(md, 'license', t),
                      'copyright': need(md, 'copyright', t), 'time_start': need(md, 'time_start', t),
                      'time_end': need(md, 'time_end', t)})
        meta_any = md
        del a, im
    gz = gzip.compress(out.tobytes(), compresslevel=9, mtime=0)
    return b, tiles, gz, meta_any


def pum_section(cache):
    p = cache / 'WorldCover_PUM_V2.0.pdf'
    if not p.exists():
        p.write_bytes(fetch(PUM_URL))
    txt = subprocess.run(['pdftotext', '-layout', str(p), '-'], capture_output=True, check=True, text=True).stdout
    m = re.search(r'5\.1 License.*?doi:10\.5281/zenodo\.7254221\.', txt, re.S)
    if not m:
        raise SystemExit('fetch_landcover: PUM section 5.1-5.2 not found')
    return '\n'.join(l.rstrip() for l in m.group(0).splitlines() if l.strip()), sha(p.read_bytes())


def spdx_cc_by():
    meta = json.loads(fetch(SPDX_META))
    tgz = fetch(meta['dist']['tarball'])
    with tarfile.open(fileobj=io.BytesIO(tgz)) as tf:
        d = json.load(tf.extractfile('package/licenses/CC-BY-4.0.json'))
    return d['licenseText'], meta['version'], meta['dist']['tarball'], sha(tgz)


def check():
    if not MANIFEST.exists():
        raise SystemExit('fetch_landcover --check: landcover/vendor/manifest.json is missing')
    files = need(json.loads(MANIFEST.read_text()), 'files', 'manifest')
    bad = 0
    for fn, rec in sorted(files.items()):
        p = VENDOR / fn
        h = sha(p.read_bytes()) if p.exists() else 'missing'
        if h != need(rec, 'sha256', fn):
            print(f'FAIL  landcover/vendor/{fn} sha256 {h[:16]} != manifest {rec["sha256"][:16]}'); bad += 1
        else:
            print(f'  ok  landcover/vendor/{fn} {h[:16]}')
    extra = sorted(p.name for p in VENDOR.iterdir() if p.name != 'manifest.json' and p.name not in files)
    if extra:
        print(f'FAIL  landcover/vendor has files the manifest does not pin: {extra}'); bad += 1
    if bad:
        raise SystemExit(f'fetch_landcover --check: {bad} failure(s)')
    print(f'fetch_landcover --check: {len(files)} vendored files match their sha256 pins')


def main():
    if '--check' in sys.argv[1:]:
        return check()
    cache = pathlib.Path(os.environ['LC_CACHE']) if 'LC_CACHE' in os.environ else \
        pathlib.Path(tempfile.mkdtemp(prefix='smartcitix-lc-'))
    cache.mkdir(parents=True, exist_ok=True)
    VENDOR.mkdir(parents=True, exist_ok=True)
    files, regions, md = {}, {}, None
    for name, (rel, key, what) in REGIONS.items():
        b, tiles, gz, md = build_region(name, cache)
        fn = f'{name}.u8.gz'
        (VENDOR / fn).write_bytes(gz)
        files[fn] = {'region': name, 'bytes': len(gz), 'sha256': sha(gz)}
        regions[name] = dict(b, what=what, file=fn, tiles=tiles,
                             bounds_from=f'{rel}#{key}[*].bbox_wgs84 (union, snapped outward)')
        print(f'  {name}: {b["cols"]}x{b["rows"]} cells at {CELL_ARCSEC}", {len(tiles)} tiles, {len(gz)} bytes')
    pum, pum_sha = pum_section(cache)
    attrib = '\n'.join([
        'ESA WorldCover 10 m 2021 v200 - attribution, licence and citation, copied verbatim from the source.',
        '',
        'From the GeoTIFF metadata of every tile used (items "copyright" and "license"):',
        'copyright: ' + need(md, 'copyright', 'tile metadata'),
        'license: ' + need(md, 'license', 'tile metadata'),
        '',
        'From WorldCover_PUM_V2.0.pdf (' + PUM_URL + '), sections 5.1-5.2:',
        pum,
        '',
        'Map attribution used by this bundle (the 2021 form of the text above):',
        '© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium',
        '',
        'Modifications made by this bundle (CC BY 4.0 section 3(a)(1)(B)): majority class of the 10 m pixels per',
        f'{CELL_ARCSEC} arc-second cell, cells under half classified set to 0 (nodata), clipped to the union of the',
        'registry bounding boxes of the 13 parishes and the 9 Bay counties (landcover/fetch_landcover.py).',
        'ESA and the WorldCover consortium have not endorsed this bundle.', ''])
    ATTRIB.write_text(attrib)
    lic, spdx_ver, spdx_url, spdx_sha = spdx_cc_by()
    LICENCE.write_text(lic if lic.endswith('\n') else lic + '\n')
    for p in (ATTRIB, LICENCE):
        files[p.name] = {'region': None, 'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
    manifest = {'source': 'ESA WorldCover 10 m 2021 v200', 'bucket': BUCKET, 'licence': 'CC-BY-4.0',
                'licence_text_from': f'{spdx_url} (spdx-license-list {spdx_ver}, CC0-1.0; tarball sha256 {spdx_sha})',
                'pum': {'url': PUM_URL, 'sha256': pum_sha}, 'provenance': 'RECORDED',
                'cell_arcsec': CELL_ARCSEC, 'src_px_per_deg': SRC_PX_PER_DEG,
                'classes': {str(k): v for k, v in CLASSES.items()},
                'encoding': {'dtype': 'uint8', 'order': 'row-major, rows north->south, cols west->east',
                             'compression': 'gzip (mtime 0)', 'nodata_value': 0,
                             'cell_value': 'majority WorldCover class code of the 10 m pixels in the cell (ties -> lower code); '
                                           '0 when fewer than half the pixels carry a class'},
                'regions': regions, 'files': files}
    MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False) + '\n')
    print(f'wrote {MANIFEST.relative_to(ROOT)} ({len(files)} files)')


if __name__ == '__main__':
    main()
