#!/usr/bin/env node
/**
 * Sessions verifier: a reading of a training log as sessions.
 *
 *   node sessions/verify.mjs <log.json>
 *
 * The input is one of three shapes, told apart by structure, never by a flag:
 *   - a raw `tc-training` array, exactly as the 3D page keeps it;
 *   - the training export training.json#export_format describes
 *     ({pack, exported, episodes}), optionally carrying `label` and a
 *     `sessions` block a builder claimed (recomputed here, never believed);
 *   - a `tc-contribution/1` package, validated FIRST through contrib/verify.mjs
 *     (imported, never copied) and then read at dataset.episodes.
 *
 * Every rule prints `ok <rule>` or `FAIL <rule>` at column 0 (FAIL on
 * stderr) and the process exits 1 on any failure. FAIL CLOSED: an episode
 * without a parseable ISO t, of a kind training/ does not declare, or with
 * an outcome the registry does not describe is a named failure, never a
 * skipped row. No nullish default appears in this file on purpose.
 *
 * WHAT A SESSION IS. A maximal run of episodes, in time order, where every
 * consecutive pair is separated by LESS than the idle gap the registry
 * declares (sessions.json#gap). A pair separated by exactly the gap, or
 * more, starts a new session. The gap is the ONE declared number in this
 * pack; everything else printed here is computed from the log.
 *
 * WHAT IT ATTESTS. Time between recorded events on one device. Not
 * attention, not presence, not skill, and not a certification of anything.
 */
import { readFileSync } from 'node:fs';
import { verify as verifyContribution } from '../contrib/verify.mjs';

const url = (p) => new URL(p, import.meta.url);
const reg = JSON.parse(readFileSync(url('./registry/sessions.json')));
const trainingReg = JSON.parse(readFileSync(url('../training/registry/training.json')));

class Missing extends Error {}
export function need(obj, key, who) {
  if (obj === null || typeof obj !== 'object' || !Object.prototype.hasOwnProperty.call(obj, key)) {
    throw new Missing(`${who} lacks ${JSON.stringify(key)}`);
  }
  return obj[key];
}
export function canonical(v) {
  if (Array.isArray(v)) return '[' + v.map(canonical).join(',') + ']';
  if (v !== null && typeof v === 'object') {
    return '{' + Object.keys(v).sort().map((k) => JSON.stringify(k) + ':' + canonical(v[k])).join(',') + '}';
  }
  return JSON.stringify(v);
}

// the registry, read: the contract is DERIVED from training/ and the copy
// here is held to the source so a stale sessions.json fails loudly
const EPISODE_KINDS = need(trainingReg, 'episode_kinds', 'training.json');
const REG_KINDS = need(reg, 'episode_kinds', 'sessions.json');
for (const k of Object.keys(EPISODE_KINDS)) {
  const want = JSON.stringify(need(EPISODE_KINDS[k], 'fields', `training.json#episode_kinds.${k}`));
  if (JSON.stringify(need(need(REG_KINDS, k, 'sessions.json#episode_kinds'), 'fields', `sessions.json#episode_kinds.${k}`)) !== want) {
    throw new Error(`sessions.json#episode_kinds.${k}.fields is not training.json's; rebuild sessions/`);
  }
}
const GAP = need(reg, 'gap', 'sessions.json');
export const GAP_MS = need(GAP, 'ms', 'sessions.json#gap');
if (!Number.isInteger(GAP_MS) || GAP_MS <= 0) throw new Error('sessions.json#gap.ms is not a positive integer');
const OUTCOME_RULE = need(reg, 'outcome', 'sessions.json');
const OUTCOME_ALWAYS = need(OUTCOME_RULE, 'keys_always', 'sessions.json#outcome');
const OUTCOME_OPTIONAL = need(OUTCOME_RULE, 'keys_optional', 'sessions.json#outcome');
const ROW_KEYS = need(OUTCOME_RULE, 'row_keys', 'sessions.json#outcome');
const TRACE_KEYS = need(OUTCOME_RULE, 'trace_sample_keys', 'sessions.json#outcome');
const TIME_AXIS = need(OUTCOME_RULE, 'best_axis', 'sessions.json#outcome');
const ACTORS = need(trainingReg, 'actors', 'training.json');
export const HUMAN_ACTOR = need(reg, 'human_actor', 'sessions.json');
if (!(HUMAN_ACTOR in ACTORS)) throw new Error('sessions.json#human_actor is not in training.json#actors');
const STEP_RECORDS = need(reg, 'lesson_steps', 'sessions.json');
export const RECORDING_STEP_KINDS = need(STEP_RECORDS, 'records', 'sessions.json#lesson_steps');
const RULES = need(need(reg, 'verifier', 'sessions.json'), 'rules', 'sessions.json#verifier');
export const LAST_LINE = need(need(reg, 'verifier', 'sessions.json'), 'last_line', 'sessions.json#verifier');
const EXPORT_PACK = need(need(trainingReg, 'storage', 'training.json'), 'key', 'training.json#storage');
const CONTRIB_TAG = 'tc-contribution/1';

/* SESSIONS_OF:BEGIN - sessionsOf(training, gapMs, humanActor, stepRecords, bestAxis)
   training   : an array of episodes as the 3D page keeps them under tc-training
   gapMs      : the idle gap, READ from sessions/registry/sessions.json#gap.ms, never typed
   humanActor : training.json's name for a learner at the keys ("human")
   stepRecords: lessons.json step kinds that record an episode, as {stepKind: episodeKind}
   bestAxis   : the rubric axis whose value is a run's time ("time")
   Pure and deterministic: no clock read, no storage, no DOM. Throws, naming the
   episode, on anything it cannot read - a session table with a silently
   dropped row would be a reading of a log that does not exist. Episodes are
   put in time order first (stable on the recorded order for equal t) because
   a rolling cap can only ever drop the oldest, so the order the page wrote
   is the order in time, and a hand-edited log is sorted rather than trusted.
   Nothing here marks a lesson step done: could_advance says only which
   recording step KINDS a session holds an episode for. */
function sessionsOf(training, gapMs, humanActor, stepRecords, bestAxis) {
  if (!Array.isArray(training)) throw new Error('sessions: the training log is not an array');
  if (!Number.isInteger(gapMs) || gapMs <= 0) throw new Error('sessions: the gap is not a positive integer of milliseconds');
  const eps = training.map((ep, i) => {
    if (ep === null || typeof ep !== 'object' || Array.isArray(ep)) throw new Error('sessions: episode ' + i + ' is not an object');
    if (typeof ep.t !== 'string' || !Number.isFinite(Date.parse(ep.t))) throw new Error('sessions: episode ' + i + ' has no parseable ISO-8601 t');
    return { i, ms: Date.parse(ep.t), ep };
  });
  eps.sort((a, b) => a.ms - b.ms || a.i - b.i);
  const sessions = [];
  let cur = null;
  for (const { i, ms, ep } of eps) {
    if (cur === null || ms - cur.lastMs >= gapMs) {
      cur = { n: sessions.length + 1, start: ep.t, end: ep.t, startMs: ms, lastMs: ms, wall_ms: 0, episodes: 0, by_kind: {},
        halls: [], campuses: [], seats: {}, scripted_runs: 0, walkaround_points: [], advisor_exchanges: 0, crew_exchanges: 0,
        traces: 0, samples: 0, could_advance: {} };
      sessions.push(cur);
    }
    cur.end = ep.t; cur.lastMs = ms; cur.wall_ms = ms - cur.startMs; cur.episodes += 1;
    const kind = ep.kind;
    if (typeof kind !== 'string') throw new Error('sessions: episode ' + i + ' has no kind');
    cur.by_kind[kind] = (kind in cur.by_kind ? cur.by_kind[kind] : 0) + 1;
    if (typeof ep.hall === 'string' && !cur.halls.includes(ep.hall)) cur.halls.push(ep.hall);
    if (typeof ep.campus === 'string' && !cur.campuses.includes(ep.campus)) cur.campuses.push(ep.campus);
    if (kind === 'sim') {
      if (typeof ep.sim !== 'string') throw new Error('sessions: sim episode ' + i + ' names no seat');
      const out = ep.outcome;
      if (out === null || typeof out !== 'object' || typeof out.passed !== 'boolean' || !Array.isArray(out.rows)) {
        throw new Error('sessions: sim episode ' + i + ' has an outcome without a boolean passed and a rows list');
      }
      if (ep.actor !== humanActor) {
        cur.scripted_runs += 1;
      } else {
        const sc = ep.scenario === null || ep.scenario === undefined ? '(none)' : String(ep.scenario);
        if (!(ep.sim in cur.seats)) cur.seats[ep.sim] = { attempts: 0, passes: 0, best_time: null, scenarios: {} };
        const seat = cur.seats[ep.sim];
        if (!(sc in seat.scenarios)) seat.scenarios[sc] = { attempts: 0, passes: 0, best_time: null };
        const s = seat.scenarios[sc];
        seat.attempts += 1; s.attempts += 1;
        if (out.passed) {
          seat.passes += 1; s.passes += 1;
          const row = out.rows.find((r) => r !== null && typeof r === 'object' && r.axis === bestAxis);
          const tv = row === undefined ? NaN : Number(row.value);
          if (Number.isFinite(tv)) {
            if (seat.best_time === null || tv < seat.best_time) seat.best_time = tv;
            if (s.best_time === null || tv < s.best_time) s.best_time = tv;
          }
        }
      }
      if ('trace' in out) {
        if (!Array.isArray(out.trace)) throw new Error('sessions: sim episode ' + i + ' has a trace that is not a list');
        cur.traces += 1; cur.samples += out.trace.length;
      }
    } else if (kind === 'walkaround') {
      const key = String(ep.sim) + ':' + String(ep.point);
      if (!cur.walkaround_points.includes(key)) cur.walkaround_points.push(key);
    } else if (kind === 'advisor') {
      cur.advisor_exchanges += 1;
    } else if (kind === 'crew') {
      cur.crew_exchanges += 1;
    } else {
      throw new Error('sessions: episode ' + i + ' is of a kind this reading does not know: ' + JSON.stringify(kind));
    }
  }
  for (const s of sessions) {
    for (const stepKind of Object.keys(stepRecords)) {
      const epKind = stepRecords[stepKind];
      s.could_advance[stepKind] = epKind in s.by_kind
        && (epKind !== 'sim' || Object.keys(s.seats).length > 0);
    }
    s.halls.sort(); s.campuses.sort(); s.walkaround_points.sort();
    s.walkaround_points = s.walkaround_points.length;
    delete s.startMs; delete s.lastMs;
  }
  /* roll-ups across sessions: every figure below is computed here */
  const seats = {};
  let simEpisodes = 0, tracedSpan = 0, scriptedSimS = 0, traces = 0, samples = 0;
  const byKind = {};
  for (const { i, ep } of eps) {
    byKind[ep.kind] = (ep.kind in byKind ? byKind[ep.kind] : 0) + 1;
    if (ep.kind !== 'sim') continue;
    simEpisodes += 1;
    const out = ep.outcome;
    if ('trace' in out) {
      traces += 1; samples += out.trace.length;
      if (out.trace.length > 1) {
        const first = out.trace[0], last = out.trace[out.trace.length - 1];
        const span = (last !== null && typeof last === 'object' ? Number(last.t) : NaN) - (first !== null && typeof first === 'object' ? Number(first.t) : NaN);
        if (!Number.isFinite(span) || span < 0) throw new Error('sessions: sim episode ' + i + ' has trace sample times that do not read as a span');
        tracedSpan += span;
      }
    }
    if (ep.actor !== humanActor) {
      const op = ep.operator;
      if (op !== null && typeof op === 'object' && Number.isFinite(op.steps) && typeof op.dt === 'number' && Number.isFinite(op.dt)) scriptedSimS += op.steps * op.dt;
      continue;
    }
    if (!(ep.sim in seats)) seats[ep.sim] = { attempts: 0, passes: 0, pass_rate: null, best_time: null, longest_pass_streak: 0, current_pass_streak: 0 };
    const seat = seats[ep.sim];
    seat.attempts += 1;
    if (out.passed) {
      seat.passes += 1; seat.current_pass_streak += 1;
      if (seat.current_pass_streak > seat.longest_pass_streak) seat.longest_pass_streak = seat.current_pass_streak;
      const row = out.rows.find((r) => r !== null && typeof r === 'object' && r.axis === bestAxis);
      const tv = row === undefined ? NaN : Number(row.value);
      if (Number.isFinite(tv) && (seat.best_time === null || tv < seat.best_time)) seat.best_time = tv;
    } else {
      seat.current_pass_streak = 0;
    }
  }
  for (const id of Object.keys(seats)) seats[id].pass_rate = seats[id].attempts === 0 ? null : seats[id].passes / seats[id].attempts;
  let longest = null;
  for (const s of sessions) if (longest === null || s.wall_ms > longest.wall_ms) longest = { n: s.n, wall_ms: s.wall_ms, episodes: s.episodes };
  const rollups = {
    sessions: sessions.length,
    episodes: eps.length,
    by_kind: byKind,
    total_wall_ms: sessions.reduce((a, s) => a + s.wall_ms, 0),
    seat_time: {
      recordable: false,
      sim_episodes: simEpisodes,
      traced_span_ms: tracedSpan,
      scripted_sim_s: scriptedSimS,
    },
    seats,
    longest_session: longest,
    traces, samples,
  };
  return { gap_ms: gapMs, sessions, rollups };
}
/* SESSIONS_OF:END */
export { sessionsOf };

/** the episodes and any claimed reading inside one of the three input shapes */
export function unwrap(input) {
  if (Array.isArray(input)) return { shape: 'tc-training array', episodes: input, claimed: null, label: null, contribution: null };
  if (input === null || typeof input !== 'object') throw new Missing('input is neither a list nor an object');
  if ('record' in input && input.record === CONTRIB_TAG) {
    const run = verifyContribution(input);
    const fails = Object.entries(run.tally).filter(([, t]) => t.fails.length).map(([k]) => k);
    return { shape: CONTRIB_TAG, episodes: need(need(input, 'dataset', 'package'), 'episodes', 'dataset'), claimed: null,
      label: need(need(input, 'contributor', 'package'), 'claimed', 'contributor'), contribution: fails };
  }
  const pack = need(input, 'pack', 'export');
  const episodes = need(input, 'episodes', 'export');
  return { shape: 'training export', pack, episodes,
    claimed: 'sessions' in input ? input.sessions : null,
    label: 'label' in input ? input.label : null, contribution: null };
}

export function verify(input) {
  const tally = {};
  for (const r of RULES) tally[r] = { checked: 0, fails: [] };
  const check = (rule, cond, msg) => { tally[rule].checked++; if (!cond) tally[rule].fails.push(msg); };

  const u = unwrap(input);
  check('input.shape', Array.isArray(u.episodes), `${u.shape}: episodes is not a list`);
  if (u.shape === 'training export') {
    check('input.shape', u.pack === need(trainingReg, 'pack', 'training.json'),
      `export.pack ${JSON.stringify(u.pack)} is not training.json's pack`);
  }
  if (u.contribution !== null) {
    check('input.shape', u.contribution.length === 0, `the ${CONTRIB_TAG} package fails contrib/verify.mjs on: ${u.contribution.join(', ')}`);
  }
  const episodes = Array.isArray(u.episodes) ? u.episodes : [];
  for (const [i, ep] of episodes.entries()) {
    const w = `episode ${i}`;
    const t = need(ep, 't', w);
    check('episode.t', typeof t === 'string' && Number.isFinite(Date.parse(t)), `${w}: t ${JSON.stringify(t)} is not a parseable ISO-8601 string`);
    const kind = need(ep, 'kind', w);
    check('episode.kind', kind in EPISODE_KINDS, `${w}: kind ${JSON.stringify(kind)} is not in training.json#episode_kinds`);
    if (kind !== 'sim') continue;
    const actor = need(ep, 'actor', w);
    check('episode.kind', actor in ACTORS, `${w}: actor ${JSON.stringify(actor)} is not in training.json#actors`);
    const out = need(ep, 'outcome', w);
    const isObj = out !== null && typeof out === 'object' && !Array.isArray(out);
    check('episode.outcome', isObj, `${w}: outcome is not an object`);
    if (!isObj) continue;
    for (const k of OUTCOME_ALWAYS) check('episode.outcome', k in out, `${w}: outcome lacks ${JSON.stringify(k)}`);
    for (const k of Object.keys(out)) check('episode.outcome', OUTCOME_ALWAYS.includes(k) || OUTCOME_OPTIONAL.includes(k),
      `${w}: outcome carries ${JSON.stringify(k)}, which training.json#episode_kinds.sim.outcome_shape does not describe`);
    if ('passed' in out) check('episode.outcome', typeof out.passed === 'boolean', `${w}: outcome.passed is not a boolean`);
    if ('rows' in out) {
      check('episode.outcome', Array.isArray(out.rows), `${w}: outcome.rows is not a list`);
      if (Array.isArray(out.rows)) {
        for (const [j, r] of out.rows.entries()) {
          const keys = r !== null && typeof r === 'object' ? Object.keys(r).sort() : null;
          check('episode.outcome', keys !== null && JSON.stringify(keys) === JSON.stringify([...ROW_KEYS].sort()),
            `${w}: rubric row ${j} has keys ${JSON.stringify(keys)}, not ${JSON.stringify(ROW_KEYS)}`);
        }
      }
    }
    if ('trace' in out) {
      check('episode.outcome', Array.isArray(out.trace), `${w}: outcome.trace is not a list`);
      if (Array.isArray(out.trace)) {
        for (const [j, smp] of out.trace.entries()) {
          const keys = smp !== null && typeof smp === 'object' ? Object.keys(smp).sort() : null;
          check('episode.outcome', keys !== null && JSON.stringify(keys) === JSON.stringify([...TRACE_KEYS].sort()),
            `${w}: trace sample ${j} has keys ${JSON.stringify(keys)}, not ${JSON.stringify(TRACE_KEYS)}`);
        }
      }
    }
  }
  const clean = Object.values(tally).every((t) => t.fails.length === 0);
  let reading = null;
  if (clean) {
    try { reading = sessionsOf(episodes, GAP_MS, HUMAN_ACTOR, RECORDING_STEP_KINDS, TIME_AXIS); }
    catch (e) { check('episode.outcome', false, e.message); }
  }
  if (reading !== null && u.claimed !== null) {
    const c = u.claimed;
    const gap = need(c, 'gap_ms', 'claimed sessions');
    check('sessions.gap', gap === GAP_MS, `the file claims a gap of ${gap} ms; the registry declares ${GAP_MS} ms, and a session table cut at another gap is another reading`);
    const cs = need(c, 'sessions', 'claimed sessions');
    check('sessions.claimed', canonical(cs) === canonical(reading.sessions),
      `the claimed session table does not recompute: claimed ${Array.isArray(cs) ? cs.length : 'no'} session(s), recomputed ${reading.sessions.length}`
      + (Array.isArray(cs) && cs.length === reading.sessions.length ? ' (same count, different rows)' : ''));
    const cr = need(c, 'rollups', 'claimed sessions');
    check('rollups.claimed', canonical(cr) === canonical(reading.rollups),
      'the claimed roll-ups do not recompute: ' + Object.keys(reading.rollups).filter((k) => !(k in cr) || canonical(cr[k]) !== canonical(reading.rollups[k])).map((k) => `${k} claimed ${JSON.stringify(cr[k])}, recomputed ${JSON.stringify(reading.rollups[k])}`).join('; '));
  }
  return { tally, reading, shape: u.shape, label: u.label };
}

const fmtMs = (ms) => {
  const s = Math.round(ms / 1000);
  return `${Math.floor(s / 3600)}h${String(Math.floor((s % 3600) / 60)).padStart(2, '0')}m${String(s % 60).padStart(2, '0')}s`;
};
export function table(reading) {
  const lines = [];
  lines.push('session  start                     end                       wall       eps  sim  adv  crew  walk  seats                          traces  could-advance');
  for (const s of reading.sessions) {
    const k = (x) => (x in s.by_kind ? s.by_kind[x] : 0);
    const seats = Object.keys(s.seats).sort().map((id) => `${id} ${s.seats[id].passes}/${s.seats[id].attempts}` + (s.seats[id].best_time === null ? '' : ` best ${s.seats[id].best_time}`)).join(', ') + (s.scripted_runs ? ` (+${s.scripted_runs} scripted)` : '');
    const adv = Object.keys(s.could_advance).filter((x) => s.could_advance[x]).join(',');
    lines.push(`${String(s.n).padStart(7)}  ${s.start}  ${s.end}  ${fmtMs(s.wall_ms).padStart(9)}  ${String(s.episodes).padStart(3)}  ${String(k('sim')).padStart(3)}  ${String(k('advisor')).padStart(3)}  ${String(k('crew')).padStart(4)}  ${String(s.walkaround_points).padStart(4)}  ${(seats === '' ? '-' : seats).padEnd(30)} ${String(s.traces).padStart(6)}  ${adv === '' ? '-' : adv}`);
  }
  const r = reading.rollups;
  lines.push(`rollups: ${r.sessions} session(s), ${r.episodes} episode(s), total wall ${fmtMs(r.total_wall_ms)}, longest session `
    + (r.longest_session === null ? 'none' : `#${r.longest_session.n} at ${fmtMs(r.longest_session.wall_ms)}`)
    + `, ${r.traces} trace(s) holding ${r.samples} sample(s)`);
  lines.push(`seat time: not recordable - a sim episode carries no duration, so ${r.seat_time.sim_episodes} sim episode(s) are counted instead; `
    + `traced span ${fmtMs(r.seat_time.traced_span_ms)} is a lower bound from ~1 Hz samples where a trace is attached; scripted sim time ${r.seat_time.scripted_sim_s}s is steps x dt of headless reference runs, not the learner's`);
  for (const id of Object.keys(r.seats).sort()) {
    const s = r.seats[id];
    lines.push(`seat ${id}: ${s.passes}/${s.attempts} passed (${s.pass_rate === null ? '-' : Math.round(s.pass_rate * 100) + '%'}), longest pass streak ${s.longest_pass_streak}, current ${s.current_pass_streak}, best ${TIME_AXIS} ${s.best_time === null ? 'none' : s.best_time}`);
  }
  return lines;
}

const isMain = process.argv[1] && new URL(`file://${process.argv[1]}`).pathname === new URL(import.meta.url).pathname;
if (isMain) {
  const path = process.argv[2];
  if (!path) { console.error('FAIL usage: node sessions/verify.mjs <tc-training.json>'); process.exit(1); }
  let failed = false;
  try {
    const input = JSON.parse(readFileSync(path, 'utf8'));
    const { tally, reading, shape, label } = verify(input);
    console.log(`input: ${shape}${label === null ? '' : ' labelled ' + JSON.stringify(label)}; gap ${GAP_MS} ms (${need(GAP, 'why', 'sessions.json#gap')})`);
    for (const [rule, t] of Object.entries(tally)) {
      const line = `${rule}: checked ${t.checked}, failing ${t.fails.length}`;
      if (t.fails.length) { failed = true; console.error(`FAIL ${line}`); for (const f of t.fails) console.error(`     ${f}`); }
      else console.log(`ok ${line}`);
    }
    if (reading !== null) for (const l of table(reading)) console.log(l);
    console.log(LAST_LINE);
  } catch (e) {
    failed = true;
    if (e instanceof Missing) console.error(`FAIL input.shape: ${e.message}`);
    else console.error(`FAIL verify: ${e.message}`);
  }
  process.exit(failed ? 1 : 0);
}
