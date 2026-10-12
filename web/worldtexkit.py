#!/usr/bin/env python3
"""World texture kit (wave 17): SURFACE DETAIL BY DEVICE TIER for the walkable worlds.

    from worldtexkit import worldtex_js, recipe_surfaces

The parish page (and the Bay page, which is the parish builder re-targeted) and the wilds pages draw their ground,
streets, walls and terrain as flat or vertex colours. On a GPU that can afford it a page now multiplies world-space
detail textures over those colours - generated in the browser (patternkit recipes and the painters below), never
fetched. A page's builder declares its SURFACES (id, painter, metres covered) and its shader KINDS (the material
family, the fragment anchor the detail GLSL goes in front of, the GLSL); this kit writes the one block of page JS.

Tiers mirror the 3D page (web/build_3d.py DRESSING block):
    base   0 px     a software rasteriser (SwiftShader, llvmpipe), under 4 GB, or a GPU texture limit under 4096:
                    NOTHING changes - the shader patch is compiled in only while the textures are on
    high   1024 px  any other device
    ultra  2048 px  a desktop (no touch) with 8 GB, 8 cores and an 8192 px texture limit
?tex=base|high|ultra overrides it. Painted after the first frame, one texture per idle slot, mipmapped (trilinear)
and anisotropic; the materials switch to the patched shaders once, when the set is complete. A budget (MB of RGBA8
with mips) steps a texture from 2048 to 1024 and skips it past that. Every texture covers a FIXED number of metres
(a recipe: its registry tile_m x 4 repeats; a painter: its declared metres, drawn in one 512 px design space scaled
to the tier), so a pattern is the same size in the world at every tier and the extra texels buy sharpness only.
Page hooks: window.__worldTex() (state) and window.__worldTexDo(tier) (paint the whole set now, for a harness).
The page carries only the neutral marker WORLD-TEX.
"""
import json
import re

TIER_PX = {'base': 0, 'high': 1024, 'ultra': 2048}
REPS = 4
PAINTERS = ('grass', 'asphalt', 'rock')


class WorldTexError(Exception):
    pass


def recipe_surfaces(pairs):
    """[(surface id, patternkit recipe id)] -> surfaces covering registry tile_m x REPS metres (fails closed)."""
    import patternkit
    out = []
    for sid, rid in pairs:
        if rid not in patternkit.EXT['recipes']:
            raise WorldTexError(f'WORLD-TEX recipe {rid} is not in surfaces/registry/exterior.json')
        out.append({'id': sid, 'paint': 'recipe', 'recipe': rid, 'reps': REPS,
                    'world_m': round(patternkit.EXT['recipes'][rid]['tile_m'] * REPS, 4)})
    return out


def _glsl(src, ids):
    """TEX(id, q) -> the detail sample (a multiplier around 1) of surface id at world coordinates q, over its metres."""
    def sub(m):
        sid = m.group(1)
        if sid not in ids:
            raise WorldTexError(f'WORLD-TEX GLSL samples {sid}, which no surface declares')
        u = sid.replace('.', '_')
        return f'texture2D(uWt_{u}, ({m.group(2)}) / uWtM_{u}).r * 2.0'
    out = re.sub(r'TEX\(([\w.]+), ([\w.]+)\)', sub, src)
    if 'TEX(' in out:
        raise WorldTexError('WORLD-TEX GLSL has a TEX( call this kit cannot expand: ' + out[out.index('TEX('):][:60])
    return out


def worldtex_js(surfaces, budgets_mb, kinds):
    """The page JS block. surfaces: [{id, paint, world_m, (recipe, reps)}]; budgets_mb: {high, ultra};
    kinds: {kind: {'anchor': fragment text the GLSL goes in front of, 'glsl': GLSL with TEX(id, q), 'normal': GLSL}}."""
    ids = [s['id'] for s in surfaces]
    if len(set(ids)) != len(ids) or not ids:
        raise WorldTexError('WORLD-TEX surfaces must be a non-empty list of unique ids')
    for s in surfaces:
        for k in ('id', 'paint', 'world_m'):
            if k not in s:
                raise WorldTexError(f'WORLD-TEX surface {s.get("id")!r} has no {k}')
        if s['paint'] not in PAINTERS + ('recipe',):
            raise WorldTexError(f'WORLD-TEX surface {s["id"]} has no painter called {s["paint"]}')
        if not (s['world_m'] > 0):
            raise WorldTexError(f'WORLD-TEX surface {s["id"]} covers {s["world_m"]} m')
    if set(budgets_mb) != {'high', 'ultra'}:
        raise WorldTexError('WORLD-TEX budgets are high and ultra, in MB')
    K = {}
    for k, v in kinds.items():
        for f in ('anchor', 'glsl', 'normal'):
            if f not in v:
                raise WorldTexError(f'WORLD-TEX kind {k} has no {f}')
        K[k] = {'anchor': v['anchor'], 'glsl': _glsl(v['glsl'], ids), 'normal': v['normal']}
    recipes = sorted({s['recipe'] for s in surfaces if s['paint'] == 'recipe'})
    pk = ''
    if recipes:
        import patternkit
        src = patternkit.PK_JS
        if src.count('const PatternKit =') != 1:
            raise WorldTexError('WORLD-TEX expects patternkit to define `const PatternKit =` exactly once')
        # a private copy: the facade kit's PatternKit stays the page's only one (web/test_facadekit.mjs)
        pk = ('const WtPK = (() => {\n' + src.replace('const PatternKit =', 'const WtPatternKit =', 1)
              + '\n  WtPatternKit.load(' + patternkit.data_json(recipes, []) + ');\n  return WtPatternKit;\n})();\n')
    else:
        pk = ('const WtPK = { rng(seed) { let h = 2166136261 >>> 0; for (const ch of String(seed)) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619) >>> 0; }\n'
              '  let a = h; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; } };   // patternkit.rng\n')
    mb = {'base': 0, **budgets_mb}
    return (r"""/* WORLD-TEX BEGIN: surface detail by device tier. base = nothing changes; high 1024 px; ultra 2048 px; ?tex= overrides;
   painted after the first frame, one texture per idle slot; mipmapped, anisotropic, budgeted. Every texture covers a fixed
   number of metres, so a pattern is the same size in the world at every tier. */
""" + pk + 'const WT_SURF = ' + json.dumps(surfaces, separators=(',', ':')) + ';\n'
        + 'const WT_KINDS = ' + json.dumps(K, separators=(',', ':')) + ';\n'
        + 'const WT_PX = { base: 0, high: %d, ultra: %d };\n' % (TIER_PX['high'], TIER_PX['ultra'])
        + 'const WT_MB = { base: 0, high: %s, ultra: %s };\n' % (mb['high'], mb['ultra'])
        + _CORE)


_CORE = r"""const WT_D0 = 512;                                     // the design space every painter draws in, scaled to the tier's size
const wtMiB = (px) => px * px * 4 * (4 / 3) / 1048576;   // RGBA8 with its mip chain
// the budget plan: each texture takes the tier's size, steps 2048 -> 1024 while it would cross the budget, and is
// skipped (0) past that; base plans nothing
function wtPlan(tierPx, budgetMb, n) {
  const out = []; let mb = 0;
  for (let i = 0; i < n; i++) {
    let px = tierPx;
    while (px > WT_PX.high && mb + wtMiB(px) > budgetMb) px /= 2;
    if (!px || mb + wtMiB(px) > budgetMb) { out.push(0); continue; }
    mb += wtMiB(px); out.push(px);
  }
  return out;
}
function wtTierAuto() {
  let soft = false;
  try {
    const gl = renderer.getContext(), ext = gl.getExtension('WEBGL_debug_renderer_info');
    soft = /swiftshader|llvmpipe|softpipe|software/i.test(ext ? String(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL)) : '');
  } catch (e) { soft = false; }
  // a browser that does not say (deviceMemory is Chromium-only) is taken as the 4 GB / 4-core middle, as on the 3D page
  const maxTex = renderer.capabilities.maxTextureSize, mem = typeof navigator.deviceMemory === 'number' ? navigator.deviceMemory : 4,
    cores = typeof navigator.hardwareConcurrency === 'number' ? navigator.hardwareConcurrency : 4;
  const touch = typeof matchMedia === 'function' && matchMedia('(pointer: coarse)').matches;
  if (soft || mem < 4 || maxTex < 4096) return 'base';
  if (!touch && mem >= 8 && cores >= 8 && maxTex >= 8192) return 'ultra';
  return 'high';
}
const wtAsked = new URLSearchParams(location.search).get('tex');
const wtNeutral = (() => { const t = new THREE.DataTexture(new Uint8Array([128, 128, 128, 255]), 1, 1); t.needsUpdate = true; return t; })();
const WT = { tier: wtAsked !== null && Object.hasOwn(WT_PX, wtAsked) ? wtAsked : wtTierAuto(), on: false, mats: new Set(), tex: {}, px: {},
  plan: [], next: 0, sched: false, painted: 0, skipped: 0, mb: 0, ms: 0, err: null,
  u: { uWtAmt: { value: 0.7 } } };
for (const s of WT_SURF) { WT.u['uWt_' + s.id.replace('.', '_')] = { value: wtNeutral }; WT.u['uWtM_' + s.id.replace('.', '_')] = { value: s.world_m }; }
const wtAniso = () => Math.min(16, renderer.capabilities.getMaxAnisotropy());
// one RNG per surface (patternkit's seeded mulberry32), so a tier repaint draws the same pattern, only sharper
function wtWrap(g, S, fn) { for (const ox of [-S, 0, S]) for (const oy of [-S, 0, S]) { g.save(); g.translate(ox, oy); fn(); g.restore(); } }
function wtPaint(s, px) {
  const c = document.createElement('canvas'); c.width = c.height = px;
  const g = c.getContext('2d'); g.fillStyle = '#808080'; g.fillRect(0, 0, px, px);
  const R = WtPK.rng(s.id), k = px / WT_D0;
  if (s.paint === 'recipe') {
    const t = px / s.reps, tc = document.createElement('canvas'); tc.width = tc.height = t;
    WtPK.draw(tc.getContext('2d'), s.recipe, { base: '#808080' }, t);
    g.fillStyle = g.createPattern(tc, 'repeat'); g.fillRect(0, 0, px, px);
  } else {
    g.save(); g.scale(k, k);
    const D = WT_D0, dots = [];
    if (s.paint === 'grass') {
      for (let i = 0; i < 40; i++) dots.push(['blob', R() * D, R() * D, 8 + R() * 22, R() > .5 ? 'rgba(90,90,90,.18)' : 'rgba(170,170,170,.14)']);
      for (let i = 0; i < 5200; i++) { const a = -Math.PI / 2 + (R() - .5) * 1.1, l = 3 + R() * 8;
        dots.push(['blade', R() * D, R() * D, a, l, R() > .45 ? 'rgba(178,178,178,.55)' : 'rgba(70,70,70,.5)']); }
    } else if (s.paint === 'rock') {   // weathered stone: broad stains, lichen and grit, a few fractures
      for (let i = 0; i < 46; i++) dots.push(['blob', R() * D, R() * D, 10 + R() * 34, R() > .5 ? 'rgba(70,70,70,.2)' : 'rgba(180,180,180,.16)']);
      for (let i = 0; i < 7000; i++) dots.push(['dot', R() * D, R() * D, .6 + R() * 1.8, R() > .5 ? 'rgba(185,185,185,.45)' : 'rgba(55,55,55,.45)']);
      for (let i = 0; i < 12; i++) { const pts = [[R() * D, R() * D]]; for (let j = 0; j < 10; j++) { const [x, y] = pts[pts.length - 1]; pts.push([x + (R() - .5) * 30, y + (R() - .5) * 30]); }
        dots.push(['crack', pts]); }
    } else {   // asphalt: aggregate, a few sealed cracks, patch repairs
      for (let i = 0; i < 6; i++) dots.push(['patch', R() * D, R() * D, 30 + R() * 60, 20 + R() * 40, 'rgba(100,100,100,.25)']);
      for (let i = 0; i < 9000; i++) dots.push(['dot', R() * D, R() * D, .6 + R() * 1.6, R() > .5 ? 'rgba(190,190,190,.5)' : 'rgba(60,60,60,.5)']);
      for (let i = 0; i < 4; i++) { const pts = [[R() * D, R() * D]]; for (let j = 0; j < 14; j++) { const [x, y] = pts[pts.length - 1]; pts.push([x + (R() - .5) * 26, y + (R() - .3) * 20]); }
        dots.push(['crack', pts]); }
    }
    for (const d of dots) (d[0] === 'crack' || Math.min(d[1], d[2], D - d[1], D - d[2]) < 100 ? (fn) => wtWrap(g, D, fn) : (fn) => fn())(() => {
      if (d[0] === 'blob') { g.fillStyle = d[4]; g.beginPath(); g.arc(d[1], d[2], d[3], 0, 2 * Math.PI); g.fill(); }
      else if (d[0] === 'blade') { g.strokeStyle = d[5]; g.lineWidth = .9; g.beginPath(); g.moveTo(d[1], d[2]); g.lineTo(d[1] + Math.cos(d[3]) * d[4], d[2] + Math.sin(d[3]) * d[4]); g.stroke(); }
      else if (d[0] === 'patch') { g.fillStyle = d[5]; g.fillRect(d[1], d[2], d[3], d[4]); }
      else if (d[0] === 'dot') { g.fillStyle = d[4]; g.fillRect(d[1], d[2], d[3], d[3]); }
      else { g.strokeStyle = 'rgba(40,40,40,.6)'; g.lineWidth = 1.1; g.beginPath(); d[1].forEach(([x, y], j) => (j ? g.lineTo(x, y) : g.moveTo(x, y))); g.stroke(); }
    });
    g.restore();
  }
  // one octave of grain at the device's own texel size: the detail the extra resolution is for
  const fine = Math.round(px * px * 0.02);
  for (let i = 0; i < fine; i++) { const up = R() > .5;
    g.fillStyle = `rgba(${up ? '255,255,255' : '0,0,0'},${(R() * .05).toFixed(3)})`; g.fillRect(R() * px, R() * px, 1.5, 1.5); }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;   // detail is data (a multiplier around 1), not a colour: no sRGB decode
  t.generateMipmaps = true; t.minFilter = THREE.LinearMipmapLinearFilter; t.magFilter = THREE.LinearFilter; t.anisotropy = wtAniso();
  return t;
}
const WT_V = 'varying vec3 vWtP; varying vec3 vWtN; varying float vWtD;\n';
function wtPatch(sh, kind) {
  const K = WT_KINDS[kind];
  if (!K) { WT.err = 'WORLD-TEX: no shader kind ' + kind; return; }
  const F = sh.fragmentShader.replace(K.anchor, K.glsl + K.anchor);
  if (F === sh.fragmentShader) { WT.err = 'WORLD-TEX: no shader anchor for ' + kind; return; }
  Object.assign(sh.uniforms, WT.u);
  const U = Object.keys(WT.u).map((k) => 'uniform ' + (k.startsWith('uWt_') ? 'sampler2D ' : 'float ') + k + ';').join(' ') + '\n';
  sh.vertexShader = WT_V + sh.vertexShader.replace('#include <project_vertex>', `#include <project_vertex>
  { vec4 wtW = vec4(transformed, 1.0);
  #ifdef USE_INSTANCING
    wtW = instanceMatrix * wtW;
  #endif
    vWtP = (modelMatrix * wtW).xyz; vWtN = normalize(mat3(modelMatrix) * ${K.normal}); vWtD = -mvPosition.z; }`);
  sh.fragmentShader = WT_V + U + F;
}
function worldTexHook(m, kind) {
  const pc = m.onBeforeCompile, pk = m.customProgramCacheKey;
  m.onBeforeCompile = (sh, r) => { if (pc) pc.call(m, sh, r); if (WT.on) wtPatch(sh, kind); };
  m.customProgramCacheKey = () => (pk ? pk.call(m) : '') + (WT.on ? '|world-tex' : '');
  WT.mats.add(m);
  return m;
}
function wtSwitch(on) { if (WT.on === on) return; WT.on = on; for (const m of WT.mats) m.needsUpdate = true; }
function wtStep() {
  WT.sched = false;
  if (WT.next >= WT_SURF.length) return;
  if (!(renderer.info.render.frame > 0)) { wtKick(500); return; }   // nothing before the first frame
  const s = WT_SURF[WT.next], px = WT.plan[WT.next], key = 'uWt_' + s.id.replace('.', '_');
  WT.next++;
  if (!px) WT.skipped++;
  else { const t0 = performance.now(); WT.tex[s.id] = wtPaint(s, px); WT.u[key].value = WT.tex[s.id]; WT.px[s.id] = px;
    WT.mb += wtMiB(px); WT.painted++; WT.ms += performance.now() - t0; }
  if (WT.next >= WT_SURF.length) wtSwitch(WT.painted > 0);   // the shaders change once, when the set is complete
  else wtKick();
}
function wtKick(ms) {
  if (WT.sched || WT.next >= WT_SURF.length) return;
  WT.sched = true;
  if (ms) setTimeout(wtStep, ms);
  else if (window.requestIdleCallback) requestIdleCallback(wtStep, { timeout: 400 });
  else setTimeout(wtStep, 120);
}
function wtSet(tier) {
  if (!Object.hasOwn(WT_PX, tier)) throw new Error('no texture tier called ' + tier + '; the tiers are ' + Object.keys(WT_PX).join(', '));
  WT.tier = tier; wtSwitch(false);
  for (const s of WT_SURF) { WT.tex[s.id]?.dispose(); WT.u['uWt_' + s.id.replace('.', '_')].value = wtNeutral; }
  Object.assign(WT, { tex: {}, px: {}, next: 0, painted: 0, skipped: 0, mb: 0, ms: 0 });
  WT.plan = wtPlan(WT_PX[tier], WT_MB[tier], WT_SURF.length);
  if (!WT_PX[tier]) WT.next = WT_SURF.length; else wtKick();
}
wtSet(WT.tier);
window.__worldTex = () => ({ tier: WT.tier, asked: wtAsked === null ? 'auto' : wtAsked, px: WT_PX[WT.tier], on: WT.on, surfaces: WT_SURF.length,
  painted: WT.painted, skipped: WT.skipped, pending: WT_SURF.length - WT.next, mb: Math.round(WT.mb * 10) / 10, budgetMb: WT_MB[WT.tier],
  paintMs: Math.round(WT.ms), aniso: wtAniso(), err: WT.err,
  sizes: WT_SURF.map((s) => [s.id, s.id in WT.px ? WT.px[s.id] : 0, s.world_m]),
  mipmaps: Object.values(WT.tex).length > 0 && Object.values(WT.tex).every((t) => t.generateMipmaps && t.minFilter === THREE.LinearMipmapLinearFilter) });
// a harness asks for a tier and then measures it: the whole set is painted now (still never before the first frame)
window.__worldTexDo = (tier) => { wtSet(tier); while (WT.next < WT_SURF.length && renderer.info.render.frame > 0) wtStep(); return window.__worldTex(); };
/* WORLD-TEX END */
"""
