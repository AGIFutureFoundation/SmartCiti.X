#!/usr/bin/env node
/**
 * datashare/analyse.mjs - what a set of episodes covers and what it misses.
 *
 *   node datashare/analyse.mjs <dataset dir | package.json ...>
 *
 * Episode counts per kind and per env / seat, success rates, range checks of every world sample against the
 * env's observation and action ranges (robotics.json via contrib.json), missing-field and outlier flags (robust
 * z over median/MAD, skipped and said so under 5 episodes), and coverage gaps per env (seeds, embodiments,
 * actors, seats with no episode). Prints a table and writes nothing. Packages are analysed as they are, verified
 * or not - analysis is not admission; build_dataset.mjs admits.
 */
import { readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { CORE } from './node_shell.mjs';

export function itemsFrom(paths) {
  const items = [];
  for (const p of paths) {
    if (statSync(p).isDirectory()) {
      for (const s of ['train', 'val', 'test']) {
        for (const line of readFileSync(join(p, s + '.jsonl'), 'utf8').split('\n')) if (line.trim()) { const r = JSON.parse(line); items.push({ id: r.id, split: s, episode: r.episode }); }
      }
    } else {
      const rec = JSON.parse(readFileSync(p, 'utf8'));
      for (const ep of rec.dataset.episodes) items.push({ episode: ep });
    }
  }
  return items;
}

export function report(a) {
  const L = [];
  L.push(`episodes ${a.episodes}; by kind: ${Object.entries(a.by_kind).map(([k, n]) => k + ' ' + n).join(', ') || 'none'}`);
  if (Object.keys(a.by_split).length) L.push(`splits: ${Object.entries(a.by_split).map(([k, n]) => k + ' ' + n).join(', ')}`);
  L.push('where                          n   outcomes  success  rate');
  for (const [w, v] of Object.entries(a.by_where)) L.push(`${w.padEnd(30)} ${String(v.n).padStart(3)} ${String(v.outcomes).padStart(9)} ${String(v.success).padStart(8)}  ${v.rate === null ? '-' : Math.round(100 * v.rate) + '%'}`);
  for (const [env, r] of Object.entries(a.range)) L.push(`range ${env}: ${r.checked} values checked, ${r.out_of_range} outside the env ranges`);
  for (const f of a.flags) L.push(`flag ${f.flag} ${f.where} ${f.episode}: ${f.detail}`);
  for (const n of a.outlier_notes) L.push(`note ${n}`);
  for (const g of a.gaps) L.push(`gap ${g.env}: ${g.gap}`);
  return L;
}

const isMain = process.argv[1] && new URL(`file://${process.argv[1]}`).pathname === new URL(import.meta.url).pathname;
if (isMain) {
  try {
    if (process.argv.length < 3) throw new Error('usage: node datashare/analyse.mjs <dataset dir | package.json ...>');
    for (const l of report(CORE.analyse(itemsFrom(process.argv.slice(2))))) console.log(l);
  } catch (e) { console.error('FAIL analyse: ' + e.message); process.exit(1); }
}
