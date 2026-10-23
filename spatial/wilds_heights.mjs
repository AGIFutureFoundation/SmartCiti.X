/**
 * Prints the wilds terrain, sampled on a coarse grid, as JSON on stdout.
 *
 * spatial/tiles.py calls this once per build so the glTF terrain tiles are
 * cut from the SAME height function the wilds page walks (wilds/core.mjs
 * wildsTerrain), not from a second copy of it. Nothing here is typed: the
 * worlds, seeds, extents and sites are read from wilds/registry/wilds.json,
 * and the grid size comes in as argv[2].
 */
import { readFileSync } from 'node:fs';
import { wildsTerrain } from '../wilds/core.mjs';

const N = Number(process.argv[2]);
if (!Number.isInteger(N) || N < 2) {
  console.error('wilds_heights: argv[2] must be an integer grid size >= 2');
  process.exit(2);
}
const reg = JSON.parse(readFileSync(new URL('../wilds/registry/wilds.json', import.meta.url)));
const out = {};
for (const w of reg.worlds) {
  const t = wildsTerrain(w);
  const half = w.extent_m / 2;
  const step = w.extent_m / (N - 1);
  const grid = [];
  for (let j = 0; j < N; j++) {
    for (let i = 0; i < N; i++) {
      grid.push(Math.round(t.height(-half + i * step, -half + j * step) * 100) / 100);
    }
  }
  out[w.id] = {
    n: N,
    step_m: step,
    half_m: half,
    grid, // row-major, j = z index, i = x index
    sites: w.sites.map((s) => ({ id: s.id, x: s.x, z: s.z, h: Math.round(t.height(s.x, s.z) * 100) / 100 })),
    trailhead: { x: w.trailhead.x, z: w.trailhead.z, h: Math.round(t.height(w.trailhead.x, w.trailhead.z) * 100) / 100 },
  };
}
process.stdout.write(JSON.stringify(out));
