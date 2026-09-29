#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy - the robotics environment registry (ROBOLAB, wave 11).

WHAT THIS IS. A catalogue of gym-style ENVIRONMENT SPECS and ROBOT EMBODIMENTS built from what this repo already
has, written to robotics/registry/robotics.json (schema tc-robotics/1, contract $SP/ROBOTICS_CONTRACT.md v1):

  * sim-seat envs  - one per training seat in sims/registry/sims.json (11). Observation = that seat's own dash[]
                     readout (names + units READ from sims/; ranges are null because sims/ does not declare them),
                     action = its controls[] (discrete keys), reward = its rubric axes, the scripted reference
                     operator sims/ already declares. They run in web/trade_craft_3d.html and are recorded by the
                     EXISTING training/ `sim` kind (+ TRACE) - nothing new is recorded for them here.
  * robokit envs   - four small world tasks the new web/robokit.py runs (teleop + scripted reference policy):
                     litter pickup (litter types READ from ambient/), litter sort (arm-on-base), ROV survey (ROV
                     limits READ from web/deepkit.py DEEP_SPEED; monitoring idea from restoration/ + underwater/),
                     gate drive (gate count READ from the forklift-run bay-yard scenario). Layouts are AUTHORED,
                     seeded (mulberry32), in env-local metres - never lat/lon.
  * embodiments    - three AUTHORED schematic robots: a wheeled rover, an arm-on-base, an ROV. Unicycle kinematics
                     (SCHEMATIC), not any real robot's dynamics.
  * teleop         - keyboard + touch (>= 44 px) mappings per embodiment.

WHAT THIS IS NOT. No model has been trained on any of this and none is claimed to be: the repo records no training
run. The reference policy is SCRIPTED (hand-written, deterministic, seeded; no model, no network). The shapes are
"shaped after" gym-style specs; this pack does not claim compatibility with RLDS, LeRobot or ML-Agents files - no
round-trip test exists. Episodes are recorded (opt-in, device-local) by training/'s `world-teleop` kind.

Fail closed: every value read from another registry is indexed directly; a missing field stops the build by name.
"""
import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'robotics.json'
BUILT = '2026-09-29'
SCHEMA = 'tc-robotics/1'
CONTRACT_VERSION = 1


class RoboticsError(Exception):
    pass


def need(cond, msg):
    if not cond:
        raise RoboticsError(msg)


sims = json.loads((ROOT / 'sims/registry/sims.json').read_text())
ambient = json.loads((ROOT / 'ambient/registry/ambient.json').read_text())
tasks = json.loads((ROOT / 'tasks/registry/tasks.json').read_text())
deep_src = (ROOT / 'web/deepkit.py').read_text()
need((ROOT / 'underwater/registry/underwater.json').exists(), 'underwater/registry/underwater.json missing')
need((ROOT / 'restoration/registry/scenarios.json').exists(), 'restoration/registry/scenarios.json missing')

# ---- DERIVED inputs ----------------------------------------------------------------------------------------------
m = re.search(r"const DEEP_SPEED = \{ vertical: ([0-9.]+), rov: ([0-9.]+), turn: ([0-9.]+) \}", deep_src)
need(m, 'web/deepkit.py DEEP_SPEED not found - the ROV limits are read from it')
DEEP_V, DEEP_ROV, DEEP_TURN = (float(x) for x in m.groups())

LITTER = sorted(ambient['litter'])            # ids of the ambient litter types (bag, bottle, ...)
need(len(LITTER) >= 3, 'ambient litter types missing')

fork = sims['sims']['forklift-run']
bay_yard = [s for s in fork['scenarios'] if s['id'] == 'bay-yard']
need(len(bay_yard) == 1, 'sims forklift-run scenario bay-yard missing')
GATES = int(bay_yard[0]['params']['gates'])

RESTO_TASKS = [t['id'] for t in tasks['tasks'] if t['kind'] == 'resto-scenario']
need(RESTO_TASKS, 'tasks/ has no resto-scenario tasks')

# ---- embodiments (AUTHORED) --------------------------------------------------------------------------------------
EMBODIMENTS = {
    'rover.wheeled': {
        'name': 'Wheeled rover', 'kind': 'wheeled-rover', 'medium': 'land', 'provenance': 'AUTHORED',
        'dims_m': {'length': 0.9, 'width': 0.7, 'height': 0.6}, 'mass_kg': 45,
        'limits': {'v_min_ms': -0.8, 'v_max_ms': 1.5, 'w_max_rads': 1.2},
        'radius_m': 0.45,
        'sensors': [{'id': 'pose', 'what': 'env-local position and heading (SCHEMATIC odometry, exact)', 'unit': 'm, rad'},
                    {'id': 'near', 'what': 'ids of AUTHORED objects within 6 m (at most 4, nearest first)', 'unit': 'ids'},
                    {'id': 'target', 'what': 'bearing and distance to the nearest open target', 'unit': 'rad, m'}],
        'kinematics': 'unicycle: e += v sin(yaw) dt, n += v cos(yaw) dt, yaw += w dt (SCHEMATIC)',
    },
    'arm.on-base': {
        'name': 'Arm on a wheeled base', 'kind': 'arm-on-base', 'medium': 'land', 'provenance': 'AUTHORED',
        'dims_m': {'length': 1.0, 'width': 0.8, 'height': 1.2}, 'mass_kg': 70,
        'limits': {'v_min_ms': -0.6, 'v_max_ms': 1.0, 'w_max_rads': 1.0, 'reach_m': 0.9, 'payload': 1},
        'radius_m': 0.5,
        'sensors': [{'id': 'pose', 'what': 'env-local position and heading (SCHEMATIC odometry, exact)', 'unit': 'm, rad'},
                    {'id': 'near', 'what': 'ids of AUTHORED objects within 6 m (at most 4, nearest first)', 'unit': 'ids'},
                    {'id': 'grip', 'what': 'whether the gripper holds an item', 'unit': 'bool'}],
        'kinematics': 'unicycle base; the arm is SCHEMATIC - a reach radius and a one-item gripper, no joint model',
    },
    'rov.survey': {
        'name': 'Survey ROV', 'kind': 'rov', 'medium': 'water', 'provenance': 'AUTHORED',
        'dims_m': {'length': 0.8, 'width': 0.6, 'height': 0.5}, 'mass_kg': 30,
        # DERIVED: the same limits the world's ROV camera uses (web/deepkit.py DEEP_SPEED)
        'limits': {'v_min_ms': -DEEP_ROV / 2, 'v_max_ms': DEEP_ROV, 'w_max_rads': DEEP_TURN, 'vz_max_ms': DEEP_V,
                   'depth_max_m': 8.0},
        'limits_source': 'web/deepkit.py#DEEP_SPEED (rov, turn, vertical); depth_max_m AUTHORED',
        'radius_m': 0.4,
        'sensors': [{'id': 'pose', 'what': 'env-local position, heading and depth (SCHEMATIC, exact)', 'unit': 'm, rad, m'},
                    {'id': 'near', 'what': 'ids of AUTHORED monitoring targets within 6 m (at most 4)', 'unit': 'ids'},
                    {'id': 'target', 'what': 'bearing, distance and depth of the nearest unvisited target', 'unit': 'rad, m, m'}],
        'kinematics': 'unicycle in the horizontal plane + a depth rate (SCHEMATIC); no buoyancy, current or tether model',
    },
}

KEYS_BASE = [{'keys': 'W / ArrowUp', 'field': 'v', 'value': 'max'},
             {'keys': 'S / ArrowDown', 'field': 'v', 'value': 'min'},
             {'keys': 'A / ArrowLeft', 'field': 'w', 'value': '+max'},
             {'keys': 'D / ArrowRight', 'field': 'w', 'value': '-max'}]
TOUCH_BASE = [{'id': 'fwd', 'label_key': 'robo.t.fwd', 'field': 'v', 'value': 'max'},
              {'id': 'back', 'label_key': 'robo.t.back', 'field': 'v', 'value': 'min'},
              {'id': 'left', 'label_key': 'robo.t.left', 'field': 'w', 'value': '+max'},
              {'id': 'right', 'label_key': 'robo.t.right', 'field': 'w', 'value': '-max'}]
TELEOP = {
    'rover.wheeled': {'keyboard': KEYS_BASE, 'touch': TOUCH_BASE, 'min_touch_px': 44},
    'arm.on-base': {'keyboard': KEYS_BASE + [{'keys': 'G / Space', 'field': 'grip', 'value': 1}],
                    'touch': TOUCH_BASE + [{'id': 'grip', 'label_key': 'robo.t.grip', 'field': 'grip', 'value': 1}],
                    'min_touch_px': 44},
    'rov.survey': {'keyboard': KEYS_BASE + [{'keys': 'R', 'field': 'vz', 'value': '-max (up)'},
                                            {'keys': 'F', 'field': 'vz', 'value': '+max (down)'}],
                   'touch': TOUCH_BASE + [{'id': 'up', 'label_key': 'robo.t.up', 'field': 'vz', 'value': '-max'},
                                          {'id': 'down', 'label_key': 'robo.t.down', 'field': 'vz', 'value': '+max'}],
                   'min_touch_px': 44},
}

# ---- robokit envs (AUTHORED layouts, DERIVED counts) --------------------------------------------------------------
HALF = 20.0          # arena half-size, metres (AUTHORED)
DT, CAP = 0.1, 600   # control step and episode cap -> 60 s
SEEDS = [1, 2, 3, 4, 5]
DIAG = round((2 * HALF) * 2 ** 0.5, 2)


def base_obs(emb):
    lim = EMBODIMENTS[emb]['limits']
    return [{'name': 'pose_e', 'unit': 'm', 'low': -HALF, 'high': HALF, 'dtype': 'float'},
            {'name': 'pose_n', 'unit': 'm', 'low': -HALF, 'high': HALF, 'dtype': 'float'},
            {'name': 'yaw', 'unit': 'rad', 'low': -3.1416, 'high': 3.1416, 'dtype': 'float'},
            {'name': 'v', 'unit': 'm/s', 'low': lim['v_min_ms'], 'high': lim['v_max_ms'], 'dtype': 'float'},
            {'name': 'w', 'unit': 'rad/s', 'low': -lim['w_max_rads'], 'high': lim['w_max_rads'], 'dtype': 'float'},
            {'name': 'target_bearing', 'unit': 'rad', 'low': -3.1416, 'high': 3.1416, 'dtype': 'float'},
            {'name': 'target_dist', 'unit': 'm', 'low': 0, 'high': DIAG, 'dtype': 'float'},
            {'name': 'near', 'unit': 'ids', 'low': 0, 'high': 4, 'dtype': 'id-list', 'shape': [4]}]


def base_action(emb):
    lim = EMBODIMENTS[emb]['limits']
    return [{'name': 'v', 'unit': 'm/s', 'low': lim['v_min_ms'], 'high': lim['v_max_ms']},
            {'name': 'w', 'unit': 'rad/s', 'low': -lim['w_max_rads'], 'high': lim['w_max_rads']}]


STEP_PENALTY = {'term': 'time', 'weight': -0.01, 'unit': 'per step', 'why': 'finish sooner'}
COLLIDE = {'term': 'collision', 'weight': -0.5, 'unit': 'per contact', 'why': 'an obstacle or the arena wall was struck'}
CAP_TERM = {'id': 'cap', 'when': f'{CAP} control steps ({CAP * DT:.0f} s) elapsed'}
REF_STEPS = ['turn toward the nearest open target (proportional on bearing)',
             'drive at a speed that falls with the heading error',
             'veer away when an obstacle sits within 2 m ahead']

ENVS = {
    'world.litter-pickup': {
        'name': 'Litter pickup', 'embodiments': ['rover.wheeled'], 'medium': 'land',
        'brief': 'Drive the rover over AUTHORED litter items (types read from ambient/) to collect them all.',
        'objects': {'litter': 8, 'obstacles': 6, 'litter_types': LITTER},
        'sources': ['ambient/registry/ambient.json#litter', 'tasks/registry/tasks.json#tasks'],
        'observation_extra': [{'name': 'collected', 'unit': 'count', 'low': 0, 'high': 8, 'dtype': 'int'}],
        'action_extra': [],
        'reward': [{'term': 'pickup', 'weight': 1.0, 'unit': 'per item', 'why': 'an item was collected (within 0.9 m)'},
                   STEP_PENALTY, COLLIDE],
        'termination': [{'id': 'all-collected', 'when': 'every litter item is collected (success)'}, CAP_TERM],
    },
    'world.litter-sort': {
        'name': 'Litter sort', 'embodiments': ['arm.on-base'], 'medium': 'land',
        'brief': 'Pick each litter item with the arm (grip within reach) and drop it in the bin.',
        'objects': {'litter': 4, 'obstacles': 4, 'bin': 1, 'litter_types': LITTER},
        'sources': ['ambient/registry/ambient.json#litter'],
        'observation_extra': [{'name': 'carrying', 'unit': 'bool', 'low': 0, 'high': 1, 'dtype': 'bool'},
                              {'name': 'binned', 'unit': 'count', 'low': 0, 'high': 4, 'dtype': 'int'}],
        'action_extra': [{'name': 'grip', 'unit': '0|1', 'low': 0, 'high': 1}],
        'reward': [{'term': 'pickup', 'weight': 0.2, 'unit': 'per grip', 'why': 'an item was lifted'},
                   {'term': 'deposit', 'weight': 1.0, 'unit': 'per item', 'why': 'an item was dropped in the bin'},
                   STEP_PENALTY, COLLIDE],
        'termination': [{'id': 'all-binned', 'when': 'every item is in the bin (success)'}, CAP_TERM],
    },
    'world.rov-survey': {
        'name': 'ROV monitoring survey', 'embodiments': ['rov.survey'], 'medium': 'water',
        'brief': 'Visit each AUTHORED monitoring target at its depth, like the restoration monitoring the Bay ROV does.',
        'objects': {'targets': 4, 'obstacles': 4},
        'sources': ['web/deepkit.py#DEEP_SPEED', 'underwater/registry/underwater.json#restore_hooks',
                    'restoration/registry/scenarios.json#scenarios', f'tasks/registry/tasks.json#{RESTO_TASKS[0]}'],
        'observation_extra': [{'name': 'depth', 'unit': 'm', 'low': 0, 'high': 8.0, 'dtype': 'float'},
                              {'name': 'target_depth', 'unit': 'm', 'low': 0, 'high': 8.0, 'dtype': 'float'},
                              {'name': 'visited', 'unit': 'count', 'low': 0, 'high': 4, 'dtype': 'int'}],
        'action_extra': [{'name': 'vz', 'unit': 'm/s', 'low': -DEEP_V, 'high': DEEP_V}],
        'reward': [{'term': 'visit', 'weight': 1.0, 'unit': 'per target', 'why': 'within 1.5 m across and 1 m in depth'},
                   STEP_PENALTY, COLLIDE],
        'termination': [{'id': 'all-visited', 'when': 'every target is visited (success)'}, CAP_TERM],
    },
    'world.gate-drive': {
        'name': 'Gate drive', 'embodiments': ['rover.wheeled'], 'medium': 'land',
        'brief': f'Take {GATES} gates in order (the gate count of the forklift-run bay-yard lane), without striking a cone.',
        'objects': {'gates': GATES, 'obstacles': 4},
        'sources': ['sims/registry/sims.json#sims.forklift-run.scenarios.bay-yard.params.gates',
                    'fleet/registry/fleet.json#honesty'],
        'observation_extra': [{'name': 'gates_taken', 'unit': 'count', 'low': 0, 'high': GATES, 'dtype': 'int'}],
        'action_extra': [],
        'reward': [{'term': 'gate', 'weight': 1.0, 'unit': 'per gate', 'why': 'the next gate was passed within 1.2 m of its centre'},
                   STEP_PENALTY, COLLIDE],
        'termination': [{'id': 'all-gates', 'when': 'every gate is taken in order (success)'}, CAP_TERM],
    },
}

envs = {}
for eid, e in ENVS.items():
    emb = e['embodiments'][0]
    need(emb in EMBODIMENTS, f'{eid}: embodiment {emb} unknown')
    envs[eid] = {
        'id': eid, 'version': 1, 'name': e['name'], 'brief': e['brief'], 'provenance': 'AUTHORED', 'runner': 'robokit',
        'medium': e['medium'],
        'world': {'pages': ['web/trade_craft_parishes.html', 'web/trade_craft_bay.html', 'web/trade_craft_robotics.html'],
                  'frame': 'env-local metres, origin at the AUTHORED spawn, yaw 0 = +n, CCW positive; never lat/lon',
                  'arena_half_m': HALF},
        'embodiments': e['embodiments'], 'objects': e['objects'], 'sources': e['sources'],
        'observation': base_obs(emb) + e['observation_extra'],
        'action': {'type': 'continuous', 'fields': base_action(emb) + e['action_extra']},
        'reward': e['reward'], 'termination': e['termination'],
        'episode_cap': {'steps': CAP, 'dt_s': DT}, 'seeds': SEEDS, 'rng': 'mulberry32(seed)',
        'reference_policy': {'id': f'ref.{eid.split(".")[1]}', 'provenance': 'SCRIPTED', 'steps': REF_STEPS,
                             'note': 'hand-written and deterministic; not learned, no model, no network'},
    }

# ---- sim-seat envs (DERIVED from sims/) -----------------------------------------------------------------------------
for sid, s in sims['sims'].items():
    envs[f'sim.{sid}'] = {
        'id': f'sim.{sid}', 'version': 1, 'name': s['name'], 'brief': s['task'], 'provenance': 'DERIVED',
        'runner': 'sim-seat', 'medium': 'land',
        'world': {'pages': ['web/trade_craft_3d.html'], 'frame': 'the seat\'s own SCHEMATIC simulator',
                  'launch': f'web/trade_craft_3d.html?sim={sid}'},
        'embodiments': [], 'sources': [f'sims/registry/sims.json#sims.{sid}'],
        'observation': [{'name': d['id'], 'unit': d['unit'], 'low': None, 'high': None,
                         'dtype': 'float' if d['unit'] else 'display', 'label': d['label']} for d in s['dash']],
        'observation_note': 'the seat\'s dash[] readout (the TRACE gauges); sims/ declares names and units, not ranges, '
                            'so low/high are null rather than invented',
        'action': {'type': 'discrete', 'fields': [{'keys': c['keys'], 'action': c['action']} for c in s['controls']]},
        'reward': [{'term': r['axis'], 'weight': 1.0, 'unit': 'rubric row ok', 'why': r['measure'], 'pass': r['pass']}
                   for r in s['rubric']],
        'termination': [{'id': 'results', 'when': 'the seat posts its results panel (simResults)'},
                        {'id': 'trace-cap', 'when': 'TRACE stops sampling at its cap (the run itself continues)'}],
        'episode_cap': {'steps': None, 'dt_s': 1, 'note': 'TRACE ~1 Hz, capped by training/ trace.max_samples'},
        'seeds': [], 'scenarios': [c['id'] for c in s['scenarios']],
        'reference_policy': {'id': f'operator.{sid}', 'provenance': 'SCRIPTED',
                             'levels': s['operator']['levels'],
                             'steps': [p['step'] for p in s['operator']['procedure']],
                             'note': 'the scripted reference operator sims/ declares for this seat'},
        'recorded_by': 'training/ kind `sim` (existing)',
    }

HONESTY = {
    'trained': 'NOTHING HAS BEEN TRAINED. No model has been trained on these environments or on any episode they '
               'produce, and the repo records no training run. They are specs and a runnable schematic sandbox.',
    'authored': 'Arenas, embodiments and dynamics are AUTHORED / SCHEMATIC (unicycle kinematics, circle '
                'obstacles); not the dynamics of any real robot, vehicle or ROV.',
    'derived': 'Counts and limits named in `sources` are READ from sims/, ambient/, tasks/, restoration/, '
               'underwater/ and web/deepkit.py at build time.',
    'scripted': 'Reference policies are SCRIPTED: hand-written, deterministic, seeded - no model, no network.',
    'formats': 'Shaped after gym-style environment specs. Not an RLDS, LeRobot or ML-Agents file: no round-trip '
               'test exists in the repo, so no compatibility is claimed.',
    'data': 'Episodes (training/ kind world-teleop) are opt-in per episode, device-local, and carry no names, '
            'emails, free text, audio, camera, biometric, device id or real-world location. Classroom / K-12 '
            'mode offers neither recording nor sharing.',
}

need(all(t['min_touch_px'] >= 44 for t in TELEOP.values()), 'touch controls must be at least 44 px')
need(set(TELEOP) == set(EMBODIMENTS), 'every embodiment needs a teleop mapping')
for eid, e in envs.items():
    for o in e['observation']:
        need(o['unit'] is not None and o['name'], f'{eid}: observation without a unit')
    need(e['reward'] and e['termination'], f'{eid}: an env needs reward terms and termination')

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
doc = {
    'pack': 'smartcitix-robotics', 'schema': SCHEMA, 'contract_version': CONTRACT_VERSION, 'built': BUILT,
    'source_stamp': stamp, 'honesty': HONESTY, 'embodiments': {k: {'id': k, **v} for k, v in EMBODIMENTS.items()},
    'teleop': TELEOP, 'envs': envs,
    'episode_kind': 'world-teleop (training/registry/training.json#world_episode_kinds)',
    'counts': {'embodiments': len(EMBODIMENTS), 'envs': len(envs),
               'robokit_envs': sum(1 for e in envs.values() if e['runner'] == 'robokit'),
               'sim_seat_envs': sum(1 for e in envs.values() if e['runner'] == 'sim-seat'),
               'trained_models': 0},
}
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
print(f"robotics: {doc['counts']['envs']} env specs ({doc['counts']['robokit_envs']} robokit, "
      f"{doc['counts']['sim_seat_envs']} sim-seat), {len(EMBODIMENTS)} AUTHORED embodiments, 0 trained models "
      f"(source stamp {stamp})")
