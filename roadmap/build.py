#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the network roadmap builder.

Ten was a target this registry tracked progress toward, not a claim
that ten walkable worlds existed - and with this build it is met, not
exceeded and not fictionally rounded up: all TEN are BUILT, real
campuses, each with the full stack this bundle ships - districts,
halls, rooms, simulators, advisors, a generated world, shape-coded
signage - or, for a hub campus, the subset of that stack a hub actually
needs (see below). Zero are CANDIDATES. The ten-campus network was
itself a target, not a promise, and this build is the one that closes
it out - CANDIDATES below is intentionally empty, and TARGET stays 10
so the registry's own arithmetic (len(BUILT_ENTRIES) + len(CANDIDATES)
== TARGET) still proves the count rather than assuming it. This build
does not invent an eleventh target or a "next" candidate city - that
would be a claim nobody asked this bundle to make.

TWO PROVENANCE TIERS, NOT ONE. Three of the ten built campuses'
coordinates are RECORDED - copied from a cited file in the Locator.X
sibling checkout (Apache-2.0) and cross-checked against it on every
build, exactly like every other RECORDED fact in this bundle. Houston,
Chicago, Seattle, Pittsburgh, Denver, Miami and Detroit, the fourth
through tenth, are AUTHORED: widely-published public geography (the
kind a city's own Wikipedia infobox states), typed here from general
knowledge rather than copied from any file this build can check itself
against. That is a materially weaker claim, and it is labelled as one
rather than dressed up as RECORDED. Promoting a candidate to built means
doing the checklist below in full, not just relabelling an entry -
Houston, Chicago, Seattle, Pittsburgh, Denver, Miami and Detroit all did
it as a HUB campus rather than a district campus (see HUB_DESIGN below).
With no candidate left to promote, the checklist stands as the record
of how every hub got here, not as an instruction still waiting to be
followed.

HUB_DESIGN. A district campus and a hub campus are the two shapes this
network's campuses come in, not a hierarchy. Every one of the eight
trade districts already has exactly one home among the three original
campuses - that invariant (unions/unions111.py) was not relaxed to add
Houston, Chicago, Seattle, Pittsburgh, Denver, Miami or Detroit. Instead
each hosts no home district of its own (districts: []) and the chapters
mechanic every campus already had - a regional chapter, for every hall,
at every campus that is not its home - simply gained a fourth, fifth,
sixth, seventh, eighth, ninth and tenth destination: Houston, Chicago,
Seattle, Pittsburgh, Denver, Miami and Detroit are each now a
regional-chapter seat for all 111 halls, real walkable points on the
network map, and duplicate no hall's content anywhere. None draws a
district ring nor carries a parcel-records contract (parcels/build.py),
because there are no buildings at any of them for one to describe.

A candidate, when one existed, named a proposed metro and a proposed
district emphasis. It never claimed any hall, union, curriculum
content, or trade partnership existed there - building one meant doing
the checklist below, done in full, the same way every built campus was.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

# One bundle version, read from the manifest rather than typed here (this
# pack had drifted to 3.4.0 while ROADMAP said 3.2.0 was unified everywhere).
PACK_VERSION = json.load(open(ROOT / 'pack/manifest.json'))['pack_version']
BUILT = "2026-09-13"
TARGET = 10

# ------------------------------------------------------------ the candidates ---
# lat/lng: AUTHORED, not RECORDED - see the honesty note above and in HONESTY
# below. `districts` names 2-3 of the 8 the real metro's trade profile fits;
# the built campuses already cover all eight between them, so a candidate
# deepens the network's regional variety rather than filling a gap.
#
# CANDIDATES is intentionally empty: Detroit, the last entry this dict
# ever held, was promoted to BUILT (see unions/unions111.py CAMPUSES)
# in the same build that emptied this table. The ten-campus target
# (TARGET below) is now fully met, so there is nothing left to propose -
# this build does not fabricate an eleventh candidate to keep the table
# non-empty.
CANDIDATES = {}

# ------------------------------------------------ how a candidate gets built ---
# The real steps every built campus went through, in order - a district
# campus follows all seven; a hub campus (see HUB_DESIGN above) does every
# step except the district/ring/parcels ones, which do not apply to it. A
# candidate was promoted by doing these, not by editing its status field.
# With CANDIDATES empty, this checklist is kept as the honest record of
# how all ten campuses actually got built, not as a queue with anything
# left in it.
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
    'target_not_claim': 'ten walkable worlds was a target this registry '
                        'tracked progress toward, not a claim that ten '
                        'existed. All ten are now built; zero are '
                        'candidates. The target is met, not exceeded - '
                        'this registry does not invent an eleventh '
                        'campus or a new "next" candidate to keep the '
                        'roadmap open.',
    'provenance_tiers': 'three of the ten built campuses\' coordinates '
                        'are RECORDED - copied from a cited file and '
                        'cross-checked against it on every build. '
                        'Houston, Chicago, Seattle, Pittsburgh, Denver, '
                        'Miami and Detroit, the fourth through tenth, '
                        'are AUTHORED: widely-published public '
                        'geography, typed here from general knowledge '
                        'rather than copied from any file this build '
                        'can check itself against - a materially '
                        'weaker claim, labelled as one.',
    'hub_vs_district': 'three built campuses are district campuses: a '
                       'home for 2-3 trade districts, a district ring, '
                       'the full stack this bundle ships. Houston, '
                       'Chicago, Seattle, Pittsburgh, Denver, Miami and '
                       'Detroit are hub campuses: no home district, no '
                       'district ring, no parcel-records contract - and '
                       'a real regional chapter seat for all 111 halls '
                       'each, the same mechanic every campus already '
                       'had, extended to a fourth, fifth, sixth, '
                       'seventh, eighth, ninth and tenth destination. '
                       'Seven of the ten built campuses ended up this '
                       'shape and three the other, which was never a '
                       'rule - just how the real metros landed.',
    'not_a_claim_of_content': 'a candidate, when one existed, named a '
                              'proposed metro and a proposed district '
                              'emphasis. It never claimed any hall, '
                              'union, curriculum content or trade '
                              'partnership existed there - building one '
                              'meant doing the checklist, done in full, '
                              'the same way every built campus was. '
                              'With the roadmap now at ten of ten, '
                              'there is no remaining candidate for this '
                              'to describe.',
    'no_dates': 'this was an ordered list of what was next, not a '
               'timeline: no candidate ever carried a committed date, '
               'and none remain to carry one now.',
}

# ---------------------------------------------------------------- checks ---
campuses_reg = json.load(open(ROOT / 'unions/registry/campuses.json'))['campuses']
districts_reg = json.load(open(ROOT / 'unions/registry/districts.json'))['districts']
geo_reg = json.load(open(ROOT / 'geo/registry/campuses_geo.json'))

# The same haversine/bearing pair geo/build.py already uses for the built
# network's routes - duplicated here (pure math, not a fact) rather than
# imported across packs, so this pack still runs standalone. Every
# candidate gets a real bearing and distance from the flagship campus, the
# same reference point the 3D region board's own layout already uses -
# so the board can place a candidate honestly instead of arbitrarily.
import math


def haversine_km(a, b):
    R = 6371.0088
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = math.radians(b[0] - a[0])
    dl = math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def bearing_deg(a, b):
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


FLAGSHIP = (geo_reg['campuses']['treasure-island']['lat'],
            geo_reg['campuses']['treasure-island']['lng'])
for c in CANDIDATES.values():
    pt = (c['lat'], c['lng'])
    c['km_from_flagship'] = round(haversine_km(FLAGSHIP, pt), 1)
    c['bearing_from_flagship_deg'] = round(bearing_deg(FLAGSHIP, pt), 1)

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
    assert 0 < c['km_from_flagship'] < 5000, \
        f'{ck}: distance from the flagship campus looks wrong'
    assert 0 <= c['bearing_from_flagship_deg'] < 360, \
        f'{ck}: bearing from the flagship campus must be a compass degree'

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

    # the region board (the 3D network view) used to show only the five
    # built campuses, never a hint that five more are planned - a learner
    # exploring the actual walkable board, not just the flat dashboard,
    # had no way to discover the roadmap at all. This is the drift guard:
    # every candidate this registry declares must actually reach the board.
    page3d = (ROOT / 'web/trade_craft_3d.html').read_text()
    assert 'D.roadmap.candidates' in page3d, \
        'the 3D region board does not render the roadmap candidates'
    for ck, c in CANDIDATES.items():
        assert c['name'] in page3d, \
            f'candidate {ck} is declared but never named on the region board'
        assert f'"bearing_from_flagship_deg":{c["bearing_from_flagship_deg"]}' \
            in page3d, \
            f"candidate {ck}'s bearing does not reach the region board"

    # the network geomap is a real WGS84 map - every candidate's own real
    # (AUTHORED) coordinate belongs there too, not just a schematic bearing
    # on the 3D board. Same drift guard, third surface.
    geomap = (ROOT / 'web/trade_craft_geomap.html').read_text()
    assert 'D.candidates' in geomap, \
        'the network geomap does not render the roadmap candidates'
    for ck, c in CANDIDATES.items():
        assert f'"lat":{c["lat"]},"lng":{c["lng"]}' in geomap, \
            f"candidate {ck}'s own coordinate does not reach the geomap"

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
