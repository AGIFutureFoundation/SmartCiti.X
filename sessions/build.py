#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the sessions contract builder.

WHAT WAS MISSING. The 3D page records a learner's episodes under `tc-training`
with an ISO timestamp on every one, and nothing read those timestamps as
TIME: the progress page counted episodes and the completion record matched
them one by one, but "how long did I sit, how many times, and what did each
sitting hold" was a question no surface answered. This pack makes a SESSION
a first-class, measured thing computed from the log the page already keeps -
never a new record, never a new key.

THE ONE DECLARED NUMBER. A session is a maximal run of episodes in time
order where consecutive episodes are separated by LESS than an idle gap. The
gap is declared here, once, with its reason (see GAP below). It is this
pack's own choice, not a standard, and the registry says so. Every other
figure in this pack - wall time, episodes by kind, seats, passes, best time,
streaks, the longest session - is computed from a log.

WHAT IT IS NOT. Sessions are a reading of a device-local log. They attest
time between recorded events, not attention: a browser left open records
nothing, and a learner who closed the recorder recorded nothing. Nothing here
certifies anybody, and no lesson step is ever marked done here - a session
only says which recording step KINDS it holds an episode for; completion/
decides what a step needs.

PROVENANCE. DERIVED: the episode kinds, their field lists, the actors, the
outcome shape and the trace shape are READ from training/registry/training.json;
the recording step kinds from lessons/registry/lessons.json; the ids in the
fixture from sims/registry/sims.json. The fixture is SCRIPTED - labelled as
not a learner - and every mutant breaks exactly one named rule.
"""
import copy
import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'sessions.json'
FIX = HERE / 'fixture'
BUILT = '2026-09-26'


def req(mapping, key, who):
    """A missing key raises and names itself; no default is decided here."""
    if not isinstance(mapping, dict) or key not in mapping:
        raise KeyError(f'{who}: {key!r} does not resolve')
    return mapping[key]


MANIFEST_PATH = 'pack/manifest.json'
TRAINING_PATH = 'training/registry/training.json'
LESSONS_PATH = 'lessons/registry/lessons.json'
SIMS_PATH = 'sims/registry/sims.json'
VERIFY_FILE = 'sessions/verify.mjs'

MANIFEST = json.load(open(ROOT / MANIFEST_PATH))
TRAINING = json.load(open(ROOT / TRAINING_PATH))
LESSONS = json.load(open(ROOT / LESSONS_PATH))
SIMS = json.load(open(ROOT / SIMS_PATH))

PRODUCT = req(MANIFEST, 'product', MANIFEST_PATH)
PACK_VERSION = req(MANIFEST, 'pack_version', MANIFEST_PATH)
for rel, reg in ((TRAINING_PATH, TRAINING), (LESSONS_PATH, LESSONS), (SIMS_PATH, SIMS)):
    if req(reg, 'pack_version', rel) != PACK_VERSION:
        raise AssertionError(f'{rel}: pack_version disagrees with {MANIFEST_PATH}')

# ------------------------------------------------------------ the one number ---
# 30 minutes: this pack's own choice, with its reason, and not a standard. A
# seat run on these schematic simulators is a few minutes; an advisor or crew
# exchange is seconds; a walkaround point is one click. A learner who has
# recorded nothing for half an hour has, for this reading, stopped - long
# enough that a coffee break, a re-read of a placard or a slow seat entry does
# not cut a sitting in two, short enough that an evening and the next morning
# never merge. A pair of episodes exactly the gap apart starts a new session.
GAP_MINUTES = 30
GAP_MS = GAP_MINUTES * 60 * 1000
GAP = {
    'ms': GAP_MS,
    'minutes': GAP_MINUTES,
    'rule': 'consecutive episodes in time order LESS than gap.ms apart belong to one session; a pair '
            'exactly gap.ms apart, or more, starts a new session',
    'why': f'{GAP_MINUTES} minutes is this pack\'s own choice, not a standard: a seat run here is a few '
           'minutes and an exchange is seconds, so half an hour of silence is long enough that a break, a '
           're-read placard or a slow seat entry does not cut one sitting in two, and short enough that an '
           'evening and the next morning never merge. It is the ONE declared number in this pack; every '
           'other figure is computed from the log',
    'declared_by': 'sessions/build.py, once; the progress page and the verifier READ it from this registry',
}

# ---------------------------------------------------------- from training/ ---
EPISODE_KINDS = req(TRAINING, 'episode_kinds', TRAINING_PATH)
ACTORS = req(TRAINING, 'actors', TRAINING_PATH)
TRAINING_STORAGE = req(TRAINING, 'storage', TRAINING_PATH)
TRAINING_KEY = req(TRAINING_STORAGE, 'key', TRAINING_PATH + '#storage')
TRAINING_PACK = req(TRAINING, 'pack', TRAINING_PATH)
TRACE = req(TRAINING, 'trace', TRAINING_PATH)
TRAINING_HONESTY = req(TRAINING, 'honesty', TRAINING_PATH)
HUMAN_ACTOR = 'human'
if HUMAN_ACTOR not in ACTORS:
    raise AssertionError(f'{TRAINING_PATH}#actors names no {HUMAN_ACTOR!r}')
SCRIPTED_ACTOR = next(a for a in ACTORS if a != HUMAN_ACTOR)
FIELDS_BY_KIND = {k: list(req(spec, 'fields', f'{TRAINING_PATH}#episode_kinds.{k}')) for k, spec in EPISODE_KINDS.items()}
for k, fields in FIELDS_BY_KIND.items():
    if 't' not in fields:
        raise AssertionError(f'{TRAINING_PATH}#episode_kinds.{k} records no t; sessions cannot be read from it')
SIM_SPEC = req(EPISODE_KINDS, 'sim', TRAINING_PATH + '#episode_kinds')
SIM_OUTCOME = req(SIM_SPEC, 'outcome_shape', TRAINING_PATH + '#episode_kinds.sim')
OUTCOME_ALWAYS = [k for k, v in SIM_OUTCOME.items() if 'OPTIONAL' not in v]
OUTCOME_OPTIONAL = [k for k, v in SIM_OUTCOME.items() if 'OPTIONAL' in v]
if OUTCOME_ALWAYS != ['passed', 'rows'] or OUTCOME_OPTIONAL != ['trace']:
    raise AssertionError(f'{TRAINING_PATH}#episode_kinds.sim.outcome_shape changed shape; re-derive the outcome rule')
m = re.match(r'\[\{([a-z_, ]+)\}\]', req(SIM_OUTCOME, 'rows', TRAINING_PATH + '#episode_kinds.sim.outcome_shape'))
if m is None:
    raise AssertionError(f'{TRAINING_PATH}#episode_kinds.sim.outcome_shape.rows does not start with a [{{...}}] shape')
ROW_KEYS = [k.strip() for k in m.group(1).split(',')]
m = re.match(r'\[\{([a-z_, ]+)\}\]', req(SIM_OUTCOME, 'trace', TRAINING_PATH + '#episode_kinds.sim.outcome_shape'))
if m is None:
    raise AssertionError(f'{TRAINING_PATH}#episode_kinds.sim.outcome_shape.trace does not start with a [{{...}}] shape')
TRACE_KEYS = [k.strip() for k in m.group(1).split(',')]
# does a sim episode carry a duration? Read, not assumed: no field of the sim
# kind is a duration, so seat time is NOT recordable and episodes are counted
DURATION_FIELDS = [f for f in FIELDS_BY_KIND['sim'] if f in ('duration', 'duration_ms', 'elapsed', 'seconds', 'wall')]
SEAT_TIME_RECORDABLE = len(DURATION_FIELDS) > 0
if SEAT_TIME_RECORDABLE:
    raise AssertionError(f'{TRAINING_PATH}#episode_kinds.sim now carries {DURATION_FIELDS}; extend the reading to sum it')
# the axis whose value the 3D page reads as a run's best time (web/build_3d.py
# simResults: rows.find((r) => r.axis === 'time')), held to the seat rubrics
BEST_AXIS = 'time'
SIM_MAP = req(SIMS, 'sims', SIMS_PATH)
AXES_BY_SIM = {sid: [req(a, 'axis', f'{sid} rubric') for a in req(S, 'rubric', sid)] for sid, S in SIM_MAP.items()}
if not any(BEST_AXIS in axes for axes in AXES_BY_SIM.values()):
    raise AssertionError(f'{SIMS_PATH}: no seat rubric has a {BEST_AXIS!r} axis; best time cannot be read')

# ------------------------------------------------------------ from lessons/ ---
STEP_KINDS = req(LESSONS, 'step_kinds', LESSONS_PATH)
STEP_RECORDS = {}
for sk, spec in STEP_KINDS.items():
    rec = req(spec, 'records', f'{LESSONS_PATH}#step_kinds.{sk}')
    if rec is None:
        continue
    if rec not in EPISODE_KINDS:
        raise AssertionError(f'{LESSONS_PATH}#step_kinds.{sk} records {rec!r}, not an episode kind')
    STEP_RECORDS[sk] = rec
SILENT_STEP_KINDS = sorted(k for k in STEP_KINDS if k not in STEP_RECORDS)


# ------------------------------------------------------------ the splitter ---
def parse_iso(t):
    """Date.parse's answer for the ISO string the 3D page writes, in ms."""
    import datetime
    if not isinstance(t, str):
        raise ValueError('t is not a string')
    s = t[:-1] + '+00:00' if t.endswith('Z') else t
    d = datetime.datetime.fromisoformat(s)
    if d.tzinfo is None:
        d = d.replace(tzinfo=datetime.timezone.utc)
    return int(round(d.timestamp() * 1000))


def time_value(rows):
    row = None
    for r in rows:
        if isinstance(r, dict) and 'axis' in r and r['axis'] == BEST_AXIS:
            row = r
            break
    if row is None or 'value' not in row or not isinstance(row['value'], (int, float)) or isinstance(row['value'], bool):
        return None
    return row['value']


def sessions_of(training, gap_ms):
    """The Python twin of sessionsOf in sessions/verify.mjs - the same rule,
    written once more so the fixture's claimed table is an independent
    computation the JS verifier must recompute to equality."""
    eps = sorted(((parse_iso(ep['t']), i, ep) for i, ep in enumerate(training)), key=lambda x: (x[0], x[1]))
    sessions = []
    cur = None
    last_ms = start_ms = None
    for ms, i, ep in eps:
        if cur is None or ms - last_ms >= gap_ms:
            cur = {'n': len(sessions) + 1, 'start': ep['t'], 'end': ep['t'], 'wall_ms': 0, 'episodes': 0, 'by_kind': {},
                   'halls': [], 'campuses': [], 'seats': {}, 'scripted_runs': 0, 'walkaround_points': [],
                   'advisor_exchanges': 0, 'crew_exchanges': 0, 'traces': 0, 'samples': 0, 'could_advance': {}}
            sessions.append(cur)
            start_ms = ms
        cur['end'] = ep['t']
        last_ms = ms
        cur['wall_ms'] = ms - start_ms
        cur['episodes'] += 1
        kind = ep['kind']
        cur['by_kind'][kind] = (cur['by_kind'][kind] if kind in cur['by_kind'] else 0) + 1
        if isinstance(ep['hall'], str) and ep['hall'] not in cur['halls']:
            cur['halls'].append(ep['hall'])
        if isinstance(ep['campus'], str) and ep['campus'] not in cur['campuses']:
            cur['campuses'].append(ep['campus'])
        if kind == 'sim':
            out = ep['outcome']
            if ep['actor'] != HUMAN_ACTOR:
                cur['scripted_runs'] += 1
            else:
                sc = '(none)' if ep['scenario'] is None else str(ep['scenario'])
                seat = cur['seats'].setdefault(ep['sim'], {'attempts': 0, 'passes': 0, 'best_time': None, 'scenarios': {}})
                s = seat['scenarios'].setdefault(sc, {'attempts': 0, 'passes': 0, 'best_time': None})
                seat['attempts'] += 1
                s['attempts'] += 1
                if out['passed']:
                    seat['passes'] += 1
                    s['passes'] += 1
                    tv = time_value(out['rows'])
                    if tv is not None:
                        if seat['best_time'] is None or tv < seat['best_time']:
                            seat['best_time'] = tv
                        if s['best_time'] is None or tv < s['best_time']:
                            s['best_time'] = tv
            if 'trace' in out:
                cur['traces'] += 1
                cur['samples'] += len(out['trace'])
        elif kind == 'walkaround':
            key = str(ep['sim']) + ':' + str(ep['point'])
            if key not in cur['walkaround_points']:
                cur['walkaround_points'].append(key)
        elif kind == 'advisor':
            cur['advisor_exchanges'] += 1
        elif kind == 'crew':
            cur['crew_exchanges'] += 1
        else:
            raise ValueError(f'episode {i}: unknown kind {kind!r}')
    for s in sessions:
        for sk, ek in STEP_RECORDS.items():
            s['could_advance'][sk] = ek in s['by_kind'] and (ek != 'sim' or len(s['seats']) > 0)
        s['halls'].sort()
        s['campuses'].sort()
        s['walkaround_points'] = len(sorted(s['walkaround_points']))
    seats = {}
    sim_episodes = traced_span = scripted_sim_s = traces = samples = 0
    by_kind = {}
    for ms, i, ep in eps:
        by_kind[ep['kind']] = (by_kind[ep['kind']] if ep['kind'] in by_kind else 0) + 1
        if ep['kind'] != 'sim':
            continue
        sim_episodes += 1
        out = ep['outcome']
        if 'trace' in out:
            traces += 1
            samples += len(out['trace'])
            if len(out['trace']) > 1:
                traced_span += out['trace'][-1]['t'] - out['trace'][0]['t']
        if ep['actor'] != HUMAN_ACTOR:
            op = ep['operator']
            if isinstance(op['dt'], (int, float)) and not isinstance(op['dt'], bool):
                scripted_sim_s += op['steps'] * op['dt']
            continue
        seat = seats.setdefault(ep['sim'], {'attempts': 0, 'passes': 0, 'pass_rate': None, 'best_time': None,
                                            'longest_pass_streak': 0, 'current_pass_streak': 0})
        seat['attempts'] += 1
        if out['passed']:
            seat['passes'] += 1
            seat['current_pass_streak'] += 1
            seat['longest_pass_streak'] = max(seat['longest_pass_streak'], seat['current_pass_streak'])
            tv = time_value(out['rows'])
            if tv is not None and (seat['best_time'] is None or tv < seat['best_time']):
                seat['best_time'] = tv
        else:
            seat['current_pass_streak'] = 0
    for s in seats.values():
        s['pass_rate'] = None if s['attempts'] == 0 else s['passes'] / s['attempts']
    longest = None
    for s in sessions:
        if longest is None or s['wall_ms'] > longest['wall_ms']:
            longest = {'n': s['n'], 'wall_ms': s['wall_ms'], 'episodes': s['episodes']}
    rollups = {
        'sessions': len(sessions), 'episodes': len(eps), 'by_kind': by_kind,
        'total_wall_ms': sum(s['wall_ms'] for s in sessions),
        'seat_time': {'recordable': False, 'sim_episodes': sim_episodes, 'traced_span_ms': traced_span,
                      'scripted_sim_s': scripted_sim_s},
        'seats': seats, 'longest_session': longest, 'traces': traces, 'samples': samples,
    }
    return {'gap_ms': gap_ms, 'sessions': sessions, 'rollups': rollups}


# ------------------------------------------------------------- the fixture ---
FIX_SIM = sorted(SIM_MAP.keys())[0]
FIX_SIM2 = sorted(SIM_MAP.keys())[1]
FIX_HALL = req(SIM_MAP[FIX_SIM], 'halls', FIX_SIM)[0]
FIX_HALL2 = req(SIM_MAP[FIX_SIM2], 'halls', FIX_SIM2)[0]
FIX_SCENARIO = req(SIM_MAP[FIX_SIM], 'scenarios', FIX_SIM)[0]
FIX_CAMPUS = req(FIX_SCENARIO, 'campus', f'{FIX_SIM} scenario')
FIX_SCENARIO2 = req(SIM_MAP[FIX_SIM2], 'scenarios', FIX_SIM2)[0]
FIX_CAMPUS2 = req(FIX_SCENARIO2, 'campus', f'{FIX_SIM2} scenario')
FIX_CONTROLS = [req(c, 'action', f'{FIX_SIM} control') for c in req(SIM_MAP[FIX_SIM], 'controls', FIX_SIM)]
FIX_CONTROLS2 = [req(c, 'action', f'{FIX_SIM2} control') for c in req(SIM_MAP[FIX_SIM2], 'controls', FIX_SIM2)]
FIX_POINT = req(req(SIM_MAP[FIX_SIM], 'walkaround', FIX_SIM)[0], 'id', f'{FIX_SIM} walkaround')
if BEST_AXIS not in AXES_BY_SIM[FIX_SIM]:
    raise AssertionError(f'fixture: seat {FIX_SIM} has no {BEST_AXIS!r} axis to read a best time from')
FIX_LABEL = 'fixture - not a learner'


def rows_for(sim, ok, time_value_s):
    return [{'axis': a, 'value': (time_value_s if a == BEST_AXIS else 1), 'ok': ok} for a in AXES_BY_SIM[sim]]


def episode(kind, t, **fields):
    ep = {'t': t, 'kind': kind}
    for f in FIELDS_BY_KIND[kind]:
        if f in ('t', 'kind'):
            continue
        if f == 'operator' and fields['actor'] != SCRIPTED_ACTOR:
            continue
        if f not in fields:
            raise KeyError(f'fixture: a {kind} episode needs {f!r}')
        ep[f] = fields[f]
    extra = set(fields) - set(FIELDS_BY_KIND[kind])
    if extra:
        raise KeyError(f'fixture: {kind} episode given fields the registry does not declare: {sorted(extra)}')
    return ep


def iso(ms):
    import datetime
    return datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')


def synthetic_gauges(i):
    return {'load_pct': 30 + i * 5, 'hook_cm': 150 + i * 25, 'wind': 'calm', 'note': 'fixture gauges - not a machine'}


def build_fixture():
    T0 = parse_iso(f'{BUILT}T03:00:00.000Z')
    S = 1000
    # session 1: a walkaround point, a failed run, a passed run with a trace, an advisor exchange
    t0, t1, t2, t3 = T0, T0 + 60 * S, T0 + 180 * S, T0 + 240 * S
    # session 2 starts ONE SECOND OVER the gap; inside it a pair ONE SECOND SHORT of the gap stays together
    t4 = t3 + GAP_MS + S
    t5 = t4 + GAP_MS - S
    t6 = t5 + 30 * S
    # session 3: two hours on, another seat with no scenario chosen
    t7 = t6 + 2 * 3600 * S
    t8 = t7 + 120 * S
    episodes = [
        episode('walkaround', iso(t0), campus=FIX_CAMPUS, hall=FIX_HALL, sim=FIX_SIM, point=FIX_POINT),
        episode('sim', iso(t1), campus=FIX_CAMPUS, hall=FIX_HALL, sim=FIX_SIM, scenario=FIX_SCENARIO['id'],
                controls=FIX_CONTROLS, actor=HUMAN_ACTOR, outcome={'passed': False, 'rows': rows_for(FIX_SIM, False, 80)}),
        episode('sim', iso(t2), campus=FIX_CAMPUS, hall=FIX_HALL, sim=FIX_SIM, scenario=FIX_SCENARIO['id'],
                controls=FIX_CONTROLS, actor=HUMAN_ACTOR,
                outcome={'passed': True, 'rows': rows_for(FIX_SIM, True, 61.5),
                         'trace': [{'t': i * 1000, 'gauges': synthetic_gauges(i)} for i in range(4)]}),
        episode('advisor', iso(t3), campus=FIX_CAMPUS, hall=FIX_HALL, advisor='fixture-advisor', topic='fixture-topic',
                answer_kind='record'),
        episode('sim', iso(t4), campus=FIX_CAMPUS, hall=FIX_HALL, sim=FIX_SIM, scenario=FIX_SCENARIO['id'],
                controls=FIX_CONTROLS, actor=HUMAN_ACTOR, outcome={'passed': True, 'rows': rows_for(FIX_SIM, True, 55)}),
        episode('crew', iso(t5), campus=FIX_CAMPUS, hall=FIX_HALL, crew='fixture-crew', role='fixture-role',
                topic='fixture-topic', answer_kind='registry'),
        episode('sim', iso(t6), campus=FIX_CAMPUS, hall=FIX_HALL, sim=FIX_SIM, scenario=FIX_SCENARIO['id'],
                controls=FIX_CONTROLS, actor=SCRIPTED_ACTOR,
                operator={'level': 'fixture-level', 'seed': 7, 'scenario': FIX_SCENARIO['id'], 'steps': 120, 'dt': 0.05},
                outcome={'passed': True, 'rows': rows_for(FIX_SIM, True, 40)}),
        episode('sim', iso(t7), campus=FIX_CAMPUS2, hall=FIX_HALL2, sim=FIX_SIM2, scenario=None,
                controls=FIX_CONTROLS2, actor=HUMAN_ACTOR, outcome={'passed': False, 'rows': []}),
        episode('sim', iso(t8), campus=FIX_CAMPUS2, hall=FIX_HALL2, sim=FIX_SIM2, scenario=None,
                controls=FIX_CONTROLS2, actor=HUMAN_ACTOR, outcome={'passed': True, 'rows': rows_for(FIX_SIM2, True, 90)}),
    ]
    reading = sessions_of(episodes, GAP_MS)
    if reading['rollups']['sessions'] != 3:
        raise AssertionError(f'fixture: expected 3 sessions, the splitter found {reading["rollups"]["sessions"]}')
    return {
        'pack': TRAINING_PACK,
        'exported': BUILT + 'T00:00:00Z',
        'label': FIX_LABEL,
        'fixture': 'this log is SCRIPTED by sessions/build.py from synthetic episodes shaped by ' + TRAINING_PATH
                   + '; it is not a learner, its gauges are not a machine, and its sessions block is a CLAIM the '
                     'verifier recomputes rather than believes',
        'episodes': episodes,
        'sessions': reading,
    }


def mutants(good):
    """Each mutant breaks exactly one rule and names the rule it must fail."""
    out = {}
    eps = lambda m: m['episodes']

    m = copy.deepcopy(good)
    eps(m)[0]['t'] = 'yesterday'
    out['t-unparseable'] = ('episode.t', m)

    m = copy.deepcopy(good)
    eps(m)[3]['kind'] = 'joystick'
    out['unknown-kind'] = ('episode.kind', m)

    m = copy.deepcopy(good)
    del eps(m)[1]['outcome']['passed']
    out['outcome-missing-passed'] = ('episode.outcome', m)

    m = copy.deepcopy(good)
    eps(m)[1]['outcome']['score'] = 0.9
    out['outcome-foreign-key'] = ('episode.outcome', m)

    m = copy.deepcopy(good)
    eps(m)[2]['outcome']['trace'][1] = {'t': 1000, 'gauges': synthetic_gauges(1), 'joint_angles': [0, 0, 0]}
    out['trace-sample-foreign-key'] = ('episode.outcome', m)

    # the same log cut at a gap the registry does not declare: one second over
    # the declared gap, so the fixture's own one-second-over boundary merges
    m = copy.deepcopy(good)
    other = sessions_of(eps(m), GAP_MS + 2000)
    m['sessions']['sessions'] = other['sessions']  # the roll-ups are left as computed, so ONE rule fails
    if len(other['sessions']) == len(good['sessions']['sessions']):
        raise AssertionError('mutant sessions-split-wrong-gap: the wider gap did not merge the one-second-over boundary')
    out['sessions-split-wrong-gap'] = ('sessions.claimed', m)

    m = copy.deepcopy(good)
    m['sessions']['gap_ms'] = GAP_MS + 2000
    out['gap-not-the-registry'] = ('sessions.gap', m)

    m = copy.deepcopy(good)
    m['sessions']['rollups']['sessions'] = 9
    m['sessions']['rollups']['total_wall_ms'] = 12345678
    out['typed-rollup'] = ('rollups.claimed', m)

    m = copy.deepcopy(good)
    m['sessions']['rollups']['seats'][FIX_SIM]['longest_pass_streak'] = 3
    out['typed-streak'] = ('rollups.claimed', m)

    m = copy.deepcopy(good)
    m['pack'] = 'some-other-pack'
    out['wrong-pack'] = ('input.shape', m)

    return out


RULES = ['input.shape', 'episode.t', 'episode.kind', 'episode.outcome', 'sessions.gap', 'sessions.claimed', 'rollups.claimed']
SESSION_SHAPE = {
    'n': '1-based index in time order',
    'start': 't of the first episode (the ISO string as recorded)',
    'end': 't of the last episode',
    'wall_ms': 'end - start in ms: time between the first and last recorded event, not time at the keys',
    'episodes': 'episodes in the session',
    'by_kind': '{kind: n} over ' + TRAINING_PATH + '#episode_kinds',
    'halls': 'hall slugs visited, sorted, unique',
    'campuses': 'campus ids visited, sorted, unique',
    'seats': '{sim: {attempts, passes, best_time, scenarios: {scenario|"(none)": {attempts, passes, best_time}}}} '
             f'over {HUMAN_ACTOR} sim episodes only; attempts = episodes, passes = outcome.passed true, best_time = '
             f'the smallest numeric value of the {BEST_AXIS!r} rubric row among passed runs, or null when no passed '
             'run carries one',
    'scripted_runs': f'sim episodes whose actor is not {HUMAN_ACTOR}: counted apart, credited to no seat',
    'walkaround_points': 'distinct sim:point pairs marked',
    'advisor_exchanges': 'advisor episodes',
    'crew_exchanges': 'crew episodes',
    'traces': 'sim episodes carrying outcome.trace',
    'samples': 'trace samples across them',
    'could_advance': '{lesson step kind: bool} for every step kind lessons.json says records an episode: true when '
                     'the session holds at least one episode of that kind (a human seat run, for sim). By KIND only: '
                     'nothing here matches a step\'s own reference, and no step is ever marked done here',
}
ROLLUP_SHAPE = {
    'sessions': 'count', 'episodes': 'count', 'by_kind': '{kind: n}',
    'total_wall_ms': 'sum of wall_ms over sessions',
    'seat_time': {
        'recordable': False,
        'why': f'{TRAINING_PATH}#episode_kinds.sim.fields carries no duration ({", ".join(FIELDS_BY_KIND["sim"])}), so '
               'time at a seat cannot be summed; sim episodes are counted instead',
        'sim_episodes': 'count of sim episodes, every actor',
        'traced_span_ms': 'sum over traced episodes of last sample t minus first sample t: a LOWER bound on those '
                          'runs only, at ~1 Hz, and nothing about untraced runs',
        'scripted_sim_s': 'sum of operator.steps x operator.dt over scripted-reference runs whose dt is a number: '
                          'deterministic sim time of a headless reference run, never the learner\'s',
    },
    'seats': '{sim: {attempts, passes, pass_rate, best_time, longest_pass_streak, current_pass_streak}} over human '
             'sim episodes in time order across all sessions; pass_rate = passes / attempts',
    'longest_session': '{n, wall_ms, episodes} of the session with the greatest wall_ms (the earliest on a tie), or null',
    'traces': 'count', 'samples': 'count',
}
HONESTY = {
    'reading': 'a session is a reading of a device-local log: it attests time between recorded events on one '
               'browser, not attention, not presence at the keys, and nothing here is a certification',
    'not_recorded': 'a browser left open records nothing and a recorder switched off records nothing, so an idle '
                    'session and an absent one look the same here: absent',
    'seat_time': ROLLUP_SHAPE['seat_time']['why'],
    'no_step_done': 'could_advance names step KINDS a session holds an episode for; whether any lesson step is done '
                    'is completion/\'s question and is decided there against the step\'s own reference',
    'scripted': f'a run whose actor is not {HUMAN_ACTOR} is counted as scripted_runs and credited to no seat, no '
                'pass and no streak: ' + req(TRAINING_HONESTY, 'scripted', TRAINING_PATH + '#honesty'),
    'device_local': req(TRAINING_HONESTY, 'device_local', TRAINING_PATH + '#honesty'),
    'schematic': req(TRAINING_HONESTY, 'schematic', TRAINING_PATH + '#honesty'),
    'gap': GAP['why'],
    'order': 'episodes are sorted by t (stable on recorded order) before splitting: the page appends in time order '
             'and its rolling cap drops only the oldest, so a log out of order was edited by hand and is sorted '
             'rather than trusted',
    'fixture': 'the fixture is SCRIPTED and labelled ' + FIX_LABEL,
}

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
good = build_fixture()
muts = mutants(good)
verify_src = (ROOT / VERIFY_FILE).read_text(encoding='utf-8')
if '/* SESSIONS_OF:BEGIN' not in verify_src or '/* SESSIONS_OF:END */' not in verify_src:
    raise AssertionError(f'{VERIFY_FILE} no longer marks sessionsOf; the page cannot carry it')

registry = {
    'pack': 'smartcitix-trade-craft-academy-sessions',
    'product': PRODUCT,
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'provenance': 'DERIVED',
    'provenance_note': 'every fact here is read from the registry that owns it and re-derivable by build.py: the '
                       'episode shapes from ' + TRAINING_PATH + ', the recording step kinds from ' + LESSONS_PATH
                       + ', the fixture ids from ' + SIMS_PATH + '. The gap is the ONE declared number. The fixture '
                       'is SCRIPTED and labelled as not a learner',
    'honesty': HONESTY,
    'gap': GAP,
    'definition': 'a SESSION is a maximal run of episodes in time order where every consecutive pair is separated '
                  'by less than gap.ms',
    'source': {'key': TRAINING_KEY, 'registry': TRAINING_PATH, 'where': 'localStorage of the built 3D page',
               'export_shape': req(req(TRAINING, 'export_format', TRAINING_PATH), 'shape', TRAINING_PATH + '#export_format'),
               'contribution_shape': 'tc-contribution/1, validated through contrib/verify.mjs first'},
    'episode_kinds': {k: {'fields': FIELDS_BY_KIND[k], 'what': req(EPISODE_KINDS[k], 'what', f'{TRAINING_PATH}#episode_kinds.{k}')}
                      for k in EPISODE_KINDS},
    'actors': ACTORS,
    'human_actor': HUMAN_ACTOR,
    'outcome': {
        'keys_always': OUTCOME_ALWAYS,
        'keys_optional': OUTCOME_OPTIONAL,
        'row_keys': ROW_KEYS,
        'trace_sample_keys': TRACE_KEYS,
        'trace_max_samples': req(TRACE, 'max_samples', TRAINING_PATH + '#trace'),
        'best_axis': BEST_AXIS,
        'best_axis_from': 'web/build_3d.py simResults reads rows.find((r) => r.axis === \'time\') as a run\'s best; '
                          'runs and best in tc-progress are that page\'s own tallies and are NOT read here - attempts, '
                          'passes and best are recomputed from the episodes',
        'from': TRAINING_PATH + '#episode_kinds.sim.outcome_shape',
    },
    'seat_time': {'recordable': SEAT_TIME_RECORDABLE, 'sim_fields': FIELDS_BY_KIND['sim'], 'why': ROLLUP_SHAPE['seat_time']['why']},
    'lesson_steps': {
        'records': STEP_RECORDS,
        'silent': SILENT_STEP_KINDS,
        'from': LESSONS_PATH + '#step_kinds[kind].records',
        'rule': HONESTY['no_step_done'],
    },
    'session_shape': SESSION_SHAPE,
    'rollup_shape': ROLLUP_SHAPE,
    'function': {
        'name': 'sessionsOf',
        'file': VERIFY_FILE,
        'markers': ['/* SESSIONS_OF:BEGIN', '/* SESSIONS_OF:END */'],
        'carried_into': 'web/trade_craft_progress.html <script id="sessions-js">, verbatim, by web/build_progress.py',
        'signature': 'sessionsOf(training, gapMs, humanActor, stepRecords, bestAxis)',
        'page_reads_gap_from': 'the embedded copy of this registry (D.sessions.gap.ms); the page JS types no gap',
    },
    'verifier': {
        'file': VERIFY_FILE,
        'usage': 'node sessions/verify.mjs <tc-training.json | export.json | contribution.json>',
        'rules': RULES,
        'last_line': 'sessions are a reading of a device-local log; they attest time between recorded events, '
                     'not attention, and nothing here is a certification',
    },
    'fixture': {
        'label': FIX_LABEL,
        'good': 'fixture/log.json',
        'mutants': {name: {'file': f'fixture/mutant-{name}.json', 'fails': rule} for name, (rule, _) in muts.items()},
        'sessions': good['sessions']['rollups']['sessions'],
        'episodes': good['sessions']['rollups']['episodes'],
        'boundaries': {'one_second_over': 'session 1 -> 2: the pair is gap.ms + 1000 apart and splits',
                       'one_second_short': 'inside session 2: a pair gap.ms - 1000 apart stays together',
                       'two_hours': 'session 2 -> 3'},
    },
    'counts': {
        'episode_kinds': len(EPISODE_KINDS),
        'recording_step_kinds': len(STEP_RECORDS),
        'silent_step_kinds': len(SILENT_STEP_KINDS),
        'rules': len(RULES),
        'mutants': len(muts),
        'fixture_episodes': len(good['episodes']),
        'fixture_sessions': len(good['sessions']['sessions']),
    },
}

OUT.parent.mkdir(parents=True, exist_ok=True)
FIX.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(registry, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
(FIX / 'log.json').write_text(json.dumps(good, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
for name, (rule, rec) in muts.items():
    (FIX / f'mutant-{name}.json').write_text(json.dumps(rec, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
print(f'sessions: gap {GAP_MINUTES} min (the one declared number), {len(RULES)} rules, {len(muts)} mutants, fixture '
      f'{len(good["episodes"])} episodes in {len(good["sessions"]["sessions"])} sessions, {len(STEP_RECORDS)} recording '
      f'step kinds from {LESSONS_PATH} (source stamp {stamp})')
