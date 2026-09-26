/**
 * Spatial-fabric pack verification.
 *
 * Two claims, held apart on purpose. OGC GeoPose 1.0 is CLAIMED: every
 * pose must be the Basic-YPR encoding exactly, its horizontal position
 * must equal the registry that owns it (geo/ or restoration/) to the
 * digit, and - because this bundle holds no height or heading for
 * anywhere - h and yaw/pitch/roll must be zero with the UNKNOWN sidecar
 * beside them, never a number somebody typed. The OMBI fabric manifest,
 * SOM and RMAP are NOT claimed: the files may be shaped after the deck,
 * but meta/ must list them under not_claimed with a reason, and the SOM's
 * one real idea - per-branch ownership - must hold: no external origin's
 * branch may carry anything this fabric serves. Hunters Point and Former
 * Naval Station Treasure Island must arrive still walkable:false, and the
 * bay-wide Spartina program must have no pose at all, with the reason
 * stated.
 */
import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const R = (p) => JSON.parse(readFileSync(new URL(p, import.meta.url)));
const gp = R('./registry/geopose.json');
const fab = R('./registry/fabric.json');
const som = R('./registry/som.json');
const geo = R('../geo/registry/campuses_geo.json');
const resto = R('../restoration/registry/restoration.json');
const meta = R('../meta/registry/metaverse.json');
const campuses = R('../unions/registry/campuses.json').campuses;
const unions = R('../unions/registry/unions.json').unions;
const sims = R('../sims/registry/sims.json');
const advisors = R('../agents/registry/advisors.json');
const tools = R('../tools/registry/toolcribs.json');
const world = R('../world/registry/world.json');
const page = readFileSync(new URL('../web/build_3d.py', import.meta.url), 'utf8');
const terrain = R('../terrain/registry/terrain.json');
const parcels = R('../parcels/registry/parcels.json');
// The BUILT entry page is the measurement every door is held against: the
// URL parameters it reads, the rosters it validates them with, and the
// data payload those rosters come from. Read as a file, never opened in a
// browser (this suite is browser-free), and never retyped.
const page3d = readFileSync(new URL('../web/trade_craft_3d.html', import.meta.url), 'utf8');
const dataBlock = page3d.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/);
const D3 = dataBlock ? JSON.parse(dataBlock[1]) : null;
const ROSTER = D3 ? {
  hall: new Set(D3.halls.map((h) => h.slug)),
  sim: new Set(Object.keys(D3.sims.sims)),
  campus: new Set(Object.keys(D3.campuses)),
} : null;

const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const PRODUCT = 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)';
const SHAPE = 'authored from the public OMBI deck and press, Q3 2026 - not validated '
  + 'against a normative specification, and not loaded in any metaverse browser '
  + '(Sneeze, Artemis) by this build';
const refs = new Map(gp.poses.map((p) => [p.subject.ref, p]));
const byKind = (k) => gp.poses.filter((p) => p.subject.kind === k);

/* ------------------------------------------------------------ the encoding --- */
ok('the encoding is named exactly: OGC GeoPose 1.0 Basic-YPR, OGC 21-056r11, application/geopose+json',
  gp.encoding === 'OGC GeoPose 1.0 Basic-YPR, OGC 21-056r11, application/geopose+json'
  && gp.media_type === 'application/geopose+json');
ok('every pose is the Basic-YPR shape exactly: position{lat,lon,h}, orientation{yaw,pitch,roll}, nothing else',
  gp.poses.length > 0 && gp.poses.every((p) =>
    JSON.stringify(Object.keys(p.geopose)) === '["position","orientation"]'
    && JSON.stringify(Object.keys(p.geopose.position)) === '["lat","lon","h"]'
    && JSON.stringify(Object.keys(p.geopose.orientation)) === '["yaw","pitch","roll"]'));
ok('every lat is within ±90 and every lon within ±180, all finite numbers',
  gp.poses.every((p) => {
    const { lat, lon, h } = p.geopose.position;
    return Number.isFinite(lat) && Number.isFinite(lon) && Number.isFinite(h)
      && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180;
  }));
ok('the CRS is copied from the geo registry, not retyped',
  gp.crs === geo.crs && /WGS84/.test(gp.crs));

/* ------------------------------------------------- no heights, no headings --- */
ok('height is 0.0 and every angle is 0 on every pose - this bundle holds neither for anywhere',
  gp.poses.every((p) => p.geopose.position.h === 0
    && p.geopose.orientation.yaw === 0 && p.geopose.orientation.pitch === 0
    && p.geopose.orientation.roll === 0));
ok('the UNKNOWN sidecar sits beside every pose, for h and for orientation, calling each zero a placeholder',
  gp.poses.every((p) =>
    p.provenance.h_provenance === 'UNKNOWN - not held by this bundle; 0.0 is a placeholder, not a measurement'
    && p.provenance.orientation_provenance === 'UNKNOWN - no heading is recorded; 0 is a placeholder'));
ok('every sidecar carries the horizontal position\'s real provenance word and a source string',
  gp.poses.every((p) => ['RECORDED', 'DERIVED', 'AUTHORED'].includes(p.provenance.position_horizontal)
    && typeof p.provenance.source === 'string' && p.provenance.source.length > 10));

/* ---------------------------------------------------- positions = the source --- */
const nAnchors = Object.values(geo.anchors).reduce((a, v) => a + v.length, 0);
const pinned = resto.sites.filter((s) => s.pin);
ok(`the counts are the registries' own: ${Object.keys(geo.campuses).length} campuses, ${nAnchors} anchors, ${pinned.length} pinned sites`,
  byKind('campus').length === Object.keys(geo.campuses).length
  && byKind('anchor').length === nAnchors
  && byKind('restoration-site').length === pinned.length
  && gp.counts.total === gp.poses.length
  && gp.counts.campuses + gp.counts.anchors + gp.counts.restoration_sites === gp.counts.total
  && new Set(gp.poses.map((p) => p.subject.ref)).size === gp.poses.length);
ok('every campus pose equals the geo registry to the digit, at its own provenance and source',
  byKind('campus').every((p) => {
    const g = geo.campuses[p.subject.id];
    return g && p.geopose.position.lat === g.lat && p.geopose.position.lon === g.lng
      && p.provenance.position_horizontal === g.provenance
      && p.provenance.source === g.source
      && p.subject.name === campuses[p.subject.id].name;
  }));
ok('every anchor pose equals the geo registry to the digit, at its own provenance, with its km and bearing carried',
  byKind('anchor').every((p) => {
    const [ck, nm] = p.subject.id.split('/');
    const a = Array.isArray(geo.anchors[ck]) && geo.anchors[ck].find((x) => slug(x.name) === nm);
    return a && p.subject.campus === ck
      && p.geopose.position.lat === a.lat && p.geopose.position.lon === a.lng
      && p.provenance.position_horizontal === a.provenance
      && p.provenance.source === a.source
      && p.anchor.km_from_campus === a.km && p.anchor.bearing_from_campus_deg === a.bearing_deg
      && ['city', 'institution'].includes(p.anchor.kind);
  }));
ok('every pinned restoration site\'s pose equals the restoration registry to the digit, AUTHORED, citing its own source page',
  byKind('restoration-site').every((p) => {
    const s = resto.sites.find((x) => x.id === p.subject.id);
    return s && s.pin && p.geopose.position.lat === s.lat && p.geopose.position.lon === s.lng
      && p.provenance.position_horizontal === 'AUTHORED'
      && p.provenance.source.includes(s.source_url)
      && p.site.org === s.org && p.site.category === s.category;
  }));

/* ----------------------------------------------- Hunters Point and Spartina --- */
const hp = refs.get('restoration-site:hunters-point-shipyard');
ok('Hunters Point is posed, and arrives still walkable:false with its real reason carried through',
  hp && hp.site.walkable === false && /litigated federal cleanup site/.test(hp.site.walkable_reason)
  && hp.site.category === 'environmental-monitoring');
const ti = refs.get('restoration-site:treasure-island-nsti');
const tiSrc = resto.sites.find((s) => s.id === 'treasure-island-nsti');
ok('Former Naval Station Treasure Island is posed at the registry\'s own AUTHORED pin, arrives still walkable:false with its reason, and is a different pose from the DERIVED Treasure Island campus centroid',
  ti && ti.site.walkable === false && /unresolved radiological criteria/.test(ti.site.walkable_reason)
  && ti.site.category === 'environmental-monitoring' && ti.subject.campus === 'treasure-island'
  && ti.geopose.position.lat === tiSrc.lat && ti.geopose.position.lon === tiSrc.lng
  && ti.provenance.position_horizontal === 'AUTHORED'
  && (() => {
    const c = byKind('campus').find((p) => p.subject.id === 'treasure-island');
    return c && c.provenance.position_horizontal === 'DERIVED'
      && (c.geopose.position.lat !== ti.geopose.position.lat
          || c.geopose.position.lon !== ti.geopose.position.lon);
  })());
ok('the bay-wide Spartina program has no pose at all, and the reason is stated: its registry pins no coordinate',
  !refs.has('restoration-site:spartina-removal')
  && gp.unposed.length === 1 && gp.unposed[0].subject.id === 'spartina-removal'
  && /pins no single coordinate/.test(gp.unposed[0].why)
  && resto.sites.find((s) => s.id === 'spartina-removal').pin === false);

/* ------------------------------------------------------------- the fabric --- */
ok('the fabric manifest names the operator exactly, is self-hosted static files, and enters at the real 3D page',
  fab.fabric.operator === PRODUCT
  && fab.fabric.origin === 'self-hosted static files'
  && fab.fabric.entry === 'web/trade_craft_3d.html'
  && existsSync(new URL('../' + fab.fabric.entry, import.meta.url)));
ok('the manifest and the scene graph both carry the exact not-validated, not-loaded shape label',
  fab.fabric.shape === SHAPE && som.shape === SHAPE);
ok('no DID is minted, no RMAP endpoint, no server, no network',
  fab.fabric.identity.did === null && /no DID is minted/.test(fab.fabric.identity.note)
  && /no RMAP endpoint, no server, no network/.test(fab.fabric.transport)
  && !JSON.stringify(fab).includes('ws://') && !JSON.stringify(fab).includes('wss://'));
ok('one place per campus, each with a resolving GeoPose, the union registry\'s own kind, districts and hall count, a world atmosphere, and a walkable city',
  fab.places.length === Object.keys(campuses).length
  && fab.places.every((pl) => {
    const ck = pl.geopose.replace('campus:', '');
    const c = campuses[ck];
    return refs.has(pl.geopose) && c && pl.name === c.name
      && pl.kind === (c.districts.length ? 'district' : 'hub')
      && JSON.stringify(pl.districts) === JSON.stringify(c.districts)
      && pl.halls === c.halls.length && world.atmos[pl.atmosphere] && pl.walk === true;
  }));
ok('the anchored content is exactly the existing export doors - avatar-glb once, hall-glb for every one of the 111 halls - by export id, glTF 2.0 binary, produced on demand',
  fab.anchored_content.length === 1 + unions.length
  && fab.anchored_content.every((c) => meta.exports.some((e) => e.id === c.export)
    && c.format === 'glTF 2.0 binary' && c.produced_on_demand === true
    && /learner's own browser/.test(c.how))
  && unions.every((u) => fab.anchored_content.some((c) =>
    c.export === 'hall-glb' && c.scene === `tc-hall-${u.slug}` && c.file === `tc-hall-${u.slug}.glb`))
  && fab.anchored_content.filter((c) => c.export === 'avatar-glb').length === 1);
ok('every hall door is anchored at the campus that homes that hall, and the page really exports those files',
  fab.anchored_content.filter((c) => c.export === 'hall-glb').every((c) =>
    refs.has(c.anchored_at) && campuses[c.anchored_at.replace('campus:', '')].halls.includes(c.hall))
  && /tc-avatar\.glb/.test(page) && /'tc-hall-' \+ slug \+ '\.glb'/.test(page));
ok('every service runs in-page with no network, is anchored at a resolving pose, says where else it stands (also_at, a list on every one), and names its own registry file',
  fab.services.length > 0 && fab.services.every((s) =>
    s.transport === 'in-page, no network' && refs.has(s.anchored_at)
    && existsSync(new URL('../' + s.registry, import.meta.url))
    && Array.isArray(s.also_at) && s.also_at.every((r) => refs.has(r))));
ok('every simulator the registry ships (eleven now) is a service resolving to sims/, with the operator levels and the scripted reference carried',
  Object.keys(sims.sims).every((sk) => {
    const s = fab.services.find((x) => x.id === `sim:${sk}`);
    return s && s.name === sims.sims[sk].name
      && JSON.stringify(s.operator.levels) === JSON.stringify(sims.sims[sk].operator.levels)
      && s.operator.scripted_reference === true;
  }) && fab.services.filter((s) => s.kind === 'simulator').length === Object.keys(sims.sims).length);
ok('the advisors, Schools panel, eight toolroom cribs, restoration panels and training recorder are services resolving to their registries',
  JSON.stringify(fab.services.find((s) => s.id === 'advisors').advisors)
    === JSON.stringify(Object.keys(advisors.advisors))
  && fab.services.some((s) => s.id === 'schools-panel')
  && Object.keys(tools.cribs).every((dk) => fab.services.some((s) => s.id === `crib:${dk}`))
  && fab.services.find((s) => s.id === 'restoration-panel').site_panels.length === resto.sites.length
  && fab.services.find((s) => s.id === 'restoration-panel').site_panels
    .every((sp) => sp.anchored_at === null ? sp.site === 'spartina-removal' : refs.has(sp.anchored_at))
  && fab.services.some((s) => s.id === 'training-recorder'));

/* ------------------------------------------------------- external origins --- */
const badOrigins = fab.external_origins
  .filter((e) => e.served_by_this_fabric !== false || e.origin !== 'external'
    || typeof e.operator !== 'string' || !e.operator.trim())
  .map((e) => `${JSON.stringify(e.operator)} served_by_this_fabric=${e.served_by_this_fabric}`);
ok('every external origin is served_by_this_fabric: false under a named operator, and every one of its poses resolves'
  + (badOrigins.length ? ` - OFFENDING: ${badOrigins.join('; ')}` : ''),
  fab.external_origins.length > 0 && badOrigins.length === 0
  && fab.external_origins.every((e) => e.geoposes.every((r) => refs.has(r))));
ok('every restoration site\'s own organization and every AUTHORED institution anchor is an external origin',
  resto.sites.every((s) => fab.external_origins.some((e) => e.operator === s.org))
  && Object.values(geo.anchors).flat().filter((a) => a.provenance === 'AUTHORED')
    .every((a) => fab.external_origins.some((e) => e.operator === a.name)));
ok('the Navy / EPA / DTSC origin at Hunters Point carries the not-affiliated line, and no union hall is listed as an origin',
  /not\s+affiliated with/.test(fab.external_origins.find((e) =>
    e.geoposes.includes('restoration-site:hunters-point-shipyard')).note)
  && !fab.external_origins.some((e) => unions.some((u) => u.name === e.operator)));
ok('the Navy / DTSC / CDPH origin at Former Naval Station Treasure Island is its own cleanup-and-oversight origin, serving nothing through this fabric, carrying the not-affiliated line',
  (() => {
    const e = fab.external_origins.find((x) => x.geoposes.includes('restoration-site:treasure-island-nsti'));
    return e && e.kind === 'cleanup-and-oversight-agencies' && e.served_by_this_fabric === false
      && /not\s+affiliated with/.test(e.note) && /Restoration Advisory Board/.test(e.note)
      && !e.geoposes.includes('restoration-site:hunters-point-shipyard');
  })());

/* ------------------------------------------------------------------- SOM --- */
const [mine, ...ext] = som.root.branches;
const kindsOf = (rs) => [...new Set(rs.map((r) => refs.get(r).subject.kind))].sort();
const mineRefs = [...new Set(mine.children.filter((k) => k.geopose !== null).map((k) => k.geopose))];
const extRefs = [...new Set(ext.flatMap((b) => b.children).filter((k) => k.geopose !== null).map((k) => k.geopose))];
const sharedRefs = mineRefs.filter((r) => extRefs.includes(r));
const sitePanels = fab.services.find((s) => s.id === 'restoration-panel').site_panels;
ok('ownership, recounted: every leaf under this fabric\'s branch stands on a campus pose, every external leaf on an anchor or restoration-site pose, no pose is shared, and som.json#ownership states those counts - external origins served 0, without an operator 0'
  + (sharedRefs.length ? ` - SHARED: ${sharedRefs.join(', ')}` : ''),
  JSON.stringify(kindsOf(mineRefs)) === '["campus"]'
  && kindsOf(extRefs).every((k) => ['anchor', 'restoration-site'].includes(k))
  && sharedRefs.length === 0
  && JSON.stringify(som.ownership.this_fabric_pose_kinds) === JSON.stringify(kindsOf(mineRefs))
  && JSON.stringify(som.ownership.external_pose_kinds) === JSON.stringify(kindsOf(extRefs))
  && som.ownership.poses_shared_between_this_fabric_and_an_external_branch === sharedRefs.length
  && som.ownership.fabric_leaves_on_an_external_pose === sharedRefs.length
  && som.ownership.external_origins === fab.external_origins.length
  && som.ownership.external_origins_served_by_this_fabric === fab.external_origins.filter((e) => e.served_by_this_fabric).length
  && som.ownership.external_origins_served_by_this_fabric === 0
  && som.ownership.external_origins_without_a_named_operator === 0
  && som.ownership.site_panels_anchored_at_external_poses === sitePanels.filter((sp) => sp.anchored_at !== null).length
  && sitePanels.filter((sp) => sp.anchored_at !== null).every((sp) => extRefs.includes(sp.anchored_at)));
ok('the SOM has one branch per origin: this fabric first, then one per external operator',
  mine.origin === 'this fabric' && mine.owner === PRODUCT && mine.served_by_this_fabric === true
  && ext.length === fab.external_origins.length
  && ext.every((b) => b.origin === 'external' && b.served_by_this_fabric === false)
  && new Set(som.root.branches.map((b) => b.id)).size === som.root.branches.length);
ok('per-branch ownership holds: no external branch carries a place, content, service or export door, or any node this fabric serves',
  ext.every((b) => b.children.every((k) =>
    k.served_by_this_fabric === false && !['place', 'content', 'service', 'export'].includes(k.kind))));
ok('and everything this fabric serves sits under its own branch - places, content, services and the one export door, each at a resolving pose or honestly unanchored',
  mine.children.every((k) => k.served_by_this_fabric === true
    && (k.geopose === null || refs.has(k.geopose)))
  && mine.children.filter((k) => k.kind === 'place').length === fab.places.length
  && mine.children.filter((k) => k.kind === 'content').length === fab.anchored_content.length
  && mine.children.filter((k) => k.kind === 'service').length === fab.services.length
  && mine.children.filter((k) => k.kind === 'export').length === 1);
ok('every branch records the set of provenance tiers it mixes, from the five words this bundle uses, and this fabric\'s branch mixes SCHEMATIC and SCRIPTED - never AI-SYNTHESIZED',
  som.root.branches.every((b) => b.provenance_tiers.length > 0
    && b.provenance_tiers.every((t) => ['RECORDED', 'DERIVED', 'AUTHORED', 'SCHEMATIC', 'SCRIPTED'].includes(t)))
  && mine.provenance_tiers.includes('SCHEMATIC') && mine.provenance_tiers.includes('SCRIPTED'));
ok('the export door is one SCRIPTED leaf of this fabric\'s branch: unanchored, carrying the page\'s own exportGlb transport and exactly the meta/ export ids, and the built page still has the .glb button',
  (() => {
    const x = mine.children.find((k) => k.kind === 'export');
    return x && x.geopose === null && x.provenance === 'SCRIPTED'
      && x.transport === fab.export_door.transport && /GLTFExporter/.test(x.transport)
      && JSON.stringify(x.exports) === JSON.stringify(meta.exports.map((e) => e.id))
      && fab.export_door.anchored_at === null && fab.export_door.served_by_this_fabric === true
      && page3d.includes('id="glbBtn"') && page3d.includes('async function exportGlb(root, name)');
  })());

/* ---------------------------------------------------------------- doors --- */
// A door is the deep link a browser would open for a leaf: the entry page
// plus the one URL parameter that page validates against its own roster.
// The roster is read from the BUILT page's data payload above, so a door
// resolves only when the page really opens it; a door to nothing is named.
const ENTRY = 'web/trade_craft_3d.html';
const doorOpens = (d) => {
  if (!d || d.page !== ENTRY) return false;
  if (d.param === null) return d.value === null && d.href === ENTRY
    && existsSync(new URL('../' + ENTRY, import.meta.url));
  return ['hall', 'sim', 'campus'].includes(d.param) && ROSTER[d.param].has(d.value)
    && d.href === `${ENTRY}?${d.param}=${d.value}`;
};
ok('the built 3D page reads ?hall=, ?sim= and ?campus= and validates each against its own roster - D.halls[].slug, the D.sims.sims keys, the D.campuses keys - from a data payload this suite can parse',
  D3 !== null && ROSTER.hall.size > 0 && ROSTER.sim.size > 0 && ROSTER.campus.size > 0
  && page3d.includes("D.halls.some(h => h.slug === params.get('hall'))")
  && page3d.includes("Object.keys(D.sims.sims).includes(params.get('sim'))")
  && page3d.includes("D.campuses[params.get('campus')]"));
const fabricDoors = [
  ...fab.places.map((p) => [p.id, p.door]),
  ...fab.anchored_content.map((c) => [c.scene, c.door]),
  ...fab.services.map((s) => [s.id, s.door]),
  [fab.export_door.id, fab.export_door.door],
];
const dead = fabricDoors.filter(([, d]) => !doorOpens(d) || d.resolves !== true).map(([id, d]) => `${id} -> ${d && d.href}`);
ok('every door this fabric declares opens onto the built page\'s own roster - ?hall= in D.halls, ?sim= in D.sims.sims, ?campus= in D.campuses, the entry page for the two bar doors - and each records resolves: true'
  + (dead.length ? ` - DEAD DOORS: ${dead.join('; ')}` : ''),
  fabricDoors.length > 0 && dead.length === 0);
const leaves = som.root.branches.flatMap((b) => b.children);
const withDoor = leaves.filter((k) => k.door !== null);
const resolving = withDoor.filter((k) => doorOpens(k.door) && k.door.resolves === true);
const namedOnly = leaves.filter((k) => k.door === null);
const byParam = {};
for (const k of withDoor) {
  const p = k.door.param === null ? 'entry-page' : k.door.param;
  byParam[p] = p in byParam ? byParam[p] + 1 : 1;
}
ok(`the door counts are recounted from the scene graph's leaves and match: ${withDoor.length} with a door, ${resolving.length} whose door resolves, ${namedOnly.length} that can only be named - and the unit says leaves, not root branches`,
  som.doors.leaves === leaves.length
  && som.doors.branches_with_a_door === withDoor.length
  && som.doors.branches_whose_door_resolves === resolving.length
  && som.doors.branches_that_can_only_be_named === namedOnly.length
  && withDoor.length + namedOnly.length === leaves.length
  && withDoor.length === resolving.length
  && withDoor.length === mine.children.length
  && namedOnly.length === ext.reduce((a, b) => a + b.children.length, 0)
  && som.doors.page === ENTRY && /leaves/.test(som.doors.unit)
  && JSON.stringify(som.doors.roster_sizes) === JSON.stringify({ hall: ROSTER.hall.size, sim: ROSTER.sim.size, campus: ROSTER.campus.size })
  && JSON.stringify(Object.entries(som.doors.doors_by_parameter).sort()) === JSON.stringify(Object.entries(byParam).sort())
  && fab.fabric.doors === 'spatial/registry/som.json#doors');
ok('every leaf this fabric serves carries the same door its fabric.json record does, and every external leaf has door: null, named_only: true, with the reason',
  mine.children.every((k) => {
    const rec = k.kind === 'place' ? fab.places.find((p) => p.id === k.place)
      : k.kind === 'content' ? fab.anchored_content.find((c) => c.scene === k.name)
        : k.kind === 'service' ? fab.services.find((s) => s.id === k.name)
          : k.kind === 'export' ? fab.export_door : null;
    return rec && k.door !== null && JSON.stringify(k.door) === JSON.stringify(rec.door);
  })
  && ext.every((b) => b.children.every((k) => k.door === null && k.named_only === true
    && typeof k.why_no_door === 'string' && k.why_no_door.length > 40)));

/* -------------------------------------------------------------- meta/ --- */
ok('meta/ claims geopose-1.0 under standards, OGC 21-056r11, with only defensible consumers',
  meta.baseline.standards.some((s) => s.id === 'geopose-1.0' && /OGC 21-056r11/.test(s.body)
    && s.consumers.includes('any application/geopose+json reader')));
ok('meta/ lists ombi-spatial-fabric, ombi-som and rmap under not_claimed, each with a reason, never under standards',
  ['ombi-spatial-fabric', 'ombi-som', 'rmap'].every((id) =>
    meta.baseline.not_claimed.some((x) => x.id === id && x.why.length > 40)
    && !meta.baseline.standards.some((s) => s.id === id)));

/* -------------------------------------------------------------- honesty --- */
const H = gp.honesty;
ok('the honesty block covers all six lines and the reachability probe, and each says what it must',
  /claimed outright/.test(H.geopose_claimed)
  && /never a measurement/.test(H.no_heights_or_headings)
  && /not validated against a specification/.test(H.ombi_not_claimed)
  && /No RMAP endpoint, no\s+server/.test(H.static_files_only_no_rmap)
  && /separate origin/.test(H.external_origins)
  && /Sneeze,\s+Artemis/.test(H.not_loaded_in_any_browser)
  && typeof H.reachability_probe === 'object' && Array.isArray(H.reachability_probe.tried)
  && JSON.stringify(fab.honesty) === JSON.stringify(H) && JSON.stringify(som.honesty) === JSON.stringify(H));
ok('the sources cite the deck as user-supplied and the Sneeze press (Apache 2.0, June 15 2026) as public, none of it fetched by the build',
  fab.sources.some((s) => /deck, Q3 2026/.test(s.what) && /user-supplied/.test(s.how))
  && fab.sources.some((s) => /Sneeze/.test(s.what) && /Apache 2\.0/.test(s.what) && /June 15 2026/.test(s.what)
    && /metaverse-standards\.org/.test(s.url))
  && fab.sources.every((s) => /AUTHORED|claimed/.test(s.provenance)));

/* ------------------------------------------------------------- coverage --- */
// What the poses carry, recounted here from the sidecars: a pose has a height
// or a heading only when its sidecar says something other than UNKNOWN. A
// zero in the encoding is never read as a value. The lead's gap register
// reads these counts, so each is held against its own recount.
const H_UNKNOWN = 'UNKNOWN - not held by this bundle; 0.0 is a placeholder, not a measurement';
const O_UNKNOWN = 'UNKNOWN - no heading is recorded; 0 is a placeholder';
const nH = gp.poses.filter((p) => p.provenance.h_provenance !== H_UNKNOWN).length;
const nO = gp.poses.filter((p) => p.provenance.orientation_provenance !== O_UNKNOWN).length;
ok(`coverage is recounted from the sidecars: ${gp.coverage.poses_with_height} of ${gp.coverage.poses} poses carry a height, ${gp.coverage.poses_with_heading} of ${gp.coverage.poses} a heading, all ${gp.coverage.poses} a horizontal position - and today both are zero`,
  gp.coverage.poses === gp.poses.length
  && gp.coverage.poses_with_height === nH && nH === 0
  && gp.coverage.poses_with_heading === nO && nO === 0
  && gp.coverage.poses_with_horizontal_position === gp.poses.length
  && /DERIVED/.test(gp.coverage.provenance));
ok('the coverage block says why in structure: terrain/ is a Natural Earth water mask at its own cell size with its own no-elevation line, and USGS 3DEP is the parcels/ endpoint that runs only in the learner\'s browser - never verified from the build, never stored here',
  (() => {
    const w = gp.coverage.why;
    return w.terrain.registry === 'terrain/registry/terrain.json'
      && w.terrain.source === terrain.source
      && w.terrain.cell_m === terrain.counts.cell_m
      && w.terrain.no_elevation === terrain.honesty.no_elevation
      && /mask/.test(w.terrain.holds) && /no elevation/.test(w.terrain.holds)
      && w.usgs.registry === 'parcels/registry/parcels.json#elevation'
      && w.usgs.id === parcels.elevation.id && w.usgs.name === parcels.elevation.name
      && w.usgs.scope === parcels.elevation.scope
      && w.usgs.verified_from_build === parcels.elevation.verified_from_build
      && w.usgs.verified_from_build === false
      && w.usgs.stored_by_this_bundle === false
      && /browser/.test(w.usgs.runs_in);
  })());

/* ---------------------------------------------------- reachability probe --- */
// The honesty block records a MEASUREMENT, not an assertion: one curl per
// URL, its code carried as data. None may be 2xx - the day one is, the
// normative text is readable and the not-claimed shape label is stale, so
// this fails by URL and the pack must be revisited.
const probe = H.reachability_probe;
const twoxx = probe.tried.filter((t) => /^2/.test(t.http_code)).map((t) => `${t.url} -> ${t.http_code}`);
ok('every probed URL carries a three-digit code, a curl exit, what was sought and what the code meant, dated, and the probe fetched nothing at build time'
  + (twoxx.length ? ` - REVISIT THE PACK, a text answered: ${twoxx.join('; ')}` : ''),
  probe.tried.length > 0 && probe.tried.every((t) =>
    /^https:\/\//.test(t.url) && /^[0-9]{3}$/.test(t.http_code)
    && Number.isInteger(t.curl_exit) && t.sought.length > 10 && t.meaning.length > 20)
  && new Set(probe.tried.map((t) => t.url)).size === probe.tried.length
  && /^\d{4}-\d{2}-\d{2}$/.test(probe.date) && probe.dates.includes(probe.date)
  && /curl/.test(probe.how) && /RECORDED/.test(probe.provenance)
  && twoxx.length === 0 && probe.answered_2xx === twoxx.length
  && probe.tried.some((t) => /metaverse-standards\.org/.test(t.url))
  && probe.tried.some((t) => /docs\.ogc\.org/.test(t.url)));

/* ------------------------------------------------------------- flagship --- */
// WHICH campus the bundle-wide services stand at is the campus registry's
// decision (flagship: true on exactly one campus), recomputed here - never
// a slug typed in this suite or in the builder.
const claimants = Object.keys(campuses).filter((k) => campuses[k].flagship === true);
ok(`the fabric's flagship is the campus registry's own: exactly one campus flags itself (${claimants.join(', ')}), fabric.json names it, and every page-wide service is anchored and doored there`,
  claimants.length === 1 && fab.fabric.flagship.campus === claimants[0]
  && fab.fabric.flagship.claimants === 1
  && fab.fabric.flagship.decided_by === `unions/registry/campuses.json#campuses.${claimants[0]}.flagship`
  && fab.fabric.flagship.anchors_services.length > 0
  && fab.fabric.flagship.anchors_services.every((id) => {
    const s = fab.services.find((x) => x.id === id);
    return s && s.anchored_at === `campus:${claimants[0]}` && s.door.param === 'campus' && s.door.value === claimants[0];
  })
  && ['advisors', 'schools-panel', 'restoration-panel', 'training-recorder'].every((id) => fab.fabric.flagship.anchors_services.includes(id))
  && !fab.fabric.flagship.anchors_services.some((id) => id.startsWith('sim:')));

/* ------------------------------------------------------- dashboard + wiki --- */
const dash = readFileSync(new URL('../web/trade_craft_dashboard.html', import.meta.url), 'utf8');
ok('the network dashboard renders the pose count and the claimed / not-claimed split',
  dash.includes(`<b>${gp.counts.total}</b><span>GeoPose 1.0`) && dash.includes('claimed (GeoPose) / not claimed (OMBI fabric, SOM, RMAP)'));
ok('the dashboard carries the OMBI-not-claimed and no-heights honesty lines',
  dash.includes(H.ombi_not_claimed) && dash.includes(H.no_heights_or_headings));
ok('the dashboard embeds geopose.json (as application/geopose+json) and fabric.json inline, and the download buttons are wired to them',
  (() => {
    const m = dash.match(/<script id="geopose-json" type="application\/geopose\+json">([\s\S]*?)<\/script>/);
    const f = dash.match(/<script id="fabric-json" type="application\/json">([\s\S]*?)<\/script>/);
    if (!m || !f) return false;
    const emb = JSON.parse(m[1].replace(/<\\\//g, '</'));
    return emb.source_stamp === gp.source_stamp && emb.counts.total === gp.counts.total
      && JSON.parse(f[1].replace(/<\\\//g, '</')).source_stamp === fab.source_stamp
      && dash.includes('data-dl="geopose-json"') && dash.includes('data-dl="fabric-json"')
      && dash.includes("querySelectorAll('[data-dl]')") && dash.includes('URL.createObjectURL');
  })());
ok('the wiki has its Spatial-Fabric page',
  existsSync(new URL('../wiki/Spatial-Fabric.md', import.meta.url)));

/* --------------------------------------------------------------- geomap --- */
// The geomap is the one surface built to be a real WGS84 map, and it drew
// every campus, anchor and restoration marker without ever mentioning the
// pose registry that describes those exact points — an audit finding, not
// a design choice. Every campus and anchor feature now carries its own
// `geopose` property, joined by build_geomap.py at build time (never typed);
// the legend states the pose count and the claimed/not-claimed split, and a
// marker's popup states its own pose line on click.
const geomap = readFileSync(new URL('../web/trade_craft_geomap.html', import.meta.url), 'utf8');
const nClaimed = meta.baseline.standards.filter((s) => s.id === 'geopose-1.0').length;
const nNotClaimed = meta.baseline.not_claimed
  .filter((x) => ['ombi-spatial-fabric', 'ombi-som', 'rmap'].includes(x.id)).length;
ok('the geomap legend states the GeoPose pose count and the claimed / not-claimed split',
  geomap.includes(`GeoPose 1.0</b> pose (${gp.counts.total} total`)
  && geomap.includes(`${nClaimed} claimed standard / ${nNotClaimed} not-claimed`));
ok('the geomap carries the exact height/heading honesty line, unabridged, not softened',
  geomap.includes(H.no_heights_or_headings));
// a null match is a count of zero occurrences - a measurement, not a default
const occurrences = (re) => { const m = geomap.match(re); return m === null ? 0 : m.length; };
ok('every campus and anchor feature on the geomap carries its own GeoPose ref, joined at build time - not retyped',
  occurrences(/"geopose":\{"ref":"campus:/g) === gp.counts.campuses
  && occurrences(/"geopose":\{"ref":"anchor:/g) === gp.counts.anchors);
ok('a marker\'s popup renders its own pose line on click, position provenance included',
  geomap.includes('function geoposeLine(pose)') && geomap.includes('pose.position_provenance'));
ok('the geomap offers the shared on-request elevation/aerial lookup at a campus, anchor and restoration marker - never invented for a route or a city frame',
  geomap.includes('function groundTruthButtons(lat, lng)')
  && geomap.includes("(!p.kind || p.kind === 'anchor') && f.geometry.type === 'Point'"));

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('all three registries were built from the current builder source (stamp check)',
  [gp, fab, som].every((d) => d.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16)));

console.log(`spatial/test: ${n} checks passed — ${gp.counts.total} GeoPoses `
  + `(${gp.counts.campuses}/${gp.counts.anchors}/${gp.counts.restoration_sites}), `
  + `${som.root.branches.length} SOM branches / ${som.doors.leaves} leaves `
  + `(${som.doors.branches_with_a_door} doored, ${som.doors.branches_whose_door_resolves} resolving, `
  + `${som.doors.branches_that_can_only_be_named} named only), heights ${gp.coverage.poses_with_height}/${gp.coverage.poses}, `
  + `GeoPose claimed, OMBI not`);
