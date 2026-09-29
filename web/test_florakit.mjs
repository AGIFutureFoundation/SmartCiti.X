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
console.log(`\n${n} checks passed, ${bad} failed`);
process.exit(bad ? 1 : 0);
