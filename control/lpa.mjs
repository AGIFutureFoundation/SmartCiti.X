/**
 * ACP-02 — Learner Profile Agent.
 * Single writer of the proficiency vector. Deterministic, no LLM, no I/O.
 */

export const LOGISTIC_WIDTH = 12;      // spec §3.1
export const SIGMA_MAX = 15;
export const SIGMA_MIN = 3;
export const K_MAX = 12;

/** P(unaided success) for a learner at theta facing difficulty d. */
export const pSuccess = (theta, d) => 1 / (1 + Math.pow(10, (d - theta) / LOGISTIC_WIDTH));

/** Hint-rung credit (spec §4.1): rung 0 = unaided. */
export const RUNG_CREDIT = [1.0, 0.85, 0.7, 0.55, 0.4, 0.25];

const BKT_DEFAULT = { L0: 0.15, T: 0.10, G: 0.20, S: 0.10 };

/**
 * Evidence shrinkage on the mastery posterior.
 *
 * Raw BKT will report p_mastery > 0.95 after a handful of favourable
 * observations. Across a 33-node skill graph that is catastrophic: every skill
 * reads as mastered within a few attempts, the sequencer's frontier empties,
 * and the whole curriculum "completes" without the learner having learned
 * anything (measured: 33/33 skills believed mastered after 201 attempts).
 *
 * A belief held on three observations is not the same belief held on fifty.
 * The reported posterior is therefore shrunk toward the prior by how much
 * evidence stands behind it. Found in curriculum simulation, v1.3 -> v1.4.
 */
const MASTERY_EVIDENCE_K = 4;
export const shrinkMastery = (raw, n, L0 = BKT_DEFAULT.L0) =>
  L0 + (raw - L0) * (n / (n + MASTERY_EVIDENCE_K));

export function newSkillState(skillId, { theta = 35, sigma = SIGMA_MAX, bkt = BKT_DEFAULT } = {}) {
  return {
    skill_id: skillId,
    theta,
    sigma,
    p_mastery: bkt.L0,
    p_mastery_raw: bkt.L0,
    velocity: 0,
    half_life_days: 5,
    hint_dependence: 0,
    evidence_n: 0,
    consecutive_unaided: 0,
    bkt,
  };
}

export class LearnerProfile {
  constructor(learnerId, opts = {}) {
    this.learnerId = learnerId;
    this.skills = new Map();
    this.opts = opts;
    this.overrideActive = false;
  }

  get(skillId) {
    if (!this.skills.has(skillId)) this.skills.set(skillId, newSkillState(skillId, this.opts));
    return this.skills.get(skillId);
  }

  /**
   * Record one attempt. `rung` 0 = unaided. `weight` down-weights suspect
   * evidence (guess-spam 0.5, instructor override 0.3) per spec §2.2.
   */
  record(skillId, { difficulty, correct, rung = 0, weight = 1, guessSpam = false }) {
    const s = this.get(skillId);

    // Input guard at the profile boundary.
    //
    // A single non-finite difficulty used to set theta to NaN, and NaN is
    // absorbing: every later update, setpoint and gate decision on that learner
    // returned NaN for ever. One malformed telemetry event could silently
    // destroy a learner's record. ACP-01 §1.4 already says consumers must
    // tolerate malformed events; tolerating means REJECTING them, not ingesting
    // them. Rejections are counted rather than thrown, so a broken client shows
    // up in the numbers instead of taking a hall down. (Found by input fuzzing.)
    const d = Number(difficulty);
    if (!Number.isFinite(d)) {
      s.rejected_n = (s.rejected_n ?? 0) + 1;
      return { rejected: 'non-finite difficulty', outcome: 0, expected: 0, delta: 0, theta: s.theta };
    }
    difficulty = d;
    // A rung outside the ladder is a client bug, not extra credit or a crash.
    rung = Number.isFinite(rung) ? Math.max(0, Math.min(5, Math.trunc(rung))) : 0;
    weight = Number.isFinite(weight) ? Math.max(0, Math.min(1, weight)) : 1;
    correct = correct === true;
    const w = guessSpam ? Math.min(weight, 0.5) : (this.overrideActive ? Math.min(weight, 0.3) : weight);

    // graded outcome: a hinted success is partial evidence
    const outcome = correct ? RUNG_CREDIT[rung] : 0;
    const E = pSuccess(s.theta, difficulty);

    const K = Math.min(12, Math.max(2, K_MAX * (s.sigma / SIGMA_MAX)));
    const delta = K * w * (outcome - E);
    // theta lives on the same 0–100 scale as item difficulty; nothing outside
    // it is meaningful, and an unbounded theta drags the setpoint off-scale.
    s.theta = Math.max(0, Math.min(100, s.theta + delta));

    // BKT posterior; a hinted success inflates the guess parameter
    const { T, S } = s.bkt;
    const G = Math.min(0.85, s.bkt.G + rung * 0.15);
    const L = s.p_mastery_raw;   // recurse on raw; shrinkage is a reporting view
    const post = correct
      ? (L * (1 - S)) / (L * (1 - S) + (1 - L) * G)
      : (L * S) / (L * S + (1 - L) * (1 - G));
    s.p_mastery_raw = post + (1 - post) * T;

    // Uncertainty. Shrinks with evidence, but re-inflates when the learner
    // keeps surprising the model in one direction — that is a moving ability,
    // not noise, and a floor-bound sigma cannot track it (found in shadow-mode
    // simulation, v1.1 -> v1.2).
    s.surprise = 0.8 * (s.surprise ?? 0) + 0.2 * (outcome - E);
    const nonStationary = Math.abs(s.surprise) > 0.15;
    s.sigma = nonStationary
      ? Math.min(SIGMA_MAX, s.sigma + 0.6)
      : Math.max(SIGMA_MIN, s.sigma * 0.97);
    s.velocity = 0.3 * (delta * 10) + 0.7 * s.velocity;
    s.hint_dependence = 0.85 * s.hint_dependence + 0.15 * (rung > 0 ? rung / 5 : 0);
    s.evidence_n += 1;
    // reported mastery is the raw posterior, discounted by how thin the
    // evidence behind it is (see shrinkMastery)
    s.p_mastery = shrinkMastery(s.p_mastery_raw, s.evidence_n, s.bkt.L0);

    if (correct && rung === 0) s.consecutive_unaided += 1;
    else s.consecutive_unaided = 0;

    // retention half-life (spaced-retrieval update)
    s.half_life_days = correct
      ? s.half_life_days * 1.8
      : Math.max(2, s.half_life_days * 0.6);

    return { outcome, expected: E, delta, theta: s.theta };
  }

  /** Time away widens uncertainty and decays recallability (spec §2.2). */
  advanceDays(days) {
    for (const s of this.skills.values()) {
      s.sigma = Math.min(SIGMA_MAX, s.sigma + 0.15 * days);
    }
  }

  pRecall(skillId, daysSince) {
    const s = this.get(skillId);
    return Math.pow(2, -daysSince / s.half_life_days);
  }

  /** Skills between "started" and "done" — the sequencer's working set. */
  frontier() {
    return [...this.skills.values()].filter((s) => s.p_mastery >= 0.4 && s.p_mastery < 0.95);
  }
}
