/** How many skills should a learner have open at once? Measured, not asserted. */
import { POLICY } from './sequencer.mjs';
import { runAll } from './sim_curriculum.mjs';

const pad = (s, n) => String(s).padEnd(n);
console.log(pad('workingSet', 12) + pad('gated', 8) + pad('learned', 9) + pad('ability', 9) +
            pad('retain30d', 11) + pad('durable', 9) + 'reviews');
console.log('-'.repeat(66));
const rows = [];
for (const k of [1, 2, 3, 4, 5, 6, 8, 11, 33]) {
  POLICY.workingSetMax = k;
  const r = runAll().find((x) => x.strategy === 'graph');
  const durable = +(r.totalAbilityGained * r.retentionAt30d).toFixed(1);
  rows.push({ k, ...r, durable });
  console.log(pad(k, 12) + pad(r.skillsGated, 8) + pad(r.skillsLearned, 9) +
              pad(r.totalAbilityGained, 9) + pad(r.retentionAt30d, 11) +
              pad(durable, 9) + r.reviews);
}
const best = [...rows].sort((a, b) => b.durable - a.durable)[0];
const bestGated = [...rows].sort((a, b) => b.skillsGated - a.skillsGated || b.durable - a.durable)[0];
console.log(`\nmost durable ability: workingSet=${best.k} (${best.durable})`);
console.log(`most skills certified: workingSet=${bestGated.k} (${bestGated.skillsGated})`);
