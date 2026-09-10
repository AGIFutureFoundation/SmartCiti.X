/**
 * Geo registry verification.
 *
 * Coordinates are claims about the real world, so nothing is trusted: the
 * suite recomputes every distance and bearing from the stored coordinates,
 * validates the GeoJSON against its own spec's shape (lng,lat order — the
 * classic swap bug), and holds every point to its provenance discipline.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const reg = JSON.parse(readFileSync(new URL('./registry/campuses_geo.json', import.meta.url)));
const gj = JSON.parse(readFileSync(new URL('./registry/campuses.geojson', import.meta.url)));
const campuses = JSON.parse(readFileSync(new URL('../unions/registry/campuses.json', import.meta.url))).campuses;

const R = 6371.0088, rad = (d) => d * Math.PI / 180;
function haversineKm(a, b) {
  const dp = rad(b.lat - a.lat), dl = rad(b.lng - a.lng);
  const h = Math.sin(dp/2)**2
    + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dl/2)**2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
function bearingDeg(a, b) {
  const dl = rad(b.lng - a.lng);
  const y = Math.sin(dl) * Math.cos(rad(b.lat));
  const x = Math.cos(rad(a.lat)) * Math.sin(rad(b.lat))
    - Math.sin(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.cos(dl);
  return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
}

/* ------------------------------------------------------------- points ---- */
const pts = reg.campuses;
ok('one coordinate per campus, matching the union registry exactly',
  JSON.stringify(Object.keys(pts).sort()) === JSON.stringify(Object.keys(campuses).sort()));
ok('every point is a plausible WGS84 coordinate for its stated city',
  pts['treasure-island'].lat > 37 && pts['treasure-island'].lat < 38.5
  && pts['treasure-island'].lng < -122 && pts['treasure-island'].lng > -123
  && pts['oakland'].lat > 37 && pts['oakland'].lat < 38.5
  && pts['new-orleans'].lat > 29 && pts['new-orleans'].lat < 30.5
  && pts['new-orleans'].lng < -89 && pts['new-orleans'].lng > -91);
ok('every point carries its provenance and names its source',
  Object.values(pts).every((p) => ['RECORDED', 'DERIVED'].includes(p.provenance)
    && p.source.length > 10));
ok("the RECORDED point cites Locator.X's city table; the DERIVED points do not claim it",
  pts.oakland.provenance === 'RECORDED' && /Locator\.X/.test(pts.oakland.source)
  && ['treasure-island', 'new-orleans'].every((k) =>
      pts[k].provenance === 'DERIVED' && /authored/.test(pts[k].source)));

/* ---------------------------------------------------- recomputed truths --- */
ok('every stored route distance recomputes from the coordinates (±0.1 km)',
  reg.routes_km.every((r) =>
    Math.abs(haversineKm(pts[r.from], pts[r.to]) - r.km) < 0.1));
ok('every stored bearing recomputes from the coordinates (±0.2°)',
  reg.routes_km.every((r) =>
    Math.abs(bearingDeg(pts[r.from], pts[r.to]) - r.bearing_deg) < 0.2));
ok('the bay pair is a short hop and the Gulf runs are long hauls — sane scale',
  reg.routes_km.find((r) => r.from === 'treasure-island' && r.to === 'oakland').km < 15
  && reg.routes_km.filter((r) => r.to === 'new-orleans')
      .every((r) => r.km > 2900 && r.km < 3300));

/* -------------------------------------------------------------- GeoJSON --- */
const campusFeats = gj.features.filter((f) => f.properties.kind !== 'anchor');
ok('the GeoJSON is a FeatureCollection with one campus Point per campus',
  gj.type === 'FeatureCollection' && campusFeats.length === 3
  && gj.features.every((f) => f.type === 'Feature'
    && f.geometry.type === 'Point'));
ok('GeoJSON coordinates are [lng, lat] — the order the spec demands',
  campusFeats.every((f) => {
    const [lng, lat] = f.geometry.coordinates;
    const p = pts[f.properties.slug];
    return lng === p.lng && lat === p.lat && Math.abs(lng) > Math.abs(lat);
  }));
ok('GeoJSON properties carry the campus figures from the union registry',
  campusFeats.every((f) => f.properties.halls === campuses[f.properties.slug].halls.length
    && f.properties.districts === campuses[f.properties.slug].districts.length));

/* -------------------------------------------------------------- honesty --- */
ok('the registry says what a coordinate is not: an anchor, not a parcel claim',
  /does not claim a parcel/.test(reg.honesty.siting)
  && /planned locations/.test(reg.honesty.siting));
/* -------------------------------------------------------------- anchors --- */
ok('every campus carries RECORDED anchors citing their Locator.X table — eight Bay cities, seven NOLA institutions',
  Object.keys(reg.anchors).length === 3
  && reg.anchors['treasure-island'].length === 8
  && reg.anchors['oakland'].length === 4
  && reg.anchors['new-orleans'].length === 7
  && Object.values(reg.anchors).every((l) =>
    l.every((a) => a.provenance === 'RECORDED' && /Locator\.X/.test(a.source))));
ok('every anchor sits within 60 km of its campus, distances recomputed',
  Object.entries(reg.anchors).every(([ck, l]) => l.every((a) =>
    Math.abs(haversineKm(pts[ck], a) - a.km) < 0.1 && a.km < 60)));
ok('the GeoJSON carries the anchors as tagged features, [lng, lat]',
  gj.features.filter((f) => f.properties.kind === 'anchor').length === 19
  && gj.features.filter((f) => f.properties.kind === 'anchor')
      .every((f) => Math.abs(f.geometry.coordinates[0]) > Math.abs(f.geometry.coordinates[1])));
ok('every anchor, Bay city and NOLA institution alike, carries an authored blurb that says it is not the RECORDED table',
  Object.values(reg.anchors).every((l) => l.every((a) => a.blurb?.length > 40
    && /authored/.test(a.blurb_provenance))));
ok('the New Orleans city frame is RECORDED, plausible, and inside its own bounds',
  reg.city['new-orleans'].provenance === 'RECORDED'
  && /Locator\.X/.test(reg.city['new-orleans'].source)
  && (() => { const c = reg.city['new-orleans'];
    return c.center.lng > c.bounds.w && c.center.lng < c.bounds.e
      && c.center.lat > c.bounds.s && c.center.lat < c.bounds.n
      && haversineKm(pts['new-orleans'],
        { lat: c.center.lat, lng: c.center.lng }) < 6; })());
ok('every city frame is RECORDED from Locator.X and actually frames its campus',
  Object.entries(reg.city).every(([ck, c]) =>
    c.provenance === 'RECORDED' && /Locator\.X/.test(c.source)
    && c.center.lng > c.bounds.w && c.center.lng < c.bounds.e
    && c.center.lat > c.bounds.s && c.center.lat < c.bounds.n
    && pts[ck].lng > c.bounds.w && pts[ck].lng < c.bounds.e
    && pts[ck].lat > c.bounds.s && pts[ck].lat < c.bounds.n));
ok('both Bay campuses share the one committed Bay frame',
  JSON.stringify(reg.city['treasure-island'])
    === JSON.stringify(reg.city['oakland']));

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`geo/test: ${n} checks passed — ${Object.keys(pts).length} campuses, `
  + `${reg.routes_km.length} routes, CRS ${reg.crs}`);
