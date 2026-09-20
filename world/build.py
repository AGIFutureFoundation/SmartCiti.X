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
    # The haze band is the last thing the eye reads before the ground, and
    # it was one colour for the whole network: every campus ended its dome
    # on the same cool grey. The band keeps a default here and a campus may
    # state its own `haze` instead, because a refinery horizon and a high
    # desert horizon are not the same colour at the same hour.
    'horizon_haze': {'height': .12, 'strength': .5,
                     'day_tint': '214,226,236',
                     'night_tint': '150,166,190',
                     'night_strength_mul': .35,
                     'note': 'a bright band just above the horizon so the '
                             'dome does not end on a hard edge; a campus '
                             'that names its own haze overrides day_tint'},
    'stars': {'count': 420, 'only_when': 'night',
              'note': 'placed by a fixed seed, so the sky is the same sky '
                      'every time the page is opened - no two learners see '
                      'a different night'},
    # `lacunarity`, `day_lum` and `night_lum` were literals inside the
    # page's cloud loop. They are the shape of the cloud, which is a world
    # fact, so they are declared here with the rest of the dome. The values
    # are the page's own, unchanged: this is a move, not a second opinion,
    # and it is finished when the page reads them from here.
    'clouds': {'octaves': 4, 'band_from': .28, 'band_to': .78,
           'base_frequency': 1 / 44,
               'lacunarity': 2.1, 'day_lum': 232, 'night_lum': 96,
               'note': 'value noise, thickened or thinned by the weather '
                       'record rather than by a separate cloud asset'},
}

# ------------------------------------------------------------- the weather ---
# Six states, cycled from one button. Each is a set of multipliers applied
# to whichever campus atmosphere is loaded - so a campus keeps its own
# character in every weather rather than every campus looking the same in
# the rain.
#
# Two things the states used to leave unsaid, and which a yard actually
# reads by:
#
# `wet` is how wet the GROUND is, 0 to 1, independent of how hard it is
# raining at this instant. The rain state's own blurb has always promised
# "every surface in the yard reading differently" and nothing anywhere
# implemented it; a wet slab is darker and far less rough than a dry one,
# and that is the single cheapest thing a renderer can do with a ground
# recipe. Fog leaves a yard damp without a drop falling, which is why fog
# is wetter than overcast.
#
# `bank_mul` and `bank_floor` are the fog banks. A campus declares how many
# banks it keeps by reputation - the Bay six, Denver none - and the weather
# could only scale that, so FOG WEATHER OVER DENVER PUT NO FOG IN THE AIR.
# A floor fixes it: a state may put banks in the air that the campus does
# not keep on its own, while a campus that keeps them still keeps more.
WEATHER = {
    'clear': {
        'name': 'Clear', 'glyph': '☀️', 'order': 0,
        'sky_mul': 1.75, 'fog_tint': 1.0, 'fog_mul': 1.0, 'sun_mul': 1.0, 'hemi_mul': 1.0,
        'cloud': .18, 'rain': 0, 'window_glow': .5, 'wind': 0,
        'wet': 0, 'bank_mul': .5, 'bank_floor': 0,
        'blurb': 'the working day the halls were drawn for - hard shadows, '
                 'dry ground, and nothing in the air to hide a hand signal',
    },
    'overcast': {
        'name': 'Overcast', 'glyph': '☁️', 'order': 1,
        'sky_mul': 1.18, 'fog_tint': .92, 'fog_mul': 1.15, 'sun_mul': .62, 'hemi_mul': .92,
        'cloud': .72, 'rain': 0, 'window_glow': .66, 'wind': .15,
        'wet': .12, 'bank_mul': 1.0, 'bank_floor': 0,
        'blurb': 'flat light, no shadows to judge a line by - the light '
                 'a layout hand complains about',
    },
    'fog': {
        'name': 'Fog', 'glyph': '\U0001f32b️', 'order': 2,
        'sky_mul': 1.3, 'fog_tint': 1.25, 'fog_mul': .34, 'sun_mul': .5, 'hemi_mul': 1.05,
        'cloud': .5, 'rain': 0, 'window_glow': .8, 'wind': .25,
        'wet': .4, 'bank_mul': 2.0, 'bank_floor': 5,
        'blurb': 'the visibility a crane signal has to survive; the Bay '
                 'campuses were drawn with this in mind, and it leaves the '
                 'ground damp without a drop having fallen',
    },
    'rain': {
        'name': 'Rain', 'glyph': '\U0001f327️', 'order': 3,
        'sky_mul': .85, 'fog_tint': .8, 'fog_mul': .86, 'sun_mul': .55, 'hemi_mul': .8,
        'cloud': .85, 'rain': .55, 'window_glow': .85, 'wind': .35,
        'wet': .85, 'bank_mul': 1.2, 'bank_floor': 1,
        'blurb': 'wet ground, longer stopping distances, and every '
                 'surface in the yard reading differently',
    },
    'storm': {
        'name': 'Storm', 'glyph': '⛈️', 'order': 4,
        'sky_mul': .5, 'fog_tint': .62, 'fog_mul': .7, 'sun_mul': .42, 'hemi_mul': .62,
        'cloud': 1.0, 'rain': 1.0, 'window_glow': .95, 'wind': .8,
        'thunder': True,
        'wet': 1.0, 'bank_mul': 1.5, 'bank_floor': 2,
        'blurb': 'the condition that stops a lift - and the one worth '
                 'practising the stop in',
    },
    'night': {
        'name': 'Night', 'glyph': '\U0001f319', 'order': 5,
        'sky_mul': .3, 'fog_tint': .32, 'fog_mul': 1.12, 'sun_mul': .28, 'hemi_mul': .42,
        'cloud': .3, 'rain': 0, 'window_glow': 1.2, 'wind': .1,
        'moon': True, 'stars': True,
        'wet': .25, 'bank_mul': 1.3, 'bank_floor': 0,
        'blurb': 'the shift most of this work actually happens on - dew on '
                 'the steel by the small hours, and every edge lit by a '
                 'tower rather than by the sun',
    },
}

# ------------------------------------------------------- the ground, made ---
# Recipes, not images. `grain` is the speckle colour, `octaves` the number
# of value-noise passes, `speckle` how many grains are thrown on top,
# `relief` the normal-map depth (0 = flat) and `repeat` how many times one
# tile is laid across a mesh that does not ask for its own scale.
#
# PROVENANCE. A recipe is AUTHORED, and it is composed from the character a
# place is known for - the shell fill of the delta, the slag of a mill
# valley, the limerock South Florida quarries out from under itself. It is
# not a survey, a photograph or a scan of any yard, and nothing here should
# ever be read as one. The same honesty the campus atmospheres carry:
# authored by reputation.
#
# READING AT WALKING DISTANCE. One tile can cover fifteen metres of a
# campus yard, so the detail a boot is close to has to live INSIDE the
# tile: that is what the octave count and the speckle are for. The coarse
# octaves give the surface its patchwork at a distance and the fine ones
# give it something to be at arm's length. A recipe with two octaves and a
# thin speckle is a colour, not a ground - which is what most of these
# were.
GROUND = {
    'asphalt': {
        'name': 'Asphalt', 'base': '#1c2124', 'grain': '216,222,222',
        'octaves': 5, 'speckle': 3200, 'relief': .42, 'repeat': 34,
        'roughness': .96, 'metalness': .0,
        'where': 'the yard running surface and the ring road',
        'why': 'a binder course that has been driven on goes grey in the '
               'wheel tracks and keeps its aggregate proud everywhere '
               'else, so it wants fine octaves rather than a flat black',
    },
    'concrete': {
        'name': 'Concrete', 'base': '#2a3236', 'grain': '236,238,236',
        'octaves': 5, 'speckle': 1700, 'relief': .26, 'repeat': 9,
        'roughness': .88, 'metalness': .02,
        'where': 'slabs, aprons and walkways',
        'why': 'a power-trowelled slab is nearly flat and still not smooth: '
               'the relief is small on purpose and the grain does the work',
    },
    'gravel': {
        'name': 'Compacted gravel', 'base': '#3e3d36', 'grain': '208,200,182',
        'octaves': 4, 'speckle': 6400, 'relief': .90, 'repeat': 22,
        'roughness': .99, 'metalness': .0,
        'where': 'the plant yard, where the machines actually track',
        'why': 'loose aggregate is all edge and shadow; it is the deepest '
               'relief in the table short of ballast, because that is what '
               'it looks like from a metre up',
    },
    'grass': {
        'name': 'Rough grass', 'base': '#2d3d25', 'grain': '126,172,96',
        'octaves': 5, 'speckle': 7200, 'relief': .58, 'repeat': 40,
        'roughness': .98, 'metalness': .0,
        'where': 'the campus green and the verges',
        'why': 'unirrigated mown grass is never one green: the extra octave '
               'is the mower pattern and the dry patches it leaves',
    },
    'sand': {
        'name': 'Sand and fill', 'base': '#4d4536', 'grain': '218,200,162',
        'octaves': 4, 'speckle': 4800, 'relief': .44, 'repeat': 26,
        'roughness': .97, 'metalness': .0,
        'where': 'stockpiles and the excavator cut',
        'why': 'a cut face and a stockpile are the same material at two '
               'angles of repose, so it is graded fine and lit soft',
    },
    # The Bay Restoration walks stood on the campus green - one rough-grass
    # pad at every site, whatever its habitat. These four are the ground
    # those walks actually cross, and a site picks one from its own habitat
    # line in restoration/. Schematic like everything else here: composed
    # from the habitat each project describes, not sampled from the place.
    'marsh': {
        'name': 'Tidal marsh', 'base': '#32422c', 'grain': '138,166,104',
        'octaves': 5, 'speckle': 7600, 'relief': .64, 'repeat': 36,
        'roughness': .97, 'metalness': .02,
        'where': 'vegetated tidal marsh, wet underfoot between the channels',
        'why': 'pickleweed and cordgrass stand in clumps with water between '
               'them, which is a clumped grain and a trace of sheen',
    },
    'mudflat': {
        'name': 'Tidal flat', 'base': '#3e3c32', 'grain': '150,146,128',
        'octaves': 5, 'speckle': 3000, 'relief': .34, 'repeat': 30,
        'roughness': .78, 'metalness': .06,
        'where': 'the intertidal flat a managed pond becomes as it reopens',
        'why': 'a flat that has just drained holds a film of water in every '
               'channel, so it is the least rough ground in the table that '
               'is not open water',
    },
    'upland': {
        'name': 'Dry upland', 'base': '#3f4230', 'grain': '176,178,126',
        'octaves': 4, 'speckle': 6000, 'relief': .50, 'repeat': 34,
        'roughness': .98, 'metalness': .0,
        'where': 'the dry ground above the tide line and on made land: '
                 'where the uplands are planted back, and the windward fill '
                 'of an island yard that nobody waters',
        'why': 'dry grass over a thin soil shows the ground through it, '
               'which is a bright grain on a drab base rather than a green',
    },
    'levee': {
        'name': 'Levee crown', 'base': '#4b4740', 'grain': '198,190,168',
        'octaves': 3, 'speckle': 5200, 'relief': .72, 'repeat': 24,
        'roughness': .99, 'metalness': .0,
        'where': 'the compacted crown of a dike or levee, which is the path '
                 'a crew actually walks a diked site on',
        'why': 'a crown is rutted along its length by the truck that '
               'maintains it and loose at the edges where nothing drives',
    },
    'water': {
        'name': 'Open water', 'base': '#10202e', 'grain': '90,150,180',
        'octaves': 5, 'speckle': 900, 'relief': .20, 'repeat': 12,
        'roughness': .22, 'metalness': .40,
        'where': 'the Bay, the estuary and the river',
        'why': 'the only surface here that is more mirror than material, '
               'which is what the low roughness and high metalness say',
    },
    # ---------------------------------------------------- the ten yards ---
    # Every campus was laid on `concrete` or `asphalt`, and the only thing
    # that changed between San Francisco and Miami was the verge. Ten cities
    # told apart by their weather, standing on one slab. These ten are the
    # ground each of those yards is actually made of - one per campus, none
    # shared - and the campus record below says what chose it.
    #
    # AUTHORED, like the fabric beside it: what a place is built on is a
    # reputation, and no yard here was surveyed.
    'salt-slab': {
        'name': 'Salt-weathered slab', 'base': '#3a4145', 'grain': '228,232,230',
        'octaves': 5, 'speckle': 2400, 'relief': .32, 'repeat': 12,
        'roughness': .93, 'metalness': .01,
        'where': 'the concrete apron of a former naval station on made '
                 'ground, bleached pale and stained at every joint',
        'why': 'salt air takes the fines out of a slab and leaves the '
               'aggregate standing: it is paler, pitted and rust-flecked '
               'where the reinforcement is closest to the top',
    },
    'hardstand': {
        'name': 'Container hardstand', 'base': '#22282a', 'grain': '198,206,206',
        'octaves': 5, 'speckle': 2800, 'relief': .38, 'repeat': 18,
        'roughness': .95, 'metalness': .0,
        'where': 'the crane-rated hardstand of a working terminal, rutted '
                 'on the turning circles and patched everywhere else',
        'why': 'a surface built to carry a loaded stacker is repaired in '
               'pieces for thirty years, so it reads as patchwork - the '
               'coarse octaves are the patches, not noise',
    },
    'shell': {
        'name': 'Crushed shell', 'base': '#4e4c40', 'grain': '234,228,208',
        'octaves': 4, 'speckle': 7000, 'relief': .74, 'repeat': 24,
        'roughness': .98, 'metalness': .0,
        'where': 'the crushed-shell yard fill of a delta with no rock in '
                 'it, pale, sharp and loud underfoot',
        'why': 'the Gulf delta has shell where other places have quarry '
               'stone, and a shell yard is far brighter than the ground '
               'beside it - which is the whole look of the place',
    },
    'caliche': {
        'name': 'Caliche pad', 'base': '#585040', 'grain': '226,212,178',
        'octaves': 4, 'speckle': 5600, 'relief': .55, 'repeat': 26,
        'roughness': .98, 'metalness': .0,
        'where': 'the caliche and crushed-limestone pad a coastal-plain '
                 'plant yard is built up on, above ground that moves',
        'why': 'gumbo clay swells and shrinks with every wet season, so the '
               'yard is a pad brought in on trucks: buff, dusty dry and '
               'set hard, with nothing of the soil under it showing',
    },
    'ballast': {
        'name': 'Track ballast', 'base': '#3c3c3a', 'grain': '198,194,186',
        'octaves': 4, 'speckle': 6800, 'relief': .96, 'repeat': 20,
        'roughness': .99, 'metalness': .0,
        'where': 'the angular crushed stone of a rail yard, laid to drain '
                 'and never laid to be walked on',
        'why': 'ballast is deliberately sharp and deliberately loose so it '
               'keys together and sheds water; it is the deepest relief in '
               'the table because every stone casts on its neighbour',
    },
    'basalt': {
        'name': 'Crushed basalt', 'base': '#2f3639', 'grain': '178,188,188',
        'octaves': 5, 'speckle': 6000, 'relief': .80, 'repeat': 22,
        'roughness': .97, 'metalness': .01,
        'where': 'the blue-grey crushed basalt a rain-country yard is '
                 'surfaced with, darker in the joints where it stays wet',
        'why': 'the Cascade quarries are basalt, and in a climate that '
               'never fully dries the stone reads blue-grey and the gaps '
               'between it read green',
    },
    'slag': {
        'name': 'Air-cooled slag', 'base': '#474845', 'grain': '214,212,200',
        'octaves': 5, 'speckle': 6600, 'relief': .88, 'repeat': 22,
        'roughness': .99, 'metalness': .03,
        'where': 'the pale vesicular slag a mill valley paved its own yards '
                 'and roadbeds with, for a century, because it had it',
        'why': 'air-cooled blast-furnace slag is light, sharp and full of '
               'holes: it is paler than the stone around it and it glints, '
               'which is why the metalness is not quite zero',
    },
    'decomposed-granite': {
        'name': 'Decomposed granite', 'base': '#574c3e', 'grain': '228,208,178',
        'octaves': 4, 'speckle': 5800, 'relief': .50, 'repeat': 28,
        'roughness': .98, 'metalness': .0,
        'where': 'the granitic fines and road base of a Front Range yard, '
                 'pale gold and raising dust in a dry month',
        'why': 'granite weathering in a dry climate leaves a compacted '
               'sandy fine that packs like paving and travels like dust, '
               'which is a low relief over a high speckle',
    },
    'limerock': {
        'name': 'Crushed limerock', 'base': '#5e5c50', 'grain': '242,238,220',
        'octaves': 4, 'speckle': 6200, 'relief': .60, 'repeat': 26,
        'roughness': .97, 'metalness': .0,
        'where': 'the crushed oolitic limestone a subtropical coast quarries '
                 'out from under itself and lays everything on',
        'why': 'South Florida builds on the rock it is standing on, and '
               'that rock is near-white: it is the brightest ground in the '
               'table, and under a high sun it is the reason for sunglasses',
    },
    'cinder': {
        'name': 'Cinder and clinker', 'base': '#22201e', 'grain': '188,174,152',
        'octaves': 5, 'speckle': 6400, 'relief': .68, 'repeat': 24,
        'roughness': .99, 'metalness': .02,
        'where': 'the black cinder and clinker fill a coal-era plant yard '
                 'was raised on and never took back up',
        'why': 'boiler ash went under the yard because it was free and it '
               'drained; a century later it is still what the ground is, '
               'dark and rust-flecked with what the shops dropped on it',
    },
    # ------------------------------------------------------ the verges ---
    # Two more, because the verge is the other half of what tells a yard
    # where it is: the same slab looks like a different country with
    # bunch grass around it than it does with moss.
    'prairie': {
        'name': 'Prairie grass', 'base': '#4a462c', 'grain': '208,192,126',
        'octaves': 5, 'speckle': 7600, 'relief': .60, 'repeat': 46,
        'roughness': .98, 'metalness': .0,
        'where': 'the unmown bunch grass of a plains or coastal-prairie '
                 'verge, gold more of the year than it is green',
        'why': 'prairie grass grows in clumps with bare ground between '
               'them and cures standing, so the base is straw and the '
               'grain is straw - a green verge would be the wrong country',
    },
    'moss': {
        'name': 'Moss and wet turf', 'base': '#243024', 'grain': '128,172,110',
        'octaves': 5, 'speckle': 6800, 'relief': .50, 'repeat': 38,
        'roughness': .94, 'metalness': .03,
        'where': 'the shaded rain-fed verge of a temperate-rainforest yard, '
                 'which takes the joints of the path as well',
        'why': 'in a place that is wet nine months of the year moss is the '
               'ground cover rather than a defect in it: deeper green than '
               'grass, softer relief, and never quite matte',
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
# Authored ambience, by reputation. The page's surface engine draws these
# patterns and the campus builder draws these rooflines; a fabric may name
# nothing else. Closed sets, so a typo cannot invent a facade the renderer
# would silently ignore.
FACADE_PATTERNS = ('panel', 'brick', 'block', 'smooth', 'plywood', 'board')
ROOFLINES = ('flat', 'gable', 'saw')
# The ambient bed is a closed set too, and for the same reason: the page
# builds wind, insects, gulls, a harbour horn and thunder, and SILENTLY
# IGNORES anything else. An `amb` key that is not on this list is a sound
# somebody meant to hear and nobody will.
AMB_BEDS = ('wind', 'gulls', 'harbor', 'insects', 'thunder')

# `fog.mul` scales both ends of the fog distance: SMALLER IS THICKER. It
# read the other way round to whoever wrote Denver, which came out at .4 -
# the thickest air on the network, on the campus whose own character line
# says "thin, dry high-altitude light". The check below holds the two ends
# of the range in place so the reading cannot invert again.

ATMOS = {
    'treasure-island': {
        'sky': ['#0b141d', '#22323e', '#48575f', '#5e646a'],
        'fog': {'color': 0x2b3a42, 'mul': .62}, 'banks': 6,
        'haze': '208,220,228',
        'sun': {'color': 0xd8e2e8, 'i': 1.15},
        'hemi': {'sky': 0x9fb4c0, 'ground': 0x24211c, 'i': 1.15},
        'amb': {'wind': .8, 'gulls': True, 'harbor': True},
        'ground': 'salt-slab', 'verge': 'upland',
        'ground_why': 'a former naval station on made ground: the yard is '
                      'the station\'s own apron, and a lifetime of salt air '
                      'has taken the face off it. The verge is the dry, '
                      'windswept fill nobody waters - an island lawn would '
                      'be somebody else\'s campus',
        'character': 'marine layer off the Pacific; cool, grey and bright '
                     'at once, and the thickest air on the network - '
                     'authored by reputation, not measured',
    },
    'oakland': {
        'sky': ['#0c141c', '#1a2a36', '#33404a', '#5a4426'],
        'fog': {'color': 0x1f2820, 'mul': .98}, 'banks': 1,
        'haze': '218,214,198',
        'sun': {'color': 0xffd9a0, 'i': 1.7},
        'hemi': {'sky': 0xaec2cb, 'ground': 0x241d16, 'i': 1.05},
        'amb': {'wind': .45, 'gulls': True, 'harbor': True},
        'ground': 'hardstand', 'verge': 'gravel',
        'ground_why': 'a working container terminal on the estuary: the '
                      'yard is crane-rated hardstand, patched in pieces '
                      'where the stackers turn, and the verge is the '
                      'gravel margin every truck parks half on',
        'character': 'the estuary side, warmer and harder-edged than the '
                     'island, with one thin bank off the water that is '
                     'gone by the time the yard is working - authored by '
                     'reputation, not measured',
    },
    'new-orleans': {
        'sky': ['#101318', '#26272e', '#4a4238', '#6e4c30'],
        'fog': {'color': 0x2e2b26, 'mul': .78}, 'banks': 2,
        'haze': '226,210,182',
        'sun': {'color': 0xffc98a, 'i': 1.45},
        'hemi': {'sky': 0xb8ac9c, 'ground': 0x2a2018, 'i': 1.1},
        'amb': {'wind': .3, 'insects': True, 'thunder': True},
        'ground': 'shell', 'verge': 'marsh',
        'ground_why': 'a delta with no rock in it fills its yards with '
                      'crushed shell, and this campus sits between the '
                      'river and the wet margin the egret is standing in - '
                      'so the verge is marsh, which is what the animal '
                      'record has always said the ground here was',
        'character': 'Gulf humidity and a low warm haze that does not lift '
                     'with the morning, and river fog off the water before '
                     'it - authored by reputation, not measured',
    },
    'houston': {
        'sky': ['#141210', '#2c2620', '#5c4e34', '#7a5a2e'],
        'fog': {'color': 0x33291c, 'mul': .9}, 'banks': 3,
        'haze': '224,200,158',
        'sun': {'color': 0xffcf8c, 'i': 1.35},
        'hemi': {'sky': 0xbfae8c, 'ground': 0x261f14, 'i': 1.0},
        'amb': {'wind': .2, 'insects': True, 'thunder': True},
        'ground': 'caliche', 'verge': 'prairie',
        'ground_why': 'a ship-channel plant yard standing on gumbo clay is '
                      'a caliche pad brought in above ground that moves '
                      'with every wet season, and what is left unpaved '
                      'goes back to Gulf coastal prairie rather than lawn',
        'character': 'Gulf-coast heat haze over a working ship channel '
                     'that never clears the way a sea breeze clears, and a '
                     'refinery glow at the sky\'s edge after dark - '
                     'authored by reputation, not measured',
    },
    'chicago': {
        'sky': ['#12161c', '#232c38', '#4a5866', '#7d8a92'],
        'fog': {'color': 0x28313a, 'mul': 1.02}, 'banks': 4,
        'haze': '206,216,224',
        'sun': {'color': 0xdfe8ee, 'i': 1.2},
        'hemi': {'sky': 0xa8b8c2, 'ground': 0x201e1c, 'i': 1.1},
        'amb': {'wind': .95, 'gulls': True, 'harbor': False},
        'ground': 'ballast', 'verge': 'prairie',
        'ground_why': 'a rail hub is laid on the same crushed stone as the '
                      'track running through it, sharp and loose and laid '
                      'to drain, and the verge is the tallgrass prairie '
                      'holding the embankment either side of it',
        'character': 'a flat lakefront wind that never really stops, cold '
                     'and grey off the water most of the year - authored '
                     'by reputation, not measured',
    },
    'seattle': {
        'sky': ['#10151a', '#232c31', '#495459', '#7c8a8c'],
        'fog': {'color': 0x2a3236, 'mul': .8}, 'banks': 6,
        'haze': '200,210,212',
        'sun': {'color': 0xd6e0e0, 'i': .95},
        'hemi': {'sky': 0x9aabac, 'ground': 0x22201c, 'i': 1.0},
        'amb': {'wind': .5, 'gulls': True, 'harbor': True},
        'ground': 'basalt', 'verge': 'moss',
        'ground_why': 'Cascade basalt is the aggregate at hand here, and '
                      'in a climate this wet the verge is not grass but '
                      'moss - in the shade of the yard, and then in the '
                      'joints of its paths',
        'character': 'a low marine overcast off the Sound that sits on the '
                     'cranes rather than above them, a working waterfront '
                     'and the hum of aerospace manufacturing just south of '
                     'the green - authored by reputation, not measured',
    },
    'pittsburgh': {
        'sky': ['#13161a', '#282c2e', '#4c4c49', '#6e6155'],
        'fog': {'color': 0x33302a, 'mul': .84}, 'banks': 4,
        'haze': '212,206,192',
        'sun': {'color': 0xd9d0bd, 'i': 1.05},
        'hemi': {'sky': 0x9a9c96, 'ground': 0x241f1a, 'i': 1.0},
        'amb': {'wind': .4, 'gulls': False, 'harbor': True},
        'ground': 'slag', 'verge': 'grass',
        'ground_why': 'a mill valley paved its own yards and roadbeds with '
                      'the slag its furnaces made, because it had it by '
                      'the trainload; the verge is the rough grass of the '
                      'hillside the shop is cut into',
        'character': 'a river haze that settles in the valley overnight '
                     'and burns off late, over three confluent rivers '
                     'crossed by more bridges than any other American '
                     'city, and a post-industrial skyline standing where '
                     'the mills once were - authored by reputation, not '
                     'measured',
    },
    'denver': {
        'sky': ['#0b1120', '#1c2e4a', '#3f5c88', '#e8a24a'],
        # The clearest air on the network, which is the point of the place:
        # see the note above the table about which way this number reads.
        'fog': {'color': 0x2a3446, 'mul': 1.6}, 'banks': 0,
        'haze': '222,226,236',
        'sun': {'color': 0xfff2d6, 'i': 1.6},
        'hemi': {'sky': 0x8fa8c4, 'ground': 0x2c2620, 'i': 1.15},
        'amb': {'wind': .55, 'gulls': False, 'harbor': False, 'thunder': True},
        'ground': 'decomposed-granite', 'verge': 'prairie',
        'ground_why': 'Front Range granite weathers to a fine that '
                      'compacts like paving and travels like dust, which '
                      'is what a high dry yard is surfaced with; the verge '
                      'is shortgrass, gold for most of the year, because '
                      'nothing else survives a mile up without water',
        'character': 'thin, dry high-altitude light off the Front Range '
                     'with a view that goes as far as the ground allows, '
                     'a mining and energy heritage at 5,280 feet, and the '
                     'Rockies standing on the western horizon - authored '
                     'by reputation, not measured',
    },
    'miami': {
        'sky': ['#0d1b26', '#1e3a44', '#3f8a92', '#f2c14e'],
        'fog': {'color': 0x2e3a3a, 'mul': 1.0}, 'banks': 1,
        'haze': '230,224,206',
        'sun': {'color': 0xffdf9e, 'i': 1.55},
        'hemi': {'sky': 0xb9d8d6, 'ground': 0x24221a, 'i': 1.05},
        'amb': {'wind': .4, 'insects': True, 'harbor': True, 'thunder': True},
        'ground': 'limerock', 'verge': 'grass',
        'ground_why': 'everything in South Florida is laid on the limerock '
                      'quarried out from under it, and it is near-white '
                      'under a high sun; the verge is the coarse turf that '
                      'survives salt, heat and a rainy season',
        'character': 'subtropical coastal heat and humidity off Biscayne '
                     'Bay, afternoon thunderheads stacking through '
                     'hurricane season, and a working seaport at the '
                     'harbor\'s edge - authored by reputation, not '
                     'measured',
    },
    'detroit': {
        'sky': ['#12161c', '#282e34', '#4e5458', '#7a6a4a'],
        'fog': {'color': 0x2c302e, 'mul': .95}, 'banks': 3,
        'haze': '210,208,198',
        'sun': {'color': 0xe6d4a8, 'i': 1.2},
        'hemi': {'sky': 0x9ba4a2, 'ground': 0x241f1a, 'i': 1.0},
        'amb': {'wind': .45, 'gulls': False, 'harbor': True},
        'ground': 'cinder', 'verge': 'gravel',
        'ground_why': 'a coal-era plant yard was raised on its own boiler '
                      'ash because the ash was free and it drained, and '
                      'nobody has ever taken it back up; the verge is the '
                      'gravel margin between the shops and the rail spur',
        'character': 'a Great Lakes river haze off the Detroit River, a '
                     'working industrial waterfront across from Windsor, '
                     'Ontario, and a century of automotive manufacturing '
                     'standing behind the skyline - authored by '
                     'reputation, not measured',
    },
}

# ------------------------------------------------- recipes laid elsewhere ---
# Every recipe has to be laid by somebody. Ten of them are a campus's own
# ground and six more are a campus verge; these are the rest, each with the
# consumer that lays it, so a recipe cannot sit in the table unused and
# unnoticed. A recipe that is BOTH a campus surface and listed here is a
# failure too - that means this list has gone stale, not that the recipe is
# doubly justified.
LAID_ELSEWHERE = {
    'asphalt': 'the page\'s own made land and the fallback carriageway',
    'concrete': 'the page\'s slabs, walkways and building aprons',
    'sand': 'the page\'s stockpiles and the excavator cut, and the sandy '
            'habitat of a restoration site',
    'water': 'the page\'s open water, at every campus that has any',
    'mudflat': 'a Bay Restoration site whose habitat line is tidal flat',
    'levee': 'a Bay Restoration site walked along its dike crown',
}

# Recipes reach the page only when web/ is rebuilt, and that build refuses a
# recipe until somebody has decided what it SOUNDS like underfoot - its step
# family. So a recipe may run ahead of the shipped page for exactly as long
# as it is named here and nowhere else: the check below still runs, recipe
# by recipe, over everything not on this list, and the list is checked from
# both ends. A name on it that is not a recipe fails, and so does a name on
# it that the page has meanwhile learned. It empties itself, which is the
# only kind of waiver worth having.
#
# It is empty, and it is meant to stay that way: the twelve recipes the ten
# yards were rebuilt on went through here and came off again the moment
# web/ gave each of them a step family. An empty waiver list that is still
# checked from both ends costs nothing and is the difference between a
# recipe that is on its way and a recipe that never arrived.
AWAITING_PAGE = set()

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
    'recipes': 'every ground recipe is AUTHORED, and authored the way the '
               'campus atmospheres and the built fabric are: composed from '
               'the character a place is known for - shell fill in a '
               'delta, slag in a mill valley, limerock on a subtropical '
               'coast - and never taken from a survey, a photograph or a '
               'scan of any real yard. What a place is built on is a '
               'reputation, and this record says so rather than implying '
               'someone went and looked.',
}

# ---------------------------------------------------------------- checks ---
campuses = json.load(open(ROOT / 'unions/registry/campuses.json'))['campuses']
assert set(ATMOS) == set(campuses), 'one atmosphere per campus, exactly'

# Every recipe is a complete recipe. The page reads all nine numbers off it
# and has no opinion of its own about any of them, so a missing one would
# be a surface that is generated wrong rather than a build that fails.
_HEX = re.compile(r'#[0-9a-f]{6}')
for gk, g in GROUND.items():
    assert _HEX.fullmatch(g['base']), f'{gk}: base is not a colour'
    _rgb = g['grain'].split(',')
    assert len(_rgb) == 3 and all(c.isdigit() and 0 <= int(c) <= 255
                                  for c in _rgb), f'{gk}: grain is not an rgb'
    assert 1 <= g['octaves'] <= 6, f'{gk}: octaves out of range'
    assert g['speckle'] > 0 and g['repeat'] > 0, f'{gk}: nothing to look at'
    assert 0 <= g['relief'] <= 1, f'{gk}: relief is a depth, not a multiplier'
    assert 0 < g['roughness'] <= 1 and 0 <= g['metalness'] <= 1, \
        f'{gk}: a physical material has physical numbers'
    assert len(g['where']) > 15, f'{gk}: a surface with no place'
    assert len(g['why']) > 25, f'{gk}: a surface with no reason is a colour'
# A recipe that is another recipe's base colour with a different name is the
# thing this table was rebuilt to stop: ten campuses recoloured once.
_bases = [g['base'] for g in GROUND.values()]
assert len(set(_bases)) == len(_bases), 'two recipes share a base colour'

# One campus, one ground, no two alike - the whole point of the exercise.
# The verges may repeat, because two cities can genuinely have the same
# margin; what may not repeat is the surface the yard itself is made of.
_grounds = [a['ground'] for a in ATMOS.values()]
assert len(set(_grounds)) == len(_grounds), \
    'two campuses stand on the same ground: that is the fault being fixed'

# Every recipe is laid by somebody, and the waiver list empties itself.
_campus_laid = set(_grounds) | {a['verge'] for a in ATMOS.values()}
assert not (_campus_laid & set(LAID_ELSEWHERE)), \
    'LAID_ELSEWHERE names a recipe a campus already lays: it is stale'
assert set(LAID_ELSEWHERE) <= set(GROUND), 'LAID_ELSEWHERE names a non-recipe'
assert set(GROUND) == _campus_laid | set(LAID_ELSEWHERE), \
    f'recipes nobody lays: {sorted(set(GROUND) - _campus_laid - set(LAID_ELSEWHERE))}'
assert all(len(v) > 20 for v in LAID_ELSEWHERE.values()), \
    'a recipe laid elsewhere has to say by whom'

for ck, a in ATMOS.items():
    assert a['ground'] in GROUND, f'{ck}: ground {a["ground"]} is not a recipe'
    assert a['verge'] in GROUND, f'{ck}: verge {a["verge"]} is not a recipe'
    assert len(a['ground_why']) > 60, \
        f'{ck}: a ground with no reason is a preference, not a place'
    _rgb = a['haze'].split(',')
    assert len(_rgb) == 3 and all(c.isdigit() and 0 <= int(c) <= 255
                                  for c in _rgb), f'{ck}: haze is not an rgb'
    assert set(a['amb']) <= set(AMB_BEDS), \
        f'{ck}: ambient bed {sorted(set(a["amb"]) - set(AMB_BEDS))} is a sound ' \
        'nobody will hear - the page builds only the beds it knows'
    assert .5 <= a['fog']['mul'] <= 2, f'{ck}: fog distance out of range'
    assert 0 <= a['banks'] <= 8, f'{ck}: implausible number of fog banks'
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

# A reason copied from the campus next door is not a reason. Ten grounds,
# ten arguments for them, and no two the same sentence.
_whys = [a['ground_why'] for a in ATMOS.values()]
assert len(set(_whys)) == len(_whys), 'two campuses give the same reason'
# The horizon band was one colour for the whole network. It has to be worth
# having declared per campus, which means most of them have to differ.
_hazes = {a['haze'] for a in ATMOS.values()}
assert len(_hazes) >= 8, 'the horizon is the same colour almost everywhere'

# Which way `fog.mul` reads: SMALLER IS THICKER. Denver shipped at .4 - the
# thickest air of the ten, on the high-desert campus - because the number
# reads backwards to anyone who has not been told. These two hold the ends
# of the range where the character lines say they belong.
assert ATMOS['denver']['fog']['mul'] == max(a['fog']['mul'] for a in ATMOS.values()), \
    'the high desert must be the clearest air on the network'
assert ATMOS['treasure-island']['fog']['mul'] == min(
    a['fog']['mul'] for a in ATMOS.values()), \
    'the Bay must be the thickest air on the network'

orders = sorted(w['order'] for w in WEATHER.values())
assert orders == list(range(len(WEATHER))), 'the weather cycle must be a cycle'
for wk, w in WEATHER.items():
    assert 0 <= w['rain'] <= 1 and 0 <= w['cloud'] <= 1, f'{wk}: out of range'
    assert 0 < w['sky_mul'] <= 2 and 0 < w['fog_tint'] <= 2, \
        f'{wk}: sky and fog multipliers must stay sane'
    assert w['blurb'] and w['glyph'] and w['name'], f'{wk}: unlabelled state'
    assert 0 <= w['wet'] <= 1, f'{wk}: ground wetness is a fraction'
    assert 0 <= w['bank_mul'] <= 3 and 0 <= w['bank_floor'] <= 8, \
        f'{wk}: fog banks out of range'
# Wetness is not rainfall: fog wets a yard without a drop falling, and a
# storm cannot leave the ground drier than a shower. Both orderings have to
# hold or the field is decoration.
assert WEATHER['clear']['wet'] == 0, 'a clear day leaves the yard dry'
assert WEATHER['storm']['wet'] == max(w['wet'] for w in WEATHER.values()), \
    'nothing wets a yard like a storm'
assert WEATHER['fog']['wet'] > WEATHER['overcast']['wet'], \
    'fog wets the ground and an overcast sky does not'
# A fog state that puts no fog in the air over a campus that keeps none was
# the bug: the floor is what fixes it, so it has to be a real floor.
assert WEATHER['fog']['bank_floor'] >= 3, \
    'fog weather must put fog in the air on a campus that keeps none'

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
    assert AWAITING_PAGE <= set(GROUND), \
        f'awaiting the page: {sorted(AWAITING_PAGE - set(GROUND))} is not a recipe'
    for gk in GROUND:
        if gk in AWAITING_PAGE:
            # The waiver is only a waiver while it is true. Once web/ has
            # been rebuilt with this recipe - and has given it a step
            # family - the name has to come off this list, or the list
            # starts hiding a recipe that never arrived.
            assert f'"{gk}"' not in page, \
                f'ground {gk} has reached the page: take it off AWAITING_PAGE'
            continue
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
    'ground_laid_elsewhere': LAID_ELSEWHERE,
    'ground_awaiting_page': sorted(AWAITING_PAGE),
    'fauna': FAUNA,
    'atmos': ATMOS,
    'fabric': FABRIC,
}

# The provenance vocabulary of this bundle is RECORDED, DERIVED, SCHEMATIC
# and AUTHORED. One word belongs to orbis/ and to nothing else, and a
# registry that is entirely arithmetic and reputation is exactly where it
# would be reached for by accident.
assert 'ai-synthes' not in json.dumps(doc).lower(), \
    'AI-SYNTHESIZED is orbis\'s word: this ground is AUTHORED'

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'world.json').write_text(json.dumps(doc, indent=1) + '\n')
print(f"world: {len(WEATHER)} weather states, {len(GROUND)} generated ground "
      f"surfaces ({len(set(_grounds))} of them a campus yard of its own, "
      f"{len(AWAITING_PAGE)} awaiting a step family in web/), "
      f"{len(FAUNA)} animals ({doc['counts']['animals']} placed "
      f"across {len(ATMOS)} campuses) (source stamp {stamp})")
