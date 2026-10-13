#!/usr/bin/env python3
"""evals/ - what control/sim_curriculum.mjs actually produces when it is run,
published together with the limit on what it can mean.

WHY THIS PACK EXISTS

`control/sim_curriculum.mjs` compares three ways of choosing the next skill -
the ACP-05 sequencer (`graph`), the traditional one-skill-to-mastery
curriculum (`blocked`), and random unmastered choice with prerequisites
ignored (`flat`) - over the same ZPD dial, so the only thing that differs is
the choice of SKILL. That is a real measurement and it is worth publishing.

It is also the single most dangerous number in this bundle, because the
shape of the sentence it invites - "our sequencer beats blocked practice by
X%" - reads as a finding about learners, and it is not one. The simulation
runs a learner model this project WROTE. Its header says so in its own
words, and this pack quotes that sentence rather than paraphrasing it,
records it in one named field, and ships a check that fails if it is ever
softened or drifts away from what the source says.

WHAT IS MEASURED AND WHAT IS NOT

MEASURED: whether the sequencer converts three stated beliefs into outcomes
inside a simulation that assumes them. That is a question about code, and
the answer here is the code's.

NOT MEASURED: whether the three beliefs hold for a person. Nothing was
observed of any learner. No hall, no cohort, no apprentice, no classroom.
A reader who takes any number in this registry as a fact about real
learning has been misled, and this pack's job is to make that reading
impossible to reach by accident.

THE TIER, AND WHY IT IS NOT DERIVED

This bundle's closed tier set is read from auth/registry/auth.json. Two of
them could plausibly be argued for here:

  SCRIPTED - a hand-written deterministic policy, with no model behind it.
  DERIVED  - computed from something RECORDED, by a rule you can read.

Every per-run outcome is SCRIPTED: three hand-written selection policies
driven by a seeded mulberry32 PRNG over an authored skill ladder and an
authored learner model. The summary statistics this pack computes on top -
min, max, median, mean, the spread across seeds - are computed by a rule
you can read, but their INPUT is scripted output, not a recording. DERIVED
in this bundle means computed from something recorded; a statistic cannot
be more than the thing it summarises, so the summaries stay SCRIPTED too
and say here why they were not promoted. Nothing in this pack is RECORDED
and nothing is AI-SYNTHESIZED - that word belongs to orbis/.

THE SPREAD IS THE RESULT, NOT THE MEAN

One seed is an anecdote. Every metric here is published as its per-seed
values with min, max, median and range beside the mean, and every pair of
strategies is tested for whether its intervals across seeds actually
separate. Where they overlap this pack says overlap, in the same field a
reader looking for a headline would read. An overlap is a finding.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'evals.json'
SUBJECT = ROOT / 'control' / 'sim_curriculum.mjs'


def need(obj, key, where):
    """Fail CLOSED, naming the path. No bare defaults anywhere in this pack."""
    if not isinstance(obj, dict) or key not in obj:
        raise KeyError('evals: %s is missing %r' % (where, key))
    return obj[key]


MANIFEST = json.loads((ROOT / 'pack' / 'manifest.json').read_text())
PACK_VERSION = need(MANIFEST, 'pack_version', 'pack/manifest.json')

AUTH = json.loads((ROOT / 'auth' / 'registry' / 'auth.json').read_text())
TIERS = tuple(need(AUTH, 'provenance_tiers', 'auth/registry/auth.json'))
for _t in ('SCRIPTED', 'DERIVED', 'RECORDED'):
    if _t not in TIERS:
        raise ValueError('evals: the bundle tier set no longer contains %r; '
                         'this pack reasons about it by name '
                         '(auth/registry/auth.json provenance_tiers)' % _t)

# ---------------------------------------------------------------------------
# The subject, read rather than retyped.

SRC = SUBJECT.read_text()
SRC_SHA = hashlib.sha256(SUBJECT.read_bytes()).hexdigest()

_head = re.match(r'/\*\*(.*?)\*/', SRC, re.S)
if not _head:
    raise ValueError('evals: %s no longer opens with a /** */ header comment; '
                     'the assumptions and the limit are quoted out of it'
                     % SUBJECT.relative_to(ROOT))
HEADER_LINES = [re.sub(r'^\s*\*\s?', '', ln) for ln in _head.group(1).split('\n')]


def extract_assumptions(lines):
    """A1/A2/A3 exactly as the source states them, continuations joined."""
    found, cur = {}, None
    for ln in lines:
        m = re.match(r'^\s{2,}A(\d)\s+(.*\S)\s*$', ln)
        if m:
            cur = 'A' + m.group(1)
            found[cur] = m.group(2)
            continue
        if cur and re.match(r'^\s{5,}\S', ln):
            found[cur] = found[cur] + ' ' + ln.strip()
            continue
        if cur and not ln.strip():
            cur = None
    return found


def extract_limit(lines):
    """The sentence in which the source states what it does NOT show.

    Taken structurally: the header text that runs from the assumptions
    heading up to the colon that introduces A1. Deliberately NOT matched on
    the words it is supposed to contain - a matcher that required the strong
    wording would refuse to extract a softened one, and the softened one is
    exactly what the check downstream has to be able to see and fail on.
    """
    flat = re.sub(r'\s+', ' ', ' '.join(ln.strip() for ln in lines)).strip()
    m = re.search(r'(LEARNER MODEL ASSUMPTIONS.*?):\s*A1\b', flat)
    if not m:
        raise ValueError(
            'evals: could not find the assumptions heading and its A1 list in '
            'the header of %s; this pack quotes that passage verbatim and '
            'will not guess at it' % SUBJECT.relative_to(ROOT))
    return m.group(1) + ':'


ASSUMPTIONS = extract_assumptions(HEADER_LINES)
if sorted(ASSUMPTIONS) != ['A1', 'A2', 'A3']:
    raise ValueError('evals: expected A1, A2 and A3 in the header of %s, '
                     'found %r' % (SUBJECT.relative_to(ROOT),
                                   sorted(ASSUMPTIONS)))
LIMIT_SENTENCE = extract_limit(HEADER_LINES)

# Runtime constants, read out of the subject rather than typed here.
_cf = re.search(r'const ATTEMPTS = (\d+), PER_DAY = (\d+), SESSION_LEN = (\d+);', SRC)
_cl = re.search(r'const LEARNED = (\d+);', SRC)
_cr = re.search(r'const RETENTION_PROBE_DAYS = (\d+);', SRC)
if not (_cf and _cl and _cr):
    raise ValueError('evals: the ATTEMPTS / LEARNED / RETENTION_PROBE_DAYS '
                     'constants could not be read out of %s; this pack '
                     'reports the parameters a run was made under and will '
                     'not type them' % SUBJECT.relative_to(ROOT))
PARAMS = {
    'attempts': int(_cf.group(1)),
    'per_day': int(_cf.group(2)),
    'session_len': int(_cf.group(3)),
    'learned_threshold_points_above_baseline': int(_cl.group(1)),
    'retention_probe_days': int(_cr.group(1)),
}
if 'mulberry32' not in SRC:
    raise ValueError('evals: %s no longer names mulberry32; the reproduction '
                     'check in this pack rests on its seeded PRNG'
                     % SUBJECT.relative_to(ROOT))

UNION = 'welders'          # the subject's own default union
ALL_SKILLS = json.loads((ROOT / 'pack' / 'registry' / 'skills.json').read_text())
UNION_SKILLS = [s for s in need(ALL_SKILLS, 'skills', 'pack/registry/skills.json')
                if need(s, 'union', 'pack/registry/skills.json#skills[]') == UNION]
if not UNION_SKILLS:
    raise ValueError('evals: no skills for union %r in '
                     'pack/registry/skills.json' % UNION)

# The seeds. Recorded so the run can be reproduced exactly; the subject's own
# three defaults are included so this pack covers what its CLI prints.
SEEDS = [3, 11, 29, 47, 101, 233, 404, 777, 1009, 2027, 4242, 8191]
STRATEGIES = ['graph', 'blocked', 'flat']
METRICS = ['skillsGated', 'skillsLearned', 'totalAbilityGained',
           'retentionAt30d', 'prereqViolationPct', 'remediations', 'reviews',
           'verifies', 'distinctSkillsTouched']

# ---------------------------------------------------------------------------
# Run the real thing. Nothing below is typed; it is what came back.

DRIVER = '''
import { run, runAll } from %s;
const seeds = %s, strategies = %s;
const t0 = Date.now();
const runs = [];
for (const k of strategies) for (const s of seeds) runs.push({ seed: s, ...run(k, s) });
const runall = runAll(seeds);
// the same call twice, to show the seeded PRNG is the only source of variation
const twice = JSON.stringify(strategies.map((k) => run(k, seeds[0])));
const once = JSON.stringify(runs.filter((r) => r.seed === seeds[0])
  .map(({ seed, ...rest }) => rest));
process.stdout.write(JSON.stringify({
  elapsed_ms: Date.now() - t0, node: process.version,
  runs, runall, repeat_identical: twice === once,
}));
''' % (json.dumps(SUBJECT.as_uri()), json.dumps(SEEDS), json.dumps(STRATEGIES))

_t0 = time.time()
proc = subprocess.run(['node', '--input-type=module', '-e', DRIVER],
                      capture_output=True, text=True, cwd=str(ROOT))
WALL_MS = int((time.time() - _t0) * 1000)
if proc.returncode != 0:
    raise RuntimeError('evals: running control/sim_curriculum.mjs failed '
                       '(exit %d)\n%s' % (proc.returncode, proc.stderr.strip()))
SIM = json.loads(proc.stdout)
RUNS = need(SIM, 'runs', 'the simulation driver output')
RUNALL = need(SIM, 'runall', 'the simulation driver output')
if not need(SIM, 'repeat_identical', 'the simulation driver output'):
    raise RuntimeError('evals: the simulation did not return the same result '
                       'for the same seed twice in one process; it is not '
                       'the reproducible subject this pack claims it is')
if len(RUNS) != len(SEEDS) * len(STRATEGIES):
    raise ValueError('evals: expected %d runs, got %d'
                     % (len(SEEDS) * len(STRATEGIES), len(RUNS)))

# ---------------------------------------------------------------------------
# DOES THE SIMULATION KNOW WHICH HALL IT IS IN?
#
# Everything above compares three strategies inside ONE union - the subject's
# own default, welders. That is the question the subject was written to ask.
# It is not the question a buyer asks. A buyer asks what their crew, in their
# trade, would get, and the answer this pack has been publishing invites them
# to read a welders number as a crane-ops number.
#
# So this asks the prior question outright: run the SAME strategy and the SAME
# seed in every one of the 111 halls and count how many distinct outcomes come
# back. If the simulation modelled a hall at all - its seats, its equipment,
# the evidence available in it - the count would be larger than one.
#
# It is one. Every hall, every seed, one outcome. The reason is structural and
# is visible in `loadUnionGraph`: every union carries the same 11 strands by 3
# tiers, wired by the same `requires` edges, so the graph handed to the
# sequencer is isomorphic in all 111 halls and the seeded PRNG is the only
# thing that varies. Nothing in control/ reads sims/registry/sims.json. The
# simulation does not know that crane-ops has four simulator seats and that
# painters has none, and it returns the same ability, the same retention and
# the same gate count for both.
#
# That is worth publishing rather than hiding, because of what it does NOT
# mean. It does not mean the halls are interchangeable in real life. It means
# this simulation is a study of a CURRICULUM SHAPE, not of a trade, and any
# number it produces describes the shape. Read as a per-trade training
# outcome - which is exactly how a package sold to an employer would invite
# it to be read - it would be a claim the simulation never made.
HALL_SEEDS = [SEEDS[0], SEEDS[4], SEEDS[10]]
HALL_STRATEGY = 'graph'
ALL_HALLS = sorted({need(s2, 'union', 'pack/registry/skills.json#skills')
                    for s2 in need(ALL_SKILLS, 'skills',
                                   'pack/registry/skills.json')})

HALL_DRIVER = '''
import { run } from %s;
const halls = %s, seeds = %s, kind = %s;
const out = {};
for (const s of seeds) {
  const seen = {};
  for (const h of halls) {
    const j = JSON.stringify(run(kind, s, { union: h }));
    (seen[j] = seen[j] || []).push(h);
  }
  out[s] = Object.entries(seen).map(([j, hs]) => ({ outcome: JSON.parse(j), halls: hs }));
}
process.stdout.write(JSON.stringify(out));
''' % (json.dumps(SUBJECT.as_uri()), json.dumps(ALL_HALLS),
        json.dumps(HALL_SEEDS), json.dumps(HALL_STRATEGY))

_h0 = time.time()
_hp = subprocess.run(['node', '--input-type=module', '-e', HALL_DRIVER],
                     capture_output=True, text=True, cwd=str(ROOT))
HALL_MS = int((time.time() - _h0) * 1000)
if _hp.returncode != 0:
    raise RuntimeError('evals: the per-hall sweep failed (exit %d)\n%s'
                       % (_hp.returncode, _hp.stderr.strip()))
HALL_SWEEP = json.loads(_hp.stdout)

_groups = {str(s): len(HALL_SWEEP[str(s)]) for s in HALL_SEEDS}
for _s, _n in _groups.items():
    if _n < 1:
        raise ValueError('evals: seed %s produced no outcome at all' % _s)

# The contrast, named rather than left as a statistic. The richest hall by
# seat count against a hall with no seat at all, read from the sims registry
# so this cannot drift from the bindings it describes.
SIMS_REG = json.loads((ROOT / 'sims' / 'registry' / 'sims.json').read_text())
_bind = need(SIMS_REG, 'hall_bindings', 'sims/registry/sims.json')
RICHEST = max(sorted(_bind), key=lambda h: len(_bind[h]))
_unbound = [h for h in ALL_HALLS if h not in _bind]
if not _unbound:
    raise ValueError('evals: every hall now carries a seat, so the contrast '
                     'this block is built on no longer exists and the text '
                     'must be rewritten rather than quietly kept')
POOREST = _unbound[0]


def _outcome_of(seed, hall):
    for g in HALL_SWEEP[str(seed)]:
        if hall in g['halls']:
            return g['outcome']
    raise ValueError('evals: %s is missing from the seed %s sweep' % (hall, seed))


_s0 = HALL_SEEDS[0]
CONTRAST = {
    'seed': _s0,
    'richest': {'hall': RICHEST, 'seats': len(_bind[RICHEST]),
                'outcome': _outcome_of(_s0, RICHEST)},
    'poorest': {'hall': POOREST, 'seats': 0,
                'outcome': _outcome_of(_s0, POOREST)},
}
CONTRAST['identical'] = CONTRAST['richest']['outcome'] == CONTRAST['poorest']['outcome']

HALL_INDEPENDENCE = {
    'halls_swept': len(ALL_HALLS),
    'seeds': HALL_SEEDS,
    'strategy': HALL_STRATEGY,
    'distinct_outcomes_per_seed': _groups,
    'contrast': CONTRAST,
    'sweep_ms': HALL_MS,
    'means': 'the same strategy and seed were run in every hall the skills '
             'registry declares, and the distinct outcomes counted. One '
             'distinct outcome for a seed means the simulation returned the '
             'same result in all of them.',
    'why': 'every union carries the same eleven strands by three tiers wired '
           'by the same requires edges, so the graph handed to the sequencer '
           'is isomorphic across halls and the seeded generator is the only '
           'source of variation. Nothing in control/ reads the simulator '
           'registry, so no seat, no piece of equipment and no difference in '
           'available evidence reaches this simulation.',
    'honest': 'this is a study of a curriculum SHAPE, not of a trade. A '
              'number here describes the shape every hall shares. It is not '
              'a per-trade training outcome and must not be sold as one: the '
              'hall with the most simulator seats and a hall with none return '
              'the same ability, the same retention and the same gate count.',
}

# ---------------------------------------------------------------------------
# The spread. One seed is an anecdote; no mean is published without it.


def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def rnd(x):
    return round(float(x) + 0.0, 4)


by_strategy = {}
for k in STRATEGIES:
    rows = [r for r in RUNS if need(r, 'strategy', 'a simulation run') == k]
    if len(rows) != len(SEEDS):
        raise ValueError('evals: %r produced %d runs for %d seeds'
                         % (k, len(rows), len(SEEDS)))
    by_strategy[k] = rows

SPREAD = {}
for k in STRATEGIES:
    SPREAD[k] = {}
    for m in METRICS:
        vals = [need(r, m, 'a %s run' % k) for r in by_strategy[k]]
        SPREAD[k][m] = {
            'per_seed': {str(need(r, 'seed', 'a %s run' % k)): need(r, m, 'a run')
                         for r in by_strategy[k]},
            'min': rnd(min(vals)),
            'max': rnd(max(vals)),
            'median': rnd(median(vals)),
            'mean': rnd(round(sum(vals) / len(vals), 2)),
            'range': rnd(round(max(vals) - min(vals), 4)),
            'identical_across_every_seed': min(vals) == max(vals),
        }

# runAll() is the subject's own summary entry point. Published, and checked
# against the means recomputed from the per-seed rows: if the two ever
# disagree, one of them is lying about the same runs.
RUNALL_ROWS = {}
for row in RUNALL:
    k = need(row, 'strategy', 'a runAll row')
    RUNALL_ROWS[k] = {m: need(row, m, 'the runAll row for %r' % k) for m in METRICS}
    for m in METRICS:
        if RUNALL_ROWS[k][m] != SPREAD[k][m]['mean']:
            raise ValueError(
                'evals: runAll() reports %s=%r for %r while the mean of its '
                'own per-seed runs is %r' % (m, RUNALL_ROWS[k][m], k,
                                             SPREAD[k][m]['mean']))

# ---------------------------------------------------------------------------
# Do the strategies separate? Computed per metric per pair, never asserted.

PAIRS = [('graph', 'blocked'), ('graph', 'flat'), ('blocked', 'flat')]
SEPARATION = {}
for m in METRICS:
    SEPARATION[m] = {}
    for a, b in PAIRS:
        A, B = SPREAD[a][m], SPREAD[b][m]
        disjoint = A['min'] > B['max'] or B['min'] > A['max']
        if disjoint:
            higher = a if A['min'] > B['max'] else b
            gap = rnd(round(max(A['min'] - B['max'], B['min'] - A['max']), 4))
        else:
            higher = None
            gap = 0.0
        SEPARATION[m]['%s_vs_%s' % (a, b)] = {
            'intervals': {a: [A['min'], A['max']], b: [B['min'], B['max']]},
            'overlap': not disjoint,
            'separates_across_every_seed': disjoint,
            'higher': higher,
            'gap_between_intervals': gap,
        }

_disjoint = sum(1 for m in METRICS for p in SEPARATION[m]
                if SEPARATION[m][p]['separates_across_every_seed'])
_overlap = sum(1 for m in METRICS for p in SEPARATION[m]
               if SEPARATION[m][p]['overlap'])

# The retention metric's denominator, stated because it changes the reading.
# The subject reports retentionAt30d as 0 when NOTHING was learned - that is
# "there was nothing left to retain", not "everything decayed". Counted per
# strategy so a reader can see which intervals rest on an empty set.
EMPTY_DENOM = {k: sum(1 for r in by_strategy[k]
                      if need(r, 'skillsLearned', 'a run') == 0)
               for k in STRATEGIES}

# ---------------------------------------------------------------------------

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

_g, _b, _f = SPREAD['graph'], SPREAD['blocked'], SPREAD['flat']
_gated = SEPARATION['skillsGated']['graph_vs_blocked']
_learned = SEPARATION['skillsLearned']['graph_vs_blocked']
_retain = SEPARATION['retentionAt30d']['graph_vs_blocked']
_flat_retain = SEPARATION['retentionAt30d']['graph_vs_flat']

HONESTY = {
    'status': 'SCRIPTED: every number in this registry came out of running '
              'control/sim_curriculum.mjs, a hand-written deterministic '
              'simulation over an authored skill ladder and an authored '
              'learner model. Nothing here was observed of a person. Not one '
              'number is RECORDED, and the summary statistics are not '
              'promoted to DERIVED - see tier_is_not_derived.',
    'tier_is_not_derived': 'DERIVED in this bundle means computed from '
                           'something RECORDED, by a rule you can read. The '
                           'min, max, median, mean and separation figures '
                           'here are computed by a rule you can read, but '
                           'from SCRIPTED output rather than from a '
                           'recording. A summary cannot outrank what it '
                           'summarises, so it keeps the SCRIPTED tier.',
    'what_is_measured': 'Whether the ACP-05 sequencer converts three stated '
                        'beliefs into outcomes inside a simulation that '
                        'assumes those beliefs. That is a question about '
                        'code, and these numbers answer it.',
    'what_is_not_measured': 'Whether the three beliefs hold for a person. '
                            'This pack runs no learner, observes no cohort '
                            'and visits no hall. The simulation would produce '
                            'these same numbers if every one of its '
                            'assumptions were false about human beings.',
    'no_cohort_claim': 'Nothing in this registry licenses a statement about '
                       'real learners, real halls, real apprentices or real '
                       'outcomes. "The sequencer beats blocked practice by X" '
                       'is not a sentence this pack supports in any form; the '
                       'supported sentence names the simulation and its '
                       'assumptions in the same breath as the number.',
    'the_limit_is_the_sources_own': 'The limit is not this pack\'s summary of '
                                    'the subject. It is quoted verbatim from '
                                    'the header of control/sim_curriculum.mjs '
                                    'into limit.sentence, and evals/test.mjs '
                                    're-extracts it from that file and fails '
                                    'if the two stop matching or if the '
                                    'quotation is softened.',
    'the_spread_is_the_result': 'Across %d seeds, %d of the %d '
                                'metric-by-strategy-pair comparisons separate '
                                'on every seed and %d overlap. An overlapping '
                                'interval is reported as an overlap in '
                                'separation, not rounded away into a mean.'
                                % (len(SEEDS), _disjoint,
                                   len(METRICS) * len(PAIRS), _overlap),
    'blocked_wins_two_of_them': 'This is not a clean win for the sequencer '
                                'and the registry does not present one. '
                                'Across every seed, blocked practice learned '
                                'MORE skills than graph (%g-%g against '
                                '%g-%g) and gained more raw ability (%g-%g '
                                'against %g-%g). What graph does that '
                                'blocked never does in this run is pass the '
                                'skill gate (%g-%g against a flat %g) and '
                                'hold what was learned to the %d-day probe '
                                '(%g-%g against %g-%g). Reporting either half '
                                'alone would be a selected result.'
                                % (_b['skillsLearned']['min'],
                                   _b['skillsLearned']['max'],
                                   _g['skillsLearned']['min'],
                                   _g['skillsLearned']['max'],
                                   _b['totalAbilityGained']['min'],
                                   _b['totalAbilityGained']['max'],
                                   _g['totalAbilityGained']['min'],
                                   _g['totalAbilityGained']['max'],
                                   _g['skillsGated']['min'],
                                   _g['skillsGated']['max'],
                                   _b['skillsGated']['max'],
                                   PARAMS['retention_probe_days'],
                                   _g['retentionAt30d']['min'],
                                   _g['retentionAt30d']['max'],
                                   _b['retentionAt30d']['min'],
                                   _b['retentionAt30d']['max']),
    'the_retention_interval_that_overlaps': 'graph and flat retention '
                                            'intervals %s across these '
                                            'seeds, and the reason is the '
                                            'denominator, not the finding: '
                                            'retentionAt30d is a mean over '
                                            'the skills a run actually '
                                            'learned, and flat learned none '
                                            'at all on %d of %d seeds, where '
                                            'the subject reports 0. A 0 there '
                                            'means there was nothing left to '
                                            'retain, not that everything '
                                            'decayed. flat\'s retention '
                                            'interval is not comparable with '
                                            'the other two and must not be '
                                            'read as one.'
                                            % ('overlap' if _flat_retain['overlap']
                                               else 'do not overlap',
                                               EMPTY_DENOM['flat'], len(SEEDS)),
    'determinism': 'The subject seeds mulberry32 per run and touches no clock '
                   'and no network. The %d seeds are recorded, and '
                   'evals/test.mjs re-runs every one of the %d runs and '
                   'compares field by field against what is written here. A '
                   'result that cannot be reproduced is not a result.'
                   % (len(SEEDS), len(RUNS)),
    'runtime': 'The full %d-run sweep took %d ms of simulation time inside '
               'node (%d ms wall including process start) on the machine '
               'that built this. Nothing was shortened to make it quick: '
               'attempts, per-day and session length are the subject\'s own '
               'constants, read out of the file rather than typed here.'
               % (len(RUNS), need(SIM, 'elapsed_ms', 'the driver output'),
                  WALL_MS),
    'the_one_field_that_is_not_reproducible': 'counts.sim_elapsed_ms and '
                                              'counts.wall_ms are wall-clock '
                                              'timings of the machine that '
                                              'ran the build. They change on '
                                              'every build and no check holds '
                                              'them to a value; they are here '
                                              'so a reader knows the sweep is '
                                              'seconds rather than hours. '
                                              'Every other number in this '
                                              'registry is reproduced exactly '
                                              'by evals/test.mjs.',
    'one_union': 'Every run is the subject\'s default union, %r - %d skills. '
                 'This pack does not sweep unions and says nothing about the '
                 'other ladders in pack/registry/skills.json.'
                 % (UNION, len(UNION_SKILLS)),
}

# ---------------------------------------------------------------------------
# Is "course completion" VERIFIABLE? A lesson is a list of steps; only some
# step kinds record an episode (lessons.json#step_kinds[k].records is a kind
# name; null means the step leaves nothing behind). Read, counted, never typed.

def _reg(rel):
    p = ROOT / rel
    d = json.loads(p.read_text())
    return d, {'path': rel,
               'source_stamp': need(d, 'source_stamp', rel),
               'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


LESSONS_REG, _lessons_in = _reg('lessons/registry/lessons.json')
SIMS_FULL, _sims_in = _reg('sims/registry/sims.json')
CAMPUSES_REG, _campuses_in = _reg('unions/registry/campuses.json')
UNIONS_REG, _unions_in = _reg('unions/registry/unions.json')
HALLS_REG = json.loads((ROOT / 'pack' / 'registry' / 'halls.json').read_text())
_halls_in = {'path': 'pack/registry/halls.json',
             'source_stamp': None,
             'why_no_stamp': 'pack/registry/halls.json carries no source_stamp '
                             'field; its sha256 is the guard',
             'sha256': hashlib.sha256(
                 (ROOT / 'pack' / 'registry' / 'halls.json').read_bytes()).hexdigest()}

_KINDS = need(LESSONS_REG, 'step_kinds', 'lessons/registry/lessons.json')
RECORDING_KINDS = sorted(k for k in _KINDS
                         if need(_KINDS[k], 'records', 'lessons.json#step_kinds[%s]' % k) is not None)
SILENT_KINDS = sorted(k for k in _KINDS if k not in RECORDING_KINDS)
_LESSONS = need(LESSONS_REG, 'lessons', 'lessons/registry/lessons.json')
_EDGES = need(need(LESSONS_REG, 'ladder', 'lessons.json'), 'edges', 'lessons.json#ladder')
_SIMS = need(SIMS_FULL, 'sims', 'sims/registry/sims.json')
_ALL_HALL_SLUGS = sorted(need(h, 'slug', 'pack/registry/halls.json#halls[]')
                         for h in need(HALLS_REG, 'halls', 'pack/registry/halls.json'))
_UNION_SLUGS = sorted(need(u, 'slug', 'unions.json#unions[]')
                      for u in need(UNIONS_REG, 'unions', 'unions/registry/unions.json'))
_CAMPUS_OF = {}
for _cid, _c in need(CAMPUSES_REG, 'campuses', 'unions/registry/campuses.json').items():
    for _h in need(_c, 'halls', 'campuses.json#campuses[%s]' % _cid):
        _CAMPUS_OF[_h] = _cid

PER_LESSON = {}
for _lid in sorted(_LESSONS):
    _l = _LESSONS[_lid]
    _steps = need(_l, 'steps', 'lessons.json#lessons[%s]' % _lid)
    _rec = [s for s in _steps if need(s, 'kind', 'a step of %s' % _lid) in RECORDING_KINDS]
    _sil = [s for s in _steps if s['kind'] in SILENT_KINDS]
    if len(_rec) + len(_sil) != len(_steps):
        raise ValueError('evals: lesson %s uses a step kind lessons.json#step_kinds '
                         'does not declare' % _lid)
    _hall = need(_l, 'hall', 'lessons.json#lessons[%s]' % _lid)
    if _hall not in _ALL_HALL_SLUGS:
        raise ValueError('evals: lesson %s names hall %r, absent from pack/registry/halls.json'
                         % (_lid, _hall))
    _cls = ('full' if len(_sil) == 0 and len(_rec) > 0
            else 'partial' if len(_rec) > 0 else 'none')
    PER_LESSON[_lid] = {
        'hall': _hall,
        'campus': need(_l, 'campus', 'lessons.json#lessons[%s]' % _lid),
        'steps': len(_steps),
        'evidence_backed_steps': len(_rec),
        'self_reported_steps': len(_sil),
        'evidence_kinds': sorted({s['kind'] for s in _rec}),
        'silent_kinds': sorted({s['kind'] for s in _sil}),
        'sims_run': sorted({need(s, 'sim', 'a sim step of %s' % _lid)
                            for s in _steps if s['kind'] == 'sim'}),
        'can_be_evidence_backed': len(_rec) >= 1,
        'fully_evidence_backed': _cls == 'full',
        'classification': _cls,
    }

_by_cls = {c: sorted(k for k in PER_LESSON if PER_LESSON[k]['classification'] == c)
           for c in ('full', 'partial', 'none')}
_halls_with = sorted({v['hall'] for v in PER_LESSON.values()})
_halls_without = [h for h in _ALL_HALL_SLUGS if h not in set(_halls_with)]
_verifiable = {k for k in PER_LESSON if PER_LESSON[k]['can_be_evidence_backed']}

PER_UNION = {}
for _u in _UNION_SLUGS:
    _mine = [k for k in PER_LESSON if PER_LESSON[k]['hall'] == _u]
    if _mine:
        PER_UNION[_u] = {'lessons': len(_mine),
                         'verifiable': sum(1 for k in _mine if k in _verifiable),
                         'fully_verifiable': sum(1 for k in _mine
                                                 if PER_LESSON[k]['fully_evidence_backed'])}
if sorted(PER_UNION) != _halls_with:
    raise ValueError('evals: lesson halls and unions.json slugs disagree: %r'
                     % sorted(set(_halls_with) ^ set(PER_UNION)))

# Sim thresholds: sims.json has no seat-level pass threshold; it has a rubric
# per sim whose axes each carry a `pass` rule ("informational" is not one).
SIM_THRESHOLDS = {}
for _sid in sorted({s for v in PER_LESSON.values() for s in v['sims_run']}):
    if _sid not in _SIMS:
        raise KeyError('evals: sims/registry/sims.json#sims is missing %r, which a '
                       'sim step runs' % _sid)
    _rub = need(_SIMS[_sid], 'rubric', 'sims.json#sims[%s]' % _sid)
    _axes = {}
    for _a in _rub:
        _ax = need(_a, 'axis', 'a rubric axis of %s' % _sid)
        _axes[_ax] = need(_a, 'pass', 'sims.json#sims[%s].rubric[%s]' % (_sid, _ax))
    _thr = {k: v for k, v in _axes.items() if v != 'informational'}
    SIM_THRESHOLDS[_sid] = {'rubric_axes': len(_axes),
                            'thresholded_axes': len(_thr),
                            'informational_axes': len(_axes) - len(_thr),
                            'pass_rules': _thr}
_thr_declared = sum(1 for v in SIM_THRESHOLDS.values() if v['thresholded_axes'] > 0)

# Ladder: cycles and prerequisites that are themselves not verifiable.
_needs = {}
for _e in _EDGES:
    _a = need(_e, 'lesson', 'lessons.json#ladder.edges[]')
    _b = need(_e, 'needs', 'lessons.json#ladder.edges[]')
    for _x in (_a, _b):
        if _x not in PER_LESSON:
            raise KeyError('evals: ladder edge names %r, absent from lessons.json#lessons' % _x)
    _needs.setdefault(_a, []).append(_b)


def _count_cycles(needs):
    """Number of nodes that sit on a cycle (0 when acyclic). Iterative DFS."""
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {k: WHITE for k in PER_LESSON}
    on_cycle = set()
    for root in sorted(PER_LESSON):
        if colour[root] != WHITE:
            continue
        stack = [(root, iter(sorted((needs[root] if root in needs else []))))]
        colour[root] = GREY
        path = [root]
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                colour[node] = BLACK
                stack.pop()
                path.pop()
                continue
            if colour[nxt] == GREY:
                on_cycle.update(path[path.index(nxt):])
            elif colour[nxt] == WHITE:
                colour[nxt] = GREY
                path.append(nxt)
                stack.append((nxt, iter(sorted((needs[nxt] if nxt in needs else [])))))
    return len(on_cycle)


_cycle_nodes = _count_cycles(_needs)
_unverifiable_prereqs = sorted({b for a in _needs for b in _needs[a] if b not in _verifiable})
_edges_into_unverifiable = sum(1 for a in _needs for b in _needs[a] if b not in _verifiable)

COMPLETION_EVIDENCE = {
    'inputs': {'lessons': _lessons_in, 'sims': _sims_in, 'campuses': _campuses_in,
               'unions': _unions_in, 'halls': _halls_in},
    'recording_kinds': RECORDING_KINDS,
    'silent_kinds': SILENT_KINDS,
    'kinds_read_from': 'lessons/registry/lessons.json#step_kinds[k].records; a '
                       'kind records when that field is a kind name, and is '
                       'silent when it is null. station and crib are silent '
                       'by that field, whatever their name suggests.',
    'per_lesson': PER_LESSON,
    'rollup': {
        'lessons': len(PER_LESSON),
        'steps': sum(v['steps'] for v in PER_LESSON.values()),
        'evidence_backed_steps': sum(v['evidence_backed_steps'] for v in PER_LESSON.values()),
        'self_reported_steps': sum(v['self_reported_steps'] for v in PER_LESSON.values()),
        'fully_verifiable': len(_by_cls['full']),
        'partly_verifiable': len(_by_cls['partial']),
        'not_verifiable': len(_by_cls['none']),
        'lessons_by_class': _by_cls,
        'halls_total': len(_ALL_HALL_SLUGS),
        'halls_with_a_lesson': len(_halls_with),
        'halls_with_no_lesson': len(_halls_without),
        'halls_with_no_lesson_list': _halls_without,
        'halls_with_no_lesson_means': 'a hall with no lesson has NO course to '
                                      'complete; nothing about completion can be '
                                      'verified or falsified there because nothing '
                                      'is offered',
        'campuses_of_lesson_halls': sorted({_CAMPUS_OF[h] for h in _halls_with if h in _CAMPUS_OF}),
        'lesson_halls_absent_from_campus_rosters': sorted(h for h in _halls_with if h not in _CAMPUS_OF),
    },
    'per_union': PER_UNION,
    'unions_total': len(_UNION_SLUGS),
    'unions_with_a_lesson': len(PER_UNION),
    'sim_thresholds': {
        'sims_run_by_a_sim_step': len(SIM_THRESHOLDS),
        'thresholds_declared': _thr_declared,
        'per_sim': SIM_THRESHOLDS,
        'where': 'sims/registry/sims.json#sims[id].rubric[].pass, one rule per '
                 'axis; there is no seat-level or scenario-level pass threshold '
                 'field anywhere in sims.json',
        're_derivable': _thr_declared == len(SIM_THRESHOLDS),
        'passed_is_recorded_by': 'the seat, at run time, against those axis rules; '
                                 'a "passed" flag in an episode is the seat\'s '
                                 'statement and this pack re-derives none of them '
                                 'from a recording, because no recording is shipped',
    },
    'ladder': {
        'edges': len(_EDGES),
        'lessons_on_a_cycle': _cycle_nodes,
        'acyclic': _cycle_nodes == 0,
        'prerequisites_not_verifiable': _unverifiable_prereqs,
        'edges_into_unverifiable_prerequisite': _edges_into_unverifiable,
    },
    'means': 'a lesson is verifiable when at least one of its steps records an '
             'episode; fully verifiable when every step does. A self-reported '
             'step is one the learner marks done and nothing else records.',
    'honest': 'this measures what the registries DECLARE, not what any learner '
              'did: no episode has been recorded and no seat has been run. '
              'Every count here is of steps and rules, and it says nothing '
              'about whether the recorded episodes, when they exist, prove '
              'competence.',
}
if COMPLETION_EVIDENCE['ladder']['lessons_on_a_cycle'] != 0:
    raise ValueError('evals: the lesson ladder has a cycle; completion order is undefined')
if COMPLETION_EVIDENCE['rollup']['fully_verifiable'] + COMPLETION_EVIDENCE['rollup']['partly_verifiable'] + COMPLETION_EVIDENCE['rollup']['not_verifiable'] != len(PER_LESSON):
    raise ValueError('evals: lesson classes do not partition the lessons')


# ---------------------------------------------------------------------------
# ROBOT READINESS: how usable the recorded engagement is for training an agent
# or a robot - measured from the registries and from the page source, by
# structure, never typed. What a seat's gauges() returns is read out of
# web/build_3d.py with a regex a test repeats; what the recorder keeps per
# episode and per TRACE sample is read out of the same file the same way; the
# scripted reference policies are the keys of the page's own OPERATORS table.
# The class each seat lands in is a rule stated in the registry, not a score.

TRAINING_REG, _training_in = _reg('training/registry/training.json')
ORBIS_REG, _orbis_in = _reg('orbis/registry/orbis.json')
META_REG, _meta_in = _reg('meta/registry/metaverse.json')
PAGE = ROOT / 'web' / 'build_3d.py'
PAGE_SRC = PAGE.read_text()
_page_in = {'path': 'web/build_3d.py',
            'source_stamp': None,
            'why_no_stamp': 'web/build_3d.py is a builder, not a registry, and '
                            'carries no source_stamp; its sha256 is the guard',
            'sha256': hashlib.sha256(PAGE.read_bytes()).hexdigest()}
_SIM_IDS = sorted(_SIMS)

# -- which factory function builds which seat: the ternary chain in startSim --
_chain_m = re.search(r"\n  sim = simId === '[a-z-]+' \? \w+Sim\(P\)\n(?:    : simId === "
                     r"'[a-z-]+' \? \w+Sim\(P\)\n)* *: simId === '[a-z-]+' \? \w+Sim\(P\) : "
                     r"(\w+Sim)\(P\);", PAGE_SRC)
if not _chain_m:
    raise ValueError('evals: the seat factory chain (`sim = simId === ... ? ...Sim(P)`) '
                     'could not be found in web/build_3d.py')
FACTORY_OF = dict(re.findall(r"simId === '([a-z-]+)' \? (\w+Sim)\(P\)", _chain_m.group(0)))
_fallback = [s for s in _SIM_IDS if s not in FACTORY_OF]
if len(_fallback) == 1:
    FACTORY_OF[_fallback[0]] = _chain_m.group(1)
    FACTORY_FALLBACK = _fallback[0]
else:
    FACTORY_FALLBACK = None


def _factory_body(fn):
    m = re.search(r'\nfunction %s\(P = \{\}\) \{\n(.*?)\n\}\n' % re.escape(fn), PAGE_SRC, re.S)
    return m.group(1) if m else None


def gauge_fields(body):
    """The keys of the object a seat's gauges() returns, by structure.

    Both shapes the page uses are read: `gauges: () => ({ k: ..., })` and
    `gauges: () => { ...; return { k: ..., }; }`. Keys are the lines at one
    indent step inside the literal; anything else inside it is a shape this
    reader does not understand and it says so rather than guessing.
    """
    m = re.search(r'\n( +)gauges: \(\) => (\(\{|\{)\n', body)
    if not m:
        return None, 'no `gauges: () =>` arrow function in the seat factory'
    ind = m.group(1)
    rest = body[m.end():]
    if m.group(2) == '{':
        r = re.search(r'^( +)return \{\n', rest, re.M)
        if not r:
            return None, 'gauges() has a block body with no `return {` object literal'
        ind = r.group(1)
        rest = rest[r.end():]
    keys = []
    for ln in rest.split('\n'):
        km = re.match(r'^%s  ([A-Za-z_]\w*): ' % ind, ln)
        if km:
            keys.append(km.group(1))
            continue
        if re.match(r'^%s(\}\)|\})' % ind, ln):
            break
        return None, 'an unrecognised line inside the gauges() literal: %r' % ln.strip()
    if not keys:
        return None, 'the gauges() literal is empty'
    return keys, None


# -- the recorder: what an episode carries, and what a TRACE sample carries --
_rec_ctl = re.search(r"controls: def\.controls\.map\(\(c\) => c\.(\w+)\),", PAGE_SRC)
if not _rec_ctl:
    raise ValueError('evals: the recorder line `controls: def.controls.map((c) => c.<field>)` '
                     'is gone from web/build_3d.py')
CONTROL_FIELD_CAPTURED = _rec_ctl.group(1)
_push = re.search(r'simTicks\.push\((\{.*\})\);', PAGE_SRC)
if not _push:
    raise ValueError('evals: the TRACE sampler `simTicks.push({...})` is gone from web/build_3d.py')
TRACE_SAMPLE_FIELDS = re.findall(r'(?:^\{ |, )([A-Za-z_]\w*): ', _push.group(1))
_page_hz = re.search(r'TRACE_MS = Math\.round\(1000 / D\.training\.trace\.sample_hz\)', PAGE_SRC)
_page_cap = re.search(r'TRACE_MAX = D\.training\.trace\.max_samples', PAGE_SRC)
_page_guard = re.search(r'if \(!traceOn \|\| !sim \|\| !sim\.gauges \|\| simTicks\.length >= TRACE_MAX\) return;',
                        PAGE_SRC)
_keys_obj = re.search(r'\nconst keys = \{\};\n', PAGE_SRC) and re.search(r'keys\[e\.code\] = true;', PAGE_SRC)
_op_keys = re.search(r"const OP_KEYS = \[([^\]]*)\];", PAGE_SRC)
_space = re.search(r"e\.code === '(\w+)'\) \{ e\.preventDefault\(\); if \(!opRun\) sim\.action\?\.\(\); \}",
                   PAGE_SRC)
for _what, _found in (('the page reads sample_hz from D.training.trace', _page_hz),
                      ('the page reads max_samples from D.training.trace', _page_cap),
                      ('the TRACE guard line', _page_guard),
                      ('the key-state object `keys` filled by keydown', _keys_obj),
                      ('the OP_KEYS list', _op_keys),
                      ('the Space press edge that calls sim.action()', _space)):
    if not _found:
        raise ValueError('evals: %s could not be found in web/build_3d.py by structure' % _what)
OP_KEYS = re.findall(r"'(\w+)'", _op_keys.group(1))
ACTION_EDGE_KEY = _space.group(1)
_ctl_state_names = ('keys', 'controls', 'action', 'inputs')
ACTION_PER_SAMPLE = any(f in _ctl_state_names for f in TRACE_SAMPLE_FIELDS)

_TRACE = need(TRAINING_REG, 'trace', 'training/registry/training.json')
TRACE_HZ = need(_TRACE, 'sample_hz', 'training.json#trace')
TRACE_MAX = need(_TRACE, 'max_samples', 'training.json#trace')

# -- the scripted reference policies: the page's OPERATORS table --------------
_ops_m = re.search(r'\nconst OPERATORS = \{\n(.*?)\n\};\n', PAGE_SRC, re.S)
if not _ops_m:
    raise ValueError('evals: the OPERATORS table is gone from web/build_3d.py')
_ops_body = _ops_m.group(1)
_op_heads = [(m.group(1), m.start()) for m in re.finditer(r"^  '([a-z-]+)': \{", _ops_body, re.M)]
PAGE_POLICY = {}
for _i, (_sid, _at) in enumerate(_op_heads):
    _end = _op_heads[_i + 1][1] if _i + 1 < len(_op_heads) else len(_ops_body)
    PAGE_POLICY[_sid] = re.search(r'^    step\(', _ops_body[_at:_end], re.M) is not None
if not re.search(r'OPERATORS\[opRun\.sim\]\.step\(sim\.gauges\(\), opRun\)', PAGE_SRC):
    raise ValueError('evals: opStep no longer feeds the policy the seat\'s own gauges(); '
                     'the policy_input fact below would be wrong')
_ORBIS_TEXT = json.dumps(ORBIS_REG)
ORBIS_RUNNERS = [{'path': need(r, 'path', 'orbis.json#runners[]'),
                  'model': need(r, 'model', 'orbis.json#runners[]')}
                 for r in need(ORBIS_REG, 'runners', 'orbis/registry/orbis.json')]

# -- episode kinds: which could carry a trace at all --------------------------
_KINDS_T = need(TRAINING_REG, 'episode_kinds', 'training/registry/training.json')
EPISODE_KINDS = {}
for _k in sorted(_KINDS_T):
    _kd = _KINDS_T[_k]
    _fields = need(_kd, 'fields', 'training.json#episode_kinds[%s]' % _k)
    _oshape = need(_kd, 'outcome_shape', 'training.json#episode_kinds[%s]' % _k)
    EPISODE_KINDS[_k] = {
        'fields': _fields,
        'has_outcome': 'outcome' in _fields,
        'outcome_shape': _oshape,
        'can_carry_trace': isinstance(_oshape, dict) and 'trace' in _oshape,
    }
KINDS_WITH_TRACE = sorted(k for k in EPISODE_KINDS if EPISODE_KINDS[k]['can_carry_trace'])
SIM_OUTCOME_SHAPE = need(need(_KINDS_T, 'sim', 'training.json#episode_kinds'), 'outcome_shape',
                         'training.json#episode_kinds[sim]')

# -- the class rule ------------------------------------------------------------
CLASS_LADDER = ['no-observation', 'observation-only', 'observation+action',
                'observation+action+reference-policy']
CLASS_RULE = {
    'no-observation': 'the seat\'s gauges() could not be found by structure, or returns nothing',
    'observation-only': 'gauges() found, and a TRACE sample carries a gauge reading but no '
                        'control state - what the learner did at that second is not in the sample',
    'observation+action': 'a TRACE sample carries both the gauge reading and the control state '
                          'at that second (a field named one of %s)' % ', '.join(_ctl_state_names),
    'observation+action+reference-policy': 'observation+action, and the page\'s OPERATORS table '
                                           'holds a step() policy for the seat that '
                                           'sims/registry/sims.json#sims[id].operator declares',
}


def readiness_class(gauges, action_per_sample, policy):
    if not gauges:
        return CLASS_LADDER[0]
    if not action_per_sample:
        return CLASS_LADDER[1]
    if not policy:
        return CLASS_LADDER[2]
    return CLASS_LADDER[3]


PER_SIM = {}
for _sid in _SIM_IDS:
    _s = _SIMS[_sid]
    _fn = FACTORY_OF[_sid] if _sid in FACTORY_OF else None
    _body = _factory_body(_fn) if _fn else None
    if _fn is None:
        _g, _why = None, 'no factory for this seat in the startSim chain of web/build_3d.py'
    elif _body is None:
        _g, _why = None, 'the factory %s could not be found at column 0 in web/build_3d.py' % _fn
    else:
        _g, _why = gauge_fields(_body)
    _controls = need(_s, 'controls', 'sims.json#sims[%s]' % _sid)
    _captured = [need(c, CONTROL_FIELD_CAPTURED, 'sims.json#sims[%s].controls[]' % _sid)
                 for c in _controls]
    _scen = need(_s, 'scenarios', 'sims.json#sims[%s]' % _sid)
    _op = need(_s, 'operator', 'sims.json#sims[%s]' % _sid)
    _declared = (len(need(_op, 'levels', 'sims.json#sims[%s].operator' % _sid)) > 0
                 and len(need(_op, 'procedure', 'sims.json#sims[%s].operator' % _sid)) > 0)
    _in_page = _sid in PAGE_POLICY and PAGE_POLICY[_sid]
    _policy = _declared and _in_page
    _dash = [need(d, 'id', 'sims.json#sims[%s].dash[]' % _sid)
             for d in need(_s, 'dash', 'sims.json#sims[%s]' % _sid)]
    _cls = readiness_class(_g, ACTION_PER_SAMPLE, _policy)
    _nxt = CLASS_LADDER[CLASS_LADDER.index(_cls) + 1] if _cls != CLASS_LADDER[-1] else None
    PER_SIM[_sid] = {
        'name': need(_s, 'name', 'sims.json#sims[%s]' % _sid),
        'kind': need(_s, 'kind', 'sims.json#sims[%s]' % _sid),
        'has_seat': _fn is not None,
        'factory': _fn,
        'halls_bound': len(need(_s, 'halls', 'sims.json#sims[%s]' % _sid)),
        'scenarios': len(_scen),
        'scenario_ids': [need(x, 'id', 'sims.json#sims[%s].scenarios[]' % _sid) for x in _scen],
        'rubric_axes': [need(a, 'axis', 'sims.json#sims[%s].rubric[]' % _sid)
                        for a in need(_s, 'rubric', 'sims.json#sims[%s]' % _sid)],
        'controls_declared': [{'keys': need(c, 'keys', 'a control of %s' % _sid),
                               'action': need(c, 'action', 'a control of %s' % _sid)}
                              for c in _controls],
        'controls_captured': _captured,
        'controls_captured_means': 'the declared control scheme (each control\'s `%s` string), '
                                   'written once per episode - not the state of any control '
                                   'at any moment of the run' % CONTROL_FIELD_CAPTURED,
        'gauges': _g,
        'gauges_why_null': _why,
        'gauges_count': len(_g) if _g else 0,
        'dash_ids': _dash,
        'gauges_equal_dash_ids': _g == _dash,
        'trace_max_samples': TRACE_MAX,
        'trace_sample_hz': TRACE_HZ,
        'trace_sample_fields': TRACE_SAMPLE_FIELDS,
        'action_per_sample': ACTION_PER_SAMPLE,
        'action_per_sample_why': None if ACTION_PER_SAMPLE else (
            'the sampler in web/build_3d.py pushes {%s} once a second: the gauge reading '
            'alone. The key state the seat reads that same frame (`keys[e.code]`, codes %s) '
            'and the %s press edge that calls sim.action() are not written into the sample.'
            % (', '.join(TRACE_SAMPLE_FIELDS), ', '.join(OP_KEYS), ACTION_EDGE_KEY)),
        'reference_policy': _policy,
        'reference_policy_declared_in_sims_registry': _declared,
        'reference_policy_in_page_operators': _in_page,
        'reference_policy_levels': need(_op, 'levels', 'sims.json#sims[%s].operator' % _sid),
        'reference_policy_guarantees': need(_op, 'guarantees', 'sims.json#sims[%s].operator' % _sid),
        'reference_policy_in_orbis': _sid in _ORBIS_TEXT,
        'episode_kinds_that_can_carry_a_trace': KINDS_WITH_TRACE,
        'outcome_shape': SIM_OUTCOME_SHAPE,
        'readiness_class': _cls,
        'next_class': _nxt,
    }

_by_class = {c: sorted(k for k in PER_SIM if PER_SIM[k]['readiness_class'] == c)
             for c in CLASS_LADDER}
_n_seat = sum(1 for v in PER_SIM.values() if v['has_seat'])
_n_gauges = sum(1 for v in PER_SIM.values() if v['gauges'] is not None)
_n_trace = sum(1 for v in PER_SIM.values() if v['gauges'] is not None and len(KINDS_WITH_TRACE) > 0)
_n_policy = sum(1 for v in PER_SIM.values() if v['reference_policy'])
_n_orbis = sum(1 for v in PER_SIM.values() if v['reference_policy_in_orbis'])
_n_obs_act = sum(1 for v in PER_SIM.values() if v['action_per_sample'])
_n_scen = sum(v['scenarios'] for v in PER_SIM.values())
_n_gfields = sum(v['gauges_count'] for v in PER_SIM.values())
_n_ctl = sum(len(v['controls_captured']) for v in PER_SIM.values())
_n_dash_eq = sum(1 for v in PER_SIM.values() if v['gauges_equal_dash_ids'])
_EXPORT = need(TRAINING_REG, 'export_format', 'training/registry/training.json')
_BRIDGE = need(META_REG, 'unity_bridge', 'meta/registry/metaverse.json')

ROBOT_READINESS = {
    'inputs': {'training': _training_in, 'sims': _sims_in, 'orbis': _orbis_in,
               'metaverse': _meta_in, 'page': _page_in},
    'read_by_structure': {
        'seat_factories': 'the `sim = simId === ... ? ...Sim(P)` chain in startSim; the '
                          'seat missing from the chain is the chain\'s fallback',
        'seat_factory_fallback': FACTORY_FALLBACK,
        'gauges': 'inside `function <factory>(P = {}) {` up to the next column-0 `}`, the '
                  'keys one indent step inside the literal that `gauges: () =>` returns',
        'controls_captured': 'the recorder\'s `controls: def.controls.map((c) => c.%s)`'
                             % CONTROL_FIELD_CAPTURED,
        'trace_sample': 'the fields of the object `simTicks.push({...})` writes',
        'reference_policy': 'the keys of `const OPERATORS = {...}` that carry a `step(` '
                            'function, intersected with sims.json#sims[id].operator '
                            'declaring levels and a procedure',
        'policy_input': 'opStep calls OPERATORS[sim].step(sim.gauges(), run): the policy '
                        'sees the same gauges a TRACE sample keeps, nothing the seat keeps private',
        'reference_policy_in_orbis': 'whether the seat id occurs anywhere in '
                                     'orbis/registry/orbis.json',
    },
    'trace': {
        'sample_hz': TRACE_HZ,
        'max_samples': TRACE_MAX,
        'max_seconds_covered': TRACE_MAX / TRACE_HZ,
        'page_reads_hz_and_cap_from': 'training/registry/training.json#trace (D.training.trace)',
        'sample_fields': TRACE_SAMPLE_FIELDS,
        'sampled_from': need(_TRACE, 'sampled_from', 'training.json#trace'),
        'default': need(_TRACE, 'default', 'training.json#trace'),
        'action_per_sample': ACTION_PER_SAMPLE,
        'key_state_object': 'keys (web/build_3d.py: `const keys = {}`; keydown sets keys[e.code])',
        'key_codes_the_policies_drive': OP_KEYS,
        'action_edge_key': ACTION_EDGE_KEY,
        'granularity_as_training_registry_states_it': need(
            need(TRAINING_REG, 'honesty', 'training.json'), 'granularity', 'training.json#honesty'),
    },
    'episode_kinds': EPISODE_KINDS,
    'kinds_that_can_carry_a_trace': KINDS_WITH_TRACE,
    'per_sim': PER_SIM,
    'classes': {
        'ladder': CLASS_LADDER,
        'rule': CLASS_RULE,
        'is_a_score': False,
        'means': 'a class names which of three facts hold for a seat - an observation '
                 'per sample, an action per sample, a scripted policy to compare against. '
                 'It orders nothing else and ranks no seat above another.',
    },
    'rollup': {
        'seats_in_registry': len(PER_SIM),
        'seats_with_a_factory_in_the_page': _n_seat,
        'seats_with_gauges_found': _n_gauges,
        'seats_with_gauges_null': len(PER_SIM) - _n_gauges,
        'seats_whose_gauges_equal_their_dash_ids': _n_dash_eq,
        'seats_with_traces_possible': _n_trace,
        'seats_with_reference_policy': _n_policy,
        'seats_with_reference_policy_in_orbis': _n_orbis,
        'seats_with_observation_and_action': _n_obs_act,
        'seats_by_class': {c: len(_by_class[c]) for c in CLASS_LADDER},
        'seats_by_class_list': _by_class,
        'scenarios_total': _n_scen,
        'gauge_fields_total': _n_gfields,
        'controls_captured_total': _n_ctl,
        'episode_kinds': len(EPISODE_KINDS),
        'episode_kinds_that_can_carry_a_trace': len(KINDS_WITH_TRACE),
        'orbis_runners': ORBIS_RUNNERS,
        'orbis_carries_no_seat_policy': _n_orbis == 0,
        'orbis_carries_no_seat_policy_why': 'orbis/registry/orbis.json names no seat: its '
                                            'product is a text prompt per module and its '
                                            'runners are video runners; the scripted '
                                            'reference policy of a seat lives in the page\'s '
                                            'OPERATORS table and is declared in '
                                            'sims/registry/sims.json#sims[id].operator',
    },
    'to_reach_next_class': {
        'from_observation-only_to_observation+action': {
            'record_per_sample': {
                't': 'already in the sample (training.json#trace: sample_hz %s, cap %d)'
                     % (TRACE_HZ, TRACE_MAX),
                'gauges': 'already in the sample (the seat\'s own gauges() readout)',
                'keys': 'NOT in the sample: the state of the page\'s `keys` object at the '
                        'sampled frame for the codes the seat reads - %s - which are the '
                        'sims.json#sims[id].controls[].keys of that seat as key codes'
                        % ', '.join(OP_KEYS),
                'action': 'NOT in the sample: whether the %s press edge (sim.action()) '
                          'fired since the previous sample' % ACTION_EDGE_KEY,
            },
            'where_it_would_land': 'training.json#episode_kinds.sim.outcome_shape.trace, today '
                                   '"%s"' % need(SIM_OUTCOME_SHAPE, 'trace', 'outcome_shape'),
            'scripted_actions_recoverable_by_replay': 'a scripted-reference episode carries '
                                                      'operator {level, seed, scenario, steps, dt}, '
                                                      'and the page replays it deterministically '
                                                      '(opRunHeadless), so that policy\'s key '
                                                      'output at each step can be regenerated '
                                                      'inside the page - the exported file does '
                                                      'not carry it and no consumer outside the '
                                                      'page can obtain it without the page',
        },
        'from_observation+action_to_observation+action+reference-policy': {
            'needs': 'nothing further to record: every seat already has a step() policy in the '
                     'page and a declared operator in sims.json (%d of %d), so the class would '
                     'follow from the action field alone' % (_n_policy, len(PER_SIM)),
        },
    },
    'ml_agents_fork': {
        'repo': need(_BRIDGE, 'repo', 'metaverse.json#unity_bridge'),
        'status_as_recorded_there': need(_BRIDGE, 'status', 'metaverse.json#unity_bridge'),
        'export_shape': need(_EXPORT, 'shape', 'training.json#export_format'),
        'not_a_demo_file': need(_EXPORT, 'not_a_demo_file', 'training.json#export_format'),
        'no_agent_trained': need(_EXPORT, 'no_agent_trained', 'training.json#export_format'),
    },
    'honest': 'no episode has been recorded from a learner - there is no cohort, and the '
              'recorder writes only to the browser that runs it; no agent and no robot has '
              'been trained from this data, here or in the ml-agents fork recorded in '
              'meta/registry/metaverse.json. Every row above is what the registries DECLARE '
              'and what the page source RETURNS, read by structure: %d of %d seats expose a '
              'gauges() readout a TRACE could sample, %d carry a scripted reference policy, '
              'and %d write the control state into a sample - so a trace today is an '
              'observation stream without the action beside it, and no controller can be '
              'learned from it by imitation.' % (_n_gauges, len(PER_SIM), _n_policy, _n_obs_act),
}
if sum(ROBOT_READINESS['rollup']['seats_by_class'].values()) != len(PER_SIM):
    raise ValueError('evals: readiness classes do not partition the seats')
if ROBOT_READINESS['rollup']['seats_with_observation_and_action'] != 0 and not ACTION_PER_SAMPLE:
    raise ValueError('evals: an observation+action seat was counted while no sample carries an action')


payload = {
    'pack': 'evals',
    'product': 'the measured output of control/sim_curriculum.mjs across %d '
               'seeds, published together with the limit the simulation '
               'states on itself' % len(SEEDS),
    'pack_version': PACK_VERSION,
    'source_stamp': stamp,
    'provenance': {
        'tier': 'SCRIPTED',
        'tier_set_read_from': 'auth/registry/auth.json#provenance_tiers',
        'tiers_available': list(TIERS),
        'not_recorded': 'nothing here was observed of a real learner',
        'not_ai_synthesized': 'that tier belongs to orbis/ and describes '
                              'generated video; no model runs anywhere in '
                              'this pack or its subject',
    },
    'subject': {
        'path': 'control/sim_curriculum.mjs',
        'sha256': SRC_SHA,
        'spec': 'ACP-15',
        'exports_used': ['run', 'runAll'],
        'union': UNION,
        'skills_in_union': len(UNION_SKILLS),
        'skill_ladder': 'pack/registry/skills.json',
        'skill_ladder_tier': 'AUTHORED',
        'prng': 'mulberry32, seeded per run',
        'parameters': PARAMS,
        'parameters_read_from': 'the constants in control/sim_curriculum.mjs, '
                                'matched out of the source at build time and '
                                'never retyped',
        'strategies': {
            'graph': 'the ACP-05 sequencer: readiness, leverage, review, '
                     'interleaving, wheel-spin diagnosis',
            'blocked': 'the traditional curriculum: prerequisite order, one '
                       'skill worked to mastery before the next',
            'flat': 'any unmastered skill at random, prerequisites ignored '
                    '(the control)',
        },
    },
    'limit': {
        'sentence': LIMIT_SENTENCE,
        'quoted_from': 'control/sim_curriculum.mjs, header comment',
        'quoted_verbatim': True,
        'why_it_is_a_field_and_not_prose': 'so a check can hold one named '
                                           'string to what the source says, '
                                           'rather than scanning this pack\'s '
                                           'own sentences and firing on its '
                                           'honest explanations',
        'what_it_forbids': 'any sentence that reports a strategy difference '
                           'here as a difference for learners',
    },
    'assumptions': {
        'quoted_from': 'control/sim_curriculum.mjs, header comment',
        'status': 'these are the platform\'s pedagogical beliefs. This pack '
                  'records them as beliefs and tests none of them.',
        'items': {k: {'id': k, 'text': ASSUMPTIONS[k],
                      'validated_against_learners': False}
                  for k in sorted(ASSUMPTIONS)},
    },
    'seeds': SEEDS,
    'metrics': METRICS,
    'strategies': STRATEGIES,
    'runs': RUNS,
    'spread': SPREAD,
    'runall_means': RUNALL_ROWS,
    'separation': SEPARATION,
    'retention_empty_denominator_runs': EMPTY_DENOM,
    'hall_independence': HALL_INDEPENDENCE,
    'completion_evidence': COMPLETION_EVIDENCE,
    'robot_readiness': ROBOT_READINESS,
    'counts': {
        'seeds': len(SEEDS),
        'strategies': len(STRATEGIES),
        'runs': len(RUNS),
        'metrics': len(METRICS),
        'comparisons': len(METRICS) * len(PAIRS),
        'comparisons_separating_on_every_seed': _disjoint,
        'comparisons_overlapping': _overlap,
        'assumptions_recorded': len(ASSUMPTIONS),
        'assumptions_validated_against_learners': 0,
        'attempts_per_run': PARAMS['attempts'],
        'total_attempts_simulated': PARAMS['attempts'] * len(RUNS),
        'sim_elapsed_ms': need(SIM, 'elapsed_ms', 'the driver output'),
        'halls_swept': len(ALL_HALLS),
        'distinct_outcomes_across_all_halls': max(_groups.values()),
        'wall_ms': WALL_MS,
    },
    'honesty': HONESTY,
}

_blob = json.dumps(payload)
if 'AI-SYNTHESIZED' in _blob.upper():
    raise ValueError('evals: that word belongs to orbis/')
if payload['provenance']['tier'] != 'SCRIPTED':
    raise ValueError('evals: the tier of a simulation output is SCRIPTED')
if payload['counts']['assumptions_validated_against_learners'] != 0:
    raise ValueError('evals: no assumption in this pack has been validated '
                     'against a learner, and this build cannot say otherwise')

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, indent=1, sort_keys=True) + '\n')
print('evals: %d runs (%d strategies x %d seeds, %d attempts each, %d ms) '
      'from control/sim_curriculum.mjs; %d of %d comparisons separate on '
      'every seed, %d overlap; %d assumptions quoted, 0 validated against a '
      'learner; the no-evidence limit recorded verbatim in limit.sentence. '
      'robot_readiness: %d of %d seats expose gauges, %d with a scripted '
      'reference policy, %d with an action per trace sample; no learner '
      'episode, no agent trained.'
      % (len(RUNS), len(STRATEGIES), len(SEEDS), PARAMS['attempts'],
         need(SIM, 'elapsed_ms', 'the driver output'), _disjoint,
         len(METRICS) * len(PAIRS), _overlap, len(ASSUMPTIONS),
         _n_gauges, len(PER_SIM), _n_policy, _n_obs_act))
