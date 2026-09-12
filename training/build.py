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
                panel shows). EPISODE-LEVEL, not frame-by-frame: this
                records what a run was attempted under and how it ended,
                not a per-tick joint trajectory. A finer-grained recorder
                is a natural next step and is not built yet - stated
                plainly rather than implied.
  * advisor   - which advisor, which fixed topic, and whether the answer
                was `read` from another registry or `say` written here -
                never the words themselves, which the advisor registry
                already owns.
  * walkaround - which point, on which seat.

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
those the same way they clear progress, on purpose, separately.

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
                           'rows': '[{axis, value, ok}] - the rubric rows'},
        'granularity': 'episode-level: the scenario and control scheme a '
                       'run was attempted under, and how it ended - not a '
                       'per-tick trajectory',
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
    'granularity': 'episode-level records, not frame-by-frame joint '
                   'trajectories - a finer-grained recorder is a natural '
                   'next step and is not built yet.',
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

BOOTSTRAP = '--bootstrap' in __import__('sys').argv
if not BOOTSTRAP:
    page = (ROOT / 'web/trade_craft_3d.html').read_text()
    for fn in ('function recordEpisode(', 'function trainingToggle(',
               'function exportTraining(', 'function clearTraining('):
        assert fn in page, f'the page does not build the recorder: {fn} missing'
    assert '"tc-training"' in page, 'the page does not embed the declared storage key'
    for kk in EPISODE_KINDS:
        assert f"kind: '{kk}'" in page, \
            f'episode kind {kk} is declared but never recorded'
    # exactly one recorder call per declared episode kind - the shape this
    # pack promises, not more integration points quietly grown elsewhere
    assert page.count('recordEpisode({') == len(EPISODE_KINDS), \
        'recordEpisode is called somewhere other than the three declared kinds'
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
    'export_format': EXPORT_FORMAT,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'training.json').write_text(json.dumps(doc, indent=1) + '\n')
print(f"training data: {len(EPISODE_KINDS)} episode kinds, cap "
      f"{STORAGE['cap']} rolling, device-local only (source stamp {stamp})")
