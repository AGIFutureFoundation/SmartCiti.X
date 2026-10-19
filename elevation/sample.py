"""The one elevation sampler (ELEV_CONTRACT v1). Python 3 stdlib only.

    from elevation.sample import load_grid, height_m, height_world_m
    g = load_grid('parishes')                  # or 'bayarea'; KeyError-free: a missing field raises
    h = height_m(g, lat, lng)                  # metres NAVD88, or None (outside the grid / nodata)
    h = height_world_m(g, frame_origin, x, z)  # same, from a registry frame's scene metres

Rule, and the only rule (elevation/test.mjs re-implements it in JavaScript and
must agree with every pin in the registry):
  - cell (r, c) covers lat [n - (r+1)d, n - r d], lng [w + c d, w + (c+1) d],
    d = cell_arcsec / 3600, and its value applies at the cell centre;
  - inside the grid, a height is the bilinear blend of the four cell centres
    around the point (edges clamp to the outermost centres);
  - if any of those four is nodata, the height is the containing cell's own
    value, and None if that is nodata too;
  - outside the grid bounds: None. Never 0, never a default.
None means "no RECORDED height here"; the caller decides what to draw and
labels that choice (AUTHORED), it never substitutes a number silently.
"""
import gzip
import json
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
REGISTRY = HERE / 'registry' / 'elevation.json'


def _need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise SystemExit(f'elevation.sample: {where} is missing {k!r}')
    return d[k]


def load_grid(region, registry=None, vendor=None):
    reg = json.loads(pathlib.Path(registry or REGISTRY).read_text())
    grids = _need(reg, 'grids', 'elevation.json')
    g = _need(grids, region, 'elevation.json#grids')
    enc = _need(g, 'encoding', region)
    raw = gzip.decompress((pathlib.Path(vendor or HERE / 'vendor') / _need(g, 'file', region)).read_bytes())
    rows, cols = _need(g, 'rows', region), _need(g, 'cols', region)
    if len(raw) != rows * cols * 2:
        raise SystemExit(f'elevation.sample: {region} grid is {len(raw)} bytes, want {rows * cols * 2}')
    b = _need(g, 'bounds_arcsec', region)
    return {'region': region, 'rows': rows, 'cols': cols, 'raw': raw,
            'n': _need(b, 'n', region), 'w': _need(b, 'w', region), 'c': _need(g, 'cell_arcsec', region),
            'nodata': _need(enc, 'nodata_value', region), 'offset': _need(enc, 'offset_m', region),
            'scale': _need(enc, 'scale_m', region)}


def cell_m(g, r, c):
    """Height of one cell in metres, or None for nodata."""
    i = (r * g['cols'] + c) * 2
    v = g['raw'][i] | (g['raw'][i + 1] << 8)
    return None if v == g['nodata'] else round(v * g['scale'] - g['offset'], 1)


def height_m(g, lat, lng):
    fy = (g['n'] - lat * 3600.0) / g['c']          # rows from the north edge
    fx = (lng * 3600.0 - g['w']) / g['c']          # cols from the west edge
    if not (0 <= fy <= g['rows'] and 0 <= fx <= g['cols']):
        return None
    rc, cc = min(int(fy), g['rows'] - 1), min(int(fx), g['cols'] - 1)
    cy = min(max(fy - 0.5, 0.0), g['rows'] - 1.0)
    cx = min(max(fx - 0.5, 0.0), g['cols'] - 1.0)
    r0, c0 = int(math.floor(cy)), int(math.floor(cx))
    r1, c1 = min(r0 + 1, g['rows'] - 1), min(c0 + 1, g['cols'] - 1)
    ty, tx = cy - r0, cx - c0
    q = [cell_m(g, r0, c0), cell_m(g, r0, c1), cell_m(g, r1, c0), cell_m(g, r1, c1)]
    if any(v is None for v in q):
        return cell_m(g, rc, cc)
    top = q[0] + (q[1] - q[0]) * tx
    bot = q[2] + (q[3] - q[2]) * tx
    return round(top + (bot - top) * ty, 2)


R_M = 6371008.8


def height_world_m(g, origin, x, z):
    """Scene metres (x = east, z = -north) about a registry frame origin {'lat','lng'} -> height_m.

    The inverse of the registries' equirectangular LTP (parishes.json#frames.ltp_formula)."""
    lat0, lng0 = _need(origin, 'lat', 'origin'), _need(origin, 'lng', 'origin')
    lat = lat0 + math.degrees(-z / R_M)
    lng = lng0 + math.degrees(x / (R_M * math.cos(math.radians(lat0))))
    return height_m(g, lat, lng)


def resample_world(g, origin, x0, z0, dx, dz, cols, rows):
    """A scene-metre lattice for a page: heights[j * cols + i] = height_world_m(g, origin, x0 + i*dx, z0 + j*dz).

    Returns {'heights': [float | None, ...], 'none_count': int, 'provenance': 'RECORDED', ...}. None entries are
    kept as None: the caller fills them by an explicit, labelled AUTHORED rule (never 0 by default)."""
    hs = [height_world_m(g, origin, x0 + i * dx, z0 + j * dz) for j in range(rows) for i in range(cols)]
    return {'heights': hs, 'none_count': sum(h is None for h in hs), 'cols': cols, 'rows': rows,
            'x0': x0, 'z0': z0, 'dx': dx, 'dz': dz, 'units': 'm', 'provenance': 'RECORDED',
            'source': 'elevation/registry/elevation.json#grids.' + g['region'] + ' (USGS 3DEP 1 arc-second, public domain)'}
