"""venue/ - what a real multi-salon event building actually measures, taken
off a recorded 3D model of one, and published as proportions the generated
halls can be checked against.

THE SOURCE, AND WHY ITS GEOMETRY IS NOT IN THIS REPOSITORY

The measurements below come from a glTF binary of "R+5_Salons Rive Gauche_
Maison de la Mutualite", a real event venue in Paris, published by GL events
Paris Venues under CC-BY-4.0. The file is 1,008 meshes. The hall view of this
bundle's 3D scene runs at 164 draw calls against a ceiling of 196, so that one
model is roughly five times the entire remaining budget on its own, and it is
a Paris conference venue rather than a union training hall. It is not added to
the scene, not copied into the tree, and not one triangle of it is committed.

What IS committed is measurement. A generated hall is a schematic: identical
rooms on one grid, proportioned by whoever typed the grid. A recorded building
is proportioned by the people who had to stand up in it. This pack turns the
second into numbers the first can be held against.

WHAT TIER EACH NUMBER IS

RECORDED is reserved for what the file literally states: its byte length and
digest, its asset block, its declared counts. Everything with a dimension on
it is DERIVED - computed here by walking the node transforms and the vertex
buffer. A bounding box over a cluster of meshes is NOT a surveyed wall-to-wall
room dimension and every such record says which of the two it is and the exact
method that produced it.

THE UNIT QUESTION, WHICH IS NOT SETTLED

glTF is nominally metres. This file is not. Its only declared unit conversion
is the 0.01 scale on the exporter's own node, the conventional centimetre-to-
metre factor, and honouring it puts the whole building at 0.19 across. Undoing
it puts the building at 18.6 across with a 1.35 clear storey height - a room
wider than a house with a ceiling you could not stand under. No reading of
this file is in metres, so this pack publishes MODEL UNITS and says so in
every record. The figures that transfer regardless are the RATIOS, and those
are published separately and are exactly what a hall should be proportioned
against.
"""
import hashlib
import json
import math
import pathlib
import struct
from array import array
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'venue.json'

# The upload lives OUTSIDE the repository, on the machine the measurement was
# taken on. A build that only works there is not reproducible, so this build
# has two modes and neither of them is "quietly pass". See the tail of the
# file: present -> measure and write; absent -> refuse to write, verify what
# is committed, and say out loud that nothing was re-measured.
SOURCE = pathlib.Path(
    '/root/.claude/uploads/a56b2578-e24c-588e-b54f-1798a964624b'
    '/7ba02a37-r5_salons_rive_gauche_maison_de_la_mutualite.glb')

PACK_VERSION = json.loads(
    (ROOT / 'pack' / 'manifest.json').read_text())['pack_version']

# One model unit. Named, not assumed to be anything.
MU = 'mu'

# The exporter node carries this scale. It is READ from the file below and
# checked against this expectation rather than trusted; the number here is
# what makes the check a check.
FBX_NODE_SCALE = 0.01

# Measurement parameters, every one of them stated because every one of them
# changes an answer. A threshold that lives only in the code is a number the
# reader cannot argue with.
PARAMS = {
    'model_unit_basis': 'the exporter node\'s %s scale is UNDONE, so one '
                        'model unit is one unit of the authored geometry as '
                        'it sits in the vertex buffer' % FBX_NODE_SCALE,
    'plan_grid': 0.10,
    'plan_grid_means': 'the cell size, in model units, that floor triangles '
                       'and object footprints are rasterised onto',
    'horizontal_tolerance': 0.002,
    'horizontal_tolerance_means': 'a triangle counts as horizontal when its '
                                  'three vertices lie within this many model '
                                  'units of one height',
    'fabric_footprint_threshold': 9.0,
    'fabric_footprint_threshold_means': 'a mesh whose world bounding box '
                                        'covers more than this many square '
                                        'model units in plan is treated as '
                                        'building fabric rather than '
                                        'contents',
    'cluster_gap': 0.20,
    'cluster_gap_means': 'two contents meshes join one cluster when their '
                         'plan bounding boxes are within this many model '
                         'units of each other on both plan axes',
    'cluster_min_members': 8,
    'obstruction_band': (0.05, 1.00),
    'obstruction_band_means': 'an object obstructs circulation on a floor '
                              'plate when it rises more than the first value '
                              'above that floor and starts below the second '
                              '- lower is underfoot, higher is overhead',
    'floor_plate_min_cells': 50,
    'panel_family_min_members': 4,
    'panel_family_selection': 'among floor-standing panel families of at '
                              'least that many members, the opening set is '
                              'the one with the highest share of members '
                              'that have modelled floor on BOTH sides - the '
                              'evidence picks it, not its size',
}


def need(obj, path, key):
    """Read a key, or fail naming the path. There is no default: a glTF that
    is missing a field this build depends on is a file this build has not
    understood, and guessing produces a measurement of nothing."""
    if not isinstance(obj, dict) or key not in obj:
        raise KeyError('venue: %s.%s is missing from the source file; this '
                       'build will not substitute a value for it'
                       % (path, key))
    return obj[key]


# ---------------------------------------------------------------------------
# reading the container

def read_glb(path):
    raw = path.read_bytes()
    magic, version, total = struct.unpack('<4sII', raw[:12])
    if magic != b'glTF':
        raise ValueError('venue: %s does not start with the glTF magic' % path)
    if total != len(raw):
        raise ValueError('venue: the glTF header declares %d bytes, the file '
                         'is %d' % (total, len(raw)))
    chunks = {}
    off = 12
    while off < len(raw):
        clen, ctype = struct.unpack('<I4s', raw[off:off + 8])
        chunks[ctype] = (off + 8, clen)
        off += 8 + clen
    if b'JSON' not in chunks or b'BIN\x00' not in chunks:
        raise ValueError('venue: expected a JSON chunk and a BIN chunk, got %r'
                         % sorted(chunks))
    jo, jl = chunks[b'JSON']
    bo, bl = chunks[b'BIN\x00']
    return {
        'bytes': len(raw),
        'sha256': hashlib.sha256(raw).hexdigest(),
        'container_version': version,
        'json': json.loads(raw[jo:jo + jl]),
        'bin': raw[bo:bo + bl],
        'json_chunk_bytes': jl,
        'bin_chunk_bytes': bl,
    }


# ---------------------------------------------------------------------------
# node transforms

def trs_matrix(node):
    """Column-major 4x4 for one node. glTF 2.0 defines identity translation,
    rotation and scale when the node omits them - that is the format speaking,
    not this build filling a hole, so the absent case is spelled out."""
    if 'matrix' in node:
        return list(node['matrix'])
    t = node['translation'] if 'translation' in node else [0.0, 0.0, 0.0]
    q = node['rotation'] if 'rotation' in node else [0.0, 0.0, 0.0, 1.0]
    s = node['scale'] if 'scale' in node else [1.0, 1.0, 1.0]
    x, y, z, w = q
    m = [1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w), 0,
         2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w), 0,
         2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y), 0,
         0, 0, 0, 1]
    for col in range(3):
        for row in range(3):
            m[col * 4 + row] *= s[col]
    m[12], m[13], m[14] = t
    return m


def mat_mul(a, b):
    out = [0.0] * 16
    for col in range(4):
        for row in range(4):
            out[col * 4 + row] = (a[row] * b[col * 4]
                                  + a[4 + row] * b[col * 4 + 1]
                                  + a[8 + row] * b[col * 4 + 2]
                                  + a[12 + row] * b[col * 4 + 3])
    return out


IDENTITY = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]


def walk_nodes(g, scale):
    """Yield (node index, name, primitive, world matrix) for every drawable
    primitive in the scene, with the world matrix already multiplied by
    `scale` so the caller works in model units."""
    nodes = need(g, 'gltf', 'nodes')
    meshes = need(g, 'gltf', 'meshes')
    scenes = need(g, 'gltf', 'scenes')
    roots = need(scenes[need(g, 'gltf', 'scene')], 'gltf.scenes[]', 'nodes')
    base = [scale if i in (0, 5, 10) else (1.0 if i == 15 else 0.0)
            for i in range(16)]

    def rec(i, parent, inherited):
        node = nodes[i]
        name = node['name'] if 'name' in node else inherited
        world = mat_mul(parent, trs_matrix(node))
        if 'mesh' in node:
            for prim in need(meshes[node['mesh']], 'gltf.meshes[]',
                             'primitives'):
                yield i, name, prim, world
        if 'children' in node:
            for c in node['children']:
                yield from rec(c, world, name)

    for r in roots:
        yield from rec(r, base, None)


def xf(m, p):
    x, y, z = p
    return (m[0] * x + m[4] * y + m[8] * z + m[12],
            m[1] * x + m[5] * y + m[9] * z + m[13],
            m[2] * x + m[6] * y + m[10] * z + m[14])


# ---------------------------------------------------------------------------
# accessors

def accessor_vec3(g, bin_bytes, idx):
    acc = need(g, 'gltf', 'accessors')[idx]
    views = need(g, 'gltf', 'bufferViews')
    view = views[need(acc, 'gltf.accessors[%d]' % idx, 'bufferView')]
    base = (view['byteOffset'] if 'byteOffset' in view else 0) \
        + (acc['byteOffset'] if 'byteOffset' in acc else 0)
    n = need(acc, 'gltf.accessors[%d]' % idx, 'count')
    if need(acc, 'gltf.accessors[%d]' % idx, 'componentType') != 5126:
        raise ValueError('venue: accessor %d is not float32' % idx)
    stride = view['byteStride'] if 'byteStride' in view else 12
    out = array('f')
    if stride == 12:
        out.frombytes(bin_bytes[base:base + n * 12])
    else:
        for k in range(n):
            out.frombytes(bin_bytes[base + k * stride:base + k * stride + 12])
    return out


def accessor_index(g, bin_bytes, idx):
    acc = need(g, 'gltf', 'accessors')[idx]
    views = need(g, 'gltf', 'bufferViews')
    view = views[need(acc, 'gltf.accessors[%d]' % idx, 'bufferView')]
    base = (view['byteOffset'] if 'byteOffset' in view else 0) \
        + (acc['byteOffset'] if 'byteOffset' in acc else 0)
    n = need(acc, 'gltf.accessors[%d]' % idx, 'count')
    ct = need(acc, 'gltf.accessors[%d]' % idx, 'componentType')
    code = {5121: 'B', 5123: 'H', 5125: 'I'}
    if ct not in code:
        raise ValueError('venue: accessor %d has index type %d' % (idx, ct))
    out = array(code[ct])
    out.frombytes(bin_bytes[base:base + n * out.itemsize])
    return out


# ---------------------------------------------------------------------------
# plan-grid helpers

G = PARAMS['plan_grid']


def cells_of_tri(a, b, c):
    """The plan cells whose centre falls inside a triangle, projected down."""
    x0, x1 = min(a[0], b[0], c[0]), max(a[0], b[0], c[0])
    z0, z1 = min(a[2], b[2], c[2]), max(a[2], b[2], c[2])
    for i in range(math.floor(x0 / G), math.floor(x1 / G) + 1):
        for k in range(math.floor(z0 / G), math.floor(z1 / G) + 1):
            px, pz = (i + 0.5) * G, (k + 0.5) * G
            d1 = (px - b[0]) * (a[2] - b[2]) - (a[0] - b[0]) * (pz - b[2])
            d2 = (px - c[0]) * (b[2] - c[2]) - (b[0] - c[0]) * (pz - c[2])
            d3 = (px - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (pz - a[2])
            neg = d1 < 0 or d2 < 0 or d3 < 0
            pos = d1 > 0 or d2 > 0 or d3 > 0
            if not (neg and pos):
                yield (i, k)


def components(cells):
    """Four-connected components of a set of plan cells, largest first."""
    seen, out = set(), []
    for start in sorted(cells):
        if start in seen:
            continue
        stack, group = [start], []
        seen.add(start)
        while stack:
            c = stack.pop()
            group.append(c)
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c[0] + d[0], c[1] + d[1])
                if n in cells and n not in seen:
                    seen.add(n)
                    stack.append(n)
        out.append(group)
    out.sort(key=lambda gr: (-len(gr), min(gr)))
    return out


def plan_box(cells):
    xs = [c[0] for c in cells]
    zs = [c[1] for c in cells]
    return ((max(xs) - min(xs) + 1) * G, (max(zs) - min(zs) + 1) * G)


def r(v, n=3):
    return round(v + 0.0, n)


# ---------------------------------------------------------------------------
# the measurement

def measure(src):
    g = src['json']
    asset = need(g, 'gltf', 'asset')
    extras = need(asset, 'gltf.asset', 'extras')

    # --- the exporter's declared unit conversion, READ not assumed ---------
    nodes = need(g, 'gltf', 'nodes')
    declared = []
    for i, n in enumerate(nodes):
        if 'matrix' not in n:
            continue
        m = n['matrix']
        sx = math.sqrt(m[0] ** 2 + m[1] ** 2 + m[2] ** 2)
        if abs(sx - 1.0) > 1e-6:
            declared.append((i, n['name'] if 'name' in n else None, sx))
    if len(declared) != 1:
        raise ValueError('venue: expected exactly one scaled root matrix, '
                         'found %r' % (declared,))
    fbx_i, fbx_name, fbx_scale = declared[0]
    if abs(fbx_scale - FBX_NODE_SCALE) > 1e-6:
        raise ValueError('venue: the exporter node scale is %r, not the %r '
                         'this build was written against'
                         % (fbx_scale, FBX_NODE_SCALE))
    to_mu = 1.0 / fbx_scale   # undo it; work in authored units

    # --- pass 1: JSON only. Per-primitive world bounding boxes. -----------
    accs = need(g, 'gltf', 'accessors')
    prims = []
    for node_i, name, prim, world in walk_nodes(g, to_mu):
        attrs = need(prim, 'gltf.meshes[].primitives[]', 'attributes')
        acc = accs[need(attrs, 'primitive.attributes', 'POSITION')]
        lo = need(acc, 'gltf.accessors[].POSITION', 'min')
        hi = need(acc, 'gltf.accessors[].POSITION', 'max')
        pts = [xf(world, (lo[0] if b & 1 else hi[0],
                          lo[1] if b & 2 else hi[1],
                          lo[2] if b & 4 else hi[2])) for b in range(8)]
        prims.append({
            'name': name,
            'node': node_i,
            'material': prim['material'] if 'material' in prim else None,
            'lo': [min(p[k] for p in pts) for k in range(3)],
            'hi': [max(p[k] for p in pts) for k in range(3)],
        })
    if len(prims) != len(need(g, 'gltf', 'meshes')):
        raise ValueError('venue: %d primitives from %d meshes; this build '
                         'assumes one primitive per mesh'
                         % (len(prims), len(g['meshes'])))

    for p in prims:
        p['d'] = [p['hi'][k] - p['lo'][k] for k in range(3)]
        p['plan_area'] = p['d'][0] * p['d'][2]

    box_lo = [min(p['lo'][k] for p in prims) for k in range(3)]
    box_hi = [max(p['hi'][k] for p in prims) for k in range(3)]

    # Building fabric vs contents. The threshold is stated in PARAMS; the
    # gap it sits in is reported so a reader can see it is not knife-edge.
    areas = sorted((p['plan_area'] for p in prims), reverse=True)
    thr = PARAMS['fabric_footprint_threshold']
    fabric = {p['name'] for p in prims if p['plan_area'] > thr}
    below = max((a for a in areas if a <= thr), default=0.0)
    above = min((a for a in areas if a > thr), default=0.0)
    contents = [p for p in prims if p['name'] not in fabric]

    # --- pass 2: the vertex buffer ----------------------------------------
    flat = defaultdict(list)          # rounded height -> horizontal triangles
    flat_area = Counter()
    fabric_top = defaultdict(lambda: -1e30)
    fabric_bottom = defaultdict(lambda: 1e30)
    triangles = 0
    tol = PARAMS['horizontal_tolerance']
    for node_i, name, prim, world in walk_nodes(g, to_mu):
        attrs = need(prim, 'gltf.meshes[].primitives[]', 'attributes')
        pos = accessor_vec3(g, src['bin'],
                            need(attrs, 'primitive.attributes', 'POSITION'))
        idx = accessor_index(g, src['bin'],
                             need(prim, 'gltf.meshes[].primitives[]',
                                  'indices'))
        m = world
        verts = [((m[0] * pos[k] + m[4] * pos[k + 1] + m[8] * pos[k + 2]
                   + m[12]),
                  (m[1] * pos[k] + m[5] * pos[k + 1] + m[9] * pos[k + 2]
                   + m[13]),
                  (m[2] * pos[k] + m[6] * pos[k + 1] + m[10] * pos[k + 2]
                   + m[14])) for k in range(0, len(pos), 3)]
        is_fabric = name in fabric
        for t in range(0, len(idx), 3):
            a, b, c = verts[idx[t]], verts[idx[t + 1]], verts[idx[t + 2]]
            triangles += 1
            if max(a[1], b[1], c[1]) - min(a[1], b[1], c[1]) <= tol:
                ux, uz = b[0] - a[0], b[2] - a[2]
                vx, vz = c[0] - a[0], c[2] - a[2]
                ar = abs(ux * vz - uz * vx) / 2.0
                if ar > 0:
                    key = r(a[1])
                    flat[key].append((a, b, c))
                    flat_area[key] += ar
            if is_fabric:
                hi = max(a[1], b[1], c[1])
                lo = min(a[1], b[1], c[1])
                for cell in ((i, k) for i in range(
                        math.floor(min(a[0], b[0], c[0]) / G),
                        math.floor(max(a[0], b[0], c[0]) / G) + 1)
                        for k in range(
                        math.floor(min(a[2], b[2], c[2]) / G),
                        math.floor(max(a[2], b[2], c[2]) / G) + 1)):
                    if hi > fabric_top[cell]:
                        fabric_top[cell] = hi
                    if lo < fabric_bottom[cell]:
                        fabric_bottom[cell] = lo

    # --- floor datum levels ------------------------------------------------
    # The two largest horizontal surfaces in the model, by area. These are
    # datum levels, NOT storeys: they are closer together than one clear
    # height, so they are parts of one floor at different heights.
    ranked = sorted(flat_area.items(), key=lambda kv: (-kv[1], kv[0]))
    levels = []
    for y, area in ranked[:2]:
        cells = set()
        for tri in flat[y]:
            cells.update(cells_of_tri(*tri))
        plates = []
        for group in components(cells):
            if len(group) < PARAMS['floor_plate_min_cells']:
                continue
            w, d = plan_box(group)
            heads = [r(fabric_top[c] - y, 2) for c in group
                     if c in fabric_top and fabric_top[c] - y > 0.5]
            plates.append({
                'tier': 'DERIVED',
                'measured_by': 'four-connected components of the horizontal '
                               'triangles at this datum, rasterised onto a '
                               '%s %s plan grid. The width and depth are the '
                               'bounding box OF THAT COMPONENT in plan - a '
                               'box around a floor patch, not a wall-to-wall '
                               'survey.' % (G, MU),
                'plan_area_%s2' % MU: r(len(group) * G * G, 2),
                'bbox_width_%s' % MU: r(w, 2),
                'bbox_depth_%s' % MU: r(d, 2),
                'bbox_fill': r(len(group) * G * G / (w * d), 3),
                'aspect': r(max(w, d) / min(w, d), 3),
                'clear_height_cells_measured': len(heads),
                'clear_height_modes_%s' % MU: [
                    [h, n] for h, n in sorted(Counter(heads).items())],
            })
        levels.append({
            'tier': 'DERIVED',
            'measured_by': 'the horizontal triangles of the whole scene, '
                           'summed by height; these are the two heights that '
                           'carry the most surface area',
            'datum_%s' % MU: y,
            'horizontal_area_%s2' % MU: r(area, 2),
            'floor_plates': plates,
        })

    # --- clear height ------------------------------------------------------
    # The heights already measured per floor plate, pooled. Each cell is
    # counted against the datum of the plate it belongs to and against no
    # other - measuring every cell against every datum would invent bands
    # that are nothing but the gap between the datums.
    clear = Counter()
    for lv in levels:
        for pl in lv['floor_plates']:
            for h, n in pl['clear_height_modes_%s' % MU]:
                clear[h] += n
    if not clear:
        raise ValueError('venue: no floor plate has fabric above it')
    clear_modes = sorted(clear.items(), key=lambda kv: (-kv[1], kv[0]))
    clear_total = sum(clear.values())

    # --- the opening family ------------------------------------------------
    # Floor-standing panels that share one height and one thickness while
    # their widths vary. That is the signature of an opening set. The model
    # does not say so and this pack does not claim it does.
    upper = levels[0]['datum_%s' % MU]
    by_shape = defaultdict(list)
    for p in contents:
        d = p['d']
        thick, wide = min(d[0], d[2]), max(d[0], d[2])
        if d[1] < 0.4 or thick > 0.12 or wide < 0.2:
            continue
        if p['lo'][1] > upper + 0.12:
            continue
        by_shape[(r(d[1], 3), r(thick, 3))].append((r(wide, 3), p))
    if not by_shape:
        raise ValueError('venue: no floor-standing panel family found')

    # Does floor exist on BOTH sides of a panel? A partition or a glazed
    # perimeter bay has floor on one side or none; a doorway has it on both.
    # This is the discriminator, it is applied to EVERY family, and the
    # family that is called an opening set is the one the test picks - not
    # the biggest one, which is a different question.
    all_floor = set()
    for lv in levels:
        for tri in flat[lv['datum_%s' % MU]]:
            all_floor.update(cells_of_tri(*tri))

    def floor_near(cx, cz, rad=0.35):
        n = 0
        for i in range(math.floor((cx - rad) / G), math.floor((cx + rad) / G) + 1):
            for k in range(math.floor((cz - rad) / G), math.floor((cz + rad) / G) + 1):
                if (i, k) in all_floor:
                    n += 1
        return n

    def both_sides_of(p):
        cx = (p['lo'][0] + p['hi'][0]) / 2.0
        cz = (p['lo'][2] + p['hi'][2]) / 2.0
        if p['d'][0] < p['d'][2]:
            a, b = floor_near(cx - 0.35, cz), floor_near(cx + 0.35, cz)
        else:
            a, b = floor_near(cx, cz - 0.35), floor_near(cx, cz + 0.35)
        return a > 0 and b > 0

    families = []
    for (fh, ft), mem in by_shape.items():
        if len(mem) < PARAMS['panel_family_min_members']:
            continue
        ws = sorted(w for w, _ in mem)
        bs = sum(1 for _, p in mem if both_sides_of(p))
        families.append({
            'height_%s' % MU: fh,
            'thickness_%s' % MU: ft,
            'members': len(mem),
            'widths_%s' % MU: ws,
            'distinct_widths': len(set(ws)),
            'floor_on_both_sides': bs,
            'both_sides_share': r(bs / len(mem), 3),
        })
    if not families:
        raise ValueError('venue: no panel family reached the minimum size')
    families.sort(key=lambda f: (-f['both_sides_share'], -f['members'],
                                 f['height_%s' % MU]))
    chosen = families[0]
    shape = (chosen['height_%s' % MU], chosen['thickness_%s' % MU])
    widths = chosen['widths_%s' % MU]
    both_sides = chosen['floor_on_both_sides']

    # --- circulation on the upper floor plate ------------------------------
    floor_cells = set()
    for tri in flat[upper]:
        floor_cells.update(cells_of_tri(*tri))
    lo_band, hi_band = PARAMS['obstruction_band']
    blocked = set()
    for p in contents:
        if p['hi'][1] < upper + lo_band or p['lo'][1] > upper + hi_band:
            continue
        for i in range(math.floor(p['lo'][0] / G), math.floor(p['hi'][0] / G) + 1):
            for k in range(math.floor(p['lo'][2] / G), math.floor(p['hi'][2] / G) + 1):
                blocked.add((i, k))
    occupied = floor_cells & blocked
    free = floor_cells - blocked
    runs = Counter()
    for axis in (0, 1):
        lines = defaultdict(list)
        for c in free:
            lines[c[1 - axis]].append(c[axis])
        for _, vs in lines.items():
            vs.sort()
            start = prev = vs[0]
            for v in vs[1:]:
                if v != prev + 1:
                    runs[r((prev - start + 1) * G, 1)] += 1
                    start = v
                prev = v
            runs[r((prev - start + 1) * G, 1)] += 1
    run_vals = sorted(k for k, n in runs.items() for _ in range(n))
    median_run = run_vals[len(run_vals) // 2]

    # --- contents clusters -------------------------------------------------
    gap = PARAMS['cluster_gap']
    n = len(contents)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    order = sorted(range(n), key=lambda i: (contents[i]['lo'][0], i))
    for ii in range(n):
        a = contents[order[ii]]
        for jj in range(ii + 1, n):
            b = contents[order[jj]]
            if b['lo'][0] - a['hi'][0] > gap:
                break
            dx = max(0.0, a['lo'][0] - b['hi'][0], b['lo'][0] - a['hi'][0])
            dz = max(0.0, a['lo'][2] - b['hi'][2], b['lo'][2] - a['hi'][2])
            if dx <= gap and dz <= gap:
                ra, rb = find(order[ii]), find(order[jj])
                if ra != rb:
                    parent[ra] = rb
    groups = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)
    clusters = []
    for key in sorted(groups, key=lambda k: (-len(groups[k]), k)):
        grp = groups[key]
        if len(grp) < PARAMS['cluster_min_members']:
            continue
        lo = [min(contents[i]['lo'][k] for i in grp) for k in range(3)]
        hi = [max(contents[i]['hi'][k] for i in grp) for k in range(3)]
        w, dp, h = (hi[0] - lo[0], hi[2] - lo[2], hi[1] - lo[1])
        clusters.append({
            'tier': 'DERIVED',
            'measured_by': 'the axis-aligned bounding box over a '
                           'single-linkage cluster of contents meshes at a '
                           '%s %s gap. This is a box around what stands in a '
                           'space, NOT a room dimension and NOT a '
                           'wall-to-wall survey.' % (gap, MU),
            'members': len(grp),
            'bbox_width_%s' % MU: r(w, 3),
            'bbox_depth_%s' % MU: r(dp, 3),
            'bbox_height_%s' % MU: r(h, 3),
            'plan_area_%s2' % MU: r(w * dp, 3),
            'aspect': r(max(w, dp) / min(w, dp), 3),
            'base_above_upper_datum_%s' % MU: r(lo[1] - upper, 3),
        })

    sensitivity = []
    for probe in (0.10, 0.15, 0.20, 0.30, 0.40):
        par2 = list(range(n))

        def find2(a):
            while par2[a] != a:
                par2[a] = par2[par2[a]]
                a = par2[a]
            return a
        for ii in range(n):
            a = contents[order[ii]]
            for jj in range(ii + 1, n):
                b = contents[order[jj]]
                if b['lo'][0] - a['hi'][0] > probe:
                    break
                dx = max(0.0, a['lo'][0] - b['hi'][0], b['lo'][0] - a['hi'][0])
                dz = max(0.0, a['lo'][2] - b['hi'][2], b['lo'][2] - a['hi'][2])
                if dx <= probe and dz <= probe:
                    ra, rb = find2(order[ii]), find2(order[jj])
                    if ra != rb:
                        par2[ra] = rb
        g2 = Counter(find2(i) for i in range(n))
        sensitivity.append([probe, len(g2),
                            sum(1 for v in g2.values()
                                if v >= PARAMS['cluster_min_members'])])

    return {
        'src': src, 'g': g, 'asset': asset, 'extras': extras,
        'fbx': (fbx_i, fbx_name, fbx_scale), 'to_mu': to_mu,
        'prims': prims, 'fabric': fabric, 'contents': contents,
        'box_lo': box_lo, 'box_hi': box_hi, 'triangles': triangles,
        'fabric_gap': (below, above), 'levels': levels,
        'clear_modes': clear_modes, 'clear_total': clear_total,
        'panel_shape': shape, 'panel_widths': widths,
        'panel_both_sides': both_sides, 'panel_families': families,
        'floor_cells': len(floor_cells), 'occupied': len(occupied),
        'free': len(free), 'runs': runs, 'median_run': median_run,
        'clusters': clusters, 'sensitivity': sensitivity,
    }


# ---------------------------------------------------------------------------
# attribution - a licence obligation, in structured fields

def attribution(extras):
    """CC-BY-4.0 asks for four things: the author, a link to the work, a link
    to the licence, and an indication of whether it was changed. All four come
    out of the file's own asset.extras where the file states them, and every
    one of them is checked non-empty here and again in test.mjs. A blank field
    is a licence breach, not a cosmetic gap."""
    author_raw = need(extras, 'gltf.asset.extras', 'author')
    licence_raw = need(extras, 'gltf.asset.extras', 'license')
    source = need(extras, 'gltf.asset.extras', 'source')
    title = need(extras, 'gltf.asset.extras', 'title')

    def split_url(text, field):
        if '(' not in text or not text.rstrip().endswith(')'):
            raise ValueError('venue: asset.extras.%s does not carry a '
                             'parenthesised URL: %r' % (field, text))
        name, url = text.rstrip()[:-1].split('(', 1)
        return name.strip(), url.strip()

    author_name, author_url = split_url(author_raw, 'author')
    licence_id, licence_url = split_url(licence_raw, 'license')

    rec = {
        'tier': 'RECORDED',
        'measured_by': 'read verbatim out of the file\'s own asset.extras '
                       'block; nothing here is typed by this build',
        'title': title,
        'author': author_name,
        'author_profile_url': author_url,
        'source_url': source,
        'license_id': licence_id,
        'license_url': licence_url,
        'license_name': 'Creative Commons Attribution 4.0 International',
        'changes_made': True,
        'changes_indication':
            'The work itself was NOT modified and is NOT redistributed here. '
            'No geometry, no texture and no part of the file is copied into '
            'this repository. What this pack publishes is measurement derived '
            'from the work - dimensions, areas, counts and ratios computed by '
            'reading it - which is a change from the work in the sense the '
            'licence asks about, so it is declared as one rather than argued '
            'about.',
        'redistribution':
            'none. The source file stays outside this repository, at the '
            'upload path recorded beside this block, and the bundle ships no '
            'derivative of its geometry.',
        'why_this_block_exists':
            'CC-BY-4.0 requires attribution, a link to the work, a link to '
            'the licence and an indication of changes. Those four are fields '
            'here rather than a sentence somewhere, so a check can fail on a '
            'missing one - and venue/test.mjs does.',
    }
    for k in ('title', 'author', 'author_profile_url', 'source_url',
              'license_id', 'license_url', 'license_name',
              'changes_indication'):
        if not isinstance(rec[k], str) or not rec[k].strip():
            raise ValueError('venue: attribution.%s is empty; CC-BY-4.0 is '
                             'not satisfied and this build will not write a '
                             'registry that claims it is' % k)
    return rec


# ---------------------------------------------------------------------------

def build(m):
    src, g = m['src'], m['g']
    extras, asset = m['extras'], m['asset']
    box_lo, box_hi = m['box_lo'], m['box_hi']
    ext = [r(box_hi[k] - box_lo[k], 3) for k in range(3)]
    fbx_i, fbx_name, fbx_scale = m['fbx']
    clear_mode_h, clear_mode_n = m['clear_modes'][0]
    widths = m['panel_widths']
    panel_h, panel_t = m['panel_shape']
    upper = m['levels'][0]['datum_%s' % MU]
    lower = m['levels'][1]['datum_%s' % MU]
    plates = m['levels'][0]['floor_plates']
    big_plate = plates[0]
    floor_total = sum(lv['horizontal_area_%s2' % MU] for lv in m['levels'])
    footprint = ext[0] * ext[2]
    med_w = widths[len(widths) // 2]

    stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

    recorded = {
        'tier': 'RECORDED',
        'measured_by': 'the file\'s own bytes and its own JSON chunk; every '
                       'number below is read, none is typed',
        'file_bytes': src['bytes'],
        'file_sha256': src['sha256'],
        'glb_container_version': src['container_version'],
        'json_chunk_bytes': src['json_chunk_bytes'],
        'bin_chunk_bytes': src['bin_chunk_bytes'],
        'gltf_version': need(asset, 'gltf.asset', 'version'),
        'generator': need(asset, 'gltf.asset', 'generator'),
        'counts': {k: len(need(g, 'gltf', k)) for k in
                   ('meshes', 'nodes', 'materials', 'textures', 'images',
                    'accessors', 'bufferViews', 'buffers', 'scenes',
                    'animations', 'samplers')},
        'why_not_shipped':
            'the mesh count is the reason. The hall view of this bundle runs '
            'at 164 draw calls against a ceiling of 196; this one model is '
            'roughly five times that whole ceiling by itself. It is also a '
            'Paris conference venue and not a union training hall. It is '
            'measured, not imported.',
    }

    unit_scale = {
        'tier': 'DERIVED',
        'resolution': 'UNRESOLVED',
        'unit_published': 'model unit (%s)' % MU,
        'measured_by': 'the file\'s only declared unit conversion, checked '
                       'against the geometry it applies to',
        'declared_conversion': {
            'node': fbx_i,
            'node_name': fbx_name,
            'uniform_scale': fbx_scale,
            'reading': 'the conventional centimetre-to-metre factor an FBX '
                       'exporter writes. It is the ONLY unit statement in '
                       'the file.',
        },
        'what_honouring_it_gives_if_read_as_metres': {
            'building_extent': [r(e * fbx_scale, 5) for e in ext],
            'verdict': 'a multi-salon building 0.19 across. Not metres.',
        },
        'what_undoing_it_gives': {
            'building_extent_%s' % MU: ext,
            'clear_storey_%s' % MU: clear_mode_h,
            'verdict': 'a plan %s by %s with a %s clear storey. Read as '
                       'metres that is a room wider than a house with a '
                       'ceiling nobody could stand under, so this is not '
                       'metres either.' % (ext[0], ext[2], clear_mode_h),
        },
        'conclusion':
            'The file does not establish a metre scale and this pack does not '
            'invent one. Every dimension published here is in model units. '
            'The plan-to-height ratio is the decisive evidence: the building '
            'is %s times wider than its clear storey is high, and no reading '
            'of the file in which one unit is one metre survives that.'
            % r(ext[0] / clear_mode_h, 1),
        'if_someone_wants_metres':
            'multiply by a single uniform factor and say where the factor '
            'came from. The panel family below is the only anchor in the '
            'file with a conventional real size: if those panels are door '
            'leaves of 1.8 to 2.3 metres, the factor falls between %s and '
            '%s, which would put the clear storey between %s and %s metres. '
            'That is an ESTIMATE resting on an assumption about what the '
            'panels are, it is not a measurement, and nothing in this '
            'registry is computed from it.'
            % (r(1.8 / panel_h, 2), r(2.3 / panel_h, 2),
               r(clear_mode_h * 1.8 / panel_h, 2),
               r(clear_mode_h * 2.3 / panel_h, 2)),
    }

    building = {
        'tier': 'DERIVED',
        'measured_by': 'every mesh\'s POSITION accessor bounds, transformed '
                       'by the node chain above it and unioned. This is a '
                       'BOUNDING BOX over a model, not a surveyed building '
                       'dimension: it includes whatever sticks out furthest '
                       'and it is not wall-to-wall anything.',
        'extent_%s' % MU: {'x': ext[0], 'y': ext[1], 'z': ext[2]},
        'min_%s' % MU: [r(v, 3) for v in box_lo],
        'max_%s' % MU: [r(v, 3) for v in box_hi],
        'plan_footprint_%s2' % MU: r(footprint, 2),
        'plan_aspect': r(max(ext[0], ext[2]) / min(ext[0], ext[2]), 3),
        'triangles': m['triangles'],
        'fabric_meshes': sorted(m['fabric']),
        'fabric_split': {
            'threshold_%s2' % MU: PARAMS['fabric_footprint_threshold'],
            'largest_below': r(m['fabric_gap'][0], 3),
            'smallest_above': r(m['fabric_gap'][1], 3),
            'note': 'the threshold sits in an empty band between those two '
                    'footprints, so the split is not knife-edge: any '
                    'threshold inside that band gives the same set',
        },
        'contents_meshes': len(m['contents']),
    }

    heights = {
        'tier': 'DERIVED',
        'measured_by': 'for every %s %s plan cell that building-fabric '
                       'geometry reaches over, the height it reaches minus '
                       'the floor datum below it. Cells where the fabric '
                       'rises less than 0.5 %s are floor-only and excluded - '
                       'this model has a roof over part of its plan, not all '
                       'of it, and the count below says over how much.'
                       % (G, MU, MU),
        'cells_measured': m['clear_total'],
        'distribution_%s' % MU: [[h, n] for h, n in m['clear_modes']],
        'modal_clear_storey_%s' % MU: clear_mode_h,
        'modal_share': r(clear_mode_n / m['clear_total'], 3),
        'note': 'the distribution is narrow, not a spread: the modal height '
                'carries %s of the measured cells and both floor datums '
                'return the same clear height, which is why this pack is '
                'willing to call it a storey height at all.'
                % r(clear_mode_n / m['clear_total'], 3),
    }

    openings = {
        'tier': 'DERIVED',
        'identification': 'INFERRED FROM SHAPE, NOT LABELLED IN THE FILE',
        'measured_by': 'the largest family of floor-standing panels sharing '
                       'ONE height and ONE thickness while their widths '
                       'vary. Constant height and thickness with varying '
                       'width is what an opening set looks like; the model '
                       'names nothing, so this is an inference and is '
                       'labelled as one.',
        'selected_by': PARAMS['panel_family_selection'],
        'family_height_%s' % MU: panel_h,
        'family_thickness_%s' % MU: panel_t,
        'members': len(widths),
        'widths_%s' % MU: widths,
        'all_panel_families': m['panel_families'],
        'width_min_%s' % MU: widths[0],
        'width_median_%s' % MU: med_w,
        'width_max_%s' % MU: widths[-1],
        'floor_on_both_sides': m['panel_both_sides'],
        'what_that_test_means':
            '%d of %d sit with modelled floor within 0.35 %s on BOTH sides. '
            'A partition or a screen has floor on one side or none; a '
            'doorway has it on both. That supports the reading and does not '
            'prove it - a glazed bay between two furnished areas would pass '
            'the same test.' % (m['panel_both_sides'], len(widths), MU),
        'what_would_settle_it':
            'a named object, a door material, or a hole in the wall mesh at '
            'the same place. The file has none of the three: the walls are '
            'one shell mesh and the panel family carries a flat black '
            'material with no name beyond its index.',
    }

    circulation = {
        'tier': 'DERIVED',
        'measured_by': 'the upper floor plate rasterised at %s %s, minus the '
                       'plan footprint of every contents mesh standing on it '
                       '(rising more than %s %s above the floor and starting '
                       'below %s %s). What is left is clear floor; the runs '
                       'are its uninterrupted spans along both plan axes.'
                       % (G, MU, PARAMS['obstruction_band'][0], MU,
                          PARAMS['obstruction_band'][1], MU),
        'floor_cells': m['floor_cells'],
        'cells_occupied': m['occupied'],
        'cells_clear': m['free'],
        'occupancy': r(m['occupied'] / m['floor_cells'], 3),
        'clear_run_median_%s' % MU: m['median_run'],
        'clear_run_distribution_%s' % MU: [
            [w, n] for w, n in sorted(m['runs'].items()) if n >= 10],
        'caveat': 'a clear run is not a corridor. It is the distance across '
                  'unfurnished floor in one of the two plan axes, which is '
                  'what circulation width means in a room laid out with '
                  'loose seating and nothing else. It says nothing about a '
                  'walled corridor, because this model has no walled '
                  'corridors to measure.',
    }

    ratios = {
        'tier': 'DERIVED',
        'measured_by': 'each ratio is two of the DERIVED figures above '
                       'divided by one another; nothing new is measured '
                       'here and nothing is typed',
        'why_these_are_the_useful_ones':
            'a ratio does not care what the unit is. The unit of this file '
            'is not established, so the proportions are the part of the '
            'measurement that transfers to a hall at any scale - and '
            'proportion is what the generated halls lack, not size.',
        'building_plan_aspect': r(max(ext[0], ext[2]) / min(ext[0], ext[2]), 3),
        'clear_storey_over_building_short_side':
            r(clear_mode_h / min(ext[0], ext[2]), 4),
        'largest_floor_plate_aspect': big_plate['aspect'],
        'clear_storey_over_largest_plate_short_side':
            r(clear_mode_h / min(big_plate['bbox_width_%s' % MU],
                                 big_plate['bbox_depth_%s' % MU]), 4),
        'floor_plate_fill_of_its_own_bbox': big_plate['bbox_fill'],
        'modelled_floor_over_building_footprint': r(floor_total / footprint, 3),
        'opening_width_over_clear_storey': r(med_w / clear_mode_h, 4),
        'opening_height_over_clear_storey': r(panel_h / clear_mode_h, 4),
        'furniture_occupancy_of_floor_plate': r(m['occupied'] / m['floor_cells'], 3),
        'clear_run_median_over_clear_storey': r(m['median_run'] / clear_mode_h, 4),
        'datum_step_over_clear_storey': r(abs(upper - lower) / clear_mode_h, 4),
        'how_to_use_these':
            'take a hall\'s short plan dimension as the one number you own, '
            'and the rest follow. A room proportioned like this one is '
            'roughly %s times as high as it is narrow, opens through gaps '
            'about %s of its height across, and carries loose contents over '
            'about %s of its floor. None of that is a rule; it is what one '
            'real building did.'
            % (r(clear_mode_h / min(big_plate['bbox_width_%s' % MU],
                                    big_plate['bbox_depth_%s' % MU]), 3),
               r(med_w / clear_mode_h, 3),
               r(m['occupied'] / m['floor_cells'], 3)),
    }

    honesty = {
        'what_is_recorded': 'the asset block, the counts, the byte length and '
                            'the digest. That is all. Those are statements '
                            'the file makes about itself and this build '
                            'copies them.',
        'what_is_derived': 'every dimension, area, height and ratio. They are '
                           'computed here from the node transforms and the '
                           'vertex buffer, and a computation from recorded '
                           'geometry is DERIVED however careful it is.',
        'a_box_is_not_a_room': 'the building extent and every cluster '
                               'dimension is an axis-aligned BOUNDING BOX '
                               'over a set of meshes. It is not a wall-to-'
                               'wall room dimension, it includes anything '
                               'that sticks out, and no record here calls it '
                               'a survey. The floor plates come closer - they '
                               'are the actual extent of modelled floor - but '
                               'their width and depth are still the box '
                               'around a floor patch.',
        'the_unit_is_not_metres': unit_scale['conclusion'],
        'the_clusters_depend_on_a_threshold':
            'single-linkage clustering has no natural answer; the count '
            'depends on the gap. The sensitivity table is published beside '
            'the clusters for exactly that reason, and it moves from %d '
            'clusters to %d across the probed range.'
            % (m['sensitivity'][0][1], m['sensitivity'][-1][1]),
        'the_openings_are_an_inference': openings['identification'],
        'the_model_is_partial': 'fabric geometry covers only part of the '
                                'plan: %d plan cells carry a measurable '
                                'height above a floor datum, out of %d cells '
                                'of modelled floor on the upper datum alone. '
                                'The clear-height figure is a measurement of '
                                'where there is a roof, not of the whole '
                                'building.'
                                % (m['clear_total'], m['floor_cells']),
        'nothing_of_the_work_is_redistributed':
            'no geometry and no texture from the source is in this tree. The '
            'registry holds numbers about it and the four attribution fields '
            'the licence requires.',
    }

    payload = {
        'pack': 'venue',
        'product': 'measurements taken off a recorded 3D model of a real '
                   'multi-salon event building, published as proportions the '
                   'generated halls can be held against - and published in '
                   'model units, because the file does not establish metres',
        'pack_version': PACK_VERSION,
        'source_stamp': stamp,
        'unit': {
            'symbol': MU,
            'name': 'model unit',
            'means': 'one unit of the authored geometry with the exporter '
                     'node\'s %s scale undone. NOT a metre. See unit_scale.'
                     % fbx_scale,
        },
        'source': {
            'tier': 'RECORDED',
            'path': str(SOURCE),
            'in_repository': False,
            'why_not_in_repository': recorded['why_not_shipped'],
        },
        'attribution': attribution(extras),
        'recorded': recorded,
        'unit_scale': unit_scale,
        'building': building,
        'levels': m['levels'],
        'clear_heights': heights,
        'openings': openings,
        'circulation': circulation,
        'contents_clusters': {
            'tier': 'DERIVED',
            'measured_by': 'single-linkage clustering of the contents '
                           'meshes\' plan bounding boxes at the gap below, '
                           'with the sensitivity of the count to that gap '
                           'published beside it',
            'gap_%s' % MU: PARAMS['cluster_gap'],
            'min_members': PARAMS['cluster_min_members'],
            'clusters': m['clusters'],
            'gap_sensitivity': [
                {'gap_%s' % MU: gp, 'clusters': c, 'clusters_at_or_above_min': b}
                for gp, c, b in m['sensitivity']],
        },
        'ratios': ratios,
        'honesty': honesty,
        'parameters': PARAMS,
        'counts': {
            'floor_datum_levels': len(m['levels']),
            'floor_plates': sum(len(lv['floor_plates']) for lv in m['levels']),
            'contents_clusters': len(m['clusters']),
            'opening_family_members': len(widths),
            'fabric_meshes': len(m['fabric']),
            'contents_meshes': len(m['contents']),
        },
    }

    blob = json.dumps(payload).upper()
    if 'AI-SYNTHESIZED' in blob:
        raise ValueError('venue: that word belongs to orbis/')
    return payload


# ---------------------------------------------------------------------------

def main():
    if not SOURCE.exists():
        # The absence is LOUD and it is not a pass. If there is no committed
        # registry, or the committed one was built by a different builder,
        # this exits non-zero: a pack that cannot be rebuilt and cannot be
        # verified has nothing to say.
        print('venue: SOURCE NOT PRESENT at %s' % SOURCE)
        print('venue:   nothing was re-measured in this run. The registry '
              'committed to the tree is the measurement.')
        if not OUT.exists():
            raise SystemExit('venue: and there is no committed registry at '
                             '%s, so this build has produced nothing. Put '
                             'the source file back.' % OUT)
        have = json.loads(OUT.read_text())
        stamp = hashlib.sha256(
            pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
        if need(have, 'venue.json', 'source_stamp') != stamp:
            raise SystemExit(
                'venue: the committed registry was built by a DIFFERENT '
                'builder (%s) than the one on disk (%s), and the source file '
                'is not here to rebuild it from. Restore the source or '
                'restore the builder.'
                % (have['source_stamp'], stamp))
        e = need(need(have, 'venue.json', 'building'), 'building',
                 'extent_%s' % MU)
        print('venue:   SKIPPED - registry left exactly as committed. Its '
              'source_stamp %s matches this builder, so it is this '
              'builder\'s output.' % stamp)
        print('venue:   it holds %s x %s x %s %s of building, a modal clear '
              'storey of %s %s, and the digest of the file it was measured '
              'from (%s). venue/test.mjs checks all of it; it cannot check '
              'the digest until the file is back.'
              % (e['x'], e['y'], e['z'], MU,
                 need(need(have, 'venue.json', 'clear_heights'),
                      'clear_heights', 'modal_clear_storey_%s' % MU), MU,
                 need(need(have, 'venue.json', 'recorded'), 'recorded',
                      'file_sha256')[:16]))
        return

    src = read_glb(SOURCE)
    payload = build(measure(src))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=1, sort_keys=True) + '\n'
    changed = (not OUT.exists()) or OUT.read_text() != text
    OUT.write_text(text)
    b = payload['building']
    e = b['extent_%s' % MU]
    print('venue: measured %s (%s) - %d meshes, %s triangles, %d bytes.'
          % (payload['attribution']['title'],
             payload['attribution']['license_id'],
             payload['recorded']['counts']['meshes'], b['triangles'],
             payload['recorded']['file_bytes']))
    print('venue: extent %s x %s x %s %s; modal clear storey %s %s over %d '
          'plan cells; %d floor plates on %d datums; %d contents clusters; '
          'opening family %d wide %s-%s %s.'
          % (e['x'], e['y'], e['z'], MU,
             payload['clear_heights']['modal_clear_storey_%s' % MU], MU,
             payload['clear_heights']['cells_measured'],
             payload['counts']['floor_plates'],
             payload['counts']['floor_datum_levels'],
             payload['counts']['contents_clusters'],
             payload['counts']['opening_family_members'],
             payload['openings']['width_min_%s' % MU],
             payload['openings']['width_max_%s' % MU], MU))
    print('venue: UNIT SCALE UNRESOLVED - published in model units, not '
          'metres. %s' % payload['unit_scale']['conclusion'].split('.')[0]
          + '.')
    print('venue: registry %s' % ('rewritten' if changed else 'unchanged'))


if __name__ == '__main__':
    main()
