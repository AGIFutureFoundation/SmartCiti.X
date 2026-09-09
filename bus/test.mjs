/**
 * Contract tests for the bus, telemetry and audit log.
 *
 * The point of these is not that the happy path works — it is that the rules
 * the spec states are ENFORCED. Each check below is a rule that was previously
 * only prose.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { Bus, ContractViolation, TOPIC_OWNERS } from './bus.mjs';
import { AuditLog } from './audit.mjs';
import { envelope, extractSignals, toXapi, MIN_USABLE_EVENTS, MAX_CLOCK_SKEW_MS } from './telemetry.mjs';
import { Session } from './session.mjs';
import { pSuccess } from '../control/lpa.mjs';

let n = 0; const ok = (m) => { n++; console.log(`  ok  ${m}`); };

/* -------------------------------------------------- single writer ------- */
{
  const bus = new Bus();
  let heard = 0;
  bus.subscribe('dial.setpoint', 'sequencer', () => heard++);
  bus.publish('dial.setpoint', 'dial', { c: 42 });
  assert.equal(heard, 1);
  // the rule the whole bus exists for
  assert.throws(() => bus.publish('dial.setpoint', 'mentor', { c: 99 }), ContractViolation);
  assert.throws(() => bus.publish('profile.updated', 'mentor', { theta: 99 }), ContractViolation);
  assert.throws(() => bus.publish('gate.decision', 'mentor', { pass: true }), ContractViolation);
  assert.equal(heard, 1, 'a refused publish must not reach subscribers');
  ok('a mentor cannot publish dial, profile or gate state — the bus refuses');
}

{
  const bus = new Bus();
  const mentorPub = bus.publisherFor('mentor');
  assert.throws(() => mentorPub('dial.setpoint', { c: 99 }), ContractViolation);
  assert.doesNotThrow(() => mentorPub('mentor.turn', { text: 'hi' }));
  ok('a bound publisher cannot claim a role it does not own');
}

{
  const bus = new Bus({ strict: false });
  const r = bus.publish('dial.setpoint', 'mentor', {});
  assert.equal(r.ok, false);
  assert.equal(r.violation, 'single_writer');
  assert.equal(bus.stats.violations, 1);
  ok('in non-strict mode a violation is contained and counted, not silent');
}

{
  const bus = new Bus();
  assert.throws(() => bus.publish('not.a.topic', 'dial', {}), ContractViolation);
  assert.throws(() => bus.subscribe('not.a.topic', 'x', () => {}), ContractViolation);
  ok('unknown topics are refused on both publish and subscribe');
}

/* --------------------------------------------------- delivery ----------- */
{
  const bus = new Bus();
  let got = 0;
  bus.subscribe('telemetry.event', 'lpa', () => got++);
  bus.publish('telemetry.event', 'client', { a: 1 }, { event_id: 'e1' });
  bus.publish('telemetry.event', 'client', { a: 1 }, { event_id: 'e1' });
  bus.publish('telemetry.event', 'client', { a: 2 }, { event_id: 'e2' });
  assert.equal(got, 2, 'at-least-once transport must be deduped on event_id');
  assert.equal(bus.stats.duplicates, 1);
  ok('duplicate deliveries are deduped on event_id and counted');
}

{
  const bus = new Bus();
  let second = 0;
  bus.subscribe('telemetry.event', 'a', () => { throw new Error('boom'); });
  bus.subscribe('telemetry.event', 'b', () => second++);
  bus.publish('telemetry.event', 'client', {});
  assert.equal(second, 1, 'one failing subscriber must not stop its siblings');
  assert.equal(bus.stats.violations, 1);
  ok('a throwing subscriber is contained; siblings still receive the message');
}

/* ---------------------------------------------------- telemetry --------- */
{
  const e = envelope({ learner_id: 'L', verb: 'completed', context: {}, ts: new Date().toISOString() });
  assert.equal(e.ts_source, 'client');
  assert.equal(e.context.modality, 'quiz', 'missing modality defaults to quiz');
  const skewed = envelope({ learner_id: 'L', verb: 'completed',
    ts: new Date(Date.now() + MAX_CLOCK_SKEW_MS * 10).toISOString() });
  assert.equal(skewed.ts_source, 'server', 'a badly skewed client clock must not order history');
  assert.ok(envelope({ verb: 'completed' }).error, 'an event without a learner is not an event');
  assert.ok(envelope({ learner_id: 'L', verb: 'teleported' }).error, 'unknown verbs are refused');
  ok('envelope applies the §1.4 guards: skew, defaults, and required fields');
}

{
  const mk = (i) => envelope({ learner_id: 'L', verb: 'completed', event_id: `x${i}`,
                              payload: { latency_ms: 5000 + i * 100 } });
  const few = extractSignals([mk(1), mk(2)]);
  assert.equal(few.usable, false, 'two events must not produce a profile update');
  const enough = extractSignals([mk(1), mk(2), mk(3)]);
  assert.equal(enough.usable, true);
  assert.equal(enough.acc, 1);
  const dup = extractSignals([mk(1), mk(1), mk(1), mk(2), mk(3)]);
  assert.equal(dup.deduped, 2, 'repeated event_ids are removed before counting');
  ok(`silence is not evidence: under ${MIN_USABLE_EVENTS} usable events yields no update`);
}

{
  const e = envelope({ learner_id: 'L', session_id: 'S', verb: 'completed',
    context: { module_id: 'u07.l11.s02.vr_sim.core', difficulty: 52, skill_ids: ['a'] },
    payload: { latency_ms: 8200 } });
  const st = toXapi(e);
  assert.equal(st.verb.id, 'http://adlnet.gov/expapi/verbs/completed');
  assert.equal(st.result.success, true);
  assert.ok(st.object.id.includes('u07.l11.s02'));
  assert.ok(JSON.stringify(st).indexOf('anxiety') === -1, 'affect must never appear in an export');
  ok('xAPI egress is an adapter on the same pipeline, and carries no affect data');
}

/* -------------------------------------------------------- audit --------- */
{
  const log = new AuditLog();
  const e = log.append({ actor: 'dial', action: 'step_up', why: 'because', learner: 'L' });
  assert.throws(() => { 'use strict'; e.why = 'tampered'; });
  const before = log.length;
  log.entries().push({ actor: 'x', action: 'y' });
  assert.equal(log.length, before, 'entries() must hand out a copy, not the log');
  assert.throws(() => log.append({ action: 'no actor' }));
  ok('the audit log is append-only and its entries cannot be rewritten');
}

/* --------------------------------------------- the loop over the bus ---- */
{
  const skills = JSON.parse(readFileSync(new URL('../pack/registry/skills.json', import.meta.url)))
    .skills.filter((s) => s.union === 'welders');
  let day = 0;
  const S = new Session({ skills, clock: () => day });
  for (let i = 0; i < 200; i++) {
    day = Math.floor(i / 6);
    if (i % 25 === 0) for (const k of S.dial.perSkill.keys()) S.dial.startSession(k);
    const p = S.next();
    if (!p) break;
    const st = S.profile.get(p.skill);
    S.attempt(p, { correct: Math.random() < pSuccess(st.theta + 3, p.difficulty) });
  }
  assert.equal(S.bus.stats.violations, 0, 'a clean run must produce no contract violations');
  assert.ok(S.audit.length > 50, `audit captured only ${S.audit.length} entries`);
  assert.ok(S.xapi.length > 100, 'xAPI egress should mirror the attempt stream');

  // every dial adaptation carries a reason, and the learner sees the same rows
  const dialRows = S.audit.entries({ actor: 'dial' });
  assert.ok(dialRows.length > 0);
  assert.ok(dialRows.every((e) => e.why && e.why.length > 10), 'every adaptation needs a why');
  const why = S.whyThis(5);
  assert.ok(why.length > 0 && why.every((w) => w.why));
  ok(`the loop ran over the bus: ${S.bus.stats.published} messages, ${S.audit.length} audit rows, 0 violations`);

  // and the mentor still cannot steer it, mid-session, with everything warm
  assert.throws(() => S.asMentor('dial.setpoint', { c: 5 }), ContractViolation);
  assert.throws(() => S.asMentor('gate.decision', { pass: true }), ContractViolation);
  ok('mid-session, a mentor still cannot write control state');
}



/* ------------------------------------------- ACP-04 on the evidence path -- */
const WELDERS = JSON.parse(readFileSync(new URL('../pack/registry/skills.json', import.meta.url)))
  .skills.filter((s) => s.union === 'welders');
{
  const s = new Session({ skills: WELDERS });
  const pick = s.seq.next(s.skillIds, s.history);
  pick.scaffold_ceiling = 1;
  const r = s.attempt(pick, { correct: true, rung: 5 });
  const rec = s.history[s.history.length - 1];
  assert.equal(rec.rung, 1, 'a rung above the ceiling must be recorded at the ceiling');
  assert.ok(s.audit.entries().some((e) => e.action === 'hint.over_ceiling'),
    'and the discrepancy must be kept, not silently corrected');
  ok('an over-ceiling rung is clamped on the evidence path and the discrepancy audited');
}

{
  const s = new Session({ skills: WELDERS });
  const pick = s.seq.next(s.skillIds, s.history);
  pick.scaffold_ceiling = 0;                       // a verification run
  const refused = s.requestHint(pick, { rung: 1 });
  assert.equal(refused.granted, 0);
  s.attempt(pick, { correct: true, rung: 3 });
  assert.equal(s.history[s.history.length - 1].rung, 0,
    'a hint-free task must record an unaided attempt or none at all');
  ok('a verification run cannot be talked into counting a hinted success');
}



/* --------------------------------- the mentor may not write the hint record */
{
  const s = new Session({ skills: WELDERS });
  let refused = false;
  try { s.bus.publisherFor('mentor')('hint.served', { skill: 'x', granted: 5 }); }
  catch (e) { refused = e.name === 'ContractViolation'; }
  assert.ok(refused, 'the mentor delivers help; it does not get to record how much');
  ok('a mentor cannot write the hint record — delivery and restraint are separate roles');
}

console.log(`\n${n} checks passed.`);
