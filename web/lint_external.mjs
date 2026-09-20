/**
 * Every external origin a built page reaches, pinned.
 *
 * THIRD_PARTY.md is scrupulous about material that is "not vendored" and
 * fetched in the learner's own browser: it names the USGS imagery service
 * and each parcel authority that way. It did not name the FONT CDN, and
 * four pages have been asking a third party for a stylesheet on every page
 * load the whole time - a request that carries the visitor's IP address and
 * user agent to that third party before a single word of the page renders.
 *
 * The omission was not a lie anybody told; it is what happens when a
 * disclosure is maintained by hand. So this replaces the hand: the set of
 * external origins the built pages may reach is written down ONCE, here,
 * every origin must be documented in THIRD_PARTY.md, and a page that
 * reaches a new one fails the build rather than quietly adding a party to
 * the deployment nobody wrote down.
 *
 * Runs in verify_all.sh. Reaches no network - it reads the built files.
 */
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

let n = 0, bad = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); bad++; } else { n++; } };

const ROOT = new URL('..', import.meta.url).pathname;

/* The origins a built page FETCHES from. `why` is what the origin is for and
   `documented` is the string THIRD_PARTY.md must contain for it, because an
   origin allowed here and undisclosed there is the exact failure this file
   exists to stop. */
/* Empty, and that is the point. Five pages used to link Google's font
   stylesheet, which made a Google request part of opening any of them and
   sent every learner's IP and user agent along with it. The faces are
   vendored under web/vendor/fonts/ now (web/fetch_fonts.py), so no built
   page fetches anything from anywhere at run time.

   The entry is kept as an empty object rather than deleted because the
   machinery below is what holds that to be true, and because the next
   origin somebody is tempted to add belongs here, beside a `why` and the
   string THIRD_PARTY.md has to carry for it. */
const FETCHED = {};

/* Origins the pages only CITE - a source link a reader can follow, which
   costs the reader nothing until they click it. These are not typed out:
   an origin counts as cited when some registry in this bundle carries it as
   a source, which is where the restoration pack's EPA, Navy, court and news
   citations already live. Deriving it means the list cannot go stale, and
   means a page cannot cite something no registry stands behind. */
function citedOrigins() {
  const out = new Set();
  const ORIGIN_ANY = /https?:\/\/([a-z0-9.-]+\.[a-z]{2,})/gi;
  const walk = (dir) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      const full = join(dir, e.name);
      if (e.isDirectory()) {
        if (['node_modules', '.git', 'web', 'console', 'archive', 'wiki'].includes(e.name)) continue;
        walk(full);
      } else if (e.name.endsWith('.json') && full.includes('registry')) {
        for (const m of readFileSync(full, 'utf8').matchAll(ORIGIN_ANY)) {
          out.add(m[1].toLowerCase());
        }
      }
    }
  };
  walk(ROOT);
  return out;
}

/* Origins that are this bundle's own, or a bare identifier rather than a
   host anyone contacts. `w3id.org` and `adlnet.gov` appear as xAPI/JSON-LD
   IRIs - names in a vocabulary, never fetched - and `smartciti.x` is the
   product's own string. */
const SELF = new Set([
  'smartciti.x',              // the product's own string
  'w3id.org', 'adlnet.gov',   // xAPI / JSON-LD IRIs: names in a vocabulary
  'metaverse-standards.org',  // the OMBI/MSF work this bundle cites by name
  // The SVG namespace, which every inline <svg> carries and no browser ever
  // requests. It arrived with the pages' data-URI favicon and this lint
  // failed on it immediately, which is the lint doing its job: a namespace
  // that looks like a URL still has to be classified once, on purpose.
  'www.w3.org',
]);

/* Origins a PAGE offers as an outbound link of its own, rather than quoting
   from a registry. The city-point panel builds an OpenStreetMap permalink
   from the coordinates it is already showing, so the reader can check the
   point against a map that is not ours. Nothing is fetched: the link is only
   followed if the reader clicks it, and the coordinates in it are the ones
   already on screen. */
const PAGE_LINKS = {
  'www.openstreetmap.org':
    'the city-point panel\'s "check this against a map that is not ours" permalink',
};

const PAGES = [
  'index.html',
  ...readdirSync(join(ROOT, 'web')).filter((f) => f.endsWith('.html')).map((f) => 'web/' + f),
  'console/trade_craft_console.html',
];

// every absolute http(s) origin that appears anywhere in a built page
const ORIGIN = /https?:\/\/([a-z0-9.-]+\.[a-z]{2,})/gi;
const found = new Map();      // origin -> Set(page)
for (const p of PAGES) {
  let txt;
  try { txt = readFileSync(join(ROOT, p), 'utf8'); } catch { continue; }
  for (const m of txt.matchAll(ORIGIN)) {
    const host = m[1].toLowerCase();
    if (!found.has(host)) found.set(host, new Set());
    found.get(host).add(p);
  }
}

const third = readFileSync(join(ROOT, 'THIRD_PARTY.md'), 'utf8');
const cited = citedOrigins();

/* Every origin in a built page is accounted for: fetched and disclosed, or
   cited by a registry, or this bundle's own. A NEW one fails here rather
   than quietly joining the deployment. This is deliberately stricter than
   "fetched" alone, because telling a fetch from a citation by reading
   source is unreliable - a URL assembled from a template string looks like
   prose - and the honest way to be safe about that is to classify all of
   them. */
const unaccounted = [];
for (const [host, pages] of [...found].sort()) {
  if (SELF.has(host)) continue;
  if (FETCHED[host]) {
    ok(`${host} is fetched by ${pages.size} page(s) and disclosed in THIRD_PARTY.md`,
      third.includes(FETCHED[host].documented));
    continue;
  }
  if (cited.has(host)) { n++; continue; }      // cited, and a registry stands behind it
  if (PAGE_LINKS[host]) { n++; continue; }     // an outbound link the page offers
  unaccounted.push([host, pages]);
}
ok('every external origin in a built page is fetched-and-disclosed, cited by a '
  + 'registry, offered as a page link, or this bundle\'s own',
  unaccounted.length === 0);
for (const [host, pages] of unaccounted) {
  console.error(`      unaccounted: ${host}  (in ${[...pages].join(', ')})`);
  console.error('      Declare it in FETCHED here and in THIRD_PARTY.md, or cite it '
    + 'from the registry that stands behind it, or remove it.');
}

// the reverse: a FETCHED entry no page reaches any more is a stale
// permission, and stale permissions are how an allowlist stops meaning anything
for (const host of Object.keys(FETCHED)) {
  ok(`${host} is still actually referenced (no stale permission)`, found.has(host));
}

console.log(bad
  ? `lint_external: ${bad} problem(s) across ${PAGES.length} built pages`
  : `lint_external: ${n} checks - ${found.size} external origin(s) across `
    + `${PAGES.length} built pages; ${Object.keys(FETCHED).length} fetched and `
    + `disclosed, the rest cited by a registry or this bundle's own`);
process.exit(bad ? 1 : 0);
