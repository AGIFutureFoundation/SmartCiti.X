/**
 * ACP-06 — Assessment, mastery verification and anti-gaming.
 *
 * The rule that shapes everything here: BKT alone never certifies. A posterior
 * is a belief; a gate needs demonstrated, unaided performance at or above the
 * learner's own level. Propagated graph credit (ACP-15) explicitly does not
 * count — a learner is certified on what they showed, not what was inferred.
 */

export const GATE = {
  masteryThreshold: 0.95,
  consecutiveUnaided: 3,
  atOrAbove: -5,          // demonstrations must be at >= theta - 5 (band top)
  levelTest: { questions: 33, passPct: 80, retakeLockHours: 12 },
};

export const ANTIGAMING = {
  guessSpamSeconds: 3,
  guessSpamRun: 3,
  hintFarmRate: 0.5,
  hintFarmDepth: 4,
  wheelSpinAttempts: 10,
};

/**
 * Skill gate (spec §6.1 tier 1).
 *
 * A gate is AWARDED, not continuously recomputed. Once a learner has shown
 * three consecutive unaided demonstrations at level, that happened; a later
 * re-test that goes badly does not un-certify them as a side effect of a
 * query. Revocation is a deliberate act with its own policy (`revokeSkillGate`),
 * not a silent consequence of asking the question again.
 */
export function checkSkillGate(profile, skillId, history = []) {
  const s = profile.get(skillId);
  if (s.gated_at !== undefined) {
    return { skill: skillId, pass: true, believed: true, demonstrated: true,
             awarded_at: s.gated_at, why: 'gate previously awarded' };
  }
  // Count QUALIFYING attempts only — unaided, served at gate difficulty.
  //
  // Two rules, both learned the hard way in curriculum simulation:
  //
  // 1. Ordinary practice sits at the band centre by design and can never
  //    qualify, so a practice item landing between two verifications must not
  //    break the streak. Practice does not invalidate proof; a failed
  //    demonstration does.
  // 2. Qualification is stamped AT SERVE TIME (`h.gate_qualifying`), never
  //    recomputed against current theta. Recomputing meant that as a learner
  //    improved, theta rose and their own past demonstrations retroactively
  //    stopped counting — improvement disqualified the evidence for it, and
  //    nothing ever certified.
  const qualifying = history.filter(
    (h) => h.skill === skillId && h.rung === 0 &&
      (h.gate_qualifying ?? h.difficulty >= s.theta + GATE.atOrAbove));
  const recent = qualifying.slice(-GATE.consecutiveUnaided);
  const demonstrated =
    recent.length === GATE.consecutiveUnaided && recent.every((h) => h.correct);
  const believed = s.p_mastery >= GATE.masteryThreshold;
  const pass = believed && demonstrated;
  if (pass && s.gated_at === undefined) s.gated_at = history.length;   // award it
  return {
    skill: skillId,
    pass,
    believed,
    demonstrated,
    why: !believed ? 'mastery posterior below threshold'
       : !demonstrated ? 'needs 3 consecutive unaided successes at level'
       : 'mastery believed and demonstrated',
  };
}

/** Level test (tier 2): fixed difficulty, no hints, shuffled per sitting. */
export function scoreLevelTest(answers) {
  const right = answers.filter(Boolean).length;
  const pct = (right / answers.length) * 100;
  return { right, of: answers.length, pct: +pct.toFixed(1),
           pass: pct >= GATE.levelTest.passPct };
}

/** Jobsite final (tier 3): rubric + the union agent's oral check. */
export function scoreJobsiteFinal({ stepOrder, safetyViolations, timeWithinTolerance, oralAnswers }) {
  const oral = oralAnswers.filter(Boolean).length;
  const pass = stepOrder >= 0.9 && safetyViolations === 0 && timeWithinTolerance && oral >= 2;
  return { pass, stepOrder, safetyViolations, timeWithinTolerance, oral,
           why: safetyViolations > 0 ? 'safety violation is disqualifying'
              : stepOrder < 0.9 ? 'procedure out of order'
              : !timeWithinTolerance ? 'outside time tolerance'
              : oral < 2 ? 'could not explain the why'
              : 'passed all three components' };
}

/** Certification requires all three tiers — no shortcuts. */
export function certified({ skillGates, levelTest, jobsiteFinal }) {
  return skillGates.every((g) => g.pass) && levelTest?.pass === true && jobsiteFinal?.pass === true;
}

/* ------------------------------------------------------------ anti-gaming */
export function detectGuessSpam(history) {
  const tail = history.slice(-ANTIGAMING.guessSpamRun);
  return tail.length === ANTIGAMING.guessSpamRun
    && tail.every((h) => !h.correct && (h.retryGapSec ?? 99) < ANTIGAMING.guessSpamSeconds);
}

export function detectHintFarming(history, window = 20) {
  const tail = history.slice(-window);
  if (tail.length < window) return false;
  const deep = tail.filter((h) => (h.rung ?? 0) >= ANTIGAMING.hintFarmDepth).length;
  return deep / tail.length > ANTIGAMING.hintFarmRate;
}

/**
 * Integrity flags go to a human. The spec is deliberate about this: automated
 * penalties for suspected answer-sharing punish the pattern, not the person,
 * and the pattern has innocent explanations.
 */
export function flagForReview(learnerId, kind, evidence) {
  return { learnerId, kind, evidence, action: 'instructor_review', automated_penalty: false };
}


/**
 * Deliberate revocation — for a failed recertification or an integrity finding.
 * Always logged with a reason; never a side effect of a query.
 */
export function revokeSkillGate(profile, skillId, reason) {
  const s = profile.get(skillId);
  const had = s.gated_at !== undefined;
  delete s.gated_at;
  return { skill: skillId, revoked: had, reason };
}
