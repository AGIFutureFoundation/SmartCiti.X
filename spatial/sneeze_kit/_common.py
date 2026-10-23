"""
Shared helpers for the Sneeze test kit (spatial/sneeze_kit/). Standard library only.

WHAT THE KIT IS. Nothing in this repository has been loaded in Sneeze or Artemis.
The kit lets a person who has one of them verify the world tiles in minutes
(serve.py + CHECKLIST.md), run a no-Sneeze self-check first (preflight.py), and
report back in a form the repo can ingest (template.py -> ingest.py ->
spatial/registry/sneeze_runs.json). The kit makes no claim about Sneeze itself:
every statement about Sneeze comes from tiles.json#verified (primary sources).
"""
import hashlib
import json
import pathlib
import re
import sys

sys.dont_write_bytecode = True

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DEFAULT_DIST = ROOT / 'dist' / 'sneeze'
DEFAULT_TILES = ROOT / 'spatial' / 'registry' / 'tiles.json'
DEFAULT_RUNS = ROOT / 'spatial' / 'registry' / 'sneeze_runs.json'
SCHEMA_FILE = HERE / 'results.schema.json'

# Only these extensions are ever served, with these types. Anything else is a 404.
MIME = {
    '.glb': 'model/gltf-binary',
    '.json': 'application/json',
    '.wasm': 'application/wasm',
}

PROPOSED_STATUS = 'proposed'
MANIFEST_UNTESTED = 'proposed - not loaded in Sneeze, Artemis or any other metaverse browser'

# Words that are not a version / a person. Compared lower-case after strip.
PLACEHOLDERS = {'', 'unknown', 'n/a', 'na', 'none', 'null', 'latest', 'main', 'master', 'head',
                '?', '??', 'tbd', 'todo', 'x', '-', 'anonymous', 'anon', 'me', 'test', 'nobody',
                'your name', 'name', 'person'}


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_json(p):
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_tiles(path=None):
    return load_json(path or DEFAULT_TILES)


def is_placeholder(s):
    t = str(s).strip().lower()
    return t in PLACEHOLDERS or t.startswith('fill in') or '<' in t or '>' in t


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


# ------------------------------------------------------------- field table ---
# Which tiles.json#field_status row each manifest / node field belongs to.
# preflight.py fails on any key that is not on this list, or whose row is
# missing from the registry's own table: "no field outside the table".
PATH_TO_FIELD = {
    'Container': 'manifest.Container',
    'Services': 'manifest.Services',
    'Modules[].sUrl': 'manifest.Modules[].sUrl',
    'Modules[].sHash': 'manifest.Modules[].sHash',
    'Data.Scene': 'manifest.Data.Scene',
    'Data.Anchors': 'manifest.Data.Anchors (GeoPose sidecar)',
    'Data.Provenance': 'manifest.Data.Provenance (sidecar)',
    'node.Head.Self': 'node.Head.Self',
    'node.Name': 'node.Name',
    'node.Resource.sReference': 'node.Resource.sReference',
    'node.Transform.Position': 'node.Transform.Position',
    'node.aChildren': 'node.aChildren',
}

NODE_KEYS = {'Head', 'Name', 'Resource', 'Transform', 'aChildren'}
TOP_KEYS = {'Container', 'Services', 'Modules', 'Data'}
DATA_KEYS = {'Scene', 'Anchors', 'Provenance'}


def field_table(tiles):
    """name -> status ('documented' | 'proposed') from the registry's own table."""
    return {r['field']: r['status'] for r in tiles['field_status']}


def kilometres(tile):
    """(east, up, north) extents in km, read from the tile's recorded glTF bounding box
    (glTF frame: x = east, y = up, z = -north)."""
    b = tile['bbox_gltf_m']
    mn, mx = b['min'], b['max']
    return ((mx[0] - mn[0]) / 1000.0, (mx[1] - mn[1]) / 1000.0, (mx[2] - mn[2]) / 1000.0)


def manifest_tile_ids(tiles, mid):
    for m in tiles['manifests']:
        if m['id'] == mid:
            return m['tiles']
    raise KeyError(mid)


def hex64(s):
    return isinstance(s, str) and re.fullmatch(r'[0-9a-f]{64}', s) is not None
