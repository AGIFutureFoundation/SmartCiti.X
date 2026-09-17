/**
 * Contest and abuse routes — a person reaching a person.
 *
 * SECURITY.md item 9: a learner must be able to contest a certification
 * decision with a human, and anyone must be able to report abuse. Both routes
 * are built the way the rest of this pack is built:
 *
 *   - deny by default through `Authorizer` (capability, then tenant, then the
 *     self-scope that `gate.contest` shares with `learner.read.self`)
 *   - rate-limited through the `api` bucket, and the throttle audited
 *   - PII in free text redacted BEFORE it is stored, with the same regexes the
 *     mentor fabric uses inbound and outbound (`fabric/agent.mjs`), imported
 *     rather than copied so there is one list of what counts as PII
 *   - every filing, resolution, report and triage an append-only audit entry
 *   - every record frozen
 *
 * What this module deliberately does NOT do: publish. An overturned contest
 * returns a `revocation` instruction addressed to the bus's single writer for
 * `gate.decision`; the bus publishes it (ACP-09) and `control/gates.mjs`
 * applies it. A security module that wrote gate state itself would be a second
 * writer of the one aggregate the whole stack keeps single-writer.
 *
 * Overturning withdraws the contested decision from the record. It never awards
 * a gate: a gate is earned by an unaided demonstration, and `gate.review` does
 * not carry `gate.certify`.
 */
import { redactPII } from '../fabric/agent.mjs';
import { TOPIC_OWNERS } from '../bus/bus.mjs';
import { Authorizer, AGENT_ROLES, ROLES } from './authz.mjs';
import { RateLimiter } from './ratelimit.mjs';

/** Closed sets. Anything outside them is refused, not coerced. */
export const CONTEST_OUTCOMES = Object.freeze(['upheld', 'overturned']);
export const ABUSE_KINDS = Object.freeze([
  'harassment', 'cheating', 'safety', 'content', 'impersonation', 'other',
]);
export const TRIAGE_ACTIONS = Object.freeze(['dismissed', 'escalated', 'actioned', 'referred']);

/** The topic a revocation travels on, and the only role that may publish it. */
export const REVOCATION_TOPIC = 'gate.decision';
export const REVOCATION_WRITER = TOPIC_OWNERS[REVOCATION_TOPIC];

/** Both routes share the general API allowance — a contest is not an auth attempt. */
export const BUCKET = 'api';

/**
 * No agent role may hold any of these. Asserted at import so the role table
 * cannot drift into granting an agent a human-only route without failing here.
 */
export const HUMAN_ONLY = Object.freeze(['gate.contest', 'gate.review', 'abuse.report', 'abuse.triage']);
for (const role of AGENT_ROLES) {
  for (const cap of HUMAN_ONLY) {
    if (ROLES[role].includes(cap)) throw new Error(`agent role ${role} holds human-only capability ${cap}`);
  }
}

export class Throttled extends Error {
  constructor(route, retryAfterSec) {
    super(`${route} refused: over rate, retry after ${retryAfterSec}s`);
    this.name = 'Throttled'; this.route = route; this.retryAfterSec = retryAfterSec;
  }
}

const text = (v, what) => {
  if (typeof v !== 'string' || !v.trim()) throw new Error(`${what} is required`);
  return v;
};
const oneOf = (v, set, what) => {
  if (!set.includes(v)) throw new Error(`unknown ${what} "${v}" — one of ${set.join(', ')}`);
  return v;
};

export class ContestDesk {
  /**
   * @param {object} deps
   *   audit       — required. A filing that is not on the record did not happen.
   *   authorizer  — defaults to a fresh `Authorizer` bound to the same audit.
   *   limiter     — defaults to a fresh `RateLimiter`; limiting always applies.
   */
  constructor({ audit, authorizer = null, limiter = null, now = () => Date.now() } = {}) {
    if (!audit) throw new Error('a contest desk needs an audit log — a filing that is not on the record did not happen');
    this.audit = audit;
    this.now = now;
    this.authorizer = authorizer ?? new Authorizer({ audit });
    this.limiter = limiter ?? new RateLimiter({ audit, now });
    this.cases = new Map();
    this.reports = new Map();
    this.seq = 0;
  }

  #throttle(route, principal) {
    const r = this.limiter.take(BUCKET, principal.id);
    if (r.allow) return;
    this.audit.append({ actor: principal.id, action: `${route}.throttled`,
      why: 'over rate on the api bucket', after: { retryAfterSec: r.retryAfterSec } });
    throw new Throttled(route, r.retryAfterSec);
  }

  /* --------------------------------------------------------- contests ---- */

  /**
   * A learner contests a gate decision on their own record.
   * @returns the frozen case
   */
  contest({ principal, tenant, learner, gate, reason }) {
    if (!principal) throw new Error('no principal');
    text(tenant, 'tenant'); text(learner, 'learner'); text(gate, 'gate'); text(reason, 'reason');
    this.authorizer.require(principal, 'gate.contest', { tenant, learner, gate });
    this.#throttle('contest', principal);
    const redacted = redactPII(reason);
    const c = Object.freeze({
      id: `contest-${++this.seq}`, tenant, learner, gate,
      reason: redacted.text, redactions: redacted.redactions,
      filedAt: this.now(), status: 'open', resolution: null,
    });
    this.cases.set(c.id, c);
    this.audit.append({ actor: principal.id, action: 'contest.filed', learner, skill: gate,
      why: `contest ${c.id} filed against the ${gate} decision`,
      after: { id: c.id, tenant, gate, redactions: c.redactions } });
    return c;
  }

  /**
   * A human with `gate.review` resolves a case in their own tenant. The filer
   * cannot resolve their own case, whatever roles they also hold.
   * @returns {{ case: object, revocation: object|null }}
   */
  resolve(caseId, { principal, outcome, reason } = {}) {
    if (!principal) throw new Error('no principal');
    const c = this.cases.get(caseId);
    if (!c) throw new Error(`no case ${caseId}`);
    this.authorizer.require(principal, 'gate.review', { tenant: c.tenant, learner: c.learner });
    if (principal.id === c.learner) {
      this.audit.append({ actor: principal.id, action: 'authz.deny',
        why: 'the filer cannot resolve their own contest', after: { capability: 'gate.review', case: caseId } });
      throw new Error('the filer cannot resolve their own contest');
    }
    if (c.status !== 'open') throw new Error(`case ${caseId} is already ${c.status}`);
    oneOf(outcome, CONTEST_OUTCOMES, 'outcome'); text(reason, 'reason');
    const redacted = redactPII(reason);
    const resolved = Object.freeze({
      ...c, status: 'resolved',
      resolution: Object.freeze({ outcome, reason: redacted.text, resolvedBy: principal.id, resolvedAt: this.now() }),
    });
    this.cases.set(caseId, resolved);
    this.audit.append({ actor: principal.id, action: 'contest.resolved', learner: c.learner, skill: c.gate,
      why: `contest ${caseId} ${outcome} by ${principal.id}: ${redacted.text}`,
      after: { id: caseId, outcome, resolvedBy: principal.id } });

    // An overturned decision is withdrawn by the bus's own writer, not by us.
    // The shape mirrors a `gate.decision` payload (`skill`, `pass`, `why`) with
    // the arguments `revokeSkillGate(profile, skillId, reason)` takes.
    const revocation = outcome === 'overturned' ? Object.freeze({
      topic: REVOCATION_TOPIC,
      publishAs: REVOCATION_WRITER,
      payload: Object.freeze({
        skill: c.gate, pass: false, revoked: true, learner: c.learner,
        why: `the ${c.gate} decision was overturned on contest ${caseId} by ${principal.id}`,
        contest: caseId, resolvedBy: principal.id,
      }),
      apply: Object.freeze({ fn: 'revokeSkillGate', skillId: c.gate,
        reason: `contest ${caseId} overturned by ${principal.id}: ${redacted.text}` }),
    }) : null;
    return { case: resolved, revocation };
  }

  /* ------------------------------------------------------------ abuse ---- */

  /** Any human reports abuse in their own tenant. */
  report({ principal, subject, kind, detail }) {
    if (!principal) throw new Error('no principal');
    text(subject, 'subject'); text(detail, 'detail'); oneOf(kind, ABUSE_KINDS, 'kind');
    this.authorizer.require(principal, 'abuse.report', { tenant: principal.tenant });
    this.#throttle('abuse', principal);
    const d = redactPII(detail), s = redactPII(subject);
    const r = Object.freeze({
      id: `abuse-${++this.seq}`, tenant: principal.tenant, reporter: principal.id,
      subject: s.text, kind, detail: d.text, redactions: d.redactions + s.redactions,
      filedAt: this.now(), status: 'open', triage: null,
    });
    this.reports.set(r.id, r);
    this.audit.append({ actor: principal.id, action: 'abuse.reported',
      why: `abuse report ${r.id} (${kind}) filed`,
      after: { id: r.id, kind, redactions: r.redactions } });
    return r;
  }

  /** `support` or `tenant_admin` triages, in their own tenant, never their own report. */
  triage(reportId, { principal, action, note } = {}) {
    if (!principal) throw new Error('no principal');
    const r = this.reports.get(reportId);
    if (!r) throw new Error(`no report ${reportId}`);
    this.authorizer.require(principal, 'abuse.triage', { tenant: r.tenant });
    if (principal.id === r.reporter) throw new Error('the reporter cannot triage their own report');
    if (r.status !== 'open') throw new Error(`report ${reportId} is already ${r.status}`);
    oneOf(action, TRIAGE_ACTIONS, 'action'); text(note, 'note');
    const n = redactPII(note);
    const triaged = Object.freeze({
      ...r, status: 'triaged',
      triage: Object.freeze({ action, note: n.text, triagedBy: principal.id, triagedAt: this.now() }),
    });
    this.reports.set(reportId, triaged);
    this.audit.append({ actor: principal.id, action: 'abuse.triaged',
      why: `abuse report ${reportId} ${action} by ${principal.id}: ${n.text}`,
      after: { id: reportId, action, triagedBy: principal.id } });
    return triaged;
  }
}
