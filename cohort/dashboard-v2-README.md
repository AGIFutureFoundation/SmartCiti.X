# Branch-ready change set — Cohort Dashboard v2, Demo mode only

Status: Local review set, 2026-10-24. NOT pushed, branched, or opened as a pull request on GitHub.

## Files in this set
- `learner-progress-contract.json` — Phase 1 LearnerProgressEvent JSON Schema. Maps to a new contract file in the repo; do not replace the existing registry or sequencer.
- `sample-log.json` — 20 anonymised events, 5 learners, 2 strands (electrical, plumbing), 2 tiers (fundamentals, applied). Placeholder skill/hall ids, not real registry ids.
- `dashboard-v2-demo.html` — Standalone Demo-mode dashboard. Embeds the sample log, computes figures with pure functions in-page, and offers strand / tier / source filters. Banner always says "Sample data, not real learners."
- This README — mapping and acceptance notes for the eventual repo change.

## Intended repo mapping (to confirm on branch creation)
- Contract → new file alongside `cohort/` (name to match repo conventions on branch)
- Sample log → new sample file under `cohort/` for Demo mode only
- Dashboard v2 → new version of `cohort/dashboard.mjs` + `cohort/dashboard.html`, keeping v1 pure-function style and additive tests
- Do NOT change: `pack/registry/skills.json`, `control/graph.mjs` sequencer rules, gate rules, or existing tests, except by additive tests

## Acceptance, as in the spec
- [ ] Demo mode renders with the sample banner
- [ ] Filters recompute all figures from the filtered set
- [ ] Duplicate event_id rejected, invalid skill_id fails validation (to be implemented in the repo version; this demo uses validated sample data only)
- [ ] No personal data in any view or sample
- [ ] Existing v1 figures for the same sample log unchanged, or change documented

## Open questions before a GitHub branch
1. Exact existing session-log format in `cohort/build.mjs` — reconcile or add a converter
2. Real VR station ids for Phase 4 mapping
3. Owner and anonymisation rules for any real cohort log before Real mode ships
