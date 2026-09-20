#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the avatar pack builder.

The learner's avatar as data: locker sections (15–20 options each), the
CREW section carrying all 111 halls, and emotes (an emoji, a label, and a
procedural move the 3D page implements). The page renders a humanoid from
these ids — capsule body, hair, facial features, full workwear — and
stores the learner's choices in the device-local progress record.

EVERY OPTION IS NAMED, and every piece of protective equipment or trade
kit carries a note saying what hazard or what trade it answers. The wheel
draws a two-letter glyph and nothing else, so an unnamed option is an
unreadable one: the name is the option's only word, and the note is the
only place the locker says WHY a member would reach for it.

PROVENANCE: the parts, the colours and the notes are AUTHORED — typed
from general public knowledge of the trades, not cross-checked against
any standard this build can read. They are not the standard, not a
specification, and not a substitute for a qualified person on site.

THE GUARANTEE, stated and tested: avatars are COSMETIC ONLY. No option is
locked, none is paid, and none affects scoring, access, progression or
anything the rubrics measure.

THE MARKS: picking a crew stamps its mark on the vest, the shirt and the
headwear — a three-letter hall code on a shield in the district's hue.
These are the Academy's OWN insignia, generated from its roster (the same
codes the campus map prints); they are not, and do not imitate, any real
union's logo or emblem — no local is named and none is drawn.
"""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'web'))
from mapdata import HUES, make_codes  # noqa: E402

# One bundle version, read from the manifest rather than typed here (this
# pack had drifted to 3.3.0 while ROADMAP said 3.2.0 was unified everywhere).
PACK_VERSION = json.load(open(ROOT / 'pack/manifest.json'))['pack_version']
BUILT = "2026-09-14"


def lerp_hex(a, b, t):
    av = [int(a[i:i+2], 16) for i in (1, 3, 5)]
    bv = [int(b[i:i+2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(av[i] + (bv[i] - av[i]) * t):02x}'
                         for i in range(3))


# 18 skin tones, an even walk from light to deep.
SKIN = ([lerp_hex('#f6ddc8', '#c98d5c', i / 8) for i in range(9)]
        + [lerp_hex('#b97a4b', '#3c2a1e', i / 8) for i in range(9)])

HAIR_COLORS = [
    ('black', '#141210'), ('soft-black', '#241f1c'), ('dark-brown', '#3a2a1c'),
    ('brown', '#553b24'), ('chestnut', '#6c4a2b'), ('auburn', '#7a3b22'),
    ('red', '#933a24'), ('ginger', '#b55a2c'), ('dark-blond', '#8a6b3e'),
    ('blond', '#c2a05e'), ('platinum', '#ddd0b0'), ('grey', '#8d8d8d'),
    ('silver', '#b9bcbe'), ('white', '#e8e8e6'), ('dyed-blue', '#2e5f8a'),
    ('dyed-green', '#2f6b4a'),
]

# One work-palette, reused by the three colour sections that dress cloth.
# All three take the WHOLE palette: the slices this pack used to take
# excluded white from headwear (the commonest hard-hat colour there is)
# and both hi-vis hues from trousers (which is what Class E trousers are
# made of), so the slices were forbidding real, ordinary workwear.
CLOTH = [
    ('hi-vis-orange', '#e8722a'), ('hi-vis-yellow', '#d9c22e'),
    ('safety-green', '#7ac142'), ('forest', '#3c6b45'), ('olive', '#5b6238'),
    ('slate', '#4a5a64'), ('navy', '#2c3e5a'), ('royal', '#2f4d8a'),
    ('steel-blue', '#4a7a96'), ('teal', '#2f6f6a'), ('crimson', '#a03a34'),
    ('rust', '#9c5a30'), ('duck-brown', '#a5793f'), ('sand', '#c2a878'),
    ('charcoal', '#33363a'), ('grey', '#6c7276'), ('stone', '#9a978c'),
    ('white', '#e6e6e2'),
]


def prettify(oid):
    """A swatch's name is its own id read aloud, so a colour cannot be
    named one thing in the wheel and identified as another in the record.
    The compound 'hi-vis' keeps its hyphen because that is how the trade
    writes it; every other hyphen is a word break."""
    s = oid.replace('hi-vis-', 'hi-vis ').replace('-', ' ')
    return s[0].upper() + s[1:]


def coloropts(pairs):
    return [{'id': i, 'value': v, 'name': prettify(i)} for i, v in pairs]


def styleopts(items):
    """A wedge needs three things and sometimes four: the id the page
    renders from, the two-letter glyph the wedge draws, the name the
    locker says out loud, and — where the option is protective equipment
    or trade kit rather than plain clothes — the note that says which
    hazard or which trade it answers."""
    out = []
    for it in items:
        o = {'id': it[0], 'glyph': it[1], 'name': it[2]}
        if len(it) > 3:
            o['note'] = it[3]
        out.append(o)
    return out


SECTIONS = [
    {'id': 'build', 'emoji': '\U0001f9cd', 'label': 'Build', 'kind': 'style',
     'options': [
         {'id': f'{h_id}-{w_id}', 'glyph': f'{hg}{wg}',
          'name': f'{h_id.capitalize()} · {w_id}',
          'scale': [w, h, round(w * .96, 2)]}
         for h_id, hg, h in [('short', 'S', .9), ('average', 'A', 1.0),
                             ('tall', 'T', 1.08), ('towering', 'X', 1.16)]
         for w_id, wg, w in [('slim', 's', .88), ('standard', 'm', 1.0),
                             ('broad', 'b', 1.12), ('heavy', 'h', 1.24)]
     ]},
    {'id': 'skin', 'emoji': '✋', 'label': 'Skin', 'kind': 'color',
     'options': [{'id': f'tone-{i+1:02d}', 'value': v,
                  'name': f'Tone {i+1:02d}'}
                 for i, v in enumerate(SKIN)]},
    {'id': 'hair', 'emoji': '\U0001f487', 'label': 'Hair', 'kind': 'style',
     'options': styleopts([
         ('bald', '–', 'Shaved'), ('buzz', 'bz', 'Buzz cut'),
         ('crew', 'cr', 'Crew cut'), ('short', 'sh', 'Short'),
         ('side-part', 'sp', 'Side part'), ('waves', 'wv', 'Waves'),
         ('curls', 'cu', 'Curls'), ('afro', 'af', 'Afro'),
         ('bob', 'bo', 'Bob'), ('bun', 'bn', 'Bun'),
         ('ponytail', 'pt', 'Ponytail'), ('braids', 'br', 'Braids'),
         ('locs', 'lc', 'Locs'), ('mohawk', 'mo', 'Mohawk'),
         ('long', 'lg', 'Long'), ('undercut', 'uc', 'Undercut'),
         # Protective styles that keep length off the neck and out of the
         # hat band are worn on every crew; the rack held braids and locs
         # but not the two commonest ways to wear textured hair to work.
         ('cornrows', 'co', 'Cornrows'), ('twists', 'tw', 'Twists')])},
    {'id': 'haircolor', 'emoji': '\U0001f3a8', 'label': 'Hair colour',
     'kind': 'color', 'options': coloropts(HAIR_COLORS)},
    {'id': 'eyes', 'emoji': '\U0001f441', 'label': 'Eyes', 'kind': 'color',
     'options': coloropts([
         ('dark-brown', '#3a2417'), ('brown', '#5b3a22'),
         ('light-brown', '#7a512e'), ('amber', '#9c6b2e'),
         ('hazel', '#7a6a35'), ('olive-green', '#5f6b3a'),
         ('green', '#3f7048'), ('emerald', '#2e7a5a'),
         ('grey-green', '#5f7a6a'), ('grey', '#6f7a80'),
         ('blue-grey', '#5a7086'), ('blue', '#3f6690'),
         ('deep-blue', '#2e4f7e'), ('violet-grey', '#6a5f7e'),
         ('near-black', '#241a12')])},
    {'id': 'facialhair', 'emoji': '\U0001f9d4', 'label': 'Facial hair',
     'kind': 'style', 'options': styleopts([
         ('none', '–', 'Clean shaven'), ('stubble', 'st', 'Stubble'),
         ('light-mustache', 'lm', 'Light moustache'),
         ('mustache', 'mu', 'Moustache'), ('handlebar', 'hb', 'Handlebar'),
         ('chin-strap', 'cs', 'Chin strap'),
         ('soul-patch', 'sp', 'Soul patch'), ('goatee', 'go', 'Goatee'),
         ('circle-beard', 'cb', 'Circle beard'),
         ('short-beard', 'sb', 'Short beard'),
         ('full-beard', 'fb', 'Full beard'),
         ('long-beard', 'lb', 'Long beard'),
         ('mutton-chops', 'mc', 'Mutton chops'), ('walrus', 'wa', 'Walrus'),
         ('garibaldi', 'ga', 'Garibaldi'),
         ('van-dyke', 'vd', 'Van Dyke'), ('chevron', 'ch', 'Chevron'),
         ('braided-beard', 'bb', 'Braided beard'),
         # A contained beard is the answer in the halls that work clean -
         # cleanroom trades, medical gas, food and pharma plants - and it
         # is a different thing from shaving one off.
         ('beard-net', 'bn', 'Beard net')])},
    {'id': 'headwear', 'emoji': '⛑', 'label': 'Headwear', 'kind': 'style',
     'options': styleopts([
         ('none', '–', 'Bare head',
          'No head protection: the classroom, the office and the locker, '
          'and nowhere a hard-hat sign is posted.'),
         ('hard-cap', 'hc', 'Cap-style hard hat',
          'The everyday shell against the falling object and the low '
          'steel overhead.'),
         ('full-brim', 'fu', 'Full-brim hard hat',
          'A brim all the way round carries rain and sun off the neck as '
          'well as taking the overhead hit.'),
         ('climbing', 'cl', 'Climbing-style helmet',
          'A chin strap and a deeper shell, for work at height where a '
          'hat that comes off is a hat that is gone.'),
         ('vintage', 'vi', 'Old-pattern shell',
          'The tall pre-war shell, kept for the parade and the '
          'photographs rather than the deck.'),
         ('carbon', 'ca', 'Composite shell',
          'A light shell for the long shift, where the weight of the hat '
          'is the complaint by hour eight.'),
         ('ball-cap', 'bc', 'Ball cap',
          'Cloth only: sun off the face where nothing overhead can '
          'fall.'),
         ('ball-cap-back', 'bb', 'Ball cap, reversed',
          'Worn backwards so a welding hood, a face shield or a scope '
          'can sit square.'),
         ('flat-cap', 'fc', 'Flat cap',
          'Cloth and low-brimmed, for the shop and the walk to it.'),
         ('beanie', 'be', 'Beanie',
          'Knit warmth for cold work with no overhead hazard.'),
         ('bucket', 'bu', 'Bucket hat',
          'Brimmed all round against sun and glare on open ground, the '
          'survey line included.'),
         ('welding-cap', 'we', 'Welding cap',
          'A cotton crown under the hood, taking spark and spatter off '
          'the scalp.'),
         ('visor', 'vs', 'Visor',
          'Brim and sweatband with the crown left open, for heat and '
          'glare indoors.'),
         ('headband', 'hb', 'Headband',
          'Keeps sweat out of the eyes and off the inside of a safety '
          'lens.'),
         ('bandana', 'ba', 'Bandana',
          'Cloth over the scalp, worn under the hood or under the '
          'shell.'),
         ('winter-liner', 'wl', 'Winter liner',
          'An insulated liner for cold work; on site it belongs under a '
          'shell, not instead of one.'),
         # The three hard-hat facts a locker with five shells and no words
         # was silently hiding: a vented shell buys air and gives up the
         # electrical rating, a liner goes UNDER the shell, and a bump cap
         # is not a hard hat however much it looks like one.
         ('vented-cap', 'vt', 'Vented hard hat',
          'Vents for heat, and conductive by design: a vented shell '
          'carries no electrical rating.'),
         ('hard-cap-liner', 'hl', 'Hard hat over liner',
          'The cold-weather assembly: the insulated liner underneath, '
          'the shell still doing the protecting.'),
         ('sun-shade', 'ss', 'Hard hat with sun shade',
          'A brim-and-neck shade clipped to the shell, for open ground '
          'in heat-illness weather.'),
         ('bump-cap', 'bp', 'Bump cap',
          'A thin shell for pipe racks and low clearances; it is not '
          'impact-rated and never stands in for a hard hat.')])},
    {'id': 'headcolor', 'emoji': '\U0001f7e1', 'label': 'Headwear colour',
     'kind': 'color', 'options': coloropts(CLOTH)},
    {'id': 'top', 'emoji': '\U0001f455', 'label': 'Top', 'kind': 'style',
     'options': styleopts([
         ('tee', 'te', 'Tee'), ('long-sleeve', 'ls', 'Long sleeve'),
         ('henley', 'he', 'Henley'), ('polo', 'po', 'Polo'),
         ('flannel', 'fl', 'Flannel'), ('hoodie', 'ho', 'Hoodie'),
         ('sweatshirt', 'sw', 'Sweatshirt'),
         ('denim-jacket', 'dj', 'Denim jacket'),
         ('chore-coat', 'cc', 'Chore coat'),
         ('coveralls', 'co', 'Coveralls',
          'One piece over the clothes, keeping dust and spatter off what '
          'goes home in the truck.'),
         ('hi-vis-tee', 'hv', 'Hi-vis tee',
          'High-visibility in short sleeve; a short-sleeved garment '
          'cannot carry the highest visibility class on its own.'),
         ('tank', 'ta', 'Tank'),
         ('thermal', 'th', 'Thermal base layer',
          'The layer under everything else when the work is cold and '
          'standing still.'),
         ('rain-shell', 'ra', 'Rain shell',
          'A waterproof layer over the working clothes for a wet '
          'shift.'),
         ('fleece', 'fe', 'Fleece'), ('work-shirt', 'ws', 'Work shirt'),
         # The wardrobe dressed the legs for fire and traffic but not the
         # torso: there were flame-resistant trousers and no flame-
         # resistant shirt, and hi-vis only in short sleeve.
         ('fr-shirt', 'fs', 'Flame-resistant shirt',
          'Daily wear where a flash fire or an arc is possible, so the '
          'shirt does not melt into the burn.'),
         ('hi-vis-long-sleeve', 'hl', 'Hi-vis long sleeve',
          'Sleeved high-visibility, the piece a top-class ensemble needs '
          'and a vest alone cannot supply.'),
         ('sun-hoodie', 'sn', 'Sun hoodie',
          'A light hooded sun shirt: cover beats sunscreen across a '
          'ten-hour outdoor shift.'),
         ('smock', 'sm', 'Smock',
          'A lint-controlled layer for cleanroom and finishing work, '
          'where the hazard is what the member sheds.')])},
    {'id': 'topcolor', 'emoji': '\U0001f9f5', 'label': 'Top colour',
     'kind': 'color', 'options': coloropts(CLOTH)},
    {'id': 'vest', 'emoji': '\U0001f9ba', 'label': 'Vest', 'kind': 'style',
     'options': styleopts([
         ('none', '–', 'No vest',
          'Shop and indoor work, where nothing moving has to see you '
          'first.'),
         # High-visibility is a graded thing and the locker used to offer
         # two grades with no words on them. The classes are named here in
         # the order a member meets them: off-road, roadway, night.
         ('hi-vis-1', 'v1', 'Hi-vis, lowest class',
          'The least background material and tape, for off-road work '
          'away from moving traffic.'),
         ('hi-vis-2', 'v2', 'Hi-vis, roadway class',
          'The roadway vest: more background and tape, for traffic and '
          'for plant yards where equipment moves.'),
         ('hi-vis-3', 'v3', 'Hi-vis, highest class',
          'The largest vest in the rack, worn with sleeves or hi-vis '
          'trousers to make the highest-class ensemble for night work.'),
         ('surveyor', 'su', 'Surveyor vest',
          'Vertical tape and pockets deep enough for a field book and a '
          'prism.'),
         # Four harnesses, and the difference between them is which ring
         # the line clips to - the one fact a single 'harness' option
         # could not say. A member who clips fall arrest to a hip ring is
         # wearing the right harness the wrong way.
         ('harness', 'ha', 'Fall-arrest harness',
          'Full-body harness with the dorsal D-ring between the '
          'shoulder blades, which is the fall-arrest ring.'),
         ('harness-position', 'hp', 'Positioning harness',
          'Hip D-rings for leaning back on rebar or a pole; work '
          'positioning is not fall arrest and needs its own line.'),
         ('harness-suspension', 'hs', 'Retrieval harness',
          'Shoulder D-rings for a vertical lift, the harness an '
          'attendant hauls an entrant out of a hole with.'),
         ('harness-ladder', 'hl', 'Ladder-climb harness',
          'A sternal D-ring at the chest for a ladder rail or cable '
          'climb system.'),
         ('tool-vest', 'to', 'Tool vest',
          'Pockets instead of a belt, for ladder and lift work where a '
          'loaded belt drags on the hips.'),
         ('mesh', 'me', 'Mesh vest',
          'Open mesh for heat: the same visibility with air moving '
          'through it.'),
         ('insulated', 'in', 'Insulated vest',
          'A lined vest for cold work that keeps the arms free to '
          'move.'),
         ('fire-resist', 'fr', 'Flame-resistant vest',
          'For work near an ignition source, where an ordinary vest is '
          'itself the burn.'),
         ('crew-shell', 'cs', 'Crew shell',
          'A light shell in the hall’s colours: a garment for the '
          'hall and the ride in, with nothing protective in it.'),
         ('rain-vest', 'rv', 'Rain vest',
          'A coated shell over the torso for wet work with the arms '
          'left free.'),
         ('lead-apron', 'la', 'Lead apron',
          'For radiographic weld inspection, the shot everyone else '
          'clears the area for.'),
         ('life-vest', 'lv', 'Life vest',
          'Buoyancy for work over water: the dock edge, the barge and '
          'the bridge pier.'),
         ('back-support', 'bs', 'Back support',
          'A belt and brace: a reminder of lifting technique, and not a '
          'permit to lift more.'),
         ('parka-vest', 'pv', 'Insulated outer vest',
          'An outer layer for cold open ground with the sleeves of the '
          'work shirt underneath.'),
         ('cooling-vest', 'cv', 'Cooling vest',
          'A phase-change or evaporative vest for heat-illness weather '
          'worked in full protective equipment.')])},
    {'id': 'pants', 'emoji': '\U0001f456', 'label': 'Trousers', 'kind': 'style',
     'options': styleopts([
         ('jeans', 'je', 'Jeans'),
         ('duck-canvas', 'du', 'Duck canvas'), ('cargo', 'ca', 'Cargo'),
         ('carpenter', 'cp', 'Carpenter'),
         ('bib-overalls', 'bi', 'Bib overalls'), ('chinos', 'ch', 'Chinos'),
         ('shorts', 'sh', 'Shorts'),
         ('insulated', 'in', 'Insulated trousers',
          'Lined trousers for cold standing work, where movement will '
          'not keep a body warm.'),
         ('rain-pants', 'ra', 'Rain trousers',
          'Waterproof over-trousers for standing water and wet '
          'ground.'),
         ('hi-vis', 'hv', 'Hi-vis trousers',
          'High-visibility on the legs, which is where a member is seen '
          'from in a machine mirror.'),
         ('painter-white', 'pw', "Painter's whites",
          'The trade uniform of the painters, and a surface that shows '
          'the day’s work on it.'),
         ('fr-pants', 'fr', 'Flame-resistant trousers',
          'For arc and flash-fire work, so the trousers do not keep '
          'burning after the source is gone.'),
         ('khaki-work', 'kh', 'Khaki work'),
         ('black-denim', 'bd', 'Black denim'),
         ('grey-work', 'gw', 'Grey work'), ('olive-work', 'ol', 'Olive work'),
         # Legs take the hazards the vest rack never covers: the saw, the
         # kneeling trades, standing water, and the trousers that raise a
         # roadway vest to the night-work class.
         ('hi-vis-class-e', 'he', 'Hi-vis trousers, ensemble class',
          'Not a class on their own: worn with a roadway vest they make '
          'the highest-class ensemble.'),
         ('knee-pad-pants', 'kp', 'Knee-pad trousers',
          'Built-in knee pockets for the trades that work the whole day '
          'off their knees.'),
         ('saw-chaps', 'sc', 'Saw chaps',
          'Cut-resistant chaps for chainsaw work: the fibres pull out '
          'and jam the chain.'),
         ('hip-waders', 'wd', 'Hip waders',
          'For the wet trench, the treatment plant and shallow water '
          'work.')])},
    {'id': 'pantscolor', 'emoji': '\U0001f302', 'label': 'Trouser colour',
     'kind': 'color', 'options': coloropts(CLOTH)},
    {'id': 'shoes', 'emoji': '\U0001f97e', 'label': 'Footwear', 'kind': 'style',
     'options': styleopts([
         ('steel-toe-brown', 'sb', 'Steel toe, brown',
          'The ordinary work boot: a steel toe against impact and '
          'compression.'),
         ('steel-toe-black', 'sk', 'Steel toe, black',
          'The same toe in black, for the shops and plants whose dress '
          'code asks for it.'),
         ('steel-toe-tan', 'st', 'Steel toe, tan',
          'The first pair most apprentices buy, and the one they learn '
          'to re-lace.'),
         ('comp-toe-grey', 'cg', 'Composite toe',
          'A non-metallic toe: nothing to set off a detector, and '
          'nothing to carry the cold in.'),
         ('logger', 'lo', 'Logger boot',
          'A high shaft and an aggressive sole for broken ground and '
          'saw work.'),
         ('wellington', 'we', 'Wellington',
          'Pull-on and slip-resistant, for wet concrete and washdown '
          'floors.'),
         ('hiker', 'hi', 'Work hiker',
          'A light boot for survey lines and days measured in miles '
          'walked.'),
         ('rubber-yellow', 'ry', 'Chemical rubber boot',
          'Chemical-resistant rubber for the wash bay and the spill.'),
         ('rubber-green', 'rg', 'Water rubber boot',
          'Rubber for water work: wet trench, treatment plant and '
          'dock.'),
         ('sneaker-white', 'sw', 'White trainers',
          'Street shoes: no toe cap and no rating, so the hall and the '
          'classroom only.'),
         ('sneaker-black', 'sn', 'Black trainers',
          'The pair that passes a shop-floor dress code and no '
          'toe-protection rule anywhere.'),
         ('sneaker-red', 'sr', 'Red trainers',
          'Trainers in a crew colour, for the hall and the bus, with '
          'nothing protective in them.'),
         ('sneaker-blue', 'su', 'Blue trainers',
          'The pair kept in the locker for the walk home once the boots '
          'come off.'),
         ('high-top', 'ht', 'High tops',
          'Laced over the ankle for support, still with nothing on the '
          'toe.'),
         ('slip-on', 'so', 'Slip-on',
          'Quick off at the door of a clean space, and quick on '
          'again.'),
         ('lineman', 'li', 'Lineman boot',
          'A tall lace-up with a shank cut to take a climber and a pole '
          'gaff.'),
         # Boots are rated feature by feature, and the rack offered only
         # the toe. These are the other four ratings a member is sent to
         # buy by name.
         ('met-guard', 'mg', 'Metatarsal guard',
          'An external guard over the laces, for the drop and the pour '
          'that lands on the instep.'),
         ('eh-rated', 'eh', 'Electrical-hazard boot',
          'A secondary barrier against step potential; it is not an '
          'insulator and does not make a circuit safe to touch.'),
         ('puncture-sole', 'pr', 'Puncture-resistant sole',
          'A plate under the foot for demolition floors and nail-strewn '
          'decking.'),
         ('insulated-pac', 'ip', 'Insulated pac boot',
          'For standing on frozen ground through a whole winter '
          'shift.')])},
    {'id': 'tools', 'emoji': '\U0001f9f0', 'label': 'Tool belt', 'kind': 'style',
     'options': styleopts([
         ('none', '–', 'No belt',
          'The walk-through, the classroom, and the lift basket where a '
          'loaded belt snags on the rail.'),
         ('basic', 'ba', 'Basic belt',
          'Tape, knife and one pouch: what everybody carries in week '
          'one.'),
         ('framing', 'fr', 'Framing belt',
          'Hammer, speed square and nail bags for wood framing.'),
         ('electric', 'el', 'Electrician belt',
          'Side cutters, strippers and a voltage tester on the hip.'),
         ('plumber', 'pl', 'Plumber belt',
          'Wrenches, a tubing cutter and a striker for the torch.'),
         ('mason', 'ma', 'Mason belt',
          'Trowels, line blocks and a brick hammer, all of it wiped '
          'before the mud sets.'),
         ('welder', 'we', 'Welder belt',
          'Chipping hammer, wire brush, soapstone and tip cleaners.'),
         ('surveyor', 'su', 'Surveyor belt',
          'Plumb bob, field book, marking keel and the lath the '
          'stakes are cut from.'),
         ('drywall', 'dr', 'Drywall belt',
          'Taping knives in three widths, a rasp and a banjo full of '
          'tape.'),
         ('hvac', 'hv', 'HVAC belt',
          'Manifold gauges, a fin comb, nut drivers and a thermometer '
          'that reads fast.'),
         ('glazier', 'gl', 'Glazier belt',
          'Suction cups, glazing knives and setting blocks.'),
         ('roofer', 'ro', 'Roofer belt',
          'Hatchet, seam roller and a nail stripper, carried up a '
          'ladder one-handed.'),
         ('concrete', 'co', 'Concrete belt',
          'Float, edger and jointer within reach of the pour.'),
         ('rigger', 'ri', 'Rigger belt',
          'Shackles, a spud wrench and the tags that go on every '
          'sling.'),
         ('finisher', 'fi', 'Finisher belt',
          'Sanding pads, a corner tool and a spare gun tip.'),
         # Five halls on the roster worked a whole career without a belt
         # in this rack: the line trades, sheet metal, the painters, the
         # millwrights and the low-voltage crews.
         ('lineman', 'li', 'Lineman belt',
          'A body belt with climbers, a hand line and a loop for the '
          'hot stick.'),
         ('sheet-metal', 'sm', 'Sheet metal belt',
          'Snips in three cuts, a hand seamer and a scratch awl.'),
         ('painter', 'pa', 'Painter belt',
          'A five-in-one, a pot hook, brushes, and more rags than '
          'anyone else carries.'),
         ('millwright', 'mi', 'Millwright belt',
          'Dial indicator, feeler gauges and shim stock for '
          'alignment.'),
         ('low-voltage', 'lv', 'Low-voltage belt',
          'Punch-down tool, fish tape and a fibre cleaver for '
          'structured cabling.')])},
    {'id': 'outer', 'emoji': '\U0001f9e5', 'label': 'Outerwear', 'kind': 'style',
     'options': styleopts([
         ('none', '–', 'No outer layer',
          'Indoor work and the shoulder seasons, when the shirt is the '
          'whole answer.'),
         ('parka', 'pa', 'Parka',
          'A lined hooded coat for cold open ground, cut long enough '
          'to sit down in.'),
         ('rain-slicker', 'rs', 'Rain slicker',
          'A coated slicker for a long shift in standing rain.'),
         ('welding-jacket', 'wj', 'Welding jacket',
          'Leather across the shoulders and arms against spatter and '
          'arc.'),
         ('bomber', 'bo', 'Bomber jacket',
          'A short lined jacket cut to clear a tool belt.'),
         ('duster', 'du', 'Duster',
          'A long coat for wind on open sites, where the cold comes '
          'sideways.'),
         ('windbreaker', 'wb', 'Windbreaker',
          'An unlined shell for wind without the weight.'),
         ('lined-flannel', 'lf', 'Lined flannel',
          'The shirt-jacket that comes off by ten in the morning.'),
         ('hi-vis-parka', 'hp', 'Hi-vis parka',
          'A hooded coat that keeps the visibility class on through '
          'winter.'),
         ('softshell', 'ss', 'Softshell',
          'A stretch shell for cool dry work with a lot of reaching in '
          'it.'),
         ('chore-canvas', 'cc', 'Chore canvas',
          'Duck canvas that takes the abrasion of the yard.'),
         ('puffer', 'pu', 'Puffer',
          'Insulation for still, cold air where wind is not the '
          'problem.'),
         ('anorak', 'an', 'Anorak',
          'A pull-over hooded shell with the pocket on the chest.'),
         ('varsity', 'va', 'Hall jacket',
          'The crew jacket: the parade, the hall and the ride in.'),
         ('trench', 'tr', 'Trench coat',
          'A long coat for the walk between buildings and the wait at '
          'the gate.'),
         # Cold, heat, arc and splash are four different outer layers and
         # the rack had one of them. A coat is the wrong place to guess.
         ('arc-rated-coat', 'ar', 'Arc-rated coat',
          'Worn where an arc flash is possible; the whole layer system '
          'has to be arc-rated, not this coat alone.'),
         ('heated-liner', 'he', 'Heated liner',
          'A battery-heated layer for standing work in cold, where the '
          'body is not generating its own heat.'),
         ('chem-splash-coat', 'ch', 'Chemical splash coat',
          'A coated coat for washdown, spill response and anything that '
          'sprays back off the surface.'),
         ('cape-sleeves', 'cp', 'Cape sleeves',
          'Leather over the shoulders and arms for overhead welding, '
          'where the spatter comes straight down.'),
         ('insulated-coverall', 'ic', 'Insulated coverall',
          'One insulated piece over everything else for the coldest '
          'outdoor shifts.')])},
    {'id': 'extras', 'emoji': '\U0001f97d', 'label': 'Extras', 'kind': 'style',
     'options': styleopts([
         ('none', '–', 'Nothing extra',
          'The outfit as it stands, with no additional protective '
          'equipment on it.'),
         ('safety-glasses', 'sg', 'Safety glasses',
          'Impact-rated lenses, the one piece worn gate to gate on most '
          'sites.'),
         # A member who needs correction should not be choosing between
         # seeing the work and being protected from it, and street glasses
         # under a shield are neither.
         ('rx-safety-glasses', 'rx', 'Prescription safety glasses',
          'Impact-rated lenses ground to a prescription, so correction '
          'and protection are the same pair.'),
         ('sunglasses', 'su', 'Sunglasses',
          'Tint for glare on open ground and water; a tint is not an '
          'impact rating.'),
         ('ear-muffs', 'em', 'Ear muffs',
          'Over the ear, on and off quickly around intermittent '
          'noise.'),
         ('ear-plugs', 'pl', 'Ear plugs',
          'Plugs fit under a welding hood and a tight hard-hat band '
          'where muffs will not.'),
         # Five respiratory classes, low to high. The locker used to offer
         # two of them and call them both a mask.
         ('dust-mask', 'dm', 'Filtering facepiece',
          'The lowest class: a disposable facepiece for nuisance dust, '
          'and it still needs a seal.'),
         ('respirator', 're', 'Half-mask respirator',
          'Cartridges chosen for the hazard, on a seal that has to be '
          'fit-tested to the face wearing it.'),
         ('full-face-apr', 'ff', 'Full-face respirator',
          'A full facepiece: eye protection and a higher protection '
          'factor for abatement work.'),
         ('papr-hood', 'pp', 'Powered hood',
          'Powered air into a loose hood - the class that works over '
          'facial hair, where a tight-fitting mask cannot seal.'),
         ('supplied-air', 'sa', 'Supplied air',
          'Air from a line or a cylinder for confined space and '
          'blasting, where filtering the air is not enough.'),
         ('face-shield', 'fs', 'Face shield',
          'Against splash and flying chips, worn over safety glasses '
          'and never instead of them.'),
         ('welding-shield', 'ws', 'Welding shield',
          'A filter lens against arc flash, and cover against the burn '
          'on face and neck.'),
         ('knee-pads', 'kp', 'Knee pads',
          'Padding for the trades that spend the day kneeling on '
          'concrete.'),
         ('elbow-pads', 'ep', 'Elbow pads',
          'Padding for overhead and crawlspace work that rides on the '
          'elbows.'),
         ('tool-lanyard', 'tl', 'Tool lanyard',
          'A tether, so a dropped tool does not become a falling '
          'object.'),
         ('radio', 'ra', 'Hand radio',
          'The crew channel on the chest, where it can be heard over '
          'plant noise.'),
         ('headlamp', 'hl', 'Headlamp',
          'Hands-free light for the bore, the crawlspace and the night '
          'pour.'),
         ('id-badge', 'id', 'Site badge',
          'Which crew, which gate, and which orientation was sat '
          'through.'),
         ('gloves', 'gl', 'Gloves',
          'Chosen for the hazard: cut, chemical and rubber insulating '
          'gloves are not interchangeable.')])},
    {'id': 'costume', 'emoji': '\U0001f3ad', 'label': 'Costume', 'kind': 'style',
     'options': styleopts([
         ('none', '–', 'No costume'), ('krewe', 'kr', 'Krewe'),
         ('foundry', 'fo', 'Foundry suit'), ('diver', 'di', 'Dive dress'),
         ('vintage-33', 'vi', "The '33 crew"),
         ('storm-rider', 'st', 'Storm rider'),
         ('gold-journey', 'go', 'Golden journey'),
         ('hazmat', 'hz', 'Hazmat suit'), ('arc-guard', 'ar', 'Arc guard'),
         ('tunnel', 'tu', 'Tunnel crew'), ('parade', 'pd', 'Parade dress'),
         ('night-reflective', 'ni', 'Night reflective'),
         ('mascot', 'ms', 'Mascot suit'), ('frost', 'fr', 'Frost'),
         ('gala', 'ga', 'Gala'),
         # the crew mascots: original Academy animals, drawn from scratch
         ('ape-mascot', '\U0001f98d', 'Workshop ape'),
         ('pelican-mascot', '\U0001f426', 'Harbour pelican'),
         ('bear-mascot', '\U0001f43b', 'Yard bear'),
         ('gator-mascot', '\U0001f40a', 'Levee gator'),
         ('ox-mascot', '\U0001f402', 'Hauling ox')])},
]

# ------------------------------------------------------------- the crew ---
# All 111 halls, each carrying its three-letter code and district hue -
# the mark the page stamps on vest, shirt and headwear.
unions = json.load(open(ROOT / 'unions/registry/unions.json'))['unions']
halls_named = json.load(open(ROOT / 'pack/registry/halls.json'))['halls']
codes = make_codes([(h['slug'], h['name']) for h in halls_named])

CREW = {
    'id': 'crew', 'emoji': '\U0001fab5', 'label': 'Crew', 'kind': 'crew',
    'options': [
        {'id': u['slug'], 'glyph': codes[u['slug']],
         'hue': HUES[u['district']], 'district': u['district'],
         'name': u['name']}
        for u in unions
    ],
}
SECTIONS.append(CREW)

DEFAULTS = {
    'build': 'average-standard', 'skin': 'tone-08', 'hair': 'short',
    'haircolor': 'dark-brown', 'eyes': 'brown', 'facialhair': 'none',
    'headwear': 'hard-cap', 'headcolor': 'hi-vis-yellow', 'top': 'tee',
    'topcolor': 'hi-vis-orange', 'vest': 'hi-vis-2', 'pants': 'duck-canvas',
    'pantscolor': 'duck-brown', 'shoes': 'steel-toe-brown', 'tools': 'basic',
    'outer': 'none', 'extras': 'none', 'costume': 'none',
    'crew': 'ironworkers',
}

# ---------------------------------------------------------- characters ----
# One-tap personas: a full locker configuration with a name and a line of
# story. Applying one simply sets the sections - characters are made OF the
# locker, not an extra system, so every id is validated against it below.


def char(cid, emoji, name, blurb, **over):
    cfg = dict(DEFAULTS)
    cfg.update(over)
    return {'id': cid, 'emoji': emoji, 'name': name, 'blurb': blurb,
            'glyph': emoji, 'cfg': cfg}


CHARACTERS = [
    char('high-steel', '\U0001f3d7', 'The High-Steel Walker',
         'Connects iron forty storeys up and never hurries.',
         build='tall-slim', crew='ironworkers', headwear='climbing',
         vest='harness', top='long-sleeve', topcolor='slate',
         tools='rigger', extras='tool-lanyard', shoes='lineman'),
    char('wharf-boss', '⚓', 'The Wharf Operator',
         'Reads the river, the wind, and the manifest before coffee.',
         crew='port-crane', headwear='ball-cap', headcolor='navy',
         outer='rain-slicker', top='work-shirt', topcolor='steel-blue',
         shoes='rubber-yellow', extras='radio'),
    char('night-shift', '\U0001f319', 'Night Shift',
         'The city sleeps; the reflective crew does not.',
         costume='night-reflective', crew='laborers', headwear='hard-cap',
         headcolor='hi-vis-yellow', extras='headlamp',
         pantscolor='charcoal'),
    char('line-of-sight', '\U0001f4d0', 'The Line of Sight',
         'A surveyor’s patience: measure twice, argue never.',
         crew='surveyors', vest='surveyor', headwear='bucket',
         top='polo', topcolor='teal', tools='surveyor',
         extras='safety-glasses'),
    char('sparks', '⚡', 'Sparks',
         'Finds the fault before the fault finds anyone.',
         crew='electricians', headwear='welding-cap', headcolor='crimson',
         top='henley', topcolor='charcoal', tools='electric',
         extras='gloves', shoes='comp-toe-grey'),
    char('krewe-royalty', '\U0001f3ad', 'Krewe Royalty',
         'Second line in front, toolbox in back - laissez les bons temps.',
         costume='krewe', crew='laborers', hair='locs',
         facialhair='goatee'),
    char('foundry-heat', '\U0001f525', 'Foundry Heat',
         'Walks the pour line where the air itself glows.',
         costume='foundry', crew='welders', facialhair='full-beard'),
    char('deep-diver', '\U0001f93f', 'The Deep Diver',
         'Inspects the pilings nobody else will ever see.',
         costume='diver', crew='marine-terminal'),
    char('crew-of-33', '\U0001f570', "The '33 Crew",
         'Dressed like the bridge-raisers in the old photographs.',
         costume='vintage-33', crew='bricklayers', headwear='flat-cap',
         facialhair='mustache'),
    char('storm-rider', '\U0001f300', 'Storm Rider',
         'First truck in after the wind, last one out.',
         costume='storm-rider', crew='teamsters', extras='radio'),
    char('golden-journey', '\U0001f3c5', 'The Golden Journey',
         'Fifty years on the tools, and the hat to prove it.',
         costume='gold-journey', crew='operating-eng',
         facialhair='walrus', haircolor='silver', hair='short'),
    char('clean-sweep', '\U0001f9ea', 'Clean Sweep',
         'Hazmat-calm in places with warning signs on the doors.',
         costume='hazmat', crew='laborers'),
    char('arc-guard', '\U0001f6e1', 'Arc Guard',
         'Suited for the flash that must never happen.',
         costume='arc-guard', crew='welders', extras='face-shield'),
    char('tunnel-runner', '\U0001f687', 'The Tunnel Runner',
         'Knows the bore by sound alone, headlamp always on.',
         costume='tunnel', crew='miners', extras='headlamp'),
    char('parade-marshal', '\U0001f3ba', 'Parade Marshal',
         'Leads the apprentice class down Canal Street once a year.',
         costume='parade', crew='carpenters', headwear='none'),
    char('day-one', '\U0001f331', 'Day One',
         'New boots, clean gloves, and every question worth asking.',
         crew='scaffold', extras='gloves', shoes='steel-toe-tan',
         top='tee', topcolor='white'),
    char('wrench', '\U0001f98d', 'Wrench',
         'The workshop ape - an original Academy mascot who tightens '
         'everything twice.',
         costume='ape-mascot', crew='millwrights', tools='basic',
         vest='hi-vis-2'),
    # Five personas that exist to put the new kit on a body: the sections
    # each hold twenty options, and an option nobody is ever seen wearing
    # is an option nobody finds. Each of these wears one family.
    char('the-attendant', '\U0001f573', 'The Attendant',
         'Stands at the hole the whole shift and never once goes in.',
         crew='confined-space', vest='harness-suspension',
         extras='supplied-air', headwear='hard-cap', headcolor='white',
         top='long-sleeve', topcolor='slate', tools='rigger'),
    char('dry-cut', '\U0001f32b', 'The Dry Cut',
         'Argues for water on the blade before anyone starts cutting.',
         crew='masonry-restore', extras='respirator', top='coveralls',
         topcolor='stone', headwear='ball-cap-back', vest='hi-vis-1',
         tools='mason'),
    char('heat-index', '\U0001f321', 'The Heat Index',
         'Watches the index, calls the shade break, takes it first.',
         crew='airfield', headwear='sun-shade', headcolor='white',
         top='sun-hoodie', topcolor='sand', vest='cooling-vest',
         pants='hi-vis-class-e', pantscolor='hi-vis-yellow',
         shoes='comp-toe-grey'),
    char('cold-pour', '\U0001f976', 'The Cold Pour',
         'Pours at twenty degrees and blankets it before the light goes.',
         crew='cement-masons', headwear='hard-cap-liner',
         outer='insulated-coverall', shoes='insulated-pac',
         tools='concrete', pantscolor='charcoal'),
    char('hot-stick', '\U0001fa9d', 'The Hot Stick',
         'Works it live from the bucket, and checks the cover-up twice.',
         crew='transmission', tools='lineman', shoes='eh-rated',
         vest='harness-position', top='fr-shirt', topcolor='navy',
         pants='fr-pants', extras='gloves', headwear='climbing'),
]

# The gestures the wheel plays. A move is a procedural animation the page
# implements by name - an emote with a move the page does not know plays
# nothing at all, so the moves are held to a list here and named in the
# report when one is added.
EMOTES = [
    {'id': 'wave', 'emoji': '\U0001f44b', 'label': 'Wave', 'move': 'arm-wave',
     'note': 'A hand up across the yard.'},
    {'id': 'thumbs', 'emoji': '\U0001f44d', 'label': 'Thumbs up',
     'move': 'arm-up', 'note': 'Understood - the answer that carries over '
     'plant noise.'},
    {'id': 'point', 'emoji': '\U0001f449', 'label': 'Point',
     'move': 'arm-point', 'note': 'Points at the thing being talked about.'},
    {'id': 'tip', 'emoji': '\U0001f477', 'label': 'Hat tip', 'move': 'hat-tip',
     'note': 'Hat off and back on, the oldest greeting on a site.'},
    {'id': 'clap', 'emoji': '\U0001f44f', 'label': 'Clap', 'move': 'clap',
     'note': 'For the class that finished.'},
    {'id': 'flex', 'emoji': '\U0001f4aa', 'label': 'Flex', 'move': 'flex',
     'note': 'The end of a hard lift.'},
    {'id': 'spin', 'emoji': '\U0001f300', 'label': 'Spin', 'move': 'spin',
     'note': 'A turn on the spot, to be seen from every side.'},
    {'id': 'check', 'emoji': '✅', 'label': 'Safety check', 'move': 'jump',
     'note': 'A hop, for a walk-around that came back clean.'},
    # The yard's own vocabulary. Riggers and signalpersons have a hand
    # language and the locker had eight gestures, none of them from it.
    # These are shapes, played by an avatar on a pedestal; the honesty
    # line below says what they are not.
    {'id': 'hoist', 'emoji': '☝', 'label': 'Hoist', 'move': 'arm-hoist',
     'note': 'The raise shape: forearm up, finger turning.'},
    {'id': 'lower', 'emoji': '\U0001f447', 'label': 'Lower',
     'move': 'arm-lower', 'note': 'The lower shape: arm out and down, '
     'finger turning.'},
    {'id': 'stop', 'emoji': '⛔', 'label': 'Stop', 'move': 'arm-stop',
     'note': 'The stop shape: arm out, palm down, swept across.'},
    {'id': 'tie-off', 'emoji': '\U0001f517', 'label': 'Tie off',
     'move': 'clip-on', 'note': 'Clipping the lanyard on before stepping '
     'out.'},
]

GESTURES = ('the emotes are gestures an avatar plays on a pedestal. The '
            'hoist, lower and stop shapes borrow the yard’s own hand '
            'vocabulary because it is the vocabulary members learn, but '
            'playing one here is not a signalperson qualification and '
            'confers nothing: on a real lift only the qualified '
            'signalperson signals, and anyone may call a stop.')

PROVENANCE = ('AUTHORED - every part, colour, name and note in this locker '
              'is typed from general public knowledge of the trades and is '
              'not cross-checked against any standard this build can read. '
              'A note says what a piece of kit is FOR; it is not the '
              'standard, not a specification, and not a substitute for the '
              'qualified person on site. Nothing here is RECORDED, and '
              'nothing here is graded.')

# ------------------------------------------------------------ the rules ---
# Which options have to name the hazard or the trade they answer. The six
# kit sections carry a note on EVERY option: everything in them is
# protective equipment or a trade's own belt, and an unexplained piece of
# safety kit in a wheel of two-letter glyphs is a guess. The wardrobe
# sections carry notes only on the pieces that are equipment rather than
# clothes - a tee needs no hazard note and would only dilute the ones that
# do. Every section is listed, including the ones that need nothing, so a
# section added later fails this build instead of quietly escaping the
# rule.
ALL = 'ALL'
NOTED = {
    'build': set(), 'skin': set(), 'hair': set(), 'haircolor': set(),
    'eyes': set(), 'facialhair': set(), 'headcolor': set(),
    'topcolor': set(), 'pantscolor': set(), 'costume': set(),
    'crew': set(),
    'headwear': ALL, 'vest': ALL, 'shoes': ALL, 'tools': ALL,
    'outer': ALL, 'extras': ALL,
    'top': {'coveralls', 'hi-vis-tee', 'thermal', 'rain-shell', 'fr-shirt',
            'hi-vis-long-sleeve', 'sun-hoodie', 'smock'},
    'pants': {'insulated', 'rain-pants', 'hi-vis', 'painter-white',
              'fr-pants', 'hi-vis-class-e', 'knee-pad-pants', 'saw-chaps',
              'hip-waders'},
}

# The body region each extra occupies. It is here because 'extras' is one
# slot holding eye, ear, airway, hand and body kit at once: naming the
# region is what lets the page draw an unfamiliar extra at all, and what
# would let it one day hold one pick per region instead of one in total.
SLOT = {
    'none': 'none', 'safety-glasses': 'eyes', 'rx-safety-glasses': 'eyes',
    'sunglasses': 'eyes', 'ear-muffs': 'ears', 'ear-plugs': 'ears',
    'dust-mask': 'airway', 'respirator': 'airway', 'full-face-apr': 'airway',
    'papr-hood': 'airway', 'supplied-air': 'airway', 'face-shield': 'face',
    'welding-shield': 'face', 'knee-pads': 'legs', 'elbow-pads': 'arms',
    'tool-lanyard': 'torso', 'radio': 'torso', 'headlamp': 'head',
    'id-badge': 'torso', 'gloves': 'hands',
}
for _o in next(s for s in SECTIONS if s['id'] == 'extras')['options']:
    # Indexed, not defaulted: an extra with no declared region is a piece
    # of kit the page has nowhere to hang, so it stops the build.
    _o['slot'] = SLOT[_o['id']]
assert set(SLOT) == {o['id'] for o in
                     next(s for s in SECTIONS if s['id'] == 'extras')
                     ['options']}, 'a slot is declared for a missing extra'

_seen_notes = set()
for s in SECTIONS:
    ids = [o['id'] for o in s['options']]
    assert len(ids) == len(set(ids)), s['id']
    if s['kind'] == 'crew':
        assert len(ids) == 111
    else:
        assert 15 <= len(ids) <= 20, f"{s['id']}: {len(ids)} options"
    assert DEFAULTS[s['id']] in ids, s['id']
    # Every option says its own name, and no two say the same one: the
    # wheel draws a glyph and nothing else, so two options sharing a name
    # are two wedges a learner cannot tell apart.
    names = [o['name'] for o in s['options']]
    assert all(n and len(n) > 1 for n in names), f"{s['id']}: an unnamed option"
    assert len(names) == len(set(names)), f"{s['id']}: two options, one name"
    # The same for what the wedge actually draws - a repeated glyph or a
    # repeated swatch is a duplicate wearing a different id.
    if s['kind'] == 'color':
        vals = [o['value'] for o in s['options']]
        assert len(vals) == len(set(vals)), f"{s['id']}: two swatches, one colour"
    else:
        glyphs = [o['glyph'] for o in s['options']]
        assert len(glyphs) == len(set(glyphs)), f"{s['id']}: two wedges, one glyph"
    rule = NOTED[s['id']]
    want = set(ids) if rule == ALL else rule
    have = {o['id'] for o in s['options'] if 'note' in o}
    assert have == want, \
        f"{s['id']}: notes on {sorted(have - want)}, missing {sorted(want - have)}"
    for o in s['options']:
        n = o.get('note')
        if n is None:
            continue
        assert len(n) >= 40 and n.endswith('.'), f"{s['id']}/{o['id']}: {n}"
        assert n not in _seen_notes, f"{s['id']}/{o['id']}: a note used twice"
        _seen_notes.add(n)

# ------------------------------------------------- the families of kit ----
# Kit that comes in grades is only useful if the whole grade is on the
# rack: a locker that offers two of three visibility classes, one of four
# harnesses or two of five respiratory classes teaches the gap. These
# assertions hold the families whole.
_opt = {s['id']: {o['id']: o for o in s['options']} for s in SECTIONS}

_hv = {i for i in _opt['vest'] if i.startswith('hi-vis-')}
assert _hv == {'hi-vis-1', 'hi-vis-2', 'hi-vis-3'}, _hv
# The class a garment carries is not the class an ensemble carries, and
# that is the fact members get wrong: the highest class needs sleeves or
# hi-vis trousers, both of which have to exist to be worn.
assert 'hi-vis-long-sleeve' in _opt['top'] and 'hi-vis-class-e' in _opt['pants']

_harness = {i for i in _opt['vest'] if i.startswith('harness')}
assert len(_harness) == 4, _harness
for _h in _harness:
    assert 'D-ring' in _opt['vest'][_h]['note'], \
        f'{_h}: a harness note that does not say which ring the line clips to'

_airway = {i for i, o in _opt['extras'].items() if o['slot'] == 'airway'}
assert len(_airway) == 5, _airway
# The loose-fitting powered hood is the one respiratory class that works
# on a face with hair on it, and this locker holds nineteen ways to wear
# facial hair - so the class and the reason for it are both asserted.
assert 'facial hair' in _opt['extras']['papr-hood']['note']
assert len(_opt['facialhair']) >= 15
# Both hearing-protection fits, because the choice between them is a fit
# question (under a hood, under a band) and not a preference.
assert {'ear-muffs', 'ear-plugs'} <= set(_opt['extras'])
# Heat and cold are dressed on every layer the page draws, head to foot.
assert {'vented-cap', 'sun-shade'} <= set(_opt['headwear'])
assert {'hard-cap-liner'} <= set(_opt['headwear'])
assert 'cooling-vest' in _opt['vest'] and 'sun-hoodie' in _opt['top']
assert {'heated-liner', 'insulated-coverall'} <= set(_opt['outer'])
assert 'insulated-pac' in _opt['shoes']
# The one accessibility fit in the rack that is not a size: correction and
# impact protection in the same pair, so neither is the thing left off.
assert 'rx-safety-glasses' in _opt['extras']

# ---------------------------------------------------------- the emotes ----
_moves = [e['move'] for e in EMOTES]
assert len(_moves) == len(set(_moves)), 'two emotes, one move'
assert len({e['id'] for e in EMOTES}) == len(EMOTES)
for e in EMOTES:
    assert e['emoji'] and e['label'] and e['note'].endswith('.'), e['id']
assert len({e['emoji'] for e in EMOTES}) == len(EMOTES), 'two emotes, one emoji'

# -------------------------------------------------------- TradeApes -------
# SmartCiti.X TradeApes: an ORIGINAL Academy collection - one ape per hall,
# 111 in all, every one generated deterministically from the roster itself
# (fur, build, eyes, vest and kit walk the locker by hall index; the chest
# and vest carry the hall's own three-letter mark). Free and cosmetic only,
# like everything in the locker. NOT tokens: nothing here is an NFT, nothing
# is for sale, and no blockchain is involved. And original: drawn from
# scratch in this page's primitive style, imitating no third-party ape
# artwork, collection or brand.
_opt_ids = {s['id']: [o['id'] for o in s['options']] for s in SECTIONS}


def _walk(section, i, skip=0):
    """Step through a whole section by hall index. The section's length is
    read, never typed: these moduli used to be literals (16, 15, 14...)
    and a section that grew past its literal simply stopped lending its
    last options to any ape. `skip` drops the leading option where that
    option is 'none' and an ape with no tool belt is not the point."""
    opts = _opt_ids[section]
    return opts[skip + i % (len(opts) - skip)]


TRADEAPES = []
for u in unions:
    i = u['index']
    _cfg = dict(DEFAULTS)
    _cfg.update({
        'costume': 'ape-mascot', 'crew': u['slug'], 'outer': 'none',
        'build': _walk('build', i),
        'eyes': _walk('eyes', i),
        'headcolor': _walk('headcolor', i),
        'topcolor': _walk('topcolor', i),                # the fur
        'pantscolor': _walk('pantscolor', i),
        'shoes': _walk('shoes', i),
        'vest': ['hi-vis-2', 'hi-vis-3', 'surveyor', 'tool-vest'][i % 4],
        'tools': _walk('tools', i, skip=1),
        'extras': _walk('extras', i),
    })
    TRADEAPES.append({
        'hall': u['slug'], 'code': codes[u['slug']],
        'name': f'TradeApe {codes[u["slug"]]}',
        'district': u['district'], 'hue': HUES[u['district']],
        'cfg': _cfg,
    })

# Every character is made of the locker: each cfg key is a section and
# each value one of its options - an invented id fails the build.
_valid = {s['id']: {o['id'] for o in s['options']} for s in SECTIONS}
assert len({c['id'] for c in CHARACTERS}) == len(CHARACTERS)
for c in CHARACTERS:
    assert set(c['cfg']) == set(_valid), c['id']
    for k, v in c['cfg'].items():
        assert v in _valid[k], f"{c['id']}: {k}={v}"
assert len(TRADEAPES) == 111
for t in TRADEAPES:
    assert set(t['cfg']) == set(_valid), t['hall']
    for k, v in t['cfg'].items():
        assert v in _valid[k], f"{t['hall']}: {k}={v}"

GUARANTEE = ('cosmetic only: every option is free and unlocked, and no '
             'avatar choice affects scoring, access, progression or '
             'anything the rubrics measure')

# the network dashboard names its own contributing pack for every other
# platform-wide fact but used to say nothing about the locker or the
# TradeApes - the drift guard for that gap
BOOTSTRAP = '--bootstrap' in __import__('sys').argv
if not BOOTSTRAP:
    dash = (ROOT / 'web/trade_craft_dashboard.html').read_text()
    assert f'{len(SECTIONS)} / {len(TRADEAPES)}' in dash, \
        'the dashboard does not render the avatar-section / TradeApes count'
    assert GUARANTEE in dash, \
        'the dashboard does not carry the cosmetic-only guarantee'

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

doc = {
    'pack': 'smartcitix-trade-craft-academy-avatars',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'guarantee': GUARANTEE,
    'provenance': PROVENANCE,
    'gestures': GESTURES,
    'marks': 'crew marks are the Academy’s own insignia - the roster’s '
             'three-letter hall codes on a shield in the district hue, the '
             'same codes the campus map prints. They are not, and do not '
             'imitate, any real union’s logo or emblem; no local is named '
             'and none is drawn. The animal mascots are original Academy '
             'characters drawn from scratch in this page’s own primitive '
             'style; they are not, and do not imitate, any third-party '
             'character, collection or brand - no Bored Ape or other NFT '
             'artwork is reproduced or derived from.',
    'tradeapes': {
        'collection': 'SmartCiti.X TradeApes',
        # Ape anatomy reference, MEASURED from a user-supplied low-poly ape
        # GLB (Khronos glTF Blender I/O v1.6.16). Measurements only: the
        # mesh itself is NOT shipped or copied - its license is unknown and
        # its filename references a third-party collection, so the numbers
        # below are the whole of what was taken. Generic ape anatomy
        # (span~height, hunched depth, dark fur over a tan face, layered
        # eyes) is nobody's property; the TradeApes remain original
        # primitives built to these proportions.
        'ape_reference': {
            'height': 23.64, 'span': 24.24, 'depth': 13.73,
            'span_to_height': 1.03, 'depth_to_height': 0.58,
            'material_roles': ['fur', 'face', 'eyelids', 'iris', 'sclera',
                               'pupil', 'black'],
            'provenance': 'measured from a user-supplied GLB; measurements '
                          'only - the mesh is not shipped, no geometry or '
                          'texture is copied, and no third-party artwork '
                          'is derived from',
        },
        'honesty': 'an original Academy collection, generated from the '
                   'roster itself - one ape per hall, free and cosmetic '
                   'only. Not tokens: nothing is an NFT, nothing is for '
                   'sale, and no blockchain is involved. Original art: '
                   'no third-party ape artwork, collection or brand is '
                   'imitated.',
        'apes': TRADEAPES,
    },
    'sections': SECTIONS,
    'defaults': DEFAULTS,
    'characters': CHARACTERS,
    'emotes': EMOTES,
}

# The four provenance words carry weight across this bundle and one of
# them belongs to another pack: orbis/ owns AI-SYNTHESIZED, and no part of
# an avatar is that. The parts are AUTHORED, and the serialised registry
# is checked for the word rather than trusted not to contain it.
blob = json.dumps(doc, ensure_ascii=False, indent=1) + '\n'
assert 'synthes' not in blob.lower(), \
    'the avatar registry claims a synthesis provenance that orbis/ owns'
assert PROVENANCE.startswith('AUTHORED'), PROVENANCE

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'avatars.json').write_text(blob)
n_std = sum(len(s['options']) for s in SECTIONS if s['kind'] != 'crew')
n_noted = sum(1 for s in SECTIONS for o in s['options'] if 'note' in o)
print(f"avatar pack: {len(SECTIONS)} locker sections "
      f"({n_std} options + 111 crews, {n_noted} of them noting the hazard "
      f"or trade they answer), {len(CHARACTERS)} characters, "
      f"{len(EMOTES)} emotes (source stamp {stamp})")
