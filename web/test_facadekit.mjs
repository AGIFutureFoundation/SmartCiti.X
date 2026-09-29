/* web/test_facadekit.mjs - the facade kit, checked in node with the vendored three.js (no browser, no network).
 * One InstancedMesh (one draw call) whatever it shows; the box budget holds; every style dresses a building;
 * signs sit on their lots with the atlas cell on the board's face; the colour adapter falls back to the
 * AUTHORED flat colour; sign palettes pass WCAG AA by design_kit's own contrast function; the pages mount it. */
import { readFileSync, writeFileSync, mkdtempSync, existsSync, rmSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { dirname, join } from 'node:path';
import { tmpdir } from 'node:os';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m); } };
console.log('web/test_facadekit.mjs');

const THREE = await import(pathToFileURL(join(HERE, 'vendor/three.module.min.js')).href);
const src = execFileSync('python3', [join(HERE, 'facadekit.py'), '--emit'], { encoding: 'utf8' });
const dir = mkdtempSync(join(tmpdir(), 'facadekit-'));
writeFileSync(join(dir, 'facadekit.mjs'), src);
const K = await import(pathToFileURL(join(dir, 'facadekit.mjs')).href);
const D = JSON.parse(readFileSync(join(ROOT, 'facades/registry/facades.json'), 'utf8'));

ok(!src.includes('??') && !/\.get\([^)]*,/.test(src), 'fail closed: no ?? default and no .get(k, default) in the kit');
const scene = new THREE.Scene();
const mk = (o = {}) => K.createFacades(scene, { THREE, data: D, world: 'parishes', maxBoxes: 1500, radius: 90, makeCanvas: () => null, sink: false, signNear: 45, ...o });
const f = mk();
ok(scene.children.length === 1 && scene.children[0].isInstancedMesh, 'draw calls: the kit adds exactly ONE InstancedMesh to the scene');
ok(f.stats().trisPerPart === 8, `triangles: one part = ${f.stats().trisPerPart} triangles (box without its bottom and back faces)`);

/* a street of kit buildings, [x, z, w, h, d, family, yaw, colour, use] */
const B = [];
for (let i = 0; i < 60; i++) {
  const fam = i % 3 === 0 ? 'house' : 'midrise', use = fam === 'house' ? (i % 2 ? 0.25 : 0) : [1, 1.25, 2, 2.25][i % 4];
  B.push([i * 14, (i % 5) * 20, 10 + (i % 4), fam === 'house' ? 4.5 + (i % 3) : 7 + (i % 7) * 4, 12, fam, (i % 4) * Math.PI / 2, 0xffffff, use]);
}
const st = f.update(B, [], { x: 0, z: 0 });
ok(st.dressed > 0 && st.parts === f.mesh.count && st.parts <= 1500, `update: ${st.dressed} buildings dressed with ${st.parts} parts (<= budget 1500)`);
ok(st.unstyled === 0, 'rules: every kit building near the eye found a style');
const allX = []; for (let i = 0; i < f.mesh.count; i++) { const m = new THREE.Matrix4(); f.mesh.getMatrixAt(i, m); allX.push(...m.elements); }
ok(allX.every(Number.isFinite), 'update: every part matrix is finite');
ok(f.drawCalls() === 1, 'draw calls: 1 while shown');
f.setVisible(false); ok(f.drawCalls() === 0, 'overview: hidden -> 0 draw calls'); f.setVisible(true);
const small = mk({ maxBoxes: 40 }); const s2 = small.update(B, [], { x: 0, z: 0 });
ok(s2.parts <= 40 && s2.dropped > 0, `budget: a 40-part budget holds (${s2.parts}) and counts ${s2.dropped} buildings dropped`);
const far = f.update(B, [], { x: 99999, z: 0 });
ok(far.parts === 0, 'radius: nothing is dressed beyond the radius');

for (const sid of Object.keys(D.styles)) {
  const bx = K.facBoxes(D, sid, 12, 12, 14);
  ok(bx.length >= 3 && bx.every((b) => b.slice(0, 6).every(Number.isFinite) && b[3] > 0 && b[4] > 0 && b[5] > 0), `recipe ${sid}: ${bx.length} parts on a 12 x 12 x 14 m building, all positive sizes`);
}
ok(K.facBoxes(D, 'italianate-row', 10, 5, 10).every((b) => b[1] + b[4] / 2 <= 5 + 1.5 + 1e-6), 'recipe: ground parts never rise above a low wall (only eave parts sit on it)');
let threw = ''; try { K.facBoxes(D, 'no-such-style', 10, 5, 10); } catch (e) { threw = e.message; }
ok(/missing "no-such-style"/.test(threw), 'fail closed: an unknown style stops by name');
threw = ''; try { mk({ world: 'mars' }); } catch (e) { threw = e.message; }
ok(/unknown world/.test(threw), 'fail closed: an unknown world stops by name');
ok(K.facStyleFor(D, 'bay', 'house', 0, 5) === 'craftsman-bungalow' && K.facStyleFor(D, 'parishes', 'house', 0, 5) === 'creole-cottage', 'rules: the Bay and the parishes dress houses differently');
ok(K.facStyleFor(D, 'parishes', 'midrise', 2, 9) === 'brick-warehouse' && K.facStyleFor(D, 'parishes', 'midrise', 1, 40) === 'modern-glass', 'rules: industrial -> brick warehouse, tall commercial -> modern glass');

/* sink mode (the parish/Bay pages): parts go into the host's merged vertex-coloured buffer - 0 draw calls of their own */
{
  const sc = new THREE.Scene(), g = K.createFacades(sc, { THREE, data: D, world: 'parishes', maxBoxes: 400, radius: 90, makeCanvas: () => null, sink: true, signNear: 45 });
  const s1 = g.update(B, [], { x: 0, z: 0 });
  const cap = 400 * 24, pos = new Float32Array(cap * 3), nor = new Float32Array(cap * 3), col = new Float32Array(cap * 3), zeb = new Float32Array(cap).fill(7);
  const nv = g.writeInto(pos, nor, col, zeb, 10, cap);
  ok(s1.parts > 0 && nv === s1.parts * 24 && g.mesh.count === 0 && g.drawCalls() === 0, `sink: ${s1.parts} parts -> ${nv / 3} triangles in the host buffer, the kit mesh draws nothing (0 calls)`);
  ok(zeb.slice(10, 10 + nv).every((z) => z === -100) && zeb[9] === 7 && [...pos.slice(30, 30 + nv * 3)].every(Number.isFinite), 'sink: writes start at the given base, finite, zebra attribute cleared to -100');
  ok(g.writeInto(pos, nor, col, zeb, cap - 10, cap) === 0 && g.stats().dropped > 0, 'sink: a full host buffer drops parts (counted) instead of overrunning');
  const shops0 = g.signsFor(D.signs[0].parish).map((s) => ({ sign: s, x: s.x, z: s.z, yaw: 0 }));
  g.update([], shops0, { x: shops0[0].x + 30, z: shops0[0].z });
  ok(g.mesh.count >= 1 && g.drawCalls() === 1, 'sink: a play sign within 45 m draws its textured board (1 call)');
  const sF = g.update([], shops0, { x: shops0[0].x + 120, z: shops0[0].z });
  ok(sF.signs >= 1 && g.mesh.count === 0 && g.drawCalls() === 0, 'sink: a shop placed 120 m away but no play sign within 45 m -> 0 draw calls');
  g.update(B, [], { x: 0, z: 0 }); ok(g.writeInto(pos, nor, col, zeb, 0, cap) > 0, 'sink: enabled writes the parts');
  g.setEnabled(false); ok(g.writeInto(pos, nor, col, zeb, 0, cap) === 0, 'sink: disabled writes nothing (the eval before/after switch)');
}
/* signs */
const byPl = {};
for (const s of D.signs) { const bx = K.facShopBoxes(D, s, 5); byPl[s.placement] = bx; }
for (const pl of ['fascia', 'blade', 'window', 'monument']) {
  const bx = byPl[pl];
  ok(bx && bx.some((b) => b[8] === 5 && b[6] === null), `sign ${pl}: a board carries the atlas cell and no tint`);
}
ok(byPl.blade.some((b) => b[8] === 5 && Math.abs(b[9] - Math.PI / 2) < 1e-9), 'sign blade: the board turns 90 degrees to face along the street');
const parish = D.signs[0].parish, shops = f.signsFor(parish).map((s) => ({ sign: s, x: s.x, z: s.z, yaw: 0 }));
const st3 = f.update([], shops, { x: shops[0].x, z: shops[0].z });
ok(st3.signs >= 1 && st3.signs <= shops.length, `signs: ${st3.signs} play signs placed on parish ${parish}'s lots`);
ok(f.signsFor('06075').length === 0, 'signs: a place with no economy lots gets no signs (the Bay has none)');

/* colour adapter */
const flat = K.facadeColour(D, 'ironwork', 'plain');
ok(flat === D.colour_categories.ironwork.hex, 'colour adapter: no PATTERN module -> the AUTHORED flat colour');
K.setColourAdapter((cat) => (cat === 'ironwork' ? '#123456' : null));
ok(K.facadeColour(D, 'ironwork', 'plain') === '#123456' && K.facadeColour(D, 'brick-red', 'plain') === D.colour_categories['brick-red'].hex, 'colour adapter: PATTERN answer used, a non-answer falls back');
K.setColourAdapter(null);
threw = ''; try { K.facadeColour(D, 'no-colour', 'plain'); } catch (e) { threw = e.message; }
ok(/missing "no-colour"/.test(threw), 'colour adapter: an unknown category stops by name');

/* PATTERN_CONTRACT v1: the real PatternKit through the one adapter */
const pkSrc = execFileSync('python3', ['-c', `import sys; sys.path.insert(0, ${JSON.stringify(HERE)}); import patternkit as PK; sys.stdout.write(PK.es_module([], ${JSON.stringify(D.pattern_families)}))`], { encoding: 'utf8' });
writeFileSync(join(dir, 'patternkit.mjs'), pkSrc);
const PK = (await import(pathToFileURL(join(dir, 'patternkit.mjs')).href)).default;
K.setColourAdapter(K.facPatternAdapter(D, PK));
ok(Object.entries(D.pattern_map).every(([cat, id]) => K.facadeColour(D, cat, 'plain').toUpperCase() === (id === null ? D.colour_categories[cat].hex : PK.colour(id)).toUpperCase()),
   'pattern adapter: every category draws PatternKit\'s colour (a null mapping keeps the AUTHORED flat colour)');
K.setColourAdapter(null);
/* WCAG AA for every sign palette, by design_kit's own contrast() */
const pals = JSON.stringify(D.sign_rules.palettes);
const ratios = JSON.parse(execFileSync('python3', ['-c', `import sys,json; sys.path.insert(0, ${JSON.stringify(HERE)}); from design_kit import contrast; print(json.dumps([round(contrast(t, b), 2) for b, t in json.loads(sys.argv[1])]))`, pals], { encoding: 'utf8' }));
ok(ratios.every((r) => r >= 4.5), `signs: every palette passes WCAG AA text contrast (design_kit.contrast): ${ratios.join(', ')}`);

/* the pages mount it */
for (const [page, world] of [['trade_craft_parishes.html', 'parishes'], ['trade_craft_bay.html', 'bay']]) {
  const p = join(HERE, page), h = existsSync(p) ? readFileSync(p, 'utf8') : '';
  ok(h.includes("customProgramCacheKey = () => 'tc-facade'") && h.includes('const FAC_WORLD = "' + world + '"'), `mount: ${page} carries the facade kit for world ${world}`);
  ok(h.includes('setColourAdapter(facPatternAdapter(FAC_DATA, PatternKit))') && (h.match(/const PatternKit\b/g) || []).length === 1, `pattern: ${page} wires PatternKit colours through the adapter, PatternKit inlined once`);
  ok(h.includes('sink: true') && h.includes('FAC.writeInto(roadPos, roadNor, roadCol, roadZeb, facBase'), `draw calls: ${page} writes facade parts into the street mesh buffer (0 calls of their own)`);
  ok(h.includes('window.__facades = FAC;'), `mount: ${page} exposes window.__facades for the eval`);
  ok(h.includes('<li data-legend="facades" lang="en">') && h.includes(D.honesty.signs.replace(/'/g, '&#x27;').split(' - ')[0].slice(0, 30)), `legend: ${page} quotes the facades honesty line (signs are play)`);
}
rmSync(dir, { recursive: true, force: true });
console.log(`facadekit: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
