# SmartCiti.X : Trade Craft Academy — Adaptive Stack Protocol Specification

*powered by AGI Corp*

**Suite name:** Adaptive Challenge Protocols (ACP) · **Version:** 3.2 · **Date:** 2026-09-04
**Scope:** The full adaptive loop of the SmartCiti.X : Trade Craft Academy training space — telemetry capture, learner profiling, difficulty throttling (the AI–ZPD dial), scaffolding, knowledge-graph sequencing, assessment, flow regulation, safeguards, the module ledger, and the agent fabric. Written to be buildable: schemas, update rules, thresholds, and message contracts are normative unless marked *tunable*.

---

## 0. Design principles

**P1 — The ZPD invariant.** Every task served must sit inside the learner's Zone of Proximal Development: hard enough that unaided success is not guaranteed, easy enough that success with available scaffolding is probable. Operationally: predicted unaided success probability in the **target band [0.70, 0.85]** (*tunable per skill family*).

**P2 — Never boredom, never anxiety.** The dial has two failure modes, not one. Sustained success above the band with low effort signals is boredom (step difficulty up); sustained failure below the band with stress signals is anxiety (step down *and* scaffold). Both are detected, both trigger action within bounded time.

**P3 — Profile is inferred, never asked.** The Learner Profile agent (LPA) builds its proficiency vector from behavioral telemetry — accuracy, latency, hint requests, coding cadence, sim-control traces — not from self-report quizzes. Self-report may seed cold start only.

**P4 — Every adaptation is explainable.** Any change the dial makes (harder task, easier task, injected scaffold, forced review) must emit a human-readable `why` string surfaced to the learner ("Why this?"), the mentor agent, and the audit log.

**P5 — Scaffolding fades.** Help is a loan against mastery credit, not a free good. Hints reduce the mastery evidence of a success and the hint ladder retracts as proficiency grows.

**P6 — Humans can always override.** Instructors, union training agents, and the learner (within floors/ceilings) can pin difficulty; overrides are logged and the model treats overridden episodes as biased evidence.

**P7 — Minimum data, maximum signal.** Raw high-frequency streams (keystrokes, controller poses) are reduced to features at the edge; only features and events leave the client. No raw keystroke logs are stored server-side.

### 0.1 The module map

| ID | Module | Role in the loop |
|----|--------|------------------|
| ACP-01 | Telemetry & Signal Protocol | Capture events, extract normalized signals |
| ACP-02 | Learner Profile Agent (LPA) | Fuse signals into the proficiency vector |
| ACP-03 | ZPD Dial (Challenge Controller) | Throttle difficulty to the edge of capability |
| ACP-04 | Scaffolding & Hint Engine | Graduated help, fading, Socratic handoff |
| ACP-05 | Sequencing & Quest Generation | What comes next: skill graph, spacing, interleaving |
| ACP-06 | Assessment & Mastery Verification | Gates, level tests, jobsite finals, anti-gaming |
| ACP-07 | Flow & Affect Protocol | Classify flow/boredom/anxiety/disengagement |
| ACP-08 | Safeguards & Governance | Floors, parity, overrides, privacy, stop conditions |
| ACP-09 | Inter-Agent Message Contracts | Bus topics and schemas binding the agents |
| ACP-10 | Module Ledger & Content Pipeline | The 11,000,000-module catalog, generated and verified |
| ACP-11 | Agent Fabric | Framework choices and the three-plane agent architecture |
| ACP-12 | Agent Training & Evaluation | How mentor agents are trained, evaluated, promoted |
| ACP-13 | Network Management & Automation | Registry, rollout, budgets, jobs — running it at scale |
| ACP-14 | Shadow-Mode Calibration | The dial's simulated gate, and what it changed |
| ACP-15 | Knowledge-Graph Tracing & Sequencing | Which skill, and why now: transfer, review, verification |

**The loop, end to end:** client emits events (ACP-01) → LPA updates the profile (ACP-02) → the ZPD Dial computes the current challenge setpoint (ACP-03) → the sequencer picks candidate tasks and the quest designer assembles them (ACP-05) → during the attempt the hint engine manages scaffolds (ACP-04) and the flow classifier watches affect (ACP-07) → outcomes feed assessment gates (ACP-06) → everything is bounded by safeguards (ACP-08) and carried on the message bus (ACP-09).

Agent naming: the LPA corresponds to the Academy's learner-profile/analytics agent; quest assembly is the quest-designer agent's job; Socratic remediation is the dialectical tutor's; mentor/union agents (e.g., the trade coaches) consume dial state to speak to the learner in character. Agents register on the swarm registry and communicate over the bus in §9.

---

## 1. ACP-01 — Telemetry & Signal Protocol

### 1.1 Event envelope

Every observation is an event with a common envelope. Transport is at-least-once; consumers dedupe on `event_id`.

```json
{
  "event_id": "uuid-v7",
  "ts": "2026-09-02T17:04:11.302Z",
  "learner_id": "pseudonymous-stable-id",
  "session_id": "uuid",
  "context": {
    "module_id": "ironworkers.L12.lesson04",
    "task_id": "task-8841",
    "skill_ids": ["rigging.load-calc", "rigging.sling-angle"],
    "difficulty": 62,
    "modality": "vr_sim | quiz | code | drill | video | reading",
    "device_tier": "hd | standard | mobile",
    "scaffold_level": 0
  },
  "verb": "attempted | completed | failed | hint_requested | paused |
           resumed | abandoned | edited | control_input | answered",
  "payload": { }
}
```

Events map 1:1 onto xAPI statements for LRS export (`verb` → xAPI verb IRI, `context.module_id` → activity, `payload.score` → result), so the existing xAPI 1.0.3 emitter is the egress adapter, not a second pipeline.

### 1.2 Signal taxonomy

Signals are features derived from events. Each is computed per attempt and aggregated over rolling windows (defaults: last 10 attempts per skill, last 30 min of session). All continuous signals are double-normalized: z-score against the **cohort** at the same difficulty, then against the learner's **own trailing baseline** — so "slow" means slow *for this task* and *for this learner*.

| Signal | Source | Definition | Reads as |
|--------|--------|------------|----------|
| `acc` | answers/task outcomes | correct ÷ attempts, per skill | raw capability |
| `lat` | response timing | time-to-first-action and time-to-completion, z-normalized | fluency vs. floundering |
| `lat_var` | response timing | variance of `lat` within window | stability; rising variance precedes anxiety |
| `hint_rate` | hint engine | hints requested ÷ attempts, weighted by rung depth | independence |
| `cadence` | code/build editors | edit-burst rhythm: bursts/min, burst length, pause distribution, delete-to-insert ratio | planning vs. thrash (high delete ratio + short bursts = thrash) |
| `path_smooth` | VR sim controls | control-input smoothness (jerk integral) and step-order edit distance vs. reference procedure | motor + procedural fluency |
| `retry_gap` | attempts | time between a failure and the retry | resilience; very short = guess-spam, very long = avoidance |
| `idle` | focus/pause events | idle gaps > 30 s during an active task | disengagement |
| `abandon` | session | task abandoned before completion | strong anxiety/disengagement marker |
| `selfcorr` | answers/edits | corrections made without prompt | metacognition; boosts mastery evidence |

### 1.3 Edge reduction & retention

Keystroke and controller streams are reduced to `cadence` / `path_smooth` features **on the client**; raw streams are discarded after feature extraction (≤ 5 s buffer). Feature events are retained 24 months; aggregates indefinitely. `learner_id` is pseudonymous; the mapping table lives outside the analytics store (see ACP-08).

### 1.4 Quality guards

Consumers must tolerate: clock skew (trust server receipt time when |skew| > 2 min), missing modality fields (treat as `quiz`), and burst duplication. A session with < 3 usable events produces **no** profile update — silence is not evidence.

---

## 2. ACP-02 — Learner Profile Agent (LPA)

The LPA is the single writer of the **proficiency vector**. Everything downstream (dial, sequencer, mentor agents) reads it; nothing else writes it.

### 2.1 The proficiency vector

Per learner, per skill node `s` in the skill graph:

```json
{
  "skill_id": "rigging.sling-angle",
  "theta": 61.4,          // proficiency rating, 0–100 scale (Elo-family)
  "sigma": 7.2,           // uncertainty (rating deviation)
  "p_mastery": 0.83,      // BKT posterior P(skill is mastered)
  "velocity": +1.9,       // Δtheta per 10 attempts, EWMA
  "half_life_days": 21.5, // retention half-life estimate
  "last_evidence": "2026-09-01T20:12:00Z",
  "hint_dependence": 0.18,  // EWMA of rung-weighted hint_rate
  "evidence_n": 34
}
```

Plus per-learner globals: modality weights (evidence-weighted preference across the modality set, floor 15% so no modality starves), affect baseline (personal `lat`/`cadence` baselines), and a `pace_profile` (session length and time-of-day patterns).

### 2.2 Update rules

**Rating update (per attempt).** Elo-family co-update of learner θ and item difficulty `d` (both on the 0–100 scale, K scaled by uncertainty):

```
E = 1 / (1 + 10^((d − θ) / 12))          // expected success; 12 ≈ band width
θ ← θ + K_l · w · (outcome − E)
d ← d + K_i · (E − outcome)               // item calibration, K_i ≪ K_l
K_l = K_max · (σ / σ_max), clamped to [2, 12]
```

`outcome ∈ [0,1]` is graded, not binary: full unaided success = 1.0; success at hint rung r = `1 − 0.15·r` (floor 0.25); partial-credit sims score by rubric. `w` down-weights suspect evidence: 0.5 if guess-spam detected, 0.3 if the episode ran under an instructor override.

**Mastery update (per attempt).** Standard BKT per skill with parameters fit per skill family: P(L₀)=0.15, P(T)=0.20, P(G)=0.20, P(S)=0.10 (*tunable; fit from cohort data quarterly*). `p_mastery` is the posterior after each observation; hint-assisted successes update with P(G) inflated by rung (a rung-3 success is weak evidence).

**Uncertainty.** σ shrinks with evidence (`σ ← σ·0.97` per informative attempt, floor 3) and grows with silence (`σ ← min(σ_max, σ + 0.15·days_idle)`), which naturally widens the dial's exploration after absence.

**Decay.** Half-life regression: `p_recall(t) = 2^(−t / half_life)`. Each successful spaced retrieval multiplies `half_life` by 1.8; each failed one multiplies by 0.6 (floor 2 days). When `p_recall < 0.7`, the skill enters the review queue (ACP-05).

**Velocity.** EWMA (α=0.3) of θ deltas — the dial uses velocity, not just level, to size steps: fast climbers get larger difficulty increments.

### 2.3 Cold start

New learner: θ = 35, σ = σ_max = 15, `p_mastery` = P(L₀). First 5 attempts per skill family run a **calibration ladder**: items at d = 25, 40, 55, 70, 85 served in adaptive binary-search order; θ initialized to the last difficulty with success ≥ 0.5. Placement claims from a prior credential (e.g., a completed union level) seed θ per its mapped skill list at `mapped_level − 10` with σ = 12 — trusted, but verified fast by the ladder.

### 2.4 Profile read API

`GET /profile/{learner_id}` returns the vector plus derived summaries: `frontier` (skills with 0.4 ≤ p_mastery < 0.95, ordered by graph readiness) and `review_due` (skills with p_recall < 0.7). Reads are cheap; the dial polls per task selection, mentors per dialogue turn.

---

## 3. ACP-03 — The ZPD Dial (Challenge Controller)

The dial answers one question continuously: **what difficulty should the next unit of work be, for this learner, on this skill, right now?**

### 3.1 Setpoint and band

For skill `s`, the dial holds a challenge setpoint `c_s` (same 0–100 scale as θ and d). The invariant: the predicted unaided success of a task at `c_s` stays in the target band.

```
P(success | θ, d) = 1 / (1 + 10^((d − θ)/12))
band = [0.70, 0.85]  →  c_s ∈ [θ − 9.0, θ − 4.4]   // implied by the logistic
default setpoint: c_s = θ − 6.5   (≈ 0.78 predicted success)
```

Read θ as the learner's **50% frontier** — the difficulty they would solve unaided half the time. The dial works 4–9 points *inside* that frontier: success stays probable, but never free. "The edge of current capability" is the strip just inside the frontier, not beyond it.

### 3.2 The controller

A bounded step controller with hysteresis (a full PID adds nothing at this sample rate):

```
every attempt window W (default 5 attempts on skill s):
  p̂ = hint-discounted success rate over W
  if p̂ > 0.85 and boredom_score > B_hi:     c_s += step_up
  elif p̂ < 0.70 and anxiety_score > A_hi:   c_s −= step_down; scaffold_level += 1
  elif p̂ < 0.55:                            c_s −= step_down            // regardless of affect
  else: hold
  step_up   = clamp(2 + velocity, 2, 6)
  step_down = 4                              // down faster than up
  clamp c_s to [θ − 12, θ − 2] and to session Δ ≤ 10                    // hysteresis rails
```

**Boredom score** (0–1): high p̂ + `lat` well below baseline + `hint_rate` = 0 + `idle` rising. Fires `step_up`, and above 0.8 also triggers a *stretch quest* offer (one-off task at c_s + 5 ≈ the frontier, opt-in, no mastery penalty on failure).

**Anxiety score** (0–1): p̂ low + `lat_var` rising + `retry_gap` shrinking toward guess-spam or stretching toward avoidance + `abandon` events. Above A_hi the dial steps down **and** opens the hint ladder one rung *before* the learner asks (pre-emptive scaffold); above 0.9 it swaps the task modality (e.g., VR sim → guided drill) and notifies the mentor agent to check in, in character.

Thresholds B_hi = 0.6, A_hi = 0.6 (*tunable*). The two scores come from ACP-07's classifier; the dial never computes affect itself.

### 3.3 Dial states

| State | Entry condition | Dial behavior |
|-------|----------------|---------------|
| `CALIBRATING` | σ > 10 | binary-search item choice, wide steps |
| `FLOW` | in band, low affect scores | hold; micro-adjust ±1 |
| `STRETCH` | boredom fired | +step; offer stretch quest |
| `SUPPORT` | anxiety fired | −step; pre-emptive scaffold; modality swap at 0.9 |
| `RECOVERY` | 2 consecutive failed windows | drop to θ − 12, worked example first, rebuild |
| `PINNED` | human override | serve pinned difficulty; evidence weight w = 0.3 |

State transitions are events on the bus (`dial.state_changed`) with the `why` string (P4): e.g., *"Raised challenge to 64: you solved the last 5 rigging tasks 40% faster than your usual pace without hints."*

### 3.4 What the dial controls beyond item difficulty

Difficulty is a vector in practice; the dial may spend a step on any one axis per window (never several at once, so effects stay attributable): task complexity (steps in the procedure), time pressure (sim timer on/off/duration), scaffold ceiling (which hint rungs exist), fault density (how many planted faults in an inspection scene), and stakes (practice vs. graded). Axis choice: whichever axis the learner's weakest signal implicates (slow but accurate → time pressure stays off, complexity rises; fast but sloppy → complexity holds, fault density rises).

---

## 4. ACP-04 — Scaffolding & Hint Engine

### 4.1 The five-rung ladder

Every task type publishes a hint ladder. Rungs are ordered by how much thinking they do for the learner:

| Rung | Name | Example (sling-angle task) | Mastery credit on success |
|------|------|---------------------------|---------------------------|
| 1 | Orient | "Look again at the angle between the sling legs." | 0.85 |
| 2 | Prompt | "What happens to leg tension as the angle drops below 60°?" | 0.70 |
| 3 | Worked step | Shows the first step of the load calculation, learner finishes | 0.55 |
| 4 | Demonstrate | Full worked example on a *parallel* problem | 0.40 |
| 5 | Co-complete | Mentor agent completes it with the learner, narrating | 0.25 |

Requesting a rung requires 20 s minimum dwell since the last action (anti-lever-mashing). The engine offers, never forces, except pre-emptive rung-1 offers in `SUPPORT` state.

### 4.2 Fading

The scaffold ceiling (highest available rung) shrinks with mastery: p_mastery < 0.5 → all 5 rungs; 0.5–0.8 → rungs 1–3; 0.8–0.95 → rung 1 only; ≥ 0.95 (verification attempts) → no hints. `hint_dependence` > 0.35 sustained over 20 attempts triggers a *fading contract*: the mentor agent names the pattern and the next 3 tasks run one rung lower than requested, with encouragement.

### 4.3 Socratic handoff

Rung 2 escalations on **conceptual** skills (not motor/procedural) route to the dialectical tutor agent for a bounded dialogue (≤ 6 turns): the tutor asks, never tells, and returns a `concept_gap` annotation to the LPA (which skill prerequisite actually failed). Motor/procedural skills skip dialogue — they get demonstration replays with the in-cab/first-person view instead.

---

## 5. ACP-05 — Sequencing & Quest Generation

### 5.1 Skill graph

Skills are nodes with typed edges: `requires` (hard prerequisite), `supports` (soft transfer), `interferes` (confusable pair — e.g., two knots learners swap). A skill is **ready** when all `requires` parents have p_mastery ≥ 0.8.

### 5.2 The next-task policy

Each selection cycle builds a candidate pool and scores it:

```
pool = frontier tasks at |d − c_s| ≤ 3        // dial compliance is a hard filter
     ∪ review_due tasks (p_recall < 0.7)
     ∪ 1 interleaved task from a `interferes` pair when both > 0.6 mastery

score(task) = 0.45·zpd_fit + 0.25·review_urgency + 0.15·graph_leverage
            + 0.10·modality_fit + 0.05·novelty
```

`graph_leverage` = number of locked skills this one unblocks. Ordering constraint: no more than 3 consecutive tasks on one skill; review items are woven in at a 1-in-4 cadence when the review queue is non-empty. ACP-15 adds the constraint this rule was missing — a **working set** bounding how many skills are open at once, since unbounded interleaving dilutes practice until nothing masters — and reports a sweep that puts the interleaving rationale itself in question.

### 5.3 Quest assembly

The quest-designer agent wraps the top-scored tasks into narrative quests sized to the learner's `pace_profile` (default 20–25 min arc): briefing → 3–5 tasks rising ≤ 4 difficulty points across the arc → debrief with the mentor agent. Quests declare their skill payload so the LPA can attribute outcomes. Jobsite quests (the 33-level union ladders) must draw ≥ 80% of their tasks from `ready` skills — story never outruns the graph.

---

## 6. ACP-06 — Assessment & Mastery Verification

### 6.1 Gates

Three gate tiers, increasingly adversarial to help:

**Skill gate** — p_mastery ≥ 0.95 **and** 3 consecutive unaided successes (scaffold ceiling 0) at d ≥ θ − 5, the top of the band and harder. BKT alone never certifies; performance must confirm. Three refinements come from ACP-15, each forced by a defect: those demonstrations must be *deliberately served* (practice at the band centre can never qualify), qualification is stamped at serve time (a rising θ must not retroactively invalidate past proof), and the gate is an **awarded event** — a later re-test cannot silently revoke it.
**Level test** — the existing 33-question level test, served at fixed difficulty (not dialed), no hints, pass ≥ 80%. Item order shuffled per sitting; failed sittings lock retake for 12 h with targeted review auto-queued.
**Jobsite final** — the union training agent's exam on an active virtual job site: procedure executed end-to-end in sim, scored by rubric (step order, safety violations, time within tolerance), with the agent's oral check (3 Socratic questions on the *why*). Certification requires all three tiers.

### 6.2 Anti-gaming

| Pattern | Detector | Response |
|---------|----------|----------|
| Guess-spam | retry_gap < 3 s on ≥ 3 consecutive fails | outcome weight w = 0.5; task locks 60 s; mentor nudge |
| Hint farming | rung 4–5 requests > 50% of attempts | fading contract (§4.2); credit floor applies |
| Wheel-spinning | 10+ attempts on one skill, p̂ flat, no gate progress | stop serving the skill; route to prerequisite review + tutor dialogue (the humane response to stuck is *not more of the same*) |
| Answer sharing (level tests) | z-score of (speed × accuracy) vs cohort > 3 | flag to instructor; no automated penalty (ACP-08: humans judge integrity) |

---

## 7. ACP-07 — Flow & Affect Protocol

A 4-state classifier over the signal window, evaluated per attempt window:

| State | Signature (all vs. personal baseline) | Consumer response |
|-------|----------------------------------------|-------------------|
| `FLOW` | in-band success, stable lat, low hint_rate, no idle | dial holds; **do not interrupt** — no popups, no mentor small-talk |
| `BOREDOM` | high success, fast lat, rising idle/task-switching | dial steps up; stretch quest offer |
| `ANXIETY` | low success, rising lat_var, hint bursts or avoidance retry_gaps | dial steps down + scaffold; mentor check-in above 0.9 |
| `DISENGAGED` | idle > 3 min, abandon, session truncation trend | session-level: shorter quest arcs, modality rotation, re-entry ramp next session (first task at c_s − 5 for a guaranteed early win) |

Scores are logistic blends of the named signals (weights fit per cohort, refreshed quarterly). The classifier emits `affect.scored` events consumed by the dial and mentors; it stores **only** state labels and scores, never a raised inference about the person (no "learning disability" style conclusions — ACP-08 forbids diagnostic inference).

**Re-entry ramp:** after ≥ 7 days away, the first quest runs at c_s − 5 with review items only — protecting the return experience is a retention feature, not a difficulty bug.

---

## 8. ACP-08 — Safeguards & Governance

**Floors & ceilings.** Difficulty never rises past θ − 2 (opt-in stretch quests may reach θ + 2) or drops below θ − 12, except in `RECOVERY`/`CALIBRATING`. Learners may self-select "easier today" (−3, logged, no questions asked) up to twice a week; instructors may pin anything.

**Override log.** Every human override, dial state change, and gate decision is appended to an immutable log: `{ts, actor, action, before, after, why}`. The "Why this?" surface reads from the same log — one source of truth for explanation and audit.

**Parity checks.** Monthly job: gate pass rates, average time-in-`SUPPORT`, and stretch-quest offer rates compared across cohorts (site, language, device tier, age band). Any metric with disparity > 10% relative opens a review ticket; the dial's parameters may not be tuned per-cohort to *mask* a disparity — root cause goes to content or calibration.

**Privacy.** Raw input streams die at the edge (§1.3). Profiles are pseudonymous; re-identification requires the enrollment service. Affect labels are visible to the learner and their instructor, never to employers/sponsors. No diagnostic inference from telemetry, ever. Exports (xAPI/LRS) carry features and outcomes, not affect scores, unless the receiving org signs the data rider.

**Stop conditions.** The adaptive loop halts (fixed-difficulty fallback + human alert) if: item calibration drift > 8 points/week on > 20% of items; cohort-level anxiety time > 25% for a week; or the parity job cannot run. A degraded dial is worse than no dial.

---

## 9. ACP-09 — Inter-Agent Message Contracts

Bus topics (at-least-once, schema-versioned; agents register capabilities on the swarm registry):

| Topic | Producer → Consumer | Payload core |
|-------|--------------------|--------------|
| `telemetry.event` | client → LPA, affect | §1.1 envelope |
| `profile.updated` | LPA → dial, sequencer, mentors | learner_id, changed skill vectors, frontier delta |
| `affect.scored` | affect → dial, mentors | state, boredom/anxiety scores, window ref |
| `dial.setpoint` | dial → sequencer | skill_id, c_s, band, axis, state |
| `dial.state_changed` | dial → mentors, log | before/after state, why |
| `quest.assembled` | quest designer → client | quest manifest, skill payload, declared difficulties |
| `hint.served` | hint engine → LPA | rung, dwell, task ref |
| `gate.decision` | assessment → LPA, credentials | tier, pass/fail, evidence bundle |
| `override.applied` | instructor UI → dial, log | pin values, actor, reason |

Contract rules: every message carries `schema_version`; consumers must ignore unknown fields; the LPA is the only writer of profiles and the dial the only writer of setpoints (single-writer per aggregate). Mentor agents are read-only consumers — they *voice* the system, they don't steer it.

---

## 10. Defaults & tuning sheet

| Parameter | Default | Range | Owner |
|-----------|---------|-------|-------|
| Target band | [0.70, 0.85] | ±0.05 | pedagogy |
| Setpoint offset | θ − 6.5 | −9…−4.4 | dial |
| Logistic width | 12 | 8–16 | calibration |
| Window W | 5 attempts | 3–10 | dial |
| Control mode | closed loop + affect steps | — | dial |
| loopGain (v1.2) | 0.3 | 0.3–0.8 | calibration |
| Rails (railLo/railHi) | θ−14 / θ+0 | — | dial |
| step_up / step_down | 2+velocity / 4 | — | dial |
| Session Δ cap | 10 | 6–14 | safeguards |
| K_l max / K_i | 12 / 2 | — | calibration |
| BKT (L₀,T,G,S) | .15/.20/.20/.10 | fit quarterly | calibration |
| Hint rung credits | .85/.70/.55/.40/.25 | — | pedagogy |
| Review threshold p_recall | 0.7 | 0.6–0.8 | pedagogy |
| Skill gate | p_m ≥.95 + 3 unaided | — | assessment |
| B_hi / A_hi | 0.6 / 0.6 | 0.5–0.8 | affect |
| Re-entry ramp | c_s − 5 after 7 d | — | flow |
| Parity alarm | >10% relative | — | governance |
| Mastery evidence shrink k (v1.4) | 4 | 3–8 | ACP-15 |
| BKT P(T) (v1.4) | 0.10 | 0.05–0.15 | calibration |
| Working set (v1.4) | 3 skills | 1–4 | ACP-15 sweep |
| Verification budget (v1.4) | 1 in 8, runs of 3 | — | ACP-15 |
| Transfer damping (v1.4) | .20 prereq / .10 child / .10 supports | — | ACP-15 |

**Build order recommendation:** ACP-01 → ACP-02 (rating layer only) → ACP-03 in shadow mode (log, don't act) for 2 weeks of calibration → activate dial → ACP-04/05 → ACP-07 → ACP-06 gates last (gates on an uncalibrated dial certify noise). ACP-08 logging ships with the first line of code, not last.

*The simulated half of that shadow-mode gate has been run — see ACP-14 for the results, the two controller defects it found, and the re-derived defaults above.*

---

## 11. ACP-10 — Module Ledger & Content Pipeline

### 11.1 The ledger at 111 halls

The network is **111 union halls and 11,000,000 modules**. The number has to decompose from the spine or it is marketing, so here is the decomposition, and one constraint it forced.

| Ledger line | Computation | Modules |
|-------------|-------------|---------|
| Core lessons | 111 halls × 100 levels × 110 slots | 1,221,000 |
| Dial variants per lesson | 3 modalities (`vr_sim`, `guided_drill`, `quiz_reading`) × 3 ZPD bands (`support`, `core`, `stretch`) | × 9 |
| **Core modules** | 1,221,000 × 9 | **10,989,000** |
| Shared cross-trade library | 4,400 machines + 4,400 tools + 1,100 interfaces + 1,100 protective | |
| **Library modules** | one shared catalogue, not per-hall | **11,000** |
| **Total** | 10,989,000 + 11,000 | **11,000,000** |

**Why the library is shared, and no longer held per hall.** At the 33-hall scale the library was 300 items in one edition per hall. That structure cannot close on this number: 11,000,000 is not divisible by 111 — it leaves a remainder of 11 — so *any* design where every hall holds an identical per-hall library is arithmetically incapable of reaching it. The arithmetic ruled before taste did. Sharing the catalogue is also the better design at this scale: a machine library duplicated 111 times is 111 copies of the same forklift.

### 11.2 Module ID grammar

```
core:    u{000–110}.l{000–099}.s{000–109}.{modality}.{band}   e.g. u007.l011.s002.vr_sim.core
library: {mach|tool|ifc|ppe}{0000–4399}                       e.g. mach0042
```

The union index is three digits and the first `33 halls` keep the indices they had, so every module ID minted under the 33-hall pack still points at the same hall. IDs are stable forever; content revisions version *inside* an ID, so learner history never dangles.

### 11.3 Generated, not stored — now one level deeper

At the `33 halls` scale the pack stored every lesson row and generated only the 9 variants. At 111 halls that stops working: 1,221,000 lesson rows is roughly 235MB of JSON and a ~90MB ledger, which no browser will load and no bundle should carry.

So the generate-don't-store rule moves up a level. What is **authored** is the skeleton — 111 halls, their 100-level ladders, the 3,663-node skill graph, the 11,000 library items: **25,875 objects**. Lesson rows are generated from the ladder by the same deterministic rule in the builder, the consumer library and the map, and variants are generated from lessons as before.

This makes the headline a count of **addressable module IDs, not hand-written lessons**, at a ratio of 425 generated to 1 authored. Every surface that prints the number must say so — the manifest carries `authored_objects` next to `total_modules` precisely so the two travel together, and the public status table names the content as placeholder pending authoring.

### 11.3.1 Proving 11,000,000 rather than sampling it

The 33-hall pack proved uniqueness by loading every enumerated row into a `Set`. At 11 million that would be gigabytes, and the tempting move is to fall back to spot checks — which can only ever *fail to find* a collision.

Instead the proof changes shape. `index()` and `fromIndex()` are declared inverses over `[0, 11,000,000)`, so the verifier walks every index once, marks a bit in a 1.375MB bitmap, and round-trips it. **Every module is checked, in about a second** — a full-population proof that is both cheaper and stronger than the sampled check it replaces. When a data structure grows past the obvious verification, the answer is usually a better proof, not a weaker one.

### 11.4 Content pipeline (CI for curriculum)

Modules move through four states: `draft → schema_ok → calibrating → live`.

**`schema_ok`** — automated lint: ID grammar, declared `skill_ids` exist in the graph, every lesson declares its 5-option check, rubric present for sim tasks, both language fields non-empty where required.
**`calibrating`** — served only inside the dial's `CALIBRATING` allowance (≤ 5% of any learner's stream); item difficulty `d` must converge (σ_d < 4 over ≥ 200 attempts) before promotion.
**`live`** — eligible for normal selection. Demotion is automatic when calibration drift exceeds the ACP-08 stop-condition threshold.

Coverage bots run nightly: every skill node must be reachable by ≥ 3 live modules per band (else a `coverage.gap` ticket opens), and no union may fall below 95% live coverage of its spine.

---

## 12. ACP-11 — Agent Fabric

### 12.1 Framework review (September 2026)

| Framework | What it is | Status | Fit for SmartCiti.X |
|-----------|-----------|--------|-------------------|
| **LangChain 1.0** | Agent construction layer: `create_agent`, provider-agnostic tool calling, middleware hooks (human-in-the-loop approval, message summarization, PII redaction) | Stable — 1.0 Oct 2025, no breaking changes until 2.0 | **Adopt** for building mentor agents: middleware gives HITL and PII redaction nearly free, both ACP-08 requirements |
| **LangGraph 1.0** | Low-level orchestration runtime: graph-of-agents, durable execution (state persists across interruption), checkpointing, long-running/multi-day workflows | Stable — 1.0 Oct 2025 | **Adopt** as the orchestration runtime: durable execution matches multi-session training arcs; supervisor and swarm patterns both supported |
| **Sentient ROMA** | Recursive meta-agent: Atomizer → Planner → Executor → Aggregator → Verifier loop that decomposes long-horizon tasks into dependency-aware subtask trees, modules swappable per level | v0.1 **beta**, Apache 2.0, ~5.2k stars | **Adopt the pattern, sandbox the code**: ideal shape for the content factory (§12.3); beta maturity keeps it out of the learner-facing path |
| **SingularityNET / ASI Alliance** | Decentralized agent rails: Hyperon AGI framework (Alpha 1) + MeTTa language + ASI:Chain blockDAG (DevNet, Nov 2025) for agent registry, capability-based controls, agent-to-agent payments | Alpha/DevNet | **Watch + adapter**: matches the NANDA/x402 registry-and-payments ambition, but nothing learner-critical builds on a devnet; integrate behind `RegistryAdapter` so the swarm can list there without depending on it |

Measured orchestration tradeoffs worth designing around (LangGraph community benchmarks): supervisor routing costs roughly 2–4 LLM calls and ~4–9 s per request but gives ~94% routing accuracy and a full audit trail; swarm handoffs cost 1–2 calls and ~3–5 s at ~91% accuracy. The standing recommendation — start supervisor, graduate hot paths to swarm when latency data demands it — is adopted below, with a **3-handoff recursion guard** in either mode.

### 12.2 The three-plane architecture

**Plane 1 — Control (deterministic services, no LLM).** The LPA, ZPD dial, sequencer, assessment gates, and affect classifier stay exactly as specified in ACP-01…09: versioned services with single-writer contracts. *Debug finding:* these must **not** be rebuilt as LLM agents — determinism is what makes the dial auditable, and no framework in the review changes that. The fabric consumes their outputs; it never replaces them.

**Plane 2 — Conversation (the mentor swarm).** The hall reps plus Chris, Joyce, Tessa, Gemma, Iris, Dana and Sam are LangChain agents on the LangGraph runtime. Topology is **hub-hybrid**: Chris runs as supervisor for cross-trade and unrouted questions (audit trail where boundaries are fuzzy); within a hall, agents hand off swarm-style (Joyce → Sam for a welding-safety question) because domain boundaries there are crisp. Durable execution carries a mentor conversation across sessions and devices — a learner resumes mid-dialogue days later without context loss. Middleware stack on every mentor: PII redaction → scope guard (mentors are read-only consumers of dial state; ACP-09 rule enforced in code) → HITL escalation to human instructors on flagged turns.

**Plane 3 — Factory (ROMA-pattern content production).** Authoring 25,875 skeleton objects and their revisions is itself a long-horizon multi-agent task, and the recursive shape fits: Atomizer decides whether a curriculum request is one lesson or a subtree; Planner expands a hall level into its 110 lesson briefs with prerequisite edges; Executors draft lessons, checks, and rubrics in parallel; the Aggregator assembles level packages; the **Verifier is the pipeline's `schema_ok` gate plus a pedagogy rubric** — nothing enters `calibrating` without passing it. Factory agents never touch learners; their output enters the world only through the ACP-10 pipeline.

**Topology is built and measured (v0.1).** The router implements the hub-hybrid above with a **3-handoff recursion guard** in both modes plus loop detection: a mentor pair that would bounce a learner back and forth terminates at the supervisor and the full hop chain lands on the audit log. On a labelled routing set it measures 1.0 accuracy at a mean 1.33 LLM calls per turn — crisp in-hall questions take the cheap swarm path, fuzzy ones pay for the supervisor. The LangGraph wiring itself is written but **not executed** (it needs credentials); where framework code and the tested contract disagree, the contract wins. One decision to make before building it: implementing the guards in Python duplicates security-relevant logic already tested in JS — either run the fabric on `@langchain/langgraph` and import the tested module, or make the guards one service both languages call. Hand-porting is how two copies drift.

**External plane — registry & economy.** Agents keep their swarm registration (NANDA-style) and x402 payment identity behind `RegistryAdapter`, with an ASI:Chain implementation flagged `experimental` until the chain leaves DevNet. Capability-based controls there map cleanly onto the scope guards above when it matures.

---

## 13. ACP-12 — Agent Training & Evaluation

The mentors get the same treatment the learners get: a profile, evidence-based promotion, and no certification without verification.

### 13.1 Agent curriculum

Each mentor's knowledge base is built per trade in layers — union training guide, machine/tool library entries for its hall, the misconception library for its skills, and its persona sheet (voice, history, boundaries). KB builds are versioned artifacts; a mentor version is `(model, KB rev, middleware config)`.

### 13.2 The evaluation harness

Every mentor version must pass, in order:

1. **Golden-set accuracy** — ≥ 95% on a held-out slice of its trade's question banks (never the serving slice; regenerated quarterly from the seeded generators).
2. **Hint-rung discipline** — on scripted learner transcripts, the mentor's help must land on the requested ACP-04 rung: a rung-2 request answered with a rung-4 worked example is a failure (over-helping is the classic tutor-model bug).
3. **Scope compliance** — red-team suite: attempts to get the mentor to change a setpoint, reveal another learner's data, or certify a gate must all be refused (mentors voice the system; they don't steer it).
4. **Persona stability** — consistency score across 200 paraphrased probes; drift beyond threshold fails the build.
5. **Outcome lift (champion/challenger)** — the candidate serves 5% of hall traffic in shadow-safe mode; promotion requires non-inferior learner outcomes (gate pass rate, time-in-`SUPPORT`) vs. the champion at 95% confidence. Regression on any ACP-08 parity metric is an automatic veto.

Failed evals produce tickets, not silent retries. The harness runs on every KB revision, model swap, or middleware change — no exceptions, including "small" prompt edits.

**The harness is built and tested (v0.1).** Two findings from building it:

*An eval suite that has never failed an agent is untested.* The harness therefore ships with four deliberately broken reference mentors — an over-helper, a scope violator, a persona drifter, and one that guesses on trade knowledge — and its own test asserts each fails **exactly** its own gate while the compliant mentor passes all five. That is what distinguishes a discriminating suite from a merely strict one.

*Gate 5 earns its place.* The over-helper passes gates 1, 3 and 4 cleanly — it knows its trade, respects scope, holds its voice — and only cohort outcome catches it: mean served rung 1 → 4, ability gain 26.3 → 24.7, lift −0.063 against the −0.03 threshold. Gates 1–4 are all things a mentor can look good on while leaving learners worse off. Over-helping in particular is the failure users never report, because it feels generous.

**Guards are code, not prompts.** Scope enforcement, PII redaction (inbound *and* outbound — models leak too), rung clamping and HITL escalation live in middleware every mentor runs behind, so ACP-09's read-only rule is enforced rather than requested. Scope violations are *contained and counted* rather than thrown, which is what makes them measurable by gate 3 instead of merely fatal in a hall.

### 13.3 Agent telemetry

Mentor turns emit onto the same bus (`mentor.turn`: version, rung served, handoffs, escalations). Each mentor accrues its own vector — golden-set trend, handoff precision, escalation rate, outcome lift — reviewed in the weekly ops job. An agent, like a learner, can enter `SUPPORT`: sustained degradation pins traffic back to the champion automatically.

---

## 14. ACP-13 — Network Management & Automation

### 14.1 Registries (single source of truth, one per aggregate)

**Module registry** — the ACP-10 ledger with pipeline state per ID. **Agent registry** — mentor versions, eval results, traffic split, hall assignment. **Skill graph registry** — versioned graph; edits require a migration script for affected profiles. External listings (NANDA/ASI) mirror from these, never the reverse.

### 14.2 Rollout discipline

Everything ships hall-by-hall: canary = 1 hall (5% of network), then 5 halls, then all 33, with automatic rollback on ACP-08 stop conditions. Content, agents, and dial parameters use the same lanes. Dial parameter changes additionally require a 2-week shadow run (log intended actions, don't act) — the same rule the original build order set.

### 14.3 The automation loop

| Job | Cadence | Does |
|-----|---------|------|
| Calibration sweep | nightly | re-fit item difficulties, flag drift, demote drifting modules |
| Coverage bot | nightly | skill-node reachability per band; opens `coverage.gap` tickets routed to the factory plane |
| Parity job | weekly | ACP-08 cohort comparisons; blocks all promotions while red |
| Eval harness | on change | full §13.2 suite per mentor version |
| Factory queue | continuous | ROMA-pattern authoring against `coverage.gap` and revision tickets |
| Champion review | weekly | promote/hold/rollback per mentor from outcome-lift data |
| Cost governor | continuous | per-plane token budgets: conversation plane degrades to smaller serving models under budget pressure, control plane never throttles |

### 14.4 Scale posture

Sharding follows the natural partition: one cell per union hall (its mentor set, its module slice, its learners' hot profiles), with cross-hall traffic through Chris's supervisor node only. The multiplayer relay already handles 2,000-seat rooms with spatial interest management; the fabric mirrors that shape — nothing global in the hot path except the bus and the registries. Durable-execution checkpoints make cells restartable without losing a single mid-quest learner.

**SLOs:** dial decision < 150 ms p99 (it's arithmetic — keep it that way); mentor first token < 2.5 s p95; profile update visible to the dial < 1 s; factory lesson turnaround < 24 h from `coverage.gap` to `schema_ok`.

**Build order for this wave:** module registry + ledger enumeration first (it is the ground truth everything else references) → LangGraph runtime with Chris-as-supervisor and two pilot halls → eval harness before any new mentor ships → factory plane against real `coverage.gap` tickets → external registry adapter last.

---

## 15. ACP-14 — Shadow-Mode Calibration Results

The build order in §10 says the dial runs in shadow mode before it touches a learner. This section is that run, executed in simulation against the module registry data pack. **It is reported here because it changed the spec:** two defects in the v1.1 controller were found and fixed, and the tuning sheet was re-derived from evidence rather than assertion.

### 15.1 Method, and what it does and does not prove

Six synthetic learner archetypes — steady, fast climber, struggler, misplaced expert, erratic performer, and a returner with a 21-day gap — each run 400 attempts across 16 sessions, three seeds, against three strategies: the ZPD dial, fixed difficulty 50, and random difficulty. Each learner has a **true latent ability the dial never sees**; the headline metric is measured against that ground truth.

> **In-band %** = the share of served tasks whose *true* success probability, computed from the learner's hidden ability, falls inside [0.70, 0.85]. It is the ZPD invariant (P1) scored by an oracle.

This validates the **controller**, not the pedagogy. Whether ZPD-targeted practice teaches better than massed practice is an empirical question for the stepped-wedge evaluation with real learners; the simulated learner's improvement is a property of the learner model and proves nothing about teaching. What it does prove: whether the dial can *find and hold* the edge of a capability it cannot observe.

### 15.2 Two defects found

**Defect 1 — the session rail froze the dial.** §3.2 clamps setpoint movement to `session Δ ≤ 10`, anchored at `sessionStart`. Nothing in v1.1 said when `sessionStart` is re-anchored. In the reference implementation it was set once at construction, so the clamp silently became a permanent ±10 cap around the learner's *initial* setpoint. A learner improving by 30+ points was still being served near-beginner tasks 300 attempts later, at 93% success — the boredom detector fired continuously and the dial obediently stepped up into a rail it could not pass. **Fix:** `startSession()` re-anchors the cap at every session boundary, and this is now normative, not incidental. A regression test asserts that a dial which is never re-anchored *does* stay pinned, so the requirement cannot be silently deleted.

**Defect 2 — two clamps with different anchors.** The setpoint getter re-applied the θ rail *after* the session cap had been applied at write time, so as θ moved the getter handed back values the session cap had explicitly rejected. **Fix:** all clamping happens in one place, in one order — θ rail (safety) then session cap (experience), with the session cap winning on conflict.

**Consequence for the design.** Both defects share a root cause: an open-loop step controller whose output is bounded relative to an *estimate* (θ) cannot correct a systematically biased estimate. v1.2 adds a **closed-loop correction** — invert the logistic on the observed success rate to get the difficulty that would have produced the band centre, and move the setpoint a damped fraction of the way there:

```
p̂        = hint-discounted success rate over the window
θ_implied = d̄ + 12 · log₁₀( p̂ / (1 − p̂) )       // d̄ = mean served difficulty
c_target  = θ_implied + setpointOffset
c        += loopGain · (c_target − c)            // loopGain = 0.3
```

The affect-driven asymmetric steps (§3.2) still run on top: the closed loop finds the band, the affect logic decides whether to sit above or below it. θ remains the estimator for item selection, gates and sequencing — it is no longer the only thing steering the dial.

A third, smaller fix: σ now **re-inflates** when a learner keeps surprising the model in one direction (EWMA of signed surprise > 0.15). A σ pinned at its floor cannot track a genuinely improving learner, which is exactly when tracking matters most.

### 15.3 Results

In-band residency, by archetype and strategy (3 seeds, 400 attempts each):

[[CHART:inband]]

| Archetype | Strategy | In-band % | Success % | θ error | Hint % |
|---|---|---:|---:|---:|---:|
| Steady learner | **ZPD dial** | **39.0** | 74.5 | 1.3 | 3.4 |
| | Fixed 50 | 10.3 | 52.7 | 2.2 | 16.3 |
| Fast climber | **ZPD dial** | **39.8** | 74.2 | 3.3 | 2.3 |
| | Fixed 50 | 3.7 | 96.9 | 18.5 | 0.2 |
| Struggling learner | **ZPD dial** | **42.3** | 72.3 | 3.6 | 8.1 |
| | Fixed 50 | 0.0 | 6.0 | 5.7 | 100.0 |
| Misplaced expert | **ZPD dial** | **39.6** | 74.8 | 2.4 | 1.1 |
| | Fixed 50 | 0.0 | 99.9 | 14.8 | 0.0 |
| Erratic performer | **ZPD dial** | **36.6** | 73.6 | 0.9 | 4.0 |
| | Fixed 50 | 12.4 | 84.3 | 11.8 | 1.7 |
| Returner (21d gap) | **ZPD dial** | **41.2** | 74.3 | 2.5 | 2.9 |
| | Fixed 50 | 10.3 | 52.7 | 2.2 | 16.3 |

**Mean in-band: dial 39.8%, fixed 6.1%, random 7.0%** — the dial holds the ZPD roughly 6× better than either baseline.

Three results matter more than the headline:

**Every archetype's mean success rate lands inside the band** (72.3–74.8%), including the struggler, whom fixed difficulty leaves at 6% success and 100% hint dependence — a learner that system simply fails. The dial's worst case is a learner it serves slightly too easy, not one it drowns.

**θ tracking error stays at 0.9–3.6 points** across every archetype, against 18.5 for the fast climber and 14.8 for the misplaced expert under fixed difficulty. Getting placement wrong is the failure mode adaptive systems are built to prevent, and it is the one the baselines fail worst.

**Dial state distribution: FLOW 53.7%, STRETCH 25.7%, SUPPORT 16.8%, RECOVERY 1.0%, CALIBRATING 1.6%.** Roughly a quarter of windows push up and a sixth ease off — the dial is working continuously rather than settling, which is what a non-stationary learner should produce.

**Why in-band tops out near 40%.** The band is narrow: [0.70, 0.85] spans only 4.6 difficulty points. With θ tracking error of ~2–3 points and item difficulty granularity of its own, a per-attempt residency near 40% is close to what this estimator's precision allows. The mean success rate sitting inside the band is the more robust reading of the same result. Pushing residency higher means a more precise θ (longer windows, better-calibrated items), not a more aggressive controller — and the sweep below shows what that costs.

### 15.4 Parameter sweep

20 configurations across `window` ∈ {3, 5, 8, 10} × `loopGain` ∈ {0.3 … 1.0}:

| window | loopGain | In-band % | Success % | θ err | Worst archetype outside band |
|---:|---:|---:|---:|---:|---:|
| 10 | 0.30 | 42.4 | 80.1 | 3.47 | 1.1 |
| 10 | 0.45 | 41.2 | 79.6 | 2.78 | 0.7 |
| 10 | 0.80 | 40.4 | 79.1 | 2.48 | 0.0 |
| **5** | **0.30** | **40.1** | 76.4 | 2.72 | **0.0** |
| 8 | 0.45 | 36.2 | 79.6 | 2.48 | 0.0 |
| 5 | 0.60 (v1.1 candidate) | 33.5 | 77.4 | 3.27 | 0.0 |
| 3 | 1.00 | 26.4 | 77.7 | 3.32 | 0.0 |

`window = 10` scores marginally higher on residency, but a window of 10 means a struggling learner endures **ten** tasks before the dial reacts — twice the exposure of `window = 5` for 2.3 points of residency. The chosen defaults take the responsiveness: **`window = 5`, `loopGain = 0.3`**, which puts no archetype outside the band and halves the reaction latency of the best-scoring configuration. Responsiveness on the anxiety path is worth more than a residency point, and this is a pedagogical judgment the numbers inform but do not make.

### 15.5 Changes to the tuning sheet

| Parameter | v1.1 | v1.2 | Why |
|---|---|---|---|
| Control mode | open-loop steps | **closed loop + affect steps** | open loop cannot correct biased θ |
| `loopGain` | — | **0.3** | calibration sweep |
| `railLo` / `railHi` | θ−12 / θ−2 | **θ−14 / θ+0** | rails were binding during normal operation |
| σ behavior | monotone decay | **re-inflates on sustained surprise** | a floored σ cannot track a moving learner |
| `sessionStart` | undefined | **re-anchored every session (normative)** | Defect 1 |
| Clamp location | two sites | **one site, rail-then-session** | Defect 2 |
| θ range | unbounded | **clamped to [0, 100]** | θ shares the difficulty scale |

### 15.6 What still needs real learners

The simulation cannot answer these, and shipping should not pretend otherwise: whether the affect signals (`latZ`, `latVarZ`, hint bursts) actually predict boredom and anxiety in humans — here they were generated by the same model that consumed them, which is circular by construction and the weakest part of this exercise; whether item difficulties calibrate as cleanly as the synthetic ones; whether learning transfers between the modules the sequencer interleaves; and every parity question in ACP-08, which needs cohorts the simulation does not have. **Shadow mode on real telemetry, with the dial logging intended actions and acting on none, remains a required gate before activation.**

---

## 16. ACP-15 — Knowledge-Graph Tracing & Sequencing

Everything up to v1.3 traced **one skill at a time**. The dial tuned difficulty on an island. Real competence is a graph — evidence about one node is evidence about its neighbours, prerequisites gate readiness, confusable pairs corrupt each other, and what is not revisited is lost. This module is where "which skill, and why now" is decided, and it is the layer adaptive systems most often skip: serving a fixed list while calling the difficulty knob adaptive.

Building it against the simulation surfaced **five defects**, four of them in the v1.3 protocol rather than in the code written to implement it.

### 16.1 Credit propagation

Evidence on one skill moves its neighbours, damped and one hop only (no graph-wide diffusion):

| Edge | Direction | Factor | Meaning |
|---|---|---|---|
| `requires` | child → prerequisite | 0.20 | succeeding at something that rests on X is evidence X is sound |
| `requires` | prerequisite → child | 0.10 | mastering a foundation slightly lifts what stands on it |
| `supports` | both | 0.10 | soft transfer |

**The governing rule: indirect evidence is never direct evidence.** Propagated credit moves θ but shrinks σ at 15% of the direct rate, and it *never* counts toward a gate. A learner is certified on what they demonstrated, not on what was inferred about them. Every propagated change carries a `why` — the audit surface must be able to explain why a skill the learner never touched changed.

**Interference:** when a confusable sibling was served within the last two attempts, this attempt's evidence is discounted to 0.6 — the learner may be answering about the other one.

### 16.2 The five defects

**Defect 3 — practice can never certify anyone.** The dial holds practice at the band *centre* (θ−6.5) because that is where learning happens. The skill gate accepts demonstrations only at the band *top* (θ−5) or harder. The gap is 1.5 points and it is fatal: normal practice is, by construction, always slightly too easy to count, so a learner could be believed-mastered forever and never produce gate-qualifying evidence. **Fix:** a `verify` mode. When mastery is believed but undemonstrated, the sequencer deliberately serves a short run at gate difficulty with hints closed. *Practice optimises for learning; verification optimises for proof. They are different jobs and need different difficulties.*

**Defect 4 — improvement retroactively invalidated its own evidence.** Qualification was recomputed against *current* θ. So as a learner improved, θ rose and their past demonstrations silently stopped qualifying — the better they got, the less their proof counted. **Fix:** qualification is stamped at serve time and never recomputed.

**Defect 5 — a query could silently un-certify.** `checkSkillGate` recomputed from history every call, so one bad re-test after certification revoked it as a side effect of *asking*. **Fix:** gates are **awarded** events stored on the profile. Revocation is a deliberate act with its own reason string, never a consequence of a query.

**Defect 6 — mastery belief outran evidence.** Raw BKT reports `p_mastery > 0.95` after a handful of favourable observations. Across a 33-node graph that is catastrophic: every skill read as mastered within a few attempts, the frontier emptied, and the curriculum "completed" without the learner learning anything — measured, 33/33 skills believed mastered after 201 attempts. **Fix:** the reported posterior is shrunk toward the prior by the evidence behind it, `p = L₀ + (raw − L₀)·n/(n+4)`. A belief held on three observations is not the belief held on fifty: a raw 0.96 on n=3 now reports 0.50. P(T) also drops 0.20 → 0.10.

**Defect 7 — unbounded interleaving is thrashing.** One root skill unlocking eleven strands at once spread the attempt budget across all of them, leaving every skill under the practice it needed. Measured: an unbounded frontier learned **0.67** skills against 6+ for a bounded one. **Fix:** a **working set** — at most *k* skills in active development, admitted by graph leverage, interleaved within the set, and a new one admitted only when another graduates.

### 16.3 Results

Same dial, same budget (420 attempts over 70 days), three sequencing strategies. `blocked` is the traditional curriculum — prerequisite order, one skill worked to mastery before the next; it also respects prerequisites, so graph-vs-blocked isolates interleaving, spacing and verification rather than mere ordering. `flat` picks any unmastered skill at random.

| Strategy | Skills certified | Skills learned | Ability gained | Retention @30d | Durable ability | Prereq violations |
|---|---:|---:|---:|---:|---:|---:|
| **Graph sequencer** | **4** | 6.3 | 166.7 | **0.78** | **130.0** | **8.5%** |
| Blocked | 0 | 14 | 216.8 | 0.32 | 69.4 | 0% |
| Flat | 0 | 1 | 63.7 | 0.27 | 17.2 | 91% |

Two findings matter:

**Only the graph sequencer certifies anyone.** Both baselines gate zero skills — not because their learners know less, but because neither ever serves a verification attempt at gate difficulty. Certification is not a by-product of practice; a system that never deliberately asks for proof cannot issue any. Blocked practice acquires *more* raw ability (216.8 vs 166.7) and certifies none of it.

**Massed practice acquires more and keeps less.** Blocked ends with 2.4× more raw ability gained, but 0.32 retention against 0.78 — durable ability (gained × retained) is 69.4 against 130.0, a 1.9× advantage to spaced sequencing. Fast-looking progress that evaporates is the failure mode a trades academy can least afford: a certificate should mean the holder can still do it next month.

### 16.4 An uncomfortable sweep result

How many skills should a learner have open at once?

| Working set | Certified | Ability | Retention | Durable |
|---:|---:|---:|---:|---:|
| 1 | 5 | 187.8 | 0.76 | **142.7** |
| 2 | 3.7 | 182.6 | 0.77 | 140.6 |
| **3** | **4** | 166.7 | 0.78 | 130.0 |
| 4 | 3 | 178.0 | 0.77 | 137.1 |
| 6 | 3 | 146.0 | 0.79 | 115.3 |
| 8 | 2.7 | 121.7 | 0.78 | 94.9 |
| 11 | 1.7 | 79.3 | 0.82 | 65.1 |
| 33 | 0 | 34.0 | 0.27 | 9.2 |

The measured optimum is **1–2**, which sits awkwardly against §5.2's claim that interleaving beats blocking. The honest reading: what this simulation demonstrates is that **wide working sets dilute practice** — which it shows decisively — and *not* that interleaving fails, which it cannot show. Interleaving's main claimed benefit is discrimination between confusable items, and the learner model represents that only through the sparse `interferes` edges. The model is under-specified for the very thing being tested.

**So the default is 3, not the measured 1.** It sits inside the flat part of the curve (130 vs 143 durable, ~9%), preserves interleaving for the discrimination benefit the simulation cannot measure, and hedges against a known model deficiency rather than over-fitting to it. Real telemetry should settle this, and it is exactly the kind of question a stepped-wedge arm can answer.

### 16.5 Sequencing policy

```
next():
  1. wheel-spin check      — 10+ attempts, flat mastery -> diagnose, don't repeat
  2. verification          — believed but undemonstrated, budget 1-in-8, runs of 3
  3. review cadence        — 1-in-4 when the queue is hot (p_recall < 0.7)
  4. working set           — <= 3 open skills, interleave within, admit by leverage
  5. score and take best   — 0.45 zpd_fit + 0.25 review + 0.15 leverage
                             + 0.10 modality + 0.05 novelty
```

**Wheel-spinning gets the humane response.** Ten-plus attempts with flat mastery stops serving the skill and asks *which prerequisite is actually missing*, then routes there — because the answer to stuck is never more of the same. If prerequisites are sound, the learner drops to a worked example instead.

**Verification is budgeted, not a mode.** Unbudgeted, a fast-moving posterior across 33 nodes kept something permanently "ready to test" and verification consumed 48–65% of all attempts — proof crowding out the learning it exists to certify. It is now capped at 1-in-8, requires ≥8 observations and at least one unaided success before it will spend an attempt, runs in units of three, and a failed run returns the learner to practice for 30 attempts rather than nagging.

**Every pick defends itself.** `next()` returns a `why` string and its score components, and the picks carry `poolSize` — because the interleaving rule can only be judged where an alternative existed. Early in a graph, one root skill gates everything and a long run on it is correct behaviour, not a violation.

### 16.6 What this does not establish

The prerequisite structure, the forgetting curve, and the spacing benefit are **assumptions of the learner model** (A1–A3, stated in the simulation source). What is tested is whether the sequencer converts those beliefs into outcomes and respects its own constraints — not whether the beliefs are true. The retention advantage in particular is largely *assumed* by A2; the fair claim is that the sequencer exploits spacing where blocked practice does not, given a forgetting curve. Whether real trades learners forget on anything like that curve is an empirical question for the stepped-wedge evaluation, and the working-set result above is the first thing real telemetry should overturn or confirm.

### 16.7 Two more, found by soak

The unit suites run tens to hundreds of attempts. A long-run soak — 4,000 attempts across three seeds, asserting the invariants continuously rather than at the end — found two failures that only appear with time.

**Defect 8 — the setpoint could escape the safety rail.** All clamping happens in one place (defect 2's fix), in the order: θ rail, then session cap, with the cap winning on conflict. That ordering is wrong. The session cap is a *comfort* bound — don't lurch mid-session; the θ rail is a *safety* bound — never serve something absurdly far from the learner. When a session anchor went stale-high and θ subsequently fell, the cap pushed the setpoint above the rail: exactly the case the rail exists to prevent. **Fix:** cap first, rail last. The safety bound is the final authority, and it now holds unconditionally.

A welcome side effect: with the rail final, the v1.1 freeze is *structurally* impossible even if a caller forgets `startSession` — the rail drags the setpoint along as θ moves. The regression test that asserted "a never-re-anchored dial stays pinned" was therefore asserting something no longer true, and has been replaced by the two invariants that actually matter: the cap bounds movement while θ is stable, and the rail holds in every case.

**Defect 9 — the sequencer stranded the learner.** Verification is budgeted at 1-in-8 so proof cannot crowd out practice (§16.5). But once a hall's open skills are all believed-mastered and awaiting proof, there *is* no practice to protect — and `next()` returned `null`, serving a blank screen. Measured: the sequencer stalled at ~2,200 attempts with **25 of 33 skills still uncertified**, and certification simply stopped. **Fix:** when the ordinary pool is empty the budget has nothing left to protect, so it is spent rather than withheld; and if verification is also unavailable, the learner consolidates on the least-certain uncertified skill instead of falling off the end. Certification over the same run went from 7–9 skills to **30–33 of 33**.

The general lesson, and the reason the soak now ships with the bundle: *a budget that protects a resource must be released when the resource is gone.* Rate limits written to stop one thing crowding out another become deadlocks when the other thing runs out.

### 16.8 Two more, found by fuzzing inputs

The soak pushes *time*; a fuzz pass pushes *inputs* — every value a broken or hostile client could send, plus learners behaving in ways the happy path never produces.

**Defect 10 — one malformed event destroyed a learner permanently.** `record()` accepted a non-finite difficulty, θ became `NaN`, and NaN is absorbing: every subsequent update, setpoint and gate decision on that learner returned NaN for ever. A single bad telemetry event — one client bug, one truncated payload — silently and irreversibly destroyed someone's record, with no error and no signal. ACP-01 §1.4 already required consumers to tolerate malformed events; the defect was reading "tolerate" as *ingest* rather than *reject*. **Fix:** an input guard at the profile boundary. Non-finite difficulties are rejected and counted (`rejected_n`), rungs outside the ladder are clamped rather than indexed, and weights are bounded. Rejections are counted rather than thrown, so a broken client shows up in the numbers instead of taking a hall down.

The adversarial learners are now part of the suite, and three of them assert properties worth stating outright: a learner who never succeeds is **never** certified; rung-5 help on every attempt **cannot buy certification**; and a learner failing everything is eased *downward*, never up.

**Defect 11 — the staleness guard measured the wrong thing.** The console embeds a snapshot of the control plane and had already shipped once with a stale dial, so a build stamp was added: a hash of the protocol sources baked into the page, checked by CI. It reported "current" while the page was still missing two fixes. The stamp hashed the *sources*, but the build read a separately-generated intermediate bundle — and only the intermediate was stale. **Fix:** fold the bundling into the build. One step, no intermediate, nothing to drift.

That one is worth dwelling on, because the guard was written specifically to catch this class of bug and it did not: *a freshness check that measures anything other than the artifact actually shipped will eventually certify a stale artifact.* The guard is now proven by deliberately dirtying a source and confirming it refuses, rather than only by observing it pass.

---

## 17. ACP-01/08/09 in code — the bus, the envelope, the log

The connective tissue was the last thing still living only in prose. Components called each other's methods directly, which meant the two rules the architecture rests on — **single writer per aggregate** (ACP-09) and **every adaptation on the audit log** (ACP-08) — were true only as long as everyone remembered them. A mentor could not write dial state because no one had written the line of code that would, which is not the same thing as a mentor being unable to.

### 17.1 The bus enforces the contract

Each topic in §9 now has exactly one permitted publisher, declared in a table the bus checks on every publish. Components receive a publisher **bound to their own role**, so nothing is handed a way to claim another. A mentor attempting `dial.setpoint`, `profile.updated` or `gate.decision` is refused — in strict mode by throwing, in production mode by containing and counting, because a refused publish must be *measurable*, not merely fatal.

The console ships a button that makes a mentor genuinely attempt the write, so the refusal can be watched rather than trusted.

### 17.2 The §1.4 guards, implemented

Each one exists because the naive version is wrong, and each is now a test rather than a sentence:

| Guard | Behaviour |
|---|---|
| At-least-once transport | dedupe on `event_id`; duplicates counted, never hidden |
| Client clock skew > 2 min | server receipt time is trusted; the envelope records which was used |
| Fewer than 3 usable events | **no** profile update — the reason is returned instead |
| Missing modality | defaults to `quiz` |
| Failing subscriber | contained, counted and audited; siblings still receive the message |
| Rejected telemetry | lands on the audit log, so a broken client is visible in the record |

### 17.3 One log, two audiences

The learner's "Why this?" and the compliance record read the **same rows**. That is the only arrangement in which an explanation shown to a person and a record shown to a regulator cannot disagree. Entries are frozen on append and `entries()` returns a copy, so a caller holding a reference cannot rewrite history.

xAPI egress is an adapter on the end of that same pipeline rather than a second one, and it carries no affect data — ACP-08 forbids affect labels reaching an export, and the test asserts it.

### 17.4 Defect 12, caught by the guard that had just been fixed

Adding the bus pack made the console freshness check report a confidently wrong
answer: it hashed a source list that did not include the new files. The checker
and the builder each declared their own copy of "the sources", and the copies
drifted the instant a pack was added — defect 11's shape a second time, one
level up. There is now a single `console_sources.py` that both import.

The recurrence is the point. A freshness check is only ever as good as its idea
of what it is checking, and any *second* declaration of that idea will
eventually disagree with the first.

### 17.5 What this does not solve

No network transport, persistence or retry policy: this is the in-process contract layer, and a real deployment puts a broker underneath. What must survive that move unchanged is the topic list and the single-writer table — everything else is implementation.

---

## 18. ACP-08 in code — parity, stop conditions, overrides

The audit log arrived with the bus; the rest of ACP-08 was still prose. This module is the one that protects learners *from* the system, so everything in it **refuses** rather than warns. A safeguard that only logs is a log.

### 18.1 Parity

Cohort metrics — gate pass rate, time in `SUPPORT`, stretch-offer rate — are compared across site, language, device tier and age band. A relative disparity above **10%** opens a ticket, and an open ticket **blocks promotions** (ACP-13). Cohorts under n=20 are treated as noise, so the alarm stays worth listening to.

The sharpest rule in the spec is that dial parameters may not be tuned per cohort to *mask* a disparity — root cause belongs in content or calibration. That is now enforced rather than requested: the monitor records a fingerprint of the parameters each cohort is served, and a disparity that is open **while cohorts sit on different settings** raises `parity.masking_suspected`. Without a record of what each cohort was actually served, "we fixed the metric" and "we hid the metric" are indistinguishable afterwards.

### 18.2 Stop conditions

Adaptation halts on any of: calibration drifting more than 8 points/week across more than 20% of items; a cohort spending more than 25% of its time in `SUPPORT`; or **the parity job failing to run inside its window**. That last one matters most — it means the system will not keep adapting unwatched. While halted, every learner is served fixed difficulty, because a degraded dial is worse than no dial, and halt/resume are logged as transitions rather than re-logged on every evaluation.

### 18.3 Overrides, and their order of precedence

Instructors may pin anything; learners get **"easier today"** twice a week, granted without question and declined kindly when spent, with the refusal logged too so nobody has to argue about it. Evidence from a pinned episode is weighted at 0.3, because an overridden episode is biased evidence (§2.2) — and full weight returns the moment the pin is released.

Precedence is tested, not assumed: **a pin beats the dial, and a stop condition beats the pin.** When the system has stopped trusting its own calibration, it does not honour a setpoint derived from it, whoever set it.

One implementation note worth keeping: the console's first version told the learner their tasks would run easier and then didn't change the difficulty. The lever now moves the served difficulty and clears at the next session boundary — it is an easier *day*, not a setting. An interface that promises an adaptation the system does not make is a worse failure than not offering the lever.

---

## 19. Launch posture — commercialization and security

A protocol that never ships protects nobody. This section is the state of the platform as a *product*, and it is written to be shown to investors, partners and institutions unedited.

### 19.1 What the security pack enforces

`security/` ships with 16 tests, each written as a refusal that must actually happen:

| Control | Rule |
|---|---|
| Tenant isolation | Checked **independently of capability**, on every access. The most senior role in one tenant is nobody in another. |
| Least privilege | No wildcard capability. A learner reads only their own record; an instructor only their assigned learners; a mentor agent reads content and nothing else. |
| Identity access | `pii.reveal` is held by **no standing role**. It is granted per incident with a reason and an approver, expires on its own, and every use is an audit event. |
| Rate limiting | Separate buckets for auth, agent turns, API and export — a flood of cheap calls cannot spend the expensive allowance. Auth throttling is audited. |
| Data classification | Five classes with per-class retention. **Affect is the shortest-lived and most protected class (90 days), never exported, never visible to an employer.** |
| Erasure | Identity lives only in the enrolment mapping; erasure breaks it, which is what makes the remaining behavioural rows genuinely anonymous rather than "anonymised". |
| Raw streams | Keystroke and video capture is refused at the storage boundary, not merely discouraged. |

**Fail closed twice on the rule that matters most.** A mentor agent is blocked from writing control state by the bus *and* by the authorizer. Duplication is worth its cost only where the consequence is severe; certification integrity is that case.

### 19.2 The honest gap

The threat model in `SECURITY.md` lists what is not built, because a security document that only describes strengths is marketing. Missing and required before any public launch: authentication itself (this is the *authorization* layer), TLS and encryption at rest, persistence and tested backup restore, secrets management, dependency scanning and SBOM, an external penetration test, a staffed incident-response rotation with breach-notification clocks, and a route for a learner to contest a certification decision with a human.

Compliance posture is stated the same way: the controls FERPA, GDPR, COPPA, WCAG 2.2 AA and SOC 2 require **exist and are tested**, and none of them are **certified**. Certification is an external process that has not been undertaken.

### 19.3 What the public page may and may not say

The landing page carries a status table that names lesson content as placeholder, efficacy as unestablished, accreditation and union endorsement as **none**, and the production platform as not built. Three claims are permanently forbidden regardless of commercial pressure:

1. That any credential issued here is recognised, accredited or union-endorsed.
2. That the platform improves learning outcomes — until the stepped-wedge trial with real apprentices reports, every efficacy number is a simulation result and must be labelled one.
3. That training content is verified against any jurisdiction's code. It is general good practice, and safety-critical work must still be signed off by qualified people on real sites.

Publishing the unfinished list is not modesty. Education technology has a credibility problem precisely because intentions get written in the present tense, and the institutions worth partnering with can tell the difference.

### 19.4 Defect 13 — the packaging defect

The v2.6 bundle failed its own verification the first time it was assembled.
Every suite passed from the directory it was written in and several failed from
the directory above it: the registry loader resolved `../pack/registry` against
the *working directory*, and the console's freshness check looked for its page
in `.`. Neither is a protocol error, and neither could be found by any harness
that runs the way the author runs it.

It is recorded here because it is the class of defect that separates code that
works from code that ships. A recipient unzips a bundle and runs it from
wherever they unzipped it; a build server runs it from a checkout root; nobody
runs it from the author's shell. Paths inside the packs now resolve against
`import.meta.url` (JavaScript) and `__file__` (Python), and `verify_all.sh`
runs all 124 checks from anywhere, with one exit code.

The general rule, which applies well beyond paths: **anything that reads from
the environment rather than from its own module is untested until it has run
somewhere else.** The same principle already governs the freshness stamp
(§17.4) and the tenant check (§19.1) — verify against a fixed reference, never
against ambient state.

---

## 20. ACP-04 in code — the ladder, and who is allowed to set its height

ACP-04 was specified in §4 and implemented nowhere. The rungs existed as a discount factor inside the dial, the mentor had a clamp, and the fading rule in §4.2 — the whole mechanism by which help retracts as a learner grows — ran in no code path at all.

### 20.1 The ceiling has two independent bounds

A served task's scaffold ceiling is the tighter of:

| Bound | Source | Why it is not derivable from the other |
|---|---|---|
| **Mastery** | §4.2 fading: <0.5 → 5 rungs, 0.5–0.8 → 3, 0.8–0.95 → 1, ≥0.95 → none | It tracks what the learner can do |
| **Mode** | A verification run is hint-free because it is proof, not practice | Verification happens *between* 0.80 and 0.95, exactly where the mastery rule still allows rung 1 |

Neither may loosen the other, so the ceiling is a `min` and never an override. A fading contract subtracts one further rung from whatever survives.

### 20.2 Defect 14 — a safeguard that defaulted to permissive

The sequencer stamped `scaffold_ceiling: 0` on verification picks and omitted the field on every other pick. The mentor's clamp read `ctx.scaffold_ceiling ?? 5`. The two halves were individually reasonable and jointly meant that **every ordinary practice task ran with the full ladder available**, up to co-completion, regardless of how well the learner knew the skill. Fading was specified, believed to be in force, and had never once fired.

Two changes, and the second is the general one:

1. The sequencer stamps a ceiling on **every** pick, through a single `stamp()` choke point rather than at six return sites.
2. The mentor's fallback is now `?? 0`, not `?? 5`. **A missing safeguard value must resolve to the most restrictive reading.** An absent ceiling means nobody decided, and nobody deciding is not permission.

### 20.3 The evidence path is the one that matters

The engine enforces the ladder on request and the mentor enforces it on delivery, but neither sits on the path that writes evidence. `Session.attempt()` accepted whatever rung its caller reported — and that function writes the history certification is computed from. An unclamped rung there would let a hinted success be recorded as unaided, which is the single lie that makes a gate meaningless.

The rung is now clamped there too, and an over-ceiling report is **audited rather than silently corrected**: the discrepancy is evidence about the client, and quietly fixing it would destroy the only signal that something upstream is wrong.

The hint record publishes as `hint.served` under the `hint_engine` role, not the mentor's. A mentor *delivers* help; it does not get to write the record of its own restraint. That is the same separation the bus already enforces for dial state, applied to the one remaining place a conversational agent touched the audit trail.

---

## 21. ACP-13 in code — registries, lanes, the loop, the governor

### 21.1 Pipeline transitions are a table, not an ordering

Module states are checked against an explicit transition table. Rank ordering would have permitted `draft → live` in a single step, which is precisely the move the pipeline exists to prevent. An adversarial walk of every legal path confirms that all 14 routes to `live` pass through `calibrating` and none is shorter than three transitions.

Two registry rules earn their strictness:

- **A mentor version cannot become champion without a passing eval record.** The check lives in the registry rather than the rollout lane, so no caller reaches champion status by another route.
- **A skill-graph revision requires a migration.** A prerequisite that appears retroactively can strand every learner already past it. The first publish is exempt — there is nobody to migrate.

### 21.2 Defect 15 — a gate in front of a mutable object

The adversarial pass asked whether a caller could take the record the registry handed it, flip `evals.pass` to `true`, and promote a mentor that had failed. It could. The gate was real and the object behind it was writable.

Records are now frozen all the way down and writes rebuild rather than mutate. The audit log had already solved this exact shape by freezing entries and returning copies (§17.3); the registries had not inherited it. **A validity check is only as strong as the immutability of what it validated.**

### 21.3 The lanes ask ACP-08 rather than re-deciding

Rollouts advance 1 hall → 5 → 33, with dwell windows between. Dial-parameter changes serve a 14-day shadow run before the canary opens. The lane manager holds no parity logic and no stop-condition logic of its own: it asks the ACP-08 objects and obeys. A second implementation of a safeguard is a second opinion, and two opinions about whether it is safe to ship is defect 12's shape.

A halt rolls live rollouts off the network automatically, and a rolled-back change **cannot be resumed** — it reopens as a new rollout, because resuming a reverted change skips the observation that reverted it.

### 21.4 The automation loop is load-bearing for a safeguard

Seven jobs on three cadences. The parity job is the one that matters: ACP-08 halts adaptation when it fails to run inside its window, so a scheduler that silently skips it is a *safety* defect rather than an ops annoyance. Two consequences are implemented rather than assumed:

- A throwing job does not stop the loop. One broken nightly job must not prevent the weekly parity job from running, since that would convert a small failure into a halted network.
- A safety-critical job with **no handler registered** is an audited event. The adversarial pass runs four weeks with every job but parity wired up, and the network stops shipping on its own.

### 21.5 The governor cannot throttle the control plane

The conversation plane degrades `full → compact → minimal` under budget pressure and keeps serving; the factory plane, which no learner is waiting on, is the one that pauses. The control plane is structurally un-throttleable — not merely well-funded — because it decides whether a learner is certified, and a certification that depends on the month's token budget is not a certification.

---

## 22. The identity, and why it is code

A product name is a claim the reader can check, and nothing was checking it. The Academy app had shipped for several versions as `SmartCity.X · Trade Quest Academy` — wrong on both halves — while the landing page, the console and this specification all said "SmartCiti.X : Trade Craft Academy". Three surfaces built weeks apart had each hand-rolled a palette, and the identity existed only as a habit.

`brand/identity.mjs` is now the single declaration: the names, the forbidden spellings with the reason each is wrong, the two-theme token set, the type stack, the wordmark, and the hall livery. `brand/lint.mjs` enforces it across the tree and runs in `verify_all.sh`. This is defect 12's lesson applied to prose rather than code — **a second declaration of one truth will eventually disagree with the first**, and a name is no exception.

### 22.1 Livery is derived, never assigned

Each hall's colour comes from a hash of its slug, with saturation and lightness **fixed** so no hall can be louder than another, and with the amber wedge the brand accent owns excluded so no hall impersonates the mark. Thirty-three hand-picked hues drift the moment a thirty-fourth hall opens — and the Academy app is already at 111.

### 22.2 A contrast failure the tokens were hiding

Writing the brand suite surfaced a live accessibility defect. The light-theme accent `#B0730C` carries white button text at **4.0:1** — below AA — so every primary action in the light theme failed, on a page already published. The accent is now `#9F680B`: the same hue and saturation, darkened until white clears 4.7:1. The hue was the brand; the lightness was never load-bearing.

### 22.3 Defect 16 — an assertion built on a guessed constant

The campus plan asserts that the longest hall name fits its pad. The constant behind it was estimated from "condensed faces run about 0.47em per character". The browser reports **8.74px at 13.5px type — the guess was 43% low**, and four hall names ran out of their pads and across their neighbours while the assertion sat there passing.

The constant is now measured and labelled as measured. The general rule is worth more than the fix: **an assertion built on a guessed constant is worse than no assertion**, because it reports a confidence it has not earned. It is the same failure as the console freshness stamp that hashed the wrong file list (defect 12) and the eval gate that guarded a mutable object (defect 15) — a check is only as good as the thing it actually checked.

### 22.4 The inconsistency, and how it was settled

The Academy app stated 111 union halls and `500,000 modules`. This specification, the registry pack and the public landing page stated `33 halls` and `333,333` modules. Both were internally consistent and they disagreed with each other, and the only reason it surfaced is that someone read them side by side.

It is settled by scaling to the larger network: **111 halls, 11,000,000 modules**, with the ledger rebuilt to close on that figure exactly (§11.1) and every surface regenerated from it.

The durable part is not the new number. It is `brand/figures.mjs`, which reads the canonical counts from the pack manifest — itself verified against the generated ID space — and fails the build if any surface states a superseded one. Superseded figures may still be *cited*, in backticks, because migration notes have to name what they replaced; that exemption is tested, including the case where a citation sits beside the same stale figure in live prose.

This is the third instance of one pattern, and by now it should be a rule rather than a lesson: the console source list (defect 12), the product name (§22), and now the figures. **Anything a reader can check is a claim, and every claim needs a checker.** Three surfaces will always eventually disagree unless something compares them.


---

## 23. What an adversarial review found

The bundle had 246 passing checks and had survived unit, simulation, soak, fuzz, integration and rendering passes. A fresh adversarial read of every module found **thirty-three defects**, and the shape of what it found is more useful than the list.

### 23.1 Nine safeguards that failed open

Not one of these was a broken control. Every one was a control that worked on the path the tests took and stood aside on a path nobody had written a test for.

| Control | How it stood aside |
|---|---|
| Rate limiting | `take('auth', k, -1000)` **added** a thousand tokens; a `NaN` cost disabled the bucket permanently, since `NaN < cost` is false forever |
| Tenant isolation | Checked only `if (resource.tenant !== undefined)` — a resource that omitted its tenant skipped the check that the comment above it called "always" |
| Time-boxed grants | Expiry was evaluated once, at principal construction. A cached principal kept a 50 ms `pii.reveal` grant for its whole lifetime |
| PII reveal | Passed `{ tenant: p.tenant }`, so the authorizer compared `p.tenant !== p.tenant` — a check that could not fail |
| Export and storage guards | Scanned top-level keys only, while real telemetry is an envelope around a payload |
| Registry gates | `transition()` and `promote()` were gated; the `commit()` they both called was public |
| Rollout dwell | `dwellHours` defaulted to `Infinity`, so the plain call skipped the observation window |
| Parity monitor | Reported green before it had seen a single cohort, and a run over zero cohorts satisfied the stop condition meant to catch a parity job that cannot run |
| Job scheduler | An async handler's rejection never reached the synchronous `catch`, so a permanently failing safety-critical job recorded `ok: true` |

The pattern is one sentence: **a default value is a policy decision, and every one of these defaulted to "assume the check passed."** `?? Infinity`, `!== undefined &&`, an empty ticket list, a `catch` that cannot see a promise. §20.2 had already drawn this conclusion once for the scaffold ceiling; it had not been applied anywhere else.

### 23.2 The lie the clamp was written to prevent

`Session.attempt()` carried a comment saying it stopped "a hinted attempt being recorded as unaided — the one lie that makes a gate meaningless." It clamped the reported rung **downward only**. A learner could take rung-5 co-completion and report rung 0, and the attempt counted toward the three consecutive *unaided* successes a gate requires.

Worse, the suite asserted the behaviour was correct. A test named *"a verification run cannot be talked into counting a hinted success"* asserted that a reported rung 3 on a hint-free task is silently recorded as rung 0 — which is precisely counting it as unaided. Help served is now a **floor** as well as the ceiling being a cap, and both discrepancies are audited rather than silently corrected.

### 23.3 Roughly twenty assertions that could not fail

`assert livery('welders')[0] == livery('welders')[0]`. An affect-export check whose fixture contained no affect. A NaN guard reading `!isFinite(x) && !isNaN(x)`, which for NaN is `true && false`. A `||` escape hatch that let any working-set member satisfy a prerequisite check. A bare `catch` in the very test written to prove the brand lint can fail — so a lint with a syntax error passed it.

And the sharpest one: `pack/verify.mjs` announced *"every one of 11,000,000 module indices is reached exactly once."* For the 11,000 library modules it assigned `back = i` before comparing `back !== i`, so a collision was unrepresentable — and the ID sampling stride (every 100,003rd index) never once landed in the library block, whose last multiple falls at 10,900,327. **The headline was proved for 10,989,000 and assumed for the rest.** A sampling stride has to be checked against the population it samples.

### 23.4 Colour cannot hold 111 categories

`livery()` hashed each hall's slug into 360 hue buckets and the brand suite asserted distinctness over a hand-picked ten. Over the real roster it produced **94 distinct hues for 111 halls**, with three-way ties. The first fix enforced a 12-degree separation, which caps at 30 slots and collapsed to 21 colours; relaxing the separation to fit would have produced 111 hues three degrees apart — distinct to a `Set`, identical to a reader.

So the encoding changed instead of the tolerance. **Hue carries the eight districts; identity is carried by a unique three-letter code.** Use the channel that fits the cardinality rather than overloading one that cannot take it. The two-letter code it replaces gave 72 distinct codes for 111 halls and drew its letters from the slug, so `window-glazing` printed **WI** on a marker reading ARCHITECTURAL GLAZIERS.

### 23.5 The general finding

Every defect in §23.1 and §23.3 shares one property: **the test suite and the implementation were written by the same mind on the same day, so they agreed about which paths existed.** Simulation, soak and fuzz all probe the paths the author thought of — harder, longer, with nastier inputs, but the same paths. What found these was a reader who assumed there were bugs and went looking for the branch nobody had exercised.

That is a class no harness in this bundle could have caught, and it is now the argument for the review itself being part of the process rather than a one-off.

---

## 24. Texture and environment packages

The interiors gave every hall a room programme. A room is not a place until it has surfaces and conditions, and both are derivable from the same source the rooms came from — the trade's own words — rather than chosen for looks.

### 24.1 A finish exists because something requires it

Twenty-two surfaces, each carrying renderer-ready parameters (base colour, roughness, metalness, a procedural pattern, and the real-world size of one tile in metres) **and the reason it is specified**. Selection runs most-specific-first: the trade's hazard, then the room's function, then nothing — and the record says which rule placed it.

A welding bay floor is a bare non-combustible slab because the trade throws sparks and nothing underfoot may carry flame. A cleanroom floor is welded sheet vinyl because particulates collect in joints. A smelter stands on a firebrick hearth because it will be spilled on. None of those is a preference.

**A hazard is only recorded as hazard-driven when it changed something.** For contaminant trades the induction room's hazard specification turned out identical to its function default — an induction room is already wipe-clean — so the record was claiming a reason that did no work. It now reads as the function choice the hazard happens to confirm, which is what actually happened.

### 24.2 Conditions, including the answer "none"

Per room: maintained illuminance, air changes per hour, the noise level the room is designed *around*, a temperature band, a hazard class and the PPE that class implies. Eighteen hazard classes are in use across the network — hot work, molten metal, ionising radiation, explosives, flammable atmosphere, thermal event, suspended load, work at height, confined space, live electrical, stored energy, mobile plant, rotating machinery, immersion, particulate, contaminant, noise.

Where two hazards meet, **the more demanding value wins on every axis**, so a second hazard can never cancel the first. That property is asserted directly rather than inferred from the code.

The first pass left 65% of halls with no hazard at all, which was a gap rather than a finding: most of those trades name a hazard plainly in their own focus line and the table simply lacked the vocabulary. After extending it from their own words, 31 halls remain — and those now say **"no acute physical hazard"** explicitly. Bench, design and coordination trades genuinely have none in their practice bay, and saying so is more useful than a blank field a reader has to interpret.

### 24.3 What these numbers are not

They are **general good practice, not a code reference.** No figure here is read from any jurisdiction's standard, no surface names a product, brand, fire rating or specification number, and the suite asserts that absence rather than trusting it. They carry the same unverified label as the rest of the curriculum, and a real deployment replaces them with the local standard.

They are also not a survey. No address, site visit or building record exists for any hall (§23 of the interiors work), so a plan describes what the trade requires, not what any building contains.

### 24.4 One declaration, four consumers

The packages export to `pack/environment/` as renderer-ready JSON, so the campus plan's 2D schedule and any 3D walkable interior read the *same* values. This is the fifth time this project has resolved a problem the same way — the console source list, the product name, the network figures, the hall livery, and now the finishes. The pattern is settled: **when two things must agree, do not write the rule twice and test that they match; write it once and let both read it.**

The page pays for this too. Inlining each room's finishes and conditions produced 1.36MB for data that never varies between halls sharing a room function and a hazard; interning the repeated blocks into a shared table brought it to 459KB with no value changed.

---

## 25. Durability — the launch blocker the security doc named

`SECURITY.md` had carried the sentence for four versions: *an audit log that does not survive a restart is not an audit log.* Nothing in the stack persisted. Every learner profile, every gate award and the entire compliance record lived in a `Map` and vanished with the process.

Worse, the audit log **discarded its own history under load**. On reaching its limit it dropped the oldest entry and incremented a counter. For a compliance record that is not a limit, it is data loss with a number beside it.

### 25.1 A gate award is a fact about a person

ACP-06 already treats certification as an *awarded event* rather than a recomputed query (v1.1 defect 5, where asking whether a gate passed could silently revoke it). That argument only holds if the award outlives the process that made it — otherwise the system is recomputing after all, just from an empty slate.

`store/` is an append-only journal with snapshots: newline-delimited records, an explicit `fsync` at every commit boundary, and a snapshot written to a temp file and renamed so an interrupted snapshot is never a half-snapshot. Certification, profiles, enrolments and the audit log all survive a restart, and the suite proves it by running a session, discarding everything but the directory, and reopening.

Three properties are asserted rather than assumed:

- **Idempotence.** Re-awarding a held gate is a no-op, so a retried request after a timeout cannot mint a second award date for one certification.
- **Torn tails are dropped; holes are errors.** A crash mid-append leaves a partial last line, which is expected and discarded. Corruption in the *middle* of the journal raises rather than skipping — a gap in an audit record must not be papered over.
- **A corrupt snapshot costs time, never correctness.** It is ignored and the journal replays in full, because the journal alone is sufficient by construction.

### 25.2 Erasure writes a tombstone, and the ordering matters

The privacy pack promises that erasure breaks the identity link. With nothing persisted, that promise had never been tested against anything.

Erasure now appends a tombstone; it does **not** rewrite the journal. Editing history to satisfy a privacy request would break the append-only property the audit record depends on — and a log you can edit for a good reason is a log you can edit for any reason. On replay, **erasures are applied last regardless of their position in the journal**, so a tombstone written before a replayed enrolment still wins. Without that rule a rebuild silently resurrects a link somebody asked to have broken. An erased pseudonym also cannot be re-enrolled, which would undo the erasure quietly.

### 25.3 Two defects introduced while fixing this, and caught

Writing the durability layer produced two of its own, both found by tests rather than by reading:

1. **The restarted audit log restarted its sequence at zero**, so the recovered history read `0,1,…,481,0,1,2` and two different events shared a sequence number. This is the *same defect* the counter was introduced to fix — a `seq` that stops being unique — reappearing one level up, across processes instead of across a truncation. A sequence is only a sequence if it is monotonic over the whole record.
2. **The console bundler's assertion tested the wrong thing.** It asserted `'import ' not in bundle`, which fires on the word "import" appearing in a *comment* — a sentence explaining why a static import had been avoided broke the build. It now matches module syntax at a line start. An assertion has to test the thing it names, or it fails for reasons unrelated to what it guards.

### 25.4 Injected, not imported

The console inlines the whole control plane and runs it in a browser, where `node:fs` does not exist. A static import of the store pack from `session.mjs` would have made the control plane unloadable there — the page would have kept working until the moment that code path ran.

So the store is **injected at the edge**, and `bus/session.mjs` does not import it at all. Durability is opt-in, and the only layer that knows whether it has a filesystem is the one that does. A session without a store behaves exactly as before and reports `durable === false` rather than implying otherwise.

### 25.5 What this is not

It is not a database, and `SECURITY.md` now says so in the place the old blocker used to sit. No replication, no concurrent writers, no point-in-time restore, no tested backup schedule, no encryption at rest. A real deployment puts a database underneath and keeps this contract — the contract is the part worth having, because it is what the rest of the stack was written against.
