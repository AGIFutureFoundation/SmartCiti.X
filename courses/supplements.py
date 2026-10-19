"""courses/supplements.py - one supplement per lesson, composed by the rules in SUP_RULES from the registries courses/build.py
has already loaded (passed in as its namespace). Nothing here is a new fact: every term, meaning, quote, option and
answer is READ from the registry named beside it; the only words written here are the rule sentences and the i18n
template keys the page fills (course.q.* for questions, course.w.* for worksheet lines). Fail closed: a missing field
stops the build by name. Option order is index arithmetic on the lesson's position, never chance.
"""

SUP_RULES = {
    'glossary': 'the rooms and off-room places the lesson stands in (meaning: web/interiors.py purpose, lessons.json off_room_places), '
                'every tool of the hall\'s district crib (meaning: the tool\'s own `use` line), every PPE item and hazard on the '
                'condition record of a room the lesson walks (meaning: where it is listed - the record gives no definition, so none is written), '
                'the seats, scenarios and walkaround points the lesson runs (meaning: task, brief, check), the advisors and crew roles it asks '
                '(meaning: role, job)',
    'concepts': 'the lesson\'s own `why`, every step note, then from the owning registry: a station\'s lesson and doctrine, an advisor '
                'or crew topic\'s `say` (or, for a `read` topic, the binding it is read from), a crew role\'s stop condition, a '
                'scenario\'s `teaches`, a walkaround point\'s check, and the crib drill contract',
    'safety': 'labelled unverified general practice. The condition record of every room the lesson walks, quoted in the exact form '
              'the 3D page\'s condLine() prints it (a placard hangs only where the record asks for PPE), the walkaround fault line '
              'and the crew stop-work lines of the steps that bind them, the checklist of a station step, and the lesson\'s limits',
    'questions': 'one per walk, placard, advisor, walkaround, sim, crew and station step, plus one crib drill item for every lesson '
                 '(two when the lesson runs the crib check); each answer is a registry id with the pointer it resolves at, the '
                 'distractors are siblings from the same record, and the correct option\'s position is index arithmetic',
    'worksheet': 'one line per step: the step\'s own `do` line, verbatim, and a fill-in prompt for its kind',
    'where': 'the rooms and places walked, the hall\'s district crib, the advisors asked (and the room each stands in), the seats '
             'and scenarios run, the crews asked, the stations taken, and links to the lesson, the hall in 3D and the ladder',
}

WORKSHEET_KEYS = {'walk': 'course.w.walk', 'placard': 'course.w.placard', 'advisor': 'course.w.advisor',
                  'station': 'course.w.station', 'crib': 'course.w.crib', 'walkaround': 'course.w.walkaround',
                  'sim': 'course.w.sim', 'crew': 'course.w.crew'}
QUESTION_KEYS = ['course.q.walk', 'course.q.placard', 'course.q.advisor', 'course.q.point', 'course.q.scenario',
                 'course.q.crew', 'course.q.crib', 'course.q.station', 'course.q.doctrine']


def build_all(ns):
    need, req = ns['need'], ns['req']
    LESSONS, LORDER, LES = ns['LESSONS'], ns['LORDER'], ns['LES']
    ROOM_LABEL, ROOM_PURPOSE, STRANDS, OFF_ROOM = ns['ROOM_LABEL'], ns['ROOM_PURPOSE'], ns['STRANDS'], ns['OFF_ROOM']
    SIM, STATION_BY, CRIBS, CRIB_BIND = ns['SIM'], ns['STATION_BY'], ns['CRIBS'], ns['CRIB_BIND']
    ADV, ADV_BIND, CREWS = ns['ADV'], ns['ADV_BIND'], ns['CREWS']
    cond_line, cond_of = ns['cond_line'], ns['cond_of']
    STATIONS_ALL = list(STATION_BY)
    ADV_IDS = list(ADV)
    DRILL = req(CRIBS, 'drill', 'toolcribs.json')

    def place(where):
        if where in ROOM_LABEL:
            return {'where': where, 'label': ROOM_LABEL[where], 'kind': 'room'}
        p = req(OFF_ROOM, where, 'off_room_places')
        return {'where': where, 'label': p['short'], 'kind': 'place'}

    def rotate(correct, others, seed):
        """the correct option goes to position seed mod n; the others keep their order around it"""
        opts = list(others)
        pos = seed % (len(opts) + 1)
        return opts[:pos] + [correct] + opts[pos:]

    def pick(pool, avoid, start, k):
        out, i = [], 0
        while len(out) < k and i < len(pool) * 2:
            c = pool[(start + i * 3) % len(pool)]
            if c not in avoid and c not in out:
                out.append(c)
            i += 1
        return out

    sups, totals = {}, {'glossary_terms': 0, 'concepts': 0, 'placard_quotes': 0, 'placards_hung': 0, 'questions': 0,
                        'worksheet_lines': 0, 'safety_lines': 0}
    q_by_kind = {}
    for li, lid in enumerate(LORDER):
        L = LESSONS[lid]
        hall = L['hall']
        ctx = f'supplement {lid}'
        gl, seen_terms = [], set()

        def term(t, kind, meaning, source, **extra):
            key = (kind, t)
            if key in seen_terms:
                return
            seen_terms.add(key)
            gl.append({'term': t, 'kind': kind, 'meaning': meaning, 'source': source, **extra})

        concepts, seen_c = [], set()

        def concept(text, kind, source):
            need(isinstance(text, str) and text.strip(), f'{ctx}: an empty {kind} concept from {source}')
            if text in seen_c:
                return
            seen_c.add(text)
            concepts.append({'text': text, 'kind': kind, 'source': source})

        concept(L['why'], 'why', f'lessons/registry/lessons.json#lessons.{lid}.why')
        # rooms and places, in step order
        wheres = []
        for s in L['steps']:
            if s['where'] not in wheres:
                wheres.append(s['where'])
        for w in wheres:
            if w in ROOM_LABEL:
                term(ROOM_LABEL[w], 'room', ROOM_PURPOSE[w], f'web/interiors.py#ROOMS.{w}')
            else:
                p = req(OFF_ROOM, w, ctx)
                term(p['short'], 'place', p['what'], f'lessons/registry/lessons.json#off_room_places.{w}')
        # the district crib: every tool
        cb = req(CRIB_BIND, hall, ctx)
        district = cb['district']
        crib = req(req(CRIBS, 'cribs', ctx), district, ctx)
        for t in crib['tools']:
            term(t['name'], 'tool', req(t, 'use', f'{ctx} tool {t["id"]}'), f'tools/registry/toolcribs.json#cribs.{district}.tools.{t["id"]}', id=t['id'])
        # safety: the condition record of every strand room the lesson walks
        placards = []
        for w in wheres:
            if w not in ROOM_LABEL:
                continue
            c = cond_of(hall, w, ctx)
            hung = bool(c['ppe'])
            placards.append({'strand': w, 'room_label': ROOM_LABEL[w], 'quote': cond_line(c), 'ppe': list(c['ppe']),
                             'hazards': list(req(c, 'hazards', ctx)), 'placard_hung': hung,
                             'read_in_lesson': w in L['placard_steps_in'],
                             'source': f'surfaces/registry/finishes.json#halls.{hall}.conditions.{w}'})
            totals['placards_hung'] += hung
            for item in c['ppe']:
                term(item, 'ppe', None, f'surfaces/registry/finishes.json#halls.{hall}.conditions.{w}.ppe', listed_in=ROOM_LABEL[w])
            for hz in c['hazards']:
                term(hz, 'hazard', None, f'surfaces/registry/finishes.json#halls.{hall}.conditions.{w}.hazards', listed_in=ROOM_LABEL[w])
        safety_lines = []
        questions = []
        worksheet = []
        where = {'places': [place(w) for w in wheres], 'crib': {'district': district, 'name': crib['name']},
                 'advisors': [], 'seats': [], 'crews': [], 'stations': [],
                 'links': {'lesson': f'web/trade_craft_lessons.html#lesson-{lid}', 'hall3d': f'web/trade_craft_3d.html?hall={hall}',
                           'ladder': f'web/trade_craft_ladder.html?hall={hall}'}}

        def add_q(kind, stem, args, correct, others, answer_ref, labels):
            need(stem in QUESTION_KEYS, f'{ctx}: unknown question stem {stem}')
            need(len(others) >= 1, f'{ctx}: a {kind} question needs at least one distractor')
            ids = rotate(correct, others, li + len(questions))
            need(len(set(ids)) == len(ids), f'{ctx}: duplicate option in a {kind} question')
            lab = [labels[i] for i in ids]
            need(len(set(lab)) == len(lab), f'{ctx}: two options of a {kind} question read the same')
            questions.append({'id': f'{lid}.q{len(questions) + 1}', 'kind': kind, 'stem': stem, 'args': args,
                              'options': [{'id': i, 'label': labels[i]} for i in ids],
                              'answer': {'id': correct, 'ref': answer_ref}})
            q_by_kind[kind] = q_by_kind.get(kind, 0) + 1

        for s in L['steps']:
            k, n = s['kind'], s['n']
            sref = f'lessons/registry/lessons.json#lessons.{lid}.steps[{n - 1}]'
            concept(s['note'], 'note', sref + '.note')
            worksheet.append({'n': n, 'kind': k, 'do': s['do'], 'fill': WORKSHEET_KEYS[k],
                              'args': {'picks': DRILL['picks']} if k == 'crib' else {}})
            if k == 'walk':
                st = s['where']
                others = pick(STRANDS, {st}, STRANDS.index(st) + 4, 3)
                add_q('walk', 'course.q.walk', {'n': n}, st, others, f'web/interiors.py#ROOMS.{st}', ROOM_LABEL)
            elif k == 'placard':
                st = s['where']
                mine = cond_line(cond_of(hall, st, ctx))
                labels = {f'{hall}.{st}': mine}
                others = []
                for o in STRANDS:
                    if len(others) == 3:
                        break
                    q = cond_line(cond_of(hall, o, ctx))
                    if o != st and q not in labels.values():
                        labels[f'{hall}.{o}'] = q
                        others.append(f'{hall}.{o}')
                add_q('placard', 'course.q.placard', {'room': ROOM_LABEL[st]}, f'{hall}.{st}', others,
                      f'surfaces/registry/finishes.json#halls.{hall}.conditions.{st}', labels)
            elif k == 'advisor':
                aid = s['advisor']
                a = req(ADV, aid, ctx)
                topic = {t['id']: t for t in a['topics']}[s['topic']]
                term(a['name'], 'advisor', a['role'], f'agents/registry/advisors.json#advisors.{aid}')
                if topic['kind'] == 'say':
                    concept(topic['say'], 'advisor-say', f'agents/registry/advisors.json#advisors.{aid}.topics.{topic["id"]}.say')
                else:
                    concept(req(ADV_BIND, topic['bind'], ctx), 'advisor-read', f'agents/registry/advisors.json#bindings.{topic["bind"]}')
                if aid not in [x['id'] for x in where['advisors']]:
                    where['advisors'].append({'id': aid, 'name': a['name'], 'stands_in': a['stands_in'], 'at': place(a['stands_in'])['label']})
                others = pick(ADV_IDS, {aid}, ADV_IDS.index(aid) + 2, 3)
                add_q('advisor', 'course.q.advisor', {'ask': topic['ask']}, aid, others,
                      f'agents/registry/advisors.json#advisors.{aid}', {i: ADV[i]['name'] for i in ADV_IDS})
            elif k in ('walkaround', 'sim'):
                sid = s['sim']
                seat = req(SIM, sid, ctx)
                term(seat['name'], 'seat', seat['task'], f'sims/registry/sims.json#sims.{sid}.task')
                ent = next((x for x in where['seats'] if x['sim'] == sid), None)
                if not ent:
                    ent = {'sim': sid, 'name': seat['name'], 'scenarios': [], 'points': [], 'href': f'web/trade_craft_3d.html?hall={hall}&sim={sid}'}
                    where['seats'].append(ent)
                if k == 'walkaround':
                    pts = {p['id']: p for p in seat['walkaround']}
                    p = req(pts, s['point'], ctx)
                    term(p['point'], 'walkaround', p['check'], f'sims/registry/sims.json#sims.{sid}.walkaround.{p["id"]}')
                    concept(p['check'], 'walkaround-check', f'sims/registry/sims.json#sims.{sid}.walkaround.{p["id"]}.check')
                    safety_lines.append({'kind': 'walkaround-fault', 'label': p['point'], 'text': req(p, 'on_fault', ctx),
                                         'source': f'sims/registry/sims.json#sims.{sid}.walkaround.{p["id"]}.on_fault'})
                    ent['points'].append(p['id'])
                    others = [x for x in pts if x != p['id']][:3]
                    add_q('walkaround', 'course.q.point', {'check': p['check']}, p['id'], others,
                          f'sims/registry/sims.json#sims.{sid}.walkaround.{p["id"]}', {i: pts[i]['point'] for i in pts})
                else:
                    scs = {c['id']: c for c in seat['scenarios']}
                    sc = req(scs, s['scenario'], ctx)
                    term(sc['name'], 'scenario', req(sc, 'brief', ctx), f'sims/registry/sims.json#sims.{sid}.scenarios.{sc["id"]}')
                    if req(sc, 'teaches', ctx):
                        concept(sc['teaches'], 'scenario-teaches', f'sims/registry/sims.json#sims.{sid}.scenarios.{sc["id"]}.teaches')
                    ent['scenarios'].append(sc['id'])
                    others = [x for x in scs if x != sc['id']]
                    add_q('sim', 'course.q.scenario', {'seat': seat['name']}, sc['id'], others,
                          f'sims/registry/sims.json#sims.{sid}.scenarios.{sc["id"]}', {i: scs[i]['name'] for i in scs})
            elif k == 'crew':
                cid, rid = s['crew'], s['role']
                crew = req(CREWS, cid, ctx)
                role = req(crew['roles'], rid, ctx)
                term(role['name'], 'crew-role', role['job'], f'agents/registry/crews.json#crews.{cid}.roles.{rid}')
                topic = {t['id']: t for t in role['topics']}[s['topic']]
                if topic['kind'] == 'say':
                    concept(topic['say'], 'crew-say', f'agents/registry/crews.json#crews.{cid}.roles.{rid}.topics.{topic["id"]}.say')
                concept(f'{role["name"]}: {role["stops"]}', 'crew-stops', f'agents/registry/crews.json#crews.{cid}.roles.{rid}.stops')
                safety_lines.append({'kind': 'crew-stop-work', 'label': crew['name'], 'text': crew['stop_work'],
                                     'source': f'agents/registry/crews.json#crews.{cid}.stop_work'})
                if cid not in [x['crew'] for x in where['crews']]:
                    where['crews'].append({'crew': cid, 'name': crew['name'], 'seat': crew['seat'], 'roles': []})
                next(x for x in where['crews'] if x['crew'] == cid)['roles'].append(rid)
                rids = list(crew['roles'])
                others = [x for x in rids if x != rid][:3]
                add_q('crew', 'course.q.crew', {'crew': crew['name'], 'stops': role['stops']}, rid, others,
                      f'agents/registry/crews.json#crews.{cid}.roles.{rid}', {i: crew['roles'][i]['name'] for i in rids})
            elif k == 'station':
                sid = s['station']
                st = req(STATION_BY, sid, ctx)
                concept(st['lesson'], 'station-lesson', f'stations/registry/stations.json#stations.{sid}.lesson')
                concept(st['doctrine'], 'station-doctrine', f'stations/registry/stations.json#stations.{sid}.doctrine')
                for i, item in enumerate(st['checklist']):
                    safety_lines.append({'kind': 'station-checklist', 'label': st['name'], 'text': item,
                                         'source': f'stations/registry/stations.json#stations.{sid}.checklist[{i}]'})
                where['stations'].append({'id': sid, 'name': st['name'], 'room': st['room']})
                if st['quiz']:
                    qz = st['quiz']
                    opts = {o['prop']: o['label'] for o in qz['options']}
                    right = [o['prop'] for o in qz['options'] if o['correct']]
                    need(len(right) == 1, f'{ctx}: station {sid} quiz has {len(right)} correct options')
                    add_q('station', 'course.q.station', {'question': qz['question']}, right[0], [x for x in opts if x != right[0]],
                          f'stations/registry/stations.json#stations.{sid}.quiz', opts)
                else:
                    others = [x for x in pick(STATIONS_ALL, {sid}, STATIONS_ALL.index(sid) + 5, 6)
                              if STATION_BY[x]['name'] != st['name']][:3]
                    add_q('station', 'course.q.doctrine', {'doctrine': st['doctrine']}, sid, others,
                          f'stations/registry/stations.json#stations.{sid}', {i: STATION_BY[i]['name'] for i in STATIONS_ALL})
            elif k == 'crib':
                concept(DRILL['contract'], 'crib-contract', 'tools/registry/toolcribs.json#drill.contract')
            else:
                need(False, f'{ctx}: step kind {k} has no supplement rule')
        # the crib drill: one item for every lesson, two when the lesson runs the crib check
        drills = req(req(CRIBS, 'drills', ctx), district, ctx)
        tools = {t['id']: t['name'] for t in crib['tools']}
        tids = list(tools)
        n_items = 2 if any(s['kind'] == 'crib' for s in L['steps']) else 1
        for j in range(n_items):
            d = drills[(li + j) % len(drills)]
            need(d['tool'] in tools, f'{ctx}: drill answer {d["tool"]} is not a {district} crib tool')
            others = pick(tids, {d['tool']}, tids.index(d['tool']) + 1, 3)
            add_q('crib', 'course.q.crib', {'ask': d['ask']}, d['tool'], others,
                  f'tools/registry/toolcribs.json#cribs.{district}.tools.{d["tool"]}', tools)
        need(len(questions) >= 3, f'{ctx}: only {len(questions)} self-check questions')
        sups[lid] = {
            'lesson': lid, 'title': L['title'], 'hall': hall, 'hall_name': L['hall_name'], 'strand': L['strand'],
            'room_label': L['room_label'], 'tier': L['tier'],
            'glossary': gl, 'concepts': concepts,
            'safety': {'label': 'unverified general practice', 'placards': placards, 'lines': safety_lines,
                       'limits': L['limits'], 'not_certification': req(LES['honesty'], 'not_certification', 'lessons honesty')},
            'questions': questions, 'worksheet': worksheet, 'where': where,
            'provenance': {'terms': 'READ', 'meanings': 'READ', 'quotes': 'READ', 'questions': 'DERIVED', 'rules': 'AUTHORED'},
        }
        totals['glossary_terms'] += len(gl)
        totals['concepts'] += len(concepts)
        totals['placard_quotes'] += len(placards)
        totals['questions'] += len(questions)
        totals['worksheet_lines'] += len(worksheet)
        totals['safety_lines'] += len(safety_lines)
    counts = {'supplements': len(sups), 'lessons': len(LESSONS), **totals, 'questions_by_kind': q_by_kind,
              'lessons_with_placard_hung': sum(1 for s in sups.values() if any(p['placard_hung'] for p in s['safety']['placards'])),
              'min_questions': min(len(s['questions']) for s in sups.values()),
              'min_glossary': min(len(s['glossary']) for s in sups.values())}
    # coverage, recounted by courses/test.mjs: every step has a worksheet line; every step of a kind that names an id has a
    # question answered by that id (crib steps are covered by drill items); every lesson has a placard quote per strand room
    steps = [(lid, s) for lid in LORDER for s in LESSONS[lid]['steps']]
    asked = {'walk', 'placard', 'advisor', 'walkaround', 'sim', 'crew', 'station'}
    counts['coverage'] = {
        'lessons_with_supplement': len(sups), 'lessons': len(LESSONS),
        'steps_with_worksheet_line': sum(len(s['worksheet']) for s in sups.values()), 'steps': len(steps),
        'id_steps_with_question': sum(1 for lid, s in steps if s['kind'] in asked), 'id_steps': sum(1 for _l, s in steps if s['kind'] in asked),
        'crib_steps_with_drill_items': sum(1 for _l, s in steps if s['kind'] == 'crib'), 'crib_steps': sum(1 for _l, s in steps if s['kind'] == 'crib'),
        'lessons_with_crib_glossary': sum(1 for s in sups.values() if any(g['kind'] == 'tool' for g in s['glossary'])),
        'lessons_with_a_placard_hung': counts['lessons_with_placard_hung'],
        'lessons_whose_rooms_hang_no_placard': len(sups) - counts['lessons_with_placard_hung'],
        'cribs_in_glossaries': len({s['where']['crib']['district'] for s in sups.values()}), 'cribs': len(CRIBS['cribs']),
    }
    need(counts['supplements'] == counts['lessons'], 'a lesson has no supplement')
    return {'supplements': sups, 'rules': SUP_RULES, 'counts': counts,
            'keys': {'questions': QUESTION_KEYS, 'worksheet': WORKSHEET_KEYS}}
