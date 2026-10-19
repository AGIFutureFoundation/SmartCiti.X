/**
 * Checks for the fabric view cull of the parish and Bay worlds (web/build_parishes.py, block RENDER-CULL; the page
 * carries the neutral marker FABRIC-CULL). The fabric InstancedMeshes (houses, midrise, trees, lamps) draw only the
 * instances whose bounding sphere touches the camera frustum; the BUILT instances stay in a snapshot that the page's
 * stats, the eval's fabric floor and the elevation audit read. The block's own JS is cut out of the BUILT page and run
 * here against the real three.js: nothing is mirrored. Prints `  ok ` per check and `FAIL` at column 0; exit code 1 on failure.
 * Browser rows (frame time, draw calls, triangles) stay with web/eval_parishes.mjs and web/eval_bayworld.mjs.
 */
import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const THREE = await import(pathToFileURL(join(HERE, 'vendor/three.module.min.js')).href);
let fails = 0, oks = 0;
const check = (name, cond, why = '') => { if (cond) { oks++; console.log(`  ok ${name}`); } else { fails++; console.log(`FAIL ${name}${why ? ' :: ' + why : ''}`); } };
const mainOf = (f) => (readFileSync(join(HERE, f), 'utf8').match(/<script type="module" id="parishes-main">([\s\S]*?)<\/script>/) || [, ''])[1];
const main = mainOf('trade_craft_parishes.html'), bay = mainOf('trade_craft_bay.html');
const BLOCK = /\/\* FABRIC-CULL BEGIN[\s\S]*?\/\* FABRIC-CULL END \*\//;
const blk = (main.match(BLOCK) || [''])[0];

// [wiring] one block, hooked once where the built set is complete and once per frame after the camera is placed
check('[cull] one FABRIC-CULL block in the parish page and in the Bay page, neutral marker only (no team codename)',
  (main.match(/FABRIC-CULL BEGIN/g) || []).length === 1 && (bay.match(/FABRIC-CULL BEGIN/g) || []).length === 1 && !/RENDER-CULL|RENDER·|Frame Cost/.test(main + bay));
check('[cull] the built set is snapshotted once, at the end of refillFabric, and culled once, at the top of perfCull (after placeCamera)',
  (main.match(/fabSnapshot\(\);/g) || []).length === 1 && /dirty = false; markPhys\(\); fabSnapshot\(\);/.test(main)
  && (main.match(/fabCull\(over\);/g) || []).length === 1 && /function perfCull\(over\) \{\n  camera\.updateMatrixWorld\(\); camera\.matrixWorldInverse\.copy\(camera\.matrixWorld\)\.invert\(\); fabCull\(over\);/.test(main));
check('[cull] the eval\'s counts are the BUILT instances: stats instances, kit, kitUse and the elevation audit read the snapshot, never the culled mesh count',
  main.includes('block: blocks.visible ? fabBuilt(houses) + fabBuilt(blocks) : 0, tree: trees.visible ? fabBuilt(trees) : 0, lamp: lamps.visible ? fabBuilt(lamps) : 0')
  && main.includes('[k, m.visible ? fabBuilt(m) : 0]') && main.includes('i < fabBuilt(m); i++) c[Math.floor(a[i] + 0.01)]++')
  && main.includes('i < fabBuilt(m) && drawn.length < n; i++) { const f = fabFam(m);') && main.includes('drawn: { ...FAB.drawn }'));
check('[cull] no ceiling, target or eval threshold is in the block (a cull that only removes what cannot be seen)',
  !/MS_HEADROOM|CALL_HEADROOM|TRI_HEADROOM|FABRIC_FLOOR|BASE\[/.test(blk) && blk.includes('DIAG.noCull') && /< -r\)/.test(blk));

// [behaviour] the real block on the real three.js (without the block there is nothing to run)
if (!blk) { console.log(`test_rendercull: ${fails} FAIL, ${oks} ok (no FABRIC-CULL block in the parish page)`); process.exit(1); }
const N = 900;
function rig() {
  const cam = new THREE.PerspectiveCamera(62, 1.6, 0.3, 60000);
  const DIAG = {};
  const mk = (name, kit) => {
    const g = new THREE.BoxGeometry(1, 1, 1).translate(0, 0.5, 0);
    if (kit) g.setAttribute('kitUse', new THREE.InstancedBufferAttribute(new Float32Array(N), 1));
    const m = new THREE.InstancedMesh(g, new THREE.MeshBasicMaterial(), N); m.setColorAt(0, new THREE.Color(1, 1, 1)); return m;
  };
  const houses = mk('h', true), blocks = mk('b', true), trees = mk('t', false), lamps = mk('l', false);
  // a lot grid 1.6 km square around the origin; per-instance colour carries the index (red = i / N), kitUse = i % 3
  const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), V = new THREE.Vector3(), S = new THREE.Vector3(), C = new THREE.Color();
  for (const [fi, m] of [houses, blocks, trees, lamps].entries()) {
    m.count = N;
    for (let i = 0; i < N; i++) {
      const gx = (i % 30) - 15, gz = Math.floor(i / 30) - 15, s = 6 + ((i * 7 + fi * 3) % 9);
      M.compose(V.set(gx * 55 + fi * 5, 0, gz * 55 + fi * 3), Q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), i * 0.3), S.set(s, 4 + (i % 11) * 3, s)); m.setMatrixAt(i, M);
      m.setColorAt(i, C.setRGB(i / N, fi / 4, 0.5));
      if (m.geometry.attributes.kitUse) m.geometry.attributes.kitUse.array[i] = i % 3;
    }
  }
  const api = new Function('THREE', 'houses', 'blocks', 'trees', 'lamps', 'camera', 'DIAG', blk + '\nreturn { FAB, fabSnapshot, fabCull, fabBuilt, fabFam };')(THREE, houses, blocks, trees, lamps, cam, DIAG);
  const look = (x, y, z, yaw, pitch = 0) => { cam.position.set(x, y, z); cam.rotation.set(pitch, yaw, 0, 'YXZ'); cam.updateMatrixWorld(); cam.matrixWorldInverse.copy(cam.matrixWorld).invert(); };
  return { cam, DIAG, houses, blocks, trees, lamps, api, look };
}
const idxOf = (m, j) => Math.round(m.instanceColor.array[j * 3] * N);   // the red channel is the built index (Float32: exact to 1e-7)
{
  const R = rig(); R.api.fabSnapshot(); R.look(0, 1.7, 0, 0.4);
  const before = [R.houses, R.blocks, R.trees, R.lamps].map((m) => m.count);
  R.api.fabCull(false);
  const after = [R.houses, R.blocks, R.trees, R.lamps].map((m) => m.count);
  check('[cull] the BUILT counts are unchanged by a cull, the drawn counts fall (looking across a lot grid: well under half is drawn)',
    before.every((c) => c === N) && [R.houses, R.blocks, R.trees, R.lamps].every((m) => R.api.fabBuilt(m) === N) && after.every((c) => c > 0 && c < N * 0.5), JSON.stringify(after));
  // soundness: every instance whose true bounding sphere touches the true frustum is drawn (never a pop)
  const fr = new THREE.Frustum().setFromProjectionMatrix(new THREE.Matrix4().multiplyMatrices(R.cam.projectionMatrix, R.cam.matrixWorldInverse));
  let miss = 0, inside = 0, total = 0;
  for (const [fi, m] of [R.houses, R.blocks, R.trees, R.lamps].entries()) {
    const drawn = new Set(); for (let j = 0; j < m.count; j++) drawn.add(idxOf(m, j));
    const g = m.geometry; g.computeBoundingSphere();
    for (let i = 0; i < N; i++) {
      const M = new THREE.Matrix4(); const orig = R.api.fabFam(m); M.fromArray(orig.mat, i * 16);
      const sp = new THREE.Sphere().copy(g.boundingSphere).applyMatrix4(M); total++;
      if (fr.intersectsSphere(sp)) { inside++; if (!drawn.has(i)) miss++; }
    }
  }
  check('[cull] soundness: no instance whose bounding sphere touches the frustum is ever culled', inside > 100 && miss === 0, `${miss} missing of ${inside} inside (${total} total)`);
  // pairing: a drawn slot j carries ITS instance's matrix, colour and kitUse
  let bad = 0;
  for (const m of [R.houses, R.blocks, R.trees, R.lamps]) {
    const f = R.api.fabFam(m), ku = m.geometry.attributes.kitUse;
    for (let j = 0; j < m.count; j++) {
      const i = idxOf(m, j);
      for (let k = 0; k < 16; k++) if (m.instanceMatrix.array[j * 16 + k] !== f.mat[i * 16 + k]) { bad++; break; }
      if (m.instanceColor.array[j * 3 + 1] !== f.col[i * 3 + 1] || (ku && ku.array[j] !== i % 3)) bad++;
    }
  }
  check('[cull] a drawn slot carries its own instance: matrix, colour and the per-instance kitUse attribute travel together', bad === 0, `${bad} mismatched`);
  check('[cull] the block records what it did: drawn per family, cull count and cost', R.api.FAB.culls === 1 && R.api.FAB.drawn.house === after[0] && R.api.FAB.drawn.lamp === after[3] && R.api.FAB.ms >= 0);
}
{
  const R = rig(); R.api.fabSnapshot(); R.look(0, 1.7, 0, 0.4); R.api.fabCull(false); const c0 = R.api.FAB.culls;
  R.api.fabCull(false); R.look(0.2, 1.7, 0.2, 0.4); R.api.fabCull(false);
  const quiet = R.api.FAB.culls === c0;
  R.look(12, 1.7, 0, 0.4); R.api.fabCull(false); const moved = R.api.FAB.culls === c0 + 1;
  R.look(12, 1.7, 0, 0.4 + 5 * Math.PI / 180); R.api.fabCull(false); const turned = R.api.FAB.culls === c0 + 2;
  check('[cull] re-culls only on real change: none for the same view or 0.3 m of travel; one for 12 m of travel, one for 5 degrees of turn', quiet && moved && turned, `${R.api.FAB.culls} vs ${c0}`);
  R.api.fabSnapshot(); R.api.fabCull(false);
  check('[cull] after a refill the snapshot is retaken and the next cull runs although the camera has not moved', R.api.FAB.culls === c0 + 3);
}
{
  // the drift guarantee: walk and turn in small random steps (a cull runs only when the view key changes) and, after EVERY frame,
  // no instance whose sphere touches the true frustum may be missing from the draw - the stale cull is still sound
  const R = rig(); R.api.fabSnapshot(); let seed = 12345; const rnd = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296) - 0.5;
  let x = 0, z = 0, yaw = 0.7, pitch = 0, miss = 0, frames = 0, culls0 = 0;
  const fr = new THREE.Frustum();
  for (let step = 0; step < 400; step++) {
    x += rnd() * 1.4; z += rnd() * 1.4; yaw += rnd() * 0.012; pitch = Math.max(-0.4, Math.min(0.4, pitch + rnd() * 0.01));
    R.look(x, 1.7, z, yaw, pitch); R.api.fabCull(false); frames++;
    fr.setFromProjectionMatrix(new THREE.Matrix4().multiplyMatrices(R.cam.projectionMatrix, R.cam.matrixWorldInverse));
    for (const m of [R.houses, R.trees]) {
      const drawn = new Set(); for (let j = 0; j < m.count; j++) drawn.add(idxOf(m, j));
      const f = R.api.fabFam(m), g = m.geometry; g.computeBoundingSphere(); const M = new THREE.Matrix4();
      for (let i = 0; i < N; i++) { M.fromArray(f.mat, i * 16); if (fr.intersectsSphere(new THREE.Sphere().copy(g.boundingSphere).applyMatrix4(M)) && !drawn.has(i)) miss++; }
    }
  }
  check('[cull] drift: over 400 small random steps of travel and turn, between culls and after them, no instance touching the true frustum is ever missing from the draw',
    miss === 0 && R.api.FAB.culls > 20 && R.api.FAB.culls < frames, `${miss} missing, ${R.api.FAB.culls} culls in ${frames} frames`);
}
{
  const R = rig(); R.api.fabSnapshot(); R.look(0, 1.7, 700, 0.4); R.api.fabCull(false);
  R.DIAG.noCull = true; R.api.fabCull(false);
  const all = [R.houses, R.blocks, R.trees, R.lamps].every((m) => m.count === N && [...Array(N).keys()].every((j) => idxOf(m, j) === j));
  R.DIAG.noCull = false; R.api.fabCull(false);
  check('[cull] DIAG.noCull (eval only) draws every built instance in order again, and switching it off culls again', all && R.houses.count < N);
  const c = R.api.FAB.culls, n = R.houses.count; R.look(900, 1.7, -900, 2.2); R.api.fabCull(true);
  check('[cull] the overview never culls (the fabric is hidden there): no cull runs and the arrays stay as they were', R.api.FAB.culls === c && R.houses.count === n);
}
{
  const R = rig(); R.api.fabSnapshot(); R.look(0, 1.7, 0, 0, Math.PI / 2 - 0.01);   // straight up: nothing of a flat lot grid at ground level is in view
  R.api.fabCull(false);
  check('[cull] looking at the sky draws (almost) nothing while the built counts stay', R.houses.count < N * 0.1 && R.api.fabBuilt(R.houses) === N, `${R.houses.count}`);
}
console.log(fails ? `test_rendercull: ${fails} FAIL, ${oks} ok` : `test_rendercull: ${oks} ok`);
process.exit(fails ? 1 : 0);
