/* robotics/arena/test.mjs - the model arena, checked. Browser-free, network-free.
 * Recompute, never re-read: every table in robotics/arena/registry/arena.json is re-run here with the harness on the
 * same seeds and policy versions and must come out byte-equal (determinism + no stale registry); the SCRIPTED rows
 * must equal robotics.json's reference benchmark seed for seed; every statistic is recomputed from the runs; every
 * policy must carry a card, and a TRAINED policy must carry the exact honest card. When a model is present, its
 * weights must match their sha256 pin, re-training must reproduce them byte for byte, and its TRAIN and TEST seeds
 * must be disjoint (a TEST seed leaking into training fails by name). */
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import * as H from './harness.mjs';

const HERE = dirname(fileURLToPath(import.meta.url)), ROOT = join(HERE, '..', '..');
let pass = 0, fail = 0;
const ok = (m, c) => { let v = false; try { v = typeof c === 'function' ? c() : c; } catch (e) { m += ' [threw: ' + e.message + ']'; }
  if (v) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m); } };
const J = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));
const sha = (s) => createHash('sha256').update(s).digest('hex');
const AR = J('robotics/arena/registry/arena.json'), reg = J('robotics/registry/robotics.json');
const MODELS_PATH = join(HERE, 'registry/models.json'), HAS_MODELS = true;   // batch B: the model registry is required (fail closed)
let A;
try { A = H.loadArena(); } catch (e) {   // a refused model registry (no card, broken pin) fails by name, not as a crash
  console.log('FAIL  the arena loads its policy block, env core and pinned model registry [' + e.message + ']');
  console.log('robotics/arena/test: 0 passed, 1 failed'); process.exit(1);
}
const rk = Object.values(reg.envs).filter((e) => e.runner === 'robokit'), others = Object.values(reg.envs).filter((e) => e.runner !== 'robokit');
const LLM = /\b(language model|LLM|GPT|transformer|chatbot)\b/i;

/* ---- provenance ---- */
ok('the registry was built from the current arena source (stamp over build.py, harness.mjs, policies.js' + (HAS_MODELS ? ', train.mjs)' : ')'),
  AR.source_stamp === sha(Buffer.concat(['build.py', 'harness.mjs', 'policies.js'].concat(HAS_MODELS ? ['train.mjs'] : []).map((f) => readFileSync(join(HERE, f))))).slice(0, 16));
ok('schema tc-arena/1 from harness tc-arena/1', AR.schema === 'tc-arena/1' && H.HARNESS === 'tc-arena/1'
  && Object.values(AR.tables).every((t) => t.harness === 'tc-arena/1'));

/* ---- determinism: re-run every table, byte-equal ---- */
const rerun = {}, EMPTY = { runs: [], summary: {}, policy_versions: {}, seeds: [], tasks: [], results_sha256: '' };
for (const [name, t] of Object.entries(AR.tables)) {   // a harness that throws fails the named checks below instead of the whole suite
  try { rerun[name] = H.runArena(A, { policies: t.policies, seeds: t.seed_list }); } catch (e) { console.log('  (re-run of ' + name + ' threw: ' + e.message + ')'); rerun[name] = EMPTY; } }
ok('determinism: the same seeds and policy versions give byte-equal results twice in one process (all_seeds)',
  () => JSON.stringify(H.runArena(A, { policies: AR.tables.all_seeds.policies, seeds: 'all' })) === JSON.stringify(rerun.all_seeds));
for (const [name, t] of Object.entries(AR.tables)) {
  const r = rerun[name];
  ok(`determinism: table ${name} re-runs byte-equal to the registry (runs, summary, policy versions, results_sha256 ${t.results_sha256.slice(0, 12)})`,
    JSON.stringify([r.runs, r.summary, r.policy_versions, r.seeds, r.tasks]) === JSON.stringify([t.runs, t.summary, t.policy_versions, t.seeds, t.tasks])
    && r.results_sha256 === t.results_sha256);
  ok(`results_sha256 of ${name} is the sha256 of [policy versions, seeds, tasks, runs, summary]`,
    sha(JSON.stringify([t.policy_versions, t.seeds, t.tasks, t.runs, t.summary])) === t.results_sha256);
}
ok('the policy block and the env core carry no unseeded random source or clock (loader refuses them)',
  !/Math\.random|Date\.now|performance\.now/.test(A.block) && !/Math\.random/.test(A.core));
ok('the random baseline is seeded per run: same (env, level, seed) gives the same actions, another seed does not', () => {
  const e = rk[0], emb = reg.embodiments[e.embodiments[0]], seq = (s) => { const act = A.Policies.make('random', { RoboCore: A.RoboCore, env: e, seed: s, level: 1 });
    const st = A.RoboCore.reset(e, emb, s, 1); return JSON.stringify([0, 1, 2, 3, 4].map(() => act(st))); };
  return seq(3) === seq(3) && seq(3) !== seq(4); });
ok('wall time stays out of the registry and out of results_sha256 (harness --timing only)', () => {
  const t = H.runArena(A, { policies: ['greedy'], seeds: [1], timing: true }), u = H.runArena(A, { policies: ['greedy'], seeds: [1] });
  return t.timing && t.timing.greedy.runs === 13 && t.results_sha256 === u.results_sha256 && !JSON.stringify(AR).includes('ms_per_run'); });

/* ---- coverage: every registry env is run or excluded by name ---- */
const T0 = AR.tables.all_seeds;
ok('tasks = every robokit env x every declared curriculum level (4 envs, 13 env-levels), in the registry and in a fresh run',
  [T0.tasks, rerun.all_seeds.tasks].every((ts) => JSON.stringify(ts.map((t) => [t.env, t.level])) === JSON.stringify(rk.flatMap((e) => e.curriculum.levels.map((l) => [e.id, l.level]))))
  && T0.tasks.length === 13 && AR.counts.tasks === 13);
ok('every other env (the 11 sim-seat envs) is listed as excluded with a reason; run + excluded = the registry\'s 15',
  JSON.stringify(T0.excluded.map((x) => x.env)) === JSON.stringify(others.map((e) => e.id)) && T0.excluded.every((x) => x.reason.length > 40)
  && others.length === 11 && rk.length + T0.excluded.length === reg.counts.envs && AR.counts.excluded_envs === 11);
ok('all_seeds runs every declared seed; one run per (policy, task, seed), none missing, none twice',
  JSON.stringify(T0.seeds) === JSON.stringify(rk[0].seeds) && Object.values(AR.tables).every((t) =>
    new Set(t.runs.map((r) => r.slice(0, 4).join('|'))).size === t.runs.length && t.runs.length === t.policies.length * t.tasks.length * t.seeds.length));
ok('the columns are success, steps, path length, collisions and return; values are in range',
  JSON.stringify(T0.columns) === JSON.stringify(['policy', 'env', 'level', 'seed', 'success', 'steps', 'path_m', 'collisions', 'return'])
  && Object.values(AR.tables).every((t) => t.runs.every((r) => (r[4] === 0 || r[4] === 1) && r[5] > 0 && r[5] <= 600 && r[6] >= 0
    && r[6] <= reg.embodiments[reg.envs[r[1]].embodiments[0]].limits.v_max_ms * r[5] * 0.1 + 1e-6 + 0.2 * r[5] * 0.1 && Number.isInteger(r[7]) && r[7] >= 0)));
ok('SCRIPTED rows equal robotics.json reference_benchmark seed for seed (success, steps, return) - same core, same seeds', () => {
  const RB = reg.reference_benchmark.per_env;
  return T0.runs.filter((r) => r[0] === 'scripted').every((r) => { const b = RB[r[1]].levels[String(r[2])].by_seed.find((x) => x[0] === r[3]);
    return b && b[1] === r[4] && b[3] === r[5] && Math.abs(b[4] - r[8]) < 0.006; }) && T0.runs.filter((r) => r[0] === 'scripted').length === 260; });

/* ---- statistics, recomputed ---- */
const mean = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length, r4 = (x) => Math.round(x * 10000) / 10000;
for (const [name, t] of Object.entries(AR.tables)) {
  ok(`${name}: per-policy means are recomputed from the runs, and every 95% CI brackets its mean`, t.policies.every((p) => {
    const R = t.runs.filter((r) => r[0] === p), s = t.summary[p];
    return s.n === R.length && [['success_rate', 4], ['steps', 5], ['path_m', 6], ['collisions', 7], ['return', 8]].every(([k, i]) =>
      s[k].mean === r4(mean(R.map((r) => r[i]))) && s[k].ci95[0] <= s[k].mean + 1e-9 && s[k].mean <= s[k].ci95[1] + 1e-9); }));
  ok(`${name}: paired win rates against the SCRIPTED reference recount (wins + ties + losses = n; the reference ties itself)`, t.policies.every((p) => {
    const w = t.summary[p].win_vs_ref; return w.wins + w.ties + w.losses === t.summary[p].n && w.rate === r4((w.wins + 0.5 * w.ties) / t.summary[p].n); })
    && t.summary.scripted.win_vs_ref.ties === t.summary.scripted.n);
}
ok('the bootstrap is the declared one (2000 seeded resamples, 95% percentile) and reproduces', () => JSON.stringify(T0.bootstrap) === JSON.stringify(H.BOOT)
  && H.BOOT.resamples === 2000 && JSON.stringify(H.bootstrap(T0.runs.filter((r) => r[0] === 'greedy').map((r) => r[4]), A.Policies)) === JSON.stringify(T0.summary.greedy.success_rate.ci95));
ok('the leaderboard ranks its table\'s rows by success rate, then mean return, numbers copied not typed', () => {
  const t = AR.tables[AR.leaderboard.table], rows = AR.leaderboard.rows;
  return rows.length === t.policies.length && rows.every((b, i) => b.rank === i + 1 && JSON.stringify(b.success_rate) === JSON.stringify(t.summary[b.policy].success_rate)
    && JSON.stringify(b.win_vs_ref) === JSON.stringify(t.summary[b.policy].win_vs_ref))
    && rows.every((b, i) => !i || rows[i - 1].success_rate.mean > b.success_rate.mean || (rows[i - 1].success_rate.mean === b.success_rate.mean && rows[i - 1].return.mean >= b.return.mean)); });
ok('the random floor stays below the reference (measured, not assumed): random success < scripted success in every table',
  Object.values(AR.tables).every((t) => t.summary.random.success_rate.mean < t.summary.scripted.success_rate.mean));

/* ---- cards: what each policy IS ---- */
const allPolicies = [...new Set(Object.values(AR.tables).flatMap((t) => t.policies))];
ok('every policy compared carries a card (id, name, kind, what, learned, model, not), in the registry and in the policy block',
  allPolicies.every((p) => { const c = AR.cards[p], b = A.Policies.CARDS[p], has = (x, k) => x[k] !== undefined && x[k] !== null && x[k] !== '';
    return c && b && ['id', 'name', 'kind', 'what', 'learned', 'model', 'not'].every((k) => has(c, k) && (has(b, k) || (A.Policies.MODEL_POLICIES.includes(p) && k === 'what'))) && c.id === p && b.id === p; })
  && Object.keys(AR.cards).length === allPolicies.length && AR.counts.policies === allPolicies.length);
ok('a policy without a card is refused by the policy block and the harness', () => {
  let a = false, b = false; try { A.Policies.make('uncarded', {}); } catch (e) { a = /no card/.test(e.message); }
  try { H.runArena(A, { policies: ['uncarded'], seeds: [1] }); } catch (e) { b = /no card/.test(e.message); } return a && b; });
ok('kinds are SCRIPTED / BASELINE / TRAINED; learned is true exactly for TRAINED; exactly one SCRIPTED reference',
  Object.values(AR.cards).every((c) => ['SCRIPTED', 'BASELINE', 'TRAINED'].includes(c.kind) && (c.kind === 'TRAINED') === (c.learned === true))
  && Object.values(AR.cards).filter((c) => c.reference).length === 1 && AR.cards.scripted.reference === true);
ok('no card, honesty line or table claims a language model (only "not a language model" may name one)',
  !LLM.test(JSON.stringify([AR.cards, AR.honesty]).replace(/not a language model/g, '').replace(/No policy here is a language model/g, '')));
ok('trained_models counts the TRAINED models of the model registry, and every TRAINED card names its N SCRIPTED episodes exactly', () => {
  const trained = AR.models.filter((m) => m.provenance === 'TRAINED');
  return AR.counts.trained_models === trained.length && Object.values(AR.cards).filter((c) => c.kind === 'TRAINED').length === trained.length
    && trained.every((m) => new RegExp(`^a small behaviour-cloning policy( with a class-weighted grip head)? trained on ${m.train.episodes} SCRIPTED episodes; not a language model; not trained on any learner's data$`).test(m.card.what)
      && AR.cards[m.policy] && AR.cards[m.policy].what === m.card.what)
    && AR.honesty.trained.startsWith(`${trained.length} models trained here: `) && trained.every((m) => AR.honesty.trained.includes(m.card.what)); });

/* ---- the interface the orchestration layer imports ---- */
ok('interface: policies(reg), tasks(reg), runEpisode(reg, {policy, env, level, seed}) exist and agree with the tables', () => {
  const P = H.policies(reg), T = H.tasks(reg), e = H.runEpisode(reg, { policy: 'greedy', env: 'world.gate-drive', level: 2, seed: 5 });
  const row = T0.runs.find((r) => r[0] === 'greedy' && r[1] === 'world.gate-drive' && r[2] === 2 && r[3] === 5);
  return P.every((p) => p.version === (AR.tables.held_out || T0).policy_versions[p.id] || p.version === T0.policy_versions[p.id]) && T.length === 4
    && e.kind === 'world-teleop' && e.level === 2 && e.actor === 'arena-greedy' && e.steps === row[5] && (e.outcome.success ? 1 : 0) === row[4]
    && Math.abs(e.outcome.return - row[8]) < 0.006; });

/* ---- the trained model (batch B) ---- */
{
  const M = JSON.parse(readFileSync(MODELS_PATH, 'utf8'));
  const TR = await import('./train.mjs');
  ok('model registry: every model has a card, and its weights match their sha256 pin', M.models.length > 0 && M.models.every((m) =>
    m.card && m.card.what && sha(JSON.stringify(m.weights)) === m.weights_sha256));
  ok('the arena registry carries the model registry\'s cards and pins, not copies that drifted', JSON.stringify(AR.models) === JSON.stringify(M.models.map((m) =>
    Object.fromEntries(['id', 'policy', 'provenance', 'weights_sha256', 'split', 'train', 'card'].map((k) => [k, m[k]])))));
  for (const m of M.models) {
    ok(`${m.id}: held-out split - no TEST seed is a TRAIN seed, together they are the declared seeds`, () =>
      m.split.train.every((s) => !m.split.test.includes(s)) && JSON.stringify([...m.split.train, ...m.split.test].sort((a, b) => a - b)) === JSON.stringify(rk[0].seeds));
    ok(`${m.id}: every training episode came from a TRAIN seed (${m.train.episodes} = 13 tasks x ${m.split.train.length} seeds)`, () =>
      m.train.episode_list.every((e) => m.split.train.includes(e[2]) && !m.split.test.includes(e[2])) && m.train.episodes === 13 * m.split.train.length
      && m.train.episode_list.length === m.train.episodes);
    ok(`${m.id}: the trainer's split is the registry's split, and the trainer refuses a TEST seed`, () => {
      let refused = false; try { TR.dataset(reg, A.RoboCore, A.Policies, [m.split.test[0]], m.split.test); } catch (e) { refused = /TEST split/.test(e.message); }
      return JSON.stringify(TR.MODEL_SPECS[m.policy].split) === JSON.stringify(m.split) && refused; });
    ok(`${m.id}: re-training in this process reproduces the pinned weights byte for byte (sha256 ${m.weights_sha256.slice(0, 12)})`, () => {
      const r = TR.modelRecord(reg, A.RoboCore, A.Policies, TR.MODEL_SPECS[m.policy]); return r.weights_sha256 === m.weights_sha256 && JSON.stringify(r.train) === JSON.stringify(m.train); });
  }
  const HO = AR.tables.held_out;
  ok('the held-out table compares every policy, both BC models included, on the TEST seeds only', HO && JSON.stringify(HO.seeds) === JSON.stringify(M.models[0].split.test)
    && HO.policies.includes('bc') && HO.policies.includes('bcg') && AR.leaderboard.table === 'held_out'
    && M.models.every((m) => JSON.stringify(m.split.test) === JSON.stringify(HO.seeds)));
  ok('robotics.json counts the trained model and says what it is (trained_models = the model registry\'s TRAINED count)', () => {
    const n = M.models.filter((m) => m.provenance === 'TRAINED').length;
    return reg.counts.trained_models === n && n === 2 && M.models.length === 2 && /^NOTHING HAS BEEN TRAINED ON ANY LEARNER'S DATA/.test(reg.honesty.trained)
      && M.models.every((m) => reg.honesty.trained.includes(m.card.what)) && !/records no training run/.test(reg.honesty.trained); });
  for (const p of HO.policies) console.log(`  (measured) held-out seeds ${HO.seeds[0]}-${HO.seeds[HO.seeds.length - 1]} ${p}: success ${HO.summary[p].success_rate.mean} [${HO.summary[p].success_rate.ci95}], win vs ref ${HO.summary[p].win_vs_ref.rate} [${HO.summary[p].win_vs_ref.ci95}]`);
}

/* ---- the second carded policy (v3.7 exit criterion 5): held-out interval, grip timing, honesty ---- */
{
  const M = JSON.parse(readFileSync(MODELS_PATH, 'utf8')), TR = await import('./train.mjs'), HO = AR.tables.held_out;
  const second = M.models.find((m) => m.policy === 'bcg'), first = M.models.find((m) => m.policy === 'bc');
  ok('a second TRAINED policy (bcg) is carded in the model registry beside the first, with its own pinned weights and its own id', second && first && second.provenance === 'TRAINED'
    && second.id !== first.id && second.weights_sha256 !== first.weights_sha256 && new Set(M.models.map((m) => m.id)).size === M.models.length && AR.cards.bcg.kind === 'TRAINED');
  ok('the second policy has a held-out interval on seeds 11 to 20 in the arena registry: a success rate and a win rate vs the reference, each with a 95% interval that brackets its mean', () => {
    const s = HO.summary.bcg, w = s.win_vs_ref;
    return JSON.stringify(HO.seeds) === JSON.stringify([11, 12, 13, 14, 15, 16, 17, 18, 19, 20]) && s.n === 130
      && s.success_rate.ci95.length === 2 && s.success_rate.ci95[0] <= s.success_rate.mean && s.success_rate.mean <= s.success_rate.ci95[1]
      && w.ci95[0] <= w.rate && w.rate <= w.ci95[1] && AR.leaderboard.rows.some((b) => b.policy === 'bcg' && JSON.stringify(b.success_rate) === JSON.stringify(s.success_rate)); });
  ok('the second card says what data, what seeds, and what it is NOT (SCRIPTED episodes only, TRAIN seeds 1-10, TEST seeds 11-20 held out, no language model, no learner data), and how it addresses grip timing', () => {
    const c = second.card;
    return /SCRIPTED reference episodes/.test(c.data) && /TRAIN seeds 1-10/.test(c.data) && /TEST seeds 11-20 are held out/.test(c.data)
      && /not a language model; not trained on any learner's data$/.test(c.what) && /grip timing/.test(c.addresses) && /each class weighted/.test(c.optimiser)
      && /TRAIN seeds only/.test(c.selection) && /were not run while choosing/.test(c.selection) && /SCRIPTED potential-field teacher/.test(c.limits)
      && /reach circle/.test(c.inputs) && c.parameters === 26 * 32 + 32 + 32 * 4 + 4; });
  ok('the grip head is trained as classification with class weights: the record carries the close-now / other counts and the class-weighted loss, and the loss fell', () =>
    second.train.grip_positives > 0 && second.train.grip_negatives > second.train.grip_positives && second.train.grip_loss_last < second.train.grip_loss_first
    && !('grip_positives' in first.train));
  ok('the first model is untouched by the second (24-16-4, 24 features, squared error, 24 epochs): its pinned weights still re-train byte for byte', () =>
    first.card.parameters === 468 && first.train.epochs === 24 && TR.MODEL_SPECS.bc === TR.TRAIN && !TR.TRAIN.features && !TR.TRAIN.grip_loss
    && TR.modelRecord(reg, A.RoboCore, A.Policies, TR.MODEL_SPECS.bc).weights_sha256 === first.weights_sha256);
  /* grip timing: the extra features expose the signed gap to the reach circle; the 26 begin with the first 24 */
  ok('bcg features: the first 24 equal the first model\'s features, the last two are the signed gap to the reach circle (0 at the circle, + outside, - inside) and are 0 on tasks with no gripper', () => {
    const e = reg.envs['world.litter-sort'], emb = reg.embodiments[e.embodiments[0]], P = A.Policies, st = A.RoboCore.reset(e, emb, 11, 1), it = st.items[0];
    st.items.forEach((x) => { x.taken = x.id !== it.id; });
    const at = (gap) => { it.e = st.e; it.n = st.n + emb.radius_m + emb.limits.reach_m + gap; return P.featuresG(A.RoboCore, st); };
    const f0 = at(0), base = P.features(A.RoboCore, st), fo = at(0.05), fi = at(-0.05), rov = reg.envs['world.rov-survey'], sr = A.RoboCore.reset(rov, reg.embodiments[rov.embodiments[0]], 11, 1);
    return f0.length === 26 && P.FG === 26 && base.every((v, i) => f0[i] === v) && Math.abs(f0[24]) < 1e-9 && Math.abs(f0[25]) < 1e-9
      && fo[24] > 0 && fo[25] > 0 && fi[24] < 0 && fi[25] < 0 && Math.abs(fo[25]) > Math.abs(fo[24]) && P.featuresG(A.RoboCore, sr).slice(24).every((v) => v === 0); });
  ok('bcg decides from its weights alone: no call to the SCRIPTED policy in its actor, wrong-size weights are refused, and changing a weight changes its actions', () => {
    const blk = A.block, i = blk.indexOf("if (id === 'bcg')"), j = blk.indexOf('throw new Error', i + 10), actor = blk.slice(i, j);
    let refused = false; try { A.Policies.make('bcg', { RoboCore: A.RoboCore, model: H.decodeWeights(first.weights) }); } catch (e) { refused = /pinned weights/.test(e.message); }
    const e = reg.envs['world.litter-sort'], emb = reg.embodiments[e.embodiments[0]], W = H.decodeWeights(second.weights), W2 = { ...W, W2: W.W2.map((v, k) => (k % 7 === 0 ? v + 0.5 : v)) };
    const act = (w) => { const f = A.Policies.make('bcg', { RoboCore: A.RoboCore, env: e, seed: 11, level: 1, model: w }), st = A.RoboCore.reset(e, emb, 11, 1); return JSON.stringify([0, 1, 2].map(() => { const a = f(st); A.RoboCore.step(st, a); return a; })); };
    return i > 0 && actor.length > 100 && !/\.policy\s*\(/.test(actor) && !/RC\.policy/.test(actor) && refused && act(W) !== act(W2) && act(W) === act(W); });
  ok('items binned in litter sort are recounted from the sort rows for every policy in every table (the number criterion 5 reads), and the rows are one per policy x litter-sort level x seed', () =>
    Object.values(AR.tables).every((t) => t.policies.every((p) => { const R = t.sort.rows.filter((r) => r[0] === p), S = t.sort.summary[p];
      return R.length === 4 * t.seeds.length && S.items_binned === R.reduce((a, r) => a + r[4], 0) && S.items_total === R.reduce((a, r) => a + r[5], 0)
        && S.episodes_with_any === R.filter((r) => r[4] > 0).length && S.binned_per_episode.mean === r4(mean(R.map((r) => r[4])))
        && S.binned_per_episode.ci95[0] <= S.binned_per_episode.mean && S.binned_per_episode.mean <= S.binned_per_episode.ci95[1]; })
      && t.sort_sha256 === sha(JSON.stringify([t.results_sha256, t.sort])) && JSON.stringify(rerun[Object.keys(AR.tables).find((n) => AR.tables[n] === t)].sort) === JSON.stringify(t.sort)));
  ok('the sort rows agree with the runs: a run that binned every item is a success, and a success always binned every item', () =>
    HO.sort.rows.every((r) => { const run = HO.runs.find((q) => q[0] === r[0] && q[1] === r[1] && q[2] === r[2] && q[3] === r[3]); return (r[4] === r[5]) === (run[4] === 1); }));
  ok('learned_vs_reference copies the held-out numbers (scripted reference and every TRAINED policy), whatever they are; bins_something is items_binned > 0 and nothing else', () => {
    const L = AR.learned_vs_reference, trainedIds = M.models.map((m) => m.policy);
    return L.table === 'held_out' && JSON.stringify(L.seeds) === JSON.stringify(HO.seeds) && JSON.stringify(L.rows.map((r) => r.policy)) === JSON.stringify(['scripted', ...trainedIds])
      && L.rows.every((r) => r.items_binned === HO.sort.summary[r.policy].items_binned && r.items_total === HO.sort.summary[r.policy].items_total
        && JSON.stringify(r.binned_per_episode) === JSON.stringify(HO.sort.summary[r.policy].binned_per_episode)
        && JSON.stringify(r.success_rate) === JSON.stringify(HO.summary[r.policy].success_rate) && r.bins_something === (r.items_binned > 0)); });
  ok('the arena\'s honesty lines still say no language model is trained, and the count they state is the models registry\'s', () =>
    /No policy here is a language model, and none calls one/.test(AR.honesty.not_llm) && /No learner data is read/.test(AR.honesty.data) && /SCRIPTED reference episodes/.test(AR.honesty.data)
    && AR.honesty.trained.startsWith(M.models.length + ' models trained here') && AR.counts.trained_models === M.models.length);
  const L = AR.learned_vs_reference.rows;
  for (const r of L) console.log(`  (measured) litter sort, held-out seeds 11-20, items binned ${r.policy}: ${r.items_binned} of ${r.items_total}, per episode ${r.binned_per_episode.mean} [${r.binned_per_episode.ci95}], episodes with any ${r.episodes_with_any}/${r.episodes}, bins something: ${r.bins_something}`);
}
for (const p of T0.policies) console.log(`  (measured) all seeds ${p}: success ${T0.summary[p].success_rate.mean} [${T0.summary[p].success_rate.ci95}], return ${T0.summary[p].return.mean}, collisions ${T0.summary[p].collisions.mean}, win vs ref ${T0.summary[p].win_vs_ref.rate}`);
console.log(`robotics/arena/test: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
