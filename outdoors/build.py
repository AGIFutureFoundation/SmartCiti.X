#!/usr/bin/env python3
"""outdoors/ - fishing spots, rods, bait, species and crawfish/crab gear for the open worlds (FISH, wave 12).

Everything a player fishes is PLAY. The pack has two halves:

AUTHORED (outdoors/authored/catalog.json): rods/poles with AUTHORED 1-5 game stats, bait and lures, real regional
species named generally (habitats, an approximate game-calendar season, time-of-day weights, a one-line general fact,
a handling / catch-and-release tip), and the honesty lines every page quotes.

DERIVED (this build, fail closed): fishing SPOTS placed only on water the world registries already author -
  - parishes: parishes/maps/world/<fips>.json water (lakes, bayous, canals, streams, ponds - all AUTHORED, procedural);
  - Bay: bayarea/maps/world/<fips>.json water (canals, streams, ponds) plus coast spots: the county outline vertex
    nearest an AUTHORED bay label point of bayarea/registry/bayarea.json#water.labels, within COAST_MAX_M;
  - wilds: shoreline cells of the AUTHORED terrain (wilds/core.mjs, via outdoors/wilds_shore.mjs) nearest each site.
Every spot records the exact source path it came from. A spot is in the page frame the world pages use
(x = east metres, z = -north metres, relative to the region's origin_m: the numbers window.__parishes.local() returns;
wilds: the world's own x/z). A missing field stops the build with a named error; there are no defaults.

Crawfish: the rice-crawfish rotation belongs to FIELDS (seasons/). If seasons/registry/*.json exists and holds an id
naming crawfish, the crawfish species links to that id; otherwise there is no link (fail open, recorded as null).

    python3 outdoors/build.py          # writes outdoors/registry/outdoors.json
    python3 outdoors/build.py --check  # exit 1 if the registry is stale
"""
import hashlib
import json
import math
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry/outdoors.json'
COAST_MAX_M = 30000        # AUTHORED: a county coast vertex farther than this from every bay label gets no coast spot
SHORE_STEP_M = 3.0         # AUTHORED: a bank spot stands this far outside the water polygon edge
COAST_INLAND_M = 25.0      # AUTHORED: a coast spot stands this far inland of the outline vertex
MONTHS = range(1, 13)
METHODS = ('cast', 'line', 'trap')
STAT_KEYS_ROD = ('reach', 'power', 'finesse', 'tension_window')
STAT_KEYS_SPECIES = ('fight', 'wariness', 'rarity')
WILDS_HABITAT = {'mountain': 'lake', 'forest': 'lake', 'canyon': 'river', 'delta': 'marsh'}
WILDS_REGION = {'mountain': 'west', 'forest': 'west', 'canyon': 'west', 'delta': 'gulf'}


class BuildError(SystemExit):
    pass


def need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise BuildError(f'outdoors: {where} has no field {k!r}')
    return d[k]


def load(rel):
    p = ROOT / rel
    if not p.exists():
        raise BuildError(f'outdoors: missing input {rel}')
    return json.loads(p.read_text(encoding='utf-8'))


def outward(px, pz, cx, cz, step):
    dx, dz = px - cx, pz - cz
    d = math.hypot(dx, dz)
    if d == 0:
        raise BuildError(f'outdoors: degenerate water feature at {px},{pz}')
    return round(px + dx / d * step, 1), round(pz + dz / d * step, 1)


# ------------------------------------------------------------------ catalogue --
CAT = load('outdoors/authored/catalog.json')
REGIONS = need(CAT, 'regions', 'catalog')
HABITATS = need(CAT, 'habitats', 'catalog')
TIMES = need(CAT, 'times', 'catalog')
BAITS = {need(b, 'id', 'catalog.baits[]'): b for b in need(CAT, 'baits', 'catalog')}
RODS = need(CAT, 'rods', 'catalog')
SPECIES = need(CAT, 'species', 'catalog')
HONESTY = need(CAT, 'honesty', 'catalog')
for k in ('play', 'real', 'seasons', 'facts', 'wildlife', 'places'):
    need(HONESTY, k, 'catalog.honesty')
for agency in ('Louisiana Department of Wildlife and Fisheries', 'California Department of Fish and Wildlife'):
    if agency not in HONESTY['real']:
        raise BuildError(f'outdoors: honesty.real must name {agency}')

seen = set()
for r in RODS:
    rid = need(r, 'id', 'catalog.rods[]')
    if rid in seen:
        raise BuildError(f'outdoors: duplicate rod id {rid}')
    seen.add(rid)
    for k in ('title', 'method', 'stats', 'habitats', 'tip'):
        need(r, k, f'rod {rid}')
    if r['method'] not in METHODS:
        raise BuildError(f'outdoors: rod {rid} method {r["method"]!r} not in {METHODS}')
    for k in STAT_KEYS_ROD:
        v = need(r['stats'], k, f'rod {rid}.stats')
        if not (isinstance(v, int) and 1 <= v <= 5):
            raise BuildError(f'outdoors: rod {rid}.stats.{k} must be an AUTHORED integer 1-5')
    for h in r['habitats']:
        if h not in HABITATS:
            raise BuildError(f'outdoors: rod {rid} habitat {h!r} is not a catalog habitat')
for sp in SPECIES:
    sid = need(sp, 'id', 'catalog.species[]')
    if sid in seen:
        raise BuildError(f'outdoors: duplicate id {sid}')
    seen.add(sid)
    for k in ('title', 'regions', 'habitats', 'methods', 'baits', 'season', 'times', 'stats', 'fact', 'handling'):
        need(sp, k, f'species {sid}')
    for rg in sp['regions']:
        if rg not in REGIONS:
            raise BuildError(f'outdoors: species {sid} region {rg!r} unknown')
    for h in sp['habitats']:
        if h not in HABITATS:
            raise BuildError(f'outdoors: species {sid} habitat {h!r} unknown')
    for m in sp['methods']:
        if m not in METHODS:
            raise BuildError(f'outdoors: species {sid} method {m!r} unknown')
    for b in sp['baits']:
        if b not in BAITS:
            raise BuildError(f'outdoors: species {sid} bait {b!r} is not in catalog.baits')
    s = sp['season']
    if not (isinstance(s, list) and len(s) == 2 and all(isinstance(x, int) and x in MONTHS for x in s)):
        raise BuildError(f'outdoors: species {sid} season must be [start_month, end_month] (1-12, may wrap)')
    if sorted(sp['times']) != sorted(TIMES) or not any(sp['times'][t] > 0 for t in TIMES):
        raise BuildError(f'outdoors: species {sid} times must weight every catalog time ({TIMES}) with one > 0')
    for k in STAT_KEYS_SPECIES:
        v = need(sp['stats'], k, f'species {sid}.stats')
        if not (isinstance(v, int) and 1 <= v <= 5):
            raise BuildError(f'outdoors: species {sid}.stats.{k} must be an AUTHORED integer 1-5')
    if any(ch.isdigit() for ch in sp['fact']):
        raise BuildError(f'outdoors: species {sid} fact carries a number - facts stay general (no invented figures)')

# ------------------------------------------------------------------ spots --
spots = []


def add_spot(world, region_id, region, habitat, x, z, source, basis, name=None):
    if habitat not in HABITATS:
        raise BuildError(f'outdoors: spot habitat {habitat!r} unknown ({source})')
    sid = f'{world}-{region_id}-{len([s for s in spots if s["world"] == world and s["region_id"] == region_id])}'
    spots.append({'id': sid, 'world': world, 'region_id': region_id, 'region': region, 'habitat': habitat,
                  'x': x, 'z': z, 'name': name, 'hidden': False, 'source': source, 'basis': basis,
                  'provenance': 'DERIVED'})
    return spots[-1]


def water_spots(world, reg_rel, region):
    reg = load(reg_rel)
    key = 'parishes' if world == 'parishes' else 'counties'
    out_ids = []
    for fips, row in sorted(need(reg, key, reg_rel).items()):
        rel = need(row, 'path', f'{reg_rel}#{key}.{fips}')
        m = load(rel)
        if need(m, 'fips', rel) != fips:
            raise BuildError(f'outdoors: {rel} fips mismatch')
        w = need(m, 'water', rel)
        if need(w, 'provenance', rel + '#water') != 'AUTHORED':
            raise BuildError(f'outdoors: {rel}#water is not AUTHORED')
        for i, lk in enumerate(need(w, 'lakes', rel + '#water')):
            pg, (cx, cn) = need(lk, 'polygon', rel), need(lk, 'centre', rel)
            e, n = pg[0]
            x, z = outward(e, -n, cx, -cn, SHORE_STEP_M)
            add_spot(world, fips, region, 'lake', x, z, f'{rel}#water.lakes[{i}]', 'lake edge vertex, stepped onto the bank',
                     need(lk, 'name', rel))
        chans = need(w, 'channels', rel + '#water')
        by_kind = {}
        for i, ch in enumerate(chans):
            by_kind.setdefault(need(ch, 'kind', rel), []).append((i, ch))
        for kind in ('bayou', 'canal', 'stream'):
            for i, ch in (by_kind[kind] if kind in by_kind else [])[:2 if kind == 'bayou' else 1]:   # a region with no such channel simply has no such spot
                cl, pg = need(ch, 'centre', rel), need(ch, 'polygon', rel)
                k = len(cl) // 2
                if len(pg) < 2 * len(cl) or k >= len(pg):
                    raise BuildError(f'outdoors: {rel}#water.channels[{i}] polygon is not a ribbon of its centre line')
                (be, bn), (ce, cn) = pg[k], cl[k]
                x, z = outward(be, -bn, ce, -cn, SHORE_STEP_M)
                add_spot(world, fips, region, kind, x, z, f'{rel}#water.channels[{i}]',
                         f'{kind} bank at the middle of its centre line')
        ponds = sorted(enumerate(need(w, 'ponds', rel + '#water')), key=lambda t: -need(t[1], 'radius_m', rel))
        if ponds:
            for i, pd in (ponds[0], ponds[-1]):
                (e, n), (cx, cn) = need(pd, 'polygon', rel)[0], need(pd, 'centre', rel)
                x, z = outward(e, -n, cx, -cn, SHORE_STEP_M)
                s = add_spot(world, fips, region, 'pond', x, z, f'{rel}#water.ponds[{i}]', 'pond edge vertex, stepped onto the bank')
                if i == ponds[-1][0] and len(ponds) > 1:
                    s['basis'] += ' (the smallest pond: a quiet corner)'
        out_ids.append(fips)
    return out_ids


PARISH_IDS = water_spots('parishes', 'parishes/registry/world.json', 'gulf')
BAY_IDS = water_spots('bay', 'bayarea/registry/world.json', 'bay')

# Bay coast: the outline vertex nearest a bay label point, stepped inland toward the county origin
bay = load('bayarea/registry/bayarea.json')
labels = [lb for lb in need(need(bay, 'water', 'bayarea.json'), 'labels', 'bayarea.json#water')
          if 'Bay' in need(lb, 'name', 'bayarea.json#water.labels[]')]
if not labels:
    raise BuildError('outdoors: bayarea.json#water.labels holds no bay label point for coast spots')
for fips, c in sorted(need(bay, 'counties', 'bayarea.json').items()):
    ox, on = need(need(c, 'frame', f'counties.{fips}'), 'origin_in_world_m', f'counties.{fips}.frame')
    best = None
    for lb in labels:
        lx, ln = lb['world_m'][0] - ox, lb['world_m'][1] - on
        for poly in need(c, 'outline_local_m', f'counties.{fips}'):
            for ring in poly:
                for e, n in ring:
                    d = math.hypot(e - lx, n - ln)
                    if best is None or d < best[0]:
                        best = (d, e, n, lb['name'])
    if best and best[0] <= COAST_MAX_M:
        d, e, n = best[0], best[1], best[2]
        x, z = outward(e, -n, 0.0, 0.0, -COAST_INLAND_M)   # negative step = toward the county origin
        add_spot('bay', fips, 'bay', 'bay-shore', x, z, f'bayarea/registry/bayarea.json#counties.{fips}.outline_local_m',
                 f'coast vertex nearest the AUTHORED label point of {best[3]} ({round(d / 1000)} km), stepped inland', best[3])

# wilds: shoreline cells of the AUTHORED terrain
wreg = load('wilds/registry/wilds.json')
try:
    shore = json.loads(subprocess.run(['node', str(HERE / 'wilds_shore.mjs')], check=True, capture_output=True,
                                      text=True, cwd=str(ROOT)).stdout)
except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
    raise BuildError(f'outdoors: wilds shoreline scan failed: {e}')
WILDS_IDS = []
for w in need(wreg, 'worlds', 'wilds.json'):
    wid = need(w, 'id', 'wilds.json#worlds[]')
    if wid not in WILDS_HABITAT:
        raise BuildError(f'outdoors: wilds world {wid!r} has no AUTHORED habitat in WILDS_HABITAT')
    row = need(shore, wid, 'wilds_shore.mjs output')
    if not row['spots']:
        raise BuildError(f'outdoors: wilds world {wid} has no shoreline below its water level - no spot can be placed')
    for s in row['spots']:
        add_spot('wilds', wid, WILDS_REGION[wid], WILDS_HABITAT[wid], s['x'], s['z'],
                 f'wilds/core.mjs wildsTerrain(wilds/registry/wilds.json#worlds.{wid}) via outdoors/wilds_shore.mjs',
                 f'shore cell below water_level_m next to dry ground, nearest {s["near_site"]} ({s["site_distance_m"]} m)')
        spots[-1]['near_site'] = s['near_site']
    WILDS_IDS.append(wid)

# hidden spots (eggs): one quiet corner per world group, chosen by rule, never typed by id
def hide(cands, why):
    if not cands:
        raise BuildError(f'outdoors: no candidate for a hidden spot ({why})')
    cands[0]['hidden'] = True
    cands[0]['hidden_rule'] = why
    return cands[0]['id']


HIDDEN = [
    hide([s for s in spots if s['world'] == 'parishes' and 'smallest pond' in s['basis'] and s['region_id'] == '22071'],
         'the smallest pond in the start parish (22071)'),
    hide([s for s in spots if s['world'] == 'bay' and 'smallest pond' in s['basis'] and s['region_id'] == '06075'],
         'the smallest pond in the Bay start county (06075)'),
]
for wid in WILDS_IDS:
    HIDDEN.append(hide(sorted([s for s in spots if s['world'] == 'wilds' and s['region_id'] == wid],
                              key=lambda s: -math.hypot(s['x'], s['z'])), f'the {wid} shore spot farthest from the world centre'))

# every species must be catchable somewhere in its regions, and every region's spots must hold a catch
for sp in SPECIES:
    ok = [s for s in spots if s['region'] in sp['regions'] and s['habitat'] in sp['habitats']
          and any(r['method'] in sp['methods'] and s['habitat'] in r['habitats'] for r in RODS)]
    if not ok:
        raise BuildError(f'outdoors: species {sp["id"]} has no reachable spot (region x habitat x rod)')
    sp['spot_count'] = len(ok)
for s in spots:
    if not any(s['region'] in sp['regions'] and s['habitat'] in sp['habitats'] for sp in SPECIES):
        raise BuildError(f'outdoors: spot {s["id"]} ({s["region"]}/{s["habitat"]}) holds no species')

# FIELDS link (fail open)
SEASONS_LINK = None
sdir = ROOT / 'seasons/registry'
if sdir.is_dir():
    found = []

    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get('id'), str) and 'crawfish' in o['id']:
                found.append(o['id'])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    for f in sorted(sdir.glob('*.json')):
        walk(json.loads(f.read_text(encoding='utf-8')))
        if found:
            SEASONS_LINK = {'registry': str(f.relative_to(ROOT)), 'id': sorted(found)[0]}
            break
for sp in SPECIES:
    sp['seasons_link'] = SEASONS_LINK if sp['id'] == 'red-swamp-crawfish' else None

counts = {'spots': len(spots), 'hidden': len(HIDDEN), 'rods': len(RODS), 'baits': len(BAITS), 'species': len(SPECIES),
          'by_world': {w: sum(1 for s in spots if s['world'] == w) for w in ('parishes', 'bay', 'wilds')}}
body = {
    'pack': 'outdoors', 'version': 1, 'provenance': {'catalog': 'AUTHORED', 'spots': 'DERIVED from AUTHORED water'},
    'frame': 'page frame: x = east metres, z = -north metres from the region origin_m (parishes/bay); wilds = the world x/z',
    'rules': {'coast_max_m': COAST_MAX_M, 'shore_step_m': SHORE_STEP_M, 'coast_inland_m': COAST_INLAND_M,
              'wilds_habitat': WILDS_HABITAT, 'wilds_region': WILDS_REGION},
    'regions': REGIONS, 'habitats': HABITATS, 'times': TIMES, 'rods': RODS, 'baits': list(BAITS.values()),
    'species': SPECIES, 'spots': spots, 'hidden': HIDDEN, 'seasons_link': SEASONS_LINK,
    'worlds': {'parishes': PARISH_IDS, 'bay': BAY_IDS, 'wilds': WILDS_IDS},
    'honesty': HONESTY, 'counts': counts,
}
inputs = ['outdoors/authored/catalog.json', 'outdoors/wilds_shore.mjs', 'wilds/core.mjs', 'wilds/registry/wilds.json',
          'parishes/registry/world.json', 'bayarea/registry/world.json', 'bayarea/registry/bayarea.json',
          'outdoors/build.py']
h = hashlib.sha256()
for rel in inputs:
    h.update(rel.encode() + b'\0' + (ROOT / rel).read_bytes())
if SEASONS_LINK:
    inputs.append(SEASONS_LINK['registry'])   # the FIELDS link is part of what this registry says
body['inputs'] = inputs
body['source_stamp'] = h.hexdigest()[:16]
body['source_stamp_sha256'] = h.hexdigest()
text = json.dumps(body, indent=1, ensure_ascii=False) + '\n'
if '--check' in sys.argv:
    if not OUT.exists() or OUT.read_text(encoding='utf-8') != text:
        print('outdoors: registry is stale - run python3 outdoors/build.py')
        sys.exit(1)
    print('outdoors: registry current')
else:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding='utf-8')
    print(f'outdoors: {counts["spots"]} spots ({counts["by_world"]}) | {counts["hidden"]} hidden | {counts["rods"]} rods | '
          f'{counts["baits"]} baits | {counts["species"]} species | stamp {body["source_stamp"]}')
