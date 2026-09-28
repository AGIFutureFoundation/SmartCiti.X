#!/usr/bin/env python3
"""Vendor the few open-licence SVG icons the design kit uses.

Upstream: the `lucide-static` npm package (ISC). Only the icons the kit
actually draws are taken, plus the package's own LICENSE text, into
web/vendor/icons/. The tarball is fetched once from registry.npmjs.org and
its sha512 is checked against the `dist.integrity` the registry publishes
for this exact pinned version BEFORE a single byte is extracted. Every
written file's sha256, the tarball URL and the integrity are recorded in
web/vendor/icons/manifest.json; `--check` re-verifies them offline.

  python3 media/fetch_icons.py          # fetch (network: registry.npmjs.org)
  python3 media/fetch_icons.py --check  # offline re-verification
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
OUT = ROOT / 'web' / 'vendor' / 'icons'
PACKAGE = 'lucide-static'
VERSION = '1.48.0'
# the icons web/design_kit.py draws - it refuses to use one not listed here
ICONS = sorted([
    'arrow-right', 'check', 'chevron-right', 'circle-alert', 'info', 'pause', 'play',
    'hard-hat', 'graduation-cap', 'map', 'globe', 'route', 'shield-check', 'users',
    'wrench', 'building-2', 'video', 'layers',
    # wave 3: the site nav's group, home and search marks (web/sitenav.py NAV_CSS)
    'search', 'gamepad-2', 'clipboard-check', 'house',
])


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
    wanted = {f'package/icons/{n}.svg': f'{n}.svg' for n in ICONS}
    wanted['package/LICENSE'] = 'LICENSE'
    OUT.mkdir(parents=True, exist_ok=True)
    files = {}
    names = set(tf.getnames())
    for src, dst in wanted.items():
        if src not in names:
            raise SystemExit(f'{PACKAGE}@{VERSION}: no {src} in the tarball')
        data = tf.extractfile(src).read()
        (OUT / dst).write_bytes(data)
        files[dst] = {'sha256': sha256(data), 'from': f'{tarball}#{src[len("package/"):]}'}
    man = {
        'package': PACKAGE, 'version': VERSION, 'license': 'ISC',
        'tarball': tarball, 'integrity': integrity,
        'integrity_verified': 'sha512 of the downloaded tarball matched the registry dist.integrity',
        'icons': ICONS, 'files': files,
    }
    (OUT / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
    print(f'wrote {len(files)} files from {PACKAGE}@{VERSION} (integrity verified)')


def check():
    man = json.loads((OUT / 'manifest.json').read_text())
    for name, rec in man['files'].items():
        if sha256((OUT / name).read_bytes()) != rec['sha256']:
            raise SystemExit(f'{name}: sha256 does not match the manifest')
    on_disk = sorted(p.name for p in OUT.iterdir() if p.name != 'manifest.json')
    if on_disk != sorted(man['files']):
        raise SystemExit(f'web/vendor/icons holds files the manifest does not: {on_disk}')
    print(f'ok {len(man["files"])} icon files match manifest ({man["package"]}@{man["version"]})')


if __name__ == '__main__':
    check() if '--check' in sys.argv else fetch()
