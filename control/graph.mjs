/**
 * ACP-15 — Knowledge-graph tracing.
 *
 * The v1.2 control plane traced one skill at a time. Real competence is a
 * graph: evidence on one node is evidence about its neighbours, prerequisites
 * gate readiness, and confusable pairs actively corrupt each other. This layer
 * sits between the LPA and the sequencer.
 *
 * Governing rule — INDIRECT EVIDENCE IS NEVER DIRECT EVIDENCE. Propagated
 * credit moves theta but barely moves sigma, and never counts toward a gate.
 * A learner is certified on what they demonstrated, not on what was inferred
 * about them.
 */

export const TRANSFER = {
  toPrereq:   0.20,   // success on a child implies its prerequisite is sound
  fromPrereq: 0.10,   // ...and mastering a prereq slightly lifts its children
  supports:   0.10,   // soft transfer edges
  maxHops:    1,      // no graph-wide diffusion; one hop only
  sigmaShare: 0.15,   // indirect evidence shrinks sigma at 15% of direct rate
};

export const INTERFERENCE = {
  discount:   0.6,    // evidence weight when a confusable pair was just served
  windowN:    2,      // "just served" = within the last 2 attempts
};

export class SkillGraph {
  /** @param {Array} skills registry skills.json entries */
  constructor(skills) {
    this.nodes = new Map();
    for (const s of skills) this.nodes.set(s.skill_id, s);
    // reverse index: who requires me
    this.children = new Map();
    for (const s of skills) {
      for (const p of s.requires ?? []) {
        if (!this.children.has(p)) this.children.set(p, []);
        this.children.get(p).push(s.skill_id);
      }
    }
  }

  node(id) { return this.nodes.get(id) ?? null; }
  requires(id) { return this.node(id)?.requires ?? []; }
  supports(id) { return this.node(id)?.supports ?? []; }
  interferes(id) { return this.node(id)?.interferes ?? []; }
  childrenOf(id) { return this.children.get(id) ?? []; }

  /** A skill is ready when every hard prerequisite is mastered (spec §5.1). */
  ready(id, profile, threshold = 0.8) {
    return this.requires(id).every((p) => profile.get(p).p_mastery >= threshold);
  }

  /** How many locked skills this one unblocks — the `graph_leverage` term. */
  leverage(id, profile, threshold = 0.8) {
    return this.childrenOf(id).filter((c) => !this.ready(c, profile, threshold)).length;
  }

  /**
   * Propagate one attempt's evidence to neighbours. Returns what moved, so the
   * audit log can show why a skill the learner never touched changed.
   */
  propagate(profile, skillId, delta, { correct }) {
    const moved = [];
    const push = (target, factor, why) => {
      if (!this.nodes.has(target)) return;
      const t = profile.get(target);
      const d = delta * factor;
      if (Math.abs(d) < 0.01) return;
      t.theta = Math.max(0, Math.min(100, t.theta + d));
      // indirect evidence barely reduces uncertainty
      t.sigma = Math.max(3, t.sigma * (1 - (1 - 0.97) * TRANSFER.sigmaShare));
      t.indirect_n = (t.indirect_n ?? 0) + 1;
      moved.push({ skill: target, delta: +d.toFixed(3), why });
    };

    for (const p of this.requires(skillId)) {
      push(p, TRANSFER.toPrereq,
        correct ? `succeeded on ${skillId}, which rests on this`
                : `struggled on ${skillId}, which rests on this`);
    }
    if (correct) {
      for (const c of this.childrenOf(skillId)) push(c, TRANSFER.fromPrereq, `${skillId} mastered`);
    }
    for (const s of this.supports(skillId)) push(s, TRANSFER.supports, `transfers from ${skillId}`);
    return moved;
  }

  /**
   * Interference discount: if a confusable sibling was served in the last few
   * attempts, this attempt's evidence is weaker — the learner may be answering
   * about the other one.
   */
  interferenceWeight(skillId, recentSkillIds) {
    const conf = new Set(this.interferes(skillId));
    const recent = recentSkillIds.slice(-INTERFERENCE.windowN);
    return recent.some((r) => conf.has(r)) ? INTERFERENCE.discount : 1;
  }

  /** Which prerequisite is the likeliest culprit when a learner is stuck. */
  diagnose(skillId, profile) {
    const prereqs = this.requires(skillId)
      .map((p) => ({ skill: p, p_mastery: profile.get(p).p_mastery }))
      .sort((a, b) => a.p_mastery - b.p_mastery);
    const weakest = prereqs[0];
    if (weakest && weakest.p_mastery < 0.8) {
      return { cause: 'prerequisite', skill: weakest.skill, p_mastery: weakest.p_mastery };
    }
    return { cause: 'skill_itself', skill: skillId };
  }
}
