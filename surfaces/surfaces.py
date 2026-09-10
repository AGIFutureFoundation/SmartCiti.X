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
