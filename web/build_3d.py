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
from mapdata import strand_modules, PIPELINE_JS, HUES, make_codes  # noqa: E402

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
parcels_reg = json.load(open(ROOT / 'parcels/registry/parcels.json'))
tools_reg = json.load(open(ROOT / 'tools/registry/toolcribs.json'))
stations_reg = json.load(open(ROOT / 'stations/registry/stations.json'))
agents_reg = json.load(open(ROOT / 'agents/registry/advisors.json'))
training_reg = json.load(open(ROOT / 'training/registry/training.json'))
world_reg = json.load(open(ROOT / 'world/registry/world.json'))
labels_reg = json.load(open(ROOT / 'labels/registry/labels.json'))

def trim(rows, *drop):
    """Ship what is drawn, not what is explained.

    Every registry carries the prose that makes its records checkable by a
    person - what a surface is for, why an animal is in the yard, what a
    sign reads as. None of that is rendered by the page, and a byte
    shipped to every learner should be one they can see, so it is dropped
    on the way in. The registry keeps the whole truth; the wiki prints it.
    """
    if not isinstance(rows, dict):
        return rows
    if rows and all(isinstance(v, dict) for v in rows.values()):
        return {k: {kk: vv for kk, vv in v.items() if kk not in drop}
                for k, v in rows.items()}
    return {k: v for k, v in rows.items() if k not in drop}


yard = json.load(open(ROOT / 'archive/bac_yard_stations.json'))['yard_placements']



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

# Payload dedupe, measured before it was written: labels and purposes are
# one per strand (ROOM_DEFS), room geometry depends only on the envelope
# depth (LAYOUTS), so each hall ships depth + its own fixtures and the
# page inflates rooms at boot. Asserted here, so a plan change that
# breaks the invariant fails the build instead of the page.
ROOM_DEFS, LAY_LIST, LAY_IDX = {}, [], {}
for h in halls_json:
    lay = [{'strand': r['strand'], 'x': r['x'], 'y': r['y'],
            'w': r['w'], 'h': r['h']} for r in plans[h['slug']]['rooms']]
    key = json.dumps(lay, sort_keys=True)
    for i, (k2, _) in enumerate(LAY_LIST):
        if k2 == key:
            LAY_IDX[h['slug']] = i
            break
    else:
        LAY_IDX[h['slug']] = len(LAY_LIST)
        LAY_LIST.append((key, lay))
    for r in plans[h['slug']]['rooms']:
        rd = {'label': r['label'], 'purpose': r['purpose']}
        assert ROOM_DEFS.setdefault(r['strand'], rd) == rd, \
            f"room def diverges for strand {r['strand']}"

HALLS = [{
    'slug': h['slug'], 'name': h['name'], 'focus': h['focus'],
    'index': h['index'], 'district': district_of[h['slug']],
    'fixtures': {r['strand']: r['fixtures']
                 for r in plans[h['slug']]['rooms'] if r['fixtures']},
    'lay': LAY_IDX[h['slug']],
    'depth': plans[h['slug']]['envelope']['d'],
    'stations': stations_by_hall.get(h['slug'], []),
} for h in halls_json]

# finishes collapse the same way: 12 distinct maps across 111 halls
FIN_MAPS, FIN_IDX = [], {}
for sl, h in finishes_reg['halls'].items():
    key = json.dumps(h['rooms'], sort_keys=True)
    for i, (k2, m2) in enumerate(FIN_MAPS):
        if k2 == key:
            FIN_IDX[sl] = i
            break
    else:
        FIN_IDX[sl] = len(FIN_MAPS)
        FIN_MAPS.append((key, h['rooms']))

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
            'city.note', 'avatar.title', 'chapters.hall',
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
    'finMaps': [m for _, m in FIN_MAPS],
    'finIdx': FIN_IDX,
    'roomDefs': ROOM_DEFS,
    'layouts': [lay for _, lay in LAY_LIST],
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
             'honesty': sims_reg['honesty']['status'],
             'walkHonesty': sims_reg['honesty']['walkaround']},
    'imagery': parcels_reg['imagery'],
    'recHonesty': parcels_reg['honesty'],
    # only what the page actually renders: the endpoint, the query template, and the one line of scope text the lookup button shows
    'elevation': trim(parcels_reg['elevation'], 'name', 'authority',
                      'licence', 'cite', 'cite_file', 'provenance',
                      'verified_from_build', 'verification_note',
                      'traps_guarded', 'id'),
    'tools': {'cribs': tools_reg['cribs'], 'drills': tools_reg['drills'],
              'drill': tools_reg['drill'],
              'honesty': tools_reg['honesty']['status']},
    # characters and apes travel as deltas against the locker defaults
    # (the registry keeps the full truth; the page inflates at boot)
    'avatars': {'sections': avatars_reg['sections'],
                'defaults': avatars_reg['defaults'],
                'characters': [
                    {**{k: c[k] for k in ('id', 'name', 'emoji', 'blurb')},
                     'd': {k: v for k, v in c['cfg'].items()
                           if avatars_reg['defaults'].get(k) != v}}
                    for c in avatars_reg['characters']],
                'tradeapes': {
                    **avatars_reg['tradeapes'],
                    'apes': [
                        {'hall': a['hall'], 'code': a['code'],
                         'district': a['district'], 'hue': a['hue'],
                         'd': {k: v for k, v in a['cfg'].items()
                               if k != 'crew'
                               and avatars_reg['defaults'].get(k) != v}}
                        for a in avatars_reg['tradeapes']['apes']]},
                'emotes': avatars_reg['emotes'],
                'guarantee': avatars_reg['guarantee']},
    'chapters': {'of': {slug: c['home']
                        for slug, c in chapters_reg['chapters'].items()},
                 'regions': {k: v['abbr']
                             for k, v in chapters_reg['regions'].items()},
                 'hosted': chapters_reg['hosted'],
                 'honesty': chapters_reg['honesty']['chapters']},
    'strandmods': strand_modules(),
    # the advisors who stand in the rooms: their look, where each one stands,
    # and the fixed list of questions each can answer. A `read` topic carries
    # only a binding - the page resolves it against the record that already
    # holds the fact, so nothing here is a second copy of one
    # the sky, the weather it is seen under, the ground it stands on and
    # the animals moving through it - every texture a recipe, never a file.
    # The page carries only what it RENDERS; the prose that explains each
    # record stays in the registry and reaches people through the wiki,
    # because a byte shipped to every learner should be one they can see
    'world': {'sky': trim(world_reg['sky'], 'note', 'placement', 'projection'),
              'weather': world_reg['weather'],
              'ground': trim(world_reg['ground'], 'where', 'name'),
              'fauna': trim(world_reg['fauna'], 'why', 'name', 'glyph'),
              'atmos': trim(world_reg['atmos'], 'character')},
    # every sign in the world: its shape, its palette, its type and how it
    # reacts to being looked at - again, only the parts that are drawn
    'labels': {'shapes': trim(labels_reg['shapes'], 'draws', 'reads_as'),
               'palette': labels_reg['palette'],
               'type': trim(labels_reg['type'], 'note'),
               'kinds': trim(labels_reg['kinds'], 'what', 'provenance'),
               'focus': trim(labels_reg['focus'], 'contract', 'focus_rule')},
    # the training-data recorder: only what the page needs to build the
    # UI and the export envelope - the essays stay in the registry, read
    # from the wiki, exactly like the world and label packs
    'training': {'storage': training_reg['storage'],
                 'export_format': trim(training_reg['export_format'],
                     'consumer', 'not_a_demo_file', 'no_agent_trained'),
                 'kinds': trim(training_reg['episode_kinds'],
                     'granularity', 'what'),
                 # the two lines actually shown in the records panel;
                 # device-local reuses the existing progress.local i18n
                 # string, and the rest stays registry+wiki only
                 'honesty': {k: training_reg['honesty'][k]
                             for k in ('schematic', 'not_scored')}},
    'advisors': {'who': agents_reg['advisors'],
                 'honesty': agents_reg['honesty'],
                 'walk': geo_reg['walk']},
    'i18n': I18N,
}, ensure_ascii=False, separators=(',', ':'))

SIM_JS = """/* ------------------------------------------------------- simulators ----- */
// Schematic physics for practising control discipline; the graders are
// deterministic - every rubric axis is computed from measured state.
let sim = null, curSimId = null, simView = null, curScenario = null;
let simRider = null;
let waBeacons = [], waDone = new Set(), waTotal = 0;

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
  if (kind === 'arc') {
    // the welding arc: looped noise through a highpass - silent until struck
    const src = ac.createBufferSource(), f = ac.createBiquadFilter(), g = ac.createGain();
    src.buffer = noiseBuf(1.3); src.loop = true;
    f.type = 'highpass'; f.frequency.value = 1500;
    g.gain.value = 0;
    src.connect(f); f.connect(g); g.connect(master); src.start();
    engine = { osc: src, g, kind };
    return;
  }
  const osc = ac.createOscillator(), g = ac.createGain(), f = ac.createBiquadFilter();
  osc.type = kind === 'diesel' ? 'sawtooth' : 'triangle';
  osc.frequency.value = kind === 'diesel' ? 42 : 95;
  f.type = 'lowpass'; f.frequency.value = kind === 'diesel' ? 320 : 900;
  g.gain.value = 0;
  osc.connect(f); f.connect(g); g.connect(master); osc.start();
  engine = { osc, g, kind };
}
function engineSet(load) {  // 0..1 - throttle / hoist activity / arc heat
  if (!engine) return;
  if (engine.kind === 'arc') {
    engine.g.gain.setTargetAtTime(load * .17, ac.currentTime, .03);
    return;
  }
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
    // a sim may declare its own orbit frame (a bench sits closer than a tower)
    const oc = sim?.orbitCam;
    camera.position.set(...(oc?.pos ?? [36, 28, 42]));
    controls.target.set(...(oc?.tgt ?? [0, 11, 0]));
    controls.update();
  }
}

function teardownSim() {
  if (!sim) return;
  scene.remove(sim.group);
  disposeOf(sim.group);
  sim = null; simView = null; curScenario = null; simRider = null;
  waBeacons = []; waDone = new Set(); waTotal = 0;
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
  applyAtmos(campusKey);
  scene.fog.near = 90 * fogMul; scene.fog.far = 260 * fogMul;
  document.getElementById('mm').style.display = 'none';
  document.getElementById('glbBtn').style.display = 'none';
  document.getElementById('glbInBtn').style.display = 'none';
  const def = D.sims.sims[simId];
  // the campus you train at picks the regional scenario; the rubric never varies
  const sc = def.scenarios?.find((s) => s.campus === campusKey)
    ?? def.scenarios?.[0] ?? null;
  curScenario = sc;
  const P = sc?.params ?? {};
  sim = simId === 'crane-lift' ? craneSim(P)
    : simId === 'excavator-trench' ? excavatorSim(P)
    : simId === 'weld-bead' ? weldSim(P)
    : simId === 'scaffold-bay' ? scaffoldSim(P)
    : simId === 'rigging-signals' ? riggingSim(P)
    : simId === 'load-chart' ? loadChartSim(P) : forkliftSim(P);
  scene.add(sim.group);
  // your avatar takes the seat the sim declares - the learner is IN the yard
  if (sim.mount) {
    cfgInit();
    simRider = buildAvatarMesh(avatarCfg);
    simRider.scale.multiplyScalar(.92);
    simRider.position.set(...sim.mount.pos);
    simRider.rotation.y = sim.mount.yaw;
    if (sim.mount.seated) {
      const { arms } = simRider.userData;
      arms.armL.rotation.x = arms.armR.rotation.x = -1.05;
    }
    if (sim.mount.armUp) {
      // the signalperson: one hand high where the operator can read it
      simRider.userData.arms.armR.rotation.x = -2.7;
    }
    sim.mount.parent.add(simRider);
  }
  // the pre-shift walkaround: five clipboards ringing the machine. A
  // habit-builder, not a gate - the registry says so: nothing is locked
  // behind them and marking them changes no score.
  waBeacons = []; waDone = new Set(); waTotal = 0;
  if (def.walkaround) {
    waTotal = def.walkaround.length;
    const wb = new THREE.Box3().setFromObject(sim.group);
    const wr = Math.min(16, Math.max(7,
      Math.max(wb.max.x - wb.min.x, wb.max.z - wb.min.z) / 2 + 3));
    const wcx = (wb.min.x + wb.max.x) / 2, wcz = (wb.min.z + wb.max.z) / 2;
    def.walkaround.forEach((w, i) => {
      const ang = i * Math.PI * 2 / waTotal + .35;
      const px = wcx + Math.cos(ang) * wr, pz = wcz + Math.sin(ang) * wr;
      box(.06, 1.05, .06, mat.part, px, .55, pz, sim.group);
      const clip = box(.36, .46, .05, mat.paint, px, 1.25, pz, sim.group);
      clip.lookAt(wcx, 1.25, wcz);
      clip.userData.wapt = i;
      waBeacons.push(clip);
    });
  }
  controls.autoRotate = false;
  setSimView(def.view_modes[0]);
  acEnsure(); engineStart(def.audio.engine === 'diesel' ? 'diesel'
    : def.audio.engine === 'arc' ? 'arc' : 'hoist');
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
  recordEpisode({ kind: 'sim', campus: campusKey, hall: slug, sim: simId,
    scenario: curScenario?.id ?? null,
    controls: def.controls.map((c) => c.action),
    outcome: { passed, rows } });
  const rec = prog.sims[simId] ?? {};
  rec.runs = (rec.runs ?? 0) + 1;
  if (passed) {
    rec.passed = true;
    const tv = parseFloat(rows.find((r) => r.axis === 'time')?.value);
    if (isFinite(tv)) rec.best = Math.min(rec.best ?? Infinity, tv);
  }
  prog.sims[simId] = rec; saveProg(); renderChrome();
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
    mount: { parent: g, pos: [4.4, 0, 2.6], yaw: -.6 },
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
    const m = new THREE.Mesh(boxGeo(1.8, .1, 1.8),
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
    mount: { parent: g, pos: [3.2, 0, 3.4], yaw: -.7 },
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
    mount: { parent: fl, pos: [0, .58, -.34], yaw: 0, seated: true },
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
}

/* ------------------------------------------------------ weld bead run ---- */
function weldSim(P = {}) {
  const SEGS = P.segs ?? 10, BAND = P.band ?? [2, 5];
  const SEG_W = .45, FUSE = .42, BURN = 1.5, TRAVEL = .5;
  const seamL = SEGS * SEG_W, x0 = -seamL / 2;
  const g = new THREE.Group();
  simYard(g, 16, 12);
  // the bench: two plates meeting at the marked seam, welding screens behind
  const topY = 1.02;
  box(seamL + 1.6, .1, 2.2, mat.steel, 0, topY - .05, 0, g);
  for (const lx of [-seamL / 2 - .5, seamL / 2 + .5])
    for (const lz of [-.8, .8]) box(.14, .95, .14, mat.part, lx, .48, lz, g);
  box(seamL + 1.2, .05, .9, mat.metal, 0, topY + .02, -.6, g);   // plates
  box(seamL + 1.2, .05, .9, mat.metal, 0, topY + .02, .6, g);
  box(seamL, .02, .1, mat.paint, 0, topY + .05, 0, g, false);    // seam mark
  for (const sx of [-seamL / 2 - 2.2, seamL / 2 + 2.2]) {        // screens
    const scr = new THREE.Mesh(boxGeo(.08, 1.9, 3.2),
      new THREE.MeshStandardMaterial({ color: 0x5a3021, roughness: .7,
        transparent: true, opacity: .85 }));
    scr.position.set(sx, 1.3, 0); g.add(scr);
  }
  // the seam, segment by segment: dark until fused, amber in band,
  // pale out of band, a scorched hole where it burned through
  const segs = Array.from({ length: SEGS }, (_, i) => {
    const m = new THREE.Mesh(boxGeo(SEG_W - .04, .05, .16),
      new THREE.MeshStandardMaterial({ color: 0x22282b, roughness: .8 }));
    m.position.set(x0 + (i + .5) * SEG_W, topY + .06, 0); g.add(m);
    return { x: x0 + (i + .5) * SEG_W, heat: 0, good: 0,
             fused: false, burned: false, inBand: null, mesh: m };
  });
  // the torch, and the arc that lives under it
  const torch = new THREE.Group(); g.add(torch);
  const noz = new THREE.Mesh(new THREE.CylinderGeometry(.05, .08, .5, 10), mat.part);
  noz.rotation.z = .5; noz.position.y = .3; torch.add(noz);
  box(.07, .3, .07, mat.post, .22, .62, 0, torch, false);
  const arcGlow = new THREE.Mesh(new THREE.SphereGeometry(.09, 10, 10),
    new THREE.MeshStandardMaterial({ color: 0xffffff,
      emissive: 0xbfe8ff, emissiveIntensity: 2.4 }));
  arcGlow.visible = false; torch.add(arcGlow);
  const st = { x: x0 - .3, gap: 3.5, arc: false, done: false,
               burns: 0, t0: null };
  const segAt = () => {
    const i = Math.floor((st.x - x0) / SEG_W);
    return i >= 0 && i < SEGS ? segs[i] : null;
  };
  const inBand = () => st.gap >= BAND[0] && st.gap <= BAND[1];
  function paint(s) {
    s.mesh.material.color.setHex(
      s.burned ? 0x0c0e0f : s.inBand ? 0xE8A33D : 0xb9c2c6);
    if (s.burned) s.mesh.scale.y = .4;
  }
  function bandPct() {
    const fused = segs.filter((s) => s.fused);
    return fused.length
      ? Math.round(100 * fused.filter((s) => s.inBand).length / fused.length) : 0;
  }
  function finish() {
    st.done = true; st.arc = false; arcGlow.visible = false; engineSet(0);
    const fused = segs.filter((s) => s.fused).length;
    const pct = bandPct();
    const time = st.t0 ? ((performance.now() - st.t0) / 1000) : 0;
    const rows = [
      { axis: 'fusion', value: fused + '/' + SEGS, ok: fused === SEGS },
      { axis: 'band', value: pct + '%', ok: pct >= 90 },
      { axis: 'burns', value: String(st.burns), ok: st.burns === 0 },
      { axis: 'time', value: time.toFixed(1) + ' s', ok: null },
    ];
    simResults('weld-bead', rows, fused === SEGS && pct >= 90 && st.burns === 0);
  }
  return {
    group: g, orbit: true,
    orbitCam: { pos: [5.5, 4.5, 8], tgt: [0, 1, 0] },
    mount: { parent: g, pos: [-1.4, 0, 1.7], yaw: Math.PI },
    action() {
      if (st.done) return;
      if (!st.arc) {
        if (st.gap <= 6) {
          st.arc = true;
          if (!st.t0) st.t0 = performance.now();
          blip(1400, 2600, .12, 'square', .08);           // strike
        }
      } else { st.arc = false; blip(900, 300, .1, 'square', .05); }
    },
    update(dt) {
      if (st.done) return;
      if (keys.KeyW) st.x = Math.min(x0 + seamL + .4, st.x + TRAVEL * dt);
      if (keys.KeyS) st.x = Math.max(x0 - .4, st.x - TRAVEL * dt);
      if (keys.KeyQ) st.gap = Math.min(7.5, st.gap + 4 * dt);
      if (keys.KeyE) st.gap = Math.max(.5, st.gap - 4 * dt);
      if (st.arc && st.gap > 6.2) {                       // too long: the arc pops out
        st.arc = false; blip(2200, 400, .2, 'square', .1);
      }
      const s = st.arc ? segAt() : null;
      if (s && !s.burned) {
        s.heat += dt;
        if (inBand()) s.good += dt;
        if (!s.fused && s.heat >= FUSE) {
          s.fused = true; s.inBand = s.good / s.heat >= .75; paint(s);
          if (segs.every((x) => x.fused || x.burned)) return finish();
        }
        if (s.heat >= BURN) {                             // lingered: burn-through
          s.burned = true; s.fused = false; s.inBand = null; st.burns++;
          paint(s); blip(240, 60, .5, 'sawtooth', .22); buzz(300, .9);
          if (segs.every((x) => x.fused || x.burned)) return finish();
        }
      }
      torch.position.set(st.x, topY + .12 + st.gap * .022, 0);
      arcGlow.visible = st.arc;
      if (st.arc) arcGlow.scale.setScalar(.8 + .5 * Math.abs(Math.sin(performance.now() / 37)));
      arcGlow.position.y = -.02 - st.gap * .02;
      engineSet(st.arc ? .55 + .25 * Math.random() : 0);  // crackle drive (audio only)
      if (simView === 'visor') {
        camera.position.set(st.x - .7, topY + 1.15, 1.45);
        camera.lookAt(st.x + .2, topY + .05, 0);
      }
    },
    gauges: () => {
      const s = segAt();
      return {
        gap: st.gap,
        heat: Math.min(100, ((s && !s.burned ? s.heat : 0) / BURN) * 100),
        seam: { v: 0, txt: segs.filter((x) => x.fused).length + '/' + SEGS },
        band: { v: 0, txt: bandPct() + '%' },
        burns: { v: st.burns, txt: String(st.burns) },
        time: { v: 0, txt: st.t0 ? ((performance.now() - st.t0) / 1000).toFixed(0) : '\\u2013' },
      };
    },
  };
}

/* --------------------------------------------------- scaffold bay build --- */
function scaffoldSim(P = {}) {
  const PLANKS = P.planks ?? 3, RAILS = P.rails ?? 2;
  const g = new THREE.Group();
  simYard(g, 13, 10);
  const railMat = new THREE.MeshStandardMaterial({ color: 0xd8a13a, roughness: .5 });
  const alu = new THREE.MeshStandardMaterial({ color: 0xa8b4b8,
    roughness: .45, metalness: .5 });
  const mk = (geo, m, x, y, z) => {
    const mesh = new THREE.Mesh(geo, m);
    mesh.position.set(x, y, z); mesh.castShadow = true;
    mesh.visible = false; g.add(mesh);
    return mesh;
  };
  // the bay's parts, all prebuilt and hidden - placing a part reveals it.
  // STAGE LAW: sills, frames, braces, planks, then rails, and the rack
  // refuses anything out of order.
  const parts = [];
  for (const [sx, sz] of [[-1.6, -.75], [-1.6, .75], [1.6, -.75], [1.6, .75]])
    parts.push({ stage: 0,
      mesh: mk(boxGeo(.5, .1, .5), mat.wood, sx, .1, sz) });
  for (const fx of [-1.6, 1.6]) {
    const fg = new THREE.Group(); fg.position.set(fx, 0, 0);
    fg.visible = false; g.add(fg);
    for (const pz of [-.75, .75]) {
      const post = new THREE.Mesh(new THREE.CylinderGeometry(.05, .05, 2.3, 8), alu);
      post.position.set(0, 1.3, pz); post.castShadow = true; fg.add(post);
    }
    for (const ry of [.6, 2]) {
      const rung = new THREE.Mesh(new THREE.CylinderGeometry(.04, .04, 1.5, 8), alu);
      rung.rotation.x = Math.PI / 2; rung.position.set(0, ry, 0); fg.add(rung);
    }
    parts.push({ stage: 1, mesh: fg });
  }
  for (const bz of [-.8, .8]) {
    const br = new THREE.Mesh(new THREE.CylinderGeometry(.035, .035, 3.7, 8), alu);
    br.rotation.z = Math.PI / 2 - .55; br.position.set(0, 1.3, bz);
    br.castShadow = true; br.visible = false; g.add(br);
    parts.push({ stage: 2, mesh: br });
  }
  for (let i = 0; i < PLANKS; i++) {
    const pz = -((PLANKS - 1) / 2) * .55 + i * .55;
    parts.push({ stage: 3,
      mesh: mk(boxGeo(3.4, .08, .5), mat.wood, 0, 2.14, pz) });
  }
  for (let i = 0; i < RAILS; i++) {
    const side = i % 2 ? .85 : -.85, ry = 2.65 + Math.floor(i / 2) * .4;
    parts.push({ stage: 4,
      mesh: mk(boxGeo(3.4, .07, .07), railMat, 0, ry, side) });
  }
  const STAGES = ['sills', 'frames', 'braces', 'planks', 'rails'];
  // the ghost previews where the selected rack's next part will land
  const ghost = new THREE.Mesh(boxGeo(1, 1, 1),
    new THREE.MeshBasicMaterial({ color: 0x41C4D4, transparent: true,
      opacity: .28, depthWrite: false }));
  ghost.visible = false; g.add(ghost);
  const gBox = new THREE.Box3(), gSize = new THREE.Vector3(), gMid = new THREE.Vector3();
  const st = { rack: 0, faults: 0, t0: null, done: false, la: false, ld: false, lr: false };
  const nextOf = (stage) => parts.find((p) => p.stage === stage && !p.mesh.visible);
  const legal = () => { for (let i = 0; i < 5; i++) if (nextOf(i)) return i; return -1; };
  function finish() {
    st.done = true; ghost.visible = false;
    const time = st.t0 ? ((performance.now() - st.t0) / 1000) : 0;
    const rows = [
      { axis: 'sequence', value: String(st.faults), ok: st.faults === 0 },
      { axis: 'complete', value: parts.length + '/' + parts.length, ok: true },
      { axis: 'time', value: time.toFixed(1) + ' s', ok: null },
    ];
    simResults('scaffold-bay', rows, st.faults === 0);
  }
  return {
    group: g, orbit: true,
    orbitCam: { pos: [6, 4.5, 8.5], tgt: [0, 1.6, 0] },
    mount: { parent: g, pos: [2.4, 0, 1.8], yaw: -2.4 },
    action() {
      if (st.done) return;
      const lg = legal();
      if (lg < 0) return;
      if (st.rack !== lg) {                       // out of order: refused
        st.faults++;
        blip(150, 75, .32, 'square', .18); buzz(220, .8);
        return;
      }
      const p = nextOf(lg);
      p.mesh.visible = true;
      if (!st.t0) st.t0 = performance.now();
      blip(1250, 720, .07, 'triangle', .1);       // lock click
      if (!parts.some((x) => !x.mesh.visible)) finish();
    },
    update(dt) {
      if (st.done) return;
      // rack selection steps on the key edge, not the hold
      if (keys.KeyA && !st.la) st.rack = (st.rack + 4) % 5;
      if (keys.KeyD && !st.ld) st.rack = (st.rack + 1) % 5;
      if (keys.KeyR && !st.lr && legal() >= 0) st.rack = legal();
      st.la = !!keys.KeyA; st.ld = !!keys.KeyD; st.lr = !!keys.KeyR;
      engineSet(.06);
      const nx = nextOf(st.rack);
      if (nx) {
        gBox.setFromObject(nx.mesh);
        gBox.getSize(gSize); gBox.getCenter(gMid);
        ghost.position.copy(gMid);
        ghost.scale.set(Math.max(.12, gSize.x), Math.max(.12, gSize.y),
          Math.max(.12, gSize.z));
        ghost.visible = true;
      } else ghost.visible = false;
      if (simView === 'deck') {
        camera.position.set(2.7, 3.05, 0);
        camera.lookAt(-1.6, 2.1, 0);
      }
    },
    gauges: () => ({
      rack: { v: 0, txt: STAGES[st.rack] },
      stage: { v: 0, txt: legal() < 0 ? '\\u2013' : STAGES[legal()] },
      placed: { v: 0, txt: parts.filter((p) => p.mesh.visible).length + '/' + parts.length },
      faults: { v: st.faults, txt: String(st.faults) },
      time: { v: 0, txt: st.t0 ? ((performance.now() - st.t0) / 1000).toFixed(0) : '\\u2013' },
    }),
  };
}

/* ------------------------------------------------- rigging signal call --- */
function riggingSim(P = {}) {
  const SEQ = P.seq ?? ['up', 'swing-r', 'out', 'down', 'stop'];
  const g = new THREE.Group();
  simYard(g, 18, 14);
  // a yard derrick: mast, slewing boom, trolley line, hook and load -
  // it moves ONLY on a correct call from the signalperson
  const MAST = 9;
  box(.8, MAST, .8, mat.metal, -4, MAST / 2, -3, g);
  const slewG = new THREE.Group(); slewG.position.set(-4, MAST, -3); g.add(slewG);
  box(10, .5, .6, mat.post, 5, 0, 0, slewG);
  box(3, .5, .6, mat.metal, -1.5, 0, 0, slewG);
  const cableGeo = new THREE.BufferGeometry().setFromPoints(
    [new THREE.Vector3(), new THREE.Vector3()]);
  g.add(new THREE.Line(cableGeo, new THREE.LineBasicMaterial({ color: 0xd8dde0 })));
  const load = box(1.6, 1.2, 1.6, mat.brick, 0, .6, 0, g);
  // the signal pad, painted where the operator can see the hands
  const pad = new THREE.Mesh(new THREE.CylinderGeometry(1.1, 1.1, .08, 24),
    new THREE.MeshBasicMaterial({ color: 0xE8A33D, transparent: true, opacity: .35 }));
  pad.position.set(4.5, .06, 6.2); g.add(pad);
  const st = { i: 0, wrong: 0, t0: null, done: false, given: '\\u2013',
               slew: .55, r: 5.5, h: 3.2, latch: {},
               tgt: null };
  const hookPos = () => {
    const tip = slewG.localToWorld(new THREE.Vector3(st.r, 0, 0));
    return new THREE.Vector3(tip.x, st.h, tip.z);
  };
  function finish() {
    st.done = true;
    const time = st.t0 ? ((performance.now() - st.t0) / 1000) : 0;
    const rows = [
      { axis: 'calls', value: st.i + '/' + SEQ.length, ok: st.i === SEQ.length },
      { axis: 'wrong', value: String(st.wrong), ok: st.wrong === 0 },
      { axis: 'time', value: time.toFixed(1) + ' s', ok: null },
    ];
    simResults('rigging-signals', rows, st.i === SEQ.length && st.wrong === 0);
  }
  function give(sig) {
    if (st.done || st.tgt) return;         // the crane is still moving: hold
    st.given = sig;
    if (sig === SEQ[st.i]) {
      if (!st.t0) st.t0 = performance.now();
      blip(1450, 1900, .1, 'sine', .12);   // the whistle: call acknowledged
      setTimeout(() => blip(1450, 1900, .1, 'sine', .12), 140);
      st.i++;
      if (sig === 'stop') return finish();
      st.tgt = {
        'up': { h: st.h + 2.4 }, 'down': { h: Math.max(1.2, st.h - 2.4) },
        'swing-l': { slew: st.slew - .55 }, 'swing-r': { slew: st.slew + .55 },
        'out': { r: Math.min(9, st.r + 2.2) }, 'in': { r: Math.max(2.5, st.r - 2.2) },
      }[sig];
    } else {                               // out of turn: the crane holds
      st.wrong++;
      blip(220, 110, .35, 'square', .16); buzz(200, .7);
    }
  }
  return {
    group: g, orbit: true,
    orbitCam: { pos: [12, 9, 15], tgt: [0, 4, 0] },
    mount: { parent: g, pos: [4.5, .1, 6.2], yaw: -2.55, armUp: true },
    action() { give('stop'); },
    update(dt) {
      if (!st.done) {
        const SIGS = { KeyQ: 'up', KeyE: 'down', KeyA: 'swing-l',
                       KeyD: 'swing-r', KeyW: 'out', KeyS: 'in' };
        for (const [k, sig] of Object.entries(SIGS)) {
          if (keys[k] && !st.latch[k]) give(sig);
          st.latch[k] = !!keys[k];
        }
        if (st.tgt) {                      // one smooth move per call
          let close = true;
          for (const [prop, want] of Object.entries(st.tgt)) {
            st[prop] += (want - st[prop]) * Math.min(1, 3.2 * dt);
            if (Math.abs(want - st[prop]) > .04) close = false;
          }
          if (close) { Object.assign(st, st.tgt); st.tgt = null; }
        }
        engineSet(st.tgt ? .6 : .12);
      }
      slewG.rotation.y = -st.slew;
      const hp = hookPos();
      load.position.set(hp.x, Math.max(.6, hp.y - 1.4), hp.z);
      const pts = cableGeo.attributes.position.array;
      const tip = slewG.localToWorld(new THREE.Vector3(st.r, 0, 0));
      pts[0] = tip.x; pts[1] = tip.y; pts[2] = tip.z;
      pts[3] = load.position.x; pts[4] = load.position.y + .6; pts[5] = load.position.z;
      cableGeo.attributes.position.needsUpdate = true;
      if (simView === 'signal') {
        // the signalperson's eye: on the pad, watching the load
        camera.position.set(4.5, 1.75, 7.1);
        camera.lookAt(load.position.x, load.position.y + 1, load.position.z);
      }
    },
    gauges: () => ({
      step: { v: 0, txt: st.i + '/' + SEQ.length },
      called: { v: 0, txt: st.done ? '\\u2013' : (SEQ[st.i] ?? '\\u2013') },
      given: { v: 0, txt: st.given },
      wrong: { v: st.wrong, txt: String(st.wrong) },
      time: { v: 0, txt: st.t0 ? ((performance.now() - st.t0) / 1000).toFixed(0) : '\\u2013' },
    }),
  };
}

/* ------------------------------------------------- load chart judgment --- */
function loadChartSim(P = {}) {
  const CHART = D.sims.sims['load-chart'].chart;
  const cap = Object.fromEntries(CHART);
  const PICKS = P.picks ?? [{ w: 3, r: 4 }, { w: 4.8, r: 6 }, { w: 4.1, r: 8 }];
  const g = new THREE.Group();
  simYard(g, 18, 14);
  // the crane whose chart it is: mast and a fixed boom over the pick line
  const MAST = 9;
  box(.8, MAST, .8, mat.metal, -6, MAST / 2, -4, g);
  box(14, .5, .6, mat.post, 1, MAST, -4, g);
  // the pick line: a painted tick at every chart radius
  for (const [r] of CHART) {
    box(.18, .04, 1.2, mat.paint, -6 + r, .06, -4, g, false);
  }
  // the chart board - one honest number per radius, drawn as data
  const cc = document.createElement('canvas'); cc.width = 256; cc.height = 320;
  const cx2 = cc.getContext('2d');
  const ctex = new THREE.CanvasTexture(cc);
  function drawChart(hi) {
    cx2.fillStyle = '#0C1113'; cx2.fillRect(0, 0, 256, 320);
    cx2.strokeStyle = '#E8A33D'; cx2.lineWidth = 6; cx2.strokeRect(3, 3, 250, 314);
    cx2.fillStyle = '#E8EDEC'; cx2.font = '700 30px "Barlow Condensed", sans-serif';
    cx2.fillText('LOAD CHART', 42, 44);
    cx2.font = '26px "IBM Plex Mono", monospace';
    CHART.forEach(([r, t2], i) => {
      const y = 92 + i * 44;
      if (i === hi) { cx2.fillStyle = 'rgba(232,163,61,.28)'; cx2.fillRect(10, y - 30, 236, 40); }
      cx2.fillStyle = i === hi ? '#E8A33D' : '#93A3A6';
      cx2.fillText(String(r).padStart(2) + ' m', 26, y);
      cx2.fillStyle = '#E8EDEC';
      cx2.fillText(t2.toFixed(1) + ' t', 140, y);
    });
    ctex.needsUpdate = true;
  }
  drawChart(-1);
  const board = new THREE.Mesh(new THREE.PlaneGeometry(2.6, 3.25),
    new THREE.MeshBasicMaterial({ map: ctex }));
  board.position.set(4, 2.1, 3); board.rotation.y = -.5; g.add(board);
  box(.14, 2.2, .14, mat.part, 3.2, 1.1, 3.4, g);
  box(.14, 2.2, .14, mat.part, 4.8, 1.1, 2.6, g);
  const st = { i: 0, errs: 0, over: 0, t0: null, done: false, hi: -1,
               lq: false, le: false, lx: false };
  let loadMesh = null, loadLab = null;
  const anims = [];
  function spawn() {
    if (st.done) return;
    if (st.i >= PICKS.length) return finish();
    const p = PICKS[st.i];
    const s2 = .7 + p.w * .13;
    loadMesh = box(s2, s2 * .8, s2, mat.brick, -6 + p.r, s2 * .4, -4, g);
    loadLab = label(p.w.toFixed(1) + ' t', p.r + ' m radius', .55,
      { kind: 'readout' });
    loadLab.position.set(-6 + p.r, s2 * .8 + 1.2, -4); g.add(loadLab);
  }
  spawn();
  function finish() {
    st.done = true;
    const time = st.t0 ? ((performance.now() - st.t0) / 1000) : 0;
    const rows = [
      { axis: 'judgments', value: (PICKS.length - st.errs) + '/' + PICKS.length,
        ok: st.errs === 0 },
      { axis: 'overloads', value: String(st.over), ok: st.over === 0 },
      { axis: 'time', value: time.toFixed(1) + ' s', ok: null },
    ];
    simResults('load-chart', rows, st.errs === 0);
  }
  function judge(accept) {
    if (st.done || !loadMesh) return;
    const p = PICKS[st.i];
    const legal = p.w <= cap[p.r];
    if (!st.t0) st.t0 = performance.now();
    const m = loadMesh, lb = loadLab;
    loadMesh = null; loadLab = null;
    if (accept === legal) {
      if (accept) { blip(1100, 1500, .12, 'triangle', .12); anims.push({ m, lb, up: true }); }
      else { blip(700, 500, .15, 'triangle', .1); anims.push({ m, lb, up: false }); }
    } else {
      st.errs++;
      anims.push({ m, lb, up: false });
      if (accept) {                          // an overweight pick accepted
        st.over++;
        blip(240, 90, .6, 'sawtooth', .22); buzz(320, .9);
      } else { blip(300, 200, .3, 'square', .12); buzz(120, .4); }
    }
    st.i++;
    setTimeout(spawn, 650);
  }
  return {
    group: g, orbit: true,
    orbitCam: { pos: [10, 7, 13], tgt: [0, 2.5, 0] },
    mount: { parent: g, pos: [2.4, 0, 4.6], yaw: 2.5 },
    action() { judge(true); },
    update(dt) {
      if (!st.done) {
        if (keys.KeyX && !st.lx) judge(false);
        st.lx = !!keys.KeyX;
        if (keys.KeyQ && !st.lq) { st.hi = (st.hi + CHART.length) % CHART.length; drawChart(st.hi); }
        if (keys.KeyE && !st.le) { st.hi = (st.hi + 1) % CHART.length; drawChart(st.hi); }
        st.lq = !!keys.KeyQ; st.le = !!keys.KeyE;
        engineSet(anims.some((a) => a.up) ? .5 : .1);
      }
      for (let i = anims.length - 1; i >= 0; i--) {
        const a = anims[i];
        if (a.up) a.m.position.y += 2.6 * dt;
        else a.m.position.z -= 2.6 * dt;
        a.lb.position.copy(a.m.position).y += 1.4;
        if (a.m.position.y > 6.5 || a.m.position.z < -9) {
          g.remove(a.m); g.remove(a.lb); anims.splice(i, 1);
        }
      }
      if (simView === 'chart') {
        camera.position.set(2.7, 2.15, 4.9);
        camera.lookAt(board.position.x, board.position.y, board.position.z);
      }
    },
    gauges: () => {
      const p = PICKS[Math.min(st.i, PICKS.length - 1)];
      return {
        pick: { v: 0, txt: Math.min(st.i, PICKS.length) + '/' + PICKS.length },
        load: p.w,
        radius: p.r,
        chart: cap[p.r],
        errors: { v: st.errs, txt: String(st.errs) },
        time: { v: 0, txt: st.t0 ? ((performance.now() - st.t0) / 1000).toFixed(0) : '\\u2013' },
      };
    },
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
let crewDistrict = null;              // the crew wheel's first level

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

/* The humanoid: capsule body, real facial features, hair by style, the
   full wardrobe, and the crew mark - the hall's three-letter code on a
   shield in its district hue - stamped on vest, shirt and headwear.
   Parts are named for the emote moves: shoulders pivot, the hat lifts,
   the whole body spins or hops. The marks are the Academy's own insignia
   (the registry says so); no real union's logo is drawn. */
const crewTexCache = {};
function crewMarkTex(crewId) {
  if (crewTexCache[crewId]) return crewTexCache[crewId];
  const o = D.avatars.sections.find((s) => s.kind === 'crew')
    .options.find((x) => x.id === crewId);
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const g2 = c.getContext('2d');
  g2.clearRect(0, 0, 128, 128);
  const hue = o?.hue ?? 40;
  // the shield
  g2.beginPath();
  g2.moveTo(14, 18); g2.lineTo(114, 18); g2.lineTo(114, 72);
  g2.quadraticCurveTo(114, 104, 64, 122);
  g2.quadraticCurveTo(14, 104, 14, 72); g2.closePath();
  g2.fillStyle = `hsl(${hue},52%,36%)`; g2.fill();
  g2.lineWidth = 6; g2.strokeStyle = `hsl(${hue},60%,68%)`; g2.stroke();
  g2.fillStyle = '#f2f4f2';
  g2.font = '700 44px "Barlow Condensed", system-ui, sans-serif';
  g2.textAlign = 'center'; g2.textBaseline = 'middle';
  g2.fillText(o?.glyph ?? '', 64, 62);
  g2.font = '600 15px "IBM Plex Sans", sans-serif';
  g2.fillText('TCA', 64, 96);
  const tex = new THREE.CanvasTexture(c);
  crewTexCache[crewId] = tex;
  return tex;
}
function markPlane(w, h, crewId) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h),
    new THREE.MeshBasicMaterial({ map: crewMarkTex(crewId), transparent: true }));
  return m;
}

function capsule(r, len, m, x, y, z, parent) {
  const c = new THREE.Mesh(new THREE.CapsuleGeometry(r, len, 4, 10), m);
  c.position.set(x, y, z); c.castShadow = true; parent.add(c);
  return c;
}
function sphere(r, m, x, y, z, parent, sx = 1, sy = 1, sz = 1) {
  const o = new THREE.Mesh(new THREE.SphereGeometry(r, 18, 14), m);
  o.position.set(x, y, z); o.scale.set(sx, sy, sz);
  o.castShadow = true; parent.add(o);
  return o;
}

function buildAvatarMesh(cfg) {
  const g = new THREE.Group();
  const M = (hex, rough = .8) => new THREE.MeshStandardMaterial({
    color: hex, roughness: rough });
  const skin = M(optOf('skin').value, .65);
  const hairM = M(optOf('haircolor').value, .85);
  const eyeM = M(optOf('eyes').value, .3);
  const topM = M(optOf('topcolor').value, .85);
  const pantsM = M(optOf('pantscolor').value, .9);
  const hatM = M(optOf('headcolor').value, .5);
  const hiviz = new THREE.MeshStandardMaterial({
    color: 0xd9c22e, emissive: 0x4a4208, roughness: .6 });
  const reflect = new THREE.MeshStandardMaterial({
    color: 0xe8ecec, emissive: 0x555b5b, roughness: .35 });
  const dark = M('#26262a', .85);
  const shoeHex = { 'steel-toe-brown': '#6a4a2a', 'steel-toe-black': '#26262a',
    'steel-toe-tan': '#a5793f', 'comp-toe-grey': '#6c7276', logger: '#4a3320',
    wellington: '#2e4d3a', hiker: '#7a5a34', 'rubber-yellow': '#d9c22e',
    'rubber-green': '#3c6b45', 'sneaker-white': '#e6e6e2',
    'sneaker-black': '#26262a', 'sneaker-red': '#a03a34',
    'sneaker-blue': '#2f4d8a', 'high-top': '#33363a', 'slip-on': '#5d4127',
    lineman: '#3a2a1c' }[cfg.shoes] ?? '#6a4a2a';
  const shoeM = M(shoeHex, .7);
  const crewId = cfg.crew;

  // costume recipes: a themed re-dress plus a few props; the everyday
  // locker stays stored untouched underneath (costume 'none')
  let CS = {
    krewe: { top: '#5a2d82', pants: '#2f6b45', hat: '#c9a227', noVest: true },
    foundry: { top: '#9aa1a6', pants: '#7d848a', hat: '#b9bcbe',
      metal: true, noVest: true },
    diver: { top: '#274a52', pants: '#274a52', hat: '#8a6a2a', noVest: true },
    'vintage-33': { top: '#8a7f6a', pants: '#5b5244', hat: '#4a4238',
      noVest: true },
    'storm-rider': { top: '#2e4d3a', pants: '#2e4d3a', hat: '#d9c22e' },
    'gold-journey': { top: '#c9a227', pants: '#8a6a1e', hat: '#c9a227',
      metal: true, noVest: true },
    hazmat: { top: '#e3dc9a', pants: '#e3dc9a', hat: '#e3dc9a', noVest: true },
    'arc-guard': { top: '#6c7276', pants: '#6c7276', hat: '#33363a',
      noVest: true },
    tunnel: { top: '#e8722a', pants: '#e8722a', hat: '#d9c22e' },
    parade: { top: '#e6e6e2', pants: '#e6e6e2', hat: '#2c3e5a', noVest: true },
    'night-reflective': { top: '#33363a', pants: '#33363a', hat: '#33363a' },
    mascot: { top: '#2f4d8a', pants: '#d9c22e', hat: '#e8722a' },
    frost: { top: '#bcd4e6', pants: '#9cb8cc', hat: '#e6eef4', noVest: true },
    gala: { top: '#1d1f24', pants: '#1d1f24', hat: '#1d1f24', noVest: true },
    'ape-mascot': { top: '#3a2f28', pants: '#3a2f28', hat: '#3a2f28' },
    'pelican-mascot': { top: '#e8e6de', pants: '#e8e6de', hat: '#e8e6de' },
    'bear-mascot': { top: '#5d4127', pants: '#5d4127', hat: '#5d4127' },
    'gator-mascot': { top: '#3c6b45', pants: '#3c6b45', hat: '#3c6b45' },
    'ox-mascot': { top: '#6b5341', pants: '#6b5341', hat: '#6b5341' },
  }[cfg.costume];
  // an animal mascot costume swaps the whole head for an original
  // Academy animal; its fur takes the topcolor pick, so the TradeApes
  // (and any dressed mascot) vary coat by coat
  const ANIMAL = /-mascot$/.test(cfg.costume) ? cfg.costume : null;
  if (ANIMAL) CS = { ...CS, top: optOf('topcolor').value,
    pants: optOf('topcolor').value };
  // the ape is a TRUE ape, proportioned to the measured reference in the
  // registry (span ~ height, deep hunch): long arms, wide shoulders,
  // heavy haunches, low-poly flat shading
  const APE = ANIMAL === 'ape-mascot';
  const APR = D.avatars.tradeapes.ape_reference;
  const APE_ARM = 1.12, APE_SHX = 1.06;
  if (CS) {
    topM.color.set(CS.top); pantsM.color.set(CS.pants); hatM.color.set(CS.hat);
    if (CS.metal) { topM.metalness = .55; topM.roughness = .35; }
  } else {
    if (cfg.pants === 'painter-white') pantsM.color.set('#e6e6e2');
    if (cfg.top === 'hi-vis-tee') { topM.color.set('#d9c22e'); topM.emissive.set('#4a4208'); }
    if (cfg.top === 'rain-shell') topM.roughness = .3;
  }
  const vestOn = cfg.vest !== 'none' && !CS?.noVest;

  const shorts = cfg.pants === 'shorts';
  const coveralls = cfg.top === 'coveralls';
  const legM = coveralls ? topM : pantsM;

  // legs: thigh + calf capsules, then footwear with real silhouettes -
  // shafts on the boots, soles and laces on the sneakers
  const SHAFT = { wellington: .3, 'rubber-yellow': .3, 'rubber-green': .3,
    lineman: .24, logger: .2, 'high-top': .15, hiker: .13 }[cfg.shoes] ?? 0;
  const SOLED = /sneaker|high-top|hiker/.test(cfg.shoes);
  const LACED = /sneaker|high-top|hiker|steel|comp|logger|lineman/.test(cfg.shoes);
  /* ---------------------------------------------------- the skeleton ---
     A real VRM / Unity humanoid bone hierarchy (vrm-c/UniVRM, MIT): every
     bone below is an actual transform node, nested as the spec nests them,
     and the geometry hangs off the bone it belongs to. That buys three
     things at once - elbows and knees that bend, a walk cycle that reads
     as walking, and an export a Unity Humanoid or VRM importer maps whole
     instead of in part. Rest-pose world heights are unchanged, so every
     capsule sits exactly where it always did. */
  const bone = (name, parent, x, y, z) => {
    const b = new THREE.Group();
    b.name = name; b.position.set(x, y, z); parent.add(b);
    return b;
  };
  const hips = bone('hips', g, 0, .95, 0);
  const spine = bone('spine', hips, 0, .15, 0);          // world 1.10
  const chest = bone('chest', spine, 0, .25, 0);         // world 1.35
  const neck = bone('neck', chest, 0, .22, 0);           // world 1.57
  const bones = { hips, spine, chest, neck };   // head joins below
  for (const [side, sx] of [['left', -1], ['right', 1]]) {
    const up = bone(side + 'UpperLeg', hips, sx * .13, -.13, 0);   // world .82
    const lo = bone(side + 'LowerLeg', up, 0, -.40, 0);            // world .42
    const ft = bone(side + 'Foot', lo, 0, -.32, 0);                // world .10
    bones[side + 'UpperLeg'] = up;
    bones[side + 'LowerLeg'] = lo;
    bones[side + 'Foot'] = ft;
    capsule(.095, .3, legM, 0, 0, 0, up);
    capsule(.08, .26, shorts ? skin : legM, 0, 0, 0, lo);
    if (SHAFT) box(.155, SHAFT, .18, shoeM, 0, .03 + SHAFT / 2, -.01, ft);
    const b = box(.17, .13, .3, shoeM, 0, 0, .03, ft);
    sphere(.085, shoeM, 0, -.01, .17, ft, 1, .8, 1);
    if (SOLED) box(.18, .035, .33, M('#e6e6e2', .6), 0, -.072, .03, ft, false);
    if (LACED) box(.1, .022, .07, dark, 0, .058, .1, ft, false);
    b.castShadow = true;
    // trouser details ride the bone whose limb they belong to
    if (cfg.pants === 'cargo') box(.05, .13, .16, pantsM, sx * .055, -.02, 0, up, false);
    if (cfg.pants === 'hi-vis') box(.16, .05, .21, reflect, 0, .08, 0, lo, false);
    if (cfg.pants === 'fr-pants') box(.165, .04, .21, M('#33363a', .8), 0, -.10, 0, lo, false);
    if (cfg.extras === 'knee-pads') box(.14, .12, .1, dark, 0, .18, .09, lo, false);
  }
  if (cfg.pants === 'carpenter')
    box(.03, .15, .05, pantsM, .215, .88, .02, g, false);   // the hammer loop
  // hips and torso
  box(.4, .16, .26, coveralls ? topM : pantsM, 0, 1.0, 0, g);
  capsule(.2, .38, topM, 0, 1.32, 0, g);
  if (APE) {
    const furB = new THREE.MeshStandardMaterial({
      color: CS.top, roughness: .95, flatShading: true });
    capsule(.235, .28, furB, 0, 1.28, .04, g);           // barrel chest
    sphere(.19, furB, 0, 1.02, .05, g, 1, .85, 1);       // the belly
    for (const sx of [-1, 1])
      sphere(.135, furB, sx * .17, .78, .02, g, 1, 1.1, 1);  // haunches
    // span/height ratio, recorded for the harness to hold against the
    // registry's measured reference
    g.userData.apeSpanRatio =
      (2 * .3 * APE_SHX + 2 * .64 * APE_ARM + .12) / 1.93;
  }
  if (cfg.top === 'flannel' || cfg.top === 'work-shirt') {
    box(.05, .5, .27, M('#2a2523', .9), 0, 1.32, 0, g);   // placket line
  }
  if (cfg.top === 'hoodie') {
    const hood = new THREE.Mesh(new THREE.TorusGeometry(.14, .05, 8, 14), topM);
    hood.position.set(0, 1.56, -.1); hood.rotation.x = .5; g.add(hood);
  }
  if (cfg.top === 'polo') box(.23, .05, .27, topM, 0, 1.545, 0, g, false);
  if (cfg.top === 'henley')
    for (const yy of [1.46, 1.4, 1.34])
      sphere(.012, M('#d9d4c8', .5), .02, yy, .21, g);
  if (cfg.top === 'denim-jacket') {
    for (const sx of [-1, 1])
      box(.02, .42, .265, M('#3a4a5c', .9), sx * .1, 1.32, 0, g, false);
    box(.42, .06, .27, M('#3a4a5c', .9), 0, 1.1, 0, g, false);
  }
  if (cfg.top === 'chore-coat') box(.43, .16, .3, topM, 0, 1.04, 0, g);
  if (cfg.top === 'sweatshirt') box(.41, .05, .28, topM, 0, 1.11, 0, g, false);
  if (cfg.top === 'thermal')
    for (const yy of [1.24, 1.36])
      box(.415, .02, .27, M('#00000022', .9), 0, yy, 0, g, false);
  if (cfg.pants === 'bib-overalls') {
    box(.26, .3, .04, pantsM, 0, 1.38, .2, g);
    for (const sx of [-1, 1]) box(.05, .3, .03, pantsM, sx * .1, 1.55, .16, g);
  }
  // outerwear shell, worn under the vest, over everything else
  const OUTER = !CS && {
    parka: { c: '#4a5a64', hood: 1, long: 1 },
    'rain-slicker': { c: '#d9c22e', sheen: 1, hood: 1, long: 1 },
    'welding-jacket': { c: '#7a5a34' }, bomber: { c: '#2e4d3a' },
    duster: { c: '#5d4127', long: 2 },
    windbreaker: { c: '#2f4d8a', sheen: 1 },
    'lined-flannel': { c: '#a03a34' },
    'hi-vis-parka': { c: '#e8722a', viz: 1, hood: 1 },
    softshell: { c: '#33363a' }, 'chore-canvas': { c: '#a5793f', long: 1 },
    puffer: { c: '#2c3e5a', puff: 1 }, anorak: { c: '#3c6b45', hood: 1 },
    varsity: { c: '#2c3e5a' }, trench: { c: '#8a7f6a', long: 2 },
  }[cfg.outer];
  if (OUTER) {
    const om = M(OUTER.c, OUTER.sheen ? .3 : .85);
    capsule(.225, .34, om, 0, 1.31, 0, g);
    for (const sx of [-1, 1]) capsule(.088, .16, om, sx * .3, 1.4, 0, g);
    if (OUTER.long) box(.43, .1 + .08 * OUTER.long, .31, om, 0, 1.0, 0, g);
    if (OUTER.hood) {
      const hd = new THREE.Mesh(new THREE.TorusGeometry(.15, .055, 8, 14), om);
      hd.position.set(0, 1.6, -.11); hd.rotation.x = .5; g.add(hd);
    }
    if (OUTER.puff)
      for (const yy of [1.2, 1.33, 1.46]) {
        const ring = new THREE.Mesh(new THREE.TorusGeometry(.215, .05, 8, 16), om);
        ring.rotation.x = Math.PI / 2; ring.position.y = yy; g.add(ring);
      }
    if (OUTER.viz) box(.5, .05, .52, reflect, 0, 1.26, 0, g, false);
    if (cfg.outer === 'varsity')
      for (const sx of [-1, 1]) capsule(.09, .14, M('#e6e6e2', .8), sx * .3, 1.38, 0, g);
  }
  // the shirt mark
  // the crew mark rides the chest BONE, so it moves with the torso
  const crewMark = markPlane(.14, .16, crewId);
  crewMark.position.set(.1, .05, .215); chest.add(crewMark);

  // vest over it
  if (vestOn) {
    const vm = ['hi-vis-2', 'hi-vis-3', 'mesh'].includes(cfg.vest) ? hiviz
      : cfg.vest === 'fire-resist' ? M('#a03a34', .7)
      : cfg.vest === 'life-vest' ? M('#e8722a', .6)
      : cfg.vest === 'tool-vest' ? M('#5d4127', .85)
      : M('#4a5a64', .8);
    box(.46, .42, .05, vm, 0, 1.34, .2, g);
    box(.46, .42, .05, vm, 0, 1.34, -.2, g);
    for (const sx of [-1, 1]) box(.1, .06, .44, vm, sx * .17, 1.56, 0, g);
    if (cfg.vest !== 'tool-vest') {
      box(.46, .05, .055, reflect, 0, 1.24, .2, g, false);
      box(.46, .05, .055, reflect, 0, 1.24, -.2, g, false);
      if (cfg.vest === 'hi-vis-3' || cfg.vest === 'surveyor')
        for (const sx of [-1, 1])
          box(.06, .4, .055, reflect, sx * .12, 1.34, .2, g, false);
    }
    const back = markPlane(.2, .24, crewId);
    back.position.set(0, 1.36, -.228); back.rotation.y = Math.PI; g.add(back);
  }
  // tool belt
  if (cfg.tools !== 'none') {
    box(.44, .09, .3, dark, 0, .95, 0, g);
    const n = { basic: 1, framing: 3, electric: 2, plumber: 2, mason: 2,
      welder: 2, surveyor: 1, drywall: 2, hvac: 2, glazier: 1, roofer: 3,
      concrete: 2, rigger: 3, finisher: 2 }[cfg.tools] ?? 1;
    for (let i = 0; i < n; i++)
      box(.11, .16, .07, M('#5d4127', .9), -.16 + i * .16, .84, .18, g);
  }

  // arms on shoulder pivots
  const sleeves = ['long-sleeve', 'flannel', 'hoodie', 'sweatshirt',
    'denim-jacket', 'chore-coat', 'coveralls', 'thermal', 'rain-shell',
    'fleece', 'work-shirt'].includes(cfg.top);
  const tank = cfg.top === 'tank';
  const arms = {};
  const handM = cfg.extras === 'gloves' ? M('#e8722a', .7)
    : ANIMAL ? M(CS.top, .95)
    : cfg.costume === 'parade' || cfg.costume === 'mascot' ? M('#e6e6e2', .6)
    : skin;
  if (APE) handM.flatShading = true;
  for (const [nm, side, sx] of [['armL', 'left', -1], ['armR', 'right', 1]]) {
    // the arm chain hangs off the chest, so a shrug carries the whole arm
    const p = bone(side + 'UpperArm', chest, sx * .3, .17, 0);     // world 1.52
    const lo = bone(side + 'LowerArm', p, 0, -.28, 0);             // world 1.24
    const hd = bone(side + 'Hand', lo, 0, -.28, 0);                // world 0.96
    bones[side + 'UpperArm'] = p;
    bones[side + 'LowerArm'] = lo;
    bones[side + 'Hand'] = hd;
    capsule(.07, .2, tank ? skin : topM, 0, -.14, 0, p);
    capsule(.06, .18, sleeves ? topM : skin, 0, -.14, 0, lo);
    sphere(APE ? .082 : cfg.costume === 'mascot' ? .085 : .06, handM, 0, -.02, 0, hd);
    if (cfg.extras === 'elbow-pads') box(.1, .1, .09, dark, 0, -.02, .05, lo, false);
    if (cfg.costume === 'night-reflective' || cfg.costume === 'tunnel')
      box(.15, .035, .15, reflect, 0, .04, 0, lo, false);
    if (APE) { p.scale.y = APE_ARM; p.position.x *= APE_SHX; }
    arms[nm] = p;
    arms[nm + 'Lo'] = lo;
  }

  // neck + head with the face
  capsule(.06, .06, skin, 0, 1.6, 0, g);
  const head = bone('head', neck, 0, .21, 0);        // world 1.78
  bones.head = head;
  if (ANIMAL) {
    const fur = M(CS.top, .95);
    const eyePair = (ex, ey, ez, r = .018) => {
      for (const sx of [-1, 1]) {
        sphere(r * 1.7, M('#f2f2ee', .4), sx * ex, ey, ez, head, 1, 1, .55);
        sphere(r, eyeM, sx * ex, ey, ez + .02, head);
      }
    };
    if (ANIMAL === 'ape-mascot') {
      fur.flatShading = true;
      const face = new THREE.MeshStandardMaterial({
        color: '#c9a180', roughness: .7, flatShading: true });
      const lid = M('#a5794f', .75);
      sphere(.165, fur, 0, .015, -.01, head, 1, 1.05, 1);
      sphere(.115, face, 0, -.005, .085, head, 1, 1.04, .6);
      sphere(.08, face, 0, -.075, .115, head, 1.3, .8, .95);
      box(.06, .016, .02, M('#241f1c', .6), 0, -.1, .185, head, false);
      for (const sx of [-1, 1]) {
        sphere(.013, M('#241f1c', .5), sx * .022, -.052, .18, head);
        sphere(.052, fur, sx * .175, .02, -.02, head, .5, 1, .9);
        sphere(.03, face, sx * .175, .02, .01, head, .35, .7, .6);
        // the layered eye: lid band, sclera, iris, pupil
        sphere(.03, lid, sx * .052, .052, .112, head, 1.1, .55, .55);
      }
      box(.135, .03, .032, fur, 0, .082, .112, head, false);
      eyePair(.052, .033, .118);
      for (const sx of [-1, 1])
        sphere(.008, M('#0a0a0c', .3), sx * .052, .033, .152, head);
      head.scale.setScalar(1.12);
      head.position.y -= .06; head.position.z += .07;
    } else if (ANIMAL === 'pelican-mascot') {
      sphere(.15, fur, 0, .02, -.01, head, 1, 1.05, 1);
      const beak = M('#e08a2a', .55);
      box(.07, .025, .26, beak, 0, -.02, .22, head, false);
      box(.06, .02, .22, beak, 0, -.05, .2, head, false);
      sphere(.05, M('#e8b25a', .6), 0, -.085, .16, head, 1, 1.1, .9);
      eyePair(.055, .05, .11, .015);
    } else if (ANIMAL === 'bear-mascot') {
      sphere(.155, fur, 0, .01, 0, head, 1, 1, 1);
      const muz = M('#c9a180', .7);
      sphere(.07, muz, 0, -.045, .12, head, 1.1, .85, .9);
      sphere(.026, M('#241f1c', .4), 0, -.02, .19, head);
      for (const sx of [-1, 1]) sphere(.05, fur, sx * .11, .13, -.01, head);
      eyePair(.055, .04, .12);
    } else if (ANIMAL === 'gator-mascot') {
      sphere(.15, fur, 0, .02, -.02, head, 1, .9, 1);
      box(.13, .045, .22, fur, 0, -.03, .18, head);
      box(.12, .03, .2, M('#5b8a5f', .8), 0, -.065, .17, head, false);
      box(.11, .012, .18, M('#e6e6e2', .6), 0, -.048, .18, head, false);
      for (const sx of [-1, 1]) sphere(.035, fur, sx * .06, .1, .04, head);
      eyePair(.06, .095, .06, .016);
    } else if (ANIMAL === 'ox-mascot') {
      sphere(.155, fur, 0, .01, 0, head, 1.05, 1, 1);
      const muz = M('#cbb8a2', .7);
      sphere(.085, muz, 0, -.06, .11, head, 1.15, .8, .9);
      for (const sx of [-1, 1]) {
        sphere(.014, M('#241f1c', .5), sx * .03, -.06, .185, head);
        const horn = new THREE.Mesh(new THREE.ConeGeometry(.025, .12, 8),
          M('#e3d9c2', .5));
        horn.position.set(sx * .13, .14, 0);
        horn.rotation.z = sx * -.7; head.add(horn);
        sphere(.04, fur, sx * .15, .04, -.02, head, .5, .8, .9);
      }
      eyePair(.06, .04, .12);
    }
  } else {
  sphere(.145, skin, 0, 0, 0, head, 1, 1.08, 1);
  for (const sx of [-1, 1]) {
    sphere(.032, M('#f2f2ee', .4), sx * .052, .02, .118, head, 1, 1, .5);
    sphere(.016, eyeM, sx * .052, .02, .138, head);
    box(.05, .012, .02, hairM, sx * .052, .065, .125, head, false);
  }
  sphere(.028, skin, 0, -.01, .145, head, .8, 1.1, .9);           // nose
  box(.05, .012, .015, M('#8a5a4a', .6), 0, -.062, .132, head, false); // mouth
  for (const sx of [-1, 1]) sphere(.03, skin, sx * .14, 0, 0, head, .5, 1, .8);
  }

  // facial hair, from the hair colour
  const fh = ANIMAL ? 'none' : cfg.facialhair;
  if (fh !== 'none') {
    const fhM = new THREE.MeshStandardMaterial({
      color: optOf('haircolor').value, roughness: .95,
      transparent: fh === 'stubble', opacity: fh === 'stubble' ? .35 : 1 });
    const mo = () => box(.085, .02, .03, fhM, 0, -.035, .132, head, false);
    if (['light-mustache', 'mustache', 'handlebar', 'walrus'].includes(fh)) mo();
    if (fh === 'handlebar') for (const sx of [-1, 1])
      box(.02, .04, .025, fhM, sx * .05, -.05, .128, head, false);
    if (fh === 'walrus') box(.1, .035, .035, fhM, 0, -.05, .13, head, false);
    if (['goatee', 'circle-beard', 'soul-patch'].includes(fh))
      box(.05, .05, .03, fhM, 0, -.105, .11, head, false);
    if (fh === 'circle-beard') mo();
    if (['stubble', 'short-beard', 'full-beard', 'long-beard',
         'garibaldi'].includes(fh))
      sphere(.148, fhM, 0, -.045, 0, head, .95, .8, .95);
    if (['full-beard', 'long-beard', 'garibaldi'].includes(fh)) mo();
    if (fh === 'long-beard') capsule(.05, .1, fhM, 0, -.2, .06, head);
    if (fh === 'garibaldi') sphere(.09, fhM, 0, -.15, .05, head, 1, .9, .8);
    if (['chin-strap', 'mutton-chops'].includes(fh)) {
      for (const sx of [-1, 1])
        box(.03, .1, .06, fhM, sx * .125, -.04, .04, head, false);
      if (fh === 'chin-strap') box(.08, .03, .03, fhM, 0, -.125, .09, head, false);
    }
  }

  // hair, unless a full hat hides it anyway
  const hs = ANIMAL ? 'bald' : cfg.hair;
  if (hs !== 'bald') {
    const shell = (sy, y) => sphere(.152, hairM, 0, y, -.01, head, 1, sy, 1);
    if (['buzz', 'crew', 'undercut'].includes(hs)) shell(.62, .05);
    else if (['short', 'side-part', 'waves', 'curls'].includes(hs)) shell(.75, .045);
    else if (hs === 'afro') sphere(.2, hairM, 0, .07, -.01, head);
    else if (hs === 'bob') { shell(.85, .03); sphere(.15, hairM, 0, -.03, -.05, head, 1, .9, .8); }
    else if (hs === 'bun') { shell(.7, .045); sphere(.055, hairM, 0, .1, -.15, head); }
    else if (hs === 'ponytail') { shell(.7, .045); capsule(.04, .16, hairM, 0, -.06, -.16, head); }
    else if (hs === 'braids') { shell(.7, .045);
      for (const sx of [-1, 0, 1]) capsule(.025, .16, hairM, sx * .07, -.08, -.13, head); }
    else if (hs === 'locs') { shell(.75, .05);
      for (const sx of [-2, -1, 0, 1, 2]) capsule(.022, .12, hairM, sx * .05, -.05, -.12, head); }
    else if (hs === 'mohawk') box(.035, .09, .24, hairM, 0, .12, -.01, head);
    else if (hs === 'long') { shell(.8, .04);
      box(.2, .3, .05, hairM, 0, -.12, -.12, head, false); }
    if (hs === 'curls') sphere(.16, hairM, 0, .06, -.01, head, 1, .7, 1);
  }

  // headwear, on its own group so the hat-tip emote can lift it
  const hat = new THREE.Group(); hat.position.y = ANIMAL ? .17 : .13;
  head.add(hat);
  const hw = ANIMAL ? 'none' : cfg.headwear;
  const markFront = () => {
    const mk = markPlane(.09, .1, crewId);
    mk.position.set(0, .035, .135); mk.rotation.x = -.15; hat.add(mk);
  };
  if (['hard-cap', 'full-brim', 'climbing', 'vintage', 'carbon'].includes(hw)) {
    const dome = new THREE.Mesh(new THREE.CylinderGeometry(
      hw === 'vintage' ? .12 : .135, .15,
      hw === 'vintage' ? .13 : .09, 14),
      hw === 'carbon' ? M('#2a2d31', .35) : hatM);
    dome.position.y = .06; dome.castShadow = true; hat.add(dome);
    if (hw === 'full-brim') {
      const brim = new THREE.Mesh(new THREE.CylinderGeometry(.21, .225, .02, 16),
        hw === 'carbon' ? M('#2a2d31', .35) : hatM);
      brim.position.y = .015; hat.add(brim);
    } else if (hw !== 'climbing') box(.14, .02, .1, hatM, 0, .015, .17, hat, false);
    if (hw === 'climbing') box(.04, .06, .2, hatM, 0, .05, 0, hat, false);
    markFront();
  } else if (hw === 'ball-cap' || hw === 'ball-cap-back') {
    sphere(.15, hatM, 0, .03, 0, hat, 1, .68, 1);
    const brim = box(.13, .015, .12, hatM, 0, .02, hw === 'ball-cap' ? .19 : -.19, hat, false);
    if (hw === 'ball-cap') markFront();
  } else if (hw === 'flat-cap') {
    sphere(.15, hatM, 0, .025, -.02, hat, 1, .5, 1.05);
    box(.12, .012, .08, hatM, 0, .01, .16, hat, false);
  } else if (hw === 'beanie' || hw === 'winter-liner') {
    sphere(.152, hatM, 0, .03, 0, hat, 1, .8, 1);
    if (hw === 'winter-liner') for (const sx of [-1, 1])
      box(.03, .1, .08, hatM, sx * .14, -.05, .01, hat, false);
  } else if (hw === 'bucket') {
    const dm = new THREE.Mesh(new THREE.CylinderGeometry(.13, .14, .1, 14), hatM);
    dm.position.y = .05; hat.add(dm);
    const br = new THREE.Mesh(new THREE.CylinderGeometry(.19, .2, .015, 16), hatM);
    br.position.y = 0; hat.add(br);
  } else if (hw === 'welding-cap') {
    const dm = new THREE.Mesh(new THREE.CylinderGeometry(.135, .14, .09, 12), hatM);
    dm.position.y = .045; hat.add(dm);
    box(.1, .012, .07, hatM, 0, .005, .16, hat, false);
  } else if (hw === 'visor') {
    const band = new THREE.Mesh(new THREE.TorusGeometry(.145, .022, 8, 18), hatM);
    band.rotation.x = Math.PI / 2; band.position.y = .02; hat.add(band);
    box(.13, .014, .11, hatM, 0, .02, .18, hat, false);
  } else if (hw === 'headband') {
    const band = new THREE.Mesh(new THREE.TorusGeometry(.148, .02, 8, 18), hatM);
    band.rotation.x = Math.PI / 2; band.position.y = .015; hat.add(band);
  } else if (hw === 'bandana') {
    sphere(.152, hatM, 0, .02, 0, hat, 1, .55, 1);
    box(.05, .06, .02, hatM, 0, -.02, -.15, hat, false);
  }

  // extras: eye, ear and chest kit
  const ex = cfg.extras;
  if (ex === 'safety-glasses' || ex === 'sunglasses') {
    const lm = ex === 'sunglasses' ? M('#1a1c20', .3)
      : new THREE.MeshStandardMaterial({ color: 0xcfd8dc, roughness: .2,
          transparent: true, opacity: .55 });
    box(.13, .035, .02, lm, 0, .02, .148, head, false);
    for (const sx of [-1, 1]) box(.09, .012, .01, dark, sx * .1, .03, .07, head, false);
  }
  if (ex === 'ear-muffs') {
    for (const sx of [-1, 1]) sphere(.045, dark, sx * .15, .01, 0, head, .6, 1, 1);
    box(.24, .02, .02, dark, 0, .15, 0, head, false);
  }
  if (ex === 'respirator' || ex === 'dust-mask') {
    const mm = ex === 'respirator' ? M('#6c7276', .5) : M('#e6e6e2', .8);
    sphere(.07, mm, 0, -.035, .12, head, 1, .8, .7);
    if (ex === 'respirator')
      for (const sx of [-1, 1]) sphere(.028, M('#33363a', .5), sx * .05, -.05, .15, head);
  }
  if (ex === 'face-shield') {
    const sh = new THREE.Mesh(new THREE.PlaneGeometry(.24, .2),
      new THREE.MeshStandardMaterial({ color: 0xcfd8dc, roughness: .15,
        transparent: true, opacity: .35, side: THREE.DoubleSide }));
    sh.position.set(0, 0, .19); head.add(sh);
  }
  if (ex === 'welding-shield') {
    const sh = new THREE.Mesh(new THREE.PlaneGeometry(.22, .18),
      M('#173a2a', .4));
    sh.position.set(0, .16, .16); sh.rotation.x = -.5; hat.add(sh);
  }
  if (ex === 'headlamp') {
    box(.06, .04, .03, dark, 0, .05, .16, hat, false);
    sphere(.016, new THREE.MeshStandardMaterial({ color: 0xfff2cf,
      emissive: 0xffdf9a, emissiveIntensity: 1.2 }), 0, .05, .18, hat);
  }
  if (ex === 'radio') box(.06, .1, .04, dark, -.16, 1.44, .19, g, false);
  if (ex === 'id-badge') {
    const b2 = markPlane(.07, .09, crewId);
    b2.position.set(-.12, 1.3, .218); g.add(b2);
  }
  if (ex === 'tool-lanyard') {
    const ln = box(.015, .3, .015, M('#d9c22e', .6), .24, 1.14, .1, g, false);
    ln.rotation.z = .4;
  }

  // costume props
  if (CS) {
    const gold = M('#c9a227', .35); gold.metalness = .6;
    switch (cfg.costume) {
      case 'krewe':
        ['#5a2d82', '#c9a227', '#2f6b45'].forEach((c, i) => {
          const t = new THREE.Mesh(new THREE.TorusGeometry(.12 + .025 * i, .015, 6, 16), M(c, .35));
          t.position.set(0, 1.5 - .055 * i, .06); t.rotation.x = 1.25; g.add(t);
        });
        for (const sx of [-1, 1]) {
          const f = new THREE.Mesh(new THREE.ConeGeometry(.05, .16, 8), gold);
          f.position.set(sx * .3, 1.62, 0); g.add(f);
        }
        break;
      case 'foundry': {
        const hd = new THREE.Mesh(new THREE.CylinderGeometry(.16, .18, .2, 12),
          M('#b9bcbe', .3));
        hd.position.y = .06; hat.add(hd);
        box(.3, .4, .03, M('#8a8f94', .4), 0, 1.2, .22, g); break;
      }
      case 'diver': {
        const helm = new THREE.Mesh(new THREE.SphereGeometry(.2, 16, 12),
          M('#8a6a2a', .35));
        helm.position.y = .02; head.add(helm);
        const win = new THREE.Mesh(new THREE.CircleGeometry(.075, 16),
          new THREE.MeshStandardMaterial({ color: 0xbfe0e8, roughness: .15,
            transparent: true, opacity: .6 }));
        win.position.set(0, .02, .2); head.add(win);
        const hose = new THREE.Mesh(new THREE.TorusGeometry(.12, .02, 6, 14), dark);
        hose.position.set(0, 1.42, -.16); hose.rotation.y = .6; g.add(hose); break;
      }
      case 'vintage-33':
        for (const sx of [-1, 1])
          box(.05, .42, .03, M('#4a4238', .9), sx * .1, 1.34, .2, g, false);
        break;
      case 'gold-journey': {
        const sash = box(.1, .5, .03, gold, 0, 1.32, .21, g, false);
        sash.rotation.z = .6; break;
      }
      case 'parade': {
        const sash = box(.1, .5, .03, M('#a03a34', .6), 0, 1.32, .21, g, false);
        sash.rotation.z = -.6;
        const plume = new THREE.Mesh(new THREE.ConeGeometry(.03, .16, 8),
          M('#a03a34', .7));
        plume.position.set(0, .16, 0); hat.add(plume);
        for (const sx of [-1, 1]) box(.1, .03, .1, gold, sx * .3, 1.6, 0, g, false);
        break;
      }
      case 'hazmat': {
        const hd = new THREE.Mesh(new THREE.SphereGeometry(.185, 14, 10),
          M('#e3dc9a', .6));
        hd.position.y = .01; hd.scale.y = 1.1; head.add(hd);
        const win2 = new THREE.Mesh(new THREE.CircleGeometry(.08, 16),
          new THREE.MeshStandardMaterial({ color: 0xcfd8dc, roughness: .15,
            transparent: true, opacity: .5 }));
        win2.position.set(0, .02, .19); head.add(win2); break;
      }
      case 'arc-guard':
        box(.34, .12, .3, M('#6c7276', .6), 0, 1.6, 0, g); break;
      case 'tunnel':
        box(.42, .05, .28, reflect, 0, 1.3, 0, g, false);
        box(.42, .05, .28, reflect, 0, 1.14, 0, g, false); break;
      case 'night-reflective':
        box(.42, .05, .28, reflect, 0, 1.36, 0, g, false);
        box(.42, .05, .28, reflect, 0, 1.18, 0, g, false); break;
      case 'mascot': hat.scale.setScalar(1.7); break;
      case 'frost': {
        const cl = new THREE.Mesh(new THREE.TorusGeometry(.11, .04, 8, 14),
          M('#e6eef4', .7));
        cl.position.set(0, 1.56, 0); cl.rotation.x = Math.PI / 2; g.add(cl); break;
      }
      case 'gala':
        box(.16, .3, .02, M('#e6e6e2', .5), 0, 1.36, .21, g, false);
        box(.09, .035, .03, M('#1d1f24', .5), 0, 1.5, .215, g, false);
        for (const sx of [-1, 1])
          box(.03, .2, .022, M('#101114', .4), sx * .09, 1.42, .212, g, false);
        break;
      case 'storm-rider':
        box(.44, .06, .3, M('#d9c22e', .5), 0, 1.5, 0, g, false); break;
    }
  }

  const sc = optOf('build').scale ?? [1, 1, 1];
  g.scale.set(sc[0], sc[1], sc[2]);
  g.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  g.userData = { ...g.userData, arms, head, hat, bones };
  // The rig is NAMED for export in the VRM / Unity humanoid vocabulary
  // (vrm-c/UniVRM, MIT): bone() above named every bone as it was built,
  // so an importer meets the whole hierarchy rather than three loose
  // nodes. Only the root and the headwear are not VRM bones.
  g.name = 'tc-avatar';
  hat.name = 'headwear';                    // accessory, not a VRM bone
  return g;
}

function refreshAvatarMeshes() {
  if (avatarMesh) {
    const parent = avatarMesh.parent;
    parent.remove(avatarMesh);
    disposeOf(avatarMesh);
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

/* --------------------------------------------------------- the gait ----
   With a real skeleton the walk can be a walk: the legs swing in
   opposition with the knees bending only on the return, the feet roll,
   the arms counter-swing at the elbow, and the hips rise on each step.
   Driven by DISTANCE TRAVELLED rather than elapsed time, so the stride
   is tied to the ground and never moonwalks when the frame rate dips.
   Reduced-motion users keep the rest pose. */
const GAIT_LIMBS = ['leftUpperLeg', 'rightUpperLeg', 'leftLowerLeg',
  'rightLowerLeg', 'leftFoot', 'rightFoot', 'leftUpperArm', 'rightUpperArm',
  'leftLowerArm', 'rightLowerArm'];
function gait(av, dist) {
  const b = av?.userData?.bones;
  if (!b || reduced) return;
  const ph = dist * 2.2;                      // one stride per ~2.9 m
  const sw = Math.sin(ph), op = Math.sin(ph + Math.PI);
  b.leftUpperLeg.rotation.x = sw * .55;
  b.rightUpperLeg.rotation.x = op * .55;
  b.leftLowerLeg.rotation.x = Math.max(0, -sw) * .95;   // knees bend one way
  b.rightLowerLeg.rotation.x = Math.max(0, -op) * .95;
  b.leftFoot.rotation.x = -b.leftLowerLeg.rotation.x * .45;
  b.rightFoot.rotation.x = -b.rightLowerLeg.rotation.x * .45;
  b.leftUpperArm.rotation.x = op * .40;
  b.rightUpperArm.rotation.x = sw * .40;
  b.leftLowerArm.rotation.x = -Math.abs(op) * .35;
  b.rightLowerArm.rotation.x = -Math.abs(sw) * .35;
  b.chest.rotation.y = sw * .08;
  b.hips.rotation.y = -sw * .05;
  b.hips.position.y = .95 + Math.abs(sw) * .03;
}
function gaitRest(av, dt) {                    // settle back to the rest pose
  const b = av?.userData?.bones;
  if (!b) return;
  // decay per SECOND, not per frame, so the settle looks the same on a
  // 120 Hz laptop and on a phone the quality ladder has dropped to 20 fps
  const k = Math.exp(-11 * Math.min(dt || .016, .1));
  for (const n of GAIT_LIMBS) b[n].rotation.x *= k;
  b.chest.rotation.y *= k; b.hips.rotation.y *= k;
  b.hips.position.y += (.95 - b.hips.position.y) * (1 - k);
}
// the locker's idle: a breath in the spine, and a head that notices you.
// Both are bounded - the neck turns at most ~34 deg and the head ~23, so
// the avatar looks around rather than swivelling like a doll.
const NECK_MAX = .6, HEAD_MAX = .4;
function idleBreath(av, t, dt) {
  const b = av?.userData?.bones;
  if (!b || reduced) return;
  b.spine.rotation.x = Math.sin(t * 1.1) * .014;
  b.chest.rotation.x = Math.sin(t * 1.1 + .5) * .012;
  // look toward the camera: the yaw between where the body faces and where
  // the viewer stands, split between neck and head and clamped at both
  const dx = camera.position.x - av.position.x;
  const dz = camera.position.z - av.position.z;
  let yaw = Math.atan2(dx, dz) - av.rotation.y;
  yaw = Math.atan2(Math.sin(yaw), Math.cos(yaw));       // wrap to +/- PI
  const pitch = Math.max(-.3, Math.min(.3,
    -(camera.position.y - (av.position.y + 1.6)) * .08));
  const k = Math.min(1, (dt || .016) * 4);
  const nY = Math.max(-NECK_MAX, Math.min(NECK_MAX, yaw * .45));
  const hY = Math.max(-HEAD_MAX, Math.min(HEAD_MAX, yaw * .35));
  b.neck.rotation.y += (nY - b.neck.rotation.y) * k;
  b.head.rotation.y += (hY - b.head.rotation.y) * k;
  b.head.rotation.x += (pitch - b.head.rotation.x) * k;
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
    arms.armLLo.rotation.set(0, 0, 0); arms.armRLo.rotation.set(0, 0, 0);
    hat.position.y = .13; av.position.y = av.userData.baseY ?? av.position.y;
    switch (emo.move) {
      case 'arm-wave':
        arms.armR.rotation.z = -2.6 * s;
        arms.armR.rotation.x = Math.sin(emo.t * 14) * .5 * s;
        arms.armRLo.rotation.z = -.5 * s; break;   // the elbow joins in
      case 'arm-up': arms.armR.rotation.x = -2.9 * s; break;
      case 'arm-point': arms.armR.rotation.x = -1.55 * s; break;
      case 'hat-tip':
        arms.armR.rotation.x = -2.4 * s;
        hat.position.y = .13 + .14 * s; hat.rotation.z = .35 * s; break;
      case 'clap':
        arms.armLLo.rotation.x = arms.armRLo.rotation.x = -.9;
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
    // an emote owns the whole body: unwind any idle head-turn under it
    const b = av.userData.bones;
    if (b) {
      const d = Math.min(1, dt * 6);
      b.neck.rotation.y *= 1 - d;
      b.head.rotation.y *= 1 - d; b.head.rotation.x *= 1 - d;
    }
    if (k >= 1) {
      arms.armL.rotation.set(0, 0, 0); arms.armR.rotation.set(0, 0, 0);
      arms.armLLo.rotation.set(0, 0, 0); arms.armRLo.rotation.set(0, 0, 0);
      hat.position.y = .13; hat.rotation.z = 0;
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
  const isChars = wheelSection === sections.length;
  const isEmotes = wheelSection === sections.length + 1;
  const isApes = wheelSection === sections.length + 2;
  tabs.innerHTML = sections.map((s, i) =>
    `<button class="wtab ${i === wheelSection ? 'on' : ''}" data-tab="${i}"
       title="${s.label}">${s.emoji}</button>`).join('')
    + `<button class="wtab ${isChars ? 'on' : ''}" data-tab="${sections.length}"
        title="Characters">\\ud83c\\udfaa</button>`
    + `<button class="wtab ${isEmotes ? 'on' : ''}" data-tab="${sections.length + 1}"
        title="Emotes">\\ud83d\\ude00</button>`
    + `<button class="wtab ${isApes ? 'on' : ''}" data-tab="${sections.length + 2}"
        title="${D.avatars.tradeapes.collection}">\\ud83e\\udd8d</button>`;
  const svg = document.getElementById('wheel');
  const sec = sections[wheelSection] ?? null;
  const isCrew = sec?.kind === 'crew';
  // the crew wheel is two levels deep: pick a district, then a hall
  let items, pickAttr = 'data-pick', hubGlyph;
  if (isEmotes) { items = D.avatars.emotes; hubGlyph = '\\ud83d\\ude00'; }
  else if (isChars) {
    items = D.avatars.characters.map((c) => ({ id: c.id, emoji: c.emoji }));
    pickAttr = 'data-charpick'; hubGlyph = '\\ud83c\\udfaa';
  }
  else if ((isCrew || isApes) && !crewDistrict) {
    const crewSec = sections.find((x) => x.kind === 'crew');
    const seen = new Map();
    for (const o of crewSec.options)
      if (!seen.has(o.district)) seen.set(o.district, o.hue);
    items = [...seen].map(([d, hue]) => ({
      id: d, glyph: d.slice(0, 2).toUpperCase(), hue,
      value: `hsl(${hue},45%,34%)` }));
    pickAttr = 'data-crewdist';
    hubGlyph = isApes ? '\\ud83e\\udd8d' : sec.emoji;
  } else if (isApes) {
    items = D.avatars.tradeapes.apes
      .filter((t) => t.district === crewDistrict)
      .map((t) => ({ id: t.hall, glyph: t.code,
        value: `hsl(${t.hue},45%,34%)` }));
    pickAttr = 'data-apepick'; hubGlyph = '\\u2190';
  } else if (isCrew) {
    items = sec.options.filter((o) => o.district === crewDistrict)
      .map((o) => ({ ...o, value: `hsl(${o.hue},45%,34%)` }));
    pickAttr = 'data-pick'; hubGlyph = '\u2190';
  } else { items = sec.options; hubGlyph = sec.emoji; }
  const cur = isEmotes ? lastEmote
    : isApes ? (avatarCfg.costume === 'ape-mascot' ? avatarCfg.crew : null)
    : sec ? avatarCfg[sec.id] : null;
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
  const fsz = N > 14 ? 11 : 15;
  svg.innerHTML = items.map((o, i) => {
    const sel = o.id === cur;
    const fill = (isEmotes || isChars) ? 'var(--panel)'
      : o.value ?? 'var(--panel)';
    const [tx, ty] = mid(i, (r0 + R) / 2);
    const glyph = (isEmotes || isChars) ? o.emoji : o.glyph ?? '';
    return `<path d="${wedge(i)}" fill="${fill}"
        stroke="${sel ? 'var(--mark)' : 'var(--rule)'}"
        stroke-width="${sel ? 3 : 1}" ${pickAttr}="${o.id}"/>`
      + (glyph ? `<text x="${tx}" y="${ty}" text-anchor="middle"
          dominant-baseline="central" font-size="${isEmotes ? 17 : fsz}"
          fill="var(--ink)" pointer-events="none">${glyph}</text>` : '');
  }).join('')
    + `<circle cx="${cx}" cy="${cy}" r="${r0 - 6}" fill="var(--sunk)"
        stroke="var(--rule)" ${(isCrew || isApes) && crewDistrict ? 'data-crewback="1"' : ''}
        style="${(isCrew || isApes) && crewDistrict ? 'cursor:pointer' : ''}"/>`
    + `<text x="${cx}" y="${cy}" text-anchor="middle" dominant-baseline="central"
        font-size="20" pointer-events="none">${hubGlyph}</text>`;
}
function wheelShow(on) {
  document.getElementById('wheelWrap').style.display = on ? '' : 'none';
  if (on) renderWheel();
}
document.getElementById('wheelWrap').addEventListener('click', (e) => {
  const tab = e.target.closest('[data-tab]');
  if (tab) { wheelSection = +tab.dataset.tab; crewDistrict = null; renderWheel(); return; }
  const dist = e.target.closest('[data-crewdist]');
  if (dist) { crewDistrict = dist.dataset.crewdist; renderWheel(); return; }
  if (e.target.closest('[data-crewback]')) { crewDistrict = null; renderWheel(); return; }
  const ap = e.target.closest('[data-apepick]');
  if (ap) {
    const t = D.avatars.tradeapes.apes.find((x) => x.hall === ap.dataset.apepick);
    if (t) {
      avatarCfg = { ...t.cfg };
      prog.avatar = avatarCfg; saveProg();
      refreshAvatarMeshes(); renderWheel();
      if (view === 'avatar') {
        document.getElementById('hname').textContent = t.name;
        document.getElementById('hfocus').textContent =
          D.halls.find((h) => h.slug === t.hall).name + ' \\u00b7 '
          + D.avatars.tradeapes.honesty;
      }
    }
    return;
  }
  const chp = e.target.closest('[data-charpick]');
  if (chp) {
    const ch = D.avatars.characters.find((c) => c.id === chp.dataset.charpick);
    if (ch) {
      avatarCfg = { ...ch.cfg };
      prog.avatar = avatarCfg; saveProg();
      refreshAvatarMeshes(); renderWheel();
      if (view === 'avatar') {
        document.getElementById('hname').textContent = ch.name;
        document.getElementById('hfocus').textContent =
          ch.blurb + ' \u00b7 ' + D.avatars.guarantee;
      }
    }
    return;
  }
  const pick = e.target.closest('[data-pick]');
  if (!pick) return;
  const sections = D.avatars.sections;
  if (wheelSection === sections.length + 1) { playEmote(pick.dataset.pick); return; }
  avatarCfg[sections[wheelSection].id] = pick.dataset.pick;
  prog.avatar = avatarCfg; saveProg();
  refreshAvatarMeshes(); renderWheel();
});

/* ---------------------------------------------------- the locker view --- */
/* ---------------------------------------------- the metaverse layer ----- */
// Files, not a place: the connection to Unity, Sketchfab, Blender or any
// other glTF 2.0 consumer is standard files out and the learner's own
// files in. No service, no account, no upload - the meta registry states
// the contract and this page implements exactly it. The exporter/loader
// modules load on demand (repository or Pages build); where module
// resolution is unavailable the buttons degrade to a HUD line.
let lastExport = null, importedGlb = null;
function exportable(root) {
  const c = root.clone(true);
  const rm = [];
  c.traverse((o) => { if (o.isSprite || o.isLine || o.isPoints) rm.push(o); });
  rm.forEach((o) => o.parent?.remove(o));
  return c;
}
/* A minimal STORE-method zip around one file: where a host mediates
   saves (the published artifact) the allowlist takes .zip, so the .glb
   travels inside one, unchanged. */
const crcTable = (() => {
  const t = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
    t[i] = c >>> 0;
  }
  return t;
})();
function zipOne(name, u8) {
  let crc = 0xFFFFFFFF;
  for (let i = 0; i < u8.length; i++)
    crc = crcTable[(crc ^ u8[i]) & 0xFF] ^ (crc >>> 8);
  crc = (crc ^ 0xFFFFFFFF) >>> 0;
  const nm = new TextEncoder().encode(name);
  const out = new Uint8Array(30 + nm.length + u8.length + 46 + nm.length + 22);
  const dv = new DataView(out.buffer);
  const put = (off, bytes) => out.set(bytes, off);
  // local file header
  dv.setUint32(0, 0x04034b50, true); dv.setUint16(4, 20, true);
  dv.setUint32(14, crc, true);
  dv.setUint32(18, u8.length, true); dv.setUint32(22, u8.length, true);
  dv.setUint16(26, nm.length, true);
  put(30, nm); put(30 + nm.length, u8);
  // central directory
  const cd = 30 + nm.length + u8.length;
  dv.setUint32(cd, 0x02014b50, true); dv.setUint16(cd + 4, 20, true);
  dv.setUint16(cd + 6, 20, true);
  dv.setUint32(cd + 16, crc, true);
  dv.setUint32(cd + 20, u8.length, true); dv.setUint32(cd + 24, u8.length, true);
  dv.setUint16(cd + 28, nm.length, true);
  put(cd + 46, nm);
  // end of central directory
  const eo = cd + 46 + nm.length;
  dv.setUint32(eo, 0x06054b50, true);
  dv.setUint16(eo + 8, 1, true); dv.setUint16(eo + 10, 1, true);
  dv.setUint32(eo + 12, 46 + nm.length, true); dv.setUint32(eo + 16, cd, true);
  return out;
}
async function exportGlb(root, name) {
  try {
    const { GLTFExporter } = await import('three/addons/gltf/GLTFExporter.js');
    const bin = await new Promise((res, rej) =>
      new GLTFExporter().parse(exportable(root), res, rej, { binary: true }));
    lastExport = { name, bytes: bin.byteLength };
    const kb = (bin.byteLength / 1024).toFixed(0);
    // where the host mediates saves, offer the confirmed .zip door first
    const dlc = window.claude?.use ? await claude.use('downloads') : null;
    if (dlc) {
      try {
        await dlc.save({ filename: name + '.zip',
          data: new Blob([zipOne(name, new Uint8Array(bin))]) });
        document.getElementById('hint').textContent = name + '.zip · ' + kb
          + ' KB — unzip for the .glb (glTF 2.0, Unity / Sketchfab / Blender ready)';
      } catch (err) {
        document.getElementById('hint').textContent = err?.code === 'declined'
          ? 'save declined' : 'save unavailable — ' + (err?.message ?? err);
      }
      return;
    }
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([bin], { type: 'model/gltf-binary' }));
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    document.getElementById('hint').textContent = name + ' · ' + kb
      + ' KB · glTF 2.0 — Unity / Sketchfab / Blender ready';
  } catch (e) {
    document.getElementById('hint').textContent =
      'glTF export unavailable here — ' + (e?.message ?? e);
  }
}
async function importGlb(file) {
  try {
    const { GLTFLoader } = await import('three/addons/gltf/GLTFLoader.js');
    const buf = await file.arrayBuffer();
    const gltf = await new Promise((res, rej) =>
      new GLTFLoader().parse(buf, '', res, rej));
    if (importedGlb) avatarGroup.remove(importedGlb.stand);
    const obj = gltf.scene;
    // the guest stand: the learner's OWN file, fitted, local only
    const bb = new THREE.Box3().setFromObject(obj);
    const size = bb.getSize(new THREE.Vector3());
    obj.scale.setScalar(1.3 / Math.max(size.x, size.y, size.z, .001));
    bb.setFromObject(obj);
    obj.position.set(2.2 - (bb.min.x + bb.max.x) / 2,
      .35 - bb.min.y, -(bb.min.z + bb.max.z) / 2);
    const stand = new THREE.Group(); stand.name = 'guest-asset';
    const ped = new THREE.Mesh(new THREE.CylinderGeometry(.9, 1.05, .35, 20),
      mat.slab);
    ped.position.set(2.2, .17, 0); ped.receiveShadow = true;
    stand.add(ped, obj);
    avatarGroup.add(stand);
    let nodes = 0; obj.traverse(() => nodes++);
    importedGlb = { stand, nodes, name: file.name };
    document.getElementById('hint').textContent = file.name + ' · ' + nodes
      + ' nodes on the guest stand — local only, never uploaded; its licence'
      + ' (e.g. CC-BY attribution) stays the learner\\'s to honour';
  } catch (e) {
    document.getElementById('hint').textContent =
      'could not read that file as glTF — ' + (e?.message ?? e);
  }
}
document.getElementById('glbBtn').addEventListener('click', () => {
  if (view === 'avatar' && avatarMesh) exportGlb(avatarMesh, 'tc-avatar.glb');
  else if (view === 'hall' && hallGroup)
    exportGlb(hallGroup, 'tc-hall-' + slug + '.glb');
});
document.getElementById('glbInBtn').addEventListener('click', () =>
  document.getElementById('glbFile').click());
document.getElementById('glbFile').addEventListener('change', (e) => {
  if (e.target.files?.[0]) importGlb(e.target.files[0]);
  e.target.value = '';
});

function showAvatar() {
  if (sim) teardownSim();
  if (walkActive) exitWalkMode();
  view = 'avatar';
  if (hallGroup) hallGroup.visible = false;
  if (campusGroup) campusGroup.visible = false;
  if (regionGroup) regionGroup.visible = false;
  ground.visible = grid.visible = true;
  applyAtmos(null);
  scene.fog.near = 40; scene.fog.far = 140;
  document.getElementById('mm').style.display = 'none';
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
  document.getElementById('glbBtn').style.display = '';
  document.getElementById('glbInBtn').style.display = '';
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
  const was = walkAvatar.position.clone();
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
  // the gait rides the distance actually covered, after the clamps
  const moved = walkAvatar.position.distanceTo(was);
  walkAvatar.userData.dist = (walkAvatar.userData.dist ?? 0) + moved;
  if (moved > .0015) gait(walkAvatar, walkAvatar.userData.dist);
  else gaitRest(walkAvatar, dt);
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
  wheelSection = D.avatars.sections.length + 1;   // the emote tab
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

ADVISOR_JS = """/* ------------------------------------------------ advisor agents -------
   Somebody to ask. Each advisor is one of the Academy's own rigged
   avatars, standing in the room it speaks for, breathing and turning its
   head toward you like any other figure here - and answering a FIXED list
   of questions.

   Nothing is generated. A topic is either a `say` written in the advisor
   registry, or a `read` naming a binding that is resolved HERE against the
   record that already holds the fact - the hall's own condition record,
   the district's own crib, the seat's own walkaround. So the advisor never
   becomes a second copy of anything: change the condition record and the
   safety steward's answer changes with it.

   An advisor is not an instructor and not a gate. No grader reads any of
   this state, and there is nothing here for one to read. */
const ADVISOR_TABLE = D.advisors.who;
let advisorMeshes = [], nearAdvisor = null, curAdvisor = null, curTopic = null;

function advisorCfg(aid, crewSlug) {
  // an advisor wears locker options only - the look is one a learner could
  // also choose, and it takes the crew mark of the hall it stands in
  return { ...D.avatars.defaults, ...ADVISOR_TABLE[aid].crew,
           crew: crewSlug || D.avatars.defaults.crew };
}

function clearAdvisors() {
  for (const m of advisorMeshes) { m.parent?.remove(m); disposeOf(m); }
  advisorMeshes = []; nearAdvisor = null;
  const b = document.getElementById('advBtn');
  if (b) b.style.display = 'none';
}

// A whole rigged avatar is about forty draw calls. Seven of them standing
// in one hall is not worth what it costs at the far end of the room, so an
// advisor carries two bodies: the real one, and a three-box stand-in that
// reads as a person from across the floor. Only one is ever visible, and
// the swap happens well outside conversation range.
const ADV_DETAIL = 20;
function proxyFigure() {
  const g = new THREE.Group();
  const torso = new THREE.Mesh(boxGeo(.44, .62, .26), mat.part);
  torso.position.y = 1.22;
  const legs = new THREE.Mesh(boxGeo(.38, .82, .24), mat.wall);
  legs.position.y = .5;
  const head = new THREE.Mesh(boxGeo(.22, .24, .22), mat.metal);
  head.position.y = 1.66;
  g.add(torso, legs, head);
  return g;
}

function placeAdvisor(aid, parent, x, z, crewSlug) {
  const a = ADVISOR_TABLE[aid];
  if (!a) return null;
  const g = new THREE.Group();
  const body = buildAvatarMesh(advisorCfg(aid, crewSlug));
  const proxy = proxyFigure();
  proxy.visible = false;
  g.add(body, proxy);
  g.position.set(x, .45, z);
  g.rotation.y = Math.atan2(-x, -z);          // face the middle of the room
  g.scale.setScalar(.98);
  g.userData = { advisor: aid, body, proxy };
  const plate = label(a.glyph + '  ' + a.name, a.role, .44,
    { kind: 'advisor' });
  plate.position.set(0, 2.72, 0);
  g.add(plate);
  parent.add(g); advisorMeshes.push(g);
  return g;
}

// the hall: one advisor per room that has one, plus the guide at the door
function spawnHallAdvisors(h, W, DEP) {
  for (const [aid, a] of Object.entries(ADVISOR_TABLE)) {
    if (a.stands_in === 'green') continue;
    if (a.stands_in === 'door') { placeAdvisor(aid, hallGroup, 2.6,
      DEP / 2 - 3.2, h.slug); continue; }
    const r = roomRects.find((x) => x.strand === a.stands_in);
    if (!r) continue;                         // not every hall has every room
    const mx = (r.x0 + r.x1) / 2, mz = (r.z0 + r.z1) / 2;
    const len = Math.hypot(mx, mz) || 1;      // stand a step toward the aisle
    placeAdvisor(aid, hallGroup, mx - mx / len * .9, mz - mz / len * .9,
      h.slug);
  }
}

// the campus green: the dispatcher, who speaks for the whole site
function spawnCampusAdvisors() {
  for (const [aid, a] of Object.entries(ADVISOR_TABLE))
    if (a.stands_in === 'green')
      placeAdvisor(aid, campusGroup, 0, 11, null);
}

/* ---- what an advisor is standing near enough to be asked ---------------- */
const ADV_REACH = 4.2;
function advisorNear(pos) {
  let best = null, bd = 1e9, v = new THREE.Vector3();
  for (const m of advisorMeshes) {
    const d = m.getWorldPosition(v).distanceTo(pos);
    if (d < bd) { bd = d; best = m; }
  }
  return bd < ADV_REACH ? best.userData.advisor : null;
}

// Called every frame: offers the nearest advisor while walking, and keeps
// them alive - the same breath and head-turn every other figure here gets,
// so they read as people standing in a room rather than as signage.
function advisorProximity(dt) {
  const btn = document.getElementById('advBtn');
  if (!advisorMeshes.length) { if (nearAdvisor) clearAdvisors(); return; }
  const t = clock.elapsedTime, v = new THREE.Vector3();
  for (const m of advisorMeshes) {
    const near = m.getWorldPosition(v).distanceTo(camera.position) < ADV_DETAIL;
    m.userData.body.visible = near;
    m.userData.proxy.visible = !near;
    if (near) idleBreath(m.userData.body, t + m.position.x, dt);
  }
  if (!walkActive) {
    if (nearAdvisor) { nearAdvisor = null; btn.style.display = 'none'; }
    return;
  }
  const here = isTouch && walkAvatar ? walkAvatar.position : camera.position;
  const who = advisorNear(here);
  if (who === nearAdvisor) return;
  nearAdvisor = who;
  btn.style.display = who ? '' : 'none';
  if (who) btn.textContent = ADVISOR_TABLE[who].glyph + '  Ask the '
    + ADVISOR_TABLE[who].name.toLowerCase();
}

/* ---- resolving a `read` topic against the record that holds the fact ---- */
// the seat bound to a hall, if it has one: bindings are a list because a
// hall can host more than one machine, and the first is the hall's own
function seatOf(sg) {
  const bl = D.sims.bindings[sg];
  return bl && bl.length ? D.sims.sims[bl[0].sim] : null;
}
function advRead(bind, aid) {
  const esc = (s) => String(s).replace(/[&<>]/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  const h = D.halls.find((x) => x.slug === slug);
  // a room-bound answer is about the room this advisor is standing in,
  // never a room picked here: move the steward and the answer moves
  const st = (ADVISOR_TABLE[aid] || {}).stands_in;
  const room = () => h && h.rooms.find((r) => r.strand === st);
  const cond = () => (D.condOver[slug] && D.condOver[slug][st])
    || D.baseCond[st] || D.baseCond.safety;
  const li = (xs) => '<ul>' + xs.map((x) => '<li>' + x + '</li>').join('') + '</ul>';
  const cite = (w) => '<p class="src">' + esc(w) + '</p>';
  switch (bind) {
    case 'conditions.ppe': {
      const c = cond();
      // what this room demands, and then what the floor the trade is
      // actually learned on demands - the second is usually the longer
      // list, and hearing it at the door is the point of the door
      const bay = (D.condOver[slug] && D.condOver[slug].procedure)
        || D.baseCond.procedure;
      const extra = bay.ppe.filter((x) => !c.ppe.includes(x));
      return li(c.ppe.map(esc))
        + (extra.length ? '<h3>And on the practice floor, also</h3>'
            + li(extra.map(esc)) : '')
        + cite('read from this hall\\u2019s own condition records '
          + '(surfaces registry, \\u00a724.2)');
    }
    case 'conditions.hazards': {
      const c = cond();
      return (c.hazards && c.hazards.length
        ? li(c.hazards.map(esc))
        : '<p>None declared for this room \\u2014 which is a statement about '
          + 'the record, not a promise about a real one.</p>')
        + cite('read from this room\\u2019s condition record');
    }
    case 'conditions.env': {
      const c = cond();
      return '<p>' + c.lux + ' lux, ' + c.ach + ' air changes an hour, '
        + c.noise_db + ' dB, ' + c.temp_c[0] + '\\u2013' + c.temp_c[1]
        + ' \\u00b0C.</p>' + cite('read from this room\\u2019s condition record');
    }
    case 'surface.finish': {
      const r = room();
      if (!r) return '<p>That room is not laid out in this hall.</p>';
      const f = D.finCat[D.finishes[slug][r.strand].surface];
      return '<p><b>' + esc(f.name) + '</b> \\u2014 ' + esc(f.why) + '</p>'
        + cite('read from the finishes registry');
    }
    case 'crib.tools': {
      const c = h && D.tools.cribs[h.district];
      if (!c) return '<p>No crib is bound to this hall.</p>';
      return li(c.tools.map((t) => t.glyph + ' <b>' + esc(t.name) + '</b> \\u2014 '
        + esc(t.use))) + cite('read from the toolcrib registry');
    }
    case 'crib.drill':
      return '<p><b>' + esc(D.tools.drill.name) + '</b>, '
        + D.tools.drill.picks + ' picks. ' + esc(D.tools.drill.contract)
        + '</p>' + cite('read from the toolcrib registry');
    case 'sim.walkaround': {
      const s = seatOf(slug);
      if (!s) return '<p>No seat is bound to this hall, so there is nothing '
        + 'to walk before a start.</p>';
      return li(s.walkaround.map((w) => '<b>' + esc(w.point) + '</b> \\u2014 '
        + esc(w.check))) + cite('read from the simulator registry');
    }
    case 'sim.rubric': {
      const s = seatOf(slug);
      if (!s) return '<p>No seat is bound to this hall.</p>';
      return li(s.rubric.map((r) => '<b>' + esc(r.axis) + '</b> \\u2014 '
        + esc(r.measure) + ' (pass ' + esc(r.pass) + ')'))
        + '<p>' + esc(D.sims.honesty) + '</p>'
        + cite('read from the simulator registry');
    }
    case 'hall.rooms':
      return li((h ? h.rooms : []).map((r) => '<b>' + esc(r.label) + '</b> \\u2014 '
        + esc(r.purpose))) + cite('read from this hall\\u2019s own layout');
    case 'hall.focus':
      return '<p>' + esc(h ? h.focus : '') + '</p>'
        + cite('read from the hall registry');
    case 'campus.districts': {
      const c = D.campuses[campusKey];
      return li(c.districts.map((k) => '<b>' + esc(D.districts[k].name)
        + '</b> \\u2014 ' + D.districts[k].halls.length + ' halls'))
        + cite('read from the campus registry');
    }
    case 'campus.network':
      return li(D.geo.routes.filter((r) => r.from === campusKey
          || r.to === campusKey)
        .map((r) => '<b>' + esc(D.campuses[r.from === campusKey ? r.to : r.from]
          .name) + '</b> \\u2014 ' + r.km + ' km, bearing ' + r.bearing_deg
          + '\\u00b0'))
        + cite('DERIVED by great circle from the RECORDED coordinates');
    case 'city.anchors':
      return li((D.geo.anchors[campusKey] || []).map((a) => '<b>' + esc(a.name)
        + '</b> \\u2014 ' + a.km + ' km, bearing ' + a.bearing_deg + '\\u00b0'))
        + cite('RECORDED anchors, Locator.X (Apache-2.0)');
    case 'city.walk': {
      const W = D.advisors.walk, r10 = W.bands_m.ten_minute / 1000;
      const r15 = W.bands_m.fifteen_minute / 1000;
      const an = D.geo.anchors[campusKey] || [];
      const inside = an.filter((a) => a.km <= r15);
      const head = '<p>' + W.pace_note + '.</p>';
      const body = inside.length
        ? li(inside.map((a) => '<b>' + esc(a.name) + '</b> \\u2014 ' + a.km
            + ' km, inside the ' + (a.km <= r10 ? 'ten' : 'fifteen')
            + '-minute band'))
        : '<p>Not one recorded place around this campus is inside the '
          + 'fifteen-minute band \\u2014 the nearest is '
          + (an.length ? esc(an[0].name) + ' at ' + an[0].km + ' km'
             : 'not recorded') + '. This is car territory, and saying so is '
          + 'the useful part.</p>';
      return head + body + '<p class="src">' + esc(W.honesty.straight_line)
        + '</p><p class="src">' + esc(W.honesty.not_a_score) + '</p>';
    }
  }
  return '<p>No binding.</p>';
}

/* ---- the panel --------------------------------------------------------- */
function openAdvisor(aid, topicId) {
  const a = ADVISOR_TABLE[aid];
  if (!a) return;
  curAdvisor = aid; curTopic = topicId || null;
  if (topicId) {
    const tp = a.topics.find((x) => x.id === topicId);
    if (tp) recordEpisode({ kind: 'advisor', campus: campusKey, hall: slug,
      advisor: aid, topic: topicId, answer_kind: tp.kind });
  }
  const esc = (s) => String(s).replace(/[&<>]/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  const t = topicId && a.topics.find((x) => x.id === topicId);
  const answer = !t ? '<p class="focus">' + esc(a.greeting) + '</p>'
    : (t.kind === 'read' ? advRead(t.bind, aid)
       : '<p>' + esc(t.say) + '</p><p class="src">written in '
         + esc(t.cites) + '</p>');
  document.getElementById('pbody').innerHTML =
    '<h2>' + a.glyph + ' ' + esc(a.name) + '</h2>'
    + '<span class="chip">' + esc(a.role) + '</span>'
    + (t ? '<h3>' + esc(t.ask) + '</h3>' : '')
    + answer
    + '<h3>Ask</h3><div class="asks">'
    + a.topics.map((x) => '<button class="opt" data-adv="' + aid
        + '" data-topic="' + x.id + '"' + (t && t.id === x.id
          ? ' style="border-color:var(--mark)"' : '') + '>'
        + esc(x.ask) + '</button>').join('')
    + '</div>'
    + '<p class="src">' + esc(D.advisors.honesty.status) + '</p>'
    + '<p class="src">' + esc(D.advisors.honesty.not_scored) + '</p>'
    + '<p class="src">' + esc(D.advisors.honesty.not_a_person) + '</p>';
  document.body.classList.add('open');
}

document.addEventListener('click', (e) => {
  const b = e.target.closest('[data-adv]');
  if (b) openAdvisor(b.dataset.adv, b.dataset.topic);
});
document.getElementById('advBtn').addEventListener('click', () => {
  if (nearAdvisor) { if (walkActive && plc.isLocked) plc.unlock();
                     openAdvisor(nearAdvisor); }
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
/* the minimap: the campus from above, you as the amber arrow */
#mm{position:fixed;right:14px;top:62px;z-index:5;border:1px solid var(--rule);
  border-radius:9px;width:150px;height:150px}
@media(pointer:coarse){#mm{width:110px;height:110px;top:auto;bottom:200px}}
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
#panel p.src{color:var(--muted);font-size:11px;margin:6px 0 0}
.asks{display:flex;flex-direction:column;gap:4px}
.asks .opt{background:var(--sunk);border:1px solid var(--rule);color:var(--ink);border-radius:6px;padding:8px 10px;cursor:pointer;font:inherit;text-align:start;min-height:40px}
.asks .opt:hover{border-color:var(--mark)}
#advBtn{right:18px;bottom:158px}
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
  <button id="dnBtn" class="barbtn" aria-label="day / night">🌙</button>
  <button id="recBtn" class="barbtn" aria-label="records">⏱</button>
  <button id="vrBtn" class="barbtn" style="display:none">🥽 VR</button>
  <button id="arBtn" class="barbtn" style="display:none">📱 AR</button>
  <button id="satBtn" class="barbtn" style="display:none">🛰️</button>
  <button id="glbBtn" class="barbtn" style="display:none">⬇ .glb</button>
  <button id="glbInBtn" class="barbtn" style="display:none">＋ .glb</button>
  <input id="glbFile" type="file" accept=".glb,.gltf" style="display:none">
  <select id="lang"></select>
</div>
<div id="wheelWrap" style="display:none">
  <div id="wheelTabs"></div>
  <svg id="wheel" viewBox="0 0 200 200" role="listbox" aria-label="options"></svg>
</div>
<div id="joy" style="display:none"><div id="knob"></div></div>
<button id="emoBtn" class="fab" style="display:none">😀</button>
<button id="advBtn" class="fab wide" style="display:none"></button>
<button id="actBtn" class="fab wide" style="display:none"></button>
<div id="hud"><h2 id="hname"></h2><p class="focus" id="hfocus"></p><p class="hint" id="hint"></p></div>
<canvas id="mm" width="150" height="150" style="display:none"></canvas>
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
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const D = JSON.parse(document.getElementById('data').textContent);
// inflate the deduped payload: rooms from the per-depth layout and the
// per-strand defs, finishes from the 12 distinct maps - one truth per
// fact on the wire, the full shape everywhere downstream
for (const h of D.halls) {
  h.rooms = D.layouts[h.lay].map((r) => ({
    ...r, label: D.roomDefs[r.strand].label,
    purpose: D.roomDefs[r.strand].purpose,
    fixtures: h.fixtures?.[r.strand] ?? [] }));
}
D.finishes = Object.fromEntries(Object.entries(D.finIdx)
  .map(([sl, i2]) => [sl, D.finMaps[i2]]));
D.avatars.characters = D.avatars.characters.map((c) => ({
  ...c, cfg: { ...D.avatars.defaults, ...c.d } }));
D.avatars.tradeapes.apes = D.avatars.tradeapes.apes.map((a) => ({
  ...a, name: 'TradeApe ' + a.code,
  cfg: { ...D.avatars.defaults, ...a.d, crew: a.hall } }));
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
renderer.xr.enabled = true;
document.body.appendChild(renderer.domElement);

/* WebXR - experimental: the buttons appear only where the platform
   actually offers the session kind, and a refused session degrades to a
   HUD line, never an error. The same scene, the same registries; XR is
   a viewpoint, not a second world. */
/* Adaptive quality: when the frame rate stays under budget the page
   steps itself down ONCE - pixel ratio to 1, the sun stops casting
   shadows, the fog banks rest - and says so in the HUD. Manual override
   via the __tc3dDo hook; reduced-motion users are already served. */
let qLevel = 'high', qAuto = true, qAcc = 0, qFrames = 0;
function setQuality(l) {
  qLevel = l;
  renderer.setPixelRatio(l === 'low' ? 1
    : Math.min(devicePixelRatio, isTouch ? 1.5 : 2));
  key.castShadow = l !== 'low';
  for (const b of fogBanks) b.m.visible = l !== 'low';
}
function qStep(dt) {
  // harness runs (webdriver) keep deterministic visuals; they force via the hook
  if (!qAuto || qLevel === 'low' || reduced || navigator.webdriver) return;
  qAcc += dt; qFrames++;
  if (qAcc >= 5) {
    if (qFrames / qAcc < 22) {
      setQuality('low');
      document.getElementById('hint').textContent =
        '⚡ performance mode: resolution and shadows stepped down';
    }
    qAcc = 0; qFrames = 0;
  }
}

let xrMode = null;
async function xrProbe() {
  if (!navigator.xr?.isSessionSupported) return;
  for (const [mode, id] of [['immersive-vr', 'vrBtn'], ['immersive-ar', 'arBtn']]) {
    try {
      if (await navigator.xr.isSessionSupported(mode))
        document.getElementById(id).style.display = '';
    } catch (e) { /* stays hidden */ }
  }
}
xrProbe();
async function xrStart(mode) {
  try {
    const session = await navigator.xr.requestSession(mode, {
      optionalFeatures: ['local-floor'] });
    xrMode = mode;
    session.addEventListener('end', () => { xrMode = null; });
    await renderer.xr.setSession(session);
  } catch (e) {
    document.getElementById('hint').textContent =
      'XR session unavailable: ' + (e?.message ?? e);
  }
}
document.getElementById('vrBtn').addEventListener('click', () => xrStart('immersive-vr'));
document.getElementById('arBtn').addEventListener('click', () => xrStart('immersive-ar'));

const scene = new THREE.Scene();

/* ---------------------------------------------------------- the sky ----
   An equirectangular dome drawn into one canvas: the campus's own four
   gradient bands, a sun or a moon with its glow, a band of value-noise
   cloud thickened or thinned by the weather record, and after dark a star
   field placed by a FIXED seed - so it is a night sky, the same one every
   time, rather than a photograph of the night sky. No image is loaded to
   make any of it; see D.world.honesty.sky. */
const SKY = D.world.sky;
// a small deterministic generator: the same world every visit
function seeded(seed) {
  let x = seed >>> 0;
  return () => ((x = (x * 1664525 + 1013904223) >>> 0) / 4294967296);
}
// two-dimensional value noise, tiled, summed over octaves
function valueNoise(rnd, size) {
  const g = new Float32Array(size * size);
  for (let i = 0; i < g.length; i++) g[i] = rnd();
  return (x, y) => {
    const xi = Math.floor(x), yi = Math.floor(y);
    const fx = x - xi, fy = y - yi;
    const at = (a, b) => g[((b % size) + size) % size * size
      + ((a % size) + size) % size];
    const sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
    const t = at(xi, yi) + (at(xi + 1, yi) - at(xi, yi)) * sx;
    const u = at(xi, yi + 1) + (at(xi + 1, yi + 1) - at(xi, yi + 1)) * sx;
    return t + (u - t) * sy;
  };
}

function skyCanvas(stops, opts) {
  const W = 1024, H = 512;
  const c = document.createElement('canvas'); c.width = W; c.height = H;
  const g = c.getContext('2d');
  const gr = g.createLinearGradient(0, 0, 0, H);
  gr.addColorStop(0, stops[0]); gr.addColorStop(.55, stops[1]);
  gr.addColorStop(.8, stops[2]); gr.addColorStop(1, stops[3]);
  g.fillStyle = gr; g.fillRect(0, 0, W, H);

  // the stars go under everything else, and never move between visits
  if (opts.stars) {
    const rnd = seeded(0x5EEDDA7A);
    for (let i = 0; i < SKY.stars.count; i++) {
      const x = rnd() * W, y = rnd() * H * .62, a = .25 + rnd() * .7;
      const r = rnd() < .08 ? 2.1 : rnd() < .32 ? 1.4 : .9;
      g.fillStyle = `rgba(232,240,255,${(a * (1 - y / (H * .95))).toFixed(3)})`;
      g.beginPath(); g.arc(x, y, r, 0, 7); g.fill();
    }
  }

  // Sun or moon, drawn where the key light ACTUALLY comes from: azimuth
  // and elevation are read off the light itself, so the disc in the sky
  // and the shadows on the ground agree instead of merely coexisting.
  const disc = opts.moon ? SKY.disc.moon : SKY.disc.sun;
  const kp = key.position;
  const klen = Math.hypot(kp.x, kp.y, kp.z) || 1;
  const dx = W * ((Math.atan2(kp.z, kp.x) / (Math.PI * 2)) + .5);
  const dy = H * (1 - (Math.asin(Math.min(1, kp.y / klen)) / Math.PI + .5));
  const glow = g.createRadialGradient(dx, dy, 0, dx, dy, disc.glow_px);
  glow.addColorStop(0, disc.color + 'cc');
  glow.addColorStop(.35, disc.color + '44');
  glow.addColorStop(1, disc.color + '00');
  g.fillStyle = glow;
  g.fillRect(dx - disc.glow_px, dy - disc.glow_px,
    disc.glow_px * 2, disc.glow_px * 2);
  g.fillStyle = disc.color;
  g.beginPath(); g.arc(dx, dy, disc.radius_px, 0, 7); g.fill();
  // the canvas wraps around the horizon, so a disc near the seam is drawn
  // on both sides of it rather than being sliced in half
  if (dx < disc.glow_px || dx > W - disc.glow_px) {
    const wrap = dx < disc.glow_px ? dx + W : dx - W;
    const g2 = g.createRadialGradient(wrap, dy, 0, wrap, dy, disc.glow_px);
    g2.addColorStop(0, disc.color + 'cc');
    g2.addColorStop(.35, disc.color + '44');
    g2.addColorStop(1, disc.color + '00');
    g.fillStyle = g2;
    g.fillRect(wrap - disc.glow_px, dy - disc.glow_px,
      disc.glow_px * 2, disc.glow_px * 2);
    g.fillStyle = disc.color;
    g.beginPath(); g.arc(wrap, dy, disc.radius_px, 0, 7); g.fill();
  }
  if (opts.moon) {                       // bite a crescent out of it
    g.globalCompositeOperation = 'destination-out';
    g.beginPath();
    g.arc(dx - disc.radius_px * .5, dy - disc.radius_px * .25,
      disc.radius_px * .92, 0, 7);
    g.fill();
    g.globalCompositeOperation = 'source-over';
  }

  // the cloud band: value noise over octaves, alpha driven by the weather
  const amount = opts.cloud ?? .2;
  if (amount > .02) {
    const rnd = seeded(0xC10D5);
    const n = valueNoise(rnd, 64);
    const y0 = H * SKY.clouds.band_from, y1 = H * SKY.clouds.band_to;
    const img = g.getImageData(0, y0, W, y1 - y0);
    const d = img.data;
    for (let y = 0; y < y1 - y0; y++) {
      const fade = Math.sin(Math.PI * (y / (y1 - y0)));
      for (let x = 0; x < W; x++) {
        let v = 0, amp = .5, f = SKY.clouds.base_frequency;
        for (let o = 0; o < SKY.clouds.octaves; o++) {
          v += n(x * f, (y + y0) * f) * amp; amp *= .5; f *= 2.1;
        }
        const a = Math.max(0, (v - (1 - amount) * .58)) * fade * 3.2
          * Math.min(1, opts.dim ?? 1);
        if (a <= 0) continue;
        const i = (y * W + x) * 4;
        const lum = opts.moon ? 96 : 232;
        d[i] += (lum - d[i]) * Math.min(1, a);
        d[i + 1] += (lum - d[i + 1]) * Math.min(1, a);
        d[i + 2] += (lum + 6 - d[i + 2]) * Math.min(1, a);
      }
    }
    g.putImageData(img, 0, y0);
  }
  // a bright band just above the horizon, so the dome does not end on an
  // edge the eye can find
  const hz = SKY.horizon_haze;
  const hg = g.createLinearGradient(0, H * (1 - hz.height * 2), 0, H);
  const haze = opts.moon ? '150,166,190' : '214,226,236';
  hg.addColorStop(0, `rgba(${haze},0)`);
  hg.addColorStop(1, `rgba(${haze},${(hz.strength * (opts.moon ? .35 : 1))
    .toFixed(2)})`);
  g.fillStyle = hg;
  g.fillRect(0, H * (1 - hz.height * 2), W, H * hz.height * 2);
  return c;
}

function setSky(stops, opts = {}) {
  scene.background?.dispose?.();
  const t = new THREE.CanvasTexture(skyCanvas(stops, opts));
  t.mapping = THREE.EquirectangularReflectionMapping;
  t.colorSpace = THREE.SRGBColorSpace;
  scene.background = t;
}
scene.fog = new THREE.Fog(0x1a2229, 70, 170);

/* ------------------------------------------------- generated surfaces ----
   Every surface in this bundle is a RECIPE, never a file: a base colour, a
   grain, an octave count and a relief depth, all declared in the world
   registry. The colour map and its NORMAL map are both generated here, in
   this browser, at boot - which is why the render contains no third-party
   artwork, and why the whole surface set can be regenerated smaller when
   the quality ladder steps down. See D.world.honesty.textures. */
const GROUND_RECIPES = D.world.ground;
const groundCache = new Map();

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

// one recipe -> { map, normalMap }, generated once and shared
function groundTex(id, size = 256) {
  const hit = groundCache.get(id + ':' + size);
  if (hit) return hit;
  const r = GROUND_RECIPES[id];
  if (!r) return { map: null, normalMap: null };
  const rnd = seeded(0xA5 + id.length * 7919);
  const n = valueNoise(rnd, 32);
  const c = document.createElement('canvas'); c.width = c.height = size;
  const g = c.getContext('2d');
  g.fillStyle = r.base; g.fillRect(0, 0, size, size);
  // the height field the relief is read from, built as we shade
  const h = new Float32Array(size * size);
  const img = g.getImageData(0, 0, size, size), d = img.data;
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    let v = 0, amp = .5, f = 1 / 22;
    for (let o = 0; o < r.octaves; o++) {
      v += n(x * f, y * f) * amp; amp *= .5; f *= 2.07;
    }
    h[y * size + x] = v;
    const i = (y * size + x) * 4;
    const k = (v - .5) * 46;
    d[i] = Math.max(0, Math.min(255, d[i] + k));
    d[i + 1] = Math.max(0, Math.min(255, d[i + 1] + k));
    d[i + 2] = Math.max(0, Math.min(255, d[i + 2] + k));
  }
  g.putImageData(img, 0, 0);
  // the speckle sits on top of the noise, in the recipe's grain colour
  for (let i = 0; i < r.speckle; i++) {
    g.fillStyle = `rgba(${r.grain},${(.05 + rnd() * .12).toFixed(3)})`;
    const rr = rnd() * 2.4;
    g.fillRect(rnd() * size, rnd() * size, rr, rr);
  }
  const map = new THREE.CanvasTexture(c);
  map.wrapS = map.wrapT = THREE.RepeatWrapping;
  map.anisotropy = 4; map.colorSpace = THREE.SRGBColorSpace;

  // the normal map, read straight off the height field by central difference
  let normalMap = null;
  if (r.relief > .01) {
    const nc = document.createElement('canvas'); nc.width = nc.height = size;
    const ng = nc.getContext('2d');
    const nimg = ng.createImageData(size, size), nd = nimg.data;
    const at = (x, y) => h[(((y % size) + size) % size) * size
      + (((x % size) + size) % size)];
    const k = r.relief * 5.5;
    for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
      const dx = (at(x + 1, y) - at(x - 1, y)) * k;
      const dy = (at(x, y + 1) - at(x, y - 1)) * k;
      const len = Math.hypot(dx, dy, 1);
      const i = (y * size + x) * 4;
      nd[i] = (-dx / len * .5 + .5) * 255;
      nd[i + 1] = (-dy / len * .5 + .5) * 255;
      nd[i + 2] = (1 / len * .5 + .5) * 255;
      nd[i + 3] = 255;
    }
    ng.putImageData(nimg, 0, 0);
    normalMap = new THREE.CanvasTexture(nc);
    normalMap.wrapS = normalMap.wrapT = THREE.RepeatWrapping;
    normalMap.anisotropy = 4;
  }
  const out = { map, normalMap, recipe: r };
  groundCache.set(id + ':' + size, out);
  return out;
}

// One recipe can be laid at several scales, and a texture carries its own
// repeat, so the pair is cached per (recipe, repeat) rather than per
// recipe. The canvas underneath is still generated once and shared.
const groundMapCache = new Map();
function groundMaps(id, repeat) {
  const key = id + '@' + repeat;
  const hit = groundMapCache.get(key);
  if (hit) return hit;
  const base = groundTex(id);
  const map = base.map.clone(); map.needsUpdate = true;
  map.repeat.set(repeat, repeat);
  let normalMap = null;
  if (base.normalMap) {
    normalMap = base.normalMap.clone(); normalMap.needsUpdate = true;
    normalMap.repeat.set(repeat, repeat);
  }
  const out = { map, normalMap };
  groundMapCache.set(key, out);
  return out;
}

// a standard material straight off a recipe, repeat and relief included
function groundMat(id, tint, repeat) {
  const r = GROUND_RECIPES[id];
  const t = groundMaps(id, repeat ?? r.repeat);
  return new THREE.MeshStandardMaterial({
    map: t.map, normalMap: t.normalMap,
    normalScale: t.normalMap ? new THREE.Vector2(r.relief, r.relief) : null,
    color: tint ?? 0xffffff,
    roughness: r.roughness, metalness: r.metalness });
}

const asphaltTex = groundMaps('asphalt', 34).map;
const concreteTex = groundMaps('concrete', 9).map;

// far clears both the campus fog-far (1280) and the region board's
// (1300) with margin, so nothing pops at the clip plane before fog hides it
const camera = new THREE.PerspectiveCamera(50, innerWidth/innerHeight, .1, 1600);
camera.position.set(30, 26, 42);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI * .49;
controls.minDistance = 8; controls.maxDistance = 120;
controls.autoRotate = !reduced;
controls.autoRotateSpeed = .45;
controls.addEventListener('start', () => { controls.autoRotate = false; });

const hemi = new THREE.HemisphereLight(0xaec2cb, 0x241d16, 1.05);
scene.add(hemi);
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

// the first sky, now that the light it draws the sun from exists
setSky(['#0c141c', '#1a2a36', '#33404a', '#463a2a'], { cloud: .18 });

/* ------------------------------------------------------- atmosphere ----- */
// Authored ambience per campus and six weather states, both read from the
// world registry rather than written here: the fog is San Francisco's and
// the haze is New Orleans's BY REPUTATION, not by any weather record, and
// a weather state is a set of multipliers applied to whichever campus
// atmosphere is loaded - so a campus keeps its own character in the rain
// instead of every campus looking alike under it.
const ATMOS = D.world.atmos;
const WX = D.world.weather;
const WX_CYCLE = Object.entries(WX).sort((a, b) => a[1].order - b[1].order)
  .map(([k]) => k);
const DEF_ATMOS = {
  sky: ['#0c141c', '#1a2a36', '#33404a', '#463a2a'],
  fog: { color: 0x1a2229, mul: 1 }, banks: 0,
  sun: { color: 0xffe0b0, i: 1.6 },
  hemi: { sky: 0xaec2cb, ground: 0x241d16, i: 1.05 },
  amb: { wind: .2 }, ground: 'concrete', verge: 'grass',
};
let atmosKey = null, fogMul = 1, fogBanks = [], wx = 'clear', night = false;
let genMs = 0;
const darkHex = (hex, f) => '#' + [1, 3, 5].map((i) =>
  Math.round(Math.min(255, parseInt(hex.slice(i, i + 2), 16) * f))
    .toString(16).padStart(2, '0')).join('');

function applyAtmos(k) {
  const a = ATMOS[k] ?? DEF_ATMOS;
  const w = WX[wx] ?? WX.clear;
  atmosKey = ATMOS[k] ? k : null;
  night = wx === 'night';
  fogMul = a.fog.mul * w.fog_mul;
  const t0 = performance.now();
  setSky(a.sky.map((h) => darkHex(h, w.sky_mul)),
    { cloud: w.cloud, moon: !!w.moon, stars: !!w.stars,
      dim: Math.min(1, w.sky_mul) });
  genMs += performance.now() - t0;
  scene.fog.color.setHex(a.fog.color).multiplyScalar(w.fog_tint);
  // after dark the sun is swapped for moonlight rather than dimmed; under
  // weather it keeps its own colour and simply loses strength
  if (night) { key.color.setHex(0x9db4d8); hemi.color.setHex(0x35455c);
               hemi.groundColor.setHex(0x0d0c0a); }
  else if (w.sun_mul < .7) { key.color.setHex(0x8a949c);
               hemi.color.setHex(0x5c6a74); hemi.groundColor.setHex(0x1a1a18); }
  else { key.color.setHex(a.sun.color); hemi.color.setHex(a.hemi.sky);
         hemi.groundColor.setHex(a.hemi.ground); }
  key.intensity = a.sun.i * w.sun_mul;
  hemi.intensity = a.hemi.i * w.hemi_mul;
  mat.win.emissiveIntensity = w.window_glow;
  rain.visible = w.rain > 0 && !reduced;
  rainRate = w.rain;
  ambSync({ ...a.amb, wind: (a.amb.wind ?? .2) + w.wind,
            ...(w.thunder ? { thunder: true } : {}) });
  faunaWeather(w);
}

/* ----------------------------------------------------------- fauna -----
   The animals that belong in a working yard, declared per campus in the
   world registry and built here out of the same shared boxes as
   everything else. Ambience, not a survey: common names, schematic
   bodies, authored paths. Nothing is drawn from any photograph and no
   sighting, count or species record is claimed - see D.world.honesty.fauna.

   They cost almost nothing (three or four shared-geometry meshes each),
   they are the only moving thing on an idle campus, and they give the
   scene something the buildings cannot: a sense of scale that a learner
   reads without being told. */
const FAUNA = D.world.fauna;
let faunaGroup = null, faunaBodies = [], faunaGust = 0;

function faunaBody(f) {
  const g = new THREE.Group();
  const col = new THREE.Color(f.color), acc = new THREE.Color(f.accent);
  const mBody = new THREE.MeshStandardMaterial({ color: col, roughness: .85 });
  const mAcc = new THREE.MeshStandardMaterial({ color: acc, roughness: .8 });
  const sp = f.span_m;
  if (f.body === 'bird' || f.body === 'wader') {
    const torso = new THREE.Mesh(boxGeo(sp * .3, sp * .2, sp * .5), mBody);
    g.add(torso);
    const wingL = new THREE.Mesh(boxGeo(sp * .48, sp * .05, sp * .26), mBody);
    const wingR = wingL.clone();
    wingL.position.set(-sp * .36, 0, 0); wingR.position.set(sp * .36, 0, 0);
    g.add(wingL, wingR);
    const head = new THREE.Mesh(boxGeo(sp * .16, sp * .16, sp * .2), mAcc);
    head.position.set(0, sp * .12, sp * .32); g.add(head);
    if (f.body === 'wader') {              // long neck, long legs, standing
      const neck = new THREE.Mesh(boxGeo(sp * .07, sp * .5, sp * .07), mBody);
      neck.position.set(0, sp * .34, sp * .2); g.add(neck);
      head.position.set(0, sp * .6, sp * .24);
      for (const sx of [-1, 1]) {
        const leg = new THREE.Mesh(boxGeo(sp * .05, sp * .55, sp * .05), mAcc);
        leg.position.set(sx * sp * .07, -sp * .34, 0); g.add(leg);
      }
      wingL.visible = wingR.visible = false;
    }
    g.userData.wings = [wingL, wingR];
  } else {                                  // quadruped: the yard dog
    const torso = new THREE.Mesh(boxGeo(sp * .26, sp * .28, sp * .62), mBody);
    torso.position.y = sp * .42; g.add(torso);
    const head = new THREE.Mesh(boxGeo(sp * .2, sp * .2, sp * .24), mAcc);
    head.position.set(0, sp * .58, sp * .38); g.add(head);
    const tail = new THREE.Mesh(boxGeo(sp * .06, sp * .06, sp * .3), mAcc);
    tail.position.set(0, sp * .52, -sp * .42); tail.rotation.x = -.5;
    g.add(tail);
    const legs = [];
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
      const leg = new THREE.Mesh(boxGeo(sp * .07, sp * .42, sp * .07), mBody);
      leg.position.set(sx * sp * .1, sp * .21, sz * sp * .22);
      g.add(leg); legs.push(leg);
    }
    g.userData.legs = legs; g.userData.tail = tail;
  }
  return g;
}

function clearFauna() {
  if (!faunaGroup) return;
  faunaGroup.parent?.remove(faunaGroup);
  disposeOf(faunaGroup);
  faunaGroup = null; faunaBodies = [];
}

// birds fly at a groundspeed: angular rate is scaled by radius so a
// bigger campus doesn't make them cover more ground per second
const FAUNA_REF_R = 84;
function spawnFauna(campusKey, radius) {
  clearFauna();
  if (reduced) return;                      // stillness for those who ask
  faunaGroup = new THREE.Group();
  faunaGroup.name = 'tc-fauna';
  const rnd = seeded(0xFA0A + (campusKey || '').length * 131);
  const angK = FAUNA_REF_R / radius;
  for (const [fk, f] of Object.entries(FAUNA)) {
    if (!f.campuses.includes(campusKey)) continue;
    for (let i = 0; i < f.flock; i++) {
      const b = faunaBody(f);
      b.userData.kind = fk;
      b.userData.motion = f.motion;
      b.userData.speed = f.speed * (.8 + rnd() * .45) * angK;
      b.userData.phase = rnd() * Math.PI * 2;
      b.userData.rad = radius * (.3 + rnd() * .55);
      b.userData.h = f.height_m[0]
        + rnd() * (f.height_m[1] - f.height_m[0]);
      b.userData.flap = 4 + rnd() * 3;
      b.userData.span = f.span_m;
      faunaGroup.add(b); faunaBodies.push(b);
    }
  }
  scene.add(faunaGroup);
}

// weather reaches the animals too: they fly lower and faster in wind, and
// in a storm they are simply not out
function faunaWeather(w) {
  faunaGust = w.wind;
  if (faunaGroup) faunaGroup.visible = w.rain < .9;
}

function faunaStep(t, dt) {
  if (!faunaGroup || !faunaGroup.visible) return;
  for (const b of faunaBodies) {
    const u = b.userData;
    const sp = u.speed * (1 + faunaGust * .6);
    const a = u.phase + t * sp * .22;
    if (u.motion === 'circuit' || u.motion === 'glide') {
      const wob = u.motion === 'glide' ? 0 : Math.sin(t * sp + u.phase) * 2.2;
      b.position.set(Math.cos(a) * u.rad, u.h + wob - faunaGust * 3,
        Math.sin(a) * u.rad);
      b.rotation.y = -a + Math.PI / 2;
      b.rotation.z = Math.sin(t * sp * .7 + u.phase) * .18;
      const fl = u.motion === 'glide'
        ? Math.sin(t * 1.1 + u.phase) * .12          // pelicans mostly glide
        : Math.sin(t * u.flap + u.phase) * .85;
      if (u.wings) { u.wings[0].rotation.z = fl; u.wings[1].rotation.z = -fl; }
    } else if (u.motion === 'hop') {
      const hop = Math.max(0, Math.sin(t * 2.4 + u.phase)) * .35;
      b.position.set(Math.cos(a * .6) * u.rad, hop,
        Math.sin(a * .6) * u.rad);
      b.rotation.y = -a * .6 + Math.PI / 2;
      if (u.wings) { const f2 = hop * 1.6;
        u.wings[0].rotation.z = f2; u.wings[1].rotation.z = -f2; }
    } else if (u.motion === 'perch') {
      b.position.set(Math.cos(u.phase) * u.rad, 0, Math.sin(u.phase) * u.rad);
      b.rotation.y = u.phase * 2;
      b.position.y = Math.sin(t * .6 + u.phase) * .03;   // barely, breathing
    } else {                                  // patrol: the yard dog, trotting
      const seg = (t * sp * .1 + u.phase) % (Math.PI * 2);
      b.position.set(Math.cos(seg) * u.rad, 0, Math.sin(seg) * u.rad);
      b.rotation.y = -seg + Math.PI / 2;
      if (u.legs) u.legs.forEach((l, i) => {
        l.rotation.x = Math.sin(t * 7 * sp + i * 1.7) * .5;
      });
      if (u.tail) u.tail.rotation.y = Math.sin(t * 4) * .35;
    }
  }
}

// the rain: one Points cloud recycled over the camera target in storms
const rain = (() => {
  const N = 900, pos = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) {
    pos[i * 3] = (Math.random() - .5) * 220;
    pos[i * 3 + 1] = Math.random() * 90;
    pos[i * 3 + 2] = (Math.random() - .5) * 220;
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const pts = new THREE.Points(geo, new THREE.PointsMaterial({
    color: 0xaac2d2, size: .8, transparent: true, opacity: .6 }));
  pts.visible = false; pts.frustumCulled = false;
  return pts;
})();
scene.add(rain);
let rainRate = 0;
function rainStep(dt) {
  if (!rain.visible) return;
  // rain is a rate, not a switch: a shower falls slower and thinner than
  // a storm, from the same one particle cloud
  rain.material.opacity = .22 + rainRate * .42;
  rain.material.size = .5 + rainRate * .45;
  const p = rain.geometry.attributes.position.array;
  const cx2 = controls.target.x, cz2 = controls.target.z;
  for (let i = 0; i < p.length; i += 3) {
    p[i + 1] -= (28 + rainRate * 34) * dt;
    if (p[i + 1] < 0) {
      p[i + 1] = 80 + Math.random() * 10;
      p[i] = cx2 + (Math.random() - .5) * 220;
      p[i + 2] = cz2 + (Math.random() - .5) * 220;
    }
  }
  rain.geometry.attributes.position.needsUpdate = true;
}
// re-apply the current view's atmosphere and fog band (the night toggle)
function reAtmos() {
  if (view === 'campus') {
    applyAtmos(campusKey);
    scene.fog.near = 320 * fogMul; scene.fog.far = 1280 * fogMul;
  } else if (view === 'hall') {
    applyAtmos(campusKey);
    scene.fog.near = 70 * fogMul; scene.fog.far = 170 * fogMul;
  } else if (view === 'sim') {
    applyAtmos(campusKey);
    scene.fog.near = 90 * fogMul; scene.fog.far = 260 * fogMul;
  } else applyAtmos(null);
}

/* Ambient sound beds - synthesized like everything else (no recordings):
   looped filtered noise for the wind, sparse gull chirps, a rare harbor
   horn, the NOLA insect shimmer and far thunder. All ride the master
   gain, so the one mute silences the world too. */
let ambNodes = [], ambTimers = [], ambCfg = null;
function ambStop() {
  for (const t of ambTimers) clearTimeout(t);
  for (const n of ambNodes) { try { n.stop?.(); } catch (e) {} n.disconnect?.(); }
  ambTimers = []; ambNodes = [];
}
function noiseBuf(secs = 2) {
  const n = Math.floor(ac.sampleRate * secs);
  const buf = ac.createBuffer(1, n, ac.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
  return buf;
}
function ambLoop(fn, lo, hi) {
  const tick = () => { fn(); ambTimers.push(setTimeout(tick,
    (lo + Math.random() * (hi - lo)) * 1000)); };
  ambTimers.push(setTimeout(tick, (lo + Math.random() * (hi - lo)) * 500));
}
function ambSync(cfg) {
  ambCfg = cfg ?? ambCfg;
  if (!ac || !ambCfg) return;
  ambStop();
  const a = ambCfg;
  if (a.wind) {
    const src = ac.createBufferSource(); src.buffer = noiseBuf(); src.loop = true;
    const f = ac.createBiquadFilter(); f.type = 'lowpass';
    f.frequency.value = 240 + 360 * a.wind;
    const g = ac.createGain(); g.gain.value = .012 + .04 * a.wind;
    src.connect(f); f.connect(g); g.connect(master); src.start();
    ambNodes.push(src, f, g);
  }
  if (a.insects) {
    const src = ac.createBufferSource(); src.buffer = noiseBuf(); src.loop = true;
    const f = ac.createBiquadFilter(); f.type = 'bandpass';
    f.frequency.value = 4800; f.Q.value = 9;
    const g = ac.createGain(); g.gain.value = .011;
    const lfo = ac.createOscillator(), lg = ac.createGain();
    lfo.frequency.value = .6; lg.gain.value = .006;
    lfo.connect(lg); lg.connect(g.gain); lfo.start();
    src.connect(f); f.connect(g); g.connect(master); src.start();
    ambNodes.push(src, f, g, lfo, lg);
  }
  if (a.gulls) ambLoop(() => {
    const n = 2 + Math.floor(Math.random() * 2);
    for (let i = 0; i < n; i++)
      setTimeout(() => blip(1500 - i * 160, 950, .22, 'triangle', .04), i * 260);
  }, 8, 18);
  if (a.harbor) ambLoop(() => blip(98, 94, 1.6, 'square', .035), 28, 55);
  if (a.thunder) ambLoop(() => {
    const nb = ac.createBufferSource(); nb.buffer = noiseBuf(3);
    const f = ac.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 110;
    const g = ac.createGain(); g.gain.setValueAtTime(.12, ac.currentTime);
    g.gain.exponentialRampToValueAtTime(.001, ac.currentTime + 2.8);
    nb.connect(f); f.connect(g); g.connect(master); nb.start();
    ambNodes.push(nb, f, g);
  }, 35, 75);
}
// the world gets its voice on the first gesture the browser allows
renderer.domElement.addEventListener('pointerdown', () => {
  acEnsure(); ambSync(ambCfg);
}, { once: true });

// the drawn ground's outer edge - sized to clear the campus dressing at
// the scale below, so nothing floats past it
const GROUND_R = 520;
// ground: dark apron with a faint work grid
const ground = new THREE.Mesh(
  new THREE.CircleGeometry(GROUND_R, 64),
  groundMat('asphalt', 0x8f9698, 68));
// a campus can stand on a different surface from its neighbour, and the
// atmosphere record is where that is said
function setGroundSurface(campusKey) {
  const a = ATMOS[campusKey] ?? DEF_ATMOS;
  ground.material.dispose();
  ground.material = groundMat(a.ground, 0x8f9698, 68);
}
ground.rotation.x = -Math.PI/2; ground.receiveShadow = true;
scene.add(ground);
const grid = new THREE.GridHelper(GROUND_R * 2, 180, 0x28353A, 0x1b2427);
grid.position.y = .02; scene.add(grid);

const mat = {
  slab:  new THREE.MeshStandardMaterial({ map: concreteTex, color: 0xb8bdbd, roughness: .9 }),
  win:   new THREE.MeshStandardMaterial({ color: 0x0b0f11,
           emissive: 0xffc27a, emissiveIntensity: .5, roughness: .4 }),
  // open water, rough grass, plant-yard gravel and stockpile sand all come
  // straight off their recipes in the world registry - colour map and
  // normal map both generated in this browser, never loaded
  water: groundMat('water', 0x8fb4c8, 10),
  grass: groundMat('grass'),
  gravel: groundMat('gravel'),
  sand:  groundMat('sand'),
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

/* ------------------------------------------------------- the signs -----
   Every word in this world is on a sign, and a sign should be readable
   before it is read. Its SHAPE says what kind of thing it marks - a
   speech bubble is somebody who will talk to you, a tab with a pointer is
   a place you can enter, a pin on a stem is somewhere real out there, a
   chip is something you can open, a readout is a number a machine
   measured. Its COLOUR says whose it is and where it came from: a hall
   wears its district's own hue, a RECORDED place wears a solid accent, a
   SCHEMATIC one is drawn dashed and says so. Its TYPE says rank: display
   for names, sans for the line under them, mono for anything measured.

   All of that is declared in the label registry, never here. */
const LBL = D.labels;
const LKIND = LBL.kinds, LPAL = LBL.palette, LTYPE = LBL.type;
const LFOCUS = LBL.focus;
let labelSet = [];

const lblFace = (f) => LTYPE[f] ?? LTYPE.display;
const lblAccent = (kind, hue) => kind.accent === 'district'
  ? (hue == null ? LPAL.mark : `hsl(${hue} 58% 62%)`)
  : (LPAL[kind.accent] ?? LPAL.mark);

// the ten plates, drawn on the 2D context; `case` per shape so the
// registry and the page cannot drift apart without the build noticing
function labelShape(g, shape, w, h, accent, dashed) {
  const S = LBL.shapes[shape] ?? LBL.shapes.plate;
  const r = Math.min(S.radius, h / 2);
  const body = h - (S.tail ? 14 : 0) - (S.stem ? 22 : 0);
  g.save();
  g.shadowColor = 'rgba(0,0,0,.55)'; g.shadowBlur = 10; g.shadowOffsetY = 3;
  g.fillStyle = LPAL.plate;
  switch (shape) {
    case 'speech':
      g.beginPath(); g.roundRect(0, 0, w, body, r); g.fill();
      g.beginPath();                       // the tail, off to the left
      g.moveTo(26, body - 1); g.lineTo(44, body - 1); g.lineTo(30, body + 14);
      g.closePath(); g.fill();
      break;
    case 'tab':
      g.beginPath(); g.roundRect(0, 0, w, body, r); g.fill();
      g.beginPath();                       // the pointer, centred
      g.moveTo(w / 2 - 11, body - 1); g.lineTo(w / 2 + 11, body - 1);
      g.lineTo(w / 2, body + 14); g.closePath(); g.fill();
      break;
    case 'chip':
      g.beginPath(); g.roundRect(0, 0, w, body, body / 2); g.fill();
      break;
    case 'plate':
      g.beginPath(); g.roundRect(0, 0, w, body, r); g.fill();
      break;
    case 'pin':
      g.beginPath(); g.roundRect(0, 0, w, body, r); g.fill();
      g.shadowBlur = 0;
      g.strokeStyle = accent; g.lineWidth = 3;
      g.beginPath(); g.moveTo(w / 2, body); g.lineTo(w / 2, body + 15);
      g.stroke();
      g.fillStyle = accent;
      g.beginPath(); g.arc(w / 2, body + 18, 5, 0, 7); g.fill();
      break;
    case 'banner':
      g.beginPath(); g.roundRect(0, 0, w, body, r); g.fill();
      break;
    case 'marquee':
      g.beginPath(); g.roundRect(0, 0, w, body, r); g.fill();
      g.shadowBlur = 0;
      g.fillStyle = accent; g.fillRect(18, 12, w - 36, 3);
      break;
    case 'ribbon':
      g.beginPath();
      g.moveTo(14, 0); g.lineTo(w, 0); g.lineTo(w - 14, body); g.lineTo(0, body);
      g.closePath(); g.fill();
      break;
    case 'ghost':
      break;                               // no plate at all, by design
    case 'readout':
      g.fillStyle = 'rgba(6,10,12,.9)';
      g.beginPath(); g.roundRect(0, 0, w, body, r); g.fill();
      g.shadowBlur = 0;
      g.strokeStyle = accent; g.lineWidth = 2;
      g.beginPath(); g.roundRect(1, 1, w - 2, body - 2, r); g.stroke();
      break;
  }
  g.restore();
  // the accent: a stripe for the wide shapes, a dashed outline where the
  // registry says the thing behind the sign is SCHEMATIC
  if (shape === 'banner' || shape === 'plate') {
    g.fillStyle = accent;
    g.fillRect(0, 0, shape === 'banner' ? 8 : 5, body);
  }
  if (dashed) {
    g.save();
    g.setLineDash([9, 7]); g.strokeStyle = accent; g.lineWidth = 2;
    g.beginPath(); g.roundRect(1, 1, w - 2, body - 2, r); g.stroke();
    g.restore();
  }
  return body;
}

/* label(text, sub, scale, opts)
   opts: { kind, hue, badge }  - kind names a row of the label registry;
   hue is the district's, for the kinds whose accent is 'district'. */
function label(text, sub, scale = 1, opts = {}) {
  const kindId = opts.kind && LKIND[opts.kind] ? opts.kind : 'room';
  const kind = LKIND[kindId];
  const shape = kind.shape;
  const accent = lblAccent(kind, opts.hue);
  const marquee = shape === 'marquee';
  const dpr = Math.min(2, devicePixelRatio || 1);

  const c = document.createElement('canvas');
  const g = c.getContext('2d');
  const titlePx = marquee ? LTYPE.title_px + 4
    : shape === 'chip' ? LTYPE.chip_px : LTYPE.title_px;
  const titleFont = (kind.face === 'mono' ? '600 ' : '600 ')
    + titlePx + 'px ' + lblFace(kind.face);
  g.font = titleFont;
  const title = marquee ? text.toUpperCase() : text;
  const track = marquee ? LTYPE.tracking_marquee : 0;
  const tw = g.measureText(title).width + track * title.length;
  let sw = 0;
  if (sub) {
    g.font = LTYPE.sub_px + 'px ' + lblFace(kind.face === 'mono' ? 'mono' : 'body');
    sw = g.measureText(sub).width;
  }
  const padX = shape === 'chip' ? 26 : shape === 'ghost' ? 6 : 22;
  const w = Math.max(tw, sw, shape === 'chip' ? 48 : 110) + padX * 2
    + (shape === 'plate' || shape === 'banner' ? 10 : 0);
  const bodyH = (sub ? 104 : shape === 'chip' ? 54 : 68)
    + (marquee ? 14 : 0);
  const h = bodyH + (LBL.shapes[shape].tail ? 14 : 0)
    + (LBL.shapes[shape].stem ? 22 : 0);

  c.width = Math.ceil(w * dpr); c.height = Math.ceil(h * dpr);
  g.scale(dpr, dpr);
  const body = labelShape(g, shape, w, h, accent, !!kind.dashed);

  const left = padX + (shape === 'plate' ? 5 : shape === 'banner' ? 8 : 0);
  const baseline = sub ? (marquee ? 62 : 52) : body / 2 + titlePx * .35;
  g.save();
  g.shadowColor = 'rgba(0,0,0,.75)'; g.shadowBlur = 6;
  g.fillStyle = shape === 'readout' ? accent : LPAL.ink;
  g.font = titleFont;
  if (track) {                              // letter-spaced caps, by hand
    let x = left;
    for (const ch of title) { g.fillText(ch, x, baseline);
      x += g.measureText(ch).width + track; }
  } else g.fillText(title, left, baseline);
  if (sub) {
    g.fillStyle = shape === 'ghost' ? LPAL.ink : LPAL.muted;
    g.font = LTYPE.sub_px + 'px '
      + lblFace(kind.face === 'mono' ? 'mono' : 'body');
    g.fillText(sub, left, baseline + 36);
  }
  g.restore();

  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({
    map: tex, transparent: true, depthTest: false }));
  sp.scale.set(w / 90 * scale, h / 90 * scale, 1);
  sp.userData.lbl = { kind: kindId, base: sp.scale.clone(), baseY: null,
                      accent, focus: 0, hide: kind.hide_beyond_m || 0,
                      floor: kind.min_focus };
  labelSet.push(sp);
  return sp;
}

/* ---- and how a sign reads the view ------------------------------------
   Each frame every live label is scored on the angle between the view
   direction and the label (inside the declared cone) and again on
   distance; the two multiply. The score drives opacity, size and tint,
   eased rather than snapped so nothing flickers as the head turns. The
   single most centred label within reach is the FOCUS: it takes the
   accent tint and lifts, so a learner can see what they are about to act
   on without a cursor - which is what makes this work in a headset, where
   there is no cursor to have.

   This is presentation and nothing else: no label is a score, none gates
   anything, and no grader reads any of it. */
let labelFocus = null;
const _lblFwd = new THREE.Vector3(), _lblTo = new THREE.Vector3();
const _lblPos = new THREE.Vector3();
function labelStep(dt) {
  if (!labelSet.length) return;
  let live = 0, best = null, bestScore = 0;
  camera.getWorldDirection(_lblFwd);
  const cos = Math.cos(LFOCUS.cone_deg * Math.PI / 180);
  const ease = reduced ? 1 : Math.min(1, (dt || .016) * LFOCUS.ease);
  const ref = Math.max(LFOCUS.near_full_m,
    camera.position.distanceTo(controls.target));
  const tanHalfFov = Math.tan(camera.fov * Math.PI / 360);
  for (const sp of labelSet) {
    if (!sp.parent) continue;               // its group was disposed
    labelSet[live++] = sp;
    const u = sp.userData.lbl;
    sp.getWorldPosition(_lblPos);
    const dist = _lblPos.distanceTo(camera.position);
    if (u.hide && dist > u.hide) { sp.visible = false; continue; }
    _lblTo.copy(_lblPos).sub(camera.position).normalize();
    const dot = _lblTo.dot(_lblFwd);
    // angle: 1 dead ahead, 0 at the edge of the cone and beyond
    const ang = dot <= cos ? 0 : (dot - cos) / (1 - cos);
    // distance, judged RELATIVE to how far out the view is: a sign 200 m
    // off is far when you are walking and near when you are looking at
    // the whole campus from above, so the reference is the camera's own
    // distance to what it is looking at
    const rel = dist / ref;
    const near = rel <= LFOCUS.fade_from_rel ? 1
      : rel >= LFOCUS.fade_to_rel ? 0
      : 1 - (rel - LFOCUS.fade_from_rel)
          / (LFOCUS.fade_to_rel - LFOCUS.fade_from_rel);
    const want = ang * near;
    u.focus += (want - u.focus) * ease;
    const lit = Math.max(u.floor, LFOCUS.floor) ;
    sp.visible = near > .01;
    sp.material.opacity = reduced ? 1
      : Math.min(1, lit + (1 - lit) * u.focus) * (.25 + .75 * near);
    // A world-space sign grows without limit as you walk up to it. Clamp
    // what the eye actually gets: never more than max_frac of the
    // viewport's height, never less than min_frac while it is in range.
    const grow = 1 + LFOCUS.grow * u.focus;
    let h = u.base.y * grow;
    const span = 2 * dist * tanHalfFov;           // world height of the view
    const lo = span * LFOCUS.screen.min_frac, hi = span * LFOCUS.screen.max_frac;
    const k2 = h > hi ? hi / h : h < lo ? lo / h : 1;
    sp.scale.set(u.base.x * grow * k2, h * k2, 1);
    if (want > bestScore && rel < LFOCUS.fade_from_rel) {
      bestScore = want; best = sp;
    }
  }
  labelSet.length = live;
  if (best !== labelFocus) {
    if (labelFocus) {
      labelFocus.material.color.setHex(0xffffff);
      const u = labelFocus.userData.lbl;
      if (u.baseY !== null) { labelFocus.position.y = u.baseY; u.baseY = null; }
    }
    labelFocus = best;
    if (best) {
      best.material.color.set(LPAL.mark);
      const u = best.userData.lbl;
      u.baseY = best.position.y;
      best.position.y += LFOCUS.lift_m;
    }
  }
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

/* The geometry cache: identical box dimensions share ONE BufferGeometry
   (a hall's fence posts alone repeat a size dozens of times). Shared
   geometries are marked and never disposed on teardown - disposeOf()
   below is the one legal teardown path. */
const geoCache = new Map();
function boxGeo(w, h, d) {
  const k = w + '|' + h + '|' + d;
  let g2 = geoCache.get(k);
  if (!g2) {
    g2 = new THREE.BoxGeometry(w, h, d);
    g2.userData.shared = true;
    geoCache.set(k, g2);
  }
  return g2;
}
function disposeOf(root) {
  root.traverse((o) => {
    if (o.geometry && !o.geometry.userData?.shared) o.geometry.dispose();
  });
}
function box(w, h, d, m, x, y, z, group, shadow = true) {
  const b = new THREE.Mesh(boxGeo(w, h, d), m);
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
let cribCount = 0;

/* ------------------------------------------------------- the tool crib --- */
// The toolroom registry hangs a district's twelve tools on a pegboard in
// every hall's tools room. Shapes are schematic render kinds the registry
// declares; clicking the board opens the crib and its deterministic drill.
function toolMesh(tl) {
  const m = new THREE.MeshStandardMaterial({
    color: new THREE.Color().setHSL(tl.hue / 360, .5, .55),
    roughness: .45, metalness: .35 });
  let geo;
  switch (tl.shape) {
    case 'bar': geo = boxGeo(.05, .46, .05); break;
    case 'blade': geo = boxGeo(.02, .34, .16); break;
    case 'cyl': geo = new THREE.CylinderGeometry(.035, .035, .4, 8); break;
    case 'cone': geo = new THREE.ConeGeometry(.07, .3, 8); break;
    case 'meter': geo = boxGeo(.09, .26, .18); break;
    case 'case': geo = boxGeo(.12, .2, .3); break;
    case 'coil': geo = new THREE.TorusGeometry(.13, .035, 8, 14); break;
    case 'hook': geo = new THREE.TorusGeometry(.1, .04, 8, 12, Math.PI * 1.5); break;
    default: {                                   // wrench: shaft + open head
      const grp = new THREE.Group();
      const bar = new THREE.Mesh(boxGeo(.045, .38, .045), m);
      const head = new THREE.Mesh(boxGeo(.05, .09, .14), m);
      head.position.y = .21; grp.add(bar, head);
      grp.traverse((o) => { if (o.isMesh) o.castShadow = true; });
      return grp;
    }
  }
  const mesh = new THREE.Mesh(geo, m); mesh.castShadow = true;
  return mesh;
}
function buildCrib(h, rx, rz, rw, rd) {
  const dk = h.district, crib = D.tools.cribs[dk];
  const bw = Math.max(2.4, Math.min(rd - 1.2, 4.2));
  const bx = rx + rw / 2 - .32;
  const board = box(.1, 1.7, bw, mat.part, bx, 1.5, rz, hallGroup);
  board.userData.crib = dk;
  beacons.push(board);
  box(.06, .08, bw, mat.post, bx - .06, 2.38, rz, hallGroup, false);  // rail
  crib.tools.forEach((tl, i) => {
    const row = i % 2, col = (i - row) / 2;
    const tm = toolMesh(tl);
    tm.position.set(bx - .16, row ? 1.02 : 1.9,
      rz - bw / 2 + (col + .5) * bw / 6);
    tm.rotation.x = .1;
    hallGroup.add(tm);
  });
  // the crib chest below the board, and its check-out counter
  const chest = box(.8, .62, 1.1,
    new THREE.MeshStandardMaterial({ color: 0x8a2f22, roughness: .6 }),
    bx - .6, .69, rz - bw / 2 - .2, hallGroup);
  chest.userData.crib = dk;
  beacons.push(chest);
  box(.84, .03, 1.14, mat.metal, bx - .6, 1.02, rz - bw / 2 - .2, hallGroup, false);
  const lab = label(crib.name, D.tools.drill.name + ' · ' + crib.tools.length,
    .5, { kind: 'crib' });
  lab.position.set(bx - .6, 2.85, rz); hallGroup.add(lab);
  cribCount++;
}

function buildHall(sg) {
  if (hallGroup) { scene.remove(hallGroup); disposeOf(hallGroup); }
  hallGroup = new THREE.Group(); beacons = []; floors = []; roomRects = []; curRoom = null;
  hallGroup.name = 'tc-hall-' + sg;
  cribCount = 0;
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
  const fascia = new THREE.Mesh(boxGeo(W + .8, .55, .5),
    new THREE.MeshStandardMaterial({
      color: new THREE.Color().setHSL(hue/360, .55, .5), roughness: .5 }));
  fascia.position.set(0, 3.6, cz(0)); fascia.castShadow = true;
  hallGroup.add(fascia);
  const sign = label(h.name, D.i18n[loc].districts[h.district], 1.35,
    { kind: 'hall', hue: D.districts[h.district].hue });
  sign.position.set(0, 5.1, cz(0)); hallGroup.add(sign);

  // roof trusses across the span, and lit strips along the side walls
  for (let tz = 4; tz < DEP - 1; tz += 6) {
    box(W - .6, .18, .5, mat.metal, 0, 3.05, cz(tz), hallGroup, false);
    const lamp = new THREE.Mesh(boxGeo(1.6, .1, .5), mat.win);
    lamp.position.set(0, 2.9, cz(tz)); hallGroup.add(lamp);
  }
  for (const wx of [cx(0) + .18, cx(W) - .18]) {
    const strip = new THREE.Mesh(boxGeo(.06, .55, DEP * .8), mat.win);
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
    const floor = new THREE.Mesh(boxGeo(rw - .3, .06, rd - .3),
      new THREE.MeshStandardMaterial({ map: ftex,
        roughness: fin.roughness, metalness: fin.metalness }));
    floor.position.set(rx, .38, rz); floor.receiveShadow = true;
    floor.name = 'room-' + r.strand;
    floor.userData.room = r.label;
    hallGroup.add(floor); floors.push(floor);
    roomRects.push({ x0: r.x * U - W/2, x1: r.x * U - W/2 + rw,
                     z0: r.y * U - DEP/2, z1: r.y * U - DEP/2 + rd,
                     label: r.label, strand: r.strand });
    // safety rooms carry a hazard-stripe threshold at the doorway
    if (r.strand === 'safety') {
      const stripe = new THREE.Mesh(boxGeo(Math.min(rw-.6,2.4), .07, .5),
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
      const fl = label(fx, null, .34, { kind: 'fixture' });
      fl.position.set(bx, 1.85, bz); hallGroup.add(fl);
    });
    box(rw, 1.1, .12, mat.part, rx, .9, rz - rd/2, hallGroup);
    box(rw, 1.1, .12, mat.part, rx, .9, rz + rd/2, hallGroup);
    box(.12, 1.1, rd, mat.part, rx - rw/2, .9, rz, hallGroup);
    box(.12, 1.1, rd, mat.part, rx + rw/2, .9, rz, hallGroup);
    const lab = label(r.label, D.i18n[loc].strands[r.strand], .55,
      { kind: 'room' });
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

    // the district's tool crib hangs in the tools room
    if (r.strand === 'tools') buildCrib(h, rx, rz, rw, rd);
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
  clearAdvisors();
  clearFauna();
  spawnHallAdvisors(h, W, DEP);
  scene.add(hallGroup);

  document.getElementById('hname').textContent = h.name + scoreChip();
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

/* Buildings merge their decoration into ONE mesh per material - band,
   trims, window strips, door and roofline become three draw calls
   instead of a dozen, per building, across the whole campus. The main
   box stays its own mesh: it is the raycast target the hover and click
   handlers read. Merged geometries are per-building (not shared), so
   disposeOf() frees them on rebuild. */
const hueMatCache = new Map();
function hueMatOf(hue) {
  let m2 = hueMatCache.get(hue);
  if (!m2) {
    m2 = new THREE.MeshStandardMaterial({
      color: new THREE.Color().setHSL(hue / 360, .5, .45), roughness: .6 });
    hueMatCache.set(hue, m2);
  }
  return m2;
}
function building(h, style, g) {   // built at the local origin, door toward -z
  const dep = Math.max(h.depth, 5), wid = 12;
  const hgt = 6 + (h.depth % 3) * .7;
  const bld = box(wid, hgt, dep, mat.wall, 0, hgt / 2, 0, g);
  bld.userData.slug = h.slug;
  const parts = new Map();           // material -> [transformed geometries]
  const add = (m2, w, hh, d2, x, y, z, rz = 0) => {
    const ge = new THREE.BoxGeometry(w, hh, d2);
    const mx = new THREE.Matrix4().makeRotationZ(rz).setPosition(x, y, z);
    ge.applyMatrix4(mx);
    (parts.get(m2) ?? parts.set(m2, []).get(m2)).push(ge);
  };
  const hueMat = hueMatOf(D.districts[h.district].hue);
  add(hueMat, wid + .4, .9, dep + .4, 0, hgt - .2, 0);
  for (const [tx, tz] of [[-wid/2, -dep/2], [wid/2, -dep/2],
                          [-wid/2, dep/2], [wid/2, dep/2]])
    add(hueMat, .5, hgt, .5, tx, hgt / 2, tz);
  for (const zz of [-dep/2 - .03, dep/2 + .03])
    add(mat.win, wid * .78, .7, .06, 0, hgt * .55, zz);
  add(mat.part, 1.6, 2.4, .1, 0, 1.2, -dep/2 - .06);
  if (style === 'saw') {              // industrial sawtooth roofline
    for (let sx = -wid/2 + 2; sx < wid/2 - .5; sx += 4)
      add(mat.metal, 3.2, 1.5, dep - .6, sx, hgt + .55, 0, .42);
  } else if (style === 'gable') {     // pitched pair
    add(mat.part, wid * .6, .5, dep + .3, -wid * .24, hgt + 1.1, 0, .48);
    add(mat.part, wid * .6, .5, dep + .3, wid * .24, hgt + 1.1, 0, -.48);
  } else {                            // flat: parapet already, rooftop unit
    add(mat.metal, 1.6, .8, 1.2, wid * .22, hgt + .4, dep * .15);
  }
  for (const [m2, list] of parts) {
    const merged = mergeGeometries(list);
    list.forEach((ge) => ge.dispose());
    const mesh = new THREE.Mesh(merged, m2);
    mesh.castShadow = true; mesh.receiveShadow = true;
    g.add(mesh);
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

/* Lane dashes accumulate and merge into ONE mesh per campus build -
   they were the largest single mesh swarm on the board. */
let dashAcc = [];
function dashGeo(w, d2, x, z) {
  const ge = new THREE.BoxGeometry(w, .02, d2);
  ge.applyMatrix4(new THREE.Matrix4().setPosition(x, .09, z));
  dashAcc.push(ge);
}
function dashesU(u0, u1, v, g) {
  for (let u = u0 + 2; u < u1 - 2; u += 4) dashGeo(1.6, .16, u, v);
}
function dashesV(v0, v1, u, g) {
  for (let v = v0 + 2; v < v1 - 2; v += 4) dashGeo(.16, 1.6, u, v);
}
function flushDashes(g) {
  if (!dashAcc.length) return;
  const merged = mergeGeometries(dashAcc);
  dashAcc.forEach((ge) => ge.dispose());
  dashAcc = [];
  const mesh = new THREE.Mesh(merged, mat.paint);
  mesh.receiveShadow = true;
  g.add(mesh);
}

/* ------------------------------ campus dressing, keyed by campus slug --- */
function dressCampus(key, g, R) {
  if (key === 'treasure-island') {
    // the island: a bay ring beyond the ground's edge and a flag over the plaza
    const bay = new THREE.Mesh(new THREE.RingGeometry(GROUND_R - 2, GROUND_R + 760, 64), mat.water);
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
  if (key === 'houston') {
    // the hub has no district ring to dress a road frontage against, so
    // its skyline stands free on the green: a refinery silhouette on the
    // horizon (tanks, a flare stack) rather than anything at the plaza -
    // a hub campus is a real place to stand, not an empty green circle
    const tankMat = new THREE.MeshStandardMaterial({ color: 0x7a8288, roughness: .85 });
    for (let i = 0; i < 6; i++) {
      const ang = i / 6 * Math.PI * 2 + .3, rad = R + 60 + (i % 2) * 22;
      const h = 9 + (i % 3) * 4;
      const t = new THREE.Mesh(new THREE.CylinderGeometry(6, 6, h, 16), tankMat);
      t.position.set(Math.cos(ang) * rad, h / 2, Math.sin(ang) * rad);
      t.castShadow = true; g.add(t);
    }
    const stack = box(1.6, 34, 1.6, mat.metal, R + 92, 17, -R - 20, g);
    stack.castShadow = true;
    const flame = new THREE.Mesh(new THREE.ConeGeometry(1.4, 3.6, 8),
      new THREE.MeshBasicMaterial({ color: 0xff8a3c }));
    flame.position.set(R + 92, 35.6, -R - 20); g.add(flame);
    const chan = new THREE.Mesh(new THREE.PlaneGeometry(420, 90), mat.water);
    chan.rotation.x = -Math.PI / 2; chan.position.set(0, -.06, -(R + 130)); g.add(chan);
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
  const cl = label(t('chapters.hall'), '+' + D.chapters.hosted[key], 2,
    { kind: 'district' });
  cl.position.y = 12; pav.add(cl);
}
const CITY_S = 13;   // units per real kilometre in the city layer

/* An institution's panel: the RECORDED coordinate with a live-map link
   built from it, the authored blurb labelled as authored, and the union
   honesty line - hall addresses are not recorded, no local is named. */
/* elevation: USGS EPQS, one coordinate at a time, never bulk - adopted
   from Locator.X (src/sources.js, Apache-2.0). See D.elevation. */
const elevCache = {};
function elevationLookup(lat, lng, cb) {
  const key = lat.toFixed(5) + ',' + lng.toFixed(5);
  if (elevCache[key]) { cb(elevCache[key]); return; }
  const q = D.elevation.query;
  const url = D.elevation.endpoint + '?x=' + encodeURIComponent(lng)
    + '&y=' + encodeURIComponent(lat) + '&units=' + q.units
    + '&wkid=' + q.wkid + '&includeDate=' + q.includeDate;
  const done = (o) => { elevCache[key] = o; cb(o); };
  fetch(url).then((r) => r.text()).then((txt) => {
    let j = null;
    try { j = JSON.parse(txt); }
    catch (e) {
      done({ ok: false, why: 'The elevation service returned a non-JSON '
        + 'body for this point, which is how it reports a location '
        + 'outside its coverage.' });
      return;
    }
    const v = j && j.value;
    const num = typeof v === 'string' ? parseFloat(v) : v;
    if (num == null || !isFinite(num)) {
      done({ ok: false, why: 'No elevation is published for this coordinate.' });
      return;
    }
    done({ ok: true, feet: num,
      res: j.resolution == null ? null : j.resolution,
      acquired: (j.attributes && j.attributes.AcquisitionDate) || null });
  }).catch(() => done({ ok: false,
    why: 'The elevation service could not be reached from here.' }));
}

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
    <p id="elevRow">
      <button class="opt" id="elevGo" style="display:inline-block;width:auto;padding:5px 12px">
        ↕ Look up ground elevation</button></p>
    <p style="color:var(--muted);font-size:12px">coordinate: ${p.src}${
      p.bp ? `<br>description: ${p.bp}` : ''}</p>
    <p style="color:var(--muted);font-size:12px">${t('honesty.taxonomy')}</p>`;
  document.body.classList.add('open');
  const go = document.getElementById('elevGo');
  go?.addEventListener('click', () => {
    go.textContent = 'Looking up…'; go.disabled = true;
    elevationLookup(p.lat, p.lng, (o) => {
      const row = document.getElementById('elevRow');
      if (!row) return;
      row.innerHTML = o.ok
        ? `<span class="chip" style="border-color:var(--steel);color:var(--steel)">`
          + `${Math.round(o.feet)} ft</span>`
          + `<span style="color:var(--muted);font-size:12px"> USGS 3DEP ground `
          + `elevation at this coordinate${o.res ? ` · ${o.res} ft resolution` : ''}`
          + `${o.acquired ? ` · surveyed ${o.acquired}` : ''}. `
          + D.elevation.scope + `</span>`
        : `<span style="color:var(--crit);font-size:12px">${o.why}</span>`;
    });
  });
}
window.__tc3dPoi = openCityPoi;   // test hook
window.__tc3dElev = elevationLookup;   // test hook

// Two placement modes, both labelled with REAL kilometres: a compact city
// (New Orleans) lays its places at true linear offsets; a bay-scale region
// (the SF Bay, cities out to ~29 km) compresses distance the same way the
// network view does - true bearings, log-eased range - because a linear
// board that far would not be walkable. The i18n geo note states the deal.
let cityLog = false;
function cityPos(p) {
  const km = Math.hypot(p.e, p.n) || .001;
  if (!cityLog) return [p.e * CITY_S, -p.n * CITY_S];
  const r = 96 + 95 * Math.log10(1 + p.km);
  return [p.e / km * r, -p.n / km * r];
}
/* ------------------------------------------- orthoimagery ground ------- */
// The campus city layer places its RECORDED anchors at true east/north
// offsets from the campus point. This lays the authority's own public-
// domain orthoimagery underneath them at the SAME scale, georeferenced
// off the same record, so the picture and the points agree. Fetched in
// this browser from the cited service - never bundled - and a tile that
// does not arrive leaves the SCHEMATIC ground exactly as it was.
let satPlane = null, satState = 'off';
// an operator may point this at their own mirror of the same service;
// the harness uses it to prove the drawing path without the public one
const SAT_TILES = params.get('imagery') || null;
const SAT_Z = 14, SAT_SPAN = 3;          // a 3x3 tile block on the campus
const tileLat = (y, n) =>
  Math.atan(Math.sinh(Math.PI * (1 - 2 * y / n))) * 180 / Math.PI;
function satClear() {
  if (satPlane) { scene.remove(satPlane); satPlane.material.map?.dispose();
    satPlane.geometry.dispose(); satPlane = null; }
}
async function satGround() {
  if (satPlane) {                        // a second press puts it away
    satClear(); satState = 'off';
    document.getElementById('hint').textContent = t('hint.campus');
    return;
  }
  const pt = D.geo.campuses[campusKey];
  const n = 2 ** SAT_Z;
  const x0 = Math.floor((pt.lng + 180) / 360 * n) - 1;
  const la = pt.lat * Math.PI / 180;
  const y0 = Math.floor((1 - Math.log(Math.tan(la) + 1 / Math.cos(la))
    / Math.PI) / 2 * n) - 1;
  satState = 'loading';
  document.getElementById('hint').textContent =
    'Asking ' + D.imagery.authority + ' for orthoimagery...';
  const S = 256;
  const cv = document.createElement('canvas');
  cv.width = cv.height = S * SAT_SPAN;
  const cx2 = cv.getContext('2d');
  try {
    await Promise.all(Array.from({ length: SAT_SPAN * SAT_SPAN }, (_, i) => {
      const dx = i % SAT_SPAN, dy = (i - dx) / SAT_SPAN;
      const url = (SAT_TILES ?? D.imagery.tiles).replace('{z}', SAT_Z)
        .replace('{y}', y0 + dy).replace('{x}', x0 + dx);
      return new Promise((res, rej) => {
        const im = new Image();
        im.crossOrigin = 'anonymous';
        im.onload = () => { cx2.drawImage(im, dx * S, dy * S, S, S); res(); };
        im.onerror = () => rej(new Error('tile ' + (x0 + dx) + '/' + (y0 + dy)));
        im.src = url;
      });
    }));
  } catch (e) {
    satState = 'failed';
    document.getElementById('hint').textContent =
      'Orthoimagery did not answer from this network - the schematic ground '
      + 'stands. ' + D.recHonesty.availability;
    return;
  }
  // georeference the block onto the same km scale the anchors use
  const kmE = (d) => (d - pt.lng) * 111.32 * Math.cos(la);
  const kmN = (d) => (d - pt.lat) * 110.574;
  const west = x0 / n * 360 - 180, east = (x0 + SAT_SPAN) / n * 360 - 180;
  const north = tileLat(y0, n), south = tileLat(y0 + SAT_SPAN, n);
  const eW = kmE(west) * CITY_S, eE = kmE(east) * CITY_S;
  const nN = kmN(north) * CITY_S, nS = kmN(south) * CITY_S;
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  satPlane = new THREE.Mesh(
    new THREE.PlaneGeometry(Math.abs(eE - eW), Math.abs(nN - nS)),
    new THREE.MeshStandardMaterial({ map: tex, roughness: .95 }));
  satPlane.rotation.x = -Math.PI / 2;
  satPlane.position.set((eW + eE) / 2, .05, -(nN + nS) / 2);
  satPlane.receiveShadow = true;
  satPlane.name = 'orthoimagery-ground';
  scene.add(satPlane);
  satState = 'live';
  document.getElementById('hint').textContent =
    D.imagery.attribution + ' - ' + D.imagery.licence
    + ', georeferenced to the campus record. ' + D.recHonesty.fidelity;
}
document.getElementById('satBtn').addEventListener('click', satGround);

function buildCity(g, R) {
  const pois = D.geo.cityPois?.[campusKey] ?? [];
  if (!pois.length) return;
  cityLog = pois.some((p) => p.km > 15);
  const grass = new THREE.MeshStandardMaterial({ color: 0x3d5238, roughness: .95 });
  const hues = [42, 152, 205, 268, 20, 96, 330];
  const ferryMat = new THREE.LineBasicMaterial({
    color: 0x41C4D4, transparent: true, opacity: .55 });
  pois.forEach((p, i) => {
    const [x, z] = cityPos(p);
    const len = Math.hypot(x, z), ux = x / len, uz = z / len;
    if (!cityLog) {
      // the avenue: ring road out to the place's block
      const r0 = R - 22, aLen = len - r0 - 9;
      const av = box(aLen, .06, 3.6, mat.road, 0, .03, 0, g, false);
      av.position.set((r0 + aLen / 2) * ux, .03, (r0 + aLen / 2) * uz);
      av.rotation.y = -Math.atan2(uz, ux);
      for (let d = r0 + 4; d < len - 10; d += 7)
        box(1.7, .02, .16, mat.paint, d * ux, .08, d * uz, g, false)
          .rotation.y = -Math.atan2(uz, ux);
    } else {
      // across open water: a schematic ferry line, not a road
      const geoL = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3((R + 42) * ux, .5, (R + 42) * uz),
        new THREE.Vector3((len - 14) * ux, .5, (len - 14) * uz)]);
      g.add(new THREE.Line(geoL, ferryMat));
      // and its own ground: a shoreline pad in the bay
      box(24, .14, 24, mat.land, x, .07, z, g, false);
    }
    // the place: green, main block, tower, and its name with real km
    box(15, .12, 15, grass, x, .13, z, g, false);
    const hgt = 7 + (i % 3) * 2.5;
    const bmat = new THREE.MeshStandardMaterial({
      color: new THREE.Color().setHSL(hues[i % hues.length] / 360, .34, .42),
      roughness: .75 });
    const bld = box(8, hgt, 6.5, bmat, x - 2, .15 + hgt / 2, z + 1.5, g);
    const twr = box(2.6, hgt + 5, 2.6, bmat, x + 4, .15 + (hgt + 5) / 2, z - 3.5, g);
    box(3, .5, 3, mat.slab, x + 4, hgt + 5.4, z - 3.5, g, false);
    bld.userData.poi = twr.userData.poi = p.name;
    cityHits.push(bld, twr);
    const pl = label(p.name, p.km + ' km \\u00b7 RECORDED', 1.7,
      { kind: 'anchor' });
    pl.position.set(x, hgt + 10, z); g.add(pl);
    cityPois++;
  });
  cityWater(g, campusKey, R, pois);
}

/* Schematic water and crossings per city - drawn, labelled SCHEMATIC. */
function cityWater(g, key, R, pois) {
  const tag = (name, x, z) => {
    const l = label(name, 'SCHEMATIC', 1.6, { kind: 'schematic' });
    l.position.set(x, 7, z); g.add(l);
  };
  if (key === 'new-orleans') {
    // the crescent south of the uptown institutions, the lake north
    const river = new THREE.Mesh(new THREE.TubeGeometry(
      new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(-150, 0, 92), new THREE.Vector3(-15, 0, 70),
        new THREE.Vector3(110, 0, 24)), 48, 10, 8), mat.water);
    river.scale.y = .012; river.position.y = .09; g.add(river);
    tag('Mississippi River', -30, 76);
    const lake = new THREE.Mesh(new THREE.PlaneGeometry(340, 70), mat.water);
    lake.rotation.x = -Math.PI / 2; lake.position.set(10, .08, -168);
    g.add(lake);
    tag('Lake Pontchartrain', 10, -150);
    return;
  }
  if (key === 'treasure-island') {
    // the campus is an island: the Bay all around, spans east and west
    const bay = new THREE.Mesh(
      new THREE.RingGeometry(R + 52, 430, 72), mat.water);
    bay.rotation.x = -Math.PI / 2; bay.position.y = .06; g.add(bay);
    tag('San Francisco Bay', 0, -(R + 110));
    const sf = pois.find((p) => p.name === 'San Francisco');
    const spans = [];
    if (sf) {
      const [sx, sz] = cityPos(sf), sl = Math.hypot(sx, sz);
      spans.push([sx / sl, sz / sl]);              // the west span, to SF
    }
    const rte = D.geo.routes.find((r) =>
      r.from === 'treasure-island' && r.to === 'oakland');
    if (rte) {
      const b = rte.bearing_deg * Math.PI / 180;
      spans.push([Math.sin(b), -Math.cos(b)]);     // the east span
    }
    for (const [ux, uz] of spans) {
      const r0 = R + 42, r1 = 205, mid = (r0 + r1) / 2, len = r1 - r0;
      const deck = box(len, .5, 5, mat.road, mid * ux, 2.6, mid * uz, g, false);
      deck.rotation.y = -Math.atan2(uz, ux);
      for (let d = r0 + 10; d < r1; d += 26)
        box(1, 2.6, 1, mat.metal, d * ux, 1.3, d * uz, g, false);
    }
    tag('Bay Bridge', spans.length ? 160 * spans[0][0] : 0, 8);
    return;
  }
  if (key === 'oakland') {
    // the waterfront: the Bay west of the campus grounds
    const bay = new THREE.Mesh(new THREE.PlaneGeometry(240, 560), mat.water);
    bay.rotation.x = -Math.PI / 2;
    bay.position.set(-(R + 60) - 120, .06, 0); g.add(bay);
    tag('San Francisco Bay', -(R + 90), 0);
  }
}

function buildCampus(key) {
  if (campusGroup) scene.remove(campusGroup);
  campusGroup = new THREE.Group(); buildings = []; campusSpin = [];
  roadFaults = 0; roadCount = 0; cityPois = 0; cityHits = [];
  const camp = D.campuses[key];
  const dk = camp.districts;
  const R = dk.length === 2 ? 124 : 168;   // the campus scale: districts this far out
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
  // the green: rough grass between the plaza walkway and the ring road,
  // which is what a campus actually has there and what makes the ring
  // read as a road rather than a line on a slab
  const green = new THREE.Mesh(new THREE.RingGeometry(27, rr - 3, 72),
    mat.grass);
  green.rotation.x = -Math.PI / 2; green.position.y = .035;
  green.receiveShadow = true; campusGroup.add(green);
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
    const dl = label(D.i18n[loc].districts[k], null, 3,
      { kind: 'district', hue: d.hue });
    dl.position.set(rad.x * (R - 14), 15, rad.y * (R - 14));
    campusGroup.add(dl);
  });
  const plaza = new THREE.Mesh(new THREE.CylinderGeometry(24, 24, .3, 48),
    new THREE.MeshStandardMaterial({ map: concreteTex, color: 0xb8bdbd, roughness: .95 }));
  plaza.position.y = .15; plaza.receiveShadow = true; campusGroup.add(plaza);
  const sign = label(camp.name, camp.city + ', ' + camp.region, 3.2,
    { kind: 'campus' });
  sign.position.set(0, 18, 0); campusGroup.add(sign);
  dressCampus(key, campusGroup, R + 42);
  buildChapterHall(campusGroup, key);
  buildCity(campusGroup, R);
  flushDashes(campusGroup);
  walkLim = cityPois ? (cityLog ? 536 : 350) : campusR + 85;
  // fog banks: the island's weather, drifting flat haze sheets
  fogBanks = [];
  const nb = ATMOS[key]?.banks ?? 0;
  for (let i = 0; i < nb; i++) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(150 + i * 22, 34),
      new THREE.MeshBasicMaterial({ color: 0xcfd8dc, transparent: true,
        opacity: .09 + (i % 3) * .025, depthWrite: false }));
    m.rotation.x = -Math.PI / 2;
    const ang = i / nb * Math.PI * 2, rad = 70 + (i % 3) * 45;
    m.position.set(Math.cos(ang) * rad, 7 + (i % 4) * 5, Math.sin(ang) * rad);
    campusGroup.add(m);
    fogBanks.push({ m, ang, rad, sp: .015 + (i % 3) * .008 });
  }
  setGroundSurface(key);
  clearAdvisors();
  spawnCampusAdvisors();
  spawnFauna(key, R);
  scene.add(campusGroup);
  buildMinimap(key, R);
}

/* ------------------------------------------------------------ minimap --- */
// The walkable campus, from above: roads, buildings in district hues,
// the city places, and you. Drawn once per campus; the player arrow
// rides the render loop.
let mmBase = null, mmInfo = { n: 0, s: 1 };
function buildMinimap(key, R) {
  const ext = Math.max(walkLim, R + 60);
  const S2 = 66 / ext;
  mmInfo = { n: 0, s: S2, done: 0 };
  const c = document.createElement('canvas'); c.width = c.height = 150;
  const g2 = c.getContext('2d');
  g2.fillStyle = 'rgba(12,17,19,.88)'; g2.fillRect(0, 0, 150, 150);
  const X = (x) => 75 + x * S2, Y = (z) => 75 + z * S2;
  // water backdrop where the city layers put it
  if (key === 'treasure-island') {
    g2.fillStyle = 'rgba(20,40,58,.8)'; g2.fillRect(0, 0, 150, 150);
    g2.fillStyle = 'rgba(12,17,19,.95)';
    g2.beginPath(); g2.arc(75, 75, (R + 52) * S2, 0, 7); g2.fill();
  } else if (key === 'oakland') {
    g2.fillStyle = 'rgba(20,40,58,.8)';
    g2.fillRect(0, 0, X(-(R + 60)), 150);
  }
  // the ring road
  g2.strokeStyle = '#565c60'; g2.lineWidth = 3;
  g2.beginPath(); g2.arc(75, 75, (R - 24) * S2, 0, 7); g2.stroke();
  // buildings, axis-aligned, in their district hue
  const bb = new THREE.Box3();
  for (const b of buildings) {
    bb.setFromObject(b);
    const h = D.halls.find((x) => x.slug === b.userData.slug);
    const hue = D.districts[h.district].hue;
    g2.fillStyle = `hsl(${hue},45%,52%)`;
    g2.fillRect(X(bb.min.x), Y(bb.min.z),
      Math.max(2, (bb.max.x - bb.min.x) * S2),
      Math.max(2, (bb.max.z - bb.min.z) * S2));
    mmInfo.n++;
    // a fully-worked hall (stations done, every bound seat passed) rings amber
    const bound = D.sims.bindings[h.slug] ?? [];
    if ((h.stations.length || bound.length)
      && h.stations.every((id) => doneStations.has(id))
      && bound.every((x) => prog.sims[x.sim]?.passed)) {
      g2.strokeStyle = '#E8A33D'; g2.lineWidth = 1.5;
      g2.beginPath();
      g2.arc(X((bb.min.x + bb.max.x) / 2), Y((bb.min.z + bb.max.z) / 2),
        Math.max(4, (bb.max.x - bb.min.x) * S2), 0, 7);
      g2.stroke();
      mmInfo.done++;
    }
  }
  // the chapter hall and the city places
  g2.fillStyle = '#E8A33D';
  g2.beginPath(); g2.arc(75, 75, 3, 0, 7); g2.fill();
  g2.fillStyle = '#41C4D4';
  for (const p of (D.geo.cityPois?.[key] ?? [])) {
    const [px, pz] = cityPos(p);
    g2.beginPath(); g2.arc(X(px), Y(pz), 2.5, 0, 7); g2.fill();
  }
  mmBase = c;
}
function mmDraw() {
  const cv = document.getElementById('mm');
  if (!mmBase || cv.style.display === 'none') return;
  const g2 = cv.getContext('2d');
  g2.clearRect(0, 0, 150, 150);
  g2.drawImage(mmBase, 0, 0);
  if (walkActive) {
    const px = isTouch ? walkAvatar.position.x : camera.position.x;
    const pz = isTouch ? walkAvatar.position.z : camera.position.z;
    let yaw;
    if (isTouch) yaw = tYaw + Math.PI;
    else { const d = new THREE.Vector3(); camera.getWorldDirection(d);
      yaw = Math.atan2(d.x, d.z); }
    const x = 75 + px * mmInfo.s, y = 75 + pz * mmInfo.s;
    g2.save(); g2.translate(x, y); g2.rotate(yaw + Math.PI);
    g2.fillStyle = '#E8A33D';
    g2.beginPath(); g2.moveTo(0, -6); g2.lineTo(4, 5); g2.lineTo(-4, 5);
    g2.closePath(); g2.fill(); g2.restore();
  }
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
      const cl = label(String(d.halls.length), null, 1.4,
        { kind: 'station', hue: d.hue });
      cl.position.set(bx, hgt + 6, bz); regionGroup.add(cl);
    });
    const pl = label(camp.name,
      camp.city + ', ' + camp.region + ' · +' + D.chapters.hosted[key], 3.4,
      { kind: 'campus' });
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
      const al = label(a.name, a.km + ' km', 1.15, { kind: 'anchor' });
      al.position.set(ax, 9.6, az); regionGroup.add(al);
    }
  }
  // glowing routes between the campuses
  const lineMat = new THREE.LineBasicMaterial({ color: 0xE8A33D, transparent: true, opacity: .65 });
  const pairs = [];
  const pkeys = Object.keys(D.campuses);
  for (let i = 0; i < pkeys.length; i++)
    for (let j = i + 1; j < pkeys.length; j++) pairs.push([pkeys[i], pkeys[j]]);
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
      const kl = label(`${km.toLocaleString('en-US')} km`, null, 2.2,
      { kind: 'route' });
      kl.position.copy(mid).setY(mid.y + 5);
      regionGroup.add(kl);
    }
  }
  const sign = label('SmartCiti.X : Trade Craft Academy', 'powered by AGI Corp',
    3.6, { kind: 'brand' });
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
  applyAtmos(null);
  buildRegion();
  scene.fog.near = 380; scene.fog.far = 1300;
  document.getElementById('mm').style.display = 'none';
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
  document.getElementById('glbBtn').style.display = 'none';
  document.getElementById('glbInBtn').style.display = 'none';
  document.getElementById('satBtn').style.display = 'none';
  satClear(); satState = 'off';
  syncURL();
}

// the campus rollup: the whole training loop summed over the campus's
// halls - stations, bound seats, and the districts' crib checks
function campusRollup(key) {
  const halls = D.campuses[key].halls.map((sg) => D.halls.find((x) => x.slug === sg));
  let sd = 0, stot = 0, sp = 0, sb = 0;
  for (const h of halls) {
    stot += h.stations.length;
    sd += h.stations.filter((id) => doneStations.has(id)).length;
    const b = D.sims.bindings[h.slug] ?? [];
    sb += b.length;
    sp += b.filter((x) => prog.sims[x.sim]?.passed).length;
  }
  const dists = D.campuses[key].districts;
  const cd = dists.filter((dk) => prog.tools[dk]?.passed).length;
  return `✓ ${sd}/${stot} · ▶ ${sp}/${sb} · \U0001f9f0 ${cd}/${dists.length}`;
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
  applyAtmos(key);
  buildCampus(key);
  scene.fog.near = 320 * fogMul; scene.fog.far = 1280 * fogMul;
  document.getElementById('mm').style.display = '';
  controls.maxDistance = 760; controls.minDistance = 20;
  camera.position.set(0, 300, 350); controls.target.set(0, 0, 0);
  const camp = D.campuses[key];
  document.getElementById('hname').textContent =
    camp.name + '  ' + campusRollup(key);
  document.getElementById('hfocus').textContent =
    camp.city + ', ' + camp.region + ' — ' + camp.tagline
    + (D.geo.cityPois?.[key] ? ' · ' + t('city.note') : '');
  document.getElementById('hint').textContent = t('hint.campus');
  document.getElementById('walkBtn').style.display = '';
  document.getElementById('avaBtn').style.display = '';
  document.getElementById('campusBtn').style.display = 'none';
  document.getElementById('simBtn').style.display = 'none';
  document.getElementById('glbBtn').style.display = 'none';
  document.getElementById('glbInBtn').style.display = 'none';
  document.getElementById('satBtn').style.display = '';
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
  applyAtmos(campusKey);
  buildHall(sg);
  scene.fog.near = 70 * fogMul; scene.fog.far = 170 * fogMul;
  document.getElementById('mm').style.display = 'none';
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
  document.getElementById('glbBtn').style.display = '';
  document.getElementById('glbInBtn').style.display = 'none';
  document.getElementById('satBtn').style.display = 'none';
  satClear(); satState = 'off';
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

let campusR = 168, nearSlug = null, nearPoi = null;
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
__ADVISOR_JS__

/* ---------------------------------------------------------------- UI ---- */
function renderChrome() {
  const i = D.i18n[loc];
  document.documentElement.lang = loc;
  document.documentElement.dir = i.dir;
  document.getElementById('back').textContent = '← ' + t('nav.campus');
  const hall = document.getElementById('hall');
  // ✓ stations complete · ▶ every bound seat passed · 🧰 district crib passed
  const mark = (h) => {
    let m = !h.stations.length ? ''
      : h.stations.every((id) => doneStations.has(id)) ? ' ✓' : ' ●';
    const bound = D.sims.bindings[h.slug] ?? [];
    if (bound.length && bound.every((b) => prog.sims[b.sim]?.passed)) m += ' ▶';
    if (prog.tools[h.district]?.passed) m += ' \U0001f9f0';
    return m;
  };
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

/* ------------------------------------------------ training-data recorder
   Three interaction shapes, one per episode: a completed sim run (the
   scenario, the declared control scheme, the measured rubric outcome), an
   advisor exchange (which fixed topic, whether the answer was read from a
   record or written in the advisor registry), a walkaround point checked.
   Episode-level, not frame-by-frame - see D.training.honesty. Device-local,
   like tc-progress, under its OWN key so the two records never collide;
   on by default with a visible toggle; never read by any grader. */
const TR_KEY = D.training.storage.key, TR_ON_KEY = D.training.storage.toggle_key;
function trLoad() {
  try { const a = JSON.parse(localStorage.getItem(TR_KEY)); return Array.isArray(a) ? a : []; }
  catch (e) { return []; }
}
let trainingLog = trLoad();
let trainingOn = (() => {
  try { const v = localStorage.getItem(TR_ON_KEY); return v === null ? true : v === '1'; }
  catch (e) { return true; }
})();
function trainingToggle(on) {
  trainingOn = on;
  try { localStorage.setItem(TR_ON_KEY, on ? '1' : '0'); } catch (e) { /* blocked store */ }
}
function recordEpisode(ep) {
  if (!trainingOn) return;
  trainingLog.push({ t: new Date().toISOString(), ...ep });
  if (trainingLog.length > D.training.storage.cap) trainingLog.shift();
  try { localStorage.setItem(TR_KEY, JSON.stringify(trainingLog)); }
  catch (e) { /* private mode / blocked store: session-only */ }
}
function clearTraining() {
  trainingLog = [];
  try { localStorage.removeItem(TR_KEY); } catch (e) { /* blocked store */ }
}
function exportTraining() {
  return JSON.stringify({ pack: 'smartcitix-trade-craft-academy-training-data',
    exported: new Date().toISOString(), episodes: trainingLog });
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
prog.tools = typeof prog.tools === 'object' && prog.tools ? prog.tools : {};
prog.walk = typeof prog.walk === 'object' && prog.walk ? prog.walk : {};
let curStation = null;
function scoreChip() {
  const h = D.halls.find(x => x.slug === slug);
  if (view !== 'hall' || !h) return '';
  // the hall's whole training loop reads out here: stations, seats, crib
  const parts = [];
  if (h.stations.length) {
    const d = h.stations.filter((id) => doneStations.has(id)).length;
    parts.push(`\u2713 ${d}/${h.stations.length}`);
  }
  const bound = D.sims.bindings[slug] ?? [];
  if (bound.length)
    parts.push(`\u25b6 ${bound.filter((b) => prog.sims[b.sim]?.passed).length}/${bound.length}`);
  if (prog.tools[h.district]?.passed) parts.push('\U0001f9f0 \u2713');
  return parts.length ? '  ' + parts.join(' \u00b7 ') : '';
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
    ${r.strand === 'tools' ? `<p><button class="barbtn" data-crib="${h.district}">🧰 ${D.tools.cribs[h.district].name}</button></p>` : ''}
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

/* -------------------------------------------------- the crib + drill ---- */
// The crib drill keeps the registry's own contract: a pick is right or
// wrong against the crib record, the option order is index arithmetic,
// not chance, and the result lands in the same device-local record.
/* The walkaround panel: one clipboard, the whole card's state, and the
   mark. Non-gating by registry rule - nothing reads waDone but the HUD. */
function openWa(i) {
  const def = D.sims.sims[curSimId];
  const w = def.walkaround[i];
  document.getElementById('pbody').innerHTML = `
    <h2>📋 ${w.point}</h2>
    <span class="chip">${def.name}</span>
    <span class="chip">${waDone.size}/${waTotal}</span>
    <p>${w.check}.</p>
    ${waDone.has(i) ? `<p style="color:var(--good)">✓</p>`
      : `<p><button class="barbtn" data-wa="${i}">✓ ${w.point}</button></p>`}
    <ul style="color:var(--muted);font-size:12.5px">${def.walkaround.map((x, j) =>
      `<li>${waDone.has(j) ? '✓' : '·'} ${x.point}</li>`).join('')}</ul>
    <p style="color:var(--muted);font-size:12px">${D.sims.walkHonesty}</p>`;
  document.body.classList.add('open');
}

let curCrib = null, drill = null;
function openCrib(dk) {
  curCrib = dk; curStation = null; drill = null;
  const c = D.tools.cribs[dk];
  const rec = prog.tools[dk];
  document.getElementById('pbody').innerHTML = `
    <h2>${c.name}</h2>
    <span class="chip">${D.i18n[loc].districts[dk]}</span>
    <span class="chip">${c.tools.length}</span>
    ${rec?.passed ? `<span class="chip" style="border-color:var(--good);color:var(--good)">✓ ${D.tools.drill.name}</span>` : ''}
    <ul style="list-style:none;padding:0">${c.tools.map((tl) =>
      `<li style="margin:7px 0">${tl.glyph} <b>${tl.name}</b><br>
       <span style="color:var(--muted);font-size:12.5px">${tl.use}</span></li>`).join('')}</ul>
    <p><button class="barbtn" id="drillGo">▶ ${D.tools.drill.name}</button></p>
    <p style="color:var(--muted);font-size:12px">${D.tools.honesty} ${t('progress.local')}</p>`;
  document.body.classList.add('open');
}
function drillStart() {
  drill = { i: 0, right: 0, t0: performance.now() };
  drillQ();
}
function drillQ() {
  const tasks = D.tools.drills[curCrib];
  if (drill.i >= tasks.length) return drillEnd();
  const c = D.tools.cribs[curCrib], task = tasks[drill.i];
  const ti = c.tools.findIndex((x) => x.id === task.tool);
  // options by index arithmetic - the registry's own contract, no chance
  const picks = [0, 3, 6, 9].map((o) => c.tools[(ti + o) % c.tools.length]);
  const rot = drill.i % 4;
  const order = picks.map((_, j) => picks[(j + rot) % 4]);
  document.getElementById('pbody').innerHTML = `
    <h2>${c.name}</h2>
    <span class="chip">${D.tools.drill.name} ${drill.i + 1}/${tasks.length}</span>
    <div class="q"><p>${task.ask}.</p>
    ${order.map((x) => `<button class="opt" data-drill="1" data-ok="${x.id === task.tool ? 1 : 0}">${x.glyph} ${x.name}</button>`).join('')}</div>`;
}
function drillEnd() {
  const tasks = D.tools.drills[curCrib];
  const secs = (performance.now() - drill.t0) / 1000;
  const passed = drill.right === tasks.length;
  const rec = prog.tools[curCrib] ?? {};
  rec.runs = (rec.runs ?? 0) + 1;
  if (passed) { rec.passed = true; rec.best = Math.min(rec.best ?? Infinity, secs); }
  prog.tools[curCrib] = rec; saveProg(); renderChrome();
  if (view === 'hall') document.getElementById('hname').textContent =
    D.halls.find((x) => x.slug === slug).name + scoreChip();
  chime(passed); buzz(passed ? 160 : 80, .5);
  document.getElementById('pbody').innerHTML = `
    <h2>${D.tools.cribs[curCrib].name}</h2>
    <span class="chip" style="${passed ? 'border-color:var(--good);color:var(--good)' : 'border-color:var(--crit);color:var(--crit)'}">
      ${passed ? t('sim.pass') : t('sim.retry')}</span>
    <h3>${t('sim.results')}</h3>
    <table style="width:100%;border-collapse:collapse;font-size:13.5px"><tbody>
      <tr><td>picks</td><td style="text-align:end;font-family:'IBM Plex Mono',monospace">${drill.right}/${tasks.length}</td>
        <td style="text-align:end">${passed ? '✓' : '✗'}</td></tr>
      <tr><td>time</td><td style="text-align:end;font-family:'IBM Plex Mono',monospace">${secs.toFixed(1)} s</td><td></td></tr>
    </tbody></table>
    ${rec.passed && isFinite(rec.best) ? `<p style="color:var(--muted);font-size:12.5px">✓ ${rec.runs}× · best ${rec.best.toFixed(1)} s</p>` : ''}
    <p style="color:var(--muted);font-size:12px;margin-top:12px">${D.tools.honesty} ${t('progress.local')}</p>
    <p><button class="barbtn" id="drillRetry">↻ ${t('sim.retry')}</button>
       <button class="barbtn" id="drillExit">${t('ui.close')}</button></p>
    <style>#pbody td{border-top:1px solid var(--rule);padding:6px 8px;color:var(--muted)}</style>`;
  drill = null;
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
  if (view === 'sim' && waBeacons.length) {
    const wh = ray.intersectObjects(waBeacons, false)[0];
    if (wh?.object.userData.wapt !== undefined)
      return openWa(wh.object.userData.wapt);
  }
  const ahit = ray.intersectObjects(advisorMeshes, true)[0];
  if (ahit) {
    let o = ahit.object;
    while (o && !o.userData.advisor) o = o.parent;
    if (o) {
      if (walkActive && plc.isLocked) plc.unlock();
      return openAdvisor(o.userData.advisor);
    }
  }
  const hit = ray.intersectObjects(beacons, false)[0];
  if (hit?.object.userData.station) {
    if (walkActive) plc.unlock();
    return openStation(hit.object.userData.station);
  }
  if (hit?.object.userData.crib) {
    if (walkActive) plc.unlock();
    return openCrib(hit.object.userData.crib);
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
  if (e.target.id === 'cardBtn') return drawCard();
  /* portable saves: the record as JSON, exported and imported by the
     learner alone - it never leaves the device unless they carry it */
  if (e.target.id === 'expBtn') {
    saveProg();
    const j = JSON.stringify(prog);
    document.getElementById('saveBox').innerHTML =
      `<textarea id="saveTa" readonly style="width:100%;height:90px;background:var(--sunk);color:var(--ink);border:1px solid var(--rule);border-radius:7px;font:11px 'IBM Plex Mono',monospace;padding:7px"></textarea>
       <p style="color:var(--muted);font-size:11.5px;margin:4px 0 0">${t('progress.local')}</p>`;
    const ta = document.getElementById('saveTa');
    ta.value = j; ta.select();
    try { navigator.clipboard?.writeText(j); } catch (err) { /* manual copy */ }
    return;
  }
  if (e.target.id === 'impBtn') {
    document.getElementById('saveBox').innerHTML =
      `<textarea id="saveTa" style="width:100%;height:90px;background:var(--sunk);color:var(--ink);border:1px solid var(--rule);border-radius:7px;font:11px 'IBM Plex Mono',monospace;padding:7px"></textarea>
       <p><button class="barbtn" id="impGo">⇲ ✓</button>
       <span id="impMsg" style="color:var(--muted);font-size:12px"></span></p>`;
    return;
  }
  if (e.target.id === 'impGo') {
    try {
      const p = JSON.parse(document.getElementById('saveTa').value);
      if (typeof p !== 'object' || p === null || Array.isArray(p))
        throw new Error('not a record');
      localStorage.setItem(PROG_KEY, JSON.stringify(p));
      location.reload();
    } catch (err) {
      document.getElementById('impMsg').textContent = '✗ ' + (err?.message ?? err);
    }
    return;
  }
  if (e.target.id === 'trExpBtn') {
    const j = exportTraining();
    document.getElementById('trBox').innerHTML =
      `<textarea id="trTa" readonly style="width:100%;height:90px;background:var(--sunk);color:var(--ink);border:1px solid var(--rule);border-radius:7px;font:11px 'IBM Plex Mono',monospace;padding:7px"></textarea>`;
    const ta = document.getElementById('trTa');
    ta.value = j; ta.select();
    try { navigator.clipboard?.writeText(j); } catch (err) { /* manual copy */ }
    return;
  }
  if (e.target.id === 'trClearBtn') {
    clearTraining();
    openRecords();
    return;
  }
  const wa = e.target.closest('[data-wa]');
  if (wa && sim) {
    const i = +wa.dataset.wa;
    waDone.add(i);
    recordEpisode({ kind: 'walkaround', campus: campusKey, hall: slug,
      sim: curSimId, point: D.sims.sims[curSimId].walkaround[i].id });
    waBeacons[i].material = mat.steel;
    blip(900, 1300, .1, 'triangle', .1);
    if (waDone.size === waTotal) {
      chime(true);
      prog.walk[curSimId] = (prog.walk[curSimId] ?? 0) + 1;
      saveProg();
    }
    openWa(i);
    return;
  }
  const cb = e.target.closest('[data-crib]');
  if (cb) return openCrib(cb.dataset.crib);
  if (e.target.id === 'drillGo' || e.target.id === 'drillRetry')
    return drillStart();
  if (e.target.id === 'drillExit') {
    document.body.classList.remove('open'); return;
  }
  const dp = e.target.closest('.opt[data-drill]');
  if (dp && drill) {
    dp.parentElement.querySelectorAll('.opt').forEach((o) => {
      o.classList.toggle('ok', o.dataset.ok === '1'); o.disabled = true; });
    if (dp.dataset.ok === '1') drill.right++;
    else dp.classList.add('bad');
    drill.i++;
    setTimeout(drillQ, 500);
    return;
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
// the weather cycle: every state the world registry declares, in its own
// declared order, each one a set of multipliers on this campus's own
// atmosphere rather than a separate look
function setWeather(id) {
  if (!WX[id]) return;
  wx = id;
  const nxt = WX_CYCLE[(WX_CYCLE.indexOf(wx) + 1) % WX_CYCLE.length];
  const b = document.getElementById('dnBtn');
  b.textContent = WX[nxt].glyph;
  b.title = WX[wx].name + ' \u2014 ' + WX[wx].blurb
    + '. Next: ' + WX[nxt].name;
  b.setAttribute('aria-label', 'weather: ' + WX[wx].name
    + '; next ' + WX[nxt].name);
  reAtmos();
}
document.getElementById('dnBtn').addEventListener('click', () => {
  setWeather(WX_CYCLE[(WX_CYCLE.indexOf(wx) + 1) % WX_CYCLE.length]);
});
setWeather(WX[params.get('wx')] ? params.get('wx') : 'clear');
// the records panel: every seat and drill from the device-local record
function openRecords() {
  const td = "style=\\"text-align:end\\"";
  const mono = "style=\\"text-align:end;font-family:'IBM Plex Mono',monospace\\"";
  const row = (name, r) => `<tr><td>${name}</td>
    <td ${td}>${r?.runs ?? 0}</td>
    <td ${td}>${r?.passed ? '✓' : '·'}</td>
    <td ${mono}>${isFinite(r?.best) ? r.best.toFixed(1) + ' s' : '\\u2013'}</td></tr>`;
  const head = `<tr><th></th><th ${td}>\\u00d7</th><th ${td}>✓</th><th ${td}>best</th></tr>`;
  document.getElementById('pbody').innerHTML = `
    <h2>⏱ ${t('sim.results')}</h2>
    <span class="chip">✓ ${doneStations.size}/${Object.keys(D.stations).length}</span>
    <span class="chip">▶ ${Object.values(prog.sims).filter((r) => r.passed).length}/${Object.keys(D.sims.sims).length}</span>
    <span class="chip">\U0001f9f0 ${Object.values(prog.tools).filter((r) => r.passed).length}/${Object.keys(D.tools.cribs).length}</span>
    <span class="chip">📋 ${Object.values(prog.walk).reduce((a, b) => a + b, 0)}</span>
    <h3>${t('sim.start')}</h3>
    <table style="width:100%;border-collapse:collapse;font-size:13px"><tbody>
      ${head}${Object.entries(D.sims.sims).map(([id, def]) => row(def.name, prog.sims[id])).join('')}
    </tbody></table>
    <h3>${D.tools.drill.name}</h3>
    <table style="width:100%;border-collapse:collapse;font-size:13px"><tbody>
      ${head}${Object.entries(D.tools.cribs).map(([dk, c]) => row(c.name, prog.tools[dk])).join('')}
    </tbody></table>
    <p><button class="barbtn" id="cardBtn">🪪 ${t('sim.results')}</button>
       <button class="barbtn" id="expBtn">⇪ JSON</button>
       <button class="barbtn" id="impBtn">⇲ JSON</button></p>
    <div id="saveBox"></div>
    <div id="cardBox"></div>
    <h3>🤖 Training-data episodes</h3>
    <span class="chip">${trainingLog.length} / ${D.training.storage.cap} kept</span>
    <p style="margin:6px 0">
      <label style="display:inline-flex;align-items:center;gap:6px;cursor:pointer">
        <input type="checkbox" id="trOn" ${trainingOn ? 'checked' : ''}>
        <span style="font-size:12.5px;color:var(--muted)">record episodes as I train</span>
      </label></p>
    <p><button class="barbtn" id="trExpBtn">⇪ export</button>
       <button class="barbtn" id="trClearBtn">🗑 clear</button></p>
    <div id="trBox"></div>
    <p style="color:var(--muted);font-size:12px">${D.training.honesty.schematic}</p>
    <p style="color:var(--muted);font-size:12px">${D.training.honesty.not_scored}</p>
    <p style="color:var(--muted);font-size:12px;margin-top:12px">${t('progress.local')} ${D.sims.honesty}</p>
    <style>#pbody td,#pbody th{border-top:1px solid var(--rule);padding:5px 8px;color:var(--muted);font-weight:400}</style>`;
  document.body.classList.add('open');
  document.getElementById('trOn')?.addEventListener('change', (e) => trainingToggle(e.target.checked));
}
/* The progress card: the record drawn as one image the learner can save
   (long-press / right-click - the page never uploads it anywhere). */
function drawCard() {
  const c = document.createElement('canvas');
  c.width = 640; c.height = 460; c.id = 'pcard';
  c.style.cssText = 'width:100%;border:1px solid var(--rule);border-radius:10px;margin-top:8px';
  const g2 = c.getContext('2d');
  g2.fillStyle = '#12181B'; g2.fillRect(0, 0, 640, 460);
  g2.fillStyle = '#E8A33D'; g2.fillRect(0, 0, 640, 5);
  g2.fillStyle = '#E8EDEC'; g2.font = '700 30px "Barlow Condensed", sans-serif';
  g2.fillText('SmartCiti.X : Trade Craft Academy', 28, 48);
  g2.fillStyle = '#93A3A6'; g2.font = '15px "IBM Plex Sans", sans-serif';
  g2.fillText('Training record · ' + new Date().toISOString().slice(0, 10), 28, 74);
  const chips = [
    ['✓', doneStations.size + '/' + Object.keys(D.stations).length + ' stations'],
    ['▶', Object.values(prog.sims).filter((r) => r.passed).length + '/'
      + Object.keys(D.sims.sims).length + ' seats'],
    ['\U0001f9f0', Object.values(prog.tools).filter((r) => r.passed).length + '/'
      + Object.keys(D.tools.cribs).length + ' cribs'],
    ['📋', Object.values(prog.walk).reduce((a, b) => a + b, 0) + ' walkarounds'],
  ];
  chips.forEach(([ic, txt], i) => {
    const x = 28 + i * 150;
    g2.strokeStyle = '#28353A'; g2.lineWidth = 1.5;
    g2.beginPath(); g2.roundRect(x, 92, 140, 34, 17); g2.stroke();
    g2.fillStyle = '#E8EDEC'; g2.font = '14px "IBM Plex Sans", sans-serif';
    g2.fillText(ic + ' ' + txt, x + 12, 114);
  });
  g2.font = '15px "IBM Plex Mono", monospace';
  Object.entries(D.sims.sims).forEach(([id, def], i) => {
    const y = 168 + i * 32, r = prog.sims[id];
    g2.fillStyle = '#93A3A6'; g2.fillText(def.name, 28, y);
    g2.fillStyle = r?.passed ? '#5CB584' : '#41505a';
    g2.fillText(r?.passed ? '✓' : '·', 420, y);
    g2.fillStyle = '#E8EDEC';
    g2.fillText(isFinite(r?.best) ? r.best.toFixed(1) + ' s' : '\\u2013', 470, y);
  });
  g2.fillStyle = '#68787c'; g2.font = '12px "IBM Plex Sans", sans-serif';
  g2.fillText('Device-local record · cosmetic only · not equipment certification', 28, 436);
  const bx = document.getElementById('cardBox');
  bx.innerHTML = '<p style="color:var(--muted);font-size:11.5px;margin:8px 0 0">'
    + t('progress.local') + '</p>';
  bx.prepend(c);
}
document.getElementById('recBtn').addEventListener('click', () => {
  if (walkActive) plc.unlock();
  openRecords();
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
// test hooks: state for assertions, and the two panel openers the toolroom
// harness drives (module scope hides them from the page's own globals)
window.__tc3dDo = (fn, arg) => {
  if (fn === 'room') openRoom(arg ?? D.halls.find((x) => x.slug === slug)
    .rooms.find((r) => r.strand === 'tools').label);
  else if (fn === 'crib') openCrib(arg);
  else if (fn === 'wa') openWa(arg);
  else if (fn === 'quality') { qAuto = false; setQuality(arg); }
  else if (fn === 'emote') playEmote(arg);
  else if (fn === 'advisor') openAdvisor(...String(arg).split(':'));
  else if (fn === 'wx') setWeather(arg);
  // place the camera: "eyeX,eyeY,eyeZ|atX,atY,atZ" - used by the harnesses
  // and, later, by anything that wants to drive the view
  else if (fn === 'cam') {
    const [eye, at] = String(arg).split('|').map((v) => v.split(',').map(Number));
    camera.position.set(...eye);
    if (at) { controls.target.set(...at); camera.lookAt(...at); }
    controls.autoRotate = false; controls.update();
  }
  // test hooks: stand the walker beside an advisor, or well away from one
  else if (fn === 'walkTo' || fn === 'walkAway') {
    const m = advisorMeshes.find((x) => x.userData.advisor === arg);
    if (m && walkAvatar) {
      const v = m.getWorldPosition(new THREE.Vector3());
      const off = fn === 'walkTo' ? 1.4 : 40;
      walkAvatar.position.set(v.x + off, walkAvatar.position.y, v.z + off);
    }
  }
};
window.__tc3d = () => ({ view, buildings: buildings.length, plates: plates.length,
  beacons: beacons.length, floors: floors.length, slug, campusKey, loc, walkActive,
  sim: curSimId && sim ? curSimId : null, roadFaults, roadCount,
  anchors: anchorPins, simCam: simView, audio: !!ac, city: cityPois,
  scenario: curScenario?.id ?? null,
  chHosted: D.chapters.hosted[campusKey] ?? null,
  isTouch, shadows: renderer.shadowMap.enabled,
  avatar: avatarCfg ? { ...avatarCfg } : null, emote: lastEmote,
  apeSpan: (avatarMesh ?? walkAvatar)?.userData?.apeSpanRatio ?? null,
  atmos: atmosKey, fogNear: Math.round(scene.fog.near),
  fogFar: Math.round(scene.fog.far), camFar: camera.far,
  banks: fogBanks.length, mmN: mmInfo.n,
  mmVis: document.getElementById('mm').style.display !== 'none',
  simRider: !!simRider, ambN: ambNodes.length,
  cribs: cribCount, curCrib, drillN: drill ? drill.i : null,
  gau: sim?.gauges ? sim.gauges() : null,
  rollup: view === 'campus' ? campusRollup(campusKey) : null,
  mmDone: mmInfo.done ?? 0, night, wx, rain: rain.visible,
  wa: waTotal ? { done: waDone.size, total: waTotal } : null,
  xr: { vr: document.getElementById('vrBtn').style.display !== 'none',
        ar: document.getElementById('arBtn').style.display !== 'none',
        mode: xrMode, presenting: renderer.xr.isPresenting },
  meta: { exp: lastExport,
    imp: importedGlb ? { nodes: importedGlb.nodes, name: importedGlb.name } : null },
  quality: qLevel, px: renderer.getPixelRatio(),
  advisors: { here: advisorMeshes.map((m) => m.userData.advisor),
              near: nearAdvisor, open: curAdvisor, topic: curTopic },
  training: { on: trainingOn, count: trainingLog.length,
              kinds: trainingLog.map((e) => e.kind),
              last: trainingLog[trainingLog.length - 1] ?? null },
  labels: { live: labelSet.filter((x) => x.parent).length,
            kinds: [...new Set(labelSet.filter((x) => x.parent)
              .map((x) => x.userData.lbl.kind))].sort(),
            shown: labelSet.filter((x) => x.parent && x.visible).length,
            focus: labelFocus ? { kind: labelFocus.userData.lbl.kind,
              at: labelFocus.getWorldPosition(new THREE.Vector3())
                .toArray().map((v) => Math.round(v)) } : null,
            lit: labelSet.filter((x) => x.parent)
              .map((x) => Math.round(x.userData.lbl.focus * 100)),
            // what the eye actually gets: each visible sign's height as a
            // fraction of the viewport, and its opacity - the two numbers
            // the design makes a promise about
            frac: (() => {
              const tan = Math.tan(camera.fov * Math.PI / 360);
              const v = new THREE.Vector3();
              return labelSet.filter((x) => x.parent && x.visible).map((x) => {
                const d = x.getWorldPosition(v).distanceTo(camera.position);
                return Math.round(x.scale.y / (2 * d * tan) * 1000) / 1000;
              }).filter((r) => isFinite(r) && r > 0);
            })(),
            op: labelSet.filter((x) => x.parent && x.visible)
              .map((x) => Math.round(x.material.opacity * 100)),
            band: LFOCUS.screen },
  world: { wx, cycle: WX_CYCLE, rain: rainRate,
           fauna: faunaBodies.map((b) => b.userData.kind),
           // rounded so a harness can watch them move without floating noise
           faunaAt: faunaBodies.map((b) => b.position.toArray()
             .map((v) => Math.round(v * 10) / 10).join(',')),
           faunaOut: !!(faunaGroup && faunaGroup.visible),
           ground: Object.keys(GROUND_RECIPES),
           maps: groundMapCache.size, genMs: Math.round(genMs) },
  rig: (() => {                       // the VRM skeleton, as it really is
    const av = avatarMesh ?? walkAvatar ?? simRider;
    if (!av?.userData?.bones) return null;
    av.updateMatrixWorld(true);
    const v = new THREE.Vector3(), out = {};
    for (const [n, b] of Object.entries(av.userData.bones))
      out[n] = Math.round(b.getWorldPosition(v).y * 100) / 100;
    return out;
  })(),
  rigTree: (() => {                   // and how those bones hang together
    const av = avatarMesh ?? walkAvatar ?? simRider;
    if (!av?.userData?.bones) return null;
    const out = {};
    av.traverse((o) => { if (o.name) out[o.name] = o.parent?.name ?? null; });
    return out;
  })(),
  pose: (() => {                      // the joints a gait actually drives
    const av = avatarMesh ?? walkAvatar ?? simRider;
    const b = av?.userData?.bones;
    if (!b) return null;
    const r = (x) => Math.round(x * 1000) / 1000;
    return { leg: r(b.leftUpperLeg.rotation.x), knee: r(b.leftLowerLeg.rotation.x),
      legR: r(b.rightUpperLeg.rotation.x), arm: r(b.rightUpperArm.rotation.x),
      elbow: r(b.rightLowerArm.rotation.x), hipY: r(b.hips.position.y),
      neckY: r(b.neck.rotation.y), headY: r(b.head.rotation.y),
      headX: r(b.head.rotation.x), dist: r(av.userData.dist ?? 0) };
  })(),
  sat: { state: satState, plane: !!satPlane,
         tiles: SAT_TILES ?? D.imagery.tiles, z: SAT_Z,
         span: satPlane ? [Math.round(satPlane.geometry.parameters.width),
                           Math.round(satPlane.geometry.parameters.height)] : null,
         at: satPlane ? satPlane.position.toArray()
                          .map((v) => Math.round(v * 10) / 10) : null },
  perf: { calls: renderer.info.render.calls,
    tris: renderer.info.render.triangles,
    geoms: renderer.info.memory.geometries,
    tex: renderer.info.memory.textures,
    cached: geoCache.size },
  wheel: document.querySelectorAll('#wheel path').length,
  progress: { stations: doneStations.size, sims: Object.keys(prog.sims).length,
    tools: Object.keys(prog.tools).length },
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
  if (view === 'avatar' && !emo) idleBreath(avatarMesh, clock.elapsedTime, dt);
  if (!reduced) for (const b of fogBanks) {
    b.ang += dt * b.sp;
    b.m.position.x = Math.cos(b.ang) * b.rad;
    b.m.position.z = Math.sin(b.ang) * b.rad;
  }
  rainStep(dt); qStep(dt);
  if (view === 'campus') mmDraw();
  if (walkActive) (isTouch ? touchWalkStep : walkStep)(dt);
  // in a sim's operator view the sim owns the camera - the orbit controls
  // must not re-clamp it to their own distance limits
  else if (!sim || controls.enabled) controls.update();
  advisorProximity(dt);
  faunaStep(clock.elapsedTime, dt);
  labelStep(dt);
  renderer.render(scene, camera);
});
</script>
</body>
</html>
'''

page = page.replace('__DATA__', DATA).replace('__PIPELINE_JS__', PIPELINE_JS)
page = page.replace('__SIM_JS__', SIM_JS)
page = page.replace('__AVATAR_JS__', AVATAR_JS)
page = page.replace('__ADVISOR_JS__', ADVISOR_JS)
out = HERE / 'trade_craft_3d.html'
out.write_text(page)
print(f"written: {len(page):,} bytes | {len(HALLS)} halls | "
      f"{stations_reg['count']} stations | {len(I18N)} locales")
