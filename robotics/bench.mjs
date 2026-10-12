/* robotics/bench.mjs - MEASURE the SCRIPTED reference policy of web/robokit.py (ROBOKIT_CORE, the code the pages run)
 * on every robokit env, every curriculum level and every declared seed, headless and deterministic. Prints one JSON
 * document to stdout; robotics/build.py stores it as registry.reference_benchmark and robotics/test.mjs recomputes it.
 * Honesty: this measures a hand-written policy. Nothing is learned. The litter-sort block also carries a straight-line
 * path LOWER BOUND per seed (spawn -> first item -> bin, then two legs per further item) against the travel budget
 * (v_max x cap seconds): a seed whose bound exceeds the budget cannot be finished by ANY policy under the spec.
 * Usage: node robotics/bench.mjs <registry.json>   (or import { bench, loadCore } from robotics/test.mjs) */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url)), ROOT = join(HERE, '..');
export const policyVersion = (src) => createHash('sha256').update(src).digest('hex').slice(0, 16);
/* the ROBOKIT_CORE block of web/robokit.py - the very code the pages run; refused if missing or non-deterministic */
export function loadCore() {
  const kit = readFileSync(join(ROOT, 'web/robokit.py'), 'utf8');
  const core = kit.slice(kit.indexOf('/* SIM_CORE:BEGIN'), kit.indexOf('/* SIM_CORE:END */'));
  if (core.length < 3000 || /Math\.random/.test(core)) throw new Error('bench: robokit core missing or not deterministic');
  return { core, RoboCore: new Function(core + '\nreturn RoboCore;')() };
}

export function bench(reg, RoboCore, T, core) {
  if (typeof core !== 'string' || !core.length) throw new Error('bench: the robokit core source is required (policy version)');
  const rk = Object.values(reg.envs).filter((e) => e.runner === 'robokit');
  const r2 = (x) => Math.round(x * 100) / 100;
  const per_env = {}, totals = { runs: 0, success: 0 };
  let seeds = null, levels = null;
  for (const e of rk) {
    const emb = reg.embodiments[e.embodiments[0]];
    if (!e.curriculum || !Array.isArray(e.curriculum.levels)) throw new Error('bench: ' + e.id + ' has no curriculum');
    seeds = seeds || e.seeds; levels = [...new Set((levels || []).concat(e.curriculum.levels.map((l) => l.level)))].sort((a, b) => a - b);
    if (seeds.join() !== e.seeds.join()) throw new Error('bench: envs declare different seed lists');
    const out = { levels: {} };
    for (const lv of e.curriculum.levels) {
      const row = { level: lv.level, name: lv.name, runs: 0, success: 0, items: 0, return_sum: 0, steps_sum: 0, collisions: 0, by_seed: [] };
      for (const s of e.seeds) {
        const ep = RoboCore.rollout(e, emb, s, T, 'lab', lv.level);
        row.runs++; if (ep.outcome.success) row.success++; row.items += ep.outcome.collected; row.return_sum += ep.outcome.return;
        row.steps_sum += ep.steps; row.collisions += Math.round(-ep.outcome.terms.collision / 0.5);
        row.by_seed.push([s, ep.outcome.success ? 1 : 0, ep.outcome.collected, ep.steps, r2(ep.outcome.return)]);
      }
      row.mean_return = r2(row.return_sum / row.runs); row.mean_steps = Math.round(row.steps_sum / row.runs);
      delete row.return_sum; delete row.steps_sum;
      out.levels[String(lv.level)] = row;
      if (lv.level === 1) { totals.runs += row.runs; totals.success += row.success; }
    }
    if (e.objects.bin) {   // feasibility bound (level 1 layout; levels 2-3 only add obstacles, which lengthen paths)
      const budget = emb.limits.v_max_ms * e.episode_cap.steps * e.episode_cap.dt_s;
      const feas = (level) => { const bound = []; let items_bound = 0;
      for (const s of e.seeds) {
        // reach-aware: step() picks up within P = radius + reach of an item and deposits within D = P + 0.3 of the bin,
        // so the robot never has to touch either point; every leg below is shortened by those radii (a true lower bound)
        const L = RoboCore.layout(e, s, level), P = emb.radius_m + emb.limits.reach_m, D = P + 0.3, pos = (x) => Math.max(0, x);
        const db = (x) => Math.hypot(x.e - L.bin.e, x.n - L.bin.n), ds = (x) => Math.hypot(x.e, x.n);
        const first = (x) => pos(ds(x) - P) + pos(db(x) - P - D), loop = (x) => 2 * pos(db(x) - P - D);
        const lb = L.items.reduce((a, x) => a + loop(x), 0) + Math.min(...L.items.map((x) => first(x) - loop(x)));
        let best = 0;
        for (const f of L.items) { let m = first(f), k = m <= budget ? 1 : 0;
          if (k) for (const r of L.items.filter((x) => x !== f).map(loop).sort((a, b) => a - b)) { if (m + r <= budget) { m += r; k++; } else break; }
          best = Math.max(best, k); }
        items_bound += best; bound.push([s, r2(lb), lb <= budget ? 1 : 0, best]);
      }
      return { what: 'reach-aware straight-line path lower bound per seed [seed, bound_m, feasible, items_bound] against the '
        + 'travel budget v_max x cap; a seed above the budget cannot be finished by any policy under this spec (caps are not retuned)',
        budget_m: r2(budget), feasible_seeds: bound.filter((b) => b[2]).length, items_bound, by_seed: bound }; };
      out.feasibility = feas(1);
      // wave 16: a level that MOVES the items (items_near_bin_m, the added 'reachable' level) carries its own bound,
      // measured on its own layout - the level-1 bound above says nothing about it
      for (const lv of e.curriculum.levels) if (lv.params.items_near_bin_m) out.levels[String(lv.level)].feasibility = feas(lv.level);
    }
    per_env[e.id] = out;
  }
  return { policy_version: policyVersion(core), seeds, levels, per_env, totals };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const regPath = process.argv[2];
  if (!regPath) throw new Error('bench: registry path required');
  const reg = JSON.parse(readFileSync(regPath, 'utf8'));
  const tr = JSON.parse(readFileSync(join(ROOT, 'training/registry/training.json'), 'utf8'));
  const { core, RoboCore } = loadCore();
  process.stdout.write(JSON.stringify(bench(reg, RoboCore, { kind: tr.world_episode_kinds['world-teleop'], world_teleop: tr.world_teleop }, core)) + '\n');
}
