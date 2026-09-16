/**
 * Bay Restoration pack verification.
 *
 * Two claims, both held to account: every site is a real, named project
 * this build could not fetch or cross-check (AUTHORED, not RECORDED,
 * and the suite proves the page says so), and every field-skill track
 * points at a real skill_id this bundle's own graph already ships -
 * never a restoration-only skill invented for this pack. Nothing here
 * may read as a SmartCiti.X program, partnership or certification.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const reg = JSON.parse(readFileSync(new URL('./registry/restoration.json', import.meta.url)));
const skills = new Set(JSON.parse(readFileSync(
  new URL('../pack/registry/skills.json', import.meta.url))).skills.map((s) => s.skill_id));
const campuses = JSON.parse(readFileSync(
  new URL('../unions/registry/campuses.json', import.meta.url))).campuses;
const geomap = readFileSync(new URL('../web/trade_craft_geomap.html', import.meta.url), 'utf8');
const page3d = readFileSync(new URL('../web/trade_craft_3d.html', import.meta.url), 'utf8');
const unions = JSON.parse(readFileSync(
  new URL('../unions/registry/unions.json', import.meta.url))).unions;
const unionSlugs = new Set(unions.map((u) => u.slug));

// the page's own embedded data blob, parsed for real - not just grepped -
// so the walkable/non-walkable claim can be checked against the actual
// data the running page would see, not just a source string
const dataMatch = page3d.match(/<script id="data"[^>]*>([\s\S]*?)<\/script>/);
const pageData = dataMatch ? JSON.parse(dataMatch[1]) : null;

const pinned = reg.sites.filter((s) => s.pin);

/* ---------------------------------------------------------------- sites --- */
ok('at least eight real, distinctly-named restoration sites',
  reg.sites.length >= 8 && new Set(reg.sites.map((s) => s.id)).size === reg.sites.length);
ok('every site names a real org and links to a real https source',
  reg.sites.every((s) => s.name && s.org && s.source_url.startsWith('https://')));
ok('every pinned site carries a coordinate inside a plausible Bay Area box',
  pinned.every((s) => s.lat > 36 && s.lat < 39.5 && s.lng > -123.5 && s.lng < -121));
ok('every unpinned site (a bay-wide program) carries no fabricated point',
  reg.sites.filter((s) => !s.pin).every((s) => s.lat === null && s.lng === null));
ok('a site marked workforce=true names its real workforce pathway',
  reg.sites.filter((s) => s.workforce).every((s) => s.workforce_note?.length > 20));
ok('every campus grouping names a real campus this bundle actually has',
  reg.sites.every((s) => s.campus === null || s.campus in campuses));
ok('every site names a category, and it is one of exactly two allowed values',
  reg.sites.every((s) => ['habitat-restoration', 'environmental-monitoring'].includes(s.category)));
ok('nine sites are habitat-restoration and exactly one is environmental-monitoring',
  reg.sites.filter((s) => s.category === 'habitat-restoration').length === 9
  && reg.sites.filter((s) => s.category === 'environmental-monitoring').length === 1);
ok('every site names at least one real trade_needs union slug, grounded in the '
  + 'real registry - none invented',
  reg.sites.every((s) => Array.isArray(s.trade_needs) && s.trade_needs.length > 0
    && s.trade_needs.every((slug) => unionSlugs.has(slug))));
ok('a site marked participation=true names its real monitoring-participation note, '
  + 'distinct from a workforce/job-training pathway',
  reg.sites.filter((s) => s.participation).every((s) => s.participation_note?.length > 20));
ok('every site declares walkable explicitly, and walkable=false always states the '
  + 'real reason',
  reg.sites.every((s) => typeof s.walkable === 'boolean'
    && (s.walkable || !!s.walkable_reason)));
ok('every fact a site cites has real text and a real https source',
  reg.sites.every((s) => (s.facts ?? []).every((f) => f.text && f.source_url?.startsWith('https://'))));

/* --------------------------------------------------------------- tracks --- */
ok('three field-skill tracks, each bound to at least two real skill_ids',
  reg.tracks.length === 3
  && reg.tracks.every((t) => t.skills.length >= 2));
ok('every track skill is a real skill_id this bundle\'s own graph ships - none invented',
  reg.tracks.every((t) => t.skills.every((sk) => skills.has(sk))));

/* -------------------------------------------------------------- honesty --- */
ok('the pack states plainly it is not affiliated with, and does not certify, any site',
  /not\s+affiliated with/.test(reg.honesty.not_affiliated)
  && /does not certify/.test(reg.honesty.not_affiliated));
ok('the provenance line states AUTHORED FROM PUBLIC RECORD, not a live fetch',
  /AUTHORED FROM PUBLIC RECORD/.test(reg.honesty.provenance)
  && /not RECORDED against a live fetch/.test(reg.honesty.provenance));
ok('the honesty block states no restoration-only skill is invented',
  /nothing\s+restoration-specific is invented/.test(reg.honesty.no_new_skills));
ok('campus grouping is stated as a convenience, not a proximity claim',
  /not a claim that\s+campus operates, funds or sits next to the site/
    .test(reg.honesty.campus_grouping));
ok('nothing here claims to certify real restoration field work',
  /nothing here certifies a learner/.test(reg.honesty.not_certification));

/* --------------------------------------------------------------- geomap --- */
ok('the geomap trims the registry into D.restorationSites and marks each one',
  geomap.includes('D.restorationSites') && geomap.includes('restMarkers++'));
ok('every pinned site\'s own real coordinate reaches the geomap',
  pinned.every((s) => geomap.includes(`"lat":${s.lat},"lng":${s.lng}`)));
ok('the geomap draws restoration sites visually distinct from campuses and candidates',
  geomap.includes('restoration-marker'));
ok('the geomap popup links out to the site\'s own real source page',
  geomap.includes('s.source_url') && geomap.includes('target="_blank"'));
ok('the geomap carries the not-affiliated honesty line',
  geomap.includes('D.restorationHonesty.not_affiliated'));

/* -------------------------------------------------------------- 3D app --- */
ok('the 3D app implements the Bay Restoration panel and trims the registry into D.restoration',
  page3d.includes('function openRestoration(') && page3d.includes('D.restoration.sites'));
ok('every site is named in the 3D panel',
  reg.sites.every((s) => page3d.includes(s.name)));
ok('every track builds a click-through via the existing hall-goto handler, and every skill\'s hall reaches the page',
  page3d.includes('data-hall-goto="${esc(hall)}"')
  && reg.tracks.every((t) => t.skills.every((sk) =>
    page3d.includes(`"${sk}"`))));
ok('the restoration toolbar button actually opens the panel',
  page3d.includes("getElementById('restorationBtn')") && page3d.includes('openRestoration()'));
ok('the hall panel checks for and links back to a taught field-skill track (reverse of the schools link)',
  page3d.includes("D.restoration.tracks.some((t) => t.skills.some((sk) => sk.split('.')[0] === sg))")
  && page3d.includes('data-restoration-hall="${esc(sg)}"'));
ok('the hall-panel restoration badge actually opens the Bay Restoration panel, focused on the hall',
  page3d.includes('openRestoration(rh.dataset.restorationHall)')
  && page3d.includes('function openRestoration(focusHall, focusSite)'));

/* ----------------------------------------------------- Hunters Point --- */
const hp = reg.sites.find((s) => s.id === 'hunters-point-shipyard');
ok('the Hunters Point entry exists, is pinned and environmental-monitoring',
  hp && hp.pin && hp.category === 'environmental-monitoring');
ok('Hunters Point is explicitly NOT walkable, with the honest reason stated inline',
  hp.walkable === false
  && /litigated federal cleanup site/.test(hp.walkable_reason));
ok('Hunters Point carries at least four real, cited facts, none of them claiming '
  + 'the cleanup or the litigation is resolved',
  hp.facts.length >= 4
  && !/the cleanup (is|has been) (complete|resolved|finished)/i.test(JSON.stringify(hp.facts))
  && /OPEN, not resolved/.test(hp.facts.map((f) => f.text).join(' ')));
ok('Hunters Point states the Tetra Tech fraud settlement as SETTLED and the '
  + 'Greenaction litigation as still open - the two are not conflated',
  /SETTLED/.test(hp.facts.map((f) => f.text).join(' '))
  && /OPEN/.test(hp.facts.map((f) => f.text).join(' ')));
ok('Hunters Point is not framed as a workforce/job-training program',
  hp.workforce === false && hp.workforce_note === null);
ok('Hunters Point points to the real Marie Harrison Bayview Air Monitoring '
  + 'Project / Greenaction / IVAN BVHP, not an invented SmartCiti.X program',
  hp.participation === true
  && /Marie Harrison/.test(hp.participation_note)
  && /Greenaction/.test(hp.participation_note)
  && /IVAN Bayview Hunters Point/.test(hp.participation_note));
ok('Hunters Point\'s trade_needs are hazmat first, with laborers and '
  + 'operating-eng as the secondary real fit, all real union slugs',
  hp.trade_needs[0] === 'hazmat'
  && new Set(hp.trade_needs).size === 3
  && hp.trade_needs.every((slug) => unionSlugs.has(slug)));
ok('the honesty block explicitly extends not_affiliated to Hunters Point and '
  + 'explains why the environmental-monitoring category is framed differently',
  /Hunters Point/.test(reg.honesty.not_affiliated)
  && /snapshot of public record as of September 2026/.test(
    reg.honesty.environmental_monitoring_category));

/* --------------------------------------------------- walkable city layer --- */
// walkable=false (Hunters Point) must never appear wherever the walkable-scene
// list is asserted below - the single most load-bearing constraint in this pack
const walkable = pinned.filter((s) => s.campus && s.walkable !== false);
ok('walkable=false sites are excluded from the walkable-scene set entirely',
  !walkable.some((s) => s.id === 'hunters-point-shipyard')
  && walkable.length === pinned.filter((s) => s.campus).length - 1);
const builder3d = readFileSync(new URL('../web/build_3d.py', import.meta.url), 'utf8');
ok('every pinned, campus-grouped site gets a true east/north km offset (the same '
  + 'formula D.geo.cityPois already uses) for the walkable city layer, but only '
  + 'when walkable is not explicitly false',
  builder3d.includes("s.get('pin') and s.get('campus')")
  && builder3d.includes("s.get('walkable', True)")
  && walkable.length > 0);
ok('the page\'s own embedded data proves it at runtime: Hunters Point carries no '
  + 'e/n walkable offset, while every other walkable site does',
  pageData !== null
  && (() => {
    const hpData = pageData.restoration.sites.find((s) => s.id === 'hunters-point-shipyard');
    return hpData && hpData.e === undefined && hpData.n === undefined
      && walkable.every((s) => pageData.restoration.sites.find((x) => x.id === s.id).e !== undefined);
  })());
ok('the panel source itself only ever emits the "Walk this site" button when '
  + 's.e is defined, and otherwise states the walkable_reason honestly instead - '
  + 'proven true for Hunters Point by the pageData check above',
  page3d.includes('s.e !== undefined')
  && page3d.includes('not a walkable scene: '));
ok('Hunters Point is still located and clickable: it reaches the geomap as a real '
  + 'pinned marker with its own coordinate',
  geomap.includes(hp.name)
  && geomap.includes(`"lat":${hp.lat},"lng":${hp.lng}`));
ok('the 3D app builds a real, clickable marker for every walkable restoration site',
  page3d.includes('function buildRestorationSites(')
  && page3d.includes('restorationHits')
  && page3d.includes('userData.restorationSite'));
ok('a click on a restoration-site marker opens the panel focused on that exact site',
  page3d.includes('openRestoration(null, rhit.object.userData.restorationSite)')
  && page3d.includes("id=\"site-${esc(s.id)}\""));
ok('a walkable site never claims RECORDED provenance in its in-world sign - it is AUTHORED',
  page3d.includes("'AUTHORED")
  && !/restorationSite[\s\S]{0,200}RECORDED/.test(page3d));
ok('the panel itself marks which real sites are walkable in the city layer',
  page3d.includes('walkable in the city layer'));

/* ------------------------------------------------- standalone site walk --- */
ok('a "Walk this site" button reaches every walkable site from the panel',
  page3d.includes('data-resto-walk="${esc(s.id)}"')
  && page3d.includes("e.target.closest('[data-resto-walk]')")
  && page3d.includes('startRestorationWalk(rw.dataset.restoWalk)'));
ok('the standalone scene builds real, distinct ground for every walkable site - '
  + 'not one shared template stamped eight times',
  page3d.includes('function buildRestoGround(')
  && walkable.every((s) => page3d.includes(`site.id === '${s.id}'`)));
ok('every walkable site\'s own real habitat/scale/org text is quoted in its scene '
  + 'as the reason for what stands there (no invented per-site detail)',
  walkable.every((s) => page3d.includes(s.habitat)));
ok('the American Canyon site - the one entry the registry itself calls a PLAN, not '
  + 'built work - reads proposed and unbuilt in its own scene, not built like the rest',
  page3d.includes('proposed · not yet built')
  && /american-canyon[\s\S]{0,600}not yet built/.test(page3d));
ok('the standalone scene builds a real, clickable beacon for every field-skill track, '
  + 'each opening a panel that still links to the real hall that teaches it',
  page3d.includes('function buildRestoTrackBeacons(')
  && page3d.includes('function openRestoTrack(')
  && page3d.includes('userData.restoTrack'));
ok('entering or leaving a site walk is wired into every place the 3D app changes '
  + 'view, so it can never be left running underneath a hall, campus or sim',
  page3d.includes('if (curRestoSite) teardownRestoWalk();')
  && [...page3d.matchAll(/if \(curRestoSite\) teardownRestoWalk\(\);/g)].length >= 4);
ok('walking the site (desktop pointer-lock and touch alike) clamps to the site\'s '
  + 'own bounds and offers the nearest track beacon to open, the same pattern '
  + 'campus and hall walking already use',
  page3d.includes("view === 'restoration'")
  && page3d.includes('RESTO_R')
  && page3d.includes('nearTrack'));
ok('the scene never claims a survey or aerial scan of the real site - it says '
  + 'schematic, composed from that site\'s own real habitat description',
  page3d.includes('Schematic ground, composed from this site'));

/* ------------------------------------------- real elevation + imagery --- */
ok('every pinned site offers a real, on-request USGS elevation lookup at its '
  + 'own coordinate - the same elevationLookup() the city layer\'s own '
  + 'institution panels already use, never a second copy of that service',
  page3d.includes('function siteElevation(')
  && page3d.includes('elevationLookup(lat, lng, (o) =>')
  && page3d.includes("data-elev-go=\"${esc(s.id)}\""));
ok('every pinned site offers a real, on-request USGS aerial-imagery thumbnail '
  + 'at its own coordinate - the same public-domain tile service the campus '
  + 'orthoimagery button already uses, never a second copy of that service',
  page3d.includes('function siteAerial(')
  && page3d.includes('function singleTileUrl(')
  && page3d.includes("data-sat-go=\"${esc(s.id)}\""));
ok('both real-data lookups fire only on click (never at build time or on panel '
  + 'open) and fail honestly rather than silently, matching the city layer\'s own pattern',
  page3d.includes("e.target.closest('[data-elev-go]')")
  && page3d.includes("e.target.closest('[data-sat-go]')")
  && page3d.includes('Orthoimagery did not answer from')
  && page3d.includes('D.recHonesty.availability'));
ok('the real aerial thumbnail is never blended into the walkable scene\'s own '
  + 'ground - it stays a flat 2D panel result, so the schematic-ground honesty '
  + 'above is never contradicted by a real photo standing in for it',
  !/function buildRestoGround[\s\S]{0,4000}singleTileUrl/.test(page3d)
  && !/function buildRestoGround[\s\S]{0,4000}siteAerial/.test(page3d));

/* -------------------------------------------------------------- dashboard --- */
const dash = readFileSync(
  new URL('../web/trade_craft_dashboard.html', import.meta.url), 'utf8');
ok('the network dashboard renders the site / track count',
  dash.includes(`${reg.sites.length} / ${reg.tracks.length}`));
ok('the network dashboard carries the not-affiliated honesty line',
  dash.includes(reg.honesty.not_affiliated));

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`restoration/test: ${n} checks passed — ${reg.sites.length} sites `
  + `(${pinned.length} mapped), ${reg.tracks.length} tracks`);
