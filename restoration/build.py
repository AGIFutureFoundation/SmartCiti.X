#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the Bay Restoration pack builder.

WHAT THIS IS. A bridge between two real things that already exist
independently of this repository: the San Francisco Bay Restoration
Authority's actual, named shoreline and wetland restoration projects
(sfbayrestore.org), and this bundle's own trade-skill graph. It names
real sites and real workforce-development programs several of those
projects already run, and it points a learner at the real, existing
skills in this platform's own skill graph (`pack/registry/skills.json`)
that those field trades actually draw on — grounds work, site safety,
survey and monitoring, general laborer field skills. It does not invent
a certification, a partnership, or a hall: SmartCiti.X is not affiliated
with the San Francisco Bay Restoration Authority or any site operator
named below, certifies nothing about restoration work, and every real
workforce pathway named here (STRAW, Eco-Apprentice, Planting Justice's
youth program) is that organization's own program, run by them, not by
this platform.

PROVENANCE, honestly. This build reaches no network host — like every
other builder in this bundle — so the site list below could not be
fetched or cross-checked against sfbayrestore.org at build time; it was
typed from public search results describing that site's own published
project pages, the same AUTHORED tier (not RECORDED) the roadmap
candidates and the Houston/Chicago hub coordinates already carry in
this bundle. Coordinates are the named park or shoreline's approximate,
widely-published location — close enough to place a marker on a map at
Bay scale, not a surveyed or verified pin. A site's own project page
(linked below) is the source of truth this build cannot check itself
against; the `honesty` block says so on every surface this pack reaches.

CAMPUS GROUPING. This bundle's Bay Area presence is two real campuses:
Treasure Island–San Francisco and Oakland. Every restoration site below
is tagged with whichever of those two is nearer, for map/panel grouping
only — it is not a claim that the campus operates, funds or is adjacent
to the site.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

PACK_VERSION = "1.0.0"
BUILT = "2026-09-14"

# ---------------------------------------------------------------- sites ---
# Real, named restoration projects, AUTHORED FROM PUBLIC RECORD (search
# results describing each project's own published page) — not RECORDED,
# because this build reaches no network host to check the source live.
# `pin`: False means the project spans an area too large or diffuse for
# one honest point (a bay-wide program), so it is listed but not mapped.
SITES = [
    {'id': 'herons-head', 'name': "Heron's Head Park Shoreline Resilience "
     'Project (Phases 1 and 2)',
     'org': 'Port of San Francisco; Literacy for Environmental Justice',
     'city': 'San Francisco', 'county': 'San Francisco', 'campus': 'treasure-island',
     'lat': 37.7355, 'lng': -122.3803, 'pin': True,
     'habitat': 'shoreline & green infrastructure',
     'scale': 'shoreline resilience work across two funded phases',
     'workforce': True,
     'workforce_note': "the site's own Eco-Apprentice program hires "
                       'low-income transitional-age youth (18-25) for '
                       'paid green-infrastructure job training',
     'source_url': 'https://www.sfbayrestore.org/projects/'
                   'herons-head-park-shoreline-resilience-project-phases-1-and-2'},
    {'id': 'candlestick-point', 'name': 'Candlestick Point Stewardship '
     'Project (Phases 1 and 2)',
     'org': 'California State Parks; community stewardship partners',
     'city': 'San Francisco', 'county': 'San Francisco', 'campus': 'treasure-island',
     'lat': 37.7180, 'lng': -122.3750, 'pin': True,
     'habitat': 'shoreline stewardship',
     'scale': 'trash clean-up, monitoring and native plant propagation '
              'over a two-year funded period',
     'workforce': True,
     'workforce_note': 'the project funds workforce development '
                       'training alongside its stewardship work',
     'source_url': 'https://www.sfbayrestore.org/projects/'
                   'candlestick-point-stewardship-project-phase-1-and-2'},
    {'id': 'east-oakland-youth', 'name': 'Bay Restoration: Youth '
     'Engagement and Service Learning in East Oakland',
     'org': 'Planting Justice',
     'city': 'Oakland', 'county': 'Alameda', 'campus': 'oakland',
     'lat': 37.7620, 'lng': -122.1780, 'pin': True,
     'habitat': 'shoreline & upland restoration',
     'scale': 'roughly 20 youth interns trained per the funded program',
     'workforce': True,
     'workforce_note': 'Planting Justice trains youth interns in '
                       'shoreline clean-up, invasive-plant removal and '
                       'habitat restoration technique, and in '
                       'environmental-justice issues generally',
     'source_url': 'https://www.sfbayrestore.org/projects/'
                   'bay-restoration-youth-engagement-and-service-learning-east-oakland'},
    {'id': 'alviso-shoreline', 'name': 'Alviso Shoreline Habitat '
     'Restoration',
     'org': 'Grassroots Ecology',
     'city': 'San Jose', 'county': 'Santa Clara', 'campus': 'oakland',
     'lat': 37.4266, 'lng': -121.9765, 'pin': True,
     'habitat': 'marsh-adjacent upland',
     'scale': 'approximately 2 acres restored and enhanced',
     'workforce': False, 'workforce_note': None,
     'source_url': 'https://www.sfbayrestore.org/projects/'
                   'alviso-shoreline-habitat-restoration'},
    {'id': 'south-bay-salt-ponds', 'name': 'South Bay Salt Pond '
     'Restoration — ecotone levee (Phase 1)',
     'org': 'South Bay Salt Pond Restoration Project (multi-agency)',
     'city': 'Hayward (Eden Landing)', 'county': 'Alameda', 'campus': 'oakland',
     'lat': 37.6120, 'lng': -122.1130, 'pin': True,
     'habitat': 'managed pond to tidal marsh',
     'scale': 'a 4-mile ecotone levee, first phase of restoring roughly '
              '2,900 acres of ponds to tidal marsh',
     'workforce': False, 'workforce_note': None,
     'source_url': 'https://www.southbayrestoration.org/page/'
                   'restoration-project'},
    {'id': 'montezuma-wetlands', 'name': 'Montezuma Tidal and Seasonal '
     'Wetlands Restoration Project',
     'org': 'San Francisco Bay Restoration Authority (Measure AA)',
     'city': 'Suisun Marsh', 'county': 'Solano', 'campus': 'oakland',
     'lat': 38.1500, 'lng': -121.9500, 'pin': True,
     'habitat': 'tidal & seasonal wetland, adjacent upland',
     'scale': 'roughly 630 acres of diked baylands along Montezuma Slough',
     'workforce': False, 'workforce_note': None,
     'source_url': 'https://www.sfbayrestore.org/projects/'
                   'montezuma-tidal-and-seasonal-wetlands-restoration-project'},
    {'id': 'american-canyon', 'name': 'American Canyon Wetlands '
     'Restoration Plan',
     'org': 'City of American Canyon',
     'city': 'American Canyon', 'county': 'Napa', 'campus': 'oakland',
     'lat': 38.1710, 'lng': -122.2600, 'pin': True,
     'habitat': 'wetland & upland shoreline',
     'scale': 'a plan summarizing restoration opportunities along the '
              "city's shoreline",
     'workforce': False, 'workforce_note': None,
     'source_url': 'https://www.sfbayrestore.org/projects/'
                   'american-canyon-wetlands-restoration-plan'},
    {'id': 'straw-north-bay', 'name': 'Restoring Wetland-Upland '
     'Transition Zone Habitat in the North Bay with STRAW',
     'org': 'Point Blue Conservation Science (STRAW program)',
     'city': 'North Bay (four sites)', 'county': 'Marin / Sonoma',
     'campus': 'oakland',
     'lat': 38.0500, 'lng': -122.5300, 'pin': True,
     'habitat': 'wetland-upland transition zone',
     'scale': 'roughly 1.3 linear miles of habitat across four sites '
              'over five years',
     'workforce': True,
     'workforce_note': 'STRAW (Students and Teachers Restoring a '
                       'Watershed) engages over 5,000 student and '
                       'teacher participants in the restoration work '
                       'itself — a real, existing field-science '
                       'education program, not a SmartCiti.X program',
     'source_url': 'https://www.sfbayrestore.org/projects/'
                   'restoring-wetland-upland-transition-zone-habitat-'
                   'north-bay-straw'},
    {'id': 'spartina-removal', 'name': 'San Francisco Estuary Invasive '
     'Spartina Removal',
     'org': 'San Francisco Estuary Invasive Spartina Project '
            '(multi-agency)',
     'city': 'Bay-wide', 'county': 'multiple', 'campus': None,
     'lat': None, 'lng': None, 'pin': False,
     'habitat': 'tidal marsh (invasive-species removal & revegetation)',
     'scale': 'coordinated across roughly 70,000 acres of the estuary',
     'workforce': True,
     'workforce_note': 'the project provides workforce-development '
                       'internships alongside its removal and '
                       'revegetation work',
     'source_url': 'https://www.sfbayrestore.org/'},
]

# ------------------------------------------------------- field skill tracks ---
# Three tracks, each bound to real skill_ids this bundle's own skill
# graph already ships (pack/registry/skills.json) — no restoration-only
# skill is invented. A learner who works one of these real skills at a
# trade hall is already practicing a skill the field work above draws on;
# this pack states that bridge, it does not certify restoration work.
TRACKS = [
    {'id': 'habitat-grounds', 'title': 'Habitat & grounds work',
     'what': 'native planting, invasive-species removal, erosion and '
             'shoreline stabilization work — the same hands-on grounds '
             'skills this bundle already trains',
     'skills': ['grounds.procedure.applied', 'grounds.materials.applied']},
    {'id': 'field-safety', 'title': 'Field safety & labor',
     'what': 'PPE, tidal and site hazard awareness, and the general '
             'physical field-labor skill restoration crews use every day',
     'skills': ['site-safety.safety.applied', 'laborers.procedure.applied']},
    {'id': 'survey-monitoring', 'title': 'Survey & monitoring',
     'what': 'marking control points, tracking restoration progress and '
             'documenting site conditions over time',
     'skills': ['surveyors.inspection.applied', 'survey-drone.inspection.applied']},
]

HONESTY = {
    'not_affiliated': 'SmartCiti.X : Trade Craft Academy is not '
                      'affiliated with, and does not certify, endorse '
                      'or claim to fund, any site or organization named '
                      'in this pack. Every site and program below is '
                      'real and independently run by its own listed '
                      'organization.',
    'provenance': 'this build reaches no network host, so the site list '
                  'is AUTHORED FROM PUBLIC RECORD - typed from public '
                  'search results describing each site\'s own published '
                  'project page, not RECORDED against a live fetch this '
                  'build performed itself. Coordinates are each named '
                  'site\'s approximate, widely-published location, not '
                  'a surveyed pin.',
    'no_new_skills': 'every field-work skill named here is a real '
                     'skill_id this bundle\'s own skill graph already '
                     'ships (pack/registry/skills.json) - nothing '
                     'restoration-specific is invented, and practicing '
                     'one at a trade hall is the same skill a '
                     'restoration crew actually uses',
    'campus_grouping': "each site is tagged with whichever of this "
                       "bundle's two real Bay campuses "
                       "(Treasure Island-San Francisco or Oakland) is "
                       "nearer, for grouping only - not a claim that "
                       "campus operates, funds or sits next to the site",
    'not_certification': 'nothing here certifies a learner for real '
                         'restoration field work; the real workforce '
                         'programs named (Eco-Apprentice, STRAW, '
                         "Planting Justice's youth program) are the "
                         'actual path to that, run by their own '
                         'organizations, with their own application '
                         'process - this pack only names and links them',
}

# ---------------------------------------------------------------- checks ---
skills_reg = json.load(open(ROOT / 'pack/registry/skills.json'))
skill_ids = {s['skill_id'] for s in skills_reg['skills']}
campuses_reg = json.load(open(ROOT / 'unions/registry/campuses.json'))['campuses']

assert len(SITES) >= 8, 'the site list looks too thin to be worth shipping'
assert len({s['id'] for s in SITES}) == len(SITES), 'a site id repeats'
for s in SITES:
    assert s['name'] and s['org'] and s['source_url'].startswith('https://'), \
        f"{s['id']}: needs a real name, org and https source"
    assert s['campus'] in campuses_reg or s['campus'] is None, \
        f"{s['id']}: campus grouping names an unknown campus"
    if s['pin']:
        assert s['lat'] is not None and s['lng'] is not None, \
            f"{s['id']}: has a pin but no coordinate"
        assert 36.0 < s['lat'] < 39.5 and -123.5 < s['lng'] < -121.0, \
            f"{s['id']}: coordinate falls outside the Bay Area box"
    else:
        assert s['lat'] is None and s['lng'] is None, \
            f"{s['id']}: no pin but still carries a coordinate"
    if s['workforce']:
        assert s['workforce_note'], f"{s['id']}: workforce=True needs the real note"

assert len({t['id'] for t in TRACKS}) == len(TRACKS)
for t in TRACKS:
    assert len(t['skills']) >= 2, f"{t['id']}: needs at least two bound skills"
    for sk in t['skills']:
        assert sk in skill_ids, f"{t['id']}: {sk} is not a real skill_id"

pinned = [s for s in SITES if s['pin']]

BOOTSTRAP = '--bootstrap' in __import__('sys').argv
if not BOOTSTRAP:
    geomap = (ROOT / 'web/trade_craft_geomap.html').read_text()
    assert 'D.restorationSites' in geomap, \
        'the geomap does not render the Bay Restoration sites'
    for s in pinned:
        assert s['name'] in geomap, \
            f"site {s['id']} is declared but never named on the geomap"

    page3d = (ROOT / 'web/trade_craft_3d.html').read_text()
    assert 'function openRestoration(' in page3d, \
        'the 3D app does not implement the Bay Restoration panel'
    assert 'D.restoration' in page3d, \
        'the 3D app does not trim the restoration registry into D.restoration'
    for s in SITES:
        assert s['name'] in page3d, \
            f"site {s['id']} is declared but never named in the 3D panel"
    for t in TRACKS:
        assert t['title'] in page3d, \
            f"track {t['id']} is declared but never named in the 3D panel"

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

doc = {
    'pack': 'smartcitix-trade-craft-academy-bay-restoration',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'honesty': HONESTY,
    'sites': SITES,
    'tracks': TRACKS,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'restoration.json').write_text(json.dumps(doc, indent=1) + '\n')
print(f"restoration pack: {len(SITES)} real sites ({len(pinned)} mapped), "
      f"{len(TRACKS)} field-skill tracks (source stamp {stamp})")
