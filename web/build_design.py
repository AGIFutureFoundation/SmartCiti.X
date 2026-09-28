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
from sitenav import nav_html, labels as nav_labels, NAV_CSS  # noqa: E402
from staleness import emit  # noqa: E402

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

NAV = nav_html(PAGE, nav_labels('en'))
page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Design kit - Trade Craft Academy</title>
<meta name="description" content="The design kit's tokens and templates, in dark and light, each with the call that renders it.">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' stroke='%23E8A33D' stroke-width='2.6' stroke-linejoin='round'/%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E">
<link rel="stylesheet" href="vendor/fonts/fonts.css">
<style>{NAV_CSS}</style>
<style>{K.kit_css()}{GCSS}</style>
</head>
<body class="dk">
{NAV}<main>
<header class="g-intro">
<p class="dk-eyebrow">web/design_kit.py</p>
<h1>Design kit</h1>
<p>Tokens and templates any page builder can import. Every template below is shown in the dark and the light
palette with the exact call that drew it. Footage is house-made: recorded frame by frame from this build's own
3D campus (see media/registry/media.json). Icons are Lucide, vendored under the ISC licence.</p>
<ul class="g-toc">{''.join(f'<li><a href="#t-{n}">{E(t)}</a></li>' for n, t, _w, _a in EXAMPLES)}<li><a href="#tokens">Tokens</a></li></ul>
</header>
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
</body>
</html>
'''
emit(HERE / 'trade_craft_design.html', page)
