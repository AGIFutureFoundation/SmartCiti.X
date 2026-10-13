/* robotics/claw/node.mjs - the node shell of the Omega Claw core: reads the registries from the repo, loads the page
 * simulator's SIM_CORE through robotics/bench.mjs (the very code the pages run), node's sha256, and the datashare
 * core for learner packages. No network. `node robotics/claw/node.mjs --index` prints the dataset index JSON that
 * robotics/claw/build.py stores in robotics/claw/registry/claw.json. Nothing here trains a model. */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { loadCore, policyVersion } from '../bench.mjs';
import { trainOpsCore } from './core.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
export const ROOT = join(HERE, '..', '..');
const cache = new Map();
export const load = (rel) => { if (!cache.has(rel)) cache.set(rel, JSON.parse(readFileSync(join(ROOT, rel), 'utf8'))); return cache.get(rel); };
export const sha256 = (s) => createHash('sha256').update(Buffer.from(s, 'utf8')).digest('hex');
export const C = trainOpsCore({ load, sha256 });
export const AUTH = load('robotics/claw/authored/claw.json');
export const REG = load('robotics/registry/robotics.json');
export const DS_CFG = load('datashare/registry/datashare.json');
const TR = load('training/registry/training.json');
export const T = { kind: TR.world_episode_kinds['world-teleop'], world_teleop: TR.world_teleop };
const { core, RoboCore } = loadCore();
export { RoboCore };
export const POLICY_VERSION = policyVersion(core);

export function scripted() {
  if (POLICY_VERSION !== REG.reference_benchmark.policy_version) throw new Error('claw: SIM_CORE policy version ' + POLICY_VERSION + ' is not the registry benchmark version ' + REG.reference_benchmark.policy_version + ' (rebuild robotics/ first)');
  return C.buildScripted({ reg: REG, RoboCore, T, policyVersion: POLICY_VERSION, authored: AUTH, regStamp: REG.source_stamp });
}

/* learner packages -> admitted human samples, through the datashare intake rules (consent scope + revocations) */
export async function learner(packages, revocations) {
  const { CORE, verdictOf } = await import('../../datashare/node_shell.mjs');
  const pk = packages.map((p) => ({ name: p.name, record: p.record, verdict: verdictOf(p.record) }));
  return C.mergeLearner({ ds: CORE, packages: pk, revocations, built_at: '2026-01-01T00:00:00Z', reg: REG, RoboCore, T, authored: AUTH, scope: 'robot-training' });
}

export function assemble(samples, learnerCount) {
  const ds = C.finalize(samples, AUTH);
  const per = Object.values(ds.per_task);
  const idx = { episodes: samples.length, learner: learnerCount, policy_version: POLICY_VERSION, splits_def: Object.fromEntries(Object.entries(AUTH.splits).map(([k, v]) => [k, { train: v.train, val: v.val, test: v.test }])),
    balance_ratio: Math.round(Math.max(...per) / Math.min(...per) * 1000) / 1000, balance_max: AUTH.balance.max_ratio,
    repo_trained_models: REG.counts.trained_models };
  idx.digest = sha256(C.canonical(ds.samples.map((s) => [s.id, s.traj_hash, s.split, s.weight]))).slice(0, 16);
  const { card, ids } = C.renderCard(ds, idx, DS_CFG.card.template);
  return { ds, idx, card, cardIds: ids };
}

/* the SCRIPTED reference at each env's recordable level (curriculum.record_levels[0]) per seed: what a learner's
   recorded episode is measured against (path length, time to success) */
export function referencePaths() {
  const out = {};
  for (const env of Object.values(REG.envs).filter((e) => e.runner === 'robokit')) {
    const level = env.curriculum.record_levels[0], emb = REG.embodiments[env.embodiments[0]];
    out[env.id] = { level, rows: env.seeds.map((seed) => { const r = C.refSummary(env, RoboCore.rollout(env, emb, seed, T, 'lab', level));
      return [seed, r.path_m, r.time_s, +r.success]; }),
      columns: ['seed', 'path_m', 'time_s (-1 = no success)', 'success'] };
  }
  return out;
}

export function indexOf(ds, idx) {
  const rows = ds.samples.map((s) => ({ id: s.id, task: s.task, family: s.family, level: s.level, seed: s.seed, actor: s.actor, instruction_source: s.instruction.source,
    traj_hash: s.traj_hash, split: s.split, weight: s.weight, success: s.referee.success, steps: s.n_steps, samples: s.steps.length }));
  const count = (f) => { const o = {}; for (const s of ds.samples) { const k = f(s); o[k] = (o[k] || 0) + 1; } return o; };
  return { ...idx, samples: ds.samples.length, duplicates: ds.duplicates, per_task: ds.per_task, per_family: count((s) => s.family),
    success: ds.samples.filter((s) => s.referee.success).length,
    splits: Object.fromEntries(Object.keys(AUTH.splits).map((k) => [k, count((s) => s.split[k])])),
    instructions: [...new Set(ds.samples.map((s) => s.instruction.source))].sort(), rows };
}

if (process.argv[1] === fileURLToPath(import.meta.url) && process.argv.includes('--index')) {
  const { ds, idx, card } = assemble(scripted(), 0);
  const rev = load('datashare/revocations.json');
  const fails = C.validate(ds.samples, AUTH, rev, card, DS_CFG.card.template.map((s) => s.id));
  if (fails.length) { for (const f of fails.slice(0, 20)) console.error('FAIL ' + f.check + ': ' + f.detail); process.exit(1); }
  process.stdout.write(JSON.stringify({ index: indexOf(ds, idx), card, reference_paths: referencePaths() }) + '\n');
}
