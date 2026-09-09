/**
 * ACP-05 — Sequencing & next-task policy, plus ACP-15's review scheduler.
 *
 * The dial answers "how hard"; this answers "which skill, and why now". It is
 * the layer where adaptive systems usually cheat — serving whatever is next in
 * a list and calling the difficulty knob "adaptive". The policy here has to
 * defend every pick with a score and a reason.
 */
import { pSuccess } from './lpa.mjs';
import { masteryCeiling } from './hints.mjs';

export const WEIGHTS = {          // spec §5.2
  zpd_fit: 0.45, review_urgency: 0.25, graph_leverage: 0.15,
  modality_fit: 0.10, novelty: 0.05,
};
export const POLICY = {
  maxConsecutiveSameSkill: 3,     // interleaving beats blocking for retention
  reviewCadence: 4,               // 1 review item in every 4 when the queue is hot
  recallThreshold: 0.7,           // below this, a skill is due for review
  readyThreshold: 0.8,
  wheelSpinAttempts: 10,          // stuck detector
  wheelSpinProgress: 0.05,        // ...mastery movement below this over that span
  calibrationLadder: [25, 40, 55, 70, 85],
  verifyAtOrAbove: -5,            // gate-qualifying difficulty, relative to theta
  masteryBelieved: 0.95,
  verifyRun: 3,                   // consecutive unaided successes a gate needs
  verifyCooldown: 30,             // attempts to wait after a failed verification
  verifyMinEvidence: 8,           // never test a skill the learner has barely met
  verifyEveryN: 8,                // global budget: practice is the priority
  workingSetMax: 3,               // skills in active development at once (see ACP-15 sweep)
  graduateAt: 0.95,               // mastery at which a skill leaves the set
};

export class Sequencer {
  constructor(graph, profile, dial, { clock = () => 0 } = {}) {
    this.g = graph;
    this.p = profile;
    this.dial = dial;
    this.clock = clock;                 // days, injectable for simulation
    this.recentSkills = [];
    this.servedCount = new Map();
    this.lastSeen = new Map();          // skill -> day last practised
    this.attemptsSince = new Map();     // skill -> attempts since mastery check
    this.masteryAt = new Map();
    this.sinceReview = 0;
    this.calibration = new Map();       // skill -> ladder index during cold start
    this.verifyCooldown = new Map();    // skill -> attempt index it may be re-verified
    this.totalServed = 0;
    this.lastVerifyAt = -Infinity;
    this.activeVerify = null;           // {skill, hits} — a run in progress
    this.workingSet = new Set();
    this.log = [];
  }

  /* ------------------------------------------------------------- cold start */
  /** Wide binary search while sigma is high (spec §2.3). */
  calibrationPick(skillId) {
    const s = this.p.get(skillId);
    // Bounded by evidence only. Gating on sigma looked right until sigma
    // re-inflation (v1.2) started pushing established skills back into
    // placement, and calibration took 75% of all attempts.
    if (s.evidence_n >= POLICY.calibrationLadder.length) return null;
    const i = this.calibration.get(skillId) ?? 0;
    const d = POLICY.calibrationLadder[Math.min(i, POLICY.calibrationLadder.length - 1)];
    return { difficulty: d, reason: 'calibrating placement' };
  }

  advanceCalibration(skillId, correct) {
    const i = this.calibration.get(skillId) ?? 0;
    this.calibration.set(skillId, i + (correct ? 2 : 1));
  }

  /* ---------------------------------------------------------- review queue */
  reviewDue() {
    const now = this.clock();
    const out = [];
    for (const [id, st] of this.p.skills) {
      if (st.evidence_n < 5) continue;              // too new to be 'forgotten'
      const last = this.lastSeen.get(id);
      if (last === undefined) continue;
      const recall = Math.pow(2, -(now - last) / st.half_life_days);
      if (recall < POLICY.recallThreshold) out.push({ skill: id, recall });
    }
    return out.sort((a, b) => a.recall - b.recall);
  }

  /* ------------------------------------------------------- candidate pool  */
  frontier() {
    const out = [];
    for (const [id, st] of this.p.skills) {
      if (st.p_mastery >= 0.95) continue;
      if (!this.g.ready(id, this.p, POLICY.readyThreshold)) continue;
      out.push(id);
    }
    return out;
  }

  /**
   * The working set — skills in active development right now.
   *
   * Interleaving beats blocking for retention, but UNBOUNDED interleaving is
   * thrashing: when one root skill unlocks eleven strands at once, an attempt
   * budget spread across all of them leaves every skill under the practice it
   * needs and nothing masters. Measured: an unbounded frontier learned 0.67
   * skills against 6+ for a bounded one.
   *
   * So the sequencer holds at most `workingSetMax` skills open, admits a new
   * one only when another graduates, and interleaves WITHIN that set.
   */
  refreshWorkingSet() {
    for (const id of [...this.workingSet]) {
      if (this.p.get(id).p_mastery >= POLICY.graduateAt) this.workingSet.delete(id);
    }
    if (this.workingSet.size >= POLICY.workingSetMax) return;
    const ready = this.frontier().filter((id) => !this.workingSet.has(id));
    // admit by graph leverage first, then by how close the dial can place it
    const scored = ready.map((id) => ({
      id,
      lev: this.g.leverage(id, this.p, POLICY.readyThreshold),
      ev: this.p.get(id).evidence_n,
    })).sort((a, b) => b.lev - a.lev || b.ev - a.ev);
    for (const c of scored) {
      if (this.workingSet.size >= POLICY.workingSetMax) break;
      this.workingSet.add(c.id);
    }
  }

  /** Skills the learner has not started but whose prerequisites are met. */
  unlocked(allSkillIds) {
    return allSkillIds.filter((id) =>
      !this.p.skills.has(id) && this.g.ready(id, this.p, POLICY.readyThreshold));
  }

  /* ------------------------------------------------------------- scoring   */
  score(skillId, { reviewSet, modality = null }) {
    const st = this.p.get(skillId);
    const c = this.dial.setpoint(skillId);
    // zpd_fit: how close the dial can place this skill to the band centre
    const pAt = pSuccess(st.theta, c);
    const zpd_fit = Math.max(0, 1 - Math.abs(pAt - 0.775) / 0.275);
    const rev = reviewSet.get(skillId);
    const review_urgency = rev === undefined ? 0 : Math.min(1, (POLICY.recallThreshold - rev) / 0.7);
    const graph_leverage = Math.min(1, this.g.leverage(skillId, this.p, POLICY.readyThreshold) / 3);
    const modality_fit = modality ? 1 : 0.5;
    const seen = this.servedCount.get(skillId) ?? 0;
    const novelty = 1 / (1 + seen / 10);
    const total = WEIGHTS.zpd_fit * zpd_fit + WEIGHTS.review_urgency * review_urgency
      + WEIGHTS.graph_leverage * graph_leverage + WEIGHTS.modality_fit * modality_fit
      + WEIGHTS.novelty * novelty;
    return { total, zpd_fit, review_urgency, graph_leverage, modality_fit, novelty };
  }

  /* --------------------------------------------------------- verification */
  /**
   * The missing link between belief and certification.
   *
   * The dial holds practice at the band CENTRE (theta - 6.5) because that is
   * where learning happens. The skill gate only accepts demonstrations at the
   * band TOP (theta - 5) or harder. So a learner can be believed-mastered for
   * ever and never produce gate-qualifying evidence: normal practice is, by
   * construction, always 1.5 points too easy to count.
   *
   * Found in curriculum simulation (v1.3 -> v1.4). Fix: when mastery is
   * believed but undemonstrated, the sequencer deliberately serves a short
   * verification run at gate difficulty with hints closed. Practice optimises
   * for learning; verification optimises for proof. They are different jobs
   * and need different difficulties.
   */
  verificationPick(history, { ignoreBudget = false } = {}) {
    // Verification is a scarce resource, not a mode. Practice is what moves a
    // learner; proof is periodic. Without this budget, a fast-moving mastery
    // posterior across a 33-node graph keeps something permanently "ready to
    // test" and verification crowds out learning (48% of attempts, measured).
    // A run already in progress continues without paying the budget again:
    // three consecutive successes is the unit of proof, not one attempt.
    if (this.activeVerify) {
      const id = this.activeVerify.skill;
      const st = this.p.get(id);
      return { skill: id, difficulty: Math.max(this.dial.setpoint(id), st.theta + POLICY.verifyAtOrAbove),
               scaffold_ceiling: 0, mode: 'verify',
               why: `Verification run on ${short(id)} — ${this.activeVerify.hits}/${POLICY.verifyRun}.` };
    }
    if (!ignoreBudget && this.totalServed - this.lastVerifyAt < POLICY.verifyEveryN) return null;
    for (const [id, st] of this.p.skills) {
      if (st.gated_at !== undefined) continue;      // already certified
      if (st.p_mastery < POLICY.masteryBelieved) continue;
      // Belief alone is not readiness: require real evidence and at least one
      // unaided success before spending an attempt on proof.
      if (st.evidence_n < POLICY.verifyMinEvidence) continue;
      if (st.consecutive_unaided < 1) continue;
      // A failed verification means the belief was wrong. Send the learner back
      // to practice rather than re-testing them immediately -- without this the
      // system nags, and verification crowds out the learning it is meant to
      // certify (65% of attempts in the first curriculum run).
      if ((this.verifyCooldown.get(id) ?? 0) > this.totalServed) continue;
      const recent = history.filter((h) => h.skill === id).slice(-POLICY.verifyRun);
      const demonstrated = recent.length === POLICY.verifyRun && recent.every(
        (h) => h.correct && h.rung === 0 && h.difficulty >= st.theta + POLICY.verifyAtOrAbove);
      if (demonstrated) continue;
      return {
        skill: id,
        difficulty: Math.max(this.dial.setpoint(id), st.theta + POLICY.verifyAtOrAbove),
        scaffold_ceiling: 0,
        mode: 'verify',
        why: `You look ready on ${short(id)} — this one counts, no hints.`,
      };
    }
    return null;
  }

  /* -------------------------------------------------------------- next()   */
  /**
   * Pick the next skill. Returns {skill, difficulty, why, parts} — every pick
   * defends itself, because ACP-08 requires the "Why this?" surface to read
   * from the same decision the sequencer made.
   */
  next(allSkillIds, history = []) {
    return this.stamp(this.pick(allSkillIds, history));
  }

  /**
   * Every served task carries its own scaffold ceiling.
   *
   * It used to be stamped on verification picks alone, and the mentor filled
   * the gap with the most permissive value it could — so ordinary practice ran
   * with the whole ladder available no matter how well the learner knew the
   * skill, and ACP-04's fading rule never fired anywhere (v2.7 defect 14).
   *
   * A pick that already carries a ceiling keeps the tighter of the two: mode
   * (verification is hint-free because it is proof) and mastery (fading) are
   * independent bounds, and neither may loosen the other.
   */
  stamp(pick) {
    if (!pick) return pick;
    const fromMastery = masteryCeiling(this.p.get(pick.skill).p_mastery);
    const existing = pick.scaffold_ceiling;
    pick.scaffold_ceiling = existing === undefined
      ? fromMastery : Math.min(existing, fromMastery);
    return pick;
  }

  pick(allSkillIds, history = []) {
    // 1. wheel-spin check on the current skill takes priority over everything
    const spin = this.detectWheelSpin();
    if (spin) return spin;

    // 2. believed-mastered but undemonstrated: prove it, at gate difficulty
    const verify = this.verificationPick(history);
    if (verify) {
      if (!this.activeVerify) this.activeVerify = { skill: verify.skill, hits: 0 };
      this.log.push(verify);
      return verify;
    }

    this.refreshWorkingSet();
    const dueList = this.reviewDue();
    const reviewSet = new Map(dueList.map((d) => [d.skill, d.recall]));

    // 3. review cadence: 1 in 4 when the queue is non-empty
    let pool;
    let forcedReview = false;
    if (dueList.length && this.sinceReview >= POLICY.reviewCadence - 1) {
      pool = dueList.map((d) => d.skill);
      forcedReview = true;
    } else {
      pool = [...new Set([...this.workingSet, ...dueList.map((d) => d.skill)])];
    }
    if (!pool.length) pool = this.frontier().slice(0, POLICY.workingSetMax);
    if (!pool.length) pool = this.unlocked(allSkillIds).slice(0, POLICY.workingSetMax);
    if (!pool.length) {
      // Nothing ordinary left to practise. The verification budget exists to
      // stop proof crowding out practice -- with no practice to crowd out it
      // has nothing to protect, so spend it rather than serving the learner a
      // blank screen. (Soak test: the sequencer returned null and stalled the
      // whole hall at ~2,200 attempts with 25 of 33 skills still uncertified.)
      const v = this.verificationPick(history, { ignoreBudget: true });
      if (v) { if (!this.activeVerify) this.activeVerify = { skill: v.skill, hits: 0 }; this.log.push(v); return v; }
      // Still nothing: fall back to the least-certain uncertified skill, so the
      // learner keeps consolidating instead of falling off the end.
      const open = allSkillIds.filter((id) => this.p.get(id).gated_at === undefined);
      if (!open.length) return null;
      const weakest = open.reduce((a, b) =>
        this.p.get(a).sigma >= this.p.get(b).sigma ? a : b);
      const pick = { skill: weakest, difficulty: this.dial.setpoint(weakest), mode: 'consolidate',
                     poolSize: 1, why: `Keeping ${short(weakest)} sharp while the rest settles.` };
      this.log.push(pick);
      return pick;
    }

    // 4. interleaving constraint: no more than N in a row on one skill
    const tail = this.recentSkills.slice(-POLICY.maxConsecutiveSameSkill);
    const blocked = tail.length === POLICY.maxConsecutiveSameSkill
      && tail.every((s) => s === tail[0]) ? tail[0] : null;
    const eligible = pool.filter((s) => s !== blocked);
    const finalPool = eligible.length ? eligible : pool;

    // 5. score and take the best
    let best = null;
    for (const s of finalPool) {
      const parts = this.score(s, { reviewSet });
      if (!best || parts.total > best.parts.total) best = { skill: s, parts };
    }

    const cal = this.calibrationPick(best.skill);
    const difficulty = cal ? cal.difficulty : this.dial.setpoint(best.skill);
    const why = cal ? `Placing you on ${short(best.skill)} — finding your level.`
      : forcedReview ? `Bringing back ${short(best.skill)} before you lose it.`
      : best.parts.graph_leverage > 0.5 ? `${short(best.skill)} unlocks the next stage.`
      : best.parts.review_urgency > 0.3 ? `${short(best.skill)} is due for review.`
      : `Working ${short(best.skill)} at the edge of what you can do.`;

    // poolSize is on the record because the interleaving rule can only apply
    // when there is something to interleave WITH: early in a graph, one root
    // skill gates everything and a long run on it is correct, not a bug.
    const pick = { skill: best.skill, difficulty, why, parts: best.parts,
                   poolSize: finalPool.length,
                   mode: cal ? 'calibrating' : forcedReview ? 'review' : 'frontier' };
    this.log.push(pick);
    return pick;
  }

  /* ------------------------------------------------------- wheel-spinning  */
  /**
   * 10+ attempts, flat mastery, no gate progress. The humane response is NOT
   * more of the same: stop serving the skill and go find the prerequisite that
   * is actually missing (spec §6.2).
   */
  detectWheelSpin() {
    for (const [id, n] of this.attemptsSince) {
      if (n < POLICY.wheelSpinAttempts) continue;
      const st = this.p.get(id);
      const then = this.masteryAt.get(id) ?? 0;
      if (st.p_mastery - then > POLICY.wheelSpinProgress) { this.resetSpin(id); continue; }
      const dx = this.g.diagnose(id, this.p);
      this.resetSpin(id);
      if (dx.cause === 'prerequisite') {
        const pick = { skill: dx.skill, difficulty: this.dial.setpoint(dx.skill),
                       why: `${short(id)} isn't landing — stepping back to ${short(dx.skill)} first.`,
                       mode: 'remediation', diagnosis: dx };
        this.log.push(pick);
        return pick;
      }
      const pick = { skill: id, difficulty: this.dial.setpoint(id) - 8,
                     why: `Let's work ${short(id)} from a worked example.`,
                     mode: 'remediation', diagnosis: dx };
      this.log.push(pick);
      return pick;
    }
    return null;
  }

  resetSpin(id) {
    this.attemptsSince.set(id, 0);
    this.masteryAt.set(id, this.p.get(id).p_mastery);
  }

  /** Call after every attempt so the policy state stays honest. */
  record(skillId, { correct, mode = null }) {
    this.totalServed += 1;
    if (mode === 'verify') {
      this.lastVerifyAt = this.totalServed;
      if (!correct) {
        // A failed verification means the belief was wrong: end the run and
        // send the learner back to practice rather than re-testing.
        this.activeVerify = null;
        this.verifyCooldown.set(skillId, this.totalServed + POLICY.verifyCooldown);
      } else {
        const hits = (this.activeVerify?.skill === skillId ? this.activeVerify.hits : 0) + 1;
        this.activeVerify = hits >= POLICY.verifyRun ? null : { skill: skillId, hits };
      }
    }
    this.recentSkills.push(skillId);
    if (this.recentSkills.length > 20) this.recentSkills.shift();
    this.servedCount.set(skillId, (this.servedCount.get(skillId) ?? 0) + 1);
    this.lastSeen.set(skillId, this.clock());
    if (!this.masteryAt.has(skillId)) this.masteryAt.set(skillId, this.p.get(skillId).p_mastery);
    this.attemptsSince.set(skillId, (this.attemptsSince.get(skillId) ?? 0) + 1);
    const due = this.reviewDue().some((d) => d.skill === skillId);
    this.sinceReview = due ? 0 : this.sinceReview + 1;
    this.advanceCalibration(skillId, correct);
  }
}

const short = (id) => String(id).split('.').slice(-2).join(' ');
