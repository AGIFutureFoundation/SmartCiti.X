/**
 * Agent-fabric tests.
 *
 * The central claim: the eval harness catches the failures it says it catches.
 * Each adversarial stub must fail exactly its own gate — and the compliant
 * mentor must pass all of them, so the suite is not simply strict about
 * everything.
 */
import assert from 'node:assert/strict';
import { Mentor, redactPII, detectEscalation } from './agent.mjs';
import { evaluate, gateGoldenSet, gateScope, gatePersona,
         gateOutcomeLift, makeGoldens, RED_TEAM } from './evals.mjs';
import { compliant, overHelper, scopeViolator, drifter, underinformed, leaky } from './stubs.mjs';
import { Router, keywordClassifier, MAX_HANDOFFS } from './router.mjs';

let n = 0;
const ok = (m) => { n++; console.log(`  ok  ${m}`); };
const G = makeGoldens(4242, 60);

/* ------------------------------------------------------------ middleware -- */
const r1 = redactPII('reach me at sam@example.com or 415-555-0134');
assert.equal(r1.redactions, 2);
assert.ok(!r1.text.includes('example.com') && !r1.text.includes('555-0134'));
ok('PII redaction catches email and phone');

assert.equal(detectEscalation('a guy fell from the scaffold and is bleeding'), 'safety_incident');
assert.equal(detectEscalation('how do I set the amperage'), null);
ok('escalation triggers fire on incidents, stay quiet on ordinary questions');

const leakTurn = await leaky().turn('who do I contact?', {});
assert.ok(leakTurn.text.includes('[redacted-email]'), 'outbound PII must be redacted too');
assert.ok(leakTurn.redactions >= 2);
ok('outbound PII is redacted even when the mentor leaks it');

// scope violations are contained, not thrown
const sv = await scopeViolator().turn(RED_TEAM[0].prompt, { task: 'redteam' });
assert.ok(sv.violations.length > 0);
assert.ok(!sv.text.includes('done'), 'a refused turn must not echo the agreement');
ok('scope violations are contained, counted, and the response replaced');

// rung is clamped to the ceiling regardless of what the mentor returns
const clamped = await overHelper().turn('help', { task: 'hint', requested_rung: 1, scaffold_ceiling: 2 });
assert.equal(clamped.rung, 2, 'rung must be clamped to the scaffold ceiling');
assert.ok(clamped.over_helped, 'over-helping must still be recorded after clamping');
ok('hint rung clamped to ceiling, and the over-help still recorded');

/* ------------------------------------------------- the harness passes good */
const champ = compliant();
const good = await evaluate(champ, { goldens: G, quick: true });
assert.ok(good.pass, `compliant mentor failed: ${good.failedGates.join(', ')}`);
ok(`compliant mentor passes all ${good.results.length} gates`);

/* ------------------------------------- ...and fails each broken one, once - */
const cases = [
  ['over-helper',   overHelper,     'rung_discipline'],
  ['scope violator', scopeViolator, 'scope_compliance'],
  ['persona drifter', drifter,      'persona_stability'],
  ['underinformed', underinformed,  'golden_set'],
];
for (const [label, make, expectedGate] of cases) {
  const res = await evaluate(make(), { goldens: G, quick: true });
  assert.ok(!res.pass, `${label} should have failed the suite`);
  assert.deepEqual(res.failedGates, [expectedGate],
    `${label} failed ${JSON.stringify(res.failedGates)}, expected exactly [${expectedGate}]`);
  ok(`${label} fails exactly one gate: ${expectedGate}`);
}

/* --------------------------------------------- gate 5 catches what 1-4 miss */
const oh = overHelper();
const ohNoRung = await Promise.all([gateGoldenSet(oh, G), gateScope(oh), gatePersona(oh, 12)]);
assert.ok(ohNoRung.every((r) => r.pass),
  'the over-helper should look clean on knowledge, scope and persona');
const lift = await gateOutcomeLift(overHelper(), compliant(), { learners: 16, sessions: 8 });
assert.ok(lift.challenger.meanRungServed > lift.champion.meanRungServed,
  'the over-helper must show a deeper mean served rung in cohort');
assert.ok(!lift.pass, 'gate 5 should reject a challenger that depresses outcomes');
ok(`gate 5 separates on cohort outcome: mean rung served ` +
   `${lift.champion.meanRungServed} -> ${lift.challenger.meanRungServed}, ` +
   `ability gain ${lift.champion.meanAbilityGain} -> ${lift.challenger.meanAbilityGain}, ` +
   `lift ${lift.value} (threshold ${lift.threshold})`);

// and the same mentor is invisible to gates 1, 3 and 4 — that is the point
assert.ok(ohNoRung.every((r) => r.pass));
ok('gate 5 catches a mentor that gates 1, 3 and 4 all pass');

/* ---------------------------------------------------------------- router -- */
const classify = keywordClassifier({
  joyce: ['weld', 'bead', 'amperage', 'electrode'],
  sam:   ['safety', 'ppe', 'lockout', 'permit', 'hazard'],
  dana:  ['crew', 'leadership', 'schedule', 'foreman'],
});
const mk = (id) => new Mentor({ id, name: id, union: 'welders' }, {
  respond: (t, ctx) => ctx.handoffTo && ctx.handoffTo[id]
    ? { text: `passing to ${ctx.handoffTo[id]}`, handoff: ctx.handoffTo[id] }
    : { text: `${id} answers` },
});
const mentors = { chris: mk('chris'), joyce: mk('joyce'), sam: mk('sam'), dana: mk('dana') };
const router = new Router({
  mentors, halls: { welding: ['joyce', 'sam'] }, supervisor: 'chris', classify,
});

const acc = await router.measureRouting([
  { text: 'my bead is porous, wrong amperage?', hall: 'welding', expect: 'joyce' },
  { text: 'what ppe for hot work permit', hall: 'welding', expect: 'sam' },
  { text: 'electrode storage for weld rod', hall: 'welding', expect: 'joyce' },
  { text: 'who signs off the lockout permit', hall: 'welding', expect: 'sam' },
  { text: 'how do I talk to my foreman about the schedule', hall: 'welding', expect: 'dana' },
  { text: 'what time does the yard open', hall: 'welding', expect: 'chris' },
]);
assert.ok(acc.accuracy >= 0.8, `routing accuracy ${acc.accuracy}`);
ok(`router: accuracy ${acc.accuracy}, mean ${acc.meanLlmCalls} LLM calls/turn`);

// in-hall crisp questions take the cheap swarm path; fuzzy ones pay for the supervisor
const swarm = router.route('my bead is porous, wrong amperage?', 'welding');
const sup = router.route('what time does the yard open', 'welding');
assert.equal(swarm.mode, 'swarm');
assert.equal(sup.mode, 'supervisor');
assert.ok(swarm.llmCalls < sup.llmCalls);
ok('crisp in-hall questions route swarm-cheap; fuzzy ones escalate to the supervisor');

// recursion guard: a handoff cycle must terminate at the supervisor
const looping = await router.handle('weld safety weld safety', {
  hall: 'welding', ctx: { handoffTo: { joyce: 'sam', sam: 'joyce' } },
});
assert.ok(looping.hops <= MAX_HANDOFFS + 1, `chain ran to ${looping.hops} hops`);
const lastMode = looping.chain.at(-1).mode;
assert.ok(['guard_tripped', 'loop_broken'].includes(lastMode), `ended as ${lastMode}`);
ok(`handoff cycle terminates at the supervisor (${lastMode}, ${looping.hops} hops)`);

// every turn is on the audit log with its full chain
assert.ok(router.log.length > 0 && router.log.every((r) => Array.isArray(r.chain)));
ok('every routed turn carries its full hop chain for the audit log');

console.log(`\n${n} checks passed.`);
