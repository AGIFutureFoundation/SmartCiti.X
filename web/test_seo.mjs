/**
 * The site's search-engine and link-preview tags, held to web/seo.py's rules.
 *
 * Reads the BUILT pages, sitemap.xml and robots.txt (never a generator's
 * comments), and web/sitenav.py / web/seo.py only for the two facts they
 * declare: the page list and the published BASE.
 *
 *   node web/test_seo.mjs
 *   node web/test_seo.mjs --root=/tmp/broken-copy     (mutation runs)
 *
 * PENDING names the nav pages that have not adopted seo_head() yet (their
 * builders belong to other owners this wave). It is strict both ways, the
 * same rule as test_nav's NOT_WIRED: a pending page that adopts it must be
 * taken off the list, so the list can only shrink.
 */
import { readFileSync, existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const HERE = dirname(fileURLToPath(import.meta.url));
const argRoot = process.argv.slice(2).find((a) => a.startsWith('--root='));
const ROOT = resolve(argRoot ? argRoot.slice(7) : join(HERE, '..'));
const read = (p) => readFileSync(join(ROOT, p), 'utf8');

let failed = 0; let passed = 0;
function ok(name, cond, detail) {
  if (cond) { passed++; console.log(`  ok  ${name}`); return; }
  failed++; console.log(`FAIL ${name}`);
  for (const d of [].concat(detail ?? []).slice(0, 8)) console.log(`     ${typeof d === 'string' ? d : JSON.stringify(d)}`);
}

// A page whose own suite forbids every <link> (test_verify: "nothing it
// could send to"): no canonical link there; og:url carries the URL instead.
const NO_CANONICAL_LINK = { 'web/trade_craft_verify.html': 'test_verify forbids any <link> and any href to http(s)' };
// ...and whose suite forbids any script naming a remote origin, which
// JSON-LD's @context and @id do: it carries the head tags only.
const NO_JSONLD = { 'web/trade_craft_verify.html': 'test_verify: no script on the page names a remote origin' };
const PENDING = new Set([
  'web/trade_craft_3d.html', 'web/trade_craft_wilds.html', 'web/trade_craft_lessons.html',
  'web/trade_craft_progress.html', 'web/trade_craft_schools.html', 'web/trade_craft_quests.html',
  'web/trade_craft_design.html',   // MEDIA's design-kit page, new this wave
]);

// ---- the declared facts --------------------------------------------------
const nav = read('web/sitenav.py');
const FRONT = nav.match(/^FRONT_DOOR = '([^']+)'/m)[1];
const groupsSrc = nav.slice(nav.indexOf('GROUPS = ['), nav.indexOf('# Every page: path'));
const PAGES = [FRONT, ...[...groupsSrc.matchAll(/\('(web\/[^']+\.html)', 'nav\.page\.[a-z0-9_]+'\)/g)].map((m) => m[1])];
const seoSrc = read('web/seo.py');
const BASE = seoSrc.match(/^BASE = '([^']+)'/m)[1];
const DESC_MAX = Number(seoSrc.match(/^DESC_MAX = (\d+)/m)[1]);
const canon = (p) => (p === FRONT ? BASE : BASE + p);

ok(`[declared] web/sitenav.py lists pages (${PAGES.length}) and web/seo.py one https BASE ending in /`,
  PAGES.length > 10 && /^https:\/\/[^/]+\/.*\/$/.test(BASE), [BASE]);

// ---- sitemap + robots ----------------------------------------------------
const sitemap = read('sitemap.xml');
const locs = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1].replace(/&amp;/g, '&'));
ok('[shipped] sitemap.xml lists exactly the nav pages, in PAGES order, each at its canonical URL',
  JSON.stringify(locs) === JSON.stringify(PAGES.map(canon)),
  [`sitemap ${locs.length} urls, nav ${PAGES.length}`,
    ...locs.filter((l) => !PAGES.map(canon).includes(l)).map((l) => 'extra ' + l),
    ...PAGES.map(canon).filter((l) => !locs.includes(l)).map((l) => 'missing ' + l)]);
ok('[shipped] sitemap.xml is a sitemaps.org urlset and types no lastmod or priority it cannot know',
  /<urlset xmlns="http:\/\/www\.sitemaps\.org\/schemas\/sitemap\/0\.9">/.test(sitemap)
  && !/<lastmod>|<priority>|<changefreq>/.test(sitemap));
const robots = read('robots.txt');
ok('[shipped] robots.txt allows crawling and names the sitemap at BASE',
  /^User-agent: \*$/m.test(robots) && /^Allow: \/$/m.test(robots) && !/^Disallow: \/\s*$/m.test(robots)
  && robots.includes(`Sitemap: ${BASE}sitemap.xml`));

// ---- every page's head -----------------------------------------------------
const heads = {};
const titles = {};
for (const p of PAGES) {
  const page = read(p);
  const cut = ['</head>', '<body', '<nav'].map((m) => page.indexOf(m)).filter((i) => i >= 0);
  const head = page.slice(0, Math.min(...cut));
  heads[p] = head;
  titles[p] = (head.match(/<title>([^<]*)<\/title>/) || [])[1];
}
const dupT = Object.entries(titles).filter(([p, t]) => !t || Object.values(titles).filter((x) => x === t).length > 1);
ok(`[shipped] every nav page (${PAGES.length}) has a <title> and no two share one`, dupT.length === 0,
  dupT.map(([p, t]) => `${p}: ${t}`));

const adopted = PAGES.filter((p) => /data-seo-jsonld/.test(read(p)) || (NO_JSONLD[p] && /<meta property="og:url"/.test(heads[p])));
const lastScriptIsLd = adopted.filter((p) => { const all = [...read(p).matchAll(/<script\b[^>]*>/g)].map((m) => m[0]);
  return all.length > 1 && /data-seo-jsonld/.test(all[0]); });
const notAdopted = PAGES.filter((p) => !adopted.includes(p));
ok(`[shipped] every nav page carries seo_head() except the PENDING list (${adopted.length} adopted)`,
  notAdopted.every((p) => PENDING.has(p)), notAdopted.filter((p) => !PENDING.has(p)));
ok('[suite] and PENDING only shrinks: no page on it has adopted seo_head() already',
  [...PENDING].every((p) => !adopted.includes(p)), [...PENDING].filter((p) => adopted.includes(p)));

const attr = (head, sel) => {
  const m = head.match(new RegExp(`<meta (?:name|property)="${sel}" content="([^"]*)"`));
  return m ? m[1].replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#x27;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>') : null;
};
const bad = { desc: [], canon: [], og: [], img: [], ld: [], ldTypes: [], theme: [], lang: [] };
const FORBIDDEN = /"(aggregateRating|review|offers|price|priceCurrency|hasCourseInstance|educationalCredentialAwarded|accreditation|hasCredential|Course|EducationalOccupationalCredential)"/;
for (const p of adopted) {
  const h = heads[p];
  const d = attr(h, 'description');
  if (!d || !d.trim() || d.length > DESC_MAX) bad.desc.push(`${p}: ${d === null ? 'none' : d.length + ' chars'}`);
  const c = (h.match(/<link rel="canonical" href="([^"]+)"/) || [])[1];
  const nCanon = (h.match(/rel="canonical"/g) || []).length;
  if (NO_CANONICAL_LINK[p] ? nCanon !== 0
    : (nCanon !== 1 || !c || new URL(c, canon(p)).href !== canon(p))) bad.canon.push(`${p}: ${c}`);
  if (attr(h, 'og:url') !== canon(p) || attr(h, 'og:title') !== titles[p].replace(/&amp;/g, '&')
    || attr(h, 'og:description') !== d || attr(h, 'twitter:card') !== 'summary_large_image'
    || attr(h, 'twitter:description') !== d) bad.og.push(p);
  const img = attr(h, 'og:image');
  if (!img || !img.startsWith(BASE) || !existsSync(join(ROOT, img.slice(BASE.length)))
    || attr(h, 'twitter:image') !== img || !attr(h, 'og:image:alt')) bad.img.push(`${p}: ${img}`);
  const whole = read(p);
  const lds = [...whole.matchAll(/<script type="application\/ld\+json" data-seo-jsonld>([\s\S]*?)<\/script>/g)];
  let doc = null;
  try { doc = lds.length === 1 ? JSON.parse(lds[0][1]) : null; } catch (e) { doc = null; }
  if (NO_JSONLD[p]) { if (lds.length !== 0 || /data-seo-jsonld/.test(whole)) bad.ld.push(p + ' must carry none'); }
  else if (!doc || doc['@context'] !== 'https://schema.org' || !Array.isArray(doc['@graph'])) bad.ld.push(p);
  else {
    const types = doc['@graph'].map((g) => g['@type']);
    const want = p === FRONT ? ['Organization', 'WebSite'] : null;
    if ((want && JSON.stringify(types) !== JSON.stringify(want))
      || (!want && !['WebPage', 'CollectionPage'].includes(types[0]))
      || FORBIDDEN.test(lds[0][1])
      || (!want && doc['@graph'][0].url !== canon(p))) bad.ldTypes.push(`${p}: ${types.join(',')}`);
  }
  if ((h.match(/<meta name="theme-color" content="#[0-9A-Fa-f]{6}" media="\(prefers-color-scheme: (dark|light)\)">/g) || []).length !== 2) bad.theme.push(p);
  if (!/<html lang="en"/.test(read(p).slice(0, 200))) bad.lang.push(p);
}
ok(`[shipped] every adopted page's meta description is present and at most ${DESC_MAX} characters`, bad.desc.length === 0, bad.desc);
ok('[shipped] every adopted page has exactly one canonical link and it resolves to BASE + its own path '
  + `(the page${Object.keys(NO_CANONICAL_LINK).length === 1 ? '' : 's'} whose own contract forbids any <link> carry none and name it in og:url)`,
  bad.canon.length === 0, bad.canon);
ok('[shipped] the JSON-LD is never a page\'s FIRST <script> (page suites read that one as the page\'s own payload)',
  lastScriptIsLd.length === 0, lastScriptIsLd);
ok('[shipped] Open Graph and Twitter cards repeat the page\'s own title, description and canonical URL', bad.og.length === 0, bad.og);
ok('[shipped] the card image is an absolute URL under BASE naming a real screenshot in the bundle, with alt text', bad.img.length === 0, bad.img);
ok('[shipped] each adopted page carries exactly one JSON-LD block, and it parses as a schema.org @graph '
  + '(none on a page whose contract forbids a script naming a remote origin)', bad.ld.length === 0, bad.ld);
ok('[shipped] JSON-LD types are Organization+WebSite on the front door and WebPage/CollectionPage elsewhere - no Course, rating, price, offer or accreditation',
  bad.ldTypes.length === 0, bad.ldTypes);
ok('[shipped] each adopted page names a theme-color for dark and for light, and declares lang', bad.theme.length === 0 && bad.lang.length === 0, [...bad.theme, ...bad.lang]);
const descs = adopted.map((p) => attr(heads[p], 'description'));
ok('[shipped] no two adopted pages share a description', new Set(descs).size === descs.length);

// ---- generated files are current ---------------------------------------------
if (!argRoot) {
  let current = true; let out = '';
  try { out = execFileSync('python3', [join(ROOT, 'web/build_seo.py'), '--check'], { encoding: 'utf8' }); } catch (e) { current = false; out = String(e.stdout); }
  ok('[generator] sitemap.xml and robots.txt are what web/build_seo.py writes now', current, out.trim().split('\n'));
}

console.log(`seo: ${passed + failed} checks, ${failed} failures`);
process.exit(failed ? 1 : 0);
