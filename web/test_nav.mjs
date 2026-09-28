/**
 * The site navigation, held to its one declaration (web/sitenav.py).
 *
 * The pages used to link to two or four of their siblings, several to
 * none; only the front door linked them all, so a learner who landed
 * anywhere else could not walk the training loop. web/sitenav.py now
 * declares every page (PAGES, by group) and the loop (LOOP) once, and
 * every page builder puts its nav_html() right after <body>. This file
 * reads the BUILT pages and the generator sources - no browser, no network:
 *
 *   - every page file is declared, and every declared page exists;
 *   - every page a builder here owns carries exactly one site nav, at the
 *     top of the body, from nav_html() and nowhere else;
 *   - every nav href resolves to a file relative to the page carrying it;
 *   - the current page is marked once, and the mark is the page itself;
 *   - every word the nav shows is the en catalog's value for its key, and
 *     web/sitenav.py types none of them (no English literal to drift);
 *   - the loop strip appears on exactly the loop pages, current step marked;
 *   - the nav is the same nav on every page, apart from the current marker
 *     and the relative prefix.
 *
 * Every declared page's builder is wired here, web/trade_craft_3d.html
 * (web/build_3d.py) included; NOT_WIRED stays as the named place for a page
 * whose builder is not, held to existence only.
 *
 *   node web/test_nav.mjs
 */
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { join, dirname, posix } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');

let n = 0;
let bad = 0;
const ok = (text, cond, detail) => {
  if (cond) { n++; console.log(`  ok  ${text}`); return; }
  bad++;
  console.error(`FAIL ${text}`);
  if (detail !== undefined) {
    const d = Array.isArray(detail) ? detail : [detail];
    for (const x of d.slice(0, 8)) console.error(`     ${typeof x === 'string' ? x : JSON.stringify(x)}`);
  }
};

/* ------------------------------------------------------ the declaration -- */
const decl = JSON.parse(execFileSync('python3', ['-c', [
  'import json, sys',
  `sys.path.insert(0, ${JSON.stringify(HERE)})`,
  'import sitenav as s',
  'print(json.dumps({"pages": s.PAGES, "groups": s.GROUPS, "loop": s.LOOP, "keys": s.KEYS, "front": s.FRONT_DOOR}))',
].join('\n')], { encoding: 'utf8' }));
const PAGES = decl.pages; // path -> [group key, label key]
const LOOP = decl.loop.map(([p, k]) => ({ path: p, key: k }));
const LOOP_PATHS = LOOP.map((s) => s.path);

// Pages the nav links to whose builders are not wired to sitenav here.
const NOT_WIRED = new Set([]);
const OWNED = Object.keys(PAGES).filter((p) => !NOT_WIRED.has(p));

// Which builder writes which page (path from the bundle root).
const BUILDERS = {
  'index.html': 'build_home.py',
  'web/trade_craft_signin.html': 'build_auth.py',
  'web/trade_craft_3d.html': 'build_3d.py',
  'web/trade_craft_contribute.html': 'build_contribute.py',
  'web/trade_craft_verify.html': 'build_verify.py',
  'web/trade_craft_dashboard.html': 'build_dashboard.py',
  'web/trade_craft_fabric.html': 'build_fabric.py',
  'web/trade_craft_geomap.html': 'build_geomap.py',
  'web/trade_craft_interactive.html': 'build_interactive_map.py',
  'web/trade_craft_ladder.html': 'build_ladder.py',
  'web/trade_craft_landing.html': 'build_landing.py',
  'web/trade_craft_languages.html': 'build_languages.py',
  'web/trade_craft_lessons.html': 'build_lessons.py',
  'web/trade_craft_map.html': 'build_map.py',
  'web/smartcitix_trade_craft_academy.html': 'build_page.py',
  'web/trade_craft_progress.html': 'build_progress.py',
  'web/trade_craft_spaces.html': 'build_spaces.py',
  'web/trade_craft_worksites.html': 'build_worksites.py',
  'web/trade_craft_quests.html': 'build_quests.py',
  'web/trade_craft_schools.html': 'build_schools.py',
  'web/trade_craft_design.html': 'build_design.py',
  'web/trade_craft_wilds.html': 'build_wilds.py',
};

const en = JSON.parse(readFileSync(join(ROOT, 'i18n/locales/en.json'), 'utf8')).strings;
const LOCALES = readdirSync(join(ROOT, 'i18n/locales')).filter((f) => f.endsWith('.json')).sort();

/* ---------------------------------------------------------- page files -- */
const onDisk = ['index.html', ...readdirSync(HERE).filter((f) => f.endsWith('.html')).map((f) => `web/${f}`)].sort();
const undeclared = onDisk.filter((p) => !(p in PAGES));
ok(`every page file (index.html and web/*.html, ${onDisk.length} found) is declared in sitenav.PAGES`,
  undeclared.length === 0, undeclared.map((p) => `not in PAGES: ${p}`));
// A page in NOT_WIRED may be absent only while its owner is still building
// it, and only the pages the quest contract names as pending may be there.
const PENDING_OK = new Set(['web/trade_craft_wilds.html', 'web/trade_craft_schools.html']);
ok(`NOT_WIRED names only pages the quest contract lists as pending (${NOT_WIRED.size})`,
  [...NOT_WIRED].every((p) => PENDING_OK.has(p)), [...NOT_WIRED].filter((p) => !PENDING_OK.has(p)));
const absent = Object.keys(PAGES).filter((p) => !NOT_WIRED.has(p) && !existsSync(join(ROOT, p)));
ok(`every sitenav.PAGES entry (${Object.keys(PAGES).length}) exists on disk`,
  absent.length === 0, absent.map((p) => `declared but missing: ${p}`));
ok('every page the nav declares has a builder here, or is named as one whose builder is not wired',
  OWNED.every((p) => p in BUILDERS) && Object.keys(BUILDERS).every((p) => p in PAGES),
  OWNED.filter((p) => !(p in BUILDERS)));
ok('every loop step is a declared page, and the loop runs sign in, lesson, walk, export, verify, share',
  LOOP.every((s) => s.path in PAGES) && LOOP.map((s) => s.key.split('.').pop()).join()
    === 'signin,lesson,walk,export,verify,share');

/* ------------------------------------------------------------- catalogs -- */
const missingKeys = [];
for (const f of LOCALES) {
  const s = JSON.parse(readFileSync(join(ROOT, 'i18n/locales', f), 'utf8')).strings;
  for (const k of decl.keys) if (typeof s[k] !== 'string' || !s[k].trim()) missingKeys.push(`${f}: ${k}`);
}
ok(`every nav key sitenav reads (${decl.keys.length}) is in all ${LOCALES.length} locale catalogs`,
  missingKeys.length === 0, missingKeys);
ok('no nav label in any catalog carries a digit (page suites scan for typed counts)',
  LOCALES.every((f) => {
    const s = JSON.parse(readFileSync(join(ROOT, 'i18n/locales', f), 'utf8')).strings;
    return decl.keys.every((k) => !/\d/.test(s[k] ?? ''));
  }));

/* ------------------------------------------------------------ generator -- */
const navSrc = readFileSync(join(HERE, 'sitenav.py'), 'utf8');
const navCode = navSrc.replace(/"""[\s\S]*?"""/g, '').replace(/#.*$/gm, '');
const typed = decl.keys.filter((k) => [`'${en[k]}'`, `"${en[k]}"`, `>${en[k]}<`].some((q) => navCode.includes(q)));
ok('web/sitenav.py types no nav label: every word comes from the catalog by key',
  typed.length === 0, typed.map((k) => `English literal for ${k}: "${en[k]}"`));
ok('web/sitenav.py\'s CSS uses logical properties only, so the nav mirrors under dir="rtl"',
  !/\b(?:margin|padding|border)-(?:left|right)\s*:|text-align\s*:\s*(?:left|right)|float\s*:|[;{](?:left|right)\s*:/.test(navCode));
const wiring = [];
for (const [page, b] of Object.entries(BUILDERS)) {
  const src = readFileSync(join(HERE, b), 'utf8');
  // the page is either a literal or a module-level constant assigned one literal in the same file
  const constOf = (name) => { const m = [...src.matchAll(new RegExp('^' + name + " = '([^']+)'$", 'gm'))]; return m.length === 1 ? m[0][1] : `<${name} is not one literal>`; };
  const calls = [...src.matchAll(/nav_html\((?:'([^']+)'|([A-Z][A-Z_]*)), nav_labels\('en'\)\)/g)].map((m) => (m[1] !== undefined ? m[1] : constOf(m[2])));
  if (calls.length !== 1 || calls[0] !== page) wiring.push(`${b}: nav_html calls ${JSON.stringify(calls)}, want ['${page}']`);
  if (!/NAV_CSS/.test(src)) wiring.push(`${b}: does not carry NAV_CSS`);
  if (/data-sitenav|class="sitenav/.test(src)) wiring.push(`${b}: types site-nav markup of its own`);
}
ok(`each of the ${Object.keys(BUILDERS).length} builders calls nav_html() once, for its own page, with the en catalog, and types no nav markup`,
  wiring.length === 0, wiring);

/* ---------------------------------------------------------- built pages -- */
const NAV_RE = /<nav\b[^>]*\bdata-sitenav\b[^>]*>[\s\S]*?<\/nav>/g;
const LOOP_RE = /<ol\b[^>]*\bdata-sitenav-loop\b[^>]*>[\s\S]*?<\/ol>/;
const navs = {};
const perPage = { count: [], place: [], href: [], current: [], text: [], loop: [], digits: [], skip: [], search: [], target: [] };
const SKIP_RE = /^<nav\b[^>]*>\s*<a class="skip" href="#tc-main">([^<]*)<\/a>/;
const textOf = (h) => h.replace(/<[^>]*>/g, '').replace(/&amp;/g, '&').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').trim();
const expectedOrder = [decl.front, ...decl.groups.flatMap(([, items]) => items.map(([p]) => p))];

for (const page of OWNED) {
  const html = readFileSync(join(ROOT, page), 'utf8');
  const found = html.match(NAV_RE) ?? [];
  if (found.length !== 1) { perPage.count.push(`${page}: ${found.length} site navs`); continue; }
  const nav = found[0];
  navs[page] = nav;
  const at = html.indexOf(nav);
  const before = html.slice(0, at);
  if (!/(?:<body\b[^>]*>|<\/style>)\s*$/.test(before) || (/<body\b/.test(html) && !/<body\b[^>]*>\s*$/.test(before))) {
    perPage.place.push(`${page}: the nav is not the first thing in the body`);
  }
  const base = posix.dirname(page);
  // the skip link: the nav's FIRST child, to #tc-main, labelled by the catalog
  const skip = nav.match(SKIP_RE);
  // ...and it lands: the one id="tc-main" on the page is the element right after </nav>
  const after = html.slice(at + nav.length);
  if (!/^\s*<span id="tc-main" class="sitenav-skip-target" tabindex="-1"><\/span>/.test(after)
      || (html.match(/id="tc-main"/g) || []).length !== 1) {
    perPage.target.push(`${page}: the skip link's target is not the one id="tc-main" right after the nav`);
  }
  if (!skip || textOf(skip[1]) !== en['nav.skip'] || (nav.match(/class="skip"/g) ?? []).length !== 1) {
    perPage.skip.push(`${page}: the nav's first child is not the one skip link to #tc-main with the catalog label`);
  }
  // the search link: the header bar's last child, to the front door's #search palette, labelled nav.search
  const searchLinks = [...nav.matchAll(/<a class="ss-go" href="([^"]*)" data-search-go\b[^>]*>([\s\S]*?)<\/a>\s*<\/div>/g)];
  const wantSearch = page === decl.front ? '#search' : posix.relative(posix.dirname(page) || '.', decl.front) + '#search';
  if (searchLinks.length !== 1 || (nav.match(/data-search-go/g) ?? []).length !== 1 || searchLinks[0][1] !== wantSearch
    || textOf(searchLinks[0][2]) !== en['nav.search']) {
    perPage.search.push(`${page}: ${searchLinks.length} search links closing the header bar (want one, href ${wantSearch}, label nav.search)`);
  }
  const links = [...nav.matchAll(/<a\b([^>]*)>([\s\S]*?)<\/a>/g)].filter((m) => !/class="skip"|data-search-go/.test(m[1])).map((m) => ({
    href: (m[1].match(/href="([^"]*)"/) ?? [])[1],
    cur: (m[1].match(/aria-current="([^"]*)"/) ?? [])[1],
    text: textOf(m[2]),
  }));
  for (const l of links) {
    const target = l.href === undefined ? null : posix.normalize(posix.join(base, l.href));
    l.target = target;
    // a link to a NOT_WIRED page (its owner is still building it) is held to naming a declared page
    if (!target || /^[a-z]+:/.test(l.href) || (!existsSync(join(ROOT, target)) && !(NOT_WIRED.has(target) && target in PAGES))) {
      perPage.href.push(`${page}: href "${l.href}" resolves to nothing`);
    }
  }
  const marked = links.filter((l) => l.cur === 'page');
  if (marked.length !== 1 || marked[0].target !== page) {
    perPage.current.push(`${page}: ${marked.length} aria-current="page" marks${marked.length ? ` -> ${marked.map((l) => l.target).join(', ')}` : ''}`);
  }
  const loopHtml = (nav.match(LOOP_RE) ?? [null])[0];
  const mainLinks = links.slice(0, links.length - (loopHtml ? LOOP.length : 0));
  const gotOrder = mainLinks.map((l) => l.target);
  const wantText = expectedOrder.map((p) => en[PAGES[p][1]]);
  if (JSON.stringify(gotOrder) !== JSON.stringify(expectedOrder)
    || JSON.stringify(mainLinks.map((l) => l.text)) !== JSON.stringify(wantText)) {
    perPage.text.push(`${page}: links/labels differ from PAGES with the en catalog`);
  }
  const groups = [...nav.matchAll(/<span class="sitenav-g">([^<]*)<\/span>/g)].map((m) => textOf(m[1]));
  if (JSON.stringify(groups) !== JSON.stringify(decl.groups.map(([g]) => en[g]))) {
    perPage.text.push(`${page}: group labels ${JSON.stringify(groups)} are not the catalog's`);
  }
  const aria = (nav.match(/^<nav\b[^>]*aria-label="([^"]*)"/) ?? [])[1];
  if (aria !== en['nav.site']) perPage.text.push(`${page}: nav aria-label "${aria}" is not the catalog's`);
  const isStep = LOOP_PATHS.includes(page);
  if (isStep !== Boolean(loopHtml)) {
    perPage.loop.push(`${page}: loop strip ${loopHtml ? 'present' : 'absent'}, but the page ${isStep ? 'is' : 'is not'} a loop step`);
  } else if (loopHtml) {
    const steps = links.slice(links.length - LOOP.length);
    const stepCur = steps.filter((l) => l.cur === 'step');
    const loopAria = (loopHtml.match(/aria-label="([^"]*)"/) ?? [])[1];
    if (stepCur.length !== 1 || stepCur[0].target !== page
      || JSON.stringify(steps.map((l) => l.target)) !== JSON.stringify(LOOP_PATHS)
      || JSON.stringify(steps.map((l) => l.text)) !== JSON.stringify(LOOP.map((s) => en[s.key]))
      || loopAria !== en['nav.loop']) {
      perPage.loop.push(`${page}: loop strip steps/labels/current step (${stepCur.length} marked) are wrong`);
    }
  }
  if (/\d/.test(textOf(nav))) perPage.digits.push(`${page}: the nav's text carries a digit`);
}

ok(`each of the ${OWNED.length} pages built here carries exactly one site nav`, perPage.count.length === 0, perPage.count);
ok('the nav is the first thing in each page\'s body (right after <body>)', perPage.place.length === 0, perPage.place);
ok('every nav href resolves to a file, relative to the page carrying it', perPage.href.length === 0, perPage.href);
ok('the current page is marked aria-current="page" exactly once, and the mark is the page itself',
  perPage.current.length === 0, perPage.current);
ok('every nav label, group name and the nav\'s aria-label is the en catalog value for its key, in PAGES order',
  perPage.text.length === 0, perPage.text);
ok(`the loop strip appears on exactly the loop pages built here, with that page's step current`,
  perPage.loop.length === 0, perPage.loop);
ok('no nav shows a digit', perPage.digits.length === 0, perPage.digits);
ok('every page\'s header bar ends with the one search link to the front door\'s #search palette, labelled nav.search',
  perPage.search.length === 0, perPage.search);
ok('every nav opens with a skip link to #tc-main, labelled nav.skip, and NAV_CSS hides it until it has focus',
  perPage.skip.length === 0 && /\.sitenav a\.skip\{[^}]*clip-path:inset\(50%\)/.test(navSrc.replace(/'\s*\n\s*'/g, ''))
  && /\.sitenav a\.skip:focus[^{]*\{[^}]*clip-path:none/.test(navSrc.replace(/'\s*\n\s*'/g, '')), perPage.skip);
ok('every skip link lands: each page carries exactly one id="tc-main", the element right after the nav',
  perPage.target.length === 0, perPage.target);

// Same nav everywhere: resolve every href to a bundle-root path, drop the
// current markers and the loop strip, and compare.
const canon = (page, nav) => nav
  .replace(new RegExp(`\\n?${LOOP_RE.source}`), '')
  .replace(/ aria-current="[^"]*"/g, '')
  .replace(/href="[^"]*" data-search-go/g, 'data-search-to="front-door" data-search-go')
  .replace(/href="([^"]*)"/g, (_, h) => (h.startsWith('#') ? `href="${h}"` : `href="${posix.normalize(posix.join(posix.dirname(page), h))}"`));
const canons = Object.entries(navs).map(([p, nav]) => [p, canon(p, nav)]);
const ref = canons.length ? canons[0][1] : '';
const differ = canons.filter(([, c]) => c !== ref).map(([p]) => `${p}: differs from ${canons[0][0]}`);
ok('the nav is identical on every page apart from the current marker and relative prefixes',
  canons.length === OWNED.length && differ.length === 0, differ);

if (bad) {
  console.error(`web/test_nav: ${bad} FAILED, ${n} passed`);
  process.exit(1);
}
console.log(`web/test_nav: ${n} checks passed`);
