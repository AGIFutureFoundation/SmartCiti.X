#!/usr/bin/env python3
"""Snapshot the published @reactor-models catalogue from registry.npmjs.org into reactor/catalogue_npm.json.

For every package in the npm scope: name, latest version, licence, dist.integrity and tarball - and, from the
tarball (sha512-checked against that integrity before it is opened), the MODEL_NAME constant and the
sendCommand() wire names its dist sends. Nothing is typed by hand. reactor/build.py reads the snapshot offline.

  python3 reactor/fetch_catalogue.py      # network: registry.npmjs.org only
"""
import base64
import datetime
import hashlib
import io
import json
import pathlib
import re
import sys
import tarfile
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'reactor' / 'catalogue_npm.json'
SCOPE = '@reactor-models'
SEARCHED_FOR = ['minimax']


def get(url):
    last = None
    for _ in range(4):
        try:
            return urllib.request.urlopen(url, timeout=60).read()
        except Exception as e:  # npm search answers 503 under load; retry, then fail loudly
            last = e
            time.sleep(3)
    raise SystemExit(f'fetch_catalogue: {url}: {last}')


def main():
    # one page is enough: the text search ranks the scope's own packages first; the scope filter drops the rest
    d = json.loads(get('https://registry.npmjs.org/-/v1/search?text=%40reactor-models&size=100'))
    found = [o['package']['name'] for o in d['objects'] if o['package']['name'].startswith(SCOPE + '/')]
    found = sorted(set(found))
    if not found:
        sys.exit('fetch_catalogue: npm search returned no @reactor-models packages')
    pkgs = []
    for name in found:
        meta = json.loads(get('https://registry.npmjs.org/' + name.replace('/', '%2f') + '/latest'))
        integ = meta['dist']['integrity']
        blob = get(meta['dist']['tarball'])
        if 'sha512-' + base64.b64encode(hashlib.sha512(blob).digest()).decode() != integ:
            sys.exit(f'fetch_catalogue: {name}: tarball sha512 does not match dist.integrity')
        tf = tarfile.open(fileobj=io.BytesIO(blob), mode='r:gz')
        src = ''
        for m in tf.getmembers():
            if m.isfile() and re.search(r'package/dist/.*\.(mjs|js)$', m.name) and not m.name.endswith('.map'):
                src += tf.extractfile(m).read().decode('utf-8', 'replace')
        mn = set(re.findall(r'MODEL_NAME\s*=\s*"([^"]+)"', src))
        for block in re.findall(r'MODEL_NAMES\s*=\s*\{([^}]*)\}', src):   # a package with several modes
            mn |= set(re.findall(r':\s*"([a-z0-9-]+/[a-z0-9._-]+)"', block))
        mn = sorted(mn)
        if not mn or not all(re.fullmatch(r'[a-z0-9-]+/[a-z0-9._-]+', m) for m in mn):
            sys.exit(f'fetch_catalogue: {name}: no <owner>/<model> name found ({mn})')
        cmds = sorted(set(re.findall(r'sendCommand\(\s*"([a-z0-9_]+)"', src)))
        pkgs.append({'npm_package': name, 'npm_version': meta['version'], 'npm_license': meta.get('license'),
                     'npm_integrity': integ, 'tarball': meta['dist']['tarball'], 'description': meta.get('description', ''),
                     'model_names': mn, 'wire_commands': cmds})
    doc = {'scope': SCOPE, 'fetched': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d'),
           'source': 'registry.npmjs.org search scope:reactor-models + each package /latest; tarballs sha512-verified',
           'searched_for': {s: [p['npm_package'] for p in pkgs if s in (p['npm_package'] + ' '.join(p['model_names']) + p['description']).lower()] for s in SEARCHED_FOR},
           'packages': pkgs}
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    print(f'fetch_catalogue: {len(pkgs)} packages -> {OUT.relative_to(ROOT)}; searched_for {doc["searched_for"]}')


if __name__ == '__main__':
    main()
