// web/test_evalparts.mjs - node checks (no browser) for the --part=<k> split of web/eval_parishes.mjs and web/eval_bayworld.mjs.
// A full eval run takes longer than one <= 90 s browser run, so each eval can run as two parts. These checks hold that:
//   [default]  no --part runs every part (the full run stays the default); any other --part value stops the run;
//   [blocks]   the rows sit in two marked blocks, in order, and every row-producing line between the page load and the report
//              (fail(...), bad++, rows.push / perfRows.push) is inside one of them - nothing runs in neither part;
//   [verbatim] the row code inside the blocks never reads PART / RUN_PART (rows and targets do not depend on the split);
//   [union]    the rows the part blocks return are disjoint and their union is every block-made row the report prints;
//   [report]   a report line that prints a row a part may skip is guarded by that part, so a split run never prints it as ok.
// Prints "  ok <name>" per check, "FAIL <name>" at column 0, exits non-zero on any failure.
//   node web/test_evalparts.mjs [--dir=<copy of web/>]      (--dir: mutation runs on a broken copy)
import { readFileSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const dirArg = process.argv.find((a) => a.startsWith('--dir='));
const DIR = resolve(dirArg ? dirArg.slice(6) : HERE);
let fails = 0;
const check = (name, cond, info) => { if (cond) console.log('  ok ' + name); else { fails++; console.log('FAIL ' + name + (info !== undefined ? ' - ' + JSON.stringify(info) : '')); } };

// the report's code with string text blanked: '...' strings and the static text of `...` templates go, ${...} code stays
function codeOnly(t) {
  let out = '', i = 0; const stack = [];   // stack of 'tpl' (inside a template's static text) / brace depths
  while (i < t.length) {
    const c = t[i], top = stack[stack.length - 1];
    if (top === 'tpl') {
      if (c === '\\') { i += 2; continue; }
      if (c === '`') { stack.pop(); out += ' '; i++; continue; }
      if (c === '$' && t[i + 1] === '{') { stack.push(0); out += ' '; i += 2; continue; }
      out += c === '\n' ? '\n' : ' '; i++; continue;
    }
    if (c === "'" || c === '"') { const q = c; i++; while (i < t.length && t[i] !== q) i += t[i] === '\\' ? 2 : 1; i++; out += ' '; continue; }
    if (c === '`') { stack.push('tpl'); out += ' '; i++; continue; }
    if (typeof top === 'number') { if (c === '{') stack[stack.length - 1]++; else if (c === '}') { if (top === 0) { stack.pop(); out += ' '; i++; continue; } stack[stack.length - 1]--; } }
    out += c; i++;
  }
  return out;
}
const ROW_LINE = /\bfail\(|\bbad\+\+|\brows\.push\(|\bperfRows\.push\(/;
for (const [name, file, outside, nParts] of [
  ['eval_parishes', 'eval_parishes.mjs', [], 3],
  ['eval_bayworld', 'eval_bayworld.mjs', [/^const errRow = /, /^if \(errors\.length\) \{ fail\(errRow/], 2],   // the page-errors row judges whatever ran
]) {
  const L = readFileSync(join(DIR, file), 'utf8').split('\n');
  const at = (re, from = 0) => { for (let i = from; i < L.length; i++) if (re.test(L[i])) return i; return -1; };
  const K = Array.from({ length: nParts }, (_, k) => String(k + 1));
  // [default]
  check(`[default] ${name}: no --part runs all ${nParts} parts; --part=1..${nParts} runs one; anything else stops`,
    L.includes("const PART = partArg ? partArg.slice(7) : null;") && L.some((l) => l.startsWith(`const PARTS = [${K.map((k) => `'${k}'`).join(', ')}];`))
    && L.includes("const RUN_PART = Object.fromEntries(PARTS.map((k) => [k, PART === null || PART === k]));")
    && L.some((l) => l.startsWith('if (PART !== null && !PARTS.includes(PART)) {') && /process\.exit\(2\)/.test(l)));
  // [blocks]: part k = `const PARTk = RUN_PART[k] ? await (async () => {` ... `return {...};` `})() : {};`, in order, between the markers
  const b = at(/^\/\* EVAL_PARTS:BEGIN part 1/), e = at(/^\/\* EVAL_PARTS:END \*\/$/), ready = at(/^const fail = \(row, msg\) =>/);
  const blk = []; let from = b, okShape = b >= 0 && e > b && ready >= 0 && ready < b;
  for (const k of K) {
    if (k !== '1') { const mk = at(new RegExp(`^/\\* EVAL_PARTS part ${k} \\*/$`), from); okShape = okShape && mk >= 0; from = mk; }
    const o = at(new RegExp(`^const PART${k} = RUN_PART\\[${k}\\] \\? await \\(async \\(\\) => \\{$`), from), r = at(/^return \{.*\};$/, o);
    okShape = okShape && o >= 0 && r > o && L[r + 1] === '})() : {};' && (blk.length === 0 || o > blk[blk.length - 1].r);
    blk.push({ k, o, r }); from = r + 1;
  }
  const report = at(/^await browser\.close\(\);$/, e);
  okShape = okShape && blk[blk.length - 1].r < e && report > e && !L.some((l) => new RegExp(`^const PART${nParts + 1} = `).test(l))
    && L.filter((l) => /^\/\* EVAL_PARTS:BEGIN/.test(l)).length === 1 && L.filter((l) => /^\/\* EVAL_PARTS:END/.test(l)).length === 1;
  check(`[blocks] ${name}: ${nParts} part blocks in order 1..${nParts}, each an async block that returns its rows`, okShape, blk);
  if (!okShape) continue;
  const inBlock = (i) => blk.some(({ o, r }) => i > o && i < r);
  const loose = [];
  for (let i = ready + 1; i < report; i++) if (!inBlock(i) && ROW_LINE.test(L[i]) && !outside.some((re) => re.test(L[i]))) loose.push(i + 1);
  check(`[blocks] ${name}: every row-producing line between the page load and the report is inside a part`, loose.length === 0, loose);
  const bodies = blk.map(({ o, r }) => L.slice(o + 1, r));
  // [verbatim]
  const leak = bodies.flat().map((l, k) => [k, l]).filter(([, l]) => /\bRUN_PARTS?\b|\bPARTS?\b/.test(l)).map(([k]) => k);
  check(`[verbatim] ${name}: the row code in the blocks never reads PART, PARTS or RUN_PART`, leak.length === 0, leak);
  // [union]
  const decl = (body) => new Set(body.flatMap((l) => { const mm = l.match(/^const (?:\{ ([^}]*) \}|([A-Za-z_$][\w$]*)) =/); return mm ? (mm[1] ? mm[1].split(',').map((x) => x.trim()) : [mm[2]]) : []; }));
  const ret = (i) => (L[i].match(/^return \{(.*)\};$/)[1].split(',').map((x) => x.trim()).filter(Boolean));
  const rep = codeOnly(L.slice(report).join('\n')), used = (n) => new RegExp(`(?<![\\w$.])${n.replace('$', '\\$')}(?![\\w$]|\\s*:(?!:))`).test(rep);   // code only; an object key (fleet: ...) is not a use
  const same = (a, x) => a.length === x.length && a.every((v) => x.includes(v));
  const D = bodies.map(decl), R = blk.map(({ r }) => ret(r)), W = D.map((d) => [...d].filter(used));
  const all = R.flat();
  check(`[union] ${name}: each part returns exactly its rows the report prints (${R.map((x) => x.length).join(' + ')}), no row in two parts`,
    R.every((x, k) => same(x, W[k]) && x.every((n) => D[k].has(n))) && new Set(all).size === all.length, { R, W });
  const zone = L.slice(blk[0].r, e + 1).join('\n');
  const destr = (k) => { const mm = zone.match(new RegExp(`const \\{ ([^}]*(?:\\{\\}[^}]*)*) \\} = PART${k};`)); return mm ? mm[1].split(/,\s*(?![^{]*\})/).map((x) => x.split('=')[0].trim()) : null; };
  const Dx = K.map((k, i) => (R[i].length ? destr(k) : []));
  check(`[union] ${name}: the full run sees every returned row (each one destructured from its part, under its own name)`, Dx.every((d, i) => d && same(d, R[i])), Dx);
  // [report]
  const unguarded = [];
  R.forEach((names, i) => { const k = K[i]; for (const n of names) {
    if (!new RegExp(`\\b${n} = null\\b`).test(zone)) continue;
    for (const l of L.slice(report)) if (new RegExp(`(?<![\\w$.'])${n}(?![\\w$:])`).test(l) && !/^const out = /.test(l) && !l.includes(`if (RUN_PART[${k}])`)) unguarded.push(`${n}: ${l.trim().slice(0, 60)}`);
  } });
  check(`[report] ${name}: every report line that prints a row one part may skip is guarded by that part`, unguarded.length === 0, unguarded);
}
if (fails) { console.log(`FAIL test_evalparts: ${fails} failed`); process.exit(1); }
console.log('test_evalparts: all checks ok');
