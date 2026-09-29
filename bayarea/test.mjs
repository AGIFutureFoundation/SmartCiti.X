/* bayarea/test.mjs — the Bay Area county pack, checked. Browser-free, network-free.
 *
 * Recompute, never re-read: the Bay frame is recomputed from the geo registry's RECORDED Bay points, the
 * county list from the vendored topojson, counts from the entries; file shas, sizes and WebP dimensions from
 * the bytes on disk. Each check carries a [tag] the mutation harness greps for.
 */
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m); } };
const buf = (p) => readFileSync(join(ROOT, p));
const J = (p) => JSON.parse(buf(p).toString('utf8'));
const sha = (b) => createHash('sha256').update(b).digest('hex');

console.log('bayarea/test.mjs');
const REG = 'bayarea/registry/bayarea.json';
ok(existsSync(join(ROOT, REG)), '[registry] bayarea/registry/bayarea.json exists');
if (!existsSync(join(ROOT, REG))) { console.log(`\n${pass} ok, ${fail} FAIL`); process.exit(1); }
const R = J(REG);
const C = R.counties;
const IDS = Object.keys(C).sort();
const GEO = J('geo/registry/campuses_geo.json');

/* ---- stamp ---------------------------------------------------------- */
{
  const want = ['bayarea/build.py', 'bayarea/render_bay.py', 'bayarea/world_bay.py', 'bayarea/districts_map.py', 'parishes/build.py', 'parishes/render.py',
    'parishes/vendor/us-atlas/counties-10m.json', 'parishes/vendor/us-atlas/manifest.json',
    'geo/registry/campuses_geo.json', 'parcels/registry/parcels.json', 'restoration/registry/restoration.json', 'terrain/vendor/manifest.json', 'terrain/vendor/ne_coastline.json', 'terrain/vendor/ne_rivers.json', 'bayarea/authored/water_labels.json'];
  const h = createHash('sha256');
  for (const p of R.inputs) { h.update(p + '\0'); h.update(buf(p)); h.update('\0'); }
  const d = h.digest('hex');
  ok(R.pack === 'bayarea' && R.pack_version === J('pack/manifest.json').pack_version && JSON.stringify(R.inputs) === JSON.stringify(want) && d.slice(0, 16) === R.source_stamp
     && d === R.source_stamp_sha256, `[stamp] source_stamp ${R.source_stamp} is current over the ${want.length} inputs; pack_version is the bundle version read from pack/manifest.json`);
}

/* ---- vendored source ------------------------------------------------ */
{
  const man = J('parishes/vendor/us-atlas/manifest.json');
  ok(sha(buf('parishes/vendor/us-atlas/counties-10m.json')) === man.files['counties-10m.json'].sha256
     && R.source.file_sha256 === man.files['counties-10m.json'].sha256 && R.source.license === 'ISC'
     && R.source.version === '3.0.1' && /^sha512-/.test(R.source.integrity),
    '[vendor] the vendored us-atlas counties-10m.json matches the manifest sha256 the registry cites (ISC, 3.0.1)');
}

/* ---- topojson decode ------------------------------------------------ */
const TOPO = J('parishes/vendor/us-atlas/counties-10m.json');
const [sx, sy] = TOPO.transform.scale, [tx, ty] = TOPO.transform.translate;
const r6 = (v) => Math.round(v * 1e6) / 1e6;
const ARCS = TOPO.arcs.map((a) => { let x = 0, y = 0; return a.map(([dx, dy]) => { x += dx; y += dy; return [r6(x * sx + tx), r6(y * sy + ty)]; }); });
const arcPts = (i) => (i >= 0 ? ARCS[i] : ARCS[~i].slice().reverse());
const ringOf = (idx) => { const out = []; for (const i of idx) { const p = arcPts(i); out.push(...(out.length ? p.slice(1) : p)); } return out; };
const polysOf = (g) => (g.type === 'Polygon' ? [g.arcs] : g.arcs).map((poly) => poly.map(ringOf));
const pip = ([x, y], ring) => { let ins = false; for (let k = 0, n = ring.length; k < n; k++) { const [x1, y1] = ring[k], [x2, y2] = ring[(k + 1) % n]; if ((y1 > y) !== (y2 > y) && x1 + (y - y1) * (x2 - x1) / (y2 - y1) > x) ins = !ins; } return ins; };
const inPolys = (pt, polys) => polys.some((poly) => pip(pt, poly[0]) && !poly.slice(1).some((h) => pip(pt, h)));
const orient = (a, b, c) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
const cross = (p1, p2, q1, q2) => orient(q1, q2, p1) * orient(q1, q2, p2) < 0 && orient(p1, p2, q1) * orient(p1, p2, q2) < 0;
const meetsFrame = (polys, f) => {
  const K = [[f.w, f.s], [f.e, f.s], [f.e, f.n], [f.w, f.n]];
  return polys.some(([outer]) => outer.some(([x, y]) => f.w <= x && x <= f.e && f.s <= y && y <= f.n)
    || K.some((c) => pip(c, outer))
    || outer.some((a, i) => K.some((c, j) => cross(a, outer[(i + 1) % outer.length], c, K[(j + 1) % 4]))));
};
const byId = Object.fromEntries(TOPO.objects.counties.geometries.map((g) => [g.id, g]));

/* ---- Bay frame + computed county list -------------------------------- */
{
  const pts = [];
  for (const cid of ['oakland', 'treasure-island']) {
    pts.push(GEO.campuses[cid]);
    for (const a of GEO.anchors[cid]) pts.push(a);
  }
  const RS = J('restoration/registry/restoration.json').sites;
  for (const s of RS) if (s.lat !== null && s.lng !== null) pts.push({ lat: s.lat, lng: s.lng, provenance: 'RECORDED' });
  const rec = pts.filter((p) => p.provenance === 'RECORDED');
  const F = { w: Math.min(...rec.map((p) => p.lng)), s: Math.min(...rec.map((p) => p.lat)),
    e: Math.max(...rec.map((p) => p.lng)), n: Math.max(...rec.map((p) => p.lat)) };
  ok(JSON.stringify(R.bay_frame.bounds) === JSON.stringify(F) && /^DERIVED/.test(R.bay_frame.provenance)
     && R.bay_frame.excluded_points.includes('treasure-island'),
    `[frame] the Bay frame is the bbox of the ${rec.length} RECORDED Bay campus/anchor points + recorded restoration sites (DERIVED; the DERIVED Treasure Island centroid excluded)`);
  const hits = TOPO.objects.counties.geometries.filter((g) => g.id.startsWith('06') && meetsFrame(polysOf(g), F)).map((g) => g.id).sort();
  ok(hits.length > 0 && JSON.stringify(hits) === JSON.stringify(IDS) && JSON.stringify(R.selection.selected.slice().sort()) === JSON.stringify(hits),
    `[select] recomputed from the vendored outlines: exactly these ${hits.length} California counties meet the Bay frame: ${hits.map((f) => f + ' ' + byId[f].properties.name).join(', ')}`);
  const W = GEO.city.oakland.bounds;
  const wide = TOPO.objects.counties.geometries.filter((g) => g.id.startsWith('06') && meetsFrame(polysOf(g), W)).map((g) => g.id).sort();
  ok(R.selection.wider_frame.would_select === wide.length && JSON.stringify(R.selection.wider_frame.fips) === JSON.stringify(wide),
    `[select] the wider RECORDED Locator.X frame is evaluated honestly (${wide.length} counties) and recorded as not used`);
  ok(IDS.every((f) => JSON.stringify(C[f].outline.polygons) === JSON.stringify(polysOf(byId[f])) && C[f].name === byId[f].properties.name),
    '[outline] every outline and name equals the vendored Census outline vertex for vertex (RECORDED, not redrawn)');
}

/* ---- provenance per field ------------------------------------------- */
{
  const bad = [];
  for (const f of IDS) {
    const X = C[f];
    if (X.outline.provenance !== 'RECORDED') bad.push(f + ' outline');
    if (!Array.isArray(X.landmarks) || X.landmarks.length !== 0) bad.push(f + ' landmarks not empty');
    if (!X.districts.length || X.districts.some((d) => d.provenance !== 'AUTHORED')) bad.push(f + ' districts');
    if (!/NOT an official neighbourhood/.test(X.districts_note)) bad.push(f + ' districts_note');
    for (const a of X.anchors) if (a.provenance !== 'RECORDED' || !/Locator\.X/.test(a.source)) bad.push(f + ' anchor ' + a.name);
    for (const c of X.campuses) if (c.provenance !== GEO.campuses[c.campus].provenance || c.source !== GEO.campuses[c.campus].source) bad.push(f + ' campus ' + c.campus);
    const m = X.map;
    if (!/AUTHORED/.test(m.fabric) || !/not satellite, not a survey/.test(m.label) || !/AUTHORED/.test(m.fabric_layers.provenance)) bad.push(f + ' map labels');
  }
  if (R.water.labels.some((w) => w.provenance !== 'AUTHORED')) bad.push('water labels');
  ok(bad.length === 0 && R.provenance.outline.startsWith('RECORDED') && R.provenance.districts.startsWith('AUTHORED'),
    `[prov] every field carries its tier: outlines RECORDED, districts/water labels/fabric AUTHORED, anchors RECORDED, campuses copied as tagged, no landmarks${bad.length ? ' [' + bad.slice(0, 4).join('; ') + ']' : ''}`);
}


/* ---- restoration sites at their recorded coordinates ------------------- */
{
  const RS = J('restoration/registry/restoration.json').sites;
  const placed = IDS.flatMap((f) => C[f].restoration_sites.map((s) => [f, s]));
  const bad = [];
  for (const S of RS) {
    const here = placed.filter(([, s]) => s.id === S.id);
    const off = R.restoration_not_placed.filter((s) => s.id === S.id);
    if (here.length + off.length !== 1) { bad.push(S.id + ' placed ' + (here.length + off.length) + 'x'); continue; }
    if (S.lat === null) { if (!off.length) bad.push(S.id + ' has no point but was placed'); continue; }
    const [f, s] = here.length ? here[0] : [null, off[0]];
    if (s.lat !== S.lat || s.lng !== S.lng || s.provenance !== 'RECORDED') bad.push(S.id + ' coords/provenance');
    if (f && !inPolys([S.lng, S.lat], C[f].outline.polygons)) bad.push(S.id + ' not inside ' + f);
    if (!f && IDS.some((g) => inPolys([S.lng, S.lat], C[g].outline.polygons))) bad.push(S.id + ' left out although a county holds it');
  }
  ok(bad.length === 0 && R.counts.restoration_placed === placed.length,
    `[restoration] all ${RS.length} restoration registry sites accounted for: ${placed.length} placed at their recorded lat/lng in the county whose outline holds them, ${R.restoration_not_placed.length} kept aside with the reason${bad.length ? ' [' + bad.slice(0, 3).join('; ') + ']' : ''}`);
}

/* ---- adjacency + counts --------------------------------------------- */
{
  const sym = IDS.every((f) => C[f].adjacent.every((n) => C[n] && C[n].adjacent.includes(f)));
  const arcsOk = IDS.every((f) => C[f].borders.every((b) => b.segments.every((s) => C[b.with].borders.some((bb) => bb.with === f && bb.segments.some((t) => t.arc === s.arc)))));
  ok(sym && arcsOk && IDS.some((f) => C[f].adjacent.length), '[adjacency] adjacency is symmetric and every shared border arc appears in both counties');
  const K = R.counts;
  ok(K.counties === IDS.length && K.adjacency_pairs === IDS.reduce((s, f) => s + C[f].adjacent.length, 0) / 2
     && K.districts === IDS.reduce((s, f) => s + C[f].districts.length, 0)
     && K.anchors === IDS.reduce((s, f) => s + C[f].anchors.length, 0)
     && K.maps_4k === IDS.length && K.tiles === 16 * IDS.length,
    `[counts] counts recomputed: ${K.counties} counties, ${K.adjacency_pairs} pairs, ${K.districts} AUTHORED districts, ${K.anchors} anchors, ${K.tiles} tiles`);
}

/* ---- districts inside the outline ----------------------------------- */
{
  const bad = [];
  for (const f of IDS) {
    const ids = new Set();
    for (const d of C[f].districts) {
      if (!inPolys(d.seed_local_m, C[f].outline_local_m)) bad.push(d.id + ' outside');
      if (ids.has(d.id) || !d.id.startsWith(f + '-D')) bad.push(d.id + ' id');
      ids.add(d.id);
    }
  }
  ok(bad.length === 0, `[districts] every AUTHORED district seed lies inside its county's coarse outline and ids are unique${bad.length ? ' [' + bad.slice(0, 3).join('; ') + ']' : ''}`);
}

/* ---- maps + tiles --------------------------------------------------- */
const webpSize = (b) => {
  if (b.toString('ascii', 0, 4) !== 'RIFF' || b.toString('ascii', 8, 12) !== 'WEBP') return null;
  const kind = b.toString('ascii', 12, 16);
  if (kind === 'VP8X') return [1 + b.readUIntLE(24, 3), 1 + b.readUIntLE(27, 3)];
  if (kind === 'VP8 ') return [b.readUInt16LE(26) & 0x3fff, b.readUInt16LE(28) & 0x3fff];
  if (kind === 'VP8L') { const v = b.readUInt32LE(21); return [(v & 0x3fff) + 1, ((v >> 14) & 0x3fff) + 1]; }
  return null;
};
{
  const bad = [];
  for (const f of IDS) {
    const m = C[f].map;
    for (const [p, px, h] of [[m.path, 4096, m.sha256], [m.preview, 512, m.preview_sha256]]) {
      if (!existsSync(join(ROOT, p))) { bad.push(p + ' missing'); continue; }
      const b = buf(p); const d = webpSize(b);
      if (!d || d[0] !== px || d[1] !== px || sha(b) !== h) bad.push(p + ' dims/sha');
    }
    if (m.path !== `bayarea/maps/${f}-4k.webp` || m.bytes > 2000000) bad.push(f + ' path/bytes');
  }
  ok(bad.length === 0, `[maps] every county has bayarea/maps/<fips>-4k.webp (4096^2, <= 2,000,000 B) + 512 preview, sha as recorded${bad.length ? ' [' + bad.slice(0, 3).join('; ') + ']' : ''}`);
  const tb = [];
  for (const f of IDS) {
    const G = C[f].map.ground_tiles; const ex = C[f].map.extent_local_m;
    if (G.tiles.length !== 16 || !/carries no text/.test(G.label)) tb.push(f + ' count/label');
    for (const t of G.tiles) {
      if (!t.path.startsWith('bayarea/maps/tiles/') || !existsSync(join(ROOT, t.path))) { tb.push(t.path + ' missing'); continue; }
      const b = buf(t.path); const d = webpSize(b);
      if (!d || d[0] !== 1024 || d[1] !== 1024 || sha(b) !== t.sha256 || b.length !== t.bytes || b.length > 400000) tb.push(t.path + ' dims/sha/bytes');
    }
    const L = Math.min(...G.tiles.map((t) => t.bounds_local_m.left)), Rr = Math.max(...G.tiles.map((t) => t.bounds_local_m.right));
    if (Math.abs(L - ex.left) > 0.01 || Math.abs(Rr - ex.right) > 0.01) tb.push(f + ' union');
  }
  ok(tb.length === 0, `[tiles] 16 label-free 1024^2 ground tiles per county under bayarea/maps/tiles/, <= 400,000 B, sha as recorded, union = map extent${tb.length ? ' [' + tb.slice(0, 3).join('; ') + ']' : ''}`);
}


/* ---- district maps ---------------------------------------------------- */
{
  const bad = [];
  for (const f of IDS) {
    const m = C[f].map.districts_map;
    if (!m || m.path !== `bayarea/maps/districts/${f}-4k.webp` || !existsSync(join(ROOT, m.path))) { bad.push(f + ' missing'); continue; }
    const b = buf(m.path); const d = webpSize(b);
    if (!d || d[0] !== 4096 || d[1] !== 4096 || sha(b) !== m.sha256 || b.length !== m.bytes || b.length > 2000000) bad.push(f + ' dims/sha/bytes');
    if (!/AUTHORED/.test(m.label) || !/NOT official neighbourhoods/.test(m.label) || !/^AUTHORED/.test(m.provenance)) bad.push(f + ' label');
  }
  ok(bad.length === 0, `[dmaps] every county has a 4096^2 AUTHORED district map (<= 2,000,000 B, sha as recorded) labelled NOT official neighbourhoods${bad.length ? ' [' + bad.slice(0, 3).join('; ') + ']' : ''}`);
}

/* ---- streets (PARISH v1.3 format) ------------------------------------ */
{
  const bad = []; let n = 0;
  for (const f of IDS) {
    const s = C[f].map.streets;
    if (s.path !== `bayarea/maps/streets/${f}.json` || !existsSync(join(ROOT, s.path))) { bad.push(f + ' missing'); continue; }
    const b = buf(s.path);
    if (sha(b) !== s.sha256 || b.length !== s.bytes || b.length > 1500000) bad.push(f + ' sha/bytes');
    const D = JSON.parse(b.toString('utf8'));
    if (D.pack !== 'bayarea' || D.provenance !== 'AUTHORED' || D.fips !== f || D.source_stamp !== R.source_stamp
        || !['arterial', 'collector', 'local'].every((k) => Array.isArray(D.classes[k]))) bad.push(f + ' shape');
    for (const k of ['arterial', 'collector', 'local']) for (const pl of D.classes[k]) for (const v of pl) {
      n++; if (!inPolys(v, C[f].outline_local_m)) { bad.push(f + ' vertex outside'); break; }
    }
  }
  ok(bad.length === 0 && n > 0, `[streets] AUTHORED street polylines per county in PARISH v1.3 format (pack bayarea, classes arterial|collector|local), <= 1.5 MB, every one of ${n} vertices inside the RECORDED outline${bad.length ? ' [' + bad.slice(0, 3).join('; ') + ']' : ''}`);
}


/* ---- world layer (PARISH v1.4 format) -------------------------------- */
{
  const WP = 'bayarea/registry/world.json';
  const W = existsSync(join(ROOT, WP)) ? J(WP) : null;
  const PWR = J('parishes/registry/world.json');
  const bad = [];
  if (!W) bad.push('world.json missing');
  else {
    if (W.pack !== 'bayarea' || W.version !== PWR.version || JSON.stringify(Object.keys(W.counties).sort()) !== JSON.stringify(IDS)) bad.push('shape');
    if (JSON.stringify(W.buildings.hash_vectors) !== JSON.stringify(PWR.buildings.hash_vectors) || JSON.stringify(W.roads) !== JSON.stringify(PWR.roads)) bad.push('rule drift from parishes');
    for (const f of IDS) {
      const e = W.counties[f];
      if (!existsSync(join(ROOT, e.path))) { bad.push(f + ' missing'); continue; }
      const b = buf(e.path);
      if (sha(b) !== e.sha256 || b.length !== e.bytes || b.length > 600000) bad.push(f + ' sha/bytes');
      const D = JSON.parse(b.toString('utf8'));
      if (D.pack !== 'bayarea' || D.water.provenance !== 'AUTHORED' || D.counts.bayou !== 0 || D.water.lakes.length !== 0) bad.push(f + ' water');
      if (D.roads.streets_sha256 !== C[f].map.streets.sha256) bad.push(f + ' streets link');
      for (const ch of D.water.channels) for (const v of ch.centre) if (!inPolys(v, C[f].outline_local_m)) { bad.push(f + ' channel outside'); break; }
    }
  }
  ok(bad.length === 0, `[world] AUTHORED water/roads world files per county in the PARISH v1.4 shape (no bayous, no lake stand-ins, channels inside outlines, roads/building rule identical to parishes)${bad.length ? ' [' + bad.slice(0, 3).join('; ') + ']' : ''}`);
}


/* ---- satellite: declared, view-time only ------------------------------ */
{
  const S = R.satellite; const img = J('parcels/registry/parcels.json').imagery;
  ok(S.fetched_at_build === false && S.stored === false && S.usgs.tiles === img.tiles && S.usgs.attribution === img.attribution
     && S.mapbox.configured_here === false && S.mapbox.refusal_text === 'Mapbox satellite: off - no token configured',
    '[satellite] USGS imagery is the parcels/ declaration, view-time only, never fetched or stored; Mapbox off without a token');
  ok(/NOT recorded/.test(R.borders_note) && /water crossing/.test(R.borders_note),
    '[borders] the registry says land/water along shared borders is not recorded and names the bay crossing');
}


/* ---- parish-shaped view for the page machinery ------------------------ */
{
  const r = spawnSync('python3', [join(ROOT, 'bayarea/page_view.py'), '--check'], { encoding: 'utf8' });
  let v = null; try { v = JSON.parse(r.stdout); } catch { v = null; }
  ok(r.status === 0 && v && JSON.stringify(v.ids) === JSON.stringify(IDS) && v.names.every((n) => / County$/.test(n))
     && JSON.stringify(v.kinds) === JSON.stringify(['campus', 'city', 'restoration site']) && v.stamp === R.source_stamp,
    `[pageview] bayarea/page_view.py maps the Bay registries onto every key web/build_parishes.py reads (${v ? v.ids.length : 0} counties, pins kinds campus|city|restoration site)${r.status ? ' [' + (r.stderr || '').trim().slice(0, 120) + ']' : ''}`);
}


/* ---- Natural Earth shoreline (RECORDED, coarse) ------------------------- */
{
  const man = J('terrain/vendor/manifest.json'); const N = R.natural_earth; const bad = [];
  for (const layer of ['coastline', 'rivers']) {
    const L = N.layers[layer]; const f = L && L.file;
    if (!L || sha(buf(f)) !== man.files[f.split('/').pop()].sha256 || L.sha256 !== man.files[f.split('/').pop()].sha256) { bad.push(layer + ' sha'); continue; }
    const src = J(f).campuses.oakland.features.flatMap((ft) => (ft.geometry.type === 'MultiLineString' ? ft.geometry.coordinates : [ft.geometry.coordinates]));
    if (src.length !== L.lines || src.reduce((s, l) => s + l.length, 0) !== L.vertices) bad.push(layer + ' counts');
  }
  ok(bad.length === 0 && /^RECORDED at Natural Earth/.test(N.provenance) && /public domain/.test(N.licence),
    `[naturalearth] the NE 1:10m coastline (${N.layers.coastline.vertices} vertices) and rivers are carried from the vendored public-domain clip, sha-checked, tagged RECORDED coarse${bad.length ? ' [' + bad.join('; ') + ']' : ''}`);
}

/* ---- no fetch -------------------------------------------------------- */
{
  const src = ['bayarea/build.py', 'bayarea/render_bay.py', 'bayarea/world_bay.py', 'bayarea/page_view.py', 'bayarea/districts_map.py'].map((p) => buf(p).toString());
  const hostile = /https?:\/\/|urllib|requests\.|http\.client|socket|fetch\(/;
  ok(src.every((s) => !hostile.test(s)) && /^none/.test(R.fetches),
    '[nofetch] the builders name no URL and import no network client; the registry says nothing was fetched');
}

console.log(`\n${pass} ok, ${fail} FAIL`);
process.exit(fail ? 1 : 0);
