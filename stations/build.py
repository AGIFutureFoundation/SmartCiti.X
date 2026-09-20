#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the stations pack builder.

Rebrands the recovered pre-rebrand yard curriculum (archive/
bac_yard_stations.json) into the live 111-hall structure: every station is
assigned to a hall from the union roster, a strand from the skill graph,
a tier, and — through the strand — the room of that hall's floor plan where
the station physically belongs. The interactive map renders stations in
exactly those rooms, so the content and the space cannot drift apart.

The assignment table below is AUTHORED — it is a curatorial judgement about
which hall each station serves — and everything derived from it (skill_id,
room, district) is computed from the registries, then proven by
stations/test.mjs rather than trusted.

DEPTH. The recovered content is the record and is never edited in place;
where a lesson named its subject instead of teaching it, where a doctrine
line said nothing a learner did not already suspect, or where three
stations opened with the same sentence, an AUTHORED overlay in this file
deepens it. Provenance is computed per field, so the registry says which
line is recovered and which was written here.

AGREEMENT. A station stands in a room, and that room's door already states
what it requires of you. This pack reads that record - the same one the
door placard is drawn from - instead of holding a second opinion about it,
because it held one and the two disagreed.

HONESTY: station content is recovered and authored, machine-gradable but
unverified general practice until reviewed by journey-level practitioners
(ROADMAP v3.4), and the registry says so. It cites no jurisdiction, no
standard and no organisation, and the builder proves that against the
labels pack's published list of marks.
"""
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'web'))
from interiors import ROOMS  # noqa: E402

# One bundle version, read from the manifest rather than typed here.
PACK_VERSION = json.load(open(ROOT / 'pack/manifest.json'))['pack_version']
BUILT = "2026-09-09"

archive = json.load(open(ROOT / 'archive' / 'bac_yard_stations.json'))
unions = json.load(open(ROOT / 'unions' / 'registry' / 'unions.json'))['unions']
skills = json.load(open(ROOT / 'pack' / 'registry' / 'skills.json'))['skills']
by_slug = {u['slug']: u for u in unions}
skill_ids = {s['skill_id'] for s in skills}
room_of = {strand: label for strand, label, *_ in ROOMS}

# The two packs a station stands inside of, read rather than restated.
#
# LABELS owns what a sign is and what a sign may not say. A station is drawn
# in the world as a chip and the door it stands behind carries a placard, so
# this pack names those kinds and fails if the signage pack drops or renames
# them - and it lints its own words against the labels pack's published list
# of borrowed marks instead of keeping a second copy of that list.
#
# SURFACES owns what a room requires of the person in it. The door placard
# is drawn from that record; a station standing in the same room must not
# hold a second opinion about it, which is exactly the bug ROOM_PPE below
# exists to close.
labels_reg = json.load(open(ROOT / 'labels' / 'registry' / 'labels.json'))
finishes = json.load(open(ROOT / 'surfaces' / 'registry' / 'finishes.json'))
assert labels_reg['pack_version'] == PACK_VERSION, \
    'one bundle version: the labels registry is a different build'
assert finishes['pack_version'] == PACK_VERSION, \
    'one bundle version: the surfaces registry is a different build'

# The label kinds this pack depends on, named once. A station beacon wears
# the station chip; the door of the room it stands in wears the placard; the
# condition in force in that room wears the hazard notice. If signage renames
# one of these, this build stops rather than shipping a station that points
# at a sign nobody draws.
SIGN_KINDS = {
    'station': 'the chip a station beacon wears in the room it stands in',
    'placard': 'the door sign stating what the room requires of you',
    'hazard': 'the notice stating what is in force in that room',
}
for kid, why in SIGN_KINDS.items():
    assert kid in labels_reg['kinds'], f'the labels pack has no {kid} kind: {why}'
assert labels_reg['kinds']['placard']['provenance'] == 'DERIVED', \
    'the placard is derived from the room record, which is what lets a ' \
    'station read the same record instead of retyping it'

NO_MARKS = labels_reg['no_marks']


def borrowed_marks(text):
    """Every mark the given text borrows, by the labels pack's own list.

    The vocabulary is read from the signage registry rather than repeated
    here: a station's checklist and a door placard are words printed on
    signs in the same building, and there is one statement in this bundle of
    what such words may not say. The matcher is this pack's, the list is
    not.
    """
    low = ' ' + ' '.join(str(text).lower().split()) + ' '
    hits = [t for t in NO_MARKS['tokens']
            if re.search(r'(?<![a-z0-9])' + re.escape(t) + r'(?![a-z0-9])', low)]
    for pat in NO_MARKS['patterns']:
        hits += re.findall(pat, low)
    return hits

# station id -> (hall slug, strand, tier). Authored; verified downstream.
ASSIGN = {
    0:  ("bricklayers",    "safety",          "fundamentals"),  # PPE & Readiness
    1:  ("bricklayers",    "materials",       "fundamentals"),  # Mortar & Material Prep
    2:  ("bricklayers",    "procedure",       "fundamentals"),  # Bricklaying Technique
    3:  ("scaffold",       "safety",          "applied"),       # Scaffold & Fall Protection
    4:  ("bricklayers",    "safety",          "applied"),       # Silica Dust & Respiratory
    5:  ("riggers",        "procedure",       "fundamentals"),  # Rigging & Material Handling
    6:  ("bricklayers",    "layout",          "fundamentals"),  # Blueprint & Layout Reading
    7:  ("bricklayers",    "documentation",   "fundamentals"),  # Apprenticeship & Union Pathway
    8:  ("cement-masons",  "materials",       "applied"),       # Curing & Weather Protection
    9:  ("masonry-restore","procedure",       "applied"),       # Restoration & Tuckpointing
    10: ("bricklayers",    "procedure",       "applied"),       # Reinforced Masonry & Grouting
    11: ("stone-carvers",  "materials",       "applied"),       # Stone Veneer & Anchored Stone
    12: ("bricklayers",    "coordination",    "mastery"),       # Estimating & Bidding
    13: ("site-safety",    "leadership",      "applied"),       # Jobsite Safety Culture
    14: ("masonry-restore","materials",       "fundamentals"),  # Cleaning & Sealing Masonry
    15: ("refractory",     "procedure",       "applied"),       # Refractory Masonry
    16: ("masonry-restore","documentation",   "applied"),       # Historic Preservation Standards
    17: ("masonry-restore","tools",           "fundamentals"),  # Pointing & Joint Finishes
    18: ("bricklayers",    "inspection",      "applied"),       # Masonry Anchorage & Ties
    19: ("waterproofers",  "procedure",       "applied"),       # Flashing & Moisture Control
    20: ("bricklayers",    "materials",       "applied"),       # Concrete Masonry Units (CMU)
    21: ("stone-carvers",  "procedure",       "applied"),       # Natural Stone Setting
    22: ("tilesetters",    "procedure",       "fundamentals"),  # Tile & Terrazzo
    23: ("lathers",        "procedure",       "fundamentals"),  # Welding & Metal Stud Framing
    24: ("waterproofers",  "materials",       "fundamentals"),  # Caulking & Sealants
}
# --------------------------------------------------------- authored depth ---
# The recovered curriculum is the record and stays the record: archive/ is
# never edited here. What it is not, in places, is TAUGHT. A lesson that
# reads "Precision: bond patterns, plumb, level, tooled joints" is a list of
# nouns; a doctrine that reads "Reminder: no shortcut on rigging" tells a
# learner nothing they did not already suspect; and three separate stations
# opened with the same sentence about allied trades, which is what content
# looks like when it was written to fill a slot. A checklist item that would
# not change what a learner does at the bench is a placeholder wearing a
# tick box.
#
# This table is the AUTHORED overlay that deepens those. It is curation on
# the same terms as ASSIGN above: a judgement, recorded here, published with
# its provenance computed per field, and still - like everything else in
# this pack - unverified general practice pending review by journey-level
# practitioners. It cites no jurisdiction, no standard and no organisation,
# and the builder proves that against the labels pack's published list of
# marks rather than against a second copy of it.
#
# Three kinds of entry live here:
#   * `lesson` / `doctrine` - where the recovered line named a subject
#     instead of teaching it, or repeated another station's line verbatim.
#   * `checklist` - a full replacement, because a checklist is a sequence
#     and patching one item of it leaves the order somebody else's.
#   * `question` - only where the recovered question cited a document by
#     name; the options and their figures are the recovered ones untouched,
#     so a rewritten question still asks what the figures answer.
# Every station, deepened or not, gains `quiz.why`: the reason the correct
# option is correct. A quiz that marks an answer without saying why teaches
# the answer and not the trade.
DEEPEN = {
    0: {
        # Its checklist retyped the room's own PPE record, and disagreed
        # with it - see ROOM_PPE below. What a room requires is the room's
        # fact; what the TASK adds on top is this station's.
        'lesson': "Protective equipment only works if it fits, if it is "
                  "checked before it is worn, and if it is still on when the "
                  "job gets awkward. What fails on a working site is rarely "
                  "the absence of gear - it is gear in the wrong size, gear "
                  "past its life, or gear that came off for the last ten "
                  "minutes of the shift.",
        'doctrine': "Gear you have to go and look for is gear you will work "
                    "without.",
        'checklist': [
            "Read the door placard before you cross the line - it states "
            "what this room requires",
            "Add what the task requires on top of what the room requires",
            "Inspect the shell for cracks and the suspension for fraying "
            "every shift",
            "Retire a helmet that has taken an impact, however sound it "
            "looks",
            "Match glove class to the work - cut, chemical or heat is three "
            "pairs, not one",
            "Seal-check a respirator with cupped hands every time it goes on",
            "Keep spares in the gang box so nobody works bare while they "
            "look for a replacement",
            "Take contaminated gear off in the order that keeps the dirty "
            "face away from yours",
        ],
        'why': "Cutting indoors puts dust, noise and fragments in the air at "
               "once, so the answer is everything the task adds to what the "
               "room already asks for - one item of it is not a lesser "
               "answer, it is a different hazard left uncovered.",
    },
    1: {
        'lesson': "Mortar is a structural material with a working life "
                  "measured in hours: the binder begins setting the moment it "
                  "meets water, and the strength the joint ends up with is "
                  "decided by what it was batched at and how long it stood. "
                  "Retempering a board that has already stiffened buys back "
                  "workability and pays for it in strength.",
        'doctrine': "Water added after stiffening is workability bought with "
                    "strength.",
        'checklist': [
            "Know which mortar the wall was designed for before the first "
            "board is loaded",
            "Batch by volume with the same measure every time, never by the "
            "shovelful",
            "Discard a board that has stood past its working life rather "
            "than retempering it",
            "Keep bags dry and off the ground - a bag that has taken damp is "
            "waste, not stock",
            "Pre-dampen absorbent units in hot weather so the joint is not "
            "robbed of its water",
            "Wash wet cement off skin before it dries; the burn is painless "
            "until it is not",
            "Record what was batched, when and by whom, so a suspect joint "
            "has a history",
        ],
        'why': "Mortar that has stiffened has begun to set; tempering it "
               "back to a workable state breaks what has already formed, and "
               "the joint never recovers the strength it was designed for.",
    },
    2: {
        'lesson': "A wall is built to a line and a story pole, not to an eye: "
                  "the line holds the course straight and the pole holds "
                  "every course the same height, so the last brick lands "
                  "where the drawing said it would. Full head and bed joints "
                  "are what make the wall one thing instead of a stack - a "
                  "joint buttered only at the face is a crack waiting for the "
                  "first frost.",
        'doctrine': "The line is right and you are wrong, until the line is "
                    "proved wrong.",
        'checklist': [
            "Set the line to the course height off the pole, not off the "
            "last brick laid",
            "Butter head joints full depth - a face-only joint reads "
            "finished and is not",
            "Check plumb at every lead, and again before the lead is used",
            "Run the bond through an opening rather than restarting it there",
            "Tool when the mortar is thumbprint-hard: earlier smears it, "
            "later burns it",
            "Make the cut at the lead, where it can be measured, not in the "
            "middle of a wall",
            "Brush the face down before the mortar cures - a cured smear "
            "comes off with the face",
        ],
        'why': "Plumb and level are not a finish, they are what lets the "
               "next trade fit: a course that leans is outside the wall's "
               "tolerance before the wall is even up.",
    },
    3: {
        'lesson': "A scaffold is a temporary structure that gets loaded, "
                  "unloaded and altered by people who did not build it, which "
                  "is why its tag is the only statement of what the last "
                  "competent inspection found. The fall is seldom the "
                  "failure - the failure is a missing plank, a rail somebody "
                  "took off to land material, or an anchor point borrowed for "
                  "something else.",
        'doctrine': "If you did not watch it go up, the tag is everything you "
                    "know about it.",
        'checklist': [
            "Read the tag before you set foot on a deck, and read it again "
            "after any alteration",
            "Never alter, remove or borrow a component - report it and wait "
            "for the competent person",
            "Tie off before you leave the deck, and to a point somebody can "
            "name",
            "Deck the platform fully; one missing plank is the hole somebody "
            "steps into",
            "Check rails and toe boards on every open side, the ends "
            "included",
            "Climb the access way, never the cross-bracing",
            "Keep the deck clear - material underfoot turns a trip into a "
            "fall",
            "Look up before you look out: the deck above you is somebody "
            "else's floor",
        ],
        'why': "A tag records an inspection somebody signed. No tag is not a "
               "neutral state - it is an untested structure, and a red one "
               "is a structure already found wanting.",
    },
    4: {
        'lesson': "The dust that does the damage is the fraction too fine to "
                  "see, and it works slowly: the scarring is permanent and "
                  "the symptoms arrive years after the exposure that caused "
                  "them. Controls work at the source - water on the blade, "
                  "extraction at the cut - because once the dust is airborne "
                  "the respirator is the last thing between it and a lung.",
        'doctrine': "You cannot feel the exposure that harms you, and you "
                    "will not remember the day it happened.",
        'checklist': [
            "Cut wet, or cut with extraction running - never dry with "
            "neither",
            "Check the water reaches the blade before the first cut, not "
            "after it",
            "Vacuum or wet-sweep; a broom puts the settled fraction straight "
            "back in the air",
            "Screen the work so your dust does not become somebody else's "
            "exposure",
            "Shave clean where a respirator seals, and seal-check it every "
            "time",
            "Rotate the dusty task through the crew instead of giving it to "
            "one pair of lungs",
            "Change filters on a written schedule, not when breathing gets "
            "hard",
            "Know what the day's exposure plan says before the saw starts",
        ],
        # The recovered question asked which saw was "compliant", which is a
        # question about a rule this bundle does not hold. The same figures
        # answer the question that matters at the saw.
        'question': "Cutting block indoors. Which saw keeps the dust out of "
                    "the air?",
        'why': "Water at the blade takes the fine fraction out of the air at "
               "the point it is made; a dry cut and a broom afterwards makes "
               "the same dust twice.",
    },
    5: {
        'lesson': "A load under a hook is a stored-energy problem: the sling "
                  "angle decides how much of the load each leg actually "
                  "carries, and the swing radius decides who is standing in "
                  "its path when it moves. Most rigging injuries happen to "
                  "people who were not rigging - they were walking under it, "
                  "steadying it by hand, or waiting for it to land.",
        'doctrine': "One voice on the signals; anybody's voice on the stop.",
        'checklist': [
            "Know the weight before the sling is chosen, not after it is "
            "tight",
            "Read the sling angle - the wider the legs, the more each leg "
            "carries",
            "Inspect slings and shackles each shift and pull anything cut, "
            "kinked or deformed out of service",
            "Use a tag line; never steady a load with a hand",
            "Walk the load path before the lift and keep the swing radius "
            "clear during it",
            "Name the signaller out loud, so everyone knows whose signal "
            "counts",
            "If a signal is not acknowledged, nothing moves",
            "Land on dunnage that can carry it, and de-rig only once it is "
            "stable",
        ],
        'why': "An unacknowledged signal means the operator and the "
               "signaller do not share a picture of the lift, and the only "
               "safe move is the one nobody has to guess at.",
    },
    6: {
        'lesson': "Layout is where the wall is decided; everything after it "
                  "is repetition. Control lines and benchmarks are the only "
                  "agreement between the drawing and the ground, so an error "
                  "carried off them is not a small error - it is multiplied "
                  "by every course and every opening that follows.",
        'doctrine': "An error found at layout costs an hour; the same error "
                    "found at the lintel costs the wall.",
        'checklist': [
            "Find the control lines and the benchmark before measuring "
            "anything",
            "Check the drawing against the ground - openings that exist, "
            "openings that moved",
            "Build the story pole from the drawing, then build the wall from "
            "the pole",
            "Dry-bond the first course to see where the cuts land before "
            "mortar commits you",
            "Mark openings, reveals and returns on the deck where the wall "
            "will stand",
            "Flag a conflict the day you find it - the drawing is somebody "
            "else's to change",
            "Keep one marked-up set as the record; a correction on a loose "
            "sheet is lost",
        ],
        'why': "The bond is read off the drawing before the first course, "
               "because the pattern decides where every cut and every "
               "opening jamb lands.",
    },
    7: {
        # The recovered lesson named a real union and its training body. The
        # pathway it describes is general apprenticeship practice and reads
        # as such; whose programme a learner is actually in is not this
        # bundle's to state.
        'lesson': "An apprenticeship is a contract between hours worked, "
                  "instruction attended and competencies signed off, and the "
                  "record of it belongs to the apprentice. Hours that were "
                  "worked but never logged are hours that did not happen, "
                  "and the shortfall surfaces at the point somebody is due to "
                  "advance.",
        'doctrine': "The logbook is the part of your training nobody else can "
                    "rebuild for you.",
        'checklist': [
            "Log hours in the week they were worked, against the work "
            "actually done",
            "Get the signature while the person who supervised you can still "
            "remember the job",
            "Attend the related instruction - the hours and the classroom are "
            "not alternatives",
            "Track which competencies are signed and which are still open, "
            "and ask for the open ones",
            "Keep your own copy of the record, not only the one the office "
            "holds",
            "Know who reviews your progress and when the next review falls",
            "Raise a shortfall as soon as it appears: a missing month is "
            "arguable, a missing year is not",
        ],
        'why': "A logged correction is a record with the gap explained in "
               "it; an unlogged hour cannot be told apart from an hour never "
               "worked.",
    },
    8: {
        'lesson': "Fresh masonry gains strength from a reaction that needs "
                  "water and warmth, and the first days decide how far that "
                  "reaction gets. Freezing before it has set does damage no "
                  "later warm spell undoes; drying out too fast in heat and "
                  "wind stops the reaction where it stands.",
        'doctrine': "Weather does not negotiate, and the wall remembers the "
                    "first night.",
        'checklist': [
            "Cover new work against rain for the first day, and lap the "
            "cover past the wall",
            "Keep the work above freezing while it sets - heat or blankets, "
            "not hope",
            "Mist in hot, dry, windy weather; wind takes the water faster "
            "than sun does",
            "Cap the top of an unfinished wall - water gets in at the top, "
            "not at the face",
            "Do not load the wall until it has set enough to carry what is "
            "going on it",
            "Know the age at which this wall is expected to reach full "
            "strength before anything leans on it",
            "Record the overnight temperatures against the day's work, so a "
            "suspect lift has a history",
        ],
        'why': "Insulation holds the heat the reaction itself is making; "
               "spraying water on before a freeze adds the one ingredient "
               "that expands when it turns.",
    },
    9: {
        'lesson': "Repointing repairs the mortar, not the unit: the new "
                  "mortar must be softer than the brick around it so that "
                  "movement and salts are taken up by the joint, which can be "
                  "replaced, and not by the face, which cannot. A harder "
                  "repair looks tidy on the day and spalls the arrises within "
                  "a few winters.",
        'doctrine': "The repair that lasts is the one nobody can point to.",
        'checklist': [
            "Match the existing mortar by composition and hardness before "
            "matching its colour",
            "Cut the joint square, to about twice its width in depth, and no "
            "deeper",
            "Cut by hand where the unit is soft - a wheel takes the arris "
            "with the joint",
            "Pre-wet the joint so the brick does not drink the water the "
            "mortar needs",
            "Match the sand: colour and grading come from the sand, not from "
            "pigment",
            "Pack in thin layers and let each one stiffen before the next",
            "Tool to the profile that is already there, not the one you "
            "prefer",
            "Photograph and note the condition before you disturb it",
        ],
        'why': "A hand pick takes the mortar and leaves the arris; a powered "
               "wheel cannot tell the joint from the brick at the edge of the "
               "cut.",
    },
    10: {
        'checklist': [
            "Place and tie the reinforcement before the units go round it",
            "Leave cleanouts at the foot of every cell you intend to fill",
            "Check the cells are clear of droppings before any grout is "
            "called for",
            "Let the mortar gain enough strength to take the grout pressure",
            "Pour in lifts and consolidate each lift before the next is "
            "placed",
            "Reconsolidate after the initial water loss, while the lift is "
            "still plastic",
            "Verify the grout is the mix specified and record which pour it "
            "went into",
            "Inspect bar position and lap length before anything is covered",
        ],
        'why': "Grout placed in lifts can be consolidated all the way "
               "through. One tall pour traps voids at the bottom, and a void "
               "is exactly where the bar stops being connected to the wall.",
    },
    11: {
        'lesson': "Anchored veneer does not hold itself up by its mortar: the "
                  "anchors carry it back to the structure and the cavity "
                  "behind it keeps water from crossing. Corroded, missing or "
                  "over-spaced anchors are the failure, and not one of them "
                  "is visible once the wall is finished.",
        'doctrine': "What holds the stone on is the part you cannot see once "
                    "the wall is done.",
        'checklist': [
            "Confirm the anchor type against the backing before any stone is "
            "set",
            "Space anchors to the layout the wall was designed for, and add "
            "them at openings and edges",
            "Apply the scratch coat and let it cure before setting against it",
            "Keep the cavity clear - mortar droppings bridge it and carry "
            "water across",
            "Flash the base and leave the weeps open",
            "Stagger joints so no two courses line up through the panel",
            "Sound suspect units for hollows before the scaffold moves",
            "Count the anchors in a bay against the drawing while you can "
            "still reach them",
        ],
        # The recovered question cited a trade association by name. The
        # figures in its options are the recovered ones and are general
        # practice, so the question asks the same thing without the citation.
        'question': "Anchored stone veneer on a block backing. Which anchor "
                    "layout is the one to build to?",
        'why': "The spacing is what turns a row of anchors into a system: too "
               "few and too far apart, and the panel hangs off whichever "
               "anchors are left.",
    },
    12: {
        'lesson': "An estimate is a prediction with a crew's wages inside it: "
                  "quantities come off the drawing, productivity comes off "
                  "records of work actually done, and everything that is not "
                  "drawn - access, scaffold, protection, cleaning - is where "
                  "the money goes. A bid that beats the field by a wide "
                  "margin usually found less work than the job contains, not "
                  "a cheaper way to do it.",
        'doctrine': "Price the access and the protection, or the job will "
                    "price them for you.",
        'checklist': [
            "Take quantities off the drawing, then check them against a "
            "second measure",
            "Use productivity from your own completed jobs, not from memory",
            "Price scaffold, access and weather protection as their own lines",
            "Add waste at a rate the material and the cuts justify, not out "
            "of habit",
            "Write every exclusion down, so the scope argument happens before "
            "the work",
            "Read the programme - winter work and night work are not priced "
            "like day work",
            "Back-check the estimate against what the job actually cost, and "
            "correct the rates",
        ],
        'why': "A measured takeoff with a justified waste allowance is a "
               "number you can defend line by line; a figure carried over "
               "from the last job prices a different building.",
    },
    13: {
        'lesson': "Safety on a working site is carried by ordinary habits - "
                  "the talk before the shift, the near-miss somebody bothered "
                  "to report, the apprentice who felt able to say stop. None "
                  "of them shows up as an incident, which is exactly why they "
                  "are the only part of the system that can be improved "
                  "before somebody is hurt.",
        'doctrine': "An apprentice who cannot say stop is a hazard nobody has "
                    "written down.",
        'checklist': [
            "Hold the talk before the shift, about today's work and not last "
            "month's",
            "Report the near-miss - it is the only free lesson on the site",
            "Use stop-work when you need it, and back the person who used it",
            "Know the chain: who you tell, who they tell, and how long it "
            "should take",
            "Have underground services located and marked before anything "
            "breaks ground",
            "Walk the site at the start and at the end; conditions change "
            "while you work",
            "Keep walkways, landings and exits clear - the way out is not "
            "storage",
            "Close out what the last talk raised, or the next one is theatre",
        ],
        'why': "Stopping and reporting is the only response that changes the "
               "condition. Telling a workmate moves the information sideways "
               "and leaves the hazard where it was.",
    },
    14: {
        'checklist': [
            "Identify the unit and the soiling before choosing anything to "
            "put on them",
            "Test the method on a small, inconspicuous patch and let it dry "
            "fully",
            "Start with the gentlest method that could work and escalate "
            "only if it does not",
            "Pre-wet the wall so the cleaner stays on the surface instead of "
            "soaking in",
            "Keep pressure and tip angle low enough to leave the fired face "
            "intact",
            "Rinse from the top down until the runoff is clear, then rinse "
            "again",
            "Let the wall dry and gain strength before any sealer is even "
            "considered",
            "Use a vapour-permeable sealer, or the wall cannot dry from "
            "behind",
            "Record what was used, at what dilution and where, for the next "
            "cleaning",
        ],
        'why': "The gentlest method that works is the only one that can be "
               "escalated. An aggressive first attempt takes the face off "
               "with the soiling and leaves nothing to test on.",
    },
    15: {
        'lesson': "A refractory lining spends its life travelling up and down "
                  "through temperatures that move every joint in it. It is "
                  "built to expand: joints are laid tight and the expansion "
                  "is allowed for deliberately, and the dry-out afterwards "
                  "drives the water out slowly enough that steam does not "
                  "lift the work it is leaving.",
        'doctrine': "A lining fails at the joint it was never allowed to "
                    "move.",
        'checklist': [
            "Match the brick and the mortar to the service temperature of "
            "the zone",
            "Lay to a tight joint - the joint is the weakness, not the brick",
            "Leave the expansion allowance where the drawing puts it, at the "
            "size it gives",
            "Stagger joints through the thickness so no path runs straight "
            "to the shell",
            "Use anchors that survive the hot face and let the lining move "
            "with them",
            "Keep the backup insulation dry and continuous behind the "
            "working lining",
            "Dry out on the written schedule, slowly enough that steam can "
            "get out",
            "Record the heat-up, so the next outage knows what this lining "
            "has seen",
        ],
        'why': "Staggered joints with planned expansion give the lining "
               "somewhere to go when it grows; a solidly packed joint has to "
               "break something in order to move.",
    },
    16: {
        # The recovered lesson cited a government treatment standard by
        # name. The ranking of treatments it describes is ordinary
        # conservation practice and stands on its own.
        'lesson': "Historic fabric is a finite material: every intervention "
                  "removes some of it and none of it grows back. The usual "
                  "ranking - maintain, then stabilise, then repair, and only "
                  "then replace in kind - exists because each step costs more "
                  "of the original than the step before it.",
        'doctrine': "Replacement is what you do when repair has been proved "
                    "impossible, not when it looks slower.",
        'checklist': [
            "Record the condition before you touch it: photographs, notes, "
            "and where they were taken from",
            "Tell original fabric from previous repair before planning either",
            "Choose the least intervention that solves the problem, then stop",
            "Repair in place wherever the unit can still do its job",
            "Replace in kind only where the unit has failed, matching "
            "material, size and finish",
            "Keep the removed material until the work has been signed off",
            "Write down what was done, where, and with what, for whoever "
            "comes next",
        ],
        'why': "Repair keeps the original fabric and the evidence in it. "
               "Replacement and paint both throw away the thing that made the "
               "wall worth keeping.",
    },
    17: {
        'lesson': "The joint is the part of the wall the weather reaches "
                  "first, and its profile decides whether water runs off or "
                  "stands. Tooling compacts the mortar as it shapes it, and "
                  "much of what a concave joint does for weathering it does "
                  "because it was pressed, not because of its shape alone.",
        'doctrine': "Tooling is compaction; the profile is what is left "
                    "behind afterwards.",
        'checklist': [
            "Tool at thumbprint-hard - a joint tooled wet smears and one "
            "tooled late is burned",
            "Work to the profile the wall already has, or the one specified, "
            "and never a mixture",
            "Keep the depth consistent; a deep patch reads as a shadow along "
            "the wall",
            "Use a profile that sheds water on anything exposed to weather",
            "Keep the raked profile for sheltered work, where the ledge it "
            "leaves stays dry",
            "Run the iron one way so the burnish is even across the elevation",
            "Strike the head joints before the bed joints, so the horizontal "
            "run is unbroken",
        ],
        'why': "A concave joint is pressed into itself and leaves no ledge, "
               "so water runs off it instead of standing on it.",
    },
    18: {
        'lesson': "Ties make a veneer and its backing behave as one wall "
                  "under wind: the veneer takes the face load and the ties "
                  "carry it back. Type, spacing and embedment have to be "
                  "right together - a tie of the correct type embedded half "
                  "way into the joint carries almost nothing.",
        'doctrine': "A tie that is not embedded is a tie that is not there.",
        'checklist': [
            "Match the tie to the backing - what fixes into timber does not "
            "fix into steel or block",
            "Space ties to the layout the wall was designed for, and add them "
            "at openings and edges",
            "Embed the tie fully in the bed joint, never laid on top of the "
            "unit",
            "Use corrosion-resistant ties and keep mortar off the drip",
            "Never straighten and reuse a bent tie",
            "Lay the tie level or falling outward, never back towards the "
            "backing",
            "Count the ties in a bay against the drawing before the scaffold "
            "moves",
        ],
        'why': "A corrugated sheet tie is the one that fastens to a timber "
               "stud and still beds flat in the joint; wire and screw anchors "
               "belong to other backings.",
    },
    19: {
        'checklist': [
            "Flash every place the cavity is interrupted: base, heads, sills "
            "and shelves",
            "Run the flashing through to the outer face and turn it down as "
            "a drip",
            "Turn the flashing up the backing high enough to beat driven "
            "water",
            "Form an end dam at every termination so water cannot run off "
            "the side",
            "Leave the weeps open and clear above the flashing, at the "
            "spacing specified",
            "Keep mortar droppings off the flashing - a blocked cavity is a "
            "dam",
            "Lap and seal joints in the flashing generously, in the "
            "direction of flow",
            "Never fasten through the flashing below the line water can "
            "reach",
        ],
        'why': "Flashing only works as a system: something to catch the "
               "water, end dams so it cannot run off the sides, weeps to let "
               "it out, and a drip to throw it clear of the face.",
    },
    20: {
        'checklist': [
            "Set the bond out from the opening, so cuts do not land at a "
            "jamb",
            "Keep the bed joint a consistent thickness, or the coursing "
            "walks away from you",
            "Lay reinforcement in the joints at the spacing the drawing "
            "calls for",
            "Grout the cells the drawing says to grout, and only those",
            "Put control joints where the wall changes height, thickness or "
            "direction",
            "Stagger the bar laps rather than lining them up in one course",
            "Tool the joints on exposed faces once the mortar is "
            "thumbprint-hard",
            "Keep units dry before laying - a wet block shrinks as it dries "
            "in the wall",
        ],
        'why': "Running bond with reinforcement in the joints ties the wall "
               "together along its length. Stack bond with nothing in the "
               "joints has no continuity at all where the units line up.",
    },
    21: {
        'lesson': "Stone arrives as a finite number of pieces cut to a "
                  "drawing, so the sequence and the handling matter as much "
                  "as the bed: a piece broken or cut wrong is not replaced "
                  "from stock, it is re-ordered. Colour and grain are chosen "
                  "across the whole elevation, not piece by piece at the "
                  "wall.",
        'doctrine': "There is no second piece; plan the cut before the saw is "
                    "running.",
        'checklist': [
            "Lay the elevation out dry and choose the faces before anything "
            "is set",
            "Lift on the edges with proper gear - a dropped arris cannot be "
            "repaired invisibly",
            "Set on a full bed; a spot bed concentrates the load and stains "
            "the face",
            "Anchor every piece the way the drawing anchors it, including the "
            "ones nobody will see",
            "Shim and check level and plumb before the bed takes up",
            "Clean as you go - cured mortar on a polished face comes off with "
            "the polish",
            "Protect the set work from the trades following you",
        ],
        'why': "A stainless pin anchor carries the piece back to the "
               "structure and tolerates movement; mortar or adhesive alone is "
               "holding a heavy piece on with nothing to take the wind load.",
    },
    22: {
        # One of three stations whose recovered lesson was the same sentence
        # about allied trades with the trade's name changed.
        'lesson': "A tile fails at its bond, not in its body: full coverage "
                  "of adhesive means the unit is supported everywhere, and a "
                  "void under an edge is where the hollow and then the crack "
                  "start. Wet areas are harder again, because whatever water "
                  "gets under the tile has to be able to get back out.",
        'doctrine': "A hollow tile is not a bad tile; it is a bad bed.",
        'checklist': [
            "Match the adhesive to the substrate, the unit and the exposure, "
            "not to the tile alone",
            "Comb one way and flatten the ridges as you set, so the air has "
            "somewhere to go",
            "Back-butter large or heavy units - a notched bed alone will not "
            "fill under them",
            "Lift a tile early in the run and read the coverage on its back "
            "before going on",
            "Carry movement joints through the tiling and keep them at every "
            "restraint",
            "Hold the joint width consistent; a narrow joint leaves no room "
            "for movement",
            "Clean residue before it cures, especially off unglazed and stone "
            "faces",
            "Seal porous stone before grouting or the grout will colour the "
            "face",
        ],
        'why': "Near-full coverage supports the whole unit and leaves no "
               "pocket for water to stand in. Anything less is a void under a "
               "surface that gets walked on and wetted.",
    },
    23: {
        'lesson': "Light-gauge framing is a system of thin sections that only "
                  "behaves as designed when spacing, fixings and bracing are "
                  "all as drawn. A connection in the wrong place does not "
                  "fail quietly - it moves its load to the next connection, "
                  "which was never sized for it.",
        'doctrine': "A connection made off procedure is a connection nobody "
                    "can vouch for.",
        'checklist': [
            "Check gauge and spacing against the drawing before the track is "
            "fixed",
            "Snap layout lines for both tracks and keep the wall square to "
            "the grid",
            "Fix the track to the structure with the fixing specified, at the "
            "spacing specified",
            "Weld to the written procedure - the settings and the sequence, "
            "not just the look of it",
            "Leave the deflection allowance at the head, where the structure "
            "above will move",
            "Brace before the framing is loaded, not after the boards go on",
            "Inspect the welds for size and length, and for the ones somebody "
            "skipped",
            "Frame the openings the way the drawing frames them; a header is "
            "not optional",
        ],
        'why': "Porosity and undercut are weld quality, judged against what "
               "was specified. A crack is a failed weld: it is cut out and "
               "made again.",
    },
    24: {
        'lesson': "A sealant joint works by stretching, and it can only "
                  "stretch if it is bonded on two faces and free on the "
                  "third. The backer rod sets the depth, gives the bead its "
                  "hourglass section and breaks the bond at the back - which "
                  "is why a joint filled solid tears itself off the substrate "
                  "the first time the gap opens.",
        'doctrine': "Adhesion on three faces is a joint with nowhere to go.",
        'checklist': [
            "Clean and dry both faces - sealant bonds to the substrate, not "
            "to what is sitting on it",
            "Prime where the substrate calls for it and let the primer flash "
            "off",
            "Size the backer rod wider than the gap so it stays put under "
            "compression",
            "Set the rod to the depth the joint width calls for, and keep "
            "that depth even",
            "Gun ahead of the nozzle so the bead fills without trapping air",
            "Tool once, firmly, to press the sealant onto both faces",
            "Never stretch the bead into the joint: a stretched bead is "
            "already loaded",
            "Cut a test length out after cure and read the bond on both faces",
        ],
        'why': "A bead about twice as wide as it is deep can stretch and "
               "recover; a deeper, narrower bead is stiffer than the movement "
               "it has to absorb.",
    },
}

# The overlay covers the roster exactly: a station with no entry would be
# one nobody read, and an entry with no station would be depth written for
# something that does not exist. Both fail here rather than downstream.
assert set(DEEPEN) == set(ASSIGN), \
    f'overlay and roster disagree: {sorted(set(DEEPEN) ^ set(ASSIGN))}'

stations = []
for s in archive['stations']:
    hall, strand, tier = ASSIGN[s['id']]
    assert hall in by_slug, f'unknown hall {hall}'
    skill_id = f'{hall}.{strand}.{tier}'
    assert skill_id in skill_ids, f'no such skill {skill_id}'
    deep = DEEPEN[s['id']]          # asserted total above: a lookup, not a default

    # What the room this station stands in requires of the person in it.
    # This is READ from the surfaces record the door placard is drawn from,
    # never restated: station st000's recovered checklist listed the gear
    # for its own room and listed it WRONG - it called for a hard hat in a
    # room whose record does not ask for one - so a learner reading the
    # station and a learner reading the door got two answers. The record is
    # the answer; the station carries it and adds only what the TASK adds.
    cond = finishes['halls'][hall]['conditions'][strand]
    room_ppe, room_hazards = cond['ppe'], cond['hazards']

    # Per-field defaults, deliberately: an overlay entry deepens the fields
    # it names and leaves the recovered line standing everywhere else, which
    # is what makes provenance computable per field instead of per station.
    lesson = deep.get('lesson', s['lesson'])
    doctrine = deep.get('doctrine', s['doctrine'])
    checklist = deep.get('checklist', s['checklist'])
    quiz = {
        'question': deep.get('question', s['quiz']['question']),
        'options': s['quiz']['options'],
        # The reason the right option is right. Authored for every station:
        # a quiz that marks an answer without saying why teaches the answer
        # and not the trade.
        'why': deep['why'],
    }
    stations.append({
        "station_id": f"st{s['id']:03d}",
        "name": s['name'],
        "hall": hall,
        "district": by_slug[hall]['district'],
        "skill_id": skill_id,
        "strand": strand,
        "tier": tier,
        "room": room_of[strand],
        "lesson": lesson,
        "checklist": checklist,
        "doctrine": doctrine,
        "actions": s['actions'],
        "quiz": quiz,
        "color": s['color'],
        # What the room requires, and what is in force in it, carried from
        # the surfaces record rather than retyped - the same two lists the
        # door placard and the hazard notice are drawn from.
        "room_ppe": room_ppe,
        "room_hazards": room_hazards,
        # Computed per field, so nothing here claims to be recovered that
        # was written in this build, and nothing written here is buried.
        "provenance": {
            'lesson': 'AUTHORED' if 'lesson' in deep else 'RECORDED',
            'doctrine': 'AUTHORED' if 'doctrine' in deep else 'RECORDED',
            'checklist': 'AUTHORED' if 'checklist' in deep else 'RECORDED',
            'actions': 'RECORDED',
            'quiz': 'AUTHORED' if 'question' in deep else 'RECORDED',
            'quiz_why': 'AUTHORED',
            'room_ppe': 'DERIVED',
            'room_hazards': 'DERIVED',
            'assignment': 'AUTHORED',
        },
    })

# ------------------------------------------------------------- the checks ---
PROVENANCE = ('RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED')
for st in stations:
    assert set(st['provenance'].values()) <= set(PROVENANCE), \
        f"{st['station_id']}: provenance outside the bundle's words"

# An overlay entry that repeats the line it replaces is an edit nobody made.
for sid, deep in DEEPEN.items():
    rec = next(a for a in archive['stations'] if a['id'] == sid)
    for field in ('lesson', 'doctrine', 'checklist'):
        if field in deep:
            assert deep[field] != rec[field], \
                f'st{sid:03d}: the {field} overlay is the recovered line again'
    if 'question' in deep:
        assert deep['question'] != rec['quiz']['question'], \
            f'st{sid:03d}: the question overlay is the recovered question again'

# NO SIGN AND NO STATION BORROWS SOMEBODY ELSE'S AUTHORITY. The recovered
# curriculum carried a helmet specification number, a concrete test method,
# a trade association's spacing tables, a government treatment standard, a
# named union and its training body, and a hazard-control table cited by
# number. Every one of them told a learner this content had an authority
# behind it that it does not have - it is unverified general practice, and
# it has to read like it. The list of marks is the labels pack's.
for st in stations:
    text = ' '.join([st['lesson'], st['doctrine'], *st['checklist'],
                     st['quiz']['question'], st['quiz']['why'],
                     *(o['label'] for o in st['quiz']['options'])])
    hits = borrowed_marks(text)
    assert not hits, f"{st['station_id']} borrows {sorted(set(hits))}"

# ONE TRUTH PER FACT: what the ROOM requires is the room record's to state,
# and the door placard already states it. A checklist line that names an
# item from its own room's list is a second copy, and a second copy is what
# drifted in the first place.
for st in stations:
    for item in st['checklist']:
        for ppe in st['room_ppe']:
            assert not re.search(r'(?<![a-z])' + re.escape(ppe) + r'(?![a-z])',
                                 item.lower()), (
                f"{st['station_id']}: \"{item}\" retypes \"{ppe}\", which "
                f'the room record already requires and the door placard '
                f'already states')

# A checklist item that would not change what a learner does is a
# placeholder wearing a tick box. "Rinse thoroughly" and "Document method"
# were two of them. The bar is a line that says what to do and enough about
# it to be done differently tomorrow.
for st in stations:
    assert len(st['checklist']) >= 5, f"{st['station_id']}: thin checklist"
    for item in st['checklist']:
        assert len(item.split()) >= 5, \
            f"{st['station_id']}: \"{item}\" is a label, not an instruction"

# Lines repeated between stations are the tell of content written to fill a
# slot: three stations opened with the same sentence about allied trades,
# and two more shared a checklist item word for word.
for field in ('lesson', 'doctrine'):
    seen = {}
    for st in stations:
        assert st[field] not in seen, \
            f"{st['station_id']} and {seen.get(st[field])} share a {field}"
        seen[st[field]] = st['station_id']
items = [(item, st['station_id']) for st in stations for item in st['checklist']]
seen = {}
for item, sid in items:
    assert item not in seen, f'{sid} and {seen[item]} share a checklist line'
    seen[item] = sid

# Every quiz explains itself, and the explanation is a reason rather than
# the correct option read back.
for st in stations:
    why = st['quiz']['why']
    right = next(o for o in st['quiz']['options'] if o['correct'])
    assert len(why.split()) >= 12, f"{st['station_id']}: the why is a slogan"
    assert why.strip().lower() != right['label'].strip().lower(), \
        f"{st['station_id']}: the why restates the option"
    assert sum(1 for o in st['quiz']['options'] if o['correct']) == 1, \
        f"{st['station_id']}: a quiz with no single right answer is not gradable"

# Two stamps, because there are now two sources. The archive stamp proves
# the recovered record has not moved under this build; the authored stamp
# proves the overlay in this file is the one the registry was written from.
stamp = hashlib.sha256((ROOT / 'archive' / 'bac_yard_stations.json')
                       .read_bytes()).hexdigest()[:16]
authored_stamp = hashlib.sha256(
    pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

authored = {f: sum(1 for st in stations if st['provenance'][f] == 'AUTHORED')
            for f in ('lesson', 'doctrine', 'checklist', 'quiz')}

doc = {
    "pack": "smartcitix-trade-craft-academy-station-registry",
    "product": "SmartCiti.X : Trade Craft Academy (powered by AGI Corp)",
    "pack_version": PACK_VERSION,
    "built": BUILT,
    "source_stamp": stamp,
    "authored_stamp": authored_stamp,
    "count": len(stations),
    "authored": authored,
    "halls_seeded": sorted({s['hall'] for s in stations}),
    # The label kinds this content is printed on, named from the signage
    # registry rather than assumed - the station chip, the door placard and
    # the hazard notice.
    "signage": {"kinds": SIGN_KINDS,
                "note": "a station's sign, the door placard of the room it "
                        "stands in and that room's hazard notice are drawn "
                        "by the labels pack; this pack names those kinds and "
                        "reads the room record they are drawn from, so the "
                        "panel and the door cannot state different things"},
    "honesty": {
        "content": "recovered pre-rebrand yard curriculum with an authored "
                   "overlay that deepens the lessons, doctrine and "
                   "checklists that named a subject instead of teaching it. "
                   "Recovered and authored alike, it is machine-gradable but "
                   "unverified general practice pending review by "
                   "journey-level practitioners",
        "assignment": "hall/strand/tier assignment is authored curation; "
                      "everything derived from it is computed from the "
                      "registries and verified by stations/test.mjs",
        "depth": "the overlay is AUTHORED and says so field by field: every "
                 "station carries a provenance record naming which of its "
                 "lesson, doctrine, checklist and quiz is the recovered line "
                 "and which was written here. Deepening content does not "
                 "verify it, and nothing in this pack is a practitioner's "
                 "sign-off",
        "room_record": "what a room requires of the person in it is the "
                       "surfaces record's fact, not this pack's: room_ppe "
                       "and room_hazards are read from the record the door "
                       "placard is drawn from, and a checklist may not "
                       "retype an item that record already carries. The "
                       "station adds what the TASK adds, and nothing else",
        "marks": "no station cites a jurisdiction, a standard, a standards "
                 "body or a trade organisation. The recovered content did - "
                 "a helmet specification, a concrete test method, an "
                 "association's spacing table, a government treatment "
                 "standard, a named union and a control table cited by "
                 "number - and each of those told a learner this material "
                 "carries an authority it does not carry. The list of marks "
                 "is the labels pack's, read and not copied",
    },
    "stations": stations,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'stations.json').write_text(json.dumps(doc, indent=1) + '\n')
print(f"stations registry: {len(stations)} stations across "
      f"{len(doc['halls_seeded'])} halls, "
      f"{authored['checklist']} authored checklists, "
      f"{authored['lesson']} authored lessons "
      f"(archive stamp {stamp}, authored stamp {authored_stamp})")
