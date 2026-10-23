#!/usr/bin/env python3
"""
Pre-flight self-check for the Sneeze world tiles. Needs NO Sneeze, NO Artemis, NO network.

  python3 spatial/build.py                                   # build dist/sneeze/ first
  python3 spatial/sneeze_kit/preflight.py                    # serve dist/sneeze/ in-process and check it over HTTP
  python3 spatial/sneeze_kit/preflight.py --out preflight.json   # also write the report template.py embeds
  python3 spatial/sneeze_kit/preflight.py --url http://127.0.0.1:8765/   # check a server that is already running

It checks, over real HTTP requests (so the MIME types and headers a viewer would see are the ones
measured), against spatial/registry/tiles.json:
  * every manifest parses as JSON, is served as application/json, and its bytes equal the recorded sha256;
  * every manifest follows the documented SneezeDoc shape and uses no field outside the registry's
    documented/proposed table (the proposed ones in use are listed);
  * every Resource.sReference is relative, within the 128-byte limit, resolves against the manifest
    URL to a tile the registry lists for that manifest, and every listed tile is referenced exactly once;
  * every tile is served as model/gltf-binary, starts with the glTF magic, and its bytes equal the
    recorded sha256 and length; a Range request is answered correctly; CORS headers are present;
  * child positions equal the recorded offsets; the GeoPose anchors and provenance words in each
    manifest equal the registry; no file in the folder is unlisted.
It does NOT show that Sneeze or Artemis loads anything: that needs a person with one of them
(CHECKLIST.md). Exit code 0 only when every check passes. Output: "  ok <name>" / "FAIL <name>: <why>".
"""
import argparse
import http.client
import json
import math
import pathlib
import re
import sys
import threading
import urllib.parse

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import serve  # noqa: E402

SREF_MAX = 128
SELF_RE = re.compile(r'^[A-Z]-(\?|\d+)$')
SHASH_RE = re.compile(r'^sha256-[0-9a-f]{64}$')


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def check_shape(doc):
    """Return (violations, used_field_rows, sreferences, positions) for one manifest document.
    Violations name the rule. used_field_rows is the set of registry field-table rows the
    manifest actually uses (PATH_TO_FIELD)."""
    bad, used, refs, positions = [], set(), [], {}

    def v(msg):
        bad.append(msg)

    if not isinstance(doc, dict):
        return ['top-level is not an object'], used, refs, positions
    extra = set(doc) - C.TOP_KEYS
    for k in sorted(extra):
        v(f'unknown top-level field {k!r}')
    for k in sorted(C.TOP_KEYS - set(doc)):
        v(f'missing top-level field {k!r}')
    if isinstance(doc.get('Container'), str) and doc['Container'].strip():
        used.add(C.PATH_TO_FIELD['Container'])
    else:
        v('Container must be a non-empty string')
    if isinstance(doc.get('Services'), list):
        used.add(C.PATH_TO_FIELD['Services'])
        if doc['Services']:
            v('Services must be the empty list in these manifests (the docs disagree on its shape)')
    else:
        v('Services must be a list')
    mods = doc.get('Modules')
    if not isinstance(mods, list) or not mods:
        v('Modules must be a non-empty list')
    else:
        for i, m in enumerate(mods):
            if not isinstance(m, dict) or not isinstance(m.get('sUrl'), str) or not m['sUrl']:
                v(f'Modules[{i}] needs a string sUrl')
                continue
            used.add(C.PATH_TO_FIELD['Modules[].sUrl'])
            for k in sorted(set(m) - {'sUrl', 'sHash'}):
                v(f'unknown field Modules[{i}].{k}')
            if 'sHash' in m:
                used.add(C.PATH_TO_FIELD['Modules[].sHash'])
                if not isinstance(m['sHash'], str) or not SHASH_RE.match(m['sHash']):
                    v(f'Modules[{i}].sHash must be "sha256-<64 lowercase hex>"')
    data = doc.get('Data')
    if not isinstance(data, dict):
        v('Data must be an object')
        return bad, used, refs, positions
    for k in sorted(set(data) - C.DATA_KEYS):
        v(f'unknown field Data.{k}')
    if 'Scene' not in data:
        v('Data.Scene missing')
    else:
        used.add(C.PATH_TO_FIELD['Data.Scene'])
    if 'Anchors' in data:
        used.add(C.PATH_TO_FIELD['Data.Anchors'])
    if 'Provenance' in data:
        used.add(C.PATH_TO_FIELD['Data.Provenance'])

    def node(nd, path, depth):
        if depth > 8:
            v(f'{path}: nesting deeper than 8')
            return
        if not isinstance(nd, dict):
            v(f'{path}: not an object')
            return
        for k in sorted(set(nd) - C.NODE_KEYS):
            v(f'unknown field {path}.{k}')
        head = nd.get('Head')
        if not isinstance(head, dict) or set(head) != {'Self'} or not isinstance(head['Self'], str) or not SELF_RE.match(head['Self']):
            v(f'{path}.Head must be {{"Self": "<class letter>-<index or ?>"}}')
        else:
            used.add(C.PATH_TO_FIELD['node.Head.Self'])
        if isinstance(nd.get('Name'), str) and nd['Name']:
            used.add(C.PATH_TO_FIELD['node.Name'])
        else:
            v(f'{path}.Name must be a non-empty string')
        res = nd.get('Resource')
        if not isinstance(res, dict) or set(res) != {'sReference'} or not isinstance(res['sReference'], str):
            v(f'{path}.Resource must be {{"sReference": "<url>"}}')
        else:
            ref = res['sReference']
            used.add(C.PATH_TO_FIELD['node.Resource.sReference'])
            refs.append(ref)
            if len(ref.encode()) > SREF_MAX:
                v(f'{path}.Resource.sReference is {len(ref.encode())} bytes (limit {SREF_MAX})')
            if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', ref) or ref.startswith('/') or ref.startswith('//'):
                v(f'{path}.Resource.sReference must be relative to the manifest, got {ref!r}')
            elif any(seg in ('', '.', '..') for seg in ref.split('/')) or '\\' in ref or '?' in ref or '#' in ref:
                v(f'{path}.Resource.sReference must be a plain folder/file path (no ., .., empty segment, backslash, query or fragment), got {ref!r}')
        if 'Transform' in nd:
            tr = nd['Transform']
            if not isinstance(tr, dict) or set(tr) != {'Position'}:
                v(f'{path}.Transform may hold only Position (Rotation/Scale are not in the registry table)')
            else:
                pos = tr['Position']
                if not isinstance(pos, list) or len(pos) != 3 or not all(_num(x) for x in pos):
                    v(f'{path}.Transform.Position must be 3 finite numbers')
                else:
                    used.add(C.PATH_TO_FIELD['node.Transform.Position'])
                    if isinstance(res, dict) and isinstance(res.get('sReference'), str):
                        positions[res['sReference']] = pos
        if 'aChildren' in nd:
            ch = nd['aChildren']
            if not isinstance(ch, list) or not ch:
                v(f'{path}.aChildren must be a non-empty list when present')
            else:
                used.add(C.PATH_TO_FIELD['node.aChildren'])
                for i, c in enumerate(ch):
                    node(c, f'{path}.aChildren[{i}]', depth + 1)

    if 'Scene' in data:
        node(data['Scene'], 'Data.Scene', 0)
    return bad, used, refs, positions


class Http:
    def __init__(self, base):
        u = urllib.parse.urlsplit(base)
        self.base = base if base.endswith('/') else base + '/'
        self.host, self.port = u.hostname, u.port or (443 if u.scheme == 'https' else 80)
        self.https = u.scheme == 'https'

    def get(self, rel, headers=None, method='GET'):
        cls = http.client.HTTPSConnection if self.https else http.client.HTTPConnection
        c = cls(self.host, self.port, timeout=20)
        try:
            c.request(method, urllib.parse.urlsplit(self.base).path.rstrip('/') + '/' + rel.lstrip('/'), headers=headers or {})
            r = c.getresponse()
            return r.status, {k.lower(): v for k, v in r.getheaders()}, r.read()
        finally:
            c.close()


def run(dist=None, tiles_path=None, url=None, out=None, quiet=False):
    results = []

    def chk(name, cond, why=''):
        results.append((name, bool(cond), why))
        if not quiet:
            print(f'  ok {name}' if cond else f'FAIL {name}: {why}', flush=True)
        return bool(cond)

    srv = None
    try:
        tiles = C.load_tiles(tiles_path)
        chk('registry parses and lists tiles and manifests', bool(tiles['tiles']) and bool(tiles['manifests']))
    except Exception as e:  # noqa: BLE001
        chk('registry parses and lists tiles and manifests', False, str(e))
        return finish(results, {}, {}, None, out, quiet)
    table = C.field_table(tiles)
    for path, row in C.PATH_TO_FIELD.items():
        chk(f'registry field table has a row for {row}', row in table, f'{path} is used by the manifests but tiles.json#field_status has no such row')
    if url is None:
        root = pathlib.Path(dist) if dist else C.DEFAULT_DIST
        if not root.is_dir():
            chk('dist folder exists', False, f'{root} - build first: python3 spatial/build.py')
            return finish(results, {}, {}, tiles, out, quiet)
        srv = serve.make_server(root, '127.0.0.1', 0, None, None, True)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = srv.base_url()
        listed = {t['reference'] for t in tiles['tiles']} | {f'{m["id"]}.json' for m in tiles['manifests']}
        ondisk = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
        chk('the folder holds exactly the files the registry lists (no unlisted file, none missing)', ondisk == listed,
            f'unlisted: {sorted(ondisk - listed)[:5]}; missing: {sorted(listed - ondisk)[:5]}')
    else:
        base = url
    h = Http(base)
    by_tile = {t['id']: t for t in tiles['tiles']}
    ref_to_tile = {t['reference']: t for t in tiles['tiles']}
    man_sha, tile_sha = {}, {}
    seen_tiles = set()
    proposed_used = set()
    try:
        for m in tiles['manifests']:
            mid = m['id']
            try:
                st, hd, body = h.get(f'{mid}.json')
            except OSError as e:
                chk(f'{mid}.json is reachable', False, str(e))
                continue
            chk(f'{mid}.json answers 200', st == 200, f'status {st}')
            if st != 200:
                continue
            ct = hd.get('content-type', '').split(';')[0].strip().lower()
            chk(f'{mid}.json is served as application/json', ct == 'application/json', f'Content-Type {hd.get("content-type")!r}')
            chk(f'{mid}.json has a CORS allow-origin header', bool(hd.get('access-control-allow-origin')),
                'Access-Control-Allow-Origin missing')
            man_sha[mid] = C.sha256_bytes(body)
            chk(f'{mid}.json bytes equal the recorded sha256', man_sha[mid] == m['sha256'] and len(body) == m['bytes'],
                f'got {man_sha[mid][:12]}.. {len(body)} B, registry {m["sha256"][:12]}.. {m["bytes"]} B')
            try:
                doc = json.loads(body.decode('utf-8'))
            except (ValueError, UnicodeDecodeError) as e:
                chk(f'{mid}.json parses as JSON', False, str(e))
                continue
            chk(f'{mid}.json parses as JSON', True)
            bad, used, refs, positions = check_shape(doc)
            chk(f'{mid}.json follows the documented manifest shape', not bad, '; '.join(bad[:4]))
            missing_rows = sorted(r for r in used if r not in table)
            chk(f'{mid}.json uses only fields the registry table lists', not missing_rows, f'not in table: {missing_rows}')
            proposed_used |= {r for r in used if table.get(r) == 'proposed'}
            want = [by_tile[i]['reference'] for i in m['tiles']]
            chk(f'{mid}.json references exactly its {len(want)} tile(s), once each', sorted(refs) == sorted(want),
                f'refs {sorted(set(refs) ^ set(want))[:4]} dup {len(refs) - len(set(refs))}')
            murl = urllib.parse.urljoin(h.base + f'{mid}.json', '.')
            for ref in refs:
                full = urllib.parse.urljoin(murl, ref)
                rel = full[len(h.base):] if full.startswith(h.base) else None
                t = ref_to_tile.get(rel) if rel else None
                chk(f'{mid}: {ref} resolves inside the served folder to a registry tile', t is not None, f'resolved to {full}')
                if t is None or t['id'] in tile_sha:
                    continue
                seen_tiles.add(t['id'])
                st, hd, gb = h.get(rel)
                chk(f'{t["id"]} answers 200', st == 200, f'status {st}')
                if st != 200:
                    continue
                ct = hd.get('content-type', '').split(';')[0].strip().lower()
                chk(f'{t["id"]} is served as model/gltf-binary', ct == 'model/gltf-binary', f'Content-Type {hd.get("content-type")!r}')
                chk(f'{t["id"]} has a CORS allow-origin header', bool(hd.get('access-control-allow-origin')), 'Access-Control-Allow-Origin missing')
                chk(f'{t["id"]} starts with the glTF magic', gb[:4] == b'glTF', f'first bytes {gb[:4]!r}')
                tile_sha[t['id']] = C.sha256_bytes(gb)
                chk(f'{t["id"]} bytes equal the recorded sha256 and length', tile_sha[t['id']] == t['sha256'] and len(gb) == t['bytes'],
                    f'got {tile_sha[t["id"]][:12]}.. {len(gb)} B, registry {t["sha256"][:12]}.. {t["bytes"]} B')
                st, hd, part = h.get(rel, {'Range': 'bytes=0-3'})
                chk(f'{t["id"]} answers a Range request correctly', (st == 206 and part == b'glTF' and hd.get('content-range', '').startswith('bytes 0-3/'))
                    or (st == 200 and part == gb), f'status {st}, {len(part)} B')
            # positions: rooted manifests carry the recorded world offsets
            roots = [by_tile[i] for i in m['tiles']]
            if roots[0].get('world_m'):
                r0 = roots[0]['world_m']
                okp = True
                why = ''
                for t in roots:
                    w = t['world_m']
                    exp = [r0[0], r0[1], 0.0] if t is roots[0] else [w[0] - r0[0], w[1] - r0[1], 0.0]
                    got = positions.get(t['reference'])
                    if got is None:
                        okp = okp and all(abs(x) == 0 for x in exp)
                        if not okp:
                            why = f'{t["id"]}: no Position'
                    elif max(abs(a - b) for a, b in zip(got, exp)) > 0.006:
                        okp, why = False, f'{t["id"]}: Position {got} != recorded {exp}'
                chk(f'{mid}.json child positions equal the recorded offsets', okp, why)
            anchors = doc.get('Data', {}).get('Anchors', []) if isinstance(doc.get('Data'), dict) else []
            prov = doc.get('Data', {}).get('Provenance', {}) if isinstance(doc.get('Data'), dict) else {}
            exp_anchors = [{'Tile': i, 'GeoPose': by_tile[i]['anchor']['geopose'], 'PositionProvenance': by_tile[i]['anchor']['provenance']['position_horizontal']}
                           for i in m['tiles'] if by_tile[i]['anchor']]
            chk(f'{mid}.json GeoPose anchors equal the registry', anchors == exp_anchors, 'Data.Anchors differs from tiles.json')
            chk(f'{mid}.json provenance words equal the registry', prov == {i: by_tile[i]['provenance'] for i in m['tiles']}, 'Data.Provenance differs from tiles.json')
        chk('every registry tile was reached through a manifest', seen_tiles == set(by_tile), f'not reached: {sorted(set(by_tile) - seen_tiles)[:5]}')
    finally:
        if srv:
            srv.shutdown()
            srv.server_close()
    if not quiet and proposed_used:
        print('  note proposed (not documented by Sneeze) fields the manifests use: ' + '; '.join(sorted(proposed_used)), flush=True)
    return finish(results, man_sha, tile_sha, tiles, out, quiet)


def finish(results, man_sha, tile_sha, tiles, out, quiet):
    failed = [n for n, ok, _ in results if not ok]
    report = {
        'schema': 'smartcitix-sneeze-preflight/1',
        'passed': not failed,
        'checks': len(results),
        'failed': failed,
        'tiles_source_stamp': tiles['source_stamp'] if tiles else None,
        'manifest_sha256': man_sha,
        'tile_sha256': tile_sha,
        'scope': 'this reports what a plain HTTP client measured; it is not an observation in Sneeze or Artemis',
    }
    if out:
        pathlib.Path(out).write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    if not quiet:
        print(f'preflight: {len(results) - len(failed)} of {len(results)} checks passed' + ('' if not failed else f'; {len(failed)} FAILED'), flush=True)
        print('This shows the files are what the registry records and are served the way the docs expect. It does not show that Sneeze or Artemis loads them.', flush=True)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description='Pre-flight self-check (no Sneeze needed).')
    ap.add_argument('--dist', default=None, help='folder to serve and check (default dist/sneeze/)')
    ap.add_argument('--registry', default=None, help='tiles.json to check against (default spatial/registry/tiles.json)')
    ap.add_argument('--url', default=None, help='check an already-running server instead, e.g. http://127.0.0.1:8765/')
    ap.add_argument('--out', default=None, help='write the JSON report here (template.py embeds it)')
    a = ap.parse_args(argv)
    rep = run(a.dist, a.registry, a.url, a.out)
    sys.exit(0 if rep['passed'] else 1)


if __name__ == '__main__':
    main()
