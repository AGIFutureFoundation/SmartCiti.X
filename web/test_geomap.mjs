/**
 * The network geomap, held to the registries it claims to read.
 *
 * `web/build_geomap.py` writes `web/trade_craft_geomap.html`: the geo
 * registry drawn as a real WGS84 map, with per-campus rollups, each anchor's
 * provenance class, and the Bay Restoration sites - eight that walk and
 * three that state, in the registry's own words, why they do not. Every
 * figure and every class on that page is a claim about a registry. This
 * suite recomputes each claim from the registry that owns it and holds the
 * SHIPPED PAGE to the answer.
 *
 * WHICH FILE EACH CHECK READS is in its message:
 *
 *   [registry]  the registries only - no page involved
 *   [shipped]   the built HTML, and the JSON embedded in it
 *
 * MATCH STRUCTURE, NEVER A SENTENCE: the JSON in `<script id="data">`, the
 * `li[data-site]` rows, `a.walk`, `href="..."`. The one prose check (no
 * typed rollup outside the JSON) greps for the exact figure-plus-noun the
 * renderer would print, and nothing looser.
 *
 * STATIC ONLY: no browser, no network - verify_all.sh reaches neither.
 *
 *   node web/test_geomap.mjs
 *   node web/test_geomap.mjs --page=/tmp/broken.html --root=/tmp/broken-root
 *
 * `--page` and `--root` exist for the mutation tests: point the suite at a
 * broken copy of the page, or at a broken copy of the registries, and watch
 * the check that covers that fault fail by name.
 */
import { readFileSync, existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { deepStrictEqual } from 'node:assert';

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const arg = (name) => {
  const hit = args.find((a) => a.startsWith(`--${name}=`));
  return hit === undefined ? null : hit.slice(name.length + 3);
};
const ROOT = resolve(arg('root') !== null ? arg('root') : join(HERE, '..'));
const PAGE = resolve(arg('page') !== null ? arg('page') : join(HERE, 'trade_craft_geomap.html'));
const WEB = dirname(PAGE);

let n = 0, failed = 0;
function ok(text, cond) {
  if (cond) { n++; console.log(`  ok  ${text}`); }
  else { failed++; console.error(`FAIL  ${text}`); }
}
function same(a, b) {
  try { deepStrictEqual(a, b); return true; } catch { return false; }
}
// fail closed, by name: a registry or page field this suite reads must exist
function need(o, k, where) {
  if (o === null || typeof o !== 'object' || !(k in o))
    throw new Error(`test_geomap: ${where} has no field '${k}'`);
  return o[k];
}
const reg = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#x27;');

/* ------------------------------------------------------------ registries --- */
const network = reg('geo/registry/network.geojson');
const geo = reg('geo/registry/campuses_geo.json');
const spatial = reg('spatial/registry/geopose.json');
const restoration = reg('restoration/registry/restoration.json');
const campuses = need(reg('unions/registry/campuses.json'), 'campuses', 'campuses.json');
const halls = need(reg('pack/registry/halls.json'), 'halls', 'halls.json');
const lessons = need(reg('lessons/registry/lessons.json'), 'lessons', 'lessons.json');
const bindings = need(reg('sims/registry/sims.json'), 'hall_bindings', 'sims.json');
const units = need(reg('schools/registry/schools.json'), 'units', 'schools.json');

/* --------------------------------------------------------------- shipped --- */
const page = readFileSync(PAGE, 'utf8');
const dataMatch = page.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/);
ok('[shipped] the page embeds its data in <script id="data">', dataMatch !== null);
if (dataMatch === null) { console.error('FAIL  cannot continue without the embedded JSON'); process.exit(1); }
const D = JSON.parse(dataMatch[1]);
// the page with the JSON cut out: prose, markup, CSS and JS only
const outside = page.replace(dataMatch[0], '');

/* --- 1. embedded data equals the registries verbatim ---------------------- */
const stripPose = (f) => {
  const { geopose, ...rest } = f.properties;
  return { ...f, properties: rest };
};
ok('[shipped] D.network is geo/registry/network.geojson verbatim (only the joined geopose property added)',
  same({ ...D.network, features: D.network.features.map(stripPose) },
    { ...network, features: network.features.map(stripPose) })
  && network.features.every((f) => !('geopose' in f.properties)));
const poseByRef = Object.fromEntries(spatial.poses.map((p) => [p.subject.ref, p]));
ok('[shipped] every joined geopose property equals the spatial registry pose for that ref, and nothing else',
  D.network.features.every((f) => {
    const gp = f.properties.geopose;
    if (gp === undefined) return true;
    const pose = poseByRef[gp.ref];
    return pose !== undefined && same(gp, {
      ref: gp.ref, h_m: pose.geopose.position.h,
      position_provenance: pose.provenance.position_horizontal });
  }));
ok('[shipped] D.anchors is geo/registry/campuses_geo.json#anchors verbatim',
  same(D.anchors, need(geo, 'anchors', 'campuses_geo.json')));
ok('[shipped] D.restorationSites is restoration/registry/restoration.json#sites verbatim - all of them, the unpinned one included',
  same(D.restorationSites, need(restoration, 'sites', 'restoration.json')));
ok('[shipped] D.city and D.honesty are the geo registry\'s own, verbatim',
  same(D.city, geo.city) && same(D.honesty, geo.honesty));

/* --- 2. per-campus rollups recomputed --------------------------------------- */
const hallSlugs = new Set(halls.map((h) => need(h, 'slug', 'halls.json#halls[]')));
const hallsWithLesson = new Set(Object.values(lessons).map((l) => need(l, 'hall', 'lessons.json#lessons')));
const flippedHalls = units.map((u) => need(u, 'hall', 'schools.json#units[]'));
const rollups = {};
for (const [slug, c] of Object.entries(campuses)) {
  const hs = need(c, 'halls', `campuses.json#campuses.${slug}`);
  rollups[slug] = {
    name: need(c, 'name', `campuses.json#campuses.${slug}`),
    flagship: need(c, 'flagship', `campuses.json#campuses.${slug}`),
    halls: hs,
    hallsCount: hs.length,
    hallsWithLesson: hs.filter((h) => hallsWithLesson.has(h)).length,
    hallsBindingSeat: hs.filter((h) => h in bindings).length,
    flippedUnits: flippedHalls.filter((h) => hs.includes(h)).length,
  };
}
ok('[registry] every hall a campus lists exists in pack/registry/halls.json',
  Object.values(rollups).every((r) => r.halls.every((h) => hallSlugs.has(h))));
ok('[shipped] D.rollups carries exactly the campuses of unions/registry/campuses.json',
  same(Object.keys(D.rollups).sort(), Object.keys(rollups).sort()));
for (const slug of Object.keys(rollups)) {
  ok(`[shipped] ${slug}: halls / with a lesson / binding a seat / flipped units / flagship recomputed and equal `
    + `(${rollups[slug].hallsCount}/${rollups[slug].hallsWithLesson}/${rollups[slug].hallsBindingSeat}/${rollups[slug].flippedUnits}/${rollups[slug].flagship})`,
    same(D.rollups[slug], rollups[slug]));
}
ok('[shipped] the campus popup and panel render the rollups from D.rollups (rollupList), never from typed markup',
  outside.includes('function rollupList(slug)') && outside.includes('D.rollups[slug]')
  && outside.includes('rollupList(p.slug)') && outside.includes("getElementById('campusList')"));

/* --- 3. exactly one flagship ----------------------------------------------- */
const regFlag = Object.entries(campuses).filter(([, c]) => c.flagship === true).map(([s]) => s);
const pageFlag = Object.entries(D.rollups).filter(([, r]) => r.flagship === true).map(([s]) => s);
ok('[registry] exactly one campus is the flagship', regFlag.length === 1);
ok(`[shipped] exactly one flagship on the page, the registry's own (${regFlag[0]})`,
  pageFlag.length === 1 && pageFlag[0] === regFlag[0] && D.flagship === regFlag[0]);

/* --- 4. anchor provenance ---------------------------------------------------- */
const anchorPv = { RECORDED: 0, AUTHORED: 0, total: 0 };
const anchorByRef = {};
for (const [near, lst] of Object.entries(geo.anchors)) {
  for (const a of lst) {
    const pv = need(a, 'provenance', `campuses_geo.json#anchors.${near}[]`);
    anchorPv[pv] += 1; anchorPv.total += 1;
    anchorByRef[`${near}/${a.name}`] = a;
  }
}
ok(`[registry] anchor provenance is only RECORDED or AUTHORED (${anchorPv.RECORDED} RECORDED / ${anchorPv.AUTHORED} AUTHORED of ${anchorPv.total})`,
  anchorPv.RECORDED + anchorPv.AUTHORED === anchorPv.total && anchorPv.total > 0);
ok('[shipped] D.anchorProvenance equals the split recomputed from the registry',
  same(D.anchorProvenance, anchorPv));
const pageAnchors = D.network.features.filter((f) => f.properties.kind === 'anchor');
ok(`[shipped] the map draws every anchor of the registry (${pageAnchors.length})`,
  pageAnchors.length === anchorPv.total);
ok('[shipped] no anchor\'s provenance or source changed on the way to the page - each equals the registry\'s own, verbatim',
  pageAnchors.every((f) => {
    const a = anchorByRef[`${f.properties.near}/${f.properties.name}`];
    return a !== undefined && a.provenance === f.properties.provenance
      && a.source === f.properties.source;
  }));
ok('[shipped] the anchors layer is styled by each feature\'s own provenance (a match expression on the RECORDED word)',
  /'circle-color': \['match', \['get', 'provenance'\],\s*'RECORDED'/.test(outside)
  && /'circle-stroke-color': \['match', \['get', 'provenance'\],\s*'RECORDED'/.test(outside));
ok('[shipped] the legend carries one row per anchor class, with counts filled from D.anchorProvenance - not typed',
  ['RECORDED', 'AUTHORED', 'total'].every((k) => outside.includes(`data-anchor-count="${k}"`))
  && outside.includes('D.anchorProvenance[el.dataset.anchorCount]'));
ok('[shipped] an anchor popup prints its own source string verbatim (p.source) and its provenance chip (p.provenance)',
  outside.includes('${p.source}') && outside.includes('${p.provenance}'));

/* --- 5. restoration: walkable links, non-walkable refusals ------------------ */
const sites = restoration.sites;
const notWalkable = sites.filter((s) => need(s, 'walkable', `restoration.json#sites[${s.id}]`) !== true);
const walkable = sites.filter((s) => s.walkable === true);
ok(`[registry] the sites split into ${walkable.length} walkable and ${notWalkable.length} non-walkable, each non-walkable one carrying a walkable_reason`,
  notWalkable.length > 0 && walkable.length > 0
  && notWalkable.every((s) => typeof s.walkable_reason === 'string' && s.walkable_reason.length > 0));
const rowOf = (id) => {
  const m = page.match(new RegExp(`<li data-site="${id}"[^>]*>([\\s\\S]*?)</li>`));
  return m === null ? null : m[0];
};
ok('[shipped] the sites panel lists every site of the registry as li[data-site]',
  sites.every((s) => rowOf(s.id) !== null));
for (const s of notWalkable) {
  const row = rowOf(s.id);
  ok(`[shipped] ${s.id}: not walkable - the row carries walkable_reason verbatim and no walk link`,
    row !== null && row.includes('data-walkable="false"')
    && row.includes(esc(s.walkable_reason))
    && !row.includes('class="walk"') && !row.includes('trade_craft_3d.html'));
  ok(`[shipped] ${s.id}: the embedded entry keeps walkable=false and its reason verbatim`,
    D.restorationSites.some((x) => x.id === s.id && x.walkable === false
      && x.walkable_reason === s.walkable_reason));
}
ok('[shipped] every walkable site row links into the 3D environment at its own campus, and only there',
  walkable.every((s) => {
    const row = rowOf(s.id);
    return row !== null && row.includes('data-walkable="true"')
      && row.includes(`<a class="walk" href="trade_craft_3d.html?campus=${s.campus}">`)
      && s.campus in rollups;
  }));
const siteList = page.match(/<ul id="siteList">([\s\S]*?)<\/ul>/);
const nWalkLinks = siteList === null ? -1
  : (siteList[1].match(/<a class="walk" /g) === null ? 0 : siteList[1].match(/<a class="walk" /g).length);
ok('[shipped] the walk link count on the static list equals the walkable count - none leaks to a refusal',
  nWalkLinks === walkable.length);
ok('[shipped] the marker popup routes through the same walkLine() gate (s.walkable === true) and prints s.walkable_reason otherwise',
  outside.includes('function walkLine(s)') && outside.includes('if (s.walkable === true)')
  && outside.includes('${s.walkable_reason}') && outside.includes('walkLine(s)'));

/* --- 6. every href resolves --------------------------------------------------- */
const citations = new Set(sites.map((s) => s.source_url));
const hrefs = [...outside.matchAll(/href="([^"]*)"/g)].map((m) => m[1].replace(/&amp;/g, '&'));
const bad = [];
for (const h of hrefs) {
  if (h.includes('${')) continue; // a JS template, rendered from D at view time
  if (/^https?:\/\//.test(h)) { if (!citations.has(h)) bad.push(h); continue; }
  if (h.startsWith('data:image/svg+xml')) { if (!outside.includes(`rel="icon" href="${h}"`)) bad.push(h); continue; }
  const file = h.split('?')[0].split('#')[0];
  // a fragment-only link (the site nav's skip link) must land on an id this page carries
  if (file === '') { const frag = h.slice(1); if (!frag || !outside.includes(`id="${frag}"`)) bad.push(h); continue; }
  if (!existsSync(join(WEB, file))) bad.push(h);
}
ok(`[shipped] every href resolves to a file under web/ (${hrefs.length} hrefs; external ones are the registry's own citations)`
  + (bad.length ? ` - unresolved: ${bad.join(', ')}` : ''), bad.length === 0);
ok('[shipped] the walk hrefs point at the 3D environment, which exists under web/',
  existsSync(join(WEB, 'trade_craft_3d.html')));

/* --- 7. no typed count outside the JSON ------------------------------------------ */
// the exact figure-plus-noun the renderer prints; a typed copy anywhere in
// the prose, markup or JS would match here
const typed = [];
for (const r of Object.values(rollups)) {
  for (const [v, noun] of [[r.hallsCount, 'halls on this campus'], [r.hallsWithLesson, 'halls with a lesson'],
    [r.hallsBindingSeat, 'halls binding a seat'], [r.flippedUnits, 'flipped-classroom units']]) {
    const re = new RegExp(`(?:>|\\b)${v}(?:</b>)?\\s+${noun}`);
    if (re.test(outside)) typed.push(`${v} ${noun}`);
  }
}
for (const k of ['RECORDED', 'AUTHORED', 'total']) {
  const re = new RegExp(`(?:>|\\b)${anchorPv[k]}(?:</b>)?\\s+(?:of\\s+)?(?:${k}|anchors)`);
  if (re.test(outside)) typed.push(`${anchorPv[k]} ${k}`);
}
ok('[shipped] no rollup or anchor count is typed anywhere outside the JSON'
  + (typed.length ? ` - typed: ${typed.join(', ')}` : ''), typed.length === 0);

/* --- 8. generator discipline ---------------------------------------------------- */
const gen = readFileSync(join(HERE, 'build_geomap.py'), 'utf8').replace(/#.*$/gm, '');
ok('[generator] build_geomap.py fails closed by name (need()) and takes no `.get(k, default)` on a registry field',
  gen.includes('def need(d, k, where):') && !/\.get\([^)]*,[^)]*\)/.test(gen));

// a campus label must never be covered: restoration labels hang below their point,
// campus labels stand above theirs and stack on top (Treasure Island's campus and
// its naval-station site share coordinates; the site's label swallowed the clicks)
{
  const css = (sel) => { const m = page.match(new RegExp('\\.' + sel + '\\{[^}]*\\}')); return m ? m[0] : ''; };
  const z = (rule) => { const m = rule.match(/z-index:(\d+)/); return m ? Number(m[1]) : null; };
  const zc = z(css('campus-marker')), zr = z(css('restoration-marker'));
  const restAnchor = page.match(/popupForRestoration\(s\); \}\);[\s\S]*?anchor: '(\w+)'/);
  const campAnchor = page.match(/popupFor\(f\); \}\);[\s\S]*?anchor: '(\w+)'/);
  ok('[shipped] campus labels stack above restoration labels and stand on the other side of their point, so a site that shares a campus\'s coordinates cannot cover it',
    zc !== null && zr !== null && zc > zr && !!restAnchor && !!campAnchor
    && restAnchor[1] === 'top' && campAnchor[1] === 'bottom',
    `campus z ${zc}, restoration z ${zr}, anchors ${campAnchor && campAnchor[1]}/${restAnchor && restAnchor[1]}`);
  ok('[shipped] the page has exactly one <h1>, and it is the brand line the bar already shows',
    (page.match(/<h1[\s>]/g) || []).length === 1 && /<h1 class="brand">/.test(page));
}
{
  // campus labels that collide at the opening zoom must be re-placed, at load and after every zoom,
  // and the pass must try a slot below its dot before giving up (the browser smoke measures the result)
  const body = page.slice(page.indexOf('function placeCampusLabels'), page.indexOf("map.on('zoomend', placeCampusLabels)"));
  ok('[shipped] colliding campus labels are re-placed at load and after every zoom, trying below, right and left of the dot',
    page.includes("map.on('load', placeCampusLabels)") && page.includes("map.on('zoomend', placeCampusLabels)")
    && body.includes('[0, 10 + h]') && body.includes("querySelectorAll('.restoration-marker')")
    && page.includes('campusLabels.push('),
    'placeCampusLabels is missing, not hooked to load and zoomend, or no longer avoids restoration markers');
}

/* --- 9. map chrome and declutter (the opening Bay Area view) ---------------------- */
{
  const body = page.slice(page.indexOf('function placeCampusLabels'), page.indexOf("map.on('zoomend', placeCampusLabels)"));
  ok('[shipped] only a pinned restoration site gets a marker (the unpinned one has lat/lng null, which MapLibre drew at 0,0)',
    /for \(const s of D\.restorationSites\.filter\(\(x\) => x\.pin === true\)\)/.test(page)
    && restoration.sites.some((s) => s.pin !== true && s.lat === null));
  ok('[shipped] label placement computes every rectangle from map.project(), never measuring a marker right after setOffset()',
    body.includes('map.project(ll)') && !/setOffset\(o\);\s*const r = c\.el\.getBoundingClientRect\(\)/.test(body)
    && !body.includes('c.el.getBoundingClientRect()'));
  ok('[shipped] restoration sites closer than one target fold into a counted cluster, rebuilt on every placement pass, that zooms to its own sites on click',
    /function foldRestoration\(\)/.test(page) && body.includes('foldRestoration();')
    && /className = 'rest-cluster'/.test(page) && /b\.textContent = String\(sites\.length\)/.test(page)
    && /map\.fitBounds\(\[\[w, so\], \[e, n\]\]/.test(page));
  ok('[shipped] a restoration name shows only where it collides with nothing placed; hover and keyboard focus always show it',
    body.includes("classList.add('show-label')") && body.includes("classList.remove('show-label')")
    && /\.restoration-marker:focus-visible \.rm-label\{display:block\}/.test(page.replace(/\s*\n\s*/g, '')) );
  ok('[shipped] campus and restoration markers are <button>s (Enter/Space open the same popup) named after MapLibre stamps its generic "Map marker" label',
    (page.match(/document\.createElement\('button'\)/g) || []).length >= 3
    && /\.addTo\(map\) \}\);\s*el\.setAttribute\('aria-label', s\.name/.test(page)
    && /el\.setAttribute\('aria-label', f\.properties\.name/.test(page));
  ok('[shipped] one popup at a time: the opener shows a selected state, a keyboard open focuses the popup, Escape closes it',
    /function showPopup\(/.test(page) && /\.campus-marker\.is-selected\{/.test(page)
    && /if \(byKeyboard && closeBtn\) closeBtn\.focus\(\)/.test(page)
    && /e\.key !== 'Escape'/.test(page) && /currentPopup\.remove\(\); return;/.test(page));
  ok('[shipped] the find box lists every campus and pinned site from D (no typed name) and opens the one picked',
    /<datalist id="findList"><\/datalist>/.test(page) && /FIND\.push\(\{ name: c\.f\.properties\.name/.test(page)
    && /FIND\.push\(\{ name: r\.s\.name/.test(page)
    && !Object.values(D.rollups).some((r) => outside.includes(`<option value="${r.name}"`)));
  ok('[shipped] the bar sits in flow and the zoom control is top-left, so neither hides under the bar or the right-hand panels',
    /#bar\{position:relative;/.test(page) && !/#bar\{position:fixed/.test(page)
    && /NavigationControl\(\{ showCompass: false \}\), 'top-left'\)/.test(page) && /<div id="mapwrap">/.test(page));
  ok('[shipped] the legend is a <details> (folded on a phone) with a row for the counted cluster it draws',
    /<details id="legend" class="tc-panel">/.test(page) && /class="sw-cluster"/.test(page)
    && /document\.getElementById\('legend'\)\.open = false/.test(page));
}

/* --- 10. the globe (MapLibre 5) ------------------------------------------------- */
{
  const body = page.slice(page.indexOf('function placeCampusLabels'), page.indexOf("map.on('zoomend', placeCampusLabels)"));
  ok('[shipped] the legend is collapsed on load (no `open` on the <details>, nothing opens it by script) and its summary keeps the provenance hint one click away',
    /<details id="legend"[^>]*>/.test(page) && !/<details id="legend"[^>]*\bopen\b[^>]*>/.test(page)
    && !/getElementById\('legend'\)\.open = true/.test(page) && !/getElementById\('legend'\)\.setAttribute\('open'/.test(page)
    && /<summary><b>Legend: the geo registry, drawn<\/b> <span class="lg-hint">what is RECORDED, DERIVED, AUTHORED, SCHEMATIC<\/span><\/summary>/.test(page));
  ok('[shipped] the style renders on a globe, and the opening view is framed on the campuses\' own coordinates (computed, not typed)',
    /projection: \{ type: 'globe' \}/.test(page) && /bounds: NETWORK_BOUNDS, fitBoundsOptions: \{ padding: fitPadding\(\) \}/.test(page)
    && /const CAMPUS_LL = D\.network\.features\.filter\(\(x\) => x\.properties\.slug\)/.test(page)
    && /network: NETWORK_BOUNDS,/.test(page) && !/center: \[-106, 34\]/.test(page));
  ok('[shipped] a pressed-state button switches globe <-> flat (mercator) with map.setProjection, and re-places the labels',
    /<button class="barbtn tc-btn tc-btn-ghost" id="projBtn" aria-pressed="true"/.test(page)
    && /map\.setProjection\(\{ type: projection \}\)/.test(page) && /projection === 'globe' \? 'mercator' : 'globe'/.test(page)
    && /projBtn\.setAttribute\('aria-pressed'/.test(page) && /map\.once\('idle', placeCampusLabels\)/.test(page));
  ok('[shipped] a marker on the far side of the globe is invisible and takes no click or Tab stop',
    (page.match(/opacityWhenCovered: '0'/g) || []).length === 4
    && /\.maplibregl-marker\.maplibregl-marker-covered\{visibility:hidden;pointer-events:none\}/.test(page)
    && body.includes("classList.contains('maplibregl-marker-covered')) continue;"));
  ok('[shipped] no campus label is placed under the open legend or the zoom control, or off the map\'s frame; a label with no clear slot folds to its initials',
    body.includes("document.getElementById('legend'), document.querySelector('.maplibregl-ctrl-top-left')")
    && body.includes('obstacles.some((q) => hit(r, q))') && body.includes('r.right > VW - 2')
    && body.includes("c.el.classList.add('compact')") && /el\.dataset\.short = f\.properties\.name/.test(page));
}

/* --- 11. the 3D globe: geo3d halls, camera, tour, environments ------------------- */
{
  const g3 = reg('geo3d/registry/geo3d.json');
  const G3 = need(D, 'geo3d', 'page D');
  const regHalls = Object.entries(g3.campuses).flatMap(([k, c]) => c.halls.map((h) => ({ ...h, campus: k })));
  const pageHalls = G3.halls.features;
  const byDist = Object.fromEntries(Object.values(g3.campuses).flatMap((c) => c.districts).map((d) => [d.key, d]));
  ok(`[shipped] D.geo3d.halls is geo3d/registry/geo3d.json's halls, one feature each (${regHalls.length}), same ring, wall height, roofline, district hue`,
    pageHalls.length === regHalls.length && regHalls.every((h) => {
      const f = pageHalls.find((x) => x.properties.slug === h.slug);
      return f && same(f.geometry.coordinates[0], h.polygon) && f.properties.h === h.h && f.properties.top === h.top
        && f.properties.roof === h.roof && f.properties.campus === h.campus && f.properties.district === h.district
        && f.properties.color === `hsl(${byDist[h.district].hue}, 50%, 45%)` && f.properties.name === h.name;
    }));
  ok('[shipped] D.geo3d.districts is one outline per registry district, the registry\'s own ring',
    G3.districts.features.length === Object.keys(byDist).length
    && G3.districts.features.every((f) => same(f.geometry.coordinates[0], byDist[f.properties.district].polygon)));
  const lessonsPer = {};
  for (const l of Object.values(lessons)) lessonsPer[l.hall] = (lessonsPer[l.hall] || 0) + 1;
  ok('[shipped] each hall\'s lesson count is recomputed from lessons/registry/lessons.json',
    pageHalls.every((f) => f.properties.lessons === (lessonsPer[f.properties.slug] || 0)));
  ok('[shipped] the geo3d stamp, placement sentence and projection formula are the registry\'s own, verbatim',
    G3.sourceStamp === g3.source_stamp && G3.placement === g3.placement && G3.projection === g3.projection
    && same(G3.counts, g3.counts));
  const hubs = Object.keys(g3.campuses).filter((k) => g3.campuses[k].halls.length === 0);
  ok(`[shipped] the ${hubs.length} campuses with no halls carry the registry's no-invention note, and no hall feature stands on any of them`,
    same(Object.keys(G3.noHalls).sort(), hubs.sort()) && hubs.every((k) => G3.noHalls[k] === g3.campuses[k].note)
    && !pageHalls.some((f) => hubs.includes(f.properties.campus)));
  ok('[shipped] the halls draw as a fill-extrusion, height and colour read from each feature (the registry\'s h and district hue)',
    /id: 'halls3d', type: 'fill-extrusion', source: 'halls3d'/.test(page)
    && /'fill-extrusion-color': \['get', 'color'\],\s*'fill-extrusion-height': \['get', 'h'\]/.test(page));
  ok('[shipped] a hall popup says SCHEMATIC, prints its lesson and task counts from the feature, and quotes the placement sentence',
    /popupForHall\(p, lngLat\)/.test(page) && /SCHEMATIC placement/.test(page) && /\$\{p\.lessons\}<\/b> lessons for this hall/.test(page)
    && /\$\{p\.tasks\}<\/b> simulated tasks at this hall/.test(page) && /\$\{ESC\(D\.geo3d\.placement\)\}/.test(page));
  // a door is only a door if the page behind it reads the parameter
  const b3d = readFileSync(join(ROOT, 'web/build_3d.py'), 'utf8');
  const bim = readFileSync(join(ROOT, 'web/build_interactive_map.py'), 'utf8');
  ok('[shipped] the hall door walks into the 3D page at ?hall=<slug>, and web/build_3d.py reads params.get(\'hall\')',
    /href="trade_craft_3d\.html\?hall=\$\{ESC\(p\.slug\)\}"/.test(page) && /params\.get\('hall'\)/.test(b3d));
  ok('[shipped] the interactive-map door uses ?hall=<slug>, which web/build_interactive_map.py reads',
    /href="trade_craft_interactive\.html\?hall=\$\{ESC\(p\.slug\)\}"/.test(page) && /params\.get\('hall'\)/.test(bim));
  ok('[shipped] a campus popup gains doors to the 3D page (?campus=, which build_3d.py reads), the 2D map and the interactive map, all under web/',
    /popupFor[\s\S]*rollupList\(p\.slug\) \+ campusDoors\(p\.slug\)/.test(page)
    && /href="trade_craft_3d\.html\?campus=\$\{slug\}"/.test(page) && /params\.get\('campus'\)/.test(b3d)
    && /href="trade_craft_map\.html"/.test(page) && /href="trade_craft_interactive\.html"/.test(page)
    && ['trade_craft_3d.html', 'trade_craft_map.html', 'trade_craft_interactive.html'].every((f) => existsSync(join(WEB, f))));
  ok('[shipped] the campus camera is pitched (58) and turned, and under prefers-reduced-motion it jumps instead of flying',
    /matchMedia\('\(prefers-reduced-motion: reduce\)'\)/.test(page) && /pitch: 58/.test(page)
    && /if \(REDUCED\) map\.jumpTo\(v\);\s*else map\.flyTo/.test(page));
  ok('[shipped] the tour visits every campus in unions/registry/campuses.json order',
    same(G3.tour, Object.keys(campuses)) && /tour\.campus = D\.geo3d\.tour\[tour\.idx\]/.test(page));
  ok('[shipped] the tour is a pressed-state <button>; pressing it again, Escape, or dragging the map stops it',
    /<button class="barbtn tc-btn tc-btn-ghost" id="tourBtn" aria-pressed="false"/.test(page)
    && /tourBtn\.addEventListener\('click', \(\) => \(tour\.on \? stopTour\(\) : startTour\(\)\)\)/.test(page)
    && /if \(tour\.on\) \{ stopTour\(\);/.test(page) && /map\.on\('dragstart', \(\) => stopTour\(\)\)/.test(page));
  ok('[shipped] the fly-to control is a labelled <select> whose options are generated from D.geo3d.tour (no typed campus)',
    /<select class="flysel" id="flySel" aria-label="[^"]+">/.test(page) && /flySel\.insertAdjacentHTML\('beforeend', D\.geo3d\.tour\.map/.test(page));
  const styleIds = [...page.matchAll(/\{ id: '([a-z0-9-]+)', type:/g)].map((m) => m[1]);
  const toggled = [...page.matchAll(/map: \[([^\]]*)\], (?:cls|sw)/g)].flatMap((m) => [...m[1].matchAll(/'([a-z0-9-]+)'/g)].map((x) => x[1]));
  ok(`[shipped] every layer the Layers panel toggles exists in the style (${toggled.length} layer ids), each toggle a labelled checkbox`,
    toggled.length >= 10 && toggled.every((id) => styleIds.includes(id))
    && /<label><input type="checkbox" checked data-layer="\$\{l\.key\}">/.test(page));
  ok('[shipped] a hall is hit-tested from D.geo3d footprints projected to the screen (MapLibre\'s globe answers no extrusion query)',
    /function hallAt\(pt\)/.test(page) && /for \(const f of D\.geo3d\.halls\.features\)/.test(page) && /const f = hallAt\(e\.point\)/.test(page));

  // worksites: at their place's own point, or off the globe - never invented
  const ws = need(reg('worksites/registry/worksites.json'), 'sites', 'worksites.json');
  const env = need(D, 'env', 'page D');
  const wsWant = ws.map((w) => {
    const p = w.place;
    if (p.kind === 'campus') return { id: w.id, ll: [geo.campuses[p.id].lng, geo.campuses[p.id].lat] };
    if (p.kind === 'restoration-site') { const r = restoration.sites.find((x) => x.id === p.id); return { id: w.id, ll: [r.lng, r.lat] }; }
    if (p.kind === 'space' && p.campus === null) return { id: w.id, ll: null };
    return { id: w.id, ll: [geo.campuses[p.campus].lng, geo.campuses[p.campus].lat] };
  });
  ok(`[shipped] every worksite (${ws.length}) stands at its own place's registry point, or - a space with no campus - is listed off the globe`,
    env.worksitesOn.length + env.worksitesOff.length === ws.length
    && wsWant.every((w) => w.ll === null
      ? env.worksitesOff.some((x) => x.id === w.id && !('lngLat' in x))
      : env.worksitesOn.some((x) => x.id === w.id && same(x.lngLat, w.ll))));
  ok('[shipped] every worksite links to its own section of the worksites page, which carries that id',
    [...env.worksitesOn, ...env.worksitesOff].every((w) => w.href === `trade_craft_worksites.html#site-${w.id}`
      && readFileSync(join(WEB, 'trade_craft_worksites.html'), 'utf8').includes(`id="site-${w.id}"`)));
  const k12 = need(reg('schools/registry/schools.json'), 'districts', 'schools.json');
  ok(`[shipped] the ${k12.length} K-12 districts stand at their campus's own point (no address), status and provenance verbatim, marked PROPOSED`,
    env.k12.length === k12.length && k12.every((d, i) => env.k12[i].district === d.district && env.k12[i].status === d.status
      && env.k12[i].provenance === d.provenance && same(env.k12[i].lngLat, [geo.campuses[d.campus].lng, geo.campuses[d.campus].lat]))
    && /<span class="pv prop">PROPOSED<\/span>/.test(page));
  const wl = need(reg('wilds/registry/wilds.json'), 'worlds', 'wilds.json');
  ok(`[shipped] the ${wl.length} wild worlds are listed NOT on the globe: AUTHORED, "only inspired by" their region in the registry's words, linked to the wilds page, with no coordinate`,
    env.wildsOff.length === wl.length && wl.every((w, i) => env.wildsOff[i].id === w.id && env.wildsOff[i].evokes === w.inspiration.evokes
      && env.wildsOff[i].standing === w.inspiration.standing && env.wildsOff[i].provenance === 'AUTHORED'
      && env.wildsOff[i].href === `trade_craft_wilds.html#${w.id}` && !('lngLat' in env.wildsOff[i]))
    && /only <i>inspired by<\/i>/.test(page) && !/envAdd\('wild/.test(page));
  const tasksPath = join(ROOT, 'tasks/registry/tasks.json');
  if (existsSync(tasksPath)) {
    const T = JSON.parse(readFileSync(tasksPath, 'utf8'));
    const onKinds = ['hall', 'campus', 'restoration-site'];
    const on = T.tasks.filter((t) => onKinds.includes(t.place.kind) && t.place.campus in campuses);
    ok(`[shipped] tasks: ${on.length} stand at their campus, ${T.tasks.length - on.length} are listed off the globe (spaces with no campus, AUTHORED wilds), ${T.tasks.length} in all`,
      env.tasks.state.state === 'built' && env.tasks.on.length === on.length && env.tasks.off.length === T.tasks.length - on.length
      && on.every((t) => env.tasks.on.some((x) => x.id === t.id && x.place.campus === t.place.campus))
      && !env.tasks.on.some((x) => x.place.kind === 'wilds-site'));
    ok('[shipped] every task keeps its registry launch: web/ stripped from the href for this page, or null with the registry\'s own why',
      T.tasks.every((t) => {
        const x = [...env.tasks.on, ...env.tasks.off].find((y) => y.id === t.id);
        return x && (t.launch.href === null ? x.href === null && x.why === t.launch.why
          : x.href === (t.launch.href.startsWith('web/') ? t.launch.href.slice(4) : '../' + t.launch.href));
      }));
    const tPerHall = {};
    for (const t of T.tasks) if (t.place.kind === 'hall') tPerHall[t.place.id] = (tPerHall[t.place.id] || 0) + 1;
    ok('[shipped] each hall\'s task count is recomputed from tasks/registry/tasks.json',
      pageHalls.every((f) => f.properties.tasks === (tPerHall[f.properties.slug] || 0)));
    ok('[shipped] the task honesty line is the registry\'s own practice sentence',
      env.tasks.state.honesty === T.honesty.practice && env.tasks.state.source_stamp === T.source_stamp);
  } else {
    ok('[shipped] with no tasks registry built, the page says so and lists no task', env.tasks.state.state === 'absent'
      && env.tasks.on.length === 0 && env.tasks.off.length === 0);
  }
  // no typed count for the new layers either
  const typed3 = [];
  for (const [v, noun] of [[g3.counts.halls, 'halls on'], [env.k12.length, 'K-12'], [wl.length, 'wild worlds']])
    if (new RegExp(`(?:>|\\b)${v}(?:</b>)?\\s+${noun}`).test(outside)) typed3.push(`${v} ${noun}`);
  ok('[shipped] no geo3d, K-12 or wilds count is typed outside the JSON' + (typed3.length ? ' - typed: ' + typed3.join(', ') : ''), typed3.length === 0);
  ok('[shipped] the canvas theme: body.tc-theme-canvas, tc-panel panels, tc-btn bar buttons, page tokens aliased to --tc-*, and no hero band',
    /<body class="tc-theme-canvas">/.test(page) && /<section class="panel tc-panel" id="layers"/.test(page)
    && /body\.tc-theme-canvas\{--plate:var\(--tc-plate\);--panel:var\(--tc-panel\);--ink:var\(--tc-ink\)/.test(page)
    && /body\.tc-theme-canvas \.tc-panel\{/.test(page) && !/class="ph"/.test(page));
  const genRaw = readFileSync(join(HERE, 'build_geomap.py'), 'utf8');
  const g3gen = genRaw.slice(genRaw.indexOf('# ------------------------------------------------------------ the 3D globe ---'),
    genRaw.indexOf("DATA = json.dumps({"));
  ok('[shipped] the site Style menu (5 styles, MEDIA) is in the nav and its remember-my-choice script runs after the page\'s own',
    /data-sitenav-style/.test(page) && /<script>\(\(\)=>\{var K='tc-style'/.test(page.slice(page.lastIndexOf('__geomap'))));
  ok('[generator] the geo3d / worksites / K-12 / wilds / tasks readers in build_geomap.py fail closed: need() on every field, no default-taking get',
    g3gen.length > 2000 && /need\(pl, 'kind'/.test(g3gen) && /need\(ins, 'evokes'/.test(g3gen) && /need\(d, 'status'/.test(g3gen)
    && !/\.get\(/.test(g3gen.replace(/#.*$/gm, '')));
}

if (failed) {
  console.error(`FAIL  web/test_geomap: ${failed} of ${n + failed} checks failed`);
  process.exit(1);
}
console.log(`web/test_geomap: ${n} checks passed`);
