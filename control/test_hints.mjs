/**
 * ACP-04 — the hint engine, and the ceiling contract between the sequencer,
 * the engine and the mentor.
 */
import { LearnerProfile } from './lpa.mjs';
import { ZpdDial } from './dial.mjs';
import { Sequencer } from './sequencer.mjs';
import { SkillGraph } from './graph.mjs';
import { HintEngine, RUNGS, masteryCeiling, ceilingFor, creditFor, isConceptual } from './hints.mjs';
import { compliant, overHelper } from '../fabric/stubs.mjs';

let n = 0;
const ok = (label, cond) => { if (!cond) { console.error('FAIL', label); process.exit(1); } n++; console.log('  ok ', label); };
const near = (a, b, eps = 1e-9) => Math.abs(a - b) < eps;

/* ---------------------------------------------------------- the ladder ---- */
ok('the ladder credit schedule matches the dial\'s hint discount exactly',
  RUNGS.every((r) => near(r.credit, 1 - 0.15 * r.rung)));

ok('deeper help is always worth strictly less',
  RUNGS.every((r, i) => i === 0 || r.credit < RUNGS[i - 1].credit));

/* ---------------------------------------------------------- fading -------- */
ok('the ceiling falls as mastery rises, and closes entirely at 0.95',
  masteryCeiling(0.2) === 5 && masteryCeiling(0.6) === 3
  && masteryCeiling(0.85) === 1 && masteryCeiling(0.96) === 0);

ok('mode and mastery are independent bounds and the tighter one wins',
  ceilingFor({ pMastery: 0.2, taskCeiling: 0 }) === 0
  && ceilingFor({ pMastery: 0.96, taskCeiling: 5 }) === 0
  && ceilingFor({ pMastery: 0.6, taskCeiling: 5 }) === 3);

ok('a fading contract takes one rung off whatever the other bounds allow',
  ceilingFor({ pMastery: 0.2, fadeContract: 3 }) === 4
  && ceilingFor({ pMastery: 0.85, fadeContract: 3 }) === 0);

/* ------------------------------------------------------- dwell guard ------ */
{
  const p = (() => { const q = new LearnerProfile('t'); q.get('rigging.sling-angle'); return q; })();
  const h = new HintEngine(p);
  const fast = h.request('rigging.sling-angle', { rung: 1, dwellSeconds: 3 });
  const patient = h.request('rigging.sling-angle', { rung: 1, dwellSeconds: 25 });
  ok('lever-mashing is refused with a reason, patience is granted',
    fast.granted === 0 && fast.refused === 'dwell' && patient.granted === 1);
  ok('the refusal explains itself rather than failing silently',
    /seconds/.test(fast.why) && fast.why.length > 20);
}

/* --------------------------------------------- verification is hint-free -- */
{
  const p = (() => { const q = new LearnerProfile('t'); q.get('rigging.sling-angle'); return q; })();
  const s = p.get('rigging.sling-angle');
  s.p_mastery = 0.88;                        // in the window where rung 1 is allowed
  const h = new HintEngine(p);
  const practice = h.request('rigging.sling-angle', { rung: 3, taskCeiling: null });
  const verify = h.request('rigging.sling-angle', { rung: 1, taskCeiling: 0 });
  ok('at 0.88 mastery practice still gets rung 1, but a verification run gets nothing',
    practice.granted === 1 && verify.granted === 0 && verify.refused === 'verification');
  ok('the verification refusal tells the learner why the check is bare',
    /check/.test(verify.why));
}

/* ------------------------------------------------- the fading contract ---- */
{
  const p = (() => { const q = new LearnerProfile('t'); q.get('rigging.load-calc'); return q; })();
  const h = new HintEngine(p);
  let opened = null;
  for (let i = 0; i < 20; i++) opened = h.record('rigging.load-calc', { rung: i % 2 ? 1 : 0 }) ?? opened;
  ok('sustained dependence above 0.35 opens a fading contract, named out loud',
    opened && opened.action === 'fading_contract' && opened.dependence >= 0.35
    && /hint on/.test(opened.why));
  const under = h.request('rigging.load-calc', { rung: 5 });
  ok('the contract serves one rung lower than asked, and says so',
    under.granted === 4 && under.contract === true);
  ok('the contract expires after its three tasks rather than persisting',
    (() => { h.request('rigging.load-calc', { rung: 5 }); h.request('rigging.load-calc', { rung: 5 });
             return h.request('rigging.load-calc', { rung: 5 }).granted === 5; })());
}

{
  const p = (() => { const q = new LearnerProfile('t'); q.get('rigging.load-calc'); return q; })();
  const h = new HintEngine(p);
  let opened = null;
  for (let i = 0; i < 20; i++) opened = h.record('rigging.load-calc', { rung: i < 6 ? 1 : 0 }) ?? opened;
  ok('a learner at 30% dependence is left alone — the contract is for a real pattern',
    opened === null);
}

/* ---------------------------------------------------- Socratic handoff ---- */
{
  const p = (() => { const q = new LearnerProfile('t'); q.get('rigging.load-calc'); q.get('welding.bead-motor'); return q; })();
  const h = new HintEngine(p);
  const conceptual = h.request('rigging.load-calc', { rung: 2 });
  const motor = h.request('welding.bead-motor', { rung: 2 });
  ok('a rung-2 escalation on a conceptual skill opens a bounded dialogue',
    conceptual.socratic === true && conceptual.maxTurns === 6);
  ok('motor skills get demonstration, never dialogue',
    isConceptual('welding.bead-motor') === false && motor.socratic === false);
}

/* ------------------------------------- the ceiling contract, end to end --- */
{
  const skills = [
    { skill_id: 'a', base_difficulty: 50, edges: [] },
    { skill_id: 'b', base_difficulty: 55, edges: [{ to: 'a', type: 'requires' }] },
  ];
  const g = new SkillGraph(skills);
  const p = (() => { const q = new LearnerProfile('t'); for (const s of skills) q.get(s.skill_id); return q; })();
  const dial = new ZpdDial(p);
  const seq = new Sequencer(g, p, dial);
  p.get('a').p_mastery = 0.85;
  p.get('a').evidence_n = 20;
  const pick = seq.next(['a', 'b'], []);
  ok('every served task now carries a scaffold ceiling, not just verification picks',
    pick && pick.scaffold_ceiling !== undefined);
  ok('the stamped ceiling reflects the learner\'s mastery on that skill',
    pick.scaffold_ceiling === masteryCeiling(p.get(pick.skill).p_mastery));
}

/* ------------------------------------- the mentor's fallback fails closed - */
{
  const unstamped = await overHelper().turn('help me', { task: 'hint', requested_rung: 1 });
  ok('an unstamped ceiling gives no help at all, rather than the whole ladder',
    unstamped.rung === 0);
  const stamped = await overHelper().turn('help me', { task: 'hint', requested_rung: 1, scaffold_ceiling: 3 });
  ok('a stamped ceiling is honoured normally',
    stamped.rung > 0 && stamped.rung <= 3);
  ok('the over-help is still recorded even when the clamp swallows it',
    unstamped.over_helped === true);
}

/* ------------------------------------------------------------ credit ------ */
ok('credit lookup is total: garbage in returns unaided credit, not NaN',
  creditFor(0) === 1 && creditFor(5) === 0.25 && creditFor(99) === 0.25
  && creditFor(NaN) === 1 && creditFor(-3) === 1);

console.log(`\n${n} checks passed.`);
