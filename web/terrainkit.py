#!/usr/bin/env python3
"""TERRAIN_JS: ground relief for the walkable worlds (as a string), for any page.

What it gives a page (every top-level name starts with `terrain`/`TERRAIN_`):
  - a height sampler contract: an object {height(x, z) -> m, provenance, source}
    in SCENE metres (x east, z = -north, y up);
      terrainGrid(grid)          RECORDED: bilinear over a vendored elevation
                                 grid (only when an elevation pack publishes one
                                 with a licence and a pinned fetch; see
                                 ELEV_CONTRACT); outside its extent -> null;
      terrainAuthored(parts)     AUTHORED: gentle procedural relief summed from
                                 knolls (cosine bells) and levee bands (a crest
                                 beside a bank line); labelled AUTHORED, never
                                 "real elevation";
  - terrainLattice(fn, cell)     the SAME surface the mesh draws: the sampler on
                                 a cell lattice, interpolated on the triangles
                                 the patch uses, so the walker, vehicles and
                                 building bases stand on what is drawn;
  - terrainPatch(lat, box, keep) one displaced grid patch per group (a page
                                 merges it into a mesh it already draws: no
                                 extra draw call);
  - terrainSeat(lat, x, z, w, d, yaw)  base y of a footprint: the LOWEST ground
                                 under its corners and centre (never floats);
  - terrainGround(lat) / terrainFleetGround(lat, waterY, isWater)
                                 physkit ground(x, z) and a fleetkit ground
                                 adapter {height, waterLevel} - water stays at
                                 its level;
  - terrainSlope(lat, x0, z0, x1, z1, step) and terrainAudit(lat, items)
                                 the eval's measures (max slope, base gaps).

No THREE and no DOM: pure functions over plain objects (node-testable:
web/test_terrainkit.mjs). Fail closed: a missing field throws by name.

    python3 web/terrainkit.py            prints the module size and exports
    python3 web/terrainkit.py --out F    writes the module to F (tests import it)
"""
import re
import sys

TERRAIN_JS = r'''/* TERRAIN_KIT:BEGIN - ground relief sampler, lattice, patch and adapters (web/terrainkit.py). */
const TERRAIN_API = 1;
const TERRAIN_TIERS = ['RECORDED', 'AUTHORED'];
function terrainNeed(o, k, where) {
  if (o === null || typeof o !== 'object' || !(k in o)) throw new Error('terrainkit: ' + where + ' has no ' + k);
  return o[k];
}
function terrainSmooth(e0, e1, x) { const t = Math.max(0, Math.min(1, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t); }
/* a cosine bell: peak at d = 0, 0 at d >= r, zero slope at both ends */
function terrainKnoll(d, r, peak) { return d >= r ? 0 : peak * 0.5 * (1 + Math.cos(Math.PI * d / r)); }
/* a levee band beside a bank line: 0 up to toe0 (the bank stays at the ground level), rising to the crest at crest,
   falling back to 0 at toe1 (all metres from the bank line) */
function terrainLevee(d, spec) {
  const t0 = terrainNeed(spec, 'toe0', 'levee'), c = terrainNeed(spec, 'crest', 'levee'), t1 = terrainNeed(spec, 'toe1', 'levee'), pk = terrainNeed(spec, 'peak', 'levee');
  if (!(t0 < c && c < t1)) throw new Error('terrainkit: levee needs toe0 < crest < toe1');
  if (d <= t0 || d >= t1) return 0;
  return d < c ? pk * terrainSmooth(t0, c, d) : pk * (1 - terrainSmooth(c, t1, d));
}
/* RECORDED: bilinear over a regular grid (row-major, row 0 at z0, column 0 at x0, scene metres) */
function terrainGrid(g) {
  if (terrainNeed(g, 'provenance', 'grid') !== 'RECORDED') throw new Error('terrainkit: a grid sampler must be RECORDED');
  if (terrainNeed(g, 'units', 'grid') !== 'm') throw new Error('terrainkit: grid units must be m');
  const source = terrainNeed(g, 'source', 'grid'), x0 = terrainNeed(g, 'x0', 'grid'), z0 = terrainNeed(g, 'z0', 'grid');
  const dx = terrainNeed(g, 'dx', 'grid'), dz = terrainNeed(g, 'dz', 'grid'), nc = terrainNeed(g, 'cols', 'grid'), nr = terrainNeed(g, 'rows', 'grid');
  const hs = terrainNeed(g, 'heights', 'grid');
  if (!source) throw new Error('terrainkit: a RECORDED grid needs its source');
  if (hs.length !== nc * nr || nc < 2 || nr < 2) throw new Error('terrainkit: grid heights length ' + hs.length + ' != cols x rows');
  for (let i = 0; i < hs.length; i++) if (!Number.isFinite(hs[i])) throw new Error('terrainkit: grid height ' + i + ' is not finite');
  const height = (x, z) => {
    const u = (x - x0) / dx, v = (z - z0) / dz;
    if (u < 0 || v < 0 || u > nc - 1 || v > nr - 1) return null;
    const i = Math.min(nc - 2, Math.floor(u)), j = Math.min(nr - 2, Math.floor(v)), fu = u - i, fv = v - j;
    const a = hs[j * nc + i], b = hs[j * nc + i + 1], c = hs[(j + 1) * nc + i + 1], d = hs[(j + 1) * nc + i];
    return a * (1 - fu) * (1 - fv) + b * fu * (1 - fv) + c * fu * fv + d * (1 - fu) * fv;
  };
  return { height, provenance: 'RECORDED', source };
}
/* AUTHORED: parts = {knolls(x, z) -> [{x, z, r, peak}], levees(x, z) -> [{d, spec}], fade(x, z) -> 0..1, floor};
   height = fade * (sum of knolls + max of levees), clamped to >= floor (land never dips under the water level) */
function terrainAuthored(parts) {
  const knolls = terrainNeed(parts, 'knolls', 'authored'), levees = terrainNeed(parts, 'levees', 'authored'), fade = terrainNeed(parts, 'fade', 'authored');
  const floor = terrainNeed(parts, 'floor', 'authored'), note = terrainNeed(parts, 'note', 'authored');
  const height = (x, z) => {
    const f = fade(x, z); if (f <= 0) return floor;
    let h = 0, lv = 0;
    for (const k of knolls(x, z)) h += terrainKnoll(Math.hypot(x - k.x, z - k.z), k.r, k.peak);
    for (const l of levees(x, z)) lv = Math.max(lv, terrainLevee(l.d, l.spec));
    return Math.max(floor, floor + f * (h + lv));
  };
  return { height, provenance: 'AUTHORED', source: note };
}
/* the drawn surface: the sampler at lattice points (cached), interpolated on the patch's triangles - quad (i, j) is split
   along its (i, j)-(i+1, j+1) diagonal into (a, b, c) and (a, c, d), exactly as terrainPatch indexes it */
function terrainLattice(sampler, cell, cap) {
  const fn = terrainNeed(sampler, 'height', 'sampler'), prov = terrainNeed(sampler, 'provenance', 'sampler');
  if (!TERRAIN_TIERS.includes(prov)) throw new Error('terrainkit: provenance ' + prov + ' is not RECORDED or AUTHORED');
  if (!(cell > 0)) throw new Error('terrainkit: lattice cell must be > 0');
  const max = cap || 200000, cache = new Map(); let misses = 0;
  const at = (i, j) => {
    const k = i * 1048576 + j; let h = cache.get(k);
    if (h === undefined) { h = fn(i * cell, j * cell); if (h === null || !Number.isFinite(h)) throw new Error('terrainkit: sampler has no height at ' + i * cell + ', ' + j * cell); if (cache.size >= max) cache.clear(); cache.set(k, h); misses++; }
    return h;
  };
  const height = (x, z) => {
    const u = x / cell, v = z / cell, i = Math.floor(u), j = Math.floor(v), fx = u - i, fz = v - j;
    const a = at(i, j), c = at(i + 1, j + 1);
    if (fx >= fz) { const b = at(i + 1, j); return a + (b - a) * fx + (c - b) * fz; }
    const d = at(i, j + 1); return a + (c - d) * fx + (d - a) * fz;
  };
  return { cell, at, height, provenance: prov, source: sampler.source, clear: () => cache.clear(), stats: () => ({ cached: cache.size, misses }) };
}
/* one displaced grid patch per group over [x0, x1] x [z0, z1] (lattice-aligned): keep(i, j) -> group key or null decides
   each quad; lift raises the drawn surface (not the sampled one) so it never z-fights a flat mesh under it.
   Returns Map key -> {position Float32Array, normal Float32Array, uv Float32Array, index Uint32Array, quads} */
function terrainPatch(lat, x0, z0, x1, z1, keep, lift) {
  const c = lat.cell, i0 = Math.floor(x0 / c), i1 = Math.ceil(x1 / c), j0 = Math.floor(z0 / c), j1 = Math.ceil(z1 / c);
  const groups = new Map();
  for (let i = i0; i < i1; i++) for (let j = j0; j < j1; j++) {
    const g = keep(i, j); if (g === null || g === undefined) continue;
    let o = groups.get(g); if (!o) groups.set(g, o = { pos: [], ij: [], idx: [], vmap: new Map(), quads: 0 });
    const vid = (a, b) => { const k = a * 1048576 + b; let v = o.vmap.get(k); if (v === undefined) { v = o.pos.length / 3; o.vmap.set(k, v); o.ij.push(a, b); o.pos.push(a * c, lat.at(a, b) + lift, b * c); } return v; };
    const A = vid(i, j), B = vid(i + 1, j), C = vid(i + 1, j + 1), D = vid(i, j + 1);
    o.idx.push(A, C, B, A, D, C);   // wound to face +y (x east, z south)
    o.quads++;
  }
  const out = new Map();
  for (const [g, o] of groups) {
    const n = o.pos.length / 3, nor = new Float32Array(n * 3);
    for (let v = 0; v < n; v++) {
      const a = o.ij[v * 2], b = o.ij[v * 2 + 1];
      const hx = lat.at(a + 1, b) - lat.at(a - 1, b), hz = lat.at(a, b + 1) - lat.at(a, b - 1);
      let nx = -hx / (2 * c), ny = 1, nz = -hz / (2 * c); const L = Math.hypot(nx, ny, nz); nx /= L; ny /= L; nz /= L;
      nor[v * 3] = nx; nor[v * 3 + 1] = ny; nor[v * 3 + 2] = nz;
    }
    out.set(g, { position: new Float32Array(o.pos), normal: nor, uv: new Float32Array(n * 2), index: new Uint32Array(o.idx), quads: o.quads });
  }
  return out;
}
/* base y of a footprint w (x) by d (z) rotated yaw about +y: the lowest drawn ground under its 4 corners and centre */
function terrainSeat(lat, x, z, w, d, yaw) {
  const c = Math.cos(yaw), s = Math.sin(yaw); let m = lat.height(x, z);
  for (const [a, b] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) { const lx = a * w / 2, lz = b * d / 2; m = Math.min(m, lat.height(x + lx * c + lz * s, z - lx * s + lz * c)); }
  return m;
}
/* physkit createPhysics({ground}) */
function terrainGround(lat) { return (x, z) => lat.height(x, z); }
/* fleetkit ground adapter (same shape as fleetFlatGround): land rides the relief, water keeps its level; a wet point
   reads 3 m under the water level exactly as fleetFlatGround does, so fleetkit's wet test is unchanged */
function terrainFleetGround(lat, waterY, isWater) {
  return { height: (x, z) => (isWater(x, z) ? waterY - 3 : lat.height(x, z)), waterLevel: (x, z) => (isWater(x, z) ? waterY : null) };
}
/* max slope (rise over run) of the drawn surface over a box, sampled every step m in x and z */
function terrainSlope(lat, x0, z0, x1, z1, step) {
  let m = 0, at = null;
  for (let x = x0; x < x1; x += step) for (let z = z0; z < z1; z += step) {
    const h = lat.height(x, z), sx = Math.abs(lat.height(x + step, z) - h) / step, sz = Math.abs(lat.height(x, z + step) - h) / step;
    const g = Math.max(sx, sz); if (g > m) { m = g; at = [x, z]; }
  }
  return { max: m, at };
}
/* items [{id, x, z, w, d, yaw, y}]: y is where the page stood it. gap = y - lowest ground under the footprint (the base
   must touch it: |gap| <= tol) and float = y - ground at the centre (> tol means it hangs in the air) */
function terrainAudit(lat, items, tol) {
  const bad = []; let maxGap = 0, maxFloat = -Infinity;
  for (const it of items) {
    const seat = terrainSeat(lat, it.x, it.z, it.w, it.d, it.yaw), gap = it.y - seat, fl = it.y - lat.height(it.x, it.z);
    maxGap = Math.max(maxGap, Math.abs(gap)); maxFloat = Math.max(maxFloat, fl);
    if (Math.abs(gap) > tol || fl > tol) bad.push({ id: it.id, gap: +gap.toFixed(3), float: +fl.toFixed(3) });
  }
  return { n: items.length, bad, maxGap: +maxGap.toFixed(3), maxFloat: items.length ? +maxFloat.toFixed(3) : 0 };
}
/* RECORDED: GEO's elevation pack grid (elevation/registry/elevation.json grids.<region>, ELEV_CONTRACT v1), the JS twin of
   elevation/sample.py height_m + height_world_m: uint16 LE row-major (rows north->south), v = 0 nodata, else
   v * scale - offset metres NAVD88; bilinear between the 4 cell centres (edges clamp), the containing cell if any of the
   4 is nodata, null if that is nodata too or outside. Scene metres (x east, z = -north) about origin {lat, lng}. */
function terrainDem(meta, bytes, origin) {
  const w = terrainNeed(meta, 'w_arcsec', 'dem'), n = terrainNeed(meta, 'n_arcsec', 'dem'), c = terrainNeed(meta, 'cell_arcsec', 'dem');
  const rows = terrainNeed(meta, 'rows', 'dem'), cols = terrainNeed(meta, 'cols', 'dem'), nod = terrainNeed(meta, 'nodata', 'dem');
  const sc = terrainNeed(meta, 'scale_m', 'dem'), off = terrainNeed(meta, 'offset_m', 'dem'), R = terrainNeed(meta, 'R_m', 'dem'), source = terrainNeed(meta, 'source', 'dem');
  const lat0 = terrainNeed(origin, 'lat', 'dem origin'), lng0 = terrainNeed(origin, 'lng', 'dem origin');
  if (bytes.length !== rows * cols * 2) throw new Error('terrainkit: dem bytes ' + bytes.length + ' != rows x cols x 2');
  const cell = (r, k) => { const i = 2 * (r * cols + k), x = bytes[i] | (bytes[i + 1] << 8); return x === nod ? null : Math.round((x * sc - off) * 10) / 10; };
  const heightLL = (lat, lng) => {
    const fy = (n - lat * 3600) / c, fx = (lng * 3600 - w) / c;
    if (!(fy >= 0 && fy <= rows && fx >= 0 && fx <= cols)) return null;
    const rc = Math.min(Math.floor(fy), rows - 1), cc = Math.min(Math.floor(fx), cols - 1);
    const cy = Math.min(Math.max(fy - 0.5, 0), rows - 1), cx = Math.min(Math.max(fx - 0.5, 0), cols - 1);
    const r0 = Math.floor(cy), c0 = Math.floor(cx), r1 = Math.min(r0 + 1, rows - 1), c1 = Math.min(c0 + 1, cols - 1), ty = cy - r0, tx = cx - c0;
    const q = [cell(r0, c0), cell(r0, c1), cell(r1, c0), cell(r1, c1)];
    if (q.some((v) => v === null)) return cell(rc, cc);
    const top = q[0] + (q[1] - q[0]) * tx, bot = q[2] + (q[3] - q[2]) * tx;
    return Math.round((top + (bot - top) * ty) * 100) / 100;
  };
  const k = Math.PI / 180, cos0 = Math.cos(lat0 * k);
  const height = (x, z) => heightLL(lat0 + (-z / R) / k, lng0 + (x / (R * cos0)) / k);
  return { height, heightLL, provenance: 'RECORDED', source };
}
/* TERRAIN_KIT:END */
export { TERRAIN_API, TERRAIN_TIERS, terrainNeed, terrainDem, terrainSmooth, terrainKnoll, terrainLevee, terrainGrid, terrainAuthored, terrainLattice,
  terrainPatch, terrainSeat, terrainGround, terrainFleetGround, terrainSlope, terrainAudit };
'''

EXPORTS = re.findall(r'export \{([^}]*)\}', TERRAIN_JS)[0].replace('\n', ' ').split(',')
EXPORTS = [e.strip() for e in EXPORTS if e.strip()]
BEGIN, END = '/* TERRAIN_KIT:BEGIN', '/* TERRAIN_KIT:END */'


def terrain_inline():
    """The module body without its export line, for pasting into a page's own module script."""
    return TERRAIN_JS[:TERRAIN_JS.index(END) + len(END)]


if __name__ == '__main__':
    if '--out' in sys.argv:
        open(sys.argv[sys.argv.index('--out') + 1], 'w').write(TERRAIN_JS)
    print(f'TERRAIN_JS: {len(TERRAIN_JS)} bytes, {len(EXPORTS)} exports: {", ".join(EXPORTS)}')
