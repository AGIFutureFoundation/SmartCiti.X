# Skill: run-a-training-scenario

Run one of the 6 SmartCiti.X training scenarios — for agents guiding a
human learner (or describing a run).

## Source of truth

`scenarios/<id>.json` — each scenario has an id, title, audience, strands,
tiers, stations, and 5 ordered `steps`. Each step names a `stationId`, an
`action`, and a `check` (the observable completion condition). Cite steps by
station id + action text, verbatim. `scenarios/index.html` renders the same
data with a checkable step list (progress in memory only, nothing stored).

## How a run works (in the viewer)

1. Open `scenarios/index.html?scenario=<id>` (or pick from the list).
2. Work the 5 steps in order. Tap / click / Enter on a step to check it off;
   the progress bar and "n of 5 steps complete" update. Tapping again
   unchecks it.
3. "Restart this scenario" clears the checks.
4. Steps link onward: scenarios with a TradePath zone offer a deep link
   (e.g. `/?zone=hvac`) to run the matching zone in the IWSDK Training
   Centre.

## Rules for describing a run

- Give the steps in order, with station ids. Never reorder steps: sequence
  is the training (PPE before work, consent before screening, diagnose
  before charging, clean before sterilise).
- State the simulation boundary every time you describe a completed run:
  "Simulation only — NOT certification, licensure, or clinical training."
- HVAC runs: never describe venting refrigerant as an option. EPA Section
  608 prohibits intentional venting; certification is an external exam.
- Screening runs: screening is not diagnosis. Flag, refer, and record —
  never diagnose in the field. Consent comes before screening, every time.
- Safety runs: report near-misses; do not hide them.
- Do not award badges, completion records, or credentials yourself. A
  completed scenario is practice, not a qualification, and checklist state
  is not stored anywhere.
