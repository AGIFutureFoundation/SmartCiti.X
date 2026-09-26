#!/usr/bin/env python3
"""The spatial fabric's reference consumer: a page that loads the fabric and places it.

WHY THIS FILE EXISTS. `spatial/` publishes the Academy as a static spatial
fabric - `fabric.json` (the manifest: places, anchored content, services,
external origins), `geopose.json` (an OGC GeoPose 1.0 Basic-YPR pose per
campus, anchor and restoration site) and `som.json` (a Scene Object Model
tree, one branch per owner). Its own honesty block says, in its own words,
that nothing has ever opened it: the only consumers it could defend were a
reader of application/geopose+json and its own suite. RP1's Sneeze and
Artemis browsers are not reachable from this build. This generator writes
the bundle's own reference consumer: a page that is handed the three
registries and does what a metaverse browser would do with them - resolves
every pose, plots it on a real WGS84 projection, walks every branch of the
scene graph into a visible tree with its kind and its owner, and lists every
service with its transport and its door. `web/test_fabric.mjs --browser`
opens the page in headless Chromium and counts what was actually placed.

WHAT IT CLAIMS, EXACTLY. The fabric loads in THIS PAGE. It has not been
loaded in Sneeze, Artemis or any other metaverse browser, and the page says
so where a visitor reads first. The registries' honesty block is quoted
verbatim there - that h and heading are UNKNOWN placeholders, that OMBI is
shaped-after and not claimed, that every external origin is not served.

ONE TRUTH PER FACT. Every count on this page is READ from the registry that
owns it and computed here, inside a keyed `data-fig` element; the prose
carries no typed count, and `node brand/figures.mjs .` is the check that
says so. The "placed" figures are not typed either: they ship EMPTY and the
renderer fills each one from the elements it actually drew.

A MISSING FIELD FAILS THE BUILD BY NAME through `need()`. No `.get(k,
default)` and no bare `??` anywhere in this file or in the page's renderer:
a default substituted for a missing registry field is this generator
quietly deciding what a registry meant. The `door` deep link is the one
field this consumer reads by presence rather than by need: a branch that
declares a door gets it rendered as the link, and a branch that has not
declared one yet is rendered with a plain statement that no door is
declared - never with an invented one. A door is a string, repo-relative
like `fabric.entry`, and it is re-based to this page's location the same
way the entry is; any other shape stops the build by name.

WHAT IT REFUSES TO DO. It will not plot a pose whose subject ref it cannot
resolve, place a node under an owner the registry does not give it, render
a provenance word that is not one of this bundle's five tiers, or quote an
honesty sentence that the registry's own records contradict (a pose with a
non-zero height would stop the build, because the quoted block says there
is none). It links only to files the deployable site carries: a registry
path is shown as text, because `.github/assemble_site.sh` ships no
registries and a link to one would be a broken link on the published site.
And it never calls anything here AI-SYNTHESIZED.
"""
import html
import json
import pathlib
import sys
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402


def _root():
    for cand in (HERE, *HERE.parents):
        if (cand / 'spatial').is_dir() and (cand / 'pack').is_dir() and (cand / 'web').is_dir():
            return cand
    raise RuntimeError('cannot locate the packs from ' + str(HERE))


ROOT = _root()

# The registries this page exists to open, named by their repo-relative paths
# on purpose: rnd/build.py scans the generators under web/ for exactly these
# strings, and a page that reads a registry without naming it would close the
# gap in the scan while leaving it open in the bundle.
FABRIC_PATH = 'spatial/registry/fabric.json'
GEOPOSE_PATH = 'spatial/registry/geopose.json'
SOM_PATH = 'spatial/registry/som.json'
MANIFEST_PATH = 'pack/manifest.json'
PAGE_NAME = 'trade_craft_fabric.html'
SUITE = 'web/test_fabric.mjs'


def need(d, k, where):
    """Read a required field, or fail by name."""
    if not isinstance(d, dict):
        raise TypeError(f'{where}: expected an object to read {k!r} from, got {type(d).__name__}')
    if k not in d:
        raise KeyError(f'{where}: required field {k!r} is missing')
    return d[k]


def load(rel):
    return json.load(open(ROOT / rel))


# ---------------------------------------------------------------- registries
fabric_reg = load(FABRIC_PATH)
geopose_reg = load(GEOPOSE_PATH)
som_reg = load(SOM_PATH)
manifest = load(MANIFEST_PATH)

PACK_VERSION = need(manifest, 'pack_version', MANIFEST_PATH)
PRODUCT = need(fabric_reg, 'product', FABRIC_PATH)
BUILT = need(fabric_reg, 'built', FABRIC_PATH)
STAMP = need(fabric_reg, 'source_stamp', FABRIC_PATH)
PACK = need(fabric_reg, 'pack', FABRIC_PATH)
for _path, _reg in ((FABRIC_PATH, fabric_reg), (GEOPOSE_PATH, geopose_reg), (SOM_PATH, som_reg)):
    if need(_reg, 'pack_version', _path) != PACK_VERSION:
        raise AssertionError(f'{_path}: pack_version disagrees with {MANIFEST_PATH}')
    for _k, _v in (('pack', PACK), ('product', PRODUCT), ('built', BUILT), ('source_stamp', STAMP)):
        if need(_reg, _k, _path) != _v:
            raise AssertionError(f'{_path}: {_k} disagrees with {FABRIC_PATH}')

# --- fabric.json: the manifest
FABRIC = need(fabric_reg, 'fabric', FABRIC_PATH)
PLACES = need(fabric_reg, 'places', FABRIC_PATH)
ANCHORED = need(fabric_reg, 'anchored_content', FABRIC_PATH)
SERVICES = need(fabric_reg, 'services', FABRIC_PATH)
EXTERNAL = need(fabric_reg, 'external_origins', FABRIC_PATH)
HONESTY = need(fabric_reg, 'honesty', FABRIC_PATH)
SOURCES = need(fabric_reg, 'sources', FABRIC_PATH)
ENTRY = need(FABRIC, 'entry', f'{FABRIC_PATH}#fabric')
SHAPE = need(FABRIC, 'shape', f'{FABRIC_PATH}#fabric')
IDENTITY = need(FABRIC, 'identity', f'{FABRIC_PATH}#fabric')
HONESTY_KEYS = ('geopose_claimed', 'no_heights_or_headings', 'ombi_not_claimed',
                'static_files_only_no_rmap', 'external_origins', 'not_loaded_in_any_browser')
for _k in HONESTY_KEYS:
    need(HONESTY, _k, f'{FABRIC_PATH}#honesty')
if need(FABRIC, 'poses', f'{FABRIC_PATH}#fabric') != GEOPOSE_PATH:
    raise AssertionError(f'{FABRIC_PATH}#fabric.poses does not name {GEOPOSE_PATH}')
if need(FABRIC, 'scene_graph', f'{FABRIC_PATH}#fabric') != SOM_PATH:
    raise AssertionError(f'{FABRIC_PATH}#fabric.scene_graph does not name {SOM_PATH}')

# --- geopose.json: the poses
ENCODING = need(geopose_reg, 'encoding', GEOPOSE_PATH)
MEDIA_TYPE = need(geopose_reg, 'media_type', GEOPOSE_PATH)
CRS = need(geopose_reg, 'crs', GEOPOSE_PATH)
COUNTS = need(geopose_reg, 'counts', GEOPOSE_PATH)
POSES = need(geopose_reg, 'poses', GEOPOSE_PATH)
UNPOSED = need(geopose_reg, 'unposed', GEOPOSE_PATH)
if need(geopose_reg, 'honesty', GEOPOSE_PATH) != HONESTY:
    raise AssertionError(f'{GEOPOSE_PATH}#honesty is not the same block as {FABRIC_PATH}#honesty')

# --- som.json: the scene graph
SOM_SHAPE = need(som_reg, 'shape', SOM_PATH)
SOM_ROOT = need(som_reg, 'root', SOM_PATH)
INVARIANTS = need(som_reg, 'invariants', SOM_PATH)
BRANCHES = need(SOM_ROOT, 'branches', f'{SOM_PATH}#root')
COMPOSITION = need(SOM_ROOT, 'composition', f'{SOM_PATH}#root')
if need(som_reg, 'honesty', SOM_PATH) != HONESTY:
    raise AssertionError(f'{SOM_PATH}#honesty is not the same block as {FABRIC_PATH}#honesty')
if SOM_SHAPE != SHAPE:
    raise AssertionError(f'{SOM_PATH}#shape is not the same sentence as {FABRIC_PATH}#fabric.shape')

# ------------------------------------------------------------------- provenance
# The closed tier set this bundle uses. AI-SYNTHESIZED is deliberately not in
# it: it belongs to orbis/ and describes generated video. A tier is rendered
# only as the `data-tier` attribute of a `.prov` chip or of a plotted pose,
# so there is exactly one kind of place on this page where a word claims to
# be a provenance tier and exactly one place a check has to look.
TIERS_PROV = ('RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED', 'SCRIPTED')


def tier(word, where):
    if word not in TIERS_PROV:
        raise ValueError(f'{where}: provenance {word!r} is not one of {", ".join(TIERS_PROV)}')
    return word


# ------------------------------------------------------- the poses, validated
# Every pose must be exactly the Basic-YPR shape the honesty block claims, and
# every one must carry the zero placeholders the block says it carries. A
# pose that broke either would make the quoted sentence false on this page,
# so it stops the build by name instead.
POSE_BY_REF = {}
N_PLACEHOLDER = 0
KIND_COUNTS = {}
for _i, _p in enumerate(POSES):
    _w = f'{GEOPOSE_PATH}#poses[{_i}]'
    _s = need(_p, 'subject', _w)
    _ref = need(_s, 'ref', _w + '.subject')
    for _k in ('kind', 'id', 'name', 'campus'):
        need(_s, _k, _w + '.subject')
    if _ref in POSE_BY_REF:
        raise AssertionError(f'{_w}: subject ref {_ref!r} is declared twice')
    _gp = need(_p, 'geopose', _w)
    _pos = need(_gp, 'position', _w + '.geopose')
    _ori = need(_gp, 'orientation', _w + '.geopose')
    if sorted(_pos) != ['h', 'lat', 'lon'] or sorted(_ori) != ['pitch', 'roll', 'yaw']:
        raise AssertionError(f'{_w}: not the Basic-YPR shape {{position:{{lat,lon,h}}, orientation:{{yaw,pitch,roll}}}}')
    for _k in ('lat', 'lon', 'h'):
        if not isinstance(_pos[_k], (int, float)):
            raise TypeError(f'{_w}.geopose.position.{_k} is not a number')
    _prov = need(_p, 'provenance', _w)
    tier(need(_prov, 'position_horizontal', _w + '.provenance'), _w + '.provenance.position_horizontal')
    need(_prov, 'source', _w + '.provenance')
    need(_prov, 'h_provenance', _w + '.provenance')
    need(_prov, 'orientation_provenance', _w + '.provenance')
    if _pos['h'] == 0 and _ori['yaw'] == 0 and _ori['pitch'] == 0 and _ori['roll'] == 0:
        N_PLACEHOLDER += 1
    else:
        raise AssertionError(f'{_w}: carries a non-zero h or heading, and {FABRIC_PATH}#honesty.'
                             f'no_heights_or_headings says every pose emits zero placeholders')
    POSE_BY_REF[_ref] = _p
    KIND_COUNTS[_s['kind']] = (KIND_COUNTS[_s['kind']] + 1) if _s['kind'] in KIND_COUNTS else 1

N_POSES = len(POSES)
N_UNPOSED = len(UNPOSED)
for _i, _u in enumerate(UNPOSED):
    _w = f'{GEOPOSE_PATH}#unposed[{_i}]'
    need(need(_u, 'subject', _w), 'ref', _w + '.subject')
    need(_u, 'why', _w)
_wc = f'{GEOPOSE_PATH}#counts'
for _field, _have in (('total', N_POSES), ('unposed', N_UNPOSED),
                      ('campuses', KIND_COUNTS['campus'] if 'campus' in KIND_COUNTS else 0),
                      ('anchors', KIND_COUNTS['anchor'] if 'anchor' in KIND_COUNTS else 0),
                      ('restoration_sites', KIND_COUNTS['restoration-site'] if 'restoration-site' in KIND_COUNTS else 0)):
    if need(COUNTS, _field, _wc) != _have:
        raise AssertionError(f'{_wc}.{_field} says {COUNTS[_field]}, the records count {_have}')


def resolve(ref, where):
    if ref not in POSE_BY_REF:
        raise KeyError(f'{where}: geopose ref {ref!r} resolves to no pose in {GEOPOSE_PATH}')
    return POSE_BY_REF[ref]


# -------------------------------------------------------------- the doors
# A `door` is a deep link a branch (or a node, place, service or content
# record) declares into the running site. This consumer reads it by
# PRESENCE: a record without one is rendered as "no door declared", and a
# record with one gets exactly that door - a string, or an object whose
# `href` is the string (fabric.json writes {page, param, value, href}; the
# href is the one field this consumer follows and the rest are shown as the
# registry's own words). Any other shape stops the build by name, because a
# door this consumer cannot follow is not a door it may draw. A door is
# written the way every other
# path in the registries is written, repo-relative (`web/x.html?hall=...`),
# so it is resolved from THIS page's location the same way `fabric.entry`
# is: the file it lands on must exist under the repo, and the href the page
# carries is the same path relative to web/. The registry's own string is
# shown as the link text; the href is not invented, it is that string
# re-based. DOOR_HREF is keyed by the registry path of the record, which is
# the key the renderer must use to find it - a renderer that reads `door`
# raw would write a web/web/ link.
DOOR_HREF = {}      # registry path of the record -> page-relative href
DOOR_REFUSED = {}   # registry path of the record -> the registry's own why_no_door


def door_of(rec, where):
    """Three states, each rendered as itself: absent (no door declared), null
    with a why_no_door (the registry refuses one, and says why), or a door
    this consumer can follow. A null without a reason, or any other shape,
    stops the build by name."""
    if 'door' not in rec:
        return None
    d = rec['door']
    if d is None:
        why = need(rec, 'why_no_door', where)
        if not isinstance(why, str) or not why:
            raise TypeError(f'{where}.why_no_door is not a sentence')
        if where in DOOR_REFUSED:
            raise AssertionError(f'{where}: door read twice')
        DOOR_REFUSED[where] = why
        return None
    if isinstance(d, dict):
        d = need(d, 'href', where + '.door')
    if not isinstance(d, str) or not d:
        raise TypeError(f'{where}.door: a door is a non-empty string href, or an object carrying one, '
                        f'got {type(d).__name__}')
    if d.startswith(('http://', 'https://')):
        href = d
    else:
        u = urllib.parse.urlparse(d)
        if u.path.startswith('/'):
            raise ValueError(f'{where}.door: {d!r} is absolute; a door is repo-relative like {ENTRY!r}')
        target = (ROOT / u.path).resolve()
        if not target.is_file():
            raise FileNotFoundError(f'{where}.door: {d!r} lands on no file under the repo')
        try:
            rel = pathlib.Path(u.path).relative_to('web').as_posix()
        except ValueError:
            raise ValueError(f'{where}.door: {d!r} is not under web/, which is all the published site carries')
        href = rel + (('?' + u.query) if u.query else '') + (('#' + u.fragment) if u.fragment else '')
    if where in DOOR_HREF:
        raise AssertionError(f'{where}: door read twice')
    DOOR_HREF[where] = href
    return href


# ------------------------------------------------------ the scene graph, walked
# Per-branch ownership is the SOM's one real idea and the only thing this page
# could get wrong in a way that matters: a place, content or service drawn
# under an owner that does not serve it. So the walk asserts it here, on the
# same records the renderer will draw, and stops if it does not hold.
N_EXTERNAL_BRANCHES = 0
N_FABRIC_NODES = 0
N_EXTERNAL_NODES = 0
N_NODES_POSED = 0
N_NODES_UNPOSED = 0
UNPLACED_WHY = {}   # node name -> the registry's own reason it has no pose
BRANCH_DOORS = {}   # branch id -> href, for branches that declare one
for _bi, _b in enumerate(BRANCHES):
    _w = f'{SOM_PATH}#root.branches[{_bi}]'
    _bid = need(_b, 'id', _w)
    _origin = need(_b, 'origin', _w)
    need(_b, 'owner', _w)
    _served = need(_b, 'served_by_this_fabric', _w)
    for _t in need(_b, 'provenance_tiers', _w):
        tier(_t, _w + '.provenance_tiers')
    _kids = need(_b, 'children', _w)
    if _origin == 'external':
        N_EXTERNAL_BRANCHES += 1
        if _served is not False:
            raise AssertionError(f'{_w}: an external branch claims served_by_this_fabric')
    elif _origin == 'this fabric':
        if _served is not True:
            raise AssertionError(f'{_w}: this fabric\'s own branch is not served_by_this_fabric')
    else:
        raise ValueError(f'{_w}: origin {_origin!r} is neither "this fabric" nor "external"')
    _href = door_of(_b, _w)
    if _href is not None:
        BRANCH_DOORS[_bid] = _href
    for _ci, _c in enumerate(_kids):
        _cw = f'{_w}.children[{_ci}]'
        _kind = need(_c, 'kind', _cw)
        _name = need(_c, 'name', _cw)
        tier(need(_c, 'provenance', _cw), _cw + '.provenance')
        if need(_c, 'served_by_this_fabric', _cw) != _served:
            raise AssertionError(f'{_cw}: served_by_this_fabric disagrees with its own branch')
        if _origin == 'external' and _kind in ('place', 'content', 'service'):
            raise AssertionError(f'{_cw}: a {_kind} node sits under an external branch')
        _ref = need(_c, 'geopose', _cw)
        if _ref is None:
            N_NODES_UNPOSED += 1
            if 'why_no_geopose' in _c:
                UNPLACED_WHY[_name] = _c['why_no_geopose']
            elif _kind == 'content':
                _rec = [a for a in ANCHORED
                        if need(a, 'scene', f'{FABRIC_PATH}#anchored_content[]') == _name]
                if len(_rec) != 1:
                    raise KeyError(f'{_cw}: content node {_name!r} has no single anchored_content record in {FABRIC_PATH}')
                UNPLACED_WHY[_name] = need(_rec[0], 'why_unanchored', f'{FABRIC_PATH}#anchored_content[scene={_name}]')
            elif _kind == 'export':
                # the export door's own record in the manifest holds its reason
                _ed = need(fabric_reg, 'export_door', FABRIC_PATH)
                if need(_ed, 'id', f'{FABRIC_PATH}#export_door') != _name:
                    raise KeyError(f'{_cw}: export node {_name!r} is not {FABRIC_PATH}#export_door.id')
                if need(_ed, 'anchored_at', f'{FABRIC_PATH}#export_door') is not None:
                    raise AssertionError(f'{_cw}: no geopose, but {FABRIC_PATH}#export_door.anchored_at is set')
                UNPLACED_WHY[_name] = need(_ed, 'why_unanchored', f'{FABRIC_PATH}#export_door')
            else:
                raise KeyError(f'{_cw}: no geopose and no why_no_geopose - this consumer will not place it silently')
        else:
            resolve(_ref, _cw)
            N_NODES_POSED += 1
        door_of(_c, _cw)
    if _origin == 'external':
        N_EXTERNAL_NODES += len(_kids)
    else:
        N_FABRIC_NODES += len(_kids)

N_BRANCHES = len(BRANCHES)
N_NODES = N_FABRIC_NODES + N_EXTERNAL_NODES
_ic = need(INVARIANTS, 'counts', f'{SOM_PATH}#invariants')
for _field, _have in (('branches', N_BRANCHES), ('external_branches', N_EXTERNAL_BRANCHES),
                      ('fabric_nodes', N_FABRIC_NODES)):
    if need(_ic, _field, f'{SOM_PATH}#invariants.counts') != _have:
        raise AssertionError(f'{SOM_PATH}#invariants.counts.{_field} says {_ic[_field]}, the tree walks to {_have}')
N_DOORS_DECLARED = len(BRANCH_DOORS)
N_DOORS_UNDECLARED = N_BRANCHES - N_DOORS_DECLARED

# --------------------------------------------- the manifest's lists, validated
for _i, _pl in enumerate(PLACES):
    _w = f'{FABRIC_PATH}#places[{_i}]'
    for _k in ('id', 'name', 'kind', 'districts', 'halls', 'walk', 'walk_why'):
        need(_pl, _k, _w)
    resolve(need(_pl, 'geopose', _w), _w)
    door_of(_pl, _w)
for _i, _sv in enumerate(SERVICES):
    _w = f'{FABRIC_PATH}#services[{_i}]'
    for _k in ('id', 'kind', 'name', 'registry', 'transport'):
        need(_sv, _k, _w)
    tier(need(_sv, 'provenance', _w), _w + '.provenance')
    resolve(need(_sv, 'anchored_at', _w), _w)
    if 'also_at' in _sv:
        for _a in _sv['also_at']:
            resolve(_a, _w + '.also_at')
    if not (ROOT / need(_sv, 'registry', _w)).is_file():
        raise FileNotFoundError(f'{_w}.registry names a file that does not exist')
    door_of(_sv, _w)
N_UNANCHORED = 0
for _i, _a in enumerate(ANCHORED):
    _w = f'{FABRIC_PATH}#anchored_content[{_i}]'
    for _k in ('export', 'scene', 'file', 'format', 'produced_on_demand', 'how'):
        need(_a, _k, _w)
    tier(need(_a, 'provenance', _w), _w + '.provenance')
    _at = need(_a, 'anchored_at', _w)
    if _at is None:
        need(_a, 'why_unanchored', _w)
        N_UNANCHORED += 1
    else:
        resolve(_at, _w)
    door_of(_a, f'{FABRIC_PATH}#anchored_content[{_i}]')
for _i, _e in enumerate(EXTERNAL):
    _w = f'{FABRIC_PATH}#external_origins[{_i}]'
    for _k in ('operator', 'kind', 'origin', 'note'):
        need(_e, _k, _w)
    if need(_e, 'served_by_this_fabric', _w) is not False:
        raise AssertionError(f'{_w}: served_by_this_fabric is not false, and {FABRIC_PATH}#honesty.'
                             f'external_origins says it is false on every one')
    for _gp in need(_e, 'geoposes', _w):
        resolve(_gp, _w + '.geoposes')
    for _t in need(_e, 'provenance', _w):
        tier(_t, _w + '.provenance')
if not (ROOT / ENTRY).is_file():
    raise FileNotFoundError(f'{FABRIC_PATH}#fabric.entry names a file that does not exist')
ENTRY_HREF = pathlib.Path(ENTRY).relative_to('web').as_posix() if ENTRY.startswith('web/') else ENTRY

N_PLACES = len(PLACES)
N_ANCHORED = len(ANCHORED)
N_SERVICES = len(SERVICES)
N_EXTERNAL = len(EXTERNAL)

# ------------------------------------------------------------------ payload
# The registries, handed to the page in their own shape. The poses and the
# scene graph go across VERBATIM - a consumer that reshaped its input would
# be placing something other than the fabric - and the check reads them back
# out and compares them to the files.
DATA = {
    'paths': {'fabric': FABRIC_PATH, 'geopose': GEOPOSE_PATH, 'som': SOM_PATH},
    'stamp': {'pack': PACK, 'pack_version': PACK_VERSION, 'built': BUILT, 'source_stamp': STAMP},
    'fabric': FABRIC,
    'places': PLACES,
    'services': SERVICES,
    'externalOrigins': EXTERNAL,
    'anchored': ANCHORED,
    'honesty': HONESTY,
    'geopose': {'encoding': ENCODING, 'media_type': MEDIA_TYPE, 'crs': CRS, 'counts': COUNTS,
                'poses': POSES, 'unposed': UNPOSED},
    'som': {'shape': SOM_SHAPE, 'root': SOM_ROOT, 'invariants': INVARIANTS},
    'unplacedWhy': UNPLACED_WHY,
    'doorHref': DOOR_HREF,
    'doorRefused': DOOR_REFUSED,
    'entryHref': ENTRY_HREF,
}
PAYLOAD = json.dumps(DATA, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/')

E = html.escape
F = lambda x: f'{x:,}'  # noqa: E731

# ------------------------------------------------------------------------ html
# The figures, each in an element of its own and keyed by a stable `data-fig`
# name. A check recomputes the value from the registry and reads it back out
# of THIS attribute - never out of a sentence. Each label says what the
# number counts, because a quantity standing in for a different quantity is
# how this bundle's last four page faults got in.
FIGS_SPEC = (
    ('places', N_PLACES, 'places this fabric serves'),
    ('anchored-content', N_ANCHORED, 'anchored content records (.glb, produced on demand)'),
    ('services', N_SERVICES, 'services, all in-page'),
    ('external-origins', N_EXTERNAL, 'external origins, none served here'),
    ('poses', N_POSES, 'GeoPoses (OGC GeoPose 1.0 Basic-YPR)'),
    ('poses-h-placeholder', N_PLACEHOLDER, 'of those poses with h = 0 and yaw = pitch = roll = 0 as UNKNOWN placeholders'),
    ('unposed', N_UNPOSED, 'subjects with no pose, by the registry\'s own refusal'),
    ('branches', N_BRANCHES, 'SOM branches, one per owner'),
    ('external-branches', N_EXTERNAL_BRANCHES, 'of those branches owned by an external origin'),
    ('fabric-nodes', N_FABRIC_NODES, 'nodes under this fabric\'s own branch'),
    ('external-nodes', N_EXTERNAL_NODES, 'nodes under external branches'),
    ('nodes-posed', N_NODES_POSED, 'nodes whose geopose ref resolves to a pose'),
    ('nodes-unposed', N_NODES_UNPOSED, 'nodes with no pose, each with the registry\'s reason'),
    ('doors-declared', N_DOORS_DECLARED, 'branches that declare a door (deep link)'),
    ('doors-undeclared', N_DOORS_UNDECLARED, 'branches with no door declared yet'),
    ('doors-anywhere', len(DOOR_HREF), 'doors this page can follow, on any record - branch, node, place, service or content'),
    ('doors-refused', len(DOOR_REFUSED), 'records whose door is null with the registry\'s own why_no_door'),
)
FIGS = ''.join(
    f'<div class="fig" data-fig="{E(key)}"><b>{E(F(n))}</b><span>{E(lab)}</span></div>'
    for key, n, lab in FIGS_SPEC)

# Every field of the block, in the registry's own order - not only the named
# ones: a field the registry adds later is part of what it says about itself,
# and a page that quoted a fixed subset would be editing the block.
# A field that is a sentence is quoted as the sentence; a field that is a
# record (the reachability probe is one) is quoted as its own JSON, verbatim
# and unabridged, in a <pre> inside the same keyed item.


def honesty_item(k):
    v = HONESTY[k]
    if isinstance(v, str):
        return f'<li data-honesty="{E(k)}" data-honesty-shape="sentence"><b>{E(k)}</b>{E(v)}</li>'
    return (f'<li data-honesty="{E(k)}" data-honesty-shape="json"><b>{E(k)}</b>'
            f'<pre class="hj">{E(json.dumps(v, indent=1, ensure_ascii=False))}</pre></li>')


HONESTY_ITEMS = ''.join(honesty_item(k) for k in HONESTY)


def door_markup(rec, where_path):
    """A door as a link, the registry's own refusal, or the plain statement that none is declared."""
    if 'door' in rec and rec['door'] is None:
        if where_path not in DOOR_REFUSED:
            raise KeyError(f'{where_path}: door_markup reached a refused door door_of never validated')
        return (f'<span class="nodoor" data-door-refused="{E(where_path)}">no door - '
                f'{E(DOOR_REFUSED[where_path])}</span>')
    if 'door' in rec:
        if where_path not in DOOR_HREF:
            raise KeyError(f'{where_path}: door_markup reached a door door_of never validated')
        d = rec['door']
        shown = d if isinstance(d, str) else d['href']
        return (f'<a data-door="{E(where_path)}" href="{E(DOOR_HREF[where_path])}">'
                f'{E(shown)}</a>')
    return (f'<span class="nodoor" data-door-undeclared="{E(where_path)}">no door declared in '
            f'<code>{E(where_path.split("#")[0])}</code></span>')


def pose_cells(ref):
    p = POSE_BY_REF[ref]
    pos = p['geopose']['position']
    return (f'<code>{E(ref)}</code> <span class="ll">{E(str(pos["lat"]))}, {E(str(pos["lon"]))}</span>')


PLACE_ROWS = ''.join(
    f'<tr data-place="{E(pl["id"])}"><td class="k">{E(pl["name"])}</td>'
    f'<td><code>{E(pl["id"])}</code><br><span class="muted">{E(pl["kind"])}</span></td>'
    f'<td>{pose_cells(pl["geopose"])}</td>'
    f'<td>{"".join(f"<span class=chip>{E(d)}</span>" for d in pl["districts"]) or "<span class=muted>none</span>"}</td>'
    f'<td class="num">{E(F(pl["halls"]))}</td>'
    f'<td>{"walkable" if pl["walk"] else "not walkable"}<br><span class="muted">{E(pl["walk_why"])}</span></td>'
    f'<td>{door_markup(pl, f"{FABRIC_PATH}#places[{i}]")}</td></tr>'
    for i, pl in enumerate(PLACES))


def service_where(sv):
    at = [sv['anchored_at']] + (list(sv['also_at']) if 'also_at' in sv else [])
    return '<br>'.join(f'<code>{E(a)}</code>' for a in at)


def service_extra(sv):
    common = {'id', 'kind', 'name', 'registry', 'transport', 'anchored_at', 'also_at', 'provenance', 'door'}
    bits = []
    for k in sv:
        if k in common:
            continue
        v = sv[k]
        if isinstance(v, (str, int, float, bool)):
            bits.append(f'<b>{E(k)}</b> {E(str(v))}')
        elif isinstance(v, list):
            bits.append(f'<b>{E(k)}</b> {E(F(len(v)))} entries')
        else:
            bits.append(f'<b>{E(k)}</b> {E(json.dumps(v, ensure_ascii=False))}')
    return '<br>'.join(bits)


SERVICE_ROWS = ''.join(
    f'<tr data-service="{E(sv["id"])}"><td class="k">{E(sv["name"])}<br><code>{E(sv["id"])}</code></td>'
    f'<td>{E(sv["kind"])}</td>'
    f'<td data-transport>{E(sv["transport"])}</td>'
    f'<td>{service_where(sv)}</td>'
    f'<td><span class="prov" data-tier="{E(sv["provenance"])}">{E(sv["provenance"])}</span></td>'
    f'<td><code>{E(sv["registry"])}</code><br><span class="muted">{service_extra(sv)}</span></td>'
    f'<td>{door_markup(sv, f"{FABRIC_PATH}#services[{i}]")}</td></tr>'
    for i, sv in enumerate(SERVICES))

EXTERNAL_ROWS = ''.join(
    f'<tr data-external="{i}" data-served="{"true" if e["served_by_this_fabric"] else "false"}">'
    f'<td class="k">{E(e["operator"])}</td><td>{E(e["kind"])}</td>'
    f'<td><span class="chip notserved">not served by this fabric</span></td>'
    f'<td>{"<br>".join(f"<code>{E(g)}</code>" for g in e["geoposes"]) or "<span class=muted>no pose</span>"}'
    f'{"".join(f"<br><span class=muted>unposed: <code>{E(u)}</code></span>" for u in (e["unposed"] if "unposed" in e else []))}</td>'
    f'<td>{"".join(f"<span class=prov data-tier={E(t)}>{E(t)}</span>" for t in e["provenance"]) or "<span class=muted>none</span>"}</td>'
    f'<td class="muted">{E(e["note"])}</td></tr>'
    for i, e in enumerate(EXTERNAL))

POSE_ROWS = ''.join(
    f'<tr data-pose-row="{E(p["subject"]["ref"])}"><td><code>{E(p["subject"]["ref"])}</code></td>'
    f'<td>{E(p["subject"]["kind"])}</td><td class="k">{E(p["subject"]["name"])}</td>'
    f'<td class="num" data-lat>{E(str(p["geopose"]["position"]["lat"]))}</td>'
    f'<td class="num" data-lon>{E(str(p["geopose"]["position"]["lon"]))}</td>'
    f'<td class="num">{E(str(p["geopose"]["position"]["h"]))} <span class="unk">UNKNOWN</span></td>'
    f'<td class="num">{E(str(p["geopose"]["orientation"]["yaw"]))} / {E(str(p["geopose"]["orientation"]["pitch"]))} / '
    f'{E(str(p["geopose"]["orientation"]["roll"]))} <span class="unk">UNKNOWN</span></td>'
    f'<td><span class="prov" data-tier="{E(p["provenance"]["position_horizontal"])}">{E(p["provenance"]["position_horizontal"])}</span></td>'
    f'<td class="muted">{E(p["provenance"]["source"])}</td></tr>'
    for p in POSES)

UNPOSED_ITEMS = ''.join(
    f'<li data-unposed="{E(u["subject"]["ref"])}"><code>{E(u["subject"]["ref"])}</code> — '
    f'{E(u["subject"]["name"])}<br><span class="muted">{E(u["why"])}</span></li>' for u in UNPOSED)

def anchored_at_cell(a):
    if a['anchored_at'] is None:
        return f'<span class=muted>{E(a["why_unanchored"])}</span>'
    return f'<code>{E(a["anchored_at"])}</code>'


ANCHORED_ROWS = ''.join(
    f'<tr data-anchored="{E(a["scene"])}"><td class="k">{E(a["scene"])}</td><td><code>{E(a["file"])}</code></td>'
    f'<td>{E(a["format"])}</td>'
    f'<td>{anchored_at_cell(a)}</td>'
    f'<td>{"on demand" if a["produced_on_demand"] else "on disk"}</td>'
    f'<td><span class="prov" data-tier="{E(a["provenance"])}">{E(a["provenance"])}</span></td>'
    f'<td>{door_markup(a, f"{FABRIC_PATH}#anchored_content[{i}]")}</td></tr>'
    for i, a in enumerate(ANCHORED))

SOURCE_ITEMS = ''.join(
    f'<li><b>{E(s["what"])}</b>'
    + (f'<br><a href="{E(s["url"])}" rel="noopener">{E(s["url"])}</a>' if 'url' in s else '')
    + (f'<br><span class="muted">{E(s["how"])}</span>' if 'how' in s else '')
    + f'<br><span class="muted">{E(s["provenance"])}</span></li>'
    for s in SOURCES)

READS = ''.join(f'<li><code>{E(p)}</code> — {E(why)}</li>' for p, why in (
    (FABRIC_PATH, 'the manifest: places, anchored content, services, external origins, the honesty block and the sources'),
    (GEOPOSE_PATH, 'every pose, verbatim, with its provenance sidecar'),
    (SOM_PATH, 'the scene graph: every branch, its owner, and every node under it'),
    (MANIFEST_PATH, 'the pack version the three registries must agree with'),
))

# `door_of` above is the validating reader and `door_markup` re-reads the
# same field by presence, then takes the href from the map `door_of` filled
# under the same registry path - so the two cannot disagree about which
# records declare one, and a record `door_markup` sees that `door_of` did not
# is a KeyError, not a link.

CSS = r'''
:root{
  --plate:#12181B; --panel:#182023; --sunk:#0C1113; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --mark-ink:#12181B; --steel:#41C4D4;
  --good:#5CB584; --crit:#E07C68; --warn:#E8A33D;
}
*{box-sizing:border-box}
body{margin:0;background:var(--plate);color:var(--ink);
  font:14px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;padding:0 18px}
.wrap{max-width:1080px;margin:0 auto}
a{color:var(--steel)}
header.page{padding:40px 0 10px;border-bottom:3px solid var(--mark)}
header.page h1{font:700 34px/1.1 "Barlow Condensed",system-ui,sans-serif;margin:0}
header.page h1 .x{color:var(--mark)}
header.page p{color:var(--muted);margin:6px 0 14px}
h2{font:700 22px/1.2 "Barlow Condensed",system-ui,sans-serif;margin:34px 0 10px;
  color:var(--mark);letter-spacing:.02em}
h3{font:700 18px/1.25 "Barlow Condensed",system-ui,sans-serif;margin:18px 0 6px}
section{margin:0 0 10px}
.lead{background:var(--panel);border:1px solid var(--rule);border-left:4px solid var(--warn);
  border-radius:8px;padding:14px 18px}
.lead ul{margin:8px 0 0;padding-inline-start:20px}
.lead li{margin:8px 0;color:var(--muted)}
.lead li b{color:var(--ink);text-transform:uppercase;font-size:12px;letter-spacing:.06em;
  margin-inline-end:6px;display:block}
.lead pre.hj{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.45 ui-monospace,Menlo,monospace;
  color:var(--muted);margin:4px 0 0;background:var(--sunk);border:1px solid var(--rule);
  border-radius:6px;padding:8px 10px}
.consumer{background:var(--sunk);border:1px solid var(--rule);border-radius:6px;padding:10px 12px;
  color:var(--ink);margin:0 0 10px}
.figs{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0}
.fig{background:var(--panel);border:1px solid var(--rule);border-radius:8px;
  padding:10px 14px;min-width:150px;flex:1 1 150px}
.fig b{display:block;font:600 24px/1.2 "Barlow Condensed",system-ui,sans-serif;color:var(--mark)}
.fig span{color:var(--muted);font-size:12.5px}
.placed{display:flex;flex-wrap:wrap;gap:10px;margin:10px 0}
.placed div{background:var(--sunk);border:1px solid var(--rule);border-radius:8px;padding:8px 12px;
  flex:1 1 200px}
.placed b{display:block;font:600 20px/1.2 "Barlow Condensed",system-ui,sans-serif;color:var(--good);
  min-height:24px}
.placed b:empty::after{content:"not placed yet";color:var(--crit);font-size:13px}
.placed span{color:var(--muted);font-size:12.5px}
table{width:100%;border-collapse:collapse;background:var(--panel);
  border:1px solid var(--rule);border-radius:8px;overflow:hidden;margin:8px 0}
td,th{border-top:1px solid var(--rule);padding:7px 9px;vertical-align:top;font-size:13px;
  text-align:start}
th{color:var(--muted);font-weight:600;font-size:11.5px;text-transform:uppercase;letter-spacing:.05em}
tr:first-child td,tr:first-child th{border-top:0}
td.k{color:var(--ink);font-weight:600}
td.num{font:12.5px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--steel);white-space:nowrap}
.tscroll{overflow-x:auto}
td.muted,.muted{color:var(--muted);font-size:12.5px}
code{font:12.5px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted)}
.ll{font:12.5px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--steel)}
.chip{display:inline-block;border-radius:4px;padding:1px 7px;font-size:12px;
  border:1px solid var(--rule);background:var(--sunk);color:var(--muted);margin:0 6px 4px 0}
.chip.notserved{color:var(--crit);border-color:var(--crit)}
.prov{display:inline-block;border-radius:4px;padding:1px 7px;font-size:11px;
  border:1px solid var(--rule);margin:0 6px 4px 0;background:var(--sunk);color:var(--muted);
  letter-spacing:.03em}
.unk{display:inline-block;border-radius:4px;padding:0 5px;font-size:10.5px;border:1px dashed var(--crit);
  color:var(--crit);letter-spacing:.03em;margin-inline-start:4px}
.nodoor{color:var(--crit);font-size:12.5px}
.why{color:var(--ink);font-size:14px}
.mapwrap{background:var(--panel);border:1px solid var(--rule);border-radius:8px;padding:8px;
  overflow-x:auto}
svg.map{display:block;width:100%;height:auto;background:var(--sunk);border-radius:6px}
svg .grat{stroke:var(--rule);stroke-width:.6;fill:none}
svg .gratlab{fill:var(--muted);font:10px ui-monospace,Menlo,monospace}
svg .pose[data-kind="campus"]{fill:var(--mark);stroke:var(--plate);stroke-width:1}
svg .pose[data-kind="anchor"]{fill:var(--steel);stroke:var(--plate);stroke-width:.8}
svg .pose[data-kind="restoration-site"]{fill:var(--good);stroke:var(--plate);stroke-width:.8}
svg .plab{fill:var(--ink);font:600 11px system-ui,sans-serif;paint-order:stroke;stroke:var(--sunk);
  stroke-width:3px;stroke-linejoin:round}
svg .ilab{fill:var(--muted);font:10px system-ui,sans-serif}
svg .inset-title{fill:var(--mark);font:600 12px "Barlow Condensed",system-ui,sans-serif}
.insets{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px;margin-top:10px}
.inset{background:var(--sunk);border:1px solid var(--rule);border-radius:6px;padding:4px}
.inset svg{display:block;width:100%;height:auto}
.legend span{margin-inline-end:14px;font-size:12.5px;color:var(--muted)}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-inline-end:5px;vertical-align:middle}
.projection{color:var(--muted);font-size:12.5px;margin:6px 0}
ul.som{list-style:none;padding:0;margin:8px 0}
ul.som>li{background:var(--panel);border:1px solid var(--rule);border-radius:8px;padding:10px 12px;margin:8px 0}
ul.som>li[data-served="false"]{border-left:4px solid var(--crit)}
ul.som>li[data-served="true"]{border-left:4px solid var(--good)}
.bhead{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:baseline}
.bhead b{color:var(--ink)}
.bhead .own{color:var(--muted);font-size:12.5px}
ul.nodes{list-style:none;padding-inline-start:14px;margin:6px 0 0;border-inline-start:1px solid var(--rule)}
ul.nodes li{padding:2px 0 2px 8px;font-size:12.5px;color:var(--muted)}
ul.nodes li b{color:var(--ink);font-weight:500}
ul.nodes li .kind{display:inline-block;min-width:88px;color:var(--steel);
  font:11px ui-monospace,Menlo,monospace;text-transform:uppercase}
ul.nodes li .unplaced{color:var(--crit)}
details>summary{cursor:pointer;color:var(--steel);font-size:13px;margin:6px 0}
.doorline{margin-top:4px;font-size:12.5px}
footer.page{margin-top:34px;border-top:1px solid var(--rule);padding:14px 0 30px;
  color:var(--muted);font-size:14px}
footer.page a{margin-inline-end:10px}
'''

SCRIPT = r'''
/* The reference consumer.

   Everything drawn below comes out of DATA, which the generator read from
   the three spatial registries and handed across in their own shape. This
   script does what a metaverse browser would do with them and nothing more:
   it resolves every geopose ref against the pose table, projects every pose
   onto a plate carree (equirectangular) picture of WGS84 degrees, and walks
   every branch of the scene graph into a tree under the owner the registry
   names. It composes nothing into a 3D scene, because som.json says the
   composition is a browser's job, not this build's.

   The "placed" figures are counted off the DOM after drawing, never from a
   number of their own. Every lookup that should resolve is checked and
   throws by name when it does not: a node whose geopose ref is in no pose,
   or a node with no pose and no registry reason for it, stops the render
   with a message naming the registry path - it does not quietly draw one
   fewer. No `??` and no default stands in for a missing field here. */
const D = DATA;
const P = D.paths;

function must(o, k, where) {
  if (o === null || typeof o !== 'object') throw new Error(where + ': expected an object to read ' + k + ' from');
  if (!(k in o)) throw new Error(where + ': required field ' + k + ' is missing');
  return o[k];
}
function elem(tag, attrs, kids) {
  const e = document.createElement(tag);
  if (attrs) for (const k in attrs) {
    if (k === 'class') e.className = attrs[k];
    else if (k === 'text') e.textContent = attrs[k];
    else e.setAttribute(k, attrs[k]);
  }
  if (kids) for (const c of kids) e.appendChild(c);
  return e;
}
function svgEl(tag, attrs, text) {
  const e = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (text !== undefined) e.textContent = text;
  return e;
}

/* ---- the pose table: every ref resolves exactly once ---- */
const POSES = must(D.geopose, 'poses', P.geopose);
const byRef = new Map();
POSES.forEach((p, i) => {
  const w = P.geopose + '#poses[' + i + ']';
  const ref = must(must(p, 'subject', w), 'ref', w + '.subject');
  if (byRef.has(ref)) throw new Error(w + ': subject ref ' + ref + ' declared twice');
  must(must(must(p, 'geopose', w), 'position', w), 'lat', w + '.geopose.position');
  byRef.set(ref, p);
});
function pose(ref, where) {
  if (!byRef.has(ref)) throw new Error(where + ': geopose ref ' + ref + ' resolves to no pose in ' + P.geopose);
  return byRef.get(ref);
}
/* a door as the registry wrote it: a string, or an object whose href is one */
function doorText(d, where) {
  if (typeof d === 'string') return d;
  if (d !== null && typeof d === 'object') return must(d, 'href', where + '.door');
  throw new Error(where + '.door: a door is a string href or an object carrying one, got ' + typeof d);
}

/* ---- the projection: plate carree, x = lon, y = lat, one degree per
   degree on both axes. Not conformal, not equal-area; labelled as such on
   the page. No basemap: nothing appears here that the registry does not
   state. ---- */
function projector(poses, W, H, pad) {
  let lon0 = Infinity, lon1 = -Infinity, lat0 = Infinity, lat1 = -Infinity;
  for (const p of poses) {
    const q = p.geopose.position;
    lon0 = Math.min(lon0, q.lon); lon1 = Math.max(lon1, q.lon);
    lat0 = Math.min(lat0, q.lat); lat1 = Math.max(lat1, q.lat);
  }
  const dlon = Math.max(lon1 - lon0, 1e-6), dlat = Math.max(lat1 - lat0, 1e-6);
  const s = Math.min((W - 2 * pad) / dlon, (H - 2 * pad) / dlat);
  const ox = (W - dlon * s) / 2, oy = (H - dlat * s) / 2;
  return {
    x: (lon) => ox + (lon - lon0) * s,
    y: (lat) => oy + (lat1 - lat) * s,
    lon0, lon1, lat0, lat1, s, W, H,
  };
}
function niceStep(span, want) {
  const steps = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20];
  for (const st of steps) if (span / st <= want) return st;
  return 20;
}
function graticule(svg, pr, step) {
  const fmt = (v) => (Math.abs(v) >= 10 ? v.toFixed(step < 1 ? 2 : 0) : v.toFixed(step < 1 ? 3 : 0));
  const lonA = Math.ceil((pr.lon0 - 1e-9) / step) * step, latA = Math.ceil((pr.lat0 - 1e-9) / step) * step;
  for (let lon = lonA - step; lon <= pr.lon1 + step; lon += step) {
    const x = pr.x(lon);
    if (x < 0 || x > pr.W) continue;
    svg.appendChild(svgEl('line', { class: 'grat', x1: x, y1: 0, x2: x, y2: pr.H }));
    svg.appendChild(svgEl('text', { class: 'gratlab', x: x + 2, y: pr.H - 3 }, fmt(lon) + '°'));
  }
  for (let lat = latA - step; lat <= pr.lat1 + step; lat += step) {
    const y = pr.y(lat);
    if (y < 0 || y > pr.H) continue;
    svg.appendChild(svgEl('line', { class: 'grat', x1: 0, y1: y, x2: pr.W, y2: y }));
    svg.appendChild(svgEl('text', { class: 'gratlab', x: 3, y: y - 2 }, fmt(lat) + '°'));
  }
}
function plot(svg, pr, p, r) {
  const q = p.geopose.position;
  const c = svgEl('circle', {
    class: 'pose', 'data-pose': p.subject.ref, 'data-kind': p.subject.kind,
    'data-tier': p.provenance.position_horizontal,
    cx: pr.x(q.lon).toFixed(2), cy: pr.y(q.lat).toFixed(2), r,
  });
  c.appendChild(svgEl('title', {}, p.subject.name + '\n' + p.subject.ref + '\nlat ' + q.lat + ', lon ' + q.lon
    + '\nh ' + q.h + ' m - ' + p.provenance.h_provenance
    + '\nyaw/pitch/roll ' + p.geopose.orientation.yaw + '/' + p.geopose.orientation.pitch + '/'
    + p.geopose.orientation.roll + ' - ' + p.provenance.orientation_provenance
    + '\nposition: ' + p.provenance.position_horizontal + ' - ' + p.provenance.source));
  svg.appendChild(c);
  return c;
}

/* ---- the continental map: every pose ---- */
const map = document.getElementById('map');
{
  const W = 960, H = 520;
  map.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  const pr = projector(POSES, W, H, 36);
  graticule(map, pr, 5);
  for (const p of POSES) plot(map, pr, p, p.subject.kind === 'campus' ? 5 : 3);
  for (const p of POSES) {
    if (p.subject.kind !== 'campus') continue;
    const q = p.geopose.position;
    map.appendChild(svgEl('text', { class: 'plab', x: (pr.x(q.lon) + 7).toFixed(2), y: (pr.y(q.lat) - 6).toFixed(2) },
      p.subject.name));
  }
  document.getElementById('placed-poses').textContent =
    map.querySelectorAll('[data-pose]').length + ' of ' + POSES.length;
}

/* ---- one inset per place, at that campus's own scale ---- */
const insets = document.getElementById('insets');
{
  const places = must(D, 'places', P.fabric);
  let drawn = 0;
  places.forEach((pl, i) => {
    const w = P.fabric + '#places[' + i + ']';
    const cp = pose(must(pl, 'geopose', w), w);
    const slug = must(cp.subject, 'campus', w + ' -> ' + cp.subject.ref);
    const mine = POSES.filter((p) => p.subject.campus === slug);
    const W = 320, H = 240;
    const svg = svgEl('svg', { viewBox: '0 0 ' + W + ' ' + H, 'data-inset': slug, role: 'img' });
    const pr = projector(mine, W, H, 30);
    graticule(svg, pr, niceStep(Math.max(pr.lon1 - pr.lon0, pr.lat1 - pr.lat0), 4));
    svg.appendChild(svgEl('text', { class: 'inset-title', x: 6, y: 14 }, must(pl, 'name', w)));
    for (const p of mine) plot(svg, pr, p, p.subject.kind === 'campus' ? 5 : 3.5);
    for (const p of mine) {
      const q = p.geopose.position;
      svg.appendChild(svgEl('text', { class: 'ilab', x: (pr.x(q.lon) + 6).toFixed(2), y: (pr.y(q.lat) + 3).toFixed(2) },
        p.subject.kind === 'campus' ? '' : p.subject.name.length > 26 ? p.subject.name.slice(0, 25) + '…' : p.subject.name));
    }
    const box = elem('div', { class: 'inset' }, [svg]);
    insets.appendChild(box);
    drawn += svg.querySelectorAll('[data-pose]').length;
  });
  document.getElementById('placed-inset-poses').textContent = drawn + ' of ' + POSES.length;
}

/* ---- the scene graph, walked ---- */
const som = document.getElementById('som');
{
  const branches = must(must(D.som, 'root', P.som), 'branches', P.som + '#root');
  let nodesTotal = 0;
  branches.forEach((b, bi) => {
    const w = P.som + '#root.branches[' + bi + ']';
    const served = must(b, 'served_by_this_fabric', w);
    const origin = must(b, 'origin', w);
    const li = elem('li', { 'data-branch': must(b, 'id', w), 'data-origin': origin, 'data-served': String(served) });
    const head = elem('div', { class: 'bhead' }, [
      elem('b', { text: must(b, 'owner', w) }),
      elem('code', { text: b.id }),
      elem('span', { class: 'own', text: origin === 'external' ? 'external origin' : 'this fabric' }),
    ]);
    if (!served) head.appendChild(elem('span', { class: 'chip notserved', text: 'not served by this fabric' }));
    for (const t of must(b, 'provenance_tiers', w)) head.appendChild(elem('span', { class: 'prov', 'data-tier': t, text: t }));
    li.appendChild(head);
    const doorLine = elem('div', { class: 'doorline' });
    if ('door' in b && b.door === null) {
      const why = must(must(D, 'doorRefused', 'payload'), w, w + '.door (null, why_no_door)');
      doorLine.appendChild(elem('span', { class: 'nodoor', 'data-door-refused': w, text: 'no door - ' + why }));
    } else if ('door' in b) {
      const shown = doorText(b.door, w);
      const href = must(must(D, 'doorHref', 'payload'), w, w + '.door (resolved)');
      doorLine.appendChild(elem('span', { text: 'door: ' }));
      doorLine.appendChild(elem('a', { 'data-door': w, href, text: shown }));
    } else {
      doorLine.appendChild(elem('span', { class: 'nodoor', 'data-door-undeclared': w,
        text: 'no door declared in ' + P.som + ' for this branch' }));
    }
    li.appendChild(doorLine);

    const kids = must(b, 'children', w);
    nodesTotal += kids.length;
    const groups = new Map();
    kids.forEach((c, ci) => {
      const cw = w + '.children[' + ci + ']';
      const kind = must(c, 'kind', cw);
      if (!groups.has(kind)) groups.set(kind, []);
      groups.get(kind).push([c, cw]);
    });
    for (const [kind, rows] of groups) {
      const ul = elem('ul', { class: 'nodes' });
      for (const [c, cw] of rows) {
        const name = must(c, 'name', cw);
        const ref = must(c, 'geopose', cw);
        const n = elem('li', { 'data-node': name, 'data-node-kind': kind,
          'data-served': String(must(c, 'served_by_this_fabric', cw)) });
        n.appendChild(elem('span', { class: 'kind', text: kind }));
        n.appendChild(elem('b', { text: name }));
        n.appendChild(elem('span', { text: ' ' }));
        n.appendChild(elem('span', { class: 'prov', 'data-tier': must(c, 'provenance', cw), text: c.provenance }));
        if (ref === null) {
          const why = must(must(D, 'unplacedWhy', 'payload'), name, cw + ' (no geopose)');
          n.setAttribute('data-unplaced-why', why);
          n.appendChild(elem('span', { class: 'unplaced', text: ' no pose - ' + why }));
        } else {
          const p = pose(ref, cw);
          n.setAttribute('data-node-pose', ref);
          n.appendChild(elem('code', { text: ref + ' (' + p.geopose.position.lat + ', ' + p.geopose.position.lon + ')' }));
        }
        if ('door' in c && c.door === null) {
          const why = must(must(D, 'doorRefused', 'payload'), cw, cw + '.door (null, why_no_door)');
          n.setAttribute('data-door-refused', cw);
          n.appendChild(elem('span', { class: 'unplaced', text: ' no door - ' + why }));
        } else if ('door' in c) {
          const shown = doorText(c.door, cw);
          const href = must(must(D, 'doorHref', 'payload'), cw, cw + '.door (resolved)');
          n.appendChild(elem('span', { text: ' ' }));
          n.appendChild(elem('a', { 'data-door': cw, href, text: 'door ' + shown }));
        } else {
          n.setAttribute('data-door-undeclared', cw);
        }
        ul.appendChild(n);
      }
      if (rows.length > 12) {
        const det = elem('details', {}, [elem('summary', { text: rows.length + ' ' + kind + ' nodes' }), ul]);
        li.appendChild(det);
      } else {
        li.appendChild(ul);
      }
    }
    som.appendChild(li);
  });
  document.getElementById('placed-branches').textContent =
    som.querySelectorAll('[data-branch]').length + ' of ' + branches.length;
  document.getElementById('placed-nodes').textContent =
    som.querySelectorAll('[data-node]').length + ' of ' + nodesTotal;
  document.getElementById('placed-node-poses').textContent =
    som.querySelectorAll('[data-node-pose]').length + ' of ' + som.querySelectorAll('[data-node]').length;
}
'''

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' stroke='%23E8A33D' stroke-width='2.6' stroke-linejoin='round'/%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E">
<title>{E(PRODUCT.split("(")[0].strip())} — spatial fabric</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">

<header class="page">
  <h1>{E(PRODUCT.split("(")[0].strip())} — <span class="x">spatial fabric, loaded</span></h1>
  <p>{E(PRODUCT)} · pack {E(PACK_VERSION)} · built {E(BUILT)} · source stamp <code>{E(STAMP)}</code> ·
     the reference consumer of <code>{E(FABRIC_PATH)}</code>, <code>{E(GEOPOSE_PATH)}</code> and
     <code>{E(SOM_PATH)}</code></p>
</header>

<section class="lead" id="limits">
  <h2>What this page is, and what it is not</h2>
  <p class="consumer" id="consumer" data-consumer="web/{E(PAGE_NAME)}" data-not-loaded-in="Sneeze, Artemis"
     data-measured-by="{E(SUITE)}">
     This fabric loads in <b>this page</b>. It is the bundle's own reference consumer: it is handed the
     three registries in their own shape, resolves every pose, plots it on a WGS84 projection, walks
     every branch of the scene graph, and lists every service. Whether that actually happens is measured
     by <code>{E(SUITE)} --browser</code>, which opens this page in headless Chromium and counts what was
     placed. Nothing here has been opened in Sneeze, Artemis or any other metaverse browser, and this
     page does not claim otherwise. The three registries are embedded in this page verbatim at build
     time and the page fetches nothing at run time, because the published site carries pages and
     nothing under <code>spatial/</code>; the suite holds the embedded copy to the files byte for
     byte.</p>
  <p class="why">The registries' own honesty block, verbatim — h and heading are UNKNOWN placeholders,
     OMBI is shaped-after and not claimed, and every external origin is not served here:</p>
  <ul>{HONESTY_ITEMS}</ul>
  <p class="why" style="margin-top:12px">What the scene graph and manifest say they are:</p>
  <pre data-quote="shape">{E(SOM_SHAPE)}</pre>
  <pre data-quote="composition">{E(COMPOSITION)}</pre>
</section>

<section class="figs">{FIGS}</section>

<section id="poses">
  <h2>Where things stand — every GeoPose, plotted</h2>
  <p class="why">{E(ENCODING)} · <code>{E(MEDIA_TYPE)}</code> · CRS {E(CRS)}. Each mark is one pose from
     <code>{E(GEOPOSE_PATH)}</code>; hover a mark for its ref, its coordinates, its position provenance and
     its UNKNOWN sidecars. Every h is 0 and every heading is 0, as placeholders, not measurements.</p>
  <p class="projection" id="projection" data-projection="plate-carree" data-crs="{E(CRS)}">
     Projection: <b>plate carrée</b> (equirectangular) — x is longitude in degrees, y is latitude in
     degrees, one degree per degree on both axes; not conformal, not equal-area; no basemap, so nothing
     appears here that the registry does not state. Framed to the poses' own extent.</p>
  <div class="placed">
    <div><b id="placed-poses"></b><span>poses drawn on the continental map, counted off the marks actually placed, of the poses in the registry</span></div>
    <div><b id="placed-inset-poses"></b><span>poses drawn across the campus insets, counted the same way — a pose is drawn once per inset it belongs to</span></div>
  </div>
  <p class="legend">
    <span><i class="dot" style="background:var(--mark)"></i>campus</span>
    <span><i class="dot" style="background:var(--steel)"></i>anchor (a named place near a campus)</span>
    <span><i class="dot" style="background:var(--good)"></i>restoration site (an external origin's own place)</span>
  </p>
  <div class="mapwrap"><svg id="map" class="map" role="img" aria-label="every GeoPose on a plate carree projection"></svg></div>
  <h3>Each campus at its own scale</h3>
  <p class="muted">One inset per place in <code>{E(FABRIC_PATH)}</code>, framed to the poses whose subject
     belongs to that campus; the graticule step is chosen per inset and labelled in degrees.</p>
  <div class="insets" id="insets"></div>
  <details>
    <summary>Every pose as a table, with its sidecars</summary>
    <div class="tscroll"><table>
      <tr><th>ref</th><th>kind</th><th>subject</th><th>lat</th><th>lon</th><th>h (m)</th><th>yaw / pitch / roll</th><th>position</th><th>source</th></tr>
      {POSE_ROWS}
    </table></div>
  </details>
  <h3>Not posed, by the registry's own refusal</h3>
  <ul class="muted">{UNPOSED_ITEMS}</ul>
</section>

<section id="scene">
  <h2>Who owns what — the Scene Object Model, walked</h2>
  <p class="why">One branch per owner, from <code>{E(SOM_PATH)}</code>. This fabric's own branch is
     marked as served; every other branch belongs to an external origin, is marked not served, and holds
     only that origin's own poses — never a place, content or service of this fabric. A node is placed
     when its geopose ref resolves to a pose above; a node with no pose carries the registry's own
     reason instead of an invented position.</p>
  <div class="placed">
    <div><b id="placed-branches"></b><span>branches rendered, counted off the tree, of the branches in the registry</span></div>
    <div><b id="placed-nodes"></b><span>nodes rendered under those branches, of the nodes the registry holds</span></div>
    <div><b id="placed-node-poses"></b><span>of the rendered nodes, those whose geopose ref resolved to a pose</span></div>
  </div>
  <p class="muted">A door is a deep link a branch or node declares into the running site. Where one is
     declared it is the link; where the registry sets it null it gives its own reason, quoted; where none
     is declared yet the page says so. None is invented.</p>
  <ul class="som" id="som"></ul>
</section>

<section id="services">
  <h2>Services — transport and door</h2>
  <p class="why">Every service in <code>{E(FABRIC_PATH)}</code>, with the transport the registry declares
     for it, the pose it is anchored at, the registry that defines it (shown as text: registries are not
     part of the published site) and its door.</p>
  <div class="tscroll"><table>
    <tr><th>service</th><th>kind</th><th>transport</th><th>anchored at</th><th>provenance</th><th>defined in</th><th>door</th></tr>
    {SERVICE_ROWS}
  </table></div>
</section>

<section id="places">
  <h2>Places</h2>
  <p class="why">Every place this fabric serves. The fabric's declared entry is
     <a id="entry" data-entry href="{E(ENTRY_HREF)}"><code>{E(ENTRY)}</code></a>.</p>
  <div class="tscroll"><table>
    <tr><th>place</th><th>id</th><th>geopose</th><th>districts</th><th>halls</th><th>walk</th><th>door</th></tr>
    {PLACE_ROWS}
  </table></div>
</section>

<section id="external">
  <h2>External origins — named, located, not served</h2>
  <p class="why">Every other operator this fabric points at. Each is a separate origin with its own
     branch above; this fabric serves nothing for any of them.</p>
  <div class="tscroll"><table>
    <tr><th>operator</th><th>kind</th><th>served</th><th>poses</th><th>provenance</th><th>note</th></tr>
    {EXTERNAL_ROWS}
  </table></div>
</section>

<section id="content">
  <h2>Anchored content</h2>
  <p class="why">Every content record, in the fabric's declared format(s):
     {"".join(f"<span class=chip>{E(f)}</span>" for f in need(FABRIC, "content_formats", f"{FABRIC_PATH}#fabric"))}
     Each is produced on demand by the learner's own browser; none is a file on disk. Identity:
     <code>{E(json.dumps(IDENTITY, ensure_ascii=False))}</code>. Transport: {E(need(FABRIC, "transport", f"{FABRIC_PATH}#fabric"))}</p>
  <details>
    <summary>Every anchored content record</summary>
    <div class="tscroll"><table>
      <tr><th>scene</th><th>file</th><th>format</th><th>anchored at</th><th>produced</th><th>provenance</th><th>door</th></tr>
      {ANCHORED_ROWS}
    </table></div>
  </details>
</section>

<section id="sources">
  <h2>What the fabric is shaped after</h2>
  <ul class="muted">{SOURCE_ITEMS}</ul>
</section>

<section>
  <h2>What this page read</h2>
  <ul class="muted">{READS}</ul>
  <p class="muted">Every number on this page is counted from those files at build time or from the
     elements this page drew. None is typed. Whether a link's target is actually served is not something
     this page can know about itself; <code>{E(SUITE)} --browser</code> fetches each one against a local
     server and says how many answered.</p>
</section>

<footer class="page">
  <a href="{E(ENTRY_HREF)}">3D environment</a>
  <a href="trade_craft_geomap.html">network geomap</a>
  <a href="trade_craft_dashboard.html">network dashboard</a>
  <a href="trade_craft_landing.html">landing</a>
</footer>
</div>
<script>
const DATA = {PAYLOAD};
</script>
<script>
{SCRIPT}</script>
</body>
</html>
'''

out = HERE / PAGE_NAME
emit(out, page,
     f'{F(N_POSES)} poses, {F(N_BRANCHES)} SOM branches with {F(N_NODES)} nodes, '
     f'{F(N_SERVICES)} services, {F(N_DOORS_DECLARED)} doors declared; loads in this page, '
     f'not in any metaverse browser')
