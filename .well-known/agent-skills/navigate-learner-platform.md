# Skill: navigate-learner-platform

Navigate the SmartCiti.X learner platform — for agents that need to
reference exact content.

## Doors (read these first)

- `vr-entry/index.html` — Learner VR Entry: mode picker (VR / desktop /
  mobile), guided first path (skills → coach → Holodeck), skill-graph SVG
  (11 registry strands on 3 tier rings), Holodeck Coach, Holodeck entry
  button (IWSDK player link), sequencer panel.
- `scenarios/index.html` — Training scenarios viewer (6 scenarios, works
  from file://, `?scenario=` deep links).
- `scenarios/scenarios.json` — Scenario index.
- `dashboard-v2-demo.html` — Cohort Dashboard v2, demo mode, sample data.
- `learner-progress-contract.json` — LearnerProgressEvent JSON Schema.
- `sample-log.json` — 20 anonymised events, 5 pseudonymised learners.

## Scenarios (6)

| Scenario | Audience | Tier |
| --- | --- | --- |
| k12-arvr-foundations | K-12 learners | fundamentals |
| union-trades-electrical | Union trades (electrical) | applied |
| union-trades-hvac | Union trades (HVAC) | applied |
| robotics-integration | Robotic + human integration | applied |
| safety-procedures | All learners (cross-cutting) | fundamentals |
| dental-screening-outreach | Outreach learners | applied |

Deep link: `scenarios/index.html?scenario=<scenarioId>`.

## Skill graph (11 registry strands, verbatim)

coordination, documentation, inspection, layout, leadership, machines,
materials, procedure, safety, tools, troubleshooting. ZPD band 0.70–0.85;
gate 0.95 + 3 unaided successes. "Mastered" on the entry page uses the
dashboard demo rule (passed, mastery ≥ 0.60) and is labelled as such.

## What you cannot do

- You cannot move a learner's skill on the graph: VR station → skill
  mapping (Phase 4) is open — real station IDs are needed first.
- You cannot invent a training site, city, or address. Louisiana + Indiana
  sites are proposed/planned; none is named.
- You cannot name a hall as a partner. The 111-hall roster is an in-repo
  list; 0 of 111 signed off by a named practitioner.
