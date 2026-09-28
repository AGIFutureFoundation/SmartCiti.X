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

function fleetNeed(o, k, where) {
  if (o === null || typeof o !== 'object' || !(k in o) || o[k] === undefined)
    throw new Error('fleetkit: ' + where + ' has no ' + k);
  return o[k];
}

/* ----------------------------------------------------------- geometry --- */
function fleetGeoBuilder(THREE) {
  const pos = [], nor = [], col = [];
  const slotRGB = { body: [1, 0, 0], trim: [0, 1, 0], accent: [0, 0, 1] };
  function add(g, slot, m) {
    const s = slotRGB[slot];
    if (!s) throw new Error('fleetkit: unknown palette slot ' + slot);
    const ng = g.index ? g.toNonIndexed() : g;
    if (m) ng.applyMatrix4(m);
    ng.computeVertexNormals();
    const p = ng.attributes.position.array, n = ng.attributes.normal.array;
    for (let i = 0; i < p.length; i++) { pos.push(p[i]); nor.push(n[i]); }
    for (let i = 0; i < p.length / 3; i++) col.push(s[0], s[1], s[2]);
    ng.dispose(); if (ng !== g) g.dispose();
  }
  const M = () => new THREE.Matrix4();
  const api = {
    box(cx, cy, cz, sx, sy, sz, slot, rx = 0) {
      const m = M().makeTranslation(cx, cy, cz);
      if (rx) m.multiply(M().makeRotationX(rx));
      add(new THREE.BoxGeometry(Math.max(sx, 1e-3), Math.max(sy, 1e-3), Math.max(sz, 1e-3)), slot, m);
    },
    wheel(cx, cy, cz, r, w, slot) {   // axis along x
      const m = M().makeTranslation(cx, cy, cz).multiply(M().makeRotationZ(Math.PI / 2));
      add(new THREE.CylinderGeometry(r, r, w, 10), slot, m);
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
      g.computeBoundingBox(); g.computeBoundingSphere();
      return g;
    },
  };
  return api;
}

function fleetWheels(b, recipe, L, W, H) {
  const r = recipe.wheel_r * H, tw = Math.min(0.4, W * 0.16);
  const n = recipe.axles, inset = Math.max(r * 1.25, L * 0.14);
  const zs = [];
  if (n === 2) zs.push(L / 2 - inset, -L / 2 + inset);
  else { zs.push(L / 2 - inset); for (let i = 0; i < n - 1; i++) zs.push(-L / 2 + inset + i * r * 2.3); }
  for (const z of zs) for (const sx of [-1, 1]) b.wheel(sx * (W / 2 - tw / 2), r, z, r, tw, 'trim');
  return r;
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
    for (const z of [L / 2 - r, -L / 2 + r]) b.wheel(0, r, z, r, 0.06, 'trim');
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
    const top = deck + (recipe.cab_len > 0 ? recipe.cab_h * H : 0.9);
    if (recipe.extra === 'fan') { b.wheel(0, deck + H * 0.45, -L / 2 + 0.6, H * 0.35, 0.3, 'trim'); b.box(0, deck + 1.0, -L * 0.1, 0.5, 1.0, 0.5, 'accent'); }
    if (recipe.extra === 'monitor') b.rod(0, top + 0.5, 0, 0.18, 1.0, 'accent', 0.3);
    if (recipe.extra === 'mast') b.rod(0, top + H * 0.15, -L * 0.1, 0.12, H * 0.3, 'accent', 0);
    if (recipe.extra === 'lightbar') b.box(0, top + 0.08, -L * 0.08, W * 0.4, 0.14, 0.3, 'accent');
    if (recipe.extra === 'knees') for (const sx of [-1, 1]) b.box(sx * W * 0.3, deck + 1.2, L / 2 - 0.3, 0.4, 2.4, 0.4, 'accent');
    if (recipe.extra === 'crane') b.rod(W * 0.2, deck + L * 0.14, L * 0.2, 0.25, L * 0.4, 'accent', 0.7);
  } else {
    throw new Error('fleetkit: unknown archetype ' + a);
  }
  return b.done();
}

/* One material per family: vertex colour picks the slot, per-instance
   attributes carry that instance's three palette colours. */
function fleetMaterial(THREE) {
  const m = new THREE.MeshStandardMaterial({ color: 0xffffff, vertexColors: true, roughness: 0.62, metalness: 0.08, flatShading: true });
  m.onBeforeCompile = (sh) => {
    sh.vertexShader = 'attribute vec3 fleetBody;\nattribute vec3 fleetTrim;\nattribute vec3 fleetAccent;\n' +
      sh.vertexShader.replace('#include <color_vertex>',
        '#include <color_vertex>\n  vColor.rgb = color.r * fleetBody + color.g * fleetTrim + color.b * fleetAccent;');
  };
  m.customProgramCacheKey = () => 'fleet-palette-v1';
  return m;
}

function fleetHex(reg, token) {
  const c = fleetNeed(reg, 'colours', 'registry');
  if (!(token in c)) throw new Error('fleetkit: colour token ' + token + ' is not in the registry');
  return c[token];
}

/* ONE InstancedMesh per family. capacity: {familyId: n} - how many of that
   family may stand at once (every family in the registry must be named).
   Returns { group, families, spawn(id, pose) -> handle, drawCalls() }. */
function fleetCreate(THREE, reg, capacity) {
  const group = new THREE.Group(); group.name = 'fleet';
  const byId = new Map(reg.fleet.map((e) => [e.id, e]));
  const families = new Map();
  const mat = fleetMaterial(THREE);
  const zero = new THREE.Matrix4().makeScale(0, 0, 0);
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
    const mesh = new THREE.InstancedMesh(geo, mat, cap);
    mesh.name = 'fleet:' + f.id; mesh.frustumCulled = false;
    for (let i = 0; i < cap; i++) mesh.setMatrixAt(i, zero);
    mesh.visible = false;   // an empty family costs no draw call
    group.add(mesh);
    families.set(f.id, { family: f, mesh, ref, attrs, free: Array.from({ length: cap }, (_, i) => cap - 1 - i), used: 0 });
  }
  const tmpC = new THREE.Color(), q = new THREE.Quaternion(), e3 = new THREE.Euler(), m4 = new THREE.Matrix4();
  const v3 = new THREE.Vector3(), s3 = new THREE.Vector3();
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
    const scale = [e.dims_m.width / F.ref.width, e.dims_m.height / F.ref.height, e.dims_m.length / F.ref.length];
    const h = {
      id, entry: e, family: e.family, slot, alive: true,
      set(p) {
        if (!h.alive) throw new Error('fleetkit: set on a despawned ' + id);
        e3.set(p.pitch || 0, p.yaw, p.roll || 0, 'YXZ'); q.setFromEuler(e3);
        const k = 'scale' in p ? p.scale : 1;   // display-only multiplier (a showroom lineup); physics never sets it
        m4.compose(v3.set(p.x, p.y, p.z), q, s3.set(scale[0] * k, scale[1] * k, scale[2] * k));
        F.mesh.setMatrixAt(slot, m4); F.mesh.instanceMatrix.needsUpdate = true;
      },
      despawn() { if (!h.alive) return; h.alive = false; F.mesh.setMatrixAt(slot, zero); F.mesh.instanceMatrix.needsUpdate = true; F.free.push(slot); F.used--; F.mesh.visible = F.used > 0; },
    };
    h.set(pose);
    return h;
  }
  return { group, families, spawn, drawCalls: () => families.size };
}

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
  };
}
function fleetCanSpawn(spec, ground, x, z) {
  const depth = fleetDepth(ground, x, z);
  if (spec.medium === 'land') return depth > FLEET_MIN_WET_M ? { ok: false, reason: 'water: a land vehicle stays on ground' } : { ok: true, reason: '' };
  return depth < spec.draft + FLEET_KEEL_CLEAR_M ? { ok: false, reason: 'land: a boat needs water under its keel' } : { ok: true, reason: '' };
}
function fleetState(spec, ground, x, z, yaw) {
  const c = fleetCanSpawn(spec, ground, x, z);
  if (!c.ok) throw new Error('fleetkit: cannot place ' + spec.id + ' here - ' + c.reason);
  const st = { x, z, yaw, y: 0, v: 0, steer: 0, pitch: 0, roll: 0, t: 0, refused: 0, wake: 0, phase: (x * 0.37 + z * 0.11) % 6.283 };
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
  st.steer += (Math.max(-1, Math.min(1, input.steer)) - st.steer) * Math.min(1, 8 * dt);
}
function fleetMove(st, spec, yawRate, dt, ok) {
  const yaw = st.yaw + yawRate * dt;
  const sx = Math.sin(yaw), sz = Math.cos(yaw);
  const nx = st.x + sx * st.v * dt, nz = st.z + sz * st.v * dt;
  const lead = Math.sign(st.v) * spec.L / 2;
  if (!ok(nx, nz) || !ok(nx + sx * lead, nz + sz * lead)) {   // the centre and the leading end
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

/* a boat wake: flat rings dropped behind moving boats, ONE draw call */
function fleetWake(THREE, cap) {
  const geo = new THREE.RingGeometry(0.7, 1, 20).rotateX(-Math.PI / 2);
  const mat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.35, depthWrite: false });
  const mesh = new THREE.InstancedMesh(geo, mat, cap); mesh.name = 'fleet:wake'; mesh.frustumCulled = false;
  const rings = [], m4 = new THREE.Matrix4(), zero = new THREE.Matrix4().makeScale(0, 0, 0);
  for (let i = 0; i < cap; i++) mesh.setMatrixAt(i, zero);
  let next = 0, acc = 0;
  return {
    mesh,
    emit(st, spec, dt) {
      acc += dt * st.wake * 12;
      while (acc >= 1) {
        acc -= 1;
        rings[next] = { x: st.x - Math.sin(st.yaw) * spec.L * 0.5, y: st.y + spec.draft + 0.03, z: st.z - Math.cos(st.yaw) * spec.L * 0.5, age: 0, w: spec.W * 0.5 };
        next = (next + 1) % cap;
      }
    },
    update(dt) {
      for (let i = 0; i < cap; i++) {
        const r = rings[i];
        if (!r) continue;
        r.age += dt;
        if (r.age > 3) { rings[i] = null; mesh.setMatrixAt(i, zero); continue; }
        const sc = r.w + r.age * 2.2;
        m4.makeScale(sc, 1, sc).setPosition(r.x, r.y, r.z); mesh.setMatrixAt(i, m4);
      }
      mesh.instanceMatrix.needsUpdate = true;
    },
  };
}
/* FLEET_KIT:END */
export { FLEET_API, FLEET_SLOTS, FLEET_MIN_WET_M, FLEET_KEEL_CLEAR_M, fleetFamilyGeometry, fleetMaterial, fleetCreate,
  fleetGroundFromWilds, fleetFlatGround, fleetDepth, fleetSpec, fleetCanSpawn, fleetState, fleetLandStep, fleetBoatStep,
  fleetStep, fleetNearest, fleetExitPoint, fleetChaseCamera, fleetWake };
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
