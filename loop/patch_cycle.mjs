// usage: node loop/patch_cycle.mjs <n> [videoPath]
// Refresh a logged cycle's gates and check count from loop/state/evals_latest.json
// and, optionally, attach its review video (stored by bare file name; the
// media lives outside the repo). The whole ledger is validated before writing;
// on any error nothing is written and the exit code is 1.
import { readFileSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';
import { LEDGER, STATE, validateLedger, manifestVersion } from './cycle.mjs';

const die = (m) => { console.error(m); process.exit(1); };
const [n, video] = process.argv.slice(2);
if (!/^\d+$/.test(n ?? '')) die('usage: node loop/patch_cycle.mjs <n> [videoPath]');

const led = JSON.parse(readFileSync(LEDGER, 'utf8'));
const c = led.cycles.find((x) => x.n === Number(n));
if (!c) die(`cycle ${n} is not in the ledger (${led.cycles.length} cycles logged); nothing written`);

let ev;
try { ev = JSON.parse(readFileSync(join(STATE, 'evals_latest.json'), 'utf8')); }
catch { die('loop/state/evals_latest.json is missing or unreadable; run node loop/evals.mjs first'); }
c.gates = ev.gates.map((g) => ({ id: g.id, name: g.name, status: g.status, detail: g.detail, ms: g.ms ?? 0 }));
const m = ((ev.gates.find((g) => g.id === 'EV-01') || {}).detail || '').match(/^(\d+) checks/);
if (m) c.checks_total = Number(m[1]);

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
writeFileSync(LEDGER, JSON.stringify(led, null, 2) + '\n');
console.log('cycle', n, 'gates', c.gates.map((g) => g.id + ':' + g.status).join(' '),
  'checks', c.checks_total, 'video', c.video && c.video.duration_s);
