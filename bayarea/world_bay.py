#!/usr/bin/env python3
"""bayarea/world_bay.py - the WORLD LAYER of the Bay pack in PARISH_CONTRACT v1.4 format.

Writes bayarea/maps/world/<fips>.json and bayarea/registry/world.json by IMPORTING parishes/build_world.py
(build_parish, ROADS, BUILDINGS, wilds_hash, HASH_CASES) - so physkit/ambientkit/fleetkit read the same shapes.
Bay parameters (AUTHORED): no bayous (a Gulf-coast form); creeks as 'stream' and flood-control channels as
'canal'; ponds as in PARISH. San Francisco Bay, San Pablo Bay and the Pacific are OUTSIDE every land outline
(open water in the maps), so no lake stand-in is placed (no water label lies inside an outline). Run after
bayarea/build.py (build.py calls it).
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'parishes'))
import build_world as PW  # noqa: E402  parishes/build_world.py - imported, never edited

REG = ROOT / 'bayarea/registry/bayarea.json'
OUT_DIR = ROOT / 'bayarea/maps/world'
OUT_REG = ROOT / 'bayarea/registry/world.json'
N_CHANNELS = {'bayou': 0, 'canal': 2, 'stream': 5}   # AUTHORED for the Bay: creeks + flood-control channels
WATER_NOTE = 'AUTHORED water - procedural creeks, channels and ponds, NOT the real creeks or reservoirs'


def main():
    PW.N_CHANNELS = N_CHANNELS
    rb = REG.read_bytes()
    R = json.loads(rb)
    counties = PW.need(R, 'counties', 'registry')
    labels = PW.need(PW.need(R, 'water', 'registry'), 'labels', 'registry.water')
    h = hashlib.sha256()
    h.update(rb)
    srcs = {}
    for fips in sorted(counties):
        rel = PW.need(PW.need(PW.need(counties[fips], 'map', fips), 'streets', fips), 'path', fips)
        srcs[fips] = rel
        h.update((ROOT / rel).read_bytes())
    h.update(Path(__file__).read_bytes())
    h.update((ROOT / 'parishes/build_world.py').read_bytes())
    stamp = h.hexdigest()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    entries = {}
    for fips in sorted(counties):
        doc = PW.build_parish(fips, counties[fips], labels, srcs[fips])
        doc['pack'] = 'bayarea'
        doc['crs'] = 'county LOCAL metres [east_m, north_m], integers; origin = registry counties[fips].frame.origin'
        doc['water']['note'] = WATER_NOTE
        doc['buildings'] = {'mode': 'page-rule', 'see': 'bayarea/registry/world.json#buildings'}
        doc['source_stamp'] = stamp[:16]
        f = OUT_DIR / f'{fips}.json'
        f.write_text(json.dumps(doc, separators=(',', ':')) + '\n')
        size = f.stat().st_size
        if size > PW.MAX_BYTES:
            raise SystemExit(f'bay build_world: {f.name} {size} bytes over the declared budget {PW.MAX_BYTES}')
        entries[fips] = {'path': f'bayarea/maps/world/{fips}.json', 'bytes': size, 'max_bytes': PW.MAX_BYTES,
                         'sha256': PW.sha256_bytes(f.read_bytes()), 'counts': doc['counts']}
    B = dict(PW.BUILDINGS)
    B['hash_vectors'] = [{'args': list(a), 'value': PW.wilds_hash(*a)} for a in PW.HASH_CASES]
    reg = {'pack': 'bayarea', 'layer': 'world', 'version': PW.VERSION, 'format': 'PARISH_CONTRACT v1.4 world layer',
           'source_stamp': stamp, 'source_stamp_sha256': 'sha256 over bayarea/registry/bayarea.json + every '
           'bayarea/maps/streets/<fips>.json (sorted) + bayarea/world_bay.py + parishes/build_world.py',
           'water_note': WATER_NOTE, 'channels_per_kind': N_CHANNELS,
           'water_source': 'no water dataset is vendored (see parishes/registry/world.json#water_source for the '
                           'licence search); every creek, channel and pond here is AUTHORED',
           'provenance_rule': 'water AUTHORED (procedural, seeded by FIPS); the bays and ocean are open water '
                              'outside the RECORDED outlines, not modelled as lakes',
           'water_levels': {'surface_y_m': PW.SURFACE_Y_M, 'wade_max_depth_m': PW.WADE_MAX_M, 'depth_m': PW.DEPTH_M,
                            'provenance': 'AUTHORED'},
           'roads': PW.ROADS, 'buildings': B, 'counties': entries}
    OUT_REG.write_text(json.dumps(reg, indent=1) + '\n')
    print(f'bay build_world: {len(entries)} counties, {sum(e["bytes"] for e in entries.values())} bytes, '
          f'stamp {stamp[:16]}')


if __name__ == '__main__':
    main()
