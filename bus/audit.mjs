/**
 * ACP-08 — the append-only audit log.
 *
 * The spec says the "Why this?" surface and the compliance audit read from the
 * SAME log, so an explanation shown to a learner and the record shown to a
 * regulator cannot disagree. That only holds if there is one log and it is
 * genuinely append-only.
 */
export class AuditLog {
  constructor({ clock = () => Date.now(), limit = 100000 } = {}) {
    this.clock = clock;
    this.limit = limit;
    this._entries = [];
    this.truncated = 0;
  }

  /** @returns {Readonly<object>} the appended entry */
  append({ actor, action, before = null, after = null, why = '', learner = null, skill = null }) {
    if (!actor || !action) throw new Error('audit: actor and action are required');
    const e = Object.freeze({
      seq: this._entries.length,
      ts: this.clock(),
      actor, action, before, after, why, learner, skill,
    });
    this._entries.push(e);
    if (this._entries.length > this.limit) { this._entries.shift(); this.truncated++; }
    return e;
  }

  /** Entries are handed out frozen and copied — callers cannot rewrite history. */
  entries(filter = {}) {
    return this._entries.filter((e) =>
      (!filter.learner || e.learner === filter.learner) &&
      (!filter.skill || e.skill === filter.skill) &&
      (!filter.action || e.action === filter.action) &&
      (!filter.actor || e.actor === filter.actor));
  }

  /** The learner-facing surface: the same rows, phrased for a person. */
  whyThis(learner, n = 10) {
    return this.entries({ learner })
      .filter((e) => e.why)
      .slice(-n).reverse()
      .map((e) => ({ when: e.ts, what: e.action, why: e.why, skill: e.skill }));
  }

  get length() { return this._entries.length; }
}
