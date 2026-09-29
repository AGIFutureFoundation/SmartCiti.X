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
import { fileURLToPath, pathToFileURL } from 'node:url';
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


/* ---- wave 6: label-free ground tiles ---------------------------------- */
{
  const GL = 'Ground drawn from Census outline + AUTHORED fabric - not satellite, not a survey; carries no text';
  const cover = [], files = [], dims = [];
  for (const f of IDS) {
    const m = P[f].map, G = m.ground_tiles, X = m.extent_local_m;
    if (!G || G.grid !== 4 || G.tile_px !== 1024 || G.tiles.length !== 16) { cover.push(`${f} grid`); continue; }
    const at = (r, c) => G.tiles.filter((t) => t.row === r && t.col === c);
    for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) {
      const t = at(r, c);
      if (t.length !== 1) { cover.push(`${f} r${r}c${c} x${t.length}`); continue; }
      const b = t[0].bounds_local_m, T = t[0];
      if (c === 0 && b.left !== X.left) cover.push(`${f} r${r}c0 west edge ${b.left} != ${X.left}`);
      if (c === 3 && b.right !== X.right) cover.push(`${f} r${r}c3 east edge`);
      if (r === 0 && b.top !== X.top) cover.push(`${f} r0c${c} north edge`);
      if (r === 3 && b.bottom !== X.bottom) cover.push(`${f} r3c${c} south edge`);
      if (c < 3 && at(r, c + 1).length === 1 && at(r, c + 1)[0].bounds_local_m.left !== b.right) cover.push(`${f} r${r}c${c} gap/overlap east`);
      if (r < 3 && at(r + 1, c).length === 1 && at(r + 1, c)[0].bounds_local_m.top !== b.bottom) cover.push(`${f} r${r}c${c} gap/overlap south`);
      if (!(b.left < b.right && b.bottom < b.top) || Math.abs((b.right - b.left) - (X.right - X.left) / 4) > 0.02
          || Math.abs((b.top - b.bottom) - (X.top - X.bottom) / 4) > 0.02) cover.push(`${f} r${r}c${c} size`);
      if (JSON.stringify(T.px_bounds) !== JSON.stringify([c * 1024, r * 1024, c * 1024 + 1024, r * 1024 + 1024])) cover.push(`${f} r${r}c${c} px`);
      if (T.path !== `parishes/maps/tiles/${f}-r${r}c${c}.webp`) cover.push(`${f} r${r}c${c} path`);
      if (!existsSync(join(ROOT, T.path))) { files.push(`${T.path} missing`); continue; }
      const B = buf(T.path);
      if (sha(B) !== T.sha256 || B.length !== T.bytes) files.push(`${T.path} sha/bytes`);
      if (T.bytes > 400000 || G.max_bytes !== 400000) files.push(`${T.path} ${T.bytes} B over 400,000`);
      const d = webpSize(B);
      if (!d || d[0] !== 1024 || d[1] !== 1024) dims.push(`${T.path} is ${d}`);
    }
  }
  ok(cover.length === 0, `[tiles] every parish's 4x4 ground tiles cover map.extent_local_m exactly: outer edges equal the extent, shared edges are equal numbers (no gaps, no overlaps), one tile per cell${cover.length ? ' [' + cover.slice(0, 4).join('; ') + ']' : ''}`);
  ok(files.length === 0 && dims.length === 0, `[tiles] every ground tile file exists at 1024x1024 (WebP header), matches its recorded sha256 and bytes, and is at most 400,000 bytes (largest ${Math.max(...IDS.flatMap((f) => P[f].map.ground_tiles ? P[f].map.ground_tiles.tiles.map((t) => t.bytes) : [0]))})${files.concat(dims).length ? ' [' + files.concat(dims).slice(0, 4).join('; ') + ']' : ''}`);
  ok(IDS.every((f) => P[f].map.ground_tiles && P[f].map.ground_tiles.label === GL && /no text/.test(P[f].map.ground_tiles.provenance)),
    '[tiles] every tile set records the AUTHORED ground label ("... carries no text") for the page to show beside the 3D ground');
  const rs = buf('parishes/render.py').toString();
  const snap = rs.indexOf('ground = img.copy()'), firstText = rs.indexOf('d.text(', rs.indexOf('def render_all('));
  const firstLine = rs.indexOf("fill=COL['ink'], width=7", rs.indexOf('def render_all('));
  ok(snap > 0 && firstText > snap && firstLine > snap && /save_ground_tiles\(ground,/.test(rs)
     && rs.includes("GROUND_LABEL = '" + GL + "'"),
    '[tiles] the renderer snapshots the ground layer before ANY text, pin, outline, border, banner or legend is drawn and cuts tiles only from that snapshot (no labels draped on the ground)');
}

/* ---- wave 6: AUTHORED street polylines -------------------------------- */
{
  const bad = [], out = [], size = [], cls = [];
  let nPl = 0, nV = 0, total = 0;
  for (const f of IDS) {
    const S = P[f].map.streets;
    if (!S || S.path !== `parishes/maps/streets/${f}.json` || !existsSync(join(ROOT, S.path))) { bad.push(`${f} missing`); continue; }
    const B = buf(S.path);
    total += B.length;
    if (sha(B) !== S.sha256 || B.length !== S.bytes) bad.push(`${f} sha/bytes`);
    if (B.length > 1500000 || S.max_bytes !== 1500000) size.push(`${f} ${B.length} B`);
    const D = JSON.parse(B.toString());
    if (D.source_stamp !== R.source_stamp || D.fips !== f || D.pack !== 'parishes') bad.push(`${f} stamp ${D.source_stamp}`);
    if (D.provenance !== 'AUTHORED' || !/NOT the real street grid/.test(D.note) || !/INLAND water is NOT cut out/.test(D.inside_rule)) cls.push(`${f} label`);
    if (JSON.stringify(Object.keys(D.classes)) !== '["arterial","collector","local"]') cls.push(`${f} classes`);
    for (const k of ['arterial', 'collector', 'local']) {
      const L = D.classes[k] || [];
      if (L.length !== D.counts[k] || L.length !== S.counts[k]) cls.push(`${f} ${k} count`);
      if (k !== 'local' && L.length === 0) cls.push(`${f} no ${k}`);
      for (const pl of L) {
        nPl++;
        if (!Array.isArray(pl) || pl.length < 2) { cls.push(`${f} ${k} short`); continue; }
        for (const q of pl) {
          nV++;
          if (!Number.isInteger(q[0]) || !Number.isInteger(q[1])) { cls.push(`${f} ${k} non-integer`); break; }
          if (!inPolys(q, P[f].outline_local_m)) { out.push(`${f} ${k} [${q}]`); break; }
        }
      }
    }
    if (D.vertices !== S.vertices) cls.push(`${f} vertices`);
  }
  ok(bad.length === 0, `[streets] every parish has parishes/maps/streets/<fips>.json matching the registry's sha256 and bytes, stamped with the registry source_stamp${bad.length ? ' [' + bad.slice(0, 4).join('; ') + ']' : ''}`);
  ok(size.length === 0 && total <= 13 * 1500000, `[streets] byte budget: each streets file <= 1,500,000 bytes (total ${total})${size.length ? ' [' + size.join('; ') + ']' : ''}`);
  ok(cls.length === 0, `[streets] ${nPl} polylines / ${nV} vertices: classes arterial|collector|local with matching counts, integer metres, every parish has arterials and collectors, labelled AUTHORED / NOT the real street grid${cls.length ? ' [' + cls.slice(0, 4).join('; ') + ']' : ''}`);
  ok(out.length === 0, `[streets] every polyline vertex lies inside its parish's RECORDED outline (local metres, holes honoured); inland water not cut out is recorded in inside_rule${out.length ? ' [outside: ' + out.slice(0, 4).join('; ') + ']' : ''}`);
}

/* ---- wave 7 (contract v1.4): the WORLD LAYER - AUTHORED water, road profiles, building page-rule ---- */
{
  const WREG = 'parishes/registry/world.json';
  const have = existsSync(join(ROOT, WREG));
  ok(have, '[world] parishes/registry/world.json exists (python3 parishes/build_world.py)');
  const W = have ? J(WREG) : { parishes: {}, roads: { classes: {} }, buildings: {}, water_levels: { depth_m: {} } };
  // stamp: recomputed from the bytes it claims to cover
  const h = createHash('sha256'); h.update(buf(REG));
  for (const f of IDS) h.update(buf(P[f].map.streets.path));
  h.update(buf('parishes/build_world.py'));
  const stamp = h.digest('hex');
  const bad = [], size = [], prov = [], geo = [], lk = [], pd = [], rd = [];
  let nCh = 0, nV = 0, nPond = 0, total = 0;
  if (W.version !== '1.4' || W.source_stamp !== stamp) bad.push(`registry stamp ${String(W.source_stamp).slice(0, 16)} vs ${stamp.slice(0, 16)}`);
  if (JSON.stringify(Object.keys(W.parishes).sort()) !== JSON.stringify(IDS)) bad.push('parish set');
  const DEP = W.water_levels.depth_m, WID = { bayou: [14, 30], canal: [18, 24], stream: [4, 8] };
  const R0 = 6371008.8, rad = Math.PI / 180;
  for (const f of IDS) {
    const E = W.parishes[f];
    if (!E || E.path !== `parishes/maps/world/${f}.json` || !existsSync(join(ROOT, E.path))) { bad.push(`${f} missing`); continue; }
    const B = buf(E.path); total += B.length;
    if (sha(B) !== E.sha256 || B.length !== E.bytes) bad.push(`${f} sha/bytes`);
    if (B.length > 600000 || E.max_bytes !== 600000) size.push(`${f} ${B.length} B`);
    const D = JSON.parse(B.toString());
    if (D.source_stamp !== stamp.slice(0, 16) || D.fips !== f || D.version !== '1.4') bad.push(`${f} stamp ${D.source_stamp}`);
    if (JSON.stringify(D.counts) !== JSON.stringify(E.counts)) bad.push(`${f} counts`);
    // provenance: every water feature AUTHORED, nothing RECORDED
    if (D.water.provenance !== 'AUTHORED' || !/NOT the real lakes, rivers or bayous/.test(D.water.note)) prov.push(`${f} water label`);
    for (const x of [...D.water.lakes, ...D.water.channels, ...D.water.ponds]) if (x.provenance !== 'AUTHORED') prov.push(`${f} ${x.id} ${x.provenance}`);
    if (/"RECORDED"/.test(B.toString())) prov.push(`${f} RECORDED tag`);
    // channels: kind, width, depth, integer centre inside the outline, ribbon = 2 x centre
    const kc = { bayou: 0, canal: 0, stream: 0 };
    for (const c of D.water.channels) {
      nCh++;
      if (!(c.kind in WID) || c.width_m < WID[c.kind][0] || c.width_m > WID[c.kind][1] || c.depth_m !== DEP[c.kind]) geo.push(`${f} ${c.id} kind/width/depth`);
      else kc[c.kind]++;
      if (c.centre.length < 3 || c.polygon.length !== 2 * c.centre.length) geo.push(`${f} ${c.id} ribbon`);
      for (const q of c.centre) { nV++; if (!Number.isInteger(q[0]) || !Number.isInteger(q[1]) || !inPolys(q, P[f].outline_local_m)) { geo.push(`${f} ${c.id} [${q}]`); break; } }
    }
    for (const k of Object.keys(kc)) if (kc[k] !== D.counts[k] || kc[k] === 0) geo.push(`${f} ${k} count ${kc[k]}`);
    if (D.counts.channel_vertices !== D.water.channels.reduce((a, c) => a + c.centre.length, 0)) geo.push(`${f} channel_vertices`);
    // lakes: only where registry water.labels puts a named lake in THIS outline; centre = LTP of the label point
    const want = R.water.labels.filter((L) => L.inside_outline_of.includes(f));
    if (D.water.lakes.length !== want.length || D.counts.lakes !== want.length) lk.push(`${f} ${D.water.lakes.length} vs ${want.length}`);
    D.water.lakes.forEach((L, i) => {
      const w = want[i]; if (!w) return;
      const o = P[f].frame.origin;
      const e = R0 * Math.cos(o.lat * rad) * (w.lng - o.lng) * rad, n = R0 * (w.lat - o.lat) * rad;
      if (L.name !== w.name || Math.hypot(L.centre[0] - e, L.centre[1] - n) > 1 || !inPolys(L.centre, P[f].outline_local_m)
          || !/AUTHORED, NOT the shoreline/.test(L.basis) || L.depth_m !== DEP.lake) lk.push(`${f} ${L.name}`);
    });
    // ponds: centre inside, no street segment closer than the radius (they sit in the gaps the maps leave)
    const segs = [];
    const S = J(P[f].map.streets.path);
    for (const k of Object.keys(S.classes)) for (const pl of S.classes[k]) for (let i = 1; i < pl.length; i++) segs.push([pl[i - 1], pl[i]]);
    const dseg = (p, a, b) => { const dx = b[0] - a[0], dy = b[1] - a[1], L2 = dx * dx + dy * dy || 1; const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2)); return Math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy); };
    for (const q of D.water.ponds) {
      nPond++;
      if (!inPolys(q.centre, P[f].outline_local_m) || q.depth_m !== DEP.pond || q.polygon.length < 8) { pd.push(`${f} ${q.id}`); continue; }
      for (const [a, b] of segs) if (dseg(q.centre, a, b) <= q.radius_m) { pd.push(`${f} ${q.id} street at <= r`); break; }
    }
    if (D.water.ponds.length !== D.counts.ponds) pd.push(`${f} pond count`);
    // roads: the file's profile = the registry's, and it points at the v1.3 streets file by sha
    if (JSON.stringify(D.roads.classes) !== JSON.stringify(W.roads.classes) || D.roads.streets_path !== P[f].map.streets.path
        || D.roads.streets_sha256 !== P[f].map.streets.sha256 || D.roads.profile_version !== W.roads.profile_version) rd.push(`${f} roads ref`);
    if (D.buildings.mode !== 'page-rule') rd.push(`${f} buildings mode`);
  }
  if (!/NO water feature is RECORDED/.test(W.water_source) || !/@geo-maps\/\* excluded/.test(W.water_source)) prov.push('water_source statement');
  if (existsSync(join(ROOT, 'parishes/vendor/@geo-maps')) || existsSync(join(ROOT, 'parishes/vendor/geo-maps'))) prov.push('ODbL @geo-maps vendored');
  for (const [k, c] of Object.entries(W.roads.classes)) {
    const need = ['lanes', 'lane_width_m', 'parking_lanes', 'parking_width_m', 'carriageway_m', 'curb_height_m', 'sidewalk_m', 'corridor_m', 'provenance'];
    if (need.some((x) => !(x in c)) || c.provenance !== 'AUTHORED') { rd.push(`${k} fields`); continue; }
    if (Math.abs(c.carriageway_m - (c.lanes * c.lane_width_m + c.parking_lanes * c.parking_width_m)) > 0.01) rd.push(`${k} carriageway`);
    if (c.sidewalk_m.length !== 2 || Math.abs(c.corridor_m - (c.carriageway_m + c.sidewalk_m[0] + c.sidewalk_m[1])) > 0.01) rd.push(`${k} corridor`);
    if (!(c.lanes >= 1 && c.curb_height_m > 0 && c.curb_height_m <= 0.3 && c.sidewalk_m[0] > 0 && c.sidewalk_m[1] > 0)) rd.push(`${k} ranges`);
  }
  if (JSON.stringify(Object.keys(W.roads.classes)) !== '["arterial","collector","local"]') rd.push('road classes');
  ok(bad.length === 0, `[world] registry v1.4 source_stamp recomputed from parishes.json + streets + build_world.py; every parishes/maps/world/<fips>.json matches its sha256/bytes/counts and carries the stamp${bad.length ? ' [' + bad.slice(0, 4).join('; ') + ']' : ''}`);
  ok(size.length === 0, `[world] byte budget: each world file <= 600,000 bytes (total ${total})${size.length ? ' [' + size.join('; ') + ']' : ''}`);
  ok(prov.length === 0, `[world] water provenance: no public-domain source verified, so every lake/channel/pond is AUTHORED, nothing RECORDED, water legend "NOT the real lakes, rivers or bayous", no ODbL @geo-maps vendored${prov.length ? ' [' + prov.slice(0, 4).join('; ') + ']' : ''}`);
  ok(geo.length === 0, `[world] ${nCh} channels / ${nV} centre vertices: bayou|canal|stream with AUTHORED width range and depth, integer centre inside the RECORDED outline, ribbon polygon 2x centre${geo.length ? ' [' + geo.slice(0, 4).join('; ') + ']' : ''}`);
  ok(lk.length === 0, `[world] lake stand-ins only where registry water.labels names a lake inside the outline, centred on the label's LTP point (<= 1 m), basis "AUTHORED, NOT the shoreline"${lk.length ? ' [' + lk.slice(0, 4).join('; ') + ']' : ''}`);
  ok(pd.length === 0, `[world] ${nPond} ponds inside the outline with no street segment within their radius${pd.length ? ' [' + pd.slice(0, 4).join('; ') + ']' : ''}`);
  ok(rd.length === 0, `[world] road profiles arterial|collector|local AUTHORED: carriageway = lanes*lane + parking, corridor = carriageway + both sidewalks, curb 0-0.3 m; each world file references its streets file by sha256${rd.length ? ' [' + rd.slice(0, 4).join('; ') + ']' : ''}`);
  // buildings: the published rule matches the page and the hash
  const page = buf('web/build_parishes.py').toString(), C = W.buildings.constants || {};
  const { wildsHash } = await import(pathToFileURL(join(ROOT, 'wilds/core.mjs')).href);
  const vec = (W.buildings.hash_vectors || []).filter((v) => wildsHash(...v.args) === v.value);
  const pageOk = new RegExp(`CHUNK_M = ${C.CHUNK_M}\\b`).test(page) && new RegExp(`CELL = ${C.CELL}\\b`).test(page)
    && new RegExp(`DISTRICT_M = ${C.DISTRICT_M}\\b`).test(page) && new RegExp(`SEED = ${C.SEED}\\b`).test(page)
    && /h < 0\.55\) out\.block\.push\(kitLot\(/.test(page) && /function kitLot\(/.test(page);
  ok(W.buildings.mode === 'page-rule' && pageOk && vec.length >= 6 && vec.length === W.buildings.hash_vectors.length && /h < 0\.55/.test(W.buildings.rule),
    `[world] building rule: constants CELL/CHUNK_M/DISTRICT_M/SEED and the h < 0.55 kitLot rule match web/build_parishes.py; ${vec.length} wildsHash vectors reproduce wilds/core.mjs`);
  const bw = buf('parishes/build_world.py').toString();
  ok(!/\.get\(/.test(bw) && !/\?\?/.test(bw) && /raise SystemExit\(f'build_world: missing/.test(bw),
    '[world] build_world.py fails closed: no .get() defaults, missing fields raise a named error');
}

console.log(`\n${pass} ok, ${fail} FAIL`);
process.exit(fail ? 1 : 0);
