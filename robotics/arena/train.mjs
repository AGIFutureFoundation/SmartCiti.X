/* robotics/arena/train.mjs - TRAIN the one small behaviour-cloning (BC) policy of the model arena, in Node, at build
 * time, by plain minibatch gradient descent (no momentum, no Adam, no library). Data: the SCRIPTED reference policy
 * of web/robokit.py (SIM_CORE) rolled out on every robokit world task x every declared level x the TRAIN seeds only;
 * each control step gives one (features, action) pair. The TEST seeds are never rolled out here, so the arena's
 * held-out table measures BC on layouts it never saw. Model: an MLP 24-16-4 with softsign hidden units and linear
 * outputs (v, w, grip, vz; masked where a task has no such field), seeded init and seeded shuffles, so the same code
 * gives the same weights byte for byte; they are stored quantised (integer micro-units) and sha256-pinned in
 * robotics/arena/registry/models.json. Not a language model; not trained on any learner's data.
 * Usage: node robotics/arena/train.mjs [--write]   (prints the model record; --write stores models.json) */
import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { loadCore, loadPolicies } from './harness.mjs';

const HERE = dirname(fileURLToPath(import.meta.url)), ROOT = join(HERE, '..', '..');
export const TRAIN = {
  split: { train: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], test: [11, 12, 13, 14, 15, 16, 17, 18, 19, 20] },
  hidden: 16, out: 4, epochs: 24, batch: 64, lr: 0.05, init_seed: 20261012, shuffle_seed: 1018, scale: 1000000,
};

/* the training set: SCRIPTED reference episodes on the TRAIN seeds (refuses any seed of the TEST split) */
export function dataset(reg, RC, P, seeds, test) {
  const X = [], Y = [], Mk = [], episodes = [];
  for (const s of seeds) if (test.includes(s)) throw new Error('train: seed ' + s + ' belongs to the TEST split');
  for (const env of Object.values(reg.envs).filter((e) => e.runner === 'robokit')) {
    const emb = reg.embodiments[env.embodiments[0]];
    for (const lv of env.curriculum.levels) for (const s of seeds) {
      const st = RC.reset(env, emb, s, lv.level);
      while (!st.done) { const x = P.features(RC, st), a = RC.policy(st), t = P.target(st, a); X.push(x); Y.push(t.y); Mk.push(t.m); RC.step(st, a); }
      episodes.push([env.id, lv.level, s, st.step, st.done !== 'cap' ? 1 : 0]);
    }
  }
  return { X, Y, M: Mk, episodes };
}

export function train(reg, RC, P, T = TRAIN) {
  const D = dataset(reg, RC, P, T.split.train, T.split.test), F = P.F, H = T.hidden, O = T.out, N = D.X.length;
  const rnd = P.mulberry32(T.init_seed), u = (a) => (rnd() * 2 - 1) * a;
  const W1 = Float64Array.from({ length: H * F }, () => u(1 / Math.sqrt(F))), b1 = new Float64Array(H);
  const W2 = Float64Array.from({ length: O * H }, () => u(1 / Math.sqrt(H))), b2 = new Float64Array(O);
  const sh = P.mulberry32(T.shuffle_seed), idx = Array.from({ length: N }, (_, i) => i);
  const z = new Float64Array(H), h = new Float64Array(H), gy = new Float64Array(O), gh = new Float64Array(H);
  const gW1 = new Float64Array(H * F), gb1 = new Float64Array(H), gW2 = new Float64Array(O * H), gb2 = new Float64Array(O);
  const losses = [];
  for (let ep = 0; ep < T.epochs; ep++) {
    for (let i = N - 1; i > 0; i--) { const j = Math.floor(sh() * (i + 1)); const t = idx[i]; idx[i] = idx[j]; idx[j] = t; }
    let L = 0, cnt = 0;
    for (let s0 = 0; s0 < N; s0 += T.batch) {
      const B = Math.min(T.batch, N - s0); gW1.fill(0); gb1.fill(0); gW2.fill(0); gb2.fill(0);
      for (let q = s0; q < s0 + B; q++) {
        const x = D.X[idx[q]], y = D.Y[idx[q]], m = D.M[idx[q]];
        for (let j = 0; j < H; j++) { let a = b1[j]; for (let i = 0; i < F; i++) a += W1[j * F + i] * x[i]; z[j] = a; h[j] = a / (1 + Math.abs(a)); }
        for (let k = 0; k < O; k++) { let a = b2[k]; for (let j = 0; j < H; j++) a += W2[k * H + j] * h[j]; const e = (a - y[k]) * m[k]; L += e * e; cnt += m[k]; gy[k] = 2 * e / B; }
        gh.fill(0);
        for (let k = 0; k < O; k++) { gb2[k] += gy[k]; for (let j = 0; j < H; j++) { gW2[k * H + j] += gy[k] * h[j]; gh[j] += gy[k] * W2[k * H + j]; } }
        for (let j = 0; j < H; j++) { const d = 1 + Math.abs(z[j]), g = gh[j] / (d * d); gb1[j] += g; for (let i = 0; i < F; i++) gW1[j * F + i] += g * x[i]; }
      }
      for (let i = 0; i < W1.length; i++) W1[i] -= T.lr * gW1[i];
      for (let i = 0; i < H; i++) b1[i] -= T.lr * gb1[i];
      for (let i = 0; i < W2.length; i++) W2[i] -= T.lr * gW2[i];
      for (let i = 0; i < O; i++) b2[i] -= T.lr * gb2[i];
    }
    losses.push(Math.round(L / cnt * 1e6) / 1e6);
  }
  const q = (a) => Array.from(a, (x) => Math.round(x * T.scale));
  const weights = { in: F, hidden: H, out: O, act: 'softsign', scale: T.scale, W1: q(W1), b1: q(b1), W2: q(W2), b2: q(b2) };
  return { weights, episodes: D.episodes, samples: N, losses };
}
export function modelRecord(reg, RC, P, T = TRAIN) {
  const r = train(reg, RC, P, T), N = r.episodes.length;
  const weights_sha256 = createHash('sha256').update(JSON.stringify(r.weights)).digest('hex');
  return {
    id: 'bc.mlp-24-16-4', policy: 'bc', provenance: 'TRAINED',
    card: {
      what: `a small behaviour-cloning policy trained on ${N} SCRIPTED episodes; not a language model; not trained on any learner's data`,
      architecture: `MLP ${P.F}-${T.hidden}-${T.out}, softsign hidden units, linear outputs (v, w, grip, vz; masked per task)`,
      parameters: P.F * T.hidden + T.hidden + T.hidden * T.out + T.out,
      trained_by: 'robotics/arena/train.mjs, in Node at build time',
      optimiser: `plain minibatch gradient descent: learning rate ${T.lr}, batch ${T.batch}, ${T.epochs} epochs, no momentum, no Adam`,
      data: `${N} SCRIPTED reference episodes (${r.samples} control steps) on the TRAIN seeds ${T.split.train[0]}-${T.split.train[T.split.train.length - 1]}; the TEST seeds ${T.split.test[0]}-${T.split.test[T.split.test.length - 1]} are held out`,
      inputs: `${P.F} egocentric features: goal bearing and distance, two nearest obstacles and the nearest wall (bearing, clearance), contact, gripper, depth error, v, w, task one-hot`,
      determinism: `seeded init (${T.init_seed}) and shuffles (${T.shuffle_seed}); weights stored as integer micro-units and sha256-pinned`,
    },
    split: T.split,
    train: { episodes: N, samples: r.samples, epochs: T.epochs, batch: T.batch, lr: T.lr, init_seed: T.init_seed,
      shuffle_seed: T.shuffle_seed, loss_first: r.losses[0], loss_last: r.losses[r.losses.length - 1], episode_list: r.episodes },
    weights: r.weights, weights_sha256,
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const reg = JSON.parse(readFileSync(join(ROOT, 'robotics/registry/robotics.json'), 'utf8'));
  const { RoboCore } = loadCore(), { Policies } = loadPolicies();
  const m = modelRecord(reg, RoboCore, Policies);
  if (process.argv.includes('--write')) writeFileSync(join(HERE, 'registry/models.json'),
    JSON.stringify({ schema: 'tc-arena-models/1', what: 'model registry of the arena: weights sha256-pinned; each model carries its card', models: [m] }, null, 1) + '\n');
  process.stdout.write(JSON.stringify({ id: m.id, weights_sha256: m.weights_sha256, train: { ...m.train, episode_list: m.train.episode_list.length } }) + '\n');
}
