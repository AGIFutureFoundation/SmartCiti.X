/**
 * ACP-13 adversarial pass.
 *
 * One question: can a change reach learners without passing every gate that is
 * supposed to stand in front of it? The rollout lanes are the front door; this
 * looks for side doors.
 */
import { ModuleRegistry, AgentRegistry, SkillGraphRegistry } from './registries.mjs';
import { RolloutManager } from './rollout.mjs';
import { Scheduler, CostGovernor } from './jobs.mjs';
import { ParityMonitor, StopConditions } from '../bus/safeguards.mjs';
import { AuditLog } from '../bus/audit.mjs';

let n = 0;
const ok = (label, cond) => { if (!cond) { console.error('FAIL', label); process.exit(1); } n++; console.log('  ok ', label); };

/* --- side door 1: reach 'live' by repeating a legal single step ----------- */
{
  const m = new ModuleRegistry();
  m.register('x');
  let hops = 0;
  const path = [];
  // Walk every legal transition greedily 200 times and see whether 'live' is
  // reachable without passing through 'calibrating'.
  const seen = new Set(['draft']);
  const walk = (state, trail) => {
    if (trail.length > 6) return;
    for (const to of ['schema_ok', 'calibrating', 'live', 'demoted', 'draft']) {
      const probe = new ModuleRegistry(); probe.register('p');
      let curr = 'draft', okAll = true;
      for (const step of [...trail, to]) {
        try { probe.transition('p', step); curr = step; } catch { okAll = false; break; }
      }
      if (!okAll) continue;
      hops++;
      if (curr === 'live') path.push([...trail, to]);
      seen.add(curr);
      walk(curr, [...trail, to]);
    }
  };
  walk('draft', []);
  ok(`every one of the ${path.length} paths to live passes through calibrating`,
    path.length > 0 && path.every((p) => p.includes('calibrating')));
  ok('no path reaches live in fewer than three transitions',
    path.every((p) => p.length >= 3));
}

/* --- side door 2: promote a mentor by mutating the record you were handed - */
{
  const a = new AgentRegistry();
  a.register('joyce', '1.0.0', { evals: { pass: false } });
  const handed = a.get('joyce');
  try { handed.versions['1.0.0'].evals.pass = true; } catch { /* strict mode throws */ }
  let promoted = false;
  try { a.promote('joyce', '1.0.0'); promoted = true; } catch { /* refused */ }
  ok('a caller cannot flip the eval result it was handed and then promote on it',
    promoted === false && a.get('joyce').versions['1.0.0'].evals.pass === false);
  ok('the record it holds is frozen all the way down, not just at the top level',
    Object.isFrozen(handed) && Object.isFrozen(handed.versions['1.0.0'].evals));
}

/* --- side door 3: advance a rollout while the network is halted ----------- */
{
  const audit = new AuditLog();
  const parity = new ParityMonitor({ audit });
  const stop = new StopConditions({ audit, parity });
  const r = new RolloutManager({ parity, stop, audit });
  parity.report('a', { n: 100, gatePassRate: 0.9 });
  parity.report('b', { n: 100, gatePassRate: 0.89 });
  parity.run();
  stop.evaluate({ driftPointsPerWeek: 20, driftedItemShare: 0.9 });
  r.start('sneak', { kind: 'content' });
  let reached = 0;
  for (let i = 0; i < 50; i++) if (r.advance('sneak', { dwellHours: 1e6 }).ok) reached++;
  ok('fifty attempts against a halted network advance a rollout exactly zero times',
    reached === 0);
}

/* --- side door 4: starve the parity job and keep shipping ----------------- */
{
  const audit = new AuditLog();
  const parity = new ParityMonitor({ audit });
  const stop = new StopConditions({ audit, parity });
  const s = new Scheduler({ audit });
  const r = new RolloutManager({ parity, stop, audit });
  s.on('calibration_sweep', () => {});     // everything BUT parity
  r.start('starve', { kind: 'content' });
  let advanced = 0;
  for (let week = 0; week < 4; week++) {
    s.tick(604_800_000);
    stop.evaluate({}, { now: Date.now() });
    if (r.advance('starve', { dwellHours: 1e6 }).ok) advanced++;
  }
  ok('a network whose parity job never runs stops shipping on its own',
    advanced <= 1 && stop.halted === true);
}

/* --- side door 5: buy your way out of a degraded plane -------------------- */
{
  const g = new CostGovernor({ budgets: { conversation: 100, factory: 100 } });
  g.spend('conversation', 1e9);
  let admitted = 0;
  for (let i = 0; i < 1000; i++) if (g.admit('conversation', 1).ok) admitted++;
  ok('a massively over-budget conversation plane still serves, at the smallest tier',
    admitted === 1000 && g.tierFor('conversation') === 'minimal');
  g.spend('factory', 1e9);
  ok('the factory plane pauses instead, and no retry count changes that',
    Array.from({ length: 100 }, () => g.admit('factory', 1).ok).every((x) => x === false));
}

/* --- side door 6: a graph revision that silently drops a prerequisite ----- */
{
  const gr = new SkillGraphRegistry();
  gr.publish('1.0.0', { nodes: 33, edges: 40 });
  let sneaked = false;
  for (const bad of [undefined, null, '', 0, false]) {
    try { gr.publish('9.9.9', { nodes: 1, edges: 0, migration: bad }); sneaked = true; } catch { /* refused */ }
  }
  ok('no falsy value passes as a migration script',
    sneaked === false && gr.current().graphVersion === '1.0.0');
}

console.log(`\n${n} adversarial checks passed.`);
