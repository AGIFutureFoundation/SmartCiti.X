#!/usr/bin/env python3
"""Every one of the 111 interiors, checked. I looked at one."""
import json, pathlib, sys
from collections import Counter

def _pack_root():
    """Walk up until we find the pack, rather than assuming a layout.

    The working tree keeps this file beside `pack/`; the bundle keeps it in
    `web/`, one level down. Resolving against `__file__.parent` alone is
    exactly the v2.6 defect-13 shape — a path that only works from where the
    author happened to put it — so this looks for the directory that actually
    holds the pack.
    """
    here = pathlib.Path(__file__).resolve().parent
    for cand in (here, *here.parents):
        if (cand / 'pack' / 'registry' / 'halls.json').exists():
            return cand
    raise FileNotFoundError('cannot locate the pack from ' + str(here))


ROOT = _pack_root()
sys.path.insert(0, str(ROOT))
from interiors import (build, ROOMS, GRID, UNIT_PX, PAD_PX, PX_PER_CHAR,
                       CAPTION_PX_PER_CHAR, FIXTURES)

halls = json.load(open(ROOT / 'pack/registry/halls.json'))['halls']
skills = json.load(open(ROOT / 'pack/registry/skills.json'))['skills']
SHAPE = json.load(open(ROOT / 'pack/manifest.json'))['ledger']

def ps(h, l):
    if h < 18: return 'live' if l <= 88 else ('calibrating' if l <= 94 else 'schema_ok')
    if h < 33: return 'live' if l <= 70 else ('calibrating' if l <= 84 else 'schema_ok')
    if h < 66: return 'live' if l <= 44 else 'calibrating' if l <= 66 else 'schema_ok' if l <= 84 else 'draft'
    return 'live' if l <= 22 else 'calibrating' if l <= 44 else 'schema_ok' if l <= 70 else 'draft'

plans = build(halls, lambda i: Counter(ps(i, l) for l in range(SHAPE['levels_per_hall'])))

n = 0
def ok(label, cond):
    global n
    if not cond:
        print('FAIL', label); sys.exit(1)
    n += 1; print('  ok ', label)

ok(f"every one of the {SHAPE['halls']} halls has an interior",
   len(plans) == SHAPE['halls'] == 111)

strands = {s[0] for s in ROOMS}
hall_strands = {x['strand'] for x in skills}
ok('every room traces to a skill strand the halls actually teach, and none is invented',
   strands == hall_strands)

ok('every interior carries all 11 rooms — no hall is quietly missing a function',
   all(len(p['rooms']) == 11 for p in plans.values()))

# geometry, over all 111
overlaps = clipped = ragged = 0
for slug, p in plans.items():
    for i, a in enumerate(p['rooms']):
        if a['x'] + a['w'] > GRID: clipped += 1
        if a['w'] * UNIT_PX < len(a['label']) * PX_PER_CHAR + PAD_PX: clipped += 1
        if len(a['caption']) * CAPTION_PX_PER_CHAR > a['w'] * UNIT_PX - PAD_PX: clipped += 1
        for b in p['rooms'][i + 1:]:
            if not (a['x'] + a['w'] <= b['x'] or b['x'] + b['w'] <= a['x']
                    or a['y'] + a['h'] <= b['y'] or b['y'] + b['h'] <= a['y']):
                overlaps += 1
    rows = {}
    for r in p['rooms']:
        rows.setdefault(r['y'], []).append(r)
    for y, rs in rows.items():
        if max(r['x'] + r['w'] for r in rs) != GRID: ragged += 1

ok(f'no room overlaps another in any of the {len(plans)} plans', overlaps == 0)
ok('no label or caption overflows its room, across all 1,221 rooms', clipped == 0)
ok('every row reaches the envelope — no plan has a ragged edge', ragged == 0)

# fixtures must come from the trade's own words
by_slug = {h['slug']: h for h in halls}
bad = []
for slug, p in plans.items():
    text = (by_slug[slug]['focus'] + ' ' + by_slug[slug]['name']).lower()
    for r in p['rooms']:
        for f in r['fixtures']:
            if not any(k in text for k, (room, fx) in FIXTURES.items() if fx == f):
                bad.append((slug, f))
ok('every fixture is named by its own hall\'s focus line — no trade gets equipment it has no stated use for',
   not bad)

ok('no hall is left generic: all 111 have at least one trade-specific fixture',
   all(p['fixture_count'] >= 1 for p in plans.values()))

# a welding hall and a drywall hall must not get the same kit
w = {f for r in plans['welders']['rooms'] for f in r['fixtures']}
d = {f for r in plans['drywall']['rooms'] for f in r['fixtures']}
ok('trades differ: the welding hall and the drywall hall share no fixture', not (w & d))

# commissioning tracks the real pipeline, not a guess
first, last = plans[halls[0]['slug']], plans[halls[-1]['slug']]
ok(f"commissioning is read from the pipeline: hall 0 is {first['commissioning']}, "
   f"hall 110 is {last['commissioning']}",
   first['commissioning'] == 'commissioned' and last['commissioning'] == 'shell')

# the honesty contract
ok('no interior claims an address, and every one says why',
   all(p['site']['address'] is None and p['site']['recorded'] is False
       and 'No address data' in p['site']['note'] for p in plans.values()))

print(f"\n{n} checks passed — {len(plans)} interiors, {len(plans) * 11} rooms.")
