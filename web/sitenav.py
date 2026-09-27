"""The site's navigation, declared once.

Every page builder under web/ that owns a page imports this and puts
`nav_html(<its own path>, labels())` right after `<body>`, and
`NAV_CSS` in its <head>. Nothing else in the tree lists the pages a reader
can move between: before this existed, most pages linked to two or four
of their siblings and several to none, so a learner who arrived anywhere
but the front door could not walk the training loop.

PAGES      every page file (path from the bundle root), its group, and the
           i18n key its link text is read from. web/test_nav.mjs holds that
           every .html under web/ is here and every entry here exists.
LOOP       the training loop, in order: which page each step is on and the
           key for its label. Rendered as a strip only on the pages that are
           steps of the loop, with the current step marked.

Every word the nav shows comes from the locale catalog (`nav.*` keys in
i18n/locales/*.json); this file holds keys, never label text, and holds no
digits in anything it renders (page suites scan for typed counts). Hrefs
are relative to the page being built, so the same declaration works from
index.html at the root and from the pages under web/. The CSS uses only
logical properties and each page's own custom properties (with fallbacks),
so it mirrors under dir="rtl" and wraps at 360 px instead of scrolling.
"""
import html
import json
import pathlib
import posixpath

ROOT = pathlib.Path(__file__).resolve().parent.parent

FRONT_DOOR = 'index.html'

# (group key, [(page path from the bundle root, label key), ...]), in the
# order a reader sees them.
GROUPS = [
    ('nav.group.learn', [
        ('web/trade_craft_lessons.html', 'nav.page.lessons'),
        ('web/trade_craft_ladder.html', 'nav.page.ladder'),
        ('web/trade_craft_3d.html', 'nav.page.campus'),
    ]),
    ('nav.group.maps', [
        ('web/trade_craft_map.html', 'nav.page.map'),
        ('web/trade_craft_interactive.html', 'nav.page.interactive'),
        ('web/trade_craft_geomap.html', 'nav.page.geomap'),
        ('web/trade_craft_fabric.html', 'nav.page.fabric'),
    ]),
    ('nav.group.records', [
        ('web/trade_craft_progress.html', 'nav.page.progress'),
        ('web/trade_craft_verify.html', 'nav.page.verify'),
        ('web/trade_craft_contribute.html', 'nav.page.contribute'),
    ]),
    ('nav.group.sites', [
        ('web/trade_craft_spaces.html', 'nav.page.spaces'),
        ('web/trade_craft_worksites.html', 'nav.page.worksites'),
    ]),
    ('nav.group.about', [
        ('web/trade_craft_landing.html', 'nav.page.landing'),
        ('web/trade_craft_dashboard.html', 'nav.page.dashboard'),
        ('web/trade_craft_languages.html', 'nav.page.languages'),
        ('web/trade_craft_signin.html', 'nav.page.signin'),
        ('web/smartcitix_trade_craft_academy.html', 'nav.page.spec'),
    ]),
]

# Every page: path -> (group key, label key). The front door is a page too;
# its group is its own.
PAGES = {FRONT_DOOR: ('nav.group.home', 'nav.home')}
for _g, _items in GROUPS:
    for _p, _k in _items:
        assert _p not in PAGES, f'sitenav: {_p} declared twice'
        PAGES[_p] = (_g, _k)

# The training loop: sign in -> choose a lesson -> walk it in 3D -> export
# your record -> verify it -> share it.
LOOP = [
    ('web/trade_craft_signin.html', 'nav.loop.signin'),
    ('web/trade_craft_lessons.html', 'nav.loop.lesson'),
    ('web/trade_craft_3d.html', 'nav.loop.walk'),
    ('web/trade_craft_progress.html', 'nav.loop.export'),
    ('web/trade_craft_verify.html', 'nav.loop.verify'),
    ('web/trade_craft_contribute.html', 'nav.loop.share'),
]
for _p, _k in LOOP:
    assert _p in PAGES, f'sitenav: loop step {_p} is not a declared page'

KEYS = (['nav.site', 'nav.loop', 'nav.home', 'nav.group.home']
        + [g for g, _ in GROUPS] + [k for _, items in GROUPS for _, k in items]
        + [k for _, k in LOOP])


def labels(locale='en'):
    """The catalog's strings for one locale. Strict: every nav key must be
    there, the same rule as catalog.mjs's t() - a missing key fails the
    build rather than rendering a blank link."""
    doc = json.loads((ROOT / 'i18n' / 'locales' / f'{locale}.json').read_text(encoding='utf-8'))
    strings = doc['strings']
    missing = [k for k in KEYS if not isinstance(strings.get(k), str) or not strings[k].strip()]
    assert not missing, f'sitenav: {locale} catalog lacks {missing}'
    return strings


def _rel(current, target):
    base = posixpath.dirname(current) or '.'
    return posixpath.relpath(target, base)


def nav_html(current_path, labels):
    """The site header for the page at `current_path` (path from the
    bundle root): front-door link, the groups, the current page marked
    aria-current="page", and the loop strip when the page is a loop step."""
    assert current_path in PAGES, f'sitenav: {current_path} is not in PAGES'
    E = lambda k: html.escape(labels[k])

    def link(target, key, cls=''):
        cur = ' aria-current="page"' if target == current_path else ''
        c = f' class="{cls}"' if cls else ''
        return f'<a{c} href="{html.escape(_rel(current_path, target))}"{cur}>{E(key)}</a>'

    out = [f'<nav class="sitenav" data-sitenav aria-label="{E("nav.site")}">',
           '<div class="sitenav-row">',
           link(FRONT_DOOR, 'nav.home', 'sitenav-home')]
    for gkey, items in GROUPS:
        out.append(f'<div class="sitenav-group"><span class="sitenav-g">{E(gkey)}</span><ul>'
                   + ''.join(f'<li>{link(p, k)}</li>' for p, k in items) + '</ul></div>')
    out.append('</div>')
    steps = [p for p, _ in LOOP]
    if current_path in steps:
        out.append(f'<ol class="sitenav-loop" data-sitenav-loop aria-label="{E("nav.loop")}">')
        for p, k in LOOP:
            cur = ' aria-current="step"' if p == current_path else ''
            out.append(f'<li><a href="{html.escape(_rel(current_path, p))}"{cur}>{E(k)}</a></li>')
        out.append('</ol>')
    out.append('</nav>')
    return '\n'.join(out) + '\n'


NAV_CSS = (
    '.sitenav{font:13px/1.45 system-ui,sans-serif;color:var(--ink,inherit);'
    'background:var(--panel,var(--surface,transparent));'
    'border-block-end:1px solid var(--rule,var(--line,currentColor));'
    'padding-block:6px;padding-inline:16px;box-sizing:border-box;max-width:100%;'
    'overflow-wrap:anywhere}'
    '.sitenav a{color:inherit;text-decoration:none}'
    '.sitenav a:hover,.sitenav a:focus-visible{text-decoration:underline}'
    '.sitenav-row{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 16px}'
    '.sitenav-home{font-weight:700;color:var(--mark,var(--accent,inherit))!important}'
    '.sitenav-group{display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 8px;min-width:0}'
    '.sitenav-g{font-size:11px;text-transform:uppercase;letter-spacing:.06em;'
    'color:var(--muted,inherit)}'
    '.sitenav ul,.sitenav ol{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;'
    'gap:2px 10px}'
    '.sitenav [aria-current="page"]{font-weight:700;text-decoration:underline;'
    'text-underline-offset:3px;color:var(--mark,var(--accent,inherit))}'
    '.sitenav-loop{margin-block-start:6px!important;padding-block-start:6px!important;'
    'border-block-start:1px dashed var(--rule,var(--line,currentColor));counter-reset:step;'
    'align-items:baseline}'
    '.sitenav-loop li{counter-increment:step;color:var(--muted,inherit)}'
    '.sitenav-loop li::before{content:counter(step) ". ";color:var(--muted,inherit)}'
    '.sitenav-loop [aria-current="step"]{font-weight:700;color:var(--mark,var(--accent,inherit));'
    'text-decoration:underline;text-underline-offset:3px}'
    '@media(max-width:480px){.sitenav{padding-inline:10px}.sitenav-row{gap:4px 12px}}'
)
