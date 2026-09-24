#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the label registry builder.

Every word in the 3D world is on a sign, and until now every sign looked
the same: one dark rounded rectangle, whatever it was marking. A hall, a
room, a recorded city 4 km away and a machine readout all wore the same
badge, so the only way to know what a sign meant was to read it.

This registry gives each KIND of sign its own shape, palette and voice, so
it can be read before it is read:

  * SHAPE carries the category. A speech bubble is somebody who will talk
    to you. A tab with a pointer is a place you can enter. A pin on a stem
    is somewhere real, out there. A chip is a thing you can pick up or
    open. A readout is a number the machine is telling you.
  * COLOUR carries provenance and district. RECORDED wears a solid accent;
    SCHEMATIC wears a dashed outline and says so. A hall wears its
    district's own hue, which is the same hue the map and the crew mark
    use, so one colour means one thing everywhere in the bundle.
  * TYPE carries rank. Display face for names, sans for the line under
    them, mono for anything a machine measured.

NOT EVERY SIGN IS A NAME. A hall is a walkable shed with eleven rooms, an
open face and a yard, and the signs above answer only "what is this
called?". A working building also answers "which way out?", "where do we
gather?", "which door is this?", "which machine is this?" and "what is in
force here?" - so the registry carries a pointing chevron, a muster beacon,
a stencilled door number, a machine tag and a hatched notice. Each is a
shape of its own rather than a name-plate in another colour, because a sign
that has to be read before it can be told apart is the failure this whole
registry exists to fix. All five are DERIVED: they are read off plans and
records this bundle already holds, they are training signage in a drawn
building, and none of them is life-safety equipment or an approved sign.

FIELD OF VISION. A sign also reacts to being looked at. Each frame every
label is scored on how near the centre of view it is and how far away it
stands; the score drives opacity, size and tint, so what you are facing
comes forward and what is behind your shoulder recedes. The single most
centred sign within reach is the FOCUS, and it is brightened and lifted so
a learner can tell what they are about to act on without a cursor - which
is also what makes this work in a headset, where there is no cursor to
have.

HONESTY. A shape is a convention this bundle invented, not a standard.
Nothing about a label changes what a thing IS: the focus treatment is
presentation, no label is a score, and the dashed outline on a SCHEMATIC
sign is the same claim the registry behind it already makes.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

# One bundle version, read from the manifest rather than typed here.
PACK_VERSION = json.load(open(ROOT / 'pack/manifest.json'))['pack_version']
BUILT = "2026-09-17"

# ------------------------------------------------------------- the shapes ---
# Each is drawn on a canvas by the page; `draws` is the contract the suite
# holds the page to.
SHAPES = {
    'speech': {'draws': 'a rounded bubble with a tail pointing down at the '
                        'speaker', 'radius': 22, 'tail': True,
               'reads_as': 'somebody who will answer a question'},
    'tab': {'draws': 'a rounded plate with a downward pointer',
            'radius': 16, 'tail': True,
            'reads_as': 'a place you can go into'},
    'chip': {'draws': 'a small full-radius pill', 'radius': 999,
             'tail': False, 'reads_as': 'a thing you can open or pick up'},
    'plate': {'draws': 'a chamfered rectangle with a left accent stripe',
              'radius': 6, 'tail': False,
              'reads_as': 'a room, or a part of a place you are already in'},
    'pin': {'draws': 'a plate on a stem ending in a dot',
            'radius': 12, 'tail': False, 'stem': True,
            'reads_as': 'somewhere real, out there'},
    'banner': {'draws': 'a wide bar with a heavy left accent stripe',
               'radius': 4, 'tail': False,
               'reads_as': 'a whole district or section'},
    'marquee': {'draws': 'a large plate with a rule above the title and '
                         'letter-spaced caps', 'radius': 10, 'tail': False,
                'reads_as': 'the name of the whole place'},
    'ribbon': {'draws': 'a slanted parallelogram', 'radius': 2,
               'tail': False, 'reads_as': 'a route or a distance'},
    'ghost': {'draws': 'no plate at all - text with a shadow, so it does '
                       'not compete with what it labels', 'radius': 0,
              'tail': False, 'reads_as': 'a detail, there if you look'},
    'readout': {'draws': 'a dark bordered box in monospace',
                'radius': 4, 'tail': False,
                'reads_as': 'a number a machine measured'},

    # The signs a walkable building carries that a name-plate cannot. A hall
    # is a shed with eleven rooms, an open face and a yard, and until now
    # every sign in it answered the question "what is this called?". A real
    # floor also answers "which way out?", "where do we gather?", "which
    # door is this?", "which machine is this?" and "what is in force here?" -
    # five questions a name never answers. None of them is a name-plate in
    # another colour: each takes the shape the eye already reads on a wall,
    # because a sign that has to be READ to be told apart is the failure
    # this registry exists to fix.
    'chevron': {'draws': 'a plate whose leading edge runs out to a point, so '
                         'the plate itself points the way', 'radius': 4,
                'tail': False,
                'reads_as': 'the way out, and which way it runs'},
    'beacon': {'draws': 'a plate with a ringed dot struck at its leading end '
                        'and the text set in after it', 'radius': 10,
               'tail': False,
               'reads_as': 'a place to gather, marked so it can be found'},
    'stencil': {'draws': 'a hard-cornered square with a punched hole at its '
                         'head and a heavy accent border', 'radius': 0,
                'tail': False,
                'reads_as': 'the number a door answers to'},
    'tag': {'draws': 'a rectangle with its head corner cut away and an eyelet '
                     'punched through it, like a tag wired to a machine',
            'radius': 3, 'tail': False,
            'reads_as': 'the identity of one piece of kit'},
    'notice': {'draws': 'a plate banded top and bottom with diagonal hatching '
                        'in the accent colour', 'radius': 5, 'tail': False,
               'reads_as': 'a condition in force in this space, not a name'},
}

# ------------------------------------------------------------ ornaments ---
# A small mark drawn on a plate, for the one job a shape and an accent
# cannot do between them: separating two kinds that would otherwise be the
# same bitmap. The vocabulary is declared here and the asserts at the foot
# fail closed both ways, so a kind cannot name an ornament nobody draws and
# an ornament cannot sit here unused - the same rule the shapes keep.
ORNAMENTS = {
    'rule_under': 'a second rule under the title as well as over it, so the '
                  'Academy\'s own marquee is not just a campus marquee with '
                  'a different word on it',
}

# ------------------------------------------------------------- the palette ---
PALETTE = {
    'ink': '#E8EDEC',
    'muted': '#93A3A6',
    'plate': 'rgba(12,17,19,.84)',
    'plate_focus': 'rgba(18,26,29,.94)',
    'mark': '#E8A33D',            # the Academy's amber, for focus
    'steel': '#41C4D4',
    'good': '#5CB584',
    'crit': '#E07C68',
    'recorded': '#5CB584',        # provenance: solid green accent
    'derived': '#41C4D4',
    'schematic': '#93A3A6',       # provenance: muted, drawn dashed
}

# ----------------------------------------------------------- the type scale ---
TYPE = {
    'display': '"Barlow Condensed", system-ui, sans-serif',
    'body': '"IBM Plex Sans", system-ui, sans-serif',
    'mono': '"IBM Plex Mono", ui-monospace, monospace',
    'title_px': 44,
    'sub_px': 27,
    'chip_px': 34,
    'tracking_marquee': 3,
    'note': 'display for names, body for the line under them, mono for '
            'anything a machine measured - three faces, three ranks, and '
            'no fourth',
}

# --------------------------------------------------------------- the kinds ---
# `accent` is either a palette key or 'district' (take the hall's own hue).
KINDS = {
    'campus': {'shape': 'marquee', 'accent': 'mark', 'face': 'display',
               'min_focus': .15, 'hide_beyond_m': 0,
               'what': 'the name of a campus, over its plaza'},
    'district': {'shape': 'banner', 'accent': 'district', 'face': 'display',
                 'min_focus': .2, 'hide_beyond_m': 0,
                 'what': 'a district of halls, over its block'},
    'hall': {'shape': 'tab', 'accent': 'district', 'face': 'display',
             'min_focus': .25, 'hide_beyond_m': 0,
             'what': 'a hall you can walk into'},
    'room': {'shape': 'plate', 'accent': 'steel', 'face': 'display',
             'min_focus': .2, 'hide_beyond_m': 0,
             'what': 'a room inside a hall'},
    'advisor': {'shape': 'speech', 'accent': 'mark', 'face': 'display',
                'min_focus': .3, 'hide_beyond_m': 0,
                'what': 'somebody standing there who will answer questions'},
    'station': {'shape': 'chip', 'accent': 'steel', 'face': 'display',
                'min_focus': .25, 'hide_beyond_m': 46,
                'what': 'a training station'},
    'crib': {'shape': 'chip', 'accent': 'mark', 'face': 'display',
             'min_focus': .25, 'hide_beyond_m': 46,
             'what': 'a tool crib you can open'},
    'fixture': {'shape': 'ghost', 'accent': 'muted', 'face': 'body',
                'min_focus': .12, 'hide_beyond_m': 26,
                'what': 'a bench or a piece of kit, named quietly'},
    'anchor': {'shape': 'pin', 'accent': 'recorded', 'face': 'display',
               'min_focus': .2, 'hide_beyond_m': 0, 'provenance': 'RECORDED',
               'what': 'a real place, at its recorded distance and bearing'},
    'schematic': {'shape': 'pin', 'accent': 'schematic', 'face': 'display',
                  'min_focus': .2, 'hide_beyond_m': 0, 'dashed': True,
                  'provenance': 'SCHEMATIC',
                  'what': 'a drawn place - the dashed outline is the claim'},
    'route': {'shape': 'ribbon', 'accent': 'derived', 'face': 'mono',
              'min_focus': .2, 'hide_beyond_m': 0, 'provenance': 'DERIVED',
              'what': 'a distance between two recorded points'},
    'readout': {'shape': 'readout', 'accent': 'steel', 'face': 'mono',
                'min_focus': .35, 'hide_beyond_m': 0,
                'what': 'a measured number, from a seat or a chart'},
    # The Academy's own marquee drew exactly the campus marquee: same shape,
    # same accent, same face, same caps - two kinds that were one bitmap, and
    # they stand on the same board in the campus-network view, so a reader
    # met two identical signs saying different kinds of thing. The second
    # rule under the title is what tells them apart without a word being
    # read, which is the whole promise of this registry.
    'brand': {'shape': 'marquee', 'accent': 'mark', 'face': 'display',
              'min_focus': .1, 'hide_beyond_m': 0, 'ornament': 'rule_under',
              'what': 'the Academy itself'},
    # A door placard. The PPE a room asks for has been in the surfaces
    # registry since §24.2 and had nowhere to appear except a panel you had
    # to open - so a learner could walk into a room without ever being told
    # what it expects them to be wearing. It reads in `crit` because it is
    # the one sign in this world that is a REQUIREMENT rather than a name,
    # and it sits low, at the door, where it would actually be hung.
    'placard': {'shape': 'plate', 'accent': 'crit', 'face': 'body',
                'min_focus': .18, 'hide_beyond_m': 20,
                'provenance': 'DERIVED',
                'what': 'what a room requires of you, read at its door'},

    # ---- wayfinding ------------------------------------------------------
    # Every sign above answers "what is this called?". A hall is a walkable
    # shed with eleven rooms, one open face and a yard in front of it, and a
    # learner standing in the middle of it - in a headset, with no map and no
    # cursor - had no sign that answered "which way out?". The chevron is the
    # only sign in this registry that is an INSTRUCTION about movement, so it
    # is the only one whose plate has a direction: it points, and a sign that
    # points cannot be mistaken for a sign that names.
    # It hides at 30 m, and that is not a cost saving. Every OTHER kind in
    # this registry that never hides is a place NAME - a campus, a
    # district, a hall, a recorded anchor - something you are meant to read
    # from across a green. A way-out sign is read from inside the room it
    # serves, like the placard (20 m), the door number (14 m), the machine
    # tag (18 m) and the hazard notice (22 m) beside it. Hung at 0 it stood
    # legible from 55 m outside the building, where it competed with the
    # hall's own name plate and was read as one - which is what happened
    # the first time three of them were hung.
    'egress': {'shape': 'chevron', 'accent': 'good', 'face': 'display',
               'min_focus': .3, 'hide_beyond_m': 30, 'provenance': 'DERIVED',
               'what': 'the way out of a hall, read off the floor plan the '
                       'bundle drew and pointing along it'},
    # Where a floor goes when it empties. A drill that ends nowhere is a
    # drill nobody can be marked present at, and the apron in front of the
    # open face is the only part of a hall that is outside it and still in
    # it. It wears the same green as the chevron because it is the other end
    # of the same movement, and a different shape because standing still at
    # a point is not the same instruction as walking along a route.
    # 36 m, a little further than the chevron: the beacon marks a point on
    # the apron OUTSIDE the building, and the walk to it starts inside.
    'muster': {'shape': 'beacon', 'accent': 'good', 'face': 'display',
               'min_focus': .28, 'hide_beyond_m': 36, 'provenance': 'DERIVED',
               'what': 'where a hall gathers when it empties, off the same '
                       'plan the route is read from'},
    # A door number. Rooms have names, and a name is what you call a place
    # when you are standing in it; a number is what you call it over a radio
    # to somebody who is not. It is the first sign in this registry that is
    # an IDENTIFIER rather than a name, which is why it is set in mono - the
    # same rank the bundle gives every other value a machine assigned - and
    # why it is small, hard-cornered and quiet: nobody reads a door number
    # for pleasure, they read it once and say it out loud.
    'door': {'shape': 'stencil', 'accent': 'muted', 'face': 'mono',
             'min_focus': .16, 'hide_beyond_m': 14, 'provenance': 'DERIVED',
             'what': 'the number a door answers to, derived from the hall '
                     'and the room it opens into'},
    # ---- equipment identification ---------------------------------------
    # A fixture wears a ghost sign: a bench, named quietly, because its name
    # is a courtesy. A machine is not a courtesy - it is a thing with a
    # history, which is maintained, locked out, handed over and written down
    # against an identity, and none of that works if the only thing on it is
    # what it is called. The tag is the identity, so it is mono like the door
    # number and shaped like the thing it imitates: a tag wired to a machine.
    'asset': {'shape': 'tag', 'accent': 'steel', 'face': 'mono',
              'min_focus': .16, 'hide_beyond_m': 18, 'provenance': 'DERIVED',
              'what': 'the identifier of one piece of kit, derived from its '
                      'hall, its room and its place in them'},
    # ---- hazard and permit notices --------------------------------------
    # The placard above says what a room requires you to WEAR. That is not
    # the same claim as what is in force in the space right now - a permit
    # open, a supply isolated, a surface still hot - and putting the two on
    # one plate would have made a standing requirement and a temporary
    # condition read alike. A condition is not a name and not a dress code,
    # so it takes the hatched band: the one pattern in this registry that
    # means "this is not about what this place is called".
    'hazard': {'shape': 'notice', 'accent': 'crit', 'face': 'body',
               'min_focus': .22, 'hide_beyond_m': 22, 'provenance': 'DERIVED',
               'what': 'a condition in force in a space, off the hazards its '
                       'own conditions record already holds'},
}

# ------------------------------------------------- how a sign reads the view ---
FOCUS = {
    'cone_deg': 34,
    'floor': .34,
    'lift_m': .18,
    'grow': .16,
    'ease': 6.0,
    'near_full_m': 18,
    # Distance is judged RELATIVE to how far out the view is, never in
    # absolute metres: a sign 200 m away is far when you are walking and
    # near when you are looking at the whole campus from above. The
    # reference is the camera's own distance to what it is looking at.
    'fade_from_rel': 1.45,
    'fade_to_rel': 3.1,
    'contract': 'each frame a label is scored 0..1 on the angle between the '
                'view direction and the label, inside the declared cone, '
                'and again on distance relative to how far out the view '
                'is; the two are multiplied. The score '
                'drives opacity (never below the floor while in range), '
                'size and tint, and it is eased rather than snapped so '
                'nothing flickers as the head turns.',
    # A world-space sign grows without limit as you approach it and
    # vanishes as you leave. Both ends are clamped: a label may never take
    # up more than max_frac of the viewport's height, nor less than
    # min_frac while it is in range, so signage stays readable and never
    # dominates the thing it is labelling.
    'screen': {'min_frac': .034, 'max_frac': .085,
               'note': 'a fraction of viewport height, applied after the '
                       'focus grow, so the clamp is what the eye finally '
                       'sees'},
    'focus_rule': 'the single most centred label within reach is the FOCUS: '
                  'it takes the accent tint and lifts by lift_m, so a '
                  'learner can see what they are about to act on without a '
                  'cursor - which is what makes this work in a headset, '
                  'where there is no cursor to have.',
}

# ------------------------------------------- when two signs land together ---
# The focus rule above scores every sign ON ITS OWN. It can tell you how
# centred a sign is and how far off it stands; it cannot tell you that two
# signs have landed on the same pixels, because it never compares a pair.
#
# They do land on the same pixels, and it was not a near miss. Measured in
# a browser at 1280x800 through the page's own rectangle hook, the default
# hall view put twenty-two signs on screen and fifteen PAIRS of them
# overlapped, five of those covering more than half of the smaller plate:
# the Classroom plate, three training-ladder plates and seven advisor
# bubbles piled into stacks you could not read a word of. The region board
# was worse - a hundred and twenty-five signs and four hundred and
# eighty-eight overlapping pairs.
#
# The cause is arithmetic, not carelessness. `screen.min_frac` promises
# that a sign never shrinks below a readable band of the viewport, so at a
# distance EVERY sign is drawn at the same minimum height. Signs a metre
# apart in the world are then a few pixels apart on screen while each is
# tens of pixels tall, and they cover each other however carefully they
# were placed.
#
# So a sign that is covered steps back, and this declares WHICH ONE steps
# back. The order is not "whichever scored higher this frame" - that is a
# coin toss between a room plate and the advisor standing in the middle of
# it, and it would flip as the view turned. It is a fixed precedence,
# read from the top: the marquee over a place outranks the name of a room
# inside it, a room outranks the person standing in it, and a measured
# distance yields to all of them. Where you ARE beats who is there beats
# what it is called beats what was measured.
#
# Nothing is deleted and nothing is dropped from the scene. A covered sign
# fades, on the same easing as the focus score, and comes back the moment
# the view moves enough to uncover it - which is why the two thresholds
# differ: a sign hides when it is covered past `cover_hide` and does not
# return until coverage falls under `cover_show`, so a sign sitting exactly
# on the line cannot flicker.
#
# `cover_hide` is set where it is because of what a plate CONTAINS, not by
# eye. A plate is a title with a second line under it, and that second line
# is the lower third or so of the plate: a cover of a third of the plate's
# area can therefore swallow the whole of it, which is what "Materials
# Store / Materials" losing its strand name looked like. A cover of a
# seventh is a corner or a rule's worth of one end - the plate still reads.
# Measured at 1280x800 in the default hall, moving the threshold from a
# third to a seventh took the surviving overlaps from four pairs (worst
# 21%) to two (worst 11%), and the region board from 39 pairs to 12 with
# nothing over 15%.
PRECEDENCE = [
    'brand', 'campus', 'district', 'hall',      # where you are
    'egress', 'muster', 'hazard', 'placard',    # what you must do about it
    'room', 'station', 'crib', 'door',          # what this is called
    'advisor', 'anchor', 'schematic',           # who and what is out there
    'asset', 'route', 'readout', 'fixture',     # what was measured
]
DECLUTTER = {
    'precedence': PRECEDENCE,
    'cover_hide': .15,
    'cover_show': .07,
    'min_op': .05,
    'rule': 'two signs are compared as the rectangles they actually occupy '
            'on screen. Taken in precedence order, a sign that is covered '
            'by more than cover_hide of the smaller of the two plates by a '
            'sign ahead of it steps back; it returns when coverage falls '
            'under cover_show. Coverage is eased on the focus easing, so a '
            'sign fades rather than blinks.',
    'honest': 'a sign that steps back is not deleted, not disposed and not '
              'dropped from the label set or from its group; it is still '
              'scored every frame and it comes back as soon as the view '
              'moves enough to uncover it. What changes is its opacity, '
              'and a sign faded to min_op is switched off, so while it is '
              'covered it is NOT drawn and NOT on screen. That is the '
              'honest cost of the rule and a harness counting on-screen '
              'signs will not count it. The visible-MESH count cannot see '
              'this either way - a sign is a sprite and a sprite was never '
              'one of those meshes - so it is the SIGN floor in '
              'web/eval_scene.mjs, and not the mesh floor, that stops this '
              'rule being turned into a way of emptying a building.',
    'measured': 'the count this exists to hold down is overlapping PAIRS of '
                'on-screen sign rectangles, measured in a browser by '
                'web/eval_scene.mjs through the page\'s own '
                '__tc3dLabelRects() hook, against a ceiling declared there '
                'per view.',
}


# ------------------------------------------------ what a sign may not say ---
# A sign that wears a standards body's initials, a standard's designation or
# a regulator's name is claiming an authority this bundle does not have, and
# a reader cannot tell a drawn sign from an inspected one by looking at it -
# which is precisely the confusion signage is good at causing. The new
# wayfinding kinds make that risk real for the first time: an exit chevron
# and a hazard notice are the two signs in a building people are trained to
# obey without thinking.
#
# The list is explicit rather than a clever pattern, because a lint reaches
# exactly the phrasings somebody thought of - a miss is a token to add, not
# a reason to trust the pass. The one pattern is for designations of the
# form <letters><digits>.<digits>, which are a shape rather than a word and
# cannot be enumerated.
#
# The STATIONS pack reads this list rather than keeping its own copy: the
# words on a door placard and the words on a station's checklist are printed
# on the same kind of sign, in the same building, and there is one list of
# what they may not say.
NO_MARKS = {
    'why': 'no sign in this world borrows a standards body, a standard\'s '
           'designation, a regulator or a real trade organisation: the '
           'shapes are this bundle\'s own convention and the words are '
           'plain practice, so nothing here can be mistaken for an '
           'inspected, approved or certified sign.',
    'tokens': [
        # standards bodies and regulators, by the initials they are known by
        'osha', 'ansi', 'astm', 'nfpa', 'niosh', 'msha', 'epa', 'cfr',
        'iso', 'iec', 'csa', 'din', 'aci', 'aws', 'bia', 'ibc', 'irc',
        'tms', 'ada', 'ul listed', 'code-compliant', 'code compliant',
        'building code', 'per code', 'to code',
        # real trade organisations, whose training this is not
        'bac', 'jatc',
        # designations and citations that name a document rather than a
        # practice, including the ones the recovered curriculum carried
        'c39', 'table 1', 'secretary of the interior', '811',
    ],
    'patterns': [r'\b[a-z]{1,4}[ -]?\d{1,4}\.\d+\b'],
}


def borrowed_marks(text):
    """Every mark the given text borrows, lowercased, in the order found.

    Returns a list rather than a bool so the failure names what it found:
    a lint that says only "no" leaves the author guessing.
    """
    import re
    low = ' ' + ' '.join(str(text).lower().split()) + ' '
    hits = [t for t in NO_MARKS['tokens']
            if re.search(r'(?<![a-z0-9])' + re.escape(t) + r'(?![a-z0-9])', low)]
    for pat in NO_MARKS['patterns']:
        hits += re.findall(pat, low)
    return hits


HONESTY = {
    'convention': 'these shapes are a convention this bundle invented, not '
                  'a standard anyone else uses; the legend is in the wiki '
                  'and on the page rather than assumed.',
    'presentation_only': 'focus is presentation. Looking at a label changes '
                         'nothing: no label is a score, none gates anything, '
                         'and no grader reads which sign a learner faced.',
    'provenance': 'a dashed outline on a SCHEMATIC sign and a solid accent '
                  'on a RECORDED one restate the claim the registry behind '
                  'them already makes - the label never upgrades a claim.',
    'legibility': 'a label never shrinks below the declared floor while it '
                  'is in range, carries a shadow so it survives a bright '
                  'sky, and is drawn at device pixel ratio so it is not '
                  'soft on a phone.',
    'reduced_motion': 'viewers who ask for reduced motion keep the shapes '
                      'and the colours and lose the easing: labels sit at '
                      'full opacity rather than breathing as the head '
                      'turns.',
    # Wayfinding is the one part of real signage that is a life-safety
    # device, inspected and approved by somebody, and this is not that. The
    # sign says what the drawn plan says and nothing more.
    'wayfinding': 'an exit chevron, a muster beacon and a door number are a '
                  'reading of the floor plan this bundle drew, in a building '
                  'that does not exist. They are training signage: not '
                  'life-safety equipment, not an inspected route, not an '
                  'approved sign, and not a substitute for the signs on the '
                  'wall of the hall a learner is actually standing in.',
    'identification': 'a door number and an asset tag are identifiers this '
                      'bundle assigned, not numbers anybody else uses: they '
                      'are derived from the hall, the room and the fixture '
                      'that already exist in the registries, and they are '
                      'set in mono because an identifier is a value a '
                      'machine assigned, which is the rank this type scale '
                      'already gives such things.',
    'notices': 'a hazard notice states the condition the room\'s own '
               'conditions record holds. It does not classify, rate or '
               'permit anything, it cites nobody, and a space with no '
               'recorded condition gets no notice rather than one that says '
               'there is nothing to say.',
    'no_marks': NO_MARKS['why'],
    'xr_panel': 'in a WebXR session the readout kind is reused for the '
                'wrist panel: one sign per dash gauge, drawn by the same '
                'label() the world signs use, off the same gauges() values '
                'the dash reads, with a warning readout wearing the crit '
                'accent the dash uses. Those signs ride the left controller '
                '(or hang ahead of the rig without one) at a fixed size and '
                'full opacity - they are on the hand, not in the world, so '
                'the view-direction scoring above does not apply to them. '
                'Verified against a mocked WebXR session only, never a '
                'physical headset.',
}

# ---------------------------------------------------------------- checks ---
districts = json.load(open(ROOT / 'unions/registry/districts.json'))['districts']

for kk, k in KINDS.items():
    assert k['shape'] in SHAPES, f'{kk}: shape {k["shape"]} is not drawn'
    assert k['face'] in ('display', 'body', 'mono'), f'{kk}: unknown face'
    assert k['accent'] == 'district' or k['accent'] in PALETTE, \
        f'{kk}: accent {k["accent"]} is not in the palette'
    assert 0 < k['min_focus'] < 1, f'{kk}: a floor must be a fraction'
    assert k['what'], f'{kk}: a kind nobody can explain is a kind nobody needs'

# every shape earns its place
used = {k['shape'] for k in KINDS.values()}
assert used == set(SHAPES), f'shapes drawn but never used: {sorted(set(SHAPES) - used)}'

# and every ornament earns its place, on the same terms
worn = {k['ornament'] for k in KINDS.values() if 'ornament' in k}
assert worn <= set(ORNAMENTS), f'ornaments nobody draws: {sorted(worn - set(ORNAMENTS))}'
assert worn == set(ORNAMENTS), \
    f'ornaments declared and never worn: {sorted(set(ORNAMENTS) - worn)}'

# NO TWO KINDS MAY DRAW THE SAME SIGN. `campus` and `brand` did: same
# marquee, same amber, same face, same caps - one bitmap under two names,
# on the same board, which is the exact failure this registry was built to
# prevent. A kind is told apart by what is DRAWN, so the signature is the
# drawn properties and nothing else: the shape, the accent, whether the
# outline is dashed, and any ornament. A `what` string is not a signature,
# because nobody reads it off the sign.
signature = {}
for kk, k in KINDS.items():
    sig = (k['shape'], k['accent'], bool(k.get('dashed')), k.get('ornament'))
    assert sig not in signature, (
        f'{kk} draws exactly what {signature[sig]} draws: two kinds, one '
        f'bitmap. Give one of them its own shape, accent or ornament.')
    signature[sig] = kk
    if 'ornament' in k:
        assert k['ornament'] in ORNAMENTS, f'{kk}: no such ornament'

# A sign may not borrow somebody else's authority, and the words on every
# sign this registry describes are checked against the one list of marks the
# bundle keeps - including the words in the honesty block itself, which is
# where an excuse would be written if one were ever going to be.
for kk, k in KINDS.items():
    assert not borrowed_marks(k['what']), \
        f'{kk}: its description borrows {borrowed_marks(k["what"])}'
for sk, sh in SHAPES.items():
    assert not borrowed_marks(sh['draws'] + ' ' + sh['reads_as']), \
        f'{sk}: its description borrows a mark'

# provenance words stay the bundle's own, and only those. A wayfinding sign
# is DERIVED and says so: the route, the muster point, the door number and
# the asset tag are all read off plans and records this bundle already
# holds, and none of them is a thing anybody recorded in the world.
PROVENANCE = ('RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED')
for kk, k in KINDS.items():
    if 'provenance' in k:
        assert k['provenance'] in PROVENANCE, \
            f'{kk}: {k["provenance"]} is not one of the bundle\'s words'
for kk in ('egress', 'muster', 'door', 'asset', 'hazard'):
    assert KINDS[kk].get('provenance') == 'DERIVED', \
        f'{kk} is read off a plan or a record, so it must say DERIVED'

assert FOCUS['floor'] < 1 and FOCUS['cone_deg'] > 10, 'the cone must be a cone'

# The precedence is a TOTAL order over the kinds: every kind names its place
# exactly once. A kind missing from it would have no declared answer to
# "what do you yield to?", and the page fails closed on one rather than
# guessing, so the guess must not be possible here either.
assert sorted(PRECEDENCE) == sorted(KINDS), (
    'declutter.precedence must rank every kind exactly once - missing '
    f'{sorted(set(KINDS) - set(PRECEDENCE))}, unknown '
    f'{sorted(set(PRECEDENCE) - set(KINDS))}, '
    f'{len(PRECEDENCE)} entries against {len(KINDS)} kinds')
assert len(set(PRECEDENCE)) == len(PRECEDENCE), \
    'declutter.precedence ranks a kind twice'
assert 0 < DECLUTTER['cover_show'] < DECLUTTER['cover_hide'] < 1, (
    'a sign must have to be covered MORE to hide than to stay hidden, or it '
    'flickers on the threshold')
assert 0 < DECLUTTER['min_op'] < FOCUS['floor'], (
    'the opacity a stepped-back sign fades to must be under the floor a lit '
    'sign is held above, or nothing ever reads as hidden')
for _k, _v in DECLUTTER.items():
    if isinstance(_v, str):
        assert not borrowed_marks(_v), \
            f'declutter.{_k} borrows {borrowed_marks(_v)}'

assert 0 < FOCUS['screen']['min_frac'] < FOCUS['screen']['max_frac'] < .5, \
    'the on-screen clamp must be a sane band of the viewport'
assert FOCUS['fade_from_rel'] < FOCUS['fade_to_rel'], 'fade runs outward'
assert FOCUS['fade_from_rel'] > 1, \
    'a sign at the thing you are looking at must be fully lit'

# ------------------------------------------------- signs not yet drawn ---
# A kind reaches the page only if the page can draw its SHAPE. The registry
# travels into the page whole, so a kind's id appears in the page's data the
# moment the page is regenerated whether anybody drew it or not; the honest
# gate is the `case` branch in labelShape(), which is why the list below is
# computed from the page rather than believed.
#
# These five kinds are declared here and web/build_3d.py has not grown a
# branch for them yet. The list is a POLICY and not a skip, and it fails
# closed in BOTH directions: a kind whose shape the page cannot draw and
# which is not named here fails the build, and a kind named here whose shape
# the page HAS learned to draw fails it too, so the branch landing is what
# forces the name off this list. Nothing silently stays pending.
# ...and this list is now EMPTY, which is what it was for.
#
# All five landed together: web/build_3d.py grew a `case` for the chevron,
# the beacon, the stencil, the tag and the notice, and the hall hangs all
# five - a chevron in each back corner pointing at the one open face, a
# beacon on the apron, a stencilled number on every way in, a tag on every
# machine, and a hatched notice in every room whose own record names a
# hazard. Until they landed, a kind on this list fell through that switch
# and drew NO PLATE: bare text with a shadow, which is what a campus name
# looks like from across a green, and which is exactly how the first three
# hung were read when somebody looked at the hall.
#
# The gate stays. It fails closed in both directions, so the next kind
# declared here without a drawing branch fails this build, and this list
# going empty is the only way to say the registry has no unpaid promises.
PENDING_PAGE = []

BOOTSTRAP = '--bootstrap' in __import__('sys').argv
if BOOTSTRAP:
    # Bootstrap runs before there is a page to read, so the declared list
    # stands: this is the one place a value here is taken on trust, it is
    # deliberate, and the real run below recomputes and contradicts it.
    pending = sorted(PENDING_PAGE)
else:
    page = (ROOT / 'web/trade_craft_3d.html').read_text()
    drawable = {sk for sk in SHAPES if f"case '{sk}'" in page}
    pending = sorted(kk for kk, k in KINDS.items() if k['shape'] not in drawable)
    assert pending == sorted(PENDING_PAGE), (
        'PENDING_PAGE disagrees with the page: the page now draws '
        f'{sorted(set(PENDING_PAGE) - set(pending))} (take them off the '
        f'list) and cannot draw {sorted(set(pending) - set(PENDING_PAGE))} '
        '(a kind with no drawing branch must be declared pending).')
    for kk in KINDS:
        if kk in pending:
            continue
        assert f'"{kk}"' in page, f'label kind {kk} never reaches the page'
    for sk in SHAPES:
        if sk in {KINDS[kk]['shape'] for kk in pending}:
            continue
        assert f"case '{sk}'" in page, f'the page cannot draw shape {sk}'
    for fn in ('function label(', 'function labelShape(', 'function labelStep('):
        assert fn in page, f'the page does not build labels: {fn} missing'
    # focus must be presentation: no grader may read it
    for grader in ('function score', 'function grade'):
        for chunk in page.split(grader)[1:]:
            assert 'labelFocus' not in chunk[:2500], \
                'a grader reads label focus; focus is presentation only'

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

doc = {
    'pack': 'smartcitix-trade-craft-academy-labels',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'honesty': HONESTY,
    'counts': {'kinds': len(KINDS), 'shapes': len(SHAPES),
               'ornaments': len(ORNAMENTS), 'district_hues': len(districts),
               'drawn': len(KINDS) - len(pending)},
    'pending_page': pending,
    'no_marks': NO_MARKS,
    'shapes': SHAPES,
    'ornaments': ORNAMENTS,
    'palette': PALETTE,
    'type': TYPE,
    'kinds': KINDS,
    'focus': FOCUS,
    'declutter': DECLUTTER,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'labels.json').write_text(json.dumps(doc, indent=1) + '\n')
print(f"labels: {len(KINDS)} kinds over {len(SHAPES)} shapes "
      f"({len(pending)} awaiting a drawing branch), "
      f"{FOCUS['cone_deg']}-degree focus cone (source stamp {stamp})")
