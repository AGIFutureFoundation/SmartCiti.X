/**
 * RTL correctness, held at the source (v3.3 exit criterion 3, ROADMAP.md).
 *
 * §23's lesson, restated for direction instead of layout: a rendering claim
 * needs a rendering check, not an assertion that eyeballs well. This file
 * holds the source-level half of that check — the same split test_3d.mjs
 * already uses for the 3D environment's teardown contracts: no browser runs
 * here (verify_all.sh reaches no network and opens no browser), so this
 * proves the THINGS THAT MAKE RTL CORRECT are present in the generators —
 * the `dir="rtl"` switch actually reaching the document root, and logical
 * CSS properties in place of the hard-coded `left`/`right` that used to sit
 * in build_landing.py and build_map.py (found by reading, the same way the
 * brand drift and the 43%-wrong layout constant were found — nothing here
 * was verifying direction before this file existed).
 *
 * The scratch, actually-rendered half — real Chromium, the Arabic tab
 * selected, bounding boxes measured English vs Arabic, checked for overflow
 * — is run separately (not committed; browser-free stays the rule for
 * verify_all.sh) and reported in the PR/commit that added this file.
 */
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const HERE = new URL('.', import.meta.url);
const landing = readFileSync(new URL('build_landing.py', HERE), 'utf8');
const map = readFileSync(new URL('build_map.py', HERE), 'utf8');
const languages = readFileSync(new URL('build_languages.py', HERE), 'utf8');

/* ------------------------------------------------------- the dir switch - */
ok('build_languages.py stamps dir on every locale <section> from the catalog\'s own dir field, not a guess',
  /<section class="loc" id="loc-\{code\}" lang="\{code\}" dir="\{c\["dir"\]\}" hidden>/.test(languages));
ok('build_languages.py\'s show() mirrors the shown section\'s dir onto <html> — the gap this file exists '
  + 'to close: before this, only the inner <section> ever carried dir="rtl"; the page chrome (nav tabs, '
  + 'header) stayed pinned dir="ltr" no matter which language was selected, so document.dir never actually '
  + 'read "rtl" for a real user selecting Arabic',
  /document\.documentElement\.dir = document\.getElementById\('loc-' \+ loc\)\.dir;/.test(languages));
ok('the dir mirror runs inside show(), which both the tab click handler and the initial locale-detect call use — '
  + 'so first paint and every subsequent switch both set it, not just one path',
  (() => {
    const fn = languages.slice(languages.indexOf('function show(loc)'), languages.indexOf('for (const t of tabs) t.addEventListener'));
    return /documentElement\.dir/.test(fn)
      && /t\.addEventListener\('click', \(\) => show\(t\.dataset\.loc\)\);/.test(languages)
      && /^show\(/m.test(languages.slice(languages.indexOf("t.addEventListener('click'")));
  })());

/* ------------------------------------------------- logical CSS properties - */
// The specific physical-direction rules found by reading (see the file
// header): each must be gone, and its logical replacement must be present.
const FIXED = [
  { file: 'build_landing.py', src: landing, wrong: /margin-left:auto/, right: /margin-inline-start:auto/ },
  { file: 'build_landing.py', src: landing, wrong: /padding-left:22px/, right: /padding-inline-start:22px/ },
  { file: 'build_landing.py', src: landing, wrong: /position:absolute;left:0/, right: /position:absolute;inset-inline-start:0/ },
  { file: 'build_landing.py', src: landing, wrong: /text-align:left/, right: /text-align:start/ },
  { file: 'build_landing.py', src: landing, wrong: /padding-right:0/, right: /padding-inline-end:0/ },
  { file: 'build_landing.py', src: landing, wrong: /padding:0 14px 9px 0/, right: /padding-block:0 9px;padding-inline:0 14px/ },
  { file: 'build_landing.py', src: landing, wrong: /padding:11px 14px 11px 0/, right: /padding-block:11px;padding-inline:0 14px/ },
  { file: 'build_map.py', src: map, wrong: /margin-left:auto/, right: /margin-inline-start:auto/ },
  { file: 'build_map.py', src: map, wrong: /border-right:1px solid var\(--rule\);padding:20px/, right: /border-inline-end:1px solid var\(--rule\);padding:20px/ },
  { file: 'build_map.py', src: map, wrong: /border-right:none/, right: /border-inline-end:none/ },
  { file: 'build_map.py', src: map, wrong: /text-align:left;padding:9px 10px/, right: /text-align:start;padding:9px 10px/ },
];
for (const f of FIXED) {
  ok(`${f.file}: ${f.right.source} replaces the physical-direction rule that would not have mirrored under RTL`,
    !f.wrong.test(f.src) && f.right.test(f.src));
}

// No OTHER hard-coded physical-direction declaration survives in either
// file's CSS — asserted broadly, not just for the specific rules listed
// above, so a new one introduced later fails this test instead of shipping
// unnoticed the way the original ones did.
function physicalDirectionHits(src, file) {
  const css = src; // CSS lives inline in both files' page-building strings
  const rules = [
    /\bleft\s*:\s*[^;{}]/g, /\bright\s*:\s*[^;{}]/g,
    /margin-left\s*:/g, /margin-right\s*:/g,
    /padding-left\s*:/g, /padding-right\s*:/g,
    /border-left\s*:/g, /border-right\s*:/g,
    /text-align\s*:\s*(left|right)\b/g,
    /float\s*:\s*(left|right)\b/g,
  ];
  const hits = [];
  for (const re of rules) {
    for (const m of css.matchAll(re)) hits.push(`${file}: "${m[0]}"`);
  }
  return hits;
}
const stray = [...physicalDirectionHits(landing, 'build_landing.py'), ...physicalDirectionHits(map, 'build_map.py')];
ok('no other hard-coded left/right CSS property survives in build_landing.py or build_map.py '
  + (stray.length ? `— found: ${stray.join(', ')}` : ''),
  stray.length === 0);
ok('build_languages.py — the one page that actually renders per-locale today — already used logical '
  + 'properties before this file existed (border-inline-start, text-align:end), which is why it alone '
  + 'needed no CSS fix, only the document.dir mirror above',
  /border-inline-start:3px solid var\(--mark\)/.test(languages) && /text-align:end/.test(languages)
  && physicalDirectionHits(languages, 'build_languages.py').length === 0);

/* -------------------------------------------------- the mirrored layout -- */
// CSS Grid and Flexbox are direction-aware by construction (grid-template-
// columns places its first track at the inline-start edge, which is the
// RIGHT edge under dir="rtl" — no property needs to change for that to be
// true), so the two-column shell in build_map.py mirrors without a rule of
// its own; asserted here so a future rewrite to explicit left/right
// positioning would be caught by the broad physicalDirectionHits() sweep
// above rather than silently reintroducing the defect.
ok('the map\'s sidebar/plan shell is a CSS grid (inline-axis-aware, so RTL reorders it without an explicit rule)',
  /\.shell\{\{display:grid;grid-template-columns:266px minmax\(0,1fr\);/.test(map));

console.log(`web/test_rtl: ${n} checks passed`);
