# SmartCiti.X learner platform — Track A + Track B notes (2026-11-07)

Local / staging only. Nothing pushed, shared, posted, sent, or deployed.

## Track A — detailed environments + simulations

6 runnable training scenarios (5 steps each) + a self-contained viewer.
`vr-entry/` was NOT touched — the UI-toggle programme owns it (see
Conflicts); all work here is additive in `scenarios/` + repo root.

### New files

- `scenarios/k12-arvr-foundations.json` — K-12 AR/VR foundations
  (measure, tools, safety). Fundamentals.
- `scenarios/union-trades-electrical.json` — panel & conduit install.
  Applied. Deep-links to TradePath `/?zone=electrical`.
- `scenarios/union-trades-hvac.json` — diagnose, braze & commission.
  Applied. EPA Section 608 grounded. Deep-links to TradePath `/?zone=hvac`.
- `scenarios/robotics-integration.json` — human-robot integration in a
  shared cell. Applied.
- `scenarios/safety-procedures.json` — hazards, PPE, fit, report.
  Fundamentals. Cross-cutting, OSHA PPE grounded.
- `scenarios/dental-screening-outreach.json` — prevention & school
  screening. Applied. CDC grounded. Deep-links to TradePath
  `/?zone=outreach-hub`.
- `scenarios/scenarios.json` — index of the 6 scenarios (ids, titles,
  audiences, strands, tiers, files, viewer deep links).
- `scenarios/index.html` — standalone viewer: scenario list, 5-step
  checkable run with progress bar, restart, TradePath + VR-entry links,
  sources. Self-contained (zero network requests, works from `file://`);
  the scenario data is embedded inline and `verify.mjs` proves it matches
  the JSON files. `?scenario=<id>` deep link.
- `scenarios/verify.mjs` — read-only checker (see Verification).

### Grounding (nothing invented)

- Registry strands verbatim (11): coordination, documentation, inspection,
  layout, leadership, machines, materials, procedure, safety, tools,
  troubleshooting.
- OSHA PPE topic page (osha.gov) — Firecrawl scrape 2026-11-07.
- EPA Section 608 (epa.gov/section608; 40 CFR Part 82 Subpart F) —
  Firecrawl scrape 2026-11-07.
- CDC Infection Control Guidelines 2003 (MMWR 52(RR17)) via the
  UnspokenSmiled-VR wiki research notes.
- SmartCiti.X wiki: 111-hall roster is an in-repo list, 0 of 111 signed
  off; 11 simulators; 10 authored campuses (not physical); "nothing here
  certifies anybody".
- Louisiana + Indiana training sites: proposed/planned in every scenario;
  no site, city, or address named. No hall is mapped in any scenario
  (`mapped_hall: null`) — hall mapping is open (Phase 4).
- All content labelled simulation only / demo mode — NOT certification,
  licensure, or clinical training.

## Track B — fully agentic resources (repo root)

- `ai-catalog.json`, `agent.json`, `llms.txt`, `robots.txt` (Content-Signal
  ai-train=no, search=yes, ai-input=yes + Agentmap → /ai-catalog.json),
  `auth.md` (human-gated; no accounts, no OAuth, no tokens, no register_uri;
  no contact address published — do not invent one).
- `.well-known/agent-skills/` — 4 skills (navigate-learner-platform,
  run-a-training-scenario, read-learner-progress, safety-and-limits) +
  `index.json` with sha256 digests (all 4 verified DIGEST OK).
- `.well-known/api-catalog` — linkset of REAL resources only. No API exists:
  no HTTP endpoint, no MCP server, no OAuth, no live feed, no Real mode.
  Progress is the local sample log + in-page computation.
- `scenarios/scenarios.json` is the machine-readable scenario index; the
  viewer deep-link pattern is `scenarios/index.html?scenario=<id>`.

## Verification (exact results, 2026-11-07)

- `node scenarios/verify.mjs` → **All checks passed.** 6 files; index
  lists exactly the files; embedded viewer data deep-equals the JSON files;
  all strands are registry strands; all tiers valid; all steps reference
  stations defined in their file; TradePath deep links name known zones;
  inline viewer JS parses.
- All scenario JSON files parse; all ai-catalog / api-catalog hrefs resolve
  to real files.
- `node vr-entry/verify.mjs` (read-only; toggle programme's file) →
  **All checks passed** (20 events, 5 learners, 13 passed, 13 mastered demo
  rule, 1 gated, stuck = learner-a02|skill-sample-002).
- Existing files untouched: `dashboard-v2-demo.html`, `README.md`,
  `learner-progress-contract.json`, `sample-log.json` (all 2026-10-24).

## Conflicts with the UI-toggle programme

- `vr-entry/` was NOT touched by this track. At task start (13:46 PST)
  `vr-entry/index.html` was 0 bytes (mtime 21:46 UTC) — the toggle
  programme was mid-build; a python `build.py` write had truncated it
  (same EPERM pattern as below). By 21:55 UTC it was rebuilt to 50,764
  bytes and `verify.mjs` passes. Also present: 0-byte `index.html.restored`
  (21:21 UTC) and 0-byte `index4.html` (21:50 UTC) — truncated-write
  artifacts, left alone.
- No conflicts in `scenarios/` or the repo-root agent pack (all new files).

## Sandbox EPERM (persistent, 2026-11-07)

Exec-based file writes fail intermittently with EPERM; `open(..., "w")`
truncates before raising EPERM. Use the file tools for all file writes.
Do NOT run `vr-entry/build.py` here (it truncates `index.html`).

## Still needs Mike's device (not verified here)

- No real phone / desktop WebGL / Quest run: viewer and VR-entry renders,
  touch targets, Holodeck joystick, and Enter XR are all unverified on
  hardware (no WebGL, no live browser in this environment).
- No loopback HTTP serve check in this sandbox (known environment limit);
  the viewer works from `file://` by design, and over HTTP on a normal
  machine.
- VR station → skill mapping (Phase 4) is open — real station IDs needed.

## Ready for approval

- Track A scenarios + viewer (verified by `verify.mjs`); Track B agent
  pack. Nothing pushed or deployed. Suggested next step: Mike opens
  `scenarios/index.html` from disk (or served) on a real browser/phone,
  picks a scenario, and confirms the steps render and check off — then
  decides the push target with the vr-entry owner.
