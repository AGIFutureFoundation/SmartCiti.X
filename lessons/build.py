#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the lessons registry builder.

WHAT WAS MISSING. The bundle addresses 11,000,000 module IDs generated from
an authored skeleton, and the manifest says so in plain words: those are
IDs, not hand-written lessons. Around them stand 111 halls, 1,221 rooms,
25 recovered training stations, 11 operable seats, 33 regional scenarios,
55 walkaround points, 8 tool cribs, 9 room advisors, 6 crews and a flipped
classroom that names four stages. Every one of those is a THING. None of
them is a LESSON YOU CAN STAND IN: a reason to walk to one particular room
in one particular hall and do something there, in an order somebody chose,
that leaves a record behind.

That is the whole of this pack. A lesson here is a short walk with steps.
It stands in a ROOM - and a room in this bundle is identified by the skill
STRAND that requires it, because `web/interiors.py` lays every hall out
from the 11 strands the hall teaches. So a lesson names a hall and a
strand, and the build refuses a strand the hall's own skill graph does not
carry.

EVERY STEP IS AN IN-WORLD ACT, AND EVERY REFERENCE RESOLVES. A step is one
of eight kinds, declared once in STEP_KINDS and closed: walk to a room,
read the door placard of a room, take a station at its bench, run the
district crib check, walk one pre-shift point of a seat, run one seat on
one scenario, ask one room advisor one of its fixed topics, or ask one
role of one crew one of its fixed topics while that crew's seat is
running. Every id in every step is resolved against the registry that owns
it - a station id against stations/, a scenario against sims/, a topic
against agents/ - and an id that does not resolve fails the build by name.

WHAT A STEP RECORDS IS A PROPERTY OF ITS KIND, NOT OF THE STEP. The four
episode kinds already exist in `training/registry/training.json`: sim,
advisor, crew, walkaround. This pack declares NO new episode kind and no
new storage key. Four of the eight step kinds write one of those four
episodes; the other four write nothing at all, and say so with an explicit
null rather than by silence. Walking into a room is not an achievement,
and a bundle that quietly logged it would be measuring attendance while
claiming to teach.

BREADTH, NOT DEPTH. Ten lessons in one hall would prove nothing about a
bundle that claims 111 trades. So the set is spread deliberately wide and
the spread is COMPUTED and asserted: distinct halls, distinct strands, and
a hard ceiling on the share of the set any single hall may hold. All 11
strands are covered or the build fails.

THE LADDER. Lessons sequence through prerequisites, and a prerequisite is
not an opinion: each edge names a REASON from a closed set - the two
lessons stand in the same hall, or they run the same seat, or their halls
draw from the same district tool crib - and the build checks that the
reason is actually true in the registries. The graph is then proved
acyclic by walking it, and every prerequisite is proved to exist.

WHERE THIS PLUGS IN. `schools/registry/schools.json` already declares the
flipped-classroom loop: explore at home, build in class, practise on the
floor, verify unaided. A lesson is not a fifth stage. It is the CLASS and
FLOOR halves made walkable, and it is asserted never to touch the other
two: `home` stays the module pack and i18n, and the `gate` is the one
stage that registry deliberately leaves ungamified.

PROVENANCE AND LIMIT. The steps, the order and the prose are AUTHORED -
written here, by us. Nothing in this pack is AI-SYNTHESIZED; that word
belongs to `orbis/` and describes generated video, which this is not.
And the limit travels with the capability in every direction: a lesson
certifies nobody, gates nothing, and scores nothing. Its content is
unverified general practice, written to be corrected and replaced by
journey-level practitioners from the halls it names - exactly what the
manifest, the stations pack and the sims pack already say about theirs.
"""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

# One bundle version, read from the manifest rather than typed here.
PACK_VERSION = json.load(open(ROOT / 'pack/manifest.json'))['pack_version']
BUILT = "2026-09-26"


def req(mapping, key, who):
    """A missing key raises and names itself. There is no default here
    because a default is a policy decision, and nobody decided one."""
    if key not in mapping:
        raise KeyError(f'{who}: {key!r} does not resolve')
    return mapping[key]


# --------------------------------------------------------- what is read ---
# Every fact below stays owned by the file it comes from. This pack keeps
# no second copy of a hall name, a strand, a room label, a station name, a
# seat name, a scenario name, an advisor name or a crew role name.
HALLS = json.load(open(ROOT / 'pack/registry/halls.json'))['halls']
SKILLS = json.load(open(ROOT / 'pack/registry/skills.json'))['skills']
STATIONS = json.load(open(ROOT / 'stations/registry/stations.json'))
SIMS = json.load(open(ROOT / 'sims/registry/sims.json'))
TRAINING = json.load(open(ROOT / 'training/registry/training.json'))
SCHOOLS = json.load(open(ROOT / 'schools/registry/schools.json'))
FINISHES = json.load(open(ROOT / 'surfaces/registry/finishes.json'))
ADVISORS = json.load(open(ROOT / 'agents/registry/advisors.json'))
CREWS = json.load(open(ROOT / 'agents/registry/crews.json'))
CRIBS = json.load(open(ROOT / 'tools/registry/toolcribs.json'))
LABELS = json.load(open(ROOT / 'labels/registry/labels.json'))
CAMPUSES = json.load(open(ROOT / 'unions/registry/campuses.json'))['campuses']

# The room a strand requires, and the label on its door, are `web/interiors.py`'s
# fact - the module every hall interior in this bundle is laid out from. It is
# imported rather than retyped, so a room renamed there renames itself here.
sys.path.insert(0, str(ROOT / 'web'))
from interiors import ROOMS as INTERIOR_ROOMS  # noqa: E402

ROOM_LABEL = {strand: label for strand, label, _w, _h, _p in INTERIOR_ROOMS}
ROOM_PURPOSE = {strand: purpose for strand, _l, _w, _h, purpose in INTERIOR_ROOMS}
assert len(ROOM_LABEL) == 11, 'the interior programme is 11 rooms, one per strand'

# The page this pack is written to be consumed by. Read, never written.
PAGE_SRC = (ROOT / 'web/build_3d.py').read_text()

HALL_NAME = {h['slug']: h['name'] for h in HALLS}
HALL_FOCUS = {h['slug']: h['focus'] for h in HALLS}
HALL_STRANDS = {}
SKILL_IDS = set()
for s in SKILLS:
    SKILL_IDS.add(s['skill_id'])
    HALL_STRANDS.setdefault(s['union'], set()).add(s['strand'])

HALL_CAMPUS = {}
for ckey, c in CAMPUSES.items():
    for slug in c['halls']:
        assert slug not in HALL_CAMPUS, f'{slug} is sited on two campuses'
        HALL_CAMPUS[slug] = ckey

STATION_BY_ID = {s['station_id']: s for s in STATIONS['stations']}
TIER_RANK = {'fundamentals': 0, 'applied': 1, 'mastery': 2}
SCHOOL_STAGES = [s['stage'] for s in SCHOOLS['model']['stages']]

# --------------------------------------------------------- the step kinds ---
# Eight kinds, closed. `records` is the training/ episode kind the step
# writes - or None, which is a decision stated out loud rather than a gap.
# `stage` is the flipped-classroom stage the step belongs to, and it is a
# property of the kind so that no single lesson can quietly reclassify one.
NOTHING_RECORDED = None

STEP_KINDS = {
    'walk': {
        'act': 'walk to a room of this hall',
        'records': NOTHING_RECORDED,
        'stage': 'class',
        'reads': 'web/interiors.py',
        'why_no_episode': 'arriving somewhere is not an achievement, and a bundle that logged footsteps would be counting attendance while claiming to teach',
    },
    'placard': {
        'act': 'read the door placard of a room and take on what it requires',
        'records': NOTHING_RECORDED,
        'stage': 'class',
        'reads': 'surfaces/registry/finishes.json',
        'why_no_episode': 'the placard states the room condition record; reading a record changes nothing and is nobody\'s score',
    },
    'station': {
        'act': 'take a training station at its bench',
        'records': NOTHING_RECORDED,
        'stage': 'class',
        'reads': 'stations/registry/stations.json',
        'why_no_episode': 'a station mark lands in the device-local progress record the halls already keep; the training log holds simulator, advisor, crew and walkaround episodes and this pack adds no fifth kind to it',
    },
    'crib': {
        'act': 'run the district crib check at the pegboard',
        'records': NOTHING_RECORDED,
        'stage': 'class',
        'reads': 'tools/registry/toolcribs.json',
        'why_no_episode': 'the crib check is graded deterministically against the crib record and kept with the progress record, not as a training episode',
    },
    'walkaround': {
        'act': 'walk one pre-shift point of a seat and mark it',
        'records': 'walkaround',
        'stage': 'floor',
        'reads': 'sims/registry/sims.json',
        'why_no_episode': None,
    },
    'sim': {
        'act': 'run one seat on the scenario its campus owns',
        'records': 'sim',
        'stage': 'floor',
        'reads': 'sims/registry/sims.json',
        'why_no_episode': None,
    },
    'advisor': {
        'act': 'ask the advisor who stands in this room one of its fixed topics',
        'records': 'advisor',
        'stage': 'class',
        'reads': 'agents/registry/advisors.json',
        'why_no_episode': None,
    },
    'crew': {
        'act': 'ask one role of the standing crew one of its fixed topics while the seat runs',
        'records': 'crew',
        'stage': 'floor',
        'reads': 'agents/registry/crews.json',
        'why_no_episode': None,
    },
}

# The three places in a hall that are not one of the eleven strand rooms.
# Named here because a step has to be able to stand in them, and each one
# is the post of an advisor the agents registry already places there.
OFF_ROOM_PLACES = {
    'yard': {'short': 'hall yard',
             'what': 'the yard the seat is entered from and the crew musters in'},
    'door': {'short': 'hall door',
             'what': 'the threshold the orientation figure stands at'},
    'green': {'short': 'campus green',
              'what': 'the open ground outside the hall'},
}

# ------------------------------------------------------------ the lessons ---
# Each entry: id, hall, strand (the room it stands in), tier, title, one
# plain `why` sentence, the ordered steps, and what finishing it does NOT
# mean. Steps are (kind, *ids, note) - the ids resolve below or the build
# stops and names the one that did not.
LESSONS_SRC = [
 {
  'id': 'riggers-first-card',
  'hall': 'riggers', 'strand': 'coordination', 'tier': 'fundamentals',
  'title': 'Call the first lift before anybody touches the hook',
  'why': 'A lift goes wrong in the talking long before it goes wrong in the air, so the first thing worth practising is the conversation.',
  'limits': 'Finishing this does not make you a signalperson and does not qualify you to direct a lift; it is one scripted exchange and one schematic seat, and no hall, employer or authority has signed anything on the strength of it.',
  'steps': [
   ('walk', 'coordination', 'Start where the shift starts, at the table the plan gets read out at rather than the place the load hangs.'),
   ('advisor', 'foreman', 'walk', 'Ask before you walk anything, because the answer tells you what the walk is for.'),
   ('walkaround', 'rigging-signals', 'sightline', 'If you cannot see the load and the hook at once, the call you are about to make is guesswork wearing a radio.'),
   ('sim', 'rigging-signals', 'Now make the calls in order, and notice which one you wanted to skip.'),
  ],
 },
 {
  'id': 'riggers-carry-under-control',
  'hall': 'riggers', 'strand': 'machines', 'tier': 'applied',
  'title': 'Carry a load that is not fighting you',
  'why': 'Swing is not weather, it is the sum of the inputs you already made, and the seat is where that becomes obvious.',
  'limits': 'Finishing this is not crane seat time and counts toward no operator qualification; the physics here is schematic, the assessment gate still demands an unaided verification run, and nothing recorded here is read by a grader.',
  'steps': [
   ('walk', 'machines', 'The plant is checked out to a training area here, which is the only reason you are allowed near it.'),
   ('walkaround', 'crane-lift', 'rope', 'Broken wires and a latch that will not close are not run out to the end of a shift.'),
   ('crew', 'crane-lift-crew', 'rigger', 'weight', 'Ask the one person whose whole job is knowing what the thing actually weighs.'),
   ('sim', 'crane-lift', 'Move one thing at a time and let it settle; the gauge is telling you the truth even when the seat feels fine.'),
   ('advisor', 'operator', 'rubric', 'Finish by asking what you were being measured on, rather than assuming you know.'),
  ],
 },
 {
  'id': 'crane-ops-read-the-chart',
  'hall': 'crane-ops', 'strand': 'machines', 'tier': 'applied',
  'title': 'Refuse the pick the chart refuses',
  'why': 'The hardest thing on a chart is not the arithmetic, it is saying no out loud once the arithmetic has answered.',
  'limits': 'Finishing this certifies nothing and permits nothing; a real chart belongs to a real machine in a real configuration, and this seat is a teaching aid that has never lifted anything.',
  'steps': [
   ('walk', 'machines', 'Stand where the plant lives, because a chart read at a desk is a different habit from a chart read at the machine.'),
   ('walkaround', 'load-chart', 'chart', 'The chart on the board has to be the one for the machine in front of you, in the configuration it is actually in.'),
   ('sim', 'load-chart', 'Work the list and let one of them be a no; that is the judgment being taught.'),
   ('advisor', 'operator', 'task', 'Ask what the seat is for before you decide how you did at it.'),
  ],
 },
 {
  'id': 'ironworkers-plan-out-loud',
  'hall': 'ironworkers', 'strand': 'coordination', 'tier': 'applied',
  'title': 'Say the plan out loud, then change it properly',
  'why': 'A good plan that quietly stopped describing the work is more dangerous than an obviously bad one.',
  'limits': 'Finishing this does not make you a lift director and is not a lift plan anybody can work to; it is a scripted exchange about how planning fails, not an authority to plan.',
  'steps': [
   ('walk', 'coordination', 'Hand-offs happen here, which is why the exchange is staged here and not at the hook.'),
   ('walkaround', 'crane-lift', 'limits', 'A device that stops the machine is only a device until somebody has proved it still stops the machine.'),
   ('crew', 'crane-lift-crew', 'lift-director', 'plan', 'Ask what has to be in one, then compare it with what usually gets said.'),
   ('advisor', 'foreman', 'handoff', 'The hand-off is where the plan either survives or quietly dies.'),
  ],
 },
 {
  'id': 'millwrights-shop-move',
  'hall': 'millwrights', 'strand': 'machines', 'tier': 'applied',
  'title': 'Move something precise across a shop floor',
  'why': 'Precision work is usually lost in the handling rather than at the machine, and the shop move is where it gets lost.',
  'limits': 'Finishing this is not overhead crane authorisation and no employer grants one from here; the seat is schematic, the loads are not real and no alignment has been proved by anything you did.',
  'steps': [
   ('walk', 'machines', 'The bay is where plant is checked out to a training area, so this is where the move starts.'),
   ('placard', 'machines', 'Read what the bay is held to before the load moves; the sign at the door is the room condition record.'),
   ('walkaround', 'overhead-crane', 'limit', 'A stop that has never been tested is a story about a stop.'),
   ('sim', 'overhead-crane', 'Sway is the whole exercise; the placement number is just where the sway finally showed up.'),
   ('advisor', 'inspector', 'measures', 'Ask what acceptance actually means here before you decide you met it.'),
  ],
 },
 {
  'id': 'welders-the-watch',
  'hall': 'welders', 'strand': 'safety', 'tier': 'applied',
  'title': 'Stand the watch that outlasts the arc',
  'why': 'Most hot-work fires start after the welding stops, which is exactly when everybody wants to go home.',
  'limits': 'Finishing this is not a hot work permit, not fire watch training and not a welding qualification; it teaches the shape of the duty, and your jurisdiction owns the rules that make it binding.',
  'steps': [
   ('walk', 'safety', 'Gowning, permits and the atmospheric check all live in one room, which is the point of the room.'),
   ('placard', 'safety', 'Take on what the sign says before you cross the line, not after somebody notices.'),
   ('advisor', 'safety-steward', 'hazard', 'Ask what is actually in force in here rather than assuming it is the usual.'),
   ('walkaround', 'weld-bead', 'firewatch', 'The last check before the arc is the one that decides how the next hour ends.'),
   ('crew', 'hot-work-crew', 'fire-watch', 'watching', 'Ask the person whose entire job is staying when everyone else leaves.'),
  ],
 },
 {
  'id': 'boilermakers-get-them-out',
  'hall': 'boilermakers', 'strand': 'procedure', 'tier': 'applied',
  'title': 'Put somebody inside a vessel and get them back out',
  'why': 'The measure of a confined space job is not the weld, it is that the same person walked out.',
  'limits': 'Finishing this is not confined space entry training, not an entry permit and not a rescue qualification; it is a scripted exchange about roles, and nobody here may authorise an entry.',
  'steps': [
   ('walk', 'procedure', 'This is the floor the trade is actually learned on, so the rehearsal belongs here.'),
   ('placard', 'procedure', 'Read what the floor is held to before anybody goes near the hole; the door sign binds the entrant too.'),
   ('walkaround', 'weld-bead', 'gas', 'What is in the air is the first question inside a vessel and the last one too.'),
   ('crew', 'confined-space-crew', 'attendant', 'never', 'Ask what the person at the hole may never do, because that is the whole role.'),
   ('advisor', 'safety-steward', 'refuse', 'Practising the refusal is the part people skip, so practise it here where it costs nothing.'),
  ],
 },
 {
  'id': 'operating-eng-locate-first',
  'hall': 'operating-eng', 'strand': 'layout', 'tier': 'applied',
  'title': 'Prove what is under the ground before the bucket moves',
  'why': 'Marks on the ground are somebody else prediction, and the bucket does not care whose it was.',
  'limits': 'Finishing this is not excavator seat time, not a utility locating qualification and not competent person status; the ground here is schematic and no real service has ever been proved by it.',
  'steps': [
   ('walk', 'layout', 'Setting out and control points live here, and so does the habit of trusting a mark only as far as it was proved.'),
   ('advisor', 'layout-hand', 'control', 'Ask what the control actually is before you work off something painted near it.'),
   ('walkaround', 'excavator-trench', 'edge', 'What the edge will hold is a question answered before the machine stands on it.'),
   ('crew', 'trench-crew', 'locator', 'marks', 'Ask how a mark gets made, then ask what it is worth once it has been made.'),
   ('sim', 'excavator-trench', 'Cut to grade over something live, and notice the pace that keeps you honest.'),
  ],
 },
 {
  'id': 'demolition-stand-back',
  'hall': 'demolition', 'strand': 'safety', 'tier': 'applied',
  'title': 'Know where not to stand',
  'why': 'On a takedown the dangerous ground is usually the ground somebody is standing on out of habit.',
  'limits': 'Finishing this is not demolition training and confers no authority over a structure; nothing here assesses a building, and no sequence you ran is a takedown plan.',
  'steps': [
   ('walk', 'safety', 'Induction is where the day starts and where the refusal gets rehearsed.'),
   ('placard', 'safety', 'The sign at the door is the record, not a suggestion posted near one.'),
   ('walkaround', 'excavator-trench', 'tracks', 'A machine that cannot hold its ground is the hazard, whatever it is being asked to do.'),
   ('advisor', 'safety-steward', 'refuse', 'Ask whether you can stop the work, and hear the answer as a duty rather than a favour.'),
  ],
 },
 {
  'id': 'scaffold-read-the-tag',
  'hall': 'scaffold', 'strand': 'safety', 'tier': 'applied',
  'title': 'Believe the tag or believe nothing',
  'why': 'A tag is the only thing standing between a half-built bay and somebody climbing it in good faith.',
  'limits': 'Finishing this is not competent person status and is not a scaffold inspection; a tag in this bundle is a teaching prop, and no structure anywhere has been released by it.',
  'steps': [
   ('walk', 'safety', 'Start at induction, because the tag is a safety instrument before it is a piece of paperwork.'),
   ('placard', 'safety', 'Read the line at the door before the bench; the room record is the first tag you believe or do not.'),
   ('station', 'st003', 'Work the bench first; the checklist is the shape of the habit.'),
   ('walkaround', 'scaffold-bay', 'tag', 'Read what it says and what it does not say, which is usually the more useful half.'),
   ('advisor', 'safety-steward', 'ppe', 'Ask what this room requires of you, and note that the task adds to it rather than replacing it.'),
  ],
 },
 {
  'id': 'scaffold-build-in-order',
  'hall': 'scaffold', 'strand': 'materials', 'tier': 'applied',
  'title': 'Build the bay in the order that keeps you off the ground',
  'why': 'The order is not a preference; it is what decides whether the people building it are ever unprotected.',
  'limits': 'Finishing this erects nothing and inspects nothing; the bay is schematic, the sequence is unverified general practice, and no jurisdiction has reviewed a line of it.',
  'steps': [
   ('walk', 'materials', 'Stock, offcuts and consumables live here, and a bay is built from what is staged before it is built from skill.'),
   ('placard', 'materials', 'Read what the store is held to; a material room has conditions like any other.'),
   ('crew', 'scaffold-crew', 'erector', 'procedure', 'Ask for the order, then ask why that order and not a faster one.'),
   ('walkaround', 'scaffold-bay', 'planks', 'A platform is only a platform where it is complete and secured.'),
   ('sim', 'scaffold-bay', 'Run it and let the sequence score tell you where you took the shortcut.'),
  ],
 },
 {
  'id': 'waterproofers-flash-it-right',
  'hall': 'waterproofers', 'strand': 'procedure', 'tier': 'applied',
  'title': 'Give the water somewhere to go',
  'why': 'Water is not kept out of a building, it is led out of it, and the detail is where that either happens or does not.',
  'limits': 'Finishing this is not a waterproofing qualification and is not a warranty on any detail; it is unverified general practice and the manufacturer instruction for a real product always wins.',
  'steps': [
   ('walk', 'procedure', 'The practice floor is where the detail gets built badly a few times first.'),
   ('station', 'st019', 'Work the bench and read the doctrine line twice; it is the compressed version of the lesson.'),
   ('walkaround', 'scaffold-bay', 'sills', 'Everything above a bad base is a story about a bad base.'),
   ('advisor', 'inspector', 'measures', 'Ask what acceptance means here, because a detail that passes the eye can still fail the criteria.'),
  ],
 },
 {
  'id': 'bricklayers-gear-that-stays-on',
  'hall': 'bricklayers', 'strand': 'safety', 'tier': 'fundamentals',
  'title': 'Wear it for the last ten minutes too',
  'why': 'What fails is almost never the absence of gear, it is gear in the wrong size, past its life, or taken off early.',
  'limits': 'Finishing this fits nothing to your face and qualifies nobody; a seal check in a browser is a reminder of a habit, not a fit test, and a real respirator programme is a different thing entirely.',
  'steps': [
   ('walk', 'safety', 'The first room of any hall is the one that decides whether you are allowed into the others.'),
   ('placard', 'safety', 'Read the line at the door and add what the task needs on top of it.'),
   ('station', 'st000', 'Work through the bench, including the quiz you think you already know.'),
   ('advisor', 'safety-steward', 'ppe', 'Ask the room what it requires rather than guessing from what other people are wearing.'),
  ],
 },
 {
  'id': 'bricklayers-grout-the-lift',
  'hall': 'bricklayers', 'strand': 'procedure', 'tier': 'applied',
  'title': 'Pour a lift you cannot see inside',
  'why': 'Reinforced work is judged entirely on what happened in a cavity nobody will ever look into again.',
  'limits': 'Finishing this is not a masonry qualification and no wall has been built; the technique here is unverified general practice awaiting review by journey-level practitioners from this hall.',
  'steps': [
   ('walk', 'procedure', 'Practice bays are where the mistake is cheap, which is the only reason to make it here.'),
   ('placard', 'procedure', 'Read what the floor is held to before the first course goes down; the sign is the record, not a suggestion.'),
   ('station', 'st010', 'Work the bench; the checklist is the order the work actually has to happen in.'),
   ('advisor', 'inspector', 'cert', 'Ask the blunt question straight out, because the honest answer is shorter than people hope.'),
  ],
 },
 {
  'id': 'cement-masons-mind-the-weather',
  'hall': 'cement-masons', 'strand': 'materials', 'tier': 'applied',
  'title': 'Protect a pour from the day it was poured in',
  'why': 'Concrete does not fail on the day it is placed, it fails on the day it was allowed to dry wrong.',
  'limits': 'Finishing this places no concrete and tests no cylinder; nothing here is a mix design, a cure schedule or an approval to use one.',
  'steps': [
   ('walk', 'materials', 'The store is where the protection gets staged, and unstaged protection does not get used.'),
   ('placard', 'materials', 'Read the room record; conditions matter more here than almost anywhere.'),
   ('station', 'st008', 'Work the bench, then read the doctrine line as the thing to remember on a hot afternoon.'),
   ('crib', 'The pegboard check is five picks against the crib record, and it is deliberately unforgiving about near-misses.'),
   ('walk', 'inspection', 'Take the pour to where it gets accepted, because curing is judged by somebody who was not there for it.'),
   ('advisor', 'inspector', 'cert', 'Ask the blunt question about what a pass here is worth, and let the answer be the small one it is.'),
  ],
 },
 {
  'id': 'stone-carvers-hang-it-safely',
  'hall': 'stone-carvers', 'strand': 'materials', 'tier': 'applied',
  'title': 'Hang stone on something that will hold it',
  'why': 'Anchored stone is only as good as the thing behind it, which is the part nobody photographs.',
  'limits': 'Finishing this specifies no anchor and approves no substrate; an anchor on a real building is an engineered choice and nothing here may stand in for one.',
  'steps': [
   ('walk', 'materials', 'Stone gets staged before it gets set, and how it is staged decides how it is handled.'),
   ('station', 'st011', 'Work the bench and pay attention to the fixing rather than the face.'),
   ('advisor', 'inspector', 'cert', 'Ask what a pass in this building is actually worth outside it.'),
  ],
 },
 {
  'id': 'tilesetters-start-underneath',
  'hall': 'tilesetters', 'strand': 'procedure', 'tier': 'fundamentals',
  'title': 'Fix the substrate you are about to hide',
  'why': 'Every tile failure worth arguing about started under the tile, before anybody had a trowel out.',
  'limits': 'Finishing this sets no tile and approves no substrate; the sequence is unverified general practice and the system manufacturer instruction governs a real installation.',
  'steps': [
   ('walk', 'procedure', 'The practice floor is where you find out that flat is a measurement and not an opinion.'),
   ('station', 'st022', 'Work the bench and treat the preparation steps as the lesson rather than the preamble.'),
   ('crib', 'Five picks against the district record; the point is naming the tool, not recognising a picture of it.'),
   ('advisor', 'inspector', 'cert', 'Ask whether finishing here counts for anything elsewhere, and hear the answer properly.'),
  ],
 },
 {
  'id': 'lathers-frame-for-the-next-trade',
  'hall': 'lathers', 'strand': 'procedure', 'tier': 'fundamentals',
  'title': 'Frame it for whoever comes next',
  'why': 'Framing is judged by the trade that follows you, not by how quickly you finished it.',
  'limits': 'Finishing this frames nothing and is no structural approval; backing, spacing and fixings on a real job come from a drawing and an engineer, never from a lesson.',
  'steps': [
   ('walk', 'procedure', 'The practice floor is where the spacing habit gets built, one wrong stud at a time.'),
   ('station', 'st023', 'Work the bench; the checklist is mostly about what the next trade will need from you.'),
   ('crib', 'Run the pegboard check and notice which tools you could name only by sight.'),
   ('advisor', 'crib-keeper', 'tools', 'Ask what the crib actually issues, because that is the real kit list.'),
  ],
 },
 {
  'id': 'restore-point-the-joint',
  'hall': 'masonry-restore', 'strand': 'tools', 'tier': 'fundamentals',
  'title': 'Cut a joint without wrecking the brick',
  'why': 'On old work the mortar is meant to be the sacrificial part, and the tool you choose decides whether it stays that way.',
  'limits': 'Finishing this repoints nothing and specifies no mortar; matching a historic mix is analysis work, and nothing here is that analysis or a substitute for it.',
  'steps': [
   ('walk', 'tools', 'Issue, calibration and return all happen in one place, and the discipline is the lesson.'),
   ('station', 'st017', 'Work the bench and treat joint finish as an outcome of the tool rather than a decoration.'),
   ('advisor', 'crib-keeper', 'drill', 'Ask how the check is scored before you run it, so you are not guessing at the rules.'),
   ('crib', 'Five picks, graded against the crib record, with the option order fixed by arithmetic rather than chance.'),
  ],
 },
 {
  'id': 'restore-write-it-down',
  'hall': 'masonry-restore', 'strand': 'documentation', 'tier': 'applied',
  'title': 'Leave a record the next century can read',
  'why': 'On heritage work the record of what you did is part of the fabric, and an undocumented repair is close to a lost one.',
  'limits': 'Finishing this documents no building and satisfies no preservation authority; the standards named on a real job come from that jurisdiction and this bundle speaks for none of them.',
  'steps': [
   ('walk', 'documentation', 'Permits, certificates and as-builts live together for a reason.'),
   ('station', 'st016', 'Work the bench and notice how much of the standard is about restraint rather than technique.'),
   ('advisor', 'records-clerk', 'where', 'Ask where what you did is actually kept, and who can read it later.'),
  ],
 },
 {
  'id': 'refractory-dry-it-slowly',
  'hall': 'refractory', 'strand': 'procedure', 'tier': 'applied',
  'title': 'Take the lining up to heat slowly enough',
  'why': 'A lining that is rushed to temperature destroys itself from the inside, invisibly, on the first day.',
  'limits': 'Finishing this lines no furnace and is no dryout schedule; a real schedule belongs to the refractory supplier and the vessel, and nothing here replaces it.',
  'steps': [
   ('walk', 'procedure', 'The practice floor is where the mock-up stands, which is the only place to learn this cheaply.'),
   ('placard', 'procedure', 'Read what the floor is held to before the mock-up is lit; heat changes what the room requires of you.'),
   ('station', 'st015', 'Work the bench and read the doctrine line as the thing you will be tempted to ignore.'),
   ('crib', 'Five picks against the district record; industry kit is unforgiving about improvisation.'),
   ('advisor', 'inspector', 'cert', 'Ask what a pass here is worth before you let it make you confident.'),
  ],
 },
 {
  'id': 'painters-contain-it',
  'hall': 'painters', 'strand': 'safety', 'tier': 'applied',
  'title': 'Catch what you wash off',
  'why': 'What comes off a surface has to go somewhere, and the plan for that is either made beforehand or not at all.',
  'limits': 'Finishing this is no environmental permit and no containment design; what may be released, and where, is a jurisdiction matter and this bundle names no jurisdiction.',
  'steps': [
   ('walk', 'safety', 'Induction is where containment stops being somebody else problem.'),
   ('placard', 'safety', 'Read what is in force in the room before you argue about what the job needs.'),
   ('walkaround', 'pressure-washer', 'containment', 'Where the water goes is a decision, and an undecided one is still a decision.'),
   ('advisor', 'safety-steward', 'hazard', 'Ask what the hazard in this room actually is rather than the one you expected.'),
   ('sim', 'pressure-washer', 'Clean it without damaging it, and watch what the containment number does while you hurry.'),
  ],
 },
 {
  'id': 'painters-lay-the-coat',
  'hall': 'painters', 'strand': 'procedure', 'tier': 'applied',
  'title': 'Lay a coat that is actually there',
  'why': 'A finish fails at the thin places nobody saw, and spraying faster makes more of them rather than fewer.',
  'limits': 'Finishing this coats nothing and is no coating specification; film thickness, recoat windows and compatibility on a real job come from the product data sheet.',
  'steps': [
   ('walk', 'procedure', 'The practice floor is where overlap becomes a habit instead of an intention.'),
   ('placard', 'procedure', 'Read what the floor is held to before the gun is even primed; atomised coating changes what the room requires.'),
   ('walkaround', 'airless-sprayer', 'respirator', 'Atomised coating is a respiratory problem before it is a finish problem.'),
   ('sim', 'airless-sprayer', 'Watch the thin spots and the runs argue with each other; the middle of that argument is the technique.'),
  ],
 },
 {
  'id': 'hazmat-wash-and-decon',
  'hall': 'hazmat', 'strand': 'safety', 'tier': 'applied',
  'title': 'Come out cleaner than what you washed',
  'why': 'The end of a decontamination job is the part where people get exposed, because the hard work is already finished.',
  'limits': 'Finishing this is no abatement or decontamination qualification and clears no site; clearance is a measured, sampled process and nothing here samples anything.',
  'steps': [
   ('walk', 'safety', 'Gowning and the atmospheric check happen here, in that order, for a reason.'),
   ('placard', 'safety', 'Read the room record, then read it again for what it does not cover.'),
   ('walkaround', 'pressure-washer', 'ppe', 'What the water can do to a surface it can also do to a hand.'),
   ('advisor', 'safety-steward', 'env', 'Ask what light, air and noise this room is held to, because those numbers are the room promise.'),
   ('sim', 'pressure-washer', 'Run the regional case and notice how much of the score is about what you caught rather than what you cleaned.'),
  ],
 },
 {
  'id': 'electricians-clip-in-first',
  'hall': 'electricians', 'strand': 'machines', 'tier': 'applied',
  'title': 'Clip in before the basket moves',
  'why': 'Nearly everyone who falls from a basket was attached to something for most of the shift.',
  'limits': 'Finishing this is not aerial lift training and is no familiarisation on any machine; a real lift requires machine-specific training and this seat is schematic.',
  'steps': [
   ('walk', 'machines', 'The bay is where a machine gets checked out to a training area rather than borrowed.'),
   ('walkaround', 'boom-lift', 'harness', 'An anchor you did not look at is an anchor you are hoping about.'),
   ('crew', 'aerial-lift-crew', 'basket-operator', 'clip', 'Ask when the clip goes on, and notice the answer is earlier than you thought.'),
   ('sim', 'boom-lift', 'Work the points in order and let the envelope warnings teach you the shape of the machine.'),
  ],
 },
 {
  'id': 'glaziers-watch-the-line',
  'hall': 'glaziers', 'strand': 'inspection', 'tier': 'applied',
  'title': 'Keep the boom out of the zone',
  'why': 'Overhead lines do not need to be touched to kill somebody, which is why the observer job exists at all.',
  'limits': 'Finishing this is no qualified person status and sets no approach distance; approach limits are set by the utility and the jurisdiction, and this bundle sets none.',
  'steps': [
   ('walk', 'inspection', 'Acceptance criteria and sign-off live here, and an observer is an acceptance job.'),
   ('placard', 'inspection', 'Read the room record before you start deciding what good looks like.'),
   ('walkaround', 'boom-lift', 'overhead', 'Look up before the machine does, because it will not.'),
   ('crew', 'aerial-lift-crew', 'line-observer', 'zone', 'Ask what the zone is and who is allowed to say it has moved.'),
  ],
 },
 {
  'id': 'site-safety-make-it-normal',
  'hall': 'site-safety', 'strand': 'leadership', 'tier': 'applied',
  'title': 'Make stopping the job an ordinary thing to do',
  'why': 'A culture is measured by how a stop-work call is received, not by how the poster is worded.',
  'limits': 'Finishing this is no safety qualification and confers no authority on a site; the only authority a stop-work call has is the one the employer and the jurisdiction actually give it.',
  'steps': [
   ('walk', 'leadership', 'Level tests and the instructor track live here, which is where culture gets taught or not.'),
   ('station', 'st013', 'Work the bench and treat the doctrine line as the sentence you will have to say in front of people.'),
   ('advisor', 'foreman', 'gate', 'Ask what a gate actually is here, and what it refuses to count.'),
  ],
 },
 {
  'id': 'surveyors-trust-the-control',
  'hall': 'surveyors', 'strand': 'layout', 'tier': 'fundamentals',
  'title': 'Work from control, not from something near it',
  'why': 'Every layout error that survives to the end of a job started by trusting a mark that was never control.',
  'limits': 'Finishing this establishes no control network and checks no instrument; a real network is observed, adjusted and recorded, and nothing here does any of those.',
  'steps': [
   ('walk', 'layout', 'Setting out lives here, which makes this the right room to be pedantic in.'),
   ('placard', 'layout', 'Read the room record; light matters to this work more than people expect.'),
   ('advisor', 'layout-hand', 'control', 'Ask what control is, then ask how you would know if it had moved.'),
   ('advisor', 'layout-hand', 'check', 'Ask what the check is, because a layout without one is a guess with a decimal point.'),
   ('crib', 'Five picks against the district record, which is a fair test of whether you know the kit by name.'),
  ],
 },
 {
  'id': 'line-workers-find-the-fault',
  'hall': 'line-workers', 'strand': 'troubleshooting', 'tier': 'applied',
  'title': 'Find the fault instead of replacing things',
  'why': 'Swapping parts until it works is not diagnosis, it is spending somebody else money in a hopeful order.',
  'limits': 'Finishing this diagnoses nothing and authorises no switching; live distribution work is governed by the utility own procedures and this bundle holds none of them.',
  'steps': [
   ('walk', 'troubleshooting', 'Fault-finding against live rigs has its own room because it needs a different head to the practice floor.'),
   ('placard', 'troubleshooting', 'Read what the room is held to before you start pulling at anything.'),
   ('crib', 'Five picks against the district record; diagnosis starts with knowing what you are holding.'),
   ('walk', 'inspection', 'Walk the finding to where acceptance is decided, because a diagnosis nobody accepts is a rumour.'),
   ('advisor', 'inspector', 'score', 'Ask what is scored and what is not, and listen for how narrow the answer is.'),
  ],
 },
 {
  'id': 'hvacr-prove-the-sequence',
  'hall': 'hvacr', 'strand': 'inspection', 'tier': 'applied',
  'title': 'Prove the system does what the sequence says',
  'why': 'Commissioning is the moment somebody finds out whether the building does what the drawings promised.',
  'limits': 'Finishing this commissions nothing and signs off nothing; a real commissioning record is witnessed and measured, and no measurement here left this browser.',
  'steps': [
   ('walk', 'inspection', 'Acceptance criteria live here, and commissioning is acceptance with instruments attached.'),
   ('placard', 'inspection', 'Read the room record, including the part about noise.'),
   ('advisor', 'inspector', 'score', 'Ask whether a good explanation can stand in for a measurement, and note how short the answer is.'),
   ('crib', 'Five picks against the district record; the kit is half the argument in this trade.'),
  ],
 },
 {
  'id': 'fiber-splicers-keep-the-trace',
  'hall': 'fiber-splicers', 'strand': 'documentation', 'tier': 'fundamentals',
  'title': 'Keep the trace that proves the splice',
  'why': 'A splice nobody recorded is a splice somebody will have to find again in the dark.',
  'limits': 'Finishing this splices nothing and certifies no link; a real loss budget is measured against a standard and this bundle names and speaks for no standard.',
  'steps': [
   ('walk', 'documentation', 'As-builts live here, and an as-built is the only proof a buried route ever gets.'),
   ('advisor', 'records-clerk', 'where', 'Ask where the record goes and who is able to read it after you have gone.'),
   ('advisor', 'records-clerk', 'cert', 'Ask plainly whether anything here is a certificate, and take the answer seriously.'),
  ],
 },
 {
  'id': 'carpenters-return-it-the-same',
  'hall': 'carpenters', 'strand': 'tools', 'tier': 'fundamentals',
  'title': 'Return it in the state you would want to find it',
  'why': 'Crib discipline is not tidiness, it is the next person being able to start work without a search.',
  'limits': 'Finishing this is no tool competency and is no inventory of any real toolroom; no manufacturer or brand is named here and none is endorsed.',
  'steps': [
   ('walk', 'tools', 'Issue, calibration and return are one loop and this room is the whole loop.'),
   ('placard', 'tools', 'Read what the room is held to; calibration cares about conditions.'),
   ('advisor', 'crib-keeper', 'tools', 'Ask what is actually issued here, which is a shorter list than most people expect.'),
   ('crib', 'Five picks against the district record, scored deterministically and with nothing narrative able to change it.'),
  ],
 },
 # -- the seat-bound halls. sims/registry/sims.json#hall_bindings binds a
 # -- seat to a hall; a hall with a seat and no lesson had a floor and no
 # -- reason to walk onto it. One lesson per such hall, authored like the
 # -- rest, and the build below refuses a seat-bound hall with none.
 {
  'id': 'steel-erectors-land-it-on-the-bolts',
  'hall': 'steel-erectors', 'strand': 'procedure', 'tier': 'applied',
  'title': 'Land the piece where the bolts can go in',
  'why': 'A beam that arrives fast and slightly wrong costs more than one that arrives slowly and lands on its holes.',
  'limits': 'Finishing this is not connection training, not a rigging qualification and not a lift plan; the steel here is schematic, no bolt has been torqued, and no employer or hall has signed anything on the strength of it.',
  'steps': [
   ('walk', 'procedure', 'The floor is where the piece is landed badly a few times before it is landed once on its holes.'),
   ('walkaround', 'crane-lift', 'limits', 'A trip that has never been tested is a promise, and the steel does not take promises.'),
   ('crew', 'crane-lift-crew', 'signalperson', 'procedure', 'Ask for the sequence out loud, because the sequence is the part that gets improvised under a deadline.'),
   ('sim', 'crane-lift', 'Bring it in slowly enough that the last foot is a decision rather than an event.'),
   ('advisor', 'foreman', 'handoff', 'Ask what a good hand-off looks like, because the next connection starts with this one.'),
  ],
 },
 {
  'id': 'port-crane-read-the-rope',
  'hall': 'port-crane', 'strand': 'machines', 'tier': 'applied',
  'title': 'Read the rope before the box goes up',
  'why': 'A quay crane lives or dies on its ropes and the person who looked at them last, and the seat is where looking becomes a habit.',
  'limits': 'Finishing this is not crane technician standing and not a rope inspection anybody may act on; the machine here is schematic, the wire is drawn rather than run, and nothing recorded is read by any authority.',
  'steps': [
   ('walk', 'machines', 'Plant is checked out to a training area here, so the first look at the machine is taken in this bay.'),
   ('walkaround', 'overhead-crane', 'rope', 'Broken wires are counted, not glanced at, and a kink is a reason to stop rather than a note.'),
   ('walkaround', 'crane-lift', 'rope', 'The second machine gets the same look as the first; the habit is the point, not the machine.'),
   ('crew', 'crane-lift-crew', 'crane-operator', 'gauges', 'Ask what the dash is showing, because a number you cannot explain is a number you are ignoring.'),
   ('sim', 'crane-lift', 'Run the terminal case and let the swing tell you what your inputs added up to.'),
  ],
 },
 {
  'id': 'decking-walk-the-path-first',
  'hall': 'decking', 'strand': 'procedure', 'tier': 'applied',
  'title': 'Walk where the bundle will fly before it flies',
  'why': 'A deck bundle crosses a floor other people are standing on, and the walk is the only time that floor is looked at properly.',
  'limits': 'Finishing this is not signalperson standing and lifts no bundle; the floor is schematic, the call is scripted, and no hall, employer or authority has reviewed or signed a line of it.',
  'steps': [
   ('walk', 'procedure', 'The floor is where the bundle lands, so the floor is where the lesson starts and ends.'),
   ('placard', 'procedure', 'Read what this floor is held to before you decide what you are wearing is enough for it.'),
   ('walkaround', 'rigging-signals', 'path', 'Walk it end to end yourself; a path somebody described to you is a path nobody walked.'),
   ('sim', 'rigging-signals', 'Make the calls in order and notice the one you wanted to make early.'),
   ('advisor', 'foreman', 'walk', 'Ask what gets walked before a start, and compare it with what you just walked.'),
  ],
 },
 {
  'id': 'tank-erectors-isolate-before-testing',
  'hall': 'tank-erectors', 'strand': 'safety', 'tier': 'applied',
  'title': 'Isolate the shell before anybody tests the air',
  'why': 'A tank is a confined space with a weld in it, and the order of the safety steps is the whole difference between a shift and an incident.',
  'limits': 'Finishing this is not confined space entry training, not a hot work permit and not a welding qualification; nobody here may authorise an entry, and the shell you worked on has never held anything.',
  'steps': [
   ('walk', 'safety', 'Gowning, the atmospheric check and the permit board share a room because the order between them matters.'),
   ('placard', 'safety', 'Take on what the sign says before you cross the line, not after somebody points at it.'),
   ('walkaround', 'weld-bead', 'gas', 'What is in the bottle and what is in the air are two questions, and both get asked before the arc.'),
   ('crew', 'confined-space-crew', 'entry-supervisor', 'isolate', 'Ask why isolation comes first, and hear the answer as an order of operations rather than a preference.'),
   ('sim', 'weld-bead', 'Run the bead and notice how much of the score was decided before you struck it.'),
   ('advisor', 'safety-steward', 'refuse', 'Practise the refusal here, where it costs nothing and the habit is worth everything.'),
  ],
 },
 {
  'id': 'piling-stand-the-rig-on-something',
  'hall': 'piling', 'strand': 'machines', 'tier': 'applied',
  'title': 'Stand the rig on ground that will hold it',
  'why': 'A piling rig is the heaviest thing on the site standing on the ground least likely to have been looked at.',
  'limits': 'Finishing this is not rig operator standing and no ground has been assessed; the bearing here is schematic, the lift is a teaching aid, and no plan you ran is a lift plan anybody may work to.',
  'steps': [
   ('walk', 'machines', 'The bay is where plant is checked out to a training area, and the ground under it is the first check.'),
   ('placard', 'machines', 'Read what this bay is held to; the conditions on the door are the conditions you work in.'),
   ('walkaround', 'crane-lift', 'base', 'Standing water and washout are the two things that move a machine without anybody touching a lever.'),
   ('crew', 'crane-lift-crew', 'lift-director', 'change', 'Ask what happens when the lift changes, because on a piling job it always does.'),
   ('sim', 'crane-lift', 'Move one thing at a time and let it settle; the gauge is honest even when the seat feels fine.'),
  ],
 },
 {
  'id': 'shoring-read-the-ground-again',
  'hall': 'shoring', 'strand': 'layout', 'tier': 'applied',
  'title': 'Read the ground again after the rain',
  'why': 'Soil that was safe yesterday is a different material after a night of rain, and the inspection cadence is the only defence.',
  'limits': 'Finishing this is not competent person standing and is not a soil classification; the cut is schematic, the ground here has never held water, and no jurisdiction has reviewed a line of it.',
  'steps': [
   ('walk', 'layout', 'Setting out lives here, and so does the discipline of proving a mark before trusting it.'),
   ('advisor', 'layout-hand', 'check', 'Ask how you would know the line is true, because a line nobody checked is a guess in paint.'),
   ('walkaround', 'excavator-trench', 'slew-brake', 'A house that drifts on a test swing will drift over the cut, so test it where the moment is worst.'),
   ('crew', 'trench-crew', 'trench-competent-person', 'again', 'Ask how often the cut gets looked at, and notice the answer is an interval, not a one-off.'),
   ('sim', 'excavator-trench', 'Cut over old fill and let the pace stay slow enough that the ground can surprise you safely.'),
  ],
 },
 {
  'id': 'laborers-stand-where-the-cab-can-see',
  'hall': 'laborers', 'strand': 'safety', 'tier': 'applied',
  'title': 'Stand where the cab can see you',
  'why': 'The person on foot next to a machine is the one who decides whether the machine is dangerous, by where they choose to stand.',
  'limits': 'Finishing this is not ground worker training and grants no authority near plant; the machine here is schematic, no spoil has moved, and the habit it teaches is unverified general practice awaiting the hall.',
  'steps': [
   ('walk', 'safety', 'Induction is the room that decides whether you are allowed near the others, so start there.'),
   ('placard', 'safety', 'Read the door and add what the task needs on top of it, not instead of it.'),
   ('advisor', 'safety-steward', 'ppe', 'Ask what the room requires rather than copying whoever walked in ahead of you.'),
   ('walkaround', 'excavator-trench', 'edge', 'Spoil piled on the lip is weight on the wall, and the wall does not care who piled it.'),
   ('crew', 'trench-crew', 'spotter', 'where', 'Ask where you stand, and notice the answer is about the cab window, not about the trench.'),
  ],
 },
 {
  'id': 'teamsters-check-the-truck-before-the-load',
  'hall': 'teamsters', 'strand': 'machines', 'tier': 'applied',
  'title': 'Check the truck before you check the load',
  'why': 'A yard machine that fails a pre-shift check is a fault found for free, and one that skips it is a fault found the expensive way.',
  'limits': 'Finishing this is not forklift operator training and is not a licence to drive one; the yard is schematic, the loads weigh nothing, and no employer or jurisdiction issues anything on the strength of it.',
  'steps': [
   ('walk', 'machines', 'Plant checked out to a training area is the only plant you are near, which is why the check is taught here.'),
   ('placard', 'machines', 'Read what the bay is held to before you climb on anything parked in it.'),
   ('walkaround', 'forklift-run', 'mast', 'Chain that is uneven side to side lifts crooked, and crooked is how a load leaves the forks.'),
   ('sim', 'forklift-run', 'Run the lane and notice how much of the score is about what you did before the first pallet.'),
   ('advisor', 'operator', 'walk', 'Ask what should be walked before a start, and compare it with what you actually walked.'),
  ],
 },
 {
  'id': 'heavy-equip-listen-to-the-dash',
  'hall': 'heavy-equip', 'strand': 'troubleshooting', 'tier': 'applied',
  'title': 'Listen to the dash before you replace anything',
  'why': 'The gauges are the cheapest diagnostic on the machine and the one most technicians read last.',
  'limits': 'Finishing this is not a technician qualification and diagnoses no real machine; the readouts here are schematic, the fault is scripted, and nothing you concluded has been checked by anybody who repairs plant.',
  'steps': [
   ('walk', 'troubleshooting', 'Fault-finding has its own bench because it needs a different head to the practice floor.'),
   ('walkaround', 'forklift-run', 'tires', 'Chunking and loose nuts are found by looking, and looking costs a minute.'),
   ('advisor', 'operator', 'gauges', 'Ask what the readouts mean before you decide one of them is wrong.'),
   ('sim', 'forklift-run', 'Drive the lane and watch the numbers rather than the pallet; the pallet is where the numbers end up.'),
  ],
 },
 {
  'id': 'marine-terminal-brief-the-lane',
  'hall': 'marine-terminal', 'strand': 'coordination', 'tier': 'applied',
  'title': 'Brief the lane before the first box moves',
  'why': 'A terminal lane is shared ground, and a shift that starts without a briefing starts with everybody guessing who goes first.',
  'limits': 'Finishing this is not terminal operator standing and is not a traffic plan; the lane is schematic, the vehicles are drawn, and no port, employer or authority has reviewed a line of it.',
  'steps': [
   ('walk', 'coordination', 'Shift start and hand-offs happen here, so the briefing is staged here and not on the quay.'),
   ('advisor', 'foreman', 'walk', 'Ask what gets walked before a start, and notice how much of it is about other people.'),
   ('walkaround', 'forklift-run', 'guard', 'A belt that does not latch and a guard that is bent are both answers to a question nobody asked.'),
   ('sim', 'forklift-run', 'Run the lane and treat every other vehicle as somebody who did not hear the briefing.'),
  ],
 },
 {
  'id': 'shipfitters-say-what-you-cannot-see',
  'hall': 'shipfitters', 'strand': 'procedure', 'tier': 'applied',
  'title': 'Say what you cannot see from the hood',
  'why': 'Behind a welding hood the world is one bright spot, and the fitter who admits that is the one who gets the screens up.',
  'limits': 'Finishing this is not a welding qualification and not fit-up training; the seam is schematic, no hull has been tacked, and the practice here is unverified general practice awaiting journey-level review.',
  'steps': [
   ('walk', 'procedure', 'The floor is where the seam is fitted badly a few times, which is the only cheap place to do that.'),
   ('placard', 'procedure', 'Read what the floor is held to before the hood comes down and you stop being able to read anything.'),
   ('walkaround', 'weld-bead', 'screens', 'Screens protect the people who are not welding, which is everybody else in the room.'),
   ('crew', 'hot-work-crew', 'welder', 'blind', 'Ask what cannot be seen from behind the hood, and hear it as a list of jobs for somebody else.'),
   ('sim', 'weld-bead', 'Run the seam and notice how much of the score was about what was set up before the arc.'),
  ],
 },
 {
  'id': 'fabricators-lay-it-out-then-prove-it',
  'hall': 'fabricators', 'strand': 'layout', 'tier': 'applied',
  'title': 'Lay it out, then prove the line before you cut',
  'why': 'Shop steel is cut once, and a layout line nobody checked is a piece of scrap with a drawing number on it.',
  'limits': 'Finishing this is not a fabrication qualification and cuts nothing; the layout is schematic, the seam is a teaching aid, and no shop or inspector has accepted anything on the strength of it.',
  'steps': [
   ('walk', 'layout', 'Setting out and marking live here, and the habit of checking a line before trusting it lives with them.'),
   ('advisor', 'layout-hand', 'check', 'Ask how you know the line is true, because the answer is a method and not a feeling.'),
   ('walkaround', 'weld-bead', 'leads', 'A ground clamp on paint is a bead that will not run right, and the cable jacket is checked end to end.'),
   ('sim', 'weld-bead', 'Run the seam and let the width and the travel argue; the layout was supposed to settle that argument.'),
   ('advisor', 'inspector', 'measures', 'Ask what the seat measures, so that what you think you did and what was measured are the same thing.'),
  ],
 },
 {
  'id': 'pipeline-close-the-permit-properly',
  'hall': 'pipeline', 'strand': 'inspection', 'tier': 'applied',
  'title': 'Close the permit the way it was opened',
  'why': 'A hot work permit that was opened carefully and closed carelessly protected nobody for the hour that mattered most.',
  'limits': 'Finishing this is not a hot work permit, not pipeline welder standing and not a coating or integrity qualification; the permit here is a teaching prop, and your jurisdiction owns the rules that make one binding.',
  'steps': [
   ('walk', 'inspection', 'Acceptance criteria live here, and a permit closed properly is an acceptance step like any other.'),
   ('placard', 'inspection', 'Read what the bench is held to before you start deciding what a pass looks like.'),
   ('walkaround', 'weld-bead', 'extraction', 'Fume that is pulled past your face is fume you are breathing, whatever the fan sounds like.'),
   ('crew', 'hot-work-crew', 'permit-holder', 'close', 'Ask what closes the permit, and notice it is a condition of the room and not a time on a clock.'),
   ('sim', 'weld-bead', 'Run the bead and remember that the last part of the job is the part after the arc stops.'),
  ],
 },
 {
  'id': 'marine-pipe-know-when-to-come-out',
  'hall': 'marine-pipe', 'strand': 'procedure', 'tier': 'applied',
  'title': 'Know when to come out of the compartment',
  'why': 'Shipboard pipework is welded inside steel boxes, and the person inside is the last one to notice the air has changed.',
  'limits': 'Finishing this is not confined space entry training, not a welding qualification and not an entry permit; the compartment is schematic, and nobody here may authorise anybody to enter a real one.',
  'steps': [
   ('walk', 'procedure', 'The floor is where the compartment is rehearsed, which is the only cheap place to rehearse it.'),
   ('placard', 'procedure', 'Read what the floor is held to before the hatch is even a thought.'),
   ('walkaround', 'weld-bead', 'firewatch', 'A charged extinguisher within reach is the difference between a scorch mark and a shift lost.'),
   ('crew', 'confined-space-crew', 'entrant', 'air', 'Ask what changes the air in there, and hear the answer as a list of reasons to leave.'),
   ('sim', 'weld-bead', 'Run the bead and notice how much of the score was decided by the checks before it.'),
  ],
 },
 {
  'id': 'roofers-mind-the-edge-and-the-skylight',
  'hall': 'roofers', 'strand': 'safety', 'tier': 'applied',
  'title': 'Mind the edge, and the skylight nobody mentioned',
  'why': 'Roofing falls happen at the edge everybody sees and through the opening nobody briefed, and the room is where both get named.',
  'limits': 'Finishing this is not fall protection training, not competent person standing and not a roof inspection; the bay is schematic, no membrane has been laid, and no authority has reviewed a line of it.',
  'steps': [
   ('walk', 'safety', 'Induction is where the edge and the opening both get named out loud before anybody goes up.'),
   ('placard', 'safety', 'Read the line on the door and add the fall protection the task needs on top of it.'),
   ('advisor', 'safety-steward', 'hazard', 'Ask what the hazard actually is here, rather than the one you were expecting to hear about.'),
   ('walkaround', 'scaffold-bay', 'plumb', 'A frame that leans by a little at the bottom leans by a lot at the working height.'),
   ('crew', 'scaffold-crew', 'ground-tender', 'zone', 'Ask what a drop zone is, and notice it is a decision made on the ground, not on the roof.'),
   ('sim', 'scaffold-bay', 'Build the bay in order and let the sequence score show where the shortcut would have been.'),
  ],
 },
 {
  'id': 'insulators-stay-inside-the-rails',
  'hall': 'insulators', 'strand': 'materials', 'tier': 'applied',
  'title': 'Stay inside the rails while you reach',
  'why': 'Insulation work is reaching work, and reaching from a basket is where a guardrail stops being furniture.',
  'limits': 'Finishing this is not aerial lift operator training and no lift has been inspected; the basket is schematic, the material here weighs nothing, and no employer or jurisdiction issues anything from it.',
  'steps': [
   ('walk', 'materials', 'Stock and consumables are staged here, and what is staged badly is what gets reached for badly.'),
   ('placard', 'materials', 'Read what the store is held to; a material room has conditions like any other.'),
   ('crib', 'Five picks against the district record, and the point is naming the kit rather than recognising it.'),
   ('walkaround', 'boom-lift', 'guardrails', 'A gate that does not latch behind you is an opening at working height, whatever it looks like.'),
   ('crew', 'aerial-lift-crew', 'ground-attendant', 'sight', 'Ask why the person on the ground stays within sight and sound, and hear it as a rescue plan.'),
   ('sim', 'boom-lift', 'Work the points in order and let the envelope warnings teach you where the reach ends.'),
  ],
 },
 {
  'id': 'plasterers-pin-every-brace',
  'hall': 'plasterers', 'strand': 'procedure', 'tier': 'applied',
  'title': 'Pin every brace before the first hawk goes up',
  'why': 'Plastering is done off a platform, and a platform is only as good as the brace somebody did not quite pin.',
  'limits': 'Finishing this is not scaffold erector standing and not a plastering qualification; the bay is schematic, no coat has been applied, and the sequence here is unverified general practice awaiting the hall.',
  'steps': [
   ('walk', 'procedure', 'The floor is where the platform gets built wrong a few times first, which is why the lesson stands here.'),
   ('walkaround', 'scaffold-bay', 'brace-pins', 'A brace that is sprung rather than pinned is a brace that is not there when the load comes.'),
   ('crew', 'scaffold-crew', 'erector', 'why', 'Ask why the order matters that much, and hear the answer as a description of who is exposed when.'),
   ('sim', 'scaffold-bay', 'Build it in order and notice the step you wanted to skip because it looked finished already.'),
   ('advisor', 'inspector', 'score', 'Ask whether a good explanation can stand in for a measurement, and note how short the answer is.'),
  ],
 },
 {
  'id': 'firestop-write-down-what-you-sealed',
  'hall': 'firestop', 'strand': 'documentation', 'tier': 'fundamentals',
  'title': 'Write down what you sealed and with what',
  'why': 'A firestop seal is judged years later by somebody reading a record, and a seal with no record is a hole with a good story.',
  'limits': 'Finishing this is not a firestop qualification and no listed system has been installed; the record here is a teaching prop, and no inspector or authority has accepted anything on the strength of it.',
  'steps': [
   ('walk', 'documentation', 'Permits, certificates and as-builts live together here, and a seal record is an as-built in miniature.'),
   ('advisor', 'records-clerk', 'where', 'Ask where what you did is actually kept, and who can read it after you have gone.'),
   ('walkaround', 'scaffold-bay', 'tag', 'A tag that does not match what is built is a record that lies, and a lying record is worse than none.'),
   ('crew', 'scaffold-crew', 'scaffold-competent-person', 'tag', 'Ask what the tag actually says, and notice how little of it is about the platform being finished.'),
  ],
 },
 {
  'id': 'cladding-check-the-plank-you-stand-on',
  'hall': 'cladding', 'strand': 'inspection', 'tier': 'applied',
  'title': 'Check the plank you are about to stand on',
  'why': 'Rainscreen panels are hung from a platform, and the panel gets more attention than the plank it is being hung from.',
  'limits': 'Finishing this is not a cladding qualification and not a scaffold inspection; the bay is schematic, no panel has been hung, and the acceptance criteria here are unverified general practice.',
  'steps': [
   ('walk', 'inspection', 'Acceptance criteria and sign-off live here, and a plank is accepted before it is stood on.'),
   ('advisor', 'inspector', 'measures', 'Ask what the seat measures, so what you look for on the bay is what the bay is scored on.'),
   ('walkaround', 'scaffold-bay', 'planks', 'A crack is a reason to change the plank, not a reason to stand on the other end of it.'),
   ('sim', 'scaffold-bay', 'Build the bay and let the sequence score tell you where you would have been standing on nothing.'),
  ],
 },
 {
  'id': 'curtainwall-fuss-about-the-sills',
  'hall': 'curtainwall', 'strand': 'coordination', 'tier': 'applied',
  'title': 'Make the fuss about the sills early',
  'why': 'A unitised panel run is sequenced days ahead, and the bay that carries it stands on whatever was put under it on the first morning.',
  'limits': 'Finishing this is not curtain wall erector standing and not a sequencing plan; the bay is schematic, no anchor has been set, and no employer or hall has reviewed or signed any of it.',
  'steps': [
   ('walk', 'coordination', 'Hand-offs are made here, and the sequence of a panel run is a hand-off written down in advance.'),
   ('advisor', 'foreman', 'handoff', 'Ask what makes a hand-off good, then compare it with what usually gets said at the door.'),
   ('walkaround', 'scaffold-bay', 'sills', 'Blocks and debris under a standard are a base that will move, and everything above it moves with it.'),
   ('crew', 'scaffold-crew', 'erector', 'base', 'Ask why so much fuss is made at the bottom, and hear the answer as the rest of the bay explained.'),
   ('sim', 'scaffold-bay', 'Build it in order and notice that the first step is the one the score remembers longest.'),
  ],
 },
 {
  'id': 'window-glazing-let-the-ground-judge-it',
  'hall': 'window-glazing', 'strand': 'machines', 'tier': 'applied',
  'title': 'Let the ground judge the clearance, not the basket',
  'why': 'From a basket every overhead line looks further away than it is, and the person who can actually judge it is standing on the ground.',
  'limits': 'Finishing this is not aerial lift operator training and no clearance has been measured; the machine here is schematic, the lines are drawn, and nothing recorded is read by any employer or authority.',
  'steps': [
   ('walk', 'machines', 'The bay is where a machine gets checked out to a training area rather than borrowed, so the run starts here.'),
   ('walkaround', 'boom-lift', 'controls', 'Every function is tried from both stations before you trust either, and the manual lowering is tried too.'),
   ('crew', 'aerial-lift-crew', 'line-observer', 'judge', 'Ask why the basket cannot judge it, and hear the answer as a reason to keep somebody on the ground.'),
   ('sim', 'boom-lift', 'Work the points in order and let the envelope warnings teach you the shape of the machine.'),
  ],
 },
 {
  'id': 'sheetmetal-name-the-kit-before-you-climb',
  'hall': 'sheetmetal', 'strand': 'tools', 'tier': 'fundamentals',
  'title': 'Name the kit before you take it up',
  'why': 'Duct is hung from a basket with tools that were issued on the ground, and what you cannot name you cannot ask for.',
  'limits': 'Finishing this is not a sheet metal qualification and issues nothing real; the crib is a teaching prop, the basket is schematic, and no employer or hall has signed anything on the strength of it.',
  'steps': [
   ('walk', 'tools', 'Issue, calibration and return are one loop, and this room is the whole loop.'),
   ('advisor', 'crib-keeper', 'drill', 'Ask how the check is scored before you run it, so you are not guessing at the rules.'),
   ('crib', 'Five picks against the district record, graded deterministically and unforgiving about near-misses.'),
   ('walkaround', 'boom-lift', 'tires-level', 'A pad that is not level under every foot is a machine that will tell you so at full height.'),
   ('advisor', 'operator', 'task', 'Ask what the seat is for before you go up, so the run has a purpose rather than a route.'),
  ],
 },
 {
  'id': 'machinists-move-the-job-without-marking-it',
  'hall': 'machinists', 'strand': 'inspection', 'tier': 'applied',
  'title': 'Move the job across the shop without marking it',
  'why': 'A machined face is ruined in the handling more often than at the machine, and the shop move is where that happens.',
  'limits': 'Finishing this is not overhead crane authorisation and no fit has been measured; the load here is schematic, the tolerances are drawn, and no shop or inspector has accepted anything from it.',
  'steps': [
   ('walk', 'inspection', 'Acceptance lives here, and a part that arrives marked has already failed it.'),
   ('advisor', 'inspector', 'measures', 'Ask what the seat measures, because placement is the number and sway is the reason behind it.'),
   ('walkaround', 'overhead-crane', 'hook', 'A latch that does not spring back is an open hook, and an open hook is a part on the floor.'),
   ('sim', 'overhead-crane', 'Move it slowly enough that the sway settles before the part meets anything.'),
  ],
 },
 {
  'id': 'foundry-clear-the-runway-first',
  'hall': 'foundry', 'strand': 'materials', 'tier': 'applied',
  'title': 'Clear the runway before the ladle moves',
  'why': 'A ladle frame crosses a floor full of people and sand, and the move is safe or not before the hook ever takes weight.',
  'limits': 'Finishing this is not overhead crane authorisation and not foundry floor standing; nothing here is molten, the frame weighs nothing, and no employer or jurisdiction issues anything on the strength of it.',
  'steps': [
   ('walk', 'materials', 'Sand, stock and consumables are staged here, and how they are staged decides what is in the way later.'),
   ('placard', 'materials', 'Read what the store is held to; conditions matter here more than almost anywhere in the hall.'),
   ('crib', 'Five picks against the district record; industry kit is unforgiving about improvisation.'),
   ('walkaround', 'overhead-crane', 'runway', 'A route with somebody standing under it is not a route, whatever the drawing says.'),
   ('sim', 'overhead-crane', 'Run the frame move and notice how much of the score was the floor you cleared first.'),
   ('advisor', 'safety-steward', 'hazard', 'Ask what the hazard in this hall actually is, and hear the answer as the reason for the whole lesson.'),
  ],
 },
]

# ------------------------------------------------- the composed lessons ---
# The lessons above were each written by hand, one hall at a time, and they
# stop where the seats stop: every hall with a simulator seat has one, and
# the 60 halls with no seat, no station and no crew had none. Those halls
# are not empty. Each has the eleven strand rooms, a condition record for
# every one of them, a door placard wherever that record asks for PPE, a
# district tool crib, and six room advisors who stand in six of its rooms.
# That is enough for a short, honest walk and it is ALL such a walk may use.
#
# So the rest of the set is COMPOSED by one rule, written here once:
# six ARCS, one per room an advisor stands in, each a fixed sequence of
# step kinds with notes written here, by us. A hall with no hand-written
# lesson is given exactly one arc, chosen by rotation over the roster
# order so the strands spread rather than pile up, and falling through to
# the next arc when the first cannot be walked honestly - a hazard room
# whose record asks for no PPE has no placard to read, and a hall whose
# own name would repeat a name the step reads would make the title a copy.
# The rule adds no fact: the hall name and focus are READ from the roster,
# the room, the placard, the crib and the advisor from the registries that
# own them. What the rule decides - the order and the framing - is marked
# DERIVED on the lesson, not AUTHORED, because it was not chosen for that
# hall by a person; the notes and the limits are AUTHORED, because they
# were. Every composed lesson carries `authoring: "rule"` and every
# hand-written one `authoring: "hand"`, so a reader is never left to guess.
# The composed tier is `fundamentals`: a first walk, and nothing more.
COMPOSED_TIER = 'fundamentals'
ARCS = [
 {
  'arc': 'safety',
  'title': 'find out what the room is held to',
  'why': 'This hall teaches {focus}, and none of it starts until you know what the room you are standing in asks of you and who may stop the work.',
  'limits': 'Finishing this is not safety training, not an induction and not a permit to enter any real workspace; it is a walk through a schematic room and two scripted answers, and no hall, employer or authority has signed anything on the strength of it.',
  'steps': [
   ('walk', 'safety', 'Start in the room where the rules for the rest of the hall are posted, before you are anywhere near the work.'),
   ('placard?', 'safety', 'Take on what the sign asks before you cross the threshold, and notice what it asks you to put on.'),
   ('advisor', 'safety-steward', 'hazard', 'Ask what is actually in force here rather than assuming it matches the last hall you walked.'),
   ('advisor', 'safety-steward', 'refuse', 'Practise the refusal while it costs nothing, because it is the part of the job people skip.'),
  ],
 },
 {
  'arc': 'tools',
  'title': 'know the kit before you touch it',
  'why': 'This hall teaches {focus}, and the habit worth building first is knowing what is issued, what it is for and how it comes back.',
  'limits': 'Finishing this is not tool training and permits you to use nothing; the check is scored against a record, not against your hands, and no employer or hall accepts it as evidence of anything.',
  'steps': [
   ('walk', 'tools', 'Stand where things are issued and returned, since the kit a trade relies on is kept and counted here.'),
   ('placard?', 'tools', 'Read what the room is held to before you reach for anything hanging on the wall.'),
   ('advisor', 'crib-keeper', 'tools', 'Ask what is actually issued here before you guess from what you saw in another hall.'),
   ('crib', 'Pick from the board by what the record says, not by what looks familiar from another trade.'),
  ],
 },
 {
  'arc': 'layout',
  'title': 'trust a line only as far as it is proved',
  'why': 'This hall teaches {focus}, and all of it is set out from marks somebody made, so the first question is how far those marks can be trusted.',
  'limits': 'Finishing this is not setting-out training and qualifies nobody to mark anything; the floor here is schematic, no real reference has been proved by it, and nobody who does this work has reviewed these lines yet.',
  'steps': [
   ('walk', 'layout', 'Setting out starts here, and so does the habit of checking a mark before building on it.'),
   ('placard?', 'layout', 'Read what the floor is held to before you kneel on it with a tape and a pencil.'),
   ('advisor', 'layout-hand', 'control', 'Ask what the reference actually is before you measure anything off it.'),
   ('advisor', 'layout-hand', 'check', 'Ask how a line is proved, then notice how often that step gets skipped when the day is short.'),
  ],
 },
 {
  'arc': 'inspection',
  'title': 'ask what a pass would actually mean',
  'why': 'This hall teaches {focus}, and before any of that work is judged it is worth knowing who judges it, against what, and what a pass leaves unsaid.',
  'limits': 'Finishing this is not an inspection and not an acceptance of anybody\'s work; nothing here is a sign-off, no grader reads it, and the halls this trade belongs to have not reviewed a line of it.',
  'steps': [
   ('walk', 'inspection', 'Acceptance is decided at this bench, so the conversation about judging work belongs here.'),
   ('placard?', 'inspection', 'Read what the bench is held to; judging work in bad light is its own kind of mistake.'),
   ('advisor', 'inspector', 'score', 'Ask whether talk can move a result, and listen for what the answer says about the record.'),
   ('advisor', 'inspector', 'cert', 'Ask it plainly, because the honest answer is the most useful thing said in this room.'),
  ],
 },
 {
  'arc': 'coordination',
  'title': 'hand the shift over properly',
  'why': 'This hall teaches {focus}, and most of that work passes between people, so the hand-off is worth practising before the work itself.',
  'limits': 'Finishing this is not supervisor training and gives nobody the standing to run a crew; it is one scripted exchange in a schematic room, and no hall or employer has reviewed it.',
  'steps': [
   ('walk', 'coordination', 'Shift starts and hand-offs happen in this room, which is why the exchange is staged here.'),
   ('placard?', 'coordination', 'Read what the room is held to; a briefing nobody can hear is a briefing that did not happen.'),
   ('advisor', 'foreman', 'handoff', 'Ask what makes a hand-off good, then compare it with the last one you actually gave.'),
   ('advisor', 'guide', 'rooms', 'Finish at the threshold by asking what else stands here, so the next walk has somewhere to go.'),
  ],
 },
 {
  'arc': 'documentation',
  'title': 'find out where the record goes',
  'why': 'This hall teaches {focus}, and every part of it leaves paper behind, so the first thing to learn is what gets kept, where, and what it proves.',
  'limits': 'Finishing this is not permit or records training and issues no document of any kind; your progress stays on this device, nothing here certifies anybody, and no hall has reviewed a word of it.',
  'steps': [
   ('walk', 'documentation', 'Permits and as-builts are kept here, so this is where to learn what a record is and what it is not.'),
   ('placard?', 'documentation', 'Read what the room is held to, even here, where the work is paper rather than plant.'),
   ('advisor', 'records-clerk', 'where', 'Ask where your own progress is kept before assuming anybody else can see it.'),
   ('advisor', 'records-clerk', 'cert', 'Ask it plainly, and hold on to the answer when a badge or a count tempts you to think otherwise.'),
  ],
 },
]
ARC_BY_ID = {a['arc']: a for a in ARCS}


def _focus_phrase(focus):
    # "Process piping, drainage" -> "process piping, drainage"; an acronym
    # such as "ALARA" or "HVAC" keeps its capitals, because lowering it
    # would misspell a word the roster owns.
    if len(focus) > 1 and focus[0].isupper() and focus[1].islower():
        return focus[0].lower() + focus[1:]
    return focus


def _arc_names(hall, arc):
    """Every name the arc's steps would read in this hall - the same names
    build_step puts in names_read - so the rule can refuse an arc whose
    title or why would repeat one before build_step is asked to."""
    names = []
    for raw in arc['steps']:
        k = raw[0]
        if k in ('walk', 'placard?'):
            names.append(ROOM_LABEL[raw[1]])
        elif k == 'advisor':
            adv = req(ADVISORS['advisors'], raw[1], f'arc {arc["arc"]}')
            topic = req({t['id']: t for t in adv['topics']}, raw[2], f'arc {arc["arc"]}')
            names += [adv['name'], topic['ask']]
            if adv['stands_in'] in ROOM_LABEL:
                names.append(ROOM_LABEL[adv['stands_in']])
        elif k == 'crib':
            district = req(CRIBS['hall_bindings'], hall, f'arc {arc["arc"]}')['district']
            names += [req(CRIBS['cribs'], district, hall)['name'], CRIBS['drill']['name'], ROOM_LABEL['tools']]
    return names


def compose(hall, arc):
    """One arc in one hall, or the named reason it cannot be walked there."""
    conds = req(req(FINISHES['halls'], hall, hall), 'conditions', hall)
    steps = []
    for raw in arc['steps']:
        if raw[0] == 'placard?':
            strand = raw[1]
            cond = req(conds, strand, f'{hall}.{strand}')
            if req(cond, 'ppe', f'{hall}.{strand}'):
                steps.append(('placard',) + raw[1:])
            elif req(cond, 'hazards', f'{hall}.{strand}'):
                return None, f'the {strand} room is a hazard room whose record asks for no PPE, so there is no placard to read'
        else:
            steps.append(raw)
    if arc['steps'][-1][0] == 'crib':
        req(CRIBS['hall_bindings'], hall, f'{hall}: the tools arc needs a district crib')
    title = f'{HALL_NAME[hall]}: {arc["title"]}'
    why = arc['why'].format(focus=_focus_phrase(HALL_FOCUS[hall]))
    clash = [n for n in _arc_names(hall, arc) if n in title or n in why]
    if clash:
        return None, f'the framing would repeat {clash[0]!r}, a name the steps read'
    if len(title) > 70:
        return None, 'the hall name makes the title longer than a name'
    return {'id': f'{hall}-{arc["arc"]}-first-walk', 'hall': hall, 'strand': arc['arc'],
            'tier': COMPOSED_TIER, 'title': title, 'why': why, 'limits': arc['limits'],
            'steps': steps, 'authoring': 'rule', 'arc': arc['arc']}, None


_HAND_HALLS = {s['hall'] for s in LESSONS_SRC}
for _s in LESSONS_SRC:
    _s['authoring'] = 'hand'
COMPOSED = []
COMPOSE_REFUSED = {}
_order = [h['slug'] for h in sorted(HALLS, key=lambda h: h['index']) if h['slug'] not in _HAND_HALLS]
for _i, _hall in enumerate(_order):
    _why_not = []
    for _k in range(len(ARCS)):
        _arc = ARCS[(_i + _k) % len(ARCS)]
        _lesson, _reason = compose(_hall, _arc)
        if _lesson:
            COMPOSED.append(_lesson)
            break
        _why_not.append(f'{_arc["arc"]}: {_reason}')
    else:
        COMPOSE_REFUSED[_hall] = _why_not
LESSONS_SRC = LESSONS_SRC + COMPOSED

# ------------------------------------------------------------- the ladder ---
# A prerequisite edge names a reason from a closed set, and each reason is
# CHECKED against the registries below rather than taken on trust.
EDGE_REASONS = {
    'same-hall': 'both lessons stand in the same hall, so the second is the next thing to do in a building you are already in',
    'same-seat': 'both lessons run or walk the same simulator seat, so the first is seat familiarity the second assumes',
    'same-district-crib': 'both halls draw from the same district tool crib, so the kit and the vocabulary carry across',
}

LADDER_SRC = {
    'riggers-carry-under-control': [('riggers-first-card', 'same-hall')],
    'crane-ops-read-the-chart': [('riggers-first-card', 'same-district-crib')],
    'ironworkers-plan-out-loud': [('riggers-carry-under-control', 'same-seat')],
    'millwrights-shop-move': [('crane-ops-read-the-chart', 'same-district-crib')],
    'boilermakers-get-them-out': [('welders-the-watch', 'same-seat')],
    'demolition-stand-back': [('operating-eng-locate-first', 'same-seat')],
    'scaffold-build-in-order': [('scaffold-read-the-tag', 'same-hall')],
    'waterproofers-flash-it-right': [('scaffold-build-in-order', 'same-seat')],
    'bricklayers-grout-the-lift': [('bricklayers-gear-that-stays-on', 'same-hall')],
    'cement-masons-mind-the-weather': [('bricklayers-gear-that-stays-on', 'same-district-crib')],
    'stone-carvers-hang-it-safely': [('bricklayers-gear-that-stays-on', 'same-district-crib')],
    'tilesetters-start-underneath': [('bricklayers-gear-that-stays-on', 'same-district-crib')],
    'restore-write-it-down': [('restore-point-the-joint', 'same-hall')],
    'painters-lay-the-coat': [('painters-contain-it', 'same-hall')],
    'hazmat-wash-and-decon': [('painters-contain-it', 'same-seat')],
    'glaziers-watch-the-line': [('electricians-clip-in-first', 'same-seat')],
    # the seat-bound halls, sequenced off the lesson that already runs the
    # same seat, or off a sibling on the same district crib
    'steel-erectors-land-it-on-the-bolts': [('riggers-first-card', 'same-district-crib'),
                                           ('riggers-carry-under-control', 'same-seat')],
    'port-crane-read-the-rope': [('riggers-carry-under-control', 'same-seat')],
    'decking-walk-the-path-first': [('riggers-first-card', 'same-seat')],
    'tank-erectors-isolate-before-testing': [('boilermakers-get-them-out', 'same-seat')],
    'piling-stand-the-rig-on-something': [('riggers-carry-under-control', 'same-seat')],
    'shoring-read-the-ground-again': [('operating-eng-locate-first', 'same-seat')],
    'laborers-stand-where-the-cab-can-see': [('demolition-stand-back', 'same-seat')],
    'heavy-equip-listen-to-the-dash': [('teamsters-check-the-truck-before-the-load', 'same-seat')],
    'marine-terminal-brief-the-lane': [('teamsters-check-the-truck-before-the-load', 'same-seat')],
    'shipfitters-say-what-you-cannot-see': [('welders-the-watch', 'same-seat')],
    'fabricators-lay-it-out-then-prove-it': [('shipfitters-say-what-you-cannot-see', 'same-seat')],
    'pipeline-close-the-permit-properly': [('tank-erectors-isolate-before-testing', 'same-district-crib')],
    'marine-pipe-know-when-to-come-out': [('pipeline-close-the-permit-properly', 'same-seat')],
    'roofers-mind-the-edge-and-the-skylight': [('scaffold-read-the-tag', 'same-seat')],
    'insulators-stay-inside-the-rails': [('electricians-clip-in-first', 'same-seat')],
    'plasterers-pin-every-brace': [('scaffold-build-in-order', 'same-seat')],
    'firestop-write-down-what-you-sealed': [('tilesetters-start-underneath', 'same-district-crib')],
    'cladding-check-the-plank-you-stand-on': [('firestop-write-down-what-you-sealed', 'same-seat')],
    'curtainwall-fuss-about-the-sills': [('cladding-check-the-plank-you-stand-on', 'same-district-crib')],
    'window-glazing-let-the-ground-judge-it': [('glaziers-watch-the-line', 'same-seat')],
    'sheetmetal-name-the-kit-before-you-climb': [('fiber-splicers-keep-the-trace', 'same-district-crib')],
    'machinists-move-the-job-without-marking-it': [('millwrights-shop-move', 'same-seat')],
    'foundry-clear-the-runway-first': [('machinists-move-the-job-without-marking-it', 'same-seat')],
}

# The ceiling on concentration. Breadth over the trades is the claim, so
# the claim is given a number the build can fail against.
MAX_HALL_SHARE = 0.10

# ------------------------------------------------------------ the honesty ---
HONESTY = {
    # {hand}, {rule} and {arcs} are filled in below from the counts the build computes
    'status': 'AUTHORED: every sentence in this pack was written here, by us. {hand} lessons were written by hand, one hall at a time, step by step; the other {rule} are composed by one rule in lessons/build.py from {arcs} arcs written here, one per room an advisor stands in, so their step order, title and why are marked DERIVED and carry authoring "rule" - the rule reads the hall name and focus from the roster and adds no fact of its own. Nothing is fetched and no model runs behind any of it. The word AI-SYNTHESIZED belongs to orbis/ and describes generated video; it would be a false label for a hand-written walk through a building.',
    'content': 'unverified general practice. These lessons were written to be argued with, corrected and replaced by journey-level practitioners from the halls they name - the same standing the module pack, the recovered stations and the simulator seats already carry, and for the same reason: nobody who does this work for a living has reviewed a line of it yet.',
    'not_certification': 'no lesson here certifies anybody, qualifies anybody or permits anybody to do anything. Completing every lesson in this registry would leave a learner with exactly the standing they started with. Where a trade has a real ticket, that ticket is issued by a jurisdiction, an employer or a hall, and this bundle is none of those and speaks for none of them.',
    'not_a_gate': 'a lesson unlocks nothing. No step is locked behind another, the ladder is guidance about a sensible order rather than a permission system, and the assessment gate that schools/ declares stays exactly where it is: an unaided verification run that no lesson, station hour or simulator seat substitutes for.',
    'not_scored': 'finishing a lesson changes no score and is read by no grader. Four of the eight step kinds write an episode to the existing device-local training log; the other four write nothing at all, and the registry says which is which rather than leaving it to be discovered.',
    'one_truth': 'this pack holds no second copy of anything. Hall names, room labels, station names, seat names, scenario names, advisor names, crew role names and topic wordings are all read at build time from the registries that own them, and the test re-reads them the same way. A step that could not resolve its ids did not become a lesson with a footnote; it failed the build.',
    'no_jurisdiction': 'nothing here cites a standard, a code or an authority, and nothing here speaks for one. Where a step says what a crew would do, that is unverified general practice and not an instruction from anybody with the standing to give one.',
    # {lessons}, {halls} and {seat_bound} are filled in below from the counts
    # the build computes; a typed figure here would be a second copy.
    'scope': 'this is a set deliberately spread thin: {lessons} lessons across {halls} of {halls_total} halls, one in every one of the {seat_bound} halls a simulator seat is bound to and one composed first walk in every hall without a seat that the rule could walk honestly ({refused} refused), out of 1,221 rooms. It demonstrates the shape a lesson takes in this bundle. It is not a curriculum, it does not cover a trade, and no hall is finished because one of its rooms now has a lesson standing in it.',
}

PAGE_CONTRACT = {
    'data': 'ship this registry to the page as D.lessons, the same way D.guide and D.crews already arrive: the whole document, indexed by lesson id, with no per-lesson preprocessing. The page adds no field to it at boot.',
    'hall': 'in the hall view, a hall that any lesson names gets one chip per lesson on the hall roster, reading the lesson title and the room label of its strand. The chip is a way in, not a gate: it grants nothing and hides nothing.',
    'room': 'inside the hall the page already tracks curRoom and knows curRoom.strand. When the strand of the room the learner has walked into matches a lesson standing in that hall, the lesson becomes the active one; when they walk out, it stops being active. No other state is kept.',
    'hud': 'while a lesson is active the hfocus line keeps the room label and finish it already shows, and the hint line shows the lesson title, the current step number out of the step count, and that step\'s computed `do` line - never the note, which is commentary for a reader rather than an instruction for a learner mid-room.',
    'reads': 'the page must READ and never copy: the room label from the strand, the station name from D.stations, the seat name, scenario name and walkaround point from D.sims, the advisor and crew role names and the exact topic wording from D.advisors and D.crews, and the condition line for a placard step from the same condOf()/condLine() pair the hint line already uses. This registry stores ids for all of those on purpose.',
    'steps': 'render the steps in the order given, numbered. A step is marked done by the learner, in this browser only. A step is never enforced: the page must let somebody do step four first, because the building does, and a lesson that could trap a learner in a room would be a gate wearing a lesson\'s clothes.',
    'records': 'a step whose `records` is a string writes exactly that episode kind through the training recorder that already exists, with no new field and no new storage key. A step whose `records` is null writes nothing - the page must not invent an episode for it, and must not mark the lesson as recorded because a learner walked somewhere.',
    'ladder': 'render a lesson\'s prerequisites as named links with the edge reason shown. Do not disable a lesson whose prerequisites are unfinished: the ladder is advice about order and the registry says so, and enforcing it in the page would turn it into the gate this pack promises it is not.',
    'limits': 'the `limits` sentence renders with the lesson, not behind a disclosure control, and not only at the end. A learner who is told what a lesson does not mean only after finishing it has already formed the belief the sentence exists to prevent.',
    'episode': 'nothing about opening, reading or abandoning a lesson is recorded. The only episodes that reach the training log are the four the step kinds already declare, written by the recorder that was already writing them.',
}

# ============================================================== resolution ===
# From here down nothing is typed: every name, label and wording is read
# from the registry that owns it, and every id is resolved or the build
# stops and says which one did not.

EPISODE_KINDS = TRAINING['episode_kinds']
CRIB_BINDINGS = CRIBS['hall_bindings']
CRIB_DRILL = CRIBS['drill']

# the display names a step's prose may NOT repeat: if the note says it, the
# registry that owns it has a second copy and the page has two truths.
def _forbidden(names):
    return [n for n in names if n]


def build_step(lesson, idx, raw):
    hall = lesson['hall']
    kind = raw[0]
    note = raw[-1]
    spec = req(STEP_KINDS, kind, f'{lesson["id"]} step {idx}')
    step = {'n': idx, 'kind': kind, 'records': spec['records'],
            'stage': spec['stage'], 'reads': spec['reads'], 'note': note}
    names = []

    if kind in ('walk', 'placard'):
        strand = raw[1]
        step['where'] = strand
        label = req(ROOM_LABEL, strand, f'{lesson["id"]} step {idx}')
        if kind == 'walk':
            step['do'] = f'Walk to the {label} — {ROOM_PURPOSE[strand].lower()}.'
        else:
            # web/build_3d.py hangs the PPE board only where the merged
            # condition record requires something (`if (rc.ppe.length)`):
            # a room that requires nothing gets no sign rather than a sign
            # saying "nothing". A placard step in such a room would read a
            # board that is not there, so it is refused by name.
            cond = req(req(FINISHES['halls'], hall, f'{lesson["id"]} step {idx}')['conditions'],
                       strand, f'{lesson["id"]} step {idx}')
            assert cond['ppe'], \
                f'{lesson["id"]} step {idx}: the {label} of {hall} requires no PPE, so the builder hangs no placard there to read'
            step['do'] = (f'Read the door placard of the {label}: it states the '
                          f'light, air, noise and protective equipment that room is held to.')
            step['label_kind'] = 'placard'
        names.append(label)

    elif kind == 'station':
        sid = raw[1]
        st = req(STATION_BY_ID, sid, f'{lesson["id"]} step {idx}')
        assert st['hall'] == hall, \
            f'{lesson["id"]} step {idx}: station {sid} stands in {st["hall"]}, not {hall}'
        step['where'] = st['strand']
        step['station'] = sid
        label = req(ROOM_LABEL, st['strand'], f'{lesson["id"]} step {idx}')
        step['do'] = f'Take the {st["name"]} station at the {label} bench.'
        names += [st['name'], label]

    elif kind == 'crib':
        binding = req(CRIB_BINDINGS, hall, f'{lesson["id"]} step {idx}')
        district = binding['district']
        crib = req(CRIBS['cribs'], district, f'{lesson["id"]} step {idx}')
        drill = req(CRIBS['drills'], district, f'{lesson["id"]} step {idx}')
        assert len(drill) == CRIB_DRILL['picks'], \
            f'{lesson["id"]} step {idx}: the {district} drill is not the declared number of picks'
        step['where'] = 'tools'
        step['crib'] = district
        step['do'] = (f'Run the {CRIB_DRILL["name"]} at the {crib["name"]} pegboard '
                      f'— {CRIB_DRILL["picks"]} picks.')
        names += [crib['name'], CRIB_DRILL['name'], ROOM_LABEL['tools']]

    elif kind in ('walkaround', 'sim'):
        simid = raw[1]
        sim = req(SIMS['sims'], simid, f'{lesson["id"]} step {idx}')
        assert hall in sim['halls'], \
            f'{lesson["id"]} step {idx}: {hall} does not train on the {simid} seat'
        step['where'] = 'yard'
        step['sim'] = simid
        if kind == 'walkaround':
            pid = raw[2]
            pts = {p['id']: p for p in sim['walkaround']}
            pt = req(pts, pid, f'{lesson["id"]} step {idx}')
            step['point'] = pid
            step['do'] = (f'Walk the {sim["name"]} seat and mark the point '
                          f'"{pt["point"]}": {pt["check"]}.')
            names += [sim['name'], pt['point']]
        else:
            campus = req(HALL_CAMPUS, hall, f'{lesson["id"]} step {idx}')
            scens = {s['id']: s for s in sim['scenarios'] if s['campus'] == campus}
            assert len(scens) == 1, \
                f'{lesson["id"]} step {idx}: {simid} has {len(scens)} scenarios on {campus}'
            scid, sc = next(iter(scens.items()))
            step['scenario'] = scid
            step['campus'] = campus
            step['do'] = f'Run the {sim["name"]} seat on the {sc["name"]} scenario.'
            names += [sim['name'], sc['name']]

    elif kind == 'advisor':
        aid, tid = raw[1], raw[2]
        adv = req(ADVISORS['advisors'], aid, f'{lesson["id"]} step {idx}')
        topics = {t['id']: t for t in adv['topics']}
        topic = req(topics, tid, f'{lesson["id"]} step {idx}')
        where = adv['stands_in']
        step['where'] = where
        step['advisor'] = aid
        step['topic'] = tid
        step['answer_kind'] = topic['kind']
        if where in ROOM_LABEL:
            place = f'in the {ROOM_LABEL[where]}'
            names.append(ROOM_LABEL[where])
        else:
            place = f'at the {req(OFF_ROOM_PLACES, where, lesson["id"])["short"]}'
        step['do'] = f'Ask the {adv["name"]} {place}: "{topic["ask"]}"'
        names += [adv['name'], topic['ask']]

    elif kind == 'crew':
        cid, rid, tid = raw[1], raw[2], raw[3]
        crew = req(CREWS['crews'], cid, f'{lesson["id"]} step {idx}')
        assert hall in crew['halls'], \
            f'{lesson["id"]} step {idx}: the {cid} does not stand for {hall}'
        role = req(crew['roles'], rid, f'{lesson["id"]} step {idx}')
        topics = {t['id']: t for t in role['topics']}
        topic = req(topics, tid, f'{lesson["id"]} step {idx}')
        step['where'] = 'yard'
        step['crew'] = cid
        step['role'] = rid
        step['topic'] = tid
        step['seat'] = crew['seat']
        step['muster'] = crew['muster']
        step['answer_kind'] = topic['kind']
        step['do'] = (f'With the seat running, ask the {crew["name"]}\'s '
                      f'{role["name"]}: "{topic["ask"]}"')
        names += [crew['name'], role['name'], topic['ask']]

    else:
        raise AssertionError(f'{lesson["id"]} step {idx}: {kind} is not a step kind')

    step['names_read'] = _forbidden(names)
    return step


LESSONS = {}
for src in LESSONS_SRC:
    lid = src['id']
    assert lid not in LESSONS, f'{lid}: two lessons share an id'
    hall, strand, tier = src['hall'], src['strand'], src['tier']
    assert hall in HALL_NAME, f'{lid}: {hall} is not a hall in the roster'
    assert strand in req(HALL_STRANDS, hall, lid), \
        f'{lid}: {hall} does not teach the {strand} strand'
    assert tier in TIER_RANK, f'{lid}: {tier} is not a skill tier'
    skill_id = f'{hall}.{strand}.{tier}'
    assert skill_id in SKILL_IDS, f'{lid}: {skill_id} is not a skill this bundle declares'
    # a lesson stands in a ROOM, and the surfaces record is what says that
    # room exists in this hall and what it is held to
    hall_rec = req(FINISHES['halls'], hall, lid)
    assert strand in hall_rec['rooms'], f'{lid}: {hall} has no {strand} room'
    assert strand in hall_rec['conditions'], \
        f'{lid}: the {strand} room of {hall} carries no condition record'

    steps = [build_step(src, i + 1, raw) for i, raw in enumerate(src['steps'])]
    assert steps, f'{lid}: a lesson with no steps is a title'
    assert steps[0]['kind'] == 'walk' and steps[0]['where'] == strand, \
        f'{lid}: a lesson starts by walking into the room it stands in'
    # every step happens somewhere real in this hall
    for st in steps:
        assert st['where'] in hall_rec['rooms'] or st['where'] in OFF_ROOM_PLACES, \
            f'{lid} step {st["n"]}: {st["where"]} is not a room of {hall} or a place in it'
    # a crew only stands while its own seat is running, so a crew step
    # requires the lesson to be at that seat
    seats_here = {st['sim'] for st in steps if 'sim' in st}
    for st in steps:
        if st['kind'] == 'crew':
            assert st['seat'] in seats_here, \
                f'{lid} step {st["n"]}: the crew stands at the {st["seat"]} seat and this lesson never goes there'
    # a lesson that records nothing is not a lesson this bundle can show a
    # learner anything about afterwards
    written = [st['records'] for st in steps if st['records'] is not None]
    assert written, f'{lid}: no step of this lesson writes an episode'
    for k in written:
        assert k in EPISODE_KINDS, \
            f'{lid}: {k} is not an episode kind training/ already declares'

    LESSONS[lid] = {
        'id': lid, 'hall': hall, 'hall_name': HALL_NAME[hall],
        'campus': req(HALL_CAMPUS, hall, lid),
        'strand': strand, 'tier': tier, 'skill_id': skill_id,
        'room_label': ROOM_LABEL[strand],
        'title': src['title'], 'why': src['why'], 'limits': src['limits'],
        'steps': steps,
        'records': sorted(set(written)),
        'stages': sorted({st['stage'] for st in steps}),
        'reads': sorted({st['reads'] for st in steps}),
        'authoring': src['authoring'],
        # a composed lesson's order and framing were chosen by the rule
        # above, not by a person for that hall, so they say DERIVED
        'provenance': ({'steps': 'AUTHORED', 'order': 'AUTHORED',
                        'title': 'AUTHORED', 'why': 'AUTHORED',
                        'limits': 'AUTHORED', 'names': 'READ'}
                       if src['authoring'] == 'hand' else
                       {'steps': 'AUTHORED', 'order': 'DERIVED',
                        'title': 'DERIVED', 'why': 'DERIVED',
                        'limits': 'AUTHORED', 'names': 'READ'}),
    }
    if src['authoring'] == 'rule':
        LESSONS[lid]['arc'] = src['arc']

# -- the prose. One sentence of `why`, a real `limits`, and no note that
# -- repeats a name the registries already own.
for lid, L in LESSONS.items():
    assert 60 <= len(L['title']) + len(L['why']) , f'{lid}: the framing is too thin'
    assert 12 < len(L['title']) <= 70, f'{lid}: a title is a name, not a paragraph'
    assert L['why'].endswith('.') and L['why'].count('. ') == 0 and 60 < len(L['why']) <= 240, \
        f'{lid}: `why` is one plain sentence'
    assert 120 < len(L['limits']) <= 400, f'{lid}: say the limit properly or not at all'
    assert any(w in L['limits'] for w in (' not ', ' no ', ' nothing ', ' nobody ', ' never ')), \
        f'{lid}: a limits line that denies nothing is a tagline'
    for st in L['steps']:
        assert 50 <= len(st['note']) <= 200, \
            f'{lid} step {st["n"]}: a note is one useful sentence'
        for n in st['names_read']:
            assert n not in st['note'], \
                f'{lid} step {st["n"]}: the note repeats {n!r}, which is read from the registry that owns it'
        for n in st['names_read']:
            assert n not in L['title'] and n not in L['why'], \
                f'{lid}: the framing repeats {n!r} rather than reading it'

# -- nothing here certifies anybody. Every statement in the payload that
# -- claims a ticket must be denying it IN THE SAME CLAUSE. A denial two
# -- clauses later is the shape a marketing sentence takes - "this certifies
# -- you to operate a crane; nothing here is read by a grader" would pass a
# -- sentence-level check and mean the opposite of what this pack promises -
# -- so the split is on clause punctuation, not sentence punctuation. A
# -- QUESTION is not a claim: the advisor topic "Does a pass here certify
# -- me?" is a learner asking, and its answer lives in the advisor registry,
# -- so questions are skipped and everything else, authored prose and
# -- computed `do` line alike, is held to it.
import re  # noqa: E402

CLAIM_WORDS = re.compile(
    r'\b(certif(?:y|ies|ied|ying|ication|ications)|qualif(?:y|ies|ied|ication|ications)'
    r'|licen[cs]e[sd]?|licensing|ticketed)\b', re.I)
DENIALS = ('not', 'no ', 'nothing', 'nobody', 'never', 'none', 'without')
_cert_claims = []
for lid, L in LESSONS.items():
    fields = ([L['title'], L['why'], L['limits']]
              + [st['note'] for st in L['steps']] + [st['do'] for st in L['steps']])
    for field in fields:
        for sentence in re.split(r'(?<=[.!?;:])\s+', field):
            if '?' in sentence:
                continue
            if CLAIM_WORDS.search(sentence) and not any(w in sentence.lower() for w in DENIALS):
                _cert_claims.append(f'{lid}: {sentence.strip()}')
assert not _cert_claims, \
    'a lesson claims to certify, qualify or license somebody: ' + ' | '.join(_cert_claims)

# -- the flipped classroom. A lesson is the class and floor halves made
# -- walkable; it is not a fifth stage and it never touches the gate.
_stages_used = sorted({st['stage'] for L in LESSONS.values() for st in L['steps']})
for s in _stages_used:
    assert s in SCHOOL_STAGES, f'{s} is not a stage schools/ declares'
assert 'gate' not in _stages_used, \
    'the gate is the one stage schools/ leaves deliberately ungamified, and no lesson may stand in it'
assert 'home' not in _stages_used, \
    'the home stage is the module pack and i18n; a walkable lesson is not it'
assert set(_stages_used) == {'class', 'floor'}, \
    'a lesson is the class and floor halves of the loop, and nothing else'

# -- breadth. The claim is a wide spread over the trades, so it is counted.
HALLS_COVERED = sorted({L['hall'] for L in LESSONS.values()})
STRANDS_COVERED = sorted({L['strand'] for L in LESSONS.values()})
_per_hall = {}
for L in LESSONS.values():
    _per_hall[L['hall']] = (_per_hall[L['hall']] if L['hall'] in _per_hall else 0) + 1
MAX_IN_A_HALL = max(_per_hall.values())
TOP_SHARE = MAX_IN_A_HALL / len(LESSONS)
assert TOP_SHARE <= MAX_HALL_SHARE, \
    f'one hall holds {TOP_SHARE:.2%} of the lessons, over the declared {MAX_HALL_SHARE:.0%} ceiling'
assert len(STRANDS_COVERED) == len(ROOM_LABEL), \
    f'{len(STRANDS_COVERED)} of {len(ROOM_LABEL)} strands are covered; breadth means all of them'
assert len(HALLS_COVERED) >= 20, \
    f'{len(HALLS_COVERED)} halls is depth in a corner, not breadth over the trades'

# -- every seat-bound hall has a lesson. sims/registry/sims.json#hall_bindings
# -- is the list of halls with an operable seat; a hall with a floor and no
# -- reason to walk onto it is the gap this set exists to close, so the set
# -- is held to it. The list is READ, never typed.
SEAT_BOUND_HALLS = sorted(SIMS['hall_bindings'])
for slug in SEAT_BOUND_HALLS:
    assert slug in HALL_NAME, f'sims binds a seat to {slug}, which is not a hall'
_seat_bound_without = [h for h in SEAT_BOUND_HALLS if h not in _per_hall]
assert not _seat_bound_without, \
    'seat-bound halls with no lesson: ' + ', '.join(_seat_bound_without)

# -- a hazard room is walked with its placard read. compliance/build.py
# -- derives a hall's hazard rooms from surfaces/registry/finishes.json: a
# -- room whose condition record names a governing hazard. That reading is
# -- reused here, not restated: a lesson that stands in, or sends its
# -- learner through, a hazard room carries a placard step in that room.
# -- Any step with a room `where` counts as walking it - a station bench, the
# -- crib pegboard and an advisor's post included - exactly as compliance
# -- counts them.
def hazard_rooms_of(hall):
    conds = req(FINISHES['halls'], hall, 'finishes')['conditions']
    return sorted(s for s in conds if req(conds[s], 'hazards', f'{hall}.{s}'))


HAZARD_GAPS = []
for lid, L in LESSONS.items():
    walked = sorted({st['where'] for st in L['steps'] if st['where'] not in OFF_ROOM_PLACES})
    placarded = {st['where'] for st in L['steps'] if st['kind'] == 'placard'}
    gaps = [s for s in hazard_rooms_of(L['hall']) if s in walked and s not in placarded]
    L['rooms_walked'] = walked
    L['hazard_rooms_walked'] = [s for s in hazard_rooms_of(L['hall']) if s in walked]
    L['placard_steps_in'] = sorted(placarded)
    for s in gaps:
        HAZARD_GAPS.append(f'{lid} walks the {ROOM_LABEL[s]} ({s}), a hazard room of {L["hall"]}, and never reads its placard')
assert not HAZARD_GAPS, 'hazard rooms walked without a placard step: ' + ' | '.join(HAZARD_GAPS)

# the scope sentence carries the figures the build just computed, and nothing typed
HONESTY['scope'] = HONESTY['scope'].format(
    lessons=len(LESSONS), halls=len(HALLS_COVERED), halls_total=len(HALLS),
    seat_bound=len(SEAT_BOUND_HALLS), refused=len(COMPOSE_REFUSED))
HAND_COUNT = sum(1 for L in LESSONS.values() if L['authoring'] == 'hand')
RULE_COUNT = sum(1 for L in LESSONS.values() if L['authoring'] == 'rule')
HONESTY['status'] = HONESTY['status'].format(hand=HAND_COUNT, rule=RULE_COUNT, arcs=len(ARCS))
# -- every hall is walked, or the rule said by name why it could not be.
# -- A hall silently missing is the gap this rule exists to close.
_unwalked = [h['slug'] for h in HALLS
             if h['slug'] not in _per_hall and h['slug'] not in COMPOSE_REFUSED]
assert not _unwalked, 'halls with no lesson and no stated reason: ' + ', '.join(_unwalked)
for _h, _why in COMPOSE_REFUSED.items():
    assert len(_why) == len(ARCS), f'{_h}: refused without trying every arc'
# -- a composed lesson is one per hall, never beside a hand-written one,
# -- and it stands only on the step kinds a hall with no seat can support
for L in LESSONS.values():
    if L['authoring'] == 'rule':
        assert _per_hall[L['hall']] == 1, f'{L["id"]}: a composed lesson shares its hall'
        assert L['tier'] == COMPOSED_TIER, f'{L["id"]}: a composed lesson is a first walk'
        assert {st['kind'] for st in L['steps']} <= {'walk', 'placard', 'crib', 'advisor'}, \
            f'{L["id"]}: a composed lesson uses a step kind its hall cannot support'
# and every episode kind training/ declares is actually exercised
_kinds_used = sorted({k for L in LESSONS.values() for k in L['records']})
assert _kinds_used == sorted(EPISODE_KINDS), \
    f'the lesson set exercises {_kinds_used}, not every episode kind training/ declares'

# ---------------------------------------------------------------- ladder ---
LADDER = {}
for lid in LESSONS:
    LADDER[lid] = []
for lid, edges in LADDER_SRC.items():
    assert lid in LESSONS, f'the ladder sequences {lid}, which is not a lesson'
    seen = set()
    for needs, because in edges:
        assert needs in LESSONS, \
            f'{lid}: prerequisite {needs} is not a lesson in this registry'
        assert needs != lid, f'{lid}: a lesson cannot be its own prerequisite'
        assert needs not in seen, f'{lid}: {needs} is named twice'
        seen.add(needs)
        assert because in EDGE_REASONS, f'{lid}->{needs}: {because} is not a declared reason'
        A, B = LESSONS[needs], LESSONS[lid]
        if because == 'same-hall':
            assert A['hall'] == B['hall'], \
                f'{lid}->{needs}: claimed same-hall, but {A["hall"]} is not {B["hall"]}'
        elif because == 'same-seat':
            sa = {s['sim'] for s in A['steps'] if 'sim' in s}
            sb = {s['sim'] for s in B['steps'] if 'sim' in s}
            assert sa & sb, \
                f'{lid}->{needs}: claimed same-seat, but they share no simulator seat'
        elif because == 'same-district-crib':
            da = req(CRIB_BINDINGS, A['hall'], lid)['district']
            db = req(CRIB_BINDINGS, B['hall'], lid)['district']
            assert da == db, \
                f'{lid}->{needs}: claimed same-district-crib, but {da} is not {db}'
        LADDER[lid].append({'needs': needs, 'because': because,
                            'reason': EDGE_REASONS[because]})

# acyclic, proved by walking it rather than asserted by construction
_state = {}


def _visit(node, path):
    st = _state[node] if node in _state else 'new'
    if st == 'done':
        return
    if st == 'open':
        cycle = path[path.index(node):] + [node]
        raise AssertionError('the ladder has a cycle: ' + ' -> '.join(cycle))
    _state[node] = 'open'
    for e in LADDER[node]:
        _visit(e['needs'], path + [node])
    _state[node] = 'done'


for lid in LADDER:
    _visit(lid, [])

# a prerequisite may not be further along the tiers than the lesson it gates
for lid, edges in LADDER.items():
    for e in edges:
        assert TIER_RANK[LESSONS[e['needs']]['tier']] <= TIER_RANK[LESSONS[lid]['tier']], \
            f'{lid}: prerequisite {e["needs"]} sits at a higher tier than the lesson it gates'

DEPTH = {}


def _depth(node):
    if node in DEPTH:
        return DEPTH[node]
    d = 1 + max([_depth(e['needs']) for e in LADDER[node]], default=0)
    DEPTH[node] = d
    return d


for lid in LADDER:
    _depth(lid)

ROOTS = sorted(lid for lid, e in LADDER.items() if not e)
EDGES = [(lid, e['needs'], e['because']) for lid, es in LADDER.items() for e in es]
LAYERS = {}
for lid, d in DEPTH.items():
    LAYERS.setdefault(d, []).append(lid)
LADDER_LAYERS = {str(d): sorted(v) for d, v in sorted(LAYERS.items())}

# --------------------------------------------------------- final refusals ---
_reads = sorted({st['reads'] for L in LESSONS.values() for st in L['steps']})
for f in _reads:
    assert (ROOT / f).exists(), f'{f} is read by a step kind and does not exist'

# the placard step kind leans on a sign this bundle already draws, hung only
# where the room requires something: both facts are located in the page
assert 'placard' in LABELS['kinds'], \
    'the placard step reads a sign kind the labels pack no longer declares'
assert 'if (rc.ppe.length)' in PAGE_SRC and "kind: 'placard', items: rc.ppe" in PAGE_SRC, \
    'web/build_3d.py no longer hangs the PPE placard on rc.ppe.length: the placard step rule above no longer reads the page'

# the page this contract is written for still behaves the way it describes
for token in ('curRoom', 'hfocus', 'hint', "view = 'hall'", 'condLine', 'condOf'):
    assert token in PAGE_SRC, \
        f'the page contract names {token!r}, which the page no longer has'
# and the return path the contract describes is wired: the hall view reads
# D.lessons, whole, the way page_contract.data asks. This used to assert the
# absence, back when nothing had built it; lessons/test.mjs holds the page
# to the same fact from the bytes that ship.
assert 'D.lessons' in PAGE_SRC, \
    'the page no longer reads D.lessons: the contract describes a return path nothing builds'

# no network, no URL, nothing fetched at view time
_payload_text = json.dumps([LESSONS, LADDER, HONESTY, PAGE_CONTRACT, STEP_KINDS])
assert 'http://' not in _payload_text and 'https://' not in _payload_text, \
    'a lesson names no URL: this pack fetches nothing and links nowhere'
# orbis owns the generated-content word. It may appear exactly once here,
# in the sentence that says it is orbis's word and not ours.
assert 'AI-SYNTHESIZED' in HONESTY['status'], \
    'the honesty block must say which word this pack refuses and why'
_ai_elsewhere = json.dumps([LESSONS, LADDER, PAGE_CONTRACT, STEP_KINDS,
                            {k: v for k, v in HONESTY.items() if k != 'status'}])
assert 'AI-SYNTHESIZED' not in _ai_elsewhere, \
    'AI-SYNTHESIZED belongs to orbis/ and describes nothing this pack authors'
# and no real local, employer or person is named
assert not re.search(r'\bLocal\s+\d|\bIBEW\b|\bUA\s+\d|\bLiUNA\b', _payload_text), \
    'no real union local, employer or person is named in a lesson'

# ----------------------------------------------------------------- build ---
stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
ALL_STEPS = [st for L in LESSONS.values() for st in L['steps']]
by_kind = {}
for st in ALL_STEPS:
    by_kind[st['kind']] = (by_kind[st['kind']] if st['kind'] in by_kind else 0) + 1
by_episode = {}
for st in ALL_STEPS:
    if st['records'] is not None:
        by_episode[st['records']] = (by_episode[st['records']] if st['records'] in by_episode else 0) + 1

doc = {
    'pack': 'smartcitix-trade-craft-academy-lessons',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'honesty': HONESTY,
    'counts': {
        'lessons': len(LESSONS),
        'lessons_by_hand': HAND_COUNT,
        'lessons_by_rule': RULE_COUNT,
        'arcs': len(ARCS),
        'halls_refused_by_rule': len(COMPOSE_REFUSED),
        'steps': len(ALL_STEPS),
        'step_kinds': len(STEP_KINDS),
        'steps_by_kind': {k: by_kind[k] for k in sorted(by_kind)},
        'recording_steps': sum(1 for st in ALL_STEPS if st['records'] is not None),
        'silent_steps': sum(1 for st in ALL_STEPS if st['records'] is None),
        'episodes_by_kind': {k: by_episode[k] for k in sorted(by_episode)},
        'episode_kinds_used': len(by_episode),
        'episode_kinds_declared': len(EPISODE_KINDS),
        'new_episode_kinds': 0,
        'halls_covered': len(HALLS_COVERED),
        'halls_total': len(HALLS),
        'strands_covered': len(STRANDS_COVERED),
        'strands_total': len(ROOM_LABEL),
        'rooms_stood_in': len({(L['hall'], L['strand']) for L in LESSONS.values()}),
        'campuses_covered': len({L['campus'] for L in LESSONS.values()}),
        'max_lessons_in_one_hall': MAX_IN_A_HALL,
        'stations_used': len({st['station'] for st in ALL_STEPS if 'station' in st}),
        'stations_total': STATIONS['count'],
        'sims_used': len({st['sim'] for st in ALL_STEPS if 'sim' in st}),
        'sims_total': len(SIMS['sims']),
        'scenarios_used': len({(st['sim'], st['scenario']) for st in ALL_STEPS
                               if 'scenario' in st}),
        'scenarios_total': sum(len(s['scenarios']) for s in SIMS['sims'].values()),
        'walkaround_points_used': len({(st['sim'], st['point']) for st in ALL_STEPS
                                       if 'point' in st}),
        'walkaround_points_total': sum(len(s['walkaround']) for s in SIMS['sims'].values()),
        'advisors_used': len({st['advisor'] for st in ALL_STEPS if 'advisor' in st}),
        'advisor_topics_used': len({(st['advisor'], st['topic']) for st in ALL_STEPS
                                    if 'advisor' in st}),
        'crews_used': len({st['crew'] for st in ALL_STEPS if 'crew' in st}),
        'crew_roles_used': len({(st['crew'], st['role']) for st in ALL_STEPS
                                if 'crew' in st}),
        'cribs_used': len({st['crib'] for st in ALL_STEPS if 'crib' in st}),
        'prerequisite_edges': len(EDGES),
        'ladder_roots': len(ROOTS),
        'ladder_depth': max(DEPTH.values()),
        'ladder_layers': len(LADDER_LAYERS),
        'edge_reasons': len(EDGE_REASONS),
        'files_read': len(_reads),
        'seat_bound_halls': len(SEAT_BOUND_HALLS),
        'seat_bound_halls_with_a_lesson': sum(1 for h in SEAT_BOUND_HALLS if h in _per_hall),
        'hazard_rooms_walked': sum(len(L['hazard_rooms_walked']) for L in LESSONS.values()),
        'hazard_room_placard_gaps': len(HAZARD_GAPS),
        'placard_steps': by_kind['placard'],
    },
    'spread': {
        'halls': HALLS_COVERED,
        'strands': STRANDS_COVERED,
        'max_hall_share': TOP_SHARE,
        'max_hall_share_ceiling': MAX_HALL_SHARE,
        'seat_bound_halls': SEAT_BOUND_HALLS,
        'composed_halls': sorted(L['hall'] for L in LESSONS.values() if L['authoring'] == 'rule'),
        'refused_by_rule': COMPOSE_REFUSED,
        'note': 'breadth over the trades rather than depth in one: the ceiling is declared, computed and failed against, and all 11 strands must be stood in or the build stops.',
    },
    'step_kinds': STEP_KINDS,
    'off_room_places': OFF_ROOM_PLACES,
    'composition': {
        'rule': 'a hall with no hand-written lesson gets exactly one arc, chosen by rotation over the roster order and falling through to the next arc when the first cannot be walked honestly there; the arc fixes the step kinds, the order and the notes, and the hall name, focus, rooms, placard, crib and advisors are read from the registries that own them.',
        'tier': COMPOSED_TIER,
        'arcs': {a['arc']: {'title': a['title'], 'kinds': [r[0].rstrip('?') for r in a['steps']],
                            'placard_if_the_record_asks_for_ppe': True} for a in ARCS},
        'provenance': 'steps and limits AUTHORED (written here once per arc); order, title and why DERIVED (chosen by the rule, not by a person for that hall); names READ.',
    },
    'plugs_into': {
        'loop': SCHOOLS['model']['loop'],
        'stages_used': _stages_used,
        'stages_left_alone': sorted(set(SCHOOL_STAGES) - set(_stages_used)),
        'how': 'a lesson is the class and floor halves of the existing loop made walkable, in the order somebody chose. It is not a fifth stage, it does not replace the module pack at home, and it never touches the unaided gate.',
    },
    'lessons': LESSONS,
    'ladder': {
        'edges': [{'lesson': a, 'needs': b, 'because': c} for a, b, c in EDGES],
        'reasons': EDGE_REASONS,
        'prerequisites': LADDER,
        'roots': ROOTS,
        'depth': DEPTH,
        'layers': LADDER_LAYERS,
        'acyclic': True,
        'enforcement': 'none. The ladder is a sensible order, not a permission system: no lesson is locked behind another and the page contract forbids the page from locking one.',
    },
    'page_contract': PAGE_CONTRACT,
    'reads': _reads,
}

# the counts are computed above and held against the things they count
assert doc['counts']['steps'] == sum(len(L['steps']) for L in LESSONS.values())
assert doc['counts']['recording_steps'] + doc['counts']['silent_steps'] == doc['counts']['steps']
assert doc['counts']['episode_kinds_used'] == doc['counts']['episode_kinds_declared']
assert sum(doc['counts']['steps_by_kind'].values()) == doc['counts']['steps']
assert sum(doc['counts']['episodes_by_kind'].values()) == doc['counts']['recording_steps']
assert doc['counts']['ladder_roots'] + len({a for a, _b, _c in EDGES}) == doc['counts']['lessons']
assert doc['counts']['seat_bound_halls_with_a_lesson'] == doc['counts']['seat_bound_halls'], \
    'a seat-bound hall has no lesson'
assert doc['counts']['hazard_room_placard_gaps'] == 0, 'a hazard room is walked without its placard'
assert doc['counts']['hazard_rooms_walked'] == sum(
    1 for L in LESSONS.values() for r in L['hazard_rooms_walked'] if r in L['placard_steps_in']), \
    'a hazard room walked is a hazard room placarded, or the gap count above lied'

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'lessons.json').write_text(json.dumps(doc, indent=1) + '\n')
c = doc['counts']
print(f"lessons: {c['lessons']} walkable lessons, {c['steps']} steps in "
      f"{c['step_kinds']} kinds, standing in {c['rooms_stood_in']} rooms across "
      f"{c['halls_covered']} of {c['halls_total']} halls and "
      f"{c['strands_covered']} of {c['strands_total']} strands "
      f"(top hall {TOP_SHARE:.2%} of the set, ceiling {MAX_HALL_SHARE:.0%}); "
      f"{c['recording_steps']} steps write one of the {c['episode_kinds_declared']} "
      f"episode kinds training/ already has and {c['silent_steps']} write nothing; "
      f"ladder {c['prerequisite_edges']} edges, {c['ladder_roots']} roots, "
      f"depth {c['ladder_depth']}, acyclic; every one of the {c['seat_bound_halls']} "
      f"seat-bound halls has a lesson, {c['hazard_rooms_walked']} hazard rooms walked and "
      f"{c['hazard_room_placard_gaps']} without a placard step; certifies nobody "
      f"(source stamp {stamp})")
