#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the advisor registry builder.

A hall is a building until somebody in it will answer a question. This pack
declares the ADVISORS: figures who stand in the rooms and on the campus
green, and who answer a short, fixed set of questions about the place they
are standing in.

WHAT AN ADVISOR IS. A scripted guide. No model runs behind one, nothing is
generated at view time, no network is reached, and every line an advisor
can say is either written in this file or READ AT VIEW TIME from another
registry in this bundle. That second kind is the point: an advisor does not
restate a fact, it quotes the one record that already holds it. Ask the
safety steward what to wear and the answer is the hall's own condition
record; ask the crib keeper what is issued and the answer is that district's
own crib. One truth per fact survives the advisor being added.

So a topic is one of two shapes:

  * 'say'   - a sentence written here, about this bundle's own policy, with
              the record it comes from named in `cites`.
  * 'read'  - a BINDING naming the page-data path the answer must be read
              from. The page renders the live record; this registry never
              copies it. The suite checks every binding resolves.

WHAT AN ADVISOR IS NOT. Not an instructor, not a certification, not a code
ruling, and not a stand-in for the qualified person on site. Not a real
worker, steward or union officer: the figures are the Academy's own
schematic avatars wearing the Academy's own crew marks. And not a gate -
talking to one changes no score and unlocks nothing, which the suite
asserts by reading the graders.
"""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

PACK_VERSION = "3.2.0"
BUILT = "2026-09-11"

# ---------------------------------------------------------------- topics ---
# `read` bindings name a path the PAGE resolves against its own data for the
# hall or campus the learner is standing in. The suite proves each one
# resolves; the page test proves the rendered answer is that record's value.
BINDINGS = {
    'conditions.ppe': 'the PPE list on this room\'s condition record',
    'conditions.hazards': 'the hazards this room\'s condition record carries',
    'conditions.env': 'the lux, air changes and noise this room is held to',
    'surface.finish': 'the floor finish this room is given, and why',
    'crib.tools': 'the tools this district\'s crib issues',
    'crib.drill': 'how the crib check is scored',
    'sim.walkaround': 'the pre-shift walkaround points for this hall\'s seat',
    'sim.rubric': 'what the seat at this hall actually measures',
    'hall.rooms': 'the rooms this hall is laid out with',
    'hall.focus': 'what this hall is for',
    'campus.districts': 'the districts this campus holds',
    'campus.network': 'the other campuses and the distance to them',
    'city.anchors': 'the recorded places around this campus',
    'city.walk': 'which recorded places fall inside a ten- and '
                 'fifteen-minute walk of this campus',
}

ADVISORS = {
    'guide': {
        'name': 'Orientation guide',
        'role': 'meets you at the door and says what the place is',
        'stands_in': 'door',           # the hall entrance, not a room
        'glyph': '🧭',
        'crew': {'top': 'polo', 'headwear': 'ball-cap', 'vest': 'hi-vis-2',
                 'extras': 'id-badge'},
        'greeting': 'First time in this hall? Ask me what it is and where to start.',
        'topics': [
            {'id': 'what', 'ask': 'What is this hall?',
             'kind': 'read', 'bind': 'hall.focus'},
            {'id': 'rooms', 'ask': 'What is laid out in here?',
             'kind': 'read', 'bind': 'hall.rooms'},
            {'id': 'start', 'ask': 'Where should I start?',
             'kind': 'say', 'cites': 'agents/build.py',
             'say': 'At the induction room, every time. Find the safety '
                    'steward, get what the room is held to, then walk the '
                    'practice bays. Nothing here is locked, so the order is '
                    'yours - but that is the order a shift starts in.'},
            {'id': 'real', 'ask': 'How much of this is real?',
             'kind': 'say', 'cites': 'geo/registry/campuses_geo.json',
             'say': 'Three words are used on every label and they mean '
                    'exactly what they say. RECORDED is a fact taken from a '
                    'cited source and checked against it. DERIVED is '
                    'computed from a recorded fact. SCHEMATIC is drawn to '
                    'teach and is not a survey of anywhere. The buildings '
                    'you are standing in are SCHEMATIC. The coordinates the '
                    'campus sits on are RECORDED.'},
        ],
    },
    'safety-steward': {
        'name': 'Safety steward',
        'role': 'holds the room to its own condition record',
        'stands_in': 'safety',
        'glyph': '🦺',
        'crew': {'top': 'work-shirt', 'headwear': 'full-brim',
                 'vest': 'hi-vis-3', 'extras': 'safety-glasses'},
        'greeting': 'Before you go past me: ask what this room is held to.',
        'topics': [
            {'id': 'ppe', 'ask': 'What do I need on in here?',
             'kind': 'read', 'bind': 'conditions.ppe'},
            {'id': 'hazard', 'ask': 'What is the hazard here?',
             'kind': 'read', 'bind': 'conditions.hazards'},
            {'id': 'env', 'ask': 'Light, air and noise?',
             'kind': 'read', 'bind': 'conditions.env'},
            {'id': 'refuse', 'ask': 'Can I refuse the work?',
             'kind': 'say', 'cites': 'agents/build.py',
             'say': 'Yes, and the Academy teaches it as a duty rather than '
                    'a right: if the condition in front of you is not the '
                    'condition the work was planned for, you stop and you '
                    'say so. Practising the refusal is the point of the '
                    'induction room. On a real site the law that backs you '
                    'is your jurisdiction\'s, not this bundle\'s.'},
        ],
    },
    'crib-keeper': {
        'name': 'Crib keeper',
        'role': 'issues, calibrates and takes back the tools',
        'stands_in': 'tools',
        'glyph': '🧰',
        'crew': {'top': 'work-shirt', 'headwear': 'ball-cap',
                 'vest': 'tool-vest', 'extras': 'tool-lanyard'},
        'greeting': 'Issue, calibration, return. Ask me what this crib holds.',
        'topics': [
            {'id': 'tools', 'ask': 'What is issued out of this crib?',
             'kind': 'read', 'bind': 'crib.tools'},
            {'id': 'drill', 'ask': 'How is the crib check scored?',
             'kind': 'read', 'bind': 'crib.drill'},
            {'id': 'brand', 'ask': 'Whose tools are these?',
             'kind': 'say', 'cites': 'tools/registry/toolcribs.json',
             'say': 'Nobody\'s. This is a schematic aid for tool '
                    'identification and crib discipline - not an inventory '
                    'of any real toolroom, not tool competency '
                    'certification, and no manufacturer or brand is named '
                    'or drawn anywhere in it.'},
        ],
    },
    'layout-hand': {
        'name': 'Layout hand',
        'role': 'sets out the work and defends the control points',
        'stands_in': 'layout',
        'glyph': '📐',
        'crew': {'top': 'long-sleeve', 'headwear': 'hard-cap',
                 'vest': 'surveyor', 'extras': 'safety-glasses'},
        'greeting': 'Everything downstream is wrong if the line is wrong.',
        'topics': [
            {'id': 'floor', 'ask': 'Why this floor?',
             'kind': 'read', 'bind': 'surface.finish'},
            {'id': 'control', 'ask': 'What is a control point?',
             'kind': 'say', 'cites': 'agents/build.py',
             'say': 'A mark everything else is measured from, put in once '
                    'and protected. Measure from the control point, never '
                    'from the last thing you set - that is how a small '
                    'error becomes a cumulative one, and it is the habit '
                    'this floor exists to build.'},
            {'id': 'check', 'ask': 'How do I know the line is true?',
             'kind': 'say', 'cites': 'agents/build.py',
             'say': 'Close it. Run the measurement back to where it '
                    'started and see whether it lands on the same mark. A '
                    'line you have not closed is a line you are hoping '
                    'about.'},
        ],
    },
    'inspector': {
        'name': 'Inspector',
        'role': 'holds the work to the acceptance criteria',
        'stands_in': 'inspection',
        'glyph': '🔍',
        'crew': {'top': 'polo', 'headwear': 'hard-cap', 'vest': 'hi-vis-2',
                 'extras': 'id-badge'},
        'greeting': 'I sign what meets the criterion. Ask me what it is.',
        'topics': [
            {'id': 'measures', 'ask': 'What does the seat here measure?',
             'kind': 'read', 'bind': 'sim.rubric'},
            {'id': 'score', 'ask': 'Can I talk my way to a pass?',
             'kind': 'say', 'cites': 'sims/registry/sims.json',
             'say': 'No. Every rubric axis is computed from measured state, '
                    'and nothing narrative can change a score. Neither can '
                    'what you are wearing, which ape you picked, or how '
                    'long you spoke to me.'},
            {'id': 'cert', 'ask': 'Does a pass here certify me?',
             'kind': 'say', 'cites': 'sims/registry/sims.json',
             'say': 'It does not. These are schematic physics for '
                    'practising control discipline. No seat time here '
                    'counts toward equipment certification, and the '
                    'assessment gates still demand unaided verification '
                    'runs.'},
        ],
    },
    'foreman': {
        'name': 'Foreman',
        'role': 'runs the shift brief and the hand-offs',
        'stands_in': 'coordination',
        'glyph': '📋',
        'crew': {'top': 'flannel', 'headwear': 'full-brim',
                 'vest': 'hi-vis-3', 'extras': 'radio'},
        'greeting': 'Shift starts here. Ask me what gets walked before it does.',
        'topics': [
            {'id': 'walk', 'ask': 'What gets walked before a start?',
             'kind': 'read', 'bind': 'sim.walkaround'},
            {'id': 'gate', 'ask': 'Is the walkaround a gate?',
             'kind': 'say', 'cites': 'sims/registry/sims.json',
             'say': 'No - it is a habit-builder. No seat is locked behind '
                    'it, completing it changes no score, and it is not an '
                    'equipment inspection record. Do it anyway. The habit '
                    'is the only part of it that travels to a real yard.'},
            {'id': 'handoff', 'ask': 'What makes a hand-off good?',
             'kind': 'say', 'cites': 'agents/build.py',
             'say': 'Say what changed, what is still open, and what you '
                    'would do next if you were staying. Three sentences. '
                    'A hand-off that only says what was finished hands the '
                    'next crew your assumptions as well as your work.'},
        ],
    },
    'records-clerk': {
        'name': 'Records clerk',
        'role': 'keeps the permits, the certificates and the as-builts',
        'stands_in': 'documentation',
        'glyph': '🗂️',
        'crew': {'top': 'henley', 'headwear': 'none', 'vest': 'none',
                 'extras': 'id-badge'},
        'greeting': 'If it is not written down it did not happen. Ask me where it is written.',
        'topics': [
            {'id': 'where', 'ask': 'Where does my progress go?',
             'kind': 'say', 'cites': 'agents/build.py',
             'say': 'Into this browser and nowhere else. Nothing you do '
                    'here is uploaded, and no account exists to upload it '
                    'to. Clear the site data and the record is gone - '
                    'which is the trade-off for it never having left.'},
            {'id': 'cert', 'ask': 'What does the Academy certify?',
             'kind': 'say', 'cites': 'agents/build.py',
             'say': 'Nothing, by itself. It teaches and it records what you '
                    'practised. Certification is issued by the body with '
                    'the standing to issue it, under your jurisdiction - '
                    'and no partnership with any such body is claimed '
                    'anywhere in this bundle.'},
            {'id': 'partners', 'ask': 'Who are the school partners?',
             'kind': 'say', 'cites': 'schools/registry/schools.json',
             'say': 'Proposed ones. Every district named in the schools '
                    'pack is recorded as a proposed partner - no district '
                    'has reviewed or agreed to any of it, and the registry '
                    'says so on every entry rather than in a footnote.'},
        ],
    },
    'dispatcher': {
        'name': 'Dispatcher',
        'role': 'sends you to the right campus and the right hall',
        'stands_in': 'green',          # the campus green, not a hall room
        'glyph': '📡',
        'crew': {'top': 'polo', 'headwear': 'ball-cap-back', 'vest': 'mesh',
                 'extras': 'radio'},
        'greeting': 'Tell me the trade and I will tell you the campus.',
        'topics': [
            {'id': 'here', 'ask': 'What does this campus hold?',
             'kind': 'read', 'bind': 'campus.districts'},
            {'id': 'others', 'ask': 'Where are the other campuses?',
             'kind': 'read', 'bind': 'campus.network'},
            {'id': 'around', 'ask': 'What is around us?',
             'kind': 'read', 'bind': 'city.anchors'},
            {'id': 'walk', 'ask': 'What can I reach on foot?',
             'kind': 'read', 'bind': 'city.walk'},
            {'id': 'sited', 'ask': 'Is the campus really here?',
             'kind': 'say', 'cites': 'geo/registry/campuses_geo.json',
             'say': 'The coordinates are RECORDED and the distances '
                    'between campuses are DERIVED from them by great '
                    'circle. The campus itself is SCHEMATIC: no ground has '
                    'been acquired, no building has been consented, and '
                    'nothing here is a site plan.'},
        ],
    },
}

HONESTY = {
    'status': 'an advisor is a scripted guide, not an instructor and not an '
              'AI: no model runs behind one, nothing is generated at view '
              'time, no network is reached, and every line an advisor can '
              'say is written in this registry or read from another '
              'registry in this bundle.',
    'not_advice': 'nothing an advisor says is a certification, a permit, a '
                  'code ruling or a substitute for the qualified person on '
                  'site; where an advisor states a duty it states it as '
                  'this Academy teaches it, not as any jurisdiction\'s law.',
    'not_scored': 'talking to an advisor changes no score and unlocks '
                  'nothing: no grader reads advisor state, and the suite '
                  'asserts it by reading the graders.',
    'not_a_person': 'an advisor represents no real worker, steward, '
                    'instructor or union officer, and no real union local '
                    'is named: the figures are the Academy\'s own '
                    'schematic avatars wearing the Academy\'s own crew '
                    'marks.',
    'closed_book': 'an advisor cannot be asked an open question because it '
                   'has no way to answer one. The topics below are all of '
                   'them, and the suite counts them.',
}

CONTRACT = (
    'a topic is either a `say` - a sentence written in this registry about '
    'this bundle\'s own policy, with the record it comes from named in '
    '`cites` - or a `read` - a binding naming the page-data path the answer '
    'must be read from at view time. No `read` answer is copied into this '
    'registry, so the record it quotes stays the one truth for that fact.'
)

# ---------------------------------------------------------------- checks ---
rooms = json.load(open(ROOT / 'surfaces/registry/finishes.json'))
strands = set(rooms['base_conditions'])

# an advisor wears the locker's own options, never a bespoke one: the look is
# a choice any learner could also make, and the build fails if it is not
av = json.load(open(ROOT / 'avatars/registry/avatars.json'))
opts = {s['id']: {o['id'] for o in s['options']} for s in av['sections']}
for aid, a in ADVISORS.items():
    for sec, pick in a['crew'].items():
        assert sec in opts, f'{aid}: {sec} is not a locker section'
        assert pick in opts[sec], \
            f'{aid}: {sec}={pick} is not an option in the locker'
for aid, a in ADVISORS.items():
    where = a['stands_in']
    assert where in strands or where in ('door', 'green'), \
        f'{aid}: stands in {where}, which is not a room strand'
    assert a['topics'], f'{aid}: an advisor with nothing to say'
    seen = set()
    for t in a['topics']:
        assert t['id'] not in seen, f'{aid}: duplicate topic {t["id"]}'
        seen.add(t['id'])
        assert t['ask'].endswith('?'), f'{aid}/{t["id"]}: a topic is a question'
        if t['kind'] == 'read':
            assert t['bind'] in BINDINGS, \
                f'{aid}/{t["id"]}: {t["bind"]} is not a declared binding'
        else:
            assert t['kind'] == 'say' and t['say'] and t['cites'], \
                f'{aid}/{t["id"]}: a say needs words and a citation'
            cited = ROOT / t['cites']
            assert cited.exists(), f'{aid}/{t["id"]}: cites {t["cites"]}, missing'

# every declared binding is used, or it is dead weight pretending to be a contract
used = {t['bind'] for a in ADVISORS.values() for t in a['topics']
        if t['kind'] == 'read'}
assert used == set(BINDINGS), \
    f'declared bindings never used: {sorted(set(BINDINGS) - used)}'

# no advisor stands in the same room as another: one voice per room
places = [a['stands_in'] for a in ADVISORS.values()]
assert len(places) == len(set(places)), 'two advisors in one room'

# The page must actually build them. This is a two-way check - the page
# reads this registry and this registry reads the page - so a first build,
# before the page has ever seen an advisor, has nowhere to start. `--bootstrap`
# is that one-shot start and says so out loud; it is never used by verify_all.
BOOTSTRAP = '--bootstrap' in sys.argv
if not BOOTSTRAP:
    page_src = (ROOT / 'web/trade_craft_3d.html').read_text()
    for aid in ADVISORS:
        assert f'"{aid}"' in page_src, \
            f'advisor {aid} is declared but never reaches the page'
    for fn in ('ADVISOR_TABLE', 'function placeAdvisor(',
               'function spawnHallAdvisors(', 'function spawnCampusAdvisors(',
               'function advRead(', 'function openAdvisor('):
        assert fn in page_src, f'the page does not build advisors: {fn} missing'
    # every binding this registry declares must have a branch that resolves it
    for b in BINDINGS:
        assert f"case '{b}'" in page_src, \
            f'binding {b} is declared but the page cannot resolve it'
    # and no grader may read any of it
    for grader in ('function score', 'function grade'):
        for chunk in page_src.split(grader)[1:]:
            body = chunk[:2500]
            assert 'advisor' not in body.lower(), \
                'a grader reads advisor state; advisors must never be scored'

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
topics = sum(len(a['topics']) for a in ADVISORS.values())
reads = len(used)

doc = {
    'pack': 'smartcitix-trade-craft-academy-advisors',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'contract': CONTRACT,
    'honesty': HONESTY,
    'counts': {'advisors': len(ADVISORS), 'topics': topics,
               'read_bindings': reads,
               'say_topics': topics - sum(
                   1 for a in ADVISORS.values() for t in a['topics']
                   if t['kind'] == 'read')},
    'bindings': BINDINGS,
    'advisors': ADVISORS,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'advisors.json').write_text(json.dumps(doc, indent=1) + '\n')
print(f"advisors: {len(ADVISORS)} figures, {topics} topics "
      f"({reads} read from other registries, {topics - reads} written here) "
      f"(source stamp {stamp})")
