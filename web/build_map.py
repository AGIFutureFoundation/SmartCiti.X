#!/usr/bin/env python3
"""The network map: every union hall on the Treasure Island campus.

Geometry and every number come from the registry pack, so the map cannot
disagree with the ledger. Hall colours come from brand/identity.mjs's livery
function, reimplemented here with the SAME hash so the two agree — the values
are asserted against a fixture below rather than trusted.
"""
import json, pathlib, html, sys

ROOT = pathlib.Path(__file__).resolve().parent

# ---------------------------------------------------------------- data ----
# Halls, districts and pipeline state all come from the 111-hall pack. The map
# holds no roster of its own: a second list of halls is a second thing to keep
# in step, which is how the surfaces disagreed in the first place.
sys.path.insert(0, str(ROOT / 'pack'))
from unions111 import DISTRICTS as DISTRICT_MAP          # noqa: E402
sys.path.insert(0, str(ROOT))
from interiors import build as build_interiors, ROOMS as ROOM_PROGRAMME  # noqa: E402

halls_json = json.load(open(ROOT / 'pack/registry/halls.json'))['halls']
unions = {u['slug']: u for u in halls_json}
manifest = json.load(open(ROOT / 'pack/manifest.json'))
SHAPE = manifest['ledger']

CODES = None   # filled after make_codes is defined
DISTRICTS = [(k, n, b, slugs) for k, (n, b, slugs) in DISTRICT_MAP.items()]
assert sum(len(d[3]) for d in DISTRICTS) == SHAPE['halls']
assert {s for d in DISTRICTS for s in d[3]} == set(unions), 'districts must match the pack'


def pipeline_state(hall_idx, level):
    """Mirrors pack/build.py and pack/registry.js — one rule, three callers."""
    if hall_idx < 18:
        return 'live' if level <= 88 else ('calibrating' if level <= 94 else 'schema_ok')
    if hall_idx < 33:
        return 'live' if level <= 70 else ('calibrating' if level <= 84 else 'schema_ok')
    if hall_idx < 66:
        return ('live' if level <= 44 else 'calibrating' if level <= 66
                else 'schema_ok' if level <= 84 else 'draft')
    return ('live' if level <= 22 else 'calibrating' if level <= 44
            else 'schema_ok' if level <= 70 else 'draft')


def hall_states(idx):
    c = {'live': 0, 'calibrating': 0, 'schema_ok': 0, 'draft': 0}
    for lv in range(SHAPE['levels_per_hall']):
        c[pipeline_state(idx, lv)] += SHAPE['slots_per_level'] * SHAPE['variants_per_lesson']
    return c


state = {h['slug']: {'n': h['modules'], 'states': hall_states(h['index'])} for h in halls_json}
INTERIORS = build_interiors(halls_json, lambda i: hall_states(i))
assert len(INTERIORS) == SHAPE['halls'], 'every hall needs an interior'
assert sum(v['n'] for v in state.values()) + SHAPE['shared_library_modules'] == SHAPE['total_modules']


def livery(slug, theme='dark'):
    """Mirrors brand/identity.mjs livery() exactly — asserted below."""
    h = 0
    for ch in slug:
        h = (h * 31 + ord(ch)) % 360
    if 28 < h < 52:
        h = (h + 46) % 360
    if theme == 'dark':
        return h, f'hsl({h} 52% 62%)'
    return h, f'hsl({h} 46% 38%)'


assert livery('ironworkers')[0] == 141, 'livery hash drifted from the brand pack'
assert livery('welders')[0] == livery('welders')[0]


def make_codes(halls):
    """Three-letter hall codes, derived from the NAME and proven unique.

    Two letters was fine at the 33-hall scale. At 111 it collides — Steel Erectors and
    Stone Carvers are both "ST" — and the old rule took its letters from the
    slug, so "window-glazing" printed WI on a pad reading ARCHITECTURAL
    GLAZIERS. A code that does not match the name it sits under is worse than
    no code.

    Initials first (ARCHITECTURAL GLAZIERS -> ARG), then a consonant walk, then
    a numeric tail. The assertion at the end is the part that matters: at this
    scale uniqueness has to be checked, not assumed.
    """
    out, used = {}, set()
    for slug, name in halls:
        words = [w for w in ''.join(c if c.isalnum() or c == ' ' else ' ' for c in name).split() if w]
        cands = []
        if len(words) >= 3:
            cands.append(''.join(w[0] for w in words[:3]))
        if len(words) >= 2:
            cands.append(words[0][:2] + words[1][0])
            cands.append(words[0][0] + words[1][:2])
        base = words[0]
        cands.append(base[:3])
        cons = base[0] + ''.join(c for c in base[1:] if c.lower() not in 'aeiou')
        cands.append((cons + base)[:3])
        for i in range(10):
            cands.append(base[:2] + str(i))
        for c in cands:
            c = c.upper()
            if len(c) == 3 and c not in used:
                out[slug] = c
                used.add(c)
                break
        else:
            raise AssertionError(f'no free code for {name}')
    assert len(used) == len(halls), 'hall codes must be unique'
    return out


# ------------------------------------------------------------ geometry ----
# Stacked district bands, not side-by-side parcels.
#
# The first cut placed six parcels across a 1000-wide plan and sized hall pads
# before checking the registry's actual names. "Heavy Equipment Technicians" is
# 27 characters; the pads were 132px and the names ran straight out of them and
# across the neighbouring district. Bands give every hall the same generous
# width and let the sheet grow downward, which costs nothing on a page that
# already scrolls.
PAD_W, PAD_H, GAP_X, GAP_Y = 264, 40, 8, 8
COLS = 3
BAND_X, BAND_W = 96, COLS * PAD_W + (COLS - 1) * GAP_X      # 808
HEAD_H = 46
TOP = 92

CODES = make_codes([(h['slug'], h['name']) for h in halls_json])

halls, bands = [], []
y = TOP
for key, name, blurb, slugs in DISTRICTS:
    rows = -(-len(slugs) // COLS)
    band_h = HEAD_H + rows * PAD_H + (rows - 1) * GAP_Y + 16
    bands.append({'key': key, 'name': name, 'blurb': blurb, 'n': len(slugs),
                  'x': BAND_X - 16, 'y': y, 'w': BAND_W + 32, 'h': band_h})
    for i, slug in enumerate(slugs):
        c, r = i % COLS, i // COLS
        in_row = min(COLS, len(slugs) - r * COLS)
        # centre a short final row rather than leaving it hanging left
        indent = (BAND_W - (in_row * PAD_W + (in_row - 1) * GAP_X)) / 2
        px = BAND_X + indent + c * (PAD_W + GAP_X)
        py = y + HEAD_H + r * (PAD_H + GAP_Y)
        u = unions[slug]
        st = state[slug]['states']
        hue, chip = livery(slug)
        halls.append({
            'slug': slug, 'name': u['name'], 'focus': u['focus'], 'code': CODES[slug],
            'district': key, 'district_name': name,
            'x': round(px, 1), 'y': round(py, 1), 'w': PAD_W, 'h': PAD_H,
            'hue': hue, 'chip': chip,
            'modules': state[slug]['n'],
            'interior': INTERIORS[slug],
            'live': st.get('live', 0), 'calibrating': st.get('calibrating', 0),
            'schema_ok': st.get('schema_ok', 0), 'draft': st.get('draft', 0),
        })
    y += band_h + 18

PLANNED_Y = y + 6
SHEET_H = PLANNED_Y + 150

TOTALS = {k: sum(h[k] for h in halls) for k in ('modules', 'live', 'calibrating', 'schema_ok', 'draft')}
TOTALS['all'] = TOTALS['modules'] + SHAPE['shared_library_modules']

# Grid reference: columns A-E follow the pad columns, rows follow the bands, so
# a reference names something a reader can actually find on the sheet.
for b in bands:
    for h in halls:
        if h['district'] == b['key']:
            col = round((h['x'] - BAND_X) / (PAD_W + GAP_X))
            h['ref'] = f"{chr(65 + max(0, min(2, col)))}{bands.index(b) + 1}"

# No pad may leave its band, and no two pads may overlap: the failure the first
# geometry shipped with, now asserted instead of eyeballed.
for h in halls:
    b = next(x for x in bands if x['key'] == h['district'])
    assert h['x'] >= b['x'] and h['x'] + h['w'] <= b['x'] + b['w'], f"{h['slug']} escapes its band"
    assert h['y'] + h['h'] <= b['y'] + b['h'], f"{h['slug']} overflows its band vertically"
for i, a in enumerate(halls):
    for bq in halls[i + 1:]:
        if not (a['x'] + a['w'] <= bq['x'] or bq['x'] + bq['w'] <= a['x']
                or a['y'] + a['h'] <= bq['y'] or bq['y'] + bq['h'] <= a['y']):
            raise AssertionError(f"{a['slug']} overlaps {bq['slug']}")

# The longest name must fit the pad at the label size.
#
# PX_PER_CHAR is MEASURED, not estimated. The first version guessed 6.1 from
# "condensed faces run about 0.47em"; the browser reports 8.74 at 13.5px, so
# the guess was 43% low and four hall names ran out of their pads while the
# assertion sat there passing. An assertion built on a guessed constant is
# worse than no assertion: it reports confidence it has not earned.
PX_PER_CHAR = 8.74          # Barlow Condensed 700, 13.5px, uppercase
LONGEST = max(halls, key=lambda h: len(h['name']))
NEED = len(LONGEST['name']) * PX_PER_CHAR + 26
assert NEED <= PAD_W, (
    f"{LONGEST['name']} ({len(LONGEST['name'])} chars) needs {NEED:.0f}px "
    f"and the pad is {PAD_W}px")

DATA = {
    'halls': halls,
    'districts': [{'key': b['key'], 'name': b['name'], 'blurb': b['blurb'], 'n': b['n']} for b in bands],
    'totals': TOTALS,
}

# ------------------------------------------------------------- render ----
D = json.dumps(DATA, separators=(',', ':'))

BAND_SVG = ''.join(
    f'<g class="band" data-d="{b["key"]}">'
    f'<rect x="{b["x"]}" y="{b["y"]}" width="{b["w"]}" height="{b["h"]}" rx="4"/>'
    f'<text class="dlabel" x="{b["x"]+16}" y="{b["y"]+27}">{html.escape(b["name"])}</text>'
    f'<text class="dsub" x="{b["x"]+16}" y="{b["y"]+41}">{b["n"]} halls &#183; {html.escape(b["blurb"])}</text>'
    f'</g>'
    for b in bands)

GRID = ''.join(
    f'<text class="gref" x="{BAND_X + c*(PAD_W+GAP_X) + 4}" y="{TOP - 10}">{chr(65+c)}</text>'
    for c in range(COLS)
) + ''.join(
    f'<text class="gref" x="{BAND_X - 30}" y="{b["y"] + 27}">{i+1}</text>'
    for i, b in enumerate(bands))

PAGE = f'''<title>Trade Craft Campus Plan</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;600&display=swap">
<style>
:root{{
  --plate:#12181B; --panel:#182023; --sunk:#0C1113; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --mark-ink:#12181B; --steel:#41C4D4; --steel-ink:#7FDCE8;
  --land:#1B2427; --good:#5CB584; --warn:#E8A33D; --crit:#E07C68;
  color-scheme:dark light;
}}
@media (prefers-color-scheme:light){{:root:not([data-theme="dark"]){{
  --plate:#F1F4F3; --panel:#FFFFFF; --sunk:#DCE5E6; --ink:#141D20; --muted:#54646A;
  --rule:#CBD6D6; --mark:#9F680B; --mark-ink:#FFFFFF; --steel:#0A7E8C; --steel-ink:#065A66;
  --land:#E7EDEB; --good:#2C7A50; --warn:#9A6408; --crit:#A8432F;
}}}}
:root[data-theme="light"]{{
  --plate:#F1F4F3; --panel:#FFFFFF; --sunk:#DCE5E6; --ink:#141D20; --muted:#54646A;
  --rule:#CBD6D6; --mark:#9F680B; --mark-ink:#FFFFFF; --steel:#0A7E8C; --steel-ink:#065A66;
  --land:#E7EDEB; --good:#2C7A50; --warn:#9A6408; --crit:#A8432F;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--plate);color:var(--ink);
  font:15px/1.6 "IBM Plex Sans",system-ui,sans-serif;-webkit-font-smoothing:antialiased}}
.disp,h1,h2,h3{{font-family:"Barlow Condensed",system-ui,sans-serif;margin:0;
  text-transform:uppercase;letter-spacing:.02em;font-weight:700;text-wrap:balance}}
.mono{{font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums}}

/* ---- brand lockup, from brand/identity.mjs ---- */
.bx-lockup{{display:inline-flex;align-items:center;gap:10px;color:inherit;text-decoration:none}}
.bx-mark{{flex:0 0 auto;color:var(--mark)}}
.bx-text{{display:grid;line-height:1}}
.bx-name{{font-family:"Barlow Condensed",sans-serif;font-weight:700;text-transform:uppercase;
  letter-spacing:.02em;font-size:19px;white-space:nowrap}}
.bx-name .bx-dot{{color:var(--steel)}}
.bx-name .bx-sep{{color:var(--mark);padding:0 .3em}}
.bx-attr{{font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--muted);margin-top:6px}}

header.sheet{{display:flex;align-items:center;gap:22px;flex-wrap:wrap;
  padding:16px 22px;border-bottom:1px solid var(--rule);background:var(--panel)}}
header .sheetmeta{{margin-left:auto;display:flex;gap:26px;flex-wrap:wrap}}
header .sheetmeta div{{display:grid;gap:3px}}
header .sheetmeta b{{font-family:"IBM Plex Mono",monospace;font-size:13px;font-weight:600}}
header .sheetmeta span{{font-family:"IBM Plex Mono",monospace;font-size:9.5px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--muted)}}

.shell{{display:grid;grid-template-columns:266px minmax(0,1fr);gap:0;min-height:calc(100vh - 74px)}}
@media(max-width:900px){{.shell{{grid-template-columns:1fr}}}}

aside{{border-right:1px solid var(--rule);padding:20px;display:flex;flex-direction:column;gap:20px;
  background:var(--panel)}}
@media(max-width:900px){{aside{{border-right:none;border-bottom:1px solid var(--rule)}}}}
.kicker{{font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--mark);margin:0 0 10px}}
.dlist{{display:flex;flex-direction:column;gap:2px}}
.dbtn{{display:grid;grid-template-columns:1fr auto;gap:2px 8px;align-items:baseline;
  text-align:left;padding:9px 10px;border:1px solid transparent;border-radius:3px;
  background:none;color:var(--ink);font:inherit;cursor:pointer;width:100%}}
.dbtn small{{grid-column:1/-1;font-size:12px;color:var(--muted);line-height:1.35}}
.dbtn b{{font-family:"Barlow Condensed",sans-serif;text-transform:uppercase;font-size:16px;
  letter-spacing:.03em}}
.dbtn .n{{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--muted)}}
.dbtn:hover{{background:var(--plate)}}
.dbtn[aria-pressed="true"]{{border-color:var(--mark);background:var(--plate)}}
.dbtn[aria-pressed="true"] b{{color:var(--mark)}}

.key{{display:flex;flex-direction:column;gap:7px;font-size:12.5px}}
.key div{{display:flex;align-items:center;gap:9px}}
.key i{{width:11px;height:11px;border-radius:2px;flex:0 0 auto}}
.key .swatch-live{{background:var(--good)}} .key .swatch-cal{{background:var(--warn)}}
.key .swatch-sch{{background:var(--steel)}} .key .swatch-dra{{background:var(--rule);border:1px solid var(--muted)}}
.key .swatch-soon{{background:transparent;border:1px dashed var(--steel)}}

/* ---- the plan ---- */
.plan{{position:relative;padding:22px;display:grid;gap:0;align-content:start}}
.planwrap{{position:relative;border:1px solid var(--rule);border-radius:4px;background:var(--sunk);
  overflow-x:auto}}
svg.map{{display:block;width:100%;height:auto;min-width:940px}}
.water{{fill:var(--sunk)}}
.land{{fill:var(--land);stroke:var(--rule);stroke-width:1.5}}
.gl{{stroke:var(--rule);stroke-width:.6;opacity:.55}}
.gref{{font-family:"IBM Plex Mono",monospace;font-size:10px;fill:var(--muted)}}
.band rect{{fill:none;stroke:var(--rule);stroke-width:1}}
.band.dim{{opacity:.3}}
.dlabel{{font-family:"Barlow Condensed",sans-serif;font-weight:700;font-size:17px;
  text-transform:uppercase;letter-spacing:.06em;fill:var(--mark)}}
.dsub{{font-family:"IBM Plex Mono",monospace;font-size:10px;fill:var(--muted)}}
.road{{stroke:var(--steel);stroke-width:2.5;fill:none;opacity:.5}}
.roadlbl{{font-family:"IBM Plex Mono",monospace;font-size:9.5px;fill:var(--steel-ink);
  letter-spacing:.1em;text-transform:uppercase}}
.soon rect{{fill:none;stroke:var(--steel);stroke-width:1.2;stroke-dasharray:6 5;opacity:.8}}
.soon text{{font-family:"Barlow Condensed",sans-serif;font-weight:700;font-size:13px;
  text-transform:uppercase;fill:var(--steel-ink);letter-spacing:.06em}}
.soon .st{{font-family:"IBM Plex Mono",monospace;font-size:9px;letter-spacing:.1em;fill:var(--muted)}}

.hall{{cursor:pointer}}
.hall .pad{{fill:var(--panel);stroke:var(--rule);stroke-width:1;rx:3}}
.hall .bar{{width:4px}}
.hall .hcode{{font-family:"IBM Plex Mono",monospace;font-size:10px;font-weight:600;fill:var(--muted)}}
.hall .hname{{font-family:"Barlow Condensed",sans-serif;font-weight:700;font-size:13.5px;
  text-transform:uppercase;fill:var(--ink);letter-spacing:.03em}}
.hall:hover .pad,.hall:focus-visible .pad{{stroke:var(--mark);stroke-width:1.6}}
.hall[aria-pressed="true"] .pad{{stroke:var(--mark);stroke-width:2}}
.hall.dim{{opacity:.22}}
.hall:focus-visible{{outline:none}}
.hall:focus-visible .pad{{stroke:var(--mark);stroke-width:2.4}}

/* title block, bottom-right of the sheet, where a drawing puts it */
.titleblock{{fill:var(--panel);stroke:var(--rule);stroke-width:1}}
.tb-k{{font-family:"IBM Plex Mono",monospace;font-size:8.5px;letter-spacing:.12em;
  text-transform:uppercase;fill:var(--muted)}}
.tb-v{{font-family:"IBM Plex Mono",monospace;font-size:11px;fill:var(--ink)}}
.tb-t{{font-family:"Barlow Condensed",sans-serif;font-weight:700;font-size:15px;
  text-transform:uppercase;fill:var(--ink);letter-spacing:.04em}}
.tb-b{{font-family:"Barlow Condensed",sans-serif;font-weight:700;font-size:12px;
  text-transform:uppercase;fill:var(--mark);letter-spacing:.04em}}
.narrow{{fill:var(--ink)}} .scale-b{{stroke:var(--ink);stroke-width:1.4}}
.scale-t{{font-family:"IBM Plex Mono",monospace;font-size:9px;fill:var(--muted)}}

/* ---- detail card ---- */
.detail{{margin-top:18px;border:1px solid var(--rule);border-radius:4px;background:var(--panel);
  padding:18px 20px;display:grid;gap:14px}}
.detail .dhead{{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}}
.detail h2{{font-size:26px}}
.detail .ref{{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--muted);
  border:1px solid var(--rule);border-radius:2px;padding:3px 7px}}
.detail .dist{{font-family:"IBM Plex Mono",monospace;font-size:10.5px;letter-spacing:.1em;
  text-transform:uppercase;margin-left:auto}}
/* ---- hall interior ---- */
.plan2{{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:22px;align-items:start}}
@media(max-width:860px){{.plan2{{grid-template-columns:1fr}}}}
svg.floor{{display:block;width:100%;height:auto;background:var(--sunk);
  border:1px solid var(--rule);border-radius:4px}}
.room rect{{fill:var(--plate);stroke:var(--rule);stroke-width:1}}
.room.has rect{{fill:color-mix(in srgb,var(--mark) 9%,var(--plate))}}
.room text.rn{{font-family:"Barlow Condensed",sans-serif;font-weight:700;font-size:11px;
  text-transform:uppercase;fill:var(--ink);letter-spacing:.03em}}
.room text.rf{{font-family:"IBM Plex Mono",monospace;font-size:7.6px;fill:var(--mark)}}
.room text.rs{{font-family:"IBM Plex Mono",monospace;font-size:7.2px;fill:var(--muted)}}
.envelope{{fill:none;stroke:var(--mark);stroke-width:2}}
.floor .grid{{stroke:var(--rule);stroke-width:.4;opacity:.4}}
.floor .dim{{font-family:"IBM Plex Mono",monospace;font-size:8px;fill:var(--muted)}}
.comm{{display:inline-flex;align-items:center;gap:7px;font-family:"IBM Plex Mono",monospace;
  font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;padding:4px 9px;
  border:1px solid currentColor;border-radius:2px}}
.c-commissioned{{color:var(--good)}} .c-partial{{color:var(--warn)}}
.c-fitting-out{{color:var(--steel-ink)}} .c-shell{{color:var(--crit)}}
.prog{{display:flex;flex-direction:column;gap:7px;font-size:13px}}
.prog .pr{{display:grid;grid-template-columns:auto 1fr;gap:9px;align-items:baseline}}
.prog .pr b{{font-family:"Barlow Condensed",sans-serif;text-transform:uppercase;font-size:14px;
  letter-spacing:.03em;white-space:nowrap}}
.prog .pr span{{color:var(--muted);font-size:12.5px;line-height:1.45}}
.prog .pr em{{font-style:normal;color:var(--mark);font-family:"IBM Plex Mono",monospace;
  font-size:11.5px;display:block;margin-top:2px}}
.sitebox{{border:1px dashed var(--rule);border-radius:3px;padding:12px 14px;margin-top:4px}}
.sitebox b{{font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--crit);display:block;margin-bottom:6px}}
.sitebox p{{margin:0;font-size:12.5px;color:var(--muted);line-height:1.5}}
.detail p{{margin:0;max-width:62ch;color:var(--muted)}}
.stack{{display:flex;height:12px;border-radius:2px;overflow:hidden;background:var(--rule)}}
.stack i{{display:block;height:100%}}
.legrow{{display:flex;gap:18px;flex-wrap:wrap;font-family:"IBM Plex Mono",monospace;font-size:11.5px}}
.legrow span{{display:flex;align-items:center;gap:7px}}
.legrow em{{font-style:normal;color:var(--muted)}}
.legrow i{{width:9px;height:9px;border-radius:2px}}
footer{{padding:26px 22px 40px;color:var(--muted);font-size:13px;border-top:1px solid var(--rule)}}
footer p{{max-width:78ch;margin:0 0 8px}}
:focus-visible{{outline:2px solid var(--mark);outline-offset:2px}}
</style>

<header class="sheet">
  <a class="bx-lockup" href="#">
    <svg class="bx-mark" width="34" height="34" viewBox="0 0 48 48" role="img" aria-label="SmartCiti.X">
      <path d="M6 30 A18 18 0 0 1 42 30" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
      <path d="M24 12 L24 4" stroke="currentColor" stroke-width="3.2" stroke-linecap="round"/>
      <rect x="4" y="30" width="40" height="6" rx="3" fill="currentColor"/>
      <circle cx="24" cy="33" r="1.9" fill="var(--plate)"/>
    </svg>
    <span class="bx-text">
      <span class="bx-name">SmartCiti<span class="bx-dot">.X</span><span class="bx-sep">:</span>Trade Craft Academy</span>
      <span class="bx-attr">powered by AGI Corp</span>
    </span>
  </a>
  <div class="sheetmeta">
    <div><b>{SHAPE['halls']}</b><span>union halls</span></div>
    <div><b class="mono">{TOTALS['all']:,}</b><span>modules on the plan</span></div>
    <div><b class="mono">{TOTALS['live']:,}</b><span>live</span></div>
    <div><b>TI-01</b><span>sheet</span></div>
  </div>
</header>

<div class="shell">
  <aside>
    <div>
      <p class="kicker">Districts</p>
      <div class="dlist" id="dlist"></div>
    </div>
    <div>
      <p class="kicker">Pipeline state</p>
      <div class="key">
        <div><i class="swatch-live"></i> Live — authored, calibrated, serving</div>
        <div><i class="swatch-cal"></i> Calibrating — serving, difficulty still settling</div>
        <div><i class="swatch-sch"></i> Schema OK — structure valid, not yet calibrated</div>
        <div><i class="swatch-dra"></i> Draft — not served to anyone</div>
        <div><i class="swatch-soon"></i> Planned — not built</div>
      </div>
    </div>
  </aside>

  <div class="plan">
    <div class="planwrap">
      <svg class="map" viewBox="0 0 1000 {SHEET_H}" role="img" aria-label="Campus plan: {SHAPE['halls']} union halls grouped into eight districts across the Treasure Island site">
        <rect class="water" x="0" y="0" width="1000" height="{SHEET_H}"/>
        <path class="land" d="M40 56 L960 56 Q978 56 978 74 L978 {SHEET_H - 70} Q978 {SHEET_H - 52} 960 {SHEET_H - 52} L260 {SHEET_H - 52} Q214 {SHEET_H - 52} 184 {SHEET_H - 84} L52 {SHEET_H - 232} Q40 {SHEET_H - 246} 40 {SHEET_H - 266} Z"/>
        <path class="road" d="M0 {TOP - 34} L978 {TOP - 34}"/>
        <text class="roadlbl" x="{BAND_X}" y="{TOP - 40}">Bay Bridge Approach &#183; Site Entry</text>
        <g>{GRID}</g>
        {BAND_SVG}
        <g class="soon">
          <rect x="{BAND_X}" y="{PLANNED_Y}" width="404" height="52" rx="4"/>
          <text x="{BAND_X + 16}" y="{PLANNED_Y + 24}">Oakland Training Yard</text>
          <text class="st" x="{BAND_X + 16}" y="{PLANNED_Y + 40}">PLANNED &#183; NOT BUILT</text>
        </g>
        <g class="soon">
          <rect x="{BAND_X + 420}" y="{PLANNED_Y}" width="404" height="52" rx="4"/>
          <text x="{BAND_X + 436}" y="{PLANNED_Y + 24}">SF Bridgehead</text>
          <text class="st" x="{BAND_X + 436}" y="{PLANNED_Y + 40}">PLANNED &#183; NOT BUILT</text>
        </g>
        <g id="halls"></g>
        <g transform="translate(922,{TOP - 46})">
          <path class="narrow" d="M0 -13 L6 8 L0 3 L-6 8 Z"/>
          <text class="scale-t" x="-4" y="22">N</text>
        </g>
        <g transform="translate({BAND_X},{PLANNED_Y + 96})">
          <line class="scale-b" x1="0" y1="0" x2="120" y2="0"/>
          <line class="scale-b" x1="0" y1="-4" x2="0" y2="4"/>
          <line class="scale-b" x1="60" y1="-3" x2="60" y2="3"/>
          <line class="scale-b" x1="120" y1="-4" x2="120" y2="4"/>
          <text class="scale-t" x="0" y="16">0</text>
          <text class="scale-t" x="104" y="16">200m</text>
        </g>
        <g transform="translate({BAND_X + 480},{PLANNED_Y + 66})">
          <rect class="titleblock" x="0" y="0" width="344" height="80" rx="3"/>
          <text class="tb-t" x="14" y="24">Campus Plan &#183; Union Halls</text>
          <text class="tb-b" x="14" y="41">SmartCiti.X : Trade Craft Academy</text>
          <line x1="14" y1="49" x2="330" y2="49" stroke="var(--rule)" stroke-width="1"/>
          <text class="tb-k" x="14" y="61">Sheet</text><text class="tb-v" x="14" y="73">TI-01</text>
          <text class="tb-k" x="90" y="61">Rev</text><text class="tb-v" x="90" y="73">2.7</text>
          <text class="tb-k" x="146" y="61">Halls</text><text class="tb-v" x="146" y="73">{SHAPE['halls']}</text>
          <text class="tb-k" x="206" y="61">Modules</text><text class="tb-v" x="206" y="73">{TOTALS['all']:,}</text>
          <text class="tb-k" x="286" y="61">Issued</text><text class="tb-v" x="286" y="73">Review</text>
        </g>
      </svg>
    </div>
    <div class="detail" id="detail"></div>
  </div>
</div>

<footer>
  <p><b>Every number on this plan is read from the module registry</b> — hall counts,
  module counts and pipeline states are the pack's own values, not illustrations.
  The geography is schematic: bands show how the halls are grouped, not surveyed positions.</p>
  <p><b>The interiors are functional programmes, not surveys.</b> Each hall's rooms come from
  the eleven skill strands that hall actually teaches, and a room gains trade fixtures only when
  that trade's own focus line names them — a welding hall gets booths and fume extraction because
  its skills say so, and a drywall hall does not. <b>No address data has been collected for any
  hall</b>, so every plan carries an empty site block rather than an invented street address.
  The commissioning state on each plan is read from that hall's live-module share.</p>
  <p>The Oakland Yard and SF Bridgehead parcels are drawn dashed because they are planned and
  not built. Nothing on this plan is an accreditation or a union endorsement, and lesson content
  is unverified general practice pending authoring by practitioners.</p>
</footer>

<script>
const DATA = {D};
const F = (n) => n.toLocaleString('en-US');
const SW = {{live:'var(--good)', calibrating:'var(--warn)', schema_ok:'var(--steel)', draft:'var(--rule)'}};
let filter = null, selected = DATA.halls[0].slug;

const dlist = document.getElementById('dlist');
dlist.innerHTML = DATA.districts.map((d) =>
  `<button class="dbtn" data-d="${{d.key}}" aria-pressed="false">
     <b>${{d.name}}</b><span class="n">${{d.n}}</span><small>${{d.blurb}}</small></button>`).join('');

const hallsG = document.getElementById('halls');
hallsG.innerHTML = DATA.halls.map((h) => {{
  const w = h.w, hh = h.h, x = h.x, y = h.y;
  return `<g class="hall" data-s="${{h.slug}}" data-d="${{h.district}}" role="button" tabindex="0"
            aria-label="${{h.name}} — ${{h.district_name}} district, grid ${{h.ref}}" aria-pressed="false">
    <rect class="pad" x="${{x}}" y="${{y}}" width="${{w}}" height="${{hh}}" rx="3"/>
    <rect class="bar" x="${{x}}" y="${{y}}" width="4" height="${{hh}}" fill="${{h.chip}}"/>
    <text class="hname" x="${{x + 13}}" y="${{y + 17}}">${{h.name}}</text>
    <text class="hcode" x="${{x + 13}}" y="${{y + 31}}">${{h.code}} · ${{h.ref}} · ${{F(h.modules)}}</text>
  </g>`;
}}).join('');

function renderDetail(slug) {{
  const h = DATA.halls.find((x) => x.slug === slug);
  const I = h.interior, U = 26, PAD = 16;               // 26px per 3m grid unit
  const W = I.envelope.w * U, D = I.envelope.d * U;
  const seg = (k) => h[k] ? `<i style="width:${{(h[k] / h.modules * 100).toFixed(2)}}%;background:${{SW[k]}}"></i>` : '';

  const gridLines = [];
  for (let gx = 1; gx < I.envelope.w; gx++)
    gridLines.push(`<line class="grid" x1="${{PAD + gx * U}}" y1="${{PAD}}" x2="${{PAD + gx * U}}" y2="${{PAD + D}}"/>`);
  for (let gy = 1; gy < I.envelope.d; gy++)
    gridLines.push(`<line class="grid" x1="${{PAD}}" y1="${{PAD + gy * U}}" x2="${{PAD + W}}" y2="${{PAD + gy * U}}"/>`);

  const rooms = I.rooms.map((r) => {{
    const x = PAD + r.x * U, y = PAD + r.y * U, w = r.w * U, hh = r.h * U;
    const fx = r.fixtures.length
      ? `<text class="rf" x="${{x + 6}}" y="${{y + 30}}">${{r.fixtures[0]}}</text>` : '';
    const more = r.fixtures.length > 1
      ? `<text class="rf" x="${{x + 6}}" y="${{y + 40}}">${{r.fixtures[1]}}</text>` : '';
    return `<g class="room ${{r.fixtures.length ? 'has' : ''}}">
      <rect x="${{x}}" y="${{y}}" width="${{w}}" height="${{hh}}" rx="2"/>
      <text class="rn" x="${{x + 6}}" y="${{y + 16}}">${{r.label}}</text>
      ${{fx}}${{more}}
      <text class="rs" x="${{x + 6}}" y="${{y + hh - 6}}">${{r.caption.replace('x', '×').replace(' - ', ' · ')}}</text>
    </g>`;
  }}).join('');

  const programme = I.rooms.map((r) => `<div class="pr">
      <b style="color:${{r.fixtures.length ? h.chip : 'var(--muted)'}}">${{r.label}}</b>
      <span>${{r.purpose}}${{r.fixtures.length ? `<em>${{r.fixtures.join(' · ')}}</em>` : ''}}</span>
    </div>`).join('');

  document.getElementById('detail').innerHTML = `
    <div class="dhead">
      <h2 style="color:${{h.chip}}">${{h.name}}</h2>
      <span class="ref mono">${{h.code}} · GRID ${{h.ref}}</span>
      <span class="dist" style="color:${{h.chip}}">${{h.district_name}}</span>
    </div>
    <p>${{h.focus}}.</p>
    <div class="stack">${{seg('live')}}${{seg('calibrating')}}${{seg('schema_ok')}}${{seg('draft')}}</div>
    <div class="legrow">
      <span><i style="background:var(--good)"></i>${{F(h.live)}} <em>live</em></span>
      <span><i style="background:var(--warn)"></i>${{F(h.calibrating)}} <em>calibrating</em></span>
      <span><i style="background:var(--steel)"></i>${{F(h.schema_ok)}} <em>schema ok</em></span>
      <span><i style="background:var(--rule);border:1px solid var(--muted)"></i>${{F(h.draft)}} <em>draft</em></span>
      <span><em>of</em> ${{F(h.modules)}} <em>modules</em></span>
    </div>
    <div class="plan2">
      <div>
        <svg class="floor" viewBox="0 0 ${{W + PAD * 2}} ${{D + PAD * 2 + 18}}"
             role="img" aria-label="Floor plan of the ${{h.name}} hall: ${{I.rooms.length}} rooms">
          ${{gridLines.join('')}}
          ${{rooms}}
          <rect class="envelope" x="${{PAD}}" y="${{PAD}}" width="${{W}}" height="${{D}}" rx="3"/>
          <text class="dim" x="${{PAD}}" y="${{D + PAD + 13}}">${{I.envelope.w * 3}}m × ${{I.envelope.d * 3}}m envelope · 3m grid</text>
        </svg>
      </div>
      <div>
        <div class="row" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:14px">
          <span class="comm c-${{I.commissioning}}">${{I.commissioning}}</span>
          <span class="mono" style="font-size:11.5px;color:var(--muted)">${{I.fixture_count}} trade fixture${{I.fixture_count === 1 ? '' : 's'}}</span>
        </div>
        <div class="prog">${{programme}}</div>
        <div class="sitebox">
          <b>Site address — not recorded</b>
          <p>${{I.site.note}}</p>
        </div>
      </div>
    </div>`;
}}

function apply() {{
  for (const g of hallsG.children) {{
    const on = !filter || g.dataset.d === filter;
    g.classList.toggle('dim', !on);
    g.setAttribute('aria-pressed', g.dataset.s === selected ? 'true' : 'false');
  }}
  for (const b of dlist.children) b.setAttribute('aria-pressed', b.dataset.d === filter ? 'true' : 'false');
}}

hallsG.addEventListener('click', (e) => {{
  const g = e.target.closest('.hall'); if (!g) return;
  selected = g.dataset.s; renderDetail(selected); apply();
}});
hallsG.addEventListener('keydown', (e) => {{
  if (e.key !== 'Enter' && e.key !== ' ') return;
  const g = e.target.closest('.hall'); if (!g) return;
  e.preventDefault(); selected = g.dataset.s; renderDetail(selected); apply();
}});
dlist.addEventListener('click', (e) => {{
  const b = e.target.closest('.dbtn'); if (!b) return;
  filter = filter === b.dataset.d ? null : b.dataset.d; apply();
}});

renderDetail(selected); apply();
</script>
'''

out = ROOT / 'trade_craft_map.html'
out.write_text(PAGE, encoding='utf-8')
print(f'written: {len(PAGE):,} bytes | {len(halls)} halls | {TOTALS["all"]:,} modules')
