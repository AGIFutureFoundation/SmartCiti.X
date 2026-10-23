#!/usr/bin/env python3
"""
Static server for dist/sneeze/ (the Sneeze world tiles; built by `python3 spatial/build.py`).

  python3 spatial/sneeze_kit/serve.py                    # http://127.0.0.1:8765/
  python3 spatial/sneeze_kit/serve.py --port 0           # any free port
  python3 spatial/sneeze_kit/serve.py --map-wasm FILE    # also serve YOUR copy of map.wasm (see CHECKLIST.md)

It serves ONLY files under dist/sneeze/ (plus, when asked, the one map.wasm file you name and
generated "<id>.local.json" variants of the manifests that point at it). Types: .glb
model/gltf-binary, .json application/json, .wasm application/wasm; any other extension is a 404.
CORS is open (the files are public build output), HTTP Range is supported (single ranges), and
nothing is cached, so a rebuild is seen at once. Every request is printed; with --log FILE it is
also written as JSON lines. On exit it lists the tiles that were fetched and the ones that were not.

Sneeze's documentation does not say whether it uses Range requests; they are supported as a
precaution and are harmless if unused. Stdlib only. Binds to 127.0.0.1 unless you pass --host.
"""
import argparse
import http.server
import json
import os
import pathlib
import re
import socketserver
import sys
import threading
import time
import urllib.parse

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _common as C  # noqa: E402

CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
    'Access-Control-Allow-Headers': 'Range, Content-Type',
    'Access-Control-Expose-Headers': 'Content-Length, Content-Range, Accept-Ranges, Content-Type',
    'Access-Control-Max-Age': '600',
}
LOCAL_SUFFIX = '.local.json'
WASM_PATH = 'wasm/map.wasm'


def resolve_request_path(root, raw_path):
    """Map a request target to a file under root, or None. Pure function (tested directly).
    Refuses: NUL, backslash, any '.'/'..'/empty/dot-leading segment (after one percent-decode),
    an extension not in the MIME table, a non-file, and anything whose real path (symlinks
    followed) is outside root."""
    p = raw_path.split('?', 1)[0].split('#', 1)[0]
    if not p.startswith('/'):
        return None
    try:
        dec = urllib.parse.unquote(p, errors='strict')
    except UnicodeDecodeError:
        return None
    if '\x00' in dec or '\\' in dec:
        return None
    segs = dec[1:].split('/')
    if not segs or any(s == '' or s.startswith('.') for s in segs):
        return None
    root_real = pathlib.Path(root).resolve()
    cand = root_real.joinpath(*segs)
    if cand.suffix.lower() not in C.MIME:
        return None
    try:
        real = cand.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if root_real != real and root_real not in real.parents:
        return None
    return real if real.is_file() else None


def parse_range(header, size):
    """('none', None) | ('range', (a, b)) inclusive | ('bad', None) -> 416.
    A multi-range or a malformed header is ignored as HTTP allows (served whole)."""
    if not header:
        return 'none', None
    m = re.fullmatch(r'\s*bytes\s*=\s*(\d*)\s*-\s*(\d*)\s*', header)
    if not m:
        return 'none', None
    a, b = m.group(1), m.group(2)
    if a == '' and b == '':
        return 'none', None
    if a == '':
        n = int(b)
        if n == 0:
            return 'bad', None
        return 'range', (max(0, size - n), size - 1)
    a = int(a)
    b = size - 1 if b == '' else min(int(b), size - 1)
    if a >= size or a > b:
        return 'bad', None
    return 'range', (a, b)


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr, handler, root, map_wasm, logfile, quiet):
        super().__init__(addr, handler)
        self.root = pathlib.Path(root).resolve()
        self.map_wasm = pathlib.Path(map_wasm).resolve() if map_wasm else None
        self.logfile = logfile
        self.quiet = quiet
        self.lock = threading.Lock()
        self.seen = {}          # request path -> list of status codes
        self.map_module_url = None
        try:
            self.map_module_url = C.load_tiles().get('map_module_url')
        except Exception:
            pass

    def base_url(self):
        h, p = self.server_address[:2]
        return f'http://{h}:{p}/'

    def manifest_ids(self):
        return sorted(f.stem for f in self.root.glob('*.json'))

    def local_variant(self, mid):
        src = self.root / f'{mid}.json'
        if not src.is_file() or not self.map_wasm:
            return None
        doc = json.loads(src.read_text(encoding='utf-8'))
        for m in doc.get('Modules', []):
            if isinstance(m, dict) and isinstance(m.get('sUrl'), str) and re.match(r'^https?://', m['sUrl']):
                m['sUrl'] = WASM_PATH
        return (json.dumps(doc, indent=3) + '\n').encode()

    def record(self, rec):
        with self.lock:
            self.seen.setdefault(rec['path'], []).append(rec['status'])
            if self.logfile:
                with open(self.logfile, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(rec, sort_keys=True) + '\n')
        if not self.quiet:
            rng = f" range={rec['range']}" if rec.get('range') else ''
            sys.stderr.write(f"{time.strftime('%H:%M:%S')} {rec['method']} {rec['path']} -> {rec['status']} {rec['bytes']}B{rng}\n")
            sys.stderr.flush()


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = 'sneeze-kit'
    sys_version = ''
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):  # replaced by Server.record
        pass

    def _send(self, status, headers, body=None, path=None, sent=None, rng=None):
        self.send_response(status)
        for k, v in {**CORS, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', **headers}.items():
            self.send_header(k, v)
        self.end_headers()
        n = 0
        if body is not None and self.command != 'HEAD':
            self.wfile.write(body)
            n = len(body)
        self.server.record({'t': round(time.time(), 3), 'method': self.command, 'path': (path or self.path).split('?', 1)[0],
                            'status': status, 'bytes': n if sent is None else sent, 'range': rng})

    def _plain(self, status, msg):
        b = (msg + '\n').encode()
        self._send(status, {'Content-Type': 'text/plain; charset=utf-8', 'Content-Length': str(len(b))}, b)

    def do_OPTIONS(self):
        self._send(204, {'Content-Length': '0', 'Allow': 'GET, HEAD, OPTIONS'})

    def do_HEAD(self):
        self._serve()

    def do_GET(self):
        self._serve()

    def do_POST(self):
        self._send(405, {'Allow': 'GET, HEAD, OPTIONS', 'Content-Length': '0'})

    do_PUT = do_DELETE = do_PATCH = do_POST

    def _serve(self):
        srv = self.server
        raw = self.path
        if len(raw) > 2048:
            return self._plain(414, 'request target too long')
        bare = raw.split('?', 1)[0].split('#', 1)[0]
        if bare == '/':
            return self._index()
        data, ctype, real = None, None, None
        dec = urllib.parse.unquote(bare)
        if srv.map_wasm and dec == '/' + WASM_PATH:
            real, ctype = srv.map_wasm, C.MIME['.wasm']
        elif srv.map_wasm and dec.endswith(LOCAL_SUFFIX) and '/' not in dec[1:]:
            data = srv.local_variant(dec[1:-len(LOCAL_SUFFIX)]) if re.fullmatch(r'[A-Za-z0-9_-]+', dec[1:-len(LOCAL_SUFFIX)]) else None
            ctype = C.MIME['.json']
        else:
            real = resolve_request_path(srv.root, raw)
            if real is not None:
                ctype = C.MIME[real.suffix.lower()]
        if data is None and real is None:
            return self._plain(404, 'not found')
        size = len(data) if data is not None else real.stat().st_size
        kind, rg = parse_range(self.headers.get('Range'), size)
        base = {'Content-Type': ctype, 'Accept-Ranges': 'bytes'}
        if kind == 'bad':
            return self._send(416, {**base, 'Content-Range': f'bytes */{size}', 'Content-Length': '0'}, rng=self.headers.get('Range'))
        a, b = (0, size - 1) if kind == 'none' else rg
        if data is None:
            with open(real, 'rb') as f:
                f.seek(a)
                body = f.read(b - a + 1) if size else b''
        else:
            body = data[a:b + 1]
        if kind == 'range':
            return self._send(206, {**base, 'Content-Range': f'bytes {a}-{b}/{size}', 'Content-Length': str(len(body))}, body,
                              sent=len(body) if self.command != 'HEAD' else 0, rng=self.headers.get('Range'))
        return self._send(200, {**base, 'Content-Length': str(len(body))}, body)

    def _index(self):
        srv = self.server
        rows = ''.join(f'<li><a href="/{m}.json">{m}.json</a></li>' for m in srv.manifest_ids())
        html = ('<!doctype html><meta charset="utf-8"><title>Sneeze tiles</title>'
                '<p>Manifests (open one in Sneeze or Artemis by its full address):</p><ul>' + rows + '</ul>').encode()
        self._send(200, {'Content-Type': 'text/html; charset=utf-8', 'Content-Length': str(len(html))}, html)


def make_server(dist=None, host='127.0.0.1', port=0, map_wasm=None, logfile=None, quiet=True):
    root = pathlib.Path(dist) if dist else C.DEFAULT_DIST
    if not root.is_dir():
        raise SystemExit(f'no such folder: {root} - build the tiles first: python3 spatial/build.py')
    return Server((host, port), Handler, root, map_wasm, logfile, quiet)


def fetched_report(srv, tiles):
    """(fetched_ids, never_fetched_ids) of tiles, from what was requested with a 200/206."""
    got = {p for p, st in srv.seen.items() if any(s in (200, 206) for s in st)}
    ids = [(t['id'], '/' + t['reference']) for t in tiles['tiles']]
    return [i for i, p in ids if p in got], [i for i, p in ids if p not in got]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--dist', default=None, help='folder to serve (default: dist/sneeze/ in this repo)')
    ap.add_argument('--host', default='127.0.0.1', help='bind address (default 127.0.0.1; 0.0.0.0 exposes the files to your network)')
    ap.add_argument('--port', type=int, default=8765, help='port (0 = any free port)')
    ap.add_argument('--map-wasm', default=None, help='path to your own copy of map.wasm; served at /wasm/map.wasm with <id>.local.json manifests pointing at it')
    ap.add_argument('--log', default=None, help='also append each request as a JSON line to this file')
    a = ap.parse_args(argv)
    srv = make_server(a.dist, a.host, a.port, a.map_wasm, a.log, quiet=False)
    if a.map_wasm and not pathlib.Path(a.map_wasm).is_file():
        raise SystemExit(f'--map-wasm: no such file: {a.map_wasm}')
    base = srv.base_url()
    print(f'serving {srv.root.name}/ (only that folder) at {base}', flush=True)
    if a.host not in ('127.0.0.1', 'localhost', '::1'):
        print(f'WARNING: bound to {a.host}: anyone who can reach this machine can read these public build files', flush=True)
    print('manifests (give one of these full addresses to Sneeze / Artemis):', flush=True)
    for mid in srv.manifest_ids():
        print(f'  {base}{mid}.json', flush=True)
    if srv.map_wasm:
        print(f'your map.wasm ({C.sha256_file(srv.map_wasm)}) is at {base}{WASM_PATH}; use the .local.json manifests with it:', flush=True)
        for mid in srv.manifest_ids():
            print(f'  {base}{mid}{LOCAL_SUFFIX}', flush=True)
    else:
        print('these manifests name the stock map.wasm on RP1\'s CDN; if Sneeze cannot reach it, restart with --map-wasm (see CHECKLIST.md)', flush=True)
    print('Ctrl-C to stop.', flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        try:
            tiles = C.load_tiles()
            got, miss = fetched_report(srv, tiles)
            print(f'\ntiles fetched by the viewer: {len(got)} of {len(tiles["tiles"])}', flush=True)
            if miss:
                print('never fetched: ' + ', '.join(miss), flush=True)
        except Exception:
            pass


if __name__ == '__main__':
    main()
