#!/usr/bin/env python3
"""The fleet showroom: every generic vehicle and watercraft on one turntable.

Rendered from fleet/registry/fleet.json and nothing else; the registry is
embedded verbatim and every spec on the page is read from it. The 3D is
web/fleetkit.py's module, carried byte-for-byte between its FLEET_KIT markers
(web/test_fleet.mjs holds the copy to the kit), so the page drives with
exactly the physics fleet/test.mjs tests:
  - each family is ONE InstancedMesh (the whole lineup costs one draw call per
    family shown, never one per vehicle);
  - a test-drive pad (flat AUTHORED ground) and a test-float pond: a land
    vehicle is refused the water, a boat is refused the shore.

Canvas page: it takes the theme's panel/button/badge layer only (no hero
band) and colours its UI only from the theme tokens, so all five site styles
reach it. Driving here is play, not training.
"""
import html
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402
import sitenav  # noqa: E402
from sitenav import nav_html, labels as nav_labels, NAV_CSS, STYLE_JS  # noqa: E402
from design_kit import STYLE_HEAD_JS  # noqa: E402
from seo import apply_seo  # noqa: E402
from pagehero import theme  # noqa: E402
from fleetkit import fleet_inline, BEGIN as KIT_BEGIN, END as KIT_END  # noqa: E402
from physkit import phys_inline, BEGIN as PHYS_BEGIN, END as PHYS_END  # noqa: E402

THEME_CSS, THEME_JS = theme('canvas')
if THEME_JS:
    raise SystemExit('build_fleet: the canvas theme is CSS only; pagehero.theme("canvas") returned script')

PAGE = 'web/trade_craft_fleet.html'
REG = json.loads((ROOT / 'fleet/registry/fleet.json').read_text())
PHYSREG = json.loads((ROOT / 'physics/registry/physics.json').read_text())
for k in ('source_stamp', 'honesty', 'coeffs', 'pedestrian_classes'):
    if k not in PHYSREG:
        raise SystemExit(f'build_fleet: physics/registry/physics.json has no {k}')
for k in ('source_stamp', 'honesty', 'colours', 'counts', 'families', 'fleet'):
    if k not in REG:
        raise SystemExit(f'build_fleet: fleet/registry/fleet.json has no {k!r}')
C = REG['counts']
if (C['land'], C['water']) != (50, 20) or len(REG['fleet']) != 70:
    raise SystemExit(f'build_fleet: the registry must hold 50 land + 20 water, holds {C["land"]} + {C["water"]}')

_CAT = json.loads((ROOT / 'i18n/locales/en.json').read_text(encoding='utf-8'))['strings']
_USED = set()


def T(k):
    k = 'fleet.' + k
    if k not in _CAT or not isinstance(_CAT[k], str) or not _CAT[k].strip():
        raise SystemExit(f'build_fleet: i18n/locales/en.json has no fleet chrome key {k!r}')
    _USED.add(k)
    return html.escape(_CAT[k], quote=True)


def TS(k):
    return f'<span data-i18n="fleet.{k}">{T(k)}</span>'


def TA(k):
    """a chrome string in an aria-label"""
    return f'aria-label="{T(k)}" data-i18n-aria="fleet.{k}"'


# the runtime needs these keys even where no static element carries them
for _k in ('cam', 'chase', 'trafficnote', 'spec.family', 'spec.medium', 'spec.dims', 'spec.mass', 'spec.top', 'spec.accel', 'spec.turn', 'spec.seats',
           'spec.seat', 'spec.trades', 'noseat', 'openseat', 'refused', 'drive', 'float', 'medium.land', 'medium.water',
           'shown', 'authored', 'allfam', 'touch.group', 'touch.stick', 'touch.throttle', 'touch.brake', 'touch.enter', 'touch.exit',
           'drive.test'):
    T(_k)

# DRIVE (wave 11): a Test drive link per family into the wilds page (web/build_wilds.py DRIVE mount, ?drive=<family>#<world>).
# AUTHORED choice of world per medium; both must exist in wilds/registry/wilds.json (fleet/test.mjs proves a boat finds water
# and a land vehicle finds dry ground from every world's trailhead).
TESTDRIVE_WORLD = {'land': 'canyon', 'water': 'delta'}
_WILDS_IDS = [w['id'] for w in json.loads((ROOT / 'wilds/registry/wilds.json').read_text())['worlds']]
for _m, _w in TESTDRIVE_WORLD.items():
    if _w not in _WILDS_IDS:
        raise SystemExit(f'build_fleet: test-drive world {_w!r} for {_m} is not in wilds/registry/wilds.json {_WILDS_IDS}')
TESTDRIVE = {f['id']: f'trade_craft_wilds.html?drive={f["id"]}#{TESTDRIVE_WORLD[f["medium"]]}' for f in REG['families']}

# nav: the page must be declared in web/sitenav.py PAGES (lead-owned). Fail
# closed: an undeclared page stops the build by name; nothing is registered
# here and no sibling's header is borrowed.
if PAGE not in sitenav.PAGES:
    raise SystemExit(f'build_fleet: {PAGE} is not declared in web/sitenav.py PAGES (NEEDS nav: group play, key nav.page.fleet)')
NAV_STATE = 'wired'
NAV = nav_html(PAGE, nav_labels('en'))

FAMILY_OPTS = ''.join(f'<option value="{html.escape(f["id"])}" data-medium="{f["medium"]}" lang="en">'
                      f'{html.escape(f["name"])} ({f["count"]})</option>' for f in REG['families'])
KIT = fleet_inline()
PKIT = phys_inline()
if PKIT.count(PHYS_BEGIN) != 1 or PKIT.count(PHYS_END) != 1:
    raise SystemExit('build_fleet: physkit inline block must hold one PHYS_KIT block')
if KIT.count(KIT_BEGIN) != 1 or KIT.count(KIT_END) != 1:
    raise SystemExit('build_fleet: fleetkit inline block must hold one FLEET_KIT block')
ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' "
        "rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' stroke='%23E8A33D' stroke-width='2.6' "
        "stroke-linejoin='round'/%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E")

JS = r'''
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
''' + KIT + '\n' + PKIT + r'''
const REG = JSON.parse(document.getElementById('fleet-registry').textContent);
const PHYSREG = JSON.parse(document.getElementById('physics-registry').textContent);
const I18N = JSON.parse(document.getElementById('fleet-i18n').textContent);
const TESTDRIVE = JSON.parse(document.getElementById('fleet-testdrive').textContent);
function pickLocale() {
  const q = new URLSearchParams(location.search).get('lang');
  if (q && Object.hasOwn(I18N, q)) return q;
  const prefs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || 'en'];
  for (const n of prefs) { const c = String(n).slice(0, 2).toLowerCase(); if (Object.hasOwn(I18N, c)) return c; }
  return 'en';
}
const LOC = pickLocale();
function tr(k) {
  const s = I18N[LOC].strings['fleet.' + k];
  if (typeof s !== 'string') throw new Error(`fleet i18n: locale ${LOC} has no fleet.${k}`);
  return s;
}
document.documentElement.lang = LOC;
document.documentElement.dir = I18N[LOC].dir;
for (const el of document.querySelectorAll('[data-i18n]')) el.textContent = I18N[LOC].strings[el.dataset.i18n];
for (const el of document.querySelectorAll('[data-i18n-aria]')) el.setAttribute('aria-label', I18N[LOC].strings[el.dataset.i18nAria]);
const NF1 = new Intl.NumberFormat(LOC, { maximumFractionDigits: 1 });
const NF0 = new Intl.NumberFormat(LOC, { maximumFractionDigits: 0 });
const $ = (s) => document.querySelector(s);

/* ---------------------------------------------------------- the scene --- */
const canvas = $('#fleet-canvas');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(2, devicePixelRatio));
renderer.info.autoReset = false;
const scene = new THREE.Scene();
// world colours (sky, ground, water) are the scene's own, not UI chrome
scene.background = new THREE.Color(0x9fb4c2);
scene.fog = new THREE.Fog(0x9fb4c2, 400, 1400);
const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 3000);
camera.position.set(22, 12, 26);
const orbit = new OrbitControls(camera, canvas);
orbit.target.set(0, 2, 0); orbit.enableDamping = true; orbit.maxPolarAngle = Math.PI * 0.48;
scene.add(new THREE.HemisphereLight(0xeaf2ff, 0x55504a, 1.1));
const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(60, 120, 40); scene.add(sun);

/* the lot: turntable at the origin, the test-drive pad east, the pond north-east */
const PAD = { x: 360, z: 0, half: 140 };
const POND = { x: 360, z: 330, r: 170 };
const inPond = (x, z) => Math.hypot(x - POND.x, z - POND.z) < POND.r;
const GROUND = fleetFlatGround(0, 0, inPond);
const lot = new THREE.Group(); scene.add(lot);
const flat = (w, d, col, x, y, z) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d).rotateX(-Math.PI / 2), new THREE.MeshStandardMaterial({ color: col, roughness: 1 })); m.position.set(x, y, z); lot.add(m); return m; };
flat(2400, 2400, 0x7d8a6a, 300, -0.02, 150);                                 // grass
flat(PAD.half * 2, PAD.half * 2, 0x5d6166, PAD.x, 0, PAD.z);                // asphalt pad
const water = new THREE.Mesh(new THREE.CircleGeometry(POND.r, 64).rotateX(-Math.PI / 2), new THREE.MeshStandardMaterial({ color: 0x3f6f86, roughness: 0.25, metalness: 0.1 }));
water.position.set(POND.x, 0.01, POND.z); lot.add(water);
const table = new THREE.Mesh(new THREE.CylinderGeometry(40, 40, 0.4, 72), new THREE.MeshStandardMaterial({ color: 0x4a4f55, roughness: 0.7 }));
table.position.y = 0.2; lot.add(table);
const plinth = new THREE.Mesh(new THREE.CylinderGeometry(8, 8, 0.3, 48), new THREE.MeshStandardMaterial({ color: 0x6b7178, roughness: 0.5 }));
plinth.position.y = 0.55; lot.add(plinth);

const BUMP_FAMILY = 'compact-car';   // two parked cars on the pad to bump into (crash play)
const cap = Object.fromEntries(REG.families.map((f) => [f.id, f.count + 1 + (f.id === BUMP_FAMILY ? 2 : 0)]));
const FL = fleetCreate(THREE, REG, cap);
scene.add(FL.group);
const wake = fleetWake(THREE, 96); scene.add(wake.mesh);
fleetLights(FL, 1);
/* crash play on the test pad (wave 7): AUTHORED barriers, a curb and two parked cars; arcade physics from
   physics/registry/physics.json - play, never a crash test. Vehicles never strike people (none on this pad). */
const PW = createPhysics({ reg: PHYSREG, cell: 16, ground: () => 0, water: (x, z) => (inPond(x, z) ? { surface: 0, bed: -3 } : null) });
const BARRIERS = [
  { id: 'barrier-ahead', cx: PAD.x - PAD.half + 20, cz: PAD.z + 45, hx: 9, hz: 0.3, yaw: 0, y0: 0, y1: 1.1, kind: 'barrier' },
  { id: 'barrier-east', cx: PAD.x + 70, cz: PAD.z - 30, hx: 0.3, hz: 14, yaw: 0.35, y0: 0, y1: 1.1, kind: 'barrier' },
  { id: 'curb-west', cx: PAD.x - PAD.half + 20, cz: PAD.z + 20, hx: 6, hz: 0.25, yaw: 0, y0: 0, y1: 0.15, kind: 'curb' },
];
PW.addBoxes(BARRIERS);
{
  const bm = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshStandardMaterial({ color: 0xd9a441, roughness: 0.7 }), BARRIERS.length);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), up = new THREE.Vector3(0, 1, 0);
  BARRIERS.forEach((b, i) => bm.setMatrixAt(i, m.compose(new THREE.Vector3(b.cx, (b.y0 + b.y1) / 2, b.cz), q.setFromAxisAngle(up, b.yaw), new THREE.Vector3(b.hx * 2, b.y1 - b.y0, b.hz * 2))));
  bm.name = 'phys:barriers'; lot.add(bm);
}
const smoke = fleetSmoke(THREE, 96); scene.add(smoke.mesh);
let audio = null, crashes = 0, bumpers = [];
function thud(ev) {   // the sound hook: a short low tone shaped by fleetCrashTone (silent where WebAudio is unavailable)
  const t = fleetCrashTone(ev);
  if (typeof AudioContext === 'undefined') return;
  audio = audio || new AudioContext();
  const o = audio.createOscillator(), g = audio.createGain(), now = audio.currentTime;
  o.type = 'triangle'; o.frequency.setValueAtTime(t.low ? 70 : 110, now); o.frequency.exponentialRampToValueAtTime(40, now + t.seconds);
  g.gain.setValueAtTime(0.25 * t.gain, now); g.gain.exponentialRampToValueAtTime(0.001, now + t.seconds);
  o.connect(g).connect(audio.destination); o.start(now); o.stop(now + t.seconds);
}
function onCrash(ev) {
  if (ev.type !== 'crash') return;
  crashes++;
  if (ev.smoke) smoke.puff(ev.x, ev.y, ev.z, Math.min(1, ev.speed / 20));
  thud(ev);
}
const physCtx = (self) => ({ coeffs: PHYSREG, world: PW, people: [], onEvent: onCrash,
  others: [...(drv && drv !== self ? [drv] : []), ...bumpers.filter((b) => b !== self)] });
function spawnBumpers() {
  const e = REG.fleet.find((x) => x.family === BUMP_FAMILY), spec = fleetSpec(e);
  bumpers = [[PAD.x - PAD.half + 45, PAD.z + 10, 0.4], [PAD.x - PAD.half + 60, PAD.z + 30, -1.2]].map(([x, z, yaw]) => {
    const st = fleetState(spec, GROUND, x, z, yaw); return { e, spec, st, h: FL.spawn(e.id, st) };
  });
}
function dropBumpers() { for (const b of bumpers) b.h.despawn(); bumpers = []; }
/* ambient traffic demo: AUTHORED lanes on the pad (a cell grid) and rings on the pond - not real streets */
let traffic = null, trafficOn = false, camMode = 'chase';
function makeTraffic() {
  const routes = [...fleetGridLanes({ cell: 12, every: 4, x0: PAD.x - PAD.half + 6, x1: PAD.x + PAD.half - 6, z0: PAD.z - PAD.half + 6, z1: PAD.z + PAD.half - 6,
    step: 4, minLen: 60, ok: (x, z) => Math.abs(x - PAD.x) < PAD.half - 6 && Math.abs(z - PAD.z) < PAD.half - 6 && !inPond(x, z) }),
    fleetRingLane('pond-inner', POND.x, POND.z, POND.r * 0.45, 32), fleetRingLane('pond-outer', POND.x, POND.z, POND.r * 0.72, 48)];
  const t = fleetTraffic(THREE, REG, routes, GROUND, { seed: 11, landPerKm: 8, waterPerKm: 5, maxAgents: 90, maxFamilies: 10, radius: 700, speedFactor: 0.35, laneOffset: 2.2 });
  scene.add(t.group); fleetLights(t.fleet, 1); return t;
}
const BY = new Map(REG.fleet.map((e) => [e.id, e]));
const FAM = new Map(REG.families.map((f) => [f.id, f]));

/* ------------------------------------------------------- the turntable --- */
let filter = { medium: 'all', family: 'all' };
let shown = [], sel = REG.fleet[0].id, lineup = [], hero = null, spin = true, mode = 'turntable';
const LINE_R = 30, SLOT_M = 5.2;   // lineup ring radius; every lineup model is scaled to fit SLOT_M (not to scale)
function visible(e) {
  return (filter.medium === 'all' || e.medium === filter.medium) && (filter.family === 'all' || e.family === filter.family);
}
function layout() {
  for (const h of lineup) h.despawn();
  lineup = [];
  if (hero) { hero.despawn(); hero = null; }
  shown = REG.fleet.filter(visible);
  if (!shown.some((e) => e.id === sel) && shown.length) sel = shown[0].id;
  const others = shown.filter((e) => e.id !== sel);
  others.forEach((e, i) => {
    const a = (i / Math.max(1, others.length)) * Math.PI * 2;
    const k = SLOT_M / Math.max(e.dims_m.length, e.dims_m.height * 1.4);
    lineup.push(Object.assign(FL.spawn(e.id, { x: 0, y: 0.4, z: 0, yaw: 0, scale: k }), { a, k }));
  });
  if (shown.length) hero = FL.spawn(sel, { x: 0, y: 0.7, z: 0, yaw: 0 });
  $('#fleet-count').textContent = `${NF0.format(shown.length)} / ${NF0.format(REG.fleet.length)} ${tr('shown')}`;
  renderList(); renderSpec(); frameHero(true); placeTable(0);
}
let tableYaw = 0;
function placeTable(dt) {
  if (spin && !matchMedia('(prefers-reduced-motion: reduce)').matches) tableYaw += dt * 0.18;
  for (const h of lineup) {
    const a = h.a + tableYaw;
    h.set({ x: Math.sin(a) * LINE_R, y: 0.4, z: Math.cos(a) * LINE_R, yaw: a + Math.PI / 2, scale: h.k });
  }
  if (hero) hero.set({ x: 0, y: 0.7, z: 0, yaw: -tableYaw * 1.5 });
}
function frameHero(snap) {
  const e = BY.get(sel), d = Math.max(e.dims_m.length, e.dims_m.height * 2, 6);
  orbit.target.set(0, 0.7 + e.dims_m.height * 0.45, 0);
  if (snap) camera.position.set(d * 1.1, d * 0.55 + 2, d * 1.3);
}
function renderList() {
  const ul = $('#fleet-list');
  ul.replaceChildren(...shown.map((e) => {
    const li = document.createElement('li');
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'tc-btn tc-btn-ghost fl-item'; b.dataset.id = e.id; b.lang = 'en';
    b.setAttribute('aria-pressed', String(e.id === sel));
    b.textContent = e.name;
    b.addEventListener('click', () => select(e.id));
    li.append(b); return li;
  }));
}
function row(k, v, lang) {
  const dt = document.createElement('dt'); dt.textContent = tr(k);
  const dd = document.createElement('dd'); dd.textContent = v; if (lang) dd.lang = lang;
  return [dt, dd];
}
function renderSpec() {
  const e = BY.get(sel), d = e.dims_m, f = FAM.get(e.family);
  $('#spec-name').textContent = e.name;
  $('#spec-id').textContent = e.id;
  const dl = $('#spec-list');
  dl.replaceChildren(
    ...row('spec.family', f.name, 'en'),
    ...row('spec.medium', tr('medium.' + e.medium)),
    ...row('spec.dims', `${NF1.format(d.length)} × ${NF1.format(d.width)} × ${NF1.format(d.height)} m`),
    ...row('spec.mass', `${NF0.format(e.mass_kg)} kg`),
    ...row('spec.top', `${NF0.format(e.top_speed_kmh)} km/h`),
    ...row('spec.accel', `${NF1.format(e.accel_ms2)} m/s²`),
    ...row('spec.turn', `${NF1.format(e.turn_radius_m)} m`),
    ...row('spec.seats', NF0.format(e.seats)),
  );
  const seat = $('#spec-seat');
  if (e.sim_seat === null) {
    seat.replaceChildren(Object.assign(document.createElement('span'), { textContent: tr('noseat'), className: 'tc-badge tc-badge-muted' }));
  } else {
    const a = document.createElement('a');
    a.className = 'tc-btn tc-btn-primary'; a.href = e.sim_seat.href.replace(/^web\//, '');
    a.textContent = `${tr('openseat')}: ${e.sim_seat.name}`; a.dataset.seat = e.sim_seat.id;
    const p = document.createElement('p'); p.className = 'trades';
    p.textContent = `${tr('spec.trades')}: ${e.trades.halls.join(', ')}`; p.lang = 'en';
    seat.replaceChildren(a, p);
  }
  const td = document.createElement('a');   // DRIVE (wave 11): Test drive this family in the wilds
  td.className = 'tc-btn tc-btn-ghost'; td.href = TESTDRIVE[e.family]; td.dataset.testdrive = e.family; td.textContent = tr('drive.test');
  if (typeof td.href !== 'string' || !TESTDRIVE[e.family]) throw new Error('fleet: no test-drive link for ' + e.family);
  seat.appendChild(td);
  $('#btn-drive').textContent = e.medium === 'land' ? tr('drive') : tr('float');
  $('#btn-cam').textContent = camMode === 'chase' ? tr('cam') : tr('chase');
  $('#spec-badge').textContent = tr('authored');
  if (location.hash.slice(1) !== sel) history.replaceState(null, '', '#' + sel);
}
function select(id) {
  if (!BY.has(id)) throw new Error('fleet: no entry ' + id);
  if (mode !== 'turntable') exitDrive();
  sel = id;
  if (!visible(BY.get(id))) { filter = { medium: 'all', family: 'all' }; $('#f-medium-all').checked = true; $('#f-family').value = 'all'; }
  layout();
}
function step(n) { const i = shown.findIndex((e) => e.id === sel); select(shown[(i + n + shown.length) % shown.length].id); }

/* ----------------------------------------------------- drive and float --- */
let drv = null;
const keys = {};
function startDrive() {
  const e = BY.get(sel), spec = fleetSpec(e);
  const at = e.medium === 'land' ? { x: PAD.x - PAD.half + 20, z: PAD.z, yaw: 0 } : { x: POND.x, z: POND.z, yaw: Math.PI / 2 };
  const ok = fleetCanSpawn(spec, GROUND, at.x, at.z, at.yaw);
  if (!ok.ok) throw new Error('fleet: ' + ok.reason);
  const st = fleetState(spec, GROUND, at.x, at.z, at.yaw);
  drv = { e, spec, st, h: FL.spawn(e.id, st), refusedShown: 0 };
  if (e.medium === 'land') spawnBumpers();
  mode = e.medium === 'land' ? 'drive' : 'float';
  orbit.enabled = false;
  fleetChaseCamera(camera, st, spec, 0, { snap: true });
  document.body.dataset.fleetMode = mode;
  $('#btn-exit').hidden = false; $('#drive-help').hidden = false; $('#btn-cam').hidden = false;
  touch.setAboard(true);
  canvas.focus();
}
function exitDrive() {
  if (!drv) return;
  drv.h.despawn(); drv = null; mode = 'turntable'; dropBumpers();
  orbit.enabled = true; document.body.dataset.fleetMode = mode;
  $('#btn-exit').hidden = true; $('#drive-help').hidden = true; $('#btn-cam').hidden = true; $('#toast').textContent = '';
  touch.setAboard(false);
  frameHero(true);
}
/* phone driving: the kit's touch controls on the test pad (a stick, throttle, brake, get in / out) */
const touch = fleetTouchControls(document, $('.fl-stage'),
  { group: tr('touch.group'), stick: tr('touch.stick'), throttle: tr('touch.throttle'), brake: tr('touch.brake'), enter: tr('touch.enter'), exit: tr('touch.exit') },
  () => (drv ? exitDrive() : startDrive()));
function input() {
  const k = (a, b) => (keys[a] || keys[b] ? 1 : 0);
  const kb = { throttle: k('KeyW', 'ArrowUp') - k('KeyS', 'ArrowDown'), steer: k('KeyA', 'ArrowLeft') - k('KeyD', 'ArrowRight'), brake: keys.Space ? 1 : 0 };
  const t = touch.input(), big = (a, b) => (Math.abs(a) >= Math.abs(b) ? a : b);
  return { throttle: big(kb.throttle, t.throttle), steer: big(kb.steer, t.steer), brake: Math.max(kb.brake, t.brake) };
}
function driveTick(dt, inp) {
  fleetPhysStep(drv.st, drv.spec, inp, GROUND, dt, physCtx(drv));
  drv.h.set(drv.st);
  for (const b of bumpers) { fleetPhysStep(b.st, b.spec, { throttle: 0, steer: 0, brake: 0 }, GROUND, dt, physCtx(b)); b.h.set(b.st); }
  if (drv.spec.medium === 'water') { wake.emit(drv.st, drv.spec, dt); }
  if (drv.st.refused > drv.refusedShown) { drv.refusedShown = drv.st.refused; $('#toast').textContent = tr('refused'); }
  if (camMode === 'driver') fleetDriverCamera(camera, drv.st, drv.spec); else fleetChaseCamera(camera, drv.st, drv.spec, dt);
}
function toggleCam() {
  camMode = camMode === 'chase' ? 'driver' : 'chase';
  $('#btn-cam').textContent = camMode === 'chase' ? tr('cam') : tr('chase');
  $('#btn-cam').setAttribute('aria-pressed', String(camMode === 'driver'));
  if (drv && camMode === 'chase') fleetChaseCamera(camera, drv.st, drv.spec, 0, { snap: true });
}
function toggleTraffic() {
  trafficOn = !trafficOn;
  if (trafficOn && !traffic) traffic = makeTraffic();
  if (traffic) traffic.group.visible = trafficOn;
  $('#btn-traffic').setAttribute('aria-pressed', String(trafficOn));
  $('#traffic-note').hidden = !trafficOn;
}
addEventListener('keydown', (ev) => {
  if (mode === 'turntable') return;
  if (ev.code === 'Escape') { exitDrive(); return; }
  if (ev.code === 'KeyC') { toggleCam(); return; }
  if (['KeyW', 'KeyA', 'KeyS', 'KeyD', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space'].includes(ev.code)) { keys[ev.code] = true; ev.preventDefault(); }
});
addEventListener('keyup', (ev) => { keys[ev.code] = false; });

/* ------------------------------------------------------------ controls --- */
for (const r of document.querySelectorAll('input[name="f-medium"]')) r.addEventListener('change', () => {
  filter.medium = r.value; filter.family = 'all'; $('#f-family').value = 'all';
  for (const o of $('#f-family').options) o.hidden = o.value !== 'all' && filter.medium !== 'all' && o.dataset.medium !== filter.medium;
  layout();
});
$('#f-family').addEventListener('change', (ev) => { filter.family = ev.target.value; layout(); });
$('#btn-prev').addEventListener('click', () => step(-1));
$('#btn-next').addEventListener('click', () => step(1));
$('#btn-spin').addEventListener('click', (ev) => { spin = !spin; ev.currentTarget.setAttribute('aria-pressed', String(spin)); });
$('#btn-drive').addEventListener('click', startDrive);
$('#btn-exit').addEventListener('click', exitDrive);
$('#btn-cam').addEventListener('click', toggleCam);
$('#btn-traffic').addEventListener('click', toggleTraffic);

function resize() {
  const r = canvas.getBoundingClientRect();
  renderer.setSize(r.width, r.height, false);
  camera.aspect = r.width / Math.max(1, r.height); camera.updateProjectionMatrix();
}
addEventListener('resize', resize);
let last = performance.now(), calls = 0;
function frame(t) {
  const dt = Math.min(0.05, (t - last) / 1000); last = t;
  if (mode === 'turntable') { placeTable(dt); orbit.update(); }
  else driveTick(dt, input());
  if (traffic && trafficOn) traffic.update(dt, drv ? drv.st : { x: camera.position.x, z: camera.position.z },
    { coeffs: PHYSREG, people: [], others: drv ? [drv] : [], onEvent: onCrash });
  wake.update(dt); smoke.update(dt);
  renderer.info.reset();
  renderer.render(scene, camera);
  calls = renderer.info.render.calls;
  requestAnimationFrame(frame);
}
/* test hook (web/test_fleet.mjs, web/smoke.mjs): state and deterministic steps */
window.__fleet = {
  select, filter: (medium, family) => { filter = { medium, family }; layout(); return shown.length; },
  shown: () => shown.map((e) => e.id), selected: () => sel, mode: () => mode,
  drive: () => { startDrive(); return mode; }, exit: () => { exitDrive(); return mode; },
  steps(n, inp) { for (let i = 0; i < n; i++) driveTick(1 / 60, inp); const s = drv.st; return { x: s.x, y: s.y, z: s.z, v: s.v, refused: s.refused, wet: inPond(s.x, s.z) }; },
  stats: () => ({ drawCalls: calls, familyMeshes: FL.drawCalls(), familiesShown: new Set(shown.map((e) => e.family)).size, instances: lineup.length + (hero ? 1 : 0) + (drv ? 1 : 0) }),
  pond: POND, pad: PAD,
  cam: (m) => { if (m !== camMode) toggleCam(); return camMode; },
  eye: () => ({ x: camera.position.x, y: camera.position.y, z: camera.position.z }),
  traffic(on, n) {
    if (on !== trafficOn) toggleTraffic();
    if (!traffic) return null;
    let wet = 0, dry = 0;
    for (let i = 0; i < n; i++) {
      traffic.update(1 / 60, { x: PAD.x, z: PAD.z + 120 });
      for (const a of traffic.agents) { const d = fleetDepth(GROUND, a.x, a.z); if (a.spec.medium === 'land' && d > FLEET_MIN_WET_M) wet++; if (a.spec.medium === 'water' && d < a.spec.draft + FLEET_KEEL_CLEAR_M) dry++; }
    }
    return { ...traffic.stats(), wet, dry, budget: undefined };
  },
  wheels: () => FL.wheels.visible,
  touch: (show) => { touch.show(show); return touch.state(); },
  input: () => input(),
  brake: () => (drv ? drv.h.brakeLevel() : null),
  crash: () => ({ crashes, dent: drv ? drv.st.dent : null, crumple: drv ? drv.st.crumple : null, smoke: smoke.update(0), boxes: PW.boxes.length,
    bumpers: bumpers.map((b) => ({ x: b.st.x, z: b.st.z, v: b.st.v, dent: b.st.dent })), z: drv ? drv.st.z : null, barrierZ: BARRIERS[0].cz }),
};
const h0 = decodeURIComponent(location.hash.slice(1));
if (BY.has(h0)) sel = h0;
resize(); layout();
requestAnimationFrame(frame);
document.documentElement.dataset.fleetReady = '1';
'''

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>{STYLE_HEAD_JS}</script>
<link rel="icon" href="{ICON}">
<title>The fleet showroom — SmartCiti.X : Trade Craft Academy</title>
<style>
/* UI colours come ONLY from the site theme's tokens (--tc-*, the canvas theme
   layer and the Style switcher's data-style on <html>): all five styles apply. */
*{{box-sizing:border-box}}
[hidden]{{display:none!important}}
body[data-fleet-mode="drive"] #btn-drive,body[data-fleet-mode="float"] #btn-drive{{display:none}}
body.tc-theme-canvas{{margin:0;background:var(--tc-plate);color:var(--tc-ink);font:15px/1.45 system-ui,sans-serif}}
.fl-head{{padding:14px 16px 6px;max-width:1400px;margin:0 auto}}
.fl-head h1{{margin:0 0 4px;font-size:clamp(1.4rem,3vw,2rem)}}
.fl-head p{{margin:2px 0;color:var(--tc-muted);max-width:80ch}}
.fl-head .play{{color:var(--tc-ink)}}
.fl-main{{display:grid;grid-template-columns:minmax(240px,300px) 1fr;gap:12px;padding:8px 16px 16px;max-width:1400px;margin:0 auto}}
.fl-side,.fl-spec{{background:var(--tc-panel);border:1px solid var(--tc-line);border-radius:10px;padding:12px}}
.fl-side fieldset{{border:0;margin:0 0 8px;padding:0}}
.fl-side legend,.fl-side label.lb{{font-weight:600;color:var(--tc-ink)}}
.fl-side select{{width:100%;margin-top:4px;background:var(--tc-plate);color:var(--tc-ink);border:1px solid var(--tc-line);border-radius:6px;padding:6px}}
.fl-radios label{{margin-inline-end:10px;color:var(--tc-ink)}}
#fleet-count{{color:var(--tc-muted);font-size:.9em;margin:6px 0}}
#fleet-list{{list-style:none;margin:0;padding:0;max-height:52vh;overflow:auto}}
#fleet-list li{{margin:2px 0}}
.fl-item{{width:100%;text-align:start;justify-content:flex-start}}
.fl-item[aria-pressed="true"]{{outline:2px solid var(--tc-steel);outline-offset:-2px}}
.fl-stage{{position:relative;min-height:520px;border-radius:10px;overflow:hidden;border:1px solid var(--tc-line)}}
#fleet-canvas{{display:block;width:100%;height:100%;min-height:520px;touch-action:none}}
.fl-bar{{position:absolute;inset-inline:8px;top:8px;display:flex;flex-wrap:wrap;gap:6px}}
.fl-spec{{position:absolute;inset-inline-end:8px;top:60px;width:min(340px,calc(100% - 16px));max-height:calc(100% - 68px);overflow:auto}}
.fl-spec h2{{margin:0;font-size:1.15rem}}
.fl-spec .id{{color:var(--tc-muted);font-size:.8em;font-family:ui-monospace,monospace}}
.fl-spec dl{{display:grid;grid-template-columns:auto 1fr;gap:2px 10px;margin:8px 0}}
.fl-spec dt{{color:var(--tc-muted)}} .fl-spec dd{{margin:0;color:var(--tc-ink)}}
.fl-spec .trades{{color:var(--tc-muted);font-size:.85em}}
#drive-help,#toast,#traffic-note{{position:absolute;inset-inline-start:8px;bottom:8px;max-width:min(520px,60%);background:var(--tc-panel);color:var(--tc-ink);border:1px solid var(--tc-line);border-radius:8px;padding:6px 10px;font-size:.9em}}
@media (pointer:coarse){{#drive-help{{display:none}}}}
#traffic-note{{bottom:64px}} #toast:empty{{display:none}} #toast{{bottom:auto;top:52px;color:var(--tc-ink);border-color:var(--tc-amber)}}
body[data-fleet-mode="drive"] .fl-spec,body[data-fleet-mode="float"] .fl-spec{{display:none}}
.fl-honesty{{max-width:1400px;margin:0 auto;padding:0 16px 20px;color:var(--tc-muted);font-size:.9em}}
@media (max-width:760px){{.fl-main{{grid-template-columns:1fr}} #fleet-list{{max-height:30vh}} .fl-spec{{position:static;width:auto;max-height:none;margin-top:8px}} .fl-stage{{min-height:420px}} #fleet-canvas{{min-height:420px}}}}
</style>
<style>{NAV_CSS}</style>
<style data-tc-theme="canvas">{THEME_CSS}</style>
</head>
<body class="tc-theme-canvas" data-fleet-mode="turntable">
{NAV}<header class="fl-head">
  <h1>{TS("title")}</h1>
  <p>{TS("lede")}</p>
  <p>{TS("intro")}</p>
  <p class="play">{TS("play")}</p>
</header>
<main class="fl-main">
  <aside class="fl-side" {TA("list")}>
    <fieldset class="fl-radios"><legend>{TS("filter")}</legend>
      <label><input type="radio" name="f-medium" id="f-medium-all" value="all" checked> {TS("all")}</label>
      <label><input type="radio" name="f-medium" value="land"> {TS("land")}</label>
      <label><input type="radio" name="f-medium" value="water"> {TS("water")}</label>
    </fieldset>
    <label class="lb" for="f-family">{TS("family")}</label>
    <select id="f-family"><option value="all" data-i18n="fleet.allfam">{T("allfam")}</option>{FAMILY_OPTS}</select>
    <p id="fleet-count" aria-live="polite"></p>
    <ul id="fleet-list"></ul>
  </aside>
  <section class="fl-stage" {TA("title")}>
    <canvas id="fleet-canvas" tabindex="0" {TA("title")}></canvas>
    <div class="fl-bar">
      <button type="button" class="tc-btn tc-btn-ghost" id="btn-prev">{TS("prev")}</button>
      <button type="button" class="tc-btn tc-btn-ghost" id="btn-next">{TS("next")}</button>
      <button type="button" class="tc-btn tc-btn-ghost" id="btn-spin" aria-pressed="true">{TS("spin")}</button>
      <button type="button" class="tc-btn tc-btn-primary" id="btn-drive">{TS("drive")}</button>
      <button type="button" class="tc-btn tc-btn-primary" id="btn-exit" hidden>{TS("exit")}</button>
      <button type="button" class="tc-btn tc-btn-ghost" id="btn-cam" aria-pressed="false" hidden>{TS("cam")}</button>
      <button type="button" class="tc-btn tc-btn-ghost" id="btn-traffic" aria-pressed="false">{TS("traffic")}</button>
    </div>
    <p id="toast" role="status"></p>
    <p id="drive-help" hidden>{TS("controls")}</p>
    <p id="traffic-note" hidden>{TS("trafficnote")}</p>
    <div class="fl-spec">
      <span class="tc-badge tc-badge-info" id="spec-badge">{T("authored")}</span>
      <h2 id="spec-name" lang="en"></h2>
      <div class="id" id="spec-id"></div>
      <dl id="spec-list"></dl>
      <div id="spec-seat"></div>
    </div>
  </section>
</main>
<p class="fl-honesty">{TS("honesty")} <span lang="en" dir="ltr">Registry: fleet/registry/fleet.json (stamp {REG["source_stamp"]}): {C["land"]} land vehicles, {C["water"]} watercraft, {C["families"]} families, {C["linked_to_seat"]} linked to an existing training seat.</span></p>
<p class="fl-honesty" lang="en" dir="ltr">{html.escape(PHYSREG["honesty"])} Registry: physics/registry/physics.json (stamp {PHYSREG["source_stamp"]}).</p>
<script type="application/json" id="fleet-registry">__FLEET_REG__</script>
<script type="application/json" id="physics-registry">__PHYS_REG__</script>
<script type="application/json" id="fleet-i18n">__FLEET_I18N__</script>
<script type="application/json" id="fleet-testdrive">{json.dumps(TESTDRIVE, sort_keys=True)}</script>
<script type="importmap">
{{"imports":{{
  "three":"./vendor/three.module.min.js",
  "three/addons/":"./vendor/addons/"
}}}}
</script>
<script type="module">
__FLEET_JS__
</script>
<script>{STYLE_JS}</script>
</body>
</html>
'''

I18N_CAT = {}
for _f in sorted((ROOT / 'i18n/locales').glob('*.json')):
    _c = json.loads(_f.read_text(encoding='utf-8'))
    for _need in ('locale', 'dir', 'language', 'strings'):
        if _need not in _c:
            raise SystemExit(f'build_fleet: {_f.name} has no {_need!r}')
    _s = {}
    for _k in sorted(_USED):
        if _k not in _c['strings'] or not isinstance(_c['strings'][_k], str) or not _c['strings'][_k].strip():
            raise SystemExit(f'build_fleet: locale {_c["locale"]} has no fleet chrome key {_k!r}')
        _s[_k] = _c['strings'][_k]
    I18N_CAT[_c['locale']] = {'dir': _c['dir'], 'language': _c['language'], 'strings': _s}
if len(I18N_CAT) != 8 or 'en' not in I18N_CAT or not any(v['dir'] == 'rtl' for v in I18N_CAT.values()):
    raise SystemExit(f'build_fleet: expected 8 locales incl. en and an rtl one, found {sorted(I18N_CAT)}')
for ph in ('__FLEET_REG__', '__PHYS_REG__', '__FLEET_I18N__', '__FLEET_JS__'):
    if page.count(ph) != 1:
        raise SystemExit(f'build_fleet: placeholder {ph} must appear exactly once')
page = (page.replace('__FLEET_REG__', json.dumps(REG, sort_keys=True).replace('</', '<\\/'))
        .replace('__PHYS_REG__', json.dumps(PHYSREG, ensure_ascii=False).replace('</', '<\\/'))
        .replace('__FLEET_I18N__', json.dumps(I18N_CAT, ensure_ascii=False, sort_keys=True).replace('</', '<\\/'))
        .replace('__FLEET_JS__', JS))
page = apply_seo(page, PAGE, 'The fleet showroom — SmartCiti.X : Trade Craft Academy',
                 f'{C["land"]} generic land vehicles and {C["water"]} watercraft on one turntable, with a test-drive pad '
                 'and a test-float pond. Generic types, authored figures; driving here is play.', 'page')
emit(HERE / 'trade_craft_fleet.html', page,
     f'{C["land"]} land + {C["water"]} water | {C["families"]} families | {C["linked_to_seat"]} seat links | nav {NAV_STATE}')
