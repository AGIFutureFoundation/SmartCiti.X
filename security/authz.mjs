/**
 * Authorization and tenant isolation.
 *
 * Deny by default. Every capability must be granted explicitly, and every data
 * access carries a tenant. The two failure modes this exists to prevent are the
 * ones that end education companies: one school seeing another school's
 * learners, and a support tool quietly acquiring the power to change records.
 *
 * This is the policy layer, not the authentication layer — it decides what an
 * already-authenticated principal may do. Token issuance and verification
 * belong to the identity provider (see SECURITY.md).
 */

/** Capabilities are verbs on resources. There is no wildcard by design. */
export const CAPABILITIES = Object.freeze([
  'learner.read.self', 'learner.read.assigned', 'learner.read.tenant',
  'profile.write', 'dial.override', 'gate.certify', 'gate.revoke',
  'content.read', 'content.author', 'content.publish',
  'agent.deploy', 'agent.eval',
  'audit.read', 'audit.export',
  'parity.read', 'parity.run',
  'tenant.admin', 'billing.manage',
  'gate.contest', 'gate.review',   // a learner contests a gate decision; a human reviews it
  'abuse.report', 'abuse.triage',  // anyone human reports abuse; support triages it
  'pii.reveal',                    // deliberately its own capability
]);

/**
 * Roles that are voiced by a model rather than held by a person. No agent role
 * may file a contest, review one, report abuse or triage it — those routes
 * exist so a person can reach a person (ACP-09: agents voice the system).
 */
export const AGENT_ROLES = Object.freeze(['mentor_agent']);

/**
 * Roles are bundles of capabilities. Note what is NOT here:
 *   - no role has `pii.reveal` by default; it is granted per incident
 *   - `mentor_agent` has almost nothing: agents voice the system (ACP-09)
 *   - `support` can read audit but cannot touch a learner record
 */
export const ROLES = Object.freeze({
  learner:       ['learner.read.self', 'content.read', 'gate.contest', 'abuse.report'],
  instructor:    ['learner.read.assigned', 'content.read', 'dial.override', 'audit.read',
                  'gate.review', 'abuse.report'],
  hall_admin:    ['learner.read.tenant', 'content.read', 'content.author',
                  'dial.override', 'audit.read', 'parity.read', 'gate.review', 'abuse.report'],
  content_author:['content.read', 'content.author', 'abuse.report'],
  publisher:     ['content.read', 'content.author', 'content.publish', 'abuse.report'],
  ml_engineer:   ['agent.eval', 'parity.read', 'parity.run', 'audit.read', 'abuse.report'],
  release_mgr:   ['agent.deploy', 'agent.eval', 'parity.read', 'audit.read', 'abuse.report'],
  support:       ['audit.read', 'abuse.report', 'abuse.triage'],
  tenant_admin:  ['tenant.admin', 'learner.read.tenant', 'audit.read',
                  'audit.export', 'parity.read', 'billing.manage', 'abuse.report', 'abuse.triage'],
  mentor_agent:  ['content.read'],
  auditor:       ['audit.read', 'audit.export', 'parity.read', 'abuse.report'],
});

export class AccessDenied extends Error {
  constructor(msg, detail) { super(msg); this.name = 'AccessDenied'; this.detail = detail; }
}

/** A principal is who is asking. Immutable once built. */
export function principal({ id, tenant, roles = [], grants = [], assigned = [] }) {
  if (!id || !tenant) throw new Error('a principal needs an id and a tenant');
  const caps = new Set();
  for (const r of roles) for (const c of (ROLES[r] ?? [])) caps.add(c);
  for (const g of grants) {                       // per-incident, time-boxed grants
    if (!CAPABILITIES.includes(g.capability)) continue;
    if (g.expiresAt && g.expiresAt < Date.now()) continue;
    caps.add(g.capability);
  }
  return Object.freeze({ id, tenant, roles: Object.freeze([...roles]),
                         caps: Object.freeze([...caps]),
                         assigned: Object.freeze([...assigned]) });
}

export class Authorizer {
  constructor({ audit = null } = {}) { this.audit = audit; this.denials = 0; }

  /**
   * The single decision point.
   * @returns {{allow:boolean, reason:string}}
   */
  check(p, capability, resource = {}) {
    const deny = (reason) => {
      this.denials++;
      this.audit?.append({ actor: p?.id ?? 'anonymous', action: 'authz.deny',
        why: reason, after: { capability, resource: redactResource(resource) } });
      return { allow: false, reason };
    };

    if (!p) return deny('no principal');
    if (!CAPABILITIES.includes(capability)) return deny(`unknown capability "${capability}"`);
    if (!p.caps.includes(capability)) return deny(`principal lacks ${capability}`);

    // Tenant isolation is checked SEPARATELY from capability, and always.
    // Holding a capability never implies holding it in another tenant.
    if (resource.tenant !== undefined && resource.tenant !== p.tenant) {
      return deny('cross-tenant access');
    }

    // A contest is self-scoped the way `learner.read.self` is: a learner may
    // contest a decision on their own record and no one else's. A resource
    // that names no learner is refused rather than assumed to be theirs.
    if (capability === 'gate.contest') {
      if (resource.learner === undefined) return deny('a contest must name the learner whose record it concerns');
      if (resource.learner !== p.id) return deny('learners may contest only decisions on their own record');
    }

    // Reading a learner narrows further by scope.
    if (capability.startsWith('learner.read') && resource.learner !== undefined) {
      if (p.caps.includes('learner.read.tenant')) {
        // tenant-wide read, already tenant-checked above
      } else if (p.caps.includes('learner.read.assigned')) {
        if (!p.assigned.includes(resource.learner)) return deny('learner not assigned to this instructor');
      } else if (p.caps.includes('learner.read.self')) {
        if (resource.learner !== p.id) return deny('learners may read only their own record');
      }
    }
    return { allow: true, reason: 'granted' };
  }

  /** Throwing variant for call sites that should never continue on denial. */
  require(p, capability, resource = {}) {
    const r = this.check(p, capability, resource);
    if (!r.allow) throw new AccessDenied(r.reason, { capability, principal: p?.id });
    return true;
  }
}

/** Resource descriptors reach the audit log; learner ids are identifiers. */
function redactResource(r) {
  const out = { ...r };
  if (out.learner) out.learner = `learner:${String(out.learner).slice(0, 4)}…`;
  return out;
}

/**
 * Time-boxed elevation, for the cases that genuinely need it (a support agent
 * investigating a specific incident). Never a standing role.
 */
export function grant(capability, { minutes = 60, reason, approver }) {
  if (!reason || !approver) throw new Error('an elevation needs a reason and an approver');
  return Object.freeze({ capability, reason, approver, expiresAt: Date.now() + minutes * 60000 });
}
