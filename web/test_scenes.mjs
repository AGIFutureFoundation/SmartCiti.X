/**
 * Interiors and exteriors (wave 17): the hall fit-out and the building kit RUN, against the real registries,
 * without a browser.
 *
 * Same method as web/test_builddress.mjs: take the BUILT page (web/trade_craft_3d.html), lift the wave-17
 * blocks out of its module by their neutral markers, and run them in Node on the vendored three.js and its own
 * BufferGeometryUtils with the page's own payload. What it proves for the INTERIOR kit:
 *
 *   - every district has a row for every strand a hall has, and every piece a row names builds from its
 *     recipe at exactly the triangles the props registry states;
 *   - a hall's district pieces become ONE mesh with ONE material, whose triangles are the pieces' triangles
 *     and whose per-room index ranges tile the index exactly;
 *   - the distance cull: from the hall's orbit camera nothing is drawn (so the orbit views the hall
 *     ceilings are scored on pay nothing); standing in a room draws that room and only rooms within the
 *     kit's near distance, and the index it draws is those rooms' own slices;
 *   - the props pack's own wanted/skipped tallies are handed back untouched.
 *
 *   node web/test_scenes.mjs
 */
import { readFileSync, writeFileSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const HERE = fileURLToPath(new URL('.', import.meta.url));
const page = readFileSync(join(HERE, 'trade_craft_3d.html'), 'utf8');
const dm = page.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/);
if (!dm) { console.error('FAIL the built page carries no data script'); process.exit(1); }
const D = JSON.parse(dm[1]);

const THREE = await import(pathToFileURL(join(HERE, 'vendor/three.module.min.js')).href);
const tmp = mkdtempSync(join(tmpdir(), 'tc-scenes-'));
let mergeGeometries;
try {
  const bgu = readFileSync(join(HERE, 'vendor/addons/utils/BufferGeometryUtils.js'), 'utf8')
    .replace(/from 'three';/, `from '${pathToFileURL(join(HERE, 'vendor/three.module.min.js')).href}';`);
  writeFileSync(join(tmp, 'bgu.mjs'), bgu);
  ({ mergeGeometries } = await import(pathToFileURL(join(tmp, 'bgu.mjs')).href));
} finally { rmSync(tmp, { recursive: true, force: true }); }

const mod = page.slice(page.indexOf("import * as THREE from 'three';"));
const lift = (name) => {
  const i = mod.indexOf(`\nfunction ${name}(`);
  if (i < 0) { console.error('FAIL the built module has no top-level function', name); process.exit(1); }
  return mod.slice(i, mod.indexOf('\n}\n', i + 1) + 2);
};
// a whole module-level block between its neutral markers - an absent one is a failure
const block = (marker) => {
  const a = mod.indexOf(`/* ${marker} BEGIN (wave 17) */\n`);
  const b = mod.indexOf(`\n/* ${marker} END */`, a);
  if (a < 0 || b < 0) { console.error('FAIL the built module has no module-level', marker, 'block'); process.exit(1); }
  return mod.slice(a, b);
};

/* ------------------------------------------------------------ interiors -- */
ok('the built page carries no team codename in its wave-17 markers', !/SCENES/.test(page));
const IK = D.interiorKit;
ok('the payload carries the district fit-out (pieces, rows per district, an AUTHORED near rule)',
  IK && Array.isArray(IK.pieces) && IK.pieces.length > 0 && IK.byDistrict && IK.nearM > 0 && IK.eyeMaxM > 0);
const districts = new Set(D.halls.map((h) => h.district));
const STRANDS = Object.keys(D.props.by_strand);
const missing = [];
for (const d of districts) for (const s of STRANDS) if (!IK.byDistrict[d] || !Array.isArray(IK.byDistrict[d][s])) missing.push(d + '/' + s);
ok(`every hall district (${districts.size}) has a row for every strand (${STRANDS.length})`, missing.length === 0);

const mat = {};
for (const [k, c] of Object.entries({ cone: 0xE07C48, metal: 0x8f9a9d, paint: 0xd8dcd8, part: 0x2c3639, post: 0xE8A33D,
  steel: 0x41C4D4, wood: 0x8a6a42 })) mat[k] = new THREE.MeshStandardMaterial({ color: c });
const env = { THREE, mergeGeometries, D, mat, eyePos: () => new THREE.Vector3(30, 26, 42), window: {} };
const factory = new Function(...Object.keys(env), `"use strict"; let view = 'hall';
  const PROP_BY_ID = new Map(D.interiorKit.pieces.map((p) => [p.id, p])); let propStat = { wanted: 0, skipped: [] };
  const propGeoCache = new Map(); let hallSolids = [];
  ${['propMat', 'propPartAt', 'propGeo', 'wallRect'].map(lift).join('\n')}
  ${block('INTERIOR-KIT')}
  return { ikReset, ikPieces, ikStand, ikEnd, ikFlush, ikNear, ikCull, ikStep, ikIslands, IK, wallRect,
           solids: () => hallSolids, clearSolids: () => { hallSolids = []; }, rooms: () => ikRooms,
           setPropStat: (s) => { propStat = s; }, getPropStat: () => propStat,
           mesh: () => ikMesh, stat: () => ikStat, hook: window.__tc3dInterior, cacheClear: () => propGeoCache.clear() };`);
const P = factory(...Object.values(env));
const BY_ID = new Map(IK.pieces.map((p) => [p.id, p]));

// every piece builds at its registry triangles (propGeo throws otherwise)
const geoBad = [];
for (const p of IK.pieces) { try { P.ikReset('x'); P.ikPieces({ district: [...districts][0] }, { strand: STRANDS[0] }, 0, 0, 9, 6); P.ikStand(p, new THREE.Matrix4()); } catch (e) { geoBad.push(p.id + ': ' + e.message); } }
ok(`all ${IK.pieces.length} district pieces build from their recipes at the registry's triangles`, geoBad.length === 0);

// a synthetic hall per district: its eleven rooms in a row, 10 m apart, every offered piece stood in its room
const ROOMW = 9, ROOMD = 6, PITCH = 10;
const results = [];
for (const d of districts) {
  const h = { district: d };
  P.ikReset('hall-' + d);
  let want = 0;
  STRANDS.forEach((s, i) => {
    const ids = P.ikPieces(h, { strand: s }, i * PITCH, 0, ROOMW, ROOMD);
    ids.forEach((id, j) => { const pose = new THREE.Matrix4().setPosition(i * PITCH - 3 + j * .5, 0, 0); P.ikStand(BY_ID.get(id), pose); want += BY_ID.get(id).tris; });
  });
  const g = new THREE.Group();
  const m = P.ikFlush(g);
  const st = P.stat();
  results.push({ d, g, m, st, want });
}
ok('each district hall draws ONE mesh with ONE material for all its district pieces',
  results.every((r) => r.m && r.g.children.length === 1 && r.g.children[0] === r.m && !Array.isArray(r.m.material) && r.m.material.vertexColors));
ok('the mesh carries exactly the triangles of the pieces stood (per district)',
  results.every((r) => r.m.geometry.index.count / 3 === r.want && r.st.tris === r.want));
ok('per-room index ranges tile the whole index, in room order, with no gap or overlap', results.every((r) => {
  const u = r.m.userData.interiorKit; let at = 0;
  for (const rg of u.ranges) { if (!rg) continue; if (rg[0] !== at) return false; at += rg[1]; }
  return at === r.m.geometry.index.count && u.rooms.length === STRANDS.length;
}));
ok('the mesh is priced at build (visible, full range) - one drawable a hall budget counts', results.every((r) => r.m.visible));

// the cull
const far = results.map((r) => { P.ikCull(r.m, new THREE.Vector3(30, 26, 42)); return r.m.visible || r.m.geometry.drawRange.count !== 0; });
ok('from the hall orbit camera (30, 26, 42) no district piece is drawn in any district hall', far.every((x) => !x));
const R0 = results.find((r) => r.m.userData.interiorKit.ranges.filter(Boolean).length >= 3);
ok('a district hall dresses at least three of its rooms', !!R0);
{
  const u = R0.m.userData.interiorKit;
  const k = u.ranges.findIndex(Boolean);
  const eye = new THREE.Vector3(k * PITCH, 1.7, 0);
  P.ikCull(R0.m, eye);
  const near = u.rooms.map((rm, i) => rm.n && Math.hypot(Math.max(rm.x0 - eye.x, 0, eye.x - rm.x1), Math.max(rm.z0 - eye.z, 0, eye.z - rm.z1)) <= IK.nearM);
  let expect = 0; u.ranges.forEach((rg, i) => { if (rg && near[i]) expect += rg[1]; });
  ok(`standing in a room draws exactly the rooms within ${IK.nearM} m (${expect / 3} triangles of ${u.full.length / 3})`,
    R0.m.visible && R0.m.geometry.drawRange.count === expect && expect > 0 && expect < u.full.length);
  let same = true, at = 0;
  u.ranges.forEach((rg, i) => { if (rg && near[i]) { for (let j = 0; j < rg[1]; j++) if (R0.m.geometry.index.array[at + j] !== u.full[rg[0] + j]) same = false; at += rg[1]; } });
  ok('the drawn index is those rooms\' own slices of the full index', same);
  ok('a second frame at the same place rewrites nothing', P.ikCull(R0.m, eye) === false);
  P.ikCull(R0.m, new THREE.Vector3(k * PITCH, IK.eyeMaxM + 1, 0));
  ok(`an eye above ${IK.eyeMaxM} m draws none of it, even over a dressed room`, !R0.m.visible && R0.m.geometry.drawRange.count === 0);
}
// the island rule, on a room whose walls are already full: partitions as solids, a doorway in the front
// wall and one in the left wall near the back, a fixture bench at the back, and the longest district row that
// also carries a wall-mounted piece offered - its first floor piece already stood by the wall loop
{
  P.clearSolids();
  const rx = 0, rz = 0, rw = 12, rd = 9, inset = .3, x0 = -6, x1 = 6, zF = -4.5, zB = 4.5;
  P.wallRect(x1, 0, .06, rd / 2); P.wallRect(0, zB, rw / 2, .06);
  P.wallRect(x0, -1.5, .06, 3); P.wallRect(x0, 4, .06, .5);              // the left wall, a doorway at z 1.5..3.5
  // the front is one open doorway its whole width, as a room open to the hall aisle is
  P.wallRect(2, zB - 1, .7, .4);                                          // a fixture bench
  const doors = new Map([['z@' + zF.toFixed(2), [[x0, x1]]], ['x@' + x0.toFixed(2), [[1.5, 3.5]]]]);
  let best = null;
  for (const [d, row] of Object.entries(IK.byDistrict)) for (const [s2, ids] of Object.entries(row))
    if (ids.some((id) => BY_ID.get(id).layout.anchor === 'wall-mounted') && (!best || ids.length > best.ids.length)) best = { d, s: s2, ids };
  const first = best.ids.find((id) => BY_ID.get(id).layout.anchor !== 'wall-mounted');
  const before = P.solids()[0].rects.length;
  P.ikReset('island');
  P.ikPieces({ district: best.d }, { strand: best.s }, rx, rz, rw, rd);
  P.ikStand(BY_ID.get(first), new THREE.Matrix4().setPosition(5, 0, 3));   // as if the wall loop stood it
  const stood = P.ikIslands({ district: best.d }, rx, rz, rw, rd, doors, inset, best.ids);
  const rects = P.solids()[0].rects, isl = rects.slice(before);
  ok(`islands stand on an open floor (${stood} of ${best.ids.length} offered by ${best.d}/${best.s}), each registered solid`,
    stood > 0 && isl.length === stood && P.stat().islands === stood);
  const A = IK.aisleM, gapOk = isl.every((a, i) => rects.every((b) => b === a
    || Math.abs(a.u - b.u) >= a.hw + b.hw + A - 1e-9 || Math.abs(a.v - b.v) >= a.hd + b.hd + A - 1e-9));
  ok(`every island keeps a ${A} m aisle to every other solid, earlier islands included`, gapOk);
  ok(`no island stands in the room's middle row (${IK.midM} m) where stations and the advisor stand`,
    isl.every((a) => Math.abs(a.v - rz) >= a.hd + IK.midM - 1e-9));
  ok(`no island stands within ${IK.doorM} m in front of a doorway (an open front and a side wall)`,
    isl.every((a) => !(a.v - a.hd < zF + IK.doorM))
    && isl.every((a) => !(a.u - a.hw < x0 + IK.doorM && a.v - a.hd < 3.5 && a.v + a.hd > 1.5)));
  ok('no wall-mounted piece is stood as an island',
    [...P.rooms().at(-1).ids].every((id) => BY_ID.get(id).layout.anchor !== 'wall-mounted'));
  ok('a piece the wall loop already stood is not stood again as an island', P.stat().byPiece[first] === 1);
}
// the props pack's tallies are handed back
P.setPropStat({ wanted: 10, skipped: [{ prop: 'a' }] });
P.getPropStat().wanted += 4; P.getPropStat().skipped.push({ prop: 'district-piece' });
P.ikReset('t'); P.ikEnd(true, 10, 1);
ok('the district pieces\' wanted/skipped move to the kit and the props pack keeps its own figures',
  P.getPropStat().wanted === 10 && P.getPropStat().skipped.length === 1 && P.stat().wanted === 4 && P.stat().skipped[0].prop === 'district-piece');
// the page wiring, at the source: the hooks sit where the placement loop and the frame loop run
const pr = lift('placeRoomProps');
ok('placeRoomProps offers the district pieces after the strand furniture and routes them to the kit',
  /want\.push\(\.\.\.ids\);[\s\S]{0,200}want\.push\(\.\.\.ikPieces\(h, r, rx, rz, rw, rd\)\)/.test(pr)
  && /if \(ikInto\) \{ ikInto\(p, pose\); return; \}/.test(pr) && /ikEnd\(ikFrom < want\.length, ikW0, ikS0\)/.test(pr));
ok('buildHall flushes the kit after the props and the frame loop culls it', /flushProps\(hallGroup\);\s*\/\* INTERIOR-KIT BEGIN \(wave 17\) \*\/ ikFlush\(hallGroup\);/.test(mod)
  && /advisorProximity\(dt\);\s*\/\* INTERIOR-KIT BEGIN \(wave 17\) \*\/ ikStep\(\);/.test(mod));

/* ------------------------------------------------------------ exteriors -- */
const EK = D.exteriorKit;
ok('the payload carries the exterior kit (deck rules, glazing rows, an AUTHORED near rule)',
  EK && EK.decks && EK.glaze && EK.nearM > 0 && EK.eyeMaxM > 0);
// the glazing rows restate hallkit's campus-scale glazing: held to the page's own hallkit source
const hk = mod.slice(mod.indexOf('function hkShell('));
const gzSrc = { band: /a\.glaze === 'band'\) gz\(H \* ([.\d]+), Math\.max\(([.\d]+), H \* ([.\d]+)\)\)/,
  ribbon: /a\.glaze === 'ribbon'\) \{ gz\(H \* ([.\d]+), Math\.max\(([.\d]+), H \* ([.\d]+)\)\)/,
  clerestory: /a\.glaze === 'clerestory'\) gz\(H \* ([.\d]+), Math\.max\(([.\d]+), H \* ([.\d]+)\)\)/,
  punched: /\} else gz\(H \* ([.\d]+), ([.\d]+)\);/ };
const gzBad = Object.entries(gzSrc).filter(([k, re]) => {
  const m = hk.match(re), g = EK.glaze[k];
  if (!m || !g) return true;
  return k === 'punched' ? (+m[1] !== g.y || +m[2] !== g.min || g.h !== 0) : (+m[1] !== g.y || +m[2] !== g.min || +m[3] !== g.h);
}).map(([k]) => k);
ok('the exterior kit\'s glazing rows are hallkit\'s own campus-scale glazing (y, height, floor) for all four types', gzBad.length === 0);

const solidLogB = [];
const envB = { THREE, mergeGeometries, D, eyePos: () => new THREE.Vector3(0, 300, 350), window: {},
  mat: { metal: new THREE.MeshStandardMaterial(), block: new THREE.MeshStandardMaterial({ color: 0x9aa0a2 }),
         wood: new THREE.MeshStandardMaterial({ color: 0x8a6a42 }), veg: new THREE.MeshStandardMaterial({ color: 0x4c6b3a }) },
  ikMat: new THREE.MeshStandardMaterial({ vertexColors: true }), campusSolid: (x, z, r) => solidLogB.push({ u: x, v: z, r }) };
const hasScene = mod.includes('/* SCENE-KIT BEGIN (wave 17) */\n');
const factoryB = new Function(...Object.keys(envB), `"use strict"; let view = 'campus'; const solids = [];
  ${block('EXTERIOR-KIT')}
  ${hasScene ? block('SCENE-KIT') : ''}
  return { ekDressCampus, ekRoofSpots, ekTrimOf, ekNear, ekCull, ekStep, trim: () => ekTrim, hook: window.__tc3dExterior, setView: (v) => { view = v; },
           ${hasScene ? 'skDressCampus, skTreeSpots, skStreetOf, skStat: () => skStat,' : ''} };`);
const B = factoryB(...Object.values(envB));
const hallBy = new Map(D.halls.map((h) => [h.slug, h]));
const camps = [];
for (const [key, camp] of Object.entries(D.campuses)) {
  const plan = camp.districts.length ? D.campusplan[key] : null;
  const g = new THREE.Group(), cg = new THREE.Group(); g.add(cg);
  const boards = [];
  if (plan) for (const lot of plan.lots) {
    const Bt = lot.b, bg = new THREE.Group();
    bg.position.set(Bt.x, 0, Bt.z); bg.rotation.y = Bt.rot_y; cg.add(bg);
    boards.push({ h: hallBy.get(lot.hall), bg, w: Bt.w_m, d: Bt.d_m, hgt: Bt.height_m + .35, B: Bt });
  }
  solidLogB.length = 0;
  const st = B.ekDressCampus(g, boards);
  camps.push({ key, g, boards, st, trim: B.trim(), solids: solidLogB.slice() });
}
const withHalls = camps.filter((c) => c.boards.length);
ok(`every campus with halls (${withHalls.length}) dresses; each family is ONE InstancedMesh on the shared metal, at most 3 per campus`,
  withHalls.length > 0 && withHalls.every((c) => {
    const ims = c.g.children.filter((o) => o.isInstancedMesh);
    return ims.length === c.st.calls && c.st.calls <= 3 && ims.every((o) => o.material === envB.mat.metal)
      && new Set(ims.map((o) => o.name)).size === ims.length;
  }));
const decked = (h) => h.arch.roof in EK.decks;
ok('roof plant stands on exactly the halls whose archetype has a deck (parapet, monitor, high bay), one unit and one vent each',
  withHalls.every((c) => c.st.roofPlant === c.boards.filter((b) => decked(b.h)).length && c.st.vents === c.st.roofPlant
    && c.st.noDeck === c.boards.length - c.st.roofPlant));
// every rooftop unit on its own deck, inside its own roof, clear of the archetype's monitor or high bay
const spotBad = [];
for (const c of withHalls) for (const b of c.boards) {
  const sp = B.ekRoofSpots(b.h.arch, b.w, b.d, b.hgt);
  if (!sp) continue;
  const W = b.w, Dp = b.d, a = b.h.arch;
  for (const [nm, [x, y, z], hw, hd] of [['hvac', sp.hvac, EK.hvac.w / 2, EK.hvac.d / 2], ['vent', sp.vent, EK.vent.capW / 2, EK.vent.capW / 2]]) {
    if (Math.abs(x) + hw > W / 2 || Math.abs(z) + hd > Dp / 2) spotBad.push(b.h.slug + ' ' + nm + ' off the roof');
    if (y < b.hgt || y > b.hgt + .3) spotBad.push(b.h.slug + ' ' + nm + ' off the deck');
    if (a.roof === 'monitor' && Math.abs(x) - hw < W * .15 + .4) spotBad.push(b.h.slug + ' ' + nm + ' in the monitor');
    if (a.roof === 'highbay' && x - hw < -W * .18 + W * .25 + .3 && x + hw > -W * .18 - W * .25) spotBad.push(b.h.slug + ' ' + nm + ' in the high bay');
    // hallkit's own plant stands at x = W*.3 (W*.28 on a high bay), z = D*.15 / D*.2 / 0 / -D*.2
    if (Math.abs(x - (a.roof === 'highbay' ? W * .28 : W * .3)) < hw + 2 && [.15, .2, 0].some((f) => Math.abs(z - Dp * f) < hd + 1.3))
      spotBad.push(b.h.slug + ' ' + nm + ' in the archetype\'s own plant');
    if (a.plant === 'solar' && x - hw < W * .05 && x + hw > -W * .35 && [-.3, .3].some((f) => Math.abs(z - Dp * f) < hd + 1.1))
      spotBad.push(b.h.slug + ' ' + nm + ' in the solar rows');
  }
}
ok('every rooftop unit and vent sits on its own deck, inside its roof, clear of the monitor, the high bay and the archetype\'s own plant',
  spotBad.length === 0);
// the hood over the roll-up door and the mullions across the back glazing, in the building's frame
const trimBad = [];
for (const c of withHalls) for (const b of c.boards) {
  const a = b.h.arch, W = b.w, Dp = b.d, H = b.hgt, s = W / 36;
  const t = B.ekTrimOf(a, W, Dp, H);
  const dw = Math.min(a.door.w * s, W * .3), dh = Math.min(a.door.h * s, H * .8);
  const hood = t[0];
  if (Math.abs(hood[3] - W * .28) > 1e-9 || hood[0] < dw || hood[4] <= dh || hood[5] >= -Dp / 2 - .42) trimBad.push(b.h.slug + ' hood');
  const g2 = EK.glaze[a.glaze], gy = H * g2.y, gh = Math.max(g2.min, H * g2.h), gw = W * .8;
  for (const m of t.slice(3, -2)) if (Math.abs(m[3]) >= gw / 2 || Math.abs(m[4] - gy) > 1e-9 || Math.abs(m[1] - gh) > 1e-9 || m[5] <= Dp / 2 + .132) trimBad.push(b.h.slug + ' mullion');
}
ok('each hall\'s door hood is wider than and above its roll-up door, in front of the wall; its mullions span its own glazing, outside the glass',
  trimBad.length === 0);
ok('the triangles each campus reports are its instances times the shapes\' own triangles (roof and trim)',
  withHalls.every((c) => {
    const ims = c.g.children.filter((o) => o.isInstancedMesh);
    const roof = ims.filter((o) => o.name !== 'ek-trim').reduce((a, o) => a + o.geometry.index.count / 3 * o.count, 0);
    const tr = ims.find((o) => o.name === 'ek-trim');
    return roof === c.st.roofTris && tr && tr.geometry.index.count / 3 * c.st.trimInstances === c.st.trimTris;
  }));
// the near cull on the flagship
const F = withHalls.reduce((a, c) => (c.boards.length > a.boards.length ? c : a));
B.ekCull(F.trim, new THREE.Vector3(0, 300, 350));
ok(`from a campus orbit camera no street detail is drawn on ${F.key} (${F.st.trimInstances} trim instances, 0 drawn)`,
  !F.trim.visible && F.trim.count === 0);
const b0 = F.boards[0];
b0.bg.updateWorldMatrix(true, false);
const door = new THREE.Vector3(0, 1.7, -b0.d / 2 - 4).applyMatrix4(b0.bg.matrixWorld);
B.ekCull(F.trim, door);
{
  const u = F.trim.userData.exteriorKit;
  const near = u.spots.map((p) => Math.hypot(p.x - door.x, p.z - door.z) <= EK.nearM);
  let expect = 0; u.ranges.forEach(([s0, c0], i) => { if (near[i]) expect += c0; });
  ok(`standing at a hall's door draws the trim of exactly the buildings within ${EK.nearM} m (${expect} of ${u.full.length / 16} instances)`,
    F.trim.visible && F.trim.count === expect && expect > 0 && expect < u.full.length / 16);
  let same = true, at = 0;
  u.ranges.forEach(([s0, c0], i) => { if (near[i]) { for (let j = 0; j < c0 * 16; j++) if (F.trim.instanceMatrix.array[at * 16 + j] !== u.full[s0 * 16 + j]) same = false; at += c0; } });
  ok('the drawn instances are those buildings\' own matrices, in order', same);
  ok('a second frame at the same place rewrites nothing', B.ekCull(F.trim, door) === false);
  B.ekCull(F.trim, door.clone().setY(EK.eyeMaxM + 1));
  ok(`an eye above ${EK.eyeMaxM} m draws no street detail`, !F.trim.visible && F.trim.count === 0);
}
ok('buildCampus dresses the outside after the campus dressing, and the frame loop culls it',
  /bdDressCampus\(campusGroup, rr\);[^\n]*\n\s*\/\* EXTERIOR-KIT BEGIN \(wave 17\) \*\/ ekDressCampus\(campusGroup, bdCamp\.boards\);/.test(mod)
  && /ikStep\(\);[^\n]*\n\s*\/\* EXTERIOR-KIT BEGIN \(wave 17\) \*\/ ekStep\(\);/.test(mod));
console.log('  exterior kit: ' + withHalls.map((c) => `${c.key} ${c.st.roofPlant}u/${c.st.vents}v ${c.st.roofTris}tri ${c.st.roofCalls}dc + trim ${c.st.trimInstances}i`).join('; '));

/* --------------------------------------------------------- campus scene -- */
const SK = D.sceneKit;
ok('the payload carries the scene kit (plaza ring, tree, rack and pole dimensions)', SK && SK.ringR > 0 && SK.tree && SK.rack && SK.pole);
const scene = [];
for (const [key, camp] of Object.entries(D.campuses)) {
  const plan = camp.districts.length ? D.campusplan[key] : null;
  const roads = [], rects = [], g = new THREE.Group(); let lit = [];
  if (plan) {
    for (const lot of plan.lots) rects.push({ u: lot.b.aabb.x, v: lot.b.aabb.z, hw: lot.b.aabb.w / 2 + .2, hd: lot.b.aabb.d / 2 + .2 });
    for (const r of [...plan.streets, ...plan.walkways, ...plan.parking]) roads.push({ u: r.x, v: r.z, w: r.w, h: r.d });
    lit = roads.slice(0, plan.streets.length + plan.walkways.length);
  }
  solidLogB.length = 0;
  const st = B.skDressCampus(g, roads, rects, lit);
  scene.push({ key, g, st, roads, rects, solids: solidLogB.slice(), trees: g.children.find((o) => o.name === 'sk-trees') });
}
ok(`every campus (${scene.length}) stands its plaza trees as ONE InstancedMesh on the shared vertex-colour material`,
  scene.every((c) => c.st.trees > 0 && c.trees && c.trees.isInstancedMesh && c.trees.count === c.st.trees
    && c.trees.material === envB.ikMat && c.g.children.filter((o) => o.isMesh).length === 1));
const treeBad = [];
for (const c of scene) {
  const M = new THREE.Matrix4(), P = new THREE.Vector3(); let street = 0;
  for (let i = 0; i < c.trees.count; i++) {
    c.trees.getMatrixAt(i, M); P.setFromMatrixPosition(M);
    if (c.roads.some((r) => Math.abs(P.x - r.u) < r.w / 2 + SK.clearM - 1e-6 && Math.abs(P.z - r.v) < r.h / 2 + SK.clearM - 1e-6)) treeBad.push(c.key + ' road');
    if (c.rects.some((b) => Math.abs(P.x - b.u) < b.hw + SK.clearM - 1e-6 && Math.abs(P.z - b.v) < b.hd + SK.clearM - 1e-6)) treeBad.push(c.key + ' lot');
    if (Math.abs(Math.hypot(P.x, P.z) - SK.ringR) > 1e-6) street++;
  }
  c.street = street;
}
ok('no tree stands on a road, walk or parking lot, or on a hall lot', treeBad.length === 0);
ok(`street rows stand at most ${SK.streetMax} trees a campus, and only where the plan lays lit streets or walks`,
  scene.every((c) => c.street <= SK.streetMax && (c.roads.length ? true : c.street === 0)) && scene.some((c) => c.street > 0));
ok('every tree is solid through the grounds\' campusSolid(), one disc per tree', scene.every((c) => c.solids.length === c.st.trees));
{
  // a lamp ON the first ring spot, a solid disc ON the seventh, a walk over the thirteenth and a hall lot over the
  // nineteenth: those four spots must go, and only they
  const n = Math.round(360 / SK.ringStepDeg), at = (i) => { const th = (i + .5) / n * Math.PI * 2; return [Math.cos(th) * SK.ringR, Math.sin(th) * SK.ringR]; };
  const [lx, lz] = at(0), [dx, dz] = at(6);
  const [rx2, rz2] = at(12), [ox, oz] = at(18);
  const sp = B.skTreeSpots([{ u: rx2, v: rz2, w: 3, h: 3 }], [{ u: ox, v: oz, hw: 4, hd: 4 }], [[lx, lz]], [{ u: dx, v: dz, r: .6 }]);
  ok(`a ring spot within ${SK.lampClearM} m of a lamp, on a solid disc, on a walk or on a hall lot is not taken - and only those`,
    sp.every(([x, z]) => Math.hypot(x - lx, z - lz) >= SK.lampClearM && Math.hypot(x - dx, z - dz) >= .6 + SK.clearM + SK.tree.planterW / 2
      && Math.hypot(x - rx2, z - rz2) > 1 && Math.hypot(x - ox, z - oz) > 1) && sp.length === n - 4);
}
ok('the tree triangles each campus reports are its trees times the tree\'s own triangles',
  scene.every((c) => c.st.treeTris === c.trees.count * c.trees.geometry.attributes.position.count / 3));
// street furniture rides in the building kit's trim, one run per building
{
  const a0 = withHalls[0].boards[0];
  const ex = B.ekTrimOf(a0.h.arch, a0.w, a0.d, a0.hgt).length, sk = B.skStreetOf(a0.h.arch, a0.w, a0.d, a0.hgt);
  ok(`each building's near-culled run carries its street furniture (${sk.length} rack and pole bars) and no new draw call`,
    withHalls.every((c) => c.st.trimInstances === c.boards.length * (ex + sk.length) && c.st.calls <= 3));
  const W = a0.w, Dp = a0.d, s = W / 36, dw = Math.min(a0.h.arch.door.w * s, W * .3);
  ok('the bike rack stands off the roll-up door\'s side, in front of the wall; the pole stands clear of the door line',
    sk.slice(0, -3).every((m) => m[5] < -Dp / 2 - .42 && Math.abs(m[3] - W * .28) > dw / 2 + 1)
    && sk.slice(-3).every((m) => m[5] < -Dp / 2 - 1 && Math.abs(m[3]) > 1.2));
  // and on the flagship, no pole stands on a street
  const poleBad = [];
  for (const b of F.boards) {
    const p = B.skStreetOf(b.h.arch, b.w, b.d, b.hgt).at(-3);
    const w = new THREE.Vector3(p[3], 0, p[5]).applyMatrix4(b.bg.matrixWorld);
    if (D.campusplan[F.key].streets.some((r) => Math.abs(w.x - r.x) < r.w / 2 && Math.abs(w.z - r.z) < r.d / 2)) poleBad.push(b.h.slug);
  }
  ok(`no wayfinding pole stands on a street of ${F.key}`, poleBad.length === 0);
  // the rack's hoops and the pole are SOLID: one campusSolid() disc each, where the lot puts them, at least their own half-width
  const per = SK.rack.hoops + 1, solBad = [];
  for (const c of withHalls) {
    if (c.solids.length !== c.boards.length * per || c.st.streetSolids !== c.solids.length) { solBad.push(c.key + ' count'); continue; }
    c.boards.forEach((b, i) => {
      b.bg.updateWorldMatrix(true, false);
      const bars = B.skStreetOf(b.h.arch, b.w, b.d, b.hgt), mine = c.solids.slice(i * per, (i + 1) * per);
      for (let k = 0; k < SK.rack.hoops; k++) {
        const top = bars[k * 3 + 2], w = new THREE.Vector3(top[3], 0, top[5]).applyMatrix4(b.bg.matrixWorld);
        if (Math.hypot(w.x - mine[k].u, w.z - mine[k].v) > 1e-6 || mine[k].r < SK.rack.w / 2) solBad.push(b.h.slug + ' hoop');
      }
      const pole = bars.at(-3), pw = new THREE.Vector3(pole[3], 0, pole[5]).applyMatrix4(b.bg.matrixWorld), pd = mine[per - 1];
      if (Math.hypot(pw.x - pd.u, pw.z - pd.v) > 1e-6 || pd.r < .05) solBad.push(b.h.slug + ' pole');
    });
  }
  ok(`every bike-rack hoop and wayfinding pole is solid to the walker: one campusSolid() disc each at its place on the lot (${withHalls.reduce((n, c) => n + c.solids.length, 0)} discs)`,
    solBad.length === 0);
}
ok('buildCampus stands the scene kit after the building kit', /ekDressCampus\(campusGroup, bdCamp\.boards\);[^\n]*\n\s*\/\* SCENE-KIT BEGIN \(wave 17\) \*\/ skDressCampus\(campusGroup, bdCamp\.roads, bdCamp\.rects, bdCamp\.lit\);/.test(mod));
console.log('  scene kit: ' + scene.map((c) => `${c.key} ${c.st.trees} trees (${c.street} street) ${c.st.treeTris}tri`).join('; '));

console.log(`  interior kit: ${IK.pieces.length} pieces, ${districts.size} districts; per district hall tris `
  + results.map((r) => `${r.d} ${r.want}`).join(', '));
console.log(`web/test_scenes: ${n} checks passed - the wave-17 interior fit-out, building kit and campus scene run and cull as declared`);
