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
  if (file === '' || !existsSync(join(WEB, file))) bad.push(h);
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

if (failed) {
  console.error(`FAIL  web/test_geomap: ${failed} of ${n + failed} checks failed`);
  process.exit(1);
}
console.log(`web/test_geomap: ${n} checks passed`);
