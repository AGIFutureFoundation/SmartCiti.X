#!/usr/bin/env python3
"""Ambient kit for the parish worlds: grass, bushes and palms swaying in ONE
wind field, AUTHORED litter, bird flocks, and generic pets and animals that
wander, flee and follow - budgeted by distance, off in the overview.

    from ambientkit import AMBIENT_JS, AMBIENT_JS_INLINE, ambient_data

AMBIENT_JS is ES module text (export list at the end; also sets
globalThis.TCAMBIENT); AMBIENT_JS_INLINE is the same code without the export
line, for pasting into the page's module script where THREE is in scope.
ambient_data() returns the registry ambient/registry/ambient.json (built by
python3 ambient/build.py) and fails by name when it is missing or stale.

The kit brings no texture, photograph or model file and fetches nothing:
every mesh is a few triangles built in the browser, coloured per instance.
It makes exactly six InstancedMesh (grass, bush, palm, litter, bird, animal)
so it adds at most six draw calls. Scatter is deterministic from
(seed, chunk i, chunk j). Animals are never harmed: they flee or follow the
player, and step off (never onto) a road while a vehicle is near; PHYS blocks
vehicles before contact. The contract is $SP/AMBIENT_CONTRACT.md.

    python3 web/ambientkit.py --emit     prints AMBIENT_JS (ambient/test.mjs imports it)
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REG_PATH = ROOT / 'ambient' / 'registry' / 'ambient.json'


class AmbientKitError(Exception):
    pass


def ambient_data():
    """The ambient registry, JSON-safe, for embedding. Fails by name."""
    if not REG_PATH.exists():
        raise AmbientKitError('ambient/registry/ambient.json missing: run python3 ambient/build.py')
    r = subprocess.run([sys.executable, str(ROOT / 'ambient' / 'build.py'), '--check'],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise AmbientKitError('ambient/registry/ambient.json is stale: run python3 ambient/build.py')
    return json.loads(REG_PATH.read_text())


AMBIENT_CORE = r"""/* ------------------------------------------------------ TCAMBIENT kit ---
   AUTHORED ambience: generic species, not a wildlife survey; litter is set dressing (play, never a record);
   one AUTHORED wind field (not a forecast). Contract: AMBIENT_CONTRACT.md. */
class AmbientError extends Error {}
function ambNeed(obj, key, where) {
  if (obj === null || typeof obj !== 'object' || !(key in obj)) throw new AmbientError(where + ': missing "' + key + '"');
  return obj[key];
}
/* deterministic hash -> [0, 1) and a small PRNG (mulberry32) */
function ambHash(a, b, seed, k) {
  let h = (Math.imul(a | 0, 374761393) + Math.imul(b | 0, 668265263) + Math.imul(seed | 0, 2246822519) + Math.imul(k | 0, 3266489917)) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177); h ^= h >>> 16;
  return h >>> 0;
}
function ambRng(s) {
  let t = s >>> 0;
  return () => { t = (t + 0x6D2B79F5) >>> 0; let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r); return ((r ^ (r >>> 14)) >>> 0) / 4294967296; };
}
const AMB_VEG = ['grass', 'bush', 'palm', 'litter'];
/* One chunk's scatter: pure and deterministic from (seed, ci, cj). A candidate is kept with probability
   density(landUse at the point) / max density, so the expected count follows the AUTHORED density per hectare,
   never more than budgets.per_chunk. Nothing lands on a road or off the ground. */
function scatterChunk(data, seed, ci, cj, chunkM, landUse, isRoad, isGround) {
  const dens = ambNeed(data, 'densities_per_ha', 'ambient data'), uses = ambNeed(data, 'land_uses', 'ambient data');
  const per = ambNeed(ambNeed(data, 'budgets', 'ambient data'), 'per_chunk', 'budgets');
  const ha = chunkM * chunkM / 10000, x0 = ci * chunkM, z0 = cj * chunkM;
  const useAt = (x, z) => {
    const u = typeof landUse === 'function' ? landUse(x, z) : landUse;
    if (!uses.includes(u)) throw new AmbientError('scatterChunk: land use "' + u + '" has no AUTHORED density');
    return ambNeed(dens, u, 'densities_per_ha');
  };
  const out = { grass: [], bush: [], palm: [], litter: [], animals: [], flocks: [] };
  const draw = (key, maxD, cap, dAt, push) => {
    if (!(maxD > 0)) return;
    const n = Math.min(cap, Math.ceil(maxD * ha)), r = ambRng(ambHash(ci, cj, seed, key));
    for (let i = 0; i < n; i++) {
      const x = x0 + r() * chunkM, z = z0 + r() * chunkM, keep = r(), a = r(), b = r();
      if (!isGround(x, z) || isRoad(x, z)) continue;
      if (keep * maxD >= dAt(useAt(x, z))) continue;
      push(x, z, a, b, i);
    }
  };
  const maxOf = (f) => Math.max(...uses.map((u) => f(dens[u])));
  const veg = ambNeed(data, 'vegetation', 'ambient data'), litterIds = Object.keys(ambNeed(data, 'litter', 'ambient data'));
  AMB_VEG.forEach((kind, ki) => {
    draw(11 + ki, maxOf((d) => ambNeed(d, kind, 'density')), ambNeed(per, kind, 'per_chunk'), (d) => d[kind], (x, z, a, b, i) => {
      if (kind === 'litter') out.litter.push([x, z, litterIds[Math.floor(a * litterIds.length)], b * Math.PI * 2, ci + ',' + cj + ',' + i]);
      else out[kind].push([x, z, a, b]);
    });
  });
  const spc = ambNeed(data, 'species', 'ambient data');
  Object.keys(spc).sort().forEach((sid, si) => {
    const grp = spc[sid].kind === 'bird' ? 'flocks' : 'animals';
    draw(101 + si, maxOf((d) => ambNeed(d, grp, 'density')[sid] || 0), ambNeed(per, grp === 'flocks' ? 'flock' : 'animal', 'per_chunk'),
      (d) => d[grp][sid] || 0, (x, z, a, b, i) => out[grp].push({ sp: sid, x, z, hx: x, hz: z, a, b, id: ci + ',' + cj + ',' + sid + ',' + i }));
  });
  out.animals = out.animals.slice(0, per.animal); out.flocks = out.flocks.slice(0, per.flock);
  return out;
}
/* The ONE wind field (pure): unit direction in scene x/z (x = east, z = -north), a travelling-wave number and
   phase speed from the AUTHORED speed and wavelength, and a slow gust envelope. */
function windAt(wind, t) {
  const th = ambNeed(wind, 'toward_deg', 'wind') * Math.PI / 180, L = ambNeed(wind, 'wavelength_m', 'wind');
  const speed = ambNeed(wind, 'speed_mps', 'wind'), per = ambNeed(wind, 'gust_period_s', 'wind'), g = ambNeed(wind, 'gust_gain', 'wind');
  const gust = g * (0.5 + 0.5 * Math.sin(2 * Math.PI * t / per));
  return { dx: Math.cos(th), dz: -Math.sin(th), k: 2 * Math.PI / L, w: 2 * Math.PI * speed / L,
    strength: (0.35 + 0.65 * Math.min(1, speed / 8)) * (1 + gust) };
}
function ambNearestVehicle(a, vehicles) {
  let best = Infinity;
  for (const v of vehicles) { const d = Math.hypot(v.x - a.x, v.z - a.z); if (d < best) best = d; }
  return best;
}
/* One animal step (pure apart from mutating a). Modes: wander | flee | follow | yield. Never towards a vehicle,
   never onto a road while one is within vehicle_alert_m, never off the ground. */
function stepAnimal(a, sp, beh, player, vehicles, dt, isRoad, isGround) {
  if (a.rng === undefined) { a.rng = ambRng(ambHash(Math.floor(a.hx), Math.floor(a.hz), 7, 99)); a.hd = a.rng() * Math.PI * 2; a.turn = 0; a.calm = 0; }
  const dp = Math.hypot(player.x - a.x, player.z - a.z), alert = ambNearestVehicle(a, vehicles) < beh.vehicle_alert_m;
  let vx = 0, vz = 0, mode = 'wander';
  a.calm = Math.max(0, a.calm - dt);
  if (sp.flee_m > 0 && (dp < sp.flee_m || (a.mode === 'flee' && a.calm > 0))) {
    if (dp < sp.flee_m) a.calm = beh.flee_calm_s;
    const d = Math.max(dp, 1e-6); vx = (a.x - player.x) / d * sp.run_mps; vz = (a.z - player.z) / d * sp.run_mps; mode = 'flee';
  } else if (sp.follows && dp < sp.follow_m && dp > sp.keep_m) {
    const s = dp > sp.follow_m / 2 ? sp.run_mps : sp.walk_mps; vx = (player.x - a.x) / dp * s; vz = (player.z - a.z) / dp * s; mode = 'follow';
  } else if (sp.follows && dp <= sp.keep_m) {
    mode = 'follow';
  } else {
    a.turn -= dt;
    if (a.turn <= 0) { a.turn = beh.wander_turn_s[0] + a.rng() * (beh.wander_turn_s[1] - beh.wander_turn_s[0]); a.hd += (a.rng() - 0.5) * 2.4; }
    const home = Math.hypot(a.hx - a.x, a.hz - a.z);
    if (home > beh.wander_radius_m) a.hd = Math.atan2(a.hz - a.z, a.hx - a.x);
    vx = Math.cos(a.hd) * sp.walk_mps; vz = Math.sin(a.hd) * sp.walk_mps;
  }
  if (alert && isRoad(a.x, a.z)) {
    /* on a road with a vehicle near: step to the nearest off-road point (4 probes at road_step_m, then 2x) */
    let tx = null, tz = null;
    for (const m of [1, 2, 3]) for (let k = 0; k < 8 && tx === null; k++) {
      const px = a.x + Math.cos(k * Math.PI / 4) * beh.road_step_m * m, pz = a.z + Math.sin(k * Math.PI / 4) * beh.road_step_m * m;
      if (!isRoad(px, pz) && isGround(px, pz)) { tx = px; tz = pz; }
    }
    if (tx !== null) { const d = Math.hypot(tx - a.x, tz - a.z); vx = (tx - a.x) / d * sp.run_mps; vz = (tz - a.z) / d * sp.run_mps; }
    mode = 'yield';
  }
  const nx = a.x + vx * dt, nz = a.z + vz * dt;
  const blocked = !isGround(nx, nz) || (alert && mode !== 'yield' && isRoad(nx, nz) && !isRoad(a.x, a.z));
  if (!blocked) { a.x = nx; a.z = nz; } else if (mode === 'wander') { a.hd += Math.PI * (0.5 + a.rng()); a.turn = 1; }
  if (vx !== 0 || vz !== 0) a.yaw = Math.atan2(vx, vz);
  a.mode = mode; a.moving = !blocked && (vx !== 0 || vz !== 0);
  return a;
}
/* One flock step: perched species (hop/perch) sit and flush when the player is inside flush_m, then return;
   the rest circle at the world.json fauna heights. */
function stepFlock(f, sp, beh, player, dt) {
  if (f.t === undefined) { f.t = f.a * 100; f.r = beh.bird_circle_m[0] + f.b * (beh.bird_circle_m[1] - beh.bird_circle_m[0]); f.air = 0; }
  f.t += dt;
  const perches = sp.motion === 'perch' || sp.motion === 'hop';
  if (perches && sp.flush_m > 0 && Math.hypot(player.x - f.x, player.z - f.z) < sp.flush_m) f.air = beh.perch_return_s;
  f.air = Math.max(0, f.air - dt);
  f.flying = !perches || f.air > 0;
  return f;
}
function ambBirdPose(f, sp, i, out) {
  const n = i * 2.399, h = sp.height_m;
  if (!f.flying) { out.x = f.x + Math.cos(n) * 1.2 * (1 + i * 0.3); out.z = f.z + Math.sin(n) * 1.2 * (1 + i * 0.3); out.y = 0.02; out.yaw = n; out.flap = 0; return out; }
  const w = sp.fly_mps / f.r, ang = f.t * w + i * 0.5;
  const hi = h[1] > 0 ? h[0] + (h[1] - h[0]) * (0.5 + 0.5 * Math.sin(f.t * 0.2 + i)) : 3 + 2 * Math.sin(f.t + i);
  out.x = f.x + Math.cos(ang) * (f.r + i * 1.5); out.z = f.z + Math.sin(ang) * (f.r + i * 1.5); out.y = hi;
  out.yaw = -ang; out.flap = sp.motion === 'glide' ? 0.15 : Math.sin(f.t * 12 + i);
  return out;
}

function createAmbient(scene, opts) {
  const THREE = ambNeed(opts, 'THREE', 'createAmbient opts'), data = ambNeed(opts, 'data', 'createAmbient opts');
  const seed = ambNeed(opts, 'seed', 'createAmbient opts'), chunkM = ambNeed(opts, 'chunkM', 'createAmbient opts');
  const isRoad = ambNeed(opts, 'isRoad', 'createAmbient opts'), isGround = ambNeed(opts, 'isGround', 'createAmbient opts');
  if (!Number.isInteger(seed)) throw new AmbientError('createAmbient: seed must be an integer');
  if (typeof isRoad !== 'function' || typeof isGround !== 'function') throw new AmbientError('createAmbient: isRoad and isGround must be functions');
  const B = ambNeed(data, 'budgets', 'ambient data'), CAP = B.cap, LOD = B.lod_m, spc = data.species, beh = data.behaviour;
  const wind = ambNeed(data, 'wind', 'ambient data'), veg = data.vegetation;
  /* ---- geometry: a few triangles each, built here (no files) ---- */
  const tris = (P) => { const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); g.computeVertexNormals(); return g; };
  const quadP = (a, b, c, d) => [...a, ...b, ...c, ...a, ...c, ...d];
  const grassGeo = tris([...quadP([-0.5, 0, 0], [0.5, 0, 0], [0.15, 1, 0], [-0.15, 1, 0]), ...quadP([0, 0, -0.5], [0, 0, 0.5], [0, 1, 0.15], [0, 1, -0.15])]);   // 4 tris, height 1
  const bushGeo = new THREE.IcosahedronGeometry(0.5, 0).translate(0, 0.5, 0);   // 20 tris, 0..1 high
  const palmP = [];
  for (let k = 0; k < 4; k++) { const a0 = k * Math.PI / 2, a1 = a0 + Math.PI / 2, r = 0.022;
    palmP.push(...quadP([Math.cos(a0) * r * 1.4, 0, Math.sin(a0) * r * 1.4], [Math.cos(a1) * r * 1.4, 0, Math.sin(a1) * r * 1.4], [Math.cos(a1) * r, 0.92, Math.sin(a1) * r], [Math.cos(a0) * r, 0.92, Math.sin(a0) * r])); }
  for (let k = 0; k < 6; k++) { const a = k * Math.PI / 3, c = Math.cos(a), s = Math.sin(a), L = 0.2;
    palmP.push(0, 0.95, 0, c * L - s * 0.04, 0.9, s * L + c * 0.04, c * L + s * 0.04, 0.9, s * L - c * 0.04,
      c * L - s * 0.04, 0.9, s * L + c * 0.04, c * L * 1.8, 0.78, s * L * 1.8, c * L + s * 0.04, 0.9, s * L - c * 0.04); }
  const palmGeo = tris(palmP);   // 8 trunk + 12 frond tris, height 1
  const litterGeo = new THREE.BoxGeometry(1, 0.35, 0.7).translate(0, 0.175, 0);   // 12 tris
  const birdGeo = tris([0, 0, 0.35, -0.5, 0, -0.1, 0, 0, -0.2, 0, 0, 0.35, 0, 0, -0.2, 0.5, 0, -0.1, 0, 0.04, 0.4, -0.05, 0, -0.3, 0.05, 0, -0.3]);   // 3 tris
  const animalGeo = (() => { const b = new THREE.BoxGeometry(0.45, 0.4, 1).translate(0, 0.55, 0).toNonIndexed(), h = new THREE.BoxGeometry(0.3, 0.3, 0.34).translate(0, 0.8, 0.6).toNonIndexed();
    const P = [...b.attributes.position.array, ...h.attributes.position.array];
    for (const [x, z] of [[-0.15, 0.35], [0.15, 0.35], [-0.15, -0.35], [0.15, -0.35]]) P.push(...quadP([x - 0.05, 0, z], [x + 0.05, 0, z], [x + 0.05, 0.36, z], [x - 0.05, 0.36, z]));
    return tris(P); })();   // 24 + 8 = 32 tris, 1 m long
  /* ---- ONE shared wind field: the same uniform objects on every swaying material ---- */
  const WIND = { uWindT: { value: 0 }, uWindDir: { value: new THREE.Vector2(1, 0) }, uWindK: { value: 0 }, uWindW: { value: 0 }, uWindS: { value: 0 } };
  const amp = ambNeed(wind, 'amplitude_m', 'wind');
  function swayMat(kind, side) {
    const m = new THREE.MeshLambertMaterial({ color: 0xffffff, side });
    const uAmp = { value: ambNeed(amp, kind, 'wind.amplitude_m') };
    m.onBeforeCompile = (sh) => {
      Object.assign(sh.uniforms, WIND, { uWindAmp: uAmp });
      sh.vertexShader = 'uniform float uWindT, uWindK, uWindW, uWindS, uWindAmp; uniform vec2 uWindDir;\n' + sh.vertexShader.replace('#include <begin_vertex>', `#include <begin_vertex>
  { vec4 ambO = modelMatrix * instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0);
    float ambW = sin(uWindT * uWindW - dot(ambO.xz, uWindDir) * uWindK) * 0.5 + 0.5;
    float ambH = clamp(position.y, 0.0, 1.0);
    vec3 ambD = vec3(uWindDir.x, 0.0, uWindDir.y) * uWindAmp * uWindS * ambW * ambH * ambH;
    mat3 ambM = mat3(instanceMatrix);
    transformed += transpose(ambM) * ambD / max(dot(ambM[0], ambM[0]), 1e-4); }`);
    };
    m.customProgramCacheKey = () => 'tc-ambient-sway-' + kind;
    return m;
  }
  const plain = () => new THREE.MeshLambertMaterial({ color: 0xffffff });
  const meshes = {
    grass: new THREE.InstancedMesh(grassGeo, swayMat('grass', THREE.DoubleSide), CAP.grass),
    bush: new THREE.InstancedMesh(bushGeo, swayMat('bush', THREE.FrontSide), CAP.bush),
    palm: new THREE.InstancedMesh(palmGeo, swayMat('palm', THREE.DoubleSide), CAP.palm),
    litter: new THREE.InstancedMesh(litterGeo, plain(), CAP.litter),
    bird: new THREE.InstancedMesh(birdGeo, new THREE.MeshLambertMaterial({ color: 0xffffff, side: THREE.DoubleSide }), CAP.bird),
    animal: new THREE.InstancedMesh(animalGeo, plain(), CAP.animal),
  };
  if (Object.keys(meshes).length > B.draw_calls_max) throw new AmbientError('createAmbient: more meshes than budgets.draw_calls_max');
  const C = new THREE.Color();
  for (const [k, m] of Object.entries(meshes)) { m.setColorAt(0, C.set(0xffffff)); m.count = 0; m.frustumCulled = false; m.name = 'tc-ambient-' + k; scene.add(m); }
  const chunks = new Map(), picked = new Set();
  let overview = false, t = 0, lastX = Infinity, lastZ = Infinity, dirty = true, activeAnimals = [], activeFlocks = [], ms = 0;
  const M4 = new THREE.Matrix4(), Q = new THREE.Quaternion(), V = new THREE.Vector3(), S = new THREE.Vector3(), E = new THREE.Euler(), UP = new THREE.Vector3(0, 1, 0);
  const pick = (arr, a) => arr[Math.min(arr.length - 1, Math.floor(a * arr.length))];
  function refill(px, pz) {
    const order = [...chunks.values()].sort((p, q) => Math.hypot(p.cx - px, p.cz - pz) - Math.hypot(q.cx - px, q.cz - pz));
    const n = { grass: 0, bush: 0, palm: 0, litter: 0 };
    activeAnimals = []; activeFlocks = [];
    const near = (x, z, r) => (x - px) * (x - px) + (z - pz) * (z - pz) < r * r;
    const half = chunkM * 0.7072, reach = (c, k) => Math.hypot(c.cx - px, c.cz - pz) <= LOD[k] + half;   // skip whole chunks beyond a kind's LOD
    for (const c of order) {
      if (reach(c, 'grass')) for (const [x, z, a, b] of c.s.grass) { if (n.grass >= CAP.grass) break; if (!near(x, z, LOD.grass)) continue;
        const h = veg.grass.height_m[0] + a * (veg.grass.height_m[1] - veg.grass.height_m[0]);
        M4.compose(V.set(x, 0, z), Q.setFromAxisAngle(UP, b * Math.PI), S.set(veg.grass.width_m, h, veg.grass.width_m)); meshes.grass.setMatrixAt(n.grass, M4); meshes.grass.setColorAt(n.grass++, C.set(pick(veg.grass.colors, b))); }
      if (reach(c, 'bush')) for (const [x, z, a, b] of c.s.bush) { if (n.bush >= CAP.bush) break; if (!near(x, z, LOD.bush)) continue;
        const w = veg.bush.width_m[0] + b * (veg.bush.width_m[1] - veg.bush.width_m[0]);
        M4.compose(V.set(x, 0, z), Q.setFromAxisAngle(UP, a * 6.28), S.set(w, veg.bush.height_m[0] + a * (veg.bush.height_m[1] - veg.bush.height_m[0]), w * 0.85)); meshes.bush.setMatrixAt(n.bush, M4); meshes.bush.setColorAt(n.bush++, C.set(pick(veg.bush.colors, a))); }
      if (reach(c, 'palm')) for (const [x, z, a, b] of c.s.palm) { if (n.palm >= CAP.palm) break; if (!near(x, z, LOD.palm)) continue;
        const h = veg.palm.height_m[0] + a * (veg.palm.height_m[1] - veg.palm.height_m[0]);
        M4.compose(V.set(x, 0, z), Q.setFromAxisAngle(UP, b * 6.28), S.set(h, h, h)); meshes.palm.setMatrixAt(n.palm, M4); meshes.palm.setColorAt(n.palm++, C.set(pick(veg.palm.colors, b))); }
      if (reach(c, 'litter')) for (const [x, z, type, yaw, id] of c.s.litter) { if (n.litter >= CAP.litter) break; if (picked.has(id) || !near(x, z, LOD.litter)) continue;
        const L = data.litter[type], s = L.size_m, flat = type === 'paper' || type === 'bag' ? 0.15 : 1;
        M4.compose(V.set(x, 0, z), Q.setFromAxisAngle(UP, yaw), S.set(s, s * flat, s)); meshes.litter.setMatrixAt(n.litter, M4); meshes.litter.setColorAt(n.litter++, C.set(L.color)); }
      for (const a of c.s.animals) if (activeAnimals.length < CAP.animal && near(a.x, a.z, LOD.animal)) activeAnimals.push(a);
      for (const f of c.s.flocks) if (near(f.x, f.z, LOD.bird)) activeFlocks.push(f);
    }
    for (const k of ['grass', 'bush', 'palm', 'litter']) { meshes[k].count = n[k]; meshes[k].instanceMatrix.needsUpdate = true; if (meshes[k].instanceColor) meshes[k].instanceColor.needsUpdate = true; }
    lastX = px; lastZ = pz; dirty = false;
  }
  function drawMovers(dt, player) {
    let na = 0;
    for (const a of activeAnimals) {
      const sp = spc[a.sp]; stepAnimal(a, sp, beh, player, curVehicles, dt, isRoad, isGround);
      const s = sp.size_m, bob = a.moving ? Math.abs(Math.sin(t * 9 + a.a * 6)) * 0.04 * s : 0;
      M4.compose(V.set(a.x, bob, a.z), Q.setFromAxisAngle(UP, a.yaw || 0), S.set(s, s, s)); meshes.animal.setMatrixAt(na, M4); meshes.animal.setColorAt(na++, C.set(sp.color));
    }
    meshes.animal.count = na; meshes.animal.instanceMatrix.needsUpdate = true; if (meshes.animal.instanceColor) meshes.animal.instanceColor.needsUpdate = true;
    let nb = 0; const P = {};
    for (const f of activeFlocks) {
      const sp = spc[f.sp]; stepFlock(f, sp, beh, player, dt);
      for (let i = 0; i < Math.min(sp.flock, B.flock_size_max) && nb < CAP.bird; i++) {
        ambBirdPose(f, sp, i, P);
        E.set(0, P.yaw, 0); Q.setFromEuler(E);
        M4.compose(V.set(P.x, P.y, P.z), Q, S.set(sp.span_m, 1 + P.flap * 2, sp.span_m)); meshes.bird.setMatrixAt(nb, M4); meshes.bird.setColorAt(nb++, C.set(sp.color));
      }
    }
    meshes.bird.count = nb; meshes.bird.instanceMatrix.needsUpdate = true; if (meshes.bird.instanceColor) meshes.bird.instanceColor.needsUpdate = true;
  }
  let curVehicles = [];
  const api = {
    budgets: JSON.parse(JSON.stringify(B)),
    onChunkLoad(ci, cj, landUse) {
      const key = ci + ',' + cj; if (chunks.has(key)) return;
      chunks.set(key, { cx: (ci + 0.5) * chunkM, cz: (cj + 0.5) * chunkM, s: scatterChunk(data, seed, ci, cj, chunkM, landUse, isRoad, isGround) }); dirty = true;
    },
    onChunkUnload(ci, cj) { if (chunks.delete(ci + ',' + cj)) dirty = true; },
    update(dt, player, vehicles) {
      if (overview) return;
      const t0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
      if (!player || !Number.isFinite(player.x) || !Number.isFinite(player.z)) throw new AmbientError('update: player {x, z} required');
      if (!Array.isArray(vehicles)) throw new AmbientError('update: vehicles must be an array (may be empty)');
      t += dt; curVehicles = vehicles;
      const w = windAt(wind, t);
      WIND.uWindT.value = t; WIND.uWindDir.value.set(w.dx, w.dz); WIND.uWindK.value = w.k; WIND.uWindW.value = w.w; WIND.uWindS.value = w.strength;
      if (dirty || Math.hypot(player.x - lastX, player.z - lastZ) > B.refill_m) refill(player.x, player.z);
      drawMovers(dt, player);
      ms = (typeof performance !== 'undefined' ? performance.now() : Date.now()) - t0;
    },
    setOverview(on) { overview = !!on; for (const m of Object.values(meshes)) m.visible = !overview; },
    litterNear(x, z, r) { const out = []; for (const c of chunks.values()) for (const [lx, lz, type, , id] of c.s.litter) if (!picked.has(id) && Math.hypot(lx - x, lz - z) <= r) out.push({ id, type, x: lx, z: lz }); return out; },
    pickLitter(id) { if (picked.has(id)) return false; picked.add(id); dirty = true; return true; },
    stats() {
      const inst = {}; let dc = 0;
      for (const [k, m] of Object.entries(meshes)) { inst[k] = m.count; if (m.visible && m.count > 0) dc++; }
      return { drawCalls: dc, meshes: Object.keys(meshes).length, instances: inst, chunks: chunks.size, animalsActive: activeAnimals.length,
        modes: activeAnimals.reduce((o, a) => { o[a.mode || 'wander'] = (o[a.mode || 'wander'] || 0) + 1; return o; }, {}), ms, overview };
    },
    animals() { return activeAnimals.map((a) => ({ sp: a.sp, x: a.x, z: a.z, mode: a.mode })); },
    /* for PHYS fleetPhysStep ctx.people: every active animal as a circle a vehicle is never moved into */
    people() { return activeAnimals.map((a) => ({ x: a.x, z: a.z, r: spc[a.sp].size_m / 2 + 0.3, cls: spc[a.sp].cls })); },
    dispose() {
      for (const m of Object.values(meshes)) { scene.remove(m); m.geometry.dispose(); m.material.dispose(); m.dispose(); }
      chunks.clear(); activeAnimals = []; activeFlocks = [];
    },
    meshes,
  };
  return api;
}
globalThis.TCAMBIENT = { createAmbient, scatterChunk, windAt, stepAnimal, stepFlock, ambHash, AmbientError };
"""

AMBIENT_EXPORT = '\nexport { createAmbient, scatterChunk, windAt, stepAnimal, stepFlock, ambHash, ambRng, AmbientError };\n'
AMBIENT_JS_INLINE = AMBIENT_CORE
AMBIENT_JS = AMBIENT_CORE + AMBIENT_EXPORT

if __name__ == '__main__':
    if '--emit' in sys.argv:
        sys.stdout.write(AMBIENT_JS)
    else:
        print(__doc__)
