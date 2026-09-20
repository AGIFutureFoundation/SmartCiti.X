# Training data

Every interaction in this bundle already produces a structured fact: a
sim run ends in a measured rubric outcome, an advisor answer is a fixed
topic against a fixed record, a walkaround check is a point marked done.
This pack declares the shape those facts are recorded in when a learner
chooses to keep them — so the same sessions that teach a person can also
become example data for the robotics-training side of this project.

## The link this pack does not invent

`shaped to hand to the ml-agents fork RECORDED in meta/registry/metaverse.json as example JSON a conversion script could read`

That fork already exists in `meta/registry/metaverse.json`, RECORDED and
cross-checked on every build. This pack cites it; it does not claim it.
not a native Unity ML-Agents .demo (protobuf) file - this bundle has never produced or tested one, and does not claim to. exporting this file trains nothing by itself: no agent exists in this bundle and none is claimed to, until one is actually trained against this data outside it

## Three episode kinds

| Kind | What it is | Fields | Granularity |
|---|---|---|---|
| **sim** | one completed simulator run | t, kind, campus, hall, sim, scenario, controls, actor, operator, outcome | episode-level by default: the scenario and control scheme a run was attempted under, and how it ended. With TRACE on, also a coarse (~1 Hz) gauge trace across the run - still not a per-tick physics or joint trajectory; see TRACE below |
| **advisor** | one advisor question asked and answered | t, kind, campus, hall, advisor, topic, answer_kind | one exchange: which fixed topic was asked and whether the answer was read from a record or written in the advisor registry |
| **crew** | one crew role asked one question while its seat was running | t, kind, campus, hall, crew, role, topic, answer_kind | one exchange with one role of one crew: which crew was standing, which role was asked, which fixed topic, and whether the answer was read from a record or written in the crews registry |
| **walkaround** | one pre-shift walkaround point checked | t, kind, campus, hall, sim, point | one point marked - not a score, the same habit the sim registry already declares is not a gate |

## Who drove the seat: `actor`, and the SCRIPTED tier

A `sim` episode names its actor. `human` is a learner at the keys — every
episode this recorder ever kept, exactly as it was. `scripted-reference` is
the [scripted reference operator](Simulators.md) every seat carries: a
hand-written, deterministic control policy driven from the seat's own
gauges, no model, no network. A scripted episode also carries
`operator: {level, seed, scenario, steps, dt}`, the handle that replays it —
the levels are the closed set `sims/` owns, the seed drives a fixed-seed
generator, and under the records panel's headless fixed-step sweep the same
handle yields the same non-time axes every run.

| Actor | What it is |
|---|---|
| `human` | a learner at the keys - the episode carries nothing new; consumers that ignore `actor` read it exactly as before |
| `scripted-reference` | the scripted reference operator sims/ declares for every seat - a hand-written, deterministic control policy driven from the seat's own gauges, no model, no network; the episode also carries `operator: {level, seed, scenario}`, the handle that replays it |

- **SCRIPTED.** a SCRIPTED episode - actor scripted-reference - is a demonstration of a hand-written, deterministic control policy on a schematic single-machine simulator: driven from the seat's own gauges, no model behind it, no network reached, replayable from its own (level, seed, scenario) handle. Not a learned policy, not real equipment, and not a claim about any physical robot; not AI-SYNTHESIZED either, the word orbis/ keeps for generated video. It is kept through the same path, the same toggle and the same cap as a human episode, and it never credits the learner's own progress record.
- **Operator field.** {level, seed, scenario, steps, dt} - present ONLY when actor is scripted-reference: the closed level name, the integer seed of its fixed-seed generator, the scenario id, the number of control steps the run took, and the fixed step length when the run was headless (steps x dt is then its deterministic sim time - the `time` axis itself is wall-clock and informational) or null when a learner watched it at real time; absent on a human episode

## Storage

- **Key:** `tc-training` — never `tc-progress`, so the two records can never collide.
- **Cap:** 500 episodes, a rolling window: the oldest episode is dropped when the cap is reached, never the newest
- **Scope:** this browser only - localStorage, wrapped so a blocked store never breaks the page, exactly like tc-progress

## TRACE — the finer-grained recorder, built now

A separate, **off by default** add-on to the `sim` episode kind: while its
own toggle is on, a running sim's own `gauges()` readout — the exact
numbers the on-screen dashboard already shows — is sampled and folded
into that episode's `outcome.trace` when the run ends.

- **Toggle:** `tc-training-detail` — its own key, separate from `tc-training-on`; default off - heavier than an episode record, so it needs its own opt-in rather than riding the base recorder's
- **Rate / cap:** 1 Hz, capped at 90 samples per episode — a hard cap per episode, not a rolling window: sampling simply stops once a run passes max_samples seconds - the run's outcome is unaffected either way
- **Sampled from:** the running sim's own gauges() function - the exact numbers the on-screen dashboard already reads out every frame, sampled once a second rather than every frame, and computed nowhere new for this purpose
- **Scope:** attached to the sim episode it belongs to, inside the same tc-training record - no second storage key

## What this is not

- **Schematic.** every episode comes from SCHEMATIC physics and deterministic rubrics, not a real robot or a real machine: useful for exercising a training pipeline's plumbing and export format, not for training a controller that will run on real equipment.
- **Anonymous.** no name, no email, no biometric or device-identifying data is ever recorded - an episode carries only a scenario id, the control scheme the registry already declares, and the measured outcome.
- **Not a score.** recording an episode changes no score and is never read by a grader - the same guarantee this bundle keeps for advisors, and the suite proves it the same way, by reading the graders.
- **Consent.** the recorder ships on, with a visible toggle: turning it off stops new episodes without touching ones already kept, and clearing them is a separate, deliberate action.
- **Granularity.** episode-level by default. TRACE, its own off-by-default toggle, adds a coarse (~1 Hz) sample of a running sim's own gauges() readout - still not a per-tick physics or joint trajectory a real controller would train on: these are schematic single-machine simulators, not articulated robots, and gauges() returns display-shaped scalars and short labels, the same numbers the dashboard already reads out - sampled once a second instead of every frame, computed nowhere new for this purpose.

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
