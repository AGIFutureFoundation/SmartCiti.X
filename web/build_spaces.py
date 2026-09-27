#!/usr/bin/env python3
"""The custom spaces page: every declared training space drawn as a floor plan
a rep can read.

Rendered from spaces/registry/spaces.json and nothing else - the registry is
embedded verbatim, every figure on the page is read from it, the plan is drawn
at one declared metres-to-pixels scale, each item is labelled with its
registry name, the finishes are swatched with the catalogue colours the
registry copied by id, the PPE is the derived list, and every space links to
the 3D hall of each union it serves and to the lessons page. The page says
what the registry says: these spaces are declared, not yet walkable.
"""
import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402
from sitenav import nav_html, labels as nav_labels, NAV_CSS  # noqa: E402

ROOT = HERE.parent
REG_PATH = ROOT / 'spaces/registry/spaces.json'
reg = json.loads(REG_PATH.read_text())

PX_PER_M = 40          # declared once; every plan and every item is scaled by it
PLAN_PAD_PX = 24       # room for the dimension ticks around a plan
LESSONS_HREF = 'trade_craft_lessons.html'
HALL_HREF = 'trade_craft_3d.html?hall='


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def px(m):
    return round(m * PX_PER_M, 2)


KIND_FILL = {
    'prop': 'var(--steel)', 'furniture': 'var(--mark)', 'seat': 'var(--good)',
    'station': 'var(--crit)', 'crib': 'var(--mark)', 'sign': 'var(--muted)',
}

# Item labels. Placed at build, deterministically: each label's box is
# estimated from its character count at the label font (a monospace advance
# is 0.6 em; LABEL_EM pads it), and a greedy pass sets each label at the first
# candidate spot, nearest its item first, that stays inside the floor and
# overlaps no label already placed (and, where it can, no other item). A label
# set away from its item gets a leader line back to it.
LABEL_FONT_PX = 9
LABEL_EM = 0.62              # estimated advance per character, in em (Plex Mono is 0.60)
LABEL_LH = 11                # line pitch of a wrapped label
LABEL_ASC, LABEL_DESC = 8, 3 # box above the first baseline / below the last
LABEL_WRAP = 26              # characters per label line before it wraps
LABEL_GAP = 2                # clear space kept between label boxes
FLOOR_INSET = 4              # labels stay clear of the wall stroke
MIN_CONTRAST = 4.5           # WCAG AA for text
INKS = ('#0C1113', '#E8EDEC')  # the page's --sunk and --ink


def _lum(hexc):
    h = hexc.lstrip('#')
    ch = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    ch = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def label_ink(floor_hex):
    """The page ink with the most contrast on this floor; it must reach 4.5:1."""
    ink = max(INKS, key=lambda c: (contrast(c, floor_hex), c))
    if contrast(ink, floor_hex) < MIN_CONTRAST:
        raise SystemExit(f'build_spaces: no page ink reaches {MIN_CONTRAST}:1 on floor {floor_hex}')
    return ink


def wrap(name):
    lines, cur = [], ''
    for w in name.split(' '):
        if cur and len(cur) + 1 + len(w) > LABEL_WRAP:
            lines.append(cur)
            cur = w
        else:
            cur = f'{cur} {w}' if cur else w
    lines.append(cur)
    return lines


def _hit(a, b, gap=0):
    return not (a[2] + gap <= b[0] or b[2] + gap <= a[0] or a[3] + gap <= b[1] or b[3] + gap <= a[1])


def place_labels(entries, area):
    """entries: [(key, own_box, (cx, cy), lines)] -> {key: box}. Greedy, in a
    fixed order (the largest label first, then registry order)."""
    ax0, ay0, ax1, ay1 = area
    placed = {}
    order = sorted(entries, key=lambda e: (-len(e[3]) * max(len(t) for t in e[3]), e[0]))
    for key, own, (cx, cy), lines in order:
        bw = round(max(len(t) for t in lines) * LABEL_FONT_PX * LABEL_EM + 2, 2)
        bh = LABEL_ASC + (len(lines) - 1) * LABEL_LH + LABEL_DESC
        if bw > ax1 - ax0 or bh > ay1 - ay0:
            raise SystemExit(f'build_spaces: label {lines!r} does not fit the floor')

        def box_at(mx, my):
            x0 = min(max(mx - bw / 2, ax0), ax1 - bw)
            y0 = min(max(my - bh / 2, ay0), ay1 - bh)
            return (round(x0, 2), round(y0, 2), round(x0 + bw, 2), round(y0 + bh, 2))
        cands = [box_at(cx, cy),
                 box_at(cx, own[3] + 2 + bh / 2), box_at(cx, own[1] - 2 - bh / 2),
                 box_at(own[2] + 3 + bw / 2, cy), box_at(own[0] - 3 - bw / 2, cy)]
        r = 12
        while r < 2 * max(ax1 - ax0, ay1 - ay0):
            for k in range(16):
                a = math.radians(90 + k * 22.5)
                cands.append(box_at(cx + r * math.cos(a), cy + r * math.sin(a)))
            r += 8
        others = [e[1] for e in entries if e[0] != key]
        pick = None
        for strict in (True, False):
            for b in cands:
                if any(_hit(b, q, LABEL_GAP) for q in placed.values()):
                    continue
                if strict and any(_hit(b, o) for o in others):
                    continue
                pick = b
                break
            if pick:
                break
        if pick is None:
            raise SystemExit(f'build_spaces: no free spot for label {lines!r}')
        placed[key] = pick
    return placed


def label_svg(it, box, lines, side, own, centre, ink, floor_hex):
    x0, y0, x1, y1 = box
    tx = {'start': x0 + 1, 'end': x1 - 1, 'middle': (x0 + x1) / 2}[side]
    tx = round(tx, 2)
    ty = round(y0 + LABEL_ASC, 2)
    spans = ''.join(f'<tspan x="{tx}" dy="{0 if i == 0 else LABEL_LH}">{esc(t)}</tspan>'
                    for i, t in enumerate(lines))
    leader = ''
    near = (own[0] - 4, own[1] - 4, own[2] + 4, own[3] + 4)
    if not _hit(box, near):
        cx, cy = centre
        lx, ly = min(max(cx, x0), x1), min(max(cy, y0), y1)
        leader = (f'<line class="leader" x1="{round(cx, 2)}" y1="{round(cy, 2)}" '
                  f'x2="{round(lx, 2)}" y2="{round(ly, 2)}" stroke="{ink}" stroke-width="0.75"/>')
    return (leader + f'<text class="lbl" data-label-for="{it["i"]}" x="{tx}" y="{ty}" '
            f'text-anchor="{side}" font-size="{LABEL_FONT_PX}" fill="{ink}" stroke="{esc(floor_hex)}" '
            f'stroke-width="3" paint-order="stroke">{spans}</text>')


def plan_svg(s):
    W, D = s['footprint_m']['w'], s['footprint_m']['d']
    w_px, d_px = px(W), px(D)
    vw, vh = w_px + 2 * PLAN_PAD_PX, d_px + 2 * PLAN_PAD_PX
    floor_hex = s['floor']['color']
    ink = label_ink(floor_hex)
    parts = [
        f'<svg class="plan" viewBox="0 0 {vw} {vh}" width="{vw}" height="{vh}" '
        f'role="img" aria-label="{esc(s["title"])} floor plan" data-plan="{esc(s["id"])}" '
        f'data-px-per-m="{PX_PER_M}">',
        # the floor, in its catalogue colour; the wall as a stroke in its colour
        f'<rect class="floor" x="{PLAN_PAD_PX}" y="{PLAN_PAD_PX}" width="{w_px}" height="{d_px}" '
        f'fill="{esc(floor_hex)}" stroke="{esc(s["wall"]["color"])}" stroke-width="6" '
        f'data-floor="{esc(s["floor"]["id"])}" data-wall="{esc(s["wall"]["id"])}"/>',
        # dimension ticks
        f'<text class="dim" x="{PLAN_PAD_PX + w_px / 2}" y="{PLAN_PAD_PX - 8}" '
        f'text-anchor="middle" data-dim="w">{W} m</text>',
        f'<text class="dim" x="{PLAN_PAD_PX - 8}" y="{PLAN_PAD_PX + d_px / 2}" '
        f'text-anchor="middle" transform="rotate(-90 {PLAN_PAD_PX - 8} {PLAN_PAD_PX + d_px / 2})" '
        f'data-dim="d">{D} m</text>',
    ]
    # y grows upward in the declaration (bottom-left origin); SVG y grows down
    geo = {}
    for it in s['items']:
        if it['footprint'] is None:
            cx, cy = PLAN_PAD_PX + px(it['x']), PLAN_PAD_PX + d_px - px(it['y'])
            geo[it['i']] = ((cx - 9, cy - 9, cx + 9, cy + 9), (cx, cy))
        else:
            x0, y0, x1, y1 = it['rect']
            rx, ry = PLAN_PAD_PX + px(x0), PLAN_PAD_PX + d_px - px(y1)
            rw, rh = px(x1 - x0), px(y1 - y0)
            geo[it['i']] = ((rx, ry, rx + rw, ry + rh), (rx + rw / 2, ry + rh / 2))
    lines_of = {it['i']: wrap(it['name']) for it in s['items']}
    area = (PLAN_PAD_PX + FLOOR_INSET, PLAN_PAD_PX + FLOOR_INSET,
            PLAN_PAD_PX + w_px - FLOOR_INSET, PLAN_PAD_PX + d_px - FLOOR_INSET)
    boxes = place_labels([(i, g[0], g[1], lines_of[i]) for i, g in geo.items()], area)

    def side_of(cx):
        # the anchor faces into the plan: a label near a wall reads away from it
        if cx < PLAN_PAD_PX + w_px / 3:
            return 'start'
        if cx > PLAN_PAD_PX + 2 * w_px / 3:
            return 'end'
        return 'middle'

    for it in s['items']:
        fill = KIND_FILL[it['kind']]
        own, (cx, cy) = geo[it['i']]
        lbl = label_svg(it, boxes[it['i']], lines_of[it['i']], side_of(cx), own, (cx, cy), ink, floor_hex)
        if it['footprint'] is None:
            parts.append(
                f'<g class="item unknown" data-item="{it["i"]}" data-kind="{esc(it["kind"])}" '
                f'data-id="{esc(it["id"])}">'
                f'<circle cx="{cx}" cy="{cy}" r="9" fill="none" stroke="{fill}" '
                f'stroke-width="1.5" stroke-dasharray="3 2"/>'
                f'{lbl}'
                f'<title>{esc(it["name"])} ({esc(it["kind"])} {esc(it["id"])}) - '
                f'{esc(it["footprint_note"])}</title></g>')
            continue
        rx, ry, rx1, ry1 = own
        rw, rh = px(it['rect'][2] - it['rect'][0]), px(it['rect'][3] - it['rect'][1])
        parts.append(
            f'<g class="item" data-item="{it["i"]}" data-kind="{esc(it["kind"])}" '
            f'data-id="{esc(it["id"])}">'
            f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" fill="{fill}" '
            f'fill-opacity="0.55" stroke="{fill}" stroke-width="1"/>'
            f'{lbl}'
            f'<title>{esc(it["name"])} ({esc(it["kind"])} {esc(it["id"])}) - '
            f'{it["footprint"]["w"]} x {it["footprint"]["d"]} m</title></g>')
    parts.append('</svg>')
    return ''.join(parts)


def space_section(s):
    halls = ''.join(
        f'<a class="hall" href="{HALL_HREF}{esc(u["slug"])}" data-hall="{esc(u["slug"])}">'
        f'{esc(u["name"])} hall (3D)</a>' for u in s['unions'])
    fits = ''.join(
        f'<li>{esc(e["label"])} of {esc(e["hall"])}: '
        f'<span data-env="{esc(e["hall"])}">{e["w_m"]} x {e["d_m"]} m</span></li>' for e in s['fits_in'])
    ppe = (''.join(f'<li data-ppe="{esc(p)}">{esc(p)}</li>' for p in s['ppe']['required'])
           or '<li class="none" data-ppe-none="1">none derived: the strand names no base PPE and the finishes stand for no hazard</li>')
    hazards = (', '.join(f'{esc(h["hazard"])} ({esc(h["from"])} {esc(h["finish"])})' for h in s['hazards'])
               or 'none')
    kinds = ''.join(
        f'<span class="chip" data-kind-count="{k}">{n} {k}</span>'
        for k, n in s['counts']['by_kind'].items() if n)
    not_est = ''.join(
        f'<li>{esc(r["kind"])} {esc(r["id"])}: {esc(r["why"])}</li>' for r in s['cost']['not_estimated'])
    rows = ''.join(
        f'<tr data-row="{it["i"]}"><td>{it["i"]}</td><td>{esc(it["kind"])}</td>'
        f'<td><code>{esc(it["id"])}</code></td><td>{esc(it["name"])}</td>'
        f'<td class="num">{it["x"]}, {it["y"]}</td><td class="num">{it["rotation"]}</td>'
        f'<td class="num">'
        + (f'{it["footprint"]["w"]} x {it["footprint"]["d"]}' if it['footprint'] is not None
           else f'<em>{esc(it["footprint_note"])}</em>')
        + '</td></tr>' for it in s['items'])
    c = s['cost']
    return f'''<section class="space" id="space-{esc(s["id"])}" data-space="{esc(s["id"])}">
<h2>{esc(s["title"])} <span class="status" data-status>{esc(s["status"])}</span></h2>
<p class="purpose">{esc(s["purpose"])}</p>
<p class="serves">Serves {halls} · <a href="{LESSONS_HREF}" data-lessons>lessons</a>
 · would stand in the <b>{esc(s["room_label"])}</b> ({esc(s["strand"])} strand)</p>
<div class="cols">
<div class="planwrap">{plan_svg(s)}</div>
<div class="facts">
<div class="figs">
 <div class="fig"><b data-fig="area" data-space-fig="{esc(s["id"])}">{s["footprint_m"]["area_m2"]}</b><span>m² · {s["footprint_m"]["w"]} x {s["footprint_m"]["d"]} m</span></div>
 <div class="fig"><b data-fig="items" data-space-fig="{esc(s["id"])}">{s["counts"]["items"]}</b><span>items</span></div>
 <div class="fig"><b data-fig="tris" data-space-fig="{esc(s["id"])}">{c["tris"]}</b><span>triangles (declared budgets)</span></div>
 <div class="fig"><b data-fig="draw_calls" data-space-fig="{esc(s["id"])}">{c["draw_calls"]}</b><span>draw calls (pooled by material)</span></div>
 <div class="fig"><b data-fig="not_estimated" data-space-fig="{esc(s["id"])}">{len(c["not_estimated"])}</b><span>items not estimated</span></div>
</div>
<p class="chips">{kinds}</p>
<h3>Finishes</h3>
<p class="swatches">
 <span class="swatch"><i style="background:{esc(s["floor"]["color"])}" data-swatch="floor" data-finish="{esc(s["floor"]["id"])}"></i>floor: {esc(s["floor"]["name"])} <code>{esc(s["floor"]["id"])}</code> ({esc(s["floor"]["pattern"])})</span>
 <span class="swatch"><i style="background:{esc(s["wall"]["color"])}" data-swatch="wall" data-finish="{esc(s["wall"]["id"])}"></i>wall: {esc(s["wall"]["name"])} <code>{esc(s["wall"]["id"])}</code> ({esc(s["wall"]["pattern"])})</span>
</p>
<h3>PPE required <small>(derived, never typed)</small></h3>
<ul class="ppe" data-ppe-list="{esc(s["id"])}">{ppe}</ul>
<p class="hz">Hazards the finishes stand for: {hazards}</p>
<h3>Fits the room the 3D builder lays out</h3>
<ul class="fits">{fits}</ul>
<h3>Not estimated</h3>
<ul class="notest" data-not-estimated="{esc(s["id"])}">{not_est or '<li>every item declares a figure</li>'}</ul>
</div>
</div>
<details><summary>Item schedule ({s["counts"]["items"]})</summary>
<table class="sched"><thead><tr><th>#</th><th>kind</th><th>id</th><th>name</th><th>x, y (m)</th><th>rot</th><th>footprint (m)</th></tr></thead>
<tbody>{rows}</tbody></table></details>
</section>'''


c = reg['counts']
sections = '\n'.join(space_section(s) for s in reg['spaces'])
kind_legend = ''.join(
    f'<span class="lg"><i style="background:{KIND_FILL[k]}"></i>{k}</span>' for k in reg['kinds'])
toc = ''.join(f'<a href="#space-{esc(s["id"])}">{esc(s["title"])}</a>' for s in reg['spaces'])
embedded = json.dumps(reg, indent=1, sort_keys=True).replace('</', '<\\/')

NAV = nav_html('web/trade_craft_spaces.html', nav_labels('en'))

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' stroke='%23E8A33D' stroke-width='2.6' stroke-linejoin='round'/%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E">
<title>SmartCiti.X : Trade Craft Academy — custom spaces</title>
<style>
:root{{
  --plate:#12181B; --panel:#182023; --sunk:#0C1113; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --mark-ink:#12181B; --steel:#41C4D4; --good:#5FBF7A; --crit:#E0655B;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--plate);color:var(--ink);
  font:16px/1.6 "IBM Plex Sans",system-ui,sans-serif;padding:0 16px 48px}}
.wrap{{max-width:1180px;margin:0 auto}}
header{{padding:40px 0 8px;border-bottom:3px solid var(--mark)}}
header h1{{font:700 34px/1.1 "Barlow Condensed",system-ui,sans-serif;margin:0}}
header h1 .x{{color:var(--mark)}}
header p{{color:var(--muted);margin:6px 0 14px}}
a{{color:var(--steel)}}
.toc{{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}}
.toc a{{background:var(--panel);border:1px solid var(--rule);border-radius:6px;padding:6px 12px;text-decoration:none;color:var(--ink)}}
.figs{{display:flex;flex-wrap:wrap;gap:12px;margin:14px 0}}
.fig{{background:var(--panel);border:1px solid var(--rule);border-radius:8px;padding:10px 16px;min-width:120px}}
.fig b{{display:block;font:600 24px/1.2 "Barlow Condensed",system-ui,sans-serif;color:var(--mark)}}
.fig span{{color:var(--muted);font-size:13px}}
.honesty{{background:var(--sunk);border-inline-start:3px solid var(--mark);border-radius:6px;padding:14px 26px;color:var(--muted);font-size:14px}}
.space{{border-top:1px solid var(--rule);padding:28px 0}}
.space h2{{font:700 28px/1.1 "Barlow Condensed",system-ui,sans-serif;margin:0 0 6px}}
.status{{font:600 13px/1 "IBM Plex Mono",monospace;color:var(--mark-ink);background:var(--mark);border-radius:4px;padding:4px 8px;vertical-align:middle;text-transform:uppercase}}
.purpose{{margin:4px 0}}
.serves{{color:var(--muted);font-size:14px}}
.hall{{margin-inline-end:6px}}
.cols{{display:flex;flex-wrap:wrap;gap:24px;align-items:flex-start}}
.planwrap{{overflow-x:auto;max-width:100%;background:var(--sunk);border:1px solid var(--rule);border-radius:8px;padding:8px}}
.plan .dim{{fill:var(--muted);font:11px "IBM Plex Mono",monospace}}
.plan .item text.lbl{{font-family:"IBM Plex Mono",monospace;pointer-events:none}}
.plan .item .leader{{stroke-opacity:.8}}
.facts{{flex:1 1 340px;min-width:0}}
.facts h3{{font:600 16px/1.2 "Barlow Condensed",system-ui,sans-serif;margin:16px 0 6px;text-transform:uppercase;letter-spacing:.04em}}
.facts h3 small{{color:var(--muted);text-transform:none;letter-spacing:0;font-weight:400}}
.chips{{display:flex;flex-wrap:wrap;gap:6px}}
.chip,.lg{{background:var(--panel);border:1px solid var(--rule);border-radius:999px;padding:2px 10px;font-size:13px;color:var(--muted)}}
.lg i,.swatch i{{display:inline-block;width:14px;height:14px;border-radius:3px;vertical-align:-2px;margin-inline-end:6px;border:1px solid var(--rule)}}
.swatches{{display:flex;flex-direction:column;gap:6px;font-size:14px}}
.ppe{{margin:0;padding-inline-start:20px;columns:2}}
.ppe .none{{color:var(--muted);font-style:italic;columns:1}}
.hz,.fits,.notest{{color:var(--muted);font-size:14px}}
.fits,.notest{{margin:0;padding-inline-start:20px}}
details{{margin-top:14px}}
summary{{cursor:pointer;color:var(--steel)}}
.sched{{border-collapse:collapse;width:100%;font-size:13px;margin-top:8px}}
.sched th,.sched td{{border-top:1px solid var(--rule);padding:4px 8px;text-align:start;vertical-align:top}}
.sched th{{color:var(--muted);font-weight:600}}
.num{{font-variant-numeric:tabular-nums;white-space:nowrap}}
code{{font:13px "IBM Plex Mono",monospace;color:var(--steel)}}
.legend{{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}}
</style>
<style>{NAV_CSS}</style>
</head>
<body>
{NAV}<div class="wrap">
<header>
  <h1>SmartCiti<span class="x">.X</span> : Trade Craft Academy</h1>
  <p>powered by AGI Corp · custom spaces</p>
</header>
<p class="intro">Purpose-built training spaces a union or a programme declares, composed only from assets this bundle already holds and validated at build. Every space here is <b data-pack-status>{esc(reg["status"])}</b>: an authored proposal drawn as a floor plan, not a room anyone can walk into yet, and no dimension is a measurement of a real venue.</p>
<div class="figs">
 <div class="fig"><b data-fig="spaces">{c["spaces"]}</b><span>spaces declared</span></div>
 <div class="fig"><b data-fig="items">{c["items"]}</b><span>items placed</span></div>
 <div class="fig"><b data-fig="unions_served">{c["unions_served"]}</b><span>unions served</span></div>
 <div class="fig"><b data-fig="ppe_items">{c["ppe_items"]}</b><span>distinct PPE items derived</span></div>
 <div class="fig"><b data-fig="tris">{c["tris"]}</b><span>triangles, declared budgets</span></div>
 <div class="fig"><b data-fig="draw_calls">{c["draw_calls"]}</b><span>draw calls estimated</span></div>
 <div class="fig"><b data-fig="cost_estimated_items">{c["cost_estimated_items"]}</b><span>items with a declared figure</span></div>
 <div class="fig"><b data-fig="cost_not_estimated_items">{c["cost_not_estimated_items"]}</b><span>items not estimated</span></div>
 <div class="fig"><b data-fig="footprint_unknown">{c["footprint_unknown"]}</b><span>items with footprint unknown</span></div>
 <div class="fig"><b data-fig="area_m2">{c["area_m2"]}</b><span>m² declared in all</span></div>
</div>
<p class="legend">{kind_legend} <span class="lg">scale: 1 m = <span data-px-per-m>{PX_PER_M}</span> px</span></p>
<nav class="toc">{toc}</nav>
<ul class="honesty">
<li>{esc(reg["honesty"]["status"])}</li>
<li>{esc(reg["honesty"]["envelope"])}</li>
<li>{esc(reg["honesty"]["ppe"])}</li>
<li>{esc(reg["honesty"]["footprints"])}</li>
<li>{esc(reg["honesty"]["cost"])}</li>
<li>{esc(reg["honesty"]["not_stated"])}</li>
</ul>
{sections}
<footer class="serves">Registry: <code>spaces/registry/spaces.json</code> · stamp <code data-stamp>{esc(reg["source_stamp"])}</code> · authored <code data-authored-stamp>{esc(reg["authored_stamp"])}</code> · embedded verbatim below.</footer>
<script type="application/json" id="spaces-registry">{embedded}</script>
</div></body>
</html>
'''

out = HERE / 'trade_craft_spaces.html'
emit(out, page, f'{c["spaces"]} spaces | {c["items"]} items | stamp {reg["source_stamp"]}')
