#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy - the course catalogue and the lesson supplements (wave 16).

WHAT THIS IS. A catalogue that groups the walkable lessons of lessons/registry/lessons.json into COURSES, and one
SUPPLEMENT per lesson, written to courses/registry/courses.json. Nothing here is a new fact. Every course and every
supplement is composed by a rule stated in this file (and printed into the registry under `rules`) from what the
registries that own the facts already say:

  * a TRADE course per hall (pack/registry/halls.json), grouped by its district (unions/registry/districts.json):
    the lessons that stand in that hall, in ladder order (lessons.json#ladder.depth, then registry order);
  * a STRAND course per strand (the eleven rooms of web/interiors.py): every lesson whose strand it is, same order;
  * prerequisites are the ladder's own edges (lessons.json#ladder.prerequisites), split into the ones inside the
    course and the ones that point at another course;
  * seat time is counted, never timed: the seats a hall is bound to (sims/registry/sims.json#hall_bindings), and the
    seat runs, walkaround points and crew asks the lessons hold. sims/ declares no duration for any scenario (its
    `time` rubric axis is "informational"), so no minutes are given anywhere - a minute here would be invented;
  * K-12 bands are DERIVED by a rule that rests on the words of schools/registry/schools.json#bands[].offer, and the
    build stops if those words change.

A supplement (one per lesson) holds a glossary (tool, room, placard, seat and role names with the meaning the owning
registry gives them), key concepts (quoted, with the record each comes from), safety notes (the door placard quoted
verbatim in the same form the 3D page's condLine() prints it - unverified general practice), self-check questions
whose answers are registry ids, a worksheet (the steps as lines to fill in) and where to go (rooms, crib, advisors,
seats, crews). Questions and worksheet lines are stored as i18n template keys plus arguments, so the page renders them
in every locale; the arguments are registry ids or verbatim registry text.

WHAT THIS IS NOT. Not a curriculum anybody has reviewed, not a certification, not a placement. Lessons are
unverified general practice; a course is a reading order. Fail closed: a missing field stops the build by name.
"""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'courses.json'
BUILT = '2026-10-12'
SCHEMA = 'tc-courses/1'


class CourseError(Exception):
    pass


def need(cond, msg):
    if not cond:
        raise CourseError('courses: ' + msg)


def req(d, k, ctx):
    if not isinstance(d, dict) or k not in d:
        raise CourseError(f'courses: {ctx}: missing {k!r}')
    return d[k]


SOURCES = ['lessons/registry/lessons.json', 'pack/registry/halls.json', 'unions/registry/districts.json',
           'unions/registry/campuses.json', 'sims/registry/sims.json', 'stations/registry/stations.json',
           'tools/registry/toolcribs.json', 'surfaces/registry/finishes.json', 'agents/registry/advisors.json',
           'agents/registry/crews.json', 'schools/registry/schools.json', 'web/interiors.py']


def load(p):
    return json.loads((ROOT / p).read_text(encoding='utf-8'))


LES = load('lessons/registry/lessons.json')
HALLS = req(load('pack/registry/halls.json'), 'halls', 'pack/registry/halls.json')
DISTRICTS = req(load('unions/registry/districts.json'), 'districts', 'unions/registry/districts.json')
CAMPUSES = req(load('unions/registry/campuses.json'), 'campuses', 'unions/registry/campuses.json')
SIMS = load('sims/registry/sims.json')
STATIONS = load('stations/registry/stations.json')
CRIBS = load('tools/registry/toolcribs.json')
FIN = load('surfaces/registry/finishes.json')
ADV = req(load('agents/registry/advisors.json'), 'advisors', 'agents/registry/advisors.json')
ADV_BIND = req(load('agents/registry/advisors.json'), 'bindings', 'agents/registry/advisors.json')
CREWS = req(load('agents/registry/crews.json'), 'crews', 'agents/registry/crews.json')
SCHOOLS = load('schools/registry/schools.json')

sys.path.insert(0, str(ROOT / 'web'))
from interiors import ROOMS as INTERIOR_ROOMS  # noqa: E402  the room a strand stands in, and its door label

ROOM_LABEL = {s: label for s, label, _w, _h, _p in INTERIOR_ROOMS}
ROOM_PURPOSE = {s: p for s, _l, _w, _h, p in INTERIOR_ROOMS}
STRANDS = [s for s, *_ in INTERIOR_ROOMS]
need(len(STRANDS) == 11, 'web/interiors.py is expected to lay out 11 rooms, one per strand')
OFF_ROOM = req(LES, 'off_room_places', 'lessons.json')

LESSONS = req(LES, 'lessons', 'lessons.json')
LORDER = list(LESSONS)
LADDER = req(LES, 'ladder', 'lessons.json')
DEPTH = req(LADDER, 'depth', 'lessons.json#ladder')
PREQ = req(LADDER, 'prerequisites', 'lessons.json#ladder')
REASONS = req(LADDER, 'reasons', 'lessons.json#ladder')
HALL_BY = {h['slug']: h for h in HALLS}
HALL_DISTRICT = {}
for dk, d in DISTRICTS.items():
    for slug in req(d, 'halls', f'districts.{dk}'):
        need(slug not in HALL_DISTRICT, f'{slug} is in two districts')
        HALL_DISTRICT[slug] = dk
HALL_CAMPUS = {}
for ck, c in CAMPUSES.items():
    for slug in req(c, 'halls', f'campuses.{ck}'):
        HALL_CAMPUS[slug] = ck
STATION_BY = {s['station_id']: s for s in req(STATIONS, 'stations', 'stations.json')}
SIM = req(SIMS, 'sims', 'sims.json')
SIM_BIND = req(SIMS, 'hall_bindings', 'sims.json')
CRIB_BIND = req(CRIBS, 'hall_bindings', 'toolcribs.json')
FIN_HALLS = req(FIN, 'halls', 'finishes.json')
TIERS = ['fundamentals', 'applied', 'mastery']   # the skill graph's tier ladder (pack/registry/skills.json)
TIER_RANK = {t: i for i, t in enumerate(TIERS)}
SKILL_TIERS = sorted({s['tier'] for s in load('pack/registry/skills.json')['skills']}, key=lambda t: TIER_RANK[t])
need(SKILL_TIERS == TIERS, f'the skill graph tiers are {SKILL_TIERS}, not {TIERS}')

for lid, L in LESSONS.items():
    for k in ('hall', 'hall_name', 'campus', 'strand', 'tier', 'room_label', 'title', 'why', 'limits', 'steps', 'records',
              'stages', 'rooms_walked', 'placard_steps_in', 'authoring'):
        req(L, k, f'lessons.{lid}')
    need(L['tier'] in TIER_RANK, f'lessons.{lid}: tier {L["tier"]} is not on the ladder')
    need(lid in DEPTH and lid in PREQ, f'lessons.{lid}: not on the ladder')
    need(L['hall_name'] == req(HALL_BY, L['hall'], f'lessons.{lid}')['name'], f'lessons.{lid}: hall name drifted from the roster')


def lesson_key(lid):
    return (DEPTH[lid], LORDER.index(lid))


def cond_line(c):
    """The door placard, in exactly the form web/build_3d.py's condLine() prints it (re-checked by courses/test.mjs
    against the page source): lux, ACH, dB, temperature band, PPE."""
    for k in ('lux', 'ach', 'noise_db', 'temp_c', 'ppe'):
        req(c, k, 'condition record')
    return (f'{c["lux"]} lx · {c["ach"]} ACH · {c["noise_db"]} dB · '
            f'{c["temp_c"][0]}–{c["temp_c"][1]} °C · PPE: ' + (', '.join(c['ppe']) if c['ppe'] else '—'))


def cond_of(hall, strand, ctx):
    return req(req(req(FIN_HALLS, hall, ctx), 'conditions', ctx), strand, ctx)


# --------------------------------------------------------------- K-12 bands ---
# DERIVED. Each band admits a lesson by the tier ceiling schools/ gives it and by the step kinds its offer allows.
# `rests_on` is the phrase of the band's own offer the rule reads; if schools/ rewords an offer, the build stops.
BAND_RULES = {
    'K-5': {'rests_on': 'no machine seats and no station quizzes', 'max_tier': 'fundamentals',
            'kinds': ['walk', 'placard', 'advisor'],
            'why': 'awareness only: a K-5 lesson is one walked through rooms, read at the door and asked of an advisor - '
                   'no seat, no walkaround of a seat, no crew, no station, no crib check'},
    '6-8': {'rests_on': 'home modules at fundamentals tier plus class station work', 'max_tier': 'fundamentals',
            'kinds': ['walk', 'placard', 'advisor', 'station', 'crib'],
            'why': 'fundamentals tier and class-stage steps only: no simulator floor time is offered to this band'},
    '9-10': {'rests_on': 'simulator floor time', 'max_tier': 'applied',
             'kinds': ['walk', 'placard', 'advisor', 'station', 'crib', 'walkaround', 'sim', 'crew'],
             'why': 'up to applied tier, class and floor steps'},
    '11-12': {'rests_on': 'mastery-tier modules', 'max_tier': 'mastery',
              'kinds': ['walk', 'placard', 'advisor', 'station', 'crib', 'walkaround', 'sim', 'crew'],
              'why': 'every tier, class and floor steps'},
}
BANDS = req(SCHOOLS, 'bands', 'schools.json')
need([b['band'] for b in BANDS] == list(BAND_RULES), f'schools bands are {[b["band"] for b in BANDS]}, the band rule knows {list(BAND_RULES)}')
STEP_KINDS = list(req(LES, 'step_kinds', 'lessons.json'))
for b in BANDS:
    r = BAND_RULES[b['band']]
    need(r['rests_on'] in req(b, 'offer', f'bands.{b["band"]}'), f'band {b["band"]}: its offer no longer says "{r["rests_on"]}"')
    need(set(r['kinds']) <= set(STEP_KINDS), f'band {b["band"]}: unknown step kind')
    if b['tier'] is not None:
        need(b['tier'] == r['max_tier'], f'band {b["band"]}: schools gives tier {b["tier"]}, the rule {r["max_tier"]}')


def bands_of(L):
    kinds = {s['kind'] for s in L['steps']}
    return [b['band'] for b in BANDS if TIER_RANK[L['tier']] <= TIER_RANK[BAND_RULES[b['band']]['max_tier']]
            and kinds <= set(BAND_RULES[b['band']]['kinds'])]


# --------------------------------------------------------------- the outline ---
def outline_row(lid):
    L = LESSONS[lid]
    kinds = [s['kind'] for s in L['steps']]
    return {'lesson': lid, 'title': L['title'], 'hall': L['hall'], 'hall_name': L['hall_name'], 'strand': L['strand'],
            'room_label': L['room_label'], 'tier': L['tier'], 'campus': L['campus'], 'depth': DEPTH[lid],
            'steps': len(L['steps']), 'kinds': kinds, 'records': L['records'], 'authoring': L['authoring'],
            'bands': bands_of(L)}


def seat_time(lids, halls):
    seats_in, runs, points, crews = [], 0, 0, 0
    for lid in lids:
        for s in LESSONS[lid]['steps']:
            if s['kind'] in ('sim', 'walkaround'):
                need(s['sim'] in SIM, f'{lid} step {s["n"]}: seat {s["sim"]} is not in sims/')
                if s['sim'] not in seats_in:
                    seats_in.append(s['sim'])
                runs += s['kind'] == 'sim'
                points += s['kind'] == 'walkaround'
            if s['kind'] == 'crew':
                crews += 1
    bound = []
    for h in halls:
        for b in (SIM_BIND[h] if h in SIM_BIND else []):   # a hall absent from hall_bindings has no seat: that is the record
            need(b['sim'] in SIM, f'sims.hall_bindings.{h}: unknown seat {b["sim"]}')
            if b['sim'] not in bound:
                bound.append(b['sim'])
    for s in SIM.values():
        for r in s['rubric']:
            if r['axis'] == 'time':
                need(r['pass'] == 'informational', 'a seat now declares a timed pass - the course rule gives no minutes and must be revisited')
    return {'seats_bound': bound, 'seats_in_lessons': seats_in, 'seat_names': {k: SIM[k]['name'] for k in bound + seats_in},
            'sim_runs': runs, 'walkaround_points': points,
            'crew_asks': crews, 'minutes': None,
            'minutes_why': 'sims/ declares no duration for any scenario; the seat clock is an informational rubric axis, so a course gives counts and no minutes'}


def course(cid, kind, title_ref, lids, halls):
    lids = sorted(lids, key=lesson_key)
    inside = set(lids)
    pin, pout = [], []
    for lid in lids:
        for p in PREQ[lid]:
            need(p['needs'] in LESSONS and p['because'] in REASONS, f'{lid}: ladder edge to {p["needs"]} does not resolve')
            row = {'lesson': lid, 'needs': p['needs'], 'because': p['because']}
            (pin if p['needs'] in inside else pout).append(row)
    tiers = {t: sum(1 for l in lids if LESSONS[l]['tier'] == t) for t in TIERS}
    bands = {b['band']: [l for l in lids if b['band'] in bands_of(LESSONS[l])] for b in BANDS}
    return {'id': cid, 'kind': kind, **title_ref, 'lessons': lids, 'outline': [outline_row(l) for l in lids],
            'counts': {'lessons': len(lids), 'steps': sum(len(LESSONS[l]['steps']) for l in lids),
                       'recording_steps': sum(1 for l in lids for s in LESSONS[l]['steps'] if s['records']),
                       'halls': len({LESSONS[l]['hall'] for l in lids})},
            'prerequisites_inside': pin, 'prerequisites_outside': pout, 'tiers': tiers,
            'bands': [b for b, v in bands.items() if v], 'band_lessons': bands, 'seat_time': seat_time(lids, halls),
            'campuses': sorted({LESSONS[l]['campus'] for l in lids}),
            'provenance': {'grouping': 'DERIVED', 'order': 'DERIVED', 'names': 'READ', 'lessons': 'AUTHORED'}}


courses = {}
for h in HALLS:
    slug = h['slug']
    lids = [l for l in LORDER if LESSONS[l]['hall'] == slug]
    need(lids, f'hall {slug} has no lesson, so it would have an empty trade course')
    dk = req(HALL_DISTRICT, slug, f'hall {slug} district')
    ck = req(HALL_CAMPUS, slug, f'hall {slug} campus')
    courses['trade.' + slug] = course('trade.' + slug, 'trade', {
        'hall': slug, 'title': h['name'], 'focus': req(h, 'focus', f'halls.{slug}'), 'district': dk,
        'district_name': DISTRICTS[dk]['name'], 'campus': ck, 'campus_name': CAMPUSES[ck]['name']}, lids, [slug])
for st in STRANDS:
    lids = [l for l in LORDER if LESSONS[l]['strand'] == st]
    need(lids, f'strand {st} has no lesson')
    halls = sorted({LESSONS[l]['hall'] for l in lids})
    courses['strand.' + st] = course('strand.' + st, 'strand', {
        'strand': st, 'title': ROOM_LABEL[st], 'focus': ROOM_PURPOSE[st]}, lids, halls)

# every lesson sits in exactly one trade course and exactly one strand course
for lid in LORDER:
    for kind in ('trade', 'strand'):
        n = sum(1 for c in courses.values() if c['kind'] == kind and lid in c['lessons'])
        need(n == 1, f'{lid} is in {n} {kind} courses')

CATALOGUE_DISTRICTS = [{'district': dk, 'name': d['name'], 'tagline': req(d, 'tagline', f'districts.{dk}'),
                        'courses': ['trade.' + s for s in d['halls']]} for dk, d in DISTRICTS.items()]

RULES = {
    'trade_course': 'one per hall of pack/registry/halls.json: the lessons standing in that hall, grouped under the hall\'s district',
    'strand_course': 'one per room of web/interiors.py: every lesson whose strand it is, across halls',
    'order': 'ladder depth (lessons.json#ladder.depth), then the lessons registry order',
    'prerequisites': 'the ladder\'s own edges, split into those inside the course and those pointing at another course; advice about order, never a gate',
    'seat_time': 'counts only - seats bound to the course halls, seat runs, walkaround points and crew asks; no minutes, because no scenario declares a duration',
    'bands': {b: {k: r[k] for k in ('rests_on', 'max_tier', 'kinds', 'why')} for b, r in BAND_RULES.items()},
}
HONESTY = {
    'status': 'AUTHORED and DERIVED: every course is a grouping and an order chosen by the rules printed under `rules`; '
              'every name, title, room label and count is READ from the registry that owns it. Nothing is fetched and no model runs.',
    'content': 'unverified general practice. The lessons a course lists have not been reviewed by a journey-level practitioner, '
               'and grouping them does not change that.',
    'not_certification': 'no course certifies, qualifies or permits anybody to do anything. Finishing every lesson in a course '
                         'leaves a learner with exactly the standing they started with.',
    'not_a_gate': 'prerequisites are the ladder\'s advice about order. Nothing is locked, and the unaided verification gate '
                  'that schools/ declares stays where it is.',
    'bands': 'K-12 bands are DERIVED from the words of each band\'s offer in schools/; they are a reading of that offer, '
             'not a placement by any teacher or district. School districts named elsewhere remain PROPOSED partners.',
    'seat_time': 'no minutes are given: no scenario declares a duration, so a course counts seat runs instead of inventing a time.',
}

counts = {
    'courses': len(courses), 'trade_courses': sum(1 for c in courses.values() if c['kind'] == 'trade'),
    'strand_courses': sum(1 for c in courses.values() if c['kind'] == 'strand'), 'districts': len(DISTRICTS),
    'lessons': len(LESSONS), 'steps': sum(len(L['steps']) for L in LESSONS.values()),
    'halls': len(HALLS), 'strands': len(STRANDS), 'tiers': len(TIERS),
    'lessons_by_tier': {t: sum(1 for L in LESSONS.values() if L['tier'] == t) for t in TIERS},
    'lessons_by_band': {b['band']: sum(1 for L in LESSONS.values() if b['band'] in bands_of(L)) for b in BANDS},
    'courses_with_seats': sum(1 for c in courses.values() if c['seat_time']['seats_bound'] or c['seat_time']['seats_in_lessons']),
    'prerequisite_edges': sum(len(v) for v in PREQ.values()),
    'cross_course_edges_trade': sum(len(c['prerequisites_outside']) for c in courses.values() if c['kind'] == 'trade'),
}
need(counts['steps'] == LES['counts']['steps'] and counts['lessons'] == LES['counts']['lessons'],
     'the recount of lessons/steps disagrees with lessons.json#counts')

import supplements  # noqa: E402  courses/supplements.py: one supplement per lesson, same fail-closed rules

SUP = supplements.build_all(globals())

stamp = hashlib.sha256((HERE / 'build.py').read_bytes() + (HERE / 'supplements.py').read_bytes()).hexdigest()[:16]
doc = {
    'pack': 'smartcitix-courses', 'schema': SCHEMA, 'built': BUILT, 'source_stamp': stamp,
    'sources': [{'path': p, 'sha256': hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:16]} for p in SOURCES],
    'honesty': HONESTY, 'rules': RULES, 'counts': counts,
    'tiers': TIERS, 'bands': [{'band': b['band'], 'level': b['level'], 'tier': b['tier'], 'offer': b['offer']} for b in BANDS],
    'districts': CATALOGUE_DISTRICTS, 'strands': [{'strand': s, 'room_label': ROOM_LABEL[s], 'purpose': ROOM_PURPOSE[s]} for s in STRANDS],
    'courses': courses,
    'supplements': SUP['supplements'], 'supplement_rules': SUP['rules'], 'supplement_counts': SUP['counts'],
}
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
print(f"courses: {counts['courses']} courses ({counts['trade_courses']} trade in {counts['districts']} districts, "
      f"{counts['strand_courses']} strand) over {counts['lessons']} lessons / {counts['steps']} steps; "
      f"{SUP['counts']['supplements']} supplements, {SUP['counts']['questions']} self-check questions, "
      f"{SUP['counts']['glossary_terms']} glossary terms, {SUP['counts']['placard_quotes']} placard quotes (stamp {stamp})")
