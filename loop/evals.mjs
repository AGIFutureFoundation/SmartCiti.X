#!/usr/bin/env node
/**
 * Loop eval gates EV-01 .. EV-09 — executed, not described.
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
import { claimHits, VOCAB } from './honesty.mjs';

/* ------------------------------------------------------- pure functions --- */

// The claim vocabulary and the scanner live in loop/honesty.json and
// loop/honesty.mjs, shared with courses/test.mjs and courses/build.py.
export const OVERCLAIM = new RegExp(VOCAB.claims.join('|'), 'i');
export const SECRET = /\bghp_[A-Za-z0-9]{20,}|\bsk-[A-Za-z0-9_-]{20,}|\bAKIA[0-9A-Z]{16}\b|-----BEGIN [A-Z ]*-----/;

/** Overclaiming clauses in a text, with line numbers (see loop/honesty.mjs). */
export const honestyHits = claimHits;

/** A text that says a pilot runs with real learners. */
export const PILOT_TALK = /pilot.*(learner|student|cohort)/i;
const isStr = (x) => typeof x === 'string' && x.trim().length > 0;
/** A pilot record that may stand behind real learners: partner and consent plan both named. */
export const pilotRecorded = (c) => !!(c && c.pilot && c.pilot.real_learners === true
  && isStr(c.pilot.partner) && isStr(c.pilot.consent_plan_ref));

/** EV-09 over a ledger's cycles: [status, detail]. */
export function pilotGate(cycles) {
  const bad = [];
  let recorded = 0;
  for (const c of cycles) {
    if (c.pilot && c.pilot.real_learners === true && !pilotRecorded(c))
      bad.push(`cycle #${c.n} records real learners without a partner and consent_plan_ref`);
    if (pilotRecorded(c)) recorded++;
    const said = [...(c.shipped || []), ...[c.notes].flat().filter((x) => typeof x === 'string')]
      .find((t) => PILOT_TALK.test(t));
    if (said && !pilotRecorded(c)) bad.push(`cycle #${c.n} mentions a pilot with learners without a pilot record: "${said.slice(0, 60)}"`);
  }
  if (bad.length) return ['fail', bad.slice(0, 3).join('; ')];
  return ['pass', recorded ? `${recorded} pilot(s) recorded with partner and consent plan` : 'no pilot recorded'];
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
  ['EV-09', 'Pilot precondition'],
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
const SELF = new Set(['loop/evals.mjs', 'loop/test.mjs', 'loop/honesty.mjs', 'loop/honesty.json',
  'loop/registry/honesty_fixtures.json']);

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
  // The ledger is committed; the media is not (each review is ~6 MB and lives
  // outside the repo). A ledger path must be a bare file name resolved against
  // LOOP_MEDIA_DIR or loop/media/, never a machine's absolute path.
  if (isAbsolute(last.video.path) || /[\/\\]/.test(last.video.path))
    return ['fail', `cycle #${last.n} video path must be a bare file name, got ${last.video.path}`];
  const dir = process.env.LOOP_MEDIA_DIR || join(ROOT, 'loop', 'media');
  const p = join(dir, last.video.path);
  const rec = last.video.duration_s;
  // A duration off 120 +/- 0.5 s is a product-review WARN, not a release stop;
  // only a machine path in the ledger (above) or an unreadable file fails.
  const off = (d) => (Math.abs(d - 120) <= 0.5 ? '' : `, outside 120 ± 0.5 s`);
  if (!existsSync(p)) {
    return ['warn', `cycle #${last.n} recorded ${rec} s${off(rec)}; ${last.video.path} is not on this machine, so the duration was not re-measured`];
  }
  const r = spawnSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p], { encoding: 'utf8' });
  const d = Number.parseFloat(r.stdout);
  if (!Number.isFinite(d)) return ['fail', `ffprobe could not read ${last.video.path}`];
  return [off(d) ? 'warn' : 'pass', `cycle #${last.n} ${last.video.path} ${d.toFixed(2)} s${off(d)}`];
}

function ev09() {
  let L; try { L = JSON.parse(readFileSync(LEDGER, 'utf8')); } catch { return ['fail', 'ledger unreadable']; }
  return pilotGate(L.cycles || []);
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
  'EV-04': () => lint('brand/figures.mjs'), 'EV-05': ev05, 'EV-06': ev06, 'EV-07': ev07, 'EV-08': ev08, 'EV-09': ev09 };

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
