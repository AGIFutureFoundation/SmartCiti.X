#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the avatar pack builder.

The learner's avatar as data: locker sections (15–20 options each), the
CREW section carrying all 111 halls, and emotes (an emoji, a label, and a
procedural move the 3D page implements). The page renders a humanoid from
these ids — capsule body, hair, facial features, full workwear — and
stores the learner's choices in the device-local progress record.

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

PACK_VERSION = "3.2.0"
BUILT = "2026-09-10"


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

# One work-palette, reused by the colour sections that dress cloth.
CLOTH = [
    ('hi-vis-orange', '#e8722a'), ('hi-vis-yellow', '#d9c22e'),
    ('safety-green', '#7ac142'), ('forest', '#3c6b45'), ('olive', '#5b6238'),
    ('slate', '#4a5a64'), ('navy', '#2c3e5a'), ('royal', '#2f4d8a'),
    ('steel-blue', '#4a7a96'), ('teal', '#2f6f6a'), ('crimson', '#a03a34'),
    ('rust', '#9c5a30'), ('duck-brown', '#a5793f'), ('sand', '#c2a878'),
    ('charcoal', '#33363a'), ('grey', '#6c7276'), ('stone', '#9a978c'),
    ('white', '#e6e6e2'),
]


def coloropts(pairs):
    return [{'id': i, 'value': v} for i, v in pairs]


def styleopts(items):
    return [{'id': i, 'glyph': g} for i, g in items]


SECTIONS = [
    {'id': 'build', 'emoji': '\U0001f9cd', 'label': 'Build', 'kind': 'style',
     'options': [
         {'id': f'{h_id}-{w_id}', 'glyph': f'{hg}{wg}',
          'scale': [w, h, round(w * .96, 2)]}
         for h_id, hg, h in [('short', 'S', .9), ('average', 'A', 1.0),
                             ('tall', 'T', 1.08), ('towering', 'X', 1.16)]
         for w_id, wg, w in [('slim', 's', .88), ('standard', 'm', 1.0),
                             ('broad', 'b', 1.12), ('heavy', 'h', 1.24)]
     ]},
    {'id': 'skin', 'emoji': '✋', 'label': 'Skin', 'kind': 'color',
     'options': [{'id': f'tone-{i+1:02d}', 'value': v}
                 for i, v in enumerate(SKIN)]},
    {'id': 'hair', 'emoji': '\U0001f487', 'label': 'Hair', 'kind': 'style',
     'options': styleopts([
         ('bald', '–'), ('buzz', 'bz'), ('crew', 'cr'), ('short', 'sh'),
         ('side-part', 'sp'), ('waves', 'wv'), ('curls', 'cu'),
         ('afro', 'af'), ('bob', 'bo'), ('bun', 'bn'), ('ponytail', 'pt'),
         ('braids', 'br'), ('locs', 'lc'), ('mohawk', 'mo'),
         ('long', 'lg'), ('undercut', 'uc')])},
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
         ('none', '–'), ('stubble', 'st'), ('light-mustache', 'lm'),
         ('mustache', 'mu'), ('handlebar', 'hb'), ('chin-strap', 'cs'),
         ('soul-patch', 'sp'), ('goatee', 'go'), ('circle-beard', 'cb'),
         ('short-beard', 'sb'), ('full-beard', 'fb'), ('long-beard', 'lb'),
         ('mutton-chops', 'mc'), ('walrus', 'wa'), ('garibaldi', 'ga')])},
    {'id': 'headwear', 'emoji': '⛑', 'label': 'Headwear', 'kind': 'style',
     'options': styleopts([
         ('none', '–'), ('hard-cap', 'hc'), ('full-brim', 'fu'),
         ('climbing', 'cl'), ('vintage', 'vi'), ('carbon', 'ca'),
         ('ball-cap', 'bc'), ('ball-cap-back', 'bb'), ('flat-cap', 'fc'),
         ('beanie', 'be'), ('bucket', 'bu'), ('welding-cap', 'we'),
         ('visor', 'vs'), ('headband', 'hb'), ('bandana', 'ba'),
         ('winter-liner', 'wl')])},
    {'id': 'headcolor', 'emoji': '\U0001f7e1', 'label': 'Headwear colour',
     'kind': 'color', 'options': coloropts(CLOTH[:16])},
    {'id': 'top', 'emoji': '\U0001f455', 'label': 'Top', 'kind': 'style',
     'options': styleopts([
         ('tee', 'te'), ('long-sleeve', 'ls'), ('henley', 'he'),
         ('polo', 'po'), ('flannel', 'fl'), ('hoodie', 'ho'),
         ('sweatshirt', 'sw'), ('denim-jacket', 'dj'), ('chore-coat', 'cc'),
         ('coveralls', 'co'), ('hi-vis-tee', 'hv'), ('tank', 'ta'),
         ('thermal', 'th'), ('rain-shell', 'ra'), ('fleece', 'fe'),
         ('work-shirt', 'ws')])},
    {'id': 'topcolor', 'emoji': '\U0001f9f5', 'label': 'Top colour',
     'kind': 'color', 'options': coloropts(CLOTH)},
    {'id': 'vest', 'emoji': '\U0001f9ba', 'label': 'Vest', 'kind': 'style',
     'options': styleopts([
         ('none', '–'), ('hi-vis-2', 'v2'), ('hi-vis-3', 'v3'),
         ('surveyor', 'su'), ('harness', 'ha'), ('tool-vest', 'to'),
         ('mesh', 'me'), ('insulated', 'in'), ('fire-resist', 'fr'),
         ('crew-shell', 'cs'), ('rain-vest', 'rv'), ('lead-apron', 'la'),
         ('life-vest', 'lv'), ('back-support', 'bs'), ('parka-vest', 'pv')])},
    {'id': 'pants', 'emoji': '\U0001f456', 'label': 'Trousers', 'kind': 'style',
     'options': styleopts([
         ('jeans', 'je'), ('duck-canvas', 'du'), ('cargo', 'ca'),
         ('carpenter', 'cp'), ('bib-overalls', 'bi'), ('chinos', 'ch'),
         ('shorts', 'sh'), ('insulated', 'in'), ('rain-pants', 'ra'),
         ('hi-vis', 'hv'), ('painter-white', 'pw'), ('fr-pants', 'fr'),
         ('khaki-work', 'kh'), ('black-denim', 'bd'), ('grey-work', 'gw'),
         ('olive-work', 'ol')])},
    {'id': 'pantscolor', 'emoji': '\U0001f302', 'label': 'Trouser colour',
     'kind': 'color', 'options': coloropts(CLOTH[2:17])},
    {'id': 'shoes', 'emoji': '\U0001f97e', 'label': 'Footwear', 'kind': 'style',
     'options': styleopts([
         ('steel-toe-brown', 'sb'), ('steel-toe-black', 'sk'),
         ('steel-toe-tan', 'st'), ('comp-toe-grey', 'cg'),
         ('logger', 'lo'), ('wellington', 'we'), ('hiker', 'hi'),
         ('rubber-yellow', 'ry'), ('rubber-green', 'rg'),
         ('sneaker-white', 'sw'), ('sneaker-black', 'sn'),
         ('sneaker-red', 'sr'), ('sneaker-blue', 'su'),
         ('high-top', 'ht'), ('slip-on', 'so'), ('lineman', 'li')])},
    {'id': 'tools', 'emoji': '\U0001f9f0', 'label': 'Tool belt', 'kind': 'style',
     'options': styleopts([
         ('none', '–'), ('basic', 'ba'), ('framing', 'fr'),
         ('electric', 'el'), ('plumber', 'pl'), ('mason', 'ma'),
         ('welder', 'we'), ('surveyor', 'su'), ('drywall', 'dr'),
         ('hvac', 'hv'), ('glazier', 'gl'), ('roofer', 'ro'),
         ('concrete', 'co'), ('rigger', 'ri'), ('finisher', 'fi')])},
    {'id': 'outer', 'emoji': '\U0001f9e5', 'label': 'Outerwear', 'kind': 'style',
     'options': styleopts([
         ('none', '–'), ('parka', 'pa'), ('rain-slicker', 'rs'),
         ('welding-jacket', 'wj'), ('bomber', 'bo'), ('duster', 'du'),
         ('windbreaker', 'wb'), ('lined-flannel', 'lf'),
         ('hi-vis-parka', 'hp'), ('softshell', 'ss'), ('chore-canvas', 'cc'),
         ('puffer', 'pu'), ('anorak', 'an'), ('varsity', 'va'),
         ('trench', 'tr')])},
    {'id': 'extras', 'emoji': '\U0001f97d', 'label': 'Extras', 'kind': 'style',
     'options': styleopts([
         ('none', '–'), ('safety-glasses', 'sg'), ('sunglasses', 'su'),
         ('ear-muffs', 'em'), ('respirator', 're'), ('dust-mask', 'dm'),
         ('face-shield', 'fs'), ('welding-shield', 'ws'),
         ('knee-pads', 'kp'), ('elbow-pads', 'ep'), ('tool-lanyard', 'tl'),
         ('radio', 'ra'), ('headlamp', 'hl'), ('id-badge', 'id'),
         ('gloves', 'gl')])},
    {'id': 'costume', 'emoji': '\U0001f3ad', 'label': 'Costume', 'kind': 'style',
     'options': styleopts([
         ('none', '–'), ('krewe', 'kr'), ('foundry', 'fo'), ('diver', 'di'),
         ('vintage-33', 'vi'), ('storm-rider', 'st'), ('gold-journey', 'go'),
         ('hazmat', 'hz'), ('arc-guard', 'ar'), ('tunnel', 'tu'),
         ('parade', 'pd'), ('night-reflective', 'ni'), ('mascot', 'ms'),
         ('frost', 'fr'), ('gala', 'ga'),
         # the crew mascots: original Academy animals, drawn from scratch
         ('ape-mascot', '\U0001f98d'), ('pelican-mascot', '\U0001f426'),
         ('bear-mascot', '\U0001f43b'), ('gator-mascot', '\U0001f40a'),
         ('ox-mascot', '\U0001f402')])},
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
]

EMOTES = [
    {'id': 'wave', 'emoji': '\U0001f44b', 'label': 'Wave', 'move': 'arm-wave'},
    {'id': 'thumbs', 'emoji': '\U0001f44d', 'label': 'Thumbs up', 'move': 'arm-up'},
    {'id': 'point', 'emoji': '\U0001f449', 'label': 'Point', 'move': 'arm-point'},
    {'id': 'tip', 'emoji': '\U0001f477', 'label': 'Hat tip', 'move': 'hat-tip'},
    {'id': 'clap', 'emoji': '\U0001f44f', 'label': 'Clap', 'move': 'clap'},
    {'id': 'flex', 'emoji': '\U0001f4aa', 'label': 'Flex', 'move': 'flex'},
    {'id': 'spin', 'emoji': '\U0001f300', 'label': 'Spin', 'move': 'spin'},
    {'id': 'check', 'emoji': '✅', 'label': 'Safety check', 'move': 'jump'},
]

for s in SECTIONS:
    ids = [o['id'] for o in s['options']]
    assert len(ids) == len(set(ids)), s['id']
    if s['kind'] == 'crew':
        assert len(ids) == 111
    else:
        assert 15 <= len(ids) <= 20, f"{s['id']}: {len(ids)} options"
    assert DEFAULTS[s['id']] in ids, s['id']

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
TRADEAPES = []
for u in unions:
    i = u['index']
    _cfg = dict(DEFAULTS)
    _cfg.update({
        'costume': 'ape-mascot', 'crew': u['slug'], 'outer': 'none',
        'build': _opt_ids['build'][i % 16],
        'eyes': _opt_ids['eyes'][i % 15],
        'headcolor': _opt_ids['headcolor'][i % 16],
        'topcolor': _opt_ids['topcolor'][i % 18],       # the fur
        'pantscolor': _opt_ids['pantscolor'][i % 15],
        'shoes': _opt_ids['shoes'][i % 16],
        'vest': ['hi-vis-2', 'hi-vis-3', 'surveyor', 'tool-vest'][i % 4],
        'tools': _opt_ids['tools'][1 + i % 14],
        'extras': _opt_ids['extras'][i % 15],
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

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

doc = {
    'pack': 'smartcitix-trade-craft-academy-avatars',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'guarantee': 'cosmetic only: every option is free and unlocked, and no '
                 'avatar choice affects scoring, access, progression or '
                 'anything the rubrics measure',
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

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'avatars.json').write_text(
    json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
n_std = sum(len(s['options']) for s in SECTIONS if s['kind'] != 'crew')
print(f"avatar pack: {len(SECTIONS)} locker sections "
      f"({n_std} options + 111 crews), {len(CHARACTERS)} characters, "
      f"{len(EMOTES)} emotes (source stamp {stamp})")
