#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy - Bay restoration TRAINING SCENARIOS.

Writes restoration/registry/scenarios.json from the site registry this pack
already builds (restoration/registry/restoration.json) and the union roster
(unions/registry/unions.json). Run after restoration/build.py.

WHAT THIS IS. Practice scenarios for the project TYPES the Bay restoration
sites describe in their own registry words - ecotone levee work, tidal marsh
restoration, native planting, invasive Spartina removal, shoreline
resilience, shoreline trash clean-up, habitat monitoring, and (at the two
environmental-monitoring sites) cleanup-SUPPORT and safety AWARENESS only -
plus a generic water-quality / pollution-control family. Every scenario is
AUTHORED: a training scenario, not the project's actual work plan. Every step,
tool, PPE line, hazard and gate is unverified general practice, written to be
reviewed and replaced by journey-level practitioners; nothing here speaks for
a site operator, an agency or a standard.

WHERE A SCENARIO MAY SIT. A type is linked to a site only when the site's own
registry text (name, habitat or scale) contains the quoted evidence phrase;
the phrase is stored with the link and re-checked by test_scenarios.mjs.
Crew roles on a site scenario come only from that site's own `trade_needs`
(real union slugs). A water-quality scenario no site record supports stays
generic and unlinked.

HARD LIMITS. No hands-on hazardous remediation instruction anywhere: the
cleanup-support type is orientation, boundaries, observation and reporting,
and entering an exclusion zone or touching soil, debris or samples is a
FORBIDDEN action that fails the run. Herbicide mixing or application is
forbidden in the Spartina scenario (licensed applicators' work, not trained
here).

FUNDING CONTEXT. The user pointed at one news article whose host is blocked
from this environment. Only its URL headline is recorded; its funded
projects, recipients, sites and amounts are unknown here and are left as an
empty, PENDING slot. No scenario claims to be one of those projects.

Scoring is deterministic (score_run below; the same arithmetic ships in
web/restokit.py as JS and both must agree on the fixtures). A run is practice:
it never enters a completion record - completion/ is unchanged.
"""
import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'scenarios.json'
SOURCES = ('restoration/registry/restoration.json', 'unions/registry/unions.json', 'bayarea/registry/bayarea.json')
# (the two files BAY_READS inspects are checked at build time, not hashed: BAY and DEEP edit build_bayworld.py
# often, and a hash would stale this registry on every unrelated edit - the same rule as tasks/build PARAM_READS)
# a task link is written only when the Bay page is seen mounting the runner and reading #resto=<site>
BAY_PAGE = 'web/trade_craft_bay.html'
BAY_READS = (('web/restokit.py', "if (h.startsWith('resto=')) addEventListener('load', () => openSite(h.slice(6), null));"),
             ('web/build_bayworld.py', 'restokit.mount_for_landmarks(lms, '))


def fail(msg):
    raise SystemExit(f'restoration/scenarios: {msg}')


def need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise KeyError(f'restoration/scenarios: {where} has no "{k}"')
    return d[k]


LABEL = "training scenario, not the project's actual work plan"
LESSONS = 'unverified general practice'

FUNDING_CONTEXT = {
    'headline': 'EPA awards $82 million for San Francisco Bay restoration and pollution control',
    'url': ('https://smartwatermagazine.com/news/newsroom/'
            'epa-awards-82-million-for-san-francisco-bay-restoration-and-pollution-control'),
    'source': 'URL slug only - article not fetched (egress blocked)',
    'funded_projects': [],
    'status': 'PENDING',
    'note': ('Only the headline is known here. Which projects, recipients, sites and amounts the '
             'article lists is unknown; no scenario in this registry is one of them. The user may '
             'paste the article text to fill funded_projects.'),
}

# ------------------------------------------------------------------ types --
# role -> candidate trade slugs; a site instance keeps only roles whose trade
# is in that site's own trade_needs.
T = {}


def typ(tid, family, title, roles, steps, tools, ppe, hazards, gates, forbidden):
    T[tid] = {'id': tid, 'family': family, 'title': title,
              'roles': [{'role': r, 'trade': tr} for r, tr in roles],
              'steps': [{'id': s, 'text': x} for s, x in steps],
              'tools': tools, 'ppe': ppe,
              'hazards': [{'id': h, 'text': x} for h, x in hazards],
              'safety_gates': [{'id': g, 'before_step': b, 'text': x} for g, b, x in gates],
              'forbidden': [{'id': f, 'text': x} for f, x in forbidden]}


typ('ecotone-levee', 'restoration', 'Ecotone levee - grading a gentle marsh-to-upland slope',
    [('equipment operator', 'operating-eng'), ('grade checker / laborer', 'laborers'),
     ('survey lead', 'surveyors')],
    [('brief', 'crew brief: work area, tide window, haul routes and who signals the machine'),
     ('stake', 'set grade stakes and slope limits from the survey layout'),
     ('place', 'place fill in lifts along the levee face, working from the crown'),
     ('grade', 'shape the gentle transition slope to the staked grade'),
     ('check', 'check grade against stakes and record the as-built shots'),
     ('erosion', 'install temporary erosion control on the bare slope')],
    ['grade stakes', 'level / GNSS rover', 'erosion-control blanket', 'hand tools'],
    ['hi-vis vest', 'hard hat', 'safety-toe boots', 'hearing protection'],
    [('struck-by', 'struck-by and caught-between near operating equipment'),
     ('soft-edge', 'soft or undercut levee edge giving way under load'),
     ('tide', 'incoming tide cutting off the work area')],
    [('g-spotter', 'place', 'spotter and hand signals agreed before any machine moves near people'),
     ('g-tide', 'place', 'tide window confirmed and posted before work on the levee face')],
    [('ride-bucket', 'riding or standing in a bucket or on a moving machine'),
     ('blind-back', 'backing equipment without a spotter')])

typ('tidal-marsh', 'restoration', 'Tidal marsh restoration - preparing a diked or managed site for tidal return',
    [('equipment operator', 'operating-eng'), ('field laborer', 'laborers'), ('survey lead', 'surveyors')],
    [('brief', 'crew brief: tide tables, access route on levee crowns, buddy pairs'),
     ('survey', 'walk and mark the channel alignment from the design layout'),
     ('excavate', 'cut starter channels to the marked alignment'),
     ('spoil', 'place spoil where the plan marks it, never into open water'),
     ('monitor', 'photo-point and record water levels after the first tides')],
    ['survey flags', 'GNSS rover', 'staff gauge', 'camera'],
    ['hi-vis vest', 'safety-toe boots', 'PFD near open water', 'sun protection'],
    [('mud', 'soft mud entrapment off the levee crown'),
     ('drowning', 'open water and fast-moving tidal channels'),
     ('struck-by', 'operating equipment on a narrow levee crown')],
    [('g-tide', 'excavate', 'tide window confirmed before any work below the levee crown'),
     ('g-buddy', 'survey', 'buddy pairs set and PFDs checked before anyone leaves the crown')],
    [('solo-mud', 'entering the mudflat alone'),
     ('open-water', 'placing spoil into open water')])

typ('native-planting', 'restoration', 'Native planting and plant propagation',
    [('planting crew', 'laborers')],
    [('brief', 'crew brief: planting plan, species list and where not to step'),
     ('stage', 'stage plant stock in shade and keep the roots moist'),
     ('layout', 'lay out planting spots from the plan with flags'),
     ('plant', 'plant each plug to the root collar and firm the soil'),
     ('water', 'water in and mulch where the plan says'),
     ('record', 'record counts and photo-points for monitoring')],
    ['planting flags', 'hand trowels / dibbles', 'watering cans', 'data sheet'],
    ['gloves', 'safety-toe boots', 'sun protection', 'eye protection when clearing'],
    [('heat', 'heat and sun exposure'), ('ergonomic', 'repetitive bending and lifting'),
     ('sharps', 'buried debris and sharps in the soil')],
    [('g-sharps', 'plant', 'area walked and sharps flagged before hands go into the soil')],
    [('bare-hand', 'digging bare-handed in unscreened soil')])

typ('transition-zone', 'restoration', 'Wetland-upland transition zone planting',
    [('planting crew', 'laborers')],
    [('brief', 'crew brief: zone boundaries, sensitive areas and the tide line'),
     ('clear', 'hand-clear weeds from the planting band the plan marks'),
     ('plant', 'plant the band from wet edge to upland, species by elevation'),
     ('protect', 'install plant protection where the plan calls for it'),
     ('record', 'record survival plots and photo-points')],
    ['hand tools', 'planting flags', 'plant protection', 'data sheet'],
    ['gloves', 'safety-toe boots', 'sun protection'],
    [('mud', 'soft ground at the wet edge'), ('heat', 'heat and sun exposure'),
     ('wildlife', 'nesting or protected wildlife in the zone')],
    [('g-wildlife', 'clear', 'sensitive-area and nesting boundaries walked before clearing')],
    [('cross-fence', 'crossing a sensitive-area fence or marker')])

typ('spartina-removal', 'restoration', 'Invasive Spartina removal and revegetation (manual and survey work only)',
    [('field crew', 'laborers'), ('mapping lead', 'surveyors')],
    [('brief', 'crew brief: tide window, mapped patches and the buddy plan'),
     ('locate', 'navigate to the mapped patch and confirm it against the map'),
     ('flag', 'flag and record the patch location and size'),
     ('remove', 'hand-remove seedlings the crew lead identifies, bagging all plant material'),
     ('pack', 'pack out every bag - nothing left on the marsh'),
     ('reveg', 'plant native plugs where the plan marks revegetation')],
    ['GPS / map', 'flags', 'heavy bags', 'hand tools', 'native plugs'],
    ['gloves', 'mud boots', 'PFD near channels', 'sun protection'],
    [('mud', 'soft mud entrapment'), ('tide', 'incoming tide and flooding sloughs'),
     ('misid', 'mistaking native cordgrass for the invasive')],
    [('g-tide', 'locate', 'tide window confirmed before anyone enters the marsh'),
     ('g-id', 'remove', 'crew lead confirms identification before any plant is removed')],
    [('herbicide', 'mixing or applying herbicide (licensed applicators only; not trained here)'),
     ('leave-material', 'leaving removed plant material on the marsh')])

typ('shoreline-resilience', 'restoration', 'Shoreline resilience - living shoreline and green infrastructure placement',
    [('equipment operator', 'operating-eng'), ('field laborer', 'laborers')],
    [('brief', 'crew brief: tide window, lift plan and exclusion area around the machine'),
     ('layout', 'mark the footprint the design drawings show'),
     ('place', 'place material (rock, logs or planted media) as drawn'),
     ('secure', 'secure placed material per the drawings'),
     ('plant', 'plant the upper edge where the plan calls for it'),
     ('inspect', 'walk the finished reach and record photo-points')],
    ['layout paint / flags', 'hand tools', 'camera'],
    ['hi-vis vest', 'hard hat', 'safety-toe boots', 'gloves', 'PFD near open water'],
    [('struck-by', 'placed material and operating equipment'),
     ('slip', 'wet rock and algae at the shoreline'), ('tide', 'rising tide and wave run-up')],
    [('g-exclusion', 'place', 'exclusion area around the machine set before any placement'),
     ('g-tide', 'place', 'tide window confirmed before work below the high-tide line')],
    [('under-load', 'standing under or beside a suspended or swinging load')])

typ('trash-cleanup', 'restoration', 'Shoreline trash clean-up',
    [('clean-up crew', 'laborers')],
    [('brief', 'crew brief: area, tide, what not to touch and how to report it'),
     ('sweep', 'sweep the area in lines, picking up with grabbers'),
     ('sort', 'sort recyclables and trash into separate bags'),
     ('report', 'report and flag anything hazardous without touching it'),
     ('weigh', 'weigh or count bags and record the tally')],
    ['grabbers', 'bags', 'sharps container', 'data sheet', 'scale'],
    ['puncture-resistant gloves', 'safety-toe boots', 'hi-vis vest'],
    [('sharps', 'needles, glass and sharp metal'), ('unknown', 'drums, containers or unknown substances'),
     ('slip', 'slippery rocks at the waterline')],
    [('g-sharps', 'sweep', 'sharps rule stated (grabber and sharps container only) before the sweep')],
    [('touch-unknown', 'opening or moving a drum or unknown container')])

typ('habitat-monitoring', 'restoration', 'Habitat monitoring - photo-points, plots and records',
    [('monitoring lead', 'surveyors'), ('field assistant', 'laborers')],
    [('brief', 'crew brief: plot list, route and check-in times'),
     ('locate', 'relocate each permanent plot or photo-point from the record'),
     ('record', 'record cover, counts or photos exactly as the protocol asks'),
     ('qa', 'check the data sheet is complete before leaving the plot'),
     ('upload', 'file the records with date, time and observer')],
    ['GPS', 'camera', 'quadrat', 'data sheets'],
    ['safety-toe boots', 'sun protection', 'hi-vis vest'],
    [('mud', 'soft ground at plots'), ('lone', 'working alone out of sight')],
    [('g-checkin', 'locate', 'check-in times agreed with someone off-site before heading out')],
    [('move-marker', 'moving a permanent plot marker')])

typ('planning-survey', 'restoration', 'Baseline condition survey for a restoration plan',
    [('survey lead', 'surveyors'), ('field assistant', 'laborers')],
    [('brief', 'crew brief: access permissions, route and check-in times'),
     ('control', 'set or recover survey control'),
     ('transect', 'walk transects and record existing conditions'),
     ('photo', 'take photo-points at the marked stations'),
     ('file', 'file the baseline record with its method notes')],
    ['GNSS rover', 'camera', 'data sheets', 'flags'],
    ['hi-vis vest', 'safety-toe boots', 'sun protection'],
    [('access', 'private or restricted land along the shoreline'), ('mud', 'soft ground')],
    [('g-access', 'control', 'access permission confirmed before entering any parcel')],
    [('trespass', 'entering a parcel without permission')])

typ('cleanup-support', 'cleanup-awareness',
    'Cleanup-site safety AWARENESS - orientation, boundaries, observation and reporting only',
    [('awareness trainee (support zone only)', 'laborers'), ('monitoring observer', 'hazmat'),
     ('survey observer', 'surveyors')],
    [('orient', "attend the site's own health-and-safety orientation, run by the site's own staff"),
     ('boundaries', 'identify posted boundaries, signage and the support zone on the site map'),
     ('observe', 'observe from the support zone only; note where posted monitoring stations are'),
     ('report', 'report anything out of place to the supervisor; do not touch it'),
     ('log', 'log the observation with time and place')],
    ['site map', 'notebook', 'radio or phone to the supervisor'],
    ["only the PPE the site's own health-and-safety plan issues for the support zone", 'hi-vis vest'],
    [('exposure', 'contaminated soil, dust or debris beyond the posted boundary'),
     ('equipment', 'operating equipment and trucks on haul routes'),
     ('unknown', 'unknown materials or containers')],
    [('g-orient', 'boundaries', "site orientation completed before anything else on site"),
     ('g-stopwork', 'observe', 'stop-work and reporting chain stated before observing')],
    [('enter-exclusion', 'entering an exclusion zone or crossing a posted boundary'),
     ('handle-material', 'touching, moving or sampling soil, debris or any material'),
     ('eat-drink', 'eating, drinking or smoking in a controlled area')])

# ---------------------------------------------- water-quality family (generic)
typ('wq-stormwater', 'water-quality', 'Stormwater capture - inspecting a green-infrastructure cell',
    [('inspection lead', 'laborers'), ('equipment operator', 'operating-eng')],
    [('brief', 'crew brief: traffic control, inlet locations and the inspection form'),
     ('traffic', 'set traffic or pedestrian control around the cell'),
     ('inlet', 'inspect inlets and curb cuts for blockage'),
     ('surface', 'record sediment, trash and standing water in the cell'),
     ('outlet', 'check the overflow and outlet structure'),
     ('record', 'record findings and photos on the form')],
    ['inspection form', 'camera', 'measuring tape', 'cones'],
    ['hi-vis vest', 'gloves', 'safety-toe boots'],
    [('traffic', 'passing traffic'), ('sharps', 'sharps in captured trash'),
     ('confined', 'vaults and structures that are confined spaces')],
    [('g-traffic', 'inlet', 'traffic control set before anyone works at the curb')],
    [('enter-vault', 'entering a vault or structure (confined space - not trained here)')])

typ('wq-trash-capture', 'water-quality', 'Trash capture device inspection',
    [('inspection lead', 'laborers')],
    [('brief', 'crew brief: device list, traffic control and the inspection form'),
     ('traffic', 'set traffic control around the inlet'),
     ('look', 'inspect the screen or insert from above for fullness and damage'),
     ('record', 'record fullness and condition on the form'),
     ('flag', 'flag a full or damaged device for the maintenance crew')],
    ['inspection form', 'flashlight', 'camera', 'cones'],
    ['hi-vis vest', 'gloves', 'safety-toe boots'],
    [('traffic', 'passing traffic'), ('lift', 'heavy grate lifting'), ('sharps', 'sharps in captured trash')],
    [('g-traffic', 'look', 'traffic control set before the grate area is approached')],
    [('enter-inlet', 'entering the inlet or reaching into it by hand')])

typ('wq-sampling', 'water-quality', 'Water sampling technique - grab sample and chain of custody',
    [('sampler', 'laborers'), ('monitoring sampler', 'hazmat')],
    [('brief', 'crew brief: station list, bottle kit and hold times'),
     ('label', 'label the bottle before sampling'),
     ('sample', 'take the grab sample upstream of where you stand, without touching the inside of the cap'),
     ('preserve', 'cap and ice the sample'),
     ('coc', 'fill in the chain-of-custody form and sign it over')],
    ['labelled bottles', 'cooler and ice', 'chain-of-custody form', 'sampling pole'],
    ['nitrile gloves', 'PFD near water', 'safety glasses'],
    [('drowning', 'steep or slippery banks'), ('contact', 'skin contact with the water')],
    [('g-bank', 'sample', 'footing and PFD checked before reaching over the water')],
    [('touch-cap', 'touching the inside of the bottle or cap')])

typ('wq-sediment-core', 'water-quality', 'Sediment core handling AWARENESS - labelling, custody and contact avoidance',
    [('awareness trainee', 'laborers'), ('monitoring observer', 'hazmat')],
    [('brief', "crew brief: the sampling team's own plan and who handles cores (not the trainee)"),
     ('observe', 'observe core retrieval from the designated area'),
     ('label', 'check each core label matches the station log'),
     ('custody', 'check the chain-of-custody entry is complete')],
    ['station log', 'chain-of-custody form'],
    ['gloves', 'safety glasses', 'PFD on the vessel or near water'],
    [('contact', 'skin contact with sediment of unknown quality'),
     ('vessel', 'vessel motion and deck equipment')],
    [('g-plan', 'observe', "sampling team's plan read before observing")],
    [('handle-core', 'handling, opening or subsampling a core (sampling team only)')])

# ------------------------------------------------------------- site links --
# (site, type, evidence) - evidence must appear in the site's own name,
# habitat or scale text in restoration.json.
LINKS = [
    ('herons-head', 'shoreline-resilience', 'Shoreline Resilience'),
    ('herons-head', 'wq-stormwater', 'green infrastructure'),
    ('candlestick-point', 'trash-cleanup', 'trash clean-up'),
    ('candlestick-point', 'native-planting', 'native plant propagation'),
    ('candlestick-point', 'habitat-monitoring', 'monitoring'),
    ('candlestick-point', 'wq-trash-capture', 'trash clean-up'),
    ('east-oakland-youth', 'native-planting', 'upland restoration'),
    ('alviso-shoreline', 'native-planting', 'marsh-adjacent upland'),
    ('south-bay-salt-ponds', 'ecotone-levee', 'ecotone levee'),
    ('south-bay-salt-ponds', 'tidal-marsh', 'managed pond to tidal marsh'),
    ('montezuma-wetlands', 'tidal-marsh', 'tidal & seasonal wetland'),
    ('american-canyon', 'planning-survey', 'a plan summarizing restoration opportunities'),
    ('straw-north-bay', 'transition-zone', 'wetland-upland transition zone'),
    ('spartina-removal', 'spartina-removal', 'Invasive Spartina Removal'),
    ('hunters-point-shipyard', 'cleanup-support', 'federal Superfund cleanup site'),
    ('treasure-island-nsti', 'cleanup-support', 'Navy-led BRAC/CERCLA cleanup'),
]

RUBRIC = [
    {'axis': 'gates', 'measure': 'every safety gate acknowledged before the step it guards', 'pass': 'required'},
    {'axis': 'forbidden', 'measure': 'no forbidden action taken', 'pass': 'required'},
    {'axis': 'ppe', 'measure': 'share of the listed PPE selected (%)', 'pass': '== 100'},
    {'axis': 'order', 'measure': 'share of steps done in the listed order (longest in-order run, %)', 'pass': '>= 80'},
    {'axis': 'crew', 'measure': 'share of crew roles given the listed trade (%)', 'pass': '== 100'},
    {'axis': 'score', 'measure': 'floor((order*5 + crew*2 + ppe*3) / 10)', 'pass': 'informational'},
]


def lis(seq):
    """length of the longest strictly increasing subsequence (O(n^2), tiny n)"""
    best = [1] * len(seq)
    for i in range(len(seq)):
        for j in range(i):
            if seq[j] < seq[i] and best[j] + 1 > best[i]:
                best[i] = best[j] + 1
    return max(best) if best else 0


def score_run(sc, run):
    """deterministic: run = {ppe:[str], crew:{role: trade}, sequence:[str]}
    sequence tokens: 'gate:<id>', 'step:<id>', 'forbidden:<id>'"""
    seq = need(run, 'sequence', 'run')
    step_ids = [s['id'] for s in sc['steps']]
    first = {}
    for i, tok in enumerate(seq):
        if tok not in first:
            first[tok] = i
    gates_ok = True
    for g in sc['safety_gates']:
        gi = first['gate:' + g['id']] if 'gate:' + g['id'] in first else None
        si = first['step:' + g['before_step']] if 'step:' + g['before_step'] in first else None
        if gi is None or (si is not None and gi > si):
            gates_ok = False
    forbidden_ok = not any(tok.startswith('forbidden:') for tok in seq)
    done = []
    for tok in seq:
        if tok.startswith('step:') and tok[5:] in step_ids and step_ids.index(tok[5:]) not in done:
            done.append(step_ids.index(tok[5:]))
    order = (lis(done) * 100) // len(step_ids)
    chosen = need(run, 'ppe', 'run')
    ppe = (sum(1 for p in sc['ppe'] if p in chosen) * 100) // len(sc['ppe'])
    crew_run = need(run, 'crew', 'run')
    crew = (sum(1 for r in sc['crew'] if r['role'] in crew_run and crew_run[r['role']] == r['trade'])
            * 100) // len(sc['crew'])
    score = (order * 5 + crew * 2 + ppe * 3) // 10
    passed = gates_ok and forbidden_ok and ppe == 100 and order >= 80 and crew == 100
    return {'gates': gates_ok, 'forbidden': forbidden_ok, 'ppe': ppe, 'order': order,
            'crew': crew, 'score': score, 'pass': passed}


def fixtures(sc):
    perfect_seq = []
    for s in sc['steps']:
        perfect_seq += ['gate:' + g['id'] for g in sc['safety_gates'] if g['before_step'] == s['id']]
        perfect_seq.append('step:' + s['id'])
    crew = {r['role']: r['trade'] for r in sc['crew']}
    perfect = {'ppe': list(sc['ppe']), 'crew': crew, 'sequence': perfect_seq}
    no_gate = {'ppe': list(sc['ppe']), 'crew': crew,
               'sequence': [t for t in perfect_seq if t != 'gate:' + sc['safety_gates'][0]['id']]}
    forbidden = {'ppe': list(sc['ppe']), 'crew': crew,
                 'sequence': perfect_seq + ['forbidden:' + sc['forbidden'][0]['id']]}
    shuffled = {'ppe': list(sc['ppe'])[:-1], 'crew': crew,
                'sequence': [g for g in perfect_seq if g.startswith('gate:')]
                + list(reversed([t for t in perfect_seq if t.startswith('step:')]))}
    out = []
    reversed_steps = {'ppe': list(sc['ppe']), 'crew': crew, 'sequence': shuffled['sequence']}
    for name, run in (('perfect', perfect), ('gate-skipped', no_gate), ('reversed-steps', reversed_steps),
                      ('forbidden-action', forbidden), ('reversed-missing-ppe', shuffled)):
        out.append({'name': name, 'run': run, 'expect': score_run(sc, run)})
    return out


def main():
    resto = json.loads((ROOT / SOURCES[0]).read_text())
    unions = json.loads((ROOT / SOURCES[1]).read_text())
    slugs = {need(u, 'slug', 'unions.json#unions[]') for u in need(unions, 'unions', 'unions.json')}
    sites = {need(s, 'id', 'restoration.json#sites[]'): s for s in need(resto, 'sites', 'restoration.json')}
    for t in T.values():
        for r in t['roles']:
            if r['trade'] not in slugs:
                fail(f'type {t["id"]}: trade {r["trade"]} is not a union slug')
        step_ids = {s['id'] for s in t['steps']}
        if not t['safety_gates'] or not t['forbidden']:
            fail(f'type {t["id"]}: needs at least one safety gate and one forbidden action')
        for g in t['safety_gates']:
            if g['before_step'] not in step_ids:
                fail(f'type {t["id"]}: gate {g["id"]} guards unknown step {g["before_step"]}')
    scenarios = []
    for sid, tid, ev in LINKS:
        if sid not in sites:
            fail(f'link names unknown site {sid}')
        if tid not in T:
            fail(f'link names unknown type {tid}')
        s = sites[sid]
        field = next((f for f in ('name', 'habitat', 'scale') if ev in need(s, f, sid)), None)
        if field is None:
            fail(f'{sid}/{tid}: evidence {ev!r} is not in the site\'s own name, habitat or scale')
        t = T[tid]
        crew = [r for r in t['roles'] if r['trade'] in need(s, 'trade_needs', sid)]
        if not crew:
            fail(f'{sid}/{tid}: no role of this type matches the site\'s own trade_needs')
        sc = {'id': f'rs-{sid}-{tid}', 'site': sid, 'site_name': s['name'], 'type': tid,
              'family': t['family'], 'title': t['title'], 'label': LABEL, 'provenance': 'AUTHORED',
              'lessons': LESSONS, 'evidence': {'field': field, 'quote': ev},
              'category': need(s, 'category', sid), 'campus': need(s, 'campus', sid),
              'crew': crew, 'steps': t['steps'], 'tools': t['tools'], 'ppe': t['ppe'],
              'hazards': t['hazards'], 'safety_gates': t['safety_gates'], 'forbidden': t['forbidden']}
        if s['category'] == 'environmental-monitoring' and t['family'] != 'cleanup-awareness':
            fail(f'{sid}: an environmental-monitoring site takes awareness scenarios only')
        sc['fixtures'] = fixtures(sc)
        scenarios.append(sc)
    linked_types = {tid for _, tid, _ in LINKS}
    generic = []
    for t in T.values():
        if t['family'] == 'water-quality' and t['id'] not in linked_types:
            g = {'id': f'rs-generic-{t["id"]}', 'site': None, 'site_name': None, 'type': t['id'],
                 'family': t['family'], 'title': t['title'], 'label': LABEL, 'provenance': 'AUTHORED',
                 'lessons': LESSONS, 'evidence': None, 'category': None, 'campus': None,
                 'why_unlinked': 'no site record in restoration.json names this work, so it stays generic',
                 'crew': t['roles'], 'steps': t['steps'], 'tools': t['tools'], 'ppe': t['ppe'],
                 'hazards': t['hazards'], 'safety_gates': t['safety_gates'], 'forbidden': t['forbidden']}
            g['fixtures'] = fixtures(g)
            generic.append(g)
    for sc in scenarios + generic:
        exp = {f['name']: f['expect'] for f in sc['fixtures']}
        if not exp['perfect']['pass'] or exp['gate-skipped']['pass'] or exp['forbidden-action']['pass'] or exp['reversed-steps']['pass'] \
                or exp['reversed-missing-ppe']['pass']:
            fail(f'{sc["id"]}: scoring fixtures do not separate pass from fail')
    # staged task rows (TASK_CONTRACT shape). Live in tasks.json only once
    # web/taskkit.py accepts the kind; campus-less sites are not wired.
    for rel, frag in BAY_READS:
        if frag not in (ROOT / rel).read_text():
            fail(f'{rel} no longer mounts/reads #resto= ({frag[:50]!r}); refusing to write a Bay page link')
    bay = json.loads((ROOT / SOURCES[2]).read_text())
    placed = {need(x, 'id', 'bayarea.json restoration_sites[]') for c in need(bay, 'counties', 'bayarea.json').values()
              for x in need(c, 'restoration_sites', 'bayarea.json counties')}
    staged, unwired = [], []
    for i, sc in enumerate(scenarios):
        if sc['campus'] is None:
            unwired.append({'scenario': sc['id'], 'why': 'the site has no campus grouping (bay-wide, unpinned); '
                            'the task contract requires a campus on a restoration-site place'})
            continue
        staged.append({
            'id': sc['id'].replace('rs-', 'resto-sim-', 1), 'title': f'{sc["title"]} - {sc["site_name"]}',
            'kind': 'resto-scenario', 'place': {'kind': 'restoration-site', 'id': sc['site'], 'campus': sc['campus']},
            'launch': ({'href': f'{BAY_PAGE}#resto={sc["site"]}', 'lands': 'section', 'param': ['#resto']}
                       if sc['site'] in placed else
                       {'href': None, 'why': ('the Bay world page does not place this site (bayarea/registry/bayarea.json '
                                              'has no restoration_sites entry for it), so no page opens its runner')}),
            'requires': [], 'provenance': 'DERIVED',
            'source': f'restoration/registry/scenarios.json#scenarios[{i}]', 'seat': None,
            'brief': f'{LABEL}; {len(sc["steps"])} steps, {len(sc["safety_gates"])} safety gates',
        })
    srcs = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()[:16] for rel in SOURCES}
    builder = pathlib.Path(__file__).read_bytes()
    stamp = hashlib.sha256(builder + b''.join((ROOT / r).read_bytes() for r in SOURCES)).hexdigest()[:16]
    by_site = {}
    for sc in scenarios:
        by_site[sc['site']] = by_site[sc['site']] + 1 if sc['site'] in by_site else 1
    doc = {
        'pack': 'smartcitix-trade-craft-academy-bay-restoration-scenarios',
        'built': need(resto, 'built', 'restoration.json'),
        'source_stamp': stamp, 'sources': srcs,
        'honesty': {
            'label': LABEL,
            'lessons': LESSONS,
            'authored': ('Every scenario, step, tool, PPE line, hazard, gate and crew role is AUTHORED '
                         'general practice, not any site operator\'s plan and not a standard or a jurisdiction\'s rule.'),
            'no_remediation': ('No hands-on hazardous remediation is taught: at the two environmental-monitoring '
                               'sites the only type is cleanup-support AWARENESS (orientation, boundaries, '
                               'observation, reporting); entering an exclusion zone or touching material fails the run.'),
            'play': ('A run is practice. It certifies nothing and never enters a completion record; the '
                     'completion contract in completion/ is unchanged.'),
            'links': ('A type sits at a site only where the site\'s own registry text contains the quoted '
                      'evidence; crew roles come only from that site\'s own trade_needs.'),
            'paths': ('No relief/trades path step links these yet: layers/registry/paths.json holds Louisiana '
                      'parish stations only, and no Bay station id exists to attach to.'),
        },
        'funding_context': FUNDING_CONTEXT,
        'rubric': RUBRIC,
        'types': sorted(T),
        'counts': {'scenarios': len(scenarios), 'generic': len(generic), 'by_site': by_site,
                   'sites_covered': len(by_site), 'staged_tasks': len(staged)},
        'scenarios': scenarios,
        'generic': generic,
        'staged_tasks': staged,
        'unwired': unwired,
    }
    text = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
    if '--check' in __import__('sys').argv:
        if not OUT.exists() or OUT.read_text() != text:
            fail(f'{OUT.relative_to(ROOT)} differs from a fresh build (hand-edited or stale)')
        print('restoration/scenarios: --check ok, registry matches a fresh build')
        return
    OUT.write_text(text)
    print(f'restoration/scenarios: {len(scenarios)} site scenarios across {len(by_site)} sites, '
          f'{len(generic)} generic, {len(staged)} staged tasks -> {OUT.relative_to(ROOT)}  stamp {stamp}')


if __name__ == '__main__':
    try:
        main()
    except KeyError as e:
        raise SystemExit(str(e).strip('"\''))
