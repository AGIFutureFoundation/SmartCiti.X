/**
 * Geo registry verification.
 *
 * Coordinates are claims about the real world, so nothing is trusted: the
 * suite recomputes every distance and bearing from the stored coordinates,
 * validates the GeoJSON against its own spec's shape (lng,lat order — the
 * classic swap bug), and holds every point to its provenance discipline.
 */
import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';

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
  && pts['new-orleans'].lng < -89 && pts['new-orleans'].lng > -91
  && pts['houston'].lat > 29 && pts['houston'].lat < 30.5
  && pts['houston'].lng < -94 && pts['houston'].lng > -96
  && pts['chicago'].lat > 41 && pts['chicago'].lat < 42.5
  && pts['chicago'].lng < -87 && pts['chicago'].lng > -88.5
  && pts['seattle'].lat > 47 && pts['seattle'].lat < 48.5
  && pts['seattle'].lng < -121.5 && pts['seattle'].lng > -123
  && pts['pittsburgh'].lat > 40 && pts['pittsburgh'].lat < 41
  && pts['pittsburgh'].lng < -79.5 && pts['pittsburgh'].lng > -80.5
  && pts['denver'].lat > 39 && pts['denver'].lat < 40.5
  && pts['denver'].lng < -104 && pts['denver'].lng > -106
  && pts['miami'].lat > 25 && pts['miami'].lat < 26.5
  && pts['miami'].lng < -79.5 && pts['miami'].lng > -81
  && pts['detroit'].lat > 41.5 && pts['detroit'].lat < 43
  && pts['detroit'].lng < -82.5 && pts['detroit'].lng > -83.5);
ok('every point carries its provenance and names its source',
  Object.values(pts).every((p) =>
    ['RECORDED', 'DERIVED', 'AUTHORED'].includes(p.provenance)
    && p.source.length > 10));
ok("the RECORDED point cites Locator.X's city table; the DERIVED points do not claim it",
  pts.oakland.provenance === 'RECORDED' && /Locator\.X/.test(pts.oakland.source)
  && ['treasure-island', 'new-orleans'].every((k) =>
      pts[k].provenance === 'DERIVED' && /authored/.test(pts[k].source)));
ok('the AUTHORED points (Houston, Chicago, Seattle, Pittsburgh, Denver, Miami, Detroit - all hub campuses) admit they are not cross-checked - the same bar a roadmap candidate is held to',
  ['houston', 'chicago', 'seattle', 'pittsburgh', 'denver', 'miami', 'detroit'].every((k) =>
    pts[k].provenance === 'AUTHORED'
    && /not cross-checked against any\s+file this build can verify/.test(pts[k].source)));

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
  gj.type === 'FeatureCollection' && campusFeats.length === 10
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
const RECORDED_CKS = ['treasure-island', 'oakland', 'new-orleans'];
const AUTHORED_CKS = ['houston', 'chicago', 'seattle', 'pittsburgh', 'denver', 'miami', 'detroit'];
/* This check used to assert a per-campus anchor COUNT - eight for
   Treasure Island, four for Oakland, and so on. Those literals were a
   second copy of the registry, and they broke the day the Bay campuses
   took every city within 22 km from the table they already cite rather
   than a hand-picked eight. What matters is not how many there are; it is
   that the three campuses with a sibling table to cite are RECORDED to
   the last anchor, the seven without one are AUTHORED to the last anchor,
   and nobody is somewhere in between. That is now what is checked. */
ok('every campus carries anchors — RECORDED for the three flagship '
  + 'campuses, which have a Locator.X table to cite, AUTHORED for the '
  + 'seven hub campuses, which have none; and no campus mixes the two',
  Object.keys(reg.anchors).length === 10
  && RECORDED_CKS.concat(AUTHORED_CKS).every(
    (k) => Array.isArray(reg.anchors[k]) && reg.anchors[k].length > 0)
  && RECORDED_CKS.every(
    (k) => reg.anchors[k].every((a) => a.provenance === 'RECORDED'))
  && AUTHORED_CKS.every(
    (k) => reg.anchors[k].every((a) => a.provenance === 'AUTHORED')));
ok('the AUTHORED anchors (Houston, Chicago, Seattle, Pittsburgh, Denver, Miami, Detroit) admit plainly they are not RECORDED '
  + '- no sibling table lists them, unlike every anchor near the three flagship campuses',
  AUTHORED_CKS.every((ck) => reg.anchors[ck].every((a) =>
    a.source.length > 15 && !/Locator\.X/.test(a.source))));
ok('every anchor sits within 60 km of its campus, distances recomputed',
  Object.entries(reg.anchors).every(([ck, l]) => l.every((a) =>
    Math.abs(haversineKm(pts[ck], a) - a.km) < 0.1 && a.km < 60)));
ok('the GeoJSON carries the anchors as tagged features, [lng, lat]',
  // the count is the registry's, not a literal: a typed 47 here was one
  // of three places that broke when the Bay anchors densified
  gj.features.filter((f) => f.properties.kind === 'anchor').length
    === Object.values(reg.anchors).reduce((a, v) => a + v.length, 0)
  && gj.features.filter((f) => f.properties.kind === 'anchor')
      .every((f) => Math.abs(f.geometry.coordinates[0]) > Math.abs(f.geometry.coordinates[1])));
ok('the GeoJSON anchor features carry the same real provenance split as the registry',
  gj.features.filter((f) => f.properties.kind === 'anchor')
    .every((f) => RECORDED_CKS.includes(f.properties.near)
      ? f.properties.provenance === 'RECORDED'
      : f.properties.provenance === 'AUTHORED'));
ok('every anchor, RECORDED and AUTHORED alike, carries an authored blurb - '
  + 'each one honestly naming its OWN coordinate\'s tier, never claiming RECORDED for an AUTHORED point',
  Object.entries(reg.anchors).every(([ck, l]) => l.every((a) => {
    if (a.blurb?.length <= 40 || !/authored/.test(a.blurb_provenance)) return false;
    return RECORDED_CKS.includes(ck)
      ? !/same tier as the coordinate/.test(a.blurb_provenance)
      : /same tier as the coordinate/.test(a.blurb_provenance);
  })));
ok('the New Orleans city frame is RECORDED, plausible, and inside its own bounds',
  reg.city['new-orleans'].provenance === 'RECORDED'
  && /Locator\.X/.test(reg.city['new-orleans'].source)
  && (() => { const c = reg.city['new-orleans'];
    return c.center.lng > c.bounds.w && c.center.lng < c.bounds.e
      && c.center.lat > c.bounds.s && c.center.lat < c.bounds.n
      && haversineKm(pts['new-orleans'],
        { lat: c.center.lat, lng: c.center.lng }) < 6; })());
ok('every RECORDED city frame (the three flagship campuses) actually cites Locator.X and frames its campus',
  RECORDED_CKS.every((ck) => {
    const c = reg.city[ck];
    return c.provenance === 'RECORDED' && /Locator\.X/.test(c.source)
      && c.center.lng > c.bounds.w && c.center.lng < c.bounds.e
      && c.center.lat > c.bounds.s && c.center.lat < c.bounds.n
      && pts[ck].lng > c.bounds.w && pts[ck].lng < c.bounds.e
      && pts[ck].lat > c.bounds.s && pts[ck].lat < c.bounds.n;
  }));
ok('every AUTHORED city frame (the seven hub campuses) admits it is not cross-checked, and still actually frames its campus',
  AUTHORED_CKS.every((ck) => {
    const c = reg.city[ck];
    return c.provenance === 'AUTHORED' && !/Locator\.X/.test(c.source)
      && /not cross-checked/.test(c.source)
      && c.center.lng > c.bounds.w && c.center.lng < c.bounds.e
      && c.center.lat > c.bounds.s && c.center.lat < c.bounds.n
      && pts[ck].lng > c.bounds.w && pts[ck].lng < c.bounds.e
      && pts[ck].lat > c.bounds.s && pts[ck].lat < c.bounds.n;
  }));
ok('both Bay campuses share the one committed Bay frame',
  JSON.stringify(reg.city['treasure-island'])
    === JSON.stringify(reg.city['oakland']));
ok('no two hub campuses share a frame with each other or with the Bay',
  AUTHORED_CKS.every((a, i) =>
    AUTHORED_CKS.slice(i + 1).every((b) =>
      JSON.stringify(reg.city[a]) !== JSON.stringify(reg.city[b]))
    && JSON.stringify(reg.city[a]) !== JSON.stringify(reg.city['treasure-island'])));

const net = JSON.parse(readFileSync(
  new URL('./registry/network.geojson', import.meta.url)));
// the third typed anchor total. Like the other two, it is computed now.
const nAnchors = Object.values(reg.anchors).reduce((a, v) => a + v.length, 0);
const nCampuses = Object.keys(reg.campuses).length;
ok(`the network GeoJSON carries the whole registry: ${nCampuses + nAnchors} `
  + `points (${nCampuses} campuses + ${nAnchors} anchors), 45 route lines `
  + '(every campus pair), 9 frames (2 RECORDED, 7 AUTHORED)',
  net.features.filter((f) => f.geometry.type === 'Point').length
    === nCampuses + nAnchors
  && net.features.filter((f) => f.geometry.type === 'LineString').length === 45
  && net.features.filter((f) => f.geometry.type === 'Polygon').length === 9
  && net.features.filter((f) => f.geometry.type === 'Polygon')
      .every((f) => RECORDED_CKS.includes(f.properties.campus)
        ? f.properties.provenance === 'RECORDED'
        : f.properties.provenance === 'AUTHORED'));
ok('every route line ends on its own campuses and states the table\'s distance',
  net.features.filter((f) => f.properties.kind === 'route').every((f) => {
    const r = reg.routes_km.find((x) =>
      x.from === f.properties.from && x.to === f.properties.to);
    const cs = f.geometry.coordinates;
    const near = (c, k) => Math.abs(c[0] - pts[k].lng) < .001
      && Math.abs(c[1] - pts[k].lat) < .001;
    return r && f.properties.km === r.km
      && f.properties.provenance === 'DERIVED'
      && near(cs[0], f.properties.from) && near(cs[cs.length - 1], f.properties.to);
  }));
ok('every anchor point in the network file carries its blurb and its own real provenance',
  net.features.filter((f) => f.properties.kind === 'anchor')
    .every((f) => f.properties.blurb?.length > 40
      && /authored/.test(f.properties.blurb_provenance)
      && (RECORDED_CKS.includes(f.properties.near)
        ? f.properties.provenance === 'RECORDED'
        : f.properties.provenance === 'AUTHORED')));

/* ----------------------------------------------------------- on foot --- */
ok('the walk bands are the RECORDED ones, with the pace they come from stated',
  reg.walk.bands_m.ten_minute === 800
  && reg.walk.bands_m.fifteen_minute === 1200
  && /about 800 m/.test(reg.walk.pace_note)
  && /about 1\.2 km/.test(reg.walk.pace_note)
  && reg.walk.provenance.startsWith('RECORDED')
  && reg.walk.cite_file === 'src/walk.js');
ok('the six destination classes a walkable measure has to count are carried',
  reg.walk.classes.length === 6
  && ['shop', 'eat', 'work', 'care', 'learn', 'stay']
    .every((id) => reg.walk.classes.some((c) => c.id === id))
  && reg.walk.classes.every((c) => c.name.length >= 8));
ok('the walk refuses the trademark and the false precision at once',
  /not Walk Score/.test(reg.walk.honesty.not_a_score)
  && /no relationship with\s+it is claimed/.test(reg.walk.honesty.not_a_score)
  && /straight-line between/.test(reg.walk.honesty.straight_line)
  && /sometimes impossibly\s+longer/.test(reg.walk.honesty.straight_line));
ok('and it says plainly what it does NOT count, rather than implying it counts shops - '
  + 'and states real anchors span both provenance tiers, not just RECORDED',
  /holds no shop records/.test(reg.walk.honesty.what_it_counts)
  && /RECORDED where a\s+sibling source exists/.test(reg.walk.honesty.what_it_counts)
  && /AUTHORED where none does/.test(reg.walk.honesty.what_it_counts));
ok('no band is asserted without a campus to measure it from',
  Object.keys(reg.anchors).every((ck) => ck in reg.campuses));

/* ---------------------------------------------------------- cross-check --- */
// recorded_check is a contract, never a report of the build machine: the
// committed bytes are the same whether or not the sibling checkout was
// present when the registry was built. The comparison runs HERE, every run.
const rc = reg.recorded_check;
ok('recorded_check is the machine-independent contract: names the sibling checkout, what is held against it, and where the check runs',
  typeof rc === 'object' && rc.checkout === '../locator.x'
  && /when it is\s+present beside this repository/.test(rc.contract)
  && rc.held.length === 3 && /geo\/test\.mjs/.test(rc.where));
const locx = new URL('../../locator.x/', import.meta.url);
if (existsSync(locx)) {
  const app = readFileSync(new URL('src/app.js', locx), 'utf8');
  const m = /\['Oakland',([0-9.]+),(-[0-9.]+),/.exec(app);
  ok('cross-check ran: the RECORDED Oakland pair still matches the Locator.X city table',
    !!m && +m[1] === reg.campuses.oakland.lat && +m[2] === reg.campuses.oakland.lng);
  const walk = readFileSync(new URL('src/walk.js', locx), 'utf8');
  ok('cross-check ran: the walk bands and classes still match the Locator.X walk module',
    walk.includes(`R10=${reg.walk.bands_m.ten_minute}, R15=${reg.walk.bands_m.fifteen_minute}`)
    && reg.walk.classes.every((c) => walk.includes(`id:'${c.id}'`) && walk.includes(`name:'${c.name}'`)));
} else {
  ok('cross-check skipped: Locator.X checkout not present beside this repository (Oakland pair not re-held this run)', true);
  ok('cross-check skipped: Locator.X checkout not present beside this repository (walk bands not re-held this run)', true);
}

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`geo/test: ${n} checks passed — ${Object.keys(pts).length} campuses, `
  + `${reg.routes_km.length} routes, CRS ${reg.crs}`);
