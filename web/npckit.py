#!/usr/bin/env python3
"""NPC kit for the parish world: spawn, behave, steer, talk - within a budget.

    from npckit import NPC_JS, NPC_JS_INLINE, NPC_CSS, npc_data

NPC_JS is ES module text (export list at the end; also sets globalThis.TCNPC);
NPC_JS_INLINE is the same code without the export line for pasting into an
existing <script>. The kit brings no character system of its own: bodies are
four InstancedMesh parts coloured from the registry's avatars/ proxy colours,
and the nearest few are swapped for the host page's own rig through
makeBody(cfg) (web/build_3d.py's buildAvatarMesh reads the same cfg).

Every word the dialogue panel shows is either a verbatim registry quote with
its source path (npcs/registry/npcs.json) or a label the CALLER passes from
its own i18n keys; the kit types no text. Colours come only from theme tokens
so all five site styles apply. The contract is $SP/NPC_CONTRACT.md.

    python3 web/npckit.py --emit     prints NPC_JS (npcs/test.mjs imports it)
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REG_PATH = ROOT / 'npcs' / 'registry' / 'npcs.json'


class NPCKitError(Exception):
    pass


def npc_data(fips):
    """JSON-safe NPC list for one parish, plus the honesty block. Fails by name."""
    if not REG_PATH.exists():
        raise NPCKitError('npcs/registry/npcs.json missing: run python3 npcs/build.py')
    reg = json.loads(REG_PATH.read_text())
    if fips not in {p['fips'] for p in reg['parishes']}:
        raise NPCKitError(f'npc_data: parish {fips} is not in npcs/registry/npcs.json')
    return {'fips': fips, 'honesty': reg['honesty'],
            'places_status': reg['places_status'],
            'places': {p['id']: p for p in reg['places'] if p['parish'] == fips},
            'npcs': [n for n in reg['npcs'] if n['parish'] == fips]}


NPC_CSS = """
.npc-panel{position:fixed;right:16px;bottom:16px;max-width:min(420px,calc(100vw - 32px));
  max-height:min(70vh,560px);overflow:auto;z-index:40;padding:14px 16px;border-radius:12px;
  background:var(--panel);color:var(--ink);border:1px solid var(--rule);
  box-shadow:0 8px 28px color-mix(in srgb,var(--ink) 22%,transparent)}
.npc-panel[hidden]{display:none}
.npc-panel h2{margin:0 0 2px;font-size:1.1rem;color:var(--ink)}
.npc-role{margin:0 0 10px;color:var(--muted);font-size:.85rem}
.npc-line blockquote{margin:0;padding:8px 10px;border-left:3px solid var(--mark);background:var(--surface)}
.npc-line blockquote p{margin:0;color:var(--ink)}
.npc-src,.npc-cert,.npc-count,.npc-honesty{margin:6px 0 0;font-size:.78rem;color:var(--muted)}
.npc-src code,.npc-cert code{color:var(--ink);word-break:break-all}
.npc-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.npc-actions button{min-height:44px;min-width:44px;padding:6px 12px;border-radius:8px;cursor:pointer;
  border:1px solid var(--rule);background:var(--surface);color:var(--ink);font:inherit}
.npc-actions button.npc-go{background:var(--mark);color:var(--mark-ink);border-color:var(--mark)}
.npc-actions button:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.npc-points a{color:var(--link)}
"""

NPC_CORE = r"""/* ---------------------------------------------------------- TCNPC kit ---
   Scripted guides. Every line shown is a verbatim registry quote carried with
   its source path; labels come from the caller. No model, no network. */
const STATES = Object.freeze(['idle', 'wander', 'greet', 'talk', 'follow']);
const LABEL_KEYS = ['talk', 'next', 'prev', 'close', 'takeMeThere', 'source',
  'notCert', 'pointsTo', 'of', 'honesty', 'roles'];

function need(obj, key, where) {
  if (obj === null || obj === undefined || !(key in obj) ||
      obj[key] === undefined || obj[key] === null) {
    throw new Error('TCNPC: missing ' + where + '.' + key);
  }
  return obj[key];
}

/* ---- behaviour: pure transition function (unit-tested) ----
   inp = {dist, talking, following, arrived, scheduled ('idle'|'wander'),
          greetRadius} */
function nextState(state, inp) {
  if (!STATES.includes(state)) throw new Error('TCNPC: unknown state ' + state);
  if (inp.talking) return 'talk';
  if (inp.following && !inp.arrived) return 'follow';
  if (state === 'follow' && inp.arrived) return 'greet';
  if (inp.dist <= inp.greetRadius) return 'greet';
  if (inp.scheduled !== 'idle' && inp.scheduled !== 'wander') {
    throw new Error('TCNPC: bad scheduled state ' + inp.scheduled);
  }
  return inp.scheduled;
}

function scheduledAt(schedule, h) {
  for (const s of schedule) {
    const inside = s.from_h <= s.to_h ? (h >= s.from_h && h < s.to_h)
                                      : (h >= s.from_h || h < s.to_h);
    if (inside) return s;
  }
  throw new Error('TCNPC: schedule has no slot for hour ' + h);
}

/* ---- steering: arrive + separation + obstacle avoidance (pure) ----
   a = {x, z, vx, vz}; target = {x, z} | null; others = [{x, z}];
   obstacles = [{x, z, r}]; returns {vx, vz}. */
function steer(a, target, others, obstacles, o) {
  const maxSpeed = o.maxSpeed, slowR = o.slowRadius, sepR = o.sepRadius;
  let dx = 0, dz = 0;
  if (target) {
    const tx = target.x - a.x, tz = target.z - a.z;
    const d = Math.hypot(tx, tz);
    if (d > 1e-6) {
      const want = d < slowR ? maxSpeed * d / slowR : maxSpeed;
      dx += tx / d * want - a.vx; dz += tz / d * want - a.vz;
    }
  } else { dx -= a.vx; dz -= a.vz; }
  for (const b of others) {
    const ox = a.x - b.x, oz = a.z - b.z, d = Math.hypot(ox, oz);
    if (d > 1e-6 && d < sepR) {
      const k = (sepR - d) / sepR * maxSpeed * 1.5;
      dx += ox / d * k; dz += oz / d * k;
    }
  }
  for (const c of obstacles) {
    const ox = a.x - c.x, oz = a.z - c.z, d = Math.hypot(ox, oz);
    const reach = c.r + o.avoidMargin;
    if (d > 1e-6 && d < reach) {
      const k = (reach - d) / o.avoidMargin * maxSpeed * 2;
      dx += ox / d * k; dz += oz / d * k;
    }
  }
  let vx = a.vx + dx, vz = a.vz + dz;
  const s = Math.hypot(vx, vz);
  if (s > maxSpeed) { vx = vx / s * maxSpeed; vz = vz / s * maxSpeed; }
  return { vx, vz };
}

/* ---- per-frame budget: round-robin until the budget is spent ---- */
function makeBudget(budgetMs, now) {
  let cursor = 0;
  return function run(items, fn) {
    const t0 = now();
    let done = 0;
    const n = items.length;
    while (done < n) {
      fn(items[(cursor + done) % n]);
      done++;
      if (now() - t0 >= budgetMs) break;
    }
    if (n) cursor = (cursor + done) % n;
    return { updated: done, skipped: n - done, ms: now() - t0 };
  };
}

/* golden-angle ring around a home place, 2.5 m out */
function homeOffset(i) {
  const a = i * 2.399963229728653;
  return { x: Math.cos(a) * 2.5, z: Math.sin(a) * 2.5 };
}

function hash32(s) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}
function rng(seed) {
  let t = seed >>> 0;
  return () => { t = (t + 0x6D2B79F5) >>> 0; let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r); return ((r ^ (r >>> 14)) >>> 0) / 4294967296; };
}

/* ---- dialogue: pure model + markup + keys (unit-tested) ---- */
function dialogueModel(npc, idx) {
  const lines = need(npc, 'knowledge', 'npc');
  const i = Math.max(0, Math.min(lines.length - 1, idx));
  return { id: npc.id, title: need(npc, 'name', 'npc'), role: need(npc, 'role', 'npc'),
    line: need(lines[i], 'text', 'line'), source: need(lines[i], 'source', 'line'),
    pos: i + 1, total: lines.length,
    notCert: need(npc, 'not_certification', 'npc'),
    pointsTo: need(npc, 'points_to', 'npc'), guideTo: need(npc, 'guide_to', 'npc') };
}
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;',
  '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
function dialogueHTML(m, L, honesty) {
  for (const k of LABEL_KEYS) need(L, k, 'labels');
  return '<h2 id="npc-dlg-title">' + esc(m.title) + '</h2>' +
    '<p class="npc-role">' + esc(need(L.roles, m.role, 'labels.roles')) + '</p>' +
    '<div class="npc-line" aria-live="polite" aria-atomic="true">' +
      '<blockquote><p>' + esc(m.line) + '</p></blockquote>' +
      '<p class="npc-src">' + esc(L.source) + ' <code>' + esc(m.source) + '</code></p>' +
      '<p class="npc-count">' + m.pos + ' ' + esc(L.of) + ' ' + m.total + '</p>' +
    '</div>' +
    '<p class="npc-cert">' + esc(L.notCert) + ' ' + esc(m.notCert.text) +
      ' <code>' + esc(m.notCert.source) + '</code></p>' +
    '<p class="npc-points npc-src">' + esc(L.pointsTo) + ' <code>' +
      esc(m.pointsTo.kind + ':' + m.pointsTo.id) + '</code></p>' +
    '<div class="npc-actions">' +
      '<button type="button" data-npc="prev"' + (m.pos === 1 ? ' disabled' : '') + '>' + esc(L.prev) + '</button>' +
      '<button type="button" data-npc="next"' + (m.pos === m.total ? ' disabled' : '') + '>' + esc(L.next) + '</button>' +
      '<button type="button" class="npc-go" data-npc="go">' + esc(L.takeMeThere) + '</button>' +
      '<button type="button" data-npc="close">' + esc(L.close) + '</button>' +
    '</div>' +
    '<p class="npc-honesty">' + esc(L.honesty) + ' ' + esc(honesty) + '</p>';
}
function dialogueKey(idx, total, key) {
  if (key === 'Escape') return { idx, action: 'close' };
  if (key === 'ArrowRight') return { idx: Math.min(total - 1, idx + 1), action: 'line' };
  if (key === 'ArrowLeft') return { idx: Math.max(0, idx - 1), action: 'line' };
  return { idx, action: null };
}

/* ---- the kit ---- */
function createNPCKit(opt) {
  const THREE = need(opt, 'THREE', 'opts'), scene = need(opt, 'scene', 'opts');
  const npcs = need(opt, 'npcs', 'opts'), placeOf = need(opt, 'placeOf', 'opts');
  const L = need(opt, 'labels', 'opts');
  for (const k of LABEL_KEYS) need(L, k, 'labels');
  const honesty = need(opt, 'honesty', 'opts');
  const panelRoot = need(opt, 'panelRoot', 'opts');
  const num = (k, d) => (k in opt ? opt[k] : d);   // tuning knobs, not registry data
  const budgetMs = num('budgetMs', 1.0), detailMax = num('detailMax', 2);
  const detailDist = num('detailDist', 18), greetR = num('greetRadius', 4);
  const talkR = num('talkRadius', 2.5);
  const groundY = 'groundY' in opt ? opt.groundY : () => 0;
  const obstacles = 'obstacles' in opt ? opt.obstacles : [];
  const now = 'now' in opt ? opt.now : () => performance.now();
  const S = { maxSpeed: 1.2, slowRadius: 1.5, sepRadius: 1.2, avoidMargin: 0.8 };

  const agents = [];
  for (const n of npcs) {
    const home = placeOf(need(n.home, 'place', n.id + '.home'));
    if (!home) continue;                 // host could not place it: not drawn
    const off = homeOffset(need(n.home, 'offset_index', n.id + '.home'));
    const hx = home.x + off.x, hz = home.z + off.z;
    agents.push({ npc: n, id: n.id, x: hx, z: hz, vx: 0, vz: 0, heading: 0,
      home: { x: hx, z: hz }, state: 'idle', target: null, follow: null,
      rand: rng(hash32(n.id)), body: null, idx: agents.length, acc: 0 });
  }

  // four instanced parts; per-instance colour from the registry proxy hexes
  const parts = {
    torso: { geo: new THREE.BoxGeometry(0.44, 0.62, 0.26), y: 1.22 },
    legs: { geo: new THREE.BoxGeometry(0.38, 0.82, 0.24), y: 0.5 },
    head: { geo: new THREE.BoxGeometry(0.22, 0.24, 0.22), y: 1.66 },
    hat: { geo: new THREE.BoxGeometry(0.26, 0.08, 0.26), y: 1.82 },
  };
  const meshes = {};
  const col = new THREE.Color();
  for (const [k, p] of Object.entries(parts)) {
    const m = new THREE.InstancedMesh(p.geo, new THREE.MeshStandardMaterial({ roughness: 0.8 }),
      Math.max(1, agents.length));
    m.count = agents.length;
    m.userData.npcPart = k;
    for (const a of agents) {
      col.set(need(a.npc.appearance.proxy, k, a.id + '.proxy').hex);
      m.setColorAt(a.idx, col);
    }
    if (m.instanceColor) m.instanceColor.needsUpdate = true;
    scene.add(m); meshes[k] = m;
  }
  const mtx = new THREE.Matrix4(), q = new THREE.Quaternion(), pos = new THREE.Vector3();
  const one = new THREE.Vector3(1, 1, 1), zero = new THREE.Vector3(0, 0, 0), up = new THREE.Vector3(0, 1, 0);
  function writeInstance(a) {
    const y = groundY(a.x, a.z);
    q.setFromAxisAngle(up, a.heading);
    for (const [k, p] of Object.entries(parts)) {
      pos.set(a.x, y + p.y, a.z);
      mtx.compose(pos, q, a.body ? zero : one);
      meshes[k].setMatrixAt(a.idx, mtx);
    }
    if (a.body) { a.body.position.set(a.x, y, a.z); a.body.rotation.y = a.heading; }
  }
  agents.forEach(writeInstance);
  for (const m of Object.values(meshes)) m.instanceMatrix.needsUpdate = true;

  // ---- dialogue panel ----
  const panel = document.createElement('section');
  panel.className = 'npc-panel';
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-modal', 'false');
  panel.setAttribute('aria-labelledby', 'npc-dlg-title');
  panel.hidden = true;
  panelRoot.appendChild(panel);
  let talking = null, lineIdx = 0, opener = null, lastStats = { updated: 0, skipped: 0, ms: 0, detail: 0 };
  function render(focusSel) {
    panel.innerHTML = dialogueHTML(dialogueModel(talking.npc, lineIdx), L, honesty.scripted);
    const f = panel.querySelector(focusSel) || panel.querySelector('[data-npc="close"]');
    f.focus();
  }
  function talkTo(id) {
    const a = agents.find((x) => x.id === id);
    if (!a) throw new Error('TCNPC: no NPC ' + id);
    if (!talking) opener = document.activeElement;
    talking = a; lineIdx = 0; a.follow = null;
    panel.hidden = false;
    render('[data-npc="next"]:not([disabled])');
    if (opt.onTalk) opt.onTalk(a.npc);
  }
  function closeDialogue() {
    if (!talking) return;
    talking = null; panel.hidden = true; panel.innerHTML = '';
    if (opener && typeof opener.focus === 'function' && opener.isConnected) opener.focus();
    opener = null;
  }
  panel.addEventListener('click', (e) => {
    const b = e.target.closest('[data-npc]');
    if (!b || !talking) return;
    const k = b.dataset.npc;
    if (k === 'next' || k === 'prev') {
      lineIdx = dialogueKey(lineIdx, talking.npc.knowledge.length,
        k === 'next' ? 'ArrowRight' : 'ArrowLeft').idx;
      render('[data-npc="' + k + '"]:not([disabled])');
    } else if (k === 'close') closeDialogue();
    else if (k === 'go') {
      const a = talking, place = a.npc.guide_to, p = placeOf(place);
      closeDialogue();
      if (p) a.follow = { x: p.x, z: p.z, place };
      if (opt.onTakeMeThere) opt.onTakeMeThere(place, a.npc);
    }
  });
  panel.addEventListener('keydown', (e) => {
    if (!talking) return;
    const r = dialogueKey(lineIdx, talking.npc.knowledge.length, e.key);
    if (r.action === 'close') { e.preventDefault(); closeDialogue(); }
    else if (r.action === 'line' && r.idx !== lineIdx) { e.preventDefault(); lineIdx = r.idx;
      render('[data-npc="' + (e.key === 'ArrowRight' ? 'next' : 'prev') + '"]:not([disabled])'); }
  });

  let player = { x: 0, z: 0 }, clockH = 12;
  function think(a) {
    const dist = Math.hypot(player.x - a.x, player.z - a.z);
    const slot = scheduledAt(a.npc.schedule, clockH);
    const arrived = a.follow ? Math.hypot(a.follow.x - a.x, a.follow.z - a.z) < 1.2 : false;
    a.state = nextState(a.state, { dist, talking: talking === a, following: !!a.follow,
      arrived, scheduled: slot.state, greetRadius: greetR });
    if (arrived) { a.follow = null; }
    let target = null;
    if (a.state === 'follow') target = a.follow;
    else if (a.state === 'wander') {
      const r = slot.radius_m;
      if (!a.target || Math.hypot(a.target.x - a.x, a.target.z - a.z) < 0.6 ||
          Math.hypot(a.x - a.home.x, a.z - a.home.z) > r) {
        const ang = a.rand() * Math.PI * 2, rr = Math.sqrt(a.rand()) * r;
        a.target = { x: a.home.x + Math.cos(ang) * rr, z: a.home.z + Math.sin(ang) * rr };
      }
      target = a.target;
    }
    const others = [];
    for (const b of agents) if (b !== a && Math.abs(b.x - a.x) < 2 && Math.abs(b.z - a.z) < 2) others.push(b);
    others.push(player);
    const v = steer(a, target, others, obstacles, S);
    a.vx = v.vx; a.vz = v.vz;
    const dt = Math.min(a.acc, 0.25);   // time since THIS agent last ran
    a.acc = 0;
    a.x += a.vx * dt; a.z += a.vz * dt;
    if (a.state === 'greet' || a.state === 'talk') a.heading = Math.atan2(player.x - a.x, player.z - a.z);
    else if (Math.hypot(a.vx, a.vz) > 0.05) a.heading = Math.atan2(a.vx, a.vz);
    writeInstance(a);
  }
  const run = makeBudget(budgetMs, now);
  function nearest() {
    let best = null, bd = Infinity;
    for (const a of agents) { const d = Math.hypot(player.x - a.x, player.z - a.z); if (d < bd) { bd = d; best = a; } }
    return best && bd <= talkR ? best : null;
  }
  function detail() {
    if (!opt.makeBody) return 0;
    const ranked = agents.map((a) => [Math.hypot(player.x - a.x, player.z - a.z), a])
      .filter(([d]) => d <= detailDist).sort((p, r) => p[0] - r[0]).slice(0, detailMax).map(([, a]) => a);
    for (const a of agents) {
      const want = ranked.includes(a);
      if (want && !a.body) { a.body = opt.makeBody(a.npc.appearance.cfg); scene.add(a.body); writeInstance(a); }
      if (!want && a.body) { scene.remove(a.body); a.body = null; writeInstance(a); }
    }
    return ranked.length;
  }
  return {
    agents,
    update(dt, p, h) {
      for (const a of agents) a.acc += Math.min(dt, 0.1);
      player = p; clockH = h;
      const r = run(agents, think);
      const d = detail();
      for (const m of Object.values(meshes)) m.instanceMatrix.needsUpdate = true;
      lastStats = { ...r, detail: d };
      return lastStats;
    },
    talkTo, closeDialogue, nearest,
    talkNearest() { const a = nearest(); if (a) talkTo(a.id); return a; },
    stats: () => lastStats,
    dispose() {
      closeDialogue(); panel.remove();
      for (const m of Object.values(meshes)) { scene.remove(m); m.geometry.dispose(); m.material.dispose(); }
      for (const a of agents) if (a.body) scene.remove(a.body);
    },
  };
}

const TCNPC = { createNPCKit, nextState, steer, makeBudget, dialogueModel, dialogueHTML,
  dialogueKey, homeOffset, scheduledAt, STATES, LABEL_KEYS };
globalThis.TCNPC = TCNPC;
"""

NPC_JS_INLINE = NPC_CORE
NPC_JS = NPC_CORE + ("export { createNPCKit, nextState, steer, makeBudget, dialogueModel, "
                     "dialogueHTML, dialogueKey, homeOffset, scheduledAt, STATES, LABEL_KEYS };\n")

if __name__ == '__main__':
    if '--emit' in sys.argv:
        sys.stdout.write(NPC_JS)
    elif '--emit-css' in sys.argv:
        sys.stdout.write(NPC_CSS)
    else:
        print(f'NPC_JS {len(NPC_JS)} chars, NPC_CSS {len(NPC_CSS)} chars')
