#!/usr/bin/env python3
"""The parishes page: a large walkable world of New Orleans parishes.

Rendered from parishes/registry/parishes.json (PARISH owns it) through ONE
adapter, `normalise()`, that reads only the fields the PARISH contract names
and stops the build by name when one is missing. Until that registry exists
the page is built from STUB, a placeholder of the same shape whose outlines
are squares and whose names say "Stub": it is labelled STUB everywhere and is
never presented as a parish.

How it is drawn (the wilds doctrine, web/build_wilds.py, at true metre scale):
  - ground is FLAT AUTHORED ground at 0 m inside each parish outline and water
    outside it: New Orleans elevation is not held here, so there is no real
    elevation and the page says so;
  - one land mesh per LOADED parish; the parish you stand in plus every
    neighbour whose shared border is within STREAM_M of you. Walking or
    driving over a border streams the neighbour in, and a border marker names
    both parishes;
  - the AUTHORED fabric (blocks, trees) streams in CHUNK_M chunks around the
    eye, scattered by the wilds core's own hash (wilds/core.mjs, carried
    byte-for-byte), and each family is ONE InstancedMesh: one draw call;
  - landmarks are generic procedural assets (a bell tower silhouette, not a
    replica), one InstancedMesh per asset family, with the registry's
    provenance note on hover or focus.
Satellite imagery is a VIEW-TIME layer in the learner's browser only (USGS
orthoimagery as declared in parcels/registry; Mapbox only with an operator
token supplied at deploy time). Nothing fetched is stored or baked.
"""
import html
import json
import math
import re
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402
import sitenav  # noqa: E402
from sitenav import nav_html, labels as nav_labels, NAV_CSS, STYLE_JS  # noqa: E402
from design_kit import STYLE_HEAD_JS  # noqa: E402
from seo import apply_seo  # noqa: E402
from pagehero import theme  # noqa: E402
THEME_CSS, THEME_JS = theme('canvas')
if THEME_JS:
    raise SystemExit('build_parishes: the canvas theme is CSS only; pagehero.theme("canvas") returned script')

PAGE = 'web/trade_craft_parishes.html'
CORE_SRC = (ROOT / 'wilds/core.mjs').read_text()
B, E = '/* WILDS_CORE:BEGIN */', '/* WILDS_CORE:END */'
if CORE_SRC.count(B) != 1 or CORE_SRC.count(E) != 1:
    raise SystemExit('build_parishes: wilds/core.mjs must hold exactly one WILDS_CORE block')
CORE = CORE_SRC[CORE_SRC.index(B):CORE_SRC.index(E) + len(E)]


def esc(s):
    return html.escape(str(s), quote=True)


class BuildError(SystemExit):
    pass


def need(d, k, where):
    """fail closed: a missing field stops the build, named"""
    if not isinstance(d, dict) or k not in d:
        raise BuildError(f'build_parishes: {where} has no field {k!r}')
    return d[k]


# ------------------------------------------------------------------ i18n --
_CAT = json.loads((ROOT / 'i18n/locales/en.json').read_text(encoding='utf-8'))['strings']
_USED = set()


def T(k):
    if k not in _CAT or not isinstance(_CAT[k], str) or not _CAT[k].strip():
        raise BuildError(f'build_parishes: i18n/locales/en.json has no parishes chrome key {k!r}')
    return html.escape(_CAT[k], quote=True)


def TS(k):
    _USED.add(k)
    return f'<span data-i18n="{k}">{T(k)}</span>'


def TA(k):
    _USED.add(k)
    return T(k)


# ------------------------------------------------------------------- nav --
# the site nav, declared once in web/sitenav.py (Play group, nav.page.parishes);
# no fallback: an undeclared page stops the build (nav_html asserts)
if PAGE not in sitenav.PAGES:
    raise BuildError(f'build_parishes: web/sitenav.py does not declare {PAGE} (NEEDS nav: lead)')
NAV = nav_html(PAGE, nav_labels('en'))

# --------------------------------------------------------------- parishes --
REG_PATH = ROOT / 'parishes/registry/parishes.json'
if not REG_PATH.exists():
    raise BuildError('build_parishes: parishes/registry/parishes.json is not built (python3 parishes/build.py)')
REG = json.loads(REG_PATH.read_text())

# asset family per registry kind (generic silhouettes; the first matching word wins)
FAMILY_OF = [('bridge', 'bridge'), ('stadium', 'dome'), ('government', 'hall'), ('university', 'hall'),
             ('research', 'hall'), ('airport', 'hall'), ('port', 'hall'), ('square', 'tower'), ('fort', 'tower'),
             ('battlefield', 'tower'), ('park', 'other'), ('refuge', 'other'), ('flood', 'other')]


def family(kind):
    for word, fam in FAMILY_OF:
        if word in kind:
            return fam
    raise BuildError(f'build_parishes: landmark kind {kind!r} has no asset family (add it to FAMILY_OF)')


def ground_of(mp, w):
    """PARISH v1.3 label-free ground tiles: 4x4 tiles whose union is map.extent_local_m (row 0 north, col 0 west)."""
    gt = need(mp, 'ground_tiles', w + '.map')
    grid = need(gt, 'grid', w + '.map.ground_tiles')
    tiles = need(gt, 'tiles', w + '.map.ground_tiles')
    if len(tiles) != grid * grid:
        raise BuildError(f'build_parishes: {w}.map.ground_tiles holds {len(tiles)} tiles, not grid^2 = {grid * grid}')
    cells = sorted((need(t, 'row', w + '.ground_tiles[]'), need(t, 'col', w + '.ground_tiles[]')) for t in tiles)
    if cells != [(r, c) for r in range(grid) for c in range(grid)]:
        raise BuildError(f'build_parishes: {w}.map.ground_tiles does not cover the {grid}x{grid} grid exactly once')
    return {'label': need(gt, 'label', w + '.map.ground_tiles'), 'grid': grid,
            'tiles': [[need(t, 'path', w + '.ground_tiles[]'), t['row'], t['col']] for t in tiles]}


def normalise(reg):
    """The one place the PARISH contract ($SP/PARISH_CONTRACT.md v1) is read.
    Output: the shape the page script uses, in the contract's WORLD frame
    (scene x = east_m, z = -north_m). Every field is required; nothing is
    defaulted. Outlines are laid into the world frame with the contract's own
    ltp formula so shared borders coincide."""
    frames = need(reg, 'frames', 'registry')
    R = need(frames, 'R_m', 'registry.frames')
    wo = need(need(frames, 'world', 'registry.frames'), 'origin', 'registry.frames.world')
    lat0, lng0 = need(wo, 'lat', 'frames.world.origin'), need(wo, 'lng', 'frames.world.origin')
    k_e, k_n = R * math.cos(math.radians(lat0)) * math.pi / 180, R * math.pi / 180

    def xz(lng, lat):
        return [round(k_e * (lng - lng0), 2), round(-k_n * (lat - lat0), 2)]

    sel = need(need(reg, 'selection', 'registry'), 'selected', 'registry.selection')
    P = need(reg, 'parishes', 'registry')
    out = {'region': {'lat0': lat0, 'lon0': lng0, 'm_per_deg_lat': k_n, 'm_per_deg_lon': k_e,
                      'provenance': need(frames, 'ltp_formula', 'registry.frames')}, 'parishes': []}
    for fips in sel:
        p = need(P, fips, 'registry.parishes')
        w = f'parishes[{fips}]'
        outline = need(p, 'outline', w)
        rings = [[xz(lng, lat) for lng, lat in ring] for poly in need(outline, 'polygons', w + '.outline') for ring in poly]
        if not rings or any(len(r) < 3 for r in rings):
            raise BuildError(f'build_parishes: {w} has an outline ring with fewer than 3 points')
        fr = need(p, 'frame', w)
        ox, on = need(fr, 'origin_in_world_m', w + '.frame')
        mp = need(p, 'map', w)
        ext = need(mp, 'extent_local_m', w + '.map')
        lms = []
        for j, lm in enumerate(need(p, 'landmarks', w)):
            e, n = need(lm, 'world_m', f'{w}.landmarks[{j}]')
            lms.append({'id': f'{fips}-lm{j}', 'name': need(lm, 'name', f'{w}.landmarks[{j}]'), 'kind': need(lm, 'kind', f'{w}.landmarks[{j}]'),
                        'family': family(lm['kind']), 'x': e, 'z': -n,
                        'provenance': need(lm, 'provenance', f'{w}.landmarks[{j}]'), 'note': need(lm, 'note', f'{w}.landmarks[{j}]')})
        for j, an in enumerate(need(p, 'anchors', w)):
            e, n = need(an, 'world_m', f'{w}.anchors[{j}]')
            lms.append({'id': f'{fips}-an{j}', 'name': need(an, 'name', f'{w}.anchors[{j}]'), 'kind': need(an, 'kind', f'{w}.anchors[{j}]'),
                        'family': family(an['kind']), 'x': e, 'z': -n,
                        'provenance': need(an, 'provenance', f'{w}.anchors[{j}]'), 'note': need(an, 'source', f'{w}.anchors[{j}]')})
        nbs = []
        for j, bd in enumerate(need(p, 'borders', w)):
            segs = [[[e, -n] for e, n in need(sg, 'world_m', f'{w}.borders[{j}]')] for sg in need(bd, 'segments', f'{w}.borders[{j}]')]
            if not segs or any(len(sg) < 2 for sg in segs):
                raise BuildError(f'build_parishes: border {fips}|{bd["with"]} has a segment with fewer than 2 points')
            nbs.append({'id': need(bd, 'with', f'{w}.borders[{j}]'), 'segments': segs})
        out['parishes'].append({
            'id': fips, 'fips': fips, 'name': need(p, 'full_name', w), 'rings_m': rings, 'origin_m': [ox, -on],
            'map_preview': need(mp, 'preview', w + '.map'), 'map_4k': need(mp, 'path', w + '.map'),
            'map_label': need(mp, 'label', w + '.map'), 'map_fabric': need(mp, 'fabric', w + '.map'),
            'map_world': [ox + ext['left'], -(on + ext['top']), ox + ext['right'], -(on + ext['bottom'])],
            'ground': ground_of(mp, w),
            'landmarks': lms, 'neighbours': nbs, 'area_km2': need(p, 'area_km2', w)})
    ids = {p['id'] for p in out['parishes']}
    for p in out['parishes']:
        for n in p['neighbours']:
            if n['id'] not in ids:
                raise BuildError(f'build_parishes: {p["id"]} names neighbour {n["id"]!r}, not selected')
    if not out['parishes']:
        raise BuildError('build_parishes: the registry selects no parish')
    sat = need(reg, 'satellite', 'registry')
    if need(sat, 'fetched_at_build', 'registry.satellite') is not False or need(sat, 'stored', 'registry.satellite') is not False:
        raise BuildError('build_parishes: registry.satellite must say fetched_at_build false and stored false')
    usgs, mb = need(sat, 'usgs', 'registry.satellite'), need(sat, 'mapbox', 'registry.satellite')
    out['satellite'] = {'usgs': {k: need(usgs, k, 'satellite.usgs') for k in ('tiles', 'attribution', 'when_unavailable')},
                        'mapbox': {k: need(mb, k, 'satellite.mapbox') for k in ('tiles', 'attribution', 'refusal_text')},
                        'rule': need(sat, 'rule', 'registry.satellite')}
    out['honesty'] = {'outline': need(need(reg, 'provenance', 'registry'), 'outline', 'registry.provenance'),
                      'water': need(need(reg, 'water', 'registry'), 'statement', 'registry.water'),
                      'elevation': need(reg, 'elevation', 'registry'),
                      'landmarks': need(reg, 'landmarks_method', 'registry'),
                      'satellite': out['satellite']['rule']}
    labels = {p['ground']['label'] for p in out['parishes']}
    if len(labels) != 1:
        raise BuildError(f'build_parishes: parishes carry {len(labels)} different ground_tiles labels; the page shows one')
    out['honesty']['ground'] = labels.pop()
    out['source_stamp'] = need(reg, 'source_stamp', 'registry')
    return out


DATA = normalise(REG)
PARISH_STATE = 'wired'
if DATA['satellite']['mapbox']['refusal_text'] != 'Mapbox satellite: off - no token configured':
    raise BuildError('build_parishes: the Mapbox refusal text is not the contract text')

# ------------------------------------------------------ other contracts --
# INTEGRATION POINTS: FLEET (vehicles), NPC (guides), LAYERS (paths and
# stations). Each is read only when its registry exists; until then the page
# runs a named stub and says which contract is missing.
CONTRACTS = {
    'fleet': ('fleet/registry/fleet.json', 'FLEET_CONTRACT'),
    'npcs': ('npcs/registry/npcs.json', 'NPC_CONTRACT'),
    'layers': ('layers/registry/layers.json', 'LAYERS_CONTRACT'),
}
STATES, WHY = {}, {}
# FLEET: fleet/registry/fleet.json embedded verbatim, driven by web/fleetkit.py (FLEET_CONTRACT v1)
if (ROOT / 'fleet/registry/fleet.json').exists():
    from fleetkit import fleet_inline  # noqa: E402
    FLEET_REG = json.loads((ROOT / 'fleet/registry/fleet.json').read_text())
    for _k in ('families', 'fleet', 'honesty', 'counts'):
        need(FLEET_REG, _k, 'fleet/registry/fleet.json')
    FLEET_INLINE = fleet_inline()
    STATES['fleet'] = 'wired'
else:
    FLEET_REG, FLEET_INLINE = None, ''
    STATES['fleet'], WHY['fleet'] = 'stub', 'fleet/registry/fleet.json is not built'
# NPC: the registry's places are STUB (no coordinates) until parishes + layers both land in npcs/build.py
if (ROOT / 'npcs/registry/npcs.json').exists():
    _npc = json.loads((ROOT / 'npcs/registry/npcs.json').read_text())
    if need(_npc, 'places_status', 'npcs/registry/npcs.json') == 'PARISH+LAYERS':
        from npckit import NPC_JS_INLINE, NPC_CSS, npc_data  # noqa: E402
        NPC_DATA = {'npcs': [], 'places': {}, 'honesty': None}
        for _p in DATA['parishes']:
            _d = npc_data(_p['id'])
            # npckit renders honesty.scripted in the dialogue footer: pass the whole object, scripted required
            NPC_DATA['honesty'] = need(_d, 'honesty', 'npc_data')
            need(NPC_DATA['honesty'], 'scripted', 'npc_data.honesty')
            for _pid, _pl in need(_d, 'places', 'npc_data').items():
                _e, _n = need(_pl, 'world_m', f'npc place {_pid}')
                NPC_DATA['places'][_pid] = [_e, -_n]
            NPC_DATA['npcs'] += need(_d, 'npcs', 'npc_data')
        STATES['npcs'] = 'wired'
        NPC_CSS_BLOCK = f'<style>{NPC_CSS}</style>'
    else:
        NPC_DATA, NPC_JS_INLINE, NPC_CSS_BLOCK = None, '', ''
        STATES['npcs'], WHY['npcs'] = 'stub', f'npcs/registry places_status is {_npc["places_status"]}: NPC homes carry no coordinates yet'
else:
    NPC_DATA, NPC_JS_INLINE, NPC_CSS_BLOCK = None, '', ''
    STATES['npcs'], WHY['npcs'] = 'stub', 'npcs/registry/npcs.json is not built'
# LAYERS: web/pathkit.py path_data(fips) must resolve for every parish, or the layer stays a named stub
if (ROOT / 'layers/registry/layers.json').exists() and (HERE / 'pathkit.py').exists():
    # fail closed: a parish pathkit cannot resolve stops the build by name
    import pathkit  # noqa: E402
    PATHS = {}
    for _p in DATA['parishes']:
        _d = pathkit.path_data(_p['id'])
        for _st in need(_d, 'stations', f'pathkit.path_data({_p["id"]})'):
            for _k in ('id', 'layer', 'title', 'world_m', 'treasure', 'provenance'):
                need(_st, _k, f'layers station {_st.get("id")}')
        PATHS[_p['id']] = _d
    STATES['layers'] = 'wired'
    PATH_CSS_BLOCK, PATH_SCRIPT = f'<style>{pathkit.PATH_CSS}</style>', f'<script>{pathkit.PATH_JS}</script>'
else:
    PATHS, PATH_CSS_BLOCK, PATH_SCRIPT = {}, '', ''
    STATES['layers'], WHY['layers'] = 'stub', 'layers/registry/layers.json is not built'


# ----------------------------------------------------------------- quests --
QUEST_SCRIPT, QUEST_CSS_BLOCK, QUEST_STATE, QUEST_ROWS = '', '', 'pending', []
qreg_path = ROOT / 'quests/registry/quests.json'
if qreg_path.exists() and (HERE / 'questkit.py').exists():
    _allq = json.loads(qreg_path.read_text())['quests']
    QIDS = {q['id'] for q in _allq}
    pq = [q for q in _allq if q['world'].startswith('parish:')]
    if pq:
        from questkit import QUEST_CSS, quest_js, egg_attr, quest_attr  # noqa: E402
        pids = {p['id'] for p in DATA['parishes']}
        for q in pq:
            pid = q['world'].split(':', 1)[1]
            if pid not in pids:
                raise BuildError(f'build_parishes: quest {q["id"]} names parish {pid!r}, not in the parish registry')
            # finds the world fires by play (arrive, landmark, guide, station) get no click-to-find button
            if re.match(r'treasure-(parish-\d+-(arrive|lm-.+)|guide-\d+|station-.+)$', q['id']):
                continue
            attr = egg_attr(q['id']) if q['kind'] in ('treasure', 'egg') else quest_attr(q['id'])
            QUEST_ROWS.append(f'<li><button type="button" class="tc-btn tc-btn-ghost" data-parish="{esc(pid)}" {attr}>'
                              f'{esc(q["title"])}</button> <span class="help">{esc(q["hint"])}</span></li>')
        QUEST_SCRIPT = quest_js('parishes')
        QUEST_CSS_BLOCK = f'<style>{QUEST_CSS}</style>'
        QUEST_STATE = 'wired'

# the quest finds the world triggers (LAYERS_CONTRACT): only ids the quest
# registry holds are wired; every landmark treasure must name a landmark here
def slug(name):
    return '-'.join(''.join(c.lower() if c.isalnum() else ' ' for c in name).split())


FINDS = {'arrive': {}, 'border': {}, 'landmark': {}, 'ride': {}}
if QUEST_STATE == 'wired':
    for p in DATA['parishes']:
        k = f'treasure-parish-{p["id"]}-arrive'
        if k in QIDS:
            FINDS['arrive'][p['id']] = k
        for lm in p['landmarks']:
            k = f'treasure-parish-{p["id"]}-lm-{slug(lm["name"])}'
            if k in QIDS:
                FINDS['landmark'][lm['id']] = k
        for n in p['neighbours']:
            a, b = sorted((p['id'], n['id']))
            k = f'treasure-border-{a}-{b}'
            if k in QIDS:
                FINDS['border'][f'{a}|{b}'] = k
    for m in ('land', 'water'):
        if f'treasure-ride-{m}' in QIDS:
            FINDS['ride'][m] = f'treasure-ride-{m}'
    _lmq = {q for q in QIDS if q.startswith('treasure-parish-') and '-lm-' in q}
    _orph = sorted(_lmq - set(FINDS['landmark'].values()))
    if _orph:
        raise BuildError(f'build_parishes: landmark treasures with no landmark in the parish registry: {_orph}')

# ------------------------------------------------------------------- html --
n_par = len(DATA['parishes'])
n_lm = sum(len(p['landmarks']) for p in DATA['parishes'])
n_border = sum(len(p['neighbours']) for p in DATA['parishes']) // 2
stub_banner = ''
pending_rows = ''.join(
    f'<li data-contract="{k}" data-state="{STATES[k]}"><b>{esc(k)}</b>: '
    + (f'{TS("parishes.wired")} <code>{esc(CONTRACTS[k][0])}</code>' if STATES[k] == 'wired'
       else f'{TS("parishes.missing")} <code>{esc(CONTRACTS[k][1])}</code> <span class="help" data-why>{esc(WHY[k])}</span>') + '</li>'
    for k in CONTRACTS)
lm_rows = ''.join(
    f'<li data-landmark="{esc(lm["id"])}"><b>{esc(lm["name"])}</b> <span class="prov tc-badge tc-badge-muted">{esc(lm["provenance"])}</span> '
    f'<span class="help">{esc(lm["note"])}</span> <span class="help">({esc(p["name"])})</span></li>'
    for p in DATA['parishes'] for lm in p['landmarks'])
quest_block = (f'<ul class="quests">{"".join(QUEST_ROWS)}</ul><div data-tc-questlog></div>' if QUEST_STATE == 'wired'
               else f'<p class="none" data-quests-pending>{TS("parishes.quests_pending")}</p>')
honesty_rows = ''.join(f'<li data-honesty-key="{esc(k)}">{esc(v)}</li>' for k, v in sorted(DATA['honesty'].items()))
embedded = json.dumps(DATA, sort_keys=True, ensure_ascii=False).replace('</', '<\\/')
finds_embedded = json.dumps(FINDS, sort_keys=True)
npcs_embedded = json.dumps(NPC_DATA, sort_keys=True, ensure_ascii=False).replace('</', '<\\/')
# pathkit's labels in every locale (pathkit.path_labels, QUESTS-owned path.* keys; fails closed)
PATH_LABELS_BY_LOC = {}
if PATHS:
    for _f in sorted((ROOT / 'i18n/locales').glob('*.json')):
        _c = json.loads(_f.read_text(encoding='utf-8'))
        PATH_LABELS_BY_LOC[_c['locale']] = pathkit.path_labels(_c['strings'])
pathlabels_embedded = json.dumps(PATH_LABELS_BY_LOC, sort_keys=True, ensure_ascii=False).replace('</', '<\\/')
paths_embedded = json.dumps(PATHS, sort_keys=True, ensure_ascii=False).replace('</', '<\\/')
fleet_embedded = json.dumps(FLEET_REG, sort_keys=True, ensure_ascii=False).replace('</', '<\\/') if FLEET_REG else 'null'
FLEET_HONESTY = esc(FLEET_REG['honesty']) if FLEET_REG else ''
JS_KEYS = ['parishes.mode.walk', 'parishes.mode.drive', 'parishes.mode.boat', 'parishes.mode.overview',
           'parishes.border', 'parishes.ground', 'parishes.sat.usgs', 'parishes.sat.failed',
           'parishes.boat.nowater', 'parishes.boat.noland', 'parishes.stub_vehicle']
# the NPC kit's own dialogue keys (npc.*, NPC-owned, all 8 locales) travel in this page's run-time catalogue
if NPC_DATA is not None:
    from npckit import NPC_I18N_KEYS  # noqa: E402
    JS_KEYS += list(NPC_I18N_KEYS)
_USED.update(JS_KEYS)

JS = r'''
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
''' + CORE + '\n' + FLEET_INLINE + '\n' + NPC_JS_INLINE + r'''
const D = JSON.parse(document.getElementById('parishes-data').textContent);
const I18N = JSON.parse(document.getElementById('parishes-i18n').textContent);
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
  if (typeof s !== 'string') throw new Error(`parishes i18n: locale ${LOC} has no ${k}`);
  return s;
}
document.documentElement.lang = LOC;
document.documentElement.dir = I18N[LOC].dir;
for (const el of document.querySelectorAll('[data-i18n]')) el.textContent = tr(el.dataset.i18n);
for (const el of document.querySelectorAll('[data-i18n-aria]')) el.setAttribute('aria-label', tr(el.dataset.i18nAria));

/* Declared once; web/eval_parishes.mjs holds the views to targets. */
const CHUNK_M = 250, RADIUS = 3, CELL = 25, BUILD_PER_FRAME = 3;
const STREAM_M = 1500;                 // a neighbour streams in when its shared border is this close
const CAP = { block: 6000, tree: 4000, lamp: 2500, marker: 64, lm: 64 };
const PACE = { walk: 1.6, run: 6, drive: 14, boat: 8 };   // m/s, AUTHORED
const EYE = { walk: 1.7, drive: 1.4, boat: 1.2, overview: 0 };
const SEED = 20260928;

const stage = document.getElementById('stage');
const canvas = document.getElementById('view');
/* alpha: the sky is the canvas's CSS gradient (#view), so the sky costs no draw call (wave 6) */
const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: true, powerPreference: 'high-performance' });
const BASE_PR = Math.min(window.devicePixelRatio, 1.25);
/* OVERVIEW_PR: the overview renders at 0.6 of the walk resolution. DIAG (scale 1 vs 0.6, Orleans overview median):
   5b 33.3 vs 33.3 ms; wave 6 run 1 49.9 vs 50.0 ms; wave 6 run 2 (with the draped ground texture) 49.9 vs 33.3 ms.
   Scale 1 WAS slower once the ground is textured, so 0.6 stays (declared in web/eval_parishes.mjs). */
const OVERVIEW_PR = 0.6;
let prScale = 1;
function applyPR(k) { prScale = k; renderer.setPixelRatio(BASE_PR * k); resize(); }
renderer.setPixelRatio(BASE_PR);
const scene = new THREE.Scene();
/* atmosphere (wave 6, AUTHORED): the sky gradient is CSS behind a transparent canvas (no draw call); the fog is the
   gradient's horizon colour, so far ground melts into the sky; the overview keeps its water-coloured clear */
const HORIZON = 0xD3DFE3;
const SKY_BG = null, WATER_BG = new THREE.Color(0x3E6E8E);
renderer.setClearColor(HORIZON, 0);
const SKY = [[0x6E9BC3, 0], [0x9DBDD6, 30], [0xC4D6E0, 46], [HORIZON, 52], [HORIZON, 100]];   // zenith -> horizon, % of the view height
canvas.style.backgroundImage = 'linear-gradient(180deg,' + SKY.map(([c, p]) => '#' + c.toString(16).padStart(6, '0') + ' ' + p + '%').join(',') + ')';
scene.background = SKY_BG;
scene.fog = new THREE.Fog(HORIZON, 700, 4200);
const camera = new THREE.PerspectiveCamera(62, 1, 0.3, 60000);
scene.add(new THREE.HemisphereLight(0xdde9f7, 0x5a5040, 0.95));
/* sun direction: an AUTHORED mid-afternoon sun from the south-west, low enough that facades read as planes */
const SUN = new THREE.Vector3(-0.55, 0.62, 0.56).normalize();
const sun = new THREE.DirectionalLight(0xfff0d6, 1.75); sun.position.copy(SUN); scene.add(sun);
const lam = (c) => new THREE.MeshLambertMaterial({ color: c });
const matWater = new THREE.MeshLambertMaterial({ color: 0x3E6E8E, emissive: 0x9FC4DC, emissiveIntensity: 0.06 }), matBlock = lam(0xB9AE9C), matTree = new THREE.MeshLambertMaterial({ color: 0x3F6B3A, side: THREE.DoubleSide }), matMark = lam(0xE8A33D), matLm = lam(0xD8D2C4);
const LAND = [0xA7B58C, 0x9FB08F, 0xB1B790, 0x98A987];

const PAR = new Map(D.parishes.map((p, i) => {
  let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
  for (const r of p.rings_m) for (const [x, z] of r) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); z0 = Math.min(z0, z); z1 = Math.max(z1, z); }
  return [p.id, Object.assign({}, p, { idx: i, bbox: [x0, z0, x1, z1] })];
}));
function inRing(r, x, z) {
  let c = false;
  for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
    const [xi, zi] = r[i], [xj, zj] = r[j];
    if ((zi > z) !== (zj > z) && x < (xj - xi) * (z - zi) / (zj - zi) + xi) c = !c;
  }
  return c;
}
function inParish(p, x, z) {
  const b = p.bbox; if (x < b[0] || x > b[2] || z < b[1] || z > b[3]) return false;
  let c = false; for (const r of p.rings_m) if (inRing(r, x, z)) c = !c; return c;
}
/* land or water: the ground under a point is the parish that holds it, or water */
function parishAt(x, z) { for (const p of PAR.values()) if (inParish(p, x, z)) return p; return null; }
function segDist(px, pz, [ax, az], [bx, bz]) {
  const dx = bx - ax, dz = bz - az, L = dx * dx + dz * dz;
  const t = L ? Math.max(0, Math.min(1, ((px - ax) * dx + (pz - az) * dz) / L)) : 0;
  return Math.hypot(px - ax - t * dx, pz - az - t * dz);
}
function longest(segs) { let b = segs[0], bl = -1; for (const sg of segs) { let l = 0; for (let i = 1; i < sg.length; i++) l += Math.hypot(sg[i][0] - sg[i - 1][0], sg[i][1] - sg[i - 1][1]); if (l > bl) { bl = l; b = sg; } } return b; }
function lineDist(x, z, pts) { let d = Infinity; for (let i = 1; i < pts.length; i++) d = Math.min(d, segDist(x, z, pts[i - 1], pts[i])); return d; }

/* ---- ground (wave 6): the AUTHORED street grid that buildChunk leaves open (every 4th 25 m cell) is painted on
   the flat land in the fragment shader - carriageway, walkways and a dashed centre line - at no extra draw call or
   triangle; it fades out with distance so the overview does not shimmer. NOT the real street grid. ---- */
const STREET_GLSL = `
{ vec2 q = mod(vGroundXZ, 100.0);
  float road = max(step(5.0, q.x) * step(q.x, 20.0), step(5.0, q.y) * step(q.y, 20.0));
  float walk = max(step(1.5, q.x) * step(q.x, 23.5), step(1.5, q.y) * step(q.y, 23.5)) * (1.0 - road);
  float cross = step(q.x, 25.0) * step(q.y, 25.0);
  float dash = (step(abs(q.x - 12.5), 0.15) * step(0.5, fract(vGroundXZ.y / 6.0)) + step(abs(q.y - 12.5), 0.15) * step(0.5, fract(vGroundXZ.x / 6.0))) * road * (1.0 - cross);
  float far = 1.0 - smoothstep(220.0, 420.0, vGroundDist);
  diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.70, 0.68, 0.63), walk * far);
  diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.34, 0.35, 0.36), road * far);
  diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.86, 0.82, 0.62), min(dash, 1.0) * far * (1.0 - smoothstep(120.0, 260.0, vGroundDist))); }
`;
/* PARISH v1.3 ground tiles (label-free, the same pixels as the 4k map's ground) are draped on the flat land: the
   grid x grid tiles are drawn into ONE GROUND_PX canvas per parish, sampled by world x/z over map_world, so the
   parks, water and land use under your feet match the 4k map; the ground stays at exactly 0 m. Near the eye the
   painted AUTHORED grid (the one the buildings stand on) takes over from the tile's streets. */
const GROUND_PX = 2048;
function groundTexture(p, onReady) {
  const cv = document.createElement('canvas'); cv.width = cv.height = GROUND_PX;
  const cx = cv.getContext('2d'), g = p.ground, cell = GROUND_PX / g.grid; let left = g.tiles.length;
  const tex = new THREE.CanvasTexture(cv); tex.flipY = false; tex.colorSpace = THREE.SRGBColorSpace;   // no anisotropy: SwiftShader pays per tap (w6 run 1: walk frames rose)
  for (const [src, row, col] of g.tiles) {
    const im = new Image();
    im.onload = () => { cx.drawImage(im, col * cell, row * cell, cell, cell); if (--left === 0) { tex.needsUpdate = true; onReady(); } };
    im.onerror = () => { groundFailed.push(src); };
    im.src = '../' + src;
  }
  return tex;
}
const groundFailed = [], groundReady = new Set();
function streetMat(c, p) {
  const m = lam(c);
  const u = { uGround: { value: groundTexture(p, () => { u.uOn.value = 1; groundReady.add(p.id); }) }, uOn: { value: 0 },
    uBox: { value: new THREE.Vector4(p.map_world[0], p.map_world[1], p.map_world[2] - p.map_world[0], p.map_world[3] - p.map_world[1]) } };
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, u);
    sh.vertexShader = 'varying vec2 vGroundXZ; varying float vGroundDist;\n' + sh.vertexShader.replace('#include <project_vertex>', '#include <project_vertex>\n  vGroundXZ = position.xz; vGroundDist = -mvPosition.z;');
    sh.fragmentShader = 'uniform sampler2D uGround; uniform float uOn; uniform vec4 uBox; varying vec2 vGroundXZ; varying float vGroundDist;\n' + sh.fragmentShader.replace('#include <color_fragment>', '#include <color_fragment>\n' +
      '{ vec2 guv = (vGroundXZ - uBox.xy) / uBox.zw; diffuseColor.rgb = mix(diffuseColor.rgb, texture2D(uGround, guv).rgb, uOn); }\n' + STREET_GLSL);
  };
  m.customProgramCacheKey = () => 'parish-ground';
  return m;
}

/* ---- parish streaming: land meshes (flat, 0 m) for the loaded parishes ---- */
const landMesh = new Map();
function makeLand(p) {
  const shapes = p.rings_m.map((r) => new THREE.Shape(r.map(([x, z]) => new THREE.Vector2(x, -z))));
  const g = new THREE.ShapeGeometry(shapes); g.rotateX(-Math.PI / 2);
  // flat AUTHORED ground: exactly 0 m (the rotation leaves ~1e-13 m of float noise)
  const pa = g.attributes.position.array; for (let i = 1; i < pa.length; i += 3) pa[i] = 0;
  const m = new THREE.Mesh(g, streetMat(LAND[p.idx % LAND.length], p)); m.userData.parish = p.id; return m;
}
let current = null;
const loaded = new Set();
function wantedParishes(x, z) {
  const want = new Set();
  const here = parishAt(x, z) || current;
  if (here) {
    want.add(here.id);
    for (const n of here.neighbours) if (n.segments.some((sg) => lineDist(x, z, sg) < STREAM_M)) want.add(n.id);
  }
  return want;
}
function streamParishes(x, z) {
  const want = wantedParishes(x, z);
  let changed = false;
  for (const id of want) if (!loaded.has(id)) {
    if (!landMesh.has(id)) landMesh.set(id, makeLand(PAR.get(id)));
    scene.add(landMesh.get(id)); loaded.add(id); changed = true;
  }
  for (const id of [...loaded]) if (!want.has(id)) { scene.remove(landMesh.get(id)); loaded.delete(id); changed = true; }
  if (changed) { refillMarkers(); refillLandmarks(); refillStations(); }
}

/* ---- water: one plane that follows the eye, below the flat ground ---- */
const water = new THREE.Mesh(new THREE.PlaneGeometry(40000, 40000), matWater);
water.rotation.x = -Math.PI / 2; water.position.y = -0.4; scene.add(water);
/* water (wave 6): a grazing-angle sky reflection (Schlick-style fresnel toward the horizon colour) and a moving
   ripple on the same material - still one plane, one draw call */
const waterU = { uTime: { value: 0 } };
matWater.onBeforeCompile = (sh) => {
  sh.uniforms.uTime = waterU.uTime;
  sh.vertexShader = 'varying vec3 vWaterW;\n' + sh.vertexShader.replace('#include <project_vertex>', '#include <project_vertex>\n  vWaterW = (modelMatrix * vec4(transformed, 1.0)).xyz;');
  sh.fragmentShader = 'uniform float uTime; varying vec3 vWaterW;\n' + sh.fragmentShader.replace('#include <color_fragment>',
    '#include <color_fragment>\n{ vec3 v = normalize(cameraPosition - vWaterW); float fr = pow(1.0 - clamp(v.y, 0.0, 1.0), 4.0);\n' +
    '  float rip = 0.5 + 0.5 * sin(vWaterW.x * 0.09 + uTime * 1.3) * sin(vWaterW.z * 0.07 - uTime * 0.9);\n' +
    '  diffuseColor.rgb = mix(diffuseColor.rgb * (0.92 + 0.12 * rip), vec3(0.83, 0.87, 0.89), fr * 0.75); }');
};
matWater.customProgramCacheKey = () => 'parish-water';

/* ---- AUTHORED fabric: blocks and trees, chunk-streamed, one InstancedMesh each ---- */
/* trees: open-ended trunk (4 sides) and crown (6 sides), drawn double-sided: 14 triangles, was 32 (wave 6) -
   the caps were never seen from eye height; the saving pays for the building kit's roofs and porches */
const treeGeo = mergeGeometries([new THREE.CylinderGeometry(0.25, 0.3, 2, 4, 1, true).translate(0, 1, 0), new THREE.ConeGeometry(2.2, 6, 6, 1, true).translate(0, 5, 0)]);

/* ---- AUTHORED building kit (wave 6): two families, each ONE InstancedMesh (one draw call per family), style
   and height by an AUTHORED land-use district (DISTRICT_M squares hashed by wildsHash: residential, commercial,
   industrial, park) - generic forms only, no replica of any real building, NOT the real land use.
   house   : walls + gable roof + a front porch/gallery hint (canopy and two posts) - 24 triangles
   midrise : walls with a flat roof (blockGeo) - 10 triangles; the ground-floor band is painted. Industrial lots
             are low, wide flat-roofed shells in this same family with cladding colours (a separate shed family
             cost one more draw call per view, and NPC's wave-6 kit adds one: no call target may rise)
   Windows are not geometry: one shared fragment-shader pattern (bays x storeys in world metres) on every family,
   faded with distance so far facades do not shimmer. Per-instance colour (instanceColor) costs no draw call. ---- */
const DISTRICT_M = 400;
const LAND_USE = ['residential', 'commercial', 'industrial', 'park'];
function landUse(x, z) { const h = wildsHash(Math.floor(x / DISTRICT_M), Math.floor(z / DISTRICT_M), SEED, 7); return h < 0.5 ? 'residential' : h < 0.76 ? 'commercial' : h < 0.88 ? 'industrial' : 'park'; }
function triGeo(tris) {
  const pos = [], nor = [], uv = [], a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3(), n = new THREE.Vector3();
  for (const [p, q, r] of tris) {
    a.fromArray(p); b.fromArray(q); c.fromArray(r); n.subVectors(c, b).cross(new THREE.Vector3().subVectors(a, b)).normalize();
    for (const v of [p, q, r]) { pos.push(...v); nor.push(n.x, n.y, n.z); uv.push(0, 0); }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  return g;
}
const quad = (p, q, r, t) => [[p, q, r], [p, r, t]];
/* unit walls 0..1 high, footprint -0.5..0.5, no floor (never seen): 10 triangles */
function walls() { const g = new THREE.BoxGeometry(1, 1, 1).translate(0, 0.5, 0).toNonIndexed(); return keepTris(g, (ny) => ny > -0.9); }
function keepTris(g, keep) {
  const p = g.attributes.position.array, n = g.attributes.normal.array, u = g.attributes.uv.array, P = [], N = [], U = [];
  for (let t = 0; t < p.length / 9; t++) if (keep(n[t * 9 + 1])) { P.push(...p.slice(t * 9, t * 9 + 9)); N.push(...n.slice(t * 9, t * 9 + 9)); U.push(...u.slice(t * 6, t * 6 + 6)); }
  const o = new THREE.BufferGeometry(); o.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); o.setAttribute('normal', new THREE.Float32BufferAttribute(N, 3)); o.setAttribute('uv', new THREE.Float32BufferAttribute(U, 2)); return o;
}
/* a gable roof over the unit walls, ridge along x, eaves overhanging: 4 slope + 2 gable triangles */
function gable(rise, ox, oz) {
  const e = 0.97, r = 1 + rise, X = 0.5 + ox, Z = 0.5 + oz;
  return triGeo([
    ...quad([-X, e, Z], [X, e, Z], [X, r, 0], [-X, r, 0]),
    ...quad([X, e, -Z], [-X, e, -Z], [-X, r, 0], [X, r, 0]),
    [[0.5, 1, 0.5], [0.5, 1, -0.5], [0.5, r, 0]], [[-0.5, 1, -0.5], [-0.5, 1, 0.5], [-0.5, r, 0]],
  ]);
}
/* porch / gallery hint on the front (+z): canopy underside + fascia + two post faces (8 triangles) */
function porch() {
  const y = 0.48, t = 0.52, f = 0.74, w = 0.46, pw = 0.035;
  return triGeo([
    ...quad([-w, y, t], [w, y, t], [w, y, f], [-w, y, f]),
    ...quad([-w, y, f], [-w, y + 0.05, f], [w, y + 0.05, f], [w, y, f]).map((tr) => tr.slice().reverse()),
    ...quad([-w, 0, f - 0.01], [-w + pw, 0, f - 0.01], [-w + pw, y, f - 0.01], [-w, y, f - 0.01]),
    ...quad([w - pw, 0, f - 0.01], [w, 0, f - 0.01], [w, y, f - 0.01], [w - pw, y, f - 0.01]),
  ]);
}
const houseGeo = mergeGeometries([walls(), gable(0.42, 0.04, 0.08), porch()]);
const blockGeo = walls();
const KIT_KIND = { house: 0, midrise: 1 };
function kitMat(kind) {
  const m = new THREE.MeshLambertMaterial({ color: 0xffffff });
  m.defines = { KIT_KIND: KIT_KIND[kind] };
  m.onBeforeCompile = (sh) => {
    const V = 'varying vec3 vKitL; varying vec3 vKitW; varying vec3 vKitN; varying float vKitD;\n';
    sh.vertexShader = V + sh.vertexShader.replace('#include <project_vertex>', `#include <project_vertex>
  vKitL = position; vKitW = (modelMatrix * instanceMatrix * vec4(transformed, 1.0)).xyz;
  vKitN = normalize(mat3(modelMatrix) * mat3(instanceMatrix) * objectNormal); vKitD = -mvPosition.z;`);
    sh.fragmentShader = V + sh.fragmentShader.replace('#include <color_fragment>', `#include <color_fragment>
{ vec3 n = normalize(vKitN);
  float wall = (1.0 - step(0.3, abs(n.y))) * (1.0 - step(0.985, vKitL.y)) * step(abs(vKitL.z), 0.505) * step(abs(vKitL.x), 0.505);
  float u = abs(n.x) > abs(n.z) ? vKitW.z : vKitW.x;
  vec2 f = fract(vec2(u / 3.1, vKitW.y / 3.2));
  float near = 1.0 - smoothstep(160.0, 480.0, vKitD);
  float win = step(0.3, f.x) * step(f.x, 0.7) * step(0.3, f.y) * step(f.y, 0.82) * step(1.0, vKitW.y) * wall;
  #if KIT_KIND == 1
  win = max(win * step(3.6, vKitW.y), step(0.4, vKitW.y) * step(vKitW.y, 3.3) * step(0.08, f.x) * step(f.x, 0.92) * wall);
  vec3 roofC = vec3(0.40, 0.40, 0.41);
  #else
  vec3 roofC = vec3(0.31, 0.29, 0.30);
  #endif
  diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.15, 0.19, 0.24), win * near * 0.85);
  diffuseColor.rgb = mix(diffuseColor.rgb, roofC, step(0.4, n.y));
  diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.93, 0.92, 0.88), step(0.505, vKitL.z) * (1.0 - step(0.4, n.y)));
  diffuseColor.rgb *= 0.82 + 0.18 * smoothstep(0.0, 0.8, vKitW.y); }`);
  };
  m.customProgramCacheKey = () => 'parish-kit-' + kind;
  return m;
}
/* generic facade palettes (AUTHORED): painted timber for houses, brick/stone/render for midrises, cladding for sheds */
const PALETTE = {
  house: [0xEDE3CC, 0xE9D8A6, 0xB9C9B0, 0xB7CBD8, 0xE3B7A0, 0xF2EEE6, 0xD7C3DD, 0xC9D8C2],
  midrise: [0xB08A74, 0x9E7A68, 0xC9BFAE, 0xD6CFC2, 0x8F8D88, 0xBDB3A0],
  shed: [0xA9B0B5, 0x8E9AA3, 0xB8B2A2, 0x9AA59A],
};
const blocks = new THREE.InstancedMesh(blockGeo, kitMat('midrise'), CAP.block);
const houses = new THREE.InstancedMesh(houseGeo, kitMat('house'), CAP.block);
const KIT = { house: houses, midrise: blocks };
const KC = new THREE.Color();
for (const m of Object.values(KIT)) { m.setColorAt(0, KC.set(0xffffff)); m.count = 0; m.frustumCulled = false; scene.add(m); }
/* a lot: [x, z, w, h, d, family, yaw, colour]; houses face their nearest street (porch to the kerb) */
function kitLot(use, ix, iz, x, z, jx, jz, hh) {
  const c = wildsHash(ix, iz, SEED, 5);
  if (use === 'residential') {
    const ax = ((ix % 4) + 4) % 4, az = ((iz % 4) + 4) % 4;
    const yaw = az === 1 ? Math.PI : az === 3 ? 0 : ax === 1 ? -Math.PI / 2 : ax === 3 ? Math.PI / 2 : 0;
    return [x, z, 8 + 4 * jx, 4.2 + 3.6 * hh, 11 + 6 * jz, 'house', yaw, PALETTE.house[Math.floor(c * PALETTE.house.length)]];
  }
  if (use === 'industrial') return [x, z, 15 + 8 * jx, 6 + 5 * hh, 15 + 8 * jz, 'midrise', 0, PALETTE.shed[Math.floor(c * PALETTE.shed.length)]];
  return [x, z, 10 + 9 * jx, 7 + 42 * Math.pow(hh, 3), 10 + 9 * jz, 'midrise', 0, PALETTE.midrise[Math.floor(c * PALETTE.midrise.length)]];
}
const trees = new THREE.InstancedMesh(treeGeo, matTree, CAP.tree);
trees.count = 0; trees.frustumCulled = false; scene.add(trees);
const chunkData = new Map(); let queue = [], dirty = false;
function lmNear(x, z) { for (const id of loaded) for (const l of PAR.get(id).landmarks) if (Math.hypot(l.x - x, l.z - z) < 45) return true; return false; }
function buildChunk(ci, cj) {
  const out = { block: [], tree: [], lamp: [] }, n = CHUNK_M / CELL;
  for (let a = 0; a < n; a++) for (let b = 0; b < n; b++) {
    const ix = ci * n + a, iz = cj * n + b;
    const h = wildsHash(ix, iz, SEED, 1), jx = wildsHash(ix, iz, SEED, 2), jz = wildsHash(ix, iz, SEED, 3);
    const x = (ix + 0.2 + 0.6 * jx) * CELL, z = (iz + 0.2 + 0.6 * jz) * CELL;
    if (!parishAt(x, z) || lmNear(x, z)) continue;
    // streets: every fourth cell row/column stays open (AUTHORED grid, not the real street grid)
    const sx = ((ix % 4) + 4) % 4 === 0, sz = ((iz % 4) + 4) % 4 === 0;
    if (sx || sz) {
      // street trees stand on the walkway verge, not in the painted carriageway (wave 6)
      if (h < 0.18) out.tree.push([sx ? (ix + (jx < 0.5 ? 0.1 : 0.9)) * CELL : x, sz ? (iz + (jz < 0.5 ? 0.1 : 0.9)) * CELL : z, 0.8 + jx * 0.5, 0]);
      // a lamp every fourth cell along each street (one per block side), at the kerb (AUTHORED furniture on AUTHORED streets)
      if (!(sx && sz) && (((sx ? iz : ix) % 4) + 4) % 4 === 2 && ((sx ? ix : iz) & 4) === 0) out.lamp.push(sx ? [(ix + 0.08) * CELL, (iz + 0.5) * CELL, 0] : [(ix + 0.5) * CELL, (iz + 0.08) * CELL, Math.PI / 2]);
      continue;
    }
    const use = landUse(x, z);
    if (use === 'park') { if (h < 0.8) out.tree.push([x, z, 0.8 + jz * 0.6, 0]); continue; }   // a park lot: trees, no building
    if (h < 0.55) out.block.push(kitLot(use, ix, iz, x, z, jx, jz, wildsHash(ix, iz, SEED, 4)));
    else if (h < 0.8) out.tree.push([x, z, 0.8 + jz * 0.6, 0]);
  }
  return out;
}
function wantedChunks(x, z) {
  const ci = Math.floor(x / CHUNK_M), cj = Math.floor(z / CHUNK_M), s = new Set();
  for (let a = -RADIUS; a <= RADIUS; a++) for (let b = -RADIUS; b <= RADIUS; b++) s.add((ci + a) + ',' + (cj + b));
  return s;
}
function updateChunks(x, z) {
  const want = wantedChunks(x, z);
  for (const k of [...chunkData.keys()]) if (!want.has(k)) { chunkData.delete(k); dirty = true; }
  queue = [...want].filter((k) => !chunkData.has(k));
}
function pump(budget) {
  for (let i = 0; i < budget && queue.length; i++) { const k = queue.shift(); const [a, b] = k.split(',').map(Number); chunkData.set(k, buildChunk(a, b)); dirty = true; }
}
const M4 = new THREE.Matrix4(), Q = new THREE.Quaternion(), V = new THREE.Vector3(), S = new THREE.Vector3();
const UP = new THREE.Vector3(0, 1, 0);
function refillFabric() {
  let nb = 0, nt = 0, nl = 0;
  const kn = { house: 0, midrise: 0 };
  for (const c of chunkData.values()) {
    for (const [x, z, w, h, d, fam, yaw, col] of c.block) {
      if (nb >= CAP.block) break;   // CAP.block bounds the buildings of all kit families together
      const m = KIT[fam]; if (!m) throw new Error('parishes: unknown building family ' + fam);
      M4.compose(V.set(x, 0, z), Q.setFromAxisAngle(UP, yaw), S.set(w, h, d)); m.setMatrixAt(kn[fam], M4); m.setColorAt(kn[fam]++, KC.set(col)); nb++;
    }
    for (const [x, z, s] of c.tree) { if (nt >= CAP.tree) break; M4.compose(V.set(x, 0, z), Q.identity(), S.set(s, s, s)); trees.setMatrixAt(nt++, M4); }
    for (const [x, z, r] of c.lamp) { if (nl >= CAP.lamp) break; M4.compose(V.set(x, 0, z), Q.setFromAxisAngle(UP, r), S.set(1, 1, 1)); lamps.setMatrixAt(nl++, M4); }
  }
  for (const [f, m] of Object.entries(KIT)) { m.count = kn[f]; m.instanceMatrix.needsUpdate = true; m.instanceColor.needsUpdate = true; }
  trees.count = nt; lamps.count = nl; Q.identity();
  blocks.instanceMatrix.needsUpdate = true; trees.instanceMatrix.needsUpdate = true; lamps.instanceMatrix.needsUpdate = true; dirty = false;
}

/* ---- border markers and landmarks: one InstancedMesh per asset family ---- */
const markerGeo = mergeGeometries([new THREE.CylinderGeometry(0.4, 0.5, 9, 6).translate(0, 4.5, 0), new THREE.BoxGeometry(5, 1.4, 0.3).translate(0, 8, 0)]);
const markers = new THREE.InstancedMesh(markerGeo, matMark, CAP.marker); markers.count = 0; markers.frustumCulled = false; scene.add(markers);
/* generic silhouettes by kind: never a replica of the real building */
/* generic silhouettes by kind, never a replica of the real building (wave 5b: more parts, same one
   InstancedMesh per family, so detail costs triangles, not draw calls) */
const G = THREE;
const box = (w, h, d, x = 0, y = 0, z = 0) => new G.BoxGeometry(w, h, d).translate(x, y + h / 2, z);
const cyl = (r0, r1, h, x = 0, y = 0, z = 0, seg = 8) => new G.CylinderGeometry(r0, r1, h, seg).translate(x, y + h / 2, z);
const ring = (n, r, f) => Array.from({ length: n }, (_, i) => f(r * Math.cos(i * 2 * Math.PI / n), r * Math.sin(i * 2 * Math.PI / n)));
const FAMILY = {
  // a bell tower: plinth, shaft, open belfry of four corner posts, cornice, spire
  tower: () => mergeGeometries([box(9, 3, 9), box(6.5, 21, 6.5, 0, 3), ...[[-2.6, -2.6], [2.6, -2.6], [-2.6, 2.6], [2.6, 2.6]].map(([x, z]) => box(1.2, 6, 1.2, x, 24, z)),
    box(7.4, 1.2, 7.4, 0, 30), new G.ConeGeometry(4.4, 12, 4).rotateY(Math.PI / 4).translate(0, 37.2, 0)]),
  // a domed arena: stepped base, drum, dome, lantern
  dome: () => mergeGeometries([cyl(22, 22, 3, 0, 0, 0, 16), cyl(19, 19, 12, 0, 3, 0, 16), new G.SphereGeometry(19, 16, 6, 0, Math.PI * 2, 0, Math.PI / 2).scale(1, 0.55, 1).translate(0, 15, 0),
    cyl(2.2, 2.2, 3, 0, 25.4, 0, 8)]),
  // a civic hall: podium, block, six-column portico, pediment
  hall: () => mergeGeometries([box(36, 2, 24), box(30, 12, 16, 0, 2, -2), ...[-10, -6, -2, 2, 6, 10].map((x) => cyl(0.8, 0.8, 10, x, 2, 8.5)),
    box(24, 1, 5, 0, 12, 8.5), new G.ConeGeometry(14, 4, 4).rotateY(Math.PI / 4).scale(1, 1, 0.3).translate(0, 15, 8.5), box(30, 1, 16, 0, 14, -2)]),
  // a span: deck, two towers, stay cables as thin bars
  bridge: () => mergeGeometries([box(70, 1.6, 10, 0, 11), box(3, 26, 3, -18), box(3, 26, 3, 18),
    ...[-1, 1].flatMap((s) => [8, 14, 20].map((d) => box(d * 1.1, 0.3, 0.3, s * (18 - d / 2), 18 + d * 0.2, 0).rotateZ(0)))]),
  // a park or refuge pavilion: four posts, hipped roof, and a marker post
  other: () => mergeGeometries([...[[-4, -4], [4, -4], [-4, 4], [4, 4]].map(([x, z]) => cyl(0.35, 0.35, 4, x, 0, z, 6)),
    new G.ConeGeometry(7.5, 3, 4).rotateY(Math.PI / 4).translate(0, 5.5, 0), cyl(0.5, 0.9, 9, 9, 0, 0, 6)]),
};
/* AUTHORED street furniture: a lamp standard (pole, arm, lit head) on street cells, one InstancedMesh */
const lampGeo = (() => {
  const paint = (g, c) => { const col = new G.Color(c), n = g.attributes.position.count, a = new Float32Array(n * 3); for (let i = 0; i < n; i++) col.toArray(a, i * 3); g.setAttribute('color', new G.BufferAttribute(a, 3)); return g; };
  return mergeGeometries([paint(box(0.2, 6.2, 0.2), 0x3a3f44), paint(box(1.4, 0.12, 0.12, 0.7, 6.1), 0x3a3f44), paint(box(0.5, 0.22, 0.34, 1.35, 5.85), 0xfff0c2)]);
})();
const matLamp = new THREE.MeshLambertMaterial({ vertexColors: true, emissive: 0x2a2410 });
const lamps = new THREE.InstancedMesh(lampGeo, matLamp, CAP.lamp); lamps.count = 0; lamps.frustumCulled = false; scene.add(lamps);
const lmMeshes = {};
/* LAYERS stations (sims, tasks, lessons, Cognition.X K-12): one InstancedMesh, a generic kiosk */
const PATHS = JSON.parse(document.getElementById('parish-paths').textContent);
const stationGeo = mergeGeometries([new THREE.BoxGeometry(3, 3.2, 1.2).translate(0, 1.6, 0), new THREE.BoxGeometry(4, 0.5, 2).translate(0, 3.45, 0)]);
const stations = new THREE.InstancedMesh(stationGeo, matMark, 256); stations.count = 0; stations.frustumCulled = false; scene.add(stations);
for (const [k, f] of Object.entries(FAMILY)) { const m = new THREE.InstancedMesh(f(), matLm, CAP.lm); m.count = 0; m.frustumCulled = false; scene.add(m); lmMeshes[k] = m; }
const labelsEl = document.getElementById('labels');
let labelItems = [];
function refillMarkers() {
  let n = 0; const seen = new Set();
  for (const e of labelItems.filter((l) => l.kind === 'border')) e.el.remove();
  labelItems = labelItems.filter((l) => l.kind !== 'border');
  for (const id of loaded) for (const nb of PAR.get(id).neighbours) {
    const key = [id, nb.id].sort().join('|'); if (seen.has(key) || n >= CAP.marker) continue; seen.add(key);
    const pts = longest(nb.segments), mid = pts[Math.floor(pts.length / 2)];
    M4.compose(V.set(mid[0], 0, mid[1]), Q.identity(), S.set(1, 1, 1)); markers.setMatrixAt(n++, M4);
    const el = document.createElement('span'); el.className = 'lbl border'; el.dataset.border = key;
    el.textContent = `${tr('parishes.border')}: ${PAR.get(id).name} | ${PAR.get(nb.id).name}`;
    labelsEl.append(el); labelItems.push({ kind: 'border', el, x: mid[0], y: 11, z: mid[1] });
  }
  markers.count = n; markers.instanceMatrix.needsUpdate = true;
}
function refillStations() {
  stations.count = 0;
  for (const e of labelItems.filter((l) => l.kind === 'st')) e.el.remove();
  labelItems = labelItems.filter((l) => l.kind !== 'st');
  for (const id of loaded) for (const st of (PATHS[id] ? PATHS[id].stations : [])) {
    if (stations.count >= 256) break;
    const x = st.world_m[0], z = -st.world_m[1];
    M4.compose(V.set(x, 0, z), Q.identity(), S.set(1, 1, 1)); stations.setMatrixAt(stations.count++, M4);
    const el = document.createElement('button'); el.type = 'button'; el.className = 'lbl lm st'; el.dataset.station = st.id;
    el.textContent = st.title; el.setAttribute('aria-label', `${st.title} (${st.layer}, ${st.provenance})`);
    el.addEventListener('click', () => { if (window.TCPaths && PATHS[id]) { mountPaths(id); window.TCPaths.open(st.id); } });
    labelsEl.append(el); labelItems.push({ kind: 'st', el, x, y: 6, z });
  }
  stations.instanceMatrix.needsUpdate = true;
}
const pathsEl = document.getElementById('paths');
/* pathkit's labels in the reader's locale (parishes.path.*): the kit's English defaults are never used */
const PATH_L = JSON.parse(document.getElementById('parish-path-labels').textContent)[LOC];
let pathsFor = null;
function mountPaths(id) {
  if (pathsFor === id || !window.TCPaths || !PATHS[id]) return;
  pathsFor = id; pathsEl.replaceChildren(); window.TCPaths.mount(pathsEl, PATHS[id], { hrefPrefix: '', labels: PATH_L });
}
function refillLandmarks() {
  for (const m of Object.values(lmMeshes)) m.count = 0;
  for (const e of labelItems.filter((l) => l.kind === 'lm')) e.el.remove();
  labelItems = labelItems.filter((l) => l.kind !== 'lm');
  for (const id of loaded) for (const l of PAR.get(id).landmarks) {
    const m = lmMeshes[l.family]; if (!m) throw new Error(`parishes: landmark ${l.id} family ${l.family} has no mesh`);
    if (m.count >= CAP.lm) continue;
    M4.compose(V.set(l.x, 0, l.z), Q.identity(), S.set(1, 1, 1)); m.setMatrixAt(m.count++, M4);
    const el = document.createElement('button'); el.type = 'button'; el.className = 'lbl lm'; el.dataset.landmark = l.id;
    el.innerHTML = '<b></b><span class="note" role="tooltip"></span>';
    el.firstChild.textContent = l.name;
    el.lastChild.textContent = `${l.provenance}: ${l.note}`;
    el.setAttribute('aria-label', `${l.name}. ${l.provenance}: ${l.note}`);
    labelsEl.append(el); labelItems.push({ kind: 'lm', el, x: l.x, y: 36, z: l.z });
  }
  for (const m of Object.values(lmMeshes)) m.instanceMatrix.needsUpdate = true;
}
const PV = new THREE.Vector3();
function placeLabels() {
  const w = stage.clientWidth, h = stage.clientHeight;
  for (const it of labelItems) {
    PV.set(it.x, it.y, it.z);
    if (mode === 'overview' && it.kind === 'st') { it.el.hidden = true; continue; }
    const far = PV.distanceTo(camera.position) > (mode === 'overview' ? 1e9 : 2500);
    PV.project(camera);
    const vis = !far && PV.z < 1 && Math.abs(PV.x) < 1.05 && Math.abs(PV.y) < 1.05;
    it.el.hidden = !vis;
    if (vis) it.el.style.transform = `translate(${((PV.x + 1) / 2 * w).toFixed(0)}px,${((1 - PV.y) / 2 * h).toFixed(0)}px) translate(-50%,-100%)`;
  }
}

/* ---- the player: walk, drive (FLEET stub), boat (water only) ---- */
const eye = { x: 0, z: 0, yaw: 0, pitch: -0.08 };
let mode = 'walk', run = false;
const keys = new Set();
const toastEl = document.getElementById('toast');
let toastT = 0;
function toast(msg) { toastEl.textContent = msg; toastEl.hidden = false; toastT = performance.now() + 2600; }
function canStand(m, x, z) { return m === 'boat' ? parishAt(x, z) === null : parishAt(x, z) !== null; }
function nearest(x, z, wantWater) {
  for (let r = 4; r <= 60; r += 4) for (let a = 0; a < 16; a++) {
    const px = x + r * Math.cos(a * Math.PI / 8), pz = z + r * Math.sin(a * Math.PI / 8);
    if ((parishAt(px, pz) === null) === wantWater) return [px, pz];
  }
  return null;
}
/* one place applies a mode to the view (REVIEW wave 6: enterExit used to set mode directly, so leaving a ride from
   the overview kept the overview's render scale, hidden fabric and pressed Overview button) */
function applyMode(m) {
  mode = m;
  for (const b of document.querySelectorAll('[data-mode]')) b.setAttribute('aria-pressed', String(b.dataset.mode === m));
  stage.dataset.mode = m;
  applyPR(m === 'overview' ? OVERVIEW_PR : 1);
  blocks.visible = houses.visible = trees.visible = lamps.visible = m !== 'overview';
}
function setMode(m) {
  if (riding && m !== 'overview') {
    // riding: only the overview is another view; from the overview any mode button returns to the ride
    if (mode !== 'overview') return false;
    applyMode(riding.medium === 'water' ? 'boat' : 'drive'); return true;
  }
  if (m === 'boat' && mode !== 'boat') {
    const w = nearest(eye.x, eye.z, true); if (!w) { toast(tr('parishes.boat.nowater')); return false; }
    eye.x = w[0]; eye.z = w[1];
  } else if (mode === 'boat' && m !== 'boat' && m !== 'overview') {
    const l = nearest(eye.x, eye.z, false); if (!l) { toast(tr('parishes.boat.noland')); return false; }
    eye.x = l[0]; eye.z = l[1];
  }
  applyMode(m);
  if (m === 'drive' || m === 'boat') toast(tr('parishes.stub_vehicle'));
  return true;
}
for (const b of document.querySelectorAll('[data-mode]')) b.addEventListener('click', () => setMode(b.dataset.mode));
addEventListener('keydown', (e) => { if (e.target.closest && e.target.closest('input,textarea,select')) return; keys.add(e.key.toLowerCase()); run = e.shiftKey; });
addEventListener('keyup', (e) => { keys.delete(e.key.toLowerCase()); run = e.shiftKey; });
let drag = null;
canvas.addEventListener('pointerdown', (e) => { drag = [e.clientX, e.clientY]; canvas.setPointerCapture(e.pointerId); });
canvas.addEventListener('pointermove', (e) => { if (!drag) return; eye.yaw -= (e.clientX - drag[0]) * 0.005; eye.pitch = Math.max(-1.2, Math.min(0.6, eye.pitch - (e.clientY - drag[1]) * 0.004)); drag = [e.clientX, e.clientY]; });
canvas.addEventListener('pointerup', () => { drag = null; });
function step(fwd, side, dt) {
  const v = (mode === 'walk' ? (run ? PACE.run : PACE.walk) : PACE[mode]) * dt;
  const sx = -Math.sin(eye.yaw), sz = -Math.cos(eye.yaw);
  const nx = eye.x + (sx * fwd - sz * side) * v, nz = eye.z + (sz * fwd + sx * side) * v;
  if (canStand(mode, nx, nz)) { eye.x = nx; eye.z = nz; return true; }
  return false;
}
function control(dt) {
  if (mode === 'overview') return;
  if (riding) { drive(dt); return; }
  const f = (keys.has('w') || keys.has('arrowup') ? 1 : 0) - (keys.has('s') || keys.has('arrowdown') ? 1 : 0);
  const turn = (keys.has('a') || keys.has('arrowleft') ? 1 : 0) - (keys.has('d') || keys.has('arrowright') ? 1 : 0);
  eye.yaw += turn * dt * (mode === 'walk' ? 1.6 : 1.1);
  if (f) step(f, 0, dt);
}
function placeCamera() {
  if (mode === 'overview') {
    const p = current || [...PAR.values()][0], b = p.bbox, span = Math.max(b[2] - b[0], b[3] - b[1]);
    camera.position.set((b[0] + b[2]) / 2, span * 0.95, (b[1] + b[3]) / 2 + span * 0.35);
    camera.lookAt((b[0] + b[2]) / 2, 0, (b[1] + b[3]) / 2);
    scene.fog.far = span * 4; return;
  }
  scene.fog.far = 4200;
  if (riding) { fleetChaseCamera(camera, riding.st, riding.spec, 1 / 60, { snap: !!riding.snap }); riding.snap = false; water.position.x = eye.x; water.position.z = eye.z; return; }
  camera.position.set(eye.x, EYE[mode], eye.z);
  camera.rotation.set(eye.pitch, eye.yaw, 0, 'YXZ');
  water.position.x = eye.x; water.position.z = eye.z;
}
const mapLabel = document.getElementById('maplabel'), whereEl = document.getElementById('where'), hudEl = document.getElementById('hud');
/* quest finds (play only, device-only; the quest engine records them): arrive, border, landmark, ride */
const FINDS = JSON.parse(document.getElementById('parish-finds').textContent);
const found = [];
function qfind(id) { if (!id) return; found.push(id); if (window.TCQuests) window.TCQuests.find(id); }
let jumping = false;
function checkParish() {
  const p = parishAt(eye.x, eye.z);
  if (p && (!current || p.id !== current.id)) {
    if (current && !jumping) { toast(`${tr('parishes.border')}: ${current.name} → ${p.name}`); qfind(FINDS.border[[current.id, p.id].sort().join('|')]); }
    current = p;
    qfind(FINDS.arrive[p.id]);
  }
  if (current && !jumping) for (const l of current.landmarks) if (FINDS.landmark[l.id] && !found.includes(FINDS.landmark[l.id]) && Math.hypot(l.x - eye.x, l.z - eye.z) < 60) qfind(FINDS.landmark[l.id]);
  if (current) mountPaths(current.id);
  streamParishes(eye.x, eye.z);
}
function hud() {
  const lx = Math.round(eye.x - current.origin_m[0]), lz = Math.round(eye.z - current.origin_m[1]);
  whereEl.textContent = current.name;
  if (mapLabel.dataset.parish !== current.id) { mapLabel.dataset.parish = current.id; mapLabel.textContent = `${current.map_label} · ${current.map_fabric}`; }
  hudEl.textContent = `x ${lx} m · z ${lz} m · ${tr('parishes.ground')}`;
}
function teleport(x, z, yaw) {
  // a jump is not a crossing: step out of any vehicle, adopt the parish under the new spot silently
  if (riding) { riding = null; applyMode('walk'); enterBtn.setAttribute('aria-pressed', 'false'); }
  eye.x = x; eye.z = z; if (yaw !== undefined) eye.yaw = yaw;
  const was = current; current = parishAt(x, z) || current;
  if (current && current !== was) qfind(FINDS.arrive[current.id]);
  jumping = true; checkParish(); jumping = false; updateChunks(eye.x, eye.z); pump(1e9); refillFabric();
}

/* ---- minimap: the parish's own map image when the registry has one; else the outlines ---- */
const mini = document.getElementById('minimap'), mctx = mini.getContext('2d');
const mapImg = new Map();
function tok(n) { return getComputedStyle(document.body).getPropertyValue(n).trim(); }
const MINI_M = 9000;
function drawMinimap() {
  const S = mini.width, k = S / MINI_M, cx = eye.x, cz = eye.z;
  const X = (x) => (x - cx) * k + S / 2, Z = (z) => (z - cz) * k + S / 2;
  mctx.fillStyle = tok('--tc-steel'); mctx.globalAlpha = 0.35; mctx.fillRect(0, 0, S, S); mctx.globalAlpha = 1;
  for (const p of PAR.values()) {
    const src = p.map_preview;
    if (src && mapImg.has(src) && mapImg.get(src).complete && mapImg.get(src).naturalWidth) {
      const b = p.map_world; mctx.drawImage(mapImg.get(src), X(b[0]), Z(b[1]), (b[2] - b[0]) * k, (b[3] - b[1]) * k);
    } else {
      if (src && !mapImg.has(src)) { const im = new Image(); im.src = '../' + src; mapImg.set(src, im); }
      mctx.beginPath();
      for (const r of p.rings_m) r.forEach(([x, z], i) => (i ? mctx.lineTo(X(x), Z(z)) : mctx.moveTo(X(x), Z(z))));
      mctx.fillStyle = tok(loaded.has(p.id) ? '--tc-panel' : '--tc-plate'); mctx.fill('evenodd');
      mctx.strokeStyle = tok('--tc-muted'); mctx.lineWidth = 1; mctx.stroke();
    }
  }
  mctx.fillStyle = tok('--tc-amber'); mctx.beginPath(); mctx.arc(S / 2, S / 2, 4, 0, 7); mctx.fill();
  mctx.strokeStyle = tok('--tc-amber'); mctx.beginPath(); mctx.moveTo(S / 2, S / 2); mctx.lineTo(S / 2 - 12 * Math.sin(eye.yaw), S / 2 - 12 * Math.cos(eye.yaw)); mctx.stroke();
}

/* ---- satellite: VIEW-TIME only, requested by this browser, never stored ---- */
const R = D.region;
function lonlat(x, z) { return [R.lon0 + x / R.m_per_deg_lon, R.lat0 - z / R.m_per_deg_lat]; }
function tileOf(lon, lat, zm) {
  const n = 2 ** zm, xt = Math.floor((lon + 180) / 360 * n);
  const la = lat * Math.PI / 180, yt = Math.floor((1 - Math.log(Math.tan(la) + 1 / Math.cos(la)) / Math.PI) / 2 * n);
  return [xt, yt];
}
const satBtn = document.getElementById('sat'), satBox = document.getElementById('satbox'), satMsg = document.getElementById('satmsg');
/* Mapbox only with an operator token from the deploy-time runtime config
   (./config/runtime.json, never committed); read when the learner turns the
   layer on, never at load. Absent, unreadable or not a public pk. token: OFF. */
const SAT = D.satellite;
let mapboxToken = null, tokenRead = false;
/* one shared read of the operator config (REVIEW wave 6: a second toggle during the fetch used to see "no token"
   and a stale first call then appended a second <img>); every toggle bumps satGen and a superseded call stops */
let tokenP = null, satGen = 0;
function readToken() {
  if (tokenP) return tokenP; tokenRead = true;
  tokenP = (async () => {
    try {
      const r = await fetch('./config/runtime.json', { cache: 'no-store' });
      if (r.ok) { const j = await r.json(); if (j && typeof j.mapbox_token === 'string' && j.mapbox_token.startsWith('pk.')) mapboxToken = j.mapbox_token; }
    } catch (e) { mapboxToken = null; }
    return mapboxToken;
  })();
  return tokenP;
}
async function showSatellite(on) {
  const gen = ++satGen;
  satBtn.setAttribute('aria-pressed', String(on)); satBox.hidden = !on;
  satBox.replaceChildren();
  if (!on) { satMsg.textContent = ''; return satState(); }
  const tokenNow = await readToken();
  if (gen !== satGen) return satState();   // superseded by a later toggle
  const [lon, lat] = lonlat(eye.x, eye.z), zm = 16, [tx, ty] = tileOf(lon, lat, zm);
  const img = new Image(); img.alt = SAT.usgs.attribution; img.referrerPolicy = 'no-referrer';
  img.onerror = () => { satMsg.textContent = `${tr('parishes.sat.failed')} · ${tokenNow ? SAT.mapbox.attribution : SAT.mapbox.refusal_text}`; satBox.dataset.failed = '1'; };
  img.src = tokenNow ? SAT.mapbox.tiles.replace('{z}', zm).replace('{x}', tx).replace('{y}', ty).replace('{token}', encodeURIComponent(tokenNow))
    : SAT.usgs.tiles.replace('{z}', zm).replace('{y}', ty).replace('{x}', tx);
  satBox.append(img);
  satMsg.textContent = `${tr('parishes.sat.usgs')} (${SAT.usgs.attribution}) · ${tokenNow ? SAT.mapbox.attribution : SAT.mapbox.refusal_text}`;
  return satState();
}
function satState() { const im = satBox.querySelector('img'); return { box: !satBox.hidden, src: im ? im.src : null, msg: satMsg.textContent, token: mapboxToken !== null }; }
satBtn.addEventListener('click', () => showSatellite(satBtn.getAttribute('aria-pressed') !== 'true'));

/* ---- FLEET: parked vehicles per parish, enter/exit with E; boats on water only ---- */
const FLEETREG = JSON.parse(document.getElementById('fleet-registry').textContent);
const fground = fleetFlatGround(0, 0, (x, z) => parishAt(x, z) === null);
const parked = [];                     // {st, spec, h, medium}
let riding = null;
let fl = null;
function waterNear(x, z) {
  for (let r = 150; r <= 30000; r += 150) for (let a = 0; a < 24; a++) {
    const px = x + r * Math.cos(a * Math.PI / 12), pz = z + r * Math.sin(a * Math.PI / 12);
    if (parishAt(px, pz) === null && parishAt(px + 30, pz) === null && parishAt(px - 30, pz) === null && parishAt(px, pz + 30) === null && parishAt(px, pz - 30) === null) return [px, pz];
  }
  return null;
}
if (FLEETREG) {
  const land = FLEETREG.fleet.filter((e) => e.medium === 'land'), wet = FLEETREG.fleet.filter((e) => e.medium === 'water');
  const plan = [];
  D.parishes.forEach((p, i) => {
    const a = p.landmarks[0] ? [p.landmarks[0].x, p.landmarks[0].z + 90] : p.origin_m;
    for (let k = 0; k < 4; k++) plan.push({ e: land[(i * 4 + k) % land.length], x: a[0] + 14 + k * 9, z: a[1] + 8 });
    const w = waterNear(a[0], a[1]);
    if (w) for (let k = 0; k < 2; k++) plan.push({ e: wet[(i * 2 + k) % wet.length], x: w[0] + k * 25, z: w[1] });
  });
  const cap = Object.fromEntries(FLEETREG.families.map((f) => [f.id, Math.max(1, plan.filter((q) => q.e.family === f.id).length)]));
  fl = fleetCreate(THREE, FLEETREG, cap); scene.add(fl.group);
  for (const q of plan) {
    const spec = fleetSpec(q.e);
    if (!fleetCanSpawn(spec, fground, q.x, q.z).ok) continue;
    const st = fleetState(spec, fground, q.x, q.z, 0), h = fl.spawn(spec.id, st);
    parked.push({ st, spec, h, medium: q.e.medium, id: q.e.id });
  }
}
const enterBtn = document.getElementById('enter');
function enterExit() {
  if (!FLEETREG) { toast(tr('parishes.stub_vehicle')); return false; }
  if (riding) {
    const p = fleetExitPoint(riding.st, riding.spec, fground);
    if (!p) { toast(tr('parishes.boat.noland')); return false; }
    eye.x = p.x; eye.z = p.z; eye.yaw = riding.st.yaw + Math.PI; riding = null; applyMode('walk');
  } else {
    const v = fleetNearest({ x: eye.x, z: eye.z }, parked, 2.5);
    if (!v) return false;
    riding = v; riding.snap = true; applyMode(v.medium === 'water' ? 'boat' : 'drive');
    qfind(FINDS.ride[v.medium]);
  }
  stage.dataset.mode = mode; enterBtn.setAttribute('aria-pressed', String(!!riding));
  return true;
}
enterBtn.addEventListener('click', () => { if (!enterExit()) toast(tr('parishes.boat.nowater')); });
/* E / T: no key-repeat, no modifier chords, not while typing (REVIEW wave 6) */
const plainKey = (e) => !e.repeat && !e.ctrlKey && !e.metaKey && !e.altKey && !(e.target.closest && e.target.closest('input,textarea,select'));
addEventListener('keydown', (e) => { if ((e.key === 'e' || e.key === 'E') && plainKey(e)) enterExit(); });
function drive(dt) {
  const f = (keys.has('w') || keys.has('arrowup') ? 1 : 0) - (keys.has('s') || keys.has('arrowdown') ? 1 : 0);
  const t = (keys.has('a') || keys.has('arrowleft') ? 1 : 0) - (keys.has('d') || keys.has('arrowright') ? 1 : 0);
  fleetStep(riding.st, riding.spec, { throttle: f, steer: t, brake: keys.has(' ') ? 1 : 0 }, fground, dt);
  riding.h.set(riding.st); eye.x = riding.st.x; eye.z = riding.st.z;
}

/* ---- NPC guides (NPC contract v1): every line a verbatim registry quote with its source ---- */
const NPCD = JSON.parse(document.getElementById('parish-npcs').textContent);
const npcPanel = document.getElementById('npcpanel');
let npcKit = null;
const npcClock = makeClock(8, 1 / 60);
if (NPCD) {
  npcKit = TCNPC.createNPCKit({
    THREE, scene, npcs: NPCD.npcs, panelRoot: npcPanel, honesty: NPCD.honesty,
    placeOf: (id) => (Object.hasOwn(NPCD.places, id) ? { x: NPCD.places[id][0], z: NPCD.places[id][1] } : null),
    labels: labelsFrom(tr),
    onTalk: (npc) => { if (window.TCQuests) window.TCQuests.find('treasure-guide-' + npc.parish); },
  });
}
function talk() { if (!npcKit) { toast(tr('parishes.stub_vehicle')); return null; } return npcKit.talkNearest(); }
document.getElementById('talk').addEventListener('click', () => talk());
addEventListener('keydown', (e) => { if ((e.key === 't' || e.key === 'T') && plainKey(e)) talk(); });

function resize() { const w = stage.clientWidth, h = stage.clientHeight; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); }
addEventListener('resize', resize);
let labelT = 0;
let last = performance.now(), info = { calls: 0, triangles: 0 }, frameMs = 0, miniT = 0, cell = '';
function frame(now) {
  const dt = Math.min(0.1, (now - last) / 1000); last = now;
  /* the overview does not move the player: no parish check there (it would also pull the camera back to
     the player's parish and fire a false border find after view('overview', other)) */
  control(dt); if (mode !== 'overview') checkParish();
  const over = mode === 'overview';
  /* the overview (km above ground): vehicles and guides are sub-pixel, fabric is hidden, so none of them is
     updated, streamed or drawn there (headroom: web/eval_parishes.mjs overview rows) */
  if (fl) fl.group.visible = !over;
  water.visible = !over; scene.background = over ? WATER_BG : SKY_BG;   // overview: one clear instead of a full-screen water pass
  if (npcKit && !over) npcKit.update(dt, { x: eye.x, z: eye.z }, npcClock.tick(dt));   // AUTHORED game clock (npckit makeClock): one game hour per real minute
  const c = Math.floor(eye.x / CHUNK_M) + ',' + Math.floor(eye.z / CHUNK_M);
  if (!over) { if (c !== cell) { cell = c; updateChunks(eye.x, eye.z); } pump(BUILD_PER_FRAME); if (dirty) refillFabric(); }
  matWater.emissiveIntensity = 0.06 + 0.05 * Math.sin(now / 900);   // water shimmer: one uniform, no extra draw
  waterU.uTime.value = now / 1000;
  placeCamera();
  const t0 = performance.now(); renderer.render(scene, camera); frameMs = performance.now() - t0;
  info = { calls: renderer.info.render.calls, triangles: renderer.info.render.triangles };
  if (!over || now - labelT > 250) { labelT = now; placeLabels(); }
  if (now - miniT > 200) { miniT = now; drawMinimap(); hud(); }
  if (!toastEl.hidden && now > toastT) toastEl.hidden = true;
  requestAnimationFrame(frame);
}

/* ---- eval + test hooks (web/eval_parishes.mjs) ---- */
function borderApproach(a, b) {
  const nb = PAR.get(a).neighbours.find((n) => n.id === b); if (!nb) throw new Error(`parishes: ${a} has no neighbour ${b}`);
  const pts = longest(nb.segments), i = Math.floor(pts.length / 2), p0 = pts[Math.max(0, i - 1)], p1 = pts[Math.min(pts.length - 1, i)];
  const mx = (p0[0] + p1[0]) / 2, mz = (p0[1] + p1[1]) / 2;
  let nx = -(p1[1] - p0[1]), nz = p1[0] - p0[0]; const L = Math.hypot(nx, nz) || 1; nx /= L; nz /= L;
  if (!inParish(PAR.get(a), mx + nx * 40, mz + nz * 40)) { nx = -nx; nz = -nz; }
  return { from: [mx + nx * 40, mz + nz * 40], yaw: Math.atan2(nx, nz), mid: [mx, mz] };
}
/* the start spot: 90 m south of the parish's first landmark (facing it), else the frame origin when on land, else an outline vertex */
function startSpot(p) { const l = p.landmarks[0]; if (l && parishAt(l.x, l.z + 90) === p) return [l.x, l.z + 90]; return parishAt(p.origin_m[0], p.origin_m[1]) === p ? p.origin_m : p.rings_m[0][0]; }
window.__parishes = {
  ids: () => [...PAR.keys()],
  pairs: () => [...PAR.values()].flatMap((p) => p.neighbours.map((n) => [p.id, n.id])).filter(([a, b]) => a < b),
  current: () => current && current.id, loaded: () => [...loaded].sort(), mode: () => mode,
  eye: () => ({ ...eye }), teleport, setMode,
  local: () => ({ parish: current.id, x: eye.x - current.origin_m[0], z: eye.z - current.origin_m[1] }),
  view(name, id) {
    const p = PAR.get(id || D.parishes[0].id);
    if (name === 'overview') { current = p; setMode('overview'); return; }
    if (mode !== 'walk') setMode('walk');
    if (name === 'origin') { const o = startSpot(p); teleport(o[0], o[1], 0); }
    else if (name === 'border') { const n = p.neighbours[0]; if (!n) throw new Error('parishes: no neighbour for ' + p.id); const a = borderApproach(p.id, n.id); teleport(a.from[0], a.from[1], a.yaw); }
    else throw new Error('parishes: unknown view ' + name);
  },
  /* walk from 40 m inside parish a straight over its border with b; returns what was seen */
  cross(a, b, mode2 = 'walk') {
    const ap = borderApproach(a, b); setMode('walk'); teleport(ap.from[0], ap.from[1], ap.yaw);
    if (mode2 !== 'walk') setMode(mode2);
    const before = { current: current.id, loaded: [...loaded].sort() };
    let n = 0; while (current.id === a && n < 400) { if (!step(1, 0, 0.5)) break; checkParish(); n++; }
    return { before, after: { current: current.id, loaded: [...loaded].sort() }, steps: n,
      marker: [...document.querySelectorAll('.lbl.border')].map((e) => e.dataset.border) };
  },
  canStand: (m, x, z) => canStand(m, x, z),
  npcs: () => (npcKit ? { count: npcKit.agents.length, stats: npcKit.stats() } : null),
  /* stand beside the nearest guide of this parish and talk: returns the dialogue's first line and source */
  talkIn(fips) {
    const a = npcKit.agents.find((q) => q.npc.parish === fips); if (!a) throw new Error('parishes: no guide placed in ' + fips);
    teleport(a.x + 1, a.z + 1); npcKit.update(0.016, { x: eye.x, z: eye.z }, 12); npcKit.talkTo(a.id);
    const q = npcPanel.querySelector('blockquote'), src = npcPanel.querySelector('.npc-src code');
    return { id: a.id, line: q ? q.textContent : null, source: src ? src.textContent : null, open: !!npcPanel.querySelector('[role="dialog"]') || !npcPanel.hidden };
  },
  fleet: () => ({ parked: parked.length, land: parked.filter((v) => v.medium === 'land').length, water: parked.filter((v) => v.medium === 'water').length,
    riding: riding && riding.id, drawCalls: fl ? fl.drawCalls() : 0,
    wrongMedium: parked.filter((v) => (v.medium === 'water') !== (parishAt(v.st.x, v.st.z) === null)).map((v) => v.id) }),
  /* stand beside a parked vehicle of that medium, enter, drive dt seconds full throttle, report */
  ride(medium, seconds) {
    const v = parked.find((q) => q.medium === medium); if (!v) throw new Error('parishes: no parked ' + medium + ' vehicle');
    if (riding) enterExit();
    setMode('walk'); eye.x = v.st.x + Math.sin(v.st.yaw) * 0; eye.z = v.st.z; if (!enterExit()) throw new Error('parishes: could not enter ' + v.id);
    const x0 = v.st.x, z0 = v.st.z; let wet = 0, n = 0;
    for (let t = 0; t < seconds; t += 0.05) { keys.add('w'); drive(0.05); n++; if ((parishAt(v.st.x, v.st.z) === null) !== (medium === 'water')) wet++; }
    keys.delete('w');
    return { id: v.id, moved: Math.hypot(v.st.x - x0, v.st.z - z0), wrongMediumSteps: wet, steps: n, mode, refused: v.st.refused };
  },
  exit: () => { const ok = riding ? enterExit() : false; return { ok, mode, riding: riding && riding.id }; },
  stats: () => ({
    mode, current: current && current.id, loaded: [...loaded].sort(), calls: info.calls, triangles: info.triangles,
    chunks: chunkData.size, pending: queue.length, frameMs,
    instances: { block: blocks.visible ? houses.count + blocks.count : 0, tree: trees.visible ? trees.count : 0, lamp: lamps.visible ? lamps.count : 0, marker: markers.count,
      ...Object.fromEntries(Object.entries(lmMeshes).map(([k, m]) => ['lm_' + k, m.count])) },
    kit: Object.fromEntries(Object.entries(KIT).map(([k, m]) => [k, m.visible ? m.count : 0])),
    kitTris: { house: houseGeo.attributes.position.count / 3, midrise: blockGeo.attributes.position.count / 3, tree: treeGeo.index ? treeGeo.index.count / 3 : treeGeo.attributes.position.count / 3 },
    ground: { ready: [...groundReady].sort(), failed: groundFailed.slice(), px: GROUND_PX },
    atmosphere: { skyCss: getComputedStyle(canvas).backgroundImage.startsWith('linear-gradient'), clearAlpha: renderer.getClearAlpha(), fog: scene.fog.color.getHex(), horizon: HORIZON, sun: SUN.toArray().map((v) => +v.toFixed(3)) },
    fleetVisible: fl ? fl.group.visible : null, finds: [...found],
    instancedFamilies: [blocks, houses, trees, lamps, markers, stations, ...Object.values(lmMeshes)].every((m) => m.isInstancedMesh),
    stations: stations.count, pathsFor, pathChooser: !!pathsEl.querySelector('[role="radiogroup"], [role="radio"]'),
    fabricMeshes: scene.children.filter((o) => o.geometry === blockGeo || o.geometry === treeGeo).length,
    landMeshes: scene.children.filter((o) => o.userData.parish).length,
    groundY: [...landMesh.values()].every((m) => { const a = m.geometry.attributes.position.array; for (let i = 1; i < a.length; i += 3) if (a[i] !== 0) return false; return true; }),
    caps: CAP, chunkM: CHUNK_M, radius: RADIUS,
  }),
  frameTimes(n) { return new Promise((res) => { const t = []; const f = (now) => { t.push(now); if (t.length > n) res(t.slice(1).map((v, i) => v - t[i])); else requestAnimationFrame(f); }; requestAnimationFrame(f); }); },
  satellite: (on) => showSatellite(on), satState,
  /* diagnosis only (eval): render scale in the current view */
  /* eval only: draw calls per fabric family, measured as (calls with everything) - (calls with that family hidden) */
  familyCalls() {
    const fam = { house: houses, midrise: blocks, tree: trees, lamp: lamps }, out = {};
    renderer.render(scene, camera); const all = renderer.info.render.calls;
    for (const [k, m] of Object.entries(fam)) { const v = m.visible; m.visible = false; renderer.render(scene, camera); out[k] = all - renderer.info.render.calls; m.visible = v; }
    return out;
  },
  renderScale: (k) => { if (k !== undefined) applyPR(k); return { prScale, pixelRatio: renderer.getPixelRatio() }; },
};
resize();
{ const p = PAR.get('22071') || PAR.get(D.parishes[0].id); const o = startSpot(p); teleport(o[0], o[1], 0); }
requestAnimationFrame(frame);
document.documentElement.dataset.parishesReady = '1';
'''

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>{STYLE_HEAD_JS}</script>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' stroke='%23E8A33D' stroke-width='2.6' stroke-linejoin='round'/%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E">
<title>SmartCiti.X : Trade Craft Academy — the parishes</title>
<style>
/* UI colours come ONLY from the site theme's tokens (--tc-*), so all five
   styles reach this page; the world's sky, land and water are the world's. */
body.tc-theme-canvas{{--plate:var(--tc-plate);--panel:var(--tc-panel);--ink:var(--tc-ink);--muted:var(--tc-muted);
  --rule:var(--tc-line);--mark:var(--tc-amber);--mark-ink:var(--tc-amber-ink);--steel:var(--tc-steel);
  --scrim:color-mix(in srgb,var(--tc-plate) 84%,transparent);--sunk:color-mix(in srgb,var(--tc-plate) 78%,black);
  --paper:var(--tc-plate)}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--plate);color:var(--ink);font:16px/1.6 "IBM Plex Sans",system-ui,sans-serif}}
.wrap{{max-width:1280px;margin:0 auto;padding:0 16px 48px}}
header{{padding:24px 0 8px;border-bottom:3px solid var(--mark)}}
header h1{{font:700 30px/1.1 "Barlow Condensed",system-ui,sans-serif;margin:0}}
header p{{color:var(--muted);margin:6px 0 10px}}
a{{color:var(--steel)}}
.stub{{background:var(--sunk);border-inline-start:3px solid var(--mark);padding:8px 12px;border-radius:6px}}
#stage{{position:relative;height:min(72vh,720px);min-height:380px;border:1px solid var(--rule);border-radius:10px;overflow:hidden;touch-action:none;margin-top:12px;background:var(--sunk)}}
#view{{display:block;width:100%;height:100%;outline:none}}
#view:focus-visible{{outline:3px solid var(--mark);outline-offset:-3px}}
#labels{{position:absolute;inset:0;pointer-events:none;overflow:hidden}}
.lbl{{position:absolute;left:0;top:0;font:600 12px/1.2 "IBM Plex Sans",system-ui,sans-serif;background:var(--scrim);color:var(--ink);border:1px solid var(--mark);border-radius:5px;padding:4px 7px;white-space:nowrap}}
.lbl.border{{border-color:var(--steel)}}
.lbl.lm{{pointer-events:auto;cursor:help}}
.lbl.lm .note{{display:none;white-space:normal;max-width:260px;font-weight:400;color:var(--muted)}}
.lbl.lm:hover .note,.lbl.lm:focus-visible .note,.lbl.lm:focus .note{{display:block}}
.ctl{{position:absolute;top:10px;inset-inline-start:10px;display:flex;flex-wrap:wrap;gap:6px;align-items:center;max-width:calc(100% - 240px)}}
.ctl .tc-btn{{background:var(--scrim);color:var(--ink);min-block-size:40px;padding:8px 12px}}
.ctl .tc-btn[aria-pressed="true"]{{background:var(--steel);color:var(--sunk);border-color:var(--steel)}}
.where{{background:var(--scrim);color:var(--ink);border-radius:6px;padding:8px 10px;font-size:13px}}
#minimap{{position:absolute;bottom:10px;inset-inline-end:10px;width:200px;height:200px;border:2px solid var(--sunk);border-radius:8px;background:var(--sunk)}}
#satbox{{position:absolute;bottom:220px;inset-inline-end:10px;width:200px;height:200px;border:2px solid var(--steel);border-radius:8px;overflow:hidden;background:var(--sunk)}}
#satbox img{{width:100%;height:100%;object-fit:cover;display:block}}
#toast{{position:absolute;bottom:20px;left:50%;transform:translateX(-50%);background:var(--mark);color:var(--mark-ink);border-radius:6px;padding:8px 14px;font-weight:600;max-width:70%}}
.help,.none{{color:var(--muted);font-size:14px}}
.none{{font-style:italic}}
.prov{{font:600 11px/1 "IBM Plex Mono",monospace;background:var(--sunk);color:var(--muted);border-radius:4px;padding:3px 6px}}
.honesty{{background:var(--sunk);border-inline-start:3px solid var(--mark);border-radius:6px;padding:12px 26px;color:var(--muted);font-size:14px}}
h2{{font:700 24px/1.1 "Barlow Condensed",system-ui,sans-serif;margin:22px 0 6px}}
code{{font:13px "IBM Plex Mono",monospace;color:var(--steel)}}
kbd{{font:12px "IBM Plex Mono",monospace;border:1px solid var(--rule);border-radius:4px;padding:1px 5px;background:var(--sunk)}}
@media(max-width:720px){{#minimap,#satbox{{width:120px;height:120px}}#satbox{{bottom:140px}}.ctl{{max-width:calc(100% - 20px)}}}}
</style>
<style>{NAV_CSS}</style>
<style data-tc-theme="canvas">{THEME_CSS}</style>
{QUEST_CSS_BLOCK}
{PATH_CSS_BLOCK}
{NPC_CSS_BLOCK}
</head>
<body class="tc-theme-canvas">
{NAV}<div class="wrap">
<header>
  <h1>{TS("parishes.title")}</h1>
  <p>{TS("parishes.lede")}</p>
</header>
{stub_banner}
<div id="stage" data-mode="walk" data-parish-state="{PARISH_STATE}">
  <canvas id="view" tabindex="0" aria-label="{TA("parishes.canvas_label")}" data-i18n-aria="parishes.canvas_label"></canvas>
  <div id="labels"></div>
  <div class="ctl"><span class="where" id="where"></span>
    <button type="button" class="tc-btn tc-btn-ghost" data-mode="walk" aria-pressed="true">{TS("parishes.mode.walk")}</button>
    <button type="button" class="tc-btn tc-btn-ghost" id="enter" aria-pressed="false">{TS("parishes.mode.drive")} / {TS("parishes.mode.boat")} (E)</button>
    <button type="button" class="tc-btn tc-btn-ghost" id="talk">{TS("parishes.npc.talk")}</button>
    <button type="button" class="tc-btn tc-btn-ghost" data-mode="overview" aria-pressed="false">{TS("parishes.mode.overview")}</button>
    <button type="button" class="tc-btn tc-btn-ghost" id="sat" aria-pressed="false">{TS("parishes.sat.toggle")}</button>
    <span class="where" id="hud"></span></div>
  <canvas id="minimap" width="200" height="200" aria-label="{TA("parishes.minimap_label")}" data-i18n-aria="parishes.minimap_label"></canvas>
  <div id="satbox" hidden></div>
  <div id="toast" hidden role="status"></div>
</div>
<p class="help" id="maplabel" data-map-label></p>
<p class="help" data-ground-label lang="en">{esc(DATA["honesty"]["ground"])}</p>
<p class="help" id="satmsg" data-sat-msg aria-live="polite"></p>
<p class="help">{TS("parishes.help")}</p>
<h2>{TS("parishes.h.landmarks")}</h2>
<ul data-landmarks>{lm_rows}</ul>
<h2>{TS("parishes.h.layers")}</h2>
<section id="paths" data-paths aria-live="polite"></section>
<div id="npcpanel" data-npc-root></div>
<ul data-contracts>{pending_rows}</ul>
<h2>{TS("parishes.h.quests")}</h2>
<p class="help">{TS("parishes.play_note")}</p>
{quest_block}
<h2>{TS("parishes.h.honesty")}</h2>
<ul class="honesty" data-honesty-panel>
<li data-no-elevation>{TS("parishes.no_elevation")}</li>
<li>{TS("parishes.fabric_note")}</li>
<li>{TS("parishes.sat_note")}</li>
<li data-fleet-honesty>{FLEET_HONESTY}</li>
{honesty_rows}
</ul>
<footer class="help" data-honesty>Parish registry <code>parishes/registry/parishes.json</code> ({esc(PARISH_STATE)}) · stamp <code data-stamp>{esc(DATA["source_stamp"])}</code> · {n_par} parishes · {n_border} shared borders · {n_lm} landmarks · terrain core <code>wilds/core.mjs</code>.</footer>
<script type="application/json" id="parishes-data">{embedded}</script>
<script type="application/json" id="fleet-registry">{fleet_embedded}</script>
<script type="application/json" id="parish-paths">{paths_embedded}</script>
<script type="application/json" id="parish-path-labels">{pathlabels_embedded}</script>
<script type="application/json" id="parish-npcs">{npcs_embedded}</script>
<script type="application/json" id="parish-finds">{finds_embedded}</script>
<script type="application/json" id="parishes-i18n">__PARISHES_I18N__</script>
<script type="importmap">
{{"imports":{{
  "three":"./vendor/three.module.min.js",
  "three/addons/":"./vendor/addons/"
}}}}
</script>
<script type="module" id="parishes-main">{JS}</script>
{QUEST_SCRIPT}
{PATH_SCRIPT}
<script>{STYLE_JS}</script>
</div></body>
</html>
'''

I18N_CAT = {}
for _f in sorted((ROOT / 'i18n/locales').glob('*.json')):
    _c = json.loads(_f.read_text(encoding='utf-8'))
    for _need in ('locale', 'dir', 'language', 'strings'):
        need(_c, _need, _f.name)
    _s = {}
    for _k in sorted(_USED):
        if _k not in _c['strings'] or not isinstance(_c['strings'][_k], str) or not _c['strings'][_k].strip():
            raise BuildError(f'build_parishes: locale {_c["locale"]} has no parishes chrome key {_k!r}')
        _s[_k] = _c['strings'][_k]
    I18N_CAT[_c['locale']] = {'dir': _c['dir'], 'language': _c['language'], 'strings': _s}
if len(I18N_CAT) != 8 or 'en' not in I18N_CAT:
    raise BuildError(f'build_parishes: expected 8 locales incl. en, found {sorted(I18N_CAT)}')
page = page.replace('__PARISHES_I18N__', json.dumps(I18N_CAT, ensure_ascii=False, sort_keys=True).replace('</', '<\\/'))

# search and link-preview head tags (web/seo.py): head region only
page = apply_seo(page, PAGE, 'The parishes \u2014 SmartCiti.X : Trade Craft Academy',
                 'Walk and drive connected New Orleans parishes on flat authored ground: generic landmark assets, '
                 'satellite imagery as a view-time layer only.', 'page')
emit(HERE / 'trade_craft_parishes.html', page,
     f'{n_par} parishes ({PARISH_STATE}) | {n_border} borders | {n_lm} landmarks | nav wired | '
     + ' | '.join(f'{k} {v}' for k, v in STATES.items()) + f' | quests {QUEST_STATE}')
