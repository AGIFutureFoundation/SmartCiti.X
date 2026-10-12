/**
 * Buildings & scenes (wave 16): the dressing RUNS, against the real registries, without a browser.
 *
 * web/test_3d.mjs holds the generator's source to its contracts by pattern, and that is the right tool for
 * "this is pooled" or "this reads the registry". It cannot say whether the code executes: a misspelt
 * variable or a wrong three.js call passes every source check and throws the first time a campus is
 * built. verify_all.sh opens no browser, so this suite takes the BUILT page (web/trade_craft_3d.html),
 * lifts the wave-16 BUILD functions out of its module by name, and runs them in Node on the vendored
 * three.js and its own BufferGeometryUtils - with the page's own payload (the `data` script) and a
 * recording stand-in for the 2D canvas, the one browser facility they use. What it proves:
 *
 *   - every campus in the payload dresses: one name board per hall it hosts, all in ONE mesh; lamps and
 *     benches as ONE InstancedMesh per family; at most three draw calls; the triangles it reports are
 *     the triangles it built;
 *   - no lamp stands on a road, a lot or the plaza, re-checked here from the site plan's own rectangles
 *     rather than trusting the page's own test;
 *   - every board face samples its OWN atlas cell, and no two share one;
 *   - a hall's header signs are one mesh with a quad per face, their backs and lintels handed to the pool;
 *   - a texture repaint at the high tier paints in the base tier's design space and comes back
 *     mipmapped, and the device rule puts a software rasteriser on the base tier.
 *
 *   node web/test_builddress.mjs
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

// the vendored three.js, and its BufferGeometryUtils pointed at it rather than at a bare 'three'
const THREE = await import(pathToFileURL(join(HERE, 'vendor/three.module.min.js')).href);
const tmp = mkdtempSync(join(tmpdir(), 'tc-builddress-'));
let mergeGeometries;
try {
  const bgu = readFileSync(join(HERE, 'vendor/addons/utils/BufferGeometryUtils.js'), 'utf8')
    .replace(/from 'three';/, `from '${pathToFileURL(join(HERE, 'vendor/three.module.min.js')).href}';`);
  writeFileSync(join(tmp, 'bgu.mjs'), bgu);
  ({ mergeGeometries } = await import(pathToFileURL(join(tmp, 'bgu.mjs')).href));
} finally { rmSync(tmp, { recursive: true, force: true }); }

// one top-level function or const out of the built module, by name - an absent one is a failure
const mod = page.slice(page.indexOf("import * as THREE from 'three';"));
const lift = (name) => {
  let i = mod.indexOf(`\nfunction ${name}(`);
  if (i >= 0) { const j = mod.indexOf('\n}\n', i + 1); return mod.slice(i, j + 2); }
  const m = mod.match(new RegExp(`\\n(const|let) ${name}\\b[^\\n]*(\\n(?![a-z/])[^\\n]*)*`));
  if (!m) { console.error('FAIL the built module has no top-level', name); process.exit(1); }
  return m[0];
};

/* A 2D canvas that records what was drawn on it. Text is measured at 0.55 em a glyph, which is all a
   fit-to-width loop needs to terminate the way it does in a browser. */
const canvases = [];
const solidLog = [];          // what the dressing registered as solid, through the page's campusSolid()
function makeCanvas() {
  const calls = [], stack = [];
  let cur = 1;                                    // the current scale, so a stroke knows the space it was drawn in
  const ctx = { font: '10px x', fillStyle: '#000', textAlign: 'left', textBaseline: 'alphabetic', lineWidth: 1, strokeStyle: '#000',
    fillRect: (...a) => calls.push(['fillRect', ...a]), fillText: (t, x, y) => calls.push(['fillText', t, x, y, ctx.font, ctx.fillStyle]),
    measureText: (t) => ({ width: String(t).length * (parseFloat(String(ctx.font).match(/(\d+(?:\.\d+)?)px/)?.[1] ?? 10)) * 0.55 }),
    save: () => { stack.push(cur); calls.push(['save']); }, restore: () => { cur = stack.pop() ?? 1; calls.push(['restore']); },
    scale: (a, b) => { cur *= a; calls.push(['scale', a, b]); },
    beginPath() {}, moveTo() {}, lineTo() {}, stroke: () => calls.push(['stroke', cur]), arc() {}, fill() {}, closePath() {}, strokeRect() {}, rect() {},
    getImageData: (x, y, w, h) => ({ data: new Uint8ClampedArray(w * h * 4).fill(128) }),
    createImageData: (w, h) => ({ data: new Uint8ClampedArray(w * h * 4) }), putImageData() {} };
  const c = { width: 0, height: 0, getContext: () => ctx, calls };
  canvases.push(c);
  return c;
}
globalThis.document = { createElement: (t) => { if (t !== 'canvas') throw new Error('only a canvas is made here, not ' + t); return makeCanvas(); } };

const NAMES = ['TEX_TIER_PX', 'TEX_TIER_MB', 'texMiB', 'texMip', 'texTierAuto', 'texPaint', 'PATTERN_RELIEF', 'paintPattern', 'normalFromHeight',
  'BD_PART_TOP', 'bdHeaderSigns', 'bdHash', 'bdBoxGeo', 'bdNameBoards', 'bdLampGeo', 'bdBenchGeo', 'bdFurniture', 'bdDressCampus',
  'BD_LAMP_EVERY_M', 'boxGeo', 'partCollector', 'box'];
// campusSolid is the page's; here it records, so the dressing's solids can be counted
const body = NAMES.map(lift).join('\n');
const env = {
  THREE, mergeGeometries, D, loc: 'en', geoCache: new Map(), texTier: 'base', anisoNow: () => 4, isTouch: false,
  renderer: null, navigator: {}, mat: { metal: new THREE.MeshStandardMaterial(), wood: new THREE.MeshStandardMaterial() },
  lblFace: (f) => `"${f}" sans-serif`, campusKey: null, hallGroup: new THREE.Group(),
  campusSolid: (x, z, r) => solidLog.push([x, z, r]),
};
const factory = new Function(...Object.keys(env), `"use strict"; let bdCamp = null; let SURF_PX = { low: 128, high: 384 };
  const fabricOf = () => ({ trim: new THREE.MeshStandardMaterial() });
  ${body}
  return { setCamp: (c) => { bdCamp = c; }, TEX_TIER_PX, texTierAuto, texPaint, bdHeaderSigns, bdNameBoards, bdFurniture, bdDressCampus,
           BD_LAMP_EVERY_M, BD_PART_TOP,
           setRenderer: (r, nav, touch) => { renderer = r; navigator = nav; isTouch = touch; } };`);
const P = factory(...Object.values(env));

/* ------------------------------------------------------------ campuses -- */
// the page's own campus geometry, restated only as far as the dressing reads it (buildCampus())
const halls = new Map(D.halls.map((h) => [h.slug, h]));
let campusesDressed = 0, boardsTotal = 0, lampsTotal = 0;
const throws = [];
const perCampus = {};
for (const [key, camp] of Object.entries(D.campuses)) {
  const dk = camp.districts, R = dk.length === 2 ? 124 : 168;
  const plan = dk.length ? D.campusplan[key] : null;
  const RS = plan ? Math.max(R, Math.ceil(plan.radius_m) + 30) : R, rr = RS - 24;
  const g = new THREE.Group();
  const boards = [], roads = [], rects = [];
  if (plan) {
    for (const lot of plan.lots) {
      const B = lot.b, bg = new THREE.Group();
      bg.position.set(B.x, 0, B.z); bg.rotation.y = B.rot_y;
      const H = B.height_m + .35;
      boards.push({ h: halls.get(lot.hall), bg, w: B.w_m, d: B.d_m, hgt: H, headY: H * .5 });
      rects.push({ u: B.aabb.x, v: B.aabb.z, hw: B.aabb.w / 2 + .2, hd: B.aabb.d / 2 + .2 });
    }
    for (const r of [...plan.streets, ...plan.walkways, ...plan.parking]) roads.push({ u: r.x, v: r.z, w: r.w, h: r.d });
  }
  P.setCamp({ key, boards, roads, rects, lit: plan ? roads.slice(0, plan.streets.length + plan.walkways.length) : [] });
  let st; solidLog.length = 0;
  try { st = P.bdDressCampus(g, rr); } catch (e) { throws.push(key + ': ' + e.message); continue; }
  const boardMesh = g.children.find((o) => o.name === 'bd-hall-boards');
  const lamps = g.children.find((o) => o.name === 'bd-lamps'), benches = g.children.find((o) => o.name === 'bd-benches');
  const meshes = g.children.filter((o) => o.isMesh);
  let built = 0;
  for (const o of meshes) built += (o.geometry.index.count / 3) * (o.isInstancedMesh ? o.count : 1);
  // the lamps, re-checked from the plan's own rectangles
  const pos = new THREE.Vector3(), M = new THREE.Matrix4(), bad = [];
  for (let i = 0; lamps && i < lamps.count; i++) {
    lamps.getMatrixAt(i, M); pos.setFromMatrixPosition(M);
    if (roads.some((r) => Math.abs(pos.x - r.u) < r.w / 2 && Math.abs(pos.z - r.v) < r.h / 2)) bad.push('road');
    if (rects.some((b) => Math.abs(pos.x - b.u) < b.hw && Math.abs(pos.z - b.v) < b.hd)) bad.push('lot');
    if (Math.hypot(pos.x, pos.z) <= 30 || Math.hypot(pos.x, pos.z) > rr) bad.push('radius');
  }
  const solids = solidLog.slice();
  perCampus[key] = { solids, halls: boards.length, boards: st.boards.boards, lamps: lamps?.count ?? 0, benches: benches?.count ?? 0,
    drawCalls: st.drawCalls, meshes: meshes.length, tris: st.tris, built, bad, boardMesh, cells: null };
  if (boardMesh) {
    // every quad's UV rectangle, as a cell id: no two boards may sample the same one
    const uv = boardMesh.geometry.attributes.uv, cells = new Set();
    for (let q = 0; q < uv.count; q += 4) {
      const us = [0, 1, 2, 3].map((k) => uv.getX(q + k)), vs = [0, 1, 2, 3].map((k) => uv.getY(q + k));
      cells.add(`${Math.min(...us).toFixed(4)},${Math.min(...vs).toFixed(4)}`);
      if (Math.min(...us, ...vs) < 0 || Math.max(...us, ...vs) > 1) cells.add('OUT');
    }
    perCampus[key].cells = cells;
  }
  campusesDressed++; boardsTotal += st.boards.boards; lampsTotal += lamps?.count ?? 0;
}
const rows = Object.entries(perCampus);
ok(`every campus in the payload dresses without throwing (${campusesDressed} of ${Object.keys(D.campuses).length}), against its own site plan`
  + (throws.length ? ` - threw: ${throws[0]}` : ''),
  throws.length === 0 && campusesDressed === Object.keys(D.campuses).length && campusesDressed === 10);
ok(`every hall a campus hosts gets its name board, all of a campus's boards in ONE mesh (${boardsTotal} boards in ${rows.filter(([, r]) => r.boardMesh).length} meshes)`,
  rows.every(([, r]) => r.boards === r.halls && (r.halls ? r.boardMesh && r.boardMesh.geometry.index.count / 3 === 2 * r.halls : !r.boardMesh))
  && boardsTotal === D.halls.length);
ok('lamps and benches are ONE InstancedMesh per family per campus, eight benches round every plaza, and the whole dressing costs a campus at most three draw calls',
  rows.every(([, r]) => r.benches === 8 && r.lamps >= 8 && r.meshes === r.drawCalls && r.drawCalls <= 3 && r.drawCalls === (r.halls ? 3 : 2)));
ok(`no lamp stands on a road, a lot or the plaza, or past the ring - re-checked from the site plan's own rectangles (${lampsTotal} lamps on 10 campuses)`,
  rows.every(([, r]) => r.bad.length === 0));
ok('the triangles the dressing reports are the triangles it built, on every campus',
  rows.every(([, r]) => r.tris === r.built));
ok('every lamp and bench is SOLID to the walker - one campusSolid() disc each, at the instance\'s own position: the standard its own width, the bench over its seat',
  rows.every(([, r]) => r.solids.length === r.lamps + r.benches
    && r.solids.filter((q) => q[2] === .12).length === r.lamps && r.solids.filter((q) => q[2] === .6).length === r.benches));
/* The dressing's own budget, against the campus ceiling eval_scene.mjs declares - READ from its source
   by structure, as eval_campuses.mjs reads it, so there is one campus budget and not two. The dressing
   may take at most a tenth of a campus's triangle ceiling and three of its draw calls: it is furniture,
   and the measured flagship (51,930 triangles before it) has 11,470 left under the cap for everything. */
{
  const ES = readFileSync(join(HERE, 'eval_scene.mjs'), 'utf8');
  const num = (re, what) => { const m = ES.match(re); if (!m) { console.error('FAIL eval_scene.mjs no longer declares', what); process.exit(1); } return Number(m[1].replace(/_/g, '')); };
  const triCap = num(/^\s*campus:\s*\{\s*calls:\s*[\d_]+,\s*tris:\s*([\d_]+)/m, 'BASE.campus.tris') * num(/^const TRI_HEADROOM = ([\d.]+)/m, 'TRI_HEADROOM');
  const dear = rows.reduce((a, b) => (b[1].tris > a[1].tris ? b : a));
  ok(`the dressing holds to its own share of the campus ceiling read from eval_scene.mjs: at most a tenth of ${triCap.toLocaleString()} triangles and three draw calls on every campus (dearest ${dear[0]}: ${dear[1].tris.toLocaleString()} triangles, ${dear[1].drawCalls} calls)`,
    rows.every(([, r]) => r.tris <= triCap / 10 && r.drawCalls <= 3));
}
ok('every board face samples its OWN cell of the atlas, inside the texture, and no two boards share one',
  rows.every(([, r]) => !r.boardMesh || (r.cells.size === r.halls && !r.cells.has('OUT'))));
console.log('  campus dressing, built here: ' + rows.map(([k, r]) => `${k} ${r.boards}b/${r.lamps}l/${r.benches}s ${r.tris}tri ${r.drawCalls}dc`).join('; '));

/* ------------------------------------------------------- header signs -- */
{
  // a hall's rooms as the page inflates them at boot: its layout's rectangles, the shared room labels
  const h = D.halls[0];
  const rooms = D.layouts[h.lay].map((q, i) => ({ r: { strand: q.strand, label: D.roomDefs[q.strand].label }, n: i + 1, rx: i * 4, rz: 0, rw: 3.6, rd: 6 }));
  // one doorway cut in the first room's front edge, none elsewhere
  const doors = new Map([['z@' + (-3).toFixed(2), [[-.6, .6]]]]);
  const pool = new Map(), col = { add(...os) { for (const o of os) { o.updateMatrix(); (pool.get(o.material) ?? pool.set(o.material, []).get(o.material)).push(o); } } };
  const hg = env.hallGroup; hg.clear();
  const st = P.bdHeaderSigns(h, rooms, doors, col);
  const m = hg.children.filter((o) => o.isMesh);
  const backs = (pool.get(env.mat.metal) ?? []).length;
  ok(`a hall's ${rooms.length} header signs are ONE mesh with two quads a board (both faces), their backs and the one lintel handed to the pool in mat.metal`,
    m.length === 1 && m[0].name === 'bd-room-signs' && m[0].geometry.index.count / 3 === 4 * rooms.length
    && st.boards === rooms.length && st.lintels === 1 && backs === rooms.length + 1);
  const texts = canvases.at(-1).calls.filter((c) => c[0] === 'fillText').map((c) => c[1]);
  ok('each board reads its room\'s number, the room\'s registry label and its strand in the locale, nothing typed',
    rooms.every((s) => texts.includes(String(s.n).padStart(2, '0')) && texts.includes(s.r.label)
      && texts.includes(D.i18n.en.strands[s.r.strand])));
}

/* ------------------------------------------------------------ textures -- */
{
  const before = canvases.length;
  const out = P.texPaint('#8a8f93', 'brick', 1024);
  const made = canvases.slice(before);
  const scale = made[0].calls.find((c) => c[0] === 'scale');
  // brick is drawn as grooves: every stroke of the pattern must land in the base tier's design space
  const strokes = made.flatMap((c) => c.calls.filter((q) => q[0] === 'stroke'));
  ok('a high-tier repaint makes 1024 px canvases, paints the pattern scaled from the base tier\'s 384 px design space, and comes back mipmapped (LinearMipmapLinear) with a normal map',
    made.length >= 2 && made[0].width === 1024 && made[0].height === 1024 && scale && Math.abs(scale[1] - 1024 / 384) < 1e-9
    && strokes.length > 0 && strokes.every((q) => Math.abs(q[1] - 1024 / 384) < 1e-9)
    && out.map.generateMipmaps === true && out.map.minFilter === THREE.LinearMipmapLinearFilter
    && out.normalMap && out.normalMap.minFilter === THREE.LinearMipmapLinearFilter);
  const caps = (who, maxTex, mem, cores, touch) => {
    P.setRenderer({ getContext: () => ({ getExtension: () => ({ UNMASKED_RENDERER_WEBGL: 1 }), getParameter: () => who }),
      capabilities: { maxTextureSize: maxTex } }, { deviceMemory: mem, hardwareConcurrency: cores }, touch);
    return P.texTierAuto();
  };
  ok('the device rule: a software rasteriser is base whatever else it reports; a phone-sized device is base; a GPU device is high; a desktop with 8 GB, 8 cores and an 8192 px limit is ultra',
    caps('Google SwiftShader', 8192, 8, 8, false) === 'base' && caps('llvmpipe (LLVM 15)', 16384, 8, 16, false) === 'base'
    && caps('ANGLE (Apple M2)', 16384, 2, 8, true) === 'base' && caps('ANGLE (Adreno 740)', 8192, 6, 8, true) === 'high'
    && caps('ANGLE (NVIDIA RTX)', 16384, 8, 8, false) === 'ultra' && caps('ANGLE (Intel UHD)', 8192, 8, 4, false) === 'high');
}

/* ------------------------------------------------------ tier repaint -- */
/* The repaint queue itself, run on a stand-in scene. The first browser run of the high tier found the
   budget counting every live texture wider than 384 px - label sprites, the sky - so it repainted
   nothing; that is exactly the shape of scene built here. */
const tierEnv = (tier0) => {
  const NAMES2 = ['TEX_TIER_PX', 'TEX_TIER_MB', 'texMiB', 'texMip', 'texPaint', 'PATTERN_RELIEF', 'paintPattern', 'normalFromHeight',
    'texRecs', 'texSched', 'texTrack', 'texEnqueue', 'texKick', 'texStep', 'texLive', 'texSwap', 'texDrain', 'texSet'];
  const scene = new THREE.Scene();
  const f = new Function('THREE', 'scene', 'texTier', `"use strict";
    const SURF_PX = { low: 128, high: 384 }; const BOOT = { frame1: 1 }; let qLevel = 'high'; const anisoNow = () => 4;
    const window = { requestIdleCallback() {} }; const requestIdleCallback = () => {}; const mat = {}; let fabMats = null;
    ${NAMES2.map(lift).join('\n')}
    return { texTrack, texSet, texDrain, texRecs, stat: () => ({ texUpgraded, texSkipped, texMB, queued: texQ.length }) };`);
  return { scene, T: f(THREE, scene, tier0) };
};
const surf = (px, withNormal = true) => {
  const c = makeCanvas(); c.width = c.height = 384;
  const map = new THREE.CanvasTexture(c);
  const nm = withNormal ? new THREE.CanvasTexture(Object.assign(makeCanvas(), { width: 384, height: 384 })) : null;
  return { map, normalMap: nm, color: '#8a8f93', pattern: 'brick', px };
};
const wear = (scene, rec) => {
  const m = new THREE.MeshStandardMaterial({ map: rec.map.clone(), normalMap: rec.normalMap ? rec.normalMap.clone() : null });
  m.map.repeat.set(2, 3);
  scene.add(new THREE.Mesh(new THREE.BoxGeometry(), m));
  return m;
};
{
  const { scene, T } = tierEnv('base');
  const recs = Array.from({ length: 8 }, () => surf(384));
  recs.forEach((r) => T.texTrack(r));
  const worn = recs.slice(0, 6).map((r) => wear(scene, r));
  let disposed = 0; for (const m of worn) m.map.addEventListener('dispose', () => disposed++);
  // what is NOT a surface and must not spend its budget: a 2048 px label sprite and a 4096 px sky
  const big = (w) => { const c = makeCanvas(); c.width = w; c.height = w / 2; return new THREE.CanvasTexture(c); };
  // a hall view carries dozens of signs; sixteen are enough to have spent the whole budget under the old rule
  for (let i = 0; i < 16; i++) scene.add(new THREE.Sprite(new THREE.SpriteMaterial({ map: big(2048) })));
  scene.background = big(4096);
  scene.add(new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshBasicMaterial({ map: big(4096) })));
  T.texSet('high'); T.texDrain();
  const st = T.stat();
  ok(`the high tier repaints exactly the surfaces the scene wears (6 of 8; the other 2 wait in the queue) at 1024 px, keeping each material's repeat and disposing its old clone - and sixteen 2048 px label sprites and a 4096 px sky spend none of its budget (${st.texUpgraded} repainted, ${st.texSkipped} over budget, ${Math.round(st.texMB)} MB)`,
    st.texUpgraded === 6 && st.texSkipped === 0 && st.queued === 2 && disposed === 6
    && worn.every((m) => m.map.source.data.width === 1024 && m.map.repeat.x === 2 && m.map.repeat.y === 3 && m.normalMap.source.data.width === 1024)
    && recs.slice(6).every((r) => r.px === 384));
}
{
  const { scene, T } = tierEnv('base');
  // seventeen surfaces already at 2048 with normal maps, one without: 746.7 MB of the ultra tier's 768 live
  const held = [...Array.from({ length: 17 }, () => surf(2048)), surf(2048, false)];
  held.forEach((r) => { T.texRecs.add(r); wear(scene, r); });
  const fresh = Array.from({ length: 3 }, () => surf(384));
  fresh.forEach((r) => { T.texTrack(r); wear(scene, r); });
  T.texSet('ultra'); T.texDrain();
  const st = T.stat();
  ok(`ultra steps a surface down to 1024 px when 2048 would cross its budget, and leaves it at its size only when nothing fits (sizes ${fresh.map((r) => r.px).join('/')}, ${Math.round(st.texMB)} of 768 MB)`,
    fresh[0].px === 1024 && fresh[1].px === 1024 && fresh[2].px === 384 && st.texSkipped === 1 && st.texMB <= 768 + 1e-6);
}

console.log(`web/test_builddress: ${n} checks passed - the wave-16 dressing runs on every campus and hall it is given`);
