/**
 * ACP-04 — Scaffolding & hint engine.
 *
 * Help is a loan against mastery credit (P5), so this module owns three things
 * that were previously scattered or missing: what each rung costs, how high the
 * ladder reaches right now, and when a learner is leaning on it hard enough
 * that someone should say so.
 *
 * It exists because the fading rule in §4.2 was specified and implemented
 * nowhere. The sequencer stamped `scaffold_ceiling: 0` on verification picks
 * and omitted the field on every other pick; the mentor's clamp read
 * `ctx.scaffold_ceiling ?? 5` and so served the FULL ladder — up to
 * co-completion — to a learner at 0.94 mastery on ordinary practice. A default
 * that fills in the most permissive value is a safeguard that fails open
 * (v2.7 defect 14).
 *
 * The ceiling is therefore computed here, attached to every served task, and
 * the mentor's fallback is now the most restrictive value rather than the
 * loosest.
 */

/**
 * The ladder. `credit` is the mastery evidence a success at that rung is worth,
 * and it is the same schedule the dial uses to discount its success rate
 * (1 - 0.15 * rung) — one table, so a hint cannot be cheap in one subsystem and
 * expensive in another.
 */
export const RUNGS = [
  { rung: 0, name: 'unaided',      credit: 1.00, does: 'nothing' },
  { rung: 1, name: 'orient',       credit: 0.85, does: 'points at the part of the problem that matters' },
  { rung: 2, name: 'prompt',       credit: 0.70, does: 'asks the question the learner should be asking' },
  { rung: 3, name: 'worked step',  credit: 0.55, does: 'shows the first step; the learner finishes' },
  { rung: 4, name: 'demonstrate',  credit: 0.40, does: 'works a parallel problem end to end' },
  { rung: 5, name: 'co-complete',  credit: 0.25, does: 'completes it with the learner, narrating' },
];

export const HINT_POLICY = {
  dwellSeconds: 20,          // minimum since last action, per request (anti-mashing)
  maxRung: 5,
  fadeWindow: 20,            // attempts the dependence rate is measured over
  fadeThreshold: 0.35,       // sustained hint_dependence that opens a contract
  fadeContractTasks: 3,      // tasks served one rung lower than requested
  socraticMaxTurns: 6,
};

/** §4.2 fading: the ceiling shrinks as mastery grows. */
export function masteryCeiling(pMastery) {
  if (pMastery >= 0.95) return 0;
  if (pMastery >= 0.80) return 1;
  if (pMastery >= 0.50) return 3;
  return 5;
}

export function creditFor(rung) {
  const r = RUNGS[Math.max(0, Math.min(RUNGS.length - 1, Math.trunc(rung) || 0))];
  return r.credit;
}

/**
 * The single ceiling authority.
 *
 * `taskCeiling` is whatever the sequencer stamped on the served task. It is a
 * MODE constraint (a verification run is hint-free because it is proof, not
 * practice) and it is not derivable from mastery: verification happens between
 * 0.80 and 0.95, where the mastery rule still allows rung 1. The two bounds are
 * independent and the tighter one wins.
 */
export function ceilingFor({ pMastery, taskCeiling = null, fadeContract = 0 }) {
  let c = masteryCeiling(pMastery);
  if (taskCeiling !== null && taskCeiling !== undefined) c = Math.min(c, taskCeiling);
  if (fadeContract > 0) c = Math.max(0, c - 1);
  return Math.max(0, Math.min(HINT_POLICY.maxRung, c));
}

const CONCEPTUAL = new Set(['calc', 'theory', 'code', 'reading', 'planning', 'diagnosis']);

/** Motor and procedural skills get demonstration replays, not dialogue (§4.3). */
export function isConceptual(skill) {
  if (!skill) return false;
  if (skill.kind) return CONCEPTUAL.has(skill.kind);
  const id = String(skill.skill_id ?? skill);
  return [...CONCEPTUAL].some((k) => id.includes(k));
}

export class HintEngine {
  constructor(profile, cfg = {}) {
    this.p = profile;
    this.cfg = { ...HINT_POLICY, ...cfg };
    this.perSkill = new Map();
    this.log = [];
  }

  state(skillId) {
    if (!this.perSkill.has(skillId)) {
      this.perSkill.set(skillId, {
        window: [],            // 1 = attempt used a hint, 0 = unaided
        fadeContract: 0,       // tasks remaining under a fading contract
        contractsOpened: 0,
        dialogues: 0,
      });
    }
    return this.perSkill.get(skillId);
  }

  /** The ceiling for a task about to be served. */
  ceiling(skillId, taskCeiling = null) {
    const h = this.state(skillId);
    return ceilingFor({
      pMastery: this.p.get(skillId).p_mastery,
      taskCeiling,
      fadeContract: h.fadeContract,
    });
  }

  /**
   * A learner asks for help. Returns what they get and why — refusals are
   * explained, never silent, because an unexplained refusal reads as a bug
   * (P4 applies to the help ladder too).
   */
  request(skillId, { rung = 1, dwellSeconds = Infinity, taskCeiling = null, skill = null } = {}) {
    const h = this.state(skillId);
    const ceiling = this.ceiling(skillId, taskCeiling);
    const asked = Math.max(1, Math.min(this.cfg.maxRung, Math.trunc(rung) || 1));

    if (dwellSeconds < this.cfg.dwellSeconds) {
      const rec = { skillId, granted: 0, asked, ceiling, refused: 'dwell',
        why: `Give it another ${Math.ceil(this.cfg.dwellSeconds - dwellSeconds)} seconds before the next hint — the pause is where the thinking happens.` };
      this.log.push(rec);
      return rec;
    }
    if (ceiling === 0) {
      const verifying = taskCeiling === 0;
      const rec = { skillId, granted: 0, asked, ceiling, refused: verifying ? 'verification' : 'mastered',
        why: verifying
          ? 'This one is a check, not practice — it runs without hints so the result means something.'
          : 'You are past needing hints on this one. Take the swing.' };
      this.log.push(rec);
      return rec;
    }

    const granted = Math.min(asked, ceiling);
    const clamped = granted < asked;
    // §4.3: a rung-2 escalation on a conceptual skill becomes a bounded
    // Socratic dialogue rather than deeper telling.
    const socratic = granted >= 2 && isConceptual(skill ?? skillId);
    if (socratic) h.dialogues += 1;

    const rec = {
      skillId, granted, asked, ceiling, refused: null, clamped,
      credit: creditFor(granted),
      socratic,
      maxTurns: socratic ? this.cfg.socraticMaxTurns : 0,
      contract: h.fadeContract > 0,
      why: clamped
        ? `Here is a ${RUNGS[granted].name} hint — ${RUNGS[granted].does}. You are close enough on this skill that a bigger one would be doing it for you.`
        : `Here is a ${RUNGS[granted].name} hint — ${RUNGS[granted].does}.`,
    };
    if (h.fadeContract > 0) h.fadeContract -= 1;
    this.log.push(rec);
    return rec;
  }

  /**
   * Record how an attempt ended, and open a fading contract if the learner has
   * been leaning on the ladder over a sustained window. The contract is named
   * out loud — a system that quietly makes help worse is a system nobody trusts.
   */
  record(skillId, { rung = 0 } = {}) {
    const h = this.state(skillId);
    h.window.push(rung > 0 ? 1 : 0);
    if (h.window.length > this.cfg.fadeWindow) h.window.shift();
    if (h.window.length < this.cfg.fadeWindow || h.fadeContract > 0) return null;
    const dependence = h.window.reduce((a, b) => a + b, 0) / h.window.length;
    if (dependence <= this.cfg.fadeThreshold) return null;
    h.fadeContract = this.cfg.fadeContractTasks;
    h.contractsOpened += 1;
    h.window = [];
    return {
      skillId, action: 'fading_contract', dependence: +dependence.toFixed(2),
      tasks: this.cfg.fadeContractTasks,
      why: `You have taken a hint on ${Math.round(dependence * 100)}% of the last ${this.cfg.fadeWindow} tasks here. The next ${this.cfg.fadeContractTasks} run one rung lighter — you know more of this than the hints let you show.`,
    };
  }

  dependence(skillId) {
    const w = this.state(skillId).window;
    return w.length ? w.reduce((a, b) => a + b, 0) / w.length : 0;
  }
}
