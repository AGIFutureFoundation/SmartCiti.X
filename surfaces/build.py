#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the surfaces pack builder (spec §24).

Resolves a floor finish and a wall for every room of every hall: the
trade's hazard first, then the trade's craft, then the room's function, and
the record says which rule placed it. Per §24.1 a rule is only recorded as
the placer when it changed something — where its choice equals the function
default, the function decided, and the record says so.

Emits surfaces/registry/finishes.json: 111 halls × 11 rooms, each entry
carrying the surface id and the placing rule, plus the full catalogue with
its renderer-ready parameters and the reason each finish exists.
"""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'web'))
from surfaces import (SURFACES, FUNCTION_DEFAULT, HAZARD_KEYS, hazard_of,  # noqa: E402
                      BASE_CONDITIONS, HAZARD_CONDITIONS, hazards_of,
                      merge_conditions, WALLS, WALL_DEFAULT, wall_of,
                      PATTERNS, CRAFT_KEYS, crafts_of, finish_of,
                      HAZARD_ROOMS, CRAFT_ROOMS, WALL_HAZARD, CRAFT_WALL)
from interiors import ROOMS  # noqa: E402

# One bundle version, read from the manifest rather than typed here.
PACK_VERSION = json.load(open(ROOT / 'pack/manifest.json'))['pack_version']
BUILT = "2026-09-10"

unions = json.load(open(ROOT / 'unions/registry/unions.json'))['unions']
room_strands = [r[0] for r in ROOMS]
assert set(FUNCTION_DEFAULT) == set(room_strands), 'a default per room, exactly'

halls = {}
for u in unions:
    hz, hz_rooms = hazard_of(u['name'], u['focus'])
    all_hz = hazards_of(u['name'], u['focus'])
    all_cr = crafts_of(u['name'], u['focus'])
    craft_keys = [k for k, _ in all_cr]
    rooms = {}
    walls = {}
    conditions = {}
    for strand in room_strands:
        # §24.1: hazard, then craft, then function — and the rule lives in
        # the catalogue module, which the wall resolver reads too, so the
        # two cannot drift into resolving their tiers differently.
        rooms[strand] = finish_of(strand, hz, hz_rooms, craft_keys)
        # §24.4: the wall resolves against EVERY hazard the trade carries,
        # not only the finish-driving one — a trade can weld in a bay whose
        # floor was placed by a different hazard entirely, and the bay walls
        # are still the thing that stops the flash.
        walls[strand] = wall_of(strand, [k for k, _ in all_hz], craft_keys)
        # §24.2: every governing hazard has its say, more demanding wins.
        # Crafts are absent on purpose — a craft is what the trade does, not
        # what the work can do to the person, so it has nothing to say about
        # lighting, air changes or PPE.
        governing = [k for k, hrooms in all_hz if strand in hrooms]
        conditions[strand] = merge_conditions(strand, governing)
    halls[u['slug']] = {'hazard': hz, 'hazards': [k for k, _ in all_hz],
                        'craft': craft_keys[0] if craft_keys else None,
                        'crafts': craft_keys,
                        'rooms': rooms, 'walls': walls,
                        'conditions': conditions}

# One truth per fact: every count below is counted off the rows that were
# just written, never carried along in a variable that could fall out of
# step with them.
def _tally(records, key):
    return sum(1 for h in halls.values() for r in h[records].values()
               if r['placed_by'] == key)


hazard_count = _tally('rooms', 'hazard')
craft_count = _tally('rooms', 'craft')
wall_hazard_count = _tally('walls', 'hazard')
wall_craft_count = _tally('walls', 'craft')

# A finish or a wall nobody stands in front of is a preference, and §24.1
# says this catalogue holds none. The build fails rather than shipping a
# catalogue entry no rule can reach.
placed_fin = {r['surface'] for h in halls.values() for r in h['rooms'].values()}
placed_wal = {w['wall'] for h in halls.values() for w in h['walls'].values()}
unplaced_fin = sorted(set(SURFACES) - placed_fin)
unplaced_wal = sorted(set(WALLS) - placed_wal)
assert not unplaced_fin, f'finishes no rule ever places: {unplaced_fin}'
assert not unplaced_wal, f'walls no rule ever places: {unplaced_wal}'

# Every rule the record names must be a rule that exists. A placement that
# named a tier nothing declares would read as authoritative and be nothing.
for _h in halls.values():
    for _r in _h['rooms'].values():
        assert _r['placed_by'] in ('hazard', 'craft', 'function'), _r
        assert _r.get('hazard', None) in (None, *HAZARD_KEYS), _r
        assert _r.get('craft', None) in (None, *CRAFT_KEYS), _r
    for _w in _h['walls'].values():
        assert _w['placed_by'] in ('hazard', 'craft', 'function'), _w

stamp = hashlib.sha256((HERE / 'surfaces.py').read_bytes()).hexdigest()[:16]

# ------------------------------------------------------------- legibility ---
# The honesty block says every colour here was chosen by eye. Nothing then
# measured whether a sign can be read against them. This does: WCAG 2.x
# relative luminance for every floor, wall and wainscot, and the contrast of
# each against every colour the labels registry declares - read from that
# registry with its roles (text / plate / accent), never typed here, and
# stamped so a stale read fails the suite. A translucent plate is composited
# source-over onto the finish before it is compared with that finish. Every
# number is computed; the pack's own rule with teeth is at the foot: the
# text the page actually draws on a plate must reach 4.5:1 with that plate
# composited over EVERY finish, or the build refuses and names the finish.
import colorsys
import re


def _rgba(c):
    c = c.strip()
    if c.startswith('#') and len(c) == 7:
        return (int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16), 1.0)
    m = re.fullmatch(r'rgba\((\d+),(\d+),(\d+),(\d*\.?\d+)\)', c)
    assert m, f'unreadable colour {c!r}'
    return (int(m[1]), int(m[2]), int(m[3]), float(m[4]))


def _lin(v8):
    v = v8 / 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _lum(c):
    return 0.2126 * _lin(c[0]) + 0.7152 * _lin(c[1]) + 0.0722 * _lin(c[2])


def _ratio(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _over(fg, bg):
    a = fg[3]
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3)) + (1.0,)


def _lab(c):
    # sRGB (D65) -> XYZ -> CIELAB, the 1976 formula
    r, g, b = _lin(c[0]), _lin(c[1]), _lin(c[2])
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = (0.2126729 * r + 0.7151522 * g + 0.0721750 * b) / 1.00000
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 216 / 24389 else (841 / 108) * t + 4 / 29
    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def _de76(a, b):
    la, lb = _lab(a), _lab(b)
    return sum((la[i] - lb[i]) ** 2 for i in range(3)) ** 0.5


def _r3(x):
    return round(x, 3)


labels_reg = json.load(open(ROOT / 'labels/registry/labels.json'))
LPAL = labels_reg['palette']
LROLES = labels_reg['palette_roles']
LPAINT = labels_reg['paint']
role_of = {k: role for role, keys in LROLES.items() for k in keys}
assert sorted(role_of) == sorted(LPAL), 'the labels palette and its roles disagree'
palette_sha = hashlib.sha256(json.dumps([LPAL, LROLES, LPAINT], sort_keys=True)
                             .encode()).hexdigest()[:16]

FAMILIES = {
    'floor': {sid: c for sid, (n, c, *_r) in SURFACES.items()},
    'wall': {wid: c for wid, (n, c, *_r) in WALLS.items()},
    'wainscot': {wid: wc for wid, (n, c, r, m, pat, tile, wc, wm, why) in WALLS.items()
                 if wm > 0},
}
# a text colour fails under 4.5 (normal text); a plate or an accent is a
# non-text element and fails under 3.0
THRESHOLD_OF = {'text': 4.5, 'plate': 3.0, 'accent': 3.0}
luminance = {fam: {fid: round(_lum(_rgba(c)), 4) for fid, c in cols.items()}
             for fam, cols in FAMILIES.items()}
pairs = {}
failing = []
counts = {'at_or_above_4_5': 0, 'from_3_below_4_5': 0, 'below_3': 0, 'pairs': 0}
for fam, cols in FAMILIES.items():
    pairs[fam] = {}
    for fid, c in cols.items():
        bg = _rgba(c)
        row = {}
        for key, lc in LPAL.items():
            fg = _rgba(lc)
            # a translucent plate is seen composited over the finish; a text
            # or accent colour is opaque and sits straight on it
            r = _ratio(_over(fg, bg), bg) if fg[3] < 1 else _ratio(fg, bg)
            row[key] = _r3(r)
            counts['pairs'] += 1
            if r >= 4.5:
                counts['at_or_above_4_5'] += 1
            elif r >= 3.0:
                counts['from_3_below_4_5'] += 1
            else:
                counts['below_3'] += 1
            thr = THRESHOLD_OF[role_of[key]]
            if r < thr:
                failing.append({'family': fam, 'finish': fid, 'role': key,
                                'kind': role_of[key], 'ratio': _r3(r),
                                'threshold': thr})
        pairs[fam][fid] = row

# The rule with teeth. The labels registry says which text role the page
# draws on which plate role; those are the pairs a reader meets, and every
# one of them must clear 4.5:1 with the plate composited over each finish.
text_on_plate = {}
refused = []
for paint in LPAINT.values():
    for line in ('title', 'sub'):
        t, pl = paint[line], paint['plate']
        if t not in LPAL or pl not in LPAL:
            continue                     # no plate, or a page-owned plate
        key = f'{t} on {pl}'
        if key in text_on_plate:
            continue
        fg, plate = _rgba(LPAL[t]), _rgba(LPAL[pl])
        worst = None
        per_family = {}
        for fam, cols in FAMILIES.items():
            fw = None
            for fid, c in cols.items():
                r = _ratio(fg, _over(plate, _rgba(c)))
                if fw is None or r < fw[0]:
                    fw = (r, fid)
                if r < 4.5:
                    refused.append(f'{key} over {fam} {fid}: {_r3(r)}:1')
            per_family[fam] = {'ratio': _r3(fw[0]), 'finish': fw[1]}
            if worst is None or fw[0] < worst[0]:
                worst = (fw[0], fam, fw[1])
        text_on_plate[key] = {'worst': {'ratio': _r3(worst[0]), 'family': worst[1],
                                        'finish': worst[2]},
                              'per_family': per_family}
assert not refused, 'a finish under a plate takes its text below 4.5:1: ' + '; '.join(refused)

# ---------------------------------------------------------------- palette ---
# The catalogue as a whole, measured: where its hues sit, how saturated and
# how light each family runs, and how many colours are near enough to
# another to be one colour from standing height.
DE_THRESHOLD = 5.0
DE_WHY = ('CIE76 delta-E 2.3 is the just-noticeable difference for two '
          'patches side by side under even light; a rendered hall gives '
          'neither the adjacency nor the light, so the bar for "two colours '
          'a reader could tell apart" is set at about twice that, 5.0. '
          'Pairs under it are reported, not moved: the rule in this pack '
          'is that a colour is what the material is, and the suite already '
          'refuses two finishes that are exactly one colour.')


def _hsl(c):
    h, l, s = colorsys.rgb_to_hls(c[0] / 255, c[1] / 255, c[2] / 255)
    return h * 360.0, s * 100.0, l * 100.0


def _bucket(h):
    b = int(h // 30) % 12
    return f'{b * 30:03d}-{b * 30 + 29:03d}'


hue_buckets = {}
ranges = {}
for fam, cols in FAMILIES.items():
    hb = {f'{b * 30:03d}-{b * 30 + 29:03d}': 0 for b in range(12)}
    hb['grey'] = 0
    ss, ls = [], []
    for c in cols.values():
        h, sat, lig = _hsl(_rgba(c))
        if sat == 0:
            hb['grey'] += 1
        else:
            hb[_bucket(h)] += 1
        ss.append(sat)
        ls.append(lig)
    hue_buckets[fam] = hb
    ranges[fam] = {'saturation_pct': [round(min(ss), 1), round(max(ss), 1)],
                   'lightness_pct': [round(min(ls), 1), round(max(ls), 1)],
                   'count': len(cols)}
all_cols = [(f'{fam}:{fid}', _rgba(c)) for fam, cols in FAMILIES.items()
            for fid, c in cols.items()]
near = []
for i in range(len(all_cols)):
    for j in range(i + 1, len(all_cols)):
        de = _de76(all_cols[i][1], all_cols[j][1])
        if de < DE_THRESHOLD:
            near.append({'a': all_cols[i][0], 'b': all_cols[j][0], 'delta_e': _r3(de)})
near.sort(key=lambda x: (x['delta_e'], x['a'], x['b']))

LEGIBILITY = {
    'method': 'WCAG 2.x relative luminance (sRGB, D65 coefficients .2126/'
              '.7152/.0722) and contrast (L1+.05)/(L2+.05); a translucent '
              'plate is composited source-over onto the finish and then '
              'compared with it; an opaque text or accent colour is compared '
              'straight on the finish (the no-plate case)',
    'labels_stamp': labels_reg['source_stamp'],
    'palette_sha': palette_sha,
    'palette_read': {k: {'color': v, 'role': role_of[k]} for k, v in LPAL.items()},
    'thresholds': {'normal_text': 4.5, 'large_text': 3.0, 'non_text': 3.0,
                   'fails_under': THRESHOLD_OF},
    'families': {fam: len(cols) for fam, cols in FAMILIES.items()},
    'luminance': luminance,
    'pairs': pairs,
    'counts': counts,
    'failing': failing,
    'failing_by_kind': {kind: sum(1 for f in failing if f['kind'] == kind)
                        for kind in THRESHOLD_OF},
    'text_on_plate': text_on_plate,
    'rule': 'every text-on-plate pair the labels registry paints reaches '
            '4.5:1 with the plate composited over every finish here, or the '
            'build refuses and names the finish; a text colour straight on a '
            'finish (no plate) and a plate against the finish behind it are '
            'measured and listed, and a finish is never recoloured for them, '
            'because a colour here is what the material is',
    'finishes_changed': [],
}
PALETTE_BLOCK = {
    'hue_buckets_deg': hue_buckets,
    'ranges': ranges,
    'near_duplicates': {
        'delta_e_threshold': DE_THRESHOLD, 'why': DE_WHY,
        'count': len(near),
        # a floor is never mistaken for a wall, so the pairs that matter are
        # the ones inside a family; the cross-family ones are still listed
        'within_family': {fam: sum(1 for x in near if x['a'].startswith(fam + ':')
                                   and x['b'].startswith(fam + ':'))
                          for fam in FAMILIES},
        'across_families': sum(1 for x in near
                               if x['a'].split(':')[0] != x['b'].split(':')[0]),
        'pairs': near},
}

doc = {
    'pack': 'smartcitix-trade-craft-academy-surface-registry',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'spec': 'section 24 of the ACP suite',
    'honesty': {
        # The sky pack's precedent, applied here: a colour chosen by eye is
        # AUTHORED and has to say so, in the pack that chose it. This
        # catalogue's colours, roughnesses and metalnesses are all of that
        # kind, and the count of them changes nothing about the claim.
        'colours_are_authored': 'every colour, roughness and metalness in '
                  'both catalogues is AUTHORED - chosen by eye against what '
                  'the material is, and never sampled from a photograph, a '
                  'measured swatch or a supplier\'s data. What is DERIVED is '
                  'only which hall stands on which, read from the trade\'s '
                  'own words.',
        'status': 'general good practice, not a code reference; no figure '
                  'is read from any jurisdiction\'s standard and no surface '
                  'names a product, brand, fire rating or specification '
                  'number. A real deployment replaces these with the local '
                  'standard.',
    },
    'catalogue': {
        sid: {'name': n, 'color': c, 'roughness': r, 'metalness': m,
              'pattern': pat, 'tile_m': tile, 'why': why}
        for sid, (n, c, r, m, pat, tile, why) in SURFACES.items()
    },
    'wall_catalogue': {
        wid: {'name': n, 'color': c, 'roughness': r, 'metalness': m,
              'pattern': pat, 'tile_m': tile, 'wainscot': wc,
              'wainscot_m': wm, 'why': why}
        for wid, (n, c, r, m, pat, tile, wc, wm, why) in WALLS.items()
    },
    'wall_defaults': dict(WALL_DEFAULT),
    'function_defaults': dict(FUNCTION_DEFAULT),
    # The pattern vocabulary, declared once and closed in both directions by
    # the catalogue module: a renderer that meets a pattern it has no recipe
    # for can say which one it was rather than silently drawing something
    # else.
    'patterns': dict(PATTERNS),
    # The rules themselves, emitted once. Every placement in `halls` below
    # is these four tables applied to a hall's hazard and craft lists, and
    # the suite re-derives all of them from here rather than spot-checking a
    # handful - which is only possible because the rules are published
    # instead of being locked inside the builder that ran.
    'rules': {
        'hazard_rooms': {k: dict(v) for k, v in HAZARD_ROOMS.items()},
        'craft_rooms': {k: dict(v) for k, v in CRAFT_ROOMS.items()},
        'hazard_walls': {k: dict(v) for k, v in WALL_HAZARD.items()},
        'craft_walls': {k: dict(v) for k, v in CRAFT_WALL.items()},
    },
    'legibility': LEGIBILITY,
    'palette': PALETTE_BLOCK,
    'hazards_in_use': sorted({h['hazard'] for h in halls.values() if h['hazard']}),
    'crafts_in_use': sorted({c for h in halls.values() for c in h['crafts']}),
    # Halls whose trade names no hazard that would CHANGE a floor finish.
    # That is a narrower statement than "no hazard at all" (a suspended
    # load is a hazard, but not one a floor answers), and the field says
    # exactly what was tested rather than more.
    'no_finish_driving_hazard': sorted(s for s, h in halls.items() if not h['hazard']),
    'hazard_placed_finishes': hazard_count,
    'craft_placed_finishes': craft_count,
    'hazard_placed_walls': wall_hazard_count,
    'craft_placed_walls': wall_craft_count,
    # Empty by construction, and asserted above. The field is emitted rather
    # than assumed so the suite can hold the next catalogue to it too.
    'unplaced_finishes': unplaced_fin,
    'unplaced_walls': unplaced_wal,
    # Halls whose trade names no craft. Narrower than "nothing is known
    # about this trade": these halls are placed by hazard and function, and
    # the field says exactly which halls that is.
    'no_craft': sorted(s2 for s2, h in halls.items() if not h['crafts']),
    # Walls a hazard never moved. Stated the same narrow way the floor
    # field above is: these trades carry hazards, several of them, and
    # none of those hazards is answered at shoulder height.
    'no_wall_driving_hazard': sorted(
        s2 for s2, h in halls.items()
        if all(w['placed_by'] != 'hazard' for w in h['walls'].values())),
    # RECORDED / DERIVED / SCHEMATIC, after the Locator.X rooms module
    # (Apache-2.0, the same foundation): nothing is stated that the source
    # does not support. No room here is RECORDED - nothing was surveyed.
    'provenance': {
        'geometry': 'SCHEMATIC',
        'finish': 'DERIVED',
        'wall': 'DERIVED',
        # The catalogue entries themselves are AUTHORED: someone wrote each
        # colour, roughness and reason. What is DERIVED is the placement -
        # which hall gets which entry, read from the trade's own words.
        'catalogue': 'AUTHORED',
        'placement': 'DERIVED',
        'conditions': 'DERIVED',
        'discipline': 'RECORDED/DERIVED/SCHEMATIC tagging after the '
                      'Locator.X rooms module (Apache-2.0)',
    },
    'base_conditions': {k: {'lux': v[0], 'ach': v[1], 'noise_db': v[2],
                            'temp_c': list(v[3]), 'ppe': list(v[4])}
                        for k, v in BASE_CONDITIONS.items()},
    'hazard_conditions': {k: {'lux': v[0], 'ach': v[1], 'noise_db': v[2],
                              'temp_c': list(v[3]), 'ppe': list(v[4])}
                          for k, v in HAZARD_CONDITIONS.items()},
    'halls': halls,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'finishes.json').write_text(json.dumps(doc, indent=1) + '\n')
n_none = len(doc['no_finish_driving_hazard'])
n_wall_none = len(doc['no_wall_driving_hazard'])
print(f"surfaces registry: {len(SURFACES)} finishes and {len(WALLS)} walls over "
      f"{len(halls)} halls x {len(room_strands)} rooms in "
      f"{len(PATTERNS)} patterns; "
      f"{len(doc['hazards_in_use'])} hazard classes and "
      f"{len(doc['crafts_in_use'])} crafts in use, "
      f"{hazard_count} hazard-placed and {craft_count} craft-placed finishes, "
      f"{wall_hazard_count} hazard-placed and {wall_craft_count} craft-placed "
      f"walls, {n_none} halls with no finish-driving hazard, "
      f"{n_wall_none} with no wall-driving hazard; legibility "
      f"{counts['at_or_above_4_5']}/{counts['from_3_below_4_5']}/{counts['below_3']} "
      f"pairs at 4.5+/3-4.5/under 3 of {counts['pairs']}, {len(failing)} failing, "
      f"{len(near)} near-duplicate colours under dE {DE_THRESHOLD} "
      f"(source stamp {stamp})")
