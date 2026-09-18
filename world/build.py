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
import re

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

# One bundle version, read from the manifest rather than typed here.
PACK_VERSION = json.load(open(ROOT / 'pack/manifest.json'))['pack_version']
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
    # The Bay Restoration walks stood on the campus green - one rough-grass
    # pad at every site, whatever its habitat. These four are the ground
    # those walks actually cross, and a site picks one from its own habitat
    # line in restoration/. Schematic like everything else here: composed
    # from the habitat each project describes, not sampled from the place.
    'marsh': {
        'name': 'Tidal marsh', 'base': '#33412c', 'grain': '138,166,104',
        'octaves': 4, 'speckle': 7200, 'relief': .62, 'repeat': 40,
        'roughness': .97, 'metalness': .02,
        'where': 'vegetated tidal marsh, wet underfoot between the channels',
    },
    'mudflat': {
        'name': 'Tidal flat', 'base': '#3d3b31', 'grain': '150,146,128',
        'octaves': 5, 'speckle': 2600, 'relief': .30, 'repeat': 26,
        'roughness': .82, 'metalness': .06,
        'where': 'the intertidal flat a managed pond becomes as it reopens',
    },
    'upland': {
        'name': 'Dry upland', 'base': '#3f4230', 'grain': '176,178,126',
        'octaves': 3, 'speckle': 5600, 'relief': .48, 'repeat': 38,
        'roughness': .98, 'metalness': .0,
        'where': 'the dry ground above the tide line, where the uplands are '
                 'planted back',
    },
    'levee': {
        'name': 'Levee crown', 'base': '#4b4740', 'grain': '198,190,168',
        'octaves': 2, 'speckle': 4800, 'relief': .70, 'repeat': 28,
        'roughness': .99, 'metalness': .0,
        'where': 'the compacted crown of a dike or levee, which is the path '
                 'a crew actually walks a diked site on',
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
        'flock': 5, 'campuses': ['treasure-island', 'oakland', 'seattle'],
        'why': 'a working waterfront has gulls over it; both Bay campuses '
               'and the Sound waterfront at Seattle are on one',
    },
    'pelican': {
        'name': 'Brown pelican', 'glyph': '\U0001f9a9', 'body': 'bird',
        'span_m': 2.0, 'color': '#8d7f6c', 'accent': '#e0d6c2',
        'motion': 'glide', 'height_m': [10, 18], 'speed': .6,
        'flock': 3, 'campuses': ['new-orleans', 'houston', 'miami'],
        'why': 'Louisiana’s state bird, and unmistakable over any Gulf '
               'coast or Biscayne Bay alike - the ship channel and the '
               'working port both',
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
                     'chicago', 'seattle', 'pittsburgh', 'denver', 'miami',
                     'detroit'],
        'why': 'every yard in every city has them, and they are the scale '
               'reference nobody thinks about',
    },
    'yard-dog': {
        'name': 'Yard dog', 'glyph': '\U0001f415', 'body': 'quadruped',
        'span_m': 1.0, 'color': '#6f5a44', 'accent': '#3a2f24',
        'motion': 'patrol', 'height_m': [0, 0], 'speed': .55,
        'flock': 1,
        'campuses': ['treasure-island', 'oakland', 'new-orleans', 'houston',
                     'chicago', 'seattle', 'pittsburgh', 'denver', 'miami',
                     'detroit'],
        'why': 'the yard dog is a fixture of the trade, and it teaches the '
               'habit of looking down before reversing',
    },
}

# -------------------------------------------------- the campus atmospheres ---
# Moved here out of the page, unchanged: authored ambience, by reputation.
# The page's surface engine draws these patterns and the campus builder
# draws these rooflines; a fabric may name nothing else. Closed sets, so a
# typo cannot invent a facade the renderer would silently ignore.
FACADE_PATTERNS = ('panel', 'brick', 'block', 'smooth', 'plywood', 'board')
ROOFLINES = ('flat', 'gable', 'saw')

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
    'seattle': {
        'sky': ['#10151a', '#232c31', '#495459', '#7c8a8c'],
        'fog': {'color': 0x2a3236, 'mul': 1.5}, 'banks': 6,
        'sun': {'color': 0xd6e0e0, 'i': .95},
        'hemi': {'sky': 0x9aabac, 'ground': 0x22201c, 'i': 1.0},
        'amb': {'wind': .5, 'gulls': True, 'harbor': True},
        'ground': 'concrete', 'verge': 'gravel',
        'character': 'a low marine overcast off the Sound, a working '
                     'waterfront and the hum of aerospace manufacturing '
                     'just south of the green - authored by reputation, '
                     'not measured',
    },
    'pittsburgh': {
        'sky': ['#13161a', '#282c2e', '#4c4c49', '#6e6155'],
        'fog': {'color': 0x33302a, 'mul': 1.2}, 'banks': 3,
        'sun': {'color': 0xd9d0bd, 'i': 1.05},
        'hemi': {'sky': 0x9a9c96, 'ground': 0x241f1a, 'i': 1.0},
        'amb': {'wind': .4, 'gulls': False, 'harbor': True},
        'ground': 'concrete', 'verge': 'gravel',
        'character': 'a river haze over three confluent rivers crossed '
                     'by more bridges than any other American city, and '
                     'a post-industrial skyline standing where the mills '
                     'once were - authored by reputation, not measured',
    },
    'denver': {
        'sky': ['#0b1120', '#1c2e4a', '#3f5c88', '#e8a24a'],
        'fog': {'color': 0x2a3446, 'mul': .4}, 'banks': 0,
        'sun': {'color': 0xfff2d6, 'i': 1.6},
        'hemi': {'sky': 0x8fa8c4, 'ground': 0x2c2620, 'i': 1.15},
        'amb': {'wind': .55, 'gulls': False, 'harbor': False, 'thunder': True},
        'ground': 'concrete', 'verge': 'gravel',
        'character': 'thin, dry high-altitude light off the Front Range, '
                     'a mining and energy heritage at 5,280 feet, and the '
                     'Rockies standing on the western horizon - authored '
                     'by reputation, not measured',
    },
    'miami': {
        'sky': ['#0d1b26', '#1e3a44', '#3f8a92', '#f2c14e'],
        'fog': {'color': 0x2e3a3a, 'mul': 1.0}, 'banks': 1,
        'sun': {'color': 0xffdf9e, 'i': 1.55},
        'hemi': {'sky': 0xb9d8d6, 'ground': 0x24221a, 'i': 1.05},
        'amb': {'wind': .4, 'insects': True, 'harbor': True, 'thunder': True},
        'ground': 'concrete', 'verge': 'grass',
        'character': 'subtropical coastal heat and humidity off Biscayne '
                     'Bay, afternoon thunderheads stacking through '
                     'hurricane season, and a working seaport at the '
                     'harbor\'s edge - authored by reputation, not '
                     'measured',
    },
    'detroit': {
        'sky': ['#12161c', '#282e34', '#4e5458', '#7a6a4a'],
        'fog': {'color': 0x2c302e, 'mul': 1.15}, 'banks': 3,
        'sun': {'color': 0xe6d4a8, 'i': 1.2},
        'hemi': {'sky': 0x9ba4a2, 'ground': 0x241f1a, 'i': 1.0},
        'amb': {'wind': .45, 'gulls': False, 'harbor': True},
        'ground': 'concrete', 'verge': 'gravel',
        'character': 'a Great Lakes river haze off the Detroit River, a '
                     'working industrial waterfront across from Windsor, '
                     'Ontario, and a century of automotive manufacturing '
                     'standing behind the skyline - authored by '
                     'reputation, not measured',
    },
}

# ---------------------------------------------------------- built fabric --
# What each campus is BUILT of.
#
# Every campus already had its own sky, fog, sun, ambient bed and ground -
# and then all ten drew the same building: one flat envelope, one roofline
# per district, the same trim everywhere. Ten cities that were distinguished
# only by their weather.
#
# `facade` is a pattern key the page's own surface engine already knows (the
# same set the floors and walls use), `facade_color` and `trim` are the
# envelope and its band, `roof` is the roofline this city's fabric leans to
# where the district has no stronger opinion, and `roof_color` is what the
# roofline is made of.
#
# AUTHORED BY REPUTATION, exactly like the `character` line each of these
# sits beside: no site has been surveyed, no building here is drawn from a
# photograph or a plan, and no real building is depicted. What a city is
# known for building with is a reputation, and the record says so rather
# than implying a survey.
FABRIC = {
    'treasure-island': {
        'facade': 'panel', 'facade_color': '#3f4b50', 'trim': '#9db2b8',
        'roof': 'flat', 'roof_color': '#6d7a7e',
        'why': 'the flat-roofed concrete and steel sheds of a former naval '
               'station, pale and salt-weathered',
    },
    'oakland': {
        'facade': 'brick', 'facade_color': '#77463a', 'trim': '#c4763f',
        'roof': 'saw', 'roof_color': '#5b5450',
        'why': 'estuary-side brick warehousing under sawtooth light '
               'monitors, warmer and harder-edged than the island',
    },
    'new-orleans': {
        'facade': 'smooth', 'facade_color': '#8b8067', 'trim': '#4f7d6a',
        'roof': 'gable', 'roof_color': '#5e5a4e',
        'why': 'stuccoed masonry under pitched roofs with deep galleries, '
               'built for rain and shade',
    },
    'houston': {
        'facade': 'panel', 'facade_color': '#69737a', 'trim': '#d8a33d',
        'roof': 'flat', 'roof_color': '#7d858a',
        'why': 'metal-clad process plant at petrochemical scale, flat and '
               'wide with everything on the outside',
    },
    'chicago': {
        'facade': 'brick', 'facade_color': '#8a4f3d', 'trim': '#5d6b78',
        'roof': 'flat', 'roof_color': '#6a7076',
        'why': 'load-bearing masonry on a steel frame behind a flat '
               'parapet, the city that invented the arrangement',
    },
    'seattle': {
        'facade': 'plywood', 'facade_color': '#54614f', 'trim': '#a9b8ae',
        'roof': 'gable', 'roof_color': '#4e5a57',
        'why': 'heavy timber and glass under a pitched roof, green-grey '
               'and built to shed rain',
    },
    'pittsburgh': {
        'facade': 'brick', 'facade_color': '#6d4134', 'trim': '#41505a',
        'roof': 'saw', 'roof_color': '#3f4750',
        'why': 'mill brick and blackened structural steel under sawtooth '
               'glazing, a river valley of shops',
    },
    'denver': {
        'facade': 'block', 'facade_color': '#9b9078', 'trim': '#b5643a',
        'roof': 'flat', 'roof_color': '#8a8271',
        'why': 'concrete block and stone in high-desert buff, flat-roofed '
               'under a dry sky',
    },
    'miami': {
        'facade': 'smooth', 'facade_color': '#c9d2cc', 'trim': '#39a3a8',
        'roof': 'flat', 'roof_color': '#aab4b2',
        'why': 'light stucco with shuttered openings and flat roofs, '
               'detailed for wind and sun',
    },
    'detroit': {
        'facade': 'block', 'facade_color': '#7a7e79', 'trim': '#a8402f',
        'roof': 'saw', 'roof_color': '#4a4f52',
        'why': 'heavy plant in block and steel under sawtooth bays, built '
               'around the line rather than the street',
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
    # the built fabric, held to the same contract the atmosphere is
    f = FABRIC[ck]
    assert f['facade'] in FACADE_PATTERNS, \
        f'{ck}: facade {f["facade"]} is not a pattern the page can draw'
    assert f['roof'] in ROOFLINES, f'{ck}: roof {f["roof"]} is not a roofline'
    for key in ('facade_color', 'trim', 'roof_color'):
        assert re.fullmatch(r'#[0-9a-f]{6}', f[key]), f'{ck}: {key} is not a colour'
    assert len(f['why']) > 25, f'{ck}: a fabric with no reason is a preference'
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
    'fabric': FABRIC,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'world.json').write_text(json.dumps(doc, indent=1) + '\n')
print(f"world: {len(WEATHER)} weather states, {len(GROUND)} generated ground "
      f"surfaces, {len(FAUNA)} animals ({doc['counts']['animals']} placed "
      f"across {len(ATMOS)} campuses) (source stamp {stamp})")
