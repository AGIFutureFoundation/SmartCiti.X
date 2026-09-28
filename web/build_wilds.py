#!/usr/bin/env python3
"""The wilds page: large exterior worlds to walk, one page, a world switcher.

Rendered from wilds/registry/wilds.json and nothing else. The registry is
embedded verbatim; the ground is generated in the browser by the terrain
core in wilds/core.mjs, carried here byte-for-byte between its markers, so
the page and wilds/test.mjs walk on the same seeded ground.

How it stays cheap (the same doctrine web/build_3d.py keeps for the campus):
  - terrain streams in CHUNK_M chunks around the eye, one mesh per chunk,
    finer near and coarser far (LOD rings), with skirts so rings never crack;
  - every tree, bush and rock of a species is ONE InstancedMesh, refilled
    around the eye as it moves: a species costs one draw call, not thousands;
  - the site props, the caches and the trail network are each merged into
    one geometry: one draw call apiece;
  - the overview swaps the chunks for one low-resolution mesh of the whole
    world, so seeing all of it costs one draw call too.

Everything drawn is AUTHORED: an invented landscape from a seed, not a
survey. Caches and side quests are play and never enter a completion record.
"""
import html
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402
import sitenav  # noqa: E402
from sitenav import nav_html, labels as nav_labels, NAV_CSS  # noqa: E402
from seo import apply_seo  # noqa: E402  head tags only
# the enterprise theme (MEDIA, web/pagehero.py): a full-screen canvas page takes
# the panel/button/badge/focus layer only - no hero band over the world
from pagehero import theme  # noqa: E402
THEME_CSS, THEME_JS = theme('canvas')
if THEME_JS:
    raise SystemExit('build_wilds: the canvas theme is CSS only; pagehero.theme("canvas") returned script')

PAGE = 'web/trade_craft_wilds.html'
REG = json.loads((ROOT / 'wilds/registry/wilds.json').read_text())
CORE_SRC = (ROOT / 'wilds/core.mjs').read_text()
B, E = '/* WILDS_CORE:BEGIN */', '/* WILDS_CORE:END */'
if CORE_SRC.count(B) != 1 or CORE_SRC.count(E) != 1:
    raise SystemExit('build_wilds: wilds/core.mjs must hold exactly one WILDS_CORE block')
CORE = CORE_SRC[CORE_SRC.index(B):CORE_SRC.index(E) + len(E)]
LESSONS_HREF = 'trade_craft_lessons.html#lesson-'
# Page chrome comes from the catalog (wilds.* keys, all 8 locales); strict like
# sitenav.labels(): a missing or empty key stops the build.
_CAT = json.loads((ROOT / 'i18n/locales/en.json').read_text(encoding='utf-8'))['strings']


def T(k):
    if k not in _CAT or not isinstance(_CAT[k], str) or not _CAT[k].strip():
        raise SystemExit(f'build_wilds: i18n/locales/en.json has no wilds chrome key {k!r}')
    return html.escape(_CAT[k], quote=True)


def TRAW(k):
    T(k)
    return _CAT[k]


# every chrome key the page uses is recorded, and the runtime catalogue below
# carries exactly those keys for all 8 locales; a key missing from any locale
# stops the build (no silent English fallback at run time)
_USED = set()


def TS(k):
    """chrome text the runtime re-renders in the reader's locale"""
    _USED.add(k)
    return f'<span data-i18n="{k}">{T(k)}</span>'


def TA(k):
    """chrome text in an attribute (aria-label): marked data-i18n-aria"""
    _USED.add(k)
    return T(k)

HALL_HREF = 'trade_craft_3d.html?hall='


def esc(s):
    return html.escape(str(s), quote=True)


# ------------------------------------------------------------------ nav --
# the site nav, declared once in web/sitenav.py (this page sits in its Play
# group); a page built without it would be a page a learner cannot leave, so
# there is no fallback: a missing declaration stops the build
if PAGE not in sitenav.PAGES:
    raise SystemExit('build_wilds: web/sitenav.py does not declare ' + PAGE)
NAV = nav_html('web/trade_craft_wilds.html', nav_labels('en'))

# --------------------------------------------------------------- quests --
# INTEGRATION POINT (quests): the quest contract's hooks. Every quest whose
# world is "wilds:<world id>" gets a hook here, and its `place` must be one
# of that world's site or cache ids - the build stops naming it otherwise.
# Until the quest registry holds any wilds entries, no hook is emitted and
# the page says the quest log is not wired yet.
QUEST_ROWS = []
QUEST_SCRIPT = ''
QUEST_CSS_BLOCK = ''
QUEST_STATE = 'pending'
qreg_path = ROOT / 'quests/registry/quests.json'
if qreg_path.exists() and (HERE / 'questkit.py').exists():
    qreg = json.loads(qreg_path.read_text())
    wq = [q for q in qreg['quests'] if q['world'].startswith('wilds:')]
    if wq:
        from questkit import QUEST_CSS, quest_js, egg_attr, quest_attr  # noqa: E402
        # a quest's place is a site, a cache, or the world's trailhead
        places = {w['id']: {s['id'] for s in w['sites']} | {c['id'] for c in w['caches']} | {'trailhead'}
                  for w in REG['worlds']}
        for q in wq:
            wid = q['world'].split(':', 1)[1]
            if wid not in places:
                raise SystemExit(f'build_wilds: quest {q["id"]} names world {wid!r}, not in wilds/registry')
            if 'place' not in q:
                raise SystemExit(f'build_wilds: quest {q["id"]} has no place in world {wid}')
            if q['place'] not in places[wid]:
                raise SystemExit(f'build_wilds: quest {q["id"]} place {q["place"]!r} is not a site, cache or the trailhead of {wid}')
            attr = egg_attr(q['id']) if q['kind'] in ('treasure', 'egg') else quest_attr(q['id'])
            QUEST_ROWS.append(
                f'<li><button type="button" class="qhook tc-btn tc-btn-ghost" data-wilds-world="{esc(wid)}" '
                f'data-wilds-place="{esc(q["place"])}" data-wilds-kind="{esc(q["kind"])}" {attr}>'
                f'{esc(q["title"])}</button> <span class="hint">{esc(q["hint"])}</span></li>')
        QUEST_SCRIPT = quest_js('wilds')
        QUEST_CSS_BLOCK = f'<style>{QUEST_CSS}</style>'
        QUEST_STATE = 'wired'

# ---------------------------------------------------------------- tasks --
# INTEGRATION POINT (tasks): the simulated tasks TASKS registers at each wilds
# site (tasks/registry/tasks.json, place.kind "wilds-site"), read only through
# web/taskkit.py. Each site card and the in-world site panel list them with
# their launch link and the lessons linked to them; the minimap rings a site
# that has any. Until the task registry exists the page says so plainly.
TASK_STATE = 'pending'
TASKS_BY_SITE = {}
TASK_CSS_BLOCK = ''
TASK_HONESTY = ''
if (ROOT / 'tasks/registry/tasks.json').exists() and (HERE / 'taskkit.py').exists():
    import taskkit  # noqa: E402
    LESSON_TITLES = json.loads((ROOT / 'lessons/registry/lessons.json').read_text())['lessons']
    for w in REG['worlds']:
        for s in w['sites']:
            ts = taskkit.tasks_for('wilds-site', s['id'])
            for t in ts:
                if t['place']['world'] != w['id']:
                    raise SystemExit(f'build_wilds: task {t["id"]} names world {t["place"]["world"]!r} for site {s["id"]} of {w["id"]}')
                for lid in t['requires']:
                    if lid not in LESSON_TITLES:
                        raise SystemExit(f'build_wilds: task {t["id"]} requires lesson {lid!r}, not in lessons/registry')
            TASKS_BY_SITE[s['id']] = ts
    TASK_STATE = 'wired'
    TASK_CSS_BLOCK = f'<style>{taskkit.TASKS_CSS}</style>'
    TASK_HONESTY = taskkit.TASKS['honesty']['practice']


def task_href(t):
    return taskkit.rel_href(t['launch']['href'], 'web')


def site_tasks(s):
    if TASK_STATE != 'wired':
        return ''
    ts = TASKS_BY_SITE[s['id']]
    if not ts:
        return f'<p class="k">{TS("wilds.site.tasks")}</p><p class="none">{TS("wilds.site.no_task")}</p>'
    rows = []
    for t in ts:
        href = task_href(t)
        launch = (f'<a class="tlaunch tc-btn tc-btn-primary" href="{esc(href)}" data-task-launch="{esc(t["id"])}">{TS("wilds.task.launch")}</a>' if href
                  else f'<span class="none">{esc(t["launch"]["why"])}</span>')
        if t['requires']:
            req = ', '.join(f'<a href="{LESSONS_HREF}{esc(l)}">{esc(LESSON_TITLES[l]["title"])}</a>' for l in t['requires'])
            req = f'<span class="treq">{TS("wilds.task.requires")}: {req}</span>'
        else:
            req = f'<span class="treq">{TS("wilds.task.open")}</span>'
        rows.append(f'<li data-task="{esc(t["id"])}" data-kind="{esc(t["kind"])}"><b>{esc(t["title"])}</b> '
                    f'<span class="prov tc-badge tc-badge-muted">{esc(t["provenance"])}</span> {launch}<br>{req}</li>')
    # the halls working here: their tasks (seats, drills, walkarounds) launch on
    # the campus; listed through taskkit's own compact list
    ht = [t for h in s['halls'] for t in taskkit.tasks_for('hall', h['id'])]
    hall_block = (f'<p class="k">{TS("wilds.site.hall_tasks")}</p><div class="halltasks" data-hall-tasks="{esc(s["id"])}">'
                  f'{taskkit.task_list(ht, None, "web")}</div>' if ht else '')
    return f'<p class="k">{TS("wilds.site.tasks")}</p><ul class="tasks">{"".join(rows)}</ul>{hall_block}'


def world_task_fig(w):
    if TASK_STATE != 'wired':
        return ''
    n = sum(len(TASKS_BY_SITE[s['id']]) for s in w['sites'])
    return f'<div class="fig"><b data-fig-tasks="{esc(w["id"])}">{n}</b><span>{TS("wilds.fig.tasks")}</span></div>'


# --------------------------------------------------------------- cards --
def site_card(w, s):
    halls = ''.join(f'<li><a href="{HALL_HREF}{esc(h["id"])}">{esc(h["name"])}</a></li>' for h in s['halls'])
    if s['lessons']:
        lessons = ''.join(f'<li><a href="{LESSONS_HREF}{esc(l["id"])}">{esc(l["title"])}</a></li>'
                          for l in s['lessons'])
        lessons = f'<p class="k">{TS("wilds.site.lessons")}</p><ul class="links">{lessons}</ul>'
    else:
        lessons = f'<p class="k">{TS("wilds.site.lessons")}</p><p class="none">{TS("wilds.site.no_lesson")}</p>'
    return (f'<article class="site" id="site-{esc(s["id"])}" data-site="{esc(s["id"])}" data-world="{esc(w["id"])}">'
            f'<h3>{esc(s["title"])} <span class="prov tc-badge tc-badge-muted">SCHEMATIC</span></h3>'
            f'<p>{esc(s["work"])}</p>'
            f'<p class="k">{TS("wilds.site.halls")}</p><ul class="links">{halls}</ul>{lessons}{site_tasks(s)}'
            f'<button type="button" class="go tc-btn tc-btn-primary" data-goto="{esc(s["id"])}">{TS("wilds.site.go")}</button>'
            '</article>')


def world_section(w):
    sites = ''.join(site_card(w, s) for s in w['sites'])
    caches = ''.join(f'<li data-cache="{esc(c["id"])}"><b>{esc(c["kind"])}</b> {esc(c["riddle"])}</li>' for c in w['caches'])
    return (f'<section class="world" data-world-card="{esc(w["id"])}" hidden>'
            f'<h2>{esc(w["name"])}</h2>'
            f'<p class="evokes">Evokes {esc(w["inspiration"]["evokes"])} - nearest campus in spirit: '
            f'{esc(w["inspiration"]["campus_city"])}. <b>{esc(w["inspiration"]["standing"])}.</b></p>'
            f'<p class="geo" data-geolocation="{esc(w["id"])}"><span class="prov tc-badge tc-badge-muted">AUTHORED</span> {esc(w["geolocation"]["label"])}</p>'
            f'<div class="figs"><div class="fig"><b>{w["area_km2"]}</b><span>{TS("wilds.fig.area")}</span></div>'
            f'<div class="fig"><b>{len(w["sites"])}</b><span>{TS("wilds.fig.sites")}</span></div>'
            f'<div class="fig"><b>{w["trail_length_m"]}</b><span>{TS("wilds.fig.trail")}</span></div>'
            f'<div class="fig"><b>{len(w["caches"])}</b><span>{TS("wilds.fig.treasures")}</span></div>{world_task_fig(w)}</div>'
            f'<div class="sites">{sites}</div>'
            f'<h3>{TS("wilds.h.riddles")}</h3><ul class="riddles">{caches}</ul>'
            '</section>')


worlds_html = ''.join(world_section(w) for w in REG['worlds'])
switch = ''.join(f'<button type="button" class="tc-btn tc-btn-ghost" data-world="{esc(w["id"])}" aria-pressed="false">{esc(w["name"])}</button>'
                 for w in REG['worlds'])
embedded = json.dumps(REG, sort_keys=True).replace('</', '<\\/')
JS_LABELS = {k: TRAW('wilds.' + k) for k in ('mode.overview', 'mode.walk', 'pace', 'pace.walk', 'pace.run', 'pace.fast',
                                             'toast.cache', 'toast.trailhead', 'side_quest', 'flyover')}
_USED.update('wilds.' + k for k in JS_LABELS)
labels_json = json.dumps(JS_LABELS, ensure_ascii=False, sort_keys=True).replace('</', '<\\/')
site_task_counts = json.dumps({s['id']: len(TASKS_BY_SITE[s['id']]) for w in REG['worlds'] for s in w['sites']}
                              if TASK_STATE == 'wired' else {}, sort_keys=True)
c = REG['counts']
task_note = (f'<p class="help" data-tasks-honesty>{esc(TASK_HONESTY)}</p>' if TASK_STATE == 'wired'
             else '<p class="none" data-tasks-pending>Simulated tasks are not wired to this page yet: tasks/registry/tasks.json '
                  'is not built. INTEGRATION POINT for the task contract.</p>')
quest_block = (f'<ul class="quests">{"".join(QUEST_ROWS)}</ul><div data-tc-questlog></div>' if QUEST_STATE == 'wired'
               else '<p class="none" data-quests-pending>The quest log is not wired to this page yet: caches can be found, '
                    'but nothing is recorded. INTEGRATION POINT for the quest contract.</p>')

JS = r'''
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
''' + CORE + r'''
const REG = JSON.parse(document.getElementById('wilds-registry').textContent);
/* run-time locale, chosen the way the campus page does (?lang=<code> when the
   catalogue has it), then the reader's browser languages, then en. Every key
   the page uses is in every locale (the build fails otherwise), so a missing
   string here is a bug and throws by name: never a silent English fallback. */
const I18N = JSON.parse(document.getElementById('wilds-i18n').textContent);
function pickLocale() {
  const q = new URLSearchParams(location.search).get('lang');
  if (q && Object.hasOwn(I18N, q)) return q;
  const prefs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || 'en'];
  for (const n of prefs) { const c = String(n).slice(0, 2).toLowerCase(); if (Object.hasOwn(I18N, c)) return c; }
  return 'en';
}
const LOC = pickLocale();
function tr(k) {
  const s = I18N[LOC].strings[k];
  if (typeof s !== 'string') throw new Error(`wilds i18n: locale ${LOC} has no ${k}`);
  return s;
}
function renderChrome() {
  document.documentElement.lang = LOC;
  document.documentElement.dir = I18N[LOC].dir;
  for (const el of document.querySelectorAll('[data-i18n]')) el.textContent = tr(el.dataset.i18n);
  for (const el of document.querySelectorAll('[data-i18n-aria]')) el.setAttribute('aria-label', tr(el.dataset.i18nAria));
}
renderChrome();
const L_EN = JSON.parse(document.getElementById('wilds-labels').textContent);
const L = Object.fromEntries(Object.keys(L_EN).map((k) => [k, tr('wilds.' + k)]));
/* simulated tasks per site (tasks/registry via web/taskkit.py); {} until wired */
const SITE_TASKS = JSON.parse(document.getElementById('wilds-tasks').textContent);
const WORLDS = new Map(REG.worlds.map((w) => [w.id, w]));
/* Declared once. The eval (web/eval_wilds.mjs) holds these views to targets. */
const RING_SEGS = [40, 40, 20, 10];   // grid segments per chunk by ring distance from the eye
const RADIUS = 3;                      // chunk rings streamed around the eye
const VEG_R = 420, VEG_CELL = 9;       // vegetation radius and scatter cell, metres
const VEG_REFILL = 50;                 // refill vegetation after the eye moves this far
const CAP = { conifer: 5200, deciduous: 2600, rock: 1600 };
/* Tree billboards: past VEG_R, out to BB_R, each tree species is drawn as a
   crossed card (a conifer is two crossed triangles, a broadleaf two crossed
   diamonds) on a coarser BB_CELL scatter, ONE InstancedMesh per species. A
   card never stands inside VEG_R, where the full trees are. */
const BB_R = 900, BB_CELL = 18;
const BB_CAP = { conifer: 9000, deciduous: 4500 };
const SKIRT = 40, EYE_H = 1.7, WALK_MS = 1.7, RUN_MS = 5.0, FAST_MS = 24;
const BUILD_PER_FRAME = 2;

const stage = document.getElementById('stage');
const canvas = document.getElementById('view');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.25));
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(62, 1, 0.3, 9000);
const hemi = new THREE.HemisphereLight(0xdfeeff, 0x4a4032, 1.05);
const sun = new THREE.DirectionalLight(0xfff2dc, 1.6);
sun.position.set(-0.5, 0.8, 0.35);
scene.add(hemi, sun);
const orbit = new OrbitControls(camera, canvas);
orbit.enabled = false; orbit.maxPolarAngle = 1.45; orbit.enableDamping = false;

const matTerrain = new THREE.MeshLambertMaterial({ vertexColors: true });
const matVeg = new THREE.MeshLambertMaterial({ vertexColors: true });
const matProp = new THREE.MeshLambertMaterial({ vertexColors: true });
const matTrail = new THREE.MeshLambertMaterial({ color: 0xC9B48A, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
const matWater = new THREE.MeshLambertMaterial({ color: 0x3E6E8E, transparent: true, opacity: 0.86 });

let W = null, T = null, mode = 'walk';
const chunks = new Map();              // key -> { mesh, lod }
const worldGroup = new THREE.Group(); scene.add(worldGroup);
const eye = { x: 0, z: 0, yaw: 0, pitch: -0.05 };
let speedMode = 0;                     // 0 walk, 1 run, 2 fast
const col = new THREE.Color(), col2 = new THREE.Color();
let pal = null;

function hex(c) { return new THREE.Color(c); }
function groundColor(x, z, h, ny, out) {
  const b = W.biome;
  if (h < b.water_level_m + 2.5) return out.copy(pal.shore);
  const snowAt = b.snow_line_m + 60 * Math.sin(x / 170) * Math.cos(z / 230);
  if (h > snowAt && ny > 0.62) return out.copy(pal.snow);
  if (ny < 0.74) return out.copy(pal.rock).lerp(pal.mid, Math.max(0, (ny - 0.6) * 3));
  const t = Math.min(1, Math.max(0, (h - b.tree_line_m + 80) / 160));
  out.copy(pal.mid).lerp(pal.low, t);
  const k = 0.5 + 0.5 * Math.sin(x * 0.013 + Math.cos(z * 0.011) * 2);
  return out.lerp(pal.low, k * 0.35);
}

/* ------------------------------------------------------ terrain chunks -- */
function chunkGeometry(i, j, segs) {
  const size = W.chunk_m, step = size / segs, x0 = i * size, z0 = j * size;
  const n = segs + 1, G = segs + 3;              // one extra ring each side for normals
  const H = new Float32Array(G * G);
  for (let a = 0; a < G; a++) for (let c = 0; c < G; c++) H[a * G + c] = T.height(x0 + (c - 1) * step, z0 + (a - 1) * step);
  const nv = n * n + 4 * segs;                   // grid + skirt ring
  const pos = new Float32Array(nv * 3), nor = new Float32Array(nv * 3), clr = new Float32Array(nv * 3);
  const put = (v, x, y, z, nx, ny, nz) => {
    pos[v * 3] = x; pos[v * 3 + 1] = y; pos[v * 3 + 2] = z;
    nor[v * 3] = nx; nor[v * 3 + 1] = ny; nor[v * 3 + 2] = nz;
    groundColor(x, z, y, ny, col); clr[v * 3] = col.r; clr[v * 3 + 1] = col.g; clr[v * 3 + 2] = col.b;
  };
  for (let a = 0; a < n; a++) for (let c = 0; c < n; c++) {
    const h = H[(a + 1) * G + c + 1];
    const gx = (H[(a + 1) * G + c + 2] - H[(a + 1) * G + c]) / (2 * step);
    const gz = (H[(a + 2) * G + c + 1] - H[a * G + c + 1]) / (2 * step);
    const L = Math.hypot(gx, 1, gz);
    put(a * n + c, x0 + c * step, h, z0 + a * step, -gx / L, 1 / L, -gz / L);
  }
  const idx = [];
  for (let a = 0; a < segs; a++) for (let c = 0; c < segs; c++) {
    const p = a * n + c;
    idx.push(p, p + n, p + 1, p + 1, p + n, p + n + 1);
  }
  // skirt: the border walked once round, each vertex dropped SKIRT metres
  const ring = [];
  for (let c = 0; c < segs; c++) ring.push(c);
  for (let a = 0; a < segs; a++) ring.push(a * n + segs);
  for (let c = segs; c > 0; c--) ring.push(segs * n + c);
  for (let a = segs; a > 0; a--) ring.push(a * n);
  let v = n * n;
  const first = v;
  for (const r of ring) {
    put(v, pos[r * 3], pos[r * 3 + 1] - SKIRT, pos[r * 3 + 2], nor[r * 3], nor[r * 3 + 1], nor[r * 3 + 2]);
    v++;
  }
  for (let k = 0; k < ring.length; k++) {
    const a = ring[k], b2 = ring[(k + 1) % ring.length], sa = first + k, sb = first + (k + 1) % ring.length;
    idx.push(a, sa, b2, b2, sa, sb, a, b2, sa, b2, sb, sa);   // both faces: skirts are seen from either side
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
  g.setAttribute('color', new THREE.BufferAttribute(clr, 3));
  g.setIndex(idx);
  g.computeBoundingSphere();
  return g;
}
const nChunks = () => W.extent_m / W.chunk_m;
function wanted() {
  const ci = Math.floor(eye.x / W.chunk_m), cj = Math.floor(eye.z / W.chunk_m), lim = nChunks() / 2;
  const out = [];
  for (let i = ci - RADIUS; i <= ci + RADIUS; i++) for (let j = cj - RADIUS; j <= cj + RADIUS; j++) {
    if (i < -lim || j < -lim || i >= lim || j >= lim) continue;
    const r = Math.max(Math.abs(i - ci), Math.abs(j - cj));
    out.push({ key: i + ',' + j, i, j, lod: RING_SEGS[r], r });
  }
  out.sort((a, b) => a.r - b.r);
  return out;
}
let queue = [];
function updateChunks(all) {
  setHorizonBox();
  const want = wanted(), keep = new Set();
  queue = [];
  for (const w of want) {
    keep.add(w.key);
    const have = chunks.get(w.key);
    if (!have || have.lod !== w.lod) queue.push(w);
  }
  for (const [k, ch] of chunks) if (!keep.has(k)) { worldGroup.remove(ch.mesh); ch.mesh.geometry.dispose(); chunks.delete(k); }
  pump(all ? Infinity : BUILD_PER_FRAME);
}
function pump(budget) {
  while (queue.length && budget-- > 0) {
    const w = queue.shift();
    const g = chunkGeometry(w.i, w.j, w.lod);
    const old = chunks.get(w.key);
    if (old) { worldGroup.remove(old.mesh); old.mesh.geometry.dispose(); }
    const m = new THREE.Mesh(g, matTerrain); m.matrixAutoUpdate = false;
    worldGroup.add(m); chunks.set(w.key, { mesh: m, lod: w.lod });
  }
}

/* One low-resolution mesh of the whole world: the overview and the minimap's ground. */
let overviewMesh = null, horizonMesh = null;
/* The far horizon: a coarse whole-world mesh drawn in walk mode everywhere
   OUTSIDE the square of streamed chunks (the fragment shader discards inside
   it, so the fine chunks alone carry the near ground), sunk HORIZON_SINK_M
   so it can only ever sit under them at the seam. Walk-mode fog then reaches
   far enough that distant ridges read beyond the chunk radius. */
const HORIZON_SEGS = 64, HORIZON_SINK_M = 2;
const horizonBox = { value: new THREE.Vector4(0, 0, 0, 0) };
const matHorizon = new THREE.MeshLambertMaterial({ vertexColors: true });
matHorizon.onBeforeCompile = (sh) => {
  sh.uniforms.uBox = horizonBox;
  sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec2 vWxz;')
    .replace('#include <begin_vertex>', '#include <begin_vertex>\nvWxz = (modelMatrix * vec4(transformed, 1.0)).xz;');
  sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec2 vWxz;\nuniform vec4 uBox;')
    .replace('void main() {', 'void main() {\n  if (vWxz.x > uBox.x && vWxz.x < uBox.z && vWxz.y > uBox.y && vWxz.y < uBox.w) discard;');
};
function setHorizonBox() {
  const ci = Math.floor(eye.x / W.chunk_m), cj = Math.floor(eye.z / W.chunk_m), lim = nChunks() / 2;
  horizonBox.value.set(Math.max(ci - RADIUS, -lim) * W.chunk_m, Math.max(cj - RADIUS, -lim) * W.chunk_m,
    (Math.min(ci + RADIUS, lim - 1) + 1) * W.chunk_m, (Math.min(cj + RADIUS, lim - 1) + 1) * W.chunk_m);
}
function worldMesh(segs, mat, sink) {
  const size = W.extent_m, step = size / segs, n = segs + 1;
  const pos = new Float32Array(n * n * 3), clr = new Float32Array(n * n * 3);
  for (let a = 0; a < n; a++) for (let c = 0; c < n; c++) {
    const x = -size / 2 + c * step, z = -size / 2 + a * step, h = T.height(x, z), v = (a * n + c) * 3;
    pos[v] = x; pos[v + 1] = h; pos[v + 2] = z;
  }
  const idx = [];
  for (let a = 0; a < segs; a++) for (let c = 0; c < segs; c++) { const p = a * n + c; idx.push(p, p + n, p + 1, p + 1, p + n, p + n + 1); }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setIndex(idx); g.computeVertexNormals();
  const nor = g.getAttribute('normal');
  for (let k = 0; k < n * n; k++) { groundColor(pos[k * 3], pos[k * 3 + 2], pos[k * 3 + 1], nor.getY(k), col); clr[k * 3] = col.r; clr[k * 3 + 1] = col.g; clr[k * 3 + 2] = col.b; }
  g.setAttribute('color', new THREE.BufferAttribute(clr, 3));
  const m = new THREE.Mesh(g, mat); m.visible = false; m.position.y = -sink;
  worldGroup.add(m);
  return m;
}
function buildOverview() {
  overviewMesh = worldMesh(128, matTerrain, 0);
  horizonMesh = worldMesh(HORIZON_SEGS, matHorizon, HORIZON_SINK_M);
}

/* ------------------------------------------------------------ vegetation -- */
function painted(geo, hexc) {
  const g = geo.index ? geo.toNonIndexed() : geo;
  const c = new THREE.Color(hexc), n = g.getAttribute('position').count, a = new Float32Array(n * 3);
  for (let k = 0; k < n; k++) { a[k * 3] = c.r; a[k * 3 + 1] = c.g; a[k * 3 + 2] = c.b; }
  g.setAttribute('color', new THREE.BufferAttribute(a, 3));
  g.deleteAttribute('uv');
  return g;
}
function at(geo, x, y, z, ry = 0) { geo.rotateY(ry); geo.translate(x, y, z); return geo; }
const SPECIES = {
  conifer: mergeGeometries([
    painted(at(new THREE.CylinderGeometry(0.22, 0.34, 2.4, 5, 1, true), 0, 1.2, 0), 0x5A4030),
    painted(at(new THREE.ConeGeometry(2.4, 5.2, 7, 1, true), 0, 4.4, 0), 0x2E4D2C),
    painted(at(new THREE.ConeGeometry(1.7, 4.2, 7, 1, true), 0, 7.0, 0, 0.4), 0x365A33),
  ]),
  deciduous: mergeGeometries([
    painted(at(new THREE.CylinderGeometry(0.2, 0.3, 3.4, 5, 1, true), 0, 1.7, 0), 0x6B5238),
    painted(at(new THREE.IcosahedronGeometry(2.6, 0), 0, 5.0, 0), 0x6E8F3E),
  ]),
  rock: painted(new THREE.DodecahedronGeometry(1, 0), 0x8A857C),
};
const veg = {};
for (const [k, g] of Object.entries(SPECIES)) {
  const m = new THREE.InstancedMesh(g, matVeg, CAP[k]);
  m.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  m.count = 0; m.frustumCulled = false;
  scene.add(m); veg[k] = m;
}
/* the billboard cards: vertex-coloured, normals straight up so a card is lit
   like the canopy it stands for whichever way it faces */
function card(pts, hexc) {
  const g = new THREE.BufferGeometry(), n = pts.length / 3, c = new THREE.Color(hexc);
  g.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(new Array(n).fill([0, 1, 0]).flat(), 3));
  g.setAttribute('color', new THREE.Float32BufferAttribute(new Array(n).fill([c.r, c.g, c.b]).flat(), 3));
  return g;
}
const BB_SHAPES = {
  conifer: card([-2.4, 0, 0, 2.4, 0, 0, 0, 9.4, 0, 0, 0, -2.4, 0, 0, 2.4, 0, 9.4, 0], 0x2E4D2C),
  deciduous: card([0, 1.8, 0, 2.7, 5, 0, 0, 8, 0, 0, 1.8, 0, 0, 8, 0, -2.7, 5, 0,
    0, 1.8, 0, 0, 5, 2.7, 0, 8, 0, 0, 1.8, 0, 0, 8, 0, 0, 5, -2.7], 0x6E8F3E),
};
/* wave 4: BOTH species share ONE InstancedMesh (one draw call, was one per
   species). The merged geometry carries both cards, each vertex tagged with
   its species (bbPart); each instance carries the species it stands for
   (bbKind), and the vertex shader collapses the other card's vertices to a
   point, so it rasterises nothing. The eval counts both cards' triangles
   per instance; that growth is inside the declared triangle headroom. */
const BB_KINDS = Object.keys(BB_SHAPES);
const BB_TOTAL = BB_KINDS.reduce((a, k) => a + BB_CAP[k], 0);
const bbGeo = mergeGeometries(BB_KINDS.map((k, i) => {
  const g = BB_SHAPES[k].clone();
  g.setAttribute('bbPart', new THREE.Float32BufferAttribute(new Array(g.attributes.position.count).fill(i), 1));
  return g;
}));
const bbKind = new THREE.InstancedBufferAttribute(new Float32Array(BB_TOTAL), 1);
bbKind.setUsage(THREE.DynamicDrawUsage);
bbGeo.setAttribute('bbKind', bbKind);
const matBB = new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide });
matBB.onBeforeCompile = (sh) => {
  sh.vertexShader = sh.vertexShader
    .replace('#include <common>', '#include <common>\nattribute float bbPart;\nattribute float bbKind;')
    .replace('#include <begin_vertex>', '#include <begin_vertex>\ntransformed *= step(abs(bbPart - bbKind), 0.5);');
};
const bbMesh = new THREE.InstancedMesh(bbGeo, matBB, BB_TOTAL);
bbMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
bbMesh.count = 0; bbMesh.frustumCulled = false;
scene.add(bbMesh);
const bbCount = Object.fromEntries(BB_KINDS.map((k) => [k, 0]));
let bbMinR = Infinity;
function refillBillboards() {
  const cand = { conifer: [], deciduous: [] };
  const c0 = Math.floor((eye.x - BB_R) / BB_CELL), c1 = Math.floor((eye.x + BB_R) / BB_CELL);
  const r0 = Math.floor((eye.z - BB_R) / BB_CELL), r1 = Math.floor((eye.z + BB_R) / BB_CELL);
  const lim = W.extent_m / 2 - 10;
  for (let ci = c0; ci <= c1; ci++) for (let ri = r0; ri <= r1; ri++) {
    const x = (ci + wildsHash(ci, ri, W.seed, 11)) * BB_CELL, z = (ri + wildsHash(ci, ri, W.seed, 12)) * BB_CELL;
    const dx = x - eye.x, dz = z - eye.z, d2 = dx * dx + dz * dz;
    if (d2 <= VEG_R * VEG_R || d2 > BB_R * BB_R || Math.abs(x) > lim || Math.abs(z) > lim) continue;
    const roll = wildsHash(ci, ri, W.seed, 13);
    const h = T.height(x, z), g = T.growth(x, z, h, T.slope(x, z));
    const kind = roll < g.conifer ? 'conifer' : roll < g.conifer + g.deciduous ? 'deciduous' : null;
    if (kind === null || nearTrail(x, z, 4)) continue;
    cand[kind].push([d2, x, h, z, wildsHash(ci, ri, W.seed, 14)]);
  }
  bbMinR = Infinity;
  let at = 0;
  for (const k of BB_KINDS) {
    const list = cand[k], kind = BB_KINDS.indexOf(k);
    if (list.length > BB_CAP[k]) { list.sort((a, b) => a[0] - b[0]); list.length = BB_CAP[k]; }
    for (let n = 0; n < list.length; n++) {
      const [d2, x, h, z, r] = list[n];
      if (d2 < bbMinR * bbMinR) bbMinR = Math.sqrt(d2);
      const sc = 0.85 + r * 0.8;
      _e.set(0, r * 6.28, 0); _q.setFromEuler(_e); _s.set(sc, sc * (0.9 + r * 0.4), sc); _p.set(x, h - 0.2, z);
      _m.compose(_p, _q, _s); bbMesh.setMatrixAt(at + n, _m); bbKind.setX(at + n, kind);
    }
    bbCount[k] = list.length; at += list.length;
  }
  bbMesh.count = at; bbMesh.instanceMatrix.needsUpdate = true; bbKind.needsUpdate = true;
}
let vegAt = null;
const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _s = new THREE.Vector3(), _p = new THREE.Vector3(), _e = new THREE.Euler();
let trailSegs = [], clearings = [];
function nearTrail(x, z, r) {
  for (const s of trailSegs) {
    const dx = s[2] - s[0], dz = s[3] - s[1], L2 = dx * dx + dz * dz;
    let t = ((x - s[0]) * dx + (z - s[1]) * dz) / L2; t = t < 0 ? 0 : t > 1 ? 1 : t;
    const ex = x - s[0] - t * dx, ez = z - s[1] - t * dz;
    if (ex * ex + ez * ez < r * r) return true;
  }
  for (const c of clearings) { const dx = x - c.x, dz = z - c.z; if (dx * dx + dz * dz < c.r * c.r) return true; }
  return false;
}
function refillVeg() {
  vegAt = { x: eye.x, z: eye.z };
  const cand = { conifer: [], deciduous: [], rock: [] };
  const c0 = Math.floor((eye.x - VEG_R) / VEG_CELL), c1 = Math.floor((eye.x + VEG_R) / VEG_CELL);
  const r0 = Math.floor((eye.z - VEG_R) / VEG_CELL), r1 = Math.floor((eye.z + VEG_R) / VEG_CELL);
  const lim = W.extent_m / 2 - 10;
  for (let ci = c0; ci <= c1; ci++) for (let ri = r0; ri <= r1; ri++) {
    const x = (ci + wildsHash(ci, ri, W.seed, 1)) * VEG_CELL, z = (ri + wildsHash(ci, ri, W.seed, 2)) * VEG_CELL;
    const dx = x - eye.x, dz = z - eye.z, d2 = dx * dx + dz * dz;
    if (d2 > VEG_R * VEG_R || Math.abs(x) > lim || Math.abs(z) > lim) continue;
    const roll = wildsHash(ci, ri, W.seed, 3);
    if (roll > 0.97) continue;
    const h = T.height(x, z), s = T.slope(x, z), g = T.growth(x, z, h, s);
    let kind = null;
    if (roll < g.conifer) kind = 'conifer';
    else if (roll < g.conifer + g.deciduous) kind = 'deciduous';
    else if (wildsHash(ci, ri, W.seed, 4) < g.rock * 0.35) kind = 'rock';
    if (kind === null || nearTrail(x, z, kind === 'rock' ? 2.5 : 4)) continue;
    cand[kind].push([d2, x, h, z, wildsHash(ci, ri, W.seed, 5)]);
  }
  for (const k of Object.keys(cand)) {
    const list = cand[k], m = veg[k];
    if (list.length > CAP[k]) { list.sort((a, b) => a[0] - b[0]); list.length = CAP[k]; }
    for (let n = 0; n < list.length; n++) {
      const [, x, h, z, r] = list[n];
      if (k === 'rock') {
        const sc = 0.6 + r * 2.4;
        _e.set(r * 3, r * 7, r * 5); _q.setFromEuler(_e); _s.set(sc * (1 + r), sc * 0.6, sc);
        _p.set(x, h + sc * 0.15, z);
      } else {
        const sc = 0.75 + r * 0.9;
        _e.set(0, r * 6.28, 0); _q.setFromEuler(_e); _s.set(sc, sc * (0.9 + r * 0.5), sc);
        _p.set(x, h - 0.2, z);
      }
      _m.compose(_p, _q, _s); m.setMatrixAt(n, _m);
      col.setHSL(k === 'deciduous' ? 0.17 + r * 0.12 : 0.28 + r * 0.06, k === 'rock' ? 0.02 : 0.25, k === 'rock' ? 0.55 + r * 0.25 : 0.85 + r * 0.3);
      m.setColorAt(n, col);
    }
    m.count = list.length; m.instanceMatrix.needsUpdate = true;
    if (m.instanceColor) m.instanceColor.needsUpdate = true;
  }
  refillBillboards();
}

/* ------------------------------------------------ trails, props, water -- */
let trailMesh = null, propMesh = null, cacheMesh = null, water = null;
const nodePos = new Map();
function buildTrails() {
  const pos = [], idx = [];
  trailSegs = [];
  for (const leg of W.trails) {
    const a = nodePos.get(leg.from), b = nodePos.get(leg.to);
    trailSegs.push([a.x, a.z, b.x, b.z]);
    const L = Math.hypot(b.x - a.x, b.z - a.z), n = Math.ceil(L / 6);
    const px = -(b.z - a.z) / L * 1.2, pz = (b.x - a.x) / L * 1.2;
    const base = pos.length / 3;
    for (let k = 0; k <= n; k++) {
      const x = a.x + (b.x - a.x) * k / n, z = a.z + (b.z - a.z) * k / n;
      pos.push(x - px, T.height(x - px, z - pz) + 0.6, z - pz, x + px, T.height(x + px, z + pz) + 0.6, z + pz);
      if (k < n) { const p = base + k * 2; idx.push(p, p + 2, p + 1, p + 1, p + 2, p + 3); }
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(idx); g.computeVertexNormals();
  trailMesh = new THREE.Mesh(g, matTrail); worldGroup.add(trailMesh);
}
function box(w, h, d, x, y, z, c, ry = 0) { return painted(at(new THREE.BoxGeometry(w, h, d), x, y, z, ry), c); }
function cyl(r0, r1, h, x, y, z, c, seg = 6) { return painted(at(new THREE.CylinderGeometry(r0, r1, h, seg), x, y, z), c); }
const ORANGE = 0xE8A33D, STEEL = 0x8C979C, TIMBER = 0x9A6B3F, DARK = 0x33393C, CONC = 0xB8B4AA;
const KIT = {
  portal: () => [box(12, 1.6, 3, 0, 7.6, 0, CONC), box(1.6, 7, 3, -5.2, 3.5, 0, CONC), box(1.6, 7, 3, 5.2, 3.5, 0, CONC), box(8.8, 6.8, 0.4, 0, 3.4, -1.3, DARK), box(3, 2, 2, 9, 1, 4, ORANGE)],
  tower: () => [cyl(0.4, 2.8, 34, 0, 17, 0, STEEL, 4), box(16, 0.6, 0.6, 0, 30, 0, STEEL), box(10, 0.5, 0.5, 0, 26, 0, STEEL), cyl(0.3, 1.8, 30, 60, 15, 0, STEEL, 4)],
  netting: () => [box(22, 14, 0.3, 0, 7, -6, 0x707A6A), cyl(0.2, 0.2, 15, -11, 7.5, -6, STEEL), cyl(0.2, 0.2, 15, 11, 7.5, -6, STEEL), box(4, 2.4, 2, 6, 1.2, 4, ORANGE)],
  grader: () => [box(9, 1.6, 2.4, 0, 1.6, 0, 0xE0B23A), box(2.4, 2.2, 2.4, 3, 3.4, 0, 0xE0B23A), box(3.8, 0.8, 0.4, -1, 0.6, 0, DARK), box(8, 2.6, 2.6, -1, 1.8, 7, 0xC7473A)],
  turbine: () => [cyl(1.4, 2.2, 60, 0, 30, 0, 0xE9ECEE, 8), box(3, 3, 7, 0, 61, 0, 0xE9ECEE), box(1, 34, 0.6, 0, 61, 3.8, 0xE9ECEE), box(18, 1.2, 18, 0, 0.6, 0, CONC)],
  survey: () => [cyl(0.6, 0.8, 1.2, 0, 0.6, 0, CONC), cyl(0.05, 0.05, 1.6, 2, 0.8, 0, ORANGE, 4), box(6, 0.1, 6, 8, 0.05, 0, 0xDADADA)],
  lineclear: () => [cyl(0.2, 0.28, 12, 0, 6, 0, TIMBER), box(3, 0.3, 0.3, 0, 11, 0, TIMBER), cyl(0.2, 0.28, 12, 45, 6, 0, TIMBER), box(3, 0.3, 0.3, 45, 11, 0, TIMBER), box(3, 2.8, 7, 12, 1.4, 5, 0xE9ECEE)],
  bridge: () => [box(3, 0.4, 26, 0, 3, 0, TIMBER), box(0.2, 1.1, 26, 1.4, 3.7, 0, TIMBER), box(0.2, 1.1, 26, -1.4, 3.7, 0, TIMBER), box(4, 3, 1, 0, 1.5, 12.5, CONC), box(4, 3, 1, 0, 1.5, -12.5, CONC)],
  fuelbreak: () => [box(5, 2.6, 2.6, 0, 1.3, 0, 0x5E7A3E), box(1.5, 1.2, 1.2, 3, 3, 0, DARK), box(30, 0.05, 60, 0, 0.03, 0, 0x8E8458)],
  frame: () => [0, 1, 2].flatMap((k) => [box(0.4, 5, 0.4, -4, 2.5, k * 4 - 4, TIMBER), box(0.4, 5, 0.4, 4, 2.5, k * 4 - 4, TIMBER), box(8.8, 0.5, 0.5, 0, 5, k * 4 - 4, TIMBER)]).concat([box(0.4, 0.4, 9, 0, 6.8, 0, TIMBER)]),
  intake: () => [box(6, 3, 6, 0, 1.5, 0, CONC), cyl(0.5, 0.5, 30, 0, 0.5, 18, STEEL, 8).rotateX(0), box(2, 2.4, 2, 5, 1.2, -4, ORANGE)],
  lookout: () => [cyl(1, 3, 22, 0, 11, 0, STEEL, 4), box(5, 3, 5, 0, 23.5, 0, 0xD8D2C4), box(6, 0.4, 6, 0, 25.2, 0, DARK)],
  dam: () => [box(40, 4, 3, 0, 2, 0, CONC), box(6, 6, 6, 18, 3, 8, CONC), cyl(0.9, 0.9, 30, 18, 1, 25, STEEL, 8)],
  pipeline: () => [box(60, 1.1, 1.1, 0, 0.8, 0, 0x3E5C3A), box(4, 2.6, 2.4, 6, 1.3, 5, 0xE0B23A), box(3, 0.05, 8, -6, 0.03, -4, 0x6F5A45)],
  vault: () => [box(4, 0.5, 4, 0, 0.25, 0, CONC), cyl(0.05, 0.05, 2.6, 0, 1.3, 0, ORANGE, 4), cyl(1.2, 1.2, 0.1, 0, 2.6, 0, ORANGE, 3), box(6, 2.6, 2.4, 5, 1.3, 5, 0xC7473A)],
  solar: () => [0, 1, 2, 3, 4].flatMap((r) => [box(36, 0.12, 3, 0, 1.6, r * 7 - 14, 0x24344A)]).concat([box(4, 2.4, 3, 22, 1.2, 0, 0xE9ECEE)]),
  pumpstation: () => [box(14, 7, 10, 0, 3.5, 0, CONC), box(14.4, 0.6, 10.4, 0, 7.3, 0, DARK), cyl(0.8, 0.8, 24, -3, 1, 16, STEEL, 8), cyl(0.8, 0.8, 24, 3, 1, 16, STEEL, 8), box(3, 2.4, 2.4, 10, 1.2, -4, ORANGE)],
  berth: () => [box(40, 2, 12, 0, 1, 0, CONC), cyl(0.5, 0.5, 3, -16, 2.5, 5, DARK, 6), cyl(0.5, 0.5, 3, 16, 2.5, 5, DARK, 6), box(3, 18, 3, 0, 11, -2, ORANGE), box(2, 2, 28, 0, 20, 8, ORANGE), box(30, 3, 10, 0, 1, 14, 0x4A5A64)],
  boom: () => [0, 1, 2, 3, 4, 5].map((k) => cyl(0.45, 0.45, 5, -14 + k * 5.4, 0.5, 3 + (k % 2), 0xE0B23A, 8)).concat([box(6, 2.6, 2.6, 6, 1.3, -6, 0xE9ECEE), box(4, 1.6, 3, -6, 0.8, -6, 0xC7473A)]),
  quarry: () => [box(30, 8, 12, 0, 4, -14, 0xA0765A), box(24, 4, 10, 0, 2, -4, 0xA88064), box(3, 3, 5, 8, 1.5, 6, 0xE0B23A)],
};
function buildProps() {
  const parts = [];
  for (const s of W.sites) {
    const h = T.height(s.x, s.z), ry = (s.x * 7 + s.z * 3) % 6.28;
    for (const g of KIT[s.kind]()) { g.rotateY(ry); g.translate(s.x, h, s.z); parts.push(g); }
    parts.push(cyl(0.15, 0.15, 7, s.x + s.pad_m * 0.6, h + 3.5, s.z, ORANGE, 5), box(1.4, 0.9, 0.05, s.x + s.pad_m * 0.6 + 0.75, h + 6.4, s.z, ORANGE));
  }
  const th = W.trailhead, hh = T.height(th.x, th.z);
  parts.push(box(4, 2.4, 0.3, th.x, hh + 1.2, th.z, TIMBER), box(4.6, 0.3, 0.8, th.x, hh + 2.5, th.z, DARK));
  propMesh = new THREE.Mesh(mergeGeometries(parts), matProp); worldGroup.add(propMesh);
}
let cachePos = [];
function buildCaches() {
  cachePos = [];
  const parts = [];
  for (const c of W.caches) {
    let x, z;
    if (c.kind === 'summit') { const s = T.summit(); x = s.x; z = s.z; } else { x = c.x; z = c.z; }
    const h = T.height(x, z);
    cachePos.push({ id: c.id, kind: c.kind, x, z, h, found: false });
    parts.push(box(0.7, 0.45, 0.45, x, h + 0.22, z, 0x6B6F4A));
    if (c.kind === 'summit') for (let k = 0; k < 4; k++) parts.push(painted(at(new THREE.DodecahedronGeometry(0.7 - k * 0.12, 0), x + 1.4, h + 0.4 + k * 0.7, z), 0x8A857C));
  }
  cacheMesh = new THREE.Mesh(mergeGeometries(parts), matProp); worldGroup.add(cacheMesh);
}
function buildWater() {
  water = new THREE.Mesh(new THREE.PlaneGeometry(W.extent_m, W.extent_m).rotateX(-Math.PI / 2), matWater);
  water.position.y = W.biome.water_level_m; worldGroup.add(water);
}

/* ------------------------------------------------------------ minimap -- */
const mini = document.getElementById('minimap'), mctx = mini.getContext('2d');
let miniBase = null;
function buildMinimap() {
  const N = 160, img = mctx.createImageData(N, N), half = W.extent_m / 2;
  for (let a = 0; a < N; a++) for (let c = 0; c < N; c++) {
    const x = -half + (c + 0.5) * W.extent_m / N, z = -half + (a + 0.5) * W.extent_m / N, h = T.height(x, z);
    const sh = Math.max(0.55, Math.min(1.25, 1 - (T.height(x + 30, z + 30) - h) / 40));
    if (h < W.biome.water_level_m) col.set(0x3E6E8E); else groundColor(x, z, h, 0.9, col);
    const k = (a * N + c) * 4;
    img.data[k] = Math.min(255, col.r * 255 * sh); img.data[k + 1] = Math.min(255, col.g * 255 * sh); img.data[k + 2] = Math.min(255, col.b * 255 * sh); img.data[k + 3] = 255;
  }
  const off = document.createElement('canvas'); off.width = off.height = N;
  off.getContext('2d').putImageData(img, 0, 0);
  miniBase = off;
}
function toMini(x, z) { const S = mini.width; return [(x / W.extent_m + 0.5) * S, (z / W.extent_m + 0.5) * S]; }
const tok = (n) => getComputedStyle(document.body).getPropertyValue(n).trim();
function drawMinimap() {
  const S = mini.width, amber = tok('--tc-amber'), steel = tok('--tc-steel'), ink = tok('--tc-ink'), plate = tok('--tc-plate');
  mctx.imageSmoothingEnabled = true; mctx.drawImage(miniBase, 0, 0, S, S);
  mctx.strokeStyle = ink; mctx.lineWidth = 1.5; mctx.beginPath();
  for (const s of trailSegs) { const a = toMini(s[0], s[1]), b = toMini(s[2], s[3]); mctx.moveTo(a[0], a[1]); mctx.lineTo(b[0], b[1]); }
  mctx.stroke();
  mctx.fillStyle = amber;
  for (const s of W.sites) { const p = toMini(s.x, s.z); mctx.fillRect(p[0] - 3, p[1] - 3, 6, 6); }
  /* a ring marks a site with simulated tasks */
  mctx.strokeStyle = steel; mctx.lineWidth = 2;
  for (const s of W.sites) if (SITE_TASKS[s.id] > 0) { const p = toMini(s.x, s.z); mctx.beginPath(); mctx.arc(p[0], p[1], 7, 0, 6.2832); mctx.stroke(); }
  const p = toMini(eye.x, eye.z);
  mctx.save(); mctx.translate(p[0], p[1]); mctx.rotate(-eye.yaw);
  mctx.fillStyle = ink; mctx.strokeStyle = plate; mctx.beginPath();
  mctx.moveTo(0, -7); mctx.lineTo(5, 5); mctx.lineTo(-5, 5); mctx.closePath(); mctx.fill(); mctx.stroke(); mctx.restore();
}
mini.addEventListener('click', (ev) => {
  const r = mini.getBoundingClientRect();
  const x = ((ev.clientX - r.left) / r.width - 0.5) * W.extent_m, z = ((ev.clientY - r.top) / r.height - 0.5) * W.extent_m;
  const lim = W.extent_m / 2 - W.biome.rim_width_m;
  teleport(Math.max(-lim, Math.min(lim, x)), Math.max(-lim, Math.min(lim, z)), eye.yaw);
});

/* -------------------------------------------------------- site labels -- */
const labelLayer = document.getElementById('labels');
let labelEls = [];
function buildLabels() {
  labelLayer.textContent = '';
  labelEls = W.sites.map((s) => {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'lbl'; b.textContent = s.title; b.dataset.site = s.id;
    if (SITE_TASKS[s.id] > 0) { b.classList.add('has-tasks'); const n = document.createElement('span'); n.className = 'tcount'; n.textContent = String(SITE_TASKS[s.id]); b.prepend(n); }
    b.addEventListener('click', () => openSite(s.id));
    labelLayer.appendChild(b);
    return { el: b, x: s.x, z: s.z, y: T.height(s.x, s.z) + 9 };
  });
  const th = W.trailhead, b = document.createElement('span');
  b.className = 'lbl th'; b.textContent = th.name; labelLayer.appendChild(b);
  labelEls.push({ el: b, x: th.x, z: th.z, y: T.height(th.x, th.z) + 4 });
}
const _v = new THREE.Vector3();
function placeLabels() {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  for (const L of labelEls) {
    const d = Math.hypot(L.x - camera.position.x, L.z - camera.position.z);
    _v.set(L.x, L.y, L.z).project(camera);
    const show = (mode === 'overview' || d < 1500) && _v.z < 1 && Math.abs(_v.x) < 1 && Math.abs(_v.y) < 1;
    L.el.hidden = !show;
    if (show) L.el.style.transform = `translate(${((_v.x + 1) / 2 * w).toFixed(0)}px,${((1 - _v.y) / 2 * h).toFixed(0)}px) translate(-50%,-100%)`;
  }
}

/* ---------------------------------------------------------- site panel -- */
const panel = document.getElementById('panel'), panelBody = document.getElementById('panel-body');
let openId = null, thSigned = false;
function openSite(id) {
  const card = document.getElementById('site-' + id);
  if (card === null) throw new Error('wilds: no card for site ' + id);
  panelBody.textContent = '';
  const clone = card.cloneNode(true); clone.removeAttribute('id');
  const go = clone.querySelector('.go'); if (go) go.remove();
  panelBody.appendChild(clone);
  for (const q of document.querySelectorAll(`.qhook[data-wilds-place="${id}"][data-tc-quest]`)) {
    const b = document.createElement('button'); b.type = 'button'; b.className = 'qmark tc-btn tc-btn-ghost'; b.textContent = L['side_quest'] + ': ' + q.textContent;
    b.addEventListener('click', () => q.click()); panelBody.appendChild(b);
  }
  panel.hidden = false; openId = id;
}
document.getElementById('panel-close').addEventListener('click', () => { panel.hidden = true; });
function toast(msg) {
  const t = document.getElementById('toast'); t.textContent = msg; t.hidden = false;
  clearTimeout(toast.timer); toast.timer = setTimeout(() => { t.hidden = true; }, 3200);
}
function checkNear() {
  for (const s of W.sites) {
    const d = Math.hypot(s.x - eye.x, s.z - eye.z);
    if (d < s.pad_m && openId !== s.id) openSite(s.id);
  }
  // the trailhead book: a place quests may name ("trailhead"), signed by walking up to the board
  if (!thSigned && Math.hypot(W.trailhead.x - eye.x, W.trailhead.z - eye.z) < 3.5) {
    thSigned = true;
    const hooks = document.querySelectorAll(`.qhook[data-wilds-world="${W.id}"][data-wilds-place="trailhead"][data-tc-egg]`);
    if (hooks.length) for (const hk of hooks) hk.click();
    else toast(L['toast.trailhead']);
  }
  for (const c of cachePos) {
    if (c.found) continue;
    if (Math.hypot(c.x - eye.x, c.z - eye.z) < 4) {
      c.found = true;
      const hooks = document.querySelectorAll(`.qhook[data-wilds-world="${W.id}"][data-wilds-place="${c.id}"][data-tc-egg]`);
      if (hooks.length) for (const hk of hooks) hk.click();
      else toast(L['toast.cache']);
    }
  }
}

/* ------------------------------------------------------------ controls -- */
const keys = {};
addEventListener('keydown', (e) => {
  if (e.target.closest && e.target.closest('input,textarea,select')) return;
  keys[e.code] = true;
  if (e.code === 'KeyO') { if (flying !== null) stopFlyover(); setMode(mode === 'walk' ? 'overview' : 'walk'); }
  if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space'].includes(e.code) && e.target === canvas) e.preventDefault();
});
addEventListener('keyup', (e) => { keys[e.code] = false; });
addEventListener('blur', () => { for (const k in keys) keys[k] = false; });
let drag = null;
canvas.addEventListener('pointerdown', (e) => { if (mode !== 'walk') return; drag = { x: e.clientX, y: e.clientY, id: e.pointerId }; canvas.setPointerCapture(e.pointerId); canvas.focus(); });
canvas.addEventListener('pointermove', (e) => {
  if (!drag || e.pointerId !== drag.id) return;
  eye.yaw -= (e.clientX - drag.x) * 0.005; eye.pitch = Math.max(-1.3, Math.min(1.2, eye.pitch - (e.clientY - drag.y) * 0.004));
  drag.x = e.clientX; drag.y = e.clientY;
});
canvas.addEventListener('pointerup', () => { drag = null; });
canvas.addEventListener('pointercancel', () => { drag = null; });
const stick = document.getElementById('stick'), knob = stick.querySelector('i');
const stickIn = { f: 0, s: 0, id: null };
stick.addEventListener('pointerdown', (e) => { stickIn.id = e.pointerId; stick.setPointerCapture(e.pointerId); moveStick(e); });
stick.addEventListener('pointermove', (e) => { if (e.pointerId === stickIn.id) moveStick(e); });
const endStick = () => { stickIn.id = null; stickIn.f = stickIn.s = 0; knob.style.transform = ''; };
stick.addEventListener('pointerup', endStick); stick.addEventListener('pointercancel', endStick);
function moveStick(e) {
  const r = stick.getBoundingClientRect(), R = r.width / 2;
  let dx = (e.clientX - r.left - R) / R, dy = (e.clientY - r.top - R) / R; const m = Math.hypot(dx, dy);
  if (m > 1) { dx /= m; dy /= m; }
  stickIn.f = -dy; stickIn.s = dx; knob.style.transform = `translate(${dx * R * 0.6}px,${dy * R * 0.6}px)`;
}
const speedBtn = document.getElementById('speed');
const SPEEDS = [[L['pace.walk'], WALK_MS], [L['pace.run'], RUN_MS], [L['pace.fast'], FAST_MS]];
speedBtn.addEventListener('click', () => { speedMode = (speedMode + 1) % 3; speedBtn.textContent = L.pace + ': ' + SPEEDS[speedMode][0]; });
document.getElementById('mode').addEventListener('click', () => { if (flying !== null) stopFlyover(); setMode(mode === 'walk' ? 'overview' : 'walk'); });
function walk(dt) {
  let f = (keys.KeyW || keys.ArrowUp ? 1 : 0) - (keys.KeyS || keys.ArrowDown ? 1 : 0) + stickIn.f;
  let s = (keys.KeyD ? 1 : 0) - (keys.KeyA ? 1 : 0) + stickIn.s;
  const turn = (keys.ArrowLeft ? 1 : 0) - (keys.ArrowRight ? 1 : 0) + (keys.KeyQ ? 1 : 0) - (keys.KeyE ? 1 : 0);
  eye.yaw += turn * 1.6 * dt;
  const m = Math.hypot(f, s); if (m > 1) { f /= m; s /= m; }
  let v = SPEEDS[speedMode][1]; if ((keys.ShiftLeft || keys.ShiftRight) && speedMode === 0) v = RUN_MS;
  if (f < 0) v = Math.min(v, WALK_MS);
  const sx = Math.sin(eye.yaw), cz = Math.cos(eye.yaw);
  const nx = eye.x + (-sx * f + cz * s) * v * dt, nz = eye.z + (-cz * f - sx * s) * v * dt;
  const lim = W.extent_m / 2 - 20;
  if (Math.abs(nx) < lim && Math.abs(nz) < lim && T.height(nx, nz) > W.biome.water_level_m - 0.4) { eye.x = nx; eye.z = nz; }
}
/* The ground the eye stands on is the finest chunk's triangles, not the
   noise between them: on a steep slope the two differ by metres, and an
   eye placed on the noise can end up inside the mesh. Same triangle split
   as chunkGeometry's index order. */
function meshHeight(x, z) {
  const st = W.chunk_m / RING_SEGS[0], c = Math.floor(x / st), a = Math.floor(z / st);
  const u = x / st - c, v = z / st - a;
  const h00 = T.height(c * st, a * st), h10 = T.height((c + 1) * st, a * st), h01 = T.height(c * st, (a + 1) * st);
  if (u + v <= 1) return h00 + u * (h10 - h00) + v * (h01 - h00);
  const h11 = T.height((c + 1) * st, (a + 1) * st);
  return h11 + (1 - u) * (h01 - h11) + (1 - v) * (h10 - h11);
}
function placeEye() {
  camera.position.set(eye.x, Math.max(meshHeight(eye.x, eye.z), T.height(eye.x, eye.z), W.biome.water_level_m) + EYE_H, eye.z);
  camera.rotation.set(eye.pitch, eye.yaw, 0, 'YXZ');
}
function teleport(x, z, yaw) {
  eye.x = x; eye.z = z; eye.yaw = yaw; eye.pitch = -0.05;
  if (mode === 'overview') { orbit.target.set(x, T.height(x, z), z); }
  else placeEye();
  updateChunks(true); refillVeg(); openId = null;
}

/* ------------------------------------------------------------ flyover -- */
/* A deterministic camera path over the world, for the Flyover button and for
   filming (MEDIA steps it frame by frame through __wilds.flyover(t)). Its
   keyframes are DERIVED from the registry: the trailhead, then every site in
   trail order; the eye stands FLY_BACK_M out from each stop (away from the
   next one, so the path sweeps) and FLY_UP_M above the ground, looking at the
   stop; between keyframes it never drops below FLY_CLEAR_M over the ground. */
const FLY_BACK_M = 700, FLY_UP_M = 380, FLY_CLEAR_M = 120, FLY_S = 60;
let flying = null, fly = null;
function flyKeys() {
  const order = ['trailhead', ...W.trails.map((l) => l.to)], lim = W.extent_m / 2 - 50;
  const stops = order.map((id) => nodePos.get(id)), eyes = [], ats = [];
  stops.forEach((p, k) => {
    const q = stops[(k + 1) % stops.length], h = T.height(p.x, p.z);
    let dx = p.x - q.x, dz = p.z - q.z; const n = Math.hypot(dx, dz);
    if (n === 0) throw new Error('wilds flyover: two stops at one point');
    dx /= n; dz /= n;
    const ex = Math.max(-lim, Math.min(lim, p.x + dx * FLY_BACK_M)), ez = Math.max(-lim, Math.min(lim, p.z + dz * FLY_BACK_M));
    eyes.push(new THREE.Vector3(ex, Math.max(h, T.height(ex, ez)) + FLY_UP_M, ez));
    ats.push(new THREE.Vector3(p.x, h, p.z));
  });
  return { world: W.id, stops: order, eye: new THREE.CatmullRomCurve3(eyes, true, 'centripetal'), at: new THREE.CatmullRomCurve3(ats, true, 'centripetal'), eyes, ats };
}
const _fe = new THREE.Vector3(), _fa = new THREE.Vector3();
function flyTo(t) {
  if (!(t >= 0 && t <= 1)) throw new Error('wilds flyover: t must be in [0, 1], got ' + t);
  if (fly === null || fly.world !== W.id) fly = flyKeys();
  fly.eye.getPoint(t, _fe); fly.at.getPoint(t, _fa);
  _fe.y = Math.max(_fe.y, T.height(_fe.x, _fe.z) + FLY_CLEAR_M);
  if (mode !== 'overview') setMode('overview');
  orbit.enabled = false;
  camera.position.copy(_fe); orbit.target.copy(_fa); camera.lookAt(_fa);
  return { eye: [_fe.x, _fe.y, _fe.z], at: [_fa.x, _fa.y, _fa.z] };
}
function stopFlyover() {
  flying = null;
  const b = document.getElementById('fly'); b.setAttribute('aria-pressed', 'false');
  orbit.enabled = mode === 'overview';
}
document.getElementById('fly').addEventListener('click', () => {
  if (flying !== null) { stopFlyover(); return; }
  flying = performance.now(); document.getElementById('fly').setAttribute('aria-pressed', 'true');
});

/* --------------------------------------------------------------- modes -- */
function fogFor(m) {
  scene.fog = m === 'overview' ? new THREE.Fog(W.fog, W.extent_m * 0.9, W.extent_m * 2.2)
    : new THREE.Fog(W.fog, 250, W.extent_m * 0.7);
}
function setMode(m) {
  mode = m;
  document.getElementById('mode').textContent = m === 'walk' ? L['mode.overview'] : L['mode.walk'];
  document.getElementById('mode').setAttribute('aria-pressed', String(m === 'overview'));
  stage.dataset.mode = m;
  fogFor(m);
  const walkOn = m === 'walk';
  for (const ch of chunks.values()) ch.mesh.visible = walkOn;
  overviewMesh.visible = !walkOn;
  horizonMesh.visible = walkOn;
  for (const k in veg) veg[k].visible = walkOn;
  bbMesh.visible = walkOn;
  cacheMesh.visible = walkOn;
  orbit.enabled = !walkOn;
  if (!walkOn) {
    orbit.target.set(0, W.biome.relief_m * 0.3, 0);
    camera.position.set(0, W.extent_m * 0.78, W.extent_m * 0.5);
    orbit.update();
  } else placeEye();
}

async function loadWorld(id) {
  const w = WORLDS.get(id);
  if (w === undefined) throw new Error('wilds: unknown world ' + id);
  for (const ch of chunks.values()) ch.mesh.geometry.dispose();
  chunks.clear(); worldGroup.clear(); queue = [];
  if (flying !== null) stopFlyover();
  W = w; T = wildsTerrain(W); fly = null;
  pal = Object.fromEntries(Object.entries(W.biome.palette).map(([k, v]) => [k, hex(v)]));
  scene.background = new THREE.Color(W.sky); stage.style.setProperty('--wilds-sky', W.sky);
  nodePos.clear(); nodePos.set('trailhead', W.trailhead);
  for (const s of W.sites) nodePos.set(s.id, s);
  clearings = W.sites.map((s) => ({ x: s.x, z: s.z, r: s.pad_m * 1.2 }));
  buildTrails(); buildProps(); buildCaches(); buildWater(); buildOverview(); buildMinimap(); buildLabels();
  for (const c of cachePos) clearings.push({ x: c.x, z: c.z, r: 3 });
  const first = W.trails[0], to = nodePos.get(first.to);
  eye.x = W.trailhead.x; eye.z = W.trailhead.z + 6;
  eye.yaw = Math.atan2(-(to.x - eye.x), -(to.z - eye.z)); eye.pitch = -0.05;
  for (const b of document.querySelectorAll('#switch button')) b.setAttribute('aria-pressed', String(b.dataset.world === id));
  for (const s of document.querySelectorAll('[data-world-card]')) s.hidden = s.dataset.worldCard !== id;
  panel.hidden = true; openId = null; thSigned = false;
  document.getElementById('where').textContent = W.name;
  updateChunks(true); refillVeg();
  setMode('walk');
  const cur = decodeURIComponent((location.hash || '').slice(1)).split('/')[0];
  if (cur !== id) try { history.replaceState(null, '', '#' + id); } catch (e) { /* a sandboxed frame may refuse */ }
}
for (const b of document.querySelectorAll('#switch button')) b.addEventListener('click', () => loadWorld(b.dataset.world));
/* Deep links: #<world id> opens a world at its trailhead; #<world id>/<site id>
   opens it standing at that site with its panel (and its tasks) open. */
function goSite(id) {
  const s = W.sites.find((x) => x.id === id);
  if (s === undefined) throw new Error('wilds: no site ' + id + ' in ' + W.id);
  if (mode !== 'walk') setMode('walk');
  // stand on the pad, three quarters of pad_m south of its centre, facing it:
  // a task's deep link lands at the site (eval_wilds holds it within pad_m)
  teleport(s.x, s.z + s.pad_m * 0.75, 0);
  openSite(s.id);
}
async function fromHash() {
  const [wid, sid] = decodeURIComponent((location.hash || '').slice(1)).split('/');
  if (!WORLDS.has(wid)) return false;
  if (W === null || W.id !== wid) await loadWorld(wid);
  if (sid) goSite(sid);
  return true;
}
addEventListener('hashchange', () => { fromHash(); });
for (const b of document.querySelectorAll('.site .go')) b.addEventListener('click', () => {
  goSite(b.dataset.goto);
  stage.scrollIntoView({ block: 'start' });
});

/* --------------------------------------------------------------- loop -- */
function resize() {
  const w = stage.clientWidth, h = stage.clientHeight;
  renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
}
addEventListener('resize', resize);
const hud = document.getElementById('hud-alt');
let last = performance.now(), lastInfo = { calls: 0, triangles: 0 }, miniT = 0, frameMs = 0;
function frame(now) {
  const dt = Math.min(0.1, (now - last) / 1000); last = now;
  if (flying !== null) flyTo(((now - flying) / 1000 / FLY_S) % 1);
  else if (mode === 'walk') {
    walk(dt); placeEye();
    const ci = Math.floor(eye.x / W.chunk_m) + ',' + Math.floor(eye.z / W.chunk_m);
    if (ci !== frame.cell) { frame.cell = ci; updateChunks(false); } else pump(BUILD_PER_FRAME);
    if (Math.hypot(eye.x - vegAt.x, eye.z - vegAt.z) > VEG_REFILL) refillVeg();
    checkNear();
  } else orbit.update();
  const t0 = performance.now();
  renderer.render(scene, camera);
  frameMs = performance.now() - t0;
  lastInfo = { calls: renderer.info.render.calls, triangles: renderer.info.render.triangles };
  placeLabels();
  if (now - miniT > 150) { miniT = now; drawMinimap(); hud.textContent = Math.round(camera.position.y - EYE_H) + ' m (authored height)'; }
  requestAnimationFrame(frame);
}

/* Eval hooks: web/eval_wilds.mjs drives the page through these. */
function denseSpot() {
  let best = null; const lim = W.extent_m / 2 - W.biome.rim_width_m - 400, st = W.extent_m / 40;
  for (let x = -lim; x <= lim; x += st) for (let z = -lim; z <= lim; z += st) {
    const h = T.height(x, z), g = T.growth(x, z, h, T.slope(x, z)), d = g.conifer + g.deciduous;
    if (best === null || d > best.d) best = { x, z, d };
  }
  return best;
}
window.__wilds = {
  worlds: () => REG.worlds.map((w) => w.id),
  load: (id) => loadWorld(id),
  view(name) {
    if (name === 'overview') { setMode('overview'); return; }
    if (mode !== 'walk') setMode('walk');
    if (name === 'trail') { const to = nodePos.get(W.trails[0].to); teleport(W.trailhead.x, W.trailhead.z + 6, Math.atan2(-(to.x - W.trailhead.x), -(to.z - W.trailhead.z - 6))); }
    else if (name === 'dense') { const d = denseSpot(); teleport(d.x, d.z, 0.7); }
    else if (name === 'summit') { const s = T.summit(); teleport(s.x + 3, s.z + 3, Math.atan2(s.x, s.z)); eye.pitch = -0.12; placeEye(); }
    else throw new Error('wilds: unknown view ' + name);
  },
  stats: () => ({
    world: W.id, mode, calls: lastInfo.calls, triangles: lastInfo.triangles,
    chunks: mode === 'walk' ? chunks.size : 1, pending: queue.length,
    instances: Object.fromEntries(Object.entries(veg).map(([k, m]) => [k, m.visible ? m.count : 0])),
    instanced: Object.values(veg).every((m) => m.isInstancedMesh), frameMs,
    horizon: horizonMesh.visible,
    billboards: Object.fromEntries(BB_KINDS.map((k) => [k, bbMesh.visible ? bbCount[k] : 0])),
    billboardsInstanced: bbMesh.isInstancedMesh, billboardMeshes: scene.children.filter((o) => o.geometry === bbGeo).length,
    billboardMinR: bbMinR, vegR: VEG_R, billboardR: BB_R,
  }),
  frameTimes(n) {
    const gl = renderer.getContext(), out = [];
    const px = new Uint8Array(4);
    // readPixels cannot return until the frame is drawn, so it is the fence
    for (let k = 0; k < n; k++) { const t = performance.now(); renderer.render(scene, camera); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); out.push(performance.now() - t); }
    lastInfo = { calls: renderer.info.render.calls, triangles: renderer.info.render.triangles };
    return out;
  },
  caches: () => cachePos.map((c) => ({ ...c })),
  /* Flyover for filming: flyoverPath() gives the DERIVED keyframes of the
     current world; flyover(t) with t in [0,1] places the camera on the closed
     path and returns {eye, at}; flyover(null) hands the view back. */
  flyoverPath() {
    if (fly === null || fly.world !== W.id) fly = flyKeys();
    return { world: W.id, seconds: FLY_S, stops: fly.stops,
      keyframes: fly.eyes.map((e, k) => ({ eye: [e.x, e.y, e.z], at: [fly.ats[k].x, fly.ats[k].y, fly.ats[k].z] })) };
  },
  flyover(t) { if (t === null) { stopFlyover(); return null; } flying = null; return flyTo(t); },
  eye: () => ({ ...eye }),
  teleport: (x, z, yaw) => teleport(x, z, yaw),
  /* Camera hook for filming flyovers (same shape as the 3D page's
     __tc3dDo('cam', ...)): "eyeX,eyeY,eyeZ|atX,atY,atZ" places a free
     camera in overview mode (the whole world is drawn, orbit paused while
     it is held); cam(null) hands the view back to the orbit. Ground-level
     shots use view('trail'|'dense'|'summit') or teleport(). */
  cam(arg) {
    if (arg === null) { orbit.enabled = mode === 'overview'; return null; }
    const parts = String(arg).split('|').map((v) => v.split(',').map(Number));
    const eyeP = parts[0], atP = parts[1];
    if (eyeP.length !== 3 || eyeP.some((v) => !Number.isFinite(v))) throw new Error('wilds cam: expected "x,y,z|x,y,z", got ' + arg);
    if (mode !== 'overview') setMode('overview');
    orbit.enabled = false;
    camera.position.set(eyeP[0], eyeP[1], eyeP[2]);
    if (atP !== undefined) { orbit.target.set(atP[0], atP[1], atP[2]); camera.lookAt(atP[0], atP[1], atP[2]); }
    return { x: camera.position.x, y: camera.position.y, z: camera.position.z };
  },
};
resize();
if (!(await fromHash())) await loadWorld(REG.worlds[0].id);
requestAnimationFrame(frame);
document.documentElement.dataset.wildsReady = '1';
'''

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' stroke='%23E8A33D' stroke-width='2.6' stroke-linejoin='round'/%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E">
<title>SmartCiti.X : Trade Craft Academy — the wilds</title>
<style>
/* UI colours come ONLY from the site theme's tokens (--tc-*, set by the canvas
   theme layer and by the Style switcher's data-style on <html>), so every
   style applies here; the world's own sky and ground colours are the world's. */
body.tc-theme-canvas{{
  --plate:var(--tc-plate); --panel:var(--tc-panel); --sunk:color-mix(in srgb,var(--tc-plate) 78%,black);
  --ink:var(--tc-ink); --muted:var(--tc-muted); --rule:var(--tc-line); --mark:var(--tc-amber);
  --mark-ink:var(--tc-amber-ink); --steel:var(--tc-steel); --good:var(--tc-ok);
  --scrim:color-mix(in srgb,var(--tc-plate) 84%,transparent);
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--plate);color:var(--ink);font:16px/1.6 "IBM Plex Sans",system-ui,sans-serif}}
.wrap{{max-width:1280px;margin:0 auto;padding:0 16px 48px}}
header{{padding:28px 0 8px;border-bottom:3px solid var(--mark)}}
header h1{{font:700 32px/1.1 "Barlow Condensed",system-ui,sans-serif;margin:0}}
header h1 .x{{color:var(--mark)}}
header p{{color:var(--muted);margin:6px 0 12px}}
a{{color:var(--steel)}}
#switch{{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}}
#switch .tc-btn[aria-pressed="true"]{{background:var(--mark);color:var(--mark-ink);border-color:var(--mark)}}
#stage .ctl .tc-btn{{background:var(--scrim);color:var(--ink);min-block-size:40px;padding:8px 14px}}
#stage .ctl .tc-btn[aria-pressed="true"]{{background:var(--steel);color:var(--sunk);border-color:var(--steel)}}
#panel .site{{background:none;border:0;padding:0}}
.go,.qmark{{margin-top:8px}}
#stage{{position:relative;height:min(72vh,720px);min-height:380px;border:1px solid var(--rule);border-radius:10px;overflow:hidden;background:var(--wilds-sky);touch-action:none}}
#view{{display:block;width:100%;height:100%;outline:none}}
#view:focus-visible,#view:focus{{outline:3px solid var(--mark);outline-offset:-3px}}
#labels{{position:absolute;inset:0;pointer-events:none;overflow:hidden}}
.lbl{{position:absolute;left:0;top:0;pointer-events:auto;font:600 12px/1.2 "IBM Plex Sans",system-ui,sans-serif;background:var(--scrim);color:var(--ink);border:1px solid var(--mark);border-radius:5px;padding:4px 7px;white-space:nowrap;cursor:pointer;max-width:220px;overflow:hidden;text-overflow:ellipsis}}
.lbl.th{{border-color:var(--steel);cursor:default}}
.lbl .tcount{{display:inline-block;margin-inline-end:6px;min-width:18px;border-radius:9px;background:var(--steel);color:var(--sunk);text-align:center;font-size:11px;padding:1px 5px}}
.lbl.has-tasks{{border-color:var(--steel)}}
.geo{{color:var(--muted);font-size:14px;margin:2px 0}}
.tasks{{margin:0;padding-inline-start:18px}}
.tasks li{{margin:4px 0}}
.tlaunch{{min-block-size:32px;padding:4px 12px;font-size:13px;margin-inline-start:4px}}
.treq{{color:var(--muted);font-size:13px}}
.halltasks .tk-list{{margin:0;padding-inline-start:18px;font-size:14px}}
.ctl{{position:absolute;top:10px;inset-inline-start:10px;display:flex;flex-wrap:wrap;gap:6px;align-items:center;max-width:calc(100% - 200px)}}
.ctl .where{{background:var(--scrim);color:var(--ink);border-radius:6px;padding:8px 10px;font-size:13px}}
#minimap{{position:absolute;bottom:10px;inset-inline-end:10px;width:170px;height:170px;border:2px solid var(--sunk);border-radius:8px;cursor:crosshair;background:var(--sunk)}}
#stick{{position:absolute;bottom:14px;inset-inline-start:14px;width:120px;height:120px;border-radius:50%;background:color-mix(in srgb,var(--tc-plate) 35%,transparent);border:2px solid color-mix(in srgb,var(--tc-ink) 50%,transparent);touch-action:none}}
#stick i{{position:absolute;left:50%;top:50%;width:46px;height:46px;margin:-23px;border-radius:50%;background:color-mix(in srgb,var(--tc-ink) 75%,transparent)}}
#stage[data-mode="overview"] #stick{{display:none}}
#panel{{position:absolute;top:66px;inset-inline-end:10px;width:min(360px,calc(100% - 20px));max-height:calc(100% - 256px);overflow:auto;padding:10px 14px;border-color:var(--mark)}}
#panel-close{{float:inline-end;background:none;border:1px solid var(--rule);color:var(--ink);border-radius:5px;cursor:pointer;min-width:36px;min-height:36px}}
#toast{{position:absolute;bottom:150px;left:50%;transform:translateX(-50%);background:var(--mark);color:var(--mark-ink);border-radius:6px;padding:8px 14px;font-weight:600;max-width:90%}}
.help{{color:var(--muted);font-size:14px}}
kbd{{font:12px "IBM Plex Mono",monospace;border:1px solid var(--rule);border-radius:4px;padding:1px 5px;background:var(--sunk)}}
.world h2{{font:700 28px/1.1 "Barlow Condensed",system-ui,sans-serif;margin:22px 0 4px}}
.evokes{{color:var(--muted)}}
.figs{{display:flex;flex-wrap:wrap;gap:10px;margin:10px 0}}
.fig{{background:var(--panel);border:1px solid var(--rule);border-radius:8px;padding:8px 14px}}
.fig b{{display:block;font:600 22px/1.2 "Barlow Condensed",system-ui,sans-serif;color:var(--mark)}}
.fig span{{color:var(--muted);font-size:13px}}
.sites{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}}
.site{{background:var(--panel);border:1px solid var(--rule);border-radius:8px;padding:10px 14px}}
.site h3{{font:600 19px/1.2 "Barlow Condensed",system-ui,sans-serif;margin:0 0 4px}}
.prov{{font:600 11px/1 "IBM Plex Mono",monospace;background:var(--sunk);color:var(--muted);border-radius:4px;padding:3px 6px;vertical-align:middle}}
.k{{margin:8px 0 2px;color:var(--muted);font-size:13px;text-transform:uppercase;letter-spacing:.05em}}
.links{{margin:0;padding-inline-start:18px}}
.none{{color:var(--muted);font-style:italic;margin:2px 0}}
.riddles{{color:var(--muted)}}
.honesty{{background:var(--sunk);border-inline-start:3px solid var(--mark);border-radius:6px;padding:12px 26px;color:var(--muted);font-size:14px}}
.quests{{padding-inline-start:18px}}
.hint{{color:var(--muted);font-size:14px}}
footer{{margin-top:24px;color:var(--muted);font-size:14px;border-top:1px solid var(--rule);padding-top:12px}}
code{{font:13px "IBM Plex Mono",monospace;color:var(--steel)}}
@media(max-width:720px){{
  header h1{{font-size:26px}}
  #minimap{{width:110px;height:110px}}
  .ctl{{max-width:calc(100% - 20px)}}
  #stick{{width:100px;height:100px}}
  #panel{{top:auto;bottom:10px;max-height:45%}}
}}
</style>
<style>{NAV_CSS}</style>
<style data-tc-theme="canvas">{THEME_CSS}</style>
{QUEST_CSS_BLOCK}
{TASK_CSS_BLOCK}
</head>
<body class="tc-theme-canvas">
{NAV}<div class="wrap">
<header>
  <h1>SmartCiti<span class="x">.X</span> : Trade Craft Academy</h1>
  <p>powered by AGI Corp · {TS("wilds.lede")}</p>
</header>
<p class="intro" lang="en" dir="ltr">Walk <b data-fig="worlds">{c["worlds"]}</b> authored worlds, <b data-fig="area">{c["area_km2"]}</b> km² in all, with <b data-fig="sites">{c["sites"]}</b> trade work sites tied to <b data-fig="halls">{c["halls_linked"]}</b> union halls and <b data-fig="lessons">{c["lessons_linked"]}</b> lessons. Every landscape is generated from a seed: an <b>authored landscape, not a survey</b>.</p>
<div id="switch" role="group" data-i18n-aria="wilds.switch_label" aria-label="{TA("wilds.switch_label")}">{switch}</div>
<div id="stage" data-mode="walk">
  <canvas id="view" tabindex="0" aria-label="{TA("wilds.canvas_label")}" data-i18n-aria="wilds.canvas_label"></canvas>
  <div id="labels"></div>
  <div class="ctl"><span class="where" id="where"></span><button type="button" class="tc-btn tc-btn-ghost" id="mode" aria-pressed="false">{TS("wilds.mode.overview")}</button><button type="button" class="tc-btn tc-btn-ghost" id="speed">{TS("wilds.pace")}: {TS("wilds.pace.walk")}</button><button type="button" class="tc-btn tc-btn-ghost" id="fly" aria-pressed="false">{TS("wilds.flyover")}</button><span class="where" id="hud-alt"></span></div>
  <canvas id="minimap" width="170" height="170" data-i18n-aria="wilds.minimap_label" aria-label="{TA("wilds.minimap_label")}"></canvas>
  <div id="stick" aria-hidden="true"><i></i></div>
  <aside id="panel" class="tc-panel" hidden aria-live="polite"><button type="button" id="panel-close" data-i18n-aria="wilds.close" aria-label="{TA("wilds.close")}">×</button><div id="panel-body"></div></aside>
  <div id="toast" hidden role="status"></div>
</div>
<p class="help">{TS("wilds.help")}</p>
<p class="help" data-legend>{TS("wilds.legend")}</p>
{task_note}
{worlds_html}
<h2>{TS("wilds.h.quests")}</h2>
<p class="help" lang="en" dir="ltr">Caches, side quests and badges are play: they never enter a completion record and never certify anything.</p>
{quest_block}
<ul class="honesty" lang="en" dir="ltr">
<li>{esc(REG["honesty"]["landscape"])}</li>
<li>{esc(REG["honesty"]["sites"])}</li>
<li>{esc(REG["honesty"]["play"])}</li>
<li>{esc(REG["honesty"]["lessons"])}</li>
</ul>
<footer data-honesty>Authored landscape, not a survey: every world here is generated from a seed and no height is a real elevation. Registry <code>wilds/registry/wilds.json</code> · stamp <code data-stamp>{esc(REG["source_stamp"])}</code> · terrain core <code data-core-stamp>{esc(REG["core_stamp"])}</code> · embedded verbatim below.</footer>
<script type="application/json" id="wilds-registry">{embedded}</script>
<script type="application/json" id="wilds-labels">{labels_json}</script>
<script type="application/json" id="wilds-i18n">__WILDS_I18N__</script>
<script type="application/json" id="wilds-tasks">{site_task_counts}</script>
<script type="importmap">
{{"imports":{{
  "three":"./vendor/three.module.min.js",
  "three/addons/":"./vendor/addons/"
}}}}
</script>
<script type="module" id="wilds-main">{JS}</script>
{QUEST_SCRIPT}
</div></body>
</html>
'''

# ------------------------------------------------ run-time i18n catalogue --
# exactly the chrome keys this page used, for every locale in i18n/locales;
# a key missing (or empty) in any locale stops the build by name
I18N_CAT = {}
for _f in sorted((ROOT / 'i18n/locales').glob('*.json')):
    _c = json.loads(_f.read_text(encoding='utf-8'))
    for _need in ('locale', 'dir', 'language', 'strings'):
        if _need not in _c:
            raise SystemExit(f'build_wilds: {_f.name} has no {_need!r}')
    if _c['dir'] not in ('ltr', 'rtl'):
        raise SystemExit(f'build_wilds: {_f.name} dir {_c["dir"]!r} is not ltr/rtl')
    _s = {}
    for _k in sorted(_USED):
        if _k not in _c['strings'] or not isinstance(_c['strings'][_k], str) or not _c['strings'][_k].strip():
            raise SystemExit(f'build_wilds: locale {_c["locale"]} has no wilds chrome key {_k!r}')
        _s[_k] = _c['strings'][_k]
    I18N_CAT[_c['locale']] = {'dir': _c['dir'], 'language': _c['language'], 'strings': _s}
if len(I18N_CAT) != 8 or 'en' not in I18N_CAT or not any(v['dir'] == 'rtl' for v in I18N_CAT.values()):
    raise SystemExit(f'build_wilds: expected 8 locales incl. en and an rtl one, found {sorted(I18N_CAT)}')
if page.count('__WILDS_I18N__') != 1:
    raise SystemExit('build_wilds: the i18n catalogue placeholder must appear exactly once')
page = page.replace('__WILDS_I18N__', json.dumps(I18N_CAT, ensure_ascii=False, sort_keys=True).replace('</', '<\\/'))

# search and link-preview head tags (web/seo.py): head region only
page = apply_seo(page, PAGE, 'The wilds \u2014 SmartCiti.X : Trade Craft Academy',
                 f'Walk {c["worlds"]} authored exterior worlds, {c["area_km2"]} km\u00b2 in all, with trade work sites '
                 'tied to union halls and lessons. Authored landscapes, not surveys.', 'page')
out = HERE / 'trade_craft_wilds.html'
emit(out, page, f'{c["worlds"]} worlds | {c["sites"]} sites | quests {QUEST_STATE} | tasks {TASK_STATE} | nav wired')
