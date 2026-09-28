#!/usr/bin/env python3
"""FLEET_JS: the fleet's embeddable ES module (as a string), for any page.

What it gives a page (every top-level name starts with `fleet` so it can be
pasted into another module script without clashing):
  - fleetFamilyGeometry(THREE, recipe, ref)   procedural low-poly geometry of a
    family, in metres, at the family's reference size, vertex colour = palette
    slot (body / trim / accent);
  - fleetCreate(THREE, reg, capacity)          ONE InstancedMesh per family
    (so N vehicles of a family cost one draw call), with spawn/set/despawn;
  - fleetState / fleetLandStep / fleetBoatStep pure arcade physics (no THREE):
    land moves only over dry ground, a boat only over water deep enough for
    its draft, with a buoyancy bob; a move onto the wrong medium is REFUSED;
  - fleetCanSpawn, fleetGroundFromWilds, fleetFlatGround   ground adapters;
  - fleetNearest / fleetExitPoint / fleetChaseCamera        enter, exit, camera;
  - fleetWake(THREE, cap)                      a boat wake, one draw call.

All handling is SCHEMATIC arcade physics driven by the registry's AUTHORED
figures (fleet/registry/fleet.json); it is not any vehicle's real response,
the same doctrine the training seats in web/build_3d.py keep.

    python3 web/fleetkit.py            prints the module size and exports
    python3 web/fleetkit.py --out F    writes the module to F (tests import it)
"""
import re
import sys

FLEET_JS = r'''/* FLEET_KIT:BEGIN - fleet/registry/fleet.json driver (web/fleetkit.py). SCHEMATIC arcade physics. */
const FLEET_API = 1;
const FLEET_SLOTS = ['body', 'trim', 'accent'];
const FLEET_MIN_WET_M = 0.15;      // water shallower than this is dry ground for a land vehicle
const FLEET_KEEL_CLEAR_M = 0.1;    // a boat needs its draft plus this under the keel
const FLEET_STEER_VIS = 0.5;       // front-wheel angle (rad) at full steer, drawn only
const FLEET_BRAKE_GAIN = 3.0;      // extra tail-lamp glow at full brake, per instance (drawn only)

function fleetNeed(o, k, where) {
  if (o === null || typeof o !== 'object' || !(k in o) || o[k] === undefined)
    throw new Error('fleetkit: ' + where + ' has no ' + k);
  return o[k];
}

/* ----------------------------------------------------------- geometry --- */
function fleetGeoBuilder(THREE) {
  const pos = [], nor = [], col = [], lampA = [];
  const slotRGB = { body: [1, 0, 0], trim: [0, 1, 0], accent: [0, 0, 1] };
  function add(g, slot, m, lamp = 0) {
    const s = lamp ? [0, 0, 0] : slotRGB[slot];
    if (!s) throw new Error('fleetkit: unknown palette slot ' + slot);
    const ng = g.index ? g.toNonIndexed() : g;
    if (m) ng.applyMatrix4(m);
    ng.computeVertexNormals();
    const p = ng.attributes.position.array, n = ng.attributes.normal.array;
    for (let i = 0; i < p.length; i++) { pos.push(p[i]); nor.push(n[i]); }
    for (let i = 0; i < p.length / 3; i++) { col.push(s[0], s[1], s[2]); lampA.push(lamp); }
    ng.dispose(); if (ng !== g) g.dispose();
  }
  const M = () => new THREE.Matrix4();
  const api = {
    box(cx, cy, cz, sx, sy, sz, slot, rx = 0) {
      const m = M().makeTranslation(cx, cy, cz);
      if (rx) m.multiply(M().makeRotationX(rx));
      add(new THREE.BoxGeometry(Math.max(sx, 1e-3), Math.max(sy, 1e-3), Math.max(sz, 1e-3)), slot, m);
    },
    lamp(cx, cy, cz, sx, sy, sz, kind) {   // kind 1 = head/mast (white), 2 = tail (red): emissive, see fleetMaterial
      add(new THREE.BoxGeometry(sx, sy, sz), 'body', M().makeTranslation(cx, cy, cz), kind);
    },
    wheel(cx, cy, cz, r, w, slot) {   // axis along x
      const m = M().makeTranslation(cx, cy, cz).multiply(M().makeRotationZ(Math.PI / 2));
      add(new THREE.CylinderGeometry(r, r, w, 10), slot, m);
    },
    disc(cx, cy, cz, r, slot, tilt) {   // a thin disc facing +z (the driver looks along +z), tilted back by tilt
      const m = M().makeTranslation(cx, cy, cz).multiply(M().makeRotationX(Math.PI / 2 - tilt));
      add(new THREE.CylinderGeometry(r, r, 0.04, 10), slot, m);
    },
    rod(cx, cy, cz, r, len, slot, rx) {   // a cylinder in the y-z plane, tilted rx from vertical
      const m = M().makeTranslation(cx, cy, cz).multiply(M().makeRotationX(rx));
      add(new THREE.CylinderGeometry(r, r, len, 6), slot, m);
    },
    hull(L, W, depth, bow, stern, slot) {   // plan-view outline extruded upward 0..depth; +z is the bow
      const s = new THREE.Shape();
      const hw = W / 2, zb = L / 2, zs = -L / 2;
      const taper = (k) => k * L;
      // shape y = -world z
      s.moveTo(-hw * stern, -zs);
      s.lineTo(hw * stern, -zs);
      s.lineTo(hw, -(zs + taper(0.12)));
      s.lineTo(hw, -(zb - taper(bow)));
      s.lineTo(hw * 0.12, -zb);
      s.lineTo(-hw * 0.12, -zb);
      s.lineTo(-hw, -(zb - taper(bow)));
      s.lineTo(-hw, -(zs + taper(0.12)));
      s.closePath();
      const g = new THREE.ExtrudeGeometry(s, { depth, bevelEnabled: false });
      add(g, slot, M().makeRotationX(-Math.PI / 2));
    },
    done() {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
      g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
      g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
      g.setAttribute('fleetLamp', new THREE.Float32BufferAttribute(lampA, 1));
      g.computeBoundingBox(); g.computeBoundingSphere();
      return g;
    },
  };
  return api;
}

/* Wheel layout of one vehicle, in its own metres (so a wheel is round at any
   size): [{x, y, z, r, w, front}]. Land only; the wheels are drawn by ONE
   InstancedMesh shared by every family, so they can spin and steer. */
function fleetWheelLayout(recipe, L, W, H) {
  if (recipe.wheel_r === null) return [];
  const r = recipe.wheel_r * H;
  if (recipe.archetype === 'cycle') return [{ x: 0, y: r, z: L / 2 - r, r, w: 0.06, front: true }, { x: 0, y: r, z: -L / 2 + r, r, w: 0.06, front: false }];
  const tw = Math.min(0.4, W * 0.16), n = recipe.axles, inset = Math.max(r * 1.25, L * 0.14);
  const zs = [];
  if (n === 2) zs.push(L / 2 - inset, -L / 2 + inset);
  else { zs.push(L / 2 - inset); for (let i = 0; i < n - 1; i++) zs.push(-L / 2 + inset + i * r * 2.3); }
  const out = [];
  zs.forEach((z, i) => { for (const sx of [-1, 1]) out.push({ x: sx * (W / 2 - tw / 2), y: r, z, r, w: tw, front: i === 0 }); });
  return out;
}
function fleetWheels(b, recipe, L, W, H) { return recipe.wheel_r * H; }
function fleetLamps(b, recipe, L, W, H, y) {   // head lamps at the front, tail lamps at the back
  const s = Math.max(0.08, Math.min(0.3, W * 0.09));
  for (const sx of [-1, 1]) { b.lamp(sx * W * 0.36, y, L / 2 + 0.02, s * 1.4, s, 0.06, 1); b.lamp(sx * W * 0.38, y, -L / 2 - 0.02, s * 1.2, s, 0.06, 2); }
}

/* The simple cab interior seen from the driver view, placed from the driver's
   eye: a dashboard ahead, a steering wheel between eye and dashboard, the
   driver's seat (and a passenger seat when the eye sits off-centre). Built into
   the FAMILY geometry, so it is shared by the family and costs no extra draw
   call. Cycles have none; paddle craft and open boats get a seat only.
   -> [{part: 'dash'|'wheel'|'seat'|'seatback', x, y, z, sx, sy, sz}] (own metres) */
function fleetCabParts(recipe, L, W, H) {
  const a = recipe.archetype;
  if (a === 'cycle') return [];
  const e = fleetDriverEye({ recipe, L, W, H }), out = [];
  const inZ = (z) => Math.max(-L / 2 + 0.15, Math.min(L / 2 - 0.15, z));
  const low = a === 'paddle';   // a paddler sits on the floor: a low seat and a short back
  const seat = (x) => {
    const sy = low ? H * 0.6 : Math.max(0.15, e.y - 0.8), sw = Math.min(0.5, W * 0.4), bh = low ? 0.25 : 0.55;
    out.push({ part: 'seat', x, y: sy, z: inZ(e.z - 0.1), sx: sw, sy: 0.12, sz: 0.48 });
    out.push({ part: 'seatback', x, y: sy + 0.06 + bh / 2, z: inZ(e.z - 0.38), sx: sw, sy: bh, sz: 0.1 });
  };
  const cab = a === 'car' || a === 'bus' || a === 'truck' || a === 'machine' || (a === 'hull' && recipe.cab_len > 0);
  if (cab) {
    const dz = inZ(e.z + Math.min(0.8, L * 0.2)), wz = e.z + (dz - e.z) * 0.55;
    // inside the driver view's field: the dashboard ~20 deg and the wheel ~25 deg below the eye line
    out.push({ part: 'dash', x: 0, y: e.y - 0.3, z: dz, sx: Math.min(W * 0.8, 2.2), sy: 0.16, sz: 0.28 });
    out.push({ part: 'wheel', x: e.x, y: e.y - 0.26, z: wz, sx: 0.38, sy: 0.38, sz: 0.04 });
  }
  seat(e.x);
  if (cab && Math.abs(e.x) > 0.3 && a !== 'bus') seat(-e.x);
  return out;
}
function fleetCabBuild(b, recipe, L, W, H) {
  const parts = fleetCabParts(recipe, L, W, H);
  for (const q of parts) {
    if (q.part === 'wheel') b.disc(q.x, q.y, q.z, q.sx / 2, 'trim', 0.45);
    else b.box(q.x, q.y, q.z, q.sx, q.sy, q.sz, q.part === 'dash' ? 'trim' : 'accent');
  }
  return parts.length;
}
/* Five families were the least detailed (a box and a box): they get a better
   silhouette. Keyed by recipe shape, so a family's shape is still shared. */
const FLEET_DETAIL = { sedan: 'compact-car', van: 'van', coach: 'bus', frame: 'bicycle', outboard: 'skiff' };
function fleetDetailOf(r) {
  if (r.archetype === 'car' && r.body === 'none') return r.cab_h < 0.6 ? 'sedan' : 'van';
  if (r.archetype === 'bus') return 'coach';
  if (r.archetype === 'cycle' && r.body === 'none') return 'frame';
  if (r.archetype === 'hull' && r.hull === 'v' && r.cab_len === 0 && r.extra === 'none' && r.body === 'none') return 'outboard';
  return null;
}

/* The family's shared geometry, in metres, built at `ref` = {length, width,
   height}; an entry's instance is scaled by its own dims / ref. */
function fleetFamilyGeometry(THREE, recipe, ref) {
  const L = fleetNeed(ref, 'length', 'ref'), W = fleetNeed(ref, 'width', 'ref'), H = fleetNeed(ref, 'height', 'ref');
  for (const k of ['archetype', 'cab_len', 'cab_h', 'body', 'wheel_r', 'axles', 'hull', 'extra']) fleetNeed(recipe, k, 'recipe');
  const b = fleetGeoBuilder(THREE), a = recipe.archetype;
  if (a === 'car' || a === 'bus') {
    const r = fleetWheels(b, recipe, L, W, H);
    const y0 = r * 0.55, y1 = a === 'bus' ? H : H * (1 - recipe.cab_h);
    b.box(0, (y0 + y1) / 2, 0, W, y1 - y0, L, 'body');
    if (a === 'car') {
      const cl = recipe.cab_len * L, cz = -0.04 * L;
      b.box(0, (y1 + H) / 2, cz, W * 0.88, H - y1, cl, 'body');
      b.box(0, y1 + (H - y1) * 0.5, cz, W * 0.9, (H - y1) * 0.55, cl * 0.92, 'accent');
      if (recipe.body === 'bed') b.box(0, y1 + 0.12, -L * 0.33, W * 0.95, 0.24, L * 0.3, 'trim');
    } else {
      b.box(0, H * 0.7, -0.02 * L, W * 1.01, H * 0.28, L * 0.9, 'accent');
      b.box(0, H * 0.62, L / 2, W * 0.9, H * 0.5, 0.06, 'accent');
    }
    b.box(0, y0 + 0.1, L / 2, W * 0.95, 0.18, 0.1, 'trim');
    const det = fleetDetailOf(recipe);
    if (det === 'sedan' || det === 'van') {
      const cl = recipe.cab_len * L, cz = -0.04 * L, gh = H - y1;
      b.box(0, y1 + gh * 0.5, cz + cl / 2 + gh * 0.18, W * 0.84, gh * 0.95, 0.05, 'accent', -0.55);   // raked windscreen
      if (det === 'sedan') b.box(0, y1 + gh * 0.5, cz - cl / 2 - gh * 0.15, W * 0.84, gh * 0.9, 0.05, 'accent', 0.5);   // raked rear glass
      else b.box(0, y1 - 0.02, L / 2 - (L / 2 - cz - cl / 2) / 2, W * 0.9, 0.06, L / 2 - cz - cl / 2, 'body', 0.12);   // sloped nose
      for (const sx of [-1, 1]) b.box(sx * (W / 2 + 0.06), y1 + 0.08, cz + cl / 2 - 0.1, 0.12, 0.1, 0.16, 'trim');   // mirrors
      b.box(0, y0 + (y1 - y0) * 0.45, L / 2 + 0.02, W * 0.4, (y1 - y0) * 0.35, 0.04, 'trim');   // grille
      if (det === 'van') for (const sx of [-1, 1]) b.box(sx * W * 0.38, H + 0.04, cz, 0.05, 0.06, cl * 0.8, 'trim');   // roof rails
    }
    if (det === 'coach') {
      b.box(0, H * 0.62, L / 2 + 0.05, W * 0.88, H * 0.5, 0.05, 'accent', -0.12);        // raked windscreen
      b.box(0, H * 0.93, L / 2 + 0.02, W * 0.6, H * 0.08, 0.06, 'trim');                 // destination sign
      b.box(0, H + 0.12, -0.1 * L, W * 0.55, 0.24, L * 0.22, 'trim');                    // roof pod
      for (const sx of [-1, 1]) { b.box(sx * (W / 2 + 0.12), H * 0.75, L / 2 - 0.1, 0.24, 0.05, 0.05, 'trim'); b.box(sx * (W / 2 + 0.24), H * 0.66, L / 2 - 0.1, 0.06, 0.24, 0.12, 'trim'); }
    }
    fleetLamps(b, recipe, L, W, H, y0 + (y1 - y0) * 0.6);
    b.box(0, y0 + 0.1, -L / 2, W * 0.95, 0.18, 0.1, 'trim');
  } else if (a === 'truck') {
    const r = fleetWheels(b, recipe, L, W, H);
    const cl = recipe.cab_len * L, ch = recipe.cab_h * H, yb = r * 1.05;
    b.box(0, r, 0, W * 0.7, r * 0.5, L * 0.98, 'trim');                         // frame rails
    b.box(0, yb + (ch - yb) / 2, L / 2 - cl / 2, W, ch - yb, cl, 'body');          // cab
    b.box(0, yb + (ch - yb) * 0.72, L / 2 - cl * 0.3, W * 1.01, (ch - yb) * 0.32, cl * 0.5, 'accent');
    const bl = L - cl - 0.15, bz = -L / 2 + bl / 2, top = recipe.body === 'box' ? H : H * 0.62;
    const body = recipe.body;
    if (body === 'box' || body === 'broom') b.box(0, (yb + top) / 2, bz, W, top - yb, bl, 'body');
    if (body === 'broom') b.wheel(0, r * 0.6, L / 2 - cl - 0.4, r * 0.55, W * 0.8, 'accent');
    if (body === 'bed') {
      b.box(0, yb + 0.06, bz, W, 0.12, bl, 'trim');
      for (const sx of [-1, 1]) b.box(sx * (W / 2 - 0.05), yb + 0.3, bz, 0.1, 0.5, bl, 'body');
      b.box(0, yb + 0.3, -L / 2 + 0.05, W, 0.5, 0.1, 'body');
    }
    if (body === 'dump') {
      b.box(0, (yb + H * 0.85) / 2 + 0.1, bz, W, H * 0.85 - yb, bl, 'body');
      b.box(0, H * 0.85 + 0.12, bz, W * 1.02, 0.1, bl, 'trim');
    }
    if (body === 'flat' || body === 'boom' || body === 'lowboy') {
      const dy = body === 'lowboy' ? r * 0.9 : yb + 0.08;
      b.box(0, dy, bz, W, 0.16, bl, 'trim');
      b.box(0, dy + 0.5, L / 2 - cl - 0.2, W * 0.95, 1.0, 0.1, 'trim');       // headboard
    }
    if (body === 'lowboy') b.box(0, r * 0.9 + 0.5, -L / 2 + 0.6, W * 0.9, 0.2, 1.2, 'accent', 0.5);
    if (body === 'boom') {
      const len = bl * 0.9, rx = Math.PI / 2 - 0.35;
      b.rod(0, yb + 0.6 + Math.cos(rx) * len / 2, bz + Math.sin(rx) * len / 2 * 0.2 - bl * 0.1, 0.14, len, 'accent', rx);
      b.box(0, yb + 0.5, -L / 2 + 0.6, 0.8, 0.8, 0.8, 'accent');
    }
    if (body === 'ladder') {
      b.box(0, (yb + H * 0.72) / 2, bz, W, H * 0.72 - yb, bl, 'body');
      b.box(0, H * 0.85, bz + 0.3, W * 0.5, H * 0.14, bl * 1.1, 'trim');
    }
    if (recipe.extra === 'lightbar') b.box(0, ch + 0.08, L / 2 - cl / 2, W * 0.7, 0.14, 0.3, 'accent');
    fleetLamps(b, recipe, L, W, H, yb + 0.35);
  } else if (a === 'machine') {
    const r = fleetWheels(b, recipe, L, W, H);
    const cl = recipe.cab_len * L, ch = recipe.cab_h * H, yb = r * 0.9;
    const tracked = recipe.body === 'arm';
    if (tracked) for (const sx of [-1, 1]) b.box(sx * (W / 2 - W * 0.12), r * 1.2, 0, W * 0.24, r * 2.4, L * 0.55, 'trim');
    b.box(0, yb + r * 0.6, -L * 0.05, W * 0.9, r * 1.2, L * (tracked ? 0.55 : 0.8), 'body');   // chassis / counterweight
    const cz = recipe.body === 'none' ? -L * 0.2 : -L * 0.05;
    b.box(0, yb + r * 1.2 + (ch - yb - r * 1.2) / 2, cz, W * 0.7, ch - yb - r * 1.2, cl, 'body');
    b.box(0, yb + r * 1.2 + (ch - yb - r * 1.2) * 0.6, cz, W * 0.72, (ch - yb - r * 1.2) * 0.45, cl * 0.8, 'accent');
    const fz = L / 2 - L * 0.12;
    b.lamp(0, ch + 0.05, cz + cl / 2, W * 0.3, 0.1, 0.08, 1);
    b.lamp(0, yb + r * 1.2, -L * 0.05 - L * (tracked ? 0.275 : 0.4) - 0.02, W * 0.4, 0.1, 0.06, 2);
    if (recipe.body === 'forks') {
      for (const sx of [-1, 1]) b.box(sx * W * 0.25, H * 0.5, fz, 0.1, H, 0.12, 'trim');
      for (const sx of [-1, 1]) b.box(sx * W * 0.2, 0.08, L / 2 - 0.05, 0.1, 0.06, L * 0.3, 'accent');
    } else if (recipe.body === 'bucket') {
      for (const sx of [-1, 1]) b.box(sx * W * 0.45, H * 0.45, 0, 0.12, 0.2, L * 0.8, 'trim', -0.35);
      b.box(0, 0.35, L / 2 - 0.2, W * 1.02, 0.6, 0.5, 'accent');
    } else if (recipe.body === 'arm') {
      b.rod(0, H * 0.72, L * 0.18, 0.22, L * 0.42, 'accent', Math.PI / 2 - 0.55);
      b.rod(0, H * 0.55, L * 0.4, 0.16, H * 0.8, 'accent', 0.35);
      b.box(0, 0.4, L / 2 - 0.35, W * 0.4, 0.6, 0.6, 'trim');
    } else if (recipe.body === 'boom') {
      b.rod(0, H * 0.75, L * 0.1, 0.2, L * 0.78, 'accent', Math.PI / 2 - 0.12);
      b.box(0, H * 0.95, L / 2 - 0.3, W * 0.7, 0.5, 0.8, 'trim');
    } else if (recipe.body === 'none') {
      b.box(0, yb + r * 0.9, L * 0.25, W * 0.45, r * 1.1, L * 0.45, 'body');   // hood
    }
  } else if (a === 'cycle') {
    const r = recipe.wheel_r * H;
    b.lamp(0, H * 0.8, L / 2 - r * 0.9, 0.1, 0.08, 0.08, 1);
    b.lamp(0, r * 1.4, -L / 2 + r * 0.5, 0.08, 0.06, 0.05, 2);
    if (recipe.body === 'rail') {
      b.box(0, r * 0.7, 0, W * 0.4, 0.08, L * 0.7, 'body');
      b.box(0, H * 0.55, L / 2 - r, 0.06, H * 0.9, 0.06, 'body');
      b.box(0, H * 0.98, L / 2 - r, W, 0.05, 0.05, 'accent');
    } else {
      b.box(0, r * 1.2, 0, 0.07, 0.07, L * 0.62, 'body');
      b.box(0, r * 1.55, -L * 0.12, 0.07, r * 0.9, 0.07, 'body');
      b.box(0, r * 1.55, L * 0.24, 0.07, r * 1.0, 0.07, 'body');
      b.box(0, H * 0.9, -L * 0.14, 0.14, 0.05, 0.24, 'accent');
      b.box(0, H * 0.95, L * 0.25, W, 0.04, 0.04, 'trim');
      if (fleetDetailOf(recipe) === 'frame') {
        b.rod(0, r * 1.05, L * 0.08, 0.035, L * 0.36, 'body', Math.PI / 2 - 0.55);         // down tube
        b.rod(0, r * 0.95, -L * 0.24, 0.03, L * 0.28, 'body', Math.PI / 2 + 0.25);         // chain stay
        b.rod(0, r * 1.25, L / 2 - r * 1.05, 0.03, r * 1.1, 'trim', -0.3);                // fork
        b.box(0, H * 0.88, L * 0.25, 0.05, 0.14, 0.05, 'trim');                           // stem
        b.box(0.05, r, -L * 0.02, 0.02, r * 0.4, r * 0.4, 'accent');                      // chainring
      }
    }
  } else if (a === 'hull' || a === 'paddle') {
    const paddle = a === 'paddle';
    const shape = { v: [0.3, 0.85], flat: [0.08, 0.95], pontoon: [0.06, 1.0], barge: [0.04, 1.0], tub: [0.45, 0.25] }[recipe.hull];
    if (!shape) throw new Error('fleetkit: unknown hull ' + recipe.hull);
    const deck = paddle ? H : (recipe.cab_len > 0 ? H * 0.32 : H * 0.55);
    if (recipe.hull === 'pontoon') {
      for (const sx of [-1, 1]) b.rod(sx * W * 0.32, deck * 0.3, 0, deck * 0.28, L * 0.95, 'trim', Math.PI / 2);
      b.box(0, deck * 0.7, 0, W, deck * 0.18, L * 0.92, 'body');
    } else {
      b.hull(L, W, deck, shape[0], shape[1], 'body');
      b.box(0, deck * 0.35, 0, W * 1.005, deck * 0.08, L * 0.7, 'accent');         // boot stripe
    }
    if (paddle) {
      b.box(0, deck + 0.02, -L * 0.05, W * 0.45, 0.04, L * 0.18, 'trim');           // cockpit / thwart
    } else if (recipe.cab_len > 0) {
      const cl = recipe.cab_len * L, ch = recipe.cab_h * H, cz = -L * 0.08;
      b.box(0, deck + ch / 2, cz, W * 0.78, ch, cl, 'trim');
      b.box(0, deck + ch * 0.7, cz, W * 0.8, ch * 0.3, cl * 0.85, 'accent');
    } else {
      b.box(0, deck + 0.45, -L * 0.05, W * 0.3, 0.9, 0.7, 'trim');                  // console / seat
    }
    if (recipe.body === 'rail') for (const sx of [-1, 1]) b.box(sx * W * 0.48, deck + 0.8, 0, 0.05, 0.7, L * 0.85, 'accent');
    if (fleetDetailOf(recipe) === 'outboard') {
      b.box(0, deck + 0.25, -L / 2 - 0.12, 0.34, 0.5, 0.3, 'accent');                      // outboard cowl
      b.box(0, deck * 0.3, -L / 2 - 0.1, 0.1, deck * 0.9, 0.1, 'trim');                     // shaft
      b.box(0, deck + 0.02, L * 0.25, W * 0.8, 0.05, 0.25, 'trim');                         // bow thwart
    }
    const top = deck + (recipe.cab_len > 0 ? recipe.cab_h * H : 0.9);
    if (!paddle) { b.lamp(0, top + 0.12, -L * 0.08, 0.14, 0.14, 0.14, 1); b.lamp(0, deck + 0.1, -L / 2 + 0.05, 0.14, 0.12, 0.08, 2); }
    if (recipe.extra === 'fan') { b.wheel(0, deck + H * 0.45, -L / 2 + 0.6, H * 0.35, 0.3, 'trim'); b.box(0, deck + 1.0, -L * 0.1, 0.5, 1.0, 0.5, 'accent'); }
    if (recipe.extra === 'monitor') b.rod(0, top + 0.5, 0, 0.18, 1.0, 'accent', 0.3);
    if (recipe.extra === 'mast') b.rod(0, top + H * 0.15, -L * 0.1, 0.12, H * 0.3, 'accent', 0);
    if (recipe.extra === 'lightbar') b.box(0, top + 0.08, -L * 0.08, W * 0.4, 0.14, 0.3, 'accent');
    if (recipe.extra === 'knees') for (const sx of [-1, 1]) b.box(sx * W * 0.3, deck + 1.2, L / 2 - 0.3, 0.4, 2.4, 0.4, 'accent');
    if (recipe.extra === 'crane') b.rod(W * 0.2, deck + L * 0.14, L * 0.2, 0.25, L * 0.4, 'accent', 0.7);
  } else {
    throw new Error('fleetkit: unknown archetype ' + a);
  }
  const cabN = fleetCabBuild(b, recipe, L, W, H);
  const g = b.done();
  g.userData.fleetCab = cabN; g.userData.fleetDetail = fleetDetailOf(recipe);
  return g;
}

/* One material for every family: vertex colour picks the slot, per-instance
   attributes carry that instance's three palette colours; lamp faces
   (fleetLamp 1 head/mast, 2 tail) glow by the fleetLampOn uniform. */
function fleetMaterial(THREE) {
  const m = new THREE.MeshStandardMaterial({ color: 0xffffff, vertexColors: true, roughness: 0.62, metalness: 0.08, flatShading: true });
  m.userData.fleetLampOn = { value: 1 };
  m.onBeforeCompile = (sh) => {
    sh.uniforms.fleetLampOn = m.userData.fleetLampOn;
    sh.vertexShader = 'attribute vec3 fleetBody;\nattribute vec3 fleetTrim;\nattribute vec3 fleetAccent;\nattribute float fleetLamp;\nattribute float fleetBrake;\nvarying float vFleetLamp;\nvarying float vFleetBrake;\n' +
      sh.vertexShader.replace('#include <color_vertex>',
        '#include <color_vertex>\n  vColor.rgb = color.r * fleetBody + color.g * fleetTrim + color.b * fleetAccent;\n  vFleetLamp = fleetLamp;\n  vFleetBrake = fleetBrake;');
    sh.fragmentShader = 'varying float vFleetLamp;\nvarying float vFleetBrake;\nuniform float fleetLampOn;\n' +
      sh.fragmentShader.replace('#include <emissivemap_fragment>',
        '#include <emissivemap_fragment>\n#define FLEET_BRAKE_GAIN ' + FLEET_BRAKE_GAIN.toFixed(2) + '\n  if (vFleetLamp > 0.5) totalEmissiveRadiance += (vFleetLamp < 1.5 ? vec3(1.0, 0.94, 0.78) : vec3(1.0, 0.08, 0.04)) * (0.25 + 1.75 * fleetLampOn + (vFleetLamp > 1.5 ? FLEET_BRAKE_GAIN * vFleetBrake : 0.0));');
  };
  m.customProgramCacheKey = () => 'fleet-palette-v3';
  return m;
}

function fleetHex(reg, token) {
  const c = fleetNeed(reg, 'colours', 'registry');
  if (!(token in c)) throw new Error('fleetkit: colour token ' + token + ' is not in the registry');
  return c[token];
}

/* ONE InstancedMesh per family plus ONE wheel InstancedMesh for all of them.
   capacity: {familyId: n} - how many of that family may stand at once (every
   family in the registry must be named). A mesh with nothing in it is hidden:
   it costs no draw call. Returns { group, families, wheels, material, spawn(id,
   pose) -> handle, drawCalls() }. pose = {x, y, z, yaw, pitch?, roll?, steer?,
   spin?, scale?}: a physics state works directly (h.set(st)). */
function fleetCreate(THREE, reg, capacity) {
  const group = new THREE.Group(); group.name = 'fleet';
  const byId = new Map(reg.fleet.map((e) => [e.id, e]));
  const families = new Map();
  const mat = fleetMaterial(THREE);
  const zero = new THREE.Matrix4().makeScale(0, 0, 0);
  let wheelCap = 0;
  for (const f of reg.families) {
    const cap = fleetNeed(capacity, f.id, 'capacity');
    const members = reg.fleet.filter((e) => e.family === f.id);
    const ref = { length: 0, width: 0, height: 0 };
    for (const e of members) for (const k of ['length', 'width', 'height']) ref[k] += e.dims_m[k] / members.length;
    const geo = fleetFamilyGeometry(THREE, f.recipe, ref);
    const attrs = {};
    for (const s of FLEET_SLOTS) {
      const key = 'fleet' + s[0].toUpperCase() + s.slice(1);
      attrs[s] = new THREE.InstancedBufferAttribute(new Float32Array(cap * 3), 3);
      geo.setAttribute(key, attrs[s]);
    }
    attrs.brake = new THREE.InstancedBufferAttribute(new Float32Array(cap), 1);
    geo.setAttribute('fleetBrake', attrs.brake);
    const mesh = new THREE.InstancedMesh(geo, mat, cap);
    mesh.name = 'fleet:' + f.id; mesh.frustumCulled = false;
    for (let i = 0; i < cap; i++) mesh.setMatrixAt(i, zero);
    mesh.visible = false;   // an empty family costs no draw call
    group.add(mesh);
    wheelCap += cap * fleetWheelLayout(f.recipe, ref.length, ref.width, ref.height).length;
    families.set(f.id, { family: f, mesh, ref, attrs, free: Array.from({ length: cap }, (_, i) => cap - 1 - i), used: 0 });
  }
  const wheelGeo = new THREE.CylinderGeometry(1, 1, 1, 12).rotateZ(Math.PI / 2);
  const wheelMat = new THREE.MeshStandardMaterial({ color: new THREE.Color(fleetHex(reg, 'trim.dark')).convertSRGBToLinear(), roughness: 0.85, flatShading: true });
  const wheels = new THREE.InstancedMesh(wheelGeo, wheelMat, Math.max(1, wheelCap));
  wheels.name = 'fleet:wheels'; wheels.frustumCulled = false; wheels.visible = false;
  for (let i = 0; i < Math.max(1, wheelCap); i++) wheels.setMatrixAt(i, zero);
  group.add(wheels);
  const wheelFree = Array.from({ length: wheelCap }, (_, i) => wheelCap - 1 - i);
  let wheelsUsed = 0;
  const tmpC = new THREE.Color(), q = new THREE.Quaternion(), e3 = new THREE.Euler(), m4 = new THREE.Matrix4();
  const v3 = new THREE.Vector3(), s3 = new THREE.Vector3(), mv = new THREE.Matrix4(), mw = new THREE.Matrix4(), ml = new THREE.Matrix4();
  const qw = new THREE.Quaternion(), ew = new THREE.Euler();
  function spawn(id, pose) {
    const e = byId.get(id);
    if (!e) throw new Error('fleetkit: no fleet entry ' + id);
    const F = families.get(e.family);
    if (!F.free.length) throw new Error('fleetkit: family ' + e.family + ' is at capacity');
    const slot = F.free.pop(); F.used++; F.mesh.visible = true;
    for (const s of FLEET_SLOTS) {
      tmpC.set(fleetHex(reg, e.palette[s])).convertSRGBToLinear();
      F.attrs[s].setXYZ(slot, tmpC.r, tmpC.g, tmpC.b); F.attrs[s].needsUpdate = true;
    }
    F.attrs.brake.setX(slot, 0); F.attrs.brake.needsUpdate = true;
    const layout = fleetWheelLayout(e.recipe, e.dims_m.length, e.dims_m.width, e.dims_m.height);
    if (wheelFree.length < layout.length) throw new Error('fleetkit: wheel pool is at capacity');
    const wslots = layout.map(() => wheelFree.pop());
    wheelsUsed += wslots.length; if (wslots.length) wheels.visible = true;
    const scale = [e.dims_m.width / F.ref.width, e.dims_m.height / F.ref.height, e.dims_m.length / F.ref.length];
    const h = {
      id, entry: e, family: e.family, slot, wheelSlots: wslots, alive: true,
      set(p) {
        if (!h.alive) throw new Error('fleetkit: set on a despawned ' + id);
        const k = 'scale' in p ? p.scale : 1;   // display-only multiplier (a showroom lineup); physics never sets it
        e3.set('pitch' in p ? p.pitch : 0, p.yaw, 'roll' in p ? p.roll : 0, 'YXZ'); q.setFromEuler(e3);
        m4.compose(v3.set(p.x, p.y, p.z), q, s3.set(scale[0] * k, scale[1] * k, scale[2] * k));
        F.mesh.setMatrixAt(slot, m4); F.mesh.instanceMatrix.needsUpdate = true;
        if ('brake' in p) h.brake(p.brake);
        if (!wslots.length) return;
        mv.compose(v3.set(p.x, p.y, p.z), q, s3.set(k, k, k));
        const steer = ('steer' in p ? p.steer : 0) * FLEET_STEER_VIS, spin = 'spin' in p ? p.spin : 0;
        layout.forEach((w, i) => {
          ew.set(spin, w.front ? steer : 0, 0, 'YXZ'); qw.setFromEuler(ew);
          ml.compose(v3.set(w.x, w.y, w.z), qw, s3.set(w.w, w.r, w.r));
          wheels.setMatrixAt(wslots[i], mw.multiplyMatrices(mv, ml));
        });
        wheels.instanceMatrix.needsUpdate = true;
      },
      brake(level) {   // this instance's brake-lamp intensity 0..1 (drawn only)
        const b = Math.max(0, Math.min(1, level));
        if (F.attrs.brake.getX(slot) !== b) { F.attrs.brake.setX(slot, b); F.attrs.brake.needsUpdate = true; }
      },
      brakeLevel: () => F.attrs.brake.getX(slot),
      despawn() {
        if (!h.alive) return;
        h.alive = false; F.attrs.brake.setX(slot, 0); F.attrs.brake.needsUpdate = true; F.mesh.setMatrixAt(slot, zero); F.mesh.instanceMatrix.needsUpdate = true; F.free.push(slot); F.used--; F.mesh.visible = F.used > 0;
        for (const ws of wslots) { wheels.setMatrixAt(ws, zero); wheelFree.push(ws); }
        wheelsUsed -= wslots.length; wheels.visible = wheelsUsed > 0; wheels.instanceMatrix.needsUpdate = true;
      },
    };
    h.set(pose);
    return h;
  }
  const drawCalls = () => [...families.values()].filter((x) => x.mesh.visible).length + (wheels.visible ? 1 : 0);
  return { group, families, wheels, material: mat, spawn, drawCalls };
}
/* head/tail lamps: 0 = parked glow only, 1 = full */
function fleetLights(fl, level) { fl.material.userData.fleetLampOn.value = Math.max(0, Math.min(1, level)); }

/* --------------------------------------------------------- the ground --- */
/* A ground adapter is { height(x, z) -> m, waterLevel(x, z) -> m | null }.
   Wet = water surface above the ground by more than FLEET_MIN_WET_M. */
function fleetDepth(ground, x, z) {
  const wl = ground.waterLevel(x, z);
  return wl === null ? 0 : wl - ground.height(x, z);
}
function fleetGroundFromWilds(terrain, waterLevelM) {
  if (typeof terrain.height !== 'function' || typeof waterLevelM !== 'number')
    throw new Error('fleetkit: fleetGroundFromWilds(terrain from wildsTerrain(world), world.biome.water_level_m)');
  return { height: (x, z) => terrain.height(x, z), waterLevel: () => waterLevelM };
}
/* flat AUTHORED ground at groundY with water at waterY wherever isWater(x, z) */
function fleetFlatGround(groundY, waterY, isWater) {
  return { height: (x, z) => (isWater(x, z) ? groundY - 3 : groundY), waterLevel: (x, z) => (isWater(x, z) ? waterY : null) };
}

function fleetSpec(e) {
  const d = fleetNeed(e, 'dims_m', e.id);
  return {
    id: e.id, medium: fleetNeed(e, 'medium', e.id), L: d.length, W: d.width, H: d.height,
    top: fleetNeed(e, 'top_speed_ms', e.id), accel: fleetNeed(e, 'accel_ms2', e.id),
    turnR: fleetNeed(e, 'turn_radius_m', e.id), mass: fleetNeed(e, 'mass_kg', e.id),
    draft: e.medium === 'water' ? Math.max(0.1, d.height * (e.recipe.cab_len > 0 ? 0.1 : 0.18)) : 0,
    recipe: fleetNeed(e, 'recipe', e.id), wheelR: e.medium === 'land' ? e.recipe.wheel_r * d.height : 0,
  };
}
function fleetMediumOk(spec, ground, x, z) {
  const depth = fleetDepth(ground, x, z);
  return spec.medium === 'land' ? depth <= FLEET_MIN_WET_M : depth >= spec.draft + FLEET_KEEL_CLEAR_M;
}
/* the two ends (bow/stern or front/back) of a vehicle at (x, z, yaw) */
function fleetEnds(spec, x, z, yaw) {
  const s = Math.sin(yaw), c = Math.cos(yaw), h = spec.L / 2;
  return [[x + s * h, z + c * h], [x - s * h, z - c * h]];
}
/* with a yaw (5th argument) both ends are checked too, not only the centre */
function fleetCanSpawn(spec, ground, x, z, yaw) {
  const pts = typeof yaw === 'number' ? [[x, z], ...fleetEnds(spec, x, z, yaw)] : [[x, z]];
  if (pts.every(([px, pz]) => fleetMediumOk(spec, ground, px, pz))) return { ok: true, reason: '' };
  return spec.medium === 'land' ? { ok: false, reason: 'water: a land vehicle stays on ground' } : { ok: false, reason: 'land: a boat needs water under its keel' };
}
function fleetState(spec, ground, x, z, yaw) {
  const c = fleetCanSpawn(spec, ground, x, z);
  if (!c.ok) throw new Error('fleetkit: cannot place ' + spec.id + ' here - ' + c.reason);
  const st = { x, z, yaw, y: 0, v: 0, steer: 0, brake: 0, pitch: 0, roll: 0, t: 0, refused: 0, wake: 0, spin: 0, phase: (x * 0.37 + z * 0.11) % 6.283 };
  st.y = spec.medium === 'land' ? ground.height(x, z) : ground.waterLevel(x, z) - spec.draft;
  return st;
}
/* input: { throttle -1..1, steer -1..1 (+ = left), brake 0|1 } */
function fleetSpeed(st, spec, input, dt, drag) {
  const thr = Math.max(-1, Math.min(1, input.throttle));
  if (input.brake) st.v -= Math.sign(st.v) * Math.min(Math.abs(st.v), spec.accel * 2.5 * dt);
  else if (thr > 0) st.v += (st.v < 0 ? spec.accel * 2.5 : spec.accel) * thr * dt;
  else if (thr < 0) st.v += (st.v > 0 ? spec.accel * 2.5 : spec.accel * 0.6) * thr * dt;
  else st.v -= st.v * drag * dt;
  st.v = Math.max(-spec.top * 0.3, Math.min(spec.top, st.v));
  // brake lamps: full on the brake, most of the way when throttle opposes motion (drawn only)
  st.brake = input.brake ? 1 : (thr !== 0 && Math.sign(thr) !== Math.sign(st.v) && Math.abs(st.v) > 0.3 ? 0.7 : 0);
  st.steer += (Math.max(-1, Math.min(1, input.steer)) - st.steer) * Math.min(1, 8 * dt);
}
function fleetMove(st, spec, yawRate, dt, ok) {
  const yaw = st.yaw + yawRate * dt;
  const sx = Math.sin(yaw), sz = Math.cos(yaw);
  const nx = st.x + sx * st.v * dt, nz = st.z + sz * st.v * dt;
  // the centre, and BOTH ends whatever the speed (a boat turning at rest swings its bow too):
  // an end may not newly cross onto the wrong medium (one that starts there may move off it)
  const was = fleetEnds(spec, st.x, st.z, st.yaw), now = fleetEnds(spec, nx, nz, yaw);
  if (!ok(nx, nz) || now.some((q, i) => !ok(q[0], q[1]) && ok(was[i][0], was[i][1]))) {
    st.refused++; st.v = -st.v * 0.15; return false;
  }
  st.x = nx; st.z = nz; st.yaw = yaw; return true;
}
function fleetLandStep(st, spec, input, ground, dt) {
  if (spec.medium !== 'land') throw new Error('fleetkit: fleetLandStep on watercraft ' + spec.id);
  st.t += dt;
  fleetSpeed(st, spec, input, dt, 0.5);
  const R = spec.turnR * (1 + 1.5 * Math.abs(st.v) / spec.top);
  const moved = fleetMove(st, spec, st.v / R * st.steer, dt, (x, z) => fleetDepth(ground, x, z) <= FLEET_MIN_WET_M);
  const fx = Math.sin(st.yaw) * spec.L / 2, fz = Math.cos(st.yaw) * spec.L / 2;
  st.y = ground.height(st.x, st.z);
  st.pitch = -Math.atan2(ground.height(st.x + fx, st.z + fz) - ground.height(st.x - fx, st.z - fz), spec.L);
  st.roll = -st.steer * Math.min(0.08, Math.abs(st.v) / spec.top * 0.08);
  if (moved) st.spin = (st.spin + st.v * dt / spec.wheelR) % (Math.PI * 2);
  return moved;
}
function fleetBoatStep(st, spec, input, ground, dt) {
  if (spec.medium !== 'water') throw new Error('fleetkit: fleetBoatStep on land vehicle ' + spec.id);
  st.t += dt;
  fleetSpeed(st, spec, input, dt, 0.35);
  const rate = st.v / spec.turnR * st.steer + 0.12 * st.steer * (1 - Math.min(1, Math.abs(st.v) / 2));
  const moved = fleetMove(st, spec, rate, dt, (x, z) => fleetDepth(ground, x, z) >= spec.draft + FLEET_KEEL_CLEAR_M);
  const amp = Math.min(0.2, Math.max(0.02, 0.3 / Math.sqrt(spec.L))) * (1 + 0.5 * Math.abs(st.v) / spec.top);
  const w = 1.6 / Math.sqrt(Math.max(1, spec.L) / 4);
  st.y = ground.waterLevel(st.x, st.z) - spec.draft + amp * Math.sin(st.t * w + st.phase);
  st.pitch = amp * 0.25 * Math.cos(st.t * w * 0.8 + st.phase) - 0.04 * Math.abs(st.v) / spec.top;
  st.roll = amp * 0.3 * Math.sin(st.t * w * 0.6 + st.phase * 2) - st.steer * 0.05 * Math.abs(st.v) / spec.top;
  st.wake = Math.abs(st.v) / spec.top;
  return moved;
}
function fleetStep(st, spec, input, ground, dt) {
  return spec.medium === 'land' ? fleetLandStep(st, spec, input, ground, dt) : fleetBoatStep(st, spec, input, ground, dt);
}

/* ------------------------------------------------ enter / exit / camera --- */
/* nearest vehicle whose hull is within reach metres of p = {x, z};
   vehicles = [{ st, spec, ... }] */
function fleetNearest(p, vehicles, reach) {
  let best = null, bd = Infinity;
  for (const v of vehicles) {
    const c = Math.cos(v.st.yaw), s = Math.sin(v.st.yaw), dx = p.x - v.st.x, dz = p.z - v.st.z;
    const lx = Math.abs(dx * c - dz * s) - v.spec.W / 2, lz = Math.abs(dx * s + dz * c) - v.spec.L / 2;
    const d = Math.hypot(Math.max(0, lx), Math.max(0, lz));
    if (d <= reach && d < bd) { bd = d; best = v; }
  }
  return best;
}
/* a dry spot beside the vehicle to step out onto, or null (stay aboard) */
function fleetExitPoint(st, spec, ground) {
  const c = Math.cos(st.yaw), s = Math.sin(st.yaw);
  const cands = [];
  for (const k of [1, 1.8, 3, 5, 8, 12]) {
    const off = spec.W / 2 + k * 0.8;
    cands.push([c * off, -s * off], [-c * off, s * off], [-s * (spec.L / 2 + k), -c * (spec.L / 2 + k)], [s * (spec.L / 2 + k), c * (spec.L / 2 + k)]);
  }
  for (const [dx, dz] of cands) {
    const x = st.x + dx, z = st.z + dz;
    if (fleetDepth(ground, x, z) <= FLEET_MIN_WET_M) return { x, y: ground.height(x, z), z };
  }
  return null;
}
/* chase camera: behind and above, eased; camera needs position.set/lookAt */
function fleetChaseCamera(camera, st, spec, dt, eye) {
  const back = spec.L * 1.2 + 4, up = spec.H * 1.3 + 1.6;
  const tx = st.x - Math.sin(st.yaw) * back, tz = st.z - Math.cos(st.yaw) * back, ty = st.y + up;
  const k = eye && eye.snap ? 1 : Math.min(1, 4 * dt);
  const p = camera.position;
  p.set(p.x + (tx - p.x) * k, p.y + (ty - p.y) * k, p.z + (tz - p.z) * k);
  camera.lookAt(st.x, st.y + spec.H * 0.6, st.z);
}

/* a boat wake: rings dropped behind moving boats, ONE draw call. Everything
   scales with speed (st.wake = |v| / top): how often a ring drops, how wide it
   starts, how fast it spreads and how bright it is. */
function fleetWake(THREE, cap) {
  const geo = new THREE.RingGeometry(0.7, 1, 20).rotateX(-Math.PI / 2);
  const mat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.55, depthWrite: false, blending: THREE.AdditiveBlending });
  const mesh = new THREE.InstancedMesh(geo, mat, cap); mesh.name = 'fleet:wake'; mesh.frustumCulled = false;
  const rings = new Array(cap).fill(null), m4 = new THREE.Matrix4(), zero = new THREE.Matrix4().makeScale(0, 0, 0), c = new THREE.Color();
  for (let i = 0; i < cap; i++) { mesh.setMatrixAt(i, zero); mesh.setColorAt(i, c.setRGB(0, 0, 0)); }
  let next = 0, acc = 0;
  return {
    mesh, rings,
    emit(st, spec, dt) {
      acc += dt * st.wake * 12;
      while (acc >= 1) {
        acc -= 1;
        rings[next] = { x: st.x - Math.sin(st.yaw) * spec.L * 0.5, y: st.y + spec.draft + 0.03, z: st.z - Math.cos(st.yaw) * spec.L * 0.5,
          age: 0, w: spec.W * (0.35 + 0.65 * st.wake), grow: 0.6 + 3.4 * st.wake, bright: 0.2 + 0.8 * st.wake };
        next = (next + 1) % cap;
      }
    },
    size(i) { const r = rings[i]; return r ? r.w + r.age * r.grow : 0; },
    update(dt) {
      for (let i = 0; i < cap; i++) {
        const r = rings[i];
        if (!r) continue;
        r.age += dt;
        if (r.age > 3) { rings[i] = null; mesh.setMatrixAt(i, zero); continue; }
        const sc = r.w + r.age * r.grow;
        m4.makeScale(sc, 1, sc).setPosition(r.x, r.y, r.z); mesh.setMatrixAt(i, m4);
        const k = r.bright * (1 - r.age / 3); mesh.setColorAt(i, c.setRGB(k, k, k));
      }
      mesh.instanceMatrix.needsUpdate = true; if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    },
  };
}

/* --------------------------------------------------- the driver's seat --- */
/* where the driver's eye sits, in the vehicle's own frame (+z forward, y up from
   the ground/keel), from the family recipe and the entry's dims */
function fleetDriverEye(spec) {
  const r = spec.recipe, L = spec.L, W = spec.W, H = spec.H, a = r.archetype;
  if (a === 'car') return { x: -0.2 * W, y: H * 0.82, z: -0.04 * L + r.cab_len * L * 0.12 };
  if (a === 'bus') return { x: -0.25 * W, y: H * 0.62, z: L / 2 - Math.min(1.2, L * 0.12) };
  if (a === 'truck') return { x: -0.2 * W, y: r.cab_h * H * 0.8, z: L / 2 - r.cab_len * L * 0.55 };
  if (a === 'machine') return { x: 0, y: Math.min(H * 0.9, r.cab_h * H * 0.85), z: r.body === 'none' ? -0.2 * L : -0.05 * L };
  if (a === 'cycle') return { x: 0, y: H * 1.3, z: -0.12 * L };
  if (a === 'paddle') return { x: 0, y: H + 0.6, z: -0.05 * L };
  if (a === 'hull') {
    const deck = r.cab_len > 0 ? H * 0.32 : H * 0.55;
    return r.cab_len > 0 ? { x: 0, y: deck + r.cab_h * H * 0.72, z: -0.08 * L + r.cab_len * L * 0.3 } : { x: 0, y: deck + 1.2, z: -0.1 * L };
  }
  throw new Error('fleetkit: no driver eye for archetype ' + a);
}
/* interior / driver camera: at the driver's eye, looking along the heading */
function fleetDriverCamera(camera, st, spec) {
  const e = fleetDriverEye(spec), c = Math.cos(st.yaw), s = Math.sin(st.yaw);
  // local (x right-of-centre as +x at yaw 0, z forward) rotated by yaw about y
  const wx = st.x + e.x * c + e.z * s, wz = st.z - e.x * s + e.z * c, wy = st.y + e.y;
  camera.position.set(wx, wy, wz);
  camera.lookAt(wx + s * 30, wy - 30 * Math.tan(st.pitch) - 1.2, wz + c * 30);
  return { x: wx, y: wy, z: wz };
}

/* ----------------------------------------------------- ambient traffic --- */
/* Budgets (fail closed: a traffic setup that exceeds one throws by name). */
const FLEET_TRAFFIC_BUDGET = { maxAgents: 160, maxFamilies: 12, updateMs: 1.5 };
/* A route is {id, medium: 'land'|'water', points: [[x, z], ...], loop, provenance}.
   Routes are the CALLER's: AUTHORED street polylines or water lanes. Two helpers
   make them from a rule (AUTHORED, never the real street grid): */
/* grid lanes: the centre lines of every `every`-th cell row/column of a cell grid
   (web/build_parishes.py leaves those rows open as streets), clipped to where
   ok(x, z) holds, sampled every `step` m; pieces shorter than minLen dropped */
function fleetGridLanes(o) {
  for (const k of ['cell', 'every', 'x0', 'x1', 'z0', 'z1', 'step', 'minLen', 'ok']) fleetNeed(o, k, 'fleetGridLanes');
  const out = [], band = o.cell * o.every;
  const run = (fixed, horiz) => {
    let cur = [];
    const lo = horiz ? o.x0 : o.z0, hi = horiz ? o.x1 : o.z1;
    const flush = () => { if (cur.length >= 2 && Math.hypot(cur.at(-1)[0] - cur[0][0], cur.at(-1)[1] - cur[0][1]) >= o.minLen) out.push(cur); cur = []; };
    for (let t = lo; t <= hi; t += o.step) {
      const x = horiz ? t : fixed, z = horiz ? fixed : t;
      if (o.ok(x, z)) cur.push([x, z]); else flush();
    }
    flush();
  };
  for (let x = Math.ceil(o.x0 / band) * band; x <= o.x1; x += band) run(x + o.cell / 2, false);
  for (let z = Math.ceil(o.z0 / band) * band; z <= o.z1; z += band) run(z + o.cell / 2, true);
  return out.map((points, i) => ({ id: 'grid-' + i, medium: 'land', points, loop: false, provenance: 'AUTHORED' }));
}
/* a closed water lane: a ring of radius r about (cx, cz) */
function fleetRingLane(id, cx, cz, r, n) {
  const points = [];
  for (let i = 0; i < n; i++) { const a = (i / n) * Math.PI * 2; points.push([cx + Math.cos(a) * r, cz + Math.sin(a) * r]); }
  return { id, medium: 'water', points, loop: true, provenance: 'AUTHORED' };
}
/* AUTHORED street polylines (PARISH_CONTRACT v1.3) as land traffic routes,
   MEDIUM-CHECKED: each polyline is resampled every `step` m and a sample counts
   only where the ground is dry at the centre line and at +-`halfWidth` m either
   side (lane offset + half a vehicle); dry runs shorter than minLen are dropped,
   so a street that crosses water is split, never driven through it.
   streets: [{id, points: [[x, z], ...] in the world's metres, provenance: 'AUTHORED'}]
   o (all required): {step, minLen, halfWidth, map: null | ([a, b]) -> [x, z]}
   Anything but provenance 'AUTHORED' throws: these are never the real street grid. */
function fleetStreetRoutes(streets, ground, o) {
  for (const k of ['step', 'minLen', 'halfWidth', 'map']) fleetNeed(o, k, 'fleetStreetRoutes');
  if (!Array.isArray(streets)) throw new Error('fleetkit: fleetStreetRoutes needs an array of street polylines');
  const dry = (x, z) => fleetDepth(ground, x, z) <= FLEET_MIN_WET_M;
  const out = [];
  for (const st of streets) {
    const id = fleetNeed(st, 'id', 'street'), pts = fleetNeed(st, 'points', 'street ' + id);
    if (fleetNeed(st, 'provenance', 'street ' + id) !== 'AUTHORED') throw new Error('fleetkit: street ' + id + ' is not AUTHORED (' + st.provenance + ')');
    if (!Array.isArray(pts) || pts.length < 2) throw new Error('fleetkit: street ' + id + ' has fewer than 2 points');
    const P = pts.map((q) => { const m = o.map ? o.map(q) : q; if (!Number.isFinite(m[0]) || !Number.isFinite(m[1])) throw new Error('fleetkit: street ' + id + ' has a non-numeric point'); return m; });
    let cur = [], piece = 0;
    const flush = () => {
      let len = 0; for (let i = 1; i < cur.length; i++) len += Math.hypot(cur[i][0] - cur[i - 1][0], cur[i][1] - cur[i - 1][1]);
      if (cur.length >= 2 && len >= o.minLen) out.push({ id: 'street:' + id + ':' + piece++, source: id, medium: 'land', points: cur, loop: false, provenance: 'AUTHORED' });
      cur = [];
    };
    for (let i = 1; i < P.length; i++) {
      const [ax, az] = P[i - 1], [bx, bz] = P[i], seg = Math.hypot(bx - ax, bz - az);
      if (seg === 0) continue;
      const nx = -(bz - az) / seg, nz = (bx - ax) / seg, n = Math.max(1, Math.ceil(seg / o.step));
      for (let j = i === 1 ? 0 : 1; j <= n; j++) {
        const t = j / n, x = ax + (bx - ax) * t, z = az + (bz - az) * t;
        if (dry(x, z) && dry(x + nx * o.halfWidth, z + nz * o.halfWidth) && dry(x - nx * o.halfWidth, z - nz * o.halfWidth)) cur.push([x, z]);
        else flush();
      }
    }
    flush();
  }
  return out;
}
/* PARISH_CONTRACT v1.3 streets file (parishes/maps/streets/<fips>.json) -> the street list
   fleetStreetRoutes takes: [{id: '<fips>:<class>:<i>', cls, points: [[east_m, north_m], ...], provenance}].
   Points stay in the PARISH LOCAL frame: pass fleetStreetRoutes a map() into your scene
   (e.g. ([e, n]) => [e + origin_e, -(n + origin_n)] for x = east, z = -north). Fail closed. */
function fleetParishStreets(file, classes) {
  if (fleetNeed(file, 'provenance', 'streets file') !== 'AUTHORED') throw new Error('fleetkit: streets file ' + file.fips + ' is not AUTHORED');
  const C = fleetNeed(file, 'classes', 'streets file'), fips = fleetNeed(file, 'fips', 'streets file'), out = [];
  for (const cls of classes) fleetNeed(C, cls, 'streets file ' + fips + ' classes').forEach((points, i) => out.push({ id: fips + ':' + cls + ':' + i, cls, points, provenance: 'AUTHORED' }));
  return out;
}
function fleetRouteGeom(route) {
  const P = route.points.slice(); if (route.loop) P.push(P[0]);
  const cum = [0];
  for (let i = 1; i < P.length; i++) cum.push(cum[i - 1] + Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]));
  return { P, cum, len: cum.at(-1) };
}
function fleetRouteAt(g, s) {
  let lo = 0, hi = g.cum.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (g.cum[m] <= s) lo = m; else hi = m; }
  const seg = g.cum[hi] - g.cum[lo] || 1, t = (s - g.cum[lo]) / seg, A = g.P[lo], B = g.P[hi];
  return { x: A[0] + (B[0] - A[0]) * t, z: A[1] + (B[1] - A[1]) * t, yaw: Math.atan2(B[0] - A[0], B[1] - A[1]) };
}
/* Plan and run ambient traffic in its OWN fleetCreate (one InstancedMesh per
   family used + one for wheels). opts (all required): {seed, landPerKm,
   waterPerKm, maxAgents, maxFamilies, radius, speedFactor, laneOffset}.
   Every route is checked on its medium along its length, lane offsets included,
   for the agent it carries: a land agent never touches water, a boat never land.
   Returns {group, agents, routes, update(dt, eye), stats(), fleet}. */
function fleetTraffic(THREE, reg, routes, ground, opts) {
  for (const k of ['seed', 'landPerKm', 'waterPerKm', 'maxAgents', 'maxFamilies', 'radius', 'speedFactor', 'laneOffset']) fleetNeed(opts, k, 'traffic opts');
  if (opts.maxAgents > FLEET_TRAFFIC_BUDGET.maxAgents) throw new Error('fleetkit: traffic maxAgents ' + opts.maxAgents + ' is over the budget ' + FLEET_TRAFFIC_BUDGET.maxAgents);
  if (opts.maxFamilies > FLEET_TRAFFIC_BUDGET.maxFamilies) throw new Error('fleetkit: traffic maxFamilies ' + opts.maxFamilies + ' is over the budget ' + FLEET_TRAFFIC_BUDGET.maxFamilies);
  let seed = opts.seed >>> 0;
  const rnd = () => { seed = (seed + 0x6D2B79F5) >>> 0; let t = seed; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  // traffic types: land entries that move at street pace, all watercraft; a seeded family subset within budget
  const pool = { land: reg.fleet.filter((e) => e.medium === 'land' && e.top_speed_kmh >= 25), water: reg.fleet.filter((e) => e.medium === 'water') };
  const famIds = [...new Set([...pool.land, ...pool.water].map((e) => e.family))].sort();
  for (let i = famIds.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [famIds[i], famIds[j]] = [famIds[j], famIds[i]]; }
  const allowed = new Set(famIds.slice(0, opts.maxFamilies));
  for (const m of ['land', 'water']) pool[m] = pool[m].filter((e) => allowed.has(e.family));
  const okAt = (medium, spec, x, z) => {
    const d = fleetDepth(ground, x, z);
    return medium === 'land' ? d <= FLEET_MIN_WET_M : d >= spec.draft + FLEET_KEEL_CLEAR_M;
  };
  const geoms = routes.map((r) => {
    for (const k of ['id', 'medium', 'points', 'loop', 'provenance']) fleetNeed(r, k, 'route');
    if (r.points.length < 2) throw new Error('fleetkit: route ' + r.id + ' has fewer than 2 points');
    return fleetRouteGeom(r);
  });
  const routeFits = (ri, spec) => {
    const r = routes[ri], g = geoms[ri], off = opts.laneOffset + spec.W / 2 + spec.L / 2;
    for (let s = 0; s <= g.len; s += 4) {
      const p = fleetRouteAt(g, Math.min(s, g.len)), c = Math.cos(p.yaw), sn = Math.sin(p.yaw);
      for (const o of [-off, 0, off]) if (!okAt(r.medium, spec, p.x - c * o, p.z + sn * o)) return false;
    }
    return true;
  };
  const agents = [], need = Object.fromEntries(reg.families.map((f) => [f.id, 0]));
  // per-route counts by density, scaled down together (never first-come) to fit maxAgents
  const want = routes.map((r, ri) => Math.floor(geoms[ri].len / 1000 * (r.medium === 'land' ? opts.landPerKm : opts.waterPerKm)));
  const total = want.reduce((t, n) => t + n, 0), k = total > opts.maxAgents ? opts.maxAgents / total : 1;
  routes.forEach((r, ri) => {
    const g = geoms[ri], n = Math.floor(want[ri] * k), cands = pool[r.medium];
    for (let i = 0; i < n && agents.length < opts.maxAgents && cands.length; i++) {
      let e = null, spec = null;
      for (let tries = 0; tries < 6 && !e; tries++) {   // a type that fits this route on its medium, lane offset included
        const c = cands[Math.floor(rnd() * cands.length)], sp = fleetSpec(c);
        if (routeFits(ri, sp)) { e = c; spec = sp; }
      }
      if (!e) continue;
      const dir = r.loop ? 1 : (rnd() < 0.5 ? 1 : -1);
      agents.push({ e, spec, ri, s: rnd() * g.len, dir, cruise: Math.min(spec.top * opts.speedFactor, 14), v: 0, brake: 0, h: null,
        x: 0, y: 0, z: 0, yaw: 0, steer: 0, spin: 0, pitch: 0, roll: 0, t: rnd() * 10, phase: rnd() * 6.28 });
    }
  });
  for (const a of agents) need[a.e.family] = Math.min(need[a.e.family] + 1, 64);
  const fl = fleetCreate(THREE, reg, need);
  let lastMs = 0, sumMs = 0, frames = 0, drawn = 0;
  function place(a, dt) {
    const g = geoms[a.ri], p = fleetRouteAt(g, a.s);
    const yaw = a.dir > 0 ? p.yaw : p.yaw + Math.PI, c = Math.cos(yaw), sn = Math.sin(yaw);
    // keep right of the direction of travel: right = (-cos yaw, sin yaw)
    a.x = p.x - c * opts.laneOffset; a.z = p.z + sn * opts.laneOffset;
    let dy = yaw - a.yaw; dy = Math.atan2(Math.sin(dy), Math.cos(dy));
    a.steer = Math.max(-1, Math.min(1, dy / Math.max(dt, 1e-3) / 1.5)); a.yaw = yaw;
    if (a.spec.medium === 'land') { a.y = ground.height(a.x, a.z); a.spin = (a.spin + a.v * dt / a.spec.wheelR) % (Math.PI * 2); }
    else { a.t += dt; a.y = ground.waterLevel(a.x, a.z) - a.spec.draft + 0.06 * Math.sin(a.t * 1.3 + a.phase); }
  }
  function update(dt, eye) {
    const t0 = (typeof performance !== 'undefined' ? performance : Date).now();
    // following: per route and direction, slow down behind the agent ahead
    const lanes = new Map();
    for (const a of agents) { const k = a.ri + ':' + a.dir; if (!lanes.has(k)) lanes.set(k, []); lanes.get(k).push(a); }
    for (const [k, list] of lanes) {
      const g = geoms[list[0].ri];
      list.sort((p, q) => (p.s - q.s) * p.dir);
      for (let i = 0; i < list.length; i++) {
        const a = list[i], ahead = list[i + 1] || (routes[a.ri].loop && list.length > 1 ? list[0] : null);
        let gap = Infinity;
        if (ahead) { gap = (ahead.s - a.s) * a.dir; if (gap < 0) gap += g.len; gap -= (a.spec.L + ahead.spec.L) / 2; }
        let want = gap < 6 ? 0 : gap < 20 ? a.cruise * (gap - 6) / 14 : a.cruise;
        if (!routes[a.ri].loop) { const toEnd = a.dir > 0 ? g.len - a.s : a.s; if (toEnd < 30) want = Math.min(want, Math.max(1.5, a.cruise * toEnd / 30)); }   // slow for the turn-around
        a.brake = want < a.v - 0.2 ? 1 : 0;
        a.v += Math.max(-a.spec.accel * 3 * dt, Math.min(a.spec.accel * dt, want - a.v));
        a.v = Math.max(0, a.v);
      }
    }
    drawn = 0;
    for (const a of agents) {
      const g = geoms[a.ri];
      a.s += a.dir * a.v * dt;
      if (routes[a.ri].loop) a.s = ((a.s % g.len) + g.len) % g.len;
      else if (a.s > g.len) { a.s = g.len; a.dir = -1; } else if (a.s < 0) { a.s = 0; a.dir = 1; }
      place(a, dt);
      const near = Math.hypot(a.x - eye.x, a.z - eye.z) <= opts.radius;
      if (near && !a.h) a.h = fl.spawn(a.e.id, a);
      else if (!near && a.h) { a.h.despawn(); a.h = null; }
      if (a.h) { a.h.set(a); drawn++; }
    }
    lastMs = (typeof performance !== 'undefined' ? performance : Date).now() - t0; sumMs += lastMs; frames++;
  }
  return {
    group: fl.group, agents, routes, fleet: fl, update,
    stats: () => ({ agents: agents.length, drawn, drawCalls: fl.drawCalls(), families: new Set(agents.map((a) => a.e.family)).size,
      lastMs, avgMs: frames ? sumMs / frames : 0, budget: FLEET_TRAFFIC_BUDGET }),
  };
}
/* ----------------------------------------------- touch (phone) driving --- */
/* The stick's pure mapping (tested in node): drag (dx right, dy down, px) inside
   a stick of radius r -> input. Steer + = left (drag left), stick up = forward,
   down = reverse; the throttle button is full forward, the brake button brakes. */
function fleetStickInput(dx, dy, r, throttleHeld, brakeHeld) {
  const d = Math.hypot(dx, dy), k = d > r && d > 0 ? r / d : 1;
  const sx = r > 0 ? Math.max(-1, Math.min(1, (dx * k) / r)) : 0, sy = r > 0 ? Math.max(-1, Math.min(1, (dy * k) / r)) : 0;
  const dead = (v) => (Math.abs(v) < 0.12 ? 0 : v);
  return { throttle: throttleHeld ? 1 : dead(-sy), steer: dead(-sx), brake: brakeHeld ? 1 : 0 };
}
/* the controls' CSS: colours ONLY from the page's theme tokens (--tc-*) */
const FLEET_TOUCH_CSS = `.fleet-touch{position:absolute;inset:auto 0 0 0;display:none;justify-content:space-between;align-items:flex-end;padding:10px 12px;gap:10px;pointer-events:none;z-index:3}
.fleet-touch[data-on="1"]{display:flex}
.fleet-touch>*{pointer-events:auto}
.fleet-stick{position:relative;width:132px;height:132px;border-radius:50%;background:var(--tc-panel);border:2px solid var(--tc-line);touch-action:none;opacity:.92}
.fleet-stick:focus-visible,.fleet-tbtn:focus-visible{outline:3px solid var(--tc-steel);outline-offset:2px}
.fleet-knob{position:absolute;left:50%;top:50%;width:56px;height:56px;margin:-28px 0 0 -28px;border-radius:50%;background:var(--tc-steel);border:2px solid var(--tc-ink)}
.fleet-tpad{display:flex;flex-direction:column;gap:8px;align-items:stretch}
.fleet-tbtn{min-width:88px;min-height:48px;border-radius:12px;border:2px solid var(--tc-line);background:var(--tc-panel);color:var(--tc-ink);font:600 15px/1.2 system-ui,sans-serif;touch-action:none;padding:6px 10px}
.fleet-tbtn[aria-pressed="true"]{background:var(--tc-steel);color:var(--tc-plate)}
.fleet-tbtn.fleet-brake[aria-pressed="true"]{background:var(--tc-amber);color:var(--tc-plate)}
.fleet-touch [hidden]{display:none}
@media (pointer:coarse){.fleet-touch[data-auto="1"]{display:flex}}`;
/* Build the touch controls into `host` (a positioned element over the canvas).
   labels (all required, translated by the page): {group, stick, throttle, brake, enter, exit}.
   onToggle() is called by the enter/exit button (the page decides enter vs exit).
   Accessible: a labelled group; the stick is focusable and its arrow keys also
   steer/drive; every button is a real <button> >= 48 px with aria-pressed while
   held. Shown on a coarse pointer (phones) or when show(true) is called.
   -> {el, input() -> {throttle, steer, brake}, setAboard(bool), show(bool), state()} */
function fleetTouchControls(doc, host, labels, onToggle) {
  for (const k of ['group', 'stick', 'throttle', 'brake', 'enter', 'exit']) {
    const v = fleetNeed(labels, k, 'touch labels');
    if (typeof v !== 'string' || !v.trim()) throw new Error('fleetkit: touch label ' + k + ' is empty');
  }
  if (typeof onToggle !== 'function') throw new Error('fleetkit: fleetTouchControls needs an onToggle function');
  if (!doc.getElementById('fleet-touch-css')) { const cs = doc.createElement('style'); cs.id = 'fleet-touch-css'; cs.textContent = FLEET_TOUCH_CSS; doc.head.appendChild(cs); }
  const mk = (tag, cls, attrs) => { const e = doc.createElement(tag); e.className = cls; for (const [a, v] of Object.entries(attrs)) e.setAttribute(a, v); return e; };
  const el = mk('div', 'fleet-touch', { role: 'group', 'aria-label': labels.group, 'data-auto': '1', 'data-on': '0' });
  const stick = mk('div', 'fleet-stick', { role: 'application', tabindex: '0', 'aria-label': labels.stick, 'aria-roledescription': 'joystick' });
  const knob = mk('div', 'fleet-knob', { 'aria-hidden': 'true' });
  stick.appendChild(knob);
  const pad = mk('div', 'fleet-tpad', {});
  const bThr = mk('button', 'fleet-tbtn fleet-throttle', { type: 'button', 'aria-pressed': 'false' }); bThr.textContent = labels.throttle;
  const bBrk = mk('button', 'fleet-tbtn fleet-brake', { type: 'button', 'aria-pressed': 'false' }); bBrk.textContent = labels.brake;
  const bTog = mk('button', 'fleet-tbtn fleet-toggle', { type: 'button' }); bTog.textContent = labels.enter;
  pad.append(bTog, bThr, bBrk); el.append(stick, pad); host.appendChild(el);
  const S = { dx: 0, dy: 0, thr: false, brk: false, id: null, keys: {} };
  const R = () => stick.getBoundingClientRect().width / 2 || 66;
  const drawKnob = () => { const k = fleetStickInput(S.dx, S.dy, R(), false, false); knob.style.transform = 'translate(' + (-k.steer * R() * 0.6) + 'px,' + (-k.throttle * R() * 0.6) + 'px)'; };
  const fromEv = (ev) => { const b = stick.getBoundingClientRect(); S.dx = ev.clientX - (b.left + b.width / 2); S.dy = ev.clientY - (b.top + b.height / 2); drawKnob(); };
  stick.addEventListener('pointerdown', (ev) => { S.id = ev.pointerId; if (stick.setPointerCapture) try { stick.setPointerCapture(ev.pointerId); } catch (_) { /* synthetic events */ } fromEv(ev); ev.preventDefault(); });
  stick.addEventListener('pointermove', (ev) => { if (S.id === ev.pointerId) fromEv(ev); });
  const release = (ev) => { if (S.id === ev.pointerId) { S.id = null; S.dx = 0; S.dy = 0; drawKnob(); } };
  stick.addEventListener('pointerup', release); stick.addEventListener('pointercancel', release);
  const KEYS = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
  const fromKeys = () => { let x = 0, y = 0; for (const [k, v] of Object.entries(KEYS)) if (S.keys[k]) { x += v[0]; y += v[1]; } S.dx = x * R(); S.dy = y * R(); drawKnob(); };
  stick.addEventListener('keydown', (ev) => { if (ev.code in KEYS) { S.keys[ev.code] = true; fromKeys(); ev.preventDefault(); ev.stopPropagation(); } });
  stick.addEventListener('keyup', (ev) => { if (ev.code in KEYS) { S.keys[ev.code] = false; fromKeys(); ev.stopPropagation(); } });
  const hold = (btn, key) => {
    const on = (v) => (ev) => { S[key] = v; btn.setAttribute('aria-pressed', String(v)); if (ev && ev.type === 'pointerdown') ev.preventDefault(); };
    btn.addEventListener('pointerdown', on(true)); btn.addEventListener('pointerup', on(false)); btn.addEventListener('pointercancel', on(false)); btn.addEventListener('pointerleave', on(false));
    btn.addEventListener('keydown', (ev) => { if (ev.code === 'Space' || ev.code === 'Enter') { on(true)(); ev.preventDefault(); ev.stopPropagation(); } });
    btn.addEventListener('keyup', (ev) => { if (ev.code === 'Space' || ev.code === 'Enter') { on(false)(); ev.stopPropagation(); } });
  };
  hold(bThr, 'thr'); hold(bBrk, 'brk');
  bTog.addEventListener('click', () => onToggle());
  let aboard = false;
  const api = {
    el,
    input: () => fleetStickInput(S.dx, S.dy, R(), S.thr, S.brk),
    setAboard(v) { aboard = !!v; bTog.textContent = aboard ? labels.exit : labels.enter; bThr.hidden = !aboard; bBrk.hidden = !aboard; stick.hidden = !aboard; if (!aboard) { S.thr = S.brk = false; S.dx = S.dy = 0; drawKnob(); } },
    show(v) { el.dataset.on = v ? '1' : '0'; },
    state: () => ({ aboard, shown: el.dataset.on === '1', dx: S.dx, dy: S.dy, throttle: S.thr, brake: S.brk }),
  };
  api.setAboard(false);
  return api;
}
/* FLEET_KIT:END */
export { FLEET_API, FLEET_SLOTS, FLEET_MIN_WET_M, FLEET_KEEL_CLEAR_M, fleetFamilyGeometry, fleetMaterial, fleetCreate,
  fleetGroundFromWilds, fleetFlatGround, fleetDepth, fleetSpec, fleetCanSpawn, fleetState, fleetLandStep, fleetBoatStep,
  fleetStep, fleetNearest, fleetExitPoint, fleetChaseCamera, fleetWake, fleetWheelLayout, fleetLights, fleetDriverEye,
  fleetDriverCamera, FLEET_TRAFFIC_BUDGET, FLEET_STEER_VIS, fleetGridLanes, fleetRingLane, fleetTraffic,
  FLEET_BRAKE_GAIN, fleetCabParts, FLEET_DETAIL, fleetDetailOf, fleetStreetRoutes, fleetParishStreets, fleetStickInput, FLEET_TOUCH_CSS, fleetTouchControls };
'''

EXPORTS = re.findall(r'export \{([^}]*)\}', FLEET_JS)[0].replace('\n', ' ').split(',')
EXPORTS = [e.strip() for e in EXPORTS if e.strip()]
BEGIN, END = '/* FLEET_KIT:BEGIN', '/* FLEET_KIT:END */'


def fleet_inline():
    """The module body without its export line, for pasting into a page's own module script."""
    return FLEET_JS[:FLEET_JS.index(END) + len(END)]


if __name__ == '__main__':
    if '--out' in sys.argv:
        open(sys.argv[sys.argv.index('--out') + 1], 'w').write(FLEET_JS)
    print(f'FLEET_JS: {len(FLEET_JS)} bytes, {len(EXPORTS)} exports: {", ".join(EXPORTS)}')
