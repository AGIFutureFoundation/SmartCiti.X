# Safety Gate

SmartCiti.X : Trade Craft Academy, powered by AGI Corp

The Safety Gate decides whether a learner may enter a hazardous **training** station or simulator seat in the virtual campus.

## What this is not

This is a gate for a training simulator. It is **not a real-world safety system.** It does not satisfy OSHA or any other regulation, standard or code, and nothing here should be read as a claim that it does. It protects nobody on a real site. It is not a permit-to-work system, an induction record or a PPE register, and passing it certifies nothing. The hazard data it reads comes from `surfaces/registry/finishes.json`, which describes itself as "general good practice, not a code reference". The gate inherits that status. A real deployment uses the site's own permit, induction and PPE process, signed off by competent people.

## What it enforces

`canEnter(learner, target, context)` returns `{allow, reasons, required}`. It is pure: it reads its inputs and writes nothing. `enter()` makes the same decision and then records it.

**Which targets are hazardous** comes from the registries. No list of hazardous targets is typed anywhere in this code:

| Signal | Source |
|---|---|
| room hazard (molten-metal, work-at-height, mobile-plant, rotating-machinery...) | `surfaces/registry/finishes.json` → `halls[hall].conditions[strand].hazards` |
| PPE that only a hazard adds (face shield, harness, FR clothing...) | the same conditions, checked against `hazard_conditions` |
| a working floor (the room's conditions require a hard hat) | the same conditions |
| a zero-tolerance rubric axis (`pass: "== 0"`) | `sims/registry/sims.json` → the `rubric` of each seat |
| permit class: hot work, confined space, lock-out, work at height | a room hazard, or the target's own text (name, checklist, task, walkaround) on a working floor |

Stations are cross-checked against the surfaces record. A station whose `room_ppe` disagrees with the surfaces record fails the test suite. A sim is classified once for each hall it is bound to, because the room conditions differ from hall to hall.

**To enter a hazardous target, all of these must hold:**

1. **Site induction.** The learner has an in-date induction scoped to the target's hall (`hall:<slug>`) or its district (`district:<d>`, read from `unions/registry/unions.json`).
2. **PPE.** A door check for *this* learner at *this* target, no older than 5 minutes, lists every item the room's own conditions require, plus the PPE that any permit class adds. Item names must match exactly, so case and whitespace variants do not count.
3. **Permit.** Each permit class the target triggers needs a permit for this learner and this target. The permit must be in date, issued by an assigned instructor in the same tenant, and present unaltered on the chained log.
4. **Tier.** The learner has passed the `<hall>.safety.<tier>` skills below the target's tier. A safety-strand station requires only the tiers below its own, so the induction room is never locked behind itself.

A context older than 5 minutes is refused, and so is one dated in the future. Target and learner ids must be canonical registry ids, and the gate never normalises them.

## Overrides

- Only a principal built by `security/authz.mjs` with the `instructor` role can issue an override, and that principal must have the learner assigned and share the learner's tenant. Learners, peers, `mentor_agent` (including an agent that also claims `instructor`), hall admins, support staff and hand-forged principals are all refused.
- An override needs a reason of at least 12 characters. It is time-boxed to 1–60 minutes and bound to one learner and one target.
- Every override request goes on the log through `bus/audit.mjs`'s `AuditLog`, including refused ones (`safety_gate.override.granted` / `.refused`). A granted override is also published as `override.applied` through the bus by its single writer, `instructor_ui`.
- When an override admits someone, the log records a `safety_gate.allow` row and a `safety_gate.override.consumed` row with the actor, the reason and the expiry. An override can be used only once, so replaying it fails.
- An override never waives PPE. An expired override, an altered one (for example, a pushed-out expiry) or one that is not on the chained log does not admit anyone.

## The audit chain

`SafetyLedger` writes onto the repo's own `AuditLog` and keeps a SHA-256 hash chain over the gate's rows. Each hash is computed from the previous hash and the canonical row. `verify()` detects a rewritten row, a deleted row, and a `safety_gate.*` row inserted outside the chain. Permits and overrides are tokens of the form `{seq, hash, ...fields}`. The gate accepts one only when it matches a chained row exactly.

## Files

- `gate.mjs`: index building, `canEnter`, `enter`, `grantOverride`, `issuePermit`, `SafetyLedger`. It uses only Node built-ins and repo modules.
- `bypass_fixtures.mjs`: a deterministic generator of bypass attempts and legitimate entries, built from the derived index.
- `test.mjs`: `node safety_gate/test.mjs`. It prints the hazard classification and one `ok` line per check, and exits 1 on any failure.

## Limits, honestly

- Permit-class detection is a phrase match over authored text. It can miss a hazard the text does not name, and it can flag a target whose text mentions one in passing. The evidence behind each permit requirement is kept on the target (`permitEvidence`) so a reviewer can see why it was flagged.
- The induction, tier and PPE records come from the caller. The gate checks that they are present, scoped, in date and exact. It cannot know whether the person actually did the induction or actually wore the gear.
- The log is held in memory. The chain shows that rows were not changed after they were written. It does not stop someone who controls the process from replacing the whole log and its head. For that, publish the head somewhere the gate does not control (`verify({expectHead})`).
