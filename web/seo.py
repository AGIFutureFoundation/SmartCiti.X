"""Search-engine and link-preview head tags, declared once.

Every page builder calls `seo_head(path, title, description, kind)` in its
<head> in place of a hand-typed <title>. It returns the title, the meta
description, the canonical URL, Open Graph and Twitter card tags, JSON-LD
and theme-color - one set of rules for every page, so a crawler or a chat
app's link preview sees the same truthful card for the page it was handed.

What it refuses, and why (each is an assertion, so the build stops):
  - a path that is not a page in web/sitenav.py PAGES: the canonical URL,
    the sitemap and the nav must describe the same site;
  - an empty description or one over 160 characters: longer ones are cut
    mid-sentence by every search result page, which turns a true sentence
    into a misleading fragment;
  - a `kind` it does not know. The JSON-LD types are deliberately few:
    Organization + WebSite for the front door, WebPage / CollectionPage
    elsewhere. No Course, no ratings, no prices, no accreditation - the
    lessons are unverified general practice and nothing here is accredited,
    so no structured data may suggest otherwise.

BASE is the published root. The repository is AGIFutureFoundation/SmartCiti.X
and .github/workflows/pages.yml deploys it with actions/deploy-pages, whose
project-site URL follows GitHub's fixed pattern
https://<owner>.github.io/<repo>/. Neither the workflow nor the README states
a custom domain, so this is that pattern.

    DEPLOYER: if the site is served anywhere else (a custom domain, a
    fork), set BASE below - it is the only place the published origin is
    written - and rebuild the pages and web/build_seo.py.
"""
import html
import json
import pathlib
import struct

from sitenav import PAGES, FRONT_DOOR

ROOT = pathlib.Path(__file__).resolve().parent.parent

# DEPLOYER: the one place the published origin lives. Keep the trailing slash.
BASE = 'https://agifuturefoundation.github.io/SmartCiti.X/'

SITE_NAME = 'SmartCiti.X : Trade Craft Academy'
DESC_MAX = 160
KINDS = ('home', 'page', 'collection')

# The card image: a real screenshot of this build, committed under wiki/img
# (the wiki is copied into the deployed site by .github/assemble_site.sh).
OG_IMAGE = 'wiki/img/process-front-door.png'
OG_IMAGE_ALT = ('The SmartCiti.X Trade Craft Academy front door: the site header, '
                'the hero with its two calls to action and the key figures panel.')

# One theme colour, the front door's dark plate - the browser chrome tint.
THEME_DARK = '#0D1316'
THEME_LIGHT = '#F4F6F5'


def png_size(rel):
    """Width and height read from the PNG's own IHDR, so og:image:width and
    height are measured rather than typed."""
    raw = (ROOT / rel).read_bytes()
    assert raw[:8] == b'\x89PNG\r\n\x1a\n', f'seo: {rel} is not a PNG'
    return struct.unpack('>II', raw[16:24])


def canonical(path):
    """The page's public URL. The front door is the site root."""
    assert path in PAGES, f'seo: {path} is not a page in web/sitenav.py PAGES'
    return BASE if path == FRONT_DOOR else BASE + path


def _jsonld(path, title, description, kind):
    url = canonical(path)
    site = {'@type': 'WebSite', '@id': BASE + '#website', 'url': BASE,
            'name': SITE_NAME, 'inLanguage': 'en'}
    if kind == 'home':
        org = {'@type': 'Organization', '@id': BASE + '#organization',
               'name': SITE_NAME, 'url': BASE, 'description': description}
        site['publisher'] = {'@id': BASE + '#organization'}
        graph = [org, site]
    else:
        page_type = 'CollectionPage' if kind == 'collection' else 'WebPage'
        graph = [{'@type': page_type, '@id': url, 'url': url, 'name': title,
                  'description': description, 'inLanguage': 'en',
                  'isPartOf': {'@id': BASE + '#website'}}, site]
    doc = {'@context': 'https://schema.org', '@graph': graph}
    # `</` cannot close the script early once escaped.
    return json.dumps(doc, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')


def _checked(path, title, description, kind):
    assert kind in KINDS, f'seo: kind {kind!r} is not one of {KINDS}'
    assert isinstance(title, str) and title.strip(), f'seo: {path} has no title'
    assert isinstance(description, str) and description.strip(), \
        f'seo: {path} has no description'
    description = ' '.join(description.split())
    assert len(description) <= DESC_MAX, (
        f'seo: {path} description is {len(description)} characters; the limit is '
        f'{DESC_MAX} so no search result cuts it mid-sentence: {description!r}')
    return description


def seo_tail(path, title, description, kind='page'):
    """The JSON-LD block, for the END of <body>. It is kept out of <head>
    because several page suites read a page's FIRST <script> as its own
    payload or renderer; structured data is valid anywhere in the document,
    so it goes last and disturbs none of them."""
    description = _checked(path, title, description, kind)
    return (f'<script type="application/ld+json" data-seo-jsonld>'
            f'{_jsonld(path, title, description, kind)}</script>\n')


def seo_head(path, title, description, kind='page', canonical_link=True):
    """The <head> tags for one page, <title> included (JSON-LD: seo_tail).

    The canonical <link> is written RELATIVE to the page (its own file name;
    the front door's is BASE itself) - it resolves to exactly the canonical
    URL on the published site, and page suites that hold every href to a
    file in the bundle stay true. og:url, the sitemap and JSON-LD carry the
    absolute URL. `canonical_link=False` is for a page whose own contract
    forbids any <link> (the verifier: nothing it could send to); its og:url
    still names the canonical URL."""
    description = _checked(path, title, description, kind)
    url = canonical(path)
    rel = BASE if path == FRONT_DOOR else path.rsplit('/', 1)[-1]
    w, h = png_size(OG_IMAGE)
    img = BASE + OG_IMAGE
    E = lambda s: html.escape(s, quote=True)  # noqa: E731
    og_type = 'website'
    tags = [
        f'<title>{E(title)}</title>',
        f'<meta name="description" content="{E(description)}">',
        *([f'<link rel="canonical" href="{E(rel)}">'] if canonical_link else []),
        f'<meta name="theme-color" content="{THEME_DARK}" media="(prefers-color-scheme: dark)">',
        f'<meta name="theme-color" content="{THEME_LIGHT}" media="(prefers-color-scheme: light)">',
        f'<meta property="og:type" content="{og_type}">',
        f'<meta property="og:site_name" content="{E(SITE_NAME)}">',
        f'<meta property="og:title" content="{E(title)}">',
        f'<meta property="og:description" content="{E(description)}">',
        f'<meta property="og:url" content="{E(url)}">',
        '<meta property="og:locale" content="en_US">',
        f'<meta property="og:image" content="{E(img)}">',
        f'<meta property="og:image:width" content="{w}">',
        f'<meta property="og:image:height" content="{h}">',
        f'<meta property="og:image:alt" content="{E(OG_IMAGE_ALT)}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{E(title)}">',
        f'<meta name="twitter:description" content="{E(description)}">',
        f'<meta name="twitter:image" content="{E(img)}">',
        f'<meta name="twitter:image:alt" content="{E(OG_IMAGE_ALT)}">',
    ]
    return '\n'.join(tags) + '\n'


def apply_seo(page, path, title, description, kind='page', canonical_link=True, jsonld=True):
    """Swap a built page's one hand-typed <title> for the full seo_head().

    For builders whose <head> is a long literal: the swap touches only the
    <head>, and it stops the build if the head holds anything but exactly
    one <title> and no description or canonical of its own - so the page
    can never carry two conflicting cards."""
    # a page may leave </head> and even <body> implied; then the head ends
    # where the site nav (the first thing every page's body holds) begins
    marks = [page.find(m) for m in ('</head>', '<body', '<nav')]
    marks = [m for m in marks if m >= 0]
    assert marks, f'seo: {path} has no </head>, <body or <nav to bound its head'
    head_end = min(marks)
    head, rest = page[:head_end], page[head_end:]
    assert head.count('<title>') == 1, f'seo: {path} head has {head.count("<title>")} <title> tags'
    assert 'name="description"' not in head and 'rel="canonical"' not in head, \
        f'seo: {path} head already carries a description or canonical'
    start = head.index('<title>')
    end = head.index('</title>', start) + len('</title>')
    out = (head[:start] + seo_head(path, title, description, kind, canonical_link).rstrip('\n')
           + head[end:] + rest)
    # jsonld=False: for a page whose contract is that no script on it names
    # a remote origin (the verifier); JSON-LD's @context/@id are URLs.
    tail = seo_tail(path, title, description, kind) if jsonld else ''
    at = out.rfind('</body>')
    return out[:at] + tail + out[at:] if at >= 0 else out.rstrip('\n') + '\n' + tail
