/**
 * Adversarial input and property tests.
 *
 * The soak pushes TIME; this pushes INPUTS. Everything here is either a value a
 * hostile or broken client could send, or a learner behaving in a way the happy
 * path never produces. A control plane that certifies people has to degrade
 * predictably, not corrupt itself.
 *
 * Failures are collected rather than thrown, so one bad case does not hide the
 * rest of the report.
 */
import { readFileSync } from 'node:fs';
import { LearnerProfile, pSuccess, SIGMA_MAX } from './lpa.mjs';
import { ZpdDial, classifyAffect, impliedSetpoint, DEFAULTS } from './dial.mjs';
import { SkillGraph } from './graph.mjs';
import { Sequencer } from './sequencer.mjs';
import { checkSkillGate, detectGuessSpam, detectHintFarming, scoreLevelTest } from './gates.mjs';

const fails = [];
const check = (name, fn) => {
  try { const r = fn(); if (r !== true) fails.push(`${name}: ${r}`); else console.log(`  ok  ${name}`); }
  catch (e) { fails.push(`${name}: THREW ${e.message}`); }
};
const finite = (o, keys) => keys.every((k) => Number.isFinite(o[k]));

const HOSTILE = [NaN, Infinity, -Infinity, undefined, null, 1e12, -1e12, 0, '42', {}, []];

/* ------------------------------------------------------- pure math ------- */
check('pSuccess stays in [0,1] for every hostile difficulty', () => {
  for (const d of HOSTILE) {
    const v = pSuccess(50, d);
    if (Number.isNaN(v)) continue;                 // NaN in, NaN out is honest
    if (v < 0 || v > 1) return `p=${v} for d=${String(d)}`;
  }
  return true;
});

check('pSuccess is monotonically decreasing in difficulty', () => {
  let prev = 1.0000001;
  for (let d = 0; d <= 100; d += 0.5) {
    const v = pSuccess(50, d);
    if (v > prev) return `not monotone at d=${d}`;
    prev = v;
  }
  return true;
});

check('closed-loop inversion never returns a non-finite setpoint', () => {
  for (const p of [0, 1, -1, 2, NaN, 0.5]) for (const d of [0, 100, -1e6, NaN]) {
    const v = impliedSetpoint(d, p);
    if (Number.isFinite(d) && Number.isFinite(p) && !Number.isFinite(v))
      return `implied=${v} for d=${d} p=${p}`;
  }
  return true;
});

check('affect scores stay in [0,1] for hostile signal windows', () => {
  for (const v of HOSTILE) {
    const a = classifyAffect({ pHat: v, latZ: v, latVarZ: v, hintRate: v, idleRate: v, abandon: v });
    if (Number.isNaN(a.boredom) || Number.isNaN(a.anxiety)) continue;
    if (a.boredom < 0 || a.boredom > 1 || a.anxiety < 0 || a.anxiety > 1)
      return `boredom=${a.boredom} anxiety=${a.anxiety} for ${String(v)}`;
  }
  return true;
});

/* ------------------------------------------------- profile robustness ---- */
check('record() never corrupts the profile, whatever it is fed', () => {
  const p = new LearnerProfile('fuzz');
  for (const d of HOSTILE) for (const rung of [-5, 0, 3, 99, NaN]) for (const correct of [true, false]) {
    p.record('s', { difficulty: d, correct, rung });
    const s = p.get('s');
    if (!finite(s, ['theta', 'sigma', 'p_mastery']))
      return `theta=${s.theta} sigma=${s.sigma} mastery=${s.p_mastery} after d=${String(d)} rung=${rung}`;
    if (s.theta < 0 || s.theta > 100) return `theta escaped scale: ${s.theta}`;
    if (s.p_mastery < 0 || s.p_mastery > 1) return `mastery out of range: ${s.p_mastery}`;
    if (s.sigma < 0 || s.sigma > SIGMA_MAX + 1e-9) return `sigma out of range: ${s.sigma}`;
  }
  return true;
});

check('an out-of-range hint rung cannot mint extra credit', () => {
  const a = new LearnerProfile('a'), b = new LearnerProfile('b');
  const hi = a.record('s', { difficulty: 50, correct: true, rung: 99 });
  const lo = b.record('s', { difficulty: 50, correct: true, rung: 5 });
  return Math.abs(hi.outcome - lo.outcome) < 1e-9 ? true
    : `rung 99 gave outcome ${hi.outcome}, rung 5 gave ${lo.outcome}`;
});

/* ---------------------------------------------------- dial robustness ---- */
check('observe() survives malformed attempt records', () => {
  const p = new LearnerProfile('d'); const d = new ZpdDial(p);
  const junk = [{}, { correct: 'yes' }, { correct: true, rung: NaN, latZ: NaN },
                { correct: false, difficulty: Infinity }, { correct: true, latZ: 'x' }];
  for (let i = 0; i < 40; i++) d.observe('s', junk[i % junk.length]);
  const c = d.setpoint('s');
  return Number.isFinite(c) ? true : `setpoint became ${c}`;
});

check('setpoint honours the theta rail under hostile stored intent', () => {
  const p = new LearnerProfile('r'); const s = p.get('s'); s.theta = 50;
  const d = new ZpdDial(p); const st = d.state('s');
  for (const c of [1e9, -1e9, NaN, Infinity]) {
    st.c = c; st.sessionStart = 50;
    const v = d.setpoint('s');
    if (Number.isNaN(c) || !Number.isFinite(c)) { if (Number.isFinite(v) === false && !Number.isNaN(v)) return `setpoint ${v}`; continue; }
    if (v < 50 + DEFAULTS.railLo - 1e-9 || v > 50 + DEFAULTS.railHi + 1e-9)
      return `setpoint ${v} escaped rails for c=${c}`;
  }
  return true;
});

/* --------------------------------------------------- graph robustness ---- */
check('propagate() on unknown skills is a no-op, not a crash', () => {
  const g = new SkillGraph([{ skill_id: 'a', requires: ['ghost'], supports: [], interferes: [] }]);
  const p = new LearnerProfile('g');
  const moved = g.propagate(p, 'a', 1, { correct: true });
  if (moved.some((m) => m.skill === 'ghost')) return 'propagated into a non-existent node';
  const none = g.propagate(p, 'also-missing', 1, { correct: true });
  return Array.isArray(none) ? true : 'propagate on unknown source did not return a list';
});

check('a cyclic prerequisite graph does not hang readiness or leverage', () => {
  const g = new SkillGraph([
    { skill_id: 'x', requires: ['y'], supports: [], interferes: [] },
    { skill_id: 'y', requires: ['x'], supports: [], interferes: [] },
  ]);
  const p = new LearnerProfile('c');
  const t0 = Date.now();
  const ready = g.ready('x', p);
  const lev = g.leverage('x', p);
  const dx = g.diagnose('x', p);
  if (Date.now() - t0 > 2000) return 'took too long — likely traversing the cycle';
  return (ready === false && Number.isFinite(lev) && dx.cause) ? true
    : `ready=${ready} leverage=${lev} diagnose=${JSON.stringify(dx)}`;
});

/* --------------------------------------------------- gates robustness ---- */
check('gates on empty or malformed history refuse rather than certify', () => {
  const p = new LearnerProfile('gt'); const s = p.get('s'); s.theta = 50; s.p_mastery = 0.99;
  if (checkSkillGate(p, 's', []).pass) return 'certified on empty history';
  if (checkSkillGate(p, 's', [null, undefined, {}, { skill: 's' }].filter(Boolean)).pass)
    return 'certified on malformed history';
  return true;
});

check('level test scoring handles empty and oversized answer sets', () => {
  const e = scoreLevelTest([]);
  if (Number.isFinite(e.pct) === false && !Number.isNaN(e.pct)) return `pct=${e.pct}`;
  const big = scoreLevelTest(Array(1000).fill(true));
  return big.pass === true ? true : 'a perfect oversized sitting should still pass';
});

check('anti-gaming detectors do not fire on well-behaved histories', () => {
  const good = Array.from({ length: 20 }, () => ({ correct: true, rung: 0, retryGapSec: 40 }));
  if (detectGuessSpam(good)) return 'guess-spam fired on clean history';
  if (detectHintFarming(good)) return 'hint farming fired on clean history';
  return true;
});

/* ------------------------------------------- adversarial learner shapes -- */
const all = JSON.parse(readFileSync(new URL('../pack/registry/skills.json', import.meta.url))).skills;
const skills = all.filter((s) => s.union === 'welders');
const ids = skills.map((s) => s.skill_id);

function runLearner(kind, steps = 600) {
  const g = new SkillGraph(skills);
  const p = new LearnerProfile(kind);
  for (const id of ids) p.get(id);
  let day = 0;
  const d = new ZpdDial(p);
  const seq = new Sequencer(g, p, d, { clock: () => day });
  const hist = [];
  for (let i = 0; i < steps; i++) {
    day = Math.floor(i / 6);
    if (i % 25 === 0) for (const k of d.perSkill.keys()) d.startSession(k);
    if (kind === 'absent' && i === 300) { p.advanceDays(180); day += 180; }
    const pick = seq.next(ids, hist);
    if (!pick) break;
    let correct = false, rung = 0;
    if (kind === 'always-fail') correct = false;
    else if (kind === 'guess-spam') { correct = Math.random() < 0.2; }
    else if (kind === 'hint-farm') { rung = 5; correct = true; }
    else correct = Math.random() < 0.75;
    p.record(pick.skill, { difficulty: pick.difficulty, correct, rung,
                           guessSpam: kind === 'guess-spam' });
    d.observe(pick.skill, { correct, rung, latZ: 0, difficulty: pick.difficulty });
    seq.record(pick.skill, { correct, mode: pick.mode });
    checkSkillGate(p, pick.skill, hist);
    hist.push({ skill: pick.skill, correct, rung, difficulty: pick.difficulty,
                mode: pick.mode, gate_qualifying: pick.mode === 'verify' });
  }
  return { p, d, seq, hist };
}

for (const kind of ['always-fail', 'guess-spam', 'hint-farm', 'absent']) {
  check(`adversarial learner "${kind}" keeps the profile sane`, () => {
    const { p, d, hist } = runLearner(kind);
    if (!hist.length) return 'produced no attempts at all';
    for (const id of ids) {
      const s = p.get(id);
      if (!finite(s, ['theta', 'sigma', 'p_mastery'])) return `${id} corrupted: ${JSON.stringify(s).slice(0, 120)}`;
      if (s.theta < 0 || s.theta > 100) return `${id} theta ${s.theta}`;
    }
    for (const [, st] of d.perSkill) if (!Number.isFinite(st.c)) return 'dial intent became non-finite';
    return true;
  });
}

check('a learner who never succeeds is never certified', () => {
  const { p } = runLearner('always-fail');
  const gated = ids.filter((id) => p.get(id).gated_at !== undefined);
  return gated.length === 0 ? true : `certified ${gated.length} skills on zero successes`;
});

check('hint farming cannot buy certification', () => {
  const { p } = runLearner('hint-farm');
  const gated = ids.filter((id) => p.get(id).gated_at !== undefined);
  return gated.length === 0 ? true
    : `certified ${gated.length} skills while taking rung-5 help on every attempt`;
});

check('a learner who fails everything is eased downward, not upward', () => {
  const { p, d } = runLearner('always-fail');
  const worked = [...d.perSkill.keys()];
  for (const id of worked) {
    const s = p.get(id);
    const c = d.setpoint(id);
    if (c > s.theta) return `${id}: setpoint ${c.toFixed(1)} above theta ${s.theta.toFixed(1)}`;
  }
  return true;
});

check('six months away widens uncertainty rather than losing the learner', () => {
  const { p, seq } = runLearner('absent');
  const touched = [...seq.servedCount.keys()];
  if (!touched.length) return 'no skills served';
  const anyWidened = touched.some((id) => p.get(id).sigma > 3.5);
  return anyWidened ? true : 'no skill regained uncertainty after a 180-day gap';
});

if (fails.length) {
  console.log('\nFAILURES:');
  for (const f of fails) console.log('  ✗ ' + f);
  process.exit(1);
}
console.log(`\nall fuzz and adversarial checks passed.`);
