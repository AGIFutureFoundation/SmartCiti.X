/** ACP-15 tests: graph tracing, sequencing, gates. */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { LearnerProfile } from './lpa.mjs';
import { ZpdDial } from './dial.mjs';
import { SkillGraph, TRANSFER } from './graph.mjs';
import { Sequencer, POLICY } from './sequencer.mjs';
import { checkSkillGate, revokeSkillGate, scoreLevelTest, scoreJobsiteFinal,
         certified, detectGuessSpam, detectHintFarming, GATE } from './gates.mjs';
import { runAll } from './sim_curriculum.mjs';

let n = 0; const ok = (m) => { n++; console.log(`  ok  ${m}`); };
const all = JSON.parse(readFileSync(new URL('../pack/registry/skills.json', import.meta.url))).skills;
const skills = all.filter((s) => s.union === 'welders');
const g = new SkillGraph(skills);
const ids = skills.map((s) => s.skill_id);

/* -------------------------------------------------------------- graph ---- */
assert.ok(g.node('welders.safety.fundamentals'));
assert.equal(g.requires('welders.safety.fundamentals').length, 0, 'safety fundamentals is a root');
assert.ok(g.requires('welders.layout.fundamentals').includes('welders.safety.fundamentals'));
ok(`graph: ${ids.length} nodes, safety fundamentals is the root everything rests on`);

const p = new LearnerProfile('g');
for (const id of ids) p.get(id);
assert.equal(g.ready('welders.safety.fundamentals', p), true);
assert.equal(g.ready('welders.layout.applied', p), false, 'unmet prerequisites must block');
p.get('welders.layout.fundamentals').p_mastery = 0.9;
assert.equal(g.ready('welders.layout.applied', p), true);
ok('readiness gates on prerequisite mastery and opens when it is met');

/* --------------------------------------------------- credit propagation -- */
const before = p.get('welders.safety.fundamentals').theta;
const moved = g.propagate(p, 'welders.layout.fundamentals', +3, { correct: true });
const after = p.get('welders.safety.fundamentals').theta;
assert.ok(after > before, 'success on a child should lift its prerequisite');
assert.ok(after - before < 3 * 0.5, 'propagated credit must be heavily damped');
assert.ok(moved.every((m) => m.why), 'every propagated change carries a reason');
ok(`credit propagates to prerequisites, damped ${TRANSFER.toPrereq}x, each with a why`);

// indirect evidence must not shrink uncertainty like direct evidence does
const p2 = new LearnerProfile('h'); for (const id of ids) p2.get(id);
const sigDirect0 = p2.get('welders.safety.fundamentals').sigma;
p2.record('welders.safety.fundamentals', { difficulty: 30, correct: true, rung: 0 });
const dropDirect = sigDirect0 - p2.get('welders.safety.fundamentals').sigma;
const p3 = new LearnerProfile('i'); for (const id of ids) p3.get(id);
const sigInd0 = p3.get('welders.safety.fundamentals').sigma;
g.propagate(p3, 'welders.layout.fundamentals', +3, { correct: true });
const dropIndirect = sigInd0 - p3.get('welders.safety.fundamentals').sigma;
assert.ok(dropIndirect < dropDirect,
  'indirect evidence must reduce uncertainty far less than direct evidence');
ok('indirect evidence never masquerades as direct: sigma barely moves');

/* ---------------------------------------------------------- interference - */
const confSkill = skills.find((s) => s.interferes.length)?.skill_id;
if (confSkill) {
  const other = g.interferes(confSkill)[0];
  assert.equal(g.interferenceWeight(confSkill, [other]), 0.6);
  assert.equal(g.interferenceWeight(confSkill, ['welders.safety.fundamentals']), 1);
  ok('confusable pairs served back-to-back get their evidence discounted');
}

/* ------------------------------------------------------------- diagnosis - */
const p4 = new LearnerProfile('j'); for (const id of ids) p4.get(id);
p4.get('welders.safety.fundamentals').p_mastery = 0.4;
const dx = g.diagnose('welders.layout.fundamentals', p4);
assert.equal(dx.cause, 'prerequisite');
assert.equal(dx.skill, 'welders.safety.fundamentals');
ok('a stuck skill is diagnosed to the weakest prerequisite, not blamed on the learner');

/* --------------------------------------------------------------- gates --- */
const p5 = new LearnerProfile('k');
const s5 = p5.get('s'); s5.theta = 50; s5.p_mastery = 0.96;
const hist = [
  { skill: 's', correct: true, rung: 0, difficulty: 45, gate_qualifying: true },
  { skill: 's', correct: true, rung: 0, difficulty: 30, gate_qualifying: false }, // practice
  { skill: 's', correct: true, rung: 0, difficulty: 45, gate_qualifying: true },
  { skill: 's', correct: true, rung: 0, difficulty: 45, gate_qualifying: true },
];
assert.equal(checkSkillGate(p5, 's', hist).pass, true,
  'practice between demonstrations must not break the streak');
ok('gate counts qualifying demonstrations; intervening practice does not break it');

// theta moving must not retroactively disqualify past demonstrations
s5.theta = 70;
assert.equal(checkSkillGate(p5, 's', hist).pass, true, 'award must survive theta moving');
ok('improvement never retroactively invalidates the evidence for it');

// a later bad re-test does not silently un-certify
const bad = [...hist, { skill: 's', correct: false, rung: 0, difficulty: 65, gate_qualifying: true }];
assert.equal(checkSkillGate(p5, 's', bad).pass, true, 'a query must not revoke an award');
assert.equal(revokeSkillGate(p5, 's', 'failed recertification').revoked, true);
assert.equal(checkSkillGate(p5, 's', bad).pass, false, 'revocation is deliberate and does apply');
ok('certification is an awarded event; revocation is deliberate and logged');

// belief alone never certifies
const p6 = new LearnerProfile('l'); const s6 = p6.get('s'); s6.theta = 50; s6.p_mastery = 0.99;
assert.equal(checkSkillGate(p6, 's', []).pass, false, 'BKT alone must never certify');
ok('mastery belief alone never certifies — performance must confirm');

/* ------------------------------------------------- mastery needs evidence */
const p7 = new LearnerProfile('m');
for (let i = 0; i < 3; i++) p7.record('s', { difficulty: 20, correct: true, rung: 0 });
const thin = p7.get('s');
assert.ok(thin.p_mastery_raw > 0.9, 'raw posterior rises fast on easy wins');
assert.ok(thin.p_mastery < 0.7, `a 3-observation belief must not read as mastery (got ${thin.p_mastery.toFixed(2)})`);
ok(`mastery is shrunk by evidence volume: raw ${thin.p_mastery_raw.toFixed(2)} reported as ${thin.p_mastery.toFixed(2)} on n=3`);

/* ----------------------------------------------------------- anti-gaming - */
assert.equal(detectGuessSpam([
  { correct: false, retryGapSec: 1 }, { correct: false, retryGapSec: 2 }, { correct: false, retryGapSec: 1 },
]), true);
assert.equal(detectGuessSpam([
  { correct: false, retryGapSec: 30 }, { correct: false, retryGapSec: 25 }, { correct: false, retryGapSec: 40 },
]), false, 'slow, considered retries are not guess-spam');
ok('guess-spam detected on rapid retries, not on slow considered ones');

assert.equal(detectHintFarming(Array(20).fill({ rung: 5 })), true);
assert.equal(detectHintFarming(Array(20).fill({ rung: 1 })), false);
ok('hint farming detected on rung depth, not on asking for help');

assert.equal(scoreLevelTest(Array(33).fill(true).map((_, i) => i < 27)).pass, true);
assert.equal(scoreLevelTest(Array(33).fill(true).map((_, i) => i < 20)).pass, false);
assert.equal(scoreJobsiteFinal({ stepOrder: 1, safetyViolations: 1, timeWithinTolerance: true,
  oralAnswers: [true, true, true] }).pass, false, 'a safety violation is disqualifying');
ok('level test and jobsite final score correctly; safety violations disqualify');

/* -------------------------------------------------------------- sequencer */
const p8 = new LearnerProfile('n'); for (const id of ids) p8.get(id);
const d8 = new ZpdDial(p8);
let day = 0;
const seq = new Sequencer(g, p8, d8, { clock: () => day });
const picks = [];
for (let i = 0; i < 60; i++) {
  day = Math.floor(i / 6);
  const pick = seq.next(ids, []);
  assert.ok(pick && pick.why, 'every pick must defend itself with a why');
  picks.push(pick);
  p8.record(pick.skill, { difficulty: pick.difficulty, correct: true, rung: 0 });
  d8.observe(pick.skill, { correct: true, rung: 0, latZ: 0, difficulty: pick.difficulty });
  seq.record(pick.skill, { correct: true, mode: pick.mode });
}
// prerequisite discipline: never serve a skill whose prerequisites are unmet
for (const pk of picks) {
  if (pk.mode === 'calibrating' || pk.mode === 'remediation') continue;
  assert.ok(g.ready(pk.skill, p8) || seq.workingSet.has(pk.skill),
    `served ${pk.skill} with unmet prerequisites`);
}
ok(`sequencer served ${picks.length} picks, every one with a reason and prerequisite-respecting`);

assert.ok(seq.workingSet.size <= POLICY.workingSetMax,
  `working set ${seq.workingSet.size} exceeds the cap`);
ok(`working set stays capped at ${POLICY.workingSetMax} — unbounded interleaving is thrashing`);

// Interleaving constraint — only checkable where an alternative existed.
// Early in a graph a single root skill gates everything, and a long run on it
// is correct behaviour, not a violation.
let maxRun = 1, run = 1, checked = 0;
for (let i = 1; i < picks.length; i++) {
  run = picks[i].skill === picks[i - 1].skill ? run + 1 : 1;
  if ((picks[i].poolSize ?? 1) >= 2) { maxRun = Math.max(maxRun, run); checked++; }
}
assert.ok(checked > 0, 'never had a choice to interleave with — test is vacuous');
assert.ok(maxRun <= POLICY.maxConsecutiveSameSkill + 1,
  `ran ${maxRun} consecutive attempts on one skill with alternatives available`);
ok(`interleaving holds where alternatives exist: max ${maxRun} in a row over ${checked} such picks`);

/* ------------------------------------------------------- the headline ---- */
const rows = runAll();
const graph = rows.find((r) => r.strategy === 'graph');
const blocked = rows.find((r) => r.strategy === 'blocked');
const flat = rows.find((r) => r.strategy === 'flat');
assert.ok(graph.prereqViolationPct < 20 && flat.prereqViolationPct > 50,
  'graph sequencing must respect prerequisites where flat does not');
ok(`prerequisite discipline: graph ${graph.prereqViolationPct}% violations vs flat ${flat.prereqViolationPct}%`);
assert.ok(graph.skillsGated > 0 && blocked.skillsGated === 0,
  'only a sequencer that serves verification can certify anyone');
ok(`only the graph sequencer certifies: ${graph.skillsGated} skills gated vs 0 for both baselines`);
assert.ok(graph.retentionAt30d > blocked.retentionAt30d * 1.5,
  'spaced review should retain markedly better than massed practice');
ok(`retention at 30 days: graph ${graph.retentionAt30d} vs blocked ${blocked.retentionAt30d}`);

console.log(`\n${n} checks passed.`);
