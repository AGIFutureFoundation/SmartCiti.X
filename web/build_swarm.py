#!/usr/bin/env python3
"""The Omega Swarm on a map: web/trade_craft_swarm.html (wave 25).

Reads swarm/registry/swarm.json (python3 swarm/build.py) and draws it: the 9 SCRIPTED hives, their geohash
precision-5 cells as polygons on a graticule (MapLibre, vendored; no basemap tiles, so nothing is fetched), the anchors
and sites each hive covers, the member counts per hive (roles and AUTHORED simulated robots), and the router's rules in
plain words. Every figure on the page is read from the registry at build time; no count is typed here or in a string.

A read-only "try a region" panel resolves a swarm-command/1 command the way the router does, in the page. The region
parser, the real-hardware check and the resolution steps (cells, hives, members inside) are copied from
swarm/router.mjs, swarm/geohash.mjs and swarm/geo.mjs BYTE FOR BYTE (the builder slices them out by anchor and fails
closed if an anchor moves or a slice reaches the gate, the arena or the audit log). The page does not run the safety
gate or an episode and writes no audit row; it previews the fields of the row that depend only on the command and the
registry. web/test_swarm.mjs holds the embedded code equal to the sources, and holds the page's answers equal to the real
router's over a battery of commands.

Honesty: SCRIPTED orchestration, no AI model; simulation only; real hardware is always refused ("real hardware needs a
named human operator; none is configured"); a target with no safety record runs only as a dry run; not a real-world
safety system; the sim-to-real gap; no learner location; no standard claimed. The registry's own honesty lines are
quoted verbatim. Chrome words come from the swarm.* i18n keys (8 locales; 7 machine-drafted, as each catalog declares).
Page markers are neutral (SWARM-CORE, SWARM-PAGE). The page's own scripts use no network and no storage.
"""
import hashlib
import html
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402
from seo import apply_seo  # noqa: E402
from sitenav import nav_html, labels as nav_labels, NAV_CSS, STYLE_JS  # noqa: E402
from pagehero import theme  # noqa: E402
from design_kit import STYLE_HEAD_JS  # noqa: E402
import sitenav  # noqa: E402

PAGE = 'web/trade_craft_swarm.html'
E = lambda s: html.escape(str(s), quote=True)


class SwarmPageError(Exception):
    pass


def need(c, m):
    if not c:
        raise SwarmPageError('build_swarm: ' + m)


need(PAGE in sitenav.PAGES, f'{PAGE} is not declared in web/sitenav.py GROUPS (nav.page.swarm)')

# ---- every file the builder reads is observed here, and the page stamp covers exactly those ----
READS = {}


def rd(rel):
    b = (ROOT / rel).read_bytes()
    READS[rel] = hashlib.sha256(b).hexdigest()
    return b.decode('utf-8')


REG = json.loads(rd('swarm/registry/swarm.json'))
for k in ('source_stamp', 'schema', 'honesty', 'cell_scheme', 'region_limits', 'dry_run', 'real_hardware', 'hives', 'coverage',
          'unposed', 'parishes', 'capabilities', 'members', 'counts'):
    need(k in REG, f'swarm.json has no {k!r}; run python3 swarm/build.py')
CNT, HIVES, MEMBERS, COVER = REG['counts'], REG['hives'], REG['members'], REG['coverage']
need(len(HIVES) == CNT['hives'], 'the hive list and its count disagree')
need(CNT['models'] == 0 and CNT['real_hardware_members'] == 0 and CNT['operators'] == 0 and REG['real_hardware']['operators'] == [],
     'the registry no longer says 0 models, 0 real-hardware members and 0 operators; this page must not be built on that')
need(REG['cell_scheme']['name'] == 'geohash' and REG['cell_scheme']['precision'] == 5, 'the cell scheme is not geohash precision 5')
need(len(MEMBERS) == CNT['members'], 'the member list and its count disagree')
REFUSAL = REG['real_hardware']['refusal']
need(REFUSAL == 'real hardware needs a named human operator; none is configured', 'the refusal sentence changed')
ALPHABET = REG['cell_scheme']['alphabet']

# ---- the router's own code: slices of three source files, byte for byte -----------------------------------------
GEOHASH_SRC = rd('swarm/geohash.mjs')
GEO_SRC = rd('swarm/geo.mjs')
ROUTER_SRC = rd('swarm/router.mjs')
GATE_SRC = rd('swarm/gate.mjs')   # read only for the gate's own hold reason, quoted on the page
m = re.search(r"hold_reason: '([^']+)'", GATE_SRC)
need(m is not None, 'swarm/gate.mjs no longer carries NO_RECORD_RULE.hold_reason')
NO_RECORD_REASON = m.group(1)
need(NO_RECORD_REASON == 'no safety record for this target: held', 'the no-record reason changed')


def slice_between(src, start, end, what, include_end=False):
    i = src.find(start)
    need(i >= 0 and src.count(start) == 1, f'router slice {what}: start anchor {start!r} not found exactly once')
    j = src.find(end, i)
    need(j >= 0, f'router slice {what}: end anchor {end!r} not found after the start')
    if include_end:
        j += len(end)
    return src[i:j]


R_REFUSAL = slice_between(ROUTER_SRC, "export const REAL_HARDWARE_REFUSAL", "\n", 'refusal constant')
R_PARSE = slice_between(ROUTER_SRC, "const ALLOWED = ", "export function createRouter", 'region parser').rstrip('\n')
R_STEPS = slice_between(ROUTER_SRC, "    // 1. real hardware first", "    resolved.targets = targets.map((m) => m.id);", 'resolution steps 1-3', include_end=True)
for name, sl in (('refusal constant', R_REFUSAL), ('region parser', R_PARSE), ('resolution steps', R_STEPS), ('geohash', GEOHASH_SRC), ('geo', GEO_SRC)):
    need('</script' not in sl.lower() and '<!--' not in sl, f'router slice {name} could not sit inside an inline script')
    for bad in ('node:', 'import ', 'readFileSync', 'fetch(', 'XMLHttpRequest', 'WebSocket', 'localStorage'):
        need(bad not in sl, f'router slice {name} reaches {bad!r}; it is not pure enough to embed')
for bad in ('G.', 'AR.', 'log.', 'createGate', 'createArena', 'SwarmAudit'):
    need(bad not in R_STEPS, f'resolution steps 1-3 reach {bad!r}: the gate, the arena or the audit log; they cannot be embedded')
need("REAL_HARDWARE_REFUSAL" in R_REFUSAL and REFUSAL in R_REFUSAL, 'the router constant does not carry the registry refusal')

# ---- strings: every swarm.* key (and nav.page.swarm) non-empty in all 8 locales ----------------------------------
EN_ALL = json.loads((ROOT / 'i18n/locales/en.json').read_text(encoding='utf-8'))
KEYS = sorted(k for k in EN_ALL['strings'] if k.startswith('swarm.'))
need(len(KEYS) > 60, 'the swarm.* keys are missing from i18n/locales/en.json')
I18N = {}
for f in sorted((ROOT / 'i18n/locales').glob('*.json')):
    c = json.loads(f.read_text(encoding='utf-8'))
    s = c['strings']
    miss = [k for k in KEYS + ['nav.page.swarm'] if not isinstance(s.get(k), str) or not s[k].strip()]
    need(not miss, f'locale {f.name} is missing {miss[:5]}')
    I18N[c['locale']] = {'dir': c['dir'], 'strings': {k: s[k] for k in KEYS}}
need(len(I18N) == 8, f'expected 8 locales, found {sorted(I18N)}')
EN = I18N['en']['strings']
I18N_STAMP = hashlib.sha256(json.dumps(I18N, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


def T(k, tag='span', attrs='', **vars):
    need(k in EN, f'unknown key {k}')
    text = EN[k]
    extra = ''
    for name, val in vars.items():
        text = text.replace('{' + name + '}', str(val))
        extra += f' data-n="{E(val)}"'
    return f'<{tag}{attrs}{extra} data-i18n="{k}">{E(text)}</{tag}>'


# ---- geohash: the builder decodes each cell itself; the polygons are what the page draws and the suite re-decodes ----
def gh_bounds(h):
    need(h and all(ch in ALPHABET for ch in h), f'cell {h!r} is not a geohash string')
    la, lo, even = [-90.0, 90.0], [-180.0, 180.0], True
    for ch in h:
        v = ALPHABET.index(ch)
        for b in (16, 8, 4, 2, 1):
            r = lo if even else la
            mid = (r[0] + r[1]) / 2
            if v & b:
                r[0] = mid
            else:
                r[1] = mid
            even = not even
    return la[0], lo[0], la[1], lo[1]


def gh_encode(lat, lon, prec):
    la, lo, even, out, bits, ch = [-90.0, 90.0], [-180.0, 180.0], True, '', 0, 0
    while len(out) < prec:
        r, v = (lo, lon) if even else (la, lat)
        mid = (r[0] + r[1]) / 2
        if v >= mid:
            ch = (ch << 1) | 1
            r[0] = mid
        else:
            ch <<= 1
            r[1] = mid
        even = not even
        bits += 1
        if bits == 5:
            out += ALPHABET[ch]
            bits = ch = 0
    return out


PALETTE = ['#E8A33D', '#41C4D4', '#6FCF97', '#C98BE0', '#F2D16B', '#FF7A6B', '#7FA8FF', '#B8C46A', '#E58AB0']
need(len(PALETTE) >= len(HIVES), 'the hive palette is shorter than the hive list')
HIVE_IDX = {h['id']: i for i, h in enumerate(HIVES)}
feats, pts = [], []
seen_cells = set()
for h in HIVES:
    for cell, why in sorted(h['cells'].items()):
        need(cell not in seen_cells, f'cell {cell} has two owners')
        seen_cells.add(cell)
        s, w, n, e = gh_bounds(cell)
        need(gh_encode((s + n) / 2, (w + e) / 2, len(cell)) == cell, f'cell {cell} does not decode back to itself')
        feats.append({'type': 'Feature', 'properties': {'cell': cell, 'hive': h['id'], 'why': why},
                      'geometry': {'type': 'Polygon', 'coordinates': [[[w, s], [e, s], [e, n], [w, n], [w, s]]]}})
        pts.append({'type': 'Feature', 'properties': {'cell': cell, 'hive': h['id']}, 'geometry': {'type': 'Point', 'coordinates': [(w + e) / 2, (s + n) / 2]}})
need(len(feats) == CNT['cells'], 'the cell polygons and the registry cell count disagree')

# ---- per-hive figures: counted from the registry's own member and coverage lists ---------------------------------
ROBOT_ROLES = sorted({m['role'] for m in MEMBERS if m['kind'] == 'robot'})
SW_KINDS = ('claw', 'advisor', 'crew-role', 'npc')
need({m['role_kind'] for m in MEMBERS if m['kind'] == 'software'} == set(SW_KINDS), 'software role kinds changed; update the table columns')


def hive_figs(h):
    mem = [m for m in MEMBERS if m['hive'] == h['id']]
    cov = [c for c in COVER if c['hive'] == h['id']]
    f = {'campuses': len(h['campuses']), 'cells': len(h['cells']),
         'anchors': sum(1 for c in cov if c['kind'] == 'anchor'), 'sites': sum(1 for c in cov if c['kind'] == 'restoration-site'),
         'claw': sum(1 for m in mem if m.get('role_kind') == 'claw'), 'advisors': sum(1 for m in mem if m.get('role_kind') == 'advisor'),
         'crew': sum(1 for m in mem if m.get('role_kind') == 'crew-role'), 'guides': sum(1 for m in mem if m.get('role_kind') == 'npc'),
         'robots': sum(1 for m in mem if m['kind'] == 'robot'), 'members': len(mem),
         'by_robot': {r: sum(1 for m in mem if m['kind'] == 'robot' and m['role'] == r) for r in ROBOT_ROLES}}
    need(f['members'] == h['counts']['members'] and f['robots'] == h['counts']['robots'] and f['cells'] == h['counts']['cells'],
         f'hive {h["id"]}: counted figures differ from its registry counts')
    need(f['claw'] + f['advisors'] + f['crew'] + f['guides'] == h['counts']['software'], f'hive {h["id"]}: software roles do not add up')
    return f


FIGS = {h['id']: hive_figs(h) for h in HIVES}
TOT = {k: sum(FIGS[h][k] for h in FIGS) for k in ('campuses', 'cells', 'anchors', 'sites', 'claw', 'advisors', 'crew', 'guides', 'robots', 'members')}
need(TOT['cells'] == CNT['cells'] and TOT['members'] == CNT['members'] and TOT['robots'] == CNT['robots'], 'hive totals differ from the registry counts')
need(TOT['anchors'] + TOT['sites'] + TOT['campuses'] == CNT['poses'], 'covered places differ from the registry pose count')
need(TOT['claw'] + TOT['advisors'] + TOT['crew'] + TOT['guides'] == CNT['software'], 'software totals differ from the registry count')

# ---- the data the page script reads --------------------------------------------------------------------------------
CORE_DATA = {
    'source_stamp': REG['source_stamp'], 'region_limits': REG['region_limits'], 'dry_run': {'max_targets': REG['dry_run']['max_targets']},
    'hives': [{'id': h['id'], 'cells': h['cells']} for h in HIVES],
    'members': [({k: m[k] for k in ('id', 'kind', 'role', 'hive', 'lat', 'lon', 'cell')}
                 | ({'simulated': m['simulated'], 'real_hardware': m['real_hardware']} if m['kind'] == 'robot' else {})) for m in MEMBERS],
    'capabilities': REG['capabilities'],
}


def home(hid):
    return next(h for h in HIVES if h['id'] == hid)['home']


bay = home('bay-area')
need('bay-area' in HIVE_IDX and 'chicago' in HIVE_IDX and 'new-orleans' in HIVE_IDX, 'the example commands name a hive the registry no longer has')
LAT, LON = round(bay['lat'], 2), round(bay['lon'], 2)
BOX = [[round(LAT - 0.03, 2), round(LON - 0.03, 2)], [round(LAT - 0.03, 2), round(LON + 0.03, 2)],
       [round(LAT + 0.03, 2), round(LON + 0.03, 2)], [round(LAT + 0.03, 2), round(LON - 0.03, 2)]]
for cap in ('robot.litter-pickup', 'robot.gate-drive', 'robot.rov-survey', 'software.advise-visitor', 'software.schedule-tournament'):
    need(cap in REG['capabilities'], f'capability {cap} is not in the registry')
CMD = lambda i, cap, region, **x: {'schema': 'swarm-command/1', 'id': i, 'capability': cap, 'region': region, **x}
PRESETS = [
    {'id': 'bay', 'key': 'swarm.p.bay', 'command': CMD('demo-bay', 'robot.litter-pickup', {'polygon': BOX}, mode='dry-run', params={'level': 1, 'seed': 3})},
    {'id': 'gate', 'key': 'swarm.p.gate', 'command': CMD('demo-gate', 'robot.gate-drive', {'polygon': BOX}, mode='dry-run', params={'level': 1, 'seed': 3})},
    {'id': 'cells', 'key': 'swarm.p.cells', 'command': CMD('demo-cell', 'software.advise-visitor', {'cells': [home('chicago')['cell']]}, mode='dry-run')},
    {'id': 'prefix', 'key': 'swarm.p.prefix', 'command': CMD('demo-prefix', 'software.schedule-tournament', {'cells': [home('new-orleans')['cell'][:3]]}, mode='dry-run')},
    {'id': 'sea', 'key': 'swarm.p.sea', 'command': CMD('demo-sea', 'robot.rov-survey', {'polygon': [[0, -150], [0, -149], [1, -149], [1, -150]]}, mode='dry-run')},
    {'id': 'device', 'key': 'swarm.p.device', 'command': CMD('demo-device', 'robot.litter-pickup', {'polygon': BOX}, mode='live', hardware='rover-12', operator='example-operator')},
]
for p in PRESETS:
    need(p['key'] in EN, f'preset {p["id"]} has no label key')
DATA = {
    'stamp': None, 'palette': PALETTE, 'hive_ids': [h['id'] for h in HIVES], 'names': {h['id']: h['name'] for h in HIVES},
    'homes': {h['id']: [h['home']['lon'], h['home']['lat']] for h in HIVES},
    'cells': {'type': 'FeatureCollection', 'features': feats}, 'cell_points': {'type': 'FeatureCollection', 'features': pts},
    'robots': {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'properties': {'id': m['id'], 'hive': m['hive'], 'role': m['role']},
                                                           'geometry': {'type': 'Point', 'coordinates': [m['lon'], m['lat']]}}
                                                          for m in MEMBERS if m['kind'] == 'robot']},
    'presets': PRESETS, 'core': CORE_DATA, 'counts': CNT, 'robot_count': CNT['robots'],
}
# the Python modules the build ran (this file and every module of this tree it imported) are files it read, too: observed
for _m in list(sys.modules.values()):
    _f = getattr(_m, '__file__', None)
    if _f and pathlib.Path(_f).resolve().is_relative_to(ROOT) and 'site-packages' not in _f and '__pycache__' not in _f:
        _rel = pathlib.Path(_f).resolve().relative_to(ROOT).as_posix()
        READS.setdefault(_rel, hashlib.sha256(pathlib.Path(_f).read_bytes()).hexdigest())
READS['web/build_swarm.py'] = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
STAMP_SRC = json.dumps({'reads': READS, 'i18n': I18N_STAMP}, sort_keys=True)
STAMP = hashlib.sha256(STAMP_SRC.encode('utf-8')).hexdigest()[:16]
DATA['stamp'] = STAMP


def js_json(o):
    s = json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    return s.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


# ---- the router's code, assembled into one inline module, with the page's thin wrapper around steps 1-3 -------------
def verbatim(name, text):
    return f'/* BEGIN VERBATIM {name} */\n{text.rstrip(chr(10))}\n/* END VERBATIM {name} */'


PREVIEW_HEAD = '''function previewCommand(cmd, reg) {
  const members = new Map(reg.members.map((m) => [m.id, m]));
  const owner = new Map(), rects = new Map();
  for (const h of reg.hives) for (const c of Object.keys(h.cells)) { owner.set(c, h.id); rects.set(c, bounds(c)); }
  const cellsSorted = [...owner.keys()].sort();
  const emptyRes = { cells: [], hives: [], robots_in_region: 0, software_in_region: 0, targets: [] };
  const refuse = (cmd, region, code, reason, extra = {}, resolved = emptyRes) => ({ status: 'refused', refusal: { code, reason, ...extra }, resolved, region, results: [] });
  const outcome = () => {
'''
PREVIEW_TAIL = '''
    // the safety gate and the episode are NOT run here; the expectation is read from the registry capability
    const held = cap.kind === 'robot' && cap.gate_targets.length > 0;
    const results = targets.map((m) => ({ target: m.id, kind: m.kind, hive: m.hive, cell: m.cell, status: held ? 'held-by-gate' : 'dry-run-ok' }));
    return { status: held ? 'held' : 'routed', refusal: null, resolved, region, results, expect: cap.kind === 'software' ? 'software' : held ? 'held' : 'norecord' };
  };
  return outcome();
}
'''
COMMAND_HEAD = """// the command head of an audit row, as the router records it (the hash is the one field left out)
function commandHead(cmd, region) {
  const o = cmd && typeof cmd === 'object';
  return { id: o && typeof cmd.id === 'string' ? cmd.id.slice(0, 64) : null, capability: o && typeof cmd.capability === 'string' ? cmd.capability.slice(0, 64) : null,
    region_kind: region ? region.kind : null, region_cells: region && region.kind === 'cells' ? region.cells : null,
    mode: o && 'mode' in cmd ? (typeof cmd.mode === 'string' ? cmd.mode.slice(0, 32) : '(not a string)') : 'dry-run' };
}
globalThis.SwarmCore = Object.freeze({ previewCommand, commandHead, bounds, encode, realHardwareSignals, REAL_HARDWARE_REFUSAL });"""
CORE_JS = '\n'.join([
    '/* SWARM-CORE BEGIN: the router\'s own region and resolution code, copied byte for byte; no DOM, no network, no storage */',
    verbatim('swarm/geohash.mjs', GEOHASH_SRC),
    verbatim('swarm/geo.mjs', GEO_SRC),
    verbatim('swarm/router.mjs (refusal constant)', R_REFUSAL),
    verbatim('swarm/router.mjs (region parser)', R_PARSE),
    PREVIEW_HEAD + verbatim('swarm/router.mjs (resolution steps 1-3)', R_STEPS) + PREVIEW_TAIL,
    COMMAND_HEAD,
    '/* SWARM-CORE END */',
])
# the verbatim slices sit inside previewCommand's function body: BEGIN/END marker lines are comments, so they are safe there

PAGE_JS = r'''/* SWARM-PAGE BEGIN: the swarm map and the region panel; nothing stored or sent */
(function () {
  'use strict';
  window.__swarmPage = {};
  var D = JSON.parse(document.getElementById('swarm-data').textContent);
  var I = JSON.parse(document.getElementById('swarm-i18n').textContent);
  var C = globalThis.SwarmCore;
  var q = new URLSearchParams(location.search), loc = 'en', want = q.get('lang');
  if (want && Object.prototype.hasOwnProperty.call(I, want)) loc = want;
  else {
    var prefs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || 'en'];
    for (var i = 0; i < prefs.length; i++) { var c0 = String(prefs[i]).slice(0, 2).toLowerCase(); if (Object.prototype.hasOwnProperty.call(I, c0)) { loc = c0; break; } }
  }
  var L = I[loc], S = L.strings;
  function t(k, vars) {
    if (typeof S[k] !== 'string') throw new Error('swarm i18n: ' + loc + ' has no ' + k);
    var s = S[k];
    if (vars) Object.keys(vars).forEach(function (n) { s = s.split('{' + n + '}').join(String(vars[n])); });
    return s;
  }
  document.documentElement.lang = loc; document.documentElement.dir = L.dir;
  document.querySelectorAll('[data-i18n]').forEach(function (el) {
    var n = el.getAttribute('data-n');
    el.textContent = n === null ? t(el.getAttribute('data-i18n')) : t(el.getAttribute('data-i18n'), { n: n });
  });
  document.querySelectorAll('[data-i18n-label]').forEach(function (el) { el.setAttribute('aria-label', t(el.getAttribute('data-i18n-label'))); });
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---- state: the selected hive and cell; selection patches nodes in place, so focus stays where it is ---- */
  var sel = { hive: null, cell: null };
  var pickers = [].slice.call(document.querySelectorAll('[data-pick]'));
  var details = [].slice.call(document.querySelectorAll('[data-detail]'));
  var cellInfo = document.getElementById('swarm-cellinfo');
  var detailHint = document.getElementById('swarm-detail-hint');
  var rows = [].slice.call(document.querySelectorAll('tr[data-hive-row]'));
  var cellFeat = {};
  D.cells.features.forEach(function (f) { cellFeat[f.properties.cell] = f; });
  function rectOf(cell) { var b = C.bounds(cell); return [[b.w, b.s], [b.e, b.n]]; }
  function boundsOf(cells) {
    var w = 180, s = 90, e = -180, n = -90;
    cells.forEach(function (c) { var b = C.bounds(c); w = Math.min(w, b.w); s = Math.min(s, b.s); e = Math.max(e, b.e); n = Math.max(n, b.n); });
    return [[w, s], [e, n]];
  }
  var allCells = Object.keys(cellFeat);
  function cellsOf(hive) { return allCells.filter(function (c) { return cellFeat[c].properties.hive === hive; }); }
  function whyText(cell) {
    return cellFeat[cell].properties.why.map(function (w) { return t('swarm.reason.' + w); }).join(', ');
  }

  var map = null, mapReady = false;
  function paintNow() {
    if (!map || !mapReady) return;
    var hv = sel.hive || '';
    map.setPaintProperty('cells-fill', 'fill-opacity', hv ? ['case', ['==', ['get', 'hive'], hv], 0.6, 0.14] : 0.42);
    map.setPaintProperty('cells-line', 'line-width', hv ? ['case', ['==', ['get', 'hive'], hv], 1.8, 0.5] : 0.9);
    map.setFilter('cell-sel', ['==', ['get', 'cell'], sel.cell || '']);
    window.__swarmPage.paint = { hive: sel.hive, cell: sel.cell };
  }
  function fit(bb) { if (map) map.fitBounds(bb, { padding: 48, maxZoom: 12.5, duration: reduce ? 0 : 700 }); }

  function selectHive(id, opts) {
    sel.hive = id || null; if (!opts || !opts.keepCell) sel.cell = null;
    pickers.forEach(function (b) { b.setAttribute('aria-pressed', String((b.getAttribute('data-pick') || '') === (id || ''))); });
    details.forEach(function (d) { d.hidden = d.getAttribute('data-detail') !== id; });
    detailHint.hidden = !!id;
    rows.forEach(function (r) { r.classList.toggle('on', r.getAttribute('data-hive-row') === id); });
    if (!sel.cell) cellInfo.textContent = t('swarm.map.none');
    paintNow();
    if (!opts || !opts.nofit) fit(id ? boundsOf(cellsOf(id)) : boundsOf(allCells));
    window.__swarmPage.selected = sel.hive;
  }
  function selectCell(cell) {
    var f = cellFeat[cell]; if (!f) return;
    sel.cell = cell;
    cellInfo.textContent = t('swarm.map.cell', { cell: cell, hive: D.names[f.properties.hive], why: whyText(cell) });
    document.querySelectorAll('[data-cellbtn]').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-cellbtn') === cell)); });
    if (sel.hive !== f.properties.hive) selectHive(f.properties.hive, { keepCell: true, nofit: true });
    paintNow();
    if (map) map.fitBounds(rectOf(cell), { padding: 80, maxZoom: 12.5, duration: reduce ? 0 : 600 });
    window.__swarmPage.cell = cell;
  }
  pickers.forEach(function (b) { b.addEventListener('click', function () { selectHive(b.getAttribute('data-pick') || null); }); });
  document.querySelectorAll('[data-cellbtn]').forEach(function (b) { b.addEventListener('click', function () { selectCell(b.getAttribute('data-cellbtn')); }); });
  document.querySelectorAll('[data-pick-link]').forEach(function (a) {
    a.addEventListener('click', function (ev) {
      ev.preventDefault(); var id = a.getAttribute('data-pick-link'); selectHive(id);
      var d = document.getElementById('hive-' + id); if (d) d.scrollIntoView({ block: 'nearest' });
    });
  });

  /* ---- the map: geojson only, on a graticule; no tile, glyph or sprite is requested ---- */
  function tok(n, fb) {
    var v = getComputedStyle(document.body).getPropertyValue('--tc-' + n).trim();
    return /^#[0-9a-fA-F]{6}$/.test(v) ? v : fb;
  }
  var PC = null;
  function colours() { return { bg: tok('plate', '#12181B'), line: tok('line', '#2B383C'), ink: tok('ink', '#E8EDEC'), mark: tok('amber', '#E8A33D') }; }
  function grat(step, lat0, lat1, lon0, lon1) {
    var fs = [], a;
    for (a = lat0; a <= lat1; a += step) fs.push({ type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: [[lon0, a], [lon1, a]] } });
    for (a = lon0; a <= lon1; a += step) fs.push({ type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: [[a, lat0], [a, lat1]] } });
    return { type: 'FeatureCollection', features: fs };
  }
  var empty = { type: 'FeatureCollection', features: [] };
  var hiveColour = ['match', ['get', 'hive']].concat(D.hive_ids.reduce(function (a, id, k) { return a.concat([id, D.palette[k]]); }, []), ['#888888']);
  function startMap() {
    var box = document.getElementById('swarm-map');
    if (typeof maplibregl === 'undefined') throw new Error('maplibre is not loaded');
    PC = colours();
    map = new maplibregl.Map({
      container: box, attributionControl: false, cooperativeGestures: true,
      locale: { 'CooperativeGesturesHandler.MacHelpText': t('swarm.map.coop.mac'), 'CooperativeGesturesHandler.WindowsHelpText': t('swarm.map.coop.win'), 'CooperativeGesturesHandler.MobileHelpText': t('swarm.map.coop.mobile') },
      style: {
        version: 8,
        sources: {
          g5: { type: 'geojson', data: grat(5, 15, 60, -135, -55) }, g05: { type: 'geojson', data: grat(0.5, 25, 50, -125, -65) },
          cells: { type: 'geojson', data: D.cells }, cellpts: { type: 'geojson', data: D.cell_points }, robots: { type: 'geojson', data: D.robots },
          region: { type: 'geojson', data: empty }
        },
        layers: [
          { id: 'bg', type: 'background', paint: { 'background-color': PC.bg } },
          { id: 'g5', type: 'line', source: 'g5', paint: { 'line-color': PC.line, 'line-width': 1 } },
          { id: 'g05', type: 'line', source: 'g05', minzoom: 7, paint: { 'line-color': PC.line, 'line-width': 0.6, 'line-opacity': 0.7 } },
          { id: 'cells-fill', type: 'fill', source: 'cells', paint: { 'fill-color': hiveColour, 'fill-opacity': 0.42 } },
          { id: 'cells-line', type: 'line', source: 'cells', paint: { 'line-color': PC.ink, 'line-width': 0.9, 'line-opacity': 0.85 } },
          { id: 'cell-dots', type: 'circle', source: 'cellpts', paint: { 'circle-color': hiveColour, 'circle-stroke-color': PC.bg, 'circle-stroke-width': 1,
              'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, 3, 8, 4], 'circle-opacity': ['interpolate', ['linear'], ['zoom'], 7, 1, 9, 0], 'circle-stroke-opacity': ['interpolate', ['linear'], ['zoom'], 7, 1, 9, 0] } },
          { id: 'region-fill', type: 'fill', source: 'region', filter: ['==', ['get', 'k'], 'region'], paint: { 'fill-color': PC.mark, 'fill-opacity': 0.12 } },
          { id: 'region-line', type: 'line', source: 'region', filter: ['==', ['get', 'k'], 'region'], paint: { 'line-color': PC.mark, 'line-width': 2.5, 'line-dasharray': [2, 1.5] } },
          { id: 'hit-line', type: 'line', source: 'region', filter: ['==', ['get', 'k'], 'hit'], paint: { 'line-color': PC.mark, 'line-width': 3 } },
          { id: 'cell-sel', type: 'line', source: 'cells', filter: ['==', ['get', 'cell'], ''], paint: { 'line-color': PC.mark, 'line-width': 3.5 } },
          { id: 'robots', type: 'circle', source: 'robots', layout: { visibility: 'none' },
            paint: { 'circle-color': hiveColour, 'circle-radius': 4.5, 'circle-stroke-color': PC.ink, 'circle-stroke-width': 1.2 } }
        ]
      },
      bounds: boundsOf(allCells), fitBoundsOptions: { padding: 40 }
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left');
    D.hive_ids.forEach(function (id, k) {
      var el = document.createElement('div');
      el.className = 'pin'; el.setAttribute('data-pin', id);
      el.innerHTML = '<span class="dot" style="background:' + D.palette[k] + '"></span><span class="lab" lang="en" dir="ltr"></span>';
      el.querySelector('.lab').textContent = D.names[id];
      el.addEventListener('click', function () { selectHive(id); });
      new maplibregl.Marker({ element: el, anchor: 'center' }).setLngLat(D.homes[id]).addTo(map);
    });
    map.on('click', 'cells-fill', function (e) { if (e.features && e.features[0]) selectCell(e.features[0].properties.cell); });
    map.on('mouseenter', 'cells-fill', function () { map.getCanvas().style.cursor = 'pointer'; });
    map.on('mouseleave', 'cells-fill', function () { map.getCanvas().style.cursor = ''; });
    map.once('load', function () { mapReady = true; paintNow(); window.__swarmPage.mapReady = true; });
    var paintStyle = function () {
      if (!mapReady) return;
      PC = colours();
      map.setPaintProperty('bg', 'background-color', PC.bg);
      ['g5', 'g05'].forEach(function (l) { map.setPaintProperty(l, 'line-color', PC.line); });
      map.setPaintProperty('cells-line', 'line-color', PC.ink);
      ['region-fill', 'region-line', 'hit-line', 'cell-sel'].forEach(function (l) { map.setPaintProperty(l, l === 'region-fill' ? 'fill-color' : 'line-color', PC.mark); });
      map.setPaintProperty('robots', 'circle-stroke-color', PC.ink);
      map.setPaintProperty('cell-dots', 'circle-stroke-color', PC.bg);
    };
    new MutationObserver(paintStyle).observe(document.documentElement, { attributes: true, attributeFilter: ['data-style', 'data-theme'] });
    if (window.matchMedia) { var mq = window.matchMedia('(prefers-color-scheme: light)'); if (mq.addEventListener) mq.addEventListener('change', paintStyle); }
  }
  var failBox = document.getElementById('swarm-mapfail');
  try { startMap(); } catch (err) { map = null; failBox.hidden = false; document.getElementById('swarm-map').hidden = true; window.__swarmPage.mapError = String(err && err.message); }
  var robotBox = document.getElementById('swarm-robots');
  robotBox.addEventListener('change', function () { if (map && mapReady) map.setLayoutProperty('robots', 'visibility', robotBox.checked ? 'visible' : 'none'); });

  /* ---- try a region: the router's own resolution, read-only ---- */
  var presetSel = document.getElementById('swarm-preset'), cmdBox = document.getElementById('swarm-cmd'), out = document.getElementById('swarm-out');
  var els = {};
  ['status', 'refusal', 'refusal-row', 'cells', 'hives', 'robots', 'software', 'targets', 'expect', 'audit', 'invalid'].forEach(function (n) { els[n] = document.getElementById('swarm-r-' + n); });
  function setPreset(id) {
    var p = D.presets.filter(function (x) { return x.id === id; })[0];
    cmdBox.value = JSON.stringify(p.command, null, 2);
  }
  function regionGeo(r) {
    var fs = [];
    if (r && r.region) {
      if (r.region.kind === 'polygon') {
        var ring = r.region.ring.map(function (v) { return [v.lng, v.lat]; }); ring.push(ring[0]);
        fs.push({ type: 'Feature', properties: { k: 'region' }, geometry: { type: 'Polygon', coordinates: [ring] } });
      }
    }
    if (r && r.resolved) r.resolved.cells.forEach(function (c) { fs.push(cellFeat[c] ? { type: 'Feature', properties: { k: 'hit' }, geometry: cellFeat[c].geometry } : null); });
    return { type: 'FeatureCollection', features: fs.filter(Boolean) };
  }
  function auditPreview(cmd, r) {
    return {
      schema: 'swarm-audit/1 (preview: not a row)',
      command: C.commandHead(cmd, r.region),
      status: r.status, refusal: r.refusal, resolved: r.resolved, results: r.results,
      provenance: { kind: 'SCRIPTED', model: null, simulation_only: true, real_hardware: 'refused', network: false, registry_stamp: D.core.source_stamp }
    };
  }
  function run() {
    var cmd;
    out.hidden = false;
    try { cmd = JSON.parse(cmdBox.value); } catch (e) {
      els.invalid.hidden = false; els.invalid.textContent = t('swarm.try.invalid');
      document.getElementById('swarm-r-body').hidden = true; window.__swarmPage.last = null;
      if (map && mapReady) map.getSource('region').setData(empty);
      return null;
    }
    els.invalid.hidden = true; document.getElementById('swarm-r-body').hidden = false;
    var r = C.previewCommand(cmd, D.core);
    els.status.textContent = t('swarm.st.' + r.status);
    els.status.setAttribute('data-status', r.status);
    els['refusal-row'].hidden = !r.refusal;
    els.refusal.textContent = r.refusal ? r.refusal.code + ': ' + r.refusal.reason : '';
    els.cells.textContent = r.resolved.cells.length ? r.resolved.cells.join(' ') : t('swarm.try.none');
    els.hives.textContent = r.resolved.hives.length ? r.resolved.hives.map(function (h) { return D.names[h]; }).join(', ') : t('swarm.try.none');
    els.robots.textContent = String(r.resolved.robots_in_region);
    els.software.textContent = String(r.resolved.software_in_region);
    var tg = r.resolved.targets, shown = tg.slice(0, 12);
    els.targets.textContent = tg.length ? shown.join(', ') + (tg.length > shown.length ? ' ' + t('swarm.try.more', { n: tg.length - shown.length }) : '') : t('swarm.try.none');
    els.expect.textContent = r.expect ? t('swarm.try.expect.' + r.expect) : '';
    els.expect.hidden = !r.expect;
    els.audit.textContent = JSON.stringify(auditPreview(cmd, r), null, 2);
    var drawn = regionGeo(r).features.length;
    if (map && mapReady) {
      map.getSource('region').setData(regionGeo(r));
      if (r.resolved.cells.length) map.fitBounds(boundsOf(r.resolved.cells), { padding: 60, maxZoom: 12.5, duration: reduce ? 0 : 600 });
    }
    window.__swarmPage.last = { status: r.status, cells: r.resolved.cells.length, hives: r.resolved.hives, refusal: r.refusal ? r.refusal.code : null, targets: tg.length, drawn: drawn };
    return r;
  }
  presetSel.addEventListener('change', function () { setPreset(presetSel.value); run(); });
  document.getElementById('swarm-run').addEventListener('click', run);
  setPreset(presetSel.value);

  window.__swarmPage = Object.assign(window.__swarmPage || {}, {
    locale: loc, dir: L.dir, hives: D.hive_ids.length, cells: allCells.length, selected: null, cell: null, mapReady: false, mapError: null, last: null,
    select: selectHive, selectCell: selectCell, run: run, preview: function (cmd) { return C.previewCommand(cmd, D.core); },
    rendered: function () { return map && mapReady ? map.queryRenderedFeatures({ layers: ['cells-fill'] }).length : 0; },
    zoom: function () { return map ? map.getZoom() : null; }, moving: function () { return !!map && map.isMoving(); }, centre: function (c) { var b = C.bounds(c); return [(b.w + b.e) / 2, (b.s + b.n) / 2]; }, map: function () { return map; }
  });
  selectHive(null, { nofit: true });
  var h0 = location.hash.match(/^#hive-([a-z0-9-]+)$/);
  if (h0 && D.hive_ids.indexOf(h0[1]) >= 0) selectHive(h0[1]);
})();
/* SWARM-PAGE END */'''

# ---- the page body ------------------------------------------------------------------------------------------------
stats = ''.join(f'<div class="st"><dt>{T(k)}</dt><dd data-swarm-count="{c}">{CNT[c]}</dd></div>' for k, c in (
    ('swarm.s.hives', 'hives'), ('swarm.s.cells', 'cells'), ('swarm.s.poses', 'poses'), ('swarm.s.members', 'members'),
    ('swarm.s.robots', 'robots'), ('swarm.s.software', 'software'), ('swarm.s.caps', 'capabilities'),
    ('swarm.s.models', 'models'), ('swarm.s.hardware', 'real_hardware_members'), ('swarm.s.operators', 'operators')))

HON_KEYS = ('swarm.hon.scripted', 'swarm.hon.sim', 'swarm.hon.hardware', 'swarm.hon.s2r', 'swarm.hon.positions', 'swarm.hon.location', 'swarm.hon.standards', 'swarm.hon.page')
honest = (''.join(f'<li data-swarm-hon="{k.split(".")[-1]}">{T(k)}</li>' for k in HON_KEYS)
          + f'</ul><p>{T("swarm.hon.quoted")}</p><ul class="quotes">'
          + f'<li data-swarm-refusal lang="en" dir="ltr"><q>{E(REFUSAL)}</q> <cite class="muted">swarm/registry/swarm.json real_hardware.refusal</cite></li>'
          + ''.join(f'<li data-swarm-honesty="{E(k)}" lang="en" dir="ltr">{E(v)}</li>' for k, v in REG['honesty'].items()))

pick_btns = (f'<button type="button" class="btn pick" data-pick="" aria-pressed="true">{T("swarm.map.all")}</button>'
             + ''.join(f'<button type="button" class="btn pick" data-pick="{E(h["id"])}" aria-pressed="false">'
                       f'<span class="sw" style="background:{PALETTE[i]}" aria-hidden="true"></span><span lang="en" dir="ltr">{E(h["name"])}</span></button>'
                       for i, h in enumerate(HIVES)))

HEAD_COLS = [('campuses', 'swarm.t.campuses'), ('cells', 'swarm.t.cells'), ('anchors', 'swarm.t.anchors'), ('sites', 'swarm.t.sites'),
             ('claw', 'swarm.t.claw'), ('advisors', 'swarm.t.advisors'), ('crew', 'swarm.t.crew'), ('guides', 'swarm.t.guides'),
             ('robots', 'swarm.t.robots'), ('members', 'swarm.t.members')]
thead = f'<th scope="col">{T("swarm.t.hive")}</th>' + ''.join(f'<th scope="col">{T(k)}</th>' for _, k in HEAD_COLS)
body_rows = ''.join(
    f'<tr data-hive-row="{E(h["id"])}"><th scope="row"><a href="#hive-{E(h["id"])}" data-pick-link="{E(h["id"])}" lang="en" dir="ltr">{E(h["name"])}</a></th>'
    + ''.join(f'<td data-n="{c}">{FIGS[h["id"]][c]}</td>' for c, _ in HEAD_COLS) + '</tr>' for h in HIVES)
tfoot = f'<tr data-hive-row="all"><th scope="row">{T("swarm.t.total")}</th>' + ''.join(f'<td data-n="{c}">{TOT[c]}</td>' for c, _ in HEAD_COLS) + '</tr>'
table = (f'<div class="tw"><table id="swarm-members"><caption class="muted">{T("swarm.t.caption")}</caption>'
         f'<thead><tr>{thead}</tr></thead><tbody>{body_rows}</tbody><tfoot>{tfoot}</tfoot></table></div>')


def detail(i, h):
    f = FIGS[h['id']]
    cov = [c for c in COVER if c['hive'] == h['id']]
    cells = ''.join(
        f'<li><button type="button" class="btn cellbtn" data-cellbtn="{E(c)}" aria-pressed="false"><code>{E(c)}</code> '
        + ' · '.join(f'<span data-i18n="swarm.reason.{E(w)}">{E(EN["swarm.reason." + w])}</span>' for w in why) + '</button></li>'
        for c, why in sorted(h['cells'].items()))
    covers = ''.join(f'<li data-cover="{E(c["ref"])}"><code lang="en" dir="ltr">{E(c["ref"])}</code> <span class="muted">→ <code>{E(c["cell"])}</code></span></li>' for c in cov)
    robots = ''.join(f'<li data-robot-role="{E(r)}"><code lang="en" dir="ltr">{E(r)}</code> <b>{n}</b></li>' for r, n in f['by_robot'].items())
    camp = ', '.join(f'<code>{E(c)}</code>' for c in h['campuses'])
    return (f'<div class="hd" id="hive-{E(h["id"])}" data-detail="{E(h["id"])}" hidden>'
            f'<h3><span class="sw" style="background:{PALETTE[i]}" aria-hidden="true"></span><span lang="en" dir="ltr">{E(h["name"])}</span> '
            f'<span class="tag">SCRIPTED</span></h3>'
            f'<p class="muted">{T("swarm.d.campuses")}: {camp} · {T("swarm.d.home")}: <code>{E(h["home"]["cell"])}</code></p>'
            f'<div class="cols"><section aria-labelledby="hc-{i}"><h4 id="hc-{i}">{T("swarm.d.cells")}</h4><ul class="cells">{cells}</ul></section>'
            f'<section aria-labelledby="hv-{i}"><h4 id="hv-{i}">{T("swarm.d.covers")}</h4><ul class="plain">{covers}</ul>'
            f'<h4>{T("swarm.d.robots")}</h4><ul class="plain">{robots}</ul></section></div></div>')


details = ''.join(detail(i, h) for i, h in enumerate(HIVES))

rules = (f'<ol class="rules">'
         f'<li data-rule="sim">{T("swarm.rule.sim")}</li>'
         f'<li data-rule="hardware">{T("swarm.rule.hardware")} <q lang="en" dir="ltr" data-refusal>{E(REFUSAL)}</q></li>'
         f'<li data-rule="norecord">{T("swarm.rule.norecord")} <q lang="en" dir="ltr" data-norecord>{E(NO_RECORD_REASON)}</q></li>'
         f'<li data-rule="gate">{T("swarm.rule.gate")}</li>'
         f'<li data-rule="nomodel">{T("swarm.rule.nomodel")}</li>'
         f'<li data-rule="audit">{T("swarm.rule.audit")}</li>'
         f'<li data-rule="safety">{T("swarm.rule.safety")}</li></ol>')
unposed = ''.join(f'<li data-unposed="{E(u["ref"])}"><code lang="en" dir="ltr">{E(u["ref"])}</code> <span class="muted" lang="en" dir="ltr">{E(u["why"])}</span></li>' for u in REG['unposed'])
limits = (f'<ul class="plain"><li>{T("swarm.lim.fence")}</li><li>{T("swarm.lim.hives")}</li><li>{T("swarm.lim.placement")}</li><li>{T("swarm.lim.nobase")}</li>'
          f'<li>{T("swarm.lim.unposed")}<ul class="plain">{unposed}</ul></li></ul>')
preset_opts = ''.join(f'<option value="{E(p["id"])}" data-i18n="{E(p["key"])}">{E(EN[p["key"]])}</option>' for p in PRESETS)
links = ''.join(f'<li><a href="{f}">{T(k)}</a></li>' for f, k in (
    ('trade_craft_geomap.html', 'swarm.l.geomap'), ('trade_craft_hive.html', 'swarm.l.hive'), ('trade_craft_robotics.html', 'swarm.l.robotics')))
for f in ('trade_craft_geomap.html', 'trade_craft_hive.html', 'trade_craft_robotics.html'):
    need((HERE / f).exists(), f'link target {f} does not exist')

tcss, tjs = theme('doc')
NAV = nav_html(PAGE, nav_labels('en'))
ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' "
        "fill='%230C1113'/%3E%3Cpath d='M16 5 L25 10.5 V21.5 L16 27 L7 21.5 V10.5 Z' fill='none' stroke='%23E8A33D' stroke-width='2.2' stroke-linejoin='round'/%3E"
        "%3Ccircle cx='16' cy='16' r='3' fill='%2341C4D4'/%3E%3C/svg%3E")

CSS = r'''
body{font:16px/1.6 "IBM Plex Sans",system-ui,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:28px 16px 120px}
.lede{color:var(--tc-muted);max-width:72ch}
main,section,li,p,dd,dt,td,th,q,pre{overflow-wrap:anywhere}
.box{border:1px solid var(--tc-line);border-radius:10px;padding:16px;margin:0 0 20px;background:var(--tc-panel);color:var(--tc-ink);min-inline-size:0}
.box h2{margin:0 0 10px;font-size:22px}
.box h3{margin:14px 0 6px;font-size:18px;display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center}
.box h4{margin:12px 0 6px;font-size:15px}
.stats{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin:0 0 12px}
.st{display:flex;flex-direction:column-reverse}
.st dt{color:var(--tc-muted);font-size:13px}
.st dd{margin:0;font-size:26px;font-weight:700;font-variant-numeric:tabular-nums}
.honesty,.quotes,.plain,.rules{color:var(--tc-muted);padding-inline-start:20px}
.honesty li,.quotes li,.plain li,.rules li{margin:4px 0}
.quotes q,.rules q{color:var(--tc-ink)}
.muted{color:var(--tc-muted);font-size:14px}
.tag{font:600 12px/1.3 ui-monospace,monospace;border:1px solid var(--tc-line);border-radius:4px;padding:2px 6px;color:var(--tc-muted);display:inline-block}
code{font:12.5px ui-monospace,monospace}
a{color:var(--tc-link)}
.btn{min-block-size:44px;padding:0 14px;border-radius:8px;border:1px solid var(--tc-line);background:var(--tc-raised);color:var(--tc-ink);font:inherit;cursor:pointer;display:inline-flex;align-items:center;gap:8px}
.btn[aria-pressed="true"]{border-color:var(--tc-amber);box-shadow:inset 0 0 0 1px var(--tc-amber)}
.picks{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}
.sw{display:inline-block;inline-size:14px;block-size:14px;border-radius:4px;border:1px solid var(--tc-ink);flex:none}
#swarm-map{block-size:clamp(340px,62vh,640px);inline-size:100%;border:1px solid var(--tc-line);border-radius:8px;overflow:hidden;background:var(--tc-plate)}
#swarm-mapfail{border:1px solid var(--tc-line);border-radius:8px;padding:12px}
.maplibregl-ctrl-group button{inline-size:36px;block-size:36px}
.mapnote{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;margin:10px 0 0}
.mapnote label{display:inline-flex;align-items:center;gap:8px;min-block-size:44px}
.mapnote input[type=checkbox]{inline-size:22px;block-size:22px}
.pin{display:flex;align-items:center;gap:6px;cursor:pointer}
.pin .dot{inline-size:16px;block-size:16px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 0 1px #000}
.pin .lab{display:none;font:600 12px/1.2 "IBM Plex Sans",system-ui,sans-serif;background:var(--tc-panel);color:var(--tc-ink);border:1px solid var(--tc-line);border-radius:4px;padding:2px 6px;white-space:nowrap}
@media (min-width:760px){.pin .lab{display:inline}}
#swarm-cellinfo{margin:10px 0 0;min-block-size:1.6em}
.tw{overflow-x:auto;margin:0 0 12px}
table{border-collapse:collapse;min-inline-size:100%;font-variant-numeric:tabular-nums}
caption{text-align:start;padding:0 0 6px}
th,td{border-block-end:1px solid var(--tc-line);padding:6px 8px;text-align:start}
td{text-align:end}
tfoot th,tfoot td{font-weight:700}
tr.on th,tr.on td{background:var(--tc-raised)}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(300px,100%),1fr));gap:12px 24px}
.cells{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:6px}
.cellbtn{min-block-size:44px;padding:4px 10px;font-size:13px;flex-wrap:wrap}
.hd{border-block-start:1px solid var(--tc-line);padding-block-start:6px}
.rules{color:var(--tc-ink)}
.try{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(340px,100%),1fr));gap:16px}
.try label{display:block;font-size:14px;color:var(--tc-muted);margin:0 0 4px}
.try select,.try textarea{inline-size:100%;max-inline-size:100%;box-sizing:border-box;font:inherit;color:var(--tc-ink);background:var(--tc-raised);border:1px solid var(--tc-line);border-radius:8px;padding:8px 10px}
.try select{min-block-size:44px}
.try textarea{font:16px/1.4 ui-monospace,monospace;min-block-size:240px;resize:vertical}
.out dl{display:grid;grid-template-columns:minmax(0,1fr);gap:2px;margin:6px 0}
.out dt{color:var(--tc-muted);font-size:13px;margin-block-start:6px}
.out dd{margin:0}
#swarm-r-status{font-weight:700}
#swarm-r-status[data-status="refused"]{color:var(--tc-warn)}
#swarm-r-status[data-status="held"]{color:var(--tc-warn)}
pre{background:var(--tc-raised);border:1px solid var(--tc-line);border-radius:8px;padding:10px;overflow:auto;max-block-size:340px;font:12.5px/1.45 ui-monospace,monospace;white-space:pre-wrap}
.links a{display:inline-flex;align-items:center;min-block-size:44px}
'''

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="{ICON}">
<title>Omega Swarm map</title>
<script id="style-head-js">{STYLE_HEAD_JS}</script>
<link rel="stylesheet" href="vendor/maplibre/maplibre-gl.css">
<style>{NAV_CSS}</style>
<style id="tc-css">{tcss}</style>
<style>{CSS}</style>
</head>
<body class="tc-theme">
{NAV}
<main class="wrap" id="swarm-main">
<header>
{T("swarm.kicker", "p", ' class="tc-kicker"')}
{T("swarm.title", "h1", ' class="tc-page-title"')}
{T("swarm.lede", "p", ' class="lede"')}
<dl class="stats">{stats}</dl>
</header>
<section class="box" id="swarm-honesty" aria-labelledby="swarm-h-honest"><h2 id="swarm-h-honest" data-i18n="swarm.h.honest">{E(EN["swarm.h.honest"])}</h2>
<ul class="honesty">{honest}</ul></section>
<section class="box" id="swarm-mapbox" aria-labelledby="swarm-h-map"><h2 id="swarm-h-map" data-i18n="swarm.h.map">{E(EN["swarm.h.map"])}</h2>
<p class="muted" id="swarm-maphelp">{T("swarm.map.help")}</p>
<div class="picks" role="group" aria-label="{E(EN["swarm.map.hives"])}" data-i18n-label="swarm.map.hives">{pick_btns}</div>
<div id="swarm-map" role="region" aria-label="{E(EN["swarm.map.label"])}" data-i18n-label="swarm.map.label"></div>
<p id="swarm-mapfail" hidden>{T("swarm.map.fail")}</p>
<div class="mapnote"><label><input type="checkbox" id="swarm-robots"> {T("swarm.map.robots", n=CNT["robots"])}</label></div>
<p id="swarm-cellinfo" aria-live="polite">{E(EN["swarm.map.none"])}</p>
</section>
<section class="box" id="swarm-hives" aria-labelledby="swarm-h-hives"><h2 id="swarm-h-hives" data-i18n="swarm.h.hives">{E(EN["swarm.h.hives"])}</h2>
{table}
<h2 id="swarm-h-detail" data-i18n="swarm.h.detail">{E(EN["swarm.h.detail"])}</h2>
<p class="muted" id="swarm-detail-hint">{T("swarm.d.pick")}</p>
{details}
</section>
<section class="box" id="swarm-rules" aria-labelledby="swarm-h-rules"><h2 id="swarm-h-rules" data-i18n="swarm.h.rules">{E(EN["swarm.h.rules"])}</h2>{rules}</section>
<section class="box" id="swarm-try" aria-labelledby="swarm-h-try"><h2 id="swarm-h-try" data-i18n="swarm.h.try">{E(EN["swarm.h.try"])}</h2>
<p class="muted">{T("swarm.try.lede")}</p>
<div class="try"><div>
<label for="swarm-preset">{T("swarm.try.preset")}</label><select id="swarm-preset">{preset_opts}</select>
<label for="swarm-cmd" style="margin-block-start:10px">{T("swarm.try.cmd")}</label>
<textarea id="swarm-cmd" spellcheck="false" autocomplete="off" autocapitalize="off" dir="ltr" lang="en"></textarea>
<p><button type="button" class="btn" id="swarm-run">{T("swarm.try.run")}</button></p></div>
<div class="out" id="swarm-out" hidden>
<p class="muted" id="swarm-r-invalid" hidden></p>
<div id="swarm-r-body"><dl>
<dt>{T("swarm.try.status")}</dt><dd id="swarm-r-status" role="status" aria-live="polite"></dd>
<div id="swarm-r-refusal-row" hidden><dt>{T("swarm.try.refusal")}</dt><dd id="swarm-r-refusal" lang="en" dir="ltr"></dd></div>
<dt>{T("swarm.try.cells")}</dt><dd id="swarm-r-cells" dir="ltr"></dd>
<dt>{T("swarm.try.hives")}</dt><dd id="swarm-r-hives" lang="en" dir="ltr"></dd>
<dt>{T("swarm.try.robots")}</dt><dd id="swarm-r-robots"></dd>
<dt>{T("swarm.try.software")}</dt><dd id="swarm-r-software"></dd>
<dt>{T("swarm.try.targets")}</dt><dd id="swarm-r-targets" lang="en" dir="ltr"></dd></dl>
<p id="swarm-r-expect" class="muted"></p>
<h3>{T("swarm.try.audit")}</h3>
<pre id="swarm-r-audit" dir="ltr" lang="en" tabindex="0"></pre>
<p class="muted">{T("swarm.try.note")}</p></div></div></div></section>
<section class="box" id="swarm-limits" aria-labelledby="swarm-h-limits"><h2 id="swarm-h-limits" data-i18n="swarm.h.limits">{E(EN["swarm.h.limits"])}</h2>{limits}</section>
<section class="box links" id="swarm-links" aria-labelledby="swarm-h-links"><h2 id="swarm-h-links" data-i18n="swarm.h.links">{E(EN["swarm.h.links"])}</h2><ul>{links}</ul></section>
<p class="muted">swarm/registry/swarm.json · {E(REG["schema"])} · registry stamp <code data-registry-stamp>{E(REG["source_stamp"])}</code> · page stamp <code data-stamp>{E(STAMP)}</code></p>
</main>
<script type="application/json" id="swarm-data">{js_json(DATA)}</script>
<script type="application/json" id="swarm-i18n">{js_json(I18N)}</script>
<script src="vendor/maplibre/maplibre-gl.js"></script>
<script type="module" id="swarm-core">
{CORE_JS}
</script>
<script type="module" id="swarm-page">
{PAGE_JS}
</script>
<script>{tjs}</script>
<script id="style-js">{STYLE_JS}</script>
</body>
</html>
'''
TITLE = 'SmartCiti.X : Trade Craft Academy — ' + EN['swarm.nav']
page = apply_seo(page, PAGE, TITLE, EN['swarm.seo.desc'], 'page')
emit(HERE / 'trade_craft_swarm.html', page,
     f'{CNT["hives"]} hives | {CNT["cells"]} cells | {CNT["members"]} members | stamp {STAMP} | registry {REG["source_stamp"]}')
