#!/usr/bin/env python3
"""web/fishkit.py - the fishing & crawfish game kit for the open worlds (FISH, wave 12).

Reads outdoors/registry/outdoors.json (spots DERIVED from AUTHORED water; rods, bait, species AUTHORED) and emits:

  FISH_CORE    a pure, seeded game core between the FISH_CORE BEGIN/END comment markers - carried byte-for-byte
               into pages and imported headless by web/test_fishkit.mjs (no DOM, no Math.random):
                 fishRng(seed)                        mulberry32, deterministic
                 fishInSeason(sp, month)              AUTHORED game-calendar window, wraps across the new year
                 fishTimeOfDay(hour)                  'dawn' | 'day' | 'dusk' | 'night'
                 fishRodsFor(reg, spot)               rods whose habitats include the spot's
                 fishCandidates(reg, spot, ctx)       species x weight for spot x season x bait x time x rod method
                 fishPick(cands, rng)                 weighted pick (null = no bite: a teaching moment)
                 fishCast(aim, power, rod)            cast length/quality from aim + power (game units)
                 fishBiteDelay(sp, cast, rng)         seconds until the bite (wary fish wait longer)
                 fishReelInit(sp, rod) / fishReelStep(st, reeling, dt, rng)   the reel tension mini-game
                 fishTrapCheck(reg, spot, ctx, soak, rng)   crawfish / crab trap haul (a game count, not a yield)
                 fishLogAdd(log, entry)               the device-local codex (species -> caught/released/first)
  FISH_UI      the page glue: window.TCFish.mount(host) - a HUD panel (#fish-hud, registered with web/hudkit.py) with
               the cast/reel button + a small canvas meter, and a section below the stage (#fish) with rod/bait/time/
               month pickers, the nearest spots (Go), the trap line, the codex and the honesty lines. Keyboard: Space /
               Enter casts and (held) reels, R releases, K keeps a note; mouse/touch on 44 px buttons; RTL by logical CSS.
               Markers: ONE InstancedMesh for every bobber/trap/spot marker (one draw call, only while a spot is near).
  fish_data(world)  the registry slice for one world ('parishes' | 'bay' | 'wilds') - fails closed.
  fish_i18n()       the fish.* catalogue from all 8 locales (a missing key stops the build by name).

Everything caught is PLAY: stored on this device only (localStorage "tc-fish-log", try/catch), never a completion
record, never money, never a licence. Real fishing follows state rules (see the registry honesty lines).
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
REG_PATH = ROOT / 'outdoors/registry/outdoors.json'

FISH_KEYS = ['hud.toggle', 'hud.open', 'title', 'lede', 'spot', 'rod', 'bait', 'time', 'month', 'cast', 'reel',
             'release', 'keep', 'trap_set', 'trap_check', 'codex', 'near_none', 'go', 'walk_to', 'aim', 'power',
             'bite', 'snap', 'escape', 'landed', 'nobite', 'trap_haul', 'trap_empty', 'hidden_found', 'released',
             'kept', 'play', 'time_dawn', 'time_day', 'time_dusk', 'time_night', 'wrong_gear', 'codex_empty',
             'tension', 'season_note', 'keys']


class FishError(KeyError):
    pass


def _need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise FishError(f'fishkit: {where} has no {k!r}')
    return d[k]


def fish_registry():
    if not REG_PATH.exists():
        raise FishError('fishkit: outdoors/registry/outdoors.json is missing - run python3 outdoors/build.py')
    return json.loads(REG_PATH.read_text(encoding='utf-8'))


def fish_data(world):
    reg = fish_registry()
    if world not in _need(reg, 'worlds', 'outdoors.json'):
        raise FishError(f'fishkit: unknown world {world!r} (known: {sorted(reg["worlds"])})')
    spots = [s for s in _need(reg, 'spots', 'outdoors.json') if s['world'] == world]
    if not spots:
        raise FishError(f'fishkit: world {world!r} has no spots')
    regions = sorted({s['region'] for s in spots})
    out = {k: _need(reg, k, 'outdoors.json') for k in ('rods', 'baits', 'times', 'habitats', 'honesty', 'source_stamp')}
    out['world'] = world
    out['spots'] = spots
    out['species'] = [sp for sp in reg['species'] if any(r in sp['regions'] for r in regions)]
    out['agencies'] = sorted({reg['regions'][r]['agency'] for r in regions if reg['regions'][r]['agency']})
    return out


def fish_i18n():
    cat = {}
    for f in sorted((ROOT / 'i18n/locales').glob('*.json')):
        c = json.loads(f.read_text(encoding='utf-8'))
        s = {}
        for k in FISH_KEYS:
            if 'fish.' + k not in c['strings']:
                raise FishError(f'fishkit: locale {f.stem} has no key fish.{k}')
            v = c['strings']['fish.' + k]
            if not isinstance(v, str) or not v.strip():
                raise FishError(f'fishkit: locale {f.stem} has no key fish.{k}')
            s[k] = v
        cat[c['locale']] = {'dir': c['dir'], 'strings': s}
    if len(cat) != 8 or 'en' not in cat:
        raise FishError(f'fishkit: expected 8 locales incl. en, found {sorted(cat)}')
    return cat


def js_json(o):
    return json.dumps(o, ensure_ascii=False, sort_keys=True).replace('</', '<\\/')


FISH_CORE = r"""/* FISH_CORE:BEGIN */
function fishRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
function fishInSeason(sp, month) {
  const [a, b] = sp.season;
  return a <= b ? month >= a && month <= b : month >= a || month <= b;
}
function fishTimeOfDay(hour) {
  if (hour >= 5 && hour < 8) return 'dawn';
  if (hour >= 8 && hour < 17) return 'day';
  if (hour >= 17 && hour < 20) return 'dusk';
  return 'night';
}
function fishRodsFor(reg, spot) { return reg.rods.filter((r) => r.habitats.includes(spot.habitat)); }
function fishCandidates(reg, spot, ctx) {
  const rod = reg.rods.find((r) => r.id === ctx.rod);
  if (!rod) throw new Error('fish: unknown rod ' + ctx.rod);
  if (!rod.habitats.includes(spot.habitat)) return [];
  const out = [];
  for (const sp of reg.species) {
    if (!sp.regions.includes(spot.region) || !sp.habitats.includes(spot.habitat)) continue;
    if (!sp.methods.includes(rod.method) || !sp.baits.includes(ctx.bait)) continue;
    if (!fishInSeason(sp, ctx.month)) continue;
    const w = sp.times[ctx.time] * (6 - sp.stats.rarity);
    if (w > 0) out.push({ sp, w });
  }
  return out;
}
function fishPick(cands, rng) {
  let tot = 0; for (const c of cands) tot += c.w;
  if (tot <= 0) return null;
  let r = rng() * tot;
  for (const c of cands) { r -= c.w; if (r < 0) return c.sp; }
  return cands[cands.length - 1].sp;
}
/* aim in [-1, 1] (0 = straight at the marked water), power in [0, 1]; a sweet spot rewards a controlled cast */
function fishCast(aim, power, rod) {
  const p = Math.max(0, Math.min(1, power)), a = Math.max(-1, Math.min(1, aim));
  const over = p > 0.92, sweet = p >= 0.6 && p <= 0.92;
  const length = Math.round(p * rod.stats.reach * 10);
  const accuracy = Math.max(0, 1 - Math.abs(a) * (1.4 - rod.stats.finesse * 0.12));
  const quality = over ? 'tangle' : p < 0.2 ? 'short' : sweet && accuracy > 0.6 ? 'good' : 'ok';
  return { length, accuracy: Math.round(accuracy * 100) / 100, quality };
}
function fishBiteDelay(sp, cast, rng) {
  const base = 1.2 + sp.stats.wariness * 0.7, jitter = rng() * 2.2;
  const q = cast.quality === 'good' ? 0.75 : cast.quality === 'short' ? 1.4 : 1;
  return Math.round((base + jitter) * q * 10) / 10;
}
/* tension 0..1 must stay inside the green window while reeling brings the fish in (progress 0..1) */
function fishReelInit(sp, rod) {
  const width = 0.16 + rod.stats.tension_window * 0.06 - sp.stats.fight * 0.02;
  const lo = 0.5 - width / 2;
  return { tension: 0.35, progress: 0, lo, hi: lo + width, slack: 0, surge: 0, fight: sp.stats.fight, power: rod.stats.power, state: 'fight' };
}
function fishReelStep(st, reeling, dt, rng) {
  if (st.state !== 'fight') return st;
  if (st.surge <= 0 && rng() < dt * 0.25 * st.fight) st.surge = 0.5 + rng() * 0.6;
  const pull = st.surge > 0 ? 0.55 * st.fight / 5 : 0;
  st.surge = Math.max(0, st.surge - dt);
  st.tension += (reeling ? 0.55 - st.power * 0.04 : -0.5) * dt + pull * dt;
  st.tension = Math.max(0, st.tension);
  const inWin = st.tension >= st.lo && st.tension <= st.hi;
  if (reeling && inWin) st.progress += dt * (0.1 + st.power * 0.03);
  else if (st.surge > 0) st.progress = Math.max(0, st.progress - dt * 0.04);
  st.slack = st.tension < 0.06 ? st.slack + dt : 0;
  if (st.tension >= 1) st.state = 'snap';
  else if (st.slack > 1.6) st.state = 'escape';
  else if (st.progress >= 1) st.state = 'landed';
  return st;
}
/* a trap set at a spot for `soak` game hours; the haul is a small game count, never a yield */
function fishTrapCheck(reg, spot, ctx, soak, rng) {
  const cands = fishCandidates(reg, spot, { ...ctx, rod: ctx.rod });
  if (!cands.length) return { haul: [], note: 'empty' };
  const tries = Math.max(0, Math.min(6, Math.floor(soak / 2)));
  const haul = [];
  for (let i = 0; i < tries; i++) if (rng() < 0.55) haul.push(fishPick(cands, rng).id);
  return { haul, note: haul.length ? 'haul' : 'empty' };
}
function fishLogAdd(log, e) {
  const r = log[e.species] || (log[e.species] = { caught: 0, released: 0, first: e.at, spots: [] });
  r.caught += 1; if (e.released) r.released += 1;
  if (!r.spots.includes(e.spot)) r.spots.push(e.spot);
  return log;
}
/* FISH_CORE:END */"""

FISH_CSS = r"""
#fish-hud [hidden]{display:none!important}
#fish-hud{display:flex;gap:6px;align-items:center;flex-wrap:wrap;padding:6px 8px;max-inline-size:340px}
#fish-hud .tc-btn,#fish .tc-btn,#fish select{min-block-size:44px;min-inline-size:44px}
#fish-hud .tc-btn:disabled,#fish .tc-btn:disabled{color:#4b5260;background:#e4e7ec;opacity:1;cursor:not-allowed}   /* lead w12: the UA's faded disabled grey read 1.95:1; this pair reads 6.5:1 */
#fish-hud canvas{inline-size:150px;block-size:44px;border-radius:6px;background:var(--sunk,#0b1418)}
#fish-hud .fish-msg{font-size:13px;max-inline-size:320px;overflow-wrap:anywhere}
@media (max-width:600px){#fish-hud canvas{inline-size:96px}#fish-hud .fish-msg{max-inline-size:170px;font-size:12px}}
#fish .fish-grid{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:end}
#fish label{display:flex;flex-direction:column;font-size:13px;gap:2px}
#fish ul{padding-inline-start:18px}
#fish .fish-spots li,#fish .fish-codex li{margin:4px 0}
#fish .fish-codex .fact{color:var(--muted,#9aa)}
"""

FISH_UI = r"""
(function () {
  'use strict';
  const NEAR_M = 45, SHOW_M = 150, LOG_KEY = 'tc-fish-log';
  const R = JSON.parse(document.getElementById('fish-data').textContent);
  const CAT = JSON.parse(document.getElementById('fish-i18n').textContent);
  const loc = () => { const l = (document.documentElement.lang || 'en').split('-')[0]; return CAT[l] ? l : 'en'; };
  const t = (k) => CAT[loc()].strings[k];
  const rng = fishRng((new URLSearchParams(location.search).get('fishseed') | 0) || (Date.now() & 0xffffff));
  let log = {}, traps = {};
  try { const j = JSON.parse(localStorage.getItem(LOG_KEY) || '{}'); log = j.log || {}; traps = j.traps || {}; } catch (e) { log = {}; }
  const save = () => { try { localStorage.setItem(LOG_KEY, JSON.stringify({ log, traps })); } catch (e) { /* device-only; nothing else */ } };
  const hud = document.getElementById('fish-hud'), sec = document.getElementById('fish');
  const $ = (s) => sec.querySelector(s);
  const ctx = { rod: 'spinning-rod', bait: 'worm', time: fishTimeOfDay(new Date().getHours()), month: new Date().getMonth() + 1 };
  let host = null, here = null, game = { phase: 'idle' }, mk = null, found = new Set();
  const btn = hud.querySelector('[data-fish-act]'), msg = hud.querySelector('.fish-msg'), cv = hud.querySelector('canvas'), g = cv.getContext('2d');
  function say(s) { msg.textContent = s; }
  function sel(id, rows, cur) {
    const s = $(id); s.innerHTML = '';
    for (const [v, label] of rows) { const o = document.createElement('option'); o.value = v; o.textContent = label; if (v === cur) o.selected = true; s.appendChild(o); }
  }
  function labels() {
    for (const el of sec.querySelectorAll('[data-fish-t]')) el.textContent = t(el.dataset.fishT);
    for (const el of hud.querySelectorAll('[data-fish-t]')) el.textContent = t(el.dataset.fishT);
    sel('#fish-time', R.times.map((k) => [k, t('time_' + k)]), ctx.time);
    const mf = new Intl.DateTimeFormat(document.documentElement.lang || 'en', { month: 'long' });
    sel('#fish-month', Array.from({ length: 12 }, (_, i) => [String(i + 1), mf.format(new Date(2026, i, 15))]), String(ctx.month));
    renderAct(); renderCodex();
  }
  function gearRows() {
    const rods = here ? fishRodsFor(R, here) : R.rods;
    if (!rods.some((r) => r.id === ctx.rod)) ctx.rod = rods[0] ? rods[0].id : ctx.rod;
    sel('#fish-rod', rods.map((r) => [r.id, r.title]), ctx.rod);
    const rod = R.rods.find((r) => r.id === ctx.rod);
    const baits = R.baits.filter((b) => rod.method === 'trap' ? b.kind === 'trap bait' : rod.id === 'crab-line' ? b.kind === 'crab bait' : !/trap|crab/.test(b.kind));
    if (!baits.some((b) => b.id === ctx.bait)) ctx.bait = baits[0].id;
    sel('#fish-bait', baits.map((b) => [b.id, b.title + ' (' + b.kind + ')']), ctx.bait);
    $('#fish-rodtip').textContent = rod.tip;
  }
  function nearest() {
    const w = host && host.where(); if (!w) return [];
    const out = [];
    for (const s of R.spots) {
      if (!host.regions().includes(s.region_id)) continue;
      const p = host.toWorld(s.region_id, s.x, s.z), q = host.toWorld(w.region, w.x, w.z);
      if (!p || !q) continue;
      out.push({ s, d: Math.hypot(p[0] - q[0], p[1] - q[1]), p });
    }
    return out.sort((a, b) => a.d - b.d);
  }
  function renderSpots(list) {
    const ul = $('.fish-spots'); ul.innerHTML = '';
    const vis = list.filter((o) => !o.s.hidden).slice(0, 5);
    if (!vis.length) { const li = document.createElement('li'); li.textContent = t('near_none'); ul.appendChild(li); return; }
    for (const o of vis) {
      const li = document.createElement('li');
      li.innerHTML = '<span lang="en"></span> <span class="prov">' + o.s.provenance + '</span> ';
      li.firstChild.textContent = (o.s.name ? o.s.name + ' - ' : '') + R.habitats[o.s.habitat] + ' (' + Math.round(o.d) + ' m)';
      const b = document.createElement('button'); b.type = 'button'; b.className = 'tc-btn tc-btn-ghost'; b.textContent = t('go');
      b.addEventListener('click', () => host.teleport(o.p[0], o.p[1]));
      li.appendChild(b); ul.appendChild(li);
    }
  }
  function renderCodex() {
    const ul = $('.fish-codex'); ul.innerHTML = '';
    const ids = Object.keys(log).sort();
    if (!ids.length) { const li = document.createElement('li'); li.textContent = t('codex_empty'); ul.appendChild(li); return; }
    for (const id of ids) {
      const sp = R.species.find((s) => s.id === id); if (!sp) continue;
      const li = document.createElement('li'); li.lang = 'en';
      li.innerHTML = '<b></b> x<span></span> <span class="fact"></span>';
      li.children[0].textContent = sp.title; li.children[1].textContent = log[id].caught + ' (' + log[id].released + ' ' + t('released') + ')';
      li.children[2].textContent = sp.fact + ' ' + sp.handling;
      ul.appendChild(li);
    }
  }
  function rodNow() { return R.rods.find((r) => r.id === ctx.rod); }
  function renderAct() {
    const trap = rodNow().method === 'trap';
    const k = game.phase === 'aim' ? 'cast' : game.phase === 'wait' || game.phase === 'reel' ? 'reel' : game.phase === 'caught' ? 'release' : trap ? (traps[here && here.id] ? 'trap_check' : 'trap_set') : 'cast';
    btn.textContent = t(k); btn.disabled = !here;
    hud.querySelector('[data-fish-keep]').hidden = game.phase !== 'caught';
  }
  function draw() {
    const w = cv.width, h = cv.height; g.clearRect(0, 0, w, h);
    g.fillStyle = '#23343a'; g.fillRect(0, 0, w, h);
    if (game.phase === 'aim') {
      g.fillStyle = '#3f8f5a'; g.fillRect(w * 0.6, h - 14, w * 0.32, 10);
      g.fillStyle = '#e8a33d'; g.fillRect(4, h - 14, (w - 8) * game.power, 10);
      g.strokeStyle = '#41c4d4'; g.lineWidth = 3; g.beginPath(); g.moveTo(w / 2, h - 18); g.lineTo(w / 2 + game.aim * w * 0.4, 4); g.stroke();
    } else if (game.phase === 'reel' && game.st) {
      const st = game.st;
      g.fillStyle = '#3f8f5a'; g.fillRect(4 + (w - 8) * st.lo, 6, (w - 8) * (st.hi - st.lo), 14);
      g.fillStyle = st.tension > st.hi ? '#e0584f' : '#e8a33d'; g.fillRect(4 + (w - 8) * Math.min(1, st.tension) - 2, 2, 4, 22);
      g.fillStyle = '#41c4d4'; g.fillRect(4, h - 12, (w - 8) * st.progress, 8);
    } else if (game.phase === 'wait') {
      g.fillStyle = '#f2f5f7'; g.beginPath(); g.arc(w / 2, h / 2 + Math.sin(performance.now() / 300) * 3, 6, 0, 7); g.fill();
    }
  }
  function act(down) {
    if (!here) return;
    const rod = rodNow();
    if (rod.method === 'trap') {
      if (!down) return;
      if (!traps[here.id]) { traps[here.id] = { at: Date.now(), month: ctx.month, time: ctx.time }; save(); say(t('trap_set')); window.__fishLast = { trap: 'set', spot: here.id }; }
      else {
        const soak = Math.min(12, (Date.now() - traps[here.id].at) / 20000 + 4);   // AUTHORED game clock: 20 s = 1 game hour, min 4
        const r = fishTrapCheck(R, here, { ...ctx, rod: rod.id, bait: 'trap-bait' }, soak, rng);
        delete traps[here.id];
        for (const id of r.haul) { fishLogAdd(log, { species: id, at: new Date().toISOString(), spot: here.id, released: true }); tcReport(R.catches[id]); }
        save(); renderCodex();
        say(r.haul.length ? t('trap_haul').replace('{n}', r.haul.length) + ' ' + R.species.find((s) => s.id === r.haul[0]).handling : t('trap_empty'));
        window.__fishLast = { trap: 'checked', haul: r.haul, spot: here.id };
      }
      renderAct(); return;
    }
    if (game.phase === 'idle' && down) { game = { phase: 'aim', aim: 0, power: 0, dir: 1 }; say(t('aim')); }
    else if (game.phase === 'aim' && !down) {
      const cast = fishCast(game.aim, game.power, rod);
      const cands = fishCandidates(R, here, ctx), sp = fishPick(cands, rng);
      if (cast.quality === 'tangle') { game = { phase: 'idle' }; say(t('snap')); }
      else if (!sp) { game = { phase: 'idle' }; say(t('nobite')); window.__fishLast = { cast, bite: null, spot: here.id }; }
      else { game = { phase: 'wait', sp, cast, at: performance.now() + fishBiteDelay(sp, cast, rng) * 1000 }; say(t('cast') + ' ' + cast.length + ' - ' + cast.quality); }
    } else if (game.phase === 'reel') game.reeling = down;
    else if (game.phase === 'caught' && down) finish(true);
    renderAct();
  }
  /* GAMES_CONTRACT v1 s3: report through the page's TCQuests (no parallel storage); a silent no-op when not carried */
  function tcReport(id) {
    const T = window.TCQuests;
    if (!id || !T || !T.data || !T.data.quests.some((q) => q.id === id)) return null;
    try { return T.find(id); } catch (e) { return null; }
  }
  function finish(released) {
    const sp = game.sp;
    tcReport(R.catches[sp.id]);
    fishLogAdd(log, { species: sp.id, at: new Date().toISOString(), spot: here.id, released });
    save(); renderCodex();
    say((released ? t('released') : t('kept')) + ': ' + sp.title + '. ' + sp.handling);
    window.__fishLast = { species: sp.id, released, spot: here.id };
    game = { phase: 'idle' }; renderAct();
  }
  let last = performance.now(), tick = 0;
  function loop(now) {
    const dt = Math.min(0.25, (now - last) / 1000); last = now;
    if (game.phase === 'aim') { game.power += game.dir * dt * 0.8; if (game.power > 1) { game.power = 1; game.dir = -1; } if (game.power < 0) { game.power = 0; game.dir = 1; } }
    if (game.phase === 'wait' && now >= game.at) { game = { ...game, phase: 'reel', st: fishReelInit(game.sp, rodNow()), reeling: false }; say(t('bite')); renderAct(); }
    if (game.phase === 'reel') {
      fishReelStep(game.st, !!game.reeling, dt, rng);
      if (game.st.state === 'landed') { game.phase = 'caught'; say(t('landed') + ' ' + game.sp.title + ' - ' + game.sp.fact); renderAct(); }
      else if (game.st.state !== 'fight') { say(t(game.st.state)); game = { phase: 'idle' }; renderAct(); }
    }
    draw();
    if (now - tick > 400 && host) {
      tick = now;
      const list = nearest();
      const near = list.find((o) => o.d <= NEAR_M) || null;
      const prev = here && here.id; here = near ? near.s : null;
      if ((here && here.id) !== prev) { gearRows(); renderAct(); if (here && game.phase === 'idle') say(t('spot') + ': ' + R.habitats[here.habitat]); if (!here && game.phase === 'idle') say(t('walk_to')); }
      if (here && here.hidden && !found.has(here.id)) {
        found.add(here.id); say(t('hidden_found'));
        tcReport(R.eggs[here.id]);
        window.__fishFound = [...found];
      }
      renderSpots(list);
      if (mk) mk.update(list.filter((o) => !o.s.hidden && o.d < SHOW_M));
    }
    requestAnimationFrame(loop);
  }
  /* ONE InstancedMesh for every marker (spots, bobbers, traps): one draw call, hidden when nothing is near */
  function markers(THREE, scene, y) {
    const MAX = 16;
    const geo = new THREE.CylinderGeometry(0.35, 0.35, 1.6, 8);
    const mat = new THREE.MeshLambertMaterial({ color: 0xe8a33d });
    const mesh = new THREE.InstancedMesh(geo, mat, MAX);
    mesh.count = 0; mesh.visible = false; mesh.frustumCulled = false; mesh.name = 'fish-markers';
    scene.add(mesh);
    const m = new THREE.Matrix4();
    return {
      mesh,
      update(list) {
        let n = 0;
        for (const o of list) { if (n >= MAX) break; m.makeTranslation(o.p[0], y(o.p[0], o.p[1]) + 0.8, o.p[1]); mesh.setMatrixAt(n++, m); }
        mesh.count = n; mesh.visible = n > 0; mesh.instanceMatrix.needsUpdate = true;
      },
    };
  }
  function mount(h) {
    host = h;
    if (h.THREE && h.scene) mk = markers(h.THREE, h.scene, h.surfaceY);
    labels(); gearRows();
    for (const [id, k] of [['#fish-rod', 'rod'], ['#fish-bait', 'bait'], ['#fish-time', 'time'], ['#fish-month', 'month']]) {
      $(id).addEventListener('change', (e) => { ctx[k] = k === 'month' ? Number(e.target.value) : e.target.value; if (k === 'rod') gearRows(); renderAct(); });
    }
    btn.addEventListener('pointerdown', (e) => { e.preventDefault(); act(true); });
    btn.addEventListener('pointerup', () => act(false));
    btn.addEventListener('pointerleave', () => { if (game.phase === 'reel' || game.phase === 'aim') act(false); });
    hud.querySelector('[data-fish-keep]').addEventListener('click', () => { if (game.phase === 'caught') finish(false); });
    const typing = (e) => e.target && /INPUT|SELECT|TEXTAREA/.test(e.target.tagName);
    addEventListener('keydown', (e) => {
      if (typing(e) || !here) return;
      if ((e.code === 'Space' || e.key === 'Enter') && !e.repeat && e.target === document.body) { e.preventDefault(); act(true); }
      else if (e.code === 'ArrowLeft' && game.phase === 'aim') game.aim = Math.max(-1, game.aim - 0.1);
      else if (e.code === 'ArrowRight' && game.phase === 'aim') game.aim = Math.min(1, game.aim + 0.1);
      else if (e.key === 'r' && game.phase === 'caught') finish(true);
      else if (e.key === 'k' && game.phase === 'caught') finish(false);
    });
    addEventListener('keyup', (e) => { if (!typing(e) && (e.code === 'Space' || e.key === 'Enter') && e.target === document.body) act(false); });
    new MutationObserver(labels).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
    requestAnimationFrame(loop);
  }
  window.TCFish = { mount, state: () => ({ here: here && here.id, phase: game.phase, ctx: { ...ctx }, log: JSON.parse(JSON.stringify(log)), markers: mk ? mk.mesh.count : 0, reel: game.st ? { tension: game.st.tension, lo: game.st.lo, hi: game.st.hi, progress: game.st.progress } : null }),
    set: (k, v) => { ctx[k] = v; labels(); gearRows(); }, press: act, spots: () => R.spots.length };
  (function wait() { if (window.__fishHost) mount(window.__fishHost); else setTimeout(wait, 150); })();
})();
"""


def fish_hud_html(TS=None):
    return ('<div id="fish-hud" class="tc-panel" role="group" aria-label="Fishing">'
            '<button type="button" class="tc-btn" data-fish-act data-fish-t="cast" disabled>cast</button>'
            '<canvas width="150" height="44" aria-hidden="true"></canvas>'
            '<button type="button" class="tc-btn tc-btn-ghost" data-fish-keep data-fish-t="keep" hidden>keep</button>'
            '<span class="fish-msg" aria-live="polite"></span></div>')


def fish_section_html(data):
    esc = lambda s: str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    hon = data['honesty']
    return ('<section id="fish" class="fish" data-fish-root>'
            '<h2 data-fish-t="title">Fishing and crawfish</h2><p class="help" data-fish-t="lede"></p>'
            '<div class="fish-grid">'
            '<label><span data-fish-t="rod"></span><select id="fish-rod" lang="en"></select></label>'
            '<label><span data-fish-t="bait"></span><select id="fish-bait" lang="en"></select></label>'
            '<label><span data-fish-t="time"></span><select id="fish-time"></select></label>'
            '<label><span data-fish-t="month"></span><select id="fish-month"></select></label></div>'
            '<p class="help" id="fish-rodtip" lang="en"></p><p class="help" data-fish-t="keys"></p>'
            '<h3 data-fish-t="spot"></h3><ul class="fish-spots"></ul>'
            '<h3 data-fish-t="codex"></h3><ul class="fish-codex"></ul>'
            + ''.join(f'<p class="help" lang="en" data-fish-seasons-link>{esc(sp["title"])}: the Louisiana rice-crawfish rotation '
                      f'is described (in general terms) on the Seasons &amp; harvest board - <code>{esc(sp["seasons_link"]["registry"])}</code> '
                      f'id <code>{esc(sp["seasons_link"]["id"])}</code>.</p>' for sp in data['species'] if sp['seasons_link'])
            + '<p class="help" data-fish-t="season_note"></p><p class="help" data-fish-t="play"></p>'
            f'<ul class="help" data-fish-honesty lang="en">'
            + ''.join(f'<li>{esc(hon[k])}</li>' for k in ('play', 'real', 'seasons', 'facts', 'wildlife', 'places'))
            + f'</ul><p class="help" lang="en">Registry <code>outdoors/registry/outdoors.json</code> stamp '
            f'<code>{esc(data["source_stamp"])}</code> · {len(data["spots"])} spots · {len(data["species"])} species.</p>'
            '</section>')


def fish_quest_links(world):
    """From quests/source/fish.json (FISH's own source): eggs = hidden spot id -> egg id (entry place), catches =
    species id -> treasure id (the id's catch-/crab-/trap- slug names the species). Only entries of this world group."""
    src = ROOT / 'quests/source/fish.json'
    if not src.exists():
        return {}, {}
    reg = fish_registry()
    species = {sp['id'] for sp in reg['species']}
    eggs, catches = {}, {}
    for e in json.loads(src.read_text(encoding='utf-8'))['entries']:
        w = e['world']
        if not (w == world or w.startswith(world + ':')):
            continue
        if e['kind'] == 'egg':
            # a parish/Bay egg is placed ON its hidden spot id; a wilds egg is placed on the site its hidden shore
            # spot lies nearest (the wilds build validates places against sites) - one hidden spot per wilds world
            hid = [s for s in reg['spots'] if s['hidden'] and (s['id'] == e['place'] or (
                w.startswith('wilds:') and s['world'] == 'wilds' and s['region_id'] == w.split(':', 1)[1] and s['near_site'] == e['place']))]
            if len(hid) != 1:
                raise FishError(f'fishkit: egg {e["id"]} place {e["place"]!r} matches {len(hid)} hidden spots (need exactly 1)')
            eggs[hid[0]['id']] = e['id']
        elif e['kind'] == 'treasure':
            slug = e['id'].split('-fish-', 1)[1].split('-', 1)[1]
            sp = next((s for s in sorted(species) if slug == s or slug in s.split('-') or s.endswith(slug) or slug.endswith(s)), None)
            if sp is None:
                raise FishError(f'fishkit: quest {e["id"]} names no species in outdoors/registry')
            catches[sp] = e['id']
    return eggs, catches


def fish_embed(world):
    """(hud_html, section_html, tail_html) for one world ('parishes' | 'bay' | 'wilds')."""
    data = fish_data(world)
    data['eggs'], data['catches'] = fish_quest_links(world)
    for sid in data['eggs']:
        if not any(s['id'] == sid and s['hidden'] for s in data['spots']):
            raise FishError(f'fishkit: egg {data["eggs"][sid]} names {sid!r}, not a hidden spot of world {world!r}')
    tail = (f'<style id="fish-css">{FISH_CSS}</style>'
            f'<script type="application/json" id="fish-data">{js_json(data)}</script>'
            f'<script type="application/json" id="fish-i18n">{js_json(fish_i18n())}</script>'
            f'<script type="module" id="fish-kit">{FISH_CORE}\n{FISH_UI}</script>')
    return fish_hud_html(), fish_section_html(data), tail
