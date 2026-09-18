/**
 * ACP-08 tests.
 *
 * These are the checks that protect learners from the system, so each one is
 * written as a refusal that must actually happen — not a warning that gets
 * logged and ignored.
 */
import assert from 'node:assert/strict';
import { AuditLog } from './audit.mjs';
import { Bus } from './bus.mjs';
import { ParityMonitor, StopConditions, OverrideManager, PARITY, OVERRIDE } from './safeguards.mjs';

let n = 0; const ok = (m) => { n++; console.log(`  ok  ${m}`); };

/* ------------------------------------------------------------- parity ---- */
{
  const audit = new AuditLog();
  const p = new ParityMonitor({ audit });
  // a real gap: the mobile cohort certifies far less often
  p.report('device:hd',     { n: 400, gatePassRate: 0.62, timeInSupport: 0.14, stretchOfferRate: 0.22 });
  p.report('device:mobile', { n: 380, gatePassRate: 0.48, timeInSupport: 0.15, stretchOfferRate: 0.21 });
  const r = p.run();
  assert.equal(r.clean, false, 'a 23% relative gap must not read as clean');
  const t = r.tickets.find((x) => x.metric === 'gatePassRate');
  assert.ok(t, 'gate pass disparity should open a ticket');
  assert.equal(t.worst, 'device:mobile');
  assert.ok(audit.entries({ action: 'parity.ticket' }).length === r.tickets.length);
  ok(`a real cohort disparity opens a ticket (${(t.relative * 100).toFixed(0)}% on gate pass rate)`);
}

{
  const p = new ParityMonitor();
  p.report('a', { n: 300, gatePassRate: 0.60, timeInSupport: 0.15, stretchOfferRate: 0.20 });
  p.report('b', { n: 300, gatePassRate: 0.575, timeInSupport: 0.16, stretchOfferRate: 0.21 });
  assert.equal(p.run().clean, true, 'a 4% gap is under the alarm and must not cry wolf');
  ok('a small gap does not fire — the alarm is worth listening to');
}

{
  const p = new ParityMonitor();
  p.report('big',  { n: 500, gatePassRate: 0.60 });
  p.report('tiny', { n: 4,   gatePassRate: 0.10 });   // 4 learners is not evidence
  assert.equal(p.run().clean, true, 'a cohort under the minimum must not drive an alarm');
  ok(`cohorts under n=${PARITY.minCohortN} are noise, not disparity`);
}

/* the sharpest rule in ACP-08 */
{
  const audit = new AuditLog();
  const p = new ParityMonitor({ audit });
  p.report('site:north', { n: 300, gatePassRate: 0.62 });
  p.report('site:south', { n: 300, gatePassRate: 0.45 });
  p.recordParams('site:north', { setpointOffset: -6.5, loopGain: 0.3 });
  p.recordParams('site:south', { setpointOffset: -6.5, loopGain: 0.3 });
  assert.equal(p.run().masking, false, 'identical params are not masking');

  // now someone "fixes" the south site by making its dial easier
  p.recordParams('site:south', { setpointOffset: -11, loopGain: 0.3 });
  const r = p.run();
  assert.equal(r.masking, true, 'per-cohort tuning while a disparity is open must be flagged');
  assert.equal(audit.entries({ action: 'parity.masking_suspected' }).length, 1);
  ok('tuning one cohort\'s dial while its disparity is open is flagged as masking');
}

{
  const p = new ParityMonitor();
  p.report('a', { n: 300, gatePassRate: 0.62 });
  p.report('b', { n: 300, gatePassRate: 0.45 });
  p.run();
  assert.equal(p.promotionsAllowed(), false, 'promotions must be blocked while parity is red');
  p.report('b', { n: 300, gatePassRate: 0.60 });
  p.run();
  assert.equal(p.promotionsAllowed(), true);
  ok('promotions are blocked while a parity ticket is open, and released when it closes');
}

/* --- §23.1: "measured nothing" must never read as "measured and clean" --- *
 * Reproduced by execution before the fix:
 *   zero-cohort run():                  {"clean":true,"tickets":[],"masking":false}
 *   promotionsAllowed() after that run: true
 *   ageDays() after that run:           ~0 (not Infinity)
 *   StopConditions.evaluate({}) after:  {"halted":false,"reasons":[]}
 * run() filtered cohorts to those with n>=minCohortN, then for each metric
 * `if (vals.length < 2) continue;` — so with zero cohorts, or every cohort
 * under threshold, or exactly one usable cohort, no metric was ever
 * compared, tickets stayed empty, and it returned clean:true while also
 * stamping lastRunAt (so ageDays() looked fresh). Two harms: promotions
 * were waved through having measured nothing, and the staleness alarm meant
 * to catch a parity job that cannot run was silenced by a run that executes
 * but observes nothing. Fixed by a third fact, `observed`, distinct from
 * `clean` — and lastRunAt (what ageDays() reads) only advances when
 * `observed` is true. */
{
  const p = new ParityMonitor();
  const r = p.run();
  assert.equal(r.observed, false, 'zero cohorts means nothing was compared');
  assert.equal(p.promotionsAllowed(), false, 'promotions must not ride on an empty run');
  ok('run() over zero cohorts does not read as green: promotions are refused');
}

{
  const p = new ParityMonitor();
  p.report('a', { n: 5, gatePassRate: 0.9 });   // both under minCohortN=20
  p.report('b', { n: 3, gatePassRate: 0.1 });
  const r = p.run();
  assert.equal(r.observed, false, 'every cohort under threshold means nothing was compared either');
  assert.equal(p.promotionsAllowed(), false);
  ok('run() where every cohort is under threshold does not read as green');
}

{
  const p = new ParityMonitor();
  p.report('big',  { n: 500, gatePassRate: 0.60 });
  p.report('tiny', { n: 4,   gatePassRate: 0.10 });   // filtered out, same as line 41-44 above
  const r = p.run();
  assert.equal(r.clean, true, 'still true: a sub-threshold cohort does not itself contradict cleanliness');
  assert.equal(r.observed, false, 'but only one usable cohort means nothing was compared');
  assert.equal(p.promotionsAllowed(), false, 'promotions require having actually compared something');
  ok('run() with one usable cohort only (nothing to compare against) does not read as green, even though clean stays true');
}

{
  // the legitimate case: two usable cohorts that actually agree.
  const p = new ParityMonitor();
  p.report('a', { n: 300, gatePassRate: 0.60 });
  p.report('b', { n: 300, gatePassRate: 0.575 });
  const r = p.run();
  assert.equal(r.clean, true);
  assert.equal(r.observed, true, 'two usable cohorts were actually compared');
  assert.equal(p.promotionsAllowed(), true, 'measured and found nothing wrong is legitimately green');
  ok('two usable cohorts that agree is measured-and-clean, and promotions stay open');
}

{
  // the staleness interaction: an empty run must not satisfy the "parity
  // job cannot run" stop condition — it must behave exactly like a job that
  // never ran at all, not like a fresh clean one.
  const audit = new AuditLog();
  const p = new ParityMonitor({ audit });
  assert.equal(p.ageDays(), Infinity, 'never run: infinite age, as before');
  p.run();                                        // executes, observes nothing
  assert.equal(p.ageDays(), Infinity,
    'an empty run must not reset the staleness clock — it is still a parity job that cannot be trusted');
  const s = new StopConditions({ audit, parity: p });
  const review = s.evaluate({});
  assert.equal(review.halted, true, 'an empty run must not satisfy the parity-cannot-run stop condition');
  assert.ok(review.reasons.some((why) => /parity job/.test(why)));
  ok('an empty run does not silence the "parity job cannot run" stop condition — it still fires');
}

/* ----------------------------------------------------- stop conditions --- */
{
  const audit = new AuditLog();
  const parity = new ParityMonitor({ audit });
  // A real, observed, agreeing run — not an empty one. An empty run is no
  // longer "fresh and fine" (that was the fail-open this file now tests for
  // below); it is indistinguishable from a parity job that cannot run, and
  // would halt on its own before drift is ever evaluated.
  parity.report('a', { n: 100, gatePassRate: 0.80 });
  parity.report('b', { n: 100, gatePassRate: 0.79 });
  parity.run();
  const s = new StopConditions({ audit, parity });

  assert.equal(s.evaluate({}).halted, false);
  // drift alone is not enough; drift ON MANY ITEMS is
  assert.equal(s.evaluate({ driftPointsPerWeek: 12, driftedItemShare: 0.05 }).halted, false);
  const r = s.evaluate({ driftPointsPerWeek: 12, driftedItemShare: 0.4 });
  assert.equal(r.halted, true);
  assert.ok(r.reasons[0].includes('calibration'));
  assert.equal(audit.entries({ action: 'adaptation.halted' }).length, 1);
  ok('sustained calibration drift across many items halts adaptation');
}

{
  const s = new StopConditions();
  assert.equal(s.evaluate({ cohortAnxietyShare: 0.30 }).halted, true,
    'a cohort spending 30% of its time struggling must halt the dial');
  ok('a cohort stuck in SUPPORT halts adaptation');
}

{
  const audit = new AuditLog();
  const parity = new ParityMonitor({ audit });     // never run
  const s = new StopConditions({ audit, parity });
  assert.equal(s.evaluate({}).halted, true, 'a parity job that cannot run is itself a stop condition');
  ok('if the parity job cannot run, adaptation stops — no unwatched adaptation');
}

{
  const s = new StopConditions();
  const fakeDial = { setpoint: () => 71 };
  assert.equal(s.setpointFor(fakeDial, 's'), 71);
  s.evaluate({ cohortAnxietyShare: 0.9 });
  assert.equal(s.setpointFor(fakeDial, 's', 50), 50, 'while halted everyone gets fixed difficulty');
  ok('while halted the dial is bypassed for fixed difficulty, not left running degraded');
}

{
  const audit = new AuditLog();
  const parity = new ParityMonitor({ audit });
  parity.report('a', { n: 100, gatePassRate: 0.80 });
  parity.report('b', { n: 100, gatePassRate: 0.79 });
  parity.run();                                   // a real, observed, clean run
  const s = new StopConditions({ audit, parity });
  s.evaluate({ cohortAnxietyShare: 0.9 });
  s.evaluate({ cohortAnxietyShare: 0.9 });        // still bad — must not re-log
  assert.equal(audit.entries({ action: 'adaptation.halted' }).length, 1);
  s.evaluate({ cohortAnxietyShare: 0.1 });
  assert.equal(audit.entries({ action: 'adaptation.resumed' }).length, 1);
  ok('halt and resume are logged as transitions, not repeated every evaluation');
}

/* ---------------------------------------------------------- overrides ---- */
{
  const audit = new AuditLog();
  const bus = new Bus({ audit });
  let applied = 0;
  bus.subscribe('override.applied', 'dial', () => applied++);
  const o = new OverrideManager({ audit, bus });

  const r = o.pin({ learner: 'L1', skill: 's', difficulty: 70, actor: 'instructor:kim',
                    reason: 'wants a stretch before the exam' });
  assert.equal(r.ok, true);
  assert.equal(o.pinnedDifficulty('L1', 's'), 70);
  assert.equal(applied, 1, 'an override must reach the dial over the bus');
  assert.equal(o.evidenceWeight('L1', 's'), OVERRIDE.overriddenEvidenceWeight,
    'evidence from a pinned episode is biased and must be weighted down');
  assert.equal(o.evidenceWeight('L1', 'other'), 1);
  assert.ok(audit.entries({ action: 'override.pin' })[0].actor === 'instructor:kim');
  ok('an instructor pin is applied, published, attributed, and down-weights its evidence');
}

{
  const audit = new AuditLog();
  const o = new OverrideManager({ audit });
  const now = Date.now();
  assert.equal(o.easierToday({ learner: 'L', now }).ok, true);
  assert.equal(o.easierToday({ learner: 'L', now }).ok, true);
  const third = o.easierToday({ learner: 'L', now });
  assert.equal(third.ok, false, 'the third request in a week must be declined');
  assert.ok(third.why.includes('reset'), 'the refusal should tell the learner when it comes back');
  // ...and the allowance returns the following week
  assert.equal(o.easierToday({ learner: 'L', now: now + 8 * 86400000 }).ok, true);
  assert.equal(audit.entries({ action: 'override.easier_declined' }).length, 1);
  ok(`"easier today" is granted ${OVERRIDE.learnerEasierPerWeek}x per week, declined kindly, and resets`);
}

{
  const o = new OverrideManager();
  o.pin({ learner: 'L', skill: 's', difficulty: 70, actor: 'kim' });
  o.unpin({ learner: 'L', skill: 's', actor: 'kim' });
  assert.equal(o.pinnedDifficulty('L', 's'), null);
  assert.equal(o.evidenceWeight('L', 's'), 1, 'once unpinned, evidence counts fully again');
  ok('a released pin restores full evidence weight');
}

/* ------------------------------------------- the lever actually moves --- */
{
  const { Session } = await import('./session.mjs');
  const { readFileSync } = await import('node:fs');
  const skills = JSON.parse(readFileSync(new URL('../pack/registry/skills.json', import.meta.url)))
    .skills.filter((s) => s.union === 'welders');
  const S = new Session({ skills, strict: false });
  const before = S.next().difficulty;
  S.easierToday();
  const after = S.next().difficulty;
  assert.ok(after < before, `an easier day must actually serve easier tasks (${before} -> ${after})`);
  S.clearEasier();
  assert.ok(Math.abs(S.next().difficulty - before) < 1e-9, 'and it clears at the session boundary');
  ok('"easier today" moves the served difficulty, not just the message');
}

{
  const { Session } = await import('./session.mjs');
  const { readFileSync } = await import('node:fs');
  const skills = JSON.parse(readFileSync(new URL('../pack/registry/skills.json', import.meta.url)))
    .skills.filter((s) => s.union === 'welders');
  const S = new Session({ skills, strict: false });
  S.overrides.pin({ learner: S.learnerId, skill: S.skillIds[0], difficulty: 88, actor: 'kim' });
  S.stop.evaluate({ cohortAnxietyShare: 0.9 });
  const p = S.next();
  assert.equal(p.mode, 'halted', 'a halt must outrank a pin — the system stops trusting itself');
  assert.notEqual(p.difficulty, 88);
  ok('a stop condition outranks an instructor pin');
}

console.log(`\n${n} checks passed.`);
