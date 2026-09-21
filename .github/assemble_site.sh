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
    for href in re.findall(r'(?:href|src)="([^"]+)"', html):
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
