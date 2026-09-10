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
