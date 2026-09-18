/**
 * ACP-13 §14.2 — the wave 1 rehearsal.
 *
 * ROADMAP v4.0 workstream 1's exit criterion asks for "rollout lanes complete
 * for wave 1 with audit evidence." This repo has no deployment and no real
 * learners, so wave 1 cannot be completed here — only rehearsed, against
 * seeded synthetic cohorts, with every gate wired to its real ACP-08 object
 * and every decision landing in one real audit log. That is what this file
 * proves: not that a wave shipped, but that the machinery a wave would run
 * through actually enforces every gate `ops/rollout.mjs`, `bus/safeguards.mjs`
 * and `ops/jobs.mjs` claim it does, end to end, with a tamper-evident trail
 * to show for it.
 *
 * Shape borrowed from `control/soak.mjs`: seeded deterministic pseudo-
 * randomness (no `Math.random`), real registries rather than mocks, and
 * invariants checked continuously rather than only at the end. Unlike a soak,
 * this is a scripted narrative — the point is not volume, it is that a
 * single coherent rehearsal walks every named gate and leaves a trail that
 * says so.
 */
import assert from 'node:assert/strict';
import { RolloutManager, LANES } from './rollout.mjs';
import { Scheduler, JOBS } from './jobs.mjs';
import { ParityMonitor, StopConditions } from '../bus/safeguards.mjs';
import { AuditLog } from '../bus/audit.mjs';

let n = 0;
const ok = (label, cond) => {
  if (!cond) { console.error('FAIL', label); process.exit(1); }
  n++; console.log('  ok ', label);
};

// Seeded PRNG (mulberry32, same idiom as control/soak.mjs) — one stream, one
// seed, advanced in a fixed code order, so this rehearsal's synthetic cohort
// numbers are reproducible evidence rather than a fresh roll every run.
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rnd = mulberry32(20260918); // the day this rehearsal was written
const jitter = (base, spread) => base + (rnd() - 0.5) * spread;

/* ---------------------------------------------------- continuous invariants */
// One shared AuditLog for the whole rehearsal: every RolloutManager, every
// ParityMonitor, every StopConditions and every Scheduler instance below
// appends into it, so the trail asserted in step (h) is the complete record
// of everything this file did — not a per-scenario sample of it.
const audit = new AuditLog();
const violations = [];
const note = (m) => { if (!violations.includes(m)) violations.push(m); };
const VALID_HALLS = new Set([0, ...LANES.map((l) => l.halls)]);
const VALID_STATES = new Set(['pending', 'rolling', 'full', 'rolled_back']);
let lastSeq = -1;

function checkAudit() {
  const entries = audit.entries();
  for (let i = 0; i < entries.length; i++) {
    const e = entries[i];
    if (!Object.isFrozen(e)) note(`audit entry seq ${e.seq} is not frozen`);
    if (e.seq !== i) note(`audit entries are not in seq order at index ${i}`);
    if (!e.actor || !e.action) note(`audit entry seq ${e.seq} is missing actor/action`);
  }
  if (entries.length && entries[entries.length - 1].seq < lastSeq) note('audit seq went backwards');
  lastSeq = entries.length ? entries[entries.length - 1].seq : lastSeq;
}

function checkRollout(r) {
  if (!VALID_HALLS.has(r.halls)) note(`rollout ${r.id} halls ${r.halls} is not a lane count`);
  if (!VALID_STATES.has(r.state)) note(`rollout ${r.id} has an unknown state ${r.state}`);
  if (r.state === 'rolled_back' && !r.rolledBackFrom) note(`rollout ${r.id} is rolled back with no rolledBackFrom`);
}

/** advance()/deny() wrapped so every step is checked, not just the assertions we name. */
function step(rm, id, opts) {
  const rec = rm.advance(id, opts);
  checkAudit();
  checkRollout(rm.get(id));
  return rec;
}

const cohorts = (a, b) => ({
  a: { n: 150, gatePassRate: jitter(a, 0.02), timeInSupport: jitter(20, 2), stretchOfferRate: jitter(0.30, 0.02) },
  b: { n: 150, gatePassRate: jitter(b, 0.02), timeInSupport: jitter(21, 2), stretchOfferRate: jitter(0.29, 0.02) },
});

console.log('ACP-13 §14.2 wave 1 rehearsal — seeded synthetic cohorts, real ACP-08 gates\n');

/* ===================================================================== *
 * Main line: one content rollout ('wave1') walked through the lanes,
 * hitting the dwell gate, the parity gate and the halt gate in turn.
 * ===================================================================== */
const parity1 = new ParityMonitor({ audit });
const stop1 = new StopConditions({ audit, parity: parity1 });
const rollout1 = new RolloutManager({ parity: parity1, stop: stop1, audit });

rollout1.start('wave1', { kind: 'content' });
const base = step(rollout1, 'wave1');
assert.equal(base.ok, true);
assert.equal(base.lane, 'canary');
assert.equal(base.halls, 1);
ok('a content rollout opens at canary (1 hall), never the whole network', true);

/* --- (a) cannot advance past lane 0 with no dwell reported ------------- */
{
  const denied = step(rollout1, 'wave1'); // no dwellHours at all
  assert.equal(denied.ok, false);
  assert.match(denied.why, /canary needs 24h/);
  assert.match(denied.why, /no observation reported/);
  ok('(a) canary cannot advance to wave with no dwell reported, and the refusal names the lane (canary) and its required hours (24h)', true);
}

/* --- (b) cannot advance while parity is red; can once the ticket closes - */
{
  const dirty = cohorts(0.85, 0.55); // ~35% relative gap — well past the 10% alarm
  parity1.report('hall-red-a', dirty.a);
  parity1.report('hall-red-b', dirty.b);
  const dirtyRun = parity1.run();
  assert.equal(dirtyRun.clean, false);
  checkAudit();

  const blocked = step(rollout1, 'wave1', { dwellHours: 24 });
  assert.equal(blocked.ok, false);
  assert.match(blocked.why, /parity is red/);

  const clean = cohorts(0.82, 0.80); // ~2.4% relative gap — under the alarm
  parity1.report('hall-red-a', clean.a);
  parity1.report('hall-red-b', clean.b);
  const cleanRun = parity1.run();
  assert.equal(cleanRun.clean, true);
  checkAudit();

  const opened = step(rollout1, 'wave1', { dwellHours: 24 });
  assert.equal(opened.ok, true);
  assert.equal(opened.lane, 'wave');
  assert.equal(opened.halls, 5);
  ok('(b) an open parity ticket blocks the next lane, and it opens once the ticket closes — both through ACP-08, not a second opinion here', true);
}

/* --- (e) dial_params rollouts need the shadow run; content/agent do not - */
{
  rollout1.start('wave1-dial-short', { kind: 'dial_params', shadowStartedDaysAgo: 3 });
  const short = step(rollout1, 'wave1-dial-short');
  assert.equal(short.ok, false);
  assert.match(short.why, /14-day shadow/);

  rollout1.start('wave1-dial-ok', { kind: 'dial_params', shadowStartedDaysAgo: 15 });
  const shadowed = step(rollout1, 'wave1-dial-ok');
  assert.equal(shadowed.ok, true);
  assert.equal(shadowed.lane, 'canary');

  // Contrast: 'wave1' is a content rollout and reached canary (above) with no
  // shadowStartedDaysAgo at all — the shadow gate is dial_params-only.
  ok('(e) a dial_params rollout is refused a short shadow run and admitted a completed one; content/agent rollouts pass with no shadow run at all', true);
}

/* --- (c) cannot advance while adaptation is halted ---------------------- */
{
  const halt = stop1.evaluate({ cohortAnxietyShare: 0.40 });
  assert.equal(halt.halted, true);
  checkAudit();

  const denied = step(rollout1, 'wave1', { dwellHours: 48 });
  assert.equal(denied.ok, false);
  assert.match(denied.why, /adaptation is halted/);
  for (const reason of stop1.reasons) assert.ok(denied.why.includes(reason), `refusal should name reason "${reason}"`);
  ok('(c) nothing promotes into a halted network, and the refusal names the halt reasons', true);
}

/* --- (d) auto-rollback on ACP-08 halt; a rolled-back id cannot resume --- */
{
  const before = rollout1.get('wave1');
  assert.equal(before.state, 'rolling');
  assert.equal(before.laneIndex, 1); // sitting at 'wave' when the halt lands mid-wave

  const reverted = rollout1.onHalt(stop1.reasons);
  checkAudit();
  assert.ok(reverted.includes('wave1'));
  const after = rollout1.get('wave1');
  assert.equal(after.state, 'rolled_back');
  assert.equal(after.rolledBackFrom, 'wave');
  checkRollout(after);
  ok('(d) an ACP-08 halt mid-wave auto-rolls the wave back, recording rolledBackFrom as the lane it was in', true);

  const resumeAttempt = step(rollout1, 'wave1', { dwellHours: 999 });
  assert.equal(resumeAttempt.ok, false);
  assert.match(resumeAttempt.why, /rolled back/);
  ok('(d) the rolled-back id can never resume, no matter the dwell reported', true);

  // Clear the halt (mirrors an ops review re-running with clean signals) and
  // confirm a NEW id is what actually gets the wave moving again.
  const resumed = stop1.evaluate({});
  assert.equal(resumed.halted, false);
  checkAudit();
  rollout1.start('wave1-retry', { kind: 'content' });
  const retried = step(rollout1, 'wave1-retry');
  assert.equal(retried.ok, true);
  assert.equal(retried.lane, 'canary');
  ok('(d) resuming the wave requires a new rollout id — start() on a fresh id, never advance() on the rolled-back one', true);
}

/* ===================================================================== *
 * (f) self-halt when the parity job never runs, driven through a real
 * Scheduler — not by forcing StopConditions.evaluate() to fake the gap.
 * ===================================================================== */
{
  const parity2 = new ParityMonitor({ audit });
  const stop2 = new StopConditions({ audit, parity: parity2 });
  const scheduler2 = new Scheduler({ audit });
  const rollout2 = new RolloutManager({ parity: parity2, stop: stop2, audit });

  // Every job EXCEPT parity_job gets a handler — an operationally realistic
  // gap (a job that was never wired up), not a hand-authored failure.
  for (const j of JOBS) if (j.name !== 'parity_job') scheduler2.on(j.name, () => {});

  scheduler2.tick(9 * 86_400_000); // 9 simulated days — past the 8-day window
  checkAudit();
  assert.ok(audit.entries({ action: 'job.missing' }).some((e) => /parity_job/.test(e.why)),
    'the scheduler should have logged the unhandled safety-critical job');
  assert.equal(parity2.ageDays(scheduler2.clock), Infinity,
    'a parity job that never ran has infinite age, not a finite stale one');

  const review = stop2.evaluate({}, { now: scheduler2.clock });
  checkAudit();
  assert.equal(review.halted, true);
  assert.ok(review.reasons.some((r) => /parity job/.test(r)));

  rollout2.start('wave1-starved', { kind: 'content' });
  const starved = step(rollout2, 'wave1-starved');
  assert.equal(starved.ok, false);
  assert.match(starved.why, /adaptation is halted/);
  ok('(f) a network whose parity job never runs (real Scheduler, no handler registered) halts itself on ageDays() alone, and that halt blocks the rollout — no evaluate() call was forced to fake it', true);
}

/* ===================================================================== *
 * (g) canary -> wave -> full when every gate is satisfied, then refused
 * past full — a real Scheduler runs the parity job on cadence throughout.
 * ===================================================================== */
{
  const parity3 = new ParityMonitor({ audit });
  const stop3 = new StopConditions({ audit, parity: parity3 });
  const scheduler3 = new Scheduler({ audit });
  const rollout3 = new RolloutManager({ parity: parity3, stop: stop3, audit });

  scheduler3.on('parity_job', () => {
    const c = cohorts(0.82, 0.80); // stays clean the whole rehearsal
    parity3.report('hall-g-a', c.a);
    parity3.report('hall-g-b', c.b);
    return parity3.run();
  });
  for (const j of JOBS) if (j.name !== 'parity_job') scheduler3.on(j.name, () => {});

  scheduler3.tick(0);
  stop3.evaluate({}, { now: scheduler3.clock });
  checkAudit();

  rollout3.start('wave1-full', { kind: 'content' });
  const g1 = step(rollout3, 'wave1-full');
  assert.equal(g1.ok, true); assert.equal(g1.lane, 'canary'); assert.equal(g1.halls, 1);

  scheduler3.tick(86_400_000); // +1 day of dwell on canary
  stop3.evaluate({}, { now: scheduler3.clock });
  const g2 = step(rollout3, 'wave1-full', { dwellHours: 24 });
  assert.equal(g2.ok, true); assert.equal(g2.lane, 'wave'); assert.equal(g2.halls, 5);

  scheduler3.tick(2 * 86_400_000); // +2 days of dwell on wave (needs 48h)
  stop3.evaluate({}, { now: scheduler3.clock });
  const g3 = step(rollout3, 'wave1-full', { dwellHours: 48 });
  assert.equal(g3.ok, true); assert.equal(g3.lane, 'full'); assert.equal(g3.halls, LANES[2].halls);

  const g4 = step(rollout3, 'wave1-full', { dwellHours: 1e6 });
  assert.equal(g4.ok, false);
  assert.match(g4.why, /already at full network/);
  ok(`(g) with every gate satisfied the wave walks canary (1) -> wave (5) -> full (${LANES[2].halls}), and is refused "already at full network" after`, true);
}

/* ===================================================================== *
 * (h) the audit trail: every advance and denial, in order, with
 * actor/action/why populated, entries frozen, entries() returning a copy.
 * ===================================================================== */
{
  const entries = audit.entries();
  assert.ok(entries.length > 20, 'a rehearsal that touched every gate should leave more than a token trail');

  for (let i = 0; i < entries.length; i++) assert.equal(entries[i].seq, i, `entries() should be in seq order at index ${i}`);
  ok('(h) the trail is complete and in order: every appended entry appears in entries(), seq ascending with no gaps', true);

  assert.ok(entries.every((e) => Object.isFrozen(e)));
  ok('(h) every audit entry is frozen — nothing in the trail can be edited after the fact', true);

  assert.ok(entries.every((e) => e.actor && e.action && typeof e.why === 'string' && e.why.length > 0));
  ok('(h) every entry in the trail has actor, action and a populated why', true);

  const copy = audit.entries();
  assert.notEqual(copy, entries, 'entries() should hand back a fresh array each call');
  copy.push('tampering with the copy');
  assert.equal(audit.entries().length, entries.length, 'mutating a returned copy must not touch the log');
  ok('(h) entries() returns a copy, not the live array — the trail is tamper-evident, not merely append-only in principle', true);

  const advances = entries.filter((e) => e.action === 'rollout.advance');
  const denials = entries.filter((e) => e.action === 'rollout.denied');
  const rollbacks = entries.filter((e) => e.action === 'rollout.rollback');
  assert.ok(advances.some((e) => e.after.id === 'wave1' && e.after.lane === 'canary'));
  assert.ok(denials.some((e) => e.after.id === 'wave1' && /parity is red/.test(e.why)));
  assert.ok(denials.some((e) => e.after.id === 'wave1' && /adaptation is halted/.test(e.why)));
  assert.ok(rollbacks.some((e) => e.after.id === 'wave1' && /wave/.test(e.why)));
  assert.ok(advances.some((e) => e.after.id === 'wave1-full' && e.after.lane === 'full'));
  assert.ok(entries.some((e) => e.action === 'job.missing' && /parity_job/.test(e.why)));
  assert.ok(entries.some((e) => e.action === 'parity.ticket'));
  assert.ok(entries.some((e) => e.action === 'adaptation.halted'));
  assert.ok(entries.some((e) => e.action === 'adaptation.resumed'));
  ok('(h) the trail names every scenario this rehearsal ran: advances, denials, the rollback, the missing-job entry, parity tickets, halts and the resume', true);
}

if (violations.length) {
  console.log('\nINVARIANT VIOLATIONS:');
  for (const v of violations) console.log('  ✗ ' + v);
  process.exit(1);
}

/* -------------------------------------------------------------- summary --- */
console.log('\nfinal rollout states:');
for (const rm of [rollout1]) {
  for (const s of rm.status()) {
    console.log(`  ${s.id.padEnd(20)} kind=${s.kind.padEnd(11)} state=${s.state.padEnd(12)} lane=${String(s.lane).padEnd(8)} halls=${s.halls}`);
  }
}
console.log('\nfull audit trail (' + audit.entries().length + ' entries — the evidence, not a sample):');
for (const e of audit.entries()) {
  console.log(`  #${String(e.seq).padStart(3)} ${String(e.action).padEnd(20)} ${e.why}`);
}

console.log(`\n${n} rehearsal assertions passed, 0 invariant violations, ${audit.entries().length} audit entries.`);
console.log('\nThis proves the machinery: every gate refuses or opens exactly as designed, with a');
console.log('complete trail to show for it. It does NOT prove wave 1 shipped — there is no');
console.log('deployment and no real learner behind any hall count above. The ROADMAP v4.0');
console.log('exit criterion stays recorded as not met until this same walk runs against real');
console.log('cohorts on real halls.');
