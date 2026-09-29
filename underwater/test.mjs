/**
 * underwater/ + web/deepkit.py verification.
 *   node underwater/test.mjs                 node underwater/test.mjs --root=/tmp/copy (mutation runs)
 * Checks are tagged [name]; a failing check prints FAIL at column 0 and the run exits non-zero.
 */
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, mkdtempSync, rmSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join, resolve, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const rootArg = process.argv.slice(2).find((a) => a.startsWith('--root='));
const ROOT = resolve(rootArg ? rootArg.slice(7) : join(HERE, '..'));
let n = 0, bad = 0;
const ok = (tag, cond, msg) => { n++; if (cond) console.log(`  ok [${tag}] ${msg}`); else { bad++; console.log(`FAIL [${tag}] ${msg}`); } };
const rd = (p) => readFileSync(join(ROOT, p));
const js = (p) => JSON.parse(rd(p).toString());
const sha = (b) => createHash('sha256').update(b).digest('hex');

const REGP = 'underwater/registry/underwater.json';
const regRaw = rd(REGP), reg = JSON.parse(regRaw.toString());

// [stamp] the registry was written by the shipped builder
ok('stamp', reg.source_stamp === sha(rd('underwater/build.py')).slice(0, 16), `source_stamp ${reg.source_stamp} = sha256(build.py)[:16]`);

// [determinism] a rebuild into a temp file is byte-identical
const tmp = mkdtempSync(join(tmpdir(), 'deep-'));
try {
  execFileSync('python3', [join(ROOT, 'underwater/build.py'), '--out=' + join(tmp, 'u.json')], { cwd: ROOT, stdio: 'pipe' });
  ok('determinism', sha(readFileSync(join(tmp, 'u.json'))) === sha(regRaw), 'rebuild byte-identical');
} finally { rmSync(tmp, { recursive: true, force: true }); }

// [legend] provenance vocabulary + honesty text
const H = reg.honesty;
ok('legend', /AUTHORED/.test(H) && /no real bathymetry/.test(H) && /not dive training/.test(H) && /never harmed/.test(H) && /not for navigation/.test(H),
  'honesty says AUTHORED depths, no real bathymetry, not for navigation, not dive training, animals never harmed');
ok('legend', ['depth', 'substrate', 'habitat', 'shoreline_recorded', 'shoreline_authored'].every((k) => typeof reg.legend[k] === 'string')
  && /^AUTHORED/.test(reg.legend.depth) && /^AUTHORED/.test(reg.legend.habitat) && /^RECORDED/.test(reg.legend.shoreline_recorded), 'legend: depth/substrate/habitat AUTHORED, shoreline RECORDED|AUTHORED');
ok('legend', reg.bodies.every((b) => b.habitats.every((h) => h.provenance === 'AUTHORED')), 'every habitat patch AUTHORED');
ok('legend', reg.restore_hooks.status === 'PENDING' && Array.isArray(reg.restore_hooks.funded_projects) && reg.restore_hooks.funded_projects.length === 0,
  'funded_projects [] PENDING (no project named from the unfetched article)');

// [ne] every RECORDED shoreline names a vendored NE layer + scale, and the vendored file matches the manifest sha256
const man = js('terrain/vendor/manifest.json');
const rec = reg.bodies.filter((b) => b.shoreline.provenance === 'RECORDED');
ok('ne', rec.length === reg.ne_shorelines_used.length && rec.length >= 3, `${rec.length} RECORDED shorelines = ne_shorelines_used (${reg.ne_shorelines_used.join(', ')})`);
ok('ne', rec.every((b) => { const f = b.shoreline.file.split('/').pop(); return man.files[f] && man.files[f].layer === b.shoreline.layer.slice(3)
  && sha(rd(b.shoreline.file)) === man.files[f].sha256 && /1:10,000,000/.test(b.shoreline.scale); }), 'layer + 1:10m scale + vendored sha256 match the manifest');
ok('ne', reg.bodies.filter((b) => b.shoreline.provenance !== 'RECORDED').every((b) => b.shoreline.provenance === 'AUTHORED'), 'every other shoreline AUTHORED');

// [coverage] one body per lake/channel/pond of every world file, + the Bay open water
const worlds = [['parishes', 'parishes/registry/parishes.json', 'parishes', 'parishes/maps/world'], ['bay', 'bayarea/registry/bayarea.json', 'counties', 'bayarea/maps/world']];
const ids = new Set(reg.bodies.map((b) => b.id));
let want = 0, miss = [];
for (const [, rp, key, dir] of worlds) for (const f of Object.keys(js(rp)[key])) { const w = js(`${dir}/${f}.json`).water;
  for (const k of ['lakes', 'channels', 'ponds']) for (const x of w[k]) { want++; if (!ids.has(x.id)) miss.push(x.id); } }
ok('coverage', miss.length === 0 && ids.size === reg.bodies.length && reg.bodies.length === want + 1 && ids.has('bay-open-0'),
  `${reg.bodies.length} bodies = ${want} world-file water bodies + bay-open-0 (missing ${miss.length})`);
ok('coverage', reg.counts.bodies === reg.bodies.length && reg.counts.habitats === reg.bodies.reduce((a, b) => a + b.habitats.length, 0), 'counts recomputed');

// [grid] shapes, depth bounds, substrate codes
let gbad = [];
for (const b of reg.bodies) {
  if (b.grid) { const g = b.grid;
    if (g.depth_dm.length !== g.ny || g.depth_dm.some((r) => r.length !== g.nx)) gbad.push(b.id + ':shape');
    for (let j = 0; j < g.ny; j++) for (let i = 0; i < g.nx; i++) { const d = g.depth_dm[j][i], s = g.substrate[j][i];
      if (d < 0 || d > b.depth_max_dm || (d === 0) !== (s === -1) || s >= reg.substrates.length) { gbad.push(`${b.id}:${i},${j}`); break; } }
    if (!g.depth_dm.some((r) => r.some((d) => d > 0))) gbad.push(b.id + ':dry');
  } else if (b.channel_grid) { const c = b.channel_grid;
    if (c.depth_dm.length !== c.stations_world_m.length || c.depth_dm.some((r) => r.length !== c.across || r.some((d) => d <= 0 || d > b.depth_max_dm))) gbad.push(b.id + ':ch');
  } else gbad.push(b.id + ':nogrid');
}
ok('grid', gbad.length === 0, `grids well-formed, 0 < depth <= depth_max_dm on wet cells (${gbad.slice(0, 3).join(' ')})`);
const bay = reg.bodies.find((b) => b.id === 'bay-open-0');
const bayWet = bay.grid.depth_dm.flat().filter((d) => d > 0).length;
ok('grid', bayWet > 500 && bayWet < bay.grid.nx * bay.grid.ny, `Bay open water: ${bayWet} wet of ${bay.grid.nx * bay.grid.ny} cells (NE land masks the rest)`);

// [budget] registry bytes
ok('budget', regRaw.length <= 1500000, `registry ${regRaw.length} B <= 1,500,000`);

// ---- the kit (web/deepkit.py) in node with real three.js geometry and a DOM stub ----
const kitPy = rd('web/deepkit.py').toString();
ok('nofetch', !/fetch\(|XMLHttpRequest|https?:\/\//.test(kitPy.split("DEEP_JS = r'''")[1] || 'x'), 'kit JS never fetches');
const kitJs = execFileSync('python3', ['-c', 'import sys; sys.path.insert(0, "web"); from deepkit import deep_inline, deep_data; import json; print(deep_inline()); print("const __DATA = " + json.dumps(deep_data("parishes")) + ";"); print("const __BAY = " + json.dumps(deep_data("bay")) + ";")'], { cwd: ROOT, maxBuffer: 1 << 26 }).toString();
const three = pathToFileURL(join(ROOT, 'web/vendor/three.module.min.js')).href;
const el = () => ({ hidden: false, dataset: {}, setAttribute() {}, addEventListener() {}, appendChild() {}, getContext: () => ({ fillRect() {}, beginPath() {}, arc() {}, stroke() {} }), width: 0, height: 0 });
globalThis.document = { createElement: el, getElementById: () => null, body: el() };
globalThis.addEventListener = () => {};
const dir = mkdtempSync(join(tmpdir(), 'deepkit-'));
let K;
try {
  writeFileSync(join(dir, 'k.mjs'), `import * as THREE from '${three}';\n${kitJs}\nexport { THREE, DEEP_BUDGET, deepWorld, deepIndex, deepState, deepStep, deepMount, __DATA, __BAY };`);
  K = await import(pathToFileURL(join(dir, 'k.mjs')).href);
} finally { rmSync(dir, { recursive: true, force: true }); }
const { THREE } = K;

// [world] the JS registry filter equals the Python embed, fails closed on an unknown world
ok('world', JSON.stringify(K.deepWorld(reg, 'parishes')) === JSON.stringify(K.__DATA) && JSON.stringify(K.deepWorld(reg, 'bay')) === JSON.stringify(K.__BAY), 'deepWorld(reg, w) === deep_data(w) for parishes + bay');
let threw = false; try { K.deepWorld(reg, 'atlantis'); } catch (e) { threw = /no underwater bodies/.test(e.message); }
ok('world', threw, 'deepWorld throws by name on a world with no bodies');
// [fsm] the dive / ROV state machine
const idx = K.deepIndex(K.__DATA);
const lake = K.__DATA.bodies.find((b) => b.id === '22103-lake-0'), g = lake.grid;
let wi = -1, wj = -1; for (let j = 0; j < g.ny && wi < 0; j++) for (let i = 0; i < g.nx; i++) if (g.depth_dm[j][i] >= 25) { wi = i; wj = j; break; }
const E = g.origin_world_m[0] + wi * g.cell_m, N = g.origin_world_m[1] + wj * g.cell_m, S = lake.surface_y_m;
const C = (o) => ({ overview: false, waterState: 'swim', surface: S, at: idx.depthAt, eyeE: E, eyeN: N, eyeYaw: 0, ...o });
let st = K.deepState(), ev;
ev = K.deepStep(st, { dive: true }, 0.1, C({ waterState: 'dry' }));
ok('fsm', st.mode === 'off' && ev[0].type === 'refused', 'dive refused unless physkit says swim');
ev = K.deepStep(st, { dive: true }, 0.1, C({}));
ok('fsm', st.mode === 'dive' && ev[0].type === 'enter' && st.y < S, 'swim + Dive -> dive below the surface');
for (let t = 0; t < 30; t += 0.1) K.deepStep(st, { vertical: -1 }, 0.1, C({}));
const bed = S - idx.depthAt(E, N).d;
ok('fsm', Math.abs(st.y - (bed + 0.3)) < 1e-9, `swim down stops 0.3 m above the AUTHORED bed (${st.y.toFixed(2)})`);
let up = []; for (let t = 0; t < 30 && st.mode === 'dive'; t += 0.1) up = K.deepStep(st, { vertical: 1 }, 0.1, C({}));
ok('fsm', st.mode === 'off' && up.some((e) => e.type === 'exit' && e.reason === 'surfaced'), 'swim up to the top -> surfaced, mode off');
K.deepStep(st, { rov: true }, 0.1, C({ waterState: 'dry' }));
ok('fsm', st.mode === 'rov', 'ROV launches from any state when water is under the eye');
const h = (() => { const c = C({}); const hh = { ...st }; return K.deepStep(st, {}, 0.1, c), c; })();
ok('fsm', st.mode === 'rov' && st.y <= S - 0.2, 'ROV stays below the surface');
ev = K.deepStep(st, {}, 0.1, C({ overview: true }));
ok('fsm', st.mode === 'off' && ev[0].reason === 'overview', 'overview forces mode off');
K.deepStep(st, { rov: true }, 0.1, C({})); let blocked = false;
for (let t = 0; t < 8000 && !blocked; t += 1) blocked = K.deepStep(st, { fwd: 1 }, 10, C({})).some((e) => e.type === 'blocked');
ok('fsm', blocked && st.mode === 'rov' && idx.depthAt(st.e, st.n) !== null, 'ROV driven to the shore is blocked and stays in water');
ok('fsm', K.deepStep(st, { rov: true }, 0.1, C({}))[0].reason === 'toggle' && st.mode === 'off', 'ROV toggle -> off');
ok('fsm', idx.depthAt(E + 1e6, N) === null, 'no water far outside every body');

// [budget]/[overview] the mounted kit: meshes, draw calls, props
const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(60, 1, 0.1, 5000);
const added = []; const add0 = scene.add.bind(scene); scene.add = (m) => { added.push(m); return add0(m); };
const eye = { x: E, z: -N, yaw: 0 };
const kit = K.deepMount({ THREE, scene, camera, data: K.__DATA, eye, getMode: () => 'walk', waterState: () => 'swim', T: (k) => k });
const draws = () => added.filter((m) => m.visible && (m.isMesh || m.isInstancedMesh)).length;
ok('budget', added.length <= K.DEEP_BUDGET.calls && K.DEEP_BUDGET.calls === 4, `${added.length} meshes added <= 4 draw calls`);
kit.update(0.1, false);
ok('overview', draws() === 0 && kit.stats().calls === 0, 'above the surface (mode off): 0 draw calls');
kit.force('dive', E, N, S - 1);
kit.update(0.016, false);
const s1 = kit.stats();
ok('budget', s1.under && s1.calls >= 1 && s1.calls <= 4 && draws() === s1.calls, `under water: ${s1.calls} draw calls (<= 4), ${s1.props} props`);
ok('budget', s1.props <= 3 * K.DEEP_BUDGET.props && added.filter((m) => m.isInstancedMesh).every((m) => m.count <= K.DEEP_BUDGET.props), `props within ${K.DEEP_BUDGET.props} per family`);
ok('overview', scene.fog && scene.fog.isFogExp2, 'under water: exponential tint fog on');
kit.update(0.016, true);
ok('overview', draws() === 0 && kit.stats().calls === 0 && kit.state.mode === 'off', 'overview: 0 draw calls, mode off');
ok('overview', !(scene.fog && scene.fog.isFogExp2), 'overview: page fog restored');
const k2 = K.deepMount({ THREE, scene: new THREE.Scene(), camera, data: K.__DATA, eye, getMode: () => 'walk', waterState: () => 'swim', T: (k) => k, initial: 'dive' });
k2.update(0.016, false);
ok('fsm', k2.state.mode === 'dive', 'initial press (lazy load) is replayed: Dive -> dive');
kit.setTargets([{ id: 't1', world_m: [E, N], r_m: 5 }]); kit.force('rov', E, N, S - 1); kit.update(0.016, false);
ok('restore', kit.stats().sampled.includes('t1'), 'RESTORE hook: a target within r_m is reached (play only)');
const bidx = K.deepIndex(K.__BAY), bg = bay.grid; let bi = null;
for (let j = 0; j < bg.ny && !bi; j++) for (let i = 0; i < bg.nx; i++) if (bg.depth_dm[j][i] > 80) { bi = [bg.origin_world_m[0] + i * bg.cell_m, bg.origin_world_m[1] + j * bg.cell_m]; break; }
ok('grid', bi && bidx.depthAt(bi[0], bi[1]).d > 8, 'Bay open water depth lookup works in the Bay world frame');

console.log(`${n - bad}/${n} checks passed`);
if (bad) { console.log(`FAIL ${bad} check(s)`); process.exit(1); }
