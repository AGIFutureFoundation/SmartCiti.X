/**
 * ACP-11 Plane 2 — the mentor agent contract and the middleware every mentor
 * runs behind. Framework-agnostic: LangChain/LangGraph wiring adapts to this,
 * not the other way round, so the guards are testable without an LLM call.
 *
 * The load-bearing rule (ACP-09): mentors are READ-ONLY consumers of control
 * state. They voice the system; they never steer it. That is enforced here in
 * code rather than asked for in a prompt.
 */

/** Control-plane surfaces a mentor may read. Anything else is out of scope. */
export const READ_SCOPES = Object.freeze([
  'profile.summary', 'dial.state', 'module.content', 'hint.ladder', 'skill.graph',
]);

/** Actions no mentor may ever take, whatever it is asked. */
export const FORBIDDEN_ACTIONS = Object.freeze([
  'dial.set_setpoint', 'dial.pin', 'profile.write', 'gate.certify',
  'profile.read_other_learner', 'registry.write', 'override.apply',
]);

export class ScopeViolation extends Error {
  constructor(action) {
    super(`scope: mentors may not perform "${action}"`);
    this.name = 'ScopeViolation';
    this.action = action;
  }
}

/* ------------------------------------------------------------------ PII ---- */
const PII_PATTERNS = [
  [/\b\d{3}-\d{2}-\d{4}\b/g, '[redacted-id]'],
  [/\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b/g, '[redacted-email]'],
  [/\b(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b/g, '[redacted-phone]'],
  [/\b\d{1,5}\s+[A-Z][a-z]+\s+(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Lane|Ln)\b/g, '[redacted-address]'],
  [/\b(?:\d[ -]?){13,16}\b/g, '[redacted-card]'],
];

export function redactPII(text) {
  if (typeof text !== 'string') return text;
  let out = text, hits = 0;
  for (const [re, rep] of PII_PATTERNS) {
    out = out.replace(re, () => { hits++; return rep; });
  }
  return { text: out, redactions: hits };
}

/* ----------------------------------------------------------- escalation ---- */
const ESCALATION_TRIGGERS = [
  { id: 'safety_incident', re: /\b(injur|bleeding|electrocut|fell from|unconscious|ambulance)\w*/i },
  { id: 'distress',        re: /\b(kill myself|hurt myself|can'?t go on|end it all)\b/i },
  { id: 'harassment',      re: /\b(harass|threaten(?:ed|ing)?|assault(?:ed)?)\b/i },
  { id: 'credential_fraud', re: /\b(fake|forge|buy)\s+(my\s+)?(cert|certificat|licen[cs]e|ticket)\w*/i },
];

export function detectEscalation(text) {
  for (const t of ESCALATION_TRIGGERS) if (t.re.test(text)) return t.id;
  return null;
}

/* -------------------------------------------------------------- mentor ----- */
/**
 * A mentor implementation supplies `respond(turn) -> {text, rung?, handoff?,
 * actions?}`. Everything else — redaction, scope enforcement, escalation,
 * rung clamping — happens here, identically for every mentor.
 */
export class Mentor {
  /**
   * @param {object} spec   {id, name, union, persona, scopes?}
   * @param {object} impl   {respond(turn, ctx)}
   */
  constructor(spec, impl) {
    this.spec = spec;
    this.impl = impl;
    this.scopes = spec.scopes ?? READ_SCOPES;
    this.version = spec.version ?? '0.1.0';
    this.telemetry = [];
  }

  read(surface, ctx) {
    if (!this.scopes.includes(surface)) throw new ScopeViolation(`read:${surface}`);
    return ctx[surface];
  }

  /**
   * One turn. Returns {text, rung, handoff, escalated, violations, redactions}.
   * A scope violation is CONTAINED, not thrown: the turn is refused, logged and
   * counted, because a mentor that tries something forbidden must be
   * measurable by the eval harness rather than crashing the hall.
   */
  async turn(input, ctx = {}) {
    const inRedact = redactPII(String(input));
    const escalated = detectEscalation(inRedact.text);

    let raw;
    try {
      raw = await this.impl.respond({ text: inRedact.text, ...ctx }, ctx);
    } catch (err) {
      raw = { text: 'Let me get a human instructor for this one.', error: String(err) };
    }

    const violations = [];
    for (const a of raw?.actions ?? []) {
      if (FORBIDDEN_ACTIONS.includes(a)) violations.push(a);
    }

    // A mentor may never serve deeper help than the ladder allows here.
    //
    // The fallback is 0, not 5. It used to be 5, which meant that any caller
    // who forgot to stamp a ceiling got the FULL ladder including
    // co-completion — the sequencer stamped it only on verification picks, so
    // in practice every ordinary task ran unfaded (v2.7 defect 14). A missing
    // safeguard value must resolve to the most restrictive reading, never the
    // most permissive: an absent ceiling means nobody decided, and nobody
    // deciding is not permission.
    const ceiling = ctx.scaffold_ceiling ?? 0;
    const asked = ctx.requested_rung ?? 0;
    let rung = Math.max(0, Math.min(raw?.rung ?? 0, 5));
    const overHelped = rung > Math.max(asked, 0);
    rung = Math.min(rung, ceiling);

    const outRedact = redactPII(raw?.text ?? '');
    const record = {
      mentor: this.spec.id,
      version: this.version,
      rung,
      requested_rung: asked,
      over_helped: overHelped,
      handoff: raw?.handoff ?? null,
      escalated,
      violations,
      redactions: inRedact.redactions + outRedact.redactions,
      text: violations.length
        ? "That's not something I can do — I'll flag it for your instructor."
        : outRedact.text,
    };
    this.telemetry.push(record);
    return record;
  }
}
