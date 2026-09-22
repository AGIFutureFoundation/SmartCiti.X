"""Vendor real-world land and water outlines, once, clipped to our campuses.

The maps in this bundle have drawn real coordinates over a generated
graticule: the positions were true and the world around them was a grid.
This fetches the actual shape of the land.

The source is Natural Earth, whose licence is one sentence long -
"Everything here is public domain." - which is the reason it is this and
not somewhere else. The GLB models supplied as references state no
copyright at all, and a file whose licence nobody wrote down cannot be
committed to a repository that ships a full SIL OFL beside every typeface
it serves.

This is NOT part of the build. It runs once, by hand, over the network, and
its output is committed. `--check` re-verifies the committed files against
the manifest offline, which is what verify_all.sh runs. Nothing in the
bundle fetches a coastline at run time.

Clipped, not whole: the global 10m coastline is 9.6 MB of LineStrings and
this bundle needs the water's edge around ten campuses. Each campus gets a
window sized here, the features are clipped to it, and the result is a
fraction of the whole. A repository that carried the world's coastline to
draw ten bays would be carrying 9.6 MB to use perhaps forty kilobytes.
"""
import hashlib
import json
import pathlib
import sys
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
VENDOR = HERE / 'vendor'
MANIFEST = VENDOR / 'manifest.json'

RAW = 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/'
# Each layer, and why this bundle wants it. A layer nobody draws is bytes
# nobody needs, so this list is short and every entry says its purpose.
LAYERS = {
    'coastline': ('geojson/ne_10m_coastline.geojson',
                  "the water's edge - the single line that makes a bay a bay"),
    'land': ('geojson/ne_10m_land.geojson',
             'land polygons, so a map can fill the ground rather than outline it'),
    'lakes': ('geojson/ne_10m_lakes.geojson',
              'inland water, which several of these campuses sit beside'),
    'rivers': ('geojson/ne_10m_rivers_lake_centerlines.geojson',
               'the rivers three of these cities were built on'),
}
LICENCE = ('LICENSE.md', 'the one-sentence public-domain statement, vendored '
                         'beside the data it licenses')

# How much world each campus gets, in degrees. A bay reads at about a
# degree; less and the far shore is missing, more and the file grows for
# scenery nobody looks at.
WINDOW_DEG = 1.4


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'smartcitix-terrain/1'})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def clip_ring(coords, box):
    """Keep the runs of a line that fall inside the window.

    Not a true polygon clip: this cuts a LineString into the pieces that lie
    inside the box and drops the rest, keeping one point of context either
    side so a line does not end short of the frame edge. A real Sutherland-
    Hodgman clip would be more correct at the boundary and would need a
    dependency; the frame is drawn over the top of this either way.
    """
    x0, y0, x1, y1 = box
    inside = lambda p: x0 <= p[0] <= x1 and y0 <= p[1] <= y1  # noqa: E731
    runs, cur = [], []
    for i, p in enumerate(coords):
        if inside(p):
            if not cur and i:
                cur.append(coords[i - 1])      # one point of lead-in
            cur.append(p)
        elif cur:
            cur.append(p)                      # one point of lead-out
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return [r for r in runs if len(r) > 1]


def clip_poly(ring, box):
    """Sutherland-Hodgman: clip a filled ring to the window, properly.

    The first version of this kept a polygon WHOLE if any one of its
    vertices fell inside the box. That is fine for an island and ruinous
    for a continent: the North America landmass was kept entire, for all
    ten campuses, and the land layer came out at 9,043 KB against the 61 KB
    of the coastline beside it. Clipping the rings brings it to a size that
    matches what is actually drawn.

    Four half-plane passes, no dependency. The algorithm is textbook and
    only correct for convex clip windows - a rectangle is convex, which is
    the whole reason the window is one.
    """
    x0, y0, x1, y1 = box
    edges = (
        (lambda p: p[0] >= x0, lambda a, b: (x0, a[1] + (b[1] - a[1]) * (x0 - a[0]) / (b[0] - a[0]))),
        (lambda p: p[0] <= x1, lambda a, b: (x1, a[1] + (b[1] - a[1]) * (x1 - a[0]) / (b[0] - a[0]))),
        (lambda p: p[1] >= y0, lambda a, b: (a[0] + (b[0] - a[0]) * (y0 - a[1]) / (b[1] - a[1]), y0)),
        (lambda p: p[1] <= y1, lambda a, b: (a[0] + (b[0] - a[0]) * (y1 - a[1]) / (b[1] - a[1]), y1)),
    )
    out = [tuple(p[:2]) for p in ring]
    for keep, cut in edges:
        if not out:
            return []
        src, out = out, []
        for i, cur in enumerate(src):
            prev = src[i - 1]
            ci, pi = keep(cur), keep(prev)
            if ci:
                if not pi:
                    out.append(cut(prev, cur))
                out.append(cur)
            elif pi:
                out.append(cut(prev, cur))
    # six decimals is about ten centimetres of longitude; the shoreline this
    # came from is nowhere near that accurate and the extra digits are noise
    return [[round(x, 6), round(y, 6)] for x, y in out]


def clip_feature(geom, box):
    """Return the geometry's pieces inside the box, or None."""
    t = geom['type']
    if t == 'LineString':
        runs = clip_ring(geom['coordinates'], box)
        return {'type': 'MultiLineString', 'coordinates': runs} if runs else None
    if t == 'MultiLineString':
        runs = [r for line in geom['coordinates'] for r in clip_ring(line, box)]
        return {'type': 'MultiLineString', 'coordinates': runs} if runs else None
    if t in ('Polygon', 'MultiPolygon'):
        polys = geom['coordinates'] if t == 'MultiPolygon' else [geom['coordinates']]
        keep = []
        for poly in polys:
            rings = [r for r in (clip_poly(ring, box) for ring in poly) if len(r) > 2]
            if rings:
                keep.append(rings)
        return {'type': 'MultiPolygon', 'coordinates': keep} if keep else None
    return None


def harvest():
    campuses = json.loads(
        (ROOT / 'geo/registry/campuses_geo.json').read_text())['campuses']
    VENDOR.mkdir(parents=True, exist_ok=True)

    lic = fetch(RAW + LICENCE[0]).decode('utf-8')
    if 'public domain' not in lic.lower():
        raise SystemExit('the Natural Earth licence no longer reads as public '
                         'domain - stop and read it before committing anything')
    (VENDOR / 'NATURAL_EARTH_LICENSE.md').write_text(lic, encoding='utf-8')

    files, srcbytes = {}, 0
    for name, (path, why) in LAYERS.items():
        raw = fetch(RAW + path)
        srcbytes += len(raw)
        whole = json.loads(raw)
        out = {}
        for ck, c in campuses.items():
            half = WINDOW_DEG / 2
            box = (c['lng'] - half, c['lat'] - half, c['lng'] + half, c['lat'] + half)
            feats = []
            for f in whole['features']:
                g = clip_feature(f['geometry'], box)
                if g:
                    feats.append({'type': 'Feature', 'geometry': g, 'properties': {}})
            out[ck] = {'bbox': [round(v, 4) for v in box],
                       'features': feats}
        blob = json.dumps({'layer': name, 'why': why,
                           'source': RAW + path,
                           'window_deg': WINDOW_DEG,
                           'campuses': out}, separators=(',', ':'))
        fn = f'ne_{name}.json'
        (VENDOR / fn).write_text(blob, encoding='utf-8')
        files[fn] = {'layer': name, 'why': why, 'from': RAW + path,
                     'bytes': len(blob.encode()),
                     'sha256': hashlib.sha256(blob.encode()).hexdigest(),
                     'features': {k: len(v['features']) for k, v in out.items()}}
        print(f'  {name:10} {len(blob)/1024:8.1f} KB clipped from '
              f'{len(raw)/1048576:.1f} MB')

    MANIFEST.write_text(json.dumps({
        'source': 'Natural Earth (naturalearthdata.com), 10m physical vectors',
        'licence': 'public domain - see NATURAL_EARTH_LICENSE.md, vendored beside this',
        'licence_sha256': hashlib.sha256(lic.encode('utf-8')).hexdigest(),
        'window_deg': WINDOW_DEG,
        'campuses': sorted(campuses),
        'upstream_bytes': srcbytes,
        'vendored_bytes': sum(f['bytes'] for f in files.values()),
        'files': dict(sorted(files.items())),
    }, indent=1) + '\n', encoding='utf-8')
    return files


def check():
    if not MANIFEST.exists():
        print('STALE: terrain/vendor/manifest.json is missing')
        print('       run: python3 terrain/fetch_terrain.py')
        return 1
    m = json.loads(MANIFEST.read_text(encoding='utf-8'))
    bad = []
    for name, rec in m['files'].items():
        p = VENDOR / name
        if not p.exists():
            bad.append(f'{name}: missing'); continue
        if hashlib.sha256(p.read_bytes()).hexdigest() != rec['sha256']:
            bad.append(f'{name}: sha256 does not match the manifest')
    lp = VENDOR / 'NATURAL_EARTH_LICENSE.md'
    if not lp.exists():
        bad.append('NATURAL_EARTH_LICENSE.md: missing, and this data may not '
                   'be redistributed without the statement that permits it')
    elif hashlib.sha256(lp.read_bytes()).hexdigest() != m['licence_sha256']:
        bad.append('NATURAL_EARTH_LICENSE.md: sha256 does not match the manifest')
    extra = sorted(p.name for p in VENDOR.glob('ne_*.json')
                   if p.name not in m['files'])
    bad += [f'{n}: on disk but not in the manifest' for n in extra]
    if bad:
        print('STALE: terrain/vendor')
        for b in bad:
            print('       ' + b)
        return 1
    print(f"terrain/vendor is current ({len(m['files'])} layers, "
          f"{m['vendored_bytes']:,} bytes clipped from "
          f"{m['upstream_bytes']:,}, {len(m['campuses'])} campuses)")
    return 0


if __name__ == '__main__':
    sys.exit(check() if '--check' in sys.argv else (harvest() and 0))
