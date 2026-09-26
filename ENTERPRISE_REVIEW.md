# SmartCiti.X : Trade Craft Academy — enterprise review

*powered by AGI Corp*

A review of the whole bundle on 2026-09-26, for the four audiences the
Academy is meant to serve — nonprofits, corporations, training simulators
and unions — with what this pass built, what it found, and the order the
remaining work should take. Every figure below is the bundle's own; the
suites hold this file to the same numbers as every other surface.

## What was reviewed

The full bundle: every pack under `./verify_all.sh`, the spec, the roadmap,
the security posture, the front door, the walkable world, the console, and
the deploy workflow. The baseline run passed every suite once the one
Python dependency (`markdown`) was installed; the bundle's headline stood
at `1,594` checks and stands at the figure the README states now.

## What this pass built

| Increment | Where | Proof |
|---|---|---|
| **Heartbeats** — a monitored job, mentor, crew, station or service that stops reporting is a recorded lapse, once per lapse and once per recovery, on the same audit log; a safety-critical lapse reaches a halt hook; every ACP-13 job beats through the real scheduler | `ops/heartbeat.mjs` | `ops/test_heartbeat.mjs` |
| **Surface states** — the 61 authored floors and walls shown in the state the work leaves them in: wear from the room's governing hazards, intensity from its strand, wetting from a wet hazard or the weather; the closure emitted in full; the page derives with the same function the suite verifies | `surfaces/`, `web/build_3d.py` | `surfaces/test.mjs`, `web/test_3d.mjs` |
| **Crew consoles** — one console per crew of scripted agents: roster, standing, stop-work right, the run of hand-offs, and a live heartbeat board on a simulated clock | `console/` | `console/test.mjs` |
| **The front door** — a skip link, a section nav, a five-step first visit that deep-links into the flagship campus, a hall, a weather state and a crew console; every campus dot a door; a palette measured against WCAG AA at build time | `web/build_home.py` | the page's own figure gate |
| **The plaza** — five kiosks at every campus centre whose boards hold only doors, every list read from the registry that owns it | `web/build_3d.py`, `guide/` | headless Chromium: the boards open, a campus door lands, a hall door lands, the campus view stays inside its measured draw-call ceiling |
| **SUPPORT** — a mentor version that degrades in service, or goes silent, has its traffic pinned to the champion and its eval record invalidated until a fresh pass | `ops/support.mjs`, `ops/registries.mjs` | `ops/test_support.mjs` |
| **Locale machinery** — direction from a declared right-to-left set the validator enforces both ways; the count discovered, never typed; the figures lint holds every surface to it | `i18n/`, `brand/figures.mjs` | `i18n/test.mjs` |
| **Verification in CI** — `./verify_all.sh` on every push and pull request; the Pages workflow only deployed | `.github/workflows/verify.yml` | the workflow run |

Also corrected: `SECURITY.md` still said four pages loaded fonts from a
third party after they had been self-hosted; the console typed a check
count of its own; two phrases read as a locale total that were not.

## What it found

The product is unusually honest about itself, and the honesty is enforced
by code rather than by a style guide: every figure is read from a registry,
every claim carries the word for how it was come by, and a suite refuses
the surface that drifts. That discipline is the asset an enterprise buyer
will not find elsewhere. The gaps are real and are mostly the ones the
roadmap and the security document already name.

**Code gaps closed in this pass:** no liveness signal anywhere; no
consequence for a mentor that degraded after it shipped; a plaza with
nothing to do on it; a front door with no navigation; no CI gate on the
checks.

**Code gaps that remain, in the order they should be taken:**

1. **Durability.** The audit log does not survive a restart; spec §25's
   store is specified and not present. Every regulator-facing promise the
   audit log makes is hollow until it persists. Code, and the first thing
   a corporation or a union will ask about.
2. **An authentication boundary.** `security/` is authorisation only; there
   is no OIDC or SAML anywhere. An adapter in front of the authz roles, with
   the identity provider left as a deployment decision, is code. Choosing
   the provider is not.
3. **Records that can leave the browser.** The training recorder writes to
   the learner's browser and nowhere else. The xAPI adapter already exists;
   an opt-in egress to a learning record store, disclosed at the switch the
   way the voice switches are, is code.
4. **Tenancy.** The roadmap's Tenancy GA workstream has no exit criterion.
   Writing one (isolation, erasure, retention, per-tenant locale defaults,
   each a check) is the first step, and the security suite already holds
   the isolation half.
5. **The scene eval in CI.** `web/eval_scene.mjs` measures the walkable
   world in Chromium against ceilings taken on one machine. Running it in a
   workflow means re-measuring its baseline on the runner; until then it
   stays opt-in and local, and this review ran it by hand.

**Gaps that need people, not code:** native review of the seven non-English
catalogs (no reviewer has been named; none was invented); at least one
hall's content signed off by journey-level practitioners; a penetration
test; an incident-response owner and a `security@` address; the one admin
click that switches GitHub Pages on; a physical headset for the VR seat.

## By audience

**Unions.** The union roster is a taxonomy of trades, not a roster of
chartered locals, and says so. What a union needs before it can adopt a
hall is the practitioner sign-off the pack already has a mechanism for
(`pack/hall_signoff.mjs`), and a legal review of certification language per
jurisdiction, which the spec forbids the product from claiming on its own.
The crews and their stop-work rights are general practice pending that
authoring, labelled as such.

**Training simulators.** Eleven operable seats with schematic physics,
deterministic rubrics and a scripted reference operator. They are practice,
not certification, and every panel says so. The step from here is a real
machine's response curve under a named instructor's review, seat by seat,
and a headset in a hand.

**Corporations.** Procurement will ask for the security checklist at zero
open items, a persisted audit log, single sign-on, tenancy and a SOC 2
path. The cost governor, the rate limits, the contest and abuse routes and
the SBOM are built and tested; items one to four above are the gap.

**Nonprofits.** The bundle is a static site that runs from any host, needs
no accounts, works offline once loaded, and carries a flipped-classroom
model for schools. The barrier is not cost; it is the Pages switch and,
for community programmes, catalogs a native speaker has read.

## What this review did not do

It did not review any translation, sign off any content, run on a headset,
or test against a real cohort. It measured what a machine can measure and
left the rest labelled as the roadmap labels it.
