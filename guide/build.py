#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the guide registry builder.

An advisor stands in a room and answers for that room. This pack declares
the other half of the same idea: a GUIDE, one helper a learner opens from
anywhere in the app - the region board, a campus green, a hall interior, a
seat, a restoration site, the avatar locker, or any of the four panels -
and asks the questions a person actually asks on arriving somewhere.

WHAT THE GUIDE IS. A scripted helper. No model runs behind it, nothing is
generated at view time, no network is reached, and every sentence it can
say is written in this file with the repo file it is grounded in named in
`cites`. It is the same closed book the advisors are, with one difference
of shape: an advisor is bound to a ROOM, so the page has to know where the
figure is standing; the guide is bound to a PLACE, which is the view the
learner is already in, so one click from anywhere lands on the right six
questions.

THE SIX QUESTIONS, AND WHY THEY ARE THE SAME SIX EVERYWHERE. A person who
has just arrived somewhere asks a small, stable set of things: what is
this, what can I do here, how do I move, how do I get back, what is this
measuring, and what is this not claiming. Those six are declared once as
ASK_SET and every place must answer all six - the build refuses a place
that skips one and refuses a place that invents a seventh. The last two
are the ones that matter most in a bundle like this: a learner who is
never told what a view measures will assume it measures them, and a
learner who is never told what a drawing does not claim will assume it
claims everything.

CONTROLS ARE A TABLE, NOT A SENTENCE. "Use the movement keys" is not help.
So the `move` topic of every place names a CONTROL SCHEME by id, and the
page renders that scheme's rows under the answer - the actual inputs, with
what each one does. Four schemes are written here (walking, the pointer,
touch, the XR rig) because they are the page's own behaviour rather than
any registry's, and every one of their key codes is asserted to appear in
the page source. The fifth and biggest set is not written here at all: a
seat's controls are READ from `sims/registry/sims.json`, which already
declares `controls` and an `xr` mapping per seat, and the seat place's
`move` topic binds to `seat:running` - resolved by the page against the
seat that is ACTUALLY running, exactly as the Operator advisor's `seat.*`
bindings already are. One truth per fact: change a seat's control scheme
in sims/ and the guide's answer changes with it, because the guide never
kept a copy.

VOICE, WHICH IS THE PART THAT NEEDED CARE. The page will offer two things
this bundle has never offered before: reading an answer aloud
(`speechSynthesis`) and asking by voice (`SpeechRecognition` /
`webkitSpeechRecognition`). The second one is not what it looks like. In
Chrome and Edge `webkitSpeechRecognition` does not recognise speech in the
page: it streams the captured audio to a speech service run by the
browser's own vendor. This bundle's whole doctrine is that nothing is
fetched and everything traces to a record, so shipping that quietly would
break the doctrine while appearing to keep it. Both features are therefore
OFF by default, each behind its own key, and each carries a BANNER that is
COMPUTED by joining its six declared honesty fields in a declared order -
so the text that goes in front of the switch cannot drift from the text
this registry publishes, because it is not a second copy of it. Chrome 139
and later can be asked for on-device recognition, and the declared policy
asks for it wherever it is offered and STOPS rather than falling back -
a default that fails closed, which is the same rule every other default in
this bundle is held to.

HANDS, DECLARED AND UNVERIFIED. The page's own XR note says what the XR
layer has and what it does not: no hand tracking, no rendered hands, and
no run on a physical headset - the layer is proved against a MOCKED WebXR
session in headless Chromium only. This pack does not pretend otherwise.
It declares the gestures a recogniser should implement - the joints, the
distance measured, the threshold that fires it and the separate distance
that releases it, so the thing that gets built is a declared gesture
rather than an invented one - and it labels every distance in the table
AUTHORED and the whole feature UNVERIFIED-ON-HARDWARE, because no headset
has been available to this build and a mocked session proves arithmetic
and nothing about a real hand.

WHAT THE GUIDE IS NOT. Not an instructor, not a certification, not a code
ruling, not a search box and not a chat: it cannot be asked an open
question because there is nothing behind it that could answer one. Not a
gate - opening it changes no score and unlocks nothing, and there is no
guide state for a grader to read. And the provenance word for all of it is
SCRIPTED. `orbis/` owns AI-SYNTHESIZED for generated video, and it would
be a false label for a table of hand-written sentences.
"""
import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

# One bundle version, read from the manifest rather than typed here.
PACK_VERSION = json.load(open(ROOT / 'pack/manifest.json'))['pack_version']
BUILT = "2026-09-20"

# The page is READ, never written, by this pack. Every claim below that is
# about the app's own behaviour - which views exist, which key codes a seat
# may use, what the XR layer admits to - is held against this text, so a
# guide answer cannot quietly describe a page that stopped behaving that
# way. There is deliberately no check in the other direction yet: the page
# has never seen this registry, and a two-way check with nowhere to start
# is the bootstrap problem agents/build.py already has to carry a flag for.
PAGE_SRC = (ROOT / 'web/build_3d.py').read_text()

# The seat control schemes are not written in this file. They are read from
# the simulator registry, which already declares `controls` (keys and the
# action each one drives) and an `xr` mapping per seat.
SIMS = json.load(open(ROOT / 'sims/registry/sims.json'))

# ------------------------------------------------------------- the asks ---
# The six questions a person asks on arriving somewhere. Declared once,
# required of every place, and closed: the build refuses a seventh.
ASK_SET = [
    {'id': 'what', 'asks': 'what this place is'},
    {'id': 'do', 'asks': 'what can be done here'},
    {'id': 'move', 'asks': 'how to move, with the control scheme named'},
    {'id': 'back', 'asks': 'how to get back out'},
    {'id': 'measures', 'asks': 'what, if anything, this place measures'},
    {'id': 'limits', 'asks': 'what this place does NOT claim'},
]
ASK_IDS = [a['id'] for a in ASK_SET]

# ----------------------------------------------------------- the places ---
# A place is a VIEW the page already has, or one of the four panels that
# overlay whichever view the learner was in. `view` names the page's own
# `view` variable value and is asserted against the page source; a panel
# carries no view because it does not change one.
PLACES = {
    'region': {
        'name': 'The region board',
        'kind': 'world',
        'view': 'region',
        'walkable': False,
        'opened_by': 'where the app starts, and the region button in the top bar from anywhere else',
        'what_line': 'the map of ten campuses the whole bundle hangs off',
        'topics': [
            {'id': 'what', 'ask': 'What am I looking at?',
             'cites': 'unions/registry/campuses.json',
             'answer': 'The region board: the ten campuses of the Academy, '
                       'drawn as plates on a map. Each plate is one campus, '
                       'and clicking one takes you inside it. This is the '
                       'top of the app - everything else in the bundle is '
                       'reached through a campus.'},
            {'id': 'do', 'ask': 'What can I do from up here?',
             'cites': 'web/build_3d.py',
             'answer': 'Pick a campus and go in. Nothing on the board is '
                       'locked and no order is imposed, so the campus you '
                       'start with is yours to choose. Candidate sites on '
                       'the board are not campuses and open their own note '
                       'instead.'},
            {'id': 'move', 'ask': 'How do I get around the board?',
             'scheme': 'pointer',
             'cites': 'web/build_3d.py',
             'answer': 'You do not walk here, because there is nothing to '
                       'walk on yet. Drag to turn the board, use the wheel '
                       'to come in or pull back, and click a plate to enter '
                       'that campus. Walking starts once you are standing '
                       'on a campus.'},
            {'id': 'back', 'ask': 'How do I come back to this view later?',
             'cites': 'web/build_3d.py',
             'answer': 'The region button in the top bar returns here from '
                       'any view in the app. It is the one control that '
                       'always goes up a level rather than sideways.'},
            {'id': 'measures', 'ask': 'Is the board scoring me on anything?',
             'cites': 'geo/registry/campuses_geo.json',
             'answer': 'No. Nothing on the region board is measured, scored '
                       'or recorded - it is a way in, not an exercise. What '
                       'the board does carry is one coordinate per campus, '
                       'and each of those carries the word that says how '
                       'well it is known.'},
            {'id': 'limits', 'ask': 'How real is this map?',
             'cites': 'geo/registry/campuses_geo.json',
             'answer': 'The coordinates are RECORDED or DERIVED for the '
                       'flagship campuses and AUTHORED for the hubs, and '
                       'each plate says which. The campuses themselves are '
                       'SCHEMATIC: no ground has been acquired, nothing has '
                       'been consented, and this is not a site plan or a '
                       'property map.'},
        ],
    },

    'campus': {
        'name': 'A campus',
        'kind': 'world',
        'view': 'campus',
        'walkable': True,
        'opened_by': 'clicking a campus plate on the region board',
        'what_line': 'the green, the ring of halls, the training yard and the restoration pins',
        'topics': [
            {'id': 'what', 'ask': 'What is this place?',
             'cites': 'unions/registry/campuses.json',
             'answer': 'One campus of the Academy: a plaza, a ring of trade '
                       'halls around it, a fenced training yard with a stand '
                       'for each seat this campus can run, and the chapter '
                       'hall. Which halls stand here is the campus\'s own '
                       'record, not a fixed list every campus shares.'},
            {'id': 'do', 'ask': 'What can I do on the green?',
             'cites': 'web/build_3d.py',
             'answer': 'Walk into any hall through its door, take a seat '
                       'straight off its stand in the training yard, open '
                       'the chapter hall, or follow a restoration pin out to '
                       'a site. Advisors stand on the green as well as '
                       'inside the halls, and either can be asked.'},
            {'id': 'move', 'ask': 'How do I walk around out here?',
             'scheme': 'walk-keyboard',
             'cites': 'web/build_3d.py',
             'answer': 'Press the walk button and the view becomes a body: '
                       'the movement keys walk, Shift runs, and the mouse '
                       'turns your head once the pointer is locked. Walk up '
                       'to a door, a seat stand or a place marker and the '
                       'bar tells you what Enter will open.'},
            {'id': 'back', 'ask': 'How do I get off this campus?',
             'cites': 'web/build_3d.py',
             'answer': 'The region button in the top bar takes you back to '
                       'the board. Escape releases the pointer lock and '
                       'hands the camera back without leaving the campus, '
                       'which is usually what you actually want.'},
            {'id': 'measures', 'ask': 'Does walking around here count for anything?',
             'cites': 'sims/registry/sims.json',
             'answer': 'No. Walking, looking and talking to advisors are '
                       'measured nowhere and change nothing. The only things '
                       'in this bundle that produce a score are the seats in '
                       'the yard and the crib check inside a hall, and both '
                       'say so before you start.'},
            {'id': 'limits', 'ask': 'Is this campus a real place?',
             'cites': 'geo/registry/campuses_geo.json',
             'answer': 'The city it sits in is real and the coordinate is '
                       'labelled with how well it is known. The campus is '
                       'SCHEMATIC - drawn to teach, not surveyed - and no '
                       'ground has been acquired, no building consented and '
                       'no partnership with anyone here is claimed.'},
        ],
    },

    'hall': {
        'name': 'A hall interior',
        'kind': 'world',
        'view': 'hall',
        'walkable': True,
        'opened_by': 'walking through a hall door on the campus green, or picking the hall from the campus',
        'what_line': 'the rooms of one trade hall, with advisors, a crib and the stations',
        'topics': [
            {'id': 'what', 'ask': 'Whose hall is this?',
             'cites': 'unions/registry/unions.json',
             'answer': 'One trade hall of the 111 this bundle draws, laid '
                       'out in rooms: induction, layout, materials, the '
                       'practice bays, inspection, coordination and the '
                       'documentation room. The rooms a hall gets are its '
                       'own record, so two halls are not the same building '
                       'with a different sign.'},
            {'id': 'do', 'ask': 'What is there to do in here?',
             'cites': 'agents/registry/advisors.json',
             'answer': 'Find the advisor standing in a room and ask what '
                       'that room is held to - the PPE, the hazards, the '
                       'light and air it is kept at. Run the crib check in '
                       'the tool room, walk the practice bays, and take any '
                       'seat this hall trains on.'},
            {'id': 'move', 'ask': 'How do I get around inside?',
             'scheme': 'walk-keyboard',
             'cites': 'web/build_3d.py',
             'answer': 'The same walk you use outside: the movement keys, '
                       'Shift to run, the mouse to look. Stand next to an '
                       'advisor and the ask button appears; stand at a '
                       'station or a crib and Enter opens it.'},
            {'id': 'back', 'ask': 'How do I get out of this hall?',
             'cites': 'web/build_3d.py',
             'answer': 'The campus button puts you back on the green '
                       'outside, and the region button goes all the way up '
                       'to the board. Escape lets go of the pointer without '
                       'leaving the room you are in.'},
            {'id': 'measures', 'ask': 'What in here is actually scored?',
             'cites': 'tools/registry/toolcribs.json',
             'answer': 'The crib check is scored, against the tools that '
                       'district\'s crib actually issues, and the seats this '
                       'hall trains on are scored against their own rubrics. '
                       'Everything else in the hall - the rooms, the '
                       'advisors, the walk itself - is not.'},
            {'id': 'limits', 'ask': 'Does this hall belong to anybody?',
             'cites': 'unions/registry/unions.json',
             'answer': 'No. The halls carry trade names, not the name of any '
                       'real union local, employer or training centre, and '
                       'no affiliation with one is claimed or implied. The '
                       'building is SCHEMATIC and the room layout teaches a '
                       'shape of work rather than reproducing a real shop.'},
        ],
    },

    'seat': {
        'name': 'A training seat',
        'kind': 'world',
        'view': 'sim',
        'walkable': False,
        'opened_by': 'taking a stand in the campus training yard, or starting the seat from inside its hall',
        'what_line': 'one machine simulator, its dash, its rubric and its walkaround',
        'topics': [
            {'id': 'what', 'ask': 'What have I just sat down in?',
             'cites': 'sims/registry/sims.json',
             'answer': 'One training seat: a single schematic machine with a '
                       'task, a set of controls, a dash of gauges and a '
                       'rubric that measures what you did. The seat you are '
                       'in declares all four itself, and the guide reads '
                       'them from that seat rather than keeping a copy.'},
            {'id': 'do', 'ask': 'What am I meant to be doing here?',
             'cites': 'sims/registry/sims.json',
             'answer': 'Walk the pre-shift points first, then run the task '
                       'the seat states. You can also hand the seat to the '
                       'scripted reference operator and watch it drive, at '
                       'the level the panel is set to, and take it back at '
                       'any time.'},
            {'id': 'move', 'ask': 'What do the controls do?',
             'scheme': 'seat:running',
             'cites': 'sims/registry/sims.json',
             'answer': 'Every seat declares its own keys and what each one '
                       'drives, and the table under this answer is that '
                       'seat\'s own list, read live from the seat you are '
                       'actually in. Space is the verb on every seat - hook, '
                       'trigger, place, call - and a headset gets the same '
                       'seat through its own declared mapping.'},
            {'id': 'back', 'ask': 'How do I get out of the seat?',
             'cites': 'web/build_3d.py',
             'answer': 'Escape leaves the seat and puts you back where you '
                       'took it from. In a headset the B or Y button does '
                       'the same thing. Leaving mid-run scores nothing and '
                       'costs nothing - an abandoned run is simply not a '
                       'run.'},
            {'id': 'measures', 'ask': 'What is this seat actually measuring?',
             'cites': 'sims/registry/sims.json',
             'answer': 'The rubric axes the seat itself declares, every one '
                       'of them computed from measured state - where things '
                       'ended up, what was exceeded, how long it took. '
                       'Nothing narrative moves a score, and neither does '
                       'what your avatar is wearing or how long you spent '
                       'talking to an advisor.'},
            {'id': 'limits', 'ask': 'Does time in this seat certify me?',
             'cites': 'sims/registry/sims.json',
             'answer': 'It does not. These are schematic single-machine '
                       'physics for practising control discipline, not '
                       'equipment simulators and not a substitute for seat '
                       'time on real iron. No run here counts toward any '
                       'certification, and this bundle issues none.'},
        ],
    },

    'restoration': {
        'name': 'A restoration site',
        'kind': 'world',
        'view': 'restoration',
        'walkable': True,
        'opened_by': 'the restoration button in the top bar, or a restoration pin on a campus',
        'what_line': 'a walkable bay-restoration site and the training tracks bound to it',
        'topics': [
            {'id': 'what', 'ask': 'Where am I now?',
             'cites': 'restoration/registry/restoration.json',
             'answer': 'A bay restoration site: a real, named place on the '
                       'water, drawn schematically and walkable, with the '
                       'training tracks that would be worked there marked on '
                       'the ground. The site list and the tracks are one '
                       'registry, and the page draws what that registry '
                       'holds.'},
            {'id': 'do', 'ask': 'What is there to do at a site?',
             'cites': 'restoration/registry/restoration.json',
             'answer': 'Walk the site and open the track markers. Each track '
                       'names the trade skills that work would draw on, '
                       'which is the link back to the halls - a site is a '
                       'reason for a skill rather than another exercise.'},
            {'id': 'move', 'ask': 'How do I walk the site?',
             'scheme': 'walk-keyboard',
             'cites': 'web/build_3d.py',
             'answer': 'Exactly as you walk a campus: the movement keys, '
                       'Shift to run, the mouse to look. Stand at a track '
                       'marker and the bar tells you what Enter will open. '
                       'The site is bounded, so you cannot walk off it.'},
            {'id': 'back', 'ask': 'How do I leave the site?',
             'cites': 'web/build_3d.py',
             'answer': 'Escape leaves the site walk and hands you back to '
                       'the view you arrived from. The campus and region '
                       'buttons in the top bar work here the same as they do '
                       'anywhere else.'},
            {'id': 'measures', 'ask': 'Is anything measured out here?',
             'cites': 'restoration/registry/restoration.json',
             'answer': 'Nothing. A restoration site records no score and '
                       'gates nothing - it exists to put the work somewhere '
                       'real rather than to test you on it. The seats remain '
                       'the only things in this bundle that measure.'},
            {'id': 'limits', 'ask': 'Is this what the site really looks like?',
             'cites': 'restoration/registry/restoration.json',
             'answer': 'No. The place and its coordinate are real and '
                       'labelled; the ground, the water line and the '
                       'planting you are walking through are SCHEMATIC and '
                       'are not a survey, a design or a restoration plan. No '
                       'programme named here has reviewed or agreed to any '
                       'of it.'},
        ],
    },

    'locker': {
        'name': 'The avatar locker',
        'kind': 'world',
        'view': 'avatar',
        'walkable': False,
        'opened_by': 'the avatar button in the top bar',
        'what_line': 'the turntable where a learner builds the figure they walk as',
        'topics': [
            {'id': 'what', 'ask': 'What is this screen?',
             'cites': 'avatars/registry/avatars.json',
             'answer': 'The locker: a turntable with your figure on it and '
                       'the sections that make it up - build, face, hair, '
                       'headwear, top, vest, trousers, boots, tools, outer '
                       'layer, extras and crew marks. Every option is '
                       'declared in one registry, and the advisors and crews '
                       'are dressed from the same list you are.'},
            {'id': 'do', 'ask': 'What can I change in here?',
             'cites': 'avatars/registry/avatars.json',
             'answer': 'Any section, in any order, as often as you like. You '
                       'can play an emote to see how it moves, and you can '
                       'download the figure as a .glb to use elsewhere.'},
            {'id': 'move', 'ask': 'Why can I not walk in here?',
             'scheme': 'pointer',
             'cites': 'web/build_3d.py',
             'answer': 'Because there is nowhere to walk: the locker is a '
                       'turntable, not a room, and the walk control is '
                       'switched off while it is open. Drag to turn the '
                       'figure and use the wheel to come closer.'},
            {'id': 'back', 'ask': 'How do I get back to the world?',
             'cites': 'web/build_3d.py',
             'answer': 'The campus or region button in the top bar. Whatever '
                       'you changed is already applied - there is no save '
                       'step and nothing to confirm.'},
            {'id': 'measures', 'ask': 'Does any of this affect my score?',
             'cites': 'sims/registry/sims.json',
             'answer': 'None of it. No rubric, grader or gate in this bundle '
                       'reads a single thing about your figure, including '
                       'the crew marks, and no option is locked behind '
                       'anything you have done. The look is yours and it is '
                       'only a look.'},
            {'id': 'limits', 'ask': 'Do the crew marks mean anything?',
             'cites': 'avatars/registry/avatars.json',
             'answer': 'Not outside this bundle. The marks and crew colours '
                       'are the Academy\'s own, not the insignia of any real '
                       'union, employer or trade body, and wearing one '
                       'claims no membership and no qualification. The hand '
                       'emotes borrow the yard\'s vocabulary and confer '
                       'nothing either.'},
        ],
    },

    'panel-records': {
        'name': 'The records panel',
        'kind': 'panel',
        'view': None,
        'walkable': False,
        'opened_by': 'the records button in the top bar',
        'what_line': 'every run, pass and best time this browser has kept',
        'topics': [
            {'id': 'what', 'ask': 'What is this panel showing me?',
             'cites': 'web/build_3d.py',
             'answer': 'Your record: how many times you have run each seat, '
                       'whether it has ever been passed, your best time on '
                       'it, and the same three for the crib checks. It also '
                       'counts the stations you have opened and the '
                       'walkaround points you have marked.'},
            {'id': 'do', 'ask': 'What can I do with it?',
             'cites': 'training/registry/training.json',
             'answer': 'Export the whole record as JSON, import one back, or '
                       'clear it. The episode recorder\'s switches live here '
                       'too, and the sweep that has the scripted reference '
                       'operator drive every seat is one button.'},
            {'id': 'move', 'ask': 'Where am I while this is open?',
             'scheme': 'panel',
             'cites': 'web/build_3d.py',
             'answer': 'Exactly where you were: a panel slides in over the '
                       'view and the view underneath is untouched. Close it '
                       'and you are back in the same spot, facing the same '
                       'way.'},
            {'id': 'back', 'ask': 'How do I close it?',
             'cites': 'web/build_3d.py',
             'answer': 'The close button in the corner of the panel, or the '
                       'same top-bar button you opened it with. Closing it '
                       'keeps everything - the record is already written, '
                       'and there is no save step to miss.'},
            {'id': 'measures', 'ask': 'Where does this record live?',
             'cites': 'training/registry/training.json',
             'answer': 'In this browser and nowhere else. Nothing here is '
                       'uploaded, there is no account to upload it to, and '
                       'no server in this bundle has ever been asked for it. '
                       'Clear the site data and the record is gone, which is '
                       'the price of it never having left.'},
            {'id': 'limits', 'ask': 'Is a pass in here worth anything?',
             'cites': 'sims/registry/sims.json',
             'answer': 'Inside this bundle it is a record of what you '
                       'practised. Outside it, it is not a certificate, a '
                       'licence, a card or a transcript, and no body has '
                       'agreed to recognise it. The Academy certifies '
                       'nothing by itself.'},
        ],
    },

    'panel-schools': {
        'name': 'The schools panel',
        'kind': 'panel',
        'view': None,
        'walkable': False,
        'opened_by': 'the schools button in the top bar',
        'what_line': 'the flipped-classroom programme, its stages, bands and proposed districts',
        'topics': [
            {'id': 'what', 'ask': 'What is this programme?',
             'cites': 'schools/registry/schools.json',
             'answer': 'The schools side of the Academy: the stages a '
                       'partnership would run through, the age bands it '
                       'would offer at, the districts named as candidates, '
                       'and which hall each school unit would sit against. '
                       'It is a written proposal, not a running programme.'},
            {'id': 'do', 'ask': 'What can I do with this?',
             'cites': 'schools/registry/schools.json',
             'answer': 'Read it, and jump from any unit straight to the hall '
                       'it is bound to. It is a proposal you can walk '
                       'through rather than a form to fill in, and nothing '
                       'in it asks you for anything.'},
            {'id': 'move', 'ask': 'Do I lose my place while I read this?',
             'scheme': 'panel',
             'cites': 'web/build_3d.py',
             'answer': 'No. The panel is an overlay; the view behind it '
                       'stays exactly as you left it. Following a link to a '
                       'hall does change the view, deliberately.'},
            {'id': 'back', 'ask': 'How do I close it?',
             'cites': 'web/build_3d.py',
             'answer': 'The close button in the corner, or the same top-bar '
                       'button again. Nothing in the panel is a form, so '
                       'there is nothing to lose by closing it.'},
            {'id': 'measures', 'ask': 'Is any of this tracking me?',
             'cites': 'training/registry/training.json',
             'answer': 'No. The schools panel reads a registry and records '
                       'nothing at all - no score, no episode, no visit '
                       'count. Nothing you do in it is kept even locally.'},
            {'id': 'limits', 'ask': 'Are these districts actually partners?',
             'cites': 'schools/registry/schools.json',
             'answer': 'No. Every district named is recorded as a PROPOSED '
                       'partner and the registry says so on every single '
                       'entry. None has been approached, reviewed this, or '
                       'agreed to any of it, and no endorsement by any '
                       'district, school or board is claimed.'},
        ],
    },

    'panel-chapters': {
        'name': 'The chapters panel',
        'kind': 'panel',
        'view': None,
        'walkable': False,
        'opened_by': 'the chapter hall on a campus green',
        'what_line': 'which campus hosts the chapter of each hall that is not at home here',
        'topics': [
            {'id': 'what', 'ask': 'What is a chapter hall?',
             'cites': 'unions/registry/chapters.json',
             'answer': 'Every one of the 111 halls has one campus it is at '
                       'home on. The chapter hall on a campus green lists '
                       'the halls whose home is elsewhere but which keep a '
                       'chapter here, grouped by the campus they came from.'},
            {'id': 'do', 'ask': 'What is this list for?',
             'cites': 'unions/registry/chapters.json',
             'answer': 'It answers "why is this trade not here" without '
                       'making you check ten campuses. The trade is '
                       'somewhere, the list says where, and the region board '
                       'gets you there.'},
            {'id': 'move', 'ask': 'Where am I while this is up?',
             'scheme': 'panel',
             'cites': 'web/build_3d.py',
             'answer': 'Still on the campus green you opened it from, with '
                       'the view untouched behind the panel. Closing it puts '
                       'you back with nothing changed.'},
            {'id': 'back', 'ask': 'How do I close it?',
             'cites': 'web/build_3d.py',
             'answer': 'The close button in the corner of the panel, or the '
                       'chapter hall itself again. You are handed straight '
                       'back to the green you were standing on.'},
            {'id': 'measures', 'ask': 'Does this track what I read?',
             'cites': 'training/registry/training.json',
             'answer': 'No. Opening the chapter hall records nothing, scores '
                       'nothing and unlocks nothing, and it is not read by '
                       'any grader. It is a list, built from a registry, '
                       'and that is all it is.'},
            {'id': 'limits', 'ask': 'Are these real chapters?',
             'cites': 'unions/registry/chapters.json',
             'answer': 'No. The hosting is this bundle\'s own arrangement of '
                       'its own halls, not a description of where any real '
                       'union local, chapter or district actually sits. No '
                       'real local is named anywhere in it.'},
        ],
    },

    'panel-orbis': {
        'name': 'The orbis panel',
        'kind': 'panel',
        'view': None,
        'walkable': False,
        'opened_by': 'the orbis button in the top bar, while standing in a hall',
        'what_line': 'the deterministic video prompt this bundle writes for a hall, and never runs',
        'topics': [
            {'id': 'what', 'ask': 'What does this panel make?',
             'cites': 'orbis/registry/orbis.json',
             'answer': 'A text prompt for a video model, built deterministically '
                       'from the hall you are standing in. The panel writes '
                       'text and only text - it never calls a model, and '
                       'nothing on this page has ever produced a frame of '
                       'video.'},
            {'id': 'do', 'ask': 'What am I supposed to do with the prompt?',
             'cites': 'orbis/registry/orbis.json',
             'answer': 'Copy it, or export the full set for all 111 halls. '
                       'Running it is a separate, deliberate step somebody '
                       'takes on their own machine with their own key, and '
                       'the panel names the runners that would do it.'},
            {'id': 'move', 'ask': 'Where am I while this is open?',
             'scheme': 'panel',
             'cites': 'web/build_3d.py',
             'answer': 'In the hall you opened it from - the panel overlays '
                       'the view and changes nothing behind it. The prompt '
                       'is built for that hall, so which hall you are '
                       'standing in matters.'},
            {'id': 'back', 'ask': 'How do I close it?',
             'cites': 'web/build_3d.py',
             'answer': 'The close button in the corner, or the same top-bar '
                       'button again. The prompt is rebuilt every time you '
                       'open it, so nothing is lost by closing it.'},
            {'id': 'measures', 'ask': 'Does this panel send anything anywhere?',
             'cites': 'orbis/registry/orbis.json',
             'answer': 'Nothing. No network call is made from this page for '
                       'any of it, no key is held here, and nothing is '
                       'recorded when you open it. The text is built in the '
                       'page from registries already in the bundle.'},
            {'id': 'limits', 'ask': 'Is the video this describes real footage?',
             'cites': 'orbis/registry/orbis.json',
             'answer': 'It would not be. Anything generated from these '
                       'prompts is AI-SYNTHESIZED - that is the word this '
                       'bundle keeps for exactly this and for nothing else - '
                       'and it is not footage of real work, real workers or '
                       'real equipment. Nothing generated from it may be '
                       'presented as a record of anything that happened.'},
        ],
    },
}

# --------------------------------------------------------- the controls ---
# Four schemes are written here because they are the PAGE's own behaviour
# and no registry declares them; every key code in them is asserted to
# appear in the page source below, so a scheme cannot describe an input the
# app does not read. The fifth set - one per seat - is not written here at
# all: it is READ from sims/ further down.
#
# `codes` is what makes a row checkable. It lists the exact tokens the page
# must contain for the row to be true: KeyboardEvent.code values for a key
# row, and the API or handler name for a pointer, touch or XR row.
SHARED_CONTROLS = {
    'walk-keyboard': {
        'name': 'Walking',
        'where': 'a campus green, a hall interior or a restoration site, once the walk button is pressed',
        'source': 'web/build_3d.py',
        'rows': [
            {'input': 'W / S, or Up / Down',
             'does': 'walk forward and back; the back-pedal is capped below the forward walk',
             'codes': ['KeyW', 'KeyS', 'ArrowUp', 'ArrowDown']},
            {'input': 'A / D, or Left / Right',
             'does': 'step left and right without turning',
             'codes': ['KeyA', 'KeyD', 'ArrowLeft', 'ArrowRight']},
            {'input': 'Shift, held',
             'does': 'run, forward only - it buys nothing going backwards',
             'codes': ['ShiftLeft', 'ShiftRight']},
            {'input': 'Mouse, once the pointer is locked',
             'does': 'turn your head; the body follows where you look',
             'codes': ['PointerLockControls']},
            {'input': 'Enter, or E',
             'does': 'open whatever you are standing at - a hall door, a seat stand, a place marker, a restoration track',
             'codes': ['Enter', 'KeyE']},
            {'input': 'Escape',
             'does': 'release the pointer, and leave a seat or a site walk if you are in one',
             'codes': ['Escape']},
        ],
    },
    'pointer': {
        'name': 'Mouse and pointer',
        'where': 'the region board, a campus or hall you are not walking in, and the avatar locker',
        'source': 'web/build_3d.py',
        'rows': [
            {'input': 'Drag',
             'does': 'orbit the view around what is in front of you; the idle drift stops the moment you do',
             'codes': ['OrbitControls', 'autoRotate']},
            {'input': 'Wheel',
             'does': 'come closer or pull back, between the near and far limits the view is held to',
             'codes': ['minDistance', 'maxDistance']},
            {'input': 'Click',
             'does': 'open whatever is under the pointer - a campus plate, a hall door, an advisor, a station, a chapter hall, a restoration pin',
             'codes': ['pointerdown', 'pickWith']},
            {'input': 'Hover',
             'does': 'name the thing under the pointer without opening it',
             'codes': ['pointermove']},
        ],
    },
    'touch': {
        'name': 'Touch',
        'where': 'a touch device, where walking is third-person rather than first',
        'source': 'web/build_3d.py',
        'rows': [
            {'input': 'Left thumb stick',
             'does': 'move your figure; you watch it from behind rather than through its eyes',
             'codes': ['joyVec', 'touchWalkStep']},
            {'input': 'Drag on the right of the screen',
             'does': 'turn the view around your figure',
             'codes': ['tYaw', 'tPitch']},
            {'input': 'Tap',
             'does': 'the same as a click: open whatever you tapped',
             'codes': ['pointerdown', 'pickWith']},
            {'input': 'The action button',
             'does': 'open what you are standing at, the way Enter does on a keyboard',
             'codes': ['actBtn']},
            {'input': 'The emote button',
             'does': 'open the emote wheel and play a gesture',
             'codes': ['emoBtn', 'wheelShow']},
        ],
    },
    'xr-rig': {
        'name': 'In a headset, outside a seat',
        'where': 'an immersive VR or AR session, while walking rather than driving a seat',
        'source': 'web/build_3d.py',
        'rows': [
            {'input': 'Left thumb stick',
             'does': 'walk the rig in the direction you are looking',
             'codes': ['xrMove']},
            {'input': 'Right thumb stick, left or right',
             'does': 'snap-turn a fixed step per flick - deliberately not a smooth spin, which is the comfort default',
             'codes': ['xrSnap', 'XR_SNAP']},
            {'input': 'Left trigger',
             'does': 'point and pick: the ray opens exactly what a click would',
             'codes': ['xrPickLeft']},
            {'input': 'B / Y button',
             'does': 'end the session and put the headset down',
             'codes': ['ses.end()']},
        ],
    },
    'panel': {
        'name': 'A panel',
        'where': 'any of the four panels, which overlay whichever view you were in',
        'source': 'web/build_3d.py',
        'rows': [
            {'input': 'The close button in the panel corner',
             'does': 'close the panel and hand the view back untouched',
             'codes': ['pclose']},
            {'input': 'The same top-bar button again',
             'does': 'close the panel that button opened, without touching the view behind it',
             'codes': ['barbtn']},
        ],
    },
}

# ------------------------------------------------------------- the voice ---
# Two features, one shape. Each declares the SAME six honesty fields, in
# the same order, and the banner the page puts in front of the switch is
# COMPUTED by joining them - so there is exactly one copy of each sentence
# and the banner cannot drift from what this registry publishes.
VOICE_FIELDS = ('opt_in', 'leaves_the_device', 'not_ours', 'no_audio_kept',
                'on_device', 'unavailable')

VOICE = {
    'read_aloud': {
        'title': 'Read the answer aloud',
        'api': 'window.speechSynthesis with SpeechSynthesisUtterance',
        'default': 'off',
        'storage_key': 'tc-guide-voice-out',
        'opt_in': 'Reading an answer aloud is OFF until you switch it on, '
                  'and the switch is this browser\'s own.',
        'leaves_the_device': 'It is usually local and not always: most '
                             'speechSynthesis voices are installed on the '
                             'machine, but some platforms offer network '
                             'voices, where the text of the answer is sent '
                             'to the voice vendor to be spoken.',
        'not_ours': 'Where the voice is a network one, this bundle neither '
                    'operates nor can see the service that speaks it; '
                    'SpeechSynthesisVoice.localService is the only thing '
                    'that says which kind you have, and the guide shows it '
                    'rather than claiming local.',
        'no_audio_kept': 'Nothing is recorded: reading aloud captures no '
                         'microphone input, stores no audio, and hands the '
                         'browser only the text of an answer that is '
                         'already written in this registry.',
        'on_device': 'The guide prefers a voice whose localService is true, '
                     'and where the only voice available is a network one '
                     'it says so before it speaks rather than after.',
        'unavailable': 'Where the browser exposes no speechSynthesis, or '
                       'exposes it with no voice for your language, the '
                       'control is absent rather than degraded, and the '
                       'answer stays on screen exactly as written.',
    },
    'ask_by_voice': {
        'title': 'Ask the guide by voice',
        'api': 'SpeechRecognition, or webkitSpeechRecognition where that is '
               'the only name offered',
        'default': 'off',
        'storage_key': 'tc-guide-voice-in',
        'opt_in': 'Asking by voice is OFF until you switch it on, and it '
                  'stays off: the switch is this browser\'s own and nothing '
                  'in this bundle turns it on for you.',
        'leaves_the_device': 'Switching it on sends your recorded voice off '
                             'this device. Chrome and Edge do not recognise '
                             'speech inside the page - they stream the '
                             'captured audio to a speech service run by the '
                             'browser\'s own vendor, and Safari sends it to '
                             'its vendor\'s service in the same way.',
        'not_ours': 'This bundle neither operates that service, pays for '
                    'it, nor can see what it receives, keeps or does with '
                    'it; all that comes back into this page is a line of '
                    'text, and what happened to the audio is between you '
                    'and your browser\'s vendor.',
        'no_audio_kept': 'This bundle stores no audio anywhere: nothing is '
                         'written to this browser\'s storage, nothing is '
                         'uploaded by us, and the recognised words are used '
                         'once to pick a topic and then dropped.',
        'on_device': 'Chrome 139 and later can be asked to recognise on the '
                     'device instead - availableOnDevice() and '
                     'processLocally - and the guide asks for that wherever '
                     'it is offered; if the language pack is missing the '
                     'request fails with language-not-supported, and the '
                     'guide stops there and says so rather than quietly '
                     'retrying through the vendor\'s service.',
        'unavailable': 'Where the browser offers neither constructor - '
                       'Firefox, which ships it disabled, and anything '
                       'older - the control is absent rather than degraded: '
                       'nothing here substitutes another service for the '
                       'one your browser declined to provide.',
    },
}

VOICE_STORAGE = {
    'read_aloud_key': 'tc-guide-voice-out',
    'ask_by_voice_key': 'tc-guide-voice-in',
    'values': "'1' for on, '0' for off - the same one-character shape the "
              'training toggles already use',
    'default': 'absent, and an absent key reads as OFF. A missing key is '
               'never read as consent, which is the only safe direction for '
               'a default that turns a microphone on.',
    'scope': 'this browser only - localStorage, wrapped so a blocked store '
             'never breaks the page, exactly like tc-progress',
    'not_kept': 'neither key ever holds audio, a transcript or anything a '
                'learner said: each holds the state of its own switch and '
                'nothing else',
}

# -------------------------------------------------------------- the hands ---
# The 25 joints WebXR Hand Input defines. Every joint a gesture names is
# checked against this list, so a gesture cannot be declared against a
# joint that does not exist - the thumb, notably, has no intermediate
# phalanx and a gesture that reached for one would be nonsense.
HAND_JOINTS = ['wrist']
for _f in ('thumb', 'index-finger', 'middle-finger', 'ring-finger', 'pinky-finger'):
    HAND_JOINTS.append(f'{_f}-metacarpal')
    HAND_JOINTS.append(f'{_f}-phalanx-proximal')
    if _f != 'thumb':                 # the thumb has no intermediate phalanx
        HAND_JOINTS.append(f'{_f}-phalanx-intermediate')
    HAND_JOINTS.append(f'{_f}-phalanx-distal')
    HAND_JOINTS.append(f'{_f}-tip')

# Every gesture declares the joints it measures between, the distance that
# fires it and the SEPARATE distance that releases it. Two different
# numbers is the whole point: one threshold makes a gesture chatter on and
# off at the boundary, which on a `stop` gesture is a safety bug rather
# than a polish one.
GESTURES = {
    'pinch-select': {
        'name': 'Pinch to select',
        'hand': 'either',
        'does': 'select whatever the hand is aimed at - the same pick the '
                'left controller trigger already does: a door, an advisor, '
                'a station, a crib, a campus plate',
        'where': ['campus', 'hall', 'restoration'],
        'joints': ['thumb-tip', 'index-finger-tip'],
        'measure': 'the distance between the two tips; fires when it falls '
                   'below the threshold, releases when it rises back above '
                   'the release distance',
        'threshold_m': 0.020,
        'release_m': 0.035,
        'hold_ms': 0,
    },
    'point-move': {
        'name': 'Point to move',
        'hand': 'either',
        'does': 'walk the rig in the direction the index finger points, at '
                'the same speed the left thumb stick is capped at, for as '
                'long as the point is held',
        'where': ['campus', 'hall', 'restoration'],
        'joints': ['index-finger-tip', 'index-finger-metacarpal',
                   'middle-finger-tip', 'middle-finger-metacarpal',
                   'ring-finger-tip', 'ring-finger-metacarpal',
                   'pinky-finger-tip', 'pinky-finger-metacarpal'],
        'measure': 'the index tip\'s distance from its own metacarpal, while '
                   'the middle, ring and little tips are each within the '
                   'curl distance of theirs; fires above the threshold, '
                   'releases when the index tip comes back inside the '
                   'release distance',
        'threshold_m': 0.090,
        'release_m': 0.075,
        'hold_ms': 120,
        'curl_m': 0.060,
    },
    'open-palm-stop': {
        'name': 'Open palm to stop',
        'hand': 'either',
        'does': 'stop: zero the walk command and let go of every key the '
                'hand is holding - the hand\'s version of taking your hand '
                'off the stick, and the one gesture that needs no aim',
        'where': ['campus', 'hall', 'restoration'],
        'joints': ['wrist', 'thumb-tip', 'index-finger-tip',
                   'middle-finger-tip', 'ring-finger-tip', 'pinky-finger-tip'],
        'measure': 'every one of the five tips farther from the wrist than '
                   'the threshold, held for the hold time; releases when any '
                   'tip comes back inside the release distance',
        'threshold_m': 0.090,
        'release_m': 0.075,
        'hold_ms': 250,
    },
    'palm-up-guide': {
        'name': 'Palm up to open the guide',
        'hand': 'either',
        'does': 'open this guide, on the place you are standing in, without '
                'having to find a button - which is the whole point of a '
                'helper that is meant to be reachable from anywhere',
        'where': ['campus', 'hall', 'restoration'],
        'joints': ['wrist', 'thumb-tip', 'index-finger-tip',
                   'middle-finger-tip', 'ring-finger-tip', 'pinky-finger-tip',
                   'index-finger-metacarpal', 'pinky-finger-metacarpal'],
        'measure': 'the open palm above, plus the palm normal - taken from '
                   'the wrist and the two outer metacarpals - within the '
                   'declared angle of world up, held for the hold time',
        'threshold_m': 0.090,
        'release_m': 0.075,
        'hold_ms': 500,
        'angle_deg': 35,
    },
}

HAND_HONESTY = {
    'status': 'UNVERIFIED-ON-HARDWARE: no headset has been available to '
              'this build, so not one of these gestures has been made by a '
              'real hand in a real session. They are declared to be '
              'implemented and tested against a MOCKED WebXR session only.',
    'mocked_only': 'a mocked session reports whatever joint poses the test '
                   'hands it, which proves the arithmetic - the distances, '
                   'the hysteresis, the hold timers - and proves nothing '
                   'whatever about tracking quality, occlusion, latency, or '
                   'whether a person can comfortably hold the shape.',
    'declared_not_built': 'this table is a contract for the page to '
                          'implement, not a description of what the page '
                          'does today: its own XR note lists hand tracking '
                          'among the things that do not exist in it yet, '
                          'and this registry does not claim otherwise.',
    'thresholds_are_authored': 'every distance and angle here is AUTHORED - '
                               'typed from general practice, not measured '
                               'against a hand on hardware - and is '
                               'expected to move once a headset is '
                               'available to check it against.',
    'not_a_gate': 'no gesture scores anything, unlocks anything or is '
                  'recorded: the recogniser runs only inside a session that '
                  'was granted hand tracking, and off entirely otherwise.',
}

# ------------------------------------------------------------- the pack ---
CONTRACT = (
    'the guide answers six fixed questions about the place the learner is '
    'already in, and nothing else. Every answer is a sentence written in '
    'this registry with the repo file it is grounded in named in `cites`; '
    'the only thing read at view time is a control scheme, and the biggest '
    'one - a seat\'s own keys and its XR mapping - is read from the '
    'simulator registry rather than copied here. Nothing is generated, no '
    'model runs behind it, and the guide itself reaches no network.'
)

HONESTY = {
    'status': 'SCRIPTED: the guide is a hand-written, deterministic script '
              '- a fixed set of places, six fixed questions each, and one '
              'fixed answer to each. No model runs behind it, nothing is '
              'generated at view time, and the guide reaches no network of '
              'its own.',
    'closed_book': 'the guide cannot be asked an open question because it '
                   'has no way to answer one. The topics below are all of '
                   'them, and the suite counts them; asking by voice picks '
                   'one of these same topics and never produces a new '
                   'answer.',
    'not_advice': 'nothing the guide says is a certification, a permit, a '
                  'code ruling or a substitute for the qualified person on '
                  'site; where it states a duty it states it as this '
                  'Academy teaches it, not as any jurisdiction\'s law.',
    'not_scored': 'opening the guide changes no score and unlocks nothing: '
                  'no grader reads guide state, and there is no guide state '
                  'for one to read.',
    'device_local': 'the guide keeps two things in this browser and nothing '
                    'else: whether each of the two voice switches is on. No '
                    'question you ask it, by hand or by voice, is recorded '
                    'anywhere.',
    'voice': 'both voice features are off by default and opt-in, and each '
             'carries its own banner stating exactly what leaves the device '
             'when it is on. Asking by voice sends captured audio to a '
             'speech service run by the browser\'s vendor, which this '
             'bundle neither operates nor can see.',
    'hands': 'the hand gestures are declared, not proved: no headset has '
             'been available to this build, and they are declared to be '
             'implemented and tested against a mocked XR session only.',
}

PAGE_CONTRACT = {
    'data': 'D.guide, alongside D.advisors.who and D.crews.crews',
    'button': 'one control, visible in every view and over every panel - '
              'the guide is the only thing in this bundle that is reachable '
              'from everywhere, which is what makes it a guide rather than '
              'a sixth panel',
    'route': 'the page\'s own `view` maps to a place id, and a place id is '
             'the whole routing: region, campus, hall, sim, restoration and '
             'avatar are the six world places, and an open panel selects '
             'its own place instead',
    'ask': 'the six asks of that place render as six buttons; nothing '
           'accepts free text, because there is nothing behind it that '
           'could answer free text',
    'controls': 'the `move` topic names a scheme id - the page renders that '
                'scheme\'s rows under the answer, and the special id '
                'seat:running is resolved against D.sims.sims[curSimId] at '
                'view time, never copied',
    'voice': 'two switches, each behind its own computed banner read from '
             'D.guide.voice, each writing only its own key; the ask-by-'
             'voice switch is absent, not disabled, where the browser '
             'offers no recognition constructor',
    'hands': 'a recogniser built from D.guide.hands.gestures, run only '
             'inside an immersive session that was granted the '
             'hand-tracking feature, and not built at all otherwise',
    'episode': 'nothing is recorded. The guide writes no episode, and the '
               'only thing it ever puts in storage is the state of its two '
               'voice switches',
}

# ---------------------------------------------------------------- checks ---
# Each block below is a claim this pack makes about itself, turned into the
# assertion that would catch it becoming false.

# -- the asks are closed, and every place answers all six, in order
assert len(ASK_IDS) == len(set(ASK_IDS)), 'a duplicate ask id'
for pid, p in PLACES.items():
    got = [t['id'] for t in p['topics']]
    assert got == ASK_IDS, \
        f'{pid}: answers {got}, but the ask set is {ASK_IDS}'
    assert p['kind'] in ('world', 'panel'), f'{pid}: unknown kind'
    assert isinstance(p['walkable'], bool), f'{pid}: walkable is a decision'
    assert len(p['opened_by']) > 20 and len(p['what_line']) > 20, \
        f'{pid}: a place needs to say how it is reached and what it is'

# -- a world place names a view the page actually sets; a panel names none
for pid, p in PLACES.items():
    if p['kind'] == 'world':
        assert p['view'], f'{pid}: a world place is a view'
        assert f"view = '{p['view']}'" in PAGE_SRC, \
            f'{pid}: the page never sets view = {p["view"]!r}'
    else:
        assert p['view'] is None, f'{pid}: a panel does not change the view'

# -- and every view the page sets has exactly one place speaking for it, or
# -- a learner can land somewhere the guide has never heard of
page_views = set(re.findall(r"view = '([a-z]+)'", PAGE_SRC))
declared_views = {p['view'] for p in PLACES.values() if p['view']}
assert page_views == declared_views, \
    f'views the guide cannot speak for: {sorted(page_views - declared_views)}'

# -- every topic is a question, is grounded in a file that EXISTS, and is
# -- two to four plain sentences: one is a slogan, five is a lecture
_SENT = re.compile(r'(?<=[.!?])\s+')
cited = set()
for pid, p in PLACES.items():
    for t in p['topics']:
        key = f'{pid}/{t["id"]}'
        assert t['ask'].endswith('?'), f'{key}: a topic is a question'
        assert len(t['ask']) > 12, f'{key}: the ask is too short to be one'
        c = t['cites']
        assert not c.startswith('/') and '..' not in c, \
            f'{key}: cites {c}, which is not repo-relative'
        assert (ROOT / c).exists(), f'{key}: cites {c}, which does not exist'
        cited.add(c)
        n = len(_SENT.split(t['answer'].strip()))
        assert 2 <= n <= 4, f'{key}: {n} sentences, wanted two to four'
        assert 120 <= len(t['answer']) <= 460, \
            f'{key}: {len(t["answer"])} characters is outside the plain band'
        # a gate could only be expressed by a field, so there is no field
        for f in ('requires', 'unlocks', 'after', 'score', 'points'):
            assert f not in t, f'{key}: {f} would make the guide a gate'

# -- the `move` topic of every place names a control scheme, and only the
# -- places that are actually walkable may name the walking one
for pid, p in PLACES.items():
    mv = next(t for t in p['topics'] if t['id'] == 'move')
    assert 'scheme' in mv, f'{pid}: the move topic must name a control scheme'
    s = mv['scheme']
    assert s in SHARED_CONTROLS or s == 'seat:running', \
        f'{pid}: {s} is not a declared scheme'
    if s == 'walk-keyboard':
        assert p['walkable'], f'{pid}: names the walk scheme but is not walkable'
    if s == 'seat:running':
        assert pid == 'seat', f'{pid}: only the seat resolves a running seat'
    if p['walkable']:
        assert s == 'walk-keyboard', \
            f'{pid}: is walkable but its move topic names {s}'

# -- every key code and handler a written scheme claims is one the page has
for sid, s in SHARED_CONTROLS.items():
    assert s['rows'], f'{sid}: a scheme with no rows'
    seen = set()
    for r in s['rows']:
        assert r['input'] not in seen, f'{sid}: two rows for {r["input"]}'
        seen.add(r['input'])
        assert len(r['does']) > 25, f'{sid}/{r["input"]}: say what it does'
        assert r['codes'], f'{sid}/{r["input"]}: a row nothing can check'
        for code in r['codes']:
            assert code in PAGE_SRC, \
                f'{sid}/{r["input"]}: the page never reads {code}'

# -- the seat schemes are READ from sims/, never typed here. A seat's keys
# -- must resolve against the key codes the page actually drives a seat
# -- with, which the page declares once as OP_KEYS.
_op = re.search(r"const OP_KEYS = \[([^\]]+)\]", PAGE_SRC)
assert _op, 'the page no longer declares OP_KEYS; seat keys cannot be checked'
OP_KEYS = set(re.findall(r"'([A-Za-z]+)'", _op.group(1))) | {'Space'}


def key_code(token):
    """A seat declares its keys the way a person says them - 'A / D',
    'Space', 'C'. This turns one such token into the KeyboardEvent.code the
    page actually reads, and refuses anything it does not recognise rather
    than guessing: an unrecognised token is a control the guide would be
    describing without being able to check it."""
    tok = token.strip()
    if len(tok) == 1 and tok.isalpha():
        return 'Key' + tok.upper()
    assert tok == 'Space', f'{tok!r} is not a key token this build can resolve'
    return 'Space'


SEAT_CONTROLS = {}
for sid, s in SIMS['sims'].items():
    rows = []
    for c in s['controls']:
        codes = [key_code(tok) for tok in c['keys'].split('/')]
        for code in codes:
            assert code in OP_KEYS, \
                f'{sid}: control {c["keys"]!r} resolves to {code}, which the page never drives a seat with'
        # the row is the registry's own row: the keys and the action as
        # sims/ wrote them, never a paraphrase of them
        rows.append({'input': c['keys'], 'does': c['action'], 'codes': codes})
    xr = dict(s['xr'])
    if xr['grip_key'] is not None:
        assert xr['grip_key'] in OP_KEYS, \
            f'{sid}: the xr grip maps to {xr["grip_key"]}, which the page never drives a seat with'
    SEAT_CONTROLS[sid] = {'name': s['name'], 'source': 'sims/registry/sims.json',
                          'rows': rows, 'xr': xr}

assert set(SEAT_CONTROLS) == set(SIMS['sims']), \
    'a seat the simulator registry declares has no control scheme here'

# -- the voice policy. Both features carry the same six fields, both are
# -- off, and the banner is COMPUTED from those fields rather than typed.
_page_keys = set(re.findall(r"'(tc-[a-z-]+)'", PAGE_SRC))
_training_keys = {VOICE_STORAGE['read_aloud_key'], VOICE_STORAGE['ask_by_voice_key']}
_tr = json.load(open(ROOT / 'training/registry/training.json'))
_taken = _page_keys | {_tr['storage']['key'], _tr['storage']['toggle_key'],
                       _tr['trace']['toggle_key']}
for fid, f in VOICE.items():
    for k in VOICE_FIELDS:
        assert k in f and len(f[k]) > 60, f'{fid}: {k} is missing or too thin'
    assert f['default'] == 'off', \
        f'{fid}: a voice feature that defaults on is a decision this pack refuses'
    assert f['storage_key'].startswith('tc-guide-'), \
        f'{fid}: a guide key is namespaced as one'
    assert f['storage_key'] not in _taken, \
        f'{fid}: {f["storage_key"]} is already somebody else\'s key'
    # the banner is the six fields joined, in the declared order - one copy
    # of each sentence, and a banner that cannot drift from the registry
    f['banner'] = ' '.join(f[k] for k in VOICE_FIELDS)
assert VOICE['read_aloud']['storage_key'] == VOICE_STORAGE['read_aloud_key']
assert VOICE['ask_by_voice']['storage_key'] == VOICE_STORAGE['ask_by_voice_key']
assert len(_training_keys) == 2, 'the two voice switches must not share a key'

# the two facts that make the ask-by-voice banner honest rather than
# reassuring: it must say the audio leaves, and it must name whose service
# it goes to. A banner that said neither would still pass every other check
# here, so both are asserted by content.
_stt = VOICE['ask_by_voice']
assert 'sends your recorded voice off this device' in _stt['leaves_the_device'], \
    'the ask-by-voice banner must say plainly that the audio leaves'
assert 'browser\'s own vendor' in _stt['leaves_the_device'], \
    'the ask-by-voice banner must name whose service receives it'
assert 'neither operates' in _stt['not_ours'] and 'nor can see' in _stt['not_ours'], \
    'the ask-by-voice banner must disclaim both operating and seeing the service'
assert 'stores no audio' in _stt['no_audio_kept'], \
    'the ask-by-voice banner must say no audio is stored'
assert 'absent rather than degraded' in _stt['unavailable'], \
    'an unavailable feature is absent, never quietly degraded'
# and the read-aloud banner must not claim local when it cannot know
assert 'localService' in VOICE['read_aloud']['not_ours'], \
    'read-aloud must name the flag that says local from remote'
assert 'usually local and not always' in VOICE['read_aloud']['leaves_the_device'], \
    'read-aloud must not claim its voices are local'
assert 'absent rather than degraded' in VOICE['read_aloud']['unavailable'], \
    'an unavailable feature is absent, never quietly degraded'

# -- the hands. 25 joints, every named joint real, and a real hysteresis
# -- band: one threshold would chatter, and on a stop gesture that is a
# -- safety bug rather than a polish one.
assert len(HAND_JOINTS) == 25 and len(set(HAND_JOINTS)) == 25, \
    f'WebXR hand input declares 25 joints, this table has {len(HAND_JOINTS)}'
_walkable = {pid for pid, p in PLACES.items() if p['walkable']}
for gid, g in GESTURES.items():
    assert g['joints'], f'{gid}: a gesture measured against nothing'
    for j in g['joints']:
        assert j in HAND_JOINTS, f'{gid}: {j} is not a WebXR hand joint'
    assert len(g['joints']) == len(set(g['joints'])), f'{gid}: a joint named twice'
    assert g['where'], f'{gid}: a gesture that applies nowhere'
    for w in g['where']:
        assert w in _walkable, \
            f'{gid}: declared for {w}, which is not a walkable place'
    band = abs(g['release_m'] - g['threshold_m'])
    assert 0.010 <= band <= 0.040, \
        f'{gid}: a {band * 1000:.0f} mm hysteresis band is not one'
    assert 0.005 < g['threshold_m'] < 0.300, f'{gid}: threshold out of hand range'
    assert 0 <= g['hold_ms'] <= 1000, f'{gid}: hold time out of range'
    assert len(g['measure']) > 60 and len(g['does']) > 40, \
        f'{gid}: say what is measured and what it does'
    if 'curl_m' in g:
        assert 0.005 < g['curl_m'] < g['threshold_m'], \
            f'{gid}: the curl distance must be tighter than the extension one'
    if 'angle_deg' in g:
        assert 0 < g['angle_deg'] <= 90, f'{gid}: an angle out of range'
# exactly one gesture opens the guide, or the learner has two ways in and
# no way to know which one they made
assert sum(1 for g in GESTURES.values() if 'open this guide' in g['does']) == 1, \
    'exactly one gesture opens the guide'

# -- the hand claim is grounded in the page's own admission rather than in
# -- this pack's good intentions
assert 'mocked WebXR session' in PAGE_SRC, \
    'the page no longer says its XR layer is proved against a mocked session'
assert 'UNVERIFIED-ON-HARDWARE' in HAND_HONESTY['status'], \
    'the hand table must carry its unverified status in the status line'
assert 'MOCKED' in HAND_HONESTY['status'], \
    'the hand table must say what it WAS tested against'

# -- provenance. SCRIPTED is this pack's word; AI-SYNTHESIZED is orbis's,
# -- and the only place it may appear here is in the topic that explains
# -- that orbis owns it.
assert HONESTY['status'].startswith('SCRIPTED:'), \
    'the guide pack must carry the SCRIPTED provenance word'
_ai = [f'{pid}/{t["id"]}' for pid, p in PLACES.items() for t in p['topics']
       if 'AI-SYNTHESIZED' in t['answer']]
assert _ai == ['panel-orbis/limits'], \
    f'AI-SYNTHESIZED belongs to orbis/ and describes nothing this pack scripts: {_ai}'

# -- the guide reaches no network of its own. Nothing in the payload may be
# -- a URL, and no topic may carry a template the page would have to
# -- evaluate - either would make an answer something generated at view
# -- time rather than something written here.
_payload_text = json.dumps([PLACES, SHARED_CONTROLS, HONESTY, CONTRACT])
assert 'http://' not in _payload_text and 'https://' not in _payload_text, \
    'the guide names no URL: it fetches nothing and links nowhere'
for pid, p in PLACES.items():
    for t in p['topics']:
        assert '${' not in t['answer'] and '{' not in t['answer'], \
            f'{pid}/{t["id"]}: an answer is written, never a template'

# ----------------------------------------------------------------- build ---
stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
topics = [t for p in PLACES.values() for t in p['topics']]
shared_rows = sum(len(s['rows']) for s in SHARED_CONTROLS.values())
seat_rows = sum(len(s['rows']) for s in SEAT_CONTROLS.values())

doc = {
    'pack': 'smartcitix-trade-craft-academy-guide',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'contract': CONTRACT,
    'honesty': HONESTY,
    'counts': {
        'places': len(PLACES),
        'world_places': sum(1 for p in PLACES.values() if p['kind'] == 'world'),
        'panel_places': sum(1 for p in PLACES.values() if p['kind'] == 'panel'),
        'asks': len(ASK_SET),
        'topics': len(topics),
        'cited_files': len(cited),
        'control_schemes': len(SHARED_CONTROLS),
        'seat_schemes': len(SEAT_CONTROLS),
        'controls': shared_rows + seat_rows,
        'shared_controls': shared_rows,
        'seat_controls': seat_rows,
        'xr_seat_mappings': len(SEAT_CONTROLS),
        'gestures': len(GESTURES),
        'hand_joints': len(HAND_JOINTS),
        'voice_features': len(VOICE),
    },
    'ask_set': ASK_SET,
    'places': PLACES,
    'controls': {'shared': SHARED_CONTROLS, 'seats': SEAT_CONTROLS},
    'voice': {'fields': list(VOICE_FIELDS), 'features': VOICE,
              'storage': VOICE_STORAGE},
    'hands': {'honesty': HAND_HONESTY, 'session_feature': 'hand-tracking',
              'joints': HAND_JOINTS, 'gestures': GESTURES},
    'page_contract': PAGE_CONTRACT,
    'cites': sorted(cited),
}

# the counts are computed above and asserted here against the same things
# they were computed from, so a count and the thing it counts cannot drift
assert doc['counts']['topics'] == doc['counts']['places'] * doc['counts']['asks'], \
    'every place answers every ask, so the topic count is the product'
assert doc['counts']['controls'] == shared_rows + seat_rows

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'guide.json').write_text(json.dumps(doc, indent=1) + '\n')
print(f"guide: {doc['counts']['places']} places "
      f"({doc['counts']['world_places']} views, {doc['counts']['panel_places']} panels), "
      f"{doc['counts']['topics']} topics over {doc['counts']['asks']} asks, "
      f"{doc['counts']['cited_files']} files cited; "
      f"{doc['counts']['controls']} controls in "
      f"{doc['counts']['control_schemes']} written schemes and "
      f"{doc['counts']['seat_schemes']} read from sims/; "
      f"{doc['counts']['gestures']} hand gestures (unverified on hardware); "
      f"voice off by default, both switches (source stamp {stamp})")
