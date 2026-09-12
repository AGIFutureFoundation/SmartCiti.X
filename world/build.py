#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the world registry builder.

Everything the environment is made of that is not a building: the sky, the
weather it is seen under, the ground it stands on, and the animals moving
through it. Until now these lived as hard-coded tables inside the page.
They live here instead, for the same reason everything else does - one
truth per fact, stated once, checked on every build.

TEXTURES. There is no texture file in this repository and none is
downloaded. Every surface below is a RECIPE - a base colour, a grain, an
octave count, a relief depth - and the page generates the image and its
normal map in the learner's own browser at boot. That is why the bundle
has no third-party artwork in its render: there is no artwork, only
arithmetic. It is also why the textures can be regenerated at a different
resolution when the quality ladder steps down.

WEATHER. Schematic, and not a forecast. Nothing here is tied to a reading
taken anywhere at any time. The per-campus atmospheres are authored by
reputation - the Bay's fog, the Gulf's haze - and say so.

FAUNA. Common names, schematic bodies, authored flight paths. No species
record, no count and no sighting is claimed; this is ambience, not a
wildlife survey.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

PACK_VERSION = "3.2.0"
BUILT = "2026-09-11"

# ---------------------------------------------------------------- the sky ---
# The dome is drawn into one equirectangular canvas per weather state: a
# vertical gradient, a sun or moon disc, a star field after dark, and a
# band of cloud. All of it arithmetic - see the note above.
SKY = {
    'projection': 'equirectangular, drawn to a 1024x512 canvas at boot',
    'bands': ['zenith', 'upper', 'horizon', 'ground_haze'],
    'disc': {
        'sun': {'radius_px': 26, 'glow_px': 150, 'color': '#fff3d0'},
        'moon': {'radius_px': 17, 'glow_px': 82, 'color': '#cfd9ea'},
        'placement': 'the disc is drawn where the key light actually comes '
                     'from - its azimuth and elevation are read off the '
                     'light, so the sun in the sky and the shadows on the '
                     'ground agree rather than merely coexisting',
    },
    'horizon_haze': {'height': .12, 'strength': .5,
                     'note': 'a bright band just above the horizon so the '
                             'dome does not end on a hard edge'},
    'stars': {'count': 420, 'only_when': 'night',
              'note': 'placed by a fixed seed, so the sky is the same sky '
                      'every time the page is opened - no two learners see '
                      'a different night'},
    'clouds': {'octaves': 4, 'band_from': .28, 'band_to': .78,
           'base_frequency': 1 / 44,
               'note': 'value noise, thickened or thinned by the weather '
                       'record rather than by a separate cloud asset'},
}

# ------------------------------------------------------------- the weather ---
# Six states, cycled from one button. Each is a set of multipliers applied
# to whichever campus atmosphere is loaded - so a campus keeps its own
# character in every weather rather than every campus looking the same in
# the rain.
WEATHER = {
    'clear': {
        'name': 'Clear', 'glyph': '☀️', 'order': 0,
        'sky_mul': 1.75, 'fog_tint': 1.0, 'fog_mul': 1.0, 'sun_mul': 1.0, 'hemi_mul': 1.0,
        'cloud': .18, 'rain': 0, 'window_glow': .5, 'wind': 0,
        'blurb': 'the working day the halls were drawn for',
    },
    'overcast': {
        'name': 'Overcast', 'glyph': '☁️', 'order': 1,
        'sky_mul': 1.18, 'fog_tint': .92, 'fog_mul': 1.15, 'sun_mul': .62, 'hemi_mul': .92,
        'cloud': .72, 'rain': 0, 'window_glow': .66, 'wind': .15,
        'blurb': 'flat light, no shadows to judge a line by - the light '
                 'a layout hand complains about',
    },
    'fog': {
        'name': 'Fog', 'glyph': '\U0001f32b️', 'order': 2,
        'sky_mul': 1.3, 'fog_tint': 1.25, 'fog_mul': .34, 'sun_mul': .5, 'hemi_mul': 1.05,
        'cloud': .5, 'rain': 0, 'window_glow': .8, 'wind': .25,
        'blurb': 'the visibility a crane signal has to survive; the Bay '
                 'campuses were drawn with this in mind',
    },
    'rain': {
        'name': 'Rain', 'glyph': '\U0001f327️', 'order': 3,
        'sky_mul': .85, 'fog_tint': .8, 'fog_mul': .86, 'sun_mul': .55, 'hemi_mul': .8,
        'cloud': .85, 'rain': .55, 'window_glow': .85, 'wind': .35,
        'blurb': 'wet ground, longer stopping distances, and every '
                 'surface in the yard reading differently',
    },
    'storm': {
        'name': 'Storm', 'glyph': '⛈️', 'order': 4,
        'sky_mul': .5, 'fog_tint': .62, 'fog_mul': .7, 'sun_mul': .42, 'hemi_mul': .62,
        'cloud': 1.0, 'rain': 1.0, 'window_glow': .95, 'wind': .8,
        'thunder': True,
        'blurb': 'the condition that stops a lift - and the one worth '
                 'practising the stop in',
    },
    'night': {
        'name': 'Night', 'glyph': '\U0001f319', 'order': 5,
        'sky_mul': .3, 'fog_tint': .32, 'fog_mul': 1.12, 'sun_mul': .28, 'hemi_mul': .42,
        'cloud': .3, 'rain': 0, 'window_glow': 1.2, 'wind': .1,
        'moon': True, 'stars': True,
        'blurb': 'the shift most of this work actually happens on',
    },
}

# ------------------------------------------------------- the ground, made ---
# Recipes, not images. `grain` is the speckle colour, `octaves` the number
# of value-noise passes, `relief` the normal-map depth (0 = flat).
GROUND = {
    'asphalt': {
        'name': 'Asphalt', 'base': '#191f22', 'grain': '220,225,225',
        'octaves': 3, 'speckle': 1800, 'relief': .35, 'repeat': 34,
        'roughness': .96, 'metalness': .0,
        'where': 'the yard running surface and the ring road',
    },
    'concrete': {
        'name': 'Concrete', 'base': '#262e31', 'grain': '235,238,238',
        'octaves': 3, 'speckle': 1000, 'relief': .22, 'repeat': 9,
        'roughness': .9, 'metalness': .02,
        'where': 'slabs, aprons and walkways',
    },
    'gravel': {
        'name': 'Compacted gravel', 'base': '#3b3a34', 'grain': '205,198,180',
        'octaves': 2, 'speckle': 5200, 'relief': .85, 'repeat': 26,
        'roughness': .99, 'metalness': .0,
        'where': 'the plant yard, where the machines actually track',
    },
    'grass': {
        'name': 'Rough grass', 'base': '#2b3a24', 'grain': '120,168,92',
        'octaves': 4, 'speckle': 6400, 'relief': .55, 'repeat': 44,
        'roughness': .98, 'metalness': .0,
        'where': 'the campus green and the verges',
    },
    'sand': {
        'name': 'Sand and fill', 'base': '#4a4234', 'grain': '214,196,158',
        'octaves': 3, 'speckle': 4200, 'relief': .4, 'repeat': 30,
        'roughness': .97, 'metalness': .0,
        'where': 'stockpiles and the excavator cut',
    },
    'water': {
        'name': 'Open water', 'base': '#10202e', 'grain': '90,150,180',
        'octaves': 5, 'speckle': 900, 'relief': .18, 'repeat': 12,
        'roughness': .28, 'metalness': .35,
        'where': 'the Bay, the estuary and the river',
    },
}

# ------------------------------------------------------------- the animals ---
# Ambience. Common names only, authored paths, schematic bodies.
FAUNA = {
    'gull': {
        'name': 'Gull', 'glyph': '\U0001f426', 'body': 'bird',
        'span_m': 1.2, 'color': '#e6ecef', 'accent': '#9aa6ad',
        'motion': 'circuit', 'height_m': [14, 30], 'speed': 1.0,
        'flock': 5, 'campuses': ['treasure-island', 'oakland'],
        'why': 'a working waterfront has gulls over it; both Bay campuses '
               'are on one',
    },
    'pelican': {
        'name': 'Brown pelican', 'glyph': '\U0001f9a9', 'body': 'bird',
        'span_m': 2.0, 'color': '#8d7f6c', 'accent': '#e0d6c2',
        'motion': 'glide', 'height_m': [10, 18], 'speed': .6,
        'flock': 3, 'campuses': ['new-orleans', 'houston'],
        'why': 'Louisiana’s state bird, and unmistakable over any Gulf '
               'coast - the ship channel included',
    },
    'ring-billed-gull': {
        'name': 'Ring-billed gull', 'glyph': '\U0001f426', 'body': 'bird',
        'span_m': 1.1, 'color': '#e8ecec', 'accent': '#8f9ba0',
        'motion': 'circuit', 'height_m': [12, 26], 'speed': 1.0,
        'flock': 5, 'campuses': ['chicago'],
        'why': 'the lakefront gull, by reputation the most familiar bird '
               'on the Chicago waterfront',
    },
    'egret': {
        'name': 'Egret', 'glyph': '\U0001f54a️', 'body': 'wader',
        'span_m': 1.0, 'color': '#f2f4f2', 'accent': '#d8cc9a',
        'motion': 'perch', 'height_m': [0, 0], 'speed': .2,
        'flock': 2, 'campuses': ['new-orleans'],
        'why': 'standing in the wet margin, which is most of the ground '
               'around this campus',
    },
    'pigeon': {
        'name': 'Pigeon', 'glyph': '\U0001f54a️', 'body': 'bird',
        'span_m': .6, 'color': '#6b7076', 'accent': '#2f3a42',
        'motion': 'hop', 'height_m': [0, 6], 'speed': .5,
        'flock': 6,
        'campuses': ['treasure-island', 'oakland', 'new-orleans', 'houston',
                     'chicago'],
        'why': 'every yard in every city has them, and they are the scale '
               'reference nobody thinks about',
    },
    'yard-dog': {
        'name': 'Yard dog', 'glyph': '\U0001f415', 'body': 'quadruped',
        'span_m': 1.0, 'color': '#6f5a44', 'accent': '#3a2f24',
        'motion': 'patrol', 'height_m': [0, 0], 'speed': .55,
        'flock': 1,
        'campuses': ['treasure-island', 'oakland', 'new-orleans', 'houston',
                     'chicago'],
        'why': 'the yard dog is a fixture of the trade, and it teaches the '
               'habit of looking down before reversing',
    },
}

# -------------------------------------------------- the campus atmospheres ---
# Moved here out of the page, unchanged: authored ambience, by reputation.
ATMOS = {
    'treasure-island': {
        'sky': ['#0b141d', '#22323e', '#48575f', '#5e646a'],
        'fog': {'color': 0x2b3a42, 'mul': .62}, 'banks': 6,
        'sun': {'color': 0xd8e2e8, 'i': 1.15},
        'hemi': {'sky': 0x9fb4c0, 'ground': 0x24211c, 'i': 1.15},
        'amb': {'wind': .8, 'gulls': True, 'harbor': True},
        'ground': 'concrete', 'verge': 'grass',
        'character': 'marine layer off the Pacific; cool, grey and bright '
                     'at once - authored by reputation, not measured',
    },
    'oakland': {
        'sky': ['#0c141c', '#1a2a36', '#33404a', '#5a4426'],
        'fog': {'color': 0x1f2820, 'mul': 1}, 'banks': 0,
        'sun': {'color': 0xffd9a0, 'i': 1.7},
        'hemi': {'sky': 0xaec2cb, 'ground': 0x241d16, 'i': 1.05},
        'amb': {'wind': .45, 'gulls': True, 'harbor': True},
        'ground': 'asphalt', 'verge': 'gravel',
        'character': 'the estuary side, warmer and harder-edged than the '
                     'island - authored by reputation, not measured',
    },
    'new-orleans': {
        'sky': ['#101318', '#26272e', '#4a4238', '#6e4c30'],
        'fog': {'color': 0x2e2b26, 'mul': .8}, 'banks': 0,
        'sun': {'color': 0xffc98a, 'i': 1.45},
        'hemi': {'sky': 0xb8ac9c, 'ground': 0x2a2018, 'i': 1.1},
        'amb': {'wind': .3, 'insects': True, 'thunder': True},
        'ground': 'concrete', 'verge': 'grass',
        'character': 'Gulf humidity and a low warm haze - authored by '
                     'reputation, not measured',
    },
    'houston': {
        'sky': ['#141210', '#2c2620', '#5c4e34', '#7a5a2e'],
        'fog': {'color': 0x33291c, 'mul': 1.35}, 'banks': 2,
        'sun': {'color': 0xffcf8c, 'i': 1.35},
        'hemi': {'sky': 0xbfae8c, 'ground': 0x261f14, 'i': 1.0},
        'amb': {'wind': .2, 'insects': True, 'thunder': True},
        'ground': 'asphalt', 'verge': 'gravel',
        'character': 'Gulf-coast heat haze over a working ship channel, a '
                     'refinery glow at the sky\'s edge after dark - '
                     'authored by reputation, not measured',
    },
    'chicago': {
        'sky': ['#12161c', '#232c38', '#4a5866', '#7d8a92'],
        'fog': {'color': 0x28313a, 'mul': 1.1}, 'banks': 4,
        'sun': {'color': 0xdfe8ee, 'i': 1.2},
        'hemi': {'sky': 0xa8b8c2, 'ground': 0x201e1c, 'i': 1.1},
        'amb': {'wind': .95, 'gulls': True, 'harbor': False},
        'ground': 'concrete', 'verge': 'gravel',
        'character': 'a flat lakefront wind that never really stops, cold '
                     'and grey off the water most of the year - authored '
                     'by reputation, not measured',
    },
}

HONESTY = {
    'textures': 'no texture, photograph or artwork file exists in this '
                'repository and none is downloaded: every surface is a '
                'recipe - a base colour, a grain, an octave count and a '
                'relief depth - and the page generates the image and its '
                'normal map in the learner\'s own browser at boot. There '
                'is therefore no third-party artwork anywhere in the '
                'render.',
    'weather': 'schematic weather, not a forecast and not an observation: '
               'nothing here is tied to a reading taken at any real place '
               'or time, and the per-campus atmospheres are authored by '
               'reputation rather than measured.',
    'fauna': 'ambience, not a wildlife survey: common names, schematic '
             'bodies and authored paths. No species record, population '
             'count or sighting is claimed, and no animal here is drawn '
             'from any photograph.',
    'sky': 'the sky is generated, not photographed, and the night sky is '
           'placed by a fixed seed rather than from any star catalogue - '
           'it is a night sky, not the night sky.',
    'ground': 'the ground a campus stands on is SCHEMATIC like the '
              'buildings on it: the surfaces are the ones the trade '
              'actually works over, but their extent and placement are '
              'drawn to teach, not surveyed.',
}

# ---------------------------------------------------------------- checks ---
campuses = json.load(open(ROOT / 'unions/registry/campuses.json'))['campuses']
assert set(ATMOS) == set(campuses), 'one atmosphere per campus, exactly'

for ck, a in ATMOS.items():
    assert a['ground'] in GROUND, f'{ck}: ground {a["ground"]} is not a recipe'
    assert a['verge'] in GROUND, f'{ck}: verge {a["verge"]} is not a recipe'
    assert len(a['sky']) == len(SKY['bands']), \
        f'{ck}: sky stops must match the declared bands'
    assert 'reputation' in a['character'], \
        f'{ck}: an authored atmosphere must say it is authored'

orders = sorted(w['order'] for w in WEATHER.values())
assert orders == list(range(len(WEATHER))), 'the weather cycle must be a cycle'
for wk, w in WEATHER.items():
    assert 0 <= w['rain'] <= 1 and 0 <= w['cloud'] <= 1, f'{wk}: out of range'
    assert 0 < w['sky_mul'] <= 2 and 0 < w['fog_tint'] <= 2, \
        f'{wk}: sky and fog multipliers must stay sane'
    assert w['blurb'] and w['glyph'] and w['name'], f'{wk}: unlabelled state'

for fk, f in FAUNA.items():
    assert set(f['campuses']) <= set(campuses), f'{fk}: unknown campus'
    assert f['flock'] >= 1 and f['span_m'] > 0, f'{fk}: implausible'
    assert f['why'], f'{fk}: an animal in the yard needs a reason to be there'

# the page must actually build all of it, and must never fetch an image
BOOTSTRAP = '--bootstrap' in __import__('sys').argv
if not BOOTSTRAP:
    page = (ROOT / 'web/trade_craft_3d.html').read_text()
    # the page names none of these literally any more - it reads them from
    # this registry, which is the point - so they are checked in the data
    # blob, and the code that consumes them is checked by name below
    for wk in WEATHER:
        assert f'"{wk}"' in page, f'weather {wk} never reaches the page'
    for gk in GROUND:
        assert f'"{gk}"' in page, f'ground {gk} never reaches the page'
    assert 'function setWeather(' in page, 'the page has no weather cycle'
    assert 'function groundMat(' in page, 'the page builds no surface recipes'
    for fk in FAUNA:
        assert f'"{fk}"' in page, f'{fk} is declared but never reaches the page'
    for fn in ('function groundTex(', 'function skyCanvas(',
               'function spawnFauna(', 'function faunaStep('):
        assert fn in page, f'the page does not build the world: {fn} missing'
    # the texture claim is only worth making if nothing loads an image
    for banned in ('TextureLoader', '.jpg', '.png', '.hdr', '.exr',
                   'CubeTextureLoader', 'RGBELoader'):
        assert banned not in page, \
            f'the page claims every texture is generated but references {banned}'

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

doc = {
    'pack': 'smartcitix-trade-craft-academy-world',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'honesty': HONESTY,
    'counts': {'weather': len(WEATHER), 'ground': len(GROUND),
               'fauna': len(FAUNA),
               'animals': sum(f['flock'] * len(f['campuses'])
                              for f in FAUNA.values())},
    'sky': SKY,
    'weather': WEATHER,
    'ground': GROUND,
    'fauna': FAUNA,
    'atmos': ATMOS,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'world.json').write_text(json.dumps(doc, indent=1) + '\n')
print(f"world: {len(WEATHER)} weather states, {len(GROUND)} generated ground "
      f"surfaces, {len(FAUNA)} animals ({doc['counts']['animals']} placed "
      f"across {len(ATMOS)} campuses) (source stamp {stamp})")
