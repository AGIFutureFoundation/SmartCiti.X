/* parishes/test.mjs — the parish geographic base, checked. Browser-free, network-free.
 *
 * Recompute, never re-read: the parish selection is recomputed from the
 * vendored topojson and the RECORDED NOLA frame; counts, areas and metre
 * frames are recomputed from the entries; shared borders are checked vertex
 * by vertex against BOTH outlines; landmarks are point-in-polygon tested;
 * map dimensions are read from the WebP header bytes. Each check carries a
 * [tag] that the mutation harness greps for.
 */
import { readFileSync, existsSync, statSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m); } };
const buf = (p) => readFileSync(join(ROOT, p));
const J = (p) => JSON.parse(buf(p).toString('utf8'));
const sha = (b) => createHash('sha256').update(b).digest('hex');

console.log('parishes/test.mjs');
const REG = 'parishes/registry/parishes.json';
ok(existsSync(join(ROOT, REG)), '[registry] parishes/registry/parishes.json exists');
if (!existsSync(join(ROOT, REG))) { console.log(`\n${pass} ok, ${fail} FAIL`); process.exit(1); }
const R = J(REG);
const P = R.parishes;
const IDS = Object.keys(P).sort();
const GEO = J('geo/registry/campuses_geo.json');
const R_M = 6371008.8;

/* ---- stamp ---------------------------------------------------------- */
{
  const h = createHash('sha256');
  for (const p of R.inputs) { h.update(p + '\0'); h.update(buf(p)); h.update('\0'); }
  const d = h.digest('hex');
  const want = ['parishes/build.py', 'parishes/render.py', 'parishes/vendor/us-atlas/counties-10m.json',
    'parishes/vendor/us-atlas/manifest.json', 'geo/registry/campuses_geo.json', 'parcels/registry/parcels.json',
    'parishes/authored/landmarks.json'];
  ok(JSON.stringify(R.inputs) === JSON.stringify(want) && d.slice(0, 16) === R.source_stamp && d === R.source_stamp_sha256,
    `[stamp] source_stamp ${R.source_stamp} is current over the ${want.length} inputs (builder, renderer, vendored data, registries, authored landmarks)`);
}
ok(R.pack === 'parishes' && R.pack_version === J('pack/manifest.json').pack_version,
  '[stamp] the registry names its pack and the bundle version read from pack/manifest.json');

/* ---- licence + vendor ----------------------------------------------- */
{
  const man = J('parishes/vendor/us-atlas/manifest.json');
  const lic = existsSync(join(ROOT, 'parishes/vendor/us-atlas/LICENSE'))
    ? buf('parishes/vendor/us-atlas/LICENSE').toString() : '';
  ok(/Copyright 2013-2019 Michael Bostock/.test(lic) && /Permission to use, copy, modify/.test(lic)
     && man.license === 'ISC' && man.package === 'us-atlas' && man.version === '3.0.1',
    '[licence] the us-atlas ISC licence text is vendored beside the data, and the manifest names us-atlas 3.0.1 ISC');
  const files = Object.keys(man.files).sort();
  ok(files.join(',') === 'LICENSE,counties-10m.json'
     && files.every((f) => existsSync(join(ROOT, 'parishes/vendor/us-atlas', f))
       && sha(buf('parishes/vendor/us-atlas/' + f)) === man.files[f].sha256)
     && /^sha512-/.test(man.integrity) && /matched the registry dist.integrity/.test(man.integrity_verified),
    '[licence] every vendored file matches the sha256 recorded when the tarball sha512 was verified against the registry integrity');
  const third = buf('THIRD_PARTY.md').toString();
  ok(third.includes('us-atlas 3.0.1') && third.includes('parishes/vendor/us-atlas/'),
    '[licence] THIRD_PARTY.md credits us-atlas 3.0.1 and says where it lives');
}

/* ---- topojson decode (recompute from the vendored bytes) ------------- */
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
  const C = [[f.w, f.s], [f.e, f.s], [f.e, f.n], [f.w, f.n]];
  return polys.some(([outer]) => outer.some(([x, y]) => f.w <= x && x <= f.e && f.s <= y && y <= f.n)
    || C.some((c) => pip(c, outer))
    || outer.some((a, i) => C.some((c, j) => cross(a, outer[(i + 1) % outer.length], c, C[(j + 1) % 4]))));
};

/* ---- frame intersection --------------------------------------------- */
{
  const F = GEO.city['new-orleans'].bounds;
  ok(JSON.stringify(R.nola_frame.bounds) === JSON.stringify(F) && GEO.city['new-orleans'].provenance === 'RECORDED',
    `[frame] the frame is the RECORDED geo registry city.new-orleans.bounds (${F.w}, ${F.s}, ${F.e}, ${F.n})`);
  const hits = TOPO.objects.counties.geometries.filter((g) => meetsFrame(polysOf(g), F));
  const la = hits.filter((g) => g.id.startsWith('22')).map((g) => g.id).sort();
  const other = hits.filter((g) => !g.id.startsWith('22')).map((g) => g.id).sort();
  ok(JSON.stringify(la) === JSON.stringify(IDS) && JSON.stringify(R.selection.selected.slice().sort()) === JSON.stringify(la),
    `[frame] recomputed from the vendored outlines: exactly these ${la.length} parishes meet the frame: ${la.join(' ')}`);
  ok(JSON.stringify(R.selection.excluded_non_parish.map((x) => x.fips).sort()) === JSON.stringify(other),
    `[frame] non-parish counties meeting the frame are recorded as excluded, not dropped silently: ${other.join(' ')}`);
  const byId = Object.fromEntries(TOPO.objects.counties.geometries.map((g) => [g.id, g]));
  ok(IDS.every((f) => JSON.stringify(P[f].outline.polygons) === JSON.stringify(polysOf(byId[f])) && P[f].name === byId[f].properties.name),
    '[frame] every outline and name equals the vendored Census outline, vertex for vertex (RECORDED, not redrawn)');
}

/* ---- counts --------------------------------------------------------- */
{
  const C = R.counts;
  const adjPairs = IDS.reduce((s, f) => s + P[f].adjacent.length, 0) / 2;
  const lm = IDS.reduce((s, f) => s + P[f].landmarks.length, 0);
  const an = IDS.reduce((s, f) => s + P[f].anchors.length, 0);
  const mp = IDS.filter((f) => P[f].map && P[f].map.path).length;
  ok(C.parishes === IDS.length && C.adjacency_pairs === adjPairs && C.landmarks === lm && C.anchors === an
     && C.maps_4k === mp && C.excluded_non_parish === R.selection.excluded_non_parish.length
     && C.landmarks_dropped === R.landmarks_dropped.length,
    `[counts] every count recomputed from the entries: ${IDS.length} parishes, ${adjPairs} adjacency pairs, ${lm} landmarks, ${an} anchors, ${mp} maps`);
  const authored = J('parishes/authored/landmarks.json').landmarks.length;
  ok(lm + R.landmarks_dropped.length === authored,
    `[counts] kept + dropped landmarks = the ${authored} authored (none lost silently)`);
}

/* ---- metre frames + area ------------------------------------------- */
{
  const K = Math.PI / 180 * R_M;
  const fwd = (o) => ([lng, lat]) => [Math.round((lng - o.lng) * K * Math.cos(o.lat * Math.PI / 180) * 100) / 100, Math.round((lat - o.lat) * K * 100) / 100];
  let worst = 0;
  for (const f of IDS) {
    const g = fwd(P[f].frame.origin);
    P[f].outline.polygons.forEach((poly, i) => poly.forEach((ring, j) => ring.forEach((pt, k) => {
      const [e, n] = g(pt), [e2, n2] = P[f].outline_local_m[i][j][k];
      worst = Math.max(worst, Math.abs(e - e2), Math.abs(n - n2));
    })));
  }
  const ewErr = (f) => Math.round(1e5 * Math.max(...P[f].outline.polygons.flat(2).map(([, lat]) =>
    Math.abs(Math.cos(lat * Math.PI / 180) / Math.cos(P[f].frame.origin.lat * Math.PI / 180) - 1)))) / 1e3;
  ok(IDS.every((f) => Math.abs(ewErr(f) - P[f].frame.max_ew_scale_error_pct) <= 0.0011),
    `[ltp] each parish's east-west scale error is recomputed, not typed (worst ${Math.max(...IDS.map(ewErr)).toFixed(3)} %)`);
  ok(worst <= 0.011 && R.frames.R_m === R_M && /R = 6371008.8 m/.test(R.frames.ltp_formula),
    `[ltp] every local_m vertex recomputed from WGS84 with the stated formula and geo3d's R (worst ${worst.toFixed(3)} m)`);
  const area = (r) => r.reduce((s, [x1, y1], i) => { const [x2, y2] = r[(i + 1) % r.length]; return s + x1 * y2 - x2 * y1; }, 0) / 2;
  ok(IDS.every((f) => Math.abs(P[f].outline_local_m.reduce((s, poly) => s + Math.abs(area(poly[0]))
      - poly.slice(1).reduce((t, h) => t + Math.abs(area(h)), 0), 0) / 1e6 - P[f].area_km2) <= 0.051),
    '[area] every area_km2 recomputed by shoelace from the local metre outline');
  {
    const w = fwd(R.frames.world.origin);
    let worstW = 0;
    for (const f of IDS) P[f].outline.polygons.forEach((poly, i) => poly.forEach((ring, j) => ring.forEach((pt, k) => {
      const [e, n] = w(pt), [e2, n2] = P[f].outline_world_m[i][j][k];
      worstW = Math.max(worstW, Math.abs(e - e2), Math.abs(n - n2));
    })));
    ok(worstW <= 0.011, `[ltp] every outline_world_m vertex recomputed in the shared world frame (worst ${worstW.toFixed(3)} m)`);
  }
  const W = R.frames.world.origin, c = GEO.city['new-orleans'].center;
  ok(W.lat === c.lat && W.lng === c.lng, '[ltp] the world frame origin is the RECORDED city.new-orleans.center');
}

/* ---- adjacency + shared borders ------------------------------------ */
ok(IDS.every((a) => P[a].adjacent.every((b) => P[b] && P[b].adjacent.includes(a))),
  '[adjacency] adjacency is symmetric: every a->b has b->a');
ok(IDS.every((a) => P[a].adjacent.length === P[a].borders.length
     && P[a].borders.every((b) => P[a].adjacent.includes(b.with))),
  '[adjacency] each adjacent parish has exactly one borders entry');
{
  const verts = (f) => new Set(P[f].outline.polygons.flat(2).map(([x, y]) => x + ',' + y));
  const V = Object.fromEntries(IDS.map((f) => [f, verts(f)]));
  const bad = [];
  for (const a of IDS) for (const b of P[a].borders) {
    const other = P[b.with].borders.find((x) => x.with === a);
    const arcsA = b.segments.map((s) => s.arc).sort().join(), arcsB = other ? other.segments.map((s) => s.arc).sort().join() : '';
    if (arcsA !== arcsB) bad.push(`${a}-${b.with}: arcs differ`);
    for (const s of b.segments) {
      if (JSON.stringify(s.wgs84) !== JSON.stringify(ARCS[s.arc])) bad.push(`${a}-${b.with} arc ${s.arc}: not the topojson arc`);
      if (!s.wgs84.every(([x, y]) => V[a].has(x + ',' + y) && V[b.with].has(x + ',' + y))) bad.push(`${a}-${b.with} arc ${s.arc}: a point is not a vertex of both outlines`);
      const tw = other && other.segments.find((t) => t.arc === s.arc);
      if (!tw || JSON.stringify(tw.world_m) !== JSON.stringify(s.world_m)) bad.push(`${a}-${b.with} arc ${s.arc}: world_m differs between sides`);
    }
  }
  ok(bad.length === 0, `[borders] shared borders really shared: every segment is the same topojson arc, a vertex run of BOTH outlines, identical in world_m from both sides${bad.length ? ' [' + bad.slice(0, 4).join('; ') + ']' : ''}`);
}

/* ---- landmarks + anchors ------------------------------------------- */
{
  const bad = [];
  for (const f of IDS) for (const L of P[f].landmarks.concat(P[f].anchors))
    if (!inPolys([L.lng, L.lat], P[f].outline.polygons)) bad.push(`${L.name} (${f})`);
  ok(bad.length === 0, `[landmarks] every landmark and anchor lies inside its own parish outline${bad.length ? ' [outside: ' + bad.join(', ') + ']' : ''}`);
  const note = 'public record, not surveyed; verify before relying';
  ok(IDS.every((f) => P[f].landmarks.every((L) => L.provenance === 'AUTHORED' && L.note === note && L.name && L.kind)),
    `[landmarks] every landmark is AUTHORED and carries the note "${note}"`);
  const A = GEO.anchors['new-orleans'];
  const got = IDS.flatMap((f) => P[f].anchors);
  ok(got.length === A.length && A.every((a) => got.some((g) => g.name === a.name && g.lat === a.lat && g.lng === a.lng
     && g.provenance === a.provenance && g.source === a.source)),
    `[landmarks] the ${A.length} RECORDED university anchors are carried with their own provenance and source`);
}

/* ---- maps ----------------------------------------------------------- */
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
    const m = P[f].map;
    for (const [p, px] of [[m.path, 4096], [m.preview, 512]]) {
      if (!existsSync(join(ROOT, p))) { bad.push(`${p} missing`); continue; }
      const d = webpSize(buf(p));
      if (!d || d[0] !== px || d[1] !== px) bad.push(`${p} is ${d}`);
    }
  }
  ok(bad.length === 0 && IDS.every((f) => P[f].map.path === `parishes/maps/${f}-4k.webp`),
    `[maps] every parish has parishes/maps/<fips>-4k.webp at 4096x4096 and a 512x512 preview (read from the WebP header)${bad.length ? ' [' + bad.join('; ') + ']' : ''}`);
  ok(IDS.every((f) => existsSync(join(ROOT, P[f].map.path)) && sha(buf(P[f].map.path)) === P[f].map.sha256
     && sha(buf(P[f].map.preview)) === P[f].map.preview_sha256 && statSync(join(ROOT, P[f].map.path)).size === P[f].map.bytes),
    '[maps] every map file matches the sha256 and byte count the registry recorded');
  ok(IDS.every((f) => P[f].map.bytes <= 2000000),
    `[maps] every 4k map is at most 2,000,000 bytes (largest ${Math.max(...IDS.map((f) => P[f].map.bytes))})`);
  ok(IDS.every((f) => P[f].map.label === 'Map drawn from Census outline + AUTHORED fabric - not satellite, not a survey'
     && /AUTHORED street fabric - procedural, NOT the real street grid/.test(P[f].map.fabric)),
    '[maps] every map records the on-image label and the AUTHORED fabric legend line');
  ok(IDS.every((f) => { const L = P[f].map.fabric_layers; return L && /AUTHORED procedural/.test(L.provenance)
       && /NOT the real street grid, land use or buildings/.test(L.provenance) && L.hillshade === false && L.arterials >= 3
       && JSON.stringify(L.land_use) === JSON.stringify(['residential', 'commercial', 'park', 'industrial']); }),
    '[fabric] every map records its AUTHORED city fabric layers (arterials, collectors, district grids, land use, building hints; no hillshade) as NOT the real city');
  const rsrc = buf('parishes/render.py').toString();
  ok(rsrc.includes("LABEL = 'Map drawn from Census outline + AUTHORED fabric - not satellite, not a survey'")
     && /d\.text\(\(48, 75\), LABEL/.test(rsrc) && /FABRIC_NOTE\)/.test(rsrc)
     && rsrc.includes("('landuse', 'AUTHORED land use: residential, commercial, park, industrial + building hints')"),
    '[maps] the renderer draws the label, the AUTHORED street-fabric and AUTHORED land-use legend lines onto the image itself');
}

/* ---- satellite ------------------------------------------------------ */
{
  const S = R.satellite, img = J('parcels/registry/parcels.json').imagery;
  ok(S.fetched_at_build === false && S.stored === false && S.usgs.tiles === img.tiles && S.usgs.attribution === img.attribution
     && S.usgs.source === 'parcels/registry/parcels.json#imagery',
    '[satellite] USGS orthoimagery is the parcels/ declaration, view-time only, never fetched or stored');
  ok(S.mapbox.refusal_text === 'Mapbox satellite: off - no token configured' && S.mapbox.configured_here === false
     && /never committed/.test(S.mapbox.token_from) && /\{token\}/.test(S.mapbox.tiles),
    '[satellite] Mapbox is gated on a deploy-time token, off here, with the refusal text verbatim');
  const blob = ['parishes/build.py', 'parishes/render.py', REG, 'parishes/authored/landmarks.json'].map((p) => buf(p).toString()).join('\n');
  ok(!/\b[ps]k\.[A-Za-z0-9_-]{20,}/.test(blob) && !/access_token=(?!\{token\})/.test(blob),
    '[satellite] no Mapbox token (pk./sk.) and no filled access_token appears in the pack');
}

/* ---- fail closed + honesty ----------------------------------------- */
{
  const src = buf('parishes/build.py').toString() + buf('parishes/render.py').toString();
  ok(!/\.get\(/.test(src) && !/\?\?/.test(src), '[failclosed] builder and renderer take no defaults (.get / ??): missing fields stop the build');
  ok(/no real elevation/.test(R.elevation) && /INLAND water is NOT cut out/.test(R.water.statement)
     && /Lake Pontchartrain/.test(R.water.statement) && /NOT proof of land/.test(R.water.statement)
     && R.water.inland_water_cut_out === false && /INCLUDES inland water/.test(P['22071'].area_note),
    '[honesty] water and elevation stated honestly: coastline-clipped outline, inland water (Lake Pontchartrain) NOT cut out, area includes it, no real elevation');
  ok(R.water.labels.length >= 1 && R.water.labels.every((w) => w.provenance === 'AUTHORED' && /NOT cut out/.test(w.note)
     && w.inside_outline_of.length >= 1 && w.inside_outline_of.every((f) => inPolys([w.lng, w.lat], P[f].outline.polygons))),
    `[honesty] the ${R.water.labels.length} inland-water labels are AUTHORED and really do fall inside a parish outline (the reason they are labelled)`);
  ok(/inland water \(lakes, river\) is NOT cut out at 1:10m/.test(buf('parishes/render.py').toString()),
    '[honesty] every map legend says inland water is not cut out and fabric over it is not land');
  ok(IDS.every((f) => /RECORDED/.test(P[f].outline.provenance) && /1:10,000,000/.test(P[f].outline.provenance) && /coarse/.test(P[f].outline.provenance)),
    '[honesty] every outline is labelled RECORDED, 1:10m and coarse');
}

console.log(`\n${pass} ok, ${fail} FAIL`);
process.exit(fail ? 1 : 0);
