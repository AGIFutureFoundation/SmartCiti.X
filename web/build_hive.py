#!/usr/bin/env python3
"""The Omega Hive page: web/trade_craft_hive.html.

Built from hive/registry/hive.json (hive/build.py), which connects every scripted figure in the bundle - the hall
advisors and crew roles of agents/ and the NPC guides of npcs/ - to an avatars/ locker outfit, an AUTHORED
personality, an on-device voice profile and the registry lines it quotes.

The page: the honesty block (registry honesty lines verbatim plus the hive.is.* chrome), figures recounted from the
registry, the voice bar (mute, stop, status; nothing speaks until a Speak button is pressed), the council (one
question, up to five agents answer in turn with their best-matching quoted line - web/hivekit.py HiveCore.council, a
fixed word-overlap rule, no model) and the roster (every agent as a card with its portrait, personality, voice and
every line with its source path). Classroom / K-12 mode (?classroom=1 or ?class=...) shows only the play-safe roster,
withholds held lines and starts muted.

Every chrome word is a hive.* i18n key (8 locales, Arabic right-to-left). Names, roles, traits and lines are registry
data shown verbatim. No figure is typed here: each is read from the registry and the build stops on drift.
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
from hivekit import hive_registry, hive_data, portrait_svg, HIVE_CSS, HIVE_JS, hive_i18n_keys, js_json  # noqa: E402
import sitenav  # noqa: E402

PAGE = 'web/trade_craft_hive.html'
E = lambda s: html.escape(str(s), quote=True)


class HivePageError(Exception):
    pass


if PAGE not in sitenav.PAGES:
    raise HivePageError(f'build_hive: {PAGE} is not declared in web/sitenav.py (NEEDS nav: nav.page.hive)')

KINDS = ['advisor', 'crew-role', 'npc']
LINE_KINDS = ['greeting', 'say', 'read', 'job', 'stops', 'knowledge', 'limits']
PAGE_KEYS = (['hive.nav', 'hive.kicker', 'hive.title', 'hive.lede', 'hive.seo.desc', 'hive.h.honest',
              'hive.is.1', 'hive.is.2', 'hive.is.3', 'hive.is.4', 'hive.s.agents', 'hive.s.advisors', 'hive.s.roles',
              'hive.s.npcs', 'hive.s.lines', 'hive.s.models', 'hive.h.voice', 'hive.v.note', 'hive.h.roster', 'hive.f.all',
              'hive.f.search', 'hive.f.shown', 'hive.c.personality', 'hive.c.voice', 'hive.c.pitch', 'hive.c.rate',
              'hive.c.lines', 'hive.c.avatar', 'hive.c.where', 'hive.h.council', 'hive.cn.note', 'hive.cn.ask',
              'hive.cn.go', 'hive.cn.play', 'hive.cn.none', 'hive.cn.short', 'hive.cn.try', 'hive.cn.matched',
              'hive.k12.note', 'hive.h.where', 'hive.l.campus', 'hive.l.parishes', 'hive.src']
             + [f'hive.k.{k}' for k in LINE_KINDS] + [f'hive.kind.{k}' for k in KINDS])
KEYS = list(dict.fromkeys(PAGE_KEYS + hive_i18n_keys()))

I18N = {}
for f in sorted((ROOT / 'i18n/locales').glob('*.json')):
    c = json.loads(f.read_text(encoding='utf-8'))
    s = c['strings']
    miss = [k for k in KEYS if k not in s or not isinstance(s[k], str) or not s[k].strip()]
    if miss:
        raise HivePageError(f'build_hive: locale {f.name} is missing {miss[:5]}')
    I18N[c['locale']] = {'dir': c['dir'], 'strings': {k: s[k] for k in KEYS}}
if len(I18N) != 8:
    raise HivePageError(f'build_hive: expected 8 locales, found {sorted(I18N)}')
EN = I18N['en']['strings']


def T(k, tag='span', attrs=''):
    if k not in EN:
        raise HivePageError(f'build_hive: unknown key {k}')
    return f'<{tag}{attrs} data-i18n="{k}">{E(EN[k])}</{tag}>'


REG = hive_registry()
C = REG['counts']
for k in ('agents', 'advisors', 'crew_roles', 'npcs', 'lines', 'models'):
    if k not in C:
        raise HivePageError(f'build_hive: registry counts have no {k}')
if C['models'] != 0:
    raise HivePageError('build_hive: the registry counts a model - this page cannot say that')
if C['agents'] != len(REG['agents']) or C['agents'] != C['advisors'] + C['crew_roles'] + C['npcs']:
    raise HivePageError('build_hive: registry agent counts drift from the roster')
DATA = hive_data(REG, with_cfg=False)
for a in REG['agents']:
    if a['kind'] not in KINDS:
        raise HivePageError(f'build_hive: {a["id"]} has unknown kind {a["kind"]}')
    for ln in a['lines']:
        if ln['kind'] not in LINE_KINDS:
            raise HivePageError(f'build_hive: {a["id"]} line {ln["id"]} has unknown kind {ln["kind"]}')


def where(a):
    w = a['where']
    return ' · '.join(f'{E(k)} <code>{E(v)}</code>' for k, v in w.items() if v)


def card(a):
    v, p = a['voice'], a['personality']
    first = next((i for i, ln in enumerate(a['lines']) if ln['kind'] == 'greeting'), 0)
    hay = ' '.join([a['name'], a['role'], a.get('crew_name', ''), a.get('parish', '')]).lower()
    return (f'<article class="hv-card" data-agent="{E(a["id"])}" data-kind="{E(a["kind"])}" data-k12="{1 if a["k12"] else 0}" '
            f'data-hay="{E(hay)}" data-character="{E(a["avatar"]["character"])}">'
            f'<div class="hv-head">{portrait_svg(a)}<div class="hv-who"><h3>{E(a["glyph"])} {E(a["name"])}</h3>'
            f'<p class="muted">{E(a["role"])}</p>'
            f'<p><span class="tag" data-i18n="hive.kind.{a["kind"]}">{E(EN["hive.kind." + a["kind"]])}</span> '
            f'<span class="tag">SCRIPTED</span> <span class="tag">{E(p["provenance"])}</span></p></div></div>'
            f'<p class="hv-pers"><b data-i18n="hive.c.personality">{E(EN["hive.c.personality"])}</b>: '
            f'<span data-traits>{E(", ".join(p["traits"]))}</span>. <span data-style>{E(p["style"])}</span></p>'
            f'<p class="hv-av"><b data-i18n="hive.c.avatar">{E(EN["hive.c.avatar"])}</b>: <code>{E(a["avatar"]["character"])}</code> '
            f'{E(a["avatar"]["character_name"])} · <b data-i18n="hive.c.where">{E(EN["hive.c.where"])}</b>: {where(a)}</p>'
            f'<p class="hv-vc"><b data-i18n="hive.c.voice">{E(EN["hive.c.voice"])}</b>: '
            f'{T("hive.c.pitch")} <span data-pitch>{v["pitch"]:.2f}</span> · {T("hive.c.rate")} <span data-rate>{v["rate"]:.2f}</span> '
            f'<button type="button" class="hv-btn hv-say" data-speak="{E(a["id"])}" data-line="{first}">{T("hive.speak")}</button></p>'
            f'<details data-lines-for="{E(a["id"])}"><summary>{T("hive.c.lines")} (<span data-nlines>{len(a["lines"])}</span>)</summary><ol class="hv-lines"></ol></details>'
            f'</article>')


cards = ''.join(card(a) for a in REG['agents'])
stats = ''.join(f'<div class="st"><dt>{T(k)}</dt><dd data-hive-count="{c}">{C[c]}</dd></div>' for k, c in (
    ('hive.s.agents', 'agents'), ('hive.s.advisors', 'advisors'), ('hive.s.roles', 'crew_roles'),
    ('hive.s.npcs', 'npcs'), ('hive.s.lines', 'lines'), ('hive.s.models', 'models')))
honest = ''.join(f'<li data-honesty="{E(k)}">{E(v)}</li>' for k, v in REG['honesty'].items())
is_ = ''.join(f'<li>{T(f"hive.is.{i}")}</li>' for i in range(1, 5))
filters = (f'<button type="button" class="hv-btn" data-filter="all" aria-pressed="true">{T("hive.f.all")}</button>'
           + ''.join(f'<button type="button" class="hv-btn" data-filter="{k}" aria-pressed="false">{T("hive.kind." + k)}</button>' for k in KINDS))
# council suggestions: registry asks (the text is read from the registry, never typed here). WHICH asks are offered is an
# AUTHORED selection, made by measuring every registry ask through HiveCore.council: each one below seats three to
# five agents in the full roster and at least three in classroom mode (web/test_hive.mjs holds both).
SUGGEST = [('advisor:guide', 'what'), ('advisor:guide', 'real'), ('advisor:layout-hand', 'control'),
           ('advisor:inspector', 'cert'), ('advisor:safety-steward', 'refuse'), ('crew:crane-lift-crew:lift-director', 'plan'),
           ('crew:trench-crew:spotter', 'where'), ('crew:confined-space-crew:attendant', 'never'), ('advisor:dispatcher', 'sited')]
AGENT = {a['id']: a for a in REG['agents']}
TRY = []
for aid, lid in SUGGEST:
    ln = next((x for x in AGENT[aid]['lines'] if x['id'] == lid and x.get('ask_provenance') == 'REGISTRY'), None) if aid in AGENT else None
    if ln is None:
        raise HivePageError(f'build_hive: suggested ask {aid}:{lid} is not a registry ask in the hive')
    TRY.append((aid + ':' + lid, ln['ask']))
try_html = ''.join(f'<button type="button" class="hv-btn hv-try" data-ask-of="{E(r)}" data-ask="{E(q)}">{E(q)}</button>' for r, q in TRY)
links = ''.join(f'<li><a href="{h}">{T(k)}</a></li>' for h, k in (
    ('trade_craft_3d.html', 'hive.l.campus'), ('trade_craft_parishes.html', 'hive.l.parishes')))

PAGE_JS = r'''(function () {
  'use strict';
  var I = JSON.parse(document.getElementById('hive-i18n').textContent);
  var q = new URLSearchParams(location.search), loc = 'en', lq = q.get('lang');
  if (lq && Object.prototype.hasOwnProperty.call(I, lq)) loc = lq;
  else {
    var prefs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || 'en'];
    for (var i = 0; i < prefs.length; i++) { var c = String(prefs[i]).slice(0, 2).toLowerCase(); if (Object.prototype.hasOwnProperty.call(I, c)) { loc = c; break; } }
  }
  var S = I[loc].strings, t = function (k) { if (typeof S[k] !== 'string') throw new Error('hive i18n: ' + loc + ' has no ' + k); return S[k]; };
  document.documentElement.lang = loc; document.documentElement.dir = I[loc].dir;
  document.querySelectorAll('[data-i18n]').forEach(function (el) { el.textContent = t(el.getAttribute('data-i18n')); });
  document.querySelectorAll('[data-i18n-aria]').forEach(function (el) { el.setAttribute('aria-label', t(el.getAttribute('data-i18n-aria'))); });
  var D = JSON.parse(document.getElementById('hive-data').textContent), byId = {};
  D.agents.forEach(function (a) { byId[a.id] = a; });
  var k12 = q.has('classroom') || q.has('class');
  var status = document.getElementById('hive-status'), mute = document.getElementById('hive-mute');
  var lastState = 'ready';
  function onstate(code) { lastState = code; status.textContent = t('hive.v.' + code); }
  HiveVoice.init(D, { k12: k12, onstate: onstate });
  function showMute() { mute.setAttribute('aria-pressed', HiveVoice.muted() ? 'true' : 'false'); }
  showMute(); onstate(HiveVoice.muted() ? 'muted' : 'ready');
  if (k12) {
    document.getElementById('hive-k12-note').hidden = false;
    document.querySelectorAll('.hv-card[data-k12="0"]').forEach(function (el) { el.hidden = true; el.dataset.k12hide = '1'; });
  }
  mute.addEventListener('click', function () { HiveVoice.setMuted(!HiveVoice.muted()); showMute(); onstate(HiveVoice.muted() ? 'muted' : 'ready'); });
  document.getElementById('hive-stop').addEventListener('click', function () { HiveVoice.stop(); });
  function lineOf(id, li) {
    var a = byId[id], ln = a && a.lines[li];
    if (!ln || (k12 && (!a.k12 || !ln.safe))) return null;
    return [a, D.texts[ln.t][0]];
  }
  document.getElementById('hive-main').addEventListener('click', function (e) {
    var b = e.target.closest('[data-speak]');
    if (!b) return;
    var p = lineOf(b.getAttribute('data-speak'), +b.getAttribute('data-line'));
    if (p) HiveVoice.speak([p]);
  });
  /* the lines of a card are drawn from the embedded registry block when its list is first opened: one copy of each
     quote on the page, each with its source path and its own Speak button */
  function drawLines(det) {
    var ol = det.querySelector('.hv-lines'), a = byId[det.getAttribute('data-lines-for')];
    if (!a || ol.childElementCount) return ol.childElementCount;
    a.lines.forEach(function (ln, i) {
      if (k12 && !ln.safe) return;
      var li = document.createElement('li'), tag = document.createElement('span'), tx = document.createElement('span'),
          src = document.createElement('span'), code = document.createElement('code'), b = document.createElement('button');
      li.dataset.line = i; li.dataset.kind = ln.k; li.dataset.safe = ln.safe;
      tag.className = 'tag'; tag.textContent = t('hive.k.' + ln.k); li.appendChild(tag); li.appendChild(document.createTextNode(' '));
      if (ln.ask) { var qq = document.createElement('q'); qq.className = 'hv-ask'; qq.textContent = ln.ask; li.appendChild(qq); li.appendChild(document.createTextNode(' ')); }
      tx.className = 'hv-text'; tx.textContent = D.texts[ln.t][0]; li.appendChild(tx);
      src.className = 'hv-src'; src.textContent = t('hive.src') + ' '; code.textContent = D.texts[ln.t][1]; src.appendChild(code); li.appendChild(src);
      b.type = 'button'; b.className = 'hv-btn hv-say'; b.textContent = t('hive.speak'); b.setAttribute('data-speak', a.id); b.setAttribute('data-line', i);
      li.appendChild(b); ol.appendChild(li);
    });
    return ol.childElementCount;
  }
  document.querySelectorAll('details[data-lines-for]').forEach(function (d) { d.addEventListener('toggle', function () { if (d.open) drawLines(d); }); });
  /* roster filters */
  var kind = 'all', cards = [].slice.call(document.querySelectorAll('.hv-card')), search = document.getElementById('hive-search');
  function applyFilter() {
    var s = search.value.trim().toLowerCase(), n = 0;
    cards.forEach(function (el) {
      var show = !el.dataset.k12hide && (kind === 'all' || el.dataset.kind === kind) && (!s || el.dataset.hay.indexOf(s) >= 0);
      el.hidden = !show; if (show) n++;
    });
    document.getElementById('hive-count').textContent = n;
    return n;
  }
  document.querySelectorAll('[data-filter]').forEach(function (b) {
    b.addEventListener('click', function () {
      kind = b.getAttribute('data-filter');
      document.querySelectorAll('[data-filter]').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      applyFilter();
    });
  });
  search.addEventListener('input', applyFilter);
  applyFilter();
  /* council */
  var out = document.getElementById('hive-council-out'), note = document.getElementById('hive-council-note'), last = null;
  function convene(question) {
    last = HiveCore.council(D, question, { k12: k12 });
    out.textContent = '';
    last.members.forEach(function (m, i) {
      var a = D.agents[m.agent], ln = a.lines[m.line], li = document.createElement('li');
      li.dataset.agent = a.id; li.dataset.line = m.line;
      var face = document.querySelector('.hv-card[data-agent="' + a.id + '"] .hv-face');
      if (face) li.appendChild(face.cloneNode(true));
      var body = document.createElement('div'), h = document.createElement('b'), p = document.createElement('p'), src = document.createElement('code'), meta = document.createElement('span');
      h.textContent = a.glyph + ' ' + a.name; p.textContent = D.texts[ln.t][0]; src.textContent = D.texts[ln.t][1];
      meta.className = 'muted'; meta.textContent = ' · ' + t('hive.cn.matched') + ': ' + m.hits + ' · ' + t('hive.src') + ' ';
      body.appendChild(h); body.appendChild(p); meta.appendChild(src); body.appendChild(meta); li.appendChild(body);
      var sb = document.createElement('button'); sb.type = 'button'; sb.className = 'hv-btn hv-say'; sb.textContent = t('hive.speak');
      sb.setAttribute('data-speak', a.id); sb.setAttribute('data-line', m.line); body.appendChild(sb);
      out.appendChild(li);
    });
    note.textContent = last.none ? t('hive.cn.none') : last.short ? t('hive.cn.short') : '';
    document.getElementById('hive-play').disabled = last.none;
    return last;
  }
  document.getElementById('hive-form').addEventListener('submit', function (e) { e.preventDefault(); convene(document.getElementById('hive-q').value); });
  document.querySelectorAll('.hv-try').forEach(function (b) {
    b.addEventListener('click', function () { document.getElementById('hive-q').value = b.getAttribute('data-ask'); convene(b.getAttribute('data-ask')); });
  });
  document.getElementById('hive-play').addEventListener('click', function () {
    if (!last || last.none) return;
    HiveVoice.speak(last.members.map(function (m) { var a = D.agents[m.agent]; return [a, D.texts[a.lines[m.line].t][0]]; }));
  });
  window.__hivePage = { locale: loc, dir: I[loc].dir, k12: k12, shown: applyFilter, convene: convene, drawLines: drawLines, state: function () { return lastState; } };
})();'''

tcss, tjs = theme('doc')
NAV = nav_html(PAGE, nav_labels('en'))
ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' "
        "rx='6' fill='%230C1113'/%3E%3Cpath d='M16 5 l9 5 v10 l-9 5 l-9 -5 v-10z' fill='none' stroke='%23E8A33D' "
        "stroke-width='2.2'/%3E%3Ccircle cx='16' cy='15' r='3.2' fill='%2341C4D4'/%3E%3C/svg%3E")

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="{ICON}">
<title>Omega Hive</title>
<script id="style-head-js">{STYLE_HEAD_JS}</script>
<style>{NAV_CSS}</style>
<style id="tc-css">{tcss}</style>
<style id="hive-kit-css">{HIVE_CSS}</style>
<style>
body{{font:16px/1.6 "IBM Plex Sans",system-ui,sans-serif}}
.wrap{{max-width:1100px;margin:0 auto;padding:28px 16px 120px}}
.lede{{color:var(--tc-muted);max-width:72ch}}
main,section,li,p,summary{{overflow-wrap:anywhere}}
.box{{border:1px solid var(--tc-line);border-radius:10px;padding:16px;margin:0 0 20px;background:var(--tc-panel);color:var(--tc-ink);min-inline-size:0}}
.box h2{{margin:0 0 10px;font-size:22px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin:0 0 12px}}
.st{{display:flex;flex-direction:column-reverse}}
.st dt{{color:var(--tc-muted);font-size:13px}}
.st dd{{margin:0;font-size:26px;font-weight:700;font-variant-numeric:tabular-nums}}
.honesty{{color:var(--tc-muted);padding-inline-start:20px}}
.honesty li{{margin:4px 0}}
.muted{{color:var(--tc-muted);font-size:14px}}
.tag{{font:600 12px/1 ui-monospace,monospace;border:1px solid var(--tc-line);border-radius:4px;padding:3px 6px;color:var(--tc-muted);display:inline-block}}
code{{font:12px ui-monospace,monospace;overflow-wrap:anywhere}}
a{{color:var(--tc-link)}}
.links a{{display:inline-flex;align-items:center;min-block-size:44px}}
.hv-roster{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}}
.hv-card{{border:1px solid var(--tc-line);border-radius:8px;padding:12px;background:var(--tc-raised);min-inline-size:0}}
.hv-card[hidden]{{display:none}}
.hv-head{{display:flex;gap:10px;align-items:flex-start}}
.hv-who{{min-inline-size:0}}
.hv-who h3{{margin:0;font-size:17px}}
.hv-who p{{margin:2px 0}}
.hv-pers,.hv-vc,.hv-av{{font-size:14px;margin:6px 0}}
.hv-lines{{padding-inline-start:20px;font-size:14px}}
.hv-lines li{{margin:0 0 8px}}
.hv-src{{display:block;color:var(--tc-muted);font-size:12px}}
.hv-ask{{font-style:italic}}
.hv-filters{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 12px}}
.hv-filters input{{min-block-size:44px;font:inherit;color:var(--tc-ink);background:var(--tc-raised);border:1px solid var(--tc-line);border-radius:8px;padding:0 10px;min-inline-size:0;flex:1 1 200px}}
#hive-form{{display:flex;flex-wrap:wrap;gap:8px;align-items:center}}
#hive-form input{{min-block-size:44px;font:inherit;color:var(--tc-ink);background:var(--tc-raised);border:1px solid var(--tc-line);border-radius:8px;padding:0 10px;flex:1 1 240px;min-inline-size:0}}
.hv-tries{{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:8px 0}}
.hv-try{{font-size:14px}}
#hive-council-out{{list-style:none;padding:0;margin:12px 0 0}}
#hive-council-out li{{display:flex;gap:10px;align-items:flex-start;border-block-start:1px solid var(--tc-line);padding:10px 0}}
#hive-council-out li p{{margin:2px 0}}
#hive-council-out li div{{min-inline-size:0}}
</style>
</head>
<body class="tc-theme">
{NAV}
<main class="wrap" id="hive-main">
<header>
{T("hive.kicker", "p", ' class="tc-kicker"')}
{T("hive.title", "h1", ' class="tc-page-title"')}
{T("hive.lede", "p", ' class="lede"')}
<dl class="stats">{stats}</dl>
</header>
<section class="box" aria-labelledby="hive-h-honest"><h2 id="hive-h-honest" data-i18n="hive.h.honest">{E(EN["hive.h.honest"])}</h2>
<ul id="hive-is">{is_}</ul>
<ul class="honesty" id="hive-honesty">{honest}</ul>
<p class="muted" id="hive-k12-note" hidden>{T("hive.k12.note")}</p></section>
<section class="box" aria-labelledby="hive-h-voice"><h2 id="hive-h-voice" data-i18n="hive.h.voice">{E(EN["hive.h.voice"])}</h2>
<p class="muted">{T("hive.v.note")}</p>
<div class="hv-voicebar"><button type="button" class="hv-btn" id="hive-mute" aria-pressed="false">{T("hive.v.mute")}</button>
<button type="button" class="hv-btn" id="hive-stop">{T("hive.v.stop")}</button>
<span class="hv-status" id="hive-status" role="status" aria-live="polite"></span></div></section>
<section class="box" aria-labelledby="hive-h-council" id="hive-council"><h2 id="hive-h-council" data-i18n="hive.h.council">{E(EN["hive.h.council"])}</h2>
<p class="muted">{T("hive.cn.note")}</p>
<form id="hive-form"><label for="hive-q" data-i18n="hive.cn.ask">{E(EN["hive.cn.ask"])}</label>
<input id="hive-q" type="text" autocomplete="off" maxlength="200">
<button type="submit" class="hv-btn" id="hive-go">{T("hive.cn.go")}</button>
<button type="button" class="hv-btn" id="hive-play" disabled>{T("hive.cn.play")}</button></form>
<div class="hv-tries"><span class="muted" data-i18n="hive.cn.try">{E(EN["hive.cn.try"])}</span>{try_html}</div>
<p class="muted" id="hive-council-note" aria-live="polite"></p>
<ol id="hive-council-out"></ol></section>
<section class="box" aria-labelledby="hive-h-roster"><h2 id="hive-h-roster" data-i18n="hive.h.roster">{E(EN["hive.h.roster"])}</h2>
<div class="hv-filters">{filters}
<input id="hive-search" type="search" aria-label="{E(EN["hive.f.search"])}" data-i18n-aria="hive.f.search">
<span class="muted"><b id="hive-count">{C["agents"]}</b> {T("hive.f.shown")}</span></div>
<div class="hv-roster" id="hive-roster">{cards}</div></section>
<section class="box links" aria-labelledby="hive-h-where"><h2 id="hive-h-where" data-i18n="hive.h.where">{E(EN["hive.h.where"])}</h2><ul>{links}</ul></section>
<p class="muted">hive/registry/hive.json · {E(REG["schema"])} · stamp <code data-stamp>{E(REG["source_stamp"])}</code></p>
</main>
<script type="application/json" id="hive-data">{js_json(DATA)}</script>
<script type="application/json" id="hive-i18n">{js_json(I18N)}</script>
<script id="hive-kit">{HIVE_JS}</script>
<script id="hive-page">{PAGE_JS}</script>
<script>{tjs}</script>
<script id="style-js">{STYLE_JS}</script>
</body>
</html>
'''
TITLE = 'SmartCiti.X : Trade Craft Academy — ' + EN['hive.nav']
page = apply_seo(page, PAGE, TITLE, EN['hive.seo.desc'], 'page')
emit(HERE / 'trade_craft_hive.html', page,
     f'{C["agents"]} agents | {C["lines"]} quoted lines | models {C["models"]} | stamp {REG["source_stamp"]}')
