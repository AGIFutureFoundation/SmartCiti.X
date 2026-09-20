"""Self-host the web fonts, once, and record exactly what was taken.

Five pages loaded three families from fonts.googleapis.com, which made a
Google request part of opening any of them: an origin this bundle does not
control, cannot verify, and which sees a visitor's IP. Everything else here
is served from the repository, so the fonts were the last thing that was
not.

This fetches them into web/vendor/fonts/ and writes the @font-face rules
itself. It is NOT part of the build: it runs once, by hand, and its output
is committed. `--check` re-verifies the committed files against the
manifest without reaching the network, which is what verify_all.sh runs.

What is taken, and what is deliberately not: the `latin` and `latin-ext`
subsets only. This bundle ships eight locales, three of which - Arabic,
Hindi and Chinese - are in scripts none of these three families covers at
all. Those locales fell back to the reader's system fonts before this
change and they fall back to the reader's system fonts after it; taking the
Cyrillic, Greek and Vietnamese subsets would have added bytes for scripts
no locale here uses. The fallback stack in every page's CSS is what serves
those readers, and it did before too.
"""
import hashlib
import json
import pathlib
import re
import sys
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / 'vendor' / 'fonts'
MANIFEST = OUT / 'manifest.json'
CSS = OUT / 'fonts.css'

# A real browser UA, because the Google Fonts CSS endpoint serves a
# different stylesheet to clients it thinks cannot take woff2 - and the
# older format is roughly a third larger for the same glyphs.
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/120.0.0.0 Safari/537.36')

# The three families the pages ask for, at the weights they actually use.
# A weight nobody sets is a file nobody downloads, so this list is the
# union of what the five builders name, not the family's full range.
FAMILIES = [
    'Barlow+Condensed:wght@600;700',
    # the italic 400 is not decoration: web/build_page.py sets one, and a
    # missing italic face is synthesised by the browser into a sheared
    # upright, which is exactly the thing a type family exists to avoid
    'IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400',
    'IBM+Plex+Mono:wght@400;500;600',
    'Archivo:wght@500;600;700',          # the console's display face
]
# Each family's own licence, taken from the upstream project rather than
# summarised: all four are SIL OFL 1.1, but they carry different copyright
# holders and different reserved font names, and a single pasted OFL would
# name the wrong authors for three of them. The slug is Google Fonts' own
# directory name for the family.
LICENCES = {
    'Barlow Condensed': 'ofl/barlowcondensed',
    'IBM Plex Sans': 'ofl/ibmplexsans',
    'IBM Plex Mono': 'ofl/ibmplexmono',
    'Archivo': 'ofl/archivo',
}
LICENCE_URL = 'https://raw.githubusercontent.com/google/fonts/main/{}/OFL.txt'
WANT_SUBSETS = ('latin', 'latin-ext')


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def slug(family, weight, style, subset):
    f = family.lower().replace(' ', '-')
    return f'{f}-{weight}-{style}-{subset}.woff2'


def harvest():
    """Pull the CSS, keep only the subsets we want, and download each file."""
    url = ('https://fonts.googleapis.com/css2?'
           + '&'.join('family=' + f for f in FAMILIES) + '&display=swap')
    css = fetch(url).decode('utf-8')

    # The stylesheet is a run of `/* subset */ @font-face { ... }` blocks.
    # Splitting on the comment is what tells us which subset each block is
    # for - the block itself only carries a unicode-range, and matching
    # ranges by hand would be a second, worse copy of that fact.
    blocks = re.findall(r'/\*\s*([a-z-]+)\s*\*/\s*(@font-face\s*\{.*?\})', css, re.S)
    if not blocks:
        raise SystemExit('the Google Fonts CSS did not parse into subset blocks - '
                         'the endpoint has changed shape and this script must too')

    files, rules, seen = {}, [], set()
    for subset, block in blocks:
        if subset not in WANT_SUBSETS:
            continue
        fam = re.search(r"font-family:\s*'([^']+)'", block).group(1)
        wt = re.search(r'font-weight:\s*(\d+)', block).group(1)
        st = re.search(r'font-style:\s*(\w+)', block).group(1)
        src = re.search(r'url\((https://[^)]+\.woff2)\)', block).group(1)
        rng = re.search(r'unicode-range:\s*([^;]+);', block).group(1).strip()
        name = slug(fam, wt, st, subset)
        if name in seen:
            raise SystemExit(f'two blocks claim the same file name: {name}')
        seen.add(name)
        blob = fetch(src)
        if blob[:4] != b'wOF2':
            raise SystemExit(f'{name} did not come back as woff2 - refusing to '
                             'commit a file whose format is not what it claims')
        (OUT / name).write_bytes(blob)
        files[name] = {'family': fam, 'weight': int(wt), 'style': st,
                       'subset': subset, 'bytes': len(blob),
                       'sha256': hashlib.sha256(blob).hexdigest(),
                       'from': src}
        rules.append(f"""@font-face {{
  font-family: '{fam}';
  font-style: {st};
  font-weight: {wt};
  font-display: swap;
  src: url(./{name}) format('woff2');
  unicode-range: {rng};
}}""")

    if not files:
        raise SystemExit('nothing was taken - the subset filter matched no block')
    fams = sorted({f['family'] for f in files.values()})
    # A licence file is not paperwork here: redistributing these bytes is
    # only permitted with it, so a missing one means this directory may not
    # be served at all. Fetch each family's own, and refuse to write the
    # stylesheet that points at them if any is missing.
    lic = {}
    for fam in fams:
        if fam not in LICENCES:
            raise SystemExit(f'{fam} has no licence source declared - refusing '
                             'to commit a font whose terms are not recorded')
        text = fetch(LICENCE_URL.format(LICENCES[fam])).decode('utf-8')
        if 'SIL OPEN FONT LICENSE' not in text.upper():
            raise SystemExit(f'{fam}: what came back does not read as an OFL')
        name = fam.lower().replace(' ', '-') + '-OFL.txt'
        (OUT / name).write_text(text, encoding='utf-8')
        lic[fam] = {'file': name,
                    'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                    'copyright': text.splitlines()[0].strip(),
                    'from': LICENCE_URL.format(LICENCES[fam])}
    header = ('/* Self-hosted. Taken once by web/fetch_fonts.py from Google Fonts,\n'
              '   each family under its own SIL Open Font License 1.1, committed\n'
              '   beside these files:\n'
              + ''.join(f'     {fam} - {lic[fam]["file"]}\n' for fam in fams)
              + f'   {len(files)} files, {len(fams)} families, subsets: '
              f'{", ".join(WANT_SUBSETS)}.\n'
              '   Nothing on any page fetches a font at run time. */\n')
    CSS.write_text(header + '\n'.join(rules) + '\n', encoding='utf-8')
    MANIFEST.write_text(json.dumps(
        {'families': fams, 'subsets': list(WANT_SUBSETS), 'licences': lic,
         'count': len(files), 'bytes': sum(f['bytes'] for f in files.values()),
         'css_sha256': hashlib.sha256(CSS.read_bytes()).hexdigest(),
         'files': dict(sorted(files.items()))}, indent=1) + '\n', encoding='utf-8')
    return files


def check():
    """Verify the committed files against the manifest. Reaches no network."""
    if not MANIFEST.exists():
        print('STALE: web/vendor/fonts/manifest.json is missing')
        print('       run: python3 web/fetch_fonts.py')
        return 1
    m = json.loads(MANIFEST.read_text(encoding='utf-8'))
    bad = []
    for name, rec in m['files'].items():
        p = OUT / name
        if not p.exists():
            bad.append(f'{name}: missing'); continue
        blob = p.read_bytes()
        if hashlib.sha256(blob).hexdigest() != rec['sha256']:
            bad.append(f'{name}: sha256 does not match the manifest')
        elif len(blob) != rec['bytes']:
            bad.append(f'{name}: {len(blob)} bytes, manifest says {rec["bytes"]}')
    # A file on disk that the manifest does not know about is served to
    # visitors by a bundle that cannot say where it came from.
    extra = sorted(p.name for p in OUT.glob('*.woff2') if p.name not in m['files'])
    bad += [f'{n}: on disk but not in the manifest' for n in extra]
    for fam, rec in m['licences'].items():
        lp = OUT / rec['file']
        if not lp.exists():
            bad.append(f"{rec['file']}: missing, and {fam} may not be "
                       'redistributed without it')
        elif hashlib.sha256(lp.read_bytes()).hexdigest() != rec['sha256']:
            bad.append(f"{rec['file']}: sha256 does not match the manifest")
    if not CSS.exists():
        bad.append('fonts.css: missing')
    elif hashlib.sha256(CSS.read_bytes()).hexdigest() != m['css_sha256']:
        bad.append('fonts.css: sha256 does not match the manifest')
    if bad:
        print('STALE: web/vendor/fonts')
        for b in bad:
            print('       ' + b)
        return 1
    print(f"web/vendor/fonts is current ({m['count']} files, "
          f"{m['bytes']:,} bytes, {len(m['families'])} families, "
          f"{len(m['licences'])} licences, subsets {', '.join(m['subsets'])})")
    return 0


if __name__ == '__main__':
    if '--check' in sys.argv:
        sys.exit(check())
    OUT.mkdir(parents=True, exist_ok=True)
    got = harvest()
    print(f'fetched {len(got)} files, {sum(f["bytes"] for f in got.values()):,} bytes '
          f'into web/vendor/fonts/')
