// web/test_terrainkit.mjs - node checks for web/terrainkit.py (ground relief sampler, lattice, patch, adapters).
// Prints "  ok <name>" per check, "FAIL <name>" at column 0 on failure, exits non-zero on any failure.
import { execFileSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const dir = mkdtempSync(join(tmpdir(), 'terrainkit-'));
const mod = join(dir, 'terrain.mjs');
execFileSync('python3', [join(HERE, 'terrainkit.py'), '--out', mod]);
const T = await import(pathToFileURL(mod).href);
let fails = 0;
const check = (name, cond, info) => { if (cond) console.log('  ok ' + name); else { fails++; console.log('FAIL ' + name + (info !== undefined ? ' - ' + JSON.stringify(info) : '')); } };
const throwsLike = (f, re) => { try { f(); return false; } catch (e) { return re.test(e.message); } };

// [grid] RECORDED bilinear
const g = T.terrainGrid({ provenance: 'RECORDED', units: 'm', source: 'test grid', x0: 0, z0: 0, dx: 10, dz: 10, cols: 3, rows: 2, heights: [0, 10, 20, 5, 15, 25] });
check('[grid] corners reproduce the grid', g.height(0, 0) === 0 && g.height(20, 0) === 20 && g.height(20, 10) === 25 && g.height(0, 10) === 5);
check('[grid] bilinear midpoint', Math.abs(g.height(5, 5) - 7.5) < 1e-9, g.height(5, 5));
check('[grid] outside the extent is null (never extrapolated)', g.height(-1, 0) === null && g.height(0, 11) === null);
check('[grid] provenance RECORDED + source', g.provenance === 'RECORDED' && g.source === 'test grid');
check('[grid] AUTHORED data refused as a RECORDED grid', throwsLike(() => T.terrainGrid({ provenance: 'AUTHORED', units: 'm', source: 's', x0: 0, z0: 0, dx: 1, dz: 1, cols: 2, rows: 2, heights: [0, 0, 0, 0] }), /must be RECORDED/));
check('[grid] missing field throws by name', throwsLike(() => T.terrainGrid({ provenance: 'RECORDED', units: 'm', source: 's', x0: 0, z0: 0, dx: 1, cols: 2, rows: 2, heights: [0, 0, 0, 0] }), /grid has no dz/));
check('[grid] wrong heights length throws', throwsLike(() => T.terrainGrid({ provenance: 'RECORDED', units: 'm', source: 's', x0: 0, z0: 0, dx: 1, dz: 1, cols: 2, rows: 2, heights: [0, 0, 0] }), /heights length/));
check('[grid] a NaN height throws', throwsLike(() => T.terrainGrid({ provenance: 'RECORDED', units: 'm', source: 's', x0: 0, z0: 0, dx: 1, dz: 1, cols: 2, rows: 2, heights: [0, NaN, 0, 0] }), /not finite/));

// [authored] knolls and levees
check('[authored] knoll peak / edge / outside', T.terrainKnoll(0, 50, 2) === 2 && Math.abs(T.terrainKnoll(25, 50, 2) - 1) < 1e-9 && T.terrainKnoll(50, 50, 2) === 0 && T.terrainKnoll(80, 50, 2) === 0);
const LV = { toe0: 3, crest: 18, toe1: 45, peak: 1.2 };
check('[authored] levee: bank stays at 0, crest = peak, toe back to 0', T.terrainLevee(0, LV) === 0 && T.terrainLevee(3, LV) === 0 && Math.abs(T.terrainLevee(18, LV) - 1.2) < 1e-9 && T.terrainLevee(45, LV) === 0);
check('[authored] levee spec order enforced', throwsLike(() => T.terrainLevee(10, { toe0: 5, crest: 4, toe1: 9, peak: 1 }), /toe0 < crest < toe1/));
const A = T.terrainAuthored({ note: 'AUTHORED test relief', floor: 0, fade: (x) => (x < 1000 ? 1 : 0), knolls: () => [{ x: 0, z: 0, r: 100, peak: 3 }], levees: () => [{ d: 18, spec: LV }] });
check('[authored] sum = knoll + levee', Math.abs(A.height(0, 0) - 4.2) < 1e-9, A.height(0, 0));
check('[authored] fade 0 gives the floor', A.height(2000, 0) === 0);
check('[authored] provenance AUTHORED, never RECORDED', A.provenance === 'AUTHORED' && A.source === 'AUTHORED test relief');
const neg = T.terrainAuthored({ note: 'n', floor: 0, fade: () => 1, knolls: () => [{ x: 0, z: 0, r: 10, peak: -5 }], levees: () => [] });
check('[authored] never dips under the floor (land stays above the water level)', neg.height(0, 0) === 0);
check('[authored] missing part throws by name', throwsLike(() => T.terrainAuthored({ note: 'n', floor: 0, fade: () => 1, knolls: () => [] }), /authored has no levees/));

// [lattice] mesh-consistent surface
const L = T.terrainLattice(A, 10);
check('[lattice] equals the sampler at lattice points', Math.abs(L.height(30, 40) - A.height(30, 40)) < 1e-9 && Math.abs(L.height(-20, 10) - A.height(-20, 10)) < 1e-9);
const plane = T.terrainLattice({ height: (x, z) => 0.02 * x - 0.01 * z + 1, provenance: 'AUTHORED', source: 'plane' }, 10);
check('[lattice] reproduces a plane exactly (triangle interpolation)', [[3.3, 7.1], [7.9, 1.2], [-13.4, 22.8]].every(([x, z]) => Math.abs(plane.height(x, z) - (0.02 * x - 0.01 * z + 1)) < 1e-9));
check('[lattice] null sampler height throws by name', throwsLike(() => T.terrainLattice(g, 10).height(100, 100), /no height at/));
check('[lattice] unknown provenance refused', throwsLike(() => T.terrainLattice({ height: () => 0, provenance: 'SURVEYED' }, 10), /not RECORDED or AUTHORED/));

// [patch] geometry = the lattice surface
const P = T.terrainPatch(L, -50, -50, 50, 50, (i, j) => (i < 0 ? 'w' : 'e'), 0.02);
const pe = P.get('e');
check('[patch] one group per key, quads counted', P.size === 2 && pe.quads === 50 && P.get('w').quads === 50, [P.size, pe.quads]);
let vok = true;
for (let v = 0; v < pe.position.length / 3; v++) { const x = pe.position[v * 3], y = pe.position[v * 3 + 1], z = pe.position[v * 3 + 2]; if (Math.abs(y - 0.02 - L.height(x, z)) > 1e-5) vok = false; }
check('[patch] every vertex = lattice height + lift', vok);
let up = true;
for (let t = 0; t < pe.index.length; t += 3) {
  const p = (k) => [pe.position[pe.index[k] * 3], pe.position[pe.index[k] * 3 + 1], pe.position[pe.index[k] * 3 + 2]];
  const [a, b, c] = [p(t), p(t + 1), p(t + 2)], e1 = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], e2 = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
  if (e1[2] * e2[0] - e1[0] * e2[2] <= 0) up = false;   // normal.y > 0
}
check('[patch] triangles face up', up);
// triangle centroid heights equal the lattice (same diagonal split)
let tri = true;
for (let t = 0; t < pe.index.length; t += 3) {
  let cx = 0, cy = 0, cz = 0; for (let k = 0; k < 3; k++) { cx += pe.position[pe.index[t + k] * 3] / 3; cy += pe.position[pe.index[t + k] * 3 + 1] / 3; cz += pe.position[pe.index[t + k] * 3 + 2] / 3; }
  if (Math.abs(cy - 0.02 - L.height(cx, cz)) > 1e-5) tri = false;
}
check('[patch] triangle centroids lie on the lattice surface (walker stands on what is drawn)', tri);
check('[patch] normals unit length and upward', Array.from({ length: pe.normal.length / 3 }, (_, v) => [pe.normal[v * 3], pe.normal[v * 3 + 1], pe.normal[v * 3 + 2]]).every(([x, y, z]) => Math.abs(Math.hypot(x, y, z) - 1) < 1e-5 && y > 0.5));

// [seat] [audit] nothing floats
const tilted = T.terrainLattice({ height: (x) => 0.05 * x, provenance: 'AUTHORED', source: 't' }, 10);
const seat = T.terrainSeat(tilted, 100, 0, 20, 10, 0);
check('[seat] base = lowest ground under the footprint', Math.abs(seat - 0.05 * 90) < 1e-9, seat);
const seatY = T.terrainSeat(tilted, 100, 0, 20, 10, Math.PI / 2);
check('[seat] yaw rotates the footprint', Math.abs(seatY - 0.05 * 95) < 1e-9, seatY);
const au = T.terrainAudit(tilted, [{ id: 'ok', x: 100, z: 0, w: 20, d: 10, yaw: 0, y: seat }, { id: 'float', x: 50, z: 0, w: 4, d: 4, yaw: 0, y: 2.5 + 0.5 }, { id: 'flat0', x: 200, z: 0, w: 4, d: 4, yaw: 0, y: 0 }], 0.1);
check('[audit] a seated base passes, a floating one and a y=0 one on a slope are named', au.bad.map((b) => b.id).join() === 'float,flat0', au);
const sl = T.terrainSlope(tilted, 0, 0, 100, 100, 5);
check('[slope] measures the rise over run', Math.abs(sl.max - 0.05) < 1e-9, sl);

// [adapters] physkit / fleetkit
const gr = T.terrainGround(tilted);
check('[adapters] physkit ground(x, z) = lattice', gr(40, 3) === tilted.height(40, 3));
const fg = T.terrainFleetGround(tilted, -0.4, (x) => x < 0);
check('[adapters] fleet ground: land rides relief, water keeps its level (fleetFlatGround shape)', fg.height(40, 0) === tilted.height(40, 0) && fg.waterLevel(40, 0) === null && fg.waterLevel(-5, 0) === -0.4 && fg.height(-5, 0) === -3.4);

// [kit] inline contract
const py = readFileSync(join(HERE, 'terrainkit.py'), 'utf8');
check('[kit] every top-level name is terrain*/TERRAIN_*', [...py.matchAll(/^(?:function|const|let) ([A-Za-z_$][\w$]*)/gm)].every((m) => /^(terrain|TERRAIN_)/.test(m[1])));
check('[kit] no "real elevation" claim for AUTHORED relief', !/AUTHORED[^.\n]{0,40}real elevation(?! ")/.test(py.replace(/never "real elevation"/g, '')));

// [dem] RECORDED elevation pack twin (ELEV_CONTRACT v1): agrees with every registry pin GEO computed with elevation/sample.py
{
  const { gunzipSync } = await import('node:zlib');
  const ROOT = join(HERE, '..'), EREG = JSON.parse(readFileSync(join(ROOT, 'elevation/registry/elevation.json'), 'utf8'));
  const R_M = 6371008.8, bad = [];
  let n = 0;
  for (const region of ['parishes', 'bayarea']) {
    const g = EREG.grids[region], enc = g.encoding;
    const meta = { w_arcsec: g.bounds_arcsec.w, n_arcsec: g.bounds_arcsec.n, cell_arcsec: g.cell_arcsec, rows: g.rows, cols: g.cols, nodata: enc.nodata_value, scale_m: enc.scale_m, offset_m: enc.offset_m, R_m: R_M, source: 'test' };
    const bytes = gunzipSync(readFileSync(join(ROOT, 'elevation/vendor', g.file)));
    const dem = T.terrainDem(meta, bytes, { lat: 29.975, lng: -90.09 });
    for (const p of EREG.pins.filter((q) => q.region === region)) { n++; const h = dem.heightLL(p.lat, p.lng); if (h !== p.height_m) bad.push([p.id, p.height_m, h]); }
    if (region === 'parishes') {
      check('[dem] scene metres invert the world LTP (world origin reads its own pin)', dem.height(0, 0) === dem.heightLL(29.975, -90.09));
      { const d = 180 / Math.PI, la = 29.975 + (7000 / R_M) * d, lo = -90.09 + (-6000 / (R_M * Math.cos(29.975 / d))) * d;
        check('[dem] scene x east / z = -north map to the right lat/lng (7 km north, 6 km west)', Math.abs(dem.height(-6000, -7000) - dem.heightLL(la, lo)) < 1e-9 && dem.height(-6000, -7000) !== dem.height(-6000, 7000)); }
      check('[dem] outside the grid is null (never 0)', dem.heightLL(10, -90) === null);
      check('[dem] wrong byte length throws', throwsLike(() => T.terrainDem(meta, bytes.subarray(2), { lat: 0, lng: 0 }), /dem bytes/));
      { const m = { ...meta }; delete m.offset_m; check('[dem] missing meta field throws by name', throwsLike(() => T.terrainDem(m, bytes, { lat: 0, lng: 0 }), /dem has no offset_m/)); }
    }
  }
  check('[dem] JS twin agrees with every elevation.json pin (sample.py)', n > 10 && bad.length === 0, { n, bad: bad.slice(0, 4) });
}

// [page] the ELEV w14 mount in the built parish and Bay pages (web/build_parishes.py; the Bay page shares it)
{
  const EREG = JSON.parse(readFileSync(join(HERE, '..', 'elevation/registry/elevation.json'), 'utf8'));
  for (const [name, file, region] of [['parish', 'trade_craft_parishes.html', 'parishes'], ['bay', 'trade_craft_bay.html', 'bayarea']]) {
    const html = readFileSync(join(HERE, file), 'utf8');
    const D = JSON.parse(html.match(/<script type="application\/json" id="parishes-data">([\s\S]*?)<\/script>/)[1]);
    const R = D.relief;
    check(`[page] ${name}: terrain kit inlined once`, (html.match(/TERRAIN_KIT:BEGIN/g) || []).length === 1);
    check(`[page] ${name}: relief RECORDED from the pinned elevation grid (sha256 = elevation.json)`, R.mode === 'RECORDED' && R.dem.sha256 === EREG.grids[region].sha256 && R.dem.path === 'elevation/vendor/' + EREG.grids[region].file);
    check(`[page] ${name}: legend says RECORDED relative to local median land, water AUTHORED, with the USGS attribution`,
      /data-legend="relief" lang="en" hidden>Ground relief: USGS 3DEP \(RECORDED\), shown relative to local median land; water level AUTHORED\./.test(html) && html.includes(EREG.attribution.text));
    check(`[page] ${name}: relief default OFF (?relief=on), flat line kept for the off state`, /on = \/\[\?&\]relief=on\\b\/\.test\(location\.search\)/.test(html) && /<li data-no-elevation>/.test(html));
    check(`[page] ${name}: the grid is sha256-checked and gunzipped in the browser, never embedded`, /crypto\.subtle\.digest\('SHA-256', gz\)/.test(html) && /DecompressionStream\('gzip'\)/.test(html) && html.length < 4e6);
    check(`[page] ${name}: walker, vehicles, building boxes and bases read the relief`, /ground: elevGround\(\), water: waterAt/.test(html) && /const fground = elevFleetGround\(/.test(html) && /b\.y0 \+= y; b\.y1 \+= y;/.test(html) && /V\.set\(x, elevSeat\(x, z, w, d, yaw\), z\)/.test(html));
    check(`[page] ${name}: HUD line names the relief instead of 'flat ground' while on`, /\$\{elevHud\(\) \|\| tr\('parishes\.ground'\)\}/.test(html));
    check(`[page] ${name}: fades >= 10 x the tallest relief they cut (slope <= 0.15)`, Object.values(R.fade_m).every(([a, b]) => b - a >= 10 * Math.max(R.cap_m, R.knoll.peak[1], R.levee.peak)), R.fade_m);
    check(`[page] ${name}: water plane stays at -0.4`, /water\.position\.y = -0\.4/.test(html));
  }
}

if (fails) { console.log(`FAIL test_terrainkit: ${fails} failed`); process.exit(1); }
console.log('test_terrainkit: all checks ok');
