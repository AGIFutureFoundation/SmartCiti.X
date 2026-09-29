"""parishes/build_atlas.py - one 2048 px ground ATLAS per parish (PARISH v1.3 ground tiles) and per Bay county.

WORLDS (wave 11). The parish and Bay pages drape a region's 4x4 label-free ground tiles as ONE GROUND_PX = 2048
canvas: each 1024 px tile is drawn at 512 px into its (row, col) cell. This script does that composition once at
build time, so a page fetches 1 image per region instead of 16 (the published site holds at most 511 files).

- Input: the tiles the registries name (parishes/registry/parishes.json, bayarea/registry/bayarea.json), each checked
  against its recorded sha256 first (a stale tile stops the build by name). The tiles stay in the repo: economy/build.py
  reads their 1024 px pixels, and parishes/test.mjs / bayarea/test.mjs keep checking them.
- Composition: tile -> Image.reduce(2) (the 2x2 box mean; a bilinear draw at exactly half size samples the same four
  texels) -> pasted at (col * 512, row * 512). The composed canvas is saved LOSSLESS WebP, so the atlas holds the
  composed pixels exactly (checked below by decoding the file again).
- Output: <pack>/maps/atlas/<id>.webp and parishes/registry/ground_atlas.json {pack, version, source_stamp,
  rule, atlases{<tile stem>: {path, px, bytes, sha256, tiles_sha256[16], grid}}}, keyed by the tiles' path stem
  (e.g. "parishes/maps/tiles/22071"), which web/build_parishes.py (and the Bay page it hooks) look up fail-closed.
  Provenance is unchanged: the same DERIVED outline + AUTHORED fabric pixels, no text (the tiles' own label applies).

Usage: python3 parishes/build_atlas.py [--check]   (--check: rebuild in memory and compare bytes, write nothing)
"""
import hashlib
import io
import json
import pathlib
import sys

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'parishes/registry/ground_atlas.json'
ATLAS_PX = 2048
SOURCES = [('parishes', 'parishes/registry/parishes.json', 'parishes'), ('bayarea', 'bayarea/registry/bayarea.json', 'counties')]


class AtlasError(Exception):
    pass


def need(d, k, where):
    if not isinstance(d, dict) or k not in d:
        raise AtlasError(f'build_atlas: {where} has no {k!r}')
    return d[k]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def compose(tiles, grid, where):
    cell = ATLAS_PX // grid
    canvas = Image.new('RGB', (ATLAS_PX, ATLAS_PX))
    shas = []
    for t in sorted(tiles, key=lambda t: (need(t, 'row', where), need(t, 'col', where))):
        raw = (ROOT / need(t, 'path', where)).read_bytes()
        if sha(raw) != need(t, 'sha256', where):
            raise AtlasError(f'build_atlas: {t["path"]} does not match its recorded sha256 (rebuild the tiles first)')
        im = Image.open(io.BytesIO(raw)).convert('RGB')
        if im.size[0] != cell * 2 or im.size[1] != cell * 2:
            raise AtlasError(f'build_atlas: {t["path"]} is {im.size}, expected {cell * 2}^2 for a {grid}x{grid} atlas')
        canvas.paste(im.reduce(2), (t['col'] * cell, t['row'] * cell))
        shas.append(t['sha256'])
    return canvas, shas


def build():
    atlases, files = {}, {}
    for pack, reg_path, key in SOURCES:
        reg = json.loads((ROOT / reg_path).read_text())
        for rid, r in need(reg, key, reg_path).items():
            where = f'{reg_path}#{rid}.map.ground_tiles'
            gt = need(need(r, 'map', reg_path + '#' + rid), 'ground_tiles', where)
            tiles, grid = need(gt, 'tiles', where), need(gt, 'grid', where)
            if len(tiles) != grid * grid:
                raise AtlasError(f'build_atlas: {where} holds {len(tiles)} tiles, not {grid * grid}')
            stem = tiles[0]['path'].rsplit('-r', 1)[0]
            if any(t['path'].rsplit('-r', 1)[0] != stem for t in tiles):
                raise AtlasError(f'build_atlas: {where} tiles do not share one path stem')
            canvas, shas = compose(tiles, grid, where)
            buf = io.BytesIO()
            canvas.save(buf, 'WEBP', lossless=True, quality=100, method=4)
            data = buf.getvalue()
            if list(Image.open(io.BytesIO(data)).convert('RGB').getdata()) != list(canvas.getdata()):
                raise AtlasError(f'build_atlas: {stem} atlas does not decode to the composed pixels')
            path = f'{pack}/maps/atlas/{stem.rsplit("/", 1)[1]}.webp'
            files[path] = data
            atlases[stem] = {'path': path, 'px': ATLAS_PX, 'grid': grid, 'bytes': len(data), 'sha256': sha(data),
                             'tiles_sha256': shas}
    stamp = sha((json.dumps(atlases, sort_keys=True) + pathlib.Path(__file__).read_text()).encode())
    reg = {'pack': 'parishes', 'what': 'ground atlas', 'version': '1', 'source_stamp': stamp[:16], 'source_stamp_sha256': stamp,
           'rule': 'atlas = the grid x grid ground tiles, each reduced 2x by the 2x2 box mean and pasted at (col, row) x '
                   f'{ATLAS_PX} / grid px; lossless WebP; the same composition the pages drew at run time (GROUND_PX {ATLAS_PX})',
           'provenance': 'DERIVED from the recorded ground tiles (their own label and provenance apply: no text)',
           'atlases': atlases}
    return reg, files


def main():
    reg, files = build()
    text = json.dumps(reg, indent=1, sort_keys=True) + '\n'
    if '--check' in sys.argv:
        stale = [p for p, b in files.items() if not (ROOT / p).is_file() or (ROOT / p).read_bytes() != b]
        if stale or not OUT.is_file() or OUT.read_text() != text:
            raise SystemExit('build_atlas --check: stale ' + (', '.join(stale[:4]) or str(OUT.relative_to(ROOT))))
        print(f'build_atlas --check: {len(files)} atlases current')
        return
    for p, b in files.items():
        (ROOT / p).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / p).write_bytes(b)
    OUT.write_text(text)
    print(f'build_atlas: {len(files)} atlases, {sum(len(b) for b in files.values()):,} bytes, largest {max(len(b) for b in files.values()):,} B, stamp {reg["source_stamp"]}')


if __name__ == '__main__':
    try:
        main()
    except AtlasError as e:
        raise SystemExit(str(e))
