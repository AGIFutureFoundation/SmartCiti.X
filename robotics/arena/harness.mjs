/* robotics/arena/harness.mjs - the model-comparison harness (tc-arena/1). Runs several POLICIES on identical seeded
 * tasks: every robokit world task x every declared curriculum level x a seed list, on the SIM_CORE block of
 * web/robokit.py (the code the pages run) and the policy block robotics/arena/policies.js (the code the arena page
 * runs). Records per run: success, steps, path length, collisions, return (and wall time only on request, outside the
 * deterministic results). Reports per policy: means, a seeded bootstrap 95% CI, and paired win rates against the
 * SCRIPTED reference on the same (task, level, seed).
 * Deterministic: the same seed list and policy versions give byte-equal `runs`, `summary` and `results_sha256`.
 * The 11 sim-seat envs of the registry are listed in `excluded` with the reason: their runner is the 3D page's
 * operator layer, which has no headless core to drive.
 * Usage: node robotics/arena/harness.mjs [--policies scripted,random,greedy,bc] [--seeds all|train|test|1,2,3] [--timing] */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url)), ROOT = join(HERE, '..', '..');
export const HARNESS = 'tc-arena/1';
export const BOOT = { resamples: 2000, seed: 20261012, level: 0.95 };
const sha = (s) => createHash('sha256').update(s).digest('hex');
const r2 = (x) => Math.round(x * 100) / 100, r3 = (x) => Math.round(x * 1000) / 1000, r4 = (x) => Math.round(x * 10000) / 10000;

export function loadPolicies(root = ROOT) {
  const src = readFileSync(join(root, 'robotics/arena/policies.js'), 'utf8');
  const a = src.indexOf('/* MODEL_ARENA_POLICIES:BEGIN'), b = src.indexOf('/* MODEL_ARENA_POLICIES:END */');
  if (a < 0 || b < a) throw new Error('arena: the policy block markers are missing');
  const block = src.slice(a, b);
  if (/Math\.random|Date\.now|performance\.now/.test(block)) throw new Error('arena: the policy block is not deterministic');
  return { block, Policies: new Function(block + '\nreturn ArenaPolicies;')() };
}
export function loadCore(root = ROOT) {
  const kit = readFileSync(join(root, 'web/robokit.py'), 'utf8');
  const core = kit.slice(kit.indexOf('/* SIM_CORE:BEGIN'), kit.indexOf('/* SIM_CORE:END */'));
  if (core.length < 3000 || /Math\.random/.test(core)) throw new Error('arena: robokit core missing or not deterministic');
  return { core, RoboCore: new Function(core + '\nreturn RoboCore;')() };
}
/* the model registry: weights are refused unless their sha256 matches the pin stored beside them */
export function loadModels(root = ROOT) {
  const M = JSON.parse(readFileSync(join(root, 'robotics/arena/registry/models.json'), 'utf8'));
  for (const m of M.models) {
    if (!m.card || !m.card.what) throw new Error('arena: model ' + m.id + ' has no card');
    if (sha(JSON.stringify(m.weights)) !== m.weights_sha256) throw new Error('arena: model ' + m.id + ' weights do not match their sha256 pin');
  }
  return M;
}
export function loadArena(root = ROOT) {
  const reg = JSON.parse(readFileSync(join(root, 'robotics/registry/robotics.json'), 'utf8'));
  const { core, RoboCore } = loadCore(root), { block, Policies } = loadPolicies(root);
  let models = null; try { models = loadModels(root); } catch (e) { if (!/ENOENT/.test(String(e))) throw e; }
  return { reg, core, RoboCore, block, Policies, models };
}
/* policy version = sha256[:16] of what decides its actions: the policy block (+ SIM_CORE for scripted, + weights for bc) */
export function policyVersions(A, ids) {
  const v = {};
  for (const id of ids) v[id] = sha(id + '\n' + A.block + (id === 'scripted' ? A.core : '') + (A.Policies.MODEL_POLICIES.includes(id) ? JSON.stringify(modelOf(A, id).weights) : '')).slice(0, 16);
  return v;
}
/* integer micro-units -> the float weights the policy block's forward() reads */
export function decodeWeights(w) {
  const d = (a) => a.map((x) => x / w.scale);
  return { in: w.in, hidden: w.hidden, out: w.out, W1: d(w.W1), b1: d(w.b1), W2: d(w.W2), b2: d(w.b2) };
}
function modelOf(A, id) {
  const m = A.models && A.models.models.find((x) => x.policy === id);
  if (!m) throw new Error('arena: policy ' + id + ' needs a trained model in robotics/arena/registry/models.json');
  return m;
}
const bcModel = (A) => modelOf(A, 'bc');   // the first model; its split is the split of every model (checked by the tests)
const modelFor = (A, id) => A.Policies.MODEL_POLICIES.includes(id) ? decodeWeights(modelOf(A, id).weights) : null;
export function seedList(A, which) {
  const all = Object.values(A.reg.envs).find((e) => e.runner === 'robokit').seeds;
  if (which === 'all' || which === undefined) return all.slice();
  if (which === 'train' || which === 'test') { const s = bcModel(A).split[which]; if (!s) throw new Error('arena: no ' + which + ' split'); return s.slice(); }
  if (Array.isArray(which)) return which.slice();
  throw new Error('arena: unknown seed list ' + which);
}

/* one episode of `policy` on (env, level, seed) */
export function runOne(A, policy, env, level, seed, timing) {
  const emb = A.reg.embodiments[env.embodiments[0]];
  const ctx = { RoboCore: A.RoboCore, env, seed, level, model: modelFor(A, policy) };
  const act = A.Policies.make(policy, ctx), t0 = timing ? performance.now() : 0;
  const st = A.RoboCore.reset(env, emb, seed, level);
  let path = 0;
  while (!st.done) { const e0 = st.e, n0 = st.n; A.RoboCore.step(st, act(st)); path += Math.hypot(st.e - e0, st.n - n0); }
  const cw = env.reward.find((r) => r.term === 'collision').weight;
  const row = [policy, env.id, level, seed, st.done !== 'cap' ? 1 : 0, st.step, r2(path), Math.round(st.terms.collision / cw), r3(st.ret)];
  return timing ? { row, collected: st.collected, ms: performance.now() - t0 } : { row, collected: st.collected };
}

/* seeded percentile bootstrap of the mean (deterministic: fixed resample stream) */
export function bootstrap(xs, P) {
  const n = xs.length; if (!n) return [null, null];
  const rnd = P.mulberry32(BOOT.seed ^ n), means = new Float64Array(BOOT.resamples);
  for (let b = 0; b < BOOT.resamples; b++) { let s = 0; for (let i = 0; i < n; i++) s += xs[Math.floor(rnd() * n)]; means[b] = s / n; }
  means.sort();
  const lo = means[Math.floor((1 - BOOT.level) / 2 * BOOT.resamples)], hi = means[Math.ceil((1 + BOOT.level) / 2 * BOOT.resamples) - 1];
  return [r4(lo), r4(hi)];
}
const mean = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length;

export function summarise(runs, ids, P) {
  const key = (r) => r[1] + '|' + r[2] + '|' + r[3], ref = new Map(runs.filter((r) => r[0] === 'scripted').map((r) => [key(r), r]));
  const S = {};
  for (const id of ids) {
    const R = runs.filter((r) => r[0] === id), col = (i) => R.map((r) => r[i]);
    const m = (i) => ({ mean: r4(mean(col(i))), ci95: bootstrap(col(i), P) });
    const s = { n: R.length, success_rate: m(4), steps: m(5), path_m: m(6), collisions: m(7), return: m(8) };
    if (ref.size) {   // paired against the SCRIPTED reference on the same (env, level, seed): success first, then return
      let wins = 0, ties = 0, losses = 0; const pts = [];
      for (const r of R) { const q = ref.get(key(r)); if (!q) throw new Error('arena: no reference run for ' + key(r));
        const d = r[4] - q[4] || (Math.abs(r[8] - q[8]) < 1e-9 ? 0 : Math.sign(r[8] - q[8]));
        if (d > 0) { wins++; pts.push(1); } else if (d < 0) { losses++; pts.push(0); } else { ties++; pts.push(0.5); } }
      s.win_vs_ref = { wins, ties, losses, rate: r4(mean(pts)), ci95: bootstrap(pts, P) };
    }
    S[id] = s;
  }
  return S;
}

/* items binned in the bin tasks (litter sort), per policy: the number criterion 'bins something' reads. `rows` are
 * [policy, env, level, seed, items binned, items on the field]; success (all items binned) stays the headline in `runs`. */
export function sortSummary(rows, ids, P) {
  const S = {};
  for (const id of ids) {
    const R = rows.filter((r) => r[0] === id), by = {};
    for (const r of R) { const b = by[r[2]] = by[r[2]] || { episodes: 0, binned: 0, total: 0, with_any: 0 }; b.episodes++; b.binned += r[4]; b.total += r[5]; b.with_any += r[4] > 0 ? 1 : 0; }
    S[id] = { episodes: R.length, items_binned: R.reduce((a, r) => a + r[4], 0), items_total: R.reduce((a, r) => a + r[5], 0),
      episodes_with_any: R.filter((r) => r[4] > 0).length, binned_per_episode: { mean: R.length ? r4(mean(R.map((r) => r[4]))) : null, ci95: bootstrap(R.map((r) => r[4]), P) },
      share_of_items: { mean: R.length ? r4(R.reduce((a, r) => a + r[4], 0) / R.reduce((a, r) => a + r[5], 0)) : null,
        ci95: bootstrap(R.map((r) => r[4] / r[5]), P) }, by_level: by };
  }
  return S;
}

export function runArena(A, opt = {}) {
  const ids = opt.policies || A.Policies.ORDER;
  for (const id of ids) if (!A.Policies.CARDS[id]) throw new Error('arena: policy ' + id + ' has no card');
  const seeds = seedList(A, opt.seeds), envs = Object.values(A.reg.envs).filter((e) => e.runner === 'robokit' && (!opt.envs || opt.envs.includes(e.id)));
  for (const e of envs) for (const s of seeds) if (!e.seeds.includes(s)) throw new Error('arena: seed ' + s + ' is not declared for ' + e.id);
  const tasks = [], runs = [], timing = {}, sortRows = [];
  for (const e of envs) for (const lv of e.curriculum.levels) if (!opt.levels || opt.levels.includes(lv.level)) tasks.push({ env: e.id, level: lv.level, name: lv.name });
  for (const id of ids) { let ms = 0, k = 0;
    for (const t of tasks) for (const s of seeds) { const o = runOne(A, id, A.reg.envs[t.env], t.level, s, opt.timing); runs.push(o.row); if (A.reg.envs[t.env].objects.bin) sortRows.push([id, t.env, t.level, s, o.collected, A.reg.envs[t.env].objects.litter]); if (opt.timing) { ms += o.ms; k++; } }
    if (opt.timing) timing[id] = { runs: k, ms_per_run: r2(ms / k) }; }
  const excluded = Object.values(A.reg.envs).filter((e) => e.runner !== 'robokit').map((e) => ({ env: e.id, runner: e.runner,
    reason: 'no headless runner: this seat\'s SCRIPTED operator runs inside the 3D page\'s simulator, which the harness cannot step in Node' }));
  const summary = summarise(runs, ids, A.Policies);
  const cards = Object.fromEntries(ids.map((id) => [id, A.Policies.MODEL_POLICIES.includes(id) ? { ...A.Policies.CARDS[id], ...modelOf(A, id).card } : A.Policies.CARDS[id]]));
  const out = { harness: HARNESS, policies: ids, policy_versions: policyVersions(A, ids), cards, seeds, tasks, excluded,
    bootstrap: BOOT, columns: ['policy', 'env', 'level', 'seed', 'success', 'steps', 'path_m', 'collisions', 'return'], runs, summary };
  out.results_sha256 = sha(JSON.stringify([out.policy_versions, seeds, tasks, runs, summary]));
  out.sort = { what: 'items binned in the litter-sort task (every level), per policy; derived from the same runs', columns: ['policy', 'env', 'level', 'seed', 'binned', 'items'], rows: sortRows, summary: sortSummary(sortRows, ids, A.Policies) };
  out.sort_sha256 = sha(JSON.stringify([out.results_sha256, out.sort]));
  if (opt.timing) out.timing = { what: 'wall time per run on this machine (varies by machine and load; NOT part of results_sha256)', ...timing };
  return out;
}

/* ---- the interface agreed with the orchestration layer (robotics/claw/ imports these; names are theirs) ---------- */
let CACHED = null;
const arena = (reg) => { CACHED = CACHED || loadArena(); return reg ? { ...CACHED, reg } : CACHED; };
/* every policy the arena can run now (bc only when its pinned weights are present), with version and card kind */
export function policies(reg) {
  const A = arena(reg), ids = A.Policies.ORDER.filter((id) => !A.Policies.MODEL_POLICIES.includes(id) || (A.models && A.models.models.some((m) => m.policy === id)));
  const v = policyVersions(A, ids);
  return ids.map((id) => ({ id, version: v[id], provenance: A.Policies.CARDS[id].kind, card: A.Policies.MODEL_POLICIES.includes(id) ? { ...A.Policies.CARDS[id], ...modelOf(A, id).card } : A.Policies.CARDS[id] }));
}
export function tasks(reg) {
  return Object.values(arena(reg).reg.envs).filter((e) => e.runner === 'robokit').map((e) => ({ env: e.id, levels: e.curriculum.levels.map((l) => l.level), seeds: e.seeds.slice() }));
}
/* one deterministic episode as RoboCore.episode shapes it (world-teleop) plus a top-level level; actor names the policy */
export function runEpisode(reg, { policy, env, level, seed }) {
  const A = arena(reg), E = A.reg.envs[env];
  if (!E || E.runner !== 'robokit') throw new Error('arena: ' + env + ' is not a robokit env');
  const tr = JSON.parse(readFileSync(join(ROOT, 'training/registry/training.json'), 'utf8'));
  const T = { kind: tr.world_episode_kinds['world-teleop'], world_teleop: tr.world_teleop };
  const emb = A.reg.embodiments[E.embodiments[0]];
  const act = A.Policies.make(policy, { RoboCore: A.RoboCore, env: E, seed, level, model: modelFor(A, policy) });
  const st = A.RoboCore.reset(E, emb, seed, level), every = Math.round(1 / (T.world_teleop.sample_hz * E.episode_cap.dt_s)), samples = [];
  while (!st.done) { const a = act(st); if (st.step % every === 0 && samples.length < T.world_teleop.max_samples) samples.push(A.RoboCore.sample(st, a)); A.RoboCore.step(st, a); }
  return { ...A.RoboCore.episode(st, policy === 'scripted' ? 'scripted-reference' : 'arena-' + policy, 'lab', samples, T), level };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const arg = (k) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : undefined; };
  const sv = arg('--seeds');
  const A = loadArena();
  const out = runArena(A, { policies: arg('--policies') ? arg('--policies').split(',') : undefined,
    seeds: sv && /^[0-9,]+$/.test(sv) ? sv.split(',').map(Number) : sv, timing: process.argv.includes('--timing') });
  process.stdout.write(JSON.stringify(out) + '\n');
}
