# Omega Swarm

SmartCiti.X : Trade Craft Academy, powered by AGI Corp

A geo-indexed network of agent **hives**, and a router that sends a **simulated** command to the hives, robots and software inside a region. Everything here is **SCRIPTED orchestration: no AI model runs behind any of it**, as in the Omega Hive and the Omega Claw it is built from.

## What this is not

**Nothing in this directory sends a command to a real robot or a device.** There is no network, serial, ROS, USB, Bluetooth or file-writing code in it (`swarm/test.mjs` scans for that and checks what the router imports). Every routed command is a **dry run**: one SCRIPTED-policy episode of a robotics arena world, a SCHEMATIC simulation of an AUTHORED task. Its numbers say nothing about how a physical robot would behave (the **sim-to-real gap** is the whole of the distance between the two).

**A path to real hardware is refused by default, and the router has no such path to open.** A command that names real hardware (a `hardware` other than `"simulated"`, a `mode` other than `"dry-run"`, an `operator`, a device address or field, or a target that is not a registry-simulated member) is refused with

> real hardware needs a named human operator; none is configured

Naming an operator does not change that: `real_hardware.operators` in the registry is empty, and no code path uses one. Connecting a real robot would take a named human operator, a reviewed adapter and a safety case, none of which this repository has.

The safety gate (`safety_gate/`) is a gate for a training simulator. It is **not a real-world safety system** and no standard is claimed.

## Files

| File | What it is |
|---|---|
| `authored/swarm.json` | AUTHORED: the hive names, the cluster rule, the cell scheme, the robots per campus, the capabilities, the limits and the real-hardware refusal |
| `build.py` | builds `registry/swarm.json` from `spatial/registry/geopose.json`, `hive/`, `robotics/claw/`, `robotics/registry/`, `sims/`, `npcs/`, `parishes/`; fails closed; `--check` |
| `geohash.mjs`, `geo.mjs` | cell strings; point-in-polygon, polygon against a cell, haversine |
| `router.mjs` | the geo-targeted command router |
| `gate.mjs` | the router's one door to `safety_gate/` (`canEnter` only) |
| `dryrun.mjs` | one arena-harness episode for one simulated robot |
| `audit.mjs` | the audit log format, `swarm-audit/1`, hash-chained |
| `optimise.mjs` | a small swarm-optimisation demo (naive, greedy, exact assignment) |
| `test.mjs` | `node swarm/test.mjs` |

## The registry

* **Hives**: one per campus cluster. Campuses within 100 km of each other (single linkage) share a hive, so the 10 campuses give 9 hives (Oakland and Treasure Island share the Bay Area hive).
* **Cells**: **geohash**, precision 5 (a cell about 4.9 km by 4.9 km at the equator, narrower in longitude to the north). A hive owns the cell of every campus, anchor and restoration-site pose in GeoPose, the ring of cells around each campus, and the cell of each parish centre. No cell has two owners. One restoration programme has no coordinate in GeoPose and so has no cell; it is listed as unposed.
* **Members**: per hive, the 5 Omega Claw agents, the 9 Omega Hive hall advisors and the 20 crew roles (SCRIPTED); the Hive's 168 parish guides stand in their parishes; and 2 simulated robots of each of the 3 arena embodiments per campus (AUTHORED, 60 in all). A robot stands at a pose of its own campus. That is a position in a simulation, not a statement that a robot exists there.
* **Capabilities**: `robot.litter-pickup`, `robot.litter-sort`, `robot.rov-survey`, `robot.gate-drive` (the four arena worlds) and `software.schedule-tournament`, `software.audit-dataset`, `software.advise-visitor` (values quoted from registries).

## A command

```json
{ "schema": "swarm-command/1", "id": "demo-1", "capability": "robot.litter-pickup",
  "region": { "polygon": [[37.77, -122.30], [37.77, -122.24], [37.83, -122.24], [37.83, -122.30]] },
  "mode": "dry-run", "params": { "level": 1, "seed": 3 } }
```

`region` is exactly one of `polygon` ([lat, lng] pairs, 3 to 64, simple, no antimeridian) or `cells` (geohash strings; a short string names every cell beneath it). `targets` may narrow the selection to named registry members.

The router (1) refuses real hardware first; (2) checks the shape; (3) finds the cells the region touches, their hives, and the members inside; (4) for every robot target consults the safety gate and **holds** the robot when the gate says no; (5) dry-runs what passes; (6) appends one audit row, refused commands included.

**How the gate is used.** A simulated robot is not a person: its actor record holds no induction, PPE check or passed tier. The router asks the gate (`canEnter`, which is pure) about every gate record of the robot's task and takes the strictest answer. `robot.gate-drive` is the forklift-run bay-yard lane, which the gate holds for all five hall records; the other three arena worlds are headless worlds the gate's index (stations and simulator seats) has no record for, so it answers `unknown-target`; the router runs those as dry runs and the audit row says `no-record`. The gate's own reasons are quoted in the row.

**The no-record rule.** A target the gate holds no record for may proceed **only as a dry run in simulation**. In any other mode, and on any future path toward a real target, it is **held** with the reason `no safety record for this target: held`. A deny holds in every mode. The rule is the constant `NO_RECORD_RULE` and the function `gateDecision` in `gate.mjs`, and the router asks it with the command's own mode. Today a non-dry-run mode never reaches the gate because real hardware is refused first, so both outcomes are refusals; the rule stays in code so a later path cannot inherit the dry-run allowance.

## The audit log

`swarm-audit/1`: one JSON row per command, chained: `hash = sha256(prev + "\n" + canonical(row))`. Fields: `command` (id, sha256, capability, region, mode as sent), `status` (`routed`, `held`, `partial`, `refused`), `refusal` (code and reason), `resolved` (cells, hives, targets), `gate` (every consult with the gate's reasons), `results` (per target), `provenance` (SCRIPTED, model null, router source digest, registry and gate stamps, `real_hardware: "refused"`). There is no clock field, so the same command gives the same row. The log lives in memory; the caller writes `toJSONL()` wherever it wants it.

## Location privacy

No learner location is stored or sent. Positions are campuses, anchors and restoration sites already in the repo, or the centre of a parish outline; geolocation of a person stays on the device, as the geomap already does it.

## Swarm optimisation demo

`node swarm/optimise.mjs` assigns the 60 simulated robots to 57 authored task slots (one per cell holding a campus, anchor or site pose) by three rules and prints what each measured. Distances are haversine kilometres between simulated positions; no robot moves. See the numbers in the test output; they say how well a rule matches the simulated robots to the slots, not how useful a task is.

## Limits

* Geofence edges are straight lines in latitude and longitude, not great circles; a fence is a simple polygon that does not cross the antimeridian.
* The registry holds 9 hives; a region elsewhere finds none and is refused (`no-hive-in-region`).
* Robot positions are placed by a documented hash rule, not surveyed.
* Geohash is a public-domain grid used here for addressing; no conformance to any robotics or fleet-management standard is claimed.
