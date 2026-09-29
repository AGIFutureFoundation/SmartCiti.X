#!/usr/bin/env python3
"""holodeck/ - the "SmartCiti.X Powered by AGI Corp" series of holodeck packs.

A holodeck pack is one separate module a user can pick up: a union package, the
Cognition.X K-12 pack, one of the seven paths, city life, the parish worlds, the
fleet, the living world, physics. This builder NAMES the packs; it never writes
what they contain. Every figure in registry/packs.json is COUNTED at build time
from the registry the pack names in `sources` (with that file's sha256[:16]).

Fail closed. A registry that already ships in this repo (bundles/, pack/, unions/,
sims/, lessons/, schools/, layers/, parishes/, fleet/) must be there and must carry
every field read here, or the build stops by name - there is no `.get` default and
no fallback. A registry that is new this wave (economy/, ambient/, physics/, the
paths in layers/) may be absent: its pack is then PROPOSED with every count 0,
never estimated. A pack is SHIPPING only when its content exists in the repo.

No prices, no accreditation, no partner claims: a pack is a module of play and
practice. Nothing here certifies anybody; K-12 districts stay PROPOSED partners.
"""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'holodeck/registry/packs.json'
SERIES = 'SmartCiti.X Powered by AGI Corp'
KINDS = ['union', 'k12', 'path', 'world', 'system']
PATHS = ['trades', 'k12', 'responders', 'un', 'relief', 'teachers', 'roam']


class HolodeckError(Exception):
    pass


def need(obj, key, where):
    if not isinstance(obj, dict) or key not in obj:
        raise HolodeckError(f'holodeck: {where} has no {key!r}')
    return obj[key]


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()[:16]


def load(rel):
    """A registry that already ships: missing -> the build stops."""
    p = ROOT / rel
    if not p.is_file():
        raise HolodeckError(f'holodeck: required registry {rel} is missing')
    return json.loads(p.read_text(encoding='utf-8'))


def load_new(rel):
    """A registry new this wave: absent -> None (its pack is PROPOSED with 0)."""
    p = ROOT / rel
    return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else None


def src(rel):
    return {'path': rel, 'sha256': sha(rel)}


def status_of(contents):
    return 'SHIPPING' if any(v > 0 for v in contents.values()) else 'PROPOSED'


# ------------------------------------------------------------- registries --
R_BUNDLES = 'bundles/registry/bundles.json'
R_HALLS = 'pack/registry/halls.json'
R_UNIONS = 'unions/registry/unions.json'
R_SIMS = 'sims/registry/sims.json'
R_LESSONS = 'lessons/registry/lessons.json'
R_SCHOOLS = 'schools/registry/schools.json'
R_LAYERS = 'layers/registry/layers.json'
R_PARISHES = 'parishes/registry/parishes.json'
R_FLEET = 'fleet/registry/fleet.json'
R_ECON = 'economy/registry/economy.json'
R_AMBIENT = 'ambient/registry/ambient.json'
R_PHYSICS = 'physics/registry/physics.json'

B = load(R_BUNDLES)
HALLS = {need(h, 'slug', R_HALLS) for h in need(load(R_HALLS), 'halls', R_HALLS)}
UNIONS = {need(u, 'slug', R_UNIONS) for u in need(load(R_UNIONS), 'unions', R_UNIONS)}
SIMS = set(need(load(R_SIMS), 'sims', R_SIMS))
LES = need(load(R_LESSONS), 'lessons', R_LESSONS)
SCH = load(R_SCHOOLS)
LAY = load(R_LAYERS)
PAR = load(R_PARISHES)
FLEET = load(R_FLEET)

# page targets a pack may deep-link to: (page, the kit name that page must embed, or None).
# A link is emitted only for a SHIPPING pack whose page exists and embeds that kit; otherwise
# `open` is null - the catalogue never points at a world that does not carry the pack yet.
OPEN = {
    'campus': ('web/trade_craft_3d.html', None),
    'schools': ('web/trade_craft_schools.html', None),
    'parishes': ('web/trade_craft_parishes.html', None),
    'fleet': ('web/trade_craft_fleet.html', None),
    'paths': ('web/trade_craft_parishes.html', 'pathkit'),
    'econ': ('web/trade_craft_parishes.html', 'econkit'),
    'ambient': ('web/trade_craft_parishes.html', 'ambientkit'),
    'physics': ('web/trade_craft_parishes.html', 'physkit'),
}


def open_link(key, status):
    rel, kit = OPEN[key]
    if status != 'SHIPPING':
        return None
    if not (ROOT / rel).is_file():
        raise HolodeckError(f'holodeck: deep link target {rel} does not exist')
    if kit is not None and kit not in (ROOT / rel).read_text(encoding='utf-8'):
        return None
    return rel


packs = []

# ------------------------------------------------ union packages (bundles/) --
for pid, p in need(B, 'packages', R_BUNDLES).items():
    c = need(p, 'contents', f'{R_BUNDLES} packages.{pid}')
    trades = need(c, 'trades', f'packages.{pid}.contents')
    for t in trades:
        if t not in HALLS:
            raise HolodeckError(f'holodeck: package {pid} names trade {t!r} not in {R_HALLS}')
        if t not in UNIONS:
            raise HolodeckError(f'holodeck: package {pid} names trade {t!r} not in {R_UNIONS}')
    seats = need(c, 'seats', f'packages.{pid}.contents')
    for s in seats:
        if s not in SIMS:
            raise HolodeckError(f'holodeck: package {pid} names seat {s!r} not in {R_SIMS}')
    lessons = need(c, 'lessons', f'packages.{pid}.contents')
    for ls in lessons:
        if ls not in LES:
            raise HolodeckError(f'holodeck: package {pid} names lesson {ls!r} not in {R_LESSONS}')
    cells = need(c, 'ladder_cells', f'packages.{pid}.contents')
    contents = {'trades': len(trades), 'ladder_cells': len(cells), 'seats': len(seats), 'lessons': len(lessons)}
    st = status_of(contents)
    packs.append({'id': 'union-' + pid, 'kind': 'union', 'title': need(p, 'name', f'packages.{pid}'),
                  'title_from': f'{R_BUNDLES}#packages.{pid}.name', 'status': st, 'contents': contents,
                  'requires': [], 'sources': [src(R_BUNDLES), src(R_HALLS), src(R_UNIONS), src(R_SIMS), src(R_LESSONS)],
                  'open': open_link('campus', st)})

# ------------------------------------------------ Cognition.X K-12 ---------
k12_label = need(need(need(LAY, 'layers', R_LAYERS), 'k12-unit', 'layers'), 'label', 'layers.k12-unit')
if k12_label != 'Cognition.X K-12':
    raise HolodeckError(f'holodeck: layers.k12-unit.label is {k12_label!r}, expected "Cognition.X K-12"')
units = need(SCH, 'units', R_SCHOOLS)
unit_halls = {need(u, 'hall', 'schools unit') for u in units}
stations = [s for par in need(LAY, 'parishes', R_LAYERS) for s in need(par, 'stations', 'layers parish')]
k12_st = [s for s in stations if need(s, 'layer', 'station') == 'k12-unit']
k12_lessons = [lid for lid, l in LES.items() if need(l, 'hall', f'lesson {lid}') in unit_halls]
contents = {'units': len(units), 'bands': len(need(SCH, 'bands', R_SCHOOLS)),
            'stations': len(k12_st), 'lessons': len(k12_lessons)}
st = status_of(contents)
packs.append({'id': 'cognition-x-k12', 'kind': 'k12', 'title': k12_label,
              'title_from': f'{R_LAYERS}#layers.k12-unit.label', 'status': st, 'contents': contents,
              'requires': [], 'sources': [src(R_SCHOOLS), src(R_LESSONS), src(R_LAYERS)],
              'open': open_link('schools', st)})

# ------------------------------------------------ the seven paths ----------
# layers/registry/paths.json (STORY, $SP/PATHS_CONTRACT.md v1). Absent -> every path is
# PROPOSED with 0: a path is never shipped by guessing which stations fit it.
R_PATHS = 'layers/registry/paths.json'
PTH = load_new(R_PATHS)
if PTH is not None:
    if need(PTH, 'path_ids', R_PATHS) != PATHS:
        raise HolodeckError(f'holodeck: {R_PATHS} path_ids differ from {PATHS}')
    if need(PTH, 'series', R_PATHS) != 'SmartCiti.X Powered by AGI Corp':
        raise HolodeckError(f'holodeck: {R_PATHS} series is not the holodeck series')
for pth in PATHS:
    if PTH is None:
        contents, sources, reg_status, label = {'parishes': 0, 'steps': 0, 'stories': 0}, [], 'PROPOSED', None
    else:
        entries, stories = [], 0
        for par in need(PTH, 'parishes', R_PATHS):
            fips = need(par, 'fips', 'paths parish')
            mine = [x for x in need(par, 'paths', f'paths parish {fips}') if need(x, 'id', 'path') == pth]
            if len(mine) != 1:
                raise HolodeckError(f'holodeck: parish {fips} carries {len(mine)} entries for path {pth!r}')
            entries.append(mine[0])
            stories += sum(1 for x in need(par, 'stories', f'paths parish {fips}') if need(x, 'path', 'story') == pth)
        statuses = {need(x, 'status', f'path {pth}') for x in entries}
        labels = {need(x, 'label', f'path {pth}') for x in entries}
        if len(statuses) != 1 or len(labels) != 1:
            raise HolodeckError(f'holodeck: path {pth} has mixed status {statuses} or label {labels} across parishes')
        reg_status, label = statuses.pop(), labels.pop()
        if reg_status not in ('AVAILABLE', 'PROPOSED'):
            raise HolodeckError(f'holodeck: path {pth} has unknown status {reg_status!r}')
        contents = {'parishes': len(entries), 'steps': sum(len(need(x, 'steps', f'path {pth}')) for x in entries),
                    'stories': stories}
        sources = [src(R_PATHS)]
    # the registry's own PROPOSED (the UN training module) stays PROPOSED whatever it quotes
    st = status_of(contents) if reg_status == 'AVAILABLE' else 'PROPOSED'
    packs.append({'id': 'path-' + pth, 'kind': 'path', 'title_key': f'packs.path.{pth}', 'title': label,
                  'title_from': f'{R_PATHS}#parishes[].paths[{pth}].label' if label else None, 'status': st,
                  'contents': contents, 'requires': ['parish-worlds'], 'sources': sources,
                  'open': open_link('paths', st)})

# ------------------------------------------------ worlds -------------------
parishes = need(PAR, 'parishes', R_PARISHES)
landmarks = sum(len(need(p, 'landmarks', f'parish {f}')) for f, p in parishes.items())
maps = sum(1 for f, p in parishes.items() if need(p, 'map', f'parish {f}'))
contents = {'parishes': len(parishes), 'landmarks': landmarks, 'maps': maps, 'stations': len(stations)}
st = status_of(contents)
packs.append({'id': 'parish-worlds', 'kind': 'world', 'title_key': 'packs.pack.parish-worlds', 'status': st,
              'contents': contents, 'requires': [], 'sources': [src(R_PARISHES), src(R_LAYERS)],
              'open': open_link('parishes', st)})

ECON = load_new(R_ECON)
if ECON is None:
    contents, sources = {'lots': 0, 'business_types': 0, 'rentals': 0}, []
else:
    lots = sum(len(need(p, 'lots', f'economy parish {f}')) for f, p in need(ECON, 'parishes', R_ECON).items())
    contents = {'lots': lots, 'business_types': len(need(ECON, 'business_types', R_ECON)),
                'rentals': len(need(ECON, 'rentals', R_ECON))}
    sources = [src(R_ECON)]
st = status_of(contents)
packs.append({'id': 'city-life', 'kind': 'world', 'title_key': 'packs.pack.city-life', 'status': st,
              'contents': contents, 'requires': ['parish-worlds'], 'sources': sources,
              'open': open_link('econ', st)})

# ------------------------------------------------ systems ------------------
fl = need(FLEET, 'fleet', R_FLEET)
media = [need(v, 'medium', 'fleet vehicle') for v in fl]
contents = {'vehicles': len(fl), 'land': media.count('land'), 'water': media.count('water'),
            'families': len({need(v, 'family', 'fleet vehicle') for v in fl})}
st = status_of(contents)
packs.append({'id': 'fleet', 'kind': 'system', 'title_key': 'packs.pack.fleet', 'status': st,
              'contents': contents, 'requires': [], 'sources': [src(R_FLEET)], 'open': open_link('fleet', st)})

AMB = load_new(R_AMBIENT)
if AMB is None:
    contents, sources = {'species': 0, 'land_uses': 0, 'vegetation': 0, 'litter': 0}, []
else:
    contents = {'species': len(need(AMB, 'species', R_AMBIENT)), 'land_uses': len(need(AMB, 'land_uses', R_AMBIENT)),
                'vegetation': len(need(AMB, 'vegetation', R_AMBIENT)), 'litter': len(need(AMB, 'litter', R_AMBIENT))}
    sources = [src(R_AMBIENT)]
st = status_of(contents)
packs.append({'id': 'living-world', 'kind': 'system', 'title_key': 'packs.pack.living-world', 'status': st,
              'contents': contents, 'requires': ['parish-worlds'], 'sources': sources,
              'open': open_link('ambient', st)})

PHY = load_new(R_PHYSICS)
if PHY is None:
    contents, sources = {'coefficients': 0, 'pedestrian_classes': 0}, []
else:
    contents = {'coefficients': sum(len(g) for g in need(PHY, 'coeffs', R_PHYSICS).values()),
                'pedestrian_classes': len(need(PHY, 'pedestrian_classes', R_PHYSICS))}
    sources = [src(R_PHYSICS)]
st = status_of(contents)
packs.append({'id': 'physics', 'kind': 'system', 'title_key': 'packs.pack.physics', 'status': st,
              'contents': contents, 'requires': [], 'sources': sources, 'open': open_link('physics', st)})

# ------------------------------------------------ checks + write -----------
ids = [p['id'] for p in packs]
if len(set(ids)) != len(ids):
    raise HolodeckError('holodeck: duplicate pack id')
for p in packs:
    p['series'] = SERIES
    if p['kind'] not in KINDS:
        raise HolodeckError(f'holodeck: {p["id"]} has unknown kind {p["kind"]!r}')
    for r in p['requires']:
        if r not in ids:
            raise HolodeckError(f'holodeck: {p["id"]} requires unknown pack {r!r}')
    if p['status'] == 'SHIPPING' and not p['sources']:
        raise HolodeckError(f'holodeck: {p["id"]} is SHIPPING with no source registry')

payload = {
    'pack': 'smartcitix-holodeck-packs',
    'series': SERIES,
    'source_stamp': hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16],
    'kinds': KINDS,
    'paths': PATHS,
    'honesty': {
        'contents': 'every figure is counted at build time from the registry named in sources; nothing is estimated',
        'status': 'SHIPPING only when the content exists in this repo; otherwise PROPOSED with every count 0',
        'price': 'no pack carries a price; plans stay set by the operator and payments are not live',
        'certification': 'no pack certifies, qualifies or licenses anybody; lessons stay unverified general practice',
        'partners': 'no pack names a partner; K-12 districts stay PROPOSED partners with no agreement',
    },
    'counts': {'packs': len(packs), 'shipping': sum(p['status'] == 'SHIPPING' for p in packs),
               'proposed': sum(p['status'] == 'PROPOSED' for p in packs),
               'by_kind': {k: sum(p['kind'] == k for p in packs) for k in KINDS}},
    'packs': packs,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
print(f'holodeck: {len(packs)} packs | {payload["counts"]["shipping"]} SHIPPING | '
      f'{payload["counts"]["proposed"]} PROPOSED -> {OUT.relative_to(ROOT)}')
