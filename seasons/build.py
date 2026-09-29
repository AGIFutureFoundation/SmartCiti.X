#!/usr/bin/env python3
"""seasons/ - an AUTHORED game calendar of regional, seasonal tasks for the walkable worlds (FIELDS, wave 12).

WHAT THIS IS
Two regions - the Louisiana parishes world and the Bay Area counties world - each get a 12-month GAME calendar
(labelled "approximate, game calendar" wherever it is shown), staged crop tasks (rice from field prep to harvest,
sugarcane, strawberries, satsuma-style citrus, pecans, garden plots; Bay orchard, vineyard-style harvest, community
garden, shoreline cleanup day) and generic seasonal events (parade season, festival day, a storm-preparedness drill,
back-to-school). Every month, stage length and timing window is an AUTHORED game-balance value, not an agronomic
schedule. Facts are one general line naming the KIND of source; no yield, date, price or quota is stated anywhere.

WHERE PLOTS GO (fail closed, read-only inputs)
- Louisiana: on economy/registry/economy.json residential lots (AUTHORED game lots whose land use is DERIVED from the
  PARISH AUTHORED ground-tile tint) - a plot is that lot's garden; the first PLOTS_PER_WORLD residential lots by id.
- Bay: on bayarea/registry/bayarea.json AUTHORED districts - `park` districts nearest the county's local origin
  first, topped up with `residential` districts (community-garden style) where a county holds too few parks.
Each plot point is re-checked inside the RECORDED coarse outline (point in polygon, parish/county LOCAL metres);
a plot outside stops the build by name. Nothing here is a real farm, orchard, vineyard or address.

    python3 seasons/build.py      # writes seasons/registry/seasons.json
"""
import hashlib
import json
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'seasons.json'
INPUTS = ['seasons/build.py', 'economy/registry/economy.json', 'bayarea/registry/bayarea.json',
          'parishes/registry/parishes.json', 'pack/manifest.json']
TIERS = ('RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED', 'SCRIPTED')
CAL_LABEL = 'approximate, game calendar'
RULES_LINE = ('Real activity follows state rules - check the state wildlife agency (Louisiana Department of Wildlife and '
              'Fisheries; California Department of Fish and Wildlife) and your state agricultural extension service.')
PLOTS_PER_WORLD = 3


class SeasonsError(KeyError):
    """A missing or malformed registry field (named, so the build stops on it)."""


def need(obj, key, where):
    if not isinstance(obj, dict):
        raise SeasonsError(f'seasons: {where}: expected an object to read {key!r} from')
    if key not in obj:
        raise SeasonsError(f'seasons: {where}: no key {key!r}')
    return obj[key]


def load(rel):
    p = ROOT / rel
    if not p.exists():
        raise SeasonsError(f'seasons: input {rel} is missing')
    return json.loads(p.read_text())


def inside(pt, rings):
    """Even-odd point in polygon over every ring of every polygon (outline_local_m: [[ring, hole...], ...])."""
    x, y = pt
    hit = False
    for poly in rings:
        for ring in poly:
            j = len(ring) - 1
            for i in range(len(ring)):
                xi, yi = ring[i]
                xj, yj = ring[j]
                if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                    hit = not hit
                j = i
    return hit


# ------------------------------------------------------------------ safety notes (general guidance) ---
SAFETY = {
    'heat': 'Hot days: drink water often, rest in shade and wear a hat - heat illness is serious (general public-health guidance).',
    'sun': 'Sun: wear sunscreen and long sleeves outdoors in the middle of the day (general public-health guidance).',
    'water': 'Flooded fields, ditches and shorelines: never wade in moving water, wear boots, and keep well back from snakes and alligators - never approach or feed wildlife.',
    'tools': 'Tools: wear gloves, carry blades pointed down, and let a trained adult handle knives, saws and machinery.',
    'ladder': 'Ladders: have a partner steady the ladder and never over-reach from it.',
    'sharps': 'Sharp litter: never pick up glass, needles or hooks by hand - leave them and tell an adult.',
    'storm': 'Storms: follow instructions from local emergency management; a drill is practice, not a forecast.',
    'crowd': 'Crowds: agree a meeting spot, stay with your group and keep water with you.',
}

# ------------------------------------------------------------------ crops and experiences (AUTHORED) ---
# stage = (id, label, phase, window_min_days, window_max_days): the action opens window_min game days after the
# previous stage and closes window_max days after it (0, 0 = do it straight away). All values AUTHORED game balance.
def S(sid, label, phase, lo, hi):
    return {'id': sid, 'label': label, 'phase': phase, 'window_days': [lo, hi]}


TASKS = [
    # ---- Louisiana ----
    {'id': 'rice', 'region': 'louisiana', 'kind': 'crop', 'label': 'Rice field', 'plot': True,
     'months': [3, 4, 5, 6, 7, 8],
     'stages': [S('field-prep', 'Prepare the field (level it, fix the levees)', 'prepare', 0, 2),
                S('flooding', 'Flood the field', 'prepare', 1, 3),
                S('planting', 'Plant the seed', 'plant', 1, 3),
                S('growth', 'Tend the growing rice (check water depth)', 'tend', 3, 6),
                S('draining', 'Drain the field before harvest', 'tend', 3, 6),
                S('harvest', 'Harvest with the combine', 'harvest', 2, 4)],
     'fact': 'Rice is grown in flooded, levee-edged fields in parts of Louisiana; after harvest many fields are re-flooded to raise crawfish (source kind: state agricultural extension service).',
     'safety': ['heat', 'water', 'tools'], 'rotation': 'rice-crawfish-rotation', 'band': '6-8'},
    {'id': 'sugarcane-harvest', 'region': 'louisiana', 'kind': 'crop', 'label': 'Sugarcane harvest', 'plot': True,
     'months': [10, 11, 12],
     'stages': [S('check-rows', 'Walk the rows and check the cane', 'prepare', 0, 2),
                S('cut', 'Cut the cane (machine harvester)', 'harvest', 1, 3),
                S('load', 'Load the wagons', 'tend', 0, 2),
                S('haul', 'Haul the cane to the mill', 'harvest', 1, 3)],
     'fact': 'Sugarcane is a major Louisiana crop harvested in the cooler months and milled soon after cutting (source kind: state agricultural extension service).',
     'safety': ['tools', 'heat'], 'band': '6-8'},
    {'id': 'strawberry-picking', 'region': 'louisiana', 'kind': 'crop', 'label': 'Strawberry picking', 'plot': True,
     'months': [2, 3, 4, 5],
     'stages': [S('beds', 'Shape the raised beds', 'prepare', 0, 2),
                S('plant', 'Set the plants', 'plant', 1, 3),
                S('tend', 'Weed and water the rows', 'tend', 2, 5),
                S('pick', 'Pick the ripe berries (red all over)', 'harvest', 2, 5)],
     'fact': 'Strawberries are grown in parts of south-east Louisiana and picked by hand when fully red (source kind: state agricultural extension service).',
     'safety': ['sun', 'heat'], 'band': 'K-5'},
    {'id': 'citrus-harvest', 'region': 'louisiana', 'kind': 'crop', 'label': 'Satsuma-style citrus harvest', 'plot': True,
     'months': [10, 11, 12],
     'stages': [S('check-trees', 'Check the trees for ripe fruit', 'prepare', 0, 2),
                S('clip', 'Clip the fruit from the branch', 'harvest', 1, 3),
                S('sort', 'Sort and pack the fruit', 'tend', 0, 2)],
     'fact': 'Satsuma-type mandarins grow in south Louisiana and are clipped rather than pulled so the peel is not torn (source kind: state agricultural extension service).',
     'safety': ['ladder', 'tools'], 'band': 'K-5'},
    {'id': 'pecan-gathering', 'region': 'louisiana', 'kind': 'crop', 'label': 'Pecan gathering', 'plot': True,
     'months': [10, 11],
     'stages': [S('clear', 'Clear the ground under the trees', 'prepare', 0, 2),
                S('gather', 'Gather the fallen nuts', 'harvest', 1, 4),
                S('dry', 'Dry the nuts in the shade', 'tend', 1, 3)],
     'fact': 'Pecan trees are native to the region; the nuts fall in autumn and are gathered from the ground (source kind: state agricultural extension service).',
     'safety': ['sun', 'tools'], 'band': 'K-5'},
    {'id': 'garden-plot', 'region': 'louisiana', 'kind': 'crop', 'label': 'Garden plot', 'plot': True,
     'months': [2, 3, 4, 9, 10, 11],
     'stages': [S('prepare', 'Prepare the soil', 'prepare', 0, 2),
                S('plant', 'Plant seeds or seedlings', 'plant', 1, 3),
                S('tend', 'Water and weed', 'tend', 2, 5),
                S('harvest', 'Harvest the vegetables', 'harvest', 3, 6)],
     'fact': 'The Gulf Coast has two main vegetable-garden seasons, spring and autumn, with hot summers in between (source kind: state agricultural extension service).',
     'safety': ['heat', 'tools'], 'band': 'K-5'},
    # ---- Bay Area ----
    {'id': 'orchard', 'region': 'bay', 'kind': 'crop', 'label': 'Orchard harvest', 'plot': True,
     'months': [6, 7, 8, 9, 10],
     'stages': [S('prune', 'Check the pruned trees', 'prepare', 0, 2),
                S('thin', 'Thin the young fruit', 'tend', 1, 4),
                S('pick', 'Pick the ripe fruit', 'harvest', 2, 5)],
     'fact': 'Orchards of stone fruit and apples are part of the farmland around the Bay Area; fruit is picked by hand as it ripens (source kind: state agricultural extension service).',
     'safety': ['ladder', 'sun'], 'band': 'K-5'},
    {'id': 'vineyard-harvest', 'region': 'bay', 'kind': 'crop', 'label': 'Vineyard-style harvest', 'plot': True,
     'months': [8, 9, 10],
     'stages': [S('check-rows', 'Walk the rows and taste-test (game) the grapes', 'prepare', 0, 2),
                S('pick', 'Pick the bunches into bins', 'harvest', 1, 3),
                S('haul', 'Haul the bins to the press', 'tend', 0, 2)],
     'fact': 'Grapes are grown in the valleys north of the Bay and picked in late summer and autumn (source kind: state agricultural extension service).',
     'safety': ['tools', 'heat'], 'band': '9-10'},
    {'id': 'community-garden', 'region': 'bay', 'kind': 'crop', 'label': 'Community garden', 'plot': True,
     'months': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
     'stages': [S('prepare', 'Prepare the shared bed', 'prepare', 0, 2),
                S('plant', 'Plant seedlings', 'plant', 1, 3),
                S('tend', 'Water and weed on your rota day', 'tend', 2, 5),
                S('harvest', 'Harvest and share', 'harvest', 3, 6)],
     'fact': 'The Bay Area has a mild climate, so community gardens can grow something in most months (source kind: state agricultural extension service).',
     'safety': ['sun', 'tools'], 'band': 'K-5'},
    {'id': 'shoreline-cleanup', 'region': 'bay', 'kind': 'experience', 'label': 'Shoreline cleanup day', 'plot': True,
     'months': [4, 9],
     'stages': [S('sign-in', 'Sign in and get gloves and a bag', 'prepare', 0, 1),
                S('collect', 'Collect litter above the tide line', 'tend', 0, 2),
                S('sort', 'Sort and tally what you found', 'harvest', 0, 2)],
     'fact': 'Volunteer shoreline cleanups keep litter out of the Bay and record what they find (source kind: state coastal agency).',
     'safety': ['sharps', 'water', 'sun'], 'band': '6-8'},
    # ---- generic seasonal events (named generically; no real event name) ----
    {'id': 'parade-season', 'region': 'louisiana', 'kind': 'event', 'label': 'Parade season', 'plot': False,
     'months': [1, 2],
     'stages': [S('plan', 'Pick a safe viewing spot', 'prepare', 0, 2), S('go', 'Watch the parade with your group', 'harvest', 0, 3)],
     'fact': 'Winter parade season is a long community tradition in south Louisiana towns (source kind: local tourism office).',
     'safety': ['crowd'], 'band': 'K-5'},
    {'id': 'festival-day', 'region': 'louisiana', 'kind': 'event', 'label': 'Festival day', 'plot': False,
     'months': [4, 10],
     'stages': [S('plan', 'Plan the day and pack water', 'prepare', 0, 2), S('go', 'Visit the food and music stalls', 'harvest', 0, 3)],
     'fact': 'Many Louisiana towns hold food and music festivals in the mild spring and autumn months (source kind: local tourism office).',
     'safety': ['crowd', 'heat'], 'band': 'K-5'},
    {'id': 'storm-drill', 'region': 'louisiana', 'kind': 'event', 'label': 'Hurricane-preparedness drill', 'plot': False,
     'months': [6, 7, 8, 9, 10, 11],
     'stages': [S('kit', 'Pack a go-bag checklist (water, torch, radio, medicines)', 'prepare', 0, 2),
                S('route', 'Learn your evacuation route', 'tend', 0, 2),
                S('neighbours', 'Plan to check on neighbours', 'harvest', 0, 2)],
     'fact': 'The Gulf Coast plans for hurricanes every summer and autumn; official seasons and alerts come from the national weather service and local emergency management (source kind: national weather service).',
     'safety': ['storm'], 'band': '6-8'},
    {'id': 'back-to-school', 'region': 'louisiana', 'kind': 'event', 'label': 'Back-to-school week', 'plot': False,
     'months': [8],
     'stages': [S('supplies', 'Gather supplies', 'prepare', 0, 2), S('route', 'Walk the safe route to school', 'harvest', 0, 2)],
     'fact': 'In the southern states school usually starts in late summer, in the heat (source kind: local school district calendar).',
     'safety': ['heat'], 'band': 'K-5'},
    {'id': 'festival-day-bay', 'region': 'bay', 'kind': 'event', 'label': 'Festival day', 'plot': False,
     'months': [5, 9],
     'stages': [S('plan', 'Plan the day and pack water', 'prepare', 0, 2), S('go', 'Visit the food and music stalls', 'harvest', 0, 3)],
     'fact': 'Bay Area towns hold street fairs and harvest festivals through the dry months (source kind: local tourism office).',
     'safety': ['crowd', 'sun'], 'band': 'K-5'},
    {'id': 'quake-drill', 'region': 'bay', 'kind': 'event', 'label': 'Earthquake-preparedness drill', 'plot': False,
     'months': [4, 10],
     'stages': [S('drop', 'Practise drop, cover and hold on', 'prepare', 0, 1),
                S('kit', 'Check the emergency kit checklist', 'tend', 0, 2),
                S('meet', 'Agree a family meeting place', 'harvest', 0, 2)],
     'fact': 'The Bay Area lies near active faults, so schools and families practise drop, cover and hold on (source kind: state emergency services office).',
     'safety': ['storm'], 'band': 'K-5'},
    {'id': 'back-to-school-bay', 'region': 'bay', 'kind': 'event', 'label': 'Back-to-school week', 'plot': False,
     'months': [8],
     'stages': [S('supplies', 'Gather supplies', 'prepare', 0, 2), S('route', 'Walk the safe route to school', 'harvest', 0, 2)],
     'fact': 'Many California schools start in August (source kind: local school district calendar).',
     'safety': ['sun'], 'band': 'K-5'},
]

ROTATIONS = [
    {'id': 'rice-crawfish-rotation', 'region': 'louisiana', 'label': 'Rice-crawfish rotation',
     'crop': 'rice', 'rice_months': [3, 4, 5, 6, 7, 8], 'crawfish_months': [11, 12, 1, 2, 3, 4, 5],
     'text': ('In general terms: rice is harvested in late summer, the field is re-flooded in autumn, crawfish grow in '
              'the flooded stubble through winter and spring and are trapped, then the field is drained and the cycle '
              'starts again. Months here are an approximate game calendar.'),
     'crawfish_trapping': 'FISH (outdoors/ pack, web/fishkit.py) owns crawfish trapping; link here by this id.',
     'source_kind': 'state agricultural extension service', 'provenance': 'AUTHORED'},
]

PLOT_USE = {'louisiana': 'residential', 'bay': 'park'}
REGIONS = {
    'louisiana': {'label': 'Louisiana parishes', 'world': 'parishes', 'page': 'web/trade_craft_parishes.html',
                  'quest_world': 'parish'},
    'bay': {'label': 'Bay Area counties', 'world': 'bay', 'page': 'web/trade_craft_bay.html', 'quest_world': 'bay'},
}
GAME_CLOCK = {'days_per_month': 10, 'start_month': 3,
              'speeds': [{'id': 'pause', 's_per_day': 0}, {'id': '1x', 's_per_day': 12},
                         {'id': '4x', 's_per_day': 3}, {'id': '16x', 's_per_day': 0.75}],
              'provenance': 'AUTHORED', 'note': 'game time only; a game day is seconds of play, not a real day'}


def build():
    econ = load('economy/registry/economy.json')
    bay = load('bayarea/registry/bayarea.json')
    par = load('parishes/registry/parishes.json')
    manifest = load('pack/manifest.json')
    plots = {}
    # Louisiana: residential economy lots, first PLOTS_PER_WORLD by id, each re-checked inside its outline
    for fips, p in sorted(need(econ, 'parishes', 'economy.json').items()):
        outline = need(need(need(par, 'parishes', 'parishes.json'), fips, 'parishes.json#parishes'), 'outline_local_m', fips)
        lots = sorted((l for l in need(p, 'lots', fips) if need(l, 'zone', fips) == PLOT_USE['louisiana']),
                      key=lambda l: need(l, 'id', fips))[:PLOTS_PER_WORLD]
        if len(lots) < PLOTS_PER_WORLD:
            raise SeasonsError(f'seasons: parish {fips} has {len(lots)} residential lots, need {PLOTS_PER_WORLD}')
        rows = []
        for i, l in enumerate(lots):
            lm = need(l, 'local_m', l['id'])
            if not inside(lm, outline):
                raise SeasonsError(f'seasons: plot on {l["id"]} lies outside the RECORDED outline of {fips}')
            rows.append({'id': f'plot-{fips}-{i + 1}', 'fips': fips, 'local_m': lm, 'x': lm[0], 'z': -lm[1],
                         'size_m': need(l, 'size_m', l['id']), 'on': l['id'], 'land_use': PLOT_USE['louisiana'],
                         'land_use_provenance': need(l, 'landuse_provenance', l['id']), 'provenance': 'AUTHORED'})
        plots[fips] = {'region': 'louisiana', 'name': need(p, 'name', fips), 'plots': rows}
    # Bay: park districts nearest the county local origin
    for fips, c in sorted(need(bay, 'counties', 'bayarea.json').items()):
        outline = need(c, 'outline_local_m', fips)
        # park districts first; a county with too few parks (San Francisco) tops up with residential districts
        # (a community-garden style plot) - the plot records which use it sits on
        order = {PLOT_USE['bay']: 0, 'residential': 1}
        ds = [d for d in need(c, 'districts', fips) if need(d, 'use', fips) in order]
        ds.sort(key=lambda d: (order[d['use']], math.hypot(*need(d, 'seed_local_m', d['id'])), d['id']))
        rows = []
        for d in ds:
            lm = d['seed_local_m']
            if need(d, 'provenance', d['id']) != 'AUTHORED' or not inside(lm, outline):
                continue
            rows.append({'id': f'plot-{fips}-{len(rows) + 1}', 'fips': fips, 'local_m': lm, 'x': lm[0], 'z': -lm[1],
                         'size_m': [30, 30], 'on': d['id'], 'land_use': d['use'],
                         'land_use_provenance': 'AUTHORED', 'provenance': 'AUTHORED'})
            if len(rows) == PLOTS_PER_WORLD:
                break
        if len(rows) < PLOTS_PER_WORLD:
            raise SeasonsError(f'seasons: county {fips} has {len(rows)} AUTHORED park districts inside its outline, need {PLOTS_PER_WORLD}')
        plots[fips] = {'region': 'bay', 'name': need(c, 'name', fips), 'plots': rows}

    ids = set()
    for t in TASKS:
        if t['id'] in ids:
            raise SeasonsError(f'seasons: task id {t["id"]} twice')
        ids.add(t['id'])
        for s in t['safety']:
            need(SAFETY, s, t['id'] + '.safety')
        if t['region'] not in REGIONS:
            raise SeasonsError(f'seasons: task {t["id"]} region {t["region"]!r}')
        t['provenance'] = 'AUTHORED'
        t['calendar'] = CAL_LABEL
    rot_ids = {r['id'] for r in ROTATIONS}
    for t in TASKS:
        if 'rotation' in t and t['rotation'] not in rot_ids:
            raise SeasonsError(f'seasons: task {t["id"]} names rotation {t["rotation"]!r} which is not defined')
    calendar = {}
    for rid in REGIONS:
        calendar[rid] = {'label': CAL_LABEL, 'months': [
            {'month': m, 'in_season': [t['id'] for t in TASKS if t['region'] == rid and m in t['months']]}
            for m in range(1, 13)]}

    stamp = hashlib.sha256()
    for rel in INPUTS:
        stamp.update((ROOT / rel).read_bytes())
    full = stamp.hexdigest()
    reg = {
        'pack': 'seasons', 'pack_version': need(manifest, 'pack_version', 'pack/manifest.json'),
        'source_stamp': full[:16], 'source_stamp_sha256': full, 'inputs': INPUTS, 'provenance_tiers': list(TIERS),
        'honesty': {
            'play': 'Every harvest, badge and log entry here is PLAY: kept on this device only, never a completion record, never money.',
            'calendar': 'Months are an approximate, game calendar - AUTHORED for play, not a planting guide.',
            'facts': 'Facts are general and name the kind of source; no yields, dates, prices or quotas are stated.',
            'plots': 'Plots are AUTHORED game plots on AUTHORED land use - not real farms, orchards, vineyards or addresses.',
            'rules': RULES_LINE,
            'safety': 'Safety notes are general guidance, not professional advice.',
        },
        'placement': {'louisiana': 'economy/registry/economy.json residential lots (land use DERIVED from the PARISH AUTHORED tint), first 3 by id',
                      'bay': 'bayarea/registry/bayarea.json AUTHORED park districts nearest the county local origin first, topped up with residential districts where a county has too few parks',
                      'check': 'every plot point inside the RECORDED coarse outline (point in polygon, LOCAL metres)',
                      'frame': 'parish/county LOCAL metres; x = east_m, z = -north_m (scene convention)'},
        'game_clock': GAME_CLOCK, 'regions': REGIONS, 'safety': SAFETY, 'tasks': TASKS, 'rotations': ROTATIONS,
        'calendar': calendar, 'plots': plots,
        'counts': {'regions': len(REGIONS), 'tasks': len(TASKS), 'crops': sum(t['kind'] == 'crop' for t in TASKS),
                   'events': sum(t['kind'] == 'event' for t in TASKS), 'worlds': len(plots),
                   'plots': sum(len(v['plots']) for v in plots.values())},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + '\n')
    print(f'seasons: {reg["counts"]} stamp {full[:16]}')


if __name__ == '__main__':
    build()
