#!/usr/bin/env python3
"""unionpaths/build.py - one ordered path through each of the 111 union halls (wave 18, PATHWAYS).

Every hall in unions/registry/unions.json gets one path, in this fixed order:

  1. its trade course            courses/registry/courses.json#courses["trade.<slug>"]
  2. its lessons, ladder order    that course's `outline` (ladder depth, then the lessons registry order - the course rule)
  3. its simulator seats          that course's seat_time.seats_bound, in registry order
  4. its tool crib                tools/registry/toolcribs.json#hall_bindings[<slug>].district
  5. its Omega Hive advisor       the first advisor its lessons send a learner to (each lesson supplement's
                                  where.advisors, in ladder order); a hall whose lessons name none gets the Orientation
                                  guide, the one advisor that stands at every hall's door (agents/registry/advisors.json
                                  guide.stands_in "door"; web/build_3d.py places "the guide at the door")
  6. its crews                    every crew in agents/registry/crews.json whose `halls` names the hall, in registry
                                  order, each with the hive ids of its roles (hive/registry/hive.json)

Plus per-district (unions/registry/districts.json order) and per-cohort (unions.json#cohorts order) rollups.

Everything is DERIVED by the rules above from registries; every name is READ. Nothing is fetched and no model runs.
No apprenticeship hours, wages, credentials, membership or affiliation are stated: the build refuses (fails closed)
any derived record that carries such a word, and a hall missing from any source stops the build with a named error.
`--check` rebuilds in memory and exits 1 if the file on disk differs.
"""
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'union_paths.json'
BUILT = '2026-10-12'
SCHEMA = 'tc-union-paths/1'

SOURCES = ['unions/registry/unions.json', 'unions/registry/districts.json', 'unions/registry/chapters.json',
           'unions/registry/campuses.json', 'courses/registry/courses.json', 'tools/registry/toolcribs.json',
           'agents/registry/advisors.json', 'agents/registry/crews.json', 'hive/registry/hive.json']


class PathError(Exception):
    pass


def need(cond, msg):
    if not cond:
        raise PathError('unionpaths: ' + msg)


def req(d, k, ctx):
    if not isinstance(d, dict) or k not in d:
        raise PathError(f'unionpaths: {ctx}: missing {k!r}')
    return d[k]


def load(p):
    f = ROOT / p
    need(f.exists(), f'{p} is missing')
    return json.loads(f.read_text(encoding='utf-8'))


UREG = load('unions/registry/unions.json')
UNIONS = req(UREG, 'unions', 'unions.json')
COHORTS = req(UREG, 'cohorts', 'unions.json')
DISTRICTS = req(load('unions/registry/districts.json'), 'districts', 'districts.json')
CHAPTERS = load('unions/registry/chapters.json')
CAMPUSES = load('unions/registry/campuses.json')
CREG = load('courses/registry/courses.json')
COURSES = req(CREG, 'courses', 'courses.json')
SUPS = req(CREG, 'supplements', 'courses.json')
CRIBS = load('tools/registry/toolcribs.json')
CRIB_OF = req(CRIBS, 'cribs', 'toolcribs.json')
CRIB_BIND = req(CRIBS, 'hall_bindings', 'toolcribs.json')
ADVISORS = req(load('agents/registry/advisors.json'), 'advisors', 'advisors.json')
CREWS = req(load('agents/registry/crews.json'), 'crews', 'crews.json')
HIVE = load('hive/registry/hive.json')
AGENTS = {a['id']: a for a in req(HIVE, 'agents', 'hive.json')}

DOOR_ADVISOR = 'guide'
need(req(req(ADVISORS, DOOR_ADVISOR, 'advisors.json#advisors'), 'stands_in', 'advisors.json#advisors.guide') == 'door',
     'the door advisor no longer stands at the door (advisors.json#advisors.guide.stands_in)')

RULES = {
    'order': 'course, then its lessons, then its seats, then its tool crib, then its advisor, then its crews - one path per hall',
    'course': 'courses/registry/courses.json#courses["trade.<hall slug>"]; the course must name the hall and agree with the '
              'union registry on name, focus and district',
    'lessons': "the trade course's outline, which the course rule orders by ladder depth, then the lessons registry order",
    'seats': "the trade course's seat_time.seats_bound, in registry order (every seat a lesson uses is among them)",
    'crib': 'tools/registry/toolcribs.json#hall_bindings[<hall>].district names the crib; it must be the hall\'s own district',
    'advisor': "the first advisor named by the hall's lesson supplements (where.advisors), in ladder order; a hall whose "
               'lessons name none gets the Orientation guide, the advisor that stands at every hall\'s door',
    'crews': 'every crew in agents/registry/crews.json whose halls list names the hall, in registry order, with its roles '
             'as hive/registry/hive.json ids; a crew\'s seat must be one of the hall\'s bound seats',
    'district_rollup': 'unions/registry/districts.json order; halls in union registry order; seats, crews and advisors '
                       'counted once each, in order of first appearance',
    'cohort_rollup': "unions.json#cohorts order; the hall count must equal the cohort's own count",
}

# The registry's own honesty lines, quoted verbatim with their source paths, then this pack's own (AUTHORED).
QUOTED = []
for path, doc in (('unions/registry/unions.json', UREG), ('unions/registry/chapters.json', CHAPTERS),
                  ('unions/registry/campuses.json', CAMPUSES)):
    for k, v in req(doc, 'honesty', path).items():
        need(isinstance(v, str) and v.strip(), f'{path}#honesty.{k} is empty')
        QUOTED.append({'source': f'{path}#honesty.{k}', 'text': v})
for k in ('content', 'not_certification'):
    QUOTED.append({'source': f'courses/registry/courses.json#honesty.{k}', 'text': req(req(CREG, 'honesty', 'courses.json'), k, 'courses.json#honesty')})

HONESTY = {
    'status': 'DERIVED: each path is an order chosen by the rules printed under `rules`, over ids READ from the '
              'registries listed under `sources`. Nothing is fetched and no model runs.',
    'not_partner': 'A union named here is a hall in the Academy\'s own taxonomy of trades. It is not a partner, sponsor or '
                   'affiliate, it has not reviewed or endorsed any of this, and no real local is named.',
    'nothing_invented': 'No apprenticeship hours, wages, credentials, membership or affiliation are stated or implied for '
                        'any hall; the build refuses a derived record that carries one.',
    'programmes': 'Any tie to a real apprenticeship programme is PROPOSED: no agreement exists with any union, '
                  'programme or employer.',
    'voice': 'An advisor or crew role is SCRIPTED: no AI model, the device\'s own speech synthesis, only on a click, '
             'with AUTHORED personalities (hive/registry/hive.json).',
}

# words a derived record may never carry (the honesty block above is where they are named, and only to deny them)
FORBIDDEN = re.compile(r'\b(hours?|wages?|salar(y|ies)|pay rate|per hour|credential(s|ed)?|certif\w*|membership|'
                       r'affiliat\w*|apprenticeship|journeyman|journeyworker|union dues|local \d+)\b|\$\s?\d', re.I)


def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield k.replace('_', ' ').replace('-', ' ')   # a key like apprenticeship_hours is read as words
            yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)


district_names = {d: req(v, 'name', f'districts.json#{d}') for d, v in DISTRICTS.items()}
halls, seen = [], set()
for i, u in enumerate(UNIONS):
    for k in ('index', 'slug', 'name', 'focus', 'district', 'cohort'):
        req(u, k, f'unions.json#unions[{i}]')
    slug = u['slug']
    need(u['index'] == i, f'{slug}: index {u["index"]} is not its registry position {i}')
    need(slug not in seen, f'{slug}: listed twice')
    seen.add(slug)
    need(u['district'] in DISTRICTS, f'{slug}: district {u["district"]!r} is not in districts.json')
    need(slug in req(DISTRICTS[u['district']], 'halls', f'districts.json#{u["district"]}'),
         f'{slug}: districts.json#{u["district"]}.halls does not list it')
    need(u['cohort'] in COHORTS, f'{slug}: cohort {u["cohort"]!r} is not in unions.json#cohorts')

    cid = 'trade.' + slug
    c = req(COURSES, cid, 'courses.json#courses')
    need(c.get('kind') == 'trade' and c.get('hall') == slug, f'{cid}: not the trade course of hall {slug}')
    for a, b in (('title', 'name'), ('focus', 'focus'), ('district', 'district')):
        need(req(c, a, cid) == u[b], f'{cid}: {a} {c[a]!r} disagrees with unions.json {b} {u[b]!r}')
    outline = req(c, 'outline', cid)
    need(outline, f'{cid}: the course lists no lesson')
    need([r['lesson'] for r in outline] == req(c, 'lessons', cid), f'{cid}: outline and lessons disagree')
    lessons = []
    for r in outline:
        lid = req(r, 'lesson', cid)
        s = req(SUPS, lid, 'courses.json#supplements')
        need(req(r, 'hall', lid) == slug, f'{lid}: stands in {r["hall"]}, not in {slug}')
        lessons.append({'lesson': lid, 'title': req(r, 'title', lid), 'strand': req(r, 'strand', lid),
                        'room_label': req(r, 'room_label', lid), 'tier': req(r, 'tier', lid),
                        'depth': req(r, 'depth', lid), 'steps': req(r, 'steps', lid),
                        'advisors': [req(a, 'id', lid) for a in req(req(s, 'where', lid), 'advisors', lid)]})
    depths = [L['depth'] for L in lessons]
    need(depths == sorted(depths), f'{cid}: the outline is not in ladder order')

    st = req(c, 'seat_time', cid)
    seats_bound = req(st, 'seats_bound', cid)
    names = req(st, 'seat_names', cid)
    need(set(req(st, 'seats_in_lessons', cid)) <= set(seats_bound), f'{cid}: a lesson uses a seat the hall has not bound')
    seats = [{'sim': sid, 'name': req(names, sid, f'{cid}.seat_names')} for sid in seats_bound]

    bind = req(CRIB_BIND, slug, 'toolcribs.json#hall_bindings')
    crib_id = req(bind, 'district', f'toolcribs.json#hall_bindings.{slug}')
    need(crib_id == u['district'], f'{slug}: crib {crib_id!r} is not its district {u["district"]!r}')
    crib = {'crib': crib_id, 'name': req(req(CRIB_OF, crib_id, 'toolcribs.json#cribs'), 'name', crib_id),
            'skill_id': req(bind, 'skill_id', f'toolcribs.json#hall_bindings.{slug}')}

    named = []
    for L in lessons:
        for a in L['advisors']:
            if a not in named:
                named.append(a)
    adv_key, adv_rule = (named[0], 'lessons') if named else (DOOR_ADVISOR, 'door')
    adv_id = 'advisor:' + adv_key
    need(adv_id in AGENTS and AGENTS[adv_id]['kind'] == 'advisor', f'{slug}: advisor {adv_id} is not in hive.json')
    also = ['advisor:' + a for a in named[1:]]
    for a in also:
        need(a in AGENTS, f'{slug}: advisor {a} is not in hive.json')

    crews = []
    for ck, cv in CREWS.items():
        if slug not in req(cv, 'halls', f'crews.json#{ck}'):
            continue
        need(req(cv, 'seat', ck) in seats_bound, f'{slug}: crew {ck} runs seat {cv["seat"]!r}, which the hall has not bound')
        roles = [f'crew:{ck}:{r}' for r in req(cv, 'roles', ck)]
        for r in roles:
            need(r in AGENTS and AGENTS[r]['kind'] == 'crew-role', f'{slug}: crew role {r} is not in hive.json')
        crews.append({'crew': ck, 'name': req(cv, 'name', ck), 'seat': cv['seat'], 'roles': roles})

    path = [{'kind': 'course', 'ref': cid}]
    path += [{'kind': 'lesson', 'ref': L['lesson']} for L in lessons]
    path += [{'kind': 'seat', 'ref': s['sim']} for s in seats]
    path += [{'kind': 'crib', 'ref': crib_id}]
    path += [{'kind': 'advisor', 'ref': adv_id}]
    path += [{'kind': 'crew', 'ref': cr['crew']} for cr in crews]
    for n, p in enumerate(path, 1):
        p['step'] = n

    lesson_ids = [L['lesson'] for L in lessons]
    halls.append({
        'hall': slug, 'index': i, 'name': u['name'], 'focus': u['focus'], 'district': u['district'],
        'district_name': district_names[u['district']], 'cohort': u['cohort'],
        'campus': req(c, 'campus', cid), 'campus_name': req(c, 'campus_name', cid),
        'course': cid, 'lessons': [{k: L[k] for k in ('lesson', 'title', 'strand', 'room_label', 'tier', 'depth', 'steps')}
                                   for L in lessons],
        'seats': seats, 'crib': crib,
        'advisor': {'id': adv_id, 'name': AGENTS[adv_id]['name'], 'rule': adv_rule, 'also': also},
        'crews': crews, 'path': path,
        'counts': {'lessons': len(lessons), 'steps': sum(L['steps'] for L in lessons), 'seats': len(seats),
                   'crews': len(crews), 'crew_roles': sum(len(cr['roles']) for cr in crews), 'path_steps': len(path)},
        'links': {'hall3d': f'web/trade_craft_3d.html?hall={slug}',
                  'course': f'web/trade_craft_courses.html?course={cid}#course-trade',
                  'supplements': [f'web/trade_craft_courses.html?lesson={lid}#course-sup' for lid in lesson_ids],
                  'advisor': f'web/trade_craft_hive.html?agent={adv_id}',
                  'ladder': f'web/trade_craft_ladder.html?hall={slug}'},
        'provenance': {'path': 'DERIVED', 'order': 'DERIVED', 'names': 'READ', 'lessons': 'AUTHORED', 'agents': 'SCRIPTED'},
    })

need(len(halls) == len(UNIONS) == req(UREG, 'count', 'unions.json'), 'the hall count disagrees with unions.json#count')
need(sorted(h['course'] for h in halls) == sorted(k for k, v in COURSES.items() if v.get('kind') == 'trade'),
     'a trade course has no union hall, or a hall has no trade course')


def firsts(seq):
    out = []
    for x in seq:
        if x not in out:
            out.append(x)
    return out


def rollup(hs):
    prim = {}
    for h in hs:
        prim[h['advisor']['id']] = prim.get(h['advisor']['id'], 0) + 1
    return {
        'halls': [h['hall'] for h in hs], 'count': len(hs),
        'lessons': sum(h['counts']['lessons'] for h in hs), 'steps': sum(h['counts']['steps'] for h in hs),
        'halls_with_seats': sum(1 for h in hs if h['seats']), 'halls_with_crews': sum(1 for h in hs if h['crews']),
        'halls_door_advisor': sum(1 for h in hs if h['advisor']['rule'] == 'door'),
        'seats': firsts(s['sim'] for h in hs for s in h['seats']),
        'crews': firsts(c['crew'] for h in hs for c in h['crews']),
        'advisors': firsts(h['advisor']['id'] for h in hs), 'advisor_halls': prim,
    }


by_district = []
for d, dv in DISTRICTS.items():
    hs = [h for h in halls if h['district'] == d]
    need(hs, f'district {d} has no hall')
    need(sorted(h['hall'] for h in hs) == sorted(dv['halls']), f'district {d}: the halls disagree with districts.json')
    r = {'district': d, 'name': dv['name'], 'tagline': req(dv, 'tagline', f'districts.json#{d}'), 'crib': d}
    r.update(rollup(hs))
    r['cohorts'] = {k: sum(1 for h in hs if h['cohort'] == k) for k in COHORTS}
    by_district.append(r)

by_cohort = []
for k, n in COHORTS.items():
    hs = [h for h in halls if h['cohort'] == k]
    need(len(hs) == n, f'cohort {k}: {len(hs)} halls, but unions.json#cohorts says {n}')
    r = {'cohort': k}
    r.update(rollup(hs))
    r['districts'] = {d: sum(1 for h in hs if h['district'] == d) for d in DISTRICTS}
    by_cohort.append(r)

for h in halls + by_district + by_cohort:
    for s in strings(h):
        m = FORBIDDEN.search(s)
        if m:
            raise PathError(f'unionpaths: {h.get("hall") or h.get("district") or h.get("cohort")}: a derived record '
                            f'carries {m.group(0)!r} (no hours, wages, credentials, membership or affiliation may be stated)')

counts = {
    'halls': len(halls), 'districts': len(by_district), 'cohorts': len(by_cohort),
    'courses': len({h['course'] for h in halls}), 'lessons': sum(h['counts']['lessons'] for h in halls),
    'steps': sum(h['counts']['steps'] for h in halls), 'path_steps': sum(len(h['path']) for h in halls),
    'halls_with_seats': sum(1 for h in halls if h['seats']), 'seat_bindings': sum(len(h['seats']) for h in halls),
    'halls_with_crews': sum(1 for h in halls if h['crews']), 'crew_bindings': sum(len(h['crews']) for h in halls),
    'halls_lesson_advisor': sum(1 for h in halls if h['advisor']['rule'] == 'lessons'),
    'halls_door_advisor': sum(1 for h in halls if h['advisor']['rule'] == 'door'),
    'advisors_used': len({h['advisor']['id'] for h in halls}), 'cribs_used': len({h['crib']['crib'] for h in halls}),
    'hours': None, 'wages': None, 'credentials': None, 'affiliations': 0,
}
counts_why = 'hours, wages and credentials are null and affiliations 0 because no registry records any; none is invented'

stamp = hashlib.sha256((HERE / 'build.py').read_bytes()).hexdigest()[:16]
doc = {
    'pack': 'smartcitix-union-paths', 'schema': SCHEMA, 'built': BUILT, 'source_stamp': stamp,
    'sources': [{'path': p, 'sha256': hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:16]} for p in SOURCES],
    'honesty': HONESTY, 'honesty_quoted': QUOTED, 'rules': RULES, 'counts': counts, 'counts_why': counts_why,
    'cohorts': list(COHORTS), 'districts': list(DISTRICTS),
    'halls': halls, 'by_district': by_district, 'by_cohort': by_cohort,
}
text = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
if '--check' in sys.argv:
    if not OUT.exists() or OUT.read_text(encoding='utf-8') != text:
        print('unionpaths: registry/union_paths.json is stale - run python3 unionpaths/build.py')
        sys.exit(1)
    print(f'unionpaths: union_paths.json is current ({counts["halls"]} halls, stamp {stamp})')
    sys.exit(0)
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(text, encoding='utf-8')
print(f"unionpaths: {counts['halls']} hall paths ({counts['path_steps']} steps) over {counts['lessons']} lessons; "
      f"{counts['halls_with_seats']} halls with seats, {counts['halls_with_crews']} with crews, "
      f"{counts['halls_lesson_advisor']} lesson advisors + {counts['halls_door_advisor']} door guides; "
      f"{counts['districts']} district and {counts['cohorts']} cohort rollups (stamp {stamp})")
