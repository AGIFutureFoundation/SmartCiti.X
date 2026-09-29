#!/usr/bin/env python3
"""TQKIT_JS: TradesQuest field-job stations for the SmartCiti.X Holodeck, as an embeddable ES module string.

Four TradesQuest 3D field-job scenes (React Three Fiber, AGIFutureFoundation/game-world-focus @3ea15f0,
artifacts/trade-quest-3d/src/components/game/) ported to plain three.js so a union hall can place them as
walk-up stations:

  electrical   breaker panel + outlet on a backboard     (InteractableObjects.tsx, HVACObjects.tsx)
  plumbing     water heater + leaking sink trap + puddle  (PlumberWaterHeaterObjects.tsx, InteractableObjects.tsx)
  hvac         rooftop condenser, disconnect, protection  (HVACObjects.tsx, HVACWorkshopObjects.tsx)
  carpentry    stud wall on plates, bench, power tool     (CarpenterFrameObjects.tsx, CarpenterWorkshop.tsx)

Every object is an AUTHORED schematic training mock-up, not real equipment, and carries the provenance
"from game-world-focus @3ea15f0, <path>". Each station runs TradesQuest's observation-first pattern in four
steps (read the label, mark the zone, pick a training tool, stop at the tag and hand off). It is play: it never
enters a completion record and certifies nothing; the panel says so once.

What a page gets (every top-level name starts with `tq`/`TQ`, so it pastes into another module script):
  createTQStation(kind, {THREE, strings, doc}) -> {kind, group, panel, dispose, size, steps, provenance,
                                                   step(), advance(), reset(), onChange(fn)}
  tqPanelModel(kind, strings, stepIndex)       the panel's words and states, pure (no DOM)
  TQ_KINDS, TQ_HALLS, TQ_KEYS, TQ_PROVENANCE    sizes, hall ids, string keys, provenance per kind

    python3 web/tqkit.py            prints the module size and exports
    python3 web/tqkit.py --out F    writes the module to F (web/test_tqkit.mjs imports it)

The API for HALLS is published in $SP/BRIDGE_CONTRACT.md.
"""
import json
import re
import sys

TQ_COMMIT = '3ea15f0'
TQ_SRC = 'artifacts/trade-quest-3d/src/components/game/'

# kind -> hall ids (unions/registry/unions.json slugs; web/test_tqkit.mjs holds every id to that registry)
TQKIT_HALLS = {
    'electrical': {'primary': ['electricians'], 'related': ['ev-charging', 'solar', 'battery-storage']},
    'plumbing': {'primary': ['pipefitters'], 'related': ['water-distrib', 'marine-pipe', 'fire-sprinkler']},
    'hvac': {'primary': ['hvacr', 'sheetmetal'], 'related': ['bas-controls']},
    'carpentry': {'primary': ['carpenters'], 'related': ['drywall', 'lathers']},
}
TQKIT_KINDS = list(TQKIT_HALLS)
TQKIT_I18N_KEYS = (['tqkit.kicker', 'tqkit.step', 'tqkit.done', 'tqkit.next', 'tqkit.reset', 'tqkit.note',
                    'tqkit.authored']
                   + [f'tqkit.{k}.{p}' for k in TQKIT_KINDS for p in ('title', 's1', 's2', 's3', 's4')])

TQKIT_CSS = r'''/* TQ_KIT panel - tokens: TradesQuest radius, focus ring and 44 px targets; SmartCiti dark-first palette */
.tqk-panel{--tqk-bg:#0f172a;--tqk-ink:#e2e8f0;--tqk-muted:#94a3b8;--tqk-line:#334155;--tqk-accent:#f97316;
  --tqk-accent-ink:#0f172a;--tqk-done:#4ade80;--tqk-ring:hsl(24 95% 55%);--tqk-radius:.75rem;
  background:var(--tqk-bg);color:var(--tqk-ink);border:1px solid var(--tqk-line);border-radius:var(--tqk-radius);
  padding-block:.75rem;padding-inline:1rem;max-inline-size:22rem;font:500 .9rem/1.4 system-ui,sans-serif}
@media (prefers-color-scheme:light){:root:not([data-theme="dark"]) .tqk-panel{--tqk-bg:#ffffff;--tqk-ink:#0f172a;
  --tqk-muted:#475569;--tqk-line:#cbd5e1;--tqk-accent:#c2410c;--tqk-accent-ink:#ffffff;--tqk-done:#15803d}}
[data-theme="light"] .tqk-panel{--tqk-bg:#ffffff;--tqk-ink:#0f172a;--tqk-muted:#475569;--tqk-line:#cbd5e1;
  --tqk-accent:#c2410c;--tqk-accent-ink:#ffffff;--tqk-done:#15803d}
.tqk-kicker{margin:0;font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--tqk-muted)}
.tqk-title{margin:.15rem 0 .35rem;font-weight:700;font-size:1rem}
.tqk-progress{margin:0 0 .4rem;color:var(--tqk-muted)}
.tqk-steps{margin:0 0 .6rem;padding-inline-start:1.3rem}
.tqk-steps li{margin-block:.2rem;color:var(--tqk-muted)}
.tqk-steps li[data-state="current"]{color:var(--tqk-ink);font-weight:700}
.tqk-steps li[data-state="done"]{color:var(--tqk-done)}
.tqk-steps li[data-state="done"]::marker{content:"\2713  "}
.tqk-actions{display:flex;gap:.5rem;flex-wrap:wrap}
.tqk-actions button{min-block-size:44px;min-inline-size:44px;padding-inline:.9rem;border-radius:var(--tqk-radius);
  border:1px solid var(--tqk-line);background:transparent;color:var(--tqk-ink);font:inherit;cursor:pointer}
.tqk-actions .tqk-next{background:var(--tqk-accent);border-color:var(--tqk-accent);color:var(--tqk-accent-ink);font-weight:700}
.tqk-actions button:disabled{opacity:.55;cursor:default}
.tqk-actions button:focus-visible{outline:3px solid var(--tqk-ring);outline-offset:2px}
.tqk-note,.tqk-prov{margin:.5rem 0 0;font-size:.75rem;color:var(--tqk-muted)}
@media (prefers-reduced-motion:reduce){.tqk-panel *{transition:none!important;animation:none!important}}
'''

TQKIT_JS = r'''/* TQ_KIT:BEGIN - TradesQuest field-job stations for the SmartCiti.X Holodeck (web/tqkit.py). AUTHORED schematic mock-ups. */
const TQKIT_API = 1;
const TQ_ORIGIN = 'from game-world-focus @__COMMIT__, __SRC__';
const TQ_HALLS = __HALLS__;
const TQ_KEYS = __KEYS__;
const TQ_STEPS = 4;
const TQ_MESH_CAP = 20;
// colours from TradesQuest (Constants.ts COLORS, CarpenterWorkshop.tsx WOOD_COLORS, the object files' literals)
const TQ_C = { metal: '#9ca3af', water: '#a2d2ff', wood: '#8b5a2b', lumber: '#fde68a', benchBase: '#475569',
  benchTop: '#b48a58', panel: '#1f2937', slate: '#334155', zinc: '#d4d4d8', copper: '#b45309', steel: '#94a3b8',
  heater: '#cbd5e1', base: '#475569', warn: '#f97316', ok: '#22c55e', tool: '#38bdf8', tag: '#dc2626',
  stanchion: '#fbbf24', board: '#0f172a', card: '#f8fafc', amber: '#f59e0b', grille: '#1f2937', ply: '#d6b98c' };
const TQ_KINDS = {
  electrical: { size: { w: 2.4, d: 1.2, h: 2.3, clear: 1.2 }, files: ['InteractableObjects.tsx', 'HVACObjects.tsx', 'CarpenterWorkshopObjects.tsx', 'HVACWorkshopObjects.tsx'] },
  plumbing: { size: { w: 2.6, d: 1.4, h: 2.8, clear: 1.2 }, files: ['PlumberWaterHeaterObjects.tsx', 'InteractableObjects.tsx', 'HVACObjects.tsx', 'CarpenterWorkshopObjects.tsx', 'HVACWorkshopObjects.tsx'] },
  hvac: { size: { w: 2.8, d: 1.6, h: 1.9, clear: 1.2 }, files: ['HVACObjects.tsx', 'HVACWorkshopObjects.tsx', 'CarpenterWorkshopObjects.tsx'] },
  carpentry: { size: { w: 3.2, d: 1.6, h: 2.6, clear: 1.2 }, files: ['CarpenterFrameObjects.tsx', 'CarpenterWorkshop.tsx', 'CarpenterWorkshopObjects.tsx', 'HVACObjects.tsx', 'HVACWorkshopObjects.tsx'] },
};
const TQ_PROVENANCE = Object.fromEntries(Object.entries(TQ_KINDS).map(([k, v]) => [k, v.files.map((f) => TQ_ORIGIN + f)]));

function tqNeed(o, k, where) {
  if (o === null || typeof o !== 'object' || !(k in o) || o[k] === undefined) throw new Error('tqkit: ' + where + ' has no ' + k);
  return o[k];
}
function tqKind(kind) {
  if (!Object.prototype.hasOwnProperty.call(TQ_KINDS, kind)) throw new Error('tqkit: unknown kind ' + kind);
  return TQ_KINDS[kind];
}
function tqStr(strings, key) {
  if (strings === null || typeof strings !== 'object' || typeof strings[key] !== 'string' || !strings[key]) throw new Error('tqkit: missing string ' + key);
  return strings[key];
}
function tqFill(s, vars) { return s.replace(/\{(\w+)\}/g, (m, k) => { if (!(k in vars)) throw new Error('tqkit: no value for {' + k + '}'); return String(vars[k]); }); }

/* The panel's words and step states, pure. stepIndex = number of steps done (0..4). */
function tqPanelModel(kind, strings, stepIndex) {
  tqKind(kind);
  if (!Number.isInteger(stepIndex) || stepIndex < 0 || stepIndex > TQ_STEPS) throw new Error('tqkit: bad step ' + stepIndex);
  const p = 'tqkit.' + kind + '.';
  const steps = [1, 2, 3, 4].map((i) => ({ text: tqStr(strings, p + 's' + i),
    state: i <= stepIndex ? 'done' : i === stepIndex + 1 ? 'current' : 'todo' }));
  const done = stepIndex === TQ_STEPS;
  return { kind, title: tqStr(strings, p + 'title'), kicker: tqStr(strings, 'tqkit.kicker'),
    progress: done ? tqStr(strings, 'tqkit.done') : tqFill(tqStr(strings, 'tqkit.step'), { n: stepIndex + 1, total: TQ_STEPS }),
    steps, done, next: tqStr(strings, 'tqkit.next'), reset: tqStr(strings, 'tqkit.reset'),
    note: tqStr(strings, 'tqkit.note'), prov: tqStr(strings, 'tqkit.authored') + ' · from game-world-focus @__COMMIT__' };
}

/* Geometry: origin at floor centre, +y up, walk-up front +z. One mesh = one draw call; the stud row is instanced. */
function tqBuild(THREE, kind) {
  const K = tqKind(kind), S = K.size, group = new THREE.Group();
  group.name = 'tq-station-' + kind;
  const geos = [], mats = [], P = {};
  const mat = (c, o = {}) => { const m = new THREE.MeshStandardMaterial(Object.assign({ color: c, roughness: 0.5 }, o)); mats.push(m); return m; };
  const put = (geo, m, pos, file, rot) => {
    geos.push(geo); const mesh = new THREE.Mesh(geo, m);
    mesh.position.set(pos[0], pos[1], pos[2]); if (rot) mesh.rotation.set(rot[0], rot[1], rot[2]);
    mesh.userData.provenance = TQ_ORIGIN + file; mesh.userData.authored = 'AUTHORED';
    group.add(mesh); return mesh;
  };
  const box = (w, h, d) => new THREE.BoxGeometry(w, h, d);
  const cyl = (r, h, n = 16) => new THREE.CylinderGeometry(r, r, h, n);
  const X0 = -S.w / 2, Z1 = S.d / 2;
  // common: floor zone ring (HVACObjects.tsx Boundary), label board on a safety stanchion
  // (CarpenterWorkshopObjects.tsx), training-tool tray (HVACWorkshopObjects.tsx ToolsStation), lockout tag
  // (HVACObjects.tsx Disconnect), status lamp (HVACObjects.tsx Protection indicator).
  const r = Math.min(S.w, S.d) * 0.42;
  P.zone = put(new THREE.RingGeometry(r * 0.82, r, 32), mat(TQ_C.warn, { emissive: TQ_C.warn, emissiveIntensity: 0.5, side: THREE.DoubleSide }),
    [0, 0.012, Z1 - r - 0.02], 'HVACObjects.tsx', [-Math.PI / 2, 0, 0]);
  put(cyl(0.04, 1.1, 12), mat(TQ_C.stanchion, { roughness: 0.4 }), [X0 + 0.3, 0.55, Z1 - 0.22], 'CarpenterWorkshopObjects.tsx');
  P.board = put(box(0.5, 0.36, 0.04), mat(TQ_C.card, { emissive: TQ_C.amber, emissiveIntensity: 0.25 }), [X0 + 0.3, 1.28, Z1 - 0.22], 'CarpenterWorkshopObjects.tsx', [-0.2, 0.4, 0]);
  const tx = S.w / 2 - 0.55, tz = Z1 - 0.3;
  put(box(0.06, 0.54, 0.06), mat(TQ_C.slate), [tx, 0.27, tz], 'HVACWorkshopObjects.tsx');
  put(box(0.9, 0.08, 0.5), mat(TQ_C.benchBase), [tx, 0.58, tz], 'HVACWorkshopObjects.tsx');
  P.tools = [put(box(0.16, 0.16, 0.26), mat(TQ_C.tool), [tx - 0.28, 0.7, tz], 'HVACWorkshopObjects.tsx'),
    put(cyl(0.07, 0.26, 12), mat(TQ_C.tool), [tx, 0.75, tz], 'HVACWorkshopObjects.tsx'),
    put(box(0.22, 0.08, 0.3), mat(TQ_C.tool), [tx + 0.28, 0.66, tz], 'HVACWorkshopObjects.tsx')];
  let tagAt, lampAt, face = 0;
  if (kind === 'electrical') {
    const f = 'InteractableObjects.tsx';
    put(box(1.6, 2.0, 0.05), mat(TQ_C.ply, { roughness: 0.8 }), [0.2, 1.1, -S.d / 2 + 0.05], f);
    put(box(0.64, 0.95, 0.12), mat(TQ_C.metal, { roughness: 0.4 }), [0.2, 1.45, -S.d / 2 + 0.14], f);
    P.door = put(box(0.58, 0.88, 0.02), mat('#6b7280'), [0.2, 1.45, -S.d / 2 + 0.21], f);
    put(box(0.4, 0.07, 0.04), mat(TQ_C.ok), [0.2, 1.62, -S.d / 2 + 0.23], f);
    put(box(0.14, 0.22, 0.05), mat('#f3f4f6'), [-0.35, 0.45, -S.d / 2 + 0.1], f);
    put(cyl(0.035, 0.28, 10), mat(TQ_C.metal, { metalness: 0.6, roughness: 0.4 }), [0.2, 2.06, -S.d / 2 + 0.14], f);
    tagAt = [0.42, 1.3, -S.d / 2 + 0.26]; lampAt = [0.2, 1.97, -S.d / 2 + 0.24];
  } else if (kind === 'plumbing') {
    const f = 'PlumberWaterHeaterObjects.tsx', hx = -0.55, hz = -0.02;
    put(cyl(0.55, 2.0, 24), mat(TQ_C.heater, { metalness: 0.48, roughness: 0.34 }), [hx, 1.1, hz], f);
    put(new THREE.SphereGeometry(0.55, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), mat(TQ_C.steel, { metalness: 0.5, roughness: 0.3 }), [hx, 2.1, hz], f);
    put(cyl(0.66, 0.1, 24), mat(TQ_C.base, { metalness: 0.55, roughness: 0.32 }), [hx, 0.05, hz], f);
    put(cyl(0.05, 0.5, 16), mat(TQ_C.copper, { metalness: 0.35, roughness: 0.4 }), [hx - 0.25, 2.45, hz], f, [0, 0, Math.PI / 2]);
    put(cyl(0.05, 0.45, 16), mat('#64748b', { metalness: 0.35, roughness: 0.4 }), [hx + 0.25, 2.45, hz], f, [0, 0, Math.PI / 2]);
    P.evidence = put(box(0.14, 0.29, 0.04), mat(TQ_C.amber, { emissive: '#d97706', emissiveIntensity: 0.3 }), [hx, 1.45, hz + 0.56], f);
    const g = 'InteractableObjects.tsx', px = 0.75, pz = -0.4;
    put(cyl(0.08, 0.5, 16), mat(TQ_C.metal, { metalness: 0.8, roughness: 0.3 }), [px, 0.75, pz], g);
    put(cyl(0.08, 0.35, 16), mat(TQ_C.metal, { metalness: 0.8, roughness: 0.3 }), [px + 0.17, 0.5, pz], g, [0, 0, Math.PI / 2]);
    P.puddle = put(new THREE.CircleGeometry(0.34, 24), mat(TQ_C.water, { transparent: true, opacity: 0.55, roughness: 0.1, depthWrite: false }), [px, 0.014, 0.0], g, [-Math.PI / 2, 0, 0]);
    tagAt = [hx + 0.35, 0.9, hz + 0.5]; lampAt = [hx, 2.15, hz + 0.56];
  } else if (kind === 'hvac') {
    const f = 'HVACObjects.tsx';
    put(box(1.0, 0.9, 1.0), mat(TQ_C.zinc, { metalness: 0.3, roughness: 0.45 }), [0.65, 0.45, -0.25], f);
    put(cyl(0.38, 0.04, 20), mat(TQ_C.grille), [0.65, 0.92, -0.25], f);
    put(box(0.08, 1.6, 0.08), mat(TQ_C.slate), [-0.35, 0.8, -S.d / 2 + 0.06], f);
    put(box(0.6, 0.9, 0.24), mat(TQ_C.zinc, { metalness: 0.3, roughness: 0.45 }), [-0.35, 1.2, -S.d / 2 + 0.22], f);
    P.handle = put(box(0.1, 0.36, 0.05), mat(TQ_C.tag), [-0.35, 1.26, -S.d / 2 + 0.37], f, [0.55, 0, 0]);
    put(box(0.32, 0.26, 0.2), mat(TQ_C.panel), [0.2, 1.05, -0.45], f);
    tagAt = [-0.17, 0.98, -S.d / 2 + 0.38]; lampAt = [0.2, 1.24, -0.45];
  } else {
    const f = 'CarpenterFrameObjects.tsx', wz = -S.d / 2 + 0.1;
    put(box(2.7, 0.14, 0.16), mat(TQ_C.lumber, { roughness: 0.8 }), [0, 0.07, wz], f);
    put(box(2.7, 0.14, 0.16), mat(TQ_C.lumber, { roughness: 0.8 }), [0, 2.36, wz], f);
    const studGeo = box(0.05, 2.15, 0.14); geos.push(studGeo);
    const xs = [-1.3, -0.9, -0.5, -0.1, 0.3, 0.7, 1.1, 1.3];
    const studs = new THREE.InstancedMesh(studGeo, mat(TQ_C.lumber, { roughness: 0.8 }), xs.length);
    const m4 = new THREE.Matrix4();
    xs.forEach((x, i) => studs.setMatrixAt(i, m4.makeTranslation(x, 1.215, wz)));
    studs.userData.provenance = TQ_ORIGIN + f; studs.userData.authored = 'AUTHORED'; group.add(studs);
    const b = 'CarpenterWorkshop.tsx';
    put(box(1.5, 0.82, 0.6), mat(TQ_C.benchBase, { roughness: 0.6, metalness: 0.3 }), [0.35, 0.41, -0.15], b);
    put(box(1.6, 0.08, 0.7), mat(TQ_C.benchTop, { roughness: 0.8 }), [0.35, 0.86, -0.15], b);
    put(cyl(0.2, 0.04, 16), mat('#1f2937', { roughness: 0.8 }), [-0.1, 0.92, -0.2], 'CarpenterWorkshopObjects.tsx');
    put(box(0.34, 0.16, 0.24), mat(TQ_C.warn, { roughness: 0.5 }), [0.7, 0.98, -0.2], b);
    tagAt = [0.92, 0.98, -0.06]; lampAt = [0.7, 1.12, -0.2];
  }
  P.tag = [put(box(0.12, 0.16, 0.04), mat(TQ_C.tag), tagAt, 'HVACObjects.tsx'),
    put(new THREE.TorusGeometry(0.055, 0.014, 8, 12), mat('#e5e7eb', { metalness: 0.8 }), [tagAt[0], tagAt[1] + 0.13, tagAt[2]], 'HVACObjects.tsx')];
  P.lamp = put(new THREE.SphereGeometry(0.06, 12, 8), mat(TQ_C.tag, { emissive: TQ_C.tag, emissiveIntensity: 0.65 }), lampAt, 'HVACObjects.tsx');
  group.userData = { tqKind: kind, provenance: TQ_PROVENANCE[kind], authored: 'AUTHORED', tqHit: P.board };
  return { group, parts: P, geos, mats };
}

/* Step visuals, same order as TradesQuest's step feedback: done = green. */
function tqApply(P, done) {
  P.board.material.emissive.set(done >= 1 ? TQ_C.ok : TQ_C.amber);
  const z = done >= 2 ? TQ_C.ok : TQ_C.warn; P.zone.material.color.set(z); P.zone.material.emissive.set(z);
  for (const t of P.tools) t.material.color.set(done >= 3 ? TQ_C.ok : TQ_C.tool);
  const fin = done >= TQ_STEPS;
  for (const t of P.tag) t.visible = fin;
  P.lamp.material.color.set(fin ? TQ_C.ok : TQ_C.tag); P.lamp.material.emissive.set(fin ? TQ_C.ok : TQ_C.tag);
  if (P.handle) { P.handle.rotation.x = fin ? -0.9 : 0.55; P.handle.material.color.set(fin ? '#16a34a' : TQ_C.tag); }
  if (P.puddle) P.puddle.scale.setScalar(done >= 2 ? 0.6 : 1);
  if (P.evidence) P.evidence.material.color.set(done >= 1 ? TQ_C.ok : TQ_C.amber);
}

function tqPanel(doc, model, onNext, onReset) {
  const el = (tag, cls, text) => { const e = doc.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };
  const sec = el('section', 'tqk-panel');
  sec.setAttribute('role', 'region'); sec.setAttribute('data-tq-kind', model.kind);
  const kick = el('p', 'tqk-kicker'), title = el('p', 'tqk-title'), prog = el('p', 'tqk-progress'), ol = el('ol', 'tqk-steps');
  prog.setAttribute('aria-live', 'polite');
  const items = model.steps.map(() => el('li'));
  for (const li of items) ol.append(li);
  const acts = el('div', 'tqk-actions');
  const next = el('button', 'tqk-next'), reset = el('button', 'tqk-reset');
  next.setAttribute('type', 'button'); reset.setAttribute('type', 'button');
  next.addEventListener('click', onNext); reset.addEventListener('click', onReset);
  acts.append(next, reset);
  const note = el('p', 'tqk-note'), prov = el('p', 'tqk-prov');
  sec.append(kick, title, prog, ol, acts, note, prov);
  const render = (m) => {
    sec.setAttribute('aria-label', m.title);
    kick.textContent = m.kicker; title.textContent = m.title; prog.textContent = m.progress;
    m.steps.forEach((s, i) => { const li = items[i]; li.textContent = s.text; li.setAttribute('data-state', s.state);
      if (s.state === 'current') li.setAttribute('aria-current', 'step'); else li.removeAttribute('aria-current'); });
    next.textContent = m.next; reset.textContent = m.reset; next.disabled = m.done;
    note.textContent = m.note; prov.textContent = m.prov;
  };
  render(model);
  return { sec, render };
}

function createTQStation(kind, opts) {
  tqKind(kind);
  const THREE = tqNeed(opts, 'THREE', 'createTQStation opts');
  const strings = tqNeed(opts, 'strings', 'createTQStation opts');
  const doc = tqNeed(opts, 'doc', 'createTQStation opts');      // explicit: a document, or null for no DOM panel
  for (const k of TQ_KEYS) { const own = k.split('.').length === 2 || k.startsWith('tqkit.' + kind + '.'); if (own) tqStr(strings, k); }
  const built = tqBuild(THREE, kind);
  let done = 0, disposed = false;
  const subs = [];
  let ui = null;
  const sync = () => { tqApply(built.parts, done); const m = tqPanelModel(kind, strings, done); if (ui) ui.render(m); for (const f of subs) f(done, m); };
  const api = {
    kind, group: built.group, panel: null, size: Object.assign({}, TQ_KINDS[kind].size), steps: TQ_STEPS,
    provenance: TQ_PROVENANCE[kind].slice(),
    step: () => done,
    advance: () => { if (disposed) throw new Error('tqkit: station disposed'); if (done < TQ_STEPS) { done++; sync(); } return done; },
    reset: () => { if (disposed) throw new Error('tqkit: station disposed'); done = 0; sync(); return done; },
    onChange: (fn) => { subs.push(fn); },
    dispose: () => {
      if (disposed) return; disposed = true;
      if (built.group.parent) built.group.parent.remove(built.group);
      for (const g of built.geos) g.dispose();
      for (const m of built.mats) m.dispose();
      if (api.panel && api.panel.parentNode) api.panel.parentNode.removeChild(api.panel);
      subs.length = 0;
    },
  };
  if (doc) { ui = tqPanel(doc, tqPanelModel(kind, strings, 0), () => api.advance(), () => api.reset()); api.panel = ui.sec; }
  tqApply(built.parts, 0);
  return api;
}
/* TQ_KIT:END */
export { TQKIT_API, TQ_KINDS, TQ_HALLS, TQ_KEYS, TQ_STEPS, TQ_MESH_CAP, TQ_PROVENANCE, TQ_C, tqPanelModel, tqBuild, tqApply, createTQStation };
'''

TQKIT_JS = (TQKIT_JS.replace('__COMMIT__', TQ_COMMIT).replace('__SRC__', TQ_SRC)
            .replace('__HALLS__', json.dumps(TQKIT_HALLS)).replace('__KEYS__', json.dumps(TQKIT_I18N_KEYS)))
EXPORTS = [e.strip() for e in re.findall(r'export \{([^}]*)\}', TQKIT_JS)[0].split(',') if e.strip()]
BEGIN, END = '/* TQ_KIT:BEGIN', '/* TQ_KIT:END */'


def tqkit_inline():
    """The module body without its export line, for pasting into a page's own module script."""
    return TQKIT_JS[:TQKIT_JS.index(END) + len(END)]


if __name__ == '__main__':
    if '--out' in sys.argv:
        open(sys.argv[sys.argv.index('--out') + 1], 'w').write(TQKIT_JS)
    print(f'TQKIT_JS: {len(TQKIT_JS)} bytes, {len(EXPORTS)} exports: {", ".join(EXPORTS)}')
