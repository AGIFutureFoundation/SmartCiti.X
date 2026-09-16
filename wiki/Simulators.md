# The simulators

9 operable training machines live inside the
[3D environment](Campus-Map.md): open a bound hall and press **▶** (a hall
bound to more than one machine offers the choice). The
physics are schematic — built for practising control discipline (smooth
inputs, swing management, ordered procedure) — and the scoring contract is
the same shape the mentor fabric enforces: **deterministic**. Every rubric
axis is computed from measured state; nothing narrative can change a score.

## The scripted reference operator

Every seat can also be driven by a **scripted reference operator**: a
hand-written, deterministic control policy in the page — a function of the
seat's own live `gauges()` readout (the same numbers the dash shows), the
scenario's params, the seat's declared yard `layout` and a level — with no
model behind it and no network reached, exactly as the [advisors](Advisors.md)
are scripted. Its inputs land in the same key state a keyboard fills and the
same Space verb, so the seat cannot tell the two apart. In the seat, the HUD
offers a level and a **watch it drive** button; the Operator advisor quotes
the procedure; the [records panel](Training-Data.md) sweeps every seat and
yard headlessly at a fixed step and keeps the runs as SCRIPTED episodes. A
scripted run is the operator's own record — it never credits the learner.

| Level | What it is |
|---|---|
| `optimal` | the reference: the written procedure with its checks and waits intact - passes every pass-gated rubric axis on every regional scenario, proven by the build |
| `novice` | the same procedure with seeded, deterministic slips - a mis-selected rack, a wrong signal, a wandering standoff, a low carry - so the sweep also yields labelled sub-optimal episodes |
| `hurried` | the same procedure with its waits and checks removed - no settle before release, no containment before the trigger, no chart read before the hook - the failure a rushed shift actually produces |

**Provenance word:** SCRIPTED: a demonstration of a hand-written, deterministic control policy on a schematic single-machine simulator - a function of the seat's own gauges, the scenario's params and a level, no model behind it and no network reached. Not a learned policy, not real equipment, and not a claim about any physical robot; its runs are its own record, never credited to the learner watching it.

## Tower Crane Lift (machine)

Pick the load from the supply pad, carry it over the stacks and set it inside the target ring — swing under control the whole way.

Trains at: **Crane Operators**, **Riggers & Signalpersons**, **Steel Erectors**, **Port Crane Technicians**, **Ironworkers**, **Metal Deck Installers**, **Tank Erectors**, **Piling Crews** — each run exercises that hall's
`machines.applied` skill.

| Control | Action |
|---|---|
| `A / D` | slew the jib |
| `W / S` | trolley out / in |
| `Q / E` | hoist up / down |
| `Space` | hook / release the load |

| Rubric axis | Measured | Pass |
|---|---|---|
| placement | distance from target centre at release (m) | `<= 1.2` |
| swing | peak load swing during carry (m) | `<= 2.0` |
| strikes | load or hook contacts with the stacks | `== 0` |
| time | seconds from hook to release | `informational` |

**Cockpit.** A live dash of 6 gauges — `Slew °`, `Radius m`, `Hook m`, `Swing m` (warns at 1.6), `Strikes` (warns at 1), `T s` — with the
warn thresholds drawn from this registry, not hard-coded in the page.
View modes: `orbit` / `cab`. Audio is a
`hoist-motor` engine plus `overswing-chirp`, `strike-thud`, `result-chime` —
synthesized in-page (WebAudio); no recordings shipped. Haptic cues (strike, finish) fire on
gamepad rumble and the vibration API where the platform offers them.

**Pre-shift walkaround.** Five clipboards ring the machine —
*Hoist rope and hook*, *Slew ring and bolts*, *Counterweight*, *Limit switches*, *Base and ballast* — a habit-builder
the registry declares **not a gate**: nothing locks behind it and marking
it changes no score.

**Regional scenarios.** The campus you train at picks the yard — the
environment varies, the rubric never does:

| Region | Scenario | The yard |
|---|---|---|
| Treasure Island Campus | **Bay high-steel lift** | Tower steel over the bay on a still morning - a clean yard, nothing between you and your own swing. |
| Oakland Waterfront Campus | **Oakland terminal lift** | Container stacks crowd the swing path - carry high and slow, the corridors are tight. |
| Crescent Works Campus | **Crescent wharf lift** | A steady river breeze leans on the load the whole carry - trim your swing against it. |

**Scripted reference operator.** At `optimal` it passes
**placement**, **swing**, **strikes** on all three
yards. Its procedure, the step list the page's policy is written around:

1. slew and trolley the hook over the supply pad and lower it under 4.5 m
2. hook the load
3. hoist to carry height - clear of the tallest stack - before anything moves sideways
4. trolley in to a short radius, moving only while the swing gauge is low
5. slew round to the target bearing, moving only while the swing gauge is low
6. trolley out to the target radius, moving only while the swing gauge is low
7. hold everything until the swing dies away
8. lower the load to the ground
9. release once the swing is still
## Excavator Trench Cut (machine)

Cut the marked trench to grade cell by cell and land every bucket in the spoil zone — the flagged cell holds a live utility at half depth, so it stops shallow.

Trains at: **Operating Engineers**, **Shoring & Underpinning**, **Laborers**, **Demolition Workers** — each run exercises that hall's
`machines.applied` skill.

| Control | Action |
|---|---|
| `A / D` | slew the house |
| `W / S` | reach out / in |
| `Q / E` | bucket up / down |
| `Space` | dig / dump the bucket |

| Rubric axis | Measured | Pass |
|---|---|---|
| grade | trench cells finished at their marked depth | `== all` |
| utility | strikes on the flagged utility | `== 0` |
| spoil | buckets landed inside the spoil zone | `== all` |
| time | seconds first dig to last dump | `informational` |

**Cockpit.** A live dash of 7 gauges — `Slew °`, `Reach m`, `Bucket m`, `Grade`, `Spoil`, `Utility` (warns at 1), `T s` — with the
warn thresholds drawn from this registry, not hard-coded in the page.
View modes: `orbit` / `cab`. Audio is a
`diesel` engine plus `utility-alarm`, `dump-thud`, `result-chime` —
synthesized in-page (WebAudio); no recordings shipped. Haptic cues (utility, dump, finish) fire on
gamepad rumble and the vibration API where the platform offers them.

**Pre-shift walkaround.** Five clipboards ring the machine —
*Tracks and rollers*, *Bucket teeth and pins*, *Boom hydraulics*, *Slew brake*, *The trench edge* — a habit-builder
the registry declares **not a gate**: nothing locks behind it and marking
it changes no score.

**Regional scenarios.** The campus you train at picks the yard — the
environment varies, the rubric never does:

| Region | Scenario | The yard |
|---|---|---|
| Treasure Island Campus | **Seismic retrofit cut** | Deep footing cells beside a braced frame - long careful digs, one flagged conduit crossing. |
| Oakland Waterfront Campus | **Old-fill utility cut** | Waterfront fill ground, crowded with legacy lines - two flagged cells stop shallow. |
| Crescent Works Campus | **Below-sea trench** | High water table, one live utility at half depth - the flagged cell stops shallow. |

**Scripted reference operator.** At `optimal` it passes
**grade**, **utility**, **spoil** on all three
yards. Its procedure, the step list the page's policy is written around:

1. swing to the next cell short of grade, reach out to it and drop the bucket under 0.6 m
2. take one bite - the marked depth divided by the bite is the count, and a flagged cell gets no more
3. swing the full bucket to the spoil zone and reach to its centre
4. dump inside the zone, then back to the trench until every cell is at grade
## Forklift Yard Run (driving)

Thread the cone lane, pick the pallet square on the forks, and set it down inside the dock bay — without disturbing a cone.

Trains at: **Teamsters**, **Heavy Equipment Technicians**, **Operating Engineers**, **Laborers**, **Marine Terminal Operators** — each run exercises that hall's
`machines.applied` skill.

| Control | Action |
|---|---|
| `W / S` | drive / reverse |
| `A / D` | steer |
| `Space` | lift / set the pallet |

| Rubric axis | Measured | Pass |
|---|---|---|
| gates | cone gates taken in order | `== all` |
| cones | cones struck | `== 0` |
| docking | pallet inside the dock bay at set-down | `required` |
| time | seconds start to set-down | `informational` |

**Cockpit.** A live dash of 9 gauges — `Speed km/h`, `Steer °`, `Heading °`, `X m`, `Z m`, `Load`, `Gates`, `Cones` (warns at 1), `T s` — with the
warn thresholds drawn from this registry, not hard-coded in the page.
View modes: `chase` / `driver`. Audio is a
`diesel` engine plus `reverse-beeper`, `cone-thud`, `result-chime` —
synthesized in-page (WebAudio); no recordings shipped. Haptic cues (cone, gate, finish) fire on
gamepad rumble and the vibration API where the platform offers them.

**Pre-shift walkaround.** Five clipboards ring the machine —
*Tires and wheel nuts*, *Fork heels and locks*, *Mast chains*, *Horn and beeper*, *Seatbelt and overhead guard* — a habit-builder
the registry declares **not a gate**: nothing locks behind it and marking
it changes no score.

**Regional scenarios.** The campus you train at picks the yard — the
environment varies, the rubric never does:

| Region | Scenario | The yard |
|---|---|---|
| Treasure Island Campus | **Island yard run** | The training yard lane - four gates and a full-width dock bay to land the pallet in. |
| Oakland Waterfront Campus | **Terminal container lane** | A fifth gate threads the container rows - longer lane, same clean-run law. |
| Crescent Works Campus | **Wharf dock set** | The wharf dock is narrow - four gates, then a set-down with little room to be wrong. |

**Scripted reference operator.** At `optimal` it passes
**gates**, **cones**, **docking** on all three
yards. Its procedure, the step list the page's policy is written around:

1. steer for the centre of the next untaken gate, slowing into every turn
2. roll up to the pallet on the centre line and brake to a walk
3. lift once the forks are on the pallet and the truck has all but stopped
4. carry up the clear lane outside the cone rows, never back through the gates
5. square up on the dock from the lane and set the pallet down inside the bay
## Weld Bead Run (process)

Strike the arc and run one clean bead down the marked seam — hold the gap inside the band and keep the torch travelling; linger on a segment and the plate burns through.

Trains at: **Welding Trades**, **Boilermakers**, **Shipfitters**, **Structural Fabricators**, **Pipeline Trades**, **Marine Pipefitters**, **Tank Erectors** — each run exercises that hall's
`machines.applied` skill.

| Control | Action |
|---|---|
| `W / S` | travel the torch along the seam |
| `Q / E` | raise / lower the torch (arc gap) |
| `Space` | strike / break the arc |

| Rubric axis | Measured | Pass |
|---|---|---|
| fusion | seam segments fused end to end | `== all` |
| band | share of fused segments laid with the gap inside the band (%) | `>= 90` |
| burns | burn-throughs from lingering heat | `== 0` |
| time | seconds first strike to last fuse | `informational` |

**Cockpit.** A live dash of 6 gauges — `Gap mm` (warns at 5.2), `Heat %` (warns at 85), `Seam`, `Band %`, `Burns` (warns at 1), `T s` — with the
warn thresholds drawn from this registry, not hard-coded in the page.
View modes: `orbit` / `visor`. Audio is a
`arc` engine plus `burn-alarm`, `arc-pop`, `result-chime` —
synthesized in-page (WebAudio); no recordings shipped. Haptic cues (burn, finish) fire on
gamepad rumble and the vibration API where the platform offers them.

**Pre-shift walkaround.** Five clipboards ring the machine —
*Leads and clamps*, *Gas and regulator*, *Welding screens*, *Fume extraction*, *Fire watch kit* — a habit-builder
the registry declares **not a gate**: nothing locks behind it and marking
it changes no score.

**Regional scenarios.** The campus you train at picks the yard — the
environment varies, the rubric never does:

| Region | Scenario | The yard |
|---|---|---|
| Treasure Island Campus | **Deck plate seam** | A flat deck seam on the fabrication floor - the forgiving band to learn the rhythm in. |
| Oakland Waterfront Campus | **Pipe flange bead** | A longer run at a tighter gap - the plant inspector reads every millimetre of it. |
| Crescent Works Campus | **Tank shell seam** | Storage-tank shell plate in Gulf humidity - a slightly higher band, the same clean-bead law. |

**Scripted reference operator.** At `optimal` it passes
**fusion**, **band**, **burns** on all three
yards. Its procedure, the step list the page's policy is written around:

1. set the arc gap to the middle of the scenario's band before striking
2. strike the arc at the start of the seam
3. travel steadily to the end of the seam without pausing - every segment fuses in band and none lingers to a burn
## Scaffold Bay Build (process)

Erect one bay in the legal order — sills, frames, braces, planks, then guardrails. The rack refuses a part whose stage has not come, every refusal counts, and the bay is not done until the rails are on.

Trains at: **Scaffold Erectors**, **Carpenters**, **Laborers**, **Bricklayers & Allied Craft**, **Painters & Allied Trades**, **Glaziers**, **Roofers & Waterproofers**, **Cement Masons**, **Heat & Frost Insulators**, **Plasterers**, **Below-Grade Waterproofers**, **Firestop Installers**, **Rainscreen Cladding Fitters**, **Masonry Restoration**, **Curtain Wall Erectors**, **Architectural Glaziers**, **Lathers & Metal Framers**, **Stone Carvers**, **Refractory Masons** — each run exercises that hall's
`machines.applied` skill.

| Control | Action |
|---|---|
| `A / D` | choose the part rack |
| `Space` | place the next part |
| `R` | jump the rack to the legal stage |

| Rubric axis | Measured | Pass |
|---|---|---|
| sequence | placements refused for coming before their stage | `== 0` |
| complete | parts of the bay placed, rails last | `== all` |
| time | seconds first sill to last rail | `informational` |

**Cockpit.** A live dash of 5 gauges — `Rack`, `Stage`, `Parts`, `Refused` (warns at 1), `T s` — with the
warn thresholds drawn from this registry, not hard-coded in the page.
View modes: `orbit` / `deck`. Audio is a
`site` engine plus `refusal-buzz`, `lock-click`, `result-chime` —
synthesized in-page (WebAudio); no recordings shipped. Haptic cues (refusal, finish) fire on
gamepad rumble and the vibration API where the platform offers them.

**Pre-shift walkaround.** Five clipboards ring the machine —
*Sills and bearing*, *Frames plumb and level*, *Brace pins*, *Plank condition*, *The scaffold tag* — a habit-builder
the registry declares **not a gate**: nothing locks behind it and marking
it changes no score.

**Regional scenarios.** The campus you train at picks the yard — the
environment varies, the rubric never does:

| Region | Scenario | The yard |
|---|---|---|
| Treasure Island Campus | **Yard training bay** | One lift in the training yard - three planks, two rails, the order to learn by heart. |
| Oakland Waterfront Campus | **Plant maintenance bay** | A wider bay against the plant wall - four planks to deck before anyone stands the lift. |
| Crescent Works Campus | **Storm-hardening bay** | Hurricane-season work - a third rail goes on, and the same legal order holds in the wind. |

**Scripted reference operator.** At `optimal` it passes
**sequence**, **complete** on all three
yards. Its procedure, the step list the page's policy is written around:

1. jump the rack to the stage the bay is legally at - the dash names it
2. place the next part, and repeat until the rails are on
## Rigging Signal Call (process)

You are the signalperson: the lift card calls the moves, and the crane follows YOUR hands. Give each called signal in order — a wrong signal counts against you and the crane holds — and finish the lift with the stop signal.

Trains at: **Riggers & Signalpersons**, **Crane Operators**, **Steel Erectors**, **Port Crane Technicians**, **Millwrights**, **Ironworkers**, **Metal Deck Installers**, **Tank Erectors**, **Piling Crews** — each run exercises that hall's
`machines.applied` skill.

| Control | Action |
|---|---|
| `Q / E` | signal hoist up / hoist down |
| `A / D` | signal swing left / swing right |
| `W / S` | signal trolley out / trolley in |
| `Space` | signal STOP |

| Rubric axis | Measured | Pass |
|---|---|---|
| calls | called signals given, in order | `== all` |
| wrong | signals given out of turn | `== 0` |
| time | seconds first signal to stop | `informational` |

**Cockpit.** A live dash of 5 gauges — `Step`, `Called`, `Given`, `Wrong` (warns at 1), `T s` — with the
warn thresholds drawn from this registry, not hard-coded in the page.
View modes: `orbit` / `signal`. Audio is a
`hoist` engine plus `signal-whistle`, `wrong-buzz`, `result-chime` —
synthesized in-page (WebAudio); no recordings shipped. Haptic cues (wrong, finish) fire on
gamepad rumble and the vibration API where the platform offers them.

**Pre-shift walkaround.** Five clipboards ring the machine —
*Line of sight*, *Radio and whistle*, *Slings and shackles*, *The load path*, *Exclusion zone* — a habit-builder
the registry declares **not a gate**: nothing locks behind it and marking
it changes no score.

**Regional scenarios.** The campus you train at picks the yard — the
environment varies, the rubric never does:

| Region | Scenario | The yard |
|---|---|---|
| Treasure Island Campus | **First lift card** | The training card: five calls, one direction change, the stop to finish - learn the hands. |
| Oakland Waterfront Campus | **Blind terminal pick** | The operator cannot see this load - six calls thread it out of the container shadow. |
| Crescent Works Campus | **River-wind card** | The river breeze wants the load moving - six calls with two swings hold the line to the set. |

**Scripted reference operator.** At `optimal` it passes
**calls**, **wrong** on all three
yards. Its procedure, the step list the page's policy is written around:

1. read the called signal off the lift card - the dash shows it
2. give exactly that signal, wait for the crane to finish moving, and give the next; STOP ends the card
## Load Chart Judgment (process)

Work the pick list against the chart on the board: at each radius the crane has one honest number. Hook the picks the chart allows and refuse the ones it does not — an overweight pick accepted is the failure that matters.

Trains at: **Crane Operators**, **Riggers & Signalpersons**, **Port Crane Technicians**, **Heavy Equipment Technicians**, **Operating Engineers**, **Ironworkers**, **Tank Erectors** — each run exercises that hall's
`machines.applied` skill.

| Control | Action |
|---|---|
| `Space` | accept the pick - hook it |
| `X` | refuse the pick - over the chart |
| `Q / E` | walk the chart rows |

| Rubric axis | Measured | Pass |
|---|---|---|
| judgments | picks judged with the chart | `== all` |
| overloads | overweight picks accepted | `== 0` |
| time | seconds first judgment to last | `informational` |

**Cockpit.** A live dash of 6 gauges — `Pick`, `Load t`, `Radius m`, `Chart t`, `Errors` (warns at 1), `T s` — with the
warn thresholds drawn from this registry, not hard-coded in the page.
View modes: `orbit` / `chart`. Audio is a
`hoist` engine plus `overload-alarm`, `hook-click`, `result-chime` —
synthesized in-page (WebAudio); no recordings shipped. Haptic cues (overload, finish) fire on
gamepad rumble and the vibration API where the platform offers them.

**Pre-shift walkaround.** Five clipboards ring the machine —
*The chart itself*, *Radius markers*, *Ground bearing*, *Wind check*, *Hook block* — a habit-builder
the registry declares **not a gate**: nothing locks behind it and marking
it changes no score.

**Regional scenarios.** The campus you train at picks the yard — the
environment varies, the rubric never does:

| Region | Scenario | The yard |
|---|---|---|
| Treasure Island Campus | **Yard pick list** | Five picks off the training pad - one of them is over the chart, and the chart wins. |
| Oakland Waterfront Campus | **Terminal heavy list** | Six terminal picks, two of them over - the foreman will push, the chart will not. |
| Crescent Works Campus | **Barge transfer list** | Five barge picks with two over the chart - the river will not forgive the one you talk into. |

**Scripted reference operator.** At `optimal` it passes
**judgments**, **overloads** on all three
yards. Its procedure, the step list the page's policy is written around:

1. read the pick weight and radius against the chart line at that radius
2. hook the pick if its weight is inside the chart, refuse it if it is over
## Pressure Washer Surface Clean (process)

Strip the fouling off the marked test panel to a clean finish — sweep the wand cell by cell and hold your standoff; crowd the surface and linger and the substrate gouges. Set the containment berm before you ever pull the trigger, not after.

Trains at: **Painters & Allied Trades**, **Laborers**, **Hazmat & Environmental** — each run exercises that hall's
`machines.applied` skill.

| Control | Action |
|---|---|
| `A / D` | sweep the wand left / right across the panel |
| `W / S` | sweep the wand up / down across the panel |
| `Q / E` | stand off farther / move closer to the surface |
| `Space` | pull / release the spray trigger |
| `C` | deploy the containment berm / drain cover |

| Rubric axis | Measured | Pass |
|---|---|---|
| coverage | share of the panel surface cleaned (%) | `>= 95` |
| damage | substrate gouges from spraying too close or lingering too long | `== 0` |
| containment | containment berm or drain cover deployed before the first spray | `required` |
| time | seconds first spray to last clean cell | `informational` |

**Cockpit.** A live dash of 7 gauges — `Across m`, `Up m`, `Standoff m`, `Clean %`, `Damage` (warns at 1), `Contain`, `T s` — with the
warn thresholds drawn from this registry, not hard-coded in the page.
View modes: `orbit` / `wand`. Audio is a
`pump` engine plus `spray-hiss`, `breach-alarm`, `result-chime` —
synthesized in-page (WebAudio); no recordings shipped. Haptic cues (damage, breach, finish) fire on
gamepad rumble and the vibration API where the platform offers them.

**Pre-shift walkaround.** Five clipboards ring the machine —
*Eye and face protection*, *GFCI-protected power source*, *Wand trigger lock*, *Hose condition*, *Work-area containment* — a habit-builder
the registry declares **not a gate**: nothing locks behind it and marking
it changes no score.

**Regional scenarios.** The campus you train at picks the yard — the
environment varies, the rubric never does:

| Region | Scenario | The yard |
|---|---|---|
| Treasure Island Campus | **Ferry terminal seawall** | Graffiti on the ferry terminal seawall panel - a forgiving concrete face to learn the sweep on. |
| Oakland Waterfront Campus | **Terminal bulkhead fouling** | Rust bloom on a steel bulkhead panel at the marine terminal - a wider panel, the same clean-cell law. |
| Crescent Works Campus | **Levee floodwall mildew** | Gulf humidity grows mildew fast on the floodwall panel - a taller face, containment matters more here. |

**Scripted reference operator.** At `optimal` it passes
**coverage**, **damage**, **containment** on all three
yards. Its procedure, the step list the page's policy is written around:

1. deploy the containment berm before the trigger is ever pulled
2. set the standoff to the middle of the effective window, well clear of the damage distance
3. pull the trigger
4. sweep the panel cell by cell in rows, dwelling on each just past the clean time and never lingering
## Airless Paint Sprayer Finish (process)

Lay one even finish coat across the marked panel inside the masked line — hold your standoff and travel steady; crowd the surface or linger and the coat runs, rush a cell and it stays a holiday, and drift past the mask is overspray either way.

Trains at: **Painters & Allied Trades**, **Laborers** — each run exercises that hall's
`machines.applied` skill.

| Control | Action |
|---|---|
| `A / D` | sweep the gun left / right across the panel |
| `W / S` | sweep the gun up / down across the panel |
| `Q / E` | stand off farther / move closer to the surface |
| `Space` | pull / release the spray trigger |

| Rubric axis | Measured | Pass |
|---|---|---|
| coverage | share of the panel evenly coated (%) | `>= 95` |
| runs | drips from spraying too close or too slow | `== 0` |
| holidays | missed spots left uncoated | `== 0` |
| overspray | spray drift past the masked boundary | `== 0` |
| time | seconds first spray to last coated cell | `informational` |

**Cockpit.** A live dash of 8 gauges — `Across m`, `Up m`, `Standoff m`, `Coat %`, `Runs` (warns at 1), `Holidays` (warns at 1), `Overspray` (warns at 1), `T s` — with the
warn thresholds drawn from this registry, not hard-coded in the page.
View modes: `orbit` / `spray`. Audio is a
`pump` engine plus `overspray-alarm`, `run-buzz`, `result-chime` —
synthesized in-page (WebAudio); no recordings shipped. Haptic cues (run, overspray, finish) fire on
gamepad rumble and the vibration API where the platform offers them.

**Pre-shift walkaround.** Five clipboards ring the machine —
*Respirator and ventilation*, *Spray-tip guard*, *Pressure-relief procedure*, *Drop-cloth and masking*, *Fire and ignition sources* — a habit-builder
the registry declares **not a gate**: nothing locks behind it and marking
it changes no score.

**Regional scenarios.** The campus you train at picks the yard — the
environment varies, the rubric never does:

| Region | Scenario | The yard |
|---|---|---|
| Treasure Island Campus | **Ferry terminal finish coat** | A fresh finish coat on the terminal exterior wall - the forgiving panel to learn the pass rhythm on. |
| Oakland Waterfront Campus | **Dockside warehouse finish** | A wider warehouse wall panel at the terminal - more travel, the same even-coat law. |
| Crescent Works Campus | **Shotgun house finish coat** | A taller shotgun-house exterior wall panel - humidity punishes a slow pass, hold the rhythm. |

**Scripted reference operator.** At `optimal` it passes
**coverage**, **runs**, **holidays**, **overspray** on all three
yards. Its procedure, the step list the page's policy is written around:

1. set the standoff to the middle of the effective window, well clear of the run distance
2. pull the trigger inside the masked line
3. sweep the panel cell by cell in rows, dwelling on each just past the coat time, turning inside the mask

## What a simulator run is not

schematic physics for practising control discipline - smooth inputs, swing management, ordered procedure. Not equipment certification; no seat time here counts toward one, and the assessment gates still demand unaided verification runs.

**And the walkaround:** a habit-builder, not a gate: no seat is locked behind the walkaround, completing it changes no score, and it is not an equipment inspection record.

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
