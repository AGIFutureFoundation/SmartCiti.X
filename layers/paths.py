"""Seven adventure paths and one side story per path per parish (wave 7).

Called by layers/build.py after layers.json is written; writes layers/registry/paths.json.
Nothing here is new content. Every step is either a layers.json station id, a quests id, or a verbatim
quote read from a registry already in the repo, with its source "<registry>#<json path>". Which quote lands
in which parish is a play layout (dealt in turn), not a fact. Paths are suggestions and never gate anything.
Side stories are play only (QUEST_CONTRACT): never a completion record. No step rewards a crash.
"""
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'layers' / 'registry' / 'paths.json'
LAYERS_PATH = 'layers/registry/layers.json'
RESPOND = 'respond/registry/respond.json'
RESTORE = 'restoration/registry/restoration.json'
SCHOOLS = 'schools/registry/schools.json'
ECON = 'economy/registry/economy.json'
# city-life steps (ECON_CONTRACT v1 events; econkit dispatches window "tc-econ" {detail:{name, lotId, ...}})
ECON_STEPS = {'trades': ('econ.shop-opened', 'shop', 'Open a shop on a shop lot in this parish (play coins, not money).'),
              'roam': ('econ.lot-rented', 'home', 'Rent a home lot in this parish (play coins, not money).')}

UN_DISCLAIMER = 'not affiliated with or endorsed by the United Nations'
PATHS = [
    # id, label, status, npc role, what the content is
    ('trades', 'Union trades', 'AVAILABLE', 'mentor', 'union training simulator seats and their simulated tasks'),
    ('k12', 'Cognition.X K-12', 'AVAILABLE', 'k12-guide',
     'the schools/ pack units and lessons; every district is a PROPOSED partner'),
    ('responders', 'First responders', 'AVAILABLE', 'responder', 'respond/ scenario frames, quoted'),
    ('un', 'UN training (PROPOSED module)', 'PROPOSED', 'humanitarian-trainer',
     'a PROPOSED module, ' + UN_DISCLAIMER + '; it quotes only respond/ items on humanitarian themes'),
    ('relief', 'Disaster relief', 'AVAILABLE', 'relief-coordinator', 'respond/ and restoration/ items, quoted'),
    ('teachers', 'Teachers', 'AVAILABLE', 'teacher', 'the schools/ pack classroom model, quoted'),
    ('roam', 'Just roam', 'AVAILABLE', 'host', 'landmark and parish finds; free play'),
]
# registry items each quote path draws from: (registry, json path of the text, json path of the title | None)
RESPONDER_PER_PARISH = 2
RELIEF_PER_PARISH = 3
UN_ITEMS = [  # humanitarian themes only: mass care, sheltering, access and functional needs, donated help
    ('competency', 'em.mass-care-coordination'), ('competency', 'em.access-functional-needs'),
    ('competency', 'em.volunteer-donations'), ('frame', 'resp.s.shelter-operations')]
RELIEF_ITEMS = [('competency', 'em.damage-assessment'), ('competency', 'em.recovery-transition'),
                ('frame', 'resp.s.riverine-flood'), ('track', 'habitat-grounds')]
AMBIENT_HOOKS = ['ambient.pet-found', 'ambient.litter-picked']   # AMBIENT fires TCPaths.hook(name)
FORBIDDEN_HOOK = re.compile(r'crash|collide|wreck|hit', re.I)
HONESTY = {
    'play': ('Paths and side stories are play. They are kept on this device only, certify nothing and never '
             'enter a completion record.'),
    'quotes': ('Every line a path or a side story shows from a pack is quoted verbatim from that pack\'s registry, '
               'with its source; which parish shows which quote is a play layout, not a fact.'),
    'un': ('"UN training" is a PROPOSED module of this game. It is ' + UN_DISCLAIMER + '. It uses no UN emblem '
           'and no UN course. It shows only respond/ items whose own text is about humanitarian themes.'),
    'k12': 'Cognition.X K-12 districts stay PROPOSED partners: no district has reviewed or agreed.',
    'lessons': 'Lessons are unverified general practice, exactly as the lessons pack states.',
    'crash': 'No path or side story rewards crashing a vehicle.',
    'econ': ('City-life steps use PLAY COINS only, never money; every lot is an AUTHORED game lot of the economy '
             'pack, not a real property, address, listing or business.'),
}


def fail(msg):
    raise SystemExit(f'layers/paths: {msg}')


def need(d, k, where):
    if isinstance(d, dict):
        if k not in d:
            fail(f'{where} has no "{k}"')
        return d[k]
    if isinstance(d, list) and isinstance(k, int):
        if not 0 <= k < len(d):
            fail(f'{where} has no [{k}]')
        return d[k]
    fail(f'{where} is not a container for {k!r}')


def load(rel):
    p = ROOT / rel
    if not p.exists():
        fail(f'missing source {rel}')
    return json.loads(p.read_text(encoding='utf-8'))


def walk(doc, path, rel):
    """Walk 'a[3].b' in doc; the same walker the test uses. Fails by name."""
    cur = doc
    for part in re.findall(r'[^.\[\]]+|\[\d+\]', path):
        cur = need(cur, int(part[1:-1]) if part.startswith('[') else part, f'{rel}#{path}')
    return cur


def index_of(lst, key, val, rel, where):
    for i, e in enumerate(lst):
        if need(e, key, f'{rel}#{where}[{i}]') == val:
            return i
    fail(f'{rel}#{where}: no entry with {key} {val!r} (missing registry id)')


def quote(regs, kind, rid):
    """-> {registry, id, source, title, quote}; every text read from the registry by json path."""
    if kind == 'frame':
        rel, lst = RESPOND, 'scenario_frames'
        i = index_of(need(regs[rel], lst, rel), 'id', rid, rel, lst)
        tp, qp = f'{lst}[{i}].title', f'{lst}[{i}].situation'
    elif kind == 'competency':
        rel, lst = RESPOND, 'competencies'
        i = index_of(need(regs[rel], lst, rel), 'id', rid, rel, lst)
        tp, qp = f'{lst}[{i}].title', f'{lst}[{i}].what_it_is'
    elif kind == 'track':
        rel, lst = RESTORE, 'tracks'
        i = index_of(need(regs[rel], lst, rel), 'id', rid, rel, lst)
        tp, qp = f'{lst}[{i}].title', f'{lst}[{i}].what'
    elif kind == 'stage':
        rel, lst = SCHOOLS, 'model.stages'
        i = index_of(walk(regs[rel], lst, rel), 'stage', rid, rel, lst)
        tp, qp = f'{lst}[{i}].title', f'{lst}[{i}].what'
    elif kind == 'loop':
        rel = SCHOOLS
        tp, qp = 'model.name', 'model.loop'
    else:
        fail(f'unknown item kind {kind!r}')
    title, text = walk(regs[rel], tp, rel), walk(regs[rel], qp, rel)
    if not isinstance(text, str) or not text.strip() or not isinstance(title, str):
        fail(f'{rel}#{qp}: not a quotable string')
    return {'registry': rel, 'ref_id': rid, 'item_kind': kind, 'source': f'{rel}#{qp}', 'title_source': f'{rel}#{tp}',
            'title': title, 'quote': text}


def build(layers):
    regs = {r: load(r) for r in (RESPOND, RESTORE, SCHOOLS, ECON)}
    econ_parishes = need(regs[ECON], 'parishes', ECON)
    parishes = need(layers, 'parishes', LAYERS_PATH)
    frames = [need(f, 'id', RESPOND) for f in need(regs[RESPOND], 'scenario_frames', RESPOND)]
    if not frames:
        fail(f'{RESPOND} has no scenario_frames')
    stages = [need(s, 'stage', SCHOOLS) for s in walk(regs[SCHOOLS], 'model.stages', SCHOOLS)]
    quest_ids_known = set()
    out, counts = [], {pid: 0 for pid, *_ in PATHS}
    for pi, p in enumerate(parishes):
        fips = need(p, 'fips', LAYERS_PATH)
        where = f'{LAYERS_PATH} parish {fips}'
        stations = need(p, 'stations', where)
        if not stations:
            fail(f'{where} has no stations to anchor path steps')
        st_by_id = {need(s, 'id', where): s for s in stations}
        lpaths = {need(x, 'id', where): need(x, 'steps', where) for x in need(p, 'paths', where)}
        for k in ('trade', 'k12', 'explorer'):
            need(lpaths, k, where)

        def anchor(n):
            s = stations[n % len(stations)]
            return {'station': s['id'], 'world_m': need(s, 'world_m', where), 'near': need(s, 'near', where)}

        items = {
            'responders': [('frame', frames[(pi * RESPONDER_PER_PARISH + k) % len(frames)])
                           for k in range(RESPONDER_PER_PARISH)],
            'un': list(UN_ITEMS),
            'relief': [RELIEF_ITEMS[(pi * RELIEF_PER_PARISH + k) % len(RELIEF_ITEMS)] for k in range(RELIEF_PER_PARISH)],
            'teachers': [('loop', 'model')] + [('stage', s) for s in stages],
        }
        ppaths, stories = [], []
        for n_path, (pid, label, status, role, what) in enumerate(PATHS):
            if pid in ('trades', 'k12', 'roam'):
                src = {'trades': 'trade', 'k12': 'k12', 'roam': 'explorer'}[pid]
                steps = []
                for sid in lpaths[src]:
                    if pid == 'roam':
                        steps.append({'kind': 'quest', 'id': sid})
                    else:
                        if sid not in st_by_id:
                            fail(f'{where}: path {src} step {sid!r} is not a station (missing id)')
                        steps.append({'kind': 'station', 'id': sid, 'title': need(st_by_id[sid], 'title', sid)})
            else:
                steps = []
                for k, (kind, rid) in enumerate(items[pid]):
                    q = quote(regs, kind, rid)
                    steps.append({'kind': 'quote', 'id': f'pt-{fips}-{pid}-{k + 1}', **q, **anchor(pi + k + n_path)})
            counts[pid] += len(steps)
            ppaths.append({'id': pid, 'label': label, 'status': status, 'npc_role': role, 'what': what,
                           'gated': False, 'steps': steps})
            # side story: meet the path's NPC -> visit a spot -> do/read -> return to the NPC
            sid_base = f'story-{fips}-{pid}'
            if pid == 'roam':
                first = None   # free play: no walk to a station
                middle = [{'do': 'find', 'hook': h, 'text': {'ambient.pet-found': 'Find a pet or an animal wandering nearby.',
                                                             'ambient.litter-picked': 'Pick up a piece of litter.'}[h]}
                          for h in AMBIENT_HOOKS]
            elif pid in ('trades', 'k12'):
                s0 = steps[0]['id']
                first = {'station': s0, 'world_m': need(st_by_id[s0], 'world_m', s0), 'near': need(st_by_id[s0], 'near', s0)}
                middle = [{'do': 'open-station', 'station': s0, 'text': 'Open this station: ' + steps[0]['title']}]
            else:
                q = steps[0]
                first = {'station': q['station'], 'world_m': q['world_m'], 'near': q['near']}
                middle = [{'do': 'read', 'item': q['id'], 'text': 'Read: ' + q['title'], 'source': q['source']}]
            if pid in ECON_STEPS:
                hook, use, text = ECON_STEPS[pid]
                lots = [need(l, 'id', f'{ECON}#{fips}') for l in need(need(econ_parishes, fips, ECON), 'lots', f'{ECON}#{fips}')
                        if use in need(l, 'allowed', f'{ECON}#{fips}')]
                if not lots:
                    fail(f'{ECON}: parish {fips} has no {use} lot for the {pid} city-life step')
                middle = middle + [{'do': 'econ', 'hook': hook, 'lots': lots, 'text': text}]
            visit = [] if first is None else [{'do': 'visit', 'station': first['station'], 'world_m': first['world_m'],
                                               'near': first['near'], 'text': 'Walk to the marked spot.'}]
            chain = ([{'do': 'talk', 'npc_role': role, 'text': f'Meet the {role.replace("-", " ")} for this path.'}] + visit + middle +
                     [{'do': 'talk', 'npc_role': role, 'text': 'Go back and tell them what you found.'}])
            for n, st in enumerate(chain):
                st['n'] = n + 1
                st['quest'] = f'treasure-{sid_base}-{n + 1}'
                quest_ids_known.add(st['quest'])
            stories.append({'id': sid_base, 'path': pid, 'parish': fips, 'npc_role': role,
                            'quest': f'side-{sid_base}', 'title': f'{label}: a side story', 'steps': chain,
                            'provenance': 'AUTHORED'})
        out.append({'fips': fips, 'name': need(p, 'name', where), 'paths': ppaths, 'stories': stories})
    for p in out:
        for s in p['stories']:
            for st in s['steps']:
                if 'hook' in st and FORBIDDEN_HOOK.search(st['hook']):
                    fail(f'{s["id"]}: hook {st["hook"]!r} would reward a crash')
    return out, counts


def run(layers_doc, layers_text, check):
    parishes, counts = build(layers_doc)
    read = [LAYERS_PATH, RESPOND, RESTORE, SCHOOLS, ECON, 'layers/paths.py']
    srcs = {}
    for r in read:
        b = layers_text.encode() if r == LAYERS_PATH else (ROOT / r).read_bytes()
        srcs[r] = hashlib.sha256(b).hexdigest()[:16]
    doc = {'pack': 'paths', 'series': 'SmartCiti.X Powered by AGI Corp',
           'source_stamp': hashlib.sha256(''.join(f'{k}:{v}\n' for k, v in srcs.items()).encode()).hexdigest()[:16],
           'sources': srcs, 'honesty': HONESTY, 'un_disclaimer': UN_DISCLAIMER, 'ambient_hooks': AMBIENT_HOOKS,
           'econ_hooks': sorted(h for h, _, _ in ECON_STEPS.values()),
           'path_ids': [p[0] for p in PATHS],
           'counts': {'parishes': len(parishes), 'steps_by_path': counts,
                      'stories': sum(len(p['stories']) for p in parishes)},
           'parishes': parishes}
    text = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
    if check:
        if not OUT.exists() or OUT.read_text(encoding='utf-8') != text:
            sys.exit(f'{OUT.relative_to(ROOT)} is stale: run python3 layers/build.py')
        print(f'{OUT.relative_to(ROOT)} is current')
        return
    OUT.write_text(text, encoding='utf-8')
    print(f'wrote {OUT.relative_to(ROOT)}: {doc["counts"]}')
