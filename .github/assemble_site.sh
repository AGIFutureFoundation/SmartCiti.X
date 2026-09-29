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
rm -rf _site/parishes/maps/tiles   # the pages load one ground atlas per parish (parishes/maps/atlas)
python3 - <<'PY'
import json, pathlib, sys
reg = json.load(open('parishes/registry/parishes.json'))
named = [p['map'][k] for p in reg['parishes'].values() for k in ('path', 'preview')]
atl = json.load(open('parishes/registry/ground_atlas.json'))['atlases']
named += [a['path'] for k, a in atl.items() if k.startswith('parishes/')]
if (pathlib.Path('_site') / 'parishes/maps/tiles').exists():
    sys.exit('assemble: ground tiles must not ship; pages load parishes/maps/atlas')
named += [p['map']['streets']['path'] for p in reg['parishes'].values()]
missing = [m for m in named if not (pathlib.Path('_site') / m).is_file()]
if missing:
    sys.exit('assemble: parish maps named in parishes/registry are missing from _site: ' + ', '.join(missing))
print(f"parish maps: all {len(named)} registry-named maps, ground atlases and street files present in _site")
PY
# The Bay world loads its county maps the same way ('../' + path from
# bayarea/registry), and both worlds fetch underwater/registry/underwater.json
# on the first Dive/ROV press: copy them and require what the registries name.
mkdir -p _site/bayarea _site/underwater/registry
cp -r bayarea/maps _site/bayarea/maps
rm -rf _site/bayarea/maps/tiles    # the pages load one ground atlas per county (bayarea/maps/atlas)
cp underwater/registry/underwater.json _site/underwater/registry/underwater.json
# The Unspoken Smiles world loads its 4k map and one ground atlas at run time (paths from smiles/registry).
mkdir -p _site/smiles && cp -r smiles/maps _site/smiles/maps
# The parish and Bay worlds fetch the vendored USGS 3DEP grids at run time when relief is on (elevation/vendor).
mkdir -p _site/elevation/vendor && cp elevation/vendor/*.u16.gz elevation/vendor/manifest.json elevation/vendor/USGS_3DEP_USE_CONSTRAINTS.txt _site/elevation/vendor/
# ... and the vendored ESA WorldCover land-cover grids (CC BY 4.0, attribution beside them) that place the vegetation.
mkdir -p _site/landcover/vendor && cp landcover/vendor/*.u8.gz landcover/vendor/manifest.json landcover/vendor/WORLDCOVER_ATTRIBUTION.txt landcover/vendor/LICENSE_CC-BY-4.0.txt _site/landcover/vendor/
for f in landcover/vendor/parishes.u8.gz landcover/vendor/bayarea.u8.gz; do [ -f "_site/$f" ] || { echo "assemble: $f missing from _site"; exit 1; }; done
for f in elevation/vendor/parishes.u16.gz elevation/vendor/bayarea.u16.gz; do [ -f "_site/$f" ] || { echo "assemble: $f missing from _site"; exit 1; }; done
for f in smiles/maps/district-4k.webp smiles/maps/atlas.webp; do [ -f "_site/$f" ] || { echo "assemble: $f missing from _site"; exit 1; }; done
python3 - <<'PY'
import json, pathlib, sys
reg = json.load(open('bayarea/registry/bayarea.json'))
cs = reg['counties']
named = [c['map'][k] for c in cs.values() for k in ('path', 'preview')]
atl = json.load(open('parishes/registry/ground_atlas.json'))['atlases']
named += [a['path'] for k, a in atl.items() if k.startswith('bayarea/')]
if (pathlib.Path('_site') / 'bayarea/maps/tiles').exists():
    sys.exit('assemble: ground tiles must not ship; pages load bayarea/maps/atlas')
named += [c['map']['streets']['path'] for c in cs.values()]
named += ['underwater/registry/underwater.json']
missing = [m for m in named if not (pathlib.Path('_site') / m).is_file()]
if missing:
    sys.exit('assemble: Bay maps / underwater registry missing from _site: ' + ', '.join(missing))
print(f"bay maps: all {len(named)} registry-named Bay maps, ground atlases, street files and the underwater registry present in _site")
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
