#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy - world training modules (wave 19).

WHAT THIS IS. A world module is a short ordered practice set that stands in one of the walkable worlds, composed by a
stated RULE from registries that already exist. It adds no lesson, no step kind, no episode kind and no storage key:
`lessons/`, `completion/` and `courses/` are read and never changed, so their contracts stay exactly as they were.

FOUR SOURCES, ONE RULE EACH (printed into the registry under `rules`):
  * worksite district - per union district (unions/registry/districts.json), the worksites (worksites/registry/
    worksites.json) whose crew musters from a first hall of that district; the steps are the hand-off evidence of those
    worksites in hand-off order (from, then to), each evidence already one of the lesson step kinds. A district with no
    such worksite gets no module and its reason is printed.
  * restoration site - per WALKABLE site of restoration/registry/restoration.json: the scenario steps and the staged
    task title and brief of restoration/registry/scenarios.json quoted verbatim as the brief, then the hand-off evidence
    of any worksite standing at that site, then for each trade the site needs the opening step and the first recording
    step of that hall's first lesson in union-path order (unionpaths/registry/union_paths.json).
  * wilds world - per world of wilds/registry/wilds.json: the steps of its existing site walks (lessons whose arc is
    "site"), in site order, copied verbatim.
  * robot yard - one module: watch the SCRIPTED reference rover in the walkable world, then drive the same env in the
    Robotics lab. Both steps are the existing `world-teleop` episode kind (training/registry/training.json), told apart
    only by its existing `actor` field.

GREETER. Every module names one Omega Hive agent (hive/registry/hive.json): SCRIPTED, no AI model, the device's speech
synthesis, on a click. Its line is the agent's own first greeting line (else its first line), quoted with its source.

LIMITS. Lessons and modules are unverified general practice. Nothing here certifies, qualifies or licenses anybody, no
duration is stated and no credential is named; the build refuses a module whose authored words claim otherwise.
Python comments may carry the team codename; nothing built from this file does.
"""
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'modules.json'
BUILT = '2026-10-12'


class ModuleError(Exception):
    pass


def need(cond, msg):
    if not cond:
        raise ModuleError(msg)


def req(d, k, ctx):
    if not isinstance(d, dict) or k not in d:
        raise ModuleError(f'{ctx}: {k!r} does not resolve')
    return d[k]


SOURCES = ['lessons/registry/lessons.json', 'training/registry/training.json', 'worksites/registry/worksites.json',
           'unions/registry/districts.json', 'restoration/registry/restoration.json',
           'restoration/registry/scenarios.json', 'wilds/registry/wilds.json', 'robotics/registry/robotics.json',
           'hive/registry/hive.json', 'agents/registry/crews.json', 'sims/registry/sims.json',
           'stations/registry/stations.json', 'unionpaths/registry/union_paths.json', 'courses/registry/courses.json']
_RAW = {p: (ROOT / p).read_bytes() for p in SOURCES}
R = {p: json.loads(b) for p, b in _RAW.items()}

LESSONS = req(R['lessons/registry/lessons.json'], 'lessons', 'lessons.json')
LESSON_KINDS = req(R['lessons/registry/lessons.json'], 'step_kinds', 'lessons.json')
TRAINING = R['training/registry/training.json']
WORLD_KINDS = req(TRAINING, 'world_episode_kinds', 'training.json')
ACTORS = req(TRAINING, 'actors', 'training.json')
# The closed set: the lesson step kinds plus the world episode kinds training/ already declares. Nothing new.
STEP_KINDS = sorted(LESSON_KINDS) + sorted(WORLD_KINDS)
need(not set(LESSON_KINDS) & set(WORLD_KINDS), 'a world episode kind shares a name with a lesson step kind')

CREWS = req(R['agents/registry/crews.json'], 'crews', 'crews.json')
SIMS = req(R['sims/registry/sims.json'], 'sims', 'sims.json')
STATIONS = {req(s, 'station_id', 'stations[]'): s for s in req(R['stations/registry/stations.json'], 'stations', 'stations.json')}
HIVE = {req(a, 'id', 'hive.agents[]'): a for a in req(R['hive/registry/hive.json'], 'agents', 'hive.json')}
SUPS = req(R['courses/registry/courses.json'], 'supplements', 'courses.json')
UPATH = {req(h, 'hall', 'union_paths.halls[]'): h for h in req(R['unionpaths/registry/union_paths.json'], 'halls', 'union_paths.json')}
DISTRICTS = req(R['unions/registry/districts.json'], 'districts', 'districts.json')
HALL_DISTRICT = {}
for _dk, _d in DISTRICTS.items():
    for _h in req(_d, 'halls', f'districts.{_dk}'):
        HALL_DISTRICT[_h] = _dk

# ------------------------------------------------------------------ resolving one step against its owner registry ---


def resolve_evidence(ev, ctx):
    """A worksite evidence record -> a module step of the same (lesson) kind, every id resolved."""
    kind = req(ev, 'kind', ctx)
    need(kind in LESSON_KINDS, f'{ctx}: evidence kind {kind!r} is not a lesson step kind')
    step = {'kind': kind, 'records': req(LESSON_KINDS[kind], 'records', f'step_kinds.{kind}')}
    if kind == 'crew':
        crew = req(CREWS, req(ev, 'crew', ctx), f'{ctx} crew')
        role = req(req(crew, 'roles', ctx), req(ev, 'role', ctx), f'{ctx} role')
        topics = {req(t, 'id', ctx): t for t in req(role, 'topics', ctx)}
        topic = req(topics, req(ev, 'topic', ctx), f'{ctx} topic')
        need(req(topic, 'ask', ctx) == req(ev, 'ask', ctx), f'{ctx}: the ask is not the crews registry wording')
        step.update(crew=ev['crew'], role=ev['role'], topic=ev['topic'], ask=topic['ask'],
                    agent=f"crew:{ev['crew']}:{ev['role']}")
    elif kind == 'walkaround':
        seat = req(SIMS, req(ev, 'sim', ctx), f'{ctx} sim')
        pts = {req(p, 'id', ctx): p for p in req(seat, 'walkaround', ctx)}
        pt = req(pts, req(ev, 'point', ctx), f'{ctx} point')
        need(req(pt, 'check', ctx) == req(ev, 'check', ctx), f'{ctx}: the check is not the sims registry wording')
        step.update(sim=ev['sim'], point=ev['point'], label=req(pt, 'point', ctx), check=pt['check'])
    elif kind == 'sim':
        seat = req(SIMS, req(ev, 'sim', ctx), f'{ctx} sim')
        scs = {req(s, 'id', ctx): s for s in req(seat, 'scenarios', ctx)}
        sc = req(scs, req(ev, 'scenario', ctx), f'{ctx} scenario')
        step.update(sim=ev['sim'], scenario=ev['scenario'], seat_name=req(seat, 'name', ctx), scenario_name=req(sc, 'name', ctx))
    elif kind == 'station':
        st = req(STATIONS, req(ev, 'station', ctx), f'{ctx} station')
        step.update(station=ev['station'], station_name=req(st, 'name', ctx))
    else:
        raise ModuleError(f'{ctx}: evidence kind {kind!r} has no resolver here')
    return step


def lesson_step(lid, n, ctx):
    """A step copied verbatim from lessons.json, with its pointer."""
    L = req(LESSONS, lid, ctx)
    steps = req(L, 'steps', lid)
    need(1 <= n <= len(steps) and steps[n - 1]['n'] == n, f'{ctx}: {lid} has no step {n}')
    st = dict(steps[n - 1])
    need(st['kind'] in LESSON_KINDS, f'{ctx}: {lid} step {n} kind {st["kind"]!r} is not a lesson step kind')
    out = {k: st[k] for k in st if k != 'n'}
    out.update(lesson=lid, lesson_step=n, hall=req(L, 'hall', lid))
    return out


def greeter(agent_id, rule, ctx):
    a = req(HIVE, agent_id, f'{ctx} greeter')
    lines = req(a, 'lines', agent_id)
    need(lines, f'{ctx}: {agent_id} has no lines')
    g = [ln for ln in lines if ln['kind'] == 'greeting']
    line = g[0] if g else lines[0]
    return {'agent': agent_id, 'name': req(a, 'name', agent_id), 'kind': req(a, 'kind', agent_id),
            'glyph': req(a, 'glyph', agent_id), 'line': req(line, 'text', agent_id), 'line_source': req(line, 'source', agent_id),
            'rule': rule, 'provenance': 'SCRIPTED', 'voice': 'the device speech synthesis, on a click; no AI model'}


def dedupe(steps):
    seen, out = set(), []
    for s in steps:
        key = json.dumps({k: s[k] for k in sorted(s) if k not in ('note', 'from')}, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    for i, s in enumerate(out, 1):
        s['n'] = i
    return out


MODULES, REFUSED = [], {}

# ------------------------------------------------------------------------------------------ worksite districts ---
WORKSITES = req(R['worksites/registry/worksites.json'], 'sites', 'worksites.json')
by_district = {}
for i, ws in enumerate(WORKSITES):
    first_hall = req(req(ws, 'crew', ws['id']), 'halls', ws['id'])[0]
    dk = req(HALL_DISTRICT, first_hall, f'worksite {ws["id"]} first crew hall')
    by_district.setdefault(dk, []).append((i, ws))


def worksite_steps(i, ws):
    out = []
    for h in req(ws, 'handoffs', ws['id']):
        for side in ('from_evidence', 'to_evidence'):
            ev = req(h, side, f'{ws["id"]} handoff {h["n"]}')
            if ev is None:
                continue
            st = resolve_evidence(ev, f'{ws["id"]} handoff {h["n"]} {side}')
            st['note'] = req(h, 'step', ws['id'])
            st['from'] = f'worksites/registry/worksites.json#sites[{i}].handoffs[{h["n"] - 1}].{side}'
            st['worksite'] = ws['id']
            out.append(st)
    return out


for dk, d in DISTRICTS.items():
    sites = by_district.get(dk)
    if not sites:
        REFUSED[f'worksite-district:{dk}'] = 'no worksite in worksites.json has a crew whose first hall stands in this district'
        continue
    steps = dedupe([s for i, ws in sites for s in worksite_steps(i, ws)])
    first_crew = next(s for s in steps if s['kind'] == 'crew') if any(s['kind'] == 'crew' for s in steps) else None
    gid = first_crew['agent'] if first_crew and first_crew['agent'] in HIVE else 'advisor:guide'
    MODULES.append({
        'id': f'module-worksites-{dk}', 'family': 'worksite-district', 'district': dk, 'district_name': d['name'],
        'title': f"{d['name']} worksites", 'world': 'bay',
        'places': [{'worksite': ws['id'], 'title': ws['title'], 'place_kind': ws['place']['kind'], 'place': ws['place']['id'],
                    'source': f'worksites/registry/worksites.json#sites[{i}]'} for i, ws in sites],
        'brief': [{'text': ws['job'], 'source': f'worksites/registry/worksites.json#sites[{i}].job'} for i, ws in sites],
        'steps': steps,
        'greeter': greeter(gid, 'the Hive crew role asked in the first crew step; else the door guide', dk)})

# ---------------------------------------------------------------------------------------- restoration sites ---
RESTO = req(R['restoration/registry/restoration.json'], 'sites', 'restoration.json')
SCEN = R['restoration/registry/scenarios.json']
for site in RESTO:
    sid = req(site, 'id', 'restoration.sites[]')
    if not req(site, 'walkable', sid):
        REFUSED[f'restoration:{sid}'] = req(site, 'walkable_reason', sid)
        continue
    brief = []
    for i, sc in enumerate(req(SCEN, 'scenarios', 'scenarios.json')):
        if sc['site'] != sid:
            continue
        brief.append({'text': req(sc, 'title', sc['id']), 'source': f'restoration/registry/scenarios.json#scenarios[{i}].title'})
        for j, stp in enumerate(req(sc, 'steps', sc['id'])):
            brief.append({'text': req(stp, 'text', sc['id']), 'source': f'restoration/registry/scenarios.json#scenarios[{i}].steps[{j}].text'})
    runners = []
    for i, t in enumerate(req(SCEN, 'staged_tasks', 'scenarios.json')):
        if t['place']['id'] != sid:
            continue
        brief.append({'text': req(t, 'title', t['id']), 'source': f'restoration/registry/scenarios.json#staged_tasks[{i}].title'})
        brief.append({'text': req(t, 'brief', t['id']), 'source': f'restoration/registry/scenarios.json#staged_tasks[{i}].brief'})
        runners.append({'task': t['id'], 'href': req(req(t, 'launch', t['id']), 'href', t['id'])})
    need(brief, f'restoration {sid}: walkable, yet no scenario or staged task quotes it')
    steps = [s for i, ws in enumerate(WORKSITES) if ws['place']['id'] == sid for s in worksite_steps(i, ws)]
    trades = req(site, 'trade_needs', sid)
    for hall in trades:
        up = req(UPATH, hall, f'restoration {sid} trade')
        lids = [req(x, 'lesson', hall) for x in req(up, 'lessons', hall)]
        need(lids, f'restoration {sid}: hall {hall} has no lesson in its union path')
        L = LESSONS[lids[0]]
        steps.append(lesson_step(lids[0], 1, sid))
        rec = [s['n'] for s in L['steps'] if s['records'] is not None]
        if rec:
            steps.append(lesson_step(lids[0], rec[0], sid))
    steps = dedupe(steps)
    gid = req(req(UPATH, trades[0], sid), 'advisor', trades[0])['id']
    MODULES.append({
        'id': f'module-restoration-{sid}', 'family': 'restoration-site', 'site': sid, 'title': req(site, 'name', sid),
        'world': 'bay', 'places': [{'restoration_site': sid, 'source': f'restoration/registry/restoration.json#sites[{RESTO.index(site)}]'}],
        'runners': runners, 'brief': brief, 'steps': steps,
        'greeter': greeter(gid, "the Omega Hive advisor the union path names for the site's first needed trade", sid)})

# --------------------------------------------------------------------------------------------- wilds worlds ---
SITE_WALKS = {}
for lid, L in LESSONS.items():
    if L.get('arc') == 'site':
        SITE_WALKS.setdefault(L['site']['id'], []).append(lid)
WILDS_WORLDS = req(R['wilds/registry/wilds.json'], 'worlds', 'wilds.json')
for w in WILDS_WORLDS:
    wid = req(w, 'id', 'wilds.worlds[]')
    steps, places, brief = [], [], []
    for s in req(w, 'sites', wid):
        for lid in SITE_WALKS.get(s['id'], []):
            places.append({'wilds_site': s['id'], 'title': s['title'], 'lesson': lid})
        if SITE_WALKS.get(s['id']):
            wi = w['sites'].index(s)
            brief += [{'text': req(s, 'title', s['id']), 'source': f'wilds/registry/wilds.json#worlds[{WILDS_WORLDS.index(w)}].sites[{wi}].title'},
                      {'text': req(s, 'work', s['id']), 'source': f'wilds/registry/wilds.json#worlds[{WILDS_WORLDS.index(w)}].sites[{wi}].work'}]
            steps += [lesson_step(lid, st['n'], wid) for st in LESSONS[lid]['steps']]
    if not steps:
        REFUSED[f'wilds:{wid}'] = 'no site of this world has a site walk in lessons.json'
        continue
    steps = dedupe(steps)
    adv = next(s['advisor'] for s in steps if s['kind'] == 'advisor')
    MODULES.append({
        'id': f'module-wilds-{wid}', 'family': 'wilds-world', 'world': f'wilds:{wid}', 'title': req(w, 'name', wid),
        'places': places, 'brief': brief, 'steps': steps,
        'greeter': greeter(f'advisor:{adv}', 'the Hive advisor asked in the first advisor step of the first site walk', wid)})

# ------------------------------------------------------------------------------------------------ robot yard ---
ROBO = R['robotics/registry/robotics.json']
ENV_ID = 'world.litter-pickup'           # the env the walkable-world rover yard replays (web/build_parishes.py)
env = req(req(ROBO, 'envs', 'robotics.json'), ENV_ID, 'robotics.envs')
pol = req(env, 'reference_policy', ENV_ID)
need(req(pol, 'provenance', ENV_ID) == 'SCRIPTED', f'{ENV_ID}: the reference policy is not SCRIPTED')
emb = req(env, 'embodiments', ENV_ID)[0]
pages = req(req(env, 'world', ENV_ID), 'pages', ENV_ID)
need('web/trade_craft_parishes.html' in pages and 'web/trade_craft_robotics.html' in pages, f'{ENV_ID}: world or lab page not listed')
need('scripted-reference' in json.dumps(ACTORS) and 'human' in json.dumps(ACTORS), 'training actors lack human / scripted-reference')
MODULES.append({
    'id': 'module-robot-yard', 'family': 'robot-yard', 'world': 'parishes', 'title': req(env, 'name', ENV_ID),
    'places': [{'env': ENV_ID, 'source': f'robotics/registry/robotics.json#envs["{ENV_ID}"]'}],
    'brief': [{'text': req(env, 'brief', ENV_ID), 'source': f'robotics/registry/robotics.json#envs["{ENV_ID}"].brief'}] +
             [{'text': t, 'source': f'robotics/registry/robotics.json#envs["{ENV_ID}"].reference_policy.steps[{j}]'}
              for j, t in enumerate(req(pol, 'steps', ENV_ID))],
    'steps': [
        {'n': 1, 'kind': 'world-teleop', 'actor': 'scripted-reference', 'env': ENV_ID, 'embodiment': emb, 'policy': pol['id'],
         'page': 'web/trade_craft_parishes.html', 'records': None,
         'note': 'watch: the rover yard replays the reference steps on a seeded loop and stores nothing'},
        {'n': 2, 'kind': 'world-teleop', 'actor': 'human', 'env': ENV_ID, 'embodiment': emb,
         'page': 'web/trade_craft_robotics.html', 'records': 'world-teleop',
         'note': 'drive: the same env at the keys in the Robotics lab, recorded by the lab as its existing world-teleop episode'}],
    'greeter': greeter('advisor:operator', 'the Hive operator advisor, an AUTHORED choice for a driving task', 'robot-yard')})

# --------------------------------------------------------------------------------------------- checks + write ---
CERT = re.compile(r'\b(certif(?:y|ies|ied|ying|icate|icates|ication|ications)|qualif(?:y|ies|ied|ication|ications)|'
                  r'licen[cs](?:e|es|ed|ing)|accredit\w*|diploma\w*|credential\w*)\b', re.I)
DURATION = re.compile(r'\b\d+\s*(?:min|mins|minutes?|hours?|hrs?|days?|weeks?)\b|\bseat[- ]time\b', re.I)
SUP_CAP = 6


def supplements_of(m):
    """The module's own lessons, then lessons whose steps run the same seat or ask the same crew, registry order, capped."""
    seats = {s['sim'] for s in m['steps'] if s['kind'] in ('sim', 'walkaround')}
    crews = {s['crew'] for s in m['steps'] if s['kind'] == 'crew'}
    near = [lid for lid, L in LESSONS.items() if lid not in m['lessons'] and any(
        (st['kind'] in ('sim', 'walkaround') and st.get('sim') in seats) or (st['kind'] == 'crew' and st.get('crew') in crews)
        for st in L['steps'])]
    return (m['lessons'] + near)[:max(SUP_CAP, len(m['lessons']))]


for m in MODULES:
    need(m['steps'], f'{m["id"]}: no steps')
    for k, s in enumerate(m['steps'], 1):
        need(s['n'] == k, f'{m["id"]}: steps are not numbered in order')
        need(s['kind'] in STEP_KINDS, f'{m["id"]} step {k}: kind {s["kind"]!r} is not an existing step kind')
        want = LESSON_KINDS[s['kind']]['records'] if s['kind'] in LESSON_KINDS else s['records']
        need(s['records'] == want, f'{m["id"]} step {k}: records {s["records"]!r} is not the kind\'s own')
    authored = ' '.join([m['title'], m['greeter']['rule']] + [s.get('note', '') for s in m['steps'] if 'lesson' not in s and 'worksite' not in s])
    need(not CERT.search(authored), f'{m["id"]}: authored words claim a certificate, qualification or licence: {CERT.search(authored)}')
    need(not DURATION.search(authored), f'{m["id"]}: authored words state a duration')
    m['lessons'] = [lid for lid in LESSONS if any(s.get('lesson') == lid for s in m['steps'])]
    m['supplements'] = supplements_of(m)
    need(all(lid in SUPS for lid in m['supplements']), f'{m["id"]}: a supplement does not resolve in courses.json')
    m['provenance'] = 'AUTHORED by rule'
    m['standing'] = 'unverified general practice; certifies nobody'

ids = [m['id'] for m in MODULES]
need(len(ids) == len(set(ids)), 'module ids repeat')
by_family = {}
for m in MODULES:
    by_family[m['family']] = by_family.get(m['family'], 0) + 1
by_kind = {}
for m in MODULES:
    for s in m['steps']:
        by_kind[s['kind']] = by_kind.get(s['kind'], 0) + 1

stamp = hashlib.sha256((HERE / 'build.py').read_bytes() + b''.join(_RAW[p] for p in SOURCES)).hexdigest()
doc = {
    'pack': 'modules', 'schema': 'tc-modules/1', 'built': BUILT, 'source_stamp': stamp, 'sources': SOURCES,
    'provenance': 'AUTHORED by rule: every module is composed by a rule in modules/build.py from the registries listed; '
                  'every step is one of the existing step kinds and every id resolves in the registry that owns it',
    'honesty': {
        'standing': 'Lessons and modules are unverified general practice. Nothing here certifies, qualifies or licenses anybody.',
        'no_durations': 'No duration and no credential is stated; none of the source registries declares one.',
        'greeters': 'Omega Hive: SCRIPTED, no AI model, the device speech synthesis, on a click, AUTHORED personalities.',
        'no_new_kinds': 'No new step kind, episode kind or storage key: lessons, completion and courses are read, never changed.'},
    'step_kinds': STEP_KINDS,
    'rules': {
        'worksite-district': 'per union district, the worksites whose crew musters from a first hall of that district; steps are their hand-off evidence (from, then to) in order, duplicates dropped',
        'restoration-site': 'per walkable restoration site: scenario titles and steps and staged task title and brief quoted verbatim as the brief; steps are the hand-off evidence of worksites at the site, then per needed trade the opening step and first recording step of the first lesson in its union path',
        'wilds-world': 'per wilds world: the steps of its site walks in site order, copied verbatim from lessons.json',
        'robot-yard': 'one module: watch the SCRIPTED reference rover in the walkable world (world-teleop, actor scripted-reference), then drive the same env in the Robotics lab (world-teleop, actor human)',
        'greeter': 'one Omega Hive agent per module; the line is its first greeting line, else its first line',
        'supplements': 'the module\'s own lessons, then lessons whose steps run the same seat or ask the same crew, in lessons registry order, at most 6 unless its own lessons are more; each is a courses.json supplement'},
    'counts': {'modules': len(MODULES), 'by_family': by_family, 'steps': sum(len(m['steps']) for m in MODULES),
               'steps_by_kind': dict(sorted(by_kind.items())), 'brief_quotes': sum(len(m['brief']) for m in MODULES),
               'lessons_referenced': len({l for m in MODULES for l in m['lessons']}),
               'greeters': len({m['greeter']['agent'] for m in MODULES}), 'refused': len(REFUSED),
               'certifies': 0, 'durations': 0, 'trained_models': 0},
    'refused': REFUSED,
    'modules': MODULES,
}
text = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
if '--check' in sys.argv:
    if not OUT.exists() or OUT.read_text() != text:
        print('modules: registry is stale; run python3 modules/build.py', file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(text)
c = doc['counts']
print(f"modules: {c['modules']} modules {c['by_family']}, {c['steps']} steps {c['steps_by_kind']}, "
      f"{c['brief_quotes']} verbatim brief quotes, {c['lessons_referenced']} lessons referenced, "
      f"{c['greeters']} greeters, {c['refused']} refused; certifies nobody")
