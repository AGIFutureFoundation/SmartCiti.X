# Security — SmartCiti.X : Trade Craft Academy

This platform holds training records that decide whether someone is certified to
do dangerous work. The security posture follows from that: the assets worth
protecting are **a person's identity**, **the integrity of their certification**,
and **the boundary between one organisation's learners and another's**.

## What is implemented and tested

`security/` ships with 29 checks in `test.mjs` and 10 in `test_sbom.mjs`
(both run by `verify_all.sh`; each suite asserts the count stated here). Each
check is a refusal, or a hash held to the bytes in the tree:

| Module | Enforces |
|---|---|
| `authz.mjs` | deny-by-default capabilities, tenant isolation checked independently of capability, learner/instructor read scoping, contest self-scoping, time-boxed elevation; no agent role holds a human-only route |
| `ratelimit.mjs` | separate token buckets for auth, agent turns, API and export; audited auth throttling; idle sweep |
| `privacy.mjs` | data classification, per-class retention, pseudonymisation, erasure, export sanitisation, raw-stream storage refusal |
| `contest.mjs` | a learner contests a gate decision on their own record with a human (`gate.contest` → `gate.review`); anyone human reports abuse and support triages it (`abuse.report` → `abuse.triage`); PII redacted before storage, every step audited and attributed, an overturned decision returned as a revocation instruction for the bus's single gate writer rather than applied here |
| `build_sbom.py` | the software bill of materials (`registry/sbom.cdx.json`, CycloneDX 1.5): every vendored third-party file hashed, versioned from the string in the file, licensed by the banner in the file — and `test_sbom.mjs` holds it to `web/vendor/` and to `THIRD_PARTY.md` on every run |

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
| Cost exhaustion via agent calls | separate `agent` bucket; ACP-13 cost governor degrades the conversation plane, never the control plane | built and tested (`ops/jobs.mjs`, `ops/test.mjs`) |
| Prompt injection steering the dial | forbidden actions filtered after the model turn; bus refuses the publish | tested |
| Certification fraud (buying/farming a gate) | gates need unaided demonstrations at gate difficulty; hint farming cannot certify; a contested decision is reviewed by a human who is never the filer and never an agent | tested |
| Insider record tampering | audit is append-only; gates are awarded events; revocation is deliberate and attributed | tested |
| Re-identification of behavioural data | identity lives only in the enrolment mapping; erasure breaks it | tested |
| Affect data leaking to employers | affect stripped from every export; retention 90 days | tested |
| Raw biometric/keystroke capture | refused at the storage boundary | tested |
| Supply chain | zero runtime dependencies in every pack; the vendored browser libraries (three.js r160, MapLibre GL JS 4.7.1) listed in a CycloneDX 1.5 SBOM (`security/registry/sbom.cdx.json`) and verified by hash on every run | structural + tested |
| A third party added to the deployment without anyone writing it down | `web/lint_external.mjs` accounts for **every** external origin in every built page — fetched and disclosed in `THIRD_PARTY.md`, cited by a registry that stands behind it, offered as an outbound page link, or this bundle's own — and fails the build on a new one. It was written because a font CDN had been contacted on four page loads without appearing anywhere in the disclosure | tested |
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

### One open item a deployment must decide: the font CDN

Four pages (`trade_craft_landing`, `trade_craft_map`,
`smartcitix_trade_craft_academy`, `trade_craft_console`) load their typefaces
from Google Fonts. That is a third-party request made by the learner's
browser before the page renders, and it carries their IP address and user
agent to Google. It is now disclosed in `THIRD_PARTY.md` and pinned by
`web/lint_external.mjs`, but disclosure is not consent: under GDPR this is
the kind of transfer a DPIA has to cover, and it is the one place where a
bundle that otherwise reaches no network at runtime does.

The faces are Open Font License and every one already has a `system-ui`
fallback, so **self-hosting them removes the transfer without changing the
design** — it needs the font files fetched once, vendored under
`web/vendor/fonts/`, added to the SBOM, and the four `<link>` tags swapped
for a local `@font-face` block. That has not been done here: this
environment reaches no network, so the files cannot be fetched. Until it is,
the four pages contact Google and the other six do not.

## Launch checklist — status

The items a public launch requires, with what is actually the case. "Built and
tested" names where. "Open" names what kind of thing closes it — infrastructure
or people outside this tree, or a CI change the maintainers must approve — and
nothing here is closed by assertion. The roadmap's exit criterion for this
checklist (v4.0, workstream 2) requires a named human owner for every item
accepted as open; **this pass names none**, so the "Accepted by" column is
empty by design and the criterion is not met.

| # | Item | Status | Accepted by |
|---|---|---|---|
| 1 | **Authentication itself** — token issuance, MFA, session management and rotation | open — needs external infrastructure: an identity provider, not yet selected. This pack is the authorisation layer only | |
| 2 | **Transport and storage** — TLS, encryption at rest, key management | open — needs external infrastructure: the packs are in-process; a deployment must add all three | |
| 3 | **Persistence and backup** — database, backup/restore, tested recovery | open — needs external infrastructure: nothing in this tree survives a restart, and an audit log that does not survive a restart is not an audit log. Spec §25 describes the append-only journal-and-snapshot store this bundle was written against; it is specified, not present — no `store/` pack exists in this tree, and §25 says so in its own status note | |
| 4 | **Secrets management** and a rotation policy | open — needs external infrastructure | |
| 5a | **SBOM generation** | built and tested (`security/build_sbom.py` → `security/registry/sbom.cdx.json`; `security/test_sbom.mjs` verifies every hash, version and licence claim against `web/vendor/` on every run) | |
| 5b | **Dependency and container scanning in CI** | open — needs maintainer approval: no CI workflow was changed; it requires a workflow edit the maintainers must approve | |
| 6 | **Penetration test** by someone who did not write this | open — needs external people | |
| 7 | **Incident response** — on-call rotation, severity definitions, breach-notification timelines per jurisdiction, a rehearsed runbook | open — needs external people; the required shape is written below | |
| 8 | **The cost governor** (ACP-13) | built and tested (`ops/jobs.mjs` `CostGovernor` and `PLANES`; `ops/test.mjs` proves the control plane is structurally un-throttleable and the conversation plane degrades rather than refuses) | |
| 9a | **A route for a learner to contest a certification decision with a human** | built and tested (`security/contest.mjs`; `security/test.mjs`). Staffing the review queue is people and stays open under 7 | |
| 9b | **Abuse reporting** and triage | built and tested (`security/contest.mjs`; `security/test.mjs`). Staffing triage is people and stays open under 7 | |
| 10 | **Vulnerability reporting** — a monitored `security@` address, a disclosure policy with safe harbour, an acknowledgement SLA | open — needs external people; see below | |

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
