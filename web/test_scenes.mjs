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

console.log(`  interior kit: ${IK.pieces.length} pieces, ${districts.size} districts; per district hall tris `
  + results.map((r) => `${r.d} ${r.want}`).join(', '));
console.log(`web/test_scenes: ${n} checks passed - the wave-17 interior fit-out runs and culls as declared`);
