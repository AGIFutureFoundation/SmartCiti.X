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

THE OPERATOR, AND THE `seat.*` BINDINGS. Eight advisors stand in hall
rooms or on the green; the ninth, the Operator, stands inside a
simulator's own yard instead (`stands_in: 'yard'`) - a place this build
did not have a voice in before now. The `sim.*` bindings the Inspector
and Foreman already use resolve against a HALL's first bound seat (a
hall can train more than one machine, and only the first ever got
covered); the Operator's `seat.*` bindings resolve against whichever
seat is ACTUALLY running when asked, so a hall with three machines gets
three correct answers, not one answer repeated three times. Same
contract as every other topic here - read at view time from the
simulator registry, nothing copied into this one. `seat.procedure` is
the newest: the scripted reference operator's own ordered step list,
which sims/ declares and the page's policy is written around - so a
learner who asks "what is the reference procedure?" gets the same list
the operator actually drives by, quoted, never a second copy.

CREWS, AND WHY ONE VOICE WAS NOT ENOUGH. An advisor is one person in one
room, and most of what goes wrong on a trade task goes wrong in the gaps
between people rather than inside one of them. So this builder also emits
CREWS: named teams bound to a seat this bundle already has, each with the
roles that task is actually run by, and - the part that makes it a crew
rather than a list of job titles - the ordered hand-offs between them. A
learner standing in one hears the rigger call the load rigged, the
signalperson take the path and the operator call a hold, which is the shape
of the job rather than a description of it. Each role carries one condition
it stops the work for, and the build refuses any role that neither hands to
nor is handed to by another, because such a role has no reason to exist.

Crews reuse this file's own `read` bindings rather than inventing new ones,
which is deliberate: every crew answer already resolves against the seat
that is actually running, so adding crews needs no new page binding and no
second copy of any seat's record. The halls a crew reaches are READ from
its seat in the simulator registry rather than typed here. The provenance
word for all of it is SCRIPTED, the same word the reference operator
carries - and the content is unverified general practice, pending authoring
by journey-level practitioners, which the crew registry's honesty block
says in those terms rather than in a footnote.
"""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

# One bundle version, read from the manifest rather than typed here.
PACK_VERSION = json.load(open(ROOT / 'pack/manifest.json'))['pack_version']
BUILT = "2026-09-11"

# ---------------------------------------------------------------- topics ---
# `read` bindings name a path the PAGE resolves against its own data for the
# hall or campus the learner is standing in. The suite proves each one
# resolves; the page test proves the rendered answer is that record's value.
# The campus split the Dispatcher and the Orientation guide state - which
# campuses are flagship (RECORDED or DERIVED coordinates) and which are hubs
# (AUTHORED) - is READ here from the campus and geo registries and held
# against each other, so the advisors' prose can never name a hub that is
# not one or miss one that is. The doctrine's own rule: one truth, read.
_campuses = json.load(open(ROOT / 'unions/registry/campuses.json'))['campuses']
_geo = json.load(open(ROOT / 'geo/registry/campuses_geo.json'))['campuses']
_hubs = [ck for ck, c in _campuses.items() if not c['districts']]
_flagships = [ck for ck, c in _campuses.items() if c['districts']]
assert set(_hubs) | set(_flagships) == set(_geo), 'the two campus registries disagree'
assert all(_geo[ck]['provenance'] == 'AUTHORED' for ck in _hubs), \
    'a hub campus carries a coordinate tier the advisors do not say it does'
assert all(_geo[ck]['provenance'] in ('RECORDED', 'DERIVED') for ck in _flagships), \
    'a flagship campus carries a coordinate tier the advisors do not say it does'
N_WORD = {2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six', 7: 'seven',
          8: 'eight', 9: 'nine', 10: 'ten'}
HUB_CITIES = [_campuses[ck]['city'] for ck in _hubs]
HUB_N = N_WORD[len(_hubs)]
FLAG_N = N_WORD[len(_flagships)]
HUB_LIST = ', '.join(HUB_CITIES[:-1]) + ' and ' + HUB_CITIES[-1]

BINDINGS = {
    'conditions.ppe': 'the PPE list on this room\'s condition record',
    'conditions.hazards': 'the hazards this room\'s condition record carries',
    'conditions.env': 'the lux, air changes and noise this room is held to',
    'surface.finish': 'the floor finish this room is given, and why',
    'crib.tools': 'the tools this district\'s crib issues',
    'crib.drill': 'how the crib check is scored',
    'sim.walkaround': 'the pre-shift walkaround points for this hall\'s seat',
    'sim.rubric': 'what the seat at this hall actually measures',
    'seat.task': 'the goal of the seat currently running, read live rather '
                 'than from the hall it happens to have been entered from',
    'seat.controls': 'the control scheme of the seat currently running',
    'seat.dash': 'the gauges the seat currently running puts on the dash',
    'seat.rubric': 'what the seat currently running actually measures',
    'seat.walkaround': 'the pre-shift walkaround points for the seat '
                       'currently running',
    'seat.trade': 'every hall that actually trains on the seat currently '
                  'running, not just the one the learner is standing in',
    'seat.procedure': 'the scripted reference operator\'s own step list for '
                      'the seat currently running - the procedure the '
                      'page\'s policy is written around, read from the '
                      'simulator registry, with the axes it guarantees',
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
             'say': 'Four words are used on every label and they mean '
                    'exactly what they say. RECORDED is a fact taken from a '
                    'cited source and checked against it. DERIVED is '
                    'computed from a recorded fact. AUTHORED is typed from '
                    'general public knowledge, not cross-checked against '
                    'any file this build can verify - a materially weaker '
                    'claim than RECORDED, and labelled as one. SCHEMATIC is '
                    'drawn to teach and is not a survey of anywhere. The '
                    'buildings you are standing in are SCHEMATIC. The '
                    f'coordinates the {FLAG_N} flagship campuses sit on are '
                    f'RECORDED or DERIVED; the {HUB_N} hub campuses, '
                    f'{HUB_LIST}, are AUTHORED.'},
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
    'operator': {
        'name': 'Operator',
        'role': 'stands at the machine and walks you through the seat',
        'stands_in': 'yard',           # inside the sim's own yard, not a room
        'glyph': '👷',
        'crew': {'top': 'work-shirt', 'headwear': 'hard-cap',
                 'vest': 'hi-vis-2', 'extras': 'radio'},
        'greeting': 'Before you touch a control, ask me what this seat is '
                    'and what it actually measures.',
        'topics': [
            {'id': 'task', 'ask': 'What am I trying to do here?',
             'kind': 'read', 'bind': 'seat.task'},
            {'id': 'controls', 'ask': 'What do the controls do?',
             'kind': 'read', 'bind': 'seat.controls'},
            {'id': 'gauges', 'ask': 'What are the gauges telling me?',
             'kind': 'read', 'bind': 'seat.dash'},
            {'id': 'rubric', 'ask': 'What does this seat actually measure?',
             'kind': 'read', 'bind': 'seat.rubric'},
            {'id': 'walk', 'ask': 'What should I walk before I start?',
             'kind': 'read', 'bind': 'seat.walkaround'},
            {'id': 'trade', 'ask': 'Who actually trains on this machine?',
             'kind': 'read', 'bind': 'seat.trade'},
            {'id': 'procedure', 'ask': 'What is the reference procedure?',
             'kind': 'read', 'bind': 'seat.procedure'},
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
             'say': 'The coordinate here is RECORDED or DERIVED for the '
                    f'{FLAG_N} flagship campuses, AUTHORED for the {HUB_N} hub '
                    f'campuses ({", ".join(HUB_CITIES)}) - '
                    'and the distances between every campus pair are DERIVED '
                    'from those points by great circle either way. The '
                    'campus itself '
                    'is SCHEMATIC: no ground has been acquired, no '
                    'building has been consented, and nothing here is a '
                    'site plan.'},
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
    assert where in strands or where in ('door', 'green', 'yard'), \
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

# ----------------------------------------------------------------- crews ---
# An advisor is one voice in a room. A CREW is the other half of the same
# idea: a trade task that no single person is allowed to run, broken into
# the roles that actually run it, in the order they actually hand off to
# each other. A learner standing in a crew hears the job being run - the
# rigger calling the load rigged, the signalperson taking the path, the
# operator calling a hold - rather than one narrator describing all of it.
#
# WHY THESE ROLES AND NOT OTHERS. Every role here has a job nobody else on
# the crew can do and a specific condition it stops the job for. Most of
# them are roles that general practice treats as required rather than
# optional - a crane lift without a signalperson, an entry without an
# attendant, a hot work permit with nobody watching where the sparks land
# are all the same failure - and that is exactly the point being taught.
# The build refuses a role that hands to nobody and that nobody hands to,
# because a role with no place in the run is decoration.
#
# WHAT A CREW IS BOUND TO. A crew does not invent a place to stand. It
# names a SEAT that the simulator registry already declares, musters in a
# room strand the surfaces registry already declares, and reaches exactly
# the halls that seat already reaches - READ from sims/, never retyped
# here, so promoting a hall onto a seat promotes it onto the crew in the
# same edit. Every crew `read` topic reuses a binding the page already
# resolves against the live running seat, so a crew answer is a quote of
# the seat's own record and never a second copy of it.
#
# WHAT A CREW IS NOT. Not an AI, not a learned policy, not a real crew and
# not a permit. The roster, the hand-offs and the stop conditions are
# hand-written deterministic script - SCRIPTED, the same word the
# simulator registry's reference operator carries - and they are unverified
# general practice pending authoring by journey-level practitioners.

_sims_reg = json.load(open(ROOT / 'sims/registry/sims.json'))
_hall_slugs = {u['slug'] for u in
               json.load(open(ROOT / 'unions/registry/unions.json'))['unions']}

# The two values a role's `standing` may take. They are deliberately not
# the word "required": this bundle has no standing to say what a rule
# requires, only what practice widely does and what this Academy chose.
STANDING = {
    'commonly-required': 'general practice widely treats this role as one '
                         'the task may not run without',
    'academy-practice': 'the Academy runs the task this way; practice '
                        'elsewhere may fold this job into another role',
}

CREWS = {
    'crane-lift-crew': {
        'name': 'Crane lift crew',
        'job': 'Pick the load off the supply pad and set it in the ring with '
               'nobody underneath it and nobody guessing.',
        'seat': 'crane-lift',
        'muster': 'coordination',
        'why_a_crew': 'The operator cannot see the load land. That single '
                      'fact is the whole reason this is four people: one '
                      'who owns the plan, one who can see what the cab '
                      'cannot, one who knows what the load weighs and how '
                      'it is held, and one who moves nothing that was not '
                      'called.',
        'stop_work': 'Every one of the four can stop this lift, and the '
                     'crane holds on a stop signal from anyone at all - '
                     'that is the one signal nobody needs standing to give.',
        'roles': {
            'lift-director': {
                'name': 'Lift director',
                'job': 'owns the lift plan and is the only voice that changes it',
                'standing': 'commonly-required',
                'stops': 'the plan changed on the ground and nobody wrote the new one',
                'glyph': '📋',
                'wears': {'top': 'flannel', 'headwear': 'full-brim',
                          'vest': 'hi-vis-3', 'extras': 'radio'},
                'post': {'r': 7.2, 'deg': 200},
                'greeting': 'Nothing gets hooked until the plan is read out '
                            'loud and everyone here has heard their part of it.',
                'topics': [
                    {'id': 'plan', 'ask': 'What is in a lift plan?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'The weight, where it is picked from and set, '
                            'the radius at each end, the rigging chosen for '
                            'that weight, the path the load travels and who '
                            'stands where while it does. If a lift plan does '
                            'not say who is on the crew, it is a sketch.'},
                    {'id': 'change', 'ask': 'What if the lift changes?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'Then it is a different lift and it gets planned '
                            'again. The failure worth fearing is not a bad '
                            'plan - it is a good plan that quietly stopped '
                            'describing what is happening.'},
                    {'id': 'measures', 'ask': 'What is this seat holding us to?',
                     'kind': 'read', 'bind': 'seat.rubric'},
                ],
            },
            'crane-operator': {
                'name': 'Crane operator',
                'job': 'runs the machine and takes moves from one set of hands only',
                'standing': 'commonly-required',
                'stops': 'a signal I did not understand',
                'glyph': '👷',
                'wears': {'top': 'work-shirt', 'headwear': 'hard-cap',
                          'vest': 'hi-vis-2', 'extras': 'radio'},
                'post': {'r': 3.4, 'deg': 20},
                'greeting': 'I move on a signal and I hold on anything else. '
                            'Ask me what the controls do before you ask me to '
                            'do anything with them.',
                'topics': [
                    {'id': 'controls', 'ask': 'What do the controls do?',
                     'kind': 'read', 'bind': 'seat.controls'},
                    {'id': 'gauges', 'ask': 'What am I watching on the dash?',
                     'kind': 'read', 'bind': 'seat.dash'},
                    {'id': 'obey', 'ask': 'Whose signals do you take?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'One person’s, agreed before the pick, and '
                            'nobody else’s - except a stop, which I take '
                            'from anyone. Two people signalling one crane is '
                            'how a load ends up moving in a direction neither '
                            'of them meant.'},
                ],
            },
            'signalperson': {
                'name': 'Signalperson',
                'job': 'gives the crane its moves and owns the path the load travels',
                'standing': 'commonly-required',
                'stops': 'the load’s path crossing a person',
                'glyph': '📣',
                'wears': {'top': 'hi-vis-tee', 'headwear': 'hard-cap',
                          'vest': 'hi-vis-3', 'extras': 'gloves'},
                'post': {'r': 6.0, 'deg': 300},
                'greeting': 'The crane does what my hands do. Ask me what the '
                            'signals are and why there is only ever one of me.',
                'topics': [
                    {'id': 'signals', 'ask': 'Why hand signals at all?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'Because a radio fails quietly and a hand does '
                            'not. Signals are a fixed, small set precisely so '
                            'that they cannot be improvised: a signal the '
                            'operator has to interpret is a signal that has '
                            'already failed, and the correct response to one '
                            'is a hold.'},
                    {'id': 'one', 'ask': 'Can two of you signal at once?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'No. One signalperson per crane, named before the '
                            'lift and handed over out loud if it changes. The '
                            'only thing anybody else on site may signal is a '
                            'stop.'},
                    {'id': 'procedure', 'ask': 'What order does this lift run in?',
                     'kind': 'read', 'bind': 'seat.procedure'},
                ],
            },
            'rigger': {
                'name': 'Rigger',
                'job': 'chooses and makes the hitch, and knows what the load weighs',
                'standing': 'commonly-required',
                'stops': 'a load whose weight nobody can tell me',
                'glyph': '⛓️',
                'wears': {'top': 'long-sleeve', 'headwear': 'hard-cap',
                          'vest': 'tool-vest', 'tools': 'rigger'},
                'post': {'r': 5.4, 'deg': 120},
                'greeting': 'The hitch is mine and so is the weight. Ask me '
                            'either one before you ask for a hoist.',
                'topics': [
                    {'id': 'weight', 'ask': 'How do you know what it weighs?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'From the tag, the drawing or a calculation you '
                            'can show someone - never from how it looks. An '
                            'estimated weight is a decision to find out at the '
                            'worst possible moment whether the estimate was low.'},
                    {'id': 'hitch', 'ask': 'Why this hitch and not another?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'Because the sling angle, not the sling, decides '
                            'the tension. Shorten the legs and the same load '
                            'pulls harder on every one of them, which is why '
                            'the hitch is chosen for the geometry of this pick '
                            'and re-chosen when the geometry changes.'},
                    {'id': 'walk', 'ask': 'What gets walked before we hook?',
                     'kind': 'read', 'bind': 'seat.walkaround'},
                ],
            },
        },
        'run': [
            {'by': 'lift-director', 'to': 'rigger',
             'step': 'reads the plan out: weight, radius, hitch, path, and who stands where'},
            {'by': 'rigger', 'to': 'signalperson',
             'step': 'makes the hitch, checks the sling angles and calls the load rigged'},
            {'by': 'signalperson', 'to': 'crane-operator',
             'step': 'takes the load’s path, clears it of people, and gives the first move'},
            {'by': 'crane-operator', 'to': 'signalperson',
             'step': 'moves only on a signal, and calls a hold the moment one is unclear'},
            {'by': 'signalperson', 'to': 'rigger',
             'step': 'walks the load to the set and holds it still until hands are on it'},
            {'by': 'rigger', 'to': 'lift-director',
             'step': 'unhooks clear of the load and reports the pick closed against the plan'},
        ],
    },

    'hot-work-crew': {
        'name': 'Hot work crew',
        'job': 'Run an arc inside a building that was not built to have one '
               'in it, and leave it not on fire.',
        'seat': 'weld-bead',
        'muster': 'safety',
        'why_a_crew': 'A welder behind a shield can see about a hand’s '
                      'width of the world and is looking at the brightest '
                      'thing in it. Sparks travel further than people expect, '
                      'downwards and through gaps, and they smoulder for a '
                      'long time before they announce themselves. So one '
                      'person runs the bead, one watches where the sparks go, '
                      'and one owns the boundary of the area the work was '
                      'allowed in.',
        'stop_work': 'The fire watch stops this job without asking anyone, '
                     'and the permit holder stops it the moment the work '
                     'leaves the area the permit describes.',
        'roles': {
            'permit-holder': {
                'name': 'Permit holder',
                'job': 'issues the hot work permit and owns the boundary of the area it covers',
                'standing': 'commonly-required',
                'stops': 'work drifting outside the area the permit describes',
                'glyph': '🗂️',
                'wears': {'top': 'polo', 'headwear': 'hard-cap',
                          'vest': 'hi-vis-2', 'extras': 'id-badge'},
                'post': {'r': 6.8, 'deg': 210},
                'greeting': 'I issue for an area and a period, not for a '
                            'person and a day. Ask me what that means.',
                'topics': [
                    {'id': 'covers', 'ask': 'What does a hot work permit cover?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'A described area, for a described period, after '
                            'described preparation - what was moved, what was '
                            'covered, what was tested. It is not permission to '
                            'weld; it is a record that somebody walked the area '
                            'and made it survivable first.'},
                    {'id': 'close', 'ask': 'What closes it?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'The end of the fire watch, not the end of the '
                            'welding. A permit closed when the arc went out is '
                            'a permit that closed during the part of the job '
                            'where the fire usually starts.'},
                    {'id': 'trade', 'ask': 'Who trains on this seat?',
                     'kind': 'read', 'bind': 'seat.trade'},
                ],
            },
            'welder': {
                'name': 'Welder',
                'job': 'runs the bead, and can see almost nothing while doing it',
                'standing': 'commonly-required',
                'stops': 'a bead I cannot run without moving a screen or a fuel source',
                'glyph': '🔥',
                'wears': {'top': 'work-shirt', 'headwear': 'welding-cap',
                          'vest': 'fire-resist', 'extras': 'welding-shield',
                          'tools': 'welder'},
                'post': {'r': 3.2, 'deg': 350},
                'greeting': 'Behind this shield I can see the puddle and '
                            'nothing else. Ask me what the seat is asking for.',
                'topics': [
                    {'id': 'task', 'ask': 'What is this run asking for?',
                     'kind': 'read', 'bind': 'seat.task'},
                    {'id': 'controls', 'ask': 'What do the controls do?',
                     'kind': 'read', 'bind': 'seat.controls'},
                    {'id': 'blind', 'ask': 'What can you not see from there?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'Everything except the puddle. Where the spatter '
                            'landed, who walked in behind me, whether the '
                            'screen is still where it was set - none of that '
                            'reaches me, which is why somebody else is paid to '
                            'watch it and why I stop when they say so.'},
                ],
            },
            'fire-watch': {
                'name': 'Fire watch',
                'job': 'watches where the sparks land, not the arc, and stays after the arc stops',
                'standing': 'commonly-required',
                'stops': 'a spark landing somewhere I cannot see where it went',
                'glyph': '🧯',
                'wears': {'top': 'hi-vis-tee', 'headwear': 'hard-cap',
                          'vest': 'fire-resist', 'extras': 'face-shield'},
                'post': {'r': 5.6, 'deg': 80},
                'greeting': 'I am not watching the weld. Ask me what I am '
                            'watching and how long I stay.',
                'topics': [
                    {'id': 'watching', 'ask': 'What are you actually watching?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'The floor, the gaps in it, the level below, and '
                            'anything the sparks could have reached and not '
                            'obviously set alight. A fire watch who is '
                            'watching the arc is a spectator with a '
                            'fire extinguisher.'},
                    {'id': 'after', 'ask': 'How long do you stay after?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'Past the end of the work, and then a second look '
                            'after that. Smouldering is slow and quiet by '
                            'definition - if it were fast and loud it would '
                            'not need a watch. The exact period is set by the '
                            'permit and by your jurisdiction, not by this '
                            'bundle.'},
                    {'id': 'walk', 'ask': 'What gets walked before the arc?',
                     'kind': 'read', 'bind': 'seat.walkaround'},
                ],
            },
        },
        'run': [
            {'by': 'permit-holder', 'to': 'welder',
             'step': 'walks the area, clears or covers what can burn, and issues for that area only'},
            {'by': 'welder', 'to': 'fire-watch',
             'step': 'sets the screens and the leads, then says the arc is about to be struck'},
            {'by': 'fire-watch', 'to': 'welder',
             'step': 'takes station where the sparks land, not where the arc is, and says the watch is set'},
            {'by': 'welder', 'to': 'fire-watch',
             'step': 'runs the bead, and says out loud when the arc is out'},
            {'by': 'fire-watch', 'to': 'permit-holder',
             'step': 'holds the watch through the whole post-work period, then hands the permit back to be closed'},
        ],
    },

    'confined-space-crew': {
        'name': 'Confined space entry crew',
        'job': 'Put a welder inside the tank and get the same person back out.',
        # The same seat as the hot work crew, deliberately. A tank interior
        # is the textbook case where both crews run at once on one job, and
        # a learner who sees only one of them has learned the wrong lesson;
        # the build allows a seat to carry more than one crew for exactly
        # this reason, and requires each to muster in a different room.
        'seat': 'weld-bead',
        'muster': 'procedure',
        'why_a_crew': 'The entrant cannot rescue the entrant. Every part of '
                      'this roster exists because of that: somebody outside '
                      'who never goes in, whose only job is to know who is in '
                      'and to stay in contact, and somebody who owns the '
                      'conditions the entry was authorised under and can '
                      'withdraw them.',
        'stop_work': 'The attendant ends this entry alone and without '
                     'discussion, and the entrant leaves on the attendant’s '
                     'word rather than on their own judgement.',
        'roles': {
            'entry-supervisor': {
                'name': 'Entry supervisor',
                'job': 'authorises the entry against tested conditions, and closes it',
                'standing': 'commonly-required',
                'stops': 'an entry whose conditions no longer describe the space',
                'glyph': '📝',
                'wears': {'top': 'polo', 'headwear': 'hard-cap',
                          'vest': 'hi-vis-3', 'extras': 'id-badge'},
                'post': {'r': 7.0, 'deg': 160},
                'greeting': 'The entry is authorised for conditions, not for '
                            'people. Ask me which conditions.',
                'topics': [
                    {'id': 'authorise', 'ask': 'What are you authorising?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'A specific space, isolated a specific way, tested '
                            'and found to be in a specific state, entered by '
                            'named people with a named means of getting them '
                            'out. Change any one of those and the '
                            'authorisation is void - it did not describe this '
                            'anymore.'},
                    {'id': 'isolate', 'ask': 'Why isolate before testing?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'Because a test tells you what the space was like '
                            'when you tested it, and a line that can still '
                            'feed it makes that a snapshot rather than a fact. '
                            'Isolation is what turns a reading into something '
                            'worth relying on.'},
                    {'id': 'trade', 'ask': 'Which halls train on this seat?',
                     'kind': 'read', 'bind': 'seat.trade'},
                ],
            },
            'attendant': {
                'name': 'Attendant',
                'job': 'stays outside, counts who is in, keeps contact, and never enters',
                'standing': 'commonly-required',
                'stops': 'losing contact with the entrant, for any reason at all',
                'glyph': '👁️',
                'wears': {'top': 'long-sleeve', 'headwear': 'hard-cap',
                          'vest': 'hi-vis-3', 'extras': 'radio'},
                'post': {'r': 4.6, 'deg': 250},
                'greeting': 'I do not go in. Ask me why that is the whole job.',
                'topics': [
                    {'id': 'never', 'ask': 'Why do you never go in?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'Because the attendant who goes in to help is the '
                            'second casualty, and the space now contains two '
                            'people and no attendant. Most multiple-fatality '
                            'confined space events are would-be rescuers. '
                            'Staying outside is not caution; it is the '
                            'rescue plan working.'},
                    {'id': 'contact', 'ask': 'What counts as contact?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'Something that tells you the entrant is all '
                            'right, continuously, and that you would notice '
                            'stopping. Silence is not contact. A reply you '
                            'have to ask twice for is a reason to end the '
                            'entry, not a reason to ask a third time.'},
                    {'id': 'walk', 'ask': 'What gets walked before an entry?',
                     'kind': 'read', 'bind': 'seat.walkaround'},
                ],
            },
            'entrant': {
                'name': 'Entrant',
                'job': 'does the work inside, and leaves the moment they are told to',
                'standing': 'commonly-required',
                'stops': 'any change in the air, the light or the way out',
                'glyph': '🔦',
                'wears': {'top': 'coveralls', 'headwear': 'hard-cap',
                          'vest': 'harness', 'extras': 'headlamp'},
                'post': {'r': 3.0, 'deg': 40},
                'greeting': 'Inside, the exit is the only thing I keep '
                            'track of. Ask me what the work is.',
                'topics': [
                    {'id': 'task', 'ask': 'What is the work in here?',
                     'kind': 'read', 'bind': 'seat.task'},
                    {'id': 'out', 'ask': 'When do you come out?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'On the attendant’s word, on any alarm, or on '
                            'anything I do not like - and I do not finish the '
                            'pass first. The instinct to finish the thing you '
                            'are holding is the instinct this drill exists to '
                            'break.'},
                    {'id': 'air', 'ask': 'What changes the air in here?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'The work does. Welding consumes what is in the '
                            'space and adds what was not, cutting and cleaning '
                            'do the same, and a space that tested fine before '
                            'the arc is not the space that exists ten minutes '
                            'later. That is why the testing is continuous '
                            'rather than a gate at the door.'},
                ],
            },
        },
        'run': [
            {'by': 'entry-supervisor', 'to': 'attendant',
             'step': 'isolates the space, has it tested, and authorises the entry against what the test found'},
            {'by': 'attendant', 'to': 'entrant',
             'step': 'logs who is going in, sets the means of contact, and takes station at the opening'},
            {'by': 'entrant', 'to': 'attendant',
             'step': 'enters and reports that the space matches what was authorised before touching the work'},
            {'by': 'attendant', 'to': 'entry-supervisor',
             'step': 'raises anything that changed - the air, the contact, a second body at the opening'},
            {'by': 'entrant', 'to': 'attendant',
             'step': 'comes out on the word, and is counted out by name'},
        ],
    },

    'scaffold-crew': {
        'name': 'Scaffold crew',
        'job': 'Build one bay in the order that keeps the people building it '
               'off the ground and on it.',
        'seat': 'scaffold-bay',
        'muster': 'materials',
        'why_a_crew': 'A scaffold is assembled by the people who will be '
                      'standing on the unfinished version of it, which is the '
                      'only structure on site with that property. So the '
                      'order is not a preference, the material has to arrive '
                      'in that order, and the person who says the bay may be '
                      'used is not the person who built it.',
        'stop_work': 'The ground tender stops this build when anyone walks '
                     'under it, and the competent person stops it when the '
                     'bay has changed since it was tagged.',
        'roles': {
            'scaffold-competent-person': {
                'name': 'Competent person',
                'job': 'inspects the bay and tags it before anyone else stands on it',
                'standing': 'commonly-required',
                'stops': 'a bay that has been altered since it was tagged',
                'glyph': '🔍',
                'wears': {'top': 'polo', 'headwear': 'hard-cap',
                          'vest': 'hi-vis-2', 'extras': 'id-badge'},
                'post': {'r': 6.6, 'deg': 190},
                'greeting': 'A tag is a claim somebody signed. Ask me what it '
                            'claims and what voids it.',
                'topics': [
                    {'id': 'tag', 'ask': 'What does the tag actually say?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'That a named person looked at this bay, on this '
                            'date, and found it complete for the use it is '
                            'tagged for. It does not say it is safe forever '
                            'and it does not survive the bay being modified by '
                            'someone in a hurry at half past four.'},
                    {'id': 'competent', 'ask': 'What makes someone competent here?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'Being able to recognise the hazard and having the '
                            'authority to have it fixed. Both halves matter: '
                            'recognition without authority is a witness, and '
                            'authority without recognition is a signature. '
                            'Who holds that standing is decided by your '
                            'jurisdiction and your employer, never by this '
                            'bundle.'},
                    {'id': 'measures', 'ask': 'What is this bay measured on?',
                     'kind': 'read', 'bind': 'seat.rubric'},
                ],
            },
            'erector': {
                'name': 'Erector',
                'job': 'sets sills, frames, braces, planks and rails, in that order',
                'standing': 'commonly-required',
                'stops': 'a part handed up out of its stage',
                'glyph': '🔩',
                'wears': {'top': 'work-shirt', 'headwear': 'hard-cap',
                          'vest': 'harness', 'tools': 'basic'},
                'post': {'r': 3.6, 'deg': 10},
                'greeting': 'I build it in one order and refuse it in any '
                            'other. Ask me what that order is.',
                'topics': [
                    {'id': 'procedure', 'ask': 'What order does this bay go up in?',
                     'kind': 'read', 'bind': 'seat.procedure'},
                    {'id': 'why', 'ask': 'Why does the order matter that much?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'Because every stage is what the next stage is '
                            'built from. Frames on unlevel sills are already '
                            'wrong and get wronger with height; planks before '
                            'braces put weight on a frame that is not yet held '
                            'square; and rails last means the last thing you '
                            'do is the thing that stops the fall.'},
                    {'id': 'base', 'ask': 'Why so much fuss about the sills?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'A scaffold is a stack, and a stack amplifies what '
                            'is under it. Out of level at the sill is out of '
                            'plumb at the top, and a leg that is carrying on '
                            'soft ground finds that out during, not before.'},
                ],
            },
            'ground-tender': {
                'name': 'Ground tender',
                'job': 'keeps the drop zone, and passes material up in the order it is called for',
                'standing': 'academy-practice',
                'stops': 'somebody walking under the bay while a part is moving',
                'glyph': '🪜',
                'wears': {'top': 'hi-vis-tee', 'headwear': 'hard-cap',
                          'vest': 'hi-vis-3', 'extras': 'gloves'},
                'post': {'r': 5.8, 'deg': 110},
                'greeting': 'Everything that goes up goes through me, and '
                            'nothing comes down through anybody.',
                'topics': [
                    {'id': 'zone', 'ask': 'What is a drop zone?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'The ground a dropped part would reach, which is '
                            'bigger than directly underneath because parts '
                            'bounce and roll. It is kept clear by a person '
                            'rather than by tape, because tape does not notice '
                            'anyone stepping over it.'},
                    {'id': 'order', 'ask': 'Why not just send everything up at once?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'Because a deck stacked with parts that belong to '
                            'a later stage is a deck you cannot work on and a '
                            'load nobody calculated. Material arriving in '
                            'build order is the cheapest way to make the wrong '
                            'order physically awkward.'},
                    {'id': 'walk', 'ask': 'What gets walked before we start?',
                     'kind': 'read', 'bind': 'seat.walkaround'},
                ],
            },
        },
        'run': [
            {'by': 'ground-tender', 'to': 'erector',
             'step': 'levels and beds the sills, then passes the first frames up'},
            {'by': 'erector', 'to': 'ground-tender',
             'step': 'sets frames and braces, and calls for the next stage only once the one below is complete'},
            {'by': 'ground-tender', 'to': 'erector',
             'step': 'holds the drop zone and passes planks and rails in the order they were called'},
            {'by': 'erector', 'to': 'scaffold-competent-person',
             'step': 'lands the guardrails and hands the finished bay over to be inspected'},
            {'by': 'scaffold-competent-person', 'to': 'ground-tender',
             'step': 'inspects, tags the bay, and says out loud who may now stand on it'},
        ],
    },

    'trench-crew': {
        'name': 'Trench crew',
        'job': 'Cut the trench to grade over a live utility without putting '
               'the bucket or a person into it.',
        'seat': 'excavator-trench',
        'muster': 'layout',
        'why_a_crew': 'Two of the things that can go wrong here are invisible '
                      'from the cab: what is buried in front of the bucket, '
                      'and who has walked into the swing behind it. Neither '
                      'is solved by a more careful operator. They are solved '
                      'by somebody whose only job is to have seen them.',
        'stop_work': 'The spotter stops this machine with one call and does '
                     'not explain it first; the locator stops the cut when a '
                     'mark is lost rather than when it is proved wrong.',
        'roles': {
            'excavator-operator': {
                'name': 'Excavator operator',
                'job': 'runs the machine, and stops the moment the spotter goes out of sight',
                'standing': 'commonly-required',
                'stops': 'a spotter I can no longer see',
                'glyph': '👷',
                'wears': {'top': 'work-shirt', 'headwear': 'hard-cap',
                          'vest': 'hi-vis-2', 'extras': 'ear-muffs'},
                'post': {'r': 3.4, 'deg': 350},
                'greeting': 'From up here the blind spot is behind me and '
                            'below me. Ask me what the controls do.',
                'topics': [
                    {'id': 'controls', 'ask': 'What do the controls do?',
                     'kind': 'read', 'bind': 'seat.controls'},
                    {'id': 'gauges', 'ask': 'What am I watching on the dash?',
                     'kind': 'read', 'bind': 'seat.dash'},
                    {'id': 'blind', 'ask': 'What can you not see from the cab?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'The counterweight’s whole arc, the ground '
                            'immediately at the tracks, and anything at all in '
                            'the trench. That last one matters most: a bucket '
                            'is a poor instrument for finding out whether '
                            'somebody stepped down for a moment.'},
                ],
            },
            'trench-competent-person': {
                'name': 'Competent person',
                'job': 'inspects the ground and the cut, and sets what may be taken without support',
                'standing': 'commonly-required',
                'stops': 'water, spoil or vibration changing the ground since the last inspection',
                'glyph': '🪨',
                'wears': {'top': 'polo', 'headwear': 'full-brim',
                          'vest': 'hi-vis-3', 'extras': 'id-badge'},
                'post': {'r': 6.4, 'deg': 210},
                'greeting': 'The soil decides how deep this goes, not the '
                            'schedule. Ask me what I am reading it for.',
                'topics': [
                    {'id': 'soil', 'ask': 'What are you reading the ground for?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'Whether it will stand on its own, for how long, '
                            'and what has changed since the last time anyone '
                            'looked. Rain, a spoil pile set too close and a '
                            'compactor running past all change the answer '
                            'without changing the look of it.'},
                    {'id': 'again', 'ask': 'How often does it get inspected?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'Before the shift, after anything that could have '
                            'changed it, and again if you have to ask. The '
                            'point of repeated inspection is that a trench is '
                            'not a finished object - it is a hole that is '
                            'still deciding.'},
                    {'id': 'measures', 'ask': 'What is this cut measured on?',
                     'kind': 'read', 'bind': 'seat.rubric'},
                ],
            },
            'spotter': {
                'name': 'Spotter',
                'job': 'stands where the operator cannot see and owns the swing radius',
                'standing': 'commonly-required',
                'stops': 'anyone entering the swing radius',
                'glyph': '🦺',
                'wears': {'top': 'hi-vis-tee', 'headwear': 'hard-cap',
                          'vest': 'hi-vis-3', 'extras': 'radio'},
                'post': {'r': 5.6, 'deg': 300},
                'greeting': 'I stand where you cannot and I have one call. '
                            'Ask me what it is.',
                'topics': [
                    {'id': 'call', 'ask': 'What is your one call?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'Stop. Not slow, not careful, not left a bit - '
                            'stop, and then we talk. A spotter with a '
                            'vocabulary is a second operator with worse '
                            'information, and the machine cannot follow two '
                            'people.'},
                    {'id': 'where', 'ask': 'Where do you stand?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'Outside the swing, in the operator’s mirror '
                            'or eyeline, and never between the machine and '
                            'anything solid. If the operator cannot see me, I '
                            'am not spotting - I am just a person standing '
                            'near an excavator.'},
                    {'id': 'walk', 'ask': 'What gets walked before a start?',
                     'kind': 'read', 'bind': 'seat.walkaround'},
                ],
            },
            'locator': {
                'name': 'Utility locator',
                'job': 'marks what is buried before the first cut, and re-marks it when marks are lost',
                'standing': 'commonly-required',
                'stops': 'a cut near a mark that nobody has proved',
                'glyph': '📡',
                'wears': {'top': 'long-sleeve', 'headwear': 'ball-cap',
                          'vest': 'surveyor', 'tools': 'surveyor'},
                'post': {'r': 7.4, 'deg': 140},
                'greeting': 'Paint on the ground is a guess with a tolerance. '
                            'Ask me how big the tolerance is.',
                'topics': [
                    {'id': 'marks', 'ask': 'How good are the marks?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'Good enough to tell you roughly where to be '
                            'careful, and never good enough to dig hard '
                            'against. A locate has a tolerance either side, '
                            'and the depth is the least reliable part of it - '
                            'the paint says where, not how deep.'},
                    {'id': 'prove', 'ask': 'What does proving a mark mean?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'Exposing the thing by hand or by vacuum until you '
                            'can see it, rather than inferring it from a line '
                            'somebody sprayed last week. Everything else is a '
                            'hypothesis being tested with a machine that wins '
                            'every argument.'},
                    {'id': 'task', 'ask': 'What is this cut trying to do?',
                     'kind': 'read', 'bind': 'seat.task'},
                ],
            },
        },
        'run': [
            {'by': 'locator', 'to': 'trench-competent-person',
             'step': 'marks what is buried and says which marks are proved and which are only painted'},
            {'by': 'trench-competent-person', 'to': 'excavator-operator',
             'step': 'inspects the ground and sets the depth the machine may take without support'},
            {'by': 'excavator-operator', 'to': 'spotter',
             'step': 'sets up on level ground and asks for the swing radius to be walked and held'},
            {'by': 'spotter', 'to': 'excavator-operator',
             'step': 'takes station in the operator’s eyeline, keeps the radius clear, and holds the one call'},
            {'by': 'excavator-operator', 'to': 'trench-competent-person',
             'step': 'cuts cell by cell and stops shallow where the marked service runs'},
            {'by': 'trench-competent-person', 'to': 'locator',
             'step': 're-inspects after anything that changed the ground, and sends the locator back when a mark is gone'},
        ],
    },

    'aerial-lift-crew': {
        'name': 'Aerial lift crew',
        'job': 'Take the basket to every work point overhead and bring it '
               'down - including on the day the person in it cannot.',
        'seat': 'boom-lift',
        'muster': 'inspection',
        'why_a_crew': 'A basket at height with one person in it has no '
                      'recovery path. The ground attendant is that path, and '
                      'the line observer exists because judging clearance to '
                      'an overhead conductor from inside the basket is '
                      'exactly the judgement the geometry makes hardest.',
        'stop_work': 'The line observer stops every move toward the '
                     'conductor, and the ground attendant brings the basket '
                     'down without waiting for agreement from the person in it.',
        'roles': {
            'basket-operator': {
                'name': 'Basket operator',
                'job': 'works from the platform, clipped to the basket and nothing else',
                'standing': 'commonly-required',
                'stops': 'a basket I cannot level or a harness I cannot clip',
                'glyph': '🧗',
                'wears': {'top': 'work-shirt', 'headwear': 'climbing',
                          'vest': 'harness', 'extras': 'gloves'},
                'post': {'r': 3.2, 'deg': 30},
                'greeting': 'I am clipped to the basket, not to the building. '
                            'Ask me why that is not a detail.',
                'topics': [
                    {'id': 'task', 'ask': 'What is this run asking for?',
                     'kind': 'read', 'bind': 'seat.task'},
                    {'id': 'clip', 'ask': 'Why clip to the basket?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'Because a boom that moves takes the basket with '
                            'it, and anything you are tied to that does not '
                            'move becomes the thing that pulls you out. The '
                            'anchor rides with the platform for the same '
                            'reason a seatbelt is bolted to the car.'},
                    {'id': 'gauges', 'ask': 'What is the dash telling me?',
                     'kind': 'read', 'bind': 'seat.dash'},
                ],
            },
            'ground-attendant': {
                'name': 'Ground attendant',
                'job': 'mans the ground controls and can bring the basket down without help from it',
                'standing': 'commonly-required',
                'stops': 'an operator who has stopped answering',
                'glyph': '🆘',
                'wears': {'top': 'hi-vis-tee', 'headwear': 'hard-cap',
                          'vest': 'hi-vis-3', 'extras': 'radio'},
                'post': {'r': 5.4, 'deg': 250},
                'greeting': 'My job is the day this goes wrong. Ask me what '
                            'that looks like.',
                'topics': [
                    {'id': 'rescue', 'ask': 'What happens if they collapse up there?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'I bring the basket down on the ground controls, '
                            'which is why they get proved at the start of the '
                            'shift rather than discovered at the worst moment. '
                            'A rescue plan that begins with calling somebody '
                            'is a plan with a travel time in it.'},
                    {'id': 'sight', 'ask': 'Why stay within sight and sound?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'Because the first sign of most of what goes wrong '
                            'up there is somebody going quiet, and you only '
                            'notice quiet if you were listening. Wandering off '
                            'to do something useful is the most common way '
                            'this role stops existing.'},
                    {'id': 'walk', 'ask': 'What gets walked before we go up?',
                     'kind': 'read', 'bind': 'seat.walkaround'},
                ],
            },
            'line-observer': {
                'name': 'Line observer',
                'job': 'watches the clearance to the overhead conductor and nothing else',
                'standing': 'academy-practice',
                'stops': 'any part of the machine closing on the exclusion zone',
                'glyph': '⚡',
                'wears': {'top': 'long-sleeve', 'headwear': 'hard-cap',
                          'vest': 'hi-vis-3', 'extras': 'safety-glasses'},
                'post': {'r': 6.8, 'deg': 330},
                'greeting': 'I am watching one gap and nothing else. Ask me '
                            'why that gap is hard to judge from up there.',
                'topics': [
                    {'id': 'zone', 'ask': 'What is the exclusion zone?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'A distance from the conductor that no part of the '
                            'machine, the load or the person enters - measured '
                            'to the whole machine, not to the basket, because '
                            'the boom and the load get there first. The actual '
                            'distance comes from your jurisdiction and the '
                            'line’s voltage, and this bundle does not '
                            'supply it.'},
                    {'id': 'judge', 'ask': 'Why can the basket not judge it?',
                     'kind': 'say', 'cites': 'agents/build.py',
                     'say': 'Because you are looking along the gap rather than '
                            'across it, and a gap seen end-on looks like '
                            'whatever you were hoping. From the ground, at an '
                            'angle, the same gap is a distance you can '
                            'actually call.'},
                    {'id': 'measures', 'ask': 'What is this run measured on?',
                     'kind': 'read', 'bind': 'seat.rubric'},
                ],
            },
        },
        'run': [
            {'by': 'line-observer', 'to': 'basket-operator',
             'step': 'walks the overhead line, sets the exclusion zone on the ground and says where it is'},
            {'by': 'basket-operator', 'to': 'ground-attendant',
             'step': 'sets the stabilizers on the level pad, clips to the basket anchor, and calls for the ground controls to be manned'},
            {'by': 'ground-attendant', 'to': 'basket-operator',
             'step': 'proves the ground controls, then stays in sight and sound for the whole run'},
            {'by': 'basket-operator', 'to': 'line-observer',
             'step': 'takes the basket to each work point and asks for a clearance call before every move toward the line'},
            {'by': 'line-observer', 'to': 'ground-attendant',
             'step': 'calls the clearance, and calls the stop the moment the machine closes on the zone'},
        ],
    },
}

CREW_CONTRACT = (
    'a crew is a roster and a run. The roster names roles that each have a '
    'job nobody else on the crew does and one condition that role stops the '
    'work for; the run is the ordered list of hand-offs between them, and '
    'the build refuses a role that appears in neither end of it. A crew '
    'names a seat the simulator registry already declares and musters in a '
    'room strand the surfaces registry already declares; the halls it '
    'reaches are READ from that seat rather than typed here. Every `read` '
    'topic a role carries is one of the advisor registry\'s own declared '
    'bindings, resolved by the page against the seat that is actually '
    'running - so a crew quotes the record and never keeps a second copy.'
)

CREW_HONESTY = {
    'status': 'SCRIPTED: a crew is a hand-written, deterministic script - a '
              'fixed roster, a fixed order of hand-offs and a fixed list of '
              'things each role can say. No model runs behind one, nothing '
              'is generated at view time, and no network is reached. Not a '
              'learned policy, not a real crew, and not a claim about how '
              'any particular site runs a job.',
    'unverified': 'the roles, the hand-offs and the stop conditions written '
                  'here are unverified general practice, pending authoring '
                  'by journey-level practitioners of each trade. Where a '
                  'role is marked commonly-required that is a statement '
                  'about widespread practice as this Academy understands '
                  'it, not a reading of any jurisdiction\'s rule, and every '
                  'distance, period and threshold a role mentions is '
                  'deliberately left to the reader\'s own jurisdiction '
                  'rather than given a number here.',
    'not_a_permit': 'nothing a crew role says is a permit, an entry '
                    'authorisation, a tag, a certificate or a code ruling. '
                    'The permits, tags and authorisations named here are the '
                    'names of real artefacts, and this bundle issues none of '
                    'them and stands in for none of them.',
    'not_a_person': 'a crew role represents no real worker, supervisor or '
                    'union officer, and no real union local is named: the '
                    'figures are the Academy\'s own schematic avatars '
                    'wearing the Academy\'s own crew marks, exactly as the '
                    'advisors are.',
    'not_scored': 'standing in a crew changes no score and unlocks nothing: '
                  'no grader reads crew state, there is no crew state for '
                  'one to read, and the suite asserts it by reading the '
                  'graders.',
    'closed_book': 'a crew role cannot be asked an open question because it '
                   'has no way to answer one. The topics under each role '
                   'are all of them, and the suite counts them.',
}

# What the page has to do to put a crew in the walkable world. This is a
# CONTRACT, not a description of what the page does today: the crews land
# in the registry first so that the page edit is a single reviewable change
# with the data already proven to resolve. Nothing here is asserted against
# the page yet, deliberately - the bindings ARE asserted below, because
# those already exist and a crew that named one the page cannot resolve
# would be a bug shipped in silence.
CREW_PAGE_CONTRACT = {
    'data': 'D.crews.crews, alongside D.advisors.who',
    'place': 'one placeAdvisor()-shaped spawner per crew, called from '
             'startSim() beside the Operator: each role stands at its own '
             '`post` - polar, r metres from the seat\'s own yard origin at '
             '`deg` degrees - inside the sim group, so leaving the seat '
             'drops the whole crew the way clearOperatorAdvisor() drops the '
             'Operator today',
    'ask': 'openAdvisor() takes a "crew-id:role-id" key as well as an '
           'advisor id; the role\'s topics render through the same panel, '
           'and a `read` topic goes to the existing advRead() unchanged '
           'because every crew binding is already a seat.* binding',
    'run': 'the crew\'s `run` renders as the crew\'s own panel - the '
           'ordered hand-offs, each one naming the role it comes from and '
           'the role it goes to - which is the part that reads as a job '
           'being run rather than as four separate advisors',
    'episode': 'recordEpisode({kind: "crew", crew, role, topic, '
               'answer_kind}), the same envelope the advisor exchange '
               'already writes',
}

# ------------------------------------------------------------ crew checks ---
# A crew that names a seat, a hall, a room or a binding which does not exist
# is the one failure mode that matters here, so every one of them is an
# assertion rather than a convention.
_crew_role_keys = set()
_crew_stops = set()
for cid, c in CREWS.items():
    assert cid not in ADVISORS, \
        f'crew {cid} collides with an advisor id; the page keys both flat'
    assert c['seat'] in _sims_reg['sims'], \
        f'crew {cid}: seat {c["seat"]} is not a seat the simulator registry declares'
    assert c['muster'] in strands, \
        f'crew {cid}: musters in {c["muster"]}, which is not a room strand'
    # the halls a crew reaches are the seat's own halls, read rather than
    # retyped - promote a hall onto the seat and the crew follows in the
    # same edit, which is the only way this stays one truth
    c['halls'] = list(_sims_reg['sims'][c['seat']]['halls'])
    assert c['halls'], f'crew {cid}: its seat reaches no hall at all'
    for hs in c['halls']:
        assert hs in _hall_slugs, \
            f'crew {cid}: hall {hs} is not a hall the union registry declares'
    # a pair is a hand-off, not a crew: the whole claim of this pack is that
    # the task needs a team, so three is the floor
    assert len(c['roles']) >= 3, f'crew {cid}: fewer than three roles is not a crew'
    assert any(r['standing'] == 'commonly-required' for r in c['roles'].values()), \
        f'crew {cid}: no role that practice commonly treats as required'
    for rid, r in c['roles'].items():
        key = f'{cid}:{rid}'
        assert key not in _crew_role_keys, f'{key}: duplicate crew role key'
        _crew_role_keys.add(key)
        r['key'] = key                      # computed once, never typed
        assert r['standing'] in STANDING, \
            f'{key}: standing {r["standing"]} is not one of the two declared'
        assert r['stops'] not in _crew_stops, \
            f'{key}: stops for {r["stops"]}, which another role already owns'
        _crew_stops.add(r['stops'])
        assert r['glyph'] and len(r['greeting']) > 20 and len(r['job']) > 15, \
            f'{key}: a role needs a glyph, a greeting and a stated job'
        for sec, pick in r['wears'].items():
            assert sec in opts, f'{key}: {sec} is not a locker section'
            assert pick in opts[sec], \
                f'{key}: {sec}={pick} is not an option in the locker'
        assert 3.0 <= r['post']['r'] <= 9.0 and 0 <= r['post']['deg'] < 360, \
            f'{key}: post is outside the yard ring the page can place into'
        assert r['topics'], f'{key}: a role with nothing to say'
        seen = set()
        for t in r['topics']:
            assert t['id'] not in seen, f'{key}: duplicate topic {t["id"]}'
            seen.add(t['id'])
            assert t['ask'].endswith('?'), f'{key}/{t["id"]}: a topic is a question'
            if t['kind'] == 'read':
                # a crew works at a running seat, so a crew `read` may only
                # reach seat.* - a room binding would silently resolve
                # against whichever room the page last had, which is the
                # hall/seat scoping bug the Operator already exists to fix
                assert t['bind'] in BINDINGS and t['bind'].startswith('seat.'), \
                    f'{key}/{t["id"]}: {t["bind"]} is not a declared seat binding'
            else:
                assert t['kind'] == 'say' and t['say'] and t['cites'], \
                    f'{key}/{t["id"]}: a say needs words and a citation'
                assert (ROOT / t['cites']).exists(), \
                    f'{key}/{t["id"]}: cites {t["cites"]}, missing'
                # one truth per fact: a crew never restates the seat's own
                # task, rubric or walkaround in prose - it quotes them
                assert _sims_reg['sims'][c['seat']]['task'] not in t['say'], \
                    f'{key}/{t["id"]}: copies the seat\'s task instead of reading it'
    # two posts in one spot would put two rigged figures inside each other
    degs = [r['post']['deg'] for r in c['roles'].values()]
    assert len(degs) == len(set(degs)), f'crew {cid}: two roles stand in one spot'
    # the run is what makes this a crew rather than a list of job titles
    assert len(c['run']) >= 4, f'crew {cid}: a run this short is not a hand-off chain'
    for i, s in enumerate(c['run']):
        assert s['by'] in c['roles'], f'crew {cid} step {i}: {s["by"]} is not on this crew'
        assert s['to'] in c['roles'], f'crew {cid} step {i}: {s["to"]} is not on this crew'
        assert s['by'] != s['to'], f'crew {cid} step {i}: a hand-off to yourself'
        assert len(s['step']) > 25, f'crew {cid} step {i}: say what actually passes'
    # a role nobody hands to, and that hands to nobody, is decoration - and
    # the point of this pack is that every one of these roles has a job
    _by = {s['by'] for s in c['run']}
    _to = {s['to'] for s in c['run']}
    for rid in c['roles']:
        assert rid in _by, f'crew {cid}: {rid} never does anything in the run'
        assert rid in _to, f'crew {cid}: nobody ever hands to {rid}'

# two crews may share a seat - a tank interior runs hot work and a confined
# space entry at once, and that is the lesson - but they may not also share
# the room they brief in, or a learner would find two musters in one place
_musters = [(c['seat'], c['muster']) for c in CREWS.values()]
assert len(_musters) == len(set(_musters)), 'two crews muster on one seat in one room'

# The provenance word for everything in this pack is SCRIPTED. `orbis/` owns
# AI-SYNTHESIZED and nothing here may borrow it, because nothing here is
# synthesised by anything.
assert 'SCRIPTED' in CREW_HONESTY['status'], 'the crew pack must say SCRIPTED'
assert 'AI-SYNTHESIZED' not in json.dumps(CREWS) + json.dumps(CREW_HONESTY), \
    'AI-SYNTHESIZED belongs to orbis/ and describes nothing in this pack'

if not BOOTSTRAP:
    # every binding a crew role reaches for is one the page already resolves.
    # This is the check that makes the page edit a placement change and
    # nothing more: no new binding has to be written for crews to answer.
    for cid, c in CREWS.items():
        for rid, r in c['roles'].items():
            for t in r['topics']:
                if t['kind'] == 'read':
                    assert f"case '{t['bind']}'" in page_src, \
                        f'{cid}:{rid}: the page cannot resolve {t["bind"]}'

crew_topics = [t for c in CREWS.values() for r in c['roles'].values()
               for t in r['topics']]
crew_doc = {
    'pack': 'smartcitix-trade-craft-academy-crews',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'contract': CREW_CONTRACT,
    'honesty': CREW_HONESTY,
    'standing': STANDING,
    'counts': {
        'crews': len(CREWS),
        'roles': len(_crew_role_keys),
        'topics': len(crew_topics),
        'read_topics': sum(1 for t in crew_topics if t['kind'] == 'read'),
        'say_topics': sum(1 for t in crew_topics if t['kind'] == 'say'),
        'handoffs': sum(len(c['run']) for c in CREWS.values()),
        'seats': len({c['seat'] for c in CREWS.values()}),
        'halls_reached': len({h for c in CREWS.values() for h in c['halls']}),
    },
    'page_contract': CREW_PAGE_CONTRACT,
    'crews': CREWS,
}
(OUT / 'crews.json').write_text(json.dumps(crew_doc, indent=1) + '\n')
print(f"crews: {crew_doc['counts']['crews']} crews, "
      f"{crew_doc['counts']['roles']} roles, "
      f"{crew_doc['counts']['topics']} topics, "
      f"{crew_doc['counts']['handoffs']} hand-offs, over "
      f"{crew_doc['counts']['seats']} seats reaching "
      f"{crew_doc['counts']['halls_reached']} halls")
