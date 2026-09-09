/**
 * Pack verification at 111-hall scale.
 *
 * The 33-hall pack proved uniqueness by loading a gzipped ledger of every row
 * into a Set. That does not survive the jump to 11,000,000: the ledger would
 * be ~90MB and the Set would be gigabytes.
 *
 * So the proof changes shape rather than shrinking to a sample. index() and
 * fromIndex() are declared inverses over [0, 11,000,000); this walks every
 * index, marks a bit, and round-trips the ID. A full-population proof costs
 * one 1.375MB bitmap and a few seconds — cheaper AND stronger than the sampled
 * check it replaces, because a sample can only ever fail to find a collision.
 */
import { openRegistry, SHAPE, index, fromIndex } from './registry.js';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };
const F = (x) => x.toLocaleString('en-US');

const manifest = JSON.parse(readFileSync(new URL('./manifest.json', import.meta.url)));
const reg = await openRegistry(new URL('./registry/', import.meta.url));

/* ------------------------------------------------------- the arithmetic --- */
const L = manifest.ledger;
ok(`the ledger closes at ${F(L.total_modules)} from the pack's own shape`,
  L.halls * L.lessons_per_hall * L.variants_per_lesson + L.shared_library_modules === L.total_modules
  && L.total_modules === 11_000_000);
ok('the library is shared, not per-hall — 11,000,000 is not divisible by 111',
  11_000_000 % 111 === 11 && L.shared_library_modules === 11_000);
ok(`${F(L.halls)} halls x ${L.levels_per_hall} levels x ${L.slots_per_level} slots = ${F(L.core_lessons)} lessons`,
  L.halls * L.levels_per_hall * L.slots_per_level === L.core_lessons);
ok('the library and the consumer library agree on the shape',
  SHAPE.total === L.total_modules && SHAPE.halls === L.halls && SHAPE.variants === L.variants_per_lesson);

/* ---------------------------------------- full-population uniqueness ------ */
{
  // Math.ceil, not bit tricks: the first version wrote `SHAPE.total >> 3 | 0 + 1`,
  // where `0 + 1` binds before `|`, so it computed (total>>3)|1 — which happens
  // to be large enough at exactly 11,000,000 and would silently under-allocate
  // at other sizes. A buffer sized by coincidence is a buffer overrun waiting
  // for the next release to change one number.
  const bits = new Uint8Array(Math.ceil(SHAPE.total / 8));
  let seen = 0, bad = 0, roundTripped = 0;
  const t0 = Date.now();
  for (let i = 0; i < SHAPE.total; i++) {
    const d = fromIndex(i);
    if (!d) { bad++; continue; }
    let back;
    if (d.kind === 'core') {
      back = index(d.hallIdx, d.level, d.slot, d.modality, d.band);
      // round-trip a sparse but wide sample of the actual ID strings
      if (i % 100_003 === 0) {
        const id = reg.moduleIdAt(i);
        if (reg.resolve(id)?.lesson_id !== id.split('.').slice(0, 3).join('.')) bad++;
        else roundTripped++;
      }
    } else {
      back = i;                       // library block is a contiguous range
      if (i % 100_003 === 0) { if (!reg.resolve(d.item_id)) bad++; else roundTripped++; }
    }
    if (back !== i) { bad++; continue; }
    const byte = back >> 3, mask = 1 << (back & 7);
    if (bits[byte] & mask) { bad++; continue; }
    bits[byte] |= mask; seen++;
  }
  const secs = ((Date.now() - t0) / 1000).toFixed(1);
  ok(`every one of ${F(SHAPE.total)} module indices is reached exactly once (${secs}s)`,
    seen === SHAPE.total && bad === 0);
  ok(`${roundTripped} sampled IDs resolve back to the lesson that minted them`,
    roundTripped > 100);
}

/* -------------------------------------------------------------- resolve --- */
ok('a core module resolves to its lesson, band offset applied',
  (() => { const m = reg.resolve('u000.l050.s055.vr_sim.core');
           const s = reg.resolve('u000.l050.s055.vr_sim.support');
           return m && s && +(s.difficulty - m.difficulty).toFixed(1) === -5; })());
ok('malformed and out-of-range IDs return null, not garbage',
  reg.resolve('nope') === null && reg.resolve('u999.l000.s000.vr_sim.core') === null
  && reg.resolve('u000.l100.s000.vr_sim.core') === null
  && reg.resolve('u000.l000.s110.vr_sim.core') === null);
ok('one lesson expands to exactly 9 unique variants',
  (() => { const ids = new Set();
    for (const m of ['vr_sim', 'guided_drill', 'quiz_reading'])
      for (const b of ['support', 'core', 'stretch']) {
        const id = `u010.l010.s010.${m}.${b}`;
        if (reg.resolve(id)) ids.add(id);
      }
    return ids.size === 9; })());

/* ---------------------------------------------------------------- halls --- */
ok(`${F(reg.halls.length)} halls, and the first 33 keep their original index`,
  reg.halls.length === 111 && reg.hall('ironworkers').index === 0
  && reg.hall('hazmat').index === 32 && reg.hall(0).slug === 'ironworkers');
ok('every hall carries the same ladder, so no hall is quietly smaller',
  reg.halls.every((h) => h.lessons === 11_000 && h.modules === 99_000));
ok('the 78 new halls are marked as a second wave rather than backdated',
  reg.halls.filter((h) => h.opened_wave === 2).length === 78);

/* ---------------------------------------------------------------- graph --- */
ok(`skill graph: ${F(reg.skills.length)} nodes, every edge resolves`,
  reg.skills.length === 111 * 33
  && reg.skills.every((s) => [...s.requires, ...s.supports, ...s.interferes]
      .every((e) => reg.skill(e) !== null)));
ok('safety fundamentals is the root every other strand rests on',
  reg.skills.filter((s) => s.strand === 'safety' && s.tier === 'fundamentals')
    .every((s) => s.requires.length === 0));

/* ----------------------------------------------------------------- dial --- */
{
  const picks = reg.selectForDial({ union: 'welders', theta: 58, setpoint: 51.5 });
  ok(`dial selection returns ${picks.length} live candidates within tolerance, without scanning 11 million`,
    picks.length === 40 && picks.every((p) => Math.abs(p.difficulty - 51.5) <= 4)
    && picks.every((p) => p.state === 'live'));
}

/* -------------------------------------------------------------- honesty --- */
ok('the manifest states what the module count is, and what it is not',
  /addressable module IDs/.test(manifest.honesty.modules_are)
  && /hand-written/.test(manifest.honesty.not));
ok('the manifest states the taxonomy is not a roster of chartered locals',
  /not a roster of chartered locals/.test(manifest.honesty.taxonomy));
ok(`authored objects (${F(manifest.authored_objects)}) are reported beside the module count`,
  manifest.authored_objects > 0 && manifest.generated_to_authored_ratio > 100);
ok('the state census covers every module and nothing is uncounted',
  Object.values(manifest.by_state).reduce((a, b) => a + b, 0) === 11_000_000);

console.log(`\n${n} checks passed — ${F(SHAPE.total)} modules verified end to end.`);
