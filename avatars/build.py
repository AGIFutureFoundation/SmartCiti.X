#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the avatar pack builder.

The learner's avatar as data: locker sections (each with multiple
options), and emotes (an emoji, a label, and a procedural move the 3D
page implements). The page renders the avatar from these ids and stores
the learner's choices in the device-local progress record.

THE GUARANTEE, stated and tested: avatars are COSMETIC ONLY. No option
is locked, none is paid, and none affects scoring, access, progression
or anything the rubrics measure. A locker that could tilt a score is a
scoring bug; avatars/test.mjs asserts the guarantee and the page's
grading never reads the avatar record.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent

PACK_VERSION = "3.2.0"
BUILT = "2026-09-10"

# Locker sections. `kind` tells the page how to render the wheel wedge:
# 'color' wedges fill with the value, 'style' wedges show the short glyph.
SECTIONS = [
    {'id': 'build', 'emoji': '\U0001f9cd', 'label': 'Build', 'kind': 'style',
     'options': [
         {'id': 'compact', 'glyph': 'S', 'scale': [0.92, 0.92, 0.92]},
         {'id': 'standard', 'glyph': 'M', 'scale': [1.0, 1.0, 1.0]},
         {'id': 'tall', 'glyph': 'T', 'scale': [0.97, 1.1, 0.97]},
         {'id': 'broad', 'glyph': 'B', 'scale': [1.12, 1.0, 1.08]},
     ]},
    {'id': 'skin', 'emoji': '✋', 'label': 'Skin', 'kind': 'color',
     'options': [
         {'id': 'porcelain', 'value': '#f3d7c2'},
         {'id': 'sand', 'value': '#e8bc95'},
         {'id': 'honey', 'value': '#c68f5f'},
         {'id': 'bronze', 'value': '#9c6b43'},
         {'id': 'umber', 'value': '#6f4a2f'},
         {'id': 'ebony', 'value': '#4a3223'},
     ]},
    {'id': 'workwear', 'emoji': '\U0001f455', 'label': 'Workwear', 'kind': 'color',
     'options': [
         {'id': 'hi-vis-orange', 'value': '#e8722a'},
         {'id': 'hi-vis-yellow', 'value': '#d9c22e'},
         {'id': 'forest', 'value': '#3c6b45'},
         {'id': 'slate', 'value': '#4a5a64'},
         {'id': 'crimson', 'value': '#a03a34'},
         {'id': 'royal', 'value': '#2f4d8a'},
     ]},
    {'id': 'hardhat', 'emoji': '⛑', 'label': 'Hard hat', 'kind': 'style',
     'options': [
         {'id': 'cap-brim', 'glyph': 'C'},
         {'id': 'full-brim', 'glyph': 'F'},
         {'id': 'climbing', 'glyph': 'K'},
         {'id': 'vintage', 'glyph': 'V'},
     ]},
    {'id': 'hatcolor', 'emoji': '\U0001f3a8', 'label': 'Hat colour', 'kind': 'color',
     'options': [
         {'id': 'safety-white', 'value': '#e9ecec'},
         {'id': 'safety-yellow', 'value': '#e6c62d'},
         {'id': 'safety-orange', 'value': '#e07425'},
         {'id': 'safety-blue', 'value': '#2f5f9e'},
         {'id': 'safety-green', 'value': '#3b7d4f'},
         {'id': 'safety-red', 'value': '#b03a30'},
     ]},
    {'id': 'vest', 'emoji': '\U0001f9ba', 'label': 'Vest', 'kind': 'style',
     'options': [
         {'id': 'none', 'glyph': '–'},
         {'id': 'stripe', 'glyph': '||'},
         {'id': 'surveyor', 'glyph': 'X'},
         {'id': 'harness', 'glyph': 'H'},
     ]},
    {'id': 'boots', 'emoji': '\U0001f97e', 'label': 'Boots', 'kind': 'color',
     'options': [
         {'id': 'tan', 'value': '#9a6f43'},
         {'id': 'brown', 'value': '#5d4127'},
         {'id': 'black', 'value': '#26262a'},
         {'id': 'grey', 'value': '#6c7276'},
     ]},
    {'id': 'tools', 'emoji': '\U0001f9f0', 'label': 'Tool belt', 'kind': 'style',
     'options': [
         {'id': 'none', 'glyph': '–'},
         {'id': 'basic', 'glyph': 'b'},
         {'id': 'framing', 'glyph': 'f'},
         {'id': 'electric', 'glyph': 'e'},
     ]},
]

DEFAULTS = {'build': 'standard', 'skin': 'honey', 'workwear': 'hi-vis-orange',
            'hardhat': 'cap-brim', 'hatcolor': 'safety-yellow',
            'vest': 'stripe', 'boots': 'tan', 'tools': 'basic'}

# Emotes: an emoji for the wheel, a label, and the procedural move the
# page animates on the avatar. All free, all cosmetic.
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
    assert len(ids) == len(set(ids)) and len(ids) >= 4, s['id']
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
    'sections': SECTIONS,
    'defaults': DEFAULTS,
    'emotes': EMOTES,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'avatars.json').write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
n_opts = sum(len(s['options']) for s in SECTIONS)
print(f"avatar pack: {len(SECTIONS)} locker sections, {n_opts} options, "
      f"{len(EMOTES)} emotes (source stamp {stamp})")
