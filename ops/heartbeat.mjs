/**
 * ACP-13 §14.3 / §21.4 — heartbeats: the liveness contract the loop was missing.
 *
 * The scheduler already records a job that was never handled and a job that
 * threw. What nothing recorded was a component that simply STOPPED: a mentor
 * cell whose runtime died, a station whose recorder went quiet, a crew whose
 * supervisor node is gone. Silence looked exactly like health. This makes
 * silence a signal.
 *
 * Every monitored component registers with the interval it promises to beat
 * on. A beat later than interval + grace is `stale`; the lapse is audited ONCE
 * when it opens and ONCE when it closes, so a long outage is one legible
 * record rather than a sweep's worth of noise. A component that declares
 * itself safety-critical hands its lapse to a halt hook, which is how a
 * silent parity job or dial service reaches ACP-08 without a second copy of
 * ACP-08's logic living here.
 *
 * Time is injected. No wall clock is read, so a sweep is deterministic and a
 * test can age the network a week in one call.
 */

export const DEFAULT_GRACE_MS = 30_000;

export const KINDS = Object.freeze(['job', 'mentor', 'crew', 'station', 'service']);

export class HeartbeatError extends Error {}

export class HeartbeatMonitor {
  /**
   * @param {object} opts
   *   audit   — optional AuditLog; every lapse and recovery lands on it
   *   now     — the clock's starting value (ms); advanced by sweep()
   *   grace   — how far past its interval a beat may arrive before staleness
   *   onStale — called with (record) when a safety-critical component lapses
   */
  constructor({ audit = null, now = 0, grace = DEFAULT_GRACE_MS, onStale = null } = {}) {
    this.audit = audit;
    this.clock = now;
    this.grace = grace;
    this.onStale = onStale;
    this.records = new Map();
    this.lapses = [];
  }

  /**
   * A component promises to beat every `intervalMs`. Registration is not a
   * beat: a component that registers and never reports is `never`, which is
   * its own status because "not yet started" and "was alive, then died" are
   * different facts for an operator.
   */
  register(id, { kind, intervalMs, safetyCritical = false } = {}) {
    if (!id) throw new HeartbeatError('a heartbeat needs an id');
    if (!KINDS.includes(kind)) throw new HeartbeatError(`unknown kind ${kind}; one of ${KINDS.join(', ')}`);
    if (!(Number.isFinite(intervalMs) && intervalMs > 0)) throw new HeartbeatError(`${id}: intervalMs must be a positive number`);
    if (this.records.has(id)) throw new HeartbeatError(`${id} is already monitored`);
    this.records.set(id, Object.freeze({
      id, kind, intervalMs, safetyCritical,
      registeredAt: this.clock, lastBeat: null, beats: 0, stale: false, lapses: 0,
    }));
    return this.status(id);
  }

  /** A beat from an unregistered component is refused: an unknown sender's "alive" is not evidence. */
  beat(id, at = this.clock) {
    const rec = this.records.get(id);
    if (!rec) throw new HeartbeatError(`${id} is not monitored; register it first`);
    if (at < (rec.lastBeat ?? -Infinity)) {
      // A beat from the past cannot make a component younger than its last
      // report; it is recorded as ignored rather than rewinding the record.
      return { ok: false, why: 'beat is older than the last one recorded', id };
    }
    const next = { ...rec, lastBeat: at, beats: rec.beats + 1 };
    if (rec.stale) {
      next.stale = false;
      this.audit?.append({ actor: 'heartbeat', action: 'heartbeat.recovered',
        why: `${id} (${rec.kind}) is beating again after ${at - rec.lastBeat} ms of silence`,
        after: { id, kind: rec.kind, silentMs: at - rec.lastBeat } });
    }
    this.records.set(id, Object.freeze(next));
    return { ok: true, id, at };
  }

  /** How late a component is right now, in ms; negative while within its window. */
  overdueMs(id, at = this.clock) {
    const rec = this.records.get(id);
    if (!rec) throw new HeartbeatError(`${id} is not monitored`);
    const since = rec.lastBeat ?? rec.registeredAt;
    return at - since - rec.intervalMs - this.grace;
  }

  /**
   * Advance the clock and find everything that has gone quiet. A lapse is
   * audited once when it opens; a safety-critical lapse also fires the halt
   * hook. Returns the components that turned stale ON THIS sweep, so a caller
   * can act on the change rather than re-reading the whole board.
   */
  sweep(advanceMs = 0) {
    this.clock += advanceMs;
    const newlyStale = [];
    for (const [id, rec] of this.records) {
      if (rec.stale || this.overdueMs(id) <= 0) continue;
      const lastSeen = rec.lastBeat ?? null;
      const next = Object.freeze({ ...rec, stale: true, lapses: rec.lapses + 1 });
      this.records.set(id, next);
      const lapse = Object.freeze({ id, kind: rec.kind, at: this.clock, lastSeen,
        safetyCritical: rec.safetyCritical,
        why: lastSeen === null ? 'registered and never reported' : `last beat ${this.clock - lastSeen} ms ago, interval ${rec.intervalMs} ms` });
      this.lapses.push(lapse);
      newlyStale.push(lapse);
      this.audit?.append({ actor: 'heartbeat', action: 'heartbeat.stale',
        why: `${id} (${rec.kind}) went quiet: ${lapse.why}`,
        after: { id, kind: rec.kind, safetyCritical: rec.safetyCritical, lastSeen } });
      if (rec.safetyCritical) {
        // Contained, not thrown: one broken hook must not stop the sweep from
        // finding the next silent component (the scheduler's rule, §21.4).
        try { this.onStale?.(lapse); }
        catch (err) {
          this.audit?.append({ actor: 'heartbeat', action: 'heartbeat.hook_failed',
            why: `the halt hook threw for ${id}: ${String(err?.message ?? err)}`, after: { id } });
        }
      }
    }
    return newlyStale;
  }

  /** 'alive' | 'stale' | 'never' — never is a component that registered and has not reported once. */
  status(id) {
    const rec = this.records.get(id);
    if (!rec) throw new HeartbeatError(`${id} is not monitored`);
    return rec.stale ? 'stale' : rec.lastBeat === null ? 'never' : 'alive';
  }

  /** The whole board, frozen rows, for a console. */
  board() {
    return [...this.records.values()].map((rec) => Object.freeze({
      id: rec.id, kind: rec.kind, status: this.status(rec.id), safetyCritical: rec.safetyCritical,
      intervalMs: rec.intervalMs, lastBeat: rec.lastBeat, beats: rec.beats, lapses: rec.lapses,
      overdueMs: Math.max(0, this.overdueMs(rec.id)),
    }));
  }

  /** True when any safety-critical component is stale right now. */
  anyCriticalStale() {
    return [...this.records.values()].some((r) => r.stale && r.safetyCritical);
  }

  byKind(kind) { return this.board().filter((r) => r.kind === kind); }
}

/**
 * Wire a Scheduler to a monitor: every job registers as a `job` heartbeat at
 * its own cadence (continuous and on-change jobs at the sweep interval given),
 * and a successful run beats. A safety-critical job that stops running now
 * turns stale through the same contract as everything else, on top of the
 * "no handler" audit the scheduler already writes.
 */
export function monitorScheduler(scheduler, monitor, { jobs, cadence, sweepMs = 60_000 } = {}) {
  for (const job of jobs) {
    const period = cadence[job.cadence];
    monitor.register(`job:${job.name}`, {
      kind: 'job', intervalMs: period > 0 ? period : sweepMs, safetyCritical: !!job.safetyCritical,
    });
  }
  const tick = scheduler.tick.bind(scheduler);
  scheduler.tick = (advanceMs = 0, ctx = {}) => {
    const results = tick(advanceMs, ctx);
    for (const r of results) if (r.ok) monitor.beat(`job:${r.job}`, r.at);
    monitor.sweep(scheduler.clock - monitor.clock);
    return results;
  };
  return scheduler;
}
