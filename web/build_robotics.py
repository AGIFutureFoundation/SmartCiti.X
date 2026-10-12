#!/usr/bin/env python3
"""The Robotics lab page (ROBOLAB, wave 11): web/trade_craft_robotics.html.

Env catalogue (robotics/registry/robotics.json: 4 robokit world envs + one spec per training seat), embodiment cards,
a live robokit sandbox (teleop + record + scripted reference policy on the same env/seed), how a learner records a
demonstration, what is and is not trained, and links to the worlds and the Contribute (share data) page.

Every chrome word comes from the robo.* i18n keys (8 locales, Arabic right-to-left). Env / embodiment names, units
and honesty lines are registry data, shown verbatim. Figures are computed from the registry at build time; the
reference-policy results table is computed in the reader's browser from the same deterministic core the test runs.
ARENA BEGIN (wave 18): the page prints the registry's trained_models count, which is the model arena's one small
behaviour-cloning policy (robotics/arena/), trained on SCRIPTED episodes - not a language model, not on learner data.
ARENA END
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
             'robo.c.done', 'robo.h.an', 'robo.an.note', 'robo.an.count', 'robo.an.steps', 'robo.an.success',
             'robo.an.duration', 'robo.an.hist', 'robo.an.card', 'robo.an.empty', 'robo.h.bench', 'robo.bench.note',
             'robo.bench.bound', 'robo.c.level', 'robo.c.items', 'robo.bench.feas', 'robo.bench.ibound'] + ['robo.an.b.' + b for b in ('reverse', 'stop', 'forward', 'left', 'straight', 'right', 'grip', 'dive', 'rise')]
# wave 16: the benchmark chart and the episode replay viewer
PAGE_KEYS += ['robo.h.chart', 'robo.chart.note', 'robo.chart.total', 'robo.h.replay', 'robo.rp.note', 'robo.rp.src', 'robo.rp.ref',
              'robo.rp.mine', 'robo.rp.load', 'robo.rp.play', 'robo.rp.pause', 'robo.rp.scrub', 'robo.rp.actions', 'robo.rp.reward',
              'robo.rp.exact', 'robo.rp.held', 'robo.rp.none', 'robo.bench.reach']
# ---- ARENA BEGIN (wave 18): the model-arena i18n keys (chrome words of the arena section; 8 locales) ---------------------
PAGE_KEYS += ['robo.h.arena', 'robo.arena.note', 'robo.arena.match', 'robo.arena.task', 'robo.arena.pause', 'robo.arena.resume',
              'robo.arena.speed', 'robo.arena.live', 'robo.arena.board', 'robo.arena.policy', 'robo.arena.kind',
              'robo.arena.success', 'robo.arena.win', 'robo.arena.wins', 'robo.arena.cards', 'robo.arena.class', 'robo.arena.progress']
# ---- ARENA END ------------------------------------------------------------------------------------------------------------
KEYS = PAGE_KEYS + robo_i18n_keys()
# ---- CLAW BEGIN (wave 18, keys) - the training-operations panel's i18n keys (robotics/claw/panel.py)
sys.path.insert(0, str(ROOT / 'robotics' / 'claw'))
import panel as train_ops  # noqa: E402
KEYS += [k for k in train_ops.keys() if k not in KEYS]
# ---- CLAW END (keys)

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
# ARENA BEGIN (wave 18): a trained-model count is printed only when it is the model arena's pinned, carded models
_ARENA_MODELS = [m for m in json.loads((ROOT / 'robotics/arena/registry/models.json').read_text())['models'] if m['provenance'] == 'TRAINED']
if C['trained_models'] != len(_ARENA_MODELS) or not all(m['card']['what'] in REG['honesty']['trained'] for m in _ARENA_MODELS) \
        or not REG['honesty']['trained'].startswith("NOTHING HAS BEEN TRAINED ON ANY LEARNER'S DATA"):
    raise RoboticsPageError('build_robotics: the registry counts a trained model the arena model registry does not card')
# ARENA END


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


BENCH = REG['reference_benchmark']
if BENCH['policy'] != 'SCRIPTED' or BENCH['totals']['runs'] != len(BENCH['seeds']) * len(robokit_envs):
    raise RoboticsPageError('build_robotics: the reference benchmark is not a full SCRIPTED run over every seed')
bench_rows = ''.join(
    f'<tr data-bench="{E(eid)}" data-level="{E(l)}"><td><code>{E(eid)}</code></td><td>{E(l)} · {E(row["name"])}</td>'
    f'<td data-bench-success>{row["success"]} / {row["runs"]}</td><td>{row["items"]}</td><td>{row["mean_steps"]}</td><td>{row["mean_return"]:.2f}</td></tr>'
    for eid, v in BENCH['per_env'].items() for l, row in v['levels'].items())
SORT_FEAS = BENCH['per_env']['world.litter-sort']['feasibility']
if SORT_FEAS['feasible_seeds'] * 2 >= len(BENCH['seeds']):
    raise RoboticsPageError('build_robotics: robo.bench.bound says most seeds are ruled out, but the benchmark rules out only '
                            f"{len(BENCH['seeds']) - SORT_FEAS['feasible_seeds']} of {len(BENCH['seeds'])} - reword the key")


# ---- ROBO_CHART:BEGIN (wave 16) - the benchmark chart: one bar per env and curriculum level, success / runs, read from
# robotics.json#reference_benchmark only (no number is typed here). HTML bars, so the labels are real text at every width;
# the bench table further down is the table view of the same block.
def bench_chart():
    rows = []
    for eid, v in BENCH['per_env'].items():
        need_env = REG['envs'].get(eid)
        if not need_env:
            raise RoboticsPageError(f'build_robotics: the benchmark names {eid}, which is not a registry env')
        bars = ''
        for l, row in v['levels'].items():
            for k in ('success', 'runs', 'name'):
                if k not in row:
                    raise RoboticsPageError(f'build_robotics: benchmark {eid} level {l} has no {k}')
            if not row['runs']:
                raise RoboticsPageError(f'build_robotics: benchmark {eid} level {l} ran no seeds')
            pct = round(100 * row['success'] / row['runs'])
            bars += (f'<div class="bc-row" data-chart-level="{E(l)}" data-chart-success="{row["success"]}" data-chart-runs="{row["runs"]}">'
                     f'<span class="bc-lab">L{E(l)} · {E(row["name"])}</span>'
                     f'<span class="bc-track" title="{E(eid)} L{E(l)}: {row["success"]} / {row["runs"]}"><span class="bc-bar" style="inline-size:{pct}%"></span></span>'
                     f'<span class="bc-num">{row["success"]} / {row["runs"]}</span></div>')
        rows.append(f'<div class="bc-env" data-chart-env="{E(eid)}"><h3><code>{E(eid)}</code> {E(need_env["name"])}</h3>{bars}</div>')
    tot = BENCH['totals']
    return (f'<figure class="bchart" id="robo-chart"><figcaption class="muted">{T("robo.chart.note")}</figcaption>{"".join(rows)}'
            f'<p class="bc-total" data-chart-total="{tot["success"]}/{tot["runs"]}">{T("robo.chart.total")}: '
            f'<b>{tot["success"]} / {tot["runs"]}</b></p></figure>')


CHART_HTML = bench_chart()
# ROBO_CHART:END

# ---- ROBO_REPLAY:BEGIN (wave 16) - the episode replay viewer. rpTrace is pure (RoboCore only, no DOM) and is run
# headless by web/test_robotics.mjs; rpMount draws it. A reference run is re-run step by step from (env, seed, level)
# with the SCRIPTED policy - the same calls RoboCore.rollout makes, so its return, steps and samples are the rollout's.
# A recorded human episode (level 1, the only recorded level) is re-simulated from its stored samples, each action held
# until the next sample; the largest gap between the replayed and the stored poses is reported, never hidden.
REPLAY_HTML = (
    '<div class="robo-row"><label>' + T('robo.rp.src') + ' <select id="robo-rp-src"><option value="ref" data-i18n="robo.rp.ref">'
    + E(EN['robo.rp.ref']) + '</option></select></label>'
    '<label>' + T('robo.c.env') + ' <select id="robo-rp-env"></select></label>'
    '<label>' + T('robo.c.seed') + ' <select id="robo-rp-seed"></select></label>'
    '<label>' + T('robo.c.level') + ' <select id="robo-rp-level"></select></label>'
    '<button type="button" id="robo-rp-load">' + T('robo.rp.load') + '</button></div>'
    '<p class="muted" id="robo-rp-none" hidden>' + T('robo.rp.none') + '</p>'
    '<div class="robo-row"><button type="button" id="robo-rp-play" aria-pressed="false">' + T('robo.rp.play') + '</button>'
    '<label class="rp-scrub">' + T('robo.rp.scrub') + ' <input type="range" id="robo-rp-k" min="0" max="0" value="0" step="1"></label></div>'
    '<p class="robo-hud" id="robo-rp-read" aria-live="polite"></p>'
    '<p class="muted" id="robo-rp-mode"></p>'
    '<div class="rp-stage"><canvas id="robo-rp-arena" width="420" height="420" aria-label="replay arena"></canvas>'
    '<div class="rp-charts"><h4>' + T('robo.rp.actions') + '</h4><p class="rp-leg" id="robo-rp-leg"></p>'
    '<canvas id="robo-rp-act" width="560" height="140" aria-label="actions over time"></canvas>'
    '<h4>' + T('robo.rp.reward') + '</h4><canvas id="robo-rp-ret" width="560" height="120" aria-label="return over time"></canvas></div></div>')

REPLAY_JS = r'''/* REPLAY_CORE:BEGIN - pure: rpTrace(R, train, src) with src {kind:'ref', env, seed, level} or {kind:'ep', ep} */
function rpTrace(R, train, src) {
  var ep = src.kind === 'ep' ? src.ep : null, id = ep ? ep.env : src.env, env = R.envs[id];
  if (!env) throw new Error('replay: unknown env ' + id);
  var emb = R.embodiments[env.embodiments[0]], seed = ep ? ep.seed : src.seed, level = ep ? 1 : src.level;
  var names = env.action.fields.map(function (f) { return f.name; });
  var st = RoboCore.reset(env, emb, seed, level), layout = RoboCore.layout(env, seed, level);
  var policy = !ep || ep.actor === 'scripted-reference', every = Math.round(1 / (train.world_teleop.sample_hz * env.episode_cap.dt_s));
  var frames = [], events = {}, samples = [], held = null, si = 0, zero = {};
  names.forEach(function (n) { zero[n] = 0; });
  var mark = function () {
    st.items.forEach(function (x) { if (x.taken && !(x.id in events)) events[x.id] = st.step; if (x.binned && !((x.id + ':bin') in events)) events[x.id + ':bin'] = st.step; });
    st.targets.forEach(function (x) { if (x.visited && !(x.id in events)) events[x.id] = st.step; });
    st.gates.forEach(function (x, i) { if (i < st.next && !(x.id in events)) events[x.id] = st.step; });
  };
  var snap = function (a) { return { i: st.step, e: st.e, n: st.n, yaw: st.yaw, d: st.depth, ret: st.ret, got: st.collected,
    a: names.map(function (n) { return Math.round((Number(a[n]) || 0) * 1000) / 1000; }) }; };
  while (!st.done && (policy || st.step < ep.steps)) {
    var a;
    if (policy) a = RoboCore.policy(st);
    else { while (si < ep.samples.length && ep.samples[si].i <= st.step) { held = ep.samples[si]; si++; }
      a = {}; names.forEach(function (n, k) { a[n] = held ? held.a[k] : 0; }); }
    if (st.step % every === 0 && samples.length < train.world_teleop.max_samples) samples.push(RoboCore.sample(st, a));
    frames.push(snap(a)); RoboCore.step(st, a); mark();
  }
  frames.push(snap(zero));
  var drift = 0, r3 = function (x) { return Math.round(x * 1000) / 1000; };
  if (ep) ep.samples.forEach(function (x) { var f = frames[x.i]; if (!f) { drift = Infinity; return; }
    drift = Math.max(drift, Math.abs(r3(f.e) - x.pose[0]), Math.abs(r3(f.n) - x.pose[1]), Math.abs(r3(f.yaw) - x.pose[2])); });
  var ret = Math.round(st.ret * 1000) / 1000;
  return { env: env, emb: emb, seed: seed, level: level, names: names, layout: layout, frames: frames, events: events, samples: samples,
    steps: st.step, done: st.done || 'stopped', success: !!st.done && st.done !== 'cap', ret: ret, collected: st.collected,
    mode: policy ? 'policy' : 'held', drift: drift, exact: drift < 0.0015 && (!ep || Math.abs(ret - ep.outcome.return) < 0.0015) };
}
/* REPLAY_CORE:END */
function rpMount(data, t) {
  var R = data.robo, $ = function (s) { return document.getElementById(s); }, tr = null, k = 0, playing = false, mine = [];
  var src = $('robo-rp-src'), envSel = $('robo-rp-env'), seedSel = $('robo-rp-seed'), lvlSel = $('robo-rp-level'), rng = $('robo-rp-k');
  var COL = ['#3987e5', '#d95926', '#199e70'];   /* dataviz dark categorical slots 1-3, validated on the #0f1a1c chart surface */
  Object.keys(R.envs).forEach(function (id) { var o = document.createElement('option'); o.value = id; o.textContent = R.envs[id].name; envSel.appendChild(o); });
  function fillEnv() { var env = R.envs[envSel.value]; seedSel.textContent = ''; lvlSel.textContent = '';
    env.seeds.forEach(function (s) { var o = document.createElement('option'); o.value = s; o.textContent = s; seedSel.appendChild(o); });
    env.curriculum.levels.forEach(function (l) { var o = document.createElement('option'); o.value = l.level; o.textContent = l.level + ' · ' + l.name; lvlSel.appendChild(o); }); }
  function listMine() {
    var eps = window.__robokit ? window.__robokit.episodes() : [], keep = src.value;
    mine = eps.filter(function (x) { return R.envs[x.env] && Array.isArray(x.samples); });
    var og = src.querySelector('optgroup'); if (og) src.removeChild(og);
    og = document.createElement('optgroup'); og.label = t('robo.rp.mine'); if (mine.length) src.appendChild(og);
    mine.forEach(function (x, i) { var o = document.createElement('option'); o.value = 'ep:' + i;
      o.textContent = '#' + (i + 1) + ' · ' + x.env.replace('world.', '') + ' · ' + x.seed + ' · ' + x.actor + ' · ' + x.steps; og.appendChild(o); });
    src.value = Array.prototype.some.call(src.options, function (o) { return o.value === keep; }) ? keep : 'ref';
    $('robo-rp-none').hidden = mine.length > 0; refSel();
  }
  function refSel() { var ref = src.value === 'ref'; [envSel, seedSel, lvlSel].forEach(function (s) { s.disabled = !ref; }); }
  function load(s) {
    tr = rpTrace(R, data.train, s); k = 0; rng.max = String(tr.frames.length - 1); rng.value = '0';
    $('robo-rp-mode').textContent = tr.mode === 'policy' || tr.exact ? t('robo.rp.exact') : t('robo.rp.held') + ' ' + (isFinite(tr.drift) ? tr.drift.toFixed(3) : '-') + ' m';
    var leg = $('robo-rp-leg'); leg.textContent = '';
    tr.names.forEach(function (n, i) { var sw = document.createElement('span'); sw.className = 'rp-sw'; sw.style.background = COL[i % COL.length];
      var c = document.createElement('code'); c.textContent = n; leg.appendChild(sw); leg.appendChild(c); leg.appendChild(document.createTextNode(' ')); });
    draw(); return tr;
  }
  function loadSel() { if (src.value === 'ref') return load({ kind: 'ref', env: envSel.value, seed: Number(seedSel.value), level: Number(lvlSel.value) });
    return load({ kind: 'ep', ep: mine[Number(src.value.slice(3))] }); }
  function seek(i) { k = Math.max(0, Math.min(tr.frames.length - 1, i | 0)); rng.value = String(k); draw(); return tr.frames[k]; }
  function arena() {
    var cv = $('robo-rp-arena'), g = cv.getContext('2d'), W = cv.width, env = tr.env, H = env.world.arena_half_m, s = W / (2 * H);
    var X = function (e) { return W / 2 + e * s; }, Y = function (n) { return W / 2 - n * s; }, L = tr.layout, f = tr.frames[k], ev = tr.events;
    var at = function (id) { return id in ev && ev[id] <= f.i; };
    g.fillStyle = env.medium === 'water' ? '#0d2a3a' : '#16261d'; g.fillRect(0, 0, W, W);
    g.strokeStyle = '#2d4448'; g.lineWidth = 1; for (var q = -H; q <= H; q += 5) { g.beginPath(); g.moveTo(X(q), 0); g.lineTo(X(q), W); g.moveTo(0, Y(q)); g.lineTo(W, Y(q)); g.stroke(); }
    L.obst.forEach(function (b) { g.fillStyle = b.id.indexOf('cone') === 0 ? '#e8a33d' : '#6b7b80'; g.beginPath(); g.arc(X(b.e), Y(b.n), b.r * s, 0, 7); g.fill(); });
    L.gates.forEach(function (x) { g.strokeStyle = at(x.id) ? '#5fbf7a' : '#93a3a6'; g.lineWidth = 3; g.beginPath(); g.arc(X(x.e), Y(x.n), 1.2 * s, 0, 7); g.stroke(); });
    if (L.bin) { g.fillStyle = '#41c4d4'; g.fillRect(X(L.bin.e) - 0.7 * s, Y(L.bin.n) - 0.7 * s, 1.4 * s, 1.4 * s); }
    L.items.forEach(function (x) { if (at(x.id)) return; g.fillStyle = R.litter_colors[x.type]; g.beginPath(); g.arc(X(x.e), Y(x.n), 0.45 * s, 0, 7); g.fill(); });
    L.targets.forEach(function (x) { g.strokeStyle = at(x.id) ? '#5fbf7a' : '#fad08c'; g.lineWidth = 2; g.beginPath(); g.arc(X(x.e), Y(x.n), 1.5 * s, 0, 7); g.stroke(); });
    var path = function (to, col, w) { g.strokeStyle = col; g.lineWidth = w; g.beginPath(); for (var i = 0; i <= to; i++) { var p = tr.frames[i]; if (i) g.lineTo(X(p.e), Y(p.n)); else g.moveTo(X(p.e), Y(p.n)); } g.stroke(); };
    path(tr.frames.length - 1, 'rgba(232,237,236,0.25)', 1); path(k, '#e8edec', 2);
    var rr = Math.max(7, tr.emb.radius_m * s); g.save(); g.translate(X(f.e), Y(f.n)); g.rotate(-f.yaw);
    g.fillStyle = tr.emb.kind === 'rov' ? '#fad08c' : tr.emb.kind === 'arm-on-base' ? '#e0655b' : '#e8edec'; g.fillRect(-rr, -rr, 2 * rr, 2 * rr);
    g.fillStyle = '#12181b'; g.beginPath(); g.moveTo(0, -rr * 1.4); g.lineTo(-rr * 0.6, -rr * 0.2); g.lineTo(rr * 0.6, -rr * 0.2); g.fill(); g.restore();
  }
  function chart(id, series) {
    var cv = $(id), g = cv.getContext('2d'), W = cv.width, H = cv.height, n = tr.frames.length - 1 || 1, pad = 6;
    var X = function (i) { return pad + (W - 2 * pad) * i / n; }, Y = function (v) { return H - pad - (H - 2 * pad) * (v + 1) / 2; };
    g.fillStyle = '#0f1a1c'; g.fillRect(0, 0, W, H); g.strokeStyle = '#2d4448'; g.lineWidth = 1; g.beginPath(); g.moveTo(pad, Y(0)); g.lineTo(W - pad, Y(0)); g.stroke();
    series.forEach(function (sr) { g.strokeStyle = sr.col; g.lineWidth = 2; g.beginPath();
      tr.frames.forEach(function (f, i) { var y = Y(sr.val(f)); if (i) g.lineTo(X(i), y); else g.moveTo(X(i), y); }); g.stroke(); });
    g.strokeStyle = '#e8edec'; g.lineWidth = 1; g.beginPath(); g.moveTo(X(k), 0); g.lineTo(X(k), H); g.stroke();
  }
  function draw() {
    var f = tr.frames[k], r2 = function (x) { return (Math.round(x * 100) / 100).toFixed(2); };
    arena();
    var fields = tr.env.action.fields;
    chart('robo-rp-act', fields.map(function (fd, i) { var m = Math.max(Math.abs(fd.low), Math.abs(fd.high)) || 1;
      return { col: COL[i % COL.length], val: function (x) { return x.a[i] / m; } }; }));
    var lo = 0, hi = 0; tr.frames.forEach(function (x) { lo = Math.min(lo, x.ret); hi = Math.max(hi, x.ret); }); var span = Math.max(1e-6, hi - lo);
    chart('robo-rp-ret', [{ col: '#e8a33d', val: function (x) { return 2 * (x.ret - lo) / span - 1; } }]);
    $('robo-rp-read').textContent = t('robo.rp.scrub') + ' ' + f.i + ' / ' + tr.steps + ' · ' + (f.i * tr.env.episode_cap.dt_s).toFixed(1) + ' s · e ' + r2(f.e) + ' m · n ' + r2(f.n) + ' m · '
      + t('robo.return') + ' ' + r2(f.ret) + ' · ' + tr.names.map(function (n, i) { return n + ' ' + f.a[i]; }).join(' · ') + ' · L' + tr.level + ' · ' + tr.done;
    $('robo-rp-read').dataset.k = String(k);
  }
  function tick() { if (!playing) return; if (k >= tr.frames.length - 1) { setPlay(false); return; } seek(k + 2); requestAnimationFrame(tick); }
  function setPlay(on) { playing = on; var b = $('robo-rp-play'); b.setAttribute('aria-pressed', String(on)); b.textContent = t(on ? 'robo.rp.pause' : 'robo.rp.play');
    if (on) { if (k >= tr.frames.length - 1) seek(0); requestAnimationFrame(tick); } }
  envSel.addEventListener('change', fillEnv); src.addEventListener('focus', listMine); src.addEventListener('change', refSel);
  $('robo-rp-load').addEventListener('click', function () { setPlay(false); loadSel(); });
  $('robo-rp-play').addEventListener('click', function () { setPlay(!playing); });
  rng.addEventListener('input', function () { setPlay(false); seek(Number(rng.value)); });
  fillEnv(); listMine(); load({ kind: 'ref', env: envSel.value, seed: Number(seedSel.value), level: Number(lvlSel.value) });
  window.__roboReplay = { trace: function () { return tr; }, k: function () { return k; }, seek: seek, list: function () { listMine(); return mine.length; },
    loadRef: function (env, seed, level) { setPlay(false); src.value = 'ref'; refSel(); envSel.value = env; fillEnv(); seedSel.value = String(seed); lvlSel.value = String(level); return loadSel(); },
    loadMine: function (i) { setPlay(false); listMine(); src.value = 'ep:' + i; refSel(); return loadSel(); }, play: setPlay, playing: function () { return playing; } };
}'''
# ROBO_REPLAY:END


# wave 16: the ADDED litter-sort level 'reachable' carries its own bound, measured on its own layout (fail closed)
REACH = BENCH['per_env']['world.litter-sort']['levels'].get('4')
if not REACH or REACH['name'] != 'reachable' or 'feasibility' not in REACH:
    raise RoboticsPageError('build_robotics: the benchmark has no litter-sort level 4 (reachable) with its own feasibility bound')
REACH_F = REACH['feasibility']
REACH_HTML = (f'<p class="muted" id="robo-bench-reach">{T("robo.bench.reach")} {T("robo.bench.feas")}: '
              f'<b data-reach-feas>{REACH_F["feasible_seeds"]} / {len(BENCH["seeds"])}</b> · {T("robo.bench.ibound")}: '
              f'<b data-reach-ibound>{REACH_F["items_bound"]}</b> ({E(REACH_F["budget_m"])} m) · {T("robo.success")}: '
              f'<b data-reach-success>{REACH["success"]} / {REACH["runs"]}</b> · {T("robo.c.items")}: <b data-reach-items>{REACH["items"]}</b></p>')


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
      var ep = RoboCore.rollout(env, emb, s, data.train, 'lab', 1); n++; if (ep.outcome.success) ok++;
      var tr = document.createElement('tr'); tr.dataset.env = id;
      [id, s, ep.outcome.done, ep.steps, ep.outcome.return.toFixed(2), t(ep.outcome.success ? 'robo.yes' : 'robo.no')].forEach(function (v) {
        var td = document.createElement('td'); td.textContent = v; tr.appendChild(td); });
      tb.appendChild(tr);
    });
  });
  document.getElementById('robo-refrun-sum').textContent = ok + ' / ' + n;
  /* ANALYTICS_PANEL:BEGIN - the learner's own local dataset, computed here from localStorage episodes (window.__robokit
     .episodes()); no fetch, no upload, no digest of anything personal - the episodes carry none */
  var an = { count: 0 };
  function analytics() {
    var eps = window.__robokit.episodes(), out = { count: eps.length, steps: 0, success: 0, duration_s: 0, by_env: {}, by_actor: {},
      hist: { reverse: 0, stop: 0, forward: 0, left: 0, straight: 0, right: 0, grip: 0, dive: 0, rise: 0 }, samples: 0 };
    eps.forEach(function (ep) {
      out.steps += ep.steps; if (ep.outcome.success) out.success++; out.duration_s += ep.steps * ep.dt_s;
      out.by_env[ep.env] = (out.by_env[ep.env] || 0) + 1; out.by_actor[ep.actor] = (out.by_actor[ep.actor] || 0) + 1;
      var env = R.envs[ep.env], names = env ? env.action.fields.map(function (f) { return f.name; }) : ['v', 'w'];
      ep.samples.forEach(function (x) { out.samples++;
        var v = x.a[names.indexOf('v')], w = x.a[names.indexOf('w')];
        out.hist[v < -0.05 ? 'reverse' : v > 0.05 ? 'forward' : 'stop']++; out.hist[w > 0.05 ? 'left' : w < -0.05 ? 'right' : 'straight']++;
        if (names.indexOf('grip') >= 0 && x.a[names.indexOf('grip')] >= 0.5) out.hist.grip++;
        if (names.indexOf('vz') >= 0) { var z = x.a[names.indexOf('vz')]; if (z > 0.05) out.hist.dive++; else if (z < -0.05) out.hist.rise++; } });
    });
    return out;
  }
  function render() {
    var a = analytics(); an = a; var root = document.getElementById('robo-an');
    root.querySelector('[data-an="count"]').textContent = a.count; root.querySelector('[data-an="steps"]').textContent = a.steps;
    root.querySelector('[data-an="success"]').textContent = a.success + ' / ' + a.count;
    root.querySelector('[data-an="duration"]').textContent = a.count ? (a.duration_s / a.count).toFixed(1) : '0.0';
    document.getElementById('robo-an-empty').hidden = a.count > 0;
    var h = document.getElementById('robo-an-hist'); h.textContent = '';
    var mx = Math.max(1, a.samples);
    Object.keys(a.hist).forEach(function (k) { var row = document.createElement('div'); row.className = 'an-row'; row.dataset.bin = k;
      var lab = document.createElement('span'); lab.textContent = t('robo.an.b.' + k); var bar = document.createElement('span'); bar.className = 'an-bar';
      bar.style.inlineSize = Math.round(100 * a.hist[k] / mx) + '%'; var num = document.createElement('span'); num.textContent = a.hist[k];
      row.appendChild(lab); row.appendChild(bar); row.appendChild(num); h.appendChild(row); });
    var card = { schema: 'tc-dataset/1', preview: true, built_where: 'this browser, from this device\'s episodes only; nothing uploaded',
      schema_versions: { episode_kind: 'world-teleop/' + data.train.kind.v, robotics: R.schema, dataset: 'tc-dataset/1' },
      episodes: a.count, control_steps: a.steps, samples: a.samples, success: a.success, by_env: a.by_env, by_actor: a.by_actor,
      provenance: { envs: 'AUTHORED', policy: 'SCRIPTED', trained_models: 0 },
      note: 'A real tc-dataset/1 manifest (digests, dedupe, hashed-id splits, licence, consent scope) is built by datashare/ from packages you choose to export on the Contribute page.' };
    document.getElementById('robo-an-card').textContent = JSON.stringify(card, null, 1);
  }
  render(); setInterval(function () { if (window.__robokit.episodes().length !== an.count) render(); }, 1500);
  /* ANALYTICS_PANEL:END */
  rpMount(data, t);   /* wave 16: the episode replay viewer */
  window.__roboPage = { locale: loc, dir: I[loc].dir, classroom: classroom, refOk: ok, refN: n, analytics: analytics };
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
.an-row{{display:grid;grid-template-columns:7em 1fr 3em;gap:8px;align-items:center;font:13px ui-monospace,monospace}}
.an-bar{{display:block;block-size:12px;background:var(--tc-amber);border-radius:3px;min-inline-size:2px}}
.bchart{{margin:0 0 16px}}
.bc-env{{margin:0 0 10px}}.bc-env h3{{font-size:15px;margin:8px 0 4px}}
.bc-row{{display:grid;grid-template-columns:minmax(7em,11em) 1fr 4.5em;gap:8px;align-items:center;font:13px ui-monospace,monospace;min-block-size:24px}}
.bc-track{{display:block;block-size:14px;background:var(--tc-raised);border-radius:4px;overflow:hidden}}
.bc-bar{{display:block;block-size:100%;background:var(--tc-amber);border-radius:0 4px 4px 0}}
.bc-num{{text-align:end;font-variant-numeric:tabular-nums}}
.bc-total{{font-size:14px;margin:6px 0 0}}
.rp-stage{{display:flex;flex-wrap:wrap;gap:12px;align-items:flex-start}}
.rp-stage canvas{{background:#0f1a1c;border-radius:8px}}
#robo-rp-arena{{inline-size:min(100%,420px);aspect-ratio:1/1}}
.rp-charts{{flex:1 1 280px;min-inline-size:0}}.rp-charts canvas{{inline-size:100%;display:block}}
.rp-leg{{display:flex;flex-wrap:wrap;align-items:center;gap:4px;margin:0 0 4px;font-size:13px}}
.rp-sw{{display:inline-block;inline-size:14px;block-size:4px;border-radius:2px}}
.rp-scrub{{display:flex;align-items:center;gap:8px;flex:1 1 200px}}.rp-scrub input{{flex:1;min-block-size:44px;min-inline-size:0}}
#robo-rp .robo-row select,#robo-rp .robo-row button{{min-block-size:44px;min-inline-size:44px;font:inherit;color:var(--tc-ink);background:var(--tc-raised);border:1px solid var(--tc-line);border-radius:8px;padding:0 12px}}
#robo-rp .robo-row button[aria-pressed="true"]{{background:var(--tc-amber);color:var(--tc-amber-ink,#12181B)}}
#robo-rp .robo-hud{{font:13px/1.5 ui-monospace,monospace;color:var(--tc-muted);overflow-wrap:anywhere;min-block-size:3em}}
#robo-rp select{{max-inline-size:calc(100vw - 140px);text-overflow:ellipsis}}
#robo-rp .robo-row label{{min-inline-size:0;max-inline-size:100%}}
#robo-rp .robo-row{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 8px}}
pre.card-pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:12px ui-monospace,monospace;margin:0}}
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
<section class="box" aria-labelledby="robo-h-an" id="robo-an"><h2 id="robo-h-an" data-i18n="robo.h.an">{E(EN["robo.h.an"])}</h2>
<p class="muted" id="robo-an-note">{T("robo.an.note")}</p><p class="muted" id="robo-an-empty">{T("robo.an.empty")}</p>
<dl class="stats"><div class="st"><dt>{T("robo.an.count")}</dt><dd data-an="count">0</dd></div><div class="st"><dt>{T("robo.an.steps")}</dt><dd data-an="steps">0</dd></div>
<div class="st"><dt>{T("robo.an.success")}</dt><dd data-an="success">0 / 0</dd></div><div class="st"><dt>{T("robo.an.duration")}</dt><dd data-an="duration">0.0</dd></div></dl>
<h4>{T("robo.an.hist")}</h4><div id="robo-an-hist" aria-live="polite"></div>
<h4>{T("robo.an.card")}</h4><pre class="card-pre" id="robo-an-card"></pre></section>
<section class="box" aria-labelledby="robo-h-rp" id="robo-rp"><h2 id="robo-h-rp" data-i18n="robo.h.replay">{E(EN["robo.h.replay"])}</h2>
<p class="muted">{T("robo.rp.note")}</p>{REPLAY_HTML}</section>
<section class="box" aria-labelledby="robo-h-bench"><h2 id="robo-h-bench" data-i18n="robo.h.bench">{E(EN["robo.h.bench"])}</h2>
<p class="muted">{T("robo.bench.note")} <code>policy {E(BENCH["policy_version"])}</code> · seeds {E(", ".join(str(x) for x in BENCH["seeds"]))}</p>
<p class="muted" id="robo-bench-bound">{T("robo.bench.bound")} {T("robo.bench.feas")}: <b data-feas>{SORT_FEAS["feasible_seeds"]} / {len(BENCH["seeds"])}</b> · {T("robo.bench.ibound")}: <b data-ibound>{SORT_FEAS["items_bound"]}</b> ({E(SORT_FEAS["budget_m"])} m)</p>
{REACH_HTML}
<h3 data-i18n="robo.h.chart">{E(EN["robo.h.chart"])}</h3>{CHART_HTML}
<div class="tw"><table id="robo-bench"><thead><tr><th>{T("robo.c.env")}</th><th>{T("robo.c.level")}</th><th>{T("robo.success")}</th><th>{T("robo.c.items")}</th><th>{T("robo.steps")}</th><th>{T("robo.return")}</th></tr></thead><tbody>{bench_rows}</tbody></table></div></section>
<section class="box" aria-labelledby="robo-h-envs"><h2 id="robo-h-envs" data-i18n="robo.h.envs">{E(EN["robo.h.envs"])}</h2>{cards_env}</section>
<section class="box" aria-labelledby="robo-h-emb"><h2 id="robo-h-emb" data-i18n="robo.h.emb">{E(EN["robo.h.emb"])}</h2><div class="cards">{cards_emb}</div></section>
<section class="box links" aria-labelledby="robo-h-links"><h2 id="robo-h-links" data-i18n="robo.h.links">{E(EN["robo.h.links"])}</h2><ul>{links}</ul></section>
<p class="muted">robotics/registry/robotics.json · {E(REG["schema"])} · stamp <code data-stamp>{E(REG["source_stamp"])}</code></p>
</main>
<script type="application/json" id="robo-data">{js_json(DATA)}</script>
<script type="application/json" id="robo-i18n">{js_json(I18N)}</script>
<script id="robo-kit">{ROBO_JS}</script>
<script id="robo-replay">{REPLAY_JS}</script>
<script id="robo-page">{PAGE_JS}</script>
<script>{tjs}</script>
<script id="style-js">{STYLE_JS}</script>
</body>
</html>
'''
# ---- CLAW BEGIN (wave 18, panel) - the training-operations panel (robotics/claw/panel.py): its section goes right
# before the benchmark section, its CSS at the end of the page style, its three scripts after the page script.
_TO_AT = '<section class="box" aria-labelledby="robo-h-bench">'
for _a in (_TO_AT, '</style>\n</head>', '<script id="style-js">'):
    if page.count(_a) != 1:
        raise RoboticsPageError(f'build_robotics: the training-operations anchor {_a!r} is not unique')
page = page.replace(_TO_AT, train_ops.panel_html(T, EN) + '\n' + _TO_AT)
page = page.replace('</style>\n</head>', train_ops.CSS + '</style>\n</head>')
page = page.replace('<script id="style-js">', train_ops.scripts() + '\n<script id="style-js">')
# ---- CLAW END (panel)
# ---- ARENA BEGIN (wave 18): the model arena - policies compete continuously in one shared seeded world ------------------
# The arena section is spliced in at two fail-closed anchors. Everything it shows is READ: the policy block is
# robotics/arena/policies.js verbatim (the code robotics/arena/harness.mjs measured), the BC weights are
# robotics/arena/registry/models.json (sha256-checked here), the leaderboard and cards are robotics/arena/registry/arena.json.
# Live matches run in the reader's browser on the SIM_CORE block already on this page; the session tally is play and is
# never stored (no storage, no network), and classroom mode says so. Page markers are neutral: MODEL_ARENA.
import hashlib as _hl
_AR = json.loads((ROOT / 'robotics/arena/registry/arena.json').read_text())
_AM = json.loads((ROOT / 'robotics/arena/registry/models.json').read_text())
_POL = (ROOT / 'robotics/arena/policies.js').read_text()
_POL = _POL[_POL.index('/* MODEL_ARENA_POLICIES:BEGIN'):_POL.index('/* MODEL_ARENA_POLICIES:END */') + len('/* MODEL_ARENA_POLICIES:END */')]
_BC = [m for m in _AM['models'] if m['policy'] == 'bc']
if len(_BC) != 1 or _hl.sha256(json.dumps(_BC[0]['weights'], separators=(',', ':')).encode()).hexdigest() != _BC[0]['weights_sha256']:
    raise RoboticsPageError('build_robotics: the arena BC weights are missing or do not match their sha256 pin')
_LB = _AR['leaderboard']
for _k in ('table', 'seeds', 'rows'):
    if _k not in _LB:
        raise RoboticsPageError(f'build_robotics: arena leaderboard has no {_k}')
_HO = _AR['tables'][_LB['table']]
for _pid in _HO['policies']:
    if _pid not in _AR['cards'] or not _AR['cards'][_pid].get('what'):
        raise RoboticsPageError(f'build_robotics: arena policy {_pid} has no card - it cannot be shown')
_ci = lambda x: f'{x["mean"]:.2f} <span class="muted">[{x["ci95"][0]:.2f}, {x["ci95"][1]:.2f}]</span>'
_board = ''.join(
    f'<tr data-arena-rank="{r["rank"]}" data-arena-policy="{E(r["policy"])}"><td>{r["rank"]}</td><td>{E(r["name"])}</td>'
    f'<td><span class="tag">{E(r["kind"])}</span></td><td data-arena-success="{r["success_rate"]["mean"]}">{_ci(r["success_rate"])}</td>'
    f'<td data-arena-win="{r["win_vs_ref"]["rate"]}">{_ci({"mean": r["win_vs_ref"]["rate"], "ci95": r["win_vs_ref"]["ci95"]})}</td><td>{r["n"]}</td></tr>'
    for r in _LB['rows'])
_cards = ''.join(f'<li data-arena-card="{E(pid)}"><b>{E(c["name"])}</b> <span class="tag">{E(c["kind"])}</span> {E(c["what"])}. '
                 f'<span class="muted">{E(c["not"])}.</span></li>' for pid, c in _AR['cards'].items())
_ARENA_DATA = {
    'policies': _HO['policies'], 'cards': {k: {'name': v['name'], 'kind': v['kind']} for k, v in _AR['cards'].items()},
    'tasks': [[t['env'], t['level']] for t in _AR['tables']['all_seeds']['tasks']], 'seeds': _AR['tables']['all_seeds']['seeds'],
    'bc': _BC[0]['weights'], 'bc_sha256': _BC[0]['weights_sha256'], 'stamp': _AR['source_stamp'],
}
ARENA_HTML = (
    '<section class="box" aria-labelledby="robo-h-arena" id="model-arena" data-model-arena>'
    f'<h2 id="robo-h-arena" data-i18n="robo.h.arena">{E(EN["robo.h.arena"])}</h2><p class="muted">{T("robo.arena.note")}</p>'
    f'<p class="robo-honest" id="arena-class" hidden>{T("robo.arena.class")}</p>'
    f'<div class="robo-row"><button type="button" id="arena-play" aria-pressed="true">{T("robo.arena.pause")}</button>'
    f'<label>{T("robo.arena.speed")} <select id="arena-speed"><option value="1">1x</option><option value="4" selected>4x</option>'
    '<option value="16">16x</option></select></label></div>'
    f'<p class="robo-hud" aria-live="polite"><span>{T("robo.arena.match")}</span> <b id="arena-match">1</b> · '
    f'<span>{T("robo.arena.task")}</span> <b id="arena-task"></b></p>'
    '<div class="rp-stage"><canvas id="arena-world" width="420" height="420" aria-label="model arena world"></canvas>'
    f'<div class="tw"><table id="arena-score"><thead><tr><th>{T("robo.arena.policy")}</th><th>{T("robo.arena.progress")}</th>'
    f'<th>{T("robo.steps")}</th><th>{T("robo.return")}</th><th>{T("robo.arena.wins")}</th></tr></thead><tbody></tbody></table>'
    f'<p class="muted">{T("robo.arena.live")}</p></div></div>'
    f'<h3>{T("robo.arena.board")}</h3><p class="muted"><code>{E(_LB["table"])}</code> · seeds {E(", ".join(str(x) for x in _LB["seeds"]))} · '
    f'{E(_LB["order"])}</p><div class="tw"><table id="arena-board"><thead><tr><th>#</th><th>{T("robo.arena.policy")}</th>'
    f'<th>{T("robo.arena.kind")}</th><th>{T("robo.arena.success")}</th><th>{T("robo.arena.win")}</th><th>n</th></tr></thead>'
    f'<tbody>{_board}</tbody></table></div>'
    f'<h3>{T("robo.arena.cards")}</h3><ul id="arena-cards">{_cards}</ul>'
    f'<p class="muted">robotics/arena/registry/arena.json · {E(_AR["schema"])} · stamp <code>{E(_AR["source_stamp"])}</code> · '
    f'BC weights sha256 <code>{E(_BC[0]["weights_sha256"][:16])}</code></p></section>')
ARENA_JS = _POL + r'''
/* MODEL_ARENA:BEGIN - live matches: every carded policy on the same seeded task, side by side in one shared world */
(function () {
  'use strict';
  var A = JSON.parse(document.getElementById('model-arena-data').textContent), data = JSON.parse(document.getElementById('robo-data').textContent);
  var R = data.robo, I = JSON.parse(document.getElementById('robo-i18n').textContent), P = window.__roboPage || { locale: 'en', classroom: false };
  var t = function (k) { var L = I[P.locale] || I.en; return L.strings[k] || I.en.strings[k] || k; };
  var $ = function (s) { return document.getElementById(s); };
  var d = function (a) { return a.map(function (x) { return x / A.bc.scale; }); };
  var W = { in: A.bc.in, hidden: A.bc.hidden, out: A.bc.out, W1: d(A.bc.W1), b1: d(A.bc.b1), W2: d(A.bc.W2), b2: d(A.bc.b2) };
  var COL = { scripted: '#3987e5', greedy: '#d95926', random: '#93a3a6', bc: '#199e70' };
  var match = 0, cur = null, sts = [], acts = [], trails = [], playing = true, speed = 4, acc = 0, last = 0, hold = 0, lastRes = null;
  function snap() { return sts.map(function (st, i) { return { policy: A.policies[i], steps: st.step, done: st.done, success: st.done ? st.done !== 'cap' : null, ret: Math.round(st.ret * 1000) / 1000, collected: st.collected }; }); }
  var tally = {}; A.policies.forEach(function (p) { tally[p] = { wins: 0, ties: 0, played: 0 }; });
  if (P.classroom) $('arena-class').hidden = false;
  /* the match schedule is seeded too: match m -> (task, seed) from mulberry32(hash('model-arena|' + m)) */
  function schedule(m) { var r = ArenaPolicies.mulberry32(ArenaPolicies.hash('model-arena|' + m)), tk = A.tasks[Math.floor(r() * A.tasks.length)];
    return { env: tk[0], level: tk[1], seed: A.seeds[Math.floor(r() * A.seeds.length)] }; }
  function start() {
    cur = schedule(match); var env = R.envs[cur.env], emb = R.embodiments[env.embodiments[0]];
    sts = A.policies.map(function () { return RoboCore.reset(env, emb, cur.seed, cur.level); });
    acts = A.policies.map(function (p) { return ArenaPolicies.make(p, { RoboCore: RoboCore, env: env, seed: cur.seed, level: cur.level, model: W }); });
    trails = A.policies.map(function () { return [[0, 0]]; });
    $('arena-match').textContent = String(match + 1);
    $('arena-task').textContent = env.name + ' · L' + cur.level + ' · seed ' + cur.seed;
  }
  function total(st) { var o = st.env.objects; return o.gates || o.litter || o.targets; }
  function score() {   /* success first, then return - the harness's paired rule */
    var res = sts.map(function (st) { return [st.done !== 'cap' ? 1 : 0, Math.round(st.ret * 1000) / 1000]; });
    var best = res.reduce(function (b, r) { return r[0] > b[0] || (r[0] === b[0] && r[1] > b[1]) ? r : b; }, [-1, -Infinity]);
    var top = res.filter(function (r) { return r[0] === best[0] && r[1] === best[1]; }).length;
    A.policies.forEach(function (p, i) { tally[p].played++; if (res[i][0] === best[0] && res[i][1] === best[1]) { if (top > 1) tally[p].ties++; else tally[p].wins++; } });
  }
  function step() {
    if (!cur) start();
    var live = 0;
    sts.forEach(function (st, i) { if (!st.done) { RoboCore.step(st, acts[i](st)); trails[i].push([st.e, st.n]); } if (!st.done) live++; });
    if (!live) { lastRes = { task: cur, states: snap() }; score(); match++; start(); return true; }
    return false;
  }
  function row() {
    var tb = $('arena-score').tBodies[0]; tb.textContent = '';
    A.policies.forEach(function (p, i) { var st = sts[i], tr = document.createElement('tr'); tr.setAttribute('data-arena-live', p);
      [A.cards[p].name, st.collected + ' / ' + total(st) + (st.done ? (st.done === 'cap' ? ' · cap' : ' ✓') : ''), String(st.step), st.ret.toFixed(2),
        tally[p].wins + (tally[p].ties ? ' (+' + tally[p].ties + ')' : '') + ' / ' + tally[p].played].forEach(function (x, j) {
        var td = document.createElement('td'); if (!j) { var sw = document.createElement('span'); sw.className = 'arena-sw'; sw.style.background = COL[p] || '#e8edec'; td.appendChild(sw); }
        td.appendChild(document.createTextNode(x)); tr.appendChild(td); }); tb.appendChild(tr); });
  }
  function draw() {
    var cv = $('arena-world'), g = cv.getContext('2d'), Wd = cv.width, st0 = sts[0], env = st0.env, H = env.world.arena_half_m, s = Wd / (2 * H);
    var X = function (e) { return Wd / 2 + e * s; }, Y = function (n) { return Wd / 2 - n * s; };
    g.fillStyle = env.medium === 'water' ? '#0d2a3a' : '#16261d'; g.fillRect(0, 0, Wd, Wd);
    g.strokeStyle = '#2d4448'; g.lineWidth = 1; for (var q = -H; q <= H; q += 5) { g.beginPath(); g.moveTo(X(q), 0); g.lineTo(X(q), Wd); g.moveTo(0, Y(q)); g.lineTo(Wd, Y(q)); g.stroke(); }
    st0.obst.forEach(function (b) { g.fillStyle = b.id.indexOf('cone') === 0 ? '#e8a33d' : '#6b7b80'; g.beginPath(); g.arc(X(b.e), Y(b.n), b.r * s, 0, 7); g.fill(); });
    st0.gates.forEach(function (x) { g.strokeStyle = '#93a3a6'; g.lineWidth = 2; g.beginPath(); g.arc(X(x.e), Y(x.n), 1.2 * s, 0, 7); g.stroke(); });
    if (st0.bin) { g.fillStyle = '#41c4d4'; g.fillRect(X(st0.bin.e) - 0.7 * s, Y(st0.bin.n) - 0.7 * s, 1.4 * s, 1.4 * s); }
    st0.items.forEach(function (x, k) { var left = sts.filter(function (st) { return !st.items[k].taken; }).length; if (!left) return;
      g.globalAlpha = 0.35 + 0.65 * left / sts.length; g.fillStyle = R.litter_colors[x.type]; g.beginPath(); g.arc(X(x.e), Y(x.n), 0.45 * s, 0, 7); g.fill(); g.globalAlpha = 1; });
    st0.targets.forEach(function (x) { g.strokeStyle = '#fad08c'; g.lineWidth = 2; g.beginPath(); g.arc(X(x.e), Y(x.n), 1.5 * s, 0, 7); g.stroke(); });
    sts.forEach(function (st, i) { var col = COL[A.policies[i]] || '#e8edec', tr = trails[i];
      g.strokeStyle = col; g.globalAlpha = 0.55; g.lineWidth = 1.5; g.beginPath(); tr.forEach(function (p, j) { if (j) g.lineTo(X(p[0]), Y(p[1])); else g.moveTo(X(p[0]), Y(p[1])); }); g.stroke(); g.globalAlpha = 1;
      var rr = Math.max(6, st.emb.radius_m * s); g.save(); g.translate(X(st.e), Y(st.n)); g.rotate(-st.yaw); g.fillStyle = col; g.fillRect(-rr, -rr, 2 * rr, 2 * rr);
      g.fillStyle = '#12181b'; g.beginPath(); g.moveTo(0, -rr * 1.4); g.lineTo(-rr * 0.6, -rr * 0.2); g.lineTo(rr * 0.6, -rr * 0.2); g.fill(); g.restore(); });
  }
  function frame(ts) {
    var dt = last ? Math.min(0.25, (ts - last) / 1000) : 0; last = ts;
    if (playing) { if (hold > 0) hold -= dt; else { acc += dt * 10 * speed; var n = Math.floor(acc); acc -= n; for (var k = 0; k < n; k++) if (step()) { hold = 1.2; acc = 0; break; } } }
    draw(); row(); requestAnimationFrame(frame);
  }
  $('arena-play').addEventListener('click', function () { playing = !playing; this.setAttribute('aria-pressed', String(playing));
    this.textContent = t(playing ? 'robo.arena.pause' : 'robo.arena.resume'); });
  $('arena-speed').addEventListener('change', function () { speed = Number(this.value) || 1; });
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) { playing = false; $('arena-play').setAttribute('aria-pressed', 'false'); $('arena-play').textContent = t('robo.arena.resume'); }
  start(); draw(); row(); requestAnimationFrame(frame);
  /* test hook: advance whole steps without the clock; state is read-only copies */
  window.__modelArena = { schedule: schedule, match: function () { return match; }, task: function () { return cur; }, tally: function () { return JSON.parse(JSON.stringify(tally)); },
    step: function (n) { var done = 0; for (var k = 0; k < n; k++) if (step()) done++; draw(); row(); return done; },
    states: snap, last: function () { return lastRes; },
    pause: function () { playing = false; }, playing: function () { return playing; }, policies: A.policies.slice(), stores: 'nothing' };
})();
/* MODEL_ARENA:END */'''
_marker = '<section class="box" aria-labelledby="robo-h-envs">'
if page.count(_marker) != 1 or page.count('<script id="style-js">') != 1:
    raise RoboticsPageError('build_robotics: the arena anchors are missing from the page')
page = page.replace(_marker, ARENA_HTML + '\n' + _marker, 1)
page = page.replace('<script id="style-js">', f'<script type="application/json" id="model-arena-data">{js_json(_ARENA_DATA)}</script>\n'
                    f'<script id="model-arena-js">{ARENA_JS}</script>\n<script id="style-js">', 1)
page = page.replace('</style>', '#arena-world{inline-size:min(100%,420px);aspect-ratio:1/1}.arena-sw{display:inline-block;inline-size:.8em;'
                    'block-size:.8em;border-radius:2px;margin-inline-end:.4em;vertical-align:-1px}</style>', 1)
# ---- ARENA END ------------------------------------------------------------------------------------------------------------
TITLE = 'SmartCiti.X : Trade Craft Academy — ' + EN['robo.nav']
page = apply_seo(page, PAGE, TITLE, EN['robo.seo.desc'], 'page')
emit(HERE / 'trade_craft_robotics.html', page,
     f'{C["envs"]} env specs | {C["embodiments"]} embodiments | trained models {C["trained_models"]} | stamp {REG["source_stamp"]}')
