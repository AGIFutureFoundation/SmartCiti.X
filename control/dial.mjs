/**
 * ACP-03 — the ZPD dial, and ACP-07 — the affect classifier that feeds it.
 * Deterministic arithmetic: the whole point is that it stays auditable.
 */
import { pSuccess } from './lpa.mjs';

export const BAND = { lo: 0.70, hi: 0.85 };
export const BAND_CENTER = 0.775;
export const DEFAULTS = {
  setpointOffset: -6.5,     // c_s = theta + offset  (spec §3.1)
  window: 5,                // attempts per control window
  stepDown: 4,
  stepUpBase: 2,
  stepUpMax: 6,
  railLo: -14,              // c_s clamp, relative to theta (safety net only)
  railHi: 0,
  sessionDelta: 10,         // max setpoint movement WITHIN one session
  B_hi: 0.6,                // boredom threshold
  A_hi: 0.6,                // anxiety threshold
  recoveryDrop: -12,
  closedLoop: true,         // v1.2: correct the setpoint from observed success
  loopGain: 0.3,            // damping; 0.3 @ window 5 won the calibration sweep
};

/**
 * Closed-loop correction (v1.2). Given an observed success rate at a known
 * served difficulty, invert the logistic for the difficulty that WOULD have
 * produced the band centre. Open-loop stepping alone cannot correct a
 * systematically biased theta; this can.
 */
export function impliedSetpoint(servedDifficulty, pHat, offset = DEFAULTS.setpointOffset) {
  const p = Math.max(0.05, Math.min(0.95, pHat));
  const impliedTheta = servedDifficulty + LOGIT_W * Math.log10(p / (1 - p));
  return impliedTheta + offset;
}
const LOGIT_W = 12;

export const STATES = ['CALIBRATING', 'FLOW', 'STRETCH', 'SUPPORT', 'RECOVERY', 'PINNED'];

/** ACP-07 classifier. Signals arrive normalized against the learner's baseline. */
export function classifyAffect(win) {
  const { pHat, latZ, latVarZ, hintRate, idleRate, abandon } = win;
  // Each term contributes at most its own weight — an extreme signal on one
  // input must not saturate the score on its own.
  const boredom = clamp01(
    0.45 * clamp01((pHat - 0.85) / 0.15) +
    0.30 * clamp01(-latZ) +
    0.15 * (hintRate === 0 ? 1 : 0) +
    0.10 * clamp01(idleRate),
  );
  const anxiety = clamp01(
    0.40 * clamp01((0.70 - pHat) / 0.70) +
    0.25 * clamp01(latVarZ) +
    0.20 * clamp01(hintRate * 2) +
    0.15 * (abandon ? 1 : 0),
  );
  let state = 'FLOW';
  if (anxiety >= 0.6) state = 'ANXIETY';
  else if (boredom >= 0.6) state = 'BOREDOM';
  else if (idleRate > 0.5) state = 'DISENGAGED';
  return { state, boredom, anxiety };
}

const clamp01 = (x) => Math.max(0, Math.min(1, x));

export class ZpdDial {
  constructor(profile, cfg = {}) {
    this.p = profile;
    this.cfg = { ...DEFAULTS, ...cfg };
    this.perSkill = new Map();
  }

  state(skillId) {
    if (!this.perSkill.has(skillId)) {
      const s = this.p.get(skillId);
      this.perSkill.set(skillId, {
        c: s.theta + this.cfg.setpointOffset,
        dialState: s.sigma > 10 ? 'CALIBRATING' : 'FLOW',
        window: [],
        failedWindows: 0,
        sessionStart: s.theta + this.cfg.setpointOffset,
        history: [],
        pinned: null,
      });
    }
    return this.perSkill.get(skillId);
  }

  /**
   * Current challenge setpoint. ALL clamping happens here, in one place — two
   * clamp sites with different anchors is how the setpoint escaped the session
   * cap through the getter (v1.1 defect 2).
   *
   * Order: session cap first, theta rail last. The rail is the final authority
   * because it is the SAFETY bound; the session cap is a comfort bound. With
   * the order reversed a stale-high session anchor pushed the setpoint above
   * the rail once theta fell (soak test, ~2k attempts).
   *
   * `sessionStart` must be re-anchored by startSession() at every session
   * boundary — left stale it silently freezes the dial (v1.1 defect 1).
   */
  setpoint(skillId) {
    const d = this.state(skillId);
    if (d.pinned !== null) return d.pinned;
    const th = this.p.get(skillId).theta;
    // Session cap first (experience: don't lurch mid-session), theta rail LAST
    // (safety: never absurdly far from the learner). The rail is the final
    // authority -- with the order reversed, a high session anchor could push
    // the setpoint above the rail after theta fell, which is exactly the case
    // the rail exists to prevent. Found by soak test at ~2k attempts.
    const capped = clamp(d.c, d.sessionStart - this.cfg.sessionDelta,
                              d.sessionStart + this.cfg.sessionDelta);
    return clamp(capped, th + this.cfg.railLo, th + this.cfg.railHi);
  }

  predictedSuccess(skillId, difficulty) {
    return pSuccess(this.p.get(skillId).theta, difficulty);
  }

  /**
   * Feed one attempt. Returns a decision record with the `why` string the
   * spec requires on every adaptation (P4).
   */
  observe(skillId, attempt) {
    const d = this.state(skillId);
    const s = this.p.get(skillId);
    d.window.push(attempt);
    if (s.sigma <= 10 && d.dialState === 'CALIBRATING') d.dialState = 'FLOW';
    if (d.window.length < this.cfg.window) return null;

    const win = d.window;
    d.window = [];
    // hint-discounted success rate
    const pHat = win.reduce((a, x) => a + (x.correct ? (1 - 0.15 * x.rung) : 0), 0) / win.length;
    const latZ = mean(win.map((x) => x.latZ ?? 0));
    const latVarZ = variance(win.map((x) => x.latZ ?? 0));
    const hintRate = mean(win.map((x) => (x.rung > 0 ? 1 : 0)));
    const idleRate = mean(win.map((x) => (x.idle ? 1 : 0)));
    const abandon = win.some((x) => x.abandon);

    const affect = classifyAffect({ pHat, latZ, latVarZ, hintRate, idleRate, abandon });
    const before = { c: this.setpoint(skillId), state: d.dialState };

    let action = 'hold', why = 'Holding: you are landing in the target range.';
    const velocity = s.velocity;

    // v1.2 closed loop: pull the setpoint toward what the observed success rate
    // implies, before the affect-driven asymmetric steps below.
    if (this.cfg.closedLoop) {
      const servedAvg = mean(win.map((x) => x.difficulty ?? d.c));
      const target = impliedSetpoint(servedAvg, pHat, this.cfg.setpointOffset);
      if (Number.isFinite(target)) d.c += this.cfg.loopGain * (target - d.c);
    }

    if (pHat > BAND.hi && affect.boredom > this.cfg.B_hi) {
      const step = clamp(this.cfg.stepUpBase + velocity, this.cfg.stepUpBase, this.cfg.stepUpMax);
      d.c += step;
      d.dialState = 'STRETCH';
      action = 'step_up';
      why = `Raised challenge: ${Math.round(pHat * 100)}% success over the last ${win.length} tasks, faster than your usual pace and without hints.`;
      d.failedWindows = 0;
    } else if (pHat < BAND.lo && affect.anxiety > this.cfg.A_hi) {
      d.c -= this.cfg.stepDown;
      d.dialState = 'SUPPORT';
      action = 'step_down_scaffold';
      why = `Eased off and opened a hint: ${Math.round(pHat * 100)}% success with rising hesitation over the last ${win.length} tasks.`;
      d.failedWindows += 1;
    } else if (pHat < 0.55) {
      d.c -= this.cfg.stepDown;
      d.dialState = 'SUPPORT';
      action = 'step_down';
      why = `Eased off: ${Math.round(pHat * 100)}% success is below where practice pays off.`;
      d.failedWindows += 1;
    } else {
      d.dialState = d.dialState === 'CALIBRATING' ? 'CALIBRATING' : 'FLOW';
      d.failedWindows = 0;
    }

    if (d.failedWindows >= 2) {
      d.c = s.theta + this.cfg.recoveryDrop;
      d.dialState = 'RECOVERY';
      action = 'recovery';
      why = 'Stepping back to a worked example and rebuilding from there.';
      d.failedWindows = 0;
    }

    // Rails: a safety net around theta, plus bounded movement within ONE
    // session. `sessionStart` MUST be re-anchored by startSession() at every
    // session boundary — left stale it silently freezes the dial (found in
    // shadow-mode simulation, v1.1 -> v1.2).
    // Clamping is applied by setpoint(); keep the stored intent bounded only
    // loosely so a long session cannot accumulate an absurd latent value.
    d.c = clamp(d.c, s.theta - 40, s.theta + 40);

    const rec = { skillId, action, why, pHat, affect, before,
                  after: { c: this.setpoint(skillId), state: d.dialState } };
    d.history.push(rec);
    return rec;
  }

  /** Learner returns after time away: protect the re-entry (spec §7). */
  reentry(skillId, daysAway) {
    if (daysAway < 7) return null;
    const d = this.state(skillId);
    d.c -= 5;
    d.sessionStart = d.c;
    return { action: 'reentry_ramp', why: `Welcome back — starting easier after ${daysAway} days away.` };
  }

  /** Re-anchor the session cap. MUST be called at every session boundary. */
  startSession(skillId) {
    const d = this.state(skillId);
    const th = this.p.get(skillId).theta;
    d.sessionStart = clamp(d.c, th + this.cfg.railLo, th + this.cfg.railHi);
  }

  pin(skillId, difficulty) { this.state(skillId).pinned = difficulty; this.state(skillId).dialState = 'PINNED'; }
  unpin(skillId) { this.state(skillId).pinned = null; this.state(skillId).dialState = 'FLOW'; }
}

const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
const mean = (a) => (a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0);
const variance = (a) => { const m = mean(a); return mean(a.map((x) => (x - m) ** 2)); };
