#!/usr/bin/env python3
"""The network's union halls, drawn by district — not one campus.

Until this file, the plan called itself a single Treasure Island site, drew
Oakland — a real, built, 32-hall campus — as a dashed `PLANNED . NOT BUILT`
parcel, and folded all ten campuses' halls into that one place. The network
grew to ten built campuses (unions/registry/campuses.json) before this page
did; the framing is fixed here rather than carried forward again.

Geometry and every number come from the registry pack, so the map cannot
disagree with the ledger. Each district's campus attribution is read from
unions/registry/campuses.json (built campuses only — a campus that owns no
district has no halls to draw here), so this page cannot itself misstate
which campus a district belongs to, and brand/figures.mjs's built-campus
rule catches any surface, this one included, that calls a built campus
planned. Hall colours come from brand/identity.mjs's livery function,
reimplemented here with the SAME hash so the two agree — the values are
asserted against a fixture below rather than trusted.
"""
import json, pathlib, html, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent


def _pack_root():
    """The directory that holds the packs, found by walking up rather than
    trusting the working directory or a fixed layout — the earlier fixed
    `ROOT / 'pack'` only resolved in the pre-packaging tree (defect 13's
    shape), so the packaged bundle could not rebuild its own map."""
    for cand in (ROOT, *ROOT.parents):
        if (cand / 'pack').is_dir() and (cand / 'unions').is_dir():
            return cand
    raise RuntimeError('cannot locate the packs from ' + str(ROOT))


PACKS = _pack_root()

# Same rule, same reason as build_landing.py and build_languages.py: this
# page's chrome comes from the source catalog rather than being retyped as
# Python literals, and i18n/validate.mjs (catalog.mjs's own rule, run once,
# not re-typed per builder) fails this build on a bad catalog too.
_v = subprocess.run(['node', str(PACKS / 'i18n/validate.mjs')], capture_output=True, text=True)
if _v.returncode != 0:
    sys.stderr.write(_v.stdout + _v.stderr)
    sys.exit(1)

_EN_DOC = json.loads((PACKS / 'i18n/locales/en.json').read_text(encoding='utf-8'))
_EN = _EN_DOC['strings']


def S(key):
    """Look up a source-catalog string by its dotted key. Strict, like
    catalog.mjs's t(): a missing key fails the build rather than rendering
    blank."""
    if key not in _EN:
        raise KeyError(f'i18n: no en value for {key}')
    return _EN[key]


def STATE(key):
    """Look up a pipeline-state label (en.json's top-level `states` section,
    not the flat `strings` dict — reused here rather than retyped)."""
    return _EN_DOC['states'][key]

# ---------------------------------------------------------------- data ----
# Halls and pipeline state come from the module pack; districts come from the
# union registry, which is now its own pack. The map holds no roster of its
# own: a second list of halls is a second thing to keep in step, which is how
# the surfaces disagreed in the first place.
sys.path.insert(0, str(ROOT))
from interiors import build as build_interiors, ROOMS as ROOM_PROGRAMME  # noqa: E402
from mapdata import make_codes, HUES as SHARED_HUES  # noqa: E402
from staleness import emit  # noqa: E402
from seo import apply_seo  # noqa: E402  head tags only
from sitenav import nav_html, labels as nav_labels, NAV_CSS  # noqa: E402

_districts_json = json.load(open(PACKS / 'unions/registry/districts.json'))['districts']
DISTRICT_MAP = {k: (d['name'], d['tagline'], d['halls'])
                for k, d in _districts_json.items()}

halls_json = json.load(open(PACKS / 'pack/registry/halls.json'))['halls']
unions = {u['slug']: u for u in halls_json}
manifest = json.load(open(PACKS / 'pack/manifest.json'))
SHAPE = manifest['ledger']

# Campus attribution, read from the registry rather than assumed: a campus
# with no districts is a roadmap hub campus (a chapter seat, no halls of its
# own — roadmap/registry/roadmap.json), so it contributes nothing here.
_campuses_json = json.load(open(PACKS / 'unions/registry/campuses.json'))['campuses']
DISTRICT_CAMPUS = {dk: c['name']
                   for c in _campuses_json.values() for dk in c['districts']}
CAMPUS_NAMES = sorted({c['name'] for c in _campuses_json.values() if c['districts']})

CODES = None   # filled after make_codes is defined
DISTRICTS = [(k, n, b, slugs) for k, (n, b, slugs) in DISTRICT_MAP.items()]
assert sum(len(d[3]) for d in DISTRICTS) == SHAPE['halls']
assert {s for d in DISTRICTS for s in d[3]} == set(unions), 'districts must match the pack'
assert set(DISTRICT_CAMPUS) == set(DISTRICT_MAP), 'every drawn district needs a built campus'


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
    campus = DISTRICT_CAMPUS[key]
    rows = -(-len(slugs) // COLS)
    band_h = HEAD_H + rows * PAD_H + (rows - 1) * GAP_Y + 16
    bands.append({'key': key, 'name': name, 'blurb': blurb, 'n': len(slugs),
                  'campus': campus,
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
            'district': key, 'district_name': name, 'campus': campus,
            'x': round(px, 1), 'y': round(py, 1), 'w': PAD_W, 'h': PAD_H,
            'hue': hue, 'chip': chip,
            'modules': state[slug]['n'],
            'interior': INTERIORS[slug],
            'live': st.get('live', 0), 'calibrating': st.get('calibrating', 0),
            'schema_ok': st.get('schema_ok', 0), 'draft': st.get('draft', 0),
        })
    y += band_h + 18

# No "planned, not built" band: the roadmap is ten of ten built campuses and
# zero candidates (roadmap/registry/roadmap.json — target met, not exceeded),
# so there is nothing left on this network to draw as unbuilt. What follows
# is a plain footer strip for the scale bar and the title block.
FOOT_Y = y + 6
SHEET_H = FOOT_Y + 100

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

# ------------------------------------------------------ training depth ----
# What training stands in each hall, read from the registry that owns each
# fact and carried onto the page VERBATIM (the whole document, no per-hall
# preprocessing - the same contract lessons.json#page_contract.data states).
# Per-hall and legend counts are computed by the page at render from that
# payload, and cross-checked here against each registry's own published
# count, so a number on the map can only ever be the registry's number.
def need(obj, key, where):
    """§23.1: a missing field fails the build by NAME - no default, no
    `.get`, so a registry that drops a field breaks this build loudly."""
    if not isinstance(obj, dict):
        raise KeyError(f'{where} is not an object, cannot read {key!r}')
    if key not in obj:
        raise KeyError(f'{where} has no field {key!r}')
    return obj[key]


SOURCES = {
    'halls': 'pack/registry/halls.json',
    'lessons': 'lessons/registry/lessons.json',
    'sims': 'sims/registry/sims.json',
    'schools': 'schools/registry/schools.json',
    'completion': 'completion/registry/completion.json',
}
REG = {k: json.loads((PACKS / rel).read_text(encoding='utf-8')) for k, rel in SOURCES.items()}
assert REG['halls']['halls'] == halls_json, 'the hall registry read twice must agree'

_LR = SOURCES['lessons']
LESSONS = need(REG['lessons'], 'lessons', _LR)
LESSON_HALLS = set()
for lid, L in LESSONS.items():
    w = f'{_LR}#lessons.{lid}'
    if need(L, 'id', w) != lid:
        raise KeyError(f'{w} is keyed {lid!r} but carries id {L["id"]!r}')
    hall = need(L, 'hall', w)
    if hall not in unions:
        raise KeyError(f'{w} stands in {hall!r}, which pack/registry/halls.json does not list')
    need(L, 'title', w)
    if not need(L, 'steps', w):
        raise KeyError(f'{w} carries no steps')
    LESSON_HALLS.add(hall)
_LC = need(REG['lessons'], 'counts', _LR)
if need(_LC, 'halls_covered', f'{_LR}#counts') != len(LESSON_HALLS):
    raise KeyError(f'{_LR}#counts.halls_covered disagrees with the lessons it lists')
if need(_LC, 'halls_total', f'{_LR}#counts') != SHAPE['halls']:
    raise KeyError(f'{_LR}#counts.halls_total disagrees with the pack ledger')
EDGES = need(need(REG['lessons'], 'ladder', _LR), 'edges', f'{_LR}#ladder')
for i, e in enumerate(EDGES):
    w = f'{_LR}#ladder.edges[{i}]'
    for k in ('lesson', 'needs', 'because'):
        if need(e, k, w) not in LESSONS and k != 'because':
            raise KeyError(f'{w}.{k} names {e[k]!r}, which is not a lesson')
if need(_LC, 'prerequisite_edges', f'{_LR}#counts') != len(EDGES):
    raise KeyError(f'{_LR}#counts.prerequisite_edges disagrees with #ladder.edges')

_SR = SOURCES['sims']
SIMS = need(REG['sims'], 'sims', _SR)
BINDINGS = need(REG['sims'], 'hall_bindings', _SR)
for slug, bs in BINDINGS.items():
    w = f'{_SR}#hall_bindings.{slug}'
    if slug not in unions:
        raise KeyError(f'{w} binds a seat to a hall the pack does not list')
    if not bs:
        raise KeyError(f'{w} is an empty binding list')
    for j, b in enumerate(bs):
        sim = need(b, 'sim', f'{w}[{j}]')
        need(b, 'skill_id', f'{w}[{j}]')
        need(need(SIMS, sim, f'{_SR}#sims'), 'name', f'{_SR}#sims.{sim}')
_SC = need(need(REG['sims'], 'coverage', _SR), 'halls', f'{_SR}#coverage')
if need(_SC, 'with_a_seat', f'{_SR}#coverage.halls') != len(BINDINGS):
    raise KeyError(f'{_SR}#coverage.halls.with_a_seat disagrees with #hall_bindings')
if need(_SC, 'total', f'{_SR}#coverage.halls') != SHAPE['halls']:
    raise KeyError(f'{_SR}#coverage.halls.total disagrees with the pack ledger')

_HR = SOURCES['schools']
UNITS = need(REG['schools'], 'units', _HR)
_unit_halls = []
for i, u in enumerate(UNITS):
    w = f'{_HR}#units[{i}]'
    hall = need(u, 'hall', w)
    if hall not in unions:
        raise KeyError(f'{w} stands in {hall!r}, which the pack does not list')
    for k in ('class_stations', 'class_drill', 'floor_sims', 'gate', 'home'):
        need(u, k, w)
    for s in u['floor_sims']:
        if s not in SIMS:
            raise KeyError(f'{w}.floor_sims names {s!r}, which {_SR}#sims does not hold')
    _unit_halls.append(hall)
if len(set(_unit_halls)) != len(_unit_halls):
    raise KeyError(f'{_HR}#units lists a hall twice')

_CR = SOURCES['completion']
COMPLETION = need(REG['completion'], 'lessons', _CR)
if set(COMPLETION) != set(LESSONS):
    raise KeyError(f'{_CR}#lessons and {_LR}#lessons do not name the same lessons')
_completable = 0
for lid, c in COMPLETION.items():
    w = f'{_CR}#lessons.{lid}'
    if need(c, 'hall', w) != LESSONS[lid]['hall']:
        raise KeyError(f'{w}.hall disagrees with {_LR}#lessons.{lid}.hall')
    if need(c, 'steps', w) != len(LESSONS[lid]['steps']):
        raise KeyError(f'{w}.steps disagrees with {_LR}#lessons.{lid}.steps')
    ok_ = need(c, 'completable', w)
    why = need(c, 'not_completable_why', w)
    if ok_ is not (why is None):
        raise KeyError(f'{w}: completable and not_completable_why contradict each other')
    need(c, 'needs', w)
    _completable += 1 if ok_ else 0
_CC = need(REG['completion'], 'counts', _CR)
if need(_CC, 'lessons_completable', f'{_CR}#counts') != _completable:
    raise KeyError(f'{_CR}#counts.lessons_completable disagrees with #lessons')
if need(_CC, 'lessons_not_completable', f'{_CR}#counts') != len(COMPLETION) - _completable:
    raise KeyError(f'{_CR}#counts.lessons_not_completable disagrees with #lessons')
if need(_CC, 'ladder_edges', f'{_CR}#counts') != len(EDGES):
    raise KeyError(f'{_CR}#counts.ladder_edges disagrees with {_LR}#ladder.edges')


def signed_off_halls():
    """Per-hall practitioner sign-off, through the module that owns the
    rule (pack/hall_signoff.mjs) - exactly as bundles/build.py reads it.
    Counting `content_status` strings here would be a second opinion about
    what a sign-off is."""
    script = (
        "const hs = await import('./pack/hall_signoff.mjs');"
        "const halls = JSON.parse(require('fs')"
        f"  .readFileSync('{SOURCES['halls']}','utf8')).halls;"
        "const per = {};"
        "for (const h of halls) per[h.slug] = hs.claimsHallSignoff(h.content_status);"
        "console.log(JSON.stringify({"
        "  halls: per,"
        "  signed: Object.values(per).filter(Boolean).length,"
        "  of: halls.length,"
        "  statuses: hs.HALL_CONTENT_STATUSES,"
        "  claiming: hs.HALL_CONTENT_STATUSES.filter((s) => hs.claimsHallSignoff(s)) }));")
    proc = subprocess.run(
        ['node', '--input-type=module', '-e',
         "import { createRequire } from 'node:module';"
         "const require = createRequire(process.cwd() + '/x.js');" + script],
        cwd=str(PACKS), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError('cannot read pack/hall_signoff.mjs through node:\n' + proc.stderr.strip())
    return json.loads(proc.stdout)


SIGNOFF = signed_off_halls()
if need(SIGNOFF, 'of', 'pack/hall_signoff.mjs') != SHAPE['halls']:
    raise KeyError('pack/hall_signoff.mjs counted a different number of halls than the ledger')
if len(need(SIGNOFF, 'claiming', 'pack/hall_signoff.mjs')) != 1:
    raise KeyError('pack/hall_signoff.mjs must name exactly one claiming status')
SIGNOFF['claiming'] = SIGNOFF['claiming'][0]
SIGNOFF['rule'] = 'pack/hall_signoff.mjs'
SIGNOFF['caveat'] = need(need(manifest, 'honesty', 'pack/manifest.json'), 'content', 'pack/manifest.json#honesty')

# Every deep link the hall panel offers must resolve to a page in web/. The
# parameter shapes are the target pages' own: ?hall=<slug> is what
# build_3d.py, build_ladder.py and build_progress.py read, and
# #lesson-<id> is the anchor build_lessons.py writes per lesson.
LINKS = {'3d': 'trade_craft_3d.html', 'lessons': 'trade_craft_lessons.html',
         'ladder': 'trade_craft_ladder.html', 'progress': 'trade_craft_progress.html'}
for k, f in LINKS.items():
    if not (ROOT / f).is_file():
        raise FileNotFoundError(f'hall panel link {k} -> web/{f} does not exist')

DATA = {    'halls': halls,
    'districts': [{'key': b['key'], 'name': b['name'], 'blurb': b['blurb'],
                   'n': b['n'], 'campus': b['campus']} for b in bands],
    'totals': TOTALS,
    'campusNames': CAMPUS_NAMES,
    'sources': SOURCES,
    'reg': REG,
    'signoff': SIGNOFF,
    'links': LINKS,
}

# ------------------------------------------------------------- render ----
D = json.dumps(DATA, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/')

BAND_SVG = ''.join(
    f'<g class="band" data-d="{b["key"]}">'
    f'<rect x="{b["x"]}" y="{b["y"]}" width="{b["w"]}" height="{b["h"]}" rx="4"/>'
    f'<text class="dlabel" x="{b["x"]+16}" y="{b["y"]+27}">{html.escape(b["name"])}</text>'
    f'<text class="dsub" x="{b["x"]+16}" y="{b["y"]+41}">{b["n"]} halls &#183; '
    f'{html.escape(b["campus"])} &#183; {html.escape(b["blurb"])}</text>'
    f'</g>'
    for b in bands)

GRID = ''.join(
    f'<text class="gref" x="{BAND_X + c*(PAD_W+GAP_X) + 4}" y="{TOP - 10}">{chr(65+c)}</text>'
    for c in range(COLS)
) + ''.join(
    f'<text class="gref" x="{BAND_X - 30}" y="{b["y"] + 27}">{i+1}</text>'
    for i, b in enumerate(bands))

NAV = nav_html('web/trade_craft_map.html', nav_labels('en'))
from questkit import QUEST_CSS, quest_js, page_hooks  # noqa: E402  quests: egg hooks only (body tail)
QUEST_TAIL = '<style>' + QUEST_CSS + '</style>\n' + page_hooks('web/trade_craft_map.html') + quest_js('page:web/trade_craft_map.html')

PAGE = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Trade Craft {S('map.page_title')}</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' stroke='%23E8A33D' stroke-width='2.6' stroke-linejoin='round'/%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E">
<!-- Self-hosted: nothing on this page is fetched from another origin at run time. See web/fetch_fonts.py. -->
<link rel="stylesheet" href="vendor/fonts/fonts.css">
<style>
.vh{{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}}
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
header .sheetmeta{{margin-inline-start:auto;display:flex;gap:26px;flex-wrap:wrap}}
header .sheetmeta div{{display:grid;gap:3px}}
header .sheetmeta b{{font-family:"IBM Plex Mono",monospace;font-size:13px;font-weight:600}}
header .sheetmeta span{{font-family:"IBM Plex Mono",monospace;font-size:9.5px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--muted)}}

.shell{{display:grid;grid-template-columns:266px minmax(0,1fr);gap:0;min-height:calc(100vh - 74px)}}
@media(max-width:900px){{.shell{{grid-template-columns:minmax(0,1fr)}}}}

aside{{border-inline-end:1px solid var(--rule);padding:20px;display:flex;flex-direction:column;gap:20px;
  background:var(--panel)}}
@media(max-width:900px){{aside{{border-inline-end:none;border-bottom:1px solid var(--rule)}}}}
.kicker{{font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--mark);margin:0 0 10px}}
.dlist{{display:flex;flex-direction:column;gap:2px}}
.dbtn{{display:grid;grid-template-columns:1fr auto;gap:2px 8px;align-items:baseline;
  text-align:start;padding:9px 10px;border:1px solid transparent;border-radius:3px;
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

/* ---- the plan ---- */
.plan{{position:relative;padding:22px;display:grid;grid-template-columns:minmax(0,1fr);gap:0;align-content:start}}
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
  padding:18px 20px;display:grid;grid-template-columns:minmax(0,1fr);gap:14px}}
.detail .dhead{{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}}
.detail h2{{font-size:26px}}
/* the district colour is a swatch and a rule, never the text colour: the
   light hues fail contrast as text on the light theme's panel */
.detail h2.dname{{color:var(--ink);border-inline-start:6px solid var(--rule);padding-inline-start:10px}}
.detail .dist .dsw{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-inline-end:6px;vertical-align:-1px}}
.detail .ref{{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--muted);
  border:1px solid var(--rule);border-radius:2px;padding:3px 7px}}
.detail .dist{{font-family:"IBM Plex Mono",monospace;font-size:10.5px;letter-spacing:.1em;
  text-transform:uppercase;margin-inline-start:auto;overflow-wrap:anywhere;min-width:0}}
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
/* ---- training layers ---- */
.layers{{display:flex;flex-direction:column;gap:6px;font-size:12px}}
.layers label{{display:grid;grid-template-columns:auto 11px 1fr auto;gap:8px;align-items:center;cursor:pointer}}
.layers label i{{width:11px;height:11px;border-radius:50%;flex:0 0 auto}}
.layers label code{{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:10px;color:var(--muted);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.layers label .lname{{display:grid;gap:1px;line-height:1.2}}
.layers label .lc{{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:11px;white-space:nowrap}}
.layers label[data-focus="true"] code{{color:var(--mark)}}
.layers .lfocus{{border:1px solid var(--rule);background:none;color:var(--muted);font:inherit;font-size:10px;
  border-radius:2px;padding:1px 8px;cursor:pointer;grid-column:2/-1;justify-self:start;min-height:24px;min-width:24px}}
.layers .lfocus[aria-pressed="true"]{{border-color:var(--mark);color:var(--mark)}}
.hall .lm{{stroke:var(--sunk);stroke-width:.8}}
svg.map[data-off~="lessons"] .lm[data-layer="lessons"],svg.map[data-off~="seats"] .lm[data-layer="seats"],
svg.map[data-off~="units"] .lm[data-layer="units"],svg.map[data-off~="signoff"] .lm[data-layer="signoff"],
svg.map[data-off~="completable"] .lm[data-layer="completable"],svg.map[data-off~="blocked"] .lm[data-layer="blocked"]{{display:none}}
.hallpanel{{border-top:1px solid var(--rule);padding-top:14px;display:grid;gap:12px}}
.hallpanel .hp-links{{display:flex;flex-wrap:wrap;gap:6px 14px;min-width:0}}
.hallpanel .hp-links a,.hallpanel .hp-row a{{overflow-wrap:anywhere}}
.hallpanel a{{color:var(--steel);text-decoration:none;font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:11.5px}}
.hallpanel a:hover{{text-decoration:underline}}
.hallpanel .hp-row{{display:grid;grid-template-columns:auto minmax(0,1fr);gap:6px 12px;align-items:baseline;font-size:12.5px}}
.hallpanel .hp-row>.hp-k{{display:grid;gap:2px;line-height:1.2}}
.hallpanel .hp-row code{{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:10px;color:var(--muted);white-space:nowrap}}
.hallpanel .hp-row>div{{display:grid;gap:5px;min-width:0}}
.hallpanel .hp-row .lc,.hallpanel .hp-row em,.hallpanel .hp-row a{{overflow-wrap:anywhere;min-width:0}}
.hallpanel .hp-row .lc{{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:11px}}
.hallpanel .hp-row em{{font-style:normal;color:var(--muted);font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:10.5px;display:block}}
.hallpanel .hp-row .none{{color:var(--muted);font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:11px}}
.hallpanel .hp-row .yes{{color:var(--good)}} .hallpanel .hp-row .no{{color:var(--crit)}}
.hallpanel .caveat{{font-size:12px;color:var(--muted);border:1px dashed var(--rule);border-radius:3px;padding:8px 10px;margin:0}}
footer{{padding:26px 22px 40px;color:var(--muted);font-size:13px;border-top:1px solid var(--rule)}}
footer p{{max-width:78ch;margin:0 0 8px}}
.sheetnav{{display:flex;flex-wrap:wrap;gap:6px 16px;padding:8px 22px;
  border-bottom:1px solid var(--rule);background:var(--panel)}}
.sheetnav a{{color:var(--steel);text-decoration:none;font-size:12px;
  font-family:"IBM Plex Mono",monospace;letter-spacing:.04em}}
.sheetnav a:hover{{text-decoration:underline}}
:focus-visible{{outline:2px solid var(--mark);outline-offset:2px}}
</style>
<style>{NAV_CSS}</style>
{NAV}
<h1 class="vh">{S('map.page_title')}</h1>
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
    <div><b>{SHAPE['halls']}</b><span>{S('map.meta.halls')}</span></div>
    <div><b class="mono">{TOTALS['all']:,}</b><span>{S('map.meta.modules')}</span></div>
    <div><b class="mono">{TOTALS['live']:,}</b><span>{S('map.meta.live')}</span></div>
    <div><b>NET-01</b><span>{S('map.meta.sheet')}</span></div>
  </div>
</header>
<nav class="sheetnav" aria-label="{S('map.nav.aria')}">
  <a href="trade_craft_3d.html">⬡ {S('map.nav.3d')}</a>
  <a href="trade_craft_interactive.html">▦ {S('map.nav.interactive')}</a>
  <a href="trade_craft_geomap.html">🌐 {S('map.nav.geomap')}</a>
  <a href="trade_craft_dashboard.html">📊 {S('map.nav.dashboard')}</a>
  <a href="../wiki/Home.md">📖 {S('map.nav.wiki')}</a>
</nav>

<div class="shell">
  <aside>
    <div>
      <p class="kicker">{S('map.layer.districts')}</p>
      <div class="dlist" id="dlist"></div>
    </div>
    <div>
      <p class="kicker">{S('map.layer.pipeline')}</p>
      <div class="key">
        <div><i class="swatch-live"></i> {S('map.key.live')}</div>
        <div><i class="swatch-cal"></i> {S('map.key.calibrating')}</div>
        <div><i class="swatch-sch"></i> {S('map.key.schema_ok')}</div>
        <div><i class="swatch-dra"></i> {S('map.key.draft')}</div>
      </div>
    </div>
    <div>
      <p class="kicker">{S('map.layers')} &#183; {S('map.layer.stations')}</p>
      <div class="layers" id="layers"></div>
    </div>
  </aside>

  <div class="plan">
    <div class="planwrap">
      <svg class="map" viewBox="0 0 1000 {SHEET_H}" role="img" aria-label="{S('map.aria.plan').format(n=SHAPE['halls'], c=len(CAMPUS_NAMES))}">
        <rect class="water" x="0" y="0" width="1000" height="{SHEET_H}"/>
        <path class="land" d="M40 56 L960 56 Q978 56 978 74 L978 {SHEET_H - 70} Q978 {SHEET_H - 52} 960 {SHEET_H - 52} L260 {SHEET_H - 52} Q214 {SHEET_H - 52} 184 {SHEET_H - 84} L52 {SHEET_H - 232} Q40 {SHEET_H - 246} 40 {SHEET_H - 266} Z"/>
        <path class="road" d="M0 {TOP - 34} L978 {TOP - 34}"/>
        <text class="roadlbl" x="{BAND_X}" y="{TOP - 40}">{S('map.entry_road')}</text>
        <g>{GRID}</g>
        {BAND_SVG}
        <g id="halls"></g>
        <g transform="translate(922,{TOP - 46})">
          <path class="narrow" d="M0 -13 L6 8 L0 3 L-6 8 Z"/>
          <text class="scale-t" x="-4" y="22">N</text>
        </g>
        <g transform="translate({BAND_X},{FOOT_Y + 30})">
          <line class="scale-b" x1="0" y1="0" x2="120" y2="0"/>
          <line class="scale-b" x1="0" y1="-4" x2="0" y2="4"/>
          <line class="scale-b" x1="60" y1="-3" x2="60" y2="3"/>
          <line class="scale-b" x1="120" y1="-4" x2="120" y2="4"/>
          <text class="scale-t" x="0" y="16">0</text>
          <text class="scale-t" x="104" y="16">200m</text>
        </g>
        <g transform="translate({BAND_X + 480},{FOOT_Y})">
          <rect class="titleblock" x="0" y="0" width="344" height="80" rx="3"/>
          <text class="tb-t" x="14" y="24">{S('map.titleblock.title')}</text>
          <text class="tb-b" x="14" y="41">SmartCiti.X : Trade Craft Academy</text>
          <line x1="14" y1="49" x2="330" y2="49" stroke="var(--rule)" stroke-width="1"/>
          <text class="tb-k" x="14" y="61">{S('map.titleblock.sheet')}</text><text class="tb-v" x="14" y="73">NET-01</text>
          <text class="tb-k" x="90" y="61">{S('map.titleblock.rev')}</text><text class="tb-v" x="90" y="73">3.0</text>
          <text class="tb-k" x="146" y="61">{S('map.titleblock.halls')}</text><text class="tb-v" x="146" y="73">{SHAPE['halls']}</text>
          <text class="tb-k" x="206" y="61">{S('map.titleblock.modules')}</text><text class="tb-v" x="206" y="73">{TOTALS['all']:,}</text>
          <text class="tb-k" x="286" y="61">{S('map.titleblock.issued')}</text><text class="tb-v" x="286" y="73">{S('map.titleblock.review')}</text>
        </g>
      </svg>
    </div>
    <div class="detail" id="detail"></div>
  </div>
</div>

<footer>
  <p>{S('map.footer.p1')}</p>
  <p>{S('map.footer.p2')}</p>
  <p>{S('map.footer.p3')}</p>
</footer>

<script id="data" type="application/json">{D}</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const REG = DATA.reg;
const hasOwn = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
// The i18n catalog's own strings, carried in as data rather than retyped:
// layerLabels: the six training layers' prose labels, shown beside (never
// instead of) the registry field path each layer is read from.
// the {{token}} placeholders are filled below, the same contract i18n/test.mjs
// enforces server-side (placeholder survival) for every locale of this key.
const I18N = {json.dumps({
    'ariaHall': S('map.aria.hall'), 'ariaFloor': S('map.aria.floor'),
    'noAddress': S('map.detail.no_address'), 'of': S('map.detail.of'),
    'modulesWord': S('map.detail.modules_word'), 'fixture': S('map.detail.fixture'),
    'layers': S('map.layers'), 'nav3d': S('map.nav.3d'), 'hallsWord': S('map.meta.halls'),
    'layerLabels': {
        'lessons': S('map.layer.lessons'), 'seats': S('map.layer.seats'),
        'units': S('map.layer.units'), 'signoff': S('map.layer.signoff'),
        'completable': S('map.layer.completable'), 'blocked': S('map.layer.blocked'),
    },
    'states': {
        'live': STATE('live'), 'calibrating': STATE('calibrating'),
        'schema_ok': STATE('schema_ok'), 'draft': STATE('draft'),
    },
}, ensure_ascii=False)};
const fillTokens = (s, vars) => Object.entries(vars).reduce((acc, [k, v]) => acc.split(`{{${{k}}}}`).join(v), s);
const F = (n) => n.toLocaleString('en-US');
const SW = {{live:'var(--good)', calibrating:'var(--warn)', schema_ok:'var(--steel)', draft:'var(--rule)'}};
let filter = null, selected = DATA.halls[0].slug;

// Training layers. Every count here is COMPUTED from the verbatim registry
// payload above - nothing is typed - and each is held to the owning
// the published count of the owning registry; a disagreement throws rather than draws.
const LAYERS = {{
  lessons: {{ src: DATA.sources.lessons + '#lessons', sw: 'var(--mark)', by: 'halls', label: I18N.layerLabels.lessons,
    of: (h) => Object.values(REG.lessons.lessons).filter((l) => l.hall === h.slug).map((l) => l.id),
    published: () => REG.lessons.counts.halls_covered }},
  seats: {{ src: DATA.sources.sims + '#hall_bindings', sw: 'var(--steel)', by: 'halls', label: I18N.layerLabels.seats,
    of: (h) => hasOwn(REG.sims.hall_bindings, h.slug) ? REG.sims.hall_bindings[h.slug].map((b) => b.sim) : [],
    published: () => REG.sims.coverage.halls.with_a_seat }},
  units: {{ src: DATA.sources.schools + '#units', sw: 'var(--good)', by: 'halls', label: I18N.layerLabels.units,
    of: (h) => REG.schools.units.filter((u) => u.hall === h.slug).map((u) => u.class_drill),
    published: () => REG.schools.units.length }},
  signoff: {{ src: DATA.signoff.rule, sw: 'var(--crit)', by: 'halls', label: I18N.layerLabels.signoff,
    of: (h) => DATA.signoff.halls[h.slug] === true ? [DATA.signoff.claiming] : [],
    published: () => DATA.signoff.signed }},
  completable: {{ src: DATA.sources.completion + '#lessons.completable', sw: 'var(--steel-ink)', by: 'items', label: I18N.layerLabels.completable,
    of: (h) => Object.entries(REG.completion.lessons).filter(([, c]) => c.hall === h.slug && c.completable === true).map(([id]) => id),
    published: () => REG.completion.counts.lessons_completable }},
  blocked: {{ src: DATA.sources.completion + '#lessons.not_completable_why', sw: 'var(--warn)', by: 'items', label: I18N.layerLabels.blocked,
    of: (h) => Object.entries(REG.completion.lessons).filter(([, c]) => c.hall === h.slug && c.completable === false).map(([id]) => id),
    published: () => REG.completion.counts.lessons_not_completable }},
}};
const COUNTS = {{}};
for (const [k, L] of Object.entries(LAYERS)) {{
  const rows = DATA.halls.map((h) => L.of(h).length);
  const halls = rows.filter((n) => n > 0).length, items = rows.reduce((a, b) => a + b, 0);
  const got = L.by === 'halls' ? halls : items;
  if (got !== L.published()) throw new Error(k + ': computed ' + got + ' != published ' + L.published() + ' @ ' + L.src);
  COUNTS[k] = {{ halls, items }};
}}
if (COUNTS.signoff.halls !== Object.values(DATA.signoff.halls).filter((v) => v === true).length)
  throw new Error('signoff: layer != ' + DATA.signoff.rule);
const off = new Set();
let focus = null;
const layersEl = document.getElementById('layers');
layersEl.innerHTML = Object.entries(LAYERS).map(([k, L]) => `<label data-layer="${{k}}">
    <input type="checkbox" data-toggle="${{k}}" checked>
    <i style="background:${{L.sw}}"></i>
    <span class="lname">${{L.label}}<code title="${{L.src}}">${{L.src}}</code></span>
    <span class="lc" data-count="${{k}}">${{F(COUNTS[k].halls)}} ${{I18N.of}} ${{F(DATA.halls.length)}}${{L.by === 'items' ? ' · ' + F(COUNTS[k].items) : ''}}</span>
    <button class="lfocus" data-focus="${{k}}" aria-pressed="false">${{L.label}}</button>
  </label>`).join('');

const dlist = document.getElementById('dlist');
dlist.innerHTML = DATA.districts.map((d) =>
  `<button class="dbtn" data-d="${{d.key}}" aria-pressed="false">
     <b>${{d.name}}</b><span class="n">${{d.n}}</span>
     <small>${{d.campus}} &#183; ${{d.blurb}}</small></button>`).join('');

const hallsG = document.getElementById('halls');
hallsG.innerHTML = DATA.halls.map((h) => {{
  const w = h.w, hh = h.h, x = h.x, y = h.y;
  const marks = Object.entries(LAYERS).map(([k, L]) => `data-${{k}}="${{L.of(h).length}}"`).join(' ');
  return `<g class="hall" data-s="${{h.slug}}" data-d="${{h.district}}" ${{marks}} role="button" tabindex="0"
            aria-label="${{fillTokens(I18N.ariaHall, {{name: h.name, district: h.district_name, ref: h.ref}})}}" aria-pressed="false">
    <rect class="pad" x="${{x}}" y="${{y}}" width="${{w}}" height="${{hh}}" rx="3"/>
    <rect class="bar" x="${{x}}" y="${{y}}" width="4" height="${{hh}}" fill="${{h.chip}}"/>
    <text class="hname" x="${{x + 13}}" y="${{y + 17}}">${{h.name}}</text>
    <text class="hcode" x="${{x + 13}}" y="${{y + 31}}">${{h.code}} · ${{h.ref}} · ${{F(h.modules)}}</text>
    ${{Object.entries(LAYERS).map(([k, L], i) => L.of(h).length
      ? `<circle class="lm" data-layer="${{k}}" cx="${{x + w - 12 - i * 11}}" cy="${{y + hh - 11}}" r="3.6" fill="${{L.sw}}"><title>${{L.src}}</title></circle>` : '').join('')}}
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
      <b style="${{r.fixtures.length ? `color:var(--ink);box-shadow:inset 0 -3px 0 ${{h.chip}}` : 'color:var(--muted)'}}">${{r.label}}</b>
      <span>${{r.purpose}}${{r.fixtures.length ? `<em>${{r.fixtures.join(' · ')}}</em>` : ''}}</span>
    </div>`).join('');

  document.getElementById('detail').innerHTML = `
    <div class="dhead">
      <h2 class="dname" style="border-inline-start-color:${{h.chip}}">${{h.name}}</h2>
      <span class="ref mono">${{h.code}} · GRID ${{h.ref}}</span>
      <span class="dist"><i class="dsw" style="background:${{h.chip}}"></i>${{h.district_name}} &#183; ${{h.campus}}</span>
    </div>
    <p>${{h.focus}}.</p>
    <div class="stack">${{seg('live')}}${{seg('calibrating')}}${{seg('schema_ok')}}${{seg('draft')}}</div>
    <div class="legrow">
      <span><i style="background:var(--good)"></i>${{F(h.live)}} <em>${{I18N.states.live.toLowerCase()}}</em></span>
      <span><i style="background:var(--warn)"></i>${{F(h.calibrating)}} <em>${{I18N.states.calibrating.toLowerCase()}}</em></span>
      <span><i style="background:var(--steel)"></i>${{F(h.schema_ok)}} <em>${{I18N.states.schema_ok.toLowerCase()}}</em></span>
      <span><i style="background:var(--rule);border:1px solid var(--muted)"></i>${{F(h.draft)}} <em>${{I18N.states.draft.toLowerCase()}}</em></span>
      <span><em>${{I18N.of}}</em> ${{F(h.modules)}} <em>${{I18N.modulesWord}}</em></span>
    </div>
    <div class="plan2">
      <div>
        <svg class="floor" viewBox="0 0 ${{W + PAD * 2}} ${{D + PAD * 2 + 18}}"
             role="img" aria-label="${{fillTokens(I18N.ariaFloor, {{name: h.name, n: I.rooms.length}})}}">
          ${{gridLines.join('')}}
          ${{rooms}}
          <rect class="envelope" x="${{PAD}}" y="${{PAD}}" width="${{W}}" height="${{D}}" rx="3"/>
          <text class="dim" x="${{PAD}}" y="${{D + PAD + 13}}">${{I.envelope.w * 3}}m × ${{I.envelope.d * 3}}m envelope · 3m grid</text>
        </svg>
      </div>
      <div>
        <div class="row" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:14px">
          <span class="comm c-${{I.commissioning}}">${{I.commissioning}}</span>
          <span class="mono" style="font-size:11.5px;color:var(--muted)">${{I.fixture_count}} ${{I18N.fixture}}${{I.fixture_count === 1 ? '' : 's'}}</span>
        </div>
        <div class="prog">${{programme}}</div>
        <div class="sitebox">
          <b>${{I18N.noAddress}}</b>
          <p>${{I.site.note}}</p>
        </div>
      </div>
    </div>
    ${{hallPanel(h)}}`;
}}

/* The hall panel: what training stands in this hall, every line read from
   the registry payload by field name, with a deep link into the page that
   owns it. Labels are the field names of the registries, so a reader can
   follow each line back to its source. */
function hallPanel(h) {{
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
  const lessons = LAYERS.lessons.of(h).map((id) => {{
    const L = REG.lessons.lessons[id], C = REG.completion.lessons[id];
    const pre = REG.lessons.ladder.edges.filter((e) => e.lesson === id);
    return `<div data-lesson="${{id}}" data-completable="${{C.completable}}">
      <a href="${{DATA.links.lessons}}#lesson-${{id}}">${{esc(L.title)}}</a>
      <span class="lc">steps: ${{L.steps.length}} · strand: ${{esc(L.strand)}} · tier: ${{esc(L.tier)}}</span>
      ${{pre.map((e) => `<em data-needs="${{e.needs}}">needs: ${{e.needs}} (${{esc(e.because)}})</em>`).join('')}}
      ${{C.completable === true ? `<em class="yes">completable: true</em>`
        : `<em class="no">not_completable_why: ${{esc(C.not_completable_why)}}</em>`}}
    </div>`;
  }});
  const seats = LAYERS.seats.of(h).map((sim, i) => `<span class="lc" data-seat="${{sim}}">${{esc(REG.sims.sims[sim].name)}}
      <em>${{sim}} · ${{esc(REG.sims.hall_bindings[h.slug][i].skill_id)}}</em></span>`);
  const units = REG.schools.units.filter((u) => u.hall === h.slug).map((u) => `<span class="lc" data-unit="${{esc(u.class_drill)}}">
      class_drill: ${{esc(u.class_drill)}} · floor_sims: ${{u.floor_sims.join(', ')}} · class_stations: ${{u.class_stations.length}}
      <em>gate: ${{esc(u.gate)}}</em><em>home: ${{esc(u.home)}}</em></span>`);
  const signed = DATA.signoff.halls[h.slug] === true;
  const row = (k, body) => `<div class="hp-row" data-panel="${{k}}"><span class="hp-k">${{LAYERS[k].label}}<code>${{LAYERS[k].src}}</code></span>
      <div>${{body.length ? body.join('') : `<span class="none">0</span>`}}</div></div>`;
  return `<section class="hallpanel" data-hall-panel="${{h.slug}}">
    <p class="kicker">${{I18N.layers}} &#183; ${{h.name}}</p>
    <div class="hp-links">
      <a href="${{DATA.links['3d']}}?hall=${{h.slug}}">⬡ ${{I18N.nav3d}}</a>
      <a href="${{DATA.links.lessons}}">${{DATA.links.lessons}}</a>
      <a href="${{DATA.links.ladder}}?hall=${{h.slug}}">${{DATA.links.ladder}}?hall=${{h.slug}}</a>
      <a href="${{DATA.links.progress}}?hall=${{h.slug}}">${{DATA.links.progress}}?hall=${{h.slug}}</a>
    </div>
    ${{row('lessons', lessons)}}
    ${{row('seats', seats)}}
    ${{row('units', units)}}
    <div class="hp-row" data-panel="signoff" data-signed="${{signed}}"><span class="hp-k">${{I18N.layerLabels.signoff}}<code>${{DATA.signoff.rule}}</code></span>
      <div><span class="lc ${{signed ? 'yes' : 'no'}}">${{signed ? DATA.signoff.claiming : DATA.signoff.statuses[0]}}
        <em>${{F(DATA.signoff.signed)}} ${{I18N.of}} ${{F(DATA.signoff.of)}} ${{I18N.hallsWord}}</em></span></div></div>
    <p class="caveat">${{esc(DATA.signoff.caveat)}}</p>
  </section>`;
}}

function apply() {{
  document.querySelector('svg.map').dataset.off = [...off].join(' ');
  for (const g of hallsG.children) {{
    const on = (!filter || g.dataset.d === filter) && (!focus || g.dataset[focus] !== '0');
    g.classList.toggle('dim', !on);
    g.setAttribute('aria-pressed', g.dataset.s === selected ? 'true' : 'false');
  }}
  for (const b of dlist.children) b.setAttribute('aria-pressed', b.dataset.d === filter ? 'true' : 'false');
}}

/* the panel a hall opens lies far below the plan on most screens: a click that
   only fills it looks like a click that did nothing, so bring it into view and
   put focus on it (a keyboard or screen-reader user lands where the content is) */
const detailEl = document.getElementById('detail');
detailEl.setAttribute('tabindex', '-1');
function showDetail() {{
  detailEl.scrollIntoView({{ block: 'start' }});
  detailEl.focus({{ preventScroll: true }});
}}
hallsG.addEventListener('click', (e) => {{
  const g = e.target.closest('.hall'); if (!g) return;
  selected = g.dataset.s; renderDetail(selected); apply(); showDetail();
}});
hallsG.addEventListener('keydown', (e) => {{
  if (e.key !== 'Enter' && e.key !== ' ') return;
  const g = e.target.closest('.hall'); if (!g) return;
  e.preventDefault(); selected = g.dataset.s; renderDetail(selected); apply(); showDetail();
}});
layersEl.addEventListener('change', (e) => {{
  const t = e.target.closest('[data-toggle]'); if (!t) return;
  if (t.checked) off.delete(t.dataset.toggle); else off.add(t.dataset.toggle); apply();
}});
layersEl.addEventListener('click', (e) => {{
  const b = e.target.closest('[data-focus]'); if (!b) return;
  e.preventDefault(); focus = focus === b.dataset.focus ? null : b.dataset.focus;
  for (const x of layersEl.querySelectorAll('[data-focus]')) x.setAttribute('aria-pressed', x.dataset.focus === focus ? 'true' : 'false');
  apply();
}});
dlist.addEventListener('click', (e) => {{
  const b = e.target.closest('.dbtn'); if (!b) return;
  filter = filter === b.dataset.d ? null : b.dataset.d; apply();
}});

renderDetail(selected); apply();
</script>
''' + QUEST_TAIL

out = ROOT / 'trade_craft_map.html'
PAGE = apply_seo(PAGE, 'web/trade_craft_map.html', 'Network plan \u2014 SmartCiti.X : Trade Craft Academy',
    S('seo.desc.map'), 'page')
emit(out, PAGE, f'{len(halls)} halls | {TOTALS["all"]:,} modules', encoding='utf-8')
