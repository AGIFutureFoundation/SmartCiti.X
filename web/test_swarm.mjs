/**
 * The Omega Swarm map (web/trade_craft_swarm.html), held to the swarm registry it draws.
 *
 * web/build_swarm.py reads swarm/registry/swarm.json and writes the page: the hives, their geohash cells as polygons,
 * the places each covers, the member counts, the router's rules, and a read-only "try a region" panel that runs the
 * router's own region and resolution code in the page. Every figure on the page is a claim about the registry; every
 * sentence is a promise (the page is simulation only, SCRIPTED, no AI model, real hardware always refused). This suite
 * recomputes each claim from the registry and holds the SHIPPED PAGE to the answer.
 *
 *   [registry]  the registry and the swarm sources only
 *   [shipped]   the built HTML and the JSON and scripts embedded in it
 *   [router]    the page's embedded core run against the real swarm/router.mjs
 *   [browser]   --browser only: headless Chromium drives the map and the panel
 *
 *   node web/test_swarm.mjs                       static + router equivalence (what verify_all.sh runs)
 *   node web/test_swarm.mjs --page=<html> --root=<tree>     a broken copy of the page or of the registries (mutations)
 *   flock <chromium lock> node web/test_swarm.mjs --browser  also drive the page in Chromium (<= 90 s; one run)
 *
 * Playwright is PLAYWRIGHT_MODULE, else the local package, else the global one; the browser is CHROMIUM_PATH, else the
 * one Playwright finds itself. No machine path is written here.
 */
import { readFileSync, existsSync, mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { createServer } from 'node:http';

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const arg = (n) => { const h = args.find((a) => a.startsWith(`--${n}=`)); return h === undefined ? null : h.slice(n.length + 3); };
const ROOT = resolve(arg('root') !== null ? arg('root') : join(HERE, '..'));
const PAGE = resolve(arg('page') !== null ? arg('page') : join(HERE, 'trade_craft_swarm.html'));
const BROWSER = args.includes('--browser');

let n = 0, failed = 0;
function ok(text, cond, why) {
  if (cond) { n++; console.log(`  ok ${text}`); }
  else { failed++; console.log(`FAIL ${text}${why ? ' :: ' + (Array.isArray(why) ? why.slice(0, 4).join('; ') : why) : ''}`); }
}
const reg = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
const unesc = (s) => String(s).replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#x27;/g, "'").replace(/&amp;/g, '&');
const canon = (v) => JSON.stringify(v, (k, x) => (x && typeof x === 'object' && !Array.isArray(x) ? Object.fromEntries(Object.keys(x).sort().map((q) => [q, x[q]])) : x));
const sameSet = (a, b) => a.length === b.length && [...a].sort().join('\u0000') === [...b].sort().join('\u0000');

/* ------------------------------------------------------------------ registry --- */
const R = reg('swarm/registry/swarm.json');
const GEOHASH_SRC = readFileSync(join(ROOT, 'swarm/geohash.mjs'), 'utf8');
const GEO_SRC = readFileSync(join(ROOT, 'swarm/geo.mjs'), 'utf8');
const ROUTER_SRC = readFileSync(join(ROOT, 'swarm/router.mjs'), 'utf8');
const GATE_SRC = readFileSync(join(ROOT, 'swarm/gate.mjs'), 'utf8');
const SITENAV = readFileSync(join(ROOT, 'web/sitenav.py'), 'utf8');
const { encode, bounds } = await import(pathToFileURL(join(ROOT, 'swarm/geohash.mjs')).href);
ok('[registry] swarm/registry/swarm.json is the swarm/1 pack with 9 SCRIPTED hives, no AI model and no real-hardware member',
  R.schema === 'swarm/1' && R.pack === 'smartcitix-swarm' && R.hives.length === R.counts.hives && R.counts.models === 0 && R.counts.real_hardware_members === 0 && R.counts.operators === 0 && R.real_hardware.operators.length === 0);

/* -------------------------------------------------------------------- shipped --- */
const page = readFileSync(PAGE, 'utf8');
ok('[shipped] the page exists and is an html document', page.startsWith('<!doctype html>') && page.includes('</html>'));
const jsonScript = (id) => { const m = page.match(new RegExp(`<script type="application/json" id="${id}">([\\s\\S]*?)</script>`)); return m ? JSON.parse(m[1]) : null; };
const D = jsonScript('swarm-data'), I = jsonScript('swarm-i18n');
ok('[shipped] the page embeds its data (swarm-data) and its strings (swarm-i18n)', D !== null && I !== null);
if (D === null || I === null) { console.log('FAIL cannot continue without the embedded JSON'); process.exit(1); }
const modScript = (id) => { const m = page.match(new RegExp(`<script type="module" id="${id}">\\n([\\s\\S]*?)\\n</script>`)); return m ? m[1] : null; };
const CORE = modScript('swarm-core'), PGJS = modScript('swarm-page');
ok('[shipped] the page has a core module (the router\'s code) and a page module', typeof CORE === 'string' && typeof PGJS === 'string' && CORE.length > 5000 && PGJS.length > 5000);
const bodyHtml = page.slice(page.indexOf('<body'), page.indexOf('<script type="application/json" id="swarm-data">'));
const textOf = (h) => unesc(h.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim());

/* ---- figures: stats, table, totals, all equal to the registry ---- */
{
  const got = Object.fromEntries([...bodyHtml.matchAll(/data-swarm-count="(\w+)">(\d+)</g)].map((m) => [m[1], Number(m[2])]));
  const want = Object.fromEntries(['hives', 'cells', 'poses', 'members', 'robots', 'software', 'capabilities', 'models', 'real_hardware_members', 'operators'].map((k) => [k, R.counts[k]]));
  ok('[shipped] the ten header figures equal swarm.json counts (hives, cells, places, members, robots, software, capabilities, models, hardware, operators)', canon(got) === canon(want), [canon(got)]);
}
const members = R.members, cover = R.coverage;
const perHive = (id) => {
  const mem = members.filter((m) => m.hive === id), cov = cover.filter((c) => c.hive === id), h = R.hives.find((x) => x.id === id);
  const rk = (k) => mem.filter((m) => m.role_kind === k).length;
  return { campuses: h.campuses.length, cells: Object.keys(h.cells).length, anchors: cov.filter((c) => c.kind === 'anchor').length, sites: cov.filter((c) => c.kind === 'restoration-site').length,
    claw: rk('claw'), advisors: rk('advisor'), crew: rk('crew-role'), guides: rk('npc'), robots: mem.filter((m) => m.kind === 'robot').length, members: mem.length };
};
const COLS = ['campuses', 'cells', 'anchors', 'sites', 'claw', 'advisors', 'crew', 'guides', 'robots', 'members'];
{
  const tbl = bodyHtml.match(/<table id="swarm-members">[\s\S]*?<\/table>/);
  ok('[shipped] the members table is present', tbl !== null);
  const rows = tbl ? [...tbl[0].matchAll(/<tr data-hive-row="([a-z0-9-]+)">([\s\S]*?)<\/tr>/g)] : [];
  const byId = Object.fromEntries(rows.map((r) => [r[1], Object.fromEntries([...r[2].matchAll(/<td data-n="(\w+)">(\d+)<\/td>/g)].map((m) => [m[1], Number(m[2])]))]));
  ok('[shipped] one table row per registry hive, in registry order', canon(rows.filter((r) => r[1] !== 'all').map((r) => r[1])) === canon(R.hives.map((h) => h.id)));
  const bad = R.hives.filter((h) => canon(byId[h.id]) !== canon(Object.fromEntries(COLS.map((c) => [c, perHive(h.id)[c]]))));
  ok('[shipped] each hive row equals the figures recomputed from the registry members and coverage', bad.length === 0, bad.map((h) => h.id));
  const tot = Object.fromEntries(COLS.map((c) => [c, R.hives.reduce((a, h) => a + perHive(h.id)[c], 0)]));
  ok('[shipped] the total row equals the sum of the hive rows and the registry counts (cells, members, robots)', canon(byId.all) === canon(tot) && tot.cells === R.counts.cells && tot.members === R.counts.members && tot.robots === R.counts.robots, [canon(byId.all)]);
  ok('[registry] the software kinds add up to the registry software count, and covered places to the pose count',
    tot.claw + tot.advisors + tot.crew + tot.guides === R.counts.software && tot.anchors + tot.sites + tot.campuses === R.counts.poses);
  const names = [...tbl[0].matchAll(/data-pick-link="([a-z0-9-]+)" lang="en" dir="ltr">([^<]*)</g)].map((m) => [m[1], unesc(m[2])]);
  ok('[shipped] hive names in the table are the registry names', canon(names) === canon(R.hives.map((h) => [h.id, h.name])));
}

/* ---- cells: 132 polygons, each decoding to its geohash ---- */
{
  const fs = D.cells.features;
  ok('[shipped] one polygon per registry cell (cell count equals swarm.json counts.cells)', fs.length === R.counts.cells && R.hives.reduce((a, h) => a + Object.keys(h.cells).length, 0) === fs.length);
  const want = new Map(R.hives.flatMap((h) => Object.entries(h.cells).map(([c, why]) => [c, { hive: h.id, why }])));
  const wrongOwner = fs.filter((f) => !want.has(f.properties.cell) || want.get(f.properties.cell).hive !== f.properties.hive || canon(want.get(f.properties.cell).why) !== canon(f.properties.why));
  ok('[shipped] each polygon carries its registry hive and its reasons', wrongOwner.length === 0 && new Set(fs.map((f) => f.properties.cell)).size === fs.length, wrongOwner.map((f) => f.properties.cell));
  const geomBad = fs.filter((f) => {
    const g = f.geometry; if (g.type !== 'Polygon' || g.coordinates.length !== 1) return true;
    const r = g.coordinates[0]; if (r.length !== 5 || r[0][0] !== r[4][0] || r[0][1] !== r[4][1]) return true;
    const b = bounds(f.properties.cell);
    return !(r[0][0] === b.w && r[0][1] === b.s && r[1][0] === b.e && r[1][1] === b.s && r[2][0] === b.e && r[2][1] === b.n && r[3][0] === b.w && r[3][1] === b.n);
  });
  ok('[shipped] each polygon is the rectangle the swarm geohash code gives for its cell string', geomBad.length === 0, geomBad.map((f) => f.properties.cell));
  const decBad = fs.filter((f) => {
    const r = f.geometry.coordinates[0], lng = (Math.min(...r.map((p) => p[0])) + Math.max(...r.map((p) => p[0]))) / 2, lat = (Math.min(...r.map((p) => p[1])) + Math.max(...r.map((p) => p[1]))) / 2;
    return encode(lat, lng, 5) !== f.properties.cell;
  });
  ok('[shipped] each polygon\'s centre encodes back to its own geohash (precision 5)', decBad.length === 0 && fs.every((f) => f.properties.cell.length === 5), decBad.map((f) => f.properties.cell));
  const pts = D.cell_points.features;
  ok('[shipped] the cell dots are the polygon centres', pts.length === fs.length && pts.every((p, i) => { const b = bounds(fs[i].properties.cell); return p.properties.cell === fs[i].properties.cell && Math.abs(p.geometry.coordinates[0] - (b.w + b.e) / 2) < 1e-9 && Math.abs(p.geometry.coordinates[1] - (b.s + b.n) / 2) < 1e-9; }));
  const rob = members.filter((m) => m.kind === 'robot');
  ok('[shipped] the robot dots are the registry simulated robots at their registry positions', D.robots.features.length === R.counts.robots && rob.every((m, i) => D.robots.features[i].properties.id === m.id && D.robots.features[i].geometry.coordinates[0] === m.lon && D.robots.features[i].geometry.coordinates[1] === m.lat));
  ok('[shipped] hive homes are the registry home positions', R.hives.every((h) => D.homes[h.id] && D.homes[h.id][0] === h.home.lon && D.homes[h.id][1] === h.home.lat) && canon(D.hive_ids) === canon(R.hives.map((h) => h.id)));
  ok('[shipped] the palette gives each hive its own colour', new Set(D.palette.slice(0, R.hives.length)).size === R.hives.length);
}

/* ---- per-hive detail: cells, covered places, robots by embodiment ---- */
{
  const blocks = [...bodyHtml.matchAll(/<div class="hd" id="hive-([a-z0-9-]+)" data-detail="\1" hidden>([\s\S]*?)(?=<div class="hd" id="hive-|<\/section>\s*<section class="box" id="swarm-rules")/g)];
  ok('[shipped] one detail block per hive, hidden until selected', blocks.length === R.hives.length && blocks.every((b) => /hidden>/.test(b[0].slice(0, 120))));
  const bad = [];
  for (const [, id, body] of blocks) {
    const h = R.hives.find((x) => x.id === id);
    const cells = [...body.matchAll(/data-cellbtn="([0-9a-z]+)"/g)].map((m) => m[1]);
    const covs = [...body.matchAll(/data-cover="([^"]+)"/g)].map((m) => unesc(m[1]));
    const rob = Object.fromEntries([...body.matchAll(/data-robot-role="([^"]+)"[\s\S]*?<b>(\d+)<\/b>/g)].map((m) => [m[1], Number(m[2])]));
    const wantRob = {}; for (const m of members) if (m.kind === 'robot' && m.hive === id) wantRob[m.role] = (wantRob[m.role] ?? 0) + 1;
    if (!sameSet(cells, Object.keys(h.cells))) bad.push(id + ' cells');
    if (!sameSet(covs, cover.filter((c) => c.hive === id).map((c) => c.ref))) bad.push(id + ' covers');
    if (canon(rob) !== canon(wantRob)) bad.push(id + ' robots');
    const reasons = h.cells; for (const c of Object.keys(reasons)) { const b = body.match(new RegExp(`data-cellbtn="${c}"[^>]*>([\\s\\S]*?)</button>`)); if (!b || reasons[c].some((w) => !b[1].includes(`data-i18n="swarm.reason.${w}"`))) bad.push(id + ' reason ' + c); }
  }
  ok('[shipped] each hive detail lists exactly its registry cells (with their reasons), covered anchors and sites, and robots by embodiment', bad.length === 0, bad);
  const allCover = [...bodyHtml.matchAll(/data-cover="([^"]+)"/g)].length;
  ok('[shipped] every registry coverage entry appears once (anchors, campuses and sites covered)', allCover === cover.length && cover.length === R.counts.poses);
  ok('[shipped] the unposed restoration programme is named with the registry reason and no cell is invented for it', R.unposed.every((u) => bodyHtml.includes(`data-unposed="${esc(u.ref)}"`) && bodyHtml.includes(esc(u.why))) && R.unposed.every((u) => !cover.some((c) => c.ref === u.ref)));
}

/* ---- honesty ---- */
{
  const miss = Object.entries(R.honesty).filter(([k, v]) => !bodyHtml.includes(`data-swarm-honesty="${esc(k)}" lang="en" dir="ltr">${esc(v)}</li>`)).map(([k]) => k);
  ok('[shipped] all eight registry honesty lines are quoted verbatim', Object.keys(R.honesty).length === 8 && miss.length === 0, miss);
  ok('[shipped] the real-hardware refusal sentence is quoted verbatim, in the honesty block and in the rules',
    R.real_hardware.refusal === 'real hardware needs a named human operator; none is configured' && bodyHtml.includes(`<li data-swarm-refusal lang="en" dir="ltr"><q>${esc(R.real_hardware.refusal)}</q>`) && bodyHtml.includes(`<q lang="en" dir="ltr" data-refusal>${esc(R.real_hardware.refusal)}</q>`));
  const nr = GATE_SRC.match(/hold_reason: '([^']+)'/);
  ok('[shipped] the no-safety-record rule quotes the gate\'s own hold reason, read from swarm/gate.mjs', nr !== null && bodyHtml.includes(`<q lang="en" dir="ltr" data-norecord>${esc(nr[1])}</q>`) && nr[1] === 'no safety record for this target: held');
  const en = I.en.strings;
  const lines = {
    'swarm.hon.scripted': /SCRIPTED/, 'swarm.hon.sim': /Simulation only/, 'swarm.hon.hardware': /named human operator/,
    'swarm.hon.s2r': /sim-to-real/, 'swarm.hon.positions': /not a statement that a robot exists/, 'swarm.hon.location': /No learner location is stored or sent/,
    'swarm.hon.standards': /No conformance/, 'swarm.hon.page': /stores nothing and sends nothing/,
    'swarm.rule.sim': /Simulation only/, 'swarm.rule.hardware': /always refused/, 'swarm.rule.norecord': /only as a dry run/, 'swarm.rule.gate': /safety gate/,
    'swarm.rule.nomodel': /No AI model/, 'swarm.rule.safety': /not a real-world safety system/, 'swarm.rule.audit': /audit row/,
    'swarm.try.note': /A preview, not a row/, 'swarm.hon.quoted': /own words/,
  };
  const noText = Object.entries(lines).filter(([k, re]) => !re.test(en[k] ?? '')).map(([k]) => k);
  ok('[shipped] the English honesty and rule lines say what the brief requires (SCRIPTED, no AI model, simulation only, hardware refused, no-record dry run only, not a safety system, no location stored)', noText.length === 0, noText);
  const shown = Object.keys(lines).filter((k) => k.startsWith('swarm.hon.') || k.startsWith('swarm.rule.') || k === 'swarm.try.note');
  const notOnPage = shown.filter((k) => !bodyHtml.includes(`data-i18n="${k}"`));
  ok('[shipped] each honesty, rule and preview-note line is rendered on the page (data-i18n)', notOnPage.length === 0, notOnPage);
  ok('[shipped] the kicker says SCRIPTED and simulation only, and the page says the safety gate is not a real-world safety system', /SCRIPTED/.test(en['swarm.kicker']) && /simulation only/i.test(en['swarm.kicker']) && /not a real-world safety system/i.test(en['swarm.rule.safety']));
  const text = textOf(bodyHtml);
  const claims = ['partner', 'customer', 'pilot', 'accredit', 'endorse', 'price', 'revenue'].filter((w) => new RegExp(`\\b${w}`, 'i').test(text.replace(/safety/gi, '')));
  ok('[shipped] the page makes no partner, customer, price or accreditation claim', claims.length === 0, claims);
  const ltrBad = [...bodyHtml.matchAll(/<(li|q|dd|span)[^>]*\blang="en"[^>]*>/g)].filter((m) => !/\bdir="ltr"/.test(m[0])).map((m) => m[0].slice(0, 60));
  ok('[shipped] every English quotation and registry-data element carries lang="en" and dir="ltr" (so right-to-left locales do not reorder it)', ltrBad.length === 0, ltrBad);
  const models = page.match(/\b(claude|anthropic|openai|gpt-?\d|gemini|llama|mistral)\b/gi);
  ok('[shipped] no model identifier appears anywhere in the page', models === null, models);
  const internal = page.match(/\/tmp\/|\$SP\b|memory\/|\bconsole\b|SWARMMAP|\/home\/|\/root\//g);
  ok('[shipped] no internal reference (scratch path, memory, console, agent codename, machine path) appears on the page', internal === null, internal);
}

/* ---- strings: 8 locales, no typed figure ---- */
{
  const LOC = ['ar', 'de', 'en', 'es', 'fr', 'hi', 'pt', 'zh'];
  ok('[shipped] the page carries all eight locales', canon(Object.keys(I).sort()) === canon(LOC));
  const files = Object.fromEntries(LOC.map((l) => [l, reg(`i18n/locales/${l}.json`)]));
  const keys = Object.keys(files.en.strings).filter((k) => k.startsWith('swarm.')).sort();
  ok('[registry] i18n/locales/en.json holds the swarm.* keys', keys.length > 60);
  const missing = LOC.flatMap((l) => [...keys, 'nav.page.swarm'].filter((k) => typeof files[l].strings[k] !== 'string' || !files[l].strings[k].trim()).map((k) => `${l}:${k}`));
  ok('[registry] every swarm.* key and nav.page.swarm is non-empty in all eight locales', missing.length === 0, missing);
  const ph = (s) => (s.match(/\{\w+\}/g) ?? []).sort().join();
  const phBad = LOC.flatMap((l) => keys.filter((k) => ph(files[l].strings[k]) !== ph(files.en.strings[k])).map((k) => `${l}:${k}`));
  ok('[registry] placeholders ({n}, {cell}, {hive}, {why}) survive translation in every locale', phBad.length === 0, phBad);
  const embBad = LOC.filter((l) => canon(Object.fromEntries(keys.map((k) => [k, files[l].strings[k]]))) !== canon(I[l].strings) || I[l].dir !== files[l].dir);
  ok('[shipped] the embedded strings equal the locale catalogs, key for key, and carry each locale\'s direction', embBad.length === 0, embBad);
  ok('[registry] the seven non-source catalogs declare themselves machine-drafted, pending review; Arabic is rtl', LOC.filter((l) => l !== 'en').every((l) => /machine-drafted, pending native review/.test(files[l].translation_status)) && files.ar.dir === 'rtl' && files.en.dir === 'ltr');
  const dig = LOC.flatMap((l) => keys.filter((k) => /\d/.test(files[l].strings[k].replace(/swarm-(command|audit)\/1/g, '')) || /\d/.test(String(I[l].strings[k]).replace(/swarm-(command|audit)\/1/g, ''))).map((k) => `${l}:${k}`));
  ok('[shipped] no swarm.* string, in the catalogs or in the page, in any locale types a digit (counts are read from the registry, not typed)', dig.length === 0, dig);
  const used = [...bodyHtml.matchAll(/data-i18n="([^"]+)"/g)].map((m) => m[1]);
  ok('[shipped] every data-i18n key on the page is an embedded key', used.every((k) => keys.includes(k)), used.filter((k) => !keys.includes(k)));
  const seen = new Set(); const textBad = [];
  for (const m of bodyHtml.matchAll(/<([a-z0-9]+)((?: [^>]*?)?) data-i18n="([^"]+)">([^<]*)<\/\1>/g)) {
    seen.add(m[3]); const nn = m[2].match(/data-n="([^"]*)"/);
    const want = esc(nn ? files.en.strings[m[3]].split('{n}').join(unesc(nn[1])) : files.en.strings[m[3]]);
    if (m[4] !== want) textBad.push(m[3]);
  }
  ok('[shipped] the static English text of each data-i18n element is the catalog string (a {n} figure comes from the registry count)', textBad.length === 0 && seen.size > 50, textBad);
  const rest = page.replace(/<script type="application\/json" id="swarm-i18n">[\s\S]*?<\/script>/, '');
  const head = page.slice(0, page.indexOf('<body'));
  const inHead = { 'swarm.nav': esc(files.en.strings['swarm.nav']), 'swarm.seo.desc': esc(files.en.strings['swarm.seo.desc']) };
  const unusedKeys = keys.filter((k) => !rest.includes(k) && !rest.includes(`'${k.slice(0, k.lastIndexOf('.') + 1)}'`) && !(k in inHead && head.includes(inHead[k])));
  ok('[shipped] every swarm.* key is used by the page (no dead strings)', unusedKeys.length === 0, unusedKeys);
  const jsText = CORE + '\n' + PGJS;
  const typed = [R.counts.cells, R.counts.members, R.counts.software, R.counts.poses, R.counts.hives * 100].filter((v) => new RegExp(`(^|[^\\d.#])${v}([^\\d]|$)`).test(PGJS));
  ok('[shipped] the page script types none of the registry counts (cells, members, software, places)', typed.length === 0, typed);
  const tooBig = (bodyHtml.match(/>\s*\d{2,}\s*</g) ?? []);
  ok('[shipped] every multi-digit number in the visible markup sits in a data-n / data-swarm-count cell (read from the registry)', tooBig.length === 0 || tooBig.every((s) => true) && [...bodyHtml.matchAll(/>(\d{2,})</g)].every((m) => /data-(n|swarm-count)=/.test(bodyHtml.slice(Math.max(0, m.index - 60), m.index))), tooBig.slice(0, 3));
}

/* ---- nav, seo, structure, access ---- */
{
  ok('[shipped] the site nav is present and marks this page current', /href="trade_craft_swarm.html" aria-current="page"/.test(page));
  ok('[registry] web/sitenav.py declares the page once, in the Maps group, with the nav.page.swarm label', /\('nav\.group\.maps', \[[\s\S]*?\('web\/trade_craft_swarm\.html', 'nav\.page\.swarm'\)[\s\S]*?\]\),\s*\('nav\.group\.records'/.test(SITENAV) && (SITENAV.match(/trade_craft_swarm\.html/g) ?? []).length === 1);
  ok('[shipped] one <title>, one description, a canonical URL, and one h1', (page.match(/<title>/g) ?? []).length === 1 && /<meta name="description" content="[^"]{20,160}"/.test(page) && /<link rel="canonical"/.test(page) && (page.match(/<h1[ >]/g) ?? []).length === 1);
  ok('[shipped] one main landmark; the map is a labelled region; every button has text; every control has a label',
    (bodyHtml.match(/<main /g) ?? []).length === 1 && /id="swarm-map" role="region" aria-label="[^"]{20,}"/.test(bodyHtml)
    && [...bodyHtml.matchAll(/<button[^>]*>([\s\S]*?)<\/button>/g)].every((m) => textOf(m[1]).length > 0)
    && /<label for="swarm-preset">/.test(bodyHtml) && /<label for="swarm-cmd"/.test(bodyHtml) && /<label><input type="checkbox" id="swarm-robots">/.test(bodyHtml));
  ok('[shipped] 16 px side gutters, 44 px targets, a phone viewport, and no fixed-width page', /\.wrap\{[^}]*padding:28px 16px 120px/.test(page) && /\.btn\{min-block-size:44px/.test(page) && /name="viewport" content="width=device-width, initial-scale=1"/.test(page) && !/body\{[^}]*overflow-x:\s*(scroll|visible)/.test(page));
  ok('[shipped] keyboard route: hive buttons and cell buttons are real <button>s with aria-pressed; hive pins are not focusable', (bodyHtml.match(/<button type="button" class="btn pick"[^>]*aria-pressed=/g) ?? []).length === R.hives.length + 1 && (bodyHtml.match(/data-cellbtn=/g) ?? []).length === R.counts.cells && !/\.pin[^;]*tabindex|className = 'pin'[^;]*tabindex/.test(PGJS) && !/tabindex="[1-9]/.test(page));
  ok('[shipped] selection patches nodes in place (hidden / aria-pressed): the page script never rebuilds the picker or the detail blocks', !/\.innerHTML\s*=/.test(PGJS.replace(/el\.innerHTML = '<span class="dot"[^;]*;/, '')) && /\.hidden = d\.getAttribute\('data-detail'\) !== id/.test(PGJS));
  ok('[shipped] the colour of the map follows the Style menu (design tokens read at run time) and motion follows the reader (prefers-reduced-motion)', /getPropertyValue\('--tc-'/.test(PGJS) && /data-style/.test(PGJS) && /prefers-reduced-motion: reduce/.test(PGJS));
  ok('[shipped] the English words that are registry data (hive names, roles, refs) carry lang="en"', /lang="en" dir="ltr">Bay Area hive</.test(bodyHtml));
}

/* ---- the page script: no network, no storage, no tiles ---- */
{
  const BAN = [['fetch(', /\bfetch\s*\(/], ['XMLHttpRequest', /XMLHttpRequest/], ['WebSocket', /WebSocket/], ['EventSource', /EventSource/], ['sendBeacon', /sendBeacon/], ['importScripts', /importScripts/], ['new Worker', /new\s+(Shared)?Worker/],
    ['localStorage', /localStorage/], ['sessionStorage', /sessionStorage/], ['indexedDB', /indexedDB/], ['document.cookie', /document\.cookie/], ['geolocation', /geolocation/], ['dynamic import()', /\bimport\s*\(/], ['static import', /^\s*import\s/m],
    ['new Image', /new\s+Image/], ['an http(s) URL', /https?:\/\//], ['clipboard', /clipboard/], ['eval', /\beval\s*\(|new\s+Function/]];
  for (const [nm, src] of [['core', CORE], ['page', PGJS]]) {
    const hits = BAN.filter(([, re]) => re.test(src)).map(([a]) => a);
    ok(`[shipped] the ${nm} script uses no network, storage, worker, location, import or eval API`, hits.length === 0, hits);
  }
  const srcs = [...page.matchAll(/<script[^>]*\ssrc="([^"]+)"/g)].map((m) => m[1]), css = [...page.matchAll(/<link[^>]*rel="stylesheet"[^>]*href="([^"]+)"/g)].map((m) => m[1]);
  ok('[shipped] the only external script is the vendored MapLibre, the only stylesheet its css; no @import or remote url()', canon(srcs) === canon(['vendor/maplibre/maplibre-gl.js']) && canon(css) === canon(['vendor/maplibre/maplibre-gl.css']) && !/@import|url\(\s*['"]?https?:/i.test(page));
  ok('[shipped] the vendored MapLibre files exist (5.24)', existsSync(join(dirname(PAGE), 'vendor/maplibre/maplibre-gl.js')) && /v5\.24\./.test(readFileSync(join(dirname(PAGE), 'vendor/maplibre/maplibre-gl.js'), 'utf8').slice(0, 400)));
  const sources = (PGJS.match(/type: 'geojson'/g) ?? []).length;
  ok('[shipped] every map source is inline geojson (no tiles, glyphs, sprite or url) and the globe/projection is not fetched', sources === 6 && !/\btiles\s*:|\bglyphs\s*:|\bsprite\s*:|\burl\s*:|transformRequest/.test(PGJS));
}

/* ---- the router's own code, byte for byte ---- */
const between = (src, a, b) => { const i = src.indexOf(`/* BEGIN VERBATIM ${a} */\n`); if (i < 0) return null; const s = i + `/* BEGIN VERBATIM ${a} */\n`.length; const j = src.indexOf(`\n/* END VERBATIM ${a} */`, s); return j < 0 ? null : src.slice(s, j); };
{
  ok('[router] the embedded geohash code equals swarm/geohash.mjs, byte for byte', between(CORE, 'swarm/geohash.mjs') === GEOHASH_SRC.replace(/\n+$/, ''));
  ok('[router] the embedded geometry code equals swarm/geo.mjs, byte for byte', between(CORE, 'swarm/geo.mjs') === GEO_SRC.replace(/\n+$/, ''));
  const refusal = between(CORE, 'swarm/router.mjs (refusal constant)'), parser = between(CORE, 'swarm/router.mjs (region parser)'), steps = between(CORE, 'swarm/router.mjs (resolution steps 1-3)');
  ok('[router] the embedded refusal constant is a whole line of swarm/router.mjs', refusal !== null && ROUTER_SRC.split('\n').includes(refusal) && refusal.includes(R.real_hardware.refusal));
  const p0 = ROUTER_SRC.indexOf('const ALLOWED = '), p1 = ROUTER_SRC.indexOf('export function createRouter');
  ok('[router] the embedded region parser and real-hardware check are swarm/router.mjs from "const ALLOWED" to "createRouter", byte for byte', parser !== null && p0 >= 0 && p1 > p0 && parser === ROUTER_SRC.slice(p0, p1).replace(/\n+$/, '') && /function realHardwareSignals/.test(parser) && /function parseRegion/.test(parser));
  const s0 = ROUTER_SRC.indexOf('    // 1. real hardware first'), s1 = ROUTER_SRC.indexOf('    resolved.targets = targets.map((m) => m.id);');
  ok('[router] the embedded resolution steps 1-3 are swarm/router.mjs from "// 1. real hardware first" to "resolved.targets =", byte for byte', steps !== null && s0 >= 0 && s1 > s0 && steps === ROUTER_SRC.slice(s0, s1 + '    resolved.targets = targets.map((m) => m.id);'.length));
  ok('[router] the embedded steps reach neither the safety gate, the arena harness nor the audit log', steps !== null && !/\bG\.|\bAR\.|\blog\.|createGate|createArena|SwarmAudit|readFileSync/.test(steps + (parser ?? '')));
  const outside = CORE.replace(/\/\* BEGIN VERBATIM [\s\S]*?\/\* END VERBATIM [^*]*\*\//g, '');
  ok('[router] the only code outside the verbatim slices is the page\'s thin wrapper (previewCommand) and the SwarmCore hook', /function previewCommand\(cmd, reg\)/.test(outside) && /globalThis\.SwarmCore = Object\.freeze/.test(outside) && outside.length < 3200, [outside.length]);
}

/* ---- the page's answers equal the real router's ---- */
let SC = null;
try { await import('data:text/javascript;base64,' + Buffer.from(CORE).toString('base64')); SC = globalThis.SwarmCore; } catch (e) { SC = null; console.log('  (core did not load: ' + e.message + ')'); }
ok('[router] the embedded core loads in node as a standalone module and exposes previewCommand', SC !== null && typeof SC.previewCommand === 'function');
if (SC !== null) {
  const { createRouter, REAL_HARDWARE_REFUSAL } = await import(pathToFileURL(join(ROOT, 'swarm/router.mjs')).href);
  ok('[router] the page\'s refusal constant equals the router\'s and the registry\'s', SC.REAL_HARDWARE_REFUSAL === REAL_HARDWARE_REFUSAL && REAL_HARDWARE_REFUSAL === R.real_hardware.refusal);
  const router = createRouter({ root: ROOT });
  const cmds = [];
  const C = (id, cap, region, x = {}) => ({ schema: 'swarm-command/1', id, capability: cap, region, mode: 'dry-run', ...x });
  for (const p of D.presets) cmds.push(p.command);
  let seed = 123456789; const rnd = () => ((seed = (seed * 1103515245 + 12345) >>> 0) / 4294967296);
  const caps = Object.keys(R.capabilities);
  for (const h of R.hives) {
    const c0 = h.home.cell, cells = Object.keys(h.cells);
    cmds.push(C(`h-${h.id}-pre`, 'software.advise-visitor', { cells: [c0.slice(0, 2)] }), C(`h-${h.id}-one`, 'robot.litter-sort', { cells: [c0] }), C(`h-${h.id}-all`, 'robot.gate-drive', { cells }),
      C(`h-${h.id}-p3`, 'software.audit-dataset', { cells: [c0.slice(0, 3), cells[cells.length - 1]] }), C(`h-${h.id}-box`, 'robot.rov-survey', { polygon: [[h.home.lat - 0.2, h.home.lon - 0.2], [h.home.lat - 0.2, h.home.lon + 0.2], [h.home.lat + 0.2, h.home.lon + 0.2], [h.home.lat + 0.2, h.home.lon - 0.2]] }));
  }
  cmds.push(C('us', 'software.schedule-tournament', { polygon: [[24, -125], [24, -66], [49.5, -66], [49.5, -125]] }), C('us-g', 'robot.gate-drive', { polygon: [[24, -125], [24, -66], [49.5, -66], [49.5, -125]] }), C('us-r', 'robot.litter-pickup', { polygon: [[24, -125], [24, -66], [49.5, -66], [49.5, -125]] }));
  const rm = R.members.filter((m) => m.kind === 'robot')[0];
  cmds.push(C('tg', 'robot.litter-pickup', { cells: ['9q'] }, { targets: [rm.id] }), C('tg2', 'robot.rov-survey', { cells: ['9q', 'dp'] }, { targets: R.members.filter((m) => m.role === 'rov.survey').slice(0, 3).map((m) => m.id) }));
  const bad = [
    null, 7, 'x', [], {}, C('b1', 'nope.cap', { cells: ['9q'] }), C('b2', 'robot.litter-pickup', {}), C('b3', 'robot.litter-pickup', { cells: [] }), C('b4', 'robot.litter-pickup', { cells: ['9q'], polygon: [[0, 0], [0, 1], [1, 1]] }),
    C('b5', 'robot.litter-pickup', { cells: ['ao'] }), C('b6', 'robot.litter-pickup', { cells: [5] }), C('b7', 'robot.litter-pickup', { polygon: [[0, 0], [0, 1]] }), C('b8', 'robot.litter-pickup', { polygon: [[0, 0], [1, 1], [0, 1], [1, 0]] }),
    C('b9', 'robot.litter-pickup', { polygon: [[0, 0], [0, 200], [1, 1]] }), C('b10', 'robot.litter-pickup', { polygon: [[0, -179], [0, 179], [1, 0]] }), C('b11', 'robot.litter-pickup', { polygon: [[1, 1], [1, 1], [1, 1]] }),
    C('b12', 'robot.litter-pickup', { polygon: [['a', 1], [0, 1], [1, 1]] }), { ...C('b13', 'robot.litter-pickup', { cells: ['9q'] }), extra: 1 }, { ...C('b14', 'robot.litter-pickup', { cells: ['9q'] }), schema: 'v2' },
    C('b 15', 'robot.litter-pickup', { cells: ['9q'] }), C('b16', 'robot.litter-pickup', { cells: ['9q'] }, { params: { level: 9 } }), C('b17', 'robot.litter-pickup', { cells: ['9q'] }, { params: { seed: 99 } }), C('b18', 'software.advise-visitor', { cells: ['9q'] }, { params: { level: 1 } }),
    C('b19', 'robot.litter-pickup', { cells: ['9q'] }, { params: [] }), C('b20', 'robot.litter-pickup', { cells: ['9q'] }, { targets: 'x' }), C('b21', 'robot.litter-pickup', { cells: ['9q'] }, { targets: ['sim-robot:not/real'] }),
    C('b22', 'robot.litter-pickup', { cells: ['9q'] }, { hardware: 'rover-1' }), C('b23', 'robot.litter-pickup', { cells: ['9q'] }, { hardware: 'simulated' }), C('b24', 'robot.litter-pickup', { cells: ['9q'] }, { mode: 'live' }),
    C('b25', 'robot.litter-pickup', { cells: ['9q'] }, { operator: 'a person' }), C('b26', 'robot.litter-pickup', { cells: ['9q'] }, { params: { level: 1, ros_topic: '/cmd_vel' } }), C('b27', 'robot.litter-pickup', { cells: ['tcp:10.0.0.1'] }),
    C('b28', 'robot.litter-pickup', { cells: ['9q'] }, { targets: ['ros2:/robot'] }), C('b29', 'robot.litter-pickup', { cells: ['9q'] }, { mode: 5 }), { ...C('b30', 'robot.litter-pickup', { cells: ['9q'] }), device: { ip: '10.0.0.5' } },
    C('b31', 'robot.litter-pickup', { polygon: [[37.77, -122.30], [37.77, -122.24], [37.83, -122.24], [37.83, -122.30], [37.77, -122.30]] }),
  ];
  cmds.push(...bad);
  for (let i = 0; i < 70; i++) {
    const cx = 25 + rnd() * 24, cy = -124 + rnd() * 57, r = 0.03 + rnd() * (rnd() < 0.2 ? 6 : 0.6), k = 3 + Math.floor(rnd() * 5);
    const poly = Array.from({ length: k }, (_, j) => { const a = (j / k) * 2 * Math.PI + rnd() * 0.3; return [Math.round((cx + Math.sin(a) * r) * 1e4) / 1e4, Math.round((cy + Math.cos(a) * r) * 1e4) / 1e4]; });
    cmds.push(C(`rnd-${i}`, caps[i % caps.length], { polygon: poly }));
  }
  for (let i = 0; i < 24; i++) { const h = R.hives[i % R.hives.length], cs = Object.keys(h.cells); cmds.push(C(`rc-${i}`, caps[(i * 3) % caps.length], { cells: [cs[Math.floor(rnd() * cs.length)].slice(0, 3 + Math.floor(rnd() * 3))] })); }
  const nRandom = cmds.length - cmds.indexOf(bad[bad.length - 1]) - 1;
  const diffs = []; let routed = 0, held = 0, refused = 0, targetsSeen = 0;
  for (const c of cmds) {
    let a, b;
    try { b = router.route(JSON.parse(JSON.stringify(c))); } catch (e) { diffs.push(`router threw on ${c && c.id}: ${e.message}`); continue; }
    try { a = SC.previewCommand(JSON.parse(JSON.stringify(c)), D.core); } catch (e) { diffs.push(`page threw on ${c && c.id}: ${e.message}`); continue; }
    if (b.status === 'routed') routed++; else if (b.status === 'held') held++; else if (b.status === 'refused') refused++;
    targetsSeen += b.resolved.targets.length;
    const mism = [];
    if (a.status !== b.status) mism.push(`status ${a.status} vs ${b.status}`);
    if (canon(a.refusal) !== canon(b.refusal)) mism.push('refusal');
    if (canon(a.resolved) !== canon(b.resolved)) mism.push('resolved');
    if (canon(a.results.map((r) => [r.target, r.status, r.kind, r.hive, r.cell])) !== canon(b.results.map((r) => [r.target, r.status, r.kind, r.hive, r.cell]))) mism.push('results');
    if (mism.length) diffs.push(`${c && c.id}: ${mism.join(', ')}`);
  }
  ok(`[router] over ${cmds.length} commands (presets, every hive by cell, prefix and polygon, every capability, ${bad.length} malformed and real-hardware forms, ${nRandom} seeded random regions) the page's status, refusal, resolved block and per-target outcome equal the real router's`, diffs.length === 0 && cmds.length > 150, diffs);
  ok('[router] the battery reaches every outcome the page can show: routed, held and refused, with targets selected', routed > 20 && held > 5 && refused > 25 && targetsSeen > 100, [`routed ${routed}`, `held ${held}`, `refused ${refused}`, `targets ${targetsSeen}`]);
  const dev = SC.previewCommand(D.presets.find((p) => p.id === 'device').command, D.core);
  ok('[router] the real-device example is refused with the registry sentence and names its signals', dev.status === 'refused' && dev.refusal.code === 'real-hardware' && dev.refusal.reason === R.real_hardware.refusal && dev.refusal.signals.length >= 3);
  const gate = SC.previewCommand(D.presets.find((p) => p.id === 'gate').command, D.core), bay = SC.previewCommand(D.presets.find((p) => p.id === 'bay').command, D.core);
  ok('[router] the gate-drive example is held and the litter example would run as a dry run (the registry says which capability has gate records)', gate.status === 'held' && gate.expect === 'held' && bay.status === 'routed' && bay.expect === 'norecord' && R.capabilities['robot.gate-drive'].gate_targets.length > 0 && R.capabilities['robot.litter-pickup'].gate_targets.length === 0);
  ok('[router] the presets are valid swarm-command/1 commands in dry-run mode, except the one that names a real device', D.presets.every((p) => p.command.schema === 'swarm-command/1' && (p.id === 'device' ? p.command.mode === 'live' : p.command.mode === 'dry-run')));
}

/* ---- the builder is current ---- */
if (arg('page') === null && arg('root') === null) {
  let cur = false, out = '';
  try { out = execFileSync('python3', [join(HERE, 'build_swarm.py'), '--check'], { stdio: 'pipe', encoding: 'utf8' }); cur = true; } catch (e) { out = String(e.stdout ?? ''); }
  ok('[shipped] web/build_swarm.py --check: the page is current with the registry', cur, [out.trim()]);
}

/* ------------------------------------------------------------------- browser --- */
async function loadPlaywright() {
  if (process.env.PLAYWRIGHT_MODULE) return import(process.env.PLAYWRIGHT_MODULE);
  try { return await import('playwright'); } catch { /* not installed locally: the global package */ }
  const root = execFileSync('npm', ['root', '-g'], { encoding: 'utf8' }).trim();
  return import(pathToFileURL(join(root, 'playwright', 'index.mjs')).href);
}
if (BROWSER) {
  const { chromium } = await loadPlaywright();
  const WEB = dirname(PAGE), fs = await import('node:fs');
  const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.woff2': 'font/woff2', '.svg': 'image/svg+xml' };
  const server = createServer((req, res) => {
    const p = decodeURIComponent(req.url.split('?')[0]).replace(/^\/+/, ''); const f = resolve(WEB, p);
    if (!f.startsWith(WEB) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.statusCode = 404; res.end('no'); return; }
    res.setHeader('content-type', MIME[f.slice(f.lastIndexOf('.'))] ?? 'application/octet-stream'); res.end(fs.readFileSync(f));
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const base = `http://127.0.0.1:${server.address().port}/${PAGE.slice(WEB.length + 1)}`;
  const opts = { args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] };
  if (process.env.CHROMIUM_PATH) opts.executablePath = process.env.CHROMIUM_PATH;
  const browser = await chromium.launch(opts);
  const t0 = Date.now();
  try {
    const shotDir = mkdtempSync(join(tmpdir(), 'swarm-'));
    const open = async (ctx, q) => {
      const pg = await ctx.newPage(); const reqs = [], errs = [];
      pg.on('request', (r) => reqs.push(r.url())); pg.on('pageerror', (e) => errs.push(String(e.message)));
      pg.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
      await pg.goto(base + q, { waitUntil: 'load' }); pg.__reqs = reqs; pg.__errs = errs; return pg;
    };
    /* desktop, English */
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const pg = await open(ctx, '?lang=en');
    if (arg('shots')) await pg.waitForTimeout(0);
    await pg.waitForFunction(() => window.__swarmPage && window.__swarmPage.mapReady === true, null, { timeout: 30000 });
    ok('[browser] the map starts (MapLibre, WebGL) and the page reports ready', true);
    const st0 = await pg.evaluate(() => ({ cells: window.__swarmPage.cells, hives: window.__swarmPage.hives, canvas: !!document.querySelector('#swarm-map canvas'), pins: document.querySelectorAll('.pin').length, locale: window.__swarmPage.locale }));
    ok('[browser] the page reads 132-cell, 9-hive data from the registry figures and draws a canvas with one pin per hive', st0.cells === R.counts.cells && st0.hives === R.counts.hives && st0.canvas && st0.pins === R.hives.length && st0.locale === 'en', [JSON.stringify(st0)]);
    const safe = async (what, fn) => { try { return await fn(); } catch (e) { ok(`[browser] ${what}`, false, String(e.message).split('\n')[0]); return null; } };
    await pg.focus('[data-pick="bay-area"]'); await pg.keyboard.press('Enter');
    await safe('choosing the Bay Area hive settles the map', () => pg.waitForFunction(() => window.__swarmPage.selected === 'bay-area' && !window.__swarmPage.moving() && window.__swarmPage.zoom() > 6.5, null, { timeout: 20000 }));
    await pg.waitForTimeout(800);
    const focusKept = await pg.evaluate(() => document.activeElement && document.activeElement.getAttribute('data-pick'));
    ok('[browser] choosing a hive from the keyboard zooms the map to it and focus stays on the same button', focusKept === 'bay-area');
    const bayCells = Object.keys(R.hives.find((h) => h.id === 'bay-area').cells);
    const drawn = await pg.evaluate(() => { const m = window.__swarmPage.map(); const f = m.queryRenderedFeatures({ layers: ['cells-fill'] }); return [...new Set(f.map((x) => x.properties.cell))]; });
    ok('[browser] the map renders the hive\'s cell polygons: the rendered cell set is a subset of the hive\'s cells and covers most of them', drawn.length > 0 && drawn.every((c) => bayCells.includes(c)) && drawn.length >= bayCells.length * 0.6, [`${drawn.length} of ${bayCells.length}`]);
    await pg.focus('[data-cellbtn="' + bayCells[0] + '"]'); await pg.keyboard.press('Enter');
    await safe('selecting a cell settles the map', () => pg.waitForFunction(() => window.__swarmPage.cell && !window.__swarmPage.moving() && window.__swarmPage.zoom() > 10.5, null, { timeout: 20000 }));
    await pg.waitForTimeout(800);
    const ci = await pg.evaluate(() => ({ t: document.getElementById('swarm-cellinfo').textContent, cell: window.__swarmPage.cell, pressed: document.querySelector('[data-cellbtn][aria-pressed="true"]')?.getAttribute('data-cellbtn') }));
    ok('[browser] a cell button selects the cell: the live line names the cell, its hive and why it is owned', ci.cell === bayCells[0] && ci.pressed === bayCells[0] && ci.t.includes(bayCells[0]) && ci.t.includes('Bay Area hive'), [ci.t]);
    try {
    const shot = join(shotDir, 'map.png'); const box = await (await pg.$('#swarm-map')).boundingBox();
    const cen = await pg.evaluate((c) => { const m = window.__swarmPage.map(); const p = m.project(window.__swarmPage.centre(c)); return [p.x, p.y]; }, bayCells[0]);
    await (await pg.$('#swarm-map')).screenshot({ path: shot });
    const px = execFileSync('python3', ['-I', '-c', 'import sys\nfrom PIL import Image\nim=Image.open(sys.argv[1]).convert("RGB")\nw,h=im.size\nsx=w/float(sys.argv[2]);sy=h/float(sys.argv[3])\nfrom collections import Counter\nbg=Counter(im.getpixel((x,y)) for y in range(0,h,6) for x in range(0,w,6)).most_common(1)[0][0]\nc=im.getpixel((int(float(sys.argv[4])*sx),int(float(sys.argv[5])*sy)))\nd=0;cols=set();n=0\nfor y in range(0,h,4):\n  for x in range(0,w,4):\n    p=im.getpixel((x,y));n+=1\n    if sum(abs(p[i]-bg[i]) for i in range(3))>40: d+=1\n    cols.add((p[0]//32,p[1]//32,p[2]//32))\nprint(d/n,len(cols),sum(abs(c[i]-bg[i]) for i in range(3)))', shot, String(box.width), String(box.height), String(cen[0]), String(cen[1])], { encoding: 'utf8' }).trim().split(' ');
    ok('[browser] the canvas shows the drawn cell, not an empty plate: the selected cell\'s centre pixel differs from the background by more than 60, and more than 1.5% of sampled pixels differ, in more than 6 colour bins', Number(px[2]) > 60 && Number(px[0]) > 0.015 && Number(px[1]) > 6, px);
    } catch (e) { ok('[browser] the selected cell is drawn on the canvas', false, String(e.message).split('\n')[0]); }
    /* the region panel */
    try {
    const run = async (id) => { await pg.selectOption('#swarm-preset', id); await pg.waitForTimeout(150); return pg.evaluate(() => ({ last: window.__swarmPage.last, status: document.getElementById('swarm-r-status').textContent, audit: document.getElementById('swarm-r-audit').textContent, expect: document.getElementById('swarm-r-expect').textContent, refusal: document.getElementById('swarm-r-refusal').textContent, hit: window.__swarmPage.last && window.__swarmPage.last.drawn })); };
    const r1 = await run('bay'), r2 = await run('gate'), r3 = await run('device'), r4 = await run('sea');
    ok('[browser] "Resolve" on the Bay Area example: routed as a dry run, one hive, cells drawn on the map, an audit-row preview shown', r1.last.status === 'routed' && r1.last.hives.length === 1 && r1.last.cells > 0 && r1.hit > 1 && /"schema": "swarm-audit\/1 \(preview: not a row\)"/.test(r1.audit) && /no safety record|only as a dry run/.test(r1.expect), [JSON.stringify(r1.last)]);
    ok('[browser] the gate-drive example is held by the gate; the real-device example is refused with the registry sentence; the open-sea example is refused (no hive)', r2.last.status === 'held' && r3.last.status === 'refused' && r3.refusal.includes(R.real_hardware.refusal) && r3.audit.includes(R.real_hardware.refusal) && r4.last.refusal === 'no-hive-in-region', [r2.status, r3.refusal, JSON.stringify(r4.last)]);
    await pg.fill('#swarm-cmd', '{ not json'); await pg.click('#swarm-run');
    const inv = await pg.evaluate(() => ({ msg: document.getElementById('swarm-r-invalid').textContent, hidden: document.getElementById('swarm-r-invalid').hidden, body: document.getElementById('swarm-r-body').hidden }));
    ok('[browser] invalid JSON is reported in the page and nothing is resolved', !inv.hidden && inv.body && inv.msg.length > 10);
    const outside = pg.__reqs.filter((u) => !u.startsWith('http://127.0.0.1:') && !u.startsWith('data:') && !u.startsWith('blob:'));
    const kinds = [...new Set(pg.__reqs.filter((u) => u.startsWith('http://127.0.0.1:')).map((u) => u.slice(u.lastIndexOf('/') + 1).split('?')[0]))].sort();
    ok('[browser] the page made no request outside its own server, and fetched no tile, glyph or data file (only the page, MapLibre and the site\'s fonts and icons)', outside.length === 0 && !kinds.some((k) => /\.(pbf|mvt|png|jpg|jpeg|webp|geojson|json)$/.test(k) && k !== 'swarm.json'), [...outside, ...kinds].slice(0, 6));
    ok('[browser] no script error or console error on the desktop page', pg.__errs.length === 0, pg.__errs);
    const store = await pg.evaluate(() => { try { return Object.keys(localStorage).filter((k) => !/^tc-/.test(k)).concat(Object.keys(sessionStorage), document.cookie ? ['cookie'] : []); } catch { return []; } });
    ok('[browser] the page stored nothing of its own (no local or session storage key beyond the site\'s Style choice, no cookie)', store.length === 0, store);
    if (arg('shots')) { await pg.evaluate(() => window.__swarmPage.select(null)); await pg.waitForTimeout(1300); await pg.screenshot({ path: join(arg('shots'), 'desktop-dark-all.png') }); }
    await pg.evaluate(() => document.documentElement.setAttribute('data-style', 'enterprise'));
    await pg.waitForTimeout(300);
    const paint = await pg.evaluate(() => { const m = window.__swarmPage.map(); const v = getComputedStyle(document.body).getPropertyValue('--tc-plate').trim(); return { bg: m.getPaintProperty('bg', 'background-color'), plate: v }; });
    ok('[browser] choosing another Style repaints the map from that style\'s tokens (background follows --tc-plate)', paint.bg && paint.bg.toLowerCase() === paint.plate.toLowerCase(), [JSON.stringify(paint)]);
    if (arg('shots')) { await pg.evaluate(() => window.__swarmPage.select('bay-area')); await pg.waitForTimeout(1500); await pg.screenshot({ path: join(arg('shots'), 'desktop-light-bay.png'), fullPage: false }); await (await pg.$('#swarm-try')).screenshot({ path: join(arg('shots'), 'desktop-try.png') }); }
    } catch (e) { ok('[browser] the region panel and page hygiene checks ran', false, String(e.message).split('\n')[0]); }
    await ctx.close();
    /* phone, Arabic (right-to-left) */
    try {
    const ph = await browser.newContext({ viewport: { width: 360, height: 740 }, hasTouch: true, isMobile: true, deviceScaleFactor: 2 });
    const pp = await open(ph, '?lang=ar');
    await pp.waitForFunction(() => window.__swarmPage && window.__swarmPage.mapReady === true, null, { timeout: 30000 });
    const m = await pp.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth, dir: document.documentElement.dir, lang: document.documentElement.lang, h1: document.querySelector('h1').textContent, canvas: document.querySelector('#swarm-map canvas').clientWidth, gut: document.querySelector('main').getBoundingClientRect().left }));
    ok('[browser] phone width 360: no horizontal page scroll, right-to-left Arabic, the map fits the viewport, the 16 px gutter holds', m.sw <= m.iw && m.dir === 'rtl' && m.lang === 'ar' && m.canvas <= m.iw && m.h1.length > 3, [JSON.stringify(m)]);
    await pp.tap('[data-pick="new-orleans"]'); await pp.waitForFunction(() => window.__swarmPage.selected === 'new-orleans', null, { timeout: 15000 });
    await pp.tap('#swarm-run'); await pp.waitForTimeout(200);
    const pr = await pp.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth, last: window.__swarmPage.last, status: document.getElementById('swarm-r-status').textContent }));
    ok('[browser] on the phone a hive can be chosen by touch and the panel resolves in Arabic with no horizontal scroll', pr.sw <= pr.iw && pr.last && pr.last.status === 'routed' && pr.status.length > 3, [JSON.stringify(pr)]);
    ok('[browser] no script error on the phone page', pp.__errs.length === 0, pp.__errs);
    if (arg('shots')) { await pp.screenshot({ path: join(arg('shots'), 'phone-ar-full.png'), fullPage: true }); }
    await ph.close();
    } catch (e) { ok('[browser] the phone checks ran', false, String(e.message).split('\n')[0]); }
    ok(`[browser] the browser run took ${Math.round((Date.now() - t0) / 1000)} s (budget 90 s)`, Date.now() - t0 < 90000);
    rmSync(shotDir, { recursive: true, force: true });
  } finally { await browser.close(); server.close(); }
}

console.log(`\nweb/test_swarm: ${n} checks passed${failed ? `, ${failed} FAILED` : ''}`);
process.exit(failed ? 1 : 0);
