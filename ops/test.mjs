/** ACP-13 — registries, rollout lanes, the automation loop, the cost governor. */
import { ModuleRegistry, AgentRegistry, SkillGraphRegistry, RegistryError, mirror } from './registries.mjs';
import { RolloutManager, LANES } from './rollout.mjs';
import { Scheduler, CostGovernor, JOBS, PLANES } from './jobs.mjs';
import { ParityMonitor, StopConditions } from '../bus/safeguards.mjs';
import { AuditLog } from '../bus/audit.mjs';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (label, cond) => { if (!cond) { console.error('FAIL', label); process.exit(1); } n++; console.log('  ok ', label); };
const throws = (fn, re) => { try { fn(); return false; } catch (e) { return re.test(String(e.message)); } };

/* ------------------------------------------------------- module registry -- */
{
  const m = new ModuleRegistry();
  m.register('u01.l01.s01', { hall: 'ironworkers' });
  ok('a module enters the pipeline as a draft and nothing else',
    m.get('u01.l01.s01').state === 'draft');
  ok('draft cannot jump the pipeline straight to live',
    throws(() => m.transition('u01.l01.s01', 'live'), /not a legal transition/));
  m.transition('u01.l01.s01', 'schema_ok');
  m.transition('u01.l01.s01', 'calibrating');
  m.transition('u01.l01.s01', 'live');
  ok('the legal path draft -> schema_ok -> calibrating -> live is open',
    m.get('u01.l01.s01').state === 'live');
  m.transition('u01.l01.s01', 'demoted', 'calibration drift');
  ok('demotion is recorded and counted, not just a state flip',
    m.get('u01.l01.s01').state === 'demoted' && m.get('u01.l01.s01').demotions === 1);
  ok('every mutation bumps the registry version and lands in the history',
    m.version === 5 && m.history.length === 5);
  ok('history entries are frozen — the record of what shipped cannot be edited',
    Object.isFrozen(m.history[0]));
  ok('re-registering a known id is refused rather than silently overwriting',
    throws(() => m.register('u01.l01.s01'), /already registered/));
}

/* -------------------------------------------------------- agent registry -- */
{
  const a = new AgentRegistry();
  a.register('joyce', '1.0.0', { evals: { pass: false, failedGates: ['scope'] } });
  ok('a mentor version with a failing eval record cannot become champion',
    throws(() => a.promote('joyce', '1.0.0'), /no passing eval record/));
  a.register('joyce', '1.1.0', { evals: null });
  ok('a mentor version with NO eval record cannot become champion either',
    throws(() => a.promote('joyce', '1.1.0'), /no passing eval record/));
  a.register('joyce', '1.2.0', { evals: { pass: true } });
  a.promote('joyce', '1.2.0');
  ok('a passing version promotes, and the champion is the one that passed',
    a.champion('joyce') === '1.2.0');
}

/* --------------------------------------------------- skill graph registry - */
{
  const g = new SkillGraphRegistry();
  g.publish('1.0.0', { nodes: 33, edges: 40 });
  ok('the first graph publishes without a migration — there is nobody to migrate',
    g.current().graphVersion === '1.0.0');
  ok('a revision without a migration is refused: a new prerequisite can strand learners mid-ladder',
    throws(() => g.publish('1.1.0', { nodes: 34, edges: 42 }), /requires a migration/));
  g.publish('1.1.0', { nodes: 34, edges: 42, migration: 'add-node-34.mjs' });
  ok('a revision with a migration is accepted', g.current().graphVersion === '1.1.0');
}

/* ------------------------------------------------------------- mirroring -- */
{
  const m = new ModuleRegistry(); const a = new AgentRegistry();
  m.register('x'); m.transition('x', 'schema_ok'); m.transition('x', 'calibrating'); m.transition('x', 'live');
  a.register('chris', '2.0.0', { evals: { pass: true } }); a.promote('chris', '2.0.0');
  const out = mirror(m, a);
  ok('external listings mirror outward only, and say so in the payload',
    out.direction === 'outbound-only' && out.modules === 1 && out.agents[0].id === 'chris');
}

/* ------------------------------------------------------- rollout lanes ---- */
{
  const audit = new AuditLog();
  const parity = new ParityMonitor({ audit });
  const stop = new StopConditions({ audit, parity });
  const r = new RolloutManager({ parity, stop, audit });

  r.start('lesson-pack-7', { kind: 'content' });
  const a1 = r.advance('lesson-pack-7');
  ok('a content rollout starts at one hall, never the whole network',
    a1.ok && a1.lane === 'canary' && a1.halls === 1);
  const early = r.advance('lesson-pack-7', { dwellHours: 2 });
  ok('the next lane will not open before the canary has been observed',
    !early.ok && /needs 24h/.test(early.why));
  const a2 = r.advance('lesson-pack-7', { dwellHours: 30 });
  ok('after the dwell window the wave lane opens to five halls',
    a2.ok && a2.lane === 'wave' && a2.halls === 5);
  const a3 = r.advance('lesson-pack-7', { dwellHours: 60 });
  ok(`and then to the whole network (${LANES[2].halls} halls)`,
    a3.ok && a3.lane === 'full' && a3.halls === LANES[2].halls);
}

/* --------------------------------------------- dial parameters shadow first */
{
  const r = new RolloutManager({});
  r.start('dial-loopgain-0.35', { kind: 'dial_params', shadowStartedDaysAgo: 3 });
  const early = r.advance('dial-loopgain-0.35');
  ok('a dial-parameter change cannot reach even the canary without its shadow run',
    !early.ok && /14-day shadow/.test(early.why));
  r.start('dial-loopgain-ok', { kind: 'dial_params', shadowStartedDaysAgo: 15 });
  ok('a completed shadow run opens the canary lane',
    r.advance('dial-loopgain-ok').ok);
}

/* -------------------------------------------- ACP-08 owns the ship decision */
{
  const audit = new AuditLog();
  const parity = new ParityMonitor({ audit });
  const r = new RolloutManager({ parity, audit });
  r.start('pack-9', { kind: 'content' });
  r.advance('pack-9');
  parity.report('site-a', { n: 200, gatePassRate: 0.80 });
  parity.report('site-b', { n: 200, gatePassRate: 0.55 });
  parity.run();
  const blocked = r.advance('pack-9', { dwellHours: 99 });
  ok('an open parity ticket blocks the next lane, through ACP-08 rather than a second check',
    !blocked.ok && /parity is red/.test(blocked.why));
}

{
  const audit = new AuditLog();
  const parity = new ParityMonitor({ audit });
  const stop = new StopConditions({ audit, parity });
  const r = new RolloutManager({ parity, stop, audit });
  r.start('pack-10', { kind: 'content' });
  r.advance('pack-10');
  parity.report('a', { n: 100, gatePassRate: 0.80 });
  parity.report('b', { n: 100, gatePassRate: 0.79 });
  parity.run();
  stop.evaluate({ cohortAnxietyShare: 0.4 });
  const halted = r.advance('pack-10', { dwellHours: 99 });
  ok('nothing promotes into a halted network, even with parity clean',
    !halted.ok && /halted/.test(halted.why));
  const reverted = r.onHalt(stop.reasons);
  ok('the halt automatically rolls live rollouts back off the network',
    reverted.includes('pack-10') && r.get('pack-10').state === 'rolled_back');
  const resumed = r.advance('pack-10', { dwellHours: 99 });
  ok('a rolled-back change cannot be resumed — it reopens as a new rollout',
    !resumed.ok && /rolled back/.test(resumed.why));
}

/* ------------------------------------------------------- the job loop ----- */
{
  const audit = new AuditLog();
  const s = new Scheduler({ audit });
  let parityRuns = 0, nightlyRuns = 0;
  s.on('parity_job', () => { parityRuns++; return 'clean'; });
  s.on('calibration_sweep', () => { nightlyRuns++; });
  s.on('coverage_bot', () => { throw new Error('coverage index unavailable'); });

  s.tick(0);
  ok('everything due on the first tick runs', parityRuns === 1 && nightlyRuns === 1);
  s.tick(3600_000);
  ok('an hour later nothing on a nightly or weekly cadence is due again',
    parityRuns === 1 && nightlyRuns === 1);
  s.tick(86_400_000);
  ok('a day later the nightly jobs run and the weekly one does not',
    nightlyRuns === 2 && parityRuns === 1);
  s.tick(604_800_000);
  ok('a week later the parity job runs again', parityRuns === 2);
  ok('a throwing job is recorded as a failure and does not stop the loop',
    s.failures().length >= 1 && s.failures()[0].job === 'coverage_bot' && nightlyRuns >= 2);
  ok('every skip is recorded with its reason, so a quiet loop is still legible',
    s.skips.length > 0 && s.skips.every((k) => k.why));
}

{
  const audit = new AuditLog();
  const s = new Scheduler({ audit });
  s.on('calibration_sweep', () => {});
  s.tick(0);
  ok('the parity job going unhandled is audited, because ACP-08 halts when its window lapses',
    audit.entries().some((e) => e.action === 'job.missing' && /safety-critical/.test(e.why)));
}

/* ---------------------------------------------- the parity job feeds ACP-08 */
{
  const audit = new AuditLog();
  const parity = new ParityMonitor({ audit });
  const stop = new StopConditions({ audit, parity });
  const s = new Scheduler({ audit });
  s.on('parity_job', () => {
    parity.report('a', { n: 100, gatePassRate: 0.80 });
    parity.report('b', { n: 100, gatePassRate: 0.78 });
    return parity.run();
  });
  s.tick(0);
  ok('a scheduler that runs the parity job keeps the network out of the halt',
    stop.evaluate({}).halted === false);
  const s2 = new Scheduler({ audit });
  const stop2 = new StopConditions({ audit, parity: new ParityMonitor({ audit }) });
  s2.tick(0);
  ok('a scheduler that never runs it halts the network — the loop is load-bearing',
    stop2.evaluate({}).halted === true);
}

/* ------------------------------------------------------- cost governor ---- */
{
  const g = new CostGovernor({ budgets: { conversation: 1000, factory: 1000 } });
  ok('the control plane is structurally un-throttleable, not merely well-funded',
    PLANES.control.throttleable === false);
  g.spend('control', 10_000_000);
  ok('no amount of control-plane spend degrades it: certification is not a budget line',
    g.admit('control', 5000).ok === true && g.tierFor('control') === 'exact');
  g.spend('conversation', 850);
  ok('the conversation plane degrades to a smaller tier under pressure, still serving',
    g.tierFor('conversation') === 'compact' && g.admit('conversation', 1).ok === true);
  g.spend('conversation', 300);
  ok('over budget it drops to minimal rather than refusing the learner outright',
    g.tierFor('conversation') === 'minimal' && g.admit('conversation', 1).ok === true);
  g.spend('factory', 1200);
  ok('the factory plane, which no learner is waiting on, is the one that pauses',
    g.admit('factory', 1).ok === false);
  ok('the report names every plane, its pressure and whether it may be throttled',
    g.report().length === 3 && g.report().every((r) => 'throttleable' in r));
}

ok('all seven ACP-13 jobs are declared with a cadence and a description',
  JOBS.length === 7 && JOBS.every((j) => j.cadence && j.does));
ok(`the lanes are 1, 5 and ${LANES[2].halls} halls — the full lane is the whole network, read from the pack`,
  LANES[0].halls === 1 && LANES[1].halls === 5
  && LANES[2].halls === JSON.parse(readFileSync(new URL('../pack/manifest.json', import.meta.url), 'utf8')).ledger.halls);

console.log(`\n${n} checks passed.`);
