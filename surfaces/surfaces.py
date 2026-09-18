"""The surface catalogue and selection rules — spec §24, as code.

Twenty-two floor finishes, each carrying renderer-ready parameters (base
colour, roughness, metalness, a procedural pattern key, and the real-world
size of one tile in metres) AND the reason it is specified. A finish exists
because something requires it; none of these is a preference.

Selection runs most-specific-first (§24.1): the trade's hazard, then the
room's function, then nothing. A hazard is only recorded as hazard-driven
when it changed something — if the hazard's choice equals the function
default, the record says function, because that is what actually decided.

WHAT THESE ARE NOT (§24.3): general good practice, not a code reference.
No figure is read from any jurisdiction's standard, and no surface names a
product, brand, fire rating or specification number — the suite asserts
that absence rather than trusting it.
"""

# id: (name, base colour, roughness, metalness, pattern, tile_m, why)
SURFACES = {
    'bare-slab':        ('Power-floated bare slab', '#8e9294', .92, .02, 'slab', 3.0,
                         'non-combustible with nothing underfoot to carry flame or spark'),
    'sealed-slab':      ('Sealed concrete slab', '#9aa0a0', .75, .03, 'slab', 3.0,
                         'dust-proofed general working floor that survives point loads'),
    'broom-concrete':   ('Broom-finish concrete', '#94999a', .97, .02, 'broom', 3.0,
                         'traction outdoors and on wash-down ramps'),
    'epoxy-smooth':     ('Smooth epoxy resin', '#b8bfc2', .35, .05, 'smooth', 2.4,
                         'wipe-clean and chemical-resistant for controlled rooms'),
    'epoxy-quartz':     ('Quartz-broadcast epoxy', '#a8adad', .60, .04, 'speckle', 2.4,
                         'keeps grip when the process runs wet or oily'),
    'spill-berm':       ('Bermed epoxy with coved edge', '#aab4b0', .45, .04, 'smooth', 2.4,
                         'contains a spill at the room boundary until it is recovered'),
    'welded-vinyl':     ('Welded sheet vinyl', '#cfd4d6', .30, .02, 'smooth', 1.8,
                         'particulates collect in joints, so the floor has none'),
    'esd-vinyl':        ('Static-dissipative vinyl', '#a9b3b8', .40, .06, 'tile', .6,
                         'bleeds charge to ground before it can find a spark path'),
    'rubber-dielectric':('Dielectric rubber matting', '#2e3335', .90, .00, 'smooth', 1.0,
                         'insulates the person standing at live equipment'),
    'anti-fatigue':     ('Anti-fatigue matting', '#3c4245', .92, .00, 'smooth', 1.0,
                         'long standing bench work punishes joints on hard floor'),
    'firebrick-hearth': ('Firebrick hearth', '#7a4a3a', .95, .02, 'brick', .23,
                         'it will be spilled on, and must take molten metal'),
    'acid-brick':       ('Acid-resistant brick', '#8a5a4a', .80, .02, 'brick', .23,
                         'shrugs off the chemistry a plating or wash-down bay throws'),
    'steel-checker':    ('Checkerplate steel', '#6f7678', .45, .85, 'checker', .3,
                         'grip where machines drip oil, and it can be hosed'),
    'steel-grate':      ('Open steel grating', '#5f6668', .50, .80, 'grate', .3,
                         'the floor drains itself where water is the work'),
    'marine-deck':      ('Non-skid marine deck', '#55606a', .85, .30, 'speckle', 1.2,
                         'grip that survives immersion and salt'),
    'end-grain-block':  ('End-grain wood block', '#7d5f41', .85, .00, 'block', .1,
                         'kind to a dropped edge tool, and quiet underfoot'),
    'timber-plank':     ('Heavy timber planking', '#8a6a48', .90, .00, 'plank', .14,
                         'the substrate formwork and carpentry actually fasten into'),
    'raised-access':    ('Raised access floor', '#b4b9bb', .50, .15, 'tile', .6,
                         'the services run under the floor, not across it'),
    'terrazzo-ground':  ('Ground terrazzo', '#b9b3a8', .40, .03, 'speckle', 1.2,
                         'a finish trade shows its own craft where people gather'),
    'porcelain-tile':   ('Porcelain tile', '#c4c8c8', .35, .02, 'tile', .6,
                         'hard, flat and truthful under a straightedge'),
    'crushed-stone':    ('Compacted crushed stone', '#9d9689', .98, .00, 'speckle', 1.5,
                         'the ground plant actually digs, piles and tracks on'),
    'asphalt-apron':    ('Asphalt apron', '#3a3f42', .96, .02, 'speckle', 3.0,
                         'the yard running surface between door and stockpile'),
}

# Function defaults: what each room gets when the trade's hazard says nothing.
# Keyed by strand (each room owns one strand — the interiors pack's truth).
FUNCTION_DEFAULT = {
    'safety':          'epoxy-smooth',     # induction is already wipe-clean (§24.1)
    'procedure':       'sealed-slab',
    'machines':        'steel-checker',
    'tools':           'end-grain-block',
    'materials':       'sealed-slab',
    'layout':          'bare-slab',        # setting out wants dead-flat power float
    'inspection':      'epoxy-smooth',
    'troubleshooting': 'anti-fatigue',
    'coordination':    'terrazzo-ground',
    'documentation':   'raised-access',
    'leadership':      'porcelain-tile',
}

# Hazard vocabulary, drawn from the trades' own words (focus lines and
# names), most-specific-first within the list. Each hazard names the rooms
# it governs and the finish it demands there.
HAZARDS = [
    ('molten-metal',  ('molten', 'furnace', 'tapping', 'pour', 'foundry',
                       'smelter', 'refractory', 'dryout', 'heat treatment'),
        {'procedure': 'firebrick-hearth', 'machines': 'firebrick-hearth'}),
    ('hot-work',      ('weld', 'braz', 'smaw', 'gmaw', 'gtaw', 'fcaw',
                       'cutting', 'torch', 'spark'),
        {'procedure': 'bare-slab'}),
    ('corrosive',     ('electroplating', 'anodis', 'chlorin', 'acid',
                       'coating', 'decon', 'wash-down'),
        {'procedure': 'acid-brick'}),
    ('contaminant',   ('abatement', 'asbestos', 'lead', 'mould', 'moisture mapping',
                       'containment', 'hazmat', 'disposal', 'remediation'),
        {'procedure': 'spill-berm'}),
    ('particulate',   ('cleanroom', 'gowning', 'laminar', 'validation'),
        {'procedure': 'welded-vinyl', 'inspection': 'welded-vinyl'}),
    ('live-electrical',('live-line', 'energized', 'switching', 'relays',
                        'breakers', 'transformers', 'terminations', 'splices',
                        'low-voltage', 'code compliance'),
        {'procedure': 'rubber-dielectric', 'troubleshooting': 'rubber-dielectric'}),
    ('stored-energy', ('battery', 'bms', 'thermal runaway', 'electrolyser',
                       'hydrogen', 'purity'),
        {'procedure': 'esd-vinyl'}),
    ('immersion',     ('underwater', 'diving', 'lift bags', 'shipboard',
                       'sea valves', 'mooring', 'hull', 'launch', 'marine'),
        {'procedure': 'marine-deck'}),
    ('wet-process',   ('hydroblasting', 'chlorination', 'treatment trains',
                       'sludge', 'brine', 'hydrotest', 'wet removal'),
        {'procedure': 'steel-grate'}),
    ('mobile-plant',  ('earthmoving', 'excavation', 'piles', 'haul', 'earth',
                       'ballast', 'mowing', 'irrigation', 'drilling', 'blast'),
        {'procedure': 'crushed-stone', 'machines': 'broom-concrete'}),
    ('timber-trade',  ('framing', 'formwork', 'finish and layout', 'shoring',
                       'falsework'),
        {'procedure': 'timber-plank'}),
]


def hazard_of(name, focus):
    """The trade's governing hazard, from its own words — or None."""
    text = (name + ' ' + focus).lower()
    for key, words, rooms in HAZARDS:
        if any(w in text for w in words):
            return key, rooms
    return None, {}


# ------------------------------------------------------- conditions (§24.2) --
# Per room: maintained illuminance (lux), air changes per hour, the noise
# level the room is DESIGNED AROUND (dB), a temperature band (°C), and the
# PPE the work implies. The empty PPE list is the answer "none", stated
# explicitly — a briefing room genuinely requires none in ordinary use, and
# saying so is more useful than a blank a reader has to interpret.
#
# These are general good practice, not a code reference (§24.3): no figure
# is read from any jurisdiction's standard.
BASE_CONDITIONS = {
    #                 lux  ach  dB   temp°C      base PPE
    'safety':          (300,  6, 55, (18, 24), ('safety boots', 'hi-vis')),
    'procedure':       (500,  8, 80, (12, 30), ('hard hat', 'safety glasses',
                                                'safety boots', 'gloves', 'hi-vis')),
    'machines':        (500, 10, 85, (12, 28), ('hard hat', 'safety glasses',
                                                'safety boots', 'gloves', 'hi-vis',
                                                'hearing protection')),
    'tools':           (500,  4, 65, (16, 26), ('safety glasses', 'safety boots')),
    'materials':       (200,  4, 70, (5, 30),  ('hard hat', 'safety boots',
                                                'hi-vis', 'gloves')),
    'layout':          (750,  4, 60, (16, 26), ('safety boots',)),
    'inspection':      (1000, 6, 60, (18, 24), ('safety glasses',)),
    'troubleshooting': (750,  6, 70, (16, 26), ('safety glasses', 'safety boots')),
    'coordination':    (300,  4, 50, (19, 25), ()),
    'documentation':   (400,  4, 45, (19, 25), ()),
    'leadership':      (300,  4, 40, (19, 25), ()),
}

# What each hazard demands on top, in the rooms it governs. Where two
# hazards meet, the MORE DEMANDING value wins on every axis (§24.2): lux,
# air changes and design noise take the maximum, the temperature band
# narrows to the tightest demand, and PPE is the union — a second hazard
# can never cancel the first, and the suite asserts that property directly.
#                    lux   ach  dB   temp°C      added PPE
HAZARD_CONDITIONS = {
    'molten-metal':   (500, 20, 90, (10, 40), ('face shield', 'flame-resistant clothing')),
    'hot-work':       (500, 15, 85, (12, 35), ('welding hood', 'flame-resistant clothing')),
    'corrosive':      (500, 15, 80, (14, 28), ('chemical gloves', 'face shield', 'apron')),
    'contaminant':    (500, 12, 80, (14, 28), ('respirator', 'coveralls')),
    'particulate':    (750, 30, 60, (19, 23), ('coveralls', 'gowning')),
    'live-electrical':(750,  8, 70, (16, 26), ('dielectric gloves', 'arc-flash face shield')),
    'stored-energy':  (500, 12, 70, (15, 27), ('face shield',)),
    'immersion':      (500,  8, 75, (8, 32),  ('immersion suit',)),
    'wet-process':    (500, 10, 80, (10, 30), ('waterproof boots', 'face shield')),
    'mobile-plant':   (500,  8, 90, (5, 35),  ('hearing protection', 'hi-vis')),
    'timber-trade':   (500,  8, 85, (12, 30), ('hearing protection', 'dust mask')),
}
assert set(HAZARD_CONDITIONS) == {h[0] for h in HAZARDS}, \
    'every hazard class carries its condition demands'


def hazards_of(name, focus):
    """ALL the trade's matching hazards, in specificity order. Finishes take
    the first (most specific); conditions merge every one, more-demanding-
    wins, so a second hazard can never cancel the first."""
    text = (name + ' ' + focus).lower()
    out = []
    for key, words, rooms in HAZARDS:
        if any(w in text for w in words):
            out.append((key, rooms))
    return out


def merge_conditions(strand, hazard_keys):
    """The room's conditions after every governing hazard has had its say."""
    lux, ach, db, (tlo, thi), ppe = BASE_CONDITIONS[strand]
    ppe = set(ppe)
    for hz in hazard_keys:
        hlux, hach, hdb, (hlo, hhi), hppe = HAZARD_CONDITIONS[hz]
        lux = max(lux, hlux); ach = max(ach, hach); db = max(db, hdb)
        tlo = max(tlo, hlo); thi = min(thi, hhi)
        ppe |= set(hppe)
    assert tlo < thi, f'temperature band collapsed for {strand} + {hazard_keys}'
    return {'lux': lux, 'ach': ach, 'noise_db': db, 'temp_c': [tlo, thi],
            'ppe': sorted(ppe), 'hazards': sorted(hazard_keys)}


# ----------------------------------------------------------- walls (§24.4) --
# The floor catalogue above has twenty-two entries; the walls had none, so
# every room of every hall was drawn on the same flat slab colour. A wall
# is not decoration in a working building — it is what the work does to the
# room at shoulder height, and it differs by trade for the same reasons the
# floor does.
#
# Each entry carries renderer-ready parameters AND the reason it exists, on
# the same terms as SURFACES: general good practice, not a code reference
# (§24.3). No wall names a product, a brand, a fire rating or a
# specification number, and the suite asserts that absence rather than
# trusting it.
#
# `wainscot` is the band along the bottom of the wall — the height the work
# actually reaches — and `wainscot_m` is how far up it runs. A wall with no
# band declares wainscot_m 0.0 rather than omitting the field.
#
# id: (name, colour, roughness, metalness, pattern, tile_m,
#      wainscot colour, wainscot_m, why)
WALLS = {
    'painted-block':   ('Painted concrete block', '#8d9499', .88, .02, 'block', .40,
                        '#4a5b66', 1.20,
                        'the general working wall: takes a knock, takes a repaint'),
    'impact-block':    ('Impact-faced block with kerb', '#7f868b', .90, .02, 'block', .40,
                        '#5a4f3a', 1.40,
                        'stock and plant hit this wall, so the bottom of it is the '
                        'part that is built to be hit'),
    'liner-panel':     ('Washable liner panel', '#aeb7bb', .55, .12, 'panel', .90,
                        '#5f6a70', 1.00,
                        'a practice bay gets hosed out, and a lined wall sheds water '
                        'instead of soaking it'),
    'ply-lined':       ('Plywood-lined shop wall', '#9a7a4e', .85, .00, 'plywood', 1.20,
                        '#6d5334', 1.10,
                        'you hang tools, jigs and a cut list off a wall you can screw into'),
    'whiteboard-panel':('Full-height marker panel', '#d9dee0', .22, .04, 'board', 1.20,
                        '#7a848a', 0.95,
                        'setting out is drawn before it is built, and the wall is the '
                        'first place it gets drawn'),
    'matte-board':     ('Matte low-glare board', '#c4c9cb', .82, .02, 'board', 1.20,
                        '#79828a', 0.90,
                        'inspection reads surfaces at a raking angle, and a shiny wall '
                        'throws the light back into the work'),
    'acoustic-panel':  ('Fabric-faced acoustic panel', '#6e6a66', .95, .00, 'fabric', .60,
                        '#4a4744', 1.00,
                        'a room where people talk over each other is a room where the '
                        'decision gets made twice'),
    'firebrick-face':  ('Firebrick wall face', '#7a4a3a', .95, .02, 'brick', .23,
                        '#5d372b', 1.60,
                        'the wall beside a pour takes the same spatter the hearth does'),
    'weld-screen':     ('Non-combustible screened bay', '#5c6469', .92, .05, 'screen', .80,
                        '#3d454a', 1.80,
                        'the arc is not only the welder\'s problem: the bay walls stop '
                        'the flash reaching the next bay',),
    'chem-tile':       ('Glazed chemical-resistant tile', '#9fb0ae', .30, .03, 'tile', .30,
                        '#4f6a66', 1.50,
                        'what the floor shrugs off, the splash-back has to shrug off too'),
    'coved-white':     ('Coved cleanable wall', '#d5dadb', .35, .02, 'smooth', 1.50,
                        '#b3bcbe', 0.60,
                        'a square corner is somewhere particulate can sit, so the room '
                        'has no square corners'),
    'mesh-guard':      ('Guarded mesh partition', '#6a7276', .70, .55, 'mesh', .35,
                        '#454c50', 0.85,
                        'you have to see into a bay you are not allowed to walk into'),
}

# What each room's function asks of its walls when the trade's hazard says
# nothing. One per strand, exactly — the same contract FUNCTION_DEFAULT has.
WALL_DEFAULT = {
    'safety':          'painted-block',
    'procedure':       'liner-panel',
    'machines':        'impact-block',
    'tools':           'ply-lined',
    'materials':       'impact-block',
    'layout':          'whiteboard-panel',
    'inspection':      'matte-board',
    'troubleshooting': 'ply-lined',
    'coordination':    'acoustic-panel',
    'documentation':   'acoustic-panel',
    'leadership':      'acoustic-panel',
}

# What a hazard changes about a wall — and ONLY where it changes something.
# Several hazards on this list govern a floor without governing a wall
# (live-electrical and stored-energy are answered underfoot, by matting,
# not at shoulder height), so they are absent here rather than present with
# the function default copied in. An absent hazard is a statement: this
# hazard did not move the wall, and the record should not imply it did.
WALL_HAZARD = {
    'molten-metal':  {'procedure': 'firebrick-face', 'machines': 'firebrick-face'},
    'hot-work':      {'procedure': 'weld-screen'},
    'corrosive':     {'procedure': 'chem-tile'},
    'contaminant':   {'procedure': 'coved-white'},
    'particulate':   {'procedure': 'coved-white', 'inspection': 'coved-white'},
    'immersion':     {'procedure': 'chem-tile'},
    'wet-process':   {'procedure': 'chem-tile'},
    'mobile-plant':  {'procedure': 'mesh-guard', 'machines': 'mesh-guard'},
    'timber-trade':  {'procedure': 'ply-lined'},
}
assert set(WALL_DEFAULT) == set(FUNCTION_DEFAULT), 'a wall default per room, exactly'
assert set(WALL_HAZARD) <= {h[0] for h in HAZARDS}, \
    'a wall hazard override must name a hazard that exists'
assert all(w in WALLS for m in WALL_HAZARD.values() for w in m.values()), \
    'every hazard override names a wall in the catalogue'
assert all(w in WALLS for w in WALL_DEFAULT.values()), \
    'every function default names a wall in the catalogue'


def wall_of(strand, hazard_keys):
    """The room's wall after its governing hazards have had their say.

    Most-specific-first, exactly as §24.1 resolves a floor: the first
    governing hazard that names THIS strand decides. As with floors, a
    hazard is only recorded as the placer when it actually changed the
    answer — where the hazard's wall equals the function default, the
    function decided, and the record says so.
    """
    func = WALL_DEFAULT[strand]
    for hz in hazard_keys:
        want = WALL_HAZARD.get(hz, {}).get(strand)
        if want and want != func:
            return {'wall': want, 'placed_by': 'hazard', 'hazard': hz}
    return {'wall': func, 'placed_by': 'function'}
