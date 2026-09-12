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
in this bundle. Three kinds of episode, one per interaction:

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

TRACE. The finer-grained recorder this file used to describe as "a
natural next step, not built yet" - built now, scoped honestly rather
than promoted past what it actually is. While TRACE is on (its own
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

PACK_VERSION = "3.2.0"
BUILT = "2026-09-11"

EPISODE_KINDS = {
    'sim': {
        'fields': ['t', 'kind', 'campus', 'hall', 'sim', 'scenario',
                   'controls', 'outcome'],
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
    'walkaround': {
        'fields': ['t', 'kind', 'campus', 'hall', 'sim', 'point'],
        'outcome_shape': None,
        'granularity': 'one point marked - not a score, the same habit '
                       'the sim registry already declares is not a gate',
        'what': 'one pre-shift walkaround point checked',
    },
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
        'recordEpisode is called somewhere other than the three declared kinds'
    # the sample rate and cap the registry declares must be the ones the
    # page actually enforces, not a second, silently-drifted pair of numbers
    trace_ms = round(1000 / TRACE['sample_hz'])
    assert f'TRACE_MS = {trace_ms}' in page, \
        "the page's TRACE sample interval does not match the declared sample_hz"
    assert f'TRACE_MAX = {TRACE["max_samples"]}' in page, \
        "the page's TRACE cap does not match the declared max_samples"
    # the trace can only ever reach an episode through the sim outcome it
    # belongs to - never as a second, independent recordEpisode call
    assert 'trace:' in page and 'recordEpisode({ kind: \'sim\'' in page, \
        'the trace field must be attached inside the sim episode, not recorded separately'
    # the real guarantee is about WRITE direction, not read: recording is
    # strictly downstream of a score already final, so the boolean that
    # decides pass/fail for every seat must never mention training state -
    # it is computed first, and simResults(id, rows, PASSED) receives it
    import re as _re
    for m in _re.finditer(r"simResults\('[a-z-]+', rows,\s*([^)]*)\)", page):
        assert 'train' not in m.group(1).lower(), \
            f'a rubric outcome references training state: {m.group(1)[:80]}'

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

doc = {
    'pack': 'smartcitix-trade-craft-academy-training-data',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'honesty': HONESTY,
    'episode_kinds': EPISODE_KINDS,
    'storage': STORAGE,
    'trace': TRACE,
    'export_format': EXPORT_FORMAT,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'training.json').write_text(json.dumps(doc, indent=1) + '\n')
print(f"training data: {len(EPISODE_KINDS)} episode kinds, cap "
      f"{STORAGE['cap']} rolling, device-local only (source stamp {stamp})")
