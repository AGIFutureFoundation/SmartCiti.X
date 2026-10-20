#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the training-data registry builder.

Every interaction in this bundle already produces a structured fact: a
sim run ends in a measured rubric outcome, an advisor answer is a fixed
topic against a fixed record, a walkaround check is a point marked done.
This pack declares the shape those facts are recorded in when a learner
chooses to keep them - so the same sessions that teach a person can, if
they choose, become example data for the robotics-training side of this
project: the org's own `ml-agents` fork (Unity ML-Agents Toolkit,
Apache-2.0), RECORDED in `meta/registry/metaverse.json` as the training
consumer this bundle targets.

WHAT THIS IS. An EPISODE RECORDER, device-local like every other record
in this bundle. One kind of episode per interaction:

  * sim       - the scenario a learner trained under, the control scheme
                the registry already declares for that seat, and the
                final measured rubric outcome (the same rows the results
                panel shows). EPISODE-LEVEL by default: what a run was
                attempted under and how it ended. A separate, OFF-BY-
                DEFAULT toggle (see TRACE below) adds a coarse gauge
                TRACE across the run itself - still not a per-tick joint
                trajectory, see TRACE's own honesty note for exactly
                what that is and is not.
  * advisor   - which advisor, which fixed topic, and whether the answer
                was `read` from another registry or `say` written here -
                never the words themselves, which the advisor registry
                already owns.
  * walkaround - which point, on which seat.
  * walk      - (wave 20) the learner's own position entered one room of one
                hall that a lesson names as a walk target: which hall, which
                strand, which room label. One event per (hall, room); no
                coordinates, no path, no time spent. It proves a device saw
                the walker inside that room's rectangle, nothing more.
  * placard   - (wave 20) the door placard of one room was opened in the page's
                placard panel and left open, with the learner still standing
                in that room, for the declared dwell (STEP_EPISODES below).
                It proves a panel stayed open for that long, not that anyone
                read it, understood it or put anything on.
  * station   - (wave 21) a training station's quiz was answered with its
                correct option at the station's bench, for a station a lesson
                step names. It proves a device recorded that pick, not that
                the checklist was read or that anything was learned.
  * crib      - (wave 21) the district crib check was finished with every pick
                right, for a crib a lesson step names. It proves a device
                recorded a passed check of the declared number of picks.

TRACE. The finer-grained recorder, scoped to exactly what it is rather
than promoted past it. While TRACE is on (its own
toggle, default OFF - see CONSENT), a running sim's own gauges() output
- the same numbers the on-screen dashboard already reads out, nothing
new computed - is sampled once a second and appended to that episode's
`outcome.trace` array when the run ends, capped at TRACE['max_samples']
so one long run cannot balloon the record. This is still not a per-tick
physics or joint trajectory: these are schematic single-machine
simulators (a crane winch, a trench profile, a weld bead), not
articulated robots, and their `gauges()` output is display-shaped
scalars and short labels, not a state vector a controller would train
on directly. It is real data about what this session's own SCHEMATIC
simulator computed, sampled coarser than every frame and finer than
"episode-level" - stated at exactly that resolution, not dressed up as
either end.

ACTORS, AND THE SCRIPTED TIER. A sim episode names who drove the seat.
`human` is a learner at the keys - every episode this recorder kept
before actors existed, and exactly as it was. `scripted-reference` is
the scripted reference operator sims/ declares: a hand-written,
deterministic control policy in the page - a function of the seat's own
gauges, the scenario's params and a level, no model, no network - driven
either at real time while a learner watches, or headlessly at a fixed
step by the records panel's sweep, so one click yields a demonstration
episode for every seat, scenario and level. A scripted episode carries
`operator: {level, seed, scenario}`, the handle that replays it: the
levels are a closed set (sims/ owns it), the seed drives a fixed-seed
generator (no Math.random anywhere in the policy), so the same
(sim, scenario, level, seed) at the same fixed step yields the same
non-time axes every run. Its provenance word is SCRIPTED - not
AI-SYNTHESIZED, which orbis/ owns for generated video and would be a
false label for deterministic data: a scripted episode is a demonstration
of a written policy on a schematic single-machine simulator, not a
learned policy, not real equipment, and not a claim about any physical
robot. It goes through the SAME simResults -> recordEpisode path a human
run does, downstream of the same final score, gated by the same toggle
and the same rolling cap - and it never touches the learner's own
progress record, which the page guards by name.

WHAT THIS IS NOT. Not a transcript, not a surveillance log, and not real
robot data: every episode comes from SCHEMATIC physics and deterministic
rubrics, useful for exercising a training pipeline's plumbing and export
format, not for training a controller that will run on real equipment.
Not biometric, not identifying: no name, no email, no device id, nothing
but what happened in the simulator. Not a native Unity ML-Agents
demonstration file - a JSON shape a conversion script could read, not a
protobuf .demo this bundle has never produced or tested against a real
ML-Agents build. And not a score: recording an episode changes no score
and is never read by a grader, exactly as talking to an advisor is not -
the suite proves it the same way, by reading the graders.

CONSENT. Off by default is wrong for a device-local, non-uploaded record
that already keeps company with `tc-progress`; always-on with no control
is wrong for something described to a learner as training data. So the
recorder ships ON, with a visible toggle next to the export button, and
turning it off does not touch episodes already kept - a learner clears
those the same way they clear progress, on purpose, separately. TRACE
gets the opposite default for the opposite reason: it is meaningfully
heavier data than an episode record, so it ships OFF, behind its own
separate toggle next to the base one - turning the base recorder on
does not turn TRACE on, and turning TRACE on does nothing unless the
base recorder is on too, since a trace with no episode to attach to is
never kept.

HOW THIS PAIRS WITH orbis/build.py. That pack declares a second, separate
stream toward the same `ml-agents` fork: a deterministic prompt contract
that turns any of the same 111 union modules into an AI-SYNTHESIZED video
prompt for Reactor's hosted video models, dense enough to cover a module
this recorder has no episode for yet, since this recorder only ever
produces an episode once a learner actually trains here. Real schematic
episode versus AI-SYNTHESIZED video - neither claims to be the other, and
this build still exports neither anywhere by itself.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

# One bundle version, read from the manifest rather than typed here.
PACK_VERSION = json.load(open(ROOT / 'pack/manifest.json'))['pack_version']
BUILT = "2026-09-11"

ACTORS = {
    'human': 'a learner at the keys - the episode carries nothing new; '
             'consumers that ignore `actor` read it exactly as before',
    'scripted-reference': 'the scripted reference operator sims/ declares '
                          'for every seat - a hand-written, deterministic '
                          'control policy driven from the seat\'s own '
                          'gauges, no model, no network; the episode also '
                          'carries `operator: {level, seed, scenario}`, '
                          'the handle that replays it',
}

# wave 21: the crib check's number of picks is tools/'s own declaration, read here so the floor on a crib episode is
# the one truth and not a second typed 5
CRIB_PICKS = json.load(open(ROOT / 'tools/registry/toolcribs.json'))['drill']['picks']
assert isinstance(CRIB_PICKS, int) and CRIB_PICKS > 0, 'tools/ must declare how many picks the crib check has'

EPISODE_KINDS = {
    'sim': {
        'fields': ['t', 'kind', 'campus', 'hall', 'sim', 'scenario',
                   'controls', 'actor', 'operator', 'outcome'],
        'actor': 'one of ACTORS: `human` or `scripted-reference`',
        'operator': '{level, seed, scenario, steps, dt} - present ONLY when '
                    'actor is scripted-reference: the closed level name, the '
                    'integer seed of its fixed-seed generator, the scenario '
                    'id, the number of control steps the run took, and the '
                    'fixed step length when the run was headless (steps x dt '
                    'is then its deterministic sim time - the `time` axis '
                    'itself is wall-clock and informational) or null when a '
                    'learner watched it at real time; absent on a human '
                    'episode',
        'outcome_shape': {'passed': 'bool',
                           'rows': '[{axis, value, ok}] - the rubric rows',
                           'trace': '[{t, gauges}] - OPTIONAL, present only '
                                    'when TRACE is on: ~1 Hz samples of the '
                                    "sim's own gauges() readout across the "
                                    'run, capped at TRACE[\'max_samples\']'},
        'granularity': 'episode-level by default: the scenario and control '
                       'scheme a run was attempted under, and how it ended. '
                       'With TRACE on, also a coarse (~1 Hz) gauge trace '
                       'across the run - still not a per-tick physics or '
                       'joint trajectory; see TRACE below',
        'what': 'one completed simulator run',
    },
    'advisor': {
        'fields': ['t', 'kind', 'campus', 'hall', 'advisor', 'topic',
                   'answer_kind'],
        'outcome_shape': None,
        'granularity': 'one exchange: which fixed topic was asked and '
                       'whether the answer was read from a record or '
                       'written in the advisor registry',
        'what': 'one advisor question asked and answered',
    },
    # A crew answer is not an advisor answer. An advisor stands alone and
    # answers for a room or a seat; a crew role is one of several people
    # running one job, and which ROLE answered is the part worth keeping -
    # a signalperson's answer and a rigger's are different evidence about
    # the same lift. So the crew and the role are recorded, not an
    # advisor id that would flatten both into one figure.
    #
    # `seat` and `muster` are recorded too (wave 20): both are read verbatim
    # from the crew's own entry in agents/registry/crews.json at the moment of
    # the exchange - the simulator seat the crew stands at and the room
    # strand it musters in (both declared by that registry, not retyped). A lesson's crew step carries
    # exactly these two as references, so without them in the episode the
    # completion verifier could never match the step to an episode and no
    # lesson that holds a crew step could be completed.
    'crew': {
        'fields': ['t', 'kind', 'campus', 'hall', 'crew', 'role', 'topic',
                   'answer_kind', 'seat', 'muster'],
        'outcome_shape': None,
        'granularity': 'one exchange with one role of one crew: which crew '
                       'was standing, which role was asked, which fixed '
                       'topic, which seat and muster strand that crew is '
                       'bound to in the crews registry, '
                       'and whether the answer was read from a record or '
                       'written in the crews registry',
        'what': 'one crew role asked one question while its seat was running',
    },
    # WALK / PLACARD (wave 20). A lesson's walk and placard steps used to
    # record nothing, so no lesson could be completed from evidence alone.
    # These two kinds are recorded by the 3D page's STEP-EPISODE blocks.
    # `where` is the strand id: the same word a lesson step carries in its own
    # `where`, so the completion contract can match step to episode by the one
    # name. A hall has exactly one room per strand, so (hall, where) names one
    # room. `room` is that room's label as the page draws it, kept so the
    # verifier can also check it against the step's own names_read.
    'walk': {
        'fields': ['t', 'kind', 'campus', 'hall', 'where', 'room'],
        # the verifier and every page that matches a step to an episode read this: the episode's `room` must be one of
        # the step's own names_read (the room label), on top of equality on hall and where
        'names_read_field': 'room',
        'outcome_shape': None,
        'granularity': 'one event: the walker\'s position entered the rectangle '
                       'of one room of one hall that a lesson names as a walk '
                       'target. No coordinates, no path, no dwell: arriving is '
                       'all it states',
        'what': 'one lesson-target room entered on foot',
    },
    'placard': {
        'fields': ['t', 'kind', 'campus', 'hall', 'where', 'room', 'dwell_ms'],
        'names_read_field': 'room',
        # the declared floor on a numeric this episode records: a placard episode with a dwell_ms below it matches no step.
        # Read by completion/ (and its verifier) and by every page matcher from here, never retyped
        'at_least': {'dwell_ms': 5000},
        'outcome_shape': None,
        'granularity': 'one event: the placard panel of one room stayed open '
                       'for at least the declared dwell while the walker stood '
                       'in that room. `dwell_ms` is the measured open time, '
                       'floored at the declared minimum by construction',
        'what': 'one door placard panel opened and left open for its dwell',
    },
    # STATION / CRIB (wave 21). A lesson's station and crib steps used to leave only a mark in the device-local
    # progress record (tc-progress.stations, tc-progress.tools), which is a mark and not an episode, so a lesson
    # that held one could not be fully verified by episode. These two kinds are recorded by the 3D page's
    # STATION-EPISODE blocks, at the moment the page already writes that mark. `where` is the strand id the step
    # carries in its own `where` (a station's strand; 'tools' for the crib, the room its pegboard hangs in), and
    # `station` / `crib` are the very ids the step carries, so the completion contract can match step to episode
    # on every reference the step has. The name fields are the display names the step lists in names_read.
    'station': {
        'fields': ['t', 'kind', 'campus', 'hall', 'where', 'station', 'station_name'],
        'names_read_field': 'station_name',
        'outcome_shape': None,
        'granularity': 'one event: the quiz of one training station, opened at its bench, was answered with the '
                       'correct option. Nothing about the other options picked first, the time taken or the '
                       'checklist is kept: a correct pick is all it states',
        'what': 'one training station quiz answered correctly at its bench',
    },
    'crib': {
        'fields': ['t', 'kind', 'campus', 'hall', 'where', 'crib', 'crib_name', 'picks'],
        'names_read_field': 'crib_name',
        # the declared floor on a numeric this episode records: every pick of the check right. Read from
        # tools/registry/toolcribs.json (drill.picks), never retyped; a crib episode below it matches no step.
        'at_least': {'picks': CRIB_PICKS},
        'outcome_shape': None,
        'granularity': 'one event: the district crib check was finished with every one of its picks right. A '
                       'failed run records nothing; `picks` is the number right, floored at the declared number '
                       'of picks by construction',
        'what': 'one district crib check passed',
    },
    'walkaround': {
        'fields': ['t', 'kind', 'campus', 'hall', 'sim', 'point'],
        'outcome_shape': None,
        'granularity': 'one point marked - not a score, the same habit '
                       'the sim registry already declares is not a gate',
        'what': 'one pre-shift walkaround point checked',
    },
}

# STEP_EPISODES (wave 20): the two declared numbers and the honesty of the walk/placard kinds. The page READS
# these from the embedded registry (never retypes them); completion/ reads `placard.dwell_ms` into its evidence rule
# and the verifier refuses a placard episode whose dwell_ms is below it.
STEP_EPISODES = {
    'placard': {
        'dwell_ms': EPISODE_KINDS['placard']['at_least']['dwell_ms'],   # one truth: the episode kind's own floor
        'dwell_why': 'a placard is a short board - the PPE a room lists, read one item to a line. Five seconds with '
                     'the panel open and the walker in the room is long enough to read a board of that length and '
                     'short enough that a learner who means to read it is never kept waiting. It is a floor on '
                     'open time, not a measure of reading: nothing here can tell reading from looking away.',
        'opened_by': 'clicking or tapping the door placard in the room, or pressing E while standing in a room '
                     'that has one and within the label registry\'s declared read distance of it',
        'range_m_from': 'labels/registry/labels.json#kinds.placard.hide_beyond_m (read, not retyped)',
    },
    'walk': {
        'recorded_for': 'a room that a lesson step of kind walk names, in the hall the learner stands in - never for '
                        'every room, so the rolling cap is not spent on footsteps',
    },
    'station': {
        'recorded_for': 'a station that a lesson step of kind station names, in the hall the learner stands in, and only '
                        'on a correct pick of its quiz: a wrong pick, a station no lesson names, or a station of another '
                        'hall records nothing',
        'recorded_with': 'the station id and name as stations/ spells them, and the strand of the room its bench stands in',
    },
    'crib': {
        'recorded_for': 'the district crib that a lesson step of kind crib names, in the hall the learner stands in, and '
                        'only when the check ends with every pick right: a failed run, or a crib no lesson of this hall '
                        'names, records nothing',
        'picks_from': 'tools/registry/toolcribs.json#drill.picks (read, not retyped); the episode records the picks right '
                      'and is floored at that number',
    },
    'dedupe': 'one episode per (kind, hall, where) while an earlier one is still in the log: re-entering a room or '
              're-opening a placard adds nothing, so a learner cannot pad the log and the log cannot crowd out the '
              'simulator episodes it exists to keep. A station is deduped on its station id and a crib on its district, '
              'for the same reason',
    'headless': 'a scripted probe stepping the walker (wkSilent) records no walk or placard episode: only a walker '
                'the learner is driving does',
    'proves': 'that this device recorded the event it names: a walker\'s position inside a room\'s rectangle, a '
              'panel open for a dwell with the walker in the room, a correct pick on a station quiz, or a crib check '
              'finished with every pick right',
    'does_not_prove': 'competence, attention, comprehension, that anybody read the sign or the checklist, that a station '
                      'pick was not found by trying every option, that a crib pick was not guessed or learned by '
                      'repetition, that the learner is the '
                      'person named in an export, or that any real room or placard exists - the halls are '
                      'SCHEMATIC. A lesson stays unverified general practice and certifies nobody',
}

# ROBOLAB (wave 11): WORLD episode kinds - teleop demonstrations of an AUTHORED robot embodiment in a world
# (robotics/registry/robotics.json envs, run by web/robokit.py). Kept SEPARATE from EPISODE_KINDS on purpose:
# EPISODE_KINDS is the 3D page's roster (one recordEpisode call per kind, checked above against that page);
# these are recorded by robokit on the world pages, under the SAME storage key, toggle, cap and export shape -
# an extension of this recorder, never a parallel format. Contract: $SP/ROBOTICS_CONTRACT.md v1.
WORLD_EPISODE_KINDS = {
    'world-teleop': {
        'v': 1,
        'fields': ['t', 'kind', 'v', 'env', 'embodiment', 'world', 'actor', 'seed', 'hz', 'dt_s',
                   'steps', 'samples', 'outcome'],
        'actor': 'one of ACTORS: `human` (a learner at the keys / touch pad) or `scripted-reference` (the '
                 'env\'s SCRIPTED reference policy, deterministic from its seed)',
        'sample_shape': {'i': 'control step index',
                         'pose': '[e_m, n_m, yaw_rad] env-local metres (ROV adds depth_m) - never lat/lon',
                         'vel': '[v_ms, w_rads]',
                         'near': '[AUTHORED object ids within 6 m, at most 4, nearest first]',
                         'a': '[action values in the env\'s action.fields order]'},
        'outcome_shape': {'done': 'termination id', 'success': 'bool', 'return': 'number',
                          'terms': '{reward term: summed value}', 'collected': 'int'},
        'granularity': 'a fixed low-rate sample (hz) of pose, velocity, nearby AUTHORED object ids and the '
                       'control inputs, capped at max_samples - a demonstration of SCHEMATIC unicycle '
                       'kinematics in an AUTHORED arena, not a real robot\'s trajectory',
        'what': 'one teleoperated (or scripted-reference) run of a robotics env in a world',
    },
}
WORLD_TELEOP = {
    'sample_hz': 5,
    'dt_s': 0.1,
    'max_samples': 300,
    'max_samples_policy': 'a hard cap per episode: sampling stops at max_samples (60 s at 5 Hz)',
    'opt_in': 'per episode: kept only when the learner pressed Record before driving (or ran the reference '
              'policy with Record on), AND the base recorder toggle is not off',
    'no_personal_data': 'no name, email, free text, audio, camera, biometric, device id or real-world '
                        'location - only env-local pose, velocity, AUTHORED object ids and control inputs',
    'classroom': 'K-12 / classroom mode: recording and sharing are not offered at all',
    'recorder': 'web/robokit.py',
}

STORAGE = {
    'key': 'tc-training',
    'toggle_key': 'tc-training-on',
    'cap': 500,
    'cap_policy': 'a rolling window: the oldest episode is dropped when '
                  'the cap is reached, never the newest',
    'scope': 'this browser only - localStorage, wrapped so a blocked '
             'store never breaks the page, exactly like tc-progress',
}

TRACE = {
    'toggle_key': 'tc-training-detail',
    'default': 'off - heavier than an episode record, so it needs its '
              'own opt-in rather than riding the base recorder\'s',
    'sample_hz': 1,
    'max_samples': 90,
    'max_samples_policy': 'a hard cap per episode, not a rolling window: '
                          'sampling simply stops once a run passes '
                          "max_samples seconds - the run's outcome is "
                          'unaffected either way',
    'sampled_from': "the running sim's own gauges() function - the exact "
                    'numbers the on-screen dashboard already reads out '
                    'every frame, sampled once a second rather than every '
                    'frame, and computed nowhere new for this purpose',
    'scope': 'attached to the sim episode it belongs to, inside the same '
             'tc-training record - no second storage key',
}

EXPORT_FORMAT = {
    'shape': '{ "pack": "smartcitix-trade-craft-academy-training-data", '
             '"exported": ISO-8601, "episodes": [episode, ...] }',
    'consumer': 'shaped to hand to the ml-agents fork RECORDED in '
               'meta/registry/metaverse.json as example JSON a conversion '
               'script could read',
    'not_a_demo_file': 'not a native Unity ML-Agents .demo (protobuf) '
                       'file - this bundle has never produced or tested '
                       'one, and does not claim to',
    'no_agent_trained': 'exporting this file trains nothing by itself: '
                        'no agent exists in this bundle and none is '
                        'claimed to, until one is actually trained '
                        'against this data outside it',
}

HONESTY = {
    'schematic': 'every episode comes from SCHEMATIC physics and '
                'deterministic rubrics, not a real robot or a real '
                'machine: useful for exercising a training pipeline\'s '
                'plumbing and export format, not for training a '
                'controller that will run on real equipment.',
    'anonymous': 'no name, no email, no biometric or device-identifying '
                'data is ever recorded - an episode carries only a '
                'scenario id, the control scheme the registry already '
                'declares, and the measured outcome.',
    'device_local': 'recorded to this browser\'s own storage, exactly '
                    'like the progress record, and never uploaded '
                    'automatically. Export and clear are both one click, '
                    'both the learner\'s own.',
    'not_scored': 'recording an episode changes no score and is never '
                  'read by a grader - the same guarantee this bundle '
                  'keeps for advisors, and the suite proves it the same '
                  'way, by reading the graders.',
    'consent': 'the recorder ships on, with a visible toggle: turning it '
              'off stops new episodes without touching ones already kept, '
              'and clearing them is a separate, deliberate action.',
    'granularity': 'episode-level by default. TRACE, its own off-by-'
                   'default toggle, adds a coarse (~1 Hz) sample of a '
                   "running sim's own gauges() readout - still not a "
                   'per-tick physics or joint trajectory a real '
                   'controller would train on: these are schematic '
                   'single-machine simulators, not articulated robots, '
                   'and gauges() returns display-shaped scalars and '
                   'short labels, the same numbers the dashboard already '
                   'reads out - sampled once a second instead of every '
                   'frame, computed nowhere new for this purpose.',
    'orbis_pairing': 'this log only ever gets an episode once a learner '
                     'actually trains here. orbis/ builds a text prompt '
                     'for all 111 modules whether or not anyone has - a '
                     'denser, separate, AI-SYNTHESIZED stream toward the '
                     'same ml-agents fork, never a substitute for this '
                     'real one.',
    'scripted': 'a SCRIPTED episode - actor scripted-reference - is a '
                'demonstration of a hand-written, deterministic control '
                'policy on a schematic single-machine simulator: driven '
                "from the seat's own gauges, no model behind it, no "
                'network reached, replayable from its own (level, seed, '
                'scenario) handle. Not a learned policy, not real '
                'equipment, and not a claim about any physical robot; not '
                'AI-SYNTHESIZED either, the word orbis/ keeps for '
                'generated video. It is kept through the same path, the '
                'same toggle and the same cap as a human episode, and it '
                'never credits the learner\'s own progress record.',
}

# ---------------------------------------------------------------- checks ---
sims_reg = json.load(open(ROOT / 'sims/registry/sims.json'))
agents_reg = json.load(open(ROOT / 'agents/registry/advisors.json'))
meta_reg = json.load(open(ROOT / 'meta/registry/metaverse.json'))

# the ml-agents link this pack claims must be a link this bundle actually
# already records, not a new claim invented here
assert 'ml-agents' in meta_reg['unity_bridge']['repo'], \
    'the ml-agents fork this pack cites must already be RECORDED in meta/'
assert meta_reg['unity_bridge']['provenance'].startswith('RECORDED'), \
    'training/ cites the unity_bridge only because meta/ already RECORDS it'

for kk, k in EPISODE_KINDS.items():
    assert 't' in k['fields'] and 'kind' in k['fields'], \
        f'{kk}: every episode needs a timestamp and its own kind'
    assert k['what'], f'{kk}: an episode kind nobody can explain is not one'

assert STORAGE['cap'] > 0 and STORAGE['key'] != 'tc-progress', \
    'training data must not share the progress key'

assert TRACE['toggle_key'] != STORAGE['toggle_key'], \
    'TRACE needs its own toggle, separate from the base recorder\'s'
assert TRACE['sample_hz'] > 0 and TRACE['max_samples'] > 0, \
    'TRACE must sample at a real rate and cap at a real number'
assert 'off' in TRACE['default'].lower(), \
    'TRACE must default off - it is stated as heavier than the base episode'

# the scripted tier is sims/' own declaration, cited here, never re-authored:
# every seat carries an operator, at the closed level set sims/ owns
assert 'scripted-reference' in ACTORS and 'human' in ACTORS
assert all('operator' in s for s in sims_reg['sims'].values()), \
    'every seat needs a scripted reference operator before this pack names one'
assert set(sims_reg['operator_levels']) == \
    set(next(iter(sims_reg['sims'].values()))['operator']['levels']), \
    'the level set is declared once, in sims/'
assert sims_reg['honesty']['operator'].startswith('SCRIPTED'), \
    'the operator\'s provenance word is SCRIPTED, declared by sims/'
assert 'AI-SYNTHESIZED' not in sims_reg['honesty']['operator'], \
    'SCRIPTED must never borrow the word orbis/ owns for generated video'


def pass_exprs(src):
    """Every simResults(...) call's third argument - the pass/fail
    expression - read with balanced parentheses, so an inner call such as
    Math.abs(x) is captured whole rather than cut at its first ')'."""
    out, i = [], 0
    while True:
        i = src.find("simResults('", i)
        if i < 0:
            return out
        j = src.index('(', i)
        depth, k = 0, j
        while True:
            if src[k] == '(':
                depth += 1
            elif src[k] == ')':
                depth -= 1
                if depth == 0:
                    break
            k += 1
        out.append(src[j + 1:k].partition('rows,')[2].strip())
        i = k


# the extractor must itself be proven on an inner-paren expression, or the
# guard below would silently check a truncated prefix
assert pass_exprs("simResults('x', rows, Math.abs(a) <= 1 && g(t) === 0);\n"
                  "  simResults('y', rows,\n    f(train) === 0);") \
    == ['Math.abs(a) <= 1 && g(t) === 0', 'f(train) === 0'], \
    'the pass-expression extractor must read a whole third argument'

BOOTSTRAP = '--bootstrap' in __import__('sys').argv
if not BOOTSTRAP:
    page = (ROOT / 'web/trade_craft_3d.html').read_text()
    for fn in ('function recordEpisode(', 'function trainingToggle(',
               'function exportTraining(', 'function clearTraining(',
               'function traceToggle('):
        assert fn in page, f'the page does not build the recorder: {fn} missing'
    assert '"tc-training"' in page, 'the page does not embed the declared storage key'
    assert f'"{TRACE["toggle_key"]}"' in page, \
        'the page does not embed the declared TRACE toggle key'
    for kk in EPISODE_KINDS:
        assert f"kind: '{kk}'" in page, \
            f'episode kind {kk} is declared but never recorded'
    # exactly one recorder call per declared episode kind - the shape this
    # pack promises, not more integration points quietly grown elsewhere
    assert page.count('recordEpisode({') == len(EPISODE_KINDS), \
        'recordEpisode is called somewhere other than the declared kinds'
    # wave 20: the walk and placard episodes are recorded inside anchored STEP-EPISODE blocks of the page, the dwell
    # is READ from the embedded registry, a probe-driven walker records nothing, and each kind is one literal call
    assert page.count('/* STEP-EPISODE BEGIN') >= 4 and page.count('/* STEP-EPISODE BEGIN') == page.count('/* STEP-EPISODE END'), \
        'the walk and placard recorders must sit inside balanced STEP-EPISODE blocks'
    assert 'D.training.step_episodes.placard.dwell_ms' in page, \
        "the page's placard dwell must be read from the embedded registry"
    assert f'"dwell_ms":{STEP_EPISODES["placard"]["dwell_ms"]}' in page, \
        'the page embeds a placard dwell other than the declared one'
    assert "if (wkSilent) return;" in page.split('function stepWalkEntered(')[1][:400], \
        'a probe-driven walker must record no walk episode'
    # wave 21: the station and crib episodes are recorded inside anchored STATION-EPISODE blocks, only for a station or
    # crib a lesson step of this hall names, a station only on a correct pick and a crib only on a passed check
    assert page.count('/* STATION-EPISODE BEGIN') >= 3 and page.count('/* STATION-EPISODE BEGIN') == page.count('/* STATION-EPISODE END'), \
        'the station and crib recorders must sit inside balanced STATION-EPISODE blocks'
    _sb = page.split('function stationPicked(')[1][:900]
    assert "stationTargets().has(id)" in _sb and 'stationLogged(id)' in _sb, \
        'a station episode must be recorded only for a lesson-target station, once'
    _cb = page.split('function cribPassed(')[1][:900]
    assert "cribTargets().has(dk)" in _cb and 'cribLogged(dk)' in _cb, \
        'a crib episode must be recorded only for a lesson-target crib, once'
    assert 'if (passed) cribPassed(curCrib, drill.right)' in page, \
        'a crib episode must be recorded only from a passed check'
    # the sample rate and cap the page enforces are READ from this registry
    # as embedded in the page - one truth, not a second hand-typed pair - so
    # the check is that the page reads them, and that what it reads is ours
    assert 'TRACE_MS = Math.round(1000 / D.training.trace.sample_hz)' in page, \
        "the page's TRACE sample interval must be read from the embedded registry"
    assert 'TRACE_MAX = D.training.trace.max_samples' in page, \
        "the page's TRACE cap must be read from the embedded registry"
    assert f'"sample_hz":{TRACE["sample_hz"]}' in page \
        and f'"max_samples":{TRACE["max_samples"]}' in page, \
        'the page embeds a TRACE rate or cap other than the declared ones'
    # the trace can only ever reach an episode through the sim outcome it
    # belongs to - never as a second, independent recordEpisode call - and
    # it is the sampler's own array, un-re-capped: traceStep already stops
    # at the cap, so a second slice would be a second truth about it
    assert 'trace: simTicks }' in page and 'recordEpisode({ kind: \'sim\'' in page, \
        'the trace field must be attached inside the sim episode, not recorded separately'
    assert 'simTicks.slice(' not in page, \
        'the trace cap is enforced once, in traceStep - not re-capped at record time'
    # the real guarantee is about WRITE direction, not read: recording is
    # strictly downstream of a score already final, so the boolean that
    # decides pass/fail for every seat must never mention training state -
    # it is computed first, and simResults(id, rows, PASSED) receives it.
    # Read with balanced parentheses (see pass_exprs) so an expression with
    # an inner call is checked whole
    exprs = pass_exprs(page)
    assert len(exprs) == len(sims_reg['sims']), \
        f'expected one simResults call per seat, found {len(exprs)}'
    for e in exprs:
        assert e and 'train' not in e.lower() and 'oprun' not in e.lower(), \
            f'a rubric outcome references training or operator state: {e[:80]}'
    # the scripted tier reaches the record through the SAME call, as an
    # actor field - never a fourth integration point - and a scripted run
    # never credits the learner's progress record
    assert "actor: opRun ? 'scripted-reference' : 'human'" in page, \
        'the sim episode must name its actor from the live operator state'
    assert ('operator: { level: opRun.level, seed: opRun.seed, scenario: opRun.scenario,\n'
            '      steps: opRun.step, dt: opRun.fixedDt }') in page, \
        'a scripted episode must carry its replay handle'
    assert 'if (!opRun) {' in page.split('function simResults(')[1][:1400] \
        and 'prog.sims[simId] = rec; saveProg()' in page, \
        'a scripted run must never write the learner\'s progress record'
    for fn in ('const OPERATORS = {', 'window.__tc3dSim = {',
               'function opRunHeadless(', 'function opStep('):
        assert fn in page, f'the page does not build the scripted operator: {fn} missing'
    # the whole scripted section: the policy table and the shared bench
    # policy after it, up to the driver
    ops = page.split('const OPERATORS = {')[1].split('function opAttach(')[0]
    assert 'Math.random' not in ops, \
        'the scripted operator must be deterministic: no Math.random in any policy'
    # sliced per seat - a seat's own block plus the shared bench policy when
    # it delegates there - because a step id two seats share ('settle',
    # 'hook') would otherwise be satisfied by another seat's policy and a
    # dropped step would pass unnoticed
    table, _, bench = ops.partition('function opBench(')
    starts = sorted((table.find(f"'{sid}': {{"), sid) for sid in sims_reg['sims'])
    assert all(i >= 0 for i, _ in starts), 'a seat has no scripted operator policy'
    for k, (i, sid) in enumerate(starts):
        blk = table[i:starts[k + 1][0] if k + 1 < len(starts) else None]
        if 'opBench(' in blk:
            blk += bench
        assert len(blk) > 200, f'{sid}: the policy block is too small to be one'
        for p in sims_reg['sims'][sid]['operator']['procedure']:
            assert f"'{p['id']}'" in blk, \
                f"{sid}: procedure step {p['id']} is declared but ITS policy never names it"

# ROBOLAB (wave 11): the world kinds are a roster of their own - never grown into EPISODE_KINDS, never a
# name collision with it - and the recorder that keeps them writes the SAME key, honours the SAME toggle and
# rolling cap, and samples at exactly the declared rate and cap (read, not re-typed)
assert not set(WORLD_EPISODE_KINDS) & set(EPISODE_KINDS), 'a world kind must not reuse an existing kind id'
for kk, k in WORLD_EPISODE_KINDS.items():
    assert 't' in k['fields'] and 'kind' in k['fields'] and 'v' in k['fields'], \
        f'{kk}: every world episode needs a timestamp, its kind and its kind version'
for bad in ('name', 'email', 'text', 'audio', 'camera', 'lat', 'lon', 'device'):
    assert all(bad not in f for k in WORLD_EPISODE_KINDS.values() for f in k['fields']), \
        f'a world episode field names personal data: {bad}'
assert WORLD_TELEOP['max_samples'] == round(600 * WORLD_TELEOP['dt_s'] * WORLD_TELEOP['sample_hz']), \
    'the sample cap is 60 s of samples at the declared rate'
robo_src = (ROOT / 'web/robokit.py').read_text() if (ROOT / 'web/robokit.py').exists() else ''
if robo_src:
    assert 'TR_KEY_W = D_TRAIN.storage.key' in robo_src and 'D_TRAIN.storage.toggle_key' in robo_src, \
        'robokit must write the declared training storage key and honour its toggle'
    assert 'D_TRAIN.storage.cap' in robo_src, 'robokit must enforce the shared rolling cap'
    assert 'D_TRAIN.world_teleop.sample_hz' in robo_src and 'D_TRAIN.world_teleop.max_samples' in robo_src, \
        'robokit must read the sample rate and cap from this registry'
    assert "kind: 'world-teleop'" in robo_src, 'world-teleop is declared but robokit never records it'
    assert 'Math.random' not in robo_src, 'robokit must be deterministic: no Math.random'

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

doc = {
    'pack': 'smartcitix-trade-craft-academy-training-data',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'honesty': HONESTY,
    'actors': ACTORS,
    'episode_kinds': EPISODE_KINDS,
    'step_episodes': STEP_EPISODES,
    'storage': STORAGE,
    'trace': TRACE,
    'export_format': EXPORT_FORMAT,
    'world_episode_kinds': WORLD_EPISODE_KINDS,
    'world_teleop': WORLD_TELEOP,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'training.json').write_text(json.dumps(doc, indent=1) + '\n')
print(f"training data: {len(EPISODE_KINDS)} episode kinds, cap "
      f"{STORAGE['cap']} rolling, device-local only (source stamp {stamp})")
