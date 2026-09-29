#!/usr/bin/env python3
"""Flora pack: regional vegetation and street detail for the parish, Bay and Unspoken Smiles worlds.

Reads the AUTHORED declaration flora/authored/flora.json and writes flora/registry/flora.json for
web/florakit.py. Species are real regional plants named generally (live oak, bald cypress, sabal palmetto,
crape myrtle, marsh grass, cattail; coast live oak, eucalyptus, Monterey cypress, redwood, coastal scrub,
salt marsh grass; generic park / schoolyard trees for the Unspoken Smiles district). Heights, crowns, colours,
densities and placement rules are AUTHORED set dressing - no survey, count or location claim.

Fail closed (each error is named):
  FLORA-FIELD   a missing field (no defaults anywhere)
  FLORA-FAMILY  a species or detail refers to an unknown mesh family / a family has an unknown shape
  FLORA-REGION  a rule / mix names a species of another region, or an unknown land use / water class
  FLORA-COVER   a (land use, water class) pair of a region matches no rule, or a land use has no detail rule
  FLORA-RANGE   a height / crown range is empty or not positive, a colour is not #RRGGBB, a weight <= 0
  FLORA-BUDGET  sum(cap x tris) over the families exceeds budgets.tris_max, or families > draw_calls_max

    python3 flora/build.py            write the registry
    python3 flora/build.py --check    exit 1 if the registry is stale
"""
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
INPUTS = ['flora/build.py', 'flora/authored/flora.json']
OUT = HERE / 'registry' / 'flora.json'
SHAPES = {'trunk4+icosa': 28, 'trunk4+cone6': 14, 'trunk4+fronds6': 20, 'drape3': 6, 'octa': 8, 'blades3': 6, 'box5': 10}
WATER = ('shore', 'near', 'far')
LC_CODES = ['10', '20', '30', '40', '50', '60', '70', '80', '90', '95', '100']   # ESA WorldCover 2021 v200 class codes
HEX = re.compile(r'^#[0-9a-fA-F]{6}$')


class FloraBuildError(Exception):
    pass


def need(obj, key, where):
    if not isinstance(obj, dict) or key not in obj:
        raise FloraBuildError(f'FLORA-FIELD {where}: missing field "{key}"')
    return obj[key]


def rng(v, where):
    if not (isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v) and 0 < v[0] <= v[1]):
        raise FloraBuildError(f'FLORA-RANGE {where}: {v!r} is not a positive [min, max] range')
    return v


def colour(v, where):
    if not isinstance(v, str) or not HEX.match(v):
        raise FloraBuildError(f'FLORA-RANGE {where}: colour {v!r} is not #RRGGBB')
    return v


def stamp():
    h = hashlib.sha256()
    for rel in INPUTS:
        p = ROOT / rel
        if not p.exists():
            raise FloraBuildError(f'FLORA-FIELD missing input {rel}')
        h.update(rel.encode() + b'\0' + p.read_bytes() + b'\0')
    return h.hexdigest()[:16]


def build():
    src = json.loads((ROOT / 'flora/authored/flora.json').read_text(encoding='utf-8'))
    for k in ('schema', 'provenance', 'honesty', 'families', 'budgets', 'species', 'moss', 'regions', 'details'):
        need(src, k, 'flora.json')
    if src['provenance'] != 'AUTHORED':
        raise FloraBuildError('FLORA-FIELD flora.json: provenance must be AUTHORED')
    for k in ('species', 'placement', 'details', 'page_line'):
        need(src['honesty'], k, 'honesty')
    bud = src['budgets']
    for k in ('draw_calls_max', 'tris_max', 'refill_m', 'sample_m', 'chunks_per_tick', 'water_lattice_m', 'kerb_probe_m', 'shore_m', 'near_m'):
        if not isinstance(need(bud, k, 'budgets'), (int, float)) or bud[k] <= 0:
            raise FloraBuildError(f'FLORA-RANGE budgets.{k}: must be a positive number')
    fams = {}
    for fid, f in src['families'].items():
        for k in ('shape', 'tris', 'material', 'lod_m', 'cap'):
            need(f, k, f'families.{fid}')
        if f['shape'] not in SHAPES:
            raise FloraBuildError(f'FLORA-FAMILY families.{fid}: unknown shape {f["shape"]!r}')
        if f['tris'] != SHAPES[f['shape']]:
            raise FloraBuildError(f'FLORA-FAMILY families.{fid}: tris {f["tris"]} != shape {f["shape"]} ({SHAPES[f["shape"]]})')
        if f['material'] not in ('solid', 'double'):
            raise FloraBuildError(f'FLORA-FAMILY families.{fid}: material {f["material"]!r}')
        fams[fid] = dict(f)
    if len(fams) > bud['draw_calls_max']:
        raise FloraBuildError(f'FLORA-BUDGET {len(fams)} families > draw_calls_max {bud["draw_calls_max"]}')
    worst = sum(f['cap'] * f['tris'] for f in fams.values())
    if worst > bud['tris_max']:
        raise FloraBuildError(f'FLORA-BUDGET worst-case triangles {worst} > tris_max {bud["tris_max"]}')
    species = {}
    for sid, s in src['species'].items():
        for k in ('name', 'region', 'family', 'height_m', 'crown_m', 'colour', 'moss_near_water'):
            need(s, k, f'species.{sid}')
        if s['family'] not in fams or s['family'] in ('moss', 'detail'):
            raise FloraBuildError(f'FLORA-FAMILY species.{sid}: family {s["family"]!r} is not a plant family')
        if s['region'] not in src['regions']:
            raise FloraBuildError(f'FLORA-REGION species.{sid}: unknown region {s["region"]!r}')
        rng(s['height_m'], f'species.{sid}.height_m'); rng(s['crown_m'], f'species.{sid}.crown_m')
        colour(s['colour'], f'species.{sid}.colour')
        species[sid] = dict(s)
    moss = src['moss']
    for k in ('name', 'colour', 'on', 'water'):
        need(moss, k, 'moss')
    colour(moss['colour'], 'moss.colour')
    for sid in moss['on']:
        if sid not in species or species[sid]['family'] != 'broadleaf':
            raise FloraBuildError(f'FLORA-FAMILY moss.on: {sid!r} is not a broadleaf species')
    for w in moss['water']:
        if w not in WATER:
            raise FloraBuildError(f'FLORA-REGION moss.water: unknown water class {w!r}')
    details = {}
    for did, d in src['details'].items():
        for k in ('name', 'setback_m', 'boxes'):
            need(d, k, f'details.{did}')
        if not d['boxes']:
            raise FloraBuildError(f'FLORA-RANGE details.{did}: no boxes')
        for i, b in enumerate(d['boxes']):
            if not (isinstance(b, list) and len(b) == 7 and all(isinstance(x, (int, float)) for x in b[:6]) and min(b[3:6]) > 0):
                raise FloraBuildError(f'FLORA-RANGE details.{did}.boxes[{i}]: want [dx, y0, dz, w, h, d, colour]')
            colour(b[6], f'details.{did}.boxes[{i}]')
        details[did] = dict(d)
    regions = {}
    for rid, r in src['regions'].items():
        for k in ('land_uses', 'rules', 'details'):
            need(r, k, f'regions.{rid}')
        lus = r['land_uses']
        for i, rule in enumerate(r['rules']):
            for k in ('land_use', 'water', 'per_ha', 'mix'):
                need(rule, k, f'regions.{rid}.rules[{i}]')
            if rule['land_use'] != '*' and rule['land_use'] not in lus:
                raise FloraBuildError(f'FLORA-REGION regions.{rid}.rules[{i}]: unknown land use {rule["land_use"]!r}')
            if rule['water'] != '*' and rule['water'] not in WATER:
                raise FloraBuildError(f'FLORA-REGION regions.{rid}.rules[{i}]: unknown water class {rule["water"]!r}')
            if not rule['per_ha'] > 0:
                raise FloraBuildError(f'FLORA-RANGE regions.{rid}.rules[{i}]: per_ha must be > 0')
            for sid, wt in rule['mix'].items():
                if sid not in species or species[sid]['region'] != rid:
                    raise FloraBuildError(f'FLORA-REGION regions.{rid}.rules[{i}]: species {sid!r} is not a {rid} species')
                if not wt > 0:
                    raise FloraBuildError(f'FLORA-RANGE regions.{rid}.rules[{i}].mix.{sid}: weight must be > 0')
        for lu in lus:
            for w in WATER:
                if not any(ru['land_use'] in ('*', lu) and ru['water'] in ('*', w) for ru in r['rules']):
                    raise FloraBuildError(f'FLORA-COVER regions.{rid}: no rule for land use {lu!r} at water class {w!r}')
            dr = r['details'].get(lu) if isinstance(r['details'], dict) else None
            if dr is None:
                raise FloraBuildError(f'FLORA-COVER regions.{rid}.details: no detail rule for land use {lu!r}')
        for lu, dr in r['details'].items():
            if lu not in lus:
                raise FloraBuildError(f'FLORA-REGION regions.{rid}.details: unknown land use {lu!r}')
            for k in ('p_kerb', 'mix'):
                need(dr, k, f'regions.{rid}.details.{lu}')
            if not (isinstance(dr['p_kerb'], (int, float)) and 0 < dr['p_kerb'] <= 1):
                raise FloraBuildError(f'FLORA-RANGE regions.{rid}.details.{lu}.p_kerb: must be in (0, 1]')
            for did, wt in dr['mix'].items():
                if did not in details:
                    raise FloraBuildError(f'FLORA-FAMILY regions.{rid}.details.{lu}: unknown detail {did!r}')
                if not wt > 0:
                    raise FloraBuildError(f'FLORA-RANGE regions.{rid}.details.{lu}.mix.{did}: weight must be > 0')
        lc = r.get('landcover') if isinstance(r, dict) else None   # optional per region: RECORDED class -> rule | null
        if 'landcover' in r:
            if set(lc) != set(LC_CODES):
                raise FloraBuildError(f'FLORA-COVER regions.{rid}.landcover: codes {sorted(lc)} are not the WorldCover set {LC_CODES}')
            for code, lr in lc.items():
                if lr is None:
                    continue
                for k in ('per_ha', 'mix'):
                    need(lr, k, f'regions.{rid}.landcover.{code}')
                if not lr['per_ha'] > 0:
                    raise FloraBuildError(f'FLORA-RANGE regions.{rid}.landcover.{code}: per_ha must be > 0')
                for sid, wt in lr['mix'].items():
                    if sid not in species or species[sid]['region'] != rid or not wt > 0:
                        raise FloraBuildError(f'FLORA-REGION regions.{rid}.landcover.{code}: species {sid!r} is not a {rid} species (weight > 0)')
        regions[rid] = {'land_uses': list(lus), 'rules': r['rules'], 'details': r['details'], 'landcover': lc,
                        'species': sorted(s for s in species if species[s]['region'] == rid)}
    for rid in regions:
        if not regions[rid]['species']:
            raise FloraBuildError(f'FLORA-REGION regions.{rid}: no species')
    return {
        'schema': 'FLORA v1', 'provenance': 'AUTHORED', 'inputs': INPUTS, 'source_stamp': stamp(),
        'honesty': src['honesty'], 'families': fams, 'budgets': bud, 'species': species, 'moss': moss,
        'details': details, 'regions': regions,
        'counts': {'species': len(species), 'details': len(details), 'families': len(fams),
                   'worst_case_tris': worst, 'per_region': {r: len(v['species']) for r, v in regions.items()}},
    }


def main():
    try:
        reg = build()
    except FloraBuildError as e:
        print(f'flora/build.py: {e}', file=sys.stderr)
        return 2
    text = json.dumps(reg, indent=1, sort_keys=True, ensure_ascii=False) + '\n'
    if '--check' in sys.argv:
        if not OUT.exists() or OUT.read_text(encoding='utf-8') != text:
            print('flora/build.py --check: flora/registry/flora.json is stale - run python3 flora/build.py', file=sys.stderr)
            return 1
        print(f'flora registry current ({reg["source_stamp"]})')
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding='utf-8')
    print(f'wrote {OUT.relative_to(ROOT)}: {reg["counts"]["species"]} species, {reg["counts"]["details"]} details, '
          f'{reg["counts"]["families"]} families, stamp {reg["source_stamp"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
