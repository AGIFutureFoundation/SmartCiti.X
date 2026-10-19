#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy (powered by AGI Corp) - SYNTHETIC cohort session log.

Writes cohort/fixtures/session_log.jsonl: generated test data for the Cohort
Dashboard v1 (Sprint S4). NO REAL LEARNER is in it. The first line is the
header {"synthetic": true, "note": ...}; every other line is one of two
streams, each in a shape the repository already defines:

  stream "telemetry"  an ACP-01 envelope exactly as bus/telemetry.mjs envelope()
                      builds it: event_id, ts, clock_skew_ms, ts_source,
                      learner_id, session_id, context{module_id, skill_ids,
                      difficulty, modality, device_tier, scaffold_level}, verb,
                      payload. Verbs used: attempted, hint_requested,
                      completed, failed (all in VERBS).
  stream "audit"      a safety_gate ledger row in the bus/audit.mjs AuditLog
                      shape (seq, ts, actor, action, why, learner, skill,
                      before, after) with action safety_gate.allow / .deny,
                      recorded before a floor-stage run on a simulator seat.

What the generator asserts about itself:
  * learners are pseudonyms L01..L24 - no name, email, device or biometric;
  * no affect field or value is ever written (security/privacy.mjs
    NEVER_EXPORT), and no raw stream (NEVER_STORE);
  * courses, modules and stages come from courses_roadmap/registry/courses.json, the
    stage order from its stage_map, simulator targets from each course's
    floor_sims (sims/registry/sims.json ids);
  * skill_ids are '<hall>.<strand>.<tier>' from pack/registry/skills.json, for
    courses whose `halls` is non-empty. The courses registry does NOT map a
    module to a strand, so this log uses a DECLARED synthetic mapping
    (MODULE_STRANDS below; tier from the course level). A course with no hall
    carries skill_ids: [];
  * hint rungs follow control/hints.mjs: rung 1..5, and a gate (verify) stage
    is hint-free (task ceiling 0), so no hint is ever requested there;
  * deterministic: a fixed seed and a fixed base time - rebuilding writes the
    same bytes.

  python3 cohort/synth_log.py           writes cohort/fixtures/session_log.jsonl
  python3 cohort/synth_log.py --stdout  prints the same bytes, writes nothing
"""
import datetime
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'fixtures' / 'session_log.jsonl'

SEED = 20261012
BASE = datetime.datetime(2026, 9, 14, 8, 0, 0, tzinfo=datetime.timezone.utc)
N_LEARNERS = 24

# Declared synthetic mapping: module n -> skill strand (the registry has none).
MODULE_STRANDS = {1: 'safety', 2: 'tools', 3: 'procedure', 4: 'inspection', 5: 'troubleshooting'}
LEVEL_TIER = {'Foundation': 'fundamentals', 'Apprentice': 'applied', 'Journey': 'mastery'}
STAGE_DIFFICULTY = {'home': 30, 'class': 45, 'floor': 60, 'gate': 70}
STAGE_MODALITY = {'home': 'quiz', 'class': 'station', 'floor': 'sim', 'gate': 'verification'}
STAGE_MINUTES = {'home': (8, 25), 'class': (15, 40), 'floor': (12, 35), 'gate': (10, 30)}

# Planned enrolment per course: the hair/nail/esthetics drafts and the cobot
# course are deliberately small so the dashboard's n<5 suppression is exercised.
ENROLMENT = {'TCA-110': 10, 'TCA-120': 7, 'TCA-130': 6, 'TCA-140': 9, 'TCA-150': 8,
             'TCA-160': 7, 'TCA-210': 3, 'TCA-220': 4, 'TCA-230': 2, 'TCA-310': 6,
             'TCA-320': 4, 'TCA-410': 12}


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')


def build():
    courses_reg = load('courses_roadmap/registry/courses.json')
    skills = {s['skill_id'] for s in load('pack/registry/skills.json')['skills']}
    sims = set(load('sims/registry/sims.json')['sims'])
    pack_version = load('pack/manifest.json')['pack_version']
    stages = [s['stage'] for s in courses_reg['stage_map']]
    courses = {c['code']: c for c in courses_reg['courses']}
    assert set(ENROLMENT) == set(courses), 'ENROLMENT must name every registry course'

    rng = random.Random(SEED)
    learners = [f'L{i:02d}' for i in range(1, N_LEARNERS + 1)]
    ability = {l: round(rng.uniform(0.45, 0.92), 3) for l in learners}

    # Enrolment: fill each course from the least-enrolled learners first so
    # everyone takes 2-5 courses, ties broken by the seeded generator.
    load_n = {l: 0 for l in learners}
    enrol = {l: [] for l in learners}
    for code in sorted(ENROLMENT):
        pool = sorted(learners, key=lambda l: (load_n[l], rng.random()))
        for l in sorted(pool[:ENROLMENT[code]]):
            enrol[l].append(code)
            load_n[l] += 1

    lines = []
    audit_seq = 0
    for li, learner in enumerate(learners):
        clock = BASE + datetime.timedelta(hours=li * 2)
        for ci, code in enumerate(enrol[learner]):
            course = courses[code]
            tier = LEVEL_TIER[course['level']]
            sims_for = [s for s in course['floor_sims'] if s in sims]
            session_n = 0
            # Some learners stop part-way through a course: an honest dashboard
            # must show incomplete stages, not only passes.
            stop_after = len(course['modules']) if rng.random() < 0.7 else rng.randint(1, len(course['modules']))
            for module in course['modules']:
                if module['n'] > stop_after:
                    break
                strand = MODULE_STRANDS[module['n']]
                skill_ids = sorted(f'{h}.{strand}.{tier}' for h in course['halls'])
                for sid in skill_ids:
                    assert sid in skills, sid
                for stage in stages:
                    session_n += 1
                    session_id = f'{learner}-{code}-s{session_n:02d}'
                    clock += datetime.timedelta(hours=rng.randint(3, 30))
                    seq = 0
                    tries = 0
                    while True:
                        tries += 1
                        if stage == 'floor' and sims_for:
                            target = sims_for[(module['n'] - 1) % len(sims_for)]
                            allow = rng.random() > 0.12
                            audit_seq += 1
                            lines.append({
                                'stream': 'audit', 'seq': audit_seq, 'ts': iso(clock),
                                'actor': 'safety_gate',
                                'action': 'safety_gate.allow' if allow else 'safety_gate.deny',
                                'why': ('every prerequisite met' if allow else
                                        'unmet: room PPE not confirmed at the door check'),
                                'learner': learner, 'skill': target, 'before': None,
                                'after': {'via': None, 'override_id': None},
                            })
                            if not allow:
                                clock += datetime.timedelta(minutes=rng.randint(20, 120))
                                if tries >= 4:
                                    break
                                continue
                        attempt_id = f'{session_id}-a{tries}'
                        ctx = {'module_id': f'{code}.m{module["n"]}.{stage}',
                               'skill_ids': skill_ids,
                               'difficulty': STAGE_DIFFICULTY[stage],
                               'modality': STAGE_MODALITY[stage],
                               'device_tier': 'standard',
                               'scaffold_level': 0 if stage == 'gate' else min(2, tries - 1)}
                        base_pl = {'course': code, 'module': module['n'], 'stage': stage,
                                   'attempt_id': attempt_id}

                        def emit(verb, extra=None):
                            nonlocal seq
                            seq += 1
                            lines.append({
                                'stream': 'telemetry',
                                'event_id': f'{session_id}:{seq:03d}:{verb}',
                                'ts': iso(clock), 'clock_skew_ms': 0, 'ts_source': 'client',
                                'learner_id': learner, 'session_id': session_id,
                                'context': ctx, 'verb': verb,
                                'payload': {**base_pl, **(extra or {})},
                            })

                        emit('attempted')
                        p = ability[learner] - (STAGE_DIFFICULTY[stage] - 30) / 250 + 0.08 * (tries - 1)
                        if stage != 'gate':
                            rung = 0
                            while rung < 5 and rng.random() > ability[learner] + 0.1 * rung:
                                rung += 1
                                clock += datetime.timedelta(minutes=rng.randint(1, 4))
                                emit('hint_requested', {'rung': rung})
                            p += 0.05 * rung
                        lo, hi = STAGE_MINUTES[stage]
                        minutes = rng.randint(lo, hi)
                        latency_ms = minutes * 60000 + rng.randint(0, 59) * 1000
                        clock += datetime.timedelta(milliseconds=latency_ms)
                        passed = rng.random() < p
                        emit('completed' if passed else 'failed', {'latency_ms': latency_ms})
                        clock += datetime.timedelta(minutes=rng.randint(5, 90))
                        if passed or tries >= 3:
                            break
            clock += datetime.timedelta(days=1 + ci)

    header = {'synthetic': True, 'note': 'generated test data; no real learner',
              'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
              'pack_version': pack_version, 'seed': SEED, 'generator': 'cohort/synth_log.py',
              'learners': N_LEARNERS,
              'skill_mapping': 'synthetic: module n -> strand ' + ', '.join(
                  f'{k}={v}' for k, v in MODULE_STRANDS.items()) + '; tier from course level'}
    out = [json.dumps(header, sort_keys=True, separators=(',', ':'))]
    out += [json.dumps(l, sort_keys=True, separators=(',', ':')) for l in lines]
    return '\n'.join(out) + '\n'


def main():
    text = build()
    if '--stdout' in sys.argv:
        sys.stdout.write(text)
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding='utf-8')
    print(f'cohort: wrote {OUT.relative_to(ROOT)} ({text.count(chr(10)) - 1} rows, synthetic)')


if __name__ == '__main__':
    main()
