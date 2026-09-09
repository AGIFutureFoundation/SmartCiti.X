/**
 * Shadow-mode validation (spec §10 build order: run the dial in simulation
 * before it touches a learner).
 *
 * Honest framing: this validates the CONTROLLER, not the pedagogy. The
 * headline metrics are measured against each synthetic learner's TRUE latent
 * ability — which the dial never sees — so "time in band" is a real test of
 * whether the dial finds and holds the edge of capability. Learning gain is
 * reported as a secondary number and is a property of the learner model, not
 * evidence that ZPD teaching works.
 */
import { LearnerProfile, pSuccess } from './lpa.mjs';
import { ZpdDial, BAND } from './dial.mjs';

// ---------------------------------------------------------------- RNG (seeded)
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const gauss = (rnd) => {
  const u = Math.max(1e-9, rnd()), v = rnd();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
};

// ------------------------------------------------------------------ archetypes
const ARCHETYPES = [
  { id: 'steady',        label: 'Steady learner',      ability: 45, learnRate: 0.35, noise: 0.0, hintBias: 1.0 },
  { id: 'fast-climber',  label: 'Fast climber',        ability: 50, learnRate: 0.95, noise: 0.0, hintBias: 0.6 },
  { id: 'struggler',     label: 'Struggling learner',  ability: 28, learnRate: 0.15, noise: 0.0, hintBias: 1.8 },
  { id: 'misplaced-pro', label: 'Misplaced expert',    ability: 78, learnRate: 0.20, noise: 0.0, hintBias: 0.3 },
  { id: 'erratic',       label: 'Erratic performer',   ability: 50, learnRate: 0.30, noise: 0.9, hintBias: 1.1 },
  { id: 'returner',      label: 'Returner (21d gap)',  ability: 45, learnRate: 0.35, noise: 0.0, hintBias: 1.0, gapAt: 150, gapDays: 21 },
];

const SKILL = 'sim.skill';
const ATTEMPTS = 400;
const SESSION_LEN = 25;      // one quest arc (spec §5.3: 20–25 min)

/** One simulated attempt at a served difficulty. */
function attemptOutcome(arch, trueAbility, difficulty, rnd) {
  const gap = difficulty - trueAbility;
  // hint request: likelier the further the task sits above true ability
  const pHint = Math.max(0, Math.min(0.6, (gap + 4) / 30)) * arch.hintBias;
  const rung = rnd() < pHint ? 1 + Math.floor(rnd() * 2) : 0;
  // a hint effectively lowers the task for the learner
  const effective = difficulty - rung * 4;
  let p = pSuccess(trueAbility, effective);
  if (arch.noise) p = Math.max(0.02, Math.min(0.98, p + gauss(rnd) * 0.15 * arch.noise));
  const correct = rnd() < p;
  // latency z: fast when comfortably within ability, slow when stretched
  const latZ = gap / 10 + gauss(rnd) * (0.35 + 0.5 * arch.noise);
  const idle = !correct && rnd() < 0.05;
  const abandon = !correct && gap > 12 && rnd() < 0.05;
  return { correct, rung, latZ, idle, abandon };
}

/** Learning: gain is largest at moderate challenge, smaller when trivial or crushing. */
function learn(arch, trueAbility, difficulty, correct) {
  const p = pSuccess(trueAbility, difficulty);
  const shape = Math.exp(-((p - 0.75) ** 2) / (2 * 0.22 ** 2)); // peaks near p=0.75
  return arch.learnRate * shape * (correct ? 1 : 0.6) * 0.35;
}

// ------------------------------------------------------------------ strategies
function makeStrategy(kind, cfg) {
  if (kind === 'dial') {
    return {
      name: 'ZPD dial',
      init(profile) { this.dial = new ZpdDial(profile, cfg); },
      next() { return this.dial.setpoint(SKILL); },
      observe(a) { return this.dial.observe(SKILL, a); },
      states() { return this.dial.state(SKILL); },
    };
  }
  if (kind === 'fixed') {
    return { name: 'Fixed difficulty (50)', init() {}, next: () => 50, observe: () => null };
  }
  return {
    name: 'Random difficulty',
    init() { this.rnd = mulberry32(7); },
    next() { return 20 + this.rnd() * 60; },
    observe: () => null,
  };
}

// ------------------------------------------------------------------- one run
function run(arch, strategyKind, seed, cfg = {}) {
  const rnd = mulberry32(seed);
  const profile = new LearnerProfile('sim', {});
  const strat = makeStrategy(strategyKind, cfg);
  strat.init(profile);

  let trueAbility = arch.ability;
  const startAbility = trueAbility;
  let inBand = 0, correctCount = 0, hintCount = 0;
  const stateTally = {};
  const trace = [];

  for (let i = 0; i < ATTEMPTS; i++) {
    // Session boundary every SESSION_LEN attempts (one quest arc). The dial's
    // session-delta rail is anchored here; without this it never re-anchors.
    if (i % SESSION_LEN === 0 && strat.dial) strat.dial.startSession(SKILL);
    if (arch.gapAt && i === arch.gapAt) {
      profile.advanceDays(arch.gapDays);
      if (strat.dial) { strat.dial.reentry(SKILL, arch.gapDays); strat.dial.startSession(SKILL); }
    }
    const d = strat.next();
    // GROUND TRUTH: is this task actually in the learner's ZPD?
    const pTrue = pSuccess(trueAbility, d);
    if (pTrue >= BAND.lo && pTrue <= BAND.hi) inBand++;

    const out = attemptOutcome(arch, trueAbility, d, rnd);
    if (out.correct) correctCount++;
    if (out.rung > 0) hintCount++;

    profile.record(SKILL, { difficulty: d, correct: out.correct, rung: out.rung });
    strat.observe({ ...out, difficulty: d });
    if (strat.states) {
      const st = strat.states().dialState;
      stateTally[st] = (stateTally[st] || 0) + 1;
    }
    // ability lives on the same 0–100 scale as difficulty
    trueAbility = Math.min(95, trueAbility + learn(arch, trueAbility, d, out.correct));

    if (i % 10 === 0) trace.push({ i, d: +d.toFixed(1), theta: +profile.get(SKILL).theta.toFixed(1),
                                   truth: +trueAbility.toFixed(1), pTrue: +pTrue.toFixed(3) });
  }

  const s = profile.get(SKILL);
  return {
    archetype: arch.id,
    strategy: strat.name,
    inBandPct: +(100 * inBand / ATTEMPTS).toFixed(1),
    successPct: +(100 * correctCount / ATTEMPTS).toFixed(1),
    hintPct: +(100 * hintCount / ATTEMPTS).toFixed(1),
    thetaError: +Math.abs(s.theta - trueAbility).toFixed(1),
    theta: +s.theta.toFixed(1),
    trueAbility: +trueAbility.toFixed(1),
    abilityGain: +(trueAbility - startAbility).toFixed(1),
    pMastery: +s.p_mastery.toFixed(3),
    states: stateTally,
    trace,
  };
}

// --------------------------------------------------------------------- driver
export function runAll(cfg = {}, seeds = [11, 23, 37]) {
  const rows = [];
  for (const arch of ARCHETYPES) {
    for (const kind of ['dial', 'fixed', 'random']) {
      const reps = seeds.map((sd) => run(arch, kind, sd, cfg));
      const avg = (f) => +(reps.reduce((a, r) => a + f(r), 0) / reps.length).toFixed(1);
      const states = {};
      for (const r of reps) for (const [k, v] of Object.entries(r.states)) states[k] = (states[k] || 0) + v;
      rows.push({
        archetype: arch.id, label: arch.label, strategy: reps[0].strategy,
        inBandPct: avg((r) => r.inBandPct),
        successPct: avg((r) => r.successPct),
        hintPct: avg((r) => r.hintPct),
        thetaError: avg((r) => r.thetaError),
        abilityGain: avg((r) => r.abilityGain),
        states,
        trace: reps[0].trace,
      });
    }
  }
  return rows;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const rows = runAll();
  const pad = (s, n) => String(s).padEnd(n);
  console.log(pad('archetype', 16) + pad('strategy', 22) + pad('in-band%', 10) +
              pad('success%', 10) + pad('hint%', 8) + pad('θ error', 9) + 'gain');
  console.log('-'.repeat(84));
  for (const r of rows) {
    console.log(pad(r.archetype, 16) + pad(r.strategy, 22) + pad(r.inBandPct, 10) +
                pad(r.successPct, 10) + pad(r.hintPct, 8) + pad(r.thetaError, 9) + r.abilityGain);
  }
  const byStrat = {};
  for (const r of rows) (byStrat[r.strategy] ??= []).push(r.inBandPct);
  console.log('\nmean in-band % by strategy:');
  for (const [k, v] of Object.entries(byStrat))
    console.log(`  ${pad(k, 22)} ${(v.reduce((a, b) => a + b, 0) / v.length).toFixed(1)}%`);
  const dialStates = rows.filter((r) => r.strategy === 'ZPD dial')
    .reduce((acc, r) => { for (const [k, v] of Object.entries(r.states)) acc[k] = (acc[k] || 0) + v; return acc; }, {});
  console.log('\ndial state distribution:', dialStates);
}
