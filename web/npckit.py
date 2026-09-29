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
.npc-src,.npc-cert,.npc-count,.npc-honesty,.npc-lang{margin:6px 0 0;font-size:.78rem;color:var(--muted)}
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
const STATES = Object.freeze(['idle', 'wander', 'walk', 'greet', 'talk', 'follow']);
const LABEL_KEYS = ['talk', 'next', 'prev', 'close', 'takeMeThere', 'source',
  'notCert', 'pointsTo', 'of', 'honesty', 'quoteLang', 'roles'];
const ROLE_KEYS = { mentor: 'npc.role.mentor', 'k12-guide': 'npc.role.k12', ranger: 'npc.role.ranger',
  pilot: 'npc.role.pilot', host: 'npc.role.host', responder: 'npc.role.responder',
  'relief-coordinator': 'npc.role.relief', teacher: 'npc.role.teacher', 'humanitarian-trainer': 'npc.role.humanitarian' };
const LABEL_I18N = { talk: 'npc.talk', next: 'npc.next', prev: 'npc.prev', close: 'npc.close',
  takeMeThere: 'npc.take', source: 'npc.source', notCert: 'npc.notcert', pointsTo: 'npc.points',
  of: 'npc.of', honesty: 'npc.honesty', quoteLang: 'npc.quotelang' };
/* labels from the site catalogue: labelsFrom(tr) with tr(key) -> string (strict) */
function labelsFrom(tr) {
  const L = {};
  for (const [k, key] of Object.entries(LABEL_I18N)) L[k] = str(tr(key), 'i18n ' + key);
  L.roles = {};
  for (const [r, key] of Object.entries(ROLE_KEYS)) L.roles[r] = str(tr(key), 'i18n ' + key);
  return L;
}
/* a required, non-empty string - never render "undefined" */
function str(v, where) {
  if (typeof v !== 'string' || v.length === 0) throw new Error('TCNPC: missing ' + where);
  return v;
}

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
  if (inp.away) return 'walk';                    // routine: walk to this hour's place
  if (inp.scheduled !== 'idle' && inp.scheduled !== 'wander') {
    throw new Error('TCNPC: bad scheduled state ' + inp.scheduled);
  }
  return inp.scheduled;
}

/* hours wrap at midnight: any finite hour is taken modulo 24 into [0, 24) first
   (30 h = 06:00 next day, -0.5 h = 23:30) - never matched raw against the
   overnight slot, which would otherwise swallow every out-of-range hour */
function wrapH(h, where) {
  if (typeof h !== 'number' || !Number.isFinite(h)) throw new Error('TCNPC: non-finite hour in ' + where + ': ' + h);
  return ((h % 24) + 24) % 24;
}
function scheduledAt(schedule, h0) {
  const h = wrapH(h0, 'scheduledAt');
  for (const s of schedule) {
    const inside = s.from_h <= s.to_h ? (h >= s.from_h && h < s.to_h)
                                      : (h >= s.from_h || h < s.to_h);
    if (inside) return s;
  }
  throw new Error('TCNPC: schedule has no slot for hour ' + h);
}

/* simulated day clock: hoursPerSecond game hours pass per real second */
function makeClock(startH, hoursPerSecond) {
  let h = wrapH(startH, 'makeClock start');
  wrapH(hoursPerSecond, 'makeClock rate');
  return { tick(dt) { h = wrapH(h + dt * hoursPerSecond, 'makeClock tick'); return h; },
    get h() { return h; }, set(v) { h = wrapH(v, 'makeClock set'); return h; } };
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

/* ---- idle animation on the existing rig (pure, unit-tested) ----
   Timing per NPC is deterministic from hash32(id): breathing period 3.2..4.4 s
   (chest / proxy torso scale-y 1 +- 1.5 %); a glance every 7..11 s turns the
   head to one side and back over 1.4 s (sin ease, max 0.45 rad, alternating
   sides, never while greeting or talking); while talking the right arm gestures
   on a 2.4 s cycle that starts from rest when the talk starts. */
const IDLE = { breathMin: 3.2, breathSpan: 1.2, breathAmp: 0.015, glanceMin: 7, glanceSpan: 4,
  glanceDur: 1.4, glanceYaw: 0.45, gesturePeriod: 2.4, gestureAmp: 0.5 };
function idleTiming(seed) {
  const r = rng(seed);
  return { breath: IDLE.breathMin + r() * IDLE.breathSpan, every: IDLE.glanceMin + r() * IDLE.glanceSpan,
    phase: r(), side: r() < 0.5 ? -1 : 1 };
}
function idlePose(tm, t, state, talkT) {
  const breath = 1 + IDLE.breathAmp * Math.sin(2 * Math.PI * t / tm.breath);
  const u = t + tm.phase * tm.every, k = Math.floor(u / tm.every), local = u - k * tm.every;
  let yaw = 0;
  if (local < IDLE.glanceDur && state !== 'talk' && state !== 'greet') {
    yaw = (k % 2 ? -tm.side : tm.side) * IDLE.glanceYaw * Math.sin(Math.PI * local / IDLE.glanceDur);
  }
  const gesture = state === 'talk'
    ? IDLE.gestureAmp * 0.5 * (1 - Math.cos(2 * Math.PI * talkT / IDLE.gesturePeriod)) : 0;
  return { breath, yaw, gesture };
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
    line: str(need(lines[i], 'text', 'line'), 'line.text'),
    source: str(need(lines[i], 'source', 'line'), 'line.source (' + npc.id + ' line ' + (i + 1) + ')'),
    pos: i + 1, total: lines.length,
    notCert: { text: str(need(npc, 'not_certification', 'npc').text, 'not_certification.text'),
      source: str(npc.not_certification.source, 'not_certification.source') },
    pointsTo: need(npc, 'points_to', 'npc'), guideTo: need(npc, 'guide_to', 'npc') };
}
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;',
  '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
function dialogueHTML(m, L, honesty) {
  for (const k of LABEL_KEYS) need(L, k, 'labels');
  str(honesty, 'honesty.scripted');
  return '<h2 id="npc-dlg-title">' + esc(m.title) + '</h2>' +
    '<p class="npc-role">' + esc(need(L.roles, m.role, 'labels.roles')) + '</p>' +
    '<div class="npc-line" aria-live="polite" aria-atomic="true">' +
      '<blockquote><p>' + esc(m.line) + '</p></blockquote>' +
      '<p class="npc-src">' + esc(L.source) + ' <code>' + esc(m.source) + '</code></p>' +
      '<p class="npc-lang">' + esc(L.quoteLang) + '</p>' +
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
  str(honesty.scripted, 'honesty.scripted (pass npc_data(fips).honesty, the object)');
  const panelRoot = need(opt, 'panelRoot', 'opts');
  const num = (k, d) => (k in opt ? opt[k] : d);   // tuning knobs, not registry data
  const budgetMs = num('budgetMs', 1.0), detailMax = num('detailMax', 2);
  const detailDist = num('detailDist', 18), greetR = num('greetRadius', 4);
  const talkR = num('talkRadius', 2.5);
  const animDist = num('animDist', 30), animMax = num('animMax', 16), animBudgetMs = num('animBudgetMs', 0.3);
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
    const anchors = {};              // every place this NPC's routine visits
    for (const sl of need(n, 'schedule', n.id)) {
      const at = need(sl, 'at', n.id + '.schedule');
      const p = placeOf(at);
      if (!p) throw new Error('TCNPC: ' + n.id + ' routine place ' + at + ' cannot be placed');
      anchors[at] = { x: p.x + off.x, z: p.z + off.z };
    }
    agents.push({ npc: n, id: n.id, x: hx, z: hz, vx: 0, vz: 0, heading: 0, anchors,
      home: { x: hx, z: hz }, state: 'idle', target: null, follow: null,
      rand: rng(hash32(n.id)), body: null, bones: null, idx: agents.length, acc: 0,
      scale: need(need(n.appearance, 'scale', n.id + '.appearance'), 'xyz', n.id + '.appearance.scale'),
      idle: idleTiming(hash32(n.id)), pose: { breath: 1, yaw: 0, gesture: 0 }, talkT: 0 });
  }

  // four instanced parts; per-instance colour from the registry proxy hexes
  const parts = {
    torso: { geo: new THREE.BoxGeometry(0.44, 0.62, 0.26), y: 1.22 },
    legs: { geo: new THREE.BoxGeometry(0.38, 0.82, 0.24), y: 0.5 },
    head: { geo: new THREE.BoxGeometry(0.22, 0.24, 0.22), y: 1.66 },
    hat: { geo: new THREE.BoxGeometry(0.26, 0.08, 0.26), y: 1.82, optional: true },
    vest: { geo: new THREE.BoxGeometry(0.47, 0.5, 0.29), y: 1.24, optional: true },
  };
  // hat / vest: proxy value null = not worn (bare head, no vest) - the key itself is required
  for (const a of agents) for (const [k, p] of Object.entries(parts)) {
    if (!(k in need(a.npc.appearance, 'proxy', a.id + '.appearance'))) throw new Error('TCNPC: missing ' + a.id + '.proxy.' + k);
    if (!p.optional) need(a.npc.appearance.proxy, k, a.id + '.proxy');
  }
  const meshes = {};
  const col = new THREE.Color();
  for (const [k, p] of Object.entries(parts)) {
    const m = new THREE.InstancedMesh(p.geo, new THREE.MeshStandardMaterial({ roughness: 0.8 }),
      Math.max(1, agents.length));
    m.count = agents.length;
    m.userData.npcPart = k;
    for (const a of agents) {
      const pr = a.npc.appearance.proxy[k];
      col.set(pr ? str(pr.hex, a.id + '.proxy.' + k + '.hex') : '#000000');
      m.setColorAt(a.idx, col);
    }
    if (m.instanceColor) m.instanceColor.needsUpdate = true;
    scene.add(m); meshes[k] = m;
  }
  const mtx = new THREE.Matrix4(), q = new THREE.Quaternion(), pos = new THREE.Vector3();
  const sc = new THREE.Vector3(), zero = new THREE.Vector3(0, 0, 0), up = new THREE.Vector3(0, 1, 0);
  const qh = new THREE.Quaternion(), qp = new THREE.Quaternion(), side = new THREE.Vector3(1, 0, 0);
  function writeInstance(a) {
    const y = groundY(a.x, a.z), [sx, sy, sz] = a.scale, P = a.pose;
    q.setFromAxisAngle(up, a.heading);
    qh.setFromAxisAngle(up, a.heading + P.yaw).multiply(qp.setFromAxisAngle(side, 0.3 * P.gesture));
    for (const [k, p] of Object.entries(parts)) {
      const hidden = a.body || (p.optional && !a.npc.appearance.proxy[k]);
      const torso = k === 'torso' || k === 'vest';
      pos.set(a.x, y + p.y * sy, a.z);
      sc.set(sx, sy * (torso ? P.breath : 1), sz);
      mtx.compose(pos, k === 'head' || k === 'hat' ? qh : q, hidden ? zero : sc);
      meshes[k].setMatrixAt(a.idx, mtx);
    }
    if (a.body) {
      a.body.position.set(a.x, y, a.z); a.body.rotation.y = a.heading;
      const B = a.bones;
      if (B.chest) B.chest.scale.y = P.breath;
      if (B.head) B.head.rotation.y = P.yaw;
      if (B.rightUpperArm) B.rightUpperArm.rotation.x = -P.gesture;
      if (B.rightLowerArm) B.rightLowerArm.rotation.x = -0.8 * P.gesture;
    }
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
    const anc = a.anchors[slot.at];
    a.anchor = anc;
    const away = Math.hypot(a.x - anc.x, a.z - anc.z) > slot.radius_m + 1.5;
    a.state = nextState(a.state, { dist, talking: talking === a, following: !!a.follow,
      arrived, away, scheduled: slot.state, greetRadius: greetR });
    if (arrived) { a.follow = null; }
    let target = null;
    if (a.state === 'follow') target = a.follow;
    else if (a.state === 'walk') target = anc;
    else if (a.state === 'wander') {
      const r = slot.radius_m;
      if (!a.target || Math.hypot(a.target.x - a.x, a.target.z - a.z) < 0.6 ||
          Math.hypot(a.target.x - anc.x, a.target.z - anc.z) > r) {
        const ang = a.rand() * Math.PI * 2, rr = Math.sqrt(a.rand()) * r;
        a.target = { x: anc.x + Math.cos(ang) * rr, z: anc.z + Math.sin(ang) * rr };
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
      if (want && !a.body) {
        a.body = opt.makeBody(a.npc.appearance.cfg);
        a.bones = {};   // the rig's own named bones (buildAvatarMesh); a body without them just is not animated
        for (const nm of ['chest', 'head', 'rightUpperArm', 'rightLowerArm']) a.bones[nm] = a.body.getObjectByName(nm) || null;
        scene.add(a.body); writeInstance(a);
      }
      if (!want && a.body) { scene.remove(a.body); a.body = null; a.bones = null; writeInstance(a); }
    }
    return ranked.length;
  }
  /* idle animation pass: the animMax nearest within animDist, stopped when animBudgetMs is spent */
  let animT = 0;
  function animate(dt) {
    animT += dt;
    const t0 = now();
    const near = [];
    for (const a of agents) {
      if (a.state === 'talk') a.talkT += dt; else a.talkT = 0;
      const d = Math.hypot(player.x - a.x, player.z - a.z);
      if (d <= animDist) near.push([d, a]);
    }
    near.sort((p, r) => p[0] - r[0]);
    let n = 0;
    for (const [, a] of near.slice(0, animMax)) {
      if (n > 0 && now() - t0 >= animBudgetMs) break;
      a.pose = idlePose(a.idle, animT, a.state, a.talkT);
      writeInstance(a); n++;
    }
    return n;
  }
  return {
    agents,
    update(dt, p, h) {
      for (const a of agents) a.acc += Math.min(dt, 0.1);
      player = p; clockH = h;
      const r = run(agents, think);
      const d = detail();
      const an = animate(Math.min(dt, 0.1));
      for (const m of Object.values(meshes)) m.instanceMatrix.needsUpdate = true;
      lastStats = { ...r, detail: d, animated: an };
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
  dialogueKey, homeOffset, scheduledAt, wrapH, makeClock, labelsFrom, idleTiming, idlePose, IDLE, STATES, LABEL_KEYS };
globalThis.TCNPC = TCNPC;
"""

NPC_JS_INLINE = NPC_CORE
NPC_JS = NPC_CORE + ("export { createNPCKit, nextState, steer, makeBudget, dialogueModel, "
                     "dialogueHTML, dialogueKey, homeOffset, scheduledAt, wrapH, makeClock, labelsFrom, idleTiming, idlePose, IDLE, "
                     "STATES, LABEL_KEYS };\n")

# every catalogue key the kit reads via TCNPC.labelsFrom(tr): embed these in your page's i18n
NPC_I18N_KEYS = ('npc.talk', 'npc.next', 'npc.prev', 'npc.close', 'npc.take', 'npc.source',
                 'npc.notcert', 'npc.points', 'npc.of', 'npc.honesty', 'npc.quotelang',
                 'npc.role.mentor', 'npc.role.k12', 'npc.role.ranger', 'npc.role.pilot',
                 'npc.role.host', 'npc.role.responder', 'npc.role.relief', 'npc.role.teacher',
                 'npc.role.humanitarian')

if __name__ == '__main__':
    if '--emit' in sys.argv:
        sys.stdout.write(NPC_JS)
    elif '--emit-css' in sys.argv:
        sys.stdout.write(NPC_CSS)
    else:
        print(f'NPC_JS {len(NPC_JS)} chars, NPC_CSS {len(NPC_CSS)} chars')
