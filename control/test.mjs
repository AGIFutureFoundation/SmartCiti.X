/**
 * Control-plane tests, including an end-to-end run against the real
 * module registry data pack.
 */
import assert from 'node:assert/strict';
import { LearnerProfile, pSuccess, RUNG_CREDIT } from './lpa.mjs';
import { ZpdDial, classifyAffect, impliedSetpoint, BAND, DEFAULTS } from './dial.mjs';
import { openRegistry } from '../pack/registry.js';
import { runAll } from './simulate.mjs';

let n = 0;
const ok = (m) => { n++; console.log(`  ok  ${m}`); };

// --- logistic + band geometry ------------------------------------------------
assert.ok(Math.abs(pSuccess(50, 50) - 0.5) < 1e-9);
// d = theta - W*logit(p): the difficulty at which success probability is p
const lo = 50 - 12 * Math.log10(BAND.lo / (1 - BAND.lo));
const hi = 50 - 12 * Math.log10(BAND.hi / (1 - BAND.hi));
assert.ok(Math.abs(pSuccess(50, lo) - BAND.lo) < 1e-6);
assert.ok(Math.abs(pSuccess(50, hi) - BAND.hi) < 1e-6);
assert.ok(hi < lo && lo < 50, 'band must sit BELOW theta (theta is the 50% frontier)');
ok(`band geometry: theta-${(50 - lo).toFixed(1)} .. theta-${(50 - hi).toFixed(1)} maps to p=0.70..0.85`);

// --- setpoint default lands inside the band ---------------------------------
const pAtDefault = pSuccess(50, 50 + DEFAULTS.setpointOffset);
assert.ok(pAtDefault >= BAND.lo && pAtDefault <= BAND.hi, `default setpoint p=${pAtDefault}`);
ok(`default setpoint offset ${DEFAULTS.setpointOffset} -> p=${pAtDefault.toFixed(3)}, inside the band`);

// --- closed-loop inversion is the exact inverse of the logistic -------------
const implied = impliedSetpoint(60, 0.775, 0);
assert.ok(Math.abs(pSuccess(implied, 60) - 0.775) < 1e-6);
ok('closed-loop inversion recovers the difficulty that produced the observed rate');

// --- hint credit monotonically decreases ------------------------------------
for (let i = 1; i < RUNG_CREDIT.length; i++) assert.ok(RUNG_CREDIT[i] < RUNG_CREDIT[i - 1]);
ok('hint-rung credit strictly decreases with depth');

// --- a hinted success is weaker evidence than an unaided one ----------------
const a = new LearnerProfile('a'), b = new LearnerProfile('b');
const r1 = a.record('s', { difficulty: 50, correct: true, rung: 0 });
const r2 = b.record('s', { difficulty: 50, correct: true, rung: 3 });
assert.ok(r1.delta > r2.delta, 'unaided success must move theta more than a rung-3 success');
ok('unaided success moves theta more than a scaffolded one');

// --- guess-spam is down-weighted --------------------------------------------
const c = new LearnerProfile('c'), d2 = new LearnerProfile('d');
const rc = c.record('s', { difficulty: 70, correct: false, rung: 0 });
const rd = d2.record('s', { difficulty: 70, correct: false, rung: 0, guessSpam: true });
assert.ok(Math.abs(rd.delta) < Math.abs(rc.delta));
ok('guess-spam evidence is down-weighted');

// --- affect scores are bounded and each term capped at its weight -----------
const extreme = classifyAffect({ pHat: 1, latZ: -99, latVarZ: 99, hintRate: 9, idleRate: 9, abandon: true });
assert.ok(extreme.boredom <= 1 && extreme.anxiety <= 1);
const onlyFast = classifyAffect({ pHat: 0.8, latZ: -99, latVarZ: 0, hintRate: 1, idleRate: 0, abandon: false });
assert.ok(onlyFast.boredom < 0.6, 'one extreme signal alone must not trip boredom');
ok('affect scores bounded; no single signal saturates a score');

// --- the session rail re-anchors (the v1.1 freeze bug) ----------------------
const p = new LearnerProfile('p');
const dial = new ZpdDial(p);
const start = dial.setpoint('s');
for (let i = 0; i < 200; i++) {
  if (i % 25 === 0) dial.startSession('s');
  const dd = dial.setpoint('s');
  p.record('s', { difficulty: dd, correct: true, rung: 0 });
  dial.observe('s', { correct: true, rung: 0, latZ: -1, difficulty: dd });
}
assert.ok(dial.setpoint('s') - start > DEFAULTS.sessionDelta,
  'setpoint must be able to travel further than one session delta across sessions');
ok(`setpoint escapes the session rail across sessions (${start.toFixed(1)} -> ${dial.setpoint('s').toFixed(1)})`);

// --- the two clamps, and which one wins ------------------------------------
// The session cap is a COMFORT bound (don't lurch mid-session); the theta rail
// is a SAFETY bound (never absurdly far from the learner). They are applied in
// one place, cap first and rail last, so the rail is always the final word.
{
  const pr = new LearnerProfile('rails');
  const st = pr.get('s'); st.theta = 50; st.sigma = 5;
  const dl = new ZpdDial(pr);
  const d0 = dl.state('s');

  // comfort bound binds when it is tighter than the rail
  d0.sessionStart = 38; d0.c = 49;
  assert.equal(dl.setpoint('s'), 48, 'session cap should bound movement within a session');

  // safety rail wins when a stale-high anchor would push past it
  d0.sessionStart = 70; d0.c = 65;
  assert.equal(dl.setpoint('s'), 50, 'theta rail must override a stale session anchor');

  // and it holds at both extremes regardless of stored intent
  d0.sessionStart = 50; d0.c = 1e6;
  assert.ok(dl.setpoint('s') <= 50 + DEFAULTS.railHi + 1e-9);
  d0.c = -1e6;
  assert.ok(dl.setpoint('s') >= 50 + DEFAULTS.railLo - 1e-9);
}
ok('session cap bounds movement; the theta rail is the final authority');

// --- END TO END against the real registry pack ------------------------------
const reg = await openRegistry(new URL('../pack/registry/', import.meta.url));
const learner = new LearnerProfile('e2e');
const eDial = new ZpdDial(learner);
const UNION = 'welders';
let served = 0, hits = 0;
for (let session = 0; session < 12; session++) {
  eDial.startSession('welders.procedure.fundamentals');
  for (let i = 0; i < 25; i++) {
    const sp = eDial.setpoint('welders.procedure.fundamentals');
    const cands = await reg.selectForDial({ union: UNION, setpoint: sp, tolerance: 4, limit: 5 });
    if (!cands.length) continue;
    const mod = cands[0];
    served++;
    if (Math.abs(mod.difficulty - sp) <= 4) hits++;
    const correct = Math.random() < pSuccess(48, mod.difficulty);
    learner.record('welders.procedure.fundamentals',
      { difficulty: mod.difficulty, correct, rung: 0 });
    eDial.observe('welders.procedure.fundamentals',
      { correct, rung: 0, latZ: 0, difficulty: mod.difficulty });
  }
}
assert.ok(served > 100, `only ${served} modules served end to end`);
assert.equal(hits, served, 'every served module must satisfy the dial tolerance');
ok(`end-to-end: ${served} real registry modules served, all dial-compliant`);

// --- the dial beats both baselines on band residency ------------------------
const rows = runAll();
const mean = (k) => {
  const r = rows.filter((x) => x.strategy === k);
  return r.reduce((a, x) => a + x.inBandPct, 0) / r.length;
};
const dialBand = mean('ZPD dial');
assert.ok(dialBand > mean('Fixed difficulty (50)') * 2, 'dial must clearly beat fixed difficulty');
assert.ok(dialBand > mean('Random difficulty') * 2, 'dial must clearly beat random');
ok(`dial holds the band ${dialBand.toFixed(1)}% vs fixed ${mean('Fixed difficulty (50)').toFixed(1)}% / random ${mean('Random difficulty').toFixed(1)}%`);

// --- every archetype's mean success rate lands inside the band --------------
for (const r of rows.filter((x) => x.strategy === 'ZPD dial'))
  assert.ok(r.successPct >= 70 && r.successPct <= 85,
    `${r.archetype} success ${r.successPct}% outside the band`);
ok('all six learner archetypes end inside the 70–85% band');

console.log(`\n${n} checks passed.`);
