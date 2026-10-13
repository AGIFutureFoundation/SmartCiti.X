/**
 * Land-cover pack verification (LANDCOVER_CONTRACT v1).
 *
 * Every figure in landcover/registry/landcover.json is recomputed here from the vendored bytes,
 * independently of the Python builder: sha256 pins, grid geometry, class shares per region and per
 * member bbox, and every pin's class through a JavaScript twin of landcover/sample.py. The grids must
 * cover every parish and county bbox, the CC BY 4.0 legal code and the ESA WorldCover attribution and
 * citation must be vendored verbatim, and the attribution object must carry the fields a CC-BY credit
 * needs. Unspoken Smiles stays AUTHORED.
 *
 *   node landcover/test.mjs
 *   node landcover/test.mjs --root=/tmp/copy      (mutation runs: a broken copy)
 */
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { gunzipSync } from 'node:zlib';

const HERE = dirname(fileURLToPath(import.meta.url));
const rootArg = process.argv.slice(2).find((a) => a.startsWith('--root='));
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
const MAX_VENDORED_BYTES = 3 * 1024 * 1024;
const WORLDCOVER_CODES = [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100];

const reg = readJSON('landcover/registry/landcover.json');
const manBytes = read('landcover/vendor/manifest.json');
const man = JSON.parse(manBytes.toString('utf8'));

/* ------------------------------------------------------------ stamps -- */
ok('[stamp] source_stamp is sha256 of landcover/build.py',
  need(reg, 'source_stamp', 'registry') === sha(read('landcover/build.py')).slice(0, 16), [`have ${reg.source_stamp}`]);
ok('[stamp] sampler_stamp is sha256 of landcover/sample.py',
  need(reg, 'sampler_stamp', 'registry') === sha(read('landcover/sample.py')).slice(0, 16));
ok('[stamp] manifest_sha256 is sha256 of landcover/vendor/manifest.json', need(reg, 'manifest_sha256', 'registry') === sha(manBytes));

/* ----------------------------------------------------- vendored pins -- */
const files = need(man, 'files', 'manifest');
const onDisk = readdirSync(join(ROOT, 'landcover/vendor')).filter((f) => f !== 'manifest.json').sort();
ok('[pins] every vendored file is pinned in the manifest and every pin exists',
  JSON.stringify(onDisk) === JSON.stringify(Object.keys(files).sort()), [`disk ${onDisk}`, `manifest ${Object.keys(files)}`]);
let total = manBytes.length;
for (const [fn, rec] of Object.entries(files)) {
  const p = join(ROOT, 'landcover/vendor', fn);
  const b = existsSync(p) ? readFileSync(p) : Buffer.alloc(0);
  total += b.length;
  ok(`[pins] ${fn} matches its sha256 pin`, sha(b) === need(rec, 'sha256', fn) && b.length === need(rec, 'bytes', fn),
    [`have ${sha(b).slice(0, 16)} (${b.length} B), pin ${String(rec.sha256).slice(0, 16)}`]);
}
ok(`[size] vendored land-cover data stays under ${MAX_VENDORED_BYTES} bytes`, total <= MAX_VENDORED_BYTES, [`${total} B`]);
ok('[pins] fetch_landcover.py has an offline --check', /'--check'/.test(read('landcover/fetch_landcover.py').toString()));
ok('[pins] every source tile is a WorldCover 2021 v200 tile from the ESA bucket, pinned, CC-BY 4.0',
  Object.values(need(man, 'regions', 'manifest')).every((r) => need(r, 'tiles', 'region').length > 0 && r.tiles.every((t) =>
    String(t.url).startsWith('https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/')
    && /^[0-9a-f]{64}$/.test(t.sha256) && t.product_version === 'V2.0.0' && /^CC-BY 4\.0/.test(t.license))));

/* ----------------------------------------------------------- licence -- */
const lic = existsSync(join(ROOT, 'landcover/vendor/LICENSE_CC-BY-4.0.txt')) ? read('landcover/vendor/LICENSE_CC-BY-4.0.txt').toString() : '';
ok('[licence] the CC BY 4.0 legal code is vendored in full',
  lic.startsWith('Creative Commons Attribution 4.0 International') && lic.includes('Section 3 – License Conditions') && lic.length > 15000,
  [`${lic.length} chars`]);
const att = existsSync(join(ROOT, 'landcover/vendor/WORLDCOVER_ATTRIBUTION.txt')) ? read('landcover/vendor/WORLDCOVER_ATTRIBUTION.txt').toString() : '';
for (const phrase of ['copyright: ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium',
  'license: CC-BY 4.0', 'The WorldCover product is provided free of charge, without restriction of use.',
  'ESA WorldCover 10 m 2021 v200. doi:10.5281/zenodo.7254221.', 'Modifications made by this bundle', 'have not endorsed this bundle']) {
  ok(`[licence] attribution text carries "${phrase.slice(0, 52)}"`, att.includes(phrase));
}
const a = need(reg, 'attribution', 'registry');
ok('[licence] attribution object has every CC-BY field (author, title, source_url, license_id, license_url)',
  ['author', 'title', 'source_url', 'license_id', 'license_url'].every((f) => typeof a[f] === 'string' && a[f].trim())
  && a.license_id === 'CC-BY-4.0' && a.title === 'ESA WorldCover 10 m 2021 v200'
  && a.source_url === 'https://doi.org/10.5281/zenodo.7254221' && /^Zanaga, D\./.test(a.author));
ok('[licence] map attribution text is the product\'s 2021 form and the work is marked modified',
  a.text === '© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium'
  && a.modified === true && /majority class/.test(a.changes) && att.includes(a.text));

/* -------------------------------------------------------- provenance -- */
ok('[honesty] pack provenance is RECORDED', need(reg, 'provenance', 'registry') === 'RECORDED');
ok('[honesty] Unspoken Smiles has no grid and stays AUTHORED',
  need(need(reg, 'not_gridded', 'registry'), 'smiles', 'not_gridded').provenance === 'AUTHORED'
  && !('smiles' in need(reg, 'grids', 'registry')) && readJSON('smiles/registry/smiles.json').provenance === 'AUTHORED');
ok('[honesty] the registry says class is not species', need(reg, 'honesty', 'registry').some((h) => /never which trees/.test(h)));
ok('[classes] the class table is exactly WorldCover\'s 11 codes',
  JSON.stringify(Object.keys(need(reg, 'classes', 'registry')).map(Number).sort((x, y) => x - y)) === JSON.stringify(WORLDCOVER_CODES)
  && reg.classes['10'] === 'tree cover' && reg.classes['90'] === 'herbaceous wetland');

/* ------------------------------------------------------------- grids -- */
const grids = need(reg, 'grids', 'registry');
const MEMBERS = { parishes: ['parishes/registry/parishes.json', 'parishes'], bayarea: ['bayarea/registry/bayarea.json', 'counties'] };
ok('[grids] exactly the parish and Bay regions are gridded', JSON.stringify(Object.keys(grids).sort()) === JSON.stringify(Object.keys(MEMBERS).sort()));
const count = (raw, cols, r0, r1, c0, c1) => {
  const cnt = {}; let nd = 0;
  for (let r = r0; r < r1; r++) for (let c = c0; c < c1; c++) {
    const v = raw[r * cols + c];
    if (v === 0) { nd++; continue; }
    cnt[v] = (cnt[v] || 0) + 1;
  }
  return { cnt, nd };
};
const loaded = {};
for (const [name, g] of Object.entries(grids)) {
  const b = need(g, 'bounds_arcsec', name);
  const c = need(g, 'cell_arcsec', name), rows = need(g, 'rows', name), cols = need(g, 'cols', name);
  const raw = gunzipSync(read(join('landcover/vendor', need(g, 'file', name))));
  ok(`[grids] ${name}: decoded size is rows*cols`, raw.length === rows * cols, [`${raw.length} vs ${rows * cols}`]);
  ok(`[grids] ${name}: bounds are whole cells`, (b.e - b.w) === cols * c && (b.n - b.s) === rows * c);
  ok(`[grids] ${name}: registry agrees with the manifest region`,
    JSON.stringify([b.w, b.s, b.e, b.n, c, rows, cols]) === JSON.stringify(['w_arcsec', 's_arcsec', 'e_arcsec', 'n_arcsec', 'cell_arcsec', 'rows', 'cols'].map((k) => need(man.regions[name], k, name))));
  ok(`[grids] ${name}: 50-100 m cells (${g.cell_size_m.north_south} m N-S), nodata 0`,
    g.cell_size_m.north_south >= 50 && g.cell_size_m.north_south <= 100 && g.encoding.nodata_value === 0 && g.encoding.dtype === 'uint8');
  loaded[name] = { rows, cols, c, n: b.n, w: b.w, raw };
  const { cnt, nd } = count(raw, cols, 0, rows, 0, cols);
  const bogus = Object.keys(cnt).map(Number).filter((k) => !WORLDCOVER_CODES.includes(k));
  ok(`[grids] ${name}: every byte is 0 or a WorldCover class code`, bogus.length === 0, [`bogus ${bogus}`]);
  const og = need(g, 'classes_over_grid', name);
  ok(`[grids] ${name}: class counts and nodata recomputed from the bytes`,
    JSON.stringify(Object.fromEntries(Object.entries(cnt).map(([k, v]) => [k, v]))) === JSON.stringify(Object.fromEntries(Object.keys(og.cells).sort((x, y) => x - y).map((k) => [k, og.cells[k]])))
    && og.nodata_cells === nd, [`have ${JSON.stringify(og.cells)}`, `recomputed ${JSON.stringify(cnt)} nd ${nd}`]);
  ok(`[grids] ${name}: under a fifth of the cells are nodata`, nd / (rows * cols) < 0.2, [`${(nd / rows / cols).toFixed(3)}`]);
  const [rel, key] = MEMBERS[name];
  let items = need(readJSON(rel), key, rel);
  items = Array.isArray(items) ? items : Object.values(items);
  const out = items.filter((it) => {
    const [w, so, e, no] = need(it, 'bbox_wgs84', rel).map((x) => x * 3600);
    return w < b.w || so < b.s || e > b.e || no > b.n;
  });
  ok(`[cover] ${name}: all ${items.length} ${key} bboxes lie inside the grid`, out.length === 0 && items.length > 0, out.map((it) => it.name));
  const mem = need(need(reg, 'members', 'registry'), name, 'members');
  ok(`[cover] ${name}: one member entry per ${key === 'counties' ? 'county' : 'parish'}`,
    JSON.stringify(Object.keys(mem).sort()) === JSON.stringify(items.map((it) => it.fips).sort()));
  const wrong = items.filter((it) => {
    const [w, so, e, no] = it.bbox_wgs84.map((x) => x * 3600);
    const r0 = Math.max(0, Math.ceil((b.n - no) / c - 0.5)), r1 = Math.min(rows, Math.floor((b.n - so) / c - 0.5) + 1);
    const c0 = Math.max(0, Math.ceil((w - b.w) / c - 0.5)), c1 = Math.min(cols, Math.floor((e - b.w) / c - 0.5) + 1);
    const got = need(need(mem, it.fips, name), 'classes_over_bbox', it.fips);
    const { cnt: m } = count(raw, cols, r0, r1, c0, c1);
    return Object.keys(m).length !== Object.keys(got.cells).length || Object.entries(m).some(([k, v]) => got.cells[k] !== v);
  });
  ok(`[cover] ${name}: every member's bbox class counts recomputed from the bytes`, wrong.length === 0, wrong.map((it) => it.name));
}

/* ----------------------------------------------------- the one rule -- */
const classAt = (G, lat, lng) => {
  const fy = (G.n - lat * 3600) / G.c, fx = (lng * 3600 - G.w) / G.c;
  if (!(fy >= 0 && fy <= G.rows && fx >= 0 && fx <= G.cols)) return null;
  const v = G.raw[Math.min(Math.floor(fy), G.rows - 1) * G.cols + Math.min(Math.floor(fx), G.cols - 1)];
  return v === 0 ? null : v;
};
const pins = need(reg, 'pins', 'registry');
const disagree = pins.filter((p) => classAt(loaded[p.region], p.lat, p.lng) !== p.class);
ok(`[sample] all ${pins.length} pins agree with the JS twin of the one sampler`, pins.length === 24 && disagree.length === 0,
  disagree.map((p) => `${p.region}/${p.id}: registry ${p.class}, js ${classAt(loaded[p.region], p.lat, p.lng)}`));
ok('[sample] outside the grid the sampler says null, never a class',
  classAt(loaded.parishes, 35, -90) === null && classAt(loaded.bayarea, 37.8, -100) === null);
const py = read('landcover/sample.py').toString();
ok('[sample] sample.py returns None for nodata/outside and has no .get default', /return None/.test(py) && !/\.get\(/.test(py));
ok('[sample] the world origins read as recorded: New Orleans built-up, the Bay frame origin water',
  pins.find((p) => p.region === 'parishes' && p.id === 'world.origin').class === 50
  && pins.find((p) => p.region === 'bayarea' && p.id === 'world.origin').class === 80);

console.log(`\n${n} ok, ${bad} failed`);
process.exit(bad ? 1 : 0);
