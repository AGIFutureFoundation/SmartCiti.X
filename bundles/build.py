#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the sellable-package registry builder.

WHY THIS FILE EXISTS. The bundle is one enormous thing: a hall for every
trade in the taxonomy, a ladder cell for every strand and tier of every one
of them, a roster of simulator seats and a handful of walkable lessons. No
employer buys that. A contractor buys "the seats and the strand my crew
actually touches, for the people I have, starting next month", and until now
nothing in this tree expressed a subset of the bundle at all — so nothing
could be scoped, quoted or argued with.

A PACKAGE IS A FILTER, NOT A LIST. Every package below declares WHO it is
for and a filter over the registries: which trades, which strands, which
tiers, which seats. Its contents are RESOLVED at build time from
`pack/registry/skills.json`, `sims/registry/sims.json` and
`lessons/registry/lessons.json`. Nothing is typed. A filter that resolves to
no hall, no ladder cell, or to a named seat that its own trades never reach,
FAILS THE BUILD BY NAME rather than shipping an empty box with a nice title.
That is the whole design: a package cannot claim to contain something the
bundle does not have, because a package never says what it contains.

HOURS ARE NOT DECLARED ANYWHERE, SO THIS PACK DOES NOT STATE ANY. A buyer's
second question after "what is in it" is "how long does it take", and the
honest answer is that no registry in this bundle declares a duration for a
lesson step, a seat run, a scenario or a ladder cell. There is no field to
read. So `size.contact_hours` is null in every package, the reason is
published beside it, and the claim is made CHECKABLE rather than asserted:
this build rescans the registries it reads for a duration-shaped field and
fails if it finds one, because the moment a duration exists, a null here
stops being honest and becomes stale. An invented hour count would be the
single worst thing that could appear in this file — a contractor would plan
a crew's week around it.

SEAT COVERAGE TRAVELS WITH EVERY PACKAGE. `sims/registry/sims.json`
publishes what the seats reach and what they do not; each package carries
the same truth narrowed to its own scope: how many of its ladder cells
actually carry a seat, and how many of those cells sit on a prerequisite
chain with no seat anywhere in it. The unreachable list is READ from the
sims registry rather than recomputed into a second opinion — but this build
also re-derives it from the skill graph and refuses to run if the two
disagree, so reading is not the same as trusting.

NOTHING HERE CERTIFIES ANYBODY. No package is a qualification, a ticket or a
licence, no package can be sold as one, and the per-hall practitioner
sign-off count is read through `pack/hall_signoff.mjs` rather than typed —
it is zero, and no package may imply otherwise.

PROVENANCE. The filters and the buyer-facing sentences are AUTHORED: written
here, by us, arguable. The contents and every count are DERIVED: resolved
from the registries named in `reads`. Nothing in this pack is generated and
nothing is fetched.
"""
import hashlib
import json
import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

# The registries this pack resolves against, named by their repo-relative
# paths on purpose: a package's contents are only as honest as the files
# they came out of, so the file says which files those are and `reads`
# publishes the same list for a reader.
SKILLS_PATH = 'pack/registry/skills.json'
SIMS_PATH = 'sims/registry/sims.json'
LESSONS_PATH = 'lessons/registry/lessons.json'
UNIONS_PATH = 'unions/registry/unions.json'
HALLS_PATH = 'pack/registry/halls.json'
MANIFEST_PATH = 'pack/manifest.json'
SIGNOFF_PATH = 'pack/hall_signoff.mjs'

BUILT = '2026-09-24'


def need(d, k, where):
    """Read a required field, or fail by name.

    §23.1: a default is a policy decision. There is no `.get(k, default)` and
    no bare `??` anywhere in this file — a missing registry field is a
    registry that changed shape, and quietly substituting a value for it is
    this generator deciding what somebody else's pack meant.
    """
    if not isinstance(d, dict):
        raise TypeError(f'{where}: expected an object to read {k!r} from, '
                        f'got {type(d).__name__}')
    if k not in d:
        raise KeyError(f'{where}: required field {k!r} is missing')
    return d[k]


def load(rel):
    return json.load(open(ROOT / rel))


# ------------------------------------------------------------- registries ---
skills_reg = load(SKILLS_PATH)
sims_reg = load(SIMS_PATH)
lessons_reg = load(LESSONS_PATH)
unions_reg = load(UNIONS_PATH)
halls_reg = load(HALLS_PATH)
manifest = load(MANIFEST_PATH)

PACK_VERSION = need(manifest, 'pack_version', MANIFEST_PATH)
for _rel, _doc in ((SIMS_PATH, sims_reg), (LESSONS_PATH, lessons_reg),
                   (UNIONS_PATH, unions_reg), (HALLS_PATH, halls_reg)):
    if need(_doc, 'pack_version', _rel) != PACK_VERSION:
        raise AssertionError(
            f'{_rel}: pack_version disagrees with {MANIFEST_PATH}')

SKILL_ROWS = need(skills_reg, 'skills', SKILLS_PATH)
if need(skills_reg, 'count', SKILLS_PATH) != len(SKILL_ROWS):
    raise AssertionError(f'{SKILLS_PATH}: count disagrees with the records')
UNIONS = need(unions_reg, 'unions', UNIONS_PATH)
SIMS = need(sims_reg, 'sims', SIMS_PATH)
BINDINGS = need(sims_reg, 'hall_bindings', SIMS_PATH)
LESSONS = need(lessons_reg, 'lessons', LESSONS_PATH)

BY_ID = {need(s, 'skill_id', SKILLS_PATH): s for s in SKILL_ROWS}
DISTRICT_OF = {need(u, 'slug', UNIONS_PATH): need(u, 'district', UNIONS_PATH)
               for u in UNIONS}
HALLS_IN_DISTRICT = {}
for _slug, _d in DISTRICT_OF.items():
    HALLS_IN_DISTRICT.setdefault(_d, []).append(_slug)
STRANDS = sorted({need(s, 'strand', SKILLS_PATH) for s in SKILL_ROWS})
TIERS = sorted({need(s, 'tier', SKILLS_PATH) for s in SKILL_ROWS})

# Which cell each bound seat proves, inverted out of the sims registry's own
# bindings table: cell -> the seats that name it. Several seats land on one
# cell, because a seat's strand and tier are properties of the MACHINE and
# not of the hall, and a package that let four seats flatter one covered cell
# would be selling the same rung four times.
SEATS_ON_CELL = {}
for _hall, _list in BINDINGS.items():
    for _b in _list:
        _cell = need(_b, 'skill_id', f'{SIMS_PATH}#hall_bindings.{_hall}')
        SEATS_ON_CELL.setdefault(_cell, []).append(
            need(_b, 'sim', f'{SIMS_PATH}#hall_bindings.{_hall}'))

# Lessons, indexed by the ladder cell they stand on. A lesson is the only
# thing in this bundle a learner WALKS, so it is what a package's "steps"
# figure counts; a package with none says so rather than rounding up.
LESSON_CELLS = {}
for _lid, _les in LESSONS.items():
    LESSON_CELLS.setdefault(need(_les, 'skill_id', f'{LESSONS_PATH}#{_lid}'),
                            []).append(_lid)


# ------------------------------------------------- is a duration declared ---
# The claim "no registry declares a duration" is only worth making if it is
# checked. A registry declares a duration by CARRYING A FIELD for one, so
# this walks the keys of every registry this pack reads and fails if any of
# them names a length of time. Values are deliberately not scanned: a rubric
# that measures "seconds first dig to last dump" is describing a stopwatch
# inside a simulator run, not declaring how long a course takes, and a scan
# that confused the two would either cry wolf or invent a syllabus hour out
# of a sentence.
DURATION_KEY = re.compile(
    r'minute|hour|duration|seat_time|contact_time|weeks?\b|days?\b|elapsed',
    re.IGNORECASE)


def duration_keys(doc, where):
    """Every key path in `doc` that names a length of time."""
    found = []
    if isinstance(doc, dict):
        for k, v in doc.items():
            if DURATION_KEY.search(k):
                found.append(f'{where}.{k}')
            found += duration_keys(v, f'{where}.{k}')
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            found += duration_keys(v, f'{where}[{i}]')
    return found


DURATION_SCANNED = [SKILLS_PATH, SIMS_PATH, LESSONS_PATH, UNIONS_PATH,
                    HALLS_PATH, MANIFEST_PATH]
_declared = []
for _rel in DURATION_SCANNED:
    _declared += duration_keys(load(_rel), _rel)
if _declared:
    raise AssertionError(
        'a registry now declares a duration (' + ', '.join(_declared) + '), so '
        'this pack must DERIVE contact hours from it instead of publishing '
        'null — a stale null is a lie the moment the field exists')


# ------------------------------------------------ who has vouched for what --
def signed_off_halls():
    """The per-hall practitioner sign-off count, through the module that owns
    the rule. Counting `content_status` strings here would be a second
    opinion about what a sign-off is; `claimsHallSignoff()` is the only thing
    that decides, exactly as web/build_ladder.py reads it."""
    script = (
        "const hs = await import('./pack/hall_signoff.mjs');"
        "const halls = JSON.parse(require('fs')"
        f"  .readFileSync('{HALLS_PATH}','utf8')).halls;"
        "console.log(JSON.stringify({"
        "  signed: halls.filter((h) => hs.claimsHallSignoff(h.content_status)).length,"
        "  of: halls.length }));")
    proc = subprocess.run(
        ['node', '--input-type=module', '-e',
         "import { createRequire } from 'node:module';"
         "const require = createRequire(process.cwd() + '/x.js');" + script],
        cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f'cannot read {SIGNOFF_PATH} through node:\n'
                           + proc.stderr.strip())
    return json.loads(proc.stdout)


SIGNOFF = signed_off_halls()


# ---------------------------------------------------- the packages, declared -
# Each entry is a BUYER and a FILTER. Nothing below names a ladder cell, a
# lesson or a count; every one of those is resolved underneath. `trades` is
# either an explicit list of halls or a list of districts expanded from
# unions/registry/unions.json, `seats` is either the seats the resolved cells
# happen to carry or an explicit short list of the ones a crew actually
# touches — and a named seat its own trades never reach fails the build.
PACKAGES = {
    'lift-and-signal-crew': {
        'name': 'Lift & Signal Crew',
        'who': 'a contractor putting a crane crew on a structural job: the '
               'operator, the signalperson and the connectors who work under '
               'the hook.',
        'why': 'the four seats a lift crew touches on the same pick - the '
               'chart before the lift, the hands that call it, the machine '
               'that makes it and the shop crane that moves what comes off '
               'the truck - with the coordination and safety rungs beside '
               'the machine rung rather than underneath it.',
        'limits': 'this is practice on schematic seats and a ladder to '
                  'practise against. It qualifies nobody to rig, signal or '
                  'operate a crane, it is not seat time toward anything, and '
                  'the hall that would sign a rigger off has not reviewed a '
                  'line of it.',
        'filter': {
            'trades': {'kind': 'halls',
                       'ids': ['riggers', 'crane-ops', 'ironworkers',
                               'steel-erectors', 'port-crane']},
            'strands': ['machines', 'coordination', 'safety'],
            'tiers': ['fundamentals', 'applied'],
            'seats': {'kind': 'named',
                      'ids': ['crane-lift', 'rigging-signals', 'load-chart',
                              'overhead-crane']},
        },
    },
    'trench-and-locate': {
        'name': 'Trench & Locate',
        'who': 'a civil or utility contractor whose crews dig where somebody '
               'else\'s services already are.',
        'why': 'one seat and the strand it lives on: cutting to grade cell by '
               'cell while a flagged crossing stops the bucket shallow, with '
               'the procedure and safety rungs of the four halls that dig, '
               'shore and break out.',
        'limits': 'a schematic trench on a keyboard is not a locate, not a '
                  'competent-person assessment and not excavation training '
                  'anybody can sign. Nothing here speaks for a locate '
                  'authority or a jurisdiction.',
        'filter': {
            'trades': {'kind': 'halls',
                       'ids': ['operating-eng', 'shoring', 'laborers',
                               'demolition']},
            'strands': ['machines', 'safety', 'procedure'],
            'tiers': ['fundamentals', 'applied'],
            'seats': {'kind': 'named', 'ids': ['excavator-trench']},
        },
    },
    'hot-work-bay': {
        'name': 'Hot Work Bay',
        'who': 'a fabricator or shipyard training a bench of welders, and the '
               'inspection habit that has to travel with them.',
        'why': 'the bead bench - full fusion, gap inside the band, no '
               'burn-through - with the inspection and safety rungs of every '
               'hall that runs a seam, from deck plate to tank shell.',
        'limits': 'no weld procedure, no qualification and no test coupon. A '
                  'welder is qualified by a test to a procedure, witnessed by '
                  'somebody with the standing to witness it, and this bundle '
                  'is none of those things and speaks for none of them.',
        'filter': {
            'trades': {'kind': 'halls',
                       'ids': ['welders', 'boilermakers', 'shipfitters',
                               'fabricators', 'pipeline', 'marine-pipe',
                               'tank-erectors']},
            'strands': ['machines', 'safety', 'inspection'],
            'tiers': ['fundamentals', 'applied'],
            'seats': {'kind': 'named', 'ids': ['weld-bead']},
        },
    },
    'access-at-height': {
        'name': 'Access at Height',
        'who': 'a general contractor whose trades all get to the work the '
               'same two ways: up a scaffold bay or out of a basket.',
        'why': 'the two access seats every envelope and systems trade shares '
               '- the legal build order of a bay, and a boom lift flown '
               'tied-off, inside its moment envelope and out of the overhead '
               'line - across the halls that stand on them.',
        'limits': 'a schematic bay and a schematic basket. Nothing here is a '
                  'scaffold tag, a competent-person appointment, an aerial '
                  'platform card or a fall-protection qualification, and '
                  'building a bay in a browser signs nothing.',
        'filter': {
            'trades': {'kind': 'halls',
                       'ids': ['scaffold', 'carpenters', 'roofers', 'glaziers',
                               'window-glazing', 'painters', 'insulators',
                               'sheetmetal', 'electricians']},
            'strands': ['machines', 'safety', 'procedure'],
            'tiers': ['fundamentals', 'applied'],
            'seats': {'kind': 'named', 'ids': ['scaffold-bay', 'boom-lift']},
        },
    },
    'coatings-and-containment': {
        'name': 'Coatings & Containment',
        'who': 'a coatings contractor who is judged on the finish and sued '
               'over the runoff.',
        'why': 'the two bench seats that share a panel and a standoff window '
               '- strip it without gouging the substrate, coat it without '
               'runs, holidays or overspray - and the containment that has to '
               'be set before either trigger is pulled.',
        'limits': 'containment practice on a schematic panel. It is not '
                  'hazardous-materials training, not a respirator fit test '
                  'and not a discharge permit; the hazmat rungs in the ladder '
                  'here carry no seat at all.',
        'filter': {
            'trades': {'kind': 'halls', 'ids': ['painters', 'laborers', 'hazmat']},
            'strands': ['machines', 'safety', 'materials'],
            'tiers': ['fundamentals', 'applied'],
            'seats': {'kind': 'named',
                      'ids': ['pressure-washer', 'airless-sprayer']},
        },
    },
    'yard-logistics': {
        'name': 'Yard Logistics',
        'who': 'a terminal, a plant or a builder\'s yard putting new drivers '
               'on a lift truck.',
        'why': 'one driving seat - the cone lane taken in order, the pallet '
               'picked square and set inside the bay - with the coordination '
               'and safety rungs of the halls that move material around a '
               'working yard.',
        'limits': 'a schematic yard run is not a powered-industrial-truck '
                  'evaluation and carries no operator authorisation. This '
                  'package also contains no walkable lesson: the seat and the '
                  'ladder are what is in the box.',
        'filter': {
            'trades': {'kind': 'halls',
                       'ids': ['teamsters', 'heavy-equip', 'marine-terminal',
                               'operating-eng', 'laborers']},
            'strands': ['machines', 'safety', 'coordination'],
            'tiers': ['fundamentals', 'applied'],
            'seats': {'kind': 'named', 'ids': ['forklift-run']},
        },
    },
    'shop-floor-move': {
        'name': 'Shop Floor Move',
        'who': 'a plant or fabrication shop where the bridge crane runs over '
               'people all day.',
        'why': 'the overhead crane seat - bridge then trolley, never the '
               'diagonal, nothing loaded over the pedestrian aisle - with the '
               'troubleshooting and safety rungs of the shop trades whose work '
               'arrives on that hook.',
        'limits': 'a schematic bay, a schematic pendant. No overhead-crane '
                  'operator authorisation, no rigging qualification and no '
                  'inspection record comes out of it.',
        'filter': {
            'trades': {'kind': 'halls',
                       'ids': ['millwrights', 'machinists', 'foundry',
                               'boilermakers', 'riggers', 'crane-ops']},
            'strands': ['machines', 'safety', 'troubleshooting'],
            'tiers': ['fundamentals', 'applied'],
            'seats': {'kind': 'named', 'ids': ['overhead-crane']},
        },
    },
    'one-hall-ladder': {
        'name': 'One Hall, Whole Ladder',
        'who': 'a single hall or a JATC that wants its own trade end to end '
               'rather than a slice across everybody\'s.',
        'why': 'one hall\'s complete ladder - every strand, every tier, the '
               'lessons that stand in its rooms and whatever seats its cells '
               'carry - which is also the honest way to see how much of a '
               'trade this bundle has actually built.',
        'limits': 'a whole ladder is not a whole apprenticeship. Most of the '
                  'cells in it carry no seat, no lesson and no assessment, '
                  'and the ones that do carry practice rather than proof.',
        'filter': {
            'trades': {'kind': 'halls', 'ids': ['scaffold']},
            'strands': STRANDS,
            'tiers': TIERS,
            'seats': {'kind': 'whatever-the-cells-carry', 'ids': []},
        },
    },
    'safety-first-rung': {
        'name': 'Safety, First Rung, Every Trade',
        'who': 'a multi-trade employer or an owner who wants one safety '
               'starting point across a whole workforce rather than a '
               'per-trade course.',
        'why': 'the first safety rung of every hall in the taxonomy, bought as '
               'one thing: the widest package this bundle can honestly offer, '
               'and the one that shows most plainly where the seats are not.',
        'limits': 'this package contains no simulator seat. Not one hall\'s '
                  'safety strand carries a seat in this bundle - every seat '
                  'that exists sits on a machines rung - so what is bought '
                  'here is a ladder and, in one hall, a lesson. It is not '
                  'safety training, not an orientation and not an induction.',
        'filter': {
            'trades': {'kind': 'districts',
                       'ids': sorted(HALLS_IN_DISTRICT)},
            'strands': ['safety'],
            'tiers': ['fundamentals'],
            'seats': {'kind': 'whatever-the-cells-carry', 'ids': []},
        },
    },
    'environmental-control': {
        'name': 'Environmental & Site Control',
        'who': 'a remediation or site-safety contractor staffing the trades '
               'that are called in because of a hazard rather than a build.',
        'why': 'one district bought whole - the control trades - on the three '
               'strands their work is actually judged on: the procedure they '
               'follow, the safety it exists for, and the documentation that '
               'is the only trace either one leaves.',
        'limits': 'this package contains no simulator seat: no control-trade '
                  'cell on these strands carries one. It is a ladder and its '
                  'lessons, and no line of it is a licence, an accreditation '
                  'or a competent-person appointment.',
        'filter': {
            'trades': {'kind': 'districts', 'ids': ['control']},
            'strands': ['procedure', 'safety', 'documentation'],
            'tiers': ['fundamentals', 'applied'],
            'seats': {'kind': 'whatever-the-cells-carry', 'ids': []},
        },
    },
}

SEAT_FILTER_KINDS = ('named', 'whatever-the-cells-carry')
TRADE_FILTER_KINDS = ('halls', 'districts')
# A claim word that must never appear in a package's buyer-facing prose
# except to refuse it. `limits` is where a package is allowed to say
# "certifies nobody"; a name, a buyer line or a pitch line that reached for
# one of these would be selling standing this bundle does not have.
CLAIM_WORDS = re.compile(
    r'certif|qualif|licen[cs]|accredit|\bticket\b|\bcard\b|\bapprove',
    re.IGNORECASE)


# -------------------------------------------- what the seats do NOT reach ---
# The sims registry publishes the seat-coverage truth for the whole bundle,
# including the list of bound cells whose entire prerequisite chain carries no
# seat. Every package carries that same truth narrowed to its own cells, and
# the list is READ from there rather than recomputed into a second opinion.
#
# Reading is not trusting, though. The closure is re-derived here from the
# skill graph and compared; if the two ever disagree, one of them is wrong and
# this build stops rather than picking a winner. Fixing a disagreement means
# fixing sims/build.py, not editing a number into this file.
COVERAGE = need(sims_reg, 'coverage', SIMS_PATH)
UNREACHABLE = need(COVERAGE, 'unreachable_seat_cells', f'{SIMS_PATH}#coverage')


def prereq_closure(cell):
    """Every cell `cell` transitively requires. Fails closed on a dangling
    prerequisite rather than treating it as no prerequisite at all."""
    seen, stack = set(), [cell]
    while stack:
        here = stack.pop()
        if here not in BY_ID:
            raise KeyError(f'{cell}: requires {here}, which {SKILLS_PATH} '
                           'does not declare')
        for req in need(BY_ID[here], 'requires', SKILLS_PATH):
            if req not in seen:
                seen.add(req)
                stack.append(req)
    return seen


_derived_unreachable = sorted(
    c for c in SEATS_ON_CELL
    if prereq_closure(c) and not (prereq_closure(c) & set(SEATS_ON_CELL)))
if _derived_unreachable != sorted(UNREACHABLE):
    raise AssertionError(
        f'{SIMS_PATH}#coverage.unreachable_seat_cells disagrees with the '
        'closure re-derived from ' + SKILLS_PATH + ': '
        f'{sorted(set(_derived_unreachable) ^ set(UNREACHABLE))}')
# The same cross-check for the figures a package's coverage block narrows.
if need(COVERAGE, 'cells', f'{SIMS_PATH}#coverage')['with_a_seat'] != len(SEATS_ON_CELL):
    raise AssertionError(f'{SIMS_PATH}#coverage.cells.with_a_seat disagrees '
                         'with hall_bindings counted again')

UNREACHABLE_SET = set(UNREACHABLE)


# --------------------------------------------------------- the resolution ---
def resolve(pid, decl):
    """Turn one package's filter into its contents, or fail by name."""
    where = f'bundles/build.py#PACKAGES.{pid}'
    filt = need(decl, 'filter', where)

    trades_f = need(filt, 'trades', f'{where}.filter')
    kind = need(trades_f, 'kind', f'{where}.filter.trades')
    ids = need(trades_f, 'ids', f'{where}.filter.trades')
    if kind not in TRADE_FILTER_KINDS:
        raise ValueError(f'{pid}: unknown trades filter kind {kind!r}')
    if kind == 'halls':
        for slug in ids:
            if slug not in DISTRICT_OF:
                raise ValueError(f'{pid}: names hall {slug!r}, which '
                                 f'{UNIONS_PATH} does not declare')
        halls = sorted(set(ids))
    else:
        for d in ids:
            if d not in HALLS_IN_DISTRICT:
                raise ValueError(f'{pid}: names district {d!r}, which '
                                 f'{UNIONS_PATH} does not declare')
        halls = sorted({h for d in ids for h in HALLS_IN_DISTRICT[d]})
    if not halls:
        raise ValueError(f'{pid}: the trades filter resolves to no hall')

    strands = need(filt, 'strands', f'{where}.filter')
    tiers = need(filt, 'tiers', f'{where}.filter')
    for s in strands:
        if s not in STRANDS:
            raise ValueError(f'{pid}: names strand {s!r}, which {SKILLS_PATH} '
                             'does not declare')
    for t in tiers:
        if t not in TIERS:
            raise ValueError(f'{pid}: names tier {t!r}, which {SKILLS_PATH} '
                             'does not declare')

    hallset = set(halls)
    cells = sorted(need(r, 'skill_id', SKILLS_PATH) for r in SKILL_ROWS
                   if need(r, 'union', SKILLS_PATH) in hallset
                   and need(r, 'strand', SKILLS_PATH) in strands
                   and need(r, 'tier', SKILLS_PATH) in tiers)
    if not cells:
        raise ValueError(f'{pid}: the filter resolves to no ladder cell - '
                         f'{len(halls)} halls x {len(strands)} strands x '
                         f'{len(tiers)} tiers found nothing in {SKILLS_PATH}')
    cellset = set(cells)

    # Which seats the resolved cells carry, and which of those this package
    # actually sells. A named seat that no resolved cell carries is a package
    # promising a seat its own trades never reach.
    on_cell = {c: sorted(set(SEATS_ON_CELL[c])) for c in cells if c in SEATS_ON_CELL}
    available = sorted({s for v in on_cell.values() for s in v})
    seats_f = need(filt, 'seats', f'{where}.filter')
    seat_kind = need(seats_f, 'kind', f'{where}.filter.seats')
    seat_ids = need(seats_f, 'ids', f'{where}.filter.seats')
    if seat_kind not in SEAT_FILTER_KINDS:
        raise ValueError(f'{pid}: unknown seats filter kind {seat_kind!r}')
    if seat_kind == 'named':
        if not seat_ids:
            raise ValueError(f'{pid}: a named seats filter names no seat')
        for sid in seat_ids:
            if sid not in SIMS:
                raise ValueError(f'{pid}: names seat {sid!r}, which '
                                 f'{SIMS_PATH} does not declare')
            if sid not in available:
                raise ValueError(
                    f'{pid}: names seat {sid!r}, which none of its resolved '
                    'ladder cells carries - the trades, strands or tiers this '
                    'package filters on do not reach that seat')
        seats = sorted(set(seat_ids))
    else:
        if seat_ids:
            raise ValueError(f'{pid}: a {seat_kind!r} seats filter must name '
                             'no seat, and this one names ' + ', '.join(seat_ids))
        seats = available
    seatset = set(seats)
    sold = {c: [s for s in v if s in seatset] for c, v in on_cell.items()}
    sold = {c: v for c, v in sold.items() if v}
    left_out = sorted(set(available) - seatset)

    lesson_ids = sorted(lid for c in cells for lid in LESSON_CELLS.get(c, []))
    steps = sum(len(need(LESSONS[lid], 'steps', f'{LESSONS_PATH}#{lid}'))
                for lid in lesson_ids)
    if not seats and not steps:
        raise ValueError(
            f'{pid}: resolves to a ladder of {len(cells)} cells with no seat '
            'and no lesson step on any of them - a package with nothing in it '
            'a crew can do is an empty box with a title on it')

    piled = sorted(c for c, v in sold.items() if len(v) > 1)
    scenarios = sum(len(need(SIMS[s], 'scenarios', f'{SIMS_PATH}#sims.{s}'))
                    for s in seats)

    return {
        'name': need(decl, 'name', where),
        'who': need(decl, 'who', where),
        'why': need(decl, 'why', where),
        'limits': need(decl, 'limits', where),
        'filter': filt,
        'contents': {
            'trades': halls,
            'ladder_cells': cells,
            'districts': sorted({DISTRICT_OF[h] for h in halls}),
            'strands': sorted(strands),
            'tiers': sorted(tiers),
            'seats': seats,
            'seat_names': [need(SIMS[s], 'name', f'{SIMS_PATH}#sims.{s}')
                           for s in seats],
            'lessons': lesson_ids,
        },
        'size': {
            'trades': len(halls),
            'ladder_cells': len(cells),
            'seats': len(seats),
            'seat_scenarios': scenarios,
            'lessons': len(lesson_ids),
            'lesson_steps': steps,
            # Not a number this bundle has. See `duration` below: no registry
            # read here declares a length of time for anything, so there is
            # nothing to derive an hour from and nothing is invented.
            'contact_hours': None,
        },
        'coverage': {
            'cells_with_a_seat': len(sold),
            'cells_carrying_more_than_one_seat': len(piled),
            'seats_absorbed_by_those_cells': sum(len(sold[c]) for c in piled),
            'seat_bindings': sum(len(v) for v in sold.values()),
            'unreachable_seat_cells': sorted(set(sold) & UNREACHABLE_SET),
            'reachable_seat_cells': sorted(set(sold) - UNREACHABLE_SET),
            'seats_on_these_cells_not_sold': left_out,
        },
        'signoff': {'practitioner_signed_off_halls': need(SIGNOFF, 'signed', SIGNOFF_PATH),
                    'of_halls_in_this_package': len(halls)},
    }


PACKS = {}
for _pid, _decl in PACKAGES.items():
    if not re.fullmatch(r'[a-z][a-z0-9-]+', _pid):
        raise ValueError(f'{_pid}: a package id is lower-case and hyphenated')
    PACKS[_pid] = resolve(_pid, _decl)

if not 6 <= len(PACKS) <= 12:
    raise AssertionError(f'{len(PACKS)} packages: this pack ships between 6 '
                         'and 12, few enough to read and enough to choose from')

# No package may be the whole bundle wearing a smaller name, and no package
# may reach for standing the bundle does not have in the words it is sold in.
for _pid, _p in PACKS.items():
    if _p['size']['ladder_cells'] >= len(SKILL_ROWS):
        raise AssertionError(f'{_pid}: resolves the whole ladder - that is the '
                             'product, not a package of it')
    for _field in ('name', 'who', 'why'):
        if CLAIM_WORDS.search(_p[_field]):
            raise AssertionError(
                f'{_pid}.{_field}: reaches for a claim word this bundle cannot '
                'back. A package is sold on what a crew practises; `limits` is '
                'the only place any of these words belongs, and only to refuse '
                'it')
    if _p['signoff']['practitioner_signed_off_halls'] != 0:
        raise AssertionError(
            f'{_pid}: a hall now claims practitioner sign-off. That is good '
            'news and this pack must say which hall rather than carry a zero')
    if _p['size']['seats'] == 0 and 'no simulator seat' not in _p['limits']:
        raise AssertionError(
            f'{_pid}: resolves no seat, and its limits do not say so. A '
            'package with no seat in it is sellable; one that hides it is not')

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

doc = {
    'pack': 'smartcitix-trade-craft-academy-bundles',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    'honesty': {
        'status': 'AUTHORED filters, DERIVED contents. Each package below is '
                  'a buyer and a filter written here, by us; everything it '
                  'contains is resolved at build time from the registries in '
                  '`reads`. No package names a ladder cell, a seat or a '
                  'lesson - which is why no package can claim to contain '
                  'something this bundle does not have.',
        'not_certification': 'no package here certifies, qualifies, licenses '
                             'or authorises anybody to do anything. Buying '
                             'every package in this registry would leave a '
                             'crew with exactly the standing it started with. '
                             'Where a trade has a real ticket, it is issued by '
                             'a jurisdiction, an employer or a hall, and this '
                             'bundle is none of those and speaks for none of '
                             'them.',
        'not_a_price': 'nothing here is a quote. This pack sizes a package - '
                       'trades, ladder cells, seats, scenarios, lesson steps - '
                       'so that a price can be argued about against something '
                       'real. It declares no price, no headcount, no term and '
                       'no seat licence, because no registry in this bundle '
                       'declares any of those either.',
        'not_a_syllabus': 'a package is a scope, not a plan. Nothing here '
                          'sequences a week, assigns a cohort or schedules a '
                          'crew; the ladder says what order the cells build '
                          'in, and that is the whole of the ordering this '
                          'pack has to offer.',
        'seat_coverage': 'every package carries the seat-coverage truth the '
                         'sims registry publishes, narrowed to its own cells '
                         'and never recomputed into a friendlier second '
                         'opinion. Most cells in most packages carry no seat, '
                         'and a cell with no seat is not partially covered - '
                         'it is uncovered, and it is counted that way.',
        'one_truth': 'this pack holds no second copy of anything. Hall names, '
                     'strand and tier vocabularies, seat names, scenario '
                     'counts, lesson steps, the unreachable-cell list and the '
                     'practitioner sign-off count are all read at build time '
                     'from the registries and modules that own them, and '
                     'bundles/test.mjs re-reads every one of them the same '
                     'way.',
        'not_built_yet': 'no page in this bundle draws these packages. This '
                         'registry is the data a scope or a quote would be '
                         'built from; nothing renders it, and saying so here '
                         'is cheaper than letting somebody discover it.',
    },
    # The buyer's second question, answered once and honestly rather than
    # guessed at ten times.
    'duration': {
        'declared': False,
        'contact_hours': None,
        'why': 'no registry this pack reads declares a length of time for '
               'anything: not a lesson, not a step, not a seat run, not a '
               'scenario, not a ladder cell. There is no field to derive an '
               'hour from, so every package publishes null rather than a '
               'number somebody would plan a crew\'s week around.',
        'checked': 'this is not an assertion, it is a scan: the build walks '
                   'the keys of every registry in `duration.registries_scanned` '
                   'looking for a field that names a length of time, and fails '
                   'if it finds one - because the moment a duration exists, a '
                   'null here stops being honest and starts being stale.',
        'registries_scanned': DURATION_SCANNED,
        'what_would_change_it': 'a duration declared by the pack that owns the '
                                'thing being timed - a step, a seat run or a '
                                'cell - and read from there. Not a number '
                                'typed into this file.',
    },
    'coverage_contract': {
        'source': f'{SIMS_PATH}#coverage',
        'means': 'a ladder cell is covered when at least one seat this package '
                 'sells names it, and a covered cell is REACHABLE when some '
                 'cell in its prerequisite closure is also covered. The '
                 'closure is walked over the WHOLE bundle\'s seats, not just '
                 'this package\'s, which is the kinder of the two readings: a '
                 'cell counted reachable here may be reachable only through a '
                 'seat some other package sells.',
        'honest': 'this is the ratio a training coordinator should read before '
                  'the package name. The seats that exist are deterministic '
                  'and their rubrics are real, and they stand on a ladder '
                  'whose lower rungs this bundle cannot prove. Every seat in '
                  'every package sits on a chain of prerequisites that carries '
                  'no seat at all, so nothing bought here can be earned from '
                  'the bottom up inside this bundle.',
        'seats_on_these_cells_not_sold': 'the seats a package\'s own cells '
                                         'carry that its filter leaves out. A '
                                         'buyer is entitled to know what was '
                                         'in reach and not included.',
    },
    'provenance': {
        'filters': 'AUTHORED',
        'buyer_prose': 'AUTHORED',
        'contents': 'DERIVED',
        'counts': 'DERIVED',
        'seat_coverage': 'DERIVED',
        'note': 'nothing in this pack is generated and nothing is fetched. '
                'The provenance word orbis/ uses for generated video appears '
                'nowhere in this pack and never will: it would be a false '
                'label for a filter somebody wrote and a count somebody '
                'resolved, and bundles/test.mjs checks for its absence.',
    },
    'packages': PACKS,
    'counts': {
        'packages': len(PACKS),
        'trades_offered': len({h for p in PACKS.values()
                               for h in p['contents']['trades']}),
        'seats_offered': len({s for p in PACKS.values()
                              for s in p['contents']['seats']}),
        'cells_offered': len({c for p in PACKS.values()
                              for c in p['contents']['ladder_cells']}),
        'lessons_offered': len({lid for p in PACKS.values()
                                for lid in p['contents']['lessons']}),
        'packages_with_no_seat': sum(1 for p in PACKS.values()
                                     if p['size']['seats'] == 0),
    },
    'reads': sorted([SKILLS_PATH, SIMS_PATH, LESSONS_PATH, UNIONS_PATH,
                     HALLS_PATH, MANIFEST_PATH, SIGNOFF_PATH]),
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'bundles.json').write_text(json.dumps(doc, indent=1) + '\n')

print(f'bundle registry: {len(PACKS)} packages resolved from '
      f'{len(doc["reads"])} registries (source stamp {stamp})')
for _pid, _p in PACKS.items():
    _c = _p['coverage']
    print(f'  {_pid}: {_p["size"]["trades"]} trades, '
          f'{_p["size"]["ladder_cells"]} ladder cells, {_p["size"]["seats"]} seats, '
          f'{_p["size"]["lesson_steps"]} lesson steps; '
          f'{_c["cells_with_a_seat"]} cells carry a seat, '
          f'{len(_c["unreachable_seat_cells"])} of those unreachable; '
          'contact hours undeclared')
