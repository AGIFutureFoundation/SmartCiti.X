/* robotics/arena/train.mjs - TRAIN the one small behaviour-cloning (BC) policy of the model arena, in Node, at build
 * time, by plain minibatch gradient descent (no momentum, no Adam, no library). Data: the SCRIPTED reference policy
 * of web/robokit.py (SIM_CORE) rolled out on every robokit world task x every declared level x the TRAIN seeds only;
 * each control step gives one (features, action) pair. The TEST seeds are never rolled out here, so the arena's
 * held-out table measures BC on layouts it never saw. Model: an MLP 24-16-4 with softsign hidden units and linear
 * outputs (v, w, grip, vz; masked where a task has no such field), seeded init and seeded shuffles, so the same code
 * gives the same weights byte for byte; they are stored quantised (integer micro-units) and sha256-pinned in
 * robotics/arena/registry/models.json. Not a language model; not trained on any learner's data.
 * Two models: bc (the first, 24 features, squared error) and bcg (the second: 26 features that expose the gap to the
 * gripper's reach, a class-weighted hinge grip head, 32 hidden units, 60 epochs); see MODEL_SPECS.
 * Usage: node robotics/arena/train.mjs [--write]   (prints the model records; --write stores models.json) */
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
export function dataset(reg, RC, P, seeds, test, feat = P.features) {
  const X = [], Y = [], Mk = [], episodes = [];
  for (const s of seeds) if (test.includes(s)) throw new Error('train: seed ' + s + ' belongs to the TEST split');
  for (const env of Object.values(reg.envs).filter((e) => e.runner === 'robokit')) {
    const emb = reg.embodiments[env.embodiments[0]];
    for (const lv of env.curriculum.levels) for (const s of seeds) {
      const st = RC.reset(env, emb, s, lv.level);
      while (!st.done) { const x = feat(RC, st), a = RC.policy(st), t = P.target(st, a); X.push(x); Y.push(t.y); Mk.push(t.m); RC.step(st, a); }
      episodes.push([env.id, lv.level, s, st.step, st.done !== 'cap' ? 1 : 0]);
    }
  }
  return { X, Y, M: Mk, episodes };
}

export function train(reg, RC, P, T = TRAIN) {
  const feat = T.features === 'reach' ? P.featuresG : P.features, F = T.features === 'reach' ? P.FG : P.F;
  const D = dataset(reg, RC, P, T.split.train, T.split.test, feat), H = T.hidden, O = T.out, N = D.X.length;
  /* grip_loss 'whinge' (bcg): the grip output is trained as a CLASSIFICATION head - squared hinge on the score with
   * the label +-1 and inverse-frequency class weights (so the rare 'close now' class counts as much as the common one);
   * the other outputs keep the squared error. 'mse' (bc) leaves the loop exactly as it was. */
  let wPos = 1, wNeg = 1, nPos = 0, nNeg = 0;
  if (T.grip_loss === 'whinge') {
    for (let i = 0; i < N; i++) if (D.M[i][2]) { if (D.Y[i][2] >= 0.5) nPos++; else nNeg++; }
    wPos = (nPos + nNeg) / (2 * nPos); wNeg = (nPos + nNeg) / (2 * nNeg);
  }
  const rnd = P.mulberry32(T.init_seed), u = (a) => (rnd() * 2 - 1) * a;
  const W1 = Float64Array.from({ length: H * F }, () => u(1 / Math.sqrt(F))), b1 = new Float64Array(H);
  const W2 = Float64Array.from({ length: O * H }, () => u(1 / Math.sqrt(H))), b2 = new Float64Array(O);
  const sh = P.mulberry32(T.shuffle_seed), idx = Array.from({ length: N }, (_, i) => i);
  const z = new Float64Array(H), h = new Float64Array(H), gy = new Float64Array(O), gh = new Float64Array(H);
  const gW1 = new Float64Array(H * F), gb1 = new Float64Array(H), gW2 = new Float64Array(O * H), gb2 = new Float64Array(O);
  const losses = [], gripLosses = [];
  for (let ep = 0; ep < T.epochs; ep++) {
    for (let i = N - 1; i > 0; i--) { const j = Math.floor(sh() * (i + 1)); const t = idx[i]; idx[i] = idx[j]; idx[j] = t; }
    let L = 0, cnt = 0, Lg = 0, cg = 0;
    for (let s0 = 0; s0 < N; s0 += T.batch) {
      const B = Math.min(T.batch, N - s0); gW1.fill(0); gb1.fill(0); gW2.fill(0); gb2.fill(0);
      for (let q = s0; q < s0 + B; q++) {
        const x = D.X[idx[q]], y = D.Y[idx[q]], m = D.M[idx[q]];
        for (let j = 0; j < H; j++) { let a = b1[j]; for (let i = 0; i < F; i++) a += W1[j * F + i] * x[i]; z[j] = a; h[j] = a / (1 + Math.abs(a)); }
        for (let k = 0; k < O; k++) { let a = b2[k]; for (let j = 0; j < H; j++) a += W2[k * H + j] * h[j]; 
          if (k === 2 && T.grip_loss === 'whinge') { if (m[k]) { const sg = y[k] >= 0.5 ? 1 : -1, cw = sg > 0 ? wPos : wNeg, mg = Math.max(0, 1 - sg * a); Lg += cw * mg * mg; cg += 1; gy[k] = -2 * cw * sg * mg / B; } else gy[k] = 0; continue; }
          const e = (a - y[k]) * m[k]; L += e * e; cnt += m[k]; gy[k] = 2 * e / B; }
        gh.fill(0);
        for (let k = 0; k < O; k++) { gb2[k] += gy[k]; for (let j = 0; j < H; j++) { gW2[k * H + j] += gy[k] * h[j]; gh[j] += gy[k] * W2[k * H + j]; } }
        for (let j = 0; j < H; j++) { const d = 1 + Math.abs(z[j]), g = gh[j] / (d * d); gb1[j] += g; for (let i = 0; i < F; i++) gW1[j * F + i] += g * x[i]; }
      }
      for (let i = 0; i < W1.length; i++) W1[i] -= T.lr * gW1[i];
      for (let i = 0; i < H; i++) b1[i] -= T.lr * gb1[i];
      for (let i = 0; i < W2.length; i++) W2[i] -= T.lr * gW2[i];
      for (let i = 0; i < O; i++) b2[i] -= T.lr * gb2[i];
    }
    losses.push(Math.round(L / cnt * 1e6) / 1e6); if (T.grip_loss === 'whinge') gripLosses.push(Math.round(Lg / cg * 1e6) / 1e6);
  }
  const q = (a) => Array.from(a, (x) => Math.round(x * T.scale));
  const weights = { in: F, hidden: H, out: O, act: 'softsign', scale: T.scale, W1: q(W1), b1: q(b1), W2: q(W2), b2: q(b2) };
  return { weights, episodes: D.episodes, samples: N, losses, gripLosses, grip: { positives: nPos, negatives: nNeg } };
}
export const MODEL_SPECS = {
  bc: TRAIN,
  /* bcg: the second carded policy. The first never learned grip timing (its grip target is a step in the distance to the
   * pick, which a 24-input net with that distance squashed to [0, 1] over 10 m cannot place to the tenth of a metre, and
   * a squared error on a 1%-positive label settles on "never close"). Two changes, chosen on TRAIN seeds only (trained
   * on seeds 1-6, scored on 7-10; the TEST seeds were never run while choosing): two extra features that expose the gap
   * to the gripper's reach, and a class-weighted squared-hinge classification head for the grip. Width and epochs were
   * raised on the same validation seeds. */
  bcg: { ...TRAIN, features: 'reach', grip_loss: 'whinge', hidden: 32, epochs: 60 },
};
export function modelRecord(reg, RC, P, T = TRAIN) {
  const r = train(reg, RC, P, T), N = r.episodes.length, G = T.grip_loss === 'whinge', F = T.features === 'reach' ? P.FG : P.F;
  const weights_sha256 = createHash('sha256').update(JSON.stringify(r.weights)).digest('hex');
  const data = `${N} SCRIPTED reference episodes (${r.samples} control steps) on the TRAIN seeds ${T.split.train[0]}-${T.split.train[T.split.train.length - 1]}; the TEST seeds ${T.split.test[0]}-${T.split.test[T.split.test.length - 1]} are held out`;
  const card = G ? {
    what: `a small behaviour-cloning policy with a class-weighted grip head trained on ${N} SCRIPTED episodes; not a language model; not trained on any learner's data`,
    architecture: `MLP ${F}-${T.hidden}-${T.out}, softsign hidden units, linear outputs (v, w, grip score, vz; masked per task); the grip closes where its score is >= 0`,
    parameters: F * T.hidden + T.hidden + T.hidden * T.out + T.out,
    trained_by: 'robotics/arena/train.mjs, in Node at build time',
    optimiser: `plain minibatch gradient descent: learning rate ${T.lr}, batch ${T.batch}, ${T.epochs} epochs, no momentum, no Adam; v, w, vz squared error; grip a squared-hinge classification loss on the label +-1, each class weighted by n / (2 x its count) (${r.grip.positives} close-now steps against ${r.grip.negatives} others)`,
    data,
    inputs: `${F} features: the first model's ${P.F} (goal bearing and distance, two nearest obstacles and the nearest wall, contact, gripper, depth error, v, w, task one-hot) plus two that expose the signed gap between the distance to the goal and the gripper's reach circle, at 0.5 m and at 0.1 m scale`,
    addresses: 'grip timing: the first model never learned when to close the gripper and binned nothing in litter sort; this one is given the distance to the reach circle and a classifier head for the rare close-now class',
    selection: `width, epochs and the choice of the two features and the class-weighted head were made on TRAIN seeds only (trained on seeds 1-6, scored on 7-10); the TEST seeds ${T.split.test[0]}-${T.split.test[T.split.test.length - 1]} were not run while choosing and the final model was fitted once on seeds 1-10`,
    limits: 'a SCRIPTED potential-field teacher is cloned, so it can at best match that teacher; the reach features carry the teacher\'s own grip rule in a smooth form; sandbox tasks only, not a claim about any real robot',
    determinism: `seeded init (${T.init_seed}) and shuffles (${T.shuffle_seed}); weights stored as integer micro-units and sha256-pinned`,
  } : {
    what: `a small behaviour-cloning policy trained on ${N} SCRIPTED episodes; not a language model; not trained on any learner's data`,
    architecture: `MLP ${P.F}-${T.hidden}-${T.out}, softsign hidden units, linear outputs (v, w, grip, vz; masked per task)`,
    parameters: P.F * T.hidden + T.hidden + T.hidden * T.out + T.out,
    trained_by: 'robotics/arena/train.mjs, in Node at build time',
    optimiser: `plain minibatch gradient descent: learning rate ${T.lr}, batch ${T.batch}, ${T.epochs} epochs, no momentum, no Adam`,
    data,
    inputs: `${P.F} egocentric features: goal bearing and distance, two nearest obstacles and the nearest wall (bearing, clearance), contact, gripper, depth error, v, w, task one-hot`,
    determinism: `seeded init (${T.init_seed}) and shuffles (${T.shuffle_seed}); weights stored as integer micro-units and sha256-pinned`,
  };
  return {
    id: G ? `bcg.mlp-${F}-${T.hidden}-${T.out}` : 'bc.mlp-24-16-4', policy: G ? 'bcg' : 'bc', provenance: 'TRAINED',
    card,
    split: T.split,
    train: { episodes: N, samples: r.samples, epochs: T.epochs, batch: T.batch, lr: T.lr, init_seed: T.init_seed,
      shuffle_seed: T.shuffle_seed, loss_first: r.losses[0], loss_last: r.losses[r.losses.length - 1],
      ...(G ? { grip_loss_first: r.gripLosses[0], grip_loss_last: r.gripLosses[r.gripLosses.length - 1], grip_positives: r.grip.positives, grip_negatives: r.grip.negatives } : {}),
      episode_list: r.episodes },
    weights: r.weights, weights_sha256,
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const reg = JSON.parse(readFileSync(join(ROOT, 'robotics/registry/robotics.json'), 'utf8'));
  const { RoboCore } = loadCore(), { Policies } = loadPolicies();
  const ms = Object.values(MODEL_SPECS).map((T) => modelRecord(reg, RoboCore, Policies, T));
  if (process.argv.includes('--write')) writeFileSync(join(HERE, 'registry/models.json'),
    JSON.stringify({ schema: 'tc-arena-models/1', what: 'model registry of the arena: weights sha256-pinned; each model carries its card', models: ms }, null, 1) + '\n');
  for (const m of ms) process.stdout.write(JSON.stringify({ id: m.id, weights_sha256: m.weights_sha256, train: { ...m.train, episode_list: m.train.episode_list.length } }) + '\n');
}
