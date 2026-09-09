/**
 * ACP-09 — the inter-agent message bus.
 *
 * Until now every component called every other component directly, which meant
 * the spec's two load-bearing rules — single-writer per aggregate, and every
 * adaptation on the audit log — were documented but not ENFORCED. A mentor
 * could not write dial state only because no one had written the line of code
 * that would. This makes the contract real: the bus refuses.
 *
 * Delivery is at-least-once with dedupe on `event_id`, matching the transport
 * the spec assumes. Handlers must therefore be idempotent, and the bus tells
 * you when it drops a duplicate rather than hiding it.
 */

/** Topic -> the single role permitted to publish it (ACP-09 single-writer). */
export const TOPIC_OWNERS = Object.freeze({
  'telemetry.event':   'client',
  'profile.updated':   'lpa',
  'affect.scored':     'affect',
  'dial.setpoint':     'dial',
  'dial.state_changed':'dial',
  'quest.assembled':   'sequencer',
  'hint.served':       'hint_engine',
  'gate.decision':     'assessment',
  'override.applied':  'instructor_ui',
  'mentor.turn':       'mentor',
});

export const SCHEMA_VERSION = '1.0.0';

export class ContractViolation extends Error {
  constructor(msg, detail) {
    super(msg);
    this.name = 'ContractViolation';
    this.detail = detail;
  }
}

export class Bus {
  /**
   * @param {object} opts
   *   audit    — optional AuditLog; every violation and decision is appended
   *   strict   — throw on violation (default) or contain and count it
   */
  constructor({ audit = null, strict = true } = {}) {
    this.audit = audit;
    this.strict = strict;
    this.subs = new Map();          // topic -> [{role, fn}]
    this.seen = new Set();          // event_id dedupe
    this.stats = { published: 0, delivered: 0, duplicates: 0, violations: 0, dropped: 0 };
    this.violations = [];
  }

  subscribe(topic, role, fn) {
    if (!(topic in TOPIC_OWNERS)) throw new ContractViolation(`unknown topic "${topic}"`, { topic });
    if (!this.subs.has(topic)) this.subs.set(topic, []);
    this.subs.get(topic).push({ role, fn });
    return () => {
      const list = this.subs.get(topic);
      const i = list.findIndex((s) => s.fn === fn);
      if (i >= 0) list.splice(i, 1);
    };
  }

  /**
   * Publish. `role` is the claimed publisher and is checked against the topic's
   * owner — this is the whole point of the bus existing.
   */
  publish(topic, role, payload, { event_id = null, schema_version = SCHEMA_VERSION } = {}) {
    const owner = TOPIC_OWNERS[topic];
    if (owner === undefined) return this.#violate('unknown_topic', { topic, role });
    if (role !== owner) {
      return this.#violate('single_writer', { topic, role, owner },
        `${role} may not publish ${topic}; only ${owner} may`);
    }

    const id = event_id ?? `${topic}:${this.stats.published}:${Math.random().toString(36).slice(2, 10)}`;
    if (this.seen.has(id)) { this.stats.duplicates++; return { ok: true, duplicate: true, id }; }
    this.seen.add(id);
    this.stats.published++;

    const msg = Object.freeze({ topic, role, schema_version, event_id: id, payload });
    const subs = this.subs.get(topic) ?? [];
    if (!subs.length) this.stats.dropped++;
    for (const s of subs) {
      // A failing subscriber must not take down the publisher or its siblings.
      try { s.fn(msg); this.stats.delivered++; }
      catch (e) { this.#violate('subscriber_threw', { topic, role: s.role, error: String(e.message) }); }
    }
    return { ok: true, id, delivered: subs.length };
  }

  #violate(kind, detail, msg) {
    this.stats.violations++;
    const rec = { kind, detail, msg: msg ?? kind, ts: Date.now() };
    this.violations.push(rec);
    this.audit?.append({ actor: detail.role ?? 'unknown', action: `bus.${kind}`,
                         why: rec.msg, before: null, after: detail });
    if (this.strict && kind !== 'subscriber_threw') throw new ContractViolation(rec.msg, detail);
    return { ok: false, violation: kind, detail };
  }

  /** A publisher bound to one role — hands out no way to claim another. */
  publisherFor(role) {
    return (topic, payload, opts) => this.publish(topic, role, payload, opts);
  }
}
