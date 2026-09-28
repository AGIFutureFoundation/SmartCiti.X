#!/usr/bin/env python3
"""Vendor the one us-atlas file the parishes pack reads.

Upstream: the `us-atlas` npm package 3.0.1 (ISC, Michael Bostock), which
packages the U.S. Census Bureau's 2017 cartographic boundary files (public
domain) as TopoJSON. Only `counties-10m.json` (every U.S. county and parish
at 1:10,000,000, clipped to the shoreline) and the package's own LICENSE are
taken, into parishes/vendor/us-atlas/. The tarball is fetched once from
registry.npmjs.org and its sha512 is checked against the `dist.integrity`
the registry publishes for this exact pinned version BEFORE a single byte is
extracted (the pattern of media/fetch_icons.py). Every written file's
sha256, the tarball URL and the integrity are recorded in
parishes/vendor/us-atlas/manifest.json; `--check` re-verifies them offline.

  python3 parishes/fetch_usatlas.py          # fetch (network: registry.npmjs.org)
  python3 parishes/fetch_usatlas.py --check  # offline re-verification
"""
import base64
import hashlib
import io
import json
import pathlib
import sys
import tarfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'parishes' / 'vendor' / 'us-atlas'
PACKAGE = 'us-atlas'
VERSION = '3.0.1'
FILES = {'package/counties-10m.json': 'counties-10m.json', 'package/LICENSE': 'LICENSE'}


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def fetch():
    meta_url = f'https://registry.npmjs.org/{PACKAGE}/{VERSION}'
    meta = json.loads(urllib.request.urlopen(meta_url, timeout=60).read())
    if meta['version'] != VERSION or meta['license'] != 'ISC':
        raise SystemExit(f'{PACKAGE}: registry says {meta["version"]} {meta["license"]}')
    integrity = meta['dist']['integrity']
    tarball = meta['dist']['tarball']
    blob = urllib.request.urlopen(tarball, timeout=120).read()
    algo, want = integrity.split('-', 1)
    if algo != 'sha512':
        raise SystemExit(f'{PACKAGE}: integrity is {algo}, not sha512')
    got = base64.b64encode(hashlib.sha512(blob).digest()).decode()
    if got != want:
        raise SystemExit(f'{PACKAGE}: tarball sha512 does not match the registry integrity')
    tf = tarfile.open(fileobj=io.BytesIO(blob), mode='r:gz')
    names = set(tf.getnames())
    OUT.mkdir(parents=True, exist_ok=True)
    files = {}
    for src, dst in FILES.items():
        if src not in names:
            raise SystemExit(f'{PACKAGE}@{VERSION}: no {src} in the tarball')
        data = tf.extractfile(src).read()
        (OUT / dst).write_bytes(data)
        files[dst] = {'sha256': sha256(data), 'bytes': len(data),
                      'from': f'{tarball}#{src[len("package/"):]}'}
    man = {
        'package': PACKAGE, 'version': VERSION, 'license': 'ISC',
        'copyright': 'Copyright 2013-2019 Michael Bostock',
        'data_origin': 'U.S. Census Bureau cartographic boundary files, 2017, 1:10,000,000 '
                       '(public domain, work of the U.S. federal government), as packaged by us-atlas',
        'tarball': tarball, 'integrity': integrity,
        'tarball_sha512_b64': got,
        'integrity_verified': 'sha512 of the downloaded tarball matched the registry dist.integrity',
        'purl': f'pkg:npm/{PACKAGE}@{VERSION}',
        'files': files,
    }
    (OUT / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
    print(f'wrote {len(files)} files from {PACKAGE}@{VERSION} (integrity verified: {integrity[:24]}...)')


def check():
    man = json.loads((OUT / 'manifest.json').read_text())
    for name, rec in man['files'].items():
        if sha256((OUT / name).read_bytes()) != rec['sha256']:
            raise SystemExit(f'{name}: sha256 does not match the manifest')
    on_disk = sorted(p.name for p in OUT.iterdir() if p.name != 'manifest.json')
    if on_disk != sorted(man['files']):
        raise SystemExit(f'parishes/vendor/us-atlas holds files the manifest does not: {on_disk}')
    print(f'ok {len(man["files"])} us-atlas files match manifest ({man["package"]}@{man["version"]})')


if __name__ == '__main__':
    check() if '--check' in sys.argv else fetch()
