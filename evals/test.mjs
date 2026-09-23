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

console.log(`\n${pass} ok, ${fail} failed`);
console.log(`evals: ${pass} checks passed - ${RUNS.length} simulation runs `
  + `reproduced exactly from ${SEEDS.length} recorded seeds, every spread and `
  + `separation recomputed, and the source's own "produces no evidence that `
  + `the beliefs are true" limit still quoted verbatim.`);
process.exit(fail ? 1 : 0);
