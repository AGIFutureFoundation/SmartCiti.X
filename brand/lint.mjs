#!/usr/bin/env node
/**
 * Brand lint. Fails on any spelling the identity forbids, anywhere it is
 * pointed.
 *
 * This exists because the drift was found by reading, not by any check — the
 * Academy app had shipped as "SmartCity.X · Trade Quest Academy" for several
 * versions while every other surface said "SmartCiti.X : Trade Craft Academy".
 * A name is a contract with the reader and nothing was verifying it.
 *
 *   node brand/lint.mjs [paths...]        default: the repo root
 *   node brand/lint.mjs --fix [paths...]  rewrite the forbidden spellings
 *
 * Exits non-zero on any violation, so it belongs in verify_all.sh.
 */
import { readdirSync, readFileSync, writeFileSync, statSync } from 'node:fs';
import { join, extname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { FORBIDDEN, NAME } from './identity.mjs';

const ROOT = fileURLToPath(new URL('..', import.meta.url));
const EXT = new Set(['.md', '.html', '.mjs', '.js', '.py', '.json', '.txt', '.sh', '.css']);
const SKIP = new Set(['node_modules', '.git', 'dist', '__pycache__', 'registry', 'ledger']);

// identity.mjs necessarily contains the forbidden strings — it is what declares
// them. A lint that flags its own rule table is a lint nobody runs.
const SELF = 'brand/lint.mjs';
const RULES_FILE = 'brand/identity.mjs';

const args = process.argv.slice(2);
const fix = args.includes('--fix');
const targets = args.filter((a) => !a.startsWith('--'));

function* walk(dir) {
  let entries;
  try { entries = readdirSync(dir, { withFileTypes: true }); } catch { return; }
  for (const e of entries) {
    if (SKIP.has(e.name)) continue;
    const p = join(dir, e.name);
    if (e.isDirectory()) yield* walk(p);
    else if (EXT.has(extname(e.name))) yield p;
  }
}

const files = [];
for (const t of (targets.length ? targets : [ROOT])) {
  const st = statSync(t);
  if (st.isDirectory()) files.push(...walk(t));
  else files.push(t);
}

const hits = [];
let fixed = 0;
for (const f of files) {
  const rel = relative(ROOT, f) || f;
  if (rel === SELF || rel === RULES_FILE) continue;
  let text;
  try { text = readFileSync(f, 'utf8'); } catch { continue; }

  // Documentation has to be able to CITE a wrong name — §22 of the spec
  // explains that the app shipped as the wrong one, and it cannot do that
  // without writing it down. A quoted literal is the form a document uses to
  // mean "this exact string", so code spans, fenced blocks and <code> elements
  // are exempt. Prose is not: the rule is about what the product is called,
  // not about what may be quoted.
  const scan = text
    .replace(/```[\s\S]*?```/g, (m) => ' '.repeat(m.length))
    .replace(/`[^`\n]*`/g, (m) => ' '.repeat(m.length))
    .replace(/<code\b[^>]*>[\s\S]*?<\/code>/gi, (m) => ' '.repeat(m.length));
  let next = text;
  for (const rule of FORBIDDEN) {
    // Word-boundary-ish: the wrong forms contain dots and spaces, so escape
    // and match literally rather than trusting \b around punctuation.
    const re = new RegExp(rule.wrong.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g');
    const found = scan.match(re);
    if (!found) continue;
    // Count the line of the first hit so the report points somewhere.
    const line = scan.slice(0, scan.indexOf(rule.wrong)).split('\n').length;
    hits.push({ file: rel, line, n: found.length, ...rule });
    if (fix) { next = next.replace(re, rule.right); fixed += found.length; }
  }
  if (fix && next !== text) writeFileSync(f, next);
}

if (!hits.length) {
  console.log(`brand: ${files.length} files clean — "${NAME.full}", ${NAME.attribution}`);
  process.exit(0);
}

if (fix) {
  console.log(`brand: rewrote ${fixed} occurrence${fixed === 1 ? '' : 's'} across `
    + `${new Set(hits.map((h) => h.file)).size} file(s).`);
  for (const h of hits) console.log(`  ${h.file}:${h.line}  ${h.wrong} -> ${h.right}  (${h.n}x)`);
  process.exit(0);
}

console.error(`brand: ${hits.length} violation${hits.length === 1 ? '' : 's'}\n`);
for (const h of hits) {
  console.error(`  ${h.file}:${h.line}`);
  console.error(`    "${h.wrong}" x${h.n} -> "${h.right}"`);
  console.error(`    ${h.why}\n`);
}
console.error('run with --fix to rewrite, or correct by hand where the context matters.');
process.exit(1);
