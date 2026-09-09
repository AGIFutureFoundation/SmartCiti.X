/**
 * Long-run soak. The unit tests check behaviour over tens of attempts; this
 * runs thousands and asserts the invariants hold the whole way, because the
 * failures that matter in production are the slow ones.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { LearnerProfile, pSuccess, SIGMA_MAX } from './lpa.mjs';
import { ZpdDial, DEFAULTS } from './dial.mjs';
import { SkillGraph } from './graph.mjs';
import { Sequencer, POLICY } from './sequencer.mjs';
import { checkSkillGate } from './gates.mjs';

const ATTEMPTS = Number(process.argv[2] || 4000);
const all = JSON.parse(readFileSync(new URL('../pack/registry/skills.json', import.meta.url))).skills;
const skills = all.filter((s) => s.union === 'welders');
const ids = skills.map((s) => s.skill_id);

function mul(a){return function(){a|=0;a=(a+0x6D2B79F5)|0;let t=Math.imul(a^(a>>>15),1|a);
  t=(t+Math.imul(t^(t>>>7),61|t))^t;return((t^(t>>>14))>>>0)/4294967296;};}

const viol = [];
const note = (m) => { if (!viol.includes(m)) viol.push(m); };

for (const seed of [5, 19, 41]) {
  const rnd = mul(seed);
  const g = new SkillGraph(skills);
  const p = new LearnerProfile(`soak${seed}`);
  for (const id of ids) p.get(id);
  let day = 0;
  const d = new ZpdDial(p);
  const seq = new Sequencer(g, p, d, { clock: () => day });
  const hist = [];
  const latent = new Map(ids.map((id, i) => [id, 32 + (i * 7) % 30]));
  const gatedAt = new Map();
  let stalled = false, lastPick = null, sameRun = 0;

  for (let i = 0; i < ATTEMPTS; i++) {
    day = Math.floor(i / 6);
    if (i % 25 === 0) for (const k of d.perSkill.keys()) d.startSession(k);
    const pick = seq.next(ids, hist);
    if (!pick) { stalled = true; break; }

    // --- invariants at pick time
    const sk = p.get(pick.skill);
    if (!Number.isFinite(pick.difficulty)) note('non-finite difficulty served');
    if (!Number.isFinite(sk.theta) || sk.theta < 0 || sk.theta > 100) note(`theta out of scale: ${sk.theta}`);
    if (!Number.isFinite(sk.sigma) || sk.sigma < 0 || sk.sigma > SIGMA_MAX + 1e-9) note(`sigma out of range: ${sk.sigma}`);
    if (sk.p_mastery < 0 || sk.p_mastery > 1) note(`mastery out of [0,1]: ${sk.p_mastery}`);
    if (pick.mode !== 'calibrating' && pick.mode !== 'remediation') {
      const c = d.setpoint(pick.skill);
      if (c < sk.theta + DEFAULTS.railLo - 1e-6 || c > sk.theta + DEFAULTS.railHi + 1e-6)
        note(`setpoint escaped rails: c=${c.toFixed(2)} theta=${sk.theta.toFixed(2)}`);
    }
    if (seq.workingSet.size > POLICY.workingSetMax) note(`working set over cap: ${seq.workingSet.size}`);

    // interleaving: only judgeable where an alternative existed
    if (pick.skill === lastPick) sameRun++; else sameRun = 1;
    if (sameRun > POLICY.maxConsecutiveSameSkill + 1 && (pick.poolSize ?? 1) >= 2)
      note(`ran ${sameRun} on one skill with ${pick.poolSize} alternatives`);
    lastPick = pick.skill;

    const correct = rnd() < pSuccess(latent.get(pick.skill), pick.difficulty);
    const rec = p.record(pick.skill, { difficulty: pick.difficulty, correct, rung: 0 });
    if (!Number.isFinite(rec.delta)) note('non-finite theta delta');
    g.propagate(p, pick.skill, rec.delta, { correct });
    d.observe(pick.skill, { correct, rung: 0, latZ: 0, difficulty: pick.difficulty });
    seq.record(pick.skill, { correct, mode: pick.mode });
    checkSkillGate(p, pick.skill, hist);

    // a gate, once awarded, must never be withdrawn by a later query
    for (const id of ids) {
      const st = p.get(id);
      if (st.gated_at !== undefined && !gatedAt.has(id)) gatedAt.set(id, i);
      if (gatedAt.has(id) && st.gated_at === undefined) note(`gate silently revoked on ${id}`);
    }

    hist.push({ skill: pick.skill, correct, rung: 0, difficulty: pick.difficulty,
                mode: pick.mode, gate_qualifying: pick.mode === 'verify' });
  }

  // --- bounded memory: nothing may grow without limit
  if (seq.recentSkills.length > 21) note(`recentSkills unbounded: ${seq.recentSkills.length}`);
  for (const [, st] of d.perSkill) if (st.history.length > ATTEMPTS) note('dial history unbounded');
  const ungated = ids.filter((id) => p.get(id).gated_at === undefined).length;
  // Running out of work is only a fault while skills remain uncertified;
  // finishing the hall is completion.
  if (stalled && ungated > 0)
    note(`sequencer stalled after ${hist.length} attempts with ${ungated} skills uncertified`);
  if (stalled && ungated === 0) console.log(`  (seed ${seed}: hall complete at ${hist.length} attempts)`);

  const gated = ids.filter((id) => p.get(id).gated_at !== undefined).length;
  const inBand = hist.filter((h) => {
    const pt = pSuccess(latent.get(h.skill), h.difficulty);
    return pt >= 0.70 && pt <= 0.85;
  }).length;
  console.log(`seed ${String(seed).padEnd(3)} attempts ${hist.length}  gated ${String(gated).padStart(2)}/${ids.length}` +
              `  in-band ${(100 * inBand / hist.length).toFixed(1)}%` +
              `  dial-histories ${d.perSkill.size}  seq-log ${seq.log.length}`);
}

if (viol.length) {
  console.log('\nINVARIANT VIOLATIONS:');
  for (const v of viol) console.log('  ✗ ' + v);
  process.exit(1);
}
console.log(`\nno invariant violations over ${ATTEMPTS} attempts x 3 seeds.`);
