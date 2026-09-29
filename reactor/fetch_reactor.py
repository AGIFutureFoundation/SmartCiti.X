#!/usr/bin/env python3
"""Vendor the Reactor browser SDK (@reactor-team/js-sdk, Apache-2.0) into web/vendor/reactor/.

Only what the imperative `Reactor` class needs in a browser is taken: dist/index.js (the ES
module), dist/wasm/reactor_wasm.js and dist/wasm/reactor_wasm_bg.wasm (the WebRTC/session
client it loads relative to itself). The tarball is fetched from registry.npmjs.org and its
sha512 is checked against the integrity PINNED in reactor/build.py (and written to
reactor/registry/reactor.json) BEFORE a byte is extracted. The package ships no LICENSE file,
so the Apache-2.0 text is taken from the upstream repository and its sha256 recorded.

The SDK's bare imports (react, react/jsx-runtime, awaitqueue, hls.js, mp4box) are resolved by
an import map to small AUTHORED shims in web/vendor/reactor/shims/ (the React API, recordings
and clip playback are not used; awaitqueue is a serial FIFO queue). They are ours, not upstream.

Every file's sha512 goes into web/vendor/reactor/manifest.json; `--check` re-verifies offline
that each vendored file matches the manifest AND that the manifest's integrity equals the
registry pin.

  python3 reactor/fetch_reactor.py          # fetch (network: registry.npmjs.org, raw.githubusercontent.com)
  python3 reactor/fetch_reactor.py --check  # offline re-verification
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
OUT = ROOT / 'web' / 'vendor' / 'reactor'
REG = ROOT / 'reactor' / 'registry' / 'reactor.json'
LICENSE_URL = 'https://raw.githubusercontent.com/reactor-team/reactor-client-sdks/main/LICENSE'
WANTED = {
    'package/dist/index.js': 'index.js',
    'package/dist/wasm/reactor_wasm.js': 'wasm/reactor_wasm.js',
    'package/dist/wasm/reactor_wasm_bg.wasm': 'wasm/reactor_wasm_bg.wasm',
}
SHIMS = ['shims/react.js', 'shims/react-jsx-runtime.js', 'shims/awaitqueue.js', 'shims/unavailable.js']


class VendorError(Exception):
    pass


def b64sha512(b):
    return 'sha512-' + base64.b64encode(hashlib.sha512(b).digest()).decode()


def pin():
    sdk = json.loads(REG.read_text())['sdk']
    for k in ('package', 'version', 'license', 'integrity'):
        if k not in sdk:
            raise VendorError(f'reactor registry: sdk.{k} missing')
    return sdk


def fetch():
    sdk = pin()
    meta = json.loads(urllib.request.urlopen(f'https://registry.npmjs.org/{sdk["package"]}/{sdk["version"]}', timeout=60).read())
    if meta['version'] != sdk['version'] or meta['license'] != sdk['license']:
        raise VendorError(f'registry says {meta["version"]} {meta["license"]}')
    if meta['dist']['integrity'] != sdk['integrity']:
        raise VendorError('npm dist.integrity differs from the pin in reactor/build.py')
    tarball = meta['dist']['tarball']
    blob = urllib.request.urlopen(tarball, timeout=120).read()
    if b64sha512(blob) != sdk['integrity']:
        raise VendorError('tarball sha512 does not match the pinned integrity')
    tf = tarfile.open(fileobj=io.BytesIO(blob), mode='r:gz')
    names = set(tf.getnames())
    files = {}
    for src, dst in WANTED.items():
        if src not in names:
            raise VendorError(f'no {src} in the tarball')
        data = tf.extractfile(src).read()
        (OUT / dst).parent.mkdir(parents=True, exist_ok=True)
        (OUT / dst).write_bytes(data)
        files[dst] = {'sha512': b64sha512(data), 'from': f'{tarball}#{src[len("package/"):]}', 'provenance': 'UPSTREAM'}
    lic = urllib.request.urlopen(LICENSE_URL, timeout=60).read()
    if b'Apache License' not in lic or b'Version 2.0' not in lic:
        raise VendorError('upstream LICENSE is not the Apache-2.0 text')
    (OUT / 'LICENSE').write_bytes(lic)
    files['LICENSE'] = {'sha512': b64sha512(lic), 'from': LICENSE_URL + ' (main branch; the npm tarball ships none)', 'provenance': 'UPSTREAM'}
    for s in SHIMS:
        files[s] = {'sha512': b64sha512((OUT / s).read_bytes()), 'from': 'written in this repo', 'provenance': 'AUTHORED'}
    man = {'package': sdk['package'], 'version': sdk['version'], 'license': sdk['license'],
           'tarball': tarball, 'integrity': sdk['integrity'],
           'integrity_verified': 'sha512 of the downloaded tarball matched the pin in reactor/registry/reactor.json',
           'files': files}
    (OUT / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
    print(f'wrote {len(files)} files for {sdk["package"]}@{sdk["version"]} (integrity verified)')


def check():
    sdk = pin()
    man = json.loads((OUT / 'manifest.json').read_text())
    if man['integrity'] != sdk['integrity'] or man['version'] != sdk['version']:
        raise VendorError('manifest integrity/version differ from reactor/registry/reactor.json')
    for name, rec in man['files'].items():
        if b64sha512((OUT / name).read_bytes()) != rec['sha512']:
            raise VendorError(f'{name}: sha512 does not match the manifest')
    on_disk = sorted(str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file() and p.name != 'manifest.json')
    if on_disk != sorted(man['files']):
        raise VendorError(f'web/vendor/reactor holds files the manifest does not list: {on_disk}')
    print(f'ok {len(man["files"])} reactor vendor files match manifest ({man["package"]}@{man["version"]}, integrity pinned)')


if __name__ == '__main__':
    try:
        check() if '--check' in sys.argv else fetch()
    except VendorError as e:
        sys.exit(f'fetch_reactor: {e}')
