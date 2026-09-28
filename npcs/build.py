#!/usr/bin/env python3
"""NPC guides for the parish world: people who pass knowledge along by QUOTING.

An NPC here is a scripted figure, not an AI and not a person. Every line it can
say is a verbatim copy of one field of a registry this bundle already ships
(unions/, schools/, lessons/, tasks/, restoration/), carried with the path of
that field ("<file>#<json path>"). Nothing is generated, paraphrased or
summarised; npcs/test.mjs re-reads every source path and compares the text
byte for byte.

Roster, per parish:
  - union trade mentors: one per trade family (a district of
    unions/registry/districts.json) present in the parish;
  - Cognition.X K-12 guides: content from the schools/ K-12 units and bands and
    the lessons/ pack (the layer is named "Cognition.X K-12" as the product
    asks; its content comes ONLY from those two registries);
  - restoration rangers, ferry/boat pilots, station hosts.

Look: an appearance recipe is a set of avatars/ locker option ids (the same
cfg web/build_3d.py's buildAvatarMesh(cfg) reads), each id checked against
its section. Names: a role title and one AUTHORED nature word - fictional and
clearly not a real person's name.

Places: until the PARISH / LAYERS registries exist in the tree, the roster
stands on ONE stub parish (Orleans, FIPS 22071) with STUB home places; the
registry says so on its face (places_status). Fail closed: a missing field or
an unknown option / place / source stops the build by name.
"""
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent


class NPCBuildError(Exception):
    pass


def load(rel):
    p = ROOT / rel
    if not p.exists():
        raise NPCBuildError(f'missing source registry {rel}')
    return json.load(open(p))


SOURCES = {
    'unions': 'unions/registry/unions.json',
    'districts': 'unions/registry/districts.json',
    'schools': 'schools/registry/schools.json',
    'lessons': 'lessons/registry/lessons.json',
    'tasks': 'tasks/registry/tasks.json',
    'restoration': 'restoration/registry/restoration.json',
    'avatars': 'avatars/registry/avatars.json',
}
REG = {k: load(v) for k, v in SOURCES.items()}
PARISH_REG = 'parishes/registry/parishes.json'
LAYERS_REG = 'layers/registry/layers.json'

# ------------------------------------------------------------- JSON paths --
_TOK = re.compile(r'\.?([A-Za-z0-9_\-]+)|\[(\d+)\]')


def resolve(rel, path):
    """Read the value at "<a>.<b>[i].<c>" in registry rel; fail by name."""
    node = load(rel) if rel not in SOURCES.values() else REG[
        [k for k, v in SOURCES.items() if v == rel][0]]
    pos = 0
    while pos < len(path):
        m = _TOK.match(path, pos)
        if not m:
            raise NPCBuildError(f'bad source path {rel}#{path}')
        key, idx = m.group(1), m.group(2)
        if idx is not None:
            if not isinstance(node, list) or int(idx) >= len(node):
                raise NPCBuildError(f'source path {rel}#{path}: no index {idx}')
            node = node[int(idx)]
        else:
            if not isinstance(node, dict) or key not in node:
                raise NPCBuildError(f'source path {rel}#{path}: no key {key}')
            node = node[key]
        pos = m.end()
    return node


def quote(src_key, path):
    rel = SOURCES[src_key]
    text = resolve(rel, path)
    if not isinstance(text, str) or not text.strip():
        raise NPCBuildError(f'{rel}#{path} is not a non-empty string')
    return {'text': text, 'source': f'{rel}#{path}'}


# ------------------------------------------------------------ AUTHORED names
# Fictional: a role title plus ONE nature word. Never a given+family pair.
NAME_WORDS = ('Egret', 'Heron', 'Cypress', 'Tupelo', 'Willow', 'Juniper',
              'Sorrel', 'Aster', 'Magnolia', 'Pelican', 'Bayou', 'Cattail',
              'Marsh', 'Palmetto', 'Iris', 'Laurel', 'Sassafras', 'Spoonbill',
              'Ibis', 'Kestrel', 'Tern', 'Plover', 'Sedge', 'Moss', 'Cedar',
              'Hickory', 'Pecan', 'Mayhaw', 'Wren', 'Osprey', 'Rail',
              'Bittern', 'Gallinule', 'Loon', 'Teal', 'Grebe', 'Alder',
              'Birch', 'Rush', 'Fern')
ROLE_TITLE = {'mentor': 'Mentor', 'k12-guide': 'Guide', 'ranger': 'Ranger',
              'pilot': 'Pilot', 'host': 'Host'}

# ---------------------------------------------------- appearance (avatars/) --
AV = REG['avatars']
SECTION = {s['id']: s for s in AV['sections']}
OPTS = {sid: {o['id']: o for o in s['options']} for sid, s in SECTION.items()}
ROLE_OUTFIT = {   # AUTHORED outfits, locker option ids only
    'mentor': {'headwear': 'hard-cap', 'vest': 'hi-vis-2', 'top': 'long-sleeve',
               'tools': 'basic', 'extras': 'safety-glasses'},
    'k12-guide': {'headwear': 'none', 'top': 'polo', 'topcolor': 'royal',
                  'vest': 'none', 'tools': 'none', 'extras': 'id-badge',
                  'pants': 'khaki-work', 'pantscolor': 'sand',
                  'shoes': 'sneaker-black'},
    'ranger': {'headwear': 'bucket', 'headcolor': 'olive', 'top': 'long-sleeve',
               'topcolor': 'forest', 'vest': 'hi-vis-1', 'pants': 'cargo',
               'pantscolor': 'duck-brown', 'shoes': 'wellington',
               'tools': 'none', 'extras': 'radio'},
    'pilot': {'headwear': 'ball-cap', 'headcolor': 'navy', 'top': 'polo',
              'topcolor': 'navy', 'vest': 'none', 'outer': 'rain-slicker',
              'pants': 'rain-pants', 'pantscolor': 'slate',
              'shoes': 'rubber-yellow', 'tools': 'none', 'extras': 'radio'},
    'host': {'headwear': 'none', 'top': 'polo', 'topcolor': 'teal',
             'vest': 'hi-vis-2', 'tools': 'none', 'extras': 'id-badge'},
}
VARY = ('build', 'skin', 'hair', 'haircolor', 'eyes')
PROXY_PARTS = {'torso': 'topcolor', 'legs': 'pantscolor', 'head': 'skin',
               'hat': 'headcolor'}


def appearance(role, i, crew):
    cfg = dict(AV['defaults'])
    for k in VARY:                     # deterministic variety, locker ids only
        ids = list(OPTS[k])
        cfg[k] = ids[(i * 5 + len(k) * 3) % len(ids)]
    cfg.update(ROLE_OUTFIT[role])
    cfg['crew'] = crew
    for k, v in cfg.items():
        if k not in OPTS:
            raise NPCBuildError(f'appearance {role}: unknown locker section {k}')
        if v not in OPTS[k]:
            raise NPCBuildError(f'appearance {role}: {k}={v} is not an avatars/ option')
    proxy = {}
    for part, sec in PROXY_PARTS.items():
        oid = cfg[sec]
        idx = [o['id'] for o in SECTION[sec]['options']].index(oid)
        si = [s['id'] for s in AV['sections']].index(sec)
        proxy[part] = {'hex': OPTS[sec][oid]['value'],
                       'source': f"{SOURCES['avatars']}#sections[{si}].options[{idx}].value"}
    return {'rig': 'avatars locker cfg -> buildAvatarMesh(cfg) (web/build_3d.py)',
            'cfg': cfg, 'proxy': proxy}


# ------------------------------------------------------------------ places --
def parishes_and_places():
    """Parishes (PARISH) + stations/landmarks (LAYERS) when both exist, else a STUB."""
    have_p, have_l = (ROOT / PARISH_REG).exists(), (ROOT / LAYERS_REG).exists()
    if have_p != have_l:
        raise NPCBuildError(f'only one of {PARISH_REG} / {LAYERS_REG} exists: build '
                            'parishes/ then layers/ first')
    if not have_p:
        return [{'fips': '22071', 'name': 'Orleans', 'status': 'STUB'}], 'STUB', None
    par, lay = load(PARISH_REG), load(LAYERS_REG)
    sel = par['selection']['selected']
    lay_fips = [q['fips'] for q in lay['parishes']]
    if sorted(lay_fips) != sorted(sel):
        raise NPCBuildError(f'layers parishes {lay_fips} != parishes selection {sel}')
    parishes = [{'fips': f, 'name': par['parishes'][f]['name'], 'status': 'PARISH+LAYERS'}
                for f in sel]
    return parishes, 'PARISH+LAYERS', (par, lay)


STUB_PLACES = ('trade-hub', 'k12-commons', 'marsh-edge', 'ferry-landing',
               'sim-station', 'crib-station')

# -------------------------------------------------------------- knowledge --
U = REG['unions']['unions']
UIDX = {u['slug']: i for i, u in enumerate(U)}
DIST = REG['districts']['districts']
LES = REG['lessons']['lessons']
TASKS = REG['tasks']['tasks']
TIDX = {t['id']: i for i, t in enumerate(TASKS)}
SCH = REG['schools']
RES = REG['restoration']

ROUTINE = {   # AUTHORED game-clock day: (from_h, to_h, state, radius_m, where)
    'default': ((6, 9, 'wander', 6, 'home'), (9, 13, 'wander', 4, 'station'),
                (13, 15, 'wander', 6, 'landmark'), (15, 19, 'wander', 6, 'home'),
                (19, 6, 'idle', 0, 'home')),
    'pilot': ((5, 9, 'wander', 5, 'home'), (9, 12, 'wander', 4, 'station'),
              (12, 14, 'wander', 5, 'landmark'), (14, 21, 'wander', 5, 'home'),
              (21, 5, 'idle', 0, 'home')),
}


def routine(role, home, station, landmark):
    """A daily walk home -> station (guide_to) -> landmark -> home on simulated time."""
    at = {'home': home, 'station': station, 'landmark': landmark}
    return [{'from_h': f, 'to_h': t, 'state': st, 'radius_m': r, 'at': at[w], 'where': w}
            for f, t, st, r, w in ROUTINE['pilot' if role == 'pilot' else 'default']]


def lesson_for_halls(halls):
    for lid, l in LES.items():
        if l['hall'] in halls:
            return lid
    raise NPCBuildError(f'no lesson in halls {halls[:3]}...')


def mentor(fam):
    d = DIST[fam]
    halls = [h for h in d['halls'] if h in UIDX][:3]
    if len(halls) < 1:
        raise NPCBuildError(f'trade family {fam} has no union rows')
    lid = lesson_for_halls(d['halls'])
    lines = [quote('districts', f'districts.{fam}.tagline')]
    lines += [quote('unions', f'unions[{UIDX[h]}].focus') for h in halls]
    lines += [quote('lessons', f'lessons.{lid}.title'),
              quote('lessons', f'lessons.{lid}.why')]
    return {'family': fam, 'crew': halls[0], 'lines': lines,
            'points_to': {'kind': 'lesson', 'id': lid},
            'not_certification': quote('lessons', f'lessons.{lid}.limits')}


def k12(which):
    bands = SCH['bands']
    pair = (0, 1) if which == 0 else (2, 3)
    unit = SCH['units'][which]
    tier = 'fundamentals' if which == 0 else 'applied'
    lid = next((k for k, l in LES.items() if l['tier'] == tier), None)
    if lid is None:
        raise NPCBuildError(f'no {tier} lesson for the K-12 guide')
    lines = [quote('schools', 'model.loop')]
    lines += [quote('schools', f'bands[{b}].offer') for b in pair]
    lines += [quote('schools', f'units[{which}].gate'),
              quote('schools', 'honesty.districts')]
    return {'crew': unit['hall'], 'lines': lines,
            'bands': [bands[b]['band'] for b in pair],
            'points_to': {'kind': 'lesson', 'id': lid},
            'not_certification': quote('schools', 'honesty.certification')}


def ranger():
    lines = [quote('restoration', f'tracks[{i}].what')
             for i in range(len(RES['tracks']))]
    lines.append(quote('restoration', 'honesty.no_new_skills'))
    tid = next(t['id'] for t in TASKS if t['kind'] == 'restoration-walk')
    return {'crew': 'grounds', 'lines': lines,
            'points_to': {'kind': 'task', 'id': tid},
            'not_certification': quote('tasks', 'honesty.not_certification')}


MARINE = ('marine-terminal', 'marine-pipe', 'shipfitters', 'divers', 'port-crane')


def pilot():
    lines = [quote('unions', f'unions[{UIDX[h]}].focus') for h in MARINE]
    tid = next(t['id'] for t in TASKS
               if t['kind'] == 'crib-drill' and t['place']['id'] == 'marine-terminal')
    return {'crew': 'marine-terminal', 'lines': lines,
            'points_to': {'kind': 'task', 'id': tid},
            'not_certification': quote('tasks', 'honesty.not_certification')}


def host(kind):
    t = next(t for t in TASKS if t['kind'] == kind)
    i = TIDX[t['id']]
    lines = [quote('tasks', f'tasks[{i}].title'), quote('tasks', f'tasks[{i}].brief'),
             quote('tasks', 'honesty.practice'), quote('tasks', 'honesty.requires')]
    crew = t['place']['id'] if t['place']['id'] in OPTS['crew'] else AV['defaults']['crew']
    return {'crew': crew, 'lines': lines, 'points_to': {'kind': 'task', 'id': t['id']},
            'not_certification': quote('tasks', 'honesty.not_certification')}


SIMS = load('sims/registry/sims.json')['sims']
HALL_FAMILY = {h: fam for fam, d in DIST.items() for h in d['halls']}


def station_halls(st, where):
    """The hall(s) a LAYERS station stands for, read from its owning registry."""
    lay, rid = st['layer'], st['ref']['id']
    if lay == 'trade-sim':
        if rid not in SIMS:
            raise NPCBuildError(f'{where}: sim {rid} not in sims/')
        return list(SIMS[rid]['halls'])
    if lay == 'task':
        if rid not in TIDX:
            raise NPCBuildError(f'{where}: task {rid} not in tasks/')
        pl = TASKS[TIDX[rid]]['place']
        return [pl['id']] if pl['kind'] == 'hall' else []
    if lay == 'k12-unit':
        return [rid]
    if lay == 'lesson':
        if rid not in LES:
            raise NPCBuildError(f'{where}: lesson {rid} not in lessons/')
        return [LES[rid]['hall']]
    raise NPCBuildError(f'{where}: unknown layer {lay}')


RANGER_KINDS = re.compile(r'park|refuge|preserve|spillway')
PILOT_KINDS = re.compile(r'port|ferry|bridge|lake|river|levee|refuge|spillway')
HOST_CAP = 4   # AUTHORED: at most this many station hosts per parish


def mentor_at(fam, present_halls):
    d = DIST[fam]
    first = [h for h in d['halls'] if h in present_halls and h in UIDX]
    rest = [h for h in d['halls'] if h not in first and h in UIDX]
    halls = (first + rest)[:3]
    lid = next((k for k, l in LES.items() if l['hall'] in first), None)
    if lid is None:
        lid = lesson_for_halls(d['halls'])
    lines = [quote('districts', f'districts.{fam}.tagline')]
    lines += [quote('unions', f'unions[{UIDX[h]}].focus') for h in halls]
    lines += [quote('lessons', f'lessons.{lid}.title'), quote('lessons', f'lessons.{lid}.why')]
    return {'family': fam, 'crew': halls[0], 'lines': lines,
            'points_to': {'kind': 'lesson', 'id': lid},
            'not_certification': quote('lessons', f'lessons.{lid}.limits')}


def k12_at(which, hall):
    k = k12(which)
    ui = next((i for i, u in enumerate(SCH['units']) if u['hall'] == hall), None)
    if ui is not None:     # the unit this station stands for, verbatim
        k['lines'][3] = quote('schools', f'units[{ui}].gate')
        k['crew'] = hall if hall in OPTS['crew'] else k['crew']
    return k


def host_task(tid):
    i = TIDX[tid]
    t = TASKS[i]
    lines = [quote('tasks', f'tasks[{i}].title')]
    if 'brief' in t and t['brief']:
        lines.append(quote('tasks', f'tasks[{i}].brief'))
    lines += [quote('tasks', 'honesty.practice'), quote('tasks', 'honesty.requires')]
    crew = t['place']['id'] if t['place']['id'] in OPTS['crew'] else AV['defaults']['crew']
    return {'crew': crew, 'lines': lines, 'points_to': {'kind': 'task', 'id': tid},
            'not_certification': quote('tasks', 'honesty.not_certification')}


def real_parish(fips, par, lay):
    """(specs, places) for one parish from PARISH + LAYERS. Placement rules in NPC_CONTRACT."""
    pi = [q['fips'] for q in lay['parishes']].index(fips)
    lp = lay['parishes'][pi]
    pp = par['parishes'][fips]
    places, specs = [], []
    by_station = {}
    for j, st in enumerate(lp['stations']):
        places.append({'id': st['id'], 'parish': fips, 'kind': 'station', 'status': 'LAYERS',
                       'layer': st['layer'], 'ref_id': st['ref']['id'],
                       'source': f'{LAYERS_REG}#parishes[{pi}].stations[{j}].id',
                       'world_m': st['world_m'], 'local_m': st['local_m']})
        by_station[st['id']] = st
    lm_xy = {}
    for li, l in enumerate(pp['landmarks']):
        lm_xy[l['name']] = (li, l)
    lms = []
    for k, l in enumerate(lp['landmarks']):
        if l['name'] not in lm_xy:
            raise NPCBuildError(f'{fips}: layers landmark {l["name"]} not in parishes.json')
        li, pl = lm_xy[l['name']]
        pid = f'{fips}-lm-{l["id"]}'
        places.append({'id': pid, 'parish': fips, 'kind': 'landmark', 'status': 'PARISH',
                       'name': l['name'], 'landmark_kind': l['kind'],
                       'source': f'{PARISH_REG}#parishes.{fips}.landmarks[{li}].name',
                       'world_m': pl['world_m'], 'local_m': pl['local_m']})
        lms.append((pid, l))
    # trade families present = families of every hall any station stands for
    fam_home, present = {}, set()
    for st in lp['stations']:
        for h in station_halls(st, f'{fips}:{st["id"]}'):
            if h not in HALL_FAMILY:
                raise NPCBuildError(f'{fips}: hall {h} is in no unions district')
            present.add(h)
            if HALL_FAMILY[h] not in fam_home and st['layer'] in ('trade-sim', 'task'):
                fam_home[HALL_FAMILY[h]] = st['id']
    for st in lp['stations']:     # a family seen only at K-12/lesson stations
        for h in station_halls(st, fips):
            fam_home.setdefault(HALL_FAMILY[h], st['id'])
    lesson_st = {st['ref']['id']: st['id'] for st in lp['stations'] if st['layer'] == 'lesson'}
    task_st = {st['ref']['id']: st['id'] for st in lp['stations'] if st['layer'] == 'task'}
    for fam in DIST:
        if fam in fam_home:
            m = mentor_at(fam, present)
            specs.append(('mentor', fam, m, fam_home[fam],
                          lesson_st[m['points_to']['id']] if m['points_to']['id'] in lesson_st
                          else fam_home[fam]))
    units = [st for st in lp['stations'] if st['layer'] == 'k12-unit']
    lessons_here = [st for st in lp['stations'] if st['layer'] == 'lesson']
    if not units:
        raise NPCBuildError(f'{fips}: no k12-unit station for the Cognition.X K-12 guides')
    for w in (0, 1):
        ust = units[min(w, len(units) - 1)]
        k = k12_at(w, ust['ref']['id'])
        go = ust['id']
        if lessons_here:     # "take me there" leads to a lesson station in this parish
            lst = lessons_here[min(w, len(lessons_here) - 1)]
            k['points_to'] = {'kind': 'lesson', 'id': lst['ref']['id']}
            go = lst['id']
        specs.append(('k12-guide', f'k12-{w}', k, ust['id'], go))
    for st in [st for st in lp['stations'] if st['layer'] == 'task'][:HOST_CAP]:
        specs.append(('host', st['ref']['id'], host_task(st['ref']['id']), st['id'], st['id']))
    rl = next((pid for pid, l in lms if RANGER_KINDS.search(l['kind'])), None)
    if rl is not None:
        specs.append(('ranger', 'ranger', ranger(), rl, rl))
    pl_ = next((pid for pid, l in lms if PILOT_KINDS.search(l['kind'])), None)
    if pl_ is not None:
        specs.append(('pilot', 'pilot', pilot(), pl_, pl_))
    return specs, places, {'families_present': sorted(fam_home),
                           'ranger': rl is not None, 'pilot': pl_ is not None}


def build():
    parishes, places_status, real = parishes_and_places()
    npcs, places = [], []
    word = 0
    for p in parishes:
        fips = p['fips']
        if real is None:
            pl = {k: f'{fips}:stub:{k}' for k in STUB_PLACES}
            for k in STUB_PLACES:
                places.append({'id': pl[k], 'parish': fips, 'kind': 'station'
                               if k.endswith('station') else 'landmark',
                               'status': 'STUB'})
            specs = []
            for fam in DIST:
                specs.append(('mentor', fam, mentor(fam), pl['trade-hub'], pl['trade-hub']))
            for w in (0, 1):
                specs.append(('k12-guide', f'k12-{w}', k12(w), pl['k12-commons'], pl['k12-commons']))
            specs.append(('ranger', 'ranger', ranger(), pl['marsh-edge'], pl['marsh-edge']))
            specs.append(('pilot', 'pilot', pilot(), pl['ferry-landing'], pl['ferry-landing']))
            specs.append(('host', 'sim', host('sim-scenario'), pl['sim-station'], pl['sim-station']))
            specs.append(('host', 'crib', host('crib-drill'), pl['crib-station'], pl['crib-station']))
        else:
            specs, pplaces, info = real_parish(fips, *real)
            places += pplaces
            p.update(info)
        lm_here = [q['id'] for q in places if q['parish'] == fips and q['kind'] == 'landmark']
        for i, (role, key, k, home, go) in enumerate(specs):
            lm = lm_here[i % len(lm_here)] if lm_here else go   # no landmark: the station again
            if not 3 <= len(k['lines']) <= 8:
                raise NPCBuildError(f'{role}:{key} has {len(k["lines"])} lines (3..8)')
            name = f'{ROLE_TITLE[role]} {NAME_WORDS[word % len(NAME_WORDS)]}'
            word += 1
            rec = {'id': f'npc-{fips}-{role}-{key}', 'parish': fips, 'role': role,
                   'name': name, 'name_provenance': 'AUTHORED',
                   'appearance': appearance(role, i, k['crew']),
                   'home': {'place': home, 'offset_index': i},
                   'guide_to': go,
                   'schedule': routine(role, home, go, lm),
                   'knowledge': k['lines'], 'points_to': k['points_to'],
                   'not_certification': k['not_certification']}
            if role == 'mentor':
                rec['family'] = k['family']
            if role == 'k12-guide':
                rec['layer'] = 'Cognition.X K-12'
                rec['bands'] = k['bands']
            npcs.append(rec)
    by_role = {}
    for n in npcs:
        by_role[n['role']] = by_role.get(n['role'], 0) + 1
    for n in npcs:   # points_to must resolve
        pt = n['points_to']
        if pt['kind'] == 'lesson' and pt['id'] not in LES:
            raise NPCBuildError(f'{n["id"]}: lesson {pt["id"]} missing')
        if pt['kind'] == 'task' and pt['id'] not in TIDX:
            raise NPCBuildError(f'{n["id"]}: task {pt["id"]} missing')
    sources = dict(SOURCES)
    sources['sims'] = 'sims/registry/sims.json'
    if real is not None:
        sources['parishes'] = PARISH_REG
        sources['layers'] = LAYERS_REG
    stamp_src = pathlib.Path(__file__).read_bytes() + b''.join(
        (ROOT / sources[k]).read_bytes() for k in sorted(sources))
    return {
        'pack': 'smartcitix-trade-craft-academy-npcs',
        'product': REG['unions']['product'],
        'source_stamp': hashlib.sha256(stamp_src).hexdigest()[:16],
        'sources': sources,
        'honesty': {
            'scripted': 'An NPC is a scripted figure, not an AI and not a person: '
                        'no model runs behind one, nothing is generated at view time, '
                        'and every line it says is a verbatim quote of the registry '
                        'field named beside it.',
            'not_a_person': 'Names are AUTHORED: a role title and one nature word. '
                            'No NPC represents a real worker, teacher, ranger, pilot, '
                            'union officer or public figure.',
            'play': 'Talking to an NPC is play: it certifies nothing, unlocks '
                    'nothing and enters no completion record.',
            'k12': 'The Cognition.X K-12 layer quotes only schools/registry/'
                   'schools.json and lessons/registry/lessons.json; K-12 districts '
                   'stay PROPOSED partners with no agreement.',
            'schedule': 'Schedules are AUTHORED game-clock hours on simulated time '
                        '(home, station, landmark, home), not real hours of any place.',
        },
        'places_status': places_status,
        'places_note': ('STUB: home places are placeholders in the Orleans (FIPS '
                        '22071) stub parish until the PARISH and LAYERS registries '
                        'exist; they are not real locations.'
                        if places_status == 'STUB' else
                        'Home places are LAYERS station ids (AUTHORED placement inside the '
                        'RECORDED parish outline) and PARISH landmarks (AUTHORED from public '
                        'record, not surveyed); coordinates are copied from those registries.'),
        'name_words': list(NAME_WORDS),
        'parishes': parishes,
        'places': places,
        'counts': {'npcs': len(npcs), 'parishes': len(parishes),
                   'by_role': dict(sorted(by_role.items())),
                   'lines': sum(len(n['knowledge']) for n in npcs)},
        'npcs': npcs,
    }


def main():
    try:
        reg = build()
    except (NPCBuildError, KeyError) as e:
        print(f'npcs/build.py: FAIL {type(e).__name__}: {e}', file=sys.stderr)
        sys.exit(1)
    out = HERE / 'registry' / 'npcs.json'
    text = json.dumps(reg, indent=1, ensure_ascii=False) + '\n'
    if '--check' in sys.argv:     # staleness only; writes nothing
        if not out.exists() or out.read_text() != text:
            print('npcs/build.py --check: FAIL npcs/registry/npcs.json is stale; '
                  'run python3 npcs/build.py', file=sys.stderr)
            sys.exit(1)
        print(f'npcs/build.py --check: up to date (stamp {reg["source_stamp"]})')
        return
    out.parent.mkdir(exist_ok=True)
    out.write_text(text)
    print(f'npcs: {reg["counts"]["npcs"]} NPCs in {reg["counts"]["parishes"]} '
          f'parish(es) {reg["counts"]["by_role"]}, {reg["counts"]["lines"]} quoted '
          f'lines, places {reg["places_status"]}, stamp {reg["source_stamp"]}')


if __name__ == '__main__':
    main()
