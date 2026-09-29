#!/usr/bin/env python3
"""web/smileskit.py - dental and hygiene mini-games for the Unspoken Smiles world (SMILES, wave 12).

Six games, all seeded and deterministic (the pure core between SMILES_CORE markers has no DOM, no clock and no
Math.random; web/test_smileskit.mjs runs it in node):
  brushing  2-minute brushing by mouth quadrant (time and coverage per quadrant; guidance total from the registry)
  flossing  a flossing path: clean every gap of an AUTHORED game arch in order
  snacks    snack sort: tooth-friendly vs sugary (general guidance only)
  plaque    plaque hunt: seeded disclosing-tablet style spots on a tooth grid to scrub away
  handwash  20-second handwashing timer with the five steps
  drinks    "sugar in drinks": which drink USUALLY has more added sugar - categories compared, never grams
Every game ends with ONE general-guidance line from the registry and "General guidance, not medical or dental advice."
Scores, eggs and badges are play: device-local (localStorage 'tc-smiles', try/catch), never a completion record.

Python API (fail closed):
    from smileskit import smiles_data, smiles_i18n_keys, smiles_panel_html, SMILES_CSS, SMILES_JS
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
REG = ROOT / 'smiles/registry/smiles.json'
GAMES = ('brushing', 'flossing', 'snacks', 'plaque', 'handwash', 'drinks')
BANDS = {'brushing': 'K-5', 'flossing': 'K-5', 'snacks': 'K-5', 'plaque': '6-8', 'handwash': 'K-5', 'drinks': '6-8'}
STORE_KEY = 'tc-smiles'


class SmilesKitError(Exception):
    pass


def _need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise SmilesKitError(f'smileskit: {where} has no {k!r}')
    return d[k]


def smiles_data():
    r = json.loads(REG.read_text(encoding='utf-8'))
    g = _need(r, 'games', 'registry')
    for k in GAMES:
        _need(g, k, 'games')
        _need(_need(r, 'guidance', 'registry'), k, 'guidance')
    return {'stamp': _need(r, 'source_stamp', 'registry'), 'games': {k: g[k] for k in GAMES},
            'guidance': {k: r['guidance'][k] for k in GAMES}, 'disclaimer': _need(r, 'disclaimer', 'registry'),
            'bands': BANDS, 'store': STORE_KEY}


def smiles_i18n_keys():
    return (['smiles.g.' + g for g in GAMES]
            + ['smiles.q.' + q for q in ('upper-right', 'upper-left', 'lower-left', 'lower-right')]
            + ['smiles.step.' + s for s in ('wet', 'soap', 'scrub', 'rinse', 'dry')]
            + ['smiles.start', 'smiles.reset', 'smiles.time', 'smiles.coverage', 'smiles.score', 'smiles.done',
               'smiles.bin.friendly', 'smiles.bin.sugary', 'smiles.more', 'smiles.disclaimer', 'smiles.band',
               'smiles.floss.next', 'smiles.plaque.left', 'smiles.next'])


def smiles_panel_html(T):
    """The games panel: one tab button per game (44 px), a stage, and the result block (guidance + disclaimer)."""
    tabs = ''.join(f'<button type="button" class="sm-tab" data-sm-game="{g}" aria-pressed="false">{T("smiles.g." + g)}'
                   f' <small class="sm-band">{BANDS[g]}</small></button>' for g in GAMES)
    return ('<section class="sm-games" id="sm-games" aria-labelledby="sm-games-h">'
            f'<h2 id="sm-games-h">{T("smiles.h.games")}</h2>'
            f'<div class="sm-tabs" role="group">{tabs}</div>'
            '<div class="sm-stage" id="sm-stage" aria-live="polite"></div>'
            '<div class="sm-result" id="sm-result" hidden><p class="sm-guidance" id="sm-guidance"></p>'
            f'<p class="sm-disclaimer">{T("smiles.disclaimer")}</p></div></section>')


SMILES_CSS = r'''
.sm-games{margin-block:1rem}
.sm-tabs{display:flex;flex-wrap:wrap;gap:.5rem;margin-block:.5rem}
.sm-tabs button,.sm-stage button{min-block-size:44px;min-inline-size:44px;padding:.4rem .8rem;border-radius:.6rem;border:1px solid var(--tc-line,#8aa);background:var(--tc-raised,#fff);color:var(--tc-ink,#122);font:inherit;cursor:pointer}
.sm-tabs button[aria-pressed="true"]{outline:3px solid var(--tc-accent,#0a7);outline-offset:1px}
.sm-band{opacity:.8}
.sm-stage{min-block-size:8rem;padding:.6rem;border-radius:.8rem;background:var(--tc-panel,#f4f8f8);color:var(--tc-ink,#122)}
.sm-grid{display:grid;gap:.4rem;grid-template-columns:repeat(var(--sm-cols,4),minmax(44px,1fr))}
.sm-grid button[data-on="1"]{background:#c2185b;color:#fff}
.sm-grid button[data-clean="1"]{background:#e8f5e9;color:#1b5e20}
.sm-meter{block-size:14px;border-radius:7px;background:#dde;overflow:hidden}
.sm-meter>i{display:block;block-size:100%;background:#0a7}
.sm-result{margin-block-start:.6rem;padding:.6rem;border-inline-start:4px solid #0a7;background:var(--tc-raised,#fff);color:var(--tc-ink,#122)}
.sm-disclaimer{font-weight:600}
'''

SMILES_JS = r'''
/* SMILES_CORE:BEGIN - pure game core: no DOM, no clock, no unseeded randomness; seeded and deterministic */
const SmilesCore = (() => {
  const rng = (seed) => { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; };
  const shuffle = (xs, seed) => { const r = rng(seed), a = xs.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
  const band = (f) => (f >= 0.9 ? 3 : f >= 0.6 ? 2 : f > 0 ? 1 : 0);
  // brushing: time is credited only to the quadrant being brushed, each quadrant capped at total/4
  const brushNew = (g) => ({ per: g.total_s / g.quadrants.length, total: g.total_s, t: Object.fromEntries(g.quadrants.map((q) => [q, 0])), elapsed: 0 });
  const brushTick = (s, q, dt) => { if (s.elapsed >= s.total || !(q in s.t)) return s; const d = Math.min(dt, s.total - s.elapsed); s.elapsed += d; s.t[q] = Math.min(s.per, s.t[q] + d); return s; };
  const brushCoverage = (s) => Object.values(s.t).reduce((a, v) => a + v, 0) / s.total;
  const brushDone = (s) => s.elapsed >= s.total;
  // flossing: gaps between an AUTHORED arch of n teeth, cleaned in order along the path
  const flossNew = (g) => ({ gaps: g.arch_teeth - 1, next: 0, misses: 0 });
  const flossStep = (s, gap) => { if (gap === s.next) { s.next++; return true; } s.misses++; return false; };
  const flossDone = (s) => s.next >= s.gaps;
  const flossScore = (s) => band(s.gaps / (s.gaps + s.misses));
  // snack sort
  const snackNew = (g, seed) => ({ deck: shuffle(g.items, seed), i: 0, right: 0 });
  const snackSort = (s, bin) => { const it = s.deck[s.i]; if (!it) return null; const ok = it.sort === bin; if (ok) s.right++; s.i++; return ok; };
  const snackDone = (s) => s.i >= s.deck.length;
  const snackScore = (s) => band(s.right / s.deck.length);
  // plaque hunt: seeded distinct cells on the tooth grid
  const plaqueNew = (g, seed) => { const n = g.grid[0] * g.grid[1]; const cells = shuffle([...Array(n).keys()], seed).slice(0, g.spots).sort((a, b) => a - b); return { n, cols: g.grid[1], spots: cells, left: new Set(cells), taps: 0 }; };
  const plaqueScrub = (s, c) => { s.taps++; return s.left.delete(c); };
  const plaqueDone = (s) => s.left.size === 0;
  const plaqueScore = (s) => band(s.spots.length / s.taps);
  // handwashing: five steps in order; the scrub step needs scrub_s seconds
  const washNew = (g) => ({ steps: g.steps, need: g.scrub_s, i: 0, scrub: 0 });
  const washTick = (s, dt) => { if (s.steps[s.i] === 'scrub') s.scrub = Math.min(s.need, s.scrub + dt); return s; };
  const washNext = (s) => { if (s.steps[s.i] === 'scrub' && s.scrub < s.need) return false; if (s.i < s.steps.length) s.i++; return true; };
  const washDone = (s) => s.i >= s.steps.length;
  // drinks: pairs from DIFFERENT categories; the answer is the higher category rank (added sugar more likely)
  const drinksNew = (g, seed, rounds) => { const r = rng(seed), cats = g.categories, out = [];
    while (out.length < rounds) { const a = cats[Math.floor(r() * cats.length)], b = cats[Math.floor(r() * cats.length)]; if (a.rank === b.rank) continue;
      out.push({ a: { cat: a.id, name: a.examples[Math.floor(r() * a.examples.length)], rank: a.rank }, b: { cat: b.id, name: b.examples[Math.floor(r() * b.examples.length)], rank: b.rank } }); }
    return { pairs: out, i: 0, right: 0 }; };
  const drinksPick = (s, side) => { const p = s.pairs[s.i]; if (!p) return null; const other = side === 'a' ? 'b' : 'a'; const ok = p[side].rank > p[other].rank; if (ok) s.right++; s.i++; return ok; };
  const drinksDone = (s) => s.i >= s.pairs.length;
  const drinksScore = (s) => band(s.right / s.pairs.length);
  return { rng, shuffle, band, brushNew, brushTick, brushCoverage, brushDone, flossNew, flossStep, flossDone, flossScore,
    snackNew, snackSort, snackDone, snackScore, plaqueNew, plaqueScrub, plaqueDone, plaqueScore,
    washNew, washTick, washNext, washDone, drinksNew, drinksPick, drinksDone, drinksScore };
})();
/* SMILES_CORE:END */
function SmilesGames(D, t, seed) {
  const C = SmilesCore, $ = (s) => document.querySelector(s);
  const stage = $('#sm-stage'), res = $('#sm-result'), gl = $('#sm-guidance');
  let cur = null, st = null, timer = null;
  const save = (g, score) => { try { const k = D.store; const o = JSON.parse(localStorage.getItem(k) || '{}'); o.best = o.best || {}; o.best[g] = Math.max(o.best[g] || 0, score); localStorage.setItem(k, JSON.stringify(o)); } catch (e) { /* device storage unavailable: play continues */ } };
  const finish = (g, score) => { clearInterval(timer); timer = null; stage.insertAdjacentHTML('beforeend', `<p data-sm-done="${g}"><strong>${t('smiles.done')}</strong> ${t('smiles.score')}: ${'★'.repeat(score)}${'☆'.repeat(3 - score)}</p>`);
    gl.textContent = D.guidance[g]; res.hidden = false; save(g, score); };
  const btn = (label, attrs) => `<button type="button" ${attrs || ''}>${label}</button>`;
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
  const tick = (sec) => { if (cur === 'brushing' && st) { C.brushTick(st.s, st.q, sec); drawBrush(); if (C.brushDone(st.s)) finish('brushing', C.band(C.brushCoverage(st.s))); }
    if (cur === 'handwash' && st) { C.washTick(st, sec); drawWash(); } };
  const drawBrush = () => { const s = st.s; $('#sm-bt').textContent = `${Math.floor(s.elapsed)} / ${s.total} s`;
    $('#sm-bc').style.inlineSize = `${Math.round(C.brushCoverage(s) * 100)}%`;
    Object.keys(s.t).forEach((q) => { const b = stage.querySelector(`[data-q="${q}"]`); b.setAttribute('aria-pressed', String(q === st.q)); b.querySelector('small').textContent = `${Math.round(s.t[q])}/${s.per} s`; }); };
  const drawWash = () => { const step = st.steps[st.i]; $('#sm-ws').textContent = step ? t('smiles.step.' + step) : ''; $('#sm-wt').textContent = `${Math.floor(st.scrub)} / ${st.need} s`; };
  const start = {
    brushing() { const g = D.games.brushing; st = { s: C.brushNew(g), q: g.quadrants[0] };
      stage.innerHTML = `<div class="sm-grid" style="--sm-cols:2">${g.quadrants.map((q) => btn(`${t('smiles.q.' + q)} <small></small>`, `data-q="${q}" aria-pressed="false"`)).join('')}</div>`
        + `<p>${t('smiles.time')}: <span id="sm-bt"></span></p><p>${t('smiles.coverage')}</p><div class="sm-meter"><i id="sm-bc" style="inline-size:0"></i></div>`;
      stage.querySelectorAll('[data-q]').forEach((b) => b.addEventListener('click', () => { st.q = b.dataset.q; drawBrush(); }));
      drawBrush(); timer = setInterval(() => tick(1), 1000); },
    flossing() { const s = st = C.flossNew(D.games.flossing);
      stage.innerHTML = `<p>${t('smiles.floss.next')}</p><div class="sm-grid" style="--sm-cols:${Math.min(s.gaps, 5)}">${[...Array(s.gaps).keys()].map((i) => btn(String(i + 1), `data-gap="${i}"`)).join('')}</div>`;
      stage.querySelectorAll('[data-gap]').forEach((b) => b.addEventListener('click', () => { if (C.flossDone(s)) return; if (C.flossStep(s, +b.dataset.gap)) b.dataset.clean = '1'; if (C.flossDone(s)) finish('flossing', C.flossScore(s)); })); },
    snacks() { const s = st = C.snackNew(D.games.snacks, seed);
      const draw = () => { const it = s.deck[s.i]; $('#sm-sn').textContent = it ? it.name : ''; };
      stage.innerHTML = `<p class="sm-item" id="sm-sn"></p><div class="sm-grid" style="--sm-cols:2">${btn(t('smiles.bin.friendly'), 'data-bin="tooth-friendly"')}${btn(t('smiles.bin.sugary'), 'data-bin="sugary"')}</div>`;
      stage.querySelectorAll('[data-bin]').forEach((b) => b.addEventListener('click', () => { if (C.snackDone(s)) return; C.snackSort(s, b.dataset.bin); draw(); if (C.snackDone(s)) finish('snacks', C.snackScore(s)); }));
      draw(); },
    plaque() { const s = st = C.plaqueNew(D.games.plaque, seed);
      stage.innerHTML = `<p>${t('smiles.plaque.left')}: <span id="sm-pl">${s.left.size}</span></p><div class="sm-grid" style="--sm-cols:${s.cols}">${[...Array(s.n).keys()].map((i) => btn('▢', `data-cell="${i}" data-on="${s.left.has(i) ? 1 : 0}" aria-label="${i + 1}"`)).join('')}</div>`;
      stage.querySelectorAll('[data-cell]').forEach((b) => b.addEventListener('click', () => { if (C.plaqueDone(s)) return; if (C.plaqueScrub(s, +b.dataset.cell)) { b.dataset.on = '0'; b.dataset.clean = '1'; } $('#sm-pl').textContent = s.left.size; if (C.plaqueDone(s)) finish('plaque', C.plaqueScore(s)); })); },
    handwash() { st = C.washNew(D.games.handwash);
      stage.innerHTML = `<p><strong id="sm-ws"></strong></p><p>${t('smiles.time')}: <span id="sm-wt"></span></p>${btn(t('smiles.next'), 'id="sm-wn"')}`;
      $('#sm-wn').addEventListener('click', () => { C.washNext(st); drawWash(); if (C.washDone(st)) finish('handwash', 3); });
      drawWash(); timer = setInterval(() => tick(1), 1000); },
    drinks() { const s = st = C.drinksNew(D.games.drinks, seed, 5);
      const draw = () => { const p = s.pairs[s.i]; if (!p) return; $('#sm-da').textContent = p.a.name; $('#sm-db').textContent = p.b.name; };
      stage.innerHTML = `<p>${t('smiles.more')}</p><div class="sm-grid" style="--sm-cols:2">${btn('<span id="sm-da"></span>', 'data-side="a"')}${btn('<span id="sm-db"></span>', 'data-side="b"')}</div>`;
      stage.querySelectorAll('[data-side]').forEach((b) => b.addEventListener('click', () => { if (C.drinksDone(s)) return; C.drinksPick(s, b.dataset.side); draw(); if (C.drinksDone(s)) finish('drinks', C.drinksScore(s)); }));
      draw(); },
  };
  const open = (g) => { clearInterval(timer); timer = null; cur = g; res.hidden = true; document.querySelectorAll('[data-sm-game]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.smGame === g))); start[g](); };
  document.querySelectorAll('[data-sm-game]').forEach((b) => b.addEventListener('click', () => open(b.dataset.smGame)));
  return { open, tick, state: () => ({ cur, st }), esc };
}
'''


def core_js():
    a = SMILES_JS.index('/* SMILES_CORE:BEGIN')
    b = SMILES_JS.index('/* SMILES_CORE:END */') + len('/* SMILES_CORE:END */')
    return SMILES_JS[a:b]
