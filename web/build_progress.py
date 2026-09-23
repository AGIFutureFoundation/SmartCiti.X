#!/usr/bin/env python3
"""The learner progression page: the control plane, run on the learner's own record.

WHY THIS FILE EXISTS. `control/` holds a complete, tested adaptive-learning
core - `lpa.mjs` (LearnerProfile), `dial.mjs` (ZpdDial), `graph.mjs`
(SkillGraph), `sequencer.mjs` (Sequencer), `gates.mjs` (the skill gates) and
`hints.mjs` (the hint ladder). The 3D app a learner actually plays reads none
of it: `grep` for `LearnerProfile`, `ZpdDial`, `Sequencer`, `SkillGraph`,
`checkSkillGate` or `certified` in `web/build_3d.py` returns nothing. So a
learner takes a simulator seat, gets a deterministic rubric score, and nothing
sequences what comes next, nothing sets the difficulty, no gate opens or stays
shut, and no help fades. The machinery to do all of it exists and is
disconnected.

This page connects it, read-only, without touching the 3D app. It carries the
control modules' OWN SOURCE into the browser and runs their real classes over
whatever this device recorded, so that a learner can ask four questions and
get the control plane's own answers: where am I, what next and why, how hard
will it be, what may I claim, and what help do I get.

HOW THE CONTROL PLANE GETS INTO THE PAGE. Verbatim. `control_module()` reads
each `.mjs` file and applies exactly two mechanical edits - it drops the
`import` lines (the modules are concatenated in dependency order, so the names
are already in scope) and strips a leading `export ` - and asserts that
nothing else changed. `web/test_progress.mjs` re-derives the same transform
from `control/` and holds the shipped page to it byte for byte, so the page
cannot drift into being a second implementation of the control plane. It is
the control plane.

WHAT THE PAGE WILL NOT DO, which is the point of it.

  - It will not invent a learner. With no record on the device the page says
    so, in a panel of its own, and every machinery panel it then shows is
    stamped `data-profile="empty"`. There is no demo learner, no seeded
    history, no sample score.
  - It will not pick a hall for the reader. A page that opens on
    `halls[0]` because nothing said otherwise is the bug this bundle has
    already shipped once. The picker starts unselected and says so.
  - It will not show a gate as passed, or a skill as mastered, on evidence
    the record does not hold. `tc-training` records no serve difficulty, so
    every replayed attempt is stamped `gate_qualifying: false` - fail closed -
    and `checkSkillGate` is given the truth: nothing in this record was served
    at gate difficulty, so nothing in this record can qualify. The page says
    that plainly and `certified()` is called for real, with the level test and
    jobsite final it does not have, which is to say with `null`.
  - It will not attribute a `tc-progress` seat pass to a hall. That record
    names a seat and no hall, and the same seat is bound to many halls, so
    attributing it would be this page deciding which hall a learner was
    standing in. It is shown as a count and fed to nothing.

ONE TRUTH PER FACT. Every count and constant below is read from the registry
or the control module that owns it. `node brand/figures.mjs .` is the check
that says so. A missing field fails the build by name through `need()`; there
is no `.get(k, default)` in this file.
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
        if (cand / 'pack').is_dir() and (cand / 'control').is_dir() and (cand / 'auth').is_dir():
            return cand
    raise RuntimeError('cannot locate the packs from ' + str(HERE))


ROOT = _root()

# Named by their repo-relative paths on purpose: rnd/build.py scans the
# generators under web/ for exactly these strings, and a page that reads a
# registry without naming it would close the gap in the scan while leaving it
# open in the bundle.
SKILLS_PATH = 'pack/registry/skills.json'
SIMS_PATH = 'sims/registry/sims.json'
HALLS_PATH = 'pack/registry/halls.json'
MANIFEST_PATH = 'pack/manifest.json'
AUTH_PATH = 'auth/registry/auth.json'
TRAINING_PATH = 'training/registry/training.json'
LPA_PATH = 'control/lpa.mjs'
HINTS_PATH = 'control/hints.mjs'
GRAPH_PATH = 'control/graph.mjs'
GATES_PATH = 'control/gates.mjs'
DIAL_PATH = 'control/dial.mjs'
SEQUENCER_PATH = 'control/sequencer.mjs'
CONTROL_README = 'control/README.md'
APP_PATH = 'web/build_3d.py'

# Dependency order: a module's names must already be declared when the next
# one's top-level code is evaluated.
CONTROL_MODULES = (LPA_PATH, HINTS_PATH, GRAPH_PATH, GATES_PATH, DIAL_PATH, SEQUENCER_PATH)
CONTROL_TESTS = ('control/test.mjs', 'control/test_graph.mjs', 'control/test_hints.mjs')


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
halls_reg = load(HALLS_PATH)
manifest = load(MANIFEST_PATH)
auth_reg = load(AUTH_PATH)
training_reg = load(TRAINING_PATH)

PACK_VERSION = need(manifest, 'pack_version', MANIFEST_PATH)
PRODUCT = need(sims_reg, 'product', SIMS_PATH)
BUILT = need(sims_reg, 'built', SIMS_PATH)
for rel, reg in ((SIMS_PATH, sims_reg), (HALLS_PATH, halls_reg),
                 (AUTH_PATH, auth_reg), (TRAINING_PATH, training_reg)):
    if need(reg, 'pack_version', rel) != PACK_VERSION:
        raise AssertionError(f'{rel}: pack_version disagrees with {MANIFEST_PATH}')

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
SCORING_CONTRACT = need(sims_reg, 'scoring_contract', SIMS_PATH)
SIMS_HONESTY = need(sims_reg, 'honesty', SIMS_PATH)
PACK_HONESTY = need(manifest, 'honesty', MANIFEST_PATH)

# ------------------------------------------------- the storage keys, read once
# The two records the app already keeps, and the identity label that names
# whose device it is. Both key names are read from the registry that declares
# them, and the two registries are held against each other rather than one of
# them being trusted alone.
AUTH_RECORDS = need(auth_reg, 'records_named', AUTH_PATH)
AUTH_STORAGE = need(auth_reg, 'storage', AUTH_PATH)
AUTH_HONESTY = need(auth_reg, 'honesty', AUTH_PATH)
PROGRESS_KEY = need(AUTH_RECORDS, 'progress_key', f'{AUTH_PATH}#records_named')
TRAINING_KEY = need(AUTH_RECORDS, 'training_key', f'{AUTH_PATH}#records_named')
IDENTITY_KEY = need(AUTH_STORAGE, 'identity_key', f'{AUTH_PATH}#storage')

TRAINING_STORAGE = need(training_reg, 'storage', TRAINING_PATH)
if need(TRAINING_STORAGE, 'key', f'{TRAINING_PATH}#storage') != TRAINING_KEY:
    raise AssertionError(
        f'{TRAINING_PATH}#storage.key and {AUTH_PATH}#records_named.training_key name '
        'two different localStorage keys; this page would read the wrong record')
TRAINING_ON_KEY = need(TRAINING_STORAGE, 'toggle_key', f'{TRAINING_PATH}#storage')
TRAINING_CAP = need(TRAINING_STORAGE, 'cap', f'{TRAINING_PATH}#storage')
EPISODE_KINDS = need(training_reg, 'episode_kinds', TRAINING_PATH)
SIM_EPISODE = need(EPISODE_KINDS, 'sim', f'{TRAINING_PATH}#episode_kinds')
SIM_FIELDS = need(SIM_EPISODE, 'fields', f'{TRAINING_PATH}#episode_kinds.sim')
ACTORS = need(training_reg, 'actors', TRAINING_PATH)
TRAINING_HONESTY = need(training_reg, 'honesty', TRAINING_PATH)

# The page replays every recorded run at rung 0 - unaided - and says so. That
# sentence is only true while the episode record has nowhere to put a hint
# rung, so it is checked here rather than asserted on the page.
for banned in ('rung', 'hint', 'scaffold'):
    if banned in SIM_FIELDS:
        raise AssertionError(
            f'{TRAINING_PATH}#episode_kinds.sim.fields now carries {banned!r}; the page states '
            'that a recorded run carries no hint rung and is therefore replayed unaided, '
            'and that sentence would no longer be true')
# `actor` is what separates the learner's own run from the scripted reference
# operator's. The page drops every non-human episode, so the human actor name
# is read from the registry rather than typed.
HUMAN_ACTOR = 'human'
if HUMAN_ACTOR not in ACTORS:
    raise AssertionError(f'{TRAINING_PATH}#actors does not name {HUMAN_ACTOR!r}')
SCRIPTED_ACTORS = [a for a in ACTORS if a != HUMAN_ACTOR]
if not SCRIPTED_ACTORS:
    raise AssertionError(f'{TRAINING_PATH}#actors names no actor other than {HUMAN_ACTOR!r}')


# ----------------------------------- the control plane, carried in verbatim
IMPORT_RE = re.compile(r"^import\b.*?;\s*$")
EXPORT_RE = re.compile(r'^export\s+(?=const|function|class|let|var)')


def control_module(rel):
    """One control module's source, ready to run inside one module script.

    Exactly two mechanical edits, both asserted afterwards: the `import` lines
    go (the modules are concatenated in dependency order, so every name they
    import is already declared above), and a leading `export ` is stripped (an
    inline module script has no importers). Every other byte - the arithmetic,
    the comments that explain why each number is what it is, the `why` strings
    a learner reads - is carried across untouched, because a page that
    paraphrased this code would be a second opinion about it.
    """
    src = (ROOT / rel).read_text()
    out = []
    dropped = 0
    for ln in src.split('\n'):
        if IMPORT_RE.match(ln):
            dropped += 1
            continue
        out.append(EXPORT_RE.sub('', ln))
    body = '\n'.join(out)
    for ln in body.split('\n'):
        if ln.startswith('import ') or ln.startswith('export '):
            raise AssertionError(f'{rel}: the transform left {ln!r}, which an inline module '
                                 'script cannot run')
    if '</script' in body:
        raise AssertionError(f'{rel}: contains a </script close, which would end the page script')
    return body, dropped


CONTROL_SRC = {}
CONTROL_LINES = {}
CONTROL_DROPPED = 0
for rel in CONTROL_MODULES:
    body, dropped = control_module(rel)
    CONTROL_SRC[rel] = body
    CONTROL_LINES[rel] = len((ROOT / rel).read_text().rstrip('\n').split('\n'))
    CONTROL_DROPPED += dropped

CONTROL_BUNDLE = '\n'.join(
    f'/* ---- {rel} ---- carried in verbatim; see build_progress.py control_module() */\n'
    + CONTROL_SRC[rel] for rel in CONTROL_MODULES)

# The names the page's own renderer uses. Every one must be a declaration the
# bundle above actually provides, or the page would throw on load.
CONTROL_NAMES = (
    'LearnerProfile', 'pSuccess', 'RUNG_CREDIT', 'SIGMA_MAX', 'shrinkMastery',
    'SkillGraph', 'TRANSFER', 'INTERFERENCE',
    'ZpdDial', 'BAND', 'BAND_CENTER', 'DEFAULTS', 'STATES', 'classifyAffect',
    'Sequencer', 'WEIGHTS', 'POLICY',
    'checkSkillGate', 'scoreLevelTest', 'scoreJobsiteFinal', 'certified', 'GATE', 'ANTIGAMING',
    'HintEngine', 'RUNGS', 'HINT_POLICY', 'masteryCeiling', 'ceilingFor', 'creditFor',
)
for name in CONTROL_NAMES:
    if not re.search(rf'^(?:const|let|function|class)\s+{re.escape(name)}\b',
                     CONTROL_BUNDLE, re.M):
        raise AssertionError(
            f'the control bundle declares no {name!r}; the page addresses it and would throw. '
            f'Looked across {", ".join(CONTROL_MODULES)}')

# A name declared twice at module top level is a SyntaxError the moment the
# page loads, and concatenating six modules is exactly how that happens.
_decls = {}
for rel in CONTROL_MODULES:
    for m in re.finditer(r'^(?:const|let|var|function|class)\s+([A-Za-z_$][\w$]*)',
                         CONTROL_SRC[rel], re.M):
        nm = m.group(1)
        if nm in _decls:
            raise AssertionError(
                f'{rel} and {_decls[nm]} both declare {nm!r} at module top level; concatenating '
                'them into one module script is a SyntaxError')
        _decls[nm] = rel


# ------------------------------------------- control constants, read not typed
def node_dump():
    """Import the control modules and dump what they export.

    Read by IMPORTING rather than by pattern-matching the source: the build
    then states the same numbers the running page will, because both come from
    the same declarations. If node is unavailable the build fails here rather
    than shipping a page that invented its own numbers.
    """
    script = (
        "const lpa = await import('./control/lpa.mjs');"
        "const h = await import('./control/hints.mjs');"
        "const gr = await import('./control/graph.mjs');"
        "const g = await import('./control/gates.mjs');"
        "const d = await import('./control/dial.mjs');"
        "const s = await import('./control/sequencer.mjs');"
        "console.log(JSON.stringify({ GATE: g.GATE, ANTIGAMING: g.ANTIGAMING,"
        "  TRANSFER: gr.TRANSFER, INTERFERENCE: gr.INTERFERENCE,"
        "  BAND: d.BAND, BAND_CENTER: d.BAND_CENTER, DEFAULTS: d.DEFAULTS, STATES: d.STATES,"
        "  WEIGHTS: s.WEIGHTS, POLICY: s.POLICY,"
        "  RUNGS: h.RUNGS, HINT_POLICY: h.HINT_POLICY,"
        "  RUNG_CREDIT: lpa.RUNG_CREDIT, SIGMA_MAX: lpa.SIGMA_MAX, SIGMA_MIN: lpa.SIGMA_MIN,"
        "  LOGISTIC_WIDTH: lpa.LOGISTIC_WIDTH }));")
    proc = subprocess.run(
        ['node', '--input-type=module', '-e', script],
        cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError('cannot read the control modules through node:\n' + proc.stderr.strip())
    return json.loads(proc.stdout)


CONTROL = node_dump()
GATE = need(CONTROL, 'GATE', GATES_PATH)
TRANSFER = need(CONTROL, 'TRANSFER', GRAPH_PATH)
INTERFERENCE = need(CONTROL, 'INTERFERENCE', GRAPH_PATH)
BAND = need(CONTROL, 'BAND', DIAL_PATH)
DIAL_DEFAULTS = need(CONTROL, 'DEFAULTS', DIAL_PATH)
DIAL_STATES = need(CONTROL, 'STATES', DIAL_PATH)
WEIGHTS = need(CONTROL, 'WEIGHTS', SEQUENCER_PATH)
POLICY = need(CONTROL, 'POLICY', SEQUENCER_PATH)
RUNGS = need(CONTROL, 'RUNGS', HINTS_PATH)
HINT_POLICY = need(CONTROL, 'HINT_POLICY', HINTS_PATH)

if abs(sum(WEIGHTS.values()) - 1) > 1e-9:
    raise AssertionError(f'{SEQUENCER_PATH}: WEIGHTS sum to {sum(WEIGHTS.values())}, not 1; the '
                         'page renders each term as a share of the whole score')


def check_count(rel):
    """How many checks a control suite actually passes, read from its own run."""
    proc = subprocess.run(['node', rel], cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f'{rel} does not pass:\n' + (proc.stdout + proc.stderr)[-2000:])
    m = re.search(r'(\d+) checks passed', proc.stdout)
    if not m:
        raise AssertionError(f'{rel}: cannot read a check count out of its output')
    return int(m.group(1))


CONTROL_CHECKS = {rel: check_count(rel) for rel in CONTROL_TESTS}
N_CONTROL_CHECKS = sum(CONTROL_CHECKS.values())
N_CONTROL_LINES = sum(CONTROL_LINES.values())


def quote(rel, start, end):
    """One verbatim run of a source file, between two anchors, or fail by name."""
    text = (ROOT / rel).read_text()
    i = text.find(start)
    if i < 0:
        raise LookupError(f'{rel}: cannot find the opening anchor {start!r}')
    j = text.find(end, i + len(start))
    if j < 0:
        raise LookupError(f'{rel}: cannot find the closing anchor {end!r} after {start!r}')
    run = text[i:j + len(end)]
    # a doc comment's `*` gutter and a line comment's `//` are the comment's
    # shape, not the sentence's. Anchored at the start of every line, not
    # after a newline: a bare `//` line between two prose lines otherwise
    # left its marker behind in the middle of the quotation.
    run = re.sub(r'(?m)^[ \t]*(?:\*|//)[ \t]?', ' ', run)
    return re.sub(r'\s+', ' ', run).strip()


CERTIFIED_DOC = quote(GATES_PATH, 'Certification requires all three tiers', 'no shortcuts.')
CERTIFIED_EXPR = quote(GATES_PATH, 'return skillGates.every', 'jobsiteFinal?.pass === true;')
JOBSITE_DOC = quote(GATES_PATH, 'Jobsite final (tier 3)', "the union agent's oral check.")
JOBSITE_EXPR = quote(GATES_PATH, 'const pass = stepOrder', 'oral >= 2;')
GATES_RULE = quote(GATES_PATH, 'The rule that shapes everything here:', 'not what was inferred.')
GATE_QUALIFY_RULE = quote(GATES_PATH, 'Count QUALIFYING attempts only',
                          'nothing ever certified.')
GRAPH_RULE = quote(GRAPH_PATH, 'Governing rule', 'about them.')
VERIFY_RULE = quote(SEQUENCER_PATH, 'The dial holds practice at the band CENTRE',
                    'always 1.5 points too easy to count.')
FADE_RULE = quote(HINTS_PATH, 'Help is a loan against mastery credit',
                  'someone should say so.')
# The README is markdown; its emphasis markers are not part of the sentence.
NO_LLM_RULE = quote(CONTROL_README, '**The control plane has no LLM in it',
                    'rather than participants in it.').replace('**', '')
DIAL_CLAMP_RULE = quote(DIAL_PATH, 'Order: session cap first', 'is the SAFETY bound;')
SEQ_DEFENDS_RULE = quote(SEQUENCER_PATH, 'the layer where adaptive systems usually cheat',
                         'a score and a reason.')
IDENTITY_RULE = need(AUTH_HONESTY, 'local_identity_is_a_label', f'{AUTH_PATH}#honesty')
NO_BACKEND_RULE = need(AUTH_HONESTY, 'no_backend', f'{AUTH_PATH}#honesty')
TRAINING_SCOPE = need(TRAINING_STORAGE, 'scope', f'{TRAINING_PATH}#storage')
SIM_GRANULARITY = need(SIM_EPISODE, 'granularity', f'{TRAINING_PATH}#episode_kinds.sim')

# --------------------------------------------------------- the finding, measured
# The sentence at the top of this page is a measurement, so it is measured here
# and the number it states is the number this build counted. A symbol that
# turns up in the app tomorrow lands on the page as a count, not as a lie.
APP_SRC = (ROOT / APP_PATH).read_text()
APP_HITS = {name: APP_SRC.count(name) for name in
            ('LearnerProfile', 'ZpdDial', 'Sequencer', 'SkillGraph', 'checkSkillGate',
             'HintEngine', 'certified(')}
N_APP_HITS = sum(APP_HITS.values())


# ------------------------------------------------------------------ the ladder
STRANDS = []
for s in SKILLS:
    st = need(s, 'strand', f'{SKILLS_PATH}#skills[]')
    if st not in STRANDS:
        STRANDS.append(st)

_tier_after = {}
SKILL_BY_ID = {}
for s in SKILLS:
    sid = need(s, 'skill_id', f'{SKILLS_PATH}#skills[]')
    if sid in SKILL_BY_ID:
        raise AssertionError(f'{SKILLS_PATH}: skill_id {sid!r} appears twice')
    SKILL_BY_ID[sid] = s
for s in SKILLS:
    w = f'{SKILLS_PATH}#skills[{s["skill_id"]}]'
    tier = need(s, 'tier', w)
    _tier_after.setdefault(tier, set())
    for req in need(s, 'requires', w):
        if req not in SKILL_BY_ID:
            raise LookupError(f'{w}: requires {req!r}, which is in no skill record')
        prev = SKILL_BY_ID[req]
        if prev['strand'] == s['strand'] and prev['tier'] != tier:
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

BY_UNION = {}
for s in SKILLS:
    BY_UNION.setdefault(need(s, 'union', f'{SKILLS_PATH}#skills[]'), []).append(s)
for u, rows in BY_UNION.items():
    if u not in HALL_NAME:
        raise KeyError(f'{SKILLS_PATH}: skills name a union {u!r} that is in no hall record')
    for r in rows:
        w = f'{SKILLS_PATH}#skills[{r["skill_id"]}]'
        for kind in ('requires', 'supports', 'interferes'):
            for e in need(r, kind, w):
                if SKILL_BY_ID[e]['union'] != u:
                    raise AssertionError(
                        f'{w}.{kind}: {e!r} belongs to {SKILL_BY_ID[e]["union"]}, not {u}; this '
                        "page runs a hall's own graph and will not reach off it")

N_CELLS_PER_HALL = len(BY_UNION[HALLS[0]['slug']])
for u, rows in BY_UNION.items():
    if len(rows) != N_CELLS_PER_HALL:
        raise AssertionError(f'{SKILLS_PATH}: {u} has {len(rows)} cells, not {N_CELLS_PER_HALL}')
N_ROOTS_PER_HALL = sum(1 for s in BY_UNION[HALLS[0]['slug']] if not s['requires'])
for u, rows in BY_UNION.items():
    if sum(1 for s in rows if not s['requires']) != N_ROOTS_PER_HALL:
        raise AssertionError(f'{SKILLS_PATH}: {u} has a different number of root cells')
for s in SKILLS:
    if len(s['requires']) > 1:
        raise AssertionError(
            f'{SKILLS_PATH}: {s["skill_id"]} names {len(s["requires"])} prerequisites; the page '
            "states that a hall's ladder is a tree, one prerequisite per non-root cell")

# ---------------------------------------------------------------- the seats
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
        if SKILL_BY_ID[sid]['union'] != hall:
            raise AssertionError(f'{w}: {sid!r} belongs to {SKILL_BY_ID[sid]["union"]}, not {hall}')
        SEATS_BY_UNION.setdefault(hall, []).append([sim, sid])

N_HALLS = len(HALLS)
N_SKILLS = len(SKILLS)
N_STRANDS = len(STRANDS)
N_TIERS = len(TIERS)
N_SIMS = len(SIMS)
N_BOUND_HALLS = len(BINDINGS)
N_UNBOUND_HALLS = N_HALLS - N_BOUND_HALLS
# The reason a tc-progress seat pass cannot be attributed to a hall: the same
# seat stands in many halls and that record names none of them.
SIM_HALL_COUNT = {k: len(need(v, 'halls', f'{SIMS_PATH}#sims.{k}')) for k, v in SIMS.items()}
MAX_SIM_HALLS = max(SIM_HALL_COUNT.values())
MULTI_HALL_SIMS = sum(1 for n in SIM_HALL_COUNT.values() if n > 1)

# ------------------------------------------------------------------- provenance
TIERS_PROV = ('RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED', 'SCRIPTED')
PROV = (
    ('your record', 'RECORDED',
     f'what this browser wrote under {TRAINING_KEY} and {PROGRESS_KEY}, read at page load'),
    ('the ladder', 'AUTHORED', f'the skill graph in {SKILLS_PATH}, hand-built and unreviewed'),
    ('the seats', 'SCHEMATIC', f'schematic physics in {SIMS_PATH}, not equipment'),
    ('the reference operator', 'SCRIPTED',
     'a hand-written deterministic control policy, dropped from the replay because it is not you'),
    ('every decision below', 'DERIVED',
     f'arithmetic run by the real classes in {", ".join(CONTROL_MODULES)}, in this page'),
    ('the serve difficulty', 'DERIVED',
     'reconstructed by the dial, because the record stores none - see the replay panel'),
)
for _what, _t, _why in PROV:
    if _t not in TIERS_PROV:
        raise ValueError(f'provenance tier {_t!r} is not one of {", ".join(TIERS_PROV)}')

E = html.escape
F = lambda x: f'{x:,}'

# ---------------------------------------------------------------- the payload
DATA = {
    'product': PRODUCT,
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'strands': STRANDS,
    'tiers': TIERS,
    'keys': {'progress': PROGRESS_KEY, 'training': TRAINING_KEY,
             'training_on': TRAINING_ON_KEY, 'identity': IDENTITY_KEY},
    'human_actor': HUMAN_ACTOR,
    'scripted_actors': SCRIPTED_ACTORS,
    'training_cap': TRAINING_CAP,
    'halls': [
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
    'sims': {k: {'name': need(v, 'name', f'{SIMS_PATH}#sims.{k}'),
                 'halls': need(v, 'halls', f'{SIMS_PATH}#sims.{k}')}
             for k, v in SIMS.items()},
}
# `seats` is an explicit membership test rather than a defaulted lookup: an
# unbound hall has no entry in hall_bindings at all, and "this hall has no
# seat" is a fact read off the registry, not a value substituted for a missing
# one.
PAYLOAD = json.dumps(DATA, separators=(',', ':'), ensure_ascii=False)
if '</script' in PAYLOAD:
    raise AssertionError('the payload contains a </script close')

# ------------------------------------------------------------------------ html
NETWORK_FIGS = (
    ('control-lines', N_CONTROL_LINES,
     f'lines of control plane this page runs, across {F(len(CONTROL_MODULES))} modules'),
    ('control-checks', N_CONTROL_CHECKS, 'checks those modules pass in this repo'),
    ('app-hits', N_APP_HITS, f'times {APP_PATH} names any of them'),
    ('cells', N_CELLS_PER_HALL, "cells on one hall's ladder"),
    ('halls', N_HALLS, 'halls the ladder is drawn for'),
    ('sims', N_SIMS, 'simulator seats that can write a record'),
    ('unbound-halls', N_UNBOUND_HALLS, 'halls with no seat, and so no way to record anything'),
)
FIGS = ''.join(
    f'<div class="fig" data-fig="{E(key)}"><b>{E(F(n))}</b><span>{E(lab)}</span></div>'
    for key, n, lab in NETWORK_FIGS)

CONTROL_ROWS = ''.join(
    f'<tr data-module="{E(rel)}"><td class="k"><code>{E(rel)}</code></td>'
    f'<td class="num">{E(F(CONTROL_LINES[rel]))}</td><td>{E(what)}</td></tr>'
    for rel, what in (
        (LPA_PATH, 'LearnerProfile — the single writer of the proficiency vector: Elo co-update, '
                   'the BKT posterior and the evidence shrinkage on it, sigma, velocity, decay'),
        (HINTS_PATH, 'HintEngine and the rung ladder — what each rung of help costs, how high the '
                     'ladder reaches right now, and when it fades'),
        (GRAPH_PATH, 'SkillGraph — readiness, leverage, one-hop credit propagation, interference, '
                     'and the diagnosis when a learner is stuck'),
        (GATES_PATH, 'the gates — checkSkillGate, scoreLevelTest, scoreJobsiteFinal, certified, '
                     'and the anti-gaming detectors'),
        (DIAL_PATH, 'ZpdDial — the closed-loop difficulty setpoint, and the affect classifier '
                    'that decides whether to sit above or below the band'),
        (SEQUENCER_PATH, 'Sequencer — which skill next and why: the working set, the review '
                         'queue, the interleaving rule, verification and the wheel-spin detector'),
    ))

TEST_ROWS = ''.join(
    f'<tr data-suite="{E(rel)}"><td class="k"><code>{E(rel)}</code></td>'
    f'<td class="num">{E(F(CONTROL_CHECKS[rel]))}</td></tr>' for rel in CONTROL_TESTS)

WEIGHT_ROWS = ''.join(
    f'<tr data-weight-term="{E(k)}"><td class="k">{E(k)}</td><td class="num">{E(str(v))}</td>'
    f'<td>{E(why)}</td></tr>'
    for k, v, why in (
        ('zpd_fit', WEIGHTS['zpd_fit'],
         'how close the dial can place this skill to the middle of the target band'),
        ('review_urgency', WEIGHTS['review_urgency'],
         'how far the modelled recall on this skill has fallen below the review threshold'),
        ('graph_leverage', WEIGHTS['graph_leverage'],
         'how many still-locked skills this one would unblock'),
        ('modality_fit', WEIGHTS['modality_fit'],
         'whether the modality asked for matches; no modality is asked for here, so this term '
         'sits at its neutral value for every candidate and separates none of them'),
        ('novelty', WEIGHTS['novelty'], 'how little this skill has been served already'),
    ))

DIAL_ROWS = ''.join(
    f'<tr data-dial-const="{E(k)}"><td class="k">{E(k)}</td><td class="num">{E(str(v))}</td>'
    f'<td>{E(why)}</td></tr>'
    for k, v, why in (
        ('BAND.lo', BAND['lo'], 'the bottom of the target success band'),
        ('BAND.hi', BAND['hi'], 'the top of it'),
        ('setpointOffset', DIAL_DEFAULTS['setpointOffset'],
         'practice is served this far below your own level, which is the band centre'),
        ('window', DIAL_DEFAULTS['window'], 'attempts the dial waits before it moves at all'),
        ('loopGain', DIAL_DEFAULTS['loopGain'],
         'how far it moves toward what the observed success rate implies'),
        ('stepDown', DIAL_DEFAULTS['stepDown'], 'how far it eases off — faster than it steps up'),
        ('stepUpBase', DIAL_DEFAULTS['stepUpBase'], 'how far it raises the challenge'),
        ('railLo', DIAL_DEFAULTS['railLo'], 'the safety rail below your level'),
        ('railHi', DIAL_DEFAULTS['railHi'], 'the safety rail above it'),
        ('sessionDelta', DIAL_DEFAULTS['sessionDelta'],
         'how far the setpoint may move within one session'),
        ('recoveryDrop', DIAL_DEFAULTS['recoveryDrop'],
         'where it steps back to after two failed windows'),
    ))

GATE_ROWS = ''.join(
    f'<tr data-gate-const="{E(k)}"><td class="k">{E(k)}</td><td class="num">{E(str(v))}</td>'
    f'<td>{E(why)}</td></tr>'
    for k, v, why in (
        ('GATE.masteryThreshold', GATE['masteryThreshold'],
         'the posterior a gate needs before a demonstration is even considered'),
        ('GATE.consecutiveUnaided', GATE['consecutiveUnaided'],
         'consecutive unaided successes at level a gate needs'),
        ('GATE.atOrAbove', GATE['atOrAbove'],
         "a demonstration only counts at or above this, relative to your own level"),
        ('GATE.levelTest.questions', need(GATE['levelTest'], 'questions', GATES_PATH),
         'the level test: fixed difficulty, no hints, shuffled per sitting'),
        ('GATE.levelTest.passPct', need(GATE['levelTest'], 'passPct', GATES_PATH),
         'its pass mark, in percent'),
        ('GATE.levelTest.retakeLockHours', need(GATE['levelTest'], 'retakeLockHours', GATES_PATH),
         'hours a failed sitting is locked before a retake'),
        ('POLICY.verifyAtOrAbove', POLICY['verifyAtOrAbove'],
         'the difficulty the sequencer serves a verification run at'),
        ('POLICY.verifyRun', POLICY['verifyRun'], 'attempts one verification run is'),
        ('POLICY.verifyMinEvidence', POLICY['verifyMinEvidence'],
         'attempts on a skill before proof is worth spending one on'),
    ))

RUNG_ROWS = ''.join(
    f'<tr data-rung="{E(str(need(r, "rung", HINTS_PATH)))}" '
    f'data-credit="{E(str(need(r, "credit", HINTS_PATH)))}">'
    f'<td class="num">{E(str(r["rung"]))}</td><td class="k">{E(need(r, "name", HINTS_PATH))}</td>'
    f'<td class="num">{E("%.2f" % r["credit"])}</td><td>{E(need(r, "does", HINTS_PATH))}</td></tr>'
    for r in RUNGS)

HINT_ROWS = ''.join(
    f'<tr data-hint-const="{E(k)}"><td class="k">{E(k)}</td><td class="num">{E(str(v))}</td>'
    f'<td>{E(why)}</td></tr>'
    for k, v, why in (
        ('dwellSeconds', need(HINT_POLICY, 'dwellSeconds', HINTS_PATH),
         'seconds since your last action before the next hint is served at all — the pause is '
         'where the thinking happens, and asking again inside it is refused with that sentence'),
        ('maxRung', need(HINT_POLICY, 'maxRung', HINTS_PATH),
         'the highest rung the ladder reaches, ever'),
        ('socraticMaxTurns', need(HINT_POLICY, 'socraticMaxTurns', HINTS_PATH),
         'the turn ceiling: on a conceptual skill a rung-2 escalation becomes a bounded '
         'dialogue, and this is how many turns it may run before it stops'),
        ('fadeWindow', need(HINT_POLICY, 'fadeWindow', HINTS_PATH),
         'attempts your hint dependence is measured over'),
        ('fadeThreshold', need(HINT_POLICY, 'fadeThreshold', HINTS_PATH),
         'the sustained dependence that opens a fading contract'),
        ('fadeContractTasks', need(HINT_POLICY, 'fadeContractTasks', HINTS_PATH),
         'tasks that contract then serves one rung lower than you asked for — named out loud, '
         'because a system that quietly makes help worse is a system nobody trusts'),
    ))

PROV_CHIPS = ''.join(
    f'<span class="prov" data-tier="{E(t)}">{E(what)} — {E(t)} — {E(why)}</span>'
    for what, t, why in PROV)

READS = ''.join(f'<li><code>{E(p)}</code> — {E(why)}</li>' for p, why in (
    (SKILLS_PATH, "every hall's cells and the prerequisite, support and interference edges "
                  'between them — the graph SkillGraph is given'),
    (SIMS_PATH, 'hall_bindings: which seat proves which cell, which is the only hall-attributed '
                'bridge from a recorded run to a skill'),
    (HALLS_PATH, "each hall's name, focus and order"),
    (AUTH_PATH, f'the record key names {PROGRESS_KEY} and {TRAINING_KEY}, the identity key '
                f'{IDENTITY_KEY}, and what a local identity is and is not'),
    (TRAINING_PATH, 'the episode shape, the actor names, the rolling cap and the recorder toggle'),
    (MANIFEST_PATH, 'the pack version and the pack\'s own honesty block'),
    (LPA_PATH, 'LearnerProfile and pSuccess — carried into the page and run, not quoted'),
    (HINTS_PATH, 'HintEngine, RUNGS and the fading policy — carried in and run'),
    (GRAPH_PATH, 'SkillGraph — carried in and run'),
    (GATES_PATH, 'checkSkillGate, scoreLevelTest, scoreJobsiteFinal, certified — carried in and '
                 'run, and the certification expression quoted verbatim'),
    (DIAL_PATH, 'ZpdDial and the affect classifier — carried in and run'),
    (SEQUENCER_PATH, 'Sequencer, WEIGHTS and POLICY — carried in and run'),
    (CONTROL_README, 'why the control plane has no model in it'),
    (APP_PATH, f'counted, not read: how many times the app names any control class ({F(N_APP_HITS)})'),
))

LIMITS = ''.join(f'<li><b>{E(k)}</b>{E(v)}</li>' for k, v in (
    ('there is no server behind this', NO_BACKEND_RULE),
    ('whose record this is', IDENTITY_RULE),
    ('where the record lives', TRAINING_SCOPE),
    ('how coarse the record is', SIM_GRANULARITY),
    ('what a run is scored against', SCORING_CONTRACT),
    ('what the seat is', need(SIMS_HONESTY, 'status', f'{SIMS_PATH}#honesty')),
    ('what the lesson content is', need(PACK_HONESTY, 'content', f'{MANIFEST_PATH}#honesty')),
))


# --------------------------------------------------------------------- script
# The page's own renderer. Everything a learner reads below is produced by the
# control classes above it in the same module script - this code reads their
# answers and lays them out. It computes no policy of its own: there is no
# second opinion here about readiness, difficulty, gating or fading.
RENDER = r'''
const D = JSON.parse(document.getElementById('tcdata').textContent);
const HALLS = new Map(D.halls.map((h) => [h.slug, h]));
const KEYS = D.keys;
const DAY_MS = 86400000;

/* ---------------------------------------------------------------- helpers */
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
function row(cells, attrs) {
  return elem('tr', attrs, cells.map((c) => (c && c.nodeType) ? c : elem('td', { text: String(c) })));
}
const td = (text, cls) => elem('td', cls ? { class: cls, text: String(text) } : { text: String(text) });
const n1 = (x) => (Number.isFinite(x) ? x.toFixed(1) : '—');
const n2 = (x) => (Number.isFinite(x) ? x.toFixed(2) : '—');
const n3 = (x) => (Number.isFinite(x) ? x.toFixed(3) : '—');
const pc = (x) => (Number.isFinite(x) ? Math.round(x * 100) + '%' : '—');

/* ------------------------------------------------------- the device record */
/* Absent, blocked and unreadable are three different answers and the panel
   below says which one it got. A record that cannot be read is NOT an empty
   record: reporting a blocked store as "no training yet" would tell a learner
   their work was never there. */
function readRaw(key) {
  try { return { ok: true, raw: localStorage.getItem(key) }; }
  catch (e) { return { ok: false, raw: null, note: String((e && e.message) || e) }; }
}
function readJson(key) {
  const r = readRaw(key);
  if (!r.ok) return { state: 'blocked', value: null, note: r.note };
  if (r.raw === null) return { state: 'absent', value: null, note: '' };
  try { return { state: 'present', value: JSON.parse(r.raw), note: '', bytes: r.raw.length }; }
  catch (e) { return { state: 'unreadable', value: null, note: String((e && e.message) || e) }; }
}

function readRecord() {
  const training = readJson(KEYS.training);
  if (training.state === 'present' && !Array.isArray(training.value)) {
    training.state = 'unreadable';
    training.note = 'the record under ' + KEYS.training + ' is not an array of episodes';
    training.value = null;
  }
  const progress = readJson(KEYS.progress);
  const identity = readJson(KEYS.identity);
  const on = readRaw(KEYS.training_on);
  return {
    training, progress, identity,
    /* the app's own default: the recorder is ON unless this key says '0' */
    recorderOn: on.ok ? (on.raw === null ? true : on.raw === '1') : null,
    recorderSet: on.ok ? on.raw !== null : false,
  };
}

/* Every sim episode the record holds, by hall, so the picker can offer the
   halls this device actually has a record for rather than a hall of its own
   choosing. */
function hallsInRecord(rec) {
  const out = new Map();
  const eps = Array.isArray(rec.training.value) ? rec.training.value : [];
  for (const ep of eps) {
    if (!ep || ep.kind !== 'sim' || ep.actor !== D.human_actor) continue;
    if (!HALLS.has(ep.hall)) continue;
    out.set(ep.hall, (out.has(ep.hall) ? out.get(ep.hall) : 0) + 1);
  }
  return out;
}

/* --------------------------------------------------------------- the replay */
/**
 * Run the control plane over one hall's record.
 *
 * THE ONE RECONSTRUCTION, named here rather than buried. `LearnerProfile.record`
 * needs the difficulty an attempt was served at, and the episode record stores
 * none - the app never asked the dial what to serve, which is the whole finding
 * this page exists for. So the replay serves each recorded outcome at the
 * difficulty the dial WOULD have chosen at that point, stepping the dial
 * forward as it goes. That is a reconstruction and it is labelled one
 * everywhere it shows.
 *
 * Its consequence is the honest one, and it is stamped rather than argued:
 * every replayed attempt carries `gate_qualifying: false`, because the record
 * does not say at what difficulty the run was served and a gate may only count
 * a demonstration whose difficulty was stamped AT SERVE TIME. So no replayed
 * attempt can ever qualify for a skill gate, and the gate panel says exactly
 * that, in gates.mjs's own words.
 */
function replay(slug, rec) {
  const hall = HALLS.get(slug);
  if (!hall) throw new Error('progress: no hall record for ' + slug);
  const skills = hall.cells.map((c) => ({
    skill_id: c[0], label: c[1], strand: D.strands[c[2]], tier: D.tiers[c[3]],
    requires: c[4], supports: c[5], interferes: c[6],
  }));
  const allIds = skills.map((s) => s.skill_id);
  const idSet = new Set(allIds);
  const seatSkill = new Map();
  for (const pair of hall.seats) {
    const sim = pair[0], sid = pair[1];
    if (!idSet.has(sid)) {
      throw new Error('progress: hall_bindings.' + slug + ' binds seat ' + sim + ' to ' + sid
        + ', which is not a cell of this hall');
    }
    if (seatSkill.has(sim) && seatSkill.get(sim) !== sid) {
      throw new Error('progress: hall_bindings.' + slug + ' binds seat ' + sim
        + ' to two different cells');
    }
    seatSkill.set(sim, sid);
  }

  /* --- triage: what the record determines, and what it does not --- */
  const tri = { determined: [], scripted: 0, otherHall: 0, otherKind: 0,
                unbound: new Map(), noOutcome: 0, noStamp: 0 };
  const eps = Array.isArray(rec.training.value) ? rec.training.value : [];
  for (const ep of eps) {
    if (!ep || ep.kind !== 'sim') { tri.otherKind++; continue; }
    if (ep.hall !== slug) { tri.otherHall++; continue; }
    if (ep.actor !== D.human_actor) { tri.scripted++; continue; }
    if (!seatSkill.has(ep.sim)) {
      tri.unbound.set(ep.sim, (tri.unbound.has(ep.sim) ? tri.unbound.get(ep.sim) : 0) + 1);
      continue;
    }
    const o = ep.outcome;
    if (!o || typeof o.passed !== 'boolean') { tri.noOutcome++; continue; }
    const t = Date.parse(ep.t);
    if (!Number.isFinite(t)) tri.noStamp++;
    tri.determined.push({ skill: seatSkill.get(ep.sim), sim: ep.sim, correct: o.passed,
                          t: Number.isFinite(t) ? t : null });
  }

  /* --- the machinery, the real classes --- */
  const profile = new LearnerProfile(slug);
  const graph = new SkillGraph(skills);
  const dial = new ZpdDial(profile);
  const hintEngine = new HintEngine(profile);
  let day = 0;
  const seq = new Sequencer(graph, profile, dial, { clock: () => day });
  const history = [];
  const steps = [];
  const stamped = tri.determined.filter((a) => a.t !== null);
  const t0 = stamped.length ? stamped[0].t : null;
  const lastDay = new Map();
  let sessions = 0, reentries = 0, fades = 0;

  for (const a of tri.determined) {
    if (a.t !== null && t0 !== null) day = Math.floor((a.t - t0) / DAY_MS);
    const prev = lastDay.has(a.skill) ? lastDay.get(a.skill) : null;
    /* A session boundary. The record carries no session marker of any kind, so
       this is the one thing the replay reads out of the timestamps: a new
       calendar day in the record's OWN stamps is treated as a new session, and
       `startSession()` re-anchors the dial's session cap there. Leaving it
       stale is how a dial silently freezes, which control/dial.mjs documents
       as its v1.1 defect 1. */
    if (prev === null) { dial.startSession(a.skill); sessions++; }
    else if (day > prev) {
      const re = dial.reentry(a.skill, day - prev);
      if (re) reentries++;
      dial.startSession(a.skill);
      sessions++;
    }
    lastDay.set(a.skill, day);

    const cal = seq.calibrationPick(a.skill);
    const difficulty = cal ? cal.difficulty : dial.setpoint(a.skill);
    const weight = graph.interferenceWeight(a.skill, history.map((h) => h.skill));
    const r = profile.record(a.skill, { difficulty, correct: a.correct, rung: 0, weight });
    const moved = graph.propagate(profile, a.skill, r.delta, { correct: a.correct });
    const fade = hintEngine.record(a.skill, { rung: 0 });
    if (fade) fades++;
    const obs = dial.observe(a.skill, { correct: a.correct, rung: 0, difficulty });
    history.push({ skill: a.skill, difficulty, correct: a.correct, rung: 0,
                   gate_qualifying: false, t: a.t });
    seq.record(a.skill, { correct: a.correct, mode: cal ? 'calibrating' : 'frontier' });
    steps.push({ skill: a.skill, sim: a.sim, correct: a.correct, difficulty, day,
                 mode: cal ? 'calibrating' : 'frontier', weight,
                 expected: r.expected, delta: r.delta, theta: r.theta,
                 propagated: moved.length, observed: obs });
  }

  /* --- the ladder, snapshotted before anything else touches the profile --- */
  const touched = new Set([...profile.skills.keys()]);
  const nodes = skills.map((s) => {
    const st = profile.get(s.skill_id);
    return {
      id: s.skill_id, label: s.label, strand: s.strand, tier: s.tier,
      si: D.strands.indexOf(s.strand), ti: D.tiers.indexOf(s.tier),
      requires: s.requires, supports: s.supports, interferes: s.interferes,
      touched: touched.has(s.skill_id),
      attempts: history.filter((h) => h.skill === s.skill_id).length,
      theta: st.theta, sigma: st.sigma, mastery: st.p_mastery,
      evidence: st.evidence_n, indirect: st.indirect_n === undefined ? 0 : st.indirect_n,
      consecutive: st.consecutive_unaided,
      ready: graph.ready(s.skill_id, profile, POLICY.readyThreshold),
      leverage: graph.leverage(s.skill_id, profile, POLICY.readyThreshold),
      seats: hall.seats.filter((p) => p[1] === s.skill_id).map((p) => p[0]),
    };
  });

  /* --- the gates. checkSkillGate is asked; nothing here decides. --- */
  const gates = nodes.map((nd) => {
    const g = checkSkillGate(profile, nd.id, history);
    const mine = history.filter((h) => h.skill === nd.id);
    return {
      id: nd.id, strand: nd.strand, tier: nd.tier,
      pass: g.pass, believed: g.believed, demonstrated: g.demonstrated, why: g.why,
      mastery: nd.mastery, attempts: mine.length,
      unaided: mine.filter((h) => h.rung === 0).length,
      qualifying: mine.filter((h) => h.rung === 0 && h.gate_qualifying === true).length,
    };
  });
  /* certified() is CALLED, with the level test and the jobsite final this
     bundle does not have - which is to say with null. The answer is the
     module's, not this page's. */
  const cert = certified({ skillGates: gates, levelTest: null, jobsiteFinal: null });

  /* --- what the sequencer considered, captured before next() scores anything
         and instantiates the candidates --- */
  seq.refreshWorkingSet();
  const dueList = seq.reviewDue();
  const reviewSet = new Map(dueList.map((d) => [d.skill, d.recall]));
  let pool = [...new Set([...seq.workingSet, ...dueList.map((d) => d.skill)])];
  let poolFrom = 'the working set and the review queue';
  if (!pool.length) { pool = seq.frontier().slice(0, POLICY.workingSetMax); poolFrom = 'the frontier'; }
  if (!pool.length) {
    pool = seq.unlocked(allIds).slice(0, POLICY.workingSetMax);
    poolFrom = 'the skills you have not started whose prerequisites are met';
  }
  const workingSet = [...seq.workingSet];

  let pick = null, pickError = null;
  try { pick = seq.next(allIds, history); }
  catch (e) { pickError = String((e && e.message) || e); }

  /* score the pool for display, with the sequencer's own scorer */
  const scored = pool.map((id) => ({ id, parts: seq.score(id, { reviewSet }) }))
    .sort((a, b) => b.parts.total - a.parts.total);

  /* --- the dial, on the skill the sequencer picked --- */
  let dialView = null;
  if (pick) {
    const st = dial.state(pick.skill);
    const sp = dial.setpoint(pick.skill);
    dialView = {
      skill: pick.skill, setpoint: sp, served: pick.difficulty,
      state: st.dialState, pinned: st.pinned,
      theta: profile.get(pick.skill).theta, sigma: profile.get(pick.skill).sigma,
      pAtSetpoint: dial.predictedSuccess(pick.skill, sp),
      pAtServed: dial.predictedSuccess(pick.skill, pick.difficulty),
      windowFilled: st.window.length, windowNeeds: DEFAULTS.window,
      failedWindows: st.failedWindows,
      last: st.history.length ? st.history[st.history.length - 1] : null,
      moves: st.history.length,
    };
  }

  /* --- the help ladder, on the same skill. These two requests are queries:
         the engine is ASKED what it would serve right now, once with no dwell
         and once with the dwell its own policy requires. --- */
  let hintView = null;
  if (pick) {
    const hs = hintEngine.state(pick.skill);
    const taskCeiling = pick.scaffold_ceiling === undefined ? null : pick.scaffold_ceiling;
    hintView = {
      skill: pick.skill,
      mastery: profile.get(pick.skill).p_mastery,
      fromMastery: masteryCeiling(profile.get(pick.skill).p_mastery),
      taskCeiling,
      ceiling: hintEngine.ceiling(pick.skill, taskCeiling),
      dependence: hintEngine.dependence(pick.skill),
      windowFilled: hs.window.length,
      contract: hs.fadeContract, contractsOpened: hs.contractsOpened,
      noDwell: hintEngine.request(pick.skill, { rung: 1, dwellSeconds: 0,
                                                taskCeiling, skill: pick.skill }),
      withDwell: hintEngine.request(pick.skill, { rung: 1,
                                                 dwellSeconds: HINT_POLICY.dwellSeconds,
                                                 taskCeiling, skill: pick.skill }),
    };
  }

  return { slug, hall, skills, allIds, seatSkill, tri, profile, graph, dial, seq,
           history, steps, nodes, gates, cert, pool, poolFrom, workingSet, dueList,
           scored, pick, pickError, dialView, hintView,
           sessions, reentries, fades, days: t0 === null ? null : day + 1 };
}
'''

RENDER2 = r'''
/* ------------------------------------------------------------- the painting */
const COLW = 250, ROWH = 62, PADX = 12, PADY = 30, BOXW = 214, BOXH = 46;
const cx = (t) => PADX + t * COLW;
const cy = (s) => PADY + s * ROWH;

function edgePath(from, to) {
  const x1 = cx(from.ti), y1 = cy(from.si) + BOXH / 2;
  const x2 = cx(to.ti), y2 = cy(to.si) + BOXH / 2;
  if (from.si === to.si) return 'M ' + (x2 + BOXW) + ' ' + y2 + ' L ' + x1 + ' ' + y1;
  const mx = x2 + BOXW / 2;
  return 'M ' + mx + ' ' + (y2 + BOXH / 2) + ' L ' + mx + ' ' + (y1 - 2)
       + ' L ' + (x1 - 6) + ' ' + (y1 - 2) + ' L ' + x1 + ' ' + y1;
}

function paintRecord(rec) {
  const tb = document.getElementById('recstate');
  clear(tb);
  const eps = Array.isArray(rec.training.value) ? rec.training.value : [];
  const prog = (rec.progress.state === 'present' && rec.progress.value
                && typeof rec.progress.value === 'object') ? rec.progress.value : null;
  const simRec = (prog && prog.sims && typeof prog.sims === 'object') ? prog.sims : null;
  const simKeys = simRec ? Object.keys(simRec) : [];
  const stationCount = (prog && Array.isArray(prog.stations)) ? prog.stations.length : 0;
  const lines = [
    [KEYS.training, rec.training.state,
     rec.training.state === 'present'
       ? eps.length + ' episode(s), of a rolling cap of ' + D.training_cap
       : rec.training.note || 'nothing under this key'],
    [KEYS.training_on, rec.recorderOn === null ? 'blocked'
       : (rec.recorderSet ? 'set' : 'unset'),
     rec.recorderOn === null ? 'this browser refused the store'
       : rec.recorderOn
         ? 'the episode recorder is ON, so seat runs land in the record'
         : 'the episode recorder is OFF: seat runs are happening and nothing is being written, '
           + 'so this page has nothing to read no matter how much you play'],
    [KEYS.progress, rec.progress.state,
     rec.progress.state === 'present'
       ? simKeys.length + ' seat(s) with a run count, ' + stationCount + ' station(s) completed'
       : rec.progress.note || 'nothing under this key'],
    [KEYS.identity, rec.identity.state,
     rec.identity.state === 'present' ? 'a local label is set on this device'
       : rec.identity.note || 'no local label on this device'],
  ];
  for (const [k, state, note] of lines) {
    tb.appendChild(row([elem('td', { class: 'k' }, [elem('code', { text: k })]),
                        td(state, 'num'), td(note, 'muted')],
                       { 'data-key': k, 'data-key-state': state }));
  }

  const figs = document.getElementById('recfigs');
  clear(figs);
  const human = eps.filter((e) => e && e.kind === 'sim' && e.actor === D.human_actor).length;
  const scripted = eps.filter((e) => e && e.kind === 'sim' && e.actor !== D.human_actor).length;
  const pairs = [
    ['episodes', eps.length, 'episodes in the record, of every kind'],
    ['your-runs', human, 'seat runs this record attributes to you'],
    ['scripted-runs', scripted,
     'seat runs by the scripted reference operator — dropped, they are not you'],
    ['prog-seats', simKeys.length,
     'seats with a run count under ' + KEYS.progress + ' — counted, fed to nothing'],
    ['prog-stations', stationCount, 'stations marked complete — counted, fed to nothing'],
  ];
  for (const [key, n, lab] of pairs) {
    figs.appendChild(elem('div', { class: 'fig', 'data-rec': key },
      [elem('b', { text: String(n) }), elem('span', { text: lab })]));
  }

  const idl = document.getElementById('idline');
  clear(idl);
  const idv = rec.identity.value;
  const label = (idv && typeof idv === 'object' && typeof idv.label === 'string') ? idv.label : null;
  idl.setAttribute('data-identity', label === null ? 'none' : 'label');
  idl.textContent = label === null
    ? 'No local label is set on this device, so this record is a browser’s and not a person’s.'
    : 'This device labels the record ' + label + '. That is a label, not a login.';
}

function paintEmpty(rec, hallsSeen, slug) {
  const box = document.getElementById('emptynote');
  clear(box);
  const total = hallsSeen.size;
  if (slug === null) {
    box.setAttribute('data-empty', total ? 'unpicked' : 'no-record');
    box.appendChild(elem('p', { class: 'why', text: total
      ? 'This device has a record for ' + total + ' hall(s). Pick one above and the control '
        + 'plane will run on it.'
      : 'There is no training record on this device. Nothing below is anybody’s history: '
        + 'pick a hall above and every panel will run the real control plane on an EMPTY '
        + 'profile, so you can see what it does before it has anything to go on. This page '
        + 'will not invent a learner to fill the space.' }));
    return;
  }
  const mine = hallsSeen.has(slug) ? hallsSeen.get(slug) : 0;
  box.setAttribute('data-empty', mine ? 'has-record' : 'empty-profile');
  box.appendChild(elem('p', { class: 'why', text: mine
    ? 'This device recorded ' + mine + ' seat run(s) in this hall. Everything below is the '
      + 'control plane run over those runs, and nothing else.'
    : 'This device has recorded nothing in this hall. Everything below is the real control '
      + 'plane running on an EMPTY profile — no history has been invented for you, and '
      + 'every number is what the modules answer when they have been told nothing.' }));
}

function paintReplay(R) {
  const tb = document.getElementById('replaytbl');
  clear(tb);
  const t = R.tri;
  const rows = [
    ['fed to the profile', t.determined.length,
     'sim episodes in this hall, by you, whose outcome the record states'],
    ['dropped: not you', t.scripted,
     'runs by the scripted reference operator — a robot’s run is not your evidence'],
    ['dropped: another hall', t.otherHall, 'episodes recorded in a different hall'],
    ['dropped: not a seat run', t.otherKind,
     'episodes of another kind — an advisor or crew exchange carries no outcome'],
    ['dropped: seat not on this ladder', [...t.unbound.values()].reduce((a, b) => a + b, 0),
     t.unbound.size
       ? 'seat(s) ' + [...t.unbound.keys()].join(', ') + ' are bound to no cell of this hall'
       : 'none'],
    ['dropped: no outcome', t.noOutcome, 'episodes with no pass/fail in them'],
    ['no readable timestamp', t.noStamp,
     'episodes the review scheduler could not place in time; the replay held the clock still '
     + 'for those'],
  ];
  for (const [k, n, why] of rows) {
    tb.appendChild(row([td(k, 'k'), td(n, 'num'), td(why, 'muted')],
                       { 'data-triage': k, 'data-triage-n': String(n) }));
  }
  const note = document.getElementById('replaynote');
  clear(note);
  note.setAttribute('data-replay-days', R.days === null ? 'none' : String(R.days));
  note.setAttribute('data-replay-sessions', String(R.sessions));
  note.setAttribute('data-replay-qualifying',
    String(R.history.filter((h) => h.gate_qualifying === true).length));
  note.appendChild(elem('p', { class: 'why', text:
    R.history.length
      ? 'The replay stepped through ' + R.history.length + ' attempt(s) across '
        + (R.days === null ? 'an unknown number of' : R.days) + ' day(s) of the record, opening '
        + R.sessions + ' session(s) and ' + R.reentries + ' protected re-entr(ies), and '
        + 'propagated credit one hop along the graph after each one.'
      : 'There is nothing to replay in this hall, so every module below is answering from a '
        + 'standing start.' }));
  note.appendChild(elem('p', { class: 'muted', text:
    'Every one of those attempts is stamped gate_qualifying: false, because the record does '
    + 'not say what difficulty the run was served at and a gate may only count a demonstration '
    + 'whose difficulty was stamped when it was served. That is why the gate panel below reads '
    + 'the way it does, and it is the honest reading, not a limitation of this page.' }));
}

function paintLadder(R) {
  const svg = document.getElementById('ladder');
  clear(svg);
  const pos = new Map(R.nodes.map((n) => [n.id, n]));
  const W = PADX * 2 + D.tiers.length * COLW - (COLW - BOXW);
  const H = PADY + D.strands.length * ROWH + 10;
  svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  svg.setAttribute('width', W);
  svg.setAttribute('height', H);
  for (let t = 0; t < D.tiers.length; t++) {
    const lab = svgEl('text', { x: cx(t), y: 18, class: 'colhead' });
    lab.textContent = D.tiers[t];
    svg.appendChild(lab);
  }
  const edges = svgEl('g', { class: 'edges' });
  svg.appendChild(edges);
  let nEdges = 0;
  for (const kind of ['requires', 'supports', 'interferes']) {
    for (const nd of R.nodes) {
      for (const other of nd[kind]) {
        if (!pos.has(other)) {
          throw new Error('progress: ' + nd.id + ' ' + kind + ' ' + other
            + ', which is not a cell of ' + R.slug);
        }
        edges.appendChild(svgEl('path', { d: edgePath(nd, pos.get(other)), class: 'edge ' + kind,
          'data-edge': kind, 'data-from': nd.id, 'data-to': other }));
        if (kind === 'requires') nEdges++;
      }
    }
  }
  const gateOf = new Map(R.gates.map((g) => [g.id, g]));
  const g = svgEl('g', { class: 'nodes' });
  svg.appendChild(g);
  let nReady = 0, nTouched = 0, nAttempted = 0;
  for (const nd of R.nodes) {
    const gt = gateOf.get(nd.id);
    if (gt === undefined) throw new Error('progress: no gate record for ' + nd.id);
    if (nd.ready) nReady++;
    if (nd.touched) nTouched++;
    if (nd.attempts) nAttempted++;
    const cls = 'cell' + (nd.touched ? ' touched' : '')
      + (nd.ready ? ' ready' : ' locked')
      + (R.pick && R.pick.skill === nd.id ? ' picked' : '');
    const box = svgEl('g', { class: cls,
      'data-skill': nd.id, 'data-strand': nd.strand, 'data-tier': nd.tier,
      'data-ready': String(nd.ready), 'data-attempts': String(nd.attempts),
      'data-evidence': String(nd.evidence), 'data-theta': n1(nd.theta),
      'data-sigma': n1(nd.sigma), 'data-mastery': n3(nd.mastery),
      'data-leverage': String(nd.leverage),
      /* believed, demonstrated and passed are three different words and the
         module owns all three. `data-mastered` is bound to the GATE, never to
         the posterior: a belief is not a claim. */
      'data-believed': String(gt.believed),
      'data-demonstrated': String(gt.demonstrated),
      'data-gate-pass': String(gt.pass),
      'data-mastered': String(gt.pass),
      'data-picked': String(Boolean(R.pick && R.pick.skill === nd.id)) });
    box.appendChild(svgEl('rect', { x: cx(nd.ti), y: cy(nd.si), width: BOXW, height: BOXH, rx: 6 }));
    const t1 = svgEl('text', { x: cx(nd.ti) + 9, y: cy(nd.si) + 17, class: 'cname' });
    t1.textContent = nd.strand;
    box.appendChild(t1);
    const t2 = svgEl('text', { x: cx(nd.ti) + 9, y: cy(nd.si) + 31, class: 'cmark' });
    t2.textContent = nd.touched
      ? 'θ ' + n1(nd.theta) + ' · p ' + n2(nd.mastery) + ' · n ' + nd.evidence
      : (nd.ready ? 'ready, nothing recorded' : 'locked');
    box.appendChild(t2);
    const t3 = svgEl('text', { x: cx(nd.ti) + 9, y: cy(nd.si) + 43, class: 'cgate' });
    t3.textContent = gt.pass ? 'gate passed'
      /* the box is a fixed width, so the label names the first seat and
         counts the rest rather than running off the end of it into the
         next column */
      : !nd.seats.length ? 'no gate · no seat'
      : nd.seats.length === 1 ? 'no gate · seat: ' + nd.seats[0]
      : 'no gate · ' + nd.seats.length + ' seats: ' + nd.seats[0]
        + ' +' + (nd.seats.length - 1);
    box.appendChild(t3);
    box.appendChild(svgEl('title', {})).textContent = nd.label;
    g.appendChild(box);
  }
  const sum = document.getElementById('laddersum');
  clear(sum);
  const drawn = svg.querySelectorAll('[data-skill]');
  const pairs = [
    ['cells', drawn.length, 'cells on this hall’s ladder'],
    ['edges', nEdges, 'prerequisite edges between them'],
    ['attempted', nAttempted, 'cells you have actually attempted'],
    ['touched', nTouched,
     'cells the graph has moved: those, plus their neighbours one hop away'],
    ['ready', nReady, 'cells whose prerequisites are met'],
    ['gates', svg.querySelectorAll('[data-gate-pass="true"]').length, 'skill gates passed'],
  ];
  for (const [key, n, lab] of pairs) {
    sum.appendChild(elem('div', { class: 'fig', 'data-ladder': key },
      [elem('b', { text: String(n) }), elem('span', { text: lab })]));
  }
}
'''

RENDER3 = r'''
function paintPick(R) {
  const line = document.getElementById('pickline');
  clear(line);
  const parts = document.getElementById('parttbl');
  clear(parts);
  const poolT = document.getElementById('pooltbl');
  clear(poolT);

  if (R.pickError !== null) {
    line.setAttribute('data-pick', 'error');
    line.appendChild(elem('p', { class: 'nonebox',
      text: 'The sequencer threw rather than answering: ' + R.pickError }));
    return;
  }
  if (R.pick === null) {
    /* Sequencer.pick() returns null only when every skill in the hall already
       carries an awarded gate. Nothing here can award one, so this branch is
       not reachable from a replayed record - and it is still handled, by name,
       rather than defaulted into something that looks like an answer. */
    line.setAttribute('data-pick', 'none');
    line.appendChild(elem('p', { class: 'nonebox',
      text: 'The sequencer returned no task. It does that only when every skill in the hall '
        + 'already carries an awarded gate, and nothing on this page can award one.' }));
    return;
  }

  const p = R.pick;
  line.setAttribute('data-pick', 'ok');
  line.setAttribute('data-pick-skill', p.skill);
  line.setAttribute('data-pick-mode', p.mode === undefined ? 'unset' : p.mode);
  line.setAttribute('data-pick-difficulty', n1(p.difficulty));
  line.setAttribute('data-pick-ceiling',
    p.scaffold_ceiling === undefined ? 'unset' : String(p.scaffold_ceiling));
  line.setAttribute('data-pick-scored', String(p.parts !== undefined));
  const nd = R.nodes.find((x) => x.id === p.skill);
  line.appendChild(elem('h3', { text: nd === undefined ? p.skill : nd.strand + ' · ' + nd.tier }));
  line.appendChild(elem('p', { class: 'why', text: p.why }));
  line.appendChild(elem('p', { class: 'muted',
    text: p.skill + ' · mode ' + (p.mode === undefined ? 'unset' : p.mode)
      + ' · difficulty ' + n1(p.difficulty)
      + ' · hints allowed up to rung '
      + (p.scaffold_ceiling === undefined ? 'unset' : p.scaffold_ceiling)
      + (p.poolSize === undefined ? '' : ' · chosen from ' + p.poolSize + ' candidate(s)') }));
  if (p.diagnosis) {
    line.appendChild(elem('p', { class: 'muted', 'data-diagnosis': p.diagnosis.cause,
      text: 'diagnosis: ' + p.diagnosis.cause + ' — ' + p.diagnosis.skill }));
  }

  /* the score, term by term, each one a share of the whole */
  if (p.parts === undefined) {
    parts.appendChild(row([elem('td', { class: 'muted', colspan: '5',
      text: 'This pick did not come from scoring candidates. The ' + p.mode + ' rule took '
        + 'priority over the score, and the sentence above is the rule’s own reason.' })],
      { 'data-parts': 'none' }));
  } else {
    for (const term of Object.keys(WEIGHTS)) {
      const v = p.parts[term];
      const w = WEIGHTS[term];
      parts.appendChild(row([
        td(term, 'k'), td(n3(v), 'num'), td(n2(w), 'num'), td(n3(v * w), 'num'),
        td(pc((v * w) / p.parts.total), 'num')],
        { 'data-part': term, 'data-part-value': n3(v), 'data-part-weight': n2(w),
          'data-part-contribution': n3(v * w) }));
    }
    parts.appendChild(row([td('total', 'k'), td('', 'num'), td('', 'num'),
      td(n3(p.parts.total), 'num'), td('100%', 'num')],
      { 'data-part': 'total', 'data-part-contribution': n3(p.parts.total) }));
  }

  /* what else was on the table */
  const head = row([elem('th', { text: 'candidate' }), elem('th', { text: 'score' }),
    elem('th', { text: 'zpd_fit' }), elem('th', { text: 'review' }),
    elem('th', { text: 'leverage' }), elem('th', { text: 'novelty' })]);
  poolT.appendChild(head);
  for (const c of R.scored) {
    poolT.appendChild(row([
      td(c.id.split('.').slice(1).join(' · '), 'k'), td(n3(c.parts.total), 'num'),
      td(n2(c.parts.zpd_fit), 'num'), td(n2(c.parts.review_urgency), 'num'),
      td(n2(c.parts.graph_leverage), 'num'), td(n2(c.parts.novelty), 'num')],
      { 'data-candidate': c.id, 'data-candidate-total': n3(c.parts.total),
        'data-candidate-picked': String(c.id === p.skill) }));
  }
  const note = document.getElementById('poolnote');
  clear(note);
  note.setAttribute('data-pool-size', String(R.scored.length));
  note.setAttribute('data-pool-from', R.poolFrom);
  note.setAttribute('data-pool-used', String(p.parts !== undefined));
  const shape = R.scored.length
    ? 'Those ' + R.scored.length + ' candidate(s) came from ' + R.poolFrom + '. The working set '
      + 'holds at most ' + POLICY.workingSetMax + ' skills open at once, and no more than '
      + POLICY.maxConsecutiveSameSkill + ' tasks in a row may come from one skill.'
    : 'The sequencer had no candidate pool at all on this profile.';
  note.textContent = p.parts === undefined
    ? shape + ' None of them is the task above: the ' + p.mode + ' rule runs before scoring and '
      + 'took priority over all of them. This is what the sequencer would have scored otherwise.'
    : shape;
}

function paintDial(R) {
  const line = document.getElementById('dialline');
  clear(line);
  const tb = document.getElementById('dialstate');
  clear(tb);
  const last = document.getElementById('diallast');
  clear(last);
  const d = R.dialView;
  if (d === null) {
    line.setAttribute('data-dial', 'none');
    line.appendChild(elem('p', { class: 'nonebox',
      text: 'No task was picked, so there is no difficulty to set.' }));
    return;
  }
  line.setAttribute('data-dial', 'ok');
  line.setAttribute('data-dial-skill', d.skill);
  line.setAttribute('data-dial-state', d.state);
  line.setAttribute('data-dial-setpoint', n1(d.setpoint));
  line.setAttribute('data-dial-served', n1(d.served));
  line.setAttribute('data-dial-psuccess', n3(d.pAtServed));
  line.appendChild(elem('p', { class: 'why',
    text: 'The dial is ' + d.state + ' on this skill. It would serve difficulty '
      + n1(d.setpoint) + ' against your level of ' + n1(d.theta) + ', which on the logistic it '
      + 'uses is a ' + pc(d.pAtSetpoint) + ' chance of getting it unaided. The task above is '
      + 'served at ' + n1(d.served) + ' — ' + pc(d.pAtServed) + '.' }));
  line.appendChild(elem('p', { class: 'muted',
    text: 'The target band is ' + pc(BAND.lo) + '–' + pc(BAND.hi) + '. The dial waits '
      + d.windowNeeds + ' attempts before it moves at all; it has ' + d.windowFilled
      + ' in the current window and has moved ' + d.moves + ' time(s) on this skill in your '
      + 'record.' }));
  const rows = [
    ['your level (θ)', n1(d.theta), 'moved by every attempt, up on a success and down on a miss'],
    ['uncertainty (σ)', n1(d.sigma),
     'shrinks with evidence and re-inflates when you keep surprising the model'],
    ['setpoint', n1(d.setpoint), 'where the dial would place the next task'],
    ['dial state', d.state, 'one of ' + STATES.join(', ')],
    ['window', d.windowFilled + ' of ' + d.windowNeeds, 'attempts until the dial may move again'],
    ['failed windows', String(d.failedWindows),
     'two in a row drops the setpoint to θ ' + DEFAULTS.recoveryDrop + ' and starts again '
     + 'from a worked example'],
    ['pinned', d.pinned === null ? 'no' : n1(d.pinned),
     'an instructor may pin the difficulty; nothing on this page can'],
  ];
  for (const [k, v, why] of rows) {
    tb.appendChild(row([td(k, 'k'), td(v, 'num'), td(why, 'muted')], { 'data-dial-row': k }));
  }
  if (d.last === null) {
    last.setAttribute('data-dial-move', 'none');
    last.textContent = 'The dial has not moved on this skill: it needs ' + d.windowNeeds
      + ' attempts in a window before it will, and your record has ' + d.windowFilled + '.';
  } else {
    last.setAttribute('data-dial-move', d.last.action);
    last.textContent = 'Last move — ' + d.last.action + ': ' + d.last.why
      + ' (success rate over that window ' + pc(d.last.pHat) + ', affect ' + d.last.affect.state
      + ', boredom ' + n2(d.last.affect.boredom) + ', anxiety ' + n2(d.last.affect.anxiety)
      + '; setpoint ' + n1(d.last.before.c) + ' → ' + n1(d.last.after.c) + ').';
  }
}

function paintGates(R) {
  const tb = document.getElementById('gatetbl');
  clear(tb);
  tb.appendChild(row([elem('th', { text: 'skill' }), elem('th', { text: 'attempts' }),
    elem('th', { text: 'gate-qualifying' }), elem('th', { text: 'believed' }),
    elem('th', { text: 'demonstrated' }), elem('th', { text: 'gate' }),
    elem('th', { text: 'why, in gates.mjs’s own words' })]));
  for (const g of R.gates) {
    if (g.attempts === 0 && !g.believed) continue;
    tb.appendChild(row([
      td(g.strand + ' · ' + g.tier, 'k'), td(g.attempts, 'num'), td(g.qualifying, 'num'),
      td(g.believed ? 'yes' : 'no', 'num'), td(g.demonstrated ? 'yes' : 'no', 'num'),
      td(g.pass ? 'PASSED' : 'not passed', 'num'), td(g.why, 'muted')],
      { 'data-gate-skill': g.id, 'data-gate-pass': String(g.pass),
        'data-gate-believed': String(g.believed),
        'data-gate-demonstrated': String(g.demonstrated),
        'data-gate-qualifying': String(g.qualifying),
        'data-gate-attempts': String(g.attempts),
        'data-gate-mastery': n3(g.mastery) }));
  }
  const sum = document.getElementById('gatesum');
  clear(sum);
  const passed = R.gates.filter((g) => g.pass).length;
  const believed = R.gates.filter((g) => g.believed).length;
  const shown = tb.querySelectorAll('[data-gate-skill]').length;
  sum.setAttribute('data-gates-passed', String(passed));
  sum.setAttribute('data-gates-believed', String(believed));
  sum.setAttribute('data-gates-total', String(R.gates.length));
  sum.setAttribute('data-gates-shown', String(shown));
  sum.appendChild(elem('p', { class: 'why',
    text: passed + ' of ' + R.gates.length + ' skill gates in this hall are passed. '
      + believed + ' are believed on the posterior alone, which is not the same thing and never '
      + 'stands in for it. The rows above are the skills your record has touched; the rest of '
      + 'the ladder is untouched and reads the same way.' }));
  sum.appendChild(elem('p', { class: 'muted',
    text: 'Nothing in this record is gate-qualifying, and the column says so with a number. A '
      + 'gate counts only demonstrations whose difficulty was stamped at serve time, and the '
      + 'app that wrote this record never asked the dial for a difficulty, so there is nothing '
      + 'to stamp. That is a gap in the app, not a judgement about you.' }));

  const cert = document.getElementById('certline');
  clear(cert);
  cert.setAttribute('data-certified', String(R.cert));
  cert.setAttribute('data-level-test', 'none');
  cert.setAttribute('data-jobsite-final', 'none');
  cert.appendChild(elem('p', { class: 'why',
    text: 'certified() was called with these gates, with no level test and with no jobsite '
      + 'final, because this bundle holds neither. It answered ' + String(R.cert) + '.' }));
}

function paintHints(R) {
  const line = document.getElementById('hintline');
  clear(line);
  const tb = document.getElementById('hintstate');
  clear(tb);
  const asks = document.getElementById('hintasks');
  clear(asks);
  const h = R.hintView;
  if (h === null) {
    line.setAttribute('data-hint', 'none');
    line.appendChild(elem('p', { class: 'nonebox',
      text: 'No task was picked, so there is no help ladder to set.' }));
    return;
  }
  line.setAttribute('data-hint', 'ok');
  line.setAttribute('data-hint-skill', h.skill);
  line.setAttribute('data-hint-ceiling', String(h.ceiling));
  line.setAttribute('data-hint-from-mastery', String(h.fromMastery));
  line.setAttribute('data-hint-task-ceiling', h.taskCeiling === null ? 'unset' : String(h.taskCeiling));
  line.setAttribute('data-hint-contract', String(h.contract));
  const rung = RUNGS[h.ceiling];
  line.appendChild(elem('p', { class: 'why',
    text: h.ceiling === 0
      ? 'On this task the ladder is closed: no hint is available at all.'
      : 'On this task the ladder reaches rung ' + h.ceiling + ' — ' + rung.name + ', which '
        + rung.does + '. A success there is worth ' + n2(rung.credit) + ' of the mastery credit '
        + 'an unaided one is worth.' }));
  const rows = [
    ['mastery on this skill', n3(h.mastery), 'the posterior the fading rule reads'],
    ['ceiling from mastery', String(h.fromMastery),
     'the fading rule: the better you know it, the shorter the ladder gets'],
    ['ceiling from the task', h.taskCeiling === null ? 'unset' : String(h.taskCeiling),
     'a mode bound: a verification run is hint-free because it is proof, not practice'],
    ['ceiling served', String(h.ceiling), 'the tighter of the two, always'],
    ['your hint dependence', pc(h.dependence),
     'measured over the last ' + HINT_POLICY.fadeWindow + ' attempts here; '
     + h.windowFilled + ' recorded so far'],
    ['fading contract', h.contract ? h.contract + ' task(s) left' : 'none open',
     'opened at a sustained dependence above ' + HINT_POLICY.fadeThreshold
     + '; ' + h.contractsOpened + ' opened in this record'],
  ];
  for (const [k, v, why] of rows) {
    tb.appendChild(row([td(k, 'k'), td(v, 'num'), td(why, 'muted')], { 'data-hint-row': k }));
  }
  for (const [what, r] of [['asked with no pause', h.noDwell],
                           ['asked after the pause it requires', h.withDwell]]) {
    asks.appendChild(row([
      td(what, 'k'), td('rung ' + r.asked, 'num'),
      td(r.refused ? 'refused: ' + r.refused : 'rung ' + r.granted, 'num'),
      td(r.why, 'muted')],
      { 'data-ask': what, 'data-ask-granted': String(r.granted),
        'data-ask-refused': r.refused === null ? 'none' : r.refused }));
  }
}

/* ------------------------------------------------------------------ the boot */
function renderAll(slug) {
  const rec = readRecord();
  paintRecord(rec);
  const seen = hallsInRecord(rec);
  paintEmpty(rec, seen, slug);
  const box = document.getElementById('profilebox');
  box.setAttribute('data-hall', slug === null ? 'none' : slug);
  if (slug === null) {
    box.setAttribute('data-profile', 'unpicked');
    box.setAttribute('data-shown', 'false');
    return;
  }
  box.setAttribute('data-shown', 'true');
  const R = replay(slug, rec);
  box.setAttribute('data-profile', R.history.length ? 'record' : 'empty');
  box.setAttribute('data-attempts', String(R.history.length));
  paintReplay(R);
  paintLadder(R);
  paintPick(R);
  paintDial(R);
  paintGates(R);
  paintHints(R);
  window.__tcProgress = () => ({
    hall: R.slug, attempts: R.history.length,
    pick: R.pick, gatesPassed: R.gates.filter((g) => g.pass).length,
    qualifying: R.history.filter((x) => x.gate_qualifying === true).length,
    certified: R.cert,
  });
}

/* The picker. There is no default hall: a page that opens on halls[0] because
   nothing said otherwise is reporting a choice it made as a choice the reader
   made. When the record names halls, the one with the most runs is offered and
   the note says why it was offered; otherwise nothing is selected. */
const sel = document.getElementById('hallpick');
sel.appendChild(elem('option', { value: '', text: '— choose a hall —' }));
for (const h of D.halls) sel.appendChild(elem('option', { value: h.slug, text: h.name }));

const boot = readRecord();
const bootSeen = hallsInRecord(boot);
const fromUrl = new URLSearchParams(location.search).get('hall');
let start = null, why = '';
if (fromUrl !== null && HALLS.has(fromUrl)) { start = fromUrl; why = 'from the link you followed'; }
else if (fromUrl !== null) { why = 'the link named a hall that is in no hall record: ' + fromUrl; }
else if (bootSeen.size) {
  start = [...bootSeen.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0][0];
  why = 'this device has more runs recorded in this hall than in any other';
}
sel.value = start === null ? '' : start;
const note = document.getElementById('picknote');
note.setAttribute('data-picked-because', start === null ? 'nothing' : why);
note.textContent = start === null
  ? (why || 'No hall is selected, and none will be chosen for you.')
  : 'Showing ' + start + ' — ' + why + '.';
sel.addEventListener('change', (e) => {
  const v = e.target.value;
  renderAll(v === '' ? null : v);
  const n = document.getElementById('picknote');
  n.setAttribute('data-picked-because', v === '' ? 'nothing' : 'you chose it');
  n.textContent = v === '' ? 'No hall is selected, and none will be chosen for you.'
    : 'Showing ' + v + ' — you chose it.';
  history.replaceState(null, '', v === '' ? location.pathname : location.pathname + '?hall=' + v);
});
renderAll(start);
'''

SCRIPT = CONTROL_BUNDLE + '\n\n/* ---- web/build_progress.py: the page ---- */\n' + RENDER + RENDER2 + RENDER3

# ------------------------------------------------------------------------ page
TITLE = PRODUCT.split('(')[0].strip()
page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' stroke='%23E8A33D' stroke-width='2.6' stroke-linejoin='round'/%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E">
<title>{E(TITLE)} — learner progression</title>
<style>
:root{{
  --plate:#12181B; --panel:#182023; --sunk:#0C1113; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --mark-ink:#12181B; --steel:#41C4D4;
  --good:#5CB584; --crit:#E07C68; --warn:#E8A33D;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--plate);color:var(--ink);
  font:14px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;padding:0 18px}}
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
table{{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--rule);
  border-radius:8px;overflow:hidden;margin:8px 0}}
td,th{{border-top:1px solid var(--rule);padding:8px 10px;vertical-align:top;font-size:13.5px;
  text-align:start}}
th{{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;
  letter-spacing:.05em}}
tr:first-child td,tr:first-child th{{border-top:0}}
td.k{{color:var(--ink);font-weight:600;white-space:nowrap}}
td.num{{font:13px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--steel);
  white-space:nowrap}}
td.muted{{color:var(--muted)}}
.tscroll{{overflow-x:auto}}
@media (max-width:640px){{td.k,td.num{{white-space:normal}}}}
code{{font:13px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted)}}
pre{{background:var(--sunk);border:1px solid var(--rule);border-radius:6px;padding:10px 12px;
  overflow-x:auto;font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--ink)}}
.chip{{display:inline-block;border-radius:4px;padding:1px 7px;font-size:12px;
  border:1px solid var(--rule);background:var(--sunk);color:var(--muted);margin:0 6px 4px 0}}
.prov{{display:inline-block;border-radius:4px;padding:1px 7px;font-size:11px;
  border:1px solid var(--rule);margin:0 6px 4px 0;background:var(--sunk);color:var(--muted);
  letter-spacing:.03em}}
.why{{color:var(--ink);font-size:14px}}
.muted{{color:var(--muted);font-size:13px}}
.card{{background:var(--panel);border:1px solid var(--rule);border-radius:10px;
  padding:14px 16px;margin:12px 0}}
.nonebox{{background:var(--sunk);border:1px solid var(--crit);border-radius:8px;
  padding:12px 14px;color:var(--ink)}}
.toolbar{{position:sticky;top:0;background:var(--plate);padding:10px 0;z-index:2;
  border-bottom:1px solid var(--rule);display:flex;gap:10px;flex-wrap:wrap;align-items:center}}
.toolbar select{{background:var(--sunk);border:1px solid var(--rule);color:var(--ink);
  border-radius:6px;padding:8px 12px;font:inherit;flex:1 1 280px}}
.toolbar label{{color:var(--muted);font-size:13px}}
#picknote{{color:var(--warn);font-size:13px;flex:1 1 100%}}
#emptynote{{background:var(--sunk);border:1px solid var(--warn);border-radius:8px;
  padding:12px 14px;margin:12px 0}}
.gridwrap{{overflow-x:auto;background:var(--panel);border:1px solid var(--rule);
  border-radius:8px;padding:8px}}
svg#ladder{{display:block;max-width:100%;height:auto}}
svg .colhead{{fill:var(--mark);font:600 12px system-ui,sans-serif;
  text-transform:uppercase;letter-spacing:.08em}}
svg .cell rect{{fill:var(--sunk);stroke:var(--rule);stroke-width:1}}
svg .cell.ready rect{{stroke:var(--steel)}}
svg .cell.touched rect{{fill:#141d20;stroke:var(--good);stroke-width:1.6}}
svg .cell.picked rect{{stroke:var(--mark);stroke-width:2.6}}
svg .cell .cname{{fill:var(--ink);font:600 12.5px system-ui,sans-serif}}
svg .cell .cmark{{fill:var(--muted);font:11px ui-monospace,Menlo,monospace}}
svg .cell .cgate{{fill:var(--muted);font:10.5px ui-monospace,Menlo,monospace}}
svg .cell.touched .cmark{{fill:var(--good)}}
svg .cell.locked .cmark{{fill:#5d6c70}}
svg .edge{{fill:none;stroke:var(--rule);stroke-width:1.4}}
svg .edge.requires{{stroke:var(--steel)}}
svg .edge.supports{{stroke:var(--mark);stroke-dasharray:5 4}}
svg .edge.interferes{{stroke:var(--crit);stroke-dasharray:2 4}}
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
  <h1>{E(TITLE)} — <span class="x">learner progression</span></h1>
  <p>{E(PRODUCT)} · pack {E(PACK_VERSION)} · built {E(BUILT)} · the control plane in
     <code>control/</code>, run in this page over the record this browser already keeps</p>
</header>

<section class="lead" id="limits">
  <h2>What this page is, and what it is not</h2>
  <p class="why">{E(F(N_CONTROL_LINES))} lines of tested adaptive-learning control plane sit in
     <code>control/</code>. The 3D environment a learner actually plays names them
     {E(F(N_APP_HITS))} times: it hands out a deterministic rubric score and nothing sequences
     what comes next, nothing sets the difficulty, no gate opens or stays shut and no help fades.
     This page runs that machinery — the real classes, carried in verbatim — over whatever
     <code>{E(TRAINING_KEY)}</code> holds on this device, so you can see what it would do.
     <b>It changes nothing and it certifies nobody.</b></p>
  <ul>{LIMITS}</ul>
  <p class="muted">{E(NO_LLM_RULE)}</p>
</section>

<section class="figs">{FIGS}</section>

<section>
  <h2>Where your record comes from</h2>
  <p class="why">Two records, both written by the app, both in this browser and nowhere else.
     This page reads them; it never writes them.</p>
  <div class="tscroll"><table><tbody id="recstate"></tbody></table></div>
  <div class="figs" id="recfigs"></div>
  <p class="muted" id="idline"></p>
  <p class="muted">A pass under <code>{E(PROGRESS_KEY)}</code> names a seat and no hall, and
     {E(F(MULTI_HALL_SIMS))} of the {E(F(N_SIMS))} seats stand in more than one hall — one of them
     in {E(F(MAX_SIM_HALLS))}. Attributing such a pass to the hall you are looking at would be
     this page deciding which hall you were standing in. So it is counted above and fed to
     nothing. <code>{E(TRAINING_KEY)}</code> records the hall on every episode, and that is the
     only record below.</p>
</section>

<div class="toolbar">
  <label for="hallpick">hall</label>
  <select id="hallpick" aria-label="choose a union hall"></select>
  <a href="trade_craft_ladder.html">see the whole ladder and its seats</a>
  <span id="picknote"></span>
</div>

<div id="emptynote"></div>

<div id="profilebox">

<section>
  <h2>What the replay fed the modules, and what it dropped</h2>
  <p class="why">{E(VERIFY_RULE)}</p>
  <div class="tscroll"><table><tbody id="replaytbl"></tbody></table></div>
  <div id="replaynote"></div>
  <p class="muted">One reconstruction, named rather than buried: the episode record stores no
     serve difficulty — <code>{E(TRAINING_PATH)}</code> gives a sim episode the fields
     {E(', '.join(SIM_FIELDS))}, and none of them is one — so the replay serves each recorded
     outcome at the difficulty the dial would have chosen at that point, stepping the dial forward
     as it goes. The record carries no hint rung either, so every attempt is replayed unaided, at
     rung 0.</p>
</section>

<section>
  <h2>Where am I?</h2>
  <p class="why">Your hall's ladder, drawn from <code>{E(SKILLS_PATH)}</code> and read by the real
     <code>SkillGraph</code>: {E(F(N_CELLS_PER_HALL))} cells, {E(F(N_STRANDS))} strands across
     {E(F(N_TIERS))} tiers, every cell but the {E(F(N_ROOTS_PER_HALL))} root naming exactly one
     prerequisite — so a hall's ladder is a tree and readiness is a fact about it, not an
     opinion.</p>
  <p class="legend">
    <span><i class="req"></i>requires — the hard prerequisite</span>
    <span><i class="sup"></i>supports — soft transfer</span>
    <span><i class="int"></i>interferes — a confusable pair</span>
  </p>
  <div class="gridwrap"><svg id="ladder" role="img"
    aria-label="this hall's skills by strand and tier, with your position on each"></svg></div>
  <div class="figs" id="laddersum"></div>
  <p class="muted">A cell counts as <i>touched</i> when the graph moved it at all &mdash; the cells
     you attempted, plus their neighbours one hop away that propagated credit reached.
     {E(GRAPH_RULE)}</p>
</section>

<section>
  <h2>What should I do next, and why?</h2>
  <p class="why">{E(SEQ_DEFENDS_RULE)}</p>
  <div class="card" id="pickline"></div>
  <p class="why">Its score, term by term. The five weights are the sequencer's own published
     numbers and they sum to one, so the last column is each term's share of this pick:</p>
  <div class="tscroll"><table><tbody id="parttbl"></tbody></table></div>
  <div class="tscroll"><table><tbody id="pooltbl"></tbody></table></div>
  <p class="muted" id="poolnote"></p>
  <p class="why">What each term means, from <code>{E(SEQUENCER_PATH)}</code>:</p>
  <div class="tscroll"><table><tbody>
    <tr><th>term</th><th>weight</th><th>what it measures</th></tr>
    {WEIGHT_ROWS}
  </tbody></table></div>
</section>

<section>
  <h2>How hard will it be?</h2>
  <div class="card" id="dialline"></div>
  <div class="tscroll"><table><tbody id="dialstate"></tbody></table></div>
  <p class="muted" id="diallast"></p>
  <p class="why">What moves it, from <code>{E(DIAL_PATH)}</code>:</p>
  <div class="tscroll"><table><tbody>
    <tr><th>constant</th><th>value</th><th>what it decides</th></tr>
    {DIAL_ROWS}
  </tbody></table></div>
  <p class="muted">{E(DIAL_CLAMP_RULE)}</p>
</section>

<section>
  <h2>What am I allowed to claim?</h2>
  <p class="why">{E(GATES_RULE)}</p>
  <div class="tscroll"><table><tbody id="gatetbl"></tbody></table></div>
  <div id="gatesum"></div>
  <p class="muted">{E(GATE_QUALIFY_RULE)}</p>
  <p class="why">{E(CERTIFIED_DOC)} <code>{E(GATES_PATH)}</code> writes it as:</p>
  <pre data-quote="certified" data-source="{E(GATES_PATH)}">{E(CERTIFIED_EXPR)}</pre>
  <div class="card" id="certline"></div>
  <p class="why">{E(JOBSITE_DOC)} That third component is not a number this bundle can produce:
     the oral check is a person from the hall asking you to explain the why, and scoring it.
     Nothing in this bundle, on this page or in the 3D environment, is that person.</p>
  <pre data-quote="jobsite-final" data-source="{E(GATES_PATH)}">{E(JOBSITE_EXPR)}</pre>
  <p class="why">The constants those three tiers run on:</p>
  <div class="tscroll"><table><tbody>
    <tr><th>constant</th><th>value</th><th>what it decides</th></tr>
    {GATE_ROWS}
  </tbody></table></div>
</section>

<section>
  <h2>What help do I get?</h2>
  <p class="why">{E(FADE_RULE)}</p>
  <div class="card" id="hintline"></div>
  <div class="tscroll"><table><tbody id="hintstate"></tbody></table></div>
  <p class="why">And what the engine answers if you ask for a hint right now — twice, because the
     first answer is the one most systems hide:</p>
  <div class="tscroll"><table><tbody id="hintasks"></tbody></table></div>
  <p class="why">The ladder itself, from <code>{E(HINTS_PATH)}</code>. `credit` is the mastery
     evidence a success at that rung is worth, and it is the same schedule the dial uses to
     discount its success rate — one table, so a hint cannot be cheap in one subsystem and
     expensive in another:</p>
  <div class="tscroll"><table><tbody>
    <tr><th>rung</th><th>name</th><th>credit</th><th>what it does</th></tr>
    {RUNG_ROWS}
  </tbody></table></div>
  <div class="tscroll"><table><tbody>
    <tr><th>constant</th><th>value</th><th>what it decides</th></tr>
    {HINT_ROWS}
  </tbody></table></div>
</section>

</div>

<section>
  <h2>Which control plane this is</h2>
  <p class="why">Not a description of it and not a second implementation of it: the modules below
     are read by <code>web/build_progress.py</code> and carried into this page verbatim, with the
     <code>import</code> lines dropped ({E(F(CONTROL_DROPPED))} of them, because the modules are
     concatenated in dependency order) and a leading <code>export</code> stripped. Every other
     byte — the arithmetic, the comments that say why each number is what it is, the sentences you
     read above — is the module's.</p>
  <div class="tscroll"><table><tbody>
    <tr><th>module</th><th>lines</th><th>what it owns</th></tr>
    {CONTROL_ROWS}
  </tbody></table></div>
  <p class="why">Those modules pass {E(F(N_CONTROL_CHECKS))} checks in this repository, counted by
     running them:</p>
  <div class="tscroll"><table><tbody>
    <tr><th>suite</th><th>checks</th></tr>
    {TEST_ROWS}
  </tbody></table></div>
  <p>{PROV_CHIPS}</p>
</section>

<section>
  <h2>What this page read</h2>
  <ul class="muted">{READS}</ul>
  <p class="muted">Every number on this page is read from those files at build time, or computed
     in this page by those modules from your own record. None is typed.</p>
</section>

<footer class="page">
  <a href="trade_craft_ladder.html">training ladder</a>
  <a href="trade_craft_3d.html">3D environment</a>
  <a href="trade_craft_signin.html">who this device says you are</a>
  <a href="trade_craft_landing.html">landing</a>
</footer>
</div>
<script type="application/json" id="tcdata">{PAYLOAD}</script>
<script type="module">
{SCRIPT}</script>
</body>
</html>
'''

out = HERE / 'trade_craft_progress.html'
emit(out, page,
     f'{F(N_CONTROL_LINES)} lines of control plane over {F(N_CELLS_PER_HALL)} cells, '
     f'{F(N_CONTROL_CHECKS)} control checks, certifies nobody')
