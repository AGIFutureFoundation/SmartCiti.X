// usage: node loop/patch_cycle.mjs <n> [videoPath]
// Refresh a logged cycle's gates and check count from loop/state/evals_latest.json
// and, optionally, attach its review video (stored by bare file name; the
// media lives outside the repo).
//
// The gates are refreshed ONLY when that eval run belongs to the cycle: the
// cycle is the latest in the ledger and the eval run's ts is at or after the
// cycle's start. For any other cycle (or an older eval run) the cycle keeps
// the gates it recorded and only the video is attached, so patching an old
// cycle can never stamp it with a later run's results.
//
// The whole ledger is validated before writing, and the write is atomic (a
// temp file in the ledger's directory, then rename); on any error nothing is
// written and the exit code is 1.
//
// LOOP_LEDGER and LOOP_STATE override the ledger path and the state directory
// (used by loop/test.mjs with temp fixtures; never needed in normal use).
import { readFileSync, writeFileSync, renameSync, unlinkSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join, dirname, basename } from 'node:path';
import { LEDGER as DEFAULT_LEDGER, STATE as DEFAULT_STATE, validateLedger, manifestVersion } from './cycle.mjs';

const LEDGER = process.env.LOOP_LEDGER || DEFAULT_LEDGER;
const STATE = process.env.LOOP_STATE || DEFAULT_STATE;

const die = (m) => { console.error(m); process.exit(1); };
const [n, video] = process.argv.slice(2);
if (!/^\d+$/.test(n ?? '')) die('usage: node loop/patch_cycle.mjs <n> [videoPath]');

const led = JSON.parse(readFileSync(LEDGER, 'utf8'));
const c = led.cycles.find((x) => x.n === Number(n));
if (!c) die(`cycle ${n} is not in the ledger (${led.cycles.length} cycles logged); nothing written`);
const latest = led.cycles[led.cycles.length - 1] === c;

let ev = null;
try { ev = JSON.parse(readFileSync(join(STATE, 'evals_latest.json'), 'utf8')); } catch { ev = null; }

const evTs = ev && Date.parse(ev.ts);
const belongs = latest && ev && Array.isArray(ev.gates) && Number.isFinite(evTs) && evTs >= Date.parse(c.started);
let gatesNote;
if (belongs) {
  c.gates = ev.gates.map((g) => ({ id: g.id, name: g.name, status: g.status, detail: g.detail, ms: g.ms ?? 0 }));
  const m = ((ev.gates.find((g) => g.id === 'EV-01') || {}).detail || '').match(/^(\d+) checks/);
  if (m) c.checks_total = Number(m[1]);
  gatesNote = `refreshed from the eval run at ${ev.ts}`;
} else {
  const why = !ev ? 'loop/state/evals_latest.json is missing or unreadable'
    : !latest ? `cycle ${n} is not the latest cycle in the ledger`
      : `the eval run at ${ev.ts} predates cycle ${n} (started ${c.started})`;
  if (!video) die(`${why}; the cycle keeps its recorded gates and no video was given, so nothing written`);
  gatesNote = `kept as recorded (${why})`;
}

if (video) {
  let d = NaN;
  try {
    d = Number.parseFloat(execFileSync('ffprobe',
      ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', video], { encoding: 'utf8' }));
  } catch (e) { die(`ffprobe failed on ${video}: ${e.message.split('\n')[0]}; nothing written`); }
  if (!(Number.isFinite(d) && d > 0)) die(`ffprobe gave no usable duration for ${video}; nothing written`);
  c.video = { path: video.split(/[\\/]/).pop(), duration_s: Number(d.toFixed(3)) };
}

const errs = validateLedger(led, manifestVersion());
if (errs.length) die(`ledger would be invalid, nothing written:\n  ${errs.join('\n  ')}`);

// Atomic: write a sibling temp file, then rename over the ledger.
const tmp = join(dirname(LEDGER), `.${basename(LEDGER)}.${process.pid}.tmp`);
try {
  writeFileSync(tmp, JSON.stringify(led, null, 2) + '\n');
  renameSync(tmp, LEDGER);
} catch (e) {
  try { unlinkSync(tmp); } catch { /* already gone */ }
  die(`could not write ${LEDGER}: ${e.message}; ledger unchanged`);
}
console.log('cycle', n, 'gates', gatesNote + ':', c.gates.map((g) => g.id + ':' + g.status).join(' '),
  'checks', c.checks_total, 'video', c.video && c.video.duration_s);
