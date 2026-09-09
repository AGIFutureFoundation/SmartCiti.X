/**
 * ACP-08 — safeguards and governance.
 *
 * The rest of the stack decides what a learner sees. This module decides what
 * the system is allowed to do to them. Three parts:
 *
 *   ParityMonitor    — is the system treating cohorts differently, and is
 *                      anyone quietly hiding that by tuning per cohort
 *   StopConditions   — when to stop adapting at all, because a degraded dial
 *                      is worse than no dial
 *   OverrideManager  — humans can always intervene, within bounds, on the record
 *
 * Everything here refuses rather than warns. A safeguard that only logs is a
 * log, not a safeguard.
 */

export const PARITY = {
  relativeAlarm: 0.10,      // >10% relative disparity opens a ticket
  minCohortN: 20,           // below this a "disparity" is noise
  metrics: ['gatePassRate', 'timeInSupport', 'stretchOfferRate'],
};

export const STOP = {
  calibrationDriftPerWeek: 8,     // points
  driftedItemShare: 0.20,         // ...on more than a fifth of items
  cohortAnxietyShare: 0.25,       // a week above this halts adaptation
  parityJobMaxAgeDays: 8,         // a parity job that cannot run is a stop
};

export const OVERRIDE = {
  learnerEasierPerWeek: 2,        // "easier today", no questions asked
  learnerEasierDelta: -3,
  overriddenEvidenceWeight: 0.3,  // §2.2: overridden episodes are biased
};

/* ------------------------------------------------------------- parity ---- */
export class ParityMonitor {
  /** @param {AuditLog} audit */
  constructor({ audit = null, cfg = {} } = {}) {
    this.cfg = { ...PARITY, ...cfg };
    this.audit = audit;
    this.cohorts = new Map();      // key -> {n, gatePassRate, timeInSupport, stretchOfferRate}
    this.paramFingerprints = new Map(); // cohort -> fingerprint of dial params
    this.openTickets = [];
    this.lastRunAt = null;
  }

  report(cohortKey, stats) { this.cohorts.set(cohortKey, stats); }

  /**
   * Record the dial parameters a cohort is being served with.
   *
   * This exists to enforce the spec's sharpest sentence: parameters may not be
   * tuned per cohort to MASK a disparity. Without a record of what each cohort
   * was served, "we fixed the metric" and "we hid the metric" are
   * indistinguishable afterwards.
   */
  recordParams(cohortKey, params) {
    this.paramFingerprints.set(cohortKey, JSON.stringify(params, Object.keys(params).sort()));
  }

  /** True when cohorts are being served materially different dial settings. */
  paramsDiverge() {
    const seen = new Set(this.paramFingerprints.values());
    return seen.size > 1;
  }

  /** @returns {{clean:boolean, tickets:Array, masking:boolean}} */
  run({ now = Date.now() } = {}) {
    this.lastRunAt = now;
    const usable = [...this.cohorts.entries()].filter(([, s]) => (s.n ?? 0) >= this.cfg.minCohortN);
    const tickets = [];

    for (const metric of this.cfg.metrics) {
      const vals = usable.map(([k, s]) => [k, s[metric]]).filter(([, v]) => Number.isFinite(v));
      if (vals.length < 2) continue;
      const nums = vals.map(([, v]) => v);
      const hi = Math.max(...nums), lo = Math.min(...nums);
      const base = Math.max(Math.abs(hi), 1e-9);
      const rel = (hi - lo) / base;
      if (rel > this.cfg.relativeAlarm) {
        const worst = vals.find(([, v]) => v === lo)[0];
        const best = vals.find(([, v]) => v === hi)[0];
        tickets.push({ metric, relative: +rel.toFixed(3), best, worst, hi, lo });
      }
    }

    // Masking check: a disparity is open AND cohorts are on different settings.
    const masking = tickets.length > 0 && this.paramsDiverge();
    this.openTickets = tickets;

    for (const t of tickets) {
      this.audit?.append({ actor: 'parity', action: 'parity.ticket',
        why: `${t.metric} differs ${(t.relative * 100).toFixed(1)}% between ${t.best} and ${t.worst}`,
        after: t });
    }
    if (masking) {
      this.audit?.append({ actor: 'parity', action: 'parity.masking_suspected',
        why: 'cohorts are on different dial parameters while a disparity is open — '
           + 'root cause belongs in content or calibration, not in per-cohort tuning',
        after: { fingerprints: [...this.paramFingerprints.keys()] } });
    }
    return { clean: tickets.length === 0, tickets, masking };
  }

  /** ACP-13: promotions are blocked while parity is red. */
  promotionsAllowed() {
    return this.openTickets.length === 0;
  }

  ageDays(now = Date.now()) {
    return this.lastRunAt === null ? Infinity : (now - this.lastRunAt) / 86400000;
  }
}

/* -------------------------------------------------------- stop conditions - */
export class StopConditions {
  constructor({ audit = null, parity = null, cfg = {} } = {}) {
    this.cfg = { ...STOP, ...cfg };
    this.audit = audit;
    this.parity = parity;
    this.halted = false;
    this.reasons = [];
  }

  /**
   * @param {object} signals
   *   driftPointsPerWeek, driftedItemShare, cohortAnxietyShare
   * @returns {{halted:boolean, reasons:string[]}}
   */
  evaluate(signals = {}, { now = Date.now() } = {}) {
    const r = [];
    const { driftPointsPerWeek = 0, driftedItemShare = 0, cohortAnxietyShare = 0 } = signals;

    if (driftPointsPerWeek > this.cfg.calibrationDriftPerWeek
        && driftedItemShare > this.cfg.driftedItemShare) {
      r.push(`item calibration drifting ${driftPointsPerWeek.toFixed(1)} pts/week on `
           + `${(driftedItemShare * 100).toFixed(0)}% of items`);
    }
    if (cohortAnxietyShare > this.cfg.cohortAnxietyShare) {
      r.push(`cohort spent ${(cohortAnxietyShare * 100).toFixed(0)}% of time in SUPPORT`);
    }
    if (this.parity && this.parity.ageDays(now) > this.cfg.parityJobMaxAgeDays) {
      r.push('the parity job has not run inside its window');
    }

    const wasHalted = this.halted;
    this.halted = r.length > 0;
    this.reasons = r;
    if (this.halted && !wasHalted) {
      this.audit?.append({ actor: 'safeguards', action: 'adaptation.halted',
        why: `a degraded dial is worse than no dial: ${r.join('; ')}`, after: { reasons: r } });
    }
    if (!this.halted && wasHalted) {
      this.audit?.append({ actor: 'safeguards', action: 'adaptation.resumed',
        why: 'stop conditions cleared' });
    }
    return { halted: this.halted, reasons: r };
  }

  /** While halted, everyone is served fixed difficulty rather than a bad dial. */
  setpointFor(dial, skillId, fallback = 50) {
    return this.halted ? fallback : dial.setpoint(skillId);
  }
}

/* ------------------------------------------------------------ overrides --- */
export class OverrideManager {
  constructor({ audit = null, bus = null, cfg = {} } = {}) {
    this.cfg = { ...OVERRIDE, ...cfg };
    this.audit = audit;
    this.publish = bus ? bus.publisherFor('instructor_ui') : null;
    this.learnerEasierUses = new Map();   // learner -> [timestamps]
    this.pins = new Map();                // `${learner}:${skill}` -> difficulty
  }

  /** An instructor may pin anything; it is always logged and always weighted down. */
  pin({ learner, skill, difficulty, actor, reason = '' }) {
    this.pins.set(`${learner}:${skill}`, difficulty);
    const rec = { learner, skill, difficulty, actor, kind: 'pin' };
    this.audit?.append({ actor, action: 'override.pin', why: reason || 'instructor pin',
                         after: rec, learner, skill });
    this.publish?.('override.applied', rec);
    return { ok: true, evidenceWeight: this.cfg.overriddenEvidenceWeight };
  }

  unpin({ learner, skill, actor }) {
    const had = this.pins.delete(`${learner}:${skill}`);
    if (had) {
      this.audit?.append({ actor, action: 'override.unpin', why: 'pin released',
                           learner, skill });
      this.publish?.('override.applied', { learner, skill, kind: 'unpin', actor });
    }
    return { ok: had };
  }

  /**
   * The learner's own lever: "easier today", twice a week, no questions asked.
   * Bounded because it is a relief valve, not a difficulty setting.
   */
  easierToday({ learner, now = Date.now() }) {
    const week = 7 * 86400000;
    const uses = (this.learnerEasierUses.get(learner) ?? []).filter((t) => now - t < week);
    if (uses.length >= this.cfg.learnerEasierPerWeek) {
      this.audit?.append({ actor: learner, action: 'override.easier_declined',
        why: `already used ${uses.length} of ${this.cfg.learnerEasierPerWeek} this week`,
        learner });
      return { ok: false, remaining: 0,
               why: `You've used both of this week's easier days. They reset weekly.` };
    }
    uses.push(now);
    this.learnerEasierUses.set(learner, uses);
    this.audit?.append({ actor: learner, action: 'override.easier_today',
      why: 'learner asked for an easier day', after: { delta: this.cfg.learnerEasierDelta },
      learner });
    this.publish?.('override.applied',
      { learner, kind: 'easier_today', delta: this.cfg.learnerEasierDelta });
    return { ok: true, delta: this.cfg.learnerEasierDelta,
             remaining: this.cfg.learnerEasierPerWeek - uses.length };
  }

  pinnedDifficulty(learner, skill) {
    return this.pins.get(`${learner}:${skill}`) ?? null;
  }

  /** Evidence from an overridden episode is biased and must be weighted down. */
  evidenceWeight(learner, skill) {
    return this.pins.has(`${learner}:${skill}`) ? this.cfg.overriddenEvidenceWeight : 1;
  }
}
