#!/usr/bin/env bash
# Assemble the deployable site out of committed, verified pages, and refuse
# to hand over one whose own links do not resolve.
#
# Extracted from pages.yml so the two jobs that need it - the health check
# and the deploy - run the SAME assembly rather than two copies of it that
# could drift apart.
set -euo pipefail

rm -rf _site
mkdir -p _site/web/vendor _site/console
cp index.html _site/
cp web/*.html _site/web/
cp -r web/vendor/. _site/web/vendor/
cp console/trade_craft_console.html _site/console/
cp -r wiki _site/wiki
# The front door's background footage and poster (web/herovideo.py), and the
# search-engine files web/build_seo.py writes at the root.
cp -r web/media _site/web/media
cp sitemap.xml robots.txt _site/
# The parish world loads each parish's drawn map at run time ('../' + map path
# from parishes/registry), so the link check below cannot see them: copy the
# maps and require every map the registry names to be present.
mkdir -p _site/parishes
cp -r parishes/maps _site/parishes/maps
python3 - <<'PY'
import json, pathlib, sys
reg = json.load(open('parishes/registry/parishes.json'))
named = [p['map'][k] for p in reg['parishes'].values() for k in ('path', 'preview')]
named += [t['path'] for p in reg['parishes'].values() for t in p['map']['ground_tiles']['tiles']]
named += [p['map']['streets']['path'] for p in reg['parishes'].values()]
missing = [m for m in named if not (pathlib.Path('_site') / m).is_file()]
if missing:
    sys.exit('assemble: parish maps named in parishes/registry are missing from _site: ' + ', '.join(missing))
print(f"parish maps: all {len(named)} registry-named maps, ground tiles and street files present in _site")
PY

python3 - <<'PY'
import pathlib, re, sys, urllib.parse

site = pathlib.Path('_site')
# A page's markup is what a visitor follows. Script bodies also contain
# href=" strings, but those are template literals a renderer fills at run
# time ('${esc(s.source_url)}'), so they are cut out first rather than
# reported as broken files that were never meant to be files.
SCRIPT = re.compile(r'<script\b.*?</script>', re.S | re.I)
bad = []


def resolve(page, href):
    """Report the href if it does not land on a file in the assembled site."""
    if href.startswith(('http://', 'https://', 'data:', '#', 'mailto:')):
        return
    if '${' in href or '{{' in href:        # an unfilled template slot
        return
    target = (page.parent / urllib.parse.urlparse(href).path).resolve()
    if not target.exists():
        bad.append(f'{page.relative_to(site)} -> {href}')


pages = list(site.rglob('*.html'))
for page in pages:
    html = SCRIPT.sub(' ', page.read_text(errors='ignore'))
    # an attribute NAMED href or src, not one that merely ends in it: the front
    # door records each figure's registry in data-src="...", which is a citation
    # a reader sees, not a file the browser loads
    for href in re.findall(r'(?<![\w-])(?:href|src)="([^"]+)"', html):
        resolve(page, href)

# Stylesheets carry their own links, and the fonts now live behind one. A
# link check that stopped at the markup would have called the site sound
# with every @font-face pointing at a file that was never copied - the page
# would load, silently fall back to a system face, and look almost right.
sheets = list(site.rglob('*.css'))
for sheet in sheets:
    for ref in re.findall(r'url\(\s*["\']?([^"\')]+)', sheet.read_text(errors='ignore')):
        resolve(sheet, ref)

if bad:
    print('broken links in the assembled site:')
    for b in sorted(set(bad)):
        print('  ' + b)
    sys.exit(1)
print(f'link check: every local link in {len(pages)} assembled pages and '
      f'{len(sheets)} stylesheets resolves')
PY
