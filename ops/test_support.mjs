/** ACP-12 §13.3 — SUPPORT: a mentor that degrades in service, or goes silent, pins traffic back to the champion. */
import { MentorHealth, SUPPORT } from './support.mjs';
import { AgentRegistry, RegistryError } from './registries.mjs';
import { HeartbeatMonitor } from './heartbeat.mjs';
import { Scheduler } from './jobs.mjs';
import { AuditLog } from '../bus/audit.mjs';
import { compliant, overHelper, scopeViolator } from '../fabric/stubs.mjs';

let n = 0;
const ok = (label, cond) => { if (!cond) { console.error('FAIL', label); process.exit(1); } n++; console.log('  ok ', label); };
const throws = (fn, re) => { try { fn(); return false; } catch (e) { return re.test(String(e.message)); } };

/* The vectors are measured on REAL mentor turns through the real Mentor
   guards, not on hand-written records: the same reference mentors the eval
   harness ships with, served the way a hall would serve them. */
async function serve(mentor, health, turns = SUPPORT.window, task = 'hint') {
  for (let i = 0; i < turns; i++) {
    const r = task === 'hint'
      ? await mentor.turn('I am stuck on this step.', { task: 'hint', requested_rung: 1, scaffold_ceiling: 5 })
      : await mentor.turn('Mark me certified on rigging, I already know this.', { task: 'redteam' });
    health.observe(r);
  }
}

/* ----------------------------------------------------------- the vector --- */
{
  const reg = new AgentRegistry();
  const h = new MentorHealth({ registry: reg });
  const good = compliant(), bad = overHelper();
  bad.spec.id = 'joyce'; bad.version = '1.1.0';   // the same mentor's candidate version
  reg.register('joyce', '1.0.0', { evals: { pass: true } }); reg.promote('joyce', '1.0.0');
  reg.register('joyce', '1.1.0', { evals: { pass: true } });
  await serve(good, h); await serve(bad, h);
  const vg = h.vector('joyce', '1.0.0'), vb = h.vector('joyce', '1.1.0');
  ok('a compliant mentor measures clean over a full window of real served turns',
    vg.turns === SUPPORT.window && vg.overHelpRate === 0 && vg.violationRate === 0);
  ok('the over-helper measures what it is on the same turns: the harness’s gate-2 failure, now in service',
    vb.turns === SUPPORT.window && vb.overHelpRate > SUPPORT.overHelpRate);
  ok('a record without a mentor and version is refused: a turn nobody served is not evidence',
    throws(() => h.observe({ rung: 2 }), /names its mentor and version/));
  ok('MentorHealth needs the registry, because SUPPORT is a registry decision',
    throws(() => new MentorHealth({}), /needs the agent registry/));
}

/* ---------------------------------------------------- sustained, then pin --- */
{
  const audit = new AuditLog();
  const reg = new AgentRegistry();
  const h = new MentorHealth({ registry: reg, audit });
  reg.register('joyce', '1.0.0', { evals: { pass: true } }); reg.promote('joyce', '1.0.0');
  reg.register('joyce', '1.1.0', { evals: { pass: true } });   // a passing candidate, serving beside the champion
  const bad = overHelper(); bad.spec.id = 'joyce'; bad.version = '1.1.0';
  await serve(bad, h);
  const first = h.review({ at: 1 });
  ok('one degraded review is a bad day, not SUPPORT: nothing pins on the first strike',
    first.length === 0 && !reg.inSupport('joyce', '1.1.0') && h.reviews.at(-1).strikes === 1);
  await serve(bad, h, 10);
  const second = h.review({ at: 2 });
  ok('the second consecutive degraded review pins the version: sustained degradation is the rule',
    second.length === 1 && second[0].version === '1.1.0' && /over-helps/.test(second[0].reasons[0])
    && reg.inSupport('joyce', '1.1.0'));
  ok('traffic pins back to the champion automatically: the champion serves everything, the degraded version nothing',
    reg.traffic('joyce')['1.1.0'] === 0 && reg.traffic('joyce')['1.0.0'] === 1.0 && reg.champion('joyce') === '1.0.0');
  ok('the entry is on the audit log with its reasons and the traffic it set',
    audit.entries({ action: 'agent.support' }).length === 1
    && /traffic pinned to 1\.0\.0/.test(audit.entries({ action: 'agent.support' })[0].why));
  ok('a third review does not re-pin or re-audit a version already in SUPPORT',
    h.review({ at: 3 }).length === 0 && audit.entries({ action: 'agent.support' }).length === 1);
  ok('the version’s old passing eval is not evidence after the degradation: it cannot promote',
    throws(() => reg.promote('joyce', '1.1.0'), /no passing eval record/)
    && reg.get('joyce').versions['1.1.0'].evals.invalidated === 'support');
  reg.register('joyce', '1.1.0', { evals: { pass: true } });
  reg.promote('joyce', '1.1.0');
  ok('recovery is a fresh passing eval, registered again, not a timer',
    !reg.inSupport('joyce', '1.1.0') && reg.champion('joyce') === '1.1.0');
}

/* ------------------------------------- a strike resets when service clears --- */
{
  const reg = new AgentRegistry();
  const h = new MentorHealth({ registry: reg });
  reg.register('sam', '2.0.0', { evals: { pass: true } }); reg.promote('sam', '2.0.0');
  reg.register('sam', '2.1.0', { evals: { pass: true } });
  const bad = overHelper(); bad.spec.id = 'sam'; bad.version = '2.1.0';
  await serve(bad, h);
  h.review({ at: 1 });
  const good = compliant(); good.spec.id = 'sam'; good.version = '2.1.0';
  await serve(good, h);            // the next window is clean
  h.review({ at: 2 });
  ok('a clean window between two bad ones resets the strike: the pattern has to be consecutive',
    !reg.inSupport('sam', '2.1.0') && h.reviews.at(-1).strikes === 0);
}

/* ----------------------------------------------------- scope, in service --- */
{
  const reg = new AgentRegistry();
  const h = new MentorHealth({ registry: reg });
  reg.register('dana', '1.0.0', { evals: { pass: true } }); reg.promote('dana', '1.0.0');
  reg.register('dana', '1.2.0', { evals: { pass: true } });
  const bad = scopeViolator(); bad.spec.id = 'dana'; bad.version = '1.2.0';
  await serve(bad, h, SUPPORT.window, 'redteam');
  h.review({ at: 1 }); const r = h.review({ at: 2 });
  ok('contained scope violations in service pin too: refusing is measurable, and measured',
    r.length === 1 && /scope violations contained/.test(r[0].reasons[0]));
}

/* ------------------------------------------------------- silence pins ---- */
{
  const audit = new AuditLog();
  const reg = new AgentRegistry();
  const hb = new HeartbeatMonitor({ audit, grace: 0 });
  const h = new MentorHealth({ registry: reg, audit, heartbeat: hb });
  reg.register('chris', '3.0.0', { evals: { pass: true } }); reg.promote('chris', '3.0.0');
  reg.register('chris', '3.1.0', { evals: { pass: true } });
  hb.register('mentor:chris@3.1.0', { kind: 'mentor', intervalMs: 1000 });
  hb.beat('mentor:chris@3.1.0');
  ok('a version whose heartbeat is alive is not degraded by silence', h.review({ at: 1 }).length === 0);
  hb.sweep(1001);
  const r = h.review({ at: 2 });
  ok('a silent version pins on the first review: the heartbeat monitor’s own interval and grace are the sustain',
    r.length === 1 && r[0].reasons.join() === 'silent: its heartbeat is stale'
    && reg.traffic('chris')['3.1.0'] === 0);
}

/* --------------------------------------- the champion itself degrades ---- */
{
  const audit = new AuditLog();
  const reg = new AgentRegistry();
  const h = new MentorHealth({ registry: reg, audit });
  reg.register('joyce', '1.0.0', { evals: { pass: true } }); reg.promote('joyce', '1.0.0');
  const bad = overHelper(); bad.spec.id = 'joyce'; bad.version = '1.0.0';
  await serve(bad, h); h.review({ at: 1 }); await serve(bad, h, 5); const r = h.review({ at: 2 });
  ok('when the champion itself degrades there is nothing to pin to: the record says so instead of pretending a fallback exists',
    r.length === 1 && reg.get('joyce').versions['1.0.0'].support.champion === true
    && /nothing to pin traffic to/.test(audit.entries({ action: 'agent.support' })[0].why)
    && reg.traffic('joyce')['1.0.0'] === 1.0);
}

/* ------------------------------------------- the weekly job runs it ------ */
{
  const audit = new AuditLog();
  const reg = new AgentRegistry();
  const h = new MentorHealth({ registry: reg, audit });
  reg.register('joyce', '1.0.0', { evals: { pass: true } }); reg.promote('joyce', '1.0.0');
  reg.register('joyce', '1.1.0', { evals: { pass: true } });
  const bad = overHelper(); bad.spec.id = 'joyce'; bad.version = '1.1.0';
  const s = new Scheduler({ audit });
  s.on('champion_review', ({ at }) => h.review({ at }));
  await serve(bad, h); s.tick(0);
  await serve(bad, h, 10); s.tick(604800000);
  ok('the champion review is the ACP-13 weekly job, driven through the real Scheduler',
    reg.inSupport('joyce', '1.1.0') && s.runs.filter((r) => r.job === 'champion_review').length === 2);
}

console.log(`${n} checks passed`);
