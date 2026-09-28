/**
 * Fleet verification: fleet/registry/fleet.json against its builder, the sims
 * and tasks registries it links to, and web/fleetkit.py's module run for real
 * (three.js from web/vendor, physics on flat and wilds ground).
 *
 *   node fleet/test.mjs
 *   node fleet/test.mjs --root=/tmp/copy      (mutation runs: a broken copy)
 */
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';

const HERE = dirname(fileURLToPath(import.meta.url));
const hit = process.argv.slice(2).find((a) => a.startsWith('--root='));
const ROOT = resolve(hit ? hit.slice(7) : join(HERE, '..'));
let n = 0, bad = 0;
const ok = (m, c, ev = []) => {
  if (c) { n++; console.log('  ok  ' + m); return; }
  bad++; console.log('FAIL  ' + m); for (const e of ev.slice(0, 6)) console.log('      ' + e);
};
const J = (rel) => JSON.parse(readFileSync(join(ROOT, rel), 'utf8'));
const reg = J('fleet/registry/fleet.json');
const sims = J('sims/registry/sims.json');
const tasks = J('tasks/registry/tasks.json');

// ------------------------------------------------------------- registry ---
const stamp = createHash('sha256').update(readFileSync(join(ROOT, 'fleet/build.py'))).digest('hex').slice(0, 16);
ok(`source_stamp ${reg.source_stamp} is sha256[:16] of fleet/build.py`, reg.source_stamp === stamp, [`want ${stamp}`]);
const land = reg.fleet.filter((e) => e.medium === 'land'), water = reg.fleet.filter((e) => e.medium === 'water');
ok(`exactly 50 land vehicles (found ${land.length})`, land.length === 50);
ok(`exactly 20 watercraft (found ${water.length})`, water.length === 20);
ok('every entry is land or water', land.length + water.length === reg.fleet.length);
ok('counts block matches the entries', reg.counts.land === land.length && reg.counts.water === water.length
  && reg.counts.total === reg.fleet.length && reg.counts.families === reg.families.length
  && reg.counts.linked_to_seat === reg.fleet.filter((e) => e.sim_seat !== null).length);
const ids = reg.fleet.map((e) => e.id);
const dup = ids.filter((x, i) => ids.indexOf(x) !== i);
ok('fleet ids are unique', dup.length === 0, dup);
ok('every id is <family>.<slug>', reg.fleet.every((e) => e.id.startsWith(e.family + '.') && e.id.length > e.family.length + 1));
const famIds = reg.families.map((f) => f.id);
ok('family ids are unique', new Set(famIds).size === famIds.length);
const FIELDS = ['id', 'family', 'name', 'medium', 'dims_m', 'mass_kg', 'top_speed_kmh', 'top_speed_ms', 'accel_ms2',
  'turn_radius_m', 'seats', 'palette', 'recipe', 'sim_seat', 'trades', 'provenance'];
const missing = reg.fleet.flatMap((e) => FIELDS.filter((k) => !(k in e)).map((k) => `${e.id} lacks ${k}`));
ok('every entry carries every field', missing.length === 0, missing);
const pos = (v) => typeof v === 'number' && Number.isFinite(v) && v > 0;
const badNum = reg.fleet.filter((e) => !(pos(e.dims_m.length) && pos(e.dims_m.width) && pos(e.dims_m.height) && pos(e.mass_kg)
  && pos(e.top_speed_kmh) && pos(e.accel_ms2) && pos(e.turn_radius_m) && Number.isInteger(e.seats) && e.seats > 0));
ok('dims, mass, speed, accel, turn and seats are positive numbers', badNum.length === 0, badNum.map((e) => e.id));
ok('top_speed_ms is DERIVED from top_speed_kmh / 3.6', reg.fleet.every((e) => Math.abs(e.top_speed_ms - e.top_speed_kmh / 3.6) < 0.001));
ok('every entry and the registry say AUTHORED', reg.provenance === 'AUTHORED' && reg.fleet.every((e) => e.provenance === 'AUTHORED'));
const badTok = reg.fleet.flatMap((e) => ['body', 'trim', 'accent'].filter((s) => !(e.palette[s] in reg.colours)).map((s) => `${e.id}.${s}`));
ok('every palette token resolves in the colours table', badTok.length === 0, badTok);
ok('every colour is #rrggbb', Object.values(reg.colours).every((c) => /^#[0-9a-f]{6}$/.test(c)));
const famOf = new Map(reg.families.map((f) => [f.id, f]));
const recipeBad = reg.fleet.filter((e) => !famOf.has(e.family) || JSON.stringify(e.recipe) !== JSON.stringify(famOf.get(e.family).recipe)
  || e.medium !== famOf.get(e.family).medium);
ok('every entry carries its family recipe and medium (one shared geometry per family)', recipeBad.length === 0, recipeBad.map((e) => e.id));
ok('family counts match their entries', reg.families.every((f) => f.count === reg.fleet.filter((e) => e.family === f.id).length));
const ARCH = { land: ['car', 'truck', 'bus', 'machine', 'cycle'], water: ['hull', 'paddle'] };
ok('land recipes have wheels and no hull; water recipes a hull and no wheels', reg.families.every((f) =>
  ARCH[f.medium].includes(f.recipe.archetype) && (f.medium === 'land') === (f.recipe.hull === null) && (f.medium === 'land') === (f.recipe.wheel_r !== null)));
ok('at least 12 land families and 10 watercraft families', reg.families.filter((f) => f.medium === 'land').length >= 12
  && reg.families.filter((f) => f.medium === 'water').length >= 10);

// brand denylist: the twin of fleet/build.py's, applied to every string VALUE
const BRANDS = ['ford', 'chevrolet', 'chevy', 'toyota', 'honda', 'nissan', 'dodge', 'gmc', 'jeep', 'tesla', 'bmw', 'mercedes',
  'benz', 'audi', 'volkswagen', 'vw', 'volvo', 'hyundai', 'kia', 'subaru', 'mazda', 'mitsubishi', 'isuzu', 'hino',
  'freightliner', 'peterbilt', 'kenworth', 'mack', 'navistar', 'scania', 'iveco', 'caterpillar', 'komatsu', 'deere',
  'bobcat', 'kubota', 'jcb', 'hitachi', 'liebherr', 'terex', 'jlg', 'genie', 'hyster', 'linde', 'bayliner', 'whaler',
  'yamaha', 'mercury', 'evinrude', 'suzuki', 'kawasaki', 'polaris', 'harley', 'davidson', 'vespa', 'segway', 'schwinn',
  'gillig', 'oshkosh', 'tennant', 'elgin', 'zodiac', 'sea-doo', 'seadoo', 'porsche', 'ferrari', 'lamborghini', 'jaguar',
  'lexus', 'cadillac', 'buick', 'chrysler', 'fiat', 'renault', 'peugeot', 'citroen', 'skoda', 'seat', 'rivian', 'lucid'];
const brandRe = new RegExp('\\b(' + BRANDS.map((w) => w.replace(/[-]/g, '\\-')).join('|') + ')\\b', 'i');
const brandHits = [];
const scan = (o, p) => {
  if (Array.isArray(o)) o.forEach((v, i) => scan(v, `${p}[${i}]`));
  else if (o && typeof o === 'object') for (const [k, v] of Object.entries(o)) scan(v, `${p}.${k}`);
  else if (typeof o === 'string') {
    const m = o.match(brandRe);
    if (m && !(m[1].toLowerCase() === 'seat' && (p.endsWith('.honesty') || p.endsWith('.sim_seat.kind')))) brandHits.push(`${p}: ${m[1]}`);
  }
};
scan(reg, 'fleet');
ok(`no make/brand word in any registry value (${BRANDS.length} denylisted makes)`, brandHits.length === 0, brandHits);
ok('the builder and this test hold the same denylist', (() => {
  const src = readFileSync(join(ROOT, 'fleet/build.py'), 'utf8');
  const blk = src.slice(src.indexOf('BRAND_DENYLIST = ['), src.indexOf(']', src.indexOf('BRAND_DENYLIST = [')));
  const py = [...blk.matchAll(/'([^']+)'/g)].map((m) => m[1]);
  return py.length === BRANDS.length && py.every((w, i) => w === BRANDS[i]);
})());

// seat links: only to EXISTING seats; href from tasks; trades = the seat's halls
const byTask = new Map(tasks.tasks.map((t) => [t.id, t]));
const linkBad = [];
for (const e of reg.fleet) {
  if (e.sim_seat === null) { if (e.trades !== null) linkBad.push(`${e.id}: trades without a seat`); continue; }
  const s = sims.sims[e.sim_seat.id];
  if (!s) { linkBad.push(`${e.id}: seat ${e.sim_seat.id} is not in sims.json`); continue; }
  const t = byTask.get(`walkaround-${e.sim_seat.id}`);
  if (!t || t.launch.href !== e.sim_seat.href) linkBad.push(`${e.id}: href is not tasks walkaround-${e.sim_seat.id}`);
  if (e.sim_seat.name !== s.name || e.sim_seat.kind !== s.kind) linkBad.push(`${e.id}: seat name/kind drift`);
  if (!e.trades || JSON.stringify(e.trades.halls) !== JSON.stringify(s.halls)) linkBad.push(`${e.id}: trades != sims halls`);
}
ok('every seat link resolves in sims.json, launches via tasks.json, trades = the seat halls', linkBad.length === 0, linkBad);
const machineSeats = Object.entries(sims.sims).filter(([, s]) => s.kind === 'driving').map(([id]) => id);
ok(`every driving seat in sims.json (${machineSeats.join(', ')}) has a fleet entry linked to it`,
  machineSeats.every((sid) => reg.fleet.some((e) => e.sim_seat && e.sim_seat.id === sid)));
ok('family sim_seat agrees with its entries', reg.families.every((f) => reg.fleet.filter((e) => e.family === f.id)
  .every((e) => (e.sim_seat === null ? null : e.sim_seat.id) === f.sim_seat)));

// ------------------------------------------------------------------ kit ---
const dir = mkdtempSync(join(tmpdir(), 'fleetkit-'));
const kitPath = join(dir, 'fleet_kit.mjs');
execFileSync('python3', [join(ROOT, 'web/fleetkit.py'), '--out', kitPath]);
const F = await import(pathToFileURL(kitPath).href);
const THREE = await import(pathToFileURL(join(ROOT, 'web/vendor/three.module.min.js')).href);
// every family renders: non-empty geometry, palette slot colours, inside a sane envelope of its reference size
const renderBad = [];
for (const f of reg.families) {
  const mem = reg.fleet.filter((e) => e.family === f.id);
  const ref = { length: 0, width: 0, height: 0 };
  for (const e of mem) for (const k of Object.keys(ref)) ref[k] += e.dims_m[k] / mem.length;
  try {
    const g = F.fleetFamilyGeometry(THREE, f.recipe, ref);
    const tri = g.attributes.position.count / 3, bb = g.boundingBox;
    const sz = bb.getSize(new THREE.Vector3());
    const nan = Array.from(g.attributes.position.array).some((v) => !Number.isFinite(v));
    if (tri < 12 || nan) renderBad.push(`${f.id}: ${tri} triangles${nan ? ', NaN' : ''}`);
    if (sz.z > ref.length * 1.4 || sz.x > ref.width * 1.6 || sz.y > ref.height * 1.9 || sz.z < ref.length * 0.6)
      renderBad.push(`${f.id}: envelope ${sz.x.toFixed(2)}x${sz.y.toFixed(2)}x${sz.z.toFixed(2)} vs ref ${ref.width.toFixed(2)}x${ref.height.toFixed(2)}x${ref.length.toFixed(2)}`);
    if (!g.attributes.color) renderBad.push(`${f.id}: no palette slot colours`);
    if (tri > 2000) renderBad.push(`${f.id}: ${tri} triangles is not low-poly`);
  } catch (err) { renderBad.push(`${f.id}: ${err.message}`); }
}
ok(`every family (${reg.families.length}) builds a low-poly geometry within its envelope`, renderBad.length === 0, renderBad);
const cap = Object.fromEntries(reg.families.map((f) => [f.id, f.count * 2]));
const fl = F.fleetCreate(THREE, reg, cap);
for (const e of reg.fleet) { fl.spawn(e.id, { x: 0, y: 0, z: 0, yaw: 0 }); fl.spawn(e.id, { x: 5, y: 0, z: 5, yaw: 1 }); }
const meshes = fl.group.children.filter((c) => c.isInstancedMesh && c.visible);
ok(`140 spawned vehicles are ${meshes.length} InstancedMeshes: one draw call per family + one for every wheel, not per vehicle`,
  meshes.length === reg.families.length + 1 && fl.drawCalls() === reg.families.length + 1 && fl.group.children.length === reg.families.length + 1
  && fl.wheels.count === [...fl.families.values()].reduce((t, x) => t + x.mesh.count * F.fleetWheelLayout(x.family.recipe, 1, 1, 1).length, 0));
ok('each family mesh holds exactly its capacity, all in use', [...fl.families.values()].every((x) => x.mesh.count === cap[x.family.id] && x.used === cap[x.family.id]));
ok('an empty family mesh is hidden (no draw call) and shows again on spawn', (() => {
  const f2 = F.fleetCreate(THREE, reg, Object.fromEntries(reg.families.map((f) => [f.id, 1])));
  const vis0 = [...f2.families.values()].filter((x) => x.mesh.visible).length + (f2.wheels.visible ? 1 : 0);
  const h = f2.spawn('bus.school-bus', { x: 0, y: 0, z: 0, yaw: 0 });
  const vis1 = [...f2.families.values()].filter((x) => x.mesh.visible).map((x) => x.family.id);
  h.despawn();
  const vis2 = [...f2.families.values()].filter((x) => x.mesh.visible).length + (f2.wheels.visible ? 1 : 0);
  return vis0 === 0 && vis1.length === 1 && vis1[0] === 'bus' && f2.drawCalls() === 0 && vis2 === 0;
})());
let capErr = '';
try { fl.spawn(reg.fleet[0].id, { x: 0, y: 0, z: 0, yaw: 0 }); } catch (err) { capErr = err.message; }
ok('spawning past capacity throws by name', /at capacity/.test(capErr), [capErr]);
let capMiss = '';
try { F.fleetCreate(THREE, reg, {}); } catch (err) { capMiss = err.message; }
ok('fleetCreate fails closed without a capacity for every family', /capacity has no/.test(capMiss), [capMiss]);

// physics on flat AUTHORED ground: a pond of radius 30 m centred at (0, 60)
const pond = (x, z) => Math.hypot(x, z - 60) < 30;
const G = F.fleetFlatGround(0, 0, pond);
const car = F.fleetSpec(reg.fleet.find((e) => e.medium === 'land' && e.family === 'pickup'));
const boat = F.fleetSpec(reg.fleet.find((e) => e.family === 'skiff'));
const st = F.fleetState(car, G, 0, 0, 0);
let wetSeen = false, yOff = 0;
for (let i = 0; i < 1200; i++) {
  F.fleetStep(st, car, { throttle: 1, steer: 0, brake: 0 }, G, 1 / 60);
  if (pond(st.x, st.z)) wetSeen = true;
  yOff = Math.max(yOff, Math.abs(st.y - G.height(st.x, st.z)));
}
ok(`a land vehicle driven flat out at the pond stays on ground (stopped at z=${st.z.toFixed(1)}, refused ${st.refused}x)`, !wetSeen && st.refused > 0 && st.z < 30 && st.z > 20);
ok('a land vehicle rides the ground height', yOff === 0);
let thrown = '';
try { F.fleetState(car, G, 0, 60, 0); } catch (err) { thrown = err.message; }
ok('a land vehicle cannot be placed on water', /land vehicle stays on ground/.test(thrown), [thrown]);
thrown = '';
try { F.fleetState(boat, G, 0, 0, 0); } catch (err) { thrown = err.message; }
ok('a boat refuses land: it cannot be placed ashore', /boat needs water/.test(thrown), [thrown]);
const bs = F.fleetState(boat, G, 0, 60, 0);
let drySeen = false, ymin = 1e9, ymax = -1e9;
for (let i = 0; i < 1200; i++) {
  F.fleetStep(bs, boat, { throttle: 1, steer: 0, brake: 0 }, G, 1 / 60);
  if (!pond(bs.x, bs.z)) drySeen = true;
  ymin = Math.min(ymin, bs.y); ymax = Math.max(ymax, bs.y);
}
ok(`a boat driven at the shore stays on water (refused ${bs.refused}x)`, !drySeen && bs.refused > 0);
ok(`a boat bobs on the water (y ${ymin.toFixed(3)}..${ymax.toFixed(3)}), never above its waterline + 0.3 m`, ymax - ymin > 0.01 && ymax < boat.draft * -1 + 0.3 && ymin > -boat.draft - 0.3);
ok('a boat under way makes a wake signal', (() => { const s2 = F.fleetState(boat, G, 0, 50, 0); for (let i = 0; i < 60; i++) F.fleetStep(s2, boat, { throttle: 1, steer: 0.3, brake: 0 }, G, 1 / 60); return s2.wake > 0.05; })());
thrown = '';
try { F.fleetLandStep(bs, boat, { throttle: 1, steer: 0, brake: 0 }, G, 0.1); } catch (err) { thrown = err.message; }
ok('fleetLandStep refuses a watercraft by name', /on watercraft/.test(thrown));
ok('exit from a boat mid-pond is null (stay aboard); from the shore it is a dry spot', (() => {
  const mid = F.fleetState(boat, G, 0, 60, 0);
  const edge = F.fleetState(boat, G, 0, 33, Math.PI);
  const p = F.fleetExitPoint(edge, boat, G);
  return F.fleetExitPoint(mid, boat, G) === null && p !== null && !pond(p.x, p.z);
})());
ok('enter finds the vehicle within reach and not beyond', (() => {
  const v = [{ st: F.fleetState(car, G, 0, 0, 0), spec: car }];
  return F.fleetNearest({ x: car.W / 2 + 2, z: 0 }, v, 2.5) === v[0] && F.fleetNearest({ x: car.W / 2 + 4, z: 0 }, v, 2.5) === null;
})());
ok('steer + turns left (anticlockwise from above: yaw grows)', (() => {
  const s = F.fleetState(car, G, -80, -80, 0); for (let i = 0; i < 120; i++) F.fleetStep(s, car, { throttle: 1, steer: 1, brake: 0 }, G, 1 / 60); return s.yaw > 0.2;
})());
ok('a land vehicle never exceeds its top speed', (() => {
  const s = F.fleetState(car, G, -200, -400, 0); let m = 0; for (let i = 0; i < 3000; i++) { F.fleetStep(s, car, { throttle: 1, steer: 0, brake: 0 }, G, 1 / 60); m = Math.max(m, s.v); } return m <= car.top + 1e-9 && m > car.top * 0.9;
})());

// ------------------------------------------------ detail: wheels, lamps, wake, driver seat ---
ok('wheels: every land family has a wheel layout (cycles 2), no watercraft has one', reg.families.every((f) => {
  const n = F.fleetWheelLayout(f.recipe, 4, 2, 2).length;
  return f.medium === 'water' ? n === 0 : f.recipe.archetype === 'cycle' ? n === 2 : n >= 4 && n % 2 === 0;
}));
ok('wheels turn and steer: front wheels yaw with the steer, all wheels spin by distance / radius', (() => {
  const f3 = F.fleetCreate(THREE, reg, Object.fromEntries(reg.families.map((f) => [f.id, 1])));
  const s0 = F.fleetState(car, G, -150, -150, 0);
  for (let i = 0; i < 30; i++) F.fleetStep(s0, car, { throttle: 1, steer: 1, brake: 0 }, G, 1 / 60);
  const h = f3.spawn(car.id, s0), m = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), sc = new THREE.Vector3();
  const yawOf = (slot) => { f3.wheels.getMatrixAt(slot, m); m.decompose(p, q, sc); return new THREE.Euler().setFromQuaternion(q, 'YXZ').y; };
  const lay = F.fleetWheelLayout(car.recipe, car.L, car.W, car.H);
  const front = yawOf(h.wheelSlots[lay.findIndex((w) => w.front)]), rear = yawOf(h.wheelSlots[lay.findIndex((w) => !w.front)]);
  return Math.abs(front - rear - s0.steer * F.FLEET_STEER_VIS) < 1e-3 && s0.steer > 0.5 && Math.abs(s0.spin) > 0.1;
})());
ok('lamps: every family but paddle craft has head (1) and tail (2) lamp faces, drawn unlit-black and emissive', reg.families.every((f) => {
  const mem = reg.fleet.filter((e) => e.family === f.id)[0];
  const g = F.fleetFamilyGeometry(THREE, f.recipe, mem.dims_m), L = g.attributes.fleetLamp.array, C = g.attributes.color.array;
  const kinds = new Set(L);
  const black = [...L].every((k, i) => k === 0 || (C[i * 3] === 0 && C[i * 3 + 1] === 0 && C[i * 3 + 2] === 0));
  return f.recipe.archetype === 'paddle' ? kinds.size === 1 && kinds.has(0) : kinds.has(1) && kinds.has(2) && black;
}));
ok('lamps: fleetLights sets the shared lamp level, clamped 0..1', (() => { fleetLightsProbe(0.4); return fl.material.userData.fleetLampOn.value === 0.4 && (fleetLightsProbe(7), fl.material.userData.fleetLampOn.value === 1); })());
function fleetLightsProbe(v) { F.fleetLights(fl, v); }
ok('wake scales with speed: a fast boat drops more, wider, faster-spreading, brighter rings', (() => {
  const run = (thr) => {
    const w = F.fleetWake(THREE, 256), s1 = F.fleetState(boat, G, -12, 60, Math.PI / 2);
    for (let i = 0; i < 180; i++) { F.fleetStep(s1, boat, { throttle: thr, steer: 0, brake: 0 }, G, 1 / 60); w.emit(s1, boat, 1 / 60); w.update(1 / 60); }
    const live = w.rings.map((r, i) => [r, i]).filter(([r]) => r);
    return { n: live.length, size: Math.max(...live.map(([, i]) => w.size(i))), bright: Math.max(...live.map(([r]) => r.bright)) };
  };
  const slow = run(0.15), fast = run(1);
  return fast.n > slow.n * 2 && fast.size > slow.size && fast.bright > slow.bright;
})());
const eyeBad = [];
for (const e of reg.fleet) {
  const sp = F.fleetSpec(e), eye = F.fleetDriverEye(sp);
  if (Math.abs(eye.x) > sp.W / 2 || Math.abs(eye.z) > sp.L / 2 || eye.y <= 0 || eye.y > sp.H * 1.5 + 0.7) eyeBad.push(`${e.id} ${JSON.stringify(eye)}`);
}
ok('driver camera: every one of the 70 has a driver eye inside its own footprint, above the floor', eyeBad.length === 0, eyeBad);
ok('driver camera follows the heading (yaw pi/2 looks along +x) and sits at the eye', (() => {
  const cam = { position: new THREE.Vector3(), lookAt(x, y, z) { this.look = [x, y, z]; } };
  const s2 = F.fleetState(car, G, 10, 10, Math.PI / 2), w = F.fleetDriverCamera(cam, s2, car);
  return cam.look[0] - w.x > 29 && Math.abs(cam.look[2] - w.z) < 1e-6 && Math.abs(w.y - (s2.y + F.fleetDriverEye(car).y)) < 1e-9;
})());

// ------------------------------------------------------ ambient traffic ---
const lanes = F.fleetGridLanes({ cell: 12, every: 4, x0: -600, x1: 600, z0: -600, z1: 600, step: 6, minLen: 60,
  ok: (x, z) => !pond(x, z) && Math.hypot(x, z - 60) > 42 });
const routes = [...lanes, F.fleetRingLane('pond-ring', 0, 60, 18, 24),
  { id: 'across-the-pond', medium: 'land', points: [[-400, 60], [400, 60]], loop: false, provenance: 'AUTHORED' }];
const TOPTS = { seed: 7, landPerKm: 6, waterPerKm: 30, maxAgents: 140, maxFamilies: 10, radius: 400, speedFactor: 0.4, laneOffset: 1.8 };
const T1 = F.fleetTraffic(THREE, reg, routes, G, TOPTS);
ok(`traffic: AUTHORED grid lanes (${lanes.length}) + a pond ring plan ${T1.agents.length} agents within the budget (${F.FLEET_TRAFFIC_BUDGET.maxAgents})`,
  T1.agents.length > 40 && T1.agents.length <= TOPTS.maxAgents && T1.agents.some((a) => a.spec.medium === 'water') && routes.every((r) => r.provenance === 'AUTHORED'));
ok('traffic: a land route across the pond (density asks for agents) carries none: refused by medium', Math.floor(800 / 1000 * TOPTS.landPerKm) > 0 && !T1.agents.some((a) => routes[a.ri].id === 'across-the-pond'));
let tWet = 0, tDry = 0, tFast = 0, tMaxDraw = 0, tMaxDrawn = 0, tOverlap = 0;
function laneOverlaps(agents) {
  let bad = 0; const by = new Map();
  for (const a of agents) { const k = a.ri + ':' + a.dir; if (!by.has(k)) by.set(k, []); by.get(k).push(a); }
  for (const list of by.values()) for (let i = 0; i < list.length; i++) for (let j = i + 1; j < list.length; j++)
    if (Math.hypot(list[i].x - list[j].x, list[i].z - list[j].z) < (list[i].spec.L + list[j].spec.L) / 2 - 0.5) bad++;
  return bad;
}
for (let i = 0; i < 1800; i++) {
  const eye = { x: Math.sin(i / 300) * 300, z: Math.cos(i / 300) * 300 };
  T1.update(1 / 60, eye);
  for (const a of T1.agents) {
    const d = F.fleetDepth(G, a.x, a.z);
    if (a.spec.medium === 'land' && d > F.FLEET_MIN_WET_M) tWet++;
    if (a.spec.medium === 'water' && d < a.spec.draft + F.FLEET_KEEL_CLEAR_M) tDry++;
    if (a.v > a.spec.top + 1e-9) tFast++;
  }
  if (i >= 600 && i % 30 === 0) tOverlap += laneOverlaps(T1.agents);
  const st2 = T1.stats(); tMaxDraw = Math.max(tMaxDraw, st2.drawCalls); tMaxDrawn = Math.max(tMaxDrawn, st2.drawn);
}
const TS = T1.stats();
ok(`traffic: over 30 s no land agent touches water (${tWet}) and no boat touches land (${tDry})`, tWet === 0 && tDry === 0);
ok('traffic: no agent exceeds its top speed, and they do move', tFast === 0 && T1.agents.filter((a) => a.v > 1).length > T1.agents.length / 3);
ok(`traffic budget: draw calls ${tMaxDraw} <= maxFamilies + 1 wheel mesh (${TOPTS.maxFamilies + 1}); only agents within radius drawn (max ${tMaxDrawn} of ${TS.agents})`,
  tMaxDraw <= TOPTS.maxFamilies + 1 && tMaxDrawn < TS.agents && TS.families <= TOPTS.maxFamilies);
ok(`traffic budget: update ${TS.avgMs.toFixed(3)} ms/frame on average for ${TS.agents} agents (budget ${F.FLEET_TRAFFIC_BUDGET.updateMs} ms)`, TS.avgMs < F.FLEET_TRAFFIC_BUDGET.updateMs);
ok(`traffic: agents on one lane keep their distance (overlapping pairs sampled from 10 s to 30 s: ${tOverlap})`, tOverlap === 0);
ok('traffic is deterministic for a seed', JSON.stringify(F.fleetTraffic(THREE, reg, routes, G, TOPTS).agents.map((a) => a.e.id)) === JSON.stringify(T1.agents.map((a) => a.e.id)));
let over = '';
try { F.fleetTraffic(THREE, reg, routes, G, { ...TOPTS, maxAgents: 500 }); } catch (err) { over = err.message; }
ok('traffic fails closed over budget', /over the budget/.test(over), [over]);

// ------------------------------------------------ wave 6: detail, streets, touch ---
ok('brake lamps are per instance: braking one vehicle lights only its own tail lamps; despawn clears it', (() => {
  const f3 = F.fleetCreate(THREE, reg, Object.fromEntries(reg.families.map((f) => [f.id, 2])));
  const h1 = f3.spawn('pickup.crew-cab-pickup', { x: 0, y: 0, z: 0, yaw: 0 }), h2 = f3.spawn('pickup.crew-cab-pickup', { x: 9, y: 0, z: 0, yaw: 0 });
  h1.set({ x: 0, y: 0, z: 0, yaw: 0, brake: 1 }); h2.set({ x: 9, y: 0, z: 0, yaw: 0, brake: 0 });
  const a = f3.families.get('pickup').attrs.brake, one = h1.brakeLevel() === 1 && h2.brakeLevel() === 0 && a.getX(h1.slot) === 1 && a.getX(h2.slot) === 0;
  h1.set({ x: 0, y: 0, z: 0, yaw: 0, brake: 5 }); const clamped = h1.brakeLevel() === 1;
  const slot = h1.slot; h1.despawn();
  return one && clamped && a.getX(slot) === 0 && f3.drawCalls() === 2;
})());
ok('brake lamps: the shader reads the per-instance fleetBrake and only tail lamps (kind 2) gain FLEET_BRAKE_GAIN', (() => {
  const m = F.fleetMaterial(THREE), sh = { uniforms: {}, vertexShader: '#include <color_vertex>', fragmentShader: '#include <emissivemap_fragment>' };
  m.onBeforeCompile(sh);
  return /attribute float fleetBrake/.test(sh.vertexShader) && /vFleetBrake = fleetBrake/.test(sh.vertexShader)
    && /vFleetLamp > 1\.5 \? FLEET_BRAKE_GAIN \* vFleetBrake/.test(sh.fragmentShader) && F.FLEET_BRAKE_GAIN > 0;
})());
ok('brake lamps from physics: brake input = 1, throttle against motion = 0.7, coasting = 0', (() => {
  const s1 = F.fleetState(car, G, 0, -60, 0);
  for (let i = 0; i < 60; i++) F.fleetStep(s1, car, { throttle: 1, steer: 0, brake: 0 }, G, 1 / 60);
  const cruising = s1.brake;
  F.fleetStep(s1, car, { throttle: 0, steer: 0, brake: 1 }, G, 1 / 60); const braking = s1.brake;
  F.fleetStep(s1, car, { throttle: -1, steer: 0, brake: 0 }, G, 1 / 60); const opposing = s1.brake;
  F.fleetStep(s1, car, { throttle: 0, steer: 0, brake: 0 }, G, 1 / 60);
  return cruising === 0 && braking === 1 && opposing === 0.7 && s1.brake === 0;
})());
ok('brake lamps in traffic: agents that slow behind another light their own lamps, drawn from the agent state', (() => {
  let lit = 0, mism = 0;
  for (let i = 0; i < 600; i++) {
    T1.update(1 / 60, { x: 0, z: 0 });
    for (const a of T1.agents) { if (a.brake === 1) lit++; if (a.h && a.h.brakeLevel() !== a.brake) mism++; }
  }
  return lit > 0 && mism === 0;
})());
const cabBad = [];
for (const f of reg.families) {
  const mem = reg.fleet.filter((e) => e.family === f.id);
  const ref = { length: 0, width: 0, height: 0 };
  for (const e of mem) for (const k of Object.keys(ref)) ref[k] += e.dims_m[k] / mem.length;
  const parts = F.fleetCabParts(f.recipe, ref.length, ref.width, ref.height), g = F.fleetFamilyGeometry(THREE, f.recipe, ref);
  const eye = F.fleetDriverEye({ recipe: f.recipe, L: ref.length, W: ref.width, H: ref.height });
  const has = (k) => parts.filter((q) => q.part === k);
  const a = f.recipe.archetype, cab = ['car', 'bus', 'truck', 'machine'].includes(a) || (a === 'hull' && f.recipe.cab_len > 0);
  if (g.userData.fleetCab !== parts.length) cabBad.push(`${f.id}: geometry holds ${g.userData.fleetCab} cab parts, fleetCabParts says ${parts.length}`);
  if (a === 'cycle') { if (parts.length) cabBad.push(`${f.id}: a cycle has no cab`); continue; }
  if (!has('seat').length || !has('seatback').length) cabBad.push(`${f.id}: no driver seat`);
  if (cab && (has('dash').length !== 1 || has('wheel').length !== 1)) cabBad.push(`${f.id}: cab without one dashboard and one wheel`);
  for (const q of has('dash')) if (!(q.z > eye.z && q.y < eye.y)) cabBad.push(`${f.id}: dashboard not ahead of and below the eye`);
  for (const q of has('wheel')) { const d = has('dash')[0]; if (!(q.z > eye.z && q.z < d.z && q.y < eye.y)) cabBad.push(`${f.id}: wheel not between eye and dashboard`); }
  for (const q of has('seat')) if (!(q.y < eye.y && q.y > 0)) cabBad.push(`${f.id}: seat not under the eye`);
  for (const q of parts) if (Math.abs(q.x) + q.sx / 2 > ref.width / 2 + 1e-6 || Math.abs(q.z) > ref.length / 2) cabBad.push(`${f.id}: ${q.part} outside the footprint`);
}
ok('cab interior: every non-cycle family has a driver seat; every cab has one dashboard ahead and one wheel between eye and dashboard, inside the footprint, built into the SHARED family geometry', cabBad.length === 0, cabBad);
const detail = reg.families.map((f) => [f.id, F.fleetFamilyGeometry(THREE, f.recipe, { length: 4, width: 2, height: 1.6 }).userData.fleetDetail]).filter(([, d]) => d);
ok(`better silhouettes: exactly the five chosen families (${detail.map(([f, d]) => f + '=' + d).join(', ')})`, detail.length === 5
  && detail.every(([f, d]) => F.FLEET_DETAIL[d] === f) && Object.keys(F.FLEET_DETAIL).length === 5);
// AUTHORED street polylines (PARISH_CONTRACT v1.3 shape) as traffic routes, medium-checked
const STREETS = [
  { id: 'across', points: [[-300, 60], [300, 60]], provenance: 'AUTHORED' },          // crosses the pond: split in two
  { id: 'bend', points: [[-200, -40], [0, -40], [0, -240]], provenance: 'AUTHORED' },
  { id: 'stub', points: [[31, 60], [40, 60]], provenance: 'AUTHORED' },               // shorter than minLen after the check
  { id: 'skirt', points: [[-200, 91.5], [200, 91.5]], provenance: 'AUTHORED' },       // centre dry, kerb side wet near x = 0: split
];
const SOPTS = { step: 5, minLen: 40, halfWidth: 3, map: null };
const SR = F.fleetStreetRoutes(STREETS, G, SOPTS);
const srWet = SR.flatMap((r) => r.points).filter(([x, z]) => F.fleetDepth(G, x, z) > F.FLEET_MIN_WET_M || F.fleetDepth(G, x, z + 3) > F.FLEET_MIN_WET_M || F.fleetDepth(G, x, z - 3) > F.FLEET_MIN_WET_M);
ok(`streets: a polyline across the pond is split at the water (${SR.filter((r) => r.source === 'across').length} pieces), a short dry stub dropped, every point dry at +-halfWidth`,
  SR.filter((r) => r.source === 'across').length === 2 && SR.filter((r) => r.source === 'skirt').length === 2 && !SR.some((r) => r.source === 'stub') && SR.some((r) => r.source === 'bend') && srWet.length === 0
  && SR.every((r) => r.medium === 'land' && r.provenance === 'AUTHORED' && r.loop === false));
ok('streets: map() converts the caller\'s coordinates (a +1000 m shift lands the same pieces)', (() => {
  const shifted = STREETS.map((s0) => ({ ...s0, points: s0.points.map(([x, z]) => [x + 1000, z]) }));
  const R2 = F.fleetStreetRoutes(shifted, G, { ...SOPTS, map: ([x, z]) => [x - 1000, z] });
  return JSON.stringify(R2.map((r) => r.points)) === JSON.stringify(SR.map((r) => r.points));
})());
const serr = (streets, o) => { try { F.fleetStreetRoutes(streets, G, o); return ''; } catch (err) { return err.message; } };
ok('streets fail closed: a non-AUTHORED polyline, a missing option or a 1-point street throws by name',
  /not AUTHORED/.test(serr([{ id: 'x', points: [[0, 0], [90, 0]], provenance: 'RECORDED' }], SOPTS))
  && /fleetStreetRoutes has no halfWidth/.test(serr(STREETS, { step: 5, minLen: 40, map: null }))
  && /fewer than 2 points/.test(serr([{ id: 'y', points: [[0, 0]], provenance: 'AUTHORED' }], SOPTS)));
ok('streets carry traffic: 30 s on the street routes, no land agent wet', (() => {
  const T3 = F.fleetTraffic(THREE, reg, SR, G, { ...TOPTS, landPerKm: 20 });
  let wet = 0;
  for (let i = 0; i < 1800; i++) { T3.update(1 / 60, { x: 0, z: 0 }); for (const a of T3.agents) if (F.fleetDepth(G, a.x, a.z) > F.FLEET_MIN_WET_M) wet++; }
  return T3.agents.length > 3 && wet === 0;
})());
// REVIEW finding 4 (wave 6): a boat turning at rest swung its bow over land (only the centre was checked at v = 0)
ok('REVIEW#4: a 60 m ferry 2 m off the shore, steering at rest for 10 s, never swings bow or stern onto land (refused instead)', (() => {
  const shore = (x) => x > 0, GS = F.fleetFlatGround(0, 0, (x, z) => !shore(x, z)), fs = F.fleetSpec(reg.fleet.find((e) => e.id === 'ferry.vehicle-ferry'));
  const s1 = F.fleetState(fs, GS, -2 - fs.W / 2, 0, 0);
  let over = 0;
  for (let i = 0; i < 600; i++) {
    F.fleetStep(s1, fs, { throttle: 0, steer: 1, brake: 0 }, GS, 1 / 60);
    for (const d of [-1, 1]) if (shore(s1.x + Math.sin(s1.yaw) * fs.L / 2 * d)) over++;
  }
  return over === 0 && s1.refused > 0;
})());
ok('REVIEW#4: fleetCanSpawn with a yaw checks both ends (a ferry whose bow reaches land is refused); without a yaw it stays centre-only', (() => {
  const GS = F.fleetFlatGround(0, 0, (x) => x <= 0), fs = F.fleetSpec(reg.fleet.find((e) => e.id === 'ferry.vehicle-ferry'));
  return F.fleetCanSpawn(fs, GS, -10, 0, Math.PI / 2).ok === false && F.fleetCanSpawn(fs, GS, -10, 0, 0).ok === true && F.fleetCanSpawn(fs, GS, -10, 0).ok === true;
})());
// real PARISH v1.3 data: Orleans (22071) arterial + collector polylines, dry = inside the RECORDED coarse outline
ok('streets on real PARISH v1.3 data: Orleans arterials + collectors become medium-checked routes, every point inside the parish (dry) at +-halfWidth', (() => {
  const preg = J('parishes/registry/parishes.json'), par = preg.parishes['22071'], file = J(par.map.streets.path);
  const rings = par.outline_local_m.flat();
  const inside = (x, y) => { let c = false; for (const R of rings) for (let i = 0, j = R.length - 1; i < R.length; j = i++) {
    const [xi, yi] = R[i], [xj, yj] = R[j]; if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c; } return c; };
  const PG = F.fleetFlatGround(0, 0, (x, z) => !inside(x, -z));                       // scene x = east, z = -north
  const streets = F.fleetParishStreets(file, ['arterial', 'collector']);
  const R3 = F.fleetStreetRoutes(streets, PG, { step: 20, minLen: 200, halfWidth: 3.5, map: ([e, n]) => [e, -n] });
  const bad = R3.flatMap((r) => r.points).filter(([x, z]) => !inside(x, -z));
  let refused = ''; try { F.fleetParishStreets({ ...file, provenance: 'RECORDED' }, ['arterial']); } catch (err) { refused = err.message; }
  return streets.length === file.counts.arterial + file.counts.collector && R3.length > 50 && bad.length === 0 && /not AUTHORED/.test(refused);
})());
const SI = F.fleetStickInput;
ok('touch stick: centre = idle; drag left = steer left (+1); up = forward; down = reverse; clamped at the rim; small drags dead',
  JSON.stringify(SI(0, 0, 60, false, false)) === JSON.stringify({ throttle: 0, steer: 0, brake: 0 })
  && SI(-60, 0, 60, false, false).steer === 1 && SI(60, 0, 60, false, false).steer === -1
  && SI(0, -60, 60, false, false).throttle === 1 && SI(0, 60, 60, false, false).throttle === -1
  && SI(-600, 0, 60, false, false).steer === 1 && Math.abs(SI(-300, -300, 60, false, false).steer - Math.SQRT1_2) < 1e-9
  && SI(4, 3, 60, false, false).steer === 0 && SI(4, 3, 60, false, false).throttle === 0);
ok('touch buttons: throttle held = full forward, brake held = brake 1', SI(0, 0, 60, true, false).throttle === 1 && SI(0, 60, 60, true, true).brake === 1 && SI(0, 0, 60, false, true).throttle === 0);
const tcss = F.FLEET_TOUCH_CSS;
ok('touch CSS colours only from theme tokens (no hex, rgb or named colour) and >= 48 px targets', !/#[0-9a-f]{3,8}\b|rgba?\(|hsla?\(|\b(white|black|red|gray|grey)\b/i.test(tcss)
  && /var\(--tc-panel\)/.test(tcss) && /min-height:48px/.test(tcss) && /width:132px/.test(tcss) && /pointer:coarse/.test(tcss));
const terr0 = (() => { try { F.fleetTouchControls(null, null, { group: 'g', stick: 's', throttle: 't', brake: 'b', enter: 'e' }, () => {}); return ''; } catch (err) { return err.message; } })();
ok('touch controls fail closed without every translated label', /touch labels has no exit/.test(terr0), [terr0]);

// on a wilds/core.mjs world: land rides the terrain, and water there refuses it
const W = await import(pathToFileURL(join(ROOT, 'wilds/core.mjs')).href);
const wreg = J('wilds/registry/wilds.json');
const world = wreg.worlds.find((w) => w.biome.model === 'canyon') || wreg.worlds[0];
const terr = W.wildsTerrain(world);
const WG = F.fleetGroundFromWilds(terr, world.biome.water_level_m);
const th = world.trailhead;
const ws = F.fleetState(car, WG, th.x, th.z, 0);
let wOff = 0, wWet = false;
for (let i = 0; i < 900; i++) {
  F.fleetStep(ws, car, { throttle: 1, steer: Math.sin(i / 90) * 0.5, brake: 0 }, WG, 1 / 60);
  wOff = Math.max(wOff, Math.abs(ws.y - terr.height(ws.x, ws.z)));
  if (world.biome.water_level_m - terr.height(ws.x, ws.z) > F.FLEET_MIN_WET_M) wWet = true;
}
ok(`on wilds world ${world.id} a land vehicle rides wildsTerrain().height and stays dry`, wOff < 1e-9 && !wWet);

console.log(bad ? `FAIL  fleet: ${bad} of ${n + bad} checks failed` : `fleet: all ${n} checks passed`);
process.exit(bad ? 1 : 0);
