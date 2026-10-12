#!/usr/bin/env node
/**
 * The cycle ledger: what each 30-minute checkpoint of the agent loop actually
 * ran and shipped.
 *
 *   node loop/cycle.mjs add --json <file> [--ledger <path>]
 *   node loop/cycle.mjs show [--ledger <path>]
 *
 * `add` fills the gates from loop/state/evals_latest.json, the check count
 * from its EV-01 gate and heartbeat_ok from the last heartbeat line when the
 * input leaves them out, then validates the whole ledger before writing. A
 * malformed cycle is refused and the ledger is left untouched.
 *
 * The rule that makes this a release gate and not a diary: a cycle whose
 * gates include a failure cannot record a commit. A gate failure stops the
 * release; the cycle is still logged, with what it found.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { join } from 'node:path';

export const ROOT = fileURLToPath(new URL('..', import.meta.url));
export const LEDGER = join(ROOT, 'loop/registry/cycles.json');
export const STATE = join(ROOT, 'loop/state');
export const AGENTS = Object.freeze([
  'Orchestrator', 'Curriculum Mapper', 'Environment Architect', 'Robotics Integrator',
  'Licensing Researcher', 'Billing Engineer', 'Eval Warden', 'Media Producer',
]);
export const GATE_IDS = Object.freeze(['EV-01', 'EV-02', 'EV-03', 'EV-04', 'EV-05', 'EV-06', 'EV-07', 'EV-08']);
export const STATUSES = Object.freeze(['pass', 'fail', 'warn', 'absent']);

const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?Z$/;
const isStr = (s) => typeof s === 'string' && s.trim().length > 0;
const isObj = (o) => o !== null && typeof o === 'object' && !Array.isArray(o);

/** Errors for one cycle; empty array means valid. `expectN` is its required position. */
export function validateCycle(c, expectN) {
  const e = [];
  if (!isObj(c)) return ['cycle is not an object'];
  const allowed = new Set(['n', 'started', 'ended', 'sprint', 'shipped', 'agents', 'gates',
    'heartbeat_ok', 'checks_total', 'video', 'commit', 'notes']);
  for (const k of Object.keys(c)) if (!allowed.has(k)) e.push(`unknown field "${k}"`);
  if (!Number.isInteger(c.n) || c.n < 1) e.push('n must be a positive integer');
  else if (expectN !== undefined && c.n !== expectN) e.push(`n is ${c.n}, the ledger expects ${expectN}`);
  for (const k of ['started', 'ended']) if (!ISO.test(c[k] ?? '')) e.push(`${k} must be an ISO-8601 UTC timestamp`);
  if (ISO.test(c.started ?? '') && ISO.test(c.ended ?? '') && Date.parse(c.ended) < Date.parse(c.started))
    e.push('ended is before started');
  if (!isStr(c.sprint)) e.push('sprint must be a non-empty string');
  if (!Array.isArray(c.shipped) || !c.shipped.every(isStr)) e.push('shipped must be an array of non-empty strings');
  if (!Array.isArray(c.agents) || !c.agents.length) e.push('agents must be a non-empty array');
  else c.agents.forEach((a, i) => {
    if (!isObj(a)) { e.push(`agents[${i}] is not an object`); return; }
    if (!AGENTS.includes(a.name)) e.push(`agents[${i}].name "${a.name}" is not one of the eight team agents`);
    if (!isStr(a.task)) e.push(`agents[${i}].task must be a non-empty string`);
    if (!isStr(a.result)) e.push(`agents[${i}].result must be a non-empty string`);
  });
  if (!Array.isArray(c.gates)) e.push('gates must be an array (copied from evals_latest.json)');
  else {
    const ids = c.gates.map((g) => g && g.id).join();
    if (ids !== GATE_IDS.join()) e.push(`gates must be exactly ${GATE_IDS.join(',')} in order, got ${ids || 'none'}`);
    c.gates.forEach((g, i) => {
      if (!isObj(g)) return;
      if (!STATUSES.includes(g.status)) e.push(`gates[${i}].status "${g.status}" is not pass|fail|warn|absent`);
      if (!isStr(g.name)) e.push(`gates[${i}].name missing`);
      if (typeof g.detail !== 'string') e.push(`gates[${i}].detail missing`);
      if (!Number.isFinite(g.ms) || g.ms < 0) e.push(`gates[${i}].ms must be a non-negative number`);
    });
  }
  if (typeof c.heartbeat_ok !== 'boolean') e.push('heartbeat_ok must be a boolean');
  if (!Number.isInteger(c.checks_total) || c.checks_total < 0) e.push('checks_total must be a non-negative integer');
  if (c.video !== null) {
    if (!isObj(c.video) || !isStr(c.video.path) || !Number.isFinite(c.video.duration_s) || c.video.duration_s <= 0)
      e.push('video must be null or {path, duration_s>0}');
    else if (c.video.path.includes('/') || c.video.path.includes('\\'))
      e.push('video.path must be a bare file name (media lives outside the repo, see LOOP_MEDIA_DIR)');
  }
  if (c.commit !== null && !/^[0-9a-f]{7,40}$/.test(c.commit ?? '')) e.push('commit must be null or a hex sha');
  if (Array.isArray(c.gates) && c.gates.some((g) => g && g.status === 'fail') && c.commit !== null)
    e.push('a cycle with a failing gate cannot record a commit: a gate failure stops the release');
  return e;
}

/** Errors for the whole ledger; `manifestVersion` is pack/manifest.json's pack_version. */
export function validateLedger(L, manifestVersion) {
  const e = [];
  if (!isObj(L)) return ['ledger is not an object'];
  for (const k of ['pack', 'product', 'pack_version', 'loop', 'honesty', 'cycles'])
    if (!(k in L)) e.push(`ledger missing "${k}"`);
  if (!/SmartCiti\.X : Trade Craft Academy/.test(L.product ?? '')) e.push('product must carry the brand name');
  if (manifestVersion && L.pack_version !== manifestVersion)
    e.push(`pack_version ${L.pack_version} != manifest ${manifestVersion}`);
  const lp = L.loop;
  if (!isObj(lp) || !ISO.test(lp.started ?? '') || !Number.isInteger(lp.cadence_min) || lp.cadence_min <= 0
      || !Number.isInteger(lp.cycles_planned) || lp.cycles_planned <= 0)
    e.push('loop must be {started ISO, cadence_min int, cycles_planned int}');
  if (!/nothing here is deployed/i.test(L.honesty ?? '')) e.push('honesty must state plainly that nothing here is deployed');
  if (!Array.isArray(L.cycles)) e.push('cycles must be an array');
  else L.cycles.forEach((c, i) => validateCycle(c, i + 1).forEach((m) => e.push(`cycles[${i}]: ${m}`)));
  return e;
}

export function manifestVersion() {
  return JSON.parse(readFileSync(join(ROOT, 'pack/manifest.json'), 'utf8')).pack_version;
}

function readJSON(p, fallback) {
  try { return JSON.parse(readFileSync(p, 'utf8')); } catch { return fallback; }
}

/** Fill the fields a checkpoint copies from loop state rather than retyping. */
export function fillDefaults(c, ledger, state = STATE) {
  const out = { ...c };
  if (out.n === undefined) out.n = ledger.cycles.length + 1;
  const ev = readJSON(join(state, 'evals_latest.json'), null);
  if (out.gates === undefined && ev) out.gates = ev.gates;
  if (out.checks_total === undefined && ev) {
    const g = ev.gates.find((x) => x.id === 'EV-01');
    const m = g && /^(\d+) checks/.exec(g.detail);
    if (m) out.checks_total = Number(m[1]);
  }
  if (out.heartbeat_ok === undefined) {
    try {
      const lines = readFileSync(join(state, 'heartbeat.jsonl'), 'utf8').trim().split('\n');
      out.heartbeat_ok = JSON.parse(lines[lines.length - 1]).ok;
    } catch { /* left undefined: validation names it */ }
  }
  if (out.video === undefined) out.video = null;
  if (out.commit === undefined) out.commit = null;
  return out;
}

function main(argv) {
  const [cmd, ...rest] = argv;
  const opt = (k) => { const i = rest.indexOf(k); return i >= 0 ? rest[i + 1] : undefined; };
  const ledgerPath = opt('--ledger') || LEDGER;
  const ledger = readJSON(ledgerPath, null);
  if (!ledger) { console.error(`cannot read ledger ${ledgerPath}`); return 2; }
  const mv = manifestVersion();
  if (cmd === 'show') {
    const errs = validateLedger(ledger, mv);
    console.log(`${ledger.product} · loop started ${ledger.loop.started} · every ${ledger.loop.cadence_min} min · `
      + `${ledger.cycles.length}/${ledger.loop.cycles_planned} cycles logged`);
    for (const c of ledger.cycles) {
      const gs = c.gates.map((g) => `${g.id.slice(3)}:${g.status}`).join(' ');
      console.log(`  #${c.n} ${c.started} → ${c.ended}  ${c.sprint}`);
      console.log(`     shipped ${c.shipped.length} · checks ${c.checks_total} · heartbeat ${c.heartbeat_ok ? 'ok' : 'NOT ok'}`
        + ` · video ${c.video ? c.video.duration_s + ' s' : 'none'} · commit ${c.commit ?? 'none'}`);
      console.log(`     gates ${gs}`);
    }
    console.log(errs.length ? `ledger INVALID:\n  ${errs.join('\n  ')}` : 'ledger valid');
    return errs.length ? 1 : 0;
  }
  if (cmd === 'add') {
    const file = opt('--json');
    if (!file) { console.error('usage: node loop/cycle.mjs add --json <file> [--ledger <path>]'); return 2; }
    const input = readJSON(file, undefined);
    if (input === undefined) { console.error(`cannot parse ${file}`); return 2; }
    const stateDir = opt('--state') || STATE;
    const cycle = fillDefaults(input, ledger, stateDir);
    const next = { ...ledger, cycles: [...ledger.cycles, cycle] };
    const errs = validateLedger(next, mv);
    if (errs.length) {
      console.error(`cycle refused, ledger unchanged:\n  ${errs.join('\n  ')}`);
      return 1;
    }
    writeFileSync(ledgerPath, JSON.stringify(next, null, 2) + '\n');
    console.log(`cycle #${cycle.n} appended to ${ledgerPath}`);
    return 0;
  }
  console.error('usage: node loop/cycle.mjs add --json <file> | show');
  return 2;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exit(main(process.argv.slice(2)));
}
