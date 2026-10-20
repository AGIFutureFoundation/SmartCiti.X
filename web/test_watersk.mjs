/**
 * Checks for the inland water skip of the parish and Bay worlds (web/build_parishes.py, block WATER-SKIP; the page carries
 * the same neutral marker). The water plane is one full-screen pass; it is not drawn when no water can be seen from the eye.
 * The decision is exact geometry: the footprint of the view frustum on the ground plane (view depth capped at the fog's far
 * distance) against the outline edges that can border water (edges not shared, on opposite sides, by two loaded outlines),
 * the holes cut into the land meshes, and one point of drawn land. The block's own JS is cut out of the BUILT page and run
 * here (the pure core alone, then the whole block against the real three.js camera). A brute-force oracle casts rays through
 * the view and asks, for every ray that reaches the water plane inside the fog distance, whether drawn land stops it: every
 * such view must draw the water. Prints `  ok ` per check and `FAIL` at column 0; exit code 1 on failure.
 * Browser rows (frame time, draw calls) stay with web/eval_parishes.mjs and web/eval_bayworld.mjs.
 */
import { readFileSync, existsSync } from 'node:fs';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { join, dirname } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url)), ROOT = join(HERE, '..');
const THREE = await import(pathToFileURL(join(HERE, 'vendor/three.module.min.js')).href);
let fails = 0, oks = 0;
const check = (name, cond, why = '') => { if (cond) { oks++; console.log(`  ok ${name}`); } else { fails++; console.log(`FAIL ${name}${why ? ' :: ' + why : ''}`); } };
const page = (f) => readFileSync(join(HERE, f), 'utf8');
const mainOf = (h) => (h.match(/<script type="module" id="parishes-main">([\s\S]*?)<\/script>/) || [, ''])[1];
const PAGES = { parishes: page('trade_craft_parishes.html'), bay: page('trade_craft_bay.html') };
const MAIN = Object.fromEntries(Object.entries(PAGES).map(([k, h]) => [k, mainOf(h)]));
const BLOCK = /\/\* WATER-SKIP BEGIN[\s\S]*?\/\* WATER-SKIP END \*\//, PURE = /\/\* WATER-SKIP PURE BEGIN \*\/([\s\S]*?)\/\* WATER-SKIP PURE END \*\//;
const blk = (MAIN.parishes.match(BLOCK) || [''])[0], pureSrc = (MAIN.parishes.match(PURE) || [, ''])[1];

// [wiring] one block per page, hooked once after the camera is placed and the culls ran, before the draw
for (const w of ['parishes', 'bay']) {
  const m = MAIN[w];
  check(`[wsk] ${w}: one WATER-SKIP block, neutral marker only (no team codename)`, (m.match(/WATER-SKIP BEGIN/g) || []).length === 1 && (m.match(/WATER-SKIP PURE BEGIN/g) || []).length === 1 && !/WATER·|Inland Water|wave 21/.test(m.match(BLOCK) ? m.match(BLOCK)[0] : 'x'));
  check(`[wsk] ${w}: wskFrame runs once per frame, after the camera is placed and the culls ran, right before the draw`,
    (m.match(/wskFrame\(over\);/g) || []).length === 1 && /perfCull\(over\);[\s\S]*?\n  wskFrame\(over\);[^\n]*\n  fabNpc\(over\);[^\n]*\n  const t0 = performance\.now\(\); if \(!DIAG\.noRender/.test(m));
  check(`[wsk] ${w}: the plane is still one 40 km plane that follows the eye, hidden in the overview by its own line, material untouched`,
    m.includes('new THREE.PlaneGeometry(40000, 40000), matWater') && m.includes('water.visible = !over; scene.background = over ? WATER_BG : SKY_BG;') && /water\.position\.x = eye\.x; water\.position\.z = eye\.z;/.test(m) && /water\.position\.y = -0\.4/.test(m)
    && !/matWater\.(fog|visible|transparent|depthWrite)\s*=/.test(m));
  check(`[wsk] ${w}: the stats report the plane's real state (water.visible) and the skip decision (on, skip, why, evals, skipped frames)`,
    m.includes('water: { visible: water.visible, skip: wskStats(), cut: [...waterCut].sort()') && /function wskStats\(\) \{ return \{ on: !DIAG\.noWaterSkip, skip: WSK\.skip, why: WSK\.why, frames: WSK\.frames, skippedFrames: WSK\.skipped, evals: WSK\.evals/.test(m));
}
check('[wsk] the block sets no ceiling, target or eval threshold, and the pure core reads no page global',
  !/MS_HEADROOM|CALL_HEADROOM|TRI_HEADROOM|FABRIC_FLOOR|BASE\[/.test(blk) && blk.includes('DIAG.noWaterSkip') && !/\b(camera|scene|loaded|PAR|waterNet|waterCut|deep|DIAG|THREE|document|window)\b/.test(pureSrc));
check('[wsk] a dive/ROV and an eye at or under the surface always draw the water; the overview keeps frame()\'s own rule',
  /deep\.state\.mode !== 'off'\) \{ WSK\.skip = false; WSK\.why = 'dive'; WSK\.geoKey = ''; water\.visible = true;/.test(blk) && blk.includes("if (!(c.ey > 0.25)) return { water: true, why: 'eye-low' };") && /if \(over\) \{ WSK\.skip = false; WSK\.why = 'overview'; WSK\.geoKey = ''; return; \}/.test(blk));
check('[wsk] the depth cap is the fog\'s far distance (beyond it the water is exactly the fog colour), never a guess', /far: Math\.min\(camera\.far, scene\.fog \? scene\.fog\.far : camera\.far\)/.test(blk));
if (!pureSrc) { console.log(`test_watersk: ${fails} FAIL, ${oks} ok (no WATER-SKIP block in the parish page)`); process.exit(1); }

const K = new Function(pureSrc + '\nreturn { wskIn, wskBox, wskGeo, wskLand, wskPlanes, wskPoly, wskSeg, wskWater };')();
const sq = (x0, z0, x1, z1) => [[x0, z0], [x1, z0], [x1, z1], [x0, z1]];
function camOf(x, y, z, yaw, pitch, far = 4200, aspect = 1.6, fov = 62) {
  const cam = new THREE.PerspectiveCamera(fov, aspect, 0.3, 60000); cam.position.set(x, y, z); cam.rotation.set(pitch, yaw, 0, 'YXZ'); cam.updateMatrixWorld(); cam.updateProjectionMatrix();
  const e = cam.matrixWorld.elements, pj = cam.projectionMatrix.elements;
  return { ex: e[12], ey: e[13], ez: e[14], rx: e[0], ry: e[1], rz: e[2], ux: e[4], uy: e[5], uz: e[6], fx: -e[8], fy: -e[9], fz: -e[10], tx: 1 / pj[0], ty: 1 / pj[5], far };
}
// yaw 0 looks toward +z (three: a camera looks down -z, rotation.y = yaw; yaw 0 faces -z). The helper below turns "face +x" etc. into a yaw.
const FACE = { '-z': 0, '+x': -Math.PI / 2, '+z': Math.PI, '-x': Math.PI / 2 };

// [synthetic] one parish, a 20 km square of land
{
  const G = K.wskGeo([{ rings: [sq(0, 0, 20000, 20000)], holes: [] }]);
  check('[geo] a lone outline: every edge can border water (4 edges, no seam)', G.edges.length === 16 && G.seams === 0);
  check('[view] mid-land, coast more than the fog distance away in every direction: skipped', !K.wskWater(camOf(10000, 1.7, 10000, 0, -0.08), G).water);
  check('[view] looking at a coast 3 km ahead draws the water', K.wskWater(camOf(10000, 1.7, 3000, FACE['-z'], -0.08), G).water);
  check('[view] the same spot facing away from that coast (the coast is behind the eye) skips', !K.wskWater(camOf(10000, 1.7, 3000, FACE['+z'], -0.08), G).water);
  check('[view] a coast just inside the fog distance (4.0 km ahead) draws, just outside (4.4 km) skips',
    K.wskWater(camOf(10000, 1.7, 4000, FACE['-z'], 0), G).water && !K.wskWater(camOf(10000, 1.7, 4400, FACE['-z'], 0), G).water);
  check('[view] a coast 5 km ahead is beyond the fog far distance 4200: skipped; with the fog at 6 km it draws',
    !K.wskWater(camOf(10000, 1.7, 5000, FACE['-z'], 0, 4200), G).water && K.wskWater(camOf(10000, 1.7, 5000, FACE['-z'], 0, 6000), G).water);
  check('[view] a coast beside the view (outside the side planes) is not seen: facing +x with the -z coast 2 km to the left skips', !K.wskWater(camOf(10000, 1.7, 2000, FACE['+x'], 0, 1500), G).water);
  check('[view] looking at the sky (pitch up, every ray rises) holds no ground: skipped', (() => { const r = K.wskWater(camOf(10000, 1.7, 3000, FACE['-z'], 0.8), G); return !r.water && r.why === 'no-ground'; })());
  check('[view] an eye at or under 0.25 m, or under the surface, always draws', K.wskWater(camOf(10000, 0.2, 10000, 0, 0), G).water && K.wskWater(camOf(10000, -1, 10000, 0, 0), G).water);
  check('[view] a high eye (overhead 300 m) with the coast outside 4.2 km still skips; a coast 3 km off at that height draws',
    !K.wskWater(camOf(10000, 300, 10000, 0, -0.5), G).water && K.wskWater(camOf(10000, 300, 3000, FACE['-z'], -0.5), G).water);
  check('[view] an eye outside every loaded outline (a boat on the open water) draws', K.wskWater(camOf(-5000, 1.2, 10000, FACE['+x'], -0.08), G).water);
}
// [synthetic] seams: two outlines sharing an exact edge (opposite interiors) are one land; a 1 m gap, an unshared half and an overlap are not
{
  const A = sq(0, 0, 10000, 20000), B = sq(10000, 0, 20000, 20000), Bgap = sq(10001, 0, 20000, 20000), Bhalf = [[10000, 0], [20000, 0], [20000, 10000], [10000, 10000]];
  const cam = camOf(10000, 1.7, 10000, FACE['-z'], -0.08, 4200);
  const GS = K.wskGeo([{ rings: [A], holes: [] }, { rings: [B], holes: [] }]);
  check('[seam] two outlines walking the shared edge in opposite directions: the 2 shared edges drop out (6 of 8 stay)', GS.seams === 1 && GS.edges.length === 24);
  check('[seam] standing on the seam with both lands loaded and the far coast beyond the fog: skipped', !K.wskWater(cam, GS).water);
  check('[seam] the same view with only one of the two lands loaded draws (the seam is a coast)', K.wskWater(cam, K.wskGeo([{ rings: [A], holes: [] }])).water);
  check('[seam] a 1 m gap between the outlines is no seam: the view draws', K.wskWater(cam, K.wskGeo([{ rings: [A], holes: [] }, { rings: [Bgap], holes: [] }])).water);
  check('[seam] an edge that only half matches is no seam: the view draws', K.wskWater(cam, K.wskGeo([{ rings: [A], holes: [] }, { rings: [Bhalf], holes: [] }])).water);
  const Aover = sq(0, 0, 10000, 20000), Bover = sq(0, 0, 10000, 20000).reverse();
  check('[seam] two outlines on the SAME side of a shared edge (overlap) are no seam: the edge stays a boundary', K.wskGeo([{ rings: [Aover], holes: [] }, { rings: [sq(0, 0, 10000, 20000)], holes: [] }]).seams === 0
    && K.wskGeo([{ rings: [Aover], holes: [] }, { rings: [Bover], holes: [] }]).seams === 0);
  check('[seam] the orientation of a ring does not matter: a clockwise neighbour still pairs with a counter-clockwise one', K.wskGeo([{ rings: [A], holes: [] }, { rings: [B.slice().reverse()], holes: [] }]).seams === 1);
}
// [synthetic] holes
{
  const land = sq(0, 0, 20000, 20000), pond = (x, z, r) => sq(x - r, z - r, x + r, z + r);
  const cam = camOf(10000, 1.7, 10000, FACE['-z'], -0.08);
  check('[hole] a pond in the view (2 km ahead) draws', K.wskWater(cam, K.wskGeo([{ rings: [land], holes: [pond(10000, 8000, 50)] }])).water);
  check('[hole] a pond beyond the fog distance (5 km ahead) is skipped', !K.wskWater(cam, K.wskGeo([{ rings: [land], holes: [pond(10000, 5000, 50)] }])).water);
  check('[hole] a pond behind the eye and a pond far to the side are not seen', !K.wskWater(cam, K.wskGeo([{ rings: [land], holes: [pond(10000, 11500, 50), pond(14500, 10000, 50)] }])).water);
  check('[hole] a lake that holds the whole view (the eye floats on it) draws', K.wskWater(cam, K.wskGeo([{ rings: [land], holes: [pond(10000, 10000, 9000)] }])).water);
  check('[hole] a hole that holds the view while a neighbour\'s land covers the seam still draws (the hole is cut in the first land only)',
    K.wskWater(camOf(10000, 1.7, 10000, FACE['-z'], -0.08), K.wskGeo([{ rings: [sq(0, 0, 10000, 20000)], holes: [pond(10000, 10000, 9000)] }, { rings: [sq(10000, 0, 20000, 20000)], holes: [] }])).water);
  check('[hole] a hole cut in one land that reaches over the neighbour\'s land still draws when the view holds the seam (the water shows through the first land)',
    K.wskWater(camOf(11200, 1.7, 10000, FACE['-x'], -0.08, 1500), K.wskGeo([{ rings: [sq(0, 0, 10000, 20000)], holes: [pond(10000, 10000, 5000)] }, { rings: [sq(10000, 0, 20000, 20000)], holes: [] }])).why === 'in-hole');
  check('[hole] a hole in a parish does not make the neighbour\'s land a hole: a pond in A far from the view leaves a seam view skipped',
    !K.wskWater(camOf(10000, 1.7, 10000, FACE['-z'], -0.08), K.wskGeo([{ rings: [sq(0, 0, 10000, 20000)], holes: [pond(2000, 18000, 50)] }, { rings: [sq(10000, 0, 20000, 20000)], holes: [] }])).water);
  check('[land] a point is land when some outline holds it and no hole cut into that outline does',
    K.wskLand(K.wskGeo([{ rings: [land], holes: [pond(500, 500, 100)] }]), 5000, 5000) && !K.wskLand(K.wskGeo([{ rings: [land], holes: [pond(500, 500, 100)] }]), 500, 500) && !K.wskLand(K.wskGeo([{ rings: [land], holes: [] }]), -1, 5));
}

// [real data] both worlds: the registry outlines, the AUTHORED water features (held as the page holds them: ribbons thinned by 8)
const CH = 8;
function world(which) {
  const D = JSON.parse((PAGES[which].match(/<script type="application\/json" id="parishes-data">([\s\S]*?)<\/script>/) || [, 'null'])[1]);
  const feats = {};
  for (const p of D.parishes) {
    feats[p.id] = []; const f = join(ROOT, p.world); if (!existsSync(f)) continue;
    const j = JSON.parse(readFileSync(f, 'utf8')), [ox, oz] = p.origin_m;
    const add = (kind, e) => { const pg = e.polygon, n = pg.length, half = n / 2, ribbon = kind !== 'lake' && kind !== 'pond' && n % 2 === 0;
      feats[p.id].push(pg.filter((_, i) => !ribbon || (i < half ? i % CH === 0 || i === half - 1 : (i - half) % CH === 0 || i === n - 1)).map(([E, N]) => [ox + E, oz - N])); };
    for (const e of j.water.lakes) add('lake', e); for (const e of j.water.channels) add(e.kind, e); for (const e of j.water.ponds) add('pond', e);
  }
  const PAR = new Map(D.parishes.map((p) => [p.id, p]));
  const inParish = (p, x, z) => { let c = false; for (const r of p.rings_m) if (K.wskIn(r, x, z)) c = !c; return c; };
  const parishAt = (x, z) => { for (const p of PAR.values()) if (inParish(p, x, z)) return p; return null; };
  const segDist = (x, z, a, b) => { const dx = b[0] - a[0], dz = b[1] - a[1], L = dx * dx + dz * dz; let t = L ? ((x - a[0]) * dx + (z - a[1]) * dz) / L : 0; t = Math.max(0, Math.min(1, t)); return Math.hypot(x - a[0] - t * dx, z - a[1] - t * dz); };
  const lineDist = (x, z, pts) => { let d = Infinity; for (let i = 1; i < pts.length; i++) d = Math.min(d, segDist(x, z, pts[i - 1], pts[i])); return d; };
  const longest = (segs) => { let b = segs[0], bl = -1; for (const sg of segs) { let l = 0; for (let i = 1; i < sg.length; i++) l += Math.hypot(sg[i][0] - sg[i - 1][0], sg[i][1] - sg[i - 1][1]); if (l > bl) { bl = l; b = sg; } } return b; };
  const parts = (ids) => [...ids].map((id) => { const p = PAR.get(id); return { rings: p.rings_m, holes: feats[id].filter((r) => p.rings_m.some((q) => K.wskIn(q, r[0][0], r[0][1]))) }; });
  const loadedFor = (x, z, cur) => { const want = new Set(), here = parishAt(x, z) || cur; want.add(here.id); for (const n of here.neighbours) if (n.segments.some((sg) => lineDist(x, z, sg) < 1500)) want.add(n.id); return want; };
  const startSpot = (p) => { const l = p.landmarks[0]; if (l && parishAt(l.x, l.z + 90) === p) return [l.x, l.z + 90]; return parishAt(p.origin_m[0], p.origin_m[1]) === p ? p.origin_m : p.rings_m[0][0]; };
  const border = (a, b) => { const nb = PAR.get(a).neighbours.find((n) => n.id === b), pts = longest(nb.segments), i = Math.floor(pts.length / 2), p0 = pts[Math.max(0, i - 1)], p1 = pts[Math.min(pts.length - 1, i)];
    const mx = (p0[0] + p1[0]) / 2, mz = (p0[1] + p1[1]) / 2; let nx = -(p1[1] - p0[1]), nz = p1[0] - p0[0]; const L = Math.hypot(nx, nz) || 1; nx /= L; nz /= L;
    if (!inParish(PAR.get(a), mx + nx * 40, mz + nz * 40)) { nx = -nx; nz = -nz; } return { from: [mx + nx * 40, mz + nz * 40], yaw: Math.atan2(nx, nz) }; };
  return { D, PAR, feats, parts, loadedFor, startSpot, border, parishAt };
}
const W = { parishes: world('parishes'), bay: world('bay') };
const evalViews = (which) => { const w = W[which], out = [];
  for (const p of w.D.parishes) {
    const [x, z] = w.startSpot(p); out.push({ id: p.id, view: 'origin', x, z, yaw: 0, ids: w.loadedFor(x, z, p) });
    if (p.neighbours[0]) { const a = w.border(p.id, p.neighbours[0].id); out.push({ id: p.id, view: 'border', x: a.from[0], z: a.from[1], yaw: a.yaw, ids: w.loadedFor(a.from[0], a.from[1], p) }); }
  } return out; };
const decided = {};
for (const which of ['parishes', 'bay']) {
  const w = W[which], vs = evalViews(which); let sk = 0;
  const t0 = performance.now();
  for (const v of vs) { const G = K.wskGeo(w.parts(v.ids)), r = K.wskWater(camOf(v.x, 1.7, v.z, v.yaw, -0.08), G); v.skip = !r.water; v.why = r.why; if (v.skip) sk++; }
  decided[which] = vs;
  console.log(`  -- ${which}: ${sk} of ${vs.length} eval-style views (origin + border of every ${which === 'bay' ? 'county' : 'parish'}) skip the water plane; ${(performance.now() - t0).toFixed(0)} ms for all decisions`);
  check(`[real] ${which}: the skip is neither vacuous nor total (some of ${vs.length} views skip, some draw)`, sk >= 1 && sk < vs.length, `${sk} of ${vs.length}`);
  check(`[real] ${which}: every skip names the geometry it rests on (inland or no-ground), every draw names what it saw`, vs.every((v) => (v.skip ? ['inland', 'no-ground'] : ['outline-edge', 'hole-edge', 'in-hole', 'off-land', 'eye-low']).includes(v.why)));
}
// the brute-force oracle: rays through a grid of pixels (and the frame's border), the ground crossing of each ray that reaches the water plane inside the fog distance
function oracleWater(c, parts, nx = 48, ny = 30) {
  const G = K.wskGeo(parts); let hit = 0, rays = 0;
  for (let i = 0; i <= nx; i++) for (let j = 0; j <= ny; j++) {
    const u = (i / nx) * 2 - 1, v = (j / ny) * 2 - 1;
    const dx = c.fx + u * c.tx * c.rx + v * c.ty * c.ux, dy = c.fy + u * c.tx * c.ry + v * c.ty * c.uy, dz = c.fz + u * c.tx * c.rz + v * c.ty * c.uz;
    if (!(dy < -1e-9)) continue;
    const t = (c.ey + 0.4) / -dy; if (t > c.far) continue;   // depth along the forward axis is t (the pixel's depth), the fog's far distance
    const t0 = c.ey / -dy; rays++;
    if (!K.wskLand(G, c.ex + t0 * dx, c.ez + t0 * dz)) hit++;
  }
  return { hit, rays };
}
{
  // a seeded sweep of cameras over both worlds: random spot in a random parish's box, random yaw/pitch/height/aspect/fog
  let s = 12345; const rnd = () => (s = (s * 1664525 + 1013904223) >>> 0) / 4294967296;
  for (const which of ['parishes', 'bay']) {
    const w = W[which], list = [...w.PAR.values()]; let unsound = 0, skips = 0, draws = 0, n = 0, conservative = 0, firstBad = '';
    for (let k = 0; k < 1500; k++) {
      const p = list[Math.floor(rnd() * list.length)], b = p.bbox || (() => { const bb = K.wskBox(p.rings_m.flat()); return bb; })();
      const x = b[0] + rnd() * (b[2] - b[0]), z = b[1] + rnd() * (b[3] - b[1]), ids = w.loadedFor(x, z, p);
      const y = [1.2, 1.4, 1.7, 1.7, 30, 300][Math.floor(rnd() * 6)], pitch = -0.7 + rnd() * 0.9, yaw = rnd() * 2 * Math.PI, far = rnd() < 0.7 ? 4200 : 1000 + rnd() * 3000, asp = rnd() < 0.5 ? 1.6 : 1.78;
      const c = camOf(x, y, z, yaw, pitch, far, asp), parts = w.parts(ids), r = K.wskWater(c, K.wskGeo(parts)), o = oracleWater(c, parts);
      n++; if (r.water) draws++; else skips++;
      if (o.hit > 0 && !r.water) { unsound++; if (!firstBad) firstBad = `${p.id} @ ${x.toFixed(0)},${z.toFixed(0)} y${y} yaw${yaw.toFixed(2)} pitch${pitch.toFixed(2)} hits ${o.hit}/${o.rays}`; }
      if (o.hit === 0 && r.water) conservative++;
    }
    console.log(`  -- ${which}: ${n} random cameras: ${skips} skipped, ${draws} drawn (${conservative} of the drawn had no water on any sampled ray: the test is conservative there, never the other way)`);
    check(`[oracle] ${which}: no camera whose rays reach un-covered water inside the fog distance is skipped (${n} cameras, ray grid 49x31)`, unsound === 0, firstBad);
    check(`[oracle] ${which}: the sweep is not vacuous (>= 100 skipped and >= 100 drawn cameras)`, skips >= 100 && draws >= 100, `${skips} skipped, ${draws} drawn`);
  }
}
// the drawn land really covers what the test calls land: the page's own ShapeGeometry (outline + the cut holes, as cutWater builds it)
{
  let bad = 0, tested = 0, firstBad = '';
  for (const which of ['parishes', 'bay']) {
    const w = W[which];
    for (const p of w.D.parishes) {
      const holes = w.feats[p.id].filter((r) => p.rings_m.some((q) => K.wskIn(q, r[0][0], r[0][1]))), G = K.wskGeo([{ rings: p.rings_m, holes }]);
      const shapes = p.rings_m.map((r) => new THREE.Shape(r.map(([x, z]) => new THREE.Vector2(x, -z))));
      for (const r of holes) { const k = p.rings_m.findIndex((q) => K.wskIn(q, r[0][0], r[0][1])); shapes[k].holes.push(new THREE.Path(r.map(([x, z]) => new THREE.Vector2(x, -z)))); }
      const g = new THREE.ShapeGeometry(shapes); g.rotateX(-Math.PI / 2); const pa = g.attributes.position.array, ix = g.index ? g.index.array : null, nt = (ix ? ix.length : pa.length / 3) / 3;
      const tri = (i) => { const a = ix ? ix[i * 3] : i * 3, b = ix ? ix[i * 3 + 1] : i * 3 + 1, c = ix ? ix[i * 3 + 2] : i * 3 + 2; return [pa[a * 3], pa[a * 3 + 2], pa[b * 3], pa[b * 3 + 2], pa[c * 3], pa[c * 3 + 2]]; };
      const T = Array.from({ length: nt }, (_, i) => tri(i));
      const inTri = (t, x, z) => { const d1 = (x - t[2]) * (t[1] - t[3]) - (t[0] - t[2]) * (z - t[3]), d2 = (x - t[4]) * (t[3] - t[5]) - (t[2] - t[4]) * (z - t[5]), d3 = (x - t[0]) * (t[5] - t[1]) - (t[4] - t[0]) * (z - t[1]); return !((d1 < 0 || d2 < 0 || d3 < 0) && (d1 > 0 || d2 > 0 || d3 > 0)); };
      const bb = G.parishes[0].box; let s = p.id.length * 7919 + 17; const rnd = () => (s = (s * 1664525 + 1013904223) >>> 0) / 4294967296;
      for (let k = 0; k < 400; k++) {
        const x = bb[0] + rnd() * (bb[2] - bb[0]), z = bb[1] + rnd() * (bb[3] - bb[1]); if (!K.wskLand(G, x, z)) continue;
        tested++; if (!T.some((t) => inTri(t, x, z))) { bad++; if (!firstBad) firstBad = `${which} ${p.id} @ ${x.toFixed(0)},${z.toFixed(0)}`; }
      }
    }
  }
  check(`[mesh] every sampled point the test calls drawn land lies under a triangle of the land mesh the page builds (${tested} points, both worlds)`, bad === 0 && tested > 1000, `${bad} of ${tested} uncovered; ${firstBad}`);
}

// [page glue] the whole block against the real three.js camera, with the page's globals stubbed by plain data
{
  const w = W.parishes, ids = ['22071'], p = w.PAR.get('22071');
  const mk = () => {
    const camera = new THREE.PerspectiveCamera(62, 1.6, 0.3, 60000), scene = new THREE.Scene(); scene.fog = new THREE.Fog(0xd3dfe3, 700, 4200);
    const water = { visible: true }, loaded = new Set(ids), waterNet = new Map(), waterCut = new Set(), DIAG = {}, deepStub = { state: { mode: 'off' } };
    const PAR = w.PAR, inRing = K.wskIn;
    const api = new Function('camera', 'scene', 'water', 'loaded', 'PAR', 'waterNet', 'waterCut', 'inRing', 'DIAG', 'deep', 'performance', blk + '\nreturn { WSK, wskFrame, wskStats };')(camera, scene, water, loaded, PAR, waterNet, waterCut, inRing, DIAG, deepStub, performance);
    return { camera, scene, water, loaded, waterNet, waterCut, DIAG, deepStub, api, look: (x, y, z, yaw, pitch) => { camera.position.set(x, y, z); camera.rotation.set(pitch, yaw, 0, 'YXZ'); camera.updateMatrixWorld(); } };
  };
  const spot = w.startSpot(p), R = mk(); R.look(spot[0], 1.7, spot[1], 0, -0.08);
  const cv = camOf(spot[0], 1.7, spot[1], 0, -0.08), expect = !K.wskWater(cv, K.wskGeo(w.parts(ids))).water;
  R.api.wskFrame(false);
  check('[glue] the block\'s frame step agrees with the pure test for the same camera and land (22071 start spot)', R.water.visible === !expect && R.api.WSK.skip === expect, `visible ${R.water.visible} expect skip ${expect}`);
  const e1 = R.api.WSK.evals; R.api.wskFrame(false); R.api.wskFrame(false);
  check('[glue] a still camera and unchanged land cost no new decision (cached), the frame count still moves', R.api.WSK.evals === e1 && R.api.WSK.frames === 3);
  R.look(spot[0] + 5, 1.7, spot[1], 0, -0.08); R.api.wskFrame(false);
  check('[glue] a moved camera is decided again', R.api.WSK.evals === e1 + 1);
  R.waterNet.set('22071', { feats: [{ ring: sq(spot[0] - 50, spot[1] - 400, spot[0] + 50, spot[1] - 300) }], surface: 0 });
  R.loaded.add('22051'); R.api.wskFrame(false); const e2 = R.api.WSK.evals;
  check('[glue] a change of the loaded parishes rebuilds the land and decides again', e2 === e1 + 2 && R.api.WSK.geo.parishes.length === 2 && R.api.WSK.geo.holes.length === 0);
  R.api.wskFrame(false);
  check('[glue] a water net that has not been cut into the land changes nothing (the mesh has no hole yet)', R.api.WSK.evals === e2);
  R.waterCut.add('22071'); R.api.wskFrame(false);
  check('[glue] once cutWater has cut the hole, the key changes and the hole is in the land (its owner outline holds its first point)', R.api.WSK.evals === e2 + 1 && R.api.WSK.geo.holes.length === 1);
  R.look(spot[0], 1.7, spot[1], 0, -0.08); R.water.visible = true; R.api.wskFrame(true);
  check('[glue] the overview leaves the plane to frame() (hidden there by its own line) and reports why', R.api.wskStats().why === 'overview' && R.api.wskStats().skip === false);
  R.DIAG.noWaterSkip = true; R.api.wskFrame(false);
  check('[glue] DIAG.noWaterSkip (the A/B switch) draws the plane and reports on: false', R.water.visible === true && R.api.wskStats().on === false && R.api.wskStats().why === 'diag-off');
  R.DIAG.noWaterSkip = false; R.look(spot[0], 1.7, spot[1], 0, -0.08); R.api.wskFrame(false);
  check('[glue] switching the A/B switch back on with a still camera decides again (no stale draw/skip state)', R.api.wskStats().on === true && R.api.wskStats().why !== 'diag-off' && R.api.WSK.skip === !K.wskWater(camOf(spot[0], 1.7, spot[1], 0, -0.08), R.api.WSK.geo).water && R.water.visible === !R.api.WSK.skip);
  R.deepStub.state.mode = 'dive'; R.api.wskFrame(false);
  check('[glue] a dive draws the plane', R.water.visible === true && R.api.wskStats().why === 'dive');
  R.deepStub.state.mode = 'off'; R.look(spot[0], 0.1, spot[1], 0, 0); R.api.wskFrame(false);
  check('[glue] an eye under 0.25 m draws the plane', R.water.visible === true && R.api.wskStats().why === 'eye-low');
}
console.log(`test_watersk: ${fails} FAIL, ${oks} ok`);
process.exit(fails ? 1 : 0);
