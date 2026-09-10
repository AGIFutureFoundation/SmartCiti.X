# The flipped classroom

How the Academy's machinery becomes a school program: **explore at home, build and practice in class, verify unaided; the teacher circulates instead of lecturing.**
Every stage below names the subsystem that already implements it, and
`schools/test.mjs` proves those references against the packs that own
them — a program that overclaims fails its build.

| Stage | What happens | Implemented by | The gamified layer |
|---|---|---|---|
| **Explore at home** | the lesson positions of the module pack, sequenced by the skill graph with the ZPD difficulty dial, in any of the eight shipped languages | `pack/ (modules, skill graph) + i18n/` | module layers and pipeline states are the map the learner explores; progress is visible per hall |
| **Build in class** | station bench work - checklists, doctrine lines and machine-gradable quizzes at the hall stations, with the teacher moving bench to bench | `stations/ (25 recovered yard stations)` | station beacons in the 3D hall; completion marks accumulate on the hall roster |
| **Practice on the floor** | simulator seat time with the regional scenario of the campus - live dash, synthesized sound, deterministic rubric; results and best times persist device-locally | `sims/ (3 simulators, regional scenarios)` | pass/retry chips, best-time records, cockpit views |
| **Verify unaided** | assessment gates certify only unaided work; no home exploration, class bench or simulator hour substitutes for the unaided verification run | `the assessment-gate protocol (ACP-04) and the sims registry honesty note` | nothing - the gate is deliberately ungamified, and the model says so |

## Grade bands

Aligned with the Cognition.X band vocabulary (Explorer / Builder /
Practitioner / Lead), so the two platforms' materials sit in one
classroom. Explorer (K–5) is deliberately awareness-only.

| Grades | Band | Academy tier | The offer |
|---|---|---|---|
| K-5 | Explorer | — | awareness only: the campus maps, the walkable halls and the city layers; no machine seats and no station quizzes |
| 6-8 | Builder | fundamentals | home modules at fundamentals tier plus class station work |
| 9-10 | Practitioner | applied | applied-tier modules, stations, and simulator floor time with the regional scenario |
| 11-12 | Lead | mastery | mastery-tier modules, full flipped loop, and the unaided verification gate |

## School districts, honestly

The names below are **public-record identities only** — no address,
enrolment figure or policy is recorded — and every record carries the
same status, asserted by the suite:

| District | City | Nearest campus | Status |
|---|---|---|---|
| San Francisco Unified School District | San Francisco | Treasure Island Campus | proposed partner - no district has reviewed or agreed to this program, and no agreement exists |
| Oakland Unified School District | Oakland | Oakland Waterfront Campus | proposed partner - no district has reviewed or agreed to this program, and no agreement exists |
| NOLA Public Schools | New Orleans | Crescent Works Campus | proposed partner - no district has reviewed or agreed to this program, and no agreement exists |
| Jefferson Parish Schools | Jefferson Parish | Crescent Works Campus | proposed partner - no district has reviewed or agreed to this program, and no agreement exists |

## Flipped units live today

One unit per simulator-bound hall — the halls where the full loop can run
now. The floor stage runs the **regional scenario** of whichever campus
the class trains at ([Simulators](Simulators.md)).

| Hall | Floor sims | Class stations | The gate |
|---|---|---|---|
| **Crane Operators** | `crane-lift` | — | unaided verification run (ACP-04); no sim hour counts |
| **Demolition Workers** | `excavator-trench` | — | unaided verification run (ACP-04); no sim hour counts |
| **Heavy Equipment Technicians** | `forklift-run` | — | unaided verification run (ACP-04); no sim hour counts |
| **Laborers** | `excavator-trench`, `forklift-run` | — | unaided verification run (ACP-04); no sim hour counts |
| **Marine Terminal Operators** | `forklift-run` | — | unaided verification run (ACP-04); no sim hour counts |
| **Operating Engineers** | `excavator-trench`, `forklift-run` | — | unaided verification run (ACP-04); no sim hour counts |
| **Port Crane Technicians** | `crane-lift` | — | unaided verification run (ACP-04); no sim hour counts |
| **Riggers & Signalpersons** | `crane-lift` | 1 | unaided verification run (ACP-04); no sim hour counts |
| **Shoring & Underpinning** | `excavator-trench` | — | unaided verification run (ACP-04); no sim hour counts |
| **Steel Erectors** | `crane-lift` | — | unaided verification run (ACP-04); no sim hour counts |
| **Teamsters** | `forklift-run` | — | unaided verification run (ACP-04); no sim hour counts |

## What this is not

district names are public-record identities only; every record is a PROPOSED partner - no district has reviewed or agreed, and no agreement exists nothing in the school program certifies equipment operation; the assessment gates demand unaided verification and simulator hours never count toward certification

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
