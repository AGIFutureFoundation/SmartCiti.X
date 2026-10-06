/**
 * florakit verification (web/florakit.py + flora/registry/flora.json), driven in node with the vendored THREE.
 * Synthetic AUTHORED world: water where z < 0, streets on x = 100 k (carriageway |dx| < 4 m), land use by x band.
 *
 *   node web/test_florakit.mjs
 *   node web/test_florakit.mjs --root=/tmp/copy      (mutation runs: a broken copy)
 */
import { readFileSync, writeFileSync, mkdtempSync, rmSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join, resolve, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const hit = process.argv.slice(2).find((a) => a.startsWith('--root='));
const ROOT = resolve(hit ? hit.slice(7) : join(HERE, '..'));
let n = 0, bad = 0;
const ok = (m, c, ev = []) => { if (c) { n++; console.log('  ok  ' + m); return; } bad++; console.log('FAIL  ' + m); for (const e of ev) console.log('      ' + e); };

let js = '';
try { js = execFileSync('python3', [join(ROOT, 'web/florakit.py'), '--emit'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }); } catch { js = ''; }
ok('[kit] python3 web/florakit.py --emit prints the module (createFlora exported)', /export \{ createFlora/.test(js));
ok('[kit] no `??` fallbacks in the kit source', !js.includes('??'));
const tmp = mkdtempSync(join(tmpdir(), 'flora-'));
writeFileSync(join(tmp, 'k.mjs'), js);
const K = await import(pathToFileURL(join(tmp, 'k.mjs')).href);
const THREE = await import(pathToFileURL(join(ROOT, 'web/vendor/three.module.min.js')).href);
rmSync(tmp, { recursive: true, force: true });
const reg = JSON.parse(readFileSync(join(ROOT, 'flora/registry/flora.json'), 'utf8'));

const region = (r) => ({ ...reg, regions: { [r]: reg.regions[r] }, species: Object.fromEntries(Object.entries(reg.species).filter(([, s]) => s.region === r)) });
const LUX = (x) => { const b = Math.floor(x / 200); return ['residential', 'commercial', 'park', 'industrial'][((b % 4) + 4) % 4]; };
const world = (over = {}) => ({ THREE, seed: 20260929, chunkM: 250, isGround: (x, z) => z >= 0, isWater: (x, z) => z < 0,
  isRoad: (x, z) => { const d = ((x % 100) + 100) % 100; return d < 4 || d > 96; }, landUse: LUX, groundY: () => 0, landClass: () => null, ...over });
const mk = (r, over) => { const scene = new THREE.Scene(); return { scene, fl: K.createFlora(scene, { ...world(over), data: region(r), region: r }) }; };

/* ------------------------------------------------------------------ meshes, budgets ---- */
{
  const { scene, fl } = mk('louisiana');
  const ims = scene.children.filter((o) => o.isInstancedMesh);
  ok('[budget] one InstancedMesh per registry family, <= budgets.draw_calls_max', ims.length === Object.keys(reg.families).length && ims.length <= reg.budgets.draw_calls_max, [`meshes ${ims.length}`]);
  ok('[budget] two shared materials for every family (solid + double-sided)', new Set(ims.map((m) => m.material)).size === 2);
  const trisOk = ims.every((m) => m.geometry.attributes.position.count / 3 === reg.families[m.userData.flora].tris);
  ok('[budget] each family geometry has exactly the registry triangle count', trisOk);
  ok('[budget] worst case sum(cap x tris) <= budgets.tris_max', Object.values(reg.families).reduce((a, f) => a + f.cap * f.tris, 0) <= reg.budgets.tris_max);
  for (let i = 0; i < 40; i++) fl.update({ x: 500, z: 40 });
  const st = fl.stats();
  const side = 2 * Math.ceil(Math.max(...Object.values(reg.families).map((f) => f.lod_m)) / 250) + 1;
  ok('[stream] chunks stream in around the player (all (2R+1)^2 loaded, queue empty)', st.chunks === side * side && st.queue === 0, [JSON.stringify(st)]);
  ok('[lod] every family count <= its cap and total tris <= tris_max', Object.entries(st.families).every(([f, c]) => c <= reg.families[f].cap) && st.tris <= reg.budgets.tris_max, [JSON.stringify(st.families)]);
  const far = fl.near(500, 40, 1e6).filter((it) => Math.hypot(it.x - 500, it.z - 40) > reg.families[it.f].lod_m);
  ok('[lod] no drawn instance lies beyond its family lod_m', far.length === 0, [String(far.length)]);
  ok('[place] families present in a Louisiana walk: broadleaf, reed, detail', st.families.broadleaf > 0 && st.families.reed > 0 && st.families.detail > 0, [JSON.stringify(st.families)]);
  ok('[place] every drawn plant is a Louisiana species', Object.keys(st.species).every((s) => s === 'spanish_moss' || reg.details[s] || reg.species[s].region === 'louisiana'), [Object.keys(st.species).join(',')]);
  ok('[cull] a family with instances has a bounding sphere (frustum culling on)', ims.filter((m) => m.count).every((m) => m.boundingSphere && m.frustumCulled));
  const drawn = fl.near(500, 40, 1e6);
  const shore = drawn.filter((it) => it.f !== 'detail' && it.z < reg.budgets.shore_m * 0.5);
  const shoreSp = new Set(shore.filter((it) => it.f !== 'moss').map((it) => it.sp));
  const allowed = new Set(Object.keys(reg.regions.louisiana.rules[0].mix));
  ok('[rules] plants within half shore_m of the water are the shoreline mix (marsh grass, cattail, bald cypress)', shore.length > 0 && [...shoreSp].every((s) => allowed.has(s)), [[...shoreSp].join(',')]);
  const moss = drawn.filter((it) => it.f === 'moss');
  ok('[rules] Spanish moss hangs only on a live oak near water', moss.length > 0 && moss.every((m) => fl.waterClass(m.x, m.z) !== 'far' && drawn.some((t) => t.sp === 'live_oak' && t.x === m.x && t.z === m.z)), [String(moss.length)]);
  const dets = drawn.filter((it) => it.f === 'detail');
  ok('[details] street details stand off the carriageway (>= 3.5 m from the street line), within the kerb band', dets.length > 0 && dets.every((d) => { const dd = ((d.x % 100) + 100) % 100; const e = Math.min(dd, 100 - dd); return e >= 3.5 && e <= reg.budgets.kerb_probe_m + 3 + 3.2; }), [String(dets.length)]);
  const plants = drawn.filter((it) => it.f !== 'detail' && it.f !== 'moss');
  ok('[place] no plant stands in water or on the carriageway', plants.every((p) => p.z >= 0 && (((p.x % 100) + 100) % 100 >= 4) && (((p.x % 100) + 100) % 100 <= 96)));
  ok('[place] heights and crowns lie inside the registry ranges', plants.every((p) => { const s = reg.species[p.sp]; return p.sy >= s.height_m[0] && p.sy <= s.height_m[1] && p.sx >= s.crown_m[0] && p.sx <= s.crown_m[1]; }));
  fl.setOverview(true);
  ok('[overview] setOverview(true): 0 draw calls, every flora mesh hidden', fl.stats().drawCalls === 0 && ims.every((m) => !m.visible));
  fl.setOverview(false);
  ok('[overview] back to the walk view: families visible again', fl.stats().drawCalls > 0);
  fl.setEnabled(false); fl.update({ x: 900, z: 900 });
  ok('[enable] setEnabled(false): 0 draw calls and no streaming (eval A/B)', fl.stats().drawCalls === 0 && fl.stats().chunks === side * side);
  fl.setEnabled(true);
  ok('[enable] setEnabled(true): families visible again', fl.stats().drawCalls > 0);
  fl.dispose();
  ok('[dispose] dispose() removes every flora mesh from the scene', !scene.children.some((o) => o.isInstancedMesh));
}
/* ------------------------------------------------------------------ determinism, ground ---- */
{
  const a = mk('louisiana').fl.placeChunk(0, 0), b = mk('louisiana').fl.placeChunk(0, 0), c = mk('louisiana', { seed: 7 }).fl.placeChunk(0, 0);
  ok('[seed] placeChunk is deterministic for (seed, ci, cj)', JSON.stringify(a) === JSON.stringify(b) && a.length > 0);
  ok('[seed] a different seed places differently', JSON.stringify(a) !== JSON.stringify(c));
  const g = mk('louisiana', { groundY: (x, z) => 2 + x * 0.001 }).fl.placeChunk(0, 0).filter((it) => it.f !== 'detail');
  ok('[ground] plants stand on groundY(x, z) (terrain hook)', g.length > 0 && g.every((it) => Math.abs(it.y - (2 + it.x * 0.001)) < 1e-9));
}
/* ------------------------------------------------------------------ RECORDED land cover ---- */
{
  const wet = mk('louisiana', { landClass: () => 90 }).fl.placeChunk(0, 0).filter((it) => it.f !== 'detail');
  const m90 = reg.regions.louisiana.landcover['90'].mix;
  ok('[landcover] class 90 (herbaceous wetland) places only its RECORDED mix (+ moss), marked src R', wet.length > 0 && wet.every((it) => it.src === 'R' && (m90[it.sp] || it.f === 'moss')), [String(wet.length)]);
  const water = mk('louisiana', { landClass: () => 80 }).fl.placeChunk(0, 0).filter((it) => it.f !== 'detail');
  ok('[landcover] class 80 (water) and 50 (built-up) place no plants', water.length === 0 && mk('louisiana', { landClass: () => 50 }).fl.placeChunk(0, 0).filter((it) => it.f !== 'detail').length === 0);
  const half = mk('louisiana', { landClass: (x) => (x < 125 ? 10 : null) }); for (let i = 0; i < 40; i++) half.fl.update({ x: 125, z: 60 });
  const lc = half.fl.stats().landcover;
  ok('[landcover] null class -> AUTHORED rules, counted; stats share of plants from RECORDED classes', lc.plantsRecorded > 0 && lc.plantsAuthored > 0 && lc.authoredSamples > 0 && lc.recordedSamples > 0 && lc.shareRecorded > 0 && lc.shareRecorded < 1, [JSON.stringify(lc)]);
  let e5 = ''; try { mk('louisiana', { landClass: () => 77 }).fl.placeChunk(0, 0); } catch (e) { e5 = String(e.message); }
  ok('[landcover] an unknown class code throws naming it', /77/.test(e5));
  half.fl.reset(); ok('[landcover] reset() drops the placed chunks (re-place when the grid arrives)', half.fl.stats().chunks === 0);
}
/* ------------------------------------------------------------------ regions ---- */
{
  const { fl } = mk('bay'); for (let i = 0; i < 40; i++) fl.update({ x: 30, z: 60 });
  const sp = Object.keys(fl.stats().species).filter((s) => !reg.details[s]);
  ok('[region] the Bay kit places only Bay species (no live oak / moss)', sp.length > 0 && sp.every((s) => reg.species[s].region === 'bay'), [sp.join(',')]);
  const redw = fl.near(30, 60, 1e6).filter((it) => it.sp === 'redwood');
  ok('[region] Bay redwoods stand only in park land away from water (AUTHORED canyon stand-in)', redw.every((r) => LUX(r.x) === 'park' && fl.waterClass(r.x, r.z) === 'far'), [String(redw.length)]);
  const sm = mk('smiles', { landUse: () => 'school' }).fl.placeChunk(0, 0).filter((it) => it.f !== 'detail');
  ok('[region] Smiles school land gets schoolyard trees and hedges only', sm.length > 0 && sm.every((it) => ['school_tree', 'hedge'].includes(it.sp)));
}
/* ------------------------------------------------------------------ fail closed ---- */
{
  let e1 = ''; try { mk('louisiana', { landUse: () => 'swamp' }).fl.placeChunk(0, 0); } catch (e) { e1 = String(e.message); }
  ok('[fail] an unknown land use throws FloraError naming it', /swamp.*not a louisiana land use/.test(e1), [e1]);
  let e2 = ''; try { K.createFlora(new THREE.Scene(), { ...world(), data: region('louisiana'), region: 'louisiana', isWater: undefined }); } catch (e) { e2 = String(e.message); }
  ok('[fail] a missing adapter throws naming it (isWater)', /isWater/.test(e2));
  let e3 = ''; try { K.createFlora(new THREE.Scene(), { ...world(), data: region('louisiana'), region: 'mars' }); } catch (e) { e3 = String(e.message); }
  ok('[fail] an unknown region throws naming it', /mars/.test(e3));
  let py = '';
  try { py = execFileSync('python3', ['-c', 'import sys; sys.path.insert(0, "web"); import florakit; florakit.flora_data("mars")'], { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }); } catch (e) { py = String(e.stderr); }
  ok('[fail] flora_data(unknown region) raises FloraKitError by name', /FloraKitError.*mars/.test(py));
}
/* ------------------------------------------------------------------ pages ---- */
for (const [page, region] of [['web/trade_craft_parishes.html', 'louisiana'], ['web/trade_craft_bay.html', 'bay'], ['web/trade_craft_smiles.html', 'smiles']]) {
  let h = ''; try { h = readFileSync(join(ROOT, page), 'utf8'); } catch { h = ''; }
  ok(`[page] ${page}: flora mounted for region ${region} with the registry stamp and the honesty line`,
    h.includes(`region: "${region}"`) && h.includes(reg.source_stamp) && h.includes(reg.honesty.page_line));
}
for (const [page, grid] of [['web/trade_craft_parishes.html', 'parishes'], ['web/trade_craft_bay.html', 'bayarea']]) {
  let h = ''; try { h = readFileSync(join(ROOT, page), 'utf8'); } catch { h = ''; }
  const lc = JSON.parse(readFileSync(join(ROOT, 'landcover/registry/landcover.json'), 'utf8'));
  ok(`[landcover] ${page}: fetches landcover/vendor/${grid}.u8.gz pinned to the registry sha256, landClass wired, WorldCover attribution + modification note on the legend`,
    h.includes(`"path": "landcover/vendor/${lc.grids[grid].file}"`) && h.includes(`"sha256": "${lc.grids[grid].sha256}"`) && h.includes('landClass: floraClass') && h.includes(lc.attribution.text) && h.includes('modified: ' + lc.attribution.changes) && h.includes('CC BY 4.0'));
}
/* ------------------------------------------------------------------ ENV w15: footprint adapters + stub-vehicle root cause ---- */
{
  // kit: a footprint adapter drops every sample inside a building, nothing drawn stands in it, draw-call shape unchanged
  const box = (x, z) => x >= 20 && x <= 180 && z >= 20 && z <= 180;
  const off = mk('louisiana'), on = mk('louisiana', { footprint: box, chunkReady: () => true });
  for (let i = 0; i < 40; i++) { off.fl.update({ x: 100, z: 100 }); on.fl.update({ x: 100, z: 100 }); }
  const inOff = off.fl.near(100, 100, 1e6).filter((it) => box(it.x, it.z)).length, inOn = on.fl.near(100, 100, 1e6).filter((it) => box(it.x, it.z)).length;
  const fs = on.fl.stats().footprint, ims = (sc) => sc.children.filter((o) => o.isInstancedMesh).length;
  ok('[env] footprint adapter: no flora item stands inside a footprint (counted in stats().footprint), same InstancedMesh set',
    inOff > 0 && inOn === 0 && fs && fs.adapter && fs.skipped > 0 && fs.checked >= fs.skipped && ims(on.scene) === ims(off.scene) && off.fl.stats().footprint === null, [JSON.stringify({ inOff, inOn, fs })]);
  // kit: chunkReady false holds every chunk in the queue (deferred), true lets them place
  let ready = false; const g = mk('louisiana', { footprint: () => false, chunkReady: () => ready });
  for (let i = 0; i < 10; i++) g.fl.update({ x: 100, z: 100 });
  const held = g.fl.stats(); ready = true; for (let i = 0; i < 40; i++) g.fl.update({ x: 100, z: 100 });
  ok('[env] chunkReady false holds flora chunks back (deferred, none placed) until the page has built them',
    held.chunks === 0 && held.footprint.deferred > 0 && g.fl.stats().chunks > 0, [JSON.stringify({ held: held.footprint, chunks: held.chunks, after: g.fl.stats().chunks })]);
  let e4 = ''; try { mk('louisiana', { footprint: 'yes' }); } catch (e) { e4 = String(e.message); }
  ok('[env] a non-function footprint adapter throws FloraError naming it', /footprint must be a function/.test(e4), [e4]);
  let py2 = '';
  try { py2 = execFileSync('python3', ['-c', 'import sys; sys.path.insert(0, "web"); import florakit as f; f.flora_mount_js("louisiana", seed="S", chunk_m="C", is_ground="g", is_road="r", is_water="w", land_use="l", eye="e", overview="o", footprint="fp")'], { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }); } catch (e) { py2 = String(e.stderr); }
  ok('[env] flora_mount_js refuses a footprint without the chunk_ready gate (FloraKitError by name)', /FloraKitError.*chunk_ready/.test(py2), [py2.slice(-200)]);
}
for (const page of ['web/trade_craft_parishes.html', 'web/trade_craft_bay.html']) {
  let h = ''; try { h = readFileSync(join(ROOT, page), 'utf8'); } catch { h = ''; }
  // page adapters, run as written in the page against a rotated building in a NEIGHBOUR chunk that reaches across the edge
  const a = h.indexOf('/* ENV w15 flora footprint adapters'), b = h.indexOf('let envBoardings = 0;');
  let fx = null; try { fx = new Function('chunkData', 'CHUNK_M', h.slice(a, b) + '\nreturn { envFootprint, envChunkReady };'); } catch { fx = null; }
  let r = { wired: h.includes('landClass: floraClass, footprint: envFootprint, chunkReady: envChunkReady') };
  if (a > 0 && b > a && fx) {
    const cd = new Map(); for (let i = -1; i <= 1; i++) for (let j = -1; j <= 1; j++) if (!(i === 1 && j === 1)) cd.set(i + ',' + j, { block: [] });
    cd.get('0,0').block.push([248, 125, 40, 9, 10, 'midrise', Math.PI / 2]);   // centred in chunk 0,0, turned 90 deg: 40 m along world z, 10 m along x (x 243..253 reaches into chunk 1,0)
    const F = fx(cd, 250);
    r = { ...r, inNb: F.envFootprint(252, 140), outAlong: F.envFootprint(252, 146), inPad: F.envFootprint(253.3, 125), outPad: F.envFootprint(253.7, 125), readyMissing: F.envChunkReady(0, 0) };
    cd.set('1,1', { block: [] }); r.readyAll = F.envChunkReady(0, 0);
  }
  ok(`[env] ${page}: flora footprint adapters wired; a rotated building centred next door excludes its whole footprint (+0.5 m pad); a chunk waits for its 3x3 page chunks`,
    r.wired && r.inNb === true && r.outAlong === false && r.inPad === true && r.outPad === false && r.readyMissing === false && r.readyAll === true, [JSON.stringify(r)]);
  // goal 1 root cause: setMode('drive'|'boat') toasted the stub-vehicle line unconditionally although FLEETREG is embedded
  const s0 = h.indexOf('function setMode(m) {'), s1 = s0 < 0 ? -1 : h.indexOf('\n}\n', s0);
  const reg = h.match(/<script type="application\/json" id="fleet-registry">(\{.{0,40})/);
  const run = (m, fleet) => {
    const toasts = [], ctx = { riding: null, mode: 'walk', eye: { x: 0, z: 0 }, toasts, toast: (t) => toasts.push(t), tr: (k) => k, applyMode: (q) => { ctx.mode = q; },
      nearest: () => null, FLEETREG: fleet ? { fleet: [] } : null, envBoardings: 0, entered: 0,
      parked: [{ medium: 'land', st: { x: 30, z: 40 } }, { medium: 'water', st: { x: -300, z: 10 } }] };
    ctx.enterExit = () => { ctx.entered++; ctx.mode = ctx.eye.x === -300 ? 'boat' : 'drive'; return true; };
    const f = new Function('ctx', 'with (ctx) { ' + h.slice(s0, s1 + 2) + ' return setMode; }')(ctx);
    return { ret: f(m), toasts, entered: ctx.entered, mode: ctx.mode, at: [ctx.eye.x, ctx.eye.z] };
  };
  let d = null; try { d = s0 > 0 && s1 > s0 ? { drive: run('drive', true), boat: run('boat', true), stub: run('drive', false) } : null; } catch (e) { d = { err: String(e.message) }; }
  ok(`[env] ${page}: with the fleet registry embedded, setMode('drive'|'boat') boards the nearest parked vehicle of that medium and never shows the stub-vehicle line (only a null registry does)`,
    !!reg && !!d && !d.err && d.drive.ret === true && d.drive.entered === 1 && d.drive.at.join() === '30,40' && !d.drive.toasts.includes('parishes.stub_vehicle')
      && d.boat.entered === 1 && d.boat.at.join() === '-300,10' && !d.boat.toasts.includes('parishes.stub_vehicle')
      && d.stub.entered === 0 && d.stub.toasts.includes('parishes.stub_vehicle'), [JSON.stringify(d)]);
}
console.log(`\n${n} checks passed, ${bad} failed`);
process.exit(bad ? 1 : 0);
