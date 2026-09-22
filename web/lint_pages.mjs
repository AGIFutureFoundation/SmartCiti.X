/**
 * The PAGE, checked - not the data behind it.
 *
 * A sibling app shipped completely broken while every one of its checks
 * passed, because every check there validated the data and none looked at
 * the page. Three faults, all static, all visible to anyone who opened the
 * file: a fragment of an older build's JavaScript sat in the body OUTSIDE
 * any <script> and rendered as visible text; the body was an older app's
 * shell while the script addressed six element ids that existed nowhere in
 * the file, so three functions threw on load; the doctype was declared
 * twice and two other pages declared no <meta charset> and rendered
 * mojibake. This bundle builds its pages from Python generators and holds
 * them to 2,000-odd checks, none of which would have noticed any of that.
 * This file closes that gap. It reads the built HTML the way a browser's
 * tokenizer does and asks the questions a browser would answer by breaking.
 *
 * Runs in verify_all.sh. No browser, no network, no dependency beyond the
 * node stdlib: it reads the built files. `node web/lint_pages.mjs` walks
 * every .html in the bundle (vendor/ and node_modules/ excluded);
 * `node web/lint_pages.mjs FILE...` lints just those files, which is how
 * the mutation tests exercise it against a broken copy.
 *
 * CHECKS, each with the fault it targets and the false positive it was
 * narrowed against (a check that cries wolf gets switched off):
 *
 *  1. valid UTF-8. Fault: bytes that are not UTF-8 render as U+FFFD once
 *     the page (correctly) declares utf-8. FP: a page deliberately in a
 *     legacy encoding - none here, and check 3 forbids it anyway.
 *  2. exactly one doctype, and nothing but whitespace / a BOM / comments
 *     before it. Fault: none (quirks mode), or two (the second is parse
 *     garbage), or one after content (also quirks). FP: a comment or BOM
 *     ahead of the doctype is legal and is allowed.
 *  3. one <meta charset> (or http-equiv content-type), utf-8, closing
 *     within the first 1024 bytes - the spec's prescan window. Fault:
 *     missing, late, duplicated, or a non-utf-8 value. FP: `charset=` in a
 *     script body, a comment, or prose is not a declaration, so the search
 *     runs only over markup-context tags.
 *  4. script tags balance in tokenizer order: after `<script ...>` the body
 *     runs to the next `</script` no matter what it contains (a browser
 *     does the same, which is why `<\/script>` exists), so `<script` inside
 *     a JS string or regex is never a tag, and a `</script>` inside a JS
 *     string IS a close - and the orphaned tail it leaves is then caught by
 *     check 5. Fault: an unclosed <script>, a stray </script>, an
 *     unterminated comment. FP: `<script` in a comment, <style>, <title>
 *     or <textarea>, all raw-text contexts, is skipped as text.
 *  5. no JavaScript rendered as visible text: a text run (between tags,
 *     comments removed, outside <pre>/<code>/<textarea>/<template> and the
 *     raw-text elements) that shows TWO OR MORE distinct JS signatures -
 *     `function name(`, `=> {`, `const x =`, `document.getElementById(`,
 *     `.addEventListener(`, `});`, `window.x =`, `return ...;`. Fault: a
 *     leaked build fragment, which is many lines of all of these. FP: prose
 *     that quotes one JavaScript idiom outside <code> ("call
 *     addEventListener on it") - one signature never fails; a paragraph
 *     that quotes two verbatim idioms outside <code> would, and belongs in
 *     <code>.
 *  6. every element id a page's own script addresses by literal exists
 *     somewhere the page can produce it. An address is
 *     getElementById('x'), querySelector('#x'), querySelector('#x ...')
 *     (its root), $('#x'). It is satisfied by an id="x" in the static
 *     markup, or - the runtime case - an id="x" / id='x' literal inside any
 *     of the page's own inline scripts (a renderer's template), `.id = 'x'`,
 *     setAttribute('id', 'x'), or an `id: 'x'` property. An interpolated
 *     template id (`id="row${i}"`) satisfies any addressed id that starts
 *     with its literal prefix when the prefix is 2+ characters; an empty
 *     prefix satisfies nothing, on purpose. Fault: the observed one - ids
 *     addressed that nothing in the file creates. FP: an id assembled by
 *     string concatenation outside a template literal ('row' + i) and then
 *     addressed by literal elsewhere; rename either side to the same shape.
 *     An `id:` data property (a scenario id that happens to equal an element
 *     id) is a known blind spot of the conservative direction: it can hide
 *     a fault, never invent one.
 *  7. an id addressed AT BOOT is in the static markup, and for a classic
 *     script the element precedes the script. "At boot" is deliberately
 *     narrow: the address sits at bracket depth 0 of an inline script - a
 *     top-level statement that runs when the script executes - and is
 *     either chained straight away (`getElementById('x').foo`) or assigned
 *     to a name that is dereferenced at depth 0 later with no null guard.
 *     Code inside any function, handler or DOMContentLoaded body is depth
 *     1+ and is not boot. A concise arrow at top level
 *     (`const f = () => document.getElementById('x')`) is skipped by the
 *     `=>` in its statement. Fault: a runtime-only id read before its
 *     renderer has run, or a body element read by a classic script placed
 *     above it. FP: a top-level lookup held in a variable and only ever
 *     used inside a null check the scan does not recognise - the scan
 *     recognises `if (x)`, `if (!x)`, `x &&`, `x ?.`, `x ||`.
 *  8. each inline script's brackets balance after strings, comments,
 *     template literals and regex literals are blanked - a script that is
 *     a fragment of a longer one, or two scripts pasted into one, does
 *     not. FP: a division whose left operand ends in a token the blanker
 *     reads as an operator (`x++ / 2`) followed on the same line by a quote
 *     or bracket; there is none in this bundle and the balance printed in
 *     each page's summary line is how you would find one.
 *
 * TRAPS this file is written around, because they have bitten here before:
 * a check for "string X is absent" matches the comment explaining why X
 * was removed, so anything read out of a script is read out of the script
 * with comments and strings blanked; `<script` inside a regex literal or a
 * string is not a tag (see check 4); files may carry deliberate NUL bytes,
 * so everything is read as UTF-8 text in-process and nothing shells out.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';

const ROOT = resolve(new URL('..', import.meta.url).pathname);
let n = 0, bad = 0;

const ok = (page, m, c, evidence = []) => {
  if (c) { n++; console.log(`  ok  ${page}: ${m}`); return; }
  bad++;
  console.log(`FAIL  ${page}: ${m}`);
  for (const e of evidence) console.log(`      ${e}`);
};

/* ------------------------------------------------------------- pages --- */
function walk(dir, out) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    if (e.isDirectory()) {
      if (['.git', 'node_modules', 'vendor', '__pycache__'].includes(e.name)) continue;
      walk(join(dir, e.name), out);
    } else if (e.isFile() && e.name.toLowerCase().endsWith('.html')) {
      out.push(join(dir, e.name));
    }
  }
  return out;
}
const args = process.argv.slice(2);
const PAGES = (args.length ? args.map((a) => resolve(a)) : walk(ROOT, []).sort())
  .filter((p) => { try { return statSync(p).isFile(); } catch { return false; } });
const label = (p) => (p.startsWith(ROOT + '/') ? relative(ROOT, p) : p);

/* ----------------------------------------------------------- helpers --- */
const lineOf = (text, at) => { let l = 1; for (let i = 0; i < at && i < text.length; i++) if (text.charCodeAt(i) === 10) l++; return l; };
const snip = (s, w = 80) => s.replace(/\s+/g, ' ').trim().slice(0, w);

/* attributes of one start tag: `<name a="1" b='2' c=3 d>` -> {a:'1',...} */
function parseAttrs(tag) {
  const out = {};
  const body = tag.replace(/^<[a-zA-Z][^\s/>]*/, '').replace(/\/?>$/, '');
  const re = /([^\s"'<>/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
  for (const m of body.matchAll(re)) out[m[1].toLowerCase()] = m[2] ?? m[3] ?? m[4] ?? '';
  return out;
}

/* JavaScript with its strings, comments, template literals and regex
   literals blanked to spaces of the same length: what is left is structure
   (brackets, keywords, identifiers) and nothing that could quote a bracket
   or a `<script`. Length-preserving, so offsets into the blanked text are
   offsets into the source. */
function blankJs(src) {
  const n = src.length;
  let out = '', i = 0, lastSig = '', lastWord = '';
  const pad = (a, b) => ' '.repeat(Math.max(0, b - a));
  const keywordBefore = /^(return|typeof|case|in|of|instanceof|new|delete|void|throw|do|else|yield|await)$/;
  while (i < n) {
    const c = src[i], d = src[i + 1];
    if (c === '/' && d === '/') { let j = src.indexOf('\n', i); if (j < 0) j = n; out += pad(i, j); i = j; continue; }
    if (c === '/' && d === '*') { let j = src.indexOf('*/', i + 2); j = j < 0 ? n : j + 2; out += pad(i, j); i = j; continue; }
    if (c === '"' || c === "'") {
      let j = i + 1;
      while (j < n && src[j] !== c && src[j] !== '\n') { if (src[j] === '\\') j++; j++; }
      j++; out += c + pad(i + 1, j - 1) + c; i = j; lastSig = c; lastWord = ''; continue;
    }
    if (c === '`') {
      let j = i + 1, depth = 0;
      while (j < n) {
        if (src[j] === '\\') { j += 2; continue; }
        if (src[j] === '`' && depth === 0) break;
        if (src[j] === '$' && src[j + 1] === '{') { depth++; j += 2; continue; }
        if (src[j] === '}' && depth > 0) depth--;
        j++;
      }
      j++; out += '`' + pad(i + 1, j - 1) + '`'; i = j; lastSig = '`'; lastWord = ''; continue;
    }
    if (c === '/') {
      const regexHere = lastSig === '' || '(,=:[!&|?{};+-*%<>~^'.includes(lastSig)
        || (/[A-Za-z_$]/.test(lastSig) && keywordBefore.test(lastWord));
      if (regexHere) {
        let j = i + 1, cls = false;
        while (j < n && src[j] !== '\n') {
          if (src[j] === '\\') { j += 2; continue; }
          if (src[j] === '[') cls = true; else if (src[j] === ']') cls = false;
          else if (src[j] === '/' && !cls) break;
          j++;
        }
        j++; while (j < n && /[a-z]/.test(src[j])) j++;
        out += '/' + pad(i + 1, j - 1) + '/'; i = j; lastSig = '/'; lastWord = ''; continue;
      }
    }
    out += c;
    if (!/\s/.test(c)) {
      lastSig = c;
      lastWord = /[A-Za-z_$0-9]/.test(c) ? lastWord + c : '';
    }
    i++;
  }
  return out;
}

/* bracket depth at every offset of blanked JS, and the final balance */
function depthMap(b) {
  const d = new Int32Array(b.length + 1);
  let depth = 0;
  for (let i = 0; i < b.length; i++) {
    const c = b[i];
    if (c === '{' || c === '(' || c === '[') depth++;
    else if (c === '}' || c === ')' || c === ']') depth--;
    d[i + 1] = depth;
  }
  return d;
}

/* ---------------------------------------------------------- tokenizer --- */
/* A walk over the file in the order and states a browser's tokenizer uses.
   Markup context is where tags live; a comment runs to `-->`; a raw-text
   element (script, style, title, textarea, xmp, noscript, noembed,
   noframes, iframe) runs to its own close tag and NOTHING inside it is a
   tag. Everything the checks need is collected in one pass. */
const RAW = new Set(['script', 'style', 'title', 'textarea', 'xmp', 'noscript', 'noembed', 'noframes', 'iframe']);
const NO_TEXT = new Set(['pre', 'code', 'template']);   // visible code, or not in the DOM

function tokenize(text) {
  const T = {
    doctypes: [], tags: [], scripts: [], texts: [], staticIds: new Map(),
    strayCloses: [], unclosedScripts: [], unterminatedComments: [], firstTagAt: -1,
  };
  const n = text.length;
  let i = 0, textStart = 0;
  let noText = 0;                       // depth inside pre/code/template
  const openStack = [];                 // names of open NO_TEXT elements
  const flushText = (end) => { if (end > textStart && noText === 0) T.texts.push({ start: textStart, end }); };
  const endTag = (from) => {            // index just past the `>` of a tag starting at `from`, honouring quotes
    let j = from + 1, q = null;
    while (j < n) {
      const c = text[j];
      if (q) { if (c === q) q = null; }
      else if (c === '"' || c === "'") q = c;
      else if (c === '>') return j + 1;
      j++;
    }
    return n;
  };
  while (i < n) {
    if (text[i] !== '<') { i++; continue; }
    if (text.startsWith('<!--', i)) {
      flushText(i);
      let j = text.indexOf('-->', i + 4);
      if (j < 0) { T.unterminatedComments.push(i); j = n; } else j += 3;
      i = j; textStart = i; continue;
    }
    if (/^<!doctype/i.test(text.slice(i, i + 9))) {
      flushText(i);
      T.doctypes.push(i); i = endTag(i); textStart = i; continue;
    }
    const m = /^<(\/?)([a-zA-Z][a-zA-Z0-9-]*)/.exec(text.slice(i, i + 40));
    if (!m) { i++; continue; }          // `<` followed by space, digit etc. is text
    flushText(i);
    const isClose = m[1] === '/', name = m[2].toLowerCase();
    const tagEnd = endTag(i);
    const tag = text.slice(i, tagEnd);
    if (T.firstTagAt < 0) T.firstTagAt = i;
    if (isClose && name === 'script') { T.strayCloses.push(i); i = tagEnd; textStart = i; continue; }
    const attrs = isClose ? {} : parseAttrs(tag);
    T.tags.push({ name, isClose, at: i, end: tagEnd, attrs });
    if (!isClose && attrs.id !== undefined && noText === 0 && !openStack.includes('template')) {
      if (!T.staticIds.has(attrs.id)) T.staticIds.set(attrs.id, i);
    }
    i = tagEnd;
    if (!isClose && RAW.has(name) && !/\/>$/.test(tag)) {
      const closeRe = new RegExp(`</${name}(?=[\\s/>])`, 'ig');
      closeRe.lastIndex = i;
      const cm = closeRe.exec(text);
      const bodyEnd = cm ? cm.index : n;
      if (name === 'script') {
        T.scripts.push({ attrs, at: T.tags[T.tags.length - 1].at, bodyStart: i, body: text.slice(i, bodyEnd) });
        if (!cm) T.unclosedScripts.push(T.tags[T.tags.length - 1].at);
      }
      i = cm ? endTag(cm.index) : n;
      textStart = i; continue;
    }
    if (NO_TEXT.has(name)) {
      if (!isClose) { noText++; openStack.push(name); }
      else if (noText > 0) { noText--; openStack.pop(); }
    }
    textStart = i;
  }
  flushText(n);
  return T;
}

/* --------------------------------------------------------- id sources --- */
const JS_TYPES = /^(|module|text\/javascript|application\/javascript|text\/ecmascript|application\/ecmascript)$/i;
const JSON_TYPES = /json|importmap|speculationrules/i;
const scriptKind = (s) => {
  if (s.attrs.src !== undefined) return 'external';
  const t = (s.attrs.type || '').trim();
  if (JS_TYPES.test(t)) return 'js';
  if (JSON_TYPES.test(t)) return 'json';
  return 'other';
};

/* every id a script addresses by literal: [{id, at (offset in body), form}] */
function addressedIds(body) {
  const out = [];
  const forms = [
    [/\bgetElementById\(\s*(['"`])([^'"`$\\]+)\1\s*\)/g, 'getElementById'],
    [/\bquerySelector(?:All)?\(\s*(['"`])#([A-Za-z_][\w-]*)(?:[\s>+~.[:][^'"`]*)?\1/g, 'querySelector'],
    [/(?<![\w$.])\$\(\s*(['"`])#([A-Za-z_][\w-]*)(?:[\s>+~.[:][^'"`]*)?\1/g, '$'],
  ];
  for (const [re, form] of forms) for (const m of body.matchAll(re)) out.push({ id: m[2], at: m.index, end: m.index + m[0].length, form });
  return out;
}

/* ids a script can create at runtime: literal id attributes in any string
   or template, `.id = 'x'` (not `==`), setAttribute('id','x'), `id: 'x'`;
   plus the literal prefixes of interpolated template ids */
function runtimeIds(body) {
  const ids = new Map(), prefixes = [];
  const add = (id, at) => { if (!ids.has(id)) ids.set(id, at); };
  for (const m of body.matchAll(/\bid=\\?(["'])([^"'`\\$]+)\\?\1/g)) add(m[2], m.index);
  for (const m of body.matchAll(/\bid=\\?(["'])([^"'`\\$]*)\$\{/g)) prefixes.push(m[2]);
  for (const m of body.matchAll(/\.id\s*=(?!=)\s*(['"])([^'"`$]+)\1/g)) add(m[2], m.index);
  for (const m of body.matchAll(/setAttribute\(\s*(['"])id\1\s*,\s*(['"])([^'"`$]+)\2/g)) add(m[3], m.index);
  for (const m of body.matchAll(/\bid\s*:\s*(['"])([^'"`$]+)\1/g)) add(m[2], m.index);
  return { ids, prefixes: prefixes.filter((p) => p.length >= 2) };
}

/* the addresses at bracket depth 0 that a browser evaluates when the script
   runs, and that would throw on null: chained straight away, or held in a
   name that is dereferenced at depth 0 with no null guard */
function bootAddresses(body, addrs) {
  const b = blankJs(body), depth = depthMap(b), out = [];
  for (const a of addrs) {
    if (depth[a.at] !== 0) continue;
    // the statement this address belongs to: back to the last depth-0 `;`, `{` or `}`
    let s = a.at;
    while (s > 0 && !(depth[s] === 0 && /[;{}]/.test(b[s - 1]))) s--;
    if (b.slice(s, a.at).includes('=>')) continue;          // a concise arrow's body, not boot
    const after = b.slice(a.end, a.end + 3);
    if (/^\s*\./.test(after) && !/^\s*\?\./.test(after)) { out.push({ ...a, how: 'chained at once' }); continue; }
    const asg = /(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:document\.|window\.document\.)?$/.exec(b.slice(s, a.at));
    if (!asg) continue;
    const name = asg[1];
    const rest = b.slice(a.end);
    const restDepth = depth.subarray(a.end);
    const guarded = new RegExp(`if\\s*\\(\\s*!?\\s*${name}\\s*\\)|\\b${name}\\s*(?:&&|\\|\\||\\?\\.)`).test(rest);
    if (guarded) continue;
    const deref = new RegExp(`\\b${name}\\s*\\.(?!\\s*\\?)`, 'g');
    for (const m of rest.matchAll(deref)) {
      if (restDepth[m.index] === 0) { out.push({ ...a, how: `held in ${name}, dereferenced at line +${lineOf(rest, m.index) - 1}` }); break; }
    }
  }
  return out;
}

/* ------------------------------------------------------ text signatures --- */
const SIGNATURES = [
  ['function name(', /\bfunction\s+[\w$]+\s*\(/],
  ['=> {', /=>\s*\{/],
  ['const x =', /\b(?:const|let|var)\s+[\w$]+\s*=[^=]/],
  ['document.getElementById(', /\bdocument\.(?:getElementById|querySelector(?:All)?|createElement|addEventListener|body\.)/],
  ['.addEventListener(', /\.addEventListener\(/],
  ['});', /\}\s*\)?\s*;/],
  ['window.x =', /\bwindow\.[\w$]+\s*=[^=]/],
  ['return ...;', /\breturn\b[^;\n]*;/],
];

/* ------------------------------------------------------------- checks --- */
console.log('web/lint_pages.mjs');
ok('bundle', `the walk found built pages to lint (${PAGES.length})`, PAGES.length > 0);

for (const path of PAGES) {
  const page = label(path);
  const buf = readFileSync(path);
  let utf8 = true;
  try { new TextDecoder('utf-8', { fatal: true }).decode(buf); } catch { utf8 = false; }
  const text = buf.toString('utf8');
  const T = tokenize(text);
  const line = (at) => lineOf(text, at);

  const jsScripts = T.scripts.filter((s) => scriptKind(s) === 'js');
  const addrAll = jsScripts.flatMap((s) => addressedIds(s.body).map((a) => ({ ...a, script: s })));
  // runtime-created ids across every inline script, each with the line that creates it
  const rt = { ids: new Map(), prefixes: [] };
  for (const s of jsScripts) {
    const r = runtimeIds(s.body);
    for (const [id, at] of r.ids) if (!rt.ids.has(id)) rt.ids.set(id, s.bodyStart + at);
    rt.prefixes.push(...r.prefixes);
  }
  const balances = T.scripts.map((s) => (scriptKind(s) === 'js' || scriptKind(s) === 'json') ? depthMap(blankJs(s.body))[s.body.length] : 0);

  console.log(`page  ${page}  (${buf.length} bytes, ${T.scripts.length} script(s), ${T.staticIds.size} static ids, `
    + `${new Set(addrAll.map((a) => a.id)).size} addressed ids, ${rt.ids.size} runtime-created ids, `
    + `bracket balance ${balances.join('/') || '-'})`);

  /* 1. encoding */
  ok(page, 'the file is valid UTF-8 throughout', utf8,
    ['strict UTF-8 decode failed: a byte sequence in this file is not UTF-8 and will render as U+FFFD']);

  /* 2. doctype */
  {
    const before = T.doctypes.length ? text.slice(0, T.doctypes[0]).replace(/^﻿/, '').replace(/<!--[\s\S]*?-->/g, '').trim() : '';
    const first = T.doctypes.length > 0 && before === '' && (T.firstTagAt < 0 || T.doctypes[0] < T.firstTagAt);
    ok(page, 'exactly one doctype, and it is the first thing in the file', T.doctypes.length === 1 && first,
      T.doctypes.length === 0
        ? [`no <!doctype> found; the file starts with: ${snip(text.slice(0, 60))}`, 'a page without a doctype renders in quirks mode']
        : T.doctypes.length > 1
          ? [`${T.doctypes.length} doctypes, at lines ${T.doctypes.map(line).join(', ')}`]
          : [`the doctype at line ${line(T.doctypes[0])} comes after content: ${snip(text.slice(0, T.doctypes[0]).trim(), 60)}`]);
  }

  /* 3. charset */
  {
    const metas = T.tags.filter((t) => !t.isClose && t.name === 'meta'
      && (t.attrs.charset !== undefined || (/content-type/i.test(t.attrs['http-equiv'] || '') && /charset=/i.test(t.attrs.content || ''))));
    const value = (t) => (t.attrs.charset ?? (/charset=([^\s;"']+)/i.exec(t.attrs.content || '') || [])[1] ?? '').trim().toLowerCase();
    const endByte = (t) => Buffer.byteLength(text.slice(0, t.end), 'utf8');
    const bom = buf.length >= 3 && buf[0] === 0xEF && buf[1] === 0xBB && buf[2] === 0xBF;
    const good = metas.length === 1 && endByte(metas[0]) <= 1024 && value(metas[0]) === 'utf-8';
    ok(page, 'one <meta charset="utf-8">, and it closes within the first 1024 bytes', good,
      metas.length === 0
        ? [`no <meta charset> in the markup${bom ? ' (a BOM is present, which browsers honour, but the declaration is still required here)' : ''}`,
          `the head starts: ${snip(text.slice(0, 80))}`,
          `non-ASCII characters in the file: ${(text.match(/[^\x00-\x7F]/g) || []).length} - these render as mojibake when the server sends no charset`]
        : metas.length > 1
          ? [`${metas.length} charset declarations, at lines ${metas.map((t) => line(t.at)).join(', ')}`]
          : [`<meta charset> at line ${line(metas[0].at)} is "${value(metas[0])}" and ends at byte ${endByte(metas[0])} (must be utf-8, within 1024)`]);
  }

  /* 4. script tags */
  {
    const ev = [
      ...T.unclosedScripts.map((at) => `<script> opened at line ${line(at)} is never closed`),
      ...T.strayCloses.map((at) => `stray </script> at line ${line(at)} with no open <script> before it - the markup above it is what the browser ran as script, or nothing`),
      ...T.unterminatedComments.map((at) => `<!-- at line ${line(at)} is never closed; everything after it is swallowed`),
    ];
    ok(page, `script tags balance in tokenizer order (${T.scripts.length} <script>...</script> pair(s), no stray close, no unterminated comment)`, ev.length === 0, ev);
  }

  /* 5. leaked script text */
  {
    const ev = [];
    for (const t of T.texts) {
      const run = text.slice(t.start, t.end);
      if (!/[{};=]/.test(run)) continue;
      const hits = SIGNATURES.filter(([, re]) => re.test(run)).map(([name]) => name);
      if (hits.length >= 2) ev.push(`line ${line(t.start)}: visible text shows ${hits.join(' + ')}: ${snip(run)}`);
    }
    ok(page, 'no JavaScript sits in the body as visible text (outside <script>, <pre>, <code>)', ev.length === 0, ev);
  }

  /* 6. addressed ids exist somewhere */
  {
    const seen = new Set(), ev = [];
    for (const a of addrAll) {
      if (seen.has(a.id)) continue;
      seen.add(a.id);
      const found = T.staticIds.has(a.id) || rt.ids.has(a.id) || rt.prefixes.some((p) => a.id.startsWith(p));
      if (!found) ev.push(`#${a.id} - ${a.form} at line ${line(a.script.bodyStart + a.at)}, but no element carries id="${a.id}" in the markup and no script creates one`);
    }
    const total = seen.size, stat = [...seen].filter((id) => T.staticIds.has(id)).length;
    ok(page, `every id the scripts address exists: ${total} addressed, ${stat} in the static markup, ${total - stat - ev.length} created by the page's own renderers${ev.length ? `, ${ev.length} nowhere` : ''}`, ev.length === 0, ev);
  }

  /* 7. boot addresses are static and precede a classic script */
  {
    const ev = []; let boot = 0;
    for (const s of jsScripts) {
      const isModule = /^module$/i.test((s.attrs.type || '').trim());
      for (const a of bootAddresses(s.body, addressedIds(s.body))) {
        boot++;
        const at = line(s.bodyStart + a.at);
        if (!T.staticIds.has(a.id)) {
          ev.push(`#${a.id} is read at boot (line ${at}, ${a.how}) but ${rt.ids.has(a.id)
            ? `only a renderer creates it (line ${line(rt.ids.get(a.id))}) - it is null when this line runs`
            : 'nothing in the file creates it'}`);
        } else if (!isModule && T.staticIds.get(a.id) > s.at) {
          ev.push(`#${a.id} is read at boot (line ${at}, ${a.how}) by a classic script at line ${line(s.at)}, but the element is at line ${line(T.staticIds.get(a.id))}, below it - not parsed yet`);
        }
      }
    }
    ok(page, `every id read at boot (${boot} top-level, unguarded) is in the static markup and already parsed when the script runs`, ev.length === 0, ev);
  }

  /* 8. brackets balance per script */
  {
    const ev = T.scripts.map((s, k) => [s, balances[k]]).filter(([, b]) => b !== 0)
      .map(([s, b]) => `<script${s.attrs.type ? ` type="${s.attrs.type}"` : ''}> at line ${line(s.at)} ends with bracket balance ${b > 0 ? '+' : ''}${b} - a fragment, or two scripts run together`);
    ok(page, 'every inline script parses as a whole: brackets balance once strings, comments and regexes are blanked', ev.length === 0, ev);
  }
}

console.log(bad
  ? `lint_pages: ${bad} fault(s) across ${PAGES.length} page(s), ${n} checks passed`
  : `lint_pages: ${n} checks across ${PAGES.length} page(s), no faults`);
process.exit(bad ? 1 : 0);
