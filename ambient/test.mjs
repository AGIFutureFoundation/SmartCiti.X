/**
 * Ambient pack + kit verification (ambient/registry/ambient.json, web/ambientkit.py).
 *
 * Recomputes the registry's claims from the files that own them (stamp, reused fauna, land uses), then drives
 * the kit itself in node with the vendored THREE: budgets (meshes <= draw_calls_max, instances <= caps, LOD
 * radii), deterministic scatter, overview off, flee / follow / road-yield behaviour, wind ranges, dispose.
 *
 *   node ambient/test.mjs
 *   node ambient/test.mjs --root=/tmp/copy      (mutation runs: a broken copy)
 */
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, mkdtempSync, rmSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join, resolve, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const hit = process.argv.slice(2).find((a) => a.startsWith('--root='));
const ROOT = resolve(hit ? hit.slice(7) : join(HERE, '..'));

let n = 0, bad = 0;
const ok = (m, c, evidence = []) => {
  if (c) { n++; console.log('  ok  ' + m); return; }
  bad++; console.log('FAIL  ' + m); for (const e of evidence) console.log('      ' + e);
};
const readJSON = (rel) => JSON.parse(readFileSync(join(ROOT, rel), 'utf8'));
const reg = readJSON('ambient/registry/ambient.json');
const world = readJSON('world/registry/world.json');
const parishes = readJSON('parishes/registry/parishes.json');

/* ---------------------------------------------------------------- registry ---- */
{
  const h = createHash('sha256');
  for (const rel of reg.inputs) h.update(Buffer.concat([Buffer.from(rel), Buffer.from([0]), readFileSync(join(ROOT, rel)), Buffer.from([0])]));
  ok('source_stamp is sha256 of the declared inputs (ambient/build.py, authored, world.json, parishes.json)',
    h.digest('hex').slice(0, 16) === reg.source_stamp && reg.inputs.includes('ambient/build.py'));
  let fresh = true;
  try { execFileSync('python3', [join(ROOT, 'ambient/build.py'), '--check'], { stdio: 'pipe' }); } catch { fresh = false; }
  ok('ambient/build.py --check: registry is current', fresh);
}
const GENERIC = new Set(['dog', 'cat', 'squirrel', 'duck', 'rodent', 'pigeon', 'pelican', 'egret', 'gull', 'heron', 'sparrow']);
const BREEDS = /retriever|labrador|poodle|terrier|bulldog|shepherd|spaniel|beagle|husky|chihuahua|dachshund|siamese|persian|maine coon|tabby|calico|mallard|pekin|brand|®|™/i;
{
  const bad1 = Object.entries(reg.species).filter(([id, s]) => !GENERIC.has(id) || s.name.toLowerCase() !== id || BREEDS.test(s.name) || 'named' in s || 'breed' in s);
  ok('species list is generic: id in the generic list, name = the generic noun, no breed, no named animal',
    Object.keys(reg.species).length > 0 && bad1.length === 0, bad1.map(([id, s]) => id + ' -> ' + s.name));
  const drift = [];
  for (const [id, s] of Object.entries(reg.species)) {
    if (!s.reused_from) continue;
    const f = world.fauna[s.reused_from.split('#fauna.')[1]];
    for (const k of ['color', 'accent', 'span_m', 'body', 'motion', 'height_m', 'flock']) if (!f || JSON.stringify(f[k]) !== JSON.stringify(s[k])) drift.push(id + '.' + k);
  }
  ok('reused species copy their appearance from world/registry/world.json#fauna exactly', drift.length === 0, drift);
  ok('world fauna honesty carried verbatim; page_line says AUTHORED and never harmed',
    reg.world_fauna_honesty === world.honesty.fauna && /AUTHORED/.test(reg.honesty.page_line) && /(never harmed|no animal is ever harmed)/.test(reg.honesty.page_line));
}
{
  const lu = new Set();
  for (const f of parishes.selection.selected) for (const u of parishes.parishes[f].map.fabric_layers.land_use) lu.add(u);
  const dk = Object.keys(reg.densities_per_ha);
  ok('no density without a land use: densities_per_ha keys = the parish fabric land uses, both ways',
    dk.length === lu.size && dk.every((u) => lu.has(u)) && JSON.stringify([...reg.land_uses].sort()) === JSON.stringify([...lu].sort()),
    ['densities: ' + dk.join(','), 'parishes: ' + [...lu].join(',')]);
  const orphan = [];
  for (const [u, d] of Object.entries(reg.densities_per_ha)) for (const g of ['animals', 'flocks']) for (const sid of Object.keys(d[g])) {
    const want = g === 'animals' ? 'ground' : 'bird';
    if (!reg.species[sid] || reg.species[sid].kind !== want) orphan.push(u + '.' + g + '.' + sid);
  }
  ok('every density names a registry species of the right kind', orphan.length === 0, orphan);
}
{
  const w = reg.wind, R = w.ranges, out = [];
  const inR = (v, [lo, hi]) => typeof v === 'number' && v >= lo && v <= hi;
  if (!inR(w.speed_mps, R.speed_mps) || R.speed_mps[1] > 15) out.push('speed_mps');
  if (!inR(w.gust_gain, R.gust_gain) || R.gust_gain[1] > 1) out.push('gust_gain');
  if (!inR(w.gust_period_s, R.gust_period_s) || R.gust_period_s[0] < 1) out.push('gust_period_s');
  if (!inR(w.wavelength_m, R.wavelength_m) || R.wavelength_m[0] < 2) out.push('wavelength_m');
  for (const [k, v] of Object.entries(w.amplitude_m)) if (!inR(v, R.amplitude_m) || R.amplitude_m[1] > 0.5) out.push('amplitude_m.' + k);
  ok('wind params inside their ranges, and the ranges inside hard bounds (speed <= 15 m/s, sway <= 0.5 m)', out.length === 0, out);
}

/* ---------------------------------------------------------------- kit ---- */
let js = '';
try { js = execFileSync('python3', [join(ROOT, 'web/ambientkit.py'), '--emit'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }); } catch (e) { js = ''; }
ok('python3 web/ambientkit.py --emit prints the kit module (createAmbient exported)', /export \{ createAmbient/.test(js));
if (!js) { console.log(`ambient/test: ${bad + 1} FAILED, ${n} passed`); process.exit(1); }
const src = readFileSync(join(ROOT, 'web/ambientkit.py'), 'utf8') + readFileSync(join(ROOT, 'ambient/build.py'), 'utf8');
ok('fail closed: no ?? defaults and no .get(k, default) in the kit or the builder', !/\?\?/.test(src) && !/\.get\([^)]*,/.test(src));
ok('the kit fetches and loads nothing (no fetch, loader, URL or image)', !/fetch\(|Loader|https?:|\.png|\.jpg|\.webp|\.glb/.test(js));
const tmp = mkdtempSync(join(tmpdir(), 'amb-'));
writeFileSync(join(tmp, 'k.mjs'), js);
const K = await import(pathToFileURL(join(tmp, 'k.mjs')).href);
const THREE = await import(pathToFileURL(join(ROOT, 'web/vendor/three.module.min.js')).href);
rmSync(tmp, { recursive: true, force: true });

const B = reg.budgets, CH = 250;
const road = (x) => ((Math.floor(x / 25) % 4) + 4) % 4 === 0;            // a street every 4th 25 m column (the page's rule)
const isRoad = (x, z) => road(x) || road(z), isGround = (x, z) => z < 700;   // water north... z >= 700 is "not ground"
const mixed = (x, z) => reg.land_uses[(Math.floor(x / 400) + 2 * Math.floor(z / 400)) & 3];
{
  const a = K.scatterChunk(reg, 7, 1, -2, CH, mixed, isRoad, isGround), b = K.scatterChunk(reg, 7, 1, -2, CH, mixed, isRoad, isGround);
  const c = K.scatterChunk(reg, 8, 1, -2, CH, mixed, isRoad, isGround);
  ok('deterministic scatter: same (seed, chunk) gives identical scatter; another seed differs',
    JSON.stringify(a) === JSON.stringify(b) && JSON.stringify(a.grass) !== JSON.stringify(c.grass) && a.grass.length > 0);
  let onRoad = 0, offGround = 0, over = [];
  for (let i = -3; i <= 3; i++) for (let j = -3; j <= 3; j++) {
    const s = K.scatterChunk(reg, 7, i, j, CH, mixed, isRoad, isGround);
    for (const k of ['grass', 'bush', 'palm', 'litter']) {
      if (s[k].length > B.per_chunk[k]) over.push(i + ',' + j + ' ' + k);
      for (const [x, z] of s[k]) { if (isRoad(x, z)) onRoad++; if (!isGround(x, z)) offGround++; }
    }
    if (s.animals.length > B.per_chunk.animal) over.push(i + ',' + j + ' animal');
    if (s.flocks.length > B.per_chunk.flock) over.push(i + ',' + j + ' flock');
    for (const o of [...s.animals, ...s.flocks]) { if (isRoad(o.x, o.z)) onRoad++; if (!isGround(o.x, o.z)) offGround++; }
  }
  for (const u of reg.land_uses) {   // road-free, all-ground chunks: the densest AUTHORED density meets the cap here
    const s = K.scatterChunk(reg, 5, 0, 0, CH, u, () => false, () => true);
    for (const k of ['grass', 'bush', 'palm', 'litter']) if (s[k].length > B.per_chunk[k]) over.push(u + ' ' + k + ' ' + s[k].length);
  }
  ok('per-chunk instance budgets respected for every kind over 49 chunks and every land use', over.length === 0, over.slice(0, 5));
  ok('nothing scattered on a road or off the ground', onRoad === 0 && offGround === 0, ['on road ' + onRoad, 'off ground ' + offGround]);
  const all = () => false, yes = () => true, D = reg.densities_per_ha;
  const top = reg.land_uses.reduce((p, u) => (D[u].grass > D[p].grass ? u : p));
  const low = reg.land_uses.reduce((p, u) => (D[u].grass < D[p].grass ? u : p));
  const nt = K.scatterChunk(reg, 3, 0, 0, CH, top, all, yes).grass.length, nl = K.scatterChunk(reg, 3, 0, 0, CH, low, all, yes).grass.length;
  const expLow = D[low].grass * CH * CH / 10000;
  ok('densities drive the scatter: the densest land use fills its chunk cap, the sparsest is near its AUTHORED density',
    nt === Math.min(B.per_chunk.grass, Math.ceil(D[top].grass * 6.25)) && Math.abs(nl - expLow) <= Math.max(6, expLow * 0.4), [top + ' ' + nt, low + ' ' + nl + ' ~' + expLow]);
  let threw = '';
  try { K.scatterChunk(reg, 3, 0, 0, CH, 'wetland', all, yes); } catch (e) { threw = String(e.message); }
  ok('a land use with no AUTHORED density throws by name', /wetland/.test(threw) && /density/.test(threw), [threw]);
}
{
  const scene = new THREE.Scene(), before = scene.children.length;
  const amb = K.createAmbient(scene, { THREE, data: reg, seed: 11, chunkM: CH, isRoad, isGround });
  const added = scene.children.length - before;
  for (let i = -3; i <= 3; i++) for (let j = -3; j <= 3; j++) amb.onChunkLoad(i, j, 'park');
  const P = { x: 60, z: 60 };
  for (let k = 0; k < 30; k++) amb.update(1 / 30, P, []);
  const st = amb.stats(), capOver = Object.entries(st.instances).filter(([k, v]) => v > B.cap[k]);
  ok('draw calls added <= budgets.draw_calls_max (8): one InstancedMesh per kind, every species shares one',
    added === B.meshes.length && added <= B.draw_calls_max && st.drawCalls <= B.draw_calls_max && B.draw_calls_max <= 8, ['added ' + added, 'stats ' + st.drawCalls]);
  ok('global instance caps respected with 49 park chunks loaded', capOver.length === 0 && st.instances.grass > 0, capOver.map(String));
  const far = [];
  const m4 = new THREE.Matrix4(), v = new THREE.Vector3();
  for (const k of ['grass', 'bush', 'palm', 'litter']) {
    const m = amb.meshes[k];
    for (let i = 0; i < m.count; i++) { m.getMatrixAt(i, m4); v.setFromMatrixPosition(m4); if (Math.hypot(v.x - P.x, v.z - P.z) > B.lod_m[k] + 0.01) { far.push(k); break; } }
  }
  for (const a of amb.animals()) if (Math.hypot(a.x - P.x, a.z - P.z) > B.lod_m.animal + 50) far.push('animal');
  ok('LOD by distance: every drawn instance lies inside its kind\'s lod_m radius', far.length === 0, far);
  const ppl = amb.people(), cls = new Set(['pet', 'animal']);
  ok('people() hands PHYS every active animal as a circle with cls pet|animal (PHYS_PEDESTRIAN_CLASSES)',
    ppl.length === st.animalsActive && ppl.length > 0 && ppl.every((q) => cls.has(q.cls) && q.r > 0 && Number.isFinite(q.x)), [JSON.stringify(ppl[0])]);
  const g0 = st.instances.grass;
  amb.setOverview(true);
  amb.update(1, { x: 5000, z: 5000 }, []);
  const so = amb.stats();
  ok('overview: every ambient mesh hidden, zero draw calls, nothing refilled or stepped',
    so.drawCalls === 0 && Object.values(amb.meshes).every((m) => !m.visible) && so.instances.grass === g0);
  amb.setOverview(false);
  const names = new Set(scene.children.map((c) => c.name));
  amb.dispose();
  ok('dispose removes every ambient mesh from the scene', names.has('tc-ambient-grass') && scene.children.length === before);
}
{
  const beh = reg.behaviour, none = () => false, yes = () => true;
  const cat = { x: 3, z: 0, hx: 3, hz: 0 }, sp = reg.species.cat, d0 = 3;
  for (let k = 0; k < 30; k++) K.stepAnimal(cat, sp, beh, { x: 0, z: 0 }, [], 1 / 30, none, yes);
  ok('flee works: a cat inside flee_m runs away from the player at run speed',
    cat.mode === 'flee' && Math.hypot(cat.x, cat.z) > d0 + sp.run_mps * 0.8, [cat.mode + ' d=' + Math.hypot(cat.x, cat.z).toFixed(2)]);
  const dog = { x: 10, z: 0, hx: 10, hz: 0 }, dsp = reg.species.dog;
  for (let k = 0; k < 300; k++) K.stepAnimal(dog, dsp, beh, { x: 0, z: 0 }, [], 1 / 30, none, yes);
  const dd = Math.hypot(dog.x, dog.z);
  ok('follow works: a dog inside follow_m trails the player and stops at keep_m, never on top of them',
    dog.mode === 'follow' && dd <= dsp.keep_m + 0.3 && dd >= dsp.keep_m - 0.3, [dog.mode + ' d=' + dd.toFixed(2)]);
  const rd = (x) => Math.abs(x) < 4;   // a road along z at x in (-4, 4)
  const duck = { x: 0.5, z: 0, hx: 0.5, hz: 0 };
  for (let k = 0; k < 90; k++) K.stepAnimal(duck, reg.species.duck, beh, { x: 200, z: 0 }, [{ x: 0, z: 10 }], 1 / 30, (x) => rd(x), yes);
  ok('an animal on the road steps off it while a vehicle is within vehicle_alert_m', !rd(duck.x), ['x=' + duck.x.toFixed(2) + ' ' + duck.mode]);
  const sq = { x: 4.2, z: 0, hx: -30, hz: 0 }; let entered = 0;
  for (let k = 0; k < 600; k++) { K.stepAnimal(sq, reg.species.squirrel, beh, { x: 300, z: 0 }, [{ x: 0, z: 5 }], 1 / 30, (x) => rd(x), yes); if (rd(sq.x)) entered++; }
  ok('an animal never steps onto a road while a vehicle is near (home across the road, 20 s)', entered === 0, ['entered ' + entered]);
  const w0 = K.windAt(reg.wind, 0), w1 = K.windAt(reg.wind, 3.3);
  ok('one wind field: unit direction, strength bounded by (1 + gust_gain), same direction at every time',
    Math.abs(Math.hypot(w0.dx, w0.dz) - 1) < 1e-9 && [0.7, 3.3, 11, 60].every((s) => { const w = K.windAt(reg.wind, s); return w.dx === w0.dx && w.dz === w0.dz; }) && w0.strength > 0 && w1.strength <= 1 + reg.wind.gust_gain + 1e-9);
}

if (bad) { console.log(`ambient/test: ${bad} FAILED, ${n} passed`); process.exit(1); }
console.log(`ambient/test: ${n} checks passed - ${reg.counts.species} generic species, ${reg.counts.land_uses} land uses, `
  + `${B.meshes.length} meshes (<= ${B.draw_calls_max} draw calls)`);
