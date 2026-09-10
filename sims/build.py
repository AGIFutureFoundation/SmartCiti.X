#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the simulator registry builder.

The operable training simulators, defined as data: what machine, which
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
        # Regional scenarios: the campus you train at picks the yard. The
        # ENVIRONMENT varies; the rubric contract above never does.
        'scenarios': [
            {'id': 'bay-steel', 'campus': 'treasure-island',
             'name': 'Bay high-steel lift',
             'brief': 'Tower steel over the bay on a still morning - a '
                      'clean yard, nothing between you and your own swing.',
             'params': {'stack_h': 1.0, 'drift': 0.0}},
            {'id': 'oak-terminal', 'campus': 'oakland',
             'name': 'Oakland terminal lift',
             'brief': 'Container stacks crowd the swing path - carry high '
                      'and slow, the corridors are tight.',
             'params': {'stack_h': 1.5, 'drift': 0.0}},
            {'id': 'nola-wharf', 'campus': 'new-orleans',
             'name': 'Crescent wharf lift',
             'brief': 'A steady river breeze leans on the load the whole '
                      'carry - trim your swing against it.',
             'params': {'stack_h': 1.0, 'drift': 0.5}},
        ],
    },
    'excavator-trench': {
        'name': 'Excavator Trench Cut',
        'kind': 'machine',
        'task': 'Cut the marked trench to grade cell by cell and land every '
                'bucket in the spoil zone — the flagged cell holds a live '
                'utility at half depth, so it stops shallow.',
        'controls': [
            {'keys': 'A / D', 'action': 'slew the house'},
            {'keys': 'W / S', 'action': 'reach out / in'},
            {'keys': 'Q / E', 'action': 'bucket up / down'},
            {'keys': 'Space', 'action': 'dig / dump the bucket'},
        ],
        'rubric': [
            {'axis': 'grade', 'measure': 'trench cells finished at their marked depth',
             'pass': '== all'},
            {'axis': 'utility', 'measure': 'strikes on the flagged utility',
             'pass': '== 0'},
            {'axis': 'spoil', 'measure': 'buckets landed inside the spoil zone',
             'pass': '== all'},
            {'axis': 'time', 'measure': 'seconds first dig to last dump',
             'pass': 'informational'},
        ],
        'halls': ['operating-eng', 'shoring', 'laborers', 'demolition'],
        'skill_strand': 'machines',
        'skill_tier': 'applied',
        'dash': [
            {'id': 'reach', 'label': 'Reach', 'unit': 'm'},
            {'id': 'depth', 'label': 'Bucket', 'unit': 'm'},
            {'id': 'grade', 'label': 'Grade', 'unit': ''},
            {'id': 'spoil', 'label': 'Spoil', 'unit': ''},
            {'id': 'utility', 'label': 'Utility', 'unit': '', 'warn_at': 1},
            {'id': 'time', 'label': 'T', 'unit': 's'},
        ],
        'audio': {'engine': 'diesel',
                  'alerts': ['utility-alarm', 'dump-thud', 'result-chime'],
                  'note': 'synthesized in-page (WebAudio); no recordings shipped'},
        'haptics': ['utility', 'dump', 'finish'],
        'view_modes': ['orbit', 'cab'],
        # Regional scenarios: the trench profile is the region's own -
        # cells carry their marked depth and flagged utilities as data.
        'scenarios': [
            {'id': 'bay-retrofit', 'campus': 'treasure-island',
             'name': 'Seismic retrofit cut',
             'brief': 'Deep footing cells beside a braced frame - long '
                      'careful digs, one flagged conduit crossing.',
             'params': {'cells': [{'d': 2.0}, {'d': 2.0},
                                  {'d': 0.5, 'util': True}, {'d': 1.5}]}},
            {'id': 'oak-fill', 'campus': 'oakland',
             'name': 'Old-fill utility cut',
             'brief': 'Waterfront fill ground, crowded with legacy lines - '
                      'two flagged cells stop shallow.',
             'params': {'cells': [{'d': 1.5}, {'d': 0.5, 'util': True},
                                  {'d': 1.5}, {'d': 0.5, 'util': True}]}},
            {'id': 'nola-below-sea', 'campus': 'new-orleans',
             'name': 'Below-sea trench',
             'brief': 'High water table, one live utility at half depth - '
                      'the flagged cell stops shallow.',
             'params': {'cells': [{'d': 1.5}, {'d': 1.5},
                                  {'d': 0.5, 'util': True}, {'d': 1.5}]}},
        ],
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
        # Regional scenarios: gate count and dock tolerance are the
        # region's lane, declared here; "all gates, no cones" stays the law.
        'scenarios': [
            {'id': 'bay-yard', 'campus': 'treasure-island',
             'name': 'Island yard run',
             'brief': 'The training yard lane - four gates and a full-width '
                      'dock bay to land the pallet in.',
             'params': {'gates': 4, 'dock_w': 2.2}},
            {'id': 'oak-lane', 'campus': 'oakland',
             'name': 'Terminal container lane',
             'brief': 'A fifth gate threads the container rows - longer '
                      'lane, same clean-run law.',
             'params': {'gates': 5, 'dock_w': 2.2}},
            {'id': 'nola-dock', 'campus': 'new-orleans',
             'name': 'Wharf dock set',
             'brief': 'The wharf dock is narrow - four gates, then a '
                      'set-down with little room to be wrong.',
             'params': {'gates': 4, 'dock_w': 1.5}},
        ],
    },
    'weld-bead': {
        'name': 'Weld Bead Run',
        'kind': 'process',
        'task': 'Strike the arc and run one clean bead down the marked '
                'seam — hold the gap inside the band and keep the torch '
                'travelling; linger on a segment and the plate burns '
                'through.',
        'controls': [
            {'keys': 'W / S', 'action': 'travel the torch along the seam'},
            {'keys': 'Q / E', 'action': 'raise / lower the torch (arc gap)'},
            {'keys': 'Space', 'action': 'strike / break the arc'},
        ],
        'rubric': [
            {'axis': 'fusion', 'measure': 'seam segments fused end to end',
             'pass': '== all'},
            {'axis': 'band', 'measure': 'share of fused segments laid with the '
                                        'gap inside the band (%)',
             'pass': '>= 90'},
            {'axis': 'burns', 'measure': 'burn-throughs from lingering heat',
             'pass': '== 0'},
            {'axis': 'time', 'measure': 'seconds first strike to last fuse',
             'pass': 'informational'},
        ],
        'halls': ['welders', 'boilermakers', 'shipfitters', 'fabricators',
                  'pipeline'],
        'skill_strand': 'machines',
        'skill_tier': 'applied',
        'dash': [
            {'id': 'gap', 'label': 'Gap', 'unit': 'mm', 'warn_at': 5.2},
            {'id': 'heat', 'label': 'Heat', 'unit': '%', 'warn_at': 85},
            {'id': 'seam', 'label': 'Seam', 'unit': ''},
            {'id': 'band', 'label': 'Band', 'unit': '%'},
            {'id': 'burns', 'label': 'Burns', 'unit': '', 'warn_at': 1},
            {'id': 'time', 'label': 'T', 'unit': 's'},
        ],
        'audio': {'engine': 'arc',
                  'alerts': ['burn-alarm', 'arc-pop', 'result-chime'],
                  'note': 'synthesized in-page (WebAudio); no recordings shipped'},
        'haptics': ['burn', 'finish'],
        'view_modes': ['orbit', 'visor'],
        # Regional scenarios: seam length and gap band are the yard's own;
        # "full fusion, in band, zero burns" stays the law everywhere.
        'scenarios': [
            {'id': 'bay-deck-seam', 'campus': 'treasure-island',
             'name': 'Deck plate seam',
             'brief': 'A flat deck seam on the fabrication floor - the '
                      'forgiving band to learn the rhythm in.',
             'params': {'segs': 10, 'band': [2.0, 5.0]}},
            {'id': 'oak-flange-bead', 'campus': 'oakland',
             'name': 'Pipe flange bead',
             'brief': 'A longer run at a tighter gap - the plant '
                      'inspector reads every millimetre of it.',
             'params': {'segs': 12, 'band': [2.0, 4.5]}},
            {'id': 'nola-tank-seam', 'campus': 'new-orleans',
             'name': 'Tank shell seam',
             'brief': 'Storage-tank shell plate in Gulf humidity - a '
                      'slightly higher band, the same clean-bead law.',
             'params': {'segs': 10, 'band': [2.5, 5.5]}},
        ],
    },
    'scaffold-bay': {
        'name': 'Scaffold Bay Build',
        'kind': 'process',
        'task': 'Erect one bay in the legal order — sills, frames, braces, '
                'planks, then guardrails. The rack refuses a part whose '
                'stage has not come, every refusal counts, and the bay is '
                'not done until the rails are on.',
        'controls': [
            {'keys': 'A / D', 'action': 'choose the part rack'},
            {'keys': 'Space', 'action': 'place the next part'},
            {'keys': 'R', 'action': 'jump the rack to the legal stage'},
        ],
        'rubric': [
            {'axis': 'sequence', 'measure': 'placements refused for coming '
                                            'before their stage',
             'pass': '== 0'},
            {'axis': 'complete', 'measure': 'parts of the bay placed, rails last',
             'pass': '== all'},
            {'axis': 'time', 'measure': 'seconds first sill to last rail',
             'pass': 'informational'},
        ],
        'halls': ['scaffold', 'carpenters', 'laborers', 'bricklayers',
                  'painters'],
        'skill_strand': 'machines',
        'skill_tier': 'applied',
        'dash': [
            {'id': 'rack', 'label': 'Rack', 'unit': ''},
            {'id': 'stage', 'label': 'Stage', 'unit': ''},
            {'id': 'placed', 'label': 'Parts', 'unit': ''},
            {'id': 'faults', 'label': 'Refused', 'unit': '', 'warn_at': 1},
            {'id': 'time', 'label': 'T', 'unit': 's'},
        ],
        'audio': {'engine': 'site',
                  'alerts': ['refusal-buzz', 'lock-click', 'result-chime'],
                  'note': 'synthesized in-page (WebAudio); no recordings shipped'},
        'haptics': ['refusal', 'finish'],
        'view_modes': ['orbit', 'deck'],
        # Regional scenarios: the bay is the region's own - plank count and
        # rail count vary; "legal order, zero refusals" stays the law.
        'scenarios': [
            {'id': 'bay-training-bay', 'campus': 'treasure-island',
             'name': 'Yard training bay',
             'brief': 'One lift in the training yard - three planks, two '
                      'rails, the order to learn by heart.',
             'params': {'planks': 3, 'rails': 2}},
            {'id': 'oak-plant-bay', 'campus': 'oakland',
             'name': 'Plant maintenance bay',
             'brief': 'A wider bay against the plant wall - four planks '
                      'to deck before anyone stands the lift.',
             'params': {'planks': 4, 'rails': 2}},
            {'id': 'nola-storm-bay', 'campus': 'new-orleans',
             'name': 'Storm-hardening bay',
             'brief': 'Hurricane-season work - a third rail goes on, and '
                      'the same legal order holds in the wind.',
             'params': {'planks': 3, 'rails': 3}},
        ],
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
