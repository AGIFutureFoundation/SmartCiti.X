#!/usr/bin/env node
/**
 * Loop heartbeat: a fast (< 3 s) liveness probe, run at the top of every
 * checkpoint and as often as the orchestrator likes in between.
 *
 *   node loop/heartbeat.mjs
 *
 * Appends one line to loop/state/heartbeat.jsonl: {ts, ok, checks:[{name,ok,detail,hard}]}.
 * Hard checks (a registry on the wrong pack_version, a missing tool, an
 * unreadable ledger) exit 1. Soft checks (a dirty tree, a stale cycle or eval
 * run) are warnings: printed, recorded, exit 0.
 */
import { readdirSync, readFileSync, appendFileSync, mkdirSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { ROOT, LEDGER, STATE, manifestVersion } from './cycle.mjs';

export const STALE_CYCLE_MIN = 45;   // cadence is 30 min; 15 min of grace
export const STALE_EVAL_MIN = 45;

const sh = (cmd, args) => {
  try { return execFileSync(cmd, args, { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim(); }
  catch { return null; }
};
const ageMin = (iso, now) => (now - Date.parse(iso)) / 60000;

/** Every <dir>/registry/*.json that declares pack_version, with its value. */
export function registryVersions(root = ROOT) {
  const out = [];
  for (const d of readdirSync(root, { withFileTypes: true })) {
    if (!d.isDirectory() || d.name.startsWith('.') || d.name === 'node_modules') continue;
    let files; try { files = readdirSync(join(root, d.name, 'registry')); } catch { continue; }
    for (const f of files.filter((x) => x.endsWith('.json'))) {
      let doc; try { doc = JSON.parse(readFileSync(join(root, d.name, 'registry', f), 'utf8')); } catch { continue; }
      if (doc && typeof doc === 'object' && 'pack_version' in doc)
        out.push({ file: `${d.name}/registry/${f}`, version: doc.pack_version });
    }
  }
  return out;
}

export function heartbeatLine(checks, now = new Date()) {
  return { ts: now.toISOString(), ok: checks.every((c) => c.ok || !c.hard), checks };
}

export function runHeartbeat(now = new Date()) {
  const checks = [];
  const add = (name, ok, detail, hard) => checks.push({ name, ok, detail, hard });

  const branch = sh('git', ['branch', '--show-current']);
  const dirty = sh('git', ['status', '--porcelain']);
  add('git', branch !== null,
    branch === null ? 'not a git checkout' : `${branch}, ${dirty ? dirty.split('\n').length : 0} dirty files`, true);

  let mv = null;
  try { mv = manifestVersion(); } catch { /* reported below */ }
  const regs = registryVersions();
  const off = regs.filter((r) => r.version !== mv);
  add('pack_version', mv !== null && off.length === 0,
    mv === null ? 'pack/manifest.json unreadable'
      : off.length ? `${off.length} off ${mv}: ${off.map((r) => `${r.file}=${r.version}`).join(', ')}`
        : `${regs.length} registries at ${mv}`, true);

  for (const t of ['node', 'python3', 'ffmpeg']) {
    const p = sh('which', [t]);
    add(`tool:${t}`, !!p, p || 'not found on PATH', true);
  }

  let ledger = null;
  try { ledger = JSON.parse(readFileSync(LEDGER, 'utf8')); } catch { /* hard fail below */ }
  if (!ledger) add('last_cycle', false, 'loop/registry/cycles.json unreadable', true);
  else if (!ledger.cycles.length) add('last_cycle', true, `no cycles yet (loop started ${ledger.loop.started})`, false);
  else {
    const last = ledger.cycles[ledger.cycles.length - 1];
    const a = ageMin(last.ended, now);
    add('last_cycle', a <= STALE_CYCLE_MIN, `#${last.n} ended ${a.toFixed(0)} min ago`, false);
  }

  let ev = null;
  try { ev = JSON.parse(readFileSync(join(STATE, 'evals_latest.json'), 'utf8')); } catch { /* none yet */ }
  if (!ev) add('last_eval', false, 'no eval run recorded yet', false);
  else {
    const a = ageMin(ev.ts, now);
    const fails = ev.gates.filter((g) => g.status === 'fail').map((g) => g.id);
    add('last_eval', a <= STALE_EVAL_MIN && !fails.length,
      `${a.toFixed(0)} min ago, ${fails.length ? 'failing ' + fails.join(',') : 'no failing gates'}`, false);
  }
  return heartbeatLine(checks, now);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const t0 = Date.now();
  const line = runHeartbeat();
  mkdirSync(STATE, { recursive: true });
  appendFileSync(join(STATE, 'heartbeat.jsonl'), JSON.stringify(line) + '\n');
  for (const c of line.checks) {
    const mark = c.ok ? 'ok  ' : c.hard ? 'FAIL' : 'warn';
    console.log(`${mark}  ${c.name.padEnd(14)} ${c.detail}`);
  }
  console.log(`heartbeat ${line.ok ? 'ok' : 'FAILED'} in ${Date.now() - t0} ms -> loop/state/heartbeat.jsonl`);
  process.exit(line.ok ? 0 : 1);
}
