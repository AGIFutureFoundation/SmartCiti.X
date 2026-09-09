/**
 * Data classification, retention, pseudonymisation and erasure.
 *
 * The design commitment from ACP-01/08: the analytics store never holds
 * identity. It holds a pseudonymous id; the mapping to a real person lives in a
 * separate enrolment service behind its own capability (`pii.reveal`). Erasure
 * is therefore cheap and complete — break the mapping and the behavioural
 * record is genuinely anonymous rather than "anonymised".
 */

export const CLASS = Object.freeze({
  IDENTITY: 'identity',        // name, email, employer — enrolment service only
  BEHAVIOURAL: 'behavioural',  // attempts, latencies, signals — pseudonymous
  DERIVED: 'derived',          // theta, mastery, gates — pseudonymous
  AFFECT: 'affect',            // flow/anxiety labels — never exported, never sold
  AGGREGATE: 'aggregate',      // cohort counts — no individual inside
});

export const RETENTION_DAYS = Object.freeze({
  [CLASS.IDENTITY]: 'contractual',     // while enrolled + statutory period
  [CLASS.BEHAVIOURAL]: 730,            // 24 months (ACP-01 §1.3)
  [CLASS.DERIVED]: 730,
  [CLASS.AFFECT]: 90,                  // shortest: it is the most sensitive
  [CLASS.AGGREGATE]: null,             // indefinite; contains no individual
});

/** Fields that must never leave the platform in an export. */
export const NEVER_EXPORT = Object.freeze(['affect', 'anxiety', 'boredom', 'affect_state']);

/** Raw high-frequency streams are never stored at all (ACP-01 §1.3). */
export const NEVER_STORE = Object.freeze(['keystrokes', 'controller_poses', 'raw_audio', 'raw_video']);

export class PrivacyService {
  constructor({ audit = null } = {}) {
    this.audit = audit;
    this.mapping = new Map();      // pseudonym -> identity record (the ONLY link)
    this.erased = new Set();
  }

  /** Enrol a person and hand back only the pseudonym. */
  enrol(identity, pseudonym) {
    if (!pseudonym) throw new Error('a pseudonym must be supplied, not derived from identity');
    this.mapping.set(pseudonym, { ...identity, enrolledAt: Date.now() });
    this.audit?.append({ actor: 'enrolment', action: 'privacy.enrolled',
      why: 'learner enrolled', learner: pseudonym });
    return pseudonym;
  }

  /** Revealing identity is a capability, an event, and a logged decision. */
  reveal(pseudonym, { authorizer, principal: p }) {
    authorizer.require(p, 'pii.reveal', { tenant: p.tenant });
    const rec = this.mapping.get(pseudonym) ?? null;
    this.audit?.append({ actor: p.id, action: 'privacy.pii_revealed',
      why: 'identity lookup under an explicit grant', learner: pseudonym });
    return rec;
  }

  /**
   * Erasure. Breaking the mapping is what makes the behavioural record
   * genuinely anonymous; aggregates survive because they contain no individual.
   */
  erase(pseudonym, { reason = 'learner request' } = {}) {
    const had = this.mapping.delete(pseudonym);
    this.erased.add(pseudonym);
    this.audit?.append({ actor: 'privacy', action: 'privacy.erased',
      why: reason, learner: pseudonym, after: { mappingRemoved: had } });
    return { erased: true, mappingRemoved: had,
             note: 'behavioural rows retained without any link to a person; aggregates unaffected' };
  }

  isErased(pseudonym) { return this.erased.has(pseudonym); }

  /** Strip anything that must not be exported, whatever the caller asked for. */
  sanitiseExport(rows) {
    return rows.map((r) => {
      const out = {};
      for (const [k, v] of Object.entries(r)) {
        if (NEVER_EXPORT.some((bad) => k.toLowerCase().includes(bad))) continue;
        out[k] = v;
      }
      return out;
    });
  }

  /** A storage guard: refuse to persist anything on the never-store list. */
  assertStorable(record) {
    const bad = Object.keys(record).filter((k) =>
      NEVER_STORE.some((n) => k.toLowerCase().includes(n)));
    if (bad.length) throw new Error(`refusing to store raw stream fields: ${bad.join(', ')}`);
    return true;
  }

  /** @returns {boolean} whether a row of the given class is past retention. */
  expired(cls, ageDays) {
    const limit = RETENTION_DAYS[cls];
    if (limit === null || limit === 'contractual') return false;
    return ageDays > limit;
  }
}
