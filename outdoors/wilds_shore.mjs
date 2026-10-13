// outdoors/wilds_shore.mjs - DERIVED shoreline points in the AUTHORED wilds terrain (wilds/core.mjs, read only).
// Usage: node outdoors/wilds_shore.mjs  -> JSON on stdout: { <world id>: [{x, z, depth_m, near_site}] }
// A shore point is a grid cell whose terrain height is BELOW the world's biome.water_level_m while a 4-neighbour
// cell is at or above it (wet next to dry). For each world the scan keeps the shore cell nearest to each site and
// to the trailhead (distinct cells only), so every spot is somewhere a player can walk to. Nothing is guessed:
// a world whose terrain never dips below its water level returns an empty list and outdoors/build.py fails by name.
import { readFileSync } from 'node:fs';
import { wildsTerrain } from '../wilds/core.mjs';

const STEP = 32;   // AUTHORED scan step in metres
const reg = JSON.parse(readFileSync(new URL('../wilds/registry/wilds.json', import.meta.url), 'utf8'));
const out = {};
for (const w of reg.worlds) {
  const T = wildsTerrain(w);
  const half = w.extent_m / 2 - w.biome.rim_width_m;   // stay inside the rim
  const lvl = w.biome.water_level_m;
  const shore = [];
  for (let x = -half; x <= half; x += STEP) {
    for (let z = -half; z <= half; z += STEP) {
      const h = T.height(x, z);
      if (h >= lvl) continue;
      const dry = [[STEP, 0], [-STEP, 0], [0, STEP], [0, -STEP]].some(([dx, dz]) => T.height(x + dx, z + dz) >= lvl);
      if (dry) shore.push({ x, z, depth_m: Math.round((lvl - h) * 10) / 10 });
    }
  }
  const anchors = [...w.sites.map((s) => ({ id: s.id, x: s.x, z: s.z })), { id: 'trailhead', x: w.trailhead.x, z: w.trailhead.z }];
  const picked = [];
  const used = new Set();
  for (const a of anchors) {
    let best = null, bd = Infinity;
    for (const c of shore) {
      const k = c.x + ',' + c.z; if (used.has(k)) continue;
      const d = Math.hypot(c.x - a.x, c.z - a.z);
      if (d < bd) { bd = d; best = c; }
    }
    if (!best) continue;
    // spread: skip a shore cell within 400 m of one already picked
    if (picked.some((p) => Math.hypot(p.x - best.x, p.z - best.z) < 400)) continue;
    used.add(best.x + ',' + best.z);
    picked.push({ ...best, near_site: a.id, site_distance_m: Math.round(bd) });
  }
  out[w.id] = { scan_step_m: STEP, water_level_m: lvl, shore_cells: shore.length, spots: picked };
}
process.stdout.write(JSON.stringify(out));
