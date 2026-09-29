"""bayarea/districts_map.py - the DISTRICT maps: each county's 4k map with its AUTHORED districts drawn on top.

Input: the county 4k map just rendered (bayarea/maps/<fips>-4k.webp) and the registry districts (seeds in LOCAL
metres, the same Voronoi seeds the fabric uses). A district cell = the land pixels nearest to its seed (Voronoi,
computed at 1024 px and scaled x4). Output: bayarea/maps/districts/<fips>-4k.webp (4096^2, <= 2,000,000 B) with the
cell edges, each district's short id (D001...) at its seed, and a strip saying the districts are AUTHORED, NOT
official neighbourhoods. Deterministic; no text is added to the ground tiles.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from render import SIZE, MAX_BYTES, font, sha256

LOW = 1024
EDGE = (92, 52, 140)
NOTE = 'AUTHORED districts (procedural Voronoi cells) - NOT official neighbourhoods'


def draw(root, gid, county, left, top, mpp):
    src = root / 'bayarea' / 'maps' / f'{gid}-4k.webp'
    img = Image.open(src).convert('RGB')
    seeds = np.array([d['seed_local_m'] for d in county['districts']], dtype=np.float64)
    step = mpp * SIZE / LOW
    xs = left + (np.arange(LOW) + 0.5) * step
    ys = top - (np.arange(LOW) + 0.5) * step
    lab = np.zeros((LOW, LOW), dtype=np.int32)
    for r0 in range(0, LOW, 128):
        E, N = np.meshgrid(xs, ys[r0:r0 + 128])
        d2 = (E[..., None] - seeds[:, 0]) ** 2 + (N[..., None] - seeds[:, 1]) ** 2
        lab[r0:r0 + 128] = np.argmin(d2, axis=2)
    land = Image.new('L', (LOW, LOW), 0)
    ld = ImageDraw.Draw(land)
    for poly in county['outline_local_m']:
        ld.polygon([((e - left) / step, (top - n) / step) for e, n in poly[0]], fill=255)
        for h in poly[1:]:
            ld.polygon([((e - left) / step, (top - n) / step) for e, n in h], fill=0)
    edge = np.zeros((LOW, LOW), dtype=bool)
    edge[:, 1:] |= lab[:, 1:] != lab[:, :-1]
    edge[1:, :] |= lab[1:, :] != lab[:-1, :]
    edge &= np.array(land) > 0
    em = Image.fromarray((edge * 255).astype(np.uint8), 'L').resize((SIZE, SIZE), Image.NEAREST)
    em = em.filter(ImageFilter.MaxFilter(3))
    img.paste(Image.new('RGB', (SIZE, SIZE), EDGE), (0, 0), em)
    d = ImageDraw.Draw(img)
    f = font(34)
    for dd in county['districts']:
        x = (dd['seed_local_m'][0] - left) / mpp
        y = (top - dd['seed_local_m'][1]) / mpp
        d.text((x, y), dd['id'].split('-')[1], font=f, fill=EDGE, anchor='mm', stroke_width=4, stroke_fill=(255, 255, 255))
    d.rectangle([1900, 470, SIZE, 550], fill=EDGE)
    d.text((1930, 510), NOTE, font=font(42), fill=(255, 255, 255), anchor='lm')
    out = root / 'bayarea' / 'maps' / 'districts'
    out.mkdir(parents=True, exist_ok=True)
    f4 = out / f'{gid}-4k.webp'
    q = 78
    img.save(f4, 'WEBP', quality=q, method=6)
    while f4.stat().st_size > MAX_BYTES and q > 40:
        q -= 6
        img.save(f4, 'WEBP', quality=q, method=6)
    return {'path': f'bayarea/maps/districts/{gid}-4k.webp', 'px': SIZE, 'bytes': f4.stat().st_size,
            'max_bytes': MAX_BYTES, 'webp_quality': q, 'sha256': sha256(f4), 'label': NOTE,
            'georeference': 'same square, extent and pixel rule as map (extent_local_m, m_per_px)',
            'cells': 'nearest district seed among this county\'s districts, land pixels only, computed at '
                     f'{LOW} px and scaled x{SIZE // LOW}', 'provenance': 'AUTHORED districts over the DERIVED map'}
