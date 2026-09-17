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
 * branch may carry anything this fabric serves. Hunters Point must arrive
 * still walkable:false, and the bay-wide Spartina program must have no
 * pose at all, with the reason stated.
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
    const a = (geo.anchors[ck] || []).find((x) => slug(x.name) === nm);
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
ok('every service runs in-page with no network, is anchored at a resolving pose, and names its own registry file',
  fab.services.length > 0 && fab.services.every((s) =>
    s.transport === 'in-page, no network' && refs.has(s.anchored_at)
    && existsSync(new URL('../' + s.registry, import.meta.url))
    && (s.also_at ?? []).every((r) => refs.has(r))));
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
ok('every external origin is served_by_this_fabric: false, and every one of its poses resolves',
  fab.external_origins.length > 0 && fab.external_origins.every((e) =>
    e.served_by_this_fabric === false && e.origin === 'external'
    && e.geoposes.every((r) => refs.has(r))));
ok('every restoration site\'s own organization and every AUTHORED institution anchor is an external origin',
  resto.sites.every((s) => fab.external_origins.some((e) => e.operator === s.org))
  && Object.values(geo.anchors).flat().filter((a) => a.provenance === 'AUTHORED')
    .every((a) => fab.external_origins.some((e) => e.operator === a.name)));
ok('the Navy / EPA / DTSC origin at Hunters Point carries the not-affiliated line, and no union hall is listed as an origin',
  /not\s+affiliated with/.test(fab.external_origins.find((e) =>
    e.geoposes.includes('restoration-site:hunters-point-shipyard')).note)
  && !fab.external_origins.some((e) => unions.some((u) => u.name === e.operator)));

/* ------------------------------------------------------------------- SOM --- */
const [mine, ...ext] = som.root.branches;
ok('the SOM has one branch per origin: this fabric first, then one per external operator',
  mine.origin === 'this fabric' && mine.owner === PRODUCT && mine.served_by_this_fabric === true
  && ext.length === fab.external_origins.length
  && ext.every((b) => b.origin === 'external' && b.served_by_this_fabric === false)
  && new Set(som.root.branches.map((b) => b.id)).size === som.root.branches.length);
ok('per-branch ownership holds: no external branch carries a place, content or service, or any node this fabric serves',
  ext.every((b) => b.children.every((k) =>
    k.served_by_this_fabric === false && !['place', 'content', 'service'].includes(k.kind))));
ok('and everything this fabric serves sits under its own branch - places, content and services, each at a resolving pose',
  mine.children.every((k) => k.served_by_this_fabric === true
    && (k.geopose === null || refs.has(k.geopose)))
  && mine.children.filter((k) => k.kind === 'place').length === fab.places.length
  && mine.children.filter((k) => k.kind === 'content').length === fab.anchored_content.length
  && mine.children.filter((k) => k.kind === 'service').length === fab.services.length);
ok('every branch records the set of provenance tiers it mixes, from the four words this bundle uses',
  som.root.branches.every((b) => b.provenance_tiers.length > 0
    && b.provenance_tiers.every((t) => ['RECORDED', 'DERIVED', 'AUTHORED', 'SCHEMATIC'].includes(t)))
  && mine.provenance_tiers.includes('SCHEMATIC'));

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
ok('the honesty block covers all six lines, and each says what it must',
  /claimed outright/.test(H.geopose_claimed)
  && /never a measurement/.test(H.no_heights_or_headings)
  && /not validated against a specification/.test(H.ombi_not_claimed)
  && /No RMAP endpoint, no\s+server/.test(H.static_files_only_no_rmap)
  && /separate origin/.test(H.external_origins)
  && /Sneeze,\s+Artemis/.test(H.not_loaded_in_any_browser)
  && JSON.stringify(fab.honesty) === JSON.stringify(H) && JSON.stringify(som.honesty) === JSON.stringify(H));
ok('the sources cite the deck as user-supplied and the Sneeze press (Apache 2.0, June 15 2026) as public, none of it fetched by the build',
  fab.sources.some((s) => /deck, Q3 2026/.test(s.what) && /user-supplied/.test(s.how))
  && fab.sources.some((s) => /Sneeze/.test(s.what) && /Apache 2\.0/.test(s.what) && /June 15 2026/.test(s.what)
    && /metaverse-standards\.org/.test(s.url))
  && fab.sources.every((s) => /AUTHORED|claimed/.test(s.provenance)));

/* ------------------------------------------------------- dashboard + wiki --- */
const dash = readFileSync(new URL('../web/trade_craft_dashboard.html', import.meta.url), 'utf8');
ok('the network dashboard renders the pose count and the claimed / not-claimed split',
  dash.includes(`<b>${gp.counts.total}</b>`) && dash.includes('claimed (GeoPose) / not claimed (OMBI fabric, SOM, RMAP)'));
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

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('all three registries were built from the current builder source (stamp check)',
  [gp, fab, som].every((d) => d.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16)));

console.log(`spatial/test: ${n} checks passed — ${gp.counts.total} GeoPoses `
  + `(${gp.counts.campuses}/${gp.counts.anchors}/${gp.counts.restoration_sites}), `
  + `${som.root.branches.length} SOM branches, GeoPose claimed, OMBI not`);
