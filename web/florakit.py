#!/usr/bin/env python3
"""florakit: regional vegetation and street detail for the parish, Bay and Unspoken Smiles worlds.

    from florakit import FLORA_JS, FLORA_JS_INLINE, flora_data, flora_mount_js

FLORA_JS is ES module text (export list at the end; also sets globalThis.TCFLORA); FLORA_JS_INLINE is the
same code without the export line, for pages that paste it into their own module script.

Data: flora/registry/flora.json (python3 flora/build.py). Species are real regional plants named generally;
sizes, colours, densities and placement rules are AUTHORED - not a tree survey, species map or count.

JS API (THREE r160 in scope; no textures, no assets, no network):
  const fl = createFlora(scene, {THREE, data, region, seed, chunkM, isGround, isRoad, isWater, landUse, groundY});
    isGround/isRoad/isWater (x, z) -> bool; landUse (x, z) -> one of data.regions[region].land_uses (else throws);
    groundY (x, z) -> metres (the page's ground: 0 on flat AUTHORED ground, or a terrain sampler).
  fl.update({x, z})     stream chunks around the player (budgets.chunks_per_tick) and refill the nearest instances
  fl.setOverview(bool)  true: every flora mesh hidden (0 draw calls)
  fl.setEnabled(bool)   false: hidden and not streamed (eval A/B)
  fl.reset()            drop every placed chunk and re-place (the page calls it when its RECORDED land cover arrives)
  landClass (x, z) -> ESA WorldCover class code (RECORDED) or null (no class there: the AUTHORED land-use rules apply, counted)
  fl.stats()            {drawCalls, families{f: n}, species{id: n}, tris, chunks, queue, region}
  fl.placeChunk(ci, cj) the chunk's deterministic item list (pure: same inputs -> same list)
  fl.near(x, z, r)      drawn items within r (eval / tests)
  fl.dispose()
  ENV w15 footprint adapters (optional; when given they must be functions, else FloraError by name):
    footprint (x, z) -> true when the point stands inside a page building footprint: the sample is dropped
      (plants AND kerb details), counted in stats().footprint {checked, skipped}; absent -> null.
    chunkReady (ci, cj) -> false while the page has not built that chunk's buildings yet: the chunk is held
      at the back of the stream queue (re-tried on later ticks, counted in stats().footprint.deferred), so a
      footprint test never runs against missing buildings.
One InstancedMesh per family (7 at most, registry budgets.draw_calls_max), two shared materials, per-instance
colour, nearest-cap distance LOD per family (families.*.lod_m / cap) and a bounding sphere per refill so a
family out of the view frustum is culled whole.

  python3 web/florakit.py --emit    print FLORA_JS (the test imports it)
"""
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
REG_PATH = ROOT / 'flora' / 'registry' / 'flora.json'


class FloraKitError(Exception):
    pass


def flora_data(region=None):
    """The flora registry, JSON-safe (optionally cut to one region's species). Fails by name."""
    if not REG_PATH.exists():
        raise FloraKitError('flora/registry/flora.json missing: run python3 flora/build.py')
    r = subprocess.run([sys.executable, str(ROOT / 'flora' / 'build.py'), '--check'], capture_output=True, text=True)
    if r.returncode != 0:
        raise FloraKitError('flora/registry/flora.json is stale: run python3 flora/build.py')
    reg = json.loads(REG_PATH.read_text(encoding='utf-8'))
    if region is None:
        return reg
    if region not in reg['regions']:
        raise FloraKitError(f'florakit: unknown region {region!r} (have {sorted(reg["regions"])})')
    out = dict(reg)
    out.pop('wilds', None)   # WORLD w16: the wilds ground-flora section is the wilds page's (wilds_flora_data)
    out['regions'] = {region: reg['regions'][region]}
    out['species'] = {k: v for k, v in reg['species'].items() if v['region'] == region}
    return out


FLORA_CORE = r"""/* ------------------------------------------------------- TCFLORA kit ---
   AUTHORED vegetation and street detail: real regional plants named generally, placed by AUTHORED rules on
   land use and distance to water - not a tree survey, species map or count. Registry: flora/registry/flora.json. */
class FloraError extends Error {}
function flNeed(obj, key, where) {
  if (obj === null || typeof obj !== 'object' || !(key in obj)) throw new FloraError('florakit ' + where + ': missing "' + key + '"');
  return obj[key];
}
function flHash(a, b, seed, k) {
  let h = (Math.imul(a | 0, 374761393) + Math.imul(b | 0, 668265263) + Math.imul(seed | 0, 2246822519) + Math.imul(k | 0, 3266489917)) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177); h ^= h >>> 16;
  return h >>> 0;
}
function flRng(s) {
  let a = s >>> 0;
  return () => { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
function flPick(mix, u) {
  const ks = Object.keys(mix); let tot = 0; for (const k of ks) tot += mix[k];
  let acc = 0; for (const k of ks) { acc += mix[k] / tot; if (u < acc) return k; }
  return ks[ks.length - 1];
}
const FL_WATER = ['shore', 'near', 'far'];
/* unit geometries: x, z span the crown (scale = crown m), y spans the height (scale = height m). Non-indexed,
   vertex colour 1 on foliage and a dark neutral on trunks (the per-instance colour multiplies both). */
function floraGeometry(THREE, shape) {
  const P = [], C = [];
  const TR = [0.42, 0.34, 0.28], LF = [1, 1, 1];
  const tri = (a, b, c, col) => { P.push(...a, ...b, ...c); for (let i = 0; i < 3; i++) C.push(...col); };
  const quad = (a, b, c, d, col) => { tri(a, b, c, col); tri(a, c, d, col); };
  const trunk = (y0, y1, r) => { for (let i = 0; i < 4; i++) { const a0 = (i + 0.5) * Math.PI / 2, a1 = (i + 1.5) * Math.PI / 2;
    const p = (a, y) => [Math.cos(a) * r, y, Math.sin(a) * r]; quad(p(a0, y0), p(a1, y0), p(a1, y1), p(a0, y1), TR); } };
  if (shape === 'trunk4+icosa') {
    trunk(0, 0.42, 0.05);
    const g = new THREE.IcosahedronGeometry(1, 0), pos = g.attributes.position;
    for (let i = 0; i < pos.count; i += 3) { const v = (k) => [pos.getX(k) * 0.5, 0.62 + pos.getY(k) * 0.36, pos.getZ(k) * 0.5]; tri(v(i), v(i + 1), v(i + 2), LF); }
    g.dispose();
  } else if (shape === 'trunk4+cone6') {
    trunk(0, 0.2, 0.06);
    for (let i = 0; i < 6; i++) { const a0 = i * Math.PI / 3, a1 = (i + 1) * Math.PI / 3;
      tri([Math.cos(a0) * 0.5, 0.15, Math.sin(a0) * 0.5], [0, 1, 0], [Math.cos(a1) * 0.5, 0.15, Math.sin(a1) * 0.5], LF); }
  } else if (shape === 'trunk4+fronds6') {
    trunk(0, 0.92, 0.04);
    for (let i = 0; i < 6; i++) { const a = i * Math.PI / 3, c = Math.cos(a), s = Math.sin(a), w = 0.07;
      quad([-s * w, 0.93, c * w], [s * w, 0.93, -c * w], [c * 0.5 + s * w, 0.74, s * 0.5 - c * w], [c * 0.5 - s * w, 0.74, s * 0.5 + c * w], LF); }
  } else if (shape === 'drape3') {
    for (let i = 0; i < 3; i++) { const a = i * 2 * Math.PI / 3 + 0.4, x = Math.cos(a) * 0.3, z = Math.sin(a) * 0.3, tx = -Math.sin(a) * 0.08, tz = Math.cos(a) * 0.08;
      quad([x - tx, 0.52, z - tz], [x + tx, 0.52, z + tz], [x + tx * 0.3, 0.3, z + tz * 0.3], [x - tx * 0.3, 0.3, z - tz * 0.3], LF); }
  } else if (shape === 'octa') {
    const t = [0, 1, 0], b = [0, 0, 0], r = [[0.5, 0.5, 0], [0, 0.5, 0.5], [-0.5, 0.5, 0], [0, 0.5, -0.5]];
    for (let i = 0; i < 4; i++) { const a = r[i], c = r[(i + 1) % 4]; tri(a, t, c, LF); tri(c, b, a, LF); }
  } else if (shape === 'blades3') {
    for (let i = 0; i < 3; i++) { const a = i * Math.PI / 3, c = Math.cos(a) * 0.5, s = Math.sin(a) * 0.5;
      quad([-c, 0, -s], [c, 0, s], [c * 0.25, 1, s * 0.25], [-c * 0.25, 1, -s * 0.25], LF); }
  } else if (shape === 'box5') {
    const v = (x, y, z) => [x - 0.5, y, z - 0.5];
    quad(v(0, 1, 0), v(0, 1, 1), v(1, 1, 1), v(1, 1, 0), LF);                                   // top
    quad(v(0, 0, 1), v(1, 0, 1), v(1, 1, 1), v(0, 1, 1), LF); quad(v(1, 0, 0), v(0, 0, 0), v(0, 1, 0), v(1, 1, 0), LF);
    quad(v(1, 0, 1), v(1, 0, 0), v(1, 1, 0), v(1, 1, 1), LF); quad(v(0, 0, 0), v(0, 0, 1), v(0, 1, 1), v(0, 1, 0), LF);
  } else throw new FloraError('florakit: unknown shape ' + shape);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); g.setAttribute('color', new THREE.Float32BufferAttribute(C, 3));
  g.computeVertexNormals(); g.computeBoundingSphere();
  return g;
}
function createFlora(scene, o) {
  const THREE = flNeed(o, 'THREE', 'createFlora'), data = flNeed(o, 'data', 'createFlora'), region = flNeed(o, 'region', 'createFlora');
  const seed = flNeed(o, 'seed', 'createFlora'), chunkM = flNeed(o, 'chunkM', 'createFlora');
  const fn = {};
  for (const k of ['isGround', 'isRoad', 'isWater', 'landUse', 'groundY', 'landClass']) { fn[k] = flNeed(o, k, 'createFlora'); if (typeof fn[k] !== 'function') throw new FloraError('florakit createFlora: ' + k + ' must be a function'); }
  /* ENV w15: optional footprint adapters - given => a function (no silent default: a non-function is named) */
  for (const k of ['footprint', 'chunkReady']) { fn[k] = k in o ? o[k] : null; if (fn[k] !== null && typeof fn[k] !== 'function') throw new FloraError('florakit createFlora: ' + k + ' must be a function when given'); }
  const R = flNeed(flNeed(data, 'regions', 'data'), region, 'data.regions'), B = flNeed(data, 'budgets', 'data'), FAM = flNeed(data, 'families', 'data');
  const SP = flNeed(data, 'species', 'data'), DET = flNeed(data, 'details', 'data'), MOSS = flNeed(data, 'moss', 'data');
  const S = flNeed(B, 'sample_m', 'budgets'), L = flNeed(B, 'water_lattice_m', 'budgets'), K = flNeed(B, 'kerb_probe_m', 'budgets');
  const SHORE = flNeed(B, 'shore_m', 'budgets'), NEAR = flNeed(B, 'near_m', 'budgets'), REFILL = flNeed(B, 'refill_m', 'budgets'), PER_TICK = flNeed(B, 'chunks_per_tick', 'budgets');
  const LU = flNeed(R, 'land_uses', 'region'), RULES = flNeed(R, 'rules', 'region'), DRULES = flNeed(R, 'details', 'region'), LC = flNeed(R, 'landcover', 'region');
  const lcRule = (k) => { const key = String(k); if (!LC || !(key in LC)) throw new FloraError('florakit: land cover class ' + key + ' has no ' + region + ' rule'); return LC[key]; };
  if (Object.keys(FAM).length > flNeed(B, 'draw_calls_max', 'budgets')) throw new FloraError('florakit: more families than budgets.draw_calls_max');
  const mats = { solid: new THREE.MeshLambertMaterial({ vertexColors: true }), double: new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide }) };
  const meshes = {}, C = new THREE.Color();
  for (const [fid, f] of Object.entries(FAM)) {
    const g = floraGeometry(THREE, flNeed(f, 'shape', 'families.' + fid));
    if (g.attributes.position.count / 3 !== flNeed(f, 'tris', 'families.' + fid)) throw new FloraError('florakit: family ' + fid + ' geometry has ' + g.attributes.position.count / 3 + ' triangles, registry says ' + f.tris);
    const m = new THREE.InstancedMesh(g, flNeed(mats, flNeed(f, 'material', 'families.' + fid), 'materials'), flNeed(f, 'cap', 'families.' + fid));
    m.setColorAt(0, C.set('#ffffff')); m.count = 0; m.visible = false; m.name = 'flora:' + fid; m.userData.flora = fid;
    scene.add(m); meshes[fid] = m;
  }
  const maxLod = Math.max(...Object.values(FAM).map((f) => flNeed(f, 'lod_m', 'families')));
  const RC = Math.ceil(maxLod / chunkM);
  const wcache = new Map();
  const wet = (x, z) => { const ix = Math.round(x / L), iz = Math.round(z / L), k = ix + ',' + iz; let v = wcache.get(k); if (v === undefined) { v = !!fn.isWater(ix * L, iz * L); wcache.set(k, v); } return v; };
  const ring = (x, z, r) => { for (let i = 0; i < 8; i++) { const a = i * Math.PI / 4; if (wet(x + Math.cos(a) * r, z + Math.sin(a) * r)) return true; } return false; };
  const waterClass = (x, z) => (ring(x, z, SHORE) ? 'shore' : (ring(x, z, NEAR * 0.5) || ring(x, z, NEAR)) ? 'near' : 'far');
  const ruleFor = (lu, wc) => { for (const r of RULES) if ((r.land_use === '*' || r.land_use === lu) && (r.water === '*' || r.water === wc)) return r; throw new FloraError('florakit: no rule for ' + lu + '/' + wc + ' in ' + region); };
  const kerb = (x, z) => { for (const [dx, dz] of [[K, 0], [-K, 0], [0, K], [0, -K]]) if (fn.isRoad(x + dx, z + dz)) return [dx / K, dz / K]; return null; };
  function placeChunk(ci, cj) {
    const items = [], n = Math.max(1, Math.round(chunkM / S)), step = chunkM / n;
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
      const rnd = flRng(flHash(ci * n + i, cj * n + j, seed, 7919));
      const x = ci * chunkM + (i + rnd()) * step, z = cj * chunkM + (j + rnd()) * step;
      if (!fn.isGround(x, z) || fn.isRoad(x, z)) continue;
      if (fn.footprint) { counts.footChecked++; if (fn.footprint(x, z)) { counts.footSkipped++; continue; } }   // ENV w15: nothing stands inside a page building
      const lu = fn.landUse(x, z);
      if (!LU.includes(lu)) throw new FloraError('florakit: landUse returned ' + JSON.stringify(lu) + ', not a ' + region + ' land use');
      const y = fn.groundY(x, z), kd = kerb(x, z), u = rnd(), v = rnd(), w = rnd(), ry = rnd() * Math.PI * 2;
      if (kd) {   // a kerb sample: AUTHORED street furniture, facing the street
        const dr = flNeed(DRULES, lu, 'region.details');
        if (u >= dr.p_kerb) continue;
        const did = flPick(dr.mix, v), d = flNeed(DET, did, 'details'), rot = Math.atan2(-kd[0], -kd[1]);
        const cs = Math.cos(rot), sn = Math.sin(rot), bx = x - kd[0] * (d.setback_m - K * 0.25), bz = z - kd[1] * (d.setback_m - K * 0.25);
        for (const b of d.boxes) items.push({ f: 'detail', sp: did, x: bx + b[0] * cs + b[2] * sn, y: y + b[1], z: bz - b[0] * sn + b[2] * cs, sx: b[3], sy: b[4], sz: b[5], ry: rot, col: b[6] });
        continue;
      }
      const wc = waterClass(x, z), k = fn.landClass(x, z);   // RECORDED land cover class, or null (no class: AUTHORED rules)
      const src = k === null ? 'A' : 'R', rule = k === null ? ruleFor(lu, wc) : lcRule(k);
      if (src === 'A') counts.authoredSamples++; else counts.recordedSamples++;
      if (rule === null || u >= rule.per_ha * step * step / 10000) continue;
      const sid = flPick(rule.mix, v), sp = flNeed(SP, sid, 'species'), hr = sp.height_m, cr = sp.crown_m;
      const h = hr[0] + (hr[1] - hr[0]) * w, c = cr[0] + (cr[1] - cr[0]) * rnd();
      items.push({ f: sp.family, sp: sid, x, y, z, sx: c, sy: h, sz: c, ry, col: sp.colour, src });
      if (sp.moss_near_water && MOSS.on.includes(sid) && MOSS.water.includes(wc)) items.push({ f: 'moss', sp: 'spanish_moss', x, y, z, sx: c, sy: h, sz: c, ry, col: MOSS.colour, src });
    }
    return items;
  }
  const counts = { recordedSamples: 0, authoredSamples: 0, footChecked: 0, footSkipped: 0, footDeferred: 0 };
  const chunks = new Map(); let queue = [], pc = null, last = null, dirty = false, overview = false, enabled = true, drawn = [], species = {}, lcDrawn = { recorded: 0, authored: 0 };
  const M = new THREE.Matrix4(), V = new THREE.Vector3(), Q = new THREE.Quaternion(), SC = new THREE.Vector3(), UP = new THREE.Vector3(0, 1, 0);
  function refill(px, pz) {
    const byF = {}; for (const f in meshes) byF[f] = [];
    for (const items of chunks.values()) for (const it of items) { const d2 = (it.x - px) ** 2 + (it.z - pz) ** 2, lod = FAM[it.f].lod_m; if (d2 <= lod * lod) byF[it.f].push([d2, it]); }
    drawn = []; species = {}; lcDrawn = { recorded: 0, authored: 0 };
    for (const [f, m] of Object.entries(meshes)) {
      const list = byF[f].sort((a, b) => a[0] - b[0]).slice(0, FAM[f].cap);
      list.forEach(([, it], i) => { M.compose(V.set(it.x, it.y, it.z), Q.setFromAxisAngle(UP, it.ry), SC.set(it.sx, it.sy, it.sz)); m.setMatrixAt(i, M); m.setColorAt(i, C.set(it.col)); drawn.push(it); species[it.sp] = (species[it.sp] || 0) + 1; if (it.src === 'R') lcDrawn.recorded++; else if (it.src === 'A') lcDrawn.authored++; });
      m.count = list.length; m.instanceMatrix.needsUpdate = true; if (m.instanceColor) m.instanceColor.needsUpdate = true;
      if (list.length) m.computeBoundingSphere();
      m.visible = enabled && !overview && list.length > 0;
    }
    last = [px, pz]; dirty = false;
  }
  function update(p) {
    if (!enabled) return;
    const x = flNeed(p, 'x', 'update'), z = flNeed(p, 'z', 'update');
    const ci = Math.floor(x / chunkM), cj = Math.floor(z / chunkM), key = ci + ',' + cj;
    if (key !== pc) {
      pc = key; const want = new Set(), q = [];
      for (let a = -RC; a <= RC; a++) for (let b = -RC; b <= RC; b++) { const k = (ci + a) + ',' + (cj + b); want.add(k); if (!chunks.has(k)) q.push([a * a + b * b, ci + a, cj + b]); }
      for (const k of [...chunks.keys()]) if (!want.has(k)) { chunks.delete(k); dirty = true; }
      queue = q.sort((s, t) => s[0] - t[0]).map((e) => [e[1], e[2]]);
    }
    for (let i = 0; i < PER_TICK && queue.length; i++) {
      const [a, b] = queue.shift();
      if (fn.chunkReady && !fn.chunkReady(a, b)) { queue.push([a, b]); counts.footDeferred++; break; }   // ENV w15: the page's buildings are not built there yet - back of the queue, next tick
      chunks.set(a + ',' + b, placeChunk(a, b)); dirty = true;
    }
    if (dirty || !last || Math.hypot(x - last[0], z - last[1]) > REFILL) refill(x, z);
  }
  function setOverview(on) { overview = !!on; for (const m of Object.values(meshes)) m.visible = enabled && !overview && m.count > 0; }
  function setEnabled(on) { enabled = !!on; setOverview(overview); }   // eval A/B: off = every flora mesh hidden, no streaming
  function stats() {
    const families = {}; let tris = 0, calls = 0;
    for (const [f, m] of Object.entries(meshes)) { const n = m.visible ? m.count : 0; families[f] = n; tris += n * FAM[f].tris; if (n) calls++; }
    const pl = lcDrawn.recorded + lcDrawn.authored;
    return { drawCalls: calls, families, species: overview || !enabled ? {} : { ...species }, tris, chunks: chunks.size, queue: queue.length, region, overview, enabled,
      landcover: { plantsRecorded: lcDrawn.recorded, plantsAuthored: lcDrawn.authored, shareRecorded: pl ? +(lcDrawn.recorded / pl).toFixed(3) : 0,
        recordedSamples: counts.recordedSamples, authoredSamples: counts.authoredSamples },
      footprint: fn.footprint || fn.chunkReady ? { adapter: !!fn.footprint, ready: !!fn.chunkReady, checked: counts.footChecked, skipped: counts.footSkipped, deferred: counts.footDeferred } : null };
  }
  function reset() { chunks.clear(); queue = []; pc = null; last = null; for (const k in counts) counts[k] = 0; }   // re-place (e.g. when the RECORDED land cover arrives)
  function near(x, z, r) { return drawn.filter((it) => (it.x - x) ** 2 + (it.z - z) ** 2 <= r * r); }
  function dispose() { for (const m of Object.values(meshes)) { scene.remove(m); m.geometry.dispose(); m.dispose(); } for (const mt of Object.values(mats)) mt.dispose(); chunks.clear(); }
  return { update, setOverview, setEnabled, reset, stats, placeChunk, near, dispose, meshes, materials: mats, waterClass, budgets: JSON.parse(JSON.stringify(B)) };
}
globalThis.TCFLORA = { createFlora, floraGeometry, flHash, flRng, flPick, FloraError };
"""

FLORA_EXPORT = '\nexport { createFlora, floraGeometry, flHash, flRng, flPick, FloraError, createWildsFlora };\n'   # WORLD w16: + createWildsFlora
FLORA_JS_INLINE = FLORA_CORE

# BEGIN WORLD w16 (WORLD·Worlds & Locales): ground flora for the wilds worlds (web/build_wilds.py WORLD w16 block).
# The wilds already draw their own trees, rocks and billboards and have little draw-call headroom (eval_wilds forest
# dense: 11 calls against a ceiling of 12), so the wilds take florakit's understory FAMILIES (registry wilds.families:
# shrub, reed) as PARTS of ONE InstancedMesh - a per-instance part index and a vertex-shader collapse (the page's wave-4
# billboard pattern) - instead of one InstancedMesh per family: one draw call for all ground flora, near the eye only
# (wilds.radius_m), hidden in the overview. Every part is drawn (collapsed) for every instance, so the triangle worst
# case is cap x sum(part tris) (flora/build.py holds it to wilds.tris_max).
FLORA_WILDS_CORE = r"""/* ------------------------------------------------- TCFLORA wilds ground flora (WORLD w16) ---
   ONE InstancedMesh for every ground plant of a wilds world: florakit's shrub / reed shapes are parts of one geometry,
   each instance draws only its own part (flPart vs flKind). AUTHORED placement by biome rule - not a survey. */
function createWildsFlora(scene, o) {
  const THREE = flNeed(o, 'THREE', 'createWildsFlora'), data = flNeed(o, 'data', 'createWildsFlora');
  const biome = flNeed(o, 'biome', 'createWildsFlora'), seed = flNeed(o, 'seed', 'createWildsFlora');
  const fn = {};
  for (const k of ['height', 'slope', 'blocked']) { fn[k] = flNeed(o, k, 'createWildsFlora'); if (typeof fn[k] !== 'function') throw new FloraError('florakit createWildsFlora: ' + k + ' must be a function'); }
  const waterLevel = flNeed(o, 'waterLevel', 'createWildsFlora'), snowLine = flNeed(o, 'snowLine', 'createWildsFlora'), lim = flNeed(o, 'lim', 'createWildsFlora');
  const WL = flNeed(data, 'wilds', 'data'), FAM = flNeed(data, 'families', 'data');
  const PARTS = flNeed(WL, 'families', 'wilds'), SPEC = flNeed(WL, 'species', 'wilds'), RULE = flNeed(flNeed(WL, 'biomes', 'wilds'), biome, 'wilds.biomes');
  const CELL = flNeed(WL, 'cell_m', 'wilds'), RAD = flNeed(WL, 'radius_m', 'wilds'), CAP = flNeed(WL, 'cap', 'wilds');
  const SLOPE = flNeed(WL, 'max_slope', 'wilds'), SNOW = flNeed(WL, 'snow_margin_m', 'wilds'), CLEAR = flNeed(WL, 'trail_clear_m', 'wilds');
  const wet = flNeed(RULE, 'wet', 'wilds.biomes.' + biome);
  /* the merged geometry: part i = florakit's shape for PARTS[i]; flPart tags its vertices */
  const P = [], C = [], N = [], T = [];
  PARTS.forEach((fid, i) => {
    const g = floraGeometry(THREE, flNeed(flNeed(FAM, fid, 'families'), 'shape', 'families.' + fid));
    const n = g.attributes.position.count;
    P.push(...g.attributes.position.array); C.push(...g.attributes.color.array); N.push(...g.attributes.normal.array);
    for (let k = 0; k < n; k++) T.push(i);
    g.dispose();
  });
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); geo.setAttribute('color', new THREE.Float32BufferAttribute(C, 3));
  geo.setAttribute('normal', new THREE.Float32BufferAttribute(N, 3)); geo.setAttribute('flPart', new THREE.Float32BufferAttribute(T, 1));
  const kind = new THREE.InstancedBufferAttribute(new Float32Array(CAP), 1);
  kind.setUsage(THREE.DynamicDrawUsage); geo.setAttribute('flKind', kind);
  const mat = new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide });
  mat.onBeforeCompile = (sh) => {
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nattribute float flPart;\nattribute float flKind;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\ntransformed *= step(abs(flPart - flKind), 0.5);');
  };
  const mesh = new THREE.InstancedMesh(geo, mat, CAP);
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  mesh.setColorAt(0, new THREE.Color('#ffffff')); mesh.count = 0; mesh.frustumCulled = false; mesh.name = 'flora:wilds'; mesh.userData.flora = 'wilds';
  scene.add(mesh);
  const triPer = geo.attributes.position.count / 3;
  const p = (r) => r.per_ha * CELL * CELL / 10000;
  /* pure: the plants within RAD of (x, z), nearest first, at most CAP */
  function place(x0, z0) {
    const out = [];
    const c0 = Math.floor((x0 - RAD) / CELL), c1 = Math.floor((x0 + RAD) / CELL), r0 = Math.floor((z0 - RAD) / CELL), r1 = Math.floor((z0 + RAD) / CELL);
    for (let ci = c0; ci <= c1; ci++) for (let ri = r0; ri <= r1; ri++) {
      const rnd = flRng(flHash(ci, ri, seed, 4241));
      const x = (ci + rnd()) * CELL, z = (ri + rnd()) * CELL, dx = x - x0, dz = z - z0, d2 = dx * dx + dz * dz;
      if (d2 > RAD * RAD || Math.abs(x) > lim || Math.abs(z) > lim) continue;
      const u = rnd(), v = rnd(), w = rnd(), ry = rnd() * Math.PI * 2;
      const h = fn.height(x, z);
      if (h < waterLevel || h > snowLine - SNOW) continue;
      const rule = wet !== null && h < waterLevel + wet.band_m ? wet : RULE;
      if (u >= p(rule)) continue;
      if (fn.slope(x, z) > SLOPE || fn.blocked(x, z, CLEAR)) continue;
      const sp = flPick(rule.mix, v), s = flNeed(SPEC, sp, 'wilds.species');
      const crown = s.crown_m[0] + (s.crown_m[1] - s.crown_m[0]) * w, ht = s.height_m[0] + (s.height_m[1] - s.height_m[0]) * (1 - w * 0.5);
      out.push({ d2, sp, part: PARTS.indexOf(s.family), x, y: h - 0.05, z, crown, ht, ry, tint: 0.88 + 0.24 * v });
    }
    out.sort((a, b) => a.d2 - b.d2);
    if (out.length > CAP) out.length = CAP;
    return out;
  }
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), sc = new THREE.Vector3(), ps = new THREE.Vector3(), col = new THREE.Color();
  let drawn = [], species = {}, minR = Infinity, maxR = 0;
  function refill(eye) {
    drawn = place(eye.x, eye.z); species = {}; minR = Infinity; maxR = 0;
    drawn.forEach((it, n) => {
      e.set(0, it.ry, 0); q.setFromEuler(e); sc.set(it.crown, it.ht, it.crown); ps.set(it.x, it.y, it.z);
      m4.compose(ps, q, sc); mesh.setMatrixAt(n, m4); kind.setX(n, it.part);
      col.set(SPEC[it.sp].colour).multiplyScalar(it.tint); mesh.setColorAt(n, col);
      species[it.sp] = (species[it.sp] || 0) + 1;
      const r = Math.sqrt(it.d2); if (r < minR) minR = r; if (r > maxR) maxR = r;
    });
    mesh.count = drawn.length; mesh.instanceMatrix.needsUpdate = true; kind.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    return drawn.length;
  }
  function setVisible(on) { mesh.visible = !!on; }
  function stats() {
    const n = mesh.visible ? mesh.count : 0;
    return { biome, meshes: 1, instanced: mesh.isInstancedMesh, instances: n, cap: CAP, radius: RAD, maxR: n ? +maxR.toFixed(1) : 0,
      tris: n * triPer, triPerInstance: triPer, parts: PARTS.slice(), species: n ? { ...species } : {} };
  }
  function dispose() { scene.remove(mesh); geo.dispose(); mat.dispose(); }
  return { refill, place, setVisible, stats, dispose, mesh };
}
globalThis.TCFLORA.createWildsFlora = createWildsFlora;
"""
WILDS_FLORA_JS_INLINE = FLORA_CORE + FLORA_WILDS_CORE


def wilds_flora_data():
    """WORLD w16: what the wilds page embeds - the wilds section, the families it draws as parts, the honesty."""
    reg = flora_data()
    if 'wilds' not in reg:
        raise FloraKitError('flora/registry/flora.json has no wilds section: run python3 flora/build.py')
    wl = reg['wilds']
    return {'schema': reg['schema'], 'provenance': reg['provenance'], 'source_stamp': reg['source_stamp'], 'wilds': wl,
            'families': {f: reg['families'][f] for f in wl['families']}}


def wilds_flora_mount_js(*, seed, biome, height, slope, blocked, water_level, snow_line, lim):
    """JS text for the wilds page: the kit, the embedded data and a createWildsFlora call (JS expressions in)."""
    data = json.dumps(wilds_flora_data(), ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return (WILDS_FLORA_JS_INLINE + f'\n/* WORLD w16 wilds ground-flora mount */\nconst WILDS_FLORA_DATA = {data};\n'
            + f'function mountWildsFlora() {{ return createWildsFlora(scene, {{ THREE, data: WILDS_FLORA_DATA, biome: {biome}, seed: {seed}, '
            + f'height: {height}, slope: {slope}, blocked: {blocked}, waterLevel: {water_level}, snowLine: {snow_line}, lim: {lim} }}); }}\n')
# END WORLD w16
FLORA_JS = FLORA_CORE + FLORA_WILDS_CORE + FLORA_EXPORT   # WORLD w16: the module carries the wilds kit too


def flora_mount_js(region, *, seed, chunk_m, is_ground, is_road, is_water, land_use, eye, overview, ground_y=None, land_class='() => null',
                   footprint=None, chunk_ready=None):
    """JS text for a page's module script: embeds the region's data, creates the kit and ticks it on its own
    animation frame (hidden, 0 draw calls, while `overview` is true). The ground hook uses a terrain sampler
    globalThis.TCTERRAIN.heightAt(x, z) when a page mounts one, else the flat AUTHORED ground y = 0; a page with its own
    ground function (e.g. the parish page's ELEV w14 elevY) passes it as ground_y (JS expression).
    ENV w15: footprint / chunk_ready (JS expressions) wire the optional footprint adapters; when neither is given the
    options end in the FLORA_ADAPTERS_MARK comment, which a page's ENV block replaces exactly once (so a builder block
    owned by another agent never has to change its call)."""
    data = json.dumps(flora_data(region), ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return (FLORA_JS_INLINE
            + f'\n/* VEG w14 flora mount ({region}) */\nconst FLORA_DATA = {data};\n'
            + 'const floraGroundY = (x, z) => (globalThis.TCTERRAIN && typeof globalThis.TCTERRAIN.heightAt === "function") ? globalThis.TCTERRAIN.heightAt(x, z) : 0;\n'
            + f'const flora = createFlora(scene, {{ THREE, data: FLORA_DATA, region: {json.dumps(region)}, seed: {seed}, chunkM: {chunk_m},\n'
            + f'  isGround: {is_ground}, isRoad: {is_road}, isWater: {is_water}, landUse: {land_use}, groundY: {ground_y or "floraGroundY"}, landClass: {land_class}{_adapters(footprint, chunk_ready)} }});\n'
            + f'(function floraTick() {{ const over = {overview}; flora.setOverview(over); if (!over) flora.update({eye}); requestAnimationFrame(floraTick); }})();\n'
            + 'window.__flora = flora;\n')



FLORA_ADAPTERS_MARK = ' /*FLORA_ADAPTERS*/'   # ENV w15: the hook a page block replaces with ', footprint: f, chunkReady: g'


def _adapters(footprint, chunk_ready):
    """ENV w15: both adapters or neither - a footprint test without the readiness gate would run against missing buildings."""
    if (footprint is None) != (chunk_ready is None):
        raise FloraKitError('flora_mount_js: footprint and chunk_ready go together (a footprint test needs the chunkReady gate)')
    return FLORA_ADAPTERS_MARK if footprint is None else f', footprint: {footprint}, chunkReady: {chunk_ready}'


if __name__ == '__main__':
    if '--emit' in sys.argv:
        sys.stdout.write(FLORA_JS)
    else:
        print(__doc__)
