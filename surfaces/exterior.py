"""
SmartCiti.X : exterior pattern families and colour categories (wave 11).

Two AUTHORED catalogues, parameters only - no image file is shipped; web/patternkit.py
draws each recipe at runtime onto a power-of-two canvas.

EXT_RECIPES  id -> recipe. `kind` names the drawing algorithm in patternkit (closed set
             EXT_KINDS); every count is PER TILE so a tile repeats exactly (tileable by
             construction); `tile_m` is the real-world edge of one tile in metres (AUTHORED,
             chosen by eye for scale, not read from any product or standard); `joint_shade`
             derives the joint/shadow colour from the base colour (negative = darker);
             `uses` says which building part it may dress.
COLOUR_FAMILIES  family id -> {name, why, colours: [(id, name, hex, use)], lettering}.
             `use` is one of COLOUR_USES. `lettering` lists (fg id, bg id) pairs a page may
             set text in (a sign, a label); each must reach WCAG AA 4.5:1 or the build stops.
LANDUSE_HINTS  the world's land-use classes -> the recipes and families that suit them
             (a suggestion table a world may read; AUTHORED, not a planning rule).

No colour here is a paint brand's, a standard's official value or a trademarked name:
every name is descriptive, written for this catalogue.
"""

# bond params: `courses` rows per tile; `per_course` stretchers per tile width (a header is half a
# stretcher); `offset` shifts every odd course (every header course for English) by that many
# stretchers; `header_every` 0 = stretchers only, 1 = Flemish (S,H alternate in a course),
# 2 = English (a stretcher course, then a header course); `joint` = joint / course height.
EXT_KINDS = ('bond', 'herringbone', 'basketweave', 'lap', 'board_batten', 'shingle',
             'speckle', 'formed', 'corrugated', 'seam', 'cobble', 'hex', 'barrel', 'slate')

COLOUR_USES = ('body', 'trim', 'accent', 'roof', 'ground')

EXT_FAMILIES = ('brick', 'siding', 'render', 'concrete', 'metal', 'paving', 'roof')

# id: (family, name, kind, params, tile_m, joint_shade, uses, why)
EXT_RECIPES = {
    # ---- brick bonds: courses x bricks per course, joint as a fraction of the unit height
    'brick.running': ('brick', 'Running bond brick', 'bond',
                      {'courses': 12, 'per_course': 4, 'offset': 0.5, 'joint': 0.14, 'header_every': 0, 'vary': 0.06},
                      0.90, -0.28, ('wall',), 'Half-lap stretchers: the everyday wall of a commercial street.'),
    'brick.flemish': ('brick', 'Flemish bond brick', 'bond',
                      {'courses': 16, 'per_course': 6, 'offset': 0.75, 'joint': 0.14, 'header_every': 1, 'vary': 0.05},
                      1.20, -0.28, ('wall',), 'Stretcher and header alternating in every course; headers drawn darker.'),
    'brick.english': ('brick', 'English bond brick', 'bond',
                      {'courses': 12, 'per_course': 4, 'offset': 0.25, 'joint': 0.14, 'header_every': 2, 'vary': 0.05},
                      0.90, -0.28, ('wall',), 'A course of stretchers, then a course of headers.'),
    'brick.stack': ('brick', 'Stack bond brick', 'bond',
                    {'courses': 12, 'per_course': 4, 'offset': 0.0, 'joint': 0.14, 'header_every': 0, 'vary': 0.04},
                    0.90, -0.28, ('wall', 'ground'), 'Joints aligned both ways: a modern, decorative bond.'),
    'brick.herringbone': ('brick', 'Herringbone brick', 'herringbone',
                          {'units': 8, 'ratio': 2, 'joint': 0.12, 'vary': 0.06},
                          0.80, -0.30, ('ground', 'wall'), 'Units at right angles in a zigzag: courtyards and walks.'),
    'brick.basketweave': ('brick', 'Basketweave brick', 'basketweave',
                          {'cells': 4, 'per_cell': 2, 'joint': 0.12, 'vary': 0.05},
                          0.80, -0.30, ('ground',), 'Pairs of units turned each cell: a patio or plaza floor.'),
    # ---- siding: boards per tile, shadow as the dark lap line fraction
    'siding.clapboard': ('siding', 'Clapboard siding', 'lap',
                         {'boards': 8, 'shadow': 0.22, 'bevel': 1, 'vary': 0.02},
                         1.20, -0.30, ('wall',), 'Bevelled boards overlapping downward: a deep shadow line under each.'),
    'siding.shiplap': ('siding', 'Shiplap siding', 'lap',
                       {'boards': 8, 'shadow': 0.08, 'bevel': 0, 'vary': 0.02},
                       1.20, -0.25, ('wall',), 'Rebated boards lying flat: a thin, even groove.'),
    'siding.board_batten': ('siding', 'Board-and-batten siding', 'board_batten',
                            {'boards': 4, 'batten': 0.14, 'vary': 0.02},
                            1.20, -0.22, ('wall',), 'Wide vertical boards with a narrow batten over each seam.'),
    'siding.shingle': ('siding', 'Straight-cut shingle', 'shingle',
                       {'rows': 8, 'per_row': 6, 'shape': 'square', 'joint': 0.08, 'vary': 0.08},
                       1.00, -0.30, ('wall', 'roof'), 'Staggered straight-cut shingles, each a little different.'),
    'siding.fishscale': ('siding', 'Fish-scale shingle', 'shingle',
                         {'rows': 8, 'per_row': 6, 'shape': 'round', 'joint': 0.08, 'vary': 0.06},
                         1.00, -0.30, ('wall',), 'Round-butt shingles: a gable-end ornament.'),
    # ---- renders and mixes: seeded speckle, wrapped at the tile edges
    'render.stucco': ('render', 'Stucco render', 'speckle',
                      {'dots': 900, 'size': [0.004, 0.012], 'spread': 0.10, 'aggregate': 0},
                      1.00, -0.10, ('wall',), 'A trowelled cement render: fine, low-contrast grain.'),
    'render.terrazzo': ('render', 'Terrazzo', 'speckle',
                        {'dots': 260, 'size': [0.010, 0.034], 'spread': 0.30, 'aggregate': 1},
                        0.60, -0.35, ('ground', 'wall'), 'Stone chips set in a binder and ground flat.'),
    # ---- concrete
    'concrete.board_formed': ('concrete', 'Board-formed concrete', 'formed',
                              {'boards': 6, 'grain': 14, 'tie_holes': 2, 'vary': 0.05},
                              1.20, -0.18, ('wall',), 'Concrete cast against planks: the grain and tie holes stay.'),
    'concrete.block': ('concrete', 'Concrete block', 'bond',
                       {'courses': 4, 'per_course': 2, 'offset': 0.5, 'joint': 0.06, 'header_every': 0, 'vary': 0.04},
                       0.80, -0.22, ('wall',), 'Large hollow units in running bond: warehouses and yards.'),
    # ---- metal
    'metal.corrugated': ('metal', 'Corrugated metal', 'corrugated',
                         {'waves': 8, 'bands': 6},
                         0.80, -0.30, ('wall', 'roof'), 'A sine-profile sheet: sheds, docks, workshops.'),
    'metal.standing_seam': ('metal', 'Standing-seam metal', 'seam',
                            {'panels': 4, 'seam': 0.05},
                            1.60, -0.30, ('roof', 'wall'), 'Flat pans joined by raised seams: a modern roof.'),
    # ---- paving
    'paving.pavers': ('paving', 'Concrete pavers', 'bond',
                      {'courses': 4, 'per_course': 2, 'offset': 0.5, 'joint': 0.05, 'header_every': 0, 'vary': 0.07},
                      0.80, -0.30, ('ground',), 'Rectangular pavers in running bond: sidewalks and plazas.'),
    'paving.cobble': ('paving', 'Cobblestones', 'cobble',
                      {'cols': 6, 'rows': 6, 'jitter': 0.18, 'joint': 0.10, 'vary': 0.12},
                      0.90, -0.40, ('ground',), 'Rounded setts in loose rows: an old street.'),
    'paving.hex': ('paving', 'Hexagon pavers', 'hex',
                   {'cols': 4, 'rows': 4, 'joint': 0.07, 'vary': 0.06},
                   0.90, -0.30, ('ground',), 'Six-sided pavers: a park path.'),
    # ---- roofs
    'roof.barrel_tile': ('roof', 'Barrel clay tile', 'barrel',
                         {'rows': 6, 'per_row': 6, 'shade': 0.25},
                         1.20, -0.35, ('roof',), 'Half-round tiles laid in rows: a warm-climate roof.'),
    'roof.slate': ('roof', 'Slate roof', 'slate',
                   {'rows': 8, 'per_row': 5, 'joint': 0.06, 'vary': 0.10},
                   1.00, -0.35, ('roof',), 'Split stone laid in staggered courses.'),
    'roof.asphalt_shingle': ('roof', 'Three-tab roof shingle', 'shingle',
                             {'rows': 10, 'per_row': 4, 'shape': 'square', 'joint': 0.10, 'vary': 0.10},
                             1.00, -0.35, ('roof',), 'Granular strip shingles: the common house roof.'),
}

# family id -> (name, why, colours [(id, name, hex, use)], lettering [(fg, bg)])
COLOUR_FAMILIES = {
    'earth': ('Earth', 'Fired clay, adobe and sandstone: warm, low-chroma bodies with a dark trim.',
              [('adobe', 'Adobe', '#C79A74', 'body'),
               ('fired_clay', 'Fired clay', '#9C4E35', 'body'),
               ('sandstone', 'Sandstone', '#E3CFA5', 'body'),
               ('umber_trim', 'Umber trim', '#4A3223', 'trim'),
               ('ochre', 'Ochre', '#C8912C', 'accent'),
               ('terracotta_roof', 'Terracotta roof', '#CF7A4E', 'roof'),
               ('packed_earth', 'Packed earth', '#8C7A62', 'ground')],
              [('umber_trim', 'sandstone'), ('sandstone', 'umber_trim')]),
    'coastal': ('Coastal', 'Weathered boards, sea-glass and sand: light bodies, white trim.',
                [('driftwood', 'Driftwood', '#B7AE9E', 'body'),
                 ('sea_glass', 'Sea glass', '#9FC7BE', 'body'),
                 ('shell_white', 'Shell white', '#F3F0E8', 'trim'),
                 ('harbour_blue', 'Harbour blue', '#2F5F7F', 'accent'),
                 ('weathered_shingle', 'Weathered shingle', '#6E6A64', 'roof'),
                 ('dune_sand', 'Dune sand', '#D9C7A0', 'ground')],
                [('harbour_blue', 'shell_white'), ('shell_white', 'harbour_blue')]),
    'creole': ('Creole and Caribbean', 'Saturated shotgun-house bodies with contrasting shutters and trim.',
               [('mango', 'Mango', '#E8A33D', 'body'),
                ('bougainvillea', 'Bougainvillea', '#B8336A', 'body'),
                ('lagoon', 'Lagoon', '#2A9D8F', 'body'),
                ('lime_wash', 'Lime wash', '#F4EFD8', 'trim'),
                ('shutter_green', 'Shutter green', '#173F2A', 'accent'),
                ('rust_roof', 'Rust roof', '#8A3B24', 'roof'),
                ('shell_path', 'Shell path', '#CFC6B2', 'ground')],
               [('shutter_green', 'lime_wash'), ('lime_wash', 'shutter_green'), ('lime_wash', 'rust_roof')]),
    'midcentury': ('Mid-century', 'Breeze-block pastels and teak: flat planes with one bright accent.',
                   [('avocado', 'Avocado', '#8C9A4B', 'body'),
                    ('pale_turquoise', 'Pale turquoise', '#8FCFCB', 'body'),
                    ('teak', 'Teak', '#7A4A2A', 'trim'),
                    ('atomic_orange', 'Atomic orange', '#D8662B', 'accent'),
                    ('charcoal_roof', 'Charcoal roof', '#3A3C3E', 'roof'),
                    ('terrazzo_white', 'Terrazzo white', '#E6E2D8', 'ground')],
                   [('teak', 'terrazzo_white'), ('terrazzo_white', 'charcoal_roof')]),
    'industrial': ('Industrial', 'Galvanised sheet, weathered steel and concrete: greys with a hard accent.',
                   [('galvanised', 'Galvanised', '#A7ADB1', 'body'),
                    ('weathering_steel', 'Weathering steel', '#7E3F22', 'body'),
                    ('concrete_grey', 'Concrete grey', '#8E8D88', 'body'),
                    ('iron_black', 'Iron black', '#1E2226', 'trim'),
                    ('crane_yellow', 'Crane yellow', '#E3B21B', 'accent'),
                    ('sheet_roof', 'Sheet roof', '#5C6166', 'roof'),
                    ('yard_asphalt', 'Yard asphalt', '#3F4042', 'ground')],
                   [('iron_black', 'crane_yellow'), ('crane_yellow', 'iron_black'), ('iron_black', 'galvanised')]),
    'civic': ('Civic and safety accent', 'Stone and brick public buildings, with the high-visibility accents a '
              'yard or hall uses to mark a hazard (AUTHORED hues, not any standard\'s official value).',
              [('limestone', 'Limestone', '#DCD3C0', 'body'),
               ('civic_brick', 'Civic brick', '#8E3B2E', 'body'),
               ('slate_trim', 'Slate trim', '#2E3A45', 'trim'),
               ('signal_orange', 'Signal orange', '#E8641E', 'accent'),
               ('caution_yellow', 'Caution yellow', '#F2C81B', 'accent'),
               ('copper_roof', 'Copper roof', '#4E8B78', 'roof'),
               ('plaza_granite', 'Plaza granite', '#B5B0A8', 'ground')],
              [('slate_trim', 'limestone'), ('slate_trim', 'caution_yellow'), ('limestone', 'civic_brick')]),
    'park': ('Park and landscape', 'Planting, bark and path: greens that read apart from each other.',
             [('meadow', 'Meadow', '#7FA650', 'ground'),
              ('canopy', 'Canopy', '#3E7A3F', 'body'),
              ('bark', 'Bark', '#3F2D20', 'trim'),
              ('path_gravel', 'Path gravel', '#C9BFA9', 'ground'),
              ('bloom', 'Bloom', '#D9577A', 'accent'),
              ('pond', 'Pond', '#3C7F9C', 'accent')],
             [('bark', 'path_gravel'), ('path_gravel', 'bark')]),
    'night': ('Night and neon', 'After-dark signs and glazing: dark bodies with emissive accents.',
              [('night_body', 'Night body', '#141722', 'body'),
               ('dusk_trim', 'Dusk trim', '#4C4F6B', 'trim'),
               ('neon_pink', 'Neon pink', '#FF5FA2', 'accent'),
               ('neon_cyan', 'Neon cyan', '#3FE0F0', 'accent'),
               ('sodium_amber', 'Sodium amber', '#F5A623', 'accent'),
               ('wet_asphalt', 'Wet asphalt', '#3E4147', 'ground')],
              [('neon_cyan', 'night_body'), ('neon_pink', 'night_body'), ('sodium_amber', 'wet_asphalt')]),
}

# the world's land-use classes (parishes/build_world.py landUse) plus 'civic' for halls
LANDUSE_HINTS = {
    'residential': {'wall': ['siding.clapboard', 'siding.shiplap', 'siding.board_batten', 'siding.fishscale',
                             'render.stucco', 'brick.running'],
                    'roof': ['roof.asphalt_shingle', 'roof.barrel_tile', 'metal.standing_seam', 'roof.slate'],
                    'ground': ['paving.pavers', 'brick.herringbone'],
                    'families': ['creole', 'coastal', 'midcentury', 'earth']},
    'commercial': {'wall': ['brick.running', 'brick.flemish', 'brick.english', 'render.stucco', 'brick.stack'],
                   'roof': ['metal.standing_seam', 'roof.slate'],
                   'ground': ['paving.pavers', 'render.terrazzo', 'brick.basketweave'],
                   'families': ['earth', 'midcentury', 'night']},
    'industrial': {'wall': ['metal.corrugated', 'concrete.block', 'concrete.board_formed'],
                   'roof': ['metal.corrugated', 'metal.standing_seam'],
                   'ground': ['paving.pavers'],
                   'families': ['industrial', 'civic']},
    'civic': {'wall': ['brick.flemish', 'concrete.board_formed', 'render.stucco', 'brick.english'],
              'roof': ['roof.slate', 'metal.standing_seam'],
              'ground': ['render.terrazzo', 'paving.hex', 'brick.herringbone'],
              'families': ['civic', 'earth']},
    'park': {'wall': ['siding.board_batten'],
             'roof': ['siding.shingle'],
             'ground': ['paving.cobble', 'paving.hex', 'brick.herringbone'],
             'families': ['park']},
}

# Colour-vision-deficiency simulation: Machado, Oliveira and Fernandes (2009), severity 1.0,
# applied to LINEAR sRGB, result clipped to [0,1]; the published matrices, not tuned here.
CVD_MATRICES = {
    'protanopia': [[0.152286, 1.052583, -0.204868],
                   [0.114503, 0.786281, 0.113216],
                   [-0.003882, -0.048116, 1.051998]],
    'deuteranopia': [[0.367322, 0.860646, -0.227968],
                     [0.280085, 0.672501, 0.047413],
                     [-0.011820, 0.042940, 0.968881]],
}
# every pair of colours inside one family must stay at least this far apart (CIE76 dE) under
# normal vision AND under each simulation, or the build stops and names the pair.
CVD_MIN_DE = 10.0
CVD_WHY = ('CIE76 dE 2.3 is a just-noticeable difference side by side; 10 is about four times that, '
           'a gap a reader sees at a glance on a facade at street distance. Inside one family these '
           'colours are body, trim, accent, roof and ground of the same building, so each must read '
           'apart from every other for a reader with protanopia or deuteranopia too.')
QUALITY_SIZES = {'low': 128, 'medium': 256, 'high': 512}
