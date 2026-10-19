"""bayarea/render_bay.py - draw the 4096x4096 Bay Area county maps, 512 previews, label-free ground tiles and
AUTHORED street polylines. Reuses parishes/render.py by IMPORT (city_fabric, arterials, street_polylines,
save_ground_tiles, save_streets, fonts, palette, budgets); render_all below is parishes/render.py render_all
parameterised for the Bay pack (output dir bayarea/maps, context counties by state FIPS, county wording, Bay
legend, AUTHORED districts exported from the same fabric the map draws). Same georeference rules as PARISH v1.3.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'parishes'))
import render as R  # noqa: E402  (parishes/render.py - imported, never edited)
from render import (SIZE, PREVIEW, LABEL, FABRIC_NOTE, QUALITY, MAX_BYTES, COL, USE, USE_ORDER, STREET,  # noqa: E402
                    font, sha256, nice_scale, city_fabric, arterials, save_ground_tiles, save_streets)

GROUND_LABEL = R.GROUND_LABEL
STREETS_NOTE = R.STREETS_NOTE


def retag_tiles(gt):
    for t in gt['tiles']:
        if not t['path'].startswith('parishes/maps/tiles/'):
            raise SystemExit('tile path shape changed in parishes/render.py: ' + t['path'])
        t['path'] = 'bayarea/maps/tiles/' + t['path'][len('parishes/maps/tiles/'):]
    gt['crs'] = 'county LOCAL metres'
    return gt


def retag_streets(out_dir, gid, st):
    f = out_dir / 'streets' / f'{gid}.json'
    doc = json.loads(f.read_text())
    if doc['pack'] != 'parishes':
        raise SystemExit('streets doc shape changed in parishes/render.py')
    doc['pack'] = 'bayarea'
    doc['crs'] = 'county LOCAL metres [east_m, north_m]; frame origin = registry counties[fips].frame.origin'
    f.write_text(json.dumps(doc, separators=(',', ':')) + '\n')
    if f.stat().st_size > R.STREETS_MAX_BYTES:
        raise SystemExit(f'streets {gid}: over the declared budget')
    st['path'] = f'bayarea/maps/streets/{gid}.json'
    st['bytes'] = f.stat().st_size
    st['sha256'] = sha256(f)
    return st


def render_all(ROOT, counties, by_id, arcs, polygons_of, ltp, frame, water_labels, stamp, state_prefixes, districts_of):
    out_dir = ROOT / 'bayarea' / 'maps'
    out_dir.mkdir(parents=True, exist_ok=True)
    # candidate neighbours drawn for context: every county whose state FIPS is in state_prefixes
    ctx = {}
    for gid, g in by_id.items():
        if gid[:2] in state_prefixes:
            polys = polygons_of(g, arcs)
            xs = [p[0] for q in polys for p in q[0]]
            ys = [p[1] for q in polys for p in q[0]]
            ctx[gid] = (polys, (min(xs), min(ys), max(xs), max(ys)))
    k = math.radians(1) * 6371008.8
    maps = {}
    for gid, P in counties.items():
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
        land, theta0, ctr, fab = city_fabric(P['outline_local_m'], left, top, mpp, int(gid), near_water)
        n_art, art_lines = arterials(ImageDraw.Draw(land), theta0, ctr, P['outline_local_m'], left, top, mpp, int(gid))
        img.paste(land, (0, 0), mask)
        # the GROUND layer: water, neighbouring land, parish land use + streets - snapshot BEFORE any text,
        # pins, borders, banner or legend is drawn, so no label is ever draped on the 3D ground
        ground = img.copy()
        ground_tiles = retag_tiles(save_ground_tiles(ground, out_dir, gid, left, top, right, bottom, mpp))
        streets = retag_streets(out_dir, gid, save_streets(out_dir, gid, P, fab, art_lines, mpp, stamp))
        P['districts'] = districts_of(gid, P, fab)
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
            nb = counties[b['with']]
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
            for line_i, txt in enumerate((W['name'], 'open water (outside every land outline)')):
                bb = d.textbbox((x, y + line_i * 64), txt, font=font(58 - line_i * 16), anchor='mm')
                if free(bb):
                    taken.append(bb)
                    d.text((x, y + line_i * 64), txt, font=font(58 - line_i * 16), fill=COL['water_ink'],
                           anchor='mm', stroke_width=5, stroke_fill=(255, 255, 255))
        # pins
        for L, colr, tag in ([(L, COL['lmk'], 'AUTHORED') for L in P['campuses'] + P['restoration_sites']]
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
               f"{mpp:.2f} m per pixel  |  no real elevation  |  districts AUTHORED, not official neighbourhoods",
               font=font(46), fill=COL['ink'], anchor='lm', stroke_width=5, stroke_fill=(255, 255, 255))
        # legend
        lx, ly = 48, SIZE - 758
        d.rectangle([lx, ly, lx + 1840, SIZE - 48], fill=COL['panel'], outline=COL['ink'], width=4)
        rows = [('land', 'county land (RECORDED outline, coarse)'),
                ('nbr', 'neighbouring land (RECORDED outline)'),
                ('water', 'open water = outside every land outline (bay / ocean side; not surveyed)'),
                ('inland', 'inland water (reservoirs, sloughs, delta) is NOT cut out at 1:10m: fabric over it is not land'),
                ('fabric', FABRIC_NOTE + '; districts AUTHORED'),
                ('landuse', 'AUTHORED land use: residential, commercial, park, industrial + building hints'),
                ('border', 'shared border with a selected county (walk/drive across)'),
                ('lmk', 'campus (geo registry, as tagged) / restoration site (restoration registry, RECORDED)'),
                ('anchor', 'city point: RECORDED (geo registry, Locator.X CITIES, Apache-2.0)')]
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
            'path': f'bayarea/maps/{gid}-4k.webp', 'preview': f'bayarea/maps/{gid}-512.webp',
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
            'ground_tiles': ground_tiles, 'streets': streets,
        }
        print(f'  map {gid}: {f4.stat().st_size} bytes, {mpp:.2f} m/px')
    return maps

