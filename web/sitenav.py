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
        ('web/trade_craft_classroom.html', 'nav.page.classroom'),
    ]),
    ('nav.group.play', [
        ('web/trade_craft_quests.html', 'nav.page.quests'),
        ('web/trade_craft_wilds.html', 'nav.page.wilds'),
        ('web/trade_craft_parishes.html', 'nav.page.parishes'),
        ('web/trade_craft_bay.html', 'nav.page.bay'),
        ('web/trade_craft_smiles.html', 'nav.page.smiles'),
        ('web/trade_craft_fleet.html', 'nav.page.fleet'),
        ('web/trade_craft_packs.html', 'nav.page.packs'),
    ]),
    # Robotics (wave 11): the robot training lab and the page where a learner saves, analyses and (opt-in)
    # shares their own episode data - the contribute page, named for what it now does
    ('nav.group.robotics', [
        ('web/trade_craft_robotics.html', 'nav.page.robotics'),
        ('web/trade_craft_contribute.html', 'nav.page.sharedata'),
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
        ('web/trade_craft_plans.html', 'nav.page.plans'),
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

# the five site styles (web/design_kit.py STYLES) the nav's Style menu offers
from design_kit import STYLES, STYLE_KEY, STYLE_HEAD_JS, style_css  # noqa: E402
STYLE_KEYS = ['nav.style', 'nav.style.default'] + [st['label_key'] for st in STYLES]

KEYS = (['nav.site', 'nav.loop', 'nav.home', 'nav.group.home', 'nav.skip', 'nav.search'] + STYLE_KEYS
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
    out.append(style_menu(labels))
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


def style_menu(labels):
    """The Style menu: a native disclosure (the summary is the button) holding
    a labelled radio group - arrow keys move between the five styles, and
    screen readers hear the group's legend and each style's name. The
    summary shows the current choice (CSS :has picks which name shows). No
    script is needed to switch (style_css applies on :checked); STYLE_JS,
    when a page includes it, remembers the choice in localStorage."""
    E = lambda k: html.escape(labels[k])
    cur = ''.join(f'<span class="sn-cur" data-s="{st["id"]}">{E(st["label_key"])}</span>' for st in STYLES)
    opts = ''.join(f'<label class="sn-opt"><input type="radio" name="{STYLE_KEY}" value="{st["id"]}">'
                   f'<span class="sn-sw" data-s="{st["id"]}" aria-hidden="true"></span>{E(st["label_key"])}</label>'
                   for st in STYLES)
    return (f'<details class="sitenav-style" data-sitenav-style><summary><span class="sn-lbl">{E("nav.style")}</span>'
            f'<span class="sn-cur sn-cur-default">{E("nav.style.default")}</span>{cur}</summary>'
            f'<fieldset class="sn-styles"><legend>{E("nav.style")}</legend>{opts}</fieldset></details>')


# The page script that remembers the style (optional; after the page's own
# scripts): checks the stored style's radio, and on every change sets
# <html data-style> and stores it. Storage may throw (private mode,
# blocked): every access is in try/catch and the page keeps its default.
STYLE_JS = ("(()=>{var K='" + STYLE_KEY + "',h=document.documentElement,v=h.getAttribute('data-style');"
            "if(!v){try{v=localStorage.getItem(K)}catch(e){v=null}}"
            "var r=v&&document.querySelector('input[name=\"'+K+'\"][value=\"'+v+'\"]');"
            "if(r){r.checked=true;h.setAttribute('data-style',v)}"
            "document.addEventListener('change',function(e){var t=e.target;if(!t||t.name!==K)return;"
            "h.setAttribute('data-style',t.value);try{localStorage.setItem(K,t.value)}catch(e){}});})();")



def with_style_memory(page_html, remember=True):
    """Make a finished page follow the reader's saved style (AUDIT row 12):
    STYLE_HEAD_JS (design_kit) as <script id="style-head-js"> right before
    the first <style> in <head>, so the stored style applies before first
    paint, and - when `remember` - STYLE_JS as <script id="style-js"> right
    before </body>, which checks the stored style's radio and stores a new
    choice. remember=False is for a page whose suite allows exactly one
    storage write of its own (sign in): the saved style still applies there,
    a choice made on that page lasts for the visit only. Both scripts carry
    an id, so page suites that read the first bare <script> are unaffected.
    Each anchor must occur as stated, or the build stops by name."""
    assert 'id="style-head-js"' not in page_html and 'id="style-js"' not in page_html, \
        'sitenav.with_style_memory: the page already carries a style script'
    # a page may leave </head> (and </body>) implied, as HTML allows: then the
    # head region ends at <body
    n_head = page_html.count('</head>')
    assert n_head <= 1, 'sitenav.with_style_memory: more than one </head>'
    head_end = (page_html.find('</head>') if n_head else page_html.find('<body') if '<body' in page_html
                else page_html.find('<nav class="sitenav"'))
    assert head_end > 0, 'sitenav.with_style_memory: no </head>, no <body and no site nav'
    first_style = page_html.find('<style', 0, head_end)
    assert first_style > 0, 'sitenav.with_style_memory: no <style> in <head>'
    page_html = (page_html[:first_style] + f'<script id="style-head-js">{STYLE_HEAD_JS}</script>\n'
                 + page_html[first_style:])
    if remember:
        end = '</body>' if '</body>' in page_html else '</html>' if '</html>' in page_html else None
        assert end is None or page_html.count(end) == 1, f'sitenav.with_style_memory: more than one {end}'
        at = page_html.rfind(end) if end else len(page_html)
        page_html = page_html[:at] + f'<script id="style-js">{STYLE_JS}</script>\n' + page_html[at:]
    return page_html


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
    '.sitenav-loop{font-size:12.5px}'
    # AUDIT row 9: every nav control is a 44 px tap target on a phone (WCAG 2.5.5 comfort size)
    '.sitenav a:not(.skip),.sitenav-menu>summary{min-block-size:44px;display:inline-flex;align-items:center}}'
    '@media (prefers-reduced-motion:reduce){.sitenav *{transition:none!important}}'
)


# ------------------------------------------------------------ premium layer
# Glass header (blur where the browser supports backdrop-filter; the solid
# panel above stays as the fallback), a gradient hairline, a tinted pill with
# an accent bar for the current page, and one vendored Lucide icon per group,
# on the home link and on the search link - drawn as CSS masks in
# currentColor, so the markup (and every page suite that reads it) is
# untouched and the icons take each page's own ink. The icons come from
# web/vendor/icons/ (lucide-static, ISC; media/fetch_icons.py verifies them);
# a group without an icon, or an icon not vendored, stops the build by name.
# A page that opts into the theme layer (<body class="tc-theme">, see
# web/pagehero.py) also gets a sticky header.
GROUP_ICONS = {
    'nav.group.learn': 'graduation-cap', 'nav.group.play': 'gamepad-2', 'nav.group.robotics': 'wrench',
    'nav.group.maps': 'map', 'nav.group.records': 'clipboard-check',
    'nav.group.sites': 'hard-hat', 'nav.group.about': 'info',
}
HOME_ICON, SEARCH_ICON = 'house', 'search'


def _icon_mask(name):
    import re
    import urllib.parse
    icon_dir = ROOT / 'web' / 'vendor' / 'icons'
    vendored = json.loads((icon_dir / 'manifest.json').read_text(encoding='utf-8'))['icons']
    assert name in vendored, f'sitenav: icon {name!r} is not vendored (media/fetch_icons.py ICONS)'
    svg = (icon_dir / f'{name}.svg').read_text(encoding='utf-8')
    svg = re.sub(r'<!--.*?-->', '', svg, flags=re.S)
    svg = re.sub(r'\s*class="[^"]*"', '', svg)
    svg = re.sub(r'\s+', ' ', svg).replace('> <', '><').replace(' />', '/>').strip()
    svg = svg.replace('currentColor', 'black').replace('"', "'")
    return 'url("data:image/svg+xml,' + urllib.parse.quote(svg, safe="/:=' ,.-") + '")'


assert set(GROUP_ICONS) == {g for g, _ in GROUPS}, \
    f'sitenav: GROUP_ICONS must name exactly the nav groups, differs by {set(GROUP_ICONS) ^ {g for g, _ in GROUPS}}'

_ICO = ('content:"";display:inline-block;flex:none;inline-size:1.05em;block-size:1.05em;'
        'background:currentColor;-webkit-mask:var(--sn-i) center/contain no-repeat;'
        'mask:var(--sn-i) center/contain no-repeat;opacity:.85')
NAV_CSS += (
    # The bar stays the page's SOLID panel: an earlier translucent glass mix
    # serialised as color(srgb ...) and contrast tools read it as black (HOMEUX
    # measured 1.00:1 in light). Depth comes from the hairline and, when
    # sticky, a shadow - so nav text contrast is exactly the page's ink/panel.
    'body.tc-theme>.sitenav{box-shadow:0 6px 18px -12px rgba(0,0,0,.55)}'
    '.sitenav::after{content:"";position:absolute;inset-inline:0;inset-block-end:-1px;block-size:1px;'
    'pointer-events:none;background:linear-gradient(90deg,transparent,var(--sn-mark),transparent);opacity:.6}'
    '.sitenav a{transition:background-color .15s,color .15s}'
    '.sitenav-g{display:inline-flex;align-items:center;gap:5px}'
    '.sitenav-g::before,.sitenav-home::before,.sitenav .ss-go::before{' + _ICO + '}'
    '.sitenav a.sitenav-home{display:inline-flex;align-items:center;gap:6px}'
    '.sitenav-home::before{--sn-i:' + _icon_mask(HOME_ICON) + '}'
    '.sitenav .ss-go>svg{display:none}'
    '.sitenav .ss-go{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--sn-rule);border-radius:999px;padding-inline:12px}'
    '.sitenav .ss-go::before{--sn-i:' + _icon_mask(SEARCH_ICON) + '}'
    '.sitenav [aria-current="page"]{background:transparent;box-shadow:inset 0 -3px 0 var(--sn-mark),'
    'inset 0 0 0 1px var(--sn-rule)}'
    '.sitenav-loop [aria-current="step"]{background:transparent}'
    + ''.join(f'.sitenav-group:nth-child({i + 1}) .sitenav-g::before{{--sn-i:{_icon_mask(GROUP_ICONS[g])}}}'
              for i, (g, _) in enumerate(GROUPS))
    + 'body.tc-theme>.sitenav{position:sticky;inset-block-start:0}'
    'html:has(body.tc-theme){scroll-padding-block-start:72px}'
    '@media (forced-colors:active){.sitenav-g::before,.sitenav-home::before,.sitenav .ss-go::before{display:none}'
    '.sitenav .ss-go>svg{display:inline}}'
    '@media (prefers-reduced-motion:reduce){.sitenav a{transition:none}}'
)


_SW = ''.join(f'.sn-sw[data-s="{st["id"]}"]{{background:linear-gradient(135deg,{st["tokens"]["plate"]} 50%,'
              f'{st["tokens"]["accent"]} 50%)}}' for st in STYLES)
NAV_CSS += (
    '.sitenav-style{position:relative;flex:none}'
    '.sitenav-style>summary{display:inline-flex;align-items:center;gap:6px;min-block-size:44px;padding-inline:10px;'
    'cursor:pointer;list-style:none;border-radius:999px;white-space:nowrap}'
    '.sitenav-style>summary::-webkit-details-marker{display:none}'
    '.sitenav-style>summary:hover{background:color-mix(in srgb,currentColor 11%,transparent)}'
    '.sitenav-style>summary:focus-visible{outline:2px solid var(--sn-mark);outline-offset:2px}'
    '.sitenav-style .sn-lbl{color:var(--sn-mute)}'
    '.sitenav-style .sn-cur{display:none;font-weight:700}'
    '.sitenav-style:not(:has(input:checked)) .sn-cur-default{display:inline}'
    + ''.join(f'.sitenav-style:has(input[value="{st["id"]}"]:checked) .sn-cur[data-s="{st["id"]}"]{{display:inline}}'
              for st in STYLES)
    + '.sn-styles{position:absolute;inset-inline-end:0;inset-block-start:calc(100% + 6px);z-index:70;margin:0;'
    'min-inline-size:220px;padding-block:8px;padding-inline:8px;display:grid;gap:2px;background:var(--sn-bg);'
    'color:var(--sn-ink);border:1px solid var(--sn-rule);border-radius:10px;box-shadow:0 16px 32px -12px rgba(0,0,0,.45)}'
    '.sn-styles legend{padding-block:2px 6px;padding-inline:6px;font-size:11px;'
    'font-weight:600;text-transform:uppercase;letter-spacing:.07em;color:var(--sn-mute)}'
    '.sn-opt{display:flex;align-items:center;gap:8px;min-block-size:40px;padding-inline:6px;border-radius:6px;cursor:pointer}'
    '.sn-opt:hover{background:color-mix(in srgb,currentColor 10%,transparent)}'
    '.sn-opt:has(input:checked){box-shadow:inset 3px 0 0 var(--sn-mark);font-weight:700}'
    '.sn-opt input{accent-color:var(--sn-mark);margin:0}'
    '.sn-opt input:focus-visible{outline:2px solid var(--sn-mark);outline-offset:2px}'
    '.sn-sw{inline-size:18px;block-size:18px;border-radius:50%;border:1px solid var(--sn-rule);flex:none}'
    + _SW
    + '.sitenav-style>summary::before{' + _ICO + ';--sn-i:' + _icon_mask('layers') + '}'
    # on a phone the bar keeps its four controls on one row: the style name and
    # the search word stay in the accessibility tree but are visually hidden
    + '@media(max-width:720px){.sitenav-style .sn-lbl{display:none}'
    '.sitenav-style .sn-cur,.sitenav .ss-go>span{position:absolute;inline-size:1px;block-size:1px;overflow:hidden;'
    'clip-path:inset(50%);white-space:nowrap}.sitenav .ss-go,.sitenav-style>summary{padding-inline:12px}}'
    + style_css().replace('\n', '')
)


# The search link and its CSS come from web/sitesearch.py, which itself reads
# PAGES / FRONT_DOOR / labels from here - so it is imported last, once those
# exist. (Import sitenav before sitesearch; every builder does.)
from sitesearch import search_trigger, SEARCH_TRIGGER_CSS  # noqa: E402
NAV_CSS = NAV_CSS + SEARCH_TRIGGER_CSS.strip().replace('\n', '')
