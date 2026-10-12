/* robotics/claw/arena_adapter.mjs - the Omega Claw drives the ARENA harness (robotics/arena/harness.mjs, owned by the
 * arena pack; imported here, never edited). The Scheduler builds the queue policies x tasks x levels x seeds, the
 * harness runs each episode, the Referee re-judges every outcome against the task's own termination rules in
 * robotics/registry/robotics.json, and the Evaluator pairs every policy with the SCRIPTED reference on the same
 * (task, level, seed) and reports exact sign-test p-values and a seeded bootstrap interval. Deterministic; no clock.
 * `node robotics/claw/arena_adapter.mjs` prints the tournament JSON robotics/claw/build.py stores. Trains nothing. */
import { fileURLToPath } from 'node:url';
import { policies, tasks, runEpisode } from '../arena/harness.mjs';
import { C, REG, AUTH, load } from './node.mjs';

export function tournament() {
  const P = policies(REG), Tk = tasks(REG);
  const ref = P.find((p) => p.card && p.card.reference === true);
  if (!ref) throw new Error('claw: the harness names no reference policy');
  const queue = C.schedule(P, Tk);
  const runs = [];
  let disagree = 0;
  for (const q of queue) {
    const ep = runEpisode(REG, q);
    const env = REG.envs[q.env], j = C.referee(env, ep);
    if (!j.agrees) disagree++;
    runs.push({ ...q, success: j.success, rule: j.rule, steps: ep.steps, collected: ep.outcome.collected, return: ep.outcome.return,
      collisions: Math.round((ep.outcome.terms.collision || 0) / env.reward.find((r) => r.term === 'collision').weight), path_m: Math.round(C.pathLen(ep.samples) * 100) / 100 });
  }
  const per = {};
  for (const p of P) { const rs = runs.filter((r) => r.policy === p.id);
    per[p.id] = { version: p.version, provenance: p.provenance, runs: rs.length, success: rs.filter((r) => r.success).length, cap: rs.filter((r) => r.rule === 'cap').length,
      collisions: rs.reduce((a, r) => a + r.collisions, 0), mean_return: Math.round(rs.reduce((a, r) => a + r.return, 0) / rs.length * 1000) / 1000 }; }
  const refRuns = runs.filter((r) => r.policy === ref.id);
  const paired = {};
  for (const p of P) if (p.id !== ref.id) paired[p.id + ' vs ' + ref.id] = C.compare(runs.filter((r) => r.policy === p.id), refRuns);
  // the agents' lines for this tournament: AUTHORED templates, every number measured above
  const A = (role, id) => load('robotics/claw/authored/claw.json').agents[role].lines.find((l) => l.id === id);
  const levels = Tk.reduce((a, t) => a + t.levels.length, 0), seeds = Tk[0].seeds.length;
  const said = {
    scheduler: C.render(A('scheduler', 'queue'), { runs: queue.length, policies: P.length, tasks: Tk.length, levels, seeds }),
    referee: C.render(A('referee', 'verdict'), { success: runs.filter((r) => r.success).length, runs: runs.length, cap: runs.filter((r) => r.rule === 'cap').length, disagree }),
    evaluator: Object.fromEntries(Object.entries(paired).map(([k, v]) => [k, C.render(A('evaluator', 'paired'), { pairs: v.pairs, a_only: v.a_only, b_only: v.b_only, p: v.p })])),
  };
  const cols = ['policy', 'env', 'level', 'seed', 'success', 'rule', 'steps', 'collected', 'return', 'collisions', 'path_m'];
  return { harness_interface: ['policies', 'tasks', 'runEpisode'], reference: ref.id, policies: P.map((p) => ({ id: p.id, version: p.version, provenance: p.provenance })),
    queue_size: queue.length, referee_disagreements: disagree, per_policy: per, paired, said, columns: cols, runs: runs.map((r) => cols.map((c) => typeof r[c] === 'boolean' ? +r[c] : r[c])) };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) process.stdout.write(JSON.stringify(tournament()) + '\n');
