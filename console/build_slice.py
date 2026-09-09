#!/usr/bin/env python3
"""The console's data slice, cut from the 111-hall pack.

The console runs the real control plane on real pack data, but it cannot hold
11,000,000 modules in a browser page — so it takes four halls and generates
their lessons the same way the pack's consumer library does. Every ledger
figure in the slice is read from the manifest rather than restated, because a
console that quotes its own numbers is one more surface that can disagree.
"""
import json, pathlib, sys


def _pack_root():
    """Walk up to the directory that holds the pack, rather than assuming a
    layout — the fixed `ROOT / 'pack'` only resolved in the pre-packaging
    tree (the v2.6 defect-13 shape)."""
    here = pathlib.Path(__file__).resolve().parent
    for cand in (here, *here.parents):
        if (cand / 'pack' / 'registry' / 'halls.json').exists():
            return cand
    raise FileNotFoundError('cannot locate the pack from ' + str(here))


HERE = pathlib.Path(__file__).resolve().parent
ROOT = _pack_root()
sys.path.insert(0, str(ROOT / 'pack'))
from build import pipeline_state, lesson_of, STRANDS, TIERS, FORMS, SLOTS, LEVELS  # noqa: E402

manifest = json.load(open(ROOT / 'pack/manifest.json'))
halls = json.load(open(ROOT / 'pack/registry/halls.json'))['halls']
skills = json.load(open(ROOT / 'pack/registry/skills.json'))['skills']
variants = json.load(open(ROOT / 'pack/registry/variants.json'))
library = json.load(open(ROOT / 'pack/registry/library.json'))

PICK = ['ironworkers', 'electricians', 'welders', 'crane-ops']
picked = [h for h in halls if h['slug'] in PICK]
assert len(picked) == 4

slice_skills = [s for s in skills if s['union'] in PICK]

# A representative lesson per hall, generated — the console generates the rest
# on demand exactly as the Academy does.
sample = [lesson_of(h['index'], 50, 55) | {'union': h['slug']} for h in picked]

L = manifest['ledger']
out = {
    'product': manifest['product'],
    'pack_version': manifest['pack_version'],
    'ledger': L,
    'authored_objects': manifest['authored_objects'],
    'generated_to_authored_ratio': manifest['generated_to_authored_ratio'],
    'honesty': manifest['honesty'],
    'counts': {'total_modules': L['total_modules'], 'by_state': manifest['by_state']},
    'unions': [{'slug': h['slug'], 'name': h['name'], 'focus': h['focus'],
                'index': h['index'], 'lessons': h['lessons'], 'modules': h['modules']}
               for h in picked],
    'skills': slice_skills,
    'variants': variants,
    'library': {'count': library['count'], 'shared': True},
    'lessons': sample,
    'shape': {'levels': LEVELS, 'slots': SLOTS},
}
json.dump(out, open(HERE / 'app_slice.json', 'w'), separators=(',', ':'))
print(f"slice: {len(picked)} halls, {len(slice_skills)} skills, "
      f"{sum(h['modules'] for h in picked):,} modules addressable in-console")
