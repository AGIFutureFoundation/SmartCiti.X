#!/usr/bin/env node
/**
 * Loop eval gates EV-01 .. EV-08 — executed, not described.
 *
 *   node loop/evals.mjs
 *
 * Writes loop/state/evals_latest.json {ts, gates:[{id,name,status,detail,ms}]},
 * appends the same object to loop/state/evals.jsonl, prints a table, and exits
 * 1 if any gate fails. "absent" means the thing a gate checks does not exist
 * yet (no courses suite, no review video); it is recorded, never counted as a
 * pass. A gate failure stops the release: loop/cycle.mjs refuses to record a
 * commit for a cycle whose gates include a failure.
 */
import { readFileSync, writeFileSync, appendFileSync, mkdirSync, existsSync, statSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { join, extname, isAbsolute } from 'node:path';
import { pathToFileURL } from 'node:url';
import { ROOT, LEDGER, STATE, validateLedger, manifestVersion } from './cycle.mjs';

/* ------------------------------------------------------- pure functions --- */

// Phrases that claim a relationship or a deployment the project does not have.
export const OVERCLAIM = /\b(?:accredited|endorsed|certified by|partnered with|deployed to|in production at)\b/i;
// A sentence that also says no/not/none/never/zero/planned/proposed (or
// nothing / n't) is a disclaimer, not a claim.
export const NEGATION = /\b(?:no|not|none|never|nothing|zero|planned|proposed)\b|n't\b/i;
export const SECRET = /\bghp_[A-Za-z0-9]{20,}|\bsk-[A-Za-z0-9_-]{20,}|\bAKIA[0-9A-Z]{16}\b|-----BEGIN [A-Z ]*-----/;

/** Strip code spans and fenced blocks: quoting a phrase is not claiming it. */
const unquote = (t) => t.replace(/```[\s\S]*?```/g, ' ').replace(/`[^`\n]*`/g, ' ');

/** Overclaiming sentences in a text, with line numbers. */
export function honestyHits(text) {
  const hits = [];
  unquote(text).split('\n').forEach((line, i) => {
    for (const s of line.split(/(?<=[.!?])\s+/)) {
      if (NEGATION.test(s)) continue;
      // A phrase inside a regex alternation (`accredited|endorsed`) is a lint's
      // rule table naming what it hunts, not a claim; anything else counts.
      const claims = [...s.matchAll(new RegExp(OVERCLAIM.source, 'gi'))].filter((m) =>
        s[m.index - 1] !== '|' && s[m.index + m[0].length] !== '|');
      if (claims.length) hits.push({ line: i + 1, text: s.trim().slice(0, 120) });
    }
  });
  return hits;
}

/** Lines that look like credentials. */
export function secretHits(text) {
  const hits = [];
  text.split('\n').forEach((line, i) => { if (SECRET.test(line)) hits.push({ line: i + 1 }); });
  return hits;
}

/** Parse verify_all.sh's closing line: "<n> checks, <m> failing suites". */
export function parseVerify(out) {
  // stderr is appended after stdout, so the summary is the last such line, not the last line.
  const all = [...out.matchAll(/^(\d+) checks, (\d+) failing suites\s*$/gm)];
  const m = all[all.length - 1];
  const failed = out.split('\n').filter((l) => /^(FAIL|DRIFT)\s/.test(l)).map((l) => l.trim().split(/\s+/)[1]);
  return m ? { total: Number(m[1]), failing: Number(m[2]), failed } : null;
}

export const GATES = Object.freeze([
  ['EV-01', 'Verification suite (verify_all.sh)'],
  ['EV-02', 'Courses suite'],
  ['EV-03', 'Brand lint'],
  ['EV-04', 'Figures lint'],
  ['EV-05', 'Honesty lint on branch changes'],
  ['EV-06', 'Review video 120 ± 0.5 s'],
  ['EV-07', 'Cycle ledger schema'],
  ['EV-08', 'No secrets in diff'],
]);

/* -------------------------------------------------------------- runners --- */

const run = (cmd, args, timeout = 300000) => {
  const r = spawnSync(cmd, args, { cwd: ROOT, encoding: 'utf8', timeout, maxBuffer: 64 << 20 });
  return { rc: r.status ?? 1, out: (r.stdout || '') + (r.stderr || '') };
};
const tail = (s, n = 1) => s.trim().split('\n').slice(-n).join(' | ').slice(0, 200);

const TEXT = new Set(['.md', '.html', '.mjs', '.js', '.py', '.json', '.txt', '.sh', '.css', '.yml', '.yaml', '.csv']);
// The gate's own rule table names the phrases it hunts, and its test suite
// must contain overclaiming fixtures to prove the gate catches them;
// loop/state holds its own output. None of these is a claim about the project.
const SELF = new Set(['loop/evals.mjs', 'loop/test.mjs']);

/** Files changed on this branch vs origin/main, plus uncommitted and untracked. */
export function changedFiles() {
  const lists = [
    run('git', ['diff', '--name-only', 'origin/main...HEAD']).out,
    run('git', ['diff', '--name-only', 'HEAD']).out,
    run('git', ['ls-files', '--others', '--exclude-standard']).out,
  ];
  return [...new Set(lists.join('\n').split('\n').map((s) => s.trim()).filter(Boolean))]
    .filter((f) => !f.startsWith('loop/state/') && !SELF.has(f))
    .filter((f) => existsSync(join(ROOT, f)) && statSync(join(ROOT, f)).isFile());
}

function ev01() {
  const r = run('bash', ['./verify_all.sh'], 600000);
  const p = parseVerify(r.out);
  if (!p) return ['fail', `no summary line; rc ${r.rc}: ${tail(r.out)}`];
  const d = `${p.total} checks, ${p.failing} failing suites${p.failed.length ? ': ' + p.failed.join(', ') : ''}`;
  return [r.rc === 0 && p.failing === 0 ? 'pass' : 'fail', d];
}

function ev02() {
  if (!existsSync(join(ROOT, 'courses/test.mjs'))) return ['absent', 'courses/test.mjs does not exist yet'];
  const r = run('node', ['courses/test.mjs']);
  const n = (r.out.match(/^ {2}ok /gm) || []).length;
  return [r.rc === 0 ? 'pass' : 'fail', `${n} checks${r.rc ? ', rc ' + r.rc + ': ' + tail(r.out) : ''}`];
}

function lint(script) {
  const r = run('node', [script, '.']);
  return [r.rc === 0 ? 'pass' : 'fail', tail(r.out, r.rc ? 3 : 1) || `rc ${r.rc}`];
}

function ev05() {
  const files = changedFiles().filter((f) => TEXT.has(extname(f)));
  const hits = [];
  for (const f of files) {
    for (const h of honestyHits(readFileSync(join(ROOT, f), 'utf8'))) hits.push(`${f}:${h.line} "${h.text}"`);
  }
  return hits.length ? ['fail', `${hits.length} overclaim(s): ${hits.slice(0, 3).join('; ')}`]
    : ['pass', `${files.length} changed text files, 0 overclaims`];
}

function ev06() {
  let L; try { L = JSON.parse(readFileSync(LEDGER, 'utf8')); } catch { return ['fail', 'ledger unreadable']; }
  const last = L.cycles[L.cycles.length - 1];
  if (!last) return ['absent', 'no cycles logged yet'];
  if (!last.video) return ['absent', `cycle #${last.n} has no review video recorded`];
  const p = isAbsolute(last.video.path) ? last.video.path : join(ROOT, last.video.path);
  if (!existsSync(p)) return ['fail', `cycle #${last.n} video missing on disk: ${last.video.path}`];
  const r = spawnSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p], { encoding: 'utf8' });
  const d = Number.parseFloat(r.stdout);
  if (!Number.isFinite(d)) return ['fail', `ffprobe could not read ${last.video.path}`];
  return [Math.abs(d - 120) <= 0.5 ? 'pass' : 'fail', `cycle #${last.n} ${last.video.path} ${d.toFixed(2)} s`];
}

function ev07() {
  let L; try { L = JSON.parse(readFileSync(LEDGER, 'utf8')); } catch (e) { return ['fail', `unreadable: ${e.message}`]; }
  const errs = validateLedger(L, manifestVersion());
  return errs.length ? ['fail', errs.slice(0, 3).join('; ')] : ['pass', `valid, ${L.cycles.length} cycles`];
}

function ev08() {
  const hits = [];
  const diff = run('git', ['diff', 'origin/main...HEAD']).out + '\n' + run('git', ['diff', 'HEAD']).out;
  const added = diff.split('\n').filter((l) => l.startsWith('+') && !l.startsWith('+++')).join('\n');
  if (secretHits(added).length) hits.push(`${secretHits(added).length} in committed/staged diff`);
  const untracked = run('git', ['ls-files', '--others', '--exclude-standard']).out.split('\n').filter(Boolean);
  for (const f of untracked) {
    if (f.startsWith('loop/state/')) continue;
    let t; try { t = readFileSync(join(ROOT, f), 'utf8'); } catch { continue; }
    const h = secretHits(t);
    if (h.length) hits.push(`${f}:${h[0].line}`);
  }
  return hits.length ? ['fail', `possible secret: ${hits.slice(0, 3).join(', ')}`]
    : ['pass', `diff + ${untracked.length} untracked files clean`];
}

const RUNNERS = { 'EV-01': ev01, 'EV-02': ev02, 'EV-03': () => lint('brand/lint.mjs'),
  'EV-04': () => lint('brand/figures.mjs'), 'EV-05': ev05, 'EV-06': ev06, 'EV-07': ev07, 'EV-08': ev08 };

export function runGates(only) {
  const gates = [];
  for (const [id, name] of GATES) {
    if (only && !only.includes(id)) continue;
    const t0 = Date.now();
    let status, detail;
    try { [status, detail] = RUNNERS[id](); } catch (e) { status = 'fail'; detail = `gate crashed: ${e.message}`; }
    gates.push({ id, name, status, detail, ms: Date.now() - t0 });
  }
  return { ts: new Date().toISOString(), gates };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const res = runGates();
  mkdirSync(STATE, { recursive: true });
  writeFileSync(join(STATE, 'evals_latest.json'), JSON.stringify(res, null, 2) + '\n');
  appendFileSync(join(STATE, 'evals.jsonl'), JSON.stringify(res) + '\n');
  for (const g of res.gates) {
    console.log(`${g.id}  ${g.status.toUpperCase().padEnd(6)} ${String(g.ms).padStart(6)} ms  ${g.name.padEnd(36)} ${g.detail}`);
  }
  const failed = res.gates.filter((g) => g.status === 'fail');
  console.log(failed.length ? `RELEASE BLOCKED: ${failed.map((g) => g.id).join(', ')} failing`
    : 'all gates pass or absent -> loop/state/evals_latest.json');
  process.exit(failed.length ? 1 : 0);
}
