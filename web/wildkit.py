#!/usr/bin/env python3
"""web/wildkit.py - the wildlife kit (BAYOU, wave 12): sightings, photo mode, a field-guide codex and the wildlife
games, embeddable in any world page (parish, Bay, wilds).

Everything is play and AUTHORED (wildlife/registry/wildlife.json): real regional species named generally, sighting
windows on an approximate GAME calendar, spawns seeded per 250 m cell on the page's own AUTHORED habitat (water /
shore / land predicates the page supplies) - never a survey or a range map. Safe viewing is the game: a photo taken
closer than the species' AUTHORED safe distance is refused ("too close - back away").
The alligator season is a licensed-tag harvest SIMULATION with no gore (a catch is a tag recorded); in K-12 /
classroom mode (?k12=1, a loaded class plan, or the toggle) it becomes an alligator NEST SURVEY instead, and the
panel says so.

Python API (fail closed - a missing registry field or locale key stops the build by name):
    from wildkit import WildKitError, WILD_CSS, WILD_JS, WILD_I18N_KEYS, wild_data, wild_i18n, wild_panel_html
    data = wild_data('parishes' | 'bay' | 'wilds')          # compact JSON-safe dict for the region
    html = wild_panel_html(region, hooks)                    # the panel section (+ hidden egg hooks: attr strings)
    embed <script type="application/json" id="wild-data">, <script type="application/json" id="wild-i18n">, WILD_JS,
    then TCWILD.mount({root, data, i18n, getPlayer, isWater, isGround, seed, month, worldId?})
Quest finds go through window.TCQuests.find(id) only when the page carries that id (GAMES_CONTRACT sec 3);
the codex lives in localStorage "tc-wild" (device-only, guarded). No network, no assets, no draw calls.
`python3 web/wildkit.py --emit` prints WILD_JS (web/test_wildkit.mjs imports the pure core from it).
"""
import html as _html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REG = ROOT / 'wildlife/registry/wildlife.json'
REGIONS = ('parishes', 'bay', 'wilds')
WILD_I18N_KEYS = [
    'wild.title', 'wild.play', 'wild.near', 'wild.none', 'wild.photo', 'wild.too_close', 'wild.too_far',
    'wild.photo_ok', 'wild.codex', 'wild.gator', 'wild.nest', 'wild.nest_note', 'wild.turtle', 'wild.litter',
    'wild.classroom', 'wild.next', 'wild.done', 'wild.safety', 'wild.window', 'wild.bin.trash', 'wild.bin.recycle',
    'wild.bin.leave', 'wild.right', 'wild.wrong', 'wild.close', 'wild.seen', 'wild.off_season',
]


class WildKitError(KeyError):
    pass


def _need(d, k, where):
    if not isinstance(d, dict):
        raise WildKitError(f'wildkit: {where}: expected an object to read {k!r} from')
    if k not in d:
        raise WildKitError(f'wildkit: {where}: required field {k!r} is missing')
    return d[k]


def _reg():
    if not REG.exists():
        raise WildKitError('wildkit: wildlife/registry/wildlife.json is missing; run python3 wildlife/build.py')
    return json.loads(REG.read_text(encoding='utf-8'))


def wild_data(region):
    if region not in REGIONS:
        raise WildKitError(f'wildkit: region {region!r} is not one of {REGIONS}')
    R = _reg()
    sp = []
    for s in _need(R, 'species', 'registry'):
        if region not in _need(s, 'regions', s['id']):
            continue
        q = _need(s, 'quests', s['id'])
        sp.append({'id': s['id'], 'name': _need(s, 'name', s['id']), 'group': _need(s, 'group', s['id']),
                   'habitat': _need(s, 'habitat', s['id']), 'months': _need(_need(s, 'window', s['id']), 'months', s['id']),
                   'times': s['window']['times'], 'points': _need(s, 'points', s['id']),
                   'rarity': _need(s, 'rarity', s['id']), 'colour': _need(s, 'colour', s['id']),
                   'safe': _need(_need(s, 'game_m', s['id']), 'safe', s['id']), 'photo': s['game_m']['photo'],
                   'dangerous': _need(s, 'dangerous', s['id']), 'fact': _need(s, 'fact', s['id']),
                   'safety': _need(s, 'safety', s['id']), 'quest': q[region] if region in q else None})
    if not sp:
        raise WildKitError(f'wildkit: no species for region {region!r}')
    G = _need(R, 'games', 'registry')
    gs = _need(G, 'gator-season', 'games')
    games = {
        'turtle': {'title': _need(G['turtle-crossing'], 'title', 'turtle'), 'label': G['turtle-crossing']['label'],
                   'rounds': _need(G['turtle-crossing'], 'rounds', 'turtle'),
                   'quest': G['turtle-crossing']['quests'][region] if region in G['turtle-crossing']['quests'] else None},
        'litter': {'title': _need(G['shoreline-litter'], 'title', 'litter'), 'label': G['shoreline-litter']['label'],
                   'items': _need(G['shoreline-litter'], 'items', 'litter'), 'bins': G['shoreline-litter']['bins'],
                   'quest': G['shoreline-litter']['quests'][region] if region in G['shoreline-litter']['quests'] else None},
    }
    if _need(gs, 'region', 'gator-season') == region:
        games['gator'] = {'title': gs['title'], 'label': gs['label'], 'rules_line': _need(gs, 'rules_line', 'gator'),
                          'general': _need(gs, 'general', 'gator'), 'months': gs['months'], 'steps': gs['steps'],
                          'quest': gs['quest'], 'classroom': _need(gs, 'classroom', 'gator')}
    H = _need(R, 'honesty', 'registry')
    return {'v': 'tc-wild-data/1', 'stamp': _need(R, 'source_stamp', 'registry'), 'region': region,
            'honesty': {k: _need(H, k, 'honesty') for k in ('play', 'rules_line', 'calendar', 'species', 'habitat')},
            'safe_viewing': _need(R, 'safe_viewing', 'registry'), 'species': sp, 'games': games,
            'cell_m': 250}


def wild_i18n():
    out = {}
    for f in sorted((ROOT / 'i18n/locales').glob('*.json')):
        c = json.loads(f.read_text(encoding='utf-8'))
        st = _need(c, 'strings', f.name)
        s = {}
        for k in WILD_I18N_KEYS:
            if k not in st or not isinstance(st[k], str) or not st[k].strip():
                raise WildKitError(f'wildkit: locale {f.name} has no key {k!r}')
            s[k] = st[k]
        out[_need(c, 'locale', f.name)] = {'dir': _need(c, 'dir', f.name), 'strings': s}
    if len(out) != 8 or 'en' not in out:
        raise WildKitError(f'wildkit: expected 8 locales incl. en, found {sorted(out)}')
    return out


def _t(k):
    return _html.escape(wild_i18n()['en']['strings'][k])


def wild_panel_html(region, hooks=()):
    """The panel (registered with web/hudkit.py by the host as panel id 'wild', sel '#wild-panel') plus hidden egg
    hooks: `hooks` are attribute strings from questkit.egg_attr (the host checks their scope)."""
    d = wild_data(region)
    gator = ''
    if 'gator' in d['games']:
        gator = (f'<button type="button" class="tc-btn wild-g" data-wild-game="gator" data-i18n-wild="wild.gator">{_t("wild.gator")}</button>')
    hk = ''.join(f'<span hidden {a}></span>' for a in hooks)
    return (f'<section id="wild-panel" class="wild tc-panel" data-wild-region="{region}" aria-labelledby="wild-h">'
            f'<details class="wild-d"><summary class="wild-h"><h2 id="wild-h" class="wild-h" data-i18n-wild="wild.title">{_t("wild.title")}</h2></summary>'
            f'<p class="wild-near" data-wild-near aria-live="polite">{_t("wild.none")}</p>'
            f'<div class="wild-row"><button type="button" class="tc-btn" data-wild-photo data-i18n-wild="wild.photo">{_t("wild.photo")}</button>'
            f'<button type="button" class="tc-btn tc-btn-ghost" data-wild-codex aria-expanded="false" data-i18n-wild="wild.codex">{_t("wild.codex")}</button></div>'
            f'<div class="wild-row">{gator}'
            f'<button type="button" class="tc-btn tc-btn-ghost wild-g" data-wild-game="turtle" data-i18n-wild="wild.turtle">{_t("wild.turtle")}</button>'
            f'<button type="button" class="tc-btn tc-btn-ghost wild-g" data-wild-game="litter" data-i18n-wild="wild.litter">{_t("wild.litter")}</button></div>'
            f'<label class="wild-k12"><input type="checkbox" data-wild-k12> <span data-i18n-wild="wild.classroom">{_t("wild.classroom")}</span></label>'
            f'<div class="wild-game" data-wild-area hidden></div>'
            f'<p class="wild-note" lang="en" dir="ltr">{_html.escape(d["honesty"]["play"])} {_html.escape(d["honesty"]["calendar"])}</p>'
            f'</details>{hk}</section>')


WILD_CSS = """
.wild{padding:8px 10px;max-inline-size:22rem;font-size:.85rem;line-height:1.35}
.wild-h{font-size:.95rem;margin:0;display:inline}
.wild-d>summary{min-block-size:44px;display:flex;align-items:center;gap:6px;cursor:pointer}
.wild-row{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0}
.wild button{min-block-size:44px;min-inline-size:44px}
.wild-k12{display:flex;gap:6px;align-items:center;min-block-size:44px}
.wild-k12 input{inline-size:22px;block-size:22px}
.wild-game{max-block-size:40vh;overflow:auto;border-block-start:1px solid currentColor;padding-block-start:6px}
.wild-game ol,.wild-game ul{padding-inline-start:1.2rem;margin:4px 0}
.wild-game li[data-got="1"]::marker{content:"\\2713  "}
.wild-note{font-size:.72rem;opacity:.85;margin:4px 0 0}
.wild-sw{display:inline-block;inline-size:.8em;block-size:.8em;border-radius:50%;margin-inline-end:4px;vertical-align:middle;border:1px solid currentColor}
.wild-warn{font-weight:700}
"""

WILD_JS = r"""/* WILD-CORE:BEGIN - pure: no DOM, no storage, no network. Imported and run in node by web/test_wildkit.mjs. */
function wildRng(seed) { let a = seed >>> 0; return function () { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
function wildCellSeed(seed, ci, cj, k) { return (Math.imul(seed | 0, 73856093) ^ Math.imul(ci | 0, 19349663) ^ Math.imul(cj | 0, 83492791) ^ Math.imul(k + 1, 2654435761)) >>> 0; }
const WILD_CHANCE = { common: 0.7, uncommon: 0.4, rare: 0.15 };
function wildInWindow(sp, month, tod) { return sp.months.includes(month) && (!tod || sp.times.includes(tod)); }
function wildHabitatOk(hab, x, z, isWater, isGround) {
  if (hab === 'water') return !!isWater(x, z);
  if (!isGround(x, z) || isWater(x, z)) return false;
  let near = false;
  for (let a = 0; a < 8 && !near; a++) { const r = 30; if (isWater(x + Math.cos(a * Math.PI / 4) * r, z + Math.sin(a * Math.PI / 4) * r)) near = true; }
  if (hab === 'shore') return near;
  if (hab === 'land') return !near;
  throw new Error('wild: unknown habitat ' + hab);
}
/* spawns for one cell: deterministic from (seed, ci, cj, species index); only on the page's AUTHORED habitat */
function wildCellSpawns(data, seed, ci, cj, month, tod, isWater, isGround) {
  const out = []; const M = data.cell_m;
  data.species.forEach((sp, k) => {
    if (!wildInWindow(sp, month, tod)) return;
    const rnd = wildRng(wildCellSeed(seed, ci, cj, k));
    if (!(sp.rarity in WILD_CHANCE)) throw new Error('wild: unknown rarity ' + sp.rarity);
    if (rnd() > WILD_CHANCE[sp.rarity]) return;
    for (let t = 0; t < 12; t++) {
      const x = (ci + rnd()) * M, z = (cj + rnd()) * M;
      if (wildHabitatOk(sp.habitat, x, z, isWater, isGround)) { out.push({ id: sp.id + '@' + ci + ',' + cj, sp: sp.id, x, z }); break; }
    }
  });
  return out;
}
function wildNearby(data, seed, px, pz, month, tod, isWater, isGround, cache) {
  const M = data.cell_m, ci = Math.floor(px / M), cj = Math.floor(pz / M); const all = [];
  for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) {
    const key = (ci + a) + ',' + (cj + b) + '|' + month + '|' + tod;
    if (!cache.has(key)) cache.set(key, wildCellSpawns(data, seed, ci + a, cj + b, month, tod, isWater, isGround));
    all.push(...cache.get(key));
  }
  return all.map((s) => Object.assign({ d: Math.hypot(s.x - px, s.z - pz) }, s)).sort((u, v) => u.d - v.d);
}
/* the photo judge: the safe-viewing rule IS the game - too close is refused */
function wildJudge(sp, d) { return d < sp.safe ? 'too_close' : (d > sp.photo ? 'too_far' : 'ok'); }
function wildBearing(px, pz, x, z) { const e = x - px, n = -(z - pz); const a = (Math.atan2(e, n) * 180 / Math.PI + 360) % 360; return ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'][Math.round(a / 45) % 8]; }
function wildGatorMode(classroom, data) { const g = data.games.gator; if (!g) return null; return classroom ? { mode: 'survey', title: g.classroom.title, label: g.classroom.label, steps: g.classroom.steps, quest: g.classroom.quest } : { mode: 'harvest-sim', title: g.title, label: g.label, steps: g.steps, quest: g.quest }; }
function wildParse(raw) { try { const o = raw ? JSON.parse(raw) : null; return o && o.v === 'tc-wild/1' && o.seen && typeof o.seen === 'object' ? o : { v: 'tc-wild/1', seen: {} }; } catch (e) { return { v: 'tc-wild/1', seen: {} }; } }
/* WILD-CORE:END */
(function () {
  'use strict';
  const STORE = 'tc-wild';
  function load() { try { return wildParse(window.localStorage.getItem(STORE)); } catch (e) { return wildParse(null); } }
  function save(st) { try { window.localStorage.setItem(STORE, JSON.stringify(st)); } catch (e) { /* device-only; private mode keeps nothing */ } }
  function report(id) { const T = window.TCQuests; if (!id || !T || !T.data || !T.data.quests.some((q) => q.id === id)) return null; return T.find(id); }
  function classroomDefault() {
    try { const u = new URLSearchParams(location.search); if (u.get('k12') === '1' || u.has('plan')) return true; } catch (e) { /* no URL */ }
    try { return !!window.localStorage.getItem('tc-class-plan'); } catch (e) { return false; }
  }
  function mount(o) {
    for (const k of ['root', 'data', 'i18n', 'getPlayer', 'isWater', 'isGround', 'seed', 'month']) if (!(k in o)) throw new Error('wild: mount needs ' + k);
    const D = o.data, root = o.root; const byId = Object.fromEntries(D.species.map((s) => [s.id, s]));
    const loc = (document.documentElement.lang || 'en').split('-')[0];
    const S = (o.i18n[loc] || o.i18n.en).strings;
    for (const el of root.querySelectorAll('[data-i18n-wild]')) el.textContent = S[el.getAttribute('data-i18n-wild')];
    const near = root.querySelector('[data-wild-near]'), area = root.querySelector('[data-wild-area]');
    const k12 = root.querySelector('[data-wild-k12]'); let classroom = classroomDefault(); k12.checked = classroom;
    const caches = new Map(); let cur = null; let st = load();
    const cacheFor = () => { const w = o.worldId ? String(o.worldId()) : ''; if (!caches.has(w)) caches.set(w, new Map()); return caches.get(w); };
    const tod = () => (typeof o.timeOfDay === 'function' ? o.timeOfDay() : null);
    function tick() {
      const p = o.getPlayer(); if (!p) return;
      const list = wildNearby(D, o.seed, p.x, p.z, o.month, tod(), o.isWater, o.isGround, cacheFor());
      cur = list.find((s) => s.d <= byId[s.sp].photo * 1.6) || null;
      if (!cur) { near.textContent = S['wild.none']; return; }
      const sp = byId[cur.sp];
      near.textContent = S['wild.near'].replace('{name}', sp.name).replace('{m}', String(Math.round(cur.d))).replace('{dir}', wildBearing(p.x, p.z, cur.x, cur.z))
        + (sp.dangerous ? ' - ' + sp.safety : '');
      near.classList.toggle('wild-warn', !!sp.dangerous);
    }
    function photo() {
      tick(); if (!cur) { say(S['wild.none']); return; }
      const sp = byId[cur.sp]; const j = wildJudge(sp, cur.d);
      if (j === 'too_close') { say(S['wild.too_close'] + ' ' + sp.safety); return; }
      if (j === 'too_far') { say(S['wild.too_far']); return; }
      st = load(); st.seen[sp.id] = st.seen[sp.id] || new Date().toISOString(); save(st);
      say(S['wild.photo_ok'].replace('{name}', sp.name) + ' ' + sp.fact);
      report(sp.quest);
      if (o.worldId) report('treasure-bayou-wilds-' + o.worldId() + '-guide');
      const saf = D.region === 'wilds' ? null : 'side-bayou-photo-safari-' + D.region;
      if (saf && window.TCQuests && window.TCQuests.data.quests.some((q) => q.id === saf) && window.TCQuests.check(saf).ok) window.TCQuests.complete(saf);
      root.dispatchEvent(new CustomEvent('wild-photo', { detail: { sp: sp.id, d: cur.d } }));
    }
    function say(msg) { area.hidden = false; area.replaceChildren(Object.assign(document.createElement('p'), { textContent: msg })); }
    function codex() {
      st = load(); area.hidden = false; const ul = document.createElement('ul'); ul.setAttribute('data-wild-codex-list', '');
      for (const sp of D.species) {
        const li = document.createElement('li'); li.dataset.got = sp.id in st.seen ? '1' : '0'; li.dataset.sp = sp.id;
        const sw = Object.assign(document.createElement('span'), { className: 'wild-sw' }); sw.style.background = sp.colour;
        const b = Object.assign(document.createElement('b'), { textContent: sp.name + (sp.id in st.seen ? ' - ' + S['wild.seen'] : '') });
        const f = Object.assign(document.createElement('div'), { textContent: sp.fact });
        const s = Object.assign(document.createElement('div'), { textContent: S['wild.safety'] + ': ' + sp.safety });
        const w = Object.assign(document.createElement('div'), { textContent: S['wild.window'] + ': ' + sp.months.join(', ') + ' (' + sp.times.join(', ') + ')' });
        li.append(sw, b, f, s, w); ul.appendChild(li);
      }
      const sv = document.createElement('ol'); for (const r of D.safe_viewing) sv.appendChild(Object.assign(document.createElement('li'), { textContent: r.text }));
      area.replaceChildren(ul, sv, Object.assign(document.createElement('p'), { className: 'wild-note', textContent: D.honesty.calendar + ' ' + D.honesty.habitat }));
    }
    function steps(g) {
      area.hidden = false; let i = 0;
      const h = Object.assign(document.createElement('p'), { className: 'wild-warn', textContent: g.title + ' - ' + g.label });
      const ol = document.createElement('ol'); const btn = Object.assign(document.createElement('button'), { type: 'button', className: 'tc-btn', textContent: S['wild.next'] });
      const extra = [];
      if (g.mode === 'harvest-sim') {
        extra.push(Object.assign(document.createElement('p'), { textContent: D.games.gator.general + ' ' + D.games.gator.rules_line }));
        if (!D.games.gator.months.list.includes(o.month)) extra.push(Object.assign(document.createElement('p'), { textContent: S['wild.off_season'] + ' (' + D.games.gator.months.label + ')' }));
      } else extra.push(Object.assign(document.createElement('p'), { textContent: S['wild.nest_note'] }));
      btn.setAttribute('data-wild-next', '');
      btn.addEventListener('click', () => {
        if (i < g.steps.length) { ol.appendChild(Object.assign(document.createElement('li'), { textContent: g.steps[i].text })); i++; }
        if (i >= g.steps.length) { btn.disabled = true; btn.textContent = S['wild.done']; report(g.quest); root.dispatchEvent(new CustomEvent('wild-gator', { detail: { mode: g.mode } })); }
      });
      area.replaceChildren(h, ...extra, ol, btn); area.dataset.mode = g.mode;
    }
    function quiz(rounds, qid) {
      area.hidden = false; let i = 0, right = 0; const box = document.createElement('div');
      function show() {
        if (i >= rounds.length) { box.replaceChildren(Object.assign(document.createElement('p'), { textContent: S['wild.done'] + ' ' + right + '/' + rounds.length })); if (right === rounds.length) report(qid); return; }
        const r = rounds[i]; const p = Object.assign(document.createElement('p'), { textContent: r.q }); const row = document.createElement('div'); row.className = 'wild-row';
        r.options.forEach((op) => { const b = Object.assign(document.createElement('button'), { type: 'button', className: 'tc-btn tc-btn-ghost', textContent: op.text }); b.addEventListener('click', () => { if (op.right) right++; box.replaceChildren(Object.assign(document.createElement('p'), { textContent: (op.right ? S['wild.right'] : S['wild.wrong']) + ' ' + r.why })); i++; setTimeout(show, 900); }); row.appendChild(b); });
        box.replaceChildren(p, row);
      }
      show(); area.replaceChildren(box);
    }
    function litter() {
      const g = D.games.litter; const items = g.items.map((it) => ({ q: it.name, why: it.why, options: g.bins.map((b) => ({ text: S['wild.bin.' + b], right: b === it.bin })) }));
      quiz(items, g.quest);
    }
    root.querySelector('[data-wild-photo]').addEventListener('click', photo);
    root.querySelector('[data-wild-codex]').addEventListener('click', (e) => { const on = e.currentTarget.getAttribute('aria-expanded') !== 'true'; e.currentTarget.setAttribute('aria-expanded', String(on)); if (on) codex(); else area.hidden = true; });
    for (const b of root.querySelectorAll('[data-wild-game]')) b.addEventListener('click', () => {
      const g = b.getAttribute('data-wild-game');
      if (g === 'gator') steps(wildGatorMode(classroom, D)); else if (g === 'turtle') quiz(D.games.turtle.rounds, D.games.turtle.quest); else litter();
    });
    function relabel() { const gb = root.querySelector('[data-wild-game="gator"]'); if (gb) gb.textContent = classroom ? S['wild.nest'] : S['wild.gator']; root.dataset.k12 = classroom ? '1' : '0'; }
    k12.addEventListener('change', () => { classroom = k12.checked; relabel(); if (area.dataset.mode) steps(wildGatorMode(classroom, D)); });
    relabel();
    /* the registry's reveal line, shown on any find (public TCQuests API: on + toast; nothing parallel) */
    if (window.TCQuests && !window.__wildReveal) { window.__wildReveal = true; window.TCQuests.on('found', (e) => { if (e && e.quest && e.quest.reveal) setTimeout(() => window.TCQuests.toast(e.quest.title + ': ' + e.quest.reveal), 5400); }); }
    const iv = setInterval(tick, 500); tick();
    const api = { tick, photo, codex, state: load, nearby: () => cur, scan: (x, z) => wildNearby(D, o.seed, x, z, o.month, tod(), o.isWater, o.isGround, cacheFor()), setClassroom: (v) => { k12.checked = !!v; classroom = !!v; relabel(); }, stop: () => clearInterval(iv) };
    window.__wild = api; return api;
  }
  globalThis.TCWILD = { mount, judge: wildJudge, nearby: wildNearby, gatorMode: wildGatorMode };
})();
"""

if __name__ == '__main__':
    if '--emit' in sys.argv:
        sys.stdout.write(WILD_JS)
    elif '--data' in sys.argv:
        sys.stdout.write(json.dumps(wild_data(sys.argv[sys.argv.index('--data') + 1])))
