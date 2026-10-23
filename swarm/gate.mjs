/* swarm/gate.mjs - the router's one door to safety_gate/. It calls canEnter() only: canEnter is pure and writes nothing, and
 * this file never calls enter(), grantOverride() or issuePermit(), so a routed command cannot mint an override or a permit.
 * A simulated robot is not a person: its actor record holds no induction, no PPE check and no passed tier, and the gate
 * answers for it exactly as it would for a learner with none. The 'now' the gate reads is the fixed dry-run instant from
 * the swarm registry, so the answer does not depend on a clock. */
import { canEnter, loadIndex } from '../safety_gate/gate.mjs';
import { sha256 } from './audit.mjs';

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
