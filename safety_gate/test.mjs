#!/usr/bin/env node
/**
 * Safety Gate tests. Every bypass must be refused, every legitimate entry
 * admitted, every override that opened a door must be on the chained log
 * with its actor, reason and expiry, and the chain must catch tampering.
 *
 *   node safety_gate/test.mjs
 */
import { AuditLog } from '../bus/audit.mjs';
import { Bus } from '../bus/bus.mjs';
import { loadIndex, canEnter, enter, grantOverride, SafetyLedger, PERMIT_CLASSES, PREFIX } from './gate.mjs';
import { buildFixtures, fullLearner, fullContext, people, ISSUER, PROVENANCE_ATTACKS, T0, TENANT, LEARNER } from './bypass_fixtures.mjs';
import { createIssuer } from './gate.mjs';

let n = 0; let failed = 0;
const ok = (cond, msg, detail = '') => {
  n++;
  if (cond) console.log(`  ok ${msg}`);
  else { failed++; console.log(`  FAIL ${msg}${detail ? `\n       ${detail}` : ''}`); }
};

const index = loadIndex();
const world = () => {
  let now = T0;
  const audit = new AuditLog({ clock: () => now, limit: Number.MAX_SAFE_INTEGER });
  const ledger = new SafetyLedger({ audit, clock: () => now, issuer: ISSUER });
  return { index, ledger, audit, set: (t) => { now = t; } };
};

/* ------------------------------------------------ classification --- */
const targets = [...index.targets.values()];
const haz = targets.filter((t) => t.hazardous);
const st = targets.filter((t) => t.kind === 'station');
const sims = targets.filter((t) => t.kind === 'sim');
const tally = (list) => {
  const why = {};
  for (const t of list) for (const r of t.reasons) {
    const k = r.startsWith('permit:') ? r.split(' ')[0] : r.split(':')[0];
    why[k] = (why[k] ?? 0) + 1;
  }
  return why;
};
console.log(`hazard classification (derived from stations/sims/surfaces registries):`);
console.log(`  stations: ${st.filter((t) => t.hazardous).length}/${st.length} hazardous`);
console.log(`  sim seats (sim x hall): ${sims.filter((t) => t.hazardous).length}/${sims.length} hazardous across ${new Set(sims.map((t) => t.sim)).size} sims`);
console.log(`  reasons: ${JSON.stringify(tally(haz))}`);
const perm = {}; for (const t of haz) for (const p of t.permits) perm[p] = (perm[p] ?? 0) + 1;
console.log(`  permit-class targets: ${JSON.stringify(perm)}`);
console.log(`  open (not hazardous): ${targets.filter((t) => !t.hazardous).map((t) => t.id).join(', ')}`);

ok(index.disagreements.length === 0, 'every station\'s room_ppe/room_hazards equals the surfaces conditions record it was derived from',
  index.disagreements.join(', '));
ok(haz.length > 0 && haz.length < targets.length, `classification discriminates: ${haz.length} of ${targets.length} targets hazardous, the rest open`);
ok(targets.filter((t) => t.reasons.some((r) => r.startsWith('room-hazard:'))).every((t) => t.hazardous),
  'every target whose room carries a surfaces hazard is classed hazardous');
ok(st.filter((t) => t.strand === 'safety' && t.tier === 'fundamentals').every((t) => !t.safetySkills.includes(`${t.hall}.safety.fundamentals`)),
  'an induction-tier safety station never requires itself as its own prerequisite');
ok(Object.keys(PERMIT_CLASSES).every((cls) => haz.some((t) => t.permits.includes(cls))) || Object.keys(perm).length >= 3,
  `permit classes are found in the registries' own text/room hazards (${Object.keys(perm).join(', ')})`);
ok(haz.every((t) => t.permits.every((p) => (t.permitEvidence[p] ?? []).length > 0)),
  'every permit requirement carries the registry evidence (room hazard or phrase) that triggered it');

/* ------------------------------------------------------- fixtures --- */
const fixtures = buildFixtures(index);
const bypass = fixtures.filter((f) => f.expect === 'block');
const legit = fixtures.filter((f) => f.expect === 'allow');
const fixturesAgain = buildFixtures(index);
ok(fixturesAgain.length === fixtures.length && fixturesAgain.every((f, i) => f.id === fixtures[i].id),
  `fixture generation is deterministic (${fixtures.length} fixtures, same ids on a second build)`);
ok(bypass.length >= 300, `>=300 scripted bypass attempts (${bypass.length} across ${new Set(bypass.map((f) => f.family)).size} families)`);
ok(legit.length >= 50, `>=50 legitimate entries (${legit.length})`);

const results = fixtures.map((f) => {
  const w = world();
  let d; let err = null;
  try { d = f.run(w); } catch (e) { err = e; d = { allow: false, reasons: [`threw: ${e.message}`] }; }
  return { f, d, w, err };
});
const wrongBlock = results.filter((r) => r.f.expect === 'block' && r.d.allow);
const wrongAllow = results.filter((r) => r.f.expect === 'allow' && !r.d.allow);
const crashed = results.filter((r) => r.err);
ok(wrongBlock.length === 0, `blocked ${bypass.length - wrongBlock.length}/${bypass.length} bypass attempts (100% required)`,
  wrongBlock.slice(0, 5).map((r) => `${r.f.id}: ${r.d.reasons.join(' | ')}`).join('\n       '));
ok(wrongAllow.length === 0, `allowed ${legit.length - wrongAllow.length}/${legit.length} legitimate entries (100% required)`,
  wrongAllow.slice(0, 5).map((r) => `${r.f.id}: ${r.d.reasons.join(' | ')}`).join('\n       '));
ok(crashed.length === 0, 'no fixture throws - the gate refuses, it does not crash', crashed.slice(0, 3).map((r) => `${r.f.id}: ${r.err?.message}`).join('; '));

const codeMiss = results.filter((r) => r.f.expect === 'block' && r.f.expectCode
  && !r.d.reasons.some((x) => x.startsWith(`${r.f.expectCode}:`)));
ok(codeMiss.length === 0, 'every refusal names the rule that refused it (induction/ppe/permit/tier/override/unknown-target/stale-context)',
  codeMiss.slice(0, 5).map((r) => `${r.f.id} wanted ${r.f.expectCode}: ${r.d.reasons.join(' | ')}`).join('\n       '));
ok(results.every((r) => r.d.allow || r.d.reasons.length > 0) && results.filter((r) => r.d.allow && r.d.via !== 'open').every((r) => r.d.required.length > 0),
  'every decision carries reasons, and every hazardous admission lists what was required');

/* ----------------------------------------------- override auditing --- */
const viaOverride = results.filter((r) => r.d.allow && r.d.via === 'override');
const auditMiss = viaOverride.filter((r) => {
  const granted = r.w.ledger.rows(`${PREFIX}override.granted`).find((e) => e.after.override_id === r.d.override_id);
  const consumed = r.w.ledger.rows(`${PREFIX}override.consumed`).find((e) => e.after.override_id === r.d.override_id);
  return !(granted && consumed && granted.actor === granted.after.actor && granted.after.actor_roles.includes('instructor')
    && granted.why.length >= 12 && granted.after.expires_at > granted.after.issued_at
    && consumed.after.actor && consumed.after.reason && consumed.after.expires_at);
});
ok(viaOverride.length > 0 && auditMiss.length === 0,
  `every override that admitted someone (${viaOverride.length}) is on the log as granted AND consumed, with actor, reason and expiry`,
  auditMiss.map((r) => r.f.id).join(', '));
ok(results.filter((r) => r.d.allow && r.d.via === 'override').every((r) => r.w.ledger.rows(`${PREFIX}allow`).some((e) => e.after.override_id === r.d.override_id)),
  'every override-admission is also recorded as a gate allow row naming the override');
const refusedOverrides = results.filter((r) => ['learner-self-override', 'peer-learner-override', 'mentor-agent-override', 'agent-with-instructor-role', 'hall-admin-override',
  'support-override', ...PROVENANCE_ATTACKS.map(([f]) => `${f}-override`), 'unassigned-instructor-override', 'cross-tenant-instructor-override',
  'override-no-reason', 'override-whitespace-reason', 'override-too-long'].includes(r.f.family));
ok(refusedOverrides.every((r) => r.w.ledger.rows(`${PREFIX}override.refused`).length > 0 && r.w.ledger.rows(`${PREFIX}override.granted`).length === 0),
  `refused override requests are logged as refused and never as granted (${refusedOverrides.length} attempts)`);
ok(results.filter((r) => !r.err && r.w.ledger.rows(`${PREFIX}override.granted`).length).every((r) => r.f.family === 'override-tampered-ledger' || r.w.ledger.verify().ok),
  'the chained log verifies after every fixture that was not deliberately tampered');

/* ---------------------------------------------------- provenance --- */
{
  const prov = results.filter((r) => PROVENANCE_ATTACKS.some(([f]) => r.f.family === `${f}-override` || r.f.family === `${f}-permit`));
  const fam = new Set(prov.map((r) => r.f.family.replace(/-(override|permit)$/, '')));
  ok(fam.size === PROVENANCE_ATTACKS.length && prov.every((r) => !r.d.allow),
    `provenance attacks refused at override AND permit issuance (${prov.length} attempts, ${fam.size} families: forged full-caps, authz.principal() direct, spread/cloned/structuredClone copies, thawed copy, second issuer)`);
  const rowsOf = (r, a) => r.w.ledger.rows(`${PREFIX}${a}`);
  ok(prov.every((r) => {
    const kind = r.f.family.endsWith('-override') ? 'override' : 'permit';
    const refused = rowsOf(r, `${kind}.refused`).filter((e) => /provenance/.test(e.why));
    const granted = kind === 'override' ? rowsOf(r, 'override.granted').length
      : rowsOf(r, 'permit.issued').filter((e) => e.actor !== people.instructor.id || e.after.actor !== people.instructor.id).length;
    return refused.length > 0 && granted === 0 && r.w.ledger.verify().ok;
  }), 'every provenance refusal is audited on the chained log (naming provenance) and nothing is granted to the impostor');

  const w = world(); const t = haz.find((x) => x.kind === 'station');
  const req = (actor) => grantOverride(w.ledger, index, { actor, learner: LEARNER, learnerTenant: TENANT,
    target: t.id, reason: 'supervised first entry, instructor at elbow', minutes: 10 });
  ok(people.forgedInstructor.caps.length === people.instructor.caps.length && !req(people.forgedInstructor).ok,
    'a hand-built principal with the complete ROLES.instructor capability set is refused');
  ok(!req(people.authzInstructor).ok && /provenance/.test(req(people.authzInstructor).why),
    'a principal from security/authz.mjs principal() with roles [instructor], not minted by the issuer, is refused');
  ok(!req(people.rogueIssuerInstructor).ok && createIssuer().vouches(people.instructor) === false,
    'a principal minted by a different issuer is refused, and a fresh issuer does not vouch for ours');
  ok(Object.isFrozen(people.instructor) && ISSUER.vouches(people.instructor) && req(people.instructor).ok,
    'the issuer-minted instructor is frozen, vouched for, and still grants a legitimate override');
  const bare = new SafetyLedger({ audit: new AuditLog({ clock: () => T0, limit: Number.MAX_SAFE_INTEGER }), clock: () => T0 });
  ok(!grantOverride(bare, index, { actor: people.instructor, learner: LEARNER, learnerTenant: TENANT, target: t.id,
    reason: 'supervised first entry, instructor at elbow', minutes: 10 }).ok && bare.rows(`${PREFIX}override.refused`).length === 1,
    'a ledger built without an issuer refuses every override (fail closed) and audits the refusal');
  let threw = false; try { new SafetyLedger({ issuer: { mint() {}, vouches: () => true } }); } catch { threw = true; }
  ok(threw, 'a ledger cannot be constructed with a look-alike issuer object');
  const hostile = new Proxy({}, { get() { throw new Error('boom'); } });
  let r2; try { r2 = req(hostile); } catch (e) { r2 = { ok: true, why: e.message }; }
  ok(!r2.ok, 'a hostile principal (throwing getters) is refused and audited, not crashed on');
}

/* ------------------------------------------------- chain tampering --- */
{
  const w = world(); const t = haz.find((x) => x.kind === 'station');
  const o = grantOverride(w.ledger, index, { actor: people.instructor, learner: LEARNER, learnerTenant: TENANT,
    target: t.id, reason: 'supervised induction catch-up', minutes: 20 }).override;
  const c = fullContext(w, t); c.override = o;
  const L = { ...fullLearner(t), inductions: [] };
  const d = enter(L, t.id, c);
  const v = w.ledger.verify();
  ok(d.allow && v.ok && v.rows >= 3, `a clean log verifies (${v.rows} chained rows, head ${v.head.slice(0, 12)}...)`);

  // rewrite history: change the reason on the granted row
  const head = w.ledger.head();
  const i = w.audit._entries.findIndex((e) => e.action === `${PREFIX}override.granted`);
  const orig = w.audit._entries[i];
  w.audit._entries[i] = Object.freeze({ ...orig, why: 'because I said so' });
  ok(!w.ledger.verify().ok, 'rewriting an override\'s reason after the fact breaks the chain');
  w.audit._entries[i] = orig;
  ok(w.ledger.verify({ expectHead: head }).ok, 'restoring the original row restores the chain to the published head');

  const removed = w.audit._entries.splice(i, 1)[0];
  ok(!w.ledger.verify().ok, 'deleting an override row from the log is detected');
  w.audit._entries.splice(i, 0, removed);

  w.audit._entries.push(Object.freeze({ seq: 777, ts: T0, actor: 'ins-kim', action: `${PREFIX}override.granted`,
    before: null, after: {}, why: 'inserted', learner: LEARNER, skill: t.id }));
  ok(!w.ledger.verify().ok, 'a gate row inserted around the chain is detected');
  w.audit._entries.pop();

  const c2 = fullContext(w, t); c2.override = o;
  ok(!canEnter(L, t.id, c2).allow && canEnter(L, t.id, c2).reasons.some((r) => /already used/.test(r)),
    'an override is single-use: the same token is refused after it opened the door once');

  const frozen = (() => { try { w.audit.entries()[0].why = 'x'; return false; } catch { return true; } })();
  ok(frozen || w.audit.entries()[0].why !== 'x', 'rows handed out by bus/audit.mjs are frozen - callers cannot edit them in place');
}

/* --------------------------------------------- purity and the bus --- */
{
  const w = world(); const t = haz[0];
  const c = fullContext(w, t);
  const before = w.audit.length;
  canEnter(fullLearner(t), t.id, c); canEnter(null, t.id, c); canEnter(fullLearner(t), 'nope', c);
  ok(w.audit.length === before, 'canEnter is pure: deciding never writes to the log');

  const audit = new AuditLog(); const bus = new Bus({ audit });
  const seen = []; bus.subscribe('override.applied', 'console', (m) => seen.push(m));
  const ledger = new SafetyLedger({ audit, bus, clock: () => T0, issuer: ISSUER });
  grantOverride(ledger, index, { actor: people.instructor, learner: LEARNER, learnerTenant: TENANT,
    target: t.id, reason: 'supervised first entry at this bay', minutes: 10 });
  ok(seen.length === 1 && seen[0].role === 'instructor_ui' && seen[0].payload.kind === 'safety_gate.override',
    'a granted override is published on the bus as override.applied by its single writer, instructor_ui');
}

console.log(`\n${n - failed}/${n} checks passed; ${bypass.length} bypass attempts blocked ${bypass.length - wrongBlock.length}, ${legit.length} legitimate entries allowed ${legit.length - wrongAllow.length}`);
if (failed) process.exit(1);
