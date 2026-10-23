"""
The world tiles: the GIS-based worlds cut into glTF 2.0 binary (.glb) tiles,
each with a GeoPose anchor where the world is on the globe, plus one plain-JSON
manifest per world in the shape the Sneeze project's own example docs show.

This module is imported by spatial/build.py (one builder, one source stamp
line in rebuild_all) and has no side effects on import.

WHAT IS VERIFIED, AND WHERE FROM. Every fact about what Sneeze loads is
recorded with its URL in the registry this module returns
(`sneeze_documented`) and every field of the manifest is marked `documented`
(the Sneeze project's own docs or source say it) or `proposed` (nothing
primary says it). Nothing here has been opened in Sneeze or Artemis.

WHAT THE TILES ARE. Geometry is flat map geometry cut from registries this
repository already owns:
  parish-<fips>   13 Louisiana parishes   parishes/registry + parishes/maps/*
  county-<fips>    9 Bay Area counties    bayarea/registry   + bayarea/maps/*
  wild-<id>        4 authored wilds       wilds/registry + wilds/core.mjs
  campus-<slug>    3 campuses with halls  geo3d/registry (SCHEMATIC footprints)
Each layer of each tile carries its provenance word; a tile as a whole is
labelled with the WEAKEST word among its layers, so a tile is never more
recorded than its least-recorded layer.

Deliberately not exported (budget and honesty): local streets (thousands per
parish), the page-rule buildings (generated in the page from a hash, AUTHORED),
caches and hollows of the wilds (hidden play), real elevation (none is held).
"""
import hashlib
import json
import pathlib
import struct
import subprocess

import numpy as np

# ------------------------------------------------------------------ budget ---
# Constants a suite reads back and never loosens. Per-tile and total byte
# ceilings for the .glb files, and the grid size of the wilds terrain.
TILE_MAX_BYTES = 750_000
TOTAL_MAX_BYTES = 8_000_000
WILDS_GRID_N = 65
# Sneeze documents Resource.sReference as a fabric-relative URL held in a
# 128-byte field (src/context/scene/Scene.md): a longer reference is cut.
SREFERENCE_MAX_BYTES = 128

# Provenance vocabulary, strongest first. A tile takes the LAST (weakest) word
# found among its layers.
TIERS = ['RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED']

# The module the Sneeze example docs use to read Data.Scene and build nodes.
# Its source is in SneezeDoc/examples/wasm/map; the built file is hosted on
# RP1's CDN in the docs and was NOT reachable from this build (egress proxy
# 403), so it is neither fetched, vendored nor hashed here.
MAP_MODULE_URL = 'https://cdn.rp1.com/sneeze/examples/wasm/map.wasm'

SNEEZE_DOCS = 'https://github.com/MetaversalCorp/SneezeDoc/blob/main/docs'
SNEEZE_SRC = 'https://github.com/MetaversalCorp/Sneeze/blob/main'
RAW = 'https://raw.githubusercontent.com/MetaversalCorp'

# Every verified fact, with its primary URL. The suite checks each URL is a
# MetaversalCorp URL and that the list is what the field table cites.
VERIFIED = [
    {'id': 'licence',
     'fact': 'Sneeze is Apache-2.0 licensed (README: "Apache License 2.0"); the '
             'repository page showed no published release when read, and its '
             'GitHub description field was empty',
     'url': 'https://github.com/MetaversalCorp/Sneeze'},
    {'id': 'glb-loaded',
     'fact': 'a node\'s Resource.sReference is fetched by URL and sniffed by '
             'content: the ASCII magic "glTF" (binary GLB) or a leading "{" '
             '(glTF JSON) is parsed as glTF via fastgltf; anything else is '
             'decoded as an image texture',
     'url': f'{RAW}/Sneeze/main/src/context/scene/Scene.md'},
    {'id': 'glb-axes',
     'fact': 'glTF is right-handed Y-up and Sneeze\'s world is right-handed '
             'Z-up; every imported model is converted at import with '
             'glTF (x, y, z) -> world (x, -z, y)',
     'url': f'{RAW}/Sneeze/main/src/context/viewport/GltfMesh.cpp'},
    {'id': 'texture-cap',
     'fact': 'imported textures are downscaled to at most 1024 px; these tiles '
             'carry no textures',
     'url': f'{RAW}/Sneeze/main/src/context/viewport/GltfMesh.cpp'},
    {'id': 'manifest-is-msf',
     'fact': 'a fabric is described by an MSF manifest: JSON, either a JWS '
             'compact serialization (signed) or plain unsigned JSON; Parse '
             'accepts both and unsigned JSON gets a synthetic fingerprint '
             'that is "100% untrustworthy"',
     'url': f'{RAW}/Sneeze/main/src/context/msf/MsfFile.md'},
    {'id': 'manifest-shape',
     'fact': 'the plain-JSON example manifest has Container, Services '
             '(empty list), Modules [{sUrl}] and Data.Scene; a node has '
             'Head.Self ("P-?"), Name, Resource.sReference, optional '
             'Transform {Position [x,y,z] metres, Rotation quaternion '
             '[x,y,z,w], Scale} relative to its parent, and aChildren',
     'url': f'{RAW}/SneezeDoc/main/docs/examples/02-stool-and-bucket.md'},
    {'id': 'manifest-example-01',
     'fact': 'the smallest working fabric is stool.json: one node whose '
             'Resource.sReference is assets/Stool.glb, read by a stock '
             'map.wasm module from Data.Scene',
     'url': f'{RAW}/SneezeDoc/main/docs/examples/01-stool.md'},
    {'id': 'unsigned-caveat',
     'fact': 'unsigned plain JSON "works today ... but it is not how a fabric '
             'is meant to be published, and it may not always work"; browsers '
             'will expect signed fabrics',
     'url': f'{RAW}/SneezeDoc/main/docs/examples/01-stool.md'},
    {'id': 'relative-urls',
     'fact': 'an address without scheme:// is relative to the fabric file; '
             'a leading / starts at the host root; .. steps up a folder',
     'url': f'{RAW}/SneezeDoc/main/docs/examples/01-stool.md'},
    {'id': 'own-hosting',
     'fact': 'the docs say to host your own copies of the module and assets '
             'and not depend on RP1\'s server',
     'url': f'{RAW}/SneezeDoc/main/docs/examples/01-stool.md'},
    {'id': 'load-flow',
     'fact': 'loading a fabric = fetch the MSF by URL, parse, verify '
             'signature and chain, open a container, fetch the declared WASM '
             'modules; the host-function surface by which a module builds '
             'the scene is "partially implemented"',
     'url': f'{RAW}/SneezeDoc/main/docs/architecture/fabric-loading.md'},
    {'id': 'data-block',
     'fact': 'Data is "a general block of information the fabric carries for '
             'its modules to read; you can put anything you want in it"; the '
             'stock map module reads Data.Scene',
     'url': f'{RAW}/SneezeDoc/main/docs/examples/01-stool.md'},
    {'id': 'no-geopose-doc',
     'fact': 'GeoPose, latitude/longitude and a fabric-discovery service do '
             'not appear in the Sneeze README, scene, msf or fabric-loading '
             'docs read; the standards page names the OGC only as "relevant '
             'to anchoring fabrics to physical locations"',
     'url': f'{RAW}/SneezeDoc/main/docs/overview/standards.md'},
]

# ------------------------------------------------------------- field table ---
# One row per manifest / tile field: documented (cites VERIFIED ids) or
# proposed (no primary source). The suite checks the manifests use no field
# that is not in this table, and that every row says which it is.
FIELD_STATUS = [
    ('manifest.Container', 'documented', ['manifest-shape']),
    ('manifest.Services', 'documented', ['manifest-shape']),
    ('manifest.Modules[].sUrl', 'documented', ['manifest-shape']),
    ('manifest.Modules[].sHash', 'documented', ['manifest-example-01']),
    ('manifest.Data.Scene', 'documented', ['manifest-example-01', 'data-block']),
    ('node.Head.Self', 'documented', ['manifest-shape']),
    ('node.Name', 'documented', ['manifest-shape']),
    ('node.Resource.sReference', 'documented', ['glb-loaded', 'manifest-shape']),
    ('node.Transform.Position', 'documented', ['manifest-shape']),
    ('node.aChildren', 'documented', ['manifest-shape']),
    ('tile.glb_2_0_binary', 'documented', ['glb-loaded']),
    ('tile.axes_y_up_to_z_up', 'documented', ['glb-axes']),
    ('manifest.unsigned_plain_json', 'documented', ['manifest-is-msf', 'unsigned-caveat']),
    ('manifest.Modules[0].sUrl = the stock map module on the RP1 CDN', 'documented', ['manifest-example-01', 'own-hosting']),
    ('manifest.Data.Anchors (GeoPose sidecar)', 'proposed', []),
    ('manifest.Data.Provenance (sidecar)', 'proposed', []),
    ('world horizontal axes are east/north (ENU)', 'proposed', []),
    ('GeoPose anchor consumed by any Sneeze component', 'proposed', []),
    ('attaching one manifest to another (child fabrics)', 'proposed', []),
    ('camera / render scale at 10-100 km tile extents', 'proposed', []),
    ('a tile this size loads inside Sneeze\'s frame budget', 'proposed', []),
    ('signing (JWS, X.509 chain)', 'proposed', []),
]

# ---------------------------------------------------------------- helpers ---
def need(obj, key, where):
    """One key, or a named failure. No default arm."""
    if not isinstance(obj, dict):
        raise TypeError(f'tiles: {where}: expected an object to read {key!r} from')
    if key not in obj:
        raise KeyError(f'tiles: {where}: no key {key!r} (it holds {sorted(obj)[:12]})')
    return obj[key]


def weakest(words):
    order = {w: i for i, w in enumerate(TIERS)}
    for w in words:
        if w not in order:
            raise ValueError(f'tiles: provenance word {w!r} is not one of {TIERS}')
    return max(words, key=lambda w: order[w])


def hex_rgb(h):
    h = h.lstrip('#')
    assert len(h) == 6, h
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


# ---------------------------------------------------------------- geometry ---
def ring_area(ring):
    a = 0.0
    for i in range(len(ring)):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % len(ring)]
        a += x0 * y1 - x1 * y0
    return a / 2


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _in_tri(p, a, b, c):
    d1, d2, d3 = _cross(a, b, p), _cross(b, c, p), _cross(c, a, p)
    neg = d1 < 0 or d2 < 0 or d3 < 0
    pos = d1 > 0 or d2 > 0 or d3 > 0
    return not (neg and pos)


def ear_clip(ring):
    """Triangulate one simple ring (no holes) by ear clipping.
    Returns index triples into `ring`, all counter-clockwise in the ring's
    own (x, y) plane. Fails by name when the ring is not simple enough."""
    pts = list(ring)
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    n = len(pts)
    if n < 3:
        raise ValueError('tiles: a ring with fewer than 3 distinct vertices')
    idx = list(range(n))
    if ring_area(pts) < 0:
        idx.reverse()
    tris = []
    guard = 0
    while len(idx) > 3:
        guard += 1
        if guard > 4 * n * n:
            raise ValueError('tiles: ear clipping did not terminate (ring is not simple)')
        clipped = False
        m = len(idx)
        for k in range(m):
            i0, i1, i2 = idx[(k - 1) % m], idx[k], idx[(k + 1) % m]
            a, b, c = pts[i0], pts[i1], pts[i2]
            if _cross(a, b, c) <= 1e-9:
                continue  # reflex or degenerate
            if any(_in_tri(pts[j], a, b, c) and pts[j] not in (a, b, c)
                   for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((i0, i1, i2))
            del idx[k]
            clipped = True
            break
        if not clipped:
            # a collinear sliver: drop the flattest vertex and carry on
            m = len(idx)
            flat = min(range(m), key=lambda k: abs(_cross(
                pts[idx[(k - 1) % m]], pts[idx[k]], pts[idx[(k + 1) % m]])))
            del idx[flat]
    tris.append(tuple(idx))
    return pts, tris


def tri_area_sum(pts, tris):
    return sum(abs(_cross(pts[a], pts[b], pts[c])) / 2 for a, b, c in tris)


def _seg_cross(p1, p2, p3, p4):
    """Proper crossing point of segments p1p2 and p3p4, or None."""
    d1x, d1y = p2[0] - p1[0], p2[1] - p1[1]
    d2x, d2y = p4[0] - p3[0], p4[1] - p3[1]
    den = d1x * d2y - d1y * d2x
    if abs(den) < 1e-12:
        return None
    t = ((p3[0] - p1[0]) * d2y - (p3[1] - p1[1]) * d2x) / den
    u = ((p3[0] - p1[0]) * d1y - (p3[1] - p1[1]) * d1x) / den
    if 1e-9 < t < 1 - 1e-9 and 1e-9 < u < 1 - 1e-9:
        return (p1[0] + t * d1x, p1[1] + t * d1y)
    return None


def simple_loops(ring, depth=0):
    """Split a ring that crosses itself into simple loops at each crossing.
    The coarse 1:10m county outlines hold a few bow-ties; a loop is a
    ring with no crossing. Returns (loops, number_of_crossings_split)."""
    pts = [tuple(q) for q in ring]
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    n = len(pts)
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            x = _seg_cross(pts[i], pts[(i + 1) % n], pts[j], pts[(j + 1) % n])
            if x is not None:
                loop1 = [x] + pts[i + 1:j + 1]
                loop2 = pts[j + 1:] + pts[:i + 1] + [x]
                if depth > 20:
                    raise ValueError('tiles: outline crosses itself too many times to split')
                a, na = simple_loops(loop1, depth + 1)
                b, nb = simple_loops(loop2, depth + 1)
                return a + b, na + nb + 1
    return [pts], 0


class Layer:
    """One glTF primitive: positions (x, y, z) in glTF axes, normals, indices."""

    def __init__(self, name, provenance, source, rgb, note):
        assert provenance in TIERS, (name, provenance)
        self.name, self.provenance, self.source = name, provenance, source
        self.rgb, self.note = rgb, note
        self.pos, self.nrm, self.col, self.idx = [], [], [], []

    def add_verts(self, pts, normal=(0.0, 1.0, 0.0), colors=None):
        base = len(self.pos)
        for k, p in enumerate(pts):
            self.pos.append(tuple(float(v) for v in p))
            self.nrm.append(tuple(normal) if not isinstance(normal, list) else tuple(normal[k]))
            if colors is not None:
                self.col.append(tuple(colors[k]))
        return base

    def add_tri(self, a, b, c):
        self.idx.extend((a, b, c))

    def add_up_tri(self, a, b, c):
        """Add a triangle whose normal faces +Y (up), whatever its input order."""
        p, q, r = self.pos[a], self.pos[b], self.pos[c]
        ux, uz = q[0] - p[0], q[2] - p[2]
        vx, vz = r[0] - p[0], r[2] - p[2]
        ny = uz * vx - ux * vz  # y of (q-p) x (r-p)
        if abs(ny) < 1e-12:
            return
        self.idx.extend((a, b, c) if ny > 0 else (a, c, b))

    @property
    def triangles(self):
        return len(self.idx) // 3


def to_gl(x_east, y_north, h=0.0):
    """Repo scene convention (geo3d): x = east, y(up) = height, z = -north."""
    return (x_east, h, -y_north)


def polygon_layer(layer, rings_local, y):
    """Fill rings (each a list of [east, north]) at height y, up-facing.
    A ring that crosses itself is split into simple loops first. Returns
    (area of the loops, number of crossings split)."""
    area_in = 0.0
    area_out = 0.0
    splits = 0
    for ring in rings_local:
        loops, k = simple_loops(ring)
        splits += k
        for loop in loops:
            if len({tuple(q) for q in loop}) < 3 or abs(ring_area(loop)) < 1e-6:
                continue
            pts, tris = ear_clip(loop)
            base = layer.add_verts([to_gl(px, py, y) for px, py in pts])
            for a, b, c in tris:
                layer.add_up_tri(base + a, base + b, base + c)
            area_in += abs(ring_area(pts))
            area_out += tri_area_sum(pts, tris)
    if abs(area_in - area_out) > 1e-6 * max(1.0, area_in):
        raise ValueError(f'tiles: layer {layer.name}: triangulated area {area_out} '
                         f'differs from loop area {area_in}')
    return area_in, splits


def ribbon_layer(layer, polyline, width, y, miter_cap=2.0):
    """A strip of `width` metres along a polyline of [east, north]."""
    pts = [tuple(p) for p in polyline]
    # drop repeated consecutive points
    clean = [pts[0]]
    for p in pts[1:]:
        if p != clean[-1]:
            clean.append(p)
    pts = clean
    if len(pts) < 2:
        return 0
    n = len(pts)
    hw = width / 2
    left, right = [], []
    for i, p in enumerate(pts):
        if i == 0:
            dx, dy = pts[1][0] - p[0], pts[1][1] - p[1]
            ln = (dx * dx + dy * dy) ** 0.5
            nx, ny, s = -dy / ln, dx / ln, 1.0
        elif i == n - 1:
            dx, dy = p[0] - pts[i - 1][0], p[1] - pts[i - 1][1]
            ln = (dx * dx + dy * dy) ** 0.5
            nx, ny, s = -dy / ln, dx / ln, 1.0
        else:
            d0x, d0y = p[0] - pts[i - 1][0], p[1] - pts[i - 1][1]
            d1x, d1y = pts[i + 1][0] - p[0], pts[i + 1][1] - p[1]
            l0 = (d0x * d0x + d0y * d0y) ** 0.5
            l1 = (d1x * d1x + d1y * d1y) ** 0.5
            n0 = (-d0y / l0, d0x / l0)
            n1 = (-d1y / l1, d1x / l1)
            mx, my = n0[0] + n1[0], n0[1] + n1[1]
            ml = (mx * mx + my * my) ** 0.5
            if ml < 1e-9:
                nx, ny, s = n0[0], n0[1], 1.0
            else:
                nx, ny = mx / ml, my / ml
                cosh = nx * n0[0] + ny * n0[1]
                s = min(1.0 / max(cosh, 1e-6), miter_cap)
        left.append((p[0] + nx * hw * s, p[1] + ny * hw * s))
        right.append((p[0] - nx * hw * s, p[1] - ny * hw * s))
    base = layer.add_verts([to_gl(*q, y) for q in left] + [to_gl(*q, y) for q in right])
    for i in range(n - 1):
        l0, l1, r0, r1 = base + i, base + i + 1, base + n + i, base + n + i + 1
        layer.add_up_tri(l0, r0, l1)
        layer.add_up_tri(l1, r0, r1)
    return n - 1


def box_layer(layer, corners_xz, y0, y1):
    """An extruded footprint: 4 corners (x, z in glTF axes), floor y0, roof y1."""
    assert len(corners_xz) == 4
    cx = sum(c[0] for c in corners_xz) / 4
    cz = sum(c[1] for c in corners_xz) / 4
    # order the corners counter-clockwise seen from above (+Y down onto x/z)
    ordered = sorted(corners_xz, key=lambda c: np.arctan2(c[1] - cz, c[0] - cx))
    ring = [(c[0], c[1]) for c in ordered]
    # roof
    base = layer.add_verts([(x, y1, z) for x, z in ring], (0.0, 1.0, 0.0))
    layer.add_up_tri(base, base + 1, base + 2)
    layer.add_up_tri(base, base + 2, base + 3)
    # four walls, each with its own outward normal
    for i in range(4):
        (x0, z0), (x1, z1) = ring[i], ring[(i + 1) % 4]
        ex, ez = x1 - x0, z1 - z0
        ln = (ex * ex + ez * ez) ** 0.5
        nrm = (ez / ln, 0.0, -ex / ln)
        b = layer.add_verts([(x0, y0, z0), (x1, y0, z1), (x1, y1, z1), (x0, y1, z0)], nrm)
        for tri in ((b, b + 1, b + 2), (b, b + 2, b + 3)):
            p, q, r = (layer.pos[t] for t in tri)
            u = (q[0] - p[0], q[1] - p[1], q[2] - p[2])
            v = (r[0] - p[0], r[1] - p[1], r[2] - p[2])
            cr = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            if cr[0] * nrm[0] + cr[1] * nrm[1] + cr[2] * nrm[2] > 0:
                layer.add_tri(*tri)
            else:
                layer.add_tri(tri[0], tri[2], tri[1])


# --------------------------------------------------------------- glb writer ---
def _pad4(b, fill=b'\x00'):
    return b + fill * (-len(b) % 4)


def write_glb(path, tile_id, layers, asset_extras):
    """Serialise layers as glTF 2.0 binary: header, JSON chunk, BIN chunk.
    One mesh, one primitive per layer, one material per layer. No textures,
    no extensions, no animation, no skin: nothing a loader must guess at."""
    blob = bytearray()
    views, accessors, prims, mats = [], [], [], []

    def add_view(data, target):
        off = len(blob)
        blob.extend(data)
        blob.extend(b'\x00' * (-len(blob) % 4))
        views.append({'buffer': 0, 'byteOffset': off, 'byteLength': len(data), 'target': target})
        return len(views) - 1

    for ly in layers:
        if not ly.idx:
            raise ValueError(f'tiles: {tile_id}: layer {ly.name} has no triangles')
        pos = np.asarray(ly.pos, dtype='<f4')
        nrm = np.asarray(ly.nrm, dtype='<f4')
        n_idx = max(ly.idx)
        if n_idx >= len(pos):
            raise ValueError(f'tiles: {tile_id}: layer {ly.name} indexes past its vertices')
        idt = '<u2' if len(pos) < 65535 else '<u4'
        ct = 5123 if idt == '<u2' else 5125
        idx = np.asarray(ly.idx, dtype=idt)
        vp = add_view(pos.tobytes(), 34962)
        vn = add_view(nrm.tobytes(), 34962)
        vi = add_view(idx.tobytes(), 34963)
        ap = len(accessors)
        accessors.append({'bufferView': vp, 'componentType': 5126, 'count': len(pos), 'type': 'VEC3',
                          'min': [float(v) for v in pos.min(axis=0)],
                          'max': [float(v) for v in pos.max(axis=0)]})
        accessors.append({'bufferView': vn, 'componentType': 5126, 'count': len(nrm), 'type': 'VEC3'})
        accessors.append({'bufferView': vi, 'componentType': ct, 'count': len(idx), 'type': 'SCALAR'})
        attrs = {'POSITION': ap, 'NORMAL': ap + 1}
        if ly.col:
            col = np.asarray(ly.col, dtype='<f4')
            vc = add_view(col.tobytes(), 34962)
            accessors.append({'bufferView': vc, 'componentType': 5126, 'count': len(col), 'type': 'VEC3'})
            attrs['COLOR_0'] = len(accessors) - 1
        mats.append({'name': ly.name,
                     'pbrMetallicRoughness': {'baseColorFactor': [*ly.rgb, 1.0],
                                              'metallicFactor': 0.0, 'roughnessFactor': 1.0},
                     'doubleSided': True,
                     'extras': {'provenance': ly.provenance, 'source': ly.source, 'note': ly.note}})
        prims.append({'attributes': attrs, 'indices': ap + 2, 'material': len(mats) - 1, 'mode': 4,
                      'extras': {'layer': ly.name, 'provenance': ly.provenance}})
    js = {
        'asset': {'version': '2.0',
                  'generator': 'SmartCiti.X spatial/tiles.py (hand-written glTF 2.0 binary writer, no library)',
                  'extras': asset_extras},
        'scene': 0,
        'scenes': [{'name': tile_id, 'nodes': [0]}],
        'nodes': [{'name': tile_id, 'mesh': 0}],
        'meshes': [{'name': tile_id, 'primitives': prims}],
        'materials': mats,
        'accessors': accessors,
        'bufferViews': views,
        'buffers': [{'byteLength': len(blob)}],
    }
    jb = _pad4(json.dumps(js, separators=(',', ':'), sort_keys=False).encode('utf-8'), b' ')
    bb = bytes(blob)
    total = 12 + 8 + len(jb) + 8 + len(bb)
    out = (struct.pack('<4sII', b'glTF', 2, total)
           + struct.pack('<I4s', len(jb), b'JSON') + jb
           + struct.pack('<I4s', len(bb), b'BIN\x00') + bb)
    assert len(out) == total and len(out) % 4 == 0
    path.write_bytes(out)
    return out


# -------------------------------------------------------------- tile makers ---
SRC_OUTLINE = ('RECORDED outline: US Census Bureau 2017 cartographic boundary file '
               '(1:10,000,000, coarse) via us-atlas 3.0.1, converted to local metres by the registry')
STREETS_NOTE = ('AUTHORED procedural street polylines of the map fabric, NOT the real street grid; '
                'arterial and collector classes only, local streets are not exported')
WATER_NOTE = 'AUTHORED procedural water, NOT the real rivers, bayous or lakes'

# draw offsets so flat layers do not fight in the depth buffer; not heights
Y_GROUND, Y_WATER, Y_COLLECTOR, Y_ARTERIAL = 0.0, 1.5, 3.0, 4.5

COL_GROUND = [0.80, 0.82, 0.76]
COL_WATER = [0.30, 0.52, 0.75]
COL_COLLECTOR = [0.55, 0.55, 0.58]
COL_ARTERIAL = [0.32, 0.32, 0.36]
COL_HALL = [0.70, 0.66, 0.58]
COL_SITE = [0.85, 0.45, 0.15]


def region_tile(root, kind, fips, rec):
    """A parish or county tile. `rec` is the registry record of the region."""
    maps = 'parishes' if kind == 'parish' else 'bayarea'
    wf = json.load(open(root / f'{maps}/maps/world/{fips}.json'))
    sf = json.load(open(root / f'{maps}/maps/streets/{fips}.json'))
    where = f'{maps}/registry/{maps}.json#{fips}'
    outline = need(rec, 'outline_local_m', where)
    rings = []
    degenerate = 0
    for poly in outline:
        assert len(poly) == 1, f'tiles: {where}: a polygon with holes ({len(poly) - 1}) is not handled'
        ring = poly[0]
        distinct = {tuple(pt) for pt in ring}
        if len(distinct) < 3:
            # the registry's coarse outline holds a two-point sliver here: it
            # has no area, so there is nothing to fill; it is counted, not hidden
            degenerate += 1
            continue
        rings.append(ring)
    assert rings, f'tiles: {where}: no ring with area'
    layers = []
    ground = Layer('ground', 'DERIVED', SRC_OUTLINE, COL_GROUND,
                   'flat fill of the coarse outline at 0 m; no elevation is held (the ground is flat AUTHORED at 0 m)')
    area, splits = polygon_layer(ground, rings, Y_GROUND)
    layers.append(ground)

    water = Layer('water', 'AUTHORED', WATER_NOTE, COL_WATER,
                  'channels as ribbons of their authored width, ponds as filled polygons; drawn 1.5 m above the ground plane for depth only')
    n_ch = n_po = 0
    for ch in need(need(wf, 'water', f'{maps}/maps/world/{fips}.json'), 'channels', 'water'):
        n_ch += 1 if ribbon_layer(water, ch['centre'], ch['width_m'], Y_WATER) else 0
    for po in need(wf['water'], 'ponds', 'water'):
        pts = po['polygon']
        if pts[0] == pts[-1]:
            pts = pts[:-1]
        polygon_layer(water, [pts], Y_WATER)
        n_po += 1
    if water.idx:
        layers.append(water)

    cls = need(sf, 'classes', f'{maps}/maps/streets/{fips}.json')
    widths = need(sf, 'widths_m', f'{maps}/maps/streets/{fips}.json')
    n_street = {}
    for klass, y, col in (('collector', Y_COLLECTOR, COL_COLLECTOR), ('arterial', Y_ARTERIAL, COL_ARTERIAL)):
        ly = Layer(f'streets-{klass}', 'AUTHORED', STREETS_NOTE, col,
                   f'{klass} streets as ribbons of the registry width ({widths[klass]} m); drawn above the ground plane for depth only')
        c = 0
        for line in cls[klass]:
            c += 1 if ribbon_layer(ly, line, widths[klass], y) else 0
        n_street[klass] = c
        if ly.idx:
            layers.append(ly)
    omitted_local = len(cls['local'])

    frame = need(rec, 'frame', where)
    origin = need(frame, 'origin', where + '.frame')
    wm = need(frame, 'origin_in_world_m', where + '.frame')
    full = need(rec, 'full_name', where)
    counts = {'ground_area_km2_triangulated': round(area / 1e6, 3),
              'outline_rings_filled': len(rings), 'outline_degenerate_rings_skipped': degenerate,
              'outline_self_crossings_split': splits,
              'channels': n_ch, 'ponds': n_po,
              'streets_arterial': n_street['arterial'], 'streets_collector': n_street['collector'],
              'streets_local_not_exported': omitted_local}
    return {
        'id': f'{kind}-{fips}',
        'world': 'parishes' if kind == 'parish' else 'bayarea',
        'kind': kind,
        'name': full,
        'layers': layers,
        'frame_origin': {'lat': origin['lat'], 'lng': origin['lng'], 'provenance': 'DERIVED',
                         'source': f'{maps}/registry/{maps}.json#{fips}.frame.origin '
                                   '(area-weighted centroid of the coarse outline)'},
        'world_m': wm,
        'counts': counts,
    }


def wild_tile(world, hts):
    """A wilds terrain tile cut from wilds/core.mjs heights."""
    w = world
    wid = w['id']
    h = hts[wid]
    n, step, half = h['n'], h['step_m'], h['half_m']
    grid = np.asarray(h['grid'], dtype=np.float64).reshape(n, n)
    pal = {k: hex_rgb(v) for k, v in w['biome']['palette'].items()}
    wl, tl, sl = w['biome']['water_level_m'], w['biome']['tree_line_m'], w['biome']['snow_line_m']
    terrain = Layer('terrain', 'AUTHORED',
                    f'wilds/registry/wilds.json worlds[{wid}] seed {w["seed"]} via wilds/core.mjs wildsTerrain',
                    [1.0, 1.0, 1.0],
                    f'height grid {n}x{n} at {step:.1f} m spacing (coarse: site pads of about 40 m are not resolved); '
                    'AUTHORED terrain from a seed, NOT real elevation; vertex colours banded from the biome palette by height')
    pos, nrm, col = [], [], []
    for j in range(n):
        for i in range(n):
            x, z, y = -half + i * step, -half + j * step, grid[j, i]
            gx = (grid[j, min(i + 1, n - 1)] - grid[j, max(i - 1, 0)]) / (step * (min(i + 1, n - 1) - max(i - 1, 0)))
            gz = (grid[min(j + 1, n - 1), i] - grid[max(j - 1, 0), i]) / (step * (min(j + 1, n - 1) - max(j - 1, 0)))
            nv = np.array([-gx, 1.0, -gz])
            nv /= np.linalg.norm(nv)
            if y <= wl + 1.5:
                c = pal['shore']
            elif y >= sl:
                c = pal['snow']
            elif y >= tl:
                c = pal['rock']
            else:
                t = (y - wl) / max(tl - wl, 1.0)
                c = [pal['low'][k] * (1 - t) + pal['mid'][k] * t for k in range(3)]
            pos.append((x, y, z))
            nrm.append(tuple(nv))
            col.append(tuple(c))
    base = terrain.add_verts(pos, normal=nrm, colors=col)
    for j in range(n - 1):
        for i in range(n - 1):
            a = base + j * n + i
            b, c2, d = a + 1, a + n, a + n + 1
            terrain.add_up_tri(a, c2, b)
            terrain.add_up_tri(b, c2, d)
    layers = [terrain]
    sites = Layer('sites', 'AUTHORED', 'wilds/registry/wilds.json sites + trailhead (AUTHORED schematic places)',
                  COL_SITE, 'a 16 m square, 14 m tall marker at each site and the trailhead; schematic, not a building')
    markers = [(s['id'], s['x'], s['z'], s['h']) for s in h['sites']] + [
        ('trailhead', h['trailhead']['x'], h['trailhead']['z'], h['trailhead']['h'])]
    for _id, x, z, y in markers:
        box_layer(sites, [(x - 8, z - 8), (x + 8, z - 8), (x + 8, z + 8), (x - 8, z + 8)], y, y + 14)
    layers.append(sites)
    return {
        'id': f'wild-{wid}', 'world': 'wilds', 'kind': 'wild', 'name': w['name'],
        'layers': layers, 'frame_origin': None, 'world_m': None,
        'counts': {'grid': n, 'grid_step_m': round(step, 3), 'extent_m': w['extent_m'],
                   'sites_marked': len(h['sites']), 'trailhead_marked': 1,
                   'caches_not_exported': len(w['caches'])},
        'geolocation': w['geolocation'],
    }


def campus_tile(ck, camp):
    """A campus tile: the SCHEMATIC hall footprints of geo3d, extruded."""
    halls = need(camp, 'halls', f'geo3d/registry/geo3d.json#campuses.{ck}')
    ly = Layer('halls', 'SCHEMATIC',
               'geo3d/registry/geo3d.json halls[].corners_m + h (the AUTHORED campus site plan, campusplan/authored/rules.json)',
               COL_HALL, 'each hall as an extruded footprint; a 3D drawing of a functional programme, '
               'not a building anyone owns or built, not a survey')
    for hl in halls:
        c = [(x, z) for x, z in hl['corners_m']]
        box_layer(ly, c, 0.0, float(hl['h']))
    return {
        'id': f'campus-{ck}', 'world': 'campus', 'kind': 'campus', 'name': camp['name'],
        'layers': [ly], 'frame_origin': None, 'world_m': None,
        'counts': {'halls': len(halls)}, 'campus': ck,
    }


# ------------------------------------------------------------------- build ---
def build(root, out_dir, geopose_by_ref, h_prov):
    """Cut every tile, write the .glb files and the plain-JSON manifests,
    return the tiles registry document (the caller writes it)."""
    root = pathlib.Path(root)
    out_dir = pathlib.Path(out_dir)
    tiles_dir = out_dir / 'tiles'
    if tiles_dir.exists():
        for old in tiles_dir.glob('*.glb'):
            old.unlink()  # a build output: nothing stale survives a rebuild
    for old in out_dir.glob('*.json') if out_dir.exists() else []:
        old.unlink()
    tiles_dir.mkdir(parents=True, exist_ok=True)

    parishes = json.load(open(root / 'parishes/registry/parishes.json'))
    bay = json.load(open(root / 'bayarea/registry/bayarea.json'))
    wilds = json.load(open(root / 'wilds/registry/wilds.json'))
    geo3d = json.load(open(root / 'geo3d/registry/geo3d.json'))

    # wilds heights from the page's own terrain function
    proc = subprocess.run(['node', str(root / 'spatial/wilds_heights.mjs'), str(WILDS_GRID_N)],
                          capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f'tiles: wilds_heights.mjs failed ({proc.returncode}): {proc.stderr.strip()[:300]}')
    hts = json.loads(proc.stdout)

    specs = []   # (world key, tile dict)
    for fips, rec in sorted(need(parishes, 'parishes', 'parishes.json').items()):
        specs.append(region_tile(root, 'parish', fips, rec))
    for fips, rec in sorted(need(bay, 'counties', 'bayarea.json').items()):
        specs.append(region_tile(root, 'county', fips, rec))
    for w in wilds['worlds']:
        specs.append(wild_tile(w, hts))
    campuses_without = []
    for ck, camp in need(geo3d, 'campuses', 'geo3d.json').items():
        if camp['halls_count'] == 0:
            campuses_without.append({'campus': ck, 'name': camp['name'],
                                     'why': need(camp, 'note', f'geo3d.json#campuses.{ck}')})
            continue
        specs.append(campus_tile(ck, camp))

    tiles = []
    for t in specs:
        layers = t['layers']
        prov_layers = {ly.name: ly.provenance for ly in layers}
        t_prov = weakest(list(prov_layers.values()))
        fname = f'{t["id"]}.glb'
        ref = f'tiles/{fname}'
        if len(ref.encode()) > SREFERENCE_MAX_BYTES:
            raise ValueError(f'tiles: {ref} is longer than Sneeze\'s 128-byte sReference field')

        # anchor
        anchor = None
        no_anchor = None
        if t['kind'] in ('parish', 'county'):
            fo = t['frame_origin']
            anchor = {
                'geopose': {'position': {'lat': fo['lat'], 'lon': fo['lng'], 'h': 0.0},
                            'orientation': {'yaw': 0, 'pitch': 0, 'roll': 0}},
                'provenance': {
                    'position_horizontal': fo['provenance'],
                    'source': fo['source'],
                    'h_provenance': h_prov,
                    'orientation_provenance': 'DERIVED - the tile\'s local frame is east/north/up by construction, '
                                              'so the identity rotation is its true orientation relative to '
                                              'LTP-ENU; the sign convention of GeoPose yaw was not checked '
                                              'against the OGC text, and identity needs none',
                },
                'tile_origin_is': 'the glb origin (0, 0, 0)',
            }
        elif t['kind'] == 'campus':
            ref_pose = geopose_by_ref[f'campus:{t["campus"]}']
            anchor = {
                'geopose': json.loads(json.dumps(ref_pose['geopose'])),
                'provenance': {
                    'position_horizontal': ref_pose['provenance']['position_horizontal'],
                    'source': ref_pose['provenance']['source'] + ' (the existing campus pose in geopose.json, copied)',
                    'h_provenance': h_prov,
                    'orientation_provenance': 'SCHEMATIC - the campus drawing is north-up about its centroid '
                                              '(geo3d placement); no heading or site survey is recorded',
                },
                'tile_origin_is': 'the campus centroid (0, 0, 0)',
                'pose_ref': f'campus:{t["campus"]}',
            }
            assert anchor['geopose'] == ref_pose['geopose']
        else:
            geol = t['geolocation']
            assert geol['on_globe'] is False
            no_anchor = ('no GeoPose: this world is not on the globe - ' + geol['coordinates'] +
                         ' (wilds/registry/wilds.json geolocation). No latitude or longitude is invented.')

        extras = {'tile': t['id'], 'world': t['world'], 'provenance': t_prov,
                  'provenance_layers': prov_layers,
                  'axes': 'glTF Y-up; x = east, z = -north for georeferenced tiles (scene convention of geo3d); '
                          'wilds tiles use their own x/z metres (authored, no north)',
                  'honesty': 'flat map geometry from registries; AUTHORED where labelled; not a survey; '
                             'not loaded in any metaverse browser by this build'}
        data = write_glb(tiles_dir / fname, t['id'], layers, extras)
        bb = {'min': [round(min(p[k] for ly in layers for p in ly.pos), 2) for k in range(3)],
              'max': [round(max(p[k] for ly in layers for p in ly.pos), 2) for k in range(3)]}
        tiles.append({
            'id': t['id'], 'world': t['world'], 'kind': t['kind'], 'name': t['name'],
            'file': f'dist/sneeze/{ref}', 'reference': ref,
            'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(),
            'format': 'glTF 2.0 binary (.glb): magic glTF, version 2, one JSON chunk, one BIN chunk; '
                      'no extensions, no textures, no animation',
            'provenance': t_prov,
            'provenance_rule': 'the weakest word among the layers: a tile is never more recorded than its '
                               'least-recorded layer',
            'layers': [{'name': ly.name, 'provenance': ly.provenance, 'source': ly.source,
                        'note': ly.note, 'vertices': len(ly.pos), 'triangles': ly.triangles}
                       for ly in layers],
            'vertices': sum(len(ly.pos) for ly in layers),
            'triangles': sum(ly.triangles for ly in layers),
            'bbox_gltf_m': bb,
            'counts': t['counts'],
            'world_m': t['world_m'],
            'anchor': anchor,
            'no_anchor_because': no_anchor,
            'status': 'proposed - not loaded in Sneeze, Artemis or any other metaverse browser',
        })

    total = sum(x['bytes'] for x in tiles)
    if any(x['bytes'] > TILE_MAX_BYTES for x in tiles):
        raise ValueError('tiles: a tile exceeds TILE_MAX_BYTES: ' +
                         ', '.join(f'{x["id"]}={x["bytes"]}' for x in tiles if x['bytes'] > TILE_MAX_BYTES))
    if total > TOTAL_MAX_BYTES:
        raise ValueError(f'tiles: {total} bytes exceed TOTAL_MAX_BYTES {TOTAL_MAX_BYTES}')

    # ------------------------------------------------------------ manifests
    manifests = []
    by_id = {x['id']: x for x in tiles}

    def node_for(t, rel):
        nd = {'Head': {'Self': 'P-?'},
              'Name': f'{t["name"]} ({t["provenance"]}, weakest layer)',
              'Resource': {'sReference': t['reference']}}
        if rel is not None and any(abs(v) > 0 for v in rel):
            nd['Transform'] = {'Position': [round(v, 2) for v in rel]}
        return nd

    def manifest(mid, container, title, ids, rooted_by_world_m):
        ts = [by_id[i] for i in ids]
        root_t = ts[0]
        if rooted_by_world_m:
            r0 = root_t['world_m']
            scene = node_for(root_t, [r0[0], r0[1], 0.0])
            kids = []
            for t in ts[1:]:
                w = t['world_m']
                kids.append(node_for(t, [w[0] - r0[0], w[1] - r0[1], 0.0]))
            if kids:
                scene['aChildren'] = kids
        else:
            scene = node_for(root_t, None)
        doc = {
            'Container': container,
            'Services': [],
            'Modules': [{'sUrl': MAP_MODULE_URL}],
            'Data': {
                'Scene': scene,
                'Anchors': [{'Tile': t['id'], 'GeoPose': t['anchor']['geopose'],
                             'PositionProvenance': t['anchor']['provenance']['position_horizontal']}
                            for t in ts if t['anchor']],
                'Provenance': {t['id']: t['provenance'] for t in ts},
            },
        }
        text = json.dumps(doc, indent=3) + '\n'
        (out_dir / f'{mid}.json').write_text(text)
        manifests.append({
            'id': mid, 'file': f'dist/sneeze/{mid}.json', 'title': title, 'container': container,
            'tiles': ids, 'bytes': len(text.encode()),
            'sha256': hashlib.sha256(text.encode()).hexdigest(),
            'envelope': 'unsigned plain JSON (the form the Sneeze example docs call convenient but not the '
                        'preferred way to publish); not signed, no certificate held',
            'status': 'proposed - not loaded in Sneeze, Artemis or any other metaverse browser',
        })

    manifest('parishes', 'smartcitix-world-parishes', 'Louisiana parishes around New Orleans',
             [x['id'] for x in tiles if x['world'] == 'parishes'], True)
    manifest('bayarea', 'smartcitix-world-bayarea', 'San Francisco Bay Area counties',
             [x['id'] for x in tiles if x['world'] == 'bayarea'], True)
    for x in tiles:
        if x['world'] == 'wilds':
            manifest(f'wilds-{x["id"].split("-", 1)[1]}', f'smartcitix-world-{x["id"]}',
                     f'{x["name"]} (authored wilds world)', [x['id']], False)
        if x['world'] == 'campus':
            manifest(f'campus-{x["id"].split("-", 1)[1]}', f'smartcitix-world-{x["id"]}',
                     f'{x["name"]} (SCHEMATIC hall footprints)', [x['id']], False)

    doc = {
        'tiles': tiles,
        'manifests': manifests,
        'campuses_without_tile': campuses_without,
        'budget': {'tile_max_bytes': TILE_MAX_BYTES, 'total_max_bytes': TOTAL_MAX_BYTES,
                   'wilds_grid_n': WILDS_GRID_N, 'sreference_max_bytes': SREFERENCE_MAX_BYTES,
                   'total_bytes': total, 'largest_tile_bytes': max(x['bytes'] for x in tiles),
                   'manifest_bytes': sum(m['bytes'] for m in manifests)},
        'map_module_url': MAP_MODULE_URL,
        'verified': VERIFIED,
        'field_status': [{'field': f, 'status': s, 'verified_ids': v} for f, s, v in FIELD_STATUS],
    }
    return doc
