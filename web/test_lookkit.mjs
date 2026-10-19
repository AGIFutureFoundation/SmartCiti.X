// web/test_lookkit.mjs - the shared physically based look (web/lookkit.py) on the built pages.
// Prints `ok` per check and `FAIL` at column 0; exit 1 on any failure.
// What it holds: ACES Filmic + sRGB output + the stated exposure; the sun/sky rule computed in the page agrees with
// the Python kit to the digit; per-class roughness / metalness land on the named materials and fail closed; and the
// kit adds nothing that draws (no geometry, mesh, light or scene.add), so draw calls and triangles cannot move.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
let fails = 0, n = 0;
const check = (name, cond, why = '') => { n++; if (cond) console.log('  ok  ' + name); else { fails++; console.log('FAIL ' + name + (why ? ' - ' + why : '')); } };
const read = (f) => readFileSync(join(HERE, f), 'utf8');

const PAGES = [
  { id: 'campus3d', file: 'trade_craft_3d.html', exposure: 1.12, sunRule: 'registry' },
  { id: 'parishes', file: 'trade_craft_parishes.html', exposure: 0.95, sunRule: 'kit' },
  { id: 'bay', file: 'trade_craft_bay.html', exposure: 0.95, sunRule: 'kit' },
  { id: 'wilds', file: 'trade_craft_wilds.html', exposure: 0.95, sunRule: 'kit' },
];
const CLASSES = ['glass', 'metal', 'masonry', 'paving', 'foliage', 'water'];

function kitOf(page) {
  const a = page.indexOf('/* LOOK-KIT BEGIN'), b = page.indexOf('/* LOOK-KIT END */');
  return a < 0 || b < a ? null : page.slice(a, b);
}
function lift(kit) {
  const THREE = { ACESFilmicToneMapping: 4, SRGBColorSpace: 'srgb' };
  const window = {};
  const api = new Function('THREE', 'window', kit + '\nreturn { LOOK, lookRenderer, lookView, lookSunRule, lookSun, lookMat, lookMats, lookStat };')(THREE, window);
  api.window = window;
  return api;
}
const fakeColor = () => { const c = { v: 0, setHex(h) { c.v = h; }, getHexString() { return c.v.toString(16).padStart(6, '0'); } }; return c; };

for (const P of PAGES) {
  const page = read(P.file);
  const kit = kitOf(page);
  check(`${P.id}: exactly one LOOK-KIT block`, kit !== null && page.split('/* LOOK-KIT BEGIN').length === 2 && page.split('/* LOOK-KIT END */').length === 2);
  if (!kit) continue;
  check(`${P.id}: the kit draws nothing (no new THREE.*, no scene.add, no geometry)`, !/new THREE\.|scene\.add|Geometry|InstancedMesh/.test(kit));
  const K = lift(kit);
  check(`${P.id}: ACES Filmic, sRGB out, exposure ${P.exposure}`, K.LOOK.tone.tone_mapping === 'ACESFilmic' && K.LOOK.tone.output_color_space === 'srgb' && K.LOOK.exposure === P.exposure, JSON.stringify(K.LOOK.tone) + ' ' + K.LOOK.exposure);
  const r = {}; K.lookRenderer(r);
  check(`${P.id}: lookRenderer sets the tone map, colour space and exposure on the renderer`, r.toneMapping === 4 && r.outputColorSpace === 'srgb' && r.toneMappingExposure === P.exposure);
  check(`${P.id}: sun rule is '${P.sunRule}'`, K.LOOK.sunRule === P.sunRule);
  // the page's rule and the Python kit's rule agree at every stated sample elevation
  const bad = K.LOOK.samples.filter((s) => { const j = K.lookSunRule(s.h); return j.cct !== s.cct || j.sunI !== s.sunI || j.skyI !== s.skyI || j.sunHex !== s.sunHex || j.skyHex !== s.skyHex; });
  check(`${P.id}: the page's sun/sky rule equals the Python kit at ${K.LOOK.samples.length} elevations`, K.LOOK.samples.length >= 5 && bad.length === 0, JSON.stringify(bad[0] || {}));
  let mono = true;
  for (let h = 2; h <= 90; h++) { const a = K.lookSunRule(h - 1), b = K.lookSunRule(h); if (!(b.cct >= a.cct && b.sunI > a.sunI && b.skyI > a.skyI)) mono = false; }
  check(`${P.id}: a higher sun is never warmer or dimmer (rule is monotone in elevation)`, mono);
  check(`${P.id}: the class table has the six surface classes with roughness and metalness in [0, 1]`,
    CLASSES.every((c) => K.LOOK.classes[c] && ['roughness', 'metalness', 'env'].every((k) => K.LOOK.classes[c][k] >= 0 && K.LOOK.classes[c][k] <= 1)));
  const C = (c) => K.LOOK.classes[c] || { roughness: NaN, metalness: NaN };
  check(`${P.id}: metal is the only metallic class; glass and water are the smoothest`,
    CLASSES.filter((c) => C(c).metalness > 0.5).join() === 'metal'
    && Math.max(C('glass').roughness, C('water').roughness) < Math.min(...['metal', 'masonry', 'paving', 'foliage'].map((c) => C(c).roughness)));
  // fail closed: an unknown class, a material without PBR parameters, a mapped name the page lacks
  let t1 = false, t2 = false, t3 = false;
  try { K.lookMat({ roughness: 1, metalness: 0 }, 'chrome'); } catch { t1 = true; }
  try { K.lookMat({ color: 1 }, 'water'); } catch { t2 = true; }
  try { K.lookMats({}); } catch { t3 = true; }
  check(`${P.id}: lookMat / lookMats fail closed (unknown class, no roughness, missing material)`, t1 && t2 && t3);
  // every mapped material receives its class numbers
  const table = {}; for (const k of Object.keys(K.LOOK.map)) table[k] = { roughness: 0.5, metalness: 0.5, envMapIntensity: 1 };
  try { K.lookMats(table); } catch (e) { table.__err = String(e); }
  const wrong = Object.keys(K.LOOK.map).filter((k) => { const c = K.LOOK.classes[K.LOOK.map[k]]; return !c || table[k].roughness !== c.roughness || table[k].metalness !== c.metalness || table[k].envMapIntensity !== c.env; });
  check(`${P.id}: each of the ${Object.keys(K.LOOK.map).length} mapped materials takes its class roughness / metalness / env share`, Object.keys(K.LOOK.map).length > 0 && wrong.length === 0, wrong.join());
  check(`${P.id}: no internal names in the page's look block`, !/REALISM|\/tmp|scratchpad|memory\/|console/i.test(kit));
}

// ---- the 3D campus page: hooked at the renderer and at the shared material table -----------------------------
{
  const page = read('trade_craft_3d.html');
  const K = lift(kitOf(page));
  const iTone = page.indexOf('renderer.toneMappingExposure = 1.12;\nlookRenderer(renderer);   // LOOK-KIT');
  check('campus3d: lookRenderer(renderer) follows the renderer set-up exactly once', iTone > 0 && page.split('lookRenderer(renderer);').length === 2);
  const tbl = /\nconst mat = \{([\s\S]*?)\n\};/.exec(page);
  const names = tbl ? new Set([...tbl[1].matchAll(/^\s{2}(\w+):/gm)].map((m) => m[1])) : new Set();
  const missing = Object.keys(K.LOOK.map).filter((k) => !names.has(k));
  check('campus3d: every mapped name is in the shared material table', tbl && missing.length === 0, missing.join());
  const iUse = page.indexOf('for (const m of Object.values(mat)) m.userData.shared = true;\nlookMats(mat);   // LOOK-KIT');
  check('campus3d: lookMats(mat) runs right after the shared material table, once', iUse > tbl.index && page.split('lookMats(mat);').length === 2);
  const covered = new Set(Object.values(K.LOOK.map));
  check('campus3d: all six classes are used on the campus', CLASSES.every((c) => covered.has(c)), CLASSES.filter((c) => !covered.has(c)).join());
  check('campus3d: the sun and sky stay on the hour/weather registry (lookSun is never called)', !/lookSun\(/.test(page.replace(kitOf(page), '')));
}

// ---- the worlds pages (parish, Bay = the parish builder re-targeted, wilds): sun, sky and water -------------------
const vec = (x, y, z) => ({ x, y, z, clone() { return vec(this.x, this.y, this.z); }, sub(o) { this.x -= o.x; this.y -= o.y; this.z -= o.z; return this; },
  normalize() { const l = Math.hypot(this.x, this.y, this.z); this.x /= l; this.y /= l; this.z /= l; return this; } });
for (const W of [{ id: 'parishes', file: 'trade_craft_parishes.html', flat: true, std: 5 }, { id: 'bay', file: 'trade_craft_bay.html', flat: true, std: 3 },
                 { id: 'wilds', file: 'trade_craft_wilds.html', flat: false, std: 3 }]) {
  const page = read(W.file);
  const kit = kitOf(page);
  if (!kit) { check(`${W.id}: has the look kit`, false); continue; }
  const K = lift(kit);
  const body = page.replace(kit, '');
  const iSun = body.indexOf('lookRenderer(renderer); lookSun(sun, hemi);   // LOOK-KIT');
  const iDecl = body.indexOf('new THREE.DirectionalLight(');
  check(`${W.id}: the renderer and the sun/sky are set by the kit once, right after the sun exists`,
    iSun > iDecl && iDecl > 0 && body.split('lookSun(sun, hemi);').length === 2 && body.split('lookRenderer(renderer);').length === 2);
  if (W.flat) check(`${W.id}: the rule is applied before FLAT_LIGHT bakes the sun into the unlit land`, iSun > 0 && iSun < body.indexOf('const FLAT_LIGHT = '));
  // the page's own sun direction, resolved by the page's own kit: elevation, colour and intensity follow the rule
  const m = W.flat ? /const SUN = new THREE\.Vector3\(([-\d.]+), ([-\d.]+), ([-\d.]+)\)/.exec(body) : /sun\.position\.set\(([-\d.]+), ([-\d.]+), ([-\d.]+)\);/.exec(body);
  const sun = { position: m ? vec(+m[1], +m[2], +m[3]) : vec(0, 1, 0), target: { position: vec(0, 0, 0) }, color: fakeColor(), intensity: -1 };
  const hemi = { color: fakeColor(), intensity: -1 };
  K.lookSun(sun, hemi);
  const want = K.lookSunRule(Math.asin(sun.position.clone().normalize().y) * 180 / Math.PI);
  check(`${W.id}: sun ${K.lookStat.sun.h} deg -> ${want.cct} K at ${want.sunI}, sky ${want.skyI} (the kit's rule, not a hand number)`,
    m && sun.intensity === want.sunI && hemi.intensity === want.skyI && sun.color.v === want.sunHex && hemi.color.v === want.skyHex
    && K.lookStat.sun.h > 20 && K.lookStat.sun.h < 70);
  const wDecl = /const matWater = new THREE\.(\w+)\(/.exec(body);
  check(`${W.id}: the water is a standard (PBR) material of the water class, set right after it is made`,
    wDecl && wDecl[1] === 'MeshStandardMaterial' && body.split('lookMats({ matWater });').length === 2
    && body.indexOf('lookMats({ matWater });') > wDecl.index && body.indexOf('lookMats({ matWater });') - wDecl.index < 600
    && JSON.stringify(K.LOOK.map) === '{"matWater":"water"}');
  check(`${W.id}: land, buildings and trees stay diffuse (no other material changed shading model)`,
    (body.match(/new THREE\.MeshStandardMaterial\(/g) || []).length === W.std, String((body.match(/new THREE\.MeshStandardMaterial\(/g) || []).length));
}

// wave 20: PER-VIEW EXPOSURE - the network view is metered up, the campus and hall frames keep the page's number
{
  const page = read('trade_craft_3d.html'), K = lift(kitOf(page)), py = read('lookkit.py');
  const ve = K.LOOK.view_exposure, pyVal = Number((/VIEW_EXPOSURE = \{'region': ([0-9.]+)\}/.exec(py) || [])[1]);
  check('campus3d: the page names exactly one view with its own exposure, region, equal to the Python kit, above the page exposure and within (0, 4]',
    Object.keys(ve).join() === 'region' && ve.region === pyVal && ve.region > K.LOOK.exposure && ve.region <= 4, JSON.stringify(ve));
  const r = {}; K.lookRenderer(r);
  const at = (v) => { K.lookView(v); return r.toneMappingExposure; };
  check('campus3d: lookView sets the region exposure for the network view and the page exposure (1.12) for campus, hall, avatar, sim, restoration and an unknown view',
    at('region') === ve.region && ['campus', 'hall', 'avatar', 'sim', 'restoration', 'nonsense', 'toString'].every((v) => at('region') === ve.region && at(v) === 1.12));
  const wk = lift(kitOf(read('trade_craft_parishes.html')));
  check('parishes, Bay and wilds: no view has its own exposure (the worlds keep 0.95 everywhere)',
    ['trade_craft_parishes.html', 'trade_craft_bay.html', 'trade_craft_wilds.html'].every((f) => Object.keys(lift(kitOf(read(f))).LOOK.view_exposure).length === 0) && wk.LOOK.exposure === 0.95);
  check('campus3d: the exposure of the view drawn is set at the top of xrRender, the one draw, once',
    /function xrRender\(\) \{\n  lookView\(view\);   \/\/ LOOK-KIT/.test(page) && page.split('lookView(view);').length === 2);
  check('campus3d: the per-view exposure moves a uniform only (no new draw call or object in the kit, no scene.add)', !/new THREE\.|scene\.add|Geometry|InstancedMesh/.test(kitOf(page)));
}

console.log(fails ? `web/test_lookkit: ${fails} of ${n} checks FAILED` : `web/test_lookkit: ${n} checks passed - one physically based look, drawn with nothing new`);
process.exit(fails ? 1 : 0);
