/**
 * ACP-13 §14.3 — the automation loop, and §14.3's cost governor.
 *
 * Seven jobs on three cadences. The one that matters most is the parity job,
 * because ACP-08 trips a stop condition when it fails to run inside its
 * window — so the scheduler is not merely convenience infrastructure, it is
 * load-bearing for a safeguard. A scheduler that silently skips a job is
 * therefore a safety defect, not an ops annoyance, and every skip is recorded.
 */

export const CADENCE = { continuous: 0, onChange: -1, nightly: 86400000, weekly: 604800000 };

export const JOBS = [
  { name: 'calibration_sweep', cadence: 'nightly',    does: 're-fit item difficulties, flag drift, demote drifting modules' },
  { name: 'coverage_bot',      cadence: 'nightly',    does: 'skill-node reachability per band; opens coverage.gap tickets' },
  { name: 'parity_job',        cadence: 'weekly',     does: 'ACP-08 cohort comparisons; blocks promotions while red', safetyCritical: true },
  { name: 'eval_harness',      cadence: 'onChange',   does: 'the full mentor eval suite per version' },
  { name: 'factory_queue',     cadence: 'continuous', does: 'authoring against coverage.gap and revision tickets' },
  { name: 'champion_review',   cadence: 'weekly',     does: 'promote / hold / rollback per mentor from outcome-lift data' },
  { name: 'cost_governor',     cadence: 'continuous', does: 'per-plane token budgets' },
];

export class Scheduler {
  constructor({ audit = null, now = 0 } = {}) {
    this.audit = audit;
    this.clock = now;
    this.handlers = new Map();
    this.lastRun = new Map();
    this.runs = [];
    this.skips = [];
  }

  on(name, fn) {
    if (!JOBS.some((j) => j.name === name)) throw new Error(`unknown job ${name}`);
    this.handlers.set(name, fn);
    return this;
  }

  due(name, at = this.clock) {
    const job = JOBS.find((j) => j.name === name);
    const period = CADENCE[job.cadence];
    if (period <= 0) return true;                       // continuous / on-change
    const last = this.lastRun.get(name);
    return last === undefined || at - last >= period;
  }

  /**
   * Run everything due. A handler that throws does NOT stop the loop — one
   * broken nightly job must not prevent the weekly parity job from running,
   * since that would convert a small failure into a halted network. Failures
   * are recorded and surfaced.
   */
  tick(advanceMs = 0, ctx = {}) {
    this.clock += advanceMs;
    const results = [];
    for (const job of JOBS) {
      if (!this.due(job.name)) continue;
      const fn = this.handlers.get(job.name);
      if (!fn) {
        this.skips.push({ job: job.name, at: this.clock, why: 'no handler registered' });
        if (job.safetyCritical) {
          this.audit?.append({ actor: 'ops', action: 'job.missing',
            why: `${job.name} is safety-critical and has no handler; ACP-08 will halt adaptation when its window lapses`,
            after: { job: job.name } });
        }
        continue;
      }
      let out, error = null;
      try { out = fn({ ...ctx, at: this.clock, job: job.name }); }
      catch (err) { error = String(err?.message ?? err); }
      this.lastRun.set(job.name, this.clock);
      const rec = { job: job.name, at: this.clock, ok: error === null, error, out };
      this.runs.push(rec);
      results.push(rec);
      if (error) {
        this.audit?.append({ actor: 'ops', action: 'job.failed',
          why: `${job.name} failed: ${error}`, after: { job: job.name } });
      }
    }
    return results;
  }

  lastRunAt(name) { return this.lastRun.get(name) ?? null; }
  failures() { return this.runs.filter((r) => !r.ok); }
}

/* ------------------------------------------------------- cost governor ---- */

/**
 * §14.3: the conversation plane degrades to smaller serving models under
 * budget pressure; the control plane NEVER throttles.
 *
 * The control plane is arithmetic — the dial, the profile, the gates — and it
 * is what decides whether a learner is certified. Degrading it to save tokens
 * would make certification a function of the month's budget. So the governor
 * cannot throttle it, and the test asserts that rather than trusting the
 * configuration to stay right.
 */
export const PLANES = {
  control:      { throttleable: false, tiers: ['exact'] },
  conversation: { throttleable: true,  tiers: ['full', 'compact', 'minimal'] },
  factory:      { throttleable: true,  tiers: ['full', 'compact', 'paused'] },
};

export class CostGovernor {
  constructor({ budgets = {}, audit = null } = {}) {
    this.budgets = { conversation: 1_000_000, factory: 500_000, control: Infinity, ...budgets };
    this.spent = { control: 0, conversation: 0, factory: 0 };
    this.audit = audit;
  }

  spend(plane, tokens) {
    if (!PLANES[plane]) throw new Error(`unknown plane ${plane}`);
    this.spent[plane] += tokens;
    return this.tierFor(plane);
  }

  pressure(plane) {
    const b = this.budgets[plane];
    if (!Number.isFinite(b) || b <= 0) return 0;
    return this.spent[plane] / b;
  }

  /** Which serving tier a plane runs at right now. */
  tierFor(plane) {
    const spec = PLANES[plane];
    if (!spec.throttleable) return spec.tiers[0];
    const p = this.pressure(plane);
    const i = p >= 1.0 ? spec.tiers.length - 1 : p >= 0.8 ? 1 : 0;
    return spec.tiers[i];
  }

  /** The governor may refuse conversation and factory work; never control. */
  admit(plane, tokens) {
    if (!PLANES[plane].throttleable) return { ok: true, tier: 'exact', why: 'the control plane is never throttled' };
    const tier = this.tierFor(plane);
    if (tier === 'paused') {
      return { ok: false, tier, why: `${plane} is over budget and paused until the window resets` };
    }
    return { ok: true, tier, why: tier === 'full' ? 'within budget' : `serving at ${tier} under budget pressure` };
  }

  report() {
    return Object.keys(PLANES).map((p) => ({
      plane: p, spent: this.spent[p], budget: this.budgets[p],
      pressure: +this.pressure(p).toFixed(2), tier: this.tierFor(p),
      throttleable: PLANES[p].throttleable,
    }));
  }
}
