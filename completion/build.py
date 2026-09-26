#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the completion contract builder.

WHAT WAS MISSING. A learner's progress lives in one localStorage key of the
built page (`tc-progress`: which seats passed, which crib checks passed,
which stations were taken). Nothing exported it and nothing could check an
export. This pack fixes the SHAPE of an exported record (`tc-completion/1`),
documents what each field proves and does not prove, and ships a verifier
(`verify.mjs`) that re-checks a record against the registries it names.

WHAT IT IS NOT. A digest proves the record has not changed since it was
exported; it proves nothing about who exported it. `identity.signature` is
null because this bundle has no signing key and no server, and the verifier
refuses a record that carries one. Nothing here is an accreditation, a
ticket or a certificate; no duration and no price is claimed.

PROVENANCE. DERIVED: every fact below is read from the registry that owns it
(lessons, sims, tools, stations, halls, the manifest). The pass rule per
seat is READ from sims/registry/sims.json - and that registry scores a seat
per rubric AXIS, not as one number, so no scalar threshold is stated and none
is invented. The fixture record is SCRIPTED - labelled as not a learner.
"""
import copy
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'completion.json'
FIX = HERE / 'fixture'
BUILT = '2026-09-26'


def req(mapping, key, who):
    """A missing key raises and names itself; no default is decided here."""
    if key not in mapping:
        raise KeyError(f'{who}: {key!r} does not resolve')
    return mapping[key]


MANIFEST = json.load(open(ROOT / 'pack/manifest.json'))
LESSONS = json.load(open(ROOT / 'lessons/registry/lessons.json'))
SIMS = json.load(open(ROOT / 'sims/registry/sims.json'))
CRIBS = json.load(open(ROOT / 'tools/registry/toolcribs.json'))
STATIONS = json.load(open(ROOT / 'stations/registry/stations.json'))
HALLS = json.load(open(ROOT / 'pack/registry/halls.json'))
TRAINING = json.load(open(ROOT / 'training/registry/training.json'))
EPISODE_KINDS = req(TRAINING, 'episode_kinds', 'training.json')

PRODUCT = req(MANIFEST, 'product', 'manifest')
PACK_VERSION = req(MANIFEST, 'pack_version', 'manifest')
STEP_KINDS = req(LESSONS, 'step_kinds', 'lessons.json')
LESSON_MAP = req(LESSONS, 'lessons', 'lessons.json')
LADDER = req(req(LESSONS, 'ladder', 'lessons.json'), 'edges', 'lessons.json#ladder')
SIM_MAP = req(SIMS, 'sims', 'sims.json')
CRIB_MAP = req(CRIBS, 'cribs', 'toolcribs.json')
STATION_IDS = [req(s, 'station_id', 'station') for s in req(STATIONS, 'stations', 'stations.json')]
HALL_SLUGS = [req(h, 'slug', 'hall') for h in req(HALLS, 'halls', 'halls.json')]

# ------------------------------------------------------------ evidence rule ---
# What a done step can be backed by is a property of its KIND, read from the
# lessons registry. A kind that writes a training episode is 'episode-backed'
# (the only class this bundle calls evidence-backed). Two silent kinds
# (station, crib) leave a DEVICE MARK in the local progress record the page
# keeps - a mark, not a recorded episode - so an export can carry that mark as
# 'device-mark'. The other two silent kinds leave nothing at all, and a done
# mark on them is the learner's word: 'self-reported'.
PROGRESS_RECORD_KINDS = {
    'station': {'evidence': {'station': 'station id'}, 'from': 'tc-progress.stations'},
    'crib': {'evidence': {'crib': 'district', 'passed': 'bool'}, 'from': 'tc-progress.tools[district].passed'},
}
# A step's REFERENCE fields are everything on it that names a thing, i.e. all
# but the step's own bookkeeping. Which of those an episode can be checked
# against is read from training.json#episode_kinds[kind].fields: a reference
# the episode never records is 'not checkable', named here, never defaulted.
STEP_META = {'n', 'kind', 'records', 'stage', 'reads', 'note', 'do', 'names_read', 'where', 'label_kind'}
STEP_REFS = {}
for L in req(LESSONS, 'lessons', 'lessons.json').values():
    for st in req(L, 'steps', 'lesson'):
        STEP_REFS.setdefault(req(st, 'kind', 'step'), set()).update(k for k in st if k not in STEP_META)
EVIDENCE_RULE = {}
for kind, spec in STEP_KINDS.items():
    records = req(spec, 'records', f'step_kinds.{kind}')
    if records is not None:
        ep_fields = req(req(EPISODE_KINDS, records, 'training.json#episode_kinds'), 'fields', f'episode_kinds.{records}')
        refs = sorted(STEP_REFS[kind] | {'hall'})  # the lesson's hall is a reference of every step
        checkable = [f for f in refs if f in ep_fields]
        not_checkable = [f for f in refs if f not in ep_fields]
        if kind == 'sim':
            shape = {'sim': 'sim id', 'scenario': 'scenario id', 'score': 'number', 'passed': 'bool'}
            rule = 'ids.sim / ids.scenario: the evidence sim and scenario must be the step\'s own'
        else:
            shape = {'episode': kind, 't': 'ISO-8601 string (the page writes new Date().toISOString()); Date.parse must be finite', **{f: f'the step\'s own {f}, verbatim' for f in checkable}}
            rule = 'step.episode-evidence: episode == step kind, t an ISO-8601 string that parses, every checkable field equals the step\'s own value'
        # evidenceable: every reference the step carries is recorded by its
        # episode. A kind with any unrecorded reference cannot be evidenced by
        # this bundle, so a done step of that kind is refused, not trusted.
        evidenceable = not not_checkable
        EVIDENCE_RULE[kind] = {
            'class': 'episode-backed', 'records': records, 'evidence_required_when_done': True,
            'evidenceable': evidenceable,
            'evidenceable_why': ('every reference field the step carries is recorded by the episode' if evidenceable else
                                 f'a {kind} step cannot be evidenced by this bundle: the {records} episode records '
                                 + ' and '.join(f'no {f}' for f in not_checkable)),
            'evidence_shape': shape, 'episode_fields': ep_fields,
            'checkable': checkable, 'not_checkable': not_checkable,
            'not_checkable_why': 'the episode kind never records these step references (training.json#episode_kinds), so no export can carry them and the verifier does not pretend to check them',
            'rule': rule,
        }
    elif kind in PROGRESS_RECORD_KINDS:
        EVIDENCE_RULE[kind] = {
            'class': 'device-mark', 'records': None, 'evidence_required_when_done': False,
            'evidence_shape': PROGRESS_RECORD_KINDS[kind]['evidence'],
            'from': PROGRESS_RECORD_KINDS[kind]['from'],
            'why_no_episode': req(spec, 'why_no_episode', f'step_kinds.{kind}'),
        }
    else:
        EVIDENCE_RULE[kind] = {
            'class': 'self-reported', 'records': None, 'evidence_required_when_done': False,
            'evidence_shape': None,
            'why_no_episode': req(spec, 'why_no_episode', f'step_kinds.{kind}'),
        }

RECORDING_KINDS = sorted(k for k, r in EVIDENCE_RULE.items() if r['class'] == 'episode-backed')
SILENT_KINDS = sorted(k for k, r in EVIDENCE_RULE.items() if r['class'] != 'episode-backed')

# ------------------------------------------------------------- per lesson ---
PER_LESSON = {}
tot_rec = tot_silent = 0
for lid, L in LESSON_MAP.items():
    steps = req(L, 'steps', lid)
    by = {'episode-backed': 0, 'device-mark': 0, 'self-reported': 0}
    for s in steps:
        by[EVIDENCE_RULE[req(s, 'kind', f'{lid} step')]['class']] += 1
    unevidenceable = sorted({req(st, 'kind', lid) for st in steps
                             if EVIDENCE_RULE[st['kind']]['class'] == 'episode-backed'
                             and not EVIDENCE_RULE[st['kind']]['evidenceable']})
    PER_LESSON[lid] = {
        'hall': req(L, 'hall', lid),
        # a lesson with a step of a non-evidenceable kind can never verify as complete
        'completable': not unevidenceable,
        'not_completable_why': None if not unevidenceable else
            'carries a step of a kind this bundle cannot evidence: ' + ', '.join(unevidenceable),
        'steps': len(steps),
        'recording_steps': by['episode-backed'],
        'silent_steps': by['device-mark'] + by['self-reported'],
        'episode_backed_steps': by['episode-backed'],
        'device_mark_steps': by['device-mark'],
        'self_reported_steps': by['self-reported'],
        'needs': sorted(e['needs'] for e in LADDER if e['lesson'] == lid),
    }
    tot_rec += by['episode-backed']
    tot_silent += by['device-mark'] + by['self-reported']
counts = req(LESSONS, 'counts', 'lessons.json')
assert tot_rec == req(counts, 'recording_steps', 'counts'), 'recording step count drifted from lessons.json'
assert tot_silent == req(counts, 'silent_steps', 'counts'), 'silent step count drifted from lessons.json'

# ------------------------------------------------------------- per sim ---
# The sims registry has a rubric per seat, each axis with its own pass rule.
# There is no scalar score threshold anywhere in it, so `threshold` is null
# and the verifier takes `passed` from the record instead of re-deriving it.
SIM_RULES = {}
for sid, S in SIM_MAP.items():
    axes = [{'axis': req(a, 'axis', f'{sid} rubric'), 'pass': req(a, 'pass', f'{sid} rubric')}
            for a in req(S, 'rubric', sid)]
    SIM_RULES[sid] = {
        'name': req(S, 'name', sid),
        'scenarios': [req(sc, 'id', f'{sid} scenario') for sc in req(S, 'scenarios', sid)],
        'threshold': None,
        'why': 'sims/registry/sims.json scores this seat per rubric axis ("pass" rule per axis below) '
               'and publishes no scalar score threshold; none is invented here. The page sets '
               'tc-progress.sims[id].passed from the axes, and the verifier takes `passed` from the '
               'record without re-deriving it.',
        'rubric_axes': axes,
        'scoring_contract': req(SIMS, 'scoring_contract', 'sims.json'),
    }

# --------------------------------------------------------------- honesty ---
HONESTY = {
    'proves': [
        'the record has not changed since it was exported: its SHA-256 digest recomputes over the canonical form',
        'every lesson, step, hall, seat, scenario, station and district it names exists in this bundle at the stated pack version',
        'every step marked done whose kind writes a training episode carries that episode as evidence',
        'no lesson is marked complete with a step still undone, and none ahead of its ladder prerequisite',
    ],
    'does_not_prove': [
        'who the learner is: identity.claimed is typed by the person, attested by this device only, and nothing checks it',
        'that the device was honest: a record can be written by hand and will verify if it is internally consistent',
        'that a self-reported step (walk, placard) happened at all',
        'a station or crib mark is a device-local mark, not a recorded episode',
        'that the seat was passed under supervision, or that any score means anything outside this bundle',
        'any accreditation, ticket, licence or credential; no hall, employer or authority has signed anything',
        'any duration of training, and no price is claimed',
    ],
    'digest': 'a digest proves integrity since export, not identity',
    'signature': 'null, always: this bundle has no signing key and no server; a non-null signature is refused as a forgery',
    'accreditation': 'nothing here is an accreditation',
}

DIGEST_RULE = {
    'alg': 'SHA-256',
    'over': 'canonical JSON of every top-level field except digest: keys sorted recursively, no whitespace, UTF-8',
    'numbers': 'exporters write integers for score and attempts so Python and JavaScript canonicalise alike',
}

CONTRACT = {
    'record': {'is': 'the literal string tc-completion/1', 'proves': 'which contract the verifier applies'},
    'product': {'is': 'pack/manifest.json product', 'proves': 'which product wrote it; nothing about the learner'},
    'pack_version': {'is': 'pack/manifest.json pack_version', 'proves': 'which registries the ids resolve against'},
    'exported_at': {'is': 'ISO-8601 string, device clock', 'proves': 'nothing: a device clock is not attested'},
    'identity': {'is': '{claimed: string|null, attested_by: "this device only", signature: null}',
                 'proves': 'nothing about who the learner is; claimed is typed, not checked'},
    'lessons': {'is': 'one entry per lesson the export covers: lesson id, hall, complete, steps[]',
                'proves': 'per step: done and its evidence per the evidence rule of its kind'},
    'sims': {'is': '{sim id: {passed, score, attempts}} from tc-progress.sims',
             'proves': 'the page marked the seat passed; the score has no registry threshold'},
    'tools': {'is': '{district: {passed}} from tc-progress.tools', 'proves': 'the crib check was graded passed on this device'},
    'stations': {'is': 'station ids from tc-progress.stations', 'proves': 'a station was taken at its bench on this device'},
    'honesty': {'is': 'the proves / does_not_prove lists of this registry, carried in the record',
                'proves': 'that the record says of itself what this registry says of it'},
    'digest': DIGEST_RULE,
}

# ------------------------------------------------------------- the fixture ---
def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def digest_of(record):
    body = {k: v for k, v in record.items() if k != 'digest'}
    return hashlib.sha256(canonical(body)).hexdigest()


def stamp_digest(record):
    record['digest'] = {'alg': DIGEST_RULE['alg'], 'over': DIGEST_RULE['over'], 'hex': digest_of(record)}
    return record


# The fixture completes a ladder pair: the first completable lesson that
# needs nothing, and the first completable lesson that needs exactly it.
# Computed, so a lesson that stops being completable drops out by itself.
ROOT_LESSON = next(lid for lid, p in PER_LESSON.items() if p['completable'] and not p['needs'])
NEXT_LESSON = next(lid for lid, p in PER_LESSON.items() if p['completable'] and p['needs'] == [ROOT_LESSON])
COMPLETE = [ROOT_LESSON, NEXT_LESSON]
PARTIAL = {'scaffold-read-the-tag': 2}  # first N steps done, the rest not
for lid in COMPLETE:
    assert PER_LESSON[lid]['completable'], f'fixture: {lid} is not completable'
    for need in PER_LESSON[lid]['needs']:
        assert need in COMPLETE, f'fixture: {lid} needs {need}, which the fixture does not complete'


def evidence_for(step, done, hall):
    kind = step['kind']
    if not done:
        return None
    if kind == 'sim':
        n_gated = sum(1 for a in SIM_RULES[step['sim']]['rubric_axes'] if a['pass'] != 'informational')
        return {'sim': step['sim'], 'scenario': step['scenario'], 'score': n_gated, 'passed': True}
    if kind == 'station':
        return {'station': step['station']}
    if kind == 'crib':
        return {'crib': step['crib'], 'passed': True}
    if kind in ('walkaround', 'advisor', 'crew'):
        ev = {'episode': kind, 't': f'{BUILT}T03:00:{step["n"]:02d}.000Z'}
        for f in EVIDENCE_RULE[kind]['checkable']:
            ev[f] = hall if f == 'hall' else step[f]
        return ev
    return None


def build_fixture():
    lessons, sims, tools, stations = [], {}, {}, []
    for lid, L in LESSON_MAP.items():
        n_done = len(L['steps']) if lid in COMPLETE else (PARTIAL[lid] if lid in PARTIAL else 0)
        steps = []
        for s in L['steps']:
            done = s['n'] <= n_done
            ev = evidence_for(s, done, L['hall'])
            steps.append({'step': s['n'], 'kind': s['kind'], 'done': done, 'evidence': ev})
            if done and s['kind'] == 'sim':
                rec = sims.setdefault(s['sim'], {'passed': True, 'score': ev['score'], 'attempts': 0})
                rec['attempts'] += 1
            if done and s['kind'] == 'crib':
                tools[s['crib']] = {'passed': True}
            if done and s['kind'] == 'station' and s['station'] not in stations:
                stations.append(s['station'])
        lessons.append({'lesson': lid, 'hall': L['hall'], 'complete': lid in COMPLETE, 'steps': steps})
    rec = {
        'record': 'tc-completion/1',
        'product': PRODUCT,
        'pack_version': PACK_VERSION,
        'exported_at': BUILT + 'T00:00:00Z',
        'identity': {'claimed': 'fixture — not a learner', 'attested_by': 'this device only', 'signature': None},
        'lessons': lessons,
        'sims': sims,
        'tools': tools,
        'stations': stations,
        'honesty': {'proves': HONESTY['proves'], 'does_not_prove': HONESTY['does_not_prove']},
    }
    return stamp_digest(rec)


def find_lesson(rec, lid):
    return next(x for x in rec['lessons'] if x['lesson'] == lid)


def mutants(good):
    """Each mutant breaks exactly one rule and names the rule it must fail."""
    out = {}

    m = copy.deepcopy(good)
    m['digest']['hex'] = '0' * 64
    out['bad-digest'] = ('digest', m)

    m = copy.deepcopy(good)
    m['identity']['signature'] = 'sig:' + '0' * 32
    out['forged-signature'] = ('identity.signature', stamp_digest(m))

    m = copy.deepcopy(good)
    lesson = find_lesson(m, COMPLETE[0])
    st = next(s for s in lesson['steps'] if s['kind'] in RECORDING_KINDS)
    st['evidence'] = None
    out['recording-step-without-evidence'] = ('step.recording-evidence', stamp_digest(m))

    m = copy.deepcopy(good)
    lesson = find_lesson(m, COMPLETE[1])
    lesson['steps'][-1]['done'] = False
    lesson['steps'][-1]['evidence'] = None
    out['complete-lesson-with-undone-step'] = ('lesson.complete-all-steps', stamp_digest(m))

    m = copy.deepcopy(good)
    m['sims']['not-a-seat'] = {'passed': True, 'score': 1, 'attempts': 1}
    out['unknown-sim'] = ('ids.sim', stamp_digest(m))

    m = copy.deepcopy(good)
    find_lesson(m, COMPLETE[0])['complete'] = False
    for s in find_lesson(m, COMPLETE[0])['steps']:
        s['done'] = False
        s['evidence'] = None
    out['prerequisite-not-met'] = ('ladder.prerequisite', stamp_digest(m))

    m = copy.deepcopy(good)
    lesson = find_lesson(m, COMPLETE[0])
    st = next(s for s in lesson['steps'] if s['kind'] == 'walkaround')
    st['evidence']['episode'] = 'advisor'
    out['episode-wrong-kind'] = ('step.episode-evidence', stamp_digest(m))

    m = copy.deepcopy(good)
    lesson = find_lesson(m, COMPLETE[0])
    st = next(s for s in lesson['steps'] if s['kind'] == 'walkaround')
    st['evidence']['point'] = 'no-such-point'
    out['episode-wrong-point'] = ('step.episode-evidence', stamp_digest(m))

    m = copy.deepcopy(good)
    lesson = find_lesson(m, COMPLETE[0])
    st = next(s for s in lesson['steps'] if s['kind'] == 'walkaround')
    st['evidence']['t'] = 'yesterday'
    out['episode-t-unparseable'] = ('step.episode-evidence', stamp_digest(m))

    m = copy.deepcopy(good)
    crew_lid, crew_step = next((lid, st) for lid, L in LESSON_MAP.items() for st in L['steps'] if st['kind'] == 'crew')
    entry = next(x for x in find_lesson(m, crew_lid)['steps'] if x['step'] == crew_step['n'])
    entry['done'] = True
    entry['evidence'] = {'episode': 'crew', 't': f'{BUILT}T03:00:{crew_step["n"]:02d}.000Z', 'hall': LESSON_MAP[crew_lid]['hall'],
                         'crew': crew_step['crew'], 'role': crew_step['role'], 'topic': crew_step['topic'],
                         'answer_kind': crew_step['answer_kind']}
    out['crew-done-unrecordable'] = ('step.episode-evidence', stamp_digest(m))

    m = copy.deepcopy(good)
    m['lessons'].append({'lesson': 'no-such-lesson', 'hall': HALL_SLUGS[0], 'complete': False, 'steps': []})
    out['unknown-lesson'] = ('ids.lesson', stamp_digest(m))

    m = copy.deepcopy(good)
    m['stations'].append('st999')
    out['unknown-station'] = ('ids.station', stamp_digest(m))

    m = copy.deepcopy(good)
    del m['identity']['attested_by']
    out['missing-field'] = ('record.fields', stamp_digest(m))

    m = copy.deepcopy(good)
    lesson = find_lesson(m, COMPLETE[0])
    st = next(s for s in lesson['steps'] if s['kind'] == 'sim')
    st['evidence']['scenario'] = 'no-such-scenario'
    out['unknown-scenario'] = ('ids.scenario', stamp_digest(m))

    return out


# -------------------------------------------------------------------- write ---
stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
good = build_fixture()
muts = mutants(good)

registry = {
    'pack': 'smartcitix-trade-craft-academy-completion',
    'product': PRODUCT,
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'provenance': 'DERIVED',
    'provenance_note': 'every fact here is read from the registry that owns it and re-derivable by build.py; '
                       'the fixture record is SCRIPTED and labelled as not a learner',
    'honesty': HONESTY,
    'record_tag': 'tc-completion/1',
    'progress_source': {'key': 'tc-progress', 'where': 'localStorage of the built page (web/build_3d.py)',
                        'fields': ['sims[id].passed', 'tools[district].passed', 'stations[]']},
    'contract': CONTRACT,
    'digest': DIGEST_RULE,
    'evidence_classes': {
        'episode-backed': 'the step kind records a training episode; only this class is called evidence-backed',
        'device-mark': 'station or crib: a mark in the device-local progress record, not a recorded episode',
        'self-reported': 'walk or placard: no mark at all; done is the learner\'s word',
    },
    'evidence_rule': EVIDENCE_RULE,
    'recording_kinds': RECORDING_KINDS,
    'silent_kinds': SILENT_KINDS,
    'counts': {
        'lessons': len(PER_LESSON),
        'recording_steps': tot_rec,
        'silent_steps': tot_silent,
        'episode_backed_steps': sum(p['episode_backed_steps'] for p in PER_LESSON.values()),
        'device_mark_steps': sum(p['device_mark_steps'] for p in PER_LESSON.values()),
        'self_reported_steps': sum(p['self_reported_steps'] for p in PER_LESSON.values()),
        'sims': len(SIM_RULES),
        'sims_with_threshold': sum(1 for s in SIM_RULES.values() if s['threshold'] is not None),
        'ladder_edges': len(LADDER),
        'lessons_completable': sum(1 for p in PER_LESSON.values() if p['completable']),
        'lessons_not_completable': sum(1 for p in PER_LESSON.values() if not p['completable']),
        'fixture_mutants': len(muts),
    },
    'lessons': PER_LESSON,
    'sims': SIM_RULES,
    'ladder': LADDER,
    'resolves_against': {
        'lessons': 'lessons/registry/lessons.json', 'sims': 'sims/registry/sims.json',
        'halls': 'pack/registry/halls.json', 'stations': 'stations/registry/stations.json',
        'tools': 'tools/registry/toolcribs.json', 'manifest': 'pack/manifest.json',
        'training': 'training/registry/training.json',
    },
    'verifier': {'run': 'node completion/verify.mjs <record.json>',
                 'rules': ['record.fields', 'digest', 'identity.signature', 'ids.lesson', 'ids.hall', 'ids.step',
                           'ids.sim', 'ids.scenario', 'ids.station', 'ids.district', 'step.recording-evidence', 'step.episode-evidence',
                           'lesson.complete-all-steps', 'sim.threshold', 'ladder.prerequisite']},
    'fixture': {
        'good': 'fixture/good.json',
        'mutants': {f'fixture/mutant-{name}.json': rule for name, (rule, _m) in muts.items()},
    },
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(registry, indent=1, ensure_ascii=False) + '\n')
FIX.mkdir(parents=True, exist_ok=True)
(FIX / 'good.json').write_text(json.dumps(good, indent=1, ensure_ascii=False) + '\n')
for name, (_rule, m) in muts.items():
    (FIX / f'mutant-{name}.json').write_text(json.dumps(m, indent=1, ensure_ascii=False) + '\n')
print(f'completion/registry/completion.json: {len(PER_LESSON)} lessons, {tot_rec} recording / {tot_silent} silent steps, '
      f'{len(SIM_RULES)} seats (none with a scalar threshold), {len(muts)} fixture mutants (source stamp {stamp})')
