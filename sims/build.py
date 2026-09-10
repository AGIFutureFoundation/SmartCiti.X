#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the simulator registry builder.

Two operable training simulators, defined as data: what machine, which
halls train on it, which skill each run exercises, and the deterministic
rubric that scores it. The 3D environment implements the physics and the
controls; this registry owns the curriculum claims, so the sim and the
skill graph cannot drift apart — sims/test.mjs proves every binding.

SCORING CONTRACT, the same shape the mentor fabric enforces (ACP-11) and
the sibling VR prototype ships: the grader is DETERMINISTIC. Every axis is
computed from measured state (distance, counts, peak amplitudes); nothing
narrative can change a score.

HONESTY: these are schematic physics for practising control discipline —
smooth inputs, swing management, ordered procedure. They are not equipment
certification and no seat time here counts toward one; the registry says
so, and the assessment gates still demand unaided verification runs.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

PACK_VERSION = "3.2.0"
BUILT = "2026-09-10"

SIMS = {
    'crane-lift': {
        'name': 'Tower Crane Lift',
        'kind': 'machine',
        'task': 'Pick the load from the supply pad, carry it over the stacks '
                'and set it inside the target ring — swing under control the '
                'whole way.',
        'controls': [
            {'keys': 'A / D', 'action': 'slew the jib'},
            {'keys': 'W / S', 'action': 'trolley out / in'},
            {'keys': 'Q / E', 'action': 'hoist up / down'},
            {'keys': 'Space', 'action': 'hook / release the load'},
        ],
        'rubric': [
            {'axis': 'placement', 'measure': 'distance from target centre at release (m)',
             'pass': '<= 1.2'},
            {'axis': 'swing', 'measure': 'peak load swing during carry (m)',
             'pass': '<= 2.0'},
            {'axis': 'strikes', 'measure': 'load or hook contacts with the stacks',
             'pass': '== 0'},
            {'axis': 'time', 'measure': 'seconds from hook to release',
             'pass': 'informational'},
        ],
        'halls': ['crane-ops', 'riggers', 'steel-erectors', 'port-crane'],
        'skill_strand': 'machines',
        'skill_tier': 'applied',
        'dash': [
            {'id': 'slew', 'label': 'Slew', 'unit': '\u00b0'},
            {'id': 'radius', 'label': 'Radius', 'unit': 'm'},
            {'id': 'hook', 'label': 'Hook', 'unit': 'm'},
            {'id': 'swing', 'label': 'Swing', 'unit': 'm', 'warn_at': 1.6},
            {'id': 'strikes', 'label': 'Strikes', 'unit': '', 'warn_at': 1},
            {'id': 'time', 'label': 'T', 'unit': 's'},
        ],
        'audio': {'engine': 'hoist-motor',
                  'alerts': ['overswing-chirp', 'strike-thud', 'result-chime'],
                  'note': 'synthesized in-page (WebAudio); no recordings shipped'},
        'haptics': ['strike', 'finish'],
        'view_modes': ['orbit', 'cab'],
    },
    'forklift-run': {
        'name': 'Forklift Yard Run',
        'kind': 'driving',
        'task': 'Thread the cone lane, pick the pallet square on the forks, '
                'and set it down inside the dock bay — without disturbing '
                'a cone.',
        'controls': [
            {'keys': 'W / S', 'action': 'drive / reverse'},
            {'keys': 'A / D', 'action': 'steer'},
            {'keys': 'Space', 'action': 'lift / set the pallet'},
        ],
        'rubric': [
            {'axis': 'gates', 'measure': 'cone gates taken in order',
             'pass': '== all'},
            {'axis': 'cones', 'measure': 'cones struck',
             'pass': '== 0'},
            {'axis': 'docking', 'measure': 'pallet inside the dock bay at set-down',
             'pass': 'required'},
            {'axis': 'time', 'measure': 'seconds start to set-down',
             'pass': 'informational'},
        ],
        'halls': ['teamsters', 'heavy-equip', 'operating-eng', 'laborers',
                  'marine-terminal'],
        'skill_strand': 'machines',
        'skill_tier': 'applied',
        'dash': [
            {'id': 'speed', 'label': 'Speed', 'unit': 'km/h'},
            {'id': 'steer', 'label': 'Steer', 'unit': '\u00b0'},
            {'id': 'load', 'label': 'Load', 'unit': ''},
            {'id': 'gates', 'label': 'Gates', 'unit': ''},
            {'id': 'cones', 'label': 'Cones', 'unit': '', 'warn_at': 1},
            {'id': 'time', 'label': 'T', 'unit': 's'},
        ],
        'audio': {'engine': 'diesel',
                  'alerts': ['reverse-beeper', 'cone-thud', 'result-chime'],
                  'note': 'synthesized in-page (WebAudio); no recordings shipped'},
        'haptics': ['cone', 'gate', 'finish'],
        'view_modes': ['chase', 'driver'],
    },
}

unions = json.load(open(ROOT / 'unions/registry/unions.json'))['unions']
skills = {s['skill_id'] for s in
          json.load(open(ROOT / 'pack/registry/skills.json'))['skills']}
slugs = {u['slug'] for u in unions}

bindings = {}
for sim_id, sim in SIMS.items():
    for hall in sim['halls']:
        assert hall in slugs, f'{sim_id}: unknown hall {hall}'
        skill = f"{hall}.{sim['skill_strand']}.{sim['skill_tier']}"
        assert skill in skills, f'{sim_id}: no such skill {skill}'
        bindings.setdefault(hall, []).append(
            {'sim': sim_id, 'skill_id': skill})

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

doc = {
    'pack': 'smartcitix-trade-craft-academy-sim-registry',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'scoring_contract': 'deterministic: every rubric axis is computed from '
                        'measured state; nothing narrative can change a score',
    'honesty': {
        'status': 'schematic physics for practising control discipline - '
                  'smooth inputs, swing management, ordered procedure. Not '
                  'equipment certification; no seat time here counts toward '
                  'one, and the assessment gates still demand unaided '
                  'verification runs.',
    },
    'sims': SIMS,
    'hall_bindings': bindings,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'sims.json').write_text(json.dumps(doc, indent=1) + '\n')
n_halls = len(bindings)
print(f"sim registry: {len(SIMS)} simulators bound to {n_halls} halls "
      f"(source stamp {stamp})")
