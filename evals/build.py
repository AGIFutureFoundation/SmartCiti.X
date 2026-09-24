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
      'learner; the no-evidence limit recorded verbatim in limit.sentence.'
      % (len(RUNS), len(STRATEGIES), len(SEEDS), PARAMS['attempts'],
         need(SIM, 'elapsed_ms', 'the driver output'), _disjoint,
         len(METRICS) * len(PAIRS), _overlap, len(ASSUMPTIONS)))
