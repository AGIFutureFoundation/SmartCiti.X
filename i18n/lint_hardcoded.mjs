#!/usr/bin/env node
/**
 * Hard-coded-English lint (v3.3 exit criterion 2, ROADMAP.md).
 *
 * Landing, campus-map and languages must carry zero hard-coded English
 * strings — user-visible text belongs in the i18n catalog (`i18n/locales/`),
 * not typed into the Python page generators. Same shape of argument as
 * brand/lint.mjs: a string a reader can see is a claim about what the page
 * says, and a claim needs a checker.
 *
 * This reads the GENERATOR SOURCE (web/build_landing.py, web/build_map.py,
 * web/build_languages.py), not the built HTML. The built pages interpolate
 * catalog strings into English text either way, so grepping the OUTPUT would
 * only prove the catalog's own English values ended up on the page — it
 * cannot tell a `{S('landing.hero.title')}` lookup apart from a literal
 * `'Train the trades...'` typed straight into the Python. Reading the
 * generator is the only way to prove the STRING'S HOME is the catalog.
 *
 * What counts as user-visible text, in scope for this lint:
 *   - text nodes inside the one HTML-producing string each builder
 *     assembles (`BODY` in build_landing.py, `PAGE` in build_map.py, `page`
 *     in build_languages.py) — including inside that page's own <script>,
 *     since a JS template literal can carry hard-coded prose just as easily
 *     as a Python string can;
 *   - the `alt`, `title`, `placeholder` and `aria-label` attribute values on
 *     any element in that string.
 * Out of scope, and why:
 *   - <style> content and CSS-in-JS (property names, selectors) — styling,
 *     not prose a viewer reads as language;
 *   - code identifiers, operators and non-prose JS/CSS tokens generally —
 *     this lint flags a candidate only when it reads as at least two English
 *     words, so `toLocaleString`, `--rule` and `TI-01` do not trip it;
 *   - a Python f-string's `{...}` interpolations — by construction these are
 *     either a catalog lookup (`S('key')`), a pack-derived number, or code;
 *     literal text is only what remains OUTSIDE every `{...}`, at the exact
 *     brace nesting depth zero, which is what this lint actually scans (see
 *     stripInterpolations below — depth-counted the same way
 *     training/build.py's balanced-paren reader counts parens, because an
 *     f-string's escaped `{{`/`}}` and a JS object literal nested inside a
 *     Python interpolation both still balance in raw brace COUNT even
 *     though they mean different things to their own language);
 *   - the brand name and its parts ("SmartCiti.X", "Trade Craft Academy",
 *     "AGI Corp", "AGI Future Foundation", "powered by AGI Corp") — identity,
 *     not translatable copy, the same exemption brand/lint.mjs itself
 *     carries for the rule table that names the brand;
 *   - two planned-campus place names, "Oakland Training Yard" and
 *     "SF Bridgehead" — proper nouns, the same class of exemption as the
 *     111 hall names i18n/README.md documents as staying in English by
 *     design, not translatable UI chrome. Documented here AND there.
 *
 *   node i18n/lint_hardcoded.mjs
 *
 * Exits non-zero on any hard-coded string found, or if the self-test at the
 * bottom (a fixture snippet the rule must catch) fails to catch it — a
 * guard nobody has watched fail is not proven, the same argument
 * security/test_sbom.mjs makes by tampering a byte and training/build.py's
 * balanced-paren reader makes by testing itself on a nested expression.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const ROOT = fileURLToPath(new URL('..', import.meta.url));

// ---------------------------------------------------------------- brand ---
const EXEMPT_EXACT = new Set([
  'SmartCiti.X', 'Trade Craft Academy', 'AGI Corp', 'AGI Future Foundation',
  'powered by AGI Corp', 'SmartCiti', 'Trade Craft', 'Academy',
  // planned-campus place names — see file-header note above and
  // i18n/README.md's hall-name exemption, the same class of proper noun.
  'Oakland Training Yard', 'SF Bridgehead',
]);
// Also strip the brand name where it appears INSIDE a longer literal (e.g.
// "SmartCiti.X : Trade Craft Academy" in a title-block <text>), so what is
// left over is judged on its own.
const EXEMPT_SUBSTRINGS = [
  'SmartCiti.X : Trade Craft Academy', 'SmartCiti.X', 'Trade Craft Academy',
  'AGI Future Foundation', 'AGI Corp', 'Oakland Training Yard', 'SF Bridgehead',
];

/**
 * Depth-count `{`/`}` and keep only the characters at depth 0. Works on raw
 * character counts, not f-string semantics — sound because Python requires
 * every f-string's braces (real interpolations AND escaped `{{`/`}}`
 * doubling) to balance for the file to parse at all, and this file DOES
 * parse (the build runs). See the file-header note for why this also
 * correctly discards CSS and JS bodies, which are wrapped in doubled braces
 * throughout these generators.
 */
export function stripInterpolations(s) {
  let out = '';
  let depth = 0;
  for (const c of s) {
    if (c === '{') { depth++; continue; }
    if (c === '}') { depth = Math.max(0, depth - 1); continue; }
    if (depth === 0) out += c;
  }
  return out;
}

const ATTR_RE = /\b(?:alt|title|placeholder|aria-label)\s*=\s*"([^"]*)"/g;

/**
 * English-prose test: at least two words, SEPARATED BY WHITESPACE (not by
 * punctuation), each purely alphabetic (with an internal apostrophe or
 * hyphen allowed). This is deliberately stricter than "two letter runs"
 * so an email address (`x@agifuturefoundation.org`, two dot/at-separated
 * runs, no space) or a CSS/JS token (`toLocaleString`, one run) does not
 * trip it, while "Site address" or "Not built" (two space-separated words)
 * does.
 */
function looksLikeProse(s) {
  const words = s.trim().split(/\s+/).filter((w) => /^[A-Za-z]+(?:['-][A-Za-z]+)*$/.test(w));
  return words.length >= 2;
}

// A JS string/template literal, single/double/back-quoted, with escapes.
const JS_STRING_RE = /'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*"|`(?:[^`\\]|\\.)*`/g;

function candidates(htmlText) {
  const out = [];
  // <style> content is CSS — selectors and properties, not prose a viewer
  // reads as language (see the file-header note on scope).
  let text = htmlText.replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, ' ');
  // <script> content is JS code — variable names, comments and bare
  // statements are not prose and would flood this lint with noise (a code
  // comment explaining the code is not a string on the page). What COULD
  // still carry hard-coded prose is a JS string/template literal, so pull
  // those out and check THEM, then drop the rest of the script wholesale.
  text = text.replace(/<script\b[^>]*>([\s\S]*?)<\/script>/gi, (_, body) => {
    // Strip `//` line comments first — a comment can itself contain an
    // apostrophe ("catalog's own strings"), which would otherwise look
    // like the OPEN of a string literal to JS_STRING_RE and swallow
    // everything up to the next quote character, real code included. None
    // of this file's own string literals contain `//`, so truncating each
    // line at its first `//` is safe here (documented, not assumed).
    const noComments = body.split('\n').map((l) => l.replace(/\/\/.*/, '')).join('\n');
    for (const m of noComments.matchAll(JS_STRING_RE)) {
      out.push(m[0].slice(1, -1)); // strip the quote/backtick delimiters
    }
    return ' ';
  });
  for (const m of text.matchAll(ATTR_RE)) out.push(m[1]);
  for (const line of text.replace(/<[^>]*>/g, '\n').split('\n')) {
    const t = line.trim();
    if (t) out.push(t);
  }
  return out;
}

/** Extract one `NAME = f?("""|''')...\1` block's inner text, non-greedy. */
function extractVar(src, name) {
  const re = new RegExp(`\\b${name}\\s*=\\s*f?("""|''')`);
  const m = re.exec(src);
  if (!m) throw new Error(`lint_hardcoded: cannot find ${name} = f"""...""" in source`);
  const q = m[1];
  const start = m.index + m[0].length;
  const end = src.indexOf(q, start);
  if (end < 0) throw new Error(`lint_hardcoded: unterminated ${name} block`);
  return src.slice(start, end);
}

/** landing.py's final assembly concatenates a few plain string literals
 * (not an f-string) around BODY — extract those too so the title/link
 * lines are checked, not skipped. Bounded by paren depth (same
 * balanced-reading precedent as stripInterpolations/training/build.py),
 * not a guessed line offset, so it stops exactly at the assembly's own
 * closing `)` rather than spilling into whatever code follows. */
function extractConcatLiterals(src, fromMarker) {
  const i = src.indexOf(fromMarker);
  if (i < 0) return '';
  const open = src.indexOf('(', i);
  let depth = 0, end = -1;
  for (let k = open; k < src.length; k++) {
    if (src[k] === '(') depth++;
    else if (src[k] === ')') { depth--; if (depth === 0) { end = k; break; } }
  }
  const slice = src.slice(open, end < 0 ? src.length : end + 1);
  let out = '';
  const re = /'((?:[^'\\]|\\.)*)'/g;
  for (const m of slice.matchAll(re)) out += m[1].replace(/\\n/g, '\n') + '\n';
  return out;
}

function check(file, pieces, exemptExtra = []) {
  const hits = [];
  const seen = new Set();
  const exemptAll = new Set([...EXEMPT_EXACT, ...exemptExtra]);
  for (const raw of pieces) {
    let stripped = stripInterpolations(raw);
    for (const s of candidates(stripped)) {
      let t = s;
      for (const ex of EXEMPT_SUBSTRINGS) t = t.split(ex).join(' ');
      t = t.replace(/[·—–&][a-z#0-9]*;?/gi, ' ').trim();
      if (exemptAll.has(s.trim()) || exemptAll.has(t)) continue;
      if (!looksLikeProse(t)) continue;
      const key = `${file}::${t}`;
      if (seen.has(key)) continue;
      seen.add(key);
      hits.push({ file, text: t });
    }
  }
  return hits;
}

// ------------------------------------------------------------ the pages ---
function lintFile(rel, varName, opts = {}) {
  const src = readFileSync(ROOT + '/' + rel, 'utf8');
  const pieces = [extractVar(src, varName)];
  if (opts.concatFrom) pieces.push(extractConcatLiterals(src, opts.concatFrom));
  return check(rel, pieces);
}

function run() {
  const hits = [
    ...lintFile('web/build_landing.py', 'BODY', { concatFrom: "page = ('<title>" }),
    ...lintFile('web/build_map.py', 'PAGE'),
    ...lintFile('web/build_languages.py', 'page'),
  ];
  return hits;
}

// -------------------------------------------------------------- self-test -
// Prove the rule bites before trusting it clean, the way security/test_sbom
// .mjs proves its hash check by tampering a byte and training/build.py's
// balanced-paren reader proves itself on a nested expression.
function selfTest() {
  const fixtureBad = extractCandidatesFrom(`
    <div class="wrap">
      <h1>{S('landing.hero.title')}</h1>
      <p>Please contact our sales team before you sign anything.</p>
    </div>
  `);
  if (!fixtureBad.some((c) => /contact our sales team/.test(c))) {
    throw new Error('self-test FAILED: a hard-coded sentence was not detected');
  }
  const fixtureAttr = extractCandidatesFrom(
    '<img alt="A hand-typed caption nobody translated">',
  );
  if (!fixtureAttr.some((c) => /hand-typed caption/.test(c))) {
    throw new Error('self-test FAILED: hard-coded alt text was not detected');
  }
  const fixtureJs = extractCandidatesFrom(
    "<script>el.textContent = 'Please wait while we load your results';</script>",
  );
  if (!fixtureJs.some((c) => /Please wait while we load/.test(c))) {
    throw new Error('self-test FAILED: a hard-coded JS string literal was not detected');
  }
  const fixtureClean = extractCandidatesFrom(`
    <style>.kicker{font-family:"IBM Plex Mono",monospace;text-transform:uppercase}</style>
    <div class="wrap">
      <h1>{S('landing.hero.title')}</h1>
      <p>{S('landing.hero.lede')}</p>
      <span class="mono">TI-01</span>
      <div style="color:var(--ink)">SmartCiti.X : Trade Craft Academy</div>
    </div>
    <script>
      // a code comment explaining what happens next, in full English sentences
      const dlist = document.getElementById('dlist');
      el.setAttribute('aria-label', I18N.ariaHall.replace('{name}', h.name));
    </script>
  `);
  if (fixtureClean.length) {
    throw new Error(`self-test FAILED: a clean, catalog-sourced snippet was flagged: ${JSON.stringify(fixtureClean)}`);
  }
}

function extractCandidatesFrom(snippet) {
  return check('fixture', [snippet]).map((h) => h.text);
}

selfTest();
console.log('lint_hardcoded: self-test passed (catches a hard-coded sentence, catches hard-coded '
  + 'alt text, and does not flag a clean catalog-sourced snippet)');

const hits = run();
if (hits.length) {
  console.error(`lint_hardcoded: ${hits.length} hard-coded string${hits.length === 1 ? '' : 's'} found\n`);
  for (const h of hits) console.error(`  ${h.file}\n    "${h.text}"\n`);
  console.error('move this text into i18n/locales/en.json (and the other seven locales) and '
    + 'read it back with S(\'...\') instead of typing it into the generator.');
  process.exit(1);
}
console.log('lint_hardcoded: web/build_landing.py, web/build_map.py and web/build_languages.py '
  + 'carry zero hard-coded English strings (brand name and planned-campus place names exempted, '
  + 'see this file\'s header)');
