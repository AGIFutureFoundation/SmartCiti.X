# Upgrade candidates — the sibling repositories

A reviewed survey (2026-09-09) of three AGI Future Foundation repositories
for assets the Academy could adopt. This page is hand-maintained survey
material, not generated from the registries; treat each row as a candidate
to be verified before adoption, per the roadmap's standing rules.

## 1. The pre-rebrand yard (`stonebyte-vr-bac-yard-`)

**The clearest orphaned Academy artifact found.** The repository holds a
complete single-file Three.js training-yard application — 25 interactive
stations of BAC (Bricklayers & Allied Craftworkers) masonry curriculum —
committed under the filename `README.md`. It predates the current identity;
the pre-rebrand product name it carries is a forbidden spelling here, so the
**data** (not the branding) has been recovered to
[`archive/bac_yard_stations.json`](../archive/bac_yard_stations.json): every
station's checklist, doctrine line, four interactive actions, machine-gradable
three-option quiz, and the 25-prop yard layout.

**Why it matters:** the masonry-family halls (`bricklayers`,
`masonry-restore`, `stone-carvers`, `tilesetters`, `terrazzo`, `refractory`,
plus safety stations matching `scaffold`, `site-safety`, `riggers`,
`surveyors`) currently hold skeleton-only registry slots. These stations are
real curriculum content — with citations in the trade's own vocabulary
(mortar types N/S/M, silica Table 1 controls, scaffold tagging) — that fits
those empty slots. Folding it in as authored content belongs to the v3.4
authoring milestone; its quizzes carry correct-answer flags, so each station
is machine-gradable today.

**Caveats:** despite the repository name there is no WebXR code — it is a
3D canvas yard, not a headset app — and the content is unverified general
practice, the same status as the rest of the curriculum.

## 2. `vr-safety-training` — engineering for the `vr_sim` modality

A complete, runnable Unity 6 + OpenXR VR safety-training prototype: five
walkable sites (construction, warehouse, fire response, chemical processing,
electrical maintenance), 11/11 tests passing. The Academy's `vr_sim` variant
band is addressable but unimplemented; this is the strongest engineering
candidate for it:

| Asset | Maps to |
|---|---|
| Deterministic scoring engine, with the LLM coach architecturally unable to change the score | The mentor fabric's guard contract (ACP-11) — same guarantee, already shipped |
| Ordered-procedure rubric (PPE → barricade → guardrail → cart → walkdown) with sequence gating | The jobsite-final assessment shape; step-order edit distance is computable from it |
| Session gating: minimum time per site, coach-turns per site before completion | A completion contract for hall-level modules |
| Privacy-conscious JSONL telemetry (no learner identity, no raw conversation) | The telemetry envelope's quality guards (ACP-08) |
| Procedural site generation with isolation hoarding between areas | The 3D counterpart of the generated hall floor plans |

Its five sites are workplace types, not trades, and its site list is a fixed
five-value enum — scaling toward 111 halls means making sites data-driven,
which is exactly what the interiors pack already knows how to feed.

## 3. `Locator.X` — machinery, not content

A different product (real-estate analytics and its own 92-lesson academy) in
a different domain: **no trades, union or taxonomy overlap** — but mature
machinery in the same engineering dialect as this bundle:

- A dependency-free canvas map renderer (a MapLibre-compatible subset) —
  directly relevant to keeping the campus map self-contained.
- A single-file build pipeline (module registry → minify → pack data into
  one HTML) — a more mature version of what `web/build_*.py` do.
- A shipped ZPD difficulty dial (per-track proficiency, tightening tolerance
  bands, difficulty-pooled content, hint-penalized scoring) — a second,
  independently written implementation of the Academy's own dial, useful as
  a cross-check.
- Curriculum-as-CSV with a build-gate validator that fails when catalog and
  shipped content disagree — the same doctrine as this bundle's staleness
  guards.
- A provenance discipline for generated layouts (`RECORDED` / `DERIVED` /
  `SCHEMATIC` on every line) that would strengthen the generated hall floor
  plans — and a no-library WebXR entry point with a graceful fallback.

## Disposition

Nothing on this page changes the packs today. The recovered yard data sits
in `archive/` with its [provenance](Provenance.md) recorded; everything else
is scheduled through [`ROADMAP.md`](../ROADMAP.md) (v3.4 authoring, v4.0
`vr_sim` pilot) so each adoption arrives with its own verifier, as the
standing rules require.

---

*Hand-maintained; reviewed 2026-09-09. The generated wiki pages carry the
registry truths — this page carries candidates only.*
