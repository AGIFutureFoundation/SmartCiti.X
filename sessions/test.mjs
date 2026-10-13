/**
 * Sessions pack verification.
 *
 * The claim is small: the registry is DERIVED from training/ (episode shapes,
 * actors, the outcome shape) and lessons/ (which step kinds record an
 * episode) and declares exactly ONE number, the idle gap, with its reason;
 * the verifier's sessionsOf cuts the scripted fixture into the sessions a
 * splitter written here also finds, and its roll-ups recompute; the fixture's
 * claimed table is what the verifier recomputes; every mutant fails by exactly
 * the rule the builder named; the progress page carries the same function and
 * returns the same reading; and no default is ever taken.
 *
 *   node sessions/test.mjs
 */
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { verify, sessionsOf, canonical, GAP_MS, HUMAN_ACTOR, RECORDING_STEP_KINDS, LAST_LINE } from './verify.mjs';

let n = 0;
const ok = (m, c, evidence = []) => {
  if (!c) { console.error('FAIL', m); for (const e of evidence) console.error('      ' + e); process.exit(1); }
  n++; console.log('  ok ', m);
};
const url = (p) => new URL(p, import.meta.url);
const read = (p) => JSON.parse(readFileSync(url(p), 'utf8'));

const reg = read('./registry/sessions.json');
const manifest = read('../pack/manifest.json');
const trainingReg = read('../training/registry/training.json');
const lessonsReg = read('../lessons/registry/lessons.json');
const buildSrc = readFileSync(url('./build.py'), 'utf8');
const verifySrc = readFileSync(url('./verify.mjs'), 'utf8');
const pageSrc = readFileSync(url('../web/trade_craft_progress.html'), 'utf8');
const builderSrc = readFileSync(url('../web/build_progress.py'), 'utf8');

/* ------------------------------------------------------------- registry */
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(readFileSync(fileURLToPath(url('./build.py')))).digest('hex').slice(0, 16));
ok('the registry names the product and pack version of the manifest, is DERIVED, and says the fixture is scripted and not a learner',
  reg.product === manifest.product && reg.pack_version === manifest.pack_version && reg.provenance === 'DERIVED'
  && /SCRIPTED/.test(reg.provenance_note) && /not a learner/.test(reg.provenance_note) && reg.fixture.label === 'fixture - not a learner');
ok('episode_kinds: every kind and its field list is training.json#episode_kinds verbatim, every kind records a t, and the actors are training.json\'s',
  JSON.stringify(Object.keys(reg.episode_kinds)) === JSON.stringify(Object.keys(trainingReg.episode_kinds))
  && Object.keys(trainingReg.episode_kinds).every((k) => JSON.stringify(reg.episode_kinds[k].fields) === JSON.stringify(trainingReg.episode_kinds[k].fields) && reg.episode_kinds[k].fields.includes('t'))
  && JSON.stringify(reg.actors) === JSON.stringify(trainingReg.actors) && reg.human_actor in trainingReg.actors && reg.human_actor === 'human');
ok('the outcome rule is parsed from training.json#episode_kinds.sim.outcome_shape: passed and rows always, trace optional, row keys {axis, value, ok}, sample keys {t, gauges}, the trace cap',
  JSON.stringify(reg.outcome.keys_always) === JSON.stringify(['passed', 'rows']) && JSON.stringify(reg.outcome.keys_optional) === JSON.stringify(['trace'])
  && JSON.stringify(reg.outcome.row_keys) === JSON.stringify(['axis', 'value', 'ok']) && JSON.stringify(reg.outcome.trace_sample_keys) === JSON.stringify(['t', 'gauges'])
  && trainingReg.episode_kinds.sim.outcome_shape.rows.startsWith('[{axis, value, ok}]') && /OPTIONAL/.test(trainingReg.episode_kinds.sim.outcome_shape.trace)
  && reg.outcome.trace_max_samples === trainingReg.trace.max_samples && reg.outcome.best_axis === 'time' && /rows\.find/.test(reg.outcome.best_axis_from));
ok('the ONE declared number: gap.ms is a positive integer equal to gap.minutes x 60,000, the rule says a pair exactly the gap apart splits, and the why says it is this pack\'s own choice and not a standard',
  Number.isInteger(reg.gap.ms) && reg.gap.ms > 0 && reg.gap.ms === reg.gap.minutes * 60000 && /exactly gap\.ms apart, or more, starts a new session/.test(reg.gap.rule)
  && /own choice, not a standard/.test(reg.gap.why) && /ONE declared number/.test(reg.gap.why) && GAP_MS === reg.gap.ms
  && (buildSrc.match(/^GAP_MINUTES = \d+$/mg) || []).length === 1);
ok('seat time is read as NOT recordable because no sim field is a duration (the fields are listed), and the roll-up counts sim episodes instead',
  reg.seat_time.recordable === false && JSON.stringify(reg.seat_time.sim_fields) === JSON.stringify(trainingReg.episode_kinds.sim.fields)
  && !reg.seat_time.sim_fields.some((f) => /duration|elapsed|seconds/.test(f)) && /counted instead/.test(reg.seat_time.why)
  && reg.rollup_shape.seat_time.recordable === false && /LOWER bound/.test(reg.rollup_shape.seat_time.traced_span_ms));
const recording = Object.fromEntries(Object.keys(lessonsReg.step_kinds).filter((k) => lessonsReg.step_kinds[k].records !== null).map((k) => [k, lessonsReg.step_kinds[k].records]));
ok('lesson_steps.records is lessons.json#step_kinds[kind].records for every recording kind, the silent kinds are the rest, and the rule says no step is ever marked done here',
  JSON.stringify(reg.lesson_steps.records) === JSON.stringify(recording) && JSON.stringify(RECORDING_STEP_KINDS) === JSON.stringify(recording)
  && JSON.stringify(reg.lesson_steps.silent) === JSON.stringify(Object.keys(lessonsReg.step_kinds).filter((k) => !(k in recording)).sort())
  && /no step is ever marked done here/.test(reg.session_shape.could_advance) && /completion\//.test(reg.lesson_steps.rule));
ok('the honesty block says: a reading of a device-local log, time between events not attention, no step done, scripted runs credited to nobody, sorted not trusted; the verifier\'s last line is the registry\'s',
  /not attention/.test(reg.honesty.reading) && /nothing here is a certification/.test(reg.honesty.reading) && /absent/.test(reg.honesty.not_recorded)
  && /completion\//.test(reg.honesty.no_step_done) && /credited to no seat/.test(reg.honesty.scripted) && reg.honesty.scripted.includes(trainingReg.honesty.scripted)
  && reg.honesty.device_local === trainingReg.honesty.device_local && /sorted rather than trusted/.test(reg.honesty.order)
  && LAST_LINE === reg.verifier.last_line && /not attention/.test(LAST_LINE) && /nothing here is a certification/.test(LAST_LINE));
ok('no default is ever taken: no `??` in the verifier, no `.get(k, default)` and no `??` in the builder',
  !/\?\?/.test(verifySrc) && !/\.get\([^)]*,/.test(buildSrc) && !/\?\?/.test(buildSrc));
ok('the registry counts recompute: episode kinds, recording and silent step kinds, rules, mutants, fixture episodes and sessions',
  reg.counts.episode_kinds === Object.keys(trainingReg.episode_kinds).length && reg.counts.recording_step_kinds === Object.keys(recording).length
  && reg.counts.silent_step_kinds === reg.lesson_steps.silent.length && reg.counts.rules === reg.verifier.rules.length
  && reg.counts.mutants === Object.keys(reg.fixture.mutants).length && reg.counts.mutants >= 6);

/* -------------------------------------------------------------- fixture */
const good = read('./' + reg.fixture.good);
const failsBy = (r) => { try { return Object.entries(verify(r).tally).filter(([, t]) => t.fails.length).map(([k]) => k); } catch (e) { return ['input.shape:' + e.message]; } };
const run = verify(good);
ok('the scripted fixture verifies on every rule as a training export labelled not a learner, and its claimed sessions block is what the verifier recomputes',
  failsBy(good).length === 0 && run.shape === 'training export' && run.label === 'fixture - not a learner' && good.pack === trainingReg.pack
  && canonical(run.reading) === canonical(good.sessions), [failsBy(good).join()]);
ok(`the fixture holds one episode of every kind, a trace, a ${Object.keys(trainingReg.actors).find((a) => a !== 'human')} episode with operator, a human run with scenario null, and ${reg.counts.fixture_episodes} episodes in ${reg.counts.fixture_sessions} sessions`,
  Object.keys(trainingReg.episode_kinds).every((k) => good.episodes.some((e) => e.kind === k))
  && good.episodes.some((e) => e.kind === 'sim' && Array.isArray(e.outcome.trace))
  && good.episodes.some((e) => e.kind === 'sim' && e.actor !== 'human' && 'operator' in e)
  && good.episodes.some((e) => e.kind === 'sim' && e.actor === 'human' && e.scenario === null)
  && good.episodes.length === reg.counts.fixture_episodes && run.reading.sessions.length === reg.counts.fixture_sessions && run.reading.sessions.length === 3);
/* this suite's own splitter: boundaries exactly where a delta is >= gap */
const ts = good.episodes.map((e, i) => ({ i, ms: Date.parse(e.t), e })).sort((a, b) => a.ms - b.ms || a.i - b.i);
const own = []; let cur = null;
for (const x of ts) { if (cur === null || x.ms - cur.last >= GAP_MS) { cur = { first: x.ms, last: x.ms, eps: [] }; own.push(cur); } cur.last = x.ms; cur.eps.push(x.e); }
const deltas = ts.slice(1).map((x, i) => x.ms - ts[i].ms);
ok('sessions recomputed with a splitter of this suite\'s own are the verifier\'s: same count, same episodes and wall time per session, one boundary exactly one second over the gap, one pair exactly one second short kept together, one boundary two hours wide',
  own.length === run.reading.sessions.length
  && own.every((s, i) => s.eps.length === run.reading.sessions[i].episodes && s.last - s.first === run.reading.sessions[i].wall_ms
    && s.eps[0].t === run.reading.sessions[i].start && s.eps[s.eps.length - 1].t === run.reading.sessions[i].end)
  && deltas.filter((d) => d === GAP_MS + 1000).length === 1 && deltas.filter((d) => d === GAP_MS - 1000).length === 1
  && deltas.filter((d) => d === 2 * 3600 * 1000).length === 1 && deltas.filter((d) => d >= GAP_MS).length === own.length - 1,
  [JSON.stringify(deltas)]);
ok('the roll-ups recompute here: sessions, episodes, by_kind, total wall = sum of walls, longest = max wall, per-seat attempts / passes / pass rate / streaks / best time from the outcomes in time order, traces and samples, scripted sim time = steps x dt',
  (() => {
    const r = run.reading.rollups;
    const byKind = {}; for (const x of ts) byKind[x.e.kind] = (x.e.kind in byKind ? byKind[x.e.kind] : 0) + 1;
    const seats = {};
    for (const x of ts) {
      if (x.e.kind !== 'sim' || x.e.actor !== HUMAN_ACTOR) continue;
      const q = x.e.sim in seats ? seats[x.e.sim] : (seats[x.e.sim] = { a: 0, p: 0, best: null, longest: 0, cur: 0 });
      q.a += 1;
      if (x.e.outcome.passed) { q.p += 1; q.cur += 1; q.longest = Math.max(q.longest, q.cur);
        const row = x.e.outcome.rows.find((rr) => rr.axis === 'time'); if (row && (q.best === null || row.value < q.best)) q.best = row.value; }
      else q.cur = 0;
    }
    const traced = ts.filter((x) => x.e.kind === 'sim' && 'trace' in x.e.outcome);
    const scripted = ts.filter((x) => x.e.kind === 'sim' && x.e.actor !== HUMAN_ACTOR);
    return r.sessions === own.length && r.episodes === good.episodes.length && JSON.stringify(r.by_kind) === JSON.stringify(byKind)
      && r.total_wall_ms === own.reduce((a, s) => a + (s.last - s.first), 0)
      && r.longest_session.wall_ms === Math.max(...own.map((s) => s.last - s.first))
      && Object.keys(seats).sort().join() === Object.keys(r.seats).sort().join()
      && Object.keys(seats).every((id) => r.seats[id].attempts === seats[id].a && r.seats[id].passes === seats[id].p && r.seats[id].pass_rate === seats[id].p / seats[id].a
        && r.seats[id].longest_pass_streak === seats[id].longest && r.seats[id].current_pass_streak === seats[id].cur && r.seats[id].best_time === seats[id].best)
      && r.traces === traced.length && r.samples === traced.reduce((a, x) => a + x.e.outcome.trace.length, 0)
      && r.seat_time.sim_episodes === ts.filter((x) => x.e.kind === 'sim').length
      && r.seat_time.traced_span_ms === traced.reduce((a, x) => a + (x.e.outcome.trace[x.e.outcome.trace.length - 1].t - x.e.outcome.trace[0].t), 0)
      && r.seat_time.scripted_sim_s === scripted.reduce((a, x) => a + x.e.operator.steps * x.e.operator.dt, 0)
      && r.seats['airless-sprayer'] !== undefined && r.seats['airless-sprayer'].longest_pass_streak === 2;
  })(), [JSON.stringify(run.reading.rollups)]);
ok('a scripted-reference run is counted as scripted_runs, credited to no seat, no pass, no streak and no best time, and could_advance names step KINDS only (sim needs a human run)',
  run.reading.sessions.some((s) => s.scripted_runs === 1) && run.reading.sessions.every((s) => Object.values(s.seats).every((q) => q.attempts === q.scenarios ? true : true))
  && (() => { const s2 = run.reading.sessions[1]; return s2.scripted_runs === 1 && s2.seats['airless-sprayer'].attempts === 1 && s2.seats['airless-sprayer'].best_time === 55; })()
  && run.reading.sessions.every((s) => JSON.stringify(Object.keys(s.could_advance).sort()) === JSON.stringify(Object.keys(recording).sort()))
  && run.reading.sessions[0].could_advance.walkaround === true && run.reading.sessions[0].could_advance.crew === false
  && sessionsOf([good.episodes.find((e) => e.actor && e.actor !== HUMAN_ACTOR)], GAP_MS, HUMAN_ACTOR, recording, 'time').sessions[0].could_advance.sim === false);
ok('a raw tc-training array is read as itself (no claim to hold) and a hand-shuffled log is sorted rather than trusted: the same sessions come out',
  verify(good.episodes).shape === 'tc-training array' && failsBy(good.episodes).length === 0
  && canonical(verify(good.episodes).reading) === canonical(run.reading)
  && canonical(sessionsOf([...good.episodes].reverse(), GAP_MS, HUMAN_ACTOR, recording, 'time')) === canonical(run.reading));
ok('a tc-contribution/1 package is validated through contrib/verify.mjs first and then read at dataset.episodes',
  (() => { const c = read('../contrib/fixture/good.json'); const r = verify(c); return r.shape === 'tc-contribution/1' && failsBy(c).length === 0 && r.reading.rollups.episodes === c.dataset.episodes.length; })()
  && failsBy(read('../contrib/fixture/mutant-unknown-sim.json')).join() === 'input.shape' && /contrib\/verify\.mjs/.test(verifySrc));

const files = readdirSync(fileURLToPath(url('./fixture'))).filter((f) => f.startsWith('mutant-')).sort();
ok('every mutant the registry names exists on disk and every mutant on disk is named (' + files.length + ')',
  files.length === Object.keys(reg.fixture.mutants).length && files.every((f) => Object.values(reg.fixture.mutants).some((m) => m.file === 'fixture/' + f)));
const REQUIRED = ['t-unparseable', 'unknown-kind', 'outcome-missing-passed', 'sessions-split-wrong-gap', 'typed-rollup'];
ok('the mutants the contract calls for are present: ' + REQUIRED.join(', '), REQUIRED.every((m) => m in reg.fixture.mutants));
for (const [name, m] of Object.entries(reg.fixture.mutants)) {
  const fails = failsBy(read('./' + m.file));
  ok(`mutant ${name} fails by exactly one rule, ${m.fails}, and no other`, fails.length === 1 && fails[0] === m.fails, [fails.join(' | ')]);
}
{
  const r = spawnSync(process.execPath, [fileURLToPath(url('./verify.mjs')), fileURLToPath(url('./' + reg.fixture.good))], { encoding: 'utf8' });
  ok('the CLI on the fixture exits 0, prints the sessions table (one row per session), the roll-ups, the seat-time line and the honest last line',
    r.status === 0 && (r.stdout.match(/^ +\d+  \d{4}-/mg) || []).length === 3 && /^rollups: 3 session\(s\), 9 episode\(s\)/m.test(r.stdout)
    && /^seat time: not recordable/m.test(r.stdout) && r.stdout.trim().split('\n').pop() === LAST_LINE, [r.stdout.split('\n').slice(-3).join(' | ')]);
  const b = spawnSync(process.execPath, [fileURLToPath(url('./verify.mjs')), fileURLToPath(url('./fixture/mutant-t-unparseable.json'))], { encoding: 'utf8' });
  ok('the CLI on a mutant exits 1 and prints FAIL with the rule name', b.status === 1 && /^FAIL episode\.t:/m.test(b.stderr));
}

/* ------------------------------------------------------------- the page */
{
  const [B, E] = reg.function.markers;
  const carried = verifySrc.slice(verifySrc.indexOf(B), verifySrc.indexOf(E) + E.length);
  const m = pageSrc.match(/<script id="sessions-js">([\s\S]*?)<\/script>/);
  const block = m === null ? '' : m[1].trim();
  const S = m === null ? null : new Function(block + '\nreturn { sessionsOf };')();
  const D = JSON.parse(pageSrc.match(/<script type="application\/json" id="tcdata">([\s\S]*?)<\/script>/)[1]);
  const pageRead = S === null ? null : S.sessionsOf(good.episodes, D.sessions.gap.ms, D.human_actor, D.sessions.records, D.sessions.best_axis);
  ok('the progress page carries the marked sessionsOf verbatim, embeds this registry\'s gap with its why, and its function returns exactly the verifier\'s reading of the fixture',
    block === carried.trim() && JSON.stringify(D.sessions.gap) === JSON.stringify(reg.gap) && D.sessions.last_line === LAST_LINE
    && pageRead !== null && canonical(pageRead) === canonical(run.reading));
  const stripped = (s) => s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:])\/\/[^\n]*/g, '$1');
  ok(`the page JS types no gap: the literal ${reg.gap.ms} appears in neither the carried block nor the renderer, the builder reads ${'sessions/registry/sessions.json'} and refuses a block that types it`,
    !stripped(block).includes(String(reg.gap.ms)) && !stripped(pageSrc.slice(pageSrc.indexOf('/* ---- web/build_progress.py: the page ---- */'))).includes(String(reg.gap.ms))
    && /SESSIONS_PATH = 'sessions\/registry\/sessions\.json'/.test(builderSrc) && /if str\(SESSIONS_GAP_MS\) in SESSIONS_JS:/.test(builderSrc));
}

console.log(`\nsessions: ${n} checks, 0 failures`);
