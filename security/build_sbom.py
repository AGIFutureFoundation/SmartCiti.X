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

Works the bundle MEASURES rather than ships - a CC-BY 3D scan read for its
dimensions, say - are NOT components: no byte of them is here. They are named
in metadata.properties as smartcitix:measurement_sources, read out of the
registry of the pack that measured them.

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
# The second vendor root (wave 5b): data, not browser code. parishes/fetch_usatlas.py
# vendored us-atlas's counties-10m.json + LICENSE after checking the npm tarball's
# sha512 against the registry dist.integrity, and recorded each file's sha256 in
# its manifest. Every file here is checked against that manifest before it is listed.
PARISH_VENDOR = ROOT / 'parishes' / 'vendor'
USATLAS_MANIFEST = PARISH_VENDOR / 'us-atlas' / 'manifest.json'
USATLAS = {
    'purl': 'pkg:npm/us-atlas',
    'license': 'ISC',
    'license_url': 'https://github.com/topojson/us-atlas/blob/master/LICENSE',
    'vcs': 'https://github.com/topojson/us-atlas',
    'website': 'https://www.npmjs.com/package/us-atlas',
}
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
        'license_url': 'https://github.com/maplibre/maplibre-gl-js/blob/v5.24.0/LICENSE.txt',
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
    # The design kit's icons: only the SVGs web/design_kit.py draws, taken by
    # media/fetch_icons.py from the npm tarball after its sha512 matched the
    # registry's dist.integrity. Each SVG carries its own one-line banner.
    'lucide-static': {
        'purl': 'pkg:npm/lucide-static',
        'license': 'ISC',
        'license_url': 'https://github.com/lucide-icons/lucide/blob/main/LICENSE',
        'vcs': 'https://github.com/lucide-icons/lucide',
        'website': 'https://lucide.dev/',
    },
}
ICON_MANIFEST = VENDOR / 'icons' / 'manifest.json'

# The font manifest web/fetch_fonts.py wrote: which family each file belongs
# to, and the upstream URL it came from. Read, never restated - the family
# and subset are already recorded there per file, and writing them again
# here would be a second copy that drifts the first time a weight changes.
FONT_MANIFEST = VENDOR / 'fonts' / 'manifest.json'
FAMILY_UP = {'Barlow Condensed': 'barlow-condensed', 'IBM Plex Sans': 'ibm-plex-sans',
             'IBM Plex Mono': 'ibm-plex-mono', 'Archivo': 'archivo'}

BANNER_RE = re.compile(r'\A\s*/\*\*.*?\*/', re.S)
# an SVG's banner is an XML comment on its first line
SVG_BANNER_RE = re.compile(r'\A\s*<!--.*?-->', re.S)


def banner_of(src):
    """The leading licence banner, verbatim, or None when the file has none."""
    m = BANNER_RE.match(src) or SVG_BANNER_RE.match(src)
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
    if parts[0] == 'icons':
        return classify_icon(rel, parts[-1], src)
    raise SystemExit(f'unclassified vendored file {rel}')


def classify_icon(rel, name, src):
    """An icon SVG, the package LICENSE, or the manifest media/fetch_icons.py
    wrote. Every file must be accounted for by that manifest, hash and all."""
    if name == 'manifest.json':
        return 'first-party', name, None, None
    man = json.loads(ICON_MANIFEST.read_text(encoding='utf-8'))
    rec = man['files'].get(name)
    if rec is None:
        raise SystemExit(f'{rel}: not in web/vendor/icons/manifest.json - run '
                         'media/fetch_icons.py rather than dropping an icon in by hand')
    if hashlib.sha256((ICON_MANIFEST.parent / name).read_bytes()).hexdigest() != rec['sha256']:
        raise SystemExit(f'{rel}: bytes differ from the hash recorded at fetch time')
    if name == 'LICENSE':
        return 'lucide-static', 'LICENSE', None, None
    m = re.search(r'lucide-static v(\d+\.\d+\.\d+)', src)
    assert m, f'{rel}: no lucide-static version in its banner'
    return 'lucide-static', 'icons/' + name, m.group(1), m.group(0)


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


# The four fields CC-BY asks for, which a measuring pack records in its own
# registry. Named here so the failure below can name the one that is missing.
CC_BY_FIELDS = ('author', 'title', 'source_url', 'license_id', 'license_url')


def measurement_sources():
    """Works the bundle MEASURES but does not redistribute.

    Not components, and deliberately so: no byte of such a work is vendored,
    fetched or shipped, nothing derived from it runs, and `test_sbom.mjs`
    holds the component list to `web/vendor/` exactly. But a BOM is where a
    downstream reader looks for the obligations that ride along with the
    bundle, and publishing measurements of a CC-BY work carries one. So the
    work is named in metadata, where a statement about the bundle belongs,
    and never in `components`, where a statement about shipped bytes belongs.

    Found STRUCTURALLY - any pack registry with an `attribution` block whose
    `license_id` is a CC-BY licence - so a pack added later is picked up
    without editing this list. Nothing is typed here: every value is read out
    of the registry that owns it, and a missing field is fatal rather than
    defaulted, because a half-stated attribution is worse than a loud build.
    """
    out = []
    for reg in sorted(ROOT.glob('*/registry/*.json')):
        rel = reg.relative_to(ROOT).as_posix()
        try:
            doc = json.loads(reg.read_text(encoding='utf-8'))
        except (ValueError, UnicodeDecodeError):
            continue
        if not isinstance(doc, dict) or 'attribution' not in doc:
            continue
        attr = doc['attribution']
        if 'license_id' not in attr:
            raise SystemExit(f'{rel}: attribution block with no license_id; a '
                             'licence this build cannot read is one it cannot honour')
        if not str(attr['license_id']).startswith('CC-BY'):
            continue
        for field in CC_BY_FIELDS:
            if field not in attr or not str(attr[field]).strip():
                raise SystemExit(f'{rel}: attribution.{field} is missing or empty; '
                                 'CC-BY asks for the author, the work, the licence '
                                 'and an indication of changes')
        out.append((rel, attr))
    return out


def parish_vendor_components():
    """Components for parishes/vendor/: every file must be in the manifest
    parishes/fetch_usatlas.py wrote, with the same sha256, or the build stops."""
    man = json.loads(USATLAS_MANIFEST.read_text(encoding='utf-8'))
    assert man['package'] == 'us-atlas' and man['license'] == USATLAS['license'], 'us-atlas manifest: package/licence'
    assert man['integrity'].startswith('sha512-'), 'us-atlas manifest: no sha512 integrity recorded'
    out = []
    for p in sorted(q for q in PARISH_VENDOR.rglob('*') if q.is_file()):
        rel = p.relative_to(ROOT).as_posix()
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        if p == USATLAS_MANIFEST:
            out.append({
                'type': 'file', 'bom-ref': rel, 'name': 'smartcitix/parishes/vendor/us-atlas/manifest.json',
                'version': MANIFEST['pack_version'],
                'hashes': [{'alg': 'SHA-256', 'content': digest}],
                'evidence': {'occurrences': [{'location': rel}]},
                'properties': [
                    {'name': 'smartcitix:vendored_path', 'value': rel},
                    {'name': 'smartcitix:first_party', 'value': 'generated by parishes/fetch_usatlas.py; it records '
                     'where each vendored us-atlas file came from, the verified tarball integrity and each hash'},
                ],
            })
            continue
        if p.parent != USATLAS_MANIFEST.parent or p.name not in man['files']:
            raise SystemExit(f'{rel}: not in parishes/vendor/us-atlas/manifest.json - run '
                             'parishes/fetch_usatlas.py rather than dropping a file in by hand')
        if digest != man['files'][p.name]['sha256']:
            raise SystemExit(f'{rel}: bytes differ from the hash recorded at fetch time')
        out.append({
            'type': 'library', 'bom-ref': rel, 'name': 'us-atlas', 'version': man['version'],
            'purl': f"{USATLAS['purl']}@{man['version']}#{p.name}",
            'hashes': [{'alg': 'SHA-256', 'content': digest}],
            'licenses': [{'license': {'id': USATLAS['license'], 'url': USATLAS['license_url']}}],
            'externalReferences': [
                {'type': 'vcs', 'url': USATLAS['vcs']},
                {'type': 'website', 'url': USATLAS['website']},
                {'type': 'license', 'url': USATLAS['license_url']},
                {'type': 'distribution', 'url': man['tarball']},
            ],
            'evidence': {'occurrences': [{'location': rel}], 'copyright': []},
            'properties': [
                {'name': 'smartcitix:vendored_path', 'value': rel},
                {'name': 'smartcitix:version_evidence',
                 'value': 'no version string in this file; version attributed from '
                          'parishes/vendor/us-atlas/manifest.json, which parishes/fetch_usatlas.py wrote after the '
                          f"tarball sha512 matched the npm registry dist.integrity ({man['integrity']})"},
                {'name': 'smartcitix:licence_evidence',
                 'value': 'no licence banner in this file; ' + (
                     'it IS the full ISC licence text of the us-atlas package, taken from the same verified tarball'
                     if p.name == 'LICENSE' else
                     'the full ISC text of the us-atlas package is committed beside it at '
                     'parishes/vendor/us-atlas/LICENSE; the Census outlines it packages are public domain')},
                {'name': 'smartcitix:data_origin', 'value': man['data_origin']},
            ],
        })
    return out


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
                     'value': ('generated by media/fetch_icons.py; it records where each vendored '
                               'icon came from and its hash rather than being one')
                     if rel.startswith('icons/') else
                              'generated by web/fetch_fonts.py; it describes the '
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
        elif up == 'lucide-static':
            props.append({'name': 'smartcitix:licence_evidence',
                          'value': 'no licence banner in this file; it IS the full ISC licence text of '
                                   'the lucide-static package, taken from the same verified tarball'})
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

    comps.extend(parish_vendor_components())

    stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
    measured = measurement_sources()
    first_party = ('everything outside web/vendor/ and parishes/vendor/ is original to '
                   'the bundle; orbis/runner-*/ carry their own '
                   'LICENSE files and are first-party')
    if measured:
        first_party += ('. One exception, and it is measurement rather than code: '
                        'the packs named in smartcitix:measurement_sources publish '
                        "figures DERIVED from somebody else's licensed work while "
                        'redistributing no part of that work')
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
                'description': 'the implementation bundle; every pack outside web/vendor and parishes/vendor is first-party '
                               'with zero runtime dependencies',
            },
            'tools': {'components': [{'type': 'application', 'name': 'security/build_sbom.py',
                                      'version': MANIFEST['pack_version']}]},
            'properties': [
                {'name': 'smartcitix:source_stamp', 'value': stamp},
                {'name': 'smartcitix:scope', 'value': 'every file under web/vendor/ and parishes/vendor/, and nothing else — '
                                                      'the test walks the tree and holds the list to it'},
                {'name': 'smartcitix:first_party', 'value': first_party},
                {'name': 'smartcitix:ci_scanning', 'value': 'dependency and container scanning in CI: not '
                                                            'configured — needs a workflow change the '
                                                            'maintainers must approve'},
                {'name': 'smartcitix:reproducible', 'value': 'no timestamp and no serial number on purpose: '
                                                             'the same tree builds the same document'},
                # One property per measured work - NOT a component. Every value
                # comes out of the registry named at the end of it.
                *[{'name': 'smartcitix:measurement_sources',
                   'value': f"{a['title']} by {a['author']}, {a['license_id']}, {a['source_url']} "
                            f"(licence deed {a['license_url']}). MEASURED, NOT REDISTRIBUTED: no "
                            'geometry, no texture and no part of the file is in this bundle, and no '
                            'component listed here comes from it. The measurements published from it, '
                            "and the licence's four attribution fields, are in "
                            f'{rel}; THIRD_PARTY.md credits it for a human reader.'}
                  for rel, a in measured],
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
