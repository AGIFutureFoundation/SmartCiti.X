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

PACK_VERSION = "3.2.0"
BUILT = "2026-09-11"

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
    'brand': {'shape': 'marquee', 'accent': 'mark', 'face': 'display',
              'min_focus': .1, 'hide_beyond_m': 0,
              'what': 'the Academy itself'},
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

# provenance words stay the bundle's three, and only those
for kk, k in KINDS.items():
    if 'provenance' in k:
        assert k['provenance'] in ('RECORDED', 'DERIVED', 'SCHEMATIC'), \
            f'{kk}: {k["provenance"]} is not one of the three words'

assert FOCUS['floor'] < 1 and FOCUS['cone_deg'] > 10, 'the cone must be a cone'
assert 0 < FOCUS['screen']['min_frac'] < FOCUS['screen']['max_frac'] < .5, \
    'the on-screen clamp must be a sane band of the viewport'
assert FOCUS['fade_from_rel'] < FOCUS['fade_to_rel'], 'fade runs outward'
assert FOCUS['fade_from_rel'] > 1, \
    'a sign at the thing you are looking at must be fully lit'

BOOTSTRAP = '--bootstrap' in __import__('sys').argv
if not BOOTSTRAP:
    page = (ROOT / 'web/trade_craft_3d.html').read_text()
    for kk in KINDS:
        assert f'"{kk}"' in page, f'label kind {kk} never reaches the page'
    for sk in SHAPES:
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
               'district_hues': len(districts)},
    'shapes': SHAPES,
    'palette': PALETTE,
    'type': TYPE,
    'kinds': KINDS,
    'focus': FOCUS,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'labels.json').write_text(json.dumps(doc, indent=1) + '\n')
print(f"labels: {len(KINDS)} kinds over {len(SHAPES)} shapes, "
      f"{FOCUS['cone_deg']}-degree focus cone (source stamp {stamp})")
