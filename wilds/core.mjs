/**
 * The terrain core of the wilds: a pure, deterministic function of a world's
 * registry entry. It is carried byte-for-byte into web/trade_craft_wilds.html
 * between the WILDS_CORE markers (web/test_wilds.mjs holds the copy to this
 * file), and wilds/test.mjs imports it directly, so the node test and the
 * page walk on exactly the same ground.
 *
 * Nothing here is a survey. The ground is AUTHORED: seeded gradient noise
 * shaped by the biome parameters the registry declares. No elevation is read
 * from any real place, and no height it returns is a real height.
 */
/* WILDS_CORE:BEGIN */
function wildsMulberry(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function wildsNoise(seed) {
  const rnd = wildsMulberry(seed);
  const p = new Uint8Array(512);
  const base = new Uint8Array(256);
  for (let i = 0; i < 256; i++) base[i] = i;
  for (let i = 255; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    const t = base[i]; base[i] = base[j]; base[j] = t;
  }
  for (let i = 0; i < 512; i++) p[i] = base[i & 255];
  const GX = [1, -1, 1, -1, 1, -1, 0, 0], GY = [1, 1, -1, -1, 0, 0, 1, -1];
  const fade = (t) => t * t * t * (t * (t * 6 - 15) + 10);
  function n2(x, y) {
    const xi = Math.floor(x), yi = Math.floor(y);
    const xf = x - xi, yf = y - yi;
    const X = xi & 255, Y = yi & 255;
    const g = (h, dx, dy) => { const k = h & 7; return GX[k] * dx + GY[k] * dy; };
    const aa = p[p[X] + Y], ab = p[p[X] + Y + 1], ba = p[p[X + 1] + Y], bb = p[p[X + 1] + Y + 1];
    const u = fade(xf), v = fade(yf);
    const x1 = g(aa, xf, yf) + u * (g(ba, xf - 1, yf) - g(aa, xf, yf));
    const x2 = g(ab, xf, yf - 1) + u * (g(bb, xf - 1, yf - 1) - g(ab, xf, yf - 1));
    return (x1 + v * (x2 - x1)) * 0.7071;   // about -1..1
  }
  return n2;
}

function wildsSmooth(e0, e1, x) {
  const t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0)));
  return t * t * (3 - 2 * t);
}

/* One world's ground. `world` is the registry entry; every field read here
   is required by wilds/build.py, so nothing is defaulted. */
function wildsTerrain(world) {
  const b = world.biome;
  const n = wildsNoise(world.seed);
  const n2 = wildsNoise(world.seed ^ 0x5bd1e995);
  const half = world.extent_m / 2;
  const fbm = (x, z, oct, sc) => {
    let s = 0, a = 1, f = 1 / sc, tot = 0;
    for (let o = 0; o < oct; o++) { s += a * n(x * f, z * f); tot += a; a *= 0.5; f *= 2.03; }
    return s / tot;
  };
  const ridged = (x, z, oct, sc) => {
    let s = 0, a = 1, f = 1 / sc, tot = 0, w = 1;
    for (let o = 0; o < oct; o++) {
      let r = 1 - Math.abs(n2(x * f, z * f)); r *= r; r *= w; w = Math.min(1, r * 2);
      s += a * r; tot += a; a *= 0.5; f *= 2.01;
    }
    return s / tot;
  };
  function raw(x, z) {
    let h;
    if (b.model === 'ridged') {
      const mass = 0.5 + 0.5 * fbm(x + 913, z - 377, 3, b.feature_m * 2.2);
      h = b.relief_m * Math.pow(ridged(x, z, b.octaves, b.feature_m), 1.25) * (0.35 + 0.9 * mass)
        + b.relief_m * 0.18 * fbm(x, z, 3, b.feature_m * 0.5);
    } else if (b.model === 'rolling') {
      h = b.relief_m * (0.55 * fbm(x, z, b.octaves, b.feature_m)
        + 0.3 * fbm(x - 4000, z + 2500, 3, b.feature_m * 3));
    } else if (b.model === 'canyon') {
      const plateau = b.relief_m * (0.6 + 0.25 * fbm(x, z, b.octaves, b.feature_m));
      const steps = b.terrace_m;
      const terr = Math.floor(plateau / steps) * steps + steps * wildsSmooth(0.75, 1, (plateau / steps) % 1);
      const riverX = b.river_amp_m * Math.sin(z / b.river_wavelength_m) + b.river_amp_m * 0.4 * Math.sin(z / (b.river_wavelength_m * 0.37) + 1.3);
      const d = Math.abs(x - riverX);
      const cut = 1 - wildsSmooth(b.river_half_m, b.canyon_half_m, d + 25 * fbm(x, z, 2, 180));
      h = terr * (1 - cut) + (b.water_level_m - 6) * cut;
    } else {
      throw new Error('wildsTerrain: unknown biome.model ' + b.model);
    }
    // the edge of the world rises to a rim so nobody walks off it
    const edge = Math.max(Math.abs(x), Math.abs(z));
    h += b.rim_m * wildsSmooth(half - b.rim_width_m, half, edge);
    return h;
  }
  // site pads are levelled to their own centre; a hidden hollow is a bowl
  const pads = world.sites.map((s) => ({ x: s.x, z: s.z, r: s.pad_m, h: raw(s.x, s.z) }));
  pads.push({ x: world.trailhead.x, z: world.trailhead.z, r: world.trailhead.pad_m, h: raw(world.trailhead.x, world.trailhead.z) });
  const hollows = world.caches.filter((c) => c.kind === 'hollow')
    .map((c) => ({ x: c.x, z: c.z, r: c.hollow_m, d: c.hollow_depth_m }));
  function height(x, z) {
    let h = raw(x, z);
    for (const p of pads) {
      const dx = x - p.x, dz = z - p.z;
      const d2 = dx * dx + dz * dz, R = p.r * 1.8;
      if (d2 < R * R) h += (p.h - h) * (1 - wildsSmooth(p.r, R, Math.sqrt(d2)));
    }
    for (const o of hollows) {
      const dx = x - o.x, dz = z - o.z, d = Math.sqrt(dx * dx + dz * dz);
      if (d < o.r) { const k = 1 - d / o.r; h -= o.d * k * k * (3 - 2 * k); }
    }
    return h;
  }
  function slope(x, z) {
    const e = 4;
    const gx = (height(x + e, z) - height(x - e, z)) / (2 * e);
    const gz = (height(x, z + e) - height(x, z - e)) / (2 * e);
    return Math.sqrt(gx * gx + gz * gz);
  }
  /* Vegetation density 0..1 for one species at a point: the biome's bands
     (water, tree line, snow line, steepness) decide where anything grows. */
  function growth(x, z, h, s) {
    if (h < b.water_level_m + 1.5) return { conifer: 0, deciduous: 0, rock: s > 0.5 ? 0.3 : 0.05 };
    const tl = b.tree_line_m + 40 * n(x / 300, z / 300);
    const alpine = 1 - wildsSmooth(tl - 60, tl, h);
    const flat = 1 - wildsSmooth(b.max_tree_slope - 0.15, b.max_tree_slope, s);
    const patch = 0.5 + 0.5 * fbm(x + 7000, z - 7000, 3, b.stand_m);
    const tree = b.tree_density * alpine * flat * wildsSmooth(b.clearing, b.clearing + 0.25, patch);
    const decid = b.deciduous_share * (0.5 + 0.5 * n(x / 700 + 11, z / 700 - 3));
    const rock = b.rock_density * (0.25 + wildsSmooth(0.35, 0.9, s) + (1 - alpine) * 0.6);
    return { conifer: tree * (1 - decid), deciduous: tree * decid, rock: Math.min(1, rock) };
  }
  /* The highest ground on a coarse grid, then refined: the summit register
     is placed here, so it is derived from the seed, never typed. */
  function summit() {
    let best = { x: 0, z: 0, h: -1e9 };
    const step = world.extent_m / 96, lim = half - b.rim_width_m - 200;
    for (let x = -lim; x <= lim; x += step) for (let z = -lim; z <= lim; z += step) {
      const h = height(x, z); if (h > best.h) best = { x, z, h };
    }
    for (let r = step / 2; r > 2; r /= 2) {
      let moved = true;
      while (moved) {
        moved = false;
        for (const [dx, dz] of [[r, 0], [-r, 0], [0, r], [0, -r]]) {
          const h = height(best.x + dx, best.z + dz);
          if (h > best.h) { best = { x: best.x + dx, z: best.z + dz, h }; moved = true; }
        }
      }
    }
    return best;
  }
  return { height, slope, growth, summit, raw, half };
}

/* Deterministic scatter: one candidate per cell, jittered by a hash of the
   cell and the seed, kept when the growth density beats the hash. */
function wildsHash(ix, iz, seed, k) {
  let h = Math.imul(ix, 374761393) ^ Math.imul(iz, 668265263) ^ Math.imul(seed, 2246822519) ^ Math.imul(k, 3266489917);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}
/* WILDS_CORE:END */

export { wildsMulberry, wildsNoise, wildsSmooth, wildsTerrain, wildsHash };
