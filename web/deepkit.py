"""web/deepkit.py - DEEP underwater kit (embeddable in any world page that has physkit water states).

    from deepkit import DEEP_CSS, deep_inline, deep_data, deep_panel_html, DEEP_I18N_KEYS

- deep_data(world) -> the underwater/registry/underwater.json subset for one world ('parishes' | 'bay'): embed it as
  <script type="application/json" id="deep-data">.
- deep_inline() -> ES code (no imports; THREE is passed in) between /* DEEP_KIT:BEGIN */ and /* DEEP_KIT:END */ to
  paste into the page's module script. Top-level names start with deep/DEEP_.
- deepWorld(reg, world) (JS) = deep_data for pages that fetch the registry lazily; deepMount({..., initial: 'dive'|'rov'})
  replays the press that triggered the load.
- deepMount({THREE, scene, camera, data, eye, getMode, waterState, T}) -> kit {update(dt, overview), state, hud(),
  setTargets(list), stats()}; call kit.update(dt, mode === 'overview') AFTER the page places its camera.

Budget: <= 4 draw calls (1 seafloor + 3 instanced habitat families), 0 in the overview and 0 above the surface.
Honesty: depths / substrates / habitats are AUTHORED (registry legend); dive and ROV are a game camera for monitoring
practice, not dive training or dive-safety instruction; animals are never harmed (no fauna is drawn or touched).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / 'underwater/registry/underwater.json'
DEEP_I18N_KEYS = ['deep.dive', 'deep.rov', 'deep.up', 'deep.down', 'deep.honesty', 'deep.hud.depth',
                  'deep.hud.heading', 'deep.hud.alt', 'deep.hud.substrate', 'deep.refused']


class DeepKitError(Exception):
    pass


def deep_data(world):
    reg = json.loads(REG.read_text())
    for k in ('honesty', 'legend', 'substrates', 'bodies', 'source_stamp'):
        if k not in reg:
            raise DeepKitError(f'deepkit: underwater.json has no {k!r}')
    bodies = [b for b in reg['bodies'] if b['world'] == world]
    if not bodies:
        raise DeepKitError(f'deepkit: no underwater bodies for world {world!r}')
    return {'world': world, 'stamp': reg['source_stamp'], 'honesty': reg['honesty'], 'legend': reg['legend'],
            'substrates': reg['substrates'], 'bodies': bodies}


DEEP_CSS = '''
.deep-panel{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin:6px 0}
.deep-hud{position:absolute;left:50%;transform:translateX(-50%);bottom:8px;z-index:3;background:var(--scrim,rgba(0,0,0,.6));color:var(--ink,#fff);
  font:12px/1.4 "IBM Plex Mono",ui-monospace,monospace;padding:6px 8px;border-radius:6px;pointer-events:none;max-width:min(90vw,360px)}
.deep-hud[hidden]{display:none}
.deep-note{color:var(--muted,#aaa);font-size:12px;margin:4px 0}
'''


def deep_panel_html(T):
    """T(key) -> localised text. Buttons + HUD + the honesty line (shown once, plainly)."""
    return (f'<div class="deep-panel" id="deep-panel">'
            f'<button type="button" class="tc-btn tc-btn-ghost" id="deep-dive" aria-pressed="false">{T("deep.dive")}</button>'
            f'<button type="button" class="tc-btn tc-btn-ghost" id="deep-rov" aria-pressed="false">{T("deep.rov")}</button>'
            f'<button type="button" class="tc-btn tc-btn-ghost" id="deep-up">{T("deep.up")}</button>'
            f'<button type="button" class="tc-btn tc-btn-ghost" id="deep-down">{T("deep.down")}</button></div>'
            f'<p class="deep-note" id="deep-note">{T("deep.honesty")}</p>')


DEEP_JS = r'''
/* DEEP_KIT:BEGIN - underwater kit (web/deepkit.py); AUTHORED depths, game camera only */
const DEEP_BUDGET = { calls: 4, props: 900, patchM: 192, res: 48 };
const DEEP_MODES = ['off', 'dive', 'rov'];
const DEEP_SPEED = { vertical: 1.2, rov: 2.5, turn: 1.2 };   // AUTHORED m/s, rad/s
/* index: body lookup by WORLD [east, north]; depthAt -> {d (m), sub (class name), body} | null */
function deepIndex(data) {
  const B = 512, buckets = new Map(), add = (b, w, s, e, n) => {
    for (let i = Math.floor(w / B); i <= Math.floor(e / B); i++) for (let j = Math.floor(s / B); j <= Math.floor(n / B); j++) {
      const k = i + ',' + j; if (!buckets.has(k)) buckets.set(k, []); buckets.get(k).push(b); } };
  for (const b of data.bodies) {
    if (b.grid) { const g = b.grid, o = g.origin_world_m; add(b, o[0], o[1], o[0] + (g.nx - 1) * g.cell_m, o[1] + (g.ny - 1) * g.cell_m); }
    else if (b.channel_grid) { const st = b.channel_grid.stations_world_m, h = b.channel_grid.width_m;
      add(b, Math.min(...st.map((p) => p[0])) - h, Math.min(...st.map((p) => p[1])) - h, Math.max(...st.map((p) => p[0])) + h, Math.max(...st.map((p) => p[1])) + h); }
    else throw new Error('deepkit: body ' + b.id + ' has no grid');
  }
  function inBody(b, e, n) {
    if (b.grid) { const g = b.grid, i = Math.round((e - g.origin_world_m[0]) / g.cell_m), j = Math.round((n - g.origin_world_m[1]) / g.cell_m);
      if (i < 0 || j < 0 || i >= g.nx || j >= g.ny) return null; const d = g.depth_dm[j][i]; if (!d) return null;
      return { d: d / 10, sub: data.substrates[g.substrate[j][i]], body: b }; }
    const c = b.channel_grid, st = c.stations_world_m, half = c.width_m / 2; let best = null;
    for (let k = 0; k < st.length - 1; k++) { const [ax, ay] = st[k], [bx, by] = st[k + 1], dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy || 1;
      const t = Math.max(0, Math.min(1, ((e - ax) * dx + (n - ay) * dy) / L2)), px = ax + dx * t - e, py = ay + dy * t - n, dist = Math.hypot(px, py);
      if (dist <= half && (!best || dist < best.dist)) { const side = (dx * (n - ay) - dy * (e - ax)) >= 0 ? 1 : -1; best = { dist, k: t < 0.5 ? k : k + 1, a: Math.round(2 + side * 2 * dist / half) }; } }
    if (!best) return null; const a = Math.max(0, Math.min(c.across - 1, best.a));
    return { d: c.depth_dm[best.k][a] / 10, sub: data.substrates[c.substrate[best.k][a]], body: b };
  }
  function depthAt(e, n) { const L = buckets.get(Math.floor(e / B) + ',' + Math.floor(n / B)); if (!L) return null;
    for (const b of L) { const r = inBody(b, e, n); if (r) return r; } return null; }
  return { depthAt, bodies: data.bodies.length };
}
/* deepWorld: the registry subset for one world, fail closed (the JS twin of deep_data) - for pages that fetch the
   registry lazily on the first Dive/ROV press instead of embedding it */
function deepWorld(reg, world) {
  for (const k of ['honesty', 'legend', 'substrates', 'bodies', 'source_stamp']) if (!(k in reg)) throw new Error('deepkit: underwater.json has no ' + k);
  const bodies = reg.bodies.filter((b) => b.world === world); if (!bodies.length) throw new Error('deepkit: no underwater bodies for world ' + world);
  return { world, stamp: reg.source_stamp, honesty: reg.honesty, legend: reg.legend, substrates: reg.substrates, bodies };
}
/* the dive / ROV state machine (pure: no THREE, no DOM). st {mode, y, e, n, heading}; ctx {overview, waterState
   ('dry'|'wade'|'swim' from physkit), surface, at(e, n) -> depthAt result | null, eyeE, eyeN}; returns events */
function deepState() { return { mode: 'off', y: 0, e: 0, n: 0, heading: 0 }; }
function deepStep(st, input, dt, ctx) {
  const ev = [], at = ctx.at(st.mode === 'rov' ? st.e : ctx.eyeE, st.mode === 'rov' ? st.n : ctx.eyeN);
  if (ctx.overview) { if (st.mode !== 'off') { st.mode = 'off'; ev.push({ type: 'exit', reason: 'overview' }); } return ev; }
  if (st.mode === 'off') {
    if (input.dive) { if (ctx.waterState === 'swim' && ctx.at(ctx.eyeE, ctx.eyeN)) { Object.assign(st, { mode: 'dive', y: ctx.surface - 0.5, e: ctx.eyeE, n: ctx.eyeN }); ev.push({ type: 'enter', mode: 'dive' }); }
      else ev.push({ type: 'refused', mode: 'dive', reason: 'not-swimming' }); }
    else if (input.rov) { const w = ctx.at(ctx.eyeE, ctx.eyeN) || ctx.at(ctx.eyeE + 6 * Math.sin(ctx.eyeYaw || 0) * -1, ctx.eyeN + 6 * Math.cos(ctx.eyeYaw || 0));
      if (w) { Object.assign(st, { mode: 'rov', y: ctx.surface - 0.3, e: ctx.eyeE, n: ctx.eyeN, heading: 0 }); ev.push({ type: 'enter', mode: 'rov' }); }
      else ev.push({ type: 'refused', mode: 'rov', reason: 'no-water' }); }
    return ev;
  }
  if ((st.mode === 'dive' && input.dive) || (st.mode === 'rov' && input.rov)) { ev.push({ type: 'exit', reason: 'toggle', mode: st.mode }); st.mode = 'off'; return ev; }
  if (st.mode === 'dive') { st.e = ctx.eyeE; st.n = ctx.eyeN;
    if (!at || ctx.waterState !== 'swim') { st.mode = 'off'; ev.push({ type: 'exit', reason: 'left-water' }); return ev; } }
  if (st.mode === 'rov') {
    st.heading += (input.turn || 0) * DEEP_SPEED.turn * dt;
    const f = (input.fwd || 0) * DEEP_SPEED.rov * dt, ne = st.e + Math.sin(st.heading) * f, nn = st.n + Math.cos(st.heading) * f;
    if (f && ctx.at(ne, nn)) { st.e = ne; st.n = nn; } else if (f) ev.push({ type: 'blocked', reason: 'shore' });
  }
  const here = ctx.at(st.e, st.n); if (!here) { st.mode = 'off'; ev.push({ type: 'exit', reason: 'left-water' }); return ev; }
  const top = ctx.surface - 0.2, floor = ctx.surface - here.d + (st.mode === 'rov' ? 0.5 : 0.3);
  st.y += (input.vertical || 0) * DEEP_SPEED.vertical * dt;
  if (st.mode === 'dive' && (input.vertical || 0) > 0 && st.y >= top) { st.mode = 'off'; ev.push({ type: 'exit', reason: 'surfaced' }); return ev; }
  st.y = Math.max(Math.min(floor, top), Math.min(top, st.y));
  return ev;
}
function deepHud(st, ctx) {
  const here = ctx.at(st.e, st.n); if (st.mode === 'off' || !here) return null;
  return { mode: st.mode, depth_m: +(ctx.surface - st.y).toFixed(1), heading_deg: Math.round(((st.heading * 180 / Math.PI) % 360 + 360) % 360),
    alt_m: +(st.y - (ctx.surface - here.d)).toFixed(1), substrate: here.sub, body: here.body.id };
}
function deepMount(o) {
  for (const k of ['THREE', 'scene', 'camera', 'data', 'eye', 'getMode', 'waterState', 'T']) if (!(k in o)) throw new Error('deepkit: deepMount needs ' + k);
  const { THREE, scene, camera, data } = o, idx = deepIndex(data), st = deepState();
  const surface = data.bodies[0].surface_y_m; let targets = [], sampled = new Set();
  const SUBCOL = { mudflat: [0.36, 0.31, 0.24], mud: [0.29, 0.25, 0.2], sand: [0.62, 0.56, 0.42], shell: [0.72, 0.7, 0.62], riprap: [0.42, 0.42, 0.44] };
  /* caustic-ish light: one small canvas pattern scrolled over the seafloor (no extra draw call) */
  const cv = document.createElement('canvas'); cv.width = cv.height = 64; const cx = cv.getContext('2d'); cx.fillStyle = '#9a9a9a'; cx.fillRect(0, 0, 64, 64);
  cx.strokeStyle = '#ffffff'; cx.globalAlpha = 0.35; for (let i = 0; i < 9; i++) { cx.beginPath(); cx.arc((i * 23) % 64, (i * 37) % 64, 6 + (i * 7) % 11, 0, 6.28); cx.stroke(); }
  const tex = new THREE.CanvasTexture(cv); tex.wrapS = tex.wrapT = THREE.RepeatWrapping; tex.repeat.set(24, 24);
  const R = DEEP_BUDGET.res, geo = new THREE.PlaneGeometry(DEEP_BUDGET.patchM, DEEP_BUDGET.patchM, R, R).rotateX(-Math.PI / 2);
  geo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(geo.attributes.position.count * 3), 3));
  const floor = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ vertexColors: true, map: tex }));
  floor.visible = false; floor.frustumCulled = false; floor.name = 'deep-floor'; scene.add(floor);
  const fam = {}, dummy = new THREE.Object3D();
  const mk = (name, g, color) => { const m = new THREE.InstancedMesh(g, new THREE.MeshBasicMaterial({ color }), DEEP_BUDGET.props); m.count = 0; m.visible = false; m.frustumCulled = false; m.name = 'deep-' + name; scene.add(m); fam[name] = m; };
  mk('eelgrass', new THREE.PlaneGeometry(0.18, 1.3).translate(0, 0.65, 0), 0x3f7a3a);
  mk('oyster', new THREE.DodecahedronGeometry(0.25, 0), 0x8a8474);
  mk('riprap', new THREE.DodecahedronGeometry(0.45, 0), 0x6b6b6e);
  let patchKey = null, savedFog = null, savedBg = null, under = false;
  function buildPatch(e0, n0) {
    const p = geo.attributes.position, c = geo.attributes.color, half = DEEP_BUDGET.patchM / 2;
    floor.position.set(e0, 0, -n0);
    for (let i = 0; i < p.count; i++) { const e = e0 + p.getX(i), n = n0 - p.getZ(i), r = idx.depthAt(e, n);
      p.setY(i, r ? surface - r.d : surface - 0.05); const col = r ? SUBCOL[r.sub] : SUBCOL.mud; c.setXYZ(i, col[0], col[1], col[2]); }
    p.needsUpdate = c.needsUpdate = true; geo.computeBoundingSphere();
    const counts = { eelgrass: 0, oyster: 0, riprap: 0 };
    for (const b of data.bodies) for (const h of b.habitats) {
      const [he, hn] = h.world_m; if (Math.abs(he - e0) > half + h.r_m || Math.abs(hn - n0) > half + h.r_m) continue;   // a patch overlapping the seafloor square
      const m = fam[h.kind]; if (!m) throw new Error('deepkit: unknown habitat ' + h.kind);
      for (let k = 0; k < h.count && m.count < DEEP_BUDGET.props; k++) {
        const a = k * 2.399, rr = h.r_m * Math.sqrt((k + 0.5) / h.count), e = he + Math.cos(a) * rr, n = hn + Math.sin(a) * rr, r = idx.depthAt(e, n); if (!r) continue;
        dummy.position.set(e, surface - r.d, -n); dummy.rotation.set(0, a, 0); dummy.scale.setScalar(0.8 + (k % 5) * 0.1); dummy.updateMatrix();
        m.setMatrixAt(m.count++, dummy.matrix); counts[h.kind]++; }
    }
    for (const m of Object.values(fam)) m.instanceMatrix.needsUpdate = true;
    return counts;
  }
  const keys = new Set(), press = { dive: o.initial === 'dive', rov: o.initial === 'rov' }, hold = { up: 0, down: 0 };
  addEventListener('keydown', (e) => { if (e.target.closest && e.target.closest('input,textarea,select')) return; keys.add(e.key.toLowerCase()); });
  addEventListener('keyup', (e) => keys.delete(e.key.toLowerCase()));
  const btn = (id) => document.getElementById(id);
  if (btn('deep-dive')) btn('deep-dive').addEventListener('click', () => { press.dive = true; });
  if (btn('deep-rov')) btn('deep-rov').addEventListener('click', () => { press.rov = true; });
  for (const [id, k] of [['deep-up', 'up'], ['deep-down', 'down']]) { const b = btn(id); if (!b) continue;
    b.addEventListener('pointerdown', () => { hold[k] = 1; }); for (const x of ['pointerup', 'pointerleave', 'pointercancel']) b.addEventListener(x, () => { hold[k] = 0; }); }
  const hudEl = document.createElement('div'); hudEl.className = 'deep-hud'; hudEl.hidden = true; hudEl.id = 'deep-hud';
  (o.hudParent || document.body).appendChild(hudEl);
  let lastEvents = [], info = { calls: 0, props: 0 }, msg = '';
  const ctx = () => ({ overview: false, waterState: o.waterState(), surface, at: idx.depthAt, eyeE: o.eye.x, eyeN: -o.eye.z, eyeYaw: o.eye.yaw });
  function update(dt, overview) {
    const c = ctx(); c.overview = overview;
    const input = { dive: press.dive, rov: press.rov, vertical: (keys.has('r') || hold.up ? 1 : 0) - (keys.has('f') || hold.down ? 1 : 0),
      fwd: (keys.has('i') ? 1 : 0) - (keys.has('k') ? 1 : 0), turn: (keys.has('l') ? 1 : 0) - (keys.has('j') ? 1 : 0) };
    press.dive = press.rov = false;
    const ev = deepStep(st, input, dt, c); if (ev.length) lastEvents = ev;
    for (const e of ev) if (e.type === 'refused') { msg = o.T('deep.refused'); }
    if (btn('deep-dive')) btn('deep-dive').setAttribute('aria-pressed', String(st.mode === 'dive'));
    if (btn('deep-rov')) btn('deep-rov').setAttribute('aria-pressed', String(st.mode === 'rov'));
    const on = st.mode !== 'off';
    if (on) { camera.position.set(st.e, st.y, -st.n); if (st.mode === 'rov') camera.rotation.set(-0.25, -st.heading + Math.PI, 0, 'YXZ'); }
    const wasUnder = under; under = on && camera.position.y < surface;
    if (under && !wasUnder) { savedFog = scene.fog; savedBg = scene.background; }
    if (under) { const lk = st.mode !== 'off' ? idx.depthAt(st.e, st.n) : null; const look = lk ? lk.body.look : null;
      if (look) { const col = new THREE.Color(look.tint); if (!(scene.fog && scene.fog.isFogExp2)) scene.fog = new THREE.FogExp2(col, look.fog_density); scene.fog.color.copy(col); scene.fog.density = look.fog_density; scene.background = col; }
      const k = Math.round(st.e / 64) + ',' + Math.round(st.n / 64); if (k !== patchKey) { patchKey = k; buildPatch(Math.round(st.e / 64) * 64, Math.round(st.n / 64) * 64); }
      tex.offset.x = (performance.now() / 9000) % 1; tex.offset.y = (performance.now() / 13000) % 1; }
    else if (wasUnder) { scene.fog = savedFog; scene.background = savedBg; }
    floor.visible = under; for (const m of Object.values(fam)) m.visible = under && m.count > 0;
    info = { calls: (floor.visible ? 1 : 0) + Object.values(fam).filter((m) => m.visible).length, props: Object.values(fam).reduce((a, m) => a + m.count, 0) };
    for (const t of targets) { if (!on || sampled.has(t.id)) continue; if (Math.hypot(t.world_m[0] - st.e, t.world_m[1] - st.n) < t.r_m) { sampled.add(t.id); lastEvents = [{ type: 'target', id: t.id }]; if (o.onTarget) o.onTarget(t); } }
    const h = deepHud(st, c); hudEl.hidden = !h;
    if (h) hudEl.textContent = `${h.mode.toUpperCase()} · ${o.T('deep.hud.depth')} ${h.depth_m} m · ${o.T('deep.hud.heading')} ${h.heading_deg}° · ${o.T('deep.hud.alt')} ${h.alt_m} m · ${o.T('deep.hud.substrate')} ${h.substrate} · AUTHORED`;
    const note = btn('deep-note'); if (note && msg) { note.dataset.msg = msg; }
    return on;
  }
  /* RESTORE hook: monitoring targets [{id, world_m [e, n], r_m, label}] - reached by dive/ROV -> onTarget(t) (play only) */
  function setTargets(list) { for (const t of list) for (const k of ['id', 'world_m', 'r_m']) if (!(k in t)) throw new Error('deepkit: target needs ' + k); targets = list.slice(); sampled = new Set(); }
  return { update, state: st, hud: () => deepHud(st, ctx()), setTargets, depthAt: idx.depthAt,
    stats: () => ({ mode: st.mode, under, calls: info.calls, props: info.props, budget: DEEP_BUDGET, events: lastEvents.map((e) => e.type + ':' + (e.reason || e.mode || e.id || '')), sampled: [...sampled], bodies: idx.bodies }),
    force(mode, e, n, y) { Object.assign(st, { mode, e, n, y }); patchKey = null; } };
}
/* DEEP_KIT:END */
'''


def deep_inline():
    s = DEEP_JS
    a, b = s.index('/* DEEP_KIT:BEGIN'), s.index('/* DEEP_KIT:END */') + len('/* DEEP_KIT:END */')
    return s[a:b]
