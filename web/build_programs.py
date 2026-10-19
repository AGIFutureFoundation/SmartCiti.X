#!/usr/bin/env python3
"""The Programs page: web/trade_craft_programs.html (wave 18).

Reads programs/registry/programs.json (python3 programs/build.py): the K-12 program pathways by grade band, the
teacher program cards and the nonprofit sectors. Every chrome word comes from the prog.* i18n keys (8 locales,
Arabic right-to-left); every registry string (band offers, course, lesson and hall titles, agent names and lines,
Cognition.X blocks, sector quotes) is shown verbatim in English. Counts are read from the registry, never typed here.

The page states that districts, programmes and organisations are PROPOSED, that the UN path is PROPOSED and not
affiliated, that nothing is accredited, and that games, coins and badges are play. It saves nothing and sends nothing:
no storage, no request. It speaks nothing either: an agent's voice lives on the Hive page, where classroom mode starts
muted.
"""
import html
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402
from seo import apply_seo  # noqa: E402
from sitenav import nav_html, labels as nav_labels, NAV_CSS, STYLE_JS  # noqa: E402
from pagehero import theme  # noqa: E402
from design_kit import STYLE_HEAD_JS  # noqa: E402
import sitenav  # noqa: E402

PAGE = 'web/trade_craft_programs.html'
E = lambda s: html.escape(str(s), quote=True)


class ProgramsPageError(Exception):
    pass


def need(c, m):
    if not c:
        raise ProgramsPageError('build_programs: ' + m)
    return c


need(PAGE in sitenav.PAGES, f'{PAGE} is not declared in web/sitenav.py GROUPS (nav.page.programs)')
REG = json.loads(need((ROOT / 'programs/registry/programs.json').exists() and
                      (ROOT / 'programs/registry/programs.json').read_text(encoding='utf-8'),
                      'programs/registry/programs.json is missing; run python3 programs/build.py'))
for k in ('source_stamp', 'honesty', 'rules', 'bands', 'cards', 'sectors', 'counts', 'attribution', 'districts'):
    need(k in REG, f'programs.json has no {k!r}; run python3 programs/build.py')
HV = json.loads((ROOT / 'hive/registry/hive.json').read_text(encoding='utf-8'))
AG = {a['id']: a for a in HV['agents']}

# ---- strings, strict: every prog.* key of en must be non-empty in all 8 locales ----
I18N = {}
EN_ALL = json.loads((ROOT / 'i18n/locales/en.json').read_text(encoding='utf-8'))
KEYS = sorted(k for k in EN_ALL['strings'] if k.startswith('prog.'))
need(len(KEYS) > 40, 'the prog.* keys are missing from i18n/locales/en.json')
for f in sorted((ROOT / 'i18n/locales').glob('*.json')):
    c = json.loads(f.read_text(encoding='utf-8'))
    s = c['strings']
    miss = [k for k in KEYS if not isinstance(s.get(k), str) or not s[k].strip()]
    need(not miss, f'locale {f.name} is missing {miss[:5]}')
    I18N[c['locale']] = {'dir': c['dir'], 'strings': {k: s[k] for k in KEYS}}
need(len(I18N) == 8, f'expected 8 locales, found {sorted(I18N)}')
EN = I18N['en']['strings']


def T(k, tag='span', attrs=''):
    need(k in EN, f'no i18n key {k}')
    return f'<{tag}{attrs} data-i18n="{k}">{E(EN[k])}</{tag}>'


def TN(k, n, tag='span'):
    """a counted label: the number rides in data-n and the locale template fills {n}"""
    need(k in EN and '{n}' in EN[k], f'{k} is not a {{n}} template')
    return f'<{tag} data-i18n-n="{k}" data-n="{int(n)}">{E(EN[k].replace("{n}", str(int(n))))}</{tag}>'


def V(s, tag='span', attrs=''):
    """registry text, verbatim, in English"""
    return f'<{tag} lang="en" dir="ltr"{attrs}>{E(s)}</{tag}>'


def rel(href):
    need(href.startswith('web/'), f'href {href} is not under web/')
    target = href[4:]
    need((HERE / target.split('?')[0].split('#')[0]).exists(), f'link target {target} does not exist')
    return target


WORLD_KEY = {'campus': 'prog.world.campus', 'parishes': 'prog.world.parishes', 'wilds': 'prog.world.wilds',
             'smiles': 'prog.world.smiles', 'bay': 'prog.world.bay'}


# ---------------------------------------------------------------- K-12 pathways
def band_panel(b):
    c = b['counts']
    adv = [AG[a] for a in b['agents'] if AG[a]['kind'] == 'advisor']
    roles = {}
    for a in b['agents']:
        if AG[a]['kind'] == 'npc':
            roles[AG[a]['role']] = roles.get(AG[a]['role'], 0) + 1
    meet = (f'<p>{TN("prog.count.agents", c["agents"])}</p><ul class="chips">'
            + ''.join(f'<li>{E(a["glyph"])} {V(a["name"])}</li>' for a in adv)
            + ''.join(f'<li>{V(r)} × {n}</li>' for r, n in roles.items()) + '</ul>')
    courses = ''.join(
        f'<li data-course="{E(x["course"])}">{V(x["title"], "b")}: '
        + ', '.join(f'<a lang="en" dir="ltr" href="trade_craft_courses.html?lesson={E(l["id"])}#course-sup">{E(l["title"])}</a>' for l in x['lessons'])
        + '</li>' for x in b['courses'])
    mods = ''.join(
        f'<li data-module="{E(m["module"])}">{V(m["hall_name"], "b")}: '
        + ', '.join(V(l['title']) for l in m['lessons'])
        + ' · ' + ' '.join(f'<span class="tag" data-i18n="{WORLD_KEY[w]}">{E(EN[WORLD_KEY[w]])}</span>' for w in m['worlds']) + '</li>'
        for m in b['modules'])
    cx = ''.join(
        f'<li data-cx="{E(x["cx_module"])}">{V(x["pack"] + " · " + x["name"], "b")} {TN("prog.count.blocks", len(x["blocks"]))}'
        f'<div class="cxq">{V(x["first"]["theme"], "q")} <small>{E(x["first"]["block_id"])} · {E(x["first"]["band"])}</small><br>'
        f'{T("prog.cx.try", "em")}: {V(x["first"]["transfer_check"])}</div></li>'
        for x in b['cognitionx'])
    return f'''<section class="band box" data-band="{E(b["band"])}" aria-labelledby="band-{E(b["band"])}">
<h3 id="band-{E(b["band"])}">{E(b["band"])} · {V(b["level"])}</h3>
<p><b data-i18n="prog.offer">{E(EN["prog.offer"])}</b>: {V(b["offer"], "q")}</p>
<p class="counts">{TN("prog.count.courses", c["courses"])} · {TN("prog.count.lessons", c["lessons"])} ({TN("prog.count.held", c["lessons_held"])}) · {TN("prog.count.modules", c["modules"])} · {TN("prog.count.blocks", c["blocks"])} ({TN("prog.count.held", c["blocks_held"])}) · {TN("prog.count.cards", c["cards"])}</p>
<ol class="program">
<li><details open><summary>{T("prog.step.meet")}</summary>{meet}</details></li>
<li><details><summary>{T("prog.step.courses")} · {TN("prog.count.courses", c["courses"])}</summary><ul class="list">{courses}</ul></details></li>
<li><details><summary>{T("prog.step.modules")} · {TN("prog.count.modules", c["modules"])}</summary><ul class="list">{mods}</ul></details></li>
<li><details><summary>{T("prog.step.cx")} · {TN("prog.count.blocks", c["blocks"])}</summary><p class="muted small">{T("prog.cx.attr")}</p><ul class="list">{cx}</ul></details></li>
</ol>
</section>'''


# ---------------------------------------------------------------- teacher cards
def card(c):
    g = c['greeter']
    does = ''.join(f'<li>{V(d["text"])}</li>' for d in c['does'])
    lessons = ''.join(f'<li><a lang="en" dir="ltr" href="trade_craft_courses.html?lesson={E(l["id"])}#course-sup">{E(l["title"])}</a></li>' for l in c['lessons'])
    where = ''.join(f'<li><span class="tag" data-i18n="{WORLD_KEY[w["world"]]}">{E(EN[WORLD_KEY[w["world"]]])}</span> '
                    f'<a lang="en" dir="ltr" href="{E(rel(w["href"]))}">{E(w["title"])}</a></li>' for w in c['where'])
    course = (f' · <a href="trade_craft_courses.html" data-i18n="prog.card.course">{E(EN["prog.card.course"])}</a>' if c['course'] else '')
    return f'''<article class="pcard" data-card="{E(c["id"])}" data-band="{E(c["band"])}">
<h3>{V(c["hall_name"])} <span class="tag">{E(c["band"])} · {V(c["level"])}</span></h3>
<h4 data-i18n="prog.card.does">{E(EN["prog.card.does"])}</h4><ul>{does}</ul>
<h4 data-i18n="prog.card.lessons">{E(EN["prog.card.lessons"])}</h4><ul>{lessons}</ul>
<h4 data-i18n="prog.card.where">{E(EN["prog.card.where"])}</h4><ul class="where">{where}</ul>
<h4 data-i18n="prog.card.greeter">{E(EN["prog.card.greeter"])}</h4>
<p class="greeter" data-agent="{E(g["id"])}">{E(AG[g["id"]]["glyph"])} {V(g["name"], "b")} · {V(g["role"])}<br>{V(g["opener"]["text"], "q")}</p>
<p class="small"><a href="trade_craft_hive.html?classroom=1" data-i18n="prog.card.meet">{E(EN["prog.card.meet"])}</a>{course}</p>
</article>'''


# ---------------------------------------------------------------- sectors
def sector(s):
    def block(key, items, why_key=None):
        if items:
            return f'<div class="sec-row"><h4 data-i18n="{key}">{E(EN[key])}</h4><ul class="chips">{items}</ul></div>'
        why = s.get('empty_why', {}).get(why_key or '', '')
        need(why, f'sector {s["id"]} has an empty {key} without a stated reason')
        return f'<div class="sec-row"><h4 data-i18n="{key}">{E(EN[key])}</h4><p class="muted">{T("prog.sec.none")}: {V(why)}</p></div>'

    quotes = ''.join(f'<li>{V(q["text"], "q")}</li>' for q in s['quotes'])
    extra = ''
    if 'programmes' in s:
        extra += block('prog.sec.programmes', ''.join(f'<li>{V(p["name"])}</li>' for p in s['programmes']))
    if 'paths' in s:
        extra += block('prog.sec.paths', ''.join(f'<li>{V(p["label"])} · {V(p["status"])}</li>' for p in s['paths']))
    if 'sites' in s:
        extra += block('prog.sec.sites', ''.join(f'<li>{V(x["name"])} <small lang="en" dir="ltr">({E(x["org"])})</small></li>' for x in s['sites']))
    scen = ''.join(f'<li>{V(x.get("title") or x["id"])}</li>' for x in s['scenarios'])
    halls = ''.join(f'<li>{V(h["hall_name"])}</li>' for h in s['halls'])
    courses = ''.join(f'<li>{V(c)}</li>' for c in s['courses'])
    agents = ''.join(f'<li>{V(AG[a]["name"])}</li>' for a in s['agents'])
    worlds = ''.join(f'<li><a href="{E(w["href"])}" data-i18n="{WORLD_KEY[w["id"]]}">{E(EN[WORLD_KEY[w["id"]]])}</a> {V(w["title"], "small")}</li>' for w in s['worlds'])
    cx = ''.join(f'<li>{V(p["slug"])} {TN("prog.count.blocks", p["blocks"])}</li>' for p in s['cognitionx_packs'])
    return f'''<article class="sector box" data-sector="{E(s["id"])}">
<h3><span data-i18n="prog.sec.{E(s["id"])}">{E(EN["prog.sec." + s["id"]])}</span> <span class="tag warn" data-i18n="prog.sec.status">{E(EN["prog.sec.status"])}</span></h3>
<h4 data-i18n="prog.sec.quotes">{E(EN["prog.sec.quotes"])}</h4><ul class="quotes">{quotes}</ul>
{extra}
<details><summary><span data-i18n="prog.sec.scenarios">{E(EN["prog.sec.scenarios"])}</span> ({len(s["scenarios"])})</summary><ul class="chips">{scen}</ul></details>
{block("prog.sec.halls", halls, "halls")}
<details><summary><span data-i18n="prog.sec.courses">{E(EN["prog.sec.courses"])}</span> ({len(s["courses"])})</summary>{block("prog.sec.courses", courses, "courses")}</details>
{block("prog.sec.agents", agents, "agents")}
{block("prog.sec.worlds", worlds)}
{block("prog.sec.cx", cx, "cognitionx_packs")}
</article>'''


for w in {w['href'] for s in REG['sectors'] for w in s['worlds']}:
    need((HERE / w).exists(), f'sector world page {w} does not exist')

bands_html = ''.join(band_panel(b) for b in REG['bands'])
# ACCESS BEGIN world-place (wave 19, ACCESS·Internal & External Access): each K-12 card place that names a WORLD PLACE
# gets a second link that lands on that place (the card's own page link is kept as it is). From registry data only:
#   - parishes station 'parish:<fips>/<sid>' and K-12 path step 'k12:<fips>/<n>' (layers/registry/paths.json
#     parishes[fips].paths[id=k12].steps[n-1].id): the station's world_m in layers/registry/layers.json ->
#     trade_craft_parishes.html?at=<e>,<-n + 6>,0 (6 m south of the kiosk, facing it; the world page reads ?at=);
#   - wilds site 'wilds:<world>/<site>' (wilds/registry/wilds.json) -> trade_craft_wilds.html#<world>/<site> (the wilds
#     page's own deep link: it stands the walker at the site with its panel open).
# A place the registries cannot resolve stops the build by name. Page marker: data-world-place.
_WP_LAY = {p['fips']: {s['id']: s for s in p['stations']} for p in json.loads((ROOT / 'layers/registry/layers.json').read_text())['parishes']}
_WP_PATHS = {p['fips']: p['paths'] for p in json.loads((ROOT / 'layers/registry/paths.json').read_text())['parishes']}
_WP_WILDS = {w['id']: {s['id'] for s in w['sites']} for w in json.loads((ROOT / 'wilds/registry/wilds.json').read_text())['worlds']}


def _wp_href(w):
    kind, rest = w['id'].split(':', 1)
    if kind in ('parish', 'k12'):
        fips, tail = rest.split('/', 1)
        need(fips in _WP_LAY, f'world place {w["id"]}: parish {fips} has no layers station list')
        if kind == 'k12':
            k = [p for p in _WP_PATHS.get(fips, []) if p['id'] == 'k12']
            need(len(k) == 1 and 1 <= int(tail) <= len(k[0]['steps']), f'world place {w["id"]}: no k12 step {tail} in paths.json')
            tail = k[0]['steps'][int(tail) - 1]['id']
        st = _WP_LAY[fips].get(tail)
        need(st is not None, f'world place {w["id"]}: station {tail} is not in layers.json')
        e, n = st['world_m']
        return f'trade_craft_parishes.html?at={e:.1f},{-n + 6:.1f},0'
    if kind == 'wilds':
        wid, sid = rest.split('/', 1)
        need(sid in _WP_WILDS.get(wid, set()), f'world place {w["id"]}: site {sid} is not in wilds.json world {wid}')
        return f'trade_craft_wilds.html#{wid}/{sid}'
    return None


_wp_card0 = card


def card(c):
    out, pos = _wp_card0(c), 0
    for w in c['where']:   # the card writes its places in order: walk them with a cursor (titles can repeat)
        a = f'<a lang="en" dir="ltr" href="{E(rel(w["href"]))}">{E(w["title"])}</a></li>'
        i = out.find(a, pos)
        need(i >= 0, f'world place {w["id"]}: its card link is missing in card {c["id"]}')
        pos = i + len(a)
        h = _wp_href(w)
        if h is None:
            continue
        go = (f' <a class="go-place" data-world-place="{E(w["id"])}" href="{E(h)}" lang="en" dir="ltr" '
              f'aria-label="Go to {E(w["title"])} in the world">&#8982; go</a>')
        out = out[:pos - 5] + go + out[pos - 5:]
        pos += len(go)
    return out
# ACCESS END world-place
cards_html = ''.join(card(c) for c in REG['cards'])
sectors_html = ''.join(sector(s) for s in REG['sectors'])
band_opts = ''.join(f'<option value="{E(b["band"])}">{E(b["band"])} · {E(b["level"])}</option>' for b in REG['bands'])
H = REG['honesty']
honesty = ''.join(f'<li>{T(k)}</li>' for k in ('prog.honesty.proposed', 'prog.honesty.un', 'prog.honesty.accredited', 'prog.honesty.play', 'prog.honesty.derived'))
reg_honesty = ''.join(f'<li>{V(x["text"])} <small lang="en" dir="ltr">{E(x["source"])}</small></li>' for x in (H['districts'], H['cognitionx'], H['standards']))
districts = ''.join(f'<li>{V(d["district"])}: {V(d["status"])}</li>' for d in REG['districts'])
rules = ''.join(f'<li><b lang="en">{E(k)}</b>: {V(v)}</li>' for k, v in REG['rules'].items() if isinstance(v, str))
A = REG['attribution']
links = ''.join(f'<li><a href="{f}">{V(t)}</a></li>' for f, t in (
    ('trade_craft_schools.html', 'Schools'), ('trade_craft_classroom.html', 'Classroom'), ('trade_craft_courses.html', 'Courses'),
    ('trade_craft_hive.html', 'Omega Hive'), ('trade_craft_smiles.html', 'Smiles'), ('trade_craft_parishes.html', 'Parishes'),
    ('trade_craft_bay.html', 'Bay')))
for f in ('trade_craft_schools.html', 'trade_craft_classroom.html', 'trade_craft_courses.html', 'trade_craft_hive.html',
          'trade_craft_smiles.html', 'trade_craft_parishes.html', 'trade_craft_bay.html'):
    need((HERE / f).exists(), f'linked page {f} does not exist')

PAGE_JS = r'''(function () {
  'use strict';
  var I = JSON.parse(document.getElementById('prog-i18n').textContent);
  var q = new URLSearchParams(location.search), loc = 'en', want = q.get('lang');
  if (want && Object.prototype.hasOwnProperty.call(I, want)) loc = want;
  else {
    var prefs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || 'en'];
    for (var i = 0; i < prefs.length; i++) { var c = String(prefs[i]).slice(0, 2).toLowerCase(); if (Object.prototype.hasOwnProperty.call(I, c)) { loc = c; break; } }
  }
  var L = I[loc], S = L.strings;
  document.documentElement.lang = loc; document.documentElement.dir = L.dir;
  document.querySelectorAll('[data-i18n]').forEach(function (el) {
    var s = S[el.getAttribute('data-i18n')];
    if (typeof s !== 'string') throw new Error('programs i18n: ' + loc + ' has no ' + el.getAttribute('data-i18n'));
    el.textContent = s;
  });
  document.querySelectorAll('[data-i18n-n]').forEach(function (el) {
    el.textContent = S[el.getAttribute('data-i18n-n')].replace('{n}', el.getAttribute('data-n'));
  });
  /* the band filter: one band's pathway and its cards; nothing is stored */
  var pick = document.getElementById('prog-band');
  function show(band) {
    var n = 0;
    document.querySelectorAll('section.band').forEach(function (s) { s.hidden = !!band && s.getAttribute('data-band') !== band; });
    document.querySelectorAll('article.pcard').forEach(function (c) { var hit = !band || c.getAttribute('data-band') === band; c.hidden = !hit; if (hit) n++; });
    document.getElementById('prog-shown').textContent = S['prog.shown'].replace('{n}', String(n));
    return n;
  }
  pick.addEventListener('change', function () { show(pick.value); });
  var first = q.get('band');
  if (first && pick.querySelector('option[value="' + CSS.escape(first) + '"]')) pick.value = first;
  window.__programsPage = { locale: loc, dir: L.dir, show: show, bands: document.querySelectorAll('section.band').length,
    cards: document.querySelectorAll('article.pcard').length, sectors: document.querySelectorAll('article.sector').length };
  show(pick.value);
})();'''

I18N_JSON = json.dumps(I18N, ensure_ascii=False).replace('</', '<\\/')
tcss, tjs = theme('doc')
NAV = nav_html(PAGE, nav_labels('en'))
ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' "
        "fill='%230C1113'/%3E%3Cpath d='M6 24 l6-10 l5 6 l4-6 l5 10 z' fill='none' stroke='%23E8A33D' stroke-width='2.2' stroke-linejoin='round'/%3E"
        "%3Ccircle cx='22' cy='9' r='3' fill='%2341C4D4'/%3E%3C/svg%3E")
C = REG['counts']
page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="{ICON}">
<title>Programs</title>
<script id="style-head-js">{STYLE_HEAD_JS}</script>
<style>{NAV_CSS}</style>
<style id="tc-css">{tcss}</style>
<style>
body{{font:16px/1.6 "IBM Plex Sans",system-ui,sans-serif}}
.wrap{{max-width:1100px;margin:0 auto;padding:28px 16px 120px}}
.box{{border:1px solid var(--line,#2a3236);border-radius:10px;padding:14px 16px;margin:14px 0;background:var(--panel,transparent)}}
.honesty{{border-color:#E8A33D}}
.honesty li{{margin:4px 0}}
.muted{{opacity:.78}} .small{{font-size:.9em}}
.tag{{display:inline-block;font-size:.78em;padding:1px 8px;border:1px solid currentColor;border-radius:999px;opacity:.85;white-space:nowrap}}
.tag.warn{{color:inherit;opacity:1;border-color:#E8A33D}}
/* list links are tap targets on a phone: at least 32 px tall */
li a{{display:inline-flex;align-items:center;min-block-size:32px}}
.chips{{display:flex;flex-wrap:wrap;gap:6px 14px;list-style:none;padding:0;margin:6px 0}}
.list li{{margin:6px 0}}
.program>li{{margin:8px 0}}
summary{{cursor:pointer;font-weight:600}}
q,.q{{font-style:italic}}
.cxq{{margin:4px 0 8px;padding-inline-start:10px;border-inline-start:3px solid #41C4D4}}
.cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}}
.pcard{{border:1px solid var(--line,#2a3236);border-radius:10px;padding:12px 14px;min-width:0}}
.pcard h3{{margin:0 0 6px;font-size:1.05em}} .pcard h4{{margin:10px 0 2px;font-size:.92em}}
.pcard ul{{margin:2px 0;padding-inline-start:18px}}
.greeter{{margin:4px 0}}
.sectors{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px}}
.sector h4{{margin:10px 0 2px;font-size:.92em}}
.quotes li{{margin:4px 0}}
a,li,p,q{{overflow-wrap:anywhere}}
label select{{margin-inline-start:6px}}
@media (max-width:480px){{.cards,.sectors{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
{NAV}
<main class="wrap" id="main">
<h1 data-i18n="prog.title">{E(EN["prog.title"])}</h1>
<p data-i18n="prog.lead">{E(EN["prog.lead"])}</p>
<section class="box honesty" id="prog-honesty" aria-labelledby="prog-h-honesty"><h2 id="prog-h-honesty" data-i18n="prog.honesty.h">{E(EN["prog.honesty.h"])}</h2>
<ul>{honesty}</ul><ul class="small muted">{reg_honesty}</ul><ul class="small">{districts}</ul></section>
<section class="box" id="prog-find"><label>{T("prog.f.band")} <select id="prog-band"><option value="" data-i18n="prog.f.any">{E(EN["prog.f.any"])}</option>{band_opts}</select></label>
<span class="muted" id="prog-shown" aria-live="polite"></span></section>
<section id="prog-k12" aria-labelledby="prog-h-k12"><h2 id="prog-h-k12" data-i18n="prog.h.k12">{E(EN["prog.h.k12"])}</h2>
<p data-i18n="prog.k12.intro">{E(EN["prog.k12.intro"])}</p>{bands_html}</section>
<section id="prog-cards" aria-labelledby="prog-h-cards"><h2 id="prog-h-cards" data-i18n="prog.h.cards">{E(EN["prog.h.cards"])}</h2>
<p data-i18n="prog.cards.intro">{E(EN["prog.cards.intro"])}</p><p class="small muted" data-i18n="prog.card.muted">{E(EN["prog.card.muted"])}</p>
<div class="cards">{cards_html}</div></section>
<section id="prog-sectors" aria-labelledby="prog-h-sectors"><h2 id="prog-h-sectors" data-i18n="prog.h.sectors">{E(EN["prog.h.sectors"])}</h2>
<p data-i18n="prog.sectors.intro">{E(EN["prog.sectors.intro"])}</p><div class="sectors">{sectors_html}</div></section>
<section class="box" id="prog-rules" aria-labelledby="prog-h-rules"><h2 id="prog-h-rules" data-i18n="prog.h.rules">{E(EN["prog.h.rules"])}</h2><ul class="small">{rules}</ul>
<p class="small muted" lang="en">{E(A["text"])} · {E(A["license"])} · <a href="{E(A["license_url"])}" rel="license noopener">{E(A["license_url"])}</a> · <a href="{E(A["repo"])}" rel="noopener">{E(A["repo"])}</a> @ {E(A["commit"][:12])}</p></section>
<section class="box" id="prog-links" aria-labelledby="prog-h-links"><h2 id="prog-h-links" data-i18n="prog.h.links">{E(EN["prog.h.links"])}</h2><ul class="chips">{links}</ul></section>
<p class="muted small">programs/registry/programs.json · {E(REG["schema"])} · stamp <code data-stamp>{E(REG["source_stamp"])}</code></p>
</main>
<script type="application/json" id="prog-i18n">{I18N_JSON}</script>
<script id="prog-page">{PAGE_JS}</script>
<script>{tjs}</script>
<script id="style-js">{STYLE_JS}</script>
</body>
</html>
'''
TITLE = 'SmartCiti.X : Trade Craft Academy — ' + EN['prog.nav']
page = apply_seo(page, PAGE, TITLE, EN['prog.seo.desc'], 'page')
emit(HERE / 'trade_craft_programs.html', page,
     f'{C["bands"]} bands | {C["cards"]} cards | {C["sectors"]} sectors | {C["allow_list_agents"]} allow-listed agents | stamp {REG["source_stamp"]}')
