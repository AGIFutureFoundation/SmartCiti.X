/* swarm/gate.mjs - the router's one door to safety_gate/. It calls canEnter() only: canEnter is pure and writes nothing, and
 * this file never calls enter(), grantOverride() or issuePermit(), so a routed command cannot mint an override or a permit.
 * A simulated robot is not a person: its actor record holds no induction, no PPE check and no passed tier, and the gate
 * answers for it exactly as it would for a learner with none. The 'now' the gate reads is the fixed dry-run instant from
 * the swarm registry, so the answer does not depend on a clock. */
import { canEnter, loadIndex } from '../safety_gate/gate.mjs';
import { sha256 } from './audit.mjs';

/* The no-record rule. A target the gate holds no record for (a headless arena world) may proceed ONLY as a dry run in
 * simulation. In any other mode, and on any future path toward a real target, it HOLDS with this reason. A deny holds
 * in every mode. Today no other mode is reachable (the router refuses real hardware first); the rule is kept in code so a
 * later path cannot inherit the dry-run allowance. */
export const NO_RECORD_RULE = Object.freeze({ proceeds_only_in: 'dry-run', hold_reason: 'no safety record for this target: held' });
export function gateDecision(verdict, mode) {
  if (verdict === 'deny') return Object.freeze({ proceed: false, reason: null });
  if (verdict === 'no-record' && mode !== NO_RECORD_RULE.proceeds_only_in) return Object.freeze({ proceed: false, reason: NO_RECORD_RULE.hold_reason });
  return Object.freeze({ proceed: verdict === 'allow' || verdict === 'no-record', reason: null });
}

export function createGate({ root, epochMs, index } = {}) {
  const idx = index ?? loadIndex(root);
  const ctx = Object.freeze({ index: idx, now: epochMs, asOf: epochMs });
  return Object.freeze({
    stamps: idx.stamps,
    actorFor(robotId) {
      return Object.freeze({ id: 'simbot-' + sha256(robotId).slice(0, 16), tenant: 'sim', inductions: Object.freeze([]), passed: Object.freeze([]) });
    },
    /* one decision from the gate, frozen: { target, allow, via, code, reasons } */
    consult(actor, targetId) {
      const d = canEnter(actor, targetId, ctx);
      return Object.freeze({ target: targetId, allow: d.allow === true, via: d.via ?? null, code: String(d.reasons[0] ?? '').split(':')[0], reasons: Object.freeze([...d.reasons]) });
    },
  });
}
