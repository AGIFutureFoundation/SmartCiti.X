#!/usr/bin/env python3
"""The Unspoken Smiles world page (SMILES, wave 12): web/trade_craft_smiles.html.

A lighter walkable 3D district (three.js from web/vendor) built from smiles/registry/smiles.json: the AUTHORED 4k map
is the ground, the clinic's rooms are walk-in outlines whose panel links every one of the 37 programme stations at its
source URL, the school / park / playground / community centre / shop / van lot hold the six mini-games of
web/smileskit.py, a mobile dental van drives its AUTHORED loop, and eight tooth-fairy style eggs hide in the zones
(quests/source/smiles.json; reported to TCQuests when the quest registry carries them).

Site nav, one <h1>, the style head script, hudkit-managed panels, 44 px targets; every chrome word is an i18n key in
8 locales (Arabic right-to-left). Registry text (zone, room, station and snack names, guidance lines) is shown verbatim.
Why not DERIVED from the parish machinery like the Bay world: the parish builder needs a county/parish geography pack
(outlines, streets, lots, ~5 min build); an AUTHORED 800 m district has none, so this wave ships the lighter page.
"""
import html
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402
from seo import apply_seo  # noqa: E402
from sitenav import nav_html, labels as nav_labels, NAV_CSS, STYLE_JS  # noqa: E402
from pagehero import theme  # noqa: E402
from design_kit import STYLE_HEAD_JS  # noqa: E402
from hudkit import HUD_CSS, HUD_JS, HUD_I18N_KEYS, hud_layer, flow_anchors_present  # noqa: E402
from physkit import phys_inline  # noqa: E402
from smileskit import smiles_data, smiles_i18n_keys, smiles_panel_html, SMILES_CSS, SMILES_JS  # noqa: E402
import sitenav  # noqa: E402

PAGE = 'web/trade_craft_smiles.html'
E = lambda s: html.escape(str(s), quote=True)


class SmilesPageError(Exception):
    pass


NAV_NOTE = ''
if PAGE not in sitenav.PAGES:
    raise SystemExit('build_smiles: web/trade_craft_smiles.html is not in web/sitenav.py PAGES')

PAGE_KEYS = ['smiles.nav', 'smiles.kicker', 'smiles.title', 'smiles.lede', 'smiles.seo.desc', 'smiles.authored',
             'smiles.play', 'smiles.walk', 'smiles.near', 'smiles.h.games', 'smiles.h.clinic', 'smiles.h.map',
             'smiles.h.eggs', 'smiles.eggs.found', 'smiles.station.src', 'smiles.pad.up', 'smiles.pad.down',
             'smiles.pad.left', 'smiles.pad.right', 'smiles.map.alt', 'smiles.nowebgl', 'smiles.playhere',
             'smiles.egg.got', 'smiles.programme']
KEYS = PAGE_KEYS + smiles_i18n_keys() + HUD_I18N_KEYS

I18N = {}
for f in sorted((ROOT / 'i18n/locales').glob('*.json')):
    c = json.loads(f.read_text(encoding='utf-8'))
    s = c['strings']
    miss = [k for k in KEYS if k not in s or not isinstance(s[k], str) or not s[k].strip()]
    if miss:
        raise SmilesPageError(f'build_smiles: locale {f.name} is missing {miss[:5]}')
    I18N[c['locale']] = {'dir': c['dir'], 'strings': {k: s[k] for k in KEYS}}
if len(I18N) != 8:
    raise SmilesPageError(f'build_smiles: expected 8 locales, found {sorted(I18N)}')
EN = I18N['en']['strings']


def T(k, tag='span', attrs=''):
    if k not in EN:
        raise SmilesPageError(f'build_smiles: unknown key {k}')
    return f'<{tag}{attrs} data-i18n="{k}">{E(EN[k])}</{tag}>'


def TS(k):
    return T(k)


def TA(k):
    if k not in EN:
        raise SmilesPageError(f'build_smiles: unknown key {k}')
    return E(EN[k])


REG = json.loads((ROOT / 'smiles/registry/smiles.json').read_text(encoding='utf-8'))
for k in ('walls', 'doors', 'zones', 'rooms', 'stations', 'eggs', 'van_route', 'map', 'atlas', 'counts', 'programmes', 'streets'):
    if k not in REG:
        raise SmilesPageError(f'build_smiles: smiles registry has no {k!r}')
if REG['provenance'] != 'AUTHORED':
    raise SmilesPageError('build_smiles: the district must be AUTHORED')
DATA = smiles_data()
PHYS = json.loads((ROOT / 'physics/registry/physics.json').read_text(encoding='utf-8'))
for k in ('coeffs', 'honesty'):
    if k not in PHYS:
        raise SmilesPageError(f'build_smiles: physics/registry/physics.json has no {k!r}')
ST = {s['id']: s for s in REG['stations']}

# quests: eggs are reported to TCQuests only when the shared quest registry carries every one of them
QREG = ROOT / 'quests/registry/quests.json'
QIDS = {q['id'] for q in json.loads(QREG.read_text(encoding='utf-8'))['quests']} if QREG.exists() else set()
QUESTS_ON = all(g['id'] in QIDS for g in REG['eggs'])
QUEST_BLOCK = ''
if QUESTS_ON:
    from questkit import quest_js, QUEST_CSS  # noqa: E402
    QUEST_BLOCK = f'<style id="quest-css">{QUEST_CSS}</style>' + quest_js('smiles', page=PAGE)


def room_card(r):
    items = ''.join(f'<li data-station="{E(sid)}"><a href="{E(ST[sid]["url"])}" rel="noopener" target="_blank">'
                    f'{E(ST[sid]["name"])}</a> <code>{E(sid)}</code></li>' for sid in r['stations'])
    return (f'<details class="room" data-room="{E(r["id"])}"><summary>{E(r["name"])} '
            f'<span class="tag">{len(r["stations"])}</span></summary><ul>{items}</ul></details>')


rooms_html = ''.join(room_card(r) for r in REG['rooms'])
progs = ' · '.join(f'{E(p["name"])} ({p["stations"]})' for p in REG['programmes'])
shelf = ''.join(f'<li data-egg="{E(g["id"])}" data-found="0"><span class="egg-t">{E(g["title"])}</span> '
                f'<span class="muted">{E(g["hint"])}</span></li>' for g in REG['eggs'])


def js_json(x):
    return json.dumps(x, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')


WORLD = {
    'size': REG['size_m'], 'zones': REG['zones'], 'rooms': [{k: r[k] for k in ('id', 'name', 'rect', 'stations')} for r in REG['rooms']],
    'stations': {s['id']: {'name': s['name'], 'url': s['url']} for s in REG['stations']},
    'eggs': REG['eggs'], 'van': REG['van_route'], 'walls': REG['walls'], 'doors': REG['doors'], 'streets': REG['streets'],
    'map': '../' + REG['map']['image'], 'atlas': '../' + REG['atlas']['image'], 'atlas_grid': REG['atlas']['grid'],
    'atlas_cells': REG['atlas']['cells'], 'games_at': {g: REG['games'][g]['zone'] for g in DATA['games']},
    'quests': QUESTS_ON,
}

HUD_PANELS = [
    {'id': 'near', 'kind': 'panel', 'sel': '#sm-near', 'slot': 'te', 'order': 1, 'compact': 'none'},
    {'id': 'toast', 'kind': 'panel', 'sel': '#sm-toast', 'slot': 't', 'order': 0, 'compact': 'none'},
    {'id': 'pad', 'kind': 'panel', 'sel': '#sm-pad', 'slot': 'bs', 'order': 0, 'compact': 'none'},
    {'id': 'minimap', 'kind': 'panel', 'sel': '#sm-mini', 'slot': 'be', 'order': 0, 'compact': 'none'},
    {'id': 'eggs', 'kind': 'panel', 'sel': '#sm-eggcount', 'slot': 'ts', 'order': 0, 'compact': 'none'},
    {'id': 'games', 'kind': 'flow', 'goto': '#sm-games', 'anchor': '<section class="sm-games" id="sm-games"', 'icon': 'route', 'label': 'smiles.h.games'},
    {'id': 'legend', 'kind': 'flow', 'goto': '[data-legend]', 'anchor': '<p class="help" data-legend>', 'icon': 'info', 'label': 'hud.open.legend'},
]
HUD_LAYER = hud_layer(HUD_PANELS, TS, TA)

WORLD_JS = r'''
import * as THREE from './vendor/three.module.min.js';
__PHYS_INLINE__
const W = JSON.parse(document.getElementById('sm-world').textContent);
const P = window.__smilesPage, t = P.t;
const $ = (s) => document.querySelector(s);
const state = { ready: false, pos: { x: 205, z: 420 }, heading: Math.PI, near: null, found: new Set(), vanAt: null, error: null };
window.__smilesWorld = state;
try { const o = JSON.parse(localStorage.getItem('tc-smiles') || '{}'); (o.eggs || []).forEach((id) => state.found.add(id)); } catch (e) { /* device storage unavailable */ }
const saveEggs = () => { try { const o = JSON.parse(localStorage.getItem('tc-smiles') || '{}'); o.eggs = [...state.found]; localStorage.setItem('tc-smiles', JSON.stringify(o)); } catch (e) { /* play continues */ } };
const toast = (msg) => { const el = $('#sm-toast'); el.textContent = msg; el.hidden = false; clearTimeout(toast.h); toast.h = setTimeout(() => { el.hidden = true; }, 2600); };
const shelf = () => { document.querySelectorAll('[data-egg]').forEach((li) => { li.dataset.found = state.found.has(li.dataset.egg) ? '1' : '0'; });
  $('#sm-eggn').textContent = `${state.found.size} / ${W.eggs.length}`; };
const inRect = (x, z, r) => x >= r[0] && x <= r[0] + r[2] && z >= r[1] && z <= r[1] + r[3];
const stage = $('#sm-stage3d'), canvas = $('#sm-canvas');
let renderer;
try { renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true }); }
catch (e) { state.error = 'webgl'; $('#sm-nogl').hidden = false; shelf(); }
if (renderer) {
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xbfe3f2);
  scene.fog = new THREE.Fog(0xbfe3f2, 120, 520);
  const cam = new THREE.PerspectiveCamera(60, 1, 0.5, 1500);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x6b8f5e, 1.1));
  const sun = new THREE.DirectionalLight(0xffffff, 1.2); sun.position.set(200, 400, 100); scene.add(sun);
  const loader = new THREE.TextureLoader();
  const [SW, SH] = W.size;
  const mapTex = loader.load(W.map); mapTex.colorSpace = THREE.SRGBColorSpace; mapTex.anisotropy = 8;
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(SW, SH), new THREE.MeshLambertMaterial({ map: mapTex }));
  ground.rotation.x = -Math.PI / 2; ground.position.set(SW / 2, 0, SH / 2); scene.add(ground);
  // ONE atlas image; each cell's material gets its sub-rectangle only once the image has loaded (a clone made
  // before then has no image data and three warns on needsUpdate)
  const cellMats = {};
  const cell = (name) => (cellMats[name] = cellMats[name] || new THREE.MeshLambertMaterial({ color: 0xffffff }));
  loader.load(W.atlas, (atlas) => { atlas.colorSpace = THREE.SRGBColorSpace; const g = W.atlas_grid;
    for (const name in cellMats) { const c = W.atlas_cells[name], tx = atlas.clone(); tx.repeat.set(1 / g, 1 / g); tx.offset.set(c.col / g, 1 - (c.row + 1) / g); tx.needsUpdate = true; cellMats[name].map = tx; cellMats[name].needsUpdate = true; } });
  // every wall drawn is also a solid physkit box (web/physkit.py, the shared arcade physics; same yaw as the mesh)
  const BOXES = [];
  const wall = (x0, z0, x1, z1, h, mat, id) => { const len = Math.hypot(x1 - x0, z1 - z0); if (len < 0.05) return; const m = new THREE.Mesh(new THREE.BoxGeometry(len, h, 0.4), mat);
    const yaw = -Math.atan2(z1 - z0, x1 - x0); m.position.set((x0 + x1) / 2, h / 2, (z0 + z1) / 2); m.rotation.y = yaw; scene.add(m);
    BOXES.push({ id, cx: (x0 + x1) / 2, cz: (z0 + z1) / 2, hx: len / 2, hz: 0.2, yaw, y0: 0, y1: h, kind: 'wall' }); };
  // walls and doorways come from the registry (smiles/build.py walls_for): drawn here and solid in physkit
  const roomMat = new THREE.MeshLambertMaterial({ color: 0x5b9ec2 });
  for (const w of W.walls) wall(w.from[0], w.from[1], w.to[0], w.to[1], w.h, w.mat === 'room' ? roomMat : cell(w.mat), w.id);
  // houses and market stalls: solid footprints from the registry
  const houseMat = new THREE.MeshLambertMaterial({ color: 0xbe7864 }), stallMat = new THREE.MeshLambertMaterial({ color: 0xe0a040 });
  for (const zn of W.zones) for (const [sx, sz, sw, sd] of zn.solids) { const h = zn.kind === 'residential' ? 6 : 2.4;
    const m = new THREE.Mesh(new THREE.BoxGeometry(sw, h, sd), zn.kind === 'residential' ? houseMat : stallMat); m.position.set(sx + sw / 2, h / 2, sz + sd / 2); scene.add(m);
    BOXES.push({ id: zn.id + ':solid:' + BOXES.length, cx: sx + sw / 2, cz: sz + sd / 2, hx: sw / 2, hz: sd / 2, yaw: 0, y0: 0, y1: h, kind: 'building' }); }
  // bus shelter
  const bs = W.zones.find((z) => z.kind === 'busstop');
  if (bs) { const [bx, bz, bw, bd] = bs.rect; const m = new THREE.Mesh(new THREE.BoxGeometry(bw, 0.3, bd), new THREE.MeshLambertMaterial({ color: 0xffc107 })); m.position.set(bx + bw / 2, 2.6, bz + bd / 2); scene.add(m); }
  const PREG = JSON.parse(document.getElementById('sm-phys').textContent), PHYS_R = physCoeffs(PREG).avatar.radius;
  const PW = createPhysics({ reg: PREG, cell: 16, ground: () => 0, water: () => null });
  PW.addBoxes(BOXES);
  const av = physAvatar(state.pos.x, 0, state.pos.z);
  state.boxes = BOXES.length; state.inside = 0;
  // playground and park furniture: a few simple shapes (AUTHORED)
  const addBox = (x, z, w, h, d, color) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), new THREE.MeshLambertMaterial({ color })); m.position.set(x, h / 2, z); scene.add(m); return m; };
  const pg = W.zones.find((z) => z.id === 'playground').rect; addBox(pg[0] + 100, pg[1] + 50, 6, 3, 2, 0xe53935); addBox(pg[0] + 40, pg[1] + 60, 10, 0.4, 3, 0x1e88e5);
  const park = W.zones.find((z) => z.id === 'park').rect;
  for (let i = 0; i < 24; i++) { const tx = park[0] + 12 + ((i * 53) % (park[2] - 24)), tz = park[1] + 12 + ((i * 29) % (park[3] - 60));
    const tr = new THREE.Mesh(new THREE.ConeGeometry(3, 9, 8), new THREE.MeshLambertMaterial({ color: 0x3f7f45 })); tr.position.set(tx, 5.5, tz); scene.add(tr); addBox(tx, tz, 0.8, 1.2, 0.8, 0x7a5230); }
  // eggs: small bright shapes, hidden among the zones (found by walking up to them)
  const eggMesh = {};
  for (const g of W.eggs) { const m = new THREE.Mesh(new THREE.OctahedronGeometry(0.9), new THREE.MeshLambertMaterial({ color: 0xffd54f, emissive: 0x6b5200 }));
    m.position.set(g.at[0], 1.1, g.at[1]); m.visible = !state.found.has(g.id); scene.add(m); eggMesh[g.id] = m; }
  // the mobile dental van on its loop
  const van = addBox(0, 0, 6, 2.6, 2.6, 0xe05896); const vanPath = W.van.path; const segL = vanPath.slice(1).map((b, i) => Math.hypot(b[0] - vanPath[i][0], b[1] - vanPath[i][1]));
  const loopL = segL.reduce((a, v) => a + v, 0);
  const vanAt = (d) => { d = ((d % loopL) + loopL) % loopL; for (let i = 0; i < segL.length; i++) { if (d <= segL[i]) { const a = vanPath[i], b = vanPath[i + 1], f = d / segL[i]; return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, Math.atan2(b[1] - a[1], b[0] - a[0])]; } d -= segL[i]; } return [vanPath[0][0], vanPath[0][1], 0]; };
  // the walker
  const me = new THREE.Group(); const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.45, 1.0, 4, 8), new THREE.MeshLambertMaterial({ color: 0x00897b }));
  body.position.y = 1.0; me.add(body); scene.add(me);
  const keys = new Set(); const pad = { f: 0, t: 0 };
  addEventListener('keydown', (e) => { if (e.target.closest && e.target.closest('input,select,textarea')) return; if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'w', 'a', 's', 'd', 'W', 'A', 'S', 'D'].includes(e.key)) { keys.add(e.key.toLowerCase()); if (document.activeElement === canvas) e.preventDefault(); } });
  addEventListener('keyup', (e) => keys.delete(e.key.toLowerCase()));
  document.querySelectorAll('[data-pad]').forEach((b) => { const on = () => { const v = b.dataset.pad; if (v === 'up') pad.f = 1; if (v === 'down') pad.f = -1; if (v === 'left') pad.t = 1; if (v === 'right') pad.t = -1; };
    const off = () => { pad.f = 0; pad.t = 0; }; b.addEventListener('pointerdown', on); b.addEventListener('pointerup', off); b.addEventListener('pointerleave', off); b.addEventListener('click', () => { on(); step(0.35); off(); }); });
  const mini = $('#sm-mini-dot');
  const zoneAt = (x, z) => W.zones.find((zn) => inRect(x, z, zn.rect)) || null;
  const roomAt = (x, z) => W.rooms.find((r) => inRect(x, z, r.rect)) || null;
  const nearPanel = () => { const zn = zoneAt(state.pos.x, state.pos.z), rm = roomAt(state.pos.x, state.pos.z); const key = (zn ? zn.id : '-') + '|' + (rm ? rm.id : '-');
    if (key === state.near) return; state.near = key; const box = $('#sm-near-body');
    if (!zn) { box.textContent = t('smiles.walk'); return; }
    let h = `<strong>${P.esc(zn.name)}</strong>`;
    if (rm) h += `<p>${P.esc(rm.name)}</p><ul>${rm.stations.map((sid) => `<li><a href="${P.esc(W.stations[sid].url)}" rel="noopener" target="_blank">${P.esc(W.stations[sid].name)}</a></li>`).join('')}</ul>`;
    const gs = Object.keys(W.games_at).filter((g) => W.games_at[g] === zn.id);
    if (gs.length) h += gs.map((g) => `<button type="button" data-play="${g}">${P.esc(t('smiles.playhere'))}: ${P.esc(t('smiles.g.' + g))}</button>`).join('');
    box.innerHTML = h; box.querySelectorAll('[data-play]').forEach((b) => b.addEventListener('click', () => { P.games.open(b.dataset.play); $('#sm-games').scrollIntoView({ block: 'start' }); })); };
  const findEggs = () => { for (const g of W.eggs) { if (state.found.has(g.id)) continue; if (Math.hypot(g.at[0] - state.pos.x, g.at[1] - state.pos.z) < 3) {
      state.found.add(g.id); eggMesh[g.id].visible = false; saveEggs(); shelf(); toast(`${t('smiles.egg.got')}: ${g.title} - ${g.badge}. ${g.reveal}`);
      if (W.quests) { const T = window.TCQuests; if (T && T.data && T.data.quests.some((q) => q.id === g.id)) T.find(g.id); } } } };
  const WALK_MS = 9;   // AUTHORED arcade walking pace for an 1200 m district (play, not a real speed)
  function step(dt) { const f = (keys.has('arrowup') || keys.has('w') ? 1 : 0) - (keys.has('arrowdown') || keys.has('s') ? 1 : 0) + pad.f + state.auto;
    const tr = (keys.has('arrowleft') || keys.has('a') ? 1 : 0) - (keys.has('arrowright') || keys.has('d') ? 1 : 0) + pad.t;
    state.heading += tr * 2.2 * dt; const v = WALK_MS * Math.max(-1, Math.min(1, f));
    PW.stepAvatar(av, { vx: Math.sin(state.heading) * v, vz: Math.cos(state.heading) * v, jump: false }, dt);
    state.pos.x = av.x; state.pos.z = av.z;
    if (PW.query(av.x, av.z, PHYS_R * 0.5).some((b) => b.y1 > av.y + 0.3)) state.inside++; }
  state.auto = 0;
  state.teleport = (x, z) => { av.x = x; av.z = z; av.vx = 0; av.vz = 0; state.pos.x = x; state.pos.z = z; };
  state.face = (h) => { state.heading = h; };
  const resize = () => { const w = stage.clientWidth, h = stage.clientHeight; renderer.setSize(w, h, false); cam.aspect = w / Math.max(1, h); cam.updateProjectionMatrix(); };
  new ResizeObserver(resize).observe(stage); resize();
  let last = performance.now(), vanD = 0, frames = 0;
  const loop = (now) => { const dt = Math.min(0.1, (now - last) / 1000); last = now; step(dt); vanD += 8 * dt;
    const v = vanAt(vanD); van.position.set(v[0], 1.3, v[1]); van.rotation.y = -v[2]; state.vanAt = [v[0], v[1]];
    me.position.set(state.pos.x, 0, state.pos.z); me.rotation.y = state.heading;
    cam.position.set(state.pos.x - Math.sin(state.heading) * 14, 8, state.pos.z - Math.cos(state.heading) * 14); cam.lookAt(state.pos.x, 1.5, state.pos.z);
    for (const id in eggMesh) eggMesh[id].rotation.y += dt * 2;
    mini.style.insetInlineStart = `${(state.pos.x / SW) * 100}%`; mini.style.insetBlockStart = `${(state.pos.z / SH) * 100}%`;
    nearPanel(); findEggs(); renderer.render(scene, cam); frames++; if (frames === 3) state.ready = true; requestAnimationFrame(loop); };
  shelf(); requestAnimationFrame(loop);
}
'''

PAGE_JS = r'''(function () {
  'use strict';
  var I = JSON.parse(document.getElementById('sm-i18n').textContent);
  var q = new URLSearchParams(location.search), loc = 'en', lq = q.get('lang');
  if (lq && Object.prototype.hasOwnProperty.call(I, lq)) loc = lq;
  else {
    var prefs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || 'en'];
    for (var i = 0; i < prefs.length; i++) { var c = String(prefs[i]).slice(0, 2).toLowerCase(); if (Object.prototype.hasOwnProperty.call(I, c)) { loc = c; break; } }
  }
  var S = I[loc].strings, t = function (k) { if (typeof S[k] !== 'string') throw new Error('smiles i18n: ' + loc + ' has no ' + k); return S[k]; };
  document.documentElement.lang = loc; document.documentElement.dir = I[loc].dir;
  document.querySelectorAll('[data-i18n]').forEach(function (el) { el.textContent = t(el.getAttribute('data-i18n')); });
  document.querySelectorAll('[data-i18n-aria]').forEach(function (el) { el.setAttribute('aria-label', t(el.getAttribute('data-i18n-aria'))); });
  var D = JSON.parse(document.getElementById('sm-data').textContent);
  var seed = Number(q.get('seed')) || 1;
  var games = SmilesGames(D, t, seed);
  window.__smilesPage = { locale: loc, dir: I[loc].dir, t: t, games: games, esc: games.esc, seed: seed };
})();'''

tcss, tjs = theme('doc')
NAV = nav_html(PAGE, nav_labels('en'))
ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' "
        "height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M9 9c3-2 5 0 7 0s4-2 7 0c2 2 1 6 0 9-1 4-2 7-3 7s-2-5-4-5-3 5-4 5-2-3-3-7c-1-3-2-7 0-9z' "
        "fill='%23F4F7F6'/%3E%3C/svg%3E")

zone_legend = ''.join(f'<li><span class="sw" style="background:{E(z["colour"])}"></span>{E(z["name"])}</li>' for z in REG['zones'])

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="{ICON}">
<title>Unspoken Smiles world</title>
<script id="style-head-js">{STYLE_HEAD_JS}</script>
<style>{NAV_CSS}</style>
<style id="tc-css">{tcss}</style>
<style id="hud-css">{HUD_CSS}</style>
<style id="sm-css">{SMILES_CSS}</style>
<style>
body{{font:16px/1.6 "IBM Plex Sans",system-ui,sans-serif}}
.wrap{{max-width:1100px;margin:0 auto;padding:20px 16px 120px}}
.lede{{color:var(--tc-muted);max-width:72ch}}
main,section,li,p,summary{{overflow-wrap:anywhere}}
.box{{border:1px solid var(--tc-line);border-radius:10px;padding:16px;margin:0 0 20px;background:var(--tc-panel);color:var(--tc-ink);min-inline-size:0}}
.box h2{{margin:0 0 10px;font-size:22px}}
#sm-stage3d{{position:relative;block-size:min(70vh,620px);min-block-size:360px;border-radius:10px;overflow:hidden;background:#bfe3f2;margin:0 0 16px}}
#sm-canvas{{display:block;inline-size:100%;block-size:100%;touch-action:none}}
.sm-panel{{background:rgba(255,255,255,.92);color:#10202a;border-radius:8px;padding:8px 10px;max-inline-size:280px;font-size:14px}}
.sm-panel ul{{margin:4px 0;padding-inline-start:18px;max-block-size:160px;overflow:auto}}
.sm-panel a{{color:#0b5a7a;display:inline-flex;align-items:center;min-block-size:44px}}
.sm-panel button{{min-block-size:44px;min-inline-size:44px;margin:4px 4px 0 0;border-radius:8px;border:1px solid #6a8;background:#fff;color:#10202a;font:inherit}}
#sm-pad{{display:grid;grid-template-columns:repeat(3,44px);grid-template-rows:repeat(2,44px);gap:4px}}
#sm-pad button{{min-block-size:44px;min-inline-size:44px;border-radius:10px;border:1px solid #6a8;background:rgba(255,255,255,.9);color:#10202a;font:700 18px/1 system-ui}}
#sm-pad [data-pad=up]{{grid-column:2}}#sm-pad [data-pad=left]{{grid-column:1;grid-row:2}}#sm-pad [data-pad=down]{{grid-column:2;grid-row:2}}#sm-pad [data-pad=right]{{grid-column:3;grid-row:2}}
#sm-mini{{position:relative;inline-size:120px;block-size:120px;border-radius:8px;overflow:hidden;border:2px solid #fff;background:#7ab068}}
#sm-mini img{{inline-size:100%;block-size:100%;display:block}}
#sm-mini-dot{{position:absolute;inline-size:10px;block-size:10px;margin:-5px;border-radius:50%;background:#d81b60;border:2px solid #fff}}
#sm-toast{{background:#10202a;color:#fff;border-radius:8px;padding:6px 12px}}
.room{{border-block-start:1px solid var(--tc-line);padding:6px 0}}
.room summary{{cursor:pointer;min-block-size:44px;display:flex;align-items:center;gap:6px}}
.room li a{{display:inline-flex;align-items:center;min-block-size:44px;color:var(--tc-link)}}
.rooms{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:0 16px}}
.tag{{font:600 12px/1 ui-monospace,monospace;border:1px solid var(--tc-line);border-radius:4px;padding:3px 6px;color:var(--tc-muted)}}
.muted{{color:var(--tc-muted);font-size:14px}}
code{{font:13px ui-monospace,monospace}}
.eggs li[data-found="1"] .egg-t{{font-weight:700}}
.eggs li[data-found="1"] .egg-t::before{{content:"\\2605 "}}
.legend{{list-style:none;padding:0;display:flex;flex-wrap:wrap;gap:6px 14px}}
.sw{{display:inline-block;inline-size:14px;block-size:14px;border-radius:3px;margin-inline-end:6px;vertical-align:-2px;border:1px solid #445}}
.mapimg{{inline-size:100%;max-inline-size:640px;block-size:auto;border-radius:8px}}
a{{color:var(--tc-link)}}
</style>
</head>
<body class="tc-theme">
{NAV}
<main class="wrap" id="sm-main">
<header>
{T("smiles.kicker", "p", ' class="tc-kicker"')}
{T("smiles.title", "h1", ' class="tc-page-title"')}
{T("smiles.lede", "p", ' class="lede"')}
<p class="muted"><span class="tag">AUTHORED</span> {T("smiles.authored")} · {T("smiles.programme")}: {progs}</p>
<p class="muted" data-play-note>{T("smiles.play")}</p>
</header>
<div id="sm-stage3d">
<canvas id="sm-canvas" tabindex="0" aria-label="{TA("smiles.walk")}" data-i18n-aria="smiles.walk"></canvas>
<p id="sm-nogl" class="sm-panel" hidden>{T("smiles.nowebgl")}</p>
<div id="sm-near" class="sm-panel"><div id="sm-near-body">{T("smiles.walk")}</div></div>
<div id="sm-toast" role="status" hidden></div>
<div id="sm-eggcount" class="sm-panel">{T("smiles.eggs.found")}: <b id="sm-eggn">0 / {len(REG["eggs"])}</b></div>
<div id="sm-pad" role="group" aria-label="{TA("smiles.walk")}" data-i18n-aria="smiles.walk">
<button type="button" data-pad="up" aria-label="{TA("smiles.pad.up")}" data-i18n-aria="smiles.pad.up">&#8593;</button>
<button type="button" data-pad="left" aria-label="{TA("smiles.pad.left")}" data-i18n-aria="smiles.pad.left">&#8630;</button>
<button type="button" data-pad="down" aria-label="{TA("smiles.pad.down")}" data-i18n-aria="smiles.pad.down">&#8595;</button>
<button type="button" data-pad="right" aria-label="{TA("smiles.pad.right")}" data-i18n-aria="smiles.pad.right">&#8631;</button>
</div>
<div id="sm-mini"><img src="../{E(REG["map"]["image"])}" alt="{TA("smiles.map.alt")}" data-i18n-aria="smiles.map.alt" width="120" height="120"><span id="sm-mini-dot"></span></div>
{HUD_LAYER}
</div>
<section class="box">{smiles_panel_html(T)}</section>
<section class="box" aria-labelledby="sm-h-clinic"><h2 id="sm-h-clinic" data-i18n="smiles.h.clinic">{E(EN["smiles.h.clinic"])}</h2>
<p class="muted">{E(REG["rooms_note"])} {T("smiles.station.src")}: <code>{E(REG["stations_from"]["from"])}@{E(REG["stations_from"]["ref_commit"][:12])}</code></p>
<div class="rooms">{rooms_html}</div></section>
<section class="box" aria-labelledby="sm-h-eggs"><h2 id="sm-h-eggs" data-i18n="smiles.h.eggs">{E(EN["smiles.h.eggs"])}</h2><ul class="eggs">{shelf}</ul></section>
<section class="box" aria-labelledby="sm-h-map"><h2 id="sm-h-map" data-i18n="smiles.h.map">{E(EN["smiles.h.map"])}</h2>
<p class="help" data-legend>{E(REG["place_note"])} {E(REG["van_route"]["note"])}</p>
<ul class="legend">{zone_legend}</ul>
<img class="mapimg" src="../{E(REG["map"]["image"])}" alt="{TA("smiles.map.alt")}" data-i18n-aria="smiles.map.alt" width="640" height="640" loading="lazy">
</section>
<p class="muted">smiles/registry/smiles.json · {E(REG["schema"])} · stamp <code data-stamp>{E(REG["source_stamp"])}</code></p>
</main>
<script type="application/json" id="sm-data">{js_json(DATA)}</script>
<script type="application/json" id="sm-world">{js_json(WORLD)}</script>
<script type="application/json" id="sm-i18n">{js_json(I18N)}</script>
<script id="sm-kit">{SMILES_JS}</script>
<script id="sm-page">{PAGE_JS}</script>
<script id="hud-kit">{HUD_JS}</script>
<script type="application/json" id="sm-phys">{js_json(PHYS)}</script>
<script type="module" id="sm-world-js">{WORLD_JS.replace('__PHYS_INLINE__', phys_inline())}</script>
<script>{tjs}</script>
<script id="style-js">{STYLE_JS}</script>
{QUEST_BLOCK}
</body>
</html>
'''
flow_anchors_present(HUD_PANELS, page)
TITLE = 'SmartCiti.X : Trade Craft Academy — ' + EN['smiles.nav']
page = apply_seo(page, PAGE, TITLE, EN['smiles.seo.desc'], 'page')
emit(HERE / 'trade_craft_smiles.html', page,
     f'{REG["counts"]["stations"]} stations | {REG["counts"]["rooms"]} rooms | {REG["counts"]["eggs"]} eggs | quests {"on" if QUESTS_ON else "off"} | {NAV_NOTE} | stamp {REG["source_stamp"][:16]}')
