#!/usr/bin/env python3
"""web/fieldkit.py - seasons & harvest play for the walkable worlds (FIELDS, wave 12).

An embeddable kit, the way web/robokit.py is: a page section below the stage plus a tail before </body>, its own
fields.* catalogue ([data-fk-i18n], so the host page's catalogue is unchanged), and
ONE scene mount for the 3D plot markers.

- Season clock: GAME time (seconds of play per game day; pause / 1x / 4x / 16x from seasons/registry game_clock),
  month selectable; months are "approximate, game calendar".
- Farm-plot mini-game: pick a plot (AUTHORED, on AUTHORED land use - seasons/registry plots) and an in-season task,
  then step through its stages (prepare -> plant -> tend -> harvest) inside each stage's timing window in game days.
  Too early: wait. Too late: the task starts again from its first stage. Seeded and deterministic (FieldCore).
- Seasonal board: a hudkit panel (#fk-board, slot te; its list folds away under 600 px) listing what is in season now in this world.
- Harvest log: device-local (localStorage "tc-fields-v1", try/catch; memory-only if storage throws). PLAY: never a
  completion record, never money. A finished task reports a treasure through TCQuests.find (GAMES_CONTRACT s.3) when
  the page carries that quest; otherwise nothing is reported.
- 3D: every plot of the loaded parishes/counties is TWO instances (bed + post) of ONE InstancedMesh (1 draw call),
  drawn only while the player has the plots shown (Start / Go to plot / Show plots) and never in the overview - with
  the plots hidden the kit costs 0 draw calls, so the page's eval rows are not moved by it.

Python API (fail closed):
    from fieldkit import fields_section_html, fields_tail, fields_scene_js, fields_board_html, FIELDS_HUD_PANEL
"""
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REG = ROOT / 'seasons' / 'registry' / 'seasons.json'
WORLDS = {'parishes': 'louisiana', 'bay': 'bay'}
STORAGE_KEY = 'tc-fields-v1'
MAX_PLOTS = 66   # instance budget / 2; checked against the registry


class FieldKitError(KeyError):
    """A missing registry field, locale key or world (named, so the build stops on it)."""


def _need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise FieldKitError(f'fieldkit: {where} has no field {k!r}')
    return d[k]


def fields_data(world):
    """The JSON the page embeds for one world: its region's tasks, calendar, rotations, plots, clock and honesty."""
    if world not in WORLDS:
        raise FieldKitError(f'fieldkit: unknown world {world!r} (known: {sorted(WORLDS)})')
    if not REG.exists():
        raise FieldKitError('fieldkit: seasons/registry/seasons.json is not built (python3 seasons/build.py)')
    r = json.loads(REG.read_text())
    region = WORLDS[world]
    tasks = [t for t in _need(r, 'tasks', 'seasons.json') if _need(t, 'region', 'task') == region]
    plots = {f: _need(w, 'plots', f) for f, w in _need(r, 'plots', 'seasons.json').items() if _need(w, 'region', f) == region}
    n = sum(len(v) for v in plots.values())
    if not tasks or not plots:
        raise FieldKitError(f'fieldkit: seasons.json holds no tasks or plots for region {region!r}')
    if n > MAX_PLOTS:
        raise FieldKitError(f'fieldkit: {n} plots > instance budget {MAX_PLOTS}')
    return {
        'world': world, 'region': region, 'stamp': _need(r, 'source_stamp', 'seasons.json'),
        'clock': _need(r, 'game_clock', 'seasons.json'), 'honesty': _need(r, 'honesty', 'seasons.json'),
        'calendar': _need(_need(r, 'calendar', 'seasons.json'), region, 'seasons.json#calendar'),
        'safety': _need(r, 'safety', 'seasons.json'), 'tasks': tasks,
        'rotations': [x for x in _need(r, 'rotations', 'seasons.json') if _need(x, 'region', 'rotation') == region],
        'plots': plots, 'storage': STORAGE_KEY,
    }


FIELDS_I18N_KEYS = ['fields.panel', 'fields.lede', 'fields.clock', 'fields.month', 'fields.speed', 'fields.pause',
                    'fields.day', 'fields.board', 'fields.plot', 'fields.task', 'fields.start', 'fields.step',
                    'fields.goto', 'fields.show', 'fields.log', 'fields.clear', 'fields.early', 'fields.late',
                    'fields.done', 'fields.off_season', 'fields.window', 'fields.anywhere', 'fields.safety',
                    'fields.empty', 'fields.nostore', 'fields.play', 'fields.calendar', 'fields.points',
                    'fields.hud.board']


def fields_catalog():
    """{locale: {dir, strings}} for the 8 locales - fail closed on a missing or empty key."""
    out = {}
    for f in sorted((ROOT / 'i18n/locales').glob('*.json')):
        c = json.loads(f.read_text(encoding='utf-8'))
        st = _need(c, 'strings', f.name)
        miss = [k for k in FIELDS_I18N_KEYS if k not in st or not isinstance(st[k], str) or not st[k].strip()]
        if miss:
            raise FieldKitError(f'fieldkit: locale {f.name} is missing {miss[:5]}')
        out[_need(c, 'locale', f.name)] = {'dir': _need(c, 'dir', f.name), 'strings': {k: st[k] for k in FIELDS_I18N_KEYS}}
    if len(out) != 8 or 'en' not in out:
        raise FieldKitError(f'fieldkit: expected 8 locales incl. en, found {sorted(out)}')
    return out


def _T(k):
    return f'<span data-fk-i18n="{k}">{html.escape(fields_catalog()["en"]["strings"][k])}</span>'


# compact 'none': the board needs no host-catalogue key (UX owns hud.*); under 600 px its list folds away by CSS and
# only the month + the link to the section stay (NEEDS UX: a hud.open.fields key would let it fold to an icon)
FIELDS_HUD_PANEL = {'id': 'fields', 'kind': 'panel', 'sel': '#fk-board', 'slot': 'te', 'order': 2, 'compact': 'none'}


def fields_board_html():
    """The seasonal board the HUD layout manager adopts into its top-end slot (placed inside the stage)."""
    return (f'<div id="fk-board" class="tc-panel fk-board" aria-live="polite"><b>{_T("fields.hud.board")}</b> '
            f'<span id="fk-board-when"></span><ul id="fk-board-list"></ul>'
            f'<a href="#fields" class="fk-open">{_T("fields.panel")}</a></div>')


def fields_section_html(world):
    d = fields_data(world)
    h = d['honesty']
    return (f'<section class="fk" id="fields" data-fields-world="{world}" aria-labelledby="fk-h">'
            f'<h2 id="fk-h">{_T("fields.panel")}</h2><p class="fk-note">{_T("fields.lede")}</p>'
            f'<div class="fk-row" role="group" aria-label="clock"><b>{_T("fields.clock")}</b>'
            f'<label>{_T("fields.month")} <select id="fk-month"></select></label>'
            f'<span>{_T("fields.speed")}</span><span id="fk-speeds" class="fk-row"></span>'
            f'<span id="fk-now" class="fk-now" aria-live="polite"></span>'
            f'<span class="fk-tag">{_T("fields.calendar")}</span></div>'
            f'<div class="fk-cols"><div><h3>{_T("fields.board")}</h3><ul id="fk-list" class="fk-list"></ul></div>'
            f'<div><h3>{_T("fields.plot")}</h3>'
            f'<div class="fk-row"><label>{_T("fields.plot")} <select id="fk-plot"></select></label>'
            f'<label>{_T("fields.task")} <select id="fk-task"></select></label>'
            f'<button type="button" id="fk-start">{_T("fields.start")}</button>'
            f'<button type="button" id="fk-goto">{_T("fields.goto")}</button>'
            f'<button type="button" id="fk-show" aria-pressed="false">{_T("fields.show")}</button></div>'
            f'<canvas id="fk-canvas" width="360" height="120" aria-hidden="true"></canvas>'
            f'<p id="fk-stage" class="fk-now" aria-live="polite"></p>'
            f'<button type="button" id="fk-step" class="fk-big" disabled>{_T("fields.step")}</button>'
            f'<p id="fk-msg" class="fk-note" role="status"></p>'
            f'<h3>{_T("fields.log")}</h3><ol id="fk-log" class="fk-list"></ol>'
            f'<button type="button" id="fk-clear">{_T("fields.clear")}</button></div></div>'
            f'<p class="fk-note">{_T("fields.play")}</p>'
            f'<p class="fk-note" lang="en">{html.escape(h["calendar"])} {html.escape(h["plots"])} {html.escape(h["facts"])} '
            f'{html.escape(h["rules"])} {html.escape(h["safety"])}</p>'
            f'<p class="fk-note" id="fk-nostore" hidden>{_T("fields.nostore")}</p></section>')


FIELDS_CSS = r'''
.fk{border:1px solid var(--tc-line,#28353A);border-radius:10px;padding:12px;margin:16px 0;background:var(--tc-panel,#182023);color:var(--tc-ink,#E8EDEC);min-inline-size:0}
.fk h2,.fk h3{margin:0 0 8px}.fk h3{font-size:17px;margin-top:8px}
.fk-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 8px}
.fk select,.fk button{min-block-size:44px;min-inline-size:44px;font:inherit;color:var(--tc-ink,#E8EDEC);background:var(--tc-raised,#1E282B);border:1px solid var(--tc-line,#28353A);border-radius:8px;padding:0 12px;cursor:pointer;max-inline-size:100%}
.fk button[aria-pressed="true"]{background:var(--tc-amber,#E8A33D);color:var(--tc-amber-ink,#12181B)}
.fk button:disabled{opacity:.6;cursor:not-allowed}
.fk .fk-big{inline-size:100%;font-weight:700}
.fk-cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:16px}
.fk-list{margin:0;padding-inline-start:20px;overflow-wrap:anywhere}.fk-list li{margin:0 0 8px}
.fk-note,.fk-list small{color:var(--tc-muted,#93A3A6);font-size:14px;overflow-wrap:anywhere}
.fk-now{font:14px/1.5 ui-monospace,monospace;overflow-wrap:anywhere}
.fk-tag{font:600 12px/1 ui-monospace,monospace;background:var(--tc-raised,#1E282B);border-radius:4px;padding:4px 6px;color:var(--tc-muted,#93A3A6)}
.fk canvas{display:block;inline-size:100%;max-inline-size:360px;block-size:auto;background:var(--tc-raised,#1E282B);border-radius:8px;margin:0 0 8px}
.fk-board{padding:6px 10px;max-inline-size:280px;font-size:13px;line-height:1.35}
.fk-board ul{display:flex;flex-wrap:wrap;gap:2px 10px;margin:2px 0;padding:0;list-style:none}.fk-board li::before{content:"\2022 ";color:var(--tc-amber,#E8A33D)}
.fk-board .fk-open{display:inline-flex;align-items:center;min-block-size:44px;line-height:1.2}
[data-hud-compact] .fk-board ul{display:none}@media(max-width:600px){.fk-board ul{display:none}}
'''

FIELDS_JS = r'''
/* FIELDS_CORE:BEGIN - pure core (no DOM): game clock, in-season board, staged task windows, seeded tips */
const FieldCore = (() => {
  const need = (o, k, w) => { if (o === null || typeof o !== 'object' || !(k in o)) throw new Error('fieldkit: ' + w + ' has no ' + k); return o[k]; };
  function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  const hash = (s) => { let h = 2166136261; for (const c of String(s)) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; };
  function clock(data) { const c = need(data, 'clock', 'data');
    return { month: need(c, 'start_month', 'clock'), day: 0, t: 0, speed: '1x', dpm: need(c, 'days_per_month', 'clock'), speeds: need(c, 'speeds', 'clock') }; }
  function setSpeed(ck, id) { if (!ck.speeds.some((s) => s.id === id)) throw new Error('fieldkit: unknown speed ' + id); ck.speed = id; }
  function setMonth(ck, m) { if (!(Number.isInteger(m) && m >= 1 && m <= 12)) throw new Error('fieldkit: month ' + m); ck.month = m; ck.day = 0; }
  /* advance by dtS real seconds; returns game days advanced */
  function tick(ck, dtS) {
    const sp = ck.speeds.find((s) => s.id === ck.speed); if (!sp) throw new Error('fieldkit: speed ' + ck.speed);
    if (!(sp.s_per_day > 0) || !(dtS > 0)) return 0;
    const dd = dtS / sp.s_per_day; ck.t += dd; ck.day += dd;
    while (ck.day >= ck.dpm) { ck.day -= ck.dpm; ck.month = ck.month % 12 + 1; }
    return dd;
  }
  const task = (data, id) => { const t = need(data, 'tasks', 'data').find((x) => x.id === id); if (!t) throw new Error('fieldkit: no task ' + id); return t; };
  function inSeason(data, month) {
    const m = need(data, 'calendar', 'data').months.find((x) => x.month === month); if (!m) throw new Error('fieldkit: no calendar month ' + month);
    return m.in_season.map((id) => task(data, id));
  }
  /* start a task on a plot (plot tasks) or anywhere (events); refuses what is not in season this game month */
  function start(data, ck, plotId, taskId) {
    const t = task(data, taskId);
    if (!t.months.includes(ck.month)) return { ok: false, why: 'off_season' };
    if (t.plot && !plotId) return { ok: false, why: 'no_plot' };
    return { ok: true, st: { plot: t.plot ? plotId : null, task: taskId, i: 0, last: ck.t, points: 0, month: ck.month } };
  }
  function windowOf(data, st, ck) {
    const t = task(data, st.task), s = t.stages[st.i], [lo, hi] = s.window_days, el = ck.t - st.last;
    return { stage: s, n: st.i, of: t.stages.length, el, lo, hi, state: el < lo ? 'wait' : el > hi ? 'closed' : 'open' };
  }
  /* do the current stage: inside the window it advances (3 play points in the middle third, else 2); early = wait;
     late = the task starts again from its first stage (a lost crop in the game - no penalty kept) */
  function act(data, st, ck) {
    const w = windowOf(data, st, ck);
    if (w.state === 'wait') return { ok: false, why: 'early', wait: w.lo - w.el };
    if (w.state === 'closed') { st.i = 0; st.last = ck.t; st.points = 0; return { ok: false, why: 'late' }; }
    const third = (w.hi - w.lo) / 3, mid = w.el >= w.lo + third && w.el <= w.hi - third;
    st.points += (mid || w.hi === w.lo) ? 3 : 2; st.i++; st.last = ck.t;
    if (st.i >= task(data, st.task).stages.length) return { ok: true, done: true, points: st.points };
    return { ok: true, done: false };
  }
  /* the seeded tip: which safety note of the task a (seed, month, plot) shows - same inputs, same tip */
  function tip(data, seed, month, plotId, taskId) {
    const t = task(data, taskId), r = mulberry32(hash(seed + ':' + month + ':' + plotId + ':' + taskId))();
    return need(data, 'safety', 'data')[t.safety[Math.floor(r * t.safety.length)]];
  }
  function questId(t) { return 'treasure-fields-' + (t.kind === 'event' ? 'event-' : 'harvest-') + t.id; }
  return { clock, setSpeed, setMonth, tick, inSeason, start, act, windowOf, tip, questId, task, mulberry32, hash };
})();
/* FIELDS_CORE:END */

function fieldsMount(root, data, opts) {
  const t = opts.t, $ = (id) => { const e = document.getElementById(id); if (!e) throw new Error('fieldkit: #' + id + ' missing'); return e; };
  const SEED = opts.seed, lang = document.documentElement.lang || 'en';
  let store = null; try { store = window.localStorage; store.getItem('x'); } catch (e) { store = null; }
  const load = () => { if (!store) return null; try { const v = JSON.parse(store.getItem(data.storage) || 'null'); return v && v.v === 1 ? v : null; } catch (e) { return null; } };
  const S = load() || { v: 1, log: [], run: null, month: data.clock.start_month };
  const save = () => { if (!store) return; try { store.setItem(data.storage, JSON.stringify(S)); } catch (e) { /* memory only */ } };
  if (!store) $('fk-nostore').hidden = false;
  const ck = FieldCore.clock(data); FieldCore.setMonth(ck, S.month);
  if (S.run) { S.run.last = 0; }   // game time restarts at 0 on a new visit; the stage window restarts with it
  let shown = false;
  const monthName = (m) => { try { return new Intl.DateTimeFormat(lang, { month: 'long' }).format(new Date(2026, m - 1, 15)); } catch (e) { return String(m); } };
  const ms = $('fk-month');
  for (let m = 1; m <= 12; m++) { const o = document.createElement('option'); o.value = m; o.textContent = monthName(m); ms.appendChild(o); }
  ms.addEventListener('change', () => { FieldCore.setMonth(ck, +ms.value); S.month = ck.month; save(); render(); });
  $('fk-task').addEventListener('change', () => draw());
  const sp = $('fk-speeds');
  for (const s of data.clock.speeds) { const b = document.createElement('button'); b.type = 'button'; b.dataset.speed = s.id;
    b.textContent = s.id === 'pause' ? t('fields.pause') : s.id; b.setAttribute('aria-pressed', String(s.id === ck.speed));
    b.addEventListener('click', () => { FieldCore.setSpeed(ck, s.id); sp.querySelectorAll('button').forEach((x) => x.setAttribute('aria-pressed', String(x.dataset.speed === s.id))); }); sp.appendChild(b); }
  const plotsAll = Object.entries(data.plots).flatMap(([f, ps]) => ps.map((p) => ({ ...p, fips: f })));
  const plotSel = $('fk-plot'), taskSel = $('fk-task');
  function fillPlots() {
    const here = window.__fields && window.__fields.current ? window.__fields.current() : null;
    const list = plotsAll.filter((p) => !here || p.fips === here), use = list.length ? list : plotsAll, keep = plotSel.value;
    plotSel.textContent = '';
    for (const p of use) { const o = document.createElement('option'); o.value = p.id; o.textContent = p.id + ' (' + p.land_use + ')'; plotSel.appendChild(o); }
    if (use.some((p) => p.id === keep)) plotSel.value = keep;
  }
  function fillTasks() {
    const keep = taskSel.value; taskSel.textContent = '';
    for (const x of FieldCore.inSeason(data, ck.month)) { const o = document.createElement('option'); o.value = x.id;
      o.textContent = x.label + (x.plot ? '' : ' - ' + t('fields.anywhere')); taskSel.appendChild(o); }
    if ([...taskSel.options].some((o) => o.value === keep)) taskSel.value = keep;
  }
  const msg = (k, extra) => { $('fk-msg').textContent = t(k) + (extra ? ' ' + extra : ''); };
  function board() {
    const now = FieldCore.inSeason(data, ck.month);
    $('fk-board-when').textContent = monthName(ck.month);
    const bl = $('fk-board-list'); bl.textContent = '';
    for (const x of now.slice(0, 4)) { const li = document.createElement('li'); li.textContent = x.label; li.lang = 'en'; bl.appendChild(li); }
    const ul = $('fk-list'); ul.textContent = '';
    for (const x of now) {
      const li = document.createElement('li'); li.dataset.task = x.id;
      const b = document.createElement('b'); b.textContent = x.label; b.lang = 'en'; li.appendChild(b);
      const sm = document.createElement('small'); sm.lang = 'en';
      const rot = x.rotation ? data.rotations.find((r) => r.id === x.rotation) : null;
      sm.textContent = ' ' + x.fact + (rot ? ' ' + rot.text : '') + ' ' + t('fields.safety') + ': ' + x.safety.map((k) => data.safety[k]).join(' ');
      li.appendChild(document.createElement('br')); li.appendChild(sm); ul.appendChild(li);
    }
  }
  function logView() {
    const ol = $('fk-log'); ol.textContent = '';
    if (!S.log.length) { const li = document.createElement('li'); li.textContent = t('fields.empty'); ol.appendChild(li); return; }
    for (const e of S.log.slice(-12).reverse()) { const li = document.createElement('li'); li.dataset.log = e.task;
      li.textContent = monthName(e.month) + ' · ' + FieldCore.task(data, e.task).label + (e.plot ? ' · ' + e.plot : '') + ' · ' + e.points + ' ' + t('fields.points'); ol.appendChild(li); }
  }
  const cv = $('fk-canvas'), cx = cv.getContext('2d');
  function draw() {
    const W = cv.width, H = cv.height; cx.clearRect(0, 0, W, H);
    if (!S.run) {   // idle: the selected task's months on the 12-month game calendar, this game month outlined
      const sel = taskSel.value ? FieldCore.task(data, taskSel.value) : null, cw = (W - 20) / 12;
      for (let m = 1; m <= 12; m++) { cx.fillStyle = sel && sel.months.includes(m) ? '#3F8F4F' : '#28353A'; cx.fillRect(10 + (m - 1) * cw, 40, cw - 3, 34);
        if (m === ck.month) { cx.strokeStyle = '#E8A33D'; cx.lineWidth = 3; cx.strokeRect(10 + (m - 1) * cw, 38, cw - 3, 38); }
        cx.fillStyle = '#E8EDEC'; cx.font = '11px ui-monospace,monospace'; cx.fillText(monthName(m).slice(0, 3), 12 + (m - 1) * cw, 92); }
      if (sel) { cx.font = '12px ui-monospace,monospace'; cx.fillText(sel.label, 10, 25); }
      return;
    }
    const w = FieldCore.windowOf(data, S.run, ck), x = FieldCore.task(data, S.run.task), span = Math.max(w.hi + 2, 4), px = (d) => 10 + (W - 20) * Math.min(d, span) / span;
    cx.fillStyle = '#5a4632'; cx.fillRect(10, 50, W - 20, 22);               // soil
    cx.fillStyle = '#3F8F4F'; cx.fillRect(px(w.lo), 50, Math.max(3, px(w.hi) - px(w.lo)), 22);   // the window
    cx.fillStyle = '#E8A33D'; cx.fillRect(px(w.el) - 2, 40, 4, 42);           // now
    for (let i = 0; i < w.of; i++) { cx.fillStyle = i < w.n ? '#3F8F4F' : i === w.n ? '#E8A33D' : '#28353A'; cx.fillRect(10 + i * 26, 10, 20, 20); }
    cx.fillStyle = '#E8EDEC'; cx.font = '12px ui-monospace,monospace'; cx.fillText(x.label, 10 + w.of * 26 + 6, 25);
  }
  function stageView() {
    const btn = $('fk-step'), st = $('fk-stage');
    if (!S.run) { btn.disabled = true; btn.textContent = t('fields.step'); delete btn.dataset.state; st.textContent = ''; draw(); return; }
    const w = FieldCore.windowOf(data, S.run, ck);
    btn.disabled = false; btn.dataset.state = w.state;
    st.textContent = (w.n + 1) + '/' + w.of + ' · ' + w.stage.label + ' · ' + t('fields.window').replace('{lo}', w.lo).replace('{hi}', w.hi)
      + ' · ' + t('fields.day') + ' ' + w.el.toFixed(1);
    st.lang = 'en'; btn.textContent = w.stage.label; draw();
  }
  function render() {
    ms.value = String(ck.month); fillTasks(); fillPlots(); board(); logView(); stageView();
    $('fk-now').textContent = monthName(ck.month) + ' · ' + t('fields.day') + ' ' + (Math.floor(ck.day) + 1) + '/' + ck.dpm;
  }
  function report(x) {
    const T = window.TCQuests, id = FieldCore.questId(x);
    if (!T || !T.data || !T.data.quests.some((q) => q.id === id)) return null;
    return T.find(id);
  }
  function setShown(v) { shown = v; $('fk-show').setAttribute('aria-pressed', String(v)); }
  $('fk-show').addEventListener('click', () => setShown(!shown));
  $('fk-start').addEventListener('click', () => {
    const r = FieldCore.start(data, ck, plotSel.value, taskSel.value);
    if (!r.ok) { msg(r.why === 'off_season' ? 'fields.off_season' : 'fields.early'); return; }
    S.run = r.st; save(); setShown(true);
    msg('fields.start', '- ' + FieldCore.tip(data, SEED, ck.month, r.st.plot || 'anywhere', r.st.task)); render();
  });
  $('fk-goto').addEventListener('click', () => { if (window.__fields && window.__fields.goto) { setShown(true); window.__fields.goto(S.run && S.run.plot ? S.run.plot : plotSel.value); } });
  $('fk-step').addEventListener('click', () => {
    if (!S.run) return;
    const r = FieldCore.act(data, S.run, ck);
    if (!r.ok) { msg(r.why === 'early' ? 'fields.early' : 'fields.late'); save(); stageView(); return; }
    if (r.done) {
      const x = FieldCore.task(data, S.run.task);
      S.log.push({ task: x.id, plot: S.run.plot, month: ck.month, points: r.points }); S.run = null;
      msg('fields.done', '(' + r.points + ' ' + t('fields.points') + ')'); report(x);
      root.dispatchEvent(new CustomEvent('tc-fields', { bubbles: true, detail: { name: 'harvest', task: x.id, points: r.points } }));
    }
    save(); render();
  });
  $('fk-clear').addEventListener('click', () => { S.log = []; S.run = null; save(); render(); });
  let last = performance.now(), acc = 0, m0 = ck.month;
  function loop(now) {
    const dt = Math.min(0.25, (now - last) / 1000); last = now; FieldCore.tick(ck, dt); acc += dt;
    if (ck.month !== m0) { m0 = ck.month; S.month = ck.month; save(); render(); }
    else if (acc > 0.25) { acc = 0; $('fk-now').textContent = monthName(ck.month) + ' · ' + t('fields.day') + ' ' + (Math.floor(ck.day) + 1) + '/' + ck.dpm; stageView(); }
    requestAnimationFrame(loop);
  }
  render(); requestAnimationFrame(loop);
  const api = {
    clock: () => ({ ...ck, speeds: undefined }), state: () => JSON.parse(JSON.stringify(S)), shown: () => shown, setShown,
    phaseOf(plotId) { if (!S.run || S.run.plot !== plotId) return null; return FieldCore.windowOf(data, S.run, ck).stage.phase; },
    advance(days) { const sp0 = ck.speed; ck.speed = data.clock.speeds.find((s) => s.s_per_day > 0).id;
      const spd = data.clock.speeds.find((s) => s.id === ck.speed).s_per_day; FieldCore.tick(ck, days * spd); ck.speed = sp0; render(); return ck.t; },
    select(plotId, taskId) { fillPlots(); if (plotId) plotSel.value = plotId; fillTasks(); taskSel.value = taskId; return [plotSel.value, taskSel.value]; },
    render,
  };
  window.TCFields = api;
  return api;
}
'''

# the scene mount: ONE InstancedMesh (bed + post per plot) for the plots of the loaded parishes/counties; placed in the
# page's module script (THREE, scene, PAR, loaded, mode, eye, teleport, parishAt, renderer, camera in scope)
FIELDS_SCENE_JS = r'''
/* FIELDS w12: the AUTHORED plots of the loaded parishes/counties - one InstancedMesh (bed + post per plot), drawn only
   while the player has the plots shown (web/fieldkit.py) and never in the overview; hidden = 0 draw calls */
const FK_DATA = JSON.parse(document.getElementById('fields-data').textContent);
const FK_MAX = 2 * Object.values(FK_DATA.plots).reduce((n, ps) => n + ps.length, 0);
const fkMesh = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshLambertMaterial({ color: 0xffffff }), FK_MAX);
fkMesh.count = 0; fkMesh.visible = false; fkMesh.frustumCulled = false; fkMesh.name = 'fields-plots'; scene.add(fkMesh);
const FK_COL = { none: 0x6B4F36, prepare: 0x4A3626, plant: 0x9CCB6B, tend: 0x3F8F4F, harvest: 0xE8B84A, post: 0xE8A33D };
const fkM = new THREE.Matrix4(), fkC = new THREE.Color();
function fkWorld(id) {
  for (const [f, ps] of Object.entries(FK_DATA.plots)) { const p = ps.find((q) => q.id === id); if (p) {
    const P = PAR.get(f); if (!P) throw new Error('fieldkit: plot ' + id + ' names ' + f + ', which this page does not hold');
    return { x: P.origin_m[0] + p.x, z: P.origin_m[1] + p.z, p, fips: f }; } }
  throw new Error('fieldkit: no plot ' + id);
}
let fkT = 0;
function fkStep(now) {
  const on = !!(window.TCFields && window.TCFields.shown()) && mode !== 'overview';
  if (now - fkT > 300 || fkMesh.visible !== on) {
    fkT = now; let n = 0;
    if (on) for (const f of loaded) { const ps = FK_DATA.plots[f]; if (!ps) continue;
      for (const p of ps) { const w = fkWorld(p.id), ph = window.TCFields.phaseOf(p.id) || 'none';
        fkM.makeScale(p.size_m[0], 0.3, p.size_m[1]).setPosition(w.x, 0.15, w.z); fkMesh.setMatrixAt(n, fkM); fkMesh.setColorAt(n++, fkC.setHex(FK_COL[ph]));
        fkM.makeScale(0.5, 7, 0.5).setPosition(w.x, 3.5, w.z); fkMesh.setMatrixAt(n, fkM); fkMesh.setColorAt(n++, fkC.setHex(FK_COL.post)); } }
    fkMesh.count = n; fkMesh.visible = on && n > 0; fkMesh.instanceMatrix.needsUpdate = true; if (fkMesh.instanceColor) fkMesh.instanceColor.needsUpdate = true;
  }
  requestAnimationFrame(fkStep);
}
requestAnimationFrame(fkStep);
window.__fields = {
  current: () => current && current.id,
  plots: () => Object.values(FK_DATA.plots).flat().filter((p) => PAR.has(p.fips)).map((p) => { const w = fkWorld(p.id); return { id: p.id, fips: w.fips, x: w.x, z: w.z, land: parishAt(w.x, w.z) ? parishAt(w.x, w.z).id : null }; }),
  goto(id) { const w = fkWorld(id); if (mode !== 'walk') setMode('walk'); teleport(w.x, w.z + 30, 0); if (window.TCFields) window.TCFields.render(); return { x: eye.x, z: eye.z, parish: current && current.id }; },
  stats: () => ({ instances: fkMesh.count, visible: fkMesh.visible, max: FK_MAX }),
  /* eval: draw calls this kit adds, measured as (calls with it) - (calls with it hidden) */
  drawCalls() { renderer.render(scene, camera); const all = renderer.info.render.calls; const v = fkMesh.visible; fkMesh.visible = false;
    renderer.render(scene, camera); const off = renderer.info.render.calls; fkMesh.visible = v; return all - off; },
};
'''


def fields_scene_js():
    return FIELDS_SCENE_JS


def fields_tail(world):
    """css, data, catalogue, kit and mount - appended before </body> (the mount runs on DOMContentLoaded, after the
    page's module has set <html lang>)."""
    d = fields_data(world)
    j = lambda x: json.dumps(x, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return (f'<style id="fields-css">{FIELDS_CSS}</style>\n'
            f'<script type="application/json" id="fields-data">{j(d)}</script>\n'
            f'<script type="application/json" id="fields-i18n">{j(fields_catalog())}</script>\n'
            f'<script id="fields-kit">{FIELDS_JS}</script>\n'
            '<script id="fields-mount">document.addEventListener("DOMContentLoaded", function () {\n'
            '  var root = document.getElementById("fields"), cat = JSON.parse(document.getElementById("fields-i18n").textContent);\n'
            '  var L = cat[document.documentElement.lang] || cat.en, t = function (k) { var s = L.strings[k];\n'
            '    if (typeof s !== "string") throw new Error("fields i18n: no " + k); return s; };\n'
            '  document.querySelectorAll("[data-fk-i18n]").forEach(function (el) { el.textContent = t(el.getAttribute("data-fk-i18n")); });\n'
            '  fieldsMount(root, JSON.parse(document.getElementById("fields-data").textContent), { t: t, seed: 20260929 });\n'
            '});</script>\n')


if __name__ == '__main__':
    import sys
    if '--emit' in sys.argv:
        print(FIELDS_JS)
