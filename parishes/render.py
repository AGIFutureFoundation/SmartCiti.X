"""parishes/render.py - draw the 4096x4096 parish maps (Python + PIL only).

Each map is DRAWN from the RECORDED Census outline (coarse 1:10m) plus our own
layers: neighbouring outlines, open water (= outside every land outline), an
AUTHORED procedural street fabric (NOT the real street grid; styled and
legended as such) and landmark pins. It is a map we draw - not satellite
imagery, not a survey - and the image says so on its face.

Georeference (recorded per map in the registry): the map is north-up in the
parish local tangent plane; pixel (px, py) centre is at
  east_m  = left_m + (px + 0.5) * m_per_px
  north_m = top_m  - (py + 0.5) * m_per_px
"""
import hashlib
import math
import random

import numpy as np

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIZE = 4096
PREVIEW = 512
LABEL = 'Map drawn from Census outline + AUTHORED fabric - not satellite, not a survey'
FABRIC_NOTE = 'AUTHORED street fabric - procedural, NOT the real street grid'
QUALITY = 78
MAX_BYTES = 2_000_000
COL = {
    'water': (156, 194, 214), 'water_ink': (60, 104, 130),
    'land': (239, 232, 210), 'nbr': (214, 208, 190), 'nbr_ink': (140, 132, 110),
    'ink': (34, 38, 44), 'border': (214, 120, 30),
    'lmk': (200, 60, 40), 'anchor': (30, 80, 170), 'panel': (255, 255, 255), 'banner': (20, 24, 30),
}


def font(sz):
    return ImageFont.load_default(size=sz)


def sha256(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def nice_scale(mpp):
    target = mpp * 600
    for v in (500, 1000, 2000, 5000, 10000, 20000, 50000):
        if v >= target * 0.6:
            return v
    return 50000


# AUTHORED land-use palette (muted; flat - no hillshade, there is no elevation)
USE = {  # use: (block tint, building tint)
    'residential': ((236, 230, 216), (214, 203, 185)),
    'commercial': ((234, 224, 216), (201, 185, 172)),
    'park': ((208, 224, 192), None),
    'industrial': ((227, 225, 231), (192, 188, 202)),
}
USE_ORDER = ['residential', 'commercial', 'park', 'industrial']
STREET = {'local': (255, 255, 251), 'collector': (252, 247, 234), 'collector_edge': (212, 200, 178),
          'arterial': (244, 206, 140), 'arterial_edge': (190, 150, 92)}


def city_fabric(outline_local, left, top, mpp, seed, near_water):
    """AUTHORED procedural city fabric (numpy, per pixel, deterministic per FIPS).

    Districts are a jittered-grid Voronoi partition; each district keeps ONE
    grid orientation, taken from the outline's long axis plus a slowly varying
    field, so neighbouring districts differ only a little (smooth blending, no
    hatch). Streets: local grid per district; collectors on district edges;
    arterials (drawn after, by the caller) along and across the long axis.
    Blocks get a muted land-use tint; residential/commercial/industrial blocks
    get building-footprint hints (setback, lots, courtyards). None of this is
    the real city: the caller legends it AUTHORED."""
    rnd = random.Random(seed)
    pts = np.array([p for poly in outline_local for p in poly[0]], dtype=np.float64)
    ctr = pts.mean(0)
    w, v = np.linalg.eigh(np.cov((pts - ctr).T))
    ax = v[:, int(np.argmax(w))]
    theta0 = math.atan2(ax[1], ax[0])
    D = max(2600.0, 170 * mpp)                      # district spacing (m)
    x0, y0 = pts.min(0) - D
    x1, y1 = pts.max(0) + D
    ni, nj = int((x1 - x0) // D) + 2, int((y1 - y0) // D) + 2
    ph1, ph2 = rnd.uniform(0, 6.28), rnd.uniform(0, 6.28)
    SX = np.zeros((ni, nj)); SY = np.zeros((ni, nj)); ANG = np.zeros((ni, nj))
    SU = np.zeros((ni, nj)); SV = np.zeros((ni, nj)); TY = np.zeros((ni, nj), dtype=np.int32)
    nwH, nwW = near_water.shape
    for i in range(ni):
        for j in range(nj):
            sx = x0 + (i + 0.2 + 0.6 * rnd.random()) * D
            sy = y0 + (j + 0.2 + 0.6 * rnd.random()) * D
            SX[i, j], SY[i, j] = sx, sy
            ANG[i, j] = theta0 + 0.30 * math.sin(sx / 11000 + ph1) + 0.22 * math.cos(sy / 9000 + ph2)
            su = max(95.0, 7.5 * mpp) * rnd.uniform(0.95, 1.25)
            SU[i, j], SV[i, j] = su, su * rnd.choice([1.0, 1.7, 2.6, 2.6])
            qx = int((sx - left) / mpp * nwW / SIZE); qy = int((top - sy) / mpp * nwH / SIZE)
            wet = 0 <= qx < nwW and 0 <= qy < nwH and near_water[qy, qx]
            r = rnd.random()
            if wet and r < 0.55:
                TY[i, j] = 3                          # industrial near open water
            elif r < 0.08:
                TY[i, j] = 2                          # a large park district
            elif r < 0.24:
                TY[i, j] = 1                          # commercial / mixed centre
            else:
                TY[i, j] = 0                          # residential
    out = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)
    wl = max(9.0, 1.15 * mpp)                           # local street width (m)
    wc = max(22.0, 2.6 * mpp)                           # collector half-width scale (m)
    tint = np.array([USE[u][0] for u in USE_ORDER], dtype=np.uint8)
    bld = np.array([USE[u][1] if USE[u][1] else USE[u][0] for u in USE_ORDER], dtype=np.uint8)
    xs = left + (np.arange(SIZE) + 0.5) * mpp
    for r0 in range(0, SIZE, 256):
        ys = top - (np.arange(r0, r0 + 256) + 0.5) * mpp
        E, N = np.meshgrid(xs, ys)
        ci = np.floor((E - x0) / D).astype(np.int32); cj = np.floor((N - y0) / D).astype(np.int32)
        best = np.full(E.shape, np.inf); second = np.full(E.shape, np.inf)
        bi = np.zeros(E.shape, dtype=np.int32); bj = np.zeros(E.shape, dtype=np.int32)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                ii = np.clip(ci + di, 0, ni - 1); jj = np.clip(cj + dj, 0, nj - 1)
                dd = np.hypot(E - SX[ii, jj], N - SY[ii, jj])
                closer = dd < best
                second = np.where(closer, best, np.minimum(second, dd))
                best = np.where(closer, dd, best)
                bi = np.where(closer, ii, bi); bj = np.where(closer, jj, bj)
        a = ANG[bi, bj]; ca, sa = np.cos(a), np.sin(a)
        dx, dy = E - SX[bi, bj], N - SY[bi, bj]
        u = dx * ca + dy * sa; v = -dx * sa + dy * ca
        su, sv = SU[bi, bj], SV[bi, bj]
        fu, fv = np.mod(u, su), np.mod(v, sv)
        kb = (np.floor(u / su).astype(np.int64) * 73856093) ^ (np.floor(v / sv).astype(np.int64) * 19349663) \
            ^ ((bi * 1000 + bj).astype(np.int64) * 83492791)
        rb = (np.mod(kb, 1000) / 1000.0)
        ty = TY[bi, bj]
        use = np.where(ty == 2, 2,
              np.where(ty == 3, np.where(rb < 0.15, 0, 3),
              np.where(ty == 1, np.where(rb < 0.06, 2, np.where(rb < 0.25, 0, 1)),
                       np.where(rb < 0.06, 2, np.where(rb < 0.12, 1, 0)))))
        px_ = tint[use]
        # building-footprint hints inside the block (setback from the street, lots, courtyard)
        setb = max(6.0, 0.6 * mpp)
        iu, iv = fu - wl, fv - wl                      # position inside the block
        bu, bv = su - wl, sv - wl                      # block size
        inner = (iu > setb) & (iu < bu - setb) & (iv > setb) & (iv < bv - setb)
        edge = np.minimum(np.minimum(iu, bu - iu), np.minimum(iv, bv - iv))
        lot = np.maximum(18.0, 1.6 * mpp)
        lots = np.mod(np.where(np.minimum(iu, bu - iu) < np.minimum(iv, bv - iv), iv, iu), lot) > max(3.0, 0.45 * mpp)
        res_b = inner & (edge < 0.30 * np.minimum(bu, bv) + setb) & lots
        com_b = inner & (edge < 0.42 * np.minimum(bu, bv) + setb) & (np.mod(np.where(bu > bv, iu, iv), 2 * lot) > max(3.0, 0.45 * mpp))
        ind_b = (iu > 2.5 * setb) & (iu < bu - 2.5 * setb) & (iv > 2.5 * setb) & (iv < bv - 2.5 * setb)
        has_b = np.where(use == 0, res_b, np.where(use == 1, com_b, np.where(use == 3, ind_b, False)))
        px_ = np.where(has_b[..., None], bld[use], px_)
        # streets: local grid, then collectors on district edges (smooth Voronoi bisectors)
        park_path = (use == 2)
        street = ((fu < wl) | (fv < wl)) & ~park_path
        px_ = np.where(street[..., None], np.array(STREET['local'], dtype=np.uint8), px_)
        gap = second - best
        px_ = np.where((gap < wc * 1.35)[..., None], np.array(STREET['collector_edge'], dtype=np.uint8), px_)
        px_ = np.where((gap < wc)[..., None], np.array(STREET['collector'], dtype=np.uint8), px_)
        out[r0:r0 + 256] = px_
    return Image.fromarray(out, 'RGB'), theta0, ctr


def arterials(draw, theta0, ctr, outline_local, left, top, mpp, seed):
    """AUTHORED arterials: gently curving roads along the outline's long axis,
    and fewer across it, spaced by the parish's own extent."""
    rnd = random.Random(seed * 7 + 1)
    pts = np.array([p for poly in outline_local for p in poly[0]], dtype=np.float64)
    ca, sa = math.cos(theta0), math.sin(theta0)
    U = (pts[:, 0] - ctr[0]) * ca + (pts[:, 1] - ctr[1]) * sa
    V = -(pts[:, 0] - ctr[0]) * sa + (pts[:, 1] - ctr[1]) * ca
    lines = []
    span_v = V.max() - V.min(); span_u = U.max() - U.min()
    for k in range(1, 4):                                   # along the long axis
        vv = V.min() + span_v * k / 4 + rnd.uniform(-0.05, 0.05) * span_v
        amp, ph = rnd.uniform(0.01, 0.03) * span_v, rnd.uniform(0, 6.28)
        lines.append([(uu, vv + amp * math.sin(uu / span_u * 6.28 + ph))
                      for uu in np.linspace(U.min() - 500, U.max() + 500, 60)])
    for k in range(1, max(2, int(span_u / 9000)) + 1):     # across it
        uu0 = U.min() + span_u * k / (max(2, int(span_u / 9000)) + 1)
        amp, ph = rnd.uniform(0.01, 0.03) * span_u, rnd.uniform(0, 6.28)
        lines.append([(uu0 + amp * math.sin(vv / span_v * 6.28 + ph), vv)
                      for vv in np.linspace(V.min() - 500, V.max() + 500, 60)])
    wpx = max(4, int(round(34 / mpp)))
    for pass_, colr, extra in (('edge', STREET['arterial_edge'], 4), ('fill', STREET['arterial'], 0)):
        for ln in lines:
            xy = []
            for uu, vv in ln:
                e = ctr[0] + uu * ca - vv * sa; n = ctr[1] + uu * sa + vv * ca
                xy.append(((e - left) / mpp, (top - n) / mpp))
            draw.line(xy, fill=colr, width=wpx + extra, joint='curve')
    return len(lines)


def render_all(ROOT, parishes, by_id, arcs, polygons_of, ltp, frame, water_labels):
    out_dir = ROOT / 'parishes' / 'maps'
    out_dir.mkdir(parents=True, exist_ok=True)
    # candidate neighbours drawn for context: every county of LA (22) and MS (28)
    ctx = {}
    for gid, g in by_id.items():
        if gid[:2] in ('22', '28'):
            polys = polygons_of(g, arcs)
            xs = [p[0] for q in polys for p in q[0]]
            ys = [p[1] for q in polys for p in q[0]]
            ctx[gid] = (polys, (min(xs), min(ys), max(xs), max(ys)))
    k = math.radians(1) * 6371008.8
    maps = {}
    for gid, P in parishes.items():
        lat0, lng0 = P['frame']['origin']['lat'], P['frame']['origin']['lng']
        c = math.cos(math.radians(lat0))
        fwd = ltp(lat0, lng0)
        pts = [p for poly in P['outline_local_m'] for p in poly[0]]
        x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
        y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
        side = max(x1 - x0, y1 - y0) * 1.16
        mpp = side / SIZE
        cxm, cym = (x0 + x1) / 2, (y0 + y1) / 2
        left, top = cxm - side / 2, cym + side / 2 + side * 0.03  # a little headroom for the banner
        right, bottom = left + side, top - side

        def px(lng, lat):
            e, n = fwd(lng, lat)
            return ((e - left) / mpp, (top - n) / mpp)

        ext_ll = (lng0 + left / (k * c), lat0 + bottom / k, lng0 + right / (k * c), lat0 + top / k)
        img = Image.new('RGB', (SIZE, SIZE), COL['water'])
        d = ImageDraw.Draw(img)
        allland = Image.new('L', (512, 512), 0)
        ald = ImageDraw.Draw(allland)

        def px8(lng, lat):
            x, y = px(lng, lat)
            return (x / 8, y / 8)
        for poly in P['outline']['polygons']:
            ald.polygon([px8(*q) for q in poly[0]], fill=255)
        # neighbours (context land)
        for nid, (polys, bb) in ctx.items():
            if nid == gid or bb[2] < ext_ll[0] or bb[0] > ext_ll[2] or bb[3] < ext_ll[1] or bb[1] > ext_ll[3]:
                continue
            for poly in polys:
                d.polygon([px(*q) for q in poly[0]], fill=COL['nbr'], outline=COL['nbr_ink'], width=3)
                ald.polygon([px8(*q) for q in poly[0]], fill=255)
                for h in poly[1:]:
                    d.polygon([px(*q) for q in h], fill=COL['water'])
        # the parish land + its AUTHORED fabric, masked to the land
        mask = Image.new('L', (SIZE, SIZE), 0)
        md = ImageDraw.Draw(mask)
        for poly in P['outline']['polygons']:
            md.polygon([px(*q) for q in poly[0]], fill=255)
            for h in poly[1:]:
                md.polygon([px(*q) for q in h], fill=0)
        eroded = allland.filter(ImageFilter.MinFilter(9)).filter(ImageFilter.MinFilter(9))
        near_water = (np.array(allland) > 0) & (np.array(eroded) == 0)
        land, theta0, ctr = city_fabric(P['outline_local_m'], left, top, mpp, int(gid), near_water)
        n_art = arterials(ImageDraw.Draw(land), theta0, ctr, P['outline_local_m'], left, top, mpp, int(gid))
        img.paste(land, (0, 0), mask)
        d = ImageDraw.Draw(img)
        for poly in P['outline']['polygons']:
            for ring in poly:
                r = [px(*q) for q in ring]
                d.line(r + r[:1], fill=COL['ink'], width=7, joint='curve')
        for b in P['borders']:
            for s in b['segments']:
                d.line([px(*q) for q in s['wgs84']], fill=COL['border'], width=14, joint='curve')
        # neighbour names at their visible centroid (selected ones only, to stay honest about scope)
        taken = [(0, 0, SIZE, 420), (0, SIZE - 774, 1900, SIZE), (SIZE - 700, SIZE - 260, SIZE, SIZE)]

        def free(bb):
            return not any(bb[0] < t[2] and t[0] < bb[2] and bb[1] < t[3] and t[1] < bb[3] for t in taken)
        for b in P['borders']:
            nb = parishes[b['with']]
            o = nb['frame']['origin']
            x, y = px(o['lng'], o['lat'])
            x, y = min(max(x, 420), SIZE - 420), min(max(y, 480), SIZE - 700)
            bb = d.textbbox((x, y), nb['full_name'], font=font(56), anchor='mm')
            if free(bb):
                taken.append(bb)
                d.text((x, y), nb['full_name'], font=font(56), fill=COL['nbr_ink'], anchor='mm',
                       stroke_width=4, stroke_fill=COL['nbr'])
        for W in water_labels:
            x, y = px(W['lng'], W['lat'])
            if not (0 < x < SIZE and 0 < y < SIZE):
                continue
            for line_i, txt in enumerate((W['name'], 'open water - NOT cut out at 1:10m')):
                bb = d.textbbox((x, y + line_i * 64), txt, font=font(58 - line_i * 16), anchor='mm')
                if free(bb):
                    taken.append(bb)
                    d.text((x, y + line_i * 64), txt, font=font(58 - line_i * 16), fill=COL['water_ink'],
                           anchor='mm', stroke_width=5, stroke_fill=(255, 255, 255))
        # pins
        for L, colr, tag in ([(L, COL['lmk'], 'AUTHORED') for L in P['landmarks']]
                             + [(A, COL['anchor'], 'RECORDED') for A in P['anchors']]):
            x, y = px(L['lng'], L['lat'])
            r = 22
            if tag == 'RECORDED':
                d.rectangle([x - r, y - r, x + r, y + r], fill=colr, outline=(255, 255, 255), width=6)
            else:
                d.ellipse([x - r, y - r, x + r, y + r], fill=colr, outline=(255, 255, 255), width=6)
            for (ox, oy, an) in ((34, 0, 'lm'), (-34, 0, 'rm'), (0, -44, 'mb'), (0, 44, 'mt'),
                                 (34, 48, 'lm'), (34, -48, 'lm')):
                bb = d.textbbox((x + ox, y + oy), L['name'], font=font(44), anchor=an)
                if free(bb):
                    break
            taken.append(bb)
            d.text((x + ox, y + oy), L['name'], font=font(44), fill=COL['ink'], anchor=an,
                   stroke_width=5, stroke_fill=(255, 255, 255))
        # banner + title
        d.rectangle([0, 0, SIZE, 150], fill=COL['banner'])
        d.text((48, 75), LABEL, font=font(64), fill=(255, 255, 255), anchor='lm')
        d.text((60, 250), f"{P['full_name']}", font=font(120), fill=COL['ink'], anchor='lm',
               stroke_width=8, stroke_fill=(255, 255, 255))
        d.text((64, 350), f"FIPS {gid}  |  outline RECORDED (Census 2017 via us-atlas, 1:10m, coarse)  |  "
               f"{mpp:.2f} m per pixel  |  no real elevation",
               font=font(46), fill=COL['ink'], anchor='lm', stroke_width=5, stroke_fill=(255, 255, 255))
        # legend
        lx, ly = 48, SIZE - 758
        d.rectangle([lx, ly, lx + 1840, SIZE - 48], fill=COL['panel'], outline=COL['ink'], width=4)
        rows = [('land', 'parish land (RECORDED outline, coarse)'),
                ('nbr', 'neighbouring land (RECORDED outline)'),
                ('water', 'open water = outside every land outline (Gulf side; not surveyed)'),
                ('inland', 'inland water (lakes, river) is NOT cut out at 1:10m: fabric over it is not land'),
                ('fabric', FABRIC_NOTE),
                ('landuse', 'AUTHORED land use: residential, commercial, park, industrial + building hints'),
                ('border', 'shared border with a selected parish (walk/drive across)'),
                ('lmk', 'landmark: AUTHORED from public record, approximate'),
                ('anchor', 'university anchor: RECORDED (geo registry)')]
        for i, (key, txt) in enumerate(rows):
            yy = ly + 50 + i * 74
            if key == 'fabric':
                d.rectangle([lx + 30, yy - 22, lx + 110, yy + 22], fill=USE['residential'][0], outline=COL['ink'], width=2)
                d.line([(lx + 30, yy), (lx + 110, yy)], fill=STREET['arterial_edge'], width=12)
                d.line([(lx + 30, yy), (lx + 110, yy)], fill=STREET['arterial'], width=8)
                d.line([(lx + 70, yy - 22), (lx + 70, yy + 22)], fill=STREET['collector_edge'], width=4)
            elif key == 'landuse':
                for j, u in enumerate(USE_ORDER):
                    d.rectangle([lx + 30 + j * 20, yy - 22, lx + 50 + j * 20, yy + 22], fill=USE[u][0], outline=COL['ink'], width=1)
            elif key == 'inland':
                d.rectangle([lx + 30, yy - 22, lx + 110, yy + 22], fill=COL['land'], outline=COL['water_ink'], width=4)
                d.text((lx + 70, yy), '?', font=font(40), fill=COL['water_ink'], anchor='mm')
            elif key == 'border':
                d.line([(lx + 30, yy), (lx + 110, yy)], fill=COL['border'], width=14)
            elif key in ('lmk', 'anchor'):
                if key == 'anchor':
                    d.rectangle([lx + 50, yy - 20, lx + 90, yy + 20], fill=COL[key])
                else:
                    d.ellipse([lx + 50, yy - 20, lx + 90, yy + 20], fill=COL[key])
            else:
                d.rectangle([lx + 30, yy - 22, lx + 110, yy + 22], fill=COL[key], outline=COL['ink'], width=2)
            d.text((lx + 140, yy), txt, font=font(46), fill=COL['ink'], anchor='lm')
        # scale bar + north arrow
        sv = nice_scale(mpp)
        spx = sv / mpp
        sx, sy = SIZE - 120 - spx, SIZE - 110
        d.rectangle([sx - 30, sy - 110, SIZE - 60, SIZE - 40], fill=COL['panel'], outline=COL['ink'], width=3)
        d.rectangle([sx, sy, sx + spx, sy + 22], fill=COL['ink'])
        d.text((sx + spx / 2, sy - 40), f'{sv / 1000:g} km', font=font(48), fill=COL['ink'], anchor='mm')
        ax, ay = SIZE - 150, 330
        d.polygon([(ax, ay - 110), (ax - 50, ay + 40), (ax + 50, ay + 40)], fill=COL['ink'])
        d.text((ax, ay + 90), 'N', font=font(72), fill=COL['ink'], anchor='mm', stroke_width=5,
               stroke_fill=(255, 255, 255))
        f4 = out_dir / f'{gid}-4k.webp'
        fp = out_dir / f'{gid}-512.webp'
        q = QUALITY
        img.save(f4, 'WEBP', quality=q, method=6)
        while f4.stat().st_size > MAX_BYTES and q > 40:  # keep each 4k file at or under ~2 MB
            q -= 6
            img.save(f4, 'WEBP', quality=q, method=6)
        img.resize((PREVIEW, PREVIEW), Image.LANCZOS).save(fp, 'WEBP', quality=82, method=6)
        maps[gid] = {
            'path': f'parishes/maps/{gid}-4k.webp', 'preview': f'parishes/maps/{gid}-512.webp',
            'px': SIZE, 'preview_px': PREVIEW, 'm_per_px': round(mpp, 4),
            'extent_local_m': {'left': round(left, 2), 'right': round(right, 2),
                               'bottom': round(bottom, 2), 'top': round(top, 2)},
            'extent_wgs84': [round(v, 6) for v in ext_ll],
            'pixel_to_local_m': 'east_m = left + (px + 0.5) * m_per_px; north_m = top - (py + 0.5) * m_per_px',
            'bytes': f4.stat().st_size, 'webp_quality': q, 'max_bytes': MAX_BYTES, 'preview_bytes': fp.stat().st_size,
            'sha256': sha256(f4), 'preview_sha256': sha256(fp),
            'label': LABEL, 'fabric': FABRIC_NOTE,
            'fabric_layers': {'arterials': n_art, 'collectors': 'district edges', 'local_grid': 'one orientation per district',
                              'land_use': USE_ORDER, 'building_hints': True, 'hillshade': False,
                              'provenance': 'AUTHORED procedural, seeded by FIPS; NOT the real street grid, land use or buildings'}, 'provenance': 'DERIVED outline + AUTHORED fabric; not imagery',
        }
        print(f'  map {gid}: {f4.stat().st_size} bytes, {mpp:.2f} m/px')
    return maps
