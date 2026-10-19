#!/usr/bin/env python3
"""Facade kit: AUTHORED exterior details (cornices, parapets, galleries, shutters, awnings, brackets, trims,
storefront glazing, stoops, downpipes, rooftop units) and generic PLAY business signs for the open worlds.

    from facadekit import FACADE_JS, FACADE_JS_INLINE, facade_data, facade_mount_js

FACADE_JS is ES module text (export list at the end; also sets globalThis.TCFACADE); FACADE_JS_INLINE is the same
code without the export line, for pasting into a page's module script where THREE is in scope.
facade_data() returns facades/registry/facades.json and fails by name when it is missing or stale.

Draw calls: EVERY detail part and every sign board is an instance of ONE unit box in ONE InstancedMesh with ONE
material, so the kit costs exactly one draw call whatever it shows. Sign faces come from one canvas atlas texture
(cell 0 is plain white, so a detail part's colour is its instance colour); only the box's +z face of a sign board
samples its atlas cell. Parts are generated for the buildings nearest the eye first, up to a box budget, and the
mesh is hidden in the overview. The box drops its bottom face (never seen): 10 triangles per part.

Colours go through ONE adapter (facadeColour): the PATTERN pack's module when a page supplies it via
setColourAdapter(fn), else this pack's AUTHORED flat colours. Signs are play on AUTHORED economy game lots.

    python3 web/facadekit.py --emit     prints FACADE_JS (web/test_facadekit.mjs imports it)
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REG_PATH = ROOT / 'facades' / 'registry' / 'facades.json'


class FacadeKitError(Exception):
    pass


def facade_data():
    if not REG_PATH.exists():
        raise FacadeKitError('facades/registry/facades.json missing: run python3 facades/build.py')
    r = subprocess.run([sys.executable, str(ROOT / 'facades' / 'build.py'), '--check'], capture_output=True, text=True)
    if r.returncode != 0:
        raise FacadeKitError('facades/registry/facades.json is stale: run python3 facades/build.py')
    return json.loads(REG_PATH.read_text())


FACADE_CORE = r"""/* ------------------------------------------------------ TCFACADE kit ---
   AUTHORED facade recipes (generic building types, no replica) and PLAY signs on AUTHORED game lots
   (never a real business, name or address). One InstancedMesh = one draw call. */
class FacadeError extends Error {}
function facNeed(o, k, where) {
  if (o === null || typeof o !== 'object' || !(k in o)) throw new FacadeError('facades: ' + where + ': missing "' + k + '"');
  return o[k];
}
const FAC_USES = ['residential', 'commercial', 'industrial'];
/* ---- the ONE colour adapter: PATTERN's module when a page supplies it, else AUTHORED flat colours ---- */
let facAdapter = null;
function setColourAdapter(fn) { if (fn !== null && typeof fn !== 'function') throw new FacadeError('facades: adapter must be a function or null'); facAdapter = fn; }
function facadeColour(data, category, pattern) {
  const cats = facNeed(data, 'colour_categories', 'data');
  const c = facNeed(cats, category, 'colour_categories');
  if (facAdapter) { const hex = facAdapter(category, pattern); if (typeof hex === 'string' && /^#[0-9A-Fa-f]{6}$/.test(hex)) return hex; }
  return facNeed(c, 'hex', category);
}
/* PATTERN_CONTRACT v1: an adapter from this pack's categories to PatternKit colour ids (data.pattern_map; null = keep
   the AUTHORED flat colour). PatternKit.colour throws on an unknown id - no silent fallback there. */
function facPatternAdapter(data, PK) {
  const map = facNeed(data, 'pattern_map', 'data');
  return (cat) => { const id = facNeed(map, cat, 'pattern_map'); return id === null ? null : PK.colour(id); };
}
/* ---- style selection: first AUTHORED rule that matches ---- */
function facStyleFor(data, world, family, useF, h) {
  const use = family === 'hall' ? 'civic' : FAC_USES[Math.floor(useF)];
  if (use === undefined) throw new FacadeError('facades: unknown kit land use ' + useF);
  const variant = (useF - Math.floor(useF)) > 0.2 ? 1 : 0;
  for (const r of facNeed(data, 'rules', 'data')) {
    if ((r.world === world || r.world === '*') && r.family === family && r.use === use && (r.variant === '*' || r.variant === variant) && h <= r.h_max) return r.style;
  }
  return null;   // no rule: the building gets no details (counted by the caller)
}
/* ---- a style recipe -> boxes in the building's local frame (front face at +z = d/2, ground y = 0) ----
   box = [lx, ly, lz, sx, sy, sz, category, pattern, cell, yawOff]; h_m < 0 means "up to the eave minus |h_m|" */
function facBoxes(data, styleId, w, h, d) {
  const st = facNeed(facNeed(data, 'styles', 'data'), styleId, 'styles'), out = [], fz = d / 2;
  for (const c of facNeed(st, 'components', styleId)) {
    const y0 = (c.y_ref === 'eave' ? h : 0) + c.y_m;
    const hh = c.h_m < 0 ? h + c.h_m - y0 : c.h_m;
    if (hh <= 0.02) continue;
    if (c.y_ref === 'ground' && y0 + hh > h + 0.01 && c.layout !== 'roof') continue;   // taller than this building's wall
    const cz = c.layout === 'roof' ? fz - c.out_m : fz + c.out_m + c.depth_m / 2, cy = y0 + hh / 2;
    const P = (x, sw) => out.push([x, cy, cz, sw, hh, c.depth_m, c.colour_category, c.pattern_id, 0, 0]);
    if (c.layout === 'band') P(0, w + (c.out_m > 0.2 ? 0 : 2 * Math.min(c.depth_m, 0.3)));
    else if (c.layout === 'single' || c.layout === 'roof') { if (c.width_m < w) P(c.x_m, c.width_m); }
    else if (c.layout === 'repeat') {
      const k = Math.max(2, Math.floor(w / c.spacing_m) + 1), a = -w / 2 + c.width_m / 2, b = w / 2 - c.width_m / 2;
      for (let i = 0; i < k; i++) P(a + (b - a) * i / (k - 1), c.width_m);
    } else if (c.layout === 'pair') {
      const k = Math.max(1, Math.floor(w / c.spacing_m));
      for (let i = 0; i < k; i++) { const x = -w / 2 + (i + 0.5) * w / k; if (k > 1 && Math.abs(x) < 0.8) continue; P(x - 0.6 - c.width_m / 2, c.width_m); P(x + 0.6 + c.width_m / 2, c.width_m); }
    } else throw new FacadeError('facades: unknown layout ' + c.layout);
  }
  return out;
}
/* ---- a play sign on a shop at an economy lot: the shop shell, the midcentury storefront recipe, the board ---- */
const FAC_SHOP = { h: 4.6 };
function facShopBoxes(data, sign, cell) {
  const [lw, ld] = facNeed(sign, 'lot_size_m', sign.lot_id);
  const w = Math.min(Math.max(lw - 4, 6), 14), d = Math.min(Math.max(ld - 6, 6), 12), h = FAC_SHOP.h;
  const out = [[0, h / 2, 0, w, h, d, 'stone-pale', 'plain', 0, 0]];
  for (const b of facBoxes(data, 'midcentury-commercial', w, h, d)) out.push(b);
  const pl = facNeed(sign, 'placement', sign.lot_id), fz = d / 2;
  if (pl === 'fascia') out.push([0, 3.55, fz + 0.34, Math.min(w * 0.8, 7), 0.8, 0.12, null, 'plain', cell, 0]);   // proud of the fascia band
  else if (pl === 'window') out.push([-w / 4, 1.7, fz + 0.09, 2.2, 0.55, 0.03, null, 'plain', cell, 0]);
  else if (pl === 'blade') { out.push([w / 2 - 0.8, 3.9, fz + 0.75, 0.08, 0.08, 1.5, 'ironwork', 'plain', 0, 0]); out.push([w / 2 - 0.8, 3.35, fz + 1.05, 1.5, 0.75, 0.08, null, 'plain', cell, Math.PI / 2]); }
  else if (pl === 'monument') { out.push([0, 0.25, fz + 3.2, 2.8, 0.5, 0.6, 'stone-pale', 'plain', 0, 0]); out.push([0, 1.05, fz + 3.2, 2.6, 1.1, 0.3, null, 'plain', cell, 0]); }
  else throw new FacadeError('facades: unknown sign placement ' + pl);
  return out;
}
/* ---- sign atlas: canvas cells, cell 0 plain white; icons are simple generic pictograms ---- */
const FAC_ATLAS = { cols: 4, rows: 16, cw: 256, ch: 64 };
const FAC_ICON = {
  bolt: [[0.55, 0.1, 0.3, 0.55, 0.5, 0.55, 0.4, 0.9, 0.72, 0.4, 0.5, 0.4, 0.62, 0.1]], drop: [[0.5, 0.1, 0.75, 0.6, 0.5, 0.9, 0.25, 0.6, 0.5, 0.1]],
  saw: [[0.15, 0.7, 0.85, 0.3, 0.85, 0.55, 0.15, 0.85, 0.15, 0.7]], spark: [[0.5, 0.1, 0.5, 0.9], [0.1, 0.5, 0.9, 0.5], [0.22, 0.22, 0.78, 0.78], [0.78, 0.22, 0.22, 0.78]],
  fan: [[0.5, 0.5, 0.5, 0.1, 0.7, 0.3, 0.5, 0.5, 0.9, 0.5, 0.7, 0.7, 0.5, 0.5, 0.5, 0.9, 0.3, 0.7, 0.5, 0.5, 0.1, 0.5, 0.3, 0.3, 0.5, 0.5]],
  leaf: [[0.2, 0.85, 0.3, 0.35, 0.8, 0.15, 0.7, 0.65, 0.2, 0.85], [0.2, 0.85, 0.6, 0.4]], brush: [[0.3, 0.9, 0.7, 0.9, 0.7, 0.55, 0.3, 0.55, 0.3, 0.9], [0.5, 0.55, 0.5, 0.1]],
  gear: [[0.5, 0.1, 0.6, 0.3, 0.85, 0.3, 0.72, 0.5, 0.85, 0.7, 0.6, 0.7, 0.5, 0.9, 0.4, 0.7, 0.15, 0.7, 0.28, 0.5, 0.15, 0.3, 0.4, 0.3, 0.5, 0.1]],
  wrench: [[0.2, 0.85, 0.6, 0.45], [0.6, 0.45, 0.55, 0.2, 0.7, 0.1, 0.85, 0.25, 0.7, 0.3, 0.8, 0.45, 0.6, 0.45]], pane: [[0.2, 0.15, 0.8, 0.15, 0.8, 0.85, 0.2, 0.85, 0.2, 0.15], [0.5, 0.15, 0.5, 0.85], [0.2, 0.5, 0.8, 0.5]],
  loaf: [[0.15, 0.7, 0.15, 0.45, 0.5, 0.3, 0.85, 0.45, 0.85, 0.7, 0.15, 0.7], [0.35, 0.4, 0.4, 0.6], [0.55, 0.38, 0.6, 0.6]],
  anchor: [[0.5, 0.15, 0.5, 0.85], [0.3, 0.3, 0.7, 0.3], [0.15, 0.6, 0.3, 0.85, 0.7, 0.85, 0.85, 0.6]], hammer: [[0.3, 0.2, 0.8, 0.2, 0.8, 0.35, 0.3, 0.35, 0.3, 0.2], [0.55, 0.35, 0.55, 0.9]],
  basket: [[0.15, 0.4, 0.85, 0.4, 0.75, 0.85, 0.25, 0.85, 0.15, 0.4], [0.3, 0.4, 0.5, 0.12, 0.7, 0.4]],
};
function facDrawSign(ctx, cell, sign) {
  const { cols, cw, ch } = FAC_ATLAS, x0 = (cell % cols) * cw, y0 = Math.floor(cell / cols) * ch;
  const [bg, fg] = facNeed(sign, 'palette', sign.lot_id), icon = FAC_ICON[facNeed(sign, 'icon', sign.lot_id)];
  if (!icon) throw new FacadeError('facades: no pictogram for icon ' + sign.icon);
  ctx.fillStyle = bg; ctx.fillRect(x0, y0, cw, ch);
  ctx.strokeStyle = fg; ctx.lineWidth = 3; ctx.strokeRect(x0 + 3, y0 + 3, cw - 6, ch - 6);
  ctx.lineWidth = 3; ctx.lineJoin = 'round';
  for (const pl of icon) { ctx.beginPath(); for (let i = 0; i < pl.length; i += 2) { const px = x0 + 8 + pl[i] * 44, py = y0 + 10 + pl[i + 1] * 44; if (i) ctx.lineTo(px, py); else ctx.moveTo(px, py); } ctx.stroke(); }
  ctx.fillStyle = fg; ctx.textBaseline = 'middle';
  let fs = 26; ctx.font = 'bold ' + fs + 'px sans-serif';
  while (fs > 12 && ctx.measureText(sign.name).width > cw - 68) { fs -= 1; ctx.font = 'bold ' + fs + 'px sans-serif'; }
  ctx.fillText(sign.name, x0 + 60, y0 + ch / 2 + 1);
}
/* ---- the kit ---- */
function createFacades(scene, opts) {
  const THREE = facNeed(opts, 'THREE', 'opts'), data = facNeed(opts, 'data', 'opts'), world = facNeed(opts, 'world', 'opts');
  if (!['parishes', 'bay', 'campus'].includes(world)) throw new FacadeError('facades: unknown world ' + world);
  const maxBoxes = facNeed(opts, 'maxBoxes', 'opts'), radius = facNeed(opts, 'radius', 'opts');
  const makeCanvas = facNeed(opts, 'makeCanvas', 'opts');   // () => canvas | null (null: signs render as blank boards)
  /* sink true: detail parts are written as triangles into a HOST merged vertex-coloured buffer (writeInto) - 0 draw
     calls of their own; only the textured sign boards within signNear m of the eye use the kit's InstancedMesh */
  const sink = facNeed(opts, 'sink', 'opts'), signNear = facNeed(opts, 'signNear', 'opts');
  const box = new THREE.BoxGeometry(1, 1, 1).toNonIndexed();
  { /* drop the bottom and back faces (never seen): 12 -> 8 triangles */
    const p = box.attributes.position.array, n = box.attributes.normal.array, u = box.attributes.uv.array, P = [], N = [], U = [];
    for (let t = 0; t < p.length / 9; t++) if (n[t * 9 + 1] > -0.9 && n[t * 9 + 2] > -0.9) {   /* bottom and back (against the wall) */ P.push(...p.slice(t * 9, t * 9 + 9)); N.push(...n.slice(t * 9, t * 9 + 9)); U.push(...u.slice(t * 6, t * 6 + 6)); }
    box.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); box.setAttribute('normal', new THREE.Float32BufferAttribute(N, 3)); box.setAttribute('uv', new THREE.Float32BufferAttribute(U, 2));
  }
  const cellAttr = new THREE.InstancedBufferAttribute(new Float32Array(maxBoxes), 1);
  box.setAttribute('fcCell', cellAttr);
  const canvas = makeCanvas();
  let tex = null;
  if (canvas) {
    canvas.width = FAC_ATLAS.cols * FAC_ATLAS.cw; canvas.height = FAC_ATLAS.rows * FAC_ATLAS.ch;
    const ctx = canvas.getContext('2d'); ctx.fillStyle = '#FFFFFF'; ctx.fillRect(0, 0, FAC_ATLAS.cw, FAC_ATLAS.ch);
    tex = new THREE.CanvasTexture(canvas); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 4;
  }
  const mat = new THREE.MeshLambertMaterial({ color: 0xffffff, map: tex });
  mat.onBeforeCompile = (sh) => {
    sh.vertexShader = 'attribute float fcCell;\n' + sh.vertexShader.replace('#include <uv_vertex>', `#include <uv_vertex>
#ifdef USE_MAP
{ float sel = step(0.5, fcCell) * step(0.5, normal.z);
  vec2 org = vec2(mod(fcCell, ${FAC_ATLAS.cols}.0), floor(fcCell / ${FAC_ATLAS.cols}.0)) * sel;
  vec2 q = mix(vec2(0.5), uv, sel);
  vMapUv = vec2((org.x + q.x) / ${FAC_ATLAS.cols}.0, 1.0 - (org.y + 1.0 - q.y) / ${FAC_ATLAS.rows}.0); }
#endif`);
  };
  mat.customProgramCacheKey = () => 'tc-facade';
  const mesh = new THREE.InstancedMesh(box, mat, maxBoxes);
  mesh.name = 'tc-facades'; mesh.count = 0; mesh.frustumCulled = false; mesh.setColorAt(0, new THREE.Color(1, 1, 1));
  scene.add(mesh);
  let enabled = true;
  const signsBy = new Map();
  for (const s of facNeed(data, 'signs', 'data')) { if (!signsBy.has(s.parish)) signsBy.set(s.parish, []); signsBy.get(s.parish).push(s); }
  const cells = new Map(); let nextCell = 1;
  const colCache = new Map(), C = new THREE.Color();
  function colourOf(cat, pat) { const k = cat + '|' + pat; if (!colCache.has(k)) colCache.set(k, new THREE.Color(facadeColour(data, cat, pat))); return colCache.get(k); }
  function cellFor(sign) {
    if (cells.has(sign.lot_id)) return cells.get(sign.lot_id);
    if (nextCell >= FAC_ATLAS.cols * FAC_ATLAS.rows) return 0;   // atlas full: the board is drawn as a plain detail part
    const c = nextCell++; if (canvas) { facDrawSign(canvas.getContext('2d'), c, sign); tex.needsUpdate = true; }   // no canvas: a blank board
    cells.set(sign.lot_id, c); return c;
  }
  const M4 = new THREE.Matrix4(), Q = new THREE.Quaternion(), V = new THREE.Vector3(), S = new THREE.Vector3(), UP = new THREE.Vector3(0, 1, 0);
  let st = { buildings: 0, dressed: 0, unstyled: 0, parts: 0, signs: 0, dropped: 0, byStyle: {}, shops: [] };
  const BP = box.attributes.position.array, BN = box.attributes.normal.array, VPB = BP.length / 3;
  let parts = [], ni = 0;
  function partMatrix(bx, x, z, yaw) {
    const [lx, ly, lz, sx, sy, sz, , , , yo] = bx;
    V.set(lx, ly, lz).applyAxisAngle(UP, yaw); V.x += x; V.z += z;
    return M4.compose(V, Q.setFromAxisAngle(UP, yaw + yo), S.set(sx, sy, sz));
  }
  function put(n, bx, x, z, yaw) {
    parts.push([bx, x, z, yaw]);
    if (sink) return;
    mesh.setMatrixAt(n, partMatrix(bx, x, z, yaw)); mesh.setColorAt(n, bx[6] === null ? C.set(0xffffff) : colourOf(bx[6], bx[7])); cellAttr.array[n] = bx[8];
  }
  const P3 = new THREE.Vector3(), N3 = new THREE.Vector3();
  /* write every non-sign part as triangles into the host's vertex-coloured buffer from vertex `base`; returns vertices written */
  function writeInto(pos, nor, col, zeb, base, capV) {
    let v = base;
    if (!enabled) { st.sinkTris = 0; return 0; }
    for (const [bx, x, z, yaw] of parts) {
      if (bx[8] > 0) continue;
      if (v + VPB > capV) { st.dropped++; continue; }
      partMatrix(bx, x, z, yaw); Q.setFromAxisAngle(UP, yaw + bx[9]); const c = colourOf(bx[6], bx[7]);
      for (let i = 0; i < VPB; i++, v++) {
        P3.fromArray(BP, i * 3).applyMatrix4(M4); N3.fromArray(BN, i * 3).applyQuaternion(Q);
        pos[v * 3] = P3.x; pos[v * 3 + 1] = P3.y; pos[v * 3 + 2] = P3.z; nor[v * 3] = N3.x; nor[v * 3 + 1] = N3.y; nor[v * 3 + 2] = N3.z;
        col[v * 3] = c.r; col[v * 3 + 1] = c.g; col[v * 3 + 2] = c.b; if (zeb) zeb[v] = -100;
      }
    }
    st.sinkTris = (v - base) / 3;
    return v - base;
  }
  /* buildings: [x, z, w, h, d, family, yaw, colour, use]; shops: [{sign, x, z, yaw}] in the same world frame */
  function update(buildings, shops, eye) {
    const near = [];
    for (const b of buildings) { const dd = Math.hypot(b[0] - eye.x, b[1] - eye.z); if (dd < radius) near.push([dd, b]); }
    near.sort((a, b) => a[0] - b[0]);
    let n = 0; parts = []; st = { buildings: near.length, dressed: 0, unstyled: 0, parts: 0, signs: 0, dropped: 0, byStyle: {}, shops: [], sinkTris: 0, signBoards: 0 };
    for (const s of shops) {   // play signs first: they are few and they are what a player looks for
      if (Math.hypot(s.x - eye.x, s.z - eye.z) > radius * 2) continue;
      const bx = facShopBoxes(data, s.sign, cellFor(s.sign));
      if (n + bx.length > maxBoxes) { st.dropped++; continue; }
      for (const b of bx) put(n++, b, s.x, s.z, s.yaw);
      st.signs++; st.shops.push({ lot: s.sign.lot_id, name: s.sign.name, placement: s.sign.placement, x: s.x, z: s.z, yaw: s.yaw });
    }
    for (const [, b] of near) {
      const style = facStyleFor(data, world, b[5], b[8], b[3]);
      if (style === null) { st.unstyled++; continue; }
      const bx = facBoxes(data, style, b[2], b[3], b[4]);
      if (n + bx.length > maxBoxes) { st.dropped++; continue; }
      for (const q of bx) put(n++, q, b[0], b[1], b[6]);
      st.dressed++; st.byStyle[style] = (st.byStyle[style] || 0) + 1;
    }
    st.parts = n;
    if (sink) {   /* the kit's own mesh draws only the sign boards near the eye (0 instances -> 0 draw calls) */
      ni = 0;
      for (const [bx, x, z, yaw] of parts) if (bx[8] > 0 && Math.hypot(x - eye.x, z - eye.z) <= signNear) { mesh.setMatrixAt(ni, partMatrix(bx, x, z, yaw)); mesh.setColorAt(ni, C.set(0xffffff)); cellAttr.array[ni++] = bx[8]; }
      n = ni; st.signBoards = ni;
    }
    mesh.count = n; mesh.instanceMatrix.needsUpdate = true; if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true; cellAttr.needsUpdate = true;
    return st;
  }
  return {
    mesh, update, writeInto, drawCalls: () => (mesh.visible && mesh.count > 0 ? 1 : 0),
    setVisible(v) { mesh.visible = !!v && enabled; },
    setEnabled(v) { enabled = !!v; mesh.visible = mesh.visible && enabled; },   /* the eval's before/after switch */
    signsFor(parish) { return signsBy.has(parish) ? signsBy.get(parish) : []; },
    stats: () => ({ ...st, byStyle: { ...st.byStyle }, shops: st.shops.map((q) => ({ ...q })), visible: mesh.visible, enabled, count: mesh.count, trisPerPart: box.attributes.position.count / 3, atlasCells: nextCell - 1, world }),
    dispose() { scene.remove(mesh); box.dispose(); mat.dispose(); if (tex) tex.dispose(); },
  };
}
globalThis.TCFACADE = { createFacades, facPatternAdapter, facStyleFor, facBoxes, facShopBoxes, facadeColour, setColourAdapter, FAC_ATLAS };
"""
FACADE_EXPORTS = '\nexport { createFacades, facPatternAdapter, facStyleFor, facBoxes, facShopBoxes, facadeColour, setColourAdapter, FacadeError, FAC_ATLAS, FAC_ICON };\n'
FACADE_JS = FACADE_CORE + FACADE_EXPORTS
FACADE_JS_INLINE = FACADE_CORE


def facade_mount_js(world, data=None, host_js=''):
    """The kit + the registry for one world, as inline JS (for a page's module script where THREE is in scope),
    plus PATTERN's PatternKit (PATTERN_CONTRACT v1, only the colour families the map names, no recipes) unless the
    host script already holds one (host_js contains 'const PatternKit'). The page adds its own glue."""
    if world not in ('parishes', 'bay', 'campus'):
        raise FacadeKitError(f'facadekit: unknown world {world!r}')
    d = facade_data() if data is None else data
    blob = json.dumps(d, sort_keys=True, ensure_ascii=False).replace('</', '<\\/')
    pk = ''
    if 'const PatternKit' not in host_js:
        sys.path.insert(0, str(ROOT / 'web'))
        import patternkit  # noqa: E402
        pk = patternkit.inline_script([], d['pattern_families']) + '\n'
    return pk + FACADE_JS_INLINE + f'\nconst FAC_DATA = {blob};\nconst FAC_WORLD = {json.dumps(world)};\n'


def pattern_honesty_line():
    sys.path.insert(0, str(ROOT / 'web'))
    import patternkit  # noqa: E402
    return patternkit.honesty_line()


if __name__ == '__main__':
    if '--emit' in sys.argv:
        sys.stdout.write(FACADE_JS)
    else:
        print(__doc__)
