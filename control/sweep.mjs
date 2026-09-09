/**
 * Parameter sweep over the ACP-03 tuning sheet. Produces the calibration
 * evidence for the defaults, rather than asserting them.
 */
import { runAll } from './simulate.mjs';

const grid = [];
for (const window of [3, 5, 8, 10])
  for (const loopGain of [0.3, 0.45, 0.6, 0.8, 1.0])
    grid.push({ window, loopGain });

const results = [];
for (const cfg of grid) {
  const rows = runAll(cfg).filter((r) => r.strategy === 'ZPD dial');
  const inBand = rows.reduce((a, r) => a + r.inBandPct, 0) / rows.length;
  const success = rows.reduce((a, r) => a + r.successPct, 0) / rows.length;
  const thetaErr = rows.reduce((a, r) => a + r.thetaError, 0) / rows.length;
  // how far the mean success rate of the WORST archetype sits from the band
  const worst = rows.reduce((w, r) => {
    const miss = r.successPct < 70 ? 70 - r.successPct : r.successPct > 85 ? r.successPct - 85 : 0;
    return Math.max(w, miss);
  }, 0);
  results.push({ ...cfg, inBand: +inBand.toFixed(1), success: +success.toFixed(1),
                 thetaErr: +thetaErr.toFixed(2), worstMiss: +worst.toFixed(1) });
}

results.sort((a, b) => b.inBand - a.inBand);
const pad = (s, n) => String(s).padEnd(n);
console.log(pad('window', 8) + pad('loopGain', 10) + pad('in-band%', 10) +
            pad('success%', 10) + pad('θ err', 8) + 'worst archetype miss');
console.log('-'.repeat(62));
for (const r of results)
  console.log(pad(r.window, 8) + pad(r.loopGain, 10) + pad(r.inBand, 10) +
              pad(r.success, 10) + pad(r.thetaErr, 8) + r.worstMiss);

const best = results[0];
console.log(`\nbest in-band: window=${best.window} loopGain=${best.loopGain} -> ${best.inBand}%`);
const safest = [...results].sort((a, b) => a.worstMiss - b.worstMiss || b.inBand - a.inBand)[0];
console.log(`safest (no archetype outside band): window=${safest.window} loopGain=${safest.loopGain} -> in-band ${safest.inBand}%, worst miss ${safest.worstMiss}`);
