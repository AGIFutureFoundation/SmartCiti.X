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
BUILT = "2026-09-20"


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
   ('placard', 'coordination', 'The sign at the door is the room own condition record; read it before you decide what you are wearing is enough.'),
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
   ('placard', 'coordination', 'Read what the room is held to; it is a short sign and it is the only one that binds you.'),
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
   ('placard', 'documentation', 'Read the room record; this is a clean room in spirit even when it is not one on paper.'),
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
]

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
}

# The ceiling on concentration. Breadth over the trades is the claim, so
# the claim is given a number the build can fail against.
MAX_HALL_SHARE = 0.10

# ------------------------------------------------------------ the honesty ---
HONESTY = {
    'status': 'AUTHORED: every lesson, every step order and every sentence in this pack was written here, by us. Nothing is generated, nothing is fetched and no model runs behind any of it. The word AI-SYNTHESIZED belongs to orbis/ and describes generated video; it would be a false label for a hand-written walk through a building.',
    'content': 'unverified general practice. These lessons were written to be argued with, corrected and replaced by journey-level practitioners from the halls they name - the same standing the module pack, the recovered stations and the simulator seats already carry, and for the same reason: nobody who does this work for a living has reviewed a line of it yet.',
    'not_certification': 'no lesson here certifies anybody, qualifies anybody or permits anybody to do anything. Completing every lesson in this registry would leave a learner with exactly the standing they started with. Where a trade has a real ticket, that ticket is issued by a jurisdiction, an employer or a hall, and this bundle is none of those and speaks for none of them.',
    'not_a_gate': 'a lesson unlocks nothing. No step is locked behind another, the ladder is guidance about a sensible order rather than a permission system, and the assessment gate that schools/ declares stays exactly where it is: an unaided verification run that no lesson, station hour or simulator seat substitutes for.',
    'not_scored': 'finishing a lesson changes no score and is read by no grader. Four of the eight step kinds write an episode to the existing device-local training log; the other four write nothing at all, and the registry says which is which rather than leaving it to be discovered.',
    'one_truth': 'this pack holds no second copy of anything. Hall names, room labels, station names, seat names, scenario names, advisor names, crew role names and topic wordings are all read at build time from the registries that own them, and the test re-reads them the same way. A step that could not resolve its ids did not become a lesson with a footnote; it failed the build.',
    'no_jurisdiction': 'nothing here cites a standard, a code or an authority, and nothing here speaks for one. Where a step says what a crew would do, that is unverified general practice and not an instruction from anybody with the standing to give one.',
    'scope': 'this is a small set deliberately spread thin: a couple of dozen lessons across a couple of dozen halls, out of 111 halls and 1,221 rooms. It demonstrates the shape a lesson takes in this bundle. It is not a curriculum, it does not cover a trade, and no hall is finished because one of its rooms now has a lesson standing in it.',
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
        'provenance': {'steps': 'AUTHORED', 'order': 'AUTHORED',
                       'title': 'AUTHORED', 'why': 'AUTHORED',
                       'limits': 'AUTHORED', 'names': 'READ'},
    }

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
    _per_hall[L['hall']] = _per_hall.get(L['hall'], 0) + 1
MAX_IN_A_HALL = max(_per_hall.values())
TOP_SHARE = MAX_IN_A_HALL / len(LESSONS)
assert TOP_SHARE <= MAX_HALL_SHARE, \
    f'one hall holds {TOP_SHARE:.2%} of the lessons, over the declared {MAX_HALL_SHARE:.0%} ceiling'
assert len(STRANDS_COVERED) == len(ROOM_LABEL), \
    f'{len(STRANDS_COVERED)} of {len(ROOM_LABEL)} strands are covered; breadth means all of them'
assert len(HALLS_COVERED) >= 20, \
    f'{len(HALLS_COVERED)} halls is depth in a corner, not breadth over the trades'
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
    st = _state.get(node, 'new')
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

# the placard step kind leans on a sign this bundle already draws
assert 'placard' in LABELS['kinds'], \
    'the placard step reads a sign kind the labels pack no longer declares'

# the page this contract is written for still behaves the way it describes
for token in ('curRoom', 'hfocus', 'hint', "view = 'hall'", 'condLine', 'condOf'):
    assert token in PAGE_SRC, \
        f'the page contract names {token!r}, which the page no longer has'
# and it has not been wired yet, which is a fact rather than an omission
assert 'D.lessons' not in PAGE_SRC, \
    'the page now reads D.lessons: update this contract to describe what it actually does'

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
    by_kind[st['kind']] = by_kind.get(st['kind'], 0) + 1
by_episode = {}
for st in ALL_STEPS:
    if st['records'] is not None:
        by_episode[st['records']] = by_episode.get(st['records'], 0) + 1

doc = {
    'pack': 'smartcitix-trade-craft-academy-lessons',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'honesty': HONESTY,
    'counts': {
        'lessons': len(LESSONS),
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
    },
    'spread': {
        'halls': HALLS_COVERED,
        'strands': STRANDS_COVERED,
        'max_hall_share': round(TOP_SHARE, 4),
        'max_hall_share_ceiling': MAX_HALL_SHARE,
        'note': 'breadth over the trades rather than depth in one: the ceiling is declared, computed and failed against, and all 11 strands must be stood in or the build stops.',
    },
    'step_kinds': STEP_KINDS,
    'off_room_places': OFF_ROOM_PLACES,
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
      f"depth {c['ladder_depth']}, acyclic; certifies nobody "
      f"(source stamp {stamp})")
