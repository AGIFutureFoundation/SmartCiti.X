#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the network roadmap builder.

Ten is a target this registry tracks progress toward, not a claim that
ten walkable worlds exist. Four are BUILT: real campuses, each with the
full stack this bundle ships - districts, halls, rooms, simulators,
advisors, a generated world, shape-coded signage - or, for a hub campus,
the subset of that stack a hub actually needs (see below). Six are
CANDIDATES: real US metros with real trade profiles, proposed as the
next six, and nothing more than proposed.

TWO PROVENANCE TIERS, NOT ONE. Three of the four built campuses'
coordinates are RECORDED - copied from a cited file in the Locator.X
sibling checkout (Apache-2.0) and cross-checked against it on every
build, exactly like every other RECORDED fact in this bundle. Houston,
the fourth, and the six candidates' city coordinates are AUTHORED:
widely-published public geography (the kind a city's own Wikipedia
infobox states), typed here from general knowledge rather than copied
from any file this build can check itself against. That is a materially
weaker claim, and it is labelled as one rather than dressed up as
RECORDED. Promoting a candidate to built means doing the checklist below
in full, not just relabelling an entry - Houston did it as a HUB campus
rather than a district campus (see HUB_DESIGN below); a future candidate
could go either way.

HUB_DESIGN. A district campus and a hub campus are the two shapes this
network's campuses come in, not a hierarchy. Every one of the eight
trade districts already has exactly one home among the three original
campuses - that invariant (unions/unions111.py) was not relaxed to add
Houston. Instead Houston hosts no home district of its own (districts:
[]) and the chapters mechanic every campus already had - a regional
chapter, for every hall, at every campus that is not its home - simply
gained a fourth destination: Houston is now a regional-chapter seat for
all 111 halls, a real walkable point on the network map, and duplicates
no hall's content anywhere. It draws no district ring and carries no
parcel-records contract (parcels/build.py), because there are no
buildings there for either to describe.

A candidate names a proposed metro and a proposed district emphasis. It
does NOT claim any hall, union, curriculum content, or trade partnership
exists there - building one is the checklist below, done in full, the
same way the first three were.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

PACK_VERSION = "3.2.0"
BUILT = "2026-09-12"
TARGET = 10

# ----------------------------------------------------- the seven candidates ---
# lat/lng: AUTHORED, not RECORDED - see the honesty note above and in HONESTY
# below. `districts` names 2-3 of the 8 the real metro's trade profile fits;
# the built campuses already cover all eight between them, so a candidate
# deepens the network's regional variety rather than filling a gap.
CANDIDATES = {
    'chicago': {
        'name': 'Loop Rail Campus', 'city': 'Chicago', 'region': 'Illinois',
        'lat': 41.8781, 'lng': -87.6298,
        'districts': ['structural', 'transport', 'systems'],
        'why': 'the nation\'s rail hub and a structural-steel skyline built '
               'by the trades that invented the high-rise - transport, '
               'structural and the building systems a dense downtown runs on',
    },
    'seattle': {
        'name': 'Sound Aerospace Campus', 'city': 'Seattle',
        'region': 'Washington',
        'lat': 47.6062, 'lng': -122.3321,
        'districts': ['transport', 'structural', 'industry'],
        'why': 'aerospace manufacturing and a working port on the Sound - '
               'precision heavy industry alongside the structural and '
               'transport trades a port city depends on',
    },
    'pittsburgh': {
        'name': 'Three Rivers Steel Campus', 'city': 'Pittsburgh',
        'region': 'Pennsylvania',
        'lat': 40.4406, 'lng': -79.9959,
        'districts': ['industry', 'structural', 'earthworks'],
        'why': 'the steel city, its three rivers crossed by more bridges '
               'than any other in the country - heavy industry and the '
               'structural trades it was built to teach are its own history',
    },
    'denver': {
        'name': 'Front Range Campus', 'city': 'Denver', 'region': 'Colorado',
        'lat': 39.7392, 'lng': -104.9903,
        'districts': ['earthworks', 'energy', 'control'],
        'why': 'a mining and energy heritage at altitude, and the ground, '
               'survey and safety disciplines that heritage was built on',
    },
    'miami': {
        'name': 'Biscayne Coastal Campus', 'city': 'Miami', 'region': 'Florida',
        'lat': 25.7617, 'lng': -80.1918,
        'districts': ['envelope', 'control', 'transport'],
        'why': 'hurricane-code envelope work and storm-response discipline '
               'on a coast that tests both every season, beside a working '
               'port',
    },
    'detroit': {
        'name': 'Motor City Campus', 'city': 'Detroit', 'region': 'Michigan',
        'lat': 42.3314, 'lng': -83.0458,
        'districts': ['industry', 'structural', 'systems'],
        'why': 'a century of heavy manufacturing and the machinist, '
               'structural and building-systems trades an automotive '
               'industrial base actually runs on',
    },
}

# ------------------------------------------------ how a candidate gets built ---
# The real steps every built campus went through, in order - a district
# campus follows all seven; a hub campus (see HUB_DESIGN above) does every
# step except the district/ring/parcels ones, which do not apply to it. A
# candidate is promoted by doing these, not by editing its status field.
CHECKLIST = [
    {'step': 'source real coordinates',
     'what': 'find the metro\'s city-center and any regional-institution '
             'coordinates in a citable, checkable source - the pattern '
             'geo/build.py already follows against the Locator.X checkout',
     'file': 'geo/build.py'},
    {'step': 'cross-check on every build',
     'what': 'assert the coordinate matches the cited source whenever that '
             'checkout is present, so a drifted number fails the build '
             'rather than going unnoticed',
     'file': 'geo/build.py'},
    {'step': 'add the campus and its districts',
     'what': 'register the campus, its region and its 2-3 districts in the '
             'union registry, matching real local trade profile to the '
             'existing eight-district taxonomy',
     'file': 'unions/registry/campuses.json'},
    {'step': 'assign or share halls',
     'what': 'every hall already exists once in the pack; a new campus '
             'hosts the halls its assigned districts already declare - no '
             'hall content is duplicated per campus',
     'file': 'pack/registry/halls.json'},
    {'step': 'build the 3D campus geometry',
     'what': 'the district ring, roads and green generate from the campus '
             'record automatically - buildCampus() takes a district count '
             'and a region key, not a hand-placed layout',
     'file': 'web/build_3d.py'},
    {'step': 'give it a world',
     'what': 'an authored atmosphere (sky, ground surface, character) and '
             'the fauna that belongs on that coast or that plain',
     'file': 'world/build.py'},
    {'step': 'verify, ship, publish',
     'what': 'every suite in verify_all.sh must hold, a browser harness '
             'must prove the campus walks and judges correctly, and the '
             'hosted artifact must be rebuilt and republished',
     'file': 'verify_all.sh'},
]

HONESTY = {
    'target_not_claim': 'ten walkable worlds is a target this registry '
                        'tracks progress toward, not a claim that ten '
                        'exist. Four are built; six are candidates.',
    'provenance_tiers': 'three of the four built campuses\' coordinates '
                        'are RECORDED - copied from a cited file and '
                        'cross-checked against it on every build. '
                        'Houston, the fourth, and the six candidates\' '
                        'coordinates are AUTHORED: widely-published '
                        'public geography, typed here from general '
                        'knowledge rather than copied from any file this '
                        'build can check itself against - a materially '
                        'weaker claim, labelled as one.',
    'hub_vs_district': 'three built campuses are district campuses: a '
                       'home for 2-3 trade districts, a district ring, '
                       'the full stack this bundle ships. Houston is a '
                       'hub campus: no home district, no district ring, '
                       'no parcel-records contract - and a real regional '
                       'chapter seat for all 111 halls, the same '
                       'mechanic every campus already had, extended to a '
                       'fourth destination. Building one shape does not '
                       'oblige the next candidate to be the other.',
    'not_a_claim_of_content': 'a candidate names a proposed metro and a '
                              'proposed district emphasis. It does not '
                              'claim any hall, union, curriculum content '
                              'or trade partnership exists there - '
                              'building one is the checklist, done in '
                              'full, the same way the built campuses were.',
    'no_dates': 'this is an ordered list of what is next, not a '
               'timeline: no candidate carries a committed date.',
}

# ---------------------------------------------------------------- checks ---
campuses_reg = json.load(open(ROOT / 'unions/registry/campuses.json'))['campuses']
districts_reg = json.load(open(ROOT / 'unions/registry/districts.json'))['districts']
geo_reg = json.load(open(ROOT / 'geo/registry/campuses_geo.json'))

BUILT_ENTRIES = {
    k: {'name': v['name'], 'city': v['city'], 'region': v['region'],
        'lat': geo_reg['campuses'][k]['lat'], 'lng': geo_reg['campuses'][k]['lng'],
        'districts': v['districts'], 'halls': len(v['halls']),
        'provenance': geo_reg['campuses'][k]['provenance'],
        'source': geo_reg['campuses'][k]['source']}
    for k, v in campuses_reg.items()
}

assert len(BUILT_ENTRIES) + len(CANDIDATES) == TARGET, \
    f'the network roadmap must total exactly {TARGET} campuses, ' \
    f'built plus candidate'
assert set(BUILT_ENTRIES) & set(CANDIDATES) == set(), \
    'a candidate slug collides with a built campus'

# a continental-US sanity box, loose enough to admit Alaska/Hawaii were
# never candidates but tight enough to catch a genuine typo in a coordinate
for ck, c in CANDIDATES.items():
    assert 24 < c['lat'] < 49 and -125 < c['lng'] < -66, \
        f'{ck}: coordinate falls outside a plausible continental-US box'
    assert 2 <= len(c['districts']) <= 3, \
        f'{ck}: a candidate names 2-3 districts, not more or fewer'
    assert all(d in districts_reg for d in c['districts']), \
        f'{ck}: names a district that does not exist'
    assert len(c['why']) > 40, f'{ck}: a candidate needs a real reason'

for row in CHECKLIST:
    assert (ROOT / row['file']).exists() or row['file'] in (
        'unions/registry/campuses.json', 'pack/registry/halls.json'), \
        f"checklist step \"{row['step']}\" cites a file that does not exist"

BOOTSTRAP = '--bootstrap' in __import__('sys').argv
if not BOOTSTRAP:
    dash = (ROOT / 'web/trade_craft_dashboard.html').read_text()
    assert f'{len(BUILT_ENTRIES)}<span>/{TARGET} built' in dash, \
        'the dashboard progress meter does not match the built count'
    assert f'{len(CANDIDATES)} candidates</div>' in dash, \
        'the dashboard does not render the candidate count'
    for ck in CANDIDATES:
        assert CANDIDATES[ck]['name'] in dash, \
            f'candidate {ck} is declared but not shown on the dashboard'
    for bk in BUILT_ENTRIES:
        assert BUILT_ENTRIES[bk]['name'] in dash, \
            f'built campus {bk} is declared but not shown on the dashboard'

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

doc = {
    'pack': 'smartcitix-trade-craft-academy-roadmap',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'target': TARGET,
    'honesty': HONESTY,
    'built_campuses': BUILT_ENTRIES,
    'candidates': CANDIDATES,
    'checklist': CHECKLIST,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'roadmap.json').write_text(json.dumps(doc, indent=1) + '\n')
print(f"roadmap: {len(BUILT_ENTRIES)}/{TARGET} built, "
      f"{len(CANDIDATES)} candidates (source stamp {stamp})")
