#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the internal compliance ledger builder.

This ledger is not a code reference and cites no jurisdiction: it lists what
the bundle's OWN rules require of a hall and its rooms, and what a
tc-completion/1 record can evidence of them.

WHY THIS SHAPE. ROADMAP.md keeps the jurisdiction overlay deliberately
unstarted (the verbatim status is carried in the registry under
`jurisdiction.roadmap_status_verbatim`): this sandbox cannot fetch cited
values and must not type them from memory. So this pack derives, per hall
and per room, only what the registries already say - hazards and PPE from
surfaces/registry/finishes.json, the placard the 3D layer hangs (decided by
the same structural rule web/build_3d.py applies, read here not retyped),
the seat rubric pass rules from sims/registry/sims.json, the practitioner
sign-off status through pack/hall_signoff.mjs (run through node, as
bundles/build.py and web/build_map.py do), and the lessons that stand in the
hall with whether they carry a placard step in every hazard room. Per item
it states the evidence class a tc-completion/1 record can carry, read from
completion/registry/completion.json.

PROVENANCE. DERIVED: every fact and every count is read or computed from the
inputs stamped under `stamps`; none is typed. The fixture is completion's own
SCRIPTED record, re-used not re-authored, and one record mutant made from it.
"""
import copy
import hashlib
import json
import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'compliance.json'
FIX = HERE / 'fixture'
BUILT = '2026-09-26'

PATHS = {
    'finishes': 'surfaces/registry/finishes.json',
    'sims': 'sims/registry/sims.json',
    'lessons': 'lessons/registry/lessons.json',
    'halls': 'pack/registry/halls.json',
    'completion': 'completion/registry/completion.json',
    'manifest': 'pack/manifest.json',
    'build_3d': 'web/build_3d.py',
    'hall_signoff': 'pack/hall_signoff.mjs',
    'roadmap': 'ROADMAP.md',
    'completion_fixture': 'completion/fixture/good.json',
}


def need(mapping, key, who):
    """A missing key raises and names itself; no default is decided here."""
    if key not in mapping:
        raise KeyError(f'{who}: {key!r} does not resolve')
    return mapping[key]


def sha16(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()[:16]


STAMPS = {k: sha16(p) for k, p in PATHS.items()}
STAMPS['self'] = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

FIN = json.load(open(ROOT / PATHS['finishes']))
SIMS = json.load(open(ROOT / PATHS['sims']))
LESSONS = json.load(open(ROOT / PATHS['lessons']))
HALLS = json.load(open(ROOT / PATHS['halls']))
COMPLETION = json.load(open(ROOT / PATHS['completion']))
MANIFEST = json.load(open(ROOT / PATHS['manifest']))
BUILD_3D = (ROOT / PATHS['build_3d']).read_text()
ROADMAP = (ROOT / PATHS['roadmap']).read_text()

PRODUCT = need(MANIFEST, 'product', 'manifest')
PACK_VERSION = need(MANIFEST, 'pack_version', 'manifest')
for name, reg in (('finishes', FIN), ('sims', SIMS), ('lessons', LESSONS), ('completion', COMPLETION)):
    assert need(reg, 'pack_version', name) == PACK_VERSION, f'{name} is at another pack version'

# ---------------------------------------------------------------- roadmap ---
# The jurisdiction status, verbatim from ROADMAP.md: the block from the
# criterion's first line to its last. Located by structure (the bullet that
# names the jurisdiction overlay), never retyped.
def roadmap_quote():
    lines = ROADMAP.split('\n')
    start = next(i for i, l in enumerate(lines) if l.startswith('- A jurisdiction overlay validates end-to-end'))
    end = start + 1
    while end < len(lines) and lines[end].startswith('  '):
        end += 1
    return '\n'.join(lines[start:end]), start + 1, end


ROADMAP_QUOTE, RM_FROM, RM_TO = roadmap_quote()
assert 'deliberately left that way' in ROADMAP_QUOTE, 'ROADMAP.md jurisdiction status moved'
SURF_STATUS = need(need(FIN, 'honesty', 'finishes'), 'status', 'finishes#honesty')

# ------------------------------------------------------- surfaces per room ---
RULES = need(FIN, 'rules', 'finishes')
HAZARD_ROOMS_RULE = need(RULES, 'hazard_rooms', 'finishes#rules')
HAZARD_WALLS_RULE = need(RULES, 'hazard_walls', 'finishes#rules')
BASE_COND = need(FIN, 'base_conditions', 'finishes')
HAZ_COND = need(FIN, 'hazard_conditions', 'finishes')
FIN_HALLS = need(FIN, 'halls', 'finishes')
ROOM_STRANDS = list(BASE_COND.keys())


def merged_conditions(strand, hazard_keys):
    """surfaces.py's merge rule, applied again here to CHECK the registry's
    stored conditions (asserted equal below), so the ledger's PPE is the
    registries' and the recomputation is a test, not a second truth."""
    b = need(BASE_COND, strand, 'base_conditions')
    ppe = set(need(b, 'ppe', strand))
    for hz in hazard_keys:
        ppe |= set(need(need(HAZ_COND, hz, 'hazard_conditions'), 'ppe', hz))
    return sorted(ppe)


# ------------------------------------------------ the placard, structurally ---
# web/build_3d.py hangs a PPE placard at a room's door iff the merged
# condition record's ppe list is non-empty (`if (rc.ppe.length)` followed by a
# label of kind 'placard'), where rc = condOf(hall, strand) = the hall's
# condOver entry for the strand, else baseCond[strand]; and condOver holds a
# hall's conditions only for strands whose `hazards` list is non-empty. Each
# of those three facts is located in the file by regex; if any moves, this
# build fails rather than assuming.
def locate(pattern, who):
    m = re.search(pattern, BUILD_3D)
    assert m, f'web/build_3d.py: {who} not found by structure'
    return BUILD_3D[:m.start()].count('\n') + 1


PLACARD_STRUCTURE = {
    'hangs_when': {'line': locate(r"if \(rc\.ppe\.length\) \{\n\s*const plac = label\(rc\.ppe\.join", 'placard hang condition'),
                   'read': "if (rc.ppe.length) { const plac = label(rc.ppe.join(' · '), ..., { kind: 'placard', items: rc.ppe })"},
    'rc_is': {'line': locate(r"const rc = condOf\(h\.slug, r\.strand\);", 'rc = condOf'),
              'read': 'const rc = condOf(h.slug, r.strand);'},
    'condOf': {'line': locate(r"function condOf\(hallSlug, strand\) \{\n\s*return D\.condOver\[hallSlug\]\?\.\[strand\] \?{2} D\.baseCond\[strand\];", 'condOf'),
               'read': 'return D.condOver[hallSlug]?.[strand], else D.baseCond[strand]'},
    'condOver': {'line': locate(r"'condOver': \{sl: \{st: c for st, c in h\['conditions'\]\.items\(\)\n\s*if c\['hazards'\]\}", 'condOver'),
                 'read': "'condOver': {sl: {st: c for st, c in h['conditions'].items() if c['hazards']} for sl, h in finishes_reg['halls'].items() if any(...)}"},
    'rule': 'a room gets a door placard iff its merged condition record (hall conditions[strand] when that strand carries a hazard, '
            'else base_conditions[strand]) lists at least one PPE item; the placard shows that list',
}


def placard_for(slug, strand):
    cond = need(need(FIN_HALLS[slug], 'conditions', slug), strand, f'{slug} conditions')
    rc = cond if need(cond, 'hazards', f'{slug}.{strand}') else need(BASE_COND, strand, 'base_conditions')
    return {'hung': len(need(rc, 'ppe', strand)) > 0, 'items': list(rc['ppe'])}


# ------------------------------------------------------------- sign-off ---
def signoff_through_node():
    """Read through pack/hall_signoff.mjs exactly as bundles/build.py and
    web/build_map.py do: counting content_status strings here would be a
    second opinion about what a sign-off is."""
    script = (
        "const hs = await import('./pack/hall_signoff.mjs');"
        "const halls = JSON.parse(require('fs')"
        f"  .readFileSync('{PATHS['halls']}','utf8')).halls;"
        "const per = {};"
        "for (const h of halls) per[h.slug] = {claims: hs.claimsHallSignoff(h.content_status),"
        "  status: 'content_status' in h ? h.content_status : null,"
        "  problems: hs.validateHallContentStatus(h.slug, h)};"
        "console.log(JSON.stringify({halls: per, statuses: hs.HALL_CONTENT_STATUSES,"
        "  claiming: hs.HALL_CONTENT_STATUSES.filter((s) => hs.claimsHallSignoff(s)),"
        "  default_status: hs.HALL_CONTENT_STATUSES[0]}));")
    proc = subprocess.run(
        ['node', '--input-type=module', '-e',
         "import { createRequire } from 'node:module';"
         "const require = createRequire(process.cwd() + '/x.js');" + script],
        cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f'cannot read {PATHS["hall_signoff"]} through node:\n{proc.stderr}')
    return json.loads(proc.stdout)


SIGNOFF = signoff_through_node()
SIGN_HALLS = need(SIGNOFF, 'halls', 'signoff')
SIGN_DEFAULT = need(SIGNOFF, 'default_status', 'signoff')

# ------------------------------------------------------------- completion ---
EVIDENCE_CLASSES = need(COMPLETION, 'evidence_classes', 'completion')
EVIDENCE_RULE = need(COMPLETION, 'evidence_rule', 'completion')
COMP_SIMS = need(COMPLETION, 'sims', 'completion')
STEP_KINDS = need(LESSONS, 'step_kinds', 'lessons')
OFF_ROOM = need(LESSONS, 'off_room_places', 'lessons')
LESSON_MAP = need(LESSONS, 'lessons', 'lessons')

# The three ledger classes. A record can carry a CHECKABLE mark for an item
# (evidenceable), a done mark that is the learner's word (self-reported), or
# nothing at all because the item is a fact about the bundle, not about the
# learner, or a step kind completion says it cannot evidence (not-recordable).
LEDGER_CLASSES = {
    'evidenceable': 'a tc-completion/1 record carries a mark the verifier checks against the registries: '
                    'a sim step\'s episode (sim, scenario, score, passed) and record.sims[id].passed; a walkaround or '
                    'advisor episode; a station id in record.stations; a crib district in record.tools with passed',
    'self-reported': 'a walk or placard step: the record carries done and no evidence; completion.json says done is the '
                     'learner\'s word, so this ledger cannot treat it as evidenced',
    'not-recordable': 'the item is a fact of the bundle (a room\'s required PPE, a hung placard, a hall\'s sign-off '
                      'status, a rubric axis) or a step kind completion.json says it cannot evidence; no field of a '
                      'tc-completion/1 record carries it',
}


def step_kind_ledger_class(kind):
    rule = need(EVIDENCE_RULE, kind, 'completion#evidence_rule')
    cls = need(rule, 'class', kind)
    if cls == 'episode-backed':
        ok = need(rule, 'evidenceable', kind)
        return ('evidenceable' if ok else 'not-recordable',
                need(rule, 'evidenceable_why', kind), cls)
    if cls == 'device-mark':
        return 'evidenceable', 'a device-local mark in ' + need(rule, 'from', kind) + ' - a mark, not a recorded episode', cls
    if cls == 'self-reported':
        return 'self-reported', need(rule, 'why_no_episode', kind), cls
    raise ValueError(f'completion.json evidence class {cls!r} is not one this ledger knows')


STEP_KIND_EVIDENCE = {}
for kind in STEP_KINDS:
    lc, why, cc = step_kind_ledger_class(kind)
    STEP_KIND_EVIDENCE[kind] = {'ledger_class': lc, 'completion_class': cc, 'why': why}

# --------------------------------------------------------------- seats ---
SIM_MAP = need(SIMS, 'sims', 'sims')
HALL_BINDINGS = need(SIMS, 'hall_bindings', 'sims')
SEATS = {}
for sid, S in SIM_MAP.items():
    axes = []
    for a in need(S, 'rubric', sid):
        p = need(a, 'pass', f'{sid} rubric')
        axes.append({'axis': need(a, 'axis', f'{sid} rubric'), 'measure': need(a, 'measure', f'{sid} rubric'),
                     'pass': p, 'gates': p != 'informational'})
    comp_axes = need(COMP_SIMS[sid], 'rubric_axes', sid)
    assert [(a['axis'], a['pass']) for a in axes] == [(a['axis'], a['pass']) for a in comp_axes], f'{sid}: completion.json rubric drifted'
    SEATS[sid] = {'name': need(S, 'name', sid), 'halls': list(need(S, 'halls', sid)), 'axes': axes,
                  'gating_axes': sum(1 for a in axes if a['gates']),
                  'informational_axes': sum(1 for a in axes if not a['gates']),
                  'every_axis_gates': all(a['gates'] for a in axes),
                  'threshold': need(COMP_SIMS[sid], 'threshold', sid),
                  'evidence': {'ledger_class': 'evidenceable',
                               'carried_as': 'record.sims[id].passed (the page marks it from the axes) and a sim step\'s '
                                             'episode {sim, scenario, score, passed}',
                               'axes_are_the_rule_not_the_evidence': 'the record carries passed, not the axes; which axes '
                                                                     'decided it is the seat\'s rule in sims.json, not '
                                                                     'anything the record evidences'}}

# -------------------------------------------------------------- per hall ---
HALL_ORDER = [need(h, 'slug', 'hall') for h in need(HALLS, 'halls', 'halls')]
HALL_NAMES = {need(h, 'slug', 'hall'): need(h, 'name', 'hall') for h in HALLS['halls']}
assert sorted(HALL_ORDER) == sorted(FIN_HALLS.keys()), 'halls.json and finishes.json disagree on the hall set'
assert sorted(HALL_ORDER) == sorted(SIGN_HALLS.keys()), 'hall_signoff read another hall set'

LESSONS_BY_HALL = {}
for lid, L in LESSON_MAP.items():
    LESSONS_BY_HALL.setdefault(need(L, 'hall', lid), []).append(lid)

LEDGER = {}
ITEM_TALLY = {'evidenceable': 0, 'self-reported': 0, 'not-recordable': 0}
for slug in HALL_ORDER:
    H = FIN_HALLS[slug]
    hazards = list(need(H, 'hazards', slug))
    conds = need(H, 'conditions', slug)
    rooms = {}
    for strand in ROOM_STRANDS:
        c = need(conds, strand, f'{slug} conditions')
        governing = list(need(c, 'hazards', f'{slug}.{strand}'))
        assert set(governing) <= set(hazards), f'{slug}.{strand}: governs a hazard the hall does not carry'
        for hz in governing:
            assert strand in need(HAZARD_ROOMS_RULE, hz, 'rules.hazard_rooms'), f'{slug}.{strand}: {hz} governs a room rules.hazard_rooms does not name'
        ppe = list(need(c, 'ppe', f'{slug}.{strand}'))
        assert ppe == merged_conditions(strand, governing), f'{slug}.{strand}: stored ppe is not base ∪ hazards'
        base_ppe = list(need(BASE_COND[strand], 'ppe', strand))
        plac = placard_for(slug, strand)
        wall = need(need(H, 'walls', slug), strand, f'{slug} walls')
        rooms[strand] = {
            'hazards': governing,
            'hazard_room': bool(governing),
            'ppe': ppe,
            'ppe_from_hazards': sorted(set(ppe) - set(base_ppe)),
            'ppe_from_base': sorted(set(ppe) & set(base_ppe)),
            'wall_placed_by_hazard': need(wall, 'placed_by', f'{slug}.{strand} wall') == 'hazard',
            'placard': plac,
            'evidence': {'ledger_class': 'not-recordable',
                         'why': 'the required PPE and the hung placard are facts of the bundle; a placard step in a lesson '
                                'is self-reported (' + STEP_KIND_EVIDENCE['placard']['why'] + ')'},
        }
        ITEM_TALLY['not-recordable'] += 1
    hazard_rooms = [s for s in ROOM_STRANDS if rooms[s]['hazard_room']]
    # every hazard room has a placard iff its merged ppe is non-empty; a hazard
    # always adds PPE in this registry, but the ledger checks rather than assumes
    placard_every_hazard_room = all(rooms[s]['placard']['hung'] for s in hazard_rooms)

    seats = []
    for b in (need(HALL_BINDINGS, slug, 'hall_bindings') if slug in HALL_BINDINGS else []):
        sid = need(b, 'sim', f'{slug} binding')
        assert slug in SEATS[sid]['halls'], f'{slug}: bound to {sid} which does not list it'
        seats.append({'sim': sid, 'skill_id': need(b, 'skill_id', f'{slug} binding'),
                      'every_axis_gates': SEATS[sid]['every_axis_gates'], 'gating_axes': SEATS[sid]['gating_axes']})
        ITEM_TALLY['evidenceable'] += 1

    sign = SIGN_HALLS[slug]
    signoff = {
        'claims_signoff': need(sign, 'claims', slug),
        'content_status': need(sign, 'status', slug),
        'status_read': (need(sign, 'status', slug) if need(sign, 'status', slug) is not None
                        else SIGN_DEFAULT + ' (content_status absent: inherits the global caveat)'),
        'problems': need(sign, 'problems', slug),
        'read_through': PATHS['hall_signoff'],
        'evidence': {'ledger_class': 'not-recordable',
                     'why': 'a sign-off is the hall\'s fact, made by a named practitioner on a date in halls.json; a '
                            'learner\'s record has no field for it'},
    }
    ITEM_TALLY['not-recordable'] += 1

    lessons = []
    for lid in (LESSONS_BY_HALL[slug] if slug in LESSONS_BY_HALL else []):
        L = LESSON_MAP[lid]
        steps = need(L, 'steps', lid)
        placard_rooms = sorted({need(s, 'where', lid) for s in steps if need(s, 'kind', lid) == 'placard'})
        walked = sorted({need(s, 'where', lid) for s in steps if need(s, 'where', lid) not in OFF_ROOM})
        for w in walked:
            assert w in ROOM_STRANDS, f'{lid}: step where={w} is neither a room strand nor an off-room place'
        gaps = [s for s in hazard_rooms if s in walked and s not in placard_rooms]
        not_walked = [s for s in hazard_rooms if s not in walked]
        step_classes = {}
        for s in steps:
            k = need(s, 'kind', lid)
            lc = STEP_KIND_EVIDENCE[k]['ledger_class']
            step_classes[lc] = (step_classes[lc] if lc in step_classes else 0) + 1
            ITEM_TALLY[lc] += 1
        lessons.append({
            'lesson': lid, 'title': need(L, 'title', lid), 'steps': len(steps),
            'rooms_walked': walked,
            'placard_steps_in': placard_rooms,
            'hazard_rooms_of_hall': hazard_rooms,
            'placard_step_in_every_hazard_room': all(s in placard_rooms for s in hazard_rooms),
            'hazard_rooms_walked_without_placard_step': gaps,
            'hazard_rooms_not_walked': not_walked,
            'steps_by_ledger_class': {k: (step_classes[k] if k in step_classes else 0) for k in LEDGER_CLASSES},
            'step_kinds': [{'n': need(s, 'n', lid), 'kind': need(s, 'kind', lid), 'where': need(s, 'where', lid),
                            'ledger_class': STEP_KIND_EVIDENCE[need(s, 'kind', lid)]['ledger_class']} for s in steps],
        })

    LEDGER[slug] = {
        'name': HALL_NAMES[slug],
        'hazards': hazards,
        'hazard_rooms': hazard_rooms,
        'ppe_required_anywhere': sorted({p for r in rooms.values() for p in r['ppe']}),
        'ppe_from_hazards_anywhere': sorted({p for r in rooms.values() for p in r['ppe_from_hazards']}),
        'rooms': rooms,
        'placard_in_every_hazard_room': placard_every_hazard_room,
        'placards_hung': sum(1 for r in rooms.values() if r['placard']['hung']),
        'seats': seats,
        'signoff': signoff,
        'lessons': lessons,
        'lesson_covers_every_hazard_room': any(l['placard_step_in_every_hazard_room'] for l in lessons) if hazard_rooms else None,
    }

# ---------------------------------------------------------------- rollups ---
ROLLUPS = {
    'halls': len(LEDGER),
    'halls_with_hazards': sum(1 for h in LEDGER.values() if h['hazards']),
    'halls_without_hazards': sum(1 for h in LEDGER.values() if not h['hazards']),
    'halls_with_ppe_required': sum(1 for h in LEDGER.values() if h['ppe_required_anywhere']),
    'halls_with_hazard_added_ppe': sum(1 for h in LEDGER.values() if h['ppe_from_hazards_anywhere']),
    'halls_with_placard_in_every_hazard_room': sum(1 for h in LEDGER.values() if h['hazards'] and h['placard_in_every_hazard_room']),
    'hazard_rooms': sum(len(h['hazard_rooms']) for h in LEDGER.values()),
    'hazard_rooms_with_placard': sum(1 for h in LEDGER.values() for s in h['hazard_rooms'] if h['rooms'][s]['placard']['hung']),
    'rooms': sum(len(h['rooms']) for h in LEDGER.values()),
    'rooms_with_placard': sum(h['placards_hung'] for h in LEDGER.values()),
    'halls_signed_off': sum(1 for h in LEDGER.values() if h['signoff']['claims_signoff']),
    'halls_with_signoff_problems': sum(1 for h in LEDGER.values() if h['signoff']['problems']),
    'halls_with_a_lesson': sum(1 for h in LEDGER.values() if h['lessons']),
    'halls_with_hazards_and_a_lesson': sum(1 for h in LEDGER.values() if h['hazards'] and h['lessons']),
    'halls_with_a_lesson_covering_every_hazard_room': sum(1 for h in LEDGER.values() if h['lesson_covers_every_hazard_room'] is True),
    'lessons': sum(len(h['lessons']) for h in LEDGER.values()),
    'lessons_with_a_hazard_room_walked_without_placard_step': sum(1 for h in LEDGER.values() for l in h['lessons'] if l['hazard_rooms_walked_without_placard_step']),
    'halls_with_a_seat': sum(1 for h in LEDGER.values() if h['seats']),
    'seat_bindings': sum(len(h['seats']) for h in LEDGER.values()),
    'seats': len(SEATS),
    'seats_every_axis_gates': sum(1 for s in SEATS.values() if s['every_axis_gates']),
    'seats_with_an_informational_axis': sum(1 for s in SEATS.values() if not s['every_axis_gates']),
    'seats_with_scalar_threshold': sum(1 for s in SEATS.values() if s['threshold'] is not None),
    'items_by_ledger_class': dict(ITEM_TALLY),
    'items': sum(ITEM_TALLY.values()),
}
assert ROLLUPS['halls_with_hazards'] + ROLLUPS['halls_without_hazards'] == ROLLUPS['halls']
assert ROLLUPS['seats_every_axis_gates'] + ROLLUPS['seats_with_an_informational_axis'] == ROLLUPS['seats']
assert ROLLUPS['halls_signed_off'] == 0, 'a hall claims sign-off: ROADMAP.md criterion 1 has moved; re-read it before shipping this ledger'

# ---------------------------------------------------------------- fixture ---
def node_digest(record):
    """The digest through completion/verify.mjs's own digestOf - one truth."""
    proc = subprocess.run(
        ['node', '--input-type=module', '-e',
         "import { digestOf } from './completion/verify.mjs';"
         "let s=''; process.stdin.setEncoding('utf8'); for await (const c of process.stdin) s+=c;"
         "process.stdout.write(digestOf(JSON.parse(s)));"],
        cwd=str(ROOT), capture_output=True, text=True, input=json.dumps(record))
    if proc.returncode != 0:
        raise RuntimeError('completion/verify.mjs digestOf failed:\n' + proc.stderr)
    return proc.stdout.strip()


GOOD = json.load(open(ROOT / PATHS['completion_fixture']))
mut = copy.deepcopy(GOOD)
plac = next((lesson, st) for lesson in mut['lessons'] for st in lesson['steps'] if st['kind'] == 'placard' and st['done'])
plac[1]['evidence'] = {'episode': 'placard', 't': BUILT + 'T03:00:00.000Z', 'hall': plac[0]['hall']}
mut['digest']['hex'] = node_digest(mut)
MUTANTS = {'placard-claimed-evidenced': ('evidence.self-reported-carries-none', mut)}

REGISTRY = {
    'pack': 'smartcitix-trade-craft-academy-compliance',
    'product': PRODUCT,
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': STAMPS['self'],
    'stamps': STAMPS,
    'stamped_paths': PATHS,
    'provenance': 'DERIVED',
    'what_this_is': 'This ledger is not a code reference and cites no jurisdiction: it lists what the bundle\'s own rules '
                    'require of a hall and its rooms, and what a tc-completion/1 record can evidence of them. Every '
                    'number is computed from the stamped inputs; none is typed.',
    'jurisdiction': {
        'named': None,
        'why_none': 'the values in surfaces/registry/finishes.json are ' + SURF_STATUS,
        'roadmap_status_verbatim': ROADMAP_QUOTE,
        'roadmap_status_lines': [RM_FROM, RM_TO],
        'quote_marker': 'VERBATIM-ROADMAP-QUOTE: the only place a jurisdiction or standard is named in this registry, '
                        'and only because the roadmap names them as what this sandbox must NOT type',
    },
    'honesty': {
        'is': ['the bundle\'s internal compliance ledger: what its own registries require and what its own record format can evidence'],
        'is_not': ['a code reference', 'a jurisdiction overlay', 'a certification', 'an inspection', 'an accreditation'],
        'signoff': 'no hall\'s content is signed off by a practitioner today (read through pack/hall_signoff.mjs); every hall inherits the global caveat',
        'signature': 'a signed record attests a key, not a person (completion.json#signature)',
        'self_reported': 'a walk or placard step is the learner\'s word: it cannot be evidenced by any record',
    },
    'placard_rule': PLACARD_STRUCTURE,
    'ledger_classes': LEDGER_CLASSES,
    'evidence_classes': EVIDENCE_CLASSES,
    'step_kind_evidence': STEP_KIND_EVIDENCE,
    'signoff_statuses': {'closed_set': need(SIGNOFF, 'statuses', 'signoff'), 'claiming': need(SIGNOFF, 'claiming', 'signoff'),
                         'absent_means': SIGN_DEFAULT},
    'seats': SEATS,
    'halls': LEDGER,
    'rollups': ROLLUPS,
    'verifier': {'run': 'node compliance/verify.mjs <record.json>',
                 'rules': ['ledger.stamps', 'ledger.ppe-derived', 'ledger.placard-structural', 'ledger.signoff',
                           'ledger.rubric', 'ledger.rollups', 'evidence.self-reported-carries-none',
                           'evidence.seat-passed-in-record']},
    'fixture': {'good': 'fixture/good.json', 'good_from': PATHS['completion_fixture'],
                'report': 'fixture/report.txt',
                'mutants': {f'fixture/mutant-{n}.json': rule for n, (rule, _m) in MUTANTS.items()},
                'registry_mutants_in_test': ['ppe-typed-for-room-without', 'hall-marked-signed-off',
                                             'rubric-axis-invented-pass', 'stale-stamp']},
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(REGISTRY, indent=1, ensure_ascii=False) + '\n')
FIX.mkdir(parents=True, exist_ok=True)
(FIX / 'good.json').write_text(json.dumps(GOOD, indent=1, ensure_ascii=False) + '\n')
for n, (_r, m) in MUTANTS.items():
    (FIX / f'mutant-{n}.json').write_text(json.dumps(m, indent=1, ensure_ascii=False) + '\n')
rep = subprocess.run(['node', 'compliance/verify.mjs', 'compliance/fixture/good.json'], cwd=str(ROOT), capture_output=True, text=True)
if rep.returncode != 0:
    raise RuntimeError('the fixture does not verify:\n' + rep.stdout + rep.stderr)
(FIX / 'report.txt').write_text(rep.stdout)
R = ROLLUPS
print(f'compliance/registry/compliance.json: {R["halls"]} halls, {R["halls_with_hazards"]} with hazards, '
      f'{R["hazard_rooms"]} hazard rooms ({R["hazard_rooms_with_placard"]} with a placard), {R["halls_signed_off"]} signed off, '
      f'{R["seats"]} seats ({R["seats_every_axis_gates"]} with every axis gating), {R["items"]} items '
      f'{R["items_by_ledger_class"]} (source stamp {STAMPS["self"]})')
