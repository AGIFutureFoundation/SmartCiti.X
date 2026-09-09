/**
 * Security tests. Every one of these is an attack or a mistake that would end
 * a company that holds training records, written as a refusal that must happen.
 */
import assert from 'node:assert/strict';
import { AuditLog } from '../bus/audit.mjs';
import { Authorizer, AccessDenied, principal, grant, ROLES, CAPABILITIES } from './authz.mjs';
import { RateLimiter, BUCKETS } from './ratelimit.mjs';
import { PrivacyService, CLASS, NEVER_EXPORT } from './privacy.mjs';

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

console.log(`\n${n} checks passed.`);
