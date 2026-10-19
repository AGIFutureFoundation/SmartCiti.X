/**
 * Module links inside the worlds (wave 20): the Bay restoration site panel and scenario runner, the wilds site panel and
 * the robot yard label each link to their world training module on the Courses page.
 *
 * Re-read against modules/registry/modules.json and the built pages: every link target is a registry module and an
 * id on the Courses page; each world's links match the registry (8 restoration sites on the Bay page, 4 wilds worlds,
 * 1 robot yard); the Bay map pairs each site with its own module and that site is on the page; every locale carries
 * the link text; no team codename and no internal path in the pages. Usage: node web/test_modulelinks.mjs [root]
 * (root defaults to the repository; a sandbox copy with the same layout may be passed for mutation proofs).
 * Prints `  ok <name>` per check and `FAIL <name>` at column 0; exits non-zero on any failure.
 */
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = process.argv[2] ? path.resolve(process.argv[2]) : path.resolve(HERE, '..');
const rd = (rel) => readFileSync(path.join(ROOT, rel), 'utf8');
const LOCALES = ['ar', 'de', 'en', 'es', 'fr', 'hi', 'pt', 'zh'];
let fails = 0;
function check(name, ok, detail = '') {
  if (ok) console.log(`  ok ${name}`);
  else { fails += 1; console.log(`FAIL ${name}${detail ? ' - ' + detail : ''}`); }
}
function safe(fn, fallback) { try { return fn(); } catch (e) { check('input readable', false, e.message); return fallback; } }

const reg = safe(() => JSON.parse(rd('modules/registry/modules.json')), { modules: [] });
const mods = Array.isArray(reg.modules) ? reg.modules : [];
const byFam = (f) => mods.filter((m) => m.family === f);
const RESTO = byFam('restoration-site'), WILDS = byFam('wilds-world'), ROBOT = byFam('robot-yard');
const regIds = new Set(mods.map((m) => m.id));
const COURSES = safe(() => rd('web/trade_craft_courses.html'), '');
const BAY = safe(() => rd('web/trade_craft_bay.html'), '');
const WILDS_PAGE = safe(() => rd('web/trade_craft_wilds.html'), '');
const PARISH = safe(() => rd('web/trade_craft_parishes.html'), '');
const PAGES = { bay: BAY, wilds: WILDS_PAGE, parishes: PARISH };
const linkRe = /trade_craft_courses\.html#([A-Za-z0-9_-]+)/g;
const targets = (html) => [...html.matchAll(linkRe)].map((m) => m[1]);

// 1. the registry: the three link families, one module each per walkable place
check('registry holds 16 modules', mods.length === 16, `found ${mods.length}`);
check('registry: 8 restoration-site modules (walkable Bay sites)', RESTO.length === 8, `found ${RESTO.length}`);
check('registry: 4 wilds-world modules (one per world)', WILDS.length === 4, `found ${WILDS.length}`);
check('registry: exactly 1 robot-yard module', ROBOT.length === 1, `found ${ROBOT.length}`);
check('registry: module ids are unique and start with module-', regIds.size === mods.length && mods.every((m) => /^module-[a-z0-9-]+$/.test(m.id)));

// 2. the Courses page carries an anchor for every module it lists
check('courses page is present', COURSES.length > 0);
for (const m of mods) {
  check(`courses page has id="${m.id}"`, COURSES.includes(`id="${m.id}"`));
}

// 3. every link target on the three pages is a registry module and a Courses-page id
for (const [name, html] of Object.entries(PAGES)) {
  const t = targets(html);
  check(`${name} page: links to the Courses page exist`, t.length > 0, 'no module link');
  check(`${name} page: every link target is a registry module`, t.every((id) => regIds.has(id)),
    [...new Set(t.filter((id) => !regIds.has(id)))].join(', '));
  check(`${name} page: every link target has an anchor on the Courses page`, t.every((id) => COURSES.includes(`id="${id}"`)));
}

// 4. counts per world match the registry
const distinct = (html) => new Set(targets(html));
const restoIds = new Set(RESTO.map((m) => m.id));
const bayIds = distinct(BAY);
check('bay page: exactly the 8 restoration module links, no more', [...restoIds].every((id) => bayIds.has(id))
  && [...bayIds].filter((id) => id.startsWith('module-restoration-')).length === restoIds.size,
  `bay restoration links ${[...bayIds].filter((id) => id.startsWith('module-restoration-')).length}, registry ${restoIds.size}`);
const wildsIds = new Set(WILDS.map((m) => m.id));
check('wilds page: exactly the 4 wilds world links', distinct(WILDS_PAGE).size === wildsIds.size
  && [...wildsIds].every((id) => distinct(WILDS_PAGE).has(id)), `wilds links ${distinct(WILDS_PAGE).size}`);
const robotId = ROBOT.length === 1 ? ROBOT[0].id : null;
check('parishes page: the robot yard link is the registry robot module',
  robotId !== null && distinct(PARISH).has(robotId) && distinct(PARISH).size === 1, `targets ${[...distinct(PARISH)].join(', ')}`);

// 5. the Bay map pairs each site with its own module, and every mapped site is on the page
const bayMap = safe(() => JSON.parse(BAY.match(/const MOD = (\{.*?\});\n/)[1]), null);
check('bay page: the site-to-module map is present', bayMap !== null);
if (bayMap) {
  const want = Object.fromEntries(RESTO.map((m) => [m.site, `trade_craft_courses.html#${m.id}`]));
  check('bay page: each site maps to its own registry module', JSON.stringify(Object.keys(bayMap).sort()) === JSON.stringify(Object.keys(want).sort())
    && Object.keys(want).every((s) => bayMap[s] === want[s]));
  const rsd = safe(() => JSON.parse(BAY.match(/id="resto-site-data">(.*?)<\/script>/s)[1].replace(/<\\\//g, '</')), { sites: [] });
  const onPage = new Set((rsd.sites || []).map((s) => s.id));
  check('bay page: every mapped site is a walkable site on the page', Object.keys(bayMap).every((s) => onPage.has(s)),
    Object.keys(bayMap).filter((s) => !onPage.has(s)).join(', '));
}

// 6. the wilds map pairs each world with its own module
const wMap = safe(() => JSON.parse(WILDS_PAGE.match(/const MOD_WILDS = (\{.*?\});\n/)[1]), null);
check('wilds page: the world-to-module map is present', wMap !== null);
if (wMap) {
  const want = Object.fromEntries(WILDS.map((m) => [m.world.split(':')[1], `trade_craft_courses.html#${m.id}`]));
  check('wilds page: each world maps to its own registry module', JSON.stringify(Object.keys(wMap).sort()) === JSON.stringify(Object.keys(want).sort())
    && Object.keys(want).every((w) => wMap[w] === want[w]));
}
check('robot yard: the label link points at the registry robot module',
  robotId !== null && PARISH.includes(`ryMod.href = "trade_craft_courses.html#${robotId}"`));

// 7. link text: every locale carries it, and the pages embed it
for (const loc of LOCALES) {
  const s = safe(() => JSON.parse(rd(`i18n/locales/${loc}.json`)).strings, {});
  check(`${loc}: modlink.practice and wilds.practice_module are non-empty`, typeof s['modlink.practice'] === 'string' && s['modlink.practice'].trim() !== ''
    && typeof s['wilds.practice_module'] === 'string' && s['wilds.practice_module'].trim() !== '');
}
check('bay page: the link text is embedded for all 8 locales', bayMap !== null && /const LBL = \{/.test(BAY) && LOCALES.every((l) => BAY.includes(`"${l}":`)));
check('wilds page: the link text is in the runtime catalogue for all 8 locales',
  (WILDS_PAGE.match(/"wilds\.practice_module":/g) || []).length >= LOCALES.length);

// 8. neutral page markers and no codename or internal path in any page
// the wave-20 team names (LINKS, MODULES) must not appear on any page. Older JS comment markers (RESTORE hook,
// RESTORE-SITE, WORLD-PRACTICE) are pre-existing and are not touched by this wave; they are listed as open items.
const CODENAMES = ['LINKS', 'MODULES', 'MODULELINKS'];
for (const [name, html] of Object.entries({ ...PAGES, courses: COURSES })) {
  const bad = CODENAMES.filter((c) => new RegExp(`\\b${c}\\b`).test(html));
  check(`${name} page: no team codename in the built page`, bad.length === 0, bad.join(', '));
  check(`${name} page: no internal path or agent note`, !/\/tmp\/|scratchpad|memory\/|consoles\/|\$SP/.test(html));
}
check('bay page: link marker is present', BAY.includes('id="module-link-kit"'));
check('wilds page: link row marker is present', WILDS_PAGE.includes('dataset.moduleLink') && WILDS_PAGE.includes('function modLinkRow()'));
check('parishes page: robot yard link marker is present', PARISH.includes("ryMod.setAttribute('data-module-link'"));

console.log(fails ? `FAIL ${fails} check(s)` : `all module-link checks ok`);
process.exit(fails ? 1 : 0);
