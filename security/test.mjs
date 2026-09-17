/**
 * Security tests. Every one of these is an attack or a mistake that would end
 * a company that holds training records, written as a refusal that must happen.
 */
import assert from 'node:assert/strict';
import { AuditLog } from '../bus/audit.mjs';
import { Authorizer, AccessDenied, principal, grant, ROLES, CAPABILITIES } from './authz.mjs';
import { RateLimiter, BUCKETS } from './ratelimit.mjs';
import { PrivacyService, CLASS, NEVER_EXPORT } from './privacy.mjs';
import { ContestDesk, Throttled, CONTEST_OUTCOMES, ABUSE_KINDS, TRIAGE_ACTIONS,
         HUMAN_ONLY, REVOCATION_TOPIC, REVOCATION_WRITER } from './contest.mjs';
import { AGENT_ROLES } from './authz.mjs';
import { TOPIC_OWNERS } from '../bus/bus.mjs';
import { CostGovernor } from '../ops/jobs.mjs';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
const HERE = fileURLToPath(new URL('.', import.meta.url));
const ROOT = join(HERE, '..');

let n = 0; const ok = (m) => { n++; console.log(`  ok  ${m}`); };

/* ------------------------------------------------------ tenant isolation - */
{
  const audit = new AuditLog();
  const az = new Authorizer({ audit });
  const admin = principal({ id: 'a1', tenant: 'local-197', roles: ['tenant_admin'] });

  assert.equal(az.check(admin, 'learner.read.tenant', { tenant: 'local-197', learner: 'L9' }).allow, true);
  const cross = az.check(admin, 'learner.read.tenant', { tenant: 'local-455', learner: 'L9' });
  assert.equal(cross.allow, false);
  assert.equal(cross.reason, 'cross-tenant access');
  assert.equal(audit.entries({ action: 'authz.deny' }).length, 1, 'denials must be audited');
  ok('a tenant admin cannot read another tenant, however senior the role');
}

{
  const az = new Authorizer();
  // the highest role in one tenant is nobody in another
  const p = principal({ id: 'a', tenant: 't1', roles: ['tenant_admin'] });
  for (const cap of ['learner.read.tenant', 'audit.export', 'billing.manage']) {
    assert.equal(az.check(p, cap, { tenant: 't2' }).allow, false, `${cap} leaked across tenants`);
  }
  ok('holding a capability never implies holding it in another tenant');
}

/* ------------------------------------------------------------ least privilege */
{
  const az = new Authorizer();
  const learner = principal({ id: 'L1', tenant: 't1', roles: ['learner'] });
  assert.equal(az.check(learner, 'learner.read.self', { tenant: 't1', learner: 'L1' }).allow, true);
  assert.equal(az.check(learner, 'learner.read.self', { tenant: 't1', learner: 'L2' }).allow, false);
  for (const cap of ['profile.write', 'gate.certify', 'dial.override', 'audit.read', 'pii.reveal']) {
    assert.equal(az.check(learner, cap, { tenant: 't1' }).allow, false, `learner has ${cap}`);
  }
  ok('a learner can read only their own record and can change nothing');
}

{
  const az = new Authorizer();
  const inst = principal({ id: 'i1', tenant: 't1', roles: ['instructor'], assigned: ['L1', 'L2'] });
  assert.equal(az.check(inst, 'learner.read.assigned', { tenant: 't1', learner: 'L1' }).allow, true);
  const other = az.check(inst, 'learner.read.assigned', { tenant: 't1', learner: 'L99' });
  assert.equal(other.allow, false, 'an instructor must not read learners they were not assigned');
  ok('an instructor reads only their assigned learners, not the whole tenant');
}

{
  // The rule the whole agent fabric depends on, checked at the authz layer too.
  const az = new Authorizer();
  const agent = principal({ id: 'joyce', tenant: 't1', roles: ['mentor_agent'] });
  for (const cap of ['profile.write', 'dial.override', 'gate.certify',
                     'learner.read.tenant', 'audit.export', 'pii.reveal']) {
    assert.equal(az.check(agent, cap, { tenant: 't1' }).allow, false, `mentor agent has ${cap}`);
  }
  assert.equal(az.check(agent, 'content.read', { tenant: 't1' }).allow, true);
  ok('a mentor agent can read content and nothing else — enforced twice, in authz and on the bus');
}

{
  const az = new Authorizer();
  for (const [role, caps] of Object.entries(ROLES)) {
    assert.ok(!caps.includes('pii.reveal'), `${role} holds pii.reveal as a standing capability`);
  }
  ok('no standing role can reveal identity — it is granted per incident only');
}

{
  const audit = new AuditLog();
  const az = new Authorizer({ audit });
  const g = grant('pii.reveal', { minutes: 30, reason: 'INC-4412 duplicate record', approver: 'dpo@…' });
  const support = principal({ id: 's1', tenant: 't1', roles: ['support'], grants: [g] });
  assert.equal(az.check(support, 'pii.reveal', { tenant: 't1' }).allow, true);

  const expired = { ...g, expiresAt: Date.now() - 1000 };
  const stale = principal({ id: 's1', tenant: 't1', roles: ['support'], grants: [expired] });
  assert.equal(az.check(stale, 'pii.reveal', { tenant: 't1' }).allow, false, 'an expired grant must not work');
  assert.throws(() => grant('pii.reveal', { minutes: 30 }), /reason and an approver/);
  ok('elevation is time-boxed, needs a reason and an approver, and expires on its own');
}

{
  const az = new Authorizer();
  const p = principal({ id: 'x', tenant: 't1', roles: ['tenant_admin'] });
  assert.equal(az.check(p, 'not.a.capability', { tenant: 't1' }).allow, false);
  assert.equal(az.check(null, 'content.read').allow, false);
  assert.throws(() => principal({ id: 'x' }), /tenant/);
  assert.throws(() => az.require(p, 'pii.reveal', { tenant: 't1' }), AccessDenied);
  ok('unknown capabilities, missing principals and tenantless identities are all refused');
}

/* --------------------------------------------------------- rate limiting - */
{
  const audit = new AuditLog();
  let t = 0;
  const rl = new RateLimiter({ audit, now: () => t });
  for (let i = 0; i < BUCKETS.auth.capacity; i++) {
    assert.equal(rl.take('auth', 'user@example').allow, true);
  }
  const blocked = rl.take('auth', 'user@example');
  assert.equal(blocked.allow, false);
  assert.ok(blocked.retryAfterSec > 0, 'a refusal must say when to come back');
  assert.equal(audit.entries({ action: 'ratelimit.auth_throttled' }).length, 1);
  t += 300000;                                   // five minutes later
  assert.equal(rl.take('auth', 'user@example').allow, true);
  ok(`auth is capped at ${BUCKETS.auth.capacity} attempts per 5 minutes, throttling is audited, and it recovers`);
}

{
  let t = 0;
  const rl = new RateLimiter({ now: () => t });
  // exhaust the cheap bucket
  for (let i = 0; i < BUCKETS.api.capacity + 5; i++) rl.take('api', 'L1');
  // the expensive bucket must be untouched
  assert.equal(rl.take('agent', 'L1').allow, true,
    'a flood of cheap calls must not exhaust the agent budget');
  ok('buckets are separate: an API flood cannot spend the mentor-turn allowance');
}

{
  let t = 0;
  const rl = new RateLimiter({ now: () => t });
  rl.take('api', 'a'); rl.take('api', 'b');
  assert.equal(rl.state.size, 2);
  t += 7200000;
  assert.equal(rl.sweep(3600), 2, 'idle buckets must be swept');
  assert.equal(rl.state.size, 0);
  ok('idle rate-limit state is swept, so memory does not grow with every key ever seen');
}

/* -------------------------------------------------------------- privacy -- */
{
  const audit = new AuditLog();
  const pv = new PrivacyService({ audit });
  const az = new Authorizer({ audit });
  pv.enrol({ name: 'A. Welder', email: 'a@example.org' }, 'psu_9f3a');

  const support = principal({ id: 's1', tenant: 't1', roles: ['support'] });
  assert.throws(() => pv.reveal('psu_9f3a', { authorizer: az, principal: support }), AccessDenied,
    'identity lookup without the grant must fail');

  const g = grant('pii.reveal', { minutes: 15, reason: 'INC-1', approver: 'dpo' });
  const elevated = principal({ id: 's1', tenant: 't1', roles: ['support'], grants: [g] });
  const rec = pv.reveal('psu_9f3a', { authorizer: az, principal: elevated });
  assert.equal(rec.email, 'a@example.org');
  assert.equal(audit.entries({ action: 'privacy.pii_revealed' }).length, 1,
    'every identity lookup is an event on the record');
  ok('identity lookup requires an explicit grant and is logged every single time');
}

{
  const pv = new PrivacyService();
  pv.enrol({ name: 'B', email: 'b@example.org' }, 'psu_1');
  const r = pv.erase('psu_1');
  assert.equal(r.mappingRemoved, true);
  assert.equal(pv.isErased('psu_1'), true);
  const az = new Authorizer();
  const g = grant('pii.reveal', { minutes: 5, reason: 'x', approver: 'y' });
  const p = principal({ id: 's', tenant: 't1', roles: ['support'], grants: [g] });
  assert.equal(pv.reveal('psu_1', { authorizer: az, principal: p }), null,
    'after erasure there is nothing left to reveal');
  ok('erasure breaks the only link to a person — the behavioural record is then genuinely anonymous');
}

{
  const pv = new PrivacyService();
  const rows = [{ learner: 'psu_1', theta: 52, affect_state: 'ANXIETY', anxiety: 0.7, gate: true }];
  const out = pv.sanitiseExport(rows);
  assert.equal(out[0].theta, 52);
  for (const bad of NEVER_EXPORT) assert.equal(out[0][bad], undefined);
  assert.equal(Object.keys(out[0]).some((k) => k.includes('anxiety')), false);
  ok('affect never leaves in an export, whatever the caller asked for');
}

{
  const pv = new PrivacyService();
  assert.throws(() => pv.assertStorable({ learner: 'x', keystrokes: ['a', 'b'] }), /raw stream/);
  assert.throws(() => pv.assertStorable({ raw_video: 'blob' }), /raw stream/);
  assert.equal(pv.assertStorable({ learner: 'x', theta: 50 }), true);
  ok('raw keystroke and video streams are refused at the storage boundary, not merely discouraged');
}

{
  const pv = new PrivacyService();
  assert.equal(pv.expired(CLASS.AFFECT, 120), true, 'affect must expire soonest');
  assert.equal(pv.expired(CLASS.AFFECT, 30), false);
  assert.equal(pv.expired(CLASS.BEHAVIOURAL, 800), true);
  assert.equal(pv.expired(CLASS.BEHAVIOURAL, 400), false);
  assert.equal(pv.expired(CLASS.AGGREGATE, 99999), false, 'aggregates contain no individual');
  ok('retention is enforced per data class, with affect held shortest');
}

/* ------------------------------------------------- contest and abuse ---- */
const desk = () => {
  const audit = new AuditLog();
  let t = 0;
  const d = new ContestDesk({ audit, now: () => t });
  const learner = principal({ id: 'L1', tenant: 't1', roles: ['learner'] });
  const other = principal({ id: 'L2', tenant: 't1', roles: ['learner'] });
  const inst = principal({ id: 'i1', tenant: 't1', roles: ['instructor'], assigned: ['L1'] });
  const admin = principal({ id: 'h1', tenant: 't1', roles: ['hall_admin'] });
  const foreign = principal({ id: 'i9', tenant: 't2', roles: ['instructor', 'hall_admin', 'tenant_admin'] });
  const agent = principal({ id: 'joyce', tenant: 't1', roles: ['mentor_agent'] });
  const support = principal({ id: 's1', tenant: 't1', roles: ['support'] });
  return { audit, d, learner, other, inst, admin, foreign, agent, support, tick: (ms) => { t += ms; } };
};

{
  assert.throws(() => new ContestDesk({}), /audit log/);
  ok('a contest desk without an audit log cannot be built — a filing off the record did not happen');
}

{
  const { d, learner, other, agent, foreign } = desk();
  assert.throws(() => d.contest({ principal: learner, tenant: 't1', learner: 'L2', gate: 'rigging.sling-angle', reason: 'x' }),
    /own record/, 'contesting someone else\'s gate');
  assert.throws(() => d.contest({ principal: learner, tenant: 't2', learner: 'L1', gate: 'g', reason: 'x' }),
    /cross-tenant/, 'contesting across tenants');
  assert.throws(() => d.contest({ principal: other, tenant: 't1', learner: 'L1', gate: 'g', reason: 'x' }), AccessDenied);
  assert.throws(() => d.contest({ principal: foreign, tenant: 't1', learner: 'L1', gate: 'g', reason: 'x' }), AccessDenied);
  assert.throws(() => d.contest({ principal: agent, tenant: 't1', learner: 'joyce', gate: 'g', reason: 'x' }),
    /lacks gate.contest/, 'an agent cannot contest');
  assert.throws(() => d.contest({ principal: learner, tenant: 't1', learner: 'L1', gate: 'g', reason: '' }), /reason is required/);
  assert.throws(() => d.contest({ principal: learner, tenant: 't1', learner: 'L1', reason: 'x' }), /gate is required/);
  assert.equal(d.cases.size, 0, 'nothing was filed');
  ok('a contest is refused across tenants, against another learner\'s record, from an agent, or without its facts');
}

{
  const { d, audit, learner } = desk();
  const c = d.contest({ principal: learner, tenant: 't1', learner: 'L1', gate: 'rigging.sling-angle',
    reason: 'the examiner was my cousin, call me on 415-555-0199 or a@example.org' });
  assert.equal(c.status, 'open'); assert.equal(c.resolution, null); assert.equal(c.learner, 'L1');
  assert.ok(Object.isFrozen(c));
  assert.ok(!/415-555|example\.org/.test(c.reason), 'PII must not reach storage');
  assert.equal(c.redactions, 2);
  const e = audit.entries({ action: 'contest.filed' });
  assert.equal(e.length, 1); assert.ok(Object.isFrozen(e[0])); assert.equal(e[0].actor, 'L1');
  assert.ok(!JSON.stringify(e).includes('example.org'), 'nor the audit log');
  ok('a learner files a contest on their own gate: PII redacted before storage, the case frozen, the filing audited');
}

{
  const { d, learner, other, inst, admin, foreign, agent, support } = desk();
  const c = d.contest({ principal: learner, tenant: 't1', learner: 'L1', gate: 'g', reason: 'r' });
  for (const [who, why] of [[other, 'a learner'], [support, 'support'], [agent, 'an agent'], [foreign, 'another tenant\'s admin']]) {
    assert.throws(() => d.resolve(c.id, { principal: who, outcome: 'upheld', reason: 'x' }), AccessDenied, `${why} resolved a contest`);
  }
  const filerWithReview = principal({ id: 'L1', tenant: 't1', roles: ['learner', 'instructor'] });
  assert.throws(() => d.resolve(c.id, { principal: filerWithReview, outcome: 'upheld', reason: 'x' }), /cannot resolve their own/);
  assert.throws(() => d.resolve(c.id, { principal: inst, outcome: 'dismissed', reason: 'x' }), /unknown outcome/);
  assert.throws(() => d.resolve(c.id, { principal: inst, outcome: 'upheld', reason: '' }), /reason is required/);
  assert.throws(() => d.resolve('contest-999', { principal: inst, outcome: 'upheld', reason: 'x' }), /no case/);
  assert.equal(d.cases.get(c.id).status, 'open', 'every refusal left the case untouched');
  assert.ok(admin.caps.includes('gate.review') && inst.caps.includes('gate.review'));
  ok('resolving is refused without gate.review, from another tenant, by the filer, or with an outcome outside the closed set');
}

{
  const { d, audit, learner, inst } = desk();
  const c = d.contest({ principal: learner, tenant: 't1', learner: 'L1', gate: 'rigging.sling-angle', reason: 'r' });
  const up = d.resolve(c.id, { principal: inst, outcome: 'upheld', reason: 'demonstration reviewed, decision stands' });
  assert.equal(up.revocation, null); assert.equal(up.case.status, 'resolved');
  assert.equal(up.case.resolution.resolvedBy, 'i1'); assert.ok(Object.isFrozen(up.case) && Object.isFrozen(up.case.resolution));
  assert.throws(() => d.resolve(c.id, { principal: inst, outcome: 'overturned', reason: 'again' }), /already resolved/);
  const e = audit.entries({ action: 'contest.resolved' });
  assert.equal(e.length, 1); assert.equal(e[0].after.resolvedBy, 'i1'); assert.ok(Object.isFrozen(e[0]));
  ok('an upheld contest is attributed, audited, frozen, and cannot be resolved twice');
}

{
  const { d, learner, admin } = desk();
  const c = d.contest({ principal: learner, tenant: 't1', learner: 'L1', gate: 'rigging.sling-angle', reason: 'r' });
  const { revocation } = d.resolve(c.id, { principal: admin, outcome: 'overturned', reason: 'recorded at the wrong rung' });
  assert.ok(revocation && Object.isFrozen(revocation) && Object.isFrozen(revocation.payload));
  assert.equal(revocation.topic, REVOCATION_TOPIC);
  assert.equal(revocation.topic, 'gate.decision');
  assert.equal(revocation.publishAs, TOPIC_OWNERS['gate.decision'], 'addressed to the bus\'s single writer for the topic');
  assert.equal(REVOCATION_WRITER, 'assessment');
  assert.equal(revocation.payload.skill, 'rigging.sling-angle');
  assert.equal(revocation.payload.pass, false);
  assert.equal(revocation.payload.resolvedBy, 'h1');
  assert.deepEqual(Object.keys(revocation.apply), ['fn', 'skillId', 'reason']);
  assert.equal(revocation.apply.fn, 'revokeSkillGate');
  assert.ok(!admin.caps.includes('gate.certify') && !admin.caps.includes('gate.revoke'),
    'a reviewer neither certifies nor revokes directly — the instruction goes to the bus');
  ok('an overturned contest returns a revocation instruction for the bus\'s gate writer; security/ publishes nothing itself');
}

{
  const { d, audit, learner, tick } = desk();
  let refused = null;
  for (let i = 0; i < BUCKETS.api.capacity + 1; i++) {
    try { d.contest({ principal: learner, tenant: 't1', learner: 'L1', gate: `g${i}`, reason: 'r' }); }
    catch (e) { refused = e; break; }
  }
  assert.ok(refused instanceof Throttled && refused.retryAfterSec > 0);
  assert.equal(d.cases.size, BUCKETS.api.capacity);
  assert.equal(audit.entries({ action: 'contest.throttled' }).length, 1);
  tick(3_600_000);
  assert.ok(d.contest({ principal: learner, tenant: 't1', learner: 'L1', gate: 'later', reason: 'r' }).id);
  ok(`over-rate filings are refused after ${BUCKETS.api.capacity}, audited, and recover through the api bucket`);
}

{
  const { d, audit, learner, inst, support, agent, foreign } = desk();
  assert.throws(() => d.report({ principal: agent, subject: 'L1', kind: 'harassment', detail: 'x' }), /lacks abuse.report/);
  assert.throws(() => d.report({ principal: learner, subject: 'L2', kind: 'spam', detail: 'x' }), /unknown kind/);
  assert.throws(() => d.report({ principal: learner, subject: 'L2', kind: 'harassment', detail: '' }), /detail is required/);
  const r = d.report({ principal: learner, subject: 'L2', kind: 'harassment',
    detail: 'sent me their number 415-555-0100 and kept messaging' });
  assert.ok(Object.isFrozen(r) && r.status === 'open' && r.tenant === 't1' && r.reporter === 'L1');
  assert.ok(!r.detail.includes('415-555'), 'PII redacted before storage');
  assert.equal(audit.entries({ action: 'abuse.reported' }).length, 1);
  for (const [who, re] of [[learner, /lacks abuse.triage/], [inst, /lacks abuse.triage/], [agent, /lacks abuse.triage/], [foreign, /cross-tenant/]]) {
    assert.throws(() => d.triage(r.id, { principal: who, action: 'dismissed', note: 'x' }), re);
  }
  assert.throws(() => d.triage(r.id, { principal: support, action: 'ignored', note: 'x' }), /unknown action/);
  assert.throws(() => d.triage(r.id, { principal: support, action: 'escalated', note: '' }), /note is required/);
  const reporterTriaging = principal({ id: 'L1', tenant: 't1', roles: ['learner', 'support'] });
  assert.throws(() => d.triage(r.id, { principal: reporterTriaging, action: 'dismissed', note: 'x' }), /cannot triage their own/);
  const t = d.triage(r.id, { principal: support, action: 'escalated', note: 'to the hall admin, reach me at s1@example.org' });
  assert.equal(t.status, 'triaged'); assert.equal(t.triage.triagedBy, 's1'); assert.ok(Object.isFrozen(t.triage));
  assert.ok(!t.triage.note.includes('example.org'));
  const e = audit.entries({ action: 'abuse.triaged' });
  assert.equal(e.length, 1); assert.equal(e[0].after.triagedBy, 's1'); assert.ok(Object.isFrozen(e[0]));
  assert.throws(() => d.triage(r.id, { principal: support, action: 'dismissed', note: 'x' }), /already triaged/);
  ok('abuse: any human reports (PII redacted, audited); only support/tenant_admin triage, never across tenants, never their own report');
}

{
  const { d, learner, audit } = desk();
  let refused = null;
  for (let i = 0; i < BUCKETS.api.capacity + 1; i++) {
    try { d.report({ principal: learner, subject: 'L2', kind: 'other', detail: 'd' }); } catch (e) { refused = e; break; }
  }
  assert.ok(refused instanceof Throttled);
  assert.equal(audit.entries({ action: 'abuse.throttled' }).length, 1);
  ok('over-rate abuse reports are refused and audited too');
}

{
  for (const role of AGENT_ROLES) for (const cap of HUMAN_ONLY) {
    assert.ok(!ROLES[role].includes(cap), `${role} holds ${cap}`);
  }
  assert.ok(!ROLES.mentor_agent.includes('gate.review') && !ROLES.mentor_agent.includes('abuse.triage'));
  const humans = Object.keys(ROLES).filter((r) => !AGENT_ROLES.includes(r));
  for (const r of humans) assert.ok(ROLES[r].includes('abuse.report'), `${r} cannot report abuse`);
  assert.deepEqual(Object.keys(ROLES).filter((r) => ROLES[r].includes('gate.review')).sort(), ['hall_admin', 'instructor']);
  assert.deepEqual(Object.keys(ROLES).filter((r) => ROLES[r].includes('abuse.triage')).sort(), ['support', 'tenant_admin']);
  assert.deepEqual(Object.keys(ROLES).filter((r) => ROLES[r].includes('gate.contest')), ['learner']);
  for (const [role, caps] of Object.entries(ROLES)) assert.ok(!caps.includes('pii.reveal'), `${role} now holds pii.reveal`);
  assert.deepEqual([...CONTEST_OUTCOMES], ['upheld', 'overturned']);
  assert.ok(Object.isFrozen(CONTEST_OUTCOMES) && Object.isFrozen(ABUSE_KINDS) && Object.isFrozen(TRIAGE_ACTIONS));
  ok('after the role edits: no agent role holds a human-only route, review and triage are held exactly where stated, and pii.reveal is still held by nobody');
}

/* ---------------------------------------------- SECURITY.md is one truth -- */
{
  const pointer = readFileSync(join(HERE, 'SECURITY.md'), 'utf8');
  const root = readFileSync(join(ROOT, 'SECURITY.md'), 'utf8');
  assert.ok(pointer.split('\n').filter(Boolean).length <= 4, 'the pack copy is a pointer, not a document');
  assert.ok(pointer.includes('../SECURITY.md'), 'the pointer names the root file');
  assert.ok(!pointer.includes('## Threat model') && pointer !== root, 'the pack copy must never be a second copy again');
  assert.ok(root.includes('## Threat model'));
  ok('security/SECURITY.md is a pointer to the root SECURITY.md, never a second copy');
}

{
  const whole = readFileSync(join(ROOT, 'SECURITY.md'), 'utf8');
  // Only the two sections whose rows carry a status cell; the module table
  // describes what a module enforces, not whether it exists.
  const section = (h) => { const i = whole.indexOf(h); assert.ok(i >= 0, `no ${h}`); return whole.slice(i, whole.indexOf('\n## ', i + 1)); };
  const root = (section('## Threat model') + section('## Launch checklist')).split('\n');
  // Things that exist in the packs may not still be described as not built.
  const built = [
    [/cost governor/i, typeof CostGovernor === 'function'],
    [/contest/i, typeof ContestDesk === 'function'],
    [/SBOM/, existsSync(join(HERE, 'registry', 'sbom.cdx.json'))],
  ];
  for (const [re, exists] of built) {
    assert.ok(exists, `${re} is expected to exist`);
    const lines = root.filter((l) => re.test(l) && /\|/.test(l));   // table rows only
    assert.ok(lines.length > 0, `SECURITY.md has no table row naming ${re}`);
    for (const l of lines) {
      // Both tables carry the status in the third cell: Threat | Mitigation |
      // Status, and # | Item | Status | Accepted by.
      const status = l.split('|')[3]?.trim() ?? '';
      assert.ok(!/not built|specified, not built/i.test(status), `SECURITY.md still says not built: ${l}`);
      assert.ok(/tested/.test(status), `SECURITY.md row status does not say tested: ${l}`);
    }
  }
  const accepted = root.filter((l) => /^\| \d+[ab]? \|/.test(l));
  assert.ok(accepted.length >= 9, 'the launch checklist is a status table');
  for (const l of accepted) {
    const cells = l.split('|').map((c) => c.trim());
    assert.equal(cells[cells.length - 2], '', `an "Accepted by" cell is filled — no owner is named by this pass: ${l}`);
  }
  ok('SECURITY.md calls nothing "not built" that the packs export, and names no owner it does not have');
}

{
  const root = readFileSync(join(ROOT, 'SECURITY.md'), 'utf8');
  const m = root.match(/ships with (\d+) checks in `test\.mjs`/);
  assert.ok(m, 'SECURITY.md states this suite\'s check count');
  assert.equal(Number(m[1]), n + 1, `SECURITY.md says ${m[1]} checks; this run has ${n + 1}`);
  ok('SECURITY.md states this suite\'s check count and it is the count that ran');
}

console.log(`\n${n} checks passed.`);
