/**
 * ACP-12 §13.3 — a mentor's own vector, and SUPPORT.
 *
 * The eval harness (fabric/evals.mjs) decides whether a version may SHIP.
 * Nothing decided what happens to a version that passed and then went bad
 * in service: over-helping on real turns, tripping scope refusals, escalating
 * every second learner, or simply dying. The spec says an agent, like a
 * learner, can enter SUPPORT, and that sustained degradation pins traffic
 * back to the champion automatically. This is that.
 *
 * Each served turn is a Mentor.turn() record; the vector over a version's
 * last `window` turns is measured, never modelled. Degradation must hold for
 * `sustain` consecutive reviews before it pins - one bad review is a bad day,
 * two is a pattern. Silence is different: a heartbeat the ops monitor has
 * already found stale pins on the first review, because the monitor's own
 * interval and grace are the sustain. Recovery is not a timer: the version's
 * eval record is invalidated on entry, and only a fresh passing eval,
 * registered again, lets it promote.
 */

export const SUPPORT = Object.freeze({
  window: 40,            // turns per review window
  sustain: 2,            // consecutive degraded reviews before SUPPORT
  overHelpRate: 0.10,    // the eval harness's own gate-2 threshold, held in service
  violationRate: 0,      // any contained scope violation in the window counts
  escalationRate: 0.30,  // a mentor that hands every third learner to a human is not mentoring
});

export class MentorHealth {
  constructor({ registry, audit = null, heartbeat = null, cfg = {} } = {}) {
    if (!registry) throw new Error('MentorHealth needs the agent registry: SUPPORT is a registry decision');
    this.cfg = { ...SUPPORT, ...cfg };
    this.registry = registry;
    this.audit = audit;
    this.heartbeat = heartbeat;
    this.turns = new Map();     // "mentor@version" -> served turn records
    this.strikes = new Map();   // "mentor@version" -> consecutive degraded reviews
    this.reviews = [];
  }

  static key(mentor, version) { return `${mentor}@${version}`; }

  /** One served turn, as Mentor.turn() returned it. */
  observe(record) {
    if (!record?.mentor || !record?.version) throw new Error('a turn record names its mentor and version');
    const k = MentorHealth.key(record.mentor, record.version);
    if (!this.turns.has(k)) this.turns.set(k, []);
    this.turns.get(k).push(record);
    return this;
  }

  /** The measured vector over the last window of served turns. */
  vector(mentor, version) {
    const rows = (this.turns.get(MentorHealth.key(mentor, version)) ?? []).slice(-this.cfg.window);
    const n = rows.length;
    const rate = (f) => (n ? +(rows.filter(f).length / n).toFixed(3) : 0);
    return {
      mentor, version, turns: n,
      overHelpRate: rate((r) => r.over_helped === true),
      violationRate: rate((r) => (r.violations?.length ?? 0) > 0),
      escalationRate: rate((r) => r.escalated === true),
      handoffRate: rate((r) => !!r.handoff),
    };
  }

  /** Why a version is degraded right now: [] when it is not. */
  reasons(mentor, version) {
    const v = this.vector(mentor, version);
    const r = [];
    if (v.turns >= this.cfg.window) {
      if (v.overHelpRate > this.cfg.overHelpRate) r.push(`over-helps on ${Math.round(v.overHelpRate * 100)}% of served turns`);
      if (v.violationRate > this.cfg.violationRate) r.push(`scope violations contained on ${Math.round(v.violationRate * 100)}% of turns`);
      if (v.escalationRate > this.cfg.escalationRate) r.push(`escalates ${Math.round(v.escalationRate * 100)}% of turns to a human`);
    }
    const hb = `mentor:${mentor}@${version}`;
    if (this.heartbeat?.records.has(hb) && this.heartbeat.status(hb) === 'stale') r.push('silent: its heartbeat is stale');
    return r;
  }

  /**
   * The champion review (§14.3, weekly). Every version the registry holds
   * is measured; sustained degradation or silence pins it. Returns only the
   * versions that ENTERED support on this review, so the caller acts on the
   * change rather than re-reading the whole registry.
   */
  review({ at = null } = {}) {
    const entered = [];
    for (const mentor of this.registry.ids()) {
      const rec = this.registry.get(mentor);
      for (const version of Object.keys(rec.versions)) {
        const k = MentorHealth.key(mentor, version);
        const reasons = this.reasons(mentor, version);
        const silent = reasons.some((x) => x.startsWith('silent'));
        const degraded = reasons.length > 0;
        this.strikes.set(k, degraded && !silent ? (this.strikes.get(k) ?? 0) + 1 : 0);
        const pin = !this.registry.inSupport(mentor, version)
          && (silent || (this.strikes.get(k) ?? 0) >= this.cfg.sustain);
        this.reviews.push(Object.freeze({ at, mentor, version, reasons, strikes: this.strikes.get(k), pinned: pin }));
        if (!pin) continue;
        this.registry.support(mentor, version, { reasons, at });
        const isChampion = this.registry.champion(mentor) === version;
        this.audit?.append({ actor: 'ops', action: 'agent.support',
          why: `${mentor}@${version} entered SUPPORT: ${reasons.join('; ')}`
            + (isChampion ? '; it is the champion, so there is nothing to pin traffic to' : `; traffic pinned to ${this.registry.champion(mentor)}`),
          after: { mentor, version, reasons, traffic: this.registry.traffic(mentor) } });
        entered.push(Object.freeze({ mentor, version, reasons }));
      }
    }
    return entered;
  }
}
