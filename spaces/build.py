#!/usr/bin/env python3
"""Custom training spaces: purpose-built rooms a union or a programme declares,
composed ONLY from assets this bundle already holds.

A space is a plain AUTHORED declaration under spaces/authored/<id>.json: a
title, one sentence of purpose, the unions it serves, the strand whose room it
would stand in, a footprint in metres, a floor and a wall finish, and a list of
placed items. Everything else in spaces/registry/spaces.json is DERIVED here,
from the registry that owns each fact:

  - every item id resolves in its owning registry, by name, or the build
    fails naming spaces/authored/<file>#items[i].id (fail closed);
  - the footprint fits inside the room of that strand in EVERY serving hall's
    plan, read from web/interiors.py exactly as web/build_3d.py lays it out
    (12 grid units wide, 3 m per unit) - a space larger than that room fails
    by name;
  - an item's footprint is the x by z of the size_m props/ declares for it,
    turned by its rotation; an item whose registry declares no footprint is
    recorded as "footprint unknown, overlap not checked" rather than guessed;
  - no two known footprints overlap and every known footprint lies inside the
    space; an item with no footprint is checked as a point;
  - the PPE is never typed: it is the strand's base_conditions PPE plus the
    hazard_conditions PPE of every hazard the surfaces rules say the chosen
    finishes stand for in that strand's room; a hazard prop placed in a space
    whose finishes derive none of the hazards it is keyed to fails by name;
  - the cost is summed only from figures the registries declare (tri_budget
    per prop, one draw call per pooled material); a kind that declares no
    figure is listed as not-estimated by name.

None of these spaces is built into the 3D world. They are declared, not yet
walkable, and no dimension here is a measurement of a real venue.
"""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'web'))
from interiors import plan_for, ROOMS  # noqa: E402  (read only)

KINDS = ('prop', 'furniture', 'seat', 'station', 'crib', 'sign')
ROTATIONS = (0, 90, 180, 270)
NOT_WALKABLE = ('declared, not yet walkable: an AUTHORED proposal composed '
                'from this bundle\'s own assets; nothing here is built into '
                'the 3D world, no dimension is a measurement of a real venue, '
                'and no duration, price or accreditation is stated')


def load(rel):
    return json.load(open(ROOT / rel))


manifest = load('pack/manifest.json')
props_reg = load('props/registry/props.json')
surfaces = load('surfaces/registry/finishes.json')
labels = load('labels/registry/labels.json')
sims = load('sims/registry/sims.json')
stations = load('stations/registry/stations.json')
cribs = load('tools/registry/toolcribs.json')
unions = load('unions/registry/unions.json')
halls = load('pack/registry/halls.json')['halls']

# --------------------------------------------------------------- lookups --
# One table per kind, keyed by the id the declaration uses. Each row keeps
# only what the build reads: a name, and a footprint when the registry
# declares one (props/ size_m is [x, y-height, z]; the floor footprint is x
# by z). Kinds whose registry declares no size stay footprint-less.
LOOKUP = {
    'prop': {p['id']: p for p in props_reg['props']},
    'furniture': {p['id']: p for p in props_reg['crib_furniture']['pieces']},
    'seat': {k: v for k, v in sims['sims'].items()},
    'station': {s['station_id']: s for s in stations['stations']},
    'crib': {k: v for k, v in cribs['cribs'].items()},
    'sign': {k: v for k, v in labels['kinds'].items()},
}
REGISTRY_OF = {
    'prop': 'props/registry/props.json#props',
    'furniture': 'props/registry/props.json#crib_furniture.pieces',
    'seat': 'sims/registry/sims.json#sims',
    'station': 'stations/registry/stations.json#stations',
    'crib': 'tools/registry/toolcribs.json#cribs',
    'sign': 'labels/registry/labels.json#kinds',
}
UNION_BY_SLUG = {u['slug']: u for u in unions['unions']}
HALL_BY_SLUG = {h['slug']: h for h in halls}
STRANDS = [r[0] for r in ROOMS]
ROOM_LABEL = {r[0]: r[1] for r in ROOMS}
HAZARD_PROPS = props_reg['hazard_props']['props']
UNIT_M = 3  # web/interiors.py: envelope unit_m; asserted below against the plan


def name_of(kind, id_):
    row = LOOKUP[kind][id_]
    if kind in ('prop', 'furniture', 'seat', 'crib'):
        return row['name']
    if kind == 'station':
        return row['name']
    return row['what']  # a sign kind names what it marks


def footprint_of(kind, id_, rotation):
    """(w, d) in metres on the floor, or None when the registry declares none."""
    if kind in ('prop', 'furniture'):
        size = LOOKUP[kind][id_]['size_m']
        w, d = float(size[0]), float(size[2])
        return (d, w) if rotation in (90, 270) else (w, d)
    return None


def hall_level_states(slug):
    doc = load(f'pack/registry/halls/{slug}.json')
    c = {'live': 0, 'calibrating': 0, 'schema_ok': 0, 'draft': 0}
    for lv in doc['levels']:
        c[lv['state']] += 1
    return c


def room_envelope(slug, strand):
    """The room of this strand in this hall's plan, in metres, exactly as the
    3D builder lays it out (web/build_3d.py -> interiors.build -> plan_for)."""
    per_level = manifest['ledger']['slots_per_level'] * manifest['ledger']['variants_per_lesson']
    states = {k: v * per_level for k, v in hall_level_states(slug).items()}
    plan = plan_for(HALL_BY_SLUG[slug], states)
    assert plan['envelope']['unit_m'] == UNIT_M, 'interiors unit_m moved'
    for r in plan['rooms']:
        if r['strand'] == strand:
            return {'hall': slug, 'strand': strand, 'label': r['label'],
                    'w_m': r['w'] * UNIT_M, 'd_m': r['h'] * UNIT_M}
    raise KeyError(f'{slug} plan has no room for strand {strand}')


def hazards_for(strand, floor, wall):
    """Which hazards the surfaces rules say these finishes stand for, in a
    room of this strand. A finish placed by hazard is the surfaces pack's
    own record of that hazard; a finish only ever placed by function or
    craft derives none."""
    out = []
    for hazard, rooms in surfaces['rules']['hazard_rooms'].items():
        if strand in rooms and rooms[strand] == floor:
            out.append({'hazard': hazard, 'from': 'floor', 'finish': floor,
                        'rule': f'surfaces rules.hazard_rooms.{hazard}.{strand} = {floor}'})
    for hazard, rooms in surfaces['rules']['hazard_walls'].items():
        if strand in rooms and rooms[strand] == wall:
            out.append({'hazard': hazard, 'from': 'wall', 'finish': wall,
                        'rule': f'surfaces rules.hazard_walls.{hazard}.{strand} = {wall}'})
    return out


def overlaps(a, b):
    """Two axis-aligned rectangles (x0, y0, x1, y1) overlap when they share
    area; a shared edge is not an overlap."""
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def r3(x):
    return round(x + 0.0, 3)


def build_space(path):
    where = f'spaces/authored/{path.name}'
    decl = json.load(open(path))
    for key in ('id', 'title', 'purpose', 'unions', 'strand', 'footprint_m',
                'floor', 'wall', 'items', 'provenance'):
        if key not in decl:
            raise KeyError(f'{where} lacks {key}')
    if decl['id'] != path.stem:
        raise KeyError(f'{where}#id {decl["id"]!r} is not the file name')
    if decl['provenance'] != 'AUTHORED':
        raise KeyError(f'{where}#provenance must be AUTHORED')
    for slug in decl['unions']:
        if slug not in UNION_BY_SLUG:
            raise KeyError(f'{where}#unions names {slug!r}, not in unions/registry/unions.json')
    if decl['strand'] not in STRANDS:
        raise KeyError(f'{where}#strand {decl["strand"]!r} is not a room strand in web/interiors.py')
    if decl['floor'] not in surfaces['catalogue']:
        raise KeyError(f'{where}#floor {decl["floor"]!r} is not in surfaces catalogue')
    if decl['wall'] not in surfaces['wall_catalogue']:
        raise KeyError(f'{where}#wall {decl["wall"]!r} is not in surfaces wall_catalogue')
    W, D = float(decl['footprint_m']['w']), float(decl['footprint_m']['d'])
    if not (W > 0 and D > 0):
        raise KeyError(f'{where}#footprint_m must be positive')

    # the room this space would stand in, in every serving hall's own plan
    envelopes = [room_envelope(slug, decl['strand']) for slug in decl['unions']]
    for env in envelopes:
        fits = (W <= env['w_m'] and D <= env['d_m']) or (D <= env['w_m'] and W <= env['d_m'])
        if not fits:
            raise KeyError(
                f'{where}#footprint_m {W}x{D} m does not fit the '
                f'{env["label"]} of {env["hall"]} ({env["w_m"]}x{env["d_m"]} m), '
                f'the room web/build_3d.py lays out for strand {decl["strand"]}')

    items, rects = [], []
    for i, it in enumerate(decl['items']):
        tag = f'{where}#items[{i}]'
        for key in ('kind', 'id', 'x', 'y', 'rotation'):
            if key not in it:
                raise KeyError(f'{tag} lacks {key}')
        kind, id_ = it['kind'], it['id']
        if kind not in KINDS:
            raise KeyError(f'{tag}.kind {kind!r} is not one of {KINDS}')
        if id_ not in LOOKUP[kind]:
            raise KeyError(f'{tag}.id {id_!r} is not in {REGISTRY_OF[kind]}')
        if it['rotation'] not in ROTATIONS:
            raise KeyError(f'{tag}.rotation {it["rotation"]!r} is not one of {ROTATIONS}')
        x, y = float(it['x']), float(it['y'])
        fp = footprint_of(kind, id_, it['rotation'])
        row = {'i': i, 'kind': kind, 'id': id_, 'name': name_of(kind, id_),
               'registry': REGISTRY_OF[kind], 'x': r3(x), 'y': r3(y),
               'rotation': it['rotation']}
        if fp is None:
            row['footprint'] = None
            row['footprint_note'] = 'footprint unknown, overlap not checked'
            rect = (x, y, x, y)
        else:
            row['footprint'] = {'w': r3(fp[0]), 'd': r3(fp[1]),
                                'from': f'{REGISTRY_OF[kind]}[{id_}].size_m'}
            rect = (x - fp[0] / 2, y - fp[1] / 2, x + fp[0] / 2, y + fp[1] / 2)
        row['rect'] = [r3(v) for v in rect]
        if not (rect[0] >= 0 and rect[1] >= 0 and rect[2] <= W and rect[3] <= D):
            raise KeyError(
                f'{tag} ({kind} {id_}) lies outside the {W}x{D} m footprint: '
                f'rect {[r3(v) for v in rect]}')
        for j, other in enumerate(rects):
            if other is not None and fp is not None and overlaps(rect, other):
                raise KeyError(
                    f'{tag} ({kind} {id_}) overlaps items[{j}] '
                    f'({items[j]["kind"]} {items[j]["id"]})')
        rects.append(rect if fp is not None else None)
        items.append(row)

    # hazards and PPE - derived, never typed
    hazards = hazards_for(decl['strand'], decl['floor'], decl['wall'])
    hazard_ids = sorted({h['hazard'] for h in hazards})
    ppe = set(surfaces['base_conditions'][decl['strand']]['ppe'])
    for h in hazard_ids:
        ppe.update(surfaces['hazard_conditions'][h]['ppe'])
    ppe = sorted(ppe)
    hazard_props_placed = []
    for row in items:
        if row['kind'] == 'prop' and row['id'] in HAZARD_PROPS:
            rule = HAZARD_PROPS[row['id']]
            keyed = rule['triggered_by_hazards']
            if rule['ppe_any'] == ['*any*']:
                admitted = len(ppe) > 0
                why = 'props hazard_props: admitted when the PPE set is non-empty'
            else:
                admitted = any(h in hazard_ids for h in keyed) and any(p in ppe for p in rule['ppe_any'])
                why = (f'props hazard_props: keyed to {keyed}, ppe_any {rule["ppe_any"]}')
            if not admitted:
                raise KeyError(
                    f'{where}#items[{row["i"]}] hazard prop {row["id"]!r} is keyed to '
                    f'{keyed} with ppe_any {rule["ppe_any"]}, but the finishes derive '
                    f'hazards {hazard_ids} and PPE {ppe}')
            hazard_props_placed.append({'i': row['i'], 'id': row['id'], 'keyed_to': keyed,
                                        'ppe_any': rule['ppe_any'], 'admitted_by': why})

    # cost - only what the registries declare
    tris, materials, not_estimated = 0, set(), []
    own_mesh, instanced = 0, set()
    for row in items:
        if row['kind'] in ('prop', 'furniture'):
            p = LOOKUP[row['kind']][row['id']]
            tris += p['tri_budget']['tris']
            if p['merges'] == 'pooled':
                materials.add(p['material'])
            elif p['merges'] == 'own-mesh':
                own_mesh += 1
            else:
                instanced.add(row['id'])
        else:
            not_estimated.append({'i': row['i'], 'kind': row['kind'], 'id': row['id'],
                                  'why': f'{REGISTRY_OF[row["kind"]]} declares no triangle figure'})
    draw_calls = len(materials) + own_mesh + len(instanced)
    by_kind = {k: sum(1 for r in items if r['kind'] == k) for k in KINDS}

    floor_row = surfaces['catalogue'][decl['floor']]
    wall_row = surfaces['wall_catalogue'][decl['wall']]
    return {
        'id': decl['id'], 'title': decl['title'], 'purpose': decl['purpose'],
        'unions': [{'slug': s, 'name': UNION_BY_SLUG[s]['name'],
                    'district': UNION_BY_SLUG[s]['district']} for s in decl['unions']],
        'strand': decl['strand'], 'room_label': ROOM_LABEL[decl['strand']],
        'footprint_m': {'w': r3(W), 'd': r3(D), 'area_m2': r3(W * D)},
        'fits_in': envelopes,
        'floor': {'id': decl['floor'], 'name': floor_row['name'], 'color': floor_row['color'],
                  'pattern': floor_row['pattern']},
        'wall': {'id': decl['wall'], 'name': wall_row['name'], 'color': wall_row['color'],
                 'pattern': wall_row['pattern'], 'wainscot': wall_row['wainscot']},
        'items': items,
        'hazards': hazards,
        'ppe': {'required': ppe,
                'base_from': f'surfaces base_conditions.{decl["strand"]}.ppe',
                'hazards_from': [f'surfaces hazard_conditions.{h}.ppe' for h in hazard_ids],
                'hazard_props_placed': hazard_props_placed,
                'provenance': 'DERIVED'},
        'cost': {'tris': tris, 'draw_calls': draw_calls,
                 'pooled_materials': sorted(materials),
                 'own_mesh': own_mesh, 'instanced': len(instanced),
                 'estimated_items': len(items) - len(not_estimated),
                 'not_estimated': not_estimated,
                 'how': ('tris = sum of props tri_budget.tris over prop and furniture items; '
                         'draw_calls = one per distinct material among pooled items, plus one '
                         'per own-mesh item and one per distinct instanced id (props page_contract); '
                         'seats, stations, cribs and signs declare no figure and are not estimated'),
                 'provenance': 'DERIVED'},
        'counts': {'items': len(items), 'by_kind': by_kind,
                   'footprint_known': sum(1 for r in items if r['footprint'] is not None),
                   'footprint_unknown': sum(1 for r in items if r['footprint'] is None)},
        'status': 'declared, not yet walkable',
        'provenance': {'declaration': 'AUTHORED', 'names': 'DERIVED', 'fits_in': 'DERIVED',
                       'footprints': 'DERIVED', 'ppe': 'DERIVED', 'cost': 'DERIVED'},
        'source': where,
    }


def main():
    authored = sorted((HERE / 'authored').glob('*.json'))
    if not authored:
        raise KeyError('spaces/authored holds no declaration')
    spaces = [build_space(p) for p in authored]
    ids = [s['id'] for s in spaces]
    if len(set(ids)) != len(ids):
        raise KeyError(f'duplicate space id in {ids}')
    stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
    authored_stamp = hashlib.sha256(b''.join(p.read_bytes() for p in authored)).hexdigest()[:16]
    by_kind = {k: sum(s['counts']['by_kind'][k] for s in spaces) for k in KINDS}
    unions_served = sorted({u['slug'] for s in spaces for u in s['unions']})
    ppe_items = sorted({p for s in spaces for p in s['ppe']['required']})
    reg = {
        'pack': 'smartcitix-trade-craft-academy-spaces',
        'product': manifest['product'],
        'pack_version': manifest['pack_version'],
        'source_stamp': stamp,
        'authored_stamp': authored_stamp,
        'status': 'declared, not yet walkable',
        'honesty': {
            'status': NOT_WALKABLE,
            'composed_only_from': sorted(set(REGISTRY_OF.values())) + [
                'surfaces/registry/finishes.json#catalogue',
                'surfaces/registry/finishes.json#wall_catalogue'],
            'envelope': ('a space must fit the room of its strand in every serving hall, '
                         'read from web/interiors.py plan_for exactly as web/build_3d.py lays '
                         f'it out ({UNIT_M} m per grid unit); the room is a functional programme, '
                         'not a survey of a building'),
            'ppe': ('never typed: strand base PPE plus the PPE of every hazard the surfaces '
                    'rules say the chosen floor and wall stand for in that strand\'s room; a '
                    'hazard prop is admitted only when the finishes already derive a hazard '
                    'it is keyed to'),
            'cost': 'a prediction summed from declared per-piece figures, not a measurement',
            'footprints': ('an item with no size_m in its registry is recorded as footprint '
                           'unknown and its overlap is not checked; nothing is assumed'),
            'not_stated': 'no duration, price, accreditation or venue',
        },
        'provenance': {'declarations': 'AUTHORED', 'everything_else': 'DERIVED',
                       'colours': 'AUTHORED (surfaces catalogue, copied by id)'},
        'units': {'metres': 'x, y are the item centre from the space\'s bottom-left corner; '
                            'rotation in degrees, 90/270 swap the footprint axes',
                  'grid_unit_m': UNIT_M},
        'kinds': list(KINDS),
        'registry_of': REGISTRY_OF,
        'counts': {
            'spaces': len(spaces),
            'items': sum(s['counts']['items'] for s in spaces),
            'items_by_kind': by_kind,
            'unions_served': len(unions_served),
            'ppe_items': len(ppe_items),
            'hazards': len({h['hazard'] for s in spaces for h in s['hazards']}),
            'cost_estimated_items': sum(s['cost']['estimated_items'] for s in spaces),
            'cost_not_estimated_items': sum(len(s['cost']['not_estimated']) for s in spaces),
            'footprint_known': sum(s['counts']['footprint_known'] for s in spaces),
            'footprint_unknown': sum(s['counts']['footprint_unknown'] for s in spaces),
            'tris': sum(s['cost']['tris'] for s in spaces),
            'draw_calls': sum(s['cost']['draw_calls'] for s in spaces),
            'area_m2': r3(sum(s['footprint_m']['area_m2'] for s in spaces)),
        },
        'unions_served': unions_served,
        'ppe_items': ppe_items,
        'spaces': spaces,
    }
    out = HERE / 'registry' / 'spaces.json'
    text = json.dumps(reg, indent=1, sort_keys=True) + '\n'
    if '--check' in sys.argv:
        if not out.exists() or out.read_text() != text:
            print('STALE: spaces/registry/spaces.json  run: python3 spaces/build.py')
            sys.exit(1)
        print('spaces/registry/spaces.json is current')
        return
    out.write_text(text)
    c = reg['counts']
    print(f'spaces/registry/spaces.json: {c["spaces"]} spaces, {c["items"]} items, '
          f'{c["unions_served"]} unions served, {c["ppe_items"]} PPE items, '
          f'{c["tris"]} tris / {c["draw_calls"]} draw calls estimated over '
          f'{c["cost_estimated_items"]} items ({c["cost_not_estimated_items"]} not estimated) '
          f'| stamp {stamp}')


if __name__ == '__main__':
    main()
