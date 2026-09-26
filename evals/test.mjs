/* evals/test.mjs — the curriculum simulation's published results, checked.
 *
 * Three jobs, in the order of what would hurt most if it broke:
 *
 *   1. THE LIMIT. control/sim_curriculum.mjs says in its own header that it
 *      "produces no evidence that the beliefs are true". That sentence is
 *      the difference between a measurement and a claim about learners, and
 *      it is the first thing a growth-minded edit would soften. Two checks
 *      hold it: one re-extracts it from the source and demands the registry
 *      match character for character, one demands the strong wording itself
 *      still be there. Both look at ONE named field, limit.sentence, never
 *      at this pack's prose — a check that scanned sentences would fire on
 *      the pack's own honest explanations.
 *   2. REPRODUCTION. Every one of the recorded runs is re-run here from its
 *      recorded seed and compared field by field. A result that cannot be
 *      reproduced is not a result, so this suite does not read the numbers
 *      back — it makes them again.
 *   3. THE SPREAD. Every min, max, median, mean, range and separation
 *      verdict is recomputed from the per-seed rows. Where the strategies'
 *      intervals overlap the registry has to SAY overlap; a check here
 *      fails if an overlap is ever reported as a separation.
 *
 * Browser-free and network-free. It imports the real simulation, which
 * touches no clock and no network of its own.
 */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { run, runAll } from '../control/sim_curriculum.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok ' + m); }
                       else { fail++; console.log('  FAIL ' + m); } };
const J = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));

/* Fail CLOSED. A missing field is a broken registry, not a default. */
const at = (obj, path) => path.split('.').reduce((o, k) => {
  if (o === null || typeof o !== 'object' || !(k in o)) {
    throw new Error(`evals/test.mjs: evals.json is missing ${path} (stopped at "${k}")`);
  }
  return o[k];
}, obj);

const E = J('evals/registry/evals.json');
const SRC_PATH = join(ROOT, 'control/sim_curriculum.mjs');
const SRC = readFileSync(SRC_PATH, 'utf8');

console.log('evals/test.mjs');

/* ---- the header, re-extracted here by a second implementation ------ */
const headerMatch = SRC.match(/\/\*\*([\s\S]*?)\*\//);
if (!headerMatch) {
  throw new Error('evals/test.mjs: control/sim_curriculum.mjs no longer opens '
    + 'with a /** */ header; the limit and the assumptions are quoted from it');
}
const headerLines = headerMatch[1].split('\n').map((l) => l.replace(/^\s*\*\s?/, ''));
const headerFlat = headerLines.map((l) => l.trim()).join(' ').replace(/\s+/g, ' ').trim();

const srcLimit = (() => {
  const m = headerFlat.match(/(LEARNER MODEL ASSUMPTIONS[\s\S]*?):\s*A1\b/);
  if (!m) {
    throw new Error('evals/test.mjs: the assumptions heading and its A1 list '
      + 'are gone from the header of control/sim_curriculum.mjs — the pack '
      + 'quotes that passage and will not guess at it');
  }
  return `${m[1]}:`;
})();

const srcAssumptions = (() => {
  const out = {};
  let cur = null;
  for (const ln of headerLines) {
    const m = ln.match(/^\s{2,}A(\d)\s+(.*\S)\s*$/);
    if (m) { cur = `A${m[1]}`; out[cur] = m[2]; continue; }
    if (cur && /^\s{5,}\S/.test(ln)) { out[cur] += ` ${ln.trim()}`; continue; }
    if (cur && !ln.trim()) cur = null;
  }
  return out;
})();

/* ---- 1. THE LIMIT -------------------------------------------------- */
{
  const recorded = at(E, 'limit.sentence');
  ok(recorded === srcLimit,
     'limit.sentence is character-for-character what the header of '
     + 'control/sim_curriculum.mjs says — re-extracted here, not read back, '
     + 'so the quotation cannot drift away from the source');
  ok(recorded.includes('produces no evidence that the beliefs are true'),
     'and it still carries the strong wording verbatim: the simulation '
     + '"produces no evidence that the beliefs are true". This is the '
     + 'sentence that separates a measurement from a claim about learners, '
     + 'and softening it fails this suite');
  ok(at(E, 'limit.quoted_verbatim') === true
     && at(E, 'limit.quoted_from').startsWith('control/sim_curriculum.mjs'),
     'the limit is recorded as a verbatim quotation and names the file it '
     + 'was quoted from, rather than being this pack\'s paraphrase of it');
}

/* ---- the assumptions, verbatim ------------------------------------- */
{
  const items = at(E, 'assumptions.items');
  const ids = Object.keys(items).sort();
  ok(ids.length >= 3 && ids.every((k) => /^A\d+$/.test(k)
       && typeof items[k].text === 'string' && items[k].text.length > 20
       && items[k].id === k),
     `${ids.length} learner-model assumptions are recorded, each under the `
     + 'kind of id the source gives them and each with text on it');
  ok(ids.every((k) => items[k].text === srcAssumptions[k]),
     'and each one\'s text is what the source states, re-extracted here — a '
     + 'paraphrase of a pedagogical belief is a different belief');
  ok(ids.join(',') === Object.keys(srcAssumptions).sort().join(','),
     'and the set is exactly the set the source states — an assumption '
     + 'added to the learner model and not recorded here would be an '
     + 'unlisted belief, which is the thing this pack exists to prevent');
  ok(ids.every((k) => items[k].validated_against_learners === false)
     && at(E, 'counts.assumptions_validated_against_learners') === 0,
     'every assumption carries validated_against_learners false and the '
     + 'count agrees — this pack tests none of them and cannot say it did');
  ok(at(E, 'counts.assumptions_recorded') === ids.length,
     'the assumption count is the assumptions, counted');
}

/* ---- 2. REPRODUCTION ----------------------------------------------- */
const SEEDS = at(E, 'seeds');
const STRATS = at(E, 'strategies');
const METRICS = at(E, 'metrics');
const RUNS = at(E, 'runs');
{
  ok(Array.isArray(SEEDS) && SEEDS.length >= 3 && new Set(SEEDS).size === SEEDS.length,
     `${SEEDS.length} distinct seeds are recorded — one seed is an anecdote, `
     + 'and a seed that is not written down cannot be re-run');
  ok(RUNS.length === SEEDS.length * STRATS.length
     && at(E, 'counts.runs') === RUNS.length,
     `${RUNS.length} runs: every strategy against every seed, none missing`);

  let mismatches = 0, firstBad = null;
  for (const rec of RUNS) {
    const fresh = run(rec.strategy, rec.seed);
    for (const m of METRICS) {
      if (fresh[m] !== rec[m]) {
        mismatches++;
        if (!firstBad) firstBad = `${rec.strategy} seed ${rec.seed}: ${m} `
          + `recorded ${rec[m]}, re-ran to ${fresh[m]}`;
      }
    }
  }
  ok(mismatches === 0,
     `all ${RUNS.length} runs reproduce exactly from their recorded seeds `
     + `(${RUNS.length * METRICS.length} values re-made, not read back)`
     + (firstBad ? ` — first mismatch: ${firstBad}` : ''));
  ok(RUNS.every((r) => SEEDS.includes(r.seed) && STRATS.includes(r.strategy)),
     'every run names a seed and a strategy the registry declares');

  const freshAll = runAll(SEEDS);
  const means = at(E, 'runall_means');
  ok(freshAll.length === STRATS.length
     && freshAll.every((row) => METRICS.every(
       (m) => at(means, `${row.strategy}.${m}`) === row[m])),
     'runAll(seeds) — the subject\'s own summary entry point — reproduces '
     + 'the recorded means too, so the published table is the one its CLI '
     + 'would print for these seeds');
}

/* ---- the subject this was run against ------------------------------ */
{
  ok(createHash('sha256').update(readFileSync(SRC_PATH)).digest('hex')
     === at(E, 'subject.sha256'),
     'the registry records the digest of the simulation it was run against, '
     + 'and it is the file on disk now — edit the simulation and this run is '
     + 'stale, loudly');
  const cf = SRC.match(/const ATTEMPTS = (\d+), PER_DAY = (\d+), SESSION_LEN = (\d+);/);
  const cr = SRC.match(/const RETENTION_PROBE_DAYS = (\d+);/);
  if (!cf || !cr) throw new Error('evals/test.mjs: the run constants could not '
    + 'be read out of control/sim_curriculum.mjs');
  ok(at(E, 'subject.parameters.attempts') === Number(cf[1])
     && at(E, 'subject.parameters.per_day') === Number(cf[2])
     && at(E, 'subject.parameters.session_len') === Number(cf[3])
     && at(E, 'subject.parameters.retention_probe_days') === Number(cr[1]),
     `the run parameters are the subject's own (${cf[1]} attempts, ${cf[2]} a `
     + `day, sessions of ${cf[3]}, a ${cr[1]}-day retention probe), re-read `
     + 'from the source here — nothing was shrunk to make the sweep quick');
  ok(at(E, 'counts.total_attempts_simulated')
     === at(E, 'subject.parameters.attempts') * RUNS.length,
     'the total attempts figure is the per-run attempts times the runs');
  const skills = J('pack/registry/skills.json').skills
    .filter((s) => s.union === at(E, 'subject.union'));
  ok(skills.length === at(E, 'subject.skills_in_union') && skills.length > 0,
     `the ladder is recounted from pack/registry/skills.json: ${skills.length} `
     + `skills in the ${at(E, 'subject.union')} union`);
  ok(at(E, 'subject.skill_ladder_tier') === 'AUTHORED',
     'and the ladder those runs walk is recorded as AUTHORED — the input to '
     + 'this simulation is hand-built, so nothing RECORDED is upstream of '
     + 'any number here');
}

/* ---- 3. THE SPREAD, recomputed ------------------------------------- */
const median = (xs) => {
  const s = [...xs].sort((a, b) => a - b);
  return s.length % 2 ? s[(s.length - 1) / 2]
    : (s[s.length / 2 - 1] + s[s.length / 2]) / 2;
};
const r4 = (x) => Math.round(x * 1e4) / 1e4;
{
  const SPREAD = at(E, 'spread');
  let bad = 0, firstBad = null;
  for (const k of STRATS) {
    for (const m of METRICS) {
      const vals = RUNS.filter((r) => r.strategy === k).map((r) => r[m]);
      const s = at(SPREAD, `${k}.${m}`);
      const want = {
        min: r4(Math.min(...vals)), max: r4(Math.max(...vals)),
        median: r4(median(vals)),
        mean: r4(Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 100) / 100),
        range: r4(Math.max(...vals) - Math.min(...vals)),
      };
      for (const f of Object.keys(want)) {
        if (s[f] !== want[f]) {
          bad++;
          if (!firstBad) firstBad = `${k}.${m}.${f}: says ${s[f]}, recomputes to ${want[f]}`;
        }
      }
      if (Object.keys(s.per_seed).sort().join(',')
          !== SEEDS.map(String).sort().join(',')) {
        bad++;
        if (!firstBad) firstBad = `${k}.${m}.per_seed does not cover the recorded seeds`;
      }
    }
  }
  ok(bad === 0,
     `every min, max, median, mean and range is recomputed here from the `
     + `per-seed rows (${STRATS.length * METRICS.length} spreads)`
     + (firstBad ? ` — first mismatch: ${firstBad}` : ''));
  ok(STRATS.every((k) => METRICS.every((m) => {
       const s = at(SPREAD, `${k}.${m}`);
       return ['min', 'max', 'median', 'mean', 'range', 'per_seed']
         .every((f) => f in s);
     })),
     'not one mean is published without its spread: every metric carries '
     + 'min, max, median, range and the per-seed values beside it');
  ok(STRATS.every((k) => METRICS.every((m) => {
       const s = at(SPREAD, `${k}.${m}`);
       return s.identical_across_every_seed === (s.min === s.max);
     })),
     'and each says whether it moved across seeds at all, so a constant is '
     + 'visible as a constant rather than as a suspiciously tidy mean');
}

/* ---- separation: an overlap must be reported as an overlap --------- */
{
  const SEP = at(E, 'separation');
  const PAIRS = [['graph', 'blocked'], ['graph', 'flat'], ['blocked', 'flat']];
  let bad = 0, firstBad = null, disjoint = 0, overlap = 0;
  for (const m of METRICS) {
    for (const [a, b] of PAIRS) {
      const A = RUNS.filter((r) => r.strategy === a).map((r) => r[m]);
      const B = RUNS.filter((r) => r.strategy === b).map((r) => r[m]);
      const [aMin, aMax] = [Math.min(...A), Math.max(...A)];
      const [bMin, bMax] = [Math.min(...B), Math.max(...B)];
      const sep = aMin > bMax || bMin > aMax;
      const higher = sep ? (aMin > bMax ? a : b) : null;
      const rec = at(SEP, `${m}.${a}_vs_${b}`);
      if (rec.separates_across_every_seed !== sep || rec.overlap !== !sep
          || rec.higher !== higher) {
        bad++;
        if (!firstBad) firstBad = `${m} ${a}_vs_${b}: says `
          + `${rec.overlap ? 'overlap' : 'separates'}/higher=${rec.higher}, `
          + `recomputes to ${sep ? 'separates' : 'overlap'}/higher=${higher}`;
      }
      if (sep) disjoint++; else overlap++;
    }
  }
  ok(bad === 0,
     `all ${METRICS.length * PAIRS.length} strategy-pair comparisons are `
     + 'recomputed here from the per-seed intervals'
     + (firstBad ? ` — first mismatch: ${firstBad}` : ''));
  ok(at(E, 'counts.comparisons_separating_on_every_seed') === disjoint
     && at(E, 'counts.comparisons_overlapping') === overlap
     && disjoint + overlap === METRICS.length * PAIRS.length,
     `${disjoint} comparisons separate on every seed and ${overlap} overlap; `
     + 'both counts are the comparisons, counted, and they partition them');
  ok(overlap > 0,
     'at least one comparison overlaps and is published as an overlap — the '
     + 'registry reports the intervals it got, not a clean sweep');
}

/* ---- the findings the registry must not quietly drop --------------- */
{
  const gated = (k) => RUNS.filter((r) => r.strategy === k)
    .map((r) => r.skillsGated);
  ok(Math.min(...gated('graph')) > Math.max(...gated('blocked'))
     && Math.max(...gated('blocked')) === 0 && Math.max(...gated('flat')) === 0
     && at(E, 'separation.skillsGated.graph_vs_blocked.higher') === 'graph',
     'graph is the only strategy that gets any skill through the skill gate '
     + 'on any seed, and the registry\'s own separation field says so');
  const learned = (k) => RUNS.filter((r) => r.strategy === k)
    .map((r) => r.skillsLearned);
  ok(Math.min(...learned('blocked')) > Math.max(...learned('graph'))
     && at(E, 'separation.skillsLearned.graph_vs_blocked.higher') === 'blocked'
     && at(E, 'separation.totalAbilityGained.graph_vs_blocked.higher') === 'blocked',
     'and blocked practice learns MORE skills and gains more raw ability '
     + 'than graph on every seed — the half of the result that a headline '
     + 'would drop is in the registry as a field, not only in its prose');
  const empty = at(E, 'retention_empty_denominator_runs');
  ok(STRATS.every((k) => empty[k] === RUNS.filter(
       (r) => r.strategy === k && r.skillsLearned === 0).length),
     'the runs whose retention figure rests on an empty set are counted per '
     + 'strategy, recomputed here — a retentionAt30d of 0 there means '
     + 'nothing was learned, not that everything decayed');
}

/* ---- tier discipline ------------------------------------------------ */
{
  const tiers = at(J('auth/registry/auth.json'), 'provenance_tiers');
  ok(at(E, 'provenance.tier') === 'SCRIPTED' && tiers.includes('SCRIPTED'),
     'the pack tier is SCRIPTED — a hand-written deterministic policy over '
     + 'an authored learner model — and it is a member of the bundle\'s own '
     + 'closed tier set, read live from auth/registry/auth.json');
  ok(at(E, 'provenance.tiers_available').join(',') === tiers.join(','),
     'and the tier set this pack reasons about is that file\'s, not a '
     + 'second copy of it that could drift');
  const bad = [];
  (function walk(o, path) {
    if (Array.isArray(o)) { o.forEach((v, i) => walk(v, `${path}[${i}]`)); return; }
    if (o && typeof o === 'object') {
      for (const [k, v] of Object.entries(o)) {
        if (typeof v === 'string' && /^(tier|provenance)$/.test(k)
            && v !== 'SCRIPTED') bad.push(`${path}.${k} = ${v}`);
        walk(v, `${path}.${k}`);
      }
    }
  }(E, '$'));
  ok(bad.length === 0,
     'no field in the registry that names a tier claims anything but '
     + 'SCRIPTED' + (bad.length ? ` — found ${bad.join('; ')}` : '')
     + ' — nothing here was observed of a learner, so nothing here is '
     + 'RECORDED');
  ok(!JSON.stringify(E).includes('AI-SYNTHESIZED'),
     'the reserved provenance word does not appear — it belongs to orbis/');
}

/* ---- stamp, version, and the prose agreeing with the arithmetic ---- */
{
  ok(createHash('sha256').update(readFileSync(join(HERE, 'build.py')))
     .digest('hex').slice(0, 16) === at(E, 'source_stamp'),
     'the registry was built from the current builder (stamp check)');
  ok(at(E, 'pack') === 'evals'
     && at(E, 'pack_version') === J('pack/manifest.json').pack_version,
     'the registry names its own pack and one bundle version, read from the '
     + 'manifest rather than typed');
  const h = at(E, 'honesty');
  ok(h.the_spread_is_the_result.includes(
       String(at(E, 'counts.comparisons_separating_on_every_seed')))
     && h.the_spread_is_the_result.includes(
       String(at(E, 'counts.comparisons_overlapping'))),
     'the spread note quotes the comparison counts this build produced, so '
     + 'the sentence cannot drift away from the table under it');
  ok(h.the_retention_interval_that_overlaps.includes(
       String(at(E, 'retention_empty_denominator_runs.flat'))),
     'and the retention caveat quotes the empty-denominator count rather '
     + 'than describing it loosely');
  ok(h.determinism.includes(String(RUNS.length))
     && h.determinism.includes(String(SEEDS.length)),
     'and the determinism note quotes the seeds and runs actually made');
}

/* ---------------------- does the simulation know which hall it is in? ---- */
/* The registry's answer is no, and that answer is only worth anything if it
   is REMADE here rather than read back. So this re-runs the sweep: the same
   strategy and the same seeds in every hall the skills registry declares,
   grouping identical outcomes, and holds the registry to what comes out.

   This is also the guard on the finding going stale in the direction that
   would matter most. If somebody wires the simulation to the simulator
   registry - which would be an improvement - the sweep starts returning more
   than one outcome per seed, and this fails rather than leaving a published
   claim that the halls are indistinguishable. The finding would then have to
   be rewritten, which is the point. */
{
  const hi = at(E, 'hall_independence');
  const halls = [...new Set(J('pack/registry/skills.json').skills.map((r) => r.union))].sort();
  const seeds = at(hi, 'seeds');
  const kind = at(hi, 'strategy');

  const groups = {};
  for (const sd of seeds) {
    const seen = new Map();
    for (const h of halls) {
      const j = JSON.stringify(run(kind, sd, { union: h }));
      if (!seen.has(j)) seen.set(j, []);
      seen.get(j).push(h);
    }
    groups[String(sd)] = seen;
  }

  ok(at(hi, 'halls_swept') === halls.length && halls.length > 0,
     `the sweep covers every hall the skills registry declares (${halls.length})`);
  ok(seeds.every((sd) => at(hi, 'distinct_outcomes_per_seed')[String(sd)]
       === groups[String(sd)].size),
     'the distinct-outcome count per seed is reproduced here by re-running the '
     + 'sweep, not read back out of the registry');
  ok(seeds.every((sd) => groups[String(sd)].size === 1),
     'and it is ONE outcome per seed: the same strategy and seed return the '
     + 'same result in all 111 halls, so this simulation does not know which '
     + 'hall it is in');

  /* The named contrast. A statistic that says "indistinguishable" is easy to
     skim past; two named halls with their seat counts beside identical
     numbers is not. Both halves are re-derived - the seat counts from the
     sims registry that owns the bindings, the outcomes by running them. */
  const c = at(hi, 'contrast');
  const bind = J('sims/registry/sims.json').hall_bindings;
  const rich = at(c, 'richest'), poor = at(c, 'poorest');
  ok((bind[at(rich, 'hall')] || []).length === at(rich, 'seats')
     && at(rich, 'seats') === Math.max(...Object.values(bind).map((v) => v.length)),
     `the hall named as richest (${at(rich, 'hall')}) really does carry the most `
     + `simulator seats in the registry (${at(rich, 'seats')})`);
  ok(!(at(poor, 'hall') in bind) && at(poor, 'seats') === 0
     && halls.includes(at(poor, 'hall')),
     `the hall named as having none (${at(poor, 'hall')}) really is a declared hall `
     + 'with no seat bound to it at all');
  /* Compared as VALUES with keys sorted, not as serialisations: the registry
     is written with sorted keys and run() returns them in declaration order,
     so a raw string compare fails on key order alone and says nothing about
     whether the two halls differ. */
  const norm = (o) => JSON.stringify(Object.fromEntries(
    Object.entries(o).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))));
  const ro = norm(run(kind, at(c, 'seed'), { union: at(rich, 'hall') }));
  const po = norm(run(kind, at(c, 'seed'), { union: at(poor, 'hall') }));
  ok(ro === po && at(c, 'identical') === true
     && ro === norm(at(rich, 'outcome'))
     && po === norm(at(poor, 'outcome')),
     `re-run here, ${at(rich, 'hall')} with ${at(rich, 'seats')} seats and `
     + `${at(poor, 'hall')} with none return byte-identical outcomes, and both match `
     + 'what the registry recorded');

  /* And the sentence that stops the number being sold as something it is
     not. One named field, never this pack's prose. */
  const hon = at(hi, 'honest');
  ok(hon.length > 140 && /curriculum shape/i.test(hon)
     && /not a per-trade training outcome|must not be sold/i.test(hon),
     'the finding carries, in one named field, the thing a buyer needs: this '
     + 'measures a curriculum shape and is not a per-trade training outcome');
}

/* ------------------- is "course completion" verifiable? ------------------ */
/* Recomputed from lessons.json here - the classification, the rollups, the
   ladder walk - and held to what the registry says. Structure, not prose. */
{
  const ce = at(E, 'completion_evidence');
  const L = J('lessons/registry/lessons.json');
  const S = J('sims/registry/sims.json');
  const C = J('unions/registry/campuses.json');
  const U = J('unions/registry/unions.json');
  const sha = (p) => createHash('sha256').update(readFileSync(join(ROOT, p))).digest('hex');

  const stampsOk = [['lessons', L], ['sims', S], ['campuses', C], ['unions', U]].every(
    ([k, reg]) => at(ce, `inputs.${k}.source_stamp`) === at(reg, 'source_stamp')
      && at(ce, `inputs.${k}.sha256`) === sha(at(ce, `inputs.${k}.path`)));
  ok(stampsOk && at(ce, 'inputs.halls.sha256') === sha('pack/registry/halls.json'),
     'completion_evidence exists and every input stamp and sha256 matches the '
     + 'registry it was read from (lessons, sims, campuses, unions, halls)');

  const kinds = at(L, 'step_kinds');
  const recKinds = Object.keys(kinds).filter((k) => at(kinds[k], 'records') !== null).sort();
  ok(recKinds.join(',') === at(ce, 'recording_kinds').join(','),
     `the recording kinds are the ones step_kinds[k].records names (${recKinds.join(', ')})`);

  const lessons = at(L, 'lessons');
  const mine = {};
  for (const id of Object.keys(lessons).sort()) {
    const steps = at(lessons[id], 'steps');
    const rec = steps.filter((s) => recKinds.includes(at(s, 'kind'))).length;
    const sil = steps.length - rec;
    mine[id] = { steps: steps.length, rec, sil,
                 cls: sil === 0 && rec > 0 ? 'full' : rec > 0 ? 'partial' : 'none' };
  }
  const pl = at(ce, 'per_lesson');
  ok(Object.keys(pl).sort().join(',') === Object.keys(mine).join(',')
     && Object.keys(mine).every((id) => at(pl[id], 'steps') === mine[id].steps
        && at(pl[id], 'evidence_backed_steps') === mine[id].rec
        && at(pl[id], 'self_reported_steps') === mine[id].sil
        && at(pl[id], 'classification') === mine[id].cls
        && at(pl[id], 'can_be_evidence_backed') === (mine[id].rec >= 1)
        && at(pl[id], 'fully_evidence_backed') === (mine[id].cls === 'full')),
     'every lesson\'s step counts and classification are recomputed here from '
     + 'lessons.json and equal the registry\'s');
  ok(Object.keys(mine).every((id) => mine[id].rec > 0 || at(pl[id], 'classification') === 'none'),
     'a lesson with zero recording steps is classed not-verifiable');

  const r = at(ce, 'rollup');
  const n = (c) => Object.values(mine).filter((v) => v.cls === c).length;
  ok(at(r, 'fully_verifiable') === n('full') && at(r, 'partly_verifiable') === n('partial')
     && at(r, 'not_verifiable') === n('none')
     && at(r, 'fully_verifiable') + at(r, 'partly_verifiable') + at(r, 'not_verifiable') === 32
     && at(r, 'lessons') === 32 && at(L, 'counts.lessons') === 32,
     `the three classes are recomputed and sum to 32 lessons (${n('full')} full, `
     + `${n('partial')} partial, ${n('none')} none)`);
  const hallsAll = J('pack/registry/halls.json').halls.map((h) => at(h, 'slug'));
  const hallsWith = new Set(Object.values(lessons).map((l) => at(l, 'hall')));
  ok(at(r, 'halls_with_a_lesson') === hallsWith.size
     && at(r, 'halls_with_no_lesson') === hallsAll.length - hallsWith.size
     && at(r, 'halls_with_a_lesson') + at(r, 'halls_with_no_lesson') === 111
     && at(r, 'halls_with_no_lesson_list').length === at(r, 'halls_with_no_lesson')
     && at(r, 'halls_with_no_lesson_list').every((h) => hallsAll.includes(h) && !hallsWith.has(h)),
     `halls with a lesson (${hallsWith.size}) plus halls with none sum to 111, and the `
     + 'no-lesson list is exactly the declared halls no lesson names');
  ok(at(r, 'evidence_backed_steps') === at(L, 'counts.recording_steps')
     && at(r, 'self_reported_steps') === at(L, 'counts.silent_steps')
     && at(r, 'steps') === at(L, 'counts.steps'),
     'the step rollups equal the lessons registry\'s own recording/silent counts');

  const pu = at(ce, 'per_union');
  const unionSlugs = at(U, 'unions').map((u) => at(u, 'slug'));
  ok(Object.keys(pu).every((u) => unionSlugs.includes(u))
     && Object.values(pu).reduce((a, v) => a + at(v, 'verifiable'), 0)
        === Object.values(mine).filter((v) => v.rec > 0).length
     && Object.keys(pu).length === at(ce, 'unions_with_a_lesson')
     && at(ce, 'unions_total') === unionSlugs.length,
     'per-union verifiable counts name real union slugs and sum to the verifiable lessons');

  const st = at(ce, 'sim_thresholds');
  const simsRun = new Set(Object.values(lessons).flatMap((l) => at(l, 'steps')
    .filter((s) => at(s, 'kind') === 'sim').map((s) => at(s, 'sim'))));
  const declared = [...simsRun].filter((id) => at(S, `sims.${id}.rubric`)
    .some((a) => at(a, 'pass') !== 'informational')).length;
  ok(at(st, 'sims_run_by_a_sim_step') === simsRun.size && at(st, 'thresholds_declared') === declared
     && at(st, 're_derivable') === (declared === simsRun.size),
     `every sim a sim step runs is checked for a rubric pass rule in sims.json `
     + `(${declared} of ${simsRun.size} declare one)`);

  const edges = at(L, 'ladder.edges');
  const needs = {};
  for (const e of edges) (needs[at(e, 'lesson')] ||= []).push(at(e, 'needs'));
  const colour = {};
  let cyc = 0;
  const visit = (nd, path) => {
    if (colour[nd] === 1) { cyc++; return; }
    if (colour[nd] === 2) return;
    colour[nd] = 1;
    for (const m of needs[nd] || []) visit(m, path.concat(nd));
    colour[nd] = 2;
  };
  for (const id of Object.keys(mine)) visit(id, []);
  const badPre = [...new Set(Object.values(needs).flat())].filter((p) => mine[p].rec === 0).sort();
  ok(cyc === 0 && at(ce, 'ladder.acyclic') === true && at(ce, 'ladder.lessons_on_a_cycle') === 0
     && at(ce, 'ladder.edges') === edges.length
     && at(ce, 'ladder.prerequisites_not_verifiable').join(',') === badPre.join(','),
     `the ladder is walked here: ${edges.length} edges, no cycle, and the `
     + 'prerequisites that are themselves not verifiable match the registry\'s');
  const hon = at(ce, 'honest');
  ok(/DECLARE/.test(hon) && /no episode has been recorded/i.test(hon)
     && /NO course to complete/.test(at(r, 'halls_with_no_lesson_means')),
     'the block says in named fields that it measures declarations, not a '
     + 'learner, and that a hall with no lesson has no course to complete');
}

console.log(`\n${pass} ok, ${fail} failed`);
console.log(`evals: ${pass} checks passed - ${RUNS.length} simulation runs `
  + `reproduced exactly from ${SEEDS.length} recorded seeds, every spread and `
  + `separation recomputed, and the source's own "produces no evidence that `
  + `the beliefs are true" limit still quoted verbatim.`);
console.log(`evals/test: ${pass} checks passed`);
process.exit(fail ? 1 : 0);
