#!/usr/bin/env python3
"""PHYS_JS: the arcade physics module (as a string), for any page.

What it gives a page (every top-level name starts with `phys`/`PHYS_`, plus
the alias `createPhysics`, so it can be pasted into another module script):
  - createPhysics({reg, cell, ground, water}) a world: a uniform grid hash of
    oriented boxes (solid buildings, curbs, barriers), addBoxes / query /
    supportAt;
  - W.stepAvatar(av, input, dt)                 gravity, jump, fall, step-up
    onto curbs, slide along walls, sub-stepped so nothing tunnels, and water
    states dry / wade / swim with splash / climb-out events (no drowning is
    ever depicted: a swimmer floats with the head above the surface);
  - physBody + W.stepBody(b, dt)                a small generic rigid body
    (sphere, or a box by its bounding sphere) against ground and boxes;
  - physWaterState(depth, reg)                  the pure wade/swim rule.

No THREE and no DOM: pure functions over plain objects, so the whole module
runs in node (physics/test.mjs). Gravity is standard gravity 9.81 m/s^2; every
other coefficient comes from physics/registry/physics.json and is AUTHORED for
play - an arcade approximation, not engineering or safety advice.

    python3 web/physkit.py            prints the module size and exports
    python3 web/physkit.py --out F    writes the module to F (tests import it)
"""
import re
import sys

PHYS_JS = r'''/* PHYS_KIT:BEGIN - physics/registry/physics.json driver (web/physkit.py). Arcade physics, AUTHORED coefficients. */
const PHYS_API = 1;
const PHYS_PEDESTRIAN_CLASSES = ['person', 'npc', 'pet', 'animal'];
const PHYS_BUDGET = { maxBoxes: 60000, avatarMs: 0.5, bodies: 64 };
const PHYS_BOX_KINDS = ['building', 'curb', 'barrier', 'wall', 'prop'];
function physNeed(o, k, where) {
  if (o === null || typeof o !== 'object' || !(k in o)) throw new Error('physkit: ' + where + ' has no ' + k);
  return o[k];
}
/* the registry's coefficients as a flat {group: {name: value}}; every field read directly (fail closed) */
function physCoeffs(reg) {
  if (physNeed(reg, 'pack', 'registry') !== 'physics') throw new Error('physkit: registry pack is not physics');
  const cs = physNeed(reg, 'coeffs', 'registry'), out = {};
  for (const g of ['world', 'avatar', 'water', 'body', 'crash']) {
    const grp = physNeed(cs, g, 'coeffs'); out[g] = {};
    for (const k of Object.keys(grp)) out[g][k] = physNeed(grp[k], 'value', 'coeffs.' + g + '.' + k);
  }
  for (const [g, k] of [['world', 'gravity'], ['avatar', 'radius'], ['avatar', 'height'], ['avatar', 'step_up'], ['avatar', 'jump_speed'],
    ['water', 'wade_min'], ['water', 'swim_depth'], ['water', 'float_depth'], ['body', 'restitution'], ['body', 'friction']]) physNeed(out[g], k, 'coeffs.' + g);
  return out;
}
/* depth of water at the feet -> 'dry' | 'wade' | 'swim' */
function physWaterState(depth, C) {
  const w = C.water;
  if (!(depth >= w.wade_min)) return 'dry';
  return depth >= w.swim_depth ? 'swim' : 'wade';
}
/* ------------------------------------------------ oriented boxes (xz) --- */
/* a box: {id, cx, cz, hx, hz, yaw, y0, y1, kind}; local x axis = (cos yaw, -sin yaw), local z = (sin yaw, cos yaw) */
function physBoxCheck(b, i) {
  for (const k of ['id', 'cx', 'cz', 'hx', 'hz', 'yaw', 'y0', 'y1', 'kind']) physNeed(b, k, 'box[' + i + ']');
  if (!(b.hx > 0 && b.hz > 0 && b.y1 > b.y0)) throw new Error('physkit: box ' + b.id + ' has no size');
  if (!PHYS_BOX_KINDS.includes(b.kind)) throw new Error('physkit: box ' + b.id + ' kind ' + b.kind + ' is not one of ' + PHYS_BOX_KINDS.join('/'));
  const c = Math.cos(b.yaw), s = Math.sin(b.yaw);
  return { ...b, c, s, ex: Math.abs(c) * b.hx + Math.abs(s) * b.hz, ez: Math.abs(s) * b.hx + Math.abs(c) * b.hz };
}
/* closest point of box b's footprint to (x, z): {px, pz, d, nx, nz, inside, depth} (n points from the box to the point) */
function physBoxClosest(b, x, z) {
  const dx = x - b.cx, dz = z - b.cz;
  const lx = dx * b.c - dz * b.s, lz = dx * b.s + dz * b.c;
  const inside = Math.abs(lx) <= b.hx && Math.abs(lz) <= b.hz;
  let qx = Math.max(-b.hx, Math.min(b.hx, lx)), qz = Math.max(-b.hz, Math.min(b.hz, lz)), depth = 0, lnx = 0, lnz = 0;
  if (inside) {   // push out through the nearest face
    const fx = b.hx - Math.abs(lx), fz = b.hz - Math.abs(lz);
    if (fx < fz) { lnx = Math.sign(lx || 1); qx = lnx * b.hx; depth = fx; } else { lnz = Math.sign(lz || 1); qz = lnz * b.hz; depth = fz; }
  }
  const px = b.cx + qx * b.c + qz * b.s, pz = b.cz - qx * b.s + qz * b.c;
  let nx = x - px, nz = z - pz, d = Math.hypot(nx, nz);
  if (inside) { nx = lnx * b.c + lnz * b.s; nz = -lnx * b.s + lnz * b.c; d = -depth; }
  else if (d > 0) { nx /= d; nz /= d; }
  return { px, pz, d, nx, nz, inside };
}
/* ---------------------------------------------------------- the world --- */
function physCreate(opts) {
  const reg = physNeed(opts, 'reg', 'createPhysics opts'), cell = physNeed(opts, 'cell', 'createPhysics opts');
  const ground = physNeed(opts, 'ground', 'createPhysics opts'), water = physNeed(opts, 'water', 'createPhysics opts');
  if (!(cell > 0)) throw new Error('physkit: cell must be > 0');
  if (typeof ground !== 'function' || typeof water !== 'function') throw new Error('physkit: ground and water must be functions (x, z)');
  const C = physCoeffs(reg), g = C.world.gravity;
  const boxes = [], grid = new Map();
  let mark = 1; const seen = [];
  const key = (i, j) => (i + 32768) * 65536 + (j + 32768);
  function addBoxes(list) {
    if (!Array.isArray(list)) throw new Error('physkit: addBoxes needs an array');
    if (boxes.length + list.length > PHYS_BUDGET.maxBoxes) throw new Error('physkit: ' + (boxes.length + list.length) + ' boxes is over the budget ' + PHYS_BUDGET.maxBoxes);
    list.forEach((raw, n) => {
      const b = physBoxCheck(raw, boxes.length + n), idx = boxes.length;
      boxes.push(b); seen.push(0);
      for (let i = Math.floor((b.cx - b.ex) / cell); i <= Math.floor((b.cx + b.ex) / cell); i++)
        for (let j = Math.floor((b.cz - b.ez) / cell); j <= Math.floor((b.cz + b.ez) / cell); j++) {
          const k = key(i, j); if (!grid.has(k)) grid.set(k, []); grid.get(k).push(idx);
        }
    });
    return boxes.length;
  }
  function query(x, z, r) {
    const out = []; mark++;
    for (let i = Math.floor((x - r) / cell); i <= Math.floor((x + r) / cell); i++)
      for (let j = Math.floor((z - r) / cell); j <= Math.floor((z + r) / cell); j++) {
        const list = grid.get(key(i, j)); if (!list) continue;
        for (const idx of list) {
          if (seen[idx] === mark) continue; seen[idx] = mark;
          const b = boxes[idx];
          if (Math.abs(x - b.cx) > b.ex + r || Math.abs(z - b.cz) > b.ez + r) continue;
          if (physBoxClosest(b, x, z).d < r) out.push(b);
        }
      }
    return out;
  }
  /* the floor under (x, z): water bed where water() says so, else ground() */
  function floorAt(x, z) { const w = water(x, z); return w ? physNeed(w, 'bed', 'water(x, z)') : ground(x, z); }
  /* highest floor or box top at or below yTop under a circle of radius r */
  function supportAt(x, z, yTop, r) {
    let y = floorAt(x, z);
    for (const b of query(x, z, r)) if (b.y1 <= yTop && b.y1 > y) y = b.y1;
    return y;
  }
  function waterDepthAt(x, y, z) { const w = water(x, z); return w ? physNeed(w, 'surface', 'water(x, z)') - y : 0; }
  /* push a circle (x, z, r) out of the boxes that span [yLo, yHi]; removes the velocity into each wall (slide) */
  function pushOut(o, r, yLo, yHi, skipBelow) {
    let hit = null;
    for (let pass = 0; pass < 3; pass++) {
      let moved = false;
      for (const b of query(o.x, o.z, r)) {
        if (b.y1 <= yLo + 1e-6 || b.y0 >= yHi) continue;
        if (b.y1 <= skipBelow) continue;              // a ledge low enough to step onto
        const q = physBoxClosest(b, o.x, o.z);
        if (q.d >= r) continue;
        const push = r - q.d + 1e-4;
        o.x += q.nx * push; o.z += q.nz * push; moved = true; hit = b;
        const vn = o.vx * q.nx + o.vz * q.nz;
        if (vn < 0) { o.vx -= vn * q.nx; o.vz -= vn * q.nz; }
      }
      if (!moved) break;
    }
    return hit;
  }
  function stepAvatar(av, input, dt) {
    const A = C.avatar, Wt = C.water, ev = [];
    const vx0 = physNeed(input, 'vx', 'avatar input'), vz0 = physNeed(input, 'vz', 'avatar input'), jump = physNeed(input, 'jump', 'avatar input');
    const before = av.water;
    // horizontal intent, scaled by the water state; eased (full on ground/swimming, air_control in the air)
    const mul = av.water === 'swim' ? Wt.swim_speed : av.water === 'wade' ? Wt.wade_speed : 1;
    const ctl = av.onGround || av.water === 'swim' ? 1 : A.air_control;
    const k = Math.min(1, A.ground_accel * dt / Math.max(1e-6, Math.hypot(vx0 * mul - av.vx, vz0 * mul - av.vz))) * ctl;
    av.vx += (vx0 * mul - av.vx) * k; av.vz += (vz0 * mul - av.vz) * k;
    if (jump && av.onGround && av.water !== 'swim') { av.vy = A.jump_speed; av.onGround = false; ev.push({ type: 'jump' }); }
    const speed = Math.hypot(av.vx, av.vy, av.vz);
    const n = Math.min(400, Math.max(1, Math.ceil(speed * dt / (A.radius * C.world.max_substep_frac))));
    const h = dt / n;
    for (let i = 0; i < n; i++) {
      const depth = waterDepthAt(av.x, av.y, av.z), state = physWaterState(depth, C);
      if (state === 'swim') {   // floats: gravity cancelled, eased to the float depth (head above the surface)
        const surf = av.y + depth, target = surf - Wt.float_depth;
        av.vy = (target - av.y) * Wt.float_rate;
      } else { av.vy = Math.max(-A.max_fall_speed, av.vy - g * h); }
      const px = av.x, pz = av.z, fy = av.y;
      av.x += av.vx * h; av.z += av.vz * h;
      pushOut(av, A.radius, av.y, av.y + A.height, av.y + A.step_up);
      // a heightfield step taller than step_up is a bank: blocked on land, climbable out of water (up to float_depth)
      const nf = floorAt(av.x, av.z);
      const allow = state === 'dry' ? nf <= av.y + A.step_up : nf <= av.y + depth + Wt.climb_out_m;   // out of water: up to climb_out_m above the surface
      if (!allow) { av.x = px; av.z = pz; av.vx = 0; av.vz = 0; }
      av.y += av.vy * h;
      const sup = supportAt(av.x, av.z, Math.max(fy, av.y) + A.step_up, A.radius * 0.7);
      if (av.y <= sup) {
        if (!av.onGround && av.vy < -A.land_event_speed) ev.push({ type: 'land', speed: -av.vy });
        av.y = sup; av.vy = Math.max(0, av.vy); av.onGround = true; av.airT = 0;
      } else if (av.onGround && av.vy <= 0 && av.y - sup <= A.step_up) { av.y = sup; av.vy = 0; }   // down a curb, still walking
      else { av.onGround = false; }
      // head: a box above stops the rise
      if (av.vy > 0) for (const b of query(av.x, av.z, A.radius * 0.7)) if (b.y0 > fy + A.height - 0.05 && b.y0 < av.y + A.height) { av.y = b.y0 - A.height; av.vy = 0; }
    }
    if (!av.onGround) av.airT += dt;
    const after = physWaterState(waterDepthAt(av.x, av.y, av.z), C);
    if (after !== before) {
      if (before === 'dry') {
        ev.push({ type: 'enter-water', state: after });
        const sp = Math.max(-av.vy, Math.hypot(av.vx, av.vz));
        if (sp >= Wt.splash_speed || av.airT > 0 || after === 'swim') ev.push({ type: 'splash', strength: Math.min(1, sp / 10), x: av.x, z: av.z });
      } else if (before === 'swim') ev.push({ type: 'climb-out', to: after });
      else if (after === 'swim') ev.push({ type: 'swim' });
      else ev.push({ type: 'leave-water' });
      av.water = after;
    }
    return ev;
  }
  function stepBody(b, dt) {
    const B = C.body, Wt = C.water, ev = [];
    if (b.sleeping) return ev;
    const n = Math.min(200, Math.max(1, Math.ceil(Math.hypot(b.vx, b.vy, b.vz) * dt / (b.r * 0.5))));
    const h = dt / n;
    for (let i = 0; i < n; i++) {
      const depth = waterDepthAt(b.x, b.y - b.r, b.z);   // water above the body's lowest point
      b.vy -= g * h;
      if (depth > 0) {   // AUTHORED buoyancy on the submerged share of the bounding sphere, and water drag
        const sub = Math.min(1, depth / (2 * b.r));
        b.vy += Wt.body_buoyancy * g * sub * h;
        const d = Math.exp(-Wt.water_drag * h); b.vx *= d; b.vy *= d; b.vz *= d;
      } else { const d = Math.exp(-B.air_drag * h); b.vx *= d; b.vz *= d; }
      b.x += b.vx * h; b.y += b.vy * h; b.z += b.vz * h;
      // boxes (3D: footprint clamp + vertical clamp)
      for (const bx of query(b.x, b.z, b.r)) {
        const q = physBoxClosest(bx, b.x, b.z);
        const cy = Math.max(bx.y0, Math.min(bx.y1, b.y));
        let nx, ny, nz, d;
        if (q.inside && b.y > bx.y0 && b.y < bx.y1) { const up = bx.y1 - b.y; if (up < -q.d) { nx = 0; ny = 1; nz = 0; d = -up; } else { nx = q.nx; ny = 0; nz = q.nz; d = q.d; } }
        else { const hx = q.inside ? 0 : b.x - q.px, hz = q.inside ? 0 : b.z - q.pz, hy = b.y - cy; d = Math.hypot(hx, hy, hz); if (d >= b.r || d === 0) continue; nx = hx / d; ny = hy / d; nz = hz / d; }
        const push = b.r - d; b.x += nx * push; b.y += ny * push; b.z += nz * push;
        const vn = b.vx * nx + b.vy * ny + b.vz * nz;
        if (vn < 0) {
          b.vx -= (1 + B.restitution) * vn * nx; b.vy -= (1 + B.restitution) * vn * ny; b.vz -= (1 + B.restitution) * vn * nz;
          const f = Math.max(0, 1 - B.friction * h * g); b.vx *= ny > 0.5 ? f : 1; b.vz *= ny > 0.5 ? f : 1;
          if (-vn > 1) ev.push({ type: 'hit', with: bx.kind, id: bx.id, speed: -vn });
        }
      }
      const fl = floorAt(b.x, b.z);
      if (b.y - b.r < fl) {
        b.y = fl + b.r;
        if (b.vy < 0) { if (-b.vy > 1) ev.push({ type: 'hit', with: 'ground', speed: -b.vy }); b.vy = -b.vy * B.restitution; if (b.vy < 0.3) b.vy = 0; }
        const sp = Math.hypot(b.vx, b.vz), dv = B.friction * g * h;
        if (sp <= dv) { b.vx = 0; b.vz = 0; } else { b.vx -= b.vx / sp * dv; b.vz -= b.vz / sp * dv; }
        if (Math.hypot(b.vx, b.vy, b.vz) < B.sleep_speed && depth <= 0) { b.vx = b.vy = b.vz = 0; b.sleeping = true; break; }
      }
    }
    return ev;
  }
  return { coeffs: C, boxes, addBoxes, query, supportAt, floorAt, waterDepthAt, stepAvatar, stepBody, water, ground, cell };
}
const createPhysics = physCreate;
function physAvatar(x, y, z) { return { x, y, z, vx: 0, vy: 0, vz: 0, onGround: false, water: 'dry', airT: 0 }; }
function physBody(o) {
  for (const k of ['shape', 'x', 'y', 'z', 'r', 'mass']) physNeed(o, k, 'physBody');
  if (o.shape !== 'sphere' && o.shape !== 'box') throw new Error('physkit: body shape ' + o.shape + ' (sphere | box)');
  return { shape: o.shape, x: o.x, y: o.y, z: o.z, r: o.r, mass: o.mass, vx: 0, vy: 0, vz: 0, sleeping: false };
}
/* ---------------------------------------- PARISH v1.4 world adapters --- */
/* a chunk's building block list [x, z, w, h, d, family, yaw] (scene WORLD metres, base y 0; the page's own numbers) -> boxes */
function physBlockBoxes(chunkKey, block) {
  return block.map((r, i) => {
    if (!Array.isArray(r) || r.length < 7) throw new Error('physkit: block ' + chunkKey + '[' + i + '] is not [x, z, w, h, d, family, yaw]');
    const [x, z, w, h, d, , yaw] = r;
    return { id: chunkKey + ':' + i, cx: x, cz: z, hx: w / 2, hz: d / 2, yaw, y0: 0, y1: h, kind: 'building' };
  });
}
/* sidewalk slabs (kind 'curb') both sides of each polyline: [[x, z], ...] in scene metres; profile = world roads.classes[c] */
function physCurbBoxes(idPrefix, polylines, profile) {
  const cw = physNeed(profile, 'carriageway_m', 'road profile'), co = physNeed(profile, 'corridor_m', 'road profile');
  const ch = physNeed(profile, 'curb_height_m', 'road profile'), half = (co - cw) / 4, off = (cw + co) / 4, out = [];
  polylines.forEach((pl, k) => {
    for (let i = 0; i + 1 < pl.length; i++) {
      const [x0, z0] = pl[i], [x1, z1] = pl[i + 1], len = Math.hypot(x1 - x0, z1 - z0);
      if (len < 0.01) continue;
      const yaw = Math.atan2(x1 - x0, z1 - z0), rx = Math.cos(yaw), rz = -Math.sin(yaw), mx = (x0 + x1) / 2, mz = (z0 + z1) / 2;
      for (const sgn of [1, -1]) out.push({ id: idPrefix + ':' + k + ':' + i + (sgn > 0 ? 'r' : 'l'), cx: mx + sgn * off * rx, cz: mz + sgn * off * rz,
        hx: half, hz: len / 2, yaw, y0: 0, y1: ch, kind: 'curb' });
    }
  });
  return out;
}
function physInRing(ring, x, z) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, zi] = ring[i], [xj, zj] = ring[j];
    if ((zi > z) !== (zj > z) && x < (xj - xi) * (z - zi) / (zj - zi) + xi) inside = !inside;
  }
  return inside;
}
/* parishes/maps/world/<fips>.json water (parish LOCAL [e, n]) -> water(x, z) for createPhysics, scene frame via
   origin = parish.frame.origin_in_world_m: x = e + oe, z = -(n + on). Bucketed by a 64 m grid. */
function physWaterFromWorld(file, origin) {
  const w = physNeed(file, 'water', 'world file');
  if (physNeed(w, 'provenance', 'world water') !== 'AUTHORED') throw new Error('physkit: world water must be AUTHORED');
  const surf = physNeed(w, 'surface_y_m', 'world water'), [oe, on] = origin, cell = 64, grid = new Map(), polys = [];
  for (const kind of ['lakes', 'channels', 'ponds']) for (const f of physNeed(w, kind, 'world water')) {
    const ring = physNeed(f, 'polygon', kind).map(([e, n]) => [e + oe, -(n + on)]), depth = physNeed(f, 'depth_m', kind);
    let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
    for (const [x, z] of ring) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); z0 = Math.min(z0, z); z1 = Math.max(z1, z); }
    const idx = polys.length; polys.push({ id: physNeed(f, 'id', kind), ring, bed: surf - depth });
    for (let i = Math.floor(x0 / cell); i <= Math.floor(x1 / cell); i++) for (let j = Math.floor(z0 / cell); j <= Math.floor(z1 / cell); j++) {
      const k = i + ',' + j; if (!grid.has(k)) grid.set(k, []); grid.get(k).push(idx);
    }
  }
  const fn = (x, z) => {
    const list = grid.get(Math.floor(x / cell) + ',' + Math.floor(z / cell));
    if (!list) return null;
    let best = null;
    for (const i of list) if (physInRing(polys[i].ring, x, z) && (!best || polys[i].bed < best.bed)) best = { surface: surf, bed: polys[i].bed, id: polys[i].id };
    return best;
  };
  fn.features = polys.length;
  return fn;
}
/* PHYS_KIT:END */
export { PHYS_API, PHYS_PEDESTRIAN_CLASSES, PHYS_BUDGET, PHYS_BOX_KINDS, physCoeffs, physWaterState, physBoxCheck, physBoxClosest,
  physCreate, createPhysics, physAvatar, physBody, physBlockBoxes, physCurbBoxes, physInRing, physWaterFromWorld };
'''

EXPORTS = re.findall(r'export \{([^}]*)\}', PHYS_JS)[0].replace('\n', ' ').split(',')
EXPORTS = [e.strip() for e in EXPORTS if e.strip()]
BEGIN, END = '/* PHYS_KIT:BEGIN', '/* PHYS_KIT:END */'


def phys_inline():
    """The module body without its export line, for pasting into a page's own module script."""
    return PHYS_JS[:PHYS_JS.index(END) + len(END)]


if __name__ == '__main__':
    if '--out' in sys.argv:
        open(sys.argv[sys.argv.index('--out') + 1], 'w').write(PHYS_JS)
    print(f'PHYS_JS: {len(PHYS_JS)} bytes, {len(EXPORTS)} exports: {", ".join(EXPORTS)}')
