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
    // §23.1: "never called run()" and "called run() but had nothing to
    // compare" must not collapse into the same state. `null` means the
    // former (unchanged default; nothing here has asserted anything about
    // parity yet, and callers that never wire up a run rely on that — see
    // bus/test_safeguards.mjs and the rollout-lanes test in ops/test.mjs).
    // `run()` sets this to an explicit `true`/`false` on every call from then
    // on, and only `false` — an executed run that measured nothing — closes
    // promotionsAllowed() below.
    this.lastObserved = null;
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

  /**
   * @returns {{clean:boolean, tickets:Array, masking:boolean, observed:boolean}}
   *
   * `clean` means "no disparity ticket is open" — that is unchanged, and it
   * stays true for a run that had exactly one usable cohort (nothing to
   * compare, so nothing contradicted cleanliness either; see
   * bus/test_safeguards.mjs's "a cohort under the minimum must not drive an
   * alarm", which still asserts `clean === true` for that shape).
   *
   * `observed` is the new, separate fact this fixes: whether any metric
   * actually had >=2 usable cohorts to compare. §23.1's own catalogue of
   * this bug (spec §23.1) is precise about the mechanism — zero cohorts, or
   * every cohort under `minCohortN`, or exactly one usable cohort, all fall
   * through every `if (vals.length < 2) continue;` and leave `tickets`
   * empty. That used to read as indistinguishable from "measured and found
   * nothing wrong". It no longer does: `clean` answers "did we find a
   * problem", `observed` answers "did we look", and promotionsAllowed()
   * below requires both.
   */
  run({ now = Date.now() } = {}) {
    const usable = [...this.cohorts.entries()].filter(([, s]) => (s.n ?? 0) >= this.cfg.minCohortN);
    const tickets = [];
    let comparisons = 0; // metrics that actually had >=2 usable cohorts to compare

    for (const metric of this.cfg.metrics) {
      const vals = usable.map(([k, s]) => [k, s[metric]]).filter(([, v]) => Number.isFinite(v));
      if (vals.length < 2) continue;
      comparisons += 1;
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

    const observed = comparisons > 0;

    // Masking check: a disparity is open AND cohorts are on different settings.
    const masking = tickets.length > 0 && this.paramsDiverge();
    this.openTickets = tickets;
    this.lastObserved = observed;

    // §23.1: a default is a policy decision. `lastRunAt` used to advance
    // unconditionally, so a run that measured nothing looked, to ageDays(),
    // exactly like a run that measured cleanliness — and that silently
    // satisfied the "parity job cannot run" stop condition (STOP.parityJob-
    // MaxAgeDays) forever, which is the second, worse half of this bug.
    // `lastRunAt` — and so ageDays() — now advances only on a run that
    // actually compared something. An unobserved run leaves it exactly
    // where it was (Infinity, if this monitor has never yet observed
    // anything), so the staleness alarm still fires on a parity job that
    // runs on schedule but sees nothing, the same as it fires on a job that
    // never runs at all.
    if (observed) {
      this.lastRunAt = now;
    } else {
      this.audit?.append({ actor: 'parity', action: 'parity.no_observation',
        why: `run executed over ${this.cohorts.size} cohort(s) (${usable.length} at/above `
           + `n>=${this.cfg.minCohortN}) but no metric had two usable cohorts to compare — `
           + 'nothing was measured, so this does not count as clean and promotions fail closed',
        after: { cohorts: this.cohorts.size, usable: usable.length } });
    }

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
    return { clean: tickets.length === 0, tickets, masking, observed };
  }

  /**
   * ACP-13: promotions are blocked while parity is red, AND while the most
   * recent run() measured nothing. `lastObserved` starts `null` (run() has
   * never been called on this monitor at all — unchanged prior behaviour,
   * which callers such as the very first rollout-lanes test rely on: a
   * network with no ACP-08 wiring calling run() yet is not itself grounds to
   * refuse). It becomes an explicit `false` only when run() executed and
   * found nothing to compare, and that is what fails closed here.
   */
  promotionsAllowed() {
    return this.openTickets.length === 0 && this.lastObserved !== false;
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
