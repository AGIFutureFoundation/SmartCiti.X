"""The surface catalogue and selection rules — spec §24, as code.

A floor and a wall catalogue, each entry carrying renderer-ready parameters
(base colour, roughness, metalness, a procedural pattern key, and the
real-world size of one tile in metres) AND the reason it is specified. A
finish exists because something requires it; none of these is a preference.

Selection runs most-specific-first (§24.1): the trade's hazard — what the
work can do to a person — then the trade's craft — what the work does to
the room every day of the year — then the room's function, then nothing.
A rule is only recorded as the placer when it changed something: if a
hazard's choice equals the function default, the record says function,
because that is what actually decided.

The craft tier is the newer of the three. The first two tiers left sixty-one
halls with no hazard a floor answers, and every one of those halls drew the
same eleven floors as every other — a fibre-splicing bench, a banker shop
and a signalling hut on one sealed slab. That was not a finding about those
trades, it was the table running out of vocabulary, exactly as §24.2
records happening to the hazard list. A craft is not a hazard and is never
promoted to one: it places surfaces, it never touches the conditions
record, because what a trade does all day is not a thing PPE answers.

WHAT THESE ARE NOT (§24.3): general good practice, not a code reference.
No figure is read from any jurisdiction's standard, and no surface names a
product, brand, fire rating or specification number — the suite asserts
that absence rather than trusting it.

ON COLOUR. The first catalogue was grey: two-thirds of its entries sat
within ten points of neutral, so a plating shop, a signal hut and a stone
banker shop all read as the same concrete box under the same light. Real
working floors are not neutral — a quartz broadcast is tan because the
quartz is tan, a decontamination coating is pale blue because it has to be
seen going on and coming off, machine guarding is yellow because it is
meant to be looked at. Every colour below is the colour the material
actually is, and the suite asserts that the palette as a whole has not
drifted back to grey.
"""

# --------------------------------------------------------------- patterns --
# Every pattern key a finish or a wall may name, and what the renderer draws
# for it. This is the one place the vocabulary is declared; the asserts at
# the foot of this module fail closed both ways, so a finish cannot name a
# pattern nobody draws and a pattern cannot sit here unused by anything.
PATTERNS = {
    'slab':      'one large pour with its construction joints at the edges',
    'tile':      'a square modular tile with a grouted joint on every side',
    'brick':     'a stretcher bond with a raked mortar course',
    'plank':     'parallel board joints running one way',
    'block':     'a coursed unit face, wider than it is tall',
    'checker':   'raised two-way bars, the classic plate tread',
    'grate':     'bearing bars with open slots between them',
    'broom':     'fine combed striations dragged across a green slab',
    'smooth':    'no joint at all: a poured film with nothing to catch',
    'speckle':   'loose aggregate scattered through the surface',
    'panel':     'a ribbed sheet with a seam where two sheets meet',
    'plywood':   'sheet edges with the long grain running with them',
    'board':     'a flat drawn-on face with a single joint line',
    'fabric':    'a fine two-way weave with no hard edges',
    'screen':    'a heavy frame with a light infill inside it',
    'mesh':      'woven wire you can see through, the wire catching the light',
    # --- added with the second catalogue ---
    'diamond':   'raised lozenges in offset rows, the tread of a vehicle deck',
    'plate':     'flat plate with a ground weld seam every sheet width',
    'terrazzo':  'chip suspended in matrix, divided by a strip on a grid',
    'flake':     'irregular colour flake broadcast into a wet resin film',
    'trench':    'a floor laid to falls with a slotted drain running the bay',
    'sand':      'rammed granular floor, raked and rolled rather than laid',
    'ballast':   'crossed sleepers bedded in angular stone',
    'perf':      'a modular tile drilled through on a close grid',
    'tslot':     'a machined grid of T-slots in a heavy cast face',
    'polish':    'saw-cut control joints in a ground face with the aggregate up',
    'ashlar':    'squared stone in regular courses with fine joints',
    'glazing':   'a glazed bay divided by its transoms and mullions',
    'corrugate': 'deep profiled sheet, the ribs running full height',
    'gunite':    'sprayed material, lumpy where the nozzle laid it',
    'sheet':     'taped polythene sheeting with a lap seam every sheet width',
    'cabinet':   'a row of cubicle doors with a handle and a vent on each',
}

# id: (name, base colour, roughness, metalness, pattern, tile_m, why)
SURFACES = {
    'bare-slab':        ('Power-floated bare slab', '#848d94', .92, .02, 'slab', 3.0,
                         'non-combustible with nothing underfoot to carry flame or spark'),
    'sealed-slab':      ('Sealed concrete slab', '#a09788', .75, .03, 'slab', 3.0,
                         'dust-proofed general working floor that survives point loads'),
    'broom-concrete':   ('Broom-finish concrete', '#8e9aa0', .97, .02, 'broom', 3.0,
                         'traction outdoors and on wash-down ramps'),
    'epoxy-smooth':     ('Smooth epoxy resin', '#b0bcc4', .35, .05, 'smooth', 2.4,
                         'wipe-clean and chemical-resistant for controlled rooms'),
    'epoxy-quartz':     ('Quartz-broadcast epoxy', '#b4a68c', .60, .04, 'speckle', 2.4,
                         'keeps grip when the process runs wet or oily'),
    'spill-berm':       ('Bermed epoxy with coved edge', '#a8b09a', .45, .04, 'smooth', 2.4,
                         'contains a spill at the room boundary until it is recovered'),
    'welded-vinyl':     ('Welded sheet vinyl', '#bcd2cc', .30, .02, 'smooth', 1.8,
                         'particulates collect in joints, so the floor has none'),
    'esd-vinyl':        ('Static-dissipative vinyl', '#8fa3b4', .40, .06, 'tile', .6,
                         'bleeds charge to ground before it can find a spark path'),
    'rubber-dielectric':('Dielectric rubber matting', '#2c333c', .90, .00, 'smooth', 1.0,
                         'insulates the person standing at live equipment'),
    'anti-fatigue':     ('Anti-fatigue matting', '#38434b', .92, .00, 'smooth', 1.0,
                         'long standing bench work punishes joints on hard floor'),
    'firebrick-hearth': ('Firebrick hearth', '#8a4a33', .95, .02, 'brick', .23,
                         'it will be spilled on, and must take molten metal'),
    'acid-brick':       ('Acid-resistant brick', '#8e4e3c', .80, .02, 'brick', .23,
                         'shrugs off the chemistry a plating or wash-down bay throws'),
    'steel-checker':    ('Checkerplate steel', '#68757e', .45, .85, 'checker', .3,
                         'grip where machines drip oil, and it can be hosed'),
    'steel-grate':      ('Open steel grating', '#5c6a74', .50, .80, 'grate', .3,
                         'the floor drains itself where water is the work'),
    'marine-deck':      ('Non-skid marine deck', '#4e6470', .85, .30, 'speckle', 1.2,
                         'grip that survives immersion and salt'),
    'end-grain-block':  ('End-grain wood block', '#8a6338', .85, .00, 'block', .1,
                         'kind to a dropped edge tool, and quiet underfoot'),
    'timber-plank':     ('Heavy timber planking', '#9a7344', .90, .00, 'plank', .14,
                         'the substrate formwork and carpentry actually fasten into'),
    'raised-access':    ('Raised access floor', '#a9b4bd', .50, .15, 'tile', .6,
                         'the services run under the floor, not across it'),
    'terrazzo-ground':  ('Ground terrazzo', '#c2b7a2', .40, .03, 'speckle', 1.2,
                         'a finish trade shows its own craft where people gather'),
    'porcelain-tile':   ('Porcelain tile', '#bfc9cf', .35, .02, 'tile', .6,
                         'hard, flat and truthful under a straightedge'),
    'crushed-stone':    ('Compacted crushed stone', '#a3987f', .98, .00, 'speckle', 1.5,
                         'the ground plant actually digs, piles and tracks on'),
    'asphalt-apron':    ('Asphalt apron', '#383d46', .96, .02, 'speckle', 3.0,
                         'the yard running surface between door and stockpile'),

    # ---------------------------------------------- the second catalogue --
    # Sixteen floors the first pass had no room for. Every one of them is a
    # floor a trade on this network actually stands on, and every one is
    # reached by a rule below — the asserts refuse a finish nothing places.
    'polished-slab':    ('Ground and polished slab', '#a89f8f', .18, .04, 'polish', 2.4,
                         'a concrete trade grinds its own floor back to the aggregate '
                         'to show what it put down'),
    'steel-diamond':    ('Diamond tread plate', '#707e86', .42, .88, 'diamond', .4,
                         'a raised lozenge holds a boot on a deck a machine leaks onto'),
    'steel-plate':      ('Sealed steel plate deck', '#59656f', .38, .90, 'plate', 1.2,
                         'a welded deck spreads a point load and can be cut and let back in'),
    'terrazzo-divider': ('Divider-strip terrazzo', '#b0bda3', .35, .05, 'terrazzo', 1.2,
                         'the strip is where the pour stops and the next one starts, '
                         'and setting it out is the whole of the craft'),
    'flake-resin':      ('Broadcast flake resin', '#9f9483', .55, .04, 'flake', 2.0,
                         'flake hides the drip and the scuff a coating bay makes daily'),
    'resin-screed':     ('Heavy-duty resin screed', '#5f7a63', .62, .03, 'smooth', 2.0,
                         'takes steam and cold water an hour apart without lifting'),
    'conductive-tile':  ('Conductive floor tile', '#46525c', .45, .10, 'tile', .6,
                         'charge has to reach earth faster than the atmosphere can '
                         'find a spark'),
    'trench-drain':     ('Floor to falls with trench drain', '#869399', .70, .06, 'trench', 2.4,
                         'the wash water leaves by a route somebody chose'),
    'foundry-sand':     ('Rammed moulding-sand floor', '#6b6250', .99, .00, 'sand', 1.6,
                         'the floor and the mould are the same material, and the pour '
                         'goes into both'),
    'rail-ballast':     ('Ballasted track bed', '#7d7268', .98, .02, 'ballast', 1.4,
                         'the track is only as true as the stone under it, so the '
                         'stone is the floor'),
    'interlock-paver':  ('Interlocking concrete paving', '#8d8279', .88, .02, 'brick', .45,
                         'a buried-service trade has to lift the surface and put it '
                         'back the same afternoon'),
    'access-perf':      ('Perforated access floor tile', '#b3bec6', .48, .18, 'perf', .6,
                         'the cold air arrives through the floor, and which tile is '
                         'open is a decision somebody logs'),
    'shotcrete-invert': ('Shotcrete invert', '#79838c', .96, .02, 'gunite', 2.0,
                         'the floor of a heading is sprayed the same hour the roof is'),
    'tooling-plate':    ('T-slotted cast-iron floor plate', '#525c66', .40, .80, 'tslot', .9,
                         'a workpiece is only square to what it is clamped to'),
    'strippable-coat':  ('Strippable decontamination coating', '#9fc0bd', .30, .02, 'smooth', 2.4,
                         'the contamination leaves with the coating instead of with '
                         'the person'),
    'impact-mat':       ('Impact-absorbing mat', '#3f4e63', .94, .00, 'smooth', 1.2,
                         'a fall-arrest demonstration ends on the floor, and this is '
                         'the floor it should end on'),

    # ------------------------------------------ the timber and trade catalogue --
    # The first two passes built a working building out of concrete, resin and
    # steel, which is most of what a shop floor is and almost none of what the
    # rest of a union hall is. A hall has a bench room, a stock rack, a meeting
    # room and a board room, and the trade that owns the hall puts its own
    # material down in them: a carpenters' board room is not porcelain tile.
    #
    # So this pass is timber by species, the coloured coatings a bay is
    # actually marked out in, the stone and fired clay the masonry trades lay,
    # and the light metals a magazine or a battery room needs. Every one of
    # them rides a pattern the renderer ALREADY paints (see the assert at the
    # foot of this module and the two checks in the suite that hold this
    # catalogue to the page's own footfall and relief tables), so a finish
    # added here costs a texture and never a material.

    # --- timber, by species. A species is not a shade of brown: oak, maple
    # and fir differ in how they are finished and how hard they wear, and the
    # roughness below is the finish each one is usually laid with.
    'oak-strip':        ('White oak strip floor', '#9b7440', .78, .00, 'plank', .12,
                         'the hardwood a joinery trade lays in its own meeting room, '
                         'because the room is the first thing it is judged on'),
    'ash-board':        ('Ash board floor', '#c3ab80', .82, .00, 'plank', .16,
                         'pale, straight-grained and cheap to lift when the cable '
                         'under the record room floor has to be got at'),
    'heart-pine-reclaimed': ('Reclaimed heart pine', '#8e4f27', .86, .00, 'plank', .18,
                         'lifted out of an old mill floor and laid again: the board '
                         'room of a trade that argues for reuse should be made of it'),
    'maple-strip':      ('Hard maple strip floor', '#cfa96a', .70, .00, 'plank', .10,
                         'the hardest of the common shop timbers, and the one a '
                         'bench room floor survives a dropped chisel on'),
    'douglas-fir-plank':('Douglas fir plank', '#b07c4b', .88, .00, 'plank', .20,
                         'the stock a framing trade racks, laid as the floor of the '
                         'room it is racked in'),
    'beech-block':      ('Beech end-grain block', '#c9a06a', .80, .00, 'block', .08,
                         'end grain takes a blade point-first and closes behind it, '
                         'which is why a cutting bench stands on it'),
    'teak-deck':        ('Laid teak deck', '#a06c3b', .80, .00, 'plank', .09,
                         'the deck a shipwright lays and caulks, and the one piece of '
                         'their work anybody outside the yard ever walks on'),
    'iroko-bench-deck': ('Iroko bench decking', '#7b5227', .84, .00, 'plank', .15,
                         'oily enough to sit in salt water and not move, which is the '
                         'whole reason a fitting-out bench is built of it'),
    'bamboo-strand':    ('Strand-woven bamboo', '#a97640', .72, .00, 'plank', .13,
                         'a floor-laying trade keeps a bay of the newest substrate it '
                         'is asked to lay over, and this is currently that'),
    'oak-end-block':    ('Oak end-grain block', '#8c5b2f', .86, .00, 'block', .09,
                         'a fitter kneels at a stripped machine for an hour, and oak '
                         'end grain is kinder to a knee than steel and harder than a mat'),
    'larch-decking':    ('Open larch decking', '#a98452', .92, .00, 'plank', .14,
                         'slatted and laid clear of the ground, so a store where '
                         'everything arrives wet drains instead of rotting'),
    'rail-timber-waybeam': ('Timber waybeam', '#6f5b45', .92, .00, 'plank', .30,
                         'the longitudinal timber a rail sits on where there is no '
                         'ballast to sit in, and the thing a signals hall racks'),

    # --- resilient sheet, tile and the coloured coatings a bay is marked in.
    # These are colour SHADES with a job: a floor coating is chosen for what
    # the shade tells somebody walking in, and the trade names the colour.
    'linoleum-sheet':   ('Welded linoleum sheet', '#6f8a5e', .55, .01, 'smooth', 2.0,
                         'linseed oil and cork dust on jute: warm underfoot, and it '
                         'takes a dropped instrument without chipping'),
    'rubber-sheet-safety': ('Welded rubber sheet', '#3d4a44', .88, .00, 'smooth', 1.6,
                         'a rescue drill puts people on the floor repeatedly, and '
                         'rubber sheet is what stops that becoming the injury'),
    'vct-tile':         ('Vinyl composition tile', '#cfc6b2', .45, .01, 'tile', .30,
                         'cheap, replaceable one tile at a time, and the reason a '
                         'record room floor can be repaired on a Friday afternoon'),
    'safety-vinyl-grit':('Grit-grip safety vinyl', '#6d8f96', .65, .02, 'speckle', 1.8,
                         'carborundum through the wear layer, for the floor between '
                         'a wet plant room and a dry corridor'),
    'esd-rubber':       ('Static-dissipative rubber', '#46505a', .86, .04, 'smooth', 1.4,
                         'bleeds a charge away slowly enough not to be a shock path '
                         'and fast enough not to let one build at a cell rack'),
    'epoxy-oxide-red':  ('Oxide-red epoxy coating', '#8f3f33', .38, .03, 'smooth', 2.4,
                         'red reads as the working bay in every yard that uses '
                         'colour at all, and a trainee learns the convention by walking it'),
    'epoxy-plant-green':('Plant-room green epoxy', '#3f6b4d', .36, .03, 'smooth', 2.4,
                         'green is the safe route through a plant room, and the floor '
                         'is where the route is drawn'),
    'epoxy-slate-blue': ('Slate-blue epoxy coating', '#3f5a72', .34, .03, 'smooth', 2.4,
                         'a cold blue under array work makes a dropped washer visible '
                         'instead of lost'),
    'urethane-aisle-yellow': ('Aisle-yellow urethane coat', '#c09a24', .40, .03, 'smooth', 1.2,
                         'the aisle is the drawing: a plant yard is set out in yellow '
                         'before it is set out on paper'),
    'mma-fast-cure':    ('Fast-cure acrylic coating', '#6f6272', .30, .03, 'smooth', 2.2,
                         'goes down and is walked on the same shift, which is the only '
                         'reason a room in use can be recoated at all'),
    'polyurea-deck':    ('Polyurea deck coating', '#55696d', .48, .04, 'smooth', 2.0,
                         'sprayed thick over a steel deck and flexible enough to stay '
                         'stuck to it while the deck works'),
    'flake-terracotta': ('Terracotta flake resin', '#a4603f', .58, .03, 'flake', 2.0,
                         'warm flake hides the overspray a coating bay makes every '
                         'day without hiding a spill'),
    'quartz-graphite':  ('Graphite quartz broadcast', '#4b5257', .62, .04, 'speckle', 2.4,
                         'dark and hard: a shot-loading bench wants grip and wants '
                         'nothing that sparks'),

    # --- stone, fired clay and ground toppings. The masonry trades lay these
    # for other people; a hall of theirs stands on them too.
    'quarry-tile':      ('Unglazed quarry tile', '#9c5133', .70, .02, 'brick', .20,
                         'fired through, so it wears to the same colour it started '
                         'and a chipped corner is not a pale scar'),
    'porcelain-charcoal': ('Charcoal porcelain tile', '#4c545a', .32, .02, 'tile', .60,
                         'a dark, flat floor is the fairest ground to judge a light '
                         'finish sample against'),
    'porcelain-sand':   ('Sand porcelain tile', '#c4b49a', .34, .02, 'tile', .60,
                         'warm and low-contrast, so a glazing trade reads the light '
                         'coming through a bay rather than the floor bouncing it'),
    'slate-flag':       ('Riven slate flag', '#4f5a5e', .80, .02, 'tile', .50,
                         'split rather than sawn, so no two flags are the same '
                         'thickness and bedding them is the skill'),
    'limestone-flag':   ('Limestone flag', '#c0b89e', .76, .02, 'tile', .60,
                         'the stone the banker shop cuts, laid whole where the hall '
                         'wants to show what it cuts'),
    'granite-sett':     ('Granite sett paving', '#6e7378', .90, .02, 'brick', .12,
                         'small, square and laid to a cambered fall: the paving a '
                         'crew still sets by eye and a string line'),
    'clay-paver':       ('Clay paver floor', '#a45a3d', .86, .02, 'brick', .22,
                         'lifted, stacked and relaid the same afternoon, which is '
                         'the whole argument for a paved surface over a poured one'),
    'terrazzo-marble':  ('Marble-chip terrazzo', '#d4cbb8', .38, .03, 'terrazzo', 1.2,
                         'the chip is the finish: what is ground back decides the '
                         'floor, and choosing it is the trade'),
    'terrazzo-glass':   ('Recycled-glass terrazzo', '#7fa39a', .36, .04, 'terrazzo', 1.2,
                         'crushed glass in the matrix instead of stone, which grinds '
                         'differently and is the argument a sample bay exists to settle'),
    'granolithic-screed': ('Granolithic screed', '#97907f', .84, .02, 'polish', 2.0,
                         'a wearing topping laid monolithic with the slab under it, '
                         'and the thing a stock bay actually needs'),
    'polished-black':   ('Black-pigmented polished slab', '#33383c', .16, .04, 'polish', 2.4,
                         'pigment through the pour and ground back: the finish a '
                         'concrete trade puts in its own board room to end the argument'),

    # --- the light metals. Aluminium is not steel: it is softer, lighter and
    # it does not throw a spark, which is the only reason some of these rooms
    # are floored in it at all.
    'alu-tread':        ('Aluminium tread plate', '#b6bcc0', .40, .70, 'diamond', .40,
                         'a magazine tool store wants a floor that cannot strike a '
                         'spark off a dropped steel tool'),
    'galv-checker':     ('Galvanised checkerplate', '#8c979c', .48, .78, 'checker', .30,
                         'the zinc is why it can stand under a weld bay that gets '
                         'hosed out and still be there in ten years'),
    'stainless-deck':   ('Stainless plate deck', '#9aa4ab', .30, .82, 'plate', 1.2,
                         'wiped down every shift and never rusts into the wipe, which '
                         'is what a controlled room means by cleanable'),
    'alu-bar-grating':  ('Aluminium bar grating', '#a2aeb4', .45, .65, 'grate', .30,
                         'light enough that one person lifts a panel to get at the '
                         'pipework the grating is there to cover'),
    'perf-alu-tile':    ('Perforated aluminium tile', '#b0bec4', .42, .60, 'perf', .60,
                         'open area, in a floor whose whole job is to hand cold air '
                         'upward where somebody decided it should go'),

    # --- the remaining working floors, each one a thing a trade lays or stands on.
    'slot-drain-resin': ('Resin floor to falls with slot drain', '#7a8f86', .55, .04, 'trench', 2.4,
                         'a wash bay is a floor with a decision in it: where the '
                         'water goes, and how fast'),
    'sprayed-fibrecrete': ('Sprayed fibre-reinforced concrete', '#8b8375', .95, .02, 'gunite', 2.0,
                         'fibre instead of mesh, so the invert of a heading can be '
                         'sprayed in one pass behind the face'),
    'dry-shake-topping':('Metallic dry-shake topping', '#6b6f66', .70, .12, 'slab', 3.0,
                         'iron aggregate floated into the green slab: the hardest '
                         'wearing surface a demolition yard can put under tracked plant'),
    'anhydrite-screed': ('Anhydrite flowing screed', '#b9ae98', .80, .02, 'slab', 3.0,
                         'poured level by its own weight, which is why a long shop '
                         'floor can be flat without anyone tamping it'),
    'blast-grit-bed':   ('Blast-grit floor', '#55504a', .97, .03, 'sand', 1.6,
                         'the spent grit IS the floor of a blast bay until it is '
                         'swept and screened, and it is walked on in that state'),
}

# Function defaults: what each room gets when neither the trade's hazard nor
# its craft says anything. Keyed by strand (each room owns one strand — the
# interiors pack's truth).
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
#
# Eighteen classes. The first eleven were what the first pass could read;
# the seven marked below are the ones §24.2 already said were missing, and
# they are read out of the same focus lines the original eleven came from.
#
# Two of the original word lists have been narrowed, because they were
# matching on a word rather than on a meaning. 'pour' put a firebrick
# hearth under the terrazzo hall, whose focus line says "pours"; 'tapping'
# put one under the water-distribution hall, which taps mains. 'blast' gave
# the window-glazing hall a mobile-plant floor because it fits blast
# glazing. Those halls are now read correctly, and the smelter, the foundry
# and the blasters still match on words that can only mean what they mean.
HAZARDS = [
    ('molten-metal',  ('molten', 'furnace', 'foundry',
                       'smelter', 'refractory', 'dryout', 'heat treatment'),
        {'procedure': 'firebrick-hearth', 'machines': 'firebrick-hearth',
         'materials': 'foundry-sand'}),
    ('ionising-radiation', ('rad-controlled', 'alara', 'ionis', 'radiograph'),
        {'procedure': 'strippable-coat', 'inspection': 'strippable-coat'}),
    ('explosives',    ('shot design', 'initiation', 'detonat', 'explosive',
                       'magazine'),
        {'procedure': 'conductive-tile', 'materials': 'conductive-tile'}),
    ('hot-work',      ('weld', 'braz', 'smaw', 'gmaw', 'gtaw', 'fcaw',
                       'cutting', 'torch', 'spark'),
        {'procedure': 'bare-slab'}),
    ('corrosive',     ('electroplating', 'anodis', 'chlorin', 'acid',
                       'coating', 'decon', 'wash-down'),
        {'procedure': 'acid-brick'}),
    ('confined-space',('atmospheric testing', 'retrieval', 'tank entry',
                       'confined', 'vessel entry'),
        {'procedure': 'steel-plate', 'machines': 'steel-plate'}),
    ('contaminant',   ('abatement', 'asbestos', 'lead', 'mould', 'moisture mapping',
                       'containment', 'hazmat', 'disposal', 'remediation'),
        {'procedure': 'spill-berm'}),
    ('particulate',   ('cleanroom', 'gowning', 'laminar', 'validation'),
        {'procedure': 'welded-vinyl', 'inspection': 'welded-vinyl'}),
    ('flammable-atmosphere', ('purging', 'leak survey', 'leak detection',
                              'flammable'),
        {'procedure': 'conductive-tile'}),
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
        {'procedure': 'steel-grate', 'machines': 'trench-drain'}),
    ('work-at-height',('rope systems', 'edge management', 'steep-slope',
                       'climb rescue', 'suspended access', 'fall arrest',
                       'high-angle', 'work at height'),
        {'procedure': 'impact-mat', 'safety': 'impact-mat'}),
    ('mobile-plant',  ('earthmoving', 'excavation', 'piles', 'haul', 'earth',
                       'ballast', 'mowing', 'irrigation', 'drilling'),
        {'procedure': 'crushed-stone', 'machines': 'broom-concrete',
         'materials': 'asphalt-apron'}),
    ('suspended-load',('rigging', 'lifting', 'hoist', 'crane', 'spreader',
                       'load calculation', 'traction'),
        {'materials': 'steel-plate'}),
    ('rotating-machinery', ('precision alignment', 'machinery install',
                            'turbine', 'nacelle', 'drivetrain', 'gearbox',
                            'propulsion', 'rotating machinery'),
        {'procedure': 'epoxy-quartz', 'machines': 'steel-diamond'}),
    ('timber-trade',  ('framing', 'formwork', 'finish and layout', 'shoring',
                       'falsework'),
        {'procedure': 'timber-plank'}),
]

HAZARD_KEYS = tuple(h[0] for h in HAZARDS)
assert len(set(HAZARD_KEYS)) == len(HAZARD_KEYS), 'a hazard class names itself once'


def hazard_of(name, focus):
    """The trade's governing hazard, from its own words — or None."""
    text = (name + ' ' + focus).lower()
    for key, words, rooms in HAZARDS:
        if any(w in text for w in words):
            return key, rooms
    return None, {}


# ------------------------------------------------------------ craft (§24.1) --
# What the trade does every working day, read out of the same focus lines
# the hazards are. A craft is NOT a hazard and never becomes one: it places
# a floor and a wall, and it is deliberately absent from the conditions
# record below, because lighting, air changes and PPE answer what the work
# can do to a person and nothing here can do anything to anybody.
#
# A craft is less specific than a hazard and more specific than a room's
# function, so it resolves between them. Where a hazard has already named a
# strand the craft does not get a say at all — even when the hazard picked
# the function default on purpose (§24.1's case), because a rule that
# deliberately confirmed a default has decided, and a craft overruling that
# would be the record claiming the wrong reason again.
#
# Each entry names only the strands it CHANGES; a craft that named a room
# and chose that room's function default would be a craft taking credit for
# a decision the function had already made, and the assert below refuses it.
CRAFTS = [
    ('clean-process', ('classification, gowning', 'laminar', 'validation',
                       'zone valves'),
        {'machines': 'welded-vinyl', 'materials': 'welded-vinyl',
         'inspection': 'stainless-deck', 'documentation': 'vct-tile'}),
    ('hot-shop', ('castables', 'gunning', 'pot lines', 'moulding',
                  'shakeout', 'furnace lining'),
        {'tools': 'steel-plate', 'troubleshooting': 'steel-diamond',
         'layout': 'dry-shake-topping', 'leadership': 'granolithic-screed'}),
    ('containment-craft', ('negative air', 'hepa', 'enclosures',
                           'waste characterisation', 'moisture mapping',
                           'incident command', 'permits, jhas',
                           'monitoring and disposal', 'rad-controlled'),
        {'materials': 'spill-berm', 'tools': 'welded-vinyl',
         'inspection': 'mma-fast-cure', 'coordination': 'linoleum-sheet'}),
    ('precision-metal', ('turning, milling', 'cnc', 'metrology',
                         'jig and fixture', 'die build', 'tryout',
                         'precision alignment', 'machinery install'),
        {'inspection': 'tooling-plate', 'layout': 'tooling-plate',
         'machines': 'steel-diamond', 'troubleshooting': 'beech-block',
         'documentation': 'vct-tile'}),
    ('structural-steel', ('structural steel', 'rebar', 'plumbing up',
                          'bolting', 'connection safety', 'shear studs',
                          'weld-out', 'pressure vessel', 'detailing'),
        {'materials': 'steel-plate', 'layout': 'tooling-plate',
         'troubleshooting': 'oak-end-block', 'machines': 'dry-shake-topping'}),
    ('masonry-stone', ('masonry', 'banker work', 'lettering', 'tracery',
                       'repointing', 'dutchman', 'three-coat', 'veneer',
                       'ornamental', 'consolidation'),
        {'procedure': 'broom-concrete', 'materials': 'crushed-stone',
         'tools': 'quarry-tile', 'coordination': 'slate-flag',
         'leadership': 'limestone-flag'}),
    ('finish-trade', ('terrazzo', 'divider strips', 'resilient', 'carpet',
                      'large format', 'substrates',
                      'level of finish', 'texture'),
        {'procedure': 'terrazzo-divider', 'inspection': 'polished-slab',
         'coordination': 'bamboo-strand', 'documentation': 'terrazzo-marble',
         'materials': 'terrazzo-glass', 'leadership': 'porcelain-charcoal'}),
    ('concrete-craft', ('placement, finishing', 'curing', 'decorative concrete',
                        'boom setup', 'cleanout', 'tendon', 'stressing',
                        'elongation', 'grouting and tolerance'),
        {'procedure': 'polished-slab', 'machines': 'broom-concrete',
         'materials': 'granolithic-screed', 'leadership': 'polished-black'}),
    ('glass-envelope', ('curtain wall', 'storefront', 'glazing', 'sealants',
                        'unitised', 'water test', 'structural silicone',
                        'heritage sash'),
        {'procedure': 'polished-slab', 'materials': 'timber-plank',
         'coordination': 'porcelain-sand'}),
    ('sheet-membrane', ('duct fabrication', 'architectural metal',
                        'cavity drainage', 'low-slope', 'membranes',
                        'substructure, panels', 'mechanical insulation',
                        'metal stud', 'ceiling grid', 'mass-loaded',
                        'penetrations'),
        {'machines': 'steel-plate', 'materials': 'steel-diamond',
         'procedure': 'anhydrite-screed'}),
    ('coatings', ('coatings, containment', 'decorative finish', 'surface prep',
                  'electroplating', 'anodis', 'booming, recovery',
                  'hydroblasting', 'vacuum trucks'),
        {'machines': 'flake-resin', 'inspection': 'flake-resin',
         'materials': 'flake-terracotta', 'tools': 'blast-grit-bed'}),
    ('rail-craft', ('ballast, ties', 'rail laying', 'interlocking',
                    'track circuit', 'contact wire', 'tensioning', 'crossings'),
        {'procedure': 'rail-ballast', 'machines': 'rail-ballast',
         'materials': 'rail-timber-waybeam'}),
    ('underground', ('ground support, ventilation', 'ventilation, haulage',
                     'needle beam',
                     'jacking', 'monitoring and sequencing', 'refusal',
                     'sheet piles'),
        {'safety': 'shotcrete-invert', 'tools': 'shotcrete-invert',
         'machines': 'sprayed-fibrecrete'}),
    ('marine-craft', ('hull section', 'sea valves', 'loading arms', 'mooring',
                      'floating roof', 'shipboard'),
        {'machines': 'steel-plate', 'materials': 'marine-deck',
         'tools': 'iroko-bench-deck', 'inspection': 'polyurea-deck',
         'leadership': 'teak-deck'}),
    ('lifting-gear', ('load calculation', 'rigging hardware', 'spreaders',
                      'wire rope', 'traction and hydraulic', 'hoistway',
                      'tower and overhead'),
        {'tools': 'steel-plate', 'machines': 'steel-diamond',
         'troubleshooting': 'alu-tread'}),
    ('vehicle-shop', ('aftertreatment', 'propulsion, brakes',
                      'hydraulics, drivetrain', 'inspection cycles'),
        {'machines': 'trench-drain', 'materials': 'steel-diamond',
         'procedure': 'slot-drain-resin', 'tools': 'epoxy-oxide-red'}),
    ('hard-standing', ('pavement', 'markings', 'airside', 'ramp safety',
                       'de-icing', 'turnaround', 'gse'),
        {'procedure': 'asphalt-apron', 'machines': 'interlock-paver',
         'materials': 'clay-paver', 'layout': 'granite-sett'}),
    ('digital-systems', ('ddc', 'bacnet', 'scada', 'historian', 'otdr',
                         'white space', 'busway', 'crac', 'teach pendant',
                         'ladder logic', 'loop checks', 'access control',
                         'cctv', 'notification circuits', 'copper and fibre'),
        {'procedure': 'access-perf', 'machines': 'esd-vinyl',
         'troubleshooting': 'esd-vinyl', 'materials': 'perf-alu-tile'}),
    ('power-network', ('distribution, transmission', 'relays, breakers',
                       'terminations', 'ehv', 'conductor stringing',
                       'metering', 'revenue accuracy', 'dcfc',
                       'service upgrades', 'code compliance', 'pv array',
                       'racking, inverters'),
        {'machines': 'crushed-stone', 'materials': 'crushed-stone',
         'procedure': 'epoxy-slate-blue'}),
    ('process-fluid', ('process piping', 'hydronic', 'medical gas',
                       'refrigeration', 'air systems', 'treatment trains',
                       'steam and chilled', 'penstock', 'hangers, heads',
                       'mains, valves', 'sludge', 'blowers', 'wellhead',
                       'binary cycle', 'compression'),
        {'procedure': 'trench-drain', 'machines': 'resin-screed',
         'safety': 'safety-vinyl-grit', 'materials': 'epoxy-plant-green',
         'tools': 'alu-bar-grating'}),
    ('buried-utility', ('mains, services', 'integrity digs', 'tie-ins',
                        'leak survey', 'hydrants', 'mainline welding'),
        {'materials': 'interlock-paver', 'layout': 'interlock-paver',
         'tools': 'clay-paver'}),
    ('survey-control', ('control networks', 'gnss', 'as-builts',
                        'photogrammetry', 'airspace', 'flight planning',
                        'ndt', 'fracture-critical'),
        {'inspection': 'polished-slab', 'machines': 'sealed-slab',
         'documentation': 'linoleum-sheet'}),

    # ------------------------------------------- the crafts the first pass missed --
    # Every hall the first two passes left with no craft at all does
    # something all day that a floor and a wall answer; the registry's
    # `no_craft` list is what says which halls those were, and it is empty
    # now because of the entries below. These are read out of
    # the same focus lines as the crafts above, on the same terms: a craft is
    # what the trade DOES, never what the work can do to the person, so none
    # of them appears in the conditions record.
    ('timber-craft', ('framing, formwork', 'finish and layout',
                      'system scaffold'),
        {'coordination': 'oak-strip', 'documentation': 'ash-board',
         'leadership': 'heart-pine-reclaimed', 'tools': 'maple-strip',
         'materials': 'douglas-fir-plank'}),
    ('rope-access', ('rope systems', 'climb rescue', 'suspended access',
                     'edge management'),
        {'tools': 'alu-tread', 'documentation': 'vct-tile'}),
    ('earthmoving-craft', ('earthmoving', 'site prep', 'haul, delivery',
                           'mowing, trimming'),
        {'layout': 'urethane-aisle-yellow', 'tools': 'larch-decking'}),
    ('demolition-craft', ('selective demo', 'structural takedown',
                          'debris control'),
        {'materials': 'dry-shake-topping', 'machines': 'galv-checker',
         'coordination': 'anhydrite-screed'}),
    ('weld-shop', ('smaw', 'gmaw', 'gtaw', 'fcaw',
                   'procedure and qualification', 'underwater cutting'),
        {'machines': 'galv-checker', 'materials': 'anhydrite-screed'}),
    ('blast-craft', ('shot design', 'vibration control', 'loading, initiation'),
        {'machines': 'quartz-graphite', 'tools': 'alu-tread'}),
    ('battery-craft', ('racks, bms', 'thermal runaway'),
        {'machines': 'esd-rubber', 'materials': 'vct-tile'}),
    ('rescue-craft', ('atmospheric testing', 'patient packaging'),
        {'safety': 'rubber-sheet-safety', 'materials': 'polyurea-deck'}),
]

CRAFT_KEYS = tuple(c[0] for c in CRAFTS)
assert len(set(CRAFT_KEYS)) == len(CRAFT_KEYS), 'a craft names itself once'
assert not set(CRAFT_KEYS) & set(HAZARD_KEYS), \
    'a craft and a hazard must not share a name — the record says which tier placed a ' \
    'surface, and two tiers answering to one name makes that record unreadable'


def crafts_of(name, focus):
    """ALL the trade's matching crafts, in specificity order. The first that
    names a strand places it; the rest are recorded because they are true."""
    text = (name + ' ' + focus).lower()
    return [(key, rooms) for key, words, rooms in CRAFTS
            if any(w in text for w in words)]


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


def finish_of(strand, hazard_key, hazard_rooms, craft_keys):
    """The room's floor after hazard, craft and function have had their say.

    The rule lives here and only here — the builder reads it rather than
    restating it, so the wall and the floor cannot drift into resolving
    their tiers differently.
    """
    func = FUNCTION_DEFAULT[strand]
    want = hazard_rooms.get(strand)
    if want is not None:
        if want != func:
            return {'surface': want, 'placed_by': 'hazard', 'hazard': hazard_key}
        # the hazard named this room and chose exactly what the function
        # would have (§24.1); the function decided, and no later tier may
        # overturn a default a hazard deliberately confirmed
        return {'surface': func, 'placed_by': 'function'}
    for ck in craft_keys:
        cwant = CRAFT_ROOMS[ck].get(strand)
        if cwant and cwant != func:
            return {'surface': cwant, 'placed_by': 'craft', 'craft': ck}
    return {'surface': func, 'placed_by': 'function'}


def hazard_rooms_of(key):
    """The rooms one hazard governs, by key. Fails closed on an unknown key
    rather than handing back an empty mapping, which would silently read as
    'this hazard governs nothing'."""
    assert key in HAZARD_ROOMS, f'{key} is not a hazard class'
    return HAZARD_ROOMS[key]


HAZARD_ROOMS = {k: rooms for k, _, rooms in HAZARDS}
CRAFT_ROOMS = {k: rooms for k, _, rooms in CRAFTS}


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
    'ionising-radiation': (500, 15, 70, (16, 28), ('dosimeter', 'coveralls',
                                                   'respirator')),
    'explosives':     (500, 12, 90, (8, 32),  ('anti-static clothing',
                                               'hearing protection')),
    'hot-work':       (500, 15, 85, (12, 35), ('welding hood', 'flame-resistant clothing')),
    'corrosive':      (500, 15, 80, (14, 28), ('chemical gloves', 'face shield', 'apron')),
    'confined-space': (500, 20, 80, (10, 32), ('gas monitor', 'rescue harness')),
    'contaminant':    (500, 12, 80, (14, 28), ('respirator', 'coveralls')),
    'particulate':    (750, 30, 60, (19, 23), ('coveralls', 'gowning')),
    'flammable-atmosphere': (500, 20, 75, (8, 32), ('anti-static clothing',
                                                    'gas monitor')),
    'live-electrical':(750,  8, 70, (16, 26), ('dielectric gloves', 'arc-flash face shield')),
    'stored-energy':  (500, 12, 70, (15, 27), ('face shield',)),
    'immersion':      (500,  8, 75, (8, 32),  ('immersion suit',)),
    'wet-process':    (500, 10, 80, (10, 30), ('waterproof boots', 'face shield')),
    'work-at-height': (500,  6, 70, (8, 32),  ('full-body harness',
                                               'chinstrap helmet')),
    'mobile-plant':   (500,  8, 90, (5, 35),  ('hearing protection', 'hi-vis')),
    'suspended-load': (500,  8, 85, (5, 35),  ('hard hat', 'hi-vis')),
    'rotating-machinery': (500, 10, 88, (10, 30), ('hearing protection',
                                                   'close-fitting clothing')),
    'timber-trade':   (500,  8, 85, (12, 30), ('hearing protection', 'dust mask')),
}
assert set(HAZARD_CONDITIONS) == set(HAZARD_KEYS), \
    'every hazard class carries its condition demands'


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
# The floor catalogue had twenty-two entries; the walls had none, so every
# room of every hall was drawn on the same flat slab colour. A wall is not
# decoration in a working building — it is what the work does to the room at
# shoulder height, and it differs by trade for the same reasons the floor
# does.
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
    'painted-block':   ('Painted concrete block', '#8b969e', .88, .02, 'block', .40,
                        '#3f5763', 1.20,
                        'the general working wall: takes a knock, takes a repaint'),
    'impact-block':    ('Impact-faced block with kerb', '#948877', .90, .02, 'block', .40,
                        '#584a2f', 1.40,
                        'stock and plant hit this wall, so the bottom of it is the '
                        'part that is built to be hit'),
    'liner-panel':     ('Washable liner panel', '#b2c2ba', .55, .12, 'panel', .90,
                        '#546a66', 1.00,
                        'a practice bay gets hosed out, and a lined wall sheds water '
                        'instead of soaking it'),
    'ply-lined':       ('Plywood-lined shop wall', '#a8834f', .85, .00, 'plywood', 1.20,
                        '#6d4e2b', 1.10,
                        'you hang tools, jigs and a cut list off a wall you can screw into'),
    'whiteboard-panel':('Full-height marker panel', '#dce4e8', .22, .04, 'board', 1.20,
                        '#6f818e', 0.95,
                        'setting out is drawn before it is built, and the wall is the '
                        'first place it gets drawn'),
    'matte-board':     ('Matte low-glare board', '#c8c6bd', .82, .02, 'board', 1.20,
                        '#7b7768', 0.90,
                        'inspection reads surfaces at a raking angle, and a shiny wall '
                        'throws the light back into the work'),
    'acoustic-panel':  ('Fabric-faced acoustic panel', '#5f6b76', .95, .00, 'fabric', .60,
                        '#3d4750', 1.00,
                        'a room where people talk over each other is a room where the '
                        'decision gets made twice'),
    'firebrick-face':  ('Firebrick wall face', '#8a4a33', .95, .02, 'brick', .23,
                        '#5d3226', 1.60,
                        'the wall beside a pour takes the same spatter the hearth does'),
    'weld-screen':     ('Non-combustible screened bay', '#566269', .92, .05, 'screen', .80,
                        '#7a4326', 1.80,
                        'the arc is not only the welder\'s problem: the bay walls stop '
                        'the flash reaching the next bay',),
    'chem-tile':       ('Glazed chemical-resistant tile', '#8fb3ad', .30, .03, 'tile', .30,
                        '#3d6a64', 1.50,
                        'what the floor shrugs off, the splash-back has to shrug off too'),
    'coved-white':     ('Coved cleanable wall', '#dbe1e2', .35, .02, 'smooth', 1.50,
                        '#aebdc0', 0.60,
                        'a square corner is somewhere particulate can sit, so the room '
                        'has no square corners'),
    'mesh-guard':      ('Guarded mesh partition', '#8a8452', .70, .55, 'mesh', .35,
                        '#4a4626', 0.85,
                        'you have to see into a bay you are not allowed to walk into'),

    # ---------------------------------------------- the second catalogue --
    # Eleven walls the first pass had no room for, each reached by a rule
    # below. The same assert that refuses an unplaced floor refuses these.
    'brick-common':    ('Common brick wall', '#9a5f4a', .92, .02, 'brick', .23,
                        '#6b3c2d', 1.30,
                        'a bricklaying hall is judged on a wall, so the hall has one '
                        'to be judged against'),
    'ashlar-stone':    ('Coursed ashlar stone', '#b6a98d', .88, .02, 'ashlar', .60,
                        '#7d7159', 1.40,
                        'the banker shop matches an existing course, and the course '
                        'has to be on the wall to be matched'),
    'glazed-curtain':  ('Glazed curtain wall bay', '#7f9aa4', .12, .35, 'glazing', 1.50,
                        '#4e6b78', 1.00,
                        'a glazing trade tests against a real bay, because a sealed '
                        'joint only fails where the light gets in'),
    'corrugated-steel':('Profiled steel cladding', '#9aa7ae', .60, .50, 'corrugate', .70,
                        '#5a666e', 1.20,
                        'the cladding trade fixes to the wall it also makes, and the '
                        'rib spacing is the whole argument'),
    'stainless-splash':('Stainless splash-back', '#aeb9c0', .28, .75, 'plate', 1.00,
                        '#77838b', 1.60,
                        'a wall that is wiped down every shift should not be made of '
                        'something that minds being wiped down'),
    'gunned-castable': ('Gunned refractory castable', '#a89066', .96, .02, 'gunite', .80,
                        '#6e5a37', 1.70,
                        'a lining is sprayed, not laid, and what it looks like wet is '
                        'what it looks like for the next four years'),
    'poly-enclosure':  ('Sheeted negative-pressure enclosure', '#c4d2d0', .40, .02, 'sheet', 1.20,
                        '#8fa5a4', 1.00,
                        'the room is built the morning the work starts and binned the '
                        'evening it clears'),
    'switchgear-lineup':('Switchgear lineup face', '#8d9aa2', .35, .45, 'cabinet', .90,
                        '#48555e', 1.10,
                        'in an electrical room the wall IS the equipment, and the '
                        'labels on it are the only map anyone has'),
    'perf-acoustic':   ('Perforated metal acoustic liner', '#8b9a8c', .70, .40, 'perf', .60,
                        '#4f5c51', 1.20,
                        'a machine hall is loud because the walls give it all back, '
                        'unless the walls are built not to'),
    'rock-face':       ('Shotcreted rock face', '#7b7266', .97, .02, 'gunite', 1.00,
                        '#544d44', 1.50,
                        'underground the wall is the ground, and what holds it up is '
                        'sprayed onto it'),
    'tank-plate':      ('Lapped tank plate', '#8f6353', .78, .55, 'plate', 1.20,
                        '#5e4136', 1.40,
                        'you enter a vessel through a shell you can read: the laps, '
                        'the seams and where the primer has gone'),

    # -------------------------------------------- the timber and trade walls --
    # The same argument as the floors above, at shoulder height. A wall in a
    # working building is a material somebody chose, and the choice is usually
    # the trade's own: a joinery hall panels its board room, a masonry hall
    # limewashes brick, a concrete hall leaves the board marks on.
    #
    # Every one of these names a pattern already in the vocabulary below, so
    # the wall engine paints it with the recipe it already has.
    'oak-panelled':    ('Oak-panelled board room', '#8a6136', .78, .00, 'plank', .60,
                        '#5d3f22', 1.00,
                        'the room where the trade argues about its own standards is '
                        'panelled to that standard, and everyone in it can see the joint'),
    'pine-boarded':    ('Whitewood board lining', '#c2a373', .85, .00, 'plank', .50,
                        '#8c7448', 0.95,
                        'a boarded wall can be cut into, patched and boarded again, '
                        'which is what a room used for practice needs'),
    'birch-ply-lined': ('Birch ply lining', '#c9a97a', .80, .00, 'plywood', 1.20,
                        '#8e7047', 1.10,
                        'the face veneer is good enough to leave unpainted, so the '
                        'wall shows every screw somebody put in it'),
    'limewashed-brick':('Limewashed brick', '#cfc8bb', .90, .02, 'brick', .23,
                        '#8e887c', 1.30,
                        'lime lets the brick behind it dry out, which is the argument '
                        'a restoration trade has with paint every week'),
    'engineering-brick':('Blue engineering brick', '#4a5560', .80, .02, 'brick', .23,
                        '#2f3740', 1.30,
                        'dense enough not to take up water, which is why it is the '
                        'brick below ground and in a chamber that floods'),
    'glazed-brick':    ('Glazed white brick', '#d5dbd8', .28, .02, 'brick', .23,
                        '#8fa3a0', 1.40,
                        'a fired glaze on a structural unit: it washes down like tile '
                        'and takes a knock like brick'),
    'fair-face-concrete': ('Fair-faced concrete', '#9aa0a2', .86, .02, 'slab', .90,
                        '#6a7072', 1.20,
                        'the pour is the finish, so the formwork, the release agent '
                        'and the vibration are all on show and cannot be made good later'),
    'board-marked-concrete': ('Board-marked concrete', '#a7a396', .88, .02, 'plank', .80,
                        '#71705f', 1.30,
                        'sawn boards used as form face leave their grain in the '
                        'concrete, and setting them out is the whole of the work'),
    'plaster-cream':   ('Painted plaster, cream', '#ded0b4', .82, .01, 'smooth', 1.50,
                        '#a89a7c', 0.90,
                        'a warm near-white throws light back into a room people read '
                        'drawings in without glaring off the paper'),
    'plaster-sage':    ('Painted plaster, sage', '#9aad93', .84, .01, 'smooth', 1.50,
                        '#64775e', 0.90,
                        'a muted green is the one wall colour a finish sample can be '
                        'held against without the wall deciding the answer'),
    'plaster-slate':   ('Painted plaster, slate', '#6a7885', .84, .01, 'smooth', 1.50,
                        '#444f59', 0.95,
                        'dark walls stop a screen-lit room reflecting itself back at '
                        'the people reading the screens'),
    'plaster-ochre':   ('Painted plaster, ochre', '#c79a4e', .84, .01, 'smooth', 1.50,
                        '#8a682f', 0.95,
                        'earth pigment on lime plaster is the oldest painted wall the '
                        'trade still makes, and the one it is asked to match'),
    'epoxy-wall-coat': ('Epoxy-coated wall', '#a7c1c8', .35, .03, 'smooth', 1.50,
                        '#6e8a92', 1.50,
                        'the coating a coatings trade puts on everyone else\'s walls, '
                        'on its own, where the failures can be left up and looked at'),
    'perforated-ply':  ('Perforated ply acoustic lining', '#b99a6c', .75, .00, 'perf', .60,
                        '#7d6642', 1.10,
                        'holes and a void behind them: the cheapest honest way to stop '
                        'a hard room ringing, and visible enough to teach from'),
    'terracotta-rainscreen': ('Terracotta rainscreen', '#a5613f', .70, .05, 'panel', .70,
                        '#6d3f28', 1.20,
                        'extruded and fired, hung on rails with an open joint, so the '
                        'cavity behind it does the waterproofing'),
    'zinc-standing-seam': ('Zinc standing seam', '#7d868c', .55, .45, 'corrugate', .70,
                        '#4e565b', 1.20,
                        'the seam is folded on site and is the only thing holding the '
                        'weather out, which is why it is practised indoors first'),
    'copper-panel':    ('Copper panel', '#8a6a4a', .45, .60, 'panel', .70,
                        '#5c452f', 1.10,
                        'it changes colour for thirty years after it is fixed, so a '
                        'sample wall is the only way to argue about the finish'),
    'anodised-alu-panel': ('Anodised aluminium panel', '#9fa8ad', .35, .55, 'panel', .70,
                        '#6b7377', 1.10,
                        'the colour is grown into the oxide rather than painted on, '
                        'and a scratch cannot be touched in'),
    'acoustic-oat':    ('Acoustic panel, oatmeal', '#bfae90', .95, .00, 'fabric', .60,
                        '#857a62', 1.00,
                        'a quiet room in a warm colour, because a room people write '
                        'in all day should not feel like a booth'),
    'acoustic-rust':   ('Acoustic panel, rust', '#9a5a44', .95, .00, 'fabric', .60,
                        '#653a2c', 1.00,
                        'the absorber has to be somewhere people look, so it is worth '
                        'it being a colour they do not mind looking at'),
    'metro-tile-white':('Glazed white wall tile', '#dde3e2', .25, .02, 'tile', .30,
                        '#9aabaa', 1.50,
                        'a small glazed tile has a lot of grout in it, and keeping '
                        'that grout sound is the discipline the room is teaching'),
    'quarry-tile-wall':('Green quarry tile', '#5f7f6a', .35, .02, 'tile', .30,
                        '#3b5343', 1.50,
                        'the splash-back behind a wet bench, in a colour that does '
                        'not show every drip and does show a crack'),
    'marker-glass':    ('Glass marker wall', '#b6c9cd', .10, .20, 'glazing', 1.50,
                        '#7b9096', 1.00,
                        'you can set out full size on glass, wipe it, and see the '
                        'work through it while you do'),
    'ashlar-grey':     ('Grey ashlar course', '#9aa19a', .88, .02, 'ashlar', .60,
                        '#676d67', 1.40,
                        'a second stone to match against, because matching one '
                        'existing course teaches nothing about matching a different one'),
    'brass-screen':    ('Brass-infilled screen', '#a08a4a', .55, .50, 'screen', .80,
                        '#6a5a2c', 1.20,
                        'rope and hardware have to be visible from outside the store '
                        'without the store being open'),
    'motor-control-face': ('Motor control centre face', '#7e8a80', .40, .40, 'cabinet', .90,
                        '#4c554e', 1.10,
                        'a wall of starters and their labels: the room is the '
                        'equipment, and reading it is the lesson'),
    'clear-sheet-curtain': ('Clear sheeted curtain', '#d9e2dc', .30, .02, 'sheet', 1.20,
                        '#9fb0a8', 1.00,
                        'you can watch a containment being used without being inside '
                        'it, which is the only safe way to assess one'),
    'gunned-insulating':('Gunned insulating lining', '#c0a882', .96, .02, 'gunite', .80,
                        '#86704a', 1.60,
                        'a practice lining, gunned onto a wall so it can be cut into, '
                        'read and gunned again next week'),
}

# What each room's function asks of its walls when neither the trade's
# hazard nor its craft says anything. One per strand, exactly — the same
# contract FUNCTION_DEFAULT has.
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
    'molten-metal':  {'procedure': 'firebrick-face', 'machines': 'firebrick-face',
                      'materials': 'gunned-castable'},
    'ionising-radiation': {'procedure': 'poly-enclosure',
                           'inspection': 'poly-enclosure'},
    'hot-work':      {'procedure': 'weld-screen'},
    'corrosive':     {'procedure': 'chem-tile'},
    'confined-space':{'procedure': 'tank-plate', 'machines': 'tank-plate'},
    'contaminant':   {'procedure': 'coved-white'},
    'particulate':   {'procedure': 'coved-white', 'inspection': 'coved-white'},
    'immersion':     {'procedure': 'chem-tile'},
    'wet-process':   {'procedure': 'chem-tile'},
    'work-at-height':{'procedure': 'impact-block', 'safety': 'impact-block'},
    'mobile-plant':  {'procedure': 'mesh-guard', 'machines': 'mesh-guard'},
    'suspended-load':{'materials': 'mesh-guard'},
    'rotating-machinery': {'machines': 'perf-acoustic'},
    'timber-trade':  {'procedure': 'ply-lined'},
}

# What a craft changes about a wall, on the same terms. A craft absent from
# this table placed a floor and left the wall alone, which is a statement
# too: a fibre splicer's bench changes what is underfoot and nothing at
# shoulder height.
CRAFT_WALL = {
    'clean-process':   {'machines': 'stainless-splash', 'materials': 'stainless-splash',
                        'inspection': 'metro-tile-white'},
    'hot-shop':        {'tools': 'gunned-castable',
                        'troubleshooting': 'gunned-insulating'},
    'containment-craft': {'materials': 'coved-white', 'tools': 'coved-white',
                          'inspection': 'clear-sheet-curtain'},
    'structural-steel': {'materials': 'corrugated-steel'},
    'marine-craft':    {'machines': 'tank-plate'},
    'lifting-gear':    {'machines': 'mesh-guard'},
    'vehicle-shop':    {'machines': 'liner-panel'},
    'hard-standing':   {'procedure': 'corrugated-steel'},
    'precision-metal': {'machines': 'perf-acoustic', 'layout': 'marker-glass'},
    'masonry-stone':   {'procedure': 'ashlar-stone', 'layout': 'brick-common',
                        'coordination': 'limewashed-brick',
                        'leadership': 'plaster-ochre', 'materials': 'ashlar-grey'},
    'finish-trade':    {'materials': 'ply-lined', 'coordination': 'plaster-sage',
                        'documentation': 'perforated-ply'},
    'glass-envelope':  {'procedure': 'glazed-curtain', 'inspection': 'glazed-curtain',
                        'leadership': 'copper-panel', 'machines': 'anodised-alu-panel'},
    'sheet-membrane':  {'procedure': 'corrugated-steel', 'materials': 'corrugated-steel',
                        'leadership': 'terracotta-rainscreen',
                        'tools': 'zinc-standing-seam'},
    'coatings':        {'machines': 'chem-tile', 'materials': 'epoxy-wall-coat'},
    'rail-craft':      {'procedure': 'mesh-guard', 'machines': 'mesh-guard'},
    'underground':     {'safety': 'rock-face', 'tools': 'rock-face'},
    'digital-systems': {'procedure': 'switchgear-lineup',
                        'troubleshooting': 'switchgear-lineup',
                        'coordination': 'plaster-slate'},
    'power-network':   {'machines': 'switchgear-lineup',
                        'troubleshooting': 'switchgear-lineup',
                        'materials': 'motor-control-face'},
    'process-fluid':   {'machines': 'liner-panel', 'materials': 'glazed-brick',
                        'tools': 'quarry-tile-wall'},
    # The walls the crafts above brought with them. A craft absent from this
    # table still placed a floor and left the wall alone, which is a statement
    # too - and these are the ones where the trade's own material is the wall.
    'timber-craft':    {'leadership': 'oak-panelled', 'coordination': 'pine-boarded',
                        'tools': 'birch-ply-lined'},
    'rope-access':     {'coordination': 'acoustic-rust', 'materials': 'brass-screen'},
    'concrete-craft':  {'materials': 'fair-face-concrete',
                        'leadership': 'board-marked-concrete'},
    'buried-utility':  {'materials': 'engineering-brick'},
    'survey-control':  {'coordination': 'plaster-cream',
                        'documentation': 'acoustic-oat'},
}


def wall_of(strand, hazard_keys, craft_keys):
    """The room's wall after its hazards, then its crafts, have had their say.

    Most-specific-first, exactly as §24.1 resolves a floor: the first
    governing hazard that names THIS strand decides, then the first craft
    that does. As with floors, a rule is only recorded as the placer when it
    actually changed the answer — where its wall equals the function
    default, the function decided, and the record says so.
    """
    func = WALL_DEFAULT[strand]
    for hz in hazard_keys:
        assert hz in HAZARD_KEYS, f'{hz} is not a hazard class'
        want = WALL_HAZARD.get(hz, {}).get(strand)
        if want and want != func:
            return {'wall': want, 'placed_by': 'hazard', 'hazard': hz}
        if want:
            # the hazard named this wall and chose exactly the function
            # default; it decided, and a craft must not overrule a decision
            # a hazard has already made
            return {'wall': func, 'placed_by': 'function'}
    for ck in craft_keys:
        assert ck in CRAFT_KEYS, f'{ck} is not a craft'
        want = CRAFT_WALL.get(ck, {}).get(strand)
        if want and want != func:
            return {'wall': want, 'placed_by': 'craft', 'craft': ck}
    return {'wall': func, 'placed_by': 'function'}


# ----------------------------------------------------------------- checks --
# Every property the rest of this module relies on, asserted here rather
# than assumed downstream. A default that silently substituted would make
# each of these pass while the world quietly lost a surface.
assert set(WALL_DEFAULT) == set(FUNCTION_DEFAULT), 'a wall default per room, exactly'
assert set(WALL_HAZARD) <= set(HAZARD_KEYS), \
    'a wall hazard override must name a hazard that exists'
assert set(CRAFT_WALL) <= set(CRAFT_KEYS), \
    'a wall craft override must name a craft that exists'
assert all(w in WALLS for m in WALL_HAZARD.values() for w in m.values()), \
    'every hazard override names a wall in the catalogue'
assert all(w in WALLS for m in CRAFT_WALL.values() for w in m.values()), \
    'every craft override names a wall in the catalogue'
assert all(w in WALLS for w in WALL_DEFAULT.values()), \
    'every function default names a wall in the catalogue'
assert all(f in SURFACES for f in FUNCTION_DEFAULT.values()), \
    'every function default names a finish in the catalogue'
assert all(f in SURFACES for m in HAZARD_ROOMS.values() for f in m.values()), \
    'every hazard override names a finish in the catalogue'
assert all(f in SURFACES for m in CRAFT_ROOMS.values() for f in m.values()), \
    'every craft override names a finish in the catalogue'
assert set(HAZARD_ROOMS) == set(HAZARD_KEYS) and set(CRAFT_ROOMS) == set(CRAFT_KEYS)

# A rule that names a room and picks that room's own function default has
# changed nothing, and would only teach the record to claim a reason that
# did no work (§24.1). Hazards are exempt: hot work confirming a default on
# purpose is the case §24.1 was written about. Crafts are not — a craft is
# a weaker claim and has no business restating a default.
for _ck, _rooms in CRAFT_ROOMS.items():
    for _st, _fin in _rooms.items():
        assert _st in FUNCTION_DEFAULT, f'{_ck}: {_st} is not a room strand'
        assert _fin != FUNCTION_DEFAULT[_st], \
            f'{_ck}: {_st} restates the function default and changes nothing'
for _ck, _rooms in CRAFT_WALL.items():
    for _st, _wal in _rooms.items():
        assert _st in WALL_DEFAULT, f'{_ck}: {_st} is not a room strand'
        assert _wal != WALL_DEFAULT[_st], \
            f'{_ck}: {_st} restates the wall default and changes nothing'
for _hk, _rooms in HAZARD_ROOMS.items():
    for _st in _rooms:
        assert _st in FUNCTION_DEFAULT, f'{_hk}: {_st} is not a room strand'
for _hk, _rooms in WALL_HAZARD.items():
    for _st in _rooms:
        assert _st in WALL_DEFAULT, f'{_hk}: {_st} is not a room strand'

# The pattern vocabulary is closed in both directions: nothing may name a
# pattern the renderer has no recipe for, and no recipe may sit here unused.
_PATS_USED = ({s[4] for s in SURFACES.values()} | {w[4] for w in WALLS.values()})
assert not _PATS_USED - set(PATTERNS), \
    f'surfaces name patterns that are not declared: {sorted(_PATS_USED - set(PATTERNS))}'
assert not set(PATTERNS) - _PATS_USED, \
    f'patterns declared and never used: {sorted(set(PATTERNS) - _PATS_USED)}'

# Two surfaces sharing one colour are two surfaces the eye cannot tell
# apart, which defeats the whole point of a catalogue this size.
assert len({s[1] for s in SURFACES.values()}) == len(SURFACES), \
    'two finishes share a colour'
assert len({w[1] for w in WALLS.values()}) == len(WALLS), 'two walls share a colour'


def chroma(hexcolor):
    """How far a colour sits from neutral grey, 0-255. Pure grey is 0."""
    r, g, b = (int(hexcolor[i:i + 2], 16) for i in (1, 3, 5))
    return max(r, g, b) - min(r, g, b)


def is_warm(hexcolor):
    """True where red leads blue — the honest test for a warm material."""
    r, _, b = (int(hexcolor[i:i + 2], 16) for i in (1, 3, 5))
    return r > b


# The palette rule, asserted rather than eyeballed. The first catalogue had
# a median chroma of 9 out of 255 across the floors and 12 across the walls,
# which is another way of saying it was grey. These thresholds are the floor
# that keeps it from drifting back: a change that neutralises the palette
# fails the build rather than quietly shipping.
def _median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if len(xs) % 2 else (xs[len(xs) // 2 - 1]
                                                 + xs[len(xs) // 2]) / 2


for _label, _table, _ix in (('finishes', SURFACES, 1), ('walls', WALLS, 1)):
    _cols = [v[_ix] for v in _table.values()]
    assert _median(chroma(c) for c in _cols) >= 19, \
        f'the {_label} palette has gone grey again (median chroma below 19)'
    _warm = sum(1 for c in _cols if is_warm(c))
    assert len(_cols) // 4 <= _warm <= len(_cols) * 3 // 4, \
        f'the {_label} palette is all one temperature ({_warm} of {len(_cols)} warm)'
