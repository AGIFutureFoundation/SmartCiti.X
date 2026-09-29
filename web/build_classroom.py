#!/usr/bin/env python3
"""The classroom page: teacher/admin class-plan builder across all open worlds, learner dashboard,
and a class scoreboard built only from progress files a teacher imports.

Everything comes from classroom/registry/classroom.json (python3 classroom/build.py) through
web/classkit.py; every word from the class.* i18n keys (8 locales, Arabic right-to-left). No server,
no accounts, no network: plans are files and links (not access control), scores are play, no
student data leaves the browser, nothing here writes a completion record. Optional plan signing
uses the sign-in page's own AUTH-CORE recovery and the reader's wallet (personal_sign) only.
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
from classkit import class_data, class_i18n, auth_core, js_json, CLASS_CSS, CLASS_JS  # noqa: E402

PAGE = 'web/trade_craft_classroom.html'
E = lambda s: html.escape(str(s), quote=True)


class ClassroomPageError(Exception):
    pass


import sitenav  # noqa: E402
if PAGE not in sitenav.PAGES:
    raise SystemExit(f'build_classroom: {PAGE} is not declared in web/sitenav.py GROUPS')

D = class_data()
I18N = class_i18n()
EN = I18N['en']['strings']


def L(k):
    for loc, c in I18N.items():
        if k not in c['strings'] or not c['strings'][k].strip():
            raise ClassroomPageError(f'classroom: i18n key {k!r} is missing from {loc}')
    return EN[k]


def T(k, tag='span', attrs=''):
    return f'<{tag}{attrs} data-i18n="{k}">{E(L(k))}</{tag}>'


for k in EN:
    L(k)

worlds = ''.join(f'<label class="ck"><input type="checkbox" name="w" value="{E(w)}" checked> {T("class.w." + w)}</label>'
                 for w in D['worlds'])
mods = ''.join(f'<label class="ck"><input type="checkbox" name="m" value="{E(m["id"])}" checked> <span>{E(m["name"])}</span>'
               f' <small>({len(m["moments"])}/{len(m["places"])})</small></label>' for m in D['modules'])
mins = ''.join(f'<option value="{n}"{" selected" if n == D["rules"]["session_minutes"]["default"] else ""}>{n}</option>'
               for n in D['rules']['session_minutes']['choices'])
xp = ''.join(f'<label class="xp"><code>{E(k)}</code> <input type="number" min="0" max="1000" step="1" name="xp-{E(k)}" value="{v}"></label>'
             for k, v in sorted(D['rules']['xp'].items()))
stats = ''.join(f'<div class="st"><dt>{T(k)}</dt><dd data-cl-stat="{s}">0</dd></div>' for k, s in (
    ('class.l.sessions', 'sessions'), ('class.hud.xp', 'xp'), ('class.hud.streak', 'streak'), ('class.l.badges', 'badges'),
    ('class.l.met', 'met'), ('class.l.modules', 'modules'), ('class.l.places', 'places')))
heads = ''.join(f'<div class="st"><dt>{T("class.stat." + k)}</dt><dd data-cl-count="{k}">{len(D[k])}</dd></div>'
                for k in ('modules', 'moments', 'places'))
honest = ''.join(f'<li>{T(k)}</li>' for k in ('class.h.server', 'class.h.plan', 'class.h.play', 'class.h.data', 'class.h.lessons'))

PAGE_JS = r'''(function () {
  'use strict';
  var I = JSON.parse(document.getElementById('class-i18n').textContent);
  var q = new URLSearchParams(location.search).get('lang'), loc = 'en';
  if (q && Object.prototype.hasOwnProperty.call(I, q)) loc = q;
  else {
    var prefs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || 'en'];
    for (var i = 0; i < prefs.length; i++) { var c = String(prefs[i]).slice(0, 2).toLowerCase(); if (Object.prototype.hasOwnProperty.call(I, c)) { loc = c; break; } }
  }
  var S = I[loc].strings;
  document.documentElement.lang = loc; document.documentElement.dir = I[loc].dir;
  document.querySelectorAll('[data-i18n]').forEach(function (el) {
    var s = S[el.getAttribute('data-i18n')];
    if (typeof s !== 'string') throw new Error('class i18n: ' + loc + ' has no ' + el.getAttribute('data-i18n'));
    el.textContent = s;
  });
  var K = TCClassCore, C = TCClass.mount({}), D = C.data;
  var $ = function (s) { return document.querySelector(s); };
  function say(sel, m) { $(sel).textContent = m; }
  function formPlan() {
    var p = K.defaultPlan(D);
    p.title = $('#cl-title').value.trim().slice(0, 120);
    p.worlds = [].map.call(document.querySelectorAll('input[name=w]:checked'), function (x) { return x.value; });
    p.modules = [].map.call(document.querySelectorAll('input[name=m]:checked'), function (x) { return x.value; });
    p.paths = $('#cl-paths').checked;
    p.session_minutes = Number($('#cl-min').value);
    Object.keys(p.xp).forEach(function (k) { p.xp[k] = Number(document.querySelector('[name="xp-' + k + '"]').value); });
    return K.validatePlan(p, D);
  }
  var signed = null;
  function link(p) {
    var u = new URL(location.href); u.search = ''; u.hash = '';
    u.searchParams.set('plan', K.encodePlan(p));
    return u.toString();
  }
  function download(name, obj) {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(obj, null, 1) + '\n'], { type: 'application/json' }));
    a.download = name; document.body.appendChild(a); a.click(); a.remove();
  }
  function current() { return signed || formPlan(); }
  document.getElementById('cl-form').addEventListener('change', function () { signed = null; });
  $('#cl-all').addEventListener('click', function () { document.querySelectorAll('input[name=m]').forEach(function (x) { x.checked = true; }); signed = null; });
  $('#cl-link').addEventListener('click', function () {
    try { var p = current(); $('#cl-out').value = link(p); say('#cl-msg', ''); } catch (e) { say('#cl-msg', e.message); }
  });
  $('#cl-json').addEventListener('click', function () {
    try { download('class-plan.json', current()); say('#cl-msg', ''); } catch (e) { say('#cl-msg', e.message); }
  });
  $('#cl-sign').addEventListener('click', function () {
    var w = window.ethereum;
    if (!w || typeof w.request !== 'function') { say('#cl-msg', S['class.nowallet']); return; }
    var p;
    try { p = formPlan(); } catch (e) { say('#cl-msg', e.message); return; }
    w.request({ method: 'eth_requestAccounts' }).then(function (acc) {
      p.signer = TCClassAuth.toChecksumAddress(acc[0]);
      return w.request({ method: 'personal_sign', params: [K.planMessage(p), acc[0]] });
    }).then(function (sig) {
      p.sig = sig;
      K.verifyPlan(p, TCClassAuth);
      signed = p; $('#cl-out').value = link(p); say('#cl-msg', S['class.plan.signed']);
    }).catch(function (e) { say('#cl-msg', S['class.plan.refused'] + ': ' + e.message); });
  });
  $('#cl-import').addEventListener('change', function (ev) {
    var f = ev.target.files[0]; if (!f) return;
    f.text().then(function (t) {
      var r = C.setPlan(K.encodePlan(JSON.parse(t)));
      say('#cl-msg', r.sign === 'signed' ? S['class.plan.signed'] : S['class.plan.unsigned']); learner();
    }).catch(function (e) { say('#cl-msg', S['class.plan.refused'] + ': ' + e.message); });
  });
  function learner() {
    var st = C.state(), p = C.plan(), now = Date.now();
    var v = { sessions: st.sessions.length, xp: K.xpOf(st, D, p.xp), streak: K.streak(st.days, now), badges: K.badges(st, D, p.xp, now).length,
      met: Object.keys(st.moments).filter(function (k) { return st.moments[k].correct; }).length, modules: K.modulesDone(st, D).length,
      places: Object.keys(st.places).length };
    Object.keys(v).forEach(function (k) { document.querySelector('[data-cl-stat="' + k + '"]').textContent = String(v[k]); });
    var sc = C.scope(), ul = $('#cl-mine'); ul.textContent = '';
    D.modules.filter(function (m) { return p.modules.indexOf(m.id) >= 0; }).forEach(function (m) {
      var li = document.createElement('li'), ps = m.places.filter(function (id) { return sc.places[id]; });
      if (!ps.length) return;
      li.textContent = m.name + ' - ';
      var pl = sc.places[ps[0]], a = document.createElement('a');
      a.href = pl.href.replace(/^web\//, ''); a.textContent = S['class.l.open'] + ': ' + pl.title;
      li.appendChild(a); ul.appendChild(li);
    });
    $('#cl-name').value = st.learner;
  }
  $('#cl-name').addEventListener('change', function (ev) { C.setLearner(ev.target.value); });
  $('#cl-export').addEventListener('click', function () { download('class-progress.json', C.exportProgress()); });
  $('#cl-files').addEventListener('change', function (ev) {
    var fs = [].slice.call(ev.target.files);
    Promise.all(fs.map(function (f) { return f.text().then(function (t) { var j = null; try { j = JSON.parse(t); } catch (e) { j = null; } return { name: f.name, json: j }; }); }))
      .then(function (files) {
        var r = K.scoreboard(files, D, C.plan().xp, Date.now()), tb = $('#cl-board tbody'); tb.textContent = '';
        r.rows.forEach(function (row) {
          var tr = document.createElement('tr');
          [row.rank, row.learner, row.xp, row.met, row.modules, row.streak, row.badges].forEach(function (x) { var td = document.createElement('td'); td.textContent = String(x); tr.appendChild(td); });
          tb.appendChild(tr);
        });
        var rf = $('#cl-refused'); rf.textContent = '';
        r.refused.forEach(function (x) { var li = document.createElement('li'); li.textContent = x.name + ': ' + x.why; rf.appendChild(li); });
        window.__classBoard = r;
      });
  });
  learner();
  setInterval(learner, 5000);
  window.__classState = { locale: loc, dir: I[loc].dir, modules: D.modules.length, places: D.places.length, moments: D.moments.length, saved: C.saved(), plan: C.planSign() };
})();'''

tcss, tjs = theme('doc')
NAV = nav_html(PAGE, nav_labels('en'))
ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' "
        "height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M6 12 L16 7 L26 12 L16 17 Z' fill='none' stroke='%23E8A33D' "
        "stroke-width='2.2' stroke-linejoin='round'/%3E%3Cpath d='M10 14 V21 Q16 25 22 21 V14' fill='none' stroke='%2341C4D4' "
        "stroke-width='2.2'/%3E%3C/svg%3E")
C = D
page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="{ICON}">
<title>Classroom</title>
<script id="style-head-js">{STYLE_HEAD_JS}</script>
<style>{NAV_CSS}</style>
<style id="tc-css">{tcss}</style>
<style id="class-css">{CLASS_CSS}</style>
<style>
body{{font:16px/1.6 "IBM Plex Sans",system-ui,sans-serif}}
.wrap{{max-width:1100px;margin:0 auto;padding:28px 16px 140px}}
.lede{{color:var(--tc-muted);max-width:72ch}}
.box{{border:1px solid var(--tc-line);border-radius:10px;padding:16px;margin:0 0 20px;background:var(--tc-panel);color:var(--tc-ink);min-inline-size:0}}
.box h2{{margin:0 0 10px;font-size:20px}}
fieldset{{border:1px solid var(--tc-line);border-radius:8px;margin:0 0 12px;padding:8px 12px;min-inline-size:0}}
legend{{color:var(--tc-muted);padding:0 6px}}
.ck{{display:flex;align-items:center;gap:8px;min-block-size:44px;cursor:pointer;overflow-wrap:anywhere}}
.ck input{{inline-size:18px;block-size:18px;flex:none;accent-color:var(--tc-amber)}}
.mods{{max-block-size:320px;overflow:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:0 12px}}
.mods small{{color:var(--tc-muted)}}
.xp{{display:inline-flex;align-items:center;gap:6px;margin:4px 12px 4px 0;flex-wrap:wrap}}
.xp input,#cl-title,#cl-min,#cl-name{{min-block-size:44px;font:inherit;color:var(--tc-ink);background:var(--tc-bg);border:1px solid var(--tc-line);border-radius:6px;padding:0 8px;max-inline-size:100%}}
.xp input{{inline-size:6em}}
#cl-title,#cl-name{{inline-size:min(420px,100%)}}
.btns{{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}}
.btns button,.btns label.file{{min-block-size:44px;padding:0 14px;border-radius:8px;border:1px solid var(--tc-line);background:var(--tc-bg);color:var(--tc-ink);font:inherit;cursor:pointer;display:inline-flex;align-items:center;gap:6px}}
.btns label.file{{flex-wrap:wrap;max-inline-size:100%;overflow-wrap:anywhere;padding-block:6px}}
.btns input[type=file]{{max-inline-size:100%;min-inline-size:0}}
main,.box,label,p,li{{overflow-wrap:anywhere}}
#cl-out{{inline-size:100%;min-block-size:70px;font:13px/1.4 ui-monospace,monospace;color:var(--tc-ink);background:var(--tc-bg);border:1px solid var(--tc-line);border-radius:6px}}
.msg{{color:var(--tc-muted);min-block-size:1.4em;overflow-wrap:anywhere}}
.stats{{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin:0 0 12px}}
.st{{display:flex;flex-direction:column-reverse}}
.st dt{{color:var(--tc-muted);font-size:13px}}
.st dd{{margin:0;font-size:24px;font-weight:700;font-variant-numeric:tabular-nums}}
.tw{{overflow-x:auto}}
table{{border-collapse:collapse;inline-size:100%}}
th,td{{border-block-end:1px solid var(--tc-line);padding:6px 8px;text-align:start}}
#cl-mine a{{color:var(--tc-link)}}
.honesty{{border-block-start:1px solid var(--tc-line);padding-block-start:14px;color:var(--tc-muted)}}
.honesty li{{margin:4px 0}}
</style>
</head>
<body class="tc-theme">
{NAV}
<main class="wrap" id="class-main">
<header>
{T("class.kicker", "p", ' class="tc-kicker"')}
{T("class.title", "h1", ' class="tc-page-title"')}
{T("class.lede", "p", ' class="lede"')}
<dl class="stats">{heads}</dl>
</header>
<ul class="honesty" id="class-honesty">{honest}</ul>
<section class="box" id="cl-teacher" aria-labelledby="cl-h-t">
<h2 id="cl-h-t" data-i18n="class.tab.teacher">{E(L("class.tab.teacher"))}</h2>
<form id="cl-form" onsubmit="return false">
<p><label>{T("class.f.title")}<br><input id="cl-title" maxlength="120"></label></p>
<fieldset><legend data-i18n="class.f.worlds">{E(L("class.f.worlds"))}</legend>{worlds}
<label class="ck"><input type="checkbox" id="cl-paths" checked> {T("class.f.paths")}</label></fieldset>
<fieldset><legend data-i18n="class.f.modules">{E(L("class.f.modules"))}</legend>
<div class="btns"><button type="button" id="cl-all" data-i18n="class.f.all">{E(L("class.f.all"))}</button></div>
<div class="mods">{mods}</div>
<p class="msg" data-cx-attr>{T("class.cx.attr")} <a href="{E(D['cx_attribution']['repo'])}" rel="noopener">{E(D['cx_attribution']['text'])}</a> -
<a href="{E(D['cx_attribution']['license_url'])}" rel="license noopener">CC BY 4.0</a>. <span lang="en">{E(D['cx_attribution']['changes'])}. {E(D['cx_honesty']['blocks'])} {E(D['cx_honesty']['mapping'])}</span></p></fieldset>
<p><label>{T("class.f.minutes")} <select id="cl-min">{mins}</select></label></p>
<fieldset><legend data-i18n="class.f.xp">{E(L("class.f.xp"))}</legend>{xp}</fieldset>
</form>
<div class="btns">
<button type="button" id="cl-link" data-i18n="class.act.link">{E(L("class.act.link"))}</button>
<button type="button" id="cl-json" data-i18n="class.act.json">{E(L("class.act.json"))}</button>
<button type="button" id="cl-sign" data-i18n="class.act.sign">{E(L("class.act.sign"))}</button>
<label class="file">{T("class.act.import")} <input type="file" id="cl-import" accept="application/json,.json"></label>
</div>
<textarea id="cl-out" readonly aria-label="{E(L("class.act.link"))}"></textarea>
<p class="msg" id="cl-msg" aria-live="polite"></p>
</section>
<section class="box" id="cl-learner" aria-labelledby="cl-h-l">
<h2 id="cl-h-l" data-i18n="class.tab.learner">{E(L("class.tab.learner"))}</h2>
<dl class="stats">{stats}</dl>
<p><label>{T("class.l.learner")}<br><input id="cl-name" maxlength="60"></label></p>
<div class="btns"><button type="button" id="cl-export" data-i18n="class.act.export">{E(L("class.act.export"))}</button></div>
<ul id="cl-mine"></ul>
</section>
<section class="box" id="cl-class" aria-labelledby="cl-h-c">
<h2 id="cl-h-c" data-i18n="class.tab.board">{E(L("class.tab.board"))}</h2>
<p class="msg">{T("class.h.data")}</p>
<div class="btns"><label class="file">{T("class.act.board")} <input type="file" id="cl-files" multiple accept="application/json,.json"></label></div>
<div class="tw"><table id="cl-board"><thead><tr><th>{T("class.l.rank")}</th><th>{T("class.l.name")}</th><th>{T("class.hud.xp")}</th>
<th>{T("class.l.met")}</th><th>{T("class.l.modules")}</th><th>{T("class.hud.streak")}</th><th>{T("class.l.badges")}</th></tr></thead><tbody></tbody></table></div>
<p>{T("class.l.refused")}</p><ul id="cl-refused"></ul>
</section>
</main>
<script type="application/json" id="class-data">{js_json(D)}</script>
<script type="application/json" id="class-i18n">{js_json(I18N)}</script>
<script id="class-auth">{auth_core()}</script>
<script id="class-kit">{CLASS_JS}</script>
<script id="class-page">{PAGE_JS}</script>
<script>{tjs}</script>
<script id="style-js">{STYLE_JS}</script>
</body>
</html>
'''
TITLE = 'SmartCiti.X : Trade Craft Academy — ' + L('class.nav')
page = apply_seo(page, PAGE, TITLE, L('class.seo.desc'), 'page')
emit(HERE / 'trade_craft_classroom.html', page,
     f'{len(D["modules"])} modules | {len(D["moments"])} moments | {len(D["places"])} places | no server | nav+seo wired')
