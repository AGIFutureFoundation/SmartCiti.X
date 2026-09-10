#!/usr/bin/env python3
"""The 3D environment: every hall's floor plan, standing up.

Renders web/trade_craft_3d.html — a Three.js scene generated from the same
registries as every other surface:

  - the hall's rooms extruded from the interiors geometry (12 grid units
    wide, 3 m per unit) as a dollhouse: floor slab, low partitions, a
    district-hued fascia carrying the hall name;
  - the recovered training stations standing as beacons inside the rooms
    their strands own — click one for its lesson, checklist and gradable
    scenario check;
  - the recovered yard prop layout dressed along the apron in front of the
    building (schematic primitives; the geometry is a functional programme,
    not a building survey, and the page says so);
  - hall selector across all 111 halls grouped by district, deep-linkable
    (?hall=slug&lang=xx), UI in every shipped locale.

Three.js is pinned at 0.160.0 — the same major the recovered yard app used —
vendored into web/vendor/ and loaded as ES modules via import map, so the
page works offline and on any static host with no CDN dependency. Serve the
tree over HTTP (python3 -m http.server) — browsers refuse module imports
from file:// URLs. The page holds no data of its own.
"""
import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def _pack_root():
    for cand in (HERE, *HERE.parents):
        if (cand / 'pack').is_dir() and (cand / 'unions').is_dir():
            return cand
    raise RuntimeError('cannot locate the packs from ' + str(HERE))


ROOT = _pack_root()
sys.path.insert(0, str(ROOT / 'web'))
from interiors import build as build_interiors  # noqa: E402
from mapdata import strand_modules, PIPELINE_JS  # noqa: E402

manifest = json.load(open(ROOT / 'pack/manifest.json'))
L = manifest['ledger']
halls_json = json.load(open(ROOT / 'pack/registry/halls.json'))['halls']
districts_reg = json.load(open(ROOT / 'unions/registry/districts.json'))['districts']
campuses_reg = json.load(open(ROOT / 'unions/registry/campuses.json'))['campuses']
finishes_reg = json.load(open(ROOT / 'surfaces/registry/finishes.json'))
geo_reg = json.load(open(ROOT / 'geo/registry/campuses_geo.json'))
avatars_reg = json.load(open(ROOT / 'avatars/registry/avatars.json'))
chapters_reg = json.load(open(ROOT / 'unions/registry/chapters.json'))
sims_reg = json.load(open(ROOT / 'sims/registry/sims.json'))
stations_reg = json.load(open(ROOT / 'stations/registry/stations.json'))
yard = json.load(open(ROOT / 'archive/bac_yard_stations.json'))['yard_placements']

HUES = {'structural': 210, 'envelope': 28, 'systems': 182, 'energy': 48,
        'earthworks': 100, 'industry': 348, 'transport': 262, 'control': 148}


def hall_level_states(slug):
    doc = json.load(open(ROOT / f'pack/registry/halls/{slug}.json'))
    c = {'live': 0, 'calibrating': 0, 'schema_ok': 0, 'draft': 0}
    for lv in doc['levels']:
        c[lv['state']] += 1
    return c


census = {h['slug']: hall_level_states(h['slug']) for h in halls_json}
per_level = L['slots_per_level'] * L['variants_per_lesson']
plans = build_interiors(halls_json, lambda i: {
    k: v * per_level for k, v in census[halls_json[i]['slug']].items()})

district_of = {slug: k for k, d in districts_reg.items() for slug in d['halls']}

stations_by_hall = {}
for s in stations_reg['stations']:
    stations_by_hall.setdefault(s['hall'], []).append(s['station_id'])

HALLS = [{
    'slug': h['slug'], 'name': h['name'], 'focus': h['focus'],
    'index': h['index'], 'district': district_of[h['slug']],
    'rooms': [{'strand': r['strand'], 'label': r['label'],
               'purpose': r['purpose'], 'fixtures': r['fixtures'],
               'x': r['x'], 'y': r['y'], 'w': r['w'], 'h': r['h']}
              for r in plans[h['slug']]['rooms']],
    'depth': plans[h['slug']]['envelope']['d'],
    'stations': stations_by_hall.get(h['slug'], []),
} for h in halls_json]

I18N = {}
for f in sorted((ROOT / 'i18n/locales').glob('*.json')):
    c = json.load(open(f))
    s = c['strings']
    I18N[c['locale']] = {
        'language': c['language'], 'dir': c['dir'],
        'strings': {k: s[k] for k in (
            'nav.campus', 'language.select', 'hall.rooms', 'hall.stations',
            'station.checklist', 'station.quiz', 'ui.close',
            'map.layer.modules', 'figures.modules', 'figures.lessons', 'room.finish',
            'figures.halls', 'figures.districts', 'figures.campuses',
            'view.campus', 'view.region', 'ui.walk',
            'hint.campus', 'hint.walk', 'geo.note',
            'sim.start', 'sim.results', 'sim.pass', 'sim.retry',
            'sim.sound', 'sim.view', 'sim.choose', 'progress.local',
            'city.note', 'avatar.title',
            'honesty.taxonomy', 'honesty.content')},
        'districts': {k: v['name'] for k, v in c['districts'].items()},
        'strands': c['strands'], 'tiers': c['tiers'], 'states': c['states'],
    }

DATA = json.dumps({
    'districts': {k: {'name': d['name'], 'halls': d['halls'], 'hue': HUES[k]}
                  for k, d in districts_reg.items()},
    'campuses': campuses_reg,
    'geo': {'campuses': {k: {'lat': v['lat'], 'lng': v['lng']}
                         for k, v in geo_reg['campuses'].items()},
            'routes': geo_reg['routes_km'],
            'anchors': {k: [{'name': a['name'], 'km': a['km'],
                             'bearing_deg': a['bearing_deg']} for a in lst]
                        for k, lst in geo_reg['anchors'].items()},
            # city-layer placements: true east/north km offsets from the
            # campus point, equirectangular at the campus latitude
            'cityPois': {
                ck: [{'name': a['name'],
                      'e': round((a['lng'] - geo_reg['campuses'][ck]['lng'])
                                 * 111.32 * math.cos(math.radians(
                                     geo_reg['campuses'][ck]['lat'])), 2),
                      'n': round((a['lat'] - geo_reg['campuses'][ck]['lat'])
                                 * 110.574, 2),
                      'km': a['km'], 'bearing': a['bearing_deg'],
                      'lat': a['lat'], 'lng': a['lng'],
                      'src': a['source'],
                      'blurb': a.get('blurb', ''),
                      'bp': a.get('blurb_provenance', '')}
                     for a in geo_reg['anchors'][ck]]
                for ck in geo_reg.get('city', {})}},
    'finishes': {sl: h['rooms'] for sl, h in finishes_reg['halls'].items()},
    'finCat': finishes_reg['catalogue'],
    'baseCond': finishes_reg['base_conditions'],
    'condOver': {sl: {st: c for st, c in h['conditions'].items()
                      if c['hazards']}
                 for sl, h in finishes_reg['halls'].items()
                 if any(c['hazards'] for c in h['conditions'].values())},
    'halls': HALLS,
    'stations': {s['station_id']: {k: s[k] for k in (
        'station_id', 'name', 'hall', 'room', 'strand', 'tier',
        'lesson', 'checklist', 'doctrine', 'quiz')}
        for s in stations_reg['stations']},
    'yard': yard,
    'sims': {'sims': sims_reg['sims'], 'bindings': sims_reg['hall_bindings'],
             'honesty': sims_reg['honesty']['status']},
    'avatars': {'sections': avatars_reg['sections'],
                'defaults': avatars_reg['defaults'],
                'emotes': avatars_reg['emotes'],
                'guarantee': avatars_reg['guarantee']},
    'chapters': {'of': {slug: c['home']
                        for slug, c in chapters_reg['chapters'].items()},
                 'regions': {k: v['abbr']
                             for k, v in chapters_reg['regions'].items()},
                 'hosted': chapters_reg['hosted'],
                 'honesty': chapters_reg['honesty']['chapters']},
    'strandmods': strand_modules(),
    'i18n': I18N,
}, ensure_ascii=False, separators=(',', ':'))

SIM_JS = """/* ------------------------------------------------------- simulators ----- */
// Schematic physics for practising control discipline; the graders are
// deterministic - every rubric axis is computed from measured state.
let sim = null, curSimId = null, simView = null, curScenario = null;

/* Sound is synthesized in-page (WebAudio) - the registry says so and no
   recording is shipped. The context is created on the sim-start click, the
   one place a user gesture is guaranteed. */
let ac = null, master = null, engine = null, beeper = null, audioOn = true;
function acEnsure() {
  if (!ac) {
    ac = new (window.AudioContext || window.webkitAudioContext)();
    master = ac.createGain();
    master.gain.value = audioOn ? .9 : 0;
    master.connect(ac.destination);
  }
  if (ac.state === 'suspended') ac.resume();
}
function engineStart(kind) {
  const osc = ac.createOscillator(), g = ac.createGain(), f = ac.createBiquadFilter();
  osc.type = kind === 'diesel' ? 'sawtooth' : 'triangle';
  osc.frequency.value = kind === 'diesel' ? 42 : 95;
  f.type = 'lowpass'; f.frequency.value = kind === 'diesel' ? 320 : 900;
  g.gain.value = 0;
  osc.connect(f); f.connect(g); g.connect(master); osc.start();
  engine = { osc, g, kind };
}
function engineSet(load) {  // 0..1 - throttle / hoist activity
  if (!engine) return;
  const base = engine.kind === 'diesel' ? 42 : 95;
  engine.osc.frequency.setTargetAtTime(base * (1 + load * 1.6), ac.currentTime, .08);
  engine.g.gain.setTargetAtTime(.05 + load * .13, ac.currentTime, .1);
}
function engineStop() {
  if (engine) { engine.osc.stop(); engine = null; }
  if (beeper) { beeper.o.stop(); beeper = null; }
}
function beeperEnsure() {
  if (beeper) return;
  const o = ac.createOscillator(), g = ac.createGain();
  o.type = 'square'; o.frequency.value = 950; g.gain.value = 0;
  o.connect(g); g.connect(master); o.start();
  beeper = { o, g };
}
function beeperSet(on) {  // the pulsing reverse beeper, gated per frame
  if (!beeper) return;
  const t = ac.currentTime;
  beeper.g.gain.setTargetAtTime(
    on && Math.floor(t * 2.5) % 2 === 0 ? .05 : 0, t, .012);
}
function blip(f0, f1, dur, type = 'sine', vol = .14) {
  if (!ac) return;
  const o = ac.createOscillator(), g = ac.createGain(), t = ac.currentTime;
  o.type = type; o.frequency.setValueAtTime(f0, t);
  if (f1) o.frequency.exponentialRampToValueAtTime(f1, t + dur);
  g.gain.setValueAtTime(vol, t);
  g.gain.exponentialRampToValueAtTime(.001, t + dur);
  o.connect(g); g.connect(master); o.start(t); o.stop(t + dur + .02);
}
function thud() {  // filtered noise burst: a cone clipped, a stack struck
  if (!ac) return;
  const n = Math.floor(ac.sampleRate * .12), buf = ac.createBuffer(1, n, ac.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / n);
  const s = ac.createBufferSource(), f = ac.createBiquadFilter(), g = ac.createGain();
  s.buffer = buf; f.type = 'lowpass'; f.frequency.value = 220; g.gain.value = .5;
  s.connect(f); f.connect(g); g.connect(master); s.start();
}
function chime(good) {
  (good ? [660, 880, 1320] : [440, 330]).forEach((f, i) =>
    setTimeout(() => blip(f, null, .3, 'triangle', .12), i * 120));
}

/* Haptics, where the platform offers them: gamepad rumble and the vibration
   API. Both are best-effort - absence is silent, never an error. */
function buzz(ms, mag = .6) {
  try { navigator.vibrate?.(ms); } catch (e) { /* unsupported */ }
  try {
    for (const gp of navigator.getGamepads?.() ?? []) {
      gp?.vibrationActuator?.playEffect?.('dual-rumble',
        { duration: ms, strongMagnitude: mag, weakMagnitude: mag * .6 });
    }
  } catch (e) { /* unsupported */ }
}

/* The dash is data-driven: the sims registry declares every gauge (id,
   label, unit, warn threshold), and each sim only supplies live values. */
function initDash(def) {
  const el = document.getElementById('dash');
  el.innerHTML = def.dash.map((g) =>
    `<div class="g" id="g-${g.id}"><span class="gv">\\u2013</span>` +
    `<span class="gl">${g.label}${g.unit ? ' ' + g.unit : ''}</span></div>`).join('');
  el.style.display = 'flex';
}
function setDash(def, vals) {
  for (const g of def.dash) {
    const cell = document.getElementById('g-' + g.id);
    const x = vals[g.id];
    if (!cell || x === undefined) continue;
    const v = typeof x === 'object' ? x.v : x;
    cell.querySelector('.gv').textContent =
      typeof x === 'object' && x.txt !== undefined ? x.txt
        : Math.abs(v) >= 100 ? String(Math.round(v)) : (Math.round(v * 10) / 10).toFixed(1);
    cell.classList.toggle('warn', g.warn_at !== undefined && v >= g.warn_at);
  }
}

function setSimView(mode) {
  simView = mode;
  document.getElementById('camBtn').textContent =
    '\\u25a6 ' + t('sim.view') + ': ' + mode;
  controls.enabled = mode === 'orbit';
  if (mode === 'orbit') {
    camera.position.set(36, 28, 42);
    controls.target.set(0, 11, 0);
    controls.update();
  }
}

function teardownSim() {
  if (!sim) return;
  scene.remove(sim.group);
  sim.group.traverse((o) => o.geometry?.dispose());
  sim = null; simView = null; curScenario = null;
  controls.enabled = true;
  engineStop();
  const dash = document.getElementById('dash');
  dash.style.display = 'none'; dash.innerHTML = '';
  document.getElementById('camBtn').style.display = 'none';
  document.getElementById('sndBtn').style.display = 'none';
}

function exitSim() { teardownSim(); showHall(slug); }

function startSim(simId) {
  if (walkActive) plc.unlock();
  if (sim) teardownSim();
  curSimId = simId; view = 'sim';
  if (hallGroup) hallGroup.visible = false;
  if (campusGroup) campusGroup.visible = false;
  if (regionGroup) regionGroup.visible = false;
  ground.visible = grid.visible = true;
  scene.fog.near = 90; scene.fog.far = 260;
  const def = D.sims.sims[simId];
  // the campus you train at picks the regional scenario; the rubric never varies
  const sc = def.scenarios?.find((s) => s.campus === campusKey)
    ?? def.scenarios?.[0] ?? null;
  curScenario = sc;
  const P = sc?.params ?? {};
  sim = simId === 'crane-lift' ? craneSim(P)
    : simId === 'excavator-trench' ? excavatorSim(P) : forkliftSim(P);
  scene.add(sim.group);
  controls.autoRotate = false;
  setSimView(def.view_modes[0]);
  acEnsure(); engineStart(def.audio.engine === 'diesel' ? 'diesel' : 'hoist');
  if (def.audio.alerts.includes('reverse-beeper')) beeperEnsure();
  initDash(def);
  document.getElementById('hname').textContent =
    def.name + ' \\u2014 ' + D.halls.find(x => x.slug === slug).name;
  document.getElementById('hfocus').textContent =
    (sc ? sc.name + ' \\u2014 ' + sc.brief + ' ' : '') + def.task;
  document.getElementById('hint').textContent =
    def.controls.map(c => c.keys + ' ' + c.action).join(' \\u00b7 ') + ' \\u00b7 Esc';
  document.getElementById('simBtn').style.display = 'none';
  document.getElementById('walkBtn').style.display = 'none';
  document.getElementById('avaBtn').style.display = 'none';
  wheelShow(false);
  if (avatarGroup) avatarGroup.visible = false;
  document.getElementById('camBtn').style.display = '';
  const sb = document.getElementById('sndBtn');
  sb.style.display = '';
  sb.textContent = '\\u266a ' + t('sim.sound') + (audioOn ? '' : ' \\u2717');
}

document.getElementById('camBtn').addEventListener('click', () => {
  if (!sim) return;
  const modes = D.sims.sims[curSimId].view_modes;
  setSimView(modes[(modes.indexOf(simView) + 1) % modes.length]);
});
document.getElementById('sndBtn').addEventListener('click', () => {
  audioOn = !audioOn;
  if (master) master.gain.value = audioOn ? .9 : 0;
  document.getElementById('sndBtn').textContent =
    '\\u266a ' + t('sim.sound') + (audioOn ? '' : ' \\u2717');
});

function simResults(simId, rows, passed) {
  const def = D.sims.sims[simId];
  const i = D.i18n[loc];
  chime(passed); buzz(passed ? 180 : 90, .5);
  // the run lands in the device-local record: runs, passes, best time
  const rec = prog.sims[simId] ?? {};
  rec.runs = (rec.runs ?? 0) + 1;
  if (passed) {
    rec.passed = true;
    const tv = parseFloat(rows.find((r) => r.axis === 'time')?.value);
    if (isFinite(tv)) rec.best = Math.min(rec.best ?? Infinity, tv);
  }
  prog.sims[simId] = rec; saveProg();
  const recLine = rec.passed && isFinite(rec.best)
    ? `<p style="color:var(--muted);font-size:12.5px">\\u2713 ${rec.runs}\\u00d7 \\u00b7 best ${rec.best.toFixed(1)} s</p>`
    : '';
  document.getElementById('pbody').innerHTML = `
    <h2>${def.name}</h2>
    <span class="chip" style="${passed ? 'border-color:var(--good);color:var(--good)' : 'border-color:var(--crit);color:var(--crit)'}">
      ${passed ? t('sim.pass') : t('sim.retry')}</span>
    <h3>${t('sim.results')}</h3>
    <table style="width:100%;border-collapse:collapse;font-size:13.5px"><tbody>
      ${rows.map(r => `<tr><td>${r.axis}</td>
        <td style="text-align:end;font-family:'IBM Plex Mono',monospace">${r.value}</td>
        <td style="text-align:end">${r.ok === null ? '' : r.ok ? '\\u2713' : '\\u2717'}</td></tr>`).join('')}
    </tbody></table>
    ${recLine}
    <p style="color:var(--muted);font-size:12px;margin-top:12px">${D.sims.honesty} ${t('progress.local')}</p>
    <p><button class="barbtn" id="simRetry">\\u21bb ${t('sim.retry')}</button>
       <button class="barbtn" id="simExit">${t('ui.close')}</button></p>
    <style>#pbody td{border-top:1px solid var(--rule);padding:6px 8px;color:var(--muted)}</style>`;
  document.body.classList.add('open');
}

/* A fenced training yard, so a sim reads as a place on the campus rather
   than a void: perimeter fence, corner light masts, painted apron border. */
function simYard(g, hw, hd, cx = 0, cz = 0) {
  const fence = new THREE.MeshStandardMaterial({ color: 0x5a6468, roughness: .6 });
  const lamp = new THREE.MeshStandardMaterial({
    color: 0xfff2cf, emissive: 0xffdf9a, emissiveIntensity: .9 });
  for (let x = -hw; x <= hw; x += 6) {
    box(.14, 1.9, .14, fence, cx + x, .95, cz - hd, g);
    box(.14, 1.9, .14, fence, cx + x, .95, cz + hd, g);
  }
  for (let z = -hd + 6; z <= hd - 6; z += 6) {
    box(.14, 1.9, .14, fence, cx - hw, .95, cz + z, g);
    box(.14, 1.9, .14, fence, cx + hw, .95, cz + z, g);
  }
  box(hw * 2, .08, .06, fence, cx, 1.55, cz - hd, g, false);
  box(hw * 2, .08, .06, fence, cx, 1.55, cz + hd, g, false);
  box(.06, .08, hd * 2, fence, cx - hw, 1.55, cz, g, false);
  box(.06, .08, hd * 2, fence, cx + hw, 1.55, cz, g, false);
  box(hw * 2, .04, .5, mat.paint, cx, .03, cz - hd + 1.2, g, false);
  box(hw * 2, .04, .5, mat.paint, cx, .03, cz + hd - 1.2, g, false);
  for (const [sx, sz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
    const mx = cx + sx * (hw - 1.4), mz = cz + sz * (hd - 1.4);
    box(.3, 9, .3, mat.metal, mx, 4.5, mz, g);
    box(1.5, .35, .55, lamp, mx, 9.15, mz, g, false);
  }
}

/* --------------------------------------------------- tower crane lift ---- */
function craneSim(P = {}) {
  const sh = P.stack_h ?? 1, drift = P.drift ?? 0;
  const g = new THREE.Group();
  simYard(g, 33, 30);
  const MAST_H = 24, JIB = 28;
  box(1.4, MAST_H, 1.4, mat.metal, 0, MAST_H / 2, 0, g);
  const slewG = new THREE.Group(); slewG.position.y = MAST_H; g.add(slewG);
  box(JIB, .9, 1.1, mat.post, JIB / 2 - 3, .8, 0, slewG);
  box(7, .9, 1.1, mat.metal, -6.5, .8, 0, slewG);
  box(2.2, 2.2, 2.2, mat.part, -8.5, -.4, 0, slewG);   // counterweight
  box(1.8, 1.8, 1.8, mat.win, 1.6, -1, 1.4, slewG);    // cab
  const trolley = box(1.2, .6, 1.2, mat.steel, 10, .1, 0, slewG);
  const cableMat = new THREE.LineBasicMaterial({ color: 0xd8dde0 });
  const cableGeo = new THREE.BufferGeometry().setFromPoints(
    [new THREE.Vector3(), new THREE.Vector3()]);
  g.add(new THREE.Line(cableGeo, cableMat));
  const hook = new THREE.Mesh(new THREE.OctahedronGeometry(.45), mat.post);
  hook.castShadow = true; g.add(hook);
  const load = box(2.4, 1.6, 2.4, mat.brick, 14, .8, 10, g);
  // pads and obstacles
  const supply = box(4, .2, 4, mat.slab, 14, .1, 10, g, false);
  const target = new THREE.Mesh(new THREE.RingGeometry(1.6, 2.6, 32),
    new THREE.MeshBasicMaterial({ color: 0x5CB584, side: THREE.DoubleSide }));
  target.rotation.x = -Math.PI / 2; target.position.set(-13, .12, -9); g.add(target);
  const stacks = [box(5, 6 * sh, 3, mat.wall, 2, 3 * sh, -12, g),
                  box(4, 8 * sh, 3, mat.wall, -3, 4 * sh, 4, g)];
  const st = { slew: .6, r: 14.5, h: 6, vslew: 0, attached: false, done: false,
               loadV: new THREE.Vector2(), swingPeak: 0, swingNow: 0, strikes: 0,
               inStrike: false, t0: null, act: 0, chirped: false };
  // start the hook over open ground
  function hookPos() {
    return new THREE.Vector3(Math.cos(st.slew) * st.r, st.h,
                             Math.sin(st.slew) * st.r);
  }
  function finish() {
    st.done = true;
    const d = Math.hypot(load.position.x - target.position.x,
                         load.position.z - target.position.z);
    const time = st.t0 ? ((performance.now() - st.t0) / 1000) : 0;
    const rows = [
      { axis: 'placement', value: d.toFixed(2) + ' m', ok: d <= 1.2 },
      { axis: 'swing', value: st.swingPeak.toFixed(2) + ' m', ok: st.swingPeak <= 2.0 },
      { axis: 'strikes', value: String(st.strikes), ok: st.strikes === 0 },
      { axis: 'time', value: time.toFixed(1) + ' s', ok: null },
    ];
    simResults('crane-lift', rows, d <= 1.2 && st.swingPeak <= 2 && st.strikes === 0);
  }
  return {
    group: g, orbit: true,
    action() {
      if (st.done) return;
      const hp = hookPos();
      if (!st.attached) {
        const d = Math.hypot(hp.x - load.position.x, hp.z - load.position.z);
        if (d < 1.6 && hp.y < 4.5) {
          st.attached = true; st.t0 = performance.now();
          st.loadV.set(0, 0);
        }
      } else { st.attached = false; load.position.y = .8; finish(); }
    },
    update(dt) {
      if (st.done) return;
      const sr = 0.55, tr = 6, hr = 5;
      if (keys.KeyA) st.slew -= sr * dt;
      if (keys.KeyD) st.slew += sr * dt;
      if (keys.KeyW) st.r = Math.min(26, st.r + tr * dt);
      if (keys.KeyS) st.r = Math.max(4, st.r - tr * dt);
      if (keys.KeyQ) st.h = Math.min(22, st.h + hr * dt);
      if (keys.KeyE) st.h = Math.max(1.2, st.h - hr * dt);
      const moving = (keys.KeyA || keys.KeyD ? .4 : 0)
        + (keys.KeyW || keys.KeyS ? .3 : 0) + (keys.KeyQ || keys.KeyE ? .5 : 0);
      st.act += (Math.min(1, moving) - st.act) * Math.min(1, 5 * dt);
      engineSet(st.act);
      slewG.rotation.y = -st.slew;
      trolley.position.x = st.r;
      const hp = hookPos();
      if (st.attached) {
        // pendulum: the load chases the hook in the plan, and it shows;
        // a scenario's river breeze is a constant, deterministic lean
        st.loadV.x += drift * 1.5 * dt;
        const k = 4.5, damp = 1.6;
        const ax = (hp.x - load.position.x) * k - st.loadV.x * damp;
        const az = (hp.z - load.position.z) * k - st.loadV.y * damp;
        st.loadV.x += ax * dt; st.loadV.y += az * dt;
        load.position.x += st.loadV.x * dt;
        load.position.z += st.loadV.y * dt;
        load.position.y = Math.max(.8, hp.y - 2.2);
        const swing = Math.hypot(hp.x - load.position.x, hp.z - load.position.z);
        st.swingNow = swing;
        st.swingPeak = Math.max(st.swingPeak, swing);
        if (swing > 1.6 && !st.chirped) { st.chirped = true; blip(600, 1200, .25); }
        if (swing < 1.2) st.chirped = false;
        // strikes against the stacks
        let hit = false;
        for (const b of stacks) {
          const bb = b.geometry.parameters;
          if (Math.abs(load.position.x - b.position.x) < bb.width / 2 + 1.2
            && Math.abs(load.position.z - b.position.z) < bb.depth / 2 + 1.2
            && load.position.y - .8 < b.position.y + bb.height / 2) hit = true;
        }
        if (hit && !st.inStrike) { st.strikes++; st.inStrike = true; thud(); buzz(140); }
        if (!hit) st.inStrike = false;
      } else st.swingNow = 0;
      hook.position.copy(st.attached
        ? new THREE.Vector3(load.position.x, load.position.y + 1.6, load.position.z)
        : hp.clone().setY(Math.max(1.4, hp.y - 1)));
      const pts = cableGeo.attributes.position.array;
      const tp = new THREE.Vector3(Math.cos(st.slew) * st.r, MAST_H, Math.sin(st.slew) * st.r);
      pts[0] = tp.x; pts[1] = tp.y; pts[2] = tp.z;
      pts[3] = hook.position.x; pts[4] = hook.position.y; pts[5] = hook.position.z;
      cableGeo.attributes.position.needsUpdate = true;
      if (simView === 'cab') {
        // the operator's cab hangs BELOW the jib (sight to the hook must
        // clear it - the hook always rides directly under the jib line)
        camera.position.copy(slewG.localToWorld(new THREE.Vector3(3.8, -.6, 1.4)));
        // aim between the hook and the horizon so the yard stays in frame
        camera.lookAt(hook.position.x, hook.position.y + 8, hook.position.z);
      }
    },
    gauges: () => ({
      slew: ((st.slew * 180 / Math.PI) % 360 + 360) % 360,
      radius: st.r,
      hook: st.h,
      swing: st.swingNow,
      strikes: { v: st.strikes, txt: String(st.strikes) },
      time: { v: 0, txt: st.t0 ? ((performance.now() - st.t0) / 1000).toFixed(0) : '\\u2013' },
    }),
  };
}

/* ------------------------------------------------ excavator trench cut --- */
function excavatorSim(P = {}) {
  const g = new THREE.Group();
  simYard(g, 26, 20);
  // the machine: tracks fixed, house slews, boom+stick reach by 2-link IK
  const L1 = 5, L2 = 4.2, PIV_Y = 1.9;
  box(1.1, .7, 4.2, mat.part, -.95, .35, 0, g);
  box(1.1, .7, 4.2, mat.part, .95, .35, 0, g);
  const hg = new THREE.Group(); hg.position.y = .7; g.add(hg);
  box(2.2, 1.3, 2.6, mat.post, 0, .75, -.3, hg);        // house
  box(1.4, 1, 1, mat.part, 0, .8, -1.6, hg);            // counterweight
  box(.9, 1, .9, mat.win, .8, 1.6, .4, hg);             // cab
  const boomG = new THREE.Group();
  boomG.position.set(0, PIV_Y - .7, .2); hg.add(boomG);
  box(L1, .5, .4, mat.metal, L1 / 2, 0, 0, boomG);
  const stickG = new THREE.Group();
  stickG.position.set(L1, 0, 0); boomG.add(stickG);
  box(L2, .32, .3, mat.metal, L2 / 2, 0, 0, stickG);
  const bucket = box(.9, .7, .95, mat.part, L2, -.3, 0, stickG);
  const spoilInBucket = box(.7, .4, .75, mat.wood, L2, .15, 0, stickG, false);
  spoilInBucket.visible = false;
  // the trench: cells and flagged utilities come from the regional scenario
  const SPEC = P.cells ?? [{ d: 1.5 }, { d: 1.5 }, { d: .5, util: true }, { d: 1.5 }];
  const CZ = 6, span = SPEC.length - 1;
  const cells = SPEC.map((c, i) => {
    const cx = (i - span / 2) * 2;
    const m = new THREE.Mesh(new THREE.BoxGeometry(1.8, .1, 1.8),
      new THREE.MeshStandardMaterial({ color: 0x53575a, roughness: .95 }));
    m.position.set(cx, .05, CZ); m.receiveShadow = true; g.add(m);
    return { x: cx, z: CZ, target: c.d, d: 0, util: !!c.util, struck: false, mesh: m };
  });
  const markW = SPEC.length * 2 + 1.2;
  box(markW, .04, .28, mat.paint, 0, .11, CZ - 1.1, g, false);  // trench edge marks
  box(markW, .04, .28, mat.paint, 0, .11, CZ + 1.1, g, false);
  // utility flagging: locate posts + a painted crossing stripe per flagged cell
  const flagMat = new THREE.MeshStandardMaterial({
    color: 0xf2c744, emissive: 0x6b5410, roughness: .5 });
  for (const c of cells.filter((x) => x.util)) {
    box(.1, 1.1, .1, flagMat, c.x - 1.1, .55, c.z, g);
    box(.1, 1.1, .1, flagMat, c.x + 1.1, .55, c.z, g);
    box(.3, .04, 2.4, flagMat, c.x, .12, c.z, g, false);
  }
  // spoil zone and its growing pile
  const PAD = { x: -5, z: -4 };
  const pad = new THREE.Mesh(new THREE.CylinderGeometry(1.9, 1.9, .08, 28),
    new THREE.MeshBasicMaterial({ color: 0x8a6a42, transparent: true, opacity: .4 }));
  pad.position.set(PAD.x, .05, PAD.z); g.add(pad);
  const pile = new THREE.Mesh(new THREE.ConeGeometry(1.3, 1.1, 16), mat.wood);
  pile.position.set(PAD.x, .1, PAD.z); pile.scale.setScalar(.01);
  pile.castShadow = true; g.add(pile);
  const st = { slew: .35, r: 5.5, bh: 1.4, act: 0, carrying: false, done: false,
               strikes: 0, spoilIn: 0, spoilOut: 0, t0: null };
  const tipPos = () => new THREE.Vector3(
    Math.cos(st.slew) * st.r, st.bh, Math.sin(st.slew) * st.r);
  function cellShade(c) {
    const over = c.d > c.target + .01;
    const shade = Math.min(1, c.d / c.target);
    c.mesh.material.color.setHSL(over ? .02 : .58, over ? .45 : .2,
      .33 - .2 * shade);
  }
  function finish() {
    st.done = true;
    const atGrade = cells.filter((c) => Math.abs(c.d - c.target) < .01).length;
    const dumps = st.spoilIn + st.spoilOut;
    const time = st.t0 ? ((performance.now() - st.t0) / 1000) : 0;
    const rows = [
      { axis: 'grade', value: atGrade + '/' + cells.length, ok: atGrade === cells.length },
      { axis: 'utility', value: String(st.strikes), ok: st.strikes === 0 },
      { axis: 'spoil', value: st.spoilIn + '/' + dumps, ok: st.spoilOut === 0 },
      { axis: 'time', value: time.toFixed(1) + ' s', ok: null },
    ];
    simResults('excavator-trench', rows,
      atGrade === cells.length && st.strikes === 0 && st.spoilOut === 0);
  }
  return {
    group: g, orbit: true,
    action() {
      if (st.done) return;
      const tip = tipPos();
      if (!st.carrying) {
        const cell = cells.find((c) =>
          Math.hypot(tip.x - c.x, tip.z - c.z) < 1.1);
        if (cell && tip.y < .6 && cell.d < 2.5) {
          if (!st.t0) st.t0 = performance.now();
          cell.d += .5; st.carrying = true; spoilInBucket.visible = true;
          cellShade(cell);
          blip(180, 90, .18, 'sawtooth', .18);      // bite
          if (cell.util && cell.d > cell.target + .01 && !cell.struck) {
            cell.struck = true; st.strikes++;
            blip(980, 490, .6, 'square', .2);        // utility alarm
            buzz(320, .9);
          }
        }
      } else {
        st.carrying = false; spoilInBucket.visible = false;
        if (Math.hypot(tip.x - PAD.x, tip.z - PAD.z) < 1.9) st.spoilIn++;
        else st.spoilOut++;
        thud(); buzz(70, .3);
        pile.scale.setScalar(Math.min(1.6, .2 + st.spoilIn * .16));
        if (cells.every((c) => c.d >= c.target)) finish();
      }
    },
    update(dt) {
      if (st.done) return;
      const sr = .5, rr = 3.4, hr = 2.6;
      if (keys.KeyA) st.slew -= sr * dt;
      if (keys.KeyD) st.slew += sr * dt;
      if (keys.KeyW) st.r = Math.min(L1 + L2 - .6, st.r + rr * dt);
      if (keys.KeyS) st.r = Math.max(2.6, st.r - rr * dt);
      if (keys.KeyQ) st.bh = Math.min(3.2, st.bh + hr * dt);
      if (keys.KeyE) st.bh = Math.max(-2.4, st.bh - hr * dt);
      const moving = (keys.KeyA || keys.KeyD ? .4 : 0)
        + (keys.KeyW || keys.KeyS ? .4 : 0) + (keys.KeyQ || keys.KeyE ? .5 : 0);
      st.act += (Math.min(1, moving) - st.act) * Math.min(1, 5 * dt);
      engineSet(.15 + st.act * .85);
      hg.rotation.y = -st.slew;
      // 2-link IK in the boom plane: reach r out, bucket height bh
      const py = PIV_Y;
      const dx = st.r, dy = st.bh - py;
      const d = Math.min(L1 + L2 - .05, Math.max(1.4, Math.hypot(dx, dy)));
      const base = Math.atan2(dy, dx);
      const cosA = Math.min(1, Math.max(-1,
        (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d)));
      const cosB = Math.min(1, Math.max(-1,
        (L1 * L1 + L2 * L2 - d * d) / (2 * L1 * L2)));
      boomG.rotation.z = base + Math.acos(cosA);
      stickG.rotation.z = -(Math.PI - Math.acos(cosB));
      if (simView === 'cab') {
        const eye = hg.localToWorld(new THREE.Vector3(.8, 2.5, 1));
        camera.position.copy(eye);
        const tip = tipPos();
        camera.lookAt(tip.x, Math.min(tip.y, .8), tip.z);
      }
    },
    gauges: () => ({
      reach: st.r,
      depth: st.bh,
      grade: { v: 0, txt: cells.filter((c) => Math.abs(c.d - c.target) < .01).length + '/' + cells.length },
      spoil: { v: st.spoilOut, txt: st.spoilIn + '/' + (st.spoilIn + st.spoilOut) },
      utility: { v: st.strikes, txt: String(st.strikes) },
      time: { v: 0, txt: st.t0 ? ((performance.now() - st.t0) / 1000).toFixed(0) : '\\u2013' },
    }),
  };
}

/* --------------------------------------------------- forklift yard run --- */
function forkliftSim(P = {}) {
  const nGates = P.gates ?? 4, dockW = P.dock_w ?? 2.2;
  const laneEnd = 14 + 10 * nGates;           // the pallet waits past the last gate
  const yardHD = (laneEnd + 26) / 2;
  const g = new THREE.Group();
  simYard(g, 32, yardHD, 0, 16 - yardHD);
  const fl = new THREE.Group(); g.add(fl);
  box(1.6, 1.1, 2.6, mat.post, 0, .8, 0, fl);
  box(1.2, .9, 1.2, mat.win, 0, 1.75, -.3, fl);
  box(.15, 2.4, .15, mat.metal, -.55, 1.2, 1.4, fl);
  box(.15, 2.4, .15, mat.metal, .55, 1.2, 1.4, fl);
  const forks = new THREE.Group(); fl.add(forks);
  box(.18, .1, 1.5, mat.metal, -.4, .18, 2.2, forks);
  box(.18, .1, 1.5, mat.metal, .4, .18, 2.2, forks);
  for (const [wx, wz] of [[-.8, .9], [.8, .9], [-.8, -.9], [.8, -.9]]) {
    const w = new THREE.Mesh(new THREE.CylinderGeometry(.4, .4, .3, 14), mat.part);
    w.rotation.z = Math.PI / 2; w.position.set(wx, .4, wz);
    w.castShadow = true; fl.add(w);
  }
  // course: cone gates, pallet, dock — the gate count is the scenario's
  const GATES = Array.from({ length: nGates }, (_, i) =>
    [i % 2 === 0 ? -6 : 6, -14 - 10 * i, 0]);
  const cones = [], gates = [];
  GATES.forEach(([gx, gz], gi) => {
    const pair = [];
    for (const off of [-2.6, 2.6]) {
      const c = new THREE.Mesh(new THREE.ConeGeometry(.32, .8, 12), mat.cone);
      c.position.set(gx + off, .4, gz); c.castShadow = true;
      g.add(c); cones.push(c); pair.push(c);
    }
    gates.push({ x: gx, z: gz, taken: false, pair });
  });
  const pallet = new THREE.Group(); g.add(pallet);
  box(1.2, .14, 1.2, mat.wood, 0, .07, 0, pallet);
  box(1, .7, 1, mat.brick, 0, .52, 0, pallet);
  pallet.position.set(0, 0, -laneEnd);
  const dock = new THREE.Mesh(new THREE.PlaneGeometry(dockW * 2 + .6, dockW * 2 + .6),
    new THREE.MeshBasicMaterial({ color: 0x41C4D4, transparent: true, opacity: .28 }));
  dock.rotation.x = -Math.PI / 2; dock.position.set(14, .06, -10); g.add(dock);
  const st = { v: 0, steer: 0, phi: Math.PI, carrying: false, done: false,
               hits: 0, t0: null, placed: false };
  fl.position.set(0, 0, -2); fl.rotation.y = st.phi;
  function finish(docked) {
    st.done = true;
    const taken = gates.filter(x => x.taken).length;
    const time = st.t0 ? ((performance.now() - st.t0) / 1000) : 0;
    const rows = [
      { axis: 'gates', value: taken + '/' + gates.length, ok: taken === gates.length },
      { axis: 'cones', value: String(st.hits), ok: st.hits === 0 },
      { axis: 'docking', value: docked ? 'in the bay' : 'missed', ok: docked },
      { axis: 'time', value: time.toFixed(1) + ' s', ok: null },
    ];
    simResults('forklift-run', rows,
      taken === gates.length && st.hits === 0 && docked);
  }
  return {
    group: g, orbit: false,
    action() {
      if (st.done) return;
      const dir = new THREE.Vector3(Math.sin(st.phi), 0, Math.cos(st.phi));
      const tip = fl.position.clone().addScaledVector(dir, 2.4);
      if (!st.carrying) {
        if (Math.abs(st.v) < 1
          && tip.distanceTo(pallet.position) < 1.7) st.carrying = true;
      } else {
        st.carrying = false;
        pallet.position.set(tip.x, 0, tip.z);
        const inDock = Math.abs(pallet.position.x - dock.position.x) < dockW
          && Math.abs(pallet.position.z - dock.position.z) < dockW;
        finish(inDock);
      }
    },
    update(dt) {
      if (st.done) return;
      const acc = 5.5, drag = 1.6, vmax = 6;
      if (keys.KeyW || keys.ArrowUp) st.v += acc * dt;
      else if (keys.KeyS || keys.ArrowDown) st.v -= acc * dt;
      else st.v -= st.v * drag * dt;
      st.v = Math.max(-vmax / 2, Math.min(vmax, st.v));
      const target = (keys.KeyA || keys.ArrowLeft) ? .55
        : (keys.KeyD || keys.ArrowRight) ? -.55 : 0;
      st.steer += (target - st.steer) * Math.min(1, 8 * dt);
      if (Math.abs(st.v) > .05) {
        if (!st.t0) st.t0 = performance.now();
        st.phi += st.v / 2.2 * Math.tan(st.steer) * dt;
      }
      engineSet(Math.abs(st.v) / vmax);
      beeperSet(st.v < -.3);
      const dir = new THREE.Vector3(Math.sin(st.phi), 0, Math.cos(st.phi));
      fl.position.addScaledVector(dir, st.v * dt);
      fl.position.x = Math.max(-30, Math.min(30, fl.position.x));
      fl.position.z = Math.max(-(laneEnd + 8), Math.min(14, fl.position.z));
      fl.rotation.y = st.phi;
      if (st.carrying)
        pallet.position.copy(fl.position.clone().addScaledVector(dir, 2.4).setY(.35));
      // cones and gates
      for (const c of cones) {
        if (!c.userData.hit && c.position.distanceTo(fl.position) < 1.3) {
          c.userData.hit = true; c.rotation.z = 1.2; st.hits++;
          thud(); buzz(140);
        }
      }
      for (let gi = 0; gi < gates.length; gi++) {
        const gt = gates[gi];
        if (!gt.taken && (gi === 0 || gates[gi - 1].taken)
          && Math.hypot(fl.position.x - gt.x, fl.position.z - gt.z) < 2.4) {
          gt.taken = true;
          gt.pair.forEach((c) => { c.material = mat.steel; });
          blip(880, 1320, .18); buzz(60, .3);
        }
      }
      if (simView === 'driver') {
        // the seat: eye height over the chassis, sight line past the mast
        const eye = fl.position.clone().addScaledVector(dir, .5).setY(2.25);
        camera.position.copy(eye);
        camera.lookAt(eye.clone().addScaledVector(dir, 10).setY(1.7));
      } else {
        const camTo = fl.position.clone().addScaledVector(dir, -8.5).setY(5.2);
        camera.position.lerp(camTo, Math.min(1, 5 * dt));
        camera.lookAt(fl.position.clone().addScaledVector(dir, 4).setY(1.2));
      }
    },
    gauges: () => ({
      speed: Math.abs(st.v) * 3.6,
      steer: st.steer * 180 / Math.PI,
      load: { v: st.carrying ? 1 : 0, txt: st.carrying ? '\\u25a0' : '\\u2013' },
      gates: { v: 0, txt: gates.filter(x => x.taken).length + '/' + gates.length },
      cones: { v: st.hits, txt: String(st.hits) },
      time: { v: 0, txt: st.t0 ? ((performance.now() - st.t0) / 1000).toFixed(0) : '\\u2013' },
    }),
  };
}"""

AVATAR_JS = """/* --------------------------------------------- avatar + mobile layer ---- */
// The locker is data (avatars registry): sections, options, emotes. The
// avatar is COSMETIC ONLY - the registry guarantee, asserted by its suite:
// nothing here is read by any grader.
const isTouch = 'ontouchstart' in window;
let avatarGroup = null, avatarMesh = null, walkAvatar = null;
let avatarCfg = null, lastEmote = null;
let emo = null;                       // {move, t} while an emote plays
let wheelSection = 0;                 // index into sections; length = emotes tab

function cfgInit() {
  const base = { ...D.avatars.defaults };
  const saved = prog.avatar;
  if (saved && typeof saved === 'object') {
    for (const s of D.avatars.sections) {
      if (s.options.some((o) => o.id === saved[s.id])) base[s.id] = saved[s.id];
    }
  }
  avatarCfg = base;
}

function optOf(sectionId) {
  const s = D.avatars.sections.find((x) => x.id === sectionId);
  return s.options.find((o) => o.id === avatarCfg[sectionId]) ?? s.options[0];
}

/* A procedural worker, ~1.75 units tall, built from the cfg. Parts are
   named for the emote moves: shoulders pivot, the hat lifts, the whole
   body spins or hops. */
function buildAvatarMesh(cfg) {
  const g = new THREE.Group();
  const skin = new THREE.MeshStandardMaterial({
    color: optOf('skin').value, roughness: .75 });
  const wear = new THREE.MeshStandardMaterial({
    color: optOf('workwear').value, roughness: .85 });
  const boot = new THREE.MeshStandardMaterial({
    color: optOf('boots').value, roughness: .9 });
  const hatM = new THREE.MeshStandardMaterial({
    color: optOf('hatcolor').value, roughness: .5 });
  const hiviz = new THREE.MeshStandardMaterial({
    color: 0xd9c22e, emissive: 0x5a5010, roughness: .6 });
  // legs + boots
  for (const sx of [-1, 1]) {
    box(.16, .52, .2, wear, sx * .12, .56, 0, g);
    box(.2, .3, .3, boot, sx * .12, .15, .03, g);
  }
  // torso
  box(.5, .55, .3, wear, 0, 1.08, 0, g);
  const vest = cfg.vest;
  if (vest !== 'none') {
    box(.54, vest === 'harness' ? .2 : .4, .33, hiviz, 0,
      vest === 'harness' ? 1.24 : 1.1, 0, g);
    if (vest === 'surveyor' || vest === 'harness')
      box(.1, .5, .34, hiviz, 0, 1.08, 0, g);
  }
  // tool belt
  if (cfg.tools !== 'none') {
    box(.56, .1, .34, boot, 0, .84, 0, g);
    const n = cfg.tools === 'basic' ? 1 : cfg.tools === 'framing' ? 3 : 2;
    for (let i = 0; i < n; i++)
      box(.12, .16, .08, mat.part, -.2 + i * .2, .74, .19, g);
  }
  // arms on shoulder pivots
  const arms = {};
  for (const [nm, sx] of [['armL', -1], ['armR', 1]]) {
    const p = new THREE.Group(); p.position.set(sx * .32, 1.32, 0); g.add(p);
    box(.14, .3, .18, wear, 0, -.15, 0, p);
    box(.12, .26, .16, skin, 0, -.42, 0, p);
    arms[nm] = p;
  }
  // head + hat
  const head = new THREE.Group(); head.position.y = 1.4; g.add(head);
  box(.28, .3, .26, skin, 0, .15, 0, head);
  const hat = new THREE.Group(); hat.position.y = .32; head.add(hat);
  const dome = new THREE.Mesh(new THREE.CylinderGeometry(
    cfg.hardhat === 'vintage' ? .17 : .19, .21,
    cfg.hardhat === 'vintage' ? .2 : .14, 12), hatM);
  dome.position.y = .05; dome.castShadow = true; hat.add(dome);
  if (cfg.hardhat === 'full-brim') {
    const brim = new THREE.Mesh(new THREE.CylinderGeometry(.3, .32, .03, 14), hatM);
    hat.add(brim);
  } else if (cfg.hardhat === 'cap-brim') {
    box(.2, .03, .16, hatM, 0, 0, .24, hat, false);
  } else if (cfg.hardhat === 'climbing') {
    box(.06, .1, .3, hatM, 0, .02, 0, hat, false);   // ridge, strap look
  }
  const sc = optOf('build').scale ?? [1, 1, 1];
  g.scale.set(sc[0], sc[1], sc[2]);
  g.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  g.userData = { arms, head, hat };
  return g;
}

function refreshAvatarMeshes() {
  if (avatarMesh) {
    const parent = avatarMesh.parent;
    parent.remove(avatarMesh);
    avatarMesh.traverse((o) => o.geometry?.dispose());
    avatarMesh = buildAvatarMesh(avatarCfg);
    parent.add(avatarMesh);
  }
  if (walkAvatar) {
    const pos = walkAvatar.position.clone(), rot = walkAvatar.rotation.y;
    scene.remove(walkAvatar);
    walkAvatar = buildAvatarMesh(avatarCfg);
    walkAvatar.position.copy(pos); walkAvatar.rotation.y = rot;
    scene.add(walkAvatar);
  }
}

/* ------------------------------------------------------ emote engine ---- */
function playEmote(id) {
  const e = D.avatars.emotes.find((x) => x.id === id);
  if (!e) return;
  lastEmote = id; emo = { move: e.move, t: 0 };
  buzz(30, .2);
}
function stepEmote(dt) {
  if (!emo) return;
  emo.t += dt;
  const T = 1.3, k = Math.min(1, emo.t / T);
  const s = Math.sin(k * Math.PI);            // rise and settle
  const targets = [avatarMesh, walkAvatar].filter(Boolean);
  for (const av of targets) {
    const { arms, head, hat } = av.userData;
    arms.armL.rotation.set(0, 0, 0); arms.armR.rotation.set(0, 0, 0);
    hat.position.y = .32; av.position.y = av.userData.baseY ?? av.position.y;
    switch (emo.move) {
      case 'arm-wave':
        arms.armR.rotation.z = -2.6 * s;
        arms.armR.rotation.x = Math.sin(emo.t * 14) * .5 * s; break;
      case 'arm-up': arms.armR.rotation.x = -2.9 * s; break;
      case 'arm-point': arms.armR.rotation.x = -1.55 * s; break;
      case 'hat-tip':
        arms.armR.rotation.x = -2.4 * s;
        hat.position.y = .32 + .18 * s; hat.rotation.z = .35 * s; break;
      case 'clap':
        arms.armL.rotation.x = arms.armR.rotation.x = -1.4;
        arms.armL.rotation.z = .5 * Math.abs(Math.sin(emo.t * 12));
        arms.armR.rotation.z = -.5 * Math.abs(Math.sin(emo.t * 12)); break;
      case 'flex':
        arms.armL.rotation.z = 2.2 * s; arms.armR.rotation.z = -2.2 * s; break;
      case 'spin': av.rotation.y += dt * 10 * s; break;
      case 'jump':
        av.userData.baseY ??= av.position.y;
        av.position.y = av.userData.baseY + Math.abs(Math.sin(emo.t * 9)) * .35 * s;
        break;
    }
    if (k >= 1) {
      arms.armL.rotation.set(0, 0, 0); arms.armR.rotation.set(0, 0, 0);
      hat.position.y = .32; hat.rotation.z = 0;
      if (av.userData.baseY !== undefined) av.position.y = av.userData.baseY;
    }
  }
  if (k >= 1) emo = null;
}

/* ------------------------------------------------- the thumb wheel ------ */
// One radial control, sized for a thumb: wedges are the current locker
// section's options (colour or glyph), or the emote emojis on the last
// tab. Tap a wedge to apply or play.
function renderWheel() {
  const tabs = document.getElementById('wheelTabs');
  const sections = D.avatars.sections;
  const isEmotes = wheelSection === sections.length;
  tabs.innerHTML = sections.map((s, i) =>
    `<button class="wtab ${i === wheelSection ? 'on' : ''}" data-tab="${i}"
       title="${s.label}">${s.emoji}</button>`).join('')
    + `<button class="wtab ${isEmotes ? 'on' : ''}" data-tab="${sections.length}"
        title="Emotes">\\ud83d\\ude00</button>`;
  const svg = document.getElementById('wheel');
  const items = isEmotes ? D.avatars.emotes
    : sections[wheelSection].options;
  const cur = isEmotes ? lastEmote : avatarCfg[sections[wheelSection].id];
  const N = items.length, R = 92, r0 = 34, cx = 100, cy = 100;
  const wedge = (i) => {
    const a0 = (i / N) * Math.PI * 2 - Math.PI / 2 + .015;
    const a1 = ((i + 1) / N) * Math.PI * 2 - Math.PI / 2 - .015;
    const p = (a, rr) => `${cx + Math.cos(a) * rr},${cy + Math.sin(a) * rr}`;
    return `M ${p(a0, r0)} L ${p(a0, R)} A ${R} ${R} 0 0 1 ${p(a1, R)} `
      + `L ${p(a1, r0)} A ${r0} ${r0} 0 0 0 ${p(a0, r0)} Z`;
  };
  const mid = (i, rr) => {
    const a = ((i + .5) / N) * Math.PI * 2 - Math.PI / 2;
    return [cx + Math.cos(a) * rr, cy + Math.sin(a) * rr];
  };
  svg.innerHTML = items.map((o, i) => {
    const sel = (isEmotes ? o.id === cur : o.id === cur);
    const fill = isEmotes ? 'var(--panel)'
      : sections[wheelSection].kind === 'color' ? o.value : 'var(--panel)';
    const [tx, ty] = mid(i, (r0 + R) / 2);
    const glyph = isEmotes ? o.emoji
      : sections[wheelSection].kind === 'color' ? '' : o.glyph;
    return `<path d="${wedge(i)}" fill="${fill}"
        stroke="${sel ? 'var(--mark)' : 'var(--rule)'}"
        stroke-width="${sel ? 3 : 1}" data-pick="${o.id}"/>`
      + (glyph ? `<text x="${tx}" y="${ty}" text-anchor="middle"
          dominant-baseline="central" font-size="17"
          fill="var(--ink)" pointer-events="none">${glyph}</text>` : '');
  }).join('')
    + `<circle cx="${cx}" cy="${cy}" r="${r0 - 6}" fill="var(--sunk)"
        stroke="var(--rule)"/>`
    + `<text x="${cx}" y="${cy}" text-anchor="middle" dominant-baseline="central"
        font-size="20" pointer-events="none">${isEmotes ? '\\ud83d\\ude00' : sections[wheelSection].emoji}</text>`;
}
function wheelShow(on) {
  document.getElementById('wheelWrap').style.display = on ? '' : 'none';
  if (on) renderWheel();
}
document.getElementById('wheelWrap').addEventListener('click', (e) => {
  const tab = e.target.closest('[data-tab]');
  if (tab) { wheelSection = +tab.dataset.tab; renderWheel(); return; }
  const pick = e.target.closest('[data-pick]');
  if (!pick) return;
  const sections = D.avatars.sections;
  if (wheelSection === sections.length) { playEmote(pick.dataset.pick); return; }
  avatarCfg[sections[wheelSection].id] = pick.dataset.pick;
  prog.avatar = avatarCfg; saveProg();
  refreshAvatarMeshes(); renderWheel();
});

/* ---------------------------------------------------- the locker view --- */
function showAvatar() {
  if (sim) teardownSim();
  if (walkActive) exitWalkMode();
  view = 'avatar';
  if (hallGroup) hallGroup.visible = false;
  if (campusGroup) campusGroup.visible = false;
  if (regionGroup) regionGroup.visible = false;
  ground.visible = grid.visible = true;
  scene.fog.near = 40; scene.fog.far = 140;
  if (!avatarGroup) {
    avatarGroup = new THREE.Group();
    const ped = new THREE.Mesh(new THREE.CylinderGeometry(1.6, 1.9, .35, 24),
      mat.slab);
    ped.position.y = .17; ped.receiveShadow = true; avatarGroup.add(ped);
    avatarMesh = buildAvatarMesh(avatarCfg);
    avatarMesh.position.y = .35; avatarGroup.add(avatarMesh);
    scene.add(avatarGroup);
  }
  avatarGroup.visible = true;
  controls.enabled = true; controls.autoRotate = !reduced;
  controls.minDistance = 2.5; controls.maxDistance = 14;
  camera.position.set(3.1, 2.5, 5.2); controls.target.set(0, 1.1, 0);
  document.getElementById('hname').textContent = t('avatar.title');
  document.getElementById('hfocus').textContent = D.avatars.guarantee;
  document.getElementById('hint').textContent = '';
  for (const id of ['walkBtn', 'simBtn', 'campusBtn', 'camBtn', 'sndBtn'])
    document.getElementById(id).style.display = 'none';
  wheelShow(true);
}
document.getElementById('avaBtn').addEventListener('click', showAvatar);

/* --------------------------------------------- touch walk (3rd person) -- */
// On touch devices walk mode is third-person: a left thumb-stick moves the
// avatar, a right-side drag turns the view, and the emote wheel rides the
// right thumb. Desktop keeps first-person pointer lock.
let tYaw = 0, tPitch = .28, joyVec = { x: 0, y: 0 };
function enterTouchWalk() {
  walkActive = true;
  controls.enabled = false; controls.autoRotate = false;
  cfgInit(); // ensure cfg
  if (!walkAvatar) {
    walkAvatar = buildAvatarMesh(avatarCfg);
    scene.add(walkAvatar);
  }
  walkAvatar.visible = true;
  const spawn = view === 'hall'
    ? new THREE.Vector3(0, 0, -(D.halls.find(x => x.slug === slug).depth * U) / 2 - 8)
    : new THREE.Vector3(0, 0, 30);
  walkAvatar.position.copy(spawn);
  walkAvatar.userData.baseY = spawn.y;
  tYaw = Math.PI; tPitch = .28;
  document.getElementById('joy').style.display = '';
  document.getElementById('emoBtn').style.display = '';
  document.getElementById('hint').textContent = '';
}
function exitWalkMode() {
  if (!isTouch && walkActive) { plc.unlock(); return; }
  walkActive = false;
  if (walkAvatar) walkAvatar.visible = false;
  document.getElementById('joy').style.display = 'none';
  document.getElementById('emoBtn').style.display = 'none';
  document.getElementById('actBtn').style.display = 'none';
  wheelShow(false);
  controls.enabled = true;
  nearSlug = null; nearPoi = null;
}
function touchWalkStep(dt) {
  const sp = 5.2 * dt;
  const f = new THREE.Vector3(Math.sin(tYaw), 0, Math.cos(tYaw));
  const r = new THREE.Vector3(f.z, 0, -f.x);
  walkAvatar.position.addScaledVector(f, -joyVec.y * sp);
  walkAvatar.position.addScaledVector(r, -joyVec.x * sp);
  if (Math.hypot(joyVec.x, joyVec.y) > .1)
    walkAvatar.rotation.y = tYaw + Math.PI + Math.atan2(-joyVec.x, -joyVec.y);
  // stay on the grounds (campus) or in the hall envelope
  if (view === 'campus') {
    const len = Math.hypot(walkAvatar.position.x, walkAvatar.position.z);
    if (len > walkLim) walkAvatar.position.multiplyScalar(walkLim / len);
  } else if (view === 'hall') {
    const h = D.halls.find(x => x.slug === slug);
    const DEP = h.depth * U;
    walkAvatar.position.x = Math.min(21, Math.max(-21, walkAvatar.position.x));
    walkAvatar.position.z = Math.min(DEP / 2 - .8,
      Math.max(-DEP / 2 - 26, walkAvatar.position.z));
  }
  // third-person camera
  const back = new THREE.Vector3(Math.sin(tYaw), 0, Math.cos(tYaw));
  const eye = walkAvatar.position.clone()
    .addScaledVector(back, 5.6).setY(walkAvatar.position.y + 2.2 + tPitch * 4);
  camera.position.lerp(eye, Math.min(1, 8 * dt));
  camera.lookAt(walkAvatar.position.x, walkAvatar.position.y + 1.4,
    walkAvatar.position.z);
  // nearest door / institution for the action button
  if (view === 'campus') {
    let best = null, bd = 1e9, bp = null, pd = 1e9;
    const wp = new THREE.Vector3();
    for (const b of buildings) {
      b.getWorldPosition(wp);
      const d = Math.hypot(wp.x - walkAvatar.position.x, wp.z - walkAvatar.position.z);
      if (d < bd) { bd = d; best = b; }
    }
    for (const b of cityHits) {
      b.getWorldPosition(wp);
      const d = Math.hypot(wp.x - walkAvatar.position.x, wp.z - walkAvatar.position.z);
      if (d < pd) { pd = d; bp = b; }
    }
    const act = document.getElementById('actBtn');
    if (best && bd < 12) {
      nearSlug = best.userData.slug; nearPoi = null;
      act.style.display = '';
      act.textContent = '\\u23ce ' + D.halls.find(x => x.slug === nearSlug).name;
    } else if (bp && pd < 15) {
      nearPoi = bp.userData.poi; nearSlug = null;
      act.style.display = ''; act.textContent = '\\u23ce ' + nearPoi;
    } else { nearSlug = nearPoi = null; act.style.display = 'none'; }
  }
}
document.getElementById('actBtn').addEventListener('click', () => {
  if (nearSlug) { showHall(nearSlug); enterTouchWalk(); }
  else if (nearPoi) openCityPoi(nearPoi);
});
document.getElementById('emoBtn').addEventListener('click', () => {
  wheelSection = D.avatars.sections.length;   // the emote tab
  const w = document.getElementById('wheelWrap');
  wheelShow(w.style.display === 'none');
});

// left thumb-stick
(() => {
  const joy = document.getElementById('joy'), knob = document.getElementById('knob');
  let pid = null, cx = 0, cy = 0;
  joy.addEventListener('pointerdown', (e) => {
    pid = e.pointerId;
    try { joy.setPointerCapture(pid); } catch (err) { /* pointer already gone */ }
    const r = joy.getBoundingClientRect();
    cx = r.left + r.width / 2; cy = r.top + r.height / 2;
  });
  joy.addEventListener('pointermove', (e) => {
    if (e.pointerId !== pid) return;
    const dx = (e.clientX - cx) / 46, dy = (e.clientY - cy) / 46;
    const len = Math.hypot(dx, dy) || 1, cl = Math.min(1, len);
    joyVec.x = dx / len * cl; joyVec.y = dy / len * cl;
    knob.style.transform = `translate(${joyVec.x * 34}px, ${joyVec.y * 34}px)`;
  });
  const end = (e) => {
    if (e.pointerId !== pid) return;
    pid = null; joyVec.x = joyVec.y = 0;
    knob.style.transform = '';
  };
  joy.addEventListener('pointerup', end);
  joy.addEventListener('pointercancel', end);
})();

// right-side look drag
renderer.domElement.addEventListener('pointermove', (e) => {
  if (!(walkActive && isTouch)) return;
  if (e.buttons === 0 && e.pointerType === 'mouse') return;
  if (e.clientX < innerWidth * .45) return;   // left half is the stick's
  tYaw -= e.movementX * .006;
  tPitch = Math.min(1.1, Math.max(-.2, tPitch + e.movementY * .004));
});

"""

page = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SmartCiti.X : Trade Craft Academy — 3D hall environment</title>
<style>
:root{
  --plate:#12181B; --panel:#182023; --sunk:#0C1113; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --mark-ink:#12181B; --steel:#41C4D4;
  --good:#5CB584; --crit:#E07C68;
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--plate);color:var(--ink);
  font:14px/1.5 "IBM Plex Sans",system-ui,sans-serif;overflow:hidden}
#bar{position:fixed;top:0;left:0;right:0;z-index:5;display:flex;flex-wrap:wrap;
  gap:8px 14px;align-items:center;padding:10px 16px;
  background:color-mix(in oklab, var(--plate) 86%, transparent);
  border-bottom:2px solid var(--mark);backdrop-filter:blur(6px)}
#bar .brand{font:700 19px/1 "Barlow Condensed",system-ui,sans-serif;white-space:nowrap}
#bar .brand .x{color:var(--mark)}
#bar a{color:var(--steel);text-decoration:none;font-size:13px;white-space:nowrap}
select{background:var(--panel);color:var(--ink);border:1px solid var(--rule);
  border-radius:6px;padding:6px 9px;font:inherit;max-width:46vw}
#lang{margin-inline-start:auto}
.barbtn{background:var(--panel);color:var(--ink);border:1px solid var(--rule);
  border-radius:6px;padding:6px 11px;font:inherit;cursor:pointer;white-space:nowrap}
.barbtn:hover{border-color:var(--mark)}
#cross{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);z-index:6;
  color:var(--mark);font:400 26px/1 "IBM Plex Mono",monospace;display:none;
  pointer-events:none;text-shadow:0 0 6px rgba(0,0,0,.8)}
#hud{position:fixed;left:16px;bottom:14px;z-index:5;max-width:min(430px,86vw);
  background:color-mix(in oklab, var(--panel) 90%, transparent);
  border:1px solid var(--rule);border-radius:9px;padding:10px 14px}
#hud h2{font:600 20px "Barlow Condensed",sans-serif;margin:0}
#hud .focus{color:var(--muted);font-size:12.5px;margin:2px 0 0}
#hud .hint{color:var(--muted);font-size:11.5px;margin:6px 0 0}
#honesty{position:fixed;right:16px;bottom:14px;z-index:5;max-width:300px;
  color:var(--muted);font-size:10.5px;text-align:end;opacity:.85}
#dash{position:fixed;left:50%;bottom:14px;transform:translateX(-50%);z-index:6;
  display:none;gap:2px;background:color-mix(in oklab, var(--sunk) 90%, transparent);
  border:1px solid var(--rule);border-radius:10px;padding:8px 14px;
  backdrop-filter:blur(6px)}
#dash .g{min-width:66px;text-align:center;border-inline-start:1px solid var(--rule);
  padding:0 9px}
#dash .g:first-child{border-inline-start:none}
#dash .gv{display:block;font:600 21px/1.2 "IBM Plex Mono",monospace}
#dash .gl{display:block;color:var(--muted);font-size:10px;letter-spacing:.06em;
  text-transform:uppercase;margin-top:2px}
#dash .g.warn .gv{color:var(--crit)}
/* warning is shape AND colour, never colour alone (colourblind-safe) */
#dash .g.warn .gl::before{content:"\\25b2  ";color:var(--crit)}
/* the thumb wheel: radial options sized for a phone thumb */
#wheelWrap{position:fixed;left:50%;bottom:10px;transform:translateX(-50%);
  z-index:7;display:flex;flex-direction:column;align-items:center;gap:6px}
#wheelTabs{display:flex;gap:4px;flex-wrap:wrap;justify-content:center;
  max-width:min(92vw,360px)}
.wtab{background:var(--panel);border:1px solid var(--rule);border-radius:999px;
  min-width:40px;min-height:40px;font-size:18px;cursor:pointer;padding:2px}
.wtab.on{border-color:var(--mark);box-shadow:0 0 0 1px var(--mark)}
#wheel{width:min(64vw,250px);height:min(64vw,250px);
  filter:drop-shadow(0 4px 14px rgba(0,0,0,.5))}
#wheel path{cursor:pointer}
/* touch-walk controls */
#joy{position:fixed;left:18px;bottom:22px;z-index:7;width:112px;height:112px;
  border-radius:50%;background:color-mix(in oklab, var(--panel) 70%, transparent);
  border:1px solid var(--rule);touch-action:none}
#knob{position:absolute;left:50%;top:50%;width:52px;height:52px;margin:-26px;
  border-radius:50%;background:var(--panel);border:2px solid var(--mark)}
.fab{position:fixed;right:18px;bottom:22px;z-index:7;min-width:56px;
  min-height:56px;border-radius:999px;background:var(--panel);color:var(--ink);
  border:1px solid var(--rule);font:inherit;font-size:24px;cursor:pointer}
.fab.wide{right:18px;bottom:90px;font-size:14px;padding:0 16px;max-width:60vw;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
@media(pointer:coarse){
  .barbtn,select{min-height:42px}
  #hud{max-width:min(300px,72vw);padding:8px 11px}
  #hud h2{font-size:17px}
  #honesty{display:none}
  /* keep the wheel clear of the thumb-stick while walking */
  #wheelWrap{left:auto;right:10px;transform:none;bottom:150px}
}
canvas{display:block}
#nogl{display:none;position:fixed;inset:0;place-content:center;text-align:center;
  color:var(--muted);padding:40px}
/* station panel */
#ov{position:fixed;inset:0;background:rgba(6,10,12,.7);display:none;z-index:9}
#panel{position:fixed;top:0;inset-inline-end:0;bottom:0;width:min(480px,100%);
  background:var(--panel);border-inline-start:1px solid var(--rule);z-index:10;
  transform:translateX(105%);transition:transform .22s ease;overflow-y:auto;
  padding:20px 22px 40px}
html[dir="rtl"] #panel{transform:translateX(-105%)}
body.open #ov{display:block}
body.open #panel{transform:none}
#panel h2{font:600 22px "Barlow Condensed",sans-serif;margin:2px 0 4px;
  padding-inline-end:70px}
#panel .chip{display:inline-block;border:1px solid var(--rule);border-radius:999px;
  padding:2px 10px;font-size:12px;color:var(--muted);margin:0 4px 10px 0}
#panel h3{font:600 14px "Barlow Condensed",sans-serif;letter-spacing:.04em;
  text-transform:uppercase;color:var(--steel);margin:16px 0 6px}
#panel ul{margin:4px 0;padding-inline-start:20px;color:var(--muted)}
#pclose{position:absolute;top:12px;inset-inline-end:14px;background:none;
  border:1px solid var(--rule);color:var(--muted);border-radius:6px;
  padding:5px 11px;cursor:pointer;font:inherit}
.q{background:var(--sunk);border-radius:6px;padding:9px 12px;margin-top:8px}
.q .opt{display:block;background:none;border:1px solid var(--rule);color:var(--ink);
  border-radius:5px;padding:6px 9px;margin:5px 0;cursor:pointer;font:inherit;
  width:100%;text-align:start}
.q .opt.ok{border-color:var(--good);color:var(--good)}
.q .opt.bad{border-color:var(--crit);color:var(--crit)}
@media(prefers-reduced-motion:reduce){#panel{transition:none}}
</style>
</head>
<body>
<div id="bar">
  <span class="brand">SmartCiti<span class="x">.X</span> : Trade Craft Academy</span>
  <a href="trade_craft_interactive.html" id="back"></a>
  <select id="hall" aria-label="hall"></select>
  <button id="regionBtn" class="barbtn"></button>
  <button id="campusBtn" class="barbtn"></button>
  <button id="walkBtn" class="barbtn"></button>
  <button id="simBtn" class="barbtn"></button>
  <button id="avaBtn" class="barbtn"></button>
  <button id="camBtn" class="barbtn" style="display:none"></button>
  <button id="sndBtn" class="barbtn" style="display:none"></button>
  <select id="lang"></select>
</div>
<div id="wheelWrap" style="display:none">
  <div id="wheelTabs"></div>
  <svg id="wheel" viewBox="0 0 200 200" role="listbox" aria-label="options"></svg>
</div>
<div id="joy" style="display:none"><div id="knob"></div></div>
<button id="emoBtn" class="fab" style="display:none">😀</button>
<button id="actBtn" class="fab wide" style="display:none"></button>
<div id="hud"><h2 id="hname"></h2><p class="focus" id="hfocus"></p><p class="hint" id="hint"></p></div>
<div id="dash"></div>
<div id="honesty"></div>
<div id="nogl"></div>
<div id="cross">+</div>
<div id="ov"></div>
<aside id="panel"><button id="pclose"></button><div id="pbody"></div></aside>
<script id="data" type="application/json">__DATA__</script>
<script type="importmap">
{"imports":{
  "three":"./vendor/three.module.min.js",
  "three/addons/":"./vendor/addons/"
}}
</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { PointerLockControls } from 'three/addons/controls/PointerLockControls.js';

const D = JSON.parse(document.getElementById('data').textContent);
const params = new URLSearchParams(location.search);
let loc = D.i18n[params.get('lang')] ? params.get('lang') : 'en';
let slug = D.halls.some(h => h.slug === params.get('hall')) ? params.get('hall') : 'bricklayers';
let view = 'region';
const t = (k) => D.i18n[loc].strings[k] ?? D.i18n.en.strings[k] ?? k;
const U = 3;                       // metres per grid unit
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ------------------------------------------------------------- scene ---- */
let renderer;
try {
  renderer = new THREE.WebGLRenderer({ antialias: true });
} catch (e) {
  document.getElementById('nogl').style.display = 'grid';
  document.getElementById('nogl').textContent =
    'WebGL is unavailable in this browser; the 3D environment needs it. ' +
    'The interactive map carries the same content in 2D.';
  throw e;
}
// mobile budget: cap the pixel ratio and drop shadow maps on touch GPUs
renderer.setPixelRatio(Math.min(devicePixelRatio,
  ('ontouchstart' in window) ? 1.5 : 2));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = !('ontouchstart' in window);
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.12;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
// dusk sky: a vertical gradient the fog can sink into
{
  const c = document.createElement('canvas'); c.width = 2; c.height = 256;
  const g = c.getContext('2d');
  const gr = g.createLinearGradient(0, 0, 0, 256);
  gr.addColorStop(0, '#0c141c'); gr.addColorStop(.55, '#1a2a36');
  gr.addColorStop(.8, '#33404a'); gr.addColorStop(1, '#463a2a');
  g.fillStyle = gr; g.fillRect(0, 0, 2, 256);
  scene.background = new THREE.CanvasTexture(c);
}
scene.fog = new THREE.Fog(0x1a2229, 70, 170);

function noiseTex(base, grain, n = 1400, size = 256) {
  const c = document.createElement('canvas'); c.width = c.height = size;
  const g = c.getContext('2d');
  g.fillStyle = base; g.fillRect(0, 0, size, size);
  for (let i = 0; i < n; i++) {
    g.fillStyle = `rgba(${grain},${.05 + Math.random() * .1})`;
    const r = Math.random() * 2.2;
    g.fillRect(Math.random() * size, Math.random() * size, r, r);
  }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.anisotropy = 4;
  return t;
}
const asphaltTex = noiseTex('#191f22', '220,225,225');
asphaltTex.repeat.set(34, 34);
const concreteTex = noiseTex('#262e31', '235,238,238', 1000);
concreteTex.repeat.set(9, 9);

const camera = new THREE.PerspectiveCamera(50, innerWidth/innerHeight, .1, 900);
camera.position.set(30, 26, 42);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI * .49;
controls.minDistance = 8; controls.maxDistance = 120;
controls.autoRotate = !reduced;
controls.autoRotateSpeed = .45;
controls.addEventListener('start', () => { controls.autoRotate = false; });

scene.add(new THREE.HemisphereLight(0xaec2cb, 0x241d16, 1.05));
const key = new THREE.DirectionalLight(0xffe0b0, 1.6);
key.position.set(35, 48, 20);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
const S = 60;
Object.assign(key.shadow.camera, { left: -S, right: S, top: S, bottom: -S, far: 140 });
scene.add(key);
const fill = new THREE.DirectionalLight(0x41C4D4, .25);
fill.position.set(-30, 20, -30);
scene.add(fill);

// ground: dark apron with a faint work grid
const ground = new THREE.Mesh(
  new THREE.CircleGeometry(260, 64),
  new THREE.MeshStandardMaterial({ map: asphaltTex, color: 0x8f9698, roughness: .96 }));
ground.rotation.x = -Math.PI/2; ground.receiveShadow = true;
scene.add(ground);
const grid = new THREE.GridHelper(520, 130, 0x28353A, 0x1b2427);
grid.position.y = .02; scene.add(grid);

const mat = {
  slab:  new THREE.MeshStandardMaterial({ map: concreteTex, color: 0xb8bdbd, roughness: .9 }),
  win:   new THREE.MeshStandardMaterial({ color: 0x0b0f11,
           emissive: 0xffc27a, emissiveIntensity: .5, roughness: .4 }),
  water: new THREE.MeshStandardMaterial({ color: 0x14283a, roughness: .3,
           metalness: .3 }),
  land:  new THREE.MeshStandardMaterial({ map: asphaltTex, color: 0xcdd2d3,
           roughness: .95 }),
  road:  new THREE.MeshStandardMaterial({ color: 0x565c60, roughness: .95 }),
  drive: new THREE.MeshStandardMaterial({ color: 0x777d81, roughness: .9 }),
  walkway: new THREE.MeshStandardMaterial({ map: concreteTex, color: 0xcdd2d0,
           roughness: .95 }),
  paint: new THREE.MeshStandardMaterial({ color: 0xd8dcd8, roughness: .5 }),
  wall:  new THREE.MeshStandardMaterial({ color: 0x39454a, roughness: .85 }),
  part:  new THREE.MeshStandardMaterial({ color: 0x2c3639, roughness: .85 }),
  post:  new THREE.MeshStandardMaterial({ color: 0xE8A33D, roughness: .45,
                                          emissive: 0x7a4d08 }),
  steel: new THREE.MeshStandardMaterial({ color: 0x41C4D4, roughness: .5 }),
  wood:  new THREE.MeshStandardMaterial({ color: 0x8a6a42, roughness: .9 }),
  metal: new THREE.MeshStandardMaterial({ color: 0x8f9a9d, roughness: .55,
                                          metalness: .55 }),
  brick: new THREE.MeshStandardMaterial({ color: 0xb3462f, roughness: .92 }),
  block: new THREE.MeshStandardMaterial({ color: 0x9aa0a2, roughness: .92 }),
  cone:  new THREE.MeshStandardMaterial({ color: 0xE07C48, roughness: .6 }),
};

function label(text, sub, scale = 1) {
  const c = document.createElement('canvas');
  const ctx = c.getContext('2d');
  ctx.font = '600 44px "Barlow Condensed", sans-serif';
  const w = Math.max(ctx.measureText(text).width, 120) + 40;
  c.width = w; c.height = sub ? 110 : 72;
  ctx.fillStyle = 'rgba(12,17,19,.82)';
  ctx.beginPath(); ctx.roundRect(0, 0, c.width, c.height, 14); ctx.fill();
  ctx.fillStyle = '#E8EDEC';
  ctx.font = '600 44px "Barlow Condensed", sans-serif';
  ctx.fillText(text, 20, 50);
  if (sub) { ctx.fillStyle = '#93A3A6'; ctx.font = '28px "IBM Plex Sans", sans-serif';
             ctx.fillText(sub, 20, 90); }
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({
    map: new THREE.CanvasTexture(c), transparent: true, depthTest: false }));
  sp.scale.set(c.width/90*scale, c.height/90*scale, 1);
  return sp;
}

const finTexCache = new Map();
function finishTex(fin) {
  const key = fin.pattern + fin.color;
  if (finTexCache.has(key)) return finTexCache.get(key);
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const g = c.getContext('2d');
  g.fillStyle = fin.color; g.fillRect(0, 0, 128, 128);
  for (let i = 0; i < 260; i++) { g.fillStyle = `rgba(255,255,255,${Math.random()*.05})`;
    g.fillRect(Math.random()*128, Math.random()*128, 1.6, 1.6); }
  for (let i = 0; i < 260; i++) { g.fillStyle = `rgba(0,0,0,${Math.random()*.07})`;
    g.fillRect(Math.random()*128, Math.random()*128, 1.6, 1.6); }
  g.strokeStyle = 'rgba(0,0,0,.28)'; g.lineWidth = 2;
  const line = (x1,y1,x2,y2) => { g.beginPath(); g.moveTo(x1,y1); g.lineTo(x2,y2); g.stroke(); };
  switch (fin.pattern) {
    case 'slab': g.strokeRect(1, 1, 126, 126); break;
    case 'tile': for (let i = 0; i <= 128; i += 32) { line(i,0,i,128); line(0,i,128,i); } break;
    case 'brick': for (let y = 0; y < 128; y += 16) { line(0,y,128,y);
      for (let x = ((y/16)%2)*16; x < 128; x += 32) line(x,y,x,y+16); } break;
    case 'plank': for (let x = 0; x <= 128; x += 16) line(x,0,x,128); break;
    case 'block': for (let i = 0; i <= 128; i += 10) { line(i,0,i,128); line(0,i,128,i); } break;
    case 'checker': g.fillStyle = 'rgba(255,255,255,.16)';
      for (let y = 8; y < 128; y += 16) for (let x = 8; x < 128; x += 16) {
        g.save(); g.translate(x,y); g.rotate(.785); g.fillRect(-4,-1.4,8,2.8); g.restore(); }
      break;
    case 'grate': g.fillStyle = 'rgba(0,0,0,.5)';
      for (let y = 2; y < 128; y += 10) g.fillRect(0,y,128,4); break;
    case 'broom': for (let x = 0; x < 128; x += 3) {
      g.strokeStyle = `rgba(0,0,0,${.04+Math.random()*.06})`; g.lineWidth = 1;
      line(x,0,x,128); } break;
    default: for (let i = 0; i < 700; i++) {
      g.fillStyle = `rgba(${Math.random()>.5?'255,255,255':'0,0,0'},${.06+Math.random()*.1})`;
      g.fillRect(Math.random()*128, Math.random()*128, 2, 2); }
  }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 4;
  finTexCache.set(key, t); return t;
}

function box(w, h, d, m, x, y, z, group, shadow = true) {
  const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m);
  b.position.set(x, y, z);
  b.castShadow = shadow; b.receiveShadow = true;
  group.add(b); return b;
}

/* ------------------------------------------------------- yard props ----- */
const PROPS = {
  sawhorse: (g,x,z) => { box(1.6,.1,.25,mat.wood,x,.75,z,g);
    for (const dx of [-.65,.65]) { box(.08,.8,.5,mat.wood,x+dx,.4,z,g); } },
  wheelbarrow: (g,x,z) => { box(.9,.35,.6,mat.metal,x,.45,z,g);
    box(.06,.5,.06,mat.metal,x+.6,.3,z-.2,g); box(.06,.5,.06,mat.metal,x+.6,.3,z+.2,g);
    const wheel = new THREE.Mesh(new THREE.TorusGeometry(.2,.07,8,20), mat.part);
    wheel.position.set(x-.5,.2,z); wheel.castShadow = true; g.add(wheel); },
  mixer: (g,x,z) => { box(1,.7,.8,mat.metal,x,.35,z,g);
    const drum = new THREE.Mesh(new THREE.CylinderGeometry(.45,.3,.9,14), mat.cone);
    drum.rotation.z = .7; drum.position.set(x,.95,z); drum.castShadow = true; g.add(drum); },
  cone: (g,x,z) => { const c = new THREE.Mesh(new THREE.ConeGeometry(.28,.7,12), mat.cone);
    c.position.set(x,.35,z); c.castShadow = true; g.add(c);
    box(.55,.05,.55,mat.cone,x,.02,z,g,false); },
  ladder: (g,x,z) => { for (const dx of [-.28,.28]) box(.07,2.6,.07,mat.metal,x+dx,1.3,z,g);
    for (let i=0;i<6;i++) box(.6,.05,.05,mat.metal,x,.3+i*.42,z,g,false); },
  toolbox: (g,x,z) => { box(.8,.45,.45,mat.steel,x,.25,z,g); },
  rebar: (g,x,z) => { for (let i=0;i<5;i++)
    box(.05,.05,2.4,mat.metal,x+i*.09,.1+i*.02,z,g,false); },
  generator: (g,x,z) => { box(1.2,.9,.8,mat.part,x,.45,z,g);
    box(.1,.5,.1,mat.metal,x+.4,1.1,z,g,false); },
  signStand: (g,x,z) => { box(.08,1.5,.08,mat.metal,x,.75,z,g);
    box(.9,.6,.06,mat.post,x,1.5,z,g,false); },
  brickPallet: (g,x,z) => { box(1.1,.12,1.1,mat.wood,x,.06,z,g,false);
    box(.95,.55,.95,mat.brick,x,.42,z,g); },
  blockPallet: (g,x,z) => { box(1.1,.12,1.1,mat.wood,x,.06,z,g,false);
    box(.95,.6,.95,mat.block,x,.45,z,g); },
};

/* ---------------------------------------------------------- the hall ---- */
let hallGroup = null, beacons = [], floors = [], roomRects = [], curRoom = null;

function buildHall(sg) {
  if (hallGroup) { scene.remove(hallGroup); hallGroup.traverse(o => {
    o.geometry?.dispose(); }); }
  hallGroup = new THREE.Group(); beacons = []; floors = []; roomRects = []; curRoom = null;
  const h = D.halls.find(x => x.slug === sg);
  const hue = D.districts[h.district].hue;
  const W = 12 * U, DEP = h.depth * U;
  const cx = (x) => x - W/2, cz = (z) => z - DEP/2;   // centre the building

  // slab and perimeter (front face open)
  box(W + .6, .35, DEP + .6, mat.slab, 0, .17, 0, hallGroup);
  box(W, 3.2, .25, mat.wall, 0, 1.95, cz(DEP), hallGroup);          // back
  box(.25, 3.2, DEP, mat.wall, cx(0), 1.95, 0, hallGroup);          // left
  box(.25, 3.2, DEP, mat.wall, cx(W), 1.95, 0, hallGroup);          // right
  // district fascia over the open front
  const fascia = new THREE.Mesh(new THREE.BoxGeometry(W + .8, .55, .5),
    new THREE.MeshStandardMaterial({
      color: new THREE.Color().setHSL(hue/360, .55, .5), roughness: .5 }));
  fascia.position.set(0, 3.6, cz(0)); fascia.castShadow = true;
  hallGroup.add(fascia);
  const sign = label(h.name, D.i18n[loc].districts[h.district], 1.35);
  sign.position.set(0, 5.1, cz(0)); hallGroup.add(sign);

  // roof trusses across the span, and lit strips along the side walls
  for (let tz = 4; tz < DEP - 1; tz += 6) {
    box(W - .6, .18, .5, mat.metal, 0, 3.05, cz(tz), hallGroup, false);
    const lamp = new THREE.Mesh(new THREE.BoxGeometry(1.6, .1, .5), mat.win);
    lamp.position.set(0, 2.9, cz(tz)); hallGroup.add(lamp);
  }
  for (const wx of [cx(0) + .18, cx(W) - .18]) {
    const strip = new THREE.Mesh(new THREE.BoxGeometry(.06, .55, DEP * .8), mat.win);
    strip.position.set(wx, 2.55, 0); hallGroup.add(strip);
  }

  // rooms: tinted floor + low partitions + label
  const stns = h.stations.map(id => D.stations[id]);
  for (const r of h.rooms) {
    const rw = r.w * U, rd = r.h * U;
    const rx = cx(r.x * U + rw/2), rz = cz(r.y * U + rd/2);
    const fin = D.finCat[D.finishes[h.slug][r.strand].surface];
    const ftex = finishTex(fin).clone(); ftex.needsUpdate = true;
    ftex.repeat.set(Math.max(1, (rw - .3) / fin.tile_m),
                    Math.max(1, (rd - .3) / fin.tile_m));
    const floor = new THREE.Mesh(new THREE.BoxGeometry(rw - .3, .06, rd - .3),
      new THREE.MeshStandardMaterial({ map: ftex,
        roughness: fin.roughness, metalness: fin.metalness }));
    floor.position.set(rx, .38, rz); floor.receiveShadow = true;
    floor.userData.room = r.label;
    hallGroup.add(floor); floors.push(floor);
    roomRects.push({ x0: r.x * U - W/2, x1: r.x * U - W/2 + rw,
                     z0: r.y * U - DEP/2, z1: r.y * U - DEP/2 + rd,
                     label: r.label, strand: r.strand });
    // safety rooms carry a hazard-stripe threshold at the doorway
    if (r.strand === 'safety') {
      const stripe = new THREE.Mesh(new THREE.BoxGeometry(Math.min(rw-.6,2.4), .07, .5),
        mat.post);
      stripe.position.set(rx, .42, rz + rd/2 - .4); hallGroup.add(stripe);
    }
    // the trade's own fixtures, benched along the back of the room
    (r.fixtures || []).slice(0, 3).forEach((fx, fi) => {
      const bx = rx - rw/2 + (fi + 1) * rw / ((r.fixtures.length||1) + 1);
      const bz = rz - rd/2 + .8;
      box(1.3, .12, .7, mat.steel, bx, .95, bz, hallGroup);
      box(.12, .5, .6, mat.part, bx - .5, .62, bz, hallGroup);
      box(.12, .5, .6, mat.part, bx + .5, .62, bz, hallGroup);
      box(.5, .35, .35, mat.metal, bx, 1.25, bz, hallGroup);
      const fl = label(fx, null, .34);
      fl.position.set(bx, 1.85, bz); hallGroup.add(fl);
    });
    box(rw, 1.1, .12, mat.part, rx, .9, rz - rd/2, hallGroup);
    box(rw, 1.1, .12, mat.part, rx, .9, rz + rd/2, hallGroup);
    box(.12, 1.1, rd, mat.part, rx - rw/2, .9, rz, hallGroup);
    box(.12, 1.1, rd, mat.part, rx + rw/2, .9, rz, hallGroup);
    const lab = label(r.label, D.i18n[loc].strands[r.strand], .55);
    lab.position.set(rx, 2.2, rz); hallGroup.add(lab);

    // stations standing in this room
    const here = stns.filter(s => s.room === r.label);
    here.forEach((s, i) => {
      const px = rx - rw/2 + (i + 1) * rw / (here.length + 1);
      const post = new THREE.Mesh(new THREE.CylinderGeometry(.09, .12, 1.5, 10), mat.post);
      post.position.set(px, 1.1, rz); post.castShadow = true;
      const gem = new THREE.Mesh(new THREE.OctahedronGeometry(.34), mat.post);
      gem.position.set(px, 2.15, rz); gem.castShadow = true;
      gem.userData.station = s.station_id; gem.userData.spin = true;
      post.userData.station = s.station_id;
      hallGroup.add(post, gem); beacons.push(gem, post);
    });
  }

  // the apron: recovered yard layout for seeded halls, a light deterministic
  // dressing for the rest. Original yard coords span ±16; fold them onto the
  // strip in front of the open face.
  const props = h.stations.length ? D.yard
    : Array.from({ length: 7 }, (_, i) => {
        const keys = Object.keys(PROPS);
        return { t: keys[(h.index * 7 + i * 3) % keys.length],
                 p: [((h.index + i * 5) % 13) - 6 + ((i % 2) ? 8 : -8), 0, -(4 + (i * 2.4) % 10)] };
      });
  for (const pr of props) {
    const fn = PROPS[pr.t]; if (!fn) continue;
    const px = pr.p[0] * (h.stations.length ? .95 : 1);
    const pz = h.stations.length ? -(DEP/2 + 3 + (pr.p[2] + 16) * .42) : cz(0) + pr.p[2];
    if (Math.abs(px) > 60 || Math.abs(pz) > 60) continue;
    fn(hallGroup, px, pz);
  }
  scene.add(hallGroup);

  document.getElementById('hname').textContent = h.name;
  // the regional chapter line: home region marked, chapters at the rest
  const home = D.chapters.of[h.slug];
  document.getElementById('hfocus').textContent = h.focus + ' \\u00b7 '
    + Object.entries(D.chapters.regions)
        .map(([ck, ab]) => ab + (ck === home ? ' \\u2302' : ''))
        .join(' \\u00b7 ');
}

/* -------------------------------------------------------- campus view --- */
let campusGroup = null, buildings = [], campusSpin = [];
let regionGroup = null, plates = [], anchorPins = 0;
let campusKey = D.halls.some(h => h.slug === params.get('hall'))
  ? Object.keys(D.campuses).find(k =>
      D.campuses[k].halls.includes(params.get('hall')))
  : (D.campuses[params.get('campus')] ? params.get('campus') : 'treasure-island');

const campusOfHall = (sg) =>
  Object.keys(D.campuses).find(k => D.campuses[k].halls.includes(sg));

/* ---- buildings, campus roads, and the cluster frame --------------------- */
// Buildings and roads share one cluster-local frame (u lateral, v radial),
// so "roads never intersect buildings" is a rectangle test the build runs
// on itself: any overlap counts in roadFaults, and the harness asserts 0.
let roadFaults = 0, roadCount = 0;

const STYLE_OF = { industry: 'saw', transport: 'saw', earthworks: 'saw',
                   envelope: 'gable', control: 'gable',
                   structural: 'flat', systems: 'flat', energy: 'flat' };

function building(h, style, g) {   // built at the local origin, door toward -z
  const dep = Math.max(h.depth, 5), wid = 12;
  const hgt = 6 + (h.depth % 3) * .7;
  const hue = D.districts[h.district].hue;
  const bld = box(wid, hgt, dep, mat.wall, 0, hgt / 2, 0, g);
  bld.userData.slug = h.slug;
  const hueMat = new THREE.MeshStandardMaterial({
    color: new THREE.Color().setHSL(hue / 360, .5, .45), roughness: .6 });
  const band = new THREE.Mesh(new THREE.BoxGeometry(wid + .4, .9, dep + .4), hueMat);
  band.position.set(0, hgt - .2, 0); g.add(band);
  for (const [tx, tz] of [[-wid/2, -dep/2], [wid/2, -dep/2],
                          [-wid/2, dep/2], [wid/2, dep/2]]) {
    const trim = new THREE.Mesh(new THREE.BoxGeometry(.5, hgt, .5), hueMat);
    trim.position.set(tx, hgt / 2, tz); g.add(trim);
  }
  for (const zz of [-dep/2 - .03, dep/2 + .03]) {
    const strip = new THREE.Mesh(new THREE.BoxGeometry(wid * .78, .7, .06), mat.win);
    strip.position.set(0, hgt * .55, zz); g.add(strip);
  }
  box(1.6, 2.4, .1, mat.part, 0, 1.2, -dep/2 - .06, g, false);
  if (style === 'saw') {              // industrial sawtooth roofline
    for (let sx = -wid/2 + 2; sx < wid/2 - .5; sx += 4) {
      const w = box(3.2, 1.5, dep - .6, mat.metal, sx, hgt + .55, 0, g);
      w.rotation.z = .42;
    }
  } else if (style === 'gable') {     // pitched pair
    const r1 = box(wid * .6, .5, dep + .3, mat.part, -wid * .24, hgt + 1.1, 0, g);
    r1.rotation.z = .48;
    const r2 = box(wid * .6, .5, dep + .3, mat.part, wid * .24, hgt + 1.1, 0, g);
    r2.rotation.z = -.48;
  } else {                            // flat: parapet already, rooftop unit
    box(1.6, .8, 1.2, mat.metal, wid * .22, hgt + .4, dep * .15, g);
  }
  if (h.stations.length) {
    const bcn = new THREE.Mesh(new THREE.OctahedronGeometry(.9), mat.post);
    bcn.position.set(0, hgt + 2, 0); g.add(bcn); campusSpin.push(bcn);
  }
  return { mesh: bld, w: wid, d: dep };
}

function roadRect(u, v, w, len, m, g, y = .05) {
  const r = new THREE.Mesh(new THREE.PlaneGeometry(w, len), m);
  r.rotation.x = -Math.PI / 2; r.position.set(u, y, v);
  r.receiveShadow = true; g.add(r);
  return { u, v, w, h: len };
}

function dashesU(u0, u1, v, g) {
  for (let u = u0 + 2; u < u1 - 2; u += 4)
    box(1.6, .02, .16, mat.paint, u, .09, v, g, false);
}
function dashesV(v0, v1, u, g) {
  for (let v = v0 + 2; v < v1 - 2; v += 4)
    box(.16, .02, 1.6, mat.paint, u, .09, v, g, false);
}

/* ------------------------------ campus dressing, keyed by campus slug --- */
function dressCampus(key, g, R) {
  if (key === 'treasure-island') {
    // the island: a bay ring beyond the ground's edge and a flag over the plaza
    const bay = new THREE.Mesh(new THREE.RingGeometry(258, 640, 64), mat.water);
    bay.rotation.x = -Math.PI / 2; bay.position.y = -.08; g.add(bay);
    box(.14, 15, .14, mat.metal, 0, 7.5, -30, g);
    const flag = new THREE.Mesh(new THREE.PlaneGeometry(4.6, 2.6),
      new THREE.MeshStandardMaterial({ color: 0xE8A33D, side: THREE.DoubleSide }));
    flag.position.set(2.4, 13.4, -30); g.add(flag);
  }
  if (key === 'oakland') {
    // container rows and a gantry crane on the estuary edge
    const cols = [0xB3462F, 0x3A5A78, 0x5B7A5A, 0x8a6a42, 0x41626b];
    for (let i = 0; i < 14; i++) {
      const cx = -46 + (i % 7) * 15, cz = R + 34 + Math.floor(i / 7) * 6;
      const stack = 1 + (i * 7) % 3;
      for (let sN = 0; sN < stack; sN++) {
        const c = box(12, 2.6, 2.5, new THREE.MeshStandardMaterial({
          color: cols[(i + sN) % cols.length], roughness: .8 }),
          cx, 1.3 + sN * 2.6, cz, g);
        c.castShadow = true;
      }
    }
    for (const lx of [-14, 14]) {
      box(1.2, 26, 1.2, mat.metal, lx, 13, R + 46, g);
      box(1.2, 26, 1.2, mat.metal, lx, 13, R + 52, g);
    }
    box(34, 1.6, 2, mat.post, 0, 26, R + 49, g);
    const quay = new THREE.Mesh(new THREE.PlaneGeometry(400, 160), mat.water);
    quay.rotation.x = -Math.PI / 2; quay.position.set(0, -.06, R + 140); g.add(quay);
  }
  if (key === 'new-orleans') {
    // the river: a broad channel, pilings, and a working barge
    const river = new THREE.Mesh(new THREE.PlaneGeometry(560, 130), mat.water);
    river.rotation.x = -Math.PI / 2; river.position.set(0, -.06, R + 105); g.add(river);
    box(440, 2.4, 5, mat.slab, 0, 1.2, R + 38, g);      // the levee
    for (let i = 0; i < 12; i++)
      box(.8, 3.6, .8, mat.wood, -110 + i * 20, 1.2, R + 50, g);
    box(30, 2, 10, mat.part, 26, .9, R + 78, g);        // barge hull
    box(6, 3, 4, mat.metal, 36, 3.4, R + 78, g);        // wheelhouse
  }
}

/* ------------------------------------------------- the city layer -------- */
// A campus with a RECORDED city frame (New Orleans, from Locator.X's
// region record) grows into its real surroundings: each institution from
// the POI table stands at its true east/north offset (13 units per km,
// walkable), joined to the ring road by SCHEMATIC avenues; the river and
// lake bands are schematic too, and the labels say which is which.
let cityPois = 0, walkLim = 169, cityHits = [], chapterHit = [];

/* The regional chapter hall: one pavilion on each plaza carrying every
   union homed elsewhere - the 111-trade network made visible per campus.
   An Academy structure only; the panel repeats the no-local-named honesty. */
function openChapters() {
  const hosted = D.halls.filter((h) => D.chapters.of[h.slug] !== campusKey);
  const byHome = {};
  for (const h of hosted) (byHome[D.chapters.of[h.slug]] ??= []).push(h.name);
  document.getElementById('pbody').innerHTML = `
    <h2>${t('chapters.hall')}</h2>
    <span class="chip">${D.campuses[campusKey].name}</span>
    <span class="chip">${hosted.length} / 111</span>
    ${Object.entries(byHome).map(([ck, names]) => `
      <h3>${D.campuses[ck].name} · ${D.chapters.regions[ck]}</h3>
      <p style="color:var(--muted);font-size:13px;line-height:1.7">${names.join(' · ')}</p>`).join('')}
    <p style="color:var(--muted);font-size:12px">${D.chapters.honesty}</p>`;
  document.body.classList.add('open');
}
window.__tc3dChapters = openChapters;

function buildChapterHall(g, key) {
  const pav = new THREE.Group(); g.add(pav);
  const base = new THREE.Mesh(new THREE.CylinderGeometry(7, 7.6, .9, 8), mat.slab);
  base.position.y = .45; base.receiveShadow = true; pav.add(base);
  const walls = new THREE.Mesh(new THREE.CylinderGeometry(5.6, 6, 4.2, 8), mat.wall);
  walls.position.y = 3; walls.castShadow = walls.receiveShadow = true; pav.add(walls);
  const band = new THREE.Mesh(new THREE.CylinderGeometry(5.75, 5.75, .5, 8), mat.post);
  band.position.y = 4.6; pav.add(band);
  const roof = new THREE.Mesh(new THREE.ConeGeometry(7.2, 2.6, 8), mat.part);
  roof.position.y = 6.5; roof.castShadow = true; pav.add(roof);
  walls.userData.chapters = true;
  chapterHit = [walls];
  const cl = label(t('chapters.hall'), '+' + D.chapters.hosted[key], 2);
  cl.position.y = 12; pav.add(cl);
}
const CITY_S = 13;   // units per real kilometre in the city layer

/* An institution's panel: the RECORDED coordinate with a live-map link
   built from it, the authored blurb labelled as authored, and the union
   honesty line - hall addresses are not recorded, no local is named. */
function openCityPoi(name) {
  const p = (D.geo.cityPois?.[campusKey] ?? []).find((x) => x.name === name);
  if (!p) return;
  const osm = `https://www.openstreetmap.org/?mlat=${p.lat}&mlon=${p.lng}`
    + `#map=16/${p.lat}/${p.lng}`;
  document.getElementById('pbody').innerHTML = `
    <h2>${p.name}</h2>
    <span class="chip" style="border-color:var(--good);color:var(--good)">RECORDED</span>
    <span class="chip">${p.km} km · ${p.bearing}°</span>
    ${p.blurb ? `<p>${p.blurb}</p>` : ''}
    <p style="font-family:'IBM Plex Mono',monospace;font-size:13.5px">
      ${p.lat.toFixed(4)}, ${p.lng.toFixed(4)}
      <span style="color:var(--muted)">WGS84</span></p>
    <p><a href="${osm}" target="_blank" rel="noopener"
      style="color:var(--steel)">↗ OpenStreetMap</a>
      <span style="color:var(--muted)">· live map from the RECORDED coordinate</span></p>
    <p style="color:var(--muted);font-size:12px">coordinate: ${p.src}${
      p.bp ? `<br>description: ${p.bp}` : ''}</p>
    <p style="color:var(--muted);font-size:12px">${t('honesty.taxonomy')}</p>`;
  document.body.classList.add('open');
}
window.__tc3dPoi = openCityPoi;   // test hook

function buildCity(g, R) {
  const pois = D.geo.cityPois?.[campusKey] ?? [];
  if (!pois.length) return;
  const grass = new THREE.MeshStandardMaterial({ color: 0x3d5238, roughness: .95 });
  const hues = [42, 152, 205, 268, 20, 96, 330];
  pois.forEach((p, i) => {
    const x = p.e * CITY_S, z = -p.n * CITY_S;
    const len = Math.hypot(x, z), ux = x / len, uz = z / len;
    // the avenue: ring road out to the institution's block
    const r0 = R - 22, aLen = len - r0 - 9;
    const av = box(aLen, .06, 3.6, mat.road, 0, .03, 0, g, false);
    av.position.set((r0 + aLen / 2) * ux, .03, (r0 + aLen / 2) * uz);
    av.rotation.y = -Math.atan2(uz, ux);
    for (let d = r0 + 4; d < len - 10; d += 7)
      box(1.7, .02, .16, mat.paint, d * ux, .08, d * uz, g, false)
        .rotation.y = -Math.atan2(uz, ux);
    // the institution: green, main hall, tower, and its name with real km
    box(15, .12, 15, grass, x, .06, z, g, false);
    const hgt = 7 + (i % 3) * 2.5;
    const bmat = new THREE.MeshStandardMaterial({
      color: new THREE.Color().setHSL(hues[i % hues.length] / 360, .34, .42),
      roughness: .75 });
    const bld = box(8, hgt, 6.5, bmat, x - 2, .12 + hgt / 2, z + 1.5, g);
    const twr = box(2.6, hgt + 5, 2.6, bmat, x + 4, .12 + (hgt + 5) / 2, z - 3.5, g);
    box(3, .5, 3, mat.slab, x + 4, hgt + 5.4, z - 3.5, g, false);
    bld.userData.poi = twr.userData.poi = p.name;
    cityHits.push(bld, twr);
    const pl = label(p.name, p.km + ' km \\u00b7 RECORDED', 1.7);
    pl.position.set(x, hgt + 10, z); g.add(pl);
    cityPois++;
  });
  // the crescent: a schematic Mississippi south of the uptown institutions
  const river = new THREE.Mesh(new THREE.TubeGeometry(
    new THREE.QuadraticBezierCurve3(
      new THREE.Vector3(-150, 0, 92), new THREE.Vector3(-15, 0, 70),
      new THREE.Vector3(110, 0, 24)), 48, 10, 8), mat.water);
  river.scale.y = .012; river.position.y = .09; g.add(river);
  const rl = label('Mississippi River', 'SCHEMATIC', 1.6);
  rl.position.set(-30, 7, 76); g.add(rl);
  // and the lake north of UNO/SUNO
  const lake = new THREE.Mesh(new THREE.PlaneGeometry(340, 70), mat.water);
  lake.rotation.x = -Math.PI / 2; lake.position.set(10, .08, -168);
  g.add(lake);
  const ll = label('Lake Pontchartrain', 'SCHEMATIC', 1.6);
  ll.position.set(10, 7, -150); g.add(ll);
}

function buildCampus(key) {
  if (campusGroup) scene.remove(campusGroup);
  campusGroup = new THREE.Group(); buildings = []; campusSpin = [];
  roadFaults = 0; roadCount = 0; cityPois = 0; cityHits = [];
  const camp = D.campuses[key];
  const dk = camp.districts;
  const R = dk.length === 2 ? 62 : 84;
  campusR = R;
  const rr = R - 24;
  // the ring road, dashed, and the plaza walkway
  const ring = new THREE.Mesh(new THREE.RingGeometry(rr - 2.4, rr + 2.4, 96), mat.road);
  ring.rotation.x = -Math.PI / 2; ring.position.y = .05;
  ring.receiveShadow = true; campusGroup.add(ring); roadCount++;
  for (let a = 0; a < 64; a++) {
    const th = a / 64 * Math.PI * 2;
    const dsh = box(.16, .02, 1.6, mat.paint,
      Math.cos(th) * rr, .09, Math.sin(th) * rr, campusGroup, false);
    dsh.rotation.y = -th;
  }
  const wlk = new THREE.Mesh(new THREE.RingGeometry(24, 27, 64), mat.walkway);
  wlk.rotation.x = -Math.PI / 2; wlk.position.y = .04;
  wlk.receiveShadow = true; campusGroup.add(wlk);

  dk.forEach((k, di) => {
    const d = D.districts[k];
    const ang = di / dk.length * Math.PI * 2 - Math.PI / 2;
    const rad = new THREE.Vector2(Math.cos(ang), Math.sin(ang));
    const psi = Math.atan2(rad.x, rad.y);
    const cg = new THREE.Group();
    cg.position.set(rad.x * R, 0, rad.y * R);
    cg.rotation.y = psi;               // local +z = outward, doors face the plaza
    campusGroup.add(cg);
    const cols = Math.ceil(Math.sqrt(d.halls.length * 1.7));
    const style = STYLE_OF[k] ?? 'flat';
    // row pitch sized to the district's deepest building, so a street
    // always fits between rows with clearance on both sides
    const maxDep = Math.max(...d.halls.map((sg) =>
      Math.max(D.halls.find(x => x.slug === sg).depth, 5)));
    const pitch = maxDep + 8;
    const rows = {}, rects = [], roads = [];
    d.halls.forEach((sg, i) => {
      const h = D.halls.find(x => x.slug === sg);
      const gx = (i % cols) - (cols - 1) / 2, gz = Math.floor(i / cols);
      const bg = new THREE.Group();
      bg.position.set(gx * 16, 0, gz * pitch);
      cg.add(bg);
      const b = building(h, style, bg);
      buildings.push(b.mesh);
      (rows[gz] ??= []).push({ u: gx * 16, v: gz * pitch, halfD: b.d / 2 });
      rects.push({ u: gx * 16, v: gz * pitch, hw: b.w / 2 + .2, hd: b.d / 2 + .2 });
    });
    // roads, cluster-local: a street along each row's frontage, a driveway
    // to every door, the alley to the ring, and the spur to the plaza
    for (const members of Object.values(rows)) {
      const rv = members[0].v;
      const u0 = Math.min(...members.map(m => m.u)) - 8;
      const u1 = Math.max(...members.map(m => m.u)) + 8;
      const maxHalfD = Math.max(...members.map(m => m.halfD));
      const sv = rv - maxHalfD - 2.6;
      roads.push(roadRect((u0 + u1) / 2, sv, u1 - u0, 3.6, mat.road, cg));
      dashesU(u0, u1, sv, cg);
      for (const m of members) {
        const top = rv - m.halfD - .45, bot = sv + 1.8;
        if (top - bot > .1)
          roads.push(roadRect(m.u, (top + bot) / 2, 2.4, top - bot, mat.drive, cg, .045));
      }
      roadCount += 1 + members.length;
    }
    const lastV = Math.max(...Object.values(rows).map(m => m[0].v));
    // the alley runs up a real gap between columns: even grids have a
    // building at u=8 and their free lane at u=0, odd grids the reverse
    const alleyU = (cols % 2 === 0) ? 0 : 8;
    roads.push(roadRect(alleyU, ((rr - R) + (lastV - 2.6)) / 2, 3.2,
      (lastV - 2.6) - (rr - R), mat.road, cg));
    dashesV(rr - R, lastV - 2.6, alleyU, cg);
    roads.push(roadRect(0, ((27 - R) + (rr - R)) / 2, 4.2,
      (rr - R) - (27 - R), mat.road, cg));
    dashesV(27 - R, rr - R, 0, cg);
    roadCount += 2;
    // the guarantee: no road rectangle overlaps a building rectangle
    for (const r of roads) for (const b of rects) {
      if (Math.abs(r.u - b.u) < r.w / 2 + b.hw
        && Math.abs(r.v - b.v) < r.h / 2 + b.hd) {
        roadFaults++;
        (window.__faults ??= []).push({ r, b });
      }
    }
    const dl = label(D.i18n[loc].districts[k], null, 3);
    dl.position.set(rad.x * (R - 14), 15, rad.y * (R - 14));
    campusGroup.add(dl);
  });
  const plaza = new THREE.Mesh(new THREE.CylinderGeometry(24, 24, .3, 48),
    new THREE.MeshStandardMaterial({ map: concreteTex, color: 0xb8bdbd, roughness: .95 }));
  plaza.position.y = .15; plaza.receiveShadow = true; campusGroup.add(plaza);
  const sign = label(camp.name, camp.city + ', ' + camp.region, 3.2);
  sign.position.set(0, 18, 0); campusGroup.add(sign);
  dressCampus(key, campusGroup, R + 42);
  buildChapterHall(campusGroup, key);
  buildCity(campusGroup, R);
  walkLim = cityPois ? 162 : campusR + 85;
  scene.add(campusGroup);
}

/* ---------------------------------------------------------- region view --- */
// Plate positions from the geo registry: TRUE bearings between the real
// coordinates; distances log-compressed so 9 km of bay and 3,000 km of
// gulf share one board. The route labels carry the real kilometres.
const PLATE_POS = (() => {
  const range = (km) => 34 + 50 * Math.log10(1 + km);
  const pos = { 'treasure-island': [0, 0] };
  for (const r of D.geo.routes) {
    if (r.from !== 'treasure-island') continue;
    const b = r.bearing_deg * Math.PI / 180, d = range(r.km);
    pos[r.to] = [Math.sin(b) * d, -Math.cos(b) * d];
  }
  const ks = Object.keys(pos);
  const cx = ks.reduce((a, k) => a + pos[k][0], 0) / ks.length;
  const cz = ks.reduce((a, k) => a + pos[k][1], 0) / ks.length;
  for (const k of ks) { pos[k][0] -= cx; pos[k][1] -= cz; }
  return pos;
})();

function buildRegion() {
  if (regionGroup) scene.remove(regionGroup);
  regionGroup = new THREE.Group(); plates = []; anchorPins = 0;
  // the gulf-to-bay board: water underneath everything
  const sea = new THREE.Mesh(new THREE.PlaneGeometry(1600, 1600), mat.water);
  sea.rotation.x = -Math.PI / 2; sea.position.y = -.12; sea.receiveShadow = true;
  regionGroup.add(sea);
  const centers = {};
  for (const [key, camp] of Object.entries(D.campuses)) {
    const [px, pz] = PLATE_POS[key];
    centers[key] = new THREE.Vector3(px, 0, pz);
    const plate = new THREE.Mesh(new THREE.CylinderGeometry(36, 40, 2.2, 48), mat.land);
    plate.position.set(px, 1.1, pz); plate.receiveShadow = plate.castShadow = true;
    plate.userData.campus = key;
    regionGroup.add(plate); plates.push(plate);
    // one block per hosted district, sized by its hall count
    camp.districts.forEach((dkey, i) => {
      const d = D.districts[dkey];
      const ang = i / camp.districts.length * Math.PI * 2;
      const bx = px + Math.cos(ang) * 19, bz = pz + Math.sin(ang) * 19;
      const hgt = 4 + d.halls.length * .55;
      const blk = box(11, hgt, 11, new THREE.MeshStandardMaterial({
        color: new THREE.Color().setHSL(d.hue / 360, .45, .4), roughness: .7 }),
        bx, 2.2 + hgt / 2, bz, regionGroup);
      blk.userData.campus = key; plates.push(blk);
      const cl = label(String(d.halls.length), null, 1.4);
      cl.position.set(bx, hgt + 6, bz); regionGroup.add(cl);
    });
    const pl = label(camp.name,
      camp.city + ', ' + camp.region + ' · +' + D.chapters.hosted[key], 3.4);
    pl.position.set(px, 30, pz); regionGroup.add(pl);
    // RECORDED anchors from the geo registry: real cities and institutions
    // around each campus, marked at their true bearing on the plate rim.
    // The rim radius is log-eased so a 4 km and a 40 km anchor both read;
    // the label carries the real kilometres, like the route labels do.
    for (const a of (D.geo.anchors[key] ?? [])) {
      const b = a.bearing_deg * Math.PI / 180;
      const rr = 28 + 8 * Math.log10(1 + a.km);
      const ax = px + Math.sin(b) * rr, az = pz - Math.cos(b) * rr;
      const pin = new THREE.Mesh(new THREE.CylinderGeometry(.55, .9, 4.6, 10),
        new THREE.MeshStandardMaterial({ color: 0xE8A33D, roughness: .5,
          emissive: 0x7a4d08 }));
      pin.position.set(ax, 3.4, az); regionGroup.add(pin);
      anchorPins++;
      const al = label(a.name, a.km + ' km', 1.15);
      al.position.set(ax, 9.6, az); regionGroup.add(al);
    }
  }
  // glowing routes between the campuses
  const lineMat = new THREE.LineBasicMaterial({ color: 0xE8A33D, transparent: true, opacity: .65 });
  const pairs = [['treasure-island', 'oakland'], ['oakland', 'new-orleans'],
                 ['treasure-island', 'new-orleans']];
  for (const [a, b] of pairs) {
    const pa = centers[a], pb = centers[b];
    const mid = pa.clone().add(pb).multiplyScalar(.5); mid.y = 26;
    const curve = new THREE.QuadraticBezierCurve3(
      pa.clone().setY(3), mid, pb.clone().setY(3));
    const geo = new THREE.BufferGeometry().setFromPoints(curve.getPoints(40));
    regionGroup.add(new THREE.Line(geo, lineMat));
    const km = D.geo.routes.find((r) =>
      (r.from === a && r.to === b) || (r.from === b && r.to === a))?.km;
    if (km !== undefined) {
      const kl = label(`${km.toLocaleString('en-US')} km`, null, 2.2);
      kl.position.copy(mid).setY(mid.y + 5);
      regionGroup.add(kl);
    }
  }
  const sign = label('SmartCiti.X : Trade Craft Academy', 'powered by AGI Corp', 3.6);
  sign.position.set(0, 44, 10); regionGroup.add(sign);
  scene.add(regionGroup);
}

function showRegion() {
  if (sim) teardownSim();
  view = 'region';
  if (walkActive) (isTouch ? exitWalkMode() : plc.unlock());
  if (avatarGroup) avatarGroup.visible = false;
  wheelShow(false);
  if (hallGroup) hallGroup.visible = false;
  if (campusGroup) campusGroup.visible = false;
  ground.visible = grid.visible = false;
  buildRegion();
  scene.fog.near = 380; scene.fog.far = 1300;
  controls.maxDistance = 700; controls.minDistance = 60;
  camera.position.set(0, 225, 235); controls.target.set(10, 0, 0);
  document.getElementById('hname').textContent = t('view.region');
  document.getElementById('hfocus').textContent =
    t('figures.campuses').replace('{n}', Object.keys(D.campuses).length) + ' · ' +
    t('figures.halls').replace('{n}', D.halls.length) + ' · ' +
    t('figures.districts').replace('{n}', Object.keys(D.districts).length);
  document.getElementById('hint').textContent =
    t('hint.campus') + ' \u00b7 ' + t('geo.note');
  document.getElementById('walkBtn').style.display = 'none';
  document.getElementById('avaBtn').style.display = '';
  document.getElementById('campusBtn').style.display = 'none';
  document.getElementById('simBtn').style.display = 'none';
  syncURL();
}

function showCampus(key) {
  if (sim) teardownSim();
  campusKey = key; view = 'campus';
  if (walkActive) (isTouch ? exitWalkMode() : plc.unlock());
  if (avatarGroup) avatarGroup.visible = false;
  wheelShow(false);
  if (hallGroup) hallGroup.visible = false;
  if (regionGroup) regionGroup.visible = false;
  ground.visible = grid.visible = true;
  buildCampus(key);
  scene.fog.near = 160; scene.fog.far = 640;
  controls.maxDistance = 420; controls.minDistance = 20;
  camera.position.set(0, 165, 195); controls.target.set(0, 0, 0);
  const camp = D.campuses[key];
  document.getElementById('hname').textContent = camp.name;
  document.getElementById('hfocus').textContent =
    camp.city + ', ' + camp.region + ' — ' + camp.tagline
    + (D.geo.cityPois?.[key] ? ' · ' + t('city.note') : '');
  document.getElementById('hint').textContent = t('hint.campus');
  document.getElementById('walkBtn').style.display = '';
  document.getElementById('avaBtn').style.display = '';
  document.getElementById('campusBtn').style.display = 'none';
  document.getElementById('simBtn').style.display = 'none';
  syncURL();
}

function showHall(sg) {
  if (sim) teardownSim();
  slug = sg; view = 'hall'; campusKey = campusOfHall(sg);
  if (avatarGroup) avatarGroup.visible = false;
  if (!(isTouch && walkActive)) wheelShow(false);
  if (regionGroup) regionGroup.visible = false;
  if (campusGroup) campusGroup.visible = false;
  ground.visible = grid.visible = true;
  buildHall(sg);
  scene.fog.near = 70; scene.fog.far = 170;
  controls.maxDistance = 120; controls.minDistance = 8;
  camera.position.set(30, 26, 42); controls.target.set(0, 2, 0);
  document.getElementById('hint').textContent =
    '\u25cf ' + t('hall.stations') + ' \u00b7 ' + t('hall.rooms') + ' \u2192 ' + t('map.layer.modules');
  document.getElementById('walkBtn').style.display = '';
  document.getElementById('avaBtn').style.display = '';
  const cb = document.getElementById('campusBtn');
  cb.style.display = ''; cb.textContent = '\u2191 ' + D.campuses[campusKey].name;
  document.getElementById('simBtn').style.display =
    (D.sims.bindings[sg] && !('ontouchstart' in window)) ? '' : 'none';
  syncURL();
}

/* ----------------------------------------------------------- walk mode --- */
const plc = new PointerLockControls(camera, renderer.domElement);
let walkActive = false;
const keys = {};
document.addEventListener('keydown', (e) => {
  keys[e.code] = true;
  if (sim && e.code === 'Escape' && !document.body.classList.contains('open'))
    exitSim();
  if (sim && e.code === 'Space') { e.preventDefault(); sim.action?.(); }
  if (walkActive && view === 'campus' && nearSlug
      && (e.code === 'Enter' || e.code === 'KeyE')) enterHallWalking(nearSlug);
  if (walkActive && view === 'campus' && nearPoi
      && (e.code === 'Enter' || e.code === 'KeyE')) {
    plc.unlock(); openCityPoi(nearPoi);
  }
});
document.addEventListener('keyup', (e) => { keys[e.code] = false; });

let campusR = 84, nearSlug = null, nearPoi = null;
function enterWalk() {
  if (view === 'region' || view === 'avatar') return;
  if (isTouch) {
    if (walkActive) return exitWalkMode();
    return enterTouchWalk();
  }
  controls.autoRotate = false; controls.enabled = false;
  if (view === 'hall') {
    const h = D.halls.find(x => x.slug === slug);
    camera.position.set(0, 1.7, -(h.depth * U) / 2 - 8);
  } else {
    camera.position.set(0, 1.7, 30);
  }
  camera.lookAt(0, 1.7, 0);
  plc.lock();
}

function enterHallWalking(sg) {
  showHall(sg);
  const h = D.halls.find(x => x.slug === sg);
  camera.position.set(0, 1.7, -(h.depth * U) / 2 - 8);
  document.getElementById('hint').textContent = t('hint.walk');
}
plc.addEventListener('lock', () => {
  walkActive = true;
  document.getElementById('cross').style.display = 'block';
  document.getElementById('hint').textContent = t('hint.walk');
});
plc.addEventListener('unlock', () => {
  walkActive = false;
  document.getElementById('cross').style.display = 'none';
  controls.enabled = true;
  const fwd = new THREE.Vector3(); camera.getWorldDirection(fwd);
  controls.target.copy(camera.position).addScaledVector(fwd, 6);
  if (view === 'hall') document.getElementById('hint').textContent =
    '● ' + t('hall.stations') + ' · ' + t('hall.rooms') + ' → ' + t('map.layer.modules');
  else if (view === 'campus') document.getElementById('hint').textContent = t('hint.campus');
  nearSlug = null;
});

function walkStep(dt) {
  const sp = (keys.ShiftLeft || keys.ShiftRight ? 10 : 5) * dt;
  if (keys.KeyW || keys.ArrowUp) plc.moveForward(sp);
  if (keys.KeyS || keys.ArrowDown) plc.moveForward(-sp);
  if (keys.KeyA || keys.ArrowLeft) plc.moveRight(-sp);
  if (keys.KeyD || keys.ArrowRight) plc.moveRight(sp);
  camera.position.y = 1.7;
  if (view === 'hall') {
    const h = D.halls.find(x => x.slug === slug);
    const DEP = h.depth * U;
    camera.position.x = Math.min(21, Math.max(-21, camera.position.x));
    camera.position.z = Math.min(DEP/2 - .8, Math.max(-DEP/2 - 26, camera.position.z));
    const px = camera.position.x, pz = camera.position.z;
    const room = roomRects.find((r) =>
      px >= r.x0 && px <= r.x1 && pz >= r.z0 && pz <= r.z1) ?? null;
    if (room !== curRoom) {
      curRoom = room;
      if (room) {
        const fin = D.finCat[D.finishes[slug][room.strand].surface];
        document.getElementById('hfocus').textContent =
          room.label + ' \u2014 ' + fin.name;
        document.getElementById('hint').textContent =
          condLine(condOf(slug, room.strand));
      } else {
        document.getElementById('hfocus').textContent =
          D.halls.find(x => x.slug === slug).focus;
        document.getElementById('hint').textContent = t('hint.walk');
      }
    }
    return;
  }
  // campus stroll: stay on the grounds, and offer the nearest door
  const len = Math.hypot(camera.position.x, camera.position.z);
  const lim = walkLim;
  if (len > lim) {
    camera.position.x *= lim / len; camera.position.z *= lim / len;
  }
  let best = null, bd = 1e9;
  const wp = new THREE.Vector3();
  for (const b of buildings) {
    b.getWorldPosition(wp);
    const d = Math.hypot(wp.x - camera.position.x, wp.z - camera.position.z);
    if (d < bd) { bd = d; best = b; }
  }
  if (best && bd < 11) {
    if (nearPoi) nearPoi = null;
    nearSlug = best.userData.slug;
    const h = D.halls.find(x => x.slug === nearSlug);
    document.getElementById('hint').textContent = '\u23ce ' + h.name;
    return;
  }
  // strolling the city layer: the nearest institution offers its panel
  let pbest = null, pd = 1e9;
  for (const b of cityHits) {
    b.getWorldPosition(wp);
    const d = Math.hypot(wp.x - camera.position.x, wp.z - camera.position.z);
    if (d < pd) { pd = d; pbest = b; }
  }
  if (pbest && pd < 14) {
    nearSlug = null;
    nearPoi = pbest.userData.poi;
    document.getElementById('hint').textContent = '\u23ce ' + nearPoi;
  } else if (nearSlug || nearPoi) {
    nearSlug = null; nearPoi = null;
    document.getElementById('hint').textContent = t('hint.walk');
  }
}

__SIM_JS__

__AVATAR_JS__

/* ---------------------------------------------------------------- UI ---- */
function renderChrome() {
  const i = D.i18n[loc];
  document.documentElement.lang = loc;
  document.documentElement.dir = i.dir;
  document.getElementById('back').textContent = '← ' + t('nav.campus');
  const hall = document.getElementById('hall');
  const mark = (h) => !h.stations.length ? ''
    : h.stations.every((id) => doneStations.has(id)) ? ' ✓' : ' ●';
  hall.innerHTML = Object.entries(D.districts).map(([k, d]) =>
    `<optgroup label="${i.districts[k]}">` +
    d.halls.map(sg => `<option value="${sg}" ${sg===slug?'selected':''}>` +
      `${D.halls.find(x=>x.slug===sg).name}${mark(D.halls.find(x=>x.slug===sg))}</option>`).join('') +
    `</optgroup>`).join('');
  const lang = document.getElementById('lang');
  lang.setAttribute('aria-label', t('language.select'));
  lang.innerHTML = Object.entries(D.i18n).map(([c, v]) =>
    `<option value="${c}" ${c===loc?'selected':''}>${v.language}</option>`).join('');
  document.getElementById('regionBtn').textContent = '⌂ ' + t('view.region');
  document.getElementById('walkBtn').textContent = '⤞ ' + t('ui.walk');
  document.getElementById('simBtn').textContent = '▶ ' + t('sim.start');
  document.getElementById('avaBtn').textContent = '👤 ' + t('avatar.title');
  document.getElementById('honesty').textContent =
    t('honesty.taxonomy') + ' ' + t('honesty.content') + ' ' + t('progress.local');
  document.getElementById('pclose').textContent = t('ui.close');
}

/* The learner record is device-local only - localStorage, every access
   wrapped so a blocked store never breaks the page - and the honesty line
   in the corner says exactly that. Not a transcript, not certification. */
const PROG_KEY = 'tc-progress';
function loadProg() {
  try { return JSON.parse(localStorage.getItem(PROG_KEY)) ?? {}; }
  catch (e) { return {}; }
}
function saveProg() {
  prog.stations = [...doneStations];
  try { localStorage.setItem(PROG_KEY, JSON.stringify(prog)); }
  catch (e) { /* private mode / blocked store: session-only progress */ }
}
const prog = loadProg();
const doneStations = new Set(Array.isArray(prog.stations) ? prog.stations : []);
prog.sims = typeof prog.sims === 'object' && prog.sims ? prog.sims : {};
let curStation = null;
function scoreChip() {
  const h = D.halls.find(x => x.slug === slug);
  if (view !== 'hall' || !h.stations.length) return '';
  const d = h.stations.filter((id) => doneStations.has(id)).length;
  return ` \u2713 ${d}/${h.stations.length}`;
}
function openStation(id) {
  curStation = id;
  const s = D.stations[id]; const i = D.i18n[loc];
  document.getElementById('pbody').innerHTML = `
    <h2>${s.name}</h2>
    <span class="chip">${s.room}</span><span class="chip">${i.strands[s.strand]} · ${i.tiers[s.tier]}</span>
    <p>${s.lesson}</p><p style="color:var(--muted)">${s.doctrine}</p>
    <h3>${t('station.checklist')}</h3><ul>${s.checklist.map(c=>`<li>${c}</li>`).join('')}</ul>
    <h3>${t('station.quiz')}</h3><div class="q">${s.quiz.question}
      ${s.quiz.options.map(o=>`<button class="opt" data-ok="${o.correct?1:0}">${o.label}</button>`).join('')}</div>`;
  document.body.classList.add('open');
}

__PIPELINE_JS__

function condOf(hallSlug, strand) {
  return D.condOver[hallSlug]?.[strand] ?? D.baseCond[strand];
}
function condLine(c) {
  return `${c.lux} lx \u00b7 ${c.ach} ACH \u00b7 ${c.noise_db} dB \u00b7 `
    + `${c.temp_c[0]}\u2013${c.temp_c[1]} \u00b0C \u00b7 PPE: `
    + (c.ppe.length ? c.ppe.join(', ') : '\u2014');
}

function openRoom(roomLabel) {
  const h = D.halls.find(x => x.slug === slug);
  const r = h.rooms.find(x => x.label === roomLabel);
  const i = D.i18n[loc];
  const sm = D.strandmods[r.strand];
  const F = (n) => n.toLocaleString('en-US');
  const rows = sm.samples.map(x => {
    const id = 'u' + String(h.index).padStart(3, '0') + '.' + x.suffix;
    const st = pipeline(h.index, x.level);
    return `
    <tr><td style="font-family:'IBM Plex Mono',monospace;font-size:12px">${id}</td>
    <td>${i.tiers[x.tier]}</td><td>${x.form}</td>
    <td style="text-align:end">${x.d}</td><td>${i.states[st]}</td></tr>`; }).join('');
  document.getElementById('pbody').innerHTML = `
    <h2>${r.label}</h2>
    <span class="chip">${i.strands[r.strand]}</span>
    <span class="chip">${r.w*3}×${r.h*3} m</span>
    <p style="color:var(--muted)">${r.purpose}</p>
    ${r.fixtures?.length ? `<ul>${r.fixtures.map(f=>`<li>${f}</li>`).join('')}</ul>` : ''}
    ${(() => { const pf = D.finishes[h.slug][r.strand];
      const fin = D.finCat[pf.surface];
      return `<h3>${t('room.finish')}</h3>
        <p><b>${fin.name}</b>` +
        (pf.placed_by === 'hazard'
          ? ` <span class="chip">${pf.hazard}</span>` : '') +
        `<br><span style="color:var(--muted)">${fin.why}.</span></p>` +
        (() => { const c = condOf(h.slug, r.strand);
          return `<p style="color:var(--muted);font-size:13px">${condLine(c)}` +
            (c.hazards?.length
              ? '<br>' + c.hazards.map(z=>`<span class="chip">${z}</span>`).join(' ')
              : '') + `</p>
            <p style="font-size:11px;color:var(--muted);opacity:.8">geometry: SCHEMATIC \u00b7 finish: DERIVED \u00b7 conditions: DERIVED</p>`; })(); })()}
    <h3>${t('map.layer.modules')}</h3>
    <p style="color:var(--muted);font-size:13px">
      ${t('figures.lessons').replace('{n}', F(sm.lessons))} ·
      ${t('figures.modules').replace('{n}', F(sm.modules))} ·
      θ ${sm.d_from}–${sm.d_to}</p>
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <tbody>${rows}</tbody></table>
    <style>#pbody td{border-top:1px solid var(--rule);padding:6px 8px;color:var(--muted)}</style>`;
  document.body.classList.add('open');
}

const ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
renderer.domElement.addEventListener('pointerdown', (e) => {
  if (walkActive) ptr.set(0, 0);
  else ptr.set(e.clientX/innerWidth*2-1, -(e.clientY/innerHeight)*2+1);
  ray.setFromCamera(ptr, camera);
  if (view === 'region') {
    const phit = ray.intersectObjects(plates, false)[0];
    if (phit?.object.userData.campus) showCampus(phit.object.userData.campus);
    return;
  }
  if (view === 'campus') {
    const phit = ray.intersectObjects(chapterHit, false)[0];
    if (phit?.object.userData.chapters) {
      if (walkActive) plc.unlock();
      return openChapters();
    }
    const chit = ray.intersectObjects(cityHits, false)[0];
    if (chit?.object.userData.poi) {
      if (walkActive) plc.unlock();
      return openCityPoi(chit.object.userData.poi);
    }
    const bhit = ray.intersectObjects(buildings, false)[0];
    if (bhit?.object.userData.slug) showHall(bhit.object.userData.slug);
    return;
  }
  const hit = ray.intersectObjects(beacons, false)[0];
  if (hit?.object.userData.station) {
    if (walkActive) plc.unlock();
    return openStation(hit.object.userData.station);
  }
  if (walkActive) return;
  const fhit = ray.intersectObjects(floors, false)[0];
  if (fhit?.object.userData.room) openRoom(fhit.object.userData.room);
});
let hoverPending = false;
renderer.domElement.addEventListener('pointermove', (e) => {
  if (view === 'hall' || hoverPending) return;
  hoverPending = true;
  requestAnimationFrame(() => {
    hoverPending = false;
    ptr.set(e.clientX/innerWidth*2-1, -(e.clientY/innerHeight)*2+1);
    ray.setFromCamera(ptr, camera);
    if (view === 'campus') {
      const chit = ray.intersectObjects(cityHits, false)[0];
      if (chit?.object.userData.poi) {
        const p = D.geo.cityPois[campusKey].find((x) => x.name === chit.object.userData.poi);
        document.getElementById('hname').textContent = p.name;
        document.getElementById('hfocus').textContent =
          p.km + ' km · RECORDED — ' + (p.blurb || '');
        renderer.domElement.style.cursor = 'pointer';
        return;
      }
      const bhit = ray.intersectObjects(buildings, false)[0];
      if (bhit?.object.userData.slug) {
        const h = D.halls.find(x => x.slug === bhit.object.userData.slug);
        document.getElementById('hname').textContent = h.name;
        document.getElementById('hfocus').textContent = h.focus;
        renderer.domElement.style.cursor = 'pointer';
      } else renderer.domElement.style.cursor = '';
    } else {
      const phit = ray.intersectObjects(plates, false)[0];
      if (phit?.object.userData.campus) {
        const c = D.campuses[phit.object.userData.campus];
        document.getElementById('hname').textContent = c.name;
        document.getElementById('hfocus').textContent =
          c.city + ', ' + c.region + ' — ' + c.tagline;
        renderer.domElement.style.cursor = 'pointer';
      } else renderer.domElement.style.cursor = '';
    }
  });
});
document.addEventListener('click', (e) => {
  if (e.target.closest('#pclose') || e.target.id === 'ov')
    document.body.classList.remove('open');
  const ss = e.target.closest('[data-sim-start]');
  if (ss) {
    document.body.classList.remove('open');
    startSim(ss.dataset.simStart); return;
  }
  if (e.target.id === 'simRetry') {
    document.body.classList.remove('open');
    const id = curSimId; teardownSim(); view = 'hall'; startSim(id); return;
  }
  if (e.target.id === 'simExit') {
    document.body.classList.remove('open'); exitSim(); return;
  }
  const opt = e.target.closest('.opt');
  if (opt) { opt.parentElement.querySelectorAll('.opt').forEach(o =>
      o.classList.toggle('ok', o.dataset.ok === '1'));
    if (opt.dataset.ok !== '1') opt.classList.add('bad');
    else if (curStation) { doneStations.add(curStation); saveProg();
      const el = document.getElementById('hname');
      const h = D.halls.find(x => x.slug === slug);
      if (view === 'hall') el.textContent = h.name + scoreChip(); } }
});
document.getElementById('hall').addEventListener('change', (e) => {
  showHall(e.target.value);
});
document.getElementById('regionBtn').addEventListener('click', showRegion);
document.getElementById('campusBtn').addEventListener('click',
  () => showCampus(campusKey));
document.getElementById('walkBtn').addEventListener('click', enterWalk);
document.getElementById('simBtn').addEventListener('click', () => {
  const b = D.sims.bindings[slug];
  if (!b?.length) return;
  if (b.length === 1) return startSim(b[0].sim);
  // more than one machine trains here: the learner picks the seat
  document.getElementById('pbody').innerHTML = `<h2>${t('sim.choose')}</h2>`
    + b.map((x) => {
      const d = D.sims.sims[x.sim];
      const done = prog.sims[x.sim]?.passed ? ' ✓' : '';
      return `<p><button class="barbtn" data-sim-start="${x.sim}">▶ ${d.name}${done}</button><br>
        <span style="color:var(--muted);font-size:12.5px">${d.task}</span></p>`;
    }).join('');
  document.body.classList.add('open');
});
document.getElementById('lang').addEventListener('change', (e) => {
  loc = e.target.value; renderChrome();
  if (view === 'avatar') showAvatar();
  else if (view === 'region') showRegion();
  else if (view === 'campus') showCampus(campusKey);
  else showHall(slug);
});
function syncURL() {
  history.replaceState(null, '', view === 'region' ? `?lang=${loc}`
    : view === 'campus' ? `?campus=${campusKey}&lang=${loc}`
    : `?hall=${slug}&lang=${loc}`);
}
addEventListener('resize', () => {
  camera.aspect = innerWidth/innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

cfgInit();
renderChrome();
if (D.halls.some(h => h.slug === params.get('hall'))) showHall(params.get('hall'));
else if (D.campuses[params.get('campus')]) showCampus(params.get('campus'));
else showRegion();
// test hook: lets the harness assert scene state without poking internals
window.__tc3d = () => ({ view, buildings: buildings.length, plates: plates.length,
  beacons: beacons.length, floors: floors.length, slug, campusKey, loc, walkActive,
  sim: curSimId && sim ? curSimId : null, roadFaults, roadCount,
  anchors: anchorPins, simCam: simView, audio: !!ac, city: cityPois,
  scenario: curScenario?.id ?? null,
  chHosted: D.chapters.hosted[campusKey] ?? null,
  isTouch, shadows: renderer.shadowMap.enabled,
  avatar: avatarCfg ? { ...avatarCfg } : null, emote: lastEmote,
  wheel: document.querySelectorAll('#wheel path').length,
  progress: { stations: doneStations.size, sims: Object.keys(prog.sims).length },
  dash: document.querySelectorAll('#dash .g').length,
  cam: camera.position.toArray().map((v) => Math.round(v * 10) / 10),
  probe: (() => { const r = new THREE.Raycaster();
    r.setFromCamera(new THREE.Vector2(-.4, .4), camera);
    const h = r.intersectObjects(scene.children, true)[0];
    return h ? [h.object.material?.color?.getHexString?.(),
      Math.round(h.distance * 10) / 10, h.object.geometry?.type] : null; })() });
const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = clock.getDelta();
  if (!reduced) {
    for (const b of beacons) if (b.userData.spin) b.rotation.y += dt * 1.4;
    for (const b of campusSpin) b.rotation.y += dt * 1.1;
  }
  if (sim) {
    sim.update(dt);
    if (sim.gauges) setDash(D.sims.sims[curSimId], sim.gauges());
  }
  stepEmote(dt);
  if (walkActive) (isTouch ? touchWalkStep : walkStep)(dt);
  else controls.update();
  renderer.render(scene, camera);
});
</script>
</body>
</html>
'''

page = page.replace('__DATA__', DATA).replace('__PIPELINE_JS__', PIPELINE_JS)
page = page.replace('__SIM_JS__', SIM_JS)
page = page.replace('__AVATAR_JS__', AVATAR_JS)
out = HERE / 'trade_craft_3d.html'
out.write_text(page)
print(f"written: {len(page):,} bytes | {len(HALLS)} halls | "
      f"{stations_reg['count']} stations | {len(I18N)} locales")
