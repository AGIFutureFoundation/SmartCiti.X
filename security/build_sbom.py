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
    # The four self-hosted type families. One upstream EACH, not one
    # "webfonts" entry: they are four separate projects under four separate
    # copyrights that happen to share a licence, and collapsing them would
    # attribute three of them to the wrong authors. Each ships its own OFL
    # beside its files - see web/fetch_fonts.py, which refuses to write the
    # stylesheet if any licence is missing.
    'barlow-condensed': {
        'purl': 'pkg:generic/barlow-condensed',
        'license': 'OFL-1.1',
        'license_url': 'https://github.com/google/fonts/blob/main/ofl/barlowcondensed/OFL.txt',
        'vcs': 'https://github.com/jpt/barlow',
        'website': 'https://fonts.google.com/specimen/Barlow+Condensed',
    },
    'ibm-plex-sans': {
        'purl': 'pkg:generic/ibm-plex-sans',
        'license': 'OFL-1.1',
        'license_url': 'https://github.com/google/fonts/blob/main/ofl/ibmplexsans/OFL.txt',
        'vcs': 'https://github.com/IBM/plex',
        'website': 'https://fonts.google.com/specimen/IBM+Plex+Sans',
    },
    'ibm-plex-mono': {
        'purl': 'pkg:generic/ibm-plex-mono',
        'license': 'OFL-1.1',
        'license_url': 'https://github.com/google/fonts/blob/main/ofl/ibmplexmono/OFL.txt',
        'vcs': 'https://github.com/IBM/plex',
        'website': 'https://fonts.google.com/specimen/IBM+Plex+Mono',
    },
    'archivo': {
        'purl': 'pkg:generic/archivo',
        'license': 'OFL-1.1',
        'license_url': 'https://github.com/google/fonts/blob/main/ofl/archivo/OFL.txt',
        'vcs': 'https://github.com/Omnibus-Type/Archivo',
        'website': 'https://fonts.google.com/specimen/Archivo',
    },
}

# The font manifest web/fetch_fonts.py wrote: which family each file belongs
# to, and the upstream URL it came from. Read, never restated - the family
# and subset are already recorded there per file, and writing them again
# here would be a second copy that drifts the first time a weight changes.
FONT_MANIFEST = VENDOR / 'fonts' / 'manifest.json'
FAMILY_UP = {'Barlow Condensed': 'barlow-condensed', 'IBM Plex Sans': 'ibm-plex-sans',
             'IBM Plex Mono': 'ibm-plex-mono', 'Archivo': 'archivo'}

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
    if parts[0] == 'fonts':
        return classify_font(rel, parts[-1])
    raise SystemExit(f'unclassified vendored file {rel}')


def classify_font(rel, name):
    """A font file, its licence, or one of the two files we generated.

    The version is the upstream's own: Google Fonts serves each family under
    a `/s/<family>/v<N>/` path, and web/fetch_fonts.py recorded the exact URL
    it fetched. So the version is READ from what the origin served, the same
    rule the JavaScript files follow - not typed here.
    """
    man = json.loads(FONT_MANIFEST.read_text(encoding='utf-8'))
    if name in ('fonts.css', 'manifest.json'):
        # OURS. Generated by web/fetch_fonts.py, and first-party - but it
        # lives under web/vendor/ because the stylesheet's relative url()
        # has to sit beside the files it names. It is listed so the SBOM
        # covers the whole tree, and marked so nobody reads it as a
        # third-party component.
        return 'first-party', name, None, None
    if name.endswith('-OFL.txt'):
        for fam, lic in man['licences'].items():
            if lic['file'] == name:
                return FAMILY_UP[fam], name, font_version(lic['from']), lic['from']
        raise SystemExit(f'{rel}: a licence file no family in the manifest claims')
    rec = man['files'].get(name)
    if rec is None:
        raise SystemExit(f'{rel}: not in web/vendor/fonts/manifest.json - run '
                         'web/fetch_fonts.py rather than dropping a font in by hand')
    return FAMILY_UP[rec['family']], name, font_version(rec['from']), rec['from']


def font_version(url):
    """The `vN` Google Fonts serves this family under, read from the URL."""
    m = re.search(r'/s/[a-z0-9]+/(v\d+)/', url)
    if m:
        return m.group(1)
    # a licence comes from the google/fonts repository rather than the font
    # CDN, so it carries no v-number; the family's woff2 files supply one
    return None


def build():
    files = sorted(p for p in VENDOR.rglob('*') if p.is_file())
    assert files, 'web/vendor is empty'
    comps = []
    versions = {}
    # First pass: versions are read from the files that carry them.
    read = {}
    for p in files:
        rel = p.relative_to(VENDOR).as_posix()
        # a woff2 is not text. Reading one with errors='replace' produces
        # mojibake that the banner and version regexes would then search.
        src = ('' if p.suffix == '.woff2'
               else p.read_text(encoding='utf-8', errors='replace'))
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
        if up == 'first-party':
            # Ours, generated by web/fetch_fonts.py, living under web/vendor/
            # only because the stylesheet's relative url() must sit beside
            # the files it names. It is listed so the SBOM still accounts for
            # every file in the tree, and typed so a reader cannot mistake it
            # for something somebody else wrote.
            comps.append({
                'type': 'file',
                'bom-ref': f'web/vendor/{rel}',
                'name': f'smartcitix/{rel}',
                'version': MANIFEST['pack_version'],
                'hashes': [{'alg': 'SHA-256',
                            'content': hashlib.sha256(p.read_bytes()).hexdigest()}],
                'evidence': {'occurrences': [{'location': f'web/vendor/{rel}'}]},
                'properties': [
                    {'name': 'smartcitix:vendored_path', 'value': f'web/vendor/{rel}'},
                    {'name': 'smartcitix:first_party',
                     'value': 'generated by web/fetch_fonts.py; it describes the '
                              'vendored font files rather than being one'},
                ],
            })
            continue
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
        elif up in FAMILY_UP.values():
            # A font carries no banner - it is a binary - so the evidence is
            # the family's own OFL, committed beside it and hashed in the
            # font manifest. That is stronger than a banner, not weaker: the
            # full licence text is in the tree rather than behind a URL.
            lic = json.loads(FONT_MANIFEST.read_text(encoding='utf-8'))['licences']
            mine = next(v for k, v in lic.items() if FAMILY_UP[k] == up)
            props.append({'name': 'smartcitix:licence_evidence',
                          'value': 'no banner (binary or plain text); the full SIL OFL 1.1 for this '
                                   f"family is committed at web/vendor/fonts/{mine['file']}, "
                                   f"sha256 {mine['sha256'][:16]}..., and reads: {mine['copyright']}"})
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
    # 30 font files would drown the two JavaScript upstreams in this list,
    # so it prints one line per upstream with a file count, and names the
    # first-party entries separately rather than listing them as libraries.
    from collections import Counter
    libs = [c for c in doc['components'] if c['type'] == 'library']
    mine = [c for c in doc['components'] if c['type'] != 'library']
    per = Counter((c['name'], c['version'],
                   c['licenses'][0]['license']['id']) for c in libs)
    for (name, ver, lic), n in sorted(per.items()):
        print(f'  {name:18} {ver:9} {lic:12} {n:2} file' + ('s' if n != 1 else ''))
    for c in mine:
        print(f"  {c['name']:18} {'first-party':9} {'-':12}  1 file")
