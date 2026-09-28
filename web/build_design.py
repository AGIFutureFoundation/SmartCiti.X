#!/usr/bin/env python3
"""The template gallery: every design-kit template, in dark and light, with
the exact call that renders it.

Each example below is DATA - the arguments handed to the kit function - and
the page prints both the rendered template and that call, formatted from
the same dict. So the snippet a reader copies is the call that drew what
they are looking at, not a second copy that could drift from it.

Figures on the page (templates, icons, clips, seconds of footage) are
counted from design_kit.TEMPLATES, the icon manifest and the b-roll
registry at build time. The hero's video is the first hero clip in
media/registry/media.json; the build stops by name if there is none.
"""
import html
import json
import pathlib
import pprint
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import design_kit as K  # noqa: E402
from sitenav import nav_html, labels as nav_labels, NAV_CSS, STYLE_JS  # noqa: E402
from staleness import emit  # noqa: E402
from seo import apply_seo  # noqa: E402  head tags only
import pagehero as PH  # noqa: E402  the hero band + theme layer (web/pagehero.py)

E = html.escape
PAGE = 'web/trade_craft_design.html'
MEDIA = json.loads((ROOT / 'media' / 'registry' / 'media.json').read_text())
ICONS = json.loads((HERE / 'vendor' / 'icons' / 'manifest.json').read_text())

# Prefer a hero-quality clip. Until one is rendered, the gallery shows the
# first registered clip and SAYS it is not hero quality, naming its issue -
# never passing a flawed clip off as the finished look.
if not MEDIA['clips']:
    raise SystemExit('build_design: media/registry/media.json has no rendered clip - render one first')
heroes = [c for c in MEDIA['clips'] if c['hero']]
H = heroes[0] if heroes else MEDIA['clips'][0]
OTHER = heroes[1] if len(heroes) > 1 else H
H_NOTE = ('' if H['hero'] else
          f" Until a hero-quality clip is rendered this shows {H['id']}, which is NOT hero quality: {H['known_issue']}.")
rel = lambda p: p[len('web/'):] if p.startswith('web/') else '../' + p

EXAMPLES = [
    ('hero', 'Hero with video background',
     'A full-bleed opening band. The video is muted, loops, and sits under a scrim that keeps the '
     'text above AA contrast on every frame; the pause control is a real button, and a reader who '
     'asked for reduced motion gets the poster and never motion.' + H_NOTE,
     {'eyebrow': 'Trade Craft Academy', 'title': 'Walk the campus before you walk the site',
      'lede': 'A 3D training campus, simulator seats and a map of the network - in the browser, '
              'on a phone, offline once loaded.',
      'actions': [{'text': 'Open the campus', 'href': 'trade_craft_3d.html', 'kind': 'primary'},
                  {'text': 'See the map', 'href': 'trade_craft_geomap.html', 'kind': 'ghost'}],
      'video': {'webm': rel(H['files']['webm']['path']), 'mp4': rel(H['files']['mp4']['path']),
                'poster': rel(H['files']['poster']['path']),
                'credit': 'Footage: ' + H['title'] + ' - recorded from this build',
                'pause_label': 'Pause background video', 'play_label': 'Play background video'},
      'as_h1': False}),
    ('feature_grid', 'Feature grid with icons', 'Three to six features, each an icon, a title and one sentence.',
     [{'icon': 'building-2', 'title': 'Campus and halls', 'body': 'Every trade hall stands on the campus green, with rooms you can walk.'},
      {'icon': 'hard-hat', 'title': 'Simulator seats', 'body': 'Practice a lift or a trench in a seat that scores what you did.'},
      {'icon': 'globe', 'title': 'The network on a globe', 'body': 'Every campus and site at its own registry coordinates.'}]),
    ('stat_band', 'Stat band', 'Figures computed by the CALLER from a registry at build time; each names its source.',
     [{'value': len(K.TEMPLATES), 'label': 'templates in this kit', 'source': 'web/design_kit.py TEMPLATES'},
      {'value': len(ICONS['icons']), 'label': 'icons vendored', 'source': 'web/vendor/icons/manifest.json'},
      {'value': len(MEDIA['clips']), 'label': 'b-roll clips', 'source': 'media/registry/media.json'},
      {'value': sum(c['duration_s'] for c in MEDIA['clips']), 'label': 'seconds of footage',
       'source': 'media/registry/media.json'}]),
    ('split', 'Split media section', 'Media on one side, words on the other; stacks on a phone. reverse=True mirrors it.',
     {'media_html': f'<img src="{E(rel(OTHER["files"]["poster"]["path"]))}" alt="{E(OTHER["shows"])}" loading="lazy">',
      'eyebrow': 'Recorded here', 'title': OTHER['title'],
      'body': OTHER['shows'] + '. ' + OTHER['provenance'] + '.',
      'action': {'text': 'Open the 3D campus', 'href': 'trade_craft_3d.html', 'kind': 'ghost'},
      'reverse': False}),
    ('timeline', 'Process timeline', 'Numbered by CSS counters, so the page types no digit.',
     [{'title': 'Pick a trade', 'body': 'Find its hall on the campus.'},
      {'title': 'Learn the room', 'body': 'Walk the stations and read the lessons.'},
      {'title': 'Take the seat', 'body': 'Run the simulator and see what it scored.'},
      {'title': 'Keep the record', 'body': 'Your progress stays on your device.'}]),
    ('cta', 'CTA band', 'One action, one sentence of why.',
     {'title': 'Ready to look around?', 'body': 'The campus opens in the browser; nothing to install.',
      'action': {'text': 'Open the campus', 'href': 'trade_craft_3d.html', 'kind': 'primary'}}),
    ('callout', 'Callout and limit box', "kind='limit' is the box that says what something is NOT.",
     {'kind': 'limit', 'title': 'Play, not a credential',
      'body': 'Quests, badges and treasures are play. They never enter a completion record and certify nothing.'}),
    ('card', 'Card', 'A linked card lifts on hover; without href it is a plain article.',
     {'icon': 'map', 'title': 'Globe map', 'body': 'Every campus at its registry coordinates.',
      'badge': ('Schematic', 'steel'), 'href': 'trade_craft_geomap.html', 'go': 'Open the map'}),
    ('badge', 'Badge', 'Four tones: steel, amber, muted, ok. For provenance words and states.',
     None),
    ('breadcrumb', 'Breadcrumb', 'The last item is the current page (aria-current).',
     None),
    ('footer', 'Footer', 'Columns of links and one note line.',
     [{'title': 'Learn', 'links': [('3D campus', 'trade_craft_3d.html'), ('Lessons', 'trade_craft_lessons.html')]},
      {'title': 'Maps', 'links': [('Globe map', 'trade_craft_geomap.html'), ('Network map', 'trade_craft_map.html')]},
      {'title': 'Records', 'links': [('Progress', 'trade_craft_progress.html'), ('Verify', 'trade_craft_verify.html')]}]),
]
assert [e[0] for e in EXAMPLES] == K.TEMPLATES, 'the gallery must show every template, in order'


def render(name, args):
    if name == 'badge':
        html_ = ' '.join(K.badge(t, tone) for t, tone in
                         [('Recorded', 'ok'), ('Schematic', 'steel'), ('Authored', 'amber'), ('Proposed', 'muted')])
        call = "badge('Recorded', 'ok')  # tones: steel | amber | muted | ok"
        return html_, call
    if name == 'breadcrumb':
        items = [('Home', '../index.html'), ('About', 'trade_craft_landing.html'), ('Design kit', None)]
        return K.breadcrumb(items, 'Breadcrumb'), f'breadcrumb({pprint.pformat(items, width=90)}, "Breadcrumb")'
    if name == 'footer':
        note = 'Footage and templates are first-party; icons are Lucide (ISC).'
        return K.footer(args, note), f'footer({pprint.pformat(args, width=90, sort_dicts=False)},\n       {note!r})'
    fn = getattr(K, name)
    return fn(args), f'{name}({pprint.pformat(args, width=90, sort_dicts=False)})'


sections = []
for name, title, why, args in EXAMPLES:
    out, call = render(name, args)
    sections.append(f'''<section class="g-sec" id="t-{name}" aria-labelledby="h-{name}">
<div class="g-head"><h2 id="h-{name}">{E(title)}</h2><code class="g-fn">design_kit.{name}</code></div>
<p class="g-why">{E(why)}</p>
<div class="g-pair">
<div class="g-frame dk" data-theme="dark"><span class="g-tag">dark</span>{out}</div>
<div class="g-frame dk" data-theme="light"><span class="g-tag">light</span>{out}</div>
</div>
<details class="g-code"><summary>Usage</summary><pre><code>from design_kit import kit_css, KIT_JS, {name}
{E(call)}</code></pre></details>
</section>''')


def swatches(theme):
    p = K.TOKENS['palette'][theme]
    rows = []
    for k, v in p.items():
        rows.append(f'<li><span class="g-sw" style="background:{v}"></span><code>--dk-{k}</code><span>{v}</span></li>')
    ratios = ''.join(
        f'<li><code>{f} on {b}</code><span>{K.contrast(p[f], p[b]):.1f}:1</span></li>'
        for f, b, _m in K.CONTRAST_PAIRS)
    return (f'<div class="g-frame dk" data-theme="{theme}"><span class="g-tag">{theme}</span>'
            f'<ul class="g-swatches">{"".join(rows)}</ul><h3 class="g-sub">Contrast, computed from these values</h3>'
            f'<ul class="g-ratios">{"".join(ratios)}</ul></div>')


scale = ''.join(f'<li style="font-size:{v}"><code>--dk-t-{k}</code> Walk the campus</li>'
                for k, v in K.TOKENS['type'].items())
space = ''.join(f'<li><span class="g-bar" style="inline-size:{v}"></span><code>--dk-s-{k}</code> {v}</li>'
                for k, v in K.TOKENS['space'].items())
elev = ''.join(f'<li style="box-shadow:{v}"><code>--dk-e-{k}</code></li>' for k in K.TOKENS['elevation']
               for v in [K.TOKENS['elevation'][k]])
radii = ''.join(f'<li style="border-radius:{v}"><code>--dk-r-{k}</code></li>' for k, v in K.TOKENS['radius'].items())
icons = ''.join(f'<li>{K.icon(n)}<code>{E(n)}</code></li>' for n in ICONS['icons'])

GCSS = '''
body{margin:0;background:var(--dk-plate);color:var(--dk-ink);font-family:var(--dk-f-body)}
main{max-inline-size:1240px;margin-inline:auto;padding:var(--dk-s-5) var(--dk-s-4) var(--dk-s-9)}
.g-intro h1{font:700 var(--dk-t-4xl)/1.05 var(--dk-f-display);margin:var(--dk-s-4) 0 var(--dk-s-3)}
.g-intro p{color:var(--dk-muted);max-inline-size:70ch}
.g-toc{display:flex;flex-wrap:wrap;gap:var(--dk-s-2);list-style:none;padding:0;margin:var(--dk-s-5) 0}
.g-toc a{display:inline-block;padding:var(--dk-s-1) var(--dk-s-3);border:1px solid var(--dk-line);border-radius:var(--dk-r-pill);text-decoration:none;color:var(--dk-ink);font-size:var(--dk-t-sm)}
.g-sec{margin-block-start:var(--dk-s-8)}
.g-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:var(--dk-s-3);border-block-end:1px solid var(--dk-line);padding-block-end:var(--dk-s-2)}
.g-head h2{font:700 var(--dk-t-2xl)/1.1 var(--dk-f-display);margin:0}
.g-fn{font:var(--dk-t-sm) var(--dk-f-mono);color:var(--dk-steel)}
.g-why{color:var(--dk-muted);max-inline-size:75ch}
.g-pair{display:grid;gap:var(--dk-s-4);grid-template-columns:repeat(auto-fit,minmax(min(100%,520px),1fr))}
.g-frame{position:relative;padding:var(--dk-s-6) var(--dk-s-4) var(--dk-s-4);border:1px solid var(--dk-line);border-radius:var(--dk-r-lg);min-inline-size:0;overflow:hidden}
.g-tag{position:absolute;inset-block-start:var(--dk-s-2);inset-inline-start:var(--dk-s-3);font:600 .7rem/1 var(--dk-f-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--dk-muted)}
.g-code{margin-block-start:var(--dk-s-3)}
.g-code summary{cursor:pointer;color:var(--dk-link);font-weight:600;min-block-size:32px}
.g-code pre{overflow-x:auto;background:var(--dk-panel);border:1px solid var(--dk-line);border-radius:var(--dk-r-md);padding:var(--dk-s-4);font:var(--dk-t-sm)/1.5 var(--dk-f-mono);max-block-size:420px}
.g-swatches,.g-ratios,.g-scale,.g-space,.g-elev,.g-radii,.g-icons{list-style:none;margin:0;padding:0}
.g-swatches{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:var(--dk-s-2)}
.g-swatches li{display:grid;grid-template-columns:28px 1fr;column-gap:var(--dk-s-2);font-size:var(--dk-t-xs);align-items:center}
.g-swatches li span:last-child{grid-column:2;color:var(--dk-muted);font-family:var(--dk-f-mono)}
.g-sw{grid-row:span 2;inline-size:28px;block-size:28px;border-radius:var(--dk-r-sm);border:1px solid var(--dk-line)}
.g-sub{font:600 var(--dk-t-sm)/1 var(--dk-f-body);margin:var(--dk-s-5) 0 var(--dk-s-2)}
.g-ratios{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:var(--dk-s-1) var(--dk-s-3);font-size:var(--dk-t-xs)}
.g-ratios li{display:flex;justify-content:space-between;gap:var(--dk-s-2);border-block-end:1px dotted var(--dk-line)}
.g-scale li{margin-block:var(--dk-s-2);font-family:var(--dk-f-display);overflow-wrap:anywhere}
.g-scale code,.g-space code,.g-elev code,.g-radii code{font:var(--dk-t-xs) var(--dk-f-mono);color:var(--dk-muted);margin-inline-end:var(--dk-s-2)}
.g-space li{display:flex;align-items:center;gap:var(--dk-s-2);margin-block:var(--dk-s-1);font-size:var(--dk-t-xs)}
.g-bar{display:inline-block;block-size:10px;background:var(--dk-amber);border-radius:2px}
.g-elev,.g-radii{display:flex;flex-wrap:wrap;gap:var(--dk-s-5)}
.g-elev li,.g-radii li{inline-size:130px;block-size:72px;display:grid;place-items:center;background:var(--dk-panel);border:1px solid var(--dk-line);border-radius:var(--dk-r-md)}
.g-icons{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:var(--dk-s-3)}
.g-icons li{display:flex;align-items:center;gap:var(--dk-s-2);font:var(--dk-t-xs) var(--dk-f-mono);color:var(--dk-muted)}
.g-icons .dk-icon{color:var(--dk-steel);inline-size:24px;block-size:24px}
.g-tokens{display:grid;gap:var(--dk-s-4);grid-template-columns:repeat(auto-fit,minmax(min(100%,520px),1fr))}
'''

# ---------------------------------------------------------------- wave 3
# The page opens on the pagehero band itself (its title is the page's h1),
# then shows the band's measured contrast per clip, the theme layer's
# components in both palettes, every registered clip, and which template
# kit each pattern re-expresses.
HERO_CLIP = 'campus-green-low-dolly'
HERO_ARGS = {
    'clip': HERO_CLIP, 'kicker': 'Living style guide',
    'title': 'Studio-grade pages from our own footage', 'accent': 'our own footage',
    'accent_style': 'gradient',
    'lede': 'The hero band, the enterprise theme layer and the b-roll library every document page can use - '
            'each shown here with the call that renders it, and every contrast ratio measured.',
    'actions': [{'text': 'See the hero band', 'href': '#hero-band', 'kind': 'primary'},
                {'text': 'Browse the clips', 'href': '#clips', 'kind': 'ghost'}],
    'as_h1': True, 'labels': {'pause': 'Pause background video', 'play': 'Play background video'},
    'credit': 'Footage: recorded frame by frame from this build (' + HERO_CLIP + ')',
}
HERO_CSS, HERO_HTML, HERO_JS = PH.pagehero(PAGE, HERO_ARGS)
THEME_CSS, THEME_JS = PH.theme('doc')
OUTLINE_CSS, OUTLINE_HTML, _ = PH.pagehero(PAGE, {**HERO_ARGS, 'clip': 'hall-orbit', 'as_h1': False,
                                                  'kicker': 'accent_style outline', 'title': 'Walk the hall',
                                                  'accent': 'hall', 'accent_style': 'outline',
                                                  'lede': 'The same band on another clip, outlined accent word.',
                                                  'actions': [],
                                                  'credit': 'Footage: recorded from this build (hall-orbit)'})


def call_of(args):
    return 'head_css, hero_html, js = pagehero(PAGE, ' + pprint.pformat(args, width=100, sort_dicts=False) + ')'


rows = []
for cid in PH.clip_ids():
    m = PH.measure(cid)
    cells = ''.join(f'<td>{m["ratios"][k]:.2f}</td>' for k in PH.HERO_TEXT)
    rows.append(f'<tr data-clip="{E(cid)}"><th scope="row"><code>{E(cid)}</code></th>'
                f'<td><span class="g-sw g-sw-in" style="background:{PH.CLIPS[cid]["measured"]["brightest_rgb"]}"></span>'
                f'<code>{PH.CLIPS[cid]["measured"]["brightest_rgb"]}</code></td>'
                f'<td><span class="g-sw g-sw-in" style="background:{m["under"]}"></span><code>{m["under"]}</code></td>'
                f'{cells}<td><strong>{m["min"]:.2f}</strong></td></tr>')
contrast_table = (f'<div class="g-scroll"><table class="tc-table g-ctable"><caption>Scrim contrast per clip: '
                  f'the brightest colour measured over every frame, the scrim ({PH.SCRIM_TEXT_ALPHA} plate) '
                  f'composited over it, and every hero text colour on the result (minimum {PH.MIN_RATIO}:1)</caption>'
                  f'<thead><tr><th scope="col">clip</th><th scope="col">brightest</th><th scope="col">under text</th>'
                  + ''.join(f'<th scope="col">{E(k)}</th>' for k in PH.HERO_TEXT)
                  + f'<th scope="col">min</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')

hero_sec = f'''<section class="g-sec" id="hero-band" aria-labelledby="h-hero-band">
<div class="g-head"><h2 id="h-hero-band">Page hero band</h2><code class="g-fn">pagehero.pagehero</code></div>
<p class="g-why">The band at the top of this page. Poster first (fixed band height, no layout shift); the muted loop
starts only without reduced motion and without Save-Data, a phone gets the 480 px preview, and a pause/play button
appears once anything moves. Unknown clip ids stop the build. Below: the same band with an outlined accent word.</p>
<div class="g-demo">{OUTLINE_HTML}</div>
{contrast_table}
<details class="g-code"><summary>Usage</summary><pre><code>from pagehero import pagehero, theme
{E(call_of(HERO_ARGS))}</code></pre></details>
</section>'''

theme_demo = (
    '<div class="tc-grid">'
    '<a class="tc-card" href="trade_craft_3d.html" data-tc-reveal><span class="tc-kicker">Card</span>'
    '<strong>Linked card</strong><p>Lifts on hover; focus ring on keyboard focus.</p></a>'
    '<div class="tc-stat" data-tc-reveal><span class="tc-stat-v">' + str(len(PH.clip_ids())) + '</span>'
    '<span class="tc-stat-l">clips registered (media/registry/media.json)</span></div>'
    '<div class="tc-panel g-pad" data-tc-reveal><span class="tc-kicker">Panel</span><p>Glass where the browser can blur, '
    'solid otherwise - the canvas pages take this one.</p></div></div>'
    '<p class="g-row"><a class="tc-btn tc-btn-primary" href="#clips">Primary</a> '
    '<a class="tc-btn tc-btn-ghost" href="#patterns">Ghost</a> '
    '<span class="tc-badge tc-badge-ok">Recorded</span> <span class="tc-badge tc-badge-info">Schematic</span> '
    '<span class="tc-badge tc-badge-warn">Authored</span> <span class="tc-badge tc-badge-muted">Proposed</span></p>'
    '<div class="g-scroll"><table class="tc-table"><thead><tr><th scope="col">Component</th><th scope="col">Class</th>'
    '<th scope="col">Pages</th></tr></thead><tbody>'
    '<tr><td>Card</td><td><code>.tc-card</code></td><td>document</td></tr>'
    '<tr><td>Panel, button, badge</td><td><code>.tc-panel .tc-btn .tc-badge</code></td><td>document and canvas</td></tr>'
    '<tr><td>Table</td><td><code>.tc-table</code></td><td>document</td></tr></tbody></table></div>')
theme_sec = f'''<section class="g-sec" id="theme" aria-labelledby="h-theme">
<div class="g-head"><h2 id="h-theme">Enterprise theme layer</h2><code class="g-fn">pagehero.theme</code></div>
<p class="g-why">Opt in with <code>&lt;body class="tc-theme"&gt;</code> (document pages: page background, sticky
glass nav, components, scroll reveal) or <code>tc-theme-canvas</code> (3D, wilds, globe: panel, button, badge and
focus styling only). Tokens are design_kit.TOKENS; blocks fade in on scroll unless the reader asked for reduced motion.</p>
<div class="g-pair">
<div class="g-frame" data-theme="dark"><span class="g-tag">dark</span>{theme_demo}</div>
<div class="g-frame" data-theme="light"><span class="g-tag">light</span>{theme_demo}</div>
</div>
<details class="g-code"><summary>Usage</summary><pre><code>from pagehero import theme
theme_css, theme_js = theme('doc')      # &lt;body class="tc-theme"&gt;
theme_css, theme_js = theme('canvas')   # &lt;body class="tc-theme-canvas"&gt;</code></pre></details>
</section>'''

clip_cards = []
for c in MEDIA['clips']:
    f = c['files']
    issue = (f'<p class="g-issue"><strong>Known issue:</strong> {E(c["known_issue"])}</p>'
             if c['known_issue'] else '')
    clip_cards.append(
        f'<article class="tc-card g-clip" data-clip="{E(c["id"])}" data-tc-reveal>'
        f'<video controls muted loop playsinline preload="none" poster="{E(rel(f["poster"]["path"]))}" '
        f'width="480" height="270" aria-label="{E(c["title"])}"><source src="{E(rel(f["preview"]["path"]))}" type="video/webm">'
        f'</video><div class="g-clip-b"><code>{E(c["id"])}</code> '
        + (PH.K.badge('hero', 'ok') if c['hero'] else PH.K.badge('not hero', 'muted'))
        + f'<strong>{E(c["title"])}</strong><p>{E(c["shows"])}.</p>'
        f'<p class="g-meta">{c["duration_s"]} s, {c["fps"]} fps, {c["resolution"][0]}x{c["resolution"][1]}; '
        f'webm {f["webm"]["bytes"]:,} B, mp4 {f["mp4"]["bytes"]:,} B; scrim min {PH.measure(c["id"])["min"]:.2f}:1</p>'
        f'<p class="g-meta">{E(c["provenance"])}; {E(c["status"])}</p>{issue}</div></article>')
pend = ''.join(f'<li><code>{E(p["id"])}</code> - {E(p["why"])}</li>' for p in MEDIA['pending'])
clips_sec = f'''<section class="g-sec" id="clips" aria-labelledby="h-clips">
<div class="g-head"><h2 id="h-clips">B-roll library</h2><code class="g-fn">media/registry/media.json</code></div>
<p class="g-why">Every registered clip, first-party: filmed frame by frame from this build's own pages, graded and
encoded here; no stock. Each plays its 480 px preview on request (nothing autoplays in this gallery).</p>
<div class="tc-grid g-clips">{''.join(clip_cards)}</div>
{f'<h3 class="g-sub">Not rendered yet</h3><ul class="g-pending">{pend}</ul>' if pend else ''}
</section>'''

pat_rows = ''.join(f'<tr><td>{E(p["pattern"])}</td><td>{E(p["kit"])}</td><td>{E(p["license"])}</td></tr>'
                   for p in PH.PATTERNS)
patterns_sec = f'''<section class="g-sec" id="patterns" aria-labelledby="h-patterns">
<div class="g-head"><h2 id="h-patterns">Where the patterns come from</h2><code class="g-fn">pagehero.PATTERNS</code></div>
<p class="g-why">Layout, spacing and type-scale patterns re-expressed with our own tokens from open template kits.
No kit stylesheet, script, image or sample copy is copied into this build.</p>
<div class="g-scroll"><table class="tc-table g-ptable"><thead><tr><th scope="col">Pattern</th><th scope="col">Template kit</th>
<th scope="col">Licence</th></tr></thead><tbody>{pat_rows}</tbody></table></div>
</section>'''

# the five site styles, side by side: each preview block takes its style's
# tokens through [data-style-preview], and lists its measured ratios
_L = nav_labels('en')
style_cards = []
for st in K.STYLES:
    r = K.style_ratios(st)
    rows_ = ''.join(f'<li><code>{E(k)}</code><span>{v:.2f}:1</span></li>' for k, (v, _m) in r.items())
    style_cards.append(
        f'<article class="g-style" data-style-preview="{st["id"]}" data-style-min="{min(v for v, _m in r.values()):.2f}">'
        f'<div class="g-style-hero"><p class="ph-kicker">{E(st["id"])}</p><p class="g-style-t">{E(_L[st["label_key"]])}</p></div>'
        f'<div class="g-style-b"><p class="g-style-kit">{E(st["kit"])}</p>'
        f'<p><a class="tc-btn tc-btn-primary" href="#styles">Primary</a> <span class="tc-badge tc-badge-info">Schematic</span></p>'
        f'<p class="g-style-m">Muted text on the panel, links <a href="#styles">look like this</a>.</p>'
        f'<details class="g-code"><summary>Measured contrast</summary><ul class="g-ratios">{rows_}</ul></details></div></article>')
styles_sec = f'''<section class="g-sec" id="styles" aria-labelledby="h-styles">
<div class="g-head"><h2 id="h-styles">Five site styles</h2><code class="g-fn">design_kit.STYLES</code></div>
<p class="g-why">The Style menu in the site header switches every page between these five. Each is a full token set -
surfaces, text, accent, links, radii, shadow, display face and the hero scrim - and every pair below is measured with
design_kit.contrast when the page is built; a style that falls under its minimum stops the build by name. The hero
text is measured over each style's scrim composited on pure white, the worst frame any clip can show.</p>
<div class="g-styles">{''.join(style_cards)}</div>
<details class="g-code"><summary>Usage</summary><pre><code>&lt;html data-style="blueprint"&gt;   # set by the nav's Style menu; stored under localStorage '{K.STYLE_KEY}'
from design_kit import STYLES, STYLE_HEAD_JS, style_css
from sitenav import STYLE_JS          # page script: remembers the reader's choice</code></pre></details>
</section>'''

GCSS += '''
.g-demo{margin-block:var(--dk-s-4);border-radius:var(--dk-r-lg);overflow:hidden}
.g-demo .ph{min-block-size:320px}
.g-scroll{overflow-x:auto;margin-block:var(--dk-s-4)}
.g-ctable caption{caption-side:top;text-align:start;padding:var(--dk-s-3) var(--dk-s-4);color:var(--tc-muted);font-size:var(--dk-t-sm)}
.g-ctable td,.g-ctable th{white-space:nowrap}
.g-sw-in{display:inline-block;vertical-align:middle;margin-inline-end:6px;inline-size:16px;block-size:16px}
.g-frame .tc-grid{margin-block-end:var(--dk-s-4)}
.g-frame[data-theme]{background:var(--tc-plate);color:var(--tc-ink)}
.g-pad p{margin:var(--dk-s-2) 0 0}
.g-row{display:flex;flex-wrap:wrap;align-items:center;gap:var(--dk-s-2)}
.g-clip{padding:0;overflow:hidden}
.g-clip video{display:block;inline-size:100%;block-size:auto;aspect-ratio:16/9;background:#000}
.g-clip-b{padding:var(--dk-s-4);display:flex;flex-direction:column;gap:var(--dk-s-2)}
.g-meta{font:var(--dk-t-xs)/1.4 var(--dk-f-mono)}
.g-issue{font-size:var(--dk-t-sm)}
.g-pending{color:var(--dk-muted);font-size:var(--dk-t-sm)}
.g-styles{display:grid;gap:var(--dk-s-4);grid-template-columns:repeat(auto-fit,minmax(min(100%,210px),1fr))}
.g-style{background:var(--tc-panel);color:var(--tc-ink);border:1px solid var(--tc-line);border-radius:var(--tc-r-lg);overflow:hidden;box-shadow:var(--tc-e-2);font-family:var(--dk-f-body)}
.g-style-hero{padding:var(--dk-s-5) var(--dk-s-4);background:linear-gradient(90deg,rgb(0 0 0 / .0),rgb(0 0 0 / .0)),var(--st-scrim);color:#F4F7F6}
.g-style-hero .ph-kicker{margin:0 0 6px}
.g-style-t{margin:0;font:700 1.9rem/1 var(--dk-f-display);color:#F4F7F6}
.g-style-b{padding:var(--dk-s-4);background:var(--tc-plate)}
.g-style-kit{font:var(--dk-t-xs)/1.4 var(--dk-f-mono);color:var(--tc-muted)}
.g-style-m{color:var(--tc-muted);font-size:var(--dk-t-sm)}
.g-style a:not(.tc-btn){color:var(--tc-link)}
'''

NAV = nav_html(PAGE, nav_labels('en'))
page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Design kit - Trade Craft Academy</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' stroke='%23E8A33D' stroke-width='2.6' stroke-linejoin='round'/%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E">
<link rel="stylesheet" href="vendor/fonts/fonts.css">
<script>{K.STYLE_HEAD_JS}</script>
<style>{NAV_CSS}</style>
<style>{K.kit_css()}{GCSS}</style>
<style>{THEME_CSS}{HERO_CSS}</style>
</head>
<body class="dk tc-theme">
{NAV}{HERO_HTML}<main id="main">
<header class="g-intro">
<p class="dk-eyebrow">web/design_kit.py</p>
<p>Tokens and templates any page builder can import. Every template below is shown in the dark and the light
palette with the exact call that drew it. Footage is house-made: recorded frame by frame from this build's own
3D campus (see media/registry/media.json). Icons are Lucide, vendored under the ISC licence.</p>
<ul class="g-toc">{''.join(f'<li><a href="#t-{n}">{E(t)}</a></li>' for n, t, _w, _a in EXAMPLES)}<li><a href="#tokens">Tokens</a></li><li><a href="#styles">Five styles</a></li><li><a href="#hero-band">Hero band</a></li><li><a href="#theme">Theme layer</a></li><li><a href="#clips">Clips</a></li><li><a href="#patterns">Kit patterns</a></li></ul>
</header>
{styles_sec}{hero_sec}{theme_sec}{clips_sec}{patterns_sec}
{''.join(sections)}
<section class="g-sec" id="tokens" aria-labelledby="h-tokens">
<div class="g-head"><h2 id="h-tokens">Tokens</h2><code class="g-fn">design_kit.TOKENS</code></div>
<p class="g-why">Colour, type, spacing, radii and elevation, as custom properties. Contrast ratios are computed from the values at build time.</p>
<div class="g-tokens">{swatches('dark')}{swatches('light')}</div>
<h3 class="g-sub">Type scale</h3><ul class="g-scale">{scale}</ul>
<h3 class="g-sub">Spacing</h3><ul class="g-space">{space}</ul>
<h3 class="g-sub">Radii</h3><ul class="g-radii">{radii}</ul>
<h3 class="g-sub">Elevation</h3><ul class="g-elev">{elev}</ul>
<h3 class="g-sub">Icons</h3><ul class="g-icons">{icons}</ul>
</section>
</main>
<script>{K.KIT_JS}</script>
<script>{HERO_JS}</script>
<script>{THEME_JS}</script>
<script>{STYLE_JS}</script>
</body>
</html>
'''
page = apply_seo(page, 'web/trade_craft_design.html', 'Design kit - Trade Craft Academy',
                 "The design kit's tokens and templates, in dark and light, each with the call that renders it.", 'page')
emit(HERE / 'trade_craft_design.html', page)
