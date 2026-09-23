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

THE SCRIPTED REFERENCE OPERATOR. Every seat can also be driven by a
scripted reference operator: a hand-written, deterministic control policy
in the page - a function of the seat's own live gauges(), the scenario's
params and a skill level, with no model behind it and no network reached,
exactly as the advisors are scripted. At the `optimal` level it passes
every pass-gated rubric axis on every regional scenario, and the build
proves it by running it headlessly; the degraded levels are honestly-
labelled, seeded perturbations of the same procedure, so a sweep yields
both passing demonstrations and labelled sub-optimal episodes for the
training-data recorder in training/. This registry owns the operator's
METADATA - the closed level set, the axes it guarantees at optimal, and
its reference procedure as an ordered step list the page's policy is
structured around - so the advisor that quotes the procedure, the wiki
that documents it and the page that runs it read one truth. The `layout`
block a seat carries is the yard geometry the sim and its operator share
for the same reason: a supply pad, a spoil zone, a cell pitch, declared
once and read by both, never typed twice.

The operator's provenance word is SCRIPTED: a demonstration of a written
policy on a schematic single-machine simulator - not a learned policy,
not real equipment, and not a claim about any physical robot.
"""
import hashlib
import json
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

# One bundle version, read from the manifest rather than typed here.
PACK_VERSION = json.load(open(ROOT / 'pack/manifest.json'))['pack_version']
BUILT = "2026-09-16"

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
             'pass': '<= 1.2',
             'fails_when': 'the load is let go while it is still travelling, or over '
                           'a hook position the swing has already carried past the ring'},
            {'axis': 'swing', 'measure': 'peak load swing during carry (m)',
             'pass': '<= 2.0',
             'fails_when': 'slew or trolley is driven while the load is already '
                           'moving, so every input adds to the last one'},
            {'axis': 'strikes', 'measure': 'load or hook contacts with the stacks',
             'pass': '== 0',
             'fails_when': 'the carry crosses a stack below its height, or the load '
                           'is swung into one while parked over it'},
            {'axis': 'time', 'measure': 'seconds from hook to release',
             'pass': 'informational'},
        ],
        # every hall added below is one whose own real field work is
        # planning or making this exact pick, not a stretch: ironworkers
        # and decking crews are who a tower crane actually sets structural
        # steel and deck panels for, tank-erectors set steel plate the
        # same way, and piling rigs are themselves crane-mounted
        'halls': ['crane-ops', 'riggers', 'steel-erectors', 'port-crane',
                  'ironworkers', 'decking', 'tank-erectors', 'piling'],
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
        # the yard geometry the sim and its scripted operator both read:
        # the supply pad the load waits on and the target ring it lands in
        'layout': {'supply': [14, 10], 'target': [-13, -9]},
        # Regional scenarios: the campus you train at picks the yard. The
        # ENVIRONMENT varies; the rubric contract above never does.
        'scenarios': [
            {'id': 'bay-steel', 'campus': 'treasure-island',
             'name': 'Bay high-steel lift',
             'brief': 'Tower steel over the bay on a still morning - a '
                      'clean yard, nothing between you and your own swing.',
             'teaches': 'the clean case - nothing stands in the way, so the only thing '
                        'that can spoil this carry is your own swing',
             'params': {'stack_h': 1.0, 'drift': 0.0}},
            {'id': 'oak-terminal', 'campus': 'oakland',
             'name': 'Oakland terminal lift',
             'brief': 'Container stacks crowd the swing path - carry high '
                      'and slow, the corridors are tight.',
             'teaches': 'carry height: the stacks stand half again as tall, so the '
                        'hoist has to be finished before anything moves sideways',
             'params': {'stack_h': 1.5, 'drift': 0.0}},
            {'id': 'nola-wharf', 'campus': 'new-orleans',
             'name': 'Crescent wharf lift',
             'brief': 'A steady river breeze leans on the load the whole '
                      'carry - trim your swing against it.',
             'teaches': 'trimming against a push that never lets up - the settle before '
                        'release is a hold against the breeze, not a pause',
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
             'pass': '== all',
             'fails_when': 'a cell is left short of its marked depth - or taken past '
                           'it, because one bite too many fails exactly as one too few'},
            {'axis': 'utility', 'measure': 'strikes on the flagged utility',
             'pass': '== 0',
             'fails_when': 'a flagged cell is dug past the shallow depth the locate '
                           'marks stop it at'},
            {'axis': 'spoil', 'measure': 'buckets landed inside the spoil zone',
             'pass': '== all',
             'fails_when': 'a bucket is dumped short of the zone, putting spoil back '
                           'beside the cut it was taken out of'},
            {'axis': 'time', 'measure': 'seconds first dig to last dump',
             'pass': 'informational'},
        ],
        'halls': ['operating-eng', 'shoring', 'laborers', 'demolition'],
        'skill_strand': 'machines',
        'skill_tier': 'applied',
        'dash': [
            {'id': 'slew', 'label': 'Slew', 'unit': '°'},
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
        # the trench line and spoil zone the sim and its operator share:
        # cell i sits at x = (i - (n-1)/2) * pitch on the trench line, and
        # every dig takes one `bite` of depth
        'layout': {'pitch': 2, 'trench_z': 6, 'spoil': [-5, -4], 'bite': 0.5},
        # Regional scenarios: the trench profile is the region's own -
        # cells carry their marked depth and flagged utilities as data.
        'scenarios': [
            {'id': 'bay-retrofit', 'campus': 'treasure-island',
             'name': 'Seismic retrofit cut',
             'brief': 'Deep footing cells beside a braced frame - long '
                      'careful digs, one flagged conduit crossing.',
             'teaches': 'long bite counts beside braced steel, with one crossing that '
                        'stops shallow in the middle of them',
             'params': {'cells': [{'d': 2.0}, {'d': 2.0},
                                  {'d': 0.5, 'util': True}, {'d': 1.5}]}},
            {'id': 'oak-fill', 'campus': 'oakland',
             'name': 'Old-fill utility cut',
             'brief': 'Waterfront fill ground, crowded with legacy lines - '
                      'two flagged cells stop shallow.',
             'teaches': 'two flagged crossings in four cells - the locate marks, not '
                        'the drawing, decide where the bucket stops',
             'params': {'cells': [{'d': 1.5}, {'d': 0.5, 'util': True},
                                  {'d': 1.5}, {'d': 0.5, 'util': True}]}},
            {'id': 'nola-below-sea', 'campus': 'new-orleans',
             'name': 'Below-sea trench',
             'brief': 'High water table, one live utility at half depth - '
                      'the flagged cell stops shallow.',
             'teaches': 'a short count per cell, which is exactly when one bite too '
                        'many is easiest to take',
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
             'pass': '== all',
             'fails_when': 'a gate is driven past or taken out of turn, so the lane '
                           'is not run the way it was laid out'},
            {'axis': 'cones', 'measure': 'cones struck',
             'pass': '== 0',
             'fails_when': 'a cone is clipped by the truck, the forks or the load on '
                           'a turn taken too fast or cut too tight'},
            {'axis': 'docking', 'measure': 'pallet inside the dock bay at set-down',
             'pass': 'required',
             'fails_when': 'the pallet is set down outside the bay - short of it, or '
                           'across a line'},
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
            {'id': 'heading', 'label': 'Heading', 'unit': '\u00b0'},
            {'id': 'x', 'label': 'X', 'unit': 'm'},
            {'id': 'z', 'label': 'Z', 'unit': 'm'},
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
        # the course the sim lays out and its operator threads: gate i sits
        # at x = side[i % 2] * gate_x, z = gate_z0 - i * pitch, its cones
        # cone_offset either side; the pallet waits one pitch past the last
        # gate on the centre line; the dock bay is where it is
        'layout': {'gates': {'x': 6, 'z0': -14, 'pitch': 10, 'side': [-1, 1],
                             'cone_offset': 2.6},
                   'dock': [14, -10], 'start': [0, -2]},
        # Regional scenarios: gate count and dock tolerance are the
        # region's lane, declared here; "all gates, no cones" stays the law.
        'scenarios': [
            {'id': 'bay-yard', 'campus': 'treasure-island',
             'name': 'Island yard run',
             'brief': 'The training yard lane - four gates and a full-width '
                      'dock bay to land the pallet in.',
             'teaches': 'the lane itself - four gates in turn, and a bay wide enough to '
                        'forgive the approach',
             'params': {'gates': 4, 'dock_w': 2.2}},
            {'id': 'oak-lane', 'campus': 'oakland',
             'name': 'Terminal container lane',
             'brief': 'A fifth gate threads the container rows - longer '
                      'lane, same clean-run law.',
             'teaches': 'a fifth gate: one more direction change before the pallet, and '
                        'a return lane longer than the habit expects',
             'params': {'gates': 5, 'dock_w': 2.2}},
            {'id': 'nola-dock', 'campus': 'new-orleans',
             'name': 'Wharf dock set',
             'brief': 'The wharf dock is narrow - four gates, then a '
                      'set-down with little room to be wrong.',
             'teaches': 'the set-down - a bay a third narrower, so the squaring up has '
                        'to be done before the truck arrives at it',
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
             'pass': '== all',
             'fails_when': 'the arc is broken before the seam is finished, or a '
                           'segment is travelled over too fast to fuse at all'},
            {'axis': 'band', 'measure': 'share of fused segments laid with the '
                                        'gap inside the band (%)',
             'pass': '>= 90',
             'fails_when': 'the gap is held outside the band for more than a tenth '
                           'of the fused length'},
            {'axis': 'burns', 'measure': 'burn-throughs from lingering heat',
             'pass': '== 0',
             'fails_when': 'the torch dwells on one segment long enough for the heat '
                           'to open the plate'},
            {'axis': 'time', 'measure': 'seconds first strike to last fuse',
             'pass': 'informational'},
        ],
        # marine-pipe runs the same shipboard/dockside pipe seams shipfitters
        # and pipeline already train here; tank-erectors weld the plate
        # seams on every tank they set
        'halls': ['welders', 'boilermakers', 'shipfitters', 'fabricators',
                  'pipeline', 'marine-pipe', 'tank-erectors'],
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
             'teaches': 'the travel rhythm, on the widest gap band this bench offers ',
                        'params': {'segs': 10, 'band': [2.0, 5.0]}},
            {'id': 'oak-flange-bead', 'campus': 'oakland',
             'name': 'Pipe flange bead',
             'brief': 'A longer run at a tighter gap - the plant '
                      'inspector reads every millimetre of it.',
             'teaches': 'the same rhythm with half a millimetre less room, held two '
                        'segments longer',
             'params': {'segs': 12, 'band': [2.0, 4.5]}},
            {'id': 'nola-tank-seam', 'campus': 'new-orleans',
             'name': 'Tank shell seam',
             'brief': 'Storage-tank shell plate in Gulf humidity - a '
                      'slightly higher band, the same clean-bead law.',
             'teaches': 'a band that sits higher off the plate - the hand that learned '
                        'the deck seam has to move, not just hold',
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
             'pass': '== 0',
             'fails_when': 'a part is offered from a rack whose stage has not come - '
                           'a plank before the braces are pinned, a rail before the '
                           'deck is laid'},
            # `complete` WAS a pass gate and could never fail. The bay run ends
            # when the last part goes on and at no other moment, so the axis was
            # grading the run's own terminating condition: every finished run
            # scored it all-placed, and an unfinished one produced no score at
            # all. A gate no run can fail is not a gate, so it is reported here
            # and not gated; `sequence` is what a bay is actually graded on, and
            # the rails-last law it enforces is the same law this axis was
            # claiming to hold. Making it a gate again is a SEAT change, not a
            # rubric one - the bay would have to be signable before it is built,
            # which is what the walkaround's scaffold tag is about.
            {'axis': 'complete', 'measure': 'parts of the bay placed, rails last',
             'pass': 'informational'},
            {'axis': 'time', 'measure': 'seconds first sill to last rail',
             'pass': 'informational'},
        ],
        # every trade added below does its own real work standing on a
        # scaffold bay at height - the whole rest of the envelope district
        # that was not already covered, plus the refractory crews who
        # stage the same way inside a furnace or kiln shell
        'halls': ['scaffold', 'carpenters', 'laborers', 'bricklayers',
                  'painters', 'glaziers', 'roofers', 'cement-masons',
                  'insulators', 'plasterers', 'waterproofers', 'firestop',
                  'cladding', 'masonry-restore', 'curtainwall',
                  'window-glazing', 'lathers', 'stone-carvers', 'refractory'],
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
             'teaches': 'the order itself, on the shortest bay the yard builds ',
                        'params': {'planks': 3, 'rails': 2}},
            {'id': 'oak-plant-bay', 'campus': 'oakland',
             'name': 'Plant maintenance bay',
             'brief': 'A wider bay against the plant wall - four planks '
                      'to deck before anyone stands the lift.',
             'teaches': 'a longer plank stage - one more deck to lay before the rack '
                        'will offer a rail at all',
             'params': {'planks': 4, 'rails': 2}},
            {'id': 'nola-storm-bay', 'campus': 'new-orleans',
             'name': 'Storm-hardening bay',
             'brief': 'Hurricane-season work - a third rail goes on, and '
                      'the same legal order holds in the wind.',
             'teaches': 'a third rail: the last stage runs longer than the hand '
                        'expects, so the bay is not done where it usually is',
             'params': {'planks': 3, 'rails': 3}},
        ],
    },
    'rigging-signals': {
        'name': 'Rigging Signal Call',
        'kind': 'process',
        'task': 'You are the signalperson: the lift card calls the moves, '
                'and the crane follows YOUR hands. Give each called signal '
                'in order — a wrong signal counts against you and the '
                'crane holds — and finish the lift with the stop signal.',
        'controls': [
            {'keys': 'Q / E', 'action': 'signal hoist up / hoist down'},
            {'keys': 'A / D', 'action': 'signal swing left / swing right'},
            {'keys': 'W / S', 'action': 'signal trolley out / trolley in'},
            {'keys': 'Space', 'action': 'signal STOP'},
        ],
        'rubric': [
            {'axis': 'calls', 'measure': 'called signals given, in order',
             'pass': '== all',
             'fails_when': 'the card ends with calls unsigned - a stop given before '
                           'the last called move was made'},
            {'axis': 'wrong', 'measure': 'signals given out of turn',
             'pass': '== 0',
             'fails_when': 'a signal the card did not call for is given, while the '
                           'crane is holding on the one it did'},
            {'axis': 'time', 'measure': 'seconds first signal to stop',
             'pass': 'informational'},
        ],
        # the same real crews the crane-lift sim above now trains, signing
        # the same picks by hand before the machine ever moves
        'halls': ['riggers', 'crane-ops', 'steel-erectors', 'port-crane',
                  'millwrights', 'ironworkers', 'decking', 'tank-erectors',
                  'piling'],
        'skill_strand': 'machines',
        'skill_tier': 'applied',
        'dash': [
            {'id': 'step', 'label': 'Step', 'unit': ''},
            {'id': 'called', 'label': 'Called', 'unit': ''},
            {'id': 'given', 'label': 'Given', 'unit': ''},
            {'id': 'wrong', 'label': 'Wrong', 'unit': '', 'warn_at': 1},
            {'id': 'time', 'label': 'T', 'unit': 's'},
        ],
        'audio': {'engine': 'hoist',
                  'alerts': ['signal-whistle', 'wrong-buzz', 'result-chime'],
                  'note': 'synthesized in-page (WebAudio); no recordings shipped'},
        'haptics': ['wrong', 'finish'],
        'view_modes': ['orbit', 'signal'],
        # Regional scenarios: the lift card is the yard's own - longer
        # sequences, more direction changes; the call law never varies.
        'scenarios': [
            {'id': 'bay-first-card', 'campus': 'treasure-island',
             'name': 'First lift card',
             'brief': 'The training card: five calls, one direction '
                      'change, the stop to finish - learn the hands.',
             'teaches': 'the hands themselves - five calls and one direction change ',
                        'params': {'seq': ['up', 'swing-r', 'out', 'down', 'stop']}},
            {'id': 'oak-blind-pick', 'campus': 'oakland',
             'name': 'Blind terminal pick',
             'brief': 'The operator cannot see this load - six calls '
                      'thread it out of the container shadow.',
             'teaches': 'a retrieval move before the swing on a pick the operator '
                        'cannot see: the card, not the load, is what you read',
             'params': {'seq': ['up', 'in', 'swing-l', 'out', 'down',
                                'stop']}},
            {'id': 'nola-wind-card', 'campus': 'new-orleans',
             'name': 'River-wind card',
             'brief': 'The river breeze wants the load moving - six '
                      'calls with two swings hold the line to the set.',
             'teaches': 'two swings in opposite directions - the card doubles back, and '
                        'a hand that anticipates gives the wrong one',
             'params': {'seq': ['up', 'swing-r', 'out', 'swing-l', 'down',
                                'stop']}},
        ],
    },
    'load-chart': {
        'name': 'Load Chart Judgment',
        'kind': 'process',
        'task': 'Work the pick list against the chart on the board: at '
                'each radius the crane has one honest number. Hook the '
                'picks the chart allows and refuse the ones it does not — '
                'an overweight pick accepted is the failure that matters.',
        'controls': [
            {'keys': 'Space', 'action': 'accept the pick - hook it'},
            {'keys': 'X', 'action': 'refuse the pick - over the chart'},
            {'keys': 'Q / E', 'action': 'walk the chart rows'},
        ],
        'rubric': [
            {'axis': 'judgments', 'measure': 'picks judged with the chart',
             'pass': '== all',
             'fails_when': 'a pick is called wrong either way - one the chart allows '
                           'refused, or one it does not allow accepted'},
            {'axis': 'overloads', 'measure': 'overweight picks accepted',
             'pass': '== 0',
             'fails_when': 'a pick heavier than the chart line at its own radius is '
                           'hooked anyway'},
            {'axis': 'time', 'measure': 'seconds first judgment to last',
             'pass': 'informational'},
        ],
        # the two structural trades who plan a pick against a load chart
        # before the crane-lift sim above ever swings the jib
        'halls': ['crane-ops', 'riggers', 'port-crane', 'heavy-equip',
                  'operating-eng', 'ironworkers', 'tank-erectors'],
        'skill_strand': 'machines',
        'skill_tier': 'applied',
        # The machine's one honest chart: capacity falls as radius grows.
        # Scenarios vary the pick list only; the chart is the machine's.
        'chart': [[4, 8.0], [6, 5.2], [8, 3.6], [10, 2.4], [12, 1.6]],
        'dash': [
            {'id': 'pick', 'label': 'Pick', 'unit': ''},
            {'id': 'load', 'label': 'Load', 'unit': 't'},
            {'id': 'radius', 'label': 'Radius', 'unit': 'm'},
            {'id': 'chart', 'label': 'Chart', 'unit': 't'},
            {'id': 'errors', 'label': 'Errors', 'unit': '', 'warn_at': 1},
            {'id': 'time', 'label': 'T', 'unit': 's'},
        ],
        'audio': {'engine': 'hoist',
                  'alerts': ['overload-alarm', 'hook-click', 'result-chime'],
                  'note': 'synthesized in-page (WebAudio); no recordings shipped'},
        'haptics': ['overload', 'finish'],
        'view_modes': ['orbit', 'chart'],
        'scenarios': [
            {'id': 'bay-pick-list', 'campus': 'treasure-island',
             'name': 'Yard pick list',
             'brief': 'Five picks off the training pad - one of them is '
                      'over the chart, and the chart wins.',
             'teaches': 'reading the chart line at a radius, with one pick over and '
                        'four inside it',
             'params': {'picks': [
                 {'w': 3.0, 'r': 4}, {'w': 4.8, 'r': 6}, {'w': 4.1, 'r': 8},
                 {'w': 2.0, 'r': 10}, {'w': 1.2, 'r': 12}]}},
            {'id': 'oak-heavy-list', 'campus': 'oakland',
             'name': 'Terminal heavy list',
             'brief': 'Six terminal picks, two of them over - the '
                      'foreman will push, the chart will not.',
             'teaches': 'the same radius twice with different answers - 6 m carries one '
                        'of these picks and refuses the other',
             'params': {'picks': [
                 {'w': 7.5, 'r': 4}, {'w': 6.0, 'r': 6}, {'w': 3.6, 'r': 8},
                 {'w': 3.0, 'r': 10}, {'w': 1.5, 'r': 12}, {'w': 5.0, 'r': 6}]}},
            {'id': 'nola-barge-list', 'campus': 'new-orleans',
             'name': 'Barge transfer list',
             'brief': 'Five barge picks with two over the chart - the '
                      'river will not forgive the one you talk into.',
             'teaches': 'a pick exactly on the chart line opens the list, because at '
                        'the number is inside it - two later picks are not',
             'params': {'picks': [
                 {'w': 8.0, 'r': 4}, {'w': 5.8, 'r': 6}, {'w': 2.4, 'r': 10},
                 {'w': 4.0, 'r': 8}, {'w': 1.5, 'r': 12}]}},
        ],
    },
    'pressure-washer': {
        'name': 'Pressure Washer Surface Clean',
        'kind': 'process',
        'task': 'Strip the fouling off the marked test panel to a clean '
                'finish — sweep the wand cell by cell and hold your '
                'standoff; crowd the surface and linger and the substrate '
                'gouges. Set the containment berm before you ever pull the '
                'trigger, not after.',
        'controls': [
            {'keys': 'A / D', 'action': 'sweep the wand left / right across the panel'},
            {'keys': 'W / S', 'action': 'sweep the wand up / down across the panel'},
            {'keys': 'Q / E', 'action': 'stand off farther / move closer to the surface'},
            {'keys': 'Space', 'action': 'pull / release the spray trigger'},
            {'keys': 'C', 'action': 'deploy the containment berm / drain cover'},
        ],
        'rubric': [
            {'axis': 'coverage', 'measure': 'share of the panel surface cleaned (%)',
             'pass': '>= 95',
             'fails_when': 'the pass ends with fouling still on the panel, or with '
                           'cells cut past cleaning by the wand'},
            {'axis': 'damage', 'measure': 'substrate gouges from spraying too '
                                          'close or lingering too long',
             'pass': '== 0',
             'fails_when': 'the wand is crowded inside the damage distance and held '
                           'there until the substrate cuts'},
            {'axis': 'containment', 'measure': 'containment berm or drain cover '
                                               'deployed before the first spray',
             'pass': 'required',
             'fails_when': 'the trigger is pulled before the berm or the drain cover '
                           'is set - setting it afterwards does not count'},
            {'axis': 'time', 'measure': 'seconds first spray to last clean cell',
             'pass': 'informational'},
        ],
        # painters run the coatings/containment/industrial-finish envelope
        # work this bench trains; laborers set the same containment and
        # runoff control on the ground; hazmat owns the environmental
        # discipline the containment axis is actually testing
        'halls': ['painters', 'laborers', 'hazmat'],
        'skill_strand': 'machines',
        'skill_tier': 'applied',
        'dash': [
            {'id': 'u', 'label': 'Across', 'unit': 'm'},
            {'id': 'v', 'label': 'Up', 'unit': 'm'},
            {'id': 'gap', 'label': 'Standoff', 'unit': 'm'},
            {'id': 'coverage', 'label': 'Clean', 'unit': '%'},
            {'id': 'damage', 'label': 'Damage', 'unit': '', 'warn_at': 1},
            {'id': 'containment', 'label': 'Contain', 'unit': ''},
            {'id': 'time', 'label': 'T', 'unit': 's'},
        ],
        'audio': {'engine': 'pump',
                  'alerts': ['spray-hiss', 'breach-alarm', 'result-chime'],
                  'note': 'synthesized in-page (WebAudio); no recordings shipped'},
        'haptics': ['damage', 'breach', 'finish'],
        'view_modes': ['orbit', 'wand'],
        # the panel grid and the standoff window the sim and its operator
        # share: cells are `cell` m square from the panel's bottom-left; the
        # jet only works inside effective_max and gouges under damage_under
        'layout': {'cell': 0.62,
                   'standoff': {'effective_max': 1.6, 'damage_under': 0.55}},
        # Regional scenarios: the fouled panel is the region's own; "95%
        # clean, zero gouges, containment first" stays the law everywhere.
        'scenarios': [
            {'id': 'bay-seawall-clean', 'campus': 'treasure-island',
             'name': 'Ferry terminal seawall',
             'brief': 'Graffiti on the ferry terminal seawall panel - a '
                      'forgiving concrete face to learn the sweep on.',
             'teaches': 'the sweep pattern on a forgiving face: standoff held, rows '
                        'walked, containment set before the trigger',
             'params': {'cols': 6, 'rows': 4}},
            {'id': 'oak-bulkhead-clean', 'campus': 'oakland',
             'name': 'Terminal bulkhead fouling',
             'brief': 'Rust bloom on a steel bulkhead panel at the marine '
                      'terminal - a wider panel, the same clean-cell law.',
             'teaches': 'a wider panel - a longer row is more chances for the standoff '
                        'to drift before the row ends',
             'params': {'cols': 7, 'rows': 4}},
            {'id': 'nola-floodwall-clean', 'campus': 'new-orleans',
             'name': 'Levee floodwall mildew',
             'brief': 'Gulf humidity grows mildew fast on the floodwall '
                      'panel - a taller face, containment matters more here.',
             'teaches': 'a taller face: the rows run out of comfortable reach, and the '
                        'standoff is the first thing the arm gives up',
             'params': {'cols': 6, 'rows': 5}},
        ],
    },
    'airless-sprayer': {
        'name': 'Airless Paint Sprayer Finish',
        'kind': 'process',
        'task': 'Lay one even finish coat across the marked panel inside '
                'the masked line — hold your standoff and travel steady; '
                'crowd the surface or linger and the coat runs, rush a '
                'cell and it stays a holiday, and drift past the mask is '
                'overspray either way.',
        'controls': [
            {'keys': 'A / D', 'action': 'sweep the gun left / right across the panel'},
            {'keys': 'W / S', 'action': 'sweep the gun up / down across the panel'},
            {'keys': 'Q / E', 'action': 'stand off farther / move closer to the surface'},
            {'keys': 'Space', 'action': 'pull / release the spray trigger'},
        ],
        'rubric': [
            {'axis': 'coverage', 'measure': 'share of the panel evenly coated (%)',
             'pass': '>= 95',
             'fails_when': 'the pass ends with bare cells, or with cells spoiled by a '
                           'run and never made good'},
            {'axis': 'runs', 'measure': 'drips from spraying too close or too slow',
             'pass': '== 0',
             'fails_when': 'the gun is crowded inside the run distance, or travelled '
                           'so slowly the film sags'},
            {'axis': 'holidays', 'measure': 'missed spots left uncoated',
             'pass': '== 0',
             'fails_when': 'a cell is left bare when the pass ends - a gap between '
                           'rows, or a turn started early'},
            {'axis': 'overspray', 'measure': 'spray drift past the masked boundary',
             'pass': '== 0',
             'fails_when': 'the trigger is held through a turn that carries the gun '
                           'outside the masked line'},
            {'axis': 'time', 'measure': 'seconds first spray to last coated cell',
             'pass': 'informational'},
        ],
        # painters run the finish-coat work this bench trains; laborers
        # hang the same drop-cloth and masking containment on every job
        'halls': ['painters', 'laborers'],
        'skill_strand': 'machines',
        'skill_tier': 'applied',
        'dash': [
            {'id': 'u', 'label': 'Across', 'unit': 'm'},
            {'id': 'v', 'label': 'Up', 'unit': 'm'},
            {'id': 'gap', 'label': 'Standoff', 'unit': 'm'},
            {'id': 'coverage', 'label': 'Coat', 'unit': '%'},
            {'id': 'runs', 'label': 'Runs', 'unit': '', 'warn_at': 1},
            {'id': 'holidays', 'label': 'Holidays', 'unit': '', 'warn_at': 1},
            {'id': 'overspray', 'label': 'Overspray', 'unit': '', 'warn_at': 1},
            {'id': 'time', 'label': 'T', 'unit': 's'},
        ],
        'audio': {'engine': 'pump',
                  'alerts': ['overspray-alarm', 'run-buzz', 'result-chime'],
                  'note': 'synthesized in-page (WebAudio); no recordings shipped'},
        'haptics': ['run', 'overspray', 'finish'],
        'view_modes': ['orbit', 'spray'],
        # the same grid and standoff window as the washer bench, plus the
        # masked margin past the paintable boundary
        'layout': {'cell': 0.62, 'mask': 0.3,
                   'standoff': {'effective_max': 1.6, 'damage_under': 0.55}},
        # Regional scenarios: the wall is the region's own; "95% coat, no
        # runs, no holidays, no overspray" stays the law everywhere.
        'scenarios': [
            {'id': 'bay-terminal-finish', 'campus': 'treasure-island',
             'name': 'Ferry terminal finish coat',
             'brief': 'A fresh finish coat on the terminal exterior wall - '
                      'the forgiving panel to learn the pass rhythm on.',
             'teaches': 'the pass rhythm - dwell long enough to coat, turn inside the '
                        'mask',
             'params': {'cols': 6, 'rows': 4}},
            {'id': 'oak-warehouse-finish', 'campus': 'oakland',
             'name': 'Dockside warehouse finish',
             'brief': 'A wider warehouse wall panel at the terminal - '
                      'more travel, the same even-coat law.',
             'teaches': 'a wider wall, so the turns come later - which is where an even '
                        'coat is usually lost',
             'params': {'cols': 7, 'rows': 4}},
            {'id': 'nola-shotgun-finish', 'campus': 'new-orleans',
             'name': 'Shotgun house finish coat',
             'brief': 'A taller shotgun-house exterior wall panel - '
                      'humidity punishes a slow pass, hold the rhythm.',
             'teaches': 'a taller wall: more rows, and the last one has to lay down the '
                        'same film as the first',
             'params': {'cols': 6, 'rows': 5}},
        ],
    },
    'boom-lift': {
        'name': 'Boom Lift Basket Work',
        'kind': 'machine',
        'task': 'Set the stabilizers on the level pad, clip your harness to '
                'the basket anchor, then take the basket to every marked '
                'work point in order and back down — keeping the load '
                'moment under the line the whole way and the basket out of '
                'the overhead-line exclusion zone.',
        'controls': [
            {'keys': 'A / D', 'action': 'swing the turret'},
            {'keys': 'W / S', 'action': 'extend / retract the boom'},
            {'keys': 'Q / E', 'action': 'raise / lower the boom'},
            {'keys': 'Space', 'action': 'clip the harness (on the ground) / '
                                        'do the task at the work point'},
            {'keys': 'C', 'action': 'set the stabilizers on the pad'},
        ],
        'rubric': [
            {'axis': 'reach', 'measure': 'marked work points the basket was '
                                         'brought to, within tolerance, in order',
             'pass': '== all',
             'fails_when': 'the basket comes down with points unvisited, or a point '
                           'is passed without ever being held inside its tolerance'},
            {'axis': 'envelope', 'measure': 'load-moment envelope exceedances '
                                            '(outreach x platform load over '
                                            'the rated moment)',
             'pass': '== 0',
             'fails_when': 'the boom is extended until outreach times the platform '
                           'load passes the rated moment'},
            {'axis': 'tie-off', 'measure': 'harness clipped before the basket '
                                           'left the ground',
             'pass': 'required',
             'fails_when': 'the basket leaves the ground with the harness unclipped - '
                           'clipping it in the air is clipping it late'},
            {'axis': 'slope', 'measure': 'stabilizers set on the level pad '
                                         'before the first lift',
             'pass': 'required',
             'fails_when': 'the basket leaves the ground before the stabilizers are '
                           'down - setting them afterwards is setting them late'},
            {'axis': 'strikes', 'measure': 'basket entries into the overhead-'
                                           'line exclusion zone',
             'pass': '== 0',
             'fails_when': 'the basket is taken into the exclusion cylinder around '
                           'the overhead line instead of over it'},
            {'axis': 'time', 'measure': 'seconds tie-off to stowed',
             'pass': 'informational'},
        ],
        # every hall below does its own real work standing in an aerial
        # platform basket: overhead conduit and fixtures, glazing and
        # curtain-wall panels, exterior coatings, bolting up at height,
        # architectural metal and duct, and insulation on overhead runs
        'halls': ['electricians', 'glaziers', 'window-glazing', 'painters',
                  'ironworkers', 'steel-erectors', 'sheetmetal', 'insulators'],
        'skill_strand': 'machines',
        'skill_tier': 'applied',
        'dash': [
            {'id': 'height', 'label': 'Height', 'unit': 'm'},
            {'id': 'outreach', 'label': 'Outreach', 'unit': 'm'},
            {'id': 'swing', 'label': 'Swing', 'unit': '°'},
            {'id': 'elev', 'label': 'Boom', 'unit': '°'},
            {'id': 'moment', 'label': 'Moment', 'unit': '%', 'warn_at': 90},
            {'id': 'tieoff', 'label': 'Tie-off', 'unit': ''},
            {'id': 'stab', 'label': 'Stabs', 'unit': ''},
            {'id': 'points', 'label': 'Points', 'unit': ''},
            {'id': 'time', 'label': 'T', 'unit': 's'},
        ],
        'audio': {'engine': 'electric-hydraulic',
                  'alerts': ['limit-alarm', 'zone-alarm', 'result-chime'],
                  'note': 'synthesized in-page (WebAudio); no recordings shipped'},
        'haptics': ['limit', 'strike', 'finish'],
        'view_modes': ['orbit', 'basket'],
        # the yard geometry the sim and its operator share: the pad the
        # machine stands on (turret pivot height and boom lengths), the
        # rated moment the envelope is judged against with the platform
        # load, the transit elevation at which a fully extended boom still
        # sits inside the envelope, and the tolerance a work point counts at
        'layout': {'pivot_y': 1.9, 'boom_min': 5.0, 'boom_max': 14.0,
                   'elev_max_deg': 78, 'rated_moment': 2100, 'load_kg': 230,
                   'transit_elev_deg': 75, 'point_tol': 0.9, 'stow_h': 2.6},
        # Regional scenarios: the work-point run and the overhead line are
        # the region's own; the envelope and the tie-off law never vary.
        'scenarios': [
            {'id': 'bay-curtainwall-run', 'campus': 'treasure-island',
             'name': 'Curtain-wall panel run',
             'brief': 'Six anchor points up a curtain-wall bay on the island '
                      'campus, with the site power drop strung across in '
                      'front of them - the run to learn the basket on, and '
                      'the first thing to learn is that it is not clear '
                      'overhead.',
             'teaches': 'the basket itself - six points in two courses, with a '
                        'temporary power drop across the bay to go over',
             'params': {'points': [[-3.5, 7, 7], [0, 7, 7], [3.5, 7, 7],
                                   [3.5, 9.5, 7], [0, 9.5, 7], [-3.5, 9.5, 7]],
                        'line': {'z': 4.5, 'y': 6.0, 'r': 1.6}}},
            {'id': 'oak-terminal-fixtures', 'campus': 'oakland',
             'name': 'Terminal light-fixture run',
             'brief': 'Four fixture points along a terminal canopy with a '
                      'live feeder running overhead between the pad and the '
                      'work - go up before you go out.',
             'teaches': 'a live feeder between the pad and the work: up to transit '
                        'height before out, on every point',
             'params': {'points': [[-4, 9, 7], [-1.5, 9, 7], [1.5, 9, 7],
                                   [4, 9, 7]],
                        'line': {'z': 3.5, 'y': 6.0, 'r': 2.0}}},
            {'id': 'nola-storm-shutters', 'campus': 'new-orleans',
             'name': 'Storm-shutter run',
             'brief': 'Five shutter anchors low on a warehouse wall before '
                      'the season turns, with a service drop overhead - '
                      'short reaches, the same tie-off law.',
             'teaches': 'low work under a service drop - the reaches are short, so '
                        'going straight at them is the tempting mistake',
             'params': {'points': [[-4, 5, 7], [-2, 5, 7], [0, 5, 7],
                                   [2, 5, 7], [4, 5, 7]],
                        'line': {'z': 3.5, 'y': 6.0, 'r': 1.8}}},
        ],
    },
    'overhead-crane': {
        'name': 'Overhead Crane Shop Move',
        'kind': 'machine',
        'task': 'Hook the load, hoist it to carry height, travel the bridge '
                'and then the trolley along the marked route — never over '
                'the pedestrian aisle or the workstation, always above the '
                'obstacles — and set it down inside the target square, '
                'sway under control the whole way.',
        'controls': [
            {'keys': 'A / D', 'action': 'travel the bridge'},
            {'keys': 'W / S', 'action': 'traverse the trolley'},
            {'keys': 'Q / E', 'action': 'hoist up / down'},
            {'keys': 'Space', 'action': 'hook / release the load'},
        ],
        'rubric': [
            {'axis': 'placement', 'measure': 'distance from the target centre at set-down (m)',
             'pass': '<= 0.5',
             'fails_when': 'the load is released outside the square, or while it is '
                           'still swinging across it'},
            {'axis': 'sway', 'measure': 'peak load swing during travel (m)',
             'pass': '<= 0.6',
             'fails_when': 'bridge and trolley are driven while the load is already '
                           'moving, or both at once on the diagonal'},
            {'axis': 'path', 'measure': 'loaded passes over the pedestrian aisle '
                                        'or the workstation exclusion zone',
             'pass': '== 0',
             'fails_when': 'the loaded route is taken across the aisle or the '
                           'workstation rather than around them'},
            {'axis': 'limits', 'measure': 'hoist upper-limit (two-block) hits',
             'pass': '== 0',
             'fails_when': 'the hoist is run up into its upper limit instead of '
                           'stopped at a carry height short of it'},
            {'axis': 'clear', 'measure': 'load carried above every obstacle it '
                                         'crossed',
             'pass': 'required',
             'fails_when': 'the load is travelled at a height that does not clear '
                           'something on the route it crosses'},
            {'axis': 'time', 'measure': 'seconds hook to release',
             'pass': 'informational'},
        ],
        # the crane hall's own focus names overhead lifting outright; the
        # shop trades below are who a bridge crane actually moves coils,
        # castings, vessels and machine beds for, and who rigs the pick
        'halls': ['crane-ops', 'millwrights', 'machinists', 'foundry',
                  'boilermakers', 'riggers', 'port-crane'],
        'skill_strand': 'machines',
        'skill_tier': 'applied',
        'dash': [
            {'id': 'bridge', 'label': 'Bridge', 'unit': 'm'},
            {'id': 'trolley', 'label': 'Trolley', 'unit': 'm'},
            {'id': 'hook', 'label': 'Hook', 'unit': 'm'},
            {'id': 'sway', 'label': 'Sway', 'unit': 'm', 'warn_at': 0.45},
            {'id': 'load', 'label': 'Load', 'unit': '%'},
            {'id': 'time', 'label': 'T', 'unit': 's'},
        ],
        'audio': {'engine': 'hoist-motor',
                  'alerts': ['bridge-rumble', 'limit-alarm', 'result-chime'],
                  'note': 'synthesized in-page (WebAudio); no recordings shipped'},
        'haptics': ['limit', 'incursion', 'finish'],
        'view_modes': ['orbit', 'pendant'],
        # the bay geometry the sim and its operator share: half-extents of
        # the runway, the hook's travel, the carry height (a HOOK height;
        # the load's underside hangs `hang` below it) every obstacle sits
        # under by `clearance`, and where the pedestrian aisle runs. The
        # pickup, target, obstacles and workstation are the scenario's own.
        'layout': {'bay': [12, 8], 'hook_max': 7.0, 'hook_min': 0.4,
                   'carry_h': 5.0, 'hang': 2.0, 'clearance': 0.3,
                   'capacity_t': 5.0,
                   'aisle': {'x': [-12, 4], 'z': [1.5, 3.5]}},
        # Regional scenarios: the shop floor is the region's own; "inside
        # the square, sway low, nothing over the aisle" stays the law.
        'scenarios': [
            {'id': 'bay-fab-coil', 'campus': 'treasure-island',
             'name': 'Fabrication-shop coil move',
             'brief': 'A steel coil from the receiving pad to the slitter '
                      'stand across the island fab shop - one bench to '
                      'clear, the aisle to stay off.',
             'teaches': 'the route - one bench to carry over and an aisle the straight '
                        'line would cross',
             'params': {'pickup': [-8, -5], 'target': [6, 6], 'load_t': 3.2,
                        'obstacles': [{'x': 8, 'z': 0, 'w': 3, 'd': 2.4, 'h': 1.6}],
                        'workstation': {'x': [-4, 1], 'z': [4, 7]}}},
            {'id': 'oak-foundry-ladle', 'campus': 'oakland',
             'name': 'Foundry ladle-frame move',
             'brief': 'A ladle frame from the pour line to the maintenance '
                      'bay at the Oakland foundry - two mould stacks under '
                      'the route, carry high.',
             'teaches': 'two obstacles at different heights under the heaviest load the '
                        'bay takes: the tallest sets the carry, not the nearest',
             'params': {'pickup': [-9, -4], 'target': [7, 5], 'load_t': 4.5,
                        'obstacles': [{'x': -2, 'z': -4, 'w': 3, 'd': 3, 'h': 2.0},
                                      {'x': 7, 'z': 0, 'w': 2.6, 'd': 2.6, 'h': 1.8}],
                        'workstation': {'x': [-3, 2], 'z': [4.5, 7]}}},
            {'id': 'nola-boatshed-engine', 'campus': 'new-orleans',
             'name': 'Boat-shed engine move',
             'brief': 'A marine engine from the crate to the test stand in a '
                      'Gulf boat shed - a narrow bay, a tight square, the '
                      'crew aisle right through the middle.',
             'teaches': 'a tight square in a narrow bay with the crew aisle through the '
                        'middle - bridge, then trolley, never the diagonal',
             'params': {'pickup': [-8, -5], 'target': [5, 6], 'load_t': 2.4,
                        'obstacles': [{'x': 0, 'z': -5, 'w': 4, 'd': 2.6, 'h': 1.9}],
                        'workstation': {'x': [-5, 0], 'z': [4.5, 7]}}},
        ],
    },
}

# The in-headset control mapping, declared ONCE here per seat and read by
# the page's controller adapter (web/build_3d.py, XR block): the same
# key state a keyboard fills, so a seat cannot tell a thumbstick from a
# key. The prose is what the wiki and the wrist panel show; `grip_key` is
# the one machine-readable field - the seat's secondary edge key, where it
# has one - derived below from the seat's own controls list, never typed.
def xr_mapping(sim):
    single = [c for c in sim['controls'] if len(c['keys']) == 1 and c['keys'] in 'CXR']
    grip = single[0] if single else None
    verbs = {c['keys']: c['action'] for c in sim['controls']}
    return {
        'left_stick': 'W/S on the y axis, A/D on the x axis - '
                      + (verbs.get('W / S', 'no W/S verb on this seat')
                         + '; ' + verbs.get('A / D', 'no A/D verb on this seat')),
        'right_stick': ('Q/E on the x axis - ' + verbs['Q / E']) if 'Q / E' in verbs
                       else 'unused on this seat (no Q/E verb)',
        'trigger': 'Space, on the press edge - ' + verbs['Space'],
        'grip': (f"{grip['keys']}, held - {grip['action']}") if grip
                else 'unused on this seat (no secondary key)',
        'grip_key': f"Key{grip['keys']}" if grip else None,
        'primary': 'A / X button: start or stop watching the scripted '
                   'reference operator drive this seat, at the level the '
                   'HUD last selected',
        'secondary': 'B / Y button: leave the seat',
    }
for sim_id, sim in SIMS.items():
    sim['xr'] = xr_mapping(sim)
    assert sim['xr']['trigger'] and sim['xr']['left_stick'], f'{sim_id}: xr mapping'

# The pre-shift walkaround: five looks per machine, the habit that finds
# the fault before the shift does. DELIBERATELY NOT A GATE - the honesty
# note below says so and the suite asserts it: no seat is locked behind
# the walkaround and completing it changes no score.
WALKAROUNDS = {
    'crane-lift': [
        {'id': 'rope', 'point': 'Hoist rope and hook',
         'check': 'no broken wires or kinks, and the safety latch closes',
         'on_fault': 'the hook is out of service until the rope is changed - '
                     'broken wires and a latch that will not close are not run out'},
        {'id': 'slew-ring', 'point': 'Slew ring and bolts',
         'check': 'no missing or backed-off bolts at the ring',
         'on_fault': 'nothing slews: a ring bolt backed off is a crane down for '
                     'the mechanic, not a note for the end of the shift'},
        {'id': 'counterweight', 'point': 'Counterweight',
         'check': 'seated and pinned exactly as the configuration the chart on '
                  'the board is written for - blocks counted, not glanced at',
         'on_fault': 'nothing lifts, because a counterweight that is not the '
                     'configured one makes the chart on the board the wrong chart'},
        {'id': 'limits', 'point': 'Limit switches',
         'check': 'hoist and trolley limits trip before the steel does',
         'on_fault': 'test again cold, and if a limit still does not trip the '
                     'crane stays parked - the steel is not a limit switch'},
        {'id': 'base', 'point': 'Base and ballast',
         'check': 'bearing is even, no washout or standing water',
         'on_fault': 'stop and raise it: washout or standing water under a base is '
                     'a ground problem, and no lift is small enough to risk on one'},
    ],
    'excavator-trench': [
        {'id': 'tracks', 'point': 'Tracks and rollers',
         'check': 'tension right, no cut pads or leaking rollers',
         'on_fault': 'park it - a leaking roller or a cut pad gets fixed between '
                     'shifts, not during one'},
        {'id': 'bucket', 'point': 'Bucket teeth and pins',
         'check': 'teeth tight, pins keepered, no cracks at the ears',
         'on_fault': 'change the tooth or the pin before the first bite; a tooth '
                     'lost in a trench is a search and a shutdown'},
        {'id': 'hoses', 'point': 'Boom hydraulics',
         'check': 'no weeping hoses or chafed lines on the boom',
         'on_fault': 'shut it down, and nobody feels for a hydraulic leak with a '
                     'hand - the weep is the warning'},
        {'id': 'slew-brake', 'point': 'Slew brake',
         'check': 'holds the house still on a test swing with the boom out, '
                  'where the moment on it is worst',
         'on_fault': 'do not dig: a house that creeps under load is a machine '
                     'nobody should be sitting in'},
        {'id': 'edge', 'point': 'The trench edge',
         'check': 'spoil set back, no load surcharging the cut',
         'on_fault': 'pull the spoil back and re-cut the edge before anyone goes '
                     'near the trench, and have the competent person look at it'},
    ],
    'forklift-run': [
        {'id': 'tires', 'point': 'Tires and wheel nuts',
         'check': 'no chunking or cords, every nut marked and tight',
         'on_fault': 'tag it out - cords showing or a nut off its mark is a truck '
                     'off the yard until it is fixed'},
        {'id': 'forks', 'point': 'Fork heels and locks',
         'check': 'no heel wear past the line, both locks seat',
         'on_fault': 'change the forks; heel wear past the line is a measurement, '
                     'not a judgement call'},
        {'id': 'mast', 'point': 'Mast chains',
         'check': 'even tension side to side, no kinked or rusted links, and no '
                  'play worn into the anchor pins',
         'on_fault': 'do not lift - chains are replaced in pairs by the mechanic, '
                     'never straightened and run'},
        {'id': 'horn', 'point': 'Horn and beeper',
         'check': 'horn sounds, the reverse beeper sounds louder',
         'on_fault': 'no horn or no beeper is no run: the yard hears this truck '
                     'before it sees it'},
        {'id': 'guard', 'point': 'Seatbelt and overhead guard',
         'check': 'belt latches, guard unbent and pinned',
         'on_fault': 'stop - a bent guard or a belt that will not latch is the '
                     'whole reason the truck carries either one'},
    ],
    'weld-bead': [
        {'id': 'leads', 'point': 'Leads and clamps',
         'check': 'insulation whole end to end, ground clamp bites clean metal',
         'on_fault': 'no arc until it is changed: damaged insulation and a poor '
                     'ground are the two faults that put current where nobody '
                     'wants it'},
        {'id': 'gas', 'point': 'Gas and regulator',
         'check': 'no leaks at the test pressure, flow set to the procedure',
         'on_fault': 'shut the bottle and fix the leak before anything is struck, '
                     'and ventilate what has already collected'},
        {'id': 'screens', 'point': 'Welding screens',
         'check': 'standing and closed - nobody flashes off your arc',
         'on_fault': 'set them first - the flash that hurts someone is always the '
                     'one they did not know was coming'},
        {'id': 'extraction', 'point': 'Fume extraction',
         'check': 'running and pulling at the work, not past your face',
         'on_fault': 'no extraction, no hot work here; move the work or fix the '
                     'extraction, do not just turn your head'},
        {'id': 'firewatch', 'point': 'Fire watch kit',
         'check': 'extinguisher charged and in reach, combustibles cleared',
         'on_fault': 'clear the combustibles and put a charged extinguisher in '
                     'reach, or the hot work waits and the permit does not open'},
    ],
    'scaffold-bay': [
        {'id': 'sills', 'point': 'Sills and bearing',
         'check': 'full bearing on grade, no blocks or debris packing',
         'on_fault': 're-set on sound bearing - a sill packed up on debris instead '
                     'of borne on grade is where a collapse starts'},
        {'id': 'plumb', 'point': 'Frames plumb and level',
         'check': 'plumb both ways, level across the bay',
         'on_fault': 'take it down to the last level lift and rebuild; a bay out '
                     'of plumb does not come back into plumb further up'},
        {'id': 'brace-pins', 'point': 'Brace pins',
         'check': 'every brace pinned home, none sprung',
         'on_fault': 'stop the build and pin them, because an unpinned brace is a '
                     'brace that is not there'},
        {'id': 'planks', 'point': 'Plank condition',
         'check': 'no cracks, full bearing, cleats where the spec asks',
         'on_fault': 'pull the plank out of the deck and replace it, and nobody '
                     'stands on that bay until it is back'},
        {'id': 'tag', 'point': 'The scaffold tag',
         'check': 'current, signed, and matching what is built',
         'on_fault': 'the bay is out of service until a competent person has seen '
                     'what is built and signed for it'},
    ],
    'rigging-signals': [
        {'id': 'sightline', 'point': 'Line of sight',
         'check': 'the operator can read your hands from every planned position',
         'on_fault': 'move, or put a relay signaller in - a lift does not start on '
                     'a sightline you are hoping will hold'},
        {'id': 'radio', 'point': 'Radio and whistle',
         'check': 'checked both ways on a working channel before the first '
                  'pick, and the channel is one nobody else on the site is on',
         'on_fault': 'no two-way check, no lift; if it goes to hand signals only, '
                     'everybody is told that is what it is'},
        {'id': 'slings', 'point': 'Slings and shackles',
         'check': 'tags legible and in date, pins moused where required',
         'on_fault': 'out of service - an illegible or out-of-date tag is the same '
                     'as no tag at all'},
        {'id': 'path', 'point': 'The load path',
         'check': 'walked end to end, nothing and nobody under it',
         'on_fault': 'change the path or clear it: nothing is lifted over a person '
                     'because walking the long way was inconvenient'},
        {'id': 'zone', 'point': 'Exclusion zone',
         'check': 'barriers set and everyone briefed before the lift',
         'on_fault': 'set the barriers and brief the crew before the hook takes '
                     'weight, not while it is taking it'},
    ],
    'load-chart': [
        {'id': 'chart', 'point': 'The chart itself',
         'check': "legible, this machine's own configuration, not another's",
         'on_fault': 'stop - the wrong chart is the most expensive piece of paper '
                     'on the job'},
        {'id': 'radius-marks', 'point': 'Radius markers',
         'check': 'set out and measured from the centre of rotation, not paced '
                  'off and not read from the drawing',
         'on_fault': 'measure them, or take the pick off the list; the chart does '
                     'not accept a paced radius'},
        {'id': 'bearing', 'point': 'Ground bearing',
         'check': 'pads sized for the worst pick on the list',
         'on_fault': 'size the pads for the worst pick on the list, or that pick '
                     'comes off the list'},
        {'id': 'wind', 'point': 'Wind check',
         'check': 'inside the chart notes for the largest sail area',
         'on_fault': 'over the chart note, the pick waits - the wind is not '
                     'something the foreman can overrule'},
        {'id': 'hook', 'point': 'Hook block',
         'check': 'latch closes, swivel free, sheaves turning true',
         'on_fault': 'change the block: a latch that does not close is how a sling '
                     'walks off a hook'},
    ],
    'pressure-washer': [
        {'id': 'ppe', 'point': 'Eye and face protection',
         'check': 'safety glasses or face shield seated, no gaps at the seal',
         'on_fault': 'the trigger does not get pulled - injection and eye injuries '
                     'at this pressure are immediate and permanent'},
        {'id': 'power', 'point': 'GFCI-protected power source',
         'check': 'outlet trips on test and resets clean, no bypassed ground',
         'on_fault': 'find another supply or another machine, because a bypassed '
                     'ground on a wet job is the classic fatality here'},
        {'id': 'trigger-lock', 'point': 'Wand trigger lock',
         'check': 'safety lock engages and holds, releases only under a '
                  'deliberate pull',
         'on_fault': 'the wand is out of service - a lock that does not hold is a '
                     'wand that fires when it is set down'},
        {'id': 'hose', 'point': 'Hose condition',
         'check': 'no kinks, bursts or abraded jacket along the full length',
         'on_fault': 'replace it; a burst at working pressure is a cutting injury, '
                     'not a spill'},
        {'id': 'containment', 'point': 'Work-area containment',
         'check': 'drain cover or berm set and the area barricaded before '
                  'the first spray',
         'on_fault': 'set it before anything is pulled - wash water is out of your '
                     'hands the moment it reaches a drain'},
    ],
    'airless-sprayer': [
        {'id': 'respirator', 'point': 'Respirator and ventilation',
         'check': 'organic-vapor cartridge seated and fit-tested, area '
                  'ventilated per the coating data sheet',
         'on_fault': 'stop: a spent cartridge or a seal that leaks leaves '
                     'ventilation as the only thing between you and the solvent'},
        {'id': 'tip-guard', 'point': 'Spray-tip guard',
         'check': 'guard installed and the tip locked in its holder, never '
                  'left bare',
         'on_fault': 'do not spray - a bare tip at this pressure injects, and an '
                     'injection injury is a surgical emergency'},
        {'id': 'pressure-relief', 'point': 'Pressure-relief procedure',
         'check': 'relief followed and the gun locked out before any tip change',
         'on_fault': 'relieve and lock out before the tip comes off, every single '
                     'time; there is no quick change at this pressure'},
        {'id': 'masking', 'point': 'Drop-cloth and masking',
         'check': 'cloths and masking tape set along every edge before the '
                  'first pass',
         'on_fault': 'mask it first, because overspray lands on work that is not '
                     'yours to repaint'},
        {'id': 'ignition', 'point': 'Fire and ignition sources',
         'check': 'open flame, sparks and hot work cleared from the solvent area',
         'on_fault': 'clear the ignition sources or move the work - solvent vapour '
                     'travels and finds them'},
    ],
    'boom-lift': [
        {'id': 'tires-level', 'point': 'Tires, outriggers and the pad',
         'check': 'tires sound, outrigger pads whole, the pad level and firm '
                  'under every foot',
         'on_fault': 'nothing lifts: an outrigger on soft or sloping ground is the '
                     'commonest way one of these goes over'},
        {'id': 'controls', 'point': 'Controls and emergency lowering',
         'check': 'every function answers at the basket and the ground '
                  'station, and the manual lowering valve works',
         'on_fault': 'out of service - the ground station and the manual lowering '
                     'valve are what get a casualty out of the basket'},
        {'id': 'guardrails', 'point': 'Guardrails and gate',
         'check': 'rails tight, the gate self-closes and latches behind you',
         'on_fault': 'fix the gate before anyone steps in; the rail is what you '
                     'stand behind, not what you clip to'},
        {'id': 'harness', 'point': 'Harness and anchor point',
         'check': 'webbing and stitching whole, lanyard in date, the basket '
                  'anchor rated and unbent',
         'on_fault': 'change it - webbing and lanyards come out of service, they '
                     'are never repaired in place'},
        {'id': 'overhead', 'point': 'Overhead-hazard scan',
         'check': 'every line, beam and canopy on the run found and its '
                  'clearance called before the first lift',
         'on_fault': 'call the clearance and have the line covered, de-energised, '
                     'or the work moved; the basket is not how you test it'},
    ],
    'overhead-crane': [
        {'id': 'hook', 'point': 'Hook latch and block',
         'check': 'latch closes and springs back, no throat stretch or '
                  'twist, sheaves turning free',
         'on_fault': 'the crane is out of service - a stretched throat or a latch '
                     'that will not close is a dropped load waiting for a reason'},
        {'id': 'rope', 'point': 'Wire rope and sheaves',
         'check': 'no broken wires, kinks or crushed strands, rope seated in '
                  'every sheave groove',
         'on_fault': 'the hook is out of service until the rope is changed - '
                     'broken wires and a latch that will not close are not run out'},
        {'id': 'limit', 'point': 'Upper-limit switch test',
         'check': 'hoist stops at the limit under slow approach, before '
                  'the block ever touches the drum',
         'on_fault': 'if the limit does not stop the hoist the crane is locked '
                     'out, because two-blocking parts the rope'},
        {'id': 'pendant', 'point': 'Pendant and e-stop',
         'check': 'every button labelled and springing back, the e-stop '
                  'kills all motion and resets clean',
         'on_fault': 'do not run it - a button that sticks or an e-stop that does '
                     'not kill motion means the crane cannot be stopped'},
        {'id': 'runway', 'point': 'Runway and aisle',
         'check': 'runway clear end to end, the pedestrian aisle marked and '
                  'nobody standing under the route',
         'on_fault': 'clear the runway and the aisle before the first move, and '
                     'keep the route walked rather than assumed'},
    ],
}
for sim_id, wa in WALKAROUNDS.items():
    SIMS[sim_id]['walkaround'] = wa
assert set(WALKAROUNDS) == set(SIMS), 'every seat gets its walkaround'
# A walkaround that only says LOOK is a sightseeing tour. The value of the
# habit is the STOP: what a crew does when the point fails, decided before
# the shift rather than argued about with a foreman standing over it. So
# every point carries its own fault action, and the text has to be long
# enough to be an instruction rather than the word 'no'. This does not make
# the walkaround a gate - see the honesty note - it makes it worth doing.
for sim_id, wa in WALKAROUNDS.items():
    for w in wa:
        assert len(w.get('on_fault', '')) > 40, \
            f'{sim_id}/{w["id"]}: a walkaround point with no fault action is a look'
    assert len({w['on_fault'] for w in wa}) == len(wa), \
        f'{sim_id}: five points, five different fault actions'

# The scripted reference operator - see the module docstring. The closed
# level set is declared ONCE here; every seat's operator runs at every
# level. `guarantees` is the list of rubric axes the optimal run passes
# on every scenario, asserted below to be exactly the seat's pass-gated
# axes, and proven by the page's headless sweep. `procedure` is the
# operator's own ordered step list: the page's policy is written as a
# switch over these step ids in this order, so the Operator advisor's
# `seat.procedure` answer, the wiki and the running policy cannot drift.
OPERATOR_LEVELS = {
    'optimal': 'the reference: the written procedure with its checks and '
               'waits intact - passes every pass-gated rubric axis on '
               'every regional scenario, proven by the build',
    'novice': 'the same procedure with seeded, deterministic slips - a '
              'mis-selected rack, a wrong signal, a wandering standoff, a '
              'low carry - so the sweep also yields labelled sub-optimal '
              'episodes',
    'hurried': 'the same procedure with its waits and checks removed - no '
               'settle before release, no containment before the trigger, '
               'no chart read before the hook - the failure a rushed '
               'shift actually produces',
}
OPERATOR_HONESTY = (
    'SCRIPTED: a demonstration of a hand-written, deterministic control '
    'policy on a schematic single-machine simulator - a function of the '
    "seat's own gauges, the scenario's params and a level, no model behind "
    'it and no network reached. Not a learned policy, not real equipment, '
    'and not a claim about any physical robot; its runs are its own '
    'record, never credited to the learner watching it.'
)
OPERATORS = {
    'crane-lift': {
        'guarantees': ['placement', 'swing', 'strikes'],
        'procedure': [
            {'id': 'reach', 'step': 'slew and trolley the hook over the '
                                    'supply pad and lower it under 4.5 m'},
            {'id': 'hook', 'step': 'hook the load'},
            {'id': 'hoist', 'step': 'hoist to carry height - clear of the '
                                    'tallest stack - before anything moves '
                                    'sideways'},
            {'id': 'pull-in', 'step': 'trolley in to a short radius, moving '
                                      'only while the swing gauge is low'},
            {'id': 'slew', 'step': 'slew round to the target bearing, moving '
                                   'only while the swing gauge is low'},
            {'id': 'trolley', 'step': 'trolley out to the target radius, '
                                      'moving only while the swing gauge is '
                                      'low'},
            {'id': 'settle', 'step': 'hold everything until the swing dies '
                                     'away'},
            {'id': 'lower', 'step': 'lower the load to the ground'},
            {'id': 'release', 'step': 'release once the swing is still'},
        ],
    },
    'excavator-trench': {
        'guarantees': ['grade', 'utility', 'spoil'],
        'procedure': [
            {'id': 'cell', 'step': 'swing to the next cell short of grade, '
                                   'reach out to it and drop the bucket '
                                   'under 0.6 m'},
            {'id': 'dig', 'step': 'take one bite - the marked depth divided '
                                  'by the bite is the count, and a flagged '
                                  'cell gets no more'},
            {'id': 'carry', 'step': 'swing the full bucket to the spoil zone '
                                    'and reach to its centre'},
            {'id': 'dump', 'step': 'dump inside the zone, then back to the '
                                   'trench until every cell is at grade'},
        ],
    },
    'forklift-run': {
        'guarantees': ['gates', 'cones', 'docking'],
        'procedure': [
            {'id': 'gates', 'step': 'steer for the centre of the next '
                                    'untaken gate, slowing into every turn'},
            {'id': 'approach', 'step': 'roll up to the pallet on the centre '
                                       'line and brake to a walk'},
            {'id': 'lift', 'step': 'lift once the forks are on the pallet '
                                   'and the truck has all but stopped'},
            {'id': 'return', 'step': 'carry up the clear lane outside the '
                                     'cone rows, never back through the '
                                     'gates'},
            {'id': 'dock', 'step': 'square up on the dock from the lane and '
                                   'set the pallet down inside the bay'},
        ],
    },
    'weld-bead': {
        'guarantees': ['fusion', 'band', 'burns'],
        'procedure': [
            {'id': 'gap', 'step': 'set the arc gap to the middle of the '
                                  "scenario's band before striking"},
            {'id': 'strike', 'step': 'strike the arc at the start of the '
                                     'seam'},
            {'id': 'travel', 'step': 'travel steadily to the end of the seam '
                                     'without pausing - every segment fuses '
                                     'in band and none lingers to a burn'},
        ],
    },
    'scaffold-bay': {
        # one gated axis, because `complete` stopped being a gate above
        'guarantees': ['sequence'],
        'procedure': [
            {'id': 'rack', 'step': 'jump the rack to the stage the bay is '
                                   'legally at - the dash names it'},
            {'id': 'place', 'step': 'place the next part, and repeat until '
                                    'the rails are on'},
        ],
    },
    'rigging-signals': {
        'guarantees': ['calls', 'wrong'],
        'procedure': [
            {'id': 'read', 'step': 'read the called signal off the lift '
                                   'card - the dash shows it'},
            {'id': 'give', 'step': 'give exactly that signal, wait for the '
                                   'crane to finish moving, and give the '
                                   'next; STOP ends the card'},
        ],
    },
    'load-chart': {
        'guarantees': ['judgments', 'overloads'],
        'procedure': [
            {'id': 'read', 'step': 'read the pick weight and radius against '
                                   'the chart line at that radius'},
            {'id': 'judge', 'step': 'hook the pick if its weight is inside '
                                    'the chart, refuse it if it is over'},
        ],
    },
    'pressure-washer': {
        'guarantees': ['coverage', 'damage', 'containment'],
        'procedure': [
            {'id': 'contain', 'step': 'deploy the containment berm before the '
                                      'trigger is ever pulled'},
            {'id': 'standoff', 'step': 'set the standoff to the middle of the '
                                       'effective window, well clear of the '
                                       'damage distance'},
            {'id': 'spray', 'step': 'pull the trigger'},
            {'id': 'raster', 'step': 'sweep the panel cell by cell in rows, '
                                     'dwelling on each just past the clean '
                                     'time and never lingering'},
        ],
    },
    'airless-sprayer': {
        'guarantees': ['coverage', 'runs', 'holidays', 'overspray'],
        'procedure': [
            {'id': 'standoff', 'step': 'set the standoff to the middle of the '
                                       'effective window, well clear of the '
                                       'run distance'},
            {'id': 'spray', 'step': 'pull the trigger inside the masked '
                                    'line'},
            {'id': 'raster', 'step': 'sweep the panel cell by cell in rows, '
                                     'dwelling on each just past the coat '
                                     'time, turning inside the mask'},
        ],
    },
    'boom-lift': {
        'guarantees': ['reach', 'envelope', 'tie-off', 'slope', 'strikes'],
        'procedure': [
            {'id': 'level', 'step': 'stand on the level pad with the boom '
                                    'stowed - nothing lifts until the base '
                                    'is right'},
            {'id': 'stabilizers', 'step': 'set the stabilizers before the '
                                          'basket leaves the ground'},
            {'id': 'tie-off', 'step': 'clip the harness to the basket anchor '
                                      'on the ground, before the first lift'},
            {'id': 'raise', 'step': 'raise the boom to the transit elevation '
                                    'first - at that angle a fully extended '
                                    'boom still sits inside the envelope and '
                                    'clears the overhead line'},
            {'id': 'swing', 'step': 'swing the turret to the bearing of the '
                                    'next work point'},
            {'id': 'extend', 'step': 'extend or retract to the boom length the '
                                     'point needs, moment under the line'},
            {'id': 'settle', 'step': 'lower the boom onto the point and hold '
                                     'the basket inside the tolerance'},
            {'id': 'work', 'step': 'do the task at the point, then back up '
                                   'to transit elevation for the next one'},
            {'id': 'stow', 'step': 'once every point is done: retract fully '
                                   'at transit elevation, swing back parallel '
                                   'to the line, then lower the basket to the '
                                   'stowed height'},
        ],
    },
    'overhead-crane': {
        'guarantees': ['placement', 'sway', 'path', 'limits', 'clear'],
        'procedure': [
            {'id': 'reach', 'step': 'bridge and trolley the hook over the '
                                    'pickup and lower it onto the load'},
            {'id': 'hook', 'step': 'hook the load'},
            {'id': 'hoist', 'step': 'hoist to carry height - above every '
                                    'obstacle on the route, well short of '
                                    'the upper limit - before anything '
                                    'travels'},
            {'id': 'bridge', 'step': 'travel the bridge to the target x, '
                                     'moving only while the sway gauge is '
                                     'low'},
            {'id': 'trolley', 'step': 'traverse the trolley to the target z, '
                                      'moving only while the sway gauge is '
                                      'low'},
            {'id': 'settle', 'step': 'hold everything until the sway dies '
                                     'away'},
            {'id': 'lower', 'step': 'lower the load to just above the floor'},
            {'id': 'release', 'step': 'release once the sway is still and the '
                                      'load is over the square'},
        ],
    },
}
for sim_id, op in OPERATORS.items():
    gated = [r['axis'] for r in SIMS[sim_id]['rubric']
             if r['pass'] != 'informational']
    assert op['guarantees'] == gated, \
        f'{sim_id}: the operator must guarantee exactly the pass-gated axes'
    ids = [p['id'] for p in op['procedure']]
    assert len(ids) == len(set(ids)) and len(ids) >= 2, \
        f'{sim_id}: a procedure is an ordered list of distinct steps'
    assert all(p['step'] and len(p['step']) >= 12 for p in op['procedure']), \
        f'{sim_id}: every step is a sentence a learner can act on'
    SIMS[sim_id]['operator'] = {'levels': list(OPERATOR_LEVELS), **op}
assert set(OPERATORS) == set(SIMS), 'every seat gets its reference operator'
# --------------------------------------------------------- the yard (§24) --
# What each seat's training yard is actually floored with.
#
# A simulator yard had a fence, four light masts and a painted apron border
# standing on the page's global ground plane - so the welder, the excavator
# and the pressure washer all worked on the same nothing. The surfaces pack
# has carried twenty-two floor finishes and the reason each one exists since
# §24; a seat is a place, and a place has a floor.
#
# The id on the left is a finish in surfaces/surfaces.py, cross-checked
# against that catalogue at build time rather than trusted - one truth, in
# the pack that owns it. `why` is this SEAT's reason, which is not always
# the finish's own general reason: the welding bay is on bare slab for the
# same reason the hot-work hazard puts it there, and saying so out loud is
# how the two stay consistent.
YARD_SURFACE = {
    'crane-lift': ('asphalt-apron',
                   'a lay-down yard the load waits on and the crane tracks '
                   'over, between the stockpile and the set'),
    'excavator-trench': ('crushed-stone',
                         'the ground plant actually digs, piles and tracks '
                         'on - and the spoil goes back onto it'),
    'forklift-run': ('asphalt-apron',
                     'a yard running surface a loaded truck can turn on '
                     'without rutting it'),
    'weld-bead': ('bare-slab',
                  'non-combustible, with nothing underfoot to carry a spark - '
                  'the same reason the hot-work hazard puts the bay here'),
    'scaffold-bay': ('sealed-slab',
                     'the sills need flat, sound, dust-proofed bearing before '
                     'the first standard goes up'),
    'rigging-signals': ('asphalt-apron',
                        'the signalperson stands in the yard with the load, '
                        'not in a booth beside it'),
    'load-chart': ('sealed-slab',
                   'the chart board is read indoors, off the machine, before '
                   'anybody commits to the pick'),
    'pressure-washer': ('broom-concrete',
                        'traction on a wash-down surface, because this seat '
                        'runs wet by definition'),
    'airless-sprayer': ('epoxy-smooth',
                        'wipe-clean, because overspray lands on the floor '
                        'before it lands anywhere else'),
    'boom-lift': ('asphalt-apron',
                  'the stabilizers set on it, so what it is and how flat it '
                  'is are the first two things the walkaround asks'),
    'overhead-crane': ('sealed-slab',
                       'a shop bay floor with the aisle and the workstation '
                       'marked on it, which is the route this seat travels'),
}

for sim_id, s in SIMS.items():
    if 'layout' in s:
        assert s['layout'], f'{sim_id}: an empty layout is no shared truth'

# A PASS GATE IS ONLY A GATE IF A RUN CAN FAIL IT. Every gated axis has to
# name the failure in a sentence a practitioner would recognise; an axis
# nobody can write that sentence for is a gate that grades nothing, and the
# scaffold bay's `complete` was exactly that until it stopped being gated.
# An informational axis carries no such line, because it has no failure to
# describe - that is what informational means.
for sim_id, s in SIMS.items():
    gated = [r for r in s['rubric'] if r['pass'] != 'informational']
    assert gated, f'{sim_id}: a rubric with no gate grades nothing'
    for r in gated:
        assert len(r.get('fails_when', '')) > 40, \
            f'{sim_id}/{r["axis"]}: a gate with no describable failure is not a gate'
    assert len({r['fails_when'] for r in gated}) == len(gated), \
        f'{sim_id}: two gates failing the same way are one gate typed twice'
    for r in s['rubric']:
        assert ('fails_when' in r) == (r['pass'] != 'informational'), \
            f'{sim_id}/{r["axis"]}: only a gate has a failure'

# A scenario's params ARE the yard: the page reads each one with a `??`
# default behind it, so a scenario that leaves a key out quietly trains the
# default yard under the name of the one it declared. The required key set is
# computed from the seat's own scenarios rather than typed a second time -
# every scenario of a seat must carry all of it - and a null value is barred
# because a declared-but-null param is that same default wearing a scenario's
# name. `teaches` is the other half of the same rule: a yard that cannot say
# what it demands that its sibling yards do not is a skin, not a scenario.
for sim_id, s in SIMS.items():
    keys = set().union(*(set(x['params']) for x in s['scenarios']))
    assert keys, f'{sim_id}: scenarios that carry no params are one scenario'
    s['scenario_params'] = sorted(keys)
    for x in s['scenarios']:
        assert set(x['params']) == keys, \
            f'{sim_id}/{x["id"]}: params differ from the seat\'s set {sorted(keys)}'
        assert all(v is not None for v in x['params'].values()), \
            f'{sim_id}/{x["id"]}: a null param is the page default in disguise'
        assert len(x.get('teaches', '')) > 30, \
            f'{sim_id}/{x["id"]}: a yard that teaches nothing new is a skin'
    assert len({x['teaches'] for x in s['scenarios']}) == len(s['scenarios']), \
        f'{sim_id}: three yards, three different demands'

# THE ONE THING THIS BUILDER CAN PROVE ABOUT THE SCRIPTED OPERATOR'S ROUTE.
# The headless sweep that proves `optimal` passes runs inside the page, and
# this builder cannot run it. What it can prove is the GEOMETRY the boom
# lift's route is built on, which is the part a scenario edit breaks: the
# operator goes up to the declared transit elevation before it swings or
# extends, holds that elevation across every bearing and boom length the
# yard uses, and only lowers onto a work point along that point's own
# bearing. Sampling those three families of poses against the yard's
# declared exclusion cylinder is a deliberate superset of the path the
# policy takes - it sweeps every bearing, not only the arc between two
# consecutive points - so a clearance here is a clearance there. It proves
# the DECLARED angle, not the policy's tolerance around it; the sweep owns
# that. The margin is the slack that keeps a yard from being drawn with the
# line grazing the transit arc.
CLEAR_MARGIN = 0.25

def _basket(lay, sw_deg, el_deg, length):
    """The basket's position for a swing, elevation and boom length - the
    same three numbers the seat's own kinematics carry, in the same order."""
    el, sw = math.radians(el_deg), math.radians(sw_deg)
    h = math.cos(el) * length
    return (math.cos(sw) * h, lay['pivot_y'] + math.sin(el) * length,
            math.sin(sw) * h)

def _boom_clearance(lay, points, line):
    solved = []
    for px, py, pz in points:
        d, dy = math.hypot(px, pz), py - lay['pivot_y']
        solved.append((math.degrees(math.atan2(pz, px)), math.hypot(d, dy),
                       math.degrees(math.atan2(dy, d))))
    tr, lo = lay['transit_elev_deg'], lay['boom_min']
    hi = max(x[1] for x in solved)
    poses = [(0.0, e / 2.0, lo) for e in range(0, tr * 2 + 1)]
    steps = int((hi - lo) / 0.25) + 1
    poses += [(float(b), float(tr), lo + i * 0.25)
              for b in range(0, 360, 2) for i in range(steps + 1)]
    for bearing, length, el_pt in solved:
        poses += [(bearing, el_pt + (tr - el_pt) * i / 60.0, length)
                  for i in range(61)]
    return min(math.hypot(y - line['y'], z - line['z']) - line['r']
               for _, y, z in (_basket(lay, *q) for q in poses))

_bl = SIMS['boom-lift']
for _sc in _bl['scenarios']:
    _gap = _boom_clearance(_bl['layout'], _sc['params']['points'],
                           _sc['params']['line'])
    assert _gap >= CLEAR_MARGIN, \
        (f'boom-lift/{_sc["id"]}: the transit route passes within '
         f'{_gap:.2f} m of the overhead zone')

# §24, applied to the seats: the yard surface, cross-checked against the
# catalogue that owns it rather than copied into a second table here.
_finishes = json.load(open(ROOT / 'surfaces/registry/finishes.json'))
assert set(YARD_SURFACE) == set(SIMS), 'every seat stands on a declared floor'
for sim_id, (surf, why) in YARD_SURFACE.items():
    assert surf in _finishes['catalogue'], \
        f'{sim_id}: {surf} is not a finish in the surfaces catalogue'
    assert len(why) > 20, f'{sim_id}: a floor with no reason is a preference'
    SIMS[sim_id]['yard'] = {'surface': surf, 'why': why,
                            'name': _finishes['catalogue'][surf]['name']}

# GATES THE CURRENT SEAT CANNOT FAIL. Auditing every pass gate against the
# page's own finish condition found four where the seat stops the run at
# exactly the state the axis demands, so the axis grades the run's own
# terminating condition and no episode can score it anything but a pass.
# In each case the RUBRIC LINE IS RIGHT - a signalperson can call an early
# stop, a coat can be left short, a basket can come down with work
# unfinished - and what is wrong is the seat, so the gate stays a gate and
# the gap is declared here with the seat change that closes it. Each entry
# carries the page marker the gap lives at, and sims/test.mjs proves that
# marker is still there: close a gap and the check fails, which is the
# signal to delete the entry. This is the opposite of the scaffold bay's
# `complete`, which was not a seat gap but a tautology in the rubric and is
# no longer gated at all.
# Gates that no run could fail.
#
# Five of the thirty-four pass-gated axes were grading their run's own
# terminating condition - the seat stops at exactly the state the axis
# demands, so no episode could score them anything but a pass. Four were
# seat bugs and are now closed in the page; the fifth (scaffold-bay's
# `complete`) was a tautology in the rubric rather than a bug, and is
# informational now.
#
# This register is KEPT, and empty, because emptying it is the point: an
# entry names the page marker its gap lives at, and the suite proves that
# marker is still there. Close a gap and the check fails, which is the
# signal to delete the entry - a ratchet that turns in both directions.
# A gap found later goes here rather than into a comment nobody runs.
GATE_GAPS = []
_gated = {i: {r['axis'] for r in sm['rubric'] if r['pass'] != 'informational'}
          for i, sm in SIMS.items()}
for _g in GATE_GAPS:
    assert _g['axis'] in _gated.get(_g['sim'], ()), \
        f'{_g["sim"]}/{_g["axis"]}: a gap can only be declared against a real gate'
    assert len(_g['why']) > 40 and len(_g['fix']) > 60, \
        f'{_g["sim"]}/{_g["axis"]}: a declared gap states its cause and its cure'
    assert len(_g['page_marker']) > 20, \
        f'{_g["sim"]}/{_g["axis"]}: a gap with no marker cannot be proven still open'
assert len({g['page_marker'] for g in GATE_GAPS}) == len(GATE_GAPS), \
    'two gaps at one marker is one gap'

unions = json.load(open(ROOT / 'unions/registry/unions.json'))['unions']
SKILL_ROWS = json.load(open(ROOT / 'pack/registry/skills.json'))['skills']
skills = {s['skill_id'] for s in SKILL_ROWS}
slugs = {u['slug'] for u in unions}

bindings = {}
for sim_id, sim in SIMS.items():
    for hall in sim['halls']:
        assert hall in slugs, f'{sim_id}: unknown hall {hall}'
        skill = f"{hall}.{sim['skill_strand']}.{sim['skill_tier']}"
        assert skill in skills, f'{sim_id}: no such skill {skill}'
        bindings.setdefault(hall, []).append(
            {'sim': sim_id, 'skill_id': skill})


# ------------------------------------- what the seats do NOT reach --------
# The loop above says which cells a seat proves. It has never said which
# cells no seat reaches, and the difference is the whole product: a ladder
# is only a ladder if a learner can climb it, and every rung above is
# decoration if the rungs below carry nothing to stand on.
#
# So the same loop's output is measured here, from `pack/registry/skills.json`
# and from `bindings` itself - never typed. Three facts come out of it and
# all three are uncomfortable:
#
#   * a seat lands on very few cells. The pack declares thousands of cells
#     across a hundred and eleven halls; the seats bind a double-digit
#     handful of them. `cells.with_a_seat` over `cells.total` is that ratio
#     and the page and the README read it from here.
#
#   * seats PILE UP. Several halls bind four seats and all four name the
#     same cell, because `skill_strand` and `skill_tier` are properties of
#     the SIMULATOR, not of the hall: every machine seat in a hall resolves
#     to `<hall>.machines.applied` whatever the machine is. Four seats on
#     one cell is one covered cell, not four, and `cells.carrying_more_than_
#     one_seat` counts the collisions rather than letting the binding total
#     flatter the coverage.
#
#   * and no bound cell is REACHED. For each bound cell this walks the whole
#     `requires` closure and asks whether any cell in it carries a seat. A
#     bound cell whose entire chain of prerequisites carries no seat cannot
#     be earned inside this bundle: the prerequisites are declared, they are
#     real, and there is nothing here that proves any of them. Those cells
#     are named in `unreachable_seat_cells`.
#
# None of this is a defect in the control plane and fixing the sequencer
# would not move any of these numbers. It is seat coverage, and the honest
# thing is to publish the ratio beside the seats rather than beside nothing.
BY_ID = {s['skill_id']: s for s in SKILL_ROWS}
SEAT_CELLS = {}
for _h, _bs in bindings.items():
    for _b in _bs:
        SEAT_CELLS[_b['skill_id']] = SEAT_CELLS.get(_b['skill_id'], 0) + 1


def prereq_closure(cell):
    """Every cell `cell` transitively requires. Fails closed on a dangling
    prerequisite rather than silently treating it as no prerequisite."""
    seen, stack = set(), [cell]
    while stack:
        here = stack.pop()
        assert here in BY_ID, f'{cell}: requires {here}, which is not a skill'
        for req in BY_ID[here]['requires']:
            if req not in seen:
                seen.add(req)
                stack.append(req)
    return seen


unreachable = sorted(
    c for c in SEAT_CELLS
    if prereq_closure(c) and not (prereq_closure(c) & set(SEAT_CELLS)))
piled = sorted(c for c, n in SEAT_CELLS.items() if n > 1)

COVERAGE = {
    'halls': {'total': len(slugs), 'with_a_seat': len(bindings)},
    'strands': {
        'total': len({(s['union'], s['strand']) for s in SKILL_ROWS}),
        'with_a_seat': len({(BY_ID[c]['union'], BY_ID[c]['strand'])
                            for c in SEAT_CELLS}),
    },
    'cells': {
        'total': len(SKILL_ROWS),
        'with_a_seat': len(SEAT_CELLS),
        'carrying_more_than_one_seat': len(piled),
        'seats_absorbed_by_those_cells': sum(SEAT_CELLS[c] for c in piled),
    },
    'seats': {'bound': sum(len(v) for v in bindings.values())},
    'unreachable_seat_cells': unreachable,
    'means': 'a cell is covered when at least one seat names it, and a '
             'covered cell is REACHABLE when some cell in its prerequisite '
             'closure is also covered. Every number here is counted from '
             'pack/registry/skills.json and from hall_bindings in this same '
             'build; none of them is typed.',
    'honest': 'this is the ratio a training coordinator should read first. '
              'The seats that exist are deterministic and their rubrics are '
              'real, and they stand on a ladder whose lower rungs this '
              'bundle cannot prove. Nothing here is a certification, and a '
              'hall with no seat at all is not partially covered - it is '
              'uncovered, and it is counted that way.',
}

# The arithmetic must hold or the block is decoration. A covered count that
# exceeded the bindings, or a pile-up that absorbed more seats than were
# ever bound, would be a number that had drifted from the thing it counts.
assert COVERAGE['cells']['with_a_seat'] <= COVERAGE['seats']['bound'], \
    'more covered cells than seats bound - a seat was counted twice'
assert (COVERAGE['cells']['seats_absorbed_by_those_cells']
        <= COVERAGE['seats']['bound']), \
    'the pile-ups absorb more seats than exist'
assert COVERAGE['cells']['with_a_seat'] <= COVERAGE['cells']['total'], \
    'a seat lands on a cell the pack does not declare'
assert COVERAGE['halls']['with_a_seat'] <= COVERAGE['halls']['total'], \
    'a seat is bound to a hall that is not a union'
assert set(unreachable) <= set(SEAT_CELLS), \
    'an unreachable cell that carries no seat is not a seat gap'
for _c in piled:
    assert SEAT_CELLS[_c] > 1, 'a pile-up of one is not a pile-up'

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
        'walkaround': 'a habit-builder, not a gate: no seat is locked '
                      'behind the walkaround, completing it changes no '
                      'score, and it is not an equipment inspection record. '
                      'Each point also names what a crew would do when the '
                      'check fails, which is the half of the habit worth '
                      'having; that is unverified general practice, not a '
                      'release anybody can sign from here and not a '
                      'permission this seat grants.',
        'operator': OPERATOR_HONESTY,
        # WHO VOUCHES FOR THIS. A training coordinator's first question about
        # any curriculum is whose name is on it, and the honest answer here
        # is: nobody's yet. Saying so in the record is the difference between
        # a draft and a claim, and it is why every rubric line, walkaround
        # point and fault action is written to be argued with rather than
        # obeyed.
        'authoring': 'unverified general practice, written to be reviewed, '
                     'corrected and replaced by journey-level practitioners '
                     'from the halls each seat names. Nothing here cites a '
                     'jurisdiction, a standard or an authority, nothing here '
                     'speaks for one, and no rubric line, walkaround point '
                     'or fault action is an instruction from one - a hall '
                     'that adopts a seat owns what it says.',
        'xr': 'every seat is operable inside a WebXR session through the '
              '`xr` mapping it carries: thumbsticks, trigger, grip and the '
              'two face buttons land in the same key state a keyboard '
              'fills, so a seat cannot tell the two apart and no rubric '
              'changes in a headset. The mapping is verified against a '
              'mocked WebXR session in headless Chromium only - no physical '
              'headset has run these seats in this build.',
    },
    'operator_levels': OPERATOR_LEVELS,
    # the gates the current seat cannot fail, and the seat change that would
    # close each one - declared, not quietly left for a reader to find
    'gate_gaps': GATE_GAPS,
    'sims': SIMS,
    'hall_bindings': bindings,
    # what the seats reach and what they do not, counted from the pack
    'coverage': COVERAGE,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'sims.json').write_text(json.dumps(doc, indent=1) + '\n')
n_halls = len(bindings)
cov = COVERAGE['cells']
print(f"sim registry: {len(SIMS)} simulators bound to {n_halls} halls "
      f"(source stamp {stamp})")
print(f"  seat coverage: {cov['with_a_seat']} of {cov['total']} cells carry "
      f"a seat, {len(unreachable)} of them unreachable, "
      f"{cov['carrying_more_than_one_seat']} cells carry more than one seat")
