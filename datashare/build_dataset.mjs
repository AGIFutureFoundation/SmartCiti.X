#!/usr/bin/env node
/**
 * datashare/build_dataset.mjs - verified contribution packages -> a tc-dataset/1 directory.
 *
 *   node datashare/build_dataset.mjs --scope <agent-training|robot-training> --built-at <ISO> --out <dir>
 *        [--revocations <file>] [--strict] <package.json> ...
 *
 * Writes <dir>/manifest.json (schema versions, per-episode ids and provenance, splits, refusals, digest),
 * <dir>/train.jsonl, val.jsonl, test.jsonl ({id, episode} per line), <dir>/analysis.json and
 * <dir>/DATASET_CARD.md. Every package is first run through contrib/verify.mjs; a package it rejects, or one
 * that carries a forbidden field (name, email, free text, precise location, audio, camera, biometric), an
 * incompatible licence, a scope that does not include --scope, or that is revoked or duplicated, is REFUSED
 * BY NAME: `REFUSED <file>: <reason> - <detail>` on stderr, and listed in manifest.refused. --strict exits 1
 * on any refusal. No clock is read (--built-at is required) and nothing is sent anywhere.
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { basename, join } from 'node:path';
import { CORE, verdictOf } from './node_shell.mjs';

function args(argv) {
  const o = { files: [], strict: false, revocations: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--scope') o.scope = argv[++i];
    else if (a === '--built-at') o.built_at = argv[++i];
    else if (a === '--out') o.out = argv[++i];
    else if (a === '--revocations') o.revocations = argv[++i];
    else if (a === '--strict') o.strict = true;
    else o.files.push(a);
  }
  return o;
}

export async function buildFromFiles(o) {
  for (const k of ['scope', 'built_at', 'out']) if (typeof o[k] !== 'string') throw new Error('--' + k.replace('_', '-') + ' is required');
  const revocations = o.revocations === null ? { record: 'tc-revocations/1', packages: [], episodes: [] } : JSON.parse(readFileSync(o.revocations, 'utf8'));
  const packages = [];
  const early = [];
  for (const f of [...o.files].sort()) {
    let record;
    try { record = JSON.parse(readFileSync(f, 'utf8')); } catch (e) { early.push({ package: basename(f), reason: 'verifier', detail: 'not readable JSON: ' + e.message }); continue; }
    packages.push({ name: basename(f), record, verdict: verdictOf(record) });
  }
  const { manifest, items } = await CORE.buildDataset({ packages, scope: o.scope, built_at: o.built_at, revocations });
  if (early.length) { manifest.refused = [...early, ...manifest.refused]; delete manifest.digest; manifest.digest = { alg: 'SHA-256', over: 'canonical manifest without digest', hex: await CORE.digestOf(manifest) }; }
  const analysis = CORE.analyse(items);
  const card = CORE.renderCard(manifest, analysis);
  mkdirSync(o.out, { recursive: true });
  writeFileSync(join(o.out, 'manifest.json'), JSON.stringify(manifest, null, 1) + '\n');
  for (const s of ['train', 'val', 'test']) writeFileSync(join(o.out, s + '.jsonl'), items.filter((x) => x.split === s).map((x) => JSON.stringify({ id: x.id, episode: x.episode })).join('\n') + (items.some((x) => x.split === s) ? '\n' : ''));
  writeFileSync(join(o.out, 'analysis.json'), JSON.stringify(analysis, null, 1) + '\n');
  writeFileSync(join(o.out, 'DATASET_CARD.md'), card + '\n');
  return { manifest, analysis, card };
}

const isMain = process.argv[1] && new URL(`file://${process.argv[1]}`).pathname === new URL(import.meta.url).pathname;
if (isMain) {
  try {
    const o = args(process.argv.slice(2));
    const { manifest } = await buildFromFiles(o);
    for (const r of manifest.refused) console.error(`REFUSED ${r.package}: ${r.reason} - ${r.detail}`);
    console.log(`dataset ${manifest.record} (${manifest.scope}): ${manifest.packages.length} package(s) admitted, ${manifest.refused.length} refused; `
      + `${manifest.episodes.length} episodes (train ${manifest.splits.train}, val ${manifest.splits.val}, test ${manifest.splits.test}); `
      + `${manifest.excluded.duplicate_episodes} duplicate(s), ${manifest.excluded.revoked_episodes} revoked episode(s); manifest ${manifest.digest.hex.slice(0, 16)} -> ${o.out}`);
    process.exit(o.strict && manifest.refused.length ? 1 : 0);
  } catch (e) {
    console.error('FAIL build_dataset: ' + e.message);
    process.exit(1);
  }
}
