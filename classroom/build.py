#!/usr/bin/env python3
"""classroom/ - K-12 curriculum modules mapped onto the open worlds, plus AUTHORED play rules.

Writes classroom/registry/classroom.json from registries already in this repo, nothing typed:
  schools/registry/schools.json   Cognition.X K-12 units (one module per unit), bands, teacher model
  lessons/registry/lessons.json   lessons of each unit's hall (quoted verbatim, "unverified general practice")
  layers/registry/layers.json     parish world stations (k12-unit / lesson / trade-sim layers)
  layers/registry/paths.json      the k12 and teachers path steps per parish
  wilds/registry/wilds.json       wilds work sites that name the hall or the lesson
  sims/registry/sims.json         3D campus seats bound to the unit's hall

Every place id resolves to a real registry id or the build stops with a named error (no defaults).
XP, streaks, badges and sessions are AUTHORED play rules: they are local to a learner's browser and
never enter a completion record. K-12 districts stay PROPOSED partners. `--check` fails if stale.
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'classroom/registry/classroom.json'
SRC = {
    'schools': 'schools/registry/schools.json',
    'lessons': 'lessons/registry/lessons.json',
    'layers': 'layers/registry/layers.json',
    'paths': 'layers/registry/paths.json',
    'wilds': 'wilds/registry/wilds.json',
    'sims': 'sims/registry/sims.json',
    'cognitionx': 'cognitionx/registry/cognitionx.json',
}
WORLD_PAGES = {
    'parishes': 'web/trade_craft_parishes.html',
    'wilds': 'web/trade_craft_wilds.html',
    'campus': 'web/trade_craft_3d.html',
}


class ClassroomError(Exception):
    pass


def need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise ClassroomError(f'classroom: {where} has no {k!r}')
    return d[k]


RAW = {}
REG = {}
for k, p in SRC.items():
    f = ROOT / p
    if not f.is_file():
        raise ClassroomError(f'classroom: source registry {p} is missing')
    RAW[k] = f.read_bytes()
    REG[k] = json.loads(RAW[k])
for w, p in WORLD_PAGES.items():
    if not (ROOT / p).is_file():
        raise ClassroomError(f'classroom: world page {p} ({w}) is missing')

S, LS, LY, PA, WI, SI, CX = (REG[k] for k in ('schools', 'lessons', 'layers', 'paths', 'wilds', 'sims', 'cognitionx'))
LESSONS = need(LS, 'lessons', SRC['lessons'])
LHON = need(LS, 'honesty', SRC['lessons'])
if 'unverified general practice' not in need(LHON, 'content', 'lessons honesty'):
    raise ClassroomError('classroom: lessons pack no longer says "unverified general practice"')
SHON = need(S, 'honesty', SRC['schools'])
if 'PROPOSED' not in need(SHON, 'districts', 'schools honesty'):
    raise ClassroomError('classroom: schools districts honesty no longer says PROPOSED')
SIMS = need(SI, 'sims', SRC['sims'])
BIND = need(SI, 'hall_bindings', SRC['sims'])

places = {}


def add_place(pid, world, kind, ref, source, title, href):
    if pid in places:
        return pid
    if world not in WORLD_PAGES:
        raise ClassroomError(f'classroom: place {pid} names unknown world {world!r}')
    places[pid] = {'id': pid, 'world': world, 'kind': kind, 'ref': ref, 'source': source, 'title': title,
                   'href': href}
    return pid


# ---- parish stations and k12 path steps ----
station_ix = {}
for p in need(LY, 'parishes', SRC['layers']):
    for st in need(p, 'stations', 'layers parish'):
        station_ix[need(st, 'id', 'station')] = (need(p, 'fips', 'layers parish'), need(p, 'name', 'layers parish'), st)
by_hall_st, by_lesson_st, by_sim_st = {}, {}, {}
for sid, (fips, pname, st) in station_ix.items():
    ref = need(st, 'ref', sid)
    layer = need(st, 'layer', sid)
    if layer == 'k12-unit':
        by_hall_st.setdefault(need(ref, 'id', sid), []).append(sid)
    elif layer == 'lesson':
        by_lesson_st.setdefault(need(ref, 'id', sid), []).append(sid)
    elif layer == 'trade-sim':
        by_sim_st.setdefault(need(ref, 'id', sid), []).append(sid)


def station_place(sid):
    if sid not in station_ix:
        raise ClassroomError(f'classroom: station {sid} does not resolve in {SRC["layers"]}')
    fips, pname, st = station_ix[sid]
    return add_place(f'parish:{fips}/{sid}', 'parishes', 'station', {'fips': fips, 'station': sid},
                     f'{SRC["layers"]}#parishes[fips={fips}].stations[id={sid}]',
                     f'{pname}: {need(st, "title", sid)}', WORLD_PAGES['parishes'])


k12_steps = {}   # station id -> [k12 step place ids]
for p in need(PA, 'parishes', SRC['paths']):
    fips = need(p, 'fips', 'paths parish')
    for path in need(p, 'paths', 'paths parish'):
        if need(path, 'id', 'path') != 'k12':
            continue
        for n, step in enumerate(need(path, 'steps', 'k12 path'), 1):
            if need(step, 'kind', 'k12 step') != 'station':
                raise ClassroomError(f'classroom: k12 step {fips}#{n} is not a station step')
            sid = need(step, 'id', 'k12 step')
            if sid not in station_ix:
                raise ClassroomError(f'classroom: k12 step {fips}#{n} names unknown station {sid}')
            pid = add_place(f'k12:{fips}/{n}', 'parishes', 'path-step', {'fips': fips, 'path': 'k12', 'n': n, 'station': sid},
                            f'{SRC["paths"]}#parishes[fips={fips}].paths[id=k12].steps[{n - 1}]',
                            need(step, 'title', 'k12 step'), WORLD_PAGES['parishes'])
            k12_steps.setdefault(sid, []).append(pid)

# ---- wilds sites ----
wilds_by_hall, wilds_by_lesson = {}, {}
for w in need(WI, 'worlds', SRC['wilds']):
    wid = need(w, 'id', 'wilds world')
    for i, site in enumerate(need(w, 'sites', f'wilds {wid}')):
        sid = need(site, 'id', f'wilds {wid} site')
        pid = f'wilds:{wid}/{sid}'
        entry = (pid, wid, sid, i, need(site, 'title', pid))
        for h in need(site, 'halls', pid):
            wilds_by_hall.setdefault(need(h, 'id', pid), []).append(entry)
        for le in need(site, 'lessons', pid):
            wilds_by_lesson.setdefault(need(le, 'id', pid), []).append(entry)


def wild_place(entry):
    pid, wid, sid, i, title = entry
    return add_place(pid, 'wilds', 'site', {'world': wid, 'site': sid},
                     f'{SRC["wilds"]}#worlds[id={wid}].sites[{i}]', title, WORLD_PAGES['wilds'])


# ---- modules: one per Cognition.X unit ----
hall_names = {}
for lid, le in LESSONS.items():
    hall_names[need(le, 'hall', lid)] = need(le, 'hall_name', lid)
lesson_by_hall = {}
for lid in sorted(LESSONS):
    lesson_by_hall.setdefault(LESSONS[lid]['hall'], []).append(lid)
ALL_WHY = [(lid, need(LESSONS[lid], 'why', lid)) for lid in sorted(LESSONS)]

modules, moments = [], []
for ui, u in enumerate(need(S, 'units', SRC['schools'])):
    hall = need(u, 'hall', f'units[{ui}]')
    if hall not in hall_names:
        raise ClassroomError(f'classroom: unit hall {hall} has no lesson in {SRC["lessons"]}')
    lids = lesson_by_hall[hall]
    mplaces = []
    for sid in by_hall_st.get(hall, []):
        mplaces.append(station_place(sid))
        mplaces += k12_steps.get(sid, [])
    for e in wilds_by_hall.get(hall, []):
        mplaces.append(wild_place(e))
    mplaces.append(add_place(f'campus:{hall}', 'campus', 'hall', {'hall': hall}, f'{SRC["lessons"]}#lessons[hall={hall}]',
                             hall_names[hall], f'{WORLD_PAGES["campus"]}?hall={hall}'))
    bound = [need(b, 'sim', f'hall_bindings.{hall}') for b in BIND[hall]] if hall in BIND else []
    for sim in need(u, 'floor_sims', f'units[{ui}]'):
        if sim not in SIMS:
            raise ClassroomError(f'classroom: unit {hall} floor sim {sim} is not in {SRC["sims"]}')
        if sim not in bound:
            raise ClassroomError(f'classroom: unit {hall} floor sim {sim} is not bound to hall {hall}')
        mplaces.append(add_place(f'campus:{hall}/{sim}', 'campus', 'seat', {'hall': hall, 'sim': sim},
                                 f'{SRC["sims"]}#hall_bindings.{hall}[sim={sim}]',
                                 f'{hall_names[hall]}: {need(SIMS[sim], "name", sim)}',
                                 f'{WORLD_PAGES["campus"]}?hall={hall}&sim={sim}'))
    mo_ids = []
    for lid in lids:
        le = LESSONS[lid]
        lp = []
        for sid in by_lesson_st.get(lid, []):
            lp.append(station_place(sid))
            lp += k12_steps.get(sid, [])
        for e in wilds_by_lesson.get(lid, []):
            lp.append(wild_place(e))
        why = need(le, 'why', lid)
        # distractors: the next two lessons (sorted id order, wrapping) - verbatim, deterministic
        ix = [i for i, (x, _) in enumerate(ALL_WHY) if x == lid][0]
        others = [ALL_WHY[(ix + k) % len(ALL_WHY)] for k in (7, 29)]
        choices = [{'lesson': lid, 'text': why}] + [{'lesson': o, 'text': t} for o, t in others]
        choices.sort(key=lambda c: hashlib.sha256((lid + c['lesson']).encode()).hexdigest())
        mo = {'id': f'mo-{lid}', 'module': f'mod-{hall}', 'lesson': lid, 'kind': 'choice',
              'title': need(le, 'title', lid), 'title_source': f'{SRC["lessons"]}#lessons.{lid}.title',
              'answer': lid, 'choices': choices, 'answer_source': f'{SRC["lessons"]}#lessons.{lid}.why',
              'limits': need(le, 'limits', lid), 'limits_source': f'{SRC["lessons"]}#lessons.{lid}.limits',
              'first_do': need(need(le, 'steps', lid)[0], 'do', lid),
              'first_do_source': f'{SRC["lessons"]}#lessons.{lid}.steps[0].do',
              'places': sorted(set(lp + mplaces)), 'status': 'unverified general practice'}
        moments.append(mo)
        mo_ids.append(mo['id'])
    modules.append({
        'id': f'mod-{hall}', 'hall': hall, 'hall_name': hall_names[hall],
        'unit': {k: need(u, k, f'units[{ui}]') for k in ('home', 'class_drill', 'floor_sims', 'gate')},
        'unit_source': f'{SRC["schools"]}#units[{ui}]',
        'lessons': lids, 'moments': mo_ids, 'places': sorted(set(mplaces)),
        'worlds': sorted(set(places[p]['world'] for p in mplaces)),
    })

for m in modules:
    if not m['lessons'] or not m['places']:
        raise ClassroomError(f'classroom: module {m["id"]} has no lessons or no places')

model = need(S, 'model', SRC['schools'])
teacher_model = {
    'name': need(model, 'name', 'model'), 'name_source': f'{SRC["schools"]}#model.name',
    'loop': need(model, 'loop', 'model'), 'loop_source': f'{SRC["schools"]}#model.loop',
    'stages': [{'stage': need(st, 'stage', 'stage'), 'title': need(st, 'title', 'stage'), 'what': need(st, 'what', 'stage'),
                'source': f'{SRC["schools"]}#model.stages[{i}]'} for i, st in enumerate(need(model, 'stages', 'model'))],
}
bands = [{'band': need(b, 'band', 'band'), 'level': need(b, 'level', 'band'), 'offer': need(b, 'offer', 'band'),
          'source': f'{SRC["schools"]}#bands[{i}]'} for i, b in enumerate(need(S, 'bands', SRC['schools']))]
districts = [{'district': need(d, 'district', 'district'), 'status': need(d, 'status', 'district'),
              'source': f'{SRC["schools"]}#districts[{i}]'} for i, d in enumerate(need(S, 'districts', SRC['schools']))]

# ---- Cognition.X K-12 blocks (COGX_CONTRACT): transfer moments at the places a block maps to ----
# Block text is quoted VERBATIM (all 10 upstream columns kept by cognitionx/); CC-BY-4.0 attribution travels with it.
# Supported place grammars = the classroom ones (station, k12 step, wilds site, campus hall/seat); a k12 step also
# fires at its station. Other grammars (path quotes, module:) are counted as unsupported, never guessed.
CX_ATTR = need(CX, 'attribution', SRC['cognitionx'])
for _k in ('text', 'license', 'license_url', 'repo', 'commit', 'changes'):
    need(CX_ATTR, _k, 'cognitionx attribution')
if need(CX_ATTR, 'license', 'cognitionx attribution') != 'CC-BY-4.0':
    raise ClassroomError('classroom: cognitionx content licence is not CC-BY-4.0')
CX_HON = need(CX, 'honesty', SRC['cognitionx'])
CX_COLS = ('block_id', 'pack', 'track', 'code', 'grade', 'level', 'credential', 'theme', 'description', 'transfer_check')
cx_places = {need(p, 'id', 'cognitionx place'): p for p in need(CX, 'places', SRC['cognitionx'])}


def cx_place(pid):
    """a cognitionx place id -> classroom place ids (resolved against OUR registries), or [] if unsupported"""
    kind = need(cx_places[pid], 'kind', pid) if pid in cx_places else None
    if kind is None:
        raise ClassroomError(f'classroom: cognitionx block names place {pid} that cognitionx.places does not declare')
    ref = need(cx_places[pid], 'ref', pid)
    if kind == 'station':
        return [station_place(need(ref, 'station', pid))] if pid == f'parish:{need(ref, "fips", pid)}/{ref["station"]}' else []
    if kind == 'path-step':
        if pid not in places:
            raise ClassroomError(f'classroom: cognitionx k12 step {pid} is not a k12 path step here')
        return [pid, station_place(places[pid]['ref']['station'])]
    if kind == 'site':
        hits = [e for es in wilds_by_hall.values() for e in es if e[0] == pid] + [e for es in wilds_by_lesson.values() for e in es if e[0] == pid]
        if hits:
            return [wild_place(hits[0])]
        for w in need(WI, 'worlds', SRC['wilds']):
            for i, site in enumerate(w['sites']):
                if f'wilds:{w["id"]}/{site["id"]}' == pid:
                    return [add_place(pid, 'wilds', 'site', {'world': w['id'], 'site': site['id']},
                                      f'{SRC["wilds"]}#worlds[id={w["id"]}].sites[{i}]', site['title'], WORLD_PAGES['wilds'])]
        raise ClassroomError(f'classroom: cognitionx site {pid} is not a wilds site')
    if kind in ('hall', 'seat'):
        if pid not in places:
            hall = need(ref, 'hall', pid)
            if hall not in hall_names:
                raise ClassroomError(f'classroom: cognitionx campus place {pid} names unknown hall {hall}')
            if kind == 'hall':
                return [add_place(pid, 'campus', 'hall', {'hall': hall}, f'{SRC["lessons"]}#lessons[hall={hall}]', hall_names[hall],
                                  f'{WORLD_PAGES["campus"]}?hall={hall}')]
            sim = need(ref, 'sim', pid)
            if sim not in SIMS or sim not in [b['sim'] for b in BIND.get(hall, [])]:
                raise ClassroomError(f'classroom: cognitionx seat {pid} is not a bound sim of hall {hall}')
            return [add_place(pid, 'campus', 'seat', {'hall': hall, 'sim': sim}, f'{SRC["sims"]}#hall_bindings.{hall}[sim={sim}]',
                              f'{hall_names[hall]}: {need(SIMS[sim], "name", sim)}', f'{WORLD_PAGES["campus"]}?hall={hall}&sim={sim}')]
        return [pid]
    return []


cx_mods = {need(m, 'id', 'cognitionx module'): m for m in need(CX, 'modules', SRC['cognitionx'])}
cx_moments, cx_unsupported = [], 0
for bl in need(CX, 'blocks', SRC['cognitionx']):
    bp = need(bl, 'places', 'cognitionx block')
    if not bp:
        continue
    got = []
    for pid in bp:
        r = cx_place(pid)
        cx_unsupported += 0 if r else 1
        got += r
    if not got:
        continue
    field = need(bl, 'statement_field', bl['block_id'])
    if field not in ('description', 'theme'):
        raise ClassroomError(f'classroom: cognitionx block {bl["block_id"]} has statement_field {field!r}')
    mod = need(bl, 'module', bl['block_id'])
    if mod not in cx_mods:
        raise ClassroomError(f'classroom: cognitionx block {bl["block_id"]} names unknown module {mod}')
    cx_moments.append({'id': 'tx-' + bl['block_id'], 'module': mod, 'kind': 'transfer', 'block': {k: need(bl, k, bl['block_id']) for k in CX_COLS},
                       'band': need(bl, 'band', bl['block_id']), 'statement_field': field,
                       'source': f'{SRC["cognitionx"]}#blocks[block_id={bl["block_id"]}]', 'places': sorted(set(got))})
used_mods = sorted({m['module'] for m in cx_moments})
cx_modules = [{'id': mid, 'kind': 'cognitionx', 'pack': need(cx_mods[mid], 'pack', mid), 'name': need(cx_mods[mid], 'name', mid),
               'group': need(cx_mods[mid], 'group', mid), 'bands': need(cx_mods[mid], 'bands', mid),
               'moments': [m['id'] for m in cx_moments if m['module'] == mid],
               'places': sorted({p for m in cx_moments if m['module'] == mid for p in m['places']})} for mid in used_mods]
cognitionx = {'attribution': {k: CX_ATTR[k] for k in ('text', 'license', 'license_url', 'repo', 'commit', 'changes')},
              'honesty': CX_HON, 'modules': cx_modules, 'moments': cx_moments,
              'counts': {'blocks_mapped_upstream': sum(1 for b in CX['blocks'] if b['places']), 'moments': len(cx_moments),
                         'modules': len(cx_modules), 'unsupported_place_links': cx_unsupported}}

# ---- AUTHORED play rules (game design, not facts) ----
rules = {
    'provenance': 'AUTHORED',
    'what': 'game rules written here for play; they measure nothing and certify nothing',
    'xp': {'place_reached': 5, 'moment_tried': 5, 'moment_correct': 20, 'module_complete': 50},
    'transfer': 'a Cognition.X transfer moment is self-reported ("I tried it for real"): it earns moment_tried + moment_correct XP as play; nothing is checked',
    'streak': {'unit': 'day', 'rule': 'a calendar day (the browser\'s clock) with at least one lesson moment met keeps the streak; a missed day resets it to 1'},
    'session_minutes': {'choices': [10, 20, 30, 45], 'default': 20},
    'badges': [
        {'id': 'class-first-moment', 'rule': {'kind': 'moments', 'n': 1}},
        {'id': 'class-five-moments', 'rule': {'kind': 'moments', 'n': 5}},
        {'id': 'class-three-worlds', 'rule': {'kind': 'worlds', 'n': 3}},
        {'id': 'class-streak-3', 'rule': {'kind': 'streak', 'n': 3}},
        {'id': 'class-module-done', 'rule': {'kind': 'modules', 'n': 1}},
        {'id': 'class-xp-500', 'rule': {'kind': 'xp', 'n': 500}},
    ],
}

src_stamp = hashlib.sha256(b''.join(RAW[k] for k in sorted(RAW))).hexdigest()[:16]
doc = {
    'pack': 'classroom',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'source_stamp': src_stamp,
    'sources': [{'id': k, 'path': SRC[k], 'sha256': hashlib.sha256(RAW[k]).hexdigest()[:16]} for k in sorted(SRC)],
    'honesty': {
        'play': 'Sessions, XP, streaks, badges and scoreboards are play. They stay in this browser, never enter a completion record and certify nothing.',
        'lessons': LHON['content'].split('.')[0] + ' - lessons are quoted verbatim from the lessons pack.',
        'districts': SHON['districts'],
        'plans': 'A class plan is a file and a link that selects worlds, modules and rules. No server enforces it: it is not access control and not authentication.',
        'data': 'No student data leaves the browser. A class scoreboard exists only when a teacher imports progress files that learners chose to export.',
        'standards': 'No grade-level standards alignment is claimed; the K-12 bands are the schools pack\'s own bands, quoted.',
    },
    'worlds': [{'id': w, 'page': p} for w, p in WORLD_PAGES.items()],
    'bands': bands,
    'districts': districts,
    'teacher_model': teacher_model,
    'rules': rules,
    'counts': {'modules': len(modules), 'moments': len(moments), 'places': len(places),
               'places_by_world': {w: sum(1 for p in places.values() if p['world'] == w) for w in WORLD_PAGES},
               'lessons': len({m['lesson'] for m in moments})},
    'modules': modules,
    'moments': moments,
    'cognitionx': cognitionx,
    'places': [places[k] for k in sorted(places)],
}
text = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
if '--check' in sys.argv:
    if not OUT.is_file() or OUT.read_text(encoding='utf-8') != text:
        print('STALE: classroom/registry/classroom.json\n       run: python3 classroom/build.py')
        sys.exit(1)
    print('classroom/registry/classroom.json is current')
    sys.exit(0)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(text, encoding='utf-8')
c = doc['counts']
print(f'classroom: {c["modules"]} modules | {c["moments"]} moments | {c["places"]} places {c["places_by_world"]} | stamp {src_stamp}')
