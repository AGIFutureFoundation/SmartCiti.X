#!/usr/bin/env python3
"""The training ladder: a hall's own skill graph, with the seats marked on it.

WHY THIS FILE EXISTS. `pack/registry/skills.json` holds a skill per hall per
strand per tier, each one naming its prerequisite, and
`sims/registry/sims.json` binds simulator seats to some of those skills
through `hall_bindings`. Both registries were readable and neither was
openable: no page a union member, a training coordinator or a JATC could
open drew the ladder, and no page said which rung of it a seat actually
stands on. This generator opens both and puts them on one page, per hall.

ONE TRUTH PER FACT. Every count on this page - halls, strands, tiers, cells,
prerequisite edges, seats, bound halls, covered cells, rubric axes - is READ
from the registry that owns it and computed here. There is no typed count
anywhere below, and `node brand/figures.mjs .` is the check that says so.
Every policy sentence about readiness, gating or certification is quoted
from `control/` rather than restated: `control/gates.mjs` and
`control/graph.mjs` are imported through node and their real constants and
real source expressions are carried onto the page, because a page that
paraphrases a policy module is a second opinion about it.

A missing field fails the build by name through `need()`. No `.get(k,
default)` anywhere in this file: a default substituted for a missing
registry field is this generator quietly deciding what a registry meant.

WHAT IT DRAWS, per hall, one hall at a time.
  - the limits first: what a passing seat run is evidence OF, and what it is
    not, in the registry's and the control plane's own words;
  - the ladder - the hall's cells laid out strand by strand and tier by
    tier, with every `requires` edge drawn as an edge and every `supports`
    and `interferes` edge drawn as its own kind of edge;
  - the seats: which cell each bound seat proves, that seat's rubric axes
    with their measures and pass bars, and a link straight into it;
  - the gaps, said as plainly as the coverage: every strand that carries no
    seat at all, counted from the same data the coverage badge is counted
    from;
  - the nine declared variants a cell's lessons come in, with the band
    offsets and scaffold ceilings the pack declares for them.

WHAT IT REFUSES TO DO. It renders no coverage number that is not a count of
the badges it actually drew - the covered-cell figure is read back out of
the rendered DOM, so it cannot be larger than the seats the registry binds.
It fails closed rather than drawing a seat on a cell the hall does not have,
or an edge to a skill the hall does not have. It claims no certification:
`control/gates.mjs` `certified()` is quoted on the page and nothing in this
bundle satisfies it. And it never calls anything here AI-SYNTHESIZED - that
word belongs to `orbis/` and describes generated video; the seats are
SCRIPTED and the pack is AUTHORED.
"""
import html
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402


def _root():
    for cand in (HERE, *HERE.parents):
        if (cand / 'pack').is_dir() and (cand / 'sims').is_dir() and (cand / 'control').is_dir():
            return cand
    raise RuntimeError('cannot locate the packs from ' + str(HERE))


ROOT = _root()

# The registries this page exists to open, named by their repo-relative paths
# on purpose: rnd/build.py scans the generators under web/ for exactly these
# strings, and a page that reads a registry without naming it would close the
# gap in the scan while leaving it open in the bundle.
SKILLS_PATH = 'pack/registry/skills.json'
SIMS_PATH = 'sims/registry/sims.json'
VARIANTS_PATH = 'pack/registry/variants.json'
HALLS_PATH = 'pack/registry/halls.json'
MANIFEST_PATH = 'pack/manifest.json'
GATES_PATH = 'control/gates.mjs'
GRAPH_PATH = 'control/graph.mjs'
SIGNOFF_PATH = 'pack/hall_signoff.mjs'
SEQUENCER_PATH = 'control/sequencer.mjs'
CURRICULUM_PATH = 'control/sim_curriculum.mjs'


def need(d, k, where):
    """Read a required field, or fail by name."""
    if not isinstance(d, dict):
        raise TypeError(f'{where}: expected an object to read {k!r} from, got {type(d).__name__}')
    if k not in d:
        raise KeyError(f'{where}: required field {k!r} is missing')
    return d[k]


def load(rel):
    return json.load(open(ROOT / rel))


# ---------------------------------------------------------------- registries
skills_reg = load(SKILLS_PATH)
sims_reg = load(SIMS_PATH)
variants_reg = load(VARIANTS_PATH)
halls_reg = load(HALLS_PATH)
manifest = load(MANIFEST_PATH)

PACK_VERSION = need(manifest, 'pack_version', MANIFEST_PATH)
PRODUCT = need(sims_reg, 'product', SIMS_PATH)
BUILT = need(sims_reg, 'built', SIMS_PATH)
if need(sims_reg, 'pack_version', SIMS_PATH) != PACK_VERSION:
    raise AssertionError(f'{SIMS_PATH}: pack_version disagrees with {MANIFEST_PATH}')
if need(halls_reg, 'pack_version', HALLS_PATH) != PACK_VERSION:
    raise AssertionError(f'{HALLS_PATH}: pack_version disagrees with {MANIFEST_PATH}')

SKILLS = need(skills_reg, 'skills', SKILLS_PATH)
if need(skills_reg, 'count', SKILLS_PATH) != len(SKILLS):
    raise AssertionError(f'{SKILLS_PATH}: count field disagrees with the number of records')

HALLS = need(halls_reg, 'halls', HALLS_PATH)
if need(halls_reg, 'count', HALLS_PATH) != len(HALLS):
    raise AssertionError(f'{HALLS_PATH}: count field disagrees with the number of records')
HALL_NAME = {need(h, 'slug', f'{HALLS_PATH}#halls[]'): need(h, 'name', f'{HALLS_PATH}#halls[]')
             for h in HALLS}
HALL_FOCUS = {need(h, 'slug', f'{HALLS_PATH}#halls[]'): need(h, 'focus', f'{HALLS_PATH}#halls[]')
              for h in HALLS}
HALL_ORDER = {need(h, 'slug', f'{HALLS_PATH}#halls[]'): need(h, 'index', f'{HALLS_PATH}#halls[]')
              for h in HALLS}

SIMS = need(sims_reg, 'sims', SIMS_PATH)
BINDINGS = need(sims_reg, 'hall_bindings', SIMS_PATH)
HONESTY = need(sims_reg, 'honesty', SIMS_PATH)
OPERATOR_LEVELS = need(sims_reg, 'operator_levels', SIMS_PATH)
SCORING_CONTRACT = need(sims_reg, 'scoring_contract', SIMS_PATH)
PACK_HONESTY = need(manifest, 'honesty', MANIFEST_PATH)


# -------------------------------------------- control/ constants, read not retyped
def node_dump():
    """Import the control modules and the sign-off module and dump what they export.

    Read rather than retyped, and read by IMPORTING rather than by pattern-
    matching the source: `control/gates.mjs` GATE, `control/graph.mjs`
    TRANSFER/INTERFERENCE and `pack/hall_signoff.mjs`'s closed status set are
    the bundle's own policy, and this page must state that policy or none.
    If node is unavailable the build fails here rather than shipping a page
    that invented its own numbers.
    """
    script = (
        "const g = await import('./control/gates.mjs');"
        "const gr = await import('./control/graph.mjs');"
        "const hs = await import('./pack/hall_signoff.mjs');"
        "const signed = ["
        "  ...JSON.parse(require('fs').readFileSync('pack/registry/halls.json','utf8')).halls"
        "].filter((h) => hs.claimsHallSignoff(h.content_status)).length;"
        "console.log(JSON.stringify({ GATE: g.GATE, ANTIGAMING: g.ANTIGAMING,"
        "  TRANSFER: gr.TRANSFER, INTERFERENCE: gr.INTERFERENCE,"
        "  statuses: hs.HALL_CONTENT_STATUSES, signed_off_halls: signed }));")
    proc = subprocess.run(
        ['node', '--input-type=module', '-e',
         "import { createRequire } from 'node:module';"
         "const require = createRequire(process.cwd() + '/x.js');" + script],
        cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f'cannot read {GATES_PATH} / {GRAPH_PATH} / {SIGNOFF_PATH} through node:\n'
            + proc.stderr.strip())
    return json.loads(proc.stdout)


CONTROL = node_dump()
GATE = need(CONTROL, 'GATE', GATES_PATH)
TRANSFER = need(CONTROL, 'TRANSFER', GRAPH_PATH)
INTERFERENCE = need(CONTROL, 'INTERFERENCE', GRAPH_PATH)
HALL_STATUSES = need(CONTROL, 'statuses', SIGNOFF_PATH)
SIGNED_OFF_HALLS = need(CONTROL, 'signed_off_halls', SIGNOFF_PATH)


def quote(rel, start, end):
    """One verbatim run of a source file, between two anchors, or fail by name.

    Used for the policy EXPRESSIONS and the governing sentences in
    `control/`: the page shows what the module actually says, so a reader
    comparing the two finds one text and not two. Fails closed - a moved
    anchor stops the build rather than dropping the quotation.
    """
    text = (ROOT / rel).read_text()
    i = text.find(start)
    if i < 0:
        raise LookupError(f'{rel}: cannot find the opening anchor {start!r}')
    j = text.find(end, i + len(start))
    if j < 0:
        raise LookupError(f'{rel}: cannot find the closing anchor {end!r} after {start!r}')
    run = text[i:j + len(end)]
    run = re.sub(r'\n\s*\*\s?', ' ', run)
    return re.sub(r'\s+', ' ', run).strip()


# The three policy texts the page quotes instead of paraphrasing.
GATES_RULE = quote(GATES_PATH, 'The rule that shapes everything here:',
                   'not what was inferred.')
GRAPH_RULE = quote(GRAPH_PATH, 'Governing rule', 'about them.')
CERTIFIED_EXPR = quote(GATES_PATH, 'return skillGates.every', 'jobsiteFinal?.pass === true;')
JOBSITE_EXPR = quote(GATES_PATH, 'const pass = stepOrder', 'oral >= 2;')
GATE_WHY = quote(GATES_PATH, "'needs ", "consecutive unaided successes at level'")
CERTIFIED_DOC = quote(GATES_PATH, 'Certification requires all three tiers', 'no shortcuts.')


# ------------------------------------------------------------------ the ladder
# Strand and tier order are read from the registry, not declared here. The
# strands come out in the order the registry first mentions them; the tiers
# are ordered by the registry's OWN `requires` edges - a tier that requires
# another is drawn after it - so the column order on the page is the pack's
# prerequisite order and not this file's opinion of it.
STRANDS = []
for s in SKILLS:
    st = need(s, 'strand', f'{SKILLS_PATH}#skills[]')
    if st not in STRANDS:
        STRANDS.append(st)

_tier_after = {}
for s in SKILLS:
    w = f'{SKILLS_PATH}#skills[{s["skill_id"]}]' if 'skill_id' in s else SKILLS_PATH
    tier = need(s, 'tier', w)
    _tier_after.setdefault(tier, set())
    for req in need(s, 'requires', w):
        prev = next((x for x in SKILLS if x['skill_id'] == req), None)
        if prev is None:
            raise LookupError(f'{w}: requires {req!r}, which is in no skill record')
        if need(prev, 'strand', w) == need(s, 'strand', w) and prev['tier'] != tier:
            _tier_after[tier].add(prev['tier'])
TIERS = []
_pending = dict(_tier_after)
while _pending:
    free = [t for t, after in _pending.items() if not (after - set(TIERS))]
    if not free:
        raise AssertionError(f'{SKILLS_PATH}: the tier prerequisite order has a cycle')
    for t in sorted(free):
        TIERS.append(t)
        del _pending[t]

SKILL_BY_ID = {}
for s in SKILLS:
    sid = need(s, 'skill_id', f'{SKILLS_PATH}#skills[]')
    if sid in SKILL_BY_ID:
        raise AssertionError(f'{SKILLS_PATH}: skill_id {sid!r} appears twice')
    SKILL_BY_ID[sid] = s

BY_UNION = {}
for s in SKILLS:
    BY_UNION.setdefault(need(s, 'union', f'{SKILLS_PATH}#skills[]'), []).append(s)

for u, rows in BY_UNION.items():
    if u not in HALL_NAME:
        raise KeyError(f'{SKILLS_PATH}: skills name a union {u!r} that is in no hall record')
    seen = {(r['strand'], r['tier']) for r in rows}
    if len(seen) != len(rows):
        raise AssertionError(f'{SKILLS_PATH}: {u} has two skills in one strand/tier cell')
    for r in rows:
        w = f'{SKILLS_PATH}#skills[{r["skill_id"]}]'
        for kind in ('requires', 'supports', 'interferes'):
            for e in need(r, kind, w):
                if e not in SKILL_BY_ID:
                    raise LookupError(f'{w}.{kind}: {e!r} is in no skill record')
                if SKILL_BY_ID[e]['union'] != u:
                    raise AssertionError(
                        f'{w}.{kind}: {e!r} belongs to {SKILL_BY_ID[e]["union"]}, not {u}; '
                        'this page draws a hall\'s own ladder and will not draw an edge off it')

# -------------------------------------------------------------------- the seats
# Every binding is held to the registries on both sides before it can reach
# the page: the hall must be a hall, the seat must be a seat, the skill must
# be that hall's own skill, and the cell the binding names must be the cell
# the SEAT says it proves. A binding that fails any of these stops the build
# rather than drawing a seat on a rung it does not stand on.
SEATS_BY_UNION = {}
for hall, binds in BINDINGS.items():
    w = f'{SIMS_PATH}#hall_bindings.{hall}'
    if hall not in HALL_NAME:
        raise KeyError(f'{w}: {hall!r} is in no hall record of {HALLS_PATH}')
    for b in binds:
        sim = need(b, 'sim', w)
        sid = need(b, 'skill_id', w)
        if sim not in SIMS:
            raise KeyError(f'{w}: seat {sim!r} is in no sim record')
        if sid not in SKILL_BY_ID:
            raise LookupError(f'{w}: skill_id {sid!r} is in no skill record of {SKILLS_PATH}')
        sk = SKILL_BY_ID[sid]
        if sk['union'] != hall:
            raise AssertionError(f'{w}: {sid!r} belongs to {sk["union"]}, not {hall}')
        rec = SIMS[sim]
        ws = f'{SIMS_PATH}#sims.{sim}'
        if sk['strand'] != need(rec, 'skill_strand', ws) or sk['tier'] != need(rec, 'skill_tier', ws):
            raise AssertionError(
                f'{w}: binds {sid!r} but the seat says it proves '
                f'{rec["skill_strand"]}/{rec["skill_tier"]}')
        if hall not in need(rec, 'halls', ws):
            raise AssertionError(f'{w}: seat {sim!r} does not name {hall!r} among its halls')
        SEATS_BY_UNION.setdefault(hall, []).append([sim, sid])

# ------------------------------------------------------------- computed figures
N_HALLS = len(HALLS)
N_STRANDS = len(STRANDS)
N_TIERS = len(TIERS)
N_CELLS = len(SKILLS)
N_CELLS_PER_HALL = len(BY_UNION[HALLS[0]['slug']])
for u, rows in BY_UNION.items():
    if len(rows) != N_CELLS_PER_HALL:
        raise AssertionError(f'{SKILLS_PATH}: {u} has {len(rows)} cells, not {N_CELLS_PER_HALL}')
N_EDGES = sum(len(s['requires']) for s in SKILLS)
N_SUPPORTS = sum(len(s['supports']) for s in SKILLS)
N_INTERFERES = sum(len(s['interferes']) for s in SKILLS)
N_ROOTS = sum(1 for s in SKILLS if not s['requires'])
N_SIMS = len(SIMS)
N_BINDINGS = sum(len(v) for v in BINDINGS.values())
N_BOUND_HALLS = len(BINDINGS)
N_UNBOUND_HALLS = N_HALLS - N_BOUND_HALLS
COVERED_CELLS = sorted({b[1] for v in SEATS_BY_UNION.values() for b in v})
N_COVERED_CELLS = len(COVERED_CELLS)
N_UNCOVERED_CELLS = N_CELLS - N_COVERED_CELLS
COVERED_POSITIONS = sorted({(SKILL_BY_ID[c]['strand'], SKILL_BY_ID[c]['tier'])
                            for c in COVERED_CELLS})
N_POSITIONS = N_STRANDS * N_TIERS
N_COVERED_POSITIONS = len(COVERED_POSITIONS)
COVERED_STRANDS = sorted({p[0] for p in COVERED_POSITIONS})
UNCOVERED_STRANDS = [s for s in STRANDS if s not in COVERED_STRANDS]
N_AXES = sum(len(need(v, 'rubric', f'{SIMS_PATH}#sims.{k}')) for k, v in SIMS.items())
N_PASS_AXES = sum(1 for k, v in SIMS.items() for a in v['rubric']
                  if need(a, 'pass', f'{SIMS_PATH}#sims.{k}.rubric[]') != 'informational')
N_INFO_AXES = N_AXES - N_PASS_AXES

MODALITIES = need(variants_reg, 'modalities', VARIANTS_PATH)
BANDS = need(variants_reg, 'bands', VARIANTS_PATH)
BAND_OFFSET = need(variants_reg, 'band_offset', VARIANTS_PATH)
BAND_CEILING = need(variants_reg, 'band_scaffold_ceiling', VARIANTS_PATH)
N_VARIANTS = need(variants_reg, 'variants_per_lesson', VARIANTS_PATH)
if len(MODALITIES) * len(BANDS) != N_VARIANTS:
    raise AssertionError(
        f'{VARIANTS_PATH}: {len(MODALITIES)} modalities x {len(BANDS)} bands is not '
        f'the declared {N_VARIANTS} variants per lesson')
for b in BANDS:
    need(BAND_OFFSET, b, f'{VARIANTS_PATH}#band_offset')
    need(BAND_CEILING, b, f'{VARIANTS_PATH}#band_scaffold_ceiling')
# The pack declares a `vr_sim` modality; the eleven seats are bound to cells,
# never to a generated variant id. The page says so, and this is the check
# that keeps it true: if a seat record ever grows a module id, the sentence
# on the page stops being right and this stops the build.
SIMS_SRC = (ROOT / SIMS_PATH).read_text()
for token in ('module_id', 'lesson_id', 'vr_sim'):
    if token in SIMS_SRC:
        raise AssertionError(
            f'{SIMS_PATH} now mentions {token!r}; the page states that no seat record names a '
            'generated variant module, and that sentence would no longer be true')

# ------------------------------------------------------------------- provenance
# The closed tier set this bundle uses. AI-SYNTHESIZED is deliberately not in
# it: it belongs to orbis/ and describes generated video. A tier is rendered
# only as the `data-tier` attribute of a `.prov` chip, so there is exactly one
# place on this page where a word claims to be a provenance tier and exactly
# one place a check has to look - never a sentence.
TIERS_PROV = ('RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED', 'SCRIPTED')
PROV = (
    ('the ladder', 'AUTHORED', f'the skill graph in {SKILLS_PATH}, hand-built and unreviewed'),
    ('the seats', 'SCHEMATIC', f'schematic physics in {SIMS_PATH}, not equipment'),
    ('the reference operator', 'SCRIPTED', 'a hand-written deterministic control policy'),
    ('the coverage', 'DERIVED', f'counted from hall_bindings in {SIMS_PATH}'),
)
for _, t, _why in PROV:
    if t not in TIERS_PROV:
        raise ValueError(f'provenance tier {t!r} is not one of {", ".join(TIERS_PROV)}')

E = html.escape
F = lambda x: f'{x:,}'


def rubric_of(sim, rec):
    w = f'{SIMS_PATH}#sims.{sim}.rubric'
    out = []
    for a in need(rec, 'rubric', w):
        axis = need(a, 'axis', w)
        pas = need(a, 'pass', w)
        row = {'axis': axis, 'measure': need(a, 'measure', w), 'pass': pas}
        # `fails_when` is required of an axis with a pass bar and absent from an
        # informational one. That is the registry's shape, checked here rather
        # than smoothed over with a default.
        if pas == 'informational':
            if 'fails_when' in a:
                raise AssertionError(f'{w}.{axis}: an informational axis carries fails_when')
        else:
            row['fails_when'] = need(a, 'fails_when', f'{w}.{axis}')
        out.append(row)
    return out


DATA = {
    'product': PRODUCT,
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'strands': STRANDS,
    'tiers': TIERS,
    'unions': [
        {
            'slug': slug,
            'name': HALL_NAME[slug],
            'focus': HALL_FOCUS[slug],
            'cells': [
                [s['skill_id'], s['label'], STRANDS.index(s['strand']), TIERS.index(s['tier']),
                 s['requires'], s['supports'], s['interferes']]
                for s in sorted(BY_UNION[slug],
                                key=lambda x: (STRANDS.index(x['strand']), TIERS.index(x['tier'])))
            ],
            'seats': SEATS_BY_UNION[slug] if slug in SEATS_BY_UNION else [],
        }
        for slug in sorted(BY_UNION, key=lambda s: HALL_ORDER[s])
    ],
    'sims': {
        k: {'name': need(v, 'name', f'{SIMS_PATH}#sims.{k}'),
            'kind': need(v, 'kind', f'{SIMS_PATH}#sims.{k}'),
            'task': need(v, 'task', f'{SIMS_PATH}#sims.{k}'),
            'strand': v['skill_strand'], 'tier': v['skill_tier'],
            'halls': v['halls'],
            'rubric': rubric_of(k, v),
            'operator_levels': need(need(v, 'operator', f'{SIMS_PATH}#sims.{k}'),
                                    'levels', f'{SIMS_PATH}#sims.{k}.operator'),
            'operator_guarantees': need(v['operator'], 'guarantees',
                                        f'{SIMS_PATH}#sims.{k}.operator')}
        for k, v in SIMS.items()
    },
    'variants': {'modalities': MODALITIES, 'bands': BANDS,
                 'band_offset': BAND_OFFSET, 'band_scaffold_ceiling': BAND_CEILING,
                 'per_lesson': N_VARIANTS},
}

# `seats` above is written as an explicit membership test rather than a
# defaulted lookup on purpose: an unbound hall has no entry in
# `hall_bindings` at all, and "this hall has no seat" is a fact read off the
# registry, not a value substituted for a missing one.

PAYLOAD = json.dumps(DATA, separators=(',', ':'), ensure_ascii=False)

# ------------------------------------------------------------------------ html
# The network figures, each in an element of its own and keyed by a stable
# `data-fig` name. A check recomputes the value from the registry and reads it
# back out of THIS attribute - never out of a sentence. The prose in the
# sections below is composed from the same Python names, so a figure and the
# sentence that repeats it cannot drift apart.
NETWORK_FIGS = (
    ('halls', N_HALLS, 'union halls in the pack'),
    ('cells', N_CELLS, 'ladder cells across the network'),
    ('requires-edges', N_EDGES, 'prerequisite edges'),
    ('sims', N_SIMS, 'simulators built'),
    ('bindings', N_BINDINGS, 'seat bindings'),
    ('covered-cells', N_COVERED_CELLS, 'cells a seat stands on'),
    ('uncovered-cells', N_UNCOVERED_CELLS, 'cells with no seat'),
    ('unbound-halls', N_UNBOUND_HALLS, 'halls with no seat at all'),
    ('signed-off-halls', SIGNED_OFF_HALLS, f'halls of {F(N_HALLS)} with a practitioner sign-off'),
)
FIGS = ''.join(
    f'<div class="fig" data-fig="{E(key)}"><b>{E(F(n))}</b><span>{E(lab)}</span></div>'
    for key, n, lab in NETWORK_FIGS)

LIMITS = ''.join(
    f'<li><b>{E(k)}</b>{E(v)}</li>' for k, v in (
        ('what a run is scored against', SCORING_CONTRACT),
        ('what the seat is', need(HONESTY, 'status', f'{SIMS_PATH}#honesty')),
        ('what the reference operator is', need(HONESTY, 'operator', f'{SIMS_PATH}#honesty')),
        ('who wrote the rubric', need(HONESTY, 'authoring', f'{SIMS_PATH}#honesty')),
        ('what the lesson content is', need(PACK_HONESTY, 'content', f'{MANIFEST_PATH}#honesty')),
        ('whose taxonomy this is', need(PACK_HONESTY, 'taxonomy', f'{MANIFEST_PATH}#honesty')),
    ))

OPLEVELS = ''.join(
    f'<tr><td class="k">{E(k)}</td><td>{E(v)}</td></tr>'
    for k, v in OPERATOR_LEVELS.items())

STATUS_ROWS = ''.join(f'<li><code>{E(s)}</code></li>' for s in HALL_STATUSES)

PROV_CHIPS = ''.join(
    f'<span class="prov" data-tier="{E(t)}">{E(what)} — {E(t)} — {E(why)}</span>'
    for what, t, why in PROV)

VARIANT_ROWS = ''.join(
    f'<tr data-band="{E(b)}">' + '<td class="k">' + E(b) + '</td><td class="num">'
    + E(f'{BAND_OFFSET[b]:+d}') + '</td><td class="num">' + E(str(BAND_CEILING[b])) + '</td><td>'
    + ''.join(f'<span class="chip">{E(m)}</span>' for m in MODALITIES) + '</td></tr>'
    for b in BANDS)

GATE_ROWS = ''.join(
    f'<tr data-const="{E(k)}"><td class="k">{E(k)}</td><td class="num">{E(v)}</td>'
    f'<td>{E(why)}</td></tr>'
    for k, v, why in (
        ('GATE.masteryThreshold', str(GATE['masteryThreshold']),
         'the posterior a gate needs before demonstration is even considered'),
        ('GATE.consecutiveUnaided', str(GATE['consecutiveUnaided']),
         GATE_WHY),
        ('GATE.atOrAbove', str(GATE['atOrAbove']),
         'a demonstration only counts at or above this, relative to the learner\'s own level'),
        ('GATE.levelTest.questions', str(need(GATE['levelTest'], 'questions', GATES_PATH)),
         'the level test, fixed difficulty and no hints'),
        ('GATE.levelTest.passPct', str(need(GATE['levelTest'], 'passPct', GATES_PATH)),
         'the level test pass mark, in percent'),
        ('GATE.levelTest.retakeLockHours', str(need(GATE['levelTest'], 'retakeLockHours', GATES_PATH)),
         'hours a failed sitting is locked before a retake'),
        ('TRANSFER.maxHops', str(need(TRANSFER, 'maxHops', GRAPH_PATH)),
         'how far evidence travels along the graph — one hop, never a diffusion'),
        ('TRANSFER.sigmaShare', str(need(TRANSFER, 'sigmaShare', GRAPH_PATH)),
         'the rate at which indirect evidence shrinks uncertainty, against direct evidence'),
        ('INTERFERENCE.discount', str(need(INTERFERENCE, 'discount', GRAPH_PATH)),
         'the weight an attempt keeps when a confusable sibling was just served'),
    ))

STRAND_CHIPS = ''.join(f'<span class="chip">{E(s)}</span>' for s in STRANDS)
TIER_CHIPS = ''.join(f'<span class="chip">{E(t)}</span>' for t in TIERS)
COVERED_POS = ''.join(
    f'<span class="chip covered">{E(st)} · {E(ti)}</span>' for st, ti in COVERED_POSITIONS)
UNCOVERED_STRAND_CHIPS = ''.join(
    f'<span class="chip gap">{E(s)}</span>' for s in UNCOVERED_STRANDS)

READS = ''.join(f'<li><code>{E(p)}</code> — {E(why)}</li>' for p, why in (
    (SKILLS_PATH, 'the ladder: every cell, its label and its requires / supports / interferes edges'),
    (SIMS_PATH, 'the seats, their rubric axes and pass bars, and hall_bindings'),
    (HALLS_PATH, 'each hall\'s own name, focus and order'),
    (VARIANTS_PATH, 'the modalities, bands, band offsets and scaffold ceilings'),
    (MANIFEST_PATH, 'the pack version and the pack\'s own honesty block'),
    (GATES_PATH, 'GATE, the gate policy sentences and the certification expression'),
    (GRAPH_PATH, 'TRANSFER and INTERFERENCE, and the rule that governs propagated credit'),
    (SIGNOFF_PATH, 'the closed set of hall content statuses, and how many halls claim sign-off'),
))

SCRIPT = r'''
/* The ladder renderer.

   Everything drawn below comes out of DATA, which the generator read from
   the registries. Nothing here knows a count: the coverage figure this page
   shows is read back out of the cells this function actually drew, so the
   page cannot state a coverage larger than the seats the registry binds.

   Every lookup that should resolve is checked and throws by name when it
   does not. A seat bound to a cell this hall does not have, or an edge to a
   skill this hall does not have, stops the render with a message naming the
   registry path - it does not quietly draw one fewer edge. */
const D = DATA;
const STRANDS = D.strands, TIERS = D.tiers;
const UNIONS = new Map(D.unions.map((u) => [u.slug, u]));

const COLW = 300, ROWH = 64, PADX = 12, PADY = 30, BOXW = 258, BOXH = 44;

function elem(tag, attrs, kids) {
  const e = document.createElement(tag);
  if (attrs) for (const k in attrs) {
    if (k === 'class') e.className = attrs[k];
    else if (k === 'text') e.textContent = attrs[k];
    else e.setAttribute(k, attrs[k]);
  }
  if (kids) for (const c of kids) e.appendChild(c);
  return e;
}
function svgEl(tag, attrs) {
  const e = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  return e;
}
function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

/* the cell geometry: strand index down, tier index across - the ladder's
   own shape, taken from the registry's strand and tier order */
const cx = (t) => PADX + t * COLW;
const cy = (s) => PADY + s * ROWH;

function edgePath(from, to) {
  const x1 = cx(from.t), y1 = cy(from.s) + BOXH / 2;
  const x2 = cx(to.t), y2 = cy(to.s) + BOXH / 2;
  if (from.s === to.s) {
    return 'M ' + (x2 + BOXW) + ' ' + y2 + ' L ' + x1 + ' ' + y1;
  }
  const mx = x2 + BOXW / 2;
  return 'M ' + mx + ' ' + (y2 + BOXH / 2) + ' L ' + mx + ' ' + (y1 - 2)
       + ' L ' + (x1 - 6) + ' ' + (y1 - 2) + ' L ' + x1 + ' ' + y1;
}

function render(slug) {
  const u = UNIONS.get(slug);
  if (!u) throw new Error('ladder: no hall record for ' + slug);
  const byId = new Map(u.cells.map((c) => [c[0], c]));
  const pos = new Map(u.cells.map((c) => [c[0], { s: c[2], t: c[3] }]));

  /* seats first, so a binding that names a cell this hall does not have
     stops the render before anything claims coverage */
  const seatsOf = new Map();
  for (const [sim, sid] of u.seats) {
    if (!byId.has(sid)) {
      throw new Error('ladder: sims/registry/sims.json hall_bindings.' + slug
        + ' binds seat ' + sim + ' to ' + sid + ', which is not a cell of this hall');
    }
    if (!D.sims[sim]) {
      throw new Error('ladder: sims/registry/sims.json hall_bindings.' + slug
        + ' names seat ' + sim + ', which is in no sim record');
    }
    if (!seatsOf.has(sid)) seatsOf.set(sid, []);
    seatsOf.get(sid).push(sim);
  }

  const head = document.getElementById('hallhead');
  clear(head);
  head.appendChild(elem('h2', { text: u.name }));
  head.appendChild(elem('p', { class: 'why', text: u.focus }));
  head.appendChild(elem('p', { class: 'muted',
    text: 'hall slug ' + u.slug + ' · ' + u.cells.length + ' cells · '
      + STRANDS.length + ' strands × ' + TIERS.length + ' tiers' }));

  /* ---- the ladder itself ---- */
  const svg = document.getElementById('grid');
  clear(svg);
  const W = PADX * 2 + TIERS.length * COLW - (COLW - BOXW);
  const H = PADY + STRANDS.length * ROWH + 10;
  svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  svg.setAttribute('width', W);
  svg.setAttribute('height', H);

  for (let t = 0; t < TIERS.length; t++) {
    const lab = svgEl('text', { x: cx(t), y: 18, class: 'colhead' });
    lab.textContent = TIERS[t];
    svg.appendChild(lab);
  }

  const edges = svgEl('g', { class: 'edges' });
  svg.appendChild(edges);
  let nEdges = 0;
  const drawEdges = (kind, index) => {
    for (const c of u.cells) {
      for (const other of c[index]) {
        if (!byId.has(other)) {
          throw new Error('ladder: ' + c[0] + ' ' + kind + ' ' + other
            + ', which is not a cell of ' + slug);
        }
        const p = svgEl('path', {
          d: edgePath(pos.get(c[0]), pos.get(other)),
          class: 'edge ' + kind,
          'data-edge': kind, 'data-from': c[0], 'data-to': other,
        });
        edges.appendChild(p);
        if (kind === 'requires') nEdges++;
      }
    }
  };
  drawEdges('requires', 4);
  drawEdges('supports', 5);
  drawEdges('interferes', 6);

  const nodes = svgEl('g', { class: 'nodes' });
  svg.appendChild(nodes);
  for (const c of u.cells) {
    const [sid, label, si, ti] = c;
    const seats = seatsOf.has(sid) ? seatsOf.get(sid) : [];
    const covered = seats.length > 0 ? 'yes' : 'no';
    const g = svgEl('g', {
      class: 'cell' + (covered === 'yes' ? ' covered' : ''),
      'data-skill': sid, 'data-strand': STRANDS[si], 'data-tier': TIERS[ti],
      'data-covered': covered, 'data-seats': String(seats.length),
      'data-requires': c[4].join(' '),
    });
    g.appendChild(svgEl('rect', { x: cx(ti), y: cy(si), width: BOXW, height: BOXH, rx: 6 }));
    const t1 = svgEl('text', { x: cx(ti) + 10, y: cy(si) + 18, class: 'cname' });
    t1.textContent = STRANDS[si] + ' · ' + TIERS[ti];
    g.appendChild(t1);
    const t2 = svgEl('text', { x: cx(ti) + 10, y: cy(si) + 34, class: 'cmark' });
    /* the box is a fixed width, so the label names the first seat and counts
       the rest rather than running off the end of it; every seat is named in
       full in its own card below */
    t2.textContent = seats.length
      ? (seats.length === 1 ? 'seat: ' + seats[0]
         : seats.length + ' seats: ' + seats[0] + ' +' + (seats.length - 1) + ' more')
      : 'no seat';
    g.appendChild(t2);
    if (seats.length) {
      const a = svgEl('a', { href: 'trade_craft_3d.html?hall=' + slug + '&sim=' + seats[0] });
      a.appendChild(g);
      nodes.appendChild(a);
    } else {
      nodes.appendChild(g);
    }
    g.appendChild(svgEl('title', {})).textContent = label;
  }

  /* ---- coverage, counted off the cells that were actually drawn ---- */
  const drawn = svg.querySelectorAll('[data-skill]');
  const coveredEls = svg.querySelectorAll('[data-covered="yes"]');
  const strandsCovered = new Set();
  for (const el of coveredEls) strandsCovered.add(el.getAttribute('data-strand'));
  document.getElementById('cov-cells').textContent = String(drawn.length);
  document.getElementById('cov-covered').textContent = String(coveredEls.length);
  document.getElementById('cov-uncovered').textContent = String(drawn.length - coveredEls.length);
  document.getElementById('cov-seats').textContent = String(u.seats.length);
  document.getElementById('cov-edges').textContent = String(nEdges);
  document.getElementById('cov-strands').textContent =
    strandsCovered.size + ' of ' + STRANDS.length;

  const gaps = document.getElementById('gaps');
  clear(gaps);
  for (const s of STRANDS) {
    if (strandsCovered.has(s)) continue;
    gaps.appendChild(elem('span', { class: 'chip gap', text: s, 'data-gap-strand': s }));
  }
  document.getElementById('gap-n').textContent =
    String(STRANDS.length - strandsCovered.size) + ' of ' + STRANDS.length;

  /* ---- the seats, with their rubric axes ---- */
  const seatWrap = document.getElementById('seats');
  clear(seatWrap);
  if (!u.seats.length) {
    seatWrap.appendChild(elem('p', { class: 'nonebox', 'data-no-seats': slug,
      text: 'This hall carries no simulator seat. Every cell of its ladder is a module '
        + 'with no built seat behind it, and this page will not pretend otherwise.' }));
  }
  for (const [sim, sid] of u.seats) {
    const rec = D.sims[sim];
    const card = elem('div', { class: 'seat', 'data-seat': sim, 'data-seat-skill': sid });
    card.appendChild(elem('h3', { text: rec.name }));
    card.appendChild(elem('p', { class: 'muted',
      text: 'proves ' + rec.strand + ' · ' + rec.tier + ' — ' + sid }));
    card.appendChild(elem('p', { class: 'why', text: rec.task }));
    const tbl = elem('table', {});
    const tb = elem('tbody', {});
    tb.appendChild(elem('tr', {}, [
      elem('th', { text: 'axis' }), elem('th', { text: 'measured' }),
      elem('th', { text: 'pass bar' }), elem('th', { text: 'fails when' })]));
    for (const a of rec.rubric) {
      tb.appendChild(elem('tr', { 'data-axis': a.axis }, [
        elem('td', { class: 'k', text: a.axis }),
        elem('td', { text: a.measure }),
        elem('td', { class: 'num', text: a.pass }),
        elem('td', { class: 'muted',
          text: 'fails_when' in a ? a.fails_when : 'not pass-gated: this axis is recorded, not scored' }),
      ]));
    }
    tbl.appendChild(tb);
    card.appendChild(elem('div', { class: 'tscroll' }, [tbl]));
    card.appendChild(elem('p', { class: 'muted',
      text: 'reference operator levels: ' + rec.operator_levels.join(', ')
        + ' — guaranteed on the optimal level for the axes '
        + rec.operator_guarantees.join(', ') }));
    const a = elem('a', { class: 'open', href: 'trade_craft_3d.html?hall=' + slug + '&sim=' + sim,
      'data-open-seat': sim, text: 'open this seat' });
    card.appendChild(a);
    seatWrap.appendChild(card);
  }

  /* ---- what a run here does and does not evidence ---- */
  document.getElementById('ev-cell').textContent = u.seats.length
    ? STRANDS[byId.get(u.seats[0][1])[2]] + ' · ' + TIERS[byId.get(u.seats[0][1])[3]]
    : 'no cell at all in this hall';

  const link = document.getElementById('hall-3d');
  link.setAttribute('href', 'trade_craft_3d.html?hall=' + slug);
  if (location.search) {
    history.replaceState(null, '', location.pathname + '?hall=' + slug);
  }
}

/* ---- the picker ---- */
const sel = document.getElementById('hall');
for (const u of D.unions) {
  const o = elem('option', { value: u.slug, text: u.name + ' (' + u.slug + ')' });
  sel.appendChild(o);
}
const asked = new URLSearchParams(location.search).get('hall');
const note = document.getElementById('picknote');
/* An unreadable ?hall= is not guessed at and not silently swapped for
   another hall: the page says the name it was given is in no hall record and
   shows the registry's first hall, which it also says. */
if (asked !== null && !UNIONS.has(asked)) {
  note.textContent = 'the link asked for "' + asked + '", which is in no hall record of '
    + 'pack/registry/halls.json; showing the first hall the registry lists';
} else if (asked === null) {
  note.textContent = 'no hall named in the link; showing the first hall the registry lists';
} else {
  note.textContent = '';
}
sel.value = (asked !== null && UNIONS.has(asked)) ? asked : D.unions[0].slug;
sel.addEventListener('change', () => {
  document.getElementById('picknote').textContent = '';
  render(sel.value);
});
render(sel.value);
'''

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' stroke='%23E8A33D' stroke-width='2.6' stroke-linejoin='round'/%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E">
<title>{E(PRODUCT.split("(")[0].strip())} — training ladder</title>
<style>
:root{{
  --plate:#12181B; --panel:#182023; --sunk:#0C1113; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --mark-ink:#12181B; --steel:#41C4D4;
  --good:#5CB584; --crit:#E07C68; --warn:#E8A33D;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--plate);color:var(--ink);
  font:14px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
  padding:0 18px}}
.wrap{{max-width:1020px;margin:0 auto}}
a{{color:var(--steel)}}
header.page{{padding:40px 0 10px;border-bottom:3px solid var(--mark)}}
header.page h1{{font:700 34px/1.1 "Barlow Condensed",system-ui,sans-serif;margin:0}}
header.page h1 .x{{color:var(--mark)}}
header.page p{{color:var(--muted);margin:6px 0 14px}}
h2{{font:700 22px/1.2 "Barlow Condensed",system-ui,sans-serif;margin:34px 0 10px;
  color:var(--mark);letter-spacing:.02em}}
h3{{font:700 18px/1.25 "Barlow Condensed",system-ui,sans-serif;margin:0 0 6px}}
section{{margin:0 0 10px}}
.lead{{background:var(--panel);border:1px solid var(--rule);border-left:4px solid var(--warn);
  border-radius:8px;padding:14px 18px}}
.lead ul{{margin:8px 0 0;padding-inline-start:20px}}
.lead li{{margin:6px 0;color:var(--muted)}}
.lead li b{{color:var(--ink);text-transform:uppercase;font-size:12px;letter-spacing:.06em;
  margin-inline-end:6px;display:block}}
.figs{{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0}}
.fig{{background:var(--panel);border:1px solid var(--rule);border-radius:8px;
  padding:10px 14px;min-width:132px;flex:1 1 132px}}
.fig b{{display:block;font:600 24px/1.2 "Barlow Condensed",system-ui,sans-serif;color:var(--mark)}}
.fig span{{color:var(--muted);font-size:13px}}
table{{width:100%;border-collapse:collapse;background:var(--panel);
  border:1px solid var(--rule);border-radius:8px;overflow:hidden;margin:8px 0}}
td,th{{border-top:1px solid var(--rule);padding:8px 10px;vertical-align:top;font-size:13.5px;
  text-align:start}}
th{{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;
  letter-spacing:.05em}}
tr:first-child td,tr:first-child th{{border-top:0}}
td.k{{color:var(--ink);font-weight:600;white-space:nowrap}}
td.num{{font:13px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--steel);
  white-space:nowrap}}
.tscroll{{overflow-x:auto}}
@media (max-width:640px){{td.k,td.num{{white-space:normal}}}}
td.muted{{color:var(--muted)}}
code{{font:13px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted)}}
pre{{background:var(--sunk);border:1px solid var(--rule);border-radius:6px;padding:10px 12px;
  overflow-x:auto;font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--ink)}}
.chip{{display:inline-block;border-radius:4px;padding:1px 7px;font-size:12px;
  border:1px solid var(--rule);background:var(--sunk);color:var(--muted);margin:0 6px 4px 0}}
.chip.covered{{color:var(--good);border-color:var(--good)}}
.chip.gap{{color:var(--crit);border-color:var(--crit)}}
.prov{{display:inline-block;border-radius:4px;padding:1px 7px;font-size:11px;
  border:1px solid var(--rule);margin:0 6px 4px 0;background:var(--sunk);color:var(--muted);
  letter-spacing:.03em}}
.why{{color:var(--ink);font-size:14px}}
.muted{{color:var(--muted);font-size:13px}}
.toolbar{{position:sticky;top:0;background:var(--plate);padding:10px 0;z-index:2;
  border-bottom:1px solid var(--rule);display:flex;gap:10px;flex-wrap:wrap;align-items:center}}
.toolbar select{{background:var(--sunk);border:1px solid var(--rule);color:var(--ink);
  border-radius:6px;padding:8px 12px;font:inherit;flex:1 1 280px}}
.toolbar label{{color:var(--muted);font-size:13px}}
#picknote{{color:var(--warn);font-size:13px;flex:1 1 100%}}
.gridwrap{{overflow-x:auto;background:var(--panel);border:1px solid var(--rule);
  border-radius:8px;padding:8px}}
svg#grid{{display:block;max-width:100%;height:auto}}
svg .colhead{{fill:var(--mark);font:600 12px system-ui,sans-serif;
  text-transform:uppercase;letter-spacing:.08em}}
svg .cell rect{{fill:var(--sunk);stroke:var(--rule);stroke-width:1}}
svg .cell.covered rect{{stroke:var(--good);stroke-width:2}}
svg .cell .cname{{fill:var(--ink);font:600 12.5px system-ui,sans-serif}}
svg .cell .cmark{{fill:var(--muted);font:11.5px ui-monospace,Menlo,monospace}}
svg .cell.covered .cmark{{fill:var(--good)}}
svg .edge{{fill:none;stroke:var(--rule);stroke-width:1.4}}
svg .edge.requires{{stroke:var(--steel)}}
svg .edge.supports{{stroke:var(--mark);stroke-dasharray:5 4}}
svg .edge.interferes{{stroke:var(--crit);stroke-dasharray:2 4}}
.seat{{background:var(--panel);border:1px solid var(--rule);border-radius:10px;
  padding:14px 16px;margin:12px 0}}
.seat a.open{{display:inline-block;margin-top:6px;background:var(--mark);color:var(--mark-ink);
  font-weight:600;border-radius:6px;padding:7px 14px;text-decoration:none}}
.nonebox{{background:var(--sunk);border:1px solid var(--crit);border-radius:8px;
  padding:12px 14px;color:var(--ink)}}
.legend span{{margin-inline-end:14px;font-size:12.5px;color:var(--muted)}}
.legend i{{display:inline-block;width:22px;height:0;border-top-width:2px;
  vertical-align:middle;margin-inline-end:6px}}
.legend i.req{{border-top:2px solid var(--steel)}}
.legend i.sup{{border-top:2px dashed var(--mark)}}
.legend i.int{{border-top:2px dotted var(--crit)}}
footer.page{{margin-top:34px;border-top:1px solid var(--rule);padding:14px 0 30px;
  color:var(--muted);font-size:14px}}
footer.page a{{margin-inline-end:10px}}
</style>
</head>
<body>
<div class="wrap">

<header class="page">
  <h1>{E(PRODUCT.split("(")[0].strip())} — <span class="x">training ladder</span></h1>
  <p>{E(PRODUCT)} · pack {E(PACK_VERSION)} · built {E(BUILT)} · one hall at a time, read from
     <code>{E(SKILLS_PATH)}</code> and <code>{E(SIMS_PATH)}</code></p>
</header>

<section class="lead" id="limits">
  <h2>What a seat run is evidence of, and what it is not</h2>
  <p class="why">A passing run satisfies a rubric written in this bundle, measured on a schematic
     simulator written in this bundle, against a scripted reference operator also written in this
     bundle. <b>It certifies nobody.</b> {E(F(SIGNED_OFF_HALLS))} of {E(F(N_HALLS))} halls carry a
     practitioner sign-off, so no hall in this pack has had its content signed by the people who
     do the work.</p>
  <ul>{LIMITS}</ul>
</section>

<section class="figs">{FIGS}</section>

<section>
  <h2>The shape of the ladder, and the shape of the gap</h2>
  <p class="why">Each hall carries {E(F(N_CELLS_PER_HALL))} cells — {E(F(N_STRANDS))} strands
     across {E(F(N_TIERS))} tiers — and the network carries {E(F(N_CELLS))} of them, joined by
     {E(F(N_EDGES))} prerequisite edges, {E(F(N_SUPPORTS))} support edges and
     {E(F(N_INTERFERES))} interference edges. {E(F(N_ROOTS))} cells have no prerequisite at all.</p>
  <p class="why">{E(F(N_SIMS))} simulators are built. Their {E(F(N_BINDINGS))} bindings reach
     {E(F(N_BOUND_HALLS))} halls and stand on {E(F(N_COVERED_CELLS))} cells — which leaves
     {E(F(N_UNCOVERED_CELLS))} cells with no seat and {E(F(N_UNBOUND_HALLS))} halls with no seat at
     all. Every binding in the pack lands on the same {E(F(N_COVERED_POSITIONS))} of the
     {E(F(N_POSITIONS))} strand &times; tier positions:</p>
  <p>{COVERED_POS}</p>
  <p class="why">Which means {E(F(len(UNCOVERED_STRANDS)))} of the {E(F(N_STRANDS))} strands carry
     no simulator anywhere in the network, in any hall, at any tier:</p>
  <p>{UNCOVERED_STRAND_CHIPS}</p>
  <p class="muted">strands, in the registry's order: {STRAND_CHIPS}</p>
  <p class="muted">tiers, ordered by the registry's own prerequisite edges: {TIER_CHIPS}</p>
</section>

<div class="toolbar">
  <label for="hall">hall</label>
  <select id="hall" aria-label="choose a union hall"></select>
  <a id="hall-3d" href="trade_craft_3d.html">open this hall in the 3D environment</a>
  <span id="picknote"></span>
</div>

<section id="hallhead"></section>

<section class="figs">
  <div class="fig"><b id="cov-cells"></b><span>cells on this ladder</span></div>
  <div class="fig"><b id="cov-covered"></b><span>cells a seat stands on</span></div>
  <div class="fig"><b id="cov-uncovered"></b><span>cells with no seat</span></div>
  <div class="fig"><b id="cov-seats"></b><span>seat bindings in this hall</span></div>
  <div class="fig"><b id="cov-edges"></b><span>prerequisite edges drawn</span></div>
  <div class="fig"><b id="cov-strands"></b><span>strands with any seat</span></div>
</section>

<section>
  <h2>The ladder</h2>
  <p class="legend">
    <span><i class="req"></i>requires — the hard prerequisite edge</span>
    <span><i class="sup"></i>supports — soft transfer</span>
    <span><i class="int"></i>interferes — a confusable pair</span>
  </p>
  <div class="gridwrap"><svg id="grid" role="img"
    aria-label="the hall's skills by strand and tier, with prerequisite edges"></svg></div>
  <p class="muted">A cell outlined in green carries a seat and links into it. Every other cell is
     a module with no built seat behind it.</p>
</section>

<section>
  <h2>Where the seats sit, and what they measure</h2>
  <p class="why">A seat proves the cell the registry binds it to — <b id="ev-cell"></b> in this
     hall — and nothing above it, beside it or after it.</p>
  <div id="seats"></div>
</section>

<section>
  <h2>Strands with no seat: <span id="gap-n"></span></h2>
  <p id="gaps"></p>
  <p class="muted">Counted from the same cells the ladder drew. A strand is listed here when no
     seat in the pack stands on any of its tiers in this hall.</p>
</section>

<section>
  <h2>The same cell, taken nine ways</h2>
  <p class="why"><code>{E(VARIANTS_PATH)}</code> declares {E(F(len(MODALITIES)))} modalities
     &times; {E(F(len(BANDS)))} bands = {E(F(N_VARIANTS))} variants for every lesson under a cell.
     The band shifts the difficulty and caps how much scaffolding a learner can be given:</p>
  <div class="tscroll"><table><tbody>
    <tr><th>band</th><th>difficulty offset</th><th>scaffold ceiling</th><th>modalities</th></tr>
    {VARIANT_ROWS}
  </tbody></table></div>
  <p class="why">The pack declares a <code>vr_sim</code> modality. No seat record in
     <code>{E(SIMS_PATH)}</code> names a generated variant module: the {E(F(N_SIMS))} seats are
     bound to cells through <code>hall_bindings</code> and to nothing else, so a
     <code>vr_sim</code> variant id and a built seat are two separate things in this bundle and
     this page does not join them.</p>
</section>

<section>
  <h2>What the control plane actually does with a rung</h2>
  <p class="why">{E(GATES_RULE)}</p>
  <p class="why">{E(GRAPH_RULE)}</p>
  <div class="tscroll"><table><tbody>
    <tr><th>constant</th><th>value</th><th>what it decides</th></tr>
    {GATE_ROWS}
  </tbody></table></div>
  <p class="why">{E(CERTIFIED_DOC)} <code>{E(GATES_PATH)}</code> writes it as:</p>
  <pre data-quote="certified" data-source="{E(GATES_PATH)}">{E(CERTIFIED_EXPR)}</pre>
  <pre data-quote="jobsite-final" data-source="{E(GATES_PATH)}">{E(JOBSITE_EXPR)}</pre>
  <p class="why">Nothing on this page meets that. A seat run is not a skill gate — a gate needs
     demonstrations stamped as qualifying at serve time by the sequencer — it is not the level
     test, and it is not the jobsite final, whose oral component is a person from the hall asking
     the learner to explain the why.</p>
  <p class="muted">The closed set of content statuses a hall record may declare
     (<code>{E(SIGNOFF_PATH)}</code>):</p>
  <ul class="muted">{STATUS_ROWS}</ul>
</section>

<section>
  <h2>How the reference operator is run</h2>
  <p class="why">Every rubric axis is measured, never judged: <em>{E(SCORING_CONTRACT)}</em>. The
     bundle drives each seat with a scripted operator at {E(F(len(OPERATOR_LEVELS)))} levels, so a
     pass bar is a bar something has actually cleared:</p>
  <div class="tscroll"><table><tbody>{OPLEVELS}</tbody></table></div>
  <p class="why">Across the {E(F(N_SIMS))} seats there are {E(F(N_AXES))} rubric axes, of which
     {E(F(N_PASS_AXES))} carry a pass bar and {E(F(N_INFO_AXES))} are recorded but not scored.</p>
  <p>{PROV_CHIPS}</p>
</section>

<section>
  <h2>What this page read</h2>
  <ul class="muted">{READS}</ul>
  <p class="muted">Every number on this page is counted from those files at build time or from the
     cells this page drew. None is typed.</p>
</section>

<footer class="page">
  <a href="trade_craft_3d.html">3D environment</a>
  <a href="trade_craft_lessons.html">lessons</a>
  <a href="trade_craft_dashboard.html">network dashboard</a>
  <a href="trade_craft_landing.html">landing</a>
</footer>
</div>
<script>
const DATA = {PAYLOAD};
</script>
<script>
{SCRIPT}</script>
</body>
</html>
'''

out = HERE / 'trade_craft_ladder.html'
emit(out, page,
     f'{F(N_HALLS)} halls, {F(N_CELLS)} cells, {F(N_EDGES)} prerequisite edges, '
     f'{F(N_SIMS)} seats on {F(N_COVERED_CELLS)} cells, certifies nobody')
