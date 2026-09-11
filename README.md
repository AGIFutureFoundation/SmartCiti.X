# SmartCiti.X : Trade Craft Academy — implementation bundle v3.2

*powered by AGI Corp*

Gamified training to enhance robotic and human integrations.
The Adaptive Stack: the packs implementing the ACP protocol suite (v3.2) —
counted, like everything else here, by the table below rather than by a
number that can drift from it.

**489 checks, all passing from inside this bundle**, with no model credentials
required.

```bash
./verify_all.sh                    # everything below, one exit code
```

Or individually — every path inside a pack resolves against its own module
location, so these run from any working directory (v2.6 defect 13):

```bash
node unions/verify.mjs             # 24 — roster, districts, campuses, chapters, pack agreement
node pack/verify.mjs               # 19 — the registry, and all 11,000,000 IDs
node control/test.mjs              # 12 — learner profile, ZPD dial, affect
node control/test_graph.mjs        # 20 — skill graph, sequencer, gates
node control/test_hints.mjs        # 21 — the hint ladder, fading, the ceiling contract
node fabric/test.mjs               # 16 — mentor guards, eval harness, router
node bus/test.mjs                  # 15 — bus contracts, telemetry guards, audit
node bus/test_safeguards.mjs       # 15 — parity, stop conditions, overrides
node security/test.mjs             # 16 — authz, tenancy, rate limits, privacy
node ops/test.mjs                  # 41 — registries, rollout lanes, jobs, cost governor
node ops/fuzz.mjs                  #  9 — side doors around the promotion gates
node brand/test.mjs                # 30 — naming, tokens, contrast, livery, the lint itself
node brand/lint.mjs .              # fails on any forbidden spelling anywhere in the tree
node i18n/test.mjs                 # 16 — locale parity, placeholders, pack agreement
node stations/test.mjs             # 13 — recovered stations vs roster, skills, rooms
node surfaces/test.mjs             # 24 — finishes, conditions, more-demanding-wins, honesty
node geo/test.mjs                  # 27 — real coordinates + RECORDED anchors, recomputed distances, GeoJSON + the network map file
node sims/test.mjs                 # 22 — simulator bindings, rubrics, cockpit + scoring + regional scenarios
node tools/test.mjs                # 13 — district tool cribs, the deterministic crib drill, hall bindings
node schools/test.mjs              # 15 — flipped-classroom model, proposed districts, live units + class drills
node avatars/test.mjs              # 25 — locker depth, crews, characters, costumes, the TradeApes, marks policy, the guarantee
node parcels/test.mjs              # 15 — the city-records source contract: authorities, licences, frames, imagery, honesty
node agents/test.mjs               # 25 — the advisors: who stands where, quote-not-copy bindings, and the closed book
node meta/test.mjs                 # 24 — the metaverse layer: standards, the Unity avatar review, the complete VRM skeleton and how it moves, import policy, honesty
node control/fuzz.mjs              # 21 — hostile inputs and adversarial learners
node control/soak.mjs              # long-run invariants, 4,000 attempts x 3 seeds
python3 console/check_console.py   # fails if the console is behind its sources
python3 wiki/build_wiki.py --check # fails if the wiki is behind the registries
```

| Pack | Spec | What it is |
|---|---|---|
| `unions/` | — | **The union registry**, separated from the module pack: the 111-hall taxonomy, its eight districts and the three-campus network (Treasure Island–San Francisco, Oakland, New Orleans), a builder with a source stamp, and a verifier that proves the module pack still agrees with the roster |
| `pack/` | ACP-10 | Module registry at 111-hall scale: 25,875 authored skeleton objects (consuming the union roster), a consumer library that generates all 11,000,000 module IDs from them, and a verifier that proves uniqueness over the whole population rather than a sample |
| `control/` | ACP-02/03/04/05/06/07/15 | The deterministic control plane — profile, dial, affect, hint ladder, skill graph, sequencer, assessment gates — with two simulation harnesses |
| `fabric/` | ACP-11/12 | Mentor contract and middleware, the five-gate eval harness with adversarial stubs, supervisor/swarm router |
| `security/` | — | Deny-by-default authorization with tenant isolation, rate limiting, data classification, retention and erasure; plus `SECURITY.md` with the threat model and an honest launch checklist |
| `ops/` | ACP-13 | The three registries with a pipeline transition table, hall-by-hall rollout lanes that ask ACP-08 rather than re-deciding, the seven-job automation loop, and the cost governor that cannot throttle the control plane |
| `web/` | — | The published pages and their builders: landing page, rendered protocol spec, the languages page, the campus plan with a generated floor plan for every hall, the **network geomap** (`trade_craft_geomap.html` — the geo registry on a real WGS84 map with vendored MapLibre GL: RECORDED campuses, anchors and city frames, DERIVED great-circle routes, provenance in every popup, no basemap tiles unless asked for, and on request the public-domain USGS orthoimagery plus the city's own building footprints fetched live from its authority and extruded), the **interactive layered map** (districts, pipeline, module layers, training stations, the district tool crib on every hall panel and floor plan, all locales, searchable and deep-linkable) and the **3D environment** (the three-campus network as a 3D board — enter a campus city, then any hall for its extruded floor plan, fixtures, station beacons and first-person walk mode; each campus carries its own atmosphere — sky, fog, drifting fog banks over Treasure Island, a synthesized ambient bed of wind, gulls, harbor horns, insects and thunder (no recordings), and a day/night/storm cycle derived from the same records: crushed sky and moonlight after dark, grey light, thicker fog and falling rain in the storm — optimized to a measured budget — identical geometry shared through one cache and per-building decoration merged into one mesh per material (campus scene: ~997 → 430 draw calls), the hall/finish/avatar payload deduped on the wire and inflated at boot (3D page 660 → 432 KB, interactive map 264 → 138 KB), and an adaptive quality ladder that steps resolution and shadows down when the frame rate stays under budget — the authority's public-domain orthoimagery laid under the city layer on request, georeferenced off the same campus record the RECORDED anchors use, plus a live campus minimap that rings fully-worked halls, campus-wide completion rollups in the HUD, the learner's own avatar riding the training machines, and the district tool crib hung and clickable in every hall's tools room; experimental WebXR entry — VR and AR buttons that appear only where the platform offers the session — portable saves: the device-local record exported and imported as JSON by the learner alone; and the metaverse layer's doors — the avatar and any hall exported as named glTF 2.0 binaries, and the learner's own .glb rendered on the locker's guest stand) |
| `brand/` | — | The canonical identity: names and forbidden spellings with reasons, the two-theme token set, the wordmark, hall livery, and a lint that fails the build on drift |
| `bus/` | ACP-01/08/09 | The message bus with single-writer enforcement, the telemetry envelope and its quality guards, the append-only audit log, the parity/stop-condition/override safeguards, and the whole loop assembled over them |
| `console/` | — | **The Adaptive Console**: a single-file web app running the real protocol on the real pack, with the builder and its staleness guard |
| `i18n/` | — | **The locale catalogs**: the Academy's vocabulary in 8 languages with structural-parity and pack-agreement checks; hall names deliberately untranslated pending native review |
| `wiki/` | — | **The wiki**, generated from the registries: a page per map (campus, interiors, skill graph, languages) and a page per district, with Mermaid content graphs and a staleness guard |
| `stations/` | — | **The station registry**: the recovered pre-rebrand yard curriculum rebranded onto the live structure — 25 machine-gradable stations assigned to halls, skills and floor-plan rooms, verified against all three |
| `surfaces/` | §24 | **The surface registry**: 22 floor finishes with renderer-ready parameters and the reason each exists, resolved per room hazard-first with §24.1's discipline, plus per-room conditions (illuminance, air changes, design noise, temperature band, PPE) merged more-demanding-wins across every governing hazard — rendered as the 3D room floors and read out live in walk mode |
| `geo/` | — | **The geo registry**: real WGS84 coordinates per campus (Oakland's RECORDED from the Locator.X city table, cross-checked on build), recomputed great-circle distances and bearings, 19 RECORDED city/institution anchors and RECORDED city frames for all three campuses (the NOLA region record; the Bay Area map frame), copied from Locator.X's committed tables and sources (cross-checked on build), and Mapbox-ready GeoJSON — the 3D network view places its plates by these true bearings and marks each anchor on the campus rim, and every campus grows a walkable city layer — New Orleans at true linear offsets, Treasure Island as an island in the Bay with ferry lines and Bay Bridge spans at true bearings, Oakland on its waterfront (streets, bridges and water schematic, labelled so); plus the on-foot bands a distance only means something against — 800 m for ten minutes, 1.2 km for fifteen, and the six destination classes a walkable measure has to count — all RECORDED from Locator.X's walk module and cross-checked against it on build, carrying its caveats intact: not Walk Score®, straight-line rather than street-network, and honest that this bundle holds no shop records to count |
| `sims/` | — | **The simulator registry**: seven operable training seats (tower-crane lift, excavator trench cut, forklift yard run, the weld bead bench — arc gap, travel and burn-through discipline — the scaffold bay build — sills to rails in the legal order, refusals counted — the rigging signal call, where the learner is the signalperson and the crane follows only correct calls — and the load chart judgment, where the machine carries one honest chart and an overweight pick accepted is the failure that matters), each ringed by its five-point pre-shift walkaround — clipboards around the machine, a habit-builder the registry declares NOT a gate: nothing locks behind it and marking it changes no score with schematic physics in the 3D environment, deterministic rubrics, skill bindings proven against the roster and the graph, and a declared cockpit per machine — dash gauges with warn thresholds, synthesized audio (WebAudio, no recordings — the arc is filtered noise), haptic cues, an operator-seat view mode (cab, driver, welding visor, scaffold deck, the signalperson's pad or the chart board), and per-region training scenarios (the campus picks the yard; the rubric never varies) — not equipment certification, and the registry says so |
| `tools/` | — | **The toolroom registry**: one tool crib per district — twelve generic hand tools each with a schematic render shape, a hue and the one line of what it is for (no manufacturer or brand named or drawn) — hung on a pegboard in every hall's tools room in the 3D environment, plus the **crib drill**: a deterministic match-the-job-to-the-tool check derived from the crib itself (option order is index arithmetic, not chance), graded into the same device-local learner record as the simulators, with every hall bound through its district to a real `tools.applied` skill |
| `schools/` | — | **The schools pack**: the gamified flipped-classroom model (explore at home, build and practice in class, verify unaided — the teacher circulates), grade bands aligned with the Cognition.X vocabulary, proposed school-district records for all three regions (public-record names only; every record states that no district has reviewed or agreed), and one live flipped unit per simulator-bound hall — every reference proven against the packs that own it |
| `avatars/` | — | **The avatar pack**: a humanoid locker — 18 standard sections at 15–20 options each (build, skin, hair style + colour, eyes, facial hair, headwear from hard hats to ball caps, tops, vest, trousers, footwear, tool belts, outerwear, extras, costumes — 284 options) plus the **crew section seating all 111 halls**, each stamping its three-letter-code mark in the district hue on vest, shirt and headwear (the Academy's own insignia — no real union's logo is drawn), 17 one-tap **character** presets (each a full outfit with a line of story, validated against the locker), 19 themed **costumes** from the Mardi Gras krewe to the foundry heat suit — including five original animal mascots — plus **SmartCiti.X TradeApes**: an original collection of 111 apes, one per hall, generated deterministically from the roster (free, cosmetic only, NOT tokens — no NFT, no sale, no blockchain — and imitating no third-party ape artwork; anatomy holds to a measurements-only ape reference recorded in the registry — span, hunch and material roles measured from a user-supplied scan whose mesh is never shipped), and 8 emotes with emoji and procedural moves on a capsule-built humanoid with real facial features; **cosmetic only** — every option free and unlocked, none read by any grader, and the suite asserts it |
| `parcels/` | — | **The city-records registry**: the source contract for mimicking the three campus regions from their own records — the authority, dataset, licence, field schema and exact bounded query for each region's parcel and building-footprint GIS (New Orleans' `data.nola.gov`, the SF Assessor roll via DataSF, Alameda County's assessor FeatureServer; 254,122 records published upstream), all RECORDED from Locator.X's committed builders and cross-checked against that checkout — plus the public-domain USGS orthoimagery both maps draw. **No record is copied here**: the maps fetch from the authority in the learner's own browser and fall back to the SCHEMATIC layers, saying so on the page, when a source does not answer |
| `meta/` | — | **The metaverse-layer registry**: the interchange contract, built to the open baseline (no private standard is referenced or claimed) — glTF 2.0 export of the avatar (named rig) and any hall (named rooms) that Unity, Sketchfab, Blender, Godot and three.js open directly; learner-local .glb import onto the locker's guest stand (never uploaded, the asset's own licence stays the learner's to honour); WebXR and GeoJSON as the other two claimed standards; a recorded review of three MIT-licensed Unity avatar systems (UniVRM, Microsoft Rocketbox, Ready Player Me) read from their own checkouts, with VRM's humanoid bone vocabulary ADOPTED for the exported rig — which now carries **every bone VRM requires of a humanoid** (15 required plus chest and neck) as real nested transform nodes, so a Unity Humanoid or VRM import retargets it without a hand-built avatar definition, and the bones are driven rather than decorative: a distance-keyed walk cycle with knees that bend only one way, counter-swinging elbows, a breathing idle and a head that turns toward the viewer inside a human range — no animation clip is exported, only the rest-pose skeleton — while VRM, OMI extensions and USD stay honestly listed as NOT claimed; the org's [`ml-agents`](https://github.com/AGIFutureFoundation/ml-agents) fork (Unity ML-Agents Toolkit, Apache-2.0) RECORDED as the Unity-side training consumer — export-ready, with no trained agent claimed until one exists there; and a suite that holds every claim against the page source that implements it |
| `agents/` | — | **The advisor registry**: eight scripted guides — orientation guide at the door, safety steward, crib keeper, layout hand, inspector, foreman, records clerk, and the dispatcher on the campus green — standing in the rooms they speak for as the Academy's own rigged avatars, each answering a closed list of 28 questions between them. Fourteen of those topics carry no words at all: they are BINDINGS the page resolves against the record that already holds the fact, so the safety steward's answer is the hall's own condition record and changes when the hall does — one truth per fact survives the advisor being added. The other fourteen are written down and each names the file it was written in. An advisor is **not an instructor and not an AI**: no model runs behind one, nothing is generated at view time, no network is reached, it cannot be asked an open question, it represents no real worker or union officer, and talking to one changes no score — the suite asserts the last by reading the graders |
| `archive/` | — | Superseded working data kept for provenance, consumed by nothing and skipped by the figures lint |

Alongside the packs: [`ROADMAP.md`](ROADMAP.md) — the phased plan from v3.2
forward — and [`wiki/Home.md`](wiki/Home.md), the index of every map's page
(19 generated pages, staleness-guarded). `.github/workflows/pages.yml`
publishes the committed, verified pages — the landing page, every map and
environment under `web/`, and the wiki — to GitHub Pages on every push to
`main`; the workflow deploys, it does not build, so Pages can never show a
page the suite has not seen.

### Simulation harnesses

```bash
cd control
node simulate.mjs          # ACP-14: the dial vs fixed/random, six learner archetypes
node sweep.mjs             # dial parameter sweep (window x loopGain)
node sim_curriculum.mjs    # ACP-15: graph sequencing vs blocked/flat curricula
node sweep_workingset.mjs  # how many skills should be open at once
```

## Seventeen defects found by simulation

Every one of these was in the protocol, not merely in code written against it.
They are listed because the pattern matters: each was invisible to inspection
and obvious to a harness. Defects 8–9 needed thousands of attempts to appear;
10–11 needed hostile inputs rather than time; 12–13 only appeared when the
packs were assembled and run from somewhere other than where they were written;
14–15 needed two modules to be read against each other, since each half was
reasonable alone; 16 needed the thing to be rendered and measured, because it
was an assertion that agreed with itself and not with the browser.
All the harnesses ship alongside the unit suites, because each finds a class the
others structurally cannot.

| # | Defect | Found by |
|---|---|---|
| 1 | The session rail froze the dial — a never-re-anchored clamp pinned it ±10 from where a learner started | shadow-mode sim |
| 2 | Two clamp sites with different anchors let the setpoint escape the session cap | shadow-mode sim |
| 3 | Practice could never certify anyone: the dial serves the band centre, the gate accepts only the band top | curriculum sim |
| 4 | Improvement retroactively invalidated its own evidence — rising θ disqualified past demonstrations | curriculum sim |
| 5 | Asking whether a gate passed could silently revoke it | curriculum sim |
| 6 | Mastery belief outran evidence — 33/33 skills read as mastered after 201 attempts | curriculum sim |
| 7 | Unbounded interleaving is thrashing — a wide frontier learned 0.67 skills against 6+ | curriculum sim |
| 8 | The setpoint could escape the theta safety rail when a stale session anchor outlived a falling theta | soak |
| 9 | The verification budget deadlocked the sequencer — stalled at ~2,200 attempts with 25 of 33 skills uncertified | soak |
| 10 | One non-finite difficulty set theta to NaN and permanently destroyed a learner's profile | fuzz |
| 11 | The console staleness guard reported "current" while the page shipped a control plane two fixes behind | fuzz |
| 12 | The staleness guard's own source list was a second copy, and drifted the moment a new pack was added | integration |
| 13 | Suites passed only from the directory they were written in — the registry and console paths resolved against the working directory, so the packaged bundle's own verification could not run | packaging |
| 14 | Scaffold fading never fired anywhere: the ceiling was stamped only on verification picks and the mentor's fallback filled the gap with the *full* ladder, so every practice task ran unfaded | integration |
| 15 | The eval gate on mentor promotion stood in front of a mutable record — a caller could flip `evals.pass` on the object it had just been handed | adversarial |
| 16 | A layout assertion was built on a guessed px-per-character constant that was 43% low; it passed while four hall names overflowed their pads | rendering |
| 17 | Four published surfaces stated three different network sizes, and nothing compared them; the figures lint now reads the canonical counts from the verified pack | cross-surface |

## What has and has not been verified

**Verified here:** the ledger closes at exactly 11,000,000 with every ID proved unique;
the dial holds the ZPD ~6× better than fixed or random difficulty; the graph
sequencer is the only strategy that certifies anyone, and roughly doubles
durable ability against blocked practice; the eval harness fails each
adversarial mentor on exactly its own gate; the router's recursion guard
terminates handoff cycles.

**Not verified, and flagged in place:** `fabric/langgraph_reference.py` has
never been executed. Both simulations encode pedagogical assumptions
(prerequisite gating, forgetting curves, the cost of over-helping) and test
whether the system converts them into outcomes — they produce no evidence that
the assumptions are true. The affect signals in the dial simulation were
generated by the same model that consumed them, which is circular. The
working-set sweep result partly contradicts the interleaving rationale in
ACP-05, and the model is under-specified for that question — see ACP-15 §16.4.
Lesson titles and library labels in the registry are placeholder strings.

Shadow mode on real telemetry — logging intended actions and acting on none —
remains a required gate before activation.


## The console

`console/trade_craft_console.html` is the protocol wired to a screen — the tested
modules inlined verbatim, task content from the registry pack, every adaptation
showing its reason. Rebuild it with `python3 console/build_app.py` after changing
any protocol module. Its README lists the two integration bugs building it caught.

## v2.0 changes

Rebranded from the former working name to **SmartCiti.X : Trade Craft Academy
(powered by AGI Corp)** across every file, filename, identifier and generated
artifact — the registry and ledger were regenerated rather than patched, so no
stale brand survives in data.

Optimization pass in the same regeneration:

- **Registry payload roughly halved**, 12 MB to 6.6 MB. `union`, `level`, `slot`
  and `track` are derivable from a lesson id and its shard header, and the
  five-option check is identical on every row — writing them 1,221,000 times bought
  nothing. Flags now appear only when true. Key names stayed readable, because
  authors hand-edit these files and 2 MB is not worth a cryptic schema.
  `registry.js` hydrates the omitted fields on load, so consumers still receive
  complete lesson objects and no calling code changed.
- Dead imports and unreachable constants removed across all packs.
- Superseded bundle copies and scratch files dropped from the tree.

All checks pass against the regenerated data.

## v3.2 changes

- **Spec updated to v3.2** — §23 (what an adversarial review found: thirty-three
  defects, nine fail-open safeguards, the general finding that author-written
  tests agree with author-written code) and §24 (texture and environment
  packages) — and the version unified across the manifest, the registry and
  every generated surface.
- **Unions separated from modules.** The taxonomy now lives in `unions/` with
  its own registry, builder and source stamp; `pack/` consumes the built
  roster, and `unions/verify.mjs` proves the two packs agree instead of
  letting one directory imply it.
- **Eight languages.** `i18n/` carries the locale catalogs (English source +
  Spanish, French, German, Portuguese, Chinese, Hindi, Arabic), each held to
  structural parity and pack agreement by `i18n/test.mjs`, rendered
  direction-aware by `web/trade_craft_languages.html`. Hall names are
  deliberately untranslated pending native review, and every catalog says so.
- **A wiki and a roadmap.** `wiki/` is generated from the registries — a page
  per map with Mermaid content graphs, a page per district with every hall's
  figures — with a staleness guard in `verify_all.sh`. `ROADMAP.md` schedules
  v3.3 → v4.0 with harness-checkable exit criteria.
- **Packaged-layout path defects fixed.** `web/build_map.py`,
  `web/build_page.py` and the console slice builder resolved paths that only
  worked in the pre-packaging tree (defect 13's shape); all now walk up to
  the pack root. The duplicate `web/build_slice.py` was removed, and the
  orphaned 33-hall-era map data moved to `archive/` with its provenance
  recorded in `wiki/Provenance.md`.

## Running it as an app

The bundle is a static site: `index.html` at the root is the hub, and every
surface under `web/` and `console/` is a self-contained page. Deploy it on
any free static host, no build step required:

- **Vercel** — import the GitHub repository (framework preset: *Other*, no
  build command, output directory: repository root). `vercel.json` is
  already configured.
- **GitHub Pages** — Settings → Pages → deploy from branch, `main`, `/ (root)`.
- **Netlify** — drag the repository folder onto the drop zone, or connect
  the repo with no build command.
- **Locally** — `python3 -m http.server` from the repository root and open
  `http://localhost:8000/`. (The 3D environment needs an HTTP origin —
  browsers refuse ES-module imports from `file://` — so use the local
  server rather than double-clicking the file. Three.js 0.160.0 is
  vendored under `web/vendor/`, so every page works offline.)
