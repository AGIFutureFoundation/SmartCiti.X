#!/usr/bin/env python3
"""elevation/hillshade.py -> elevation/derived/hillshade_<region>.png + elevation/registry/hillshade.json (GROUND w16).

A same-origin relief-shading layer for the network geomap (web/build_geomap.py), made at BUILD time from the two
USGS 3DEP grids elevation/fetch_dem.py vendored (sha256-pinned in elevation/registry/elevation.json). No tile host,
no network: the page loads one PNG per region from this repository.

Provenance: every height is RECORDED (USGS 3DEP 1 arc-second, block-mean 6 arc-second cells, public domain); the
shading is DERIVED from them here (Horn gradient, one declared sun); the vertical exaggeration per region is an
AUTHORED styling choice and is declared, with its reason, in the registry and on the page.

The image: one RGBA pixel per grid cell. Ground facing the sun is white, ground facing away is black, flat ground is
fully transparent (alpha 0), so the layer reads on every map style. A cell with no RECORDED height, or with one in its
3 x 3 neighbourhood, is transparent - never shaded as if flat. Rows are resampled (nearest source row) to equal Web
Mercator steps between the grid's north and south edges, so a MapLibre image source placed on the grid's four corners
puts every row at its own latitude.

Deterministic: no clock, no randomness (Pillow PNG, fixed settings). Fail closed: a missing key or a vendored grid
that does not match its pinned sha256 stops the build by name.
  python3 elevation/hillshade.py           # write the PNGs and the registry
  python3 elevation/hillshade.py --check   # rebuild in memory, compare bytes, exit 1 on drift
"""
import gzip
import hashlib
import io
import json
import math
import pathlib
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
REG_IN = HERE / 'registry' / 'elevation.json'
REG_OUT = HERE / 'registry' / 'hillshade.json'
DERIVED = HERE / 'derived'
R_M = 6371008.8
SUN = {'azimuth_deg': 315.0, 'altitude_deg': 45.0}     # the cartographic convention: light from the north-west
ALPHA = {'shadow_max': 170, 'light_max': 110}          # alpha at full shadow / full light (0-255)
# AUTHORED styling: how many times the RECORDED heights are stretched before shading, per region, and why
EXAGGERATION = {
    'parishes': (10.0, 'the parish grid spans -8.7 to 115.9 m over about 230 km; at x1 its levees, ridges and the '
                      'Pleistocene terrace edge are below one grey level'),
    'bayarea': (1.5, 'the Bay Area grid spans -63.5 to 1432 m; x1.5 keeps the flats readable without the ranges '
                     'going black'),
}


class BuildError(SystemExit):
    pass


def need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise BuildError(f'elevation/hillshade.py: {where} is missing {k!r}')
    return d[k]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def merc_y(lat):
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def inv_merc(y):
    return math.degrees(2 * math.atan(math.exp(y)) - math.pi / 2)


def heights(region, g):
    """the vendored grid as float metres (NaN = nodata), after checking its pinned sha256"""
    fn = need(g, 'file', f'grids.{region}')
    gz = (HERE / 'vendor' / fn).read_bytes()
    if sha(gz) != need(g, 'sha256', f'grids.{region}'):
        raise BuildError(f'elevation/hillshade.py: vendor/{fn} does not match its pinned sha256 in elevation.json')
    enc = need(g, 'encoding', f'grids.{region}')
    rows, cols = need(g, 'rows', f'grids.{region}'), need(g, 'cols', f'grids.{region}')
    v = np.frombuffer(gzip.decompress(gz), dtype='<u2')
    if v.size != rows * cols:
        raise BuildError(f'elevation/hillshade.py: {fn} holds {v.size} cells, want {rows * cols}')
    v = v.reshape(rows, cols)
    h = v.astype(np.float64) * need(enc, 'scale_m', 'encoding') - need(enc, 'offset_m', 'encoding')
    h[v == need(enc, 'nodata_value', 'encoding')] = np.nan
    return h


def shade(h, n_deg, cell_deg, z):
    """Horn (1981) 3 x 3 gradient in metres (east-west cell width shrinks with cos(lat) row by row), one sun; returns
    shade in [0, 1] (NaN where the 3 x 3 window holds a nodata cell)"""
    rows, cols = h.shape
    p = np.pad(h, 1, mode='edge')
    a, b, c = p[:-2, :-2], p[:-2, 1:-1], p[:-2, 2:]
    d, f = p[1:-1, :-2], p[1:-1, 2:]
    g, hh, i = p[2:, :-2], p[2:, 1:-1], p[2:, 2:]
    dy_m = math.radians(cell_deg) * R_M
    lat = n_deg - (np.arange(rows) + 0.5) * cell_deg
    dx_m = (dy_m * np.cos(np.radians(lat)))[:, None]
    dzdx = ((c + 2 * f + i) - (a + 2 * d + g)) / (8 * dx_m) * z           # + east
    dzdy = ((g + 2 * hh + i) - (a + 2 * b + c)) / (8 * dy_m) * z          # + south (rows run south)
    zen = math.radians(90 - SUN['altitude_deg'])
    az = math.radians(SUN['azimuth_deg'])
    sx, sy, sz = math.sin(zen) * math.sin(az), math.sin(zen) * math.cos(az), math.cos(zen)   # sun vector: x east, y north
    # the surface normal (-dz/dx_east, -dz/dy_north, 1) = (-dzdx, +dzdy, 1), normalised
    nrm = np.sqrt(dzdx ** 2 + dzdy ** 2 + 1)
    s = (-dzdx * sx + dzdy * sy + sz) / nrm
    return np.clip(s, 0, 1)


def rgba(s, flat):
    """white with alpha above the flat value, black with alpha below it, transparent at flat and at NaN"""
    out = np.zeros(s.shape + (4,), dtype=np.uint8)
    ok = ~np.isnan(s)
    lit = ok & (s > flat)
    dark = ok & (s < flat)
    out[lit, 0:3] = 255
    out[lit, 3] = np.rint(np.minimum(1, (s[lit] - flat) / (1 - flat)) * ALPHA['light_max']).astype(np.uint8)
    out[dark, 3] = np.rint(np.minimum(1, (flat - s[dark]) / flat) * ALPHA['shadow_max']).astype(np.uint8)
    return out


def mercator_rows(img, n_deg, s_deg, cell_deg):
    """resample rows (nearest source row) to equal Web Mercator steps between the north and south edges"""
    rows = img.shape[0]
    yn, ys = merc_y(n_deg), merc_y(s_deg)
    src = []
    for k in range(rows):
        lat = inv_merc(yn + (k + 0.5) / rows * (ys - yn))
        src.append(min(rows - 1, max(0, int((n_deg - lat) / cell_deg))))
    return img[np.array(src)], src


def png(arr):
    buf = io.BytesIO()
    Image.fromarray(arr, 'RGBA').save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def build():
    E = json.loads(REG_IN.read_text())
    if need(E, 'provenance', 'elevation.json') != 'RECORDED':
        raise BuildError('elevation/hillshade.py: elevation.json is not RECORDED')
    grids = need(E, 'grids', 'elevation.json')
    att = need(E, 'attribution', 'elevation.json')
    flat = math.sin(math.radians(SUN['altitude_deg']))
    regions, files, stamp_in = {}, {}, []
    for region in sorted(EXAGGERATION):
        g = need(grids, region, 'elevation.json#grids')
        bd = need(g, 'bounds_deg', f'grids.{region}')
        n_deg, s_deg, w_deg, e_deg = (need(bd, k, f'grids.{region}.bounds_deg') for k in ('n', 's', 'w', 'e'))
        cell_deg = need(g, 'cell_arcsec', f'grids.{region}') / 3600
        z, why = EXAGGERATION[region]
        h = heights(region, g)
        s = shade(h, n_deg, cell_deg, z)
        img, src = mercator_rows(rgba(s, flat), n_deg, s_deg, cell_deg)
        b = png(img)
        rel = f'elevation/derived/hillshade_{region}.png'
        files[rel] = b
        valid = int((~np.isnan(s)).sum())
        stamp_in.append(need(g, 'sha256', f'grids.{region}'))
        regions[region] = {
            'file': rel, 'sha256': sha(b), 'bytes': len(b), 'width': int(img.shape[1]), 'height': int(img.shape[0]),
            # MapLibre image source corners: top-left, top-right, bottom-right, bottom-left (lng, lat)
            'coordinates': [[w_deg, n_deg], [e_deg, n_deg], [e_deg, s_deg], [w_deg, s_deg]],
            'grid': f'elevation/registry/elevation.json#grids.{region}', 'grid_sha256': g['sha256'],
            'cell_arcsec': g['cell_arcsec'], 'vertical_exaggeration': z, 'exaggeration_why': why,
            'shaded_cells': valid, 'transparent_cells': int(s.size - valid),
            'rows_resampled': 'nearest source row at equal Web Mercator steps between the north and south edges '
                              f'({len(set(src))} distinct source rows of {img.shape[0]})',
            'what': need(g, 'what', f'grids.{region}'),
        }
    stamp = sha(json.dumps({'grids': stamp_in, 'code': sha((HERE / 'hillshade.py').read_bytes()),
                            'sun': SUN, 'alpha': ALPHA}, sort_keys=True).encode())[:16]
    reg = {
        'pack': 'elevation-hillshade',
        'pack_version': need(json.loads((ROOT / 'pack/manifest.json').read_text()), 'pack_version', 'pack/manifest.json'),
        'source_stamp': stamp,
        'provenance': 'DERIVED', 'heights_provenance': 'RECORDED', 'exaggeration_provenance': 'AUTHORED',
        'label': 'Relief shading: USGS 3DEP heights (RECORDED), shaded at build time (DERIVED)',
        'source': 'elevation/registry/elevation.json (USGS 3DEP 1 arc-second, vendored and sha256-pinned)',
        'method': ('Horn 3 x 3 gradient in metres per cell (east-west width x cos(latitude) per row), one sun at '
                   f'azimuth {SUN["azimuth_deg"]:g} deg, altitude {SUN["altitude_deg"]:g} deg; facing the sun -> white, '
                   'facing away -> black, flat -> transparent; a cell with no RECORDED height in its 3 x 3 window is '
                   'transparent'),
        'sun': SUN, 'alpha': ALPHA,
        'credit': need(att, 'text', 'attribution') + ' (' + need(att, 'author', 'attribution') + ', U.S. public domain)',
        'licence_file': need(att, 'license_file', 'attribution'), 'source_url': need(att, 'source_url', 'attribution'),
        'honesty': ('The shading is computed from ~150-185 m cell means: it shows ridges, valleys, terraces and levee '
                    'belts at that scale, not street grades or buildings. Vertical exaggeration is a styling choice '
                    '(AUTHORED) declared per region. Same-origin files; no tile service is contacted.'),
        'regions': regions,
    }
    return reg, files


def dump(reg):
    return json.dumps(reg, indent=1, sort_keys=True, ensure_ascii=False) + '\n'


def main():
    reg, files = build()
    if '--check' in sys.argv[1:]:
        drift = [rel for rel, b in files.items() if not (ROOT / rel).exists() or (ROOT / rel).read_bytes() != b]
        if not REG_OUT.exists() or REG_OUT.read_text() != dump(reg):
            drift.append('elevation/registry/hillshade.json')
        if drift:
            raise SystemExit('elevation/hillshade.py --check: stale - rebuild: ' + ', '.join(drift))
        print('elevation/hillshade.py --check: registry/hillshade.json and the derived PNGs are current')
        return
    DERIVED.mkdir(exist_ok=True)
    for rel, b in files.items():
        (ROOT / rel).write_bytes(b)
    REG_OUT.write_text(dump(reg))
    print(f'elevation/hillshade.py: {len(files)} PNGs, ' + ', '.join(f'{k} {v["width"]}x{v["height"]} {v["bytes"]} B'
                                                                     for k, v in reg['regions'].items()) + f' (stamp {reg["source_stamp"]})')


if __name__ == '__main__':
    main()
