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

TWO CATEGORIES. Nine sites are 'habitat-restoration' — real planting,
invasive-removal and shoreline-stabilization field work. Two sites are
'environmental-monitoring': Hunters Point Naval Shipyard, a real,
currently-litigated federal Superfund cleanup site on the National
Priorities List, and Former Naval Station Treasure Island (NSTI), a
real Navy BRAC/CERCLA cleanup that is NOT NPL-listed — the island this
bundle's own flagship campus scene sits on, which is exactly why this
pack cannot honestly leave it out. Neither is a habitat site or an open
park. Both carry `walkable=False` on purpose: this build never renders
either as a walkable ground scene, only as a located, clickable map
marker with a flat facts-and-citations panel, the same "flat panel
result, not a walkable scene" pattern already used for the real
elevation/aerial-imagery lookups elsewhere in this pack. Their facts
are a snapshot of public record as of September 2026 (Hunters Point
typed 14 September, NSTI 17 September) — both cleanups are still open
and will keep changing. The walkable Treasure Island CAMPUS scene is a
schematic training campus at the island's DERIVED centroid; the NSTI
entry is the real-world record of the ground it stands on, and the
two are kept distinct on every surface.

TRADE NEEDS. Every site also names `trade_needs`: real union slugs from
`unions/registry/unions.json` whose OWN registered `focus` text actually
matches that site's real field work (levee/grading work calls on
`operating-eng`; site prep, excavation support and cleanup calls on
`laborers`; survey/monitoring calls on `surveyors`; containment, decon
and disposal calls on `hazmat`). A trade is never added just because it
exists in the roster — only where the site's own cited description
calls for it.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

# One bundle version, read from the manifest rather than typed here (this
# pack had drifted to 1.0.0 while ROADMAP said 3.2.0 was unified everywhere).
PACK_VERSION = json.load(open(ROOT / 'pack/manifest.json'))['pack_version']
BUILT = "2026-09-17"

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
                   'herons-head-park-shoreline-resilience-project-phases-1-and-2',
     'category': 'habitat-restoration', 'walkable': True, 'walkable_reason': None,
     'disambiguation': None,
     'participation': False, 'participation_note': None, 'facts': [],
     # shoreline resilience work is real earthmoving/grading, done by an
     # Eco-Apprentice crew with general site-labor support
     'trade_needs': ['laborers', 'operating-eng']},
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
                   'candlestick-point-stewardship-project-phase-1-and-2',
     'category': 'habitat-restoration', 'walkable': True, 'walkable_reason': None,
     'disambiguation': None,
     'participation': False, 'participation_note': None, 'facts': [],
     # the site's own scale line names "monitoring" directly alongside
     # trash clean-up and native plant propagation
     'trade_needs': ['laborers', 'surveyors']},
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
                   'bay-restoration-youth-engagement-and-service-learning-east-oakland',
     'category': 'habitat-restoration', 'walkable': True, 'walkable_reason': None,
     'disambiguation': None,
     'participation': False, 'participation_note': None, 'facts': [],
     # youth interns doing shoreline clean-up and invasive-plant removal
     # by hand - general field-labor work, nothing heavier cited
     'trade_needs': ['laborers']},
    {'id': 'alviso-shoreline', 'name': 'Alviso Shoreline Habitat '
     'Restoration',
     'org': 'Grassroots Ecology',
     'city': 'San Jose', 'county': 'Santa Clara', 'campus': 'oakland',
     'lat': 37.4266, 'lng': -121.9765, 'pin': True,
     'habitat': 'marsh-adjacent upland',
     'scale': 'approximately 2 acres restored and enhanced',
     'workforce': False, 'workforce_note': None,
     'source_url': 'https://www.sfbayrestore.org/projects/'
                   'alviso-shoreline-habitat-restoration',
     'category': 'habitat-restoration', 'walkable': True, 'walkable_reason': None,
     'disambiguation': None,
     'participation': False, 'participation_note': None, 'facts': [],
     # the smallest funded footprint in the pack - general field labor,
     # nothing heavier cited
     'trade_needs': ['laborers']},
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
                   'restoration-project',
     'category': 'habitat-restoration', 'walkable': True, 'walkable_reason': None,
     'disambiguation': None,
     'participation': False, 'participation_note': None, 'facts': [],
     # a real 4-mile ecotone levee is heavy earthmoving/grading, with
     # survey control for the grading and general site labor throughout
     'trade_needs': ['operating-eng', 'laborers', 'surveyors']},
    {'id': 'montezuma-wetlands', 'name': 'Montezuma Tidal and Seasonal '
     'Wetlands Restoration Project',
     'org': 'San Francisco Bay Restoration Authority (Measure AA)',
     'city': 'Suisun Marsh', 'county': 'Solano', 'campus': 'oakland',
     'lat': 38.1500, 'lng': -121.9500, 'pin': True,
     'habitat': 'tidal & seasonal wetland, adjacent upland',
     'scale': 'roughly 630 acres of diked baylands along Montezuma Slough',
     'workforce': False, 'workforce_note': None,
     'source_url': 'https://www.sfbayrestore.org/projects/'
                   'montezuma-tidal-and-seasonal-wetlands-restoration-project',
     'category': 'habitat-restoration', 'walkable': True, 'walkable_reason': None,
     'disambiguation': None,
     'participation': False, 'participation_note': None, 'facts': [],
     # restoring 630 acres of diked baylands to tidal wetland means real
     # levee/grading earthmoving, with general site labor alongside it
     'trade_needs': ['operating-eng', 'laborers']},
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
                   'american-canyon-wetlands-restoration-plan',
     'category': 'habitat-restoration', 'walkable': True, 'walkable_reason': None,
     'disambiguation': None,
     'participation': False, 'participation_note': None, 'facts': [],
     # the registry's own text says this is still a PLAN, not built work -
     # general field labor is the only trade honest to name this early
     'trade_needs': ['laborers']},
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
                   'north-bay-straw',
     'category': 'habitat-restoration', 'walkable': True, 'walkable_reason': None,
     'disambiguation': None,
     'participation': False, 'participation_note': None, 'facts': [],
     # student/teacher restoration-day field work - general field labor,
     # nothing heavier cited
     'trade_needs': ['laborers']},
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
     'source_url': 'https://www.sfbayrestore.org/',
     'category': 'habitat-restoration', 'walkable': False,
     # bay-wide and unpinned - there is no single point to walk to, not
     # a judgment about the work itself
     'walkable_reason': 'bay-wide, unpinned - no single point to walk',
     'disambiguation': None,
     'participation': False, 'participation_note': None, 'facts': [],
     # removal/revegetation field labor, with monitoring tracked across
     # roughly 70,000 acres of estuary
     'trade_needs': ['laborers', 'surveyors']},

    # -------------------------------------------------- environmental --
    # monitoring category. This is NOT a habitat-restoration site: no
    # planting or invasive-removal framing applies here. Hunters Point
    # Naval Shipyard is a real, currently-litigated federal Superfund
    # site in San Francisco's Bayview-Hunters Point neighborhood - the
    # facts below are a snapshot of public record as of September 2026,
    # not a claim that the cleanup or the litigation over it is finished;
    # both are open and will keep changing. `walkable` is explicitly
    # False: an actively litigated federal cleanup site is not something
    # this platform can responsibly present as a place to stroll. Each
    # `facts` entry below cites its own real source, the same terse,
    # factual pattern every other site above already uses for its one
    # source_url - this site just needs more than one citation to state
    # honestly. SmartCiti.X has no role in the cleanup, the litigation or
    # the monitoring program named below - see HONESTY['not_affiliated'].
    {'id': 'hunters-point-shipyard',
     'name': 'Hunters Point Naval Shipyard — EPA Superfund Site '
             '(Bayview-Hunters Point)',
     'org': 'US Navy (CERCLA lead agency for investigation and cleanup); '
            'US EPA Region 9 and California DTSC (oversight and '
            'enforcement of Navy cleanup activities)',
     'city': 'San Francisco', 'county': 'San Francisco', 'campus': 'treasure-island',
     'lat': 37.7280, 'lng': -122.3730, 'pin': True,
     'habitat': 'federal Superfund cleanup site — radiological soil '
                'investigation/remediation, hazardous-materials removal '
                'and demolition support; NOT habitat restoration and not '
                'an open park',
     'scale': 'an active, litigated federal Superfund cleanup on the '
              'National Priorities List — not resolved; see the cited '
              'facts below for current status as of September 2026',
     'workforce': False, 'workforce_note': None,
     'source_url': 'https://cumulis.epa.gov/supercpad/SiteProfiles/'
                   'index.cfm?fuseaction=second.cleanup&id=0902722',
     'category': 'environmental-monitoring', 'walkable': False,
     'walkable_reason': 'an actively litigated federal cleanup site is '
                        'not something this platform can responsibly '
                        'present as a place to stroll',
     # a real, community-run air-monitoring program - citizen-science
     # participation, explicitly NOT job training and NOT a SmartCiti.X
     # program (kept in a field separate from `workforce` on purpose, so
     # this is never read as a workforce-apprenticeship pathway)
     'disambiguation': None,
     'participation': True,
     'participation_note': 'the real, community-run Marie Harrison '
                           'Bayview Air Monitoring Project — ten '
                           'community air monitors placed in and around '
                           'Bayview-Hunters Point, run by Greenaction for '
                           'Health and Environmental Justice as part of '
                           'IVAN Bayview Hunters Point (bvhp-ivan.org) — '
                           'citizen-science air-monitoring participation, '
                           'not a workforce-training program, and not '
                           'run by SmartCiti.X',
     'facts': [
         {'text': "Former US Navy shipyard in San Francisco's "
                  'Bayview-Hunters Point neighborhood; an EPA Superfund '
                  'site on the National Priorities List. The Navy is '
                  'CERCLA lead agency for investigation and cleanup; US '
                  'EPA Region 9 and California DTSC oversee and enforce '
                  'Navy cleanup activities.',
          'source_url': 'https://cumulis.epa.gov/supercpad/SiteProfiles/'
                        'index.cfm?fuseaction=second.cleanup&id=0902722'},
         {'text': 'Navy contractor Tetra Tech EC Inc. was found to have '
                  'falsified radiological soil-testing data at the site '
                  'across 15 contracts worth a combined $262 million; a '
                  'federal judge approved a $57 million False Claims Act '
                  'settlement on August 24, 2026, resolving a 2013 qui '
                  'tam whistleblower complaint. This part is SETTLED, '
                  'public record.',
          'source_url': 'https://www.justice.gov/usao-ndca/pr/'
                        'tetra-tech-ec-inc-agrees-pay-57-million-settle-'
                        'false-claims-act-allegations-falsifying'},
         {'text': 'Greenaction for Health and Environmental Justice sued '
                  'the US Navy in 2024 alleging inadequate cleanup of '
                  'radioactive contamination at the site; a federal '
                  'court hearing was held February 26, 2026. This '
                  'litigation remains OPEN, not resolved.',
          'source_url': 'https://greenaction.org/2026/02/25/'
                        'february-26-2026-federal-court-hearing-on-'
                        'greenactions-lawsuit-vs-the-navy-over-inadequate-'
                        'cleanup-of-contamination-at-the-hunters-point-'
                        'naval-shipyard-superfund-site/'},
         {'text': 'The Navy began hazardous-materials removal at six '
                  'buildings in March 2026, ahead of scheduled '
                  'demolition — real, active site work.',
          'source_url': 'https://localnewsmatters.org/2026/03/09/'
                        'navy-begins-hazardous-materials-removal-for-'
                        'hunters-point-shipyard-demolition-project/'},
         {'text': 'Real community-run environmental monitoring: the '
                  'Marie Harrison Bayview Air Monitoring Project places '
                  'ten community air monitors in and around '
                  'Bayview-Hunters Point, run by Greenaction for Health '
                  'and Environmental Justice as part of IVAN Bayview '
                  'Hunters Point.',
          'source_url': 'https://insideclimatenews.org/news/27112021/'
                        'air-pollution-bayview-hunters-point-san-francisco/'},
     ],
     # containment/decon/monitoring/disposal is a direct fit for the
     # real hazmat removal work under way; demolition and excavation
     # support explain the secondary picks
     'trade_needs': ['hazmat', 'laborers', 'operating-eng']},

    # ------------------------------------------- Treasure Island (NSTI) --
    # The second environmental-monitoring site, and the one this bundle
    # cannot honestly be silent about: its flagship Treasure Island campus
    # scene sits on this island (geo/registry/campuses_geo.json ->
    # treasure-island, a DERIVED centroid). That campus scene is a
    # SCHEMATIC training campus and stays walkable; this entry is the
    # real-world record of the ground it stands on, and it is
    # walkable=False for the same reason Hunters Point is. NSTI is NOT an
    # NPL / Superfund-listed site - the `disambiguation` field says so in
    # the entry's own voice, because the NPL-listed "Treasure Island Naval
    # Station-Hunters Point Annex" is the Hunters Point entry above, a
    # different place. Facts are a snapshot of public record as of 17
    # September 2026, each typed from search-result snippets describing
    # the linked primary page (this build reaches no network host, and
    # those hosts were not reachable from the authoring sandbox either) -
    # see HONESTY['provenance']. No Site 12 coordinate is emitted: only an
    # unverified estimate exists, so Site 12 is placed in prose only.
    {'id': 'treasure-island-nsti',
     'name': 'Former Naval Station Treasure Island (NSTI) — Navy BRAC '
             'cleanup site (Treasure Island)',
     'org': 'US Navy (BRAC / CERCLA lead agency for investigation and '
            'cleanup); California DTSC (lead regulator), California '
            'Department of Public Health (radiological matters) and the '
            'San Francisco Bay Regional Water Quality Control Board '
            '(oversight)',
     'city': 'San Francisco', 'county': 'San Francisco', 'campus': 'treasure-island',
     'lat': 37.824, 'lng': -122.371, 'pin': True,
     'habitat': 'former naval station under a Navy-led BRAC/CERCLA '
                'cleanup — radiological (Ra-226) and chemical soil '
                'investigation and removal, building demolition and '
                'parcel-by-parcel transfer to the City; NOT habitat '
                'restoration, NOT an open park, and NOT an NPL Superfund '
                'site',
     'scale': 'an active federal base-closure cleanup whose principal '
              'radiological site (Site 12) still has unresolved cleanup '
              'criteria — not resolved; see the cited facts below for '
              'status as of September 2026',
     # a real union pre-apprenticeship that happens to be ON the island -
     # run by One Treasure Island with the City's OEWD/CityBuild, NOT part
     # of the Navy cleanup and NOT a SmartCiti.X program. It sits in the
     # `workforce` field like every habitat site's own program does, and
     # the note says exactly what it is and is not.
     'workforce': True,
     'workforce_note': "One Treasure Island's Construction Training "
                       'Program — an 8-week union pre-apprenticeship run '
                       "with the City's OEWD/CityBuild "
                       '(onetreasureisland.org/ctp) — a real program on '
                       'the island, run by that organization; NOT part of '
                       'the Navy cleanup and not a SmartCiti.X program',
     'source_url': 'https://media.defense.gov/2025/Apr/04/2003682676/-1/-1/0/'
                   'TRBW-0202-4856-0193_FAQ_NSTI_032125_CLEAN_ES_ACM.PDF',
     'category': 'environmental-monitoring', 'walkable': False,
     'walkable_reason': 'an active federal cleanup site with unresolved '
                        'radiological criteria is not something this '
                        'platform can responsibly present as a place to '
                        'stroll',
     # the one field only this site needs: the EPA-ID confusion is real
     # and easy to make, so it is stated in the entry itself, not left to
     # a reader to untangle
     'disambiguation': 'NOT an NPL / Superfund-listed site: NSTI carries '
                       'EPA Superfund ID CA7170023330 because it was '
                       'assessed, but was never placed on the National '
                       'Priorities List. The NPL-listed "Treasure Island '
                       'Naval Station–Hunters Point Annex" (EPA ID '
                       'CA1170090087) is the Hunters Point Naval Shipyard '
                       'entry in this same pack — a different place.',
     # a real, Navy-convened cleanup-oversight body - participation in
     # oversight, explicitly NOT job training and NOT a SmartCiti.X
     # program; kept in the `participation` field, separate from
     # `workforce`, exactly as Hunters Point's air-monitoring project is
     'participation': True,
     'participation_note': 'the real, Navy-convened NSTI Restoration '
                           'Advisory Board (RAB) — the Navy recruited '
                           'members in December 2024, held a virtual RAB '
                           'on 11 February 2025, and meets quarterly on '
                           'the first Tuesday of February, May, August '
                           'and November (bracpmo.navy.mil; '
                           'sftreasureisland.org) — cleanup-oversight '
                           'participation, not a workforce-training '
                           'program, and not run by SmartCiti.X',
     'facts': [
         {'text': 'Former US Navy station on Treasure Island in San '
                  'Francisco Bay. Listed for closure by the 1993 BRAC '
                  'Commission; closed 30 September 1997.',
          'source_url': 'https://www.militarymuseum.org/NSTI.html'},
         {'text': 'NOT an NPL / Superfund-listed site: EPA holds a '
                  'Superfund site profile for NSTI (ID CA7170023330) '
                  'because the site was assessed, but it was never placed '
                  'on the National Priorities List.',
          'source_url': 'https://cumulis.epa.gov/supercpad/cursites/'
                        'csitinfo.cfm?id=0902776'},
         {'text': 'Disambiguation: the NPL-listed "Treasure Island Naval '
                  'Station–Hunters Point Annex" (EPA ID CA1170090087) is '
                  'the Hunters Point Naval Shipyard entry in this same '
                  'pack — a different place, across the Bay in '
                  'Bayview-Hunters Point.',
          'source_url': 'https://www.toxicsites.us/site.php?epa_id='
                        'CA1170090087'},
         {'text': 'The cleanup runs under CERCLA and the BRAC program '
                  'with the US Navy as lead agency; the Navy reports '
                  'about $297 million in remediation spending through '
                  '2025 (Navy FAQ, March 2025).',
          'source_url': 'https://media.defense.gov/2025/Apr/04/2003682676/'
                        '-1/-1/0/TRBW-0202-4856-0193_FAQ_NSTI_032125_'
                        'CLEAN_ES_ACM.PDF'},
         {'text': 'Oversight: the California Department of Toxic '
                  'Substances Control (DTSC) is the lead regulator, the '
                  'California Department of Public Health (CDPH) covers '
                  'radiological matters, and the San Francisco Bay '
                  'Regional Water Quality Control Board oversees water '
                  'quality; US EPA and the NRC are consulted, not lead.',
          'source_url': 'https://www.sf.gov/'
                        'information--us-navy-cleanup-program-information'},
         {'text': 'Transfer mechanism: the Treasure Island Development '
                  'Authority (TIDA, a City agency) receives property '
                  'parcel by parcel under a December 2009 Economic '
                  'Development Conveyance agreement, and the Navy must '
                  'complete remediation before each transfer. As of the '
                  "Navy's November 2023 look-back, about 948 of about "
                  '1,077 acres (roughly 88%) had transferred and about '
                  '129 acres remained Navy-held.',
          'source_url': 'https://media.defense.gov/2023/Nov/14/2003339975/'
                        '-1/-1/0/NSTI_NOV2023_FINAL_LOOK_BACK_LOOK_AHEAD.PDF'},
         {'text': 'Radiological history: radium-226 radioluminescent '
                  'devices (compasses, gauges, deck markers), the '
                  "Navy's post-1946 damage-control and radiological "
                  'training school, and the 1960s "USS Pandemonium" '
                  "mock-ship trainer — as documented in the Navy's 2006 "
                  'Historical Radiological Assessment.',
          'source_url': 'https://media.defense.gov/2022/Mar/22/2002960667/'
                        '-1/-1/0/TI_200602_HRA.PDF'},
         {'text': "The Navy's July 2014 supplemental technical memorandum "
                  'to that Historical Radiological Assessment is the '
                  'second of the two documents that identified the '
                  "island's radiologically impacted sites.",
          'source_url': 'https://media.defense.gov/2022/Mar/22/2002960669/'
                        '-1/-1/0/TI_20140701_HRASTM_PT1OF2.PDF'},
         {'text': "Site 12 — the island's northwest end, a former housing "
                  'area holding the Northpoint and Westside Solid Waste '
                  'Disposal Areas — is the principal radiological site; '
                  'contaminants named in Navy documents include PCBs, '
                  'PAHs, dioxins, arsenic, lead and Ra-226. Its '
                  'non-radiological Record of Decision was signed in '
                  'March 2017.',
          'source_url': 'https://media.defense.gov/2022/Apr/04/2002969683/'
                        '-1/-1/0/TI_201703_ROD_SITE12_SWDA_NONRAD%20(1).PDF'},
         {'text': 'In September 2019 a degraded Ra-226 object was found '
                  'under a walkway at a Site 12 housing unit and removed; '
                  'the Navy and CDPH reported no public health risk from '
                  'it.',
          'source_url': 'https://www.bracpmo.navy.mil/Library/Timely-Topics/'
                        'Article/2988858/facts-about-a-recently-excavated-'
                        'low-level-radiological-material-at-treasure-is/'},
         {'text': 'The Site 12 radiological / solid-waste-area remedy was '
                  "still in feasibility study as of the Navy's February "
                  '2024 RAB schedule, which showed a draft Record of '
                  'Decision in February 2027 and a final in 2028 — NOT '
                  'resolved.',
          'source_url': 'https://media.defense.gov/2024/Feb/06/2003389177/'
                        '-1/-1/0/NSTI_06FEB2024_RAB_PRESO_FINAL.PDF'},
         {'text': 'A February 2026 analysis reports the Site 12 '
                  'conveyance stalled over unresolved CDPH radium-226 '
                  'building-cleanup criteria — a reported analysis, not '
                  'a Navy or CDPH statement.',
          'source_url': 'https://alamedapointenviro.com/2026/02/17/'
                        'dispute-over-radium-226-cleanup-hinders-progress-'
                        'at-closed-navy-bases/'},
         {'text': 'Other named sites: Site 6, the Old Fire Fighting '
                  'School, has a 2014 Remedial Action Plan.',
          'source_url': 'https://ceqanet.lci.ca.gov/2014022056'},
         {'text': 'Site 24, a former dry cleaner, has a 2015 Remedial '
                  'Action Plan.',
          'source_url': 'https://ceqanet.lci.ca.gov/2015022073'},
         {'text': 'Documented Site 12 field work — soil excavation and '
                  'off-site removal at the Northpoint Solid Waste Disposal '
                  "Area under the Navy's 2018 removal-action work plan, "
                  'with surface radiological scanning, building '
                  'demolition, backfill and air monitoring alongside it — '
                  "is the basis for this entry's trade_needs.",
          'source_url': 'https://media.defense.gov/2022/Apr/04/2002969685/'
                        '-1/-1/0/TI_201809_RA_NTCRA_WORKPLAN_SITE12_APPENA_'
                        'REDACTED%20(1).PDF'},
         {'text': 'Litigation: Treasure Island Former and Current '
                  'Residents v. United States (N.D. Cal. 3:20-cv-01328), '
                  'a class action against the Navy, Lennar, Tetra Tech '
                  'and others, was DISMISSED on 30 August 2022 — '
                  'dismissed, not settled; no appeal outcome is stated '
                  'here.',
          'source_url': 'https://dockets.justia.com/docket/california/'
                        'candce/3:2020cv01328/355777'},
         {'text': 'Oversight participation: the NSTI Restoration Advisory '
                  'Board is active — the Navy recruited members in '
                  'December 2024 and held a virtual RAB on 11 February '
                  '2025.',
          'source_url': 'https://www.bracpmo.navy.mil/Library/'
                        'Community-Information/Display/Article/4048336/'
                        'virtual-rab-meeting-ns-treasure-island-february-'
                        '11-2025/'},
         {'text': 'The RAB meets quarterly, on the first Tuesday of '
                  'February, May, August and November.',
          'source_url': 'https://sftreasureisland.org/event/'
                        'restoration-advisory-board-meeting'},
         {'text': 'Real environmental monitoring: the Navy posts Site 12 '
                  'air-monitoring reports publicly (for example the 24 '
                  'November – 7 December 2018 report).',
          'source_url': 'https://media.defense.gov/2022/Mar/22/2002960657/'
                        '-1/-1/0/TI_2018_11_24_TO_12_7_AIR_MONITORING_RPT_'
                        'SITE12.PDF'},
         {'text': 'TIDA maintains a public dust and hazardous-materials '
                  'control page for construction on the island.',
          'source_url': 'https://sftreasureisland.org/'
                        'dust-hazardous-materials-control'},
         {'text': "Where this pin is: the island's widely published "
                  'location (37.824, -122.371), AUTHORED — an approximate '
                  "point, not a surveyed pin. Site 12 is the island's "
                  'northwest end and gets no separate coordinate here, '
                  'because only an unverified estimate exists. This '
                  "bundle's own walkable Treasure Island campus scene is a "
                  "SCHEMATIC training campus at the island's derived "
                  'centroid — that scene stays walkable; this entry is the '
                  'real-world record of the ground it stands on, and is '
                  'not.',
          'source_url': 'https://en.wikipedia.org/wiki/'
                        'Naval_Station_Treasure_Island'},
     ],
     # the documented work is soil excavation and removal, surface
     # radiological scanning, building demolition, backfill and air
     # monitoring (see the work-plan fact above): containment / decon /
     # disposal is hazmat first; excavation support and site labor are
     # laborers; excavation and backfill are operating-eng; the demolition
     # slug covers the building teardown; surveyors covers the radiological
     # surface scanning and monitoring grid
     'trade_needs': ['hazmat', 'laborers', 'operating-eng', 'demolition',
                     'surveyors']},
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
                      'organization - this extends explicitly to Hunters '
                      'Point Naval Shipyard: SmartCiti.X has no role in '
                      'the actual cleanup, the litigation over it, or the '
                      'Marie Harrison Bayview Air Monitoring Project; and '
                      'to Former Naval Station Treasure Island: SmartCiti.X '
                      'has no role in the Navy cleanup, the Restoration '
                      'Advisory Board, the property transfers to TIDA, or '
                      "One Treasure Island's Construction Training "
                      'Program.',
    'environmental_monitoring_category': 'the environmental-monitoring '
                       "category is framed differently on purpose: it is "
                       'not habitat-restoration field work, so it never '
                       'renders as a walkable ground scene - only as a '
                       'located, clickable marker with a flat '
                       'facts-and-citations panel. It holds two sites: '
                       'Hunters Point Naval Shipyard, an NPL-listed '
                       'Superfund site with open litigation over it, and '
                       'Former Naval Station Treasure Island (NSTI), a '
                       'Navy BRAC/CERCLA cleanup that is NOT NPL-listed '
                       '(its EPA Superfund ID is an assessment record; the '
                       'NPL-listed "Treasure Island Naval Station-Hunters '
                       'Point Annex" is the Hunters Point site, a '
                       'different place). Its facts are a snapshot of '
                       'public record as of September 2026 (Hunters Point '
                       'typed 14 September, NSTI 17 September), not a '
                       'permanent claim - active federal cleanups, '
                       'unresolved radiological criteria and litigation '
                       'over them will keep changing, and this pack has '
                       'no live feed into any of it. NSTI is the island '
                       "this bundle's own Treasure Island campus scene "
                       'sits on: that scene is a schematic training campus '
                       "at the island's derived centroid and stays "
                       'walkable; the NSTI entry is the real-world record '
                       'of the ground it stands on, and is not.',
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
                       "campus operates, funds or sits next to the site. "
                       "The one entry where the grouping is literal is "
                       "Former Naval Station Treasure Island: this "
                       "bundle's schematic Treasure Island campus scene "
                       "does sit on that island, which the entry itself "
                       "states - still not a claim that the campus "
                       "operates or funds anything there",
    'not_certification': 'nothing here certifies a learner for real '
                         'restoration field work; the real workforce '
                         'programs named (Eco-Apprentice, STRAW, '
                         "Planting Justice's youth program, One Treasure "
                         "Island's Construction Training Program) are the "
                         'actual path to that, run by their own '
                         'organizations, with their own application '
                         'process - this pack only names and links them',
}

# ---------------------------------------------------------------- checks ---
skills_reg = json.load(open(ROOT / 'pack/registry/skills.json'))
skill_ids = {s['skill_id'] for s in skills_reg['skills']}
campuses_reg = json.load(open(ROOT / 'unions/registry/campuses.json'))['campuses']
unions_reg = json.load(open(ROOT / 'unions/registry/unions.json'))['unions']
union_slugs = {u['slug'] for u in unions_reg}

CATEGORIES = {'habitat-restoration', 'environmental-monitoring'}

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
    if s['participation']:
        assert s['participation_note'] and len(s['participation_note']) > 20, \
            f"{s['id']}: participation=True needs the real note"
    assert s['category'] in CATEGORIES, \
        f"{s['id']}: category must be one of {CATEGORIES}"
    assert s['trade_needs'] and isinstance(s['trade_needs'], list), \
        f"{s['id']}: trade_needs must name at least one real union slug"
    for slug in s['trade_needs']:
        assert slug in union_slugs, \
            f"{s['id']}: trade_needs names {slug!r}, not a real union slug"
    assert isinstance(s['walkable'], bool), f"{s['id']}: walkable must be a bool"
    if s['walkable']:
        assert s['pin'] and s['campus'], \
            f"{s['id']}: walkable=True needs a pin and a campus to place it in"
    else:
        assert s['walkable_reason'], \
            f"{s['id']}: walkable=False needs the honest reason stated"
    for f in s['facts']:
        assert f['text'] and f['source_url'].startswith('https://'), \
            f"{s['id']}: every fact needs real text and an https source"
    assert 'disambiguation' in s and (s['disambiguation'] is None
                                      or len(s['disambiguation']) > 40), \
        f"{s['id']}: disambiguation must be None or a real, stated note"

# the one load-bearing constraint this whole pack turns on: Hunters Point
# is pinned (locatable, clickable) but never walkable, and its category
# is the new, distinctly-framed one
hp = next(s for s in SITES if s['id'] == 'hunters-point-shipyard')
assert hp['category'] == 'environmental-monitoring' and hp['pin'] and not hp['walkable'], \
    'Hunters Point must be pinned, environmental-monitoring, and NOT walkable'
assert set(hp['trade_needs']) == {'hazmat', 'laborers', 'operating-eng'}, \
    'Hunters Point trade_needs drifted from the verified fit'
assert len(hp['facts']) >= 4, 'Hunters Point needs its citations, not a summary'
assert not hp['workforce'], \
    'Hunters Point is not a workforce/job-training program'
assert hp['participation'] and 'Greenaction' in hp['participation_note'] \
    and 'Marie Harrison' in hp['participation_note'], \
    'Hunters Point must point to the real community air-monitoring program'

# the second environmental-monitoring site holds to the same constraints,
# plus the two only it needs: it must say it is NOT NPL-listed and name
# the Hunters Point Annex EPA ID as the different place, and its lawsuit
# must read DISMISSED, never settled
ti = next(s for s in SITES if s['id'] == 'treasure-island-nsti')
assert ti['category'] == 'environmental-monitoring' and ti['pin'] and not ti['walkable'], \
    'NSTI must be pinned, environmental-monitoring, and NOT walkable'
assert ti['campus'] == 'treasure-island', \
    'NSTI is the island the Treasure Island campus scene sits on'
assert ti['trade_needs'] == ['hazmat', 'laborers', 'operating-eng', 'demolition',
                             'surveyors'], \
    'NSTI trade_needs drifted from the documented work'
assert len(ti['facts']) >= 12, 'NSTI needs its citations, not a summary'
ti_text = ' '.join(f['text'] for f in ti['facts'])
assert 'CA7170023330' in ti['disambiguation'] and 'CA1170090087' in ti['disambiguation'] \
    and 'NOT an NPL' in ti['disambiguation'], \
    'NSTI must state it is not NPL-listed and name the Hunters Point Annex ID'
assert 'DISMISSED' in ti_text and 'settled' not in ti_text.replace('not settled', ''), \
    'the NSTI class action was dismissed - never say settled'
assert '1,280' not in ti_text and 'Site 31' not in ti_text, \
    'NSTI facts must not carry the unverified figures'
assert ti['participation'] and 'Restoration Advisory Board' in ti['participation_note'] \
    and 'not a workforce-training program' in ti['participation_note'], \
    'NSTI must point to the real RAB as oversight participation, not job training'
assert ti['workforce'] and 'One Treasure Island' in ti['workforce_note'] \
    and 'NOT part of the Navy cleanup' in ti['workforce_note'], \
    "NSTI's workforce pathway is One Treasure Island's, and not the cleanup"
env_sites = [s for s in SITES if s['category'] == 'environmental-monitoring']
assert len(env_sites) == 2 and not any(s['walkable'] for s in env_sites), \
    'exactly two environmental-monitoring sites, neither walkable'
# the campus scene the NSTI entry stands on must itself stay a real,
# walkable campus in this bundle - the distinction the entry draws
assert 'treasure-island' in campuses_reg, 'the Treasure Island campus must exist'

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

    # the network dashboard names its own contributing pack for every
    # other platform-wide fact - the drift guard for this one
    dash = (ROOT / 'web/trade_craft_dashboard.html').read_text()
    assert f'{len(SITES)} / {len(TRACKS)}' in dash, \
        'the dashboard does not render the site / track count'
    assert HONESTY['not_affiliated'] in dash, \
        'the dashboard does not carry the not-affiliated honesty line'

    # the reverse direction: a hall panel that teaches a restoration
    # field-skill must itself link back to that track's entry in the
    # Bay Restoration panel - the same bidirectional pattern already
    # proven for orbis/training and Schools
    assert "D.restoration.tracks.some((t) => t.skills.some((sk) => " \
           "sk.split('.')[0] === sg))" in page3d \
        and 'data-restoration-hall="${esc(sg)}"' in page3d, \
        "the hall panel does not check for or link back to a taught track"
    assert "openRestoration(rh.dataset.restorationHall)" in page3d, \
        'the hall-panel restoration badge does not actually open the panel'

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
walkable_n = sum(1 for s in SITES if s['walkable'])
print(f"restoration pack: {len(SITES)} real sites across 2 categories "
      f"({len(pinned)} mapped, {walkable_n} walkable), "
      f"{len(TRACKS)} field-skill tracks (source stamp {stamp})")
