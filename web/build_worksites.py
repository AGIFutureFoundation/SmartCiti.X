#!/usr/bin/env python3
"""The work sites page: every declared work site drawn as a plan on its place
with the crew's roles as marked positions and the hand-offs as numbered
arrows between them.

Rendered from worksites/registry/worksites.json and nothing else - the
registry is embedded verbatim, every figure on the page is read from it, each
role stands at the polar post the crews registry gives it, every hand-off is
one numbered arrow from the post of the role handing off to the post of the
role receiving, the gates and the stop-work line are listed, and every site
links to the 3D hall of each union on it, to the custom spaces page when its
place is a space, and to the lessons page. No crew page exists in this bundle
and the page says so rather than linking to one. The page says what the
registry says: authored scenarios, no multi-user session, no certification.
"""
import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402
from seo import apply_seo  # noqa: E402  head tags only
from sitenav import nav_html, labels as nav_labels, NAV_CSS  # noqa: E402

ROOT = HERE.parent
REG_PATH = ROOT / 'worksites/registry/worksites.json'
reg = json.loads(REG_PATH.read_text())

PX_PER_M = 24          # one declared scale for a space plan
TILE_PX = 360          # a campus or a site has no footprint here: one square tile
POST_SCALE_PX = 20     # px per metre of a role's polar post radius
LESSONS_HREF = 'trade_craft_lessons.html'
SPACES_HREF = 'trade_craft_spaces.html'
HALL_HREF = 'trade_craft_3d.html?hall='
CREW_PAGE = None       # no crew page exists in this bundle


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def posts(site, cx, cy):
    out = {}
    for rid, r in site['roles'].items():
        a = math.radians(r['post']['deg'])
        out[rid] = (round(cx + r['post']['r'] * POST_SCALE_PX * math.cos(a), 1),
                    round(cy + r['post']['r'] * POST_SCALE_PX * math.sin(a), 1))
    return out


# Text boxes are estimated at build from character count x font size (a
# monospace advance is 0.6 em; TEXT_EM pads it), so the builder can keep the
# hand-off badges off the role labels and fit the viewBox to what it drew.
TEXT_EM = 0.62
LABEL_PX = 10          # role name and union under each post
DIM_PX = 11            # the place name and districts on a tile
BADGE_R = 9            # a hand-off's numbered badge
POST_R = 14            # a role's post
VIEW_MARGIN = 12       # the viewBox is the drawing's bounds plus this, each side


def text_box(x, y, s, size, anchor='start'):
    w = len(s) * size * TEXT_EM
    x0 = x - w / 2 if anchor == 'middle' else (x - w if anchor == 'end' else x)
    return (x0, y - 0.8 * size, x0 + w, y + 0.3 * size)


def _hit(a, b, gap=0):
    return not (a[2] + gap <= b[0] or b[2] + gap <= a[0] or a[3] + gap <= b[1] or b[3] + gap <= a[1])


def plan_svg(site):
    place = site['place']
    plan = place['plan']
    parts = []
    bounds = []                         # every box drawn, for the viewBox
    pad = 8 * POST_SCALE_PX             # room for the posts around the place
    if plan['kind'] == 'space-plan':
        W, D = plan['footprint_m']['w'], plan['footprint_m']['d']
        vw, vh = round(W * PX_PER_M), round(D * PX_PER_M)
        parts.append(f'<rect x="{pad}" y="{pad}" width="{vw}" height="{vh}" fill="var(--sunk)" stroke="var(--rule)" data-plan="space" data-w-m="{W}" data-d-m="{D}"/>')
        bounds.append((pad, pad, pad + vw, pad + vh))
        for it in plan['items']:
            # the spaces registry's rect: [x0, y0, x1, y1] in metres, origin bottom-left
            x0, y0, x1, y1 = it['rect']
            rx, ry = round(pad + x0 * PX_PER_M, 1), round(pad + (D - y1) * PX_PER_M, 1)
            rw, rh = round((x1 - x0) * PX_PER_M, 1), round((y1 - y0) * PX_PER_M, 1)
            tip = f'<title>{esc(it["kind"])}: {esc(it["id"])}</title>'
            if rw == 0 and rh == 0:     # a point: the registry declares no footprint
                parts.append(f'<circle class="item" cx="{rx}" cy="{ry}" r="4" data-item="{it["i"]}">{tip}</circle>')
            else:
                parts.append(f'<rect class="item" x="{rx}" y="{ry}" width="{rw}" height="{rh}" data-item="{it["i"]}">{tip}</rect>')
        cx, cy = pad + vw / 2, pad + vh / 2
    else:
        label = ' · '.join(plan['districts']) if plan['kind'] == 'campus-tile' else plan['habitat']
        parts.append(f'<rect x="{pad}" y="{pad}" width="{TILE_PX}" height="{TILE_PX}" rx="12" fill="var(--sunk)" stroke="var(--rule)" data-plan="{esc(plan["kind"])}"/>')
        parts.append(f'<text class="dim" x="{pad + 10}" y="{pad + 20}">{esc(place["name"])}</text><text class="dim" x="{pad + 10}" y="{pad + 38}">{esc(label)}</text>')
        bounds += [(pad, pad, pad + TILE_PX, pad + TILE_PX),
                   text_box(pad + 10, pad + 20, place['name'], DIM_PX), text_box(pad + 10, pad + 38, label, DIM_PX)]
        cx = cy = pad + TILE_PX / 2
    P = posts(site, cx, cy)
    # what a badge must keep off: every post and every role label
    keep_off = []
    for rid, (x, y) in P.items():
        r = site['roles'][rid]
        keep_off += [(x - POST_R, y - POST_R, x + POST_R, y + POST_R),
                     text_box(x, y + 30, r['name'], LABEL_PX, 'middle'),
                     text_box(x, y + 42, r['union'], LABEL_PX, 'middle')]
    bounds += keep_off
    parts.append(f'<defs><marker id="arr-{esc(site["id"])}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="var(--mark)"/></marker></defs>')
    badges = []
    for h in site['handoffs']:
        (x1, y1), (x2, y2) = P[h['by']], P[h['to']]
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1
        side = 1 if h['n'] % 2 else -1
        nx, ny = -dy / L, dx / L
        ox, oy = nx * 6 * side, ny * 6 * side
        sx, sy = round(x1 + dx / L * 16 + ox, 1), round(y1 + dy / L * 16 + oy, 1)
        ex, ey = round(x2 - dx / L * 16 + ox, 1), round(y2 - dy / L * 16 + oy, 1)
        cls = 'arrow' if h['verifiable'] else 'arrow unverifiable'
        parts.append(f'<line class="{cls}" x1="{sx}" y1="{sy}" x2="{ex}" y2="{ey}" marker-end="url(#arr-{esc(site["id"])})" data-handoff="{h["n"]}" data-by="{esc(h["by"])}" data-to="{esc(h["to"])}"><title>{h["n"]}. {esc(h["step"])}</title></line>')
        bounds.append((min(sx, ex) - 4, min(sy, ey) - 4, max(sx, ex) + 4, max(sy, ey) + 4))
        # the badge: first spot along its own arrow, nearest the middle and
        # on the arrow's own side, clear of every post, role label and badge
        pick = None
        for t in (0.5, 0.42, 0.58, 0.34, 0.66, 0.26, 0.74, 0.18, 0.82):
            for off in (12, 20, 28, -12, -20, 36, 44):
                mx = round(sx + (ex - sx) * t + nx * off * side, 1)
                my = round(sy + (ey - sy) * t + ny * off * side, 1)
                b = (mx - BADGE_R, my - BADGE_R, mx + BADGE_R, my + BADGE_R)
                if not any(_hit(b, o, 2) for o in keep_off + badges):
                    pick = (mx, my, b)
                    break
            if pick:
                break
        if pick is None:
            raise SystemExit(f'build_worksites: no clear spot for hand-off {h["n"]} badge on {site["id"]}')
        mx, my, b = pick
        badges.append(b)
        bounds.append(b)
        parts.append(f'<circle class="num" cx="{mx}" cy="{my}" r="{BADGE_R}" data-badge="{h["n"]}"/><text class="numt" x="{mx}" y="{round(my + 3.5, 1)}" text-anchor="middle">{h["n"]}</text>')
    for rid, (x, y) in P.items():
        r = site['roles'][rid]
        parts.append(f'<g class="post" data-role="{esc(rid)}" data-union="{esc(r["union"])}" transform="translate({x},{y})">'
                     f'<circle r="{POST_R}"/><text y="5" text-anchor="middle">{esc(r["glyph"])}</text>'
                     f'<text class="lbl" y="30" text-anchor="middle">{esc(r["name"])}</text>'
                     f'<text class="lbl u" y="42" text-anchor="middle">{esc(r["union"])}</text></g>')
    # the viewBox is the drawing's own bounds plus a margin: no empty field
    bx0 = math.floor(min(b[0] for b in bounds) - VIEW_MARGIN)
    by0 = math.floor(min(b[1] for b in bounds) - VIEW_MARGIN)
    bw = math.ceil(max(b[2] for b in bounds) + VIEW_MARGIN) - bx0
    bh = math.ceil(max(b[3] for b in bounds) + VIEW_MARGIN) - by0
    return (f'<svg class="plan" viewBox="{bx0} {by0} {bw} {bh}" width="{bw}" height="{bh}" role="img" '
            f'aria-label="plan of {esc(site["title"])}">{"".join(parts)}</svg>')


def ev_text(e):
    if e['kind'] == 'sim':
        return f'sim <code>{esc(e["sim"])}</code> / <code>{esc(e["scenario"])}</code> passed'
    if e['kind'] == 'walkaround':
        return f'walkaround <code>{esc(e["sim"])}</code> point <code>{esc(e["point"])}</code>'
    if e['kind'] == 'crew':
        return f'crew <code>{esc(e["role"])}</code> asked “{esc(e["ask"])}”'
    return f'station <code>{esc(e["station"])}</code> ({esc(e["station_name"])}) done'


def site_section(s):
    d = s['derived']
    roles = ''.join(
        f'<li data-role-row="{esc(rid)}"><b>{esc(r["glyph"])} {esc(r["name"])}</b> — <a href="{HALL_HREF}{esc(r["union"])}" data-hall="{esc(r["union"])}">{esc(r["union_name"])}</a>'
        + (f' <span class="warn">(not a hall the crew reaches: {esc(r["why_not_reached"])})</span>' if r['why_not_reached'] else '')
        + f'<br><small>{esc(r["job"])} · stops for: {esc(r["stops"])} · evidence kinds: {", ".join(d["evidence_kinds_by_role"][rid])}</small></li>'
        for rid, r in s['roles'].items())
    hand = ''.join(
        f'<tr data-handoff-row="{h["n"]}"><td class="num">{h["n"]}</td><td>{esc(h["by"])} → {esc(h["to"])}</td><td>{esc(h["step"])}</td>'
        f'<td>{ev_text(h["from_evidence"])}</td><td>{ev_text(h["to_evidence"])}</td>'
        f'<td>{"verifiable" if h["verifiable"] else "<span class=warn>unverifiable: " + esc(h["why_unverifiable"]) + "</span>"}</td></tr>'
        for h in s['handoffs'])
    ppe = s['gates']['ppe']
    if ppe['required'] is None:
        ppe_html = f'<p class="hz" data-ppe="none">{esc(ppe["why_none"])}</p>'
    else:
        ppe_html = ('<ul class="ppe">' + ''.join(f'<li data-ppe="{esc(p)}">{esc(p)}</li>' for p in ppe['required']) + '</ul>'
                    + f'<p class="hz">derived: {esc(ppe["derived_from"]["rule"])} — strand {esc(ppe["derived_from"]["strand"])}, '
                      f'hazards {esc(", ".join(ppe["derived_from"]["hazards"]) or "none")}, finishes {esc(ppe["derived_from"]["finishes"]["floor"])} / {esc(ppe["derived_from"]["finishes"]["wall"])}</p>')
    wa = ''.join(f'<li data-gate-point="{esc(g["sim"])}#{esc(g["point"])}"><b>{esc(g["label"])}</b> on <code>{esc(g["sim"])}</code>: {esc(g["check"])}</li>' for g in s['gates']['walkaround_before_first_move'])
    place_link = (f' · <a href="{s["place"]["href"]}" data-place-href>{esc(s["place"]["name"])} on the spaces page</a>' if s['place']['href'] else '')
    # #lesson-<id> is the anchor build_lessons.py writes and its fromHash() reads;
    # a bare #<id> landed on the top of the lessons page (fixed wave 3)
    lessons = ', '.join(f'<a href="{LESSONS_HREF}#lesson-{esc(l)}" data-lesson="{esc(l)}">{esc(l)}</a>' for l in d['lessons_with_this_crew']) or 'none name this crew'
    board = task_board(site_tasks(s), S('tasks.here'), TASK_LABELS, board_id=f'tasks-{s["id"]}')
    return f'''<section class="site" id="site-{esc(s["id"])}" data-site="{esc(s["id"])}">
<h2>{esc(s["title"])} <span class="status">authored scenario</span></h2>
<p class="purpose">{esc(s["job"])}</p>
<p class="serves">Place: <b data-place-kind="{esc(s["place"]["kind"])}">{esc(s["place"]["kind"])}</b> <code>{esc(s["place"]["id"])}</code>{place_link} · Crew: <b data-crew="{esc(s["crew"]["id"])}">{esc(s["crew"]["name"])}</b> on seat <code>{esc(s["crew"]["seat"])}</code>
 · <span data-crew-page="none">no crew page exists in this bundle</span> · <a href="{LESSONS_HREF}" data-lessons>lessons</a></p>
<div class="figs">
 <div class="fig"><b data-site-fig="roles">{d["roles"]}</b><span>roles</span></div>
 <div class="fig"><b data-site-fig="unions">{len(d["unions"])}</b><span>unions</span></div>
 <div class="fig"><b data-site-fig="handoffs">{d["handoffs"]}</b><span>hand-offs</span></div>
 <div class="fig"><b data-site-fig="handoffs_verifiable">{d["handoffs_verifiable"]}</b><span>verifiable from records</span></div>
 <div class="fig"><b data-site-fig="seats">{len(d["seats"])}</b><span>seats involved</span></div>
</div>
<div class="cols">
<div class="planwrap">{plan_svg(s)}</div>
<div class="facts">
<h3>Roles <small>each a marked position on the plan</small></h3><ul class="roles">{roles}</ul>
<h3>Stop work</h3><p class="stop" data-stop-work>{esc(s["stop_work"])}</p>
<h3>Gates <small>PPE is derived, never typed</small></h3>{ppe_html}
<ul class="gates">{wa}</ul>
<h3>Lessons that name this crew</h3><p class="serves">{lessons}</p>
</div></div>
{board}
<details><summary>Hand-offs, in order, with the evidence at each end</summary>
<div class="tablewrap"><table class="sched"><thead><tr><th>#</th><th>hand-off</th><th>step</th><th>from-evidence</th><th>to-evidence</th><th>verifiable?</th></tr></thead><tbody>{hand}</tbody></table></div></details>
</section>'''


# Simulated tasks for each site, from web/taskkit.py (tasks/registry/tasks.json
# only): the site's own crew hand-off, plus every task on the crew's seat -
# its walkaround and the scenarios on the site's campus (all of them when the
# site is a space with no campus). Counts are taskkit's, never typed here.
from taskkit import (task_by_id, tasks_for_seat, task_board, labels_from,  # noqa: E402
                     TASKS_CSS, TASK_FILTER_JS, TASKS as TASK_REG)
_EN_STRINGS = json.loads((ROOT / 'i18n/locales/en.json').read_text(encoding='utf-8'))['strings']
TASK_LABELS = labels_from(_EN_STRINGS)


def S(key):
    if key not in _EN_STRINGS:
        raise KeyError(f'i18n: no en value for {key}')
    return _EN_STRINGS[key]


def site_tasks(s):
    own = task_by_id(f'crew-{s["id"]}')
    camp = s['place']['campus']
    seat = [t for t in tasks_for_seat(s['crew']['seat']) if t['kind'] != 'crew-handoff'
            and (camp is None or t['kind'] != 'sim-scenario' or t['place']['campus'] == camp)]
    return [own] + seat


c = reg['counts']
TASKS_ON_SITES = sorted({t['id'] for s in reg['sites'] for t in site_tasks(s)})
sections = '\n'.join(site_section(s) for s in reg['sites'])
toc = ''.join(f'<a href="#site-{esc(s["id"])}">{esc(s["title"])}</a>' for s in reg['sites'])
embedded = json.dumps(reg, indent=1, sort_keys=True).replace('</', '<\\/')
places = ' · '.join(f'{k}: <b data-fig-place="{esc(k)}">{v}</b>' for k, v in c['places_by_kind'].items())

NAV = nav_html('web/trade_craft_worksites.html', nav_labels('en'))
# The page's hero band (MEDIA's web/pagehero.py,
# THEME_CONTRACT); every word is a tasks.ws.* catalog string. The band's title
# is the page's one <h1>.
from pagehero import pagehero  # noqa: E402
HERO_CSS, HERO_HTML, HERO_JS = pagehero('web/trade_craft_worksites.html', {
    'clip': 'hall-orbit', 'kicker': S('tasks.ws.kicker'), 'title': S('tasks.ws.title'),
    'accent': S('tasks.ws.accent'), 'accent_style': 'gradient', 'lede': S('tasks.ws.lede'),
    'actions': [{'text': S('tasks.ws.cta'), 'href': f'#site-{reg["sites"][0]["id"]}', 'kind': 'primary'}],
    'as_h1': True, 'labels': {'pause': S('tasks.ws.pause'), 'play': S('tasks.ws.play')},
    'credit': S('tasks.ws.credit'),
})
# theme('doc') is NOT taken: its light palette under prefers-color-scheme
# fought this page's own dark tokens (dark panels on a light page); the nav's
# Style switcher re-declares the page tokens instead, so every style applies.
from questkit import QUEST_CSS, quest_js, page_hooks  # noqa: E402  quests: egg hooks only
QUEST_TAIL = '<style>' + QUEST_CSS + '</style>\n' + page_hooks('web/trade_craft_worksites.html') + quest_js('page:web/trade_craft_worksites.html')

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' stroke='%23E8A33D' stroke-width='2.6' stroke-linejoin='round'/%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E">
<title>SmartCiti.X : Trade Craft Academy — work sites</title>
<style>
:root{{
  --plate:#12181B; --panel:#182023; --sunk:#0C1113; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --mark-ink:#12181B; --steel:#41C4D4; --good:#5FBF7A; --crit:#E0655B;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--plate);color:var(--ink);font:16px/1.6 "IBM Plex Sans",system-ui,sans-serif;padding:0 16px 48px}}
.wrap{{max-width:1180px;margin:0 auto}}
header{{padding:40px 0 8px;border-bottom:3px solid var(--mark)}}
header .brandline{{font:700 22px/1.1 "Barlow Condensed",system-ui,sans-serif;margin:0;color:var(--ink)}}
header .brandline .x{{color:var(--mark)}}
header p{{color:var(--muted);margin:6px 0 14px}}
a{{color:var(--steel)}}
.toc{{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}}
.toc a{{background:var(--panel);border:1px solid var(--rule);border-radius:6px;padding:6px 12px;text-decoration:none;color:var(--ink)}}
.figs{{display:flex;flex-wrap:wrap;gap:12px;margin:14px 0}}
.fig{{background:var(--panel);border:1px solid var(--rule);border-radius:8px;padding:10px 16px;min-width:120px}}
.fig b{{display:block;font:600 24px/1.2 "Barlow Condensed",system-ui,sans-serif;color:var(--mark)}}
.fig span{{color:var(--muted);font-size:13px}}
.honesty{{background:var(--sunk);border-inline-start:3px solid var(--mark);border-radius:6px;padding:14px 26px;color:var(--muted);font-size:14px}}
.site{{border-top:1px solid var(--rule);padding:28px 0}}
.site h2{{font:700 28px/1.1 "Barlow Condensed",system-ui,sans-serif;margin:0 0 6px}}
.status{{font:600 13px/1 "IBM Plex Mono",monospace;color:var(--mark-ink);background:var(--mark);border-radius:4px;padding:4px 8px;vertical-align:middle;text-transform:uppercase}}
.purpose{{margin:4px 0}}
.serves{{color:var(--muted);font-size:14px}}
.cols{{display:flex;flex-wrap:wrap;gap:24px;align-items:flex-start}}
.planwrap{{overflow-x:auto;max-width:100%;background:var(--sunk);border:1px solid var(--rule);border-radius:8px;padding:8px}}
.plan .dim{{fill:var(--muted);font:11px "IBM Plex Mono",monospace}}
.plan .item{{fill:var(--panel);stroke:var(--rule)}}
.plan .arrow{{stroke:var(--mark);stroke-width:2}}
.plan .arrow.unverifiable{{stroke-dasharray:4 4;stroke:var(--muted)}}
.plan .num{{fill:var(--mark)}}
.plan .numt{{fill:var(--mark-ink);font:700 11px "IBM Plex Mono",monospace}}
.plan .post circle{{fill:var(--panel);stroke:var(--steel);stroke-width:2}}
.plan .post text{{fill:var(--ink);font:14px system-ui}}
.plan .post .lbl{{font:10px "IBM Plex Mono",monospace;fill:var(--ink)}}
.plan .post .u{{fill:var(--muted)}}
.facts{{flex:1 1 340px;min-width:0}}
.facts h3{{font:600 16px/1.2 "Barlow Condensed",system-ui,sans-serif;margin:16px 0 6px;text-transform:uppercase;letter-spacing:.04em}}
.facts h3 small{{color:var(--muted);text-transform:none;letter-spacing:0;font-weight:400}}
.roles,.gates{{margin:0;padding-inline-start:20px;font-size:14px}}
.roles small{{color:var(--muted)}}
.stop{{margin:0;font-size:14px;border-inline-start:3px solid var(--crit);padding-inline-start:10px}}
.ppe{{margin:0;padding-inline-start:20px;columns:2;font-size:14px}}
.hz{{color:var(--muted);font-size:13px}}
/* a site style (data-style, design_kit.style_css) re-declares the plate and panel, so the status
   colours must follow it too: its own --tc-ok/--tc-warn (set on body only while a style is on),
   else the page's own scheme-aware values (QA wave 4) */
:root{{--pg-good:var(--good);--pg-warn:var(--warn);--pg-crit:var(--crit)}}
body{{--good:var(--tc-ok,var(--pg-good));--warn:var(--tc-warn,var(--pg-warn));--crit:var(--tc-warn,var(--pg-crit))}}
.warn{{color:var(--crit)}}
details{{margin-top:14px}}
summary{{cursor:pointer;color:var(--steel)}}
.sched{{border-collapse:collapse;width:100%;font-size:13px;margin-top:8px}}
.tablewrap{{overflow-x:auto;max-width:100%}}
.sched th,.sched td{{border-top:1px solid var(--rule);padding:4px 8px;text-align:start;vertical-align:top}}
.sched th{{color:var(--muted);font-weight:600}}
.num{{font-variant-numeric:tabular-nums;white-space:nowrap}}
code{{font:13px "IBM Plex Mono",monospace;color:var(--steel)}}
</style>
<style>{NAV_CSS}</style>
<style>{TASKS_CSS}</style>
<style>{HERO_CSS}</style>
</head>
<body>
{NAV}{HERO_HTML}<div class="wrap">
<header>
  <p class="brandline">SmartCiti<span class="x">.X</span> : Trade Craft Academy</p>
  <p>powered by AGI Corp · work sites</p>
</header>
<p class="intro">A work site is a scenario where a crew drawn from at least two unions works one job with hand-offs, and whose completion can be checked offline from the members' own exported records with <code>node worksites/verify.mjs &lt;site-id&gt; &lt;record.json&gt;...</code>. Every site here is an <b data-pack-status>authored scenario</b>.</p>
<div class="figs">
 <div class="fig"><b data-fig="sites">{c["sites"]}</b><span>work sites</span></div>
 <div class="fig"><b data-fig="unions_covered">{c["unions_covered"]}</b><span>unions on a site, of <span data-fig="unions_total">{c["unions_total"]}</span></span></div>
 <div class="fig"><b data-fig="crews_used">{c["crews_used"]}</b><span>crews used, of <span data-fig="crews_total">{c["crews_total"]}</span></span></div>
 <div class="fig"><b data-fig="roles">{c["roles"]}</b><span>roles assigned</span></div>
 <div class="fig"><b data-fig="handoffs">{c["handoffs"]}</b><span>hand-offs</span></div>
 <div class="fig"><b data-fig="handoffs_verifiable">{c["handoffs_verifiable"]}</b><span>verifiable from records</span></div>
 <div class="fig"><b data-fig="handoffs_unverifiable">{c["handoffs_unverifiable"]}</b><span>unverifiable, said so</span></div>
 <div class="fig"><b data-fig="seats_involved">{c["seats_involved"]}</b><span>seats involved</span></div>
 <div class="fig"><b data-tasks-fig="tasks">{len(TASKS_ON_SITES)}</b><span>{esc(S('tasks.title').lower())}</span></div>
</div>
<p class="serves" data-tasks-honesty>{esc(TASK_REG['honesty']['practice'])}</p>
<p class="serves">Places by kind: {places}</p>
<nav class="toc">{toc}</nav>
<ul class="honesty">
<li data-honesty="authored">{esc(reg["honesty"]["authored"])}</li>
<li data-honesty="no_multi_user">{esc(reg["honesty"]["no_multi_user"])}</li>
<li data-honesty="not_a_certification">{esc(reg["honesty"]["not_a_certification"])}</li>
<li data-honesty="unverified">{esc(reg["honesty"]["unverified"])}</li>
<li data-honesty="not_a_permit">{esc(reg["honesty"]["not_a_permit"])}</li>
<li data-honesty="ppe">{esc(reg["honesty"]["ppe"])}</li>
<li data-honesty="not_stated">{esc(reg["honesty"]["not_stated"])}</li>
</ul>
{sections}
<footer class="serves">Registry: <code>worksites/registry/worksites.json</code> · stamp <code data-stamp>{esc(reg["source_stamp"])}</code> · authored <code data-authored-stamp>{esc(reg["authored_stamp"])}</code> · embedded verbatim below.</footer>
<script type="application/json" id="worksites-registry">{embedded}</script>
</div>{TASK_FILTER_JS}<script>{HERO_JS}</script>{QUEST_TAIL}</body>
</html>
'''

out = HERE / 'trade_craft_worksites.html'
page = apply_seo(page, 'web/trade_craft_worksites.html', 'SmartCiti.X : Trade Craft Academy \u2014 work sites',
    'Work sites drawn from the worksites registry: each site plan with its numbered hand-offs between roles, step by step.', 'page')
emit(out, page, f'{c["sites"]} sites | {c["handoffs"]} hand-offs | stamp {reg["source_stamp"]}')
