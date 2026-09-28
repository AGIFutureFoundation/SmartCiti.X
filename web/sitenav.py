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
so it mirrors under dir="rtl". Below its one breakpoint the groups fold into
a disclosure (summary = the nav's own `nav.site` label) that drops over the
page, so a phone opens on content rather than on eight rows of links; with
no script involved - a browser too old for ::details-content gets the menu
button at every width rather than a header with links it cannot reach.
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
        ('web/trade_craft_schools.html', 'nav.page.schools'),
    ]),
    ('nav.group.play', [
        ('web/trade_craft_quests.html', 'nav.page.quests'),
        ('web/trade_craft_wilds.html', 'nav.page.wilds'),
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
        ('web/trade_craft_design.html', 'nav.page.design'),
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

KEYS = (['nav.site', 'nav.loop', 'nav.home', 'nav.group.home', 'nav.skip', 'nav.search']
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

    # The groups sit in a native disclosure, closed. On a wide screen NAV_CSS
    # hides its summary and shows its content anyway (::details-content), so
    # the header is one flat bar; on a narrow one the summary is the menu
    # button. No script: page suites count and parse <script> tags, and a
    # header has no business adding one to every page.
    # The skip link is the nav's FIRST child: the first tab stop on every
    # page, hidden until focused. It lands on the target nav_html itself
    # emits right after </nav> (id="tc-main"), so every page that carries
    # the nav has a real place to skip to - no page can ship a skip link
    # that goes nowhere, whatever its own markup calls its content.
    out = [f'<nav class="sitenav" data-sitenav aria-label="{E("nav.site")}">',
           f'<a class="skip" href="#tc-main">{E("nav.skip")}</a>',
           '<div class="sitenav-row">',
           link(FRONT_DOOR, 'nav.home', 'sitenav-home'),
           '<details class="sitenav-menu" data-sitenav-menu>'
           f'<summary>{E("nav.site")}</summary>',
           '<div class="sitenav-groups">']
    for gkey, items in GROUPS:
        out.append(f'<div class="sitenav-group"><span class="sitenav-g">{E(gkey)}</span><ul>'
                   + ''.join(f'<li>{link(p, k)}</li>' for p, k in items) + '</ul></div>')
    out.append('</div></details>')
    # The site search: a script-free link to the front door's palette
    # (index.html#search), the header bar's last child on every page.
    out.append(search_trigger(current_path, labels['nav.search']))
    out.append('</div>')
    steps = [p for p, _ in LOOP]
    if current_path in steps:
        out.append(f'<ol class="sitenav-loop" data-sitenav-loop aria-label="{E("nav.loop")}">')
        for p, k in LOOP:
            cur = ' aria-current="step"' if p == current_path else ''
            out.append(f'<li><a href="{html.escape(_rel(current_path, p))}"{cur}>{E(k)}</a></li>')
        out.append('</ol>')
    out.append('</nav>')
    # the skip link's landing point: the first thing after the header
    out.append('<span id="tc-main" class="sitenav-skip-target" tabindex="-1"></span>')
    return '\n'.join(out) + '\n'


NAV_CSS = (
    '.sitenav{--sn-ink:var(--ink,CanvasText);--sn-bg:var(--panel,var(--surface,Canvas));'
    '--sn-rule:var(--rule,var(--line,GrayText));--sn-mute:var(--muted,var(--ink,CanvasText));'
    '--sn-mark:var(--mark,var(--accent,LinkText));'
    'position:relative;z-index:40;font:500 13.5px/1.35 "IBM Plex Sans",system-ui,sans-serif;'
    'color:var(--sn-ink);background:var(--sn-bg);'
    'border-block-end:1px solid var(--sn-rule);'
    'padding-block:6px;padding-inline:16px;box-sizing:border-box;max-width:100%;'
    'overflow-wrap:anywhere}'
    '.sitenav *{box-sizing:border-box}'
    '.sitenav a{color:inherit;text-decoration:none;border-radius:6px;'
    'padding-block:4px;padding-inline:7px;display:inline-block}'
    '.sitenav a:hover{background:color-mix(in srgb,currentColor 11%,transparent)}'
    '.sitenav a:focus-visible,.sitenav summary:focus-visible{outline:2px solid var(--sn-mark);'
    'outline-offset:2px}'
    '.sitenav a.skip{position:absolute;inset-inline-start:8px;inset-block-start:4px;z-index:60;'
    'padding-block:6px;padding-inline:12px;font-weight:700;color:var(--sn-ink);'
    'background:var(--sn-bg);border:2px solid var(--sn-mark);'
    'clip-path:inset(50%);overflow:hidden;white-space:nowrap;display:inline-flex;'
    'align-items:center;min-block-size:24px;box-sizing:border-box}'
    '.sitenav a.skip:focus,.sitenav a.skip:focus-visible{clip-path:none;overflow:visible}'
    '.sitenav-row{display:flex;align-items:center;gap:6px 12px;min-width:0}'
    # Text in the header is always the page's own ink on the page's own
    # panel - the one pair every page already holds to AA. The accent marks
    # things (a border, an underline bar) but never carries text, because an
    # accent that reads on one page's surface fails on another's.
    '.sitenav-home{font-weight:700;color:var(--sn-ink)!important;white-space:nowrap;'
    'border:1px solid var(--sn-rule);border-inline-start:3px solid var(--sn-mark)}'
    '.sitenav-menu{flex:1 1 auto;min-width:0}'
    '.sitenav-menu>summary{display:none}'
    '.sitenav-menu::details-content{content-visibility:visible;display:contents}'
    # A browser without ::details-content cannot show a closed disclosure's
    # content, so there the summary stays visible at every width: the menu
    # button is the fallback, and no link is ever unreachable.
    '@supports not selector(::details-content){.sitenav-menu>summary{display:inline-flex}}'
    '.sitenav-groups{display:flex;flex-wrap:wrap;align-items:center;gap:2px 0}'
    '.sitenav-group{display:flex;flex-wrap:wrap;align-items:center;gap:0 1px;min-width:0;'
    'padding-inline:8px;border-inline-start:1px solid var(--sn-rule)}'
    '.sitenav-group:first-child{border-inline-start:0}'
    '.sitenav-g{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.07em;'
    'color:var(--sn-mute);margin-inline-end:3px}'
    '.sitenav ul,.sitenav ol{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;'
    'gap:0 1px}'
    '.sitenav [aria-current="page"]{font-weight:700;color:var(--sn-ink);'
    'background:color-mix(in srgb,currentColor 10%,transparent);'
    'box-shadow:inset 0 -3px 0 var(--sn-mark)}'
    '.sitenav-loop{margin-block-start:6px!important;padding-block-start:6px!important;'
    'border-block-start:1px solid var(--sn-rule);counter-reset:step;align-items:center;'
    'gap:4px 6px!important}'
    '.sitenav-loop li{counter-increment:step;color:var(--sn-mute);display:flex;align-items:center}'
    '.sitenav-loop li::before{content:counter(step);display:inline-grid;place-items:center;'
    'inline-size:1.5em;block-size:1.5em;border-radius:50%;font-size:11px;font-weight:700;'
    'border:1px solid var(--sn-rule);margin-inline-end:2px}'
    '.sitenav-loop a{color:var(--sn-ink)}'
    '.sitenav-loop [aria-current="step"]{font-weight:700;color:var(--sn-ink);'
    'background:color-mix(in srgb,currentColor 10%,transparent);'
    'box-shadow:inset 0 -3px 0 var(--sn-mark)}'
    '@media(max-width:720px){'
    '.sitenav{padding-inline:12px}'
    '.sitenav-row{justify-content:space-between}'
    '.sitenav-menu{flex:0 1 auto}'
    '.sitenav-menu::details-content{display:block;content-visibility:hidden}'
    '.sitenav-menu[open]::details-content{content-visibility:visible}'
    '.sitenav-menu>summary{display:inline-flex;align-items:center;gap:6px;cursor:pointer;'
    'list-style:none;padding-block:5px;padding-inline:10px;border:1px solid var(--sn-rule);'
    'border-radius:6px;font-weight:600;white-space:nowrap}'
    '.sitenav-menu>summary::-webkit-details-marker{display:none}'
    '.sitenav-menu>summary::after{content:"";inline-size:.45em;block-size:.45em;'
    'border-inline-end:2px solid currentColor;border-block-end:2px solid currentColor;'
    'transform:translateY(-2px) rotate(45deg);transition:transform .15s}'
    '.sitenav-menu[open]>summary::after{transform:translateY(2px) rotate(-135deg)}'
    '.sitenav-menu[open]>.sitenav-groups{position:absolute;inset-inline:0;top:100%;'
    'display:grid;gap:0;background:var(--sn-bg);border-block-end:1px solid var(--sn-rule);'
    'box-shadow:0 12px 24px -12px rgba(0,0,0,.45);padding-block:4px 10px;padding-inline:12px}'
    '.sitenav-group{padding-inline:0;padding-block:6px;border-inline-start:0;'
    'border-block-start:1px solid var(--sn-rule)}'
    '.sitenav-group:first-child{border-block-start:0}'
    '.sitenav-g{flex:0 0 100%;margin-block-end:2px}'
    '.sitenav-loop{font-size:12.5px}}'
    '@media (prefers-reduced-motion:reduce){.sitenav *{transition:none!important}}'
)


# The search link and its CSS come from web/sitesearch.py, which itself reads
# PAGES / FRONT_DOOR / labels from here - so it is imported last, once those
# exist. (Import sitenav before sitesearch; every builder does.)
from sitesearch import search_trigger, SEARCH_TRIGGER_CSS  # noqa: E402
NAV_CSS = NAV_CSS + SEARCH_TRIGGER_CSS.strip().replace('\n', '')
