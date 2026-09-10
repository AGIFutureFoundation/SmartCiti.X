#!/usr/bin/env python3
"""The 3D environment: every hall's floor plan, standing up.

Renders web/trade_craft_3d.html — a Three.js scene generated from the same
registries as every other surface:

  - the hall's rooms extruded from the interiors geometry (12 grid units
    wide, 3 m per unit) as a dollhouse: floor slab, low partitions, a
    district-hued fascia carrying the hall name;
  - the recovered training stations standing as beacons inside the rooms
    their strands own — click one for its lesson, checklist and gradable
    scenario check;
  - the recovered yard prop layout dressed along the apron in front of the
    building (schematic primitives; the geometry is a functional programme,
    not a building survey, and the page says so);
  - hall selector across all 111 halls grouped by district, deep-linkable
    (?hall=slug&lang=xx), UI in every shipped locale.

Three.js is pinned at 0.160.0 — the same major the recovered yard app used —
vendored into web/vendor/ and loaded as ES modules via import map, so the
page works offline and on any static host with no CDN dependency. Serve the
tree over HTTP (python3 -m http.server) — browsers refuse module imports
from file:// URLs. The page holds no data of its own.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def _pack_root():
    for cand in (HERE, *HERE.parents):
        if (cand / 'pack').is_dir() and (cand / 'unions').is_dir():
            return cand
    raise RuntimeError('cannot locate the packs from ' + str(HERE))


ROOT = _pack_root()
sys.path.insert(0, str(ROOT / 'web'))
from interiors import build as build_interiors  # noqa: E402
from mapdata import strand_modules, PIPELINE_JS  # noqa: E402

manifest = json.load(open(ROOT / 'pack/manifest.json'))
L = manifest['ledger']
halls_json = json.load(open(ROOT / 'pack/registry/halls.json'))['halls']
districts_reg = json.load(open(ROOT / 'unions/registry/districts.json'))['districts']
stations_reg = json.load(open(ROOT / 'stations/registry/stations.json'))
yard = json.load(open(ROOT / 'archive/bac_yard_stations.json'))['yard_placements']

HUES = {'structural': 210, 'envelope': 28, 'systems': 182, 'energy': 48,
        'earthworks': 100, 'industry': 348, 'transport': 262, 'control': 148}


def hall_level_states(slug):
    doc = json.load(open(ROOT / f'pack/registry/halls/{slug}.json'))
    c = {'live': 0, 'calibrating': 0, 'schema_ok': 0, 'draft': 0}
    for lv in doc['levels']:
        c[lv['state']] += 1
    return c


census = {h['slug']: hall_level_states(h['slug']) for h in halls_json}
per_level = L['slots_per_level'] * L['variants_per_lesson']
plans = build_interiors(halls_json, lambda i: {
    k: v * per_level for k, v in census[halls_json[i]['slug']].items()})

district_of = {slug: k for k, d in districts_reg.items() for slug in d['halls']}

stations_by_hall = {}
for s in stations_reg['stations']:
    stations_by_hall.setdefault(s['hall'], []).append(s['station_id'])

HALLS = [{
    'slug': h['slug'], 'name': h['name'], 'focus': h['focus'],
    'index': h['index'], 'district': district_of[h['slug']],
    'rooms': [{'strand': r['strand'], 'label': r['label'],
               'purpose': r['purpose'], 'fixtures': r['fixtures'],
               'x': r['x'], 'y': r['y'], 'w': r['w'], 'h': r['h']}
              for r in plans[h['slug']]['rooms']],
    'depth': plans[h['slug']]['envelope']['d'],
    'stations': stations_by_hall.get(h['slug'], []),
} for h in halls_json]

I18N = {}
for f in sorted((ROOT / 'i18n/locales').glob('*.json')):
    c = json.load(open(f))
    s = c['strings']
    I18N[c['locale']] = {
        'language': c['language'], 'dir': c['dir'],
        'strings': {k: s[k] for k in (
            'nav.campus', 'language.select', 'hall.rooms', 'hall.stations',
            'station.checklist', 'station.quiz', 'ui.close',
            'map.layer.modules', 'figures.modules', 'figures.lessons',
            'figures.halls', 'figures.districts', 'view.campus', 'ui.walk',
            'hint.campus', 'hint.walk',
            'honesty.taxonomy', 'honesty.content')},
        'districts': {k: v['name'] for k, v in c['districts'].items()},
        'strands': c['strands'], 'tiers': c['tiers'], 'states': c['states'],
    }

DATA = json.dumps({
    'districts': {k: {'name': d['name'], 'halls': d['halls'], 'hue': HUES[k]}
                  for k, d in districts_reg.items()},
    'halls': HALLS,
    'stations': {s['station_id']: {k: s[k] for k in (
        'station_id', 'name', 'hall', 'room', 'strand', 'tier',
        'lesson', 'checklist', 'doctrine', 'quiz')}
        for s in stations_reg['stations']},
    'yard': yard,
    'strandmods': strand_modules(),
    'i18n': I18N,
}, ensure_ascii=False, separators=(',', ':'))

page = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SmartCiti.X : Trade Craft Academy — 3D hall environment</title>
<style>
:root{
  --plate:#12181B; --panel:#182023; --sunk:#0C1113; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --mark-ink:#12181B; --steel:#41C4D4;
  --good:#5CB584; --crit:#E07C68;
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--plate);color:var(--ink);
  font:14px/1.5 "IBM Plex Sans",system-ui,sans-serif;overflow:hidden}
#bar{position:fixed;top:0;left:0;right:0;z-index:5;display:flex;flex-wrap:wrap;
  gap:8px 14px;align-items:center;padding:10px 16px;
  background:color-mix(in oklab, var(--plate) 86%, transparent);
  border-bottom:2px solid var(--mark);backdrop-filter:blur(6px)}
#bar .brand{font:700 19px/1 "Barlow Condensed",system-ui,sans-serif;white-space:nowrap}
#bar .brand .x{color:var(--mark)}
#bar a{color:var(--steel);text-decoration:none;font-size:13px;white-space:nowrap}
select{background:var(--panel);color:var(--ink);border:1px solid var(--rule);
  border-radius:6px;padding:6px 9px;font:inherit;max-width:46vw}
#lang{margin-inline-start:auto}
.barbtn{background:var(--panel);color:var(--ink);border:1px solid var(--rule);
  border-radius:6px;padding:6px 11px;font:inherit;cursor:pointer;white-space:nowrap}
.barbtn:hover{border-color:var(--mark)}
#cross{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);z-index:6;
  color:var(--mark);font:400 26px/1 "IBM Plex Mono",monospace;display:none;
  pointer-events:none;text-shadow:0 0 6px rgba(0,0,0,.8)}
#hud{position:fixed;left:16px;bottom:14px;z-index:5;max-width:min(430px,86vw);
  background:color-mix(in oklab, var(--panel) 90%, transparent);
  border:1px solid var(--rule);border-radius:9px;padding:10px 14px}
#hud h2{font:600 20px "Barlow Condensed",sans-serif;margin:0}
#hud .focus{color:var(--muted);font-size:12.5px;margin:2px 0 0}
#hud .hint{color:var(--muted);font-size:11.5px;margin:6px 0 0}
#honesty{position:fixed;right:16px;bottom:14px;z-index:5;max-width:300px;
  color:var(--muted);font-size:10.5px;text-align:end;opacity:.85}
canvas{display:block}
#nogl{display:none;position:fixed;inset:0;place-content:center;text-align:center;
  color:var(--muted);padding:40px}
/* station panel */
#ov{position:fixed;inset:0;background:rgba(6,10,12,.7);display:none;z-index:9}
#panel{position:fixed;top:0;inset-inline-end:0;bottom:0;width:min(480px,100%);
  background:var(--panel);border-inline-start:1px solid var(--rule);z-index:10;
  transform:translateX(105%);transition:transform .22s ease;overflow-y:auto;
  padding:20px 22px 40px}
html[dir="rtl"] #panel{transform:translateX(-105%)}
body.open #ov{display:block}
body.open #panel{transform:none}
#panel h2{font:600 22px "Barlow Condensed",sans-serif;margin:2px 0 4px;
  padding-inline-end:70px}
#panel .chip{display:inline-block;border:1px solid var(--rule);border-radius:999px;
  padding:2px 10px;font-size:12px;color:var(--muted);margin:0 4px 10px 0}
#panel h3{font:600 14px "Barlow Condensed",sans-serif;letter-spacing:.04em;
  text-transform:uppercase;color:var(--steel);margin:16px 0 6px}
#panel ul{margin:4px 0;padding-inline-start:20px;color:var(--muted)}
#pclose{position:absolute;top:12px;inset-inline-end:14px;background:none;
  border:1px solid var(--rule);color:var(--muted);border-radius:6px;
  padding:5px 11px;cursor:pointer;font:inherit}
.q{background:var(--sunk);border-radius:6px;padding:9px 12px;margin-top:8px}
.q .opt{display:block;background:none;border:1px solid var(--rule);color:var(--ink);
  border-radius:5px;padding:6px 9px;margin:5px 0;cursor:pointer;font:inherit;
  width:100%;text-align:start}
.q .opt.ok{border-color:var(--good);color:var(--good)}
.q .opt.bad{border-color:var(--crit);color:var(--crit)}
@media(prefers-reduced-motion:reduce){#panel{transition:none}}
</style>
</head>
<body>
<div id="bar">
  <span class="brand">SmartCiti<span class="x">.X</span> : Trade Craft Academy</span>
  <a href="trade_craft_interactive.html" id="back"></a>
  <select id="hall" aria-label="hall"></select>
  <button id="campusBtn" class="barbtn"></button>
  <button id="walkBtn" class="barbtn"></button>
  <select id="lang"></select>
</div>
<div id="hud"><h2 id="hname"></h2><p class="focus" id="hfocus"></p><p class="hint" id="hint"></p></div>
<div id="honesty"></div>
<div id="nogl"></div>
<div id="cross">+</div>
<div id="ov"></div>
<aside id="panel"><button id="pclose"></button><div id="pbody"></div></aside>
<script id="data" type="application/json">__DATA__</script>
<script type="importmap">
{"imports":{
  "three":"./vendor/three.module.min.js",
  "three/addons/":"./vendor/addons/"
}}
</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { PointerLockControls } from 'three/addons/controls/PointerLockControls.js';

const D = JSON.parse(document.getElementById('data').textContent);
const params = new URLSearchParams(location.search);
let loc = D.i18n[params.get('lang')] ? params.get('lang') : 'en';
let slug = D.halls.some(h => h.slug === params.get('hall')) ? params.get('hall') : 'bricklayers';
let view = D.halls.some(h => h.slug === params.get('hall')) ? 'hall' : 'campus';
const t = (k) => D.i18n[loc].strings[k] ?? D.i18n.en.strings[k] ?? k;
const U = 3;                       // metres per grid unit
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ------------------------------------------------------------- scene ---- */
let renderer;
try {
  renderer = new THREE.WebGLRenderer({ antialias: true });
} catch (e) {
  document.getElementById('nogl').style.display = 'grid';
  document.getElementById('nogl').textContent =
    'WebGL is unavailable in this browser; the 3D environment needs it. ' +
    'The interactive map carries the same content in 2D.';
  throw e;
}
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x12181B);
scene.fog = new THREE.Fog(0x12181B, 70, 170);

const camera = new THREE.PerspectiveCamera(50, innerWidth/innerHeight, .1, 900);
camera.position.set(30, 26, 42);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI * .49;
controls.minDistance = 8; controls.maxDistance = 120;
controls.autoRotate = !reduced;
controls.autoRotateSpeed = .45;
controls.addEventListener('start', () => { controls.autoRotate = false; });

scene.add(new THREE.HemisphereLight(0x9fb4bd, 0x1a1512, .85));
const key = new THREE.DirectionalLight(0xffe0b0, 1.6);
key.position.set(35, 48, 20);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
const S = 60;
Object.assign(key.shadow.camera, { left: -S, right: S, top: S, bottom: -S, far: 140 });
scene.add(key);
const fill = new THREE.DirectionalLight(0x41C4D4, .25);
fill.position.set(-30, 20, -30);
scene.add(fill);

// ground: dark apron with a faint work grid
const ground = new THREE.Mesh(
  new THREE.CircleGeometry(260, 64),
  new THREE.MeshStandardMaterial({ color: 0x0e1416, roughness: .96 }));
ground.rotation.x = -Math.PI/2; ground.receiveShadow = true;
scene.add(ground);
const grid = new THREE.GridHelper(520, 130, 0x28353A, 0x1b2427);
grid.position.y = .02; scene.add(grid);

const mat = {
  slab:  new THREE.MeshStandardMaterial({ color: 0x232b2e, roughness: .9 }),
  wall:  new THREE.MeshStandardMaterial({ color: 0x39454a, roughness: .85 }),
  part:  new THREE.MeshStandardMaterial({ color: 0x2c3639, roughness: .85 }),
  post:  new THREE.MeshStandardMaterial({ color: 0xE8A33D, roughness: .45,
                                          emissive: 0x7a4d08 }),
  steel: new THREE.MeshStandardMaterial({ color: 0x41C4D4, roughness: .5 }),
  wood:  new THREE.MeshStandardMaterial({ color: 0x8a6a42, roughness: .9 }),
  metal: new THREE.MeshStandardMaterial({ color: 0x8f9a9d, roughness: .55,
                                          metalness: .55 }),
  brick: new THREE.MeshStandardMaterial({ color: 0xb3462f, roughness: .92 }),
  block: new THREE.MeshStandardMaterial({ color: 0x9aa0a2, roughness: .92 }),
  cone:  new THREE.MeshStandardMaterial({ color: 0xE07C48, roughness: .6 }),
};

function label(text, sub, scale = 1) {
  const c = document.createElement('canvas');
  const ctx = c.getContext('2d');
  ctx.font = '600 44px "Barlow Condensed", sans-serif';
  const w = Math.max(ctx.measureText(text).width, 120) + 40;
  c.width = w; c.height = sub ? 110 : 72;
  ctx.fillStyle = 'rgba(12,17,19,.82)';
  ctx.beginPath(); ctx.roundRect(0, 0, c.width, c.height, 14); ctx.fill();
  ctx.fillStyle = '#E8EDEC';
  ctx.font = '600 44px "Barlow Condensed", sans-serif';
  ctx.fillText(text, 20, 50);
  if (sub) { ctx.fillStyle = '#93A3A6'; ctx.font = '28px "IBM Plex Sans", sans-serif';
             ctx.fillText(sub, 20, 90); }
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({
    map: new THREE.CanvasTexture(c), transparent: true, depthTest: false }));
  sp.scale.set(c.width/90*scale, c.height/90*scale, 1);
  return sp;
}

function box(w, h, d, m, x, y, z, group, shadow = true) {
  const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m);
  b.position.set(x, y, z);
  b.castShadow = shadow; b.receiveShadow = true;
  group.add(b); return b;
}

/* ------------------------------------------------------- yard props ----- */
const PROPS = {
  sawhorse: (g,x,z) => { box(1.6,.1,.25,mat.wood,x,.75,z,g);
    for (const dx of [-.65,.65]) { box(.08,.8,.5,mat.wood,x+dx,.4,z,g); } },
  wheelbarrow: (g,x,z) => { box(.9,.35,.6,mat.metal,x,.45,z,g);
    box(.06,.5,.06,mat.metal,x+.6,.3,z-.2,g); box(.06,.5,.06,mat.metal,x+.6,.3,z+.2,g);
    const wheel = new THREE.Mesh(new THREE.TorusGeometry(.2,.07,8,20), mat.part);
    wheel.position.set(x-.5,.2,z); wheel.castShadow = true; g.add(wheel); },
  mixer: (g,x,z) => { box(1,.7,.8,mat.metal,x,.35,z,g);
    const drum = new THREE.Mesh(new THREE.CylinderGeometry(.45,.3,.9,14), mat.cone);
    drum.rotation.z = .7; drum.position.set(x,.95,z); drum.castShadow = true; g.add(drum); },
  cone: (g,x,z) => { const c = new THREE.Mesh(new THREE.ConeGeometry(.28,.7,12), mat.cone);
    c.position.set(x,.35,z); c.castShadow = true; g.add(c);
    box(.55,.05,.55,mat.cone,x,.02,z,g,false); },
  ladder: (g,x,z) => { for (const dx of [-.28,.28]) box(.07,2.6,.07,mat.metal,x+dx,1.3,z,g);
    for (let i=0;i<6;i++) box(.6,.05,.05,mat.metal,x,.3+i*.42,z,g,false); },
  toolbox: (g,x,z) => { box(.8,.45,.45,mat.steel,x,.25,z,g); },
  rebar: (g,x,z) => { for (let i=0;i<5;i++)
    box(.05,.05,2.4,mat.metal,x+i*.09,.1+i*.02,z,g,false); },
  generator: (g,x,z) => { box(1.2,.9,.8,mat.part,x,.45,z,g);
    box(.1,.5,.1,mat.metal,x+.4,1.1,z,g,false); },
  signStand: (g,x,z) => { box(.08,1.5,.08,mat.metal,x,.75,z,g);
    box(.9,.6,.06,mat.post,x,1.5,z,g,false); },
  brickPallet: (g,x,z) => { box(1.1,.12,1.1,mat.wood,x,.06,z,g,false);
    box(.95,.55,.95,mat.brick,x,.42,z,g); },
  blockPallet: (g,x,z) => { box(1.1,.12,1.1,mat.wood,x,.06,z,g,false);
    box(.95,.6,.95,mat.block,x,.45,z,g); },
};

/* ---------------------------------------------------------- the hall ---- */
let hallGroup = null, beacons = [], floors = [];

function buildHall(sg) {
  if (hallGroup) { scene.remove(hallGroup); hallGroup.traverse(o => {
    o.geometry?.dispose(); }); }
  hallGroup = new THREE.Group(); beacons = []; floors = [];
  const h = D.halls.find(x => x.slug === sg);
  const hue = D.districts[h.district].hue;
  const W = 12 * U, DEP = h.depth * U;
  const cx = (x) => x - W/2, cz = (z) => z - DEP/2;   // centre the building

  // slab and perimeter (front face open)
  box(W + .6, .35, DEP + .6, mat.slab, 0, .17, 0, hallGroup);
  box(W, 3.2, .25, mat.wall, 0, 1.95, cz(DEP), hallGroup);          // back
  box(.25, 3.2, DEP, mat.wall, cx(0), 1.95, 0, hallGroup);          // left
  box(.25, 3.2, DEP, mat.wall, cx(W), 1.95, 0, hallGroup);          // right
  // district fascia over the open front
  const fascia = new THREE.Mesh(new THREE.BoxGeometry(W + .8, .55, .5),
    new THREE.MeshStandardMaterial({
      color: new THREE.Color().setHSL(hue/360, .55, .5), roughness: .5 }));
  fascia.position.set(0, 3.6, cz(0)); fascia.castShadow = true;
  hallGroup.add(fascia);
  const sign = label(h.name, D.i18n[loc].districts[h.district], 1.35);
  sign.position.set(0, 5.1, cz(0)); hallGroup.add(sign);

  // rooms: tinted floor + low partitions + label
  const stns = h.stations.map(id => D.stations[id]);
  for (const r of h.rooms) {
    const rw = r.w * U, rd = r.h * U;
    const rx = cx(r.x * U + rw/2), rz = cz(r.y * U + rd/2);
    const floor = new THREE.Mesh(new THREE.BoxGeometry(rw - .3, .06, rd - .3),
      new THREE.MeshStandardMaterial({
        color: new THREE.Color().setHSL(hue/360, .18, .16), roughness: .95 }));
    floor.position.set(rx, .38, rz); floor.receiveShadow = true;
    floor.userData.room = r.label;
    hallGroup.add(floor); floors.push(floor);
    // safety rooms carry a hazard-stripe threshold at the doorway
    if (r.strand === 'safety') {
      const stripe = new THREE.Mesh(new THREE.BoxGeometry(Math.min(rw-.6,2.4), .07, .5),
        mat.post);
      stripe.position.set(rx, .42, rz + rd/2 - .4); hallGroup.add(stripe);
    }
    // the trade's own fixtures, benched along the back of the room
    (r.fixtures || []).slice(0, 3).forEach((fx, fi) => {
      const bx = rx - rw/2 + (fi + 1) * rw / ((r.fixtures.length||1) + 1);
      const bz = rz - rd/2 + .8;
      box(1.3, .12, .7, mat.steel, bx, .95, bz, hallGroup);
      box(.12, .5, .6, mat.part, bx - .5, .62, bz, hallGroup);
      box(.12, .5, .6, mat.part, bx + .5, .62, bz, hallGroup);
      box(.5, .35, .35, mat.metal, bx, 1.25, bz, hallGroup);
      const fl = label(fx, null, .34);
      fl.position.set(bx, 1.85, bz); hallGroup.add(fl);
    });
    box(rw, 1.1, .12, mat.part, rx, .9, rz - rd/2, hallGroup);
    box(rw, 1.1, .12, mat.part, rx, .9, rz + rd/2, hallGroup);
    box(.12, 1.1, rd, mat.part, rx - rw/2, .9, rz, hallGroup);
    box(.12, 1.1, rd, mat.part, rx + rw/2, .9, rz, hallGroup);
    const lab = label(r.label, D.i18n[loc].strands[r.strand], .55);
    lab.position.set(rx, 2.2, rz); hallGroup.add(lab);

    // stations standing in this room
    const here = stns.filter(s => s.room === r.label);
    here.forEach((s, i) => {
      const px = rx - rw/2 + (i + 1) * rw / (here.length + 1);
      const post = new THREE.Mesh(new THREE.CylinderGeometry(.09, .12, 1.5, 10), mat.post);
      post.position.set(px, 1.1, rz); post.castShadow = true;
      const gem = new THREE.Mesh(new THREE.OctahedronGeometry(.34), mat.post);
      gem.position.set(px, 2.15, rz); gem.castShadow = true;
      gem.userData.station = s.station_id; gem.userData.spin = true;
      post.userData.station = s.station_id;
      hallGroup.add(post, gem); beacons.push(gem, post);
    });
  }

  // the apron: recovered yard layout for seeded halls, a light deterministic
  // dressing for the rest. Original yard coords span ±16; fold them onto the
  // strip in front of the open face.
  const props = h.stations.length ? D.yard
    : Array.from({ length: 7 }, (_, i) => {
        const keys = Object.keys(PROPS);
        return { t: keys[(h.index * 7 + i * 3) % keys.length],
                 p: [((h.index + i * 5) % 13) - 6 + ((i % 2) ? 8 : -8), 0, -(4 + (i * 2.4) % 10)] };
      });
  for (const pr of props) {
    const fn = PROPS[pr.t]; if (!fn) continue;
    const px = pr.p[0] * (h.stations.length ? .95 : 1);
    const pz = h.stations.length ? -(DEP/2 + 3 + (pr.p[2] + 16) * .42) : cz(0) + pr.p[2];
    if (Math.abs(px) > 60 || Math.abs(pz) > 60) continue;
    fn(hallGroup, px, pz);
  }
  scene.add(hallGroup);

  document.getElementById('hname').textContent = h.name;
  document.getElementById('hfocus').textContent = h.focus;
}

/* -------------------------------------------------------- campus view --- */
let campusGroup = null, buildings = [], campusSpin = [];

function buildCampus() {
  if (campusGroup) scene.remove(campusGroup);
  campusGroup = new THREE.Group(); buildings = []; campusSpin = [];
  const dkeys = Object.keys(D.districts);
  dkeys.forEach((k, di) => {
    const d = D.districts[k];
    const ang = di / dkeys.length * Math.PI * 2;
    const rad = new THREE.Vector2(Math.cos(ang), Math.sin(ang));
    const lat = new THREE.Vector2(-rad.y, rad.x);
    const cx = rad.x * 108, cz = rad.y * 108;
    const cols = Math.ceil(Math.sqrt(d.halls.length * 1.7));
    d.halls.forEach((sg, i) => {
      const h = D.halls.find(x => x.slug === sg);
      const gx = (i % cols) - (cols - 1) / 2, gz = Math.floor(i / cols);
      const bx = cx + lat.x * gx * 16 + rad.x * gz * 15;
      const bz = cz + lat.y * gx * 16 + rad.y * gz * 15;
      const dep = Math.max(h.depth, 5);
      const bld = box(12, 6.5, dep, mat.wall, bx, 3.25, bz, campusGroup);
      bld.userData.slug = sg; buildings.push(bld);
      const band = new THREE.Mesh(new THREE.BoxGeometry(12.4, .9, dep + .4),
        new THREE.MeshStandardMaterial({
          color: new THREE.Color().setHSL(d.hue/360, .5, .45), roughness: .6 }));
      band.position.set(bx, 6.2, bz); campusGroup.add(band);
      if (h.stations.length) {
        const bcn = new THREE.Mesh(new THREE.OctahedronGeometry(.9), mat.post);
        bcn.position.set(bx, 8.6, bz); campusGroup.add(bcn); campusSpin.push(bcn);
      }
    });
    const dl = label(D.i18n[loc].districts[k], null, 3);
    dl.position.set(cx - rad.x * 14, 15, cz - rad.y * 14);
    campusGroup.add(dl);
  });
  const plaza = new THREE.Mesh(new THREE.CylinderGeometry(26, 26, .3, 48),
    new THREE.MeshStandardMaterial({ color: 0x1c2427, roughness: .95 }));
  plaza.position.y = .15; plaza.receiveShadow = true; campusGroup.add(plaza);
  const sign = label('SmartCiti.X : Trade Craft Academy', 'powered by AGI Corp', 3.4);
  sign.position.set(0, 18, 0); campusGroup.add(sign);
  scene.add(campusGroup);
}

function showCampus() {
  view = 'campus';
  if (walkActive) plc.unlock();
  if (hallGroup) hallGroup.visible = false;
  buildCampus();
  scene.fog.near = 160; scene.fog.far = 640;
  controls.maxDistance = 420; controls.minDistance = 20;
  camera.position.set(0, 175, 205); controls.target.set(0, 0, 0);
  document.getElementById('hname').textContent = t('view.campus');
  document.getElementById('hfocus').textContent =
    t('figures.halls').replace('{n}', D.halls.length) + ' · ' +
    t('figures.districts').replace('{n}', Object.keys(D.districts).length);
  document.getElementById('hint').textContent = t('hint.campus');
  document.getElementById('walkBtn').style.display = 'none';
  syncURL();
}

function showHall(sg) {
  slug = sg; view = 'hall';
  if (campusGroup) campusGroup.visible = false;
  buildHall(sg);
  scene.fog.near = 70; scene.fog.far = 170;
  controls.maxDistance = 120; controls.minDistance = 8;
  camera.position.set(30, 26, 42); controls.target.set(0, 2, 0);
  document.getElementById('hint').textContent =
    '● ' + t('hall.stations') + ' · ' + t('hall.rooms') + ' → ' + t('map.layer.modules');
  document.getElementById('walkBtn').style.display =
    ('ontouchstart' in window) ? 'none' : '';
  syncURL();
}

/* ----------------------------------------------------------- walk mode --- */
const plc = new PointerLockControls(camera, renderer.domElement);
let walkActive = false;
const keys = {};
document.addEventListener('keydown', (e) => { keys[e.code] = true; });
document.addEventListener('keyup', (e) => { keys[e.code] = false; });

function enterWalk() {
  if (view !== 'hall') return;
  const h = D.halls.find(x => x.slug === slug);
  controls.autoRotate = false; controls.enabled = false;
  camera.position.set(0, 1.7, -(h.depth * U) / 2 - 8);
  camera.lookAt(0, 1.7, 0);
  plc.lock();
}
plc.addEventListener('lock', () => {
  walkActive = true;
  document.getElementById('cross').style.display = 'block';
  document.getElementById('hint').textContent = t('hint.walk');
});
plc.addEventListener('unlock', () => {
  walkActive = false;
  document.getElementById('cross').style.display = 'none';
  controls.enabled = true;
  const fwd = new THREE.Vector3(); camera.getWorldDirection(fwd);
  controls.target.copy(camera.position).addScaledVector(fwd, 6);
  if (view === 'hall') document.getElementById('hint').textContent =
    '● ' + t('hall.stations') + ' · ' + t('hall.rooms') + ' → ' + t('map.layer.modules');
});

function walkStep(dt) {
  const h = D.halls.find(x => x.slug === slug);
  const sp = (keys.ShiftLeft || keys.ShiftRight ? 10 : 5) * dt;
  if (keys.KeyW || keys.ArrowUp) plc.moveForward(sp);
  if (keys.KeyS || keys.ArrowDown) plc.moveForward(-sp);
  if (keys.KeyA || keys.ArrowLeft) plc.moveRight(-sp);
  if (keys.KeyD || keys.ArrowRight) plc.moveRight(sp);
  const DEP = h.depth * U;
  camera.position.x = Math.min(21, Math.max(-21, camera.position.x));
  camera.position.z = Math.min(DEP/2 - .8, Math.max(-DEP/2 - 26, camera.position.z));
  camera.position.y = 1.7;
}

/* ---------------------------------------------------------------- UI ---- */
function renderChrome() {
  const i = D.i18n[loc];
  document.documentElement.lang = loc;
  document.documentElement.dir = i.dir;
  document.getElementById('back').textContent = '← ' + t('nav.campus');
  const hall = document.getElementById('hall');
  hall.innerHTML = Object.entries(D.districts).map(([k, d]) =>
    `<optgroup label="${i.districts[k]}">` +
    d.halls.map(sg => `<option value="${sg}" ${sg===slug?'selected':''}>` +
      `${D.halls.find(x=>x.slug===sg).name}${D.halls.find(x=>x.slug===sg).stations.length?' ●':''}</option>`).join('') +
    `</optgroup>`).join('');
  const lang = document.getElementById('lang');
  lang.setAttribute('aria-label', t('language.select'));
  lang.innerHTML = Object.entries(D.i18n).map(([c, v]) =>
    `<option value="${c}" ${c===loc?'selected':''}>${v.language}</option>`).join('');
  document.getElementById('campusBtn').textContent = '⌂ ' + t('view.campus');
  document.getElementById('walkBtn').textContent = '⤞ ' + t('ui.walk');
  document.getElementById('honesty').textContent =
    t('honesty.taxonomy') + ' ' + t('honesty.content');
  document.getElementById('pclose').textContent = t('ui.close');
}

function openStation(id) {
  const s = D.stations[id]; const i = D.i18n[loc];
  document.getElementById('pbody').innerHTML = `
    <h2>${s.name}</h2>
    <span class="chip">${s.room}</span><span class="chip">${i.strands[s.strand]} · ${i.tiers[s.tier]}</span>
    <p>${s.lesson}</p><p style="color:var(--muted)">${s.doctrine}</p>
    <h3>${t('station.checklist')}</h3><ul>${s.checklist.map(c=>`<li>${c}</li>`).join('')}</ul>
    <h3>${t('station.quiz')}</h3><div class="q">${s.quiz.question}
      ${s.quiz.options.map(o=>`<button class="opt" data-ok="${o.correct?1:0}">${o.label}</button>`).join('')}</div>`;
  document.body.classList.add('open');
}

__PIPELINE_JS__

function openRoom(roomLabel) {
  const h = D.halls.find(x => x.slug === slug);
  const r = h.rooms.find(x => x.label === roomLabel);
  const i = D.i18n[loc];
  const sm = D.strandmods[r.strand];
  const F = (n) => n.toLocaleString('en-US');
  const rows = sm.samples.map(x => {
    const id = 'u' + String(h.index).padStart(3, '0') + '.' + x.suffix;
    const st = pipeline(h.index, x.level);
    return `
    <tr><td style="font-family:'IBM Plex Mono',monospace;font-size:12px">${id}</td>
    <td>${i.tiers[x.tier]}</td><td>${x.form}</td>
    <td style="text-align:end">${x.d}</td><td>${i.states[st]}</td></tr>`; }).join('');
  document.getElementById('pbody').innerHTML = `
    <h2>${r.label}</h2>
    <span class="chip">${i.strands[r.strand]}</span>
    <span class="chip">${r.w*3}×${r.h*3} m</span>
    <p style="color:var(--muted)">${r.purpose}</p>
    ${r.fixtures?.length ? `<ul>${r.fixtures.map(f=>`<li>${f}</li>`).join('')}</ul>` : ''}
    <h3>${t('map.layer.modules')}</h3>
    <p style="color:var(--muted);font-size:13px">
      ${t('figures.lessons').replace('{n}', F(sm.lessons))} ·
      ${t('figures.modules').replace('{n}', F(sm.modules))} ·
      θ ${sm.d_from}–${sm.d_to}</p>
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <tbody>${rows}</tbody></table>
    <style>#pbody td{border-top:1px solid var(--rule);padding:6px 8px;color:var(--muted)}</style>`;
  document.body.classList.add('open');
}

const ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
renderer.domElement.addEventListener('pointerdown', (e) => {
  if (walkActive) ptr.set(0, 0);
  else ptr.set(e.clientX/innerWidth*2-1, -(e.clientY/innerHeight)*2+1);
  ray.setFromCamera(ptr, camera);
  if (view === 'campus') {
    const bhit = ray.intersectObjects(buildings, false)[0];
    if (bhit?.object.userData.slug) showHall(bhit.object.userData.slug);
    return;
  }
  const hit = ray.intersectObjects(beacons, false)[0];
  if (hit?.object.userData.station) {
    if (walkActive) plc.unlock();
    return openStation(hit.object.userData.station);
  }
  if (walkActive) return;
  const fhit = ray.intersectObjects(floors, false)[0];
  if (fhit?.object.userData.room) openRoom(fhit.object.userData.room);
});
let hoverPending = false;
renderer.domElement.addEventListener('pointermove', (e) => {
  if (view !== 'campus' || hoverPending) return;
  hoverPending = true;
  requestAnimationFrame(() => {
    hoverPending = false;
    ptr.set(e.clientX/innerWidth*2-1, -(e.clientY/innerHeight)*2+1);
    ray.setFromCamera(ptr, camera);
    const bhit = ray.intersectObjects(buildings, false)[0];
    if (bhit?.object.userData.slug) {
      const h = D.halls.find(x => x.slug === bhit.object.userData.slug);
      document.getElementById('hname').textContent = h.name;
      document.getElementById('hfocus').textContent = h.focus;
      renderer.domElement.style.cursor = 'pointer';
    } else {
      renderer.domElement.style.cursor = '';
    }
  });
});
document.addEventListener('click', (e) => {
  if (e.target.closest('#pclose') || e.target.id === 'ov')
    document.body.classList.remove('open');
  const opt = e.target.closest('.opt');
  if (opt) { opt.parentElement.querySelectorAll('.opt').forEach(o =>
      o.classList.toggle('ok', o.dataset.ok === '1'));
    if (opt.dataset.ok !== '1') opt.classList.add('bad'); }
});
document.getElementById('hall').addEventListener('change', (e) => {
  showHall(e.target.value);
});
document.getElementById('campusBtn').addEventListener('click', showCampus);
document.getElementById('walkBtn').addEventListener('click', enterWalk);
document.getElementById('lang').addEventListener('change', (e) => {
  loc = e.target.value; renderChrome();
  if (view === 'campus') showCampus(); else showHall(slug);
});
function syncURL() {
  history.replaceState(null, '', view === 'campus'
    ? `?lang=${loc}` : `?hall=${slug}&lang=${loc}`);
}
addEventListener('resize', () => {
  camera.aspect = innerWidth/innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

renderChrome();
if (view === 'hall') showHall(slug); else showCampus();
// test hook: lets the harness assert scene state without poking internals
window.__tc3d = () => ({ view, buildings: buildings.length,
  beacons: beacons.length, floors: floors.length, slug, loc, walkActive });
const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = clock.getDelta();
  if (!reduced) {
    for (const b of beacons) if (b.userData.spin) b.rotation.y += dt * 1.4;
    for (const b of campusSpin) b.rotation.y += dt * 1.1;
  }
  if (walkActive) walkStep(dt);
  else controls.update();
  renderer.render(scene, camera);
});
</script>
</body>
</html>
'''

page = page.replace('__DATA__', DATA).replace('__PIPELINE_JS__', PIPELINE_JS)
out = HERE / 'trade_craft_3d.html'
out.write_text(page)
print(f"written: {len(page):,} bytes | {len(HALLS)} halls | "
      f"{stations_reg['count']} stations | {len(I18N)} locales")
