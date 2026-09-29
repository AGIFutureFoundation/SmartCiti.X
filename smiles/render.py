#!/usr/bin/env python3
"""smiles/render.py - the AUTHORED district map (4096 px) and ONE ground atlas (4x4 cells), drawn procedurally with
Pillow (same pattern as parishes/render.py: a flat authored plan with a provenance strip; deterministic noise, no
fetch). Output bytes are deterministic for the same inputs (seeded noise, lossless=False webp at a fixed quality)."""
import io
import random

from PIL import Image, ImageDraw, ImageFont

ATLAS_GRID = 4
ATLAS_CELL = 256
ATLAS_CELLS = ['grass', 'asphalt', 'sidewalk', 'clinic-tile', 'sand', 'rubber', 'wood', 'water',
               'school-floor', 'garden-soil', 'shop-floor', 'hall-floor', 'lot', 'mulch', 'lino', 'paint']
CELL_BASE = {'grass': (122, 176, 104), 'asphalt': (72, 76, 84), 'sidewalk': (196, 194, 188), 'clinic-tile': (222, 236, 244),
             'sand': (230, 212, 160), 'rubber': (206, 102, 84), 'wood': (170, 128, 84), 'water': (86, 150, 196),
             'school-floor': (236, 220, 180), 'garden-soil': (120, 88, 60), 'shop-floor': (214, 234, 214),
             'hall-floor': (220, 206, 236), 'lot': (170, 170, 180), 'mulch': (140, 100, 70), 'lino': (200, 222, 230),
             'paint': (250, 250, 250)}


def _font(px):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(p, px)
        except OSError:
            continue
    return ImageFont.load_default()


def _hex(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _speckle(img, box, base, rnd, n, spread):
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    for _ in range(n):
        x = rnd.randint(x0, x1 - 1)
        y = rnd.randint(y0, y1 - 1)
        v = rnd.randint(-spread, spread)
        c = tuple(max(0, min(255, b + v)) for b in base)
        r = rnd.randint(1, 3)
        d.ellipse((x - r, y - r, x + r, y + r), fill=c)


HOUSE = (30, 24)


def house_lots(rect):
    """AUTHORED house footprints in a residential block: a two-row grid with gardens between (deterministic)."""
    x, y, w, h = rect
    out = []
    for row in (y + 30, y + h - 30 - HOUSE[1]):
        n = int((w - 20) // 55)
        for k in range(n):
            out.append((x + 15 + k * 55, row))
    return out


STALL = (36, 24)


def market_stalls(rect):
    """AUTHORED market stall footprints: two rows of six."""
    x, y, w, h = rect
    return [(x + 20 + k * 52, y + 50 + row * 90) for row in range(2) for k in range(6)]


def render_atlas():
    rnd = random.Random(20260929)
    size = ATLAS_GRID * ATLAS_CELL
    img = Image.new('RGB', (size, size))
    cells = {}
    for i, name in enumerate(ATLAS_CELLS):
        cx, cy = (i % ATLAS_GRID) * ATLAS_CELL, (i // ATLAS_GRID) * ATLAS_CELL
        base = CELL_BASE[name]
        ImageDraw.Draw(img).rectangle((cx, cy, cx + ATLAS_CELL - 1, cy + ATLAS_CELL - 1), fill=base)
        _speckle(img, (cx, cy, cx + ATLAS_CELL, cy + ATLAS_CELL), base, rnd, 900, 14)
        d = ImageDraw.Draw(img)
        if name in ('clinic-tile', 'school-floor', 'shop-floor', 'hall-floor', 'lino', 'sidewalk'):
            step = 32 if name != 'sidewalk' else 64
            for k in range(0, ATLAS_CELL + 1, step):
                line = tuple(max(0, b - 28) for b in base)
                d.line((cx + k, cy, cx + k, cy + ATLAS_CELL), fill=line, width=2)
                d.line((cx, cy + k, cx + ATLAS_CELL, cy + k), fill=line, width=2)
        if name == 'wood':
            for k in range(0, ATLAS_CELL, 24):
                d.line((cx, cy + k, cx + ATLAS_CELL, cy + k), fill=(140, 100, 64), width=2)
        cells[name] = {'col': i % ATLAS_GRID, 'row': i // ATLAS_GRID}
    buf = io.BytesIO()
    img.save(buf, 'WEBP', quality=72, method=4)
    return buf.getvalue(), cells


def render_map(d, eggs):
    px = d['map_px']
    W, H = d['size_m']
    s = px / W
    rnd = random.Random(12)
    img = Image.new('RGB', (px, px), CELL_BASE['grass'])
    _speckle(img, (0, 0, px, px), CELL_BASE['grass'], rnd, 60000, 12)
    dr = ImageDraw.Draw(img)
    for st in d['streets']:
        (x0, y0), (x1, y1), w = st['from'], st['to'], st['width_m']
        box = (min(x0, x1) * s - w * s / 2 if x0 == x1 else min(x0, x1) * s, min(y0, y1) * s - w * s / 2 if y0 == y1 else min(y0, y1) * s,
               max(x0, x1) * s + w * s / 2 if x0 == x1 else max(x0, x1) * s, max(y0, y1) * s + w * s / 2 if y0 == y1 else max(y0, y1) * s)
        dr.rectangle(tuple(box), fill=CELL_BASE['sidewalk'])
        inner = (box[0] + 3 * s, box[1] + 3 * s, box[2] - 3 * s, box[3] - 3 * s) if x0 == x1 else \
                (box[0], box[1] + 3 * s, box[2], box[3] - 3 * s)
        if x0 == x1:
            inner = (box[0] + 3 * s, box[1], box[2] - 3 * s, box[3])
        dr.rectangle(inner, fill=CELL_BASE['asphalt'])
        k0 = int(min(x0, x1) * s) if y0 == y1 else int(min(y0, y1) * s)
        for k in range(k0, k0 + int(max(abs(x1 - x0), abs(y1 - y0)) * s), int(12 * s)):
            if y0 == y1:
                dr.rectangle((k, y0 * s - 0.4 * s, k + 6 * s, y0 * s + 0.4 * s), fill=(250, 230, 120))
            else:
                dr.rectangle((x0 * s - 0.4 * s, k, x0 * s + 0.4 * s, k + 6 * s), fill=(250, 230, 120))
    f_big, f_mid, f_small = _font(52), _font(32), _font(24)
    for z in d['zones']:
        x, y, w, h = z['rect']
        dr.rectangle((x * s, y * s, (x + w) * s, (y + h) * s), fill=_hex(z['colour']), outline=(60, 70, 80), width=8)
        if z['kind'] == 'park':
            for _ in range(60):
                tx, ty = rnd.uniform(x + 8, x + w - 8) * s, rnd.uniform(y + 8, y + h - 8) * s
                dr.ellipse((tx - 38, ty - 38, tx + 38, ty + 38), fill=(70, 130, 70))
            dr.rectangle(((x + 20) * s, (y + h - 40) * s, (x + w - 20) * s, (y + h - 20) * s), fill=CELL_BASE['water'])
        if z['kind'] == 'playground':
            dr.ellipse(((x + 20) * s, (y + 100) * s, (x + 80) * s, (y + 160) * s), fill=CELL_BASE['sand'])
        if z['kind'] == 'garden':
            for k in range(8):
                dr.rectangle(((x + 12 + k * 35) * s, (y + 20) * s, (x + 38 + k * 35) * s, (y + 90) * s), fill=CELL_BASE['garden-soil'])
        if z['kind'] == 'sports':
            dr.rectangle(((x + 20) * s, (y + 30) * s, (x + w - 20) * s, (y + h - 20) * s), outline=(250, 250, 250), width=8)
            dr.line(((x + 20) * s, (y + (h + 10) / 2) * s, (x + w - 20) * s, (y + (h + 10) / 2) * s), fill=(250, 250, 250), width=8)
            cx, cy = (x + w / 2) * s, (y + (h + 10) / 2) * s
            dr.ellipse((cx - 30 * s, cy - 30 * s, cx + 30 * s, cy + 30 * s), outline=(250, 250, 250), width=8)
        if z['kind'] == 'market':
            for n, (sx, sy) in enumerate(market_stalls(z['rect'])):
                dr.rectangle((sx * s, sy * s, (sx + STALL[0]) * s, (sy + STALL[1]) * s), fill=[(230, 90, 80), (80, 160, 220), (250, 190, 60)][n % 3])
        if z['kind'] == 'residential':
            for hx, hy in house_lots(z['rect']):
                dr.rectangle((hx * s, hy * s, (hx + HOUSE[0]) * s, (hy + HOUSE[1]) * s), fill=(190, 120, 100), outline=(90, 60, 50), width=5)
        if z['kind'] == 'library':
            for k in range(5):
                dr.rectangle(((x + 30 + k * 40) * s, (y + 80) * s, (x + 50 + k * 40) * s, (y + 250) * s), fill=(160, 110, 70))
        if z['kind'] == 'busstop':
            dr.rectangle((x * s, y * s, (x + w) * s, (y + h) * s), fill=(255, 224, 130), outline=(60, 60, 60), width=6)
            dr.text(((x + 1) * s, (y - 14) * s), 'BUS', fill=(20, 24, 30), font=f_mid)
            continue
        dr.text(((x + 6) * s, (y + 4) * s), z['name'], fill=(20, 24, 30), font=f_big)
    for r in d['rooms']:
        x, y, w, h = r['rect']
        dr.rectangle((x * s, y * s, (x + w) * s, (y + h) * s), fill=(244, 250, 252), outline=(40, 90, 120), width=6)
        dr.text(((x + 3) * s, (y + 3) * s), r['name'], fill=(20, 50, 70), font=f_mid)
        dr.text(((x + 3) * s, (y + 14) * s), f'{len(r["stations"])} station(s)', fill=(40, 70, 90), font=f_small)
    stops = d['van_route']['stops']
    dr.line([(x * s, y * s) for x, y in d['van_route']['path']], fill=(230, 90, 150), width=14)
    for p in stops:
        cx, cy = p['at'][0] * s, p['at'][1] * s
        dr.ellipse((cx - 30, cy - 30, cx + 30, cy + 30), fill=(230, 90, 150), outline=(255, 255, 255), width=6)
    dr.rectangle((0, px - 120, px, px), fill=(20, 24, 30))
    dr.text((40, px - 100), 'Unspoken Smiles district - AUTHORED game map, not a real place, not surveyed. '
            'Eggs are hidden, not drawn.', fill=(255, 255, 255), font=f_mid)
    buf = io.BytesIO()
    img.save(buf, 'WEBP', quality=60, method=4)
    return buf.getvalue()
