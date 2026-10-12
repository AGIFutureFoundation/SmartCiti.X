/**
 * Deterministic bypass attempts and legitimate entries for the Safety Gate.
 *
 * Every fixture is generated from the registry-derived index - the targets,
 * their PPE, permits and tiers are read, never typed - so a registry change
 * moves the fixtures with it. No randomness: the same registries yield the
 * same fixtures, in the same order.
 *
 * A fixture is { id, family, expect: 'block'|'allow', expectCode?, run(world) }
 * where run() returns the gate decision. `world` is a fresh ledger + clock +
 * index per fixture (see test.mjs), so fixtures cannot leak state into each other.
 */
import { principal } from '../security/authz.mjs';
import { grantOverride, issuePermit, enter, GATE, TIERS } from './gate.mjs';

export const T0 = Date.UTC(2026, 9, 12, 9, 0, 0);
const MIN = 60000;
const DAY = 86400000;

export const TENANT = 'hall-tenant-a';
export const LEARNER = 'lrn-ada';
export const OTHER = 'lrn-bo';

export const people = Object.freeze({
  instructor: principal({ id: 'ins-kim', tenant: TENANT, roles: ['instructor'], assigned: [LEARNER, OTHER] }),
  instructorUnassigned: principal({ id: 'ins-rae', tenant: TENANT, roles: ['instructor'], assigned: [OTHER] }),
  instructorOtherTenant: principal({ id: 'ins-lou', tenant: 'hall-tenant-b', roles: ['instructor'], assigned: [LEARNER] }),
  learnerSelf: principal({ id: LEARNER, tenant: TENANT, roles: ['learner'], assigned: [LEARNER] }),
  learnerPeer: principal({ id: OTHER, tenant: TENANT, roles: ['learner'], assigned: [LEARNER] }),
  mentorAgent: principal({ id: 'agent-mentor', tenant: TENANT, roles: ['mentor_agent'], assigned: [LEARNER] }),
  agentAsInstructor: principal({ id: 'agent-x', tenant: TENANT, roles: ['instructor', 'mentor_agent'], assigned: [LEARNER] }),
  hallAdmin: principal({ id: 'adm-joy', tenant: TENANT, roles: ['hall_admin'], assigned: [LEARNER] }),
  support: principal({ id: 'sup-max', tenant: TENANT, roles: ['support'], assigned: [LEARNER] }),
  // a hand-built object that claims the role but was not built by authz.principal
  forgedInstructor: Object.freeze({ id: 'ins-fake', tenant: TENANT, roles: ['instructor'], caps: [], assigned: [LEARNER] }),
});

/** A learner who has everything a target asks for. */
export function fullLearner(t, id = LEARNER) {
  return {
    id, tenant: TENANT,
    inductions: [{ scope: `hall:${t.hall}`, completed_at: T0 - 10 * DAY, expires_at: T0 + 300 * DAY }],
    passed: [...t.safetySkills],
  };
}
export const ppeCheck = (t, learner = LEARNER, at = T0 - MIN, items = t.ppe) =>
  ({ learner, target: t.id, at, items: [...items] });

/** Context with everything this learner needs, permits issued on the ledger. */
export function fullContext(w, t, { learner = LEARNER, now = T0 } = {}) {
  const permits = t.permits.map((cls) => {
    const r = issuePermit(w.ledger, w.index, { actor: people.instructor, learner, learnerTenant: TENANT,
                                               target: t.id, cls, minutes: 240 });
    if (!r.ok) throw new Error(`fixture setup: permit refused: ${r.why}`);
    return r.permit;
  });
  return { index: w.index, ledger: w.ledger, now, asOf: now - 1000, ppeCheck: ppeCheck(t, learner), permits };
}

/** An instructor override for a learner who is missing a credential. */
function override(w, t, { actor = people.instructor, learner = LEARNER, reason = 'supervised first entry, instructor at elbow', minutes = 20 } = {}) {
  return grantOverride(w.ledger, w.index, { actor, learner, learnerTenant: TENANT, target: t.id, reason, minutes });
}

const without = (o, k) => { const c = { ...o }; delete c[k]; return c; };

export function buildFixtures(index) {
  const all = [...index.targets.values()];
  const hazardous = all.filter((t) => t.hazardous).sort((a, b) => a.id.localeCompare(b.id));
  const safe = all.filter((t) => !t.hazardous).sort((a, b) => a.id.localeCompare(b.id));
  const permitT = hazardous.filter((t) => t.permits.length);
  const tierT = hazardous.filter((t) => t.safetySkills.length);
  const multiPpe = hazardous.filter((t) => t.ppe.length >= 2);
  const stations = hazardous.filter((t) => t.kind === 'station');
  // a deterministic spread across halls: first target per hall, then the rest
  const pick = (list, n) => {
    const seen = new Set(); const first = []; const rest = [];
    for (const t of list) (seen.has(t.hall) ? rest : (seen.add(t.hall), first)).push(t);
    return [...first, ...rest].slice(0, n);
  };
  const F = [];
  const add = (family, expect, t, run, expectCode = null) =>
    F.push({ id: `${family}#${F.filter((f) => f.family === family).length}:${t?.id ?? '-'}`, family, expect, expectCode, target: t?.id ?? null, run });

  /* ------------------------------------------------ bypass attempts ---- */
  for (const t of pick(hazardous, 30)) add('missing-induction', 'block', t, (w) => {
    const c = fullContext(w, t); return enter(without(fullLearner(t), 'inductions'), t.id, c); }, 'induction');

  for (const t of pick(hazardous, 15)) add('expired-induction', 'block', t, (w) => {
    const L = fullLearner(t); L.inductions = [{ scope: `hall:${t.hall}`, completed_at: T0 - 400 * DAY, expires_at: T0 - DAY }];
    return enter(L, t.id, fullContext(w, t)); }, 'induction');

  for (const t of pick(hazardous, 15)) add('wrong-hall-induction', 'block', t, (w) => {
    const other = hazardous.find((x) => x.hall !== t.hall && x.district !== t.district) ?? hazardous.find((x) => x.hall !== t.hall);
    const L = fullLearner(t); L.inductions = [{ scope: `hall:${other.hall}`, completed_at: T0 - DAY, expires_at: T0 + DAY }];
    return enter(L, t.id, fullContext(w, t)); }, 'induction');

  for (const t of pick(hazardous, 10)) add('future-dated-induction', 'block', t, (w) => {
    const L = fullLearner(t); L.inductions = [{ scope: `hall:${t.hall}`, completed_at: T0 + DAY, expires_at: T0 + 300 * DAY }];
    return enter(L, t.id, fullContext(w, t)); }, 'induction');

  for (const t of pick(hazardous.filter((x) => x.ppe.length), 30)) add('no-ppe-check', 'block', t, (w) => {
    const c = fullContext(w, t); delete c.ppeCheck; return enter(fullLearner(t), t.id, c); }, 'ppe');

  for (const t of pick(multiPpe, 30)) add('partial-ppe', 'block', t, (w) => {
    const c = fullContext(w, t); c.ppeCheck = ppeCheck(t, LEARNER, T0 - MIN, t.ppe.slice(1));
    return enter(fullLearner(t), t.id, c); }, 'ppe');

  for (const t of pick(multiPpe, 12)) add('ppe-case-tricks', 'block', t, (w) => {
    const c = fullContext(w, t);
    c.ppeCheck = ppeCheck(t, LEARNER, T0 - MIN, t.ppe.map((p, i) => (i === 0 ? ` ${p.toUpperCase()} ` : p)));
    return enter(fullLearner(t), t.id, c); }, 'ppe');

  for (const t of pick(multiPpe, 10)) add('ppe-wrong-gear', 'block', t, (w) => {
    const c = fullContext(w, t); c.ppeCheck = ppeCheck(t, LEARNER, T0 - MIN, ['bump cap', 'sunglasses', 'trainers']);
    return enter(fullLearner(t), t.id, c); }, 'ppe');

  for (const t of pick(hazardous.filter((x) => x.ppe.length), 10)) add('ppe-check-other-learner', 'block', t, (w) => {
    const c = fullContext(w, t); c.ppeCheck = ppeCheck(t, OTHER); return enter(fullLearner(t), t.id, c); }, 'ppe');

  for (const t of pick(hazardous.filter((x) => x.ppe.length), 10)) add('ppe-check-other-target', 'block', t, (w) => {
    const other = hazardous.find((x) => x.id !== t.id);
    const c = fullContext(w, t); c.ppeCheck = { ...ppeCheck(t), target: other.id }; return enter(fullLearner(t), t.id, c); }, 'ppe');

  for (const t of pick(hazardous.filter((x) => x.ppe.length), 8)) add('ppe-check-stale', 'block', t, (w) => {
    const c = fullContext(w, t); c.ppeCheck = ppeCheck(t, LEARNER, T0 - GATE.maxContextAgeMs - MIN);
    return enter(fullLearner(t), t.id, c); }, 'ppe');

  for (const t of pick(multiPpe, 8)) add('ppe-override-attempt', 'block', t, (w) => {
    const o = override(w, t).override; const c = fullContext(w, t);
    c.ppeCheck = ppeCheck(t, LEARNER, T0 - MIN, t.ppe.slice(1)); c.override = o;
    return enter(fullLearner(t), t.id, c); }, 'ppe');

  for (const t of permitT) {
    add('permit-missing', 'block', t, (w) => { const c = fullContext(w, t); c.permits = []; return enter(fullLearner(t), t.id, c); }, 'permit');
    add('permit-expired', 'block', t, (w) => {
      const c = fullContext(w, t, { now: T0 + 241 * MIN }); c.ppeCheck = ppeCheck(t, LEARNER, T0 + 240 * MIN);
      return enter(fullLearner(t), t.id, c); }, 'permit');
    add('permit-other-learner', 'block', t, (w) => {
      const c = fullContext(w, t, { learner: OTHER }); c.ppeCheck = ppeCheck(t);
      return enter(fullLearner(t), t.id, c); }, 'permit');
    add('permit-forged-unchained', 'block', t, (w) => {
      const c = fullContext(w, t); c.permits = c.permits.map((p) => ({ ...p, seq: p.seq + 1000 }));
      return enter(fullLearner(t), t.id, c); }, 'permit');
    add('permit-forged-edited-expiry', 'block', t, (w) => {
      const c = fullContext(w, t); c.permits = c.permits.map((p) => ({ ...p, expires_at: p.expires_at + 30 * DAY }));
      return enter(fullLearner(t), t.id, c); }, 'permit');
    add('permit-relabelled-learner', 'block', t, (w) => {
      const c = fullContext(w, t, { learner: OTHER }); c.ppeCheck = ppeCheck(t);
      c.permits = c.permits.map((p) => ({ ...p, learner: LEARNER }));
      return enter(fullLearner(t), t.id, c); }, 'permit');
    add('permit-wrong-station', 'block', t, (w) => {
      const other = permitT.find((x) => x.id !== t.id && x.permits.some((p) => t.permits.includes(p)));
      const c = fullContext(w, t);
      c.permits = other ? fullContext(w, other).permits : c.permits.map((p) => ({ ...p, target: 'st999' }));
      return enter(fullLearner(t), t.id, c); }, 'permit');
    add('permit-self-issued', 'block', t, (w) => {
      const c = fullContext(w, t);
      c.permits = t.permits.map((cls) => issuePermit(w.ledger, w.index, { actor: people.learnerSelf, learner: LEARNER,
        learnerTenant: TENANT, target: t.id, cls }).permit).filter(Boolean);
      return enter(fullLearner(t), t.id, c); }, 'permit');
    add('permit-agent-issued', 'block', t, (w) => {
      const c = fullContext(w, t);
      c.permits = t.permits.map((cls) => issuePermit(w.ledger, w.index, { actor: people.mentorAgent, learner: LEARNER,
        learnerTenant: TENANT, target: t.id, cls }).permit).filter(Boolean);
      return enter(fullLearner(t), t.id, c); }, 'permit');
  }

  for (const t of pick(tierT, 25)) add('skip-tier', 'block', t, (w) => {
    const L = fullLearner(t); L.passed = t.safetySkills.slice(0, -1); return enter(L, t.id, fullContext(w, t)); }, 'tier');

  for (const t of pick(tierT.filter((x) => x.safetySkills.length > 1), 10)) add('tier-wrong-hall', 'block', t, (w) => {
    const L = fullLearner(t); L.passed = t.safetySkills.map((s) => s.replace(`${t.hall}.`, 'other-hall.'));
    return enter(L, t.id, fullContext(w, t)); }, 'tier');

  for (const t of pick(tierT, 8)) add('tier-case-trick', 'block', t, (w) => {
    const L = fullLearner(t); L.passed = t.safetySkills.map((s) => s.toUpperCase()); return enter(L, t.id, fullContext(w, t)); }, 'tier');

  // overrides that must not allow - target lacks induction so only an override could open it
  const needsOverride = (w, t, o) => { const c = fullContext(w, t); c.override = o; return enter(without(fullLearner(t), 'inductions'), t.id, c); };
  const refusedTok = (r) => r.override ?? { forged: true, why: r.why };
  for (const t of pick(stations, 10)) {
    add('learner-self-override', 'block', t, (w) => needsOverride(w, t, refusedTok(override(w, t, { actor: people.learnerSelf }))), 'override');
    add('peer-learner-override', 'block', t, (w) => needsOverride(w, t, refusedTok(override(w, t, { actor: people.learnerPeer }))), 'override');
    add('mentor-agent-override', 'block', t, (w) => needsOverride(w, t, refusedTok(override(w, t, { actor: people.mentorAgent }))), 'override');
    add('agent-with-instructor-role', 'block', t, (w) => needsOverride(w, t, refusedTok(override(w, t, { actor: people.agentAsInstructor }))), 'override');
    add('hall-admin-override', 'block', t, (w) => needsOverride(w, t, refusedTok(override(w, t, { actor: people.hallAdmin }))), 'override');
    add('support-override', 'block', t, (w) => needsOverride(w, t, refusedTok(override(w, t, { actor: people.support }))), 'override');
    add('forged-principal-override', 'block', t, (w) => needsOverride(w, t, refusedTok(override(w, t, { actor: people.forgedInstructor }))), 'override');
    add('unassigned-instructor-override', 'block', t, (w) => needsOverride(w, t, refusedTok(override(w, t, { actor: people.instructorUnassigned }))), 'override');
    add('cross-tenant-instructor-override', 'block', t, (w) => needsOverride(w, t, refusedTok(override(w, t, { actor: people.instructorOtherTenant }))), 'override');
    add('override-no-reason', 'block', t, (w) => needsOverride(w, t, refusedTok(override(w, t, { reason: '' }))), 'override');
    add('override-whitespace-reason', 'block', t, (w) => needsOverride(w, t, refusedTok(override(w, t, { reason: '      ok      ' }))), 'override');
    add('override-too-long', 'block', t, (w) => needsOverride(w, t, refusedTok(override(w, t, { minutes: GATE.maxOverrideMinutes * 24 }))), 'override');
    add('override-expired', 'block', t, (w) => {
      const o = override(w, t, { minutes: 15 }).override;
      const c = fullContext(w, t, { now: T0 + 16 * MIN }); c.ppeCheck = ppeCheck(t, LEARNER, T0 + 15 * MIN); c.override = o;
      return enter(without(fullLearner(t), 'inductions'), t.id, c); }, 'override');
    add('override-replayed', 'block', t, (w) => {
      const o = override(w, t).override;
      const first = needsOverride(w, t, o);
      if (!first.allow) return { ...first, allow: true, reasons: ['fixture setup: first use should have allowed'] };
      return needsOverride(w, t, o); }, 'override');
    add('override-other-learner', 'block', t, (w) => needsOverride(w, t, override(w, t, { learner: OTHER }).override), 'override');
    add('override-other-target', 'block', t, (w) => {
      const other = hazardous.find((x) => x.id !== t.id);
      const o = grantOverride(w.ledger, w.index, { actor: people.instructor, learner: LEARNER, learnerTenant: TENANT,
        target: other.id, reason: 'supervised entry at the other bay', minutes: 20 }).override;
      return needsOverride(w, t, o); }, 'override');
    add('override-forged-extended', 'block', t, (w) => {
      const o = override(w, t, { minutes: 5 }).override;
      const c = fullContext(w, t, { now: T0 + 10 * MIN }); c.ppeCheck = ppeCheck(t, LEARNER, T0 + 9 * MIN);
      c.override = { ...o, expires_at: o.expires_at + DAY };
      return enter(without(fullLearner(t), 'inductions'), t.id, c); }, 'override');
    add('override-fabricated', 'block', t, (w) => needsOverride(w, t, {
      override_id: 'ovr-1-deadbeef', learner: LEARNER, target: t.id, actor: 'ins-kim', actor_roles: ['instructor'],
      reason: 'trust me, I am an instructor', issued_at: T0 - MIN, expires_at: T0 + 60 * MIN, seq: 0, hash: '0'.repeat(64) }), 'override');
    add('override-tampered-ledger', 'block', t, (w) => {
      const o = override(w, t).override;
      w.ledger.audit._entries.push(Object.freeze({ seq: 9999, ts: T0, actor: 'ins-kim', action: 'safety_gate.override.granted',
        before: null, after: { ...o, target: 'st000' }, why: 'slipped in', learner: LEARNER, skill: t.id }));
      return needsOverride(w, t, o); }, 'override');
  }

  // id tricks and unknowns
  const idTricks = (id) => [id.toUpperCase(), ` ${id}`, `${id} `, `${id}\n`, id.replace(/-/g, '_'), `${id}/`,
    id.replace(/^st/, 'ST'), `./${id}`, id.normalize('NFKD') + '​', `${id}%00`];
  for (const t of pick(hazardous, 12)) for (const v of idTricks(t.id).filter((x) => x !== t.id)) add('id-trick', 'block', t,
    (w) => enter(fullLearner(t), v, fullContext(w, t)), 'unknown-target');
  for (const bad of ['st999', 'st-001', 'sim:crane-lift', 'sim:crane-lift@nowhere', 'sim:moon-lander@welders', '', null, undefined, 42, {}, { id: 'ST001' }, ['st001'], '__proto__', 'constructor', 'st001;st000'])
    add('unknown-target', 'block', hazardous[0], (w) => enter(fullLearner(hazardous[0]), bad, fullContext(w, hazardous[0])), 'unknown-target');

  // learner-id tricks: credentials on a near-identical id
  for (const t of pick(stations, 8)) add('learner-id-trick', 'block', t, (w) => {
    const c = fullContext(w, t); const L = fullLearner(t); L.id = LEARNER.toUpperCase();
    c.ppeCheck = ppeCheck(t, L.id); return enter(L, t.id, c); });

  // stale / missing / future context
  for (const t of pick(hazardous, 10)) {
    add('stale-context', 'block', t, (w) => { const c = fullContext(w, t); c.asOf = c.now - GATE.maxContextAgeMs - 1; return enter(fullLearner(t), t.id, c); }, 'stale-context');
    add('future-context', 'block', t, (w) => { const c = fullContext(w, t); c.asOf = c.now + DAY; return enter(fullLearner(t), t.id, c); }, 'stale-context');
    add('no-clock', 'block', t, (w) => { const c = fullContext(w, t); delete c.now; return enter(fullLearner(t), t.id, c); }, 'stale-context');
  }
  add('no-context', 'block', hazardous[0], () => enter(fullLearner(hazardous[0]), hazardous[0].id, null), 'stale-context');
  add('no-learner', 'block', hazardous[0], (w) => enter(null, hazardous[0].id, fullContext(w, hazardous[0])), 'invalid-learner');

  // everything missing at once
  for (const t of pick(hazardous, 10)) add('bare-learner', 'block', t, (w) =>
    enter({ id: LEARNER, tenant: TENANT }, t.id, { index: w.index, ledger: w.ledger, now: T0, asOf: T0 }));

  /* --------------------------------------------- legitimate entries --- */
  for (const t of pick(hazardous, 45)) add('legit-credentials', 'allow', t, (w) => enter(fullLearner(t), t.id, fullContext(w, t)));
  for (const t of pick(hazardous.filter((x) => x.district), 6)) add('legit-district-induction', 'allow', t, (w) => {
    const L = fullLearner(t); L.inductions = [{ scope: `district:${t.district}`, completed_at: T0 - DAY, expires_at: T0 + DAY }];
    return enter(L, t.id, fullContext(w, t)); });
  for (const t of pick(multiPpe, 6)) add('legit-extra-ppe', 'allow', t, (w) => {
    const c = fullContext(w, t); c.ppeCheck = ppeCheck(t, LEARNER, T0 - MIN, [...t.ppe, 'ear plugs', 'knee pads']);
    return enter(fullLearner(t), t.id, c); });
  for (const t of pick(stations, 8)) add('legit-instructor-override', 'allow', t, (w) => {
    const o = override(w, t).override; const c = fullContext(w, t); c.override = o;
    return enter(without(fullLearner(t), 'inductions'), t.id, c); });
  for (const t of pick(permitT, 4)) add('legit-override-in-last-minute', 'allow', t, (w) => {
    const o = override(w, t, { minutes: 10 }).override;
    const c = fullContext(w, t, { now: T0 + 9 * MIN }); c.ppeCheck = ppeCheck(t, LEARNER, T0 + 8 * MIN); c.override = o;
    return enter({ ...fullLearner(t), passed: [] }, t.id, c); });
  for (const t of safe) add('legit-open-room', 'allow', t, (w) =>
    enter({ id: LEARNER, tenant: TENANT }, t.id, { index: w.index, ledger: w.ledger, now: T0, asOf: T0 }));

  return F;
}

export { TIERS };
