#!/usr/bin/env node
/* robotics/claw/export.mjs - write the Omega Claw instruction-conditioned dataset to a directory, ready for someone to
 * train a robot-learning model (a language-conditioned policy or a VLA) ELSEWHERE. This script trains nothing.
 *
 *   node robotics/claw/export.mjs --out <dir> [--revocations <file>] [<learner package.json> ...]
 *
 * Writes <dir>/manifest.json, <dir>/DATASET_CARD.md and <dir>/<scheme>/{train,val,test}.jsonl for each split scheme
 * (seen-tasks: split by seed; unseen-tasks: split by task family). One JSON object per line: the quoted instruction
 * and its source pointer, context lines, the seeded scene, observations [{pose, vel, near}], actions [[...]], outcome,
 * Referee verdict, class-balance weight, trajectory hash and provenance. Learner packages are admitted only by the
 * datashare rules (robot-training consent scope, revocation list - datashare/revocations.json by default). Every
 * dataset check runs first; any failure is printed as `FAIL <check>: <detail>` and nothing is written. No network. */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { basename, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { C, AUTH, DS_CFG, ROOT, scripted, learner, assemble, indexOf } from './node.mjs';

export async function exportDataset({ out, revocationsFile, learnerFiles }) {
  const revocations = JSON.parse(readFileSync(revocationsFile || join(ROOT, 'datashare/revocations.json'), 'utf8'));
  const sc = scripted();
  let human = [], refused = [];
  if (learnerFiles.length) {
    const r = await learner(learnerFiles.map((f) => ({ name: basename(f), record: JSON.parse(readFileSync(f, 'utf8')) })), revocations);
    human = r.samples; refused = r.manifest.refused;
  }
  const { ds, idx, card, cardIds } = assemble(sc.concat(human), human.length);
  const fails = C.validate(ds.samples, AUTH, revocations, card, cardIds);
  if (fails.length) return { fails };
  mkdirSync(out, { recursive: true });
  const line = (s) => JSON.stringify({ id: s.id, task: s.task, family: s.family, level: s.level, level_name: s.level_name, seed: s.seed, actor: s.actor,
    instruction: s.instruction, context: s.context, lesson: s.lesson, action_names: s.action_names, scene: s.scene,
    observations: s.steps.map((x) => ({ i: x.i, pose: x.pose, vel: x.vel, near: x.near })), actions: s.steps.map((x) => x.a),
    dt_s: s.dt_s, hz: s.hz, outcome: s.outcome, referee: s.referee, weight: s.weight, traj_hash: s.traj_hash, provenance: s.provenance });
  for (const scheme of Object.keys(AUTH.splits)) {
    mkdirSync(join(out, scheme), { recursive: true });
    for (const sp of ['train', 'val', 'test']) {
      const rows = ds.samples.filter((s) => s.split[scheme] === sp);
      writeFileSync(join(out, scheme, sp + '.jsonl'), rows.map(line).join('\n') + (rows.length ? '\n' : ''));
    }
  }
  const index = indexOf(ds, idx);
  const manifest = { record: 'tc-dataset/1', pack: 'smartcitix-robotics-claw', trained_models: 0, refused, ...index };
  writeFileSync(join(out, 'manifest.json'), JSON.stringify(manifest, null, 1) + '\n');
  writeFileSync(join(out, 'DATASET_CARD.md'), card + '\n');
  return { fails: [], manifest };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const a = process.argv.slice(2), o = { learnerFiles: [] };
  for (let i = 0; i < a.length; i++) { if (a[i] === '--out') o.out = a[++i]; else if (a[i] === '--revocations') o.revocationsFile = a[++i]; else o.learnerFiles.push(a[i]); }
  if (!o.out) { console.error('FAIL export: --out <dir> is required'); process.exit(1); }
  const r = await exportDataset(o);
  if (r.fails.length) { for (const f of r.fails) console.error('FAIL ' + f.check + ': ' + f.detail); process.exit(1); }
  const m = r.manifest;
  console.log(`claw dataset: ${m.samples} samples (${m.learner} learner), ${m.duplicates} duplicates removed, splits ${JSON.stringify(m.splits)}, ${m.refused.length} package(s) refused -> ${o.out}`);
}
