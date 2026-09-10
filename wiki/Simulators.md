# The simulators

3 operable training machines live inside the
[3D environment](Campus-Map.md): open a bound hall and press **▶** (a hall
bound to more than one machine offers the choice). The
physics are schematic — built for practising control discipline (smooth
inputs, swing management, ordered procedure) — and the scoring contract is
the same shape the mentor fabric enforces: **deterministic**. Every rubric
axis is computed from measured state; nothing narrative can change a score.

## Tower Crane Lift (machine)

Pick the load from the supply pad, carry it over the stacks and set it inside the target ring — swing under control the whole way.

Trains at: **Crane Operators**, **Riggers & Signalpersons**, **Steel Erectors**, **Port Crane Technicians** — each run exercises that hall's
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

**Regional scenarios.** The campus you train at picks the yard — the
environment varies, the rubric never does:

| Region | Scenario | The yard |
|---|---|---|
| Treasure Island Campus | **Bay high-steel lift** | Tower steel over the bay on a still morning - a clean yard, nothing between you and your own swing. |
| Oakland Waterfront Campus | **Oakland terminal lift** | Container stacks crowd the swing path - carry high and slow, the corridors are tight. |
| Crescent Works Campus | **Crescent wharf lift** | A steady river breeze leans on the load the whole carry - trim your swing against it. |
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

**Cockpit.** A live dash of 6 gauges — `Reach m`, `Bucket m`, `Grade`, `Spoil`, `Utility` (warns at 1), `T s` — with the
warn thresholds drawn from this registry, not hard-coded in the page.
View modes: `orbit` / `cab`. Audio is a
`diesel` engine plus `utility-alarm`, `dump-thud`, `result-chime` —
synthesized in-page (WebAudio); no recordings shipped. Haptic cues (utility, dump, finish) fire on
gamepad rumble and the vibration API where the platform offers them.

**Regional scenarios.** The campus you train at picks the yard — the
environment varies, the rubric never does:

| Region | Scenario | The yard |
|---|---|---|
| Treasure Island Campus | **Seismic retrofit cut** | Deep footing cells beside a braced frame - long careful digs, one flagged conduit crossing. |
| Oakland Waterfront Campus | **Old-fill utility cut** | Waterfront fill ground, crowded with legacy lines - two flagged cells stop shallow. |
| Crescent Works Campus | **Below-sea trench** | High water table, one live utility at half depth - the flagged cell stops shallow. |
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

**Cockpit.** A live dash of 6 gauges — `Speed km/h`, `Steer °`, `Load`, `Gates`, `Cones` (warns at 1), `T s` — with the
warn thresholds drawn from this registry, not hard-coded in the page.
View modes: `chase` / `driver`. Audio is a
`diesel` engine plus `reverse-beeper`, `cone-thud`, `result-chime` —
synthesized in-page (WebAudio); no recordings shipped. Haptic cues (cone, gate, finish) fire on
gamepad rumble and the vibration API where the platform offers them.

**Regional scenarios.** The campus you train at picks the yard — the
environment varies, the rubric never does:

| Region | Scenario | The yard |
|---|---|---|
| Treasure Island Campus | **Island yard run** | The training yard lane - four gates and a full-width dock bay to land the pallet in. |
| Oakland Waterfront Campus | **Terminal container lane** | A fifth gate threads the container rows - longer lane, same clean-run law. |
| Crescent Works Campus | **Wharf dock set** | The wharf dock is narrow - four gates, then a set-down with little room to be wrong. |

## What a simulator run is not

schematic physics for practising control discipline - smooth inputs, swing management, ordered procedure. Not equipment certification; no seat time here counts toward one, and the assessment gates still demand unaided verification runs.

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
