#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — Teacher Lesson Planner v1.

Turns the courses registry (courses_roadmap/registry/courses.json) into a teacher's
week-by-week plan: week n = module n, and inside each week the four schools
stages home -> class -> floor -> gate. Every fact in a plan is read from a
registry; nothing is invented:

  * what the teacher assigns is the module's authored stage text, verbatim;
  * the floor stage names only the simulators (sims/registry/sims.json) and
    class stations (stations/registry/stations.json) the course is bound to,
    or says plainly that no floor simulator is bound yet;
  * for the hall-less beauty courses the floor and gate stages are marked
    available: false with the Beauty School status as the teacher role;
  * the mentor agents are the course's mentors from the registry;
  * minutes come from hours_planned: the course total round(hours*60) is
    split evenly across modules and each module split 20/30/35/15 across
    home/class/floor/gate, both by largest remainder so every integer sums
    exactly.

HONESTY: every plan is a PLANNED DRAFT, not reviewed by a qualified
instructor. courses_roadmap/test_lesson_plans.mjs proves the references and the
arithmetic, and re-runs this builder to prove the output is byte-identical.

  python3 courses_roadmap/lesson_plans.py           writes courses_roadmap/registry/lesson_plans.json
  python3 courses_roadmap/lesson_plans.py --stdout  prints the same bytes, writes nothing
"""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
COURSES_PATH = HERE / 'registry/courses.json'

PACK_VERSION = json.load(open(ROOT / 'pack/manifest.json'))['pack_version']
BUILT = '2026-10-12'

courses_reg = json.load(open(COURSES_PATH))
sim_ids = set(json.load(open(ROOT / 'sims/registry/sims.json'))['sims'])
station_ids = {s['station_id'] for s in
               json.load(open(ROOT / 'stations/registry/stations.json'))['stations']}

STAGES = ['home', 'class', 'floor', 'gate']
SPLIT = {'home': 20, 'class': 30, 'floor': 35, 'gate': 15}
assert sum(SPLIT.values()) == 100

NO_FLOOR = ('no floor simulator is bound in this bundle yet — run the '
            'practice as a paper or demo exercise and record it as such')
BEAUTY_STATUS = ('home and class only in this bundle: the floor and gate '
                 'stages need the separate Beauty School simulator, which is '
                 'not part of this repository')
HALL_STATUS = ('all four stages planned: the floor stage runs on the bound '
               'simulator(s) or class station(s) named in each week, or as a '
               'paper or demo exercise where none is bound')
# Stages a hall-less (beauty) course cannot run in this bundle.
BEAUTY_UNAVAILABLE = ('floor', 'gate')
TEACHER_NOTE = ('planned draft: generated from registry data and not reviewed '
                'by a qualified instructor; adapt it, and do not present it '
                'as an approved syllabus')
GATE_ROLE = ('run the unaided verification: the learner works alone with no '
             'mentor hints; the gate is not gamified, per the schools model, '
             'and no home, class or simulator time substitutes for it')


def largest_remainder(total, weights):
    """Integers proportional to weights that sum exactly to total."""
    wsum = sum(weights)
    raw = [total * w / wsum for w in weights]
    out = [int(r) for r in raw]
    order = sorted(range(len(weights)), key=lambda i: (-(raw[i] - out[i]), i))
    for i in order[:total - sum(out)]:
        out[i] += 1
    assert sum(out) == total, (total, weights, out)
    return out


def floor_role(sims, stations):
    if not sims and not stations:
        return NO_FLOOR
    parts = []
    if sims:
        parts.append('floor simulator(s) ' + ', '.join(sims))
    if stations:
        parts.append('class station(s) ' + ', '.join(stations))
    return ('supervise the practice on ' + ' and '.join(parts)
            + '; watch each seat and record results as practice only')


plans = []
for c in courses_reg['courses']:
    sims = list(c['floor_sims'])
    stations = list(c['class_stations'])
    for s in sims:
        assert s in sim_ids, f"{c['code']}: unknown sim {s}"
    for s in stations:
        assert s in station_ids, f"{c['code']}: unknown station {s}"
    beauty = not c['halls']
    total = round(c['hours_planned'] * 60)
    per_module = largest_remainder(total, [1] * len(c['modules']))
    roles = {
        'home': 'assign the reading or video and check the prepare check '
                'before class',
        'class': 'circulate between groups and run the analyze case',
        'floor': floor_role(sims, stations),
        'gate': GATE_ROLE,
    }
    weeks = []
    for mod, mins in zip(c['modules'], per_module):
        split = largest_remainder(mins, [SPLIT[s] for s in STAGES])
        text = {s['stage']: s['text'] for s in mod['stages']}
        stages = []
        for st, m in zip(STAGES, split):
            rec = {'stage': st, 'assign': text[st], 'teacher_role': roles[st],
                   'mentors': list(c['mentors']), 'minutes': m}
            if beauty and st in BEAUTY_UNAVAILABLE:
                # No hall and no Beauty School in this bundle: the planned stage
                # text is kept, but the stage cannot run here, so the teacher is
                # told that instead of a paper exercise or a verification.
                rec['available'] = False
                rec['teacher_role'] = BEAUTY_STATUS
            if st == 'floor':
                rec['floor_sims'] = sims
                rec['class_stations'] = stations
            stages.append(rec)
        week = {'week': mod['n'], 'module': mod['n'], 'title': mod['title'],
                'minutes': mins, 'stages': stages, 'wired': mod['wired']}
        if mod.get('sites'):
            week['sites'] = mod['sites']
            week['wiring_note'] = mod['wiring_note']
        weeks.append(week)
    plans.append({
        'code': c['code'], 'title': c['title'], 'trade': c['trade'],
        'status': 'planned draft',
        'hours_planned': c['hours_planned'], 'minutes_total': total,
        'mentors': list(c['mentors']), 'halls': list(c['halls']),
        'delivery_status': BEAUTY_STATUS if beauty else HALL_STATUS,
        'catalog_section': c['catalog_section'],
        'teacher_note': TEACHER_NOTE,
        'weeks': weeks,
    })

HONESTY = {
    'status': 'every lesson plan is a PLANNED DRAFT derived only from the '
              'courses registry; none has been reviewed by a qualified '
              'instructor and none is an approved syllabus',
    'credit': 'no licensing board, jurisdiction or employer has accepted any '
              'minute of these plans; simulator and station time never count '
              'toward a licence or certification',
    'marks': 'no plan is accredited, and no union, standards body or school '
             'is a partner of it',
    'minutes': 'minutes are an arithmetic split of hours_planned '
               '(20/30/35/15 across home/class/floor/gate), not a measured '
               'or validated pacing',
}

doc = {
    'pack': 'smartcitix-trade-craft-academy-lesson-plans',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': None,
    'honesty': HONESTY,
    'source': {'courses': 'courses_roadmap/registry/courses.json',
               'courses_stamp': courses_reg['source_stamp']},
    'stage_split_percent': SPLIT,
    'plans': plans,
}

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()
                       + COURSES_PATH.read_bytes()).hexdigest()[:16]
doc['source_stamp'] = stamp
text = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'

if '--stdout' in sys.argv:
    sys.stdout.buffer.write(text.encode('utf-8'))
else:
    OUT = HERE / 'registry'
    OUT.mkdir(exist_ok=True)
    (OUT / 'lesson_plans.json').write_text(text, encoding='utf-8')
    print(f'lesson plans: {len(plans)} courses, '
          f'{sum(len(p["weeks"]) for p in plans)} weekly plans, '
          f'{sum(1 for p in plans if p["halls"] and (p["weeks"][0]["stages"][2]["floor_sims"]))} '
          f'with a floor simulator (source stamp {stamp})')
