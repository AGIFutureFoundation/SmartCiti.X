#!/usr/bin/env python3
"""Programs pack (wave 18): K-12 program pathways by grade band, teacher-facing program cards and a
nonprofit-sectors view, all DERIVED from registries that already stand, or AUTHORED by the rules printed in
`rules` below. Writes programs/registry/programs.json with a sha256 source_stamp.

Reads (fail closed - a missing field stops the build with a named error, nothing is defaulted):
  schools/registry/schools.json         bands, districts (PROPOSED), units, teacher model
  classroom/registry/classroom.json     classroom modules (one per schools unit), places with world links
  cognitionx/registry/cognitionx.json   2,064 verbatim CC BY 4.0 Cognition.X blocks and their modules
  courses/registry/courses.json         courses and their DERIVED band lessons
  lessons/registry/lessons.json         lesson titles, why and limits (for the play-safe rule)
  hive/registry/hive.json               the classroom allow-list, hold words, agents and their lines
  respond/registry/respond.json         disaster response: scenario frames, services, hall cross links
  layers/registry/paths.json            the parish paths: UN training (PROPOSED module) and Disaster relief
  smiles/registry/smiles.json           the Unspoken Smiles district (AUTHORED game district)
  restoration/registry/restoration.json and scenarios.json   the Bay restoration sites and scenarios

Nothing is fetched and no model runs. No organisation, partnership, grant, funding, accreditation or count is
invented: every name is READ, every count is computed here from the lists it counts.
Usage: python3 programs/build.py [--check]
"""
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'programs' / 'registry' / 'programs.json'


class ProgramsError(Exception):
    pass


def need(c, msg):
    if not c:
        raise ProgramsError('programs/build.py: ' + msg)
    return c


def field(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise ProgramsError(f'programs/build.py: {where} has no field {k!r}')
    return d[k]


SRC = {
    'schools': 'schools/registry/schools.json',
    'classroom': 'classroom/registry/classroom.json',
    'cognitionx': 'cognitionx/registry/cognitionx.json',
    'courses': 'courses/registry/courses.json',
    'lessons': 'lessons/registry/lessons.json',
    'hive': 'hive/registry/hive.json',
    'respond': 'respond/registry/respond.json',
    'paths': 'layers/registry/paths.json',
    'smiles': 'smiles/registry/smiles.json',
    'restoration': 'restoration/registry/restoration.json',
    'scenarios': 'restoration/registry/scenarios.json',
}
RAW, REG = {}, {}
for k, p in SRC.items():
    f = ROOT / p
    need(f.exists(), f'{p} is missing; build that pack first')
    RAW[k] = f.read_bytes()
    REG[k] = json.loads(RAW[k].decode('utf-8'))

S, CL, CX, CO, LE, HV = REG['schools'], REG['classroom'], REG['cognitionx'], REG['courses'], REG['lessons'], REG['hive']
RS, PA, SM, RE, SC = REG['respond'], REG['paths'], REG['smiles'], REG['restoration'], REG['scenarios']

# ------------------------------------------------------------------ the play-safe rule (the hive's own hold list)
K12 = field(HV, 'k12', SRC['hive'])
HOLD_WORDS = field(K12, 'hold_words', SRC['hive'] + '#k12')
need(isinstance(HOLD_WORDS, list) and HOLD_WORDS, 'hive k12.hold_words is empty')
HOLD = re.compile(r'\b(' + '|'.join(re.escape(w) for w in HOLD_WORDS) + r')\b', re.I)
ALLOW_ADV = field(K12, 'advisors', SRC['hive'] + '#k12')
ALLOW_NPC = field(K12, 'npc_roles', SRC['hive'] + '#k12')


def safe(*texts):
    return not any(HOLD.search(str(t)) for t in texts)


LESSONS = field(LE, 'lessons', SRC['lessons'])


def lesson_safe(lid):
    L = need(LESSONS.get(lid), f'lesson {lid} is not in {SRC["lessons"]}')
    return safe(field(L, 'title', lid), field(L, 'why', lid), field(L, 'limits', lid))


def lesson_title(lid):
    return field(LESSONS[lid], 'title', lid)


# ------------------------------------------------------------------ bands: schools bands, Cognition.X bands folded in by grade range
def grade_span(label):
    """'K-5' / 'K–2' / '9–10' -> (lo, hi) with K = 0"""
    parts = re.split(r'[-–]', label)
    need(len(parts) == 2, f'band label {label!r} is not a range')
    n = [0 if x.strip().upper() == 'K' else int(x) for x in parts]
    return n[0], n[1]


SBANDS = field(S, 'bands', SRC['schools'])
need(len(SBANDS) == 4, f'schools has {len(SBANDS)} bands, the pathways expect the 4 it declared')
CX_BANDS = field(CX, 'bands', SRC['cognitionx'])
CX_FOLD = {}
for b in SBANDS:
    lo, hi = grade_span(field(b, 'band', 'schools band'))
    CX_FOLD[b['band']] = [c for c in CX_BANDS if lo <= grade_span(c)[0] and grade_span(c)[1] <= hi]
need(sorted(c for v in CX_FOLD.values() for c in v) == sorted(CX_BANDS),
     f'Cognition.X bands {CX_BANDS} do not fold exactly once into the schools bands: {CX_FOLD}')

# ------------------------------------------------------------------ hive: the classroom allow-list
AGENTS = field(HV, 'agents', SRC['hive'])
BY_ID = {a['id']: a for a in AGENTS}
ALLOW = [a for a in AGENTS if field(a, 'k12', a.get('id', '?'))]
for a in ALLOW:
    role_ok = (a['kind'] == 'advisor' and a['id'].split(':', 1)[1] in ALLOW_ADV) or \
              (a['kind'] == 'npc' and field(a, 'role', a['id']) in ALLOW_NPC)
    need(role_ok, f'hive agent {a["id"]} is marked k12 but is not on the classroom allow-list')
need(len(ALLOW) == field(HV, 'counts', SRC['hive'])['k12_agents'], 'hive k12 agents differ from hive counts.k12_agents')
LINE_PREF = ['greeting', 'say', 'knowledge']


def opener(a):
    """the first play-safe line by kind preference greeting > say > knowledge, in the agent's own line order"""
    for kind in LINE_PREF:
        for i, ln in enumerate(field(a, 'lines', a['id'])):
            if ln['kind'] == kind and ln.get('k12') is True and safe(ln['text']):
                return {'text': ln['text'], 'kind': kind, 'source': ln['source'],
                        'hive_ref': f'{SRC["hive"]}#agents[id={a["id"]}].lines[{i}]'}
    raise ProgramsError(f'programs/build.py: allow-listed agent {a["id"]} has no play-safe greeting, say or knowledge line')


def agent_row(a):
    return {'id': a['id'], 'kind': a['kind'], 'name': a['name'], 'role': a['role'], 'where': a['where'], 'opener': opener(a)}


# ------------------------------------------------------------------ courses and classroom modules
COURSES = field(CO, 'courses', SRC['courses'])
MODULES = field(CL, 'modules', SRC['classroom'])
PLACES = {p['id']: p for p in field(CL, 'places', SRC['classroom'])}
UNITS = {u['hall']: u for u in field(S, 'units', SRC['schools'])}
CXM = {m['id']: m for m in field(CX, 'modules', SRC['cognitionx'])}
BLOCKS = field(CX, 'blocks', SRC['cognitionx'])
need(len(BLOCKS) == field(CX, 'counts', SRC['cognitionx'])['blocks'], 'cognitionx blocks differ from counts.blocks')


def course_for_hall(h):
    return f'trade.{h}' if f'trade.{h}' in COURSES else None


def href_of(place_id):
    p = need(PLACES.get(place_id), f'classroom place {place_id} is not in classroom places')
    return {'id': place_id, 'world': p['world'], 'kind': p['kind'], 'title': p['title'], 'href': field(p, 'href', place_id)}


def does_for(band, unit, kinds):
    """what a class does: the schools unit fields the band's offer admits (DERIVED from the course band kinds)"""
    out = [{'what': 'offer', 'text': band['offer'], 'source': f'{SRC["schools"]}#bands[band={band["band"]}].offer'}]
    if 'station' in kinds:
        out.append({'what': 'home', 'text': field(unit, 'home', unit['hall']), 'source': f'{SRC["schools"]}#units[hall={unit["hall"]}].home'})
        out.append({'what': 'class_drill', 'text': field(unit, 'class_drill', unit['hall']), 'source': f'{SRC["schools"]}#units[hall={unit["hall"]}].class_drill'})
    if 'sim' in kinds and field(unit, 'floor_sims', unit['hall']):
        out.append({'what': 'floor_sims', 'text': ', '.join(unit['floor_sims']), 'source': f'{SRC["schools"]}#units[hall={unit["hall"]}].floor_sims'})
    if 'unaided verification gate' in band['offer']:
        out.append({'what': 'gate', 'text': field(unit, 'gate', unit['hall']), 'source': f'{SRC["schools"]}#units[hall={unit["hall"]}].gate'})
    return out


def greeter_for(places):
    """lowest parish FIPS among the module's parish places that has an allow-listed k12-guide standing in it;
    otherwise the campus Orientation guide at the hall door"""
    fips = sorted({PLACES[p]['ref']['fips'] for p in places if PLACES[p]['world'] == 'parishes' and 'fips' in PLACES[p]['ref']})
    for f in fips:
        g = sorted(a['id'] for a in ALLOW if a['kind'] == 'npc' and a['role'] == 'k12-guide'
                   and str(a['where'].get('place', '')).startswith(f'st-{f}-'))
        if g:
            return BY_ID[g[0]], 'parish'
    return need(BY_ID.get('advisor:guide'), 'hive has no advisor:guide'), 'campus'


BAND_RULES = field(field(CO, 'rules', SRC['courses']), 'bands', SRC['courses'] + '#rules')
bands_out, cards = [], []
for b in SBANDS:
    bid = b['band']
    kinds = field(field(BAND_RULES, bid, 'courses rules.bands'), 'kinds', bid)
    steps, n = [], 0
    # 1. meet: the allow-listed agents, advisors first (hive order), then the parish figures (hive order)
    meet = [a['id'] for a in ALLOW if a['kind'] == 'advisor'] + [a['id'] for a in ALLOW if a['kind'] == 'npc']
    # 2. courses: each course carrying play-safe lessons for this band, courses registry order, lessons in course order
    held_lessons = []
    course_steps = []
    for cid, c in COURSES.items():
        bl = field(field(c, 'band_lessons', cid), bid, cid)
        ok = [l for l in bl if lesson_safe(l)]
        held_lessons += [l for l in bl if not lesson_safe(l)]
        if ok:
            course_steps.append({'course': cid, 'kind': c['kind'], 'title': c['title'],
                                 'lessons': [{'id': l, 'title': lesson_title(l)} for l in ok]})
    lessons_band = sorted({l['id'] for cs in course_steps for l in cs['lessons']})
    # 3. classroom modules whose lessons stand in this band and are play-safe (classroom order)
    mod_steps = []
    for m in MODULES:
        ls = [l for l in field(m, 'lessons', m['id']) if l in lessons_band]
        if not ls:
            continue
        mod_steps.append({'module': m['id'], 'hall': m['hall'], 'hall_name': m['hall_name'],
                          'lessons': [{'id': l, 'title': lesson_title(l)} for l in ls], 'places': m['places'],
                          'worlds': m['worlds'], 'course': course_for_hall(m['hall'])})
    # 4. Cognition.X: play-safe blocks in the folded bands, by module (cognitionx module order, blocks in module order)
    cx_steps, cx_held = [], 0
    by_block = {bl['block_id']: bl for bl in BLOCKS}
    for mid, m in CXM.items():
        ids = [x for x in field(m, 'blocks', mid) if by_block[x]['band'] in CX_FOLD[bid]]
        ok = [x for x in ids if safe(by_block[x]['theme'], by_block[x]['description'], by_block[x]['transfer_check'])]
        cx_held += len(ids) - len(ok)
        if ok:
            first = by_block[ok[0]]
            cx_steps.append({'cx_module': mid, 'pack': m['pack'], 'pack_slug': m['pack_slug'], 'name': m['name'],
                             'blocks': ok, 'first': {'block_id': first['block_id'], 'theme': first['theme'],
                                                    'transfer_check': first['transfer_check'], 'band': first['band']}})
    for a in meet:
        n += 1
        steps.append({'n': n, 'kind': 'agent', 'ref': a})
    for cs in course_steps:
        n += 1
        steps.append({'n': n, 'kind': 'course', 'ref': cs['course']})
    for ms in mod_steps:
        n += 1
        steps.append({'n': n, 'kind': 'module', 'ref': ms['module']})
    for xs in cx_steps:
        n += 1
        steps.append({'n': n, 'kind': 'cognitionx', 'ref': xs['cx_module']})
    blocks_band = sum(len(x['blocks']) for x in cx_steps)
    bands_out.append({
        'band': bid, 'level': b['level'], 'offer': b['offer'], 'offer_source': f'{SRC["schools"]}#bands[band={bid}]',
        'cognitionx_bands': CX_FOLD[bid], 'kinds': kinds,
        'courses': course_steps, 'modules': mod_steps, 'cognitionx': cx_steps, 'agents': meet,
        'program': steps,
        'counts': {'steps': len(steps), 'agents': len(meet), 'courses': len(course_steps), 'lessons': len(lessons_band),
                   'lessons_held': len(set(held_lessons)), 'modules': len(mod_steps), 'cx_modules': len(cx_steps),
                   'blocks': blocks_band, 'blocks_held': cx_held, 'cards': len(mod_steps)},
    })
    # teacher-facing program cards: one per classroom module that serves the band
    for ms in mod_steps:
        unit = need(UNITS.get(ms['hall']), f'schools has no unit for hall {ms["hall"]}')
        g, at = greeter_for(ms['places'])
        cards.append({
            'id': f'{bid}/{ms["module"]}', 'band': bid, 'level': b['level'], 'module': ms['module'], 'hall': ms['hall'],
            'hall_name': ms['hall_name'], 'course': ms['course'], 'does': does_for(b, unit, kinds),
            'lessons': ms['lessons'], 'where': [href_of(p) for p in ms['places'] if 'sim' in kinds or PLACES[p]['kind'] != 'seat'],
            'greeter': dict(agent_row(g), at=at), 'voice': 'classroom mode: the voice starts muted until the class turns it on',
        })

# ------------------------------------------------------------------ sectors
def trade_courses(halls):
    return [c for c in (course_for_hall(h) for h in halls) if c]


def hall_row(h):
    c = need(COURSES.get(f'trade.{h}'), f'hall {h} has no trade course in {SRC["courses"]}')
    return {'hall': h, 'hall_name': c['title'], 'campus': c['campus']}


def ordered_unique(xs):
    out = []
    for x in xs:
        if x not in out:
            out.append(x)
    return out


def npcs_of_role(role):
    return sorted(a['id'] for a in AGENTS if a['kind'] == 'npc' and a['role'] == role)


CX_COUNTS = field(CX, 'counts', SRC['cognitionx'])['by_pack']

# community health: the Unspoken Smiles district, named only as the existing pages describe it
progs = field(SM, 'programmes', SRC['smiles'])
health = {
    'id': 'community-health', 'status': 'PROPOSED',
    'from': [SRC['smiles']],
    'quotes': [
        {'text': field(SM, 'disclaimer', SRC['smiles']), 'source': f'{SRC["smiles"]}#disclaimer'},
        {'text': field(SM, 'place_note', SRC['smiles']), 'source': f'{SRC["smiles"]}#place_note'},
        {'text': field(SM, 'play_note', SRC['smiles']), 'source': f'{SRC["smiles"]}#play_note'},
    ],
    'programmes': [{'id': p['id'], 'name': p['name'], 'stations': p['stations']} for p in progs],
    'scenarios': [{'id': g, 'kind': 'game', 'source': f'{SRC["smiles"]}#games.{g}'} for g in field(SM, 'games', SRC['smiles'])],
    'worlds': [{'id': 'smiles', 'href': 'trade_craft_smiles.html', 'title': field(SM, 'name', SRC['smiles'])}],
    'halls': [], 'courses': [], 'agents': [], 'cognitionx_packs': [],
    'empty_why': {'halls': 'no union hall stands in the Smiles district', 'courses': 'no course lesson stands in the Smiles district',
                  'agents': 'no Omega Hive agent is placed in the Smiles district',
                  'cognitionx_packs': 'none of the nine vendored Cognition.X packs is a health pack'},
    'counts': {'stations': len(field(SM, 'stations', SRC['smiles'])), 'programmes': len(progs), 'games': len(SM['games'])},
}

# disaster response: respond/ frames, the halls they touch, the responder figures, the first-response Cognition.X packs
frames = field(RS, 'scenario_frames', SRC['respond'])
xl = field(RS, 'hall_cross_links', SRC['respond'])
dr_halls = sorted(xl)
RESP_PATH = need(next((p for p in field(PA, 'parishes', SRC['paths'])[0]['paths'] if p['id'] == 'responders'), None),
                 'layers paths have no responders path')
need(RESP_PATH['npc_role'] == 'responder', 'the responders path no longer names the responder role')
response = {
    'id': 'disaster-response', 'status': 'PROPOSED', 'from': [SRC['respond'], SRC['paths']],
    'quotes': [{'text': RS['honesty'][k], 'source': f'{SRC["respond"]}#honesty.{k}'}
               for k in ('scaffold_not_protocol', 'nobody_qualified_has_read_this', 'unions_and_associations')],
    'services': [{'id': k, 'name': v['name']} for k, v in field(RS, 'services', SRC['respond']).items()],
    'scenarios': [{'id': f['id'], 'kind': 'frame', 'title': f['title'], 'halls': f['halls']} for f in frames],
    'halls': [{'hall': h, 'hall_name': xl[h]['hall_name'], 'campus': xl[h]['campus']} for h in dr_halls],
    'courses': trade_courses(dr_halls),
    'agents': npcs_of_role('responder'),
    'worlds': [{'id': 'parishes', 'href': 'trade_craft_parishes.html', 'title': 'path: ' + RESP_PATH['label']}],
    'cognitionx_packs': [{'slug': s, 'blocks': CX_COUNTS[s]} for s in ('RESPOND', 'EMERGENCY')],
    'counts': {'frames': len(frames), 'services': len(RS['services']), 'halls': len(dr_halls)},
}
need(response['counts']['halls'] == RS['counts']['halls_touched'], 'respond hall_cross_links differ from counts.halls_touched')

# humanitarian training: the parish UN training (PROPOSED module) and Disaster relief paths, their trainer and relief roles
hum_items, hum_halls = [], []
frame_by_id = {f['id']: f for f in frames}
paths_used = {}
for par in field(PA, 'parishes', SRC['paths']):
    for p in par['paths']:
        if p['id'] not in ('un', 'relief'):
            continue
        paths_used[p['id']] = {'id': p['id'], 'label': p['label'], 'status': p['status'], 'npc_role': p['npc_role'], 'what': p['what']}
        for st in p['steps']:
            if st['kind'] != 'quote':
                continue
            if st['ref_id'] not in [x['ref_id'] for x in hum_items]:
                hum_items.append({'ref_id': st['ref_id'], 'path': p['id'], 'item_kind': st['item_kind'], 'title': st['title'],
                                  'source': st['title_source']})
            if st['ref_id'] in frame_by_id:
                hum_halls += frame_by_id[st['ref_id']]['halls']
need(set(paths_used) == {'un', 'relief'}, f'layers paths lack the un / relief paths: {sorted(paths_used)}')
hum_halls = ordered_unique(hum_halls)
humanitarian = {
    'id': 'humanitarian-training', 'status': 'PROPOSED', 'from': [SRC['paths'], SRC['respond']],
    'quotes': [{'text': field(PA, 'un_disclaimer', SRC['paths']), 'source': f'{SRC["paths"]}#un_disclaimer'},
               {'text': PA['honesty']['un'], 'source': f'{SRC["paths"]}#honesty.un'}],
    'paths': [paths_used['un'], paths_used['relief']],
    'scenarios': hum_items,
    'halls': [hall_row(h) for h in hum_halls],
    'courses': trade_courses(hum_halls),
    'agents': npcs_of_role(paths_used['un']['npc_role']) + npcs_of_role(paths_used['relief']['npc_role']),
    'worlds': [{'id': 'parishes', 'href': 'trade_craft_parishes.html', 'title': 'path: ' + paths_used['un']['label']},
               {'id': 'parishes', 'href': 'trade_craft_parishes.html', 'title': 'path: ' + paths_used['relief']['label']}],
    'cognitionx_packs': [], 'empty_why': {'cognitionx_packs': 'the paths quote respond/ items only'},
    'counts': {'items': len(hum_items), 'parishes': len(PA['parishes']), 'halls': len(hum_halls)},
}
need(paths_used['un']['status'] == 'PROPOSED', 'the UN training path is no longer marked PROPOSED')

# environmental restoration: the Bay restoration sites and AUTHORED scenarios
sites = field(RE, 'sites', SRC['restoration'])
scen = field(SC, 'scenarios', SRC['scenarios'])
re_halls = ordered_unique([t for s in sites for t in field(s, 'trade_needs', s['id'])] +
                          [c['trade'] for x in scen for c in field(x, 'crew', x['id'])])
restoration = {
    'id': 'environmental-restoration', 'status': 'PROPOSED', 'from': [SRC['restoration'], SRC['scenarios']],
    'quotes': [{'text': RE['honesty']['not_affiliated'], 'source': f'{SRC["restoration"]}#honesty.not_affiliated'},
               {'text': SC['honesty']['label'], 'source': f'{SRC["scenarios"]}#honesty.label'},
               {'text': SC['honesty']['no_remediation'], 'source': f'{SRC["scenarios"]}#honesty.no_remediation'}],
    'sites': [{'id': s['id'], 'name': s['name'], 'org': s['org'], 'category': s['category'], 'walkable': s['walkable']} for s in sites],
    'scenarios': [{'id': x['id'], 'kind': 'scenario', 'site': x['site'], 'title': x['title'], 'label': x['label']} for x in scen],
    'halls': [hall_row(h) for h in re_halls],
    'courses': trade_courses(re_halls),
    'agents': [], 'empty_why': {'agents': 'no Omega Hive agent in hive/registry/hive.json is placed at a Bay restoration site'},
    'worlds': [{'id': 'bay', 'href': 'trade_craft_bay.html', 'title': 'Bay world'}],
    'cognitionx_packs': [],
    'counts': {'sites': len(sites), 'scenarios': len(scen), 'halls': len(re_halls)},
}
restoration['empty_why']['cognitionx_packs'] = 'none of the nine vendored Cognition.X packs is a restoration pack'
sectors = [health, response, humanitarian, restoration]
for sec in sectors:
    for a in sec['agents']:
        need(a in BY_ID, f'sector {sec["id"]} names agent {a} that the hive does not hold')
    for c in sec['courses']:
        need(c in COURSES, f'sector {sec["id"]} names course {c} that courses.json does not hold')

# ------------------------------------------------------------------ the registry
sources = [{'path': p, 'sha256': hashlib.sha256(RAW[k]).hexdigest()} for k, p in SRC.items()]
body = {
    'pack': 'smartcitix-programs', 'schema': 'programs/1',
    'product': field(S, 'product', SRC['schools']),
    'sources': sources,
    'honesty': {
        'status': 'AUTHORED and DERIVED: every pathway, card and sector is a selection and an order chosen by the rules '
                  'printed under `rules`; every name, title, line and count is READ from the registry that owns it.',
        'proposed': 'Districts, programmes and organisations named here are PROPOSED: no district, programme or '
                    'organisation has reviewed or agreed, and no agreement, grant or funding exists.',
        'un': 'The UN path is a PROPOSED module of this game, not affiliated with or endorsed by the United Nations.',
        'not_accredited': 'Nothing here is accredited and nothing certifies anybody. Lessons are unverified general practice.',
        'play': 'Games, coins and badges are play: kept on the device, never a completion record, never money.',
        'districts': {'text': S['honesty']['districts'], 'source': f'{SRC["schools"]}#honesty.districts'},
        'cognitionx': {'text': CX['honesty']['blocks'], 'source': f'{SRC["cognitionx"]}#honesty.blocks'},
        'standards': {'text': CL['honesty']['standards'], 'source': f'{SRC["classroom"]}#honesty.standards'},
    },
    'attribution': {k: CX['attribution'][k] for k in ('text', 'author', 'title', 'source_url', 'license_id', 'license', 'license_url', 'repo', 'commit')},
    'rules': {
        'play_safe': 'a lesson is play-safe when its title, why and limits contain no word on the hive k12 hold list; a '
                     'Cognition.X block when its theme, description and transfer check contain none; an agent line when its '
                     'text contains none. Held items are counted, never reworded.',
        'band_fold': 'a Cognition.X band joins the schools band whose grade range contains it (K = 0).',
        'program_order': '1 the allow-listed Hive agents (advisors, then parish figures, hive order); 2 courses carrying '
                         'play-safe lessons for the band (courses registry order, lessons in course order); 3 classroom '
                         'modules whose lessons stand in the band (classroom order); 4 Cognition.X modules with play-safe '
                         'blocks in the folded bands (cognitionx order).',
        'cards': 'one card per band and classroom module of that band; a simulator seat is listed only when the band '
                 'admits sims. What a class does = the band offer, then the '
                 'schools unit home and class drill when the band admits stations, the floor sims when it admits sims, and '
                 'the gate when the offer names the unaided verification gate.',
        'greeter': 'the allow-listed k12-guide standing in the lowest-FIPS parish among the module places (lowest id); '
                   'with none, the campus Orientation guide at the hall door. The line is the first play-safe greeting, '
                   'say or knowledge line, in that order. In classroom mode the voice starts muted.',
        'sectors': 'community health = the Smiles district; disaster response = respond/ frames, the halls they touch and '
                   'the responder figures; humanitarian training = the parish UN training (PROPOSED) and Disaster relief '
                   'paths and their trainer and relief roles; environmental restoration = restoration/ sites and '
                   'scenarios, their trade needs and crews. Courses are the trade courses of those halls.',
        'hold_words': HOLD_WORDS, 'allow_list': {'advisors': ALLOW_ADV, 'npc_roles': ALLOW_NPC},
    },
    'districts': [{'district': d['district'], 'status': d['status'], 'source': f'{SRC["schools"]}#districts[{i}]'}
                  for i, d in enumerate(field(S, 'districts', SRC['schools']))],
    'bands': bands_out,
    'cards': cards,
    'sectors': sectors,
    'counts': {
        'bands': len(bands_out), 'cards': len(cards), 'sectors': len(sectors), 'allow_list_agents': len(ALLOW),
        'units': len(UNITS), 'modules': len(MODULES), 'blocks': len(BLOCKS), 'districts': len(S['districts']),
        'lessons_by_band': {b['band']: b['counts']['lessons'] for b in bands_out},
        'blocks_by_band': {b['band']: b['counts']['blocks'] for b in bands_out},
        'cards_by_band': {b['band']: b['counts']['cards'] for b in bands_out},
        'greeters': len({c['greeter']['id'] for c in cards}),
        'models': 0,
    },
}
stamp = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:16]
doc = {'pack': body.pop('pack'), 'schema': body.pop('schema'), 'source_stamp': stamp, **body}
text = json.dumps(doc, ensure_ascii=False, indent=1) + '\n'
if '--check' in sys.argv:
    have = OUT.read_text(encoding='utf-8') if OUT.exists() else None
    if have != text:
        print('STALE: programs/registry/programs.json\n       run: python3 programs/build.py')
        sys.exit(1)
    print('programs/registry/programs.json is current')
    sys.exit(0)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(text, encoding='utf-8')
c = doc['counts']
print(f'programs: {c["bands"]} bands | {c["cards"]} cards | {c["sectors"]} sectors | {c["allow_list_agents"]} allow-listed agents | '
      f'lessons {c["lessons_by_band"]} | blocks {c["blocks_by_band"]} | stamp {stamp}')
