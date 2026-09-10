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
    'crew': 'ironworkers',
}

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
             'and none is drawn.',
    'sections': SECTIONS,
    'defaults': DEFAULTS,
    'emotes': EMOTES,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'avatars.json').write_text(
    json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
n_std = sum(len(s['options']) for s in SECTIONS if s['kind'] != 'crew')
print(f"avatar pack: {len(SECTIONS)} locker sections "
      f"({n_std} options + 111 crews), {len(EMOTES)} emotes "
      f"(source stamp {stamp})")
