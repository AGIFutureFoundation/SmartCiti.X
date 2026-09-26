#!/usr/bin/env python3
"""Work sites: a scenario where a crew drawn from at least two unions works one
job with hand-offs, and whose completion is checkable, offline, from the
members' own exported records.

A work site is an AUTHORED declaration under worksites/authored/<id>.json: a
title, the job in one sentence, a place (a campus, a walkable restoration site
or a custom space), a crew from agents/registry/crews.json with each role
assigned to a real union, the crew's own hand-off sequence with the evidence
that proves each end of every hand-off, the crew's stop-work condition
verbatim, and the compliance gates. Everything else in
worksites/registry/worksites.json is DERIVED here from the registry that owns
each fact, and every id is resolved by name or the build fails naming the
file and the field (fail closed):

  - the place resolves in campuses.json, restoration.json (walkable only) or
    spaces.json; the PPE gate is never typed: a custom space has finishes, so
    its PPE is re-derived from surfaces/registry/finishes.json (strand base
    conditions plus the hazard conditions the space's finishes stand for) and
    held equal to what spaces/ derived; a campus or a restoration site has no
    finishes in this bundle and the registry says so;
  - the crew resolves, every role is assigned, at least two distinct unions
    are named, and a role's union is one whose hall the crew reaches (read
    from the crew's seat) or the declaration says why not;
  - the hand-offs are the crew's own run, in order, verbatim by/to; the
    stop-work line is the crew's, verbatim;
  - each hand-off names from-evidence (the act of the role handing off) and
    to-evidence (the act of the role receiving): a sim scenario passed, a
    walkaround point checked, a crew exchange of that role and topic, or a
    station done - every id resolves, a crew exchange names the role it
    evidences, and a seat run or walkaround is on a seat whose halls include
    that role's union;
  - whether each evidence is of a kind the training registry records is READ
    from training.json#episode_kinds: an evidence whose reference fields no
    episode kind carries is marked unverifiable with why, never accepted.

The fixture under worksites/fixture/ is written here too, deterministically:
one scripted crew for one site (labelled, not learners) and mutants that each
fail by name in worksites/verify.mjs. No signing happens here: python3 has no
keccak and no secp256k1, and the throwaway-key signing lives in
completion/test.mjs, which worksites/test.mjs imports.

HONESTY. These are authored scenarios. No two learners have ever been on a
site together in this bundle: there is no multi-user session here, and a crew
completion is N separate records read side by side. Nothing here is a
certification, and no duration or price is stated.
"""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
AUTHORED = HERE / 'authored'
FIXTURE = HERE / 'fixture'
OUT = HERE / 'registry' / 'worksites.json'


def load(rel):
    return json.load(open(ROOT / rel))


def fail(msg):
    print('FAIL ' + msg, file=sys.stderr)
    sys.exit(1)


def need(obj, key, who):
    if not isinstance(obj, dict) or key not in obj:
        fail(f'{who} lacks {json.dumps(key)}')
    return obj[key]


manifest = load('pack/manifest.json')
crews_reg = load('agents/registry/crews.json')
sims_reg = load('sims/registry/sims.json')
lessons_reg = load('lessons/registry/lessons.json')
unions_reg = load('unions/registry/unions.json')
campuses_reg = load('unions/registry/campuses.json')
halls_reg = load('pack/registry/halls.json')
restoration_reg = load('restoration/registry/restoration.json')
spaces_reg = load('spaces/registry/spaces.json')
training_reg = load('training/registry/training.json')
finishes_reg = load('surfaces/registry/finishes.json')
stations_reg = load('stations/registry/stations.json')
completion_reg = load('completion/registry/completion.json')
contrib_reg = load('contrib/registry/contrib.json')
completion_good = load('completion/fixture/good.json')
contrib_good = load('contrib/fixture/good.json')

CREWS = need(crews_reg, 'crews', 'crews.json')
SIMS = need(sims_reg, 'sims', 'sims.json')
LESSONS = need(lessons_reg, 'lessons', 'lessons.json')
UNIONS = {need(u, 'slug', 'union'): u for u in need(unions_reg, 'unions', 'unions.json')}
HALLS = {need(h, 'slug', 'hall'): h for h in need(halls_reg, 'halls', 'halls.json')}
CAMPUSES = need(campuses_reg, 'campuses', 'campuses.json')
SITES = {need(s, 'id', 'restoration site'): s for s in need(restoration_reg, 'sites', 'restoration.json')}
SPACES = {need(s, 'id', 'space'): s for s in need(spaces_reg, 'spaces', 'spaces.json')}
STATIONS = {need(s, 'station_id', 'station'): s for s in need(stations_reg, 'stations', 'stations.json')}
EPISODE_KINDS = need(training_reg, 'episode_kinds', 'training.json')
PRODUCT = need(unions_reg, 'product', 'unions.json')
PACK_VERSION = need(manifest, 'pack_version', 'manifest.json') if 'pack_version' in manifest else need(crews_reg, 'pack_version', 'crews.json')

if set(UNIONS) != set(HALLS):
    fail('unions.json slugs and halls.json slugs differ; a union is its hall here')

# what each evidence kind must name, and which fields would have to be on an
# episode for a record to carry it. The training registry is the only judge
# of whether such an episode exists.
EVIDENCE_SHAPES = {
    'sim': {'refs': ['sim', 'scenario'], 'episode_kind': 'sim', 'needs_fields': ['sim', 'scenario', 'outcome']},
    'walkaround': {'refs': ['sim', 'point'], 'episode_kind': 'walkaround', 'needs_fields': ['sim', 'point']},
    'crew': {'refs': ['crew', 'role', 'topic'], 'episode_kind': 'crew', 'needs_fields': ['crew', 'role', 'topic', 'hall']},
    'station': {'refs': ['station'], 'episode_kind': None, 'needs_fields': ['station']},
}
PLACE_KINDS = ('campus', 'restoration-site', 'space')


def walkaround_ids(sim_id):
    return [need(w, 'id', f'sims.json#{sim_id}.walkaround') for w in need(SIMS[sim_id], 'walkaround', f'sims.json#{sim_id}')]


def scenario_ids(sim_id):
    return [need(s, 'id', f'sims.json#{sim_id}.scenarios') for s in need(SIMS[sim_id], 'scenarios', f'sims.json#{sim_id}')]


def resolve_evidence(ev, who, role, role_union, crew_id):
    """Every id by name; returns the evidence with its verifiability derived."""
    kind = need(ev, 'kind', who)
    if kind not in EVIDENCE_SHAPES:
        fail(f'{who}: evidence kind {json.dumps(kind)} is not one of {sorted(EVIDENCE_SHAPES)}')
    shape = EVIDENCE_SHAPES[kind]
    for f in shape['refs']:
        need(ev, f, who)
    extra = sorted(set(ev) - set(shape['refs']) - {'kind'})
    if extra:
        fail(f'{who}: evidence carries {extra}, which a {kind} evidence does not name')
    out = {'kind': kind}
    for f in shape['refs']:
        out[f] = ev[f]
    if kind == 'sim':
        if ev['sim'] not in SIMS:
            fail(f'{who}: sim {ev["sim"]} is not in sims.json')
        if ev['scenario'] not in scenario_ids(ev['sim']):
            fail(f'{who}: scenario {ev["scenario"]} is not a scenario of seat {ev["sim"]}')
        if role_union not in SIMS[ev['sim']]['halls']:
            fail(f'{who}: seat {ev["sim"]} binds no {role_union} hall, so the {role} ({role_union}) cannot have run it')
        out['seat_halls'] = list(SIMS[ev['sim']]['halls'])
        out['passes_when'] = [{'axis': need(r, 'axis', 'rubric'), 'pass': need(r, 'pass', 'rubric')}
                              for r in need(SIMS[ev['sim']], 'rubric', f'sims.json#{ev["sim"]}')]
    elif kind == 'walkaround':
        if ev['sim'] not in SIMS:
            fail(f'{who}: sim {ev["sim"]} is not in sims.json')
        if ev['point'] not in walkaround_ids(ev['sim']):
            fail(f'{who}: walkaround point {ev["point"]} is not a point of seat {ev["sim"]}')
        if role_union not in SIMS[ev['sim']]['halls']:
            fail(f'{who}: seat {ev["sim"]} binds no {role_union} hall, so the {role} ({role_union}) cannot have walked it')
        pt = [w for w in SIMS[ev['sim']]['walkaround'] if w['id'] == ev['point']][0]
        out['check'] = need(pt, 'check', 'walkaround point')
    elif kind == 'crew':
        if ev['crew'] != crew_id:
            fail(f'{who}: crew evidence names crew {ev["crew"]}, not this site\'s {crew_id}')
        if ev['role'] != role:
            fail(f'{who}: crew evidence names role {ev["role"]}, but it must evidence the {role}')
        topics = [need(t, 'id', 'topic') for t in CREWS[crew_id]['roles'][role]['topics']]
        if ev['topic'] not in topics:
            fail(f'{who}: topic {ev["topic"]} is not a topic of {crew_id}:{role} ({topics})')
        out['ask'] = [t for t in CREWS[crew_id]['roles'][role]['topics'] if t['id'] == ev['topic']][0]['ask']
    elif kind == 'station':
        if ev['station'] not in STATIONS:
            fail(f'{who}: station {ev["station"]} is not in stations.json')
        out['station_name'] = STATIONS[ev['station']]['name']
        out['station_hall'] = STATIONS[ev['station']]['hall']
    # verifiability: READ from training.json - an evidence is verifiable only
    # when an episode kind records every field it references
    ek = shape['episode_kind']
    if ek is None or ek not in EPISODE_KINDS:
        out['verifiable'] = False
        out['why_unverifiable'] = (f'no episode kind in training.json#episode_kinds records a {kind}; '
                                   f'a tc-completion/1 record lists a station as a device-local mark with no time, '
                                   f'so presence can be read but the hand-off order cannot')
    else:
        fields = need(EPISODE_KINDS[ek], 'fields', f'training.json#episode_kinds.{ek}')
        missing = [f for f in shape['needs_fields'] if f not in fields]
        if missing:
            out['verifiable'] = False
            out['why_unverifiable'] = f'the {ek} episode kind records no {missing}'
        else:
            out['verifiable'] = True
            out['episode_kind'] = ek
            out['episode_fields'] = list(fields)
    return out


def derive_ppe(place_kind, place_id):
    if place_kind != 'space':
        return {'required': None, 'derived_from': None,
                'why_none': f'a {place_kind} declares no finishes in this bundle, so surfaces/ derives no PPE for it; '
                            'nothing is typed in its place'}
    sp = SPACES[place_id]
    strand = need(sp, 'strand', f'spaces.json#{place_id}')
    base = list(need(need(finishes_reg, 'base_conditions', 'finishes.json'), strand, f'finishes.json#base_conditions.{strand}')['ppe'])
    hazards = sorted({need(h, 'hazard', 'space hazard') for h in need(sp, 'hazards', f'spaces.json#{place_id}')})
    hz_ppe = []
    for h in hazards:
        hz_ppe += need(need(finishes_reg, 'hazard_conditions', 'finishes.json'), h, f'finishes.json#hazard_conditions.{h}')['ppe']
    required = sorted(set(base) | set(hz_ppe))
    spaces_says = sorted(need(need(sp, 'ppe', f'spaces.json#{place_id}'), 'required', f'spaces.json#{place_id}.ppe'))
    if required != spaces_says:
        fail(f'PPE re-derived for space {place_id} ({required}) is not what spaces/ derived ({spaces_says}); rebuild spaces/')
    return {'required': required,
            'derived_from': {'strand': strand, 'base_conditions': base, 'hazards': hazards,
                             'finishes': {'floor': sp['floor']['id'], 'wall': sp['wall']['id']},
                             'rule': 'surfaces base_conditions[strand].ppe + hazard_conditions[h].ppe for each hazard the space\'s finishes stand for'},
            'why_none': None}


def resolve_place(place, who):
    kind = need(place, 'kind', who)
    pid = need(place, 'id', who)
    if kind not in PLACE_KINDS:
        fail(f'{who}: place kind {json.dumps(kind)} is not one of {PLACE_KINDS}')
    if kind == 'campus':
        if pid not in CAMPUSES:
            fail(f'{who}: campus {pid} is not in campuses.json')
        c = CAMPUSES[pid]
        return {'kind': kind, 'id': pid, 'name': c['name'], 'campus': pid, 'halls': list(c['halls']),
                'plan': {'kind': 'campus-tile', 'districts': list(c['districts'])}, 'href': None}
    if kind == 'restoration-site':
        if pid not in SITES:
            fail(f'{who}: restoration site {pid} is not in restoration.json')
        s = SITES[pid]
        if s['walkable'] is not True:
            fail(f'{who}: restoration site {pid} is not walkable')
        return {'kind': kind, 'id': pid, 'name': s['name'], 'campus': s['campus'], 'trade_needs': list(s['trade_needs']),
                'ground': s['ground'], 'plan': {'kind': 'site-tile', 'habitat': s['habitat']}, 'href': None}
    if pid not in SPACES:
        fail(f'{who}: space {pid} is not in spaces.json')
    sp = SPACES[pid]
    return {'kind': kind, 'id': pid, 'name': sp['title'], 'campus': None,
            'plan': {'kind': 'space-plan', 'footprint_m': dict(sp['footprint_m']),
                     'items': [{'i': it['i'], 'id': it['id'], 'kind': it['kind'], 'x': it['x'], 'y': it['y'], 'rect': list(it['rect'])} for it in sp['items']]},
            'href': 'trade_craft_spaces.html#space-' + pid}


def build_site(path):
    a = json.load(open(path))
    who = f'worksites/authored/{path.name}'
    sid = need(a, 'id', who)
    if sid != path.stem:
        fail(f'{who}: id {sid} is not the file name')
    for k in ('title', 'job', 'place', 'crew', 'roles', 'handoffs', 'stop_work', 'gates'):
        need(a, k, who)
    extra = sorted(set(a) - {'id', 'title', 'job', 'place', 'crew', 'roles', 'handoffs', 'stop_work', 'gates'})
    if extra:
        fail(f'{who}: unknown fields {extra}')
    place = resolve_place(a['place'], who + '#place')
    crew_id = a['crew']
    if crew_id not in CREWS:
        fail(f'{who}: crew {crew_id} is not in crews.json')
    crew = CREWS[crew_id]
    crew_halls = list(need(crew, 'halls', f'crews.json#{crew_id}'))
    seat = need(crew, 'seat', f'crews.json#{crew_id}')
    # roles -> unions
    roles = {}
    if set(a['roles']) != set(crew['roles']):
        fail(f'{who}#roles: names {sorted(a["roles"])}, the crew has {sorted(crew["roles"])}')
    for rid, decl in a['roles'].items():
        union = need(decl, 'union', f'{who}#roles.{rid}')
        if union not in UNIONS:
            fail(f'{who}#roles.{rid}: union {union} is not in unions.json')
        reach = union in crew_halls
        if not reach and 'why_not_reached' not in decl:
            fail(f'{who}#roles.{rid}: union {union} is not a hall the {crew_id} reaches ({crew_halls}) and no why_not_reached is given')
        if reach and 'why_not_reached' in decl:
            fail(f'{who}#roles.{rid}: union {union} is reached, so why_not_reached is a claim with nothing to explain')
        r = crew['roles'][rid]
        roles[rid] = {'name': r['name'], 'job': r['job'], 'standing': r['standing'], 'stops': r['stops'],
                      'glyph': r['glyph'], 'post': dict(r['post']), 'union': union, 'union_name': UNIONS[union]['name'],
                      'hall_reached_by_crew': reach,
                      'why_not_reached': decl['why_not_reached'] if not reach else None}
    unions = sorted({r['union'] for r in roles.values()})
    if len(unions) < 2:
        fail(f'{who}: only {unions} - a work site needs at least two distinct unions')
    # handoffs: the crew's run, verbatim, in order
    run = need(crew, 'run', f'crews.json#{crew_id}')
    if len(a['handoffs']) != len(run):
        fail(f'{who}#handoffs: {len(a["handoffs"])} hand-offs, the crew runs {len(run)}')
    handoffs = []
    for i, (h, step) in enumerate(zip(a['handoffs'], run)):
        w = f'{who}#handoffs[{i}]'
        if need(h, 'by', w) != step['by'] or need(h, 'to', w) != step['to']:
            fail(f'{w}: {h["by"]}->{h["to"]} is not the crew\'s step {i + 1} {step["by"]}->{step["to"]}')
        fe = resolve_evidence(need(h, 'from_evidence', w), w + '.from_evidence', h['by'], roles[h['by']]['union'], crew_id)
        te = resolve_evidence(need(h, 'to_evidence', w), w + '.to_evidence', h['to'], roles[h['to']]['union'], crew_id)
        verifiable = fe['verifiable'] and te['verifiable']
        why = None
        if not verifiable:
            why = '; '.join(f'{side}: {e["why_unverifiable"]}' for side, e in (('from', fe), ('to', te)) if not e['verifiable'])
        handoffs.append({'n': i + 1, 'by': h['by'], 'to': h['to'], 'step': step['step'],
                         'from_evidence': fe, 'to_evidence': te, 'verifiable': verifiable, 'why_unverifiable': why})
    if a['stop_work'] != crew['stop_work']:
        fail(f'{who}#stop_work is not the crew\'s stop_work verbatim')
    # gates
    g = a['gates']
    if need(g, 'ppe', who + '#gates') != 'derived':
        fail(f'{who}#gates.ppe must be the word "derived": PPE is never typed')
    wa = []
    for j, pt in enumerate(need(g, 'walkaround_before_first_move', who + '#gates')):
        w = f'{who}#gates.walkaround_before_first_move[{j}]'
        s = need(pt, 'sim', w)
        if s not in SIMS:
            fail(f'{w}: sim {s} is not in sims.json')
        if need(pt, 'point', w) not in walkaround_ids(s):
            fail(f'{w}: point {pt["point"]} is not a point of seat {s}')
        p = [x for x in SIMS[s]['walkaround'] if x['id'] == pt['point']][0]
        wa.append({'sim': s, 'point': pt['point'], 'label': p['point'], 'check': p['check'], 'on_fault': p['on_fault']})
    extra = sorted(set(g) - {'ppe', 'walkaround_before_first_move'})
    if extra:
        fail(f'{who}#gates: unknown gates {extra}')
    ppe = derive_ppe(place['kind'], place['id'])
    # derived per site
    ev_kinds = {}
    seats = set()
    for h in handoffs:
        for side in ('from_evidence', 'to_evidence'):
            e = h[side]
            rid = h['by'] if side == 'from_evidence' else h['to']
            ev_kinds.setdefault(rid, set()).add(e['kind'])
            if 'sim' in e:
                seats.add(e['sim'])
    for p in wa:
        seats.add(p['sim'])
    seats.add(seat)
    halls = sorted(set(crew_halls) | set(unions))
    lessons = sorted(lid for lid, l in LESSONS.items()
                     if any(st['kind'] == 'crew' and st['crew'] == crew_id for st in l['steps']))
    n_ver = sum(1 for h in handoffs if h['verifiable'])
    return {
        'id': sid, 'title': a['title'], 'job': a['job'], 'place': place,
        'crew': {'id': crew_id, 'name': crew['name'], 'seat': seat, 'muster': crew['muster'], 'halls': crew_halls},
        'roles': roles, 'handoffs': handoffs, 'stop_work': a['stop_work'],
        'gates': {'ppe': ppe, 'walkaround_before_first_move': wa},
        'derived': {
            'unions': unions, 'halls': halls, 'seats': sorted(seats),
            'evidence_kinds_by_role': {r: sorted(k) for r, k in sorted(ev_kinds.items())},
            'handoffs': len(handoffs), 'handoffs_verifiable': n_ver, 'handoffs_unverifiable': len(handoffs) - n_ver,
            'roles': len(roles), 'lessons_with_this_crew': lessons,
        },
    }


# ---------------------------------------------------------------- fixture
def canonical(v):
    return json.dumps(v, separators=(',', ':'), sort_keys=True, ensure_ascii=False)


def digest_body(rec, who_key):
    body = {k: v for k, v in rec.items() if k != 'digest'}
    if isinstance(body[who_key], dict) and 'signature' in body[who_key]:
        body[who_key] = dict(body[who_key], signature=None)
    return body


def stamp_digest(rec, who_key):
    rec['digest'] = {'alg': 'SHA-256', 'over': need(need(completion_reg if who_key == 'identity' else contrib_reg, 'digest', 'reg'), 'over', 'digest'),
                     'hex': hashlib.sha256(canonical(digest_body(rec, who_key)).encode('utf-8')).hexdigest()}
    return rec


T0 = '2026-09-26T03:00:'
FIX_SITE = 'ti-tower-steel-pick'
FIX_CAMPUS = 'treasure-island'
LABEL = 'fixture crew {} - not a learner'
CONTROLS = {s: [c['action'] for c in SIMS[s]['controls']] for s in SIMS}


def ep_crew(sec, hall, role, topic):
    return {'t': f'{T0}{sec:02d}.000Z', 'kind': 'crew', 'campus': FIX_CAMPUS, 'hall': hall, 'crew': 'crane-lift-crew',
            'role': role, 'topic': topic, 'answer_kind': 'say'}


def ep_sim(sec, hall, sim, scenario, passed=True):
    rows = [{'axis': r['axis'], 'value': 0, 'ok': True} for r in SIMS[sim]['rubric']]
    return {'t': f'{T0}{sec:02d}.000Z', 'kind': 'sim', 'campus': FIX_CAMPUS, 'hall': hall, 'sim': sim, 'scenario': scenario,
            'controls': CONTROLS[sim], 'actor': 'human', 'outcome': {'passed': passed, 'rows': rows}}


def ep_walk(sec, hall, sim, point):
    return {'t': f'{T0}{sec:02d}.000Z', 'kind': 'walkaround', 'campus': FIX_CAMPUS, 'hall': hall, 'sim': sim, 'point': point}


def package(label, episodes):
    by_kind = {}
    sims = set()
    for e in episodes:
        by_kind[e['kind']] = (by_kind[e['kind']] if e['kind'] in by_kind else 0) + 1
        if 'sim' in e:
            sims.add(e['sim'])
    rec = {
        'record': need(contrib_reg, 'record_tag', 'contrib.json'), 'product': PRODUCT, 'pack_version': PACK_VERSION,
        'exported_at': '2026-09-26T00:00:00Z',
        'contributor': {'claimed': label, 'attested_by': 'this device only', 'signature': None},
        'consent': dict(contrib_good['consent']),
        'dataset': {'episodes': episodes, 'traces_attached': 0,
                    'episode_counts_by_kind': {k: by_kind[k] for k in sorted(by_kind)},
                    'sims_covered': sorted(sims),
                    'fields_by_kind': {k: list(EPISODE_KINDS[k]['fields']) for k in EPISODE_KINDS}},
        'honesty': dict(contrib_good['honesty']),
    }
    return stamp_digest(rec, 'contributor')


def completion(label, sims):
    rec = {
        'record': need(completion_reg, 'record_tag', 'completion.json'), 'product': PRODUCT, 'pack_version': PACK_VERSION,
        'exported_at': '2026-09-26T00:00:00Z',
        'identity': {'claimed': label, 'attested_by': 'this device only', 'signature': None},
        'lessons': [], 'sims': {s: {'passed': True, 'score': 2, 'attempts': 1} for s in sims}, 'tools': {}, 'stations': [],
        'honesty': dict(completion_good['honesty']),
    }
    return stamp_digest(rec, 'identity')


def good_records():
    A, B, C, D = (LABEL.format(x) for x in 'ABCD')
    return {
        'member-a-lift-director.json': package(A, [ep_crew(0, 'ironworkers', 'lift-director', 'plan'), ep_crew(9, 'ironworkers', 'lift-director', 'change')]),
        'member-b-rigger.json': package(B, [ep_sim(1, 'riggers', 'load-chart', 'bay-pick-list'), ep_crew(7, 'riggers', 'rigger', 'weight')]),
        'member-b-rigger-completion.json': completion(B, ['load-chart']),
        'member-c-signalperson.json': package(C, [ep_walk(2, 'riggers', 'rigging-signals', 'sightline'), ep_sim(3, 'riggers', 'rigging-signals', 'bay-first-card'),
                                                  ep_walk(5, 'riggers', 'rigging-signals', 'path')]),
        'member-d-crane-operator.json': package(D, [ep_sim(4, 'crane-ops', 'crane-lift', 'bay-steel')]),
    }


def mutants():
    A, B, C, D = (LABEL.format(x) for x in 'ABCD')
    out = {}
    g = good_records()
    m = dict(g); del m['member-d-crane-operator.json']
    out['role-uncovered'] = (m, 'role crane-operator')
    m = dict(g); m['member-d-crane-operator.json'] = package(C, [ep_sim(4, 'crane-ops', 'crane-lift', 'bay-steel')])
    out['two-roles-one-identity'] = (m, 'one identity cannot hold two roles')
    m = dict(g); m['member-d-crane-operator.json'] = package(D, [ep_sim(2, 'crane-ops', 'crane-lift', 'bay-steel')])
    out['handoff-out-of-order'] = (m, 'handoff 3 signalperson->crane-operator')
    m = dict(g); bad = json.loads(json.dumps(g['member-a-lift-director.json'])); bad['digest']['hex'] = '0' * 64
    m['member-a-lift-director.json'] = bad
    out['bad-digest'] = (m, 'record member-a-lift-director.json: digest')
    m = dict(g); m['member-c-signalperson.json'] = package(C, [ep_walk(2, 'riggers', 'rigging-signals', 'sightline'), ep_sim(3, 'riggers', 'rigging-signals', 'oak-blind-pick'),
                                                               ep_walk(5, 'riggers', 'rigging-signals', 'path')])
    out['wrong-scenario'] = (m, 'role signalperson')
    m = dict(g); m['member-d-crane-operator.json'] = package(D, [ep_sim(4, 'crane-ops', 'crane-lift', 'bay-steel', passed=False)])
    out['sim-not-passed'] = (m, 'role crane-operator')
    return out


def write_fixture():
    written = []
    for d in FIXTURE.glob('*'):
        if d.is_dir():
            for f in d.glob('*.json'):
                f.unlink()
            d.rmdir()
    def put(sub, files):
        (FIXTURE / sub).mkdir(parents=True, exist_ok=True)
        for name in sorted(files):
            p = FIXTURE / sub / name
            p.write_text(json.dumps(files[name], indent=1, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')
            written.append(f'{sub}/{name}')
    put('good', good_records())
    index = {'site': FIX_SITE, 'label': 'fixture crew A..D - not learners; four labels because four records, not four people',
             'good': 'fixture/good/', 'mutants': {}}
    for name, (files, fails) in mutants().items():
        put('mutant-' + name, files)
        index['mutants'][name] = {'dir': f'fixture/mutant-{name}/', 'fails': fails}
    index['signed'] = {'built_by': 'worksites/test.mjs, in memory, from fixture/good/',
                       'why_not_on_disk': 'python3 has no keccak-256 and no secp256k1; the throwaway-key signing is imported from completion/test.mjs ONLY in the test, and a build must be deterministic',
                       'signs': ['member-a-lift-director.json', 'member-b-rigger.json', 'member-b-rigger-completion.json']}
    return index, written


def main():
    authored = sorted(AUTHORED.glob('*.json'))
    if len(authored) != 8:
        fail(f'worksites/authored holds {len(authored)} declarations, not 8')
    sites = [build_site(p) for p in authored]
    ids = [s['id'] for s in sites]
    if len(set(ids)) != len(ids):
        fail('duplicate site ids')
    fixture_index, written = write_fixture()
    if FIX_SITE not in ids:
        fail(f'fixture site {FIX_SITE} is not a declared site')
    all_unions = sorted({u for s in sites for u in s['derived']['unions']})
    all_halls = sorted({h for s in sites for h in s['derived']['halls']})
    n_h = sum(s['derived']['handoffs'] for s in sites)
    n_v = sum(s['derived']['handoffs_verifiable'] for s in sites)
    by_kind = {}
    for s in sites:
        k = s['place']['kind']
        by_kind[k] = (by_kind[k] if k in by_kind else 0) + 1
    stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
    authored_stamp = hashlib.sha256(b''.join(p.read_bytes() for p in authored)).hexdigest()[:16]
    reg = {
        'pack': 'smartcitix-trade-craft-academy-worksites',
        'product': PRODUCT,
        'pack_version': PACK_VERSION,
        'built': '2026-09-26',
        'source_stamp': stamp,
        'authored_stamp': authored_stamp,
        'provenance': {'declarations': 'AUTHORED (worksites/authored/*.json: id, title, job, place, crew, role unions, hand-off evidence, gates)',
                       'everything_else': 'DERIVED (names, halls, seats, PPE, verifiability, rollups, fixture)'},
        'contract': ('a work site is a scenario where a crew drawn from at least two unions works one job with hand-offs; '
                     'its completion is checked offline by worksites/verify.mjs from the members\' own exported '
                     'tc-completion/1 records and tc-contribution/1 packages, one distinct record per role, each '
                     'verified by its own pack\'s verifier first, with the hand-offs held in order by the episodes\' timestamps'),
        'honesty': {
            'authored': 'these are AUTHORED scenarios, hand-written and validated against the registries; none is a record of a job anyone ran',
            'no_multi_user': 'no two learners have ever been on a site together here: this bundle has no multi-user session, no shared world state and no server. A crew completion is N separate records, each made alone on its own device, read side by side',
            'not_a_certification': 'a crew completion proves that N records, each internally consistent, together cover the roles and the order; not that these people stood on one site at one time; nothing here is a certification',
            'unverified': crews_reg['honesty']['unverified'],
            'not_a_permit': crews_reg['honesty']['not_a_permit'],
            'not_stated': 'no duration and no price is stated anywhere in this registry',
            'ppe': 'never typed: derived from surfaces/ for a custom space\'s finishes; a campus or a restoration site has no finishes here and the registry says so',
        },
        'evidence_kinds': {k: {'names': v['refs'], 'episode_kind': v['episode_kind']} for k, v in EVIDENCE_SHAPES.items()},
        'episode_kinds_read_from': 'training/registry/training.json#episode_kinds',
        'place_kinds': list(PLACE_KINDS),
        'verifier': {'run': 'node worksites/verify.mjs <site-id> <record.json>...',
                     'rules': ['record.verifies', 'role.covered', 'role.distinct', 'handoff.order', 'handoff.verifiable', 'identity.attested'],
                     'last_line': 'a crew completion proves that N records, each internally consistent, together cover the roles and the order; not that these people stood on one site at one time; nothing here is a certification'},
        'fixture': fixture_index,
        'counts': {
            'sites': len(sites),
            'unions_covered': len(all_unions), 'unions_total': len(UNIONS),
            'halls_involved': len(all_halls),
            'crews_used': len({s['crew']['id'] for s in sites}), 'crews_total': len(CREWS),
            'roles': sum(s['derived']['roles'] for s in sites),
            'handoffs': n_h, 'handoffs_verifiable': n_v, 'handoffs_unverifiable': n_h - n_v,
            'places_by_kind': {k: by_kind[k] for k in sorted(by_kind)},
            'seats_involved': len({x for s in sites for x in s['derived']['seats']}),
            'fixture_files': len(written),
        },
        'unions_covered': all_unions,
        'sites': sites,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    c = reg['counts']
    print(f'written: {OUT.relative_to(ROOT)} | {c["sites"]} sites | {c["unions_covered"]} of {c["unions_total"]} unions | '
          f'{c["handoffs_verifiable"]}/{c["handoffs"]} hand-offs verifiable | stamp {stamp}')


if __name__ == '__main__':
    main()
