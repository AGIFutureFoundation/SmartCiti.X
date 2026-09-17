#!/usr/bin/env python3
"""Build the software bill of materials — security/registry/sbom.cdx.json.

CycloneDX 1.5 JSON, one component per vendored third-party file, each with a
SHA-256 of the bytes as they are in the tree right now, a purl, an SPDX licence
id, and the EVIDENCE the licence and version claims rest on: the banner and
version string actually found in the file. Nothing is fetched (no network at
build) and no licence text is invented — where a file carries no banner the
SBOM says so and names what the attribution rests on instead.

Everything outside `web/vendor/` is first-party with zero runtime dependencies
(`orbis/runner-*/` carry their own LICENSE files and are first-party too), so
the component list IS the vendor tree: `security/test_sbom.mjs` walks the tree
and fails if the two ever differ.

The human-readable statement of the same facts is THIRD_PARTY.md; the test
holds the two to each other rather than letting either drift.
"""
import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
VENDOR = ROOT / 'web' / 'vendor'
MANIFEST = json.loads((ROOT / 'pack' / 'manifest.json').read_text())

# What we know about each upstream, stated once. The version is not written
# here — it is READ from the file and checked against the purl below.
UPSTREAMS = {
    'three': {
        'purl': 'pkg:npm/three',
        'license': 'MIT',
        'license_url': 'https://github.com/mrdoob/three.js/blob/r160/LICENSE',
        'vcs': 'https://github.com/mrdoob/three.js',
        'website': 'https://threejs.org/',
    },
    'maplibre-gl': {
        'purl': 'pkg:npm/maplibre-gl',
        'license': 'BSD-3-Clause',
        'license_url': 'https://github.com/maplibre/maplibre-gl-js/blob/v4.7.1/LICENSE.txt',
        'vcs': 'https://github.com/maplibre/maplibre-gl-js',
        'website': 'https://maplibre.org/',
    },
}

BANNER_RE = re.compile(r'\A\s*/\*\*.*?\*/', re.S)


def banner_of(src):
    """The leading licence banner, verbatim, or None when the file has none."""
    m = BANNER_RE.match(src)
    if not m:
        return None
    b = m.group(0).strip()
    return b if '@license' in b or 'license' in b.lower() else None


def classify(rel, src):
    """Which upstream a vendored file belongs to, its subpath in that package,
    the version string read from the file, and the evidence for it."""
    parts = rel.split('/')
    if rel == 'three.module.min.js':
        m = re.search(r'\*/\s*const t="(\d+)"', src)
        assert m, 'three.module.min.js: no `const t="<revision>"` after the banner'
        return 'three', None, f'0.{m.group(1)}.0', m.group(0)[m.group(0).index('const'):]
    if parts[0] == 'addons':
        # examples/jsm files of the three npm package. They carry no banner and
        # no version string of their own; they import from 'three' and were
        # vendored beside three.module.min.js r160 (THIRD_PARTY.md).
        assert "from 'three'" in src, f'{rel}: does not import from three'
        return 'three', 'examples/jsm/' + '/'.join(parts[1:]), None, None
    if parts[0] == 'maplibre':
        if rel.endswith('.js'):
            m = re.search(r'"use strict";var \w+="(\d+\.\d+\.\d+)";', src)
            assert m, 'maplibre-gl.js: no version string found'
            return 'maplibre-gl', 'dist/' + parts[-1], m.group(1), m.group(0)[len('"use strict";'):]
        return 'maplibre-gl', 'dist/' + parts[-1], None, None
    raise SystemExit(f'unclassified vendored file {rel}')


def build():
    files = sorted(p for p in VENDOR.rglob('*') if p.is_file())
    assert files, 'web/vendor is empty'
    comps = []
    versions = {}
    # First pass: versions are read from the files that carry them.
    read = {}
    for p in files:
        rel = p.relative_to(VENDOR).as_posix()
        src = p.read_text(encoding='utf-8', errors='replace')
        up, sub, ver, ver_ev = classify(rel, src)
        read[rel] = (src, up, sub, ver, ver_ev)
        if ver:
            assert versions.get(up, ver) == ver, f'{up}: two versions read'
            versions[up] = ver
    for up in UPSTREAMS:
        assert up in versions, f'{up}: no vendored file carries its version'

    for p in files:
        rel = p.relative_to(VENDOR).as_posix()
        src, up, sub, ver, ver_ev = read[rel]
        meta = UPSTREAMS[up]
        version = versions[up]
        banner = banner_of(src)
        props = [{'name': 'smartcitix:vendored_path', 'value': f'web/vendor/{rel}'}]
        if ver_ev:
            props.append({'name': 'smartcitix:version_evidence', 'value': ver_ev})
        else:
            props.append({'name': 'smartcitix:version_evidence',
                          'value': 'no version string in this file; version attributed from the '
                                   f'{up} file vendored beside it that carries one (see THIRD_PARTY.md)'})
        if banner:
            props.append({'name': 'smartcitix:licence_evidence', 'value': 'banner in file (evidence.copyright)'})
        elif up == 'three':
            props.append({'name': 'smartcitix:licence_evidence',
                          'value': "no licence banner in this file; it is the examples/jsm file of the three "
                                   "npm package (imports from 'three') and carries that distribution's licence, "
                                   'whose banner is in three.module.min.js: SPDX-License-Identifier: MIT'})
        else:
            props.append({'name': 'smartcitix:licence_evidence',
                          'value': 'no licence banner in this file; it is the stylesheet of the same '
                                   'maplibre-gl dist as maplibre-gl.js, whose banner names 3-Clause BSD'})
        if up == 'maplibre-gl':
            props.append({'name': 'smartcitix:licence_text',
                          'value': 'not vendored and not fetched (no network at build); the banner names '
                                   'the licence and the URL of its full text'})
        comp = {
            'type': 'library',
            'bom-ref': f'web/vendor/{rel}',
            'name': up,
            'version': version,
            'purl': f"{meta['purl']}@{version}" + (f'#{sub}' if sub else ''),
            'hashes': [{'alg': 'SHA-256', 'content': hashlib.sha256(p.read_bytes()).hexdigest()}],
            'licenses': [{'license': {'id': meta['license'], 'url': meta['license_url']}}],
            'externalReferences': [
                {'type': 'vcs', 'url': meta['vcs']},
                {'type': 'website', 'url': meta['website']},
                {'type': 'license', 'url': meta['license_url']},
            ],
            'evidence': {
                'occurrences': [{'location': f'web/vendor/{rel}'}],
                'copyright': ([{'text': banner}] if banner else []),
            },
            'properties': props,
        }
        comps.append(comp)

    stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
    doc = {
        'bomFormat': 'CycloneDX',
        'specVersion': '1.5',
        'version': 1,
        'metadata': {
            'component': {
                'type': 'application',
                'bom-ref': 'smartcitix-trade-craft-academy',
                'name': 'SmartCiti.X : Trade Craft Academy',
                'version': MANIFEST['pack_version'],
                'description': 'the implementation bundle; every pack outside web/vendor is first-party '
                               'with zero runtime dependencies',
            },
            'tools': {'components': [{'type': 'application', 'name': 'security/build_sbom.py',
                                      'version': MANIFEST['pack_version']}]},
            'properties': [
                {'name': 'smartcitix:source_stamp', 'value': stamp},
                {'name': 'smartcitix:scope', 'value': 'every file under web/vendor/, and nothing else — '
                                                      'the test walks the tree and holds the list to it'},
                {'name': 'smartcitix:first_party', 'value': 'everything outside web/vendor/ is original to '
                                                            'the bundle; orbis/runner-*/ carry their own '
                                                            'LICENSE files and are first-party'},
                {'name': 'smartcitix:ci_scanning', 'value': 'dependency and container scanning in CI: not '
                                                            'configured — needs a workflow change the '
                                                            'maintainers must approve'},
                {'name': 'smartcitix:reproducible', 'value': 'no timestamp and no serial number on purpose: '
                                                             'the same tree builds the same document'},
            ],
        },
        'components': comps,
    }
    return doc


if __name__ == '__main__':
    doc = build()
    out = HERE / 'registry'
    out.mkdir(exist_ok=True)
    (out / 'sbom.cdx.json').write_text(json.dumps(doc, indent=1) + '\n')
    print(f"sbom: {len(doc['components'])} components, source stamp "
          f"{doc['metadata']['properties'][0]['value']}")
    for c in doc['components']:
        print(f"  {c['name']:12} {c['version']:8} {c['licenses'][0]['license']['id']:12} "
              f"{c['hashes'][0]['content'][:12]}  {c['bom-ref']}")
