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

from PIL import Image, ImageDraw, ImageFont

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
    'fabric_minor': (196, 150, 170), 'fabric_major': (170, 70, 110),
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


def fabric(draw, W, left, top, mpp, seed, bbox_m):
    """AUTHORED: a patchwork of rotated block grids (3 km patches), seeded by FIPS."""
    rnd = random.Random(seed)
    patch = 3000.0
    x0, y0, x1, y1 = bbox_m
    ex = x0 - (x0 % patch)
    while ex < x1:
        ny = y0 - (y0 % patch)
        while ny < y1:
            ang = math.radians(rnd.choice([0, 0, 12, -18, 27, 45, -35]))
            sp = rnd.choice([180.0, 220.0, 260.0])
            cx, cy = ex + patch / 2, ny + patch / 2
            ca, sa = math.cos(ang), math.sin(ang)
            half = patch * 0.72
            k = -int(half // sp)
            while k * sp <= half:
                major = (k % 5 == 0)
                colr = COL['fabric_major'] if major else COL['fabric_minor']
                wid = 5 if major else 2
                for (u1, v1, u2, v2) in ((k * sp, -half, k * sp, half), (-half, k * sp, half, k * sp)):
                    pts = []
                    for u, v in ((u1, v1), (u2, v2)):
                        e = cx + u * ca - v * sa
                        n = cy + u * sa + v * ca
                        e = min(max(e, ex), ex + patch)
                        n = min(max(n, ny), ny + patch)
                        pts.append(((e - left) / mpp, (top - n) / mpp))
                    draw.line(pts, fill=colr, width=wid)
                k += 1
            ny += patch
        ex += patch


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
        # neighbours (context land)
        for nid, (polys, bb) in ctx.items():
            if nid == gid or bb[2] < ext_ll[0] or bb[0] > ext_ll[2] or bb[3] < ext_ll[1] or bb[1] > ext_ll[3]:
                continue
            for poly in polys:
                d.polygon([px(*q) for q in poly[0]], fill=COL['nbr'], outline=COL['nbr_ink'], width=3)
                for h in poly[1:]:
                    d.polygon([px(*q) for q in h], fill=COL['water'])
        # the parish land + its AUTHORED fabric, masked to the land
        mask = Image.new('L', (SIZE, SIZE), 0)
        md = ImageDraw.Draw(mask)
        for poly in P['outline']['polygons']:
            md.polygon([px(*q) for q in poly[0]], fill=255)
            for h in poly[1:]:
                md.polygon([px(*q) for q in h], fill=0)
        land = Image.new('RGB', (SIZE, SIZE), COL['land'])
        fabric(ImageDraw.Draw(land), SIZE, left, top, mpp, int(gid), (x0, y0, x1, y1))
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
        taken = [(0, 0, SIZE, 420), (0, SIZE - 700, 1900, SIZE), (SIZE - 700, SIZE - 260, SIZE, SIZE)]

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
        lx, ly = 48, SIZE - 684
        d.rectangle([lx, ly, lx + 1840, SIZE - 48], fill=COL['panel'], outline=COL['ink'], width=4)
        rows = [('land', 'parish land (RECORDED outline, coarse)'),
                ('nbr', 'neighbouring land (RECORDED outline)'),
                ('water', 'open water = outside every land outline (Gulf side; not surveyed)'),
                ('inland', 'inland water (lakes, river) is NOT cut out at 1:10m: fabric over it is not land'),
                ('fabric', FABRIC_NOTE),
                ('border', 'shared border with a selected parish (walk/drive across)'),
                ('lmk', 'landmark: AUTHORED from public record, approximate'),
                ('anchor', 'university anchor: RECORDED (geo registry)')]
        for i, (key, txt) in enumerate(rows):
            yy = ly + 50 + i * 74
            if key == 'fabric':
                d.rectangle([lx + 30, yy - 22, lx + 110, yy + 22], fill=COL['land'])
                for j in range(4):
                    d.line([(lx + 30 + j * 26, yy - 22), (lx + 30 + j * 26, yy + 22)], fill=COL['fabric_major'], width=4)
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
            'label': LABEL, 'fabric': FABRIC_NOTE, 'provenance': 'DERIVED outline + AUTHORED fabric; not imagery',
        }
        print(f'  map {gid}: {f4.stat().st_size} bytes, {mpp:.2f} m/px')
    return maps
