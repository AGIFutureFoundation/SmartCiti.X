#!/usr/bin/env python3
"""Simulated tasks: one list of every practice task the app can launch today.

Nothing here is new content. Each task is a JOIN over registries that already
exist, and every field is read from the registry that owns it:

  - sim-scenario     sims/registry/sims.json scenarios (SCRIPTED params). The
                     3D page picks a seat's scenario by the campus of the hall
                     it opens (web/build_3d.py startSim) unless ?scenario= names
                     one of the seat's own scenarios outright. The link opens the
                     first hall in sim.halls on that scenario's campus, or, when
                     no hall there teaches the seat, the seat's first hall, and
                     always names the scenario.
  - walkaround       sims/registry/sims.json walkaround points; they stand in
                     the seat's own yard, so the link opens the seat.
  - crib-drill       tools/registry/toolcribs.json hall_bindings; the crib is in
                     the hall's Tools room, so the link opens the hall.
  - crew-handoff     worksites/registry/worksites.json sites; the link opens the
                     site's own section of the worksites page.
  - restoration-walk restoration/registry/restoration.json sites the 3D campus
                     view offers a walk for (walkable, pinned, on a campus); the
                     link opens that campus.
  - wilds-site-walk  wilds/registry/wilds.json sites; the wilds page reads
                     #<world>/<site> from the hash and stands you at the site.

A link is only written when the target builder is seen reading that parameter;
otherwise the build fails by name. A task that exists in a registry but has no
link that reaches it carries href null and says why. `requires` lists only the
lessons a registry already links to that task; it is never a gate.

Tasks are practice. They certify nothing and enter no completion record.

  python3 tasks/build.py
"""
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'tasks.json'

SOURCES = (
    'sims/registry/sims.json',
    'tools/registry/toolcribs.json',
    'worksites/registry/worksites.json',
    'restoration/registry/restoration.json',
    'wilds/registry/wilds.json',
    'lessons/registry/lessons.json',
    'spaces/registry/spaces.json',
    'pack/registry/halls.json',
    'unions/registry/campuses.json',
)
# the builders whose URL handling a link depends on, and the exact source
# fragment that proves each parameter is read
PARAM_READS = {
    ('web/build_3d.py', 'hall'): "params.get('hall')",
    ('web/build_3d.py', 'sim'): "params.get('sim')",
    ('web/build_3d.py', 'campus'): "params.get('campus')",
    ('web/build_3d.py', 'scenario-by-campus'): "def.scenarios?.find((s) => s.campus === campusKey)",
    # ?scenario= is honoured only when it is one of THAT seat's own scenarios
    # (else ignored), and it wins over the campus pick inside startSim
    ('web/build_3d.py', 'scenario'): ("D.sims.sims[simDeep].scenarios.some((s) => s.id === params.get('scenario'))"),
    ('web/build_3d.py', 'scenario-wins'): "def.scenarios?.find((s) => s.id === scenarioId)\n    ?? def.scenarios?.find((s) => s.campus === campusKey)",
    ('web/build_3d.py', 'scenario-deep'): "startSim(simDeep, scenarioDeep);",
    ('web/build_wilds.py', '#world/site'): "const [wid, sid] = decodeURIComponent((location.hash || '').slice(1)).split('/');",
    # the hash's site part stands you AT the site (goSite teleports to its pad
    # and opens its card), and fromHash runs on boot, not only on hashchange
    ('web/build_wilds.py', '#world/site-goes'): "if (sid) goSite(sid);",
    ('web/build_wilds.py', '#world/site-boot'): "if (!(await fromHash())) await loadWorld(",
    ('web/build_wilds.py', '#world/site-find'): "const s = W.sites.find((x) => x.id === id);\n  if (s === undefined) throw new Error('wilds: no site ' + id + ' in ' + W.id);",
    ('web/build_worksites.py', '#site-'): 'id="site-{esc(s["id"])}"',
}
# restoration training scenarios (restoration/scenarios.py stages them in TASK_CONTRACT
# shape). They go live here only once web/taskkit.py's KIND_ORDER carries the kind
# - taskkit refuses an unknown kind, so writing them earlier would break every page
# that renders tasks. Until then tasks.json stays byte-identical and the build says so.
RESTO_SCEN = 'restoration/registry/scenarios.json'
RESTO_KIND = {'label': 'Restoration training scenario', 'provenance': 'DERIVED', 'lands': 'section'}
PAGE_3D = 'web/trade_craft_3d.html'
PAGE_WILDS = 'web/trade_craft_wilds.html'
PAGE_WORKSITES = 'web/trade_craft_worksites.html'

KINDS = {
    'sim-scenario': {'label': 'Simulator scenario', 'provenance': 'SCRIPTED', 'lands': 'seat'},
    'walkaround': {'label': 'Seat walkaround', 'provenance': 'DERIVED', 'lands': 'seat'},
    'crib-drill': {'label': 'Tool crib drill', 'provenance': 'DERIVED', 'lands': 'hall'},
    'crew-handoff': {'label': 'Crew hand-off', 'provenance': 'DERIVED', 'lands': 'section'},
    'restoration-walk': {'label': 'Restoration walk', 'provenance': 'DERIVED', 'lands': 'campus'},
    'wilds-site-walk': {'label': 'Wilds site walk', 'provenance': 'DERIVED', 'lands': 'site'},
}
HONESTY = {
    'practice': ('Tasks are practice. A task list certifies nothing, qualifies nobody and '
                 'enters no completion record; only the completion contract in completion/ '
                 'decides what a record says, and it is unchanged by this pack.'),
    'not_certification': ('Every seat, drill and walk named here keeps its own registry\'s '
                          'standing: schematic, unverified general practice, not equipment '
                          'certification and not an inspection record.'),
    'requires': ('Linked lessons are the lessons an existing registry already ties to a task. '
                 'They are a sensible order, never a lock: nothing is gated behind them.'),
    'launch': ('A launch link is written only when the target page is seen reading that '
               'parameter; "lands" says honestly where it puts you (a seat, a hall, a campus, '
               'a wilds site or a page section), and a task no link reaches says why.'),
}


def fail(msg):
    raise SystemExit(f'tasks/build: {msg}')


def need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise KeyError(f'tasks/build: {where} has no "{k}"')
    return d[k]


def load(rel):
    p = ROOT / rel
    if not p.exists():
        fail(f'missing source {rel}')
    return json.loads(p.read_text())


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def main():
    for (builder, param), frag in PARAM_READS.items():
        src = (ROOT / builder).read_text()
        if frag not in src:
            fail(f'{builder} no longer reads "{param}" (looked for {frag!r}); refusing to write a link')

    sims = load('sims/registry/sims.json')
    cribs = load('tools/registry/toolcribs.json')
    works = load('worksites/registry/worksites.json')
    resto = load('restoration/registry/restoration.json')
    wilds = load('wilds/registry/wilds.json')
    lessons = load('lessons/registry/lessons.json')
    spaces = load('spaces/registry/spaces.json')
    halls = load('pack/registry/halls.json')
    campuses = need(load('unions/registry/campuses.json'), 'campuses', 'unions/registry/campuses.json')

    hall_ids = {need(h, 'slug', 'pack/registry/halls.json#halls[]') for h in need(halls, 'halls', 'halls.json')}
    hall_name = {h['slug']: need(h, 'name', f'pack/registry/halls.json#halls.{h["slug"]}') for h in halls['halls']}
    campus_of = {}
    for ck, c in campuses.items():
        for h in need(c, 'halls', f'campuses.json#{ck}'):
            if h in campus_of:
                fail(f'hall {h} is on two campuses ({campus_of[h]}, {ck}); a task place needs one')
            campus_of[h] = ck
    space_ids = {need(s, 'id', 'spaces.json#spaces[]') for s in need(spaces, 'spaces', 'spaces.json')}
    resto_ids = {need(s, 'id', 'restoration.json#sites[]') for s in need(resto, 'sites', 'restoration.json')}
    L = need(lessons, 'lessons', 'lessons.json')

    def steps_of_kind(kind):
        for lid, les in L.items():
            for st in need(les, 'steps', f'lessons.json#lessons.{lid}'):
                if need(st, 'kind', f'lessons.json#lessons.{lid}.steps[]') == kind:
                    yield lid, les, st

    def lesson_ok(lid, where):
        if lid not in L:
            fail(f'{where} links lesson "{lid}", which is not in lessons/registry/lessons.json')
        return lid

    def hall_place(h, where):
        if h not in hall_ids:
            fail(f'{where}: hall "{h}" is not in pack/registry/halls.json')
        if h not in campus_of:
            fail(f'{where}: hall "{h}" stands on no campus in unions/registry/campuses.json')
        return {'kind': 'hall', 'id': h, 'campus': campus_of[h]}

    tasks = []

    # ---- sim scenarios (SCRIPTED) and seat walkarounds -----------------
    for sid, sim in need(sims, 'sims', 'sims.json').items():
        name = need(sim, 'name', f'sims.json#sims.{sid}')
        seat_halls = need(sim, 'halls', f'sims.json#sims.{sid}')
        for i, sc in enumerate(need(sim, 'scenarios', f'sims.json#sims.{sid}')):
            src = f'sims/registry/sims.json#sims.{sid}.scenarios[{i}]'
            sc_id = need(sc, 'id', src)
            sc_campus = need(sc, 'campus', src)
            here = [h for h in seat_halls if h in campus_of and campus_of[h] == sc_campus]
            req = sorted({lesson_ok(lid, src) for lid, _, st in steps_of_kind('sim')
                          if need(st, 'sim', lid) == sid and need(st, 'scenario', lid) == sc_id})
            # the 3D page takes ?scenario= only if it is one of this seat's own
            # scenarios; check that here too so a link it would ignore is never
            # written (a campus-picked fallback would be a different yard)
            own = [need(x, 'id', f'sims.json#sims.{sid}.scenarios[]') for x in need(sim, 'scenarios', src)]
            if own.count(sc_id) != 1:
                fail(f'{src}: scenario id "{sc_id}" is not exactly one of the {sid} seat\'s own scenarios')
            if here:
                # a hall on the scenario's own campus: the campus would pick it
                # anyway, and ?scenario= names it outright
                place = hall_place(here[0], src)
                launch = {'href': f'{PAGE_3D}?hall={here[0]}&sim={sid}&scenario={sc_id}', 'lands': 'seat',
                          'param': ['hall', 'sim', 'scenario']}
            else:
                # no hall on that campus teaches the seat: open the seat in its
                # first hall and name the scenario outright. The place stays the
                # scenario's campus (its params are that campus's); the seat
                # itself stands in a hall of another campus, said in `via`.
                if not seat_halls:
                    fail(f'{src}: seat {sid} lists no halls, so no link can open it')
                h0 = seat_halls[0]
                hall_place(h0, src)
                place = {'kind': 'campus', 'id': sc_campus, 'campus': sc_campus}
                launch = {'href': f'{PAGE_3D}?hall={h0}&sim={sid}&scenario={sc_id}', 'lands': 'seat',
                          'param': ['hall', 'sim', 'scenario'],
                          'via': {'hall': h0, 'campus': campus_of[h0], 'hall_name': hall_name[h0],
                                  'campus_name': need(campuses[campus_of[h0]], 'name',
                                                      f'unions/registry/campuses.json#{campus_of[h0]}')}}
            tasks.append({
                'id': f'sim-{sid}-{sc_id}', 'title': f'{name}: {need(sc, "name", src)}',
                'kind': 'sim-scenario', 'place': place, 'launch': launch, 'requires': req,
                'provenance': 'SCRIPTED', 'source': src, 'seat': sid,
                'brief': need(sc, 'brief', src),
            })
        src = f'sims/registry/sims.json#sims.{sid}.walkaround'
        points = need(sim, 'walkaround', f'sims.json#sims.{sid}')
        if not points:
            continue
        h0 = seat_halls[0]
        req = sorted({lesson_ok(lid, src) for lid, _, st in steps_of_kind('walkaround')
                      if need(st, 'sim', lid) == sid})
        tasks.append({
            'id': f'walkaround-{sid}', 'title': f'{name}: walkaround',
            'kind': 'walkaround', 'place': hall_place(h0, src),
            'launch': {'href': f'{PAGE_3D}?hall={h0}&sim={sid}', 'lands': 'seat', 'param': ['hall', 'sim']},
            'requires': req, 'provenance': 'DERIVED', 'source': src, 'seat': sid,
            'brief': f'{len(points)} points: ' + '; '.join(need(p, 'point', src) for p in points),
        })

    # ---- tool crib drills ---------------------------------------------------
    drill = need(cribs, 'drill', 'toolcribs.json')
    for h, b in need(cribs, 'hall_bindings', 'toolcribs.json').items():
        src = f'tools/registry/toolcribs.json#hall_bindings.{h}'
        dk = need(b, 'district', src)
        crib = need(need(cribs, 'cribs', 'toolcribs.json'), dk, src)
        picks = need(need(cribs, 'drills', 'toolcribs.json'), dk, src)
        req = sorted({lesson_ok(lid, src) for lid, les, st in steps_of_kind('crib')
                      if need(st, 'crib', lid) == dk and need(les, 'hall', lid) == h})
        tasks.append({
            'id': f'crib-{h}', 'title': f'{need(crib, "name", src)}: {need(drill, "name", "toolcribs.json#drill")}',
            'kind': 'crib-drill', 'place': hall_place(h, src),
            'launch': {'href': f'{PAGE_3D}?hall={h}', 'lands': 'hall', 'param': ['hall']},
            'requires': req, 'provenance': 'DERIVED', 'source': src, 'seat': None,
            'brief': f'{len(picks)} picks at the {need(crib, "name", src)} pegboard, in the hall\'s Tools room',
        })

    # ---- worksite crew hand-offs ------------------------------------------
    for i, s in enumerate(need(works, 'sites', 'worksites.json')):
        src = f'worksites/registry/worksites.json#sites[{i}]'
        pl = need(s, 'place', src)
        pk, pid, pc = need(pl, 'kind', src), need(pl, 'id', src), need(pl, 'campus', src)
        if pk == 'campus' and pid not in campuses:
            fail(f'{src}: campus "{pid}" is not in unions/registry/campuses.json')
        if pk == 'space' and pid not in space_ids:
            fail(f'{src}: space "{pid}" is not in spaces/registry/spaces.json')
        if pk == 'restoration-site' and pid not in resto_ids:
            fail(f'{src}: restoration site "{pid}" is not in restoration/registry/restoration.json')
        if pk not in ('campus', 'space', 'restoration-site'):
            fail(f'{src}: place kind "{pk}" has no owning registry here')
        der = need(s, 'derived', src)
        req = sorted(lesson_ok(lid, src) for lid in need(der, 'lessons_with_this_crew', src))
        crew = need(s, 'crew', src)
        tasks.append({
            'id': f'crew-{need(s, "id", src)}', 'title': need(s, 'title', src),
            'kind': 'crew-handoff', 'place': {'kind': pk, 'id': pid, 'campus': pc},
            'launch': {'href': f'{PAGE_WORKSITES}#site-{s["id"]}', 'lands': 'section', 'param': ['#site-']},
            'requires': req, 'provenance': 'DERIVED', 'source': src, 'seat': need(crew, 'seat', src),
            'brief': f'{need(crew, "name", src)}: {need(der, "roles", src)} roles, '
                     f'{need(der, "handoffs", src)} hand-offs',
        })

    # ---- restoration walks (the ones the 3D campus view offers) ------------
    for i, s in enumerate(need(resto, 'sites', 'restoration.json')):
        src = f'restoration/registry/restoration.json#sites[{i}]'
        if not (need(s, 'walkable', src) is True and need(s, 'pin', src) and need(s, 'campus', src)):
            continue
        ck = s['campus']
        if ck not in campuses:
            fail(f'{src}: campus "{ck}" is not in unions/registry/campuses.json')
        tasks.append({
            'id': f'resto-{need(s, "id", src)}', 'title': need(s, 'name', src),
            'kind': 'restoration-walk', 'place': {'kind': 'restoration-site', 'id': s['id'], 'campus': ck},
            'launch': {'href': f'{PAGE_3D}?campus={ck}', 'lands': 'campus', 'param': ['campus']},
            'requires': [], 'provenance': 'DERIVED', 'source': src, 'seat': None,
            'brief': f'{need(s, "habitat", src)}; walk it from the campus view',
        })

    # ---- wilds site walks ----------------------------------------------------
    for wi, w in enumerate(need(wilds, 'worlds', 'wilds.json')):
        wid = need(w, 'id', 'wilds.json#worlds[]')
        wc = need(need(w, 'inspiration', f'wilds.json#worlds[{wi}]'), 'campus', f'wilds.json#worlds[{wi}].inspiration')
        if wc not in campuses:
            fail(f'wilds.json#worlds[{wi}]: campus "{wc}" is not in unions/registry/campuses.json')
        for si, s in enumerate(need(w, 'sites', f'wilds.json#worlds[{wi}]')):
            src = f'wilds/registry/wilds.json#worlds[{wi}].sites[{si}]'
            req = sorted({lesson_ok(need(l, 'id', src), src) for l in need(s, 'lessons', src)})
            tasks.append({
                'id': f'wilds-{need(s, "id", src)}', 'title': need(s, 'title', src),
                'kind': 'wilds-site-walk',
                'place': {'kind': 'wilds-site', 'id': s['id'], 'world': wid, 'campus': wc},
                'launch': {'href': f'{PAGE_WILDS}#{wid}/{s["id"]}', 'lands': 'site', 'param': ['#world/site']},
                'requires': req, 'provenance': 'DERIVED', 'source': src, 'seat': None,
                'brief': f'{need(w, "name", src)}: {need(s, "work", src)}',
            })

    # ---- restoration training scenarios (staged by restoration/scenarios.py) --
    sources = list(SOURCES)
    order_m = re.search(r'KIND_ORDER = \(([^)]*)\)', (ROOT / 'web/taskkit.py').read_text())
    if order_m is None:
        fail('web/taskkit.py has no KIND_ORDER tuple; cannot tell whether resto-scenario is accepted')
    staged = need(load(RESTO_SCEN), 'staged_tasks', RESTO_SCEN)
    if "'resto-scenario'" in order_m.group(1):
        KINDS['resto-scenario'] = RESTO_KIND
        sources.append(RESTO_SCEN)
        for i, t in enumerate(staged):
            src = f'{RESTO_SCEN}#staged_tasks[{i}]'
            pl = need(t, 'place', src)
            if need(t, 'kind', src) != 'resto-scenario' or need(pl, 'kind', src) != 'restoration-site':
                fail(f'{src}: not a resto-scenario task on a restoration-site')
            if need(pl, 'id', src) not in resto_ids:
                fail(f'{src}: restoration site "{pl["id"]}" is not in restoration/registry/restoration.json')
            if need(pl, 'campus', src) not in campuses:
                fail(f'{src}: campus "{pl["campus"]}" is not in unions/registry/campuses.json')
            tasks.append(t)
        print(f'tasks/build: resto-scenario live - {len(staged)} restoration training scenarios added')
    else:
        print(f'tasks/build: resto-scenario NOT live - {len(staged)} staged in {RESTO_SCEN}; '
              'web/taskkit.py KIND_ORDER lacks the kind (NEEDS taskkit owner)')

    ids = [t['id'] for t in tasks]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        fail(f'duplicate task ids {dup}')
    for t in tasks:
        if not re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*', t['id']):
            fail(f'task id "{t["id"]}" is not kebab-case')
        if t['kind'] not in KINDS or KINDS[t['kind']]['provenance'] != t['provenance']:
            fail(f'task {t["id"]}: kind/provenance mismatch')

    def tally(key):
        out = {}
        for t in tasks:
            k = key(t)
            k = 'none' if k is None else k
            out[k] = out[k] + 1 if k in out else 1
        return dict(sorted(out.items()))

    launchable = sum(1 for t in tasks if t['launch']['href'])
    counts = {
        'tasks': len(tasks),
        'by_kind': tally(lambda t: t['kind']),
        'by_place_kind': tally(lambda t: t['place']['kind']),
        'by_campus': tally(lambda t: t['place']['campus']),
        'launchable': launchable,
        'not_launchable': len(tasks) - launchable,
        'with_linked_lessons': sum(1 for t in tasks if t['requires']),
    }
    builder = pathlib.Path(__file__).read_bytes()
    srcs = {rel: sha16((ROOT / rel).read_bytes()) for rel in sources}
    stamp = sha16(builder + b''.join((ROOT / rel).read_bytes() for rel in sources))
    reg = {
        'pack': 'smartcitix-trade-craft-academy-tasks',
        'product': need(sims, 'product', 'sims.json'),
        'built': need(sims, 'built', 'sims.json'),
        'source_stamp': stamp,
        'builder_stamp': sha16(builder),
        'sources': srcs,
        'honesty': HONESTY,
        'kinds': KINDS,
        'counts': counts,
        'tasks': tasks,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + '\n')
    print(f'tasks/build: {len(tasks)} tasks ({launchable} launchable) -> '
          f'{OUT.relative_to(ROOT)}  stamp {stamp}')
    print('  by kind: ' + ', '.join(f'{k} {v}' for k, v in counts['by_kind'].items()))
    print('  by campus: ' + ', '.join(f'{k} {v}' for k, v in counts['by_campus'].items()))


if __name__ == '__main__':
    try:
        main()
    except KeyError as e:
        raise SystemExit(str(e).strip('"\''))
