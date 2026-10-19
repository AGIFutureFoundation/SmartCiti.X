#!/usr/bin/env python3
"""City life (Sims-like play): AUTHORED game lots, generic business types, rentals and PLAY-COIN rules.

Nothing here is money. Coins are play coins - not money, never exchangeable, never bought, never linked to
payments/. Every lot is an AUTHORED game lot placed on PARISH's AUTHORED procedural fabric: NOT a real property,
address, listing or business. Numbers (coins, sizes, day length) are AUTHORED game-balance values.

Placement (DERIVED from registries already in the repo, fail closed):
  - parishes from parishes/registry/parishes.json selection.selected;
  - candidate points on a GRID_M grid around each parish LOCAL origin, nearest first;
  - kept only inside the RECORDED coarse outline (even-odd, holes honoured);
  - kept only outside WATER_KEEPOUT_M of every registry.water.labels point (inland water is not cut out of the
    outline; the keep-out is an AUTHORED approximation, not a shoreline);
  - land use at the point is DERIVED from PARISH's own AUTHORED ground tile: pixels in a WIN x WIN window are
    matched to the exact block/building tints parishes/render.py paints; a lot needs a MAJ share of one zone
    (residential or commercial) and none of the other;
  - lots keep MIN_GAP_M apart; up to PER_ZONE lots per zone per parish.
Business trade ids must be slugs in unions/registry/unions.json (build fails by name otherwise).
"""
import hashlib
import json
import math
import pathlib
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'economy.json'
PARISHES = ROOT / 'parishes' / 'registry' / 'parishes.json'
UNIONS = ROOT / 'unions' / 'registry' / 'unions.json'
RENDER = ROOT / 'parishes' / 'render.py'

GRID_M = 200.0
SEARCH_M = 32000.0
WATER_KEEPOUT_M = 12000.0
WIN = 9
MAJ = 0.15
TOL = 4.0
MARGIN = 3.0
MIN_GAP_M = 240.0
PER_ZONE = 5
LOT_SIZE_M = {'commercial': [24, 30], 'residential': [18, 30]}

COIN_RULES = {
    'unit': 'coins', 'note': 'play coins - not money', 'start_balance': 500, 'day_ms': 60000,
    'overdraft': False, 'eviction_after_unpaid_days': 3, 'practice_days': 1,
    'provenance': 'AUTHORED',
    'what': 'AUTHORED game-balance values for play; never exchangeable, never bought, never linked to payments.',
}
RENTALS = {
    'home': {'zone': 'residential', 'rent_coins_per_day': 12, 'buy_coins': 360, 'provenance': 'AUTHORED'},
    'shop': {'zone': 'commercial', 'rent_coins_per_day': 25, 'buy_coins': 750, 'provenance': 'AUTHORED'},
}
# (id, label, trade slug or None for generic)
BUSINESSES = [
    ('electrical-shop', 'Electrical contractor shop', 'electricians'),
    ('plumbing-shop', 'Plumbing and pipefitting shop', 'pipefitters'),
    ('carpentry-shop', 'Carpentry and cabinet shop', 'carpenters'),
    ('welding-shop', 'Welding and fabrication shop', 'welders'),
    ('hvac-service', 'Heating and cooling service', 'hvacr'),
    ('landscape-yard', 'Landscaping yard', 'grounds'),
    ('paint-shop', 'Painting contractor shop', 'painters'),
    ('machine-shop', 'Machine shop', 'machinists'),
    ('diesel-garage', 'Diesel repair garage', 'fleet-diesel'),
    ('glass-shop', 'Glass and glazing shop', 'glaziers'),
    ('bakery', 'Bakery', None),
    ('boat-repair', 'Boat repair', None),
    ('tool-rental', 'Tool rental', None),
    ('corner-grocery', 'Corner grocery', None),
]
TRADE_ECON = {'setup_coins': 150, 'income_coins_per_day_skilled': 60, 'income_coins_per_day_unskilled': 30,
              'staff_bonus_coins_per_day': 20, 'staff_wage_coins_per_day': 12, 'max_staff': 3}
GENERIC_ECON = {'setup_coins': 120, 'income_coins_per_day_skilled': 40, 'income_coins_per_day_unskilled': 40,
                'staff_bonus_coins_per_day': 18, 'staff_wage_coins_per_day': 12, 'max_staff': 3}


def die(msg):
    sys.stderr.write('economy/build.py: ' + msg + '\n')
    sys.exit(1)


def need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        die('missing field %s in %s' % (k, where))
    return d[k]


def render_tints():
    """the exact block/building tints parishes/render.py paints (read from its USE table, not retyped)."""
    src = RENDER.read_text()
    ns = {}
    start = src.index('USE = {')
    end = src.index('}', start) + 1
    exec(src[start:end], ns)
    use = ns['USE']
    t = {}
    for z in ('residential', 'commercial', 'park', 'industrial'):
        if z not in use:
            die('parishes/render.py USE has no %s tint' % z)
        block, bld = use[z]
        t[z] = [block] + ([bld] if bld else [])
    return t


def pip(rings, e, n):
    inside = False
    for ring in rings:
        k = len(ring)
        for i in range(k):
            (x1, y1), (x2, y2) = ring[i], ring[(i + 1) % k]
            if (y1 > n) != (y2 > n) and e < (x2 - x1) * (n - y1) / (y2 - y1) + x1:
                inside = not inside
    return inside


def main():
    P = json.loads(PARISHES.read_text())
    U = json.loads(UNIONS.read_text())
    slugs = {need(u, 'slug', 'unions.json#unions[]') for u in need(U, 'unions', 'unions.json')}
    for bid, _, trade in BUSINESSES:
        if trade is not None and trade not in slugs:
            die('business %s trade_id %s is not a slug in unions/registry/unions.json' % (bid, trade))
    tints = render_tints()
    names, zone_of = [], []
    for z, cols in tints.items():
        for c in cols:
            names.append(c)
            zone_of.append(z)
    C = np.array(names, dtype=np.float64)
    labels = need(need(P, 'water', 'parishes.json'), 'labels', 'parishes.json#water')
    wpts = [(need(l, 'name', 'water.labels[]'), need(l, 'world_m', 'water.labels[]')) for l in labels]
    selected = need(need(P, 'selection', 'parishes.json'), 'selected', 'parishes.json#selection')
    hasher = hashlib.sha256()
    for p in (pathlib.Path(__file__), PARISHES, UNIONS, RENDER):
        hasher.update(p.read_bytes())
    out_parishes, counts = {}, {'parishes': 0, 'lots': 0, 'commercial': 0, 'residential': 0, 'tiles_read': 0}
    for fips in selected:
        par = need(need(P, 'parishes', 'parishes.json'), fips, 'parishes.json#parishes')
        rings = [r for poly in need(par, 'outline_local_m', fips) for r in poly]
        org = need(need(par, 'frame', fips), 'origin_in_world_m', fips + '.frame')
        tiles = need(need(need(par, 'map', fips), 'ground_tiles', fips + '.map'), 'tiles', fips + '.ground_tiles')
        cache = {}

        def tile_at(e, n):
            for t in tiles:
                b = need(t, 'bounds_local_m', 'tile')
                if b['left'] <= e < b['right'] and b['bottom'] < n <= b['top']:
                    return t, b
            return None, None

        def zone_at(e, n):
            t, b = tile_at(e, n)
            if t is None:
                return None
            path = need(t, 'path', 'tile')
            if path not in cache:
                raw = (ROOT / path).read_bytes()
                hasher.update(raw)
                import io
                cache[path] = np.asarray(Image.open(io.BytesIO(raw)).convert('RGB')).astype(np.float64)
                counts['tiles_read'] += 1
            im = cache[path]
            h, w = im.shape[0], im.shape[1]
            px = int((e - b['left']) / (b['right'] - b['left']) * w)
            py = int((b['top'] - n) / (b['top'] - b['bottom']) * h)
            r = WIN // 2
            if px - r < 0 or py - r < 0 or px + r >= w or py + r >= h:
                return None
            win = im[py - r:py + r + 1, px - r:px + r + 1].reshape(-1, 3)
            d = np.sqrt(((win[:, None, :] - C[None]) ** 2).sum(-1))
            o = np.sort(d, -1)
            ok = (o[:, 0] < TOL) & (o[:, 1] - o[:, 0] > MARGIN)
            lab = d.argmin(-1)
            tally = {}
            for good, li in zip(ok, lab):
                if good:
                    tally[zone_of[li]] = tally.get(zone_of[li], 0) + 1
            for z, other in (('commercial', 'residential'), ('residential', 'commercial')):
                if tally.get(z, 0) >= MAJ * WIN * WIN and tally.get(other, 0) * 5 <= tally.get(z, 0):
                    return z
            return None

        k = int(SEARCH_M // GRID_M)
        cand = [(i * GRID_M, j * GRID_M) for i in range(-k, k + 1) for j in range(-k, k + 1)
                if math.hypot(i, j) * GRID_M <= SEARCH_M]
        cand.sort(key=lambda p: (round(math.hypot(p[0], p[1]), 3), p[0], p[1]))
        lots, per = [], {'commercial': 0, 'residential': 0}
        for e, n in cand:
            if per['commercial'] >= PER_ZONE and per['residential'] >= PER_ZONE:
                break
            if not pip(rings, e, n):
                continue
            we, wn = e + org[0], n + org[1]
            if any(math.hypot(we - q[0], wn - q[1]) < WATER_KEEPOUT_M for _, q in wpts):
                continue
            if any(math.hypot(e - l['local_m'][0], n - l['local_m'][1]) < MIN_GAP_M for l in lots):
                continue
            z = zone_at(e, n)
            if z is None or per[z] >= PER_ZONE:
                continue
            per[z] += 1
            kind = 'shop' if z == 'commercial' else 'home'
            lots.append({
                'id': 'lot-%s-%s%02d' % (fips, z[0], per[z]), 'parish': fips, 'zone': z,
                'local_m': [int(e), int(n)], 'x': int(e), 'z': -int(n), 'size_m': LOT_SIZE_M[z],
                'allowed': [kind], 'rent_coins_per_day': RENTALS[kind]['rent_coins_per_day'],
                'buy_coins': RENTALS[kind]['buy_coins'], 'provenance': 'AUTHORED',
                'landuse_provenance': 'DERIVED',
                'label': 'AUTHORED game lot - not a real property or address',
            })
        out_parishes[fips] = {'name': need(par, 'name', fips), 'lots': lots,
                              'counts': {'lots': len(lots), 'commercial': per['commercial'],
                                         'residential': per['residential'],
                                         'shop_rentals': per['commercial'], 'home_rentals': per['residential']}}
        counts['parishes'] += 1
        counts['lots'] += len(lots)
        counts['commercial'] += per['commercial']
        counts['residential'] += per['residential']
    btypes = []
    for bid, label, trade in BUSINESSES:
        b = {'id': bid, 'label': label, 'trade_id': trade, 'zone': 'commercial',
             'generic': trade is None, 'provenance': 'AUTHORED'}
        b.update(TRADE_ECON if trade else GENERIC_ECON)
        btypes.append(b)
    counts['business_types'] = len(btypes)
    counts['trade_linked'] = sum(1 for b in btypes if b['trade_id'])
    full = hasher.hexdigest()
    reg = {
        'pack': 'economy', 'pack_version': json.loads((ROOT / 'pack' / 'manifest.json').read_text(encoding='utf-8'))['pack_version'], 'source_stamp': full[:16], 'source_stamp_sha256': full,
        'inputs': ['economy/build.py', 'parishes/registry/parishes.json', 'unions/registry/unions.json',
                   'parishes/render.py#USE', 'parishes/maps/tiles/*.webp (read)'],
        'provenance_tiers': ['DERIVED', 'AUTHORED'],
        'honesty': {
            'coins': 'Play coins - not money: never exchangeable, never bought, never linked to payments.',
            'lots': 'Lots, shops and rentals are AUTHORED game lots on the AUTHORED map fabric - not real properties, addresses, listings or businesses.',
            'state': 'State stays in this browser (localStorage); no account, no server, no network.',
            'games': 'City life is play: it never enters a completion record and certifies nothing.',
        },
        'placement': {
            'rule': 'grid %d m around each parish LOCAL origin (nearest first, within %d m), inside the RECORDED outline, outside the water keep-out, min gap %d m, up to %d lots per zone' % (GRID_M, SEARCH_M, MIN_GAP_M, PER_ZONE),
            'landuse_method': 'DERIVED: %dx%d pixel window of PARISH AUTHORED ground tile matched to parishes/render.py USE tints (tol %.0f, margin %.0f); >= %d%% one zone and the other zone <= 1/5 of it' % (WIN, WIN, TOL, MARGIN, int(MAJ * 100)),
            'water_keepout': {'radius_m': WATER_KEEPOUT_M, 'around': [n for n, _ in wpts], 'provenance': 'AUTHORED',
                              'note': 'approximate; inland water is not cut out of the outlines, this is not a shoreline'},
            'frame': 'parish LOCAL metres (PARISH contract); x = east_m, z = -north_m',
        },
        'coin_rules': COIN_RULES, 'rentals': RENTALS, 'business_types': btypes,
        'counts': counts, 'parishes': out_parishes,
    }
    OUT.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + '\n')
    print('economy: %d parishes, %d lots (%d commercial, %d residential), %d business types, stamp %s' % (
        counts['parishes'], counts['lots'], counts['commercial'], counts['residential'], len(btypes), full[:16]))
    for f, p in out_parishes.items():
        print('  %s %-22s lots %d (shop %d, home %d)' % (f, p['name'], p['counts']['lots'], p['counts']['commercial'], p['counts']['residential']))


if __name__ == '__main__':
    main()
