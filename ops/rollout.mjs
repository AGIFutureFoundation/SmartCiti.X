/**
 * ACP-13 §14.2 — rollout discipline.
 *
 * Everything ships hall by hall: 1 hall (canary, ~3% of the network), then 5,
 * then all 33, with automatic rollback on an ACP-08 stop condition. Content,
 * agents and dial parameters use the same lanes; dial parameters additionally
 * serve a shadow run first.
 *
 * This module deliberately does NOT reimplement the parity check or the stop
 * conditions. It asks ACP-08 and obeys the answer. A second implementation of
 * a safeguard is a second opinion, and two opinions about whether it is safe to
 * ship is the same failure as the duplicated source list in defect 12.
 */

/**
 * The full lane is the whole network, read from the pack rather than written
 * down here.
 *
 * It was hardcoded to 33 and stayed 33 when the network grew to 111 — so a
 * change that reached "full" was reaching under a third of the halls while
 * every status line called it fully rolled out. Found by the figures lint,
 * which flagged `33 halls` in this pack's own suite; a stale constant in a
 * safety-adjacent lane is exactly what that lint is for.
 */
import { readFileSync } from 'node:fs';

const NETWORK_HALLS = JSON.parse(
  readFileSync(new URL('../pack/manifest.json', import.meta.url), 'utf8'),
).ledger.halls;

export const LANES = [
  { name: 'canary', halls: 1,               minDwellHours: 24 },
  { name: 'wave',   halls: 5,               minDwellHours: 48 },
  { name: 'full',   halls: NETWORK_HALLS,   minDwellHours: 0  },
];

export const ROLLOUT = {
  shadowDays: 14,           // dial-parameter changes log intended actions first
  autoRollbackOnHalt: true,
};

export class RolloutError extends Error {}

export class RolloutManager {
  /**
   * @param {object} deps
   *   parity  — an ACP-08 ParityMonitor (asked, never reimplemented)
   *   stop    — an ACP-08 StopConditions
   *   audit   — the append-only log
   */
  constructor({ parity = null, stop = null, audit = null, cfg = {} } = {}) {
    this.parity = parity;
    this.stop = stop;
    this.audit = audit;
    this.cfg = { ...ROLLOUT, ...cfg };
    this.rollouts = new Map();
  }

  start(id, { kind, shadowStartedDaysAgo = null } = {}) {
    if (!['content', 'agent', 'dial_params'].includes(kind)) {
      throw new RolloutError(`unknown rollout kind ${kind}`);
    }
    const r = {
      id, kind, laneIndex: -1, halls: 0, shadowStartedDaysAgo,
      state: 'pending', history: [], rolledBackFrom: null,
    };
    this.rollouts.set(id, r);
    return r;
  }

  get(id) {
    const r = this.rollouts.get(id);
    if (!r) throw new RolloutError(`no rollout ${id}`);
    return r;
  }

  /**
   * Advance one lane. Every refusal names its reason, because a rollout that
   * silently declines to advance is indistinguishable from one that is stuck.
   */
  advance(id, { dwellHours = Infinity, now = Date.now() } = {}) {
    const r = this.get(id);
    if (r.state === 'rolled_back') {
      return this.deny(r, 'this rollout was rolled back; open a new one rather than resuming a reverted change');
    }
    if (r.laneIndex >= LANES.length - 1) return this.deny(r, 'already at full network');

    // 1. dial parameters shadow first: log intended actions, change nothing.
    if (r.kind === 'dial_params' && r.laneIndex < 0) {
      const days = r.shadowStartedDaysAgo;
      if (days === null || days < this.cfg.shadowDays) {
        return this.deny(r, `dial parameters need a ${this.cfg.shadowDays}-day shadow run before any hall sees them `
          + `(${days === null ? 'none started' : days + ' days so far'})`);
      }
    }

    // 2. ACP-08 owns the parity answer.
    if (this.parity && !this.parity.promotionsAllowed()) {
      return this.deny(r, 'parity is red: promotions are blocked while a disparity ticket is open');
    }

    // 3. ACP-08 owns the halt answer too. Shipping into a halted network means
    //    shipping into a system that has stopped trusting its own measurements,
    //    which is precisely when a change cannot be evaluated.
    if (this.stop?.halted) {
      return this.deny(r, `adaptation is halted (${this.stop.reasons.join('; ')}) — nothing promotes into a halted network`);
    }

    // 4. dwell: a lane must be observed before the next one opens.
    const cur = LANES[Math.max(0, r.laneIndex)];
    if (r.laneIndex >= 0 && dwellHours < cur.minDwellHours) {
      return this.deny(r, `${cur.name} needs ${cur.minDwellHours}h of observation, has ${dwellHours}h`);
    }

    r.laneIndex += 1;
    const lane = LANES[r.laneIndex];
    r.halls = lane.halls;
    r.state = r.laneIndex === LANES.length - 1 ? 'full' : 'rolling';
    const rec = { ok: true, id, lane: lane.name, halls: lane.halls, state: r.state,
                  why: `${id} advanced to ${lane.name} (${lane.halls} hall${lane.halls > 1 ? 's' : ''})` };
    r.history.push(rec);
    this.audit?.append({ actor: 'ops', action: 'rollout.advance', why: rec.why,
      after: { id, lane: lane.name, halls: lane.halls } });
    return rec;
  }

  deny(r, why) {
    const rec = { ok: false, id: r.id, lane: LANES[Math.max(0, r.laneIndex)]?.name ?? 'none',
                  halls: r.halls, state: r.state, why };
    r.history.push(rec);
    this.audit?.append({ actor: 'ops', action: 'rollout.denied', why, after: { id: r.id } });
    return rec;
  }

  /** Automatic rollback: called when ACP-08 halts. Returns what it reverted. */
  onHalt(reasons = []) {
    if (!this.cfg.autoRollbackOnHalt) return [];
    const reverted = [];
    for (const r of this.rollouts.values()) {
      if (r.state !== 'rolling' && r.state !== 'full') continue;
      r.rolledBackFrom = LANES[r.laneIndex]?.name ?? null;
      r.laneIndex = -1;
      r.halls = 0;
      r.state = 'rolled_back';
      const why = `rolled back from ${r.rolledBackFrom}: ${reasons.join('; ') || 'stop condition'}`;
      r.history.push({ ok: false, id: r.id, rolledBack: true, why });
      this.audit?.append({ actor: 'ops', action: 'rollout.rollback', why, after: { id: r.id } });
      reverted.push(r.id);
    }
    return reverted;
  }

  status() {
    return [...this.rollouts.values()].map((r) => ({
      id: r.id, kind: r.kind, state: r.state,
      lane: r.laneIndex < 0 ? 'none' : LANES[r.laneIndex].name, halls: r.halls,
    }));
  }
}
