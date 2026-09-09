#!/usr/bin/env node
/**
 * Figures lint: every surface must state the same numbers as the pack.
 *
 * This exists because the surfaces DID disagree and nothing noticed. The
 * Academy app said 111 halls and 500,000 modules; the landing page, spec and
 * registry said 33 and 333,333. Both were internally consistent, both were
 * published, and the only reason it surfaced is that someone read them side by
 * side.
 *
 * A number a reader can check is a claim, and claims need a checker — the same
 * argument as the brand lint, applied to figures instead of spelling. The
 * canonical values come from the pack manifest, which is itself verified
 * against the generated ID space, so this cannot drift from the truth without
 * the pack failing first.
 *
 *   node brand/figures.mjs [paths...]
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, extname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = fileURLToPath(new URL('..', import.meta.url));
const manifest = JSON.parse(readFileSync(join(ROOT, 'pack/manifest.json'), 'utf8'));
const L = manifest.ledger;

const F = (n) => n.toLocaleString('en-US');

/**
 * Figures that are wrong ANYWHERE, with the value that replaces them. These
 * are superseded scales, not arbitrary numbers: a page may legitimately say
 * "33 lessons in this level", so only the specific claims are policed.
 */
const RULES = [
  { wrong: /\b333,333\b/g, right: F(L.total_modules),
    why: 'the 33-hall module total; the pack now closes at ' + F(L.total_modules) },
  { wrong: /\b500,000 modules\b/g, right: F(L.total_modules) + ' modules',
    why: 'the figure the Academy app carried, which matched no pack' },
  { wrong: /\b35,937\b/g, right: F(L.core_lessons),
    why: 'the 33-hall lesson count' },
  { wrong: /\b36,237\b/g, right: F(manifest.authored_objects),
    why: 'the 33-hall authored-object count' },
  { wrong: /\b33 (?:trade )?unions?\b/g, right: `${L.halls} trade unions`,
    why: `the network is ${L.halls} halls` },
  { wrong: /\b33 union halls\b/g, right: `${L.halls} union halls`,
    why: `the network is ${L.halls} halls` },
  // Added after "the 33 halls are grouped" survived in the map footer: the
  // rules above policed "33 unions" and "33 union halls" but not the bare
  // "33 halls". A lint's coverage is only the phrasings someone thought of,
  // so a miss is a rule to add, not a reason to trust the pass.
  { wrong: /\b33 halls\b/g, right: `${L.halls} halls`,
    why: `the network is ${L.halls} halls` },
];

const EXT = new Set(['.md', '.html', '.mjs', '.js', '.py', '.json', '.txt', '.sh']);
// `archive/` holds superseded working files kept for provenance; `pack/` is
// the frozen 33-hall pack, which correctly states its own figures.
const SKIP = new Set(['node_modules', '.git', 'dist', '__pycache__', 'registry',
                      'ledger', 'pack', 'archive']);
const SELF = new Set(['brand/figures.mjs']);

function* walk(dir) {
  let e; try { e = readdirSync(dir, { withFileTypes: true }); } catch { return; }
  for (const x of e) {
    if (SKIP.has(x.name)) continue;
    const p = join(dir, x.name);
    if (x.isDirectory()) yield* walk(p);
    else if (EXT.has(extname(x.name))) yield p;
  }
}

const args = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const files = [];
for (const t of (args.length ? args : [ROOT])) {
  const st = statSync(t);
  if (st.isDirectory()) files.push(...walk(t)); else files.push(t);
}

const hits = [];
for (const f of files) {
  const rel = relative(ROOT, f) || f;
  if (SELF.has(rel)) continue;
  let text; try { text = readFileSync(f, 'utf8'); } catch { continue; }
  // Same exemption as the brand lint: a quoted literal or fenced block may
  // cite a superseded figure, because the migration notes have to name it.
  const scan = text
    .replace(/```[\s\S]*?```/g, (m) => ' '.repeat(m.length))
    .replace(/`[^`\n]*`/g, (m) => ' '.repeat(m.length))
    .replace(/<code\b[^>]*>[\s\S]*?<\/code>/gi, (m) => ' '.repeat(m.length));
  for (const r of RULES) {
    const found = scan.match(r.wrong);
    if (found) hits.push({ file: rel, n: found.length, ...r });
  }
}

if (!hits.length) {
  console.log(`figures: ${files.length} files agree with the pack — `
    + `${L.halls} halls, ${F(L.total_modules)} modules`);
  process.exit(0);
}
console.error(`figures: ${hits.length} stale figure${hits.length === 1 ? '' : 's'}\n`);
for (const h of hits) {
  console.error(`  ${h.file}`);
  console.error(`    ${h.wrong.source} x${h.n} -> ${h.right}`);
  console.error(`    ${h.why}\n`);
}
console.error('surfaces must state the pack\'s figures; cite a superseded one in backticks.');
process.exit(1);
