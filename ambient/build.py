#!/usr/bin/env python3
"""Ambient pack: the living-world set dressing of the parish worlds.

Reads the AUTHORED declaration ambient/authored/ambient.json and writes
ambient/registry/ambient.json for web/ambientkit.py. Reuses first:

  - a species with reused_from takes its colour, accent, span, body, motion,
    flight heights and flock size from world/registry/world.json#fauna.<id>
    (copied, never retyped); only the behaviour numbers are AUTHORED here;
  - the land-use list is read from parishes/registry/parishes.json (every
    selected parish's map.fabric_layers.land_use, which must agree), and the
    densities must cover exactly that list - a density for a land use the
    parish fabric does not draw, or a land use with no density, fails by name;
  - the grass tint is copied from world/registry/world.json#ground.grass.grain.

Fail closed: a missing input file or field stops the build with a named
error; there are no defaults. Everything is AUTHORED ambience - no survey,
sighting, population, forecast or measurement is claimed.

    python3 ambient/build.py            write the registry
    python3 ambient/build.py --check    exit 1 if the registry is stale
"""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
INPUTS = ['ambient/build.py', 'ambient/authored/ambient.json',
          'world/registry/world.json', 'parishes/registry/parishes.json']
REUSED_FIELDS = ('color', 'accent', 'span_m', 'body', 'motion', 'height_m', 'flock')
GROUND_FIELDS = ('name', 'kind', 'cls', 'body', 'motion', 'walk_mps', 'run_mps', 'flee_m',
                 'follows', 'follow_m', 'keep_m', 'size_m', 'color', 'accent', 'span_m')
BIRD_FIELDS = ('name', 'kind', 'flush_m', 'fly_mps', 'color', 'accent', 'span_m',
               'body', 'motion', 'height_m', 'flock')
KINDS = ('grass', 'bush', 'palm', 'litter')


class AmbientBuildError(Exception):
    pass


def need(obj, key, where):
    if not isinstance(obj, dict) or key not in obj:
        raise AmbientBuildError(f'{where}: missing field "{key}"')
    return obj[key]


def load(rel):
    p = ROOT / rel
    if not p.exists():
        raise AmbientBuildError(f'missing input {rel}')
    return json.loads(p.read_text())


def land_uses(parishes):
    sel = need(need(parishes, 'selection', 'parishes.json'), 'selected', 'parishes.json#selection')
    seen = None
    for fips in sel:
        p = need(need(parishes, 'parishes', 'parishes.json'), fips, 'parishes.json#parishes')
        lu = need(need(need(p, 'map', fips), 'fabric_layers', fips + '.map'), 'land_use', fips + '.map.fabric_layers')
        if seen is None:
            seen = list(lu)
        elif sorted(seen) != sorted(lu):
            raise AmbientBuildError(f'parishes.json#{fips}.map.fabric_layers.land_use disagrees with {seen}')
    if not seen:
        raise AmbientBuildError('parishes.json: no selected parish declares a land use')
    return seen


def species(auth, world):
    fauna = need(world, 'fauna', 'world.json')
    out = {}
    for sid, s in need(auth, 'species', 'authored').items():
        where = f'ambient/authored/ambient.json#species.{sid}'
        src = need(s, 'reused_from', where)
        row = dict(s)
        if src is not None:
            f = need(fauna, src, 'world/registry/world.json#fauna')
            for k in REUSED_FIELDS:
                if k in s:
                    raise AmbientBuildError(f'{where}: "{k}" is reused from world.json#fauna.{src}; do not retype it')
                row[k] = need(f, k, f'world.json#fauna.{src}')
            row['reused_from'] = f'world/registry/world.json#fauna.{src}'
            row['provenance'] = 'appearance reused from world.json fauna; behaviour AUTHORED'
        else:
            row['provenance'] = 'AUTHORED'
        kind = need(s, 'kind', where)
        fields = GROUND_FIELDS if kind == 'ground' else BIRD_FIELDS if kind == 'bird' else None
        if fields is None:
            raise AmbientBuildError(f'{where}: kind "{kind}" is not ground or bird')
        for k in fields:
            need(row, k, where)
        if kind == 'ground' and row['cls'] not in ('pet', 'animal'):
            raise AmbientBuildError(f'{where}: cls must be pet or animal (PHYS_PEDESTRIAN_CLASSES)')
        out[sid] = row
    return out


def densities(auth, uses, spc):
    d = need(auth, 'densities_per_ha', 'authored')
    for u in d:
        if u not in uses:
            raise AmbientBuildError(f'densities_per_ha.{u}: not a land use the parish fabric draws {uses}')
    for u in uses:
        row = need(d, u, 'ambient/authored/ambient.json#densities_per_ha')
        for k in KINDS:
            v = need(row, k, f'densities_per_ha.{u}')
            if not (isinstance(v, (int, float)) and v >= 0):
                raise AmbientBuildError(f'densities_per_ha.{u}.{k}: must be a number >= 0')
        for grp, kind in (('animals', 'ground'), ('flocks', 'bird')):
            for sid, v in need(row, grp, f'densities_per_ha.{u}').items():
                if sid not in spc or spc[sid]['kind'] != kind:
                    raise AmbientBuildError(f'densities_per_ha.{u}.{grp}.{sid}: no {kind} species "{sid}"')
                if not (isinstance(v, (int, float)) and v >= 0):
                    raise AmbientBuildError(f'densities_per_ha.{u}.{grp}.{sid}: must be a number >= 0')
    return {u: d[u] for u in uses}


def main():
    auth = load('ambient/authored/ambient.json')
    world = load('world/registry/world.json')
    parishes = load('parishes/registry/parishes.json')
    uses = land_uses(parishes)
    spc = species(auth, world)
    dens = densities(auth, uses, spc)
    veg = need(auth, 'vegetation', 'authored')
    grain = need(need(need(world, 'ground', 'world.json'), 'grass', 'world.json#ground'), 'grain', 'world.json#ground.grass')
    need(veg, 'grass', 'vegetation')['tint_rgb'] = [int(c) for c in grain.split(',')]
    for k in ('wind', 'behaviour', 'budgets', 'honesty', 'litter'):
        need(auth, k, 'authored')
    budgets = auth['budgets']
    for k in ('draw_calls_max', 'meshes', 'per_chunk', 'cap', 'lod_m', 'refill_m', 'flock_size_max'):
        need(budgets, k, 'budgets')
    if len(budgets['meshes']) > budgets['draw_calls_max']:
        raise AmbientBuildError('budgets.meshes: more meshes than draw_calls_max')
    for k in ('grass', 'bush', 'palm', 'litter', 'animal', 'bird'):
        need(budgets['cap'], k, 'budgets.cap')
        need(budgets['lod_m'], k, 'budgets.lod_m')
    wind = auth['wind']
    for k, (lo, hi) in need(wind, 'ranges', 'wind').items():
        vals = list(need(wind, k, 'wind').values()) if k == 'amplitude_m' else [need(wind, k, 'wind')]
        for v in vals:
            if not (lo <= v <= hi):
                raise AmbientBuildError(f'wind.{k}={v} outside its range [{lo}, {hi}]')

    h = hashlib.sha256()
    for rel in INPUTS:
        h.update(rel.encode() + b'\0' + (ROOT / rel).read_bytes() + b'\0')
    stamp = h.hexdigest()
    reg = {
        'pack': 'ambient',
        'pack_version': json.loads((ROOT / 'pack' / 'manifest.json').read_text(encoding='utf-8'))['pack_version'],
        'source_stamp': stamp[:16],
        'source_stamp_sha256': stamp,
        'inputs': INPUTS,
        'provenance': {
            'species_appearance': 'reused from world/registry/world.json#fauna where reused_from is set, else AUTHORED',
            'behaviour': 'AUTHORED', 'densities': 'AUTHORED', 'vegetation': 'AUTHORED',
            'litter': 'AUTHORED', 'wind': 'AUTHORED', 'budgets': 'AUTHORED',
            'land_uses': 'parishes/registry/parishes.json#parishes.*.map.fabric_layers.land_use (AUTHORED fabric)'},
        'world_fauna_honesty': need(need(world, 'honesty', 'world.json'), 'fauna', 'world.json#honesty'),
        'note': need(auth, 'note', 'authored'),
        'land_uses': uses,
        'species': spc,
        'densities_per_ha': dens,
        'vegetation': veg,
        'litter': auth['litter'],
        'wind': wind,
        'behaviour': auth['behaviour'],
        'budgets': budgets,
        'honesty': auth['honesty'],
        'counts': {'species': len(spc),
                   'ground_species': sum(1 for s in spc.values() if s['kind'] == 'ground'),
                   'bird_species': sum(1 for s in spc.values() if s['kind'] == 'bird'),
                   'reused_species': sum(1 for s in spc.values() if s['reused_from']),
                   'land_uses': len(uses), 'litter_types': len(auth['litter']),
                   'vegetation_types': len(veg), 'meshes': len(budgets['meshes'])},
    }
    out = HERE / 'registry' / 'ambient.json'
    text = json.dumps(reg, indent=1, sort_keys=True, ensure_ascii=False) + '\n'
    if '--check' in sys.argv:
        if not out.exists() or out.read_text() != text:
            print('STALE: ambient/registry/ambient.json  run: python3 ambient/build.py')
            sys.exit(1)
        print('ambient/registry/ambient.json is current')
        return
    out.parent.mkdir(exist_ok=True)
    out.write_text(text)
    c = reg['counts']
    print(f'ambient/registry/ambient.json: {c["species"]} species ({c["reused_species"]} reused from world.json), '
          f'{c["land_uses"]} land uses, {c["litter_types"]} litter types, {c["meshes"]} meshes | stamp {stamp[:16]}')


if __name__ == '__main__':
    try:
        main()
    except AmbientBuildError as e:
        print('ambient/build: ' + str(e), file=sys.stderr)
        sys.exit(2)
