#!/usr/bin/env python3
"""The Robotics lab page (ROBOLAB, wave 11): web/trade_craft_robotics.html.

Env catalogue (robotics/registry/robotics.json: 4 robokit world envs + one spec per training seat), embodiment cards,
a live robokit sandbox (teleop + record + scripted reference policy on the same env/seed), how a learner records a
demonstration, what is and is not trained, and links to the worlds and the Contribute (share data) page.

Every chrome word comes from the robo.* i18n keys (8 locales, Arabic right-to-left). Env / embodiment names, units
and honesty lines are registry data, shown verbatim. Figures are computed from the registry at build time; the
reference-policy results table is computed in the reader's browser from the same deterministic core the test runs.
Nothing here says a model was trained: the registry's trained_models count is 0 and the page prints it.
Classroom / K-12 mode (?classroom=1 or ?class=...) offers no recording and no export.
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
from robokit import robo_data, robo_panel_html, robo_i18n_keys, ROBO_CSS, ROBO_JS  # noqa: E402
import sitenav  # noqa: E402

PAGE = 'web/trade_craft_robotics.html'
E = lambda s: html.escape(str(s), quote=True)


class RoboticsPageError(Exception):
    pass


if PAGE not in sitenav.PAGES:
    raise RoboticsPageError(f'build_robotics: {PAGE} is not declared in web/sitenav.py (NEEDS nav: UX, nav.page.robotics)')

PAGE_KEYS = ['robo.nav', 'robo.kicker', 'robo.title', 'robo.lede', 'robo.seo.desc', 'robo.s.envs', 'robo.s.robokit',
             'robo.s.seats', 'robo.s.emb', 'robo.s.trained', 'robo.h.try', 'robo.h.envs', 'robo.h.emb', 'robo.h.how',
             'robo.h.trained', 'robo.h.links', 'robo.h.refrun', 'robo.refrun.note', 'robo.how.1', 'robo.how.2',
             'robo.how.3', 'robo.how.4', 'robo.how.5', 'robo.is.1', 'robo.is.2', 'robo.is.3', 'robo.not.1',
             'robo.not.2', 'robo.not.3', 'robo.l.parishes', 'robo.l.bay', 'robo.l.seats', 'robo.l.contribute',
             'robo.c.obs', 'robo.c.act', 'robo.c.reward', 'robo.c.term', 'robo.c.cap', 'robo.c.seeds', 'robo.c.ref',
             'robo.c.src', 'robo.c.limits', 'robo.c.sensors', 'robo.c.teleop', 'robo.c.env', 'robo.c.seed',
             'robo.c.done']
KEYS = PAGE_KEYS + robo_i18n_keys()

I18N = {}
for f in sorted((ROOT / 'i18n/locales').glob('*.json')):
    c = json.loads(f.read_text(encoding='utf-8'))
    s = c['strings']
    miss = [k for k in KEYS if k not in s or not isinstance(s[k], str) or not s[k].strip()]
    if miss:
        raise RoboticsPageError(f'build_robotics: locale {f.name} is missing {miss[:5]}')
    I18N[c['locale']] = {'dir': c['dir'], 'strings': {k: s[k] for k in KEYS}}
if len(I18N) != 8:
    raise RoboticsPageError(f'build_robotics: expected 8 locales, found {sorted(I18N)}')
EN = I18N['en']['strings']


def T(k, tag='span', attrs=''):
    if k not in EN:
        raise RoboticsPageError(f'build_robotics: unknown key {k}')
    return f'<{tag}{attrs} data-i18n="{k}">{E(EN[k])}</{tag}>'


REG = json.loads((ROOT / 'robotics/registry/robotics.json').read_text())
DATA = robo_data()
C = REG['counts']
if C['trained_models'] != 0:
    raise RoboticsPageError('build_robotics: the registry claims a trained model - this page cannot say that')


def rng(o):
    return '' if o['low'] is None else f' [{o["low"]}, {o["high"]}]'


def env_card(e):
    obs = ''.join(f'<li><code>{E(o["name"])}</code> {E(o["unit"]) or "-"}{E(rng(o))}</li>' for o in e['observation'])
    if e['action']['type'] == 'continuous':
        act = ''.join(f'<li><code>{E(a["name"])}</code> {E(a["unit"])} [{a["low"]}, {a["high"]}]</li>' for a in e['action']['fields'])
    else:
        act = ''.join(f'<li><code>{E(a["keys"])}</code> {E(a["action"])}</li>' for a in e['action']['fields'])
    rew = ''.join(f'<li><code>{E(r["term"])}</code> {r["weight"]:+g} {E(r["unit"])} - {E(r["why"])}</li>' for r in e['reward'])
    term = ''.join(f'<li><code>{E(t["id"])}</code> {E(t["when"])}</li>' for t in e['termination'])
    cap = e['episode_cap']
    capt = f'{cap["steps"]} x {cap["dt_s"]} s' if cap['steps'] else E(cap['note'])
    seeds = ', '.join(str(s) for s in e['seeds']) or ', '.join(e.get('scenarios', []))
    src = ''.join(f'<li><code>{E(s)}</code></li>' for s in e['sources'])
    launch = e['world'].get('launch')
    go = f' <a href="{E(launch.replace("web/", ""))}">{E(launch.replace("web/", ""))}</a>' if launch else ''
    return (f'<details class="env" data-env="{E(e["id"])}"><summary><code>{E(e["id"])}</code> {E(e["name"])} '
            f'<span class="tag">{E(e["provenance"])}</span> <span class="tag">{E(e["runner"])}</span></summary>'
            f'<p>{E(e["brief"])}{go}</p><div class="grid">'
            f'<div><h4>{T("robo.c.obs")}</h4><ul>{obs}</ul></div><div><h4>{T("robo.c.act")}</h4><ul>{act}</ul></div>'
            f'<div><h4>{T("robo.c.reward")}</h4><ul>{rew}</ul></div><div><h4>{T("robo.c.term")}</h4><ul>{term}</ul>'
            f'<h4>{T("robo.c.cap")}</h4><p>{capt}</p><h4>{T("robo.c.seeds")}</h4><p>{E(seeds)}</p></div>'
            f'<div><h4>{T("robo.c.ref")}</h4><p><code>{E(e["reference_policy"]["id"])}</code> '
            f'<span class="tag">{E(e["reference_policy"]["provenance"])}</span></p>'
            f'<ul>{"".join(f"<li>{E(x)}</li>" for x in e["reference_policy"]["steps"])}</ul></div>'
            f'<div><h4>{T("robo.c.src")}</h4><ul>{src}</ul></div></div></details>')


robokit_envs = [e for e in REG['envs'].values() if e['runner'] == 'robokit']
seat_envs = [e for e in REG['envs'].values() if e['runner'] == 'sim-seat']
cards_env = ''.join(env_card(e) for e in robokit_envs) + ''.join(env_card(e) for e in seat_envs)


def emb_card(m):
    lim = ''.join(f'<li><code>{E(k)}</code> {v}</li>' for k, v in m['limits'].items())
    sen = ''.join(f'<li><code>{E(s["id"])}</code> {E(s["what"])} ({E(s["unit"])})</li>' for s in m['sensors'])
    tel = ''.join(f'<li><kbd>{E(k["keys"])}</kbd> <code>{E(k["field"])}</code> {E(k["value"])}</li>'
                  for k in REG['teleop'][m['id']]['keyboard'])
    d = m['dims_m']
    return (f'<article class="card" data-emb="{E(m["id"])}"><h3>{E(m["name"])} <span class="tag">{E(m["provenance"])}</span></h3>'
            f'<p><code>{E(m["id"])}</code> · {E(m["kind"])} · {d["length"]} x {d["width"]} x {d["height"]} m · {m["mass_kg"]} kg</p>'
            f'<p class="muted">{E(m["kinematics"])}</p>'
            f'<h4>{T("robo.c.limits")}</h4><ul>{lim}</ul><h4>{T("robo.c.sensors")}</h4><ul>{sen}</ul>'
            f'<h4>{T("robo.c.teleop")}</h4><ul>{tel}</ul></article>')


cards_emb = ''.join(emb_card(m) for m in REG['embodiments'].values())
stats = ''.join(f'<div class="st"><dt>{T(k)}</dt><dd data-robo-count="{c}">{C[c]}</dd></div>' for k, c in (
    ('robo.s.envs', 'envs'), ('robo.s.robokit', 'robokit_envs'), ('robo.s.seats', 'sim_seat_envs'),
    ('robo.s.emb', 'embodiments'), ('robo.s.trained', 'trained_models')))
honest = ''.join(f'<li data-honesty="{E(k)}">{E(v)}</li>' for k, v in REG['honesty'].items())
how = ''.join(f'<li>{T(f"robo.how.{i}")}</li>' for i in range(1, 6))
is_ = ''.join(f'<li>{T(f"robo.is.{i}")}</li>' for i in range(1, 4))
not_ = ''.join(f'<li>{T(f"robo.not.{i}")}</li>' for i in range(1, 4))
links = ''.join(f'<li><a href="{h}">{T(k)}</a></li>' for h, k in (
    ('trade_craft_parishes.html', 'robo.l.parishes'), ('trade_craft_bay.html', 'robo.l.bay'),
    ('trade_craft_3d.html', 'robo.l.seats'), ('trade_craft_contribute.html', 'robo.l.contribute')))


def js_json(x):
    return json.dumps(x, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')


PAGE_JS = r'''(function () {
  'use strict';
  var I = JSON.parse(document.getElementById('robo-i18n').textContent);
  var q = new URLSearchParams(location.search), loc = 'en', lq = q.get('lang');
  if (lq && Object.prototype.hasOwnProperty.call(I, lq)) loc = lq;
  else {
    var prefs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || 'en'];
    for (var i = 0; i < prefs.length; i++) { var c = String(prefs[i]).slice(0, 2).toLowerCase(); if (Object.prototype.hasOwnProperty.call(I, c)) { loc = c; break; } }
  }
  var S = I[loc].strings, t = function (k) { if (typeof S[k] !== 'string') throw new Error('robo i18n: ' + loc + ' has no ' + k); return S[k]; };
  document.documentElement.lang = loc; document.documentElement.dir = I[loc].dir;
  document.querySelectorAll('[data-i18n]').forEach(function (el) { el.textContent = t(el.getAttribute('data-i18n')); });
  var data = JSON.parse(document.getElementById('robo-data').textContent);
  var classroom = q.has('classroom') || q.has('class');
  roboMount(document.getElementById('robo'), data, { world: 'lab', classroom: classroom, t: t });
  /* the reference policy on every declared seed of every robokit env - computed here, now, from the same
     deterministic core robotics/test.mjs runs; nothing is typed into the page */
  var tb = document.querySelector('#robo-refrun tbody'), R = data.robo, ok = 0, n = 0;
  Object.keys(R.envs).forEach(function (id) {
    var env = R.envs[id], emb = R.embodiments[env.embodiments[0]];
    env.seeds.forEach(function (s) {
      var ep = RoboCore.rollout(env, emb, s, data.train, 'lab'); n++; if (ep.outcome.success) ok++;
      var tr = document.createElement('tr'); tr.dataset.env = id;
      [id, s, ep.outcome.done, ep.steps, ep.outcome.return.toFixed(2), t(ep.outcome.success ? 'robo.yes' : 'robo.no')].forEach(function (v) {
        var td = document.createElement('td'); td.textContent = v; tr.appendChild(td); });
      tb.appendChild(tr);
    });
  });
  document.getElementById('robo-refrun-sum').textContent = ok + ' / ' + n;
  window.__roboPage = { locale: loc, dir: I[loc].dir, classroom: classroom, refOk: ok, refN: n };
})();'''

tcss, tjs = theme('doc')
NAV = nav_html(PAGE, nav_labels('en'))
ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' "
        "height='32' rx='6' fill='%230C1113'/%3E%3Crect x='8' y='11' width='16' height='11' rx='2' fill='none' "
        "stroke='%23E8A33D' stroke-width='2.2'/%3E%3Ccircle cx='12' cy='25' r='2' fill='%2341C4D4'/%3E%3Ccircle cx='20' "
        "cy='25' r='2' fill='%2341C4D4'/%3E%3Cpath d='M16 11 V6 h5' fill='none' stroke='%2341C4D4' stroke-width='2.2'/%3E%3C/svg%3E")

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="{ICON}">
<title>Robotics lab</title>
<script id="style-head-js">{STYLE_HEAD_JS}</script>
<style>{NAV_CSS}</style>
<style id="tc-css">{tcss}</style>
<style id="robo-css">{ROBO_CSS}</style>
<style>
body{{font:16px/1.6 "IBM Plex Sans",system-ui,sans-serif}}
.wrap{{max-width:1100px;margin:0 auto;padding:28px 16px 120px}}
.lede{{color:var(--tc-muted);max-width:72ch}}
main,section,li,p,summary{{overflow-wrap:anywhere}}
.box{{border:1px solid var(--tc-line);border-radius:10px;padding:16px;margin:0 0 20px;background:var(--tc-panel);color:var(--tc-ink);min-inline-size:0}}
.box h2{{margin:0 0 10px;font-size:22px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin:0 0 12px}}
.st{{display:flex;flex-direction:column-reverse}}
.st dt{{color:var(--tc-muted);font-size:13px}}
.st dd{{margin:0;font-size:26px;font-weight:700;font-variant-numeric:tabular-nums}}
.honesty{{color:var(--tc-muted);padding-inline-start:20px}}
.honesty li{{margin:4px 0}}
.env{{border-block-start:1px solid var(--tc-line);padding:8px 0}}
.env summary{{cursor:pointer;min-block-size:44px;display:flex;align-items:center;flex-wrap:wrap;gap:6px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}}
.grid ul,.card ul{{margin:0;padding-inline-start:18px;font-size:14px}}
h4{{margin:8px 0 4px;font-size:14px;text-transform:uppercase;letter-spacing:.04em;color:var(--tc-muted)}}
.cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}}
.card{{border:1px solid var(--tc-line);border-radius:8px;padding:12px;background:var(--tc-raised);min-inline-size:0}}
.card h3{{margin:0 0 4px;font-size:18px}}
.muted{{color:var(--tc-muted);font-size:14px}}
.tag{{font:600 12px/1 ui-monospace,monospace;border:1px solid var(--tc-line);border-radius:4px;padding:3px 6px;color:var(--tc-muted)}}
code,kbd{{font:13px ui-monospace,monospace}}
.tw{{overflow-x:auto}}
table{{border-collapse:collapse;inline-size:100%}}
th,td{{border-block-end:1px solid var(--tc-line);padding:4px 8px;text-align:start;font-size:14px}}
a{{color:var(--tc-link)}}
.links a{{display:inline-flex;align-items:center;min-block-size:44px}}
</style>
</head>
<body class="tc-theme">
{NAV}
<main class="wrap" id="robo-main">
<header>
{T("robo.kicker", "p", ' class="tc-kicker"')}
{T("robo.title", "h1", ' class="tc-page-title"')}
{T("robo.lede", "p", ' class="lede"')}
<dl class="stats">{stats}</dl>
</header>
<ul class="honesty" id="robo-honesty">{honest}</ul>
<section class="box" aria-labelledby="robo-h-try"><h2 id="robo-h-try" data-i18n="robo.h.try">{E(EN["robo.h.try"])}</h2>
{robo_panel_html(T, "lab")}
</section>
<section class="box" aria-labelledby="robo-h-how"><h2 id="robo-h-how" data-i18n="robo.h.how">{E(EN["robo.h.how"])}</h2><ol>{how}</ol></section>
<section class="box" aria-labelledby="robo-h-tr"><h2 id="robo-h-tr" data-i18n="robo.h.trained">{E(EN["robo.h.trained"])}</h2>
<ul id="robo-is">{is_}</ul><ul id="robo-not">{not_}</ul></section>
<section class="box" aria-labelledby="robo-h-rr"><h2 id="robo-h-rr" data-i18n="robo.h.refrun">{E(EN["robo.h.refrun"])}</h2>
<p class="muted">{T("robo.refrun.note")} <b id="robo-refrun-sum"></b></p>
<div class="tw"><table id="robo-refrun"><thead><tr><th>{T("robo.c.env")}</th><th>{T("robo.c.seed")}</th><th>{T("robo.c.done")}</th>
<th>{T("robo.steps")}</th><th>{T("robo.return")}</th><th>{T("robo.success")}</th></tr></thead><tbody></tbody></table></div></section>
<section class="box" aria-labelledby="robo-h-envs"><h2 id="robo-h-envs" data-i18n="robo.h.envs">{E(EN["robo.h.envs"])}</h2>{cards_env}</section>
<section class="box" aria-labelledby="robo-h-emb"><h2 id="robo-h-emb" data-i18n="robo.h.emb">{E(EN["robo.h.emb"])}</h2><div class="cards">{cards_emb}</div></section>
<section class="box links" aria-labelledby="robo-h-links"><h2 id="robo-h-links" data-i18n="robo.h.links">{E(EN["robo.h.links"])}</h2><ul>{links}</ul></section>
<p class="muted">robotics/registry/robotics.json · {E(REG["schema"])} · stamp <code data-stamp>{E(REG["source_stamp"])}</code></p>
</main>
<script type="application/json" id="robo-data">{js_json(DATA)}</script>
<script type="application/json" id="robo-i18n">{js_json(I18N)}</script>
<script id="robo-kit">{ROBO_JS}</script>
<script id="robo-page">{PAGE_JS}</script>
<script>{tjs}</script>
<script id="style-js">{STYLE_JS}</script>
</body>
</html>
'''
TITLE = 'SmartCiti.X : Trade Craft Academy — ' + EN['robo.nav']
page = apply_seo(page, PAGE, TITLE, EN['robo.seo.desc'], 'page')
emit(HERE / 'trade_craft_robotics.html', page,
     f'{C["envs"]} env specs | {C["embodiments"]} embodiments | trained models {C["trained_models"]} | stamp {REG["source_stamp"]}')
