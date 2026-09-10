#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the schools pack builder.

The gamified FLIPPED-CLASSROOM model: how the Academy's existing machinery
(module pack, stations, simulators, assessment gates) becomes a school
program — learners explore at home, build and practice in class, and the
teacher circulates instead of lecturing. Every stage of the model names the
subsystem that already implements it, and schools/test.mjs proves those
references against the packs that own them, so the program cannot drift
from what the Academy actually ships.

DISTRICTS, honestly: the records below name real public school districts
in the three campus regions. The names are AUTHORED FROM PUBLIC RECORD
(identity only — no address, enrolment figure or policy is recorded), and
every record carries the same status: PROPOSED PARTNER. No district has
reviewed or agreed to this program, no agreement of any kind exists, and
nothing here claims adoption. This mirrors the union taxonomy's honesty
note, and the suite asserts it on every record.

GRADE BANDS: aligned with the Cognition.X band vocabulary (Explorer /
Builder / Practitioner / Lead) so the two platforms' materials can sit in
one classroom. The Academy's own tiers map onto the upper bands; Explorer
(K–5) is deliberately awareness-only — maps and walkable campuses, no
machine seats.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

PACK_VERSION = "3.2.0"
BUILT = "2026-09-10"

MODEL = {
    'name': 'gamified flipped classroom',
    'loop': 'explore at home, build and practice in class, verify unaided; '
            'the teacher circulates instead of lecturing',
    'stages': [
        {'stage': 'home', 'title': 'Explore at home',
         'what': 'the lesson positions of the module pack, sequenced by the '
                 'skill graph with the ZPD difficulty dial, in any of the '
                 'eight shipped languages',
         'implemented_by': 'pack/ (modules, skill graph) + i18n/',
         'gamified': 'module layers and pipeline states are the map the '
                     'learner explores; progress is visible per hall'},
        {'stage': 'class', 'title': 'Build in class',
         'what': 'station bench work - checklists, doctrine lines and '
                 'machine-gradable quizzes at the hall stations, with the '
                 'teacher moving bench to bench',
         'implemented_by': 'stations/ (25 recovered yard stations)',
         'gamified': 'station beacons in the 3D hall; completion marks '
                     'accumulate on the hall roster'},
        {'stage': 'floor', 'title': 'Practice on the floor',
         'what': 'simulator seat time with the regional scenario of the '
                 'campus - live dash, synthesized sound, deterministic '
                 'rubric; results and best times persist device-locally',
         'implemented_by': 'sims/ (3 simulators, regional scenarios)',
         'gamified': 'pass/retry chips, best-time records, cockpit views'},
        {'stage': 'gate', 'title': 'Verify unaided',
         'what': 'assessment gates certify only unaided work; no home '
                 'exploration, class bench or simulator hour substitutes '
                 'for the unaided verification run',
         'implemented_by': 'the assessment-gate protocol (ACP-04) and the '
                           'sims registry honesty note',
         'gamified': 'nothing - the gate is deliberately ungamified, and '
                     'the model says so'},
    ],
}

# Grade-band alignment, in the Cognition.X band vocabulary.
BANDS = [
    {'band': 'K-5', 'level': 'Explorer', 'tier': None,
     'offer': 'awareness only: the campus maps, the walkable halls and the '
              'city layers; no machine seats and no station quizzes'},
    {'band': '6-8', 'level': 'Builder', 'tier': 'fundamentals',
     'offer': 'home modules at fundamentals tier plus class station work'},
    {'band': '9-10', 'level': 'Practitioner', 'tier': 'applied',
     'offer': 'applied-tier modules, stations, and simulator floor time '
              'with the regional scenario'},
    {'band': '11-12', 'level': 'Lead', 'tier': 'mastery',
     'offer': 'mastery-tier modules, full flipped loop, and the unaided '
              'verification gate'},
]

DISTRICT_STATUS = ('proposed partner - no district has reviewed or agreed '
                   'to this program, and no agreement exists')

DISTRICTS = [
    {'district': 'San Francisco Unified School District',
     'campus': 'treasure-island', 'city': 'San Francisco'},
    {'district': 'Oakland Unified School District',
     'campus': 'oakland', 'city': 'Oakland'},
    {'district': 'NOLA Public Schools',
     'campus': 'new-orleans', 'city': 'New Orleans'},
    {'district': 'Jefferson Parish Schools',
     'campus': 'new-orleans', 'city': 'Jefferson Parish'},
]

# ---------------------------------------------------------------- inputs ---
campuses = json.load(open(ROOT / 'unions/registry/campuses.json'))['campuses']
sims_reg = json.load(open(ROOT / 'sims/registry/sims.json'))
stations_reg = json.load(open(ROOT / 'stations/registry/stations.json'))
unions = json.load(open(ROOT / 'unions/registry/unions.json'))['unions']

slugs = {u['slug'] for u in unions}
stations_by_hall = {}
for s in stations_reg['stations']:
    stations_by_hall.setdefault(s['hall'], []).append(s['station_id'])

for d in DISTRICTS:
    assert d['campus'] in campuses, f"unknown campus {d['campus']}"
    d['provenance'] = 'authored from public record (name only)'
    d['status'] = DISTRICT_STATUS

# Flipped units: one per simulator-bound hall — the halls where the full
# loop (home modules -> class stations if any -> floor seat -> gate) can
# run today. Every reference is proven downstream.
units = []
for hall, bindings in sorted(sims_reg['hall_bindings'].items()):
    assert hall in slugs, f'unit references unknown hall {hall}'
    units.append({
        'hall': hall,
        'home': 'module pack lesson positions, machines strand',
        'class_stations': stations_by_hall.get(hall, []),
        'floor_sims': sorted({b['sim'] for b in bindings}),
        'gate': 'unaided verification run (ACP-04); no sim hour counts',
    })

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

doc = {
    'pack': 'smartcitix-trade-craft-academy-schools',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'honesty': {
        'districts': 'district names are public-record identities only; '
                     'every record is a PROPOSED partner - no district has '
                     'reviewed or agreed, and no agreement exists',
        'certification': 'nothing in the school program certifies '
                         'equipment operation; the assessment gates demand '
                         'unaided verification and simulator hours never '
                         'count toward certification',
    },
    'model': MODEL,
    'bands': BANDS,
    'districts': DISTRICTS,
    'units': units,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'schools.json').write_text(json.dumps(doc, indent=1) + '\n')
print(f"schools pack: {len(MODEL['stages'])}-stage flipped model, "
      f"{len(BANDS)} grade bands, {len(DISTRICTS)} proposed districts, "
      f"{len(units)} flipped units (source stamp {stamp})")
