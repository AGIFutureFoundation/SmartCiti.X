/**
 * ACP-15 validation — multi-skill curriculum simulation.
 *
 * Isolates SEQUENCING: all three strategies use the same ZPD dial for
 * difficulty, so any difference is the choice of skill, not the choice of
 * challenge level.
 *
 * Strategies
 *   graph   : the ACP-05 sequencer (readiness, leverage, review, interleaving,
 *             wheel-spin diagnosis)
 *   blocked : the traditional curriculum — skills in prerequisite order, one
 *             worked to mastery before the next. Also respects prerequisites,
 *             so graph-vs-blocked isolates interleaving + spacing + diagnosis.
 *   flat    : any unmastered skill at random, prerequisites ignored (control)
 *
 * LEARNER MODEL ASSUMPTIONS — stated, not hidden. These are the platform's
 * pedagogical beliefs; the simulation tests whether the sequencer converts
 * them into outcomes, and produces no evidence that the beliefs are true:
 *   A1 practice on a skill whose prerequisites are unmet yields little (0.25x)
 *   A2 what is learned decays with time since practice, and each successful
 *      spaced retrieval lengthens that half-life
 *   A3 a confusable pair practised back-to-back is learned less cleanly
 */
import { LearnerProfile, pSuccess } from './lpa.mjs';
import { ZpdDial } from './dial.mjs';
import { SkillGraph } from './graph.mjs';
import { Sequencer } from './sequencer.mjs';
import { checkSkillGate } from './gates.mjs';
import { readFileSync } from 'node:fs';

const ATTEMPTS = 420, PER_DAY = 6, SESSION_LEN = 25;
const LEARNED = 6;   // ability points above baseline that count as 'learned'
const RETENTION_PROBE_DAYS = 30;

function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function loadUnionGraph(union = 'welders', regPath = '../pack/registry/skills.json') {
  const all = JSON.parse(readFileSync(new URL(regPath, import.meta.url))).skills;
  const mine = all.filter((s) => s.union === union);
  return { graph: new SkillGraph(mine), skillIds: mine.map((s) => s.skill_id) };
}

/** Ground-truth learner: true ability per skill, with decay and prereq gating. */
class TrueLearner {
  constructor(skillIds, graph, rnd, { base = 30, learnRate = 0.8 } = {}) {
    this.g = graph;
    this.rnd = rnd;
    this.learnRate = learnRate;
    this.state = new Map();
    for (const id of skillIds) {
      this.state.set(id, { base: base + (rnd() - 0.5) * 10, learned: 0, hl: 10, last: 0, wins: 0 });
    }
  }

  /** Effective ability now = base + learned, decayed since last practice (A2). */
  ability(id, day) {
    const s = this.state.get(id);
    const retention = Math.pow(2, -(day - s.last) / s.hl);
    return s.base + s.learned * retention;
  }

  /** Fraction of what was learned that survives to `day` — the retention metric. */
  retention(id, day) {
    const s = this.state.get(id);
    if (s.learned <= 0) return null;
    return Math.pow(2, -(day - s.last) / s.hl);
  }

  prereqReadiness(id) {
    const reqs = this.g.requires(id);
    if (!reqs.length) return 1;
    // proportion of prerequisites the learner has genuinely learned
    const got = reqs.filter((p) => this.state.get(p) && this.state.get(p).learned > LEARNED).length;
    return got / reqs.length;
  }

  practise(id, difficulty, day, recentSkills) {
    const s = this.state.get(id);
    const ability = this.ability(id, day);
    const p = pSuccess(ability, difficulty);
    const correct = this.rnd() < p;

    // A1: unmet prerequisites throttle learning
    const readiness = this.prereqReadiness(id);
    const prereqFactor = 0.25 + 0.75 * readiness;
    // A3: a confusable pair practised back-to-back is learned less cleanly
    const conf = new Set(this.g.interferes(id));
    const interference = recentSkills.slice(-2).some((r) => conf.has(r)) ? 0.75 : 1;
    // learning peaks at moderate challenge
    const shape = Math.exp(-((p - 0.75) ** 2) / (2 * 0.22 ** 2));
    const gain = this.learnRate * shape * (correct ? 1 : 0.6) * prereqFactor * interference;

    // A2: spaced retrieval lengthens the half-life; cramming does not
    const gapDays = day - s.last;
    if (correct) {
      s.wins += 1;
      s.hl = gapDays >= 1 ? Math.min(160, s.hl * 1.9) : Math.min(160, s.hl * 1.03);
    } else {
      s.hl = Math.max(3, s.hl * 0.75);
    }
    // decay is realised at practice time, then the gain is added
    s.learned = s.learned * Math.pow(2, -gapDays / s.hl) + gain;
    s.last = day;
    return { correct, p, ability };
  }
}

/* ------------------------------------------------------------- strategies */
function makePicker(kind, { graph, skillIds, profile, dial, seq, rnd }) {
  if (kind === 'graph') {
    return (history) => seq.next(skillIds, history);
  }
  if (kind === 'blocked') {
    let i = 0;
    // prerequisite order: fundamentals -> applied -> mastery within each strand
    const order = [...skillIds].sort((a, b) => rank(a) - rank(b));
    return () => {
      while (i < order.length) {
        const id = order[i];
        const st = profile.get(id);
        if (st.p_mastery >= 0.95 || (seq.servedCount.get(id) ?? 0) >= 30) { i++; continue; }
        return { skill: id, difficulty: dial.setpoint(id), mode: 'blocked' };
      }
      const id = order[order.length - 1];
      return { skill: id, difficulty: dial.setpoint(id), mode: 'blocked' };
    };
  }
  return () => {
    const open = skillIds.filter((id) => profile.get(id).p_mastery < 0.95);
    const id = (open.length ? open : skillIds)[Math.floor(rnd() * (open.length || skillIds.length))];
    return { skill: id, difficulty: dial.setpoint(id), mode: 'flat' };
  };
}
const TIER_RANK = { fundamentals: 0, applied: 1, mastery: 2 };
const rank = (id) => TIER_RANK[id.split('.').pop()] ?? 0;

/* ------------------------------------------------------------------- run  */
export function run(kind, seed, { union = 'welders' } = {}) {
  const rnd = mulberry32(seed);
  const { graph, skillIds } = loadUnionGraph(union);
  const profile = new LearnerProfile(`sim-${kind}`);
  for (const id of skillIds) profile.get(id);            // materialise the graph
  let day = 0;
  const dial = new ZpdDial(profile);
  const seq = new Sequencer(graph, profile, dial, { clock: () => day });
  const truth = new TrueLearner(skillIds, graph, rnd);
  const pick = makePicker(kind, { graph, skillIds, profile, dial, seq, rnd });

  const history = [];
  const recent = [];
  let prereqViolations = 0, remediations = 0, reviews = 0, verifies = 0;

  for (let i = 0; i < ATTEMPTS; i++) {
    day = Math.floor(i / PER_DAY);
    const p = pick(history);
    if (!p) break;
    if (i % SESSION_LEN === 0) dial.startSession(p.skill);
    if (p.mode === 'remediation') remediations++;
    if (p.mode === 'review') reviews++;
    if (p.mode === 'verify') verifies++;
    if (truth.prereqReadiness(p.skill) < 1) prereqViolations++;

    const out = truth.practise(p.skill, p.difficulty, day, recent);
    const w = graph.interferenceWeight(p.skill, recent);
    const rec = profile.record(p.skill, { difficulty: p.difficulty, correct: out.correct, rung: 0, weight: w });
    graph.propagate(profile, p.skill, rec.delta, { correct: out.correct });
    dial.observe(p.skill, { correct: out.correct, rung: 0, latZ: 0, difficulty: p.difficulty });
    seq.record(p.skill, { correct: out.correct, mode: p.mode });

    recent.push(p.skill);
    if (recent.length > 6) recent.shift();
    checkSkillGate(profile, p.skill, history);   // award on satisfaction, in flight
    history.push({ skill: p.skill, correct: out.correct, rung: 0, difficulty: p.difficulty,
                   mode: p.mode,
                   // stamped now, against the theta that was current when served
                   gate_qualifying: p.mode === 'verify' });
  }

  // outcomes
  const gated = skillIds.filter((id) => checkSkillGate(profile, id, history).pass).length;
  const learnedSkills = skillIds.filter((id) => truth.state.get(id).learned > LEARNED);
  const probeDay = day + RETENTION_PROBE_DAYS;
  const retentions = learnedSkills.map((id) => truth.retention(id, probeDay)).filter((x) => x !== null);
  const meanRetention = retentions.length
    ? retentions.reduce((a, b) => a + b, 0) / retentions.length : 0;
  const totalLearned = skillIds.reduce((a, id) => a + truth.state.get(id).learned, 0);

  return {
    strategy: kind,
    skillsGated: gated,
    skillsLearned: learnedSkills.length,
    totalAbilityGained: +totalLearned.toFixed(1),
    retentionAt30d: +meanRetention.toFixed(3),
    prereqViolationPct: +(100 * prereqViolations / ATTEMPTS).toFixed(1),
    remediations,
    reviews,
    verifies,
    distinctSkillsTouched: new Set(history.map((h) => h.skill)).size,
  };
}

export function runAll(seeds = [3, 11, 29]) {
  const rows = [];
  for (const kind of ['graph', 'blocked', 'flat']) {
    const reps = seeds.map((s) => run(kind, s));
    const avg = (f) => +(reps.reduce((a, r) => a + f(r), 0) / reps.length).toFixed(2);
    rows.push({
      strategy: kind,
      skillsGated: avg((r) => r.skillsGated),
      skillsLearned: avg((r) => r.skillsLearned),
      totalAbilityGained: avg((r) => r.totalAbilityGained),
      retentionAt30d: avg((r) => r.retentionAt30d),
      prereqViolationPct: avg((r) => r.prereqViolationPct),
      remediations: avg((r) => r.remediations),
      reviews: avg((r) => r.reviews),
      verifies: avg((r) => r.verifies),
      distinctSkillsTouched: avg((r) => r.distinctSkillsTouched),
    });
  }
  return rows;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const rows = runAll();
  const pad = (s, n) => String(s).padEnd(n);
  console.log(pad('strategy', 10) + pad('gated', 8) + pad('learned', 9) + pad('ability', 9) +
              pad('retain30d', 11) + pad('prereq-viol%', 14) + pad('remed', 7) + pad('reviews', 9) + 'verify');
  console.log('-'.repeat(80));
  for (const r of rows)
    console.log(pad(r.strategy, 10) + pad(r.skillsGated, 8) + pad(r.skillsLearned, 9) +
                pad(r.totalAbilityGained, 9) + pad(r.retentionAt30d, 11) +
                pad(r.prereqViolationPct, 14) + pad(r.remediations, 7) + pad(r.reviews, 9) + r.verifies);
}
