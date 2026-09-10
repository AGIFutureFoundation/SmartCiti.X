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
campuses_reg = json.load(open(ROOT / 'unions/registry/campuses.json'))['campuses']
finishes_reg = json.load(open(ROOT / 'surfaces/registry/finishes.json'))
geo_reg = json.load(open(ROOT / 'geo/registry/campuses_geo.json'))
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
            'map.layer.modules', 'figures.modules', 'figures.lessons', 'room.finish',
            'figures.halls', 'figures.districts', 'figures.campuses',
            'view.campus', 'view.region', 'ui.walk',
            'hint.campus', 'hint.walk', 'geo.note',
            'honesty.taxonomy', 'honesty.content')},
        'districts': {k: v['name'] for k, v in c['districts'].items()},
        'strands': c['strands'], 'tiers': c['tiers'], 'states': c['states'],
    }

DATA = json.dumps({
    'districts': {k: {'name': d['name'], 'halls': d['halls'], 'hue': HUES[k]}
                  for k, d in districts_reg.items()},
    'campuses': campuses_reg,
    'geo': {'campuses': {k: {'lat': v['lat'], 'lng': v['lng']}
                         for k, v in geo_reg['campuses'].items()},
            'routes': geo_reg['routes_km']},
    'finishes': {sl: h['rooms'] for sl, h in finishes_reg['halls'].items()},
    'finCat': finishes_reg['catalogue'],
    'baseCond': finishes_reg['base_conditions'],
    'condOver': {sl: {st: c for st, c in h['conditions'].items()
                      if c['hazards']}
                 for sl, h in finishes_reg['halls'].items()
                 if any(c['hazards'] for c in h['conditions'].values())},
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
  <button id="regionBtn" class="barbtn"></button>
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
let view = 'region';
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
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.12;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
// dusk sky: a vertical gradient the fog can sink into
{
  const c = document.createElement('canvas'); c.width = 2; c.height = 256;
  const g = c.getContext('2d');
  const gr = g.createLinearGradient(0, 0, 0, 256);
  gr.addColorStop(0, '#0c141c'); gr.addColorStop(.55, '#1a2a36');
  gr.addColorStop(.8, '#33404a'); gr.addColorStop(1, '#463a2a');
  g.fillStyle = gr; g.fillRect(0, 0, 2, 256);
  scene.background = new THREE.CanvasTexture(c);
}
scene.fog = new THREE.Fog(0x1a2229, 70, 170);

function noiseTex(base, grain, n = 1400, size = 256) {
  const c = document.createElement('canvas'); c.width = c.height = size;
  const g = c.getContext('2d');
  g.fillStyle = base; g.fillRect(0, 0, size, size);
  for (let i = 0; i < n; i++) {
    g.fillStyle = `rgba(${grain},${.05 + Math.random() * .1})`;
    const r = Math.random() * 2.2;
    g.fillRect(Math.random() * size, Math.random() * size, r, r);
  }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.anisotropy = 4;
  return t;
}
const asphaltTex = noiseTex('#191f22', '220,225,225');
asphaltTex.repeat.set(34, 34);
const concreteTex = noiseTex('#262e31', '235,238,238', 1000);
concreteTex.repeat.set(9, 9);

const camera = new THREE.PerspectiveCamera(50, innerWidth/innerHeight, .1, 900);
camera.position.set(30, 26, 42);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI * .49;
controls.minDistance = 8; controls.maxDistance = 120;
controls.autoRotate = !reduced;
controls.autoRotateSpeed = .45;
controls.addEventListener('start', () => { controls.autoRotate = false; });

scene.add(new THREE.HemisphereLight(0xaec2cb, 0x241d16, 1.05));
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
  new THREE.MeshStandardMaterial({ map: asphaltTex, color: 0x8f9698, roughness: .96 }));
ground.rotation.x = -Math.PI/2; ground.receiveShadow = true;
scene.add(ground);
const grid = new THREE.GridHelper(520, 130, 0x28353A, 0x1b2427);
grid.position.y = .02; scene.add(grid);

const mat = {
  slab:  new THREE.MeshStandardMaterial({ map: concreteTex, color: 0xb8bdbd, roughness: .9 }),
  win:   new THREE.MeshStandardMaterial({ color: 0x0b0f11,
           emissive: 0xffc27a, emissiveIntensity: .5, roughness: .4 }),
  water: new THREE.MeshStandardMaterial({ color: 0x14283a, roughness: .3,
           metalness: .3 }),
  land:  new THREE.MeshStandardMaterial({ map: asphaltTex, color: 0xcdd2d3,
           roughness: .95 }),
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

const finTexCache = new Map();
function finishTex(fin) {
  const key = fin.pattern + fin.color;
  if (finTexCache.has(key)) return finTexCache.get(key);
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const g = c.getContext('2d');
  g.fillStyle = fin.color; g.fillRect(0, 0, 128, 128);
  for (let i = 0; i < 260; i++) { g.fillStyle = `rgba(255,255,255,${Math.random()*.05})`;
    g.fillRect(Math.random()*128, Math.random()*128, 1.6, 1.6); }
  for (let i = 0; i < 260; i++) { g.fillStyle = `rgba(0,0,0,${Math.random()*.07})`;
    g.fillRect(Math.random()*128, Math.random()*128, 1.6, 1.6); }
  g.strokeStyle = 'rgba(0,0,0,.28)'; g.lineWidth = 2;
  const line = (x1,y1,x2,y2) => { g.beginPath(); g.moveTo(x1,y1); g.lineTo(x2,y2); g.stroke(); };
  switch (fin.pattern) {
    case 'slab': g.strokeRect(1, 1, 126, 126); break;
    case 'tile': for (let i = 0; i <= 128; i += 32) { line(i,0,i,128); line(0,i,128,i); } break;
    case 'brick': for (let y = 0; y < 128; y += 16) { line(0,y,128,y);
      for (let x = ((y/16)%2)*16; x < 128; x += 32) line(x,y,x,y+16); } break;
    case 'plank': for (let x = 0; x <= 128; x += 16) line(x,0,x,128); break;
    case 'block': for (let i = 0; i <= 128; i += 10) { line(i,0,i,128); line(0,i,128,i); } break;
    case 'checker': g.fillStyle = 'rgba(255,255,255,.16)';
      for (let y = 8; y < 128; y += 16) for (let x = 8; x < 128; x += 16) {
        g.save(); g.translate(x,y); g.rotate(.785); g.fillRect(-4,-1.4,8,2.8); g.restore(); }
      break;
    case 'grate': g.fillStyle = 'rgba(0,0,0,.5)';
      for (let y = 2; y < 128; y += 10) g.fillRect(0,y,128,4); break;
    case 'broom': for (let x = 0; x < 128; x += 3) {
      g.strokeStyle = `rgba(0,0,0,${.04+Math.random()*.06})`; g.lineWidth = 1;
      line(x,0,x,128); } break;
    default: for (let i = 0; i < 700; i++) {
      g.fillStyle = `rgba(${Math.random()>.5?'255,255,255':'0,0,0'},${.06+Math.random()*.1})`;
      g.fillRect(Math.random()*128, Math.random()*128, 2, 2); }
  }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 4;
  finTexCache.set(key, t); return t;
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
let hallGroup = null, beacons = [], floors = [], roomRects = [], curRoom = null;

function buildHall(sg) {
  if (hallGroup) { scene.remove(hallGroup); hallGroup.traverse(o => {
    o.geometry?.dispose(); }); }
  hallGroup = new THREE.Group(); beacons = []; floors = []; roomRects = []; curRoom = null;
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

  // roof trusses across the span, and lit strips along the side walls
  for (let tz = 4; tz < DEP - 1; tz += 6) {
    box(W - .6, .18, .5, mat.metal, 0, 3.05, cz(tz), hallGroup, false);
    const lamp = new THREE.Mesh(new THREE.BoxGeometry(1.6, .1, .5), mat.win);
    lamp.position.set(0, 2.9, cz(tz)); hallGroup.add(lamp);
  }
  for (const wx of [cx(0) + .18, cx(W) - .18]) {
    const strip = new THREE.Mesh(new THREE.BoxGeometry(.06, .55, DEP * .8), mat.win);
    strip.position.set(wx, 2.55, 0); hallGroup.add(strip);
  }

  // rooms: tinted floor + low partitions + label
  const stns = h.stations.map(id => D.stations[id]);
  for (const r of h.rooms) {
    const rw = r.w * U, rd = r.h * U;
    const rx = cx(r.x * U + rw/2), rz = cz(r.y * U + rd/2);
    const fin = D.finCat[D.finishes[h.slug][r.strand].surface];
    const ftex = finishTex(fin).clone(); ftex.needsUpdate = true;
    ftex.repeat.set(Math.max(1, (rw - .3) / fin.tile_m),
                    Math.max(1, (rd - .3) / fin.tile_m));
    const floor = new THREE.Mesh(new THREE.BoxGeometry(rw - .3, .06, rd - .3),
      new THREE.MeshStandardMaterial({ map: ftex,
        roughness: fin.roughness, metalness: fin.metalness }));
    floor.position.set(rx, .38, rz); floor.receiveShadow = true;
    floor.userData.room = r.label;
    hallGroup.add(floor); floors.push(floor);
    roomRects.push({ x0: r.x * U - W/2, x1: r.x * U - W/2 + rw,
                     z0: r.y * U - DEP/2, z1: r.y * U - DEP/2 + rd,
                     label: r.label, strand: r.strand });
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
let regionGroup = null, plates = [];
let campusKey = D.halls.some(h => h.slug === params.get('hall'))
  ? Object.keys(D.campuses).find(k =>
      D.campuses[k].halls.includes(params.get('hall')))
  : (D.campuses[params.get('campus')] ? params.get('campus') : 'treasure-island');

const campusOfHall = (sg) =>
  Object.keys(D.campuses).find(k => D.campuses[k].halls.includes(sg));

/* -------- higher-detail buildings, shared by campus and region views ---- */
function building(h, bx, bz, g, scale = 1) {
  const dep = Math.max(h.depth, 5) * scale, wid = 12 * scale;
  const hgt = (6 + (h.depth % 3) * .7) * scale;
  const hue = D.districts[h.district].hue;
  const bld = box(wid, hgt, dep, mat.wall, bx, hgt / 2, bz, g);
  bld.userData.slug = h.slug;
  const band = new THREE.Mesh(new THREE.BoxGeometry(wid + .4 * scale, .9 * scale, dep + .4 * scale),
    new THREE.MeshStandardMaterial({
      color: new THREE.Color().setHSL(hue / 360, .5, .45), roughness: .6 }));
  band.position.set(bx, hgt - .2 * scale, bz); g.add(band);
  // lit window strips front and back, and a door
  for (const zz of [bz - dep / 2 - .03, bz + dep / 2 + .03]) {
    const strip = new THREE.Mesh(
      new THREE.BoxGeometry(wid * .78, .7 * scale, .06), mat.win);
    strip.position.set(bx, hgt * .55, zz); g.add(strip);
  }
  box(1.6 * scale, 2.4 * scale, .1, mat.part, bx, 1.2 * scale, bz - dep / 2 - .06, g, false);
  // rooftop unit
  box(1.6 * scale, .8 * scale, 1.2 * scale, mat.metal,
      bx + wid * .22, hgt + .4 * scale, bz + dep * .15, g);
  if (h.stations.length) {
    const bcn = new THREE.Mesh(new THREE.OctahedronGeometry(.9 * scale), mat.post);
    bcn.position.set(bx, hgt + 2 * scale, bz);
    g.add(bcn); campusSpin.push(bcn);
  }
  return bld;
}

/* ------------------------------ campus dressing, keyed by campus slug --- */
function dressCampus(key, g, R) {
  if (key === 'treasure-island') {
    // the island: a bay ring beyond the ground's edge and a flag over the plaza
    const bay = new THREE.Mesh(new THREE.RingGeometry(258, 640, 64), mat.water);
    bay.rotation.x = -Math.PI / 2; bay.position.y = -.08; g.add(bay);
    box(.14, 15, .14, mat.metal, 0, 7.5, -30, g);
    const flag = new THREE.Mesh(new THREE.PlaneGeometry(4.6, 2.6),
      new THREE.MeshStandardMaterial({ color: 0xE8A33D, side: THREE.DoubleSide }));
    flag.position.set(2.4, 13.4, -30); g.add(flag);
  }
  if (key === 'oakland') {
    // container rows and a gantry crane on the estuary edge
    const cols = [0xB3462F, 0x3A5A78, 0x5B7A5A, 0x8a6a42, 0x41626b];
    for (let i = 0; i < 14; i++) {
      const cx = -46 + (i % 7) * 15, cz = R + 34 + Math.floor(i / 7) * 6;
      const stack = 1 + (i * 7) % 3;
      for (let sN = 0; sN < stack; sN++) {
        const c = box(12, 2.6, 2.5, new THREE.MeshStandardMaterial({
          color: cols[(i + sN) % cols.length], roughness: .8 }),
          cx, 1.3 + sN * 2.6, cz, g);
        c.castShadow = true;
      }
    }
    for (const lx of [-14, 14]) {
      box(1.2, 26, 1.2, mat.metal, lx, 13, R + 46, g);
      box(1.2, 26, 1.2, mat.metal, lx, 13, R + 52, g);
    }
    box(34, 1.6, 2, mat.post, 0, 26, R + 49, g);
    const quay = new THREE.Mesh(new THREE.PlaneGeometry(400, 160), mat.water);
    quay.rotation.x = -Math.PI / 2; quay.position.set(0, -.06, R + 140); g.add(quay);
  }
  if (key === 'new-orleans') {
    // the river: a broad channel, pilings, and a working barge
    const river = new THREE.Mesh(new THREE.PlaneGeometry(560, 130), mat.water);
    river.rotation.x = -Math.PI / 2; river.position.set(0, -.06, R + 105); g.add(river);
    box(440, 2.4, 5, mat.slab, 0, 1.2, R + 38, g);      // the levee
    for (let i = 0; i < 12; i++)
      box(.8, 3.6, .8, mat.wood, -110 + i * 20, 1.2, R + 50, g);
    box(30, 2, 10, mat.part, 26, .9, R + 78, g);        // barge hull
    box(6, 3, 4, mat.metal, 36, 3.4, R + 78, g);        // wheelhouse
  }
}

function buildCampus(key) {
  if (campusGroup) scene.remove(campusGroup);
  campusGroup = new THREE.Group(); buildings = []; campusSpin = [];
  const camp = D.campuses[key];
  const dk = camp.districts;
  const R = dk.length === 2 ? 62 : 84;
  campusR = R;
  dk.forEach((k, di) => {
    const d = D.districts[k];
    const ang = di / dk.length * Math.PI * 2 - Math.PI / 2;
    const rad = new THREE.Vector2(Math.cos(ang), Math.sin(ang));
    const lat = new THREE.Vector2(-rad.y, rad.x);
    const cx = rad.x * R, cz = rad.y * R;
    const cols = Math.ceil(Math.sqrt(d.halls.length * 1.7));
    d.halls.forEach((sg, i) => {
      const h = D.halls.find(x => x.slug === sg);
      const gx = (i % cols) - (cols - 1) / 2, gz = Math.floor(i / cols);
      const bx = cx + lat.x * gx * 16 + rad.x * gz * 15;
      const bz = cz + lat.y * gx * 16 + rad.y * gz * 15;
      buildings.push(building(h, bx, bz, campusGroup));
    });
    const dl = label(D.i18n[loc].districts[k], null, 3);
    dl.position.set(cx - rad.x * 14, 15, cz - rad.y * 14);
    campusGroup.add(dl);
  });
  const plaza = new THREE.Mesh(new THREE.CylinderGeometry(24, 24, .3, 48),
    new THREE.MeshStandardMaterial({ map: concreteTex, color: 0xb8bdbd, roughness: .95 }));
  plaza.position.y = .15; plaza.receiveShadow = true; campusGroup.add(plaza);
  const sign = label(camp.name, camp.city + ', ' + camp.region, 3.2);
  sign.position.set(0, 18, 0); campusGroup.add(sign);
  dressCampus(key, campusGroup, R + 42);
  scene.add(campusGroup);
}

/* ---------------------------------------------------------- region view --- */
// Plate positions from the geo registry: TRUE bearings between the real
// coordinates; distances log-compressed so 9 km of bay and 3,000 km of
// gulf share one board. The route labels carry the real kilometres.
const PLATE_POS = (() => {
  const range = (km) => 34 + 50 * Math.log10(1 + km);
  const pos = { 'treasure-island': [0, 0] };
  for (const r of D.geo.routes) {
    if (r.from !== 'treasure-island') continue;
    const b = r.bearing_deg * Math.PI / 180, d = range(r.km);
    pos[r.to] = [Math.sin(b) * d, -Math.cos(b) * d];
  }
  const ks = Object.keys(pos);
  const cx = ks.reduce((a, k) => a + pos[k][0], 0) / ks.length;
  const cz = ks.reduce((a, k) => a + pos[k][1], 0) / ks.length;
  for (const k of ks) { pos[k][0] -= cx; pos[k][1] -= cz; }
  return pos;
})();

function buildRegion() {
  if (regionGroup) scene.remove(regionGroup);
  regionGroup = new THREE.Group(); plates = [];
  // the gulf-to-bay board: water underneath everything
  const sea = new THREE.Mesh(new THREE.PlaneGeometry(1600, 1600), mat.water);
  sea.rotation.x = -Math.PI / 2; sea.position.y = -.12; sea.receiveShadow = true;
  regionGroup.add(sea);
  const centers = {};
  for (const [key, camp] of Object.entries(D.campuses)) {
    const [px, pz] = PLATE_POS[key];
    centers[key] = new THREE.Vector3(px, 0, pz);
    const plate = new THREE.Mesh(new THREE.CylinderGeometry(36, 40, 2.2, 48), mat.land);
    plate.position.set(px, 1.1, pz); plate.receiveShadow = plate.castShadow = true;
    plate.userData.campus = key;
    regionGroup.add(plate); plates.push(plate);
    // one block per hosted district, sized by its hall count
    camp.districts.forEach((dkey, i) => {
      const d = D.districts[dkey];
      const ang = i / camp.districts.length * Math.PI * 2;
      const bx = px + Math.cos(ang) * 19, bz = pz + Math.sin(ang) * 19;
      const hgt = 4 + d.halls.length * .55;
      const blk = box(11, hgt, 11, new THREE.MeshStandardMaterial({
        color: new THREE.Color().setHSL(d.hue / 360, .45, .4), roughness: .7 }),
        bx, 2.2 + hgt / 2, bz, regionGroup);
      blk.userData.campus = key; plates.push(blk);
      const cl = label(String(d.halls.length), null, 1.4);
      cl.position.set(bx, hgt + 6, bz); regionGroup.add(cl);
    });
    const pl = label(camp.name, camp.city + ', ' + camp.region, 3.4);
    pl.position.set(px, 30, pz); regionGroup.add(pl);
  }
  // glowing routes between the campuses
  const lineMat = new THREE.LineBasicMaterial({ color: 0xE8A33D, transparent: true, opacity: .65 });
  const pairs = [['treasure-island', 'oakland'], ['oakland', 'new-orleans'],
                 ['treasure-island', 'new-orleans']];
  for (const [a, b] of pairs) {
    const pa = centers[a], pb = centers[b];
    const mid = pa.clone().add(pb).multiplyScalar(.5); mid.y = 26;
    const curve = new THREE.QuadraticBezierCurve3(
      pa.clone().setY(3), mid, pb.clone().setY(3));
    const geo = new THREE.BufferGeometry().setFromPoints(curve.getPoints(40));
    regionGroup.add(new THREE.Line(geo, lineMat));
    const km = D.geo.routes.find((r) =>
      (r.from === a && r.to === b) || (r.from === b && r.to === a))?.km;
    if (km !== undefined) {
      const kl = label(`${km.toLocaleString('en-US')} km`, null, 2.2);
      kl.position.copy(mid).setY(mid.y + 5);
      regionGroup.add(kl);
    }
  }
  const sign = label('SmartCiti.X : Trade Craft Academy', 'powered by AGI Corp', 3.6);
  sign.position.set(0, 44, 10); regionGroup.add(sign);
  scene.add(regionGroup);
}

function showRegion() {
  view = 'region';
  if (walkActive) plc.unlock();
  if (hallGroup) hallGroup.visible = false;
  if (campusGroup) campusGroup.visible = false;
  ground.visible = grid.visible = false;
  buildRegion();
  scene.fog.near = 380; scene.fog.far = 1300;
  controls.maxDistance = 700; controls.minDistance = 60;
  camera.position.set(0, 225, 235); controls.target.set(10, 0, 0);
  document.getElementById('hname').textContent = t('view.region');
  document.getElementById('hfocus').textContent =
    t('figures.campuses').replace('{n}', Object.keys(D.campuses).length) + ' · ' +
    t('figures.halls').replace('{n}', D.halls.length) + ' · ' +
    t('figures.districts').replace('{n}', Object.keys(D.districts).length);
  document.getElementById('hint').textContent =
    t('hint.campus') + ' \u00b7 ' + t('geo.note');
  document.getElementById('walkBtn').style.display = 'none';
  document.getElementById('campusBtn').style.display = 'none';
  syncURL();
}

function showCampus(key) {
  campusKey = key; view = 'campus';
  if (walkActive) plc.unlock();
  if (hallGroup) hallGroup.visible = false;
  if (regionGroup) regionGroup.visible = false;
  ground.visible = grid.visible = true;
  buildCampus(key);
  scene.fog.near = 160; scene.fog.far = 640;
  controls.maxDistance = 420; controls.minDistance = 20;
  camera.position.set(0, 165, 195); controls.target.set(0, 0, 0);
  const camp = D.campuses[key];
  document.getElementById('hname').textContent = camp.name;
  document.getElementById('hfocus').textContent =
    camp.city + ', ' + camp.region + ' — ' + camp.tagline;
  document.getElementById('hint').textContent = t('hint.campus');
  document.getElementById('walkBtn').style.display =
    ('ontouchstart' in window) ? 'none' : '';
  document.getElementById('campusBtn').style.display = 'none';
  syncURL();
}

function showHall(sg) {
  slug = sg; view = 'hall'; campusKey = campusOfHall(sg);
  if (regionGroup) regionGroup.visible = false;
  if (campusGroup) campusGroup.visible = false;
  ground.visible = grid.visible = true;
  buildHall(sg);
  scene.fog.near = 70; scene.fog.far = 170;
  controls.maxDistance = 120; controls.minDistance = 8;
  camera.position.set(30, 26, 42); controls.target.set(0, 2, 0);
  document.getElementById('hint').textContent =
    '\u25cf ' + t('hall.stations') + ' \u00b7 ' + t('hall.rooms') + ' \u2192 ' + t('map.layer.modules');
  document.getElementById('walkBtn').style.display =
    ('ontouchstart' in window) ? 'none' : '';
  const cb = document.getElementById('campusBtn');
  cb.style.display = ''; cb.textContent = '\u2191 ' + D.campuses[campusKey].name;
  syncURL();
}

/* ----------------------------------------------------------- walk mode --- */
const plc = new PointerLockControls(camera, renderer.domElement);
let walkActive = false;
const keys = {};
document.addEventListener('keydown', (e) => {
  keys[e.code] = true;
  if (walkActive && view === 'campus' && nearSlug
      && (e.code === 'Enter' || e.code === 'KeyE')) enterHallWalking(nearSlug);
});
document.addEventListener('keyup', (e) => { keys[e.code] = false; });

let campusR = 84, nearSlug = null;
function enterWalk() {
  if (view === 'region') return;
  controls.autoRotate = false; controls.enabled = false;
  if (view === 'hall') {
    const h = D.halls.find(x => x.slug === slug);
    camera.position.set(0, 1.7, -(h.depth * U) / 2 - 8);
  } else {
    camera.position.set(0, 1.7, 30);
  }
  camera.lookAt(0, 1.7, 0);
  plc.lock();
}

function enterHallWalking(sg) {
  showHall(sg);
  const h = D.halls.find(x => x.slug === sg);
  camera.position.set(0, 1.7, -(h.depth * U) / 2 - 8);
  document.getElementById('hint').textContent = t('hint.walk');
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
  else if (view === 'campus') document.getElementById('hint').textContent = t('hint.campus');
  nearSlug = null;
});

function walkStep(dt) {
  const sp = (keys.ShiftLeft || keys.ShiftRight ? 10 : 5) * dt;
  if (keys.KeyW || keys.ArrowUp) plc.moveForward(sp);
  if (keys.KeyS || keys.ArrowDown) plc.moveForward(-sp);
  if (keys.KeyA || keys.ArrowLeft) plc.moveRight(-sp);
  if (keys.KeyD || keys.ArrowRight) plc.moveRight(sp);
  camera.position.y = 1.7;
  if (view === 'hall') {
    const h = D.halls.find(x => x.slug === slug);
    const DEP = h.depth * U;
    camera.position.x = Math.min(21, Math.max(-21, camera.position.x));
    camera.position.z = Math.min(DEP/2 - .8, Math.max(-DEP/2 - 26, camera.position.z));
    const px = camera.position.x, pz = camera.position.z;
    const room = roomRects.find((r) =>
      px >= r.x0 && px <= r.x1 && pz >= r.z0 && pz <= r.z1) ?? null;
    if (room !== curRoom) {
      curRoom = room;
      if (room) {
        const fin = D.finCat[D.finishes[slug][room.strand].surface];
        document.getElementById('hfocus').textContent =
          room.label + ' \u2014 ' + fin.name;
        document.getElementById('hint').textContent =
          condLine(condOf(slug, room.strand));
      } else {
        document.getElementById('hfocus').textContent =
          D.halls.find(x => x.slug === slug).focus;
        document.getElementById('hint').textContent = t('hint.walk');
      }
    }
    return;
  }
  // campus stroll: stay on the grounds, and offer the nearest door
  const len = Math.hypot(camera.position.x, camera.position.z);
  const lim = campusR + 85;
  if (len > lim) {
    camera.position.x *= lim / len; camera.position.z *= lim / len;
  }
  let best = null, bd = 1e9;
  for (const b of buildings) {
    const d = Math.hypot(b.position.x - camera.position.x,
                         b.position.z - camera.position.z);
    if (d < bd) { bd = d; best = b; }
  }
  if (best && bd < 11) {
    nearSlug = best.userData.slug;
    const h = D.halls.find(x => x.slug === nearSlug);
    document.getElementById('hint').textContent = '\u23ce ' + h.name;
  } else if (nearSlug) {
    nearSlug = null;
    document.getElementById('hint').textContent = t('hint.walk');
  }
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
  document.getElementById('regionBtn').textContent = '⌂ ' + t('view.region');
  document.getElementById('walkBtn').textContent = '⤞ ' + t('ui.walk');
  document.getElementById('honesty').textContent =
    t('honesty.taxonomy') + ' ' + t('honesty.content');
  document.getElementById('pclose').textContent = t('ui.close');
}

const doneStations = new Set();
let curStation = null;
function scoreChip() {
  const h = D.halls.find(x => x.slug === slug);
  if (view !== 'hall' || !h.stations.length) return '';
  const d = h.stations.filter((id) => doneStations.has(id)).length;
  return ` \u2713 ${d}/${h.stations.length}`;
}
function openStation(id) {
  curStation = id;
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

function condOf(hallSlug, strand) {
  return D.condOver[hallSlug]?.[strand] ?? D.baseCond[strand];
}
function condLine(c) {
  return `${c.lux} lx \u00b7 ${c.ach} ACH \u00b7 ${c.noise_db} dB \u00b7 `
    + `${c.temp_c[0]}\u2013${c.temp_c[1]} \u00b0C \u00b7 PPE: `
    + (c.ppe.length ? c.ppe.join(', ') : '\u2014');
}

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
    ${(() => { const pf = D.finishes[h.slug][r.strand];
      const fin = D.finCat[pf.surface];
      return `<h3>${t('room.finish')}</h3>
        <p><b>${fin.name}</b>` +
        (pf.placed_by === 'hazard'
          ? ` <span class="chip">${pf.hazard}</span>` : '') +
        `<br><span style="color:var(--muted)">${fin.why}.</span></p>` +
        (() => { const c = condOf(h.slug, r.strand);
          return `<p style="color:var(--muted);font-size:13px">${condLine(c)}` +
            (c.hazards?.length
              ? '<br>' + c.hazards.map(z=>`<span class="chip">${z}</span>`).join(' ')
              : '') + `</p>
            <p style="font-size:11px;color:var(--muted);opacity:.8">geometry: SCHEMATIC \u00b7 finish: DERIVED \u00b7 conditions: DERIVED</p>`; })(); })()}
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
  if (view === 'region') {
    const phit = ray.intersectObjects(plates, false)[0];
    if (phit?.object.userData.campus) showCampus(phit.object.userData.campus);
    return;
  }
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
  if (view === 'hall' || hoverPending) return;
  hoverPending = true;
  requestAnimationFrame(() => {
    hoverPending = false;
    ptr.set(e.clientX/innerWidth*2-1, -(e.clientY/innerHeight)*2+1);
    ray.setFromCamera(ptr, camera);
    if (view === 'campus') {
      const bhit = ray.intersectObjects(buildings, false)[0];
      if (bhit?.object.userData.slug) {
        const h = D.halls.find(x => x.slug === bhit.object.userData.slug);
        document.getElementById('hname').textContent = h.name;
        document.getElementById('hfocus').textContent = h.focus;
        renderer.domElement.style.cursor = 'pointer';
      } else renderer.domElement.style.cursor = '';
    } else {
      const phit = ray.intersectObjects(plates, false)[0];
      if (phit?.object.userData.campus) {
        const c = D.campuses[phit.object.userData.campus];
        document.getElementById('hname').textContent = c.name;
        document.getElementById('hfocus').textContent =
          c.city + ', ' + c.region + ' — ' + c.tagline;
        renderer.domElement.style.cursor = 'pointer';
      } else renderer.domElement.style.cursor = '';
    }
  });
});
document.addEventListener('click', (e) => {
  if (e.target.closest('#pclose') || e.target.id === 'ov')
    document.body.classList.remove('open');
  const opt = e.target.closest('.opt');
  if (opt) { opt.parentElement.querySelectorAll('.opt').forEach(o =>
      o.classList.toggle('ok', o.dataset.ok === '1'));
    if (opt.dataset.ok !== '1') opt.classList.add('bad');
    else if (curStation) { doneStations.add(curStation);
      const el = document.getElementById('hname');
      const h = D.halls.find(x => x.slug === slug);
      if (view === 'hall') el.textContent = h.name + scoreChip(); } }
});
document.getElementById('hall').addEventListener('change', (e) => {
  showHall(e.target.value);
});
document.getElementById('regionBtn').addEventListener('click', showRegion);
document.getElementById('campusBtn').addEventListener('click',
  () => showCampus(campusKey));
document.getElementById('walkBtn').addEventListener('click', enterWalk);
document.getElementById('lang').addEventListener('change', (e) => {
  loc = e.target.value; renderChrome();
  if (view === 'region') showRegion();
  else if (view === 'campus') showCampus(campusKey);
  else showHall(slug);
});
function syncURL() {
  history.replaceState(null, '', view === 'region' ? `?lang=${loc}`
    : view === 'campus' ? `?campus=${campusKey}&lang=${loc}`
    : `?hall=${slug}&lang=${loc}`);
}
addEventListener('resize', () => {
  camera.aspect = innerWidth/innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

renderChrome();
if (D.halls.some(h => h.slug === params.get('hall'))) showHall(params.get('hall'));
else if (D.campuses[params.get('campus')]) showCampus(params.get('campus'));
else showRegion();
// test hook: lets the harness assert scene state without poking internals
window.__tc3d = () => ({ view, buildings: buildings.length, plates: plates.length,
  beacons: beacons.length, floors: floors.length, slug, campusKey, loc, walkActive });
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
