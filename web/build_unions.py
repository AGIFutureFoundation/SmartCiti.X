#!/usr/bin/env python3
"""The union hall directory: web/trade_craft_unions.html (wave 18).

Reads unionpaths/registry/union_paths.json (python3 unionpaths/build.py): one ordered path per union hall - its trade
course, its lessons in ladder order, its simulator seats, its tool crib, its Omega Hive advisor and its crews - plus
the per-district and per-cohort rollups. Filters by district, cohort and focus. Each hall card links to the hall in
3D, its course, one supplement per lesson and its advisor on the Hive page; a Speak button says the advisor's opening
line, quoted from hive/registry/hive.json with its source, through web/hivekit.py's on-device voice (SCRIPTED, no AI
model, only on a click).

Honesty: the registries' own honesty lines are quoted verbatim; a union named here is not a partner or affiliate; no
apprenticeship hours, wages, credentials, membership or affiliation is shown, because none is recorded; any tie to a real
programme stays PROPOSED. Every chrome word comes from the union.* i18n keys (8 locales). Page markers are neutral
(UNION-PATH). The page saves nothing and sends nothing (the voice kit remembers its own mute switch, as on the Hive page).
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
from hivekit import hive_data, hive_i18n_keys, hive_registry, HIVE_JS, js_json  # noqa: E402
import sitenav  # noqa: E402

PAGE = 'web/trade_craft_unions.html'
E = lambda s: html.escape(str(s), quote=True)


class UnionPageError(Exception):
    pass


def need(c, m):
    if not c:
        raise UnionPageError('build_unions: ' + m)


need(PAGE in sitenav.PAGES, f'{PAGE} is not declared in web/sitenav.py GROUPS (nav.page.unions)')
REG = json.loads((ROOT / 'unionpaths/registry/union_paths.json').read_text(encoding='utf-8'))
for k in ('source_stamp', 'schema', 'honesty', 'honesty_quoted', 'rules', 'counts', 'halls', 'by_district', 'by_cohort', 'cohorts'):
    need(k in REG, f'union_paths.json has no {k!r}; run python3 unionpaths/build.py')
CNT, HALLS = REG['counts'], REG['halls']
need(len(HALLS) == CNT['halls'], 'the hall list and its count disagree')

# ---- strings, strict: every union.* key (and the voice keys borrowed from the Hive) non-empty in all 8 locales ----
EN_ALL = json.loads((ROOT / 'i18n/locales/en.json').read_text(encoding='utf-8'))
KEYS = sorted([k for k in EN_ALL['strings'] if k.startswith('union.')] + hive_i18n_keys())
need(len(KEYS) > 50, 'the union.* keys are missing from i18n/locales/en.json')
I18N = {}
for f in sorted((ROOT / 'i18n/locales').glob('*.json')):
    c = json.loads(f.read_text(encoding='utf-8'))
    s = c['strings']
    miss = [k for k in KEYS if not isinstance(s.get(k), str) or not s[k].strip()]
    need(not miss, f'locale {f.name} is missing {miss[:5]}')
    I18N[c['locale']] = {'dir': c['dir'], 'strings': {k: s[k] for k in KEYS},
                         'tiers': dict(c['tiers']), 'districts': {d: c['districts'][d]['name'] for d in REG['districts']}}
need(len(I18N) == 8, f'expected 8 locales, found {sorted(I18N)}')
EN = I18N['en']['strings']
for co in REG['cohorts']:
    need(f'union.cohort.{co}' in EN, f'cohort {co} has no union.cohort.{co} key')

# ---- the voice: the advisors the paths name, from the hive registry (lines once, agents pointing at them) ----
ADV_IDS = sorted({h['advisor']['id'] for h in HALLS})
HV = hive_data(ids=set(ADV_IDS), with_cfg=False)
HV_BY = {a['id']: a for a in HV['agents']}
AGENT_NAME = {a['id']: a['name'] for a in hive_registry()['agents']}   # crew roles and advisors, READ
need(sorted(HV_BY) == ADV_IDS, f'the hive registry lacks an advisor a path names: {sorted(set(ADV_IDS) - set(HV_BY))}')


def T(k, tag='span', attrs=''):
    need(k in EN, f'unknown key {k}')
    return f'<{tag}{attrs} data-i18n="{k}">{E(EN[k])}</{tag}>'


def TIER(t):
    return f'<span data-i18n-tier="{E(t)}">{E(EN_ALL["tiers"][t])}</span>'


def DIST(d):
    return f'<span data-i18n-district="{E(d)}">{E(EN_ALL["districts"][d]["name"])}</span>'


def rel(p):
    need(p.startswith('web/'), f'link {p} is not a page under web/')
    f = p[len('web/'):]
    need((HERE / f.split('?')[0].split('#')[0]).exists(), f'link {p} names a page that does not exist')
    return f


def card(h):
    L = h['links']
    les = ''.join(
        f'<li data-lesson="{E(l["lesson"])}"><a href="trade_craft_lessons.html#lesson-{E(l["lesson"])}">{E(l["title"])}</a> '
        f'<span class="muted">· {E(l["room_label"])} · {TIER(l["tier"])} · {l["steps"]} {T("union.p.steps")}</span> '
        f'<a class="pill" data-link="supp" href="{E(rel(sl))}">{T("union.p.supp")}</a></li>'
        for l, sl in zip(h['lessons'], L['supplements']))
    if h['seats']:
        seats = ', '.join(f'<a class="pill" data-link="seat" href="trade_craft_3d.html?hall={E(h["hall"])}&amp;sim={E(s["sim"])}">{E(s["name"])}</a>'
                          for s in h['seats'])
    else:
        seats = T('union.p.noseat', 'span', ' class="muted"')
    a = h['advisor']
    hv = HV_BY[a['id']]
    door = f' <span class="muted" data-door="1">{T("union.p.door")}</span>' if a['rule'] == 'door' else ''
    if a['also']:
        door += (f' <span class="muted" data-also="1">{T("union.p.also")}: '
                 + ', '.join(f'<a data-link="advisor-also" href="trade_craft_hive.html?agent={E(x)}">{E(AGENT_NAME[x])}</a>' for x in a['also'])
                 + '</span>')
    adv = (f'{E(hv["glyph"])} <b>{E(a["name"])}</b> <span class="tag">SCRIPTED</span> '
           f'<a class="pill" data-link="advisor" href="{E(rel(L["advisor"]))}">{T("union.a.hive")}</a> '
           f'<button type="button" class="btn speak" data-speak="{E(a["id"])}">{T("hive.speak")}</button>{door}')
    if h['crews']:
        crews = '<ul class="crews">' + ''.join(
            f'<li data-crew="{E(c["crew"])}"><b>{E(c["name"])}</b> <span class="muted">· {E(next(s["name"] for s in h["seats"] if s["sim"] == c["seat"]))}</span> '
            + ' '.join(f'<a class="pill" data-link="crew-role" href="trade_craft_hive.html?agent={E(r)}">{E(AGENT_NAME[r])}</a>' for r in c['roles'])
            + '</li>' for c in h['crews']) + '</ul>'
    else:
        crews = T('union.p.nocrew', 'span', ' class="muted"')
    text = ' '.join([h['name'], h['focus'], h['hall'], h['district_name']]).lower()
    return (f'<article class="uh" id="hall-{E(h["hall"])}" data-hall="{E(h["hall"])}" data-district="{E(h["district"])}" '
            f'data-cohort="{E(h["cohort"])}" data-text="{E(text)}">'
            f'<h3>{E(h["name"])}</h3>'
            f'<p class="muted">{E(h["focus"])} · {DIST(h["district"])} · {T("union.cohort." + h["cohort"])} · {E(h["campus_name"])}</p>'
            f'<ol class="upath" data-path-steps="{len(h["path"])}">'
            f'<li data-step="course"><b>{T("union.p.course")}</b> <a data-link="course" href="{E(rel(L["course"]))}">{E(h["name"])}</a> '
            f'<code>{E(h["course"])}</code></li>'
            f'<li data-step="lessons"><b>{T("union.p.lessons")}</b><ol class="les">{les}</ol></li>'
            f'<li data-step="seats"><b>{T("union.p.seats")}</b> {seats}</li>'
            f'<li data-step="crib"><b>{T("union.p.crib")}</b> {E(h["crib"]["name"])} <code>{E(h["crib"]["crib"])}</code></li>'
            f'<li data-step="advisor"><b>{T("union.p.advisor")}</b> {adv}</li>'
            f'<li data-step="crews"><b>{T("union.p.crews")}</b> {crews}</li></ol>'
            f'<p class="acts"><a class="pill" data-link="hall3d" href="{E(rel(L["hall3d"]))}">{T("union.a.walk3d")}</a> '
            f'<a class="pill" data-link="course-open" href="{E(rel(L["course"]))}">{T("union.a.course")}</a> '
            f'<a class="pill" data-link="ladder" href="{E(rel(L["ladder"]))}">{T("union.a.ladder")}</a></p></article>')


halls_html = ''.join(card(h) for h in HALLS)
need(halls_html.count('<article class="uh"') == CNT['halls'], 'a hall has no card')


def rollup_rows(rows, key, label):
    out = ''
    for r in rows:
        out += (f'<tr data-rollup="{E(r[key])}"><th scope="row"><a href="?{key}={E(r[key])}#union-halls">{label(r)}</a></th>'
                f'<td data-n="halls">{r["count"]}</td><td data-n="lessons">{r["lessons"]}</td><td data-n="seats">{r["halls_with_seats"]}</td>'
                f'<td data-n="crews">{r["halls_with_crews"]}</td><td data-n="door">{r["halls_door_advisor"]}</td>'
                f'<td data-n="advisors">{len(r["advisors"])}</td></tr>')
    return out


HEAD = ''.join(T(k, 'th', ' scope="col"') for k in ('union.r.halls', 'union.r.lessons', 'union.r.seats', 'union.r.crews', 'union.r.door', 'union.r.advisors'))
tot = (f'<tr data-rollup="all"><th scope="row">{T("union.r.total")}</th><td data-n="halls">{CNT["halls"]}</td><td data-n="lessons">{CNT["lessons"]}</td>'
       f'<td data-n="seats">{CNT["halls_with_seats"]}</td><td data-n="crews">{CNT["halls_with_crews"]}</td><td data-n="door">{CNT["halls_door_advisor"]}</td>'
       f'<td data-n="advisors">{CNT["advisors_used"]}</td></tr>')
rollups = (f'<div class="tw"><table id="union-by-district"><thead><tr><th scope="col">{T("union.f.district")}</th>{HEAD}</tr></thead><tbody>'
           + rollup_rows(REG['by_district'], 'district', lambda r: DIST(r['district'])) + f'</tbody><tfoot>{tot}</tfoot></table></div>'
           f'<div class="tw"><table id="union-by-cohort"><thead><tr><th scope="col">{T("union.f.cohort")}</th>{HEAD}</tr></thead><tbody>'
           + rollup_rows(REG['by_cohort'], 'cohort', lambda r: T('union.cohort.' + r['cohort']) + f' <code>{E(r["cohort"])}</code>')
           + f'</tbody><tfoot>{tot}</tfoot></table></div>')

stats = ''.join(f'<div class="st"><dt>{T(k)}</dt><dd data-union-count="{c}">{CNT[c]}</dd></div>' for k, c in (
    ('union.s.halls', 'halls'), ('union.s.districts', 'districts'), ('union.s.lessons', 'lessons'),
    ('union.s.steps', 'path_steps'), ('union.s.seats', 'halls_with_seats'), ('union.s.crews', 'halls_with_crews')))
honest = (''.join(f'<li>{T(k)}</li>' for k in ('union.hon.partner', 'union.hon.invented', 'union.hon.proposed', 'union.hon.lessons', 'union.hon.voice'))
          + f'</ul><p>{T("union.hon.quoted")}</p><ul class="quotes">'
          + ''.join(f'<li data-quote-src="{E(q["source"])}" lang="en"><q>{E(q["text"])}</q> <cite class="muted">{E(q["source"])}</cite></li>'
                    for q in REG['honesty_quoted'])
          + '</ul><ul class="honesty">'
          + ''.join(f'<li data-union-honesty="{E(k)}" lang="en">{E(v)}</li>' for k, v in REG['honesty'].items()))
d_opts = ''.join(f'<option value="{E(d)}" data-i18n-district="{E(d)}">{E(EN_ALL["districts"][d]["name"])}</option>' for d in REG['districts'])
c_opts = ''.join(f'<option value="{E(c)}" data-i18n="union.cohort.{E(c)}">{E(EN["union.cohort." + c])}</option>' for c in REG['cohorts'])
rules = '<dl class="kv">' + ''.join(f'<div><dt><code>{E(k)}</code></dt><dd lang="en">{E(v)}</dd></div>' for k, v in REG['rules'].items()) + '</dl>'
links = ''.join(f'<li><a href="{f}">{T(k)}</a></li>' for f, k in (
    ('trade_craft_courses.html', 'union.l.courses'), ('trade_craft_hive.html', 'union.l.hive'),
    ('trade_craft_3d.html', 'union.l.campus'), ('trade_craft_ladder.html', 'union.l.ladder')))
DATA = {'stamp': REG['source_stamp'], 'schema': REG['schema'], 'counts': CNT}

PAGE_JS = r'''(function () {
  'use strict';
  /* UNION-PATH: the union hall directory - filters, deep links and voice on a click; nothing stored or sent */
  var I = JSON.parse(document.getElementById('union-i18n').textContent);
  var HV = JSON.parse(document.getElementById('union-voice').textContent);
  var q = new URLSearchParams(location.search), loc = 'en', want = q.get('lang');
  if (want && Object.prototype.hasOwnProperty.call(I, want)) loc = want;
  else {
    var prefs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || 'en'];
    for (var i = 0; i < prefs.length; i++) { var c = String(prefs[i]).slice(0, 2).toLowerCase(); if (Object.prototype.hasOwnProperty.call(I, c)) { loc = c; break; } }
  }
  var L = I[loc], S = L.strings;
  function t(k) { if (typeof S[k] !== 'string') throw new Error('union i18n: ' + loc + ' has no ' + k); return S[k]; }
  document.documentElement.lang = loc; document.documentElement.dir = L.dir;
  document.querySelectorAll('[data-i18n]').forEach(function (el) { el.textContent = t(el.getAttribute('data-i18n')); });
  document.querySelectorAll('[data-i18n-tier]').forEach(function (el) { el.textContent = L.tiers[el.getAttribute('data-i18n-tier')]; });
  document.querySelectorAll('[data-i18n-district]').forEach(function (el) { el.textContent = L.districts[el.getAttribute('data-i18n-district')]; });
  var fText = document.getElementById('union-q'), fDist = document.getElementById('union-district'), fCo = document.getElementById('union-cohort');
  fText.placeholder = t('union.f.focus'); fText.setAttribute('aria-label', t('union.f.focus'));
  /* filters: district, cohort and a focus/name search; the URL may preset them (?district= ?cohort= ?q=) */
  var cards = [].slice.call(document.querySelectorAll('article.uh'));
  function filter() {
    var s = fText.value.trim().toLowerCase(), d = fDist.value, co = fCo.value, n = 0;
    cards.forEach(function (el) {
      var hit = (!d || el.getAttribute('data-district') === d) && (!co || el.getAttribute('data-cohort') === co)
        && (!s || el.getAttribute('data-text').indexOf(s) >= 0);
      el.hidden = !hit; if (hit) n++;
    });
    document.getElementById('union-shown').textContent = t('union.f.shown').replace('{n}', String(n));
    document.getElementById('union-empty').hidden = n > 0;
    return n;
  }
  if (q.get('district')) fDist.value = q.get('district');
  if (q.get('cohort')) fCo.value = q.get('cohort');
  if (q.get('q')) fText.value = q.get('q');
  fText.addEventListener('input', filter); fDist.addEventListener('change', filter); fCo.addEventListener('change', filter);
  /* voice: the advisor's opening line, quoted from the hive registry, spoken only on a click */
  var k12 = q.has('classroom') || q.has('class'), byId = {};
  HV.agents.forEach(function (a) { byId[a.id] = a; });
  var status = document.getElementById('union-status'), said = document.getElementById('union-said'), mute = document.getElementById('union-mute');
  function onstate(code) { status.textContent = t('hive.v.' + code); }
  HiveVoice.init(HV, { k12: k12, onstate: onstate });
  function showMute() { mute.setAttribute('aria-pressed', HiveVoice.muted() ? 'true' : 'false'); }
  showMute(); onstate(HiveVoice.muted() ? 'muted' : 'ready');
  mute.addEventListener('click', function () { HiveVoice.setMuted(!HiveVoice.muted()); showMute(); onstate(HiveVoice.muted() ? 'muted' : 'ready'); });
  document.getElementById('union-stop').addEventListener('click', function () { HiveVoice.stop(); });
  function opener(id) {
    var a = byId[id]; if (!a) return null;
    var li = k12 ? a.o12 : a.o, ln = (li === null || li === undefined) ? null : a.lines[li];
    if (!ln || (k12 && (!a.k12 || !ln.safe))) return null;
    return { agent: a, text: HV.texts[ln.t][0], source: HV.texts[ln.t][1] };
  }
  document.getElementById('union-halls').addEventListener('click', function (ev) {
    var b = ev.target.closest && ev.target.closest('[data-speak]');
    if (!b) return;
    if (HiveVoice.muted()) { onstate('muted'); return; }
    var p = opener(b.getAttribute('data-speak'));
    if (!p) { onstate('refused'); return; }
    said.hidden = false;
    said.querySelector('q').textContent = p.text; said.querySelector('code').textContent = p.source;
    HiveVoice.speak([[p.agent, p.text]]);
  });
  window.__unionPage = { locale: loc, dir: L.dir, halls: cards.length, filter: filter, opener: opener, k12: k12 };
  filter();
  if (location.hash && location.hash.indexOf('#hall-') === 0) {
    var el = document.getElementById(location.hash.slice(1));
    if (el) { el.hidden = false; el.scrollIntoView(); }
  }
})();'''

tcss, tjs = theme('doc')
NAV = nav_html(PAGE, nav_labels('en'))
ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' "
        "fill='%230C1113'/%3E%3Cpath d='M6 26 V12 L16 6 L26 12 V26 Z' fill='none' stroke='%23E8A33D' stroke-width='2.2' stroke-linejoin='round'/%3E"
        "%3Cpath d='M12 26 v-7 h8 v7' stroke='%2341C4D4' stroke-width='2.2' fill='none'/%3E%3C/svg%3E")

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="{ICON}">
<title>Union halls</title>
<script id="style-head-js">{STYLE_HEAD_JS}</script>
<style>{NAV_CSS}</style>
<style id="tc-css">{tcss}</style>
<style>
body{{font:16px/1.6 "IBM Plex Sans",system-ui,sans-serif}}
.wrap{{max-width:1100px;margin:0 auto;padding:28px 16px 120px}}
.lede{{color:var(--tc-muted);max-width:72ch}}
main,section,li,p,dd,dt,td,th,q{{overflow-wrap:anywhere}}
.box{{border:1px solid var(--tc-line);border-radius:10px;padding:16px;margin:0 0 20px;background:var(--tc-panel);color:var(--tc-ink);min-inline-size:0}}
.box h2{{margin:0 0 10px;font-size:22px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin:0 0 12px}}
.st{{display:flex;flex-direction:column-reverse}}
.st dt{{color:var(--tc-muted);font-size:13px}}
.st dd{{margin:0;font-size:26px;font-weight:700;font-variant-numeric:tabular-nums}}
.honesty,.quotes{{color:var(--tc-muted);padding-inline-start:20px}}
.honesty li,.quotes li{{margin:4px 0}}
.quotes q{{color:var(--tc-ink)}}
.muted{{color:var(--tc-muted);font-size:14px}}
.tag{{font:600 12px/1.3 ui-monospace,monospace;border:1px solid var(--tc-line);border-radius:4px;padding:2px 6px;color:var(--tc-muted);display:inline-block}}
code{{font:12.5px ui-monospace,monospace}}
a{{color:var(--tc-link)}}
.find{{display:flex;flex-wrap:wrap;gap:10px;align-items:center}}
.find input,.find select{{min-block-size:44px;font:inherit;color:var(--tc-ink);background:var(--tc-raised);border:1px solid var(--tc-line);border-radius:8px;padding:0 10px;max-inline-size:100%;min-inline-size:0}}
.find input{{inline-size:min(360px,100%)}}
.voicebar{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0 0}}
.btn{{min-block-size:44px;padding:0 14px;border-radius:8px;border:1px solid var(--tc-line);background:var(--tc-raised);color:var(--tc-ink);font:inherit;cursor:pointer}}
.btn[aria-pressed="true"]{{border-color:var(--tc-amber)}}
.halls{{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(330px,100%),1fr));gap:12px;align-items:start}}
article.uh{{border:1px solid var(--tc-line);border-radius:8px;padding:10px 12px;background:var(--tc-raised);min-inline-size:0}}
article.uh:target{{outline:3px solid var(--tc-amber);outline-offset:2px}}
article.uh h3{{margin:0;font-size:18px}}
.upath{{padding-inline-start:20px;margin:6px 0}}
.upath>li{{margin:6px 0}}
.les{{padding-inline-start:18px;margin:2px 0}}
.crews{{padding-inline-start:18px;margin:2px 0}}
.pill{{display:inline-flex;align-items:center;min-block-size:32px}}
.acts{{display:flex;flex-wrap:wrap;gap:4px 12px;margin:6px 0 0}}
.acts .pill{{min-block-size:44px}}
.tw{{overflow-x:auto;margin:0 0 12px}}
table{{border-collapse:collapse;min-inline-size:100%;font-variant-numeric:tabular-nums}}
th,td{{border-block-end:1px solid var(--tc-line);padding:6px 8px;text-align:start}}
td{{text-align:end}}
tfoot th,tfoot td{{font-weight:700}}
.kv{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:6px 16px;margin:6px 0}}
.kv dt{{color:var(--tc-muted);font-size:13px}}.kv dd{{margin:0}}
.links a{{display:inline-flex;align-items:center;min-block-size:44px}}
</style>
</head>
<body class="tc-theme">
{NAV}
<main class="wrap" id="union-main">
<header>
{T("union.kicker", "p", ' class="tc-kicker"')}
{T("union.title", "h1", ' class="tc-page-title"')}
{T("union.lede", "p", ' class="lede"')}
<dl class="stats">{stats}</dl>
</header>
<section class="box" id="union-honesty" aria-labelledby="union-h-honest"><h2 id="union-h-honest" data-i18n="union.h.honest">{E(EN["union.h.honest"])}</h2>
<ul class="honesty">{honest}</ul></section>
<section class="box" id="union-find" aria-labelledby="union-h-find"><h2 id="union-h-find" data-i18n="union.h.find">{E(EN["union.h.find"])}</h2>
<div class="find"><input type="search" id="union-q" aria-label="{E(EN["union.f.focus"])}" placeholder="{E(EN["union.f.focus"])}">
<label>{T("union.f.district")} <select id="union-district"><option value="" data-i18n="union.f.any">{E(EN["union.f.any"])}</option>{d_opts}</select></label>
<label>{T("union.f.cohort")} <select id="union-cohort"><option value="" data-i18n="union.f.any">{E(EN["union.f.any"])}</option>{c_opts}</select></label>
<span class="muted" id="union-shown" aria-live="polite"></span></div>
<p class="muted" id="union-empty" hidden>{T("union.empty")}</p>
<p class="voicebar"><button type="button" class="btn" id="union-mute" aria-pressed="false">{T("hive.v.mute")}</button>
<button type="button" class="btn" id="union-stop">{T("hive.v.stop")}</button> <span class="muted" id="union-status" aria-live="polite"></span></p>
<p class="muted" id="union-said" hidden>{T("union.v.quote")} <code></code>: <q lang="en"></q></p></section>
<section class="box" id="union-halls" aria-labelledby="union-h-halls"><h2 id="union-h-halls" data-i18n="union.h.halls">{E(EN["union.h.halls"])}</h2>
<div class="halls">{halls_html}</div></section>
<section class="box" id="union-rollups" aria-labelledby="union-h-rollup"><h2 id="union-h-rollup" data-i18n="union.h.rollup">{E(EN["union.h.rollup"])}</h2>{rollups}</section>
<section class="box" id="union-rules" aria-labelledby="union-h-rules"><h2 id="union-h-rules" data-i18n="union.h.rules">{E(EN["union.h.rules"])}</h2>{rules}</section>
<section class="box links" id="union-links" aria-labelledby="union-h-links"><h2 id="union-h-links" data-i18n="union.h.links">{E(EN["union.h.links"])}</h2><ul>{links}</ul></section>
<p class="muted">unionpaths/registry/union_paths.json · {E(REG["schema"])} · stamp <code data-stamp>{E(REG["source_stamp"])}</code></p>
</main>
<script type="application/json" id="union-data">{js_json(DATA)}</script>
<script type="application/json" id="union-i18n">{js_json(I18N)}</script>
<script type="application/json" id="union-voice">{js_json(HV)}</script>
<script id="hive-kit">{HIVE_JS}</script>
<script id="union-page">{PAGE_JS}</script>
<script>{tjs}</script>
<script id="style-js">{STYLE_JS}</script>
</body>
</html>
'''
# ACCESS BEGIN world-door (wave 19, ACCESS·Internal & External Access): a hall card links to the hall's DOOR in the
# walkable world when the hall has one: campusplan/registry/campusplan.json places a campus in a parish
# (placement.parish, north-up rot_y 0) and the hall has a lot there; the door point is placement world_scene + the lot's
# building.door - the same rule web/build_parishes.py uses for its door markers. The link stands the walker 8 m in front
# of the door, facing it (trade_craft_parishes.html?at=<x>,<z>,<yaw>; the world page reads ?at=). A hall whose campus
# has no parish placement (the Bay outline places only the Oakland campus point; Treasure Island is not placed) gets
# no world-door link. Page marker: data-link="world-door".
_WD_CP = json.loads((ROOT / 'campusplan/registry/campusplan.json').read_text())
_WD = {}
for _k, _c in _WD_CP['campuses'].items():
    _pl = _c['placement']['parish']
    if _pl is None:
        continue
    need(_pl['rot_y'] == 0, f'world door: campus {_k} placement rot_y is not the north-up rule')
    for _lot in _c['lots']:
        _b = _lot['building']
        need(_b['facing'] in ('N', 'S'), f'world door: lot {_lot["id"]} facing {_b["facing"]!r} has no stand rule')
        _dx, _dz = _pl['world_scene']['x'] + _b['door']['x'], _pl['world_scene']['z'] + _b['door']['z']
        _sz, _yaw = (_dz - 8, 3.14) if _b['facing'] == 'N' else (_dz + 8, 0)
        _WD[_lot['hall']] = (f'trade_craft_parishes.html?at={_dx:.1f},{_sz:.1f},{_yaw}', _pl['name'])
for _h, (_href, _pname) in sorted(_WD.items()):
    _i = page.find(f'<article class="uh" id="hall-{_h}"')
    need(_i >= 0, f'world door: hall {_h} has a door but no card')
    _j = page.find('</p></article>', _i)
    need(_j > _i, f'world door: card of {_h} has no actions row')
    page = (page[:_j] + f' <a class="pill" data-link="world-door" href="{E(_href)}" lang="en" dir="ltr" '
            f'aria-label="Go to the {E(_pname)} door of this hall in the walkable world">&#8982; {E(_pname)} door</a>' + page[_j:])
need(page.count('data-link="world-door"') == len(_WD), 'world door: link count differs from the door count')
# ACCESS END world-door
TITLE = 'SmartCiti.X : Trade Craft Academy — ' + EN['union.nav']
page = apply_seo(page, PAGE, TITLE, EN['union.seo.desc'], 'page')
emit(HERE / 'trade_craft_unions.html', page,
     f'{CNT["halls"]} halls | {CNT["path_steps"]} path steps | {CNT["districts"]} districts, {CNT["cohorts"]} cohorts | stamp {REG["source_stamp"]}')
