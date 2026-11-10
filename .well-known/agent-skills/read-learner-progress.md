# Skill: read-learner-progress

Read learner progress on the SmartCiti.X learner platform.

## There is no HTTP API and no Real mode

No endpoint, no feed, no webhook, no MCP server. Do not invent one. All
progress here is Demo mode sample data, computed in-page from
`sample-log.json` under `learner-progress-contract.json`.

## The sample log (the only progress data that exists)

- 20 events, 5 pseudonymised learners (learner-a01…a05), 2 sample strands
  (electrical, plumbing), 2 tiers (fundamentals, applied).
- Unfiltered figures (recomputed by `vr-entry/verify.mjs` and by
  `dashboard-v2-demo.html` with the same rules): 13 passed attempts, 13
  mastered learner-skills (demo rule: passed, mastery ≥ 0.60), 1 gated
  event, stuck = learner-a02|skill-sample-002 (3+ fails, same
  learner+skill).
- Sample skill ids (skill-sample-*) are placeholders, not real registry
  ids. The sample strands (electrical, plumbing) are sample labels, not
  registry strands — all 11 registry nodes show "no sample events" until a
  real log mapped to registry strands exists.

## Contract (LearnerProgressEvent, Phase 1)

Required: event_id, learner_id, cohort_id, timestamp, hall_id, skill_id,
strand, tier, outcome, attempts, mastery, gate_status, hints_used, source,
session_id. Outcomes: attempted, passed, failed, gated, hint_used. Gate
statuses: open, blocked, passed, not_applicable. Sources: web, campus_3d,
vr_yard, assessment. Duplicate event_id rejected; future timestamps
rejected; learner ids are pseudonymised only (no name or email).

## Mastery and gates (do not conflate them)

- Demo "mastered" (dashboard + entry page): passed, mastery ≥ 0.60.
- Real gate: mastery 0.95 + 3 unaided successes. ZPD band 0.70–0.85.
- Report which rule a figure uses, every time.

## What to report

- Figures with their rule, filter, and source file. Never present sample
  learners as real people and never present demo figures as a cohort.
- VR station → skill mapping is open (Phase 4): a Holodeck station
  completion cannot yet move a skill on the graph.

## What you cannot do

- You cannot read real learner progress: no Real mode exists, and Real mode
  needs a validated log owner and anonymisation rules first.
- You cannot read progress from the scenario viewer: its checklist state is
  in-memory only and is not stored anywhere.
