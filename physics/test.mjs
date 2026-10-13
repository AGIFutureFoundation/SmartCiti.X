/**
 * Physics verification: physics/registry/physics.json against its builder, and
 * web/physkit.py + web/fleetkit.py's crash response run for real in node
 * (deterministic: fixed time steps, no randomness, no browser).
 *
 *   node physics/test.mjs
 *   node physics/test.mjs --root=/tmp/copy      (mutation runs: a broken copy)
 */
import { createHash } from 'node:crypto';
import { readFileSync, mkdtempSync } from 'node:fs';
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
const throwsWith = (f, re) => { try { f(); return false; } catch (e) { return re.test(String(e.message)); } };
const reg = JSON.parse(readFileSync(join(ROOT, 'physics/registry/physics.json'), 'utf8'));
const fleetReg = JSON.parse(readFileSync(join(ROOT, 'fleet/registry/fleet.json'), 'utf8'));

// ------------------------------------------------------------- registry ---
const stamp = createHash('sha256').update(readFileSync(join(ROOT, 'physics/build.py'))).digest('hex').slice(0, 16);
ok(`source_stamp ${reg.source_stamp} is sha256[:16] of physics/build.py`, reg.source_stamp === stamp, [`want ${stamp}`]);
let fresh = true;
try { execFileSync('python3', [join(ROOT, 'physics/build.py'), '--check'], { stdio: 'pipe' }); } catch { fresh = false; }
ok('physics.json is what physics/build.py builds now', fresh);
const coeffs = Object.entries(reg.coeffs).flatMap(([g, grp]) => Object.entries(grp).map(([k, c]) => [g + '.' + k, c]));
const badShape = coeffs.filter(([, c]) => !['value', 'unit', 'provenance', 'note'].every((f) => f in c) || typeof c.value !== 'number');
ok(`every coefficient (${coeffs.length}) has a numeric value, unit, provenance and note`, coeffs.length >= 30 && badShape.length === 0, badShape.map((x) => x[0]));
const notAuthored = coeffs.filter(([k, c]) => (k === 'world.gravity' ? c.provenance !== 'RECORDED' : c.provenance !== 'AUTHORED'));
ok('only world.gravity is RECORDED; every other coefficient is AUTHORED', notAuthored.length === 0, notAuthored.map((x) => x[0]));
ok('gravity is 9.81 m/s^2 (standard gravity, rounded)', reg.coeffs.world.gravity.value === 9.81 && reg.coeffs.world.gravity.unit === 'm/s^2');
ok('honesty says arcade approximation, AUTHORED, not a crash test, never strikes people',
  /arcade approximation/.test(reg.honesty) && /AUTHORED/.test(reg.honesty) && /not a crash test/.test(reg.honesty) && /never strike people, NPCs, pets or animals/.test(reg.honesty));
const kitSrc = readFileSync(join(ROOT, 'web/physkit.py'), 'utf8') + readFileSync(join(ROOT, 'web/fleetkit.py'), 'utf8') + JSON.stringify(reg);
const claims = kitSrc.match(/realistic crash|crash[- ]test rated|safety rating|injur(y|ies) (is|are) shown|drown(s|ing) (is|are) shown/gi) || [];
ok('no realism / safety claim in the kits or the registry', claims.length === 0, claims);

// ------------------------------------------------------------- the kits ---
const dir = mkdtempSync(join(tmpdir(), 'physkit-'));
execFileSync('python3', [join(ROOT, 'web/physkit.py'), '--out', join(dir, 'phys.mjs')]);
execFileSync('python3', [join(ROOT, 'web/fleetkit.py'), '--out', join(dir, 'fleet.mjs')]);
const P = await import(pathToFileURL(join(dir, 'phys.mjs')).href);
const F = await import(pathToFileURL(join(dir, 'fleet.mjs')).href);
const THREE = await import(pathToFileURL(join(ROOT, 'web/vendor/three.module.min.js')).href);
const G = reg.coeffs.world.gravity.value, CW = reg.coeffs.water, CA = reg.coeffs.avatar, CC = reg.coeffs.crash;
ok('pedestrian classes: registry = kit = person/npc/pet/animal', JSON.stringify(reg.pedestrian_classes) === JSON.stringify(P.PHYS_PEDESTRIAN_CLASSES)
  && JSON.stringify(P.PHYS_PEDESTRIAN_CLASSES) === '["person","npc","pet","animal"]');
ok('createPhysics is physCreate and fails closed by name on a missing option',
  P.createPhysics === P.physCreate && throwsWith(() => P.createPhysics({ reg, cell: 16, ground: () => 0 }), /has no water/)
  && throwsWith(() => P.createPhysics({ reg: { ...reg, coeffs: { ...reg.coeffs, avatar: {} } }, cell: 16, ground: () => 0, water: () => null }), /radius/));
const mk = (water = () => null, ground = () => 0) => P.createPhysics({ reg, cell: 16, ground, water });
ok('addBoxes fails closed: missing field and unknown kind throw by name',
  throwsWith(() => mk().addBoxes([{ id: 'a', cx: 0, cz: 0, hx: 1, hz: 1, yaw: 0, y0: 0, kind: 'building' }]), /has no y1/)
  && throwsWith(() => mk().addBoxes([{ id: 'a', cx: 0, cz: 0, hx: 1, hz: 1, yaw: 0, y0: 0, y1: 3, kind: 'tree' }]), /kind tree/));
ok('addBoxes over PHYS_BUDGET.maxBoxes throws', throwsWith(() => mk().addBoxes(Array.from({ length: P.PHYS_BUDGET.maxBoxes + 1 }, (_, i) => ({ id: 'b' + i, cx: i, cz: 0, hx: 0.4, hz: 0.4, yaw: 0, y0: 0, y1: 1, kind: 'prop' }))), /over the budget/));

// grid hash = brute force
{
  const W = mk(); let s = 12345; const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  const boxes = Array.from({ length: 800 }, (_, i) => ({ id: 'g' + i, cx: rnd() * 400 - 200, cz: rnd() * 400 - 200, hx: 1 + rnd() * 8, hz: 1 + rnd() * 8, yaw: rnd() * 6.28, y0: 0, y1: 3 + rnd() * 20, kind: 'building' }));
  W.addBoxes(boxes);
  const miss = [];
  for (let i = 0; i < 300; i++) {
    const x = rnd() * 440 - 220, z = rnd() * 440 - 220, r = rnd() * 6;
    const got = new Set(W.query(x, z, r).map((b) => b.id));
    const want = W.boxes.filter((b) => P.physBoxClosest(b, x, z).d < r).map((b) => b.id);
    if (want.length !== got.size || want.some((id) => !got.has(id))) miss.push(`${x.toFixed(1)},${z.toFixed(1)} r${r.toFixed(1)}: ${want.length} vs ${got.size}`);
  }
  ok('grid-hash query equals a brute-force scan (300 random probes, 800 rotated boxes)', miss.length === 0, miss);
}

// falling, jumping
const idle = { vx: 0, vz: 0, jump: false };
function fall(W, av, dt) { let t = 0; while (!av.onGround && t < 10) { W.stepAvatar(av, idle, dt); t += dt; } return t; }
{
  const bad = [];
  for (const [h, dt] of [[20, 1 / 60], [20, 1 / 120], [5, 1 / 60], [80, 1 / 30]]) {
    const av = P.physAvatar(0, h, 0), t = fall(mk(), av, dt), want = Math.sqrt(2 * h / G);
    if (Math.abs(t - want) > Math.max(2 * dt, 0.02 * want) || av.y !== 0) bad.push(`h ${h} dt ${dt.toFixed(4)}: ${t.toFixed(3)} s vs ${want.toFixed(3)} s, y ${av.y}`);
  }
  ok('a fall from 5/20/80 m reaches the ground at sqrt(2h/g) (within 2 steps or 2 %)', bad.length === 0, bad);
}
{
  const W = mk(); W.addBoxes([{ id: 'roof', cx: 0, cz: 0, hx: 5, hz: 5, yaw: 0.3, y0: 0, y1: 12, kind: 'building' }]);
  const av = P.physAvatar(1, 30, 1); fall(W, av, 1 / 60);
  ok('falling onto a building lands on its roof (solid box top)', Math.abs(av.y - 12) < 1e-9, [`y ${av.y}`]);
}
{
  const W = mk(), av = P.physAvatar(0, 0, 0); fall(W, av, 1 / 60);
  let apex = 0, t = 0; W.stepAvatar(av, { vx: 0, vz: 0, jump: true }, 1 / 240);
  while (!av.onGround && t < 3) { W.stepAvatar(av, idle, 1 / 240); apex = Math.max(apex, av.y); t += 1 / 240; }
  const want = CA.jump_speed.value ** 2 / (2 * G);
  ok(`a jump peaks at v^2/2g = ${want.toFixed(3)} m (within 3 %) and lands again`, Math.abs(apex - want) < 0.03 * want && av.onGround, [`apex ${apex}`]);
}
// no tunnelling, sliding, step-up
{
  const bad = [];
  for (const dt of [1 / 60, 1 / 30, 1 / 10]) {
    const W = mk(); W.addBoxes([{ id: 'wall', cx: 10, cz: 0, hx: 0.15, hz: 20, yaw: 0, y0: 0, y1: 3, kind: 'wall' }]);
    const av = P.physAvatar(0, 0, 0); av.onGround = true;
    for (let i = 0; i < 120; i++) { W.stepAvatar(av, { vx: 40, vz: 0, jump: false }, dt); if (av.x > 10 - 0.15 - CA.radius.value + 1e-3) bad.push(`dt ${dt}: x ${av.x}`); }
  }
  ok('avatar at 40 m/s into a 0.3 m wall never tunnels (dt 1/60, 1/30, 1/10)', bad.length === 0, bad);
}
{
  const W = mk(); W.addBoxes([{ id: 'wall', cx: 5, cz: 0, hx: 0.5, hz: 50, yaw: 0, y0: 0, y1: 4, kind: 'building' }]);
  const av = P.physAvatar(0, 0, 0); av.onGround = true;
  for (let i = 0; i < 180; i++) W.stepAvatar(av, { vx: 3, vz: 3, jump: false }, 1 / 60);
  ok('walking diagonally into a wall slides along it (x held at the wall, z keeps moving)', av.x < 4.5 && av.x > 4.1 && av.z > 5, [`x ${av.x} z ${av.z}`]);
}
{
  const W = mk(); W.addBoxes([{ id: 'curb', cx: 5, cz: 0, hx: 1, hz: 20, yaw: 0, y0: 0, y1: 0.15, kind: 'curb' },
    { id: 'plinth', cx: 5, cz: 30, hx: 1, hz: 5, yaw: 0, y0: 0, y1: 0.6, kind: 'barrier' }]);
  const a = P.physAvatar(0, 0, 0); a.onGround = true;
  for (let i = 0; i < 120; i++) W.stepAvatar(a, { vx: 2.5, vz: 0, jump: false }, 1 / 60);
  const b = P.physAvatar(0, 0, 30); b.onGround = true;
  for (let i = 0; i < 120; i++) W.stepAvatar(b, { vx: 2.5, vz: 0, jump: false }, 1 / 60);
  ok('steps up a 0.15 m curb without a jump; a 0.6 m block stops the walker', a.x > 4.5 && Math.abs(a.y - 0.15) < 1e-9 && b.x < 4 && b.y === 0, [`curb x ${a.x} y ${a.y}`, `block x ${b.x} y ${b.y}`]);
}
// water
ok(`water thresholds: dry < ${CW.wade_min.value} m <= wade < ${CW.swim_depth.value} m <= swim`,
  P.physWaterState(0, P.physCoeffs(reg)) === 'dry' && P.physWaterState(CW.wade_min.value - 0.01, P.physCoeffs(reg)) === 'dry'
  && P.physWaterState(CW.wade_min.value, P.physCoeffs(reg)) === 'wade' && P.physWaterState(CW.swim_depth.value - 0.01, P.physCoeffs(reg)) === 'wade'
  && P.physWaterState(CW.swim_depth.value, P.physCoeffs(reg)) === 'swim' && P.physWaterState(NaN, P.physCoeffs(reg)) === 'dry');
{
  // a pond: x 10..50, bed slopes from 0 m at x=10 to -3 m at x=30 (surface 0)
  const bed = (x) => -Math.min(3, (x - 10) * 0.15);
  const W = mk((x, z) => (x > 10 && x < 50 && Math.abs(z) < 30 ? { surface: 0, bed: bed(x) } : null));
  const av = P.physAvatar(0, 0, 0); av.onGround = true;
  const seen = [], states = new Set(); let headUnder = 0;
  for (let i = 0; i < 60 * 25; i++) {
    const out = i < 60 * 12 ? 3 : -3;
    for (const e of W.stepAvatar(av, { vx: out, vz: 0, jump: false }, 1 / 60)) seen.push(e.type);
    states.add(av.water);
    if (av.water === 'swim' && av.y + CA.height.value <= 0) headUnder++;
  }
  ok('walking into a pond goes dry -> wade -> swim (enter-water, swim events) and back out (climb-out, leave-water)',
    ['enter-water', 'swim', 'climb-out', 'leave-water'].every((t) => seen.includes(t)) && states.has('wade') && states.has('swim') && av.water === 'dry', [seen.join(',')]);
  ok('a swimmer always floats with the head above the surface (no drowning)', headUnder === 0 && states.has('swim'), [`${headUnder} steps under`]);
}
{
  const W = mk((x) => (x > 0 ? { surface: 0, bed: -4 } : null));
  const av = P.physAvatar(-1, 5, 0); av.onGround = false;
  const ev = [];
  for (let i = 0; i < 240; i++) ev.push(...W.stepAvatar(av, { vx: 2, vz: 0, jump: false }, 1 / 60));
  const sp = ev.find((e) => e.type === 'splash');
  ok('jumping into deep water from 5 m splashes (strength > 0.5) and ends swimming', sp && sp.strength > 0.5 && av.water === 'swim', [JSON.stringify(ev.slice(0, 4))]);
}
// rigid bodies
{
  const W = mk(), b = P.physBody({ shape: 'sphere', x: 0, y: 10, z: 0, r: 0.3, mass: 2 });
  let impact = 0, rebound = null;
  for (let i = 0; i < 240 * 10; i++) {
    const vBefore = b.vy; W.stepBody(b, 1 / 240);
    if (rebound === null && vBefore < 0 && b.vy > 0) { impact = -vBefore; rebound = b.vy; }
  }
  const e = reg.coeffs.body.restitution.value;
  ok(`a sphere bounces with the AUTHORED restitution ${e} (rebound/impact within 5 %) and comes to rest on the ground`,
    rebound !== null && Math.abs(rebound / impact - e) < 0.05 && Math.abs(b.y - 0.3) < 1e-6 && Math.hypot(b.vx, b.vy, b.vz) === 0, [`${rebound}/${impact} y ${b.y}`]);
}
{
  const W = mk(); W.addBoxes([{ id: 'w', cx: 10, cz: 0, hx: 0.15, hz: 10, yaw: 0, y0: 0, y1: 5, kind: 'wall' }]);
  const b = P.physBody({ shape: 'box', x: 0, y: 1, z: 0, r: 0.25, mass: 1 }); b.vx = 40;
  let maxX = -1, hits = 0;
  for (let i = 0; i < 90; i++) { hits += W.stepBody(b, 1 / 30).filter((e) => e.with === 'wall').length; maxX = Math.max(maxX, b.x); }
  ok('a body thrown at 40 m/s into a 0.3 m wall bounces back (no tunnelling, one hit event)', maxX <= 10 - 0.15 && b.vx <= 0 && hits >= 1, [`maxX ${maxX} vx ${b.vx}`]);
}
{
  const W = mk(() => ({ surface: 0, bed: -10 })), b = P.physBody({ shape: 'sphere', x: 0, y: 3, z: 0, r: 0.5, mass: 5 });
  for (let i = 0; i < 60 * 20; i++) W.stepBody(b, 1 / 60);
  ok('a body dropped into deep water floats near the surface (AUTHORED buoyancy)', Math.abs(b.y) < 0.5, [`y ${b.y}`]);
}
// ------------------------------------------- PARISH v1.4 real world data ---
{
  const par = JSON.parse(readFileSync(join(ROOT, 'parishes/registry/parishes.json'), 'utf8'));
  const wf = JSON.parse(readFileSync(join(ROOT, 'parishes/maps/world/22071.json'), 'utf8'));
  const origin = par.parishes['22071'].frame.origin_in_world_m;
  const water = P.physWaterFromWorld(wf, origin);
  const pond = wf.water.ponds[0];
  const [pe, pn] = pond.centre, px = pe + origin[0], pz = -(pn + origin[1]);
  const at = water(px, pz), far = water(px + pond.radius_m + 40, pz);
  ok(`Orleans world water: ${water.features} AUTHORED features; a pond centre is water at surface ${wf.water.surface_y_m} m, bed ${(wf.water.surface_y_m - pond.depth_m).toFixed(2)} m; outside is dry`,
    water.features === wf.water.lakes.length + wf.water.channels.length + wf.water.ponds.length && at && at.surface === wf.water.surface_y_m
    && Math.abs(at.bed - (wf.water.surface_y_m - pond.depth_m)) < 1e-9 && far === null, [JSON.stringify(at), JSON.stringify(far)]);
  // walk from the bank into the deepest AUTHORED feature and back out onto the 0 m ground
  const deep = [...wf.water.channels, ...wf.water.ponds].sort((a, b) => b.depth_m - a.depth_m)[0];
  const W = mk(water);
  const c = deep.centre.length === 2 && typeof deep.centre[0] === 'number' ? deep.centre : deep.centre[Math.floor(deep.centre.length / 2)];
  const cx = c[0] + origin[0], cz = -(c[1] + origin[1]);
  let sx = cx, sz = cz; for (let d = 0; d < 400 && water(sx, sz); d += 1) sx = cx + d;   // first dry point east
  sx += 3;
  const av = P.physAvatar(sx, 0, sz); av.onGround = true;
  const seen = new Set(), states = new Set();
  for (let i = 0; i < 60 * 40; i++) {
    const toC = i < 60 * 15 ? -1 : 1, v = Math.abs(av.x - cx) < 0.5 && toC < 0 ? 0 : 2 * toC;
    for (const e of W.stepAvatar(av, { vx: v, vz: 0, jump: false }, 1 / 60)) seen.add(e.type);
    states.add(av.water);
  }
  const needSwim = deep.depth_m >= reg.coeffs.water.swim_depth.value;
  ok(`walking into ${deep.id} (${deep.depth_m} m deep) and back: ${needSwim ? 'wade, swim, climb-out' : 'wade, leave-water'}, ending dry on the 0 m bank`,
    seen.has('enter-water') && states.has('wade') && (!needSwim || (states.has('swim') && seen.has('climb-out'))) && av.water === 'dry' && av.y === 0,
    [[...seen].join(','), [...states].join(','), `y ${av.y} x ${av.x} start ${sx}`]);
  // buildings: the chunk block mapping WILDS hands over; curbs from a road profile are stepped onto
  const boxes = P.physBlockBoxes('c:0:0', [[10, 20, 8, 12, 6, 'house', 0.3, 0]]);
  ok('physBlockBoxes maps [x, z, w, h, d, family, yaw] to a solid building box (PARISH v1.4 mapping)',
    JSON.stringify(boxes[0]) === JSON.stringify({ id: 'c:0:0:0', cx: 10, cz: 20, hx: 4, hz: 3, yaw: 0.3, y0: 0, y1: 12, kind: 'building' }));
  const prof = wf.roads.classes.collector, W2 = mk();
  W2.addBoxes(P.physCurbBoxes('s', [[[0, -50], [0, 50]]], prof));
  const walker = P.physAvatar(0, 0, 0); walker.onGround = true;
  for (let i = 0; i < 210; i++) W2.stepAvatar(walker, { vx: 2, vz: 0, jump: false }, 1 / 60);
  ok(`a ${prof.curb_height_m} m curb/sidewalk from the collector profile is stepped onto (walker on the sidewalk top)`,
    walker.x > prof.carriageway_m / 2 + 0.5 && walker.x < prof.corridor_m / 2 && Math.abs(walker.y - prof.curb_height_m) < 1e-9, [`x ${walker.x} y ${walker.y}`]);
}
// ------------------------------------------------------------- crashes ---
const spec = (id) => F.fleetSpec(fleetReg.fleet.find((e) => e.id === id));
const ground = F.fleetFlatGround(0, 0, () => false);
const sedan = spec('compact-car.sedan'), pickup = spec('pickup.crew-cab-pickup'), bus = spec('bus.transit-bus');
const momentum = (xs) => xs.reduce((t, [st, sp]) => { const [vx, vz] = F.fleetVel(st); return [t[0] + sp.mass * vx, t[1] + sp.mass * vz]; }, [0, 0]);
{
  const bad = []; let spun = 0, maxSpin = 0;
  const cases = [[sedan, pickup, 0, 18, -1.2], [sedan, bus, 0.7, 25, 0.8], [pickup, pickup, 1.57, 12, 2.0], [bus, sedan, -0.4, 30, -0.5]];
  for (const [sa, sb, yawB, v, off] of cases) {
    const a = F.fleetState(sa, ground, 0, 0, 0), b = F.fleetState(sb, ground, off, 30, yawB);
    while (!F.fleetSat(F.fleetBox(a, sa), F.fleetBox(b, sb))) b.z -= 0.05;   // slide b in until the boxes first touch
    b.z -= 0.1;
    a.v = v; b.v = -v * 0.2;
    const p0 = momentum([[a, sa], [b, sb]]);
    const ev = F.fleetCollideVehicles(a, sa, b, sb, F.fleetCrashCoeffs(reg), ground);
    const p1 = momentum([[a, sa], [b, sb]]), scale = Math.hypot(...p0);
    if (!ev || Math.hypot(p1[0] - p0[0], p1[1] - p0[1]) > 1e-9 * scale) bad.push(`${sa.id} vs ${sb.id}: ${p0} -> ${p1}`);
    if (Math.abs(a.yawRate) > 1e-3 || Math.abs(b.yawRate) > 1e-3) spun++;
    maxSpin = Math.max(maxSpin, Math.abs(a.yawRate), Math.abs(b.yawRate));
  }
  ok('vehicle-vs-vehicle impulse conserves linear momentum (4 cases, within 1e-9)', bad.length === 0, bad);
  ok('off-centre crashes add yaw spin, capped at crash.max_spin', spun === cases.length && maxSpin <= CC.max_spin.value, [`${spun}/${cases.length} max ${maxSpin}`]);
}
{
  const C = F.fleetCrashCoeffs(reg), dents = [1, 5, 20, 40].map((v) => {
    const a = F.fleetState(sedan, ground, 0, 0, 0), b = F.fleetState(sedan, ground, 0, sedan.L - 0.2, Math.PI);
    a.v = v / 2; b.v = v / 2; F.fleetCollideVehicles(a, sedan, b, sedan, C, ground); return a;
  });
  ok('dent grows with impact speed (none below dent_min_ms), crumple never exceeds crumple_max',
    dents[0].dent === 0 && dents[1].dent > 0 && dents[2].dent > dents[1].dent && dents[3].dent >= dents[2].dent && dents.every((s) => s.crumple <= CC.crumple_max.value + 1e-12),
    dents.map((s) => s.dent.toFixed(3)));
}
function physCtx(world, people = [], others = []) { const events = []; return { ctx: { coeffs: reg, world, others, people, onEvent: (e) => events.push(e) }, events }; }
{
  const bad = []; let staticEv = 0, smoke = 0;
  for (const dt of [1 / 60, 1 / 30, 1 / 10]) {
    const W = mk(); W.addBoxes([{ id: 'barrier', cx: 0, cz: 30, hx: 10, hz: 0.15, yaw: 0, y0: 0, y1: 1.2, kind: 'barrier' }]);
    const st = F.fleetState(sedan, ground, 0, 0, 0); st.v = 40;
    const { ctx, events } = physCtx(W);
    for (let i = 0; i < 90; i++) { F.fleetPhysStep(st, sedan, { throttle: 1, steer: 0, brake: 0 }, ground, dt, ctx); if (st.z + sedan.L / 2 > 30 - 0.15 + 0.05) bad.push(`dt ${dt}: front at ${(st.z + sedan.L / 2).toFixed(2)}`); }
    staticEv += events.filter((e) => e.with === 'static').length; smoke += events.filter((e) => e.smoke).length;
  }
  ok('a vehicle at 40 m/s into a 0.3 m barrier never passes through (dt 1/60, 1/30, 1/10)', bad.length === 0, bad);
  ok('the barrier crash emits static crash events with smoke', staticEv >= 3 && smoke >= 3, [`${staticEv} events, ${smoke} smoke`]);
}
{
  const W = mk(); W.addBoxes([{ id: 'curb', cx: 0, cz: 20, hx: 10, hz: 0.3, yaw: 0, y0: 0, y1: 0.15, kind: 'curb' }]);
  const st = F.fleetState(sedan, ground, 0, 0, 0); st.v = 10;
  const { ctx, events } = physCtx(W);
  for (let i = 0; i < 180; i++) F.fleetPhysStep(st, sedan, { throttle: 0.3, steer: 0, brake: 0 }, ground, 1 / 60, ctx);
  ok('a curb no taller than crash.wheel_step is driven over (no crash)', st.z > 30 && events.length === 0, [`z ${st.z}`, JSON.stringify(events[0])]);
}
{
  const bad = [], yields = new Set();
  for (const cls of P.PHYS_PEDESTRIAN_CLASSES) for (const [v0, dist, dt, lat] of [[10, 30, 1 / 60, 0], [40, 12, 1 / 30, 0.5], [40, 4, 1 / 10, -0.8], [5, 8, 1 / 60, 1.4]]) {
    const person = { x: lat, z: dist, r: cls === 'pet' ? 0.25 : 0.35, cls };
    const st = F.fleetState(sedan, ground, 0, 0, 0); st.v = v0;
    const { ctx, events } = physCtx(null, [person]);
    for (let i = 0; i < 300; i++) {
      F.fleetPhysStep(st, sedan, { throttle: 1, steer: 0, brake: 0 }, ground, dt, ctx);
      if (F.fleetPeopleHit(st, sedan, [person], 0)) { bad.push(`${cls} v${v0} d${dist}: contact at step ${i}`); break; }
    }
    if (events.some((e) => e.type === 'yield' && e.cls === cls)) yields.add(cls);
  }
  ok('a vehicle driven flat out at a person/NPC/pet/animal never touches it (16 runs, up to 40 m/s)', bad.length === 0, bad);
  ok('the vehicle emits a yield event for every pedestrian class', yields.size === 4, [...yields]);
}
{
  // a struck vehicle is never shoved into a person either
  const a = F.fleetState(bus, ground, 0, 0, 0), b = F.fleetState(sedan, ground, 0, bus.L / 2 + sedan.L / 2 + 0.5, 0); a.v = 20;
  const person = { x: 0, z: b.z + sedan.L / 2 + 0.6, r: 0.3, cls: 'npc' };
  const { ctx } = physCtx(null, [person], [{ st: b, spec: sedan }]);
  let touched = 0;
  for (let i = 0; i < 120; i++) { F.fleetPhysStep(a, bus, { throttle: 1, steer: 0, brake: 0 }, ground, 1 / 60, ctx); if (F.fleetPeopleHit(b, sedan, [person], 0) || F.fleetPeopleHit(a, bus, [person], 0)) touched++; }
  ok('a crash never pushes the struck vehicle into a person', touched === 0, [`${touched} steps in contact`]);
  ok('an unknown pedestrian class throws by name', throwsWith(() => F.fleetPhysStep(a, bus, { throttle: 0, steer: 0, brake: 0 }, ground, 1 / 60, physCtx(null, [{ x: 0, z: 0, r: 1, cls: 'cyclist' }]).ctx), /unknown pedestrian class cyclist/));
}
{
  // a 3 m drop: ground 3 m for z < 20, 0 m beyond
  const g2 = { height: (x, z) => (z < 20 ? 3 : 0), waterLevel: () => null };
  const st = F.fleetState(pickup, g2, 0, 10, 0); st.v = 15;
  const { ctx, events } = physCtx(null);
  let air = 0, maxPitch = 0, t = 0, tLeave = null, tLand = null;
  for (let i = 0; i < 240; i++) {
    F.fleetPhysStep(st, pickup, { throttle: 0, steer: 0, brake: 0 }, g2, 1 / 120, ctx); t += 1 / 120;
    if (st.air) { air++; maxPitch = Math.max(maxPitch, Math.abs(st.pitch)); if (tLeave === null) tLeave = t; }
    else if (tLeave !== null && tLand === null) tLand = t;
  }
  const want = Math.sqrt(2 * 3 / G), got = tLand - tLeave;
  ok(`driving off a 3 m drop: airborne, tumbles, lands after ~sqrt(2h/g) = ${want.toFixed(3)} s (within 10 %), ground crash event, upright after`,
    air > 0 && maxPitch > 0.02 && Math.abs(got - want) < 0.1 * want && events.some((e) => e.with === 'ground') && Math.abs(st.pitch) < 1e-9 && st.y === 0,
    [`air ${air} pitch ${maxPitch} t ${got}`, `pitch after ${st.pitch}`]);
}
{
  // boats crash too and keep bobbing
  const pond = F.fleetFlatGround(-5, 0, () => true);
  const sk = spec('skiff.center-console-skiff');
  const a = F.fleetState(sk, pond, 0, 0, 0), b = F.fleetState(sk, pond, 0.5, sk.L / 2 + sk.W / 2 - 0.3, Math.PI / 2); a.v = 8;
  const p0 = momentum([[a, sk], [b, sk]]);
  const ev = F.fleetCollideVehicles(a, sk, b, sk, F.fleetCrashCoeffs(reg), pond);
  const p1 = momentum([[a, sk], [b, sk]]);
  const ys = new Set(); const { ctx } = physCtx(null);
  for (let i = 0; i < 60; i++) { F.fleetPhysStep(b, sk, { throttle: 0, steer: 0, brake: 0 }, pond, 1 / 30, ctx); ys.add(b.y.toFixed(3)); }
  ok('boat-vs-boat crash conserves momentum and the struck boat keeps bobbing on the water', ev && Math.hypot(p1[0] - p0[0], p1[1] - p0[1]) < 1e-9 * Math.hypot(...p0) && ys.size > 10);
}
{
  // ambient traffic: a player crash stops an agent, it resets after crash.reset_s, and nobody is left jammed
  const routes = [{ id: 'street', medium: 'land', points: [[0, 0], [0, 800]], loop: false, provenance: 'AUTHORED' }];
  const tr = F.fleetTraffic(THREE, fleetReg, routes, ground, { seed: 3, landPerKm: 10, waterPerKm: 0, maxAgents: 8, maxFamilies: 6, radius: 2000, speedFactor: 0.4, laneOffset: 2 });
  for (let i = 0; i < 60; i++) tr.update(1 / 30, { x: 0, z: 0 });
  const target = tr.agents[0];
  const me = F.fleetState(pickup, ground, target.x + 0.5, target.z, target.yaw + Math.PI / 2); me.v = 10;
  const events = []; const ctx = { coeffs: reg, people: [], others: [{ st: me, spec: pickup }], onEvent: (e) => events.push(e) };
  tr.update(1 / 30, { x: 0, z: 0 }, ctx);
  const crashed = target.crashT > 0 && target.v === 0 && events.some((e) => e.type === 'crash' && e.with === 'vehicle');
  me.x = 500; me.z = -500;   // the player drives off
  let t = 0; while (t < CC.reset_s.value + 1) { tr.update(1 / 30, { x: 0, z: 0 }, ctx); t += 1 / 30; }
  const back = target.crashT === 0 && target.dent === 0 && target.resets >= 1;
  for (let i = 0; i < 30 * 20; i++) tr.update(1 / 30, { x: 0, z: 0 }, ctx);
  const moving = tr.agents.filter((a) => a.v > 0.5).length;
  ok('a player crash stops an ambient agent (crash event), it resets after crash.reset_s and traffic moves again',
    crashed && back && moving >= tr.agents.length - 1, [`crashed ${crashed} back ${back} moving ${moving}/${tr.agents.length}`]);
  // a person on the street: agents stop and never touch them
  const person = { x: tr.agents[1].x, z: tr.agents[1].z + 25, r: 0.35, cls: 'animal' };
  const ctx2 = { coeffs: reg, people: [person], others: [], onEvent: () => {} };
  let touch = 0;
  for (let i = 0; i < 30 * 30; i++) { tr.update(1 / 30, { x: 0, z: 0 }, ctx2); touch += tr.agents.filter((a) => F.fleetPeopleHit(a, a.spec, [person], 0)).length; }
  ok('ambient traffic never touches a person/animal standing on the street (30 s)', touch === 0, [`${touch} contacts`]);
}
{
  const t1 = F.fleetCrashTone({ speed: 2, with: 'vehicle' }), t2 = F.fleetCrashTone({ speed: 15, with: 'static' }), t3 = F.fleetCrashTone({ speed: 90, with: 'vehicle' });
  const sm = F.fleetSmoke(THREE, 32); sm.puff(0, 1, 0, 1); const alive = sm.update(0.1); for (let i = 0; i < 100; i++) sm.update(0.1);
  ok('sound hook params rise with speed (gain <= 1); smoke puffs are one InstancedMesh and fade out',
    t1.gain < t2.gain && t3.gain === 1 && t2.low && !t1.low && sm.mesh.isInstancedMesh && alive > 0 && sm.mesh.visible === false);
}
// ------------------------------------------------------------- budgets ---
{
  const W = mk(); let s = 99; const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  W.addBoxes(Array.from({ length: 20000 }, (_, i) => ({ id: 'c' + i, cx: rnd() * 3000 - 1500, cz: rnd() * 3000 - 1500, hx: 3 + rnd() * 6, hz: 3 + rnd() * 6, yaw: rnd() * 3, y0: 0, y1: 4 + rnd() * 30, kind: 'building' })));
  const av = P.physAvatar(0, 0, 0); av.onGround = true;
  const t0 = performance.now();
  for (let i = 0; i < 3000; i++) W.stepAvatar(av, { vx: 6 * Math.cos(i / 200), vz: 6 * Math.sin(i / 200), jump: i % 300 === 0 }, 1 / 60);
  const avMs = (performance.now() - t0) / 3000;
  const st = F.fleetState(sedan, ground, 0, 0, 0); const { ctx } = physCtx(W, [{ x: 50, z: 50, r: 0.3, cls: 'person' }]);
  const t1 = performance.now();
  for (let i = 0; i < 3000; i++) F.fleetPhysStep(st, sedan, { throttle: 1, steer: Math.sin(i / 100), brake: 0 }, ground, 1 / 60, ctx);
  const vMs = (performance.now() - t1) / 3000;
  ok(`budget: avatar step ${avMs.toFixed(3)} ms <= ${P.PHYS_BUDGET.avatarMs} ms and a vehicle phys step ${vMs.toFixed(3)} ms <= 0.1 ms among 20,000 boxes`,
    avMs <= P.PHYS_BUDGET.avatarMs && vMs <= 0.1);
}

console.log(bad ? `physics: ${bad} of ${n + bad} checks FAILED` : `physics: all ${n} checks passed`);
process.exit(bad ? 1 : 0);
