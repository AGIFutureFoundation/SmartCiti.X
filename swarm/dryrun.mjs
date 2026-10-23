/* swarm/dryrun.mjs - a dry run of one simulated robot command: one SCRIPTED-policy episode of the capability's arena world
 * (robotics/arena/harness.mjs, the same SIM_CORE the pages run). It is a SCHEMATIC simulation of an AUTHORED task: no
 * robot moves, no device is opened, nothing is sent anywhere, and the numbers say nothing about a physical robot. */
import { loadArena, runOne } from '../robotics/arena/harness.mjs';
import { sha256 } from './audit.mjs';

export function createArena({ root, policy }) {
  const A = loadArena(root);
  return Object.freeze({
    stamp: A.reg.source_stamp,
    run(cap, robotId, commandId, params = {}) {
      const env = A.reg.envs[cap.env];
      if (!env || env.runner !== 'robokit') throw new Error('dryrun: ' + cap.env + ' is not an arena world');
      const level = params.level ?? cap.level, seeds = env.seeds;
      if (!env.curriculum.levels.some((l) => l.level === level)) throw new Error('dryrun: level ' + level + ' is not declared for ' + cap.env);
      const seed = params.seed ?? seeds[parseInt(sha256(commandId + ':' + robotId).slice(0, 8), 16) % seeds.length];
      if (!seeds.includes(seed)) throw new Error('dryrun: seed ' + seed + ' is not declared for ' + cap.env);
      const row = runOne(A, policy, env, level, seed).row;
      return Object.freeze({ policy: row[0], env: row[1], level: row[2], seed: row[3], success: row[4] === 1, steps: row[5], path_m: row[6], collisions: row[7] + 0, return: row[8] + 0 });
    },
  });
}
