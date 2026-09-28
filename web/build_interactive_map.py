#!/usr/bin/env python3
"""The interactive campus map: every registry, one surface, layered.

Renders web/trade_craft_interactive.html — a self-contained page with:

  - the 111 halls tiled by district, with four toggleable layers
    (district hue, pipeline state, module layers, training stations);
  - a detail panel per hall: its figures, level census, generated floor
    plan (the same room geometry the interiors pack asserts), its skill
    lattice, and — where the recovered station content seeds it — the
    stations drawn inside the rooms their strands own;
  - the full i18n catalog set, so the whole surface renders in any of the
    shipped locales, direction-aware.

Everything is read from the registries: the union roster, the module
manifest, the hall files, the skill graph, the station registry, the
interiors geometry and the locale catalogs. The page holds no data of its
own, so it cannot disagree with any of them.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def _pack_root():
    for cand in (HERE, *HERE.parents):
        if (cand / 'pack').is_dir() and (cand / 'unions').is_dir():
            return cand
    raise RuntimeError('cannot locate the packs from ' + str(HERE))


ROOT = _pack_root()
sys.path.insert(0, str(ROOT / 'web'))
from interiors import build as build_interiors  # noqa: E402
from mapdata import strand_modules, PIPELINE_JS, HUES, make_codes  # noqa: E402
from staleness import emit  # noqa: E402
from seo import apply_seo  # noqa: E402  head tags only
from sitenav import nav_html, labels as nav_labels, NAV_CSS  # noqa: E402

manifest = json.load(open(ROOT / 'pack/manifest.json'))
L = manifest['ledger']
halls_json = json.load(open(ROOT / 'pack/registry/halls.json'))['halls']
districts_reg = json.load(open(ROOT / 'unions/registry/districts.json'))['districts']
campuses_reg = json.load(open(ROOT / 'unions/registry/campuses.json'))['campuses']
stations_reg = json.load(open(ROOT / 'stations/registry/stations.json'))
tools_reg = json.load(open(ROOT / 'tools/registry/toolcribs.json'))
# The other three per-hall facts the 3D app's hall header shows and this
# panel didn't: a simulator seat (sims/), a Schools flipped unit (schools/),
# and the regional chapter seats every hall holds (unions/). No walkability
# distinction applies to any of the three, so there is no overclaim risk in
# showing them here the way there is for a restoration site's walk status.
sims_reg = json.load(open(ROOT / 'sims/registry/sims.json'))
schools_reg = json.load(open(ROOT / 'schools/registry/schools.json'))
chapters_reg = json.load(open(ROOT / 'unions/registry/chapters.json'))
schools_hall_set = {u['hall'] for u in schools_reg['units']}

# District hues: eight values far enough apart to read as categories.
assert set(HUES) == set(districts_reg), 'every district needs a hue'


def hall_level_states(slug):
    doc = json.load(open(ROOT / f'pack/registry/halls/{slug}.json'))
    c = {'live': 0, 'calibrating': 0, 'schema_ok': 0, 'draft': 0}
    for lv in doc['levels']:
        c[lv['state']] += 1
    return c


census = {h['slug']: hall_level_states(h['slug']) for h in halls_json}
# interiors wants module-state counts; levels * slots * variants per level.
per_level = L['slots_per_level'] * L['variants_per_lesson']
plans = build_interiors(halls_json, lambda i: {
    k: v * per_level for k, v in census[halls_json[i]['slug']].items()})

stations_by_hall = {}
for s in stations_reg['stations']:
    stations_by_hall.setdefault(s['hall'], []).append(s)

district_of = {slug: k for k, d in districts_reg.items() for slug in d['halls']}

# rooms dedupe, same shape as the 3D page: distinct layouts + per-strand
# defs on the wire, the full rooms inflated in-page at boot
ROOM_DEFS, LAY_LIST, LAY_IDX = {}, [], {}
for h in halls_json:
    lay = [{'strand': r['strand'], 'x': r['x'], 'y': r['y'],
            'w': r['w'], 'h': r['h']} for r in plans[h['slug']]['rooms']]
    key = json.dumps(lay, sort_keys=True)
    for i, (k2, _) in enumerate(LAY_LIST):
        if k2 == key:
            LAY_IDX[h['slug']] = i
            break
    else:
        LAY_IDX[h['slug']] = len(LAY_LIST)
        LAY_LIST.append((key, lay))
    for r in plans[h['slug']]['rooms']:
        rd = {'label': r['label'], 'purpose': r['purpose']}
        assert ROOM_DEFS.setdefault(r['strand'], rd) == rd, \
            f"room def diverges for strand {r['strand']}"

HALLS = [{
    'slug': h['slug'], 'name': h['name'], 'focus': h['focus'],
    'index': h['index'], 'district': district_of[h['slug']],
    'lessons': h['lessons'], 'modules': h['modules'],
    'census': census[h['slug']],
    'lay': LAY_IDX[h['slug']],
    'depth': plans[h['slug']]['envelope']['d'],
    'stations': [s['station_id'] for s in stations_by_hall.get(h['slug'], [])],
    # the first bound simulator seat, if this hall has one (sims/registry/
    # sims.json hall_bindings) — a hall can bind more than one machine; the
    # first is the hall's own, the same rule build_3d.py's seatOf() uses
    'sim': (lambda bl: {'id': bl[0]['sim'], 'name': sims_reg['sims'][bl[0]['sim']]['name']}
            if bl else None)(sims_reg['hall_bindings'].get(h['slug'], [])),
    'schoolsUnit': h['slug'] in schools_hall_set,
} for h in halls_json]

DISTRICTS = {k: {'name': d['name'], 'tagline': d['tagline'],
                 'halls': d['halls'], 'hue': HUES[k]}
             for k, d in districts_reg.items()}


# ---------------------------------------------------------------- lessons --
# The lesson layer: lessons/registry/lessons.json (the walks) and completion/
# registry/completion.json (what a finished step can and cannot prove). Both
# documents ship to the page whole and verbatim (lessons.json#page_contract:
# "the whole document ... no per-lesson preprocessing"); nothing below types a
# count, and every name a step points at is resolved here by name or the
# build stops. No `.get(k, default)` and no fallback: a missing key is a fault.
lessons_reg = json.load(open(ROOT / 'lessons/registry/lessons.json'))
completion_reg = json.load(open(ROOT / 'completion/registry/completion.json'))
LESSONS_R = 'lessons/registry/lessons.json'
COMPLETION_R = 'completion/registry/completion.json'


def need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise KeyError(f'{where}: no field {k!r}')
    return d[k]


HALL_BY_SLUG = {h['slug']: h for h in halls_json}
STEP_KINDS = need(lessons_reg, 'step_kinds', LESSONS_R)
OFF_ROOM = need(lessons_reg, 'off_room_places', LESSONS_R)
EVIDENCE_RULE = need(completion_reg, 'evidence_rule', COMPLETION_R)
EVIDENCE_CLASSES = need(completion_reg, 'evidence_classes', COMPLETION_R)
COMPLETION_LESSONS = need(completion_reg, 'lessons', COMPLETION_R)
LESSON_IDS_OF_HALL = {}
for lid, les in need(lessons_reg, 'lessons', LESSONS_R).items():
    w = f'{LESSONS_R}#lessons.{lid}'
    if need(les, 'id', w) != lid:
        raise KeyError(f'{w}: id {les["id"]!r} disagrees with its key')
    hall = need(les, 'hall', w)
    if hall not in HALL_BY_SLUG:
        raise KeyError(f'{w}: hall {hall!r} is not in pack/registry/halls.json')
    if need(les, 'hall_name', w) != HALL_BY_SLUG[hall]['name']:
        raise KeyError(f'{w}: hall_name {les["hall_name"]!r} is not the registry name')
    rooms_of_hall = {r['strand']: r['label'] for r in plans[hall]['rooms']}
    strand = need(les, 'strand', w)
    if strand not in rooms_of_hall:
        raise KeyError(f'{w}: strand {strand!r} has no room in hall {hall!r}')
    if need(les, 'room_label', w) != rooms_of_hall[strand]:
        raise KeyError(f'{w}: room_label {les["room_label"]!r} is not the '
                       f'{strand!r} room of hall {hall!r} ({rooms_of_hall[strand]!r})')
    if lid not in COMPLETION_LESSONS:
        raise KeyError(f'{COMPLETION_R}#lessons: no record for lesson {lid!r}')
    cw = f'{COMPLETION_R}#lessons.{lid}'
    if need(COMPLETION_LESSONS[lid], 'hall', cw) != hall:
        raise KeyError(f'{cw}: hall disagrees with {w}')
    need(COMPLETION_LESSONS[lid], 'completable', cw)
    need(COMPLETION_LESSONS[lid], 'not_completable_why', cw)
    steps = need(les, 'steps', w)
    if not steps:
        raise KeyError(f'{w}: no steps')
    for i, st in enumerate(steps):
        sw = f'{w}.steps[{i}]'
        if need(st, 'n', sw) != i + 1:
            raise KeyError(f'{sw}: n {st["n"]!r} is out of order')
        kind = need(st, 'kind', sw)
        if kind not in STEP_KINDS:
            raise KeyError(f'{sw}: kind {kind!r} is not in {LESSONS_R}#step_kinds')
        if need(st, 'records', sw) != need(STEP_KINDS[kind], 'records', f'{LESSONS_R}#step_kinds.{kind}'):
            raise KeyError(f'{sw}: records disagrees with step_kinds.{kind}')
        if kind not in EVIDENCE_RULE:
            raise KeyError(f'{sw}: kind {kind!r} has no {COMPLETION_R}#evidence_rule')
        cls = need(EVIDENCE_RULE[kind], 'class', f'{COMPLETION_R}#evidence_rule.{kind}')
        if cls not in EVIDENCE_CLASSES:
            raise KeyError(f'{COMPLETION_R}#evidence_rule.{kind}: class {cls!r} is not an evidence class')
        # the three classes exactly as completion.json draws them: a kind that
        # records an episode is episode-backed and nothing else is
        if (st['records'] is not None) != (cls == 'episode-backed'):
            raise KeyError(f'{sw}: records={st["records"]!r} but evidence class is {cls!r}')
        where = need(st, 'where', sw)
        if where not in rooms_of_hall and where not in OFF_ROOM:
            raise KeyError(f'{sw}: where {where!r} is neither a room of hall {hall!r} '
                           f'nor an off-room place')
    LESSON_IDS_OF_HALL.setdefault(hall, []).append(lid)

LADDER_EDGES = need(need(lessons_reg, 'ladder', LESSONS_R), 'edges', f'{LESSONS_R}#ladder')
for i, e in enumerate(LADDER_EDGES):
    ew = f'{LESSONS_R}#ladder.edges[{i}]'
    for side in ('lesson', 'needs'):
        if need(e, side, ew) not in lessons_reg['lessons']:
            raise KeyError(f'{ew}: {side} {e[side]!r} is not a lesson')
    need(e, 'because', ew)
if need(completion_reg, 'ladder', COMPLETION_R) != LADDER_EDGES:
    raise KeyError(f'{COMPLETION_R}#ladder disagrees with {LESSONS_R}#ladder.edges')
for h in HALLS:
    h['lessonIds'] = LESSON_IDS_OF_HALL[h['slug']] if h['slug'] in LESSON_IDS_OF_HALL else []

I18N = {}
for f in sorted((ROOT / 'i18n/locales').glob('*.json')):
    c = json.load(open(f))
    I18N[c['locale']] = {
        'language': c['language'], 'dir': c['dir'],
        'strings': c['strings'], 'districts': c['districts'],
        'strands': c['strands'], 'tiers': c['tiers'], 'states': c['states'],
    }

DATA = json.dumps({
    'ledger': {'halls': L['halls'], 'total_modules': L['total_modules'],
               'districts': len(DISTRICTS)},
    'per_level': per_level,
    'districts': DISTRICTS,
    'campuses': campuses_reg,
    'halls': HALLS,
    'roomDefs': ROOM_DEFS,
    'layouts': [lay for _, lay in LAY_LIST],
    'stations': {s['station_id']: s for s in stations_reg['stations']},
    'tools': {'cribs': tools_reg['cribs'],
              'drill': tools_reg['drill']['name'],
              'honesty': tools_reg['honesty']['status']},
    # chapter seats: every hall's home campus plus its regional seat at
    # every other campus (unions/registry/chapters.json) — an Academy
    # training structure, never a claim about a real union local, so it is
    # shown as a stat chip, never as a place (build_3d.py's own comment on
    # this same fact: "an Academy structure only").
    'chapters': {'of': {slug: c['home'] for slug, c in chapters_reg['chapters'].items()},
                 'regions': {k: v['abbr'] for k, v in chapters_reg['regions'].items()},
                 'honesty': chapters_reg['honesty']['chapters']},
    # the one simulator record a hall's badge needs, keyed for the panel —
    # full seat detail (controls, rubric, scenarios) stays in the 3D app,
    # which is what the badge deep-links to.
    'simsHonesty': sims_reg['honesty']['status'],
    'schoolsHonesty': schools_reg['honesty']['districts'],
    'strandmods': strand_modules(),
    'lessons': lessons_reg,
    'completion': completion_reg,
    'i18n': I18N,
}, ensure_ascii=False, separators=(',', ':'))

NAV = nav_html('web/trade_craft_interactive.html', nav_labels('en'))
from questkit import QUEST_CSS, quest_js, page_hooks  # noqa: E402  quests: egg hooks only (body tail)
QUEST_TAIL = '<style>' + QUEST_CSS + '</style>\n' + page_hooks('web/trade_craft_interactive.html') + quest_js('page:web/trade_craft_interactive.html')

page = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' stroke='%23E8A33D' stroke-width='2.6' stroke-linejoin='round'/%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E">
<title>SmartCiti.X : Trade Craft Academy — interactive campus map</title>
<style>
:root{
  --plate:#12181B; --panel:#182023; --sunk:#0C1113; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --mark-ink:#12181B; --steel:#41C4D4;
  --good:#5CB584; --warn:#E8A33D; --crit:#E07C68;
}
*{box-sizing:border-box}
body{margin:0;background:var(--plate);color:var(--ink);
  font:15px/1.55 "IBM Plex Sans",system-ui,sans-serif;padding:0 16px 48px}
.wrap{max-width:1180px;margin:0 auto}
header{padding:30px 0 10px;border-bottom:3px solid var(--mark);
  display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 22px}
header h1{font:700 30px/1.1 "Barlow Condensed",system-ui,sans-serif;margin:0}
header h1 .x{color:var(--mark)}
header .attr{color:var(--muted);font-size:13px}
.figs{display:flex;gap:16px;flex-wrap:wrap;margin-left:auto;color:var(--muted);font-size:13px}
.figs b{color:var(--mark);font:600 17px "Barlow Condensed",sans-serif}
.bar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:16px 0}
.bar .lbl{color:var(--muted);font-size:13px;margin-inline-end:2px}
.tgl{display:inline-flex;align-items:center;gap:6px;background:var(--panel);
  border:1px solid var(--rule);border-radius:999px;padding:6px 13px;cursor:pointer;
  font-size:13px;user-select:none}
.tgl input{accent-color:var(--mark);margin:0}
select{background:var(--panel);color:var(--ink);border:1px solid var(--rule);
  border-radius:6px;padding:6px 10px;font:inherit;margin-inline-start:auto}
.legend{display:flex;gap:14px;flex-wrap:wrap;color:var(--muted);font-size:12px;margin:2px 0 14px}
.legend .sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-inline-end:5px;vertical-align:-1px}
.campus{display:flex;flex-direction:column;gap:26px}
.campushdr{font:600 22px "Barlow Condensed",sans-serif;margin:0 0 10px;
  border-bottom:2px solid var(--mark);padding-bottom:6px;
  display:flex;flex-wrap:wrap;gap:6px 14px;align-items:baseline}
.campushdr em{color:var(--muted);font:400 13px "IBM Plex Sans",sans-serif}
.campusbody{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(430px,100%),1fr));gap:18px}
@media(max-width:480px){.campus{grid-template-columns:1fr}}
.district{background:var(--panel);border:1px solid var(--rule);border-radius:10px;padding:14px 16px}
.district h2{font:600 19px "Barlow Condensed",sans-serif;margin:0;
  border-inline-start:4px solid;padding-inline-start:10px}
.district .tag{color:var(--muted);font-size:12.5px;margin:3px 0 10px;padding-inline-start:14px}
.halls{display:grid;grid-template-columns:repeat(auto-fill,minmax(122px,1fr));gap:8px}
.hall{position:relative;background:var(--sunk);border:1px solid var(--rule);border-radius:7px;
  padding:8px 9px 7px;cursor:pointer;text-align:start;color:var(--ink);font:inherit;
  display:flex;flex-direction:column;gap:5px;min-height:58px}
.hall:hover{border-color:var(--mark)}
.hall .nm{font-size:12px;line-height:1.25;font-weight:600}
.hall .stbar{display:flex;height:5px;border-radius:3px;overflow:hidden;background:var(--rule)}
.hall .stbar i{display:block;height:100%}
.hall .badge{position:absolute;top:-6px;inset-inline-end:-6px;background:var(--mark);
  color:var(--mark-ink);font:700 10.5px/1 "IBM Plex Mono",monospace;border-radius:999px;
  padding:4px 6px;display:none}
body.L-stations .hall .badge{display:block}
body:not(.L-modules) .hall .stbar{display:none}
body.L-districts .hall{border-inline-start-width:4px}
/* detail panel */
#ov{position:fixed;inset:0;background:rgba(6,10,12,.72);display:none;z-index:9}
#panel{position:fixed;top:0;inset-inline-end:0;bottom:0;width:min(560px,100%);
  background:var(--panel);border-inline-start:1px solid var(--rule);z-index:10;
  transform:translateX(105%);transition:transform .22s ease;overflow-y:auto;
  padding:20px 22px 40px}
html[dir="rtl"] #panel{transform:translateX(-105%)}
body.open #ov{display:block}
body.open #panel{transform:none}
#panel h2{font:600 24px "Barlow Condensed",sans-serif;margin:2px 0 2px}
#panel .focus{color:var(--muted);margin:0 0 10px}
#panel .chip{display:inline-block;border:1px solid var(--rule);border-radius:999px;
  padding:2px 10px;font-size:12px;color:var(--muted);margin:0 4px 10px 0}
#panel h3{font:600 15px "Barlow Condensed",sans-serif;letter-spacing:.04em;
  text-transform:uppercase;color:var(--steel);margin:20px 0 8px}
#close{position:absolute;top:12px;inset-inline-end:14px;background:none;border:1px solid var(--rule);
  color:var(--muted);border-radius:6px;padding:5px 11px;cursor:pointer;font:inherit}
.cbar{display:flex;height:12px;border-radius:6px;overflow:hidden;background:var(--rule);margin:4px 0 6px}
.cbar i{display:block;height:100%}
.ckey{color:var(--muted);font-size:12px;display:flex;gap:12px;flex-wrap:wrap}
svg text{font-family:"IBM Plex Mono",monospace}
.stn{border:1px solid var(--rule);border-radius:8px;margin:8px 0;overflow:hidden}
.stn>button{width:100%;text-align:start;background:var(--sunk);color:var(--ink);
  border:none;padding:9px 12px;cursor:pointer;font:inherit;display:flex;gap:8px;align-items:baseline}
.stn .dot{width:9px;height:9px;border-radius:50%;background:var(--mark);flex:none;align-self:center}
.stn .rm{margin-inline-start:auto;color:var(--muted);font-size:11.5px;white-space:nowrap}
.stn .body{display:none;padding:10px 14px;border-top:1px solid var(--rule);font-size:13.5px}
.stn.open .body{display:block}
.stn .body ul{margin:6px 0;padding-inline-start:20px;color:var(--muted)}
.stn .q{background:var(--sunk);border-radius:6px;padding:8px 12px;margin-top:8px}
.stn .q .opt{display:block;background:none;border:1px solid var(--rule);color:var(--ink);
  border-radius:5px;padding:5px 9px;margin:5px 0;cursor:pointer;font:inherit;width:100%;text-align:start}
.stn .q .opt.ok{border-color:var(--good);color:var(--good)}
.stn .q .opt.bad{border-color:var(--crit);color:var(--crit)}
.lattice{display:grid;grid-template-columns:auto repeat(3,1fr);gap:4px;font-size:11.5px}
.lattice div{background:var(--sunk);border-radius:4px;padding:4px 7px;color:var(--muted)}
.lattice .hd{background:none;color:var(--steel)}
.lattice .on{color:var(--ink)}
/* lesson layer: the walks the lessons registry stands in the rooms, and the
   ladder between the halls they stand in */
.hall .lbadge{position:absolute;bottom:-6px;inset-inline-end:-6px;background:var(--steel);
  color:var(--mark-ink);font:700 10.5px/1 "IBM Plex Mono",monospace;border-radius:999px;
  padding:4px 6px;display:none}
body.L-lessons .hall .lbadge{display:block}
body.L-lessons .hall.haslesson{border-color:var(--steel)}
.campuswrap{position:relative}
#ladder{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;display:none;overflow:visible}
body.L-lessons #ladder{display:block}
#ladder path{fill:none;stroke:var(--steel);stroke-width:1.6;opacity:.75;pointer-events:stroke}
#ladder path[data-because="same-seat"]{stroke:var(--mark)}
#ladder path[data-because="same-district-crib"]{stroke:var(--good)}
#ladder path:hover{opacity:1;stroke-width:3}
.ev{display:inline-block;width:10px;height:10px;border-radius:50%;margin-inline-end:5px;vertical-align:-1px}
.ev[data-class="episode-backed"]{background:var(--steel)}
.ev[data-class="device-mark"]{background:var(--mark)}
.ev[data-class="self-reported"]{background:none;border:1.5px solid var(--muted)}
.lesson{border:1px solid var(--rule);border-radius:8px;margin:8px 0;padding:10px 12px;font-size:13.5px}
.lesson[data-completable="false"]{border-color:var(--crit)}
.lesson h4{margin:0 0 3px;font:600 15px "Barlow Condensed",sans-serif}
.lesson .why{color:var(--muted);font-size:12.5px;margin:0 0 6px}
.lesson .nc{color:var(--crit);font-size:12.5px;margin:0 0 6px}
.lesson ol{margin:4px 0;padding-inline-start:22px;color:var(--muted);font-size:12.5px}
.lesson ol li b{color:var(--ink);font-weight:500}
.lesson .links a{color:var(--steel);font-size:12.5px;margin-inline-end:12px}
.lesson .needs{color:var(--muted);font-size:12px;margin-top:6px}
footer{color:var(--muted);font-size:12.5px;margin-top:26px;border-top:1px solid var(--rule);padding-top:12px}
</style>
<style>__SITENAV_CSS__</style>
</head>
<body class="L-districts L-modules L-stations">
__SITENAV__<div class="wrap">
<header>
  <h1>SmartCiti<span class="x">.X</span> : Trade Craft Academy</h1>
  <span class="attr">powered by AGI Corp</span>
  <div class="figs" id="figs"></div>
</header>
<div class="bar" id="layers"></div>
<div class="legend" id="legend"></div>
<div class="campuswrap"><div class="campus" id="campus"></div><svg id="ladder" aria-label="lesson ladder"></svg></div>
<footer id="honesty"></footer>
</div>
<div id="ov"></div>
<aside id="panel" aria-label="hall detail"><button id="close"></button><div id="pbody"></div></aside>
<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
for (const h of D.halls) h.rooms = D.layouts[h.lay].map((r) => ({
  ...r, label: D.roomDefs[r.strand].label,
  purpose: D.roomDefs[r.strand].purpose }));
const params = new URLSearchParams(location.search);
const STATE_COLORS = {live:'var(--good)', calibrating:'var(--steel)', schema_ok:'var(--warn)', draft:'var(--rule)'};
const STATES = ['live','calibrating','schema_ok','draft'];
let loc = D.i18n[params.get('lang')] ? params.get('lang') : 'en';
let query = '';
const t = (k) => D.i18n[loc].strings[k] ?? D.i18n.en.strings[k] ?? k;
const fmt = (s, v) => s.replace(/\\{(\\w+)\\}/g, (m,k) => k in v ? v[k] : m);
const F = (n) => n.toLocaleString('en-US');
const dname = (k) => D.i18n[loc].districts[k]?.name ?? D.districts[k].name;
const dtag = (k) => D.i18n[loc].districts[k]?.tagline ?? D.districts[k].tagline;

// ---- the lesson layer. Every figure below is computed from D.lessons and
// D.completion at render; nothing in this script types a count.
const LESSONS = D.lessons.lessons;
const LADDER = D.lessons.ladder.edges;
const EV_RULE = D.completion.evidence_rule;
const EV_CLASSES = Object.keys(D.completion.evidence_classes);
const must = (o, k, where) => { if (!(o !== null && typeof o === 'object' && k in o)) throw new Error(where + ': no ' + k); return o[k]; };
const evClass = (kind) => must(must(EV_RULE, kind, 'completion.evidence_rule'), 'class', 'evidence_rule.' + kind);
const allSteps = () => Object.values(LESSONS).flatMap((l) => l.steps);
function evClassCounts(){
  const c = Object.fromEntries(EV_CLASSES.map((k) => [k, 0]));
  for (const st of allSteps()) c[evClass(st.kind)] += 1;
  return c;
}
const kindsOfClass = (cls) => Object.keys(D.lessons.step_kinds).filter((k) => evClass(k) === cls);
const completion = (lid) => must(D.completion.lessons, lid, 'completion.lessons');
const nCompletable = () => Object.keys(LESSONS).filter((lid) => completion(lid).completable).length;
const hallOfLesson = (lid) => must(LESSONS, lid, 'lessons').hall;
const edgesTouching = (lid) => LADDER.filter((e) => e.lesson === lid || e.needs === lid);

function liveShare(h){ const c=h.census; const tot=STATES.reduce((a,s)=>a+c[s],0); return c.live/tot; }

function render(){
  const i = D.i18n[loc];
  document.documentElement.lang = loc;
  document.documentElement.dir = i.dir;
  document.getElementById('figs').innerHTML =
    `<span><b>${F(D.ledger.halls)}</b> ${fmt(t('figures.halls'),{n:''}).trim()}</span>`+
    `<span><b>${F(D.ledger.total_modules)}</b> ${fmt(t('figures.modules'),{n:''}).trim()}</span>`+
    `<span><b>${D.ledger.districts}</b> ${fmt(t('figures.districts'),{n:''}).trim()}</span>`+
    `<span data-fig="lessons"><b>${Object.keys(LESSONS).length}</b> ${t('interactive.lessonsInRooms')}</span>`+
    `<span data-fig="steps"><b>${allSteps().length}</b> ${t('interactive.steps')}</span>`+
    `<span data-fig="completable"><b>${nCompletable()}</b> / ${Object.keys(LESSONS).length} ${t('interactive.completable')}</span>`;
  const LAYERS = [['districts','map.layer.districts'],['pipeline','map.layer.pipeline'],
                  ['modules','map.layer.modules'],['stations','map.layer.stations'],['lessons','interactive.lessons']];
  document.getElementById('layers').innerHTML =
    `<span class="lbl">${t('map.layers')}:</span>` +
    LAYERS.map(([k,lk]) => `<label class="tgl"><input type="checkbox" data-l="${k}" ${document.body.classList.contains('L-'+k)?'checked':''}>${t(lk)}</label>`).join('') +
    `<select id="lang" aria-label="${t('language.select')}">` +
    Object.entries(D.i18n).map(([c,v]) => `<option value="${c}" ${c===loc?'selected':''}>${v.language}</option>`).join('') + `</select>` +
    `<input id="q" type="search" value="${query.replace(/"/g,'&quot;')}" placeholder="${t('ui.search')}" aria-label="${t('ui.search')}"
      style="background:var(--panel);color:var(--ink);border:1px solid var(--rule);border-radius:999px;padding:6px 13px;font:inherit;font-size:13px;width:170px">`;
  document.getElementById('legend').innerHTML =
    STATES.map(s => `<span><span class="sw" style="background:${STATE_COLORS[s]}"></span>${i.states[s]}</span>`).join('') +
    `<span><span class="sw" style="background:var(--mark);border-radius:50%"></span>${t('map.layer.stations')}</span>` +
    Object.entries(evClassCounts()).map(([cls, n]) =>
      `<span data-evclass="${cls}" title="${D.completion.evidence_classes[cls]}"><span class="ev" data-class="${cls}"></span>${cls} (${kindsOfClass(cls).join(', ')}) · <b>${n}</b></span>`).join('') +
    [...new Set(LADDER.map((e) => e.because))].map((why) =>
      `<span data-reason="${why}"><span class="sw" style="background:none;border-top:2px solid ${why==='same-seat'?'var(--mark)':why==='same-district-crib'?'var(--good)':'var(--steel)'};height:0"></span>ladder: ${why} · <b>${LADDER.filter((e) => e.because === why).length}</b></span>`).join('');
  document.getElementById('campus').innerHTML = Object.entries(D.campuses).map(([ck, camp]) => `
    <div class="campusgrp">
      <h2 class="campushdr"><span>${camp.name}</span>
        <em>${camp.city}, ${camp.region} · ${camp.halls.length} · ${camp.tagline}</em></h2>
      <div class="campusbody">` +
    camp.districts.map(k => { const d = D.districts[k]; return `
    <section class="district" style="--hue:${d.hue}">
      <h2 style="border-color:hsl(${d.hue} 62% 58%)">${dname(k)} · ${d.halls.length}</h2>
      <p class="tag">${dtag(k)}</p>
      <div class="halls">` +
      d.halls.map(slug => { const h = D.halls.find(x=>x.slug===slug);
        const pipe = document.body.classList.contains('L-pipeline');
        const hueOn = document.body.classList.contains('L-districts');
        const bg = pipe ? `background:color-mix(in oklab, var(--good) ${Math.round(liveShare(h)*38)}%, var(--sunk))` : '';
        const bd = hueOn ? `border-inline-start-color:hsl(${d.hue} 62% 55%)` : '';
        const bar = STATES.map(s => `<i style="width:${100*h.census[s]/100}%;background:${STATE_COLORS[s]}"></i>`).join('');
        const badge = h.stations.length ? `<span class="badge">${h.stations.length}</span>` : '';
        const lbadge = h.lessonIds.length ? `<span class="lbadge">${h.lessonIds.length}</span>` : '';
        return `<button class="hall${h.lessonIds.length?' haslesson':''}" data-slug="${slug}" style="${bg};${bd}">${badge}${lbadge}<span class="nm">${h.name}</span><span class="stbar">${bar}</span></button>`;
      }).join('') + `</div></section>`; }).join('') +
    `</div></div>`).join('');
  applyFilter();
  ladderEdges();
  document.getElementById('honesty').textContent =
    t('honesty.taxonomy') + ' ' + t('honesty.modules') + ' ' + t('honesty.content');
  document.getElementById('close').textContent = t('ui.close');
}

__PIPELINE_JS__

function modTable(h){
  const i = D.i18n[loc];
  const rows = Object.entries(D.strandmods).map(([sk, sm]) => {
    const x = sm.samples[0];
    const id = 'u' + String(h.index).padStart(3,'0') + '.' + x.suffix;
    return `<tr><td>${i.strands[sk]}</td>
      <td style="font-family:'IBM Plex Mono',monospace;font-size:11.5px">${id}</td>
      <td style="text-align:end">${sm.d_from}–${sm.d_to}</td>
      <td style="text-align:end">${F(sm.modules)}</td>
      <td>${i.states[pipeline(h.index, x.level)]}</td></tr>`;
  }).join('');
  return `<table style="width:100%;border-collapse:collapse;font-size:12.5px">
    <tbody>${rows}</tbody></table>
    <style>#pbody td{border-top:1px solid var(--rule);padding:5px 7px;color:var(--muted)}</style>`;
}

function applyFilter(){
  const q = query.trim().toLowerCase();
  document.querySelectorAll('.hall').forEach(el => {
    const h = D.halls.find(x=>x.slug===el.dataset.slug);
    el.style.display = (!q || (h.name+' '+h.focus+' '+h.slug).toLowerCase().includes(q)) ? '' : 'none';
  });
}

const EDGE_LIFT = 40; // px the ladder curve lifts above the two hall tiles - a layout constant, not a count
function ladderEdges(){
  // one edge per D.lessons.ladder.edges, drawn between the tiles of the halls
  // the two lessons stand in; a same-hall edge loops on its own tile. The
  // reason is the hover title, verbatim from the registry.
  const svg = document.getElementById('ladder');
  const box = svg.parentElement.getBoundingClientRect();
  const at = (lid) => {
    const el = document.querySelector(`.hall[data-slug="${hallOfLesson(lid)}"]`);
    if (!el) throw new Error('ladder: no tile for hall ' + hallOfLesson(lid));
    const r = el.getBoundingClientRect();
    return { x: r.left - box.left + r.width / 2, y: r.top - box.top + r.height / 2 };
  };
  svg.setAttribute('viewBox', `0 0 ${box.width} ${box.height}`);
  svg.innerHTML = LADDER.map((e) => {
    const a = at(e.needs), b = at(e.lesson);
    const d = a.x === b.x && a.y === b.y
      ? `M${a.x-14} ${a.y} a14 14 0 1 1 28 0`
      : `M${a.x} ${a.y} Q${(a.x+b.x)/2} ${Math.min(a.y,b.y)-EDGE_LIFT} ${b.x} ${b.y}`;
    return `<path data-edge="${e.lesson}>${e.needs}" data-because="${e.because}" d="${d}"><title>${LESSONS[e.lesson].title} needs ${LESSONS[e.needs].title} · ${e.because}</title></path>`;
  }).join('');
}

function lessonPaths(h, U, W, yardY){
  // one path per lesson standing in this hall: its steps in order, each at
  // the room it names (D.layouts) or at the off-room place
  // (D.lessons.off_room_places), numbered, marked by kind and by the evidence
  // class completion.json gives that kind.
  const places = Object.keys(D.lessons.off_room_places);
  const roomOf = (strand) => h.rooms.find((r) => r.strand === strand);
  return h.lessonIds.map((lid, li) => {
    const les = LESSONS[lid];
    const pts = les.steps.map((st, si) => {
      const r = roomOf(st.where);
      if (r) return { x: (r.x + r.w/2)*U + (li - (h.lessonIds.length-1)/2)*12, y: (r.y + r.h/2)*U + 4 + si*2 };
      const pi = places.indexOf(st.where);
      if (pi < 0) throw new Error(`lessons.${lid}.steps[${si}]: where ${st.where} is neither a room of ${h.slug} nor an off-room place`);
      return { x: (pi + 0.5) * W / places.length + li*12, y: yardY + U*0.6 + si*2 };
    });
    const line = pts.map((p, i2) => (i2 ? 'L' : 'M') + p.x + ' ' + p.y).join(' ');
    const marks = les.steps.map((st, si) => {
      const cls = evClass(st.kind);
      const fill = cls === 'episode-backed' ? 'var(--steel)' : cls === 'device-mark' ? 'var(--mark)' : 'var(--sunk)';
      return `<g data-step="${st.n}" data-kind="${st.kind}" data-class="${cls}"><circle cx="${pts[si].x}" cy="${pts[si].y}" r="7" fill="${fill}" stroke="var(--ink)" stroke-width="1"/>` +
        `<text x="${pts[si].x}" y="${pts[si].y+3.5}" font-size="9" text-anchor="middle" fill="${cls==='self-reported'?'var(--ink)':'var(--mark-ink)'}">${st.n}</text>` +
        `<title>${st.n}. ${st.kind} · ${cls} · ${st.do}</title></g>`;
    }).join('');
    return `<g data-lesson="${lid}"><path d="${line}" fill="none" stroke="var(--steel)" stroke-width="1.5" stroke-dasharray="4 3" opacity=".85"><title>${les.title}</title></path>${marks}</g>`;
  }).join('');
}

function planSVG(h){
  const U = 26, W = 12*U, yardY = h.depth*U;
  const H = yardY + (h.lessonIds.length ? U*1.4 : 0);
  const dh = D.districts[h.district].hue;
  let dots = '';
  const stns = h.stations.map(id => D.stations[id]);
  const byRoom = {};
  stns.forEach(s => { (byRoom[s.room] ??= []).push(s); });
  const rects = h.rooms.map(r => {
    const list = byRoom[r.label] ?? [];
    const dot = list.map((s,j) =>
      `<circle cx="${r.x*U + (j+1)*(r.w*U)/(list.length+1)}" cy="${(r.y+r.h/2)*U + 6}" r="5.5" fill="var(--mark)"><title>${s.name}</title></circle>`).join('');
    // the tools room carries its district crib: the pegboard drawn in place
    const crib = r.strand === 'tools'
      ? `<rect x="${(r.x+r.w)*U-9}" y="${r.y*U+5}" width="5" height="${r.h*U-10}" rx="1.5"
          fill="var(--mark)" opacity=".8"><title>${D.tools.cribs[h.district].name} · ${D.tools.cribs[h.district].tools.length}</title></rect>`
      : '';
    return `<g><rect x="${r.x*U+1}" y="${r.y*U+1}" width="${r.w*U-2}" height="${r.h*U-2}" rx="3"
      fill="hsl(${dh} 25% 16%)" stroke="hsl(${dh} 30% 32%)"/>
      <title>${r.purpose}</title>
      <text x="${r.x*U+7}" y="${r.y*U+16}" font-size="10.5" fill="var(--ink)">${r.label}</text>
      <text x="${r.x*U+7}" y="${r.y*U+29}" font-size="9" fill="var(--muted)">${D.i18n[loc].strands[r.strand]}</text>${crib}${dot}</g>`;
  }).join('');
  const yard = h.lessonIds.length ? Object.keys(D.lessons.off_room_places).map((k, i2, arr) =>
    `<text x="${(i2+0.5)*W/arr.length}" y="${yardY+11}" font-size="9" text-anchor="middle" fill="var(--muted)">${D.lessons.off_room_places[k].short}</text>`).join('') : '';
  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;background:var(--sunk);border-radius:8px">${rects}${yard}${lessonPaths(h, U, W, yardY)}</svg>`;
}

function lessonCards(h){
  return h.lessonIds.map((lid) => {
    const les = LESSONS[lid], c = completion(lid);
    const steps = les.steps.map((st) => `<li data-step="${st.n}" data-kind="${st.kind}"><span class="ev" data-class="${evClass(st.kind)}"></span><b>${st.kind}</b> · ${st.do}</li>`).join('');
    const needs = edgesTouching(lid).map((e) => e.lesson === lid
      ? `needs <a href="trade_craft_lessons.html#lesson-${e.needs}">${LESSONS[e.needs].title}</a> (${e.because})`
      : `needed by <a href="trade_craft_lessons.html#lesson-${e.lesson}">${LESSONS[e.lesson].title}</a> (${e.because})`).join(' · ');
    return `<div class="lesson" id="lesson-${lid}" data-lesson="${lid}" data-completable="${c.completable}">
      <h4>${les.title}</h4><p class="why">${les.room_label} · ${les.why}</p>
      ${c.completable ? '' : `<p class="nc">${t('interactive.notCompletable')}: ${c.not_completable_why}</p>`}
      <ol>${steps}</ol>
      <div class="links"><a href="trade_craft_lessons.html#lesson-${lid}">lesson page</a><a href="trade_craft_3d.html?hall=${les.hall}&lang=${loc}">3D hall</a></div>
      ${needs ? `<div class="needs">${needs}</div>` : ''}</div>`;
  }).join('');
}

function openHall(slug){
  const h = D.halls.find(x=>x.slug===slug);
  const i = D.i18n[loc];
  const tot = STATES.reduce((a,s)=>a+h.census[s],0);
  const cbar = STATES.map(s=>`<i style="width:${100*h.census[s]/tot}%;background:${STATE_COLORS[s]}"></i>`).join('');
  const ckey = STATES.map(s=>`<span>${i.states[s]}: ${h.census[s]} ${t('unit.levels')}</span>`).join('');
  const stns = h.stations.map(id => D.stations[id]).map(s => `
    <div class="stn" id="${s.station_id}">
      <button data-st="${s.station_id}"><span class="dot"></span><b>${s.name}</b>
        <span class="rm">${s.room} · ${i.tiers[s.tier]}</span></button>
      <div class="body"><p>${s.lesson}</p>
        <b>${t('station.checklist')}</b><ul>${s.checklist.map(c=>`<li>${c}</li>`).join('')}</ul>
        <div class="q"><b>${t('station.quiz')}:</b> ${s.quiz.question}
          ${s.quiz.options.map((o,j)=>`<button class="opt" data-ok="${o.correct?1:0}">${o.label}</button>`).join('')}</div>
      </div></div>`).join('');
  const lat = `<div class="lattice"><div class="hd"></div>` +
    Object.entries(i.tiers).map(([,v])=>`<div class="hd">${v}</div>`).join('') +
    Object.entries(i.strands).map(([sk,sv]) => `<div class="hd">${sv}</div>` +
      ['fundamentals','applied','mastery'].map(tier => {
        const seeded = h.stations.some(id => D.stations[id].strand===sk && D.stations[id].tier===tier);
        return `<div class="${seeded?'on':''}">${seeded?'●':'·'}</div>`; }).join('')).join('');
  // the other three per-hall facts the 3D app's own header shows: a
  // simulator seat and a Schools flipped unit are not held by every hall
  // (45/111 each, sims/ and schools/), so each badge appears only when
  // this hall's own record has one — never invented for a hall without
  // one. Regional chapter seats are an Academy training structure every
  // hall holds at every campus, never a place (a stat chip, not a link).
  const simChip = h.sim
    ? `<a class="chip" href="trade_craft_3d.html?hall=${h.slug}&lang=${loc}"
        style="color:var(--warn);border-color:var(--warn)">▶ ${h.sim.name}</a>` : '';
  const schoolsChip = h.schoolsUnit
    ? `<a class="chip" href="trade_craft_3d.html?hall=${h.slug}&lang=${loc}"
        style="color:var(--mark);border-color:var(--mark)">🎓 ${t('hall.flippedUnit')}</a>` : '';
  const home = D.chapters.of[h.slug];
  const chapterChip = `<span class="chip" title="${D.chapters.honesty}">⌂ `
    + Object.entries(D.chapters.regions)
        .map(([ck, ab]) => ck === home ? `<b>${ab}</b>` : ab).join(' · ') + '</span>';
  history.replaceState(null, '', `?hall=${slug}&lang=${loc}`);
  document.getElementById('pbody').innerHTML = `
    <h2>${h.name}</h2><p class="focus">${h.focus}</p>
    <span class="chip">${dname(h.district)}</span>
    <span class="chip">${Object.values(D.campuses).find(c=>c.halls.includes(h.slug)).city}</span>
    <span class="chip">${F(h.lessons)} · ${fmt(t('figures.lessons'),{n:''}).trim()}</span>
    <span class="chip">${fmt(t('figures.modules'),{n:F(h.modules)})}</span>
    <a class="chip" id="to3d" href="trade_craft_3d.html?hall=${h.slug}&lang=${loc}" style="color:var(--steel);border-color:var(--steel)">⬡ ${t('hall.enter3d')}</a>
    ${simChip}${schoolsChip}${chapterChip}
    <h3>${t('map.layer.pipeline')}</h3><div class="cbar">${cbar}</div><div class="ckey">${ckey}</div>
    <h3>${t('hall.rooms')}</h3>${planSVG(h)}
    <h3>🧰 ${D.tools.cribs[h.district].name}</h3>
    <div>${D.tools.cribs[h.district].tools.map(tl =>
      `<span class="chip" title="${tl.use}">${tl.glyph} ${tl.name}</span>`).join(' ')}</div>
    <p style="color:var(--muted);font-size:11.5px;margin-top:6px">${D.tools.drill} · ${D.tools.honesty}</p>
    ${stns ? `<h3>${t('hall.stations')} (${h.stations.length})</h3>${stns}` : ''}
    ${h.lessonIds.length ? `<h3>${t('interactive.lessonsHere')} (${h.lessonIds.length})</h3>${lessonCards(h)}` : ''}
    <h3>${t('hall.skills')}</h3>${lat}
    <h3>${t('map.layer.modules')}</h3>${modTable(h)}`;
  document.body.classList.add('open');
}

document.addEventListener('click', (e) => {
  const hall = e.target.closest('.hall');
  if (hall) return openHall(hall.dataset.slug);
  if (e.target.closest('#close') || e.target.id === 'ov')
    return document.body.classList.remove('open');
  const st = e.target.closest('.stn > button');
  if (st) return st.parentElement.classList.toggle('open');
  const opt = e.target.closest('.opt');
  if (opt) { opt.parentElement.querySelectorAll('.opt').forEach(o =>
      o.classList.toggle('ok', o.dataset.ok==='1'));
    if (opt.dataset.ok!=='1') opt.classList.add('bad'); return; }
});
document.addEventListener('change', (e) => {
  if (e.target.dataset?.l) { document.body.classList.toggle('L-'+e.target.dataset.l, e.target.checked); render(); }
  if (e.target.id === 'lang') { loc = e.target.value; history.replaceState(null, '', `?lang=${loc}`); render(); }
});
document.addEventListener('input', (e) => {
  if (e.target.id === 'q') { query = e.target.value; applyFilter(); ladderEdges(); }
});
render();
addEventListener('resize', ladderEdges);
if (params.get('hall') && D.halls.some(h => h.slug === params.get('hall')))
  openHall(params.get('hall'));
</script>
__QUEST_TAIL__</body>
</html>
'''

page = page.replace('__SITENAV_CSS__', NAV_CSS).replace('__SITENAV__', NAV)
page = page.replace('__QUEST_TAIL__', QUEST_TAIL)
page = page.replace('__DATA__', DATA).replace('__PIPELINE_JS__', PIPELINE_JS)
out = HERE / 'trade_craft_interactive.html'
n_st = stations_reg['count']
page = apply_seo(page, 'web/trade_craft_interactive.html', 'SmartCiti.X : Trade Craft Academy \u2014 interactive campus map',
    'The interactive layered campus map: districts, pipeline and module layers, training stations and each hall\'s tool crib, searchable and deep-linkable.', 'page')
emit(out, page, f"{L['halls']} halls | {n_st} stations | {len(I18N)} locales")
