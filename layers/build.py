#!/usr/bin/env python3
"""Parish layers: where the union training simulators, the simulated tasks, the
lessons and the Cognition.X K-12 units stand in each parish of the walkable
world, and the three paths a player may follow through them.

Nothing here is new content. Every station points at an entry that already
exists in the registry that owns it, and its title is read from there:

  trade-sim   sims/registry/sims.json          a simulator seat
  task        tasks/registry/tasks.json         a simulated task (practice)
  lesson      lessons/registry/lessons.json     a lesson (unverified general practice)
  k12-unit    schools/registry/schools.json     a flipped unit of the schools/ pack,
                                                shown under the name "Cognition.X K-12";
                                                every district stays a PROPOSED partner

Which parish holds which seat is a play layout, not a fact: seats are dealt to
parishes in turn (sorted seat ids, sorted FIPS), each seat brings its first
launchable task, one K-12 unit whose floor time uses it and one lesson that puts
a learner in it. A station's spot is AUTHORED by a rule: a grid of candidate
points inside the parish's RECORDED land outline, taken nearest a landmark first
(when the parish source lists landmarks), then spread out. It is not the site of
any real training facility, school or employer, and no address is implied.

A launch link is written only where the target page reads it (tasks/build.py's
PARAM_READS are reused for the 3D and wilds pages; the lessons page's fromHash
for #lesson-<id>; the schools page's band sections for #band-<band>). Otherwise
the station carries href null and says why. Paths are suggestions: nothing is
gated, and a player can switch path at any time.

Parishes come from parishes/registry/parishes.json (PARISH_CONTRACT): the
computed selection, RECORDED coarse outlines, the shared WORLD metre frame, the
adjacency and the AUTHORED landmarks. A landmark's id here is DERIVED from its
name (lower-case, kebab). Each station also carries world_m and local_m in the
parish pack's own frames (same formula, same R).

  python3 layers/build.py [--check]
"""
import hashlib
import importlib.util
import json
import math
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'layers.json'

PARISHES_PATH = 'parishes/registry/parishes.json'
SIMS_PATH = 'sims/registry/sims.json'
TASKS_PATH = 'tasks/registry/tasks.json'
LESSONS_PATH = 'lessons/registry/lessons.json'
SCHOOLS_PATH = 'schools/registry/schools.json'
HALLS_PATH = 'pack/registry/halls.json'
PAGE_3D = 'web/trade_craft_3d.html'
PAGE_LESSONS = 'web/trade_craft_lessons.html'
PAGE_SCHOOLS = 'web/trade_craft_schools.html'
REGION_CAMPUS = 'new-orleans'   # unions/registry/campuses.json key of the campus in this region
K12_BAND = '9-10'
SEATS_PER_PARISH = 2   # AUTHORED play layout: each parish is dealt this many seats, in turn   # the schools band whose section lists each unit through the floor (its seat time)

LAYERS = {
    'trade-sim': {'label': 'Union training simulators', 'content_from': SIMS_PATH},
    'task': {'label': 'Simulated tasks', 'content_from': TASKS_PATH},
    'lesson': {'label': 'Lessons', 'content_from': LESSONS_PATH},
    'k12-unit': {'label': 'Cognition.X K-12', 'content_from': SCHOOLS_PATH + ' units (the schools/ pack)'},
}
PATHS = (('trade', 'Trade path'), ('k12', 'K-12 path'), ('explorer', 'Explorer / free play'))
HONESTY = {
    'play': ('Stations, paths, rings and badges are play. They are kept on this device only, they certify '
             'nothing and they never enter a completion record.'),
    'placement': ('Where a station stands is AUTHORED by a rule inside the parish\'s RECORDED coarse (1:10m) '
                  'outline. It is not the site of any real training facility, school or employer, and no '
                  'address is implied.'),
    'k12': ('"Cognition.X K-12" is the name of this layer; its content is the schools/ pack\'s flipped units. '
            'Every school district named there is a PROPOSED partner: no district has reviewed or agreed, '
            'and no agreement exists.'),
    'lessons': 'Lessons are unverified general practice, exactly as the lessons pack states.',
    'launch': ('A launch link is written only where the target page reads it; a station no link reaches says '
               'why. Suggested lessons are an order worth trying, never a lock: every path is open, and you '
               'can switch path at any time.'),
}


def fail(msg):
    raise SystemExit(f'layers/build: {msg}')


def story_paths():
    """layers/paths.py: the seven adventure paths + side stories (wave 7) -> layers/registry/paths.json."""
    spec = importlib.util.spec_from_file_location('layers_paths', HERE / 'paths.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        fail(f'{where} has no "{k}"')
    return d[k]


def load(rel):
    p = ROOT / rel
    if not p.exists():
        fail(f'missing source {rel}')
    return json.loads(p.read_text(encoding='utf-8'))


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


# ---------------------------------------------------------------- geometry
def polygons(outline, where):
    crs = need(outline, 'crs', where)
    if not crs.startswith('WGS84'):
        fail(f'{where}: outline crs {crs!r} is not WGS84 [lng, lat]')
    return need(outline, 'polygons', where)


def slug(name):
    s = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    if not s:
        fail(f'landmark name {name!r} gives an empty id')
    return s


def ltp(lng, lat, origin, R):
    """parishes/ ltp_formula: [east_m, north_m] about origin {lat, lng}."""
    lat0, lng0 = need(origin, 'lat', 'frame origin'), need(origin, 'lng', 'frame origin')
    return [round(R * math.cos(math.radians(lat0)) * math.radians(lng - lng0), 2), round(R * math.radians(lat - lat0), 2)]


def in_ring(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def in_land(x, y, polys):
    """Inside an outer ring and outside all of that polygon's holes."""
    for poly in polys:
        if in_ring(x, y, poly[0]) and not any(in_ring(x, y, h) for h in poly[1:]):
            return True
    return False


def metres(a, b):
    """Equirectangular distance in metres between two (lon, lat) points (placement spacing only)."""
    k = math.cos(math.radians((a[1] + b[1]) / 2))
    return math.hypot((a[0] - b[0]) * k, a[1] - b[1]) * 111_320


def place_all(n, polys, landmarks, where):
    """n AUTHORED spots inside the land: a 48x48 candidate grid over the outline's
    box, kept only inside the land; nearest a landmark first (round robin over the
    landmarks), then farthest-point spread. Deterministic."""
    xs = [p[0] for poly in polys for p in poly[0]]
    ys = [p[1] for poly in polys for p in poly[0]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    G = 48
    cand = []
    for i in range(G):
        for j in range(G):
            x = x0 + (x1 - x0) * (i + 0.5) / G
            y = y0 + (y1 - y0) * (j + 0.5) / G
            if in_land(x, y, polys):
                cand.append((round(x, 6), round(y, 6)))
    if len(cand) < n:
        fail(f'{where}: only {len(cand)} candidate spots inside the land outline for {n} stations')
    cell = metres((x0, y0), (x0 + (x1 - x0) / G, y0 + (y1 - y0) / G))
    chosen, near = [], []
    lms = [(slug(need(l, 'name', where)), (need(l, 'lng', where), need(l, 'lat', where))) for l in landmarks]
    k = 0
    while len(chosen) < n and lms and k < n:
        lid, lp = lms[k % len(lms)]
        free = [c for c in cand if c not in chosen and all(metres(c, o) >= cell for o in chosen)]
        if not free:
            break
        best = min(free, key=lambda c: (metres(c, lp), c))
        if metres(best, lp) > 4 * cell:
            break
        chosen.append(best)
        near.append(lid)
        k += 1
    if not chosen:
        cx, cy = sum(c[0] for c in cand) / len(cand), sum(c[1] for c in cand) / len(cand)
        chosen.append(min(cand, key=lambda c: (metres(c, (cx, cy)), c)))
        near.append(None)
    while len(chosen) < n:
        best = max((c for c in cand if c not in chosen), key=lambda c: (min(metres(c, o) for o in chosen), c))
        chosen.append(best)
        near.append(None)
    return chosen, near


# ---------------------------------------------------------------- launch checks
def param_reads():
    """tasks/build.py's PARAM_READS, reused: the exact builder fragments that
    prove a page reads a parameter. Checked here again, fail closed."""
    spec = importlib.util.spec_from_file_location('tasks_build', ROOT / 'tasks' / 'build.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    reads = mod.PARAM_READS
    for (builder, param), frag in reads.items():
        if frag not in (ROOT / builder).read_text(encoding='utf-8'):
            fail(f'{builder} no longer reads "{param}" (tasks/build.py PARAM_READS); refusing to write a link')
    return {param for (_b, param) in reads}


LESSON_READ = ('web/build_lessons.py',
               "const a = id.indexOf('lesson-') === 0 ? document.getElementById(id) : null;")
LESSON_ID = ('web/build_lessons.py', 'id="lesson-{E(lid)}"')
SCHOOL_BAND = ('web/build_schools.py', 'id="band-{E(band)}"')
SCHOOL_UNIT = ('web/build_schools.py', '<a href="trade_craft_lessons.html#course-{E(hall)}">')


def main():
    params = param_reads()
    for builder, frag in (LESSON_READ, LESSON_ID, SCHOOL_BAND, SCHOOL_UNIT):
        if frag not in (ROOT / builder).read_text(encoding='utf-8'):
            fail(f'{builder} no longer carries {frag!r}; refusing to write a link that relies on it')
    for p in ('hall', 'sim'):
        if p not in params:
            fail(f'tasks/build.py PARAM_READS no longer proves the 3D page reads ?{p}')
    lessons_html = (ROOT / PAGE_LESSONS).read_text(encoding='utf-8')
    schools_html = (ROOT / PAGE_SCHOOLS).read_text(encoding='utf-8')

    psrc_path = PARISHES_PATH
    parish_source = PARISHES_PATH
    psrc = load(psrc_path)
    pdict = need(psrc, 'parishes', psrc_path)
    selected = need(need(psrc, 'selection', psrc_path), 'selected', f'{psrc_path}#selection')
    if sorted(pdict) != sorted(selected):
        fail(f'{psrc_path}: parishes {sorted(pdict)} differ from selection.selected {sorted(selected)}')
    parishes = [pdict[f] for f in sorted(selected)]
    frames = need(psrc, 'frames', psrc_path)
    R = need(frames, 'R_m', f'{psrc_path}#frames')
    world_origin = need(need(frames, 'world', f'{psrc_path}#frames'), 'origin', f'{psrc_path}#frames.world')

    sims = need(load(SIMS_PATH), 'sims', SIMS_PATH)
    tasks = need(load(TASKS_PATH), 'tasks', TASKS_PATH)
    lreg = load(LESSONS_PATH)
    L = need(lreg, 'lessons', LESSONS_PATH)
    layer_of = {lid: int(d) for d, ids in need(need(lreg, 'ladder', LESSONS_PATH), 'layers', LESSONS_PATH).items()
                for lid in ids}
    key_order = list(L)
    schools = load(SCHOOLS_PATH)
    units = need(schools, 'units', SCHOOLS_PATH)
    hall_name = {need(h, 'slug', HALLS_PATH): need(h, 'name', HALLS_PATH)
                 for h in need(load(HALLS_PATH), 'halls', HALLS_PATH)}
    band_ids = [need(b, 'band', SCHOOLS_PATH) for b in need(schools, 'bands', SCHOOLS_PATH)]
    if K12_BAND not in band_ids:
        fail(f'{SCHOOLS_PATH} has no band {K12_BAND}')
    m = re.search(r'id="band-' + re.escape(K12_BAND) + r'"(.*?)(?:id="band-|$)', schools_html, re.S)
    if not m:
        fail(f'{PAGE_SCHOOLS} has no section id="band-{K12_BAND}"')
    band_section = m.group(1)

    def course_order(ids):
        for i in ids:
            if i not in layer_of:
                fail(f'{LESSONS_PATH}#ladder.layers holds no layer for lesson {i!r}')
        return sorted(set(ids), key=lambda i: (layer_of[i], key_order.index(i)))

    def lessons_in_seat(sid):
        return course_order([lid for lid, les in L.items()
                             if any(need(s, 'kind', lid) == 'sim' and need(s, 'sim', lid) == sid
                                    for s in need(les, 'steps', lid))])

    def lesson_launch(lid):
        if f'id="lesson-{lid}"' not in lessons_html:
            return {'href': None, 'why': f'{PAGE_LESSONS} carries no anchor lesson-{lid}; rebuild the lessons page'}
        return {'href': f'{PAGE_LESSONS}#lesson-{lid}', 'lands': 'section', 'param': ['#lesson-']}

    task_ix = {need(t, 'id', TASKS_PATH): i for i, t in enumerate(tasks)}
    sim_ids = sorted(sims)
    N = len(parishes)
    out = []
    counts = {'parishes': N, 'stations': 0, 'by_layer': {k: 0 for k in LAYERS}, 'launchable': 0}
    for pi, p in enumerate(parishes):
        where = f'{psrc_path}#{need(p, "fips", psrc_path)}'
        fips = need(p, 'fips', where)
        name = need(p, 'full_name', where)
        local_origin = need(need(p, 'frame', where), 'origin', f'{where}.frame')
        polys = polygons(need(p, 'outline', where), where)
        landmarks = need(p, 'landmarks', where)
        # seats dealt in turn: parish pi gets seats pi*K .. pi*K+K-1 (mod the seat count); a seat
        # dealt again in a later parish brings its next task, unit and lesson (occurrence k)
        mine = [sim_ids[(pi * SEATS_PER_PARISH + j) % len(sim_ids)] for j in range(SEATS_PER_PARISH)]
        occ = {sid: (pi * SEATS_PER_PARISH + j) // len(sim_ids) for j, sid in enumerate(mine)}
        mine = sorted(mine)   # the trade path walks its seats in seat-id order
        trade, k12 = [], []
        used_units = set()
        for sid in mine:
            sim = sims[sid]
            sname = need(sim, 'name', f'{SIMS_PATH}#sims.{sid}')
            h0 = need(sim, 'halls', f'{SIMS_PATH}#sims.{sid}')[0]
            seat_lessons = lessons_in_seat(sid)
            trade.append({'layer': 'trade-sim', 'key': f'sim-{sid}', 'title': sname,
                          'ref': {'registry': SIMS_PATH, 'id': sid, 'source': f'{SIMS_PATH}#sims.{sid}'},
                          'launch': {'href': f'{PAGE_3D}?hall={h0}&sim={sid}', 'lands': 'seat',
                                     'param': ['hall', 'sim']},
                          'suggests': seat_lessons[:2]})
            seat_tasks = [t for t in tasks if need(t, 'seat', TASKS_PATH) == sid
                          and need(need(t, 'launch', TASKS_PATH), 'href', TASKS_PATH)]
            # the region's own campus first (new-orleans scenarios), then registry order
            seat_tasks.sort(key=lambda t: (need(need(t, 'place', t['id']), 'campus', t['id']) != REGION_CAMPUS,
                                           task_ix[t['id']]))
            if seat_tasks:
                t = seat_tasks[occ[sid] % len(seat_tasks)]
                tl = t['launch']
                for prm in need(tl, 'param', t['id']):
                    if prm not in params:
                        fail(f'{TASKS_PATH}#{t["id"]}: launch param {prm!r} is not proved by tasks/build.py PARAM_READS')
                trade.append({'layer': 'task', 'key': f'task-{t["id"]}', 'title': need(t, 'title', t['id']),
                              'ref': {'registry': TASKS_PATH, 'id': t['id'],
                                      'source': f'{TASKS_PATH}#tasks[{task_ix[t["id"]]}]'},
                              'launch': {'href': tl['href'], 'lands': need(tl, 'lands', t['id']),
                                         'param': tl['param']},
                              'suggests': course_order(need(t, 'requires', t['id']))[:2]})
            seat_units = [(ui, u) for ui, u in enumerate(units)
                          if sid in need(u, 'floor_sims', f'{SCHOOLS_PATH}#units[{ui}]')]
            if seat_units:
                r = occ[sid] % len(seat_units)
                seat_units = seat_units[r:] + seat_units[:r]
            for ui, u in seat_units:
                uh = need(u, 'hall', f'{SCHOOLS_PATH}#units[{ui}]')
                if uh in used_units:
                    continue
                if uh not in hall_name:
                    fail(f'{SCHOOLS_PATH}#units[{ui}]: hall {uh!r} is not in {HALLS_PATH}')
                used_units.add(uh)
                if f'#course-{uh}"' in band_section:
                    launch = {'href': f'{PAGE_SCHOOLS}#band-{K12_BAND}', 'lands': 'section', 'param': ['#band-']}
                else:
                    launch = {'href': None, 'why': f'{PAGE_SCHOOLS} band {K12_BAND} does not list the {uh} unit'}
                hall_lessons = course_order([lid for lid, les in L.items() if need(les, 'hall', lid) == uh])
                k12.append({'layer': 'k12-unit', 'key': f'unit-{uh}',
                            'title': f'{hall_name[uh]}: flipped unit', 'ref':
                                {'registry': SCHOOLS_PATH, 'id': uh, 'source': f'{SCHOOLS_PATH}#units[{ui}]'},
                            'launch': launch, 'suggests': hall_lessons[:2]})
                break
            anchored = [lid for lid in seat_lessons if f'id="lesson-{lid}"' in lessons_html]
            pool = anchored or seat_lessons
            pick = [pool[occ[sid] % len(pool)]] if pool else []
            for lid in pick:
                k12.append({'layer': 'lesson', 'key': f'lesson-{lid}', 'title': need(L[lid], 'title', lid),
                            'ref': {'registry': LESSONS_PATH, 'id': lid, 'source': f'{LESSONS_PATH}#lessons.{lid}'},
                            'launch': lesson_launch(lid),
                            'suggests': [x for x in course_order(seat_lessons) if layer_of[x] < layer_of[lid]][:2]})
        # a station key appears once per parish even if two seats bring the same entry
        seen, rows = set(), []
        for r in trade + k12:
            if r['key'] not in seen:
                seen.add(r['key'])
                rows.append(r)
        spots, near = place_all(len(rows), polys, landmarks, where)
        stations = []
        for r, (x, y), nl in zip(rows, spots, near):
            sid = f'st-{fips}-{r["key"]}'
            for lid in r['suggests']:
                if lid not in L:
                    fail(f'{sid}: suggests lesson {lid!r}, which {LESSONS_PATH} does not hold')
            st = {'id': sid, 'layer': r['layer'], 'ref': r['ref'], 'title': r['title'],
                  'at': {'lon': x, 'lat': y}, 'world_m': ltp(x, y, world_origin, R),
                  'local_m': ltp(x, y, local_origin, R), 'near': nl, 'launch': r['launch'],
                  'suggests': r['suggests'], 'treasure': f'treasure-station-{sid}', 'provenance': 'AUTHORED'}
            stations.append(st)
            counts['by_layer'][r['layer']] += 1
            counts['launchable'] += 1 if r['launch']['href'] else 0
        counts['stations'] += len(stations)
        sid_of = {r['key']: f'st-{fips}-{r["key"]}' for r in rows}
        trade_steps = [sid_of[r['key']] for r in trade]
        # K-12 path: the units in schools/ registry order, then the lessons in ladder (course) order
        k12_units = [r for r in k12 if r['layer'] == 'k12-unit']
        k12_units.sort(key=lambda r: int(r['ref']['source'].rsplit('[', 1)[1].rstrip(']')))
        k12_less = course_order([r['ref']['id'] for r in k12 if r['layer'] == 'lesson'])
        k12_steps = [sid_of[r['key']] for r in k12_units] + [sid_of[f'lesson-{lid}'] for lid in k12_less]
        explorer = [f'treasure-parish-{fips}-arrive'] + \
                   [f'treasure-parish-{fips}-lm-{slug(need(l, "name", where))}' for l in landmarks] + \
                   [f'egg-parish-{fips}-word']
        paths = []
        for pid, label in PATHS:
            steps = {'trade': list(dict.fromkeys(trade_steps)), 'k12': list(dict.fromkeys(k12_steps)),
                     'explorer': explorer}[pid]
            paths.append({'id': pid, 'label': label, 'steps': steps, 'gated': False})
        out.append({'fips': fips, 'name': name, 'landmarks': [
            {'id': slug(need(l, 'name', where)), 'name': need(l, 'name', where), 'kind': need(l, 'kind', where)}
            for l in landmarks],
            'adjacent': sorted(need(p, 'adjacent', where)), 'stations': stations, 'paths': paths})

    # generated pages are not stamped (the schools page lists quests, which read this registry: a stamp over it
    # would make a cycle); layers/test.mjs re-checks every anchor in the pages themselves instead
    read = [psrc_path, SIMS_PATH, TASKS_PATH, LESSONS_PATH, SCHOOLS_PATH, HALLS_PATH,
            'tasks/build.py', 'web/build_3d.py', 'web/build_lessons.py', 'web/build_schools.py', 'layers/build.py']
    sources = {r: sha16((ROOT / r).read_bytes()) for r in read}
    doc = {
        'pack': 'layers',
        'source_stamp': sha16(''.join(f'{k}:{v}\n' for k, v in sources.items()).encode()),
        'sources': sources,
        'parish_source': parish_source,
        'honesty': HONESTY,
        'k12_districts': need(need(schools, 'honesty', SCHOOLS_PATH), 'districts', SCHOOLS_PATH),
        'layers': LAYERS,
        'counts': counts,
        'parishes': out,
    }
    text = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
    if '--check' in sys.argv:
        if not OUT.exists() or OUT.read_text(encoding='utf-8') != text:
            sys.exit(f'{OUT.relative_to(ROOT)} is stale: run python3 layers/build.py')
        print(f'{OUT.relative_to(ROOT)} is current')
        story_paths().run(doc, text, True)
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding='utf-8')
    story_paths().run(doc, text, False)
    print(f'wrote {OUT.relative_to(ROOT)}: {counts} from {parish_source}; parishes: '
          + ', '.join(f'{p["fips"]} {p["name"]}' for p in out))


if __name__ == '__main__':
    main()
