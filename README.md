# SmartCiti.X : Trade Craft Academy — implementation bundle v2.9

*powered by AGI Corp*

The Adaptive Stack: eight packs implementing the ACP protocol suite.

**246 checks, all passing from inside this bundle**, with no model credentials
required.

```bash
./verify_all.sh                    # everything below, one exit code
```

Or individually — every path inside a pack resolves against its own module
location, so these run from any working directory (v2.6 defect 13):

```bash
node pack/verify.mjs              # 19 — the registry, and all 11,000,000 IDs
node control/test.mjs              # 12 — learner profile, ZPD dial, affect
node control/test_graph.mjs        # 20 — skill graph, sequencer, gates
node control/test_hints.mjs        # 21 — the hint ladder, fading, the ceiling contract
node fabric/test.mjs               # 16 — mentor guards, eval harness, router
node bus/test.mjs                  # 12 — bus contracts, telemetry guards, audit
node bus/test_safeguards.mjs       # 15 — parity, stop conditions, overrides
node security/test.mjs             # 16 — authz, tenancy, rate limits, privacy
node ops/test.mjs                  # 41 — registries, rollout lanes, jobs, cost governor
node ops/fuzz.mjs                  #  9 — side doors around the promotion gates
node brand/test.mjs                # 30 — naming, tokens, contrast, livery, the lint itself
node brand/lint.mjs .              # fails on any forbidden spelling anywhere in the tree
node control/fuzz.mjs              # 21 — hostile inputs and adversarial learners
node control/soak.mjs              # long-run invariants, 4,000 attempts x 3 seeds
python3 console/check_console.py   # fails if the console is behind its sources
```

| Pack | Spec | What it is |
|---|---|---|
| `pack/` | ACP-10 | Module registry at 111-hall scale: 25,875 authored skeleton objects, a consumer library that generates all 11,000,000 module IDs from them, and a verifier that proves uniqueness over the whole population rather than a sample |
| `control/` | ACP-02/03/04/05/06/07/15 | The deterministic control plane — profile, dial, affect, hint ladder, skill graph, sequencer, assessment gates — with two simulation harnesses |
| `fabric/` | ACP-11/12 | Mentor contract and middleware, the five-gate eval harness with adversarial stubs, supervisor/swarm router |
| `security/` | — | Deny-by-default authorization with tenant isolation, rate limiting, data classification, retention and erasure; plus `SECURITY.md` with the threat model and an honest launch checklist |
| `ops/` | ACP-13 | The three registries with a pipeline transition table, hall-by-hall rollout lanes that ask ACP-08 rather than re-deciding, the seven-job automation loop, and the cost governor that cannot throttle the control plane |
| `web/` | — | The published pages and their builders: landing page, protocol spec, and the campus plan with a generated floor plan for every hall |
| `brand/` | — | The canonical identity: names and forbidden spellings with reasons, the two-theme token set, the wordmark, hall livery, and a lint that fails the build on drift |
| `bus/` | ACP-01/08/09 | The message bus with single-writer enforcement, the telemetry envelope and its quality guards, the append-only audit log, the parity/stop-condition/override safeguards, and the whole loop assembled over them |
| `console/` | — | **The Adaptive Console**: a single-file web app running the real protocol on the real pack, with the builder and its staleness guard |
| `web/` | — | The published pages and their builders: the landing page and the rendered protocol spec |

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
