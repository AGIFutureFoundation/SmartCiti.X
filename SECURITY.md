# Security — SmartCiti.X : Trade Craft Academy

This platform holds training records that decide whether someone is certified to
do dangerous work. The security posture follows from that: the assets worth
protecting are **a person's identity**, **the integrity of their certification**,
and **the boundary between one organisation's learners and another's**.

## What is implemented and tested

`security/` ships with 16 checks (`node test.mjs`). Each is a refusal:

| Module | Enforces |
|---|---|
| `authz.mjs` | deny-by-default capabilities, tenant isolation checked independently of capability, learner/instructor read scoping, time-boxed elevation |
| `ratelimit.mjs` | separate token buckets for auth, agent turns, API and export; audited auth throttling; idle sweep |
| `privacy.mjs` | data classification, per-class retention, pseudonymisation, erasure, export sanitisation, raw-stream storage refusal |

Enforced elsewhere in the stack and tested there:

- **Single-writer contracts** (`bus/bus.mjs`) — a mentor agent cannot publish
  dial, profile or gate state. Checked at the bus *and* at the authz layer, on
  the principle that the rule that matters most should fail closed twice.
- **PII redaction inbound and outbound** (`fabric/agent.mjs`) — models leak too.
- **Prompt-injection containment** — mentor tool calls are filtered against a
  forbidden-action list *after* the model responds, so a model persuaded to try
  a forbidden action still cannot perform one.
- **Append-only audit** (`bus/audit.mjs`) — entries frozen, `entries()` copies.
- **Input guards** (`control/lpa.mjs`) — malformed telemetry is rejected and
  counted, never ingested.

## Threat model

| Threat | Mitigation | Status |
|---|---|---|
| Cross-tenant data access | tenant checked separately from capability, on every access | tested |
| Privilege escalation via role sprawl | no wildcard capability; `pii.reveal` held by no standing role | tested |
| Credential stuffing / brute force | strict `auth` bucket, audited throttling | tested |
| Cost exhaustion via agent calls | separate `agent` bucket; ACP-13 cost governor degrades the conversation plane, never the control plane | partial — governor specified, not built |
| Prompt injection steering the dial | forbidden actions filtered after the model turn; bus refuses the publish | tested |
| Certification fraud (buying/farming a gate) | gates need unaided demonstrations at gate difficulty; hint farming cannot certify | tested |
| Insider record tampering | audit is append-only; gates are awarded events; revocation is deliberate and attributed | tested |
| Re-identification of behavioural data | identity lives only in the enrolment mapping; erasure breaks it | tested |
| Affect data leaking to employers | affect stripped from every export; retention 90 days | tested |
| Raw biometric/keystroke capture | refused at the storage boundary | tested |
| Supply chain | zero runtime dependencies in every pack | structural |
| Stale deployed artefact | build stamp + `check_console.py` in CI | tested |

## Deliberate design decisions

**Identity is not in the analytics store.** Behavioural and derived data carry a
pseudonym; the mapping to a person lives in the enrolment service behind its own
capability. This is what makes erasure honest rather than cosmetic: break the
mapping and the remaining rows are genuinely not about an identifiable person.

**Affect is the most protected class, not the least.** It has the shortest
retention (90 days), never appears in an export, and is visible to the learner
and their instructor only. A system that inferred "this person gets anxious" and
let an employer read it would be doing harm with a feature meant to help.

**`pii.reveal` is a separate capability held by nobody.** It is granted per
incident, with a reason and an approver, expires on its own, and every use is an
audit event. Standing access to identity is how identity leaks.

**Fail closed, twice, on the rule that matters most.** A mentor agent is blocked
from writing control state by the bus *and* by authz. Defence in depth is worth
the duplication only where the consequence is severe; this is that case.

## Compliance posture — honest status

Mapping to obligations, with what is actually done versus what a launch requires:

| Obligation | Position | Required before public launch |
|---|---|---|
| **FERPA** (US education records) | pseudonymous store, access scoping, audit trail, erasure all built | written data-sharing agreements with institutional customers; designated school-official language |
| **GDPR / UK GDPR** | lawful-basis fields, retention limits, erasure, export sanitisation built | DPIA completed and signed; DPO named; SCCs for any non-EU processing; cookie/consent surface |
| **COPPA / under-18 apprentices** | no date of birth stored; age band only where legally required | verified parental consent flow; separate under-18 policy; no behavioural profiling of minors for anything but instruction |
| **WCAG 2.2 AA** | console uses semantic markup, visible focus, theme-aware contrast | full audit with assistive tech; VPAT; keyboard-only pass on every flow |
| **SOC 2 Type II** | audit logging, access control and change management exist in code | 3–6 month observation window; formal policies; external auditor |
| **State workforce / apprenticeship rules** | none claimed | legal review per jurisdiction before any certification claim |

**Nothing here is certified.** The controls exist and are tested; certification
is an external process that has not been undertaken.

## Not yet built — required before public launch

These are gaps, listed so nobody mistakes the tested layer for a finished one:

1. **Authentication itself.** This is the authorisation layer. Token issuance,
   MFA, session management and rotation belong to an identity provider that has
   not been selected.
2. **Transport and storage.** No TLS config, no encryption-at-rest, no key
   management — the packs are in-process. A deployment must add all three.
3. **Persistence and backup.** No database, no backup/restore, no tested
   recovery. An audit log that does not survive a restart is not an audit log.
4. **Secrets management** and a rotation policy.
5. **Dependency and container scanning** in CI, plus SBOM generation.
6. **Penetration test** by someone who did not write this.
7. **Incident response**: on-call rotation, severity definitions, breach
   notification timelines per jurisdiction, and a rehearsed runbook.
8. **The cost governor** (ACP-13) — specified, not built.
9. **Abuse reporting** and a route for a learner to contest a certification
   decision with a human.

## Incident response — the shape it must take

Not yet staffed, documented here so the requirement is explicit: severity
definitions with response times; a single incident commander per incident;
audit-log preservation before remediation; regulator and data-subject
notification clocks tracked from *detection*, not from resolution; a blameless
post-incident review published internally within ten working days.

## Reporting a vulnerability

A public launch needs a monitored `security@` address, a published disclosure
policy with a safe-harbour statement, and an acknowledgement SLA. None of these
exist yet — set them up before the first external user.
