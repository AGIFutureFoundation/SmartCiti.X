#!/usr/bin/env python3
"""facades/ - AUTHORED exterior detail recipes and generic business signs for the open worlds.

WHAT THIS IS

1. Style families (Creole cottage, shotgun with a front gallery, Craftsman bungalow, Italianate row, mid-century
   commercial, brick warehouse, modern glass and metal, civic hall). Each is an AUTHORED recipe of detail
   components (cornice, parapet, gallery posts and railings, shutters, awnings, brackets, trims, storefront
   glazing, stoops, downpipes, rooftop units) with dimensions in metres and the colour-category / pattern id each
   uses. The names describe general building types found in many places; a real place name appears only as
   general geography ("common in the Gulf South"). No style is a replica of a real building, and no dimension
   is a survey, a code minimum or a standard's official value - they are game-scale AUTHORED values.
2. Business signs: one generic AUTHORED sign per economy/ commercial lot (economy/registry/economy.json, read
   only). A lot is a PLAY lot, never a real business at a real address. The business type shown on the sign
   is AUTHORED here (a deterministic pick from the economy pack's own business types); the name is built from
   word lists (place-ish word + type word, e.g. "Levee Bakery"). A denylist check proves no sign name equals
   or contains a name on a PARTIAL list of well-known national chains and brands written below.
3. Selection rules: which style dresses which building-kit family / land use in which world (AUTHORED).

Colours are AUTHORED flat fallbacks (name + hex + use) behind one adapter in web/facadekit.py; when the
PATTERN pack's colour categories are published the adapter maps category ids to them. No paint brand, no
trademarked colour name, no standard's official value.

    python3 facades/build.py            write facades/registry/facades.json
    python3 facades/build.py --check    exit 1 if the registry is stale
"""
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'facades.json'
ECON = ROOT / 'economy' / 'registry' / 'economy.json'
TIERS = ('RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED', 'SCRIPTED')


class FacadeBuildError(Exception):
    pass


def need(obj, key, where):
    if not isinstance(obj, dict):
        raise FacadeBuildError(f'facades: {where}: expected an object to read {key!r} from')
    if key not in obj:
        raise FacadeBuildError(f'facades: {where}: no key {key!r}')
    return obj[key]


# ------------------------------------------------------------ colour categories (AUTHORED flat fallbacks) ---
COLOURS = {
    'trim-light': {'hex': '#EEEAE0', 'use': 'window/door trims, cornices, gallery posts on painted timber'},
    'trim-dark': {'hex': '#3A3F44', 'use': 'trims on light render, storefront frames'},
    'shutter-green': {'hex': '#2F5D4A', 'use': 'louvred shutters on cottages and shotguns'},
    'shutter-blue': {'hex': '#35577A', 'use': 'louvred shutters, alternate'},
    'ironwork': {'hex': '#24262A', 'use': 'railings, brackets, blade-sign arms'},
    'brick-red': {'hex': '#8E4A3A', 'use': 'parapets and piers on brick fronts'},
    'stone-pale': {'hex': '#CFC6B4', 'use': 'civic cornices, stoops, sills'},
    'timber-brown': {'hex': '#6B4E36', 'use': 'Craftsman brackets, porch beams'},
    'awning-canvas': {'hex': '#9C3B36', 'use': 'fabric awnings'},
    'metal-grey': {'hex': '#8C949A', 'use': 'downpipes, rooftop units, metal canopies'},
    'glass-tint': {'hex': '#3E5C6B', 'use': 'storefront glazing and curtain-wall panels'},
    'roof-dark': {'hex': '#4A4A4E', 'use': 'parapet caps and roof edges'},
}
# PATTERN_CONTRACT v1 mapping (AUTHORED, ours): which PATTERN colour id stands in for each category on a page that
# loads PatternKit (web/facadekit.py setColourAdapter). None = no PATTERN colour fits; the flat colour above is used.
# The ids are checked against surfaces/registry/exterior.json at build time (fail closed, by name).
PATTERN_MAP = {
    'trim-light': 'creole.lime_wash', 'trim-dark': 'civic.slate_trim', 'shutter-green': 'creole.shutter_green',
    'shutter-blue': 'coastal.harbour_blue', 'ironwork': 'industrial.iron_black', 'brick-red': 'civic.civic_brick',
    'stone-pale': 'civic.limestone', 'timber-brown': 'midcentury.teak', 'awning-canvas': 'creole.bougainvillea',
    'metal-grey': 'industrial.galvanised', 'glass-tint': None, 'roof-dark': 'midcentury.charcoal_roof',
}
EXTERIOR = ROOT / 'surfaces' / 'registry' / 'exterior.json'
PATTERNS = {  # pattern ids the recipes name; PATTERN's module supplies the texture when published
    'plain': 'flat colour',
    'louvre': 'horizontal slats (shutters)',
    'stripe': 'vertical awning stripes',
    'brick-running': 'running-bond brick',
    'mullion-grid': 'glazing bars',
    'ribbed-metal': 'ribbed metal cladding',
    'dentil': 'small repeated blocks under a cornice',
}


def C(id_, component, layout, y_ref, y_m, h_m, depth_m, out_m, colour, pattern, width_m=None, spacing_m=None,
      x_m=None, note=None):
    """One detail component. layout: band (spans the front width), repeat (every spacing_m along the front),
    pair (either side of each opening, spacing_m apart), single (one at x_m from centre), roof (on the roof, x_m
    from centre, set back out_m from the front). y_ref: ground or eave (the kit building's wall height)."""
    c = {'id': id_, 'component': component, 'layout': layout, 'y_ref': y_ref, 'y_m': y_m, 'h_m': h_m,
         'depth_m': depth_m, 'out_m': out_m, 'colour_category': colour, 'pattern_id': pattern}
    if width_m is not None:
        c['width_m'] = width_m
    if spacing_m is not None:
        c['spacing_m'] = spacing_m
    if x_m is not None:
        c['x_m'] = x_m
    if note:
        c['note'] = note
    return c


STYLES = {
    'creole-cottage': {
        'label': 'Creole cottage', 'geography': 'a general cottage type common in the Gulf South',
        'components': [
            C('eave-fascia', 'cornice', 'band', 'eave', -0.35, 0.3, 0.25, 0.0, 'trim-light', 'plain'),
            C('shutters', 'shutters', 'pair', 'ground', 0.9, 2.2, 0.06, 0.03, 'shutter-green', 'louvre', width_m=0.55, spacing_m=3.1),
            C('door-trim', 'door_trim', 'single', 'ground', 0.0, 2.6, 0.08, 0.02, 'trim-light', 'plain', width_m=1.3, x_m=0.0),
            C('stoop', 'stoop', 'single', 'ground', 0.0, 0.45, 1.1, 0.0, 'stone-pale', 'plain', width_m=1.8, x_m=0.0),
            C('downpipe', 'downpipe', 'repeat', 'ground', 0.0, -0.3, 0.1, 0.05, 'metal-grey', 'plain', width_m=0.1, spacing_m=99.0),
        ]},
    'shotgun-gallery': {
        'label': 'Shotgun house with front gallery', 'geography': 'a general narrow-house type common in the Gulf South',
        'components': [
            C('gallery-posts', 'gallery_post', 'repeat', 'ground', 0.0, 3.0, 0.14, 1.9, 'trim-light', 'plain', width_m=0.14, spacing_m=2.4),
            C('gallery-rail', 'railing', 'band', 'ground', 0.5, 0.9, 0.05, 1.9, 'trim-light', 'plain'),
            C('gallery-beam', 'cornice', 'band', 'ground', 3.0, 0.3, 2.1, 0.0, 'trim-light', 'dentil'),
            C('brackets', 'bracket', 'repeat', 'ground', 2.6, 0.4, 0.35, 1.75, 'trim-light', 'plain', width_m=0.1, spacing_m=2.4),
            C('shutters', 'shutters', 'pair', 'ground', 0.9, 2.3, 0.06, 0.03, 'shutter-blue', 'louvre', width_m=0.55, spacing_m=3.2),
            C('steps', 'stoop', 'single', 'ground', 0.0, 0.5, 1.0, 2.3, 'stone-pale', 'plain', width_m=1.6, x_m=0.0),
        ]},
    'craftsman-bungalow': {
        'label': 'Craftsman bungalow', 'geography': 'a general early-20th-century house type found across North America',
        'components': [
            C('porch-piers', 'gallery_post', 'repeat', 'ground', 0.0, 2.7, 0.45, 1.8, 'stone-pale', 'plain', width_m=0.45, spacing_m=4.5),
            C('porch-beam', 'cornice', 'band', 'ground', 2.7, 0.35, 0.3, 1.8, 'timber-brown', 'plain'),
            C('eave-brackets', 'bracket', 'repeat', 'eave', -0.45, 0.4, 0.5, 0.25, 'timber-brown', 'plain', width_m=0.12, spacing_m=1.8),
            C('window-trim', 'window_trim', 'repeat', 'ground', 0.85, 1.7, 0.06, 0.02, 'trim-light', 'plain', width_m=1.4, spacing_m=3.4),
            C('steps', 'stoop', 'single', 'ground', 0.0, 0.55, 1.2, 2.4, 'stone-pale', 'plain', width_m=2.0, x_m=0.0),
        ]},
    'italianate-row': {
        'label': 'Italianate / Victorian row front', 'geography': 'a general 19th-century commercial-row type found in many older downtowns',
        'components': [
            C('cornice', 'cornice', 'band', 'eave', -0.6, 0.6, 0.55, 0.0, 'trim-light', 'dentil'),
            C('cornice-brackets', 'bracket', 'repeat', 'eave', -1.05, 0.45, 0.45, 0.05, 'trim-light', 'plain', width_m=0.18, spacing_m=1.6),
            C('window-hoods', 'window_trim', 'repeat', 'ground', 5.6, 0.25, 0.18, 0.05, 'trim-light', 'plain', width_m=1.3, spacing_m=3.1),
            C('balcony', 'balcony', 'band', 'ground', 3.6, 0.12, 1.2, 0.0, 'ironwork', 'plain'),
            C('balcony-rail', 'railing', 'band', 'ground', 3.72, 1.0, 0.04, 1.16, 'ironwork', 'plain'),
            C('storefront', 'storefront_glazing', 'band', 'ground', 0.5, 2.7, 0.04, 0.02, 'glass-tint', 'mullion-grid'),
            C('downpipe', 'downpipe', 'repeat', 'ground', 0.0, -0.4, 0.12, 0.06, 'metal-grey', 'plain', width_m=0.12, spacing_m=99.0),
        ]},
    'midcentury-commercial': {
        'label': 'Mid-century commercial', 'geography': 'a general mid-20th-century storefront type',
        'components': [
            C('parapet', 'parapet', 'band', 'eave', 0.0, 0.9, 0.3, 0.0, 'roof-dark', 'plain'),
            C('fascia-band', 'cornice', 'band', 'ground', 3.2, 0.7, 0.2, 0.05, 'trim-dark', 'plain'),
            C('flat-canopy', 'awning', 'band', 'ground', 3.0, 0.18, 1.6, 0.0, 'metal-grey', 'plain'),
            C('storefront', 'storefront_glazing', 'band', 'ground', 0.4, 2.5, 0.04, 0.02, 'glass-tint', 'mullion-grid'),
            C('rooftop-unit', 'rooftop_unit', 'roof', 'eave', 0.0, 1.2, 1.8, 3.5, 'metal-grey', 'ribbed-metal', width_m=2.2, x_m=0.0),
        ]},
    'brick-warehouse': {
        'label': 'Brick warehouse', 'geography': 'a general industrial-loft type found in many port and rail districts',
        'components': [
            C('stepped-parapet', 'parapet', 'band', 'eave', 0.0, 1.1, 0.45, 0.0, 'brick-red', 'brick-running'),
            C('pilasters', 'pilaster', 'repeat', 'ground', 0.0, -0.2, 0.35, 0.12, 'brick-red', 'brick-running', width_m=0.6, spacing_m=4.0),
            C('loading-canopy', 'awning', 'single', 'ground', 4.4, 0.2, 2.2, 0.0, 'metal-grey', 'ribbed-metal', width_m=6.0, x_m=0.0),
            C('loading-dock', 'stoop', 'single', 'ground', 0.0, 1.1, 2.4, 0.0, 'stone-pale', 'plain', width_m=6.0, x_m=0.0),
            C('downpipes', 'downpipe', 'repeat', 'ground', 0.0, -0.3, 0.16, 0.08, 'metal-grey', 'plain', width_m=0.16, spacing_m=12.0),
            C('rooftop-vent', 'rooftop_unit', 'roof', 'eave', 0.0, 1.4, 1.6, 4.0, 'metal-grey', 'ribbed-metal', width_m=1.6, x_m=-3.0),
        ]},
    'modern-glass': {
        'label': 'Modern glass and metal', 'geography': 'a general late-20th / 21st-century office type',
        'components': [
            C('roof-crown', 'parapet', 'band', 'eave', 0.0, 1.4, 0.2, 0.05, 'metal-grey', 'ribbed-metal'),
            C('fins', 'pilaster', 'repeat', 'ground', 4.0, -1.5, 0.45, 0.22, 'metal-grey', 'plain', width_m=0.12, spacing_m=3.1),
            C('entry-canopy', 'awning', 'single', 'ground', 3.6, 0.25, 3.0, 0.0, 'metal-grey', 'plain', width_m=7.0, x_m=0.0),
            C('lobby-glazing', 'storefront_glazing', 'band', 'ground', 0.2, 3.6, 0.05, 0.03, 'glass-tint', 'mullion-grid'),
            C('rooftop-unit', 'rooftop_unit', 'roof', 'eave', 0.0, 2.0, 3.0, 4.5, 'metal-grey', 'ribbed-metal', width_m=4.0, x_m=1.5),
        ]},
    'civic': {
        'label': 'Civic hall', 'geography': 'a general civic or union-hall type',
        'components': [
            C('cornice', 'cornice', 'band', 'eave', -0.7, 0.7, 0.6, 0.0, 'stone-pale', 'dentil'),
            C('piers', 'pilaster', 'repeat', 'ground', 0.0, -0.7, 0.4, 0.15, 'stone-pale', 'plain', width_m=0.9, spacing_m=6.0),
            C('entry-steps', 'stoop', 'single', 'ground', 0.0, 0.6, 2.4, 0.0, 'stone-pale', 'plain', width_m=8.0, x_m=0.0),
            C('door-surround', 'door_trim', 'single', 'ground', 0.0, 4.2, 0.25, 0.1, 'stone-pale', 'plain', width_m=4.6, x_m=0.0),
            C('downpipes', 'downpipe', 'repeat', 'ground', 0.0, -0.5, 0.16, 0.08, 'metal-grey', 'plain', width_m=0.16, spacing_m=18.0),
        ]},
}
# selection: first rule that matches (world, kit family, land use, variant 0|1, wall-height window) wins
RULES = [
    # parishes (Gulf South general geography)
    {'world': 'parishes', 'family': 'house', 'use': 'residential', 'variant': 0, 'h_max': 6.0, 'style': 'creole-cottage'},
    {'world': 'parishes', 'family': 'house', 'use': 'residential', 'variant': 0, 'h_max': 99.0, 'style': 'shotgun-gallery'},
    {'world': 'parishes', 'family': 'house', 'use': 'residential', 'variant': 1, 'h_max': 99.0, 'style': 'craftsman-bungalow'},
    # the Bay (general geography)
    {'world': 'bay', 'family': 'house', 'use': 'residential', 'variant': 0, 'h_max': 99.0, 'style': 'craftsman-bungalow'},
    {'world': 'bay', 'family': 'house', 'use': 'residential', 'variant': 1, 'h_max': 99.0, 'style': 'italianate-row'},
    # both worlds
    {'world': '*', 'family': 'midrise', 'use': 'commercial', 'variant': 0, 'h_max': 16.0, 'style': 'italianate-row'},
    {'world': '*', 'family': 'midrise', 'use': 'commercial', 'variant': 1, 'h_max': 16.0, 'style': 'midcentury-commercial'},
    {'world': '*', 'family': 'midrise', 'use': 'commercial', 'variant': '*', 'h_max': 999.0, 'style': 'modern-glass'},
    {'world': '*', 'family': 'midrise', 'use': 'residential', 'variant': '*', 'h_max': 999.0, 'style': 'italianate-row'},
    {'world': '*', 'family': 'midrise', 'use': 'industrial', 'variant': '*', 'h_max': 999.0, 'style': 'brick-warehouse'},
    {'world': '*', 'family': 'hall', 'use': 'civic', 'variant': '*', 'h_max': 999.0, 'style': 'civic'},
]

# ------------------------------------------------------------ signs ---
# word lists: generic place-ish words (no proper names of people) + a type word per business type
PLACE_WORDS = ['Levee', 'Bayou', 'Cypress', 'Harbor', 'Magnolia', 'Riverside', 'Crescent', 'Oak Row', 'Oxbow',
               'Marsh', 'Canal', 'Pelican', 'Live Oak', 'Gallery', 'Wharf', 'Sugarcane', 'Tidewater', 'Parish Line',
               'Front Street', 'Old Mill']
TYPE_WORDS = {
    'electrical-shop': ['Electric', 'Wiring Co.'], 'plumbing-shop': ['Plumbing', 'Pipe & Valve'],
    'carpentry-shop': ['Carpentry', 'Cabinet Works'], 'welding-shop': ['Welding', 'Fabrication'],
    'hvac-service': ['Heating & Air', 'Cooling Service'], 'landscape-yard': ['Landscaping', 'Garden Yard'],
    'paint-shop': ['Painting', 'Paint & Finish'], 'machine-shop': ['Machine Shop', 'Machine Works'],
    'diesel-garage': ['Diesel Repair', 'Diesel Garage'], 'glass-shop': ['Glass', 'Glass & Glazing'],
    'bakery': ['Bakery', 'Bread Oven'], 'boat-repair': ['Boat Repair', 'Marine Service'],
    'tool-rental': ['Tool Rental', 'Tool Library'], 'corner-grocery': ['Corner Grocery', 'Market'],
}
ICONS = {  # a generic pictogram id per business type (drawn as simple canvas shapes by the kit)
    'electrical-shop': 'bolt', 'plumbing-shop': 'drop', 'carpentry-shop': 'saw', 'welding-shop': 'spark',
    'hvac-service': 'fan', 'landscape-yard': 'leaf', 'paint-shop': 'brush', 'machine-shop': 'gear',
    'diesel-garage': 'wrench', 'glass-shop': 'pane', 'bakery': 'loaf', 'boat-repair': 'anchor',
    'tool-rental': 'hammer', 'corner-grocery': 'basket',
}
PLACEMENTS = ['fascia', 'blade', 'window', 'monument']
SIGN_PALETTES = [  # [background, text] - AUTHORED; WCAG AA is checked by web/test_facadekit.mjs with design_kit's contrast
    ['#1F3A4D', '#F4F1E8'], ['#6E2B25', '#FBF3E4'], ['#2E4A36', '#F2F0E6'], ['#F2EBD9', '#2A2A2A'],
    ['#3B3355', '#F5F2EC'], ['#0F4C5C', '#FFFFFF'],
]
# PARTIAL denylist: well-known national chains and brands. It is NOT exhaustive; it exists so a word-list
# collision with a famous name is caught by the build. Matching is case-insensitive on whole words.
DENYLIST_NOTE = ('PARTIAL list of well-known national chains and brands, written by hand for this pack; not exhaustive. '
                 'A sign name must not equal or contain any entry (case-insensitive, whole words).')
DENYLIST = sorted([
    'Walmart', 'Target', 'Costco', 'Home Depot', "Lowe's", 'Lowes', 'Ace Hardware', 'True Value', 'Menards',
    "McDonald's", 'McDonalds', 'Burger King', "Wendy's", 'Subway', 'Starbucks', "Dunkin'", 'Dunkin',
    'Krispy Kreme', 'Panera', "Popeyes", 'Chick-fil-A', 'Taco Bell', 'KFC', "Domino's", 'Pizza Hut',
    'Kroger', 'Safeway', 'Whole Foods', "Trader Joe's", 'Publix', 'Winn-Dixie', 'Piggly Wiggly', 'Aldi',
    '7-Eleven', 'Circle K', 'Walgreens', 'CVS', 'Rite Aid', 'Dollar General', 'Family Dollar', 'Dollar Tree',
    'AutoZone', "O'Reilly", 'NAPA', 'Pep Boys', 'Jiffy Lube', 'Midas', 'Firestone', 'Goodyear',
    'Sherwin-Williams', 'Benjamin Moore', 'Behr', 'Roto-Rooter', 'Mr. Rooter', 'Sunbelt Rentals',
    'United Rentals', 'Harbor Freight', 'Tractor Supply', 'Northern Tool', 'Grainger', 'Fastenal',
    'Safelite', 'Carrier', 'Trane', 'Lennox', 'Snap-on', 'Craftsman', 'DeWalt', 'Milwaukee', 'Stanley',
    'West Marine', 'Bass Pro Shops', 'Cabela\'s', 'Amazon', 'Apple', 'Google', 'Tesla', 'Shell', 'Exxon',
    'Chevron', 'Valero', 'Marathon', 'Sunoco', 'FedEx', 'UPS', 'Best Buy', 'IKEA', 'Nike',
])


def h32(*parts):
    return int(hashlib.sha256('|'.join(str(p) for p in parts).encode()).hexdigest()[:8], 16)


def words(s):
    return re.findall(r"[a-z0-9]+(?:['\-][a-z0-9]+)*", s.lower())


def deny_hit(name):
    """the denylist entry a name equals or contains as whole words, or None"""
    w = ' ' + ' '.join(words(name)) + ' '
    for d in DENYLIST:
        if ' ' + ' '.join(words(d)) + ' ' in w:
            return d
    return None


def build():
    econ = json.loads(ECON.read_text())
    btypes = need(econ, 'business_types', 'economy.json')
    bt_ids = [need(b, 'id', 'business_type') for b in btypes]
    for b in bt_ids:
        if b not in TYPE_WORDS or b not in ICONS:
            raise FacadeBuildError(f'facades: economy business type {b} has no TYPE_WORDS/ICONS entry here')
    for k in TYPE_WORDS:
        if k not in bt_ids:
            raise FacadeBuildError(f'facades: TYPE_WORDS names {k}, which is not an economy business type')
    if sorted(PATTERN_MAP) != sorted(COLOURS):
        raise FacadeBuildError('facades: PATTERN_MAP must name every colour category exactly once')
    ext = json.loads(EXTERIOR.read_text())
    ext_ids = {c['id'] for f in need(ext, 'colour_families', 'exterior.json').values() for c in need(f, 'colours', 'family')}
    for cat, pid in PATTERN_MAP.items():
        if pid is not None and pid not in ext_ids:
            raise FacadeBuildError(f'facades: PATTERN_MAP {cat} -> {pid} is not a colour id in surfaces/registry/exterior.json')
    # styles: validate
    for sid, s in STYLES.items():
        for c in need(s, 'components', sid):
            if c['colour_category'] not in COLOURS:
                raise FacadeBuildError(f'facades: {sid}/{c["id"]} colour {c["colour_category"]} is not a category')
            if c['pattern_id'] not in PATTERNS:
                raise FacadeBuildError(f'facades: {sid}/{c["id"]} pattern {c["pattern_id"]} is not a pattern id')
            if c['layout'] in ('repeat', 'pair', 'single', 'roof') and 'width_m' not in c:
                raise FacadeBuildError(f'facades: {sid}/{c["id"]} layout {c["layout"]} needs width_m')
        s['provenance'] = 'AUTHORED'
    for r in RULES:
        if r['style'] not in STYLES:
            raise FacadeBuildError(f'facades: rule names unknown style {r["style"]}')
    signs, used = [], set()
    for fips in sorted(need(econ, 'parishes', 'economy.json')):
        par = econ['parishes'][fips]
        for lot in need(par, 'lots', fips):
            if need(lot, 'zone', lot['id']) != 'commercial':
                continue
            lid = need(lot, 'id', fips)
            bt = bt_ids[h32('type', lid) % len(bt_ids)]
            k = 0
            while True:
                pw = PLACE_WORDS[h32('place', lid, k) % len(PLACE_WORDS)]
                tw = TYPE_WORDS[bt][h32('tw', lid, k) % len(TYPE_WORDS[bt])]
                name = f'{pw} {tw}'
                if name not in used and deny_hit(name) is None:
                    break
                k += 1
                if k > 200:
                    raise FacadeBuildError(f'facades: no unique, non-denylisted sign name for {lid}')
            used.add(name)
            w, d = need(lot, 'size_m', lid)
            signs.append({
                'lot_id': lid, 'parish': fips, 'x': need(lot, 'x', lid), 'z': need(lot, 'z', lid),
                'lot_size_m': [w, d], 'business_type': bt, 'name': name, 'icon': ICONS[bt],
                'placement': PLACEMENTS[h32('place-kind', lid) % len(PLACEMENTS)],
                'palette': SIGN_PALETTES[h32('pal', lid) % len(SIGN_PALETTES)],
                'provenance': 'AUTHORED',
                'label': 'AUTHORED play sign on an AUTHORED game lot - not a real business, name or address',
            })
    hits = [s['name'] for s in signs if deny_hit(s['name'])]
    if hits:
        raise FacadeBuildError(f'facades: denylisted sign names {hits}')
    src = pathlib.Path(__file__).read_bytes()
    eco_sha = hashlib.sha256(ECON.read_bytes()).hexdigest()
    stamp = hashlib.sha256(src + eco_sha.encode()).hexdigest()
    counts = {'styles': len(STYLES), 'components': sum(len(s['components']) for s in STYLES.values()),
              'colour_categories': len(COLOURS), 'patterns': len(PATTERNS), 'rules': len(RULES),
              'signs': len(signs), 'denylist': len(DENYLIST),
              'placements': {p: sum(1 for s in signs if s['placement'] == p) for p in PLACEMENTS}}
    return {
        'pack': 'facades', 'pack_version': json.loads((ROOT / 'pack' / 'manifest.json').read_text())['pack_version'],
        'contract': 'FACADE v1', 'source_stamp': stamp[:16], 'source_stamp_sha256': stamp,
        'inputs': [{'path': 'facades/build.py', 'sha256_16': hashlib.sha256(src).hexdigest()[:16]},
                   {'path': 'economy/registry/economy.json', 'sha256_16': eco_sha[:16]}],
        'provenance_tiers': list(TIERS), 'units': 'm',
        'honesty': {
            'styles': 'Style families are AUTHORED game-scale recipes of generic detail components; a place name is general geography only; no replica of a real building; dimensions are not survey, code or standard values.',
            'signs': 'Signs are play: AUTHORED names from word lists on AUTHORED economy game lots - never a real business, name or address.',
            'denylist': DENYLIST_NOTE,
            'colours': 'Colour categories are AUTHORED flat fallbacks (name + hex + use); no paint brand, trademarked colour name or official standard value.',
        },
        'colour_categories': COLOURS, 'pattern_map': PATTERN_MAP, 'pattern_families': sorted({v.split('.')[0] for v in PATTERN_MAP.values() if v}),
        'patterns': PATTERNS, 'styles': STYLES, 'rules': RULES,
        'sign_rules': {'placements': PLACEMENTS, 'palettes': SIGN_PALETTES, 'place_words': PLACE_WORDS,
                       'type_words': TYPE_WORDS, 'icons': ICONS},
        'denylist': {'note': DENYLIST_NOTE, 'partial': True, 'names': DENYLIST},
        'signs': signs, 'counts': counts,
    }


def main():
    reg = build()
    text = json.dumps(reg, indent=1, ensure_ascii=False, sort_keys=False) + '\n'
    if '--check' in sys.argv:
        if not OUT.exists() or OUT.read_text() != text:
            print('facades: registry is stale - run python3 facades/build.py')
            sys.exit(1)
        print('facades: registry current, stamp', reg['source_stamp'])
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    c = reg['counts']
    print(f"facades: {c['styles']} styles, {c['components']} components, {c['signs']} signs, "
          f"denylist {c['denylist']} (partial), stamp {reg['source_stamp']}")


if __name__ == '__main__':
    main()
