#!/usr/bin/env python3
"""web/robokit.py - embeddable robotics sandbox (ROBOLAB, wave 11). Contract: $SP/ROBOTICS_CONTRACT.md v1.

What it does: spawns one of the AUTHORED robot embodiments of robotics/registry/robotics.json (wheeled rover,
arm-on-base, ROV) in a small AUTHORED arena set beside a world (the parish world, the Bay world, or the Robotics
lab page), lets a learner teleoperate it (keyboard W/A/S/D + arrows, G grip, R/F depth; touch pad buttons >= 44 px),
records the run as a training/ `world-teleop` episode when the learner pressed Record, and runs the env's SCRIPTED
reference policy on the SAME env and seed so the two can be compared side by side.

Honesty: the arena, obstacles and robots are AUTHORED; the dynamics are SCHEMATIC unicycle kinematics; the
reference policy is SCRIPTED (hand-written, deterministic, seeded - no model, no network). Nothing is trained here
and no model has been trained on these episodes. Episodes are device-local (localStorage `tc-training`, the SAME
key, toggle and rolling cap training/ declares) and carry no personal data: env-local metres, velocities, AUTHORED
object ids and control inputs only. Classroom / K-12 mode (?classroom=1 or the page's class flag) offers no
recording at all.

Python API (fail closed):
    from robokit import robo_data, robo_i18n_keys, ROBO_CSS, ROBO_JS, robo_panel_html, RoboKitError
    from robokit import robo_catalog, robo_world_T, robo_world_tail   # world pages: own catalogue, own [data-robo-i18n]
    data = robo_data()                     # the JSON the JS reads: {robo: envs/embodiments/teleop, train: storage+world_teleop}
    html = robo_panel_html(T, world)       # T(key) -> escaped text with data-i18n; world in ('parishes','bay','lab')
    JS:  ROBO_JS defines RoboCore (pure: no DOM) and roboMount(root, data, {world, classroom}) -> window.__robokit
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
WORLDS = ('parishes', 'bay', 'lab')


class RoboKitError(Exception):
    pass


def _need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise RoboKitError(f'robokit: {where} has no field {k!r}')
    return d[k]


def robo_data():
    rp, tp = ROOT / 'robotics/registry/robotics.json', ROOT / 'training/registry/training.json'
    if not rp.exists():
        raise RoboKitError('robokit: robotics/registry/robotics.json is not built (python3 robotics/build.py)')
    reg, tr = json.loads(rp.read_text()), json.loads(tp.read_text())
    amb = json.loads((ROOT / 'ambient/registry/ambient.json').read_text())
    envs = {k: v for k, v in _need(reg, 'envs', 'robotics.json').items() if _need(v, 'runner', k) == 'robokit'}
    if not envs:
        raise RoboKitError('robokit: robotics.json declares no robokit env')
    litter = {k: _need(v, 'color', f'ambient litter {k}') for k, v in _need(amb, 'litter', 'ambient.json').items()}
    return {
        'robo': {'schema': _need(reg, 'schema', 'robotics.json'), 'stamp': _need(reg, 'source_stamp', 'robotics.json'),
                 'envs': envs, 'embodiments': _need(reg, 'embodiments', 'robotics.json'),
                 'teleop': _need(reg, 'teleop', 'robotics.json'), 'litter_colors': litter},
        'train': {'storage': _need(tr, 'storage', 'training.json'),
                  'world_teleop': _need(tr, 'world_teleop', 'training.json'),
                  'kind': _need(tr, 'world_episode_kinds', 'training.json')['world-teleop'],
                  'pack': _need(tr, 'pack', 'training.json')},
    }


ROBO_I18N_KEYS = ['robo.panel', 'robo.env', 'robo.seed', 'robo.reset', 'robo.record', 'robo.stop', 'robo.ref',
                  'robo.compare', 'robo.you', 'robo.refpol', 'robo.return', 'robo.steps', 'robo.success',
                  'robo.kept', 'robo.honesty', 'robo.classroom', 'robo.off', 'robo.hint', 'robo.t.fwd', 'robo.t.back',
                  'robo.t.left', 'robo.t.right', 'robo.t.grip', 'robo.t.up', 'robo.t.down', 'robo.yes', 'robo.no',
                  'robo.export', 'robo.recording', 'robo.done']


def robo_i18n_keys():
    return list(ROBO_I18N_KEYS)


def robo_catalog():
    """{locale: {dir, strings: {robo.* kit key: text}}} for the 8 locales - fail closed on a missing key. World pages embed
    this as #robo-i18n and robokit translates its own [data-robo-i18n] nodes, so the host page's catalogue (and its
    exactly-the-used-keys check) never carries robo.* keys."""
    out = {}
    for f in sorted((ROOT / 'i18n/locales').glob('*.json')):
        c = json.loads(f.read_text(encoding='utf-8'))
        st = _need(c, 'strings', f.name)
        miss = [k for k in ROBO_I18N_KEYS if not isinstance(st.get(k), str) or not st[k].strip()]
        if miss:
            raise RoboKitError(f'robokit: locale {f.name} is missing {miss[:5]}')
        out[_need(c, 'locale', f.name)] = {'dir': _need(c, 'dir', f.name), 'strings': {k: st[k] for k in ROBO_I18N_KEYS}}
    if len(out) != 8:
        raise RoboKitError(f'robokit: expected 8 locales, found {sorted(out)}')
    return out


def robo_world_T(k):
    """the translator world pages pass to robo_panel_html: English text now, re-translated at run time by robokit"""
    import html as _h
    return f'<span data-robo-i18n="{k}">{_h.escape(robo_catalog()["en"]["strings"][k])}</span>'


def robo_world_tail(world):
    """everything a world page appends before </body>: css, data, catalogue, kit, and the mount (after the page's own
    module has set <html lang>, i.e. on DOMContentLoaded)"""
    if world not in WORLDS:
        raise RoboKitError(f'robokit: unknown world {world!r}')
    j = lambda x: json.dumps(x, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return (f'<style id="robo-css">{ROBO_CSS}</style>\n<script type="application/json" id="robo-data">{j(robo_data())}</script>\n'
            f'<script type="application/json" id="robo-i18n">{j(robo_catalog())}</script>\n<script id="robo-kit">{ROBO_JS}</script>\n'
            '<script id="robo-mount">document.addEventListener("DOMContentLoaded", function () {\n'
            '  var root = document.getElementById("robo"), cat = JSON.parse(document.getElementById("robo-i18n").textContent);\n'
            '  var L = cat[document.documentElement.lang] || cat.en, t = function (k) { var s = L.strings[k];\n'
            '    if (typeof s !== "string") throw new Error("robo i18n: no " + k); return s; };\n'
            '  root.querySelectorAll("[data-robo-i18n]").forEach(function (el) { el.textContent = t(el.getAttribute("data-robo-i18n")); });\n'
            '  var q = new URLSearchParams(location.search);\n'
            f'  roboMount(root, JSON.parse(document.getElementById("robo-data").textContent), {{ world: "{world}", '
            'classroom: q.has("classroom") || q.has("class"), t: t });\n});</script>\n')


ROBO_CSS = r'''
.robo{border:1px solid var(--tc-line,#28353A);border-radius:10px;padding:12px;background:var(--tc-panel,#182023);color:var(--tc-ink,#E8EDEC);min-inline-size:0}
.robo h2,.robo h3{margin:0 0 8px;font-size:18px}
.robo-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 8px}
.robo-row select,.robo-row button,.robo-pad button{min-block-size:44px;min-inline-size:44px;font:inherit;color:var(--tc-ink,#E8EDEC);background:var(--tc-raised,#1E282B);border:1px solid var(--tc-line,#28353A);border-radius:8px;padding:0 12px;cursor:pointer}
.robo-row button[aria-pressed="true"]{background:var(--tc-amber,#E8A33D);color:var(--tc-amber-ink,#12181B)}
.robo-row button:disabled{opacity:.6;cursor:not-allowed}
.robo-stage{display:flex;flex-wrap:wrap;gap:12px;align-items:flex-start}
.robo canvas{inline-size:min(100%,420px);aspect-ratio:1/1;background:#0f1a1c;border-radius:8px;touch-action:none;outline-offset:2px}
.robo-pad{display:grid;grid-template-columns:repeat(3,minmax(48px,auto));gap:6px;touch-action:none;user-select:none}
.robo-pad button{font-size:15px}
.robo-pad [data-slot="fwd"]{grid-column:2}.robo-pad [data-slot="left"]{grid-column:1;grid-row:2}
.robo-pad [data-slot="right"]{grid-column:3;grid-row:2}.robo-pad [data-slot="back"]{grid-column:2;grid-row:3}
.robo-pad [data-slot="grip"],.robo-pad [data-slot="up"]{grid-column:1;grid-row:3}.robo-pad [data-slot="down"]{grid-column:3;grid-row:3}
.robo-hud{font:13px/1.5 ui-monospace,monospace;color:var(--tc-muted,#93A3A6);overflow-wrap:anywhere;min-block-size:3em}
.robo table{border-collapse:collapse;font-size:14px}
.robo th,.robo td{border-block-end:1px solid var(--tc-line,#28353A);padding:4px 8px;text-align:start}
.robo .robo-honest{color:var(--tc-muted,#93A3A6);font-size:13px;margin:8px 0 0}
'''


def robo_panel_html(T, world):
    if world not in WORLDS:
        raise RoboKitError(f'robokit: unknown world {world!r}')
    return (f'<section class="robo" id="robo" data-robo-world="{world}" aria-labelledby="robo-h">'
            f'<h2 id="robo-h">{T("robo.panel")}</h2>'
            f'<div class="robo-row"><label>{T("robo.env")} <select id="robo-env"></select></label>'
            f'<label>{T("robo.seed")} <select id="robo-seed"></select></label>'
            f'<button type="button" id="robo-reset">{T("robo.reset")}</button>'
            f'<button type="button" id="robo-rec" aria-pressed="false">{T("robo.record")}</button>'
            f'<button type="button" id="robo-ref">{T("robo.ref")}</button>'
            f'<button type="button" id="robo-export">{T("robo.export")}</button></div>'
            f'<p class="robo-hud" id="robo-hint">{T("robo.hint")}</p>'
            f'<div class="robo-stage"><canvas id="robo-canvas" width="420" height="420" tabindex="0" '
            f'aria-label="robot arena"></canvas>'
            f'<div><div class="robo-pad" id="robo-pad"></div><p class="robo-hud" id="robo-hud" aria-live="polite"></p>'
            f'<h3>{T("robo.compare")}</h3><table id="robo-cmp"><thead><tr><th></th><th>{T("robo.return")}</th>'
            f'<th>{T("robo.steps")}</th><th>{T("robo.success")}</th></tr></thead><tbody>'
            f'<tr data-row="human"><th>{T("robo.you")}</th><td>-</td><td>-</td><td>-</td></tr>'
            f'<tr data-row="ref"><th>{T("robo.refpol")}</th><td>-</td><td>-</td><td>-</td></tr></tbody></table>'
            f'<p class="robo-hud" id="robo-kept"></p></div></div>'
            f'<p class="robo-honest">{T("robo.honesty")}</p>'
            f'<p class="robo-honest" id="robo-class" hidden>{T("robo.classroom")}</p></section>')


ROBO_JS = r'''
/* ROBOKIT_CORE:BEGIN - pure env core (no DOM): AUTHORED arena, SCHEMATIC unicycle kinematics, SCRIPTED policy */
const RoboCore = (() => {
  function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  const wrap = (a) => { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; };
  const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
  const hash = (s) => { let h = 2166136261; for (const c of s) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; };
  function field(env, name) { const f = env.action.fields.find((x) => x.name === name); if (!f) throw new Error('robokit: action field ' + name); return f; }
  function layout(env, seed) {
    const rnd = mulberry32((hash(env.id) ^ Math.imul(seed, 2654435761)) >>> 0), H = env.world.arena_half_m, o = env.objects;
    const obst = [], items = [], gates = [], targets = []; let bin = null;
    const free = (e, n, clear) => Math.hypot(e, n) > 3.5 && Math.abs(e) < H - 1.5 && Math.abs(n) < H - 1.5
      && obst.every((b) => Math.hypot(b.e - e, b.n - n) > b.r + clear) && items.concat(targets, gates).every((b) => Math.hypot(b.e - e, b.n - n) > clear + 1)
      && (!bin || Math.hypot(bin.e - e, bin.n - n) > clear + 1.5);
    const place = (clear) => { for (let k = 0; k < 400; k++) { const e = (rnd() * 2 - 1) * (H - 2), n = (rnd() * 2 - 1) * (H - 2); if (free(e, n, clear)) return [e, n]; } throw new Error('robokit: layout could not place an object'); };
    if (o.gates) for (let i = 0, pe = 0, pn = 0; i < o.gates; i++) { const a = (i + 0.5) / o.gates * 2 * Math.PI + (rnd() - 0.5) * 0.4, R = 9 + rnd() * 4;
      const e = -Math.sin(a) * R, n = Math.cos(a) * R, L = Math.hypot(e - pe, n - pn), ue = (e - pe) / L, un = (n - pn) / L;
      gates.push({ id: 'gate-' + (i + 1), e, n, a });   // the two cones flank the line from the previous gate (or the spawn)
      for (const s of [-1, 1]) obst.push({ id: 'cone-' + (i + 1) + (s < 0 ? 'a' : 'b'), e: e - un * 1.8 * s, n: n + ue * 1.8 * s, r: 0.3 });
      pe = e; pn = n; }
    if (o.bin) { const p = place(2); bin = { id: 'bin', e: p[0], n: p[1] }; }
    for (let i = 0; i < (o.obstacles || 0); i++) { const r = 0.8 + rnd() * 0.7, p = place(r + 2.2); obst.push({ id: 'rock-' + (i + 1), e: p[0], n: p[1], r }); }
    const types = o.litter_types || [];
    for (let i = 0; i < (o.litter || 0); i++) { const p = place(1.2); items.push({ id: 'litter-' + (i + 1), e: p[0], n: p[1], type: types[Math.floor(rnd() * types.length)], taken: false, binned: false }); }
    for (let i = 0; i < (o.targets || 0); i++) { const p = place(1.5); targets.push({ id: 'target-' + (i + 1), e: p[0], n: p[1], d: 1 + Math.round(rnd() * 60) / 10, visited: false }); }
    return { obst, items, gates, targets, bin };
  }
  function reset(env, emb, seed) {
    if (!env.seeds.includes(seed)) throw new Error('robokit: seed ' + seed + ' is not declared for ' + env.id);
    const L = layout(env, seed);
    return { env, emb, seed, e: 0, n: 0, yaw: 0, v: 0, w: 0, depth: 0, step: 0, next: 0, carrying: null, contact: false,
      backoff: 0, ret: 0, terms: Object.fromEntries(env.reward.map((r) => [r.term, 0])), done: null, collected: 0, ...L };
  }
  function goal(st) {
    const env = st.env;
    if (env.objects.gates) return st.gates[st.next] || null;
    if (env.objects.bin && st.carrying) return st.bin;
    const open = st.items.filter((x) => !x.taken).concat(st.targets.filter((x) => !x.visited));
    let best = null, bd = Infinity; for (const x of open) { const d = Math.hypot(x.e - st.e, x.n - st.n); if (d < bd) { bd = d; best = x; } }
    return best;
  }
  function near(st) {
    const all = st.obst.concat(st.items.filter((x) => !x.taken), st.targets.filter((x) => !x.visited), st.gates.slice(st.next), st.bin ? [st.bin] : []);
    return all.map((x) => [x.id, Math.hypot(x.e - st.e, x.n - st.n)]).filter((p) => p[1] <= 6).sort((a, b) => a[1] - b[1] || (a[0] < b[0] ? -1 : 1)).slice(0, 4).map((p) => p[0]);
  }
  function obs(st) {
    const g = goal(st), o = { pose_e: st.e, pose_n: st.n, yaw: st.yaw, v: st.v, w: st.w,
      target_bearing: g ? wrap(Math.atan2(-(g.e - st.e), g.n - st.n) - st.yaw) : 0, target_dist: g ? Math.hypot(g.e - st.e, g.n - st.n) : 0, near: near(st) };
    if (st.env.objects.litter && !st.env.objects.bin) o.collected = st.collected;
    if (st.env.objects.bin) { o.carrying = st.carrying ? 1 : 0; o.binned = st.collected; }
    if (st.env.objects.targets) { o.depth = st.depth; o.target_depth = g ? g.d : 0; o.visited = st.collected; }
    if (st.env.objects.gates) o.gates_taken = st.next;
    return o;
  }
  function add(st, term, k) { const r = st.env.reward.find((x) => x.term === term); if (!r) throw new Error('robokit: reward term ' + term); st.terms[term] += r.weight * k; st.ret += r.weight * k; return r.weight * k; }
  function step(st, a) {
    if (st.done) return { obs: obs(st), reward: 0, done: st.done };
    const env = st.env, dt = env.episode_cap.dt_s, lim = st.emb.limits, R = st.emb.radius_m, H = env.world.arena_half_m;
    const fv = field(env, 'v'), fw = field(env, 'w'), r0 = st.ret;
    st.v = clamp(Number(a.v) || 0, fv.low, fv.high); st.w = clamp(Number(a.w) || 0, fw.low, fw.high);
    st.yaw = wrap(st.yaw + st.w * dt);
    const ne = st.e - Math.sin(st.yaw) * st.v * dt, nn = st.n + Math.cos(st.yaw) * st.v * dt;
    const hit = Math.abs(ne) > H - R || Math.abs(nn) > H - R || st.obst.some((b) => Math.hypot(b.e - ne, b.n - nn) < b.r + R);
    if (hit) { if (!st.contact) add(st, 'collision', 1); st.contact = true; st.v = 0; } else { st.contact = false; st.e = ne; st.n = nn; }
    if (env.objects.targets) { const fz = field(env, 'vz'); st.depth = clamp(st.depth + clamp(Number(a.vz) || 0, fz.low, fz.high) * dt, 0, lim.depth_max_m); }
    add(st, 'time', 1);
    if (env.objects.gates) { const g = st.gates[st.next]; if (g && Math.hypot(g.e - st.e, g.n - st.n) < 1.2) { st.next++; st.collected = st.next; add(st, 'gate', 1); } }
    else if (env.objects.bin) {
      if (Number(a.grip) >= 0.5) {
        if (!st.carrying) { const it = st.items.find((x) => !x.taken && Math.hypot(x.e - st.e, x.n - st.n) < R + lim.reach_m); if (it) { it.taken = true; st.carrying = it; add(st, 'pickup', 1); } }
        else if (Math.hypot(st.bin.e - st.e, st.bin.n - st.n) < R + lim.reach_m + 0.3) { st.carrying.binned = true; st.carrying = null; st.collected++; add(st, 'deposit', 1); }
      }
    } else if (env.objects.litter) { for (const it of st.items) if (!it.taken && Math.hypot(it.e - st.e, it.n - st.n) < 0.9) { it.taken = true; st.collected++; add(st, 'pickup', 1); } }
    else if (env.objects.targets) { for (const t of st.targets) if (!t.visited && Math.hypot(t.e - st.e, t.n - st.n) < 1.5 && Math.abs(t.d - st.depth) < 1.0) { t.visited = true; st.collected++; add(st, 'visit', 1); } }
    st.step++;
    const total = env.objects.gates || env.objects.litter || env.objects.targets;
    if (st.collected >= total) st.done = env.termination[0].id; else if (st.step >= env.episode_cap.steps) st.done = 'cap';
    return { obs: obs(st), reward: st.ret - r0, done: st.done };
  }
  /* SCRIPTED reference policy: a potential field (unit pull to the goal, push from obstacles and walls within 2.5 m),
     speed falling with heading error, a short reverse after a strike; grip in reach; depth proportional. Deterministic. */
  function policy(st) {
    const o = obs(st), lim = st.emb.limits, g = goal(st), H = st.env.world.arena_half_m;
    // steer on a potential field: unit pull toward the goal + a push away from every obstacle and wall within 2.5 m
    let fe = 0, fn = 0;
    if (g) { const L = Math.max(1e-6, o.target_dist); fe = (g.e - st.e) / L; fn = (g.n - st.n) / L; }
    for (const ob of st.obst) { const de = st.e - ob.e, dn = st.n - ob.n, L = Math.hypot(de, dn), c = L - ob.r - st.emb.radius_m;
      if (c < 2.5 && L > 1e-6 && (!g || c < o.target_dist)) { const k = 1.6 * (2.5 - c) / 2.5; fe += de / L * k; fn += dn / L * k; } }
    for (const [ax, sgn] of [['e', 1], ['e', -1], ['n', 1], ['n', -1]]) { const c = H - sgn * st[ax] - st.emb.radius_m;
      if (c < 2.5) { const k = -sgn * 1.6 * (2.5 - c) / 2.5; if (ax === 'e') fe += k; else fn += k; } }
    const b = wrap(Math.atan2(-fe, fn) - st.yaw);
    let w = clamp(2.2 * b, -lim.w_max_rads, lim.w_max_rads), v = lim.v_max_ms * Math.max(0, Math.cos(b)) ** 2;
    if (o.target_dist < 2) v = Math.min(v, 0.4 + 0.4 * o.target_dist);
    if (st.contact && !st.backoff) st.backoff = 6;   // struck: reverse 0.6 s, then the field steers around
    if (st.backoff) { st.backoff--; v = lim.v_min_ms * 0.6; w = 0; }
    const a = { v, w };
    if (st.env.objects.bin) a.grip = o.target_dist < st.emb.radius_m + lim.reach_m ? 1 : 0;
    if (st.env.objects.targets) { a.vz = clamp(1.5 * (o.target_depth - o.depth), -lim.vz_max_ms, lim.vz_max_ms); if (Math.abs(o.target_depth - o.depth) > 1 && o.target_dist < 3) a.v = Math.min(a.v, 0.3); }
    return a;
  }
  function vec(st, a) { return st.env.action.fields.map((f) => Math.round((Number(a[f.name]) || 0) * 1000) / 1000); }
  function sample(st, a) {
    const r3 = (x) => Math.round(x * 1000) / 1000, pose = [r3(st.e), r3(st.n), r3(st.yaw)];
    if (st.env.objects.targets) pose.push(r3(st.depth));
    return { i: st.step, pose, vel: [r3(st.v), r3(st.w)], near: near(st), a: vec(st, a) };
  }
  function episode(st, actor, world, samples, T) {
    return { kind: 'world-teleop', v: T.kind.v, env: st.env.id, embodiment: st.emb.id, world, actor, seed: st.seed,
      hz: T.world_teleop.sample_hz, dt_s: st.env.episode_cap.dt_s, steps: st.step, samples,
      outcome: { done: st.done || 'stopped', success: !!st.done && st.done !== 'cap', return: Math.round(st.ret * 1000) / 1000,
        terms: Object.fromEntries(Object.entries(st.terms).map(([k, x]) => [k, Math.round(x * 1000) / 1000])), collected: st.collected } };
  }
  function rollout(env, emb, seed, T, world) {
    const st = reset(env, emb, seed), every = Math.round(1 / (T.world_teleop.sample_hz * env.episode_cap.dt_s)), samples = [];
    while (!st.done) { const a = policy(st); if (st.step % every === 0 && samples.length < T.world_teleop.max_samples) samples.push(sample(st, a)); step(st, a); }
    return episode(st, 'scripted-reference', world, samples, T);
  }
  return { mulberry32, layout, reset, step, obs, policy, sample, episode, rollout, near };
})();
/* ROBOKIT_CORE:END */

/* ROBOKIT_UI:BEGIN - teleop, record, compare. roboMount(root, data, {world, classroom, t}) */
function roboMount(root, data, opt) {
  const R = data.robo, D_TRAIN = data.train, world = opt.world, $ = (s) => root.querySelector(s);
  const t = opt.t || ((k) => k);
  const TR_KEY_W = D_TRAIN.storage.key, TR_ON = D_TRAIN.storage.toggle_key, CAP = D_TRAIN.storage.cap;
  const HZ = D_TRAIN.world_teleop.sample_hz, MAXS = D_TRAIN.world_teleop.max_samples;
  const classroom = !!opt.classroom;
  let env = null, emb = null, st = null, rec = false, samples = [], held = {}, acc = 0, last = 0, kept = 0, lastHuman = null;
  const sel = $('#robo-env'), seedSel = $('#robo-seed'), cv = $('#robo-canvas'), g = cv.getContext('2d');
  for (const e of Object.values(R.envs)) { const o = document.createElement('option'); o.value = e.id; o.textContent = e.name; sel.appendChild(o); }
  const baseOn = () => { try { return localStorage.getItem(TR_ON) !== '0'; } catch (e) { return true; } };
  function keep(ep) {
    if (classroom || !baseOn()) return false;
    let log = []; try { const a = JSON.parse(localStorage.getItem(TR_KEY_W)); if (Array.isArray(a)) log = a; } catch (e) { /* blocked store */ }
    log.push({ t: new Date().toISOString(), ...ep }); while (log.length > CAP) log.shift();
    try { localStorage.setItem(TR_KEY_W, JSON.stringify(log)); } catch (e) { /* private mode: not kept */ return false; }
    kept++; return true;
  }
  function pad() {
    const p = $('#robo-pad'); p.textContent = '';
    for (const b of R.teleop[emb.id].touch) {
      const el = document.createElement('button'); el.type = 'button'; el.dataset.slot = b.id; el.textContent = t(b.label_key);
      const on = (ev) => { ev.preventDefault(); held[b.id] = true; }, off = () => { held[b.id] = false; };
      el.addEventListener('pointerdown', on); el.addEventListener('pointerup', off); el.addEventListener('pointerleave', off); el.addEventListener('pointercancel', off);
      p.appendChild(el);
    }
  }
  function load(id, seed) {
    env = R.envs[id]; emb = R.embodiments[env.embodiments[0]];
    seedSel.textContent = ''; for (const s of env.seeds) { const o = document.createElement('option'); o.value = s; o.textContent = s; seedSel.appendChild(o); }
    seedSel.value = String(seed || env.seeds[0]); sel.value = id;
    st = RoboCore.reset(env, emb, Number(seedSel.value)); samples = []; setRec(false); pad(); draw(); hud();
  }
  function setRec(on) { rec = on && !classroom; $('#robo-rec').setAttribute('aria-pressed', String(rec)); $('#robo-rec').textContent = t(rec ? 'robo.stop' : 'robo.record'); }
  const keys = new Set();
  /* keys are read only while focus is inside this panel (click the arena), and they stop here - a world page's own
     walk / drive keys never see them, and robokit never sees the world's */
  const DRIVE = ['w', 'a', 's', 'd', 'g', ' ', 'r', 'f', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'];
  root.addEventListener('keydown', (ev) => { const k = ev.key.toLowerCase(); if (!DRIVE.includes(k) || ev.target.tagName === 'SELECT') return;
    keys.add(k); ev.stopPropagation(); if (ev.target === cv || k.startsWith('arrow') || k === ' ') ev.preventDefault(); });
  root.addEventListener('keyup', (ev) => { keys.delete(ev.key.toLowerCase()); ev.stopPropagation(); });
  root.addEventListener('focusout', (ev) => { if (!root.contains(ev.relatedTarget)) keys.clear(); });
  function action() {
    const L = emb.limits, f = (n) => keys.has(n);
    const a = { v: (f('w') || f('arrowup') || held.fwd) ? L.v_max_ms : (f('s') || f('arrowdown') || held.back) ? L.v_min_ms : 0,
      w: ((f('a') || f('arrowleft') || held.left) ? L.w_max_rads : 0) - ((f('d') || f('arrowright') || held.right) ? L.w_max_rads : 0) };
    if (env.objects.bin) a.grip = (f('g') || f(' ') || held.grip) ? 1 : 0;
    if (env.objects.targets) a.vz = ((f('f') || held.down) ? L.vz_max_ms : 0) - ((f('r') || held.up) ? L.vz_max_ms : 0);
    return a;
  }
  const every = () => Math.round(1 / (HZ * env.episode_cap.dt_s));
  function tick(a) {
    if (st.done) return;
    if (rec && st.step % every() === 0 && samples.length < MAXS) samples.push(RoboCore.sample(st, a));
    RoboCore.step(st, a);
    if (st.done) finish('human');
  }
  function row(which, ep) { const r = root.querySelector(`[data-row="${which}"]`).children;
    r[1].textContent = ep.outcome.return.toFixed(2); r[2].textContent = ep.steps; r[3].textContent = t(ep.outcome.success ? 'robo.yes' : 'robo.no'); }
  function finish(actor) {
    const ep = RoboCore.episode(st, actor, world, samples, D_TRAIN);
    lastHuman = ep; row('human', ep);
    if (rec) { const ok = keep(ep); $('#robo-kept').textContent = ok ? t('robo.kept') + ' ' + kept : t('robo.off'); }
    setRec(false); samples = [];
    return ep;
  }
  function runRef() {
    const ep = RoboCore.rollout(env, emb, st.seed, D_TRAIN, world);
    row('ref', ep);
    if (rec) { const ok = keep(ep); $('#robo-kept').textContent = ok ? t('robo.kept') + ' ' + kept : t('robo.off'); setRec(false); }
    return ep;
  }
  function hud() {
    const o = RoboCore.obs(st), r = (x) => (Math.round(x * 100) / 100).toFixed(2);
    $('#robo-hud').textContent = `e ${r(o.pose_e)} m · n ${r(o.pose_n)} m · yaw ${r(o.yaw)} rad · v ${r(o.v)} m/s` +
      (o.depth !== undefined ? ` · depth ${r(o.depth)} m` : '') + ` · step ${st.step}/${env.episode_cap.steps} · R ${r(st.ret)}` +
      (st.done ? ' · ' + t('robo.done') + ': ' + st.done : '') + (rec ? ' · ' + t('robo.recording') + ' ' + samples.length : '');
  }
  function draw() {
    const W = cv.width, H = env.world.arena_half_m, s = W / (2 * H), X = (e) => W / 2 + e * s, Y = (n) => W / 2 - n * s;
    g.fillStyle = env.medium === 'water' ? '#0d2a3a' : '#16261d'; g.fillRect(0, 0, W, W);
    g.strokeStyle = '#2d4448'; g.lineWidth = 1; for (let k = -H; k <= H; k += 5) { g.beginPath(); g.moveTo(X(k), 0); g.lineTo(X(k), W); g.moveTo(0, Y(k)); g.lineTo(W, Y(k)); g.stroke(); }
    for (const b of st.obst) { g.fillStyle = b.id.startsWith('cone') ? '#e8a33d' : '#6b7b80'; g.beginPath(); g.arc(X(b.e), Y(b.n), b.r * s, 0, 7); g.fill(); }
    st.gates.forEach((q, i) => { g.strokeStyle = i < st.next ? '#5fbf7a' : i === st.next ? '#41c4d4' : '#93a3a6'; g.lineWidth = 3; g.beginPath(); g.arc(X(q.e), Y(q.n), 1.2 * s, 0, 7); g.stroke(); });
    if (st.bin) { g.fillStyle = '#41c4d4'; g.fillRect(X(st.bin.e) - 0.7 * s, Y(st.bin.n) - 0.7 * s, 1.4 * s, 1.4 * s); }
    for (const it of st.items) if (!it.taken || (st.carrying === it)) { g.fillStyle = R.litter_colors[it.type]; const p = st.carrying === it ? [st.e, st.n] : [it.e, it.n]; g.beginPath(); g.arc(X(p[0]), Y(p[1]), 0.45 * s, 0, 7); g.fill(); }
    for (const q of st.targets) { g.strokeStyle = q.visited ? '#5fbf7a' : '#fad08c'; g.lineWidth = 2; g.beginPath(); g.arc(X(q.e), Y(q.n), 1.5 * s, 0, 7); g.stroke(); g.fillStyle = '#fad08c'; g.font = '11px monospace'; g.fillText(q.d.toFixed(1) + ' m', X(q.e) + 1.6 * s, Y(q.n)); }
    const rr = Math.max(7, emb.radius_m * s);   // drawn at least 14 px so it reads on a phone g.save(); g.translate(X(st.e), Y(st.n)); g.rotate(-st.yaw);
    g.fillStyle = emb.kind === 'rov' ? '#fad08c' : emb.kind === 'arm-on-base' ? '#e0655b' : '#e8edec'; g.fillRect(-rr, -rr, 2 * rr, 2 * rr);
    g.fillStyle = '#12181b'; g.beginPath(); g.moveTo(0, -rr * 1.4); g.lineTo(-rr * 0.6, -rr * 0.2); g.lineTo(rr * 0.6, -rr * 0.2); g.fill(); g.restore();
  }
  function loop(ts) {
    const dt = env.episode_cap.dt_s; if (last) acc += Math.min(0.25, (ts - last) / 1000); last = ts;
    while (acc >= dt) { acc -= dt; const a = action(); if (a.v || a.w || a.grip || a.vz || rec) tick(a); }
    draw(); hud(); requestAnimationFrame(loop);
  }
  sel.addEventListener('change', () => load(sel.value));
  seedSel.addEventListener('change', () => load(env.id, Number(seedSel.value)));
  $('#robo-reset').addEventListener('click', () => load(env.id, st.seed));
  $('#robo-rec').addEventListener('click', () => { if (rec) { if (st.step) finish('human'); else setRec(false); } else { load(env.id, st.seed); setRec(true); cv.focus(); } });
  $('#robo-ref').addEventListener('click', () => runRef());
  $('#robo-export').addEventListener('click', () => {
    let log = []; try { const a = JSON.parse(localStorage.getItem(TR_KEY_W)); if (Array.isArray(a)) log = a; } catch (e) { /* none */ }
    const doc = { pack: D_TRAIN.pack, exported: new Date().toISOString(), episodes: log.filter((x) => x.kind === 'world-teleop') };
    const u = URL.createObjectURL(new Blob([JSON.stringify(doc, null, 1)], { type: 'application/json' }));
    const a = document.createElement('a'); a.href = u; a.download = 'tc-world-teleop.json'; a.click(); setTimeout(() => URL.revokeObjectURL(u), 1000);
  });
  if (classroom) { $('#robo-rec').disabled = true; $('#robo-export').disabled = true; $('#robo-class').hidden = false; }
  load(Object.keys(R.envs)[0]);
  requestAnimationFrame(loop);
  const api = { envs: () => Object.keys(R.envs), reset: (id, seed) => { load(id, seed); return RoboCore.obs(st); },
    step: (a) => { if (rec && st.step % every() === 0 && samples.length < MAXS) samples.push(RoboCore.sample(st, a)); const r = RoboCore.step(st, a); return { ...r, info: { terms: st.terms } }; },
    drive: (a, n) => { for (let i = 0; i < n && !st.done; i++) tick(a); if (st.done) return lastHuman; return null; },
    stop: () => (st.step ? finish('human') : null), record: (on) => setRec(on),
    policy: () => RoboCore.policy(st), rollout: (id, seed) => RoboCore.rollout(R.envs[id], R.embodiments[R.envs[id].embodiments[0]], seed, D_TRAIN, world),
    runRef, recording: () => rec, kept: () => kept, state: () => ({ env: env.id, seed: st.seed, step: st.step, done: st.done, ret: st.ret, samples: samples.length }),
    episodes: () => { try { return (JSON.parse(localStorage.getItem(TR_KEY_W)) || []).filter((x) => x.kind === 'world-teleop'); } catch (e) { return []; } } };
  window.__robokit = api;
  return api;
}
/* ROBOKIT_UI:END */
'''
