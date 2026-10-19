/**
 * Elevation pack verification (ELEV_CONTRACT v1).
 *
 * Every figure in elevation/registry/elevation.json is recomputed here from
 * the vendored bytes, independently of the Python builder: the sha256 pins,
 * the grid geometry, the per-region and per-member stats, and every pin's
 * height through a JavaScript twin of elevation/sample.py's one rule. The
 * grids must cover every parish and county bbox the owning registries hold,
 * the licence text must be vendored verbatim, and the pack must say RECORDED
 * only where it holds data (Unspoken Smiles stays AUTHORED).
 *
 *   node elevation/test.mjs
 *   node elevation/test.mjs --root=/tmp/copy      (mutation runs: a broken copy)
 */
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { gunzipSync } from 'node:zlib';

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const rootArg = args.find((a) => a.startsWith('--root='));
const ROOT = resolve(rootArg ? rootArg.slice(7) : join(HERE, '..'));

let n = 0, bad = 0;
const ok = (m, c, evidence = []) => {
  if (c) { n++; console.log('  ok  ' + m); return; }
  bad++;
  console.log('FAIL  ' + m);
  for (const e of evidence) console.log('      ' + e);
};
const die = (m) => { console.log('FAIL  ' + m); console.log(`\n${n} ok, ${bad + 1} failed`); process.exit(1); };
const need = (o, k, where) => {
  if (o === null || typeof o !== 'object' || !(k in o)) die(`[schema] ${where} is missing ${k}`);
  return o[k];
};
const read = (rel) => readFileSync(join(ROOT, rel));
const readJSON = (rel) => JSON.parse(read(rel).toString('utf8'));
const sha = (b) => createHash('sha256').update(b).digest('hex');

const MAX_VENDORED_BYTES = 4 * 1024 * 1024;   // the pack's own size budget ("a few MB")

const reg = readJSON('elevation/registry/elevation.json');
const manBytes = read('elevation/vendor/manifest.json');
const man = JSON.parse(manBytes.toString('utf8'));

/* ------------------------------------------------------------ stamps -- */
ok('[stamp] source_stamp is sha256 of elevation/build.py',
  need(reg, 'source_stamp', 'registry') === sha(read('elevation/build.py')).slice(0, 16), [`have ${reg.source_stamp}`]);
ok('[stamp] sampler_stamp is sha256 of elevation/sample.py',
  need(reg, 'sampler_stamp', 'registry') === sha(read('elevation/sample.py')).slice(0, 16), [`have ${reg.sampler_stamp}`]);
ok('[stamp] manifest_sha256 is sha256 of elevation/vendor/manifest.json',
  need(reg, 'manifest_sha256', 'registry') === sha(manBytes));

/* ----------------------------------------------------- vendored pins -- */
const files = need(man, 'files', 'manifest');
const onDisk = readdirSync(join(ROOT, 'elevation/vendor')).filter((f) => f !== 'manifest.json').sort();
ok('[pins] every vendored file is pinned in the manifest and every pin exists',
  JSON.stringify(onDisk) === JSON.stringify(Object.keys(files).sort()), [`disk ${onDisk}`, `manifest ${Object.keys(files)}`]);
let total = manBytes.length;
for (const [fn, rec] of Object.entries(files)) {
  const p = join(ROOT, 'elevation/vendor', fn);
  const b = existsSync(p) ? readFileSync(p) : Buffer.alloc(0);
  total += b.length;
  ok(`[pins] ${fn} matches its sha256 pin`, sha(b) === need(rec, 'sha256', fn) && b.length === need(rec, 'bytes', fn),
    [`have ${sha(b).slice(0, 16)} (${b.length} B), pin ${String(rec.sha256).slice(0, 16)}`]);
}
ok(`[size] vendored elevation data stays under ${MAX_VENDORED_BYTES} bytes`, total <= MAX_VENDORED_BYTES, [`${total} B`]);
ok('[pins] fetch_dem.py has an offline --check', /'--check'/.test(read('elevation/fetch_dem.py').toString()));

/* ----------------------------------------------------------- licence -- */
const licFile = need(reg, 'licence_file', 'registry');
const lic = existsSync(join(ROOT, licFile)) ? read(licFile).toString('utf8') : '';
ok('[licence] USGS use-constraints text is vendored beside the grids', lic.length > 0, [licFile]);
for (const phrase of ['U.S. public domain', 'Use constraints:', 'Acknowledgement of the originating agencies',
  'Any user who modifies the data is obligated to describe the types of modifications they perform',
  'not to misrepresent the data', 'has not approved or endorsed']) {
  ok(`[licence] constraints text carries "${phrase.slice(0, 48)}"`, lic.includes(phrase));
}
ok('[licence] registry licence names public domain and the constraints file',
  /public domain/.test(need(reg, 'licence', 'registry')) && reg.licence.includes('USGS_3DEP_USE_CONSTRAINTS.txt'));
ok('[licence] attribution block names the USGS, the source host and a non-CC licence id',
  need(reg, 'attribution', 'registry').author === 'U.S. Geological Survey'
  && /^Elevation: USGS 3D Elevation Program/.test(reg.attribution.text)
  && reg.attribution.source_url === man.base_url && reg.attribution.license_id === 'LicenseRef-US-Government-Public-Domain');
ok('[licence] registry states its modifications (the metadata requires it)',
  /block mean/.test(need(reg, 'modifications', 'registry')));
ok('[licence] every source tile is from the USGS staged-products host and pinned',
  Object.values(need(man, 'regions', 'manifest')).every((r) => need(r, 'tiles', 'region').every((t) =>
    t.published === false || (String(t.url).startsWith('https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1/')
      && /^[0-9a-f]{64}$/.test(t.sha256) && /North American Vertical Datum of 1988/.test(t.vertical_datum)))));

/* -------------------------------------------------------- provenance -- */
ok('[honesty] pack provenance is RECORDED', need(reg, 'provenance', 'registry') === 'RECORDED');
ok('[honesty] Unspoken Smiles has no grid and stays AUTHORED',
  need(need(reg, 'not_gridded', 'registry'), 'smiles', 'not_gridded').provenance === 'AUTHORED'
  && !('smiles' in need(reg, 'grids', 'registry'))
  && readJSON('smiles/registry/smiles.json').provenance === 'AUTHORED');
ok('[honesty] the registry says what a cell cannot resolve (levees, grades)',
  need(reg, 'honesty', 'registry').some((h) => /levee/.test(h) && /NOT resolved/.test(h)));

/* ------------------------------------------------------------- grids -- */
const grids = need(reg, 'grids', 'registry');
const MEMBERS = { parishes: ['parishes/registry/parishes.json', 'parishes'], bayarea: ['bayarea/registry/bayarea.json', 'counties'] };
ok('[grids] exactly the parish and Bay regions are gridded',
  JSON.stringify(Object.keys(grids).sort()) === JSON.stringify(Object.keys(MEMBERS).sort()));

const loaded = {};
for (const [name, g] of Object.entries(grids)) {
  const enc = need(g, 'encoding', name);
  const b = need(g, 'bounds_arcsec', name);
  const c = need(g, 'cell_arcsec', name), rows = need(g, 'rows', name), cols = need(g, 'cols', name);
  const raw = gunzipSync(read(join('elevation/vendor', need(g, 'file', name))));
  ok(`[grids] ${name}: decoded size is rows*cols*2`, raw.length === rows * cols * 2, [`${raw.length} vs ${rows * cols * 2}`]);
  ok(`[grids] ${name}: bounds are whole cells`, (b.e - b.w) === cols * c && (b.n - b.s) === rows * c);
  ok(`[grids] ${name}: registry agrees with the manifest region`,
    JSON.stringify([b.w, b.s, b.e, b.n, c, rows, cols]) === JSON.stringify(['w_arcsec', 's_arcsec', 'e_arcsec', 'n_arcsec', 'cell_arcsec', 'rows', 'cols'].map((k) => need(man.regions[name], k, name))));
  ok(`[grids] ${name}: 30-200 m cells (${g.cell_size_m.north_south} m N-S)`,
    g.cell_size_m.north_south >= 30 && g.cell_size_m.north_south <= 200 && g.units === 'm' && g.vertical_datum === 'NAVD88');
  ok(`[grids] ${name}: encoding is uint16, nodata 0, h = v*0.1 - 100`,
    enc.nodata_value === 0 && enc.scale_m === 0.1 && enc.offset_m === 100 && /uint16 little-endian/.test(enc.dtype));
  const G = { rows, cols, c, n: b.n, w: b.w, raw, nodata: enc.nodata_value, scale: enc.scale_m, offset: enc.offset_m };
  loaded[name] = G;
  // stats over the whole grid, recomputed
  let lo = Infinity, hi = -Infinity, s = 0, v = 0, nd = 0;
  for (let i = 0; i < rows * cols; i++) {
    const x = raw[2 * i] | (raw[2 * i + 1] << 8);
    if (x === 0) { nd++; continue; }
    v++; s += x; if (x < lo) lo = x; if (x > hi) hi = x;
  }
  const m = (x) => Math.round((x * 0.1 - 100) * 10) / 10;
  const st = need(g, 'stats', name);
  ok(`[grids] ${name}: min/max/valid/nodata recomputed from the bytes`,
    st.min_m === m(lo) && st.max_m === m(hi) && st.valid_cells === v && st.nodata_cells === nd,
    [`have ${JSON.stringify(st).slice(0, 120)}`, `recomputed ${m(lo)} ${m(hi)} ${v} ${nd}`]);
  ok(`[grids] ${name}: mean recomputed`, Math.abs(st.mean_m - (s / v * 0.1 - 100)) < 0.006);
  ok(`[grids] ${name}: under a quarter of the cells are nodata`, nd / (rows * cols) < 0.25, [`${(nd / rows / cols).toFixed(3)}`]);
  // coverage: every member bbox inside the grid
  const [rel, key] = MEMBERS[name];
  const src = readJSON(rel);
  let items = need(src, key, rel);
  items = Array.isArray(items) ? items : Object.values(items);
  const out = items.filter((it) => {
    const [w, so, e, no] = need(it, 'bbox_wgs84', rel).map((x) => x * 3600);
    return w < b.w || so < b.s || e > b.e || no > b.n;
  });
  ok(`[cover] ${name}: all ${items.length} ${key} bboxes lie inside the grid`, out.length === 0 && items.length > 0,
    out.map((it) => it.name));
  const mem = need(need(reg, 'members', 'registry'), name, 'members');
  ok(`[cover] ${name}: one member entry per ${key === 'counties' ? 'county' : 'parish'} in ${rel}`,
    JSON.stringify(Object.keys(mem).sort()) === JSON.stringify(items.map((it) => it.fips).sort()));
  // per-member stats over the cells whose centre lies in the member's bbox, recomputed
  const wrong = items.filter((it) => {
    const [w, so, e, no] = it.bbox_wgs84.map((x) => x * 3600);
    const r0 = Math.max(0, Math.ceil((b.n - no) / c - 0.5)), r1 = Math.min(rows, Math.floor((b.n - so) / c - 0.5) + 1);
    const c0 = Math.max(0, Math.ceil((w - b.w) / c - 0.5)), c1 = Math.min(cols, Math.floor((e - b.w) / c - 0.5) + 1);
    let a = Infinity, z = -Infinity, cnt = 0;
    for (let r = r0; r < r1; r++) for (let q = c0; q < c1; q++) {
      const x = raw[2 * (r * cols + q)] | (raw[2 * (r * cols + q) + 1] << 8);
      if (x === 0) continue;
      cnt++; if (x < a) a = x; if (x > z) z = x;
    }
    const got = need(need(mem, it.fips, name), 'stats_over_bbox', it.fips);
    return got.min_m !== m(a) || got.max_m !== m(z) || got.valid_cells !== cnt;
  });
  ok(`[cover] ${name}: every member's bbox min/max/valid recomputed from the bytes`, wrong.length === 0,
    wrong.map((it) => it.name));
}
ok('[cover] 13 parishes and 9 Bay counties are covered',
  Object.keys(reg.members.parishes).length === 13 && Object.keys(reg.members.bayarea).length === 9);

/* ----------------------------------------------------- the one rule -- */
// JavaScript twin of elevation/sample.py height_m(): bilinear between the 4 centres, containing cell if any is nodata.
const cellM = (G, r, c) => {
  const x = G.raw[2 * (r * G.cols + c)] | (G.raw[2 * (r * G.cols + c) + 1] << 8);
  return x === G.nodata ? null : Math.round((x * G.scale - G.offset) * 10) / 10;
};
const heightM = (G, lat, lng) => {
  const fy = (G.n - lat * 3600) / G.c, fx = (lng * 3600 - G.w) / G.c;
  if (!(fy >= 0 && fy <= G.rows && fx >= 0 && fx <= G.cols)) return null;
  const rc = Math.min(Math.floor(fy), G.rows - 1), cc = Math.min(Math.floor(fx), G.cols - 1);
  const cy = Math.min(Math.max(fy - 0.5, 0), G.rows - 1), cx = Math.min(Math.max(fx - 0.5, 0), G.cols - 1);
  const r0 = Math.floor(cy), c0 = Math.floor(cx), r1 = Math.min(r0 + 1, G.rows - 1), c1 = Math.min(c0 + 1, G.cols - 1);
  const ty = cy - r0, tx = cx - c0;
  const q = [cellM(G, r0, c0), cellM(G, r0, c1), cellM(G, r1, c0), cellM(G, r1, c1)];
  if (q.some((v) => v === null)) return cellM(G, rc, cc);
  const top = q[0] + (q[1] - q[0]) * tx, bot = q[2] + (q[3] - q[2]) * tx;
  return Math.round((top + (bot - top) * ty) * 100) / 100;
};
const pins = need(reg, 'pins', 'registry');
const disagree = pins.filter((p) => {
  const h = heightM(loaded[p.region], p.lat, p.lng);
  return h === null ? p.height_m !== null : (p.height_m === null || Math.abs(h - p.height_m) > 0.011);
});
ok(`[sample] all ${pins.length} pins agree with the JS twin of the one sampler`, pins.length === 24 && disagree.length === 0,
  disagree.map((p) => `${p.region}/${p.id}: registry ${p.height_m}, js ${heightM(loaded[p.region], p.lat, p.lng)}`));
ok('[sample] every member frame origin has a RECORDED height (none fell on nodata)',
  pins.filter((p) => p.id.endsWith('.frame_origin')).every((p) => typeof p.height_m === 'number'));
ok('[sample] outside the grid the sampler says null, never 0',
  heightM(loaded.parishes, 35, -90) === null && heightM(loaded.bayarea, 37.8, -100) === null);
const py = read('elevation/sample.py').toString();
ok('[sample] sample.py returns None outside the grid and has no default height',
  /return None/.test(py) && !/\.get\(/.test(py) && !/\?\?/.test(read('elevation/test.mjs').toString().replace(/\/\/.*|'[^']*'/g, '')));
// geography sanity against the source's own relief: Bay max above 1000 m, parish relief under 200 m
ok('[sample] relief is the right order: Bay max > 1000 m, parish max < 200 m, parish mean < 30 m',
  grids.bayarea.stats.max_m > 1000 && grids.parishes.stats.max_m < 200 && grids.parishes.stats.mean_m < 30);

console.log(`\n${n} ok, ${bad} failed`);
process.exit(bad ? 1 : 0);
