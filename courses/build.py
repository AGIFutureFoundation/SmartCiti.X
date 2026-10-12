#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the courses pack builder.

Maps the 2026 Q4 curriculum draft (courses/draft/curriculum_2026q4.json:
twelve PLANNED courses, each module authored as a four-phase flipped loop)
onto machinery the repository already ships:

  * the four authored phases land on the schools model's four stages -
    prepare->home, analyze->class, practice->floor, verify->gate - with the
    authored text kept verbatim;
  * every course names the real halls (unions/registry/unions.json) it is
    taught through, the simulators bound to those halls
    (sims/registry/sims.json hall_bindings) and the recovered yard stations
    that sit in them (stations/registry/stations.json);
  * the S1 slice - TCA-140 Welding modules 1-2 - is marked `wired` and names
    the exact sites it runs on; every other module is `wired: false`.

HONESTY: every course is a PLANNED DRAFT. Nothing is shipped, accredited or
endorsed; no licensing body has accepted any hour of it. The mapping only
binds draft text to existing sites - it does not make the draft true.
courses/test.mjs proves every reference and re-runs this builder to prove
the registry is byte-identical to a fresh build.

  python3 courses/build.py           writes courses/registry/courses.json
  python3 courses/build.py --stdout  prints the same bytes, writes nothing
  python3 courses/build.py --scan-fixtures
                                     prints the honesty verdict for every case
                                     in loop/registry/honesty_fixtures.json
"""
import datetime
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

PACK_VERSION = json.load(open(ROOT / 'pack/manifest.json'))['pack_version']
BUILT = '2026-10-12'
DRAFT_PATH = HERE / 'draft/curriculum_2026q4.json'

draft = json.load(open(DRAFT_PATH))
slugs = {u['slug'] for u in json.load(open(ROOT / 'unions/registry/unions.json'))['unions']}
sims_reg = json.load(open(ROOT / 'sims/registry/sims.json'))
stations_reg = json.load(open(ROOT / 'stations/registry/stations.json'))
lessons_reg = json.load(open(ROOT / 'lessons/registry/lessons.json'))

PHASE_TO_STAGE = [('prepare', 'home'), ('analyze', 'class'),
                  ('practice', 'floor'), ('verify', 'gate')]
MENTORS = ['Chris', 'Joyce', 'Tessa', 'Gemma', 'Iris', 'Dana', 'Sam']

ROSTER_NOTE = ('outside the 111-hall roster: cosmetology, nail and esthetics '
               'courses have no trade hall and are delivered through the '
               'separate Beauty School simulator, not through any hall, '
               'station or yard simulator of this pack; Beauty School is a '
               'separately published simulator and is not part of this repository')

# What a learner can actually run in THIS bundle, stated on every course so an
# empty floor stage is never silent (product review on PR #107).
DELIVERY_FULL = 'all four stages can run in this bundle'
DELIVERY_NO_FLOOR = ('home, class and gate can run in this bundle; no floor simulator '
                     'or class station is bound yet, so practice runs as a paper or demo '
                     'exercise and is recorded as such')
DELIVERY_STATION_ONLY = ('home, class and gate can run in this bundle; class stations are '
                         'bound but no floor simulator is, so practice runs at the bound '
                         'class station(s) or as a paper or demo exercise and is recorded as such')
DELIVERY_BEAUTY = ('home and class only in this bundle: the floor and gate stages need '
                   'the separate Beauty School simulator, which is not part of this repository')

# Authored curation: which real halls teach each course. Every slug is
# asserted against unions.json below; nothing here may name a hall the
# roster does not hold.
HALLS = {
    'TCA-110': {'halls': ['electricians']},
    'TCA-120': {'halls': ['pipefitters'],
                'mapping_note': 'the 111-hall roster has no plumbers hall; '
                                'plumbing is mapped to the nearest piping '
                                'trade, pipefitters, until a plumbing hall '
                                'exists - pipefitting is not plumbing and '
                                'this mapping says so',
                'mapping_review': '2026-10-12',
                'mapping_review_note': 'the plumbing-to-pipefitters mapping was '
                                       'last reviewed on 2026-10-12 and is '
                                       're-reviewed whenever the hall roster '
                                       '(unions/registry/unions.json) changes'},
    'TCA-130': {'halls': ['hvacr']},
    'TCA-140': {'halls': ['welders', 'fabricators']},
    'TCA-150': {'halls': ['carpenters']},
    'TCA-160': {'halls': ['heavy-equip', 'operating-eng', 'survey-drone']},
    'TCA-210': {'halls': [], 'roster_note': ROSTER_NOTE},
    'TCA-220': {'halls': [], 'roster_note': ROSTER_NOTE},
    'TCA-230': {'halls': [], 'roster_note': ROSTER_NOTE},
    'TCA-310': {'halls': ['robotics', 'automation-int']},
    'TCA-320': {'halls': ['robotics', 'automation-int', 'plc-techs']},
    'TCA-410': {'halls': ['site-safety'], 'cross_hall': True,
                'cross_hall_reason': 'crew leadership and emotional '
                                     'intelligence apply on every crew in '
                                     'every hall; the course is anchored at '
                                     'site-safety, where a crew lead owns '
                                     'the culture of the job site'},
}

# The S1 slice: TCA-140 modules 1-2 (1-based) and the sites they run on.
# kind names the registry that owns the id: sim -> sims.json,
# station -> stations.json, lesson -> lessons.json.
WIRED = {
    ('TCA-140', 1): [
        {'kind': 'sim', 'id': 'weld-bead',
         'use': 'practice: set-up and first arc on the Weld Bead Run seat'},
        {'kind': 'lesson', 'id': 'welders-the-watch',
         'use': 'prepare/verify: fire watch and hot-work walk in the '
                'welders Induction & PPE room'},
    ],
    ('TCA-140', 2): [
        {'kind': 'sim', 'id': 'weld-bead',
         'use': 'practice: bead runs graded on fusion and gap band'},
    ],
    # S3: TCA-110 and TCA-130 read against every registry that binds the
    # electricians and hvacr halls. A crib site names the district crib
    # (tools/registry/toolcribs.json) and the one tool its drill asks for.
    ('TCA-110', 1): [
        {'kind': 'crib', 'id': 'systems', 'tool': 'multimeter',
         'use': 'prepare: name the multimeter in the Building-systems crib '
                'check before the meter-use practice'},
    ],
    ('TCA-130', 1): [
        {'kind': 'crib', 'id': 'systems', 'tool': 'manifold-gauge',
         'use': 'prepare: name the manifold gauge set in the Building-systems '
                'crib check before connecting gauges'},
        {'kind': 'lesson', 'id': 'hvacr-prove-the-sequence',
         'use': 'class: the hvacr Inspection Bench lesson that walks to that '
                'crib check and asks the Inspector whether talk can stand in '
                'for a measurement'},
    ],
    # S4: TCA-120, TCA-150 and TCA-220 read against the same registries; only
    # genuine content matches are wired.
    ('TCA-120', 4): [
        {'kind': 'crib', 'id': 'systems', 'tool': 'pipe-wrench',
         'use': 'prepare: name the pipe wrench in the Building-systems crib '
                'check before assembling the threaded sediment trap'},
    ],
    ('TCA-150', 1): [
        {'kind': 'crib', 'id': 'envelope', 'tool': 'chalk-line',
         'use': 'prepare: name the chalk line in the Envelope & finish crib '
                'check before snapping wall lines'},
        {'kind': 'lesson', 'id': 'carpenters-return-it-the-same',
         'use': 'class: the carpenters Tool Crib lesson (issue, calibration '
                'and return) that ends at that crib check'},
    ],
}

# Why each wired module's sites match its content - stated, not implied.
WIRING_NOTES = {
    ('TCA-110', 1): 'the module practises measuring voltage, continuity and '
                    'resistance; the systems crib drill (bound to the '
                    'electricians hall) asks for the tool that reads voltage, '
                    'current and resistance in one instrument - the multimeter. '
                    'It covers tool identification only; no simulator runs the '
                    'live-dead-live sequence itself',
    ('TCA-130', 1): 'the module practises connecting manifold gauges and reading '
                    'suction and liquid pressures; the systems crib drill (bound '
                    'to the hvacr hall) asks for the tool that reads both sides '
                    'of a refrigeration circuit at once, and the hvacr lesson '
                    'hvacr-prove-the-sequence runs that crib check. It covers '
                    'tool identification and a measurement-first inspection '
                    'habit only; no simulator runs a refrigeration circuit',
    ('TCA-120', 4): 'the module practises replacing a gas water heater, '
                    'including its sediment trap, which is assembled from '
                    'threaded pipe and fittings; the systems crib drill (bound '
                    'to the pipefitters hall) asks for the tool that grips and '
                    'turns threaded pipe - the pipe wrench. It covers tool '
                    'identification only; no simulator runs the water-heater '
                    'swap, the venting check or the gas leak test, and the '
                    'pipefitters hall stands in for a plumbing hall',
    ('TCA-150', 1): 'the module practises layout and has the learner snap '
                    'wall lines with a chalk line; the envelope crib drill '
                    '(bound to the carpenters hall) asks for the tool that '
                    'snaps a straight layout line, and the carpenters lesson '
                    'carpenters-return-it-the-same runs that crib check. It '
                    'covers tool identification and crib discipline only; no '
                    'simulator runs wall-plate layout or squaring',
}

# What is missing for the modules left unwired, per course (S3 courses lane).
WIRING_GAPS = {
    'TCA-110': 'modules 2-5 are unwired: no simulator, class station or lesson '
               'in this bundle practises grounding and bonding, conductor '
               'sizing, device wiring or lockout/tagout; the only electricians '
               'sim (boom-lift) and lesson (electricians-clip-in-first) teach '
               'aerial-lift basket work, which no module of this course covers, '
               'and the bas-controls, fire-alarm and instrumentation halls bind '
               'only the same systems crib',
    'TCA-130': 'modules 2-5 are unwired: no hvacr simulator or class station '
               'exists in this bundle (sims.json has no hvacr hall binding and '
               'stations.json has no hvacr station), so charging, refrigerant '
               'recovery, airflow and controls practice have no site; the one '
               'hvacr lesson covers commissioning inspection, not these tasks',
    'TCA-120': 'modules 1-3 are unwired: no simulator, class station or '
               'lesson in this bundle practises DWV layout, sweating copper or '
               'crimping PEX, or setting fixtures; pipefitters has no simulator '
               'binding, no class station and no lesson, and the systems crib '
               'drill asks for no plumbing tool beyond the pipe wrench (its '
               'crimper closes electrical connectors, not PEX rings)',
    'TCA-150': 'modules 2-5 are unwired: no simulator, class station or lesson '
               'in this bundle practises wall framing, stair layout, rafter '
               'cutting or door hanging; the carpenters sim scaffold-bay '
               'erects a scaffold bay, which no module of this course '
               'practises, and the envelope crib drill asks for no framing '
               'or trim tool beyond the chalk line',
    'TCA-220': 'no module is wired: nail technology has no hall in the '
               '111-hall roster, so no simulator, class station, lesson or '
               'tool crib in this bundle binds it; its floor and gate stages '
               'need the separate Beauty School simulator, which is not part '
               'of this repository',
}

CATALOG_HOLD = ('coming soon: held out of the main catalog until a sprint '
                'commits to Beauty School; the course stays in this registry '
                'and nothing is deleted')

# The honesty scanner. The vocabulary is loop/honesty.json, shared with
# loop/honesty.mjs (EV-05 and courses/test.mjs); the rules below mirror that
# module line for line, and courses/test.mjs runs both over
# loop/registry/honesty_fixtures.json and requires identical verdicts.
HONESTY_VOCAB = json.load(open(ROOT / 'loop/honesty.json'))
HONESTY_FIXTURES = ROOT / 'loop/registry/honesty_fixtures.json'
_CLAIM = re.compile('|'.join(HONESTY_VOCAB['claims']), re.I | re.A)
_NEG = re.compile('|'.join(HONESTY_VOCAB['negations']), re.I | re.A)
_ABBR = re.compile('|'.join(HONESTY_VOCAB['abbreviations']), re.A)
_PLACEHOLDER = '\u00a7\u00a7'
_BREAK = re.compile(r'[.!?;](?=\s|\Z)|,\s+(?=(?:but|not)\b)|\n', re.I | re.A)


def _prepare(text):
    """Blank fences (keeping newlines) and code spans; replace abbreviations."""
    text = re.sub(r'```[\s\S]*?```', lambda m: re.sub(r'[^\n]', '', m.group(0)), text)
    text = re.sub(r'`[^`\n]*`', ' ', text)
    return _ABBR.sub(_PLACEHOLDER, text)


def _soft_wrap(t, i):
    prev = t[t.rfind('\n', 0, i) + 1:i].rstrip()
    j = t.find('\n', i + 1)
    nxt = t[i + 1:(j if j >= 0 else len(t))].lstrip()
    return bool(re.search(r'[\w,):]$', prev, re.A)) and bool(re.match(r'[A-Za-z(`]', nxt))


def _clauses(t):
    out, start = [], 0
    for m in _BREAK.finditer(t):
        if m.group(0) == '\n' and _soft_wrap(t, m.start()):
            continue
        out.append((start, t[start:m.end()]))
        start = m.end()
    out.append((start, t[start:]))
    return [c for c in out if c[1].strip()]


def _tight(c, i):
    def solid(k):
        return 0 <= k < len(c) and not c[k].isspace() and c[k] != '|'
    return 0 <= i < len(c) and c[i] == '|' and solid(i - 1) and solid(i + 1)


def _clause_claim(c):
    negs = [m.start() for m in _NEG.finditer(c)]
    for m in _CLAIM.finditer(c):
        if any(i < m.start() for i in negs):
            continue
        if _tight(c, m.start() - 1) or _tight(c, m.end()):
            continue
        return m.start()
    return -1


def claim_hits(text):
    """Overclaiming clauses in a text: [(line, clause)]."""
    t = _prepare(text)
    hits = []
    for start, c in _clauses(t):
        k = _clause_claim(c)
        if k >= 0:
            hits.append((t[:start + k].count('\n') + 1, ' '.join(c.split())[:120]))
    return hits


def unnegated_claims(text):
    """Clauses that use a forbidden claim word without an earlier negation."""
    return [c for _, c in claim_hits(text)]


if '--scan-fixtures' in sys.argv:
    cases = json.load(open(HONESTY_FIXTURES))['cases']
    json.dump([('flag' if claim_hits(x['text']) else 'clean') for x in cases], sys.stdout)
    sys.stdout.write('\n')
    sys.exit(0)


def mentor_names(text):
    return [w for w in re.findall(r'\b[A-Z][a-z]+\b', text) if w in MENTORS]


MONTHS = {m: i for i, m in enumerate(
    'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(), 1)}


def parse_window(weeks):
    left, right = [s.strip() for s in weeks.split(' - ')]
    rm, rd, ry = re.match(r'(\w{3}) (\d+), (\d{4})$', right).groups()
    end = datetime.date(int(ry), MONTHS[rm], int(rd))
    m = re.match(r'(\w{3}) (\d+)(?:, (\d{4}))?$', left)
    lm, ld, ly = m.groups()
    start = datetime.date(int(ly) if ly else end.year, MONTHS[lm], int(ld))
    if start > end:
        start = start.replace(year=end.year - 1)
    return start.isoformat(), end.isoformat()


sims_by_hall = {h: sorted({b['sim'] for b in bs})
                for h, bs in sims_reg['hall_bindings'].items()}
stations_by_hall = {}
for s in stations_reg['stations']:
    stations_by_hall.setdefault(s['hall'], []).append(s['station_id'])
sim_ids = set(sims_reg['sims'])
station_ids = {s['station_id'] for s in stations_reg['stations']}
lesson_ids = set(lessons_reg['lessons'])
cribs_reg = json.load(open(ROOT / 'tools/registry/toolcribs.json'))
crib_ids = set(cribs_reg['cribs'])
SITE_OWNERS = {'sim': sim_ids, 'station': station_ids, 'lesson': lesson_ids,
               'crib': crib_ids}

courses = []
for c in draft['courses']:
    code = c['code']
    m = HALLS[code]
    for h in m['halls']:
        assert h in slugs, f'{code}: unknown hall {h}'
    floor = sorted({s for h in m['halls'] for s in sims_by_hall.get(h, [])})
    stations = sorted({s for h in m['halls'] for s in stations_by_hall.get(h, [])})
    names = mentor_names(c['mentor'])
    assert names, f'{code}: no mentor named'
    modules = []
    for i, mod in enumerate(c['modules'], 1):
        f = mod['flipped']
        stages = [{'stage': st, 'phase': ph, 'text': f[ph]}
                  for ph, st in PHASE_TO_STAGE]
        sites = WIRED.get((code, i))
        rec = {'n': i, 'title': mod['title'], 'stages': stages,
               'wired': bool(sites)}
        if sites:
            for s in sites:
                assert s['id'] in SITE_OWNERS[s['kind']], \
                    f"{code} m{i}: unknown {s['kind']} {s['id']}"
                if s['kind'] == 'crib':
                    assert any(cribs_reg['hall_bindings'].get(h, {}).get('district') == s['id']
                               for h in m['halls']), f'{code} m{i}: crib not bound to a course hall'
                    assert s['tool'] in {d['tool'] for d in cribs_reg['drills'][s['id']]}, \
                        f"{code} m{i}: tool {s['tool']} not asked by the {s['id']} drill"
                if s['kind'] == 'lesson':
                    assert lessons_reg['lessons'][s['id']]['hall'] in m['halls'], \
                        f"{code} m{i}: lesson outside the course halls"
            rec['sites'] = sites
            rec['wiring_note'] = WIRING_NOTES.get((code, i), 'the S1 welding slice: '
                                                  'the sites named run this module')
        modules.append(rec)
    rec = {
        'code': code, 'title': c['title'], 'trade': c['trade'],
        'status': 'planned draft',
        'level': c['level'], 'hours_planned': c['hours'],
        'mentor_text': c['mentor'], 'mentors': names,
        'halls': m['halls'],
    }
    for k in ('mapping_note', 'mapping_review', 'mapping_review_note',
              'roster_note', 'cross_hall', 'cross_hall_reason'):
        if k in m:
            rec[k] = m[k]
    # DELIVERY_FULL needs a bound floor simulator; class stations alone
    # (TCA-410) do not run the floor stage (CodeRabbit on PR #107).
    rec['delivery_status'] = (DELIVERY_BEAUTY if 'roster_note' in m
                              else DELIVERY_FULL if floor
                              else DELIVERY_STATION_ONLY if stations else DELIVERY_NO_FLOOR)
    # Catalog section (product review on PR #107): where the course is listed.
    rec['catalog_section'] = ('coming-soon' if 'roster_note' in m
                              else 'available' if floor else 'home-and-class')
    if rec['catalog_section'] == 'coming-soon':
        rec['catalog_note'] = CATALOG_HOLD
    if code in WIRING_GAPS:
        rec['wiring_gap'] = WIRING_GAPS[code]
    rec.update({
        'floor_sims': floor, 'class_stations': stations,
        'robotics_link': c['robotics_link'],
        'licensure_note': c['licensure_note'],
        'modules': modules,
    })
    courses.append(rec)

# A closed status set, so the registry can say what actually happened to a
# sprint instead of reading "planned" forever (product review on PR #107).
SPRINT_STATUSES = ('planned', 'in-progress', 'shipped', 'slipped', 'cancelled')
SPRINT_OUTCOMES = {
    'S1': ('shipped', 'partial: the schema and honesty parts were met; the '
                      '200-session hint-ladder run was not executed'),
    'S2': ('shipped', 'met on the fixture set only: after cycle-3 tuning the guards '
                      'escalate 80 of 80 out-of-scope prompts with 0 of 48 false '
                      'escalations, but a blind held-out batch caught 2 of 12, so '
                      'the regex guards do not generalise to unseen phrasing '
                      '(fabric/test_mentor_scope.mjs)'),
    'S3': ('shipped', 'met on the scripted suite: 981 of 981 bypass attempts blocked '
                      'and 78 of 78 legitimate entries allowed, overrides audited '
                      '(safety_gate/test.mjs); electrical and HVAC wiring partial, '
                      '2 of 10 modules wired, to tool cribs only'),
    'S4': ('shipped', 'partial: the cohort dashboard reconciles 310 figures with an '
                      'independent recomputation at 0.00% error on SYNTHETIC data '
                      '(cohort/test.mjs); its skill map uses an invented '
                      'module-to-strand mapping; the trade-accuracy review by a '
                      'qualified human was not done, no reviewer is engaged'),
}
# A pilot with real learners is an ethical and legal precondition, not a note:
# the sprint record names it and loop/evals.mjs EV-09 enforces it in the ledger.
PRECONDITIONS = {'S8': ['a named partner', 'an IRB approval or consent-plan reference',
                        'EV-09 passing on the cycle that records the pilot']}

sprints = []
for s in draft['rapid_roadmap']:
    start, end = parse_window(s['weeks'])
    status, result = SPRINT_OUTCOMES.get(s['sprint'], ('planned', None))
    rec = {'sprint': s['sprint'], 'start': start, 'end': end,
           'weeks': s['weeks'], 'status': status, 'gate_result': result,
           'ship': s['ship'], 'eval_gate': s['eval_gate']}
    if s['sprint'] in PRECONDITIONS:
        rec['preconditions'] = PRECONDITIONS[s['sprint']]
    sprints.append(rec)

HONESTY = {
    'status': 'every course in this pack is a PLANNED DRAFT: nothing is '
              'shipped or deployed, learning efficacy is unestablished, and '
              'only the modules marked wired are bound to sites that exist',
    'credit': 'no licensing board, jurisdiction or employer has accepted '
              'any hour of these courses; simulator, station and lesson '
              'time never count toward a licence or certification',
    'marks': 'no course is accredited, and no union, standards body or '
             'school is a partner of it; codes and standards are named as '
             'reference topics only',
    'mapping': 'hall, simulator and station bindings are authored curation '
               'read against the registries that own them; a binding means '
               'the site exists, not that the course content was reviewed '
               'by practitioners of that trade',
}

doc = {
    'pack': 'smartcitix-trade-craft-academy-courses',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': None,
    'honesty': HONESTY,
    'source': {'draft': 'courses/draft/curriculum_2026q4.json',
               'draft_status': draft['meta']['status'],
               'pedagogy': draft['meta']['pedagogy']},
    'stage_map': [{'phase': ph, 'stage': st} for ph, st in PHASE_TO_STAGE],
    'mentor_roster': MENTORS,
    'courses': courses,
    'teacher_kit': draft['teacher_kit'],
    'student_kit': draft['student_kit'],
    'agent_assist': draft['agent_assist'],
    'sprints': sprints,
}

# Guard the output, not just the inputs: no unnegated claim may be emitted.
def strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from strings(v)


bad = [s for t in strings(doc) for s in unnegated_claims(t)]
assert not bad, f'unnegated claim(s): {bad}'

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()
                       + DRAFT_PATH.read_bytes()).hexdigest()[:16]
doc['source_stamp'] = stamp
text = json.dumps(doc, indent=1) + '\n'

if '--stdout' in sys.argv:
    sys.stdout.write(text)
else:
    OUT = HERE / 'registry'
    OUT.mkdir(exist_ok=True)
    (OUT / 'courses.json').write_text(text)
    wired = sum(m['wired'] for c in courses for m in c['modules'])
    print(f'courses pack: {len(courses)} planned courses, '
          f'{sum(len(c["modules"]) for c in courses)} modules '
          f'({wired} wired), {len(sprints)} sprints (source stamp {stamp})')
