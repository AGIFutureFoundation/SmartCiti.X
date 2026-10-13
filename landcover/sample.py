"""The one land-cover sampler (LANDCOVER_CONTRACT v1). Python 3 stdlib only.

    from landcover.sample import load_grid, class_at, landcover_at, resample_world
    g = load_grid('parishes')                   # or 'bayarea'; a missing field raises by name
    k = class_at(g, lat, lng)                   # WorldCover class code (10 tree cover ... 95 mangroves), or None
    k = landcover_at(g, origin, x, z)           # same, from scene metres about a registry frame origin
    L = resample_world(g, origin, x0, z0, dx, dz, cols, rows)

Rule: classes are categories, never interpolated - a point takes the class of the cell containing it
(cell (r, c) covers lat [n-(r+1)d, n-r d], lng [w+c d, w+(c+1)d], d = cell_arcsec/3600; a point on the
south/east outer edge belongs to the last row/col). Nodata (0) and points outside the grid -> None,
never a default class. None means "no RECORDED land cover here": the caller picks an AUTHORED rule and
labels it. Frames: the same equirectangular LTP inverse as elevation/sample.py (x east, z = -north).
"""
import gzip
import json
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
REGISTRY = HERE / 'registry' / 'landcover.json'
R_M = 6371008.8


def _need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise SystemExit(f'landcover.sample: {where} is missing {k!r}')
    return d[k]


def load_grid(region, registry=None, vendor=None):
    reg = json.loads(pathlib.Path(registry or REGISTRY).read_text())
    g = _need(_need(reg, 'grids', 'landcover.json'), region, 'landcover.json#grids')
    raw = gzip.decompress((pathlib.Path(vendor or HERE / 'vendor') / _need(g, 'file', region)).read_bytes())
    rows, cols = _need(g, 'rows', region), _need(g, 'cols', region)
    if len(raw) != rows * cols:
        raise SystemExit(f'landcover.sample: {region} grid is {len(raw)} bytes, want {rows * cols}')
    b = _need(g, 'bounds_arcsec', region)
    return {'region': region, 'rows': rows, 'cols': cols, 'raw': raw, 'n': _need(b, 'n', region),
            'w': _need(b, 'w', region), 'c': _need(g, 'cell_arcsec', region),
            'nodata': _need(_need(g, 'encoding', region), 'nodata_value', region),
            'names': {int(k): v for k, v in _need(reg, 'classes', 'landcover.json').items()}}


def class_at(g, lat, lng):
    fy = (g['n'] - lat * 3600.0) / g['c']
    fx = (lng * 3600.0 - g['w']) / g['c']
    if not (0 <= fy <= g['rows'] and 0 <= fx <= g['cols']):
        return None
    v = g['raw'][min(int(fy), g['rows'] - 1) * g['cols'] + min(int(fx), g['cols'] - 1)]
    return None if v == g['nodata'] else v


def landcover_at(g, origin, x, z):
    lat0, lng0 = _need(origin, 'lat', 'origin'), _need(origin, 'lng', 'origin')
    lat = lat0 + math.degrees(-z / R_M)
    lng = lng0 + math.degrees(x / (R_M * math.cos(math.radians(lat0))))
    return class_at(g, lat, lng)


def resample_world(g, origin, x0, z0, dx, dz, cols, rows):
    """classes[j * cols + i] = landcover_at(g, origin, x0 + i*dx, z0 + j*dz); None kept (fill by a labelled AUTHORED rule)."""
    ks = [landcover_at(g, origin, x0 + i * dx, z0 + j * dz) for j in range(rows) for i in range(cols)]
    return {'classes': ks, 'none_count': sum(k is None for k in ks), 'names': g['names'], 'cols': cols, 'rows': rows,
            'x0': x0, 'z0': z0, 'dx': dx, 'dz': dz, 'provenance': 'RECORDED',
            'source': 'landcover/registry/landcover.json#grids.' + g['region'] + ' (ESA WorldCover 10 m 2021 v200, CC BY 4.0)'}
