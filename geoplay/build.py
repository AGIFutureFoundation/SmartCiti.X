"""Builds geoplay/registry/geoplay.json and spatial/registry/drops_geopose.json:
the geo-anchored training-drop layer (the "Pokemon Go style" idea, as play).

A STOP is a public place that an existing registry already pins at a real
coordinate; a DROP is one existing task from tasks/registry/tasks.json pinned
to a stop, with the lessons that task already requires. Nothing is invented:

  * stops come only from geo/registry/campuses_geo.json (an anchor) or
    restoration/registry/restoration.json (a pinned site), by the rules in
    geoplay/source/rules.json; a record that fails the public-place rule is
    REFUSED with its reason and listed, never silently dropped;
  * a stop with no task the tasks registry puts on the globe is listed as
    unpinned, never shown with an empty drop;
  * the coordinate, its provenance word and its source string are the
    registry's own, copied, never upgraded;
  * each stop also gets a GeoPose 1.0 Basic-YPR pose (same encoding as
    spatial/registry/geopose.json, height and heading UNKNOWN) written to
    spatial/registry/drops_geopose.json.

Safety rule the build enforces: a stop's source record must state that the
place is public and be a university, college or public park, and must not name
a port, laboratory, station, pier, shipyard, cleanup site, wetland, levee and
so on. Failing records go to `refused`. The build also stops if a radius leaves
the declared bounds.

No learner location exists in this pack: it holds public pins and rules only.
Fails closed: a missing registry field stops the build with a named error.
"""
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / 'registry' / 'geoplay.json'
POSE_OUT = ROOT / 'spatial' / 'registry' / 'drops_geopose.json'

GEO_PATH = 'geo/registry/campuses_geo.json'
RESTO_PATH = 'restoration/registry/restoration.json'
TASKS_PATH = 'tasks/registry/tasks.json'
LESSONS_PATH = 'lessons/registry/lessons.json'
GEOPOSE_PATH = 'spatial/registry/geopose.json'
UNIONS_PATH = 'unions/registry/campuses.json'
RULES_PATH = 'geoplay/source/rules.json'


def need(d, k, where):
    if not isinstance(d, dict):
        raise TypeError(f'{where}: expected an object to read {k!r} from, got {type(d).__name__}')
    if k not in d:
        raise KeyError(f'{where}: required field {k!r} is missing')
    return d[k]


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def words(s):
    return set(re.findall(r"[a-z]+", s.lower()))


geo = load(GEO_PATH)
resto = load(RESTO_PATH)
tasks_reg = load(TASKS_PATH)
lessons_reg = load(LESSONS_PATH)
geopose = load(GEOPOSE_PATH)
campuses_reg = need(load(UNIONS_PATH), 'campuses', UNIONS_PATH)
rules = load(RULES_PATH)

RAD = need(rules, 'radius_m', RULES_PATH)
R_MIN, R_MAX = need(RAD, 'min', 'rules#radius_m'), need(RAD, 'max', 'rules#radius_m')
R_BY = need(RAD, 'by_class', 'rules#radius_m')
MAX_DROPS = need(rules, 'max_drops_per_stop', RULES_PATH)
CLASSES = need(rules, 'classes', RULES_PATH)
DENY = set(need(rules, 'deny_words', RULES_PATH))
ON_GLOBE = need(rules, 'task_places_on_globe', RULES_PATH)
SAFETY = need(rules, 'safety_line', RULES_PATH)
LESSONS = need(lessons_reg, 'lessons', LESSONS_PATH)
TASKS = need(tasks_reg, 'tasks', TASKS_PATH)
assert 0 < R_MIN <= R_MAX, 'rules: radius bounds are not ordered'
assert set(R_BY) == set(CLASSES), 'rules: a class has no radius, or a radius has no class'
for c, r in R_BY.items():
    assert R_MIN <= r <= R_MAX, f'rules: the {c} radius {r} is outside {R_MIN}..{R_MAX}'
assert SAFETY == 'Stay aware of your surroundings; do not enter roads or private property.', \
    'the visible safety line was changed'

# tasks the registry puts on the globe: launchable, at a campus or a restoration site
TASK_OK = []
for t in TASKS:
    pl = need(t, 'place', f'tasks.json#{t["id"]}')
    la = need(t, 'launch', f'tasks.json#{t["id"]}')
    if need(la, 'href', f'tasks.json#{t["id"]}.launch') is None:
        continue
    if need(pl, 'kind', f'tasks.json#{t["id"]}.place') in ON_GLOBE and need(pl, 'campus', f'tasks.json#{t["id"]}.place') in campuses_reg:
        TASK_OK.append(t)

stops, refused, unpinned = [], [], []
used_tasks = set()


def refuse(ref, name, why):
    refused.append({'ref': ref, 'name': name, 'reason': why})


def drops_for(stop_src_kind, key, campus, take_from):
    """tasks that belong at this stop: a restoration site's own tasks, or the
    campus-kind tasks of the campus, in registry order, not yet used."""
    if stop_src_kind == 'restoration-site':
        pool = [t for t in TASK_OK if t['place']['kind'] == 'restoration-site' and t['place']['id'] == key]
    else:
        pool = [t for t in TASK_OK if t['place']['kind'] == 'campus' and t['place']['campus'] == campus]
    pool = [t for t in pool if t['id'] not in used_tasks]
    return pool[:take_from]


def drop_row(t):
    reqs = need(t, 'requires', f'tasks.json#{t["id"]}')
    for lid in reqs:
        assert lid in LESSONS, f'tasks.json#{t["id"]} requires lesson {lid!r} that lessons.json does not carry'
    return {'id': 'drop-' + t['id'], 'task': t['id'], 'title': t['title'], 'task_kind': t['kind'],
            'task_place': {'kind': t['place']['kind'], 'id': t['place']['id'], 'campus': t['place']['campus']},
            'provenance': 'DERIVED', 'lessons': list(reqs)}


# ---- 1. anchors: public universities and colleges -------------------------
C = need(geo, 'campuses', GEO_PATH)
for campus, lst in need(geo, 'anchors', GEO_PATH).items():
    for a in lst:
        w = f'{GEO_PATH}#anchors.{campus}[{need(a, "name", GEO_PATH + "#anchors." + campus + "[]")}]'
        name, blurb, src = need(a, 'name', w), need(a, 'blurb', w), need(a, 'source', w)
        lat, lng, pv = need(a, 'lat', w), need(a, 'lng', w), need(a, 'provenance', w)
        ref = f'anchor:{campus}:{slug(name)}'
        cls = CLASSES['public-university']
        ws = words(name + ' ' + src)
        hit = sorted(ws & DENY)
        if hit:
            refuse(ref, name, 'its name or source names a restricted or non-campus place type: ' + ', '.join(hit))
            continue
        if not (words(name + ' ' + blurb) & set(cls['must_name_one_of'])):
            refuse(ref, name, 'not a university or college campus (a city or other place)')
            continue
        if not (words(blurb + ' ' + src) >= {cls['must_state']}):
            refuse(ref, name, 'the registry record does not state that the place is public')
            continue
        picks = drops_for('campus', None, campus, MAX_DROPS)
        if not picks:
            unpinned.append({'ref': ref, 'name': name, 'campus': campus,
                             'reason': 'public campus passes the rule, but tasks/registry/tasks.json puts no campus-level task on the globe for this campus'})
            continue
        used_tasks.update(t['id'] for t in picks)
        stops.append({
            'id': 'stop-' + campus + '-' + slug(name), 'name': name, 'class': 'public-university',
            'campus': campus, 'lat': lat, 'lng': lng, 'coordinate_provenance': pv,
            'source_ref': w, 'source_text': src, 'public_basis': blurb,
            'radius_m': R_BY['public-university'],
            'drops': [drop_row(t) for t in picks]})

# ---- 2. pinned restoration sites: public parks ----------------------------
for s in need(resto, 'sites', RESTO_PATH):
    w = f'{RESTO_PATH}#sites[{need(s, "id", RESTO_PATH + "#sites[]")}]'
    sid, name = need(s, 'id', w), need(s, 'name', w)
    ref = f'restoration-site:{sid}'
    cls = CLASSES['public-park']
    if not need(s, 'pin', w) or need(s, 'lat', w) is None:
        refuse(ref, name, 'not pinned: the registry holds no single point for it')
        continue
    if need(s, 'walkable', w) is not True:
        refuse(ref, name, 'the registry marks it not walkable: ' + str(need(s, 'walkable_reason', w)))
        continue
    hit = sorted(words(name + ' ' + need(s, 'habitat', w)) & DENY)
    if hit:
        refuse(ref, name, 'its name or habitat names a restricted or non-park place type: ' + ', '.join(hit))
        continue
    if need(s, 'category', w) != cls['category'] or need(s, 'ground', w) != cls['ground']:
        refuse(ref, name, f'ground is {s["ground"]!r}, not the upland a public park stop needs (water, marsh, mudflat and levee ground are refused)')
        continue
    if not any(o in need(s, 'org', w) for o in cls['org_must_match']):
        refuse(ref, name, 'its operator is not a named public park authority in the rules')
        continue
    if not any(n in name for n in cls['name_must_match']):
        refuse(ref, name, 'its name does not say it is a park or point')
        continue
    picks = drops_for('restoration-site', sid, need(s, 'campus', w), MAX_DROPS)
    if not picks:
        unpinned.append({'ref': ref, 'name': name, 'campus': s['campus'],
                         'reason': 'public park passes the rule, but no task is pinned to this site in tasks/registry/tasks.json'})
        continue
    used_tasks.update(t['id'] for t in picks)
    stops.append({
        'id': 'stop-' + sid, 'name': name, 'class': 'public-park', 'campus': s['campus'],
        'lat': s['lat'], 'lng': s['lng'],
        'coordinate_provenance': 'AUTHORED',
        'source_ref': w, 'source_text': 'restoration/registry/restoration.json ' + s['source_url'],
        'public_basis': 'operated by ' + s['org'] + '; ' + s['habitat'],
        'radius_m': R_BY['public-park'],
        'drops': [drop_row(t) for t in picks]})

# ---- invariants -----------------------------------------------------------
for st in stops:
    assert R_MIN <= st['radius_m'] <= R_MAX, f'{st["id"]}: radius outside bounds'
    assert -90 <= st['lat'] <= 90 and -180 <= st['lng'] <= 180, f'{st["id"]}: coordinate out of range'
    assert 1 <= len(st['drops']) <= MAX_DROPS
ids = [st['id'] for st in stops]
assert len(set(ids)) == len(ids), 'stop id collision'
dids = [d['id'] for st in stops for d in st['drops']]
assert len(set(dids)) == len(dids), 'a task is pinned twice'
assert stops, 'no stop passed the public-place rule'
n_refused_unpinned = len(refused)

# ---- GeoPose anchors -------------------------------------------------------
H_UNKNOWN = 'UNKNOWN - not held by this bundle; 0.0 is a placeholder, not a measurement'
O_UNKNOWN = 'UNKNOWN - no heading is recorded; 0 is a placeholder'
poses = []
for st in stops:
    st['geopose_ref'] = 'training-drop-stop:' + st['id']
    poses.append({
        'subject': {'kind': 'training-drop-stop', 'id': st['id'], 'name': st['name'],
                    'campus': st['campus'], 'ref': st['geopose_ref']},
        'geopose': {'position': {'lat': st['lat'], 'lon': st['lng'], 'h': 0.0},
                    'orientation': {'yaw': 0, 'pitch': 0, 'roll': 0}},
        'provenance': {'position_horizontal': st['coordinate_provenance'], 'source': st['source_ref'],
                       'h_provenance': H_UNKNOWN, 'orientation_provenance': O_UNKNOWN}})

reads = [GEO_PATH, RESTO_PATH, TASKS_PATH, LESSONS_PATH, GEOPOSE_PATH, UNIONS_PATH, RULES_PATH]
# geopose.json is read only for its encoding, media type and CRS words, so only those words
# stamp this pack (the rest of that file belongs to spatial/build.py and moves with it)
stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()
                       + b''.join((ROOT / r).read_bytes() for r in reads if r != GEOPOSE_PATH)
                       + json.dumps([geopose['encoding'], geopose['media_type'], geopose['crs']]).encode()).hexdigest()[:16]
by_class = {c: sum(1 for st in stops if st['class'] == c) for c in CLASSES}
counts = {'stops': len(stops), 'drops': len(dids), 'stops_by_class': by_class,
          'campuses_with_stops': len({st['campus'] for st in stops}),
          'unpinned_public_places': len(unpinned), 'refused': len(refused),
          'anchors_read': sum(len(v) for v in geo['anchors'].values()), 'restoration_sites_read': len(resto['sites']),
          'tasks_on_globe_launchable': len(TASK_OK), 'tasks_pinned': len(dids),
          'lessons_linked': len({l for st in stops for d in st['drops'] for l in d['lessons']}),
          'geoposes': len(poses)}
doc = {
    'pack': 'geoplay', 'product': need(lessons_reg, 'product', LESSONS_PATH),
    'pack_version': need(lessons_reg, 'pack_version', LESSONS_PATH),
    'source_stamp': stamp, 'reads': reads,
    'honesty': {'play': rules['play'], 'no_hosting': rules['no_hosting'], 'privacy': rules['privacy'],
                'siting': 'A stop is the registry\'s own map point for a public place; it is not a surveyed entrance and no address is recorded. '
                          'A human must visit and confirm a place before any drop is offered outside this map.',
                'provenance': 'Each stop keeps the coordinate provenance word of the registry it was read from (RECORDED / DERIVED / AUTHORED); each pairing of a task to a stop is DERIVED by the rule in geoplay/build.py, with no content written here.',
                'safety_more': rules['safety_more']},
    'safety_line': SAFETY,
    'rules': {'radius_m': {'min': R_MIN, 'max': R_MAX, 'by_class': R_BY, 'why': RAD['why']},
              'accuracy_max_m': need(rules, 'accuracy_max_m', RULES_PATH), 'max_drops_per_stop': MAX_DROPS,
              'classes': {c: {k: v for k, v in CLASSES[c].items() if k not in ('from',)} for c in CLASSES},
              'deny_words': sorted(DENY), 'task_places_on_globe': ON_GLOBE},
    'ar': rules['ar'],
    'geopose': {'file': 'spatial/registry/drops_geopose.json', 'encoding': geopose['encoding'],
                'media_type': geopose['media_type'], 'crs': geopose['crs']},
    'counts': counts, 'stops': stops, 'unpinned': unpinned, 'refused': refused,
}
pose_doc = {
    'pack': 'smartcitix-trade-craft-academy-spatial-fabric-drops', 'product': doc['product'],
    'pack_version': doc['pack_version'], 'source_stamp': stamp,
    'encoding': geopose['encoding'], 'media_type': geopose['media_type'], 'crs': geopose['crs'],
    'honesty': {'geopose': 'Same encoding and the same placeholder rule as spatial/registry/geopose.json: every pose is {position: {lat, lon, h}, orientation: {yaw, pitch, roll}}; h = 0.0 and yaw = pitch = roll = 0 are placeholders beside an explicit UNKNOWN sidecar, never measurements. These poses locate public map points for a game; the build writes them from geoplay/registry/geoplay.json and no learner position is ever written.',
                'not_in_geopose_json': 'These are kept in their own file so the 89 poses of geopose.json and their counts stay exactly as spatial/build.py counts them.'},
    'counts': {'poses': len(poses)}, 'poses': poses,
}
text = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
ptext = json.dumps(pose_doc, indent=1, ensure_ascii=False) + '\n'
if '--check' in sys.argv:
    for p, t in ((OUT, text), (POSE_OUT, ptext)):
        if not p.exists() or p.read_text(encoding='utf-8') != t:
            sys.exit(f'{p.relative_to(ROOT)} is stale: run python3 geoplay/build.py')
        print(f'{p.relative_to(ROOT)} is current')
else:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding='utf-8')
    POSE_OUT.write_text(ptext, encoding='utf-8')
    print(f'geoplay: {len(stops)} stops, {len(dids)} drops, {len(unpinned)} unpinned public places, '
          f'{len(refused)} refused, {len(poses)} GeoPose anchors')
