/* robotics/test.mjs - the robotics env registry and the robokit core, checked. Browser-free, network-free.
 *
 * Recompute, never re-read: counts are recounted, DERIVED values are re-derived from the registries they cite
 * (sims/, ambient/, web/deepkit.py), and the deterministic core is extracted from web/robokit.py and run here -
 * the same code the page runs - so determinism, sample shape and the contract's field list are proven, not
 * asserted. The most important family: NOTHING IS TRAINED (trained_models 0, honesty says so, no format claim).
 */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (m, c) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m); } };
const J = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));

const reg = J('robotics/registry/robotics.json');
const sims = J('sims/registry/sims.json'), amb = J('ambient/registry/ambient.json'), tr = J('training/registry/training.json');
const envs = Object.values(reg.envs), rk = envs.filter((e) => e.runner === 'robokit'), seats = envs.filter((e) => e.runner === 'sim-seat');

/* ---- provenance, schema, stamp ---- */
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(readFileSync(join(HERE, 'build.py'))).digest('hex').slice(0, 16));
ok('schema tc-robotics/1, contract version 1', reg.schema === 'tc-robotics/1' && reg.contract_version === 1);
ok('counts are recounted from the entries: envs, robokit envs, sim-seat envs, embodiments',
  reg.counts.envs === envs.length && reg.counts.robokit_envs === rk.length && reg.counts.sim_seat_envs === seats.length
  && reg.counts.embodiments === Object.keys(reg.embodiments).length && rk.length === 4);

/* ---- honesty: nothing trained ---- */
ok('NOTHING HAS BEEN TRAINED: trained_models is 0 and the honesty line says so first',
  reg.counts.trained_models === 0 && /^NOTHING HAS BEEN TRAINED/.test(reg.honesty.trained));
ok('no external-format compatibility is claimed (RLDS / LeRobot / ML-Agents named only as "not", no round-trip test)',
  /Not an RLDS, LeRobot or ML-Agents file/.test(reg.honesty.formats) && /no round-trip/.test(reg.honesty.formats));
ok('every embodiment is AUTHORED and every reference policy is SCRIPTED',
  Object.values(reg.embodiments).every((m) => m.provenance === 'AUTHORED')
  && envs.every((e) => e.reference_policy.provenance === 'SCRIPTED'));
ok('the three embodiment kinds the brief names exist: wheeled rover, arm-on-base, ROV',
  ['wheeled-rover', 'arm-on-base', 'rov'].every((k) => Object.values(reg.embodiments).some((m) => m.kind === k)));
ok('the data honesty line forbids personal data and names classroom mode',
  /no names, emails, free text, audio, camera, biometric, device id or real-world location/.test(reg.honesty.data)
  && /Classroom \/ K-12/.test(reg.honesty.data));

/* ---- env spec shape (contract v1) ---- */
const SPEC = ['id', 'version', 'provenance', 'runner', 'world', 'embodiments', 'sources', 'observation', 'action',
  'reward', 'termination', 'episode_cap', 'seeds', 'reference_policy'];
ok('every env carries the contract v1 spec fields', envs.every((e) => SPEC.every((k) => k in e) && e.version === 1));
ok('every observation field has a name, a unit and a dtype; no field is a real-world position',
  envs.every((e) => e.observation.every((o) => o.name && typeof o.unit === 'string' && o.dtype
    && !/lat|lon|gps|geo/.test(o.name))));
ok('robokit observations and actions carry real numeric ranges (low < high)',
  rk.every((e) => e.observation.every((o) => typeof o.low === 'number' && o.low < o.high)
    && e.action.type === 'continuous' && e.action.fields.every((a) => a.low < a.high)));
ok('robokit action ranges are the embodiment limits, not a second hand-typed set',
  rk.every((e) => { const L = reg.embodiments[e.embodiments[0]].limits, f = Object.fromEntries(e.action.fields.map((a) => [a.name, a]));
    return f.v.low === L.v_min_ms && f.v.high === L.v_max_ms && f.w.high === L.w_max_rads && f.w.low === -L.w_max_rads
      && (!f.vz || f.vz.high === L.vz_max_ms); }));
ok('every env has weighted reward terms with a reason, and termination includes the step cap',
  envs.every((e) => e.reward.length && e.reward.every((r) => typeof r.weight === 'number' && r.why))
  && rk.every((e) => e.termination.some((t) => t.id === 'cap') && e.termination[0].id !== 'cap'));
ok('robokit episode cap is 600 steps x 0.1 s = 60 s, matching the training/ sample cap at 5 Hz',
  rk.every((e) => e.episode_cap.steps * e.episode_cap.dt_s === 60)
  && tr.world_teleop.max_samples === 60 * tr.world_teleop.sample_hz);
ok('robokit seeds are declared integers', rk.every((e) => e.seeds.length >= 3 && e.seeds.every(Number.isInteger)));

/* ---- DERIVED values re-derived ---- */
const ds = readFileSync(join(ROOT, 'web/deepkit.py'), 'utf8').match(/const DEEP_SPEED = \{ vertical: ([0-9.]+), rov: ([0-9.]+), turn: ([0-9.]+) \}/);
const rov = reg.embodiments['rov.survey'].limits;
ok('the ROV limits are web/deepkit.py DEEP_SPEED (re-read here)',
  ds && rov.v_max_ms === Number(ds[2]) && rov.w_max_rads === Number(ds[3]) && rov.vz_max_ms === Number(ds[1]));
ok('the gate count is the forklift-run bay-yard gate count (re-read from sims/)',
  reg.envs['world.gate-drive'].objects.gates === sims.sims['forklift-run'].scenarios.find((s) => s.id === 'bay-yard').params.gates);
ok('the litter types are the ambient litter ids (re-read from ambient/)',
  JSON.stringify(reg.envs['world.litter-pickup'].objects.litter_types) === JSON.stringify(Object.keys(amb.litter).sort()));
ok('one sim-seat env per training seat, observation = its dash ids+units, action = its controls, reward = its rubric axes',
  seats.length === Object.keys(sims.sims).length && Object.entries(sims.sims).every(([id, s]) => {
    const e = reg.envs[`sim.${id}`];
    return e && JSON.stringify(e.observation.map((o) => [o.name, o.unit])) === JSON.stringify(s.dash.map((d) => [d.id, d.unit]))
      && e.observation.every((o) => o.low === null && o.high === null)
      && JSON.stringify(e.action.fields.map((a) => a.keys)) === JSON.stringify(s.controls.map((c) => c.keys))
      && JSON.stringify(e.reward.map((r) => r.term)) === JSON.stringify(s.rubric.map((r) => r.axis))
      && e.recorded_by.includes('`sim`');
  }));

/* ---- teleop ---- */
ok('every embodiment has keyboard + touch teleop, touch targets >= 44 px, each touch field an action field of its envs',
  Object.keys(reg.embodiments).every((id) => { const t = reg.teleop[id];
    return t && t.keyboard.length >= 4 && t.touch.length >= 4 && t.min_touch_px >= 44
      && rk.filter((e) => e.embodiments.includes(id)).every((e) => t.touch.every((b) => e.action.fields.some((a) => a.name === b.field)));
  }));

/* ---- the deterministic core, run here ---- */
const kit = readFileSync(join(ROOT, 'web/robokit.py'), 'utf8');
const core = kit.slice(kit.indexOf('/* ROBOKIT_CORE:BEGIN'), kit.indexOf('/* ROBOKIT_CORE:END */'));
ok('the core is present and deterministic: no Math.random, no Date, no network', core.length > 3000
  && !/Math\.random|Date\.|fetch\(|XMLHttpRequest/.test(core));
const RoboCore = new Function(core + '\nreturn RoboCore;')();
const T = { kind: tr.world_episode_kinds['world-teleop'], world_teleop: tr.world_teleop };
const EP_FIELDS = tr.world_episode_kinds['world-teleop'].fields.filter((f) => f !== 't');   // t is stamped at keep time
const runs = [];
for (const e of rk) for (const s of e.seeds) {
  const emb = { ...reg.embodiments[e.embodiments[0]] };
  const a = RoboCore.rollout(e, emb, s, T, 'lab'), b = RoboCore.rollout(e, emb, s, T, 'lab');
  runs.push({ e, s, a, same: JSON.stringify(a) === JSON.stringify(b) });
}
ok('same (env, seed) -> byte-identical scripted episode, every env and seed', runs.every((r) => r.same));
ok('different seeds lay the arena out differently', rk.every((e) => {
  const L = e.seeds.map((s) => JSON.stringify(RoboCore.layout(e, s))); return new Set(L).size === L.length; }));
ok('an undeclared seed is refused by name', (() => { try { RoboCore.reset(rk[0], reg.embodiments[rk[0].embodiments[0]], 999); return false; }
  catch (x) { return /seed 999 is not declared/.test(x.message); } })());
ok('every episode has exactly the contract field list (t is stamped when kept)',
  runs.every((r) => JSON.stringify(Object.keys(r.a)) === JSON.stringify(EP_FIELDS) && r.a.kind === 'world-teleop'
    && r.a.actor === 'scripted-reference' && r.a.hz === 5 && r.a.v === 1));
ok('samples: <= 300, one every 2 steps (5 Hz at 0.1 s), shape {i,pose,vel,near,a}, a in action-field order',
  runs.every((r) => r.a.samples.length <= 300 && r.a.samples.length === Math.min(300, Math.ceil(r.a.steps / 2))
    && r.a.samples.every((x, k) => x.i === 2 * k && Object.keys(x).join(',') === 'i,pose,vel,near,a'
      && x.a.length === r.e.action.fields.length && x.pose.length === (r.e.objects.targets ? 4 : 3) && x.near.length <= 4)));
ok('nearby ids are only env-local AUTHORED object ids', runs.every((r) => r.a.samples.every((x) =>
  x.near.every((id) => /^(litter|rock|cone|gate|target|bin)(-\d+[ab]?)?$/.test(id)))));
ok('outcome shape {done, success, return, terms, collected}; terms sum to the return; success only on a success termination',
  runs.every((r) => { const o = r.a.outcome, sum = Object.values(o.terms).reduce((x, y) => x + y, 0);
    return Object.keys(o).join(',') === 'done,success,return,terms,collected' && Math.abs(sum - o.return) < 0.01
      && o.success === (o.done === r.e.termination[0].id); }));
ok('the step cap holds: no episode runs past 600 steps', runs.every((r) => r.a.steps <= 600));
/* the reference policy is measured, not promised: print it, and hold it to beating an idle robot */
const idle = (e, s) => { const st = RoboCore.reset(e, reg.embodiments[e.embodiments[0]], s);
  while (!st.done) RoboCore.step(st, Object.fromEntries(e.action.fields.map((a) => [a.name, 0]))); return st.ret; };
const beat = runs.filter((r) => r.a.outcome.return > idle(r.e, r.s)).length, succ = runs.filter((r) => r.a.outcome.success).length;
console.log(`  (measured) scripted reference: ${succ}/${runs.length} runs reach a success termination; `
  + rk.map((e) => `${e.id} ${runs.filter((r) => r.e === e && r.a.outcome.success).length}/${e.seeds.length}`).join(', '));
ok(`the scripted reference beats an idle robot on most runs (${beat}/${runs.length} measured)`, beat >= Math.ceil(runs.length * 0.75));

/* ---- wave 15: AUTHORED curriculum, MEASURED reference benchmark, litter-sort feasibility ---- */
ok('every robokit env carries an AUTHORED 3-level curriculum whose level 1 IS the spec (empty override), recording at level 1 only',
  rk.every((e) => e.curriculum && e.curriculum.provenance === 'AUTHORED' && e.curriculum.levels.map((l) => l.level).join() === '1,2,3'
    && Object.keys(e.curriculum.levels[0].params).length === 0 && JSON.stringify(e.curriculum.record_levels) === '[1]'
    && e.curriculum.levels.every((l) => Object.keys(l.params).every((k) => ['obstacles', 'gate_gap_m', 'current_ms'].includes(k)))));
ok('levels 2 and 3 change the layout (or the dynamics) of every env, and an undeclared level is refused by name',
  rk.every((e) => { const emb = reg.embodiments[e.embodiments[0]], a = RoboCore.rollout(e, emb, e.seeds[0], T, 'lab', 1);
    return [2, 3].every((l) => JSON.stringify(RoboCore.rollout(e, emb, e.seeds[0], T, 'lab', l)) !== JSON.stringify(a)); })
  && (() => { try { RoboCore.reset(rk[0], reg.embodiments[rk[0].embodiments[0]], 1, 9); return false; } catch (x) { return /level 9 is not declared/.test(x.message); } })());
ok('no curriculum level raises an object count past the observation range the spec declares',
  rk.every((e) => e.curriculum.levels.every((l) => !('litter' in l.params) && !('targets' in l.params) && !('gates' in l.params))));
const B = reg.reference_benchmark;
ok('the reference benchmark block exists: SCRIPTED policy, measured by robotics/bench.mjs, 20 declared seeds, levels 1-3',
  B && B.policy === 'SCRIPTED' && B.measured_by === 'robotics/bench.mjs' && B.seeds.length === 20
  && rk.every((e) => e.seeds.join() === B.seeds.join()) && B.levels.join() === '1,2,3' && /Not a learned policy/.test(B.what));
ok('the benchmark policy version is the sha256[:16] of the CURRENT robokit core (a stale block fails here)',
  B.policy_version === createHash('sha256').update(core).digest('hex').slice(0, 16));
const { bench } = await import('./bench.mjs');
const RE = bench(reg, RoboCore, T, core);
ok('the stored benchmark counts equal a fresh headless recount: success, items, mean steps per env and level',
  JSON.stringify(Object.fromEntries(Object.entries(RE.per_env).map(([k, v]) => [k, v.levels])))
    === JSON.stringify(Object.fromEntries(Object.entries(B.per_env).map(([k, v]) => [k, v.levels])))
  && B.totals.runs === RE.totals.runs && B.totals.success === RE.totals.success);
const F = B.per_env['world.litter-sort'].feasibility, S1 = B.per_env['world.litter-sort'].levels['1'];
ok(`litter-sort feasibility bound is stored per seed against v_max x cap (${F.budget_m} m): success never exceeds the feasible seeds, items never exceed the bound (${S1.items}/${F.items_bound} items binned, ${F.feasible_seeds}/20 feasible)`,
  F.by_seed.length === 20 && F.budget_m === reg.embodiments['arm.on-base'].limits.v_max_ms * 600 * 0.1
  && S1.success <= F.feasible_seeds && S1.items <= F.items_bound && F.by_seed.every((b) => b[1] > 0 && (b[2] === 1) === (b[1] <= F.budget_m)));
ok('every robokit env declares the "stopped" ending (learner pressed Stop), and it is never a success termination',
  rk.every((e) => e.termination.some((t) => t.id === 'stopped') && e.termination[0].id !== 'stopped'));
{ const e = reg.envs['world.litter-sort'], emb = reg.embodiments[e.embodiments[0]], st = RoboCore.reset(e, emb, e.seeds[0], 1);
  const P = emb.radius_m + emb.limits.reach_m; st.carrying = st.items[0]; st.items[0].taken = true;
  st.e = st.bin.e; st.n = st.bin.n - (P + 0.2); st.yaw = 0; const a = RoboCore.policy(st); RoboCore.step(st, a);
  ok(`policy v3: carrying, the scripted gripper closes inside the deposit circle (${(P + 0.2).toFixed(1)} m from the bin, beyond the ${P.toFixed(1)} m pickup circle) and the item is binned`,
    a.grip === 1 && st.collected === 1 && st.carrying === null); }
console.log(`  (measured) benchmark: ${rk.map((e) => `${e.id} ` + [1, 2, 3].map((l) => `L${l} ${B.per_env[e.id].levels[String(l)].success}/${B.per_env[e.id].levels[String(l)].runs}`).join(' ')).join('; ')}`);

console.log(`robotics/test: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
