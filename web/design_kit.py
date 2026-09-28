"""The design kit: tokens and HTML/CSS templates any page builder can import.

    from design_kit import kit_css, KIT_JS, hero, feature_grid, ...

Everything here is presentation. A template takes its words and figures as
arguments and prints them escaped; it never invents one. Figures a page
shows come from that page's registries, exactly as before.

TOKENS     type scale, spacing, radii, elevation, and the two palettes. The
           dark palette is the brand's own (plate, panel, ink, muted, amber,
           steel); the light palette is its accessible counterpart, every
           text/background pair of which web/test_design.mjs holds to WCAG
           AA by computing the contrast ratio from these very values.
kit_css()  the stylesheet: the tokens as custom properties (dark by
           default, light under prefers-color-scheme or data-theme="light",
           forced either way by data-theme on any ancestor), then every
           template's rules. All selectors are prefixed `dk-`, all
           properties logical, so it mirrors under dir="rtl" and cannot
           collide with a page's own classes.
KIT_JS     the only script the kit needs: the hero video's pause control.
           A reader who asked for reduced motion gets the poster, never
           motion, and the control is a real <button> with a pressed state.
icon()     inlines one vendored Lucide SVG (web/vendor/icons/, ISC). Only
           the icons media/fetch_icons.py took exist; any other name fails
           the build by name.
TEMPLATES  every template's name, in gallery order - the gallery and its
           test both walk this, so a template cannot be added unseen.
"""
import html
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ICON_DIR = HERE / 'vendor' / 'icons'
_ICON_MANIFEST = json.loads((ICON_DIR / 'manifest.json').read_text(encoding='utf-8'))

E = html.escape

TOKENS = {
    'font': {
        'display': "'Barlow Condensed', 'Archivo', system-ui, sans-serif",
        'body': "'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif",
        'mono': "'IBM Plex Mono', ui-monospace, 'SFMono-Regular', monospace",
    },
    # a 1.25 modular scale from 16 px, the display end clamped to the viewport
    'type': {
        'xs': '0.8rem', 'sm': '0.9rem', 'md': '1rem', 'lg': '1.25rem',
        'xl': '1.563rem', '2xl': '1.953rem', '3xl': 'clamp(1.953rem, 1.4rem + 2.4vw, 2.441rem)',
        '4xl': 'clamp(2.2rem, 1.3rem + 4vw, 3.815rem)',
    },
    'space': {'1': '4px', '2': '8px', '3': '12px', '4': '16px', '5': '24px',
              '6': '32px', '7': '48px', '8': '64px', '9': '96px'},
    'radius': {'sm': '4px', 'md': '8px', 'lg': '14px', 'pill': '999px'},
    'elevation': {
        '1': '0 1px 2px rgb(0 0 0 / .18), 0 1px 1px rgb(0 0 0 / .12)',
        '2': '0 4px 12px rgb(0 0 0 / .18), 0 2px 4px rgb(0 0 0 / .12)',
        '3': '0 16px 40px rgb(0 0 0 / .28), 0 4px 10px rgb(0 0 0 / .14)',
    },
    'palette': {
        # the brand, as given
        'dark': {
            'plate': '#12181B', 'panel': '#182023', 'raised': '#1F292D', 'line': '#2B383C',
            'ink': '#E8EDEC', 'muted': '#93A3A6', 'amber': '#E8A33D', 'steel': '#41C4D4',
            'amber-ink': '#12181B', 'link': '#41C4D4', 'warn': '#E8A33D', 'ok': '#6FCF97',
        },
        # the accessible light counterpart: amber and steel darkened until
        # they read as TEXT on the light surfaces (test_design computes it)
        'light': {
            'plate': '#F4F6F6', 'panel': '#FFFFFF', 'raised': '#EAEFEF', 'line': '#D3DCDD',
            'ink': '#12181B', 'muted': '#4E5C5F', 'amber': '#8F5500', 'steel': '#0B6B78',
            'amber-ink': '#FFFFFF', 'link': '#0B6B78', 'warn': '#8F5500', 'ok': '#1E7A45',
        },
    },
}

# text/background pairs the kit actually sets, each held to a minimum ratio
CONTRAST_PAIRS = [
    ('ink', 'plate', 7.0), ('ink', 'panel', 7.0), ('ink', 'raised', 4.5),
    ('muted', 'plate', 4.5), ('muted', 'panel', 4.5),
    ('amber', 'plate', 4.5), ('amber', 'panel', 4.5),
    ('steel', 'plate', 4.5), ('steel', 'panel', 4.5), ('link', 'panel', 4.5),
    ('amber-ink', 'amber', 4.5), ('ok', 'panel', 4.5),
]

TEMPLATES = ['hero', 'feature_grid', 'stat_band', 'split', 'timeline', 'cta',
             'callout', 'card', 'badge', 'breadcrumb', 'footer']


def _need(d, keys, what):
    """Fail closed: a template given a record missing a field stops the build."""
    for k in keys:
        if k not in d:
            raise KeyError(f'design_kit.{what}: missing field {k!r}')


def icon(name, cls='dk-icon'):
    """One vendored Lucide icon, inline, decorative (aria-hidden)."""
    if name not in _ICON_MANIFEST['icons']:
        raise KeyError(f'design_kit.icon: {name!r} is not vendored (media/fetch_icons.py ICONS)')
    svg = (ICON_DIR / f'{name}.svg').read_text(encoding='utf-8')
    svg = re.sub(r'<!--.*?-->', '', svg, flags=re.S).strip()
    svg = re.sub(r'\s*\n\s*', ' ', svg)
    svg = svg.replace('class="lucide ', f'class="{cls} lucide ', 1)
    return svg.replace('<svg ', '<svg aria-hidden="true" focusable="false" ', 1)


def _vars(theme):
    p = TOKENS['palette'][theme]
    return ''.join(f'--dk-{k}:{v};' for k, v in p.items())


def kit_css():
    t = TOKENS
    base = ''.join(f'--dk-t-{k}:{v};' for k, v in t['type'].items())
    base += ''.join(f'--dk-s-{k}:{v};' for k, v in t['space'].items())
    base += ''.join(f'--dk-r-{k}:{v};' for k, v in t['radius'].items())
    base += ''.join(f'--dk-e-{k}:{v};' for k, v in t['elevation'].items())
    base += ''.join(f'--dk-f-{k}:{v};' for k, v in t['font'].items())
    dark, light = _vars('dark'), _vars('light')
    return f""":root{{{base}{dark}color-scheme:dark}}
@media (prefers-color-scheme: light){{:root:not([data-theme="dark"]){{{light}color-scheme:light}}}}
[data-theme="dark"]{{{dark}color-scheme:dark}}
[data-theme="light"]{{{light}color-scheme:light}}
.dk{{font-family:var(--dk-f-body);color:var(--dk-ink);background:var(--dk-plate);line-height:1.55;font-size:var(--dk-t-md)}}
.dk *{{box-sizing:border-box}}
/* the site nav (web/sitenav.py) reads --ink/--panel/--line/--muted/--mark; hand it the kit palette so its
   labels sit on the kit panel, and keep .dk a from recolouring nav links (was 2.09:1 in dark) */
body.dk{{--ink:var(--dk-ink);--panel:var(--dk-panel);--line:var(--dk-line);--muted:var(--dk-muted);--mark:var(--dk-amber)}}
.dk .sitenav a{{color:inherit}}
.dk h2,.dk h3{{font-family:var(--dk-f-display);letter-spacing:.01em;line-height:1.1;margin:0 0 var(--dk-s-3)}}
.dk p{{margin:0 0 var(--dk-s-3)}}
.dk a{{color:var(--dk-link)}}
.dk :focus-visible{{outline:3px solid var(--dk-steel);outline-offset:2px;border-radius:var(--dk-r-sm)}}
.dk-icon{{inline-size:1.25em;block-size:1.25em;flex:none;vertical-align:-.2em}}
.dk-wrap{{max-inline-size:1120px;margin-inline:auto;padding-inline:var(--dk-s-4)}}
.dk-eyebrow{{font:600 var(--dk-t-xs)/1 var(--dk-f-mono);letter-spacing:.14em;text-transform:uppercase;color:var(--dk-amber);margin:0 0 var(--dk-s-3)}}
.dk-btn{{display:inline-flex;align-items:center;gap:var(--dk-s-2);padding:var(--dk-s-3) var(--dk-s-5);border-radius:var(--dk-r-md);font:600 var(--dk-t-md)/1.1 var(--dk-f-body);text-decoration:none;border:1px solid transparent;min-block-size:44px;cursor:pointer}}
.dk-btn-primary{{background:var(--dk-amber);color:var(--dk-amber-ink)}}
.dk-btn-primary:hover{{filter:brightness(1.08)}}
.dk-btn-ghost{{background:transparent;color:var(--dk-ink);border-color:var(--dk-line)}}
.dk-btn-ghost:hover{{border-color:var(--dk-steel)}}
.dk .dk-btn-primary{{color:var(--dk-amber-ink)}}
.dk .dk-btn-ghost{{color:var(--dk-ink)}}
/* hero */
.dk-hero{{position:relative;isolation:isolate;overflow:hidden;min-block-size:min(78vh,640px);display:grid;align-items:end;background:var(--dk-panel);border-radius:var(--dk-r-lg)}}
.dk-hero-media,.dk-hero-media video,.dk-hero-media img{{position:absolute;inset:0;inline-size:100%;block-size:100%;object-fit:cover;z-index:-2}}
.dk-hero-scrim{{position:absolute;inset:0;z-index:-1;background:linear-gradient(180deg,rgb(18 24 27 / .15) 0%,rgb(18 24 27 / .55) 55%,rgb(18 24 27 / .92) 100%),linear-gradient(90deg,rgb(18 24 27 / .7),transparent 70%)}}
.dk-hero-body{{padding:var(--dk-s-8) var(--dk-s-6) var(--dk-s-7);max-inline-size:720px;color:#E8EDEC}}
.dk-hero-body .dk-eyebrow{{color:#E8A33D}}
.dk-hero-title{{font:700 var(--dk-t-4xl)/1.02 var(--dk-f-display);margin:0 0 var(--dk-s-4);letter-spacing:.005em}}
.dk-hero-lede{{font-size:var(--dk-t-lg);color:#C9D3D2;max-inline-size:56ch}}
.dk-hero .dk-btn-ghost{{color:#E8EDEC;border-color:rgb(232 237 236 / .45)}}
.dk-actions{{display:flex;flex-wrap:wrap;gap:var(--dk-s-3);margin-block-start:var(--dk-s-5)}}
.dk-hero-pause{{position:absolute;inset-block-start:var(--dk-s-4);inset-inline-end:var(--dk-s-4);display:inline-flex;align-items:center;gap:var(--dk-s-2);padding:var(--dk-s-2) var(--dk-s-3);border-radius:var(--dk-r-pill);background:rgb(18 24 27 / .66);color:#E8EDEC;border:1px solid rgb(232 237 236 / .3);font:500 var(--dk-t-xs)/1 var(--dk-f-body);min-block-size:36px;cursor:pointer}}
.dk-hero-pause .dk-i-play{{display:none}}
.dk-hero-pause[aria-pressed="true"] .dk-i-play{{display:inline}}
.dk-hero-pause[aria-pressed="true"] .dk-i-pause{{display:none}}
.dk-hero-credit{{position:absolute;inset-block-end:var(--dk-s-2);inset-inline-end:var(--dk-s-4);font:500 .7rem/1 var(--dk-f-mono);color:rgb(232 237 236 / .7);letter-spacing:.06em}}
/* feature grid */
.dk-grid{{display:grid;gap:var(--dk-s-4);grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr))}}
.dk-feature{{padding:var(--dk-s-5);background:var(--dk-panel);border:1px solid var(--dk-line);border-radius:var(--dk-r-lg)}}
.dk-feature-icon{{display:inline-grid;place-items:center;inline-size:44px;block-size:44px;border-radius:var(--dk-r-md);background:color-mix(in srgb,var(--dk-steel) 16%,transparent);color:var(--dk-steel);margin-block-end:var(--dk-s-4)}}
.dk-feature h3{{font-size:var(--dk-t-xl)}}
.dk-feature p{{color:var(--dk-muted);margin:0}}
/* stat band */
.dk-stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,180px),1fr));background:var(--dk-panel);border-block:1px solid var(--dk-line)}}
.dk-stat{{padding:var(--dk-s-5) var(--dk-s-5);border-inline-start:1px solid var(--dk-line)}}
.dk-stat:first-child{{border-inline-start:0}}
.dk-stat-v{{font:700 var(--dk-t-3xl)/1 var(--dk-f-display);color:var(--dk-amber);display:block}}
.dk-stat-l{{display:block;margin-block-start:var(--dk-s-2);font-weight:600}}
.dk-stat-src{{display:block;margin-block-start:var(--dk-s-1);font:var(--dk-t-xs)/1.3 var(--dk-f-mono);color:var(--dk-muted)}}
/* split */
.dk-split{{display:grid;gap:var(--dk-s-6);align-items:center;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr))}}
.dk-split-media{{border-radius:var(--dk-r-lg);overflow:hidden;box-shadow:var(--dk-e-2);background:var(--dk-raised);aspect-ratio:16/9}}
.dk-split-media video,.dk-split-media img{{inline-size:100%;block-size:100%;object-fit:cover;display:block}}
.dk-split-rev .dk-split-media{{order:2}}
.dk-split h2{{font-size:var(--dk-t-2xl)}}
.dk-split p{{color:var(--dk-muted)}}
/* timeline */
.dk-steps{{list-style:none;margin:0;padding:0;counter-reset:dk-step;display:grid;gap:var(--dk-s-4)}}
.dk-step{{position:relative;padding-inline-start:var(--dk-s-8);counter-increment:dk-step}}
.dk-step::before{{content:counter(dk-step);position:absolute;inset-inline-start:0;inset-block-start:0;inline-size:40px;block-size:40px;border-radius:50%;display:grid;place-items:center;font:700 var(--dk-t-lg)/1 var(--dk-f-display);background:var(--dk-raised);color:var(--dk-amber);border:2px solid var(--dk-amber)}}
.dk-step:not(:last-child)::after{{content:"";position:absolute;inset-inline-start:19px;inset-block-start:44px;inset-block-end:calc(-1 * var(--dk-s-4) + 4px);border-inline-start:2px dashed var(--dk-line)}}
.dk-step h3{{font-size:var(--dk-t-lg);margin-block-end:var(--dk-s-1)}}
.dk-step p{{color:var(--dk-muted);margin:0}}
/* CTA band */
.dk-cta{{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:var(--dk-s-5);padding:var(--dk-s-7) var(--dk-s-6);border-radius:var(--dk-r-lg);background:linear-gradient(120deg,var(--dk-panel),var(--dk-raised));border:1px solid var(--dk-line);box-shadow:var(--dk-e-1)}}
.dk-cta h2{{font-size:var(--dk-t-2xl);margin:0 0 var(--dk-s-2)}}
.dk-cta p{{color:var(--dk-muted);margin:0;max-inline-size:60ch}}
/* callout / limit box */
.dk-callout{{display:flex;gap:var(--dk-s-3);padding:var(--dk-s-4) var(--dk-s-5);border-radius:var(--dk-r-md);background:var(--dk-panel);border:1px solid var(--dk-line);border-inline-start:4px solid var(--dk-steel)}}
.dk-callout-limit{{border-inline-start-color:var(--dk-amber)}}
.dk-callout .dk-icon{{color:var(--dk-steel);margin-block-start:.15em}}
.dk-callout-limit .dk-icon{{color:var(--dk-amber)}}
.dk-callout strong{{display:block;margin-block-end:var(--dk-s-1)}}
.dk-callout p{{margin:0;color:var(--dk-muted)}}
/* card */
.dk-card{{display:flex;flex-direction:column;gap:var(--dk-s-2);padding:var(--dk-s-5);background:var(--dk-panel);border:1px solid var(--dk-line);border-radius:var(--dk-r-lg);box-shadow:var(--dk-e-1);text-decoration:none;color:inherit;transition:box-shadow .2s,transform .2s,border-color .2s}}
a.dk-card:hover{{box-shadow:var(--dk-e-3);transform:translateY(-2px);border-color:var(--dk-steel)}}
.dk-card-head{{display:flex;align-items:center;justify-content:space-between;gap:var(--dk-s-2);color:var(--dk-steel)}}
.dk-card h3{{font-size:var(--dk-t-xl);margin:0;color:var(--dk-ink)}}
.dk-card p{{margin:0;color:var(--dk-muted)}}
.dk-card-go{{margin-block-start:auto;display:inline-flex;align-items:center;gap:var(--dk-s-1);font-weight:600;color:var(--dk-link)}}
/* badge */
.dk-badge{{display:inline-flex;align-items:center;gap:var(--dk-s-1);padding:2px var(--dk-s-2);border-radius:var(--dk-r-pill);font:600 var(--dk-t-xs)/1.5 var(--dk-f-mono);letter-spacing:.06em;text-transform:uppercase;border:1px solid currentColor}}
.dk-badge-steel{{color:var(--dk-steel)}}
.dk-badge-amber{{color:var(--dk-amber)}}
.dk-badge-muted{{color:var(--dk-muted)}}
.dk-badge-ok{{color:var(--dk-ok)}}
/* breadcrumb */
.dk-crumbs ol{{list-style:none;display:flex;flex-wrap:wrap;gap:var(--dk-s-1);margin:0;padding:0;font-size:var(--dk-t-sm);color:var(--dk-muted)}}
.dk-crumbs li{{display:inline-flex;align-items:center;gap:var(--dk-s-1)}}
.dk-crumbs li+li::before{{content:"/";color:var(--dk-line);margin-inline-end:var(--dk-s-1)}}
.dk-crumbs [aria-current]{{color:var(--dk-ink);font-weight:600}}
/* footer */
.dk-footer{{padding:var(--dk-s-7) var(--dk-s-5) var(--dk-s-5);background:var(--dk-panel);border-block-start:1px solid var(--dk-line);border-radius:var(--dk-r-lg)}}
.dk-footer-cols{{display:grid;gap:var(--dk-s-5);grid-template-columns:repeat(auto-fit,minmax(min(100%,160px),1fr))}}
.dk-footer h3{{font:600 var(--dk-t-xs)/1 var(--dk-f-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--dk-muted);margin-block-end:var(--dk-s-3)}}
.dk-footer ul{{list-style:none;margin:0;padding:0;display:grid;gap:var(--dk-s-2)}}
.dk-footer a{{color:var(--dk-ink);text-decoration:none}}
.dk-footer a:hover{{color:var(--dk-steel);text-decoration:underline}}
.dk-footer-note{{margin-block-start:var(--dk-s-6);padding-block-start:var(--dk-s-4);border-block-start:1px solid var(--dk-line);font-size:var(--dk-t-sm);color:var(--dk-muted)}}
@media (prefers-reduced-motion: reduce){{.dk-card,a.dk-card:hover{{transition:none;transform:none}}}}
"""


# The hero's pause control. Reduced motion: the video never starts, the
# poster stands, and the button says "Play" so motion is opt-in.
KIT_JS = """(() => {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  for (const hero of document.querySelectorAll('[data-dk-hero]')) {
    const v = hero.querySelector('video');
    const b = hero.querySelector('.dk-hero-pause');
    if (!v || !b) continue;
    const set = (paused) => {
      b.setAttribute('aria-pressed', String(paused));
      b.querySelector('.dk-hero-pause-t').textContent = paused ? b.dataset.play : b.dataset.pause;
    };
    if (reduce) { v.removeAttribute('autoplay'); v.pause(); set(true); }
    else v.play().then(() => set(false), () => set(true));
    b.addEventListener('click', () => {
      if (v.paused) v.play().then(() => set(false), () => set(true));
      else { v.pause(); set(true); }
    });
  }
})();"""


def button(text, href, kind='primary', icon_name=None):
    ic = icon(icon_name) if icon_name else ''
    return f'<a class="dk-btn dk-btn-{E(kind)}" href="{E(href)}">{E(text)}{ic}</a>'


def hero(d):
    """{eyebrow, title, lede, actions:[{text,href,kind}], video|None,
    pause_label, play_label} - video: {webm, mp4, poster, credit}. The title
    is a <p> styled as display text unless as_h1=True: a page has ONE h1."""
    _need(d, ['eyebrow', 'title', 'lede', 'actions', 'video', 'as_h1'], 'hero')
    tag = 'h1' if d['as_h1'] else 'p'
    acts = ''.join(button(a['text'], a['href'], a['kind'],
                          'arrow-right' if a['kind'] == 'primary' else None) for a in d['actions'])
    media = ''
    v = d['video']
    if v is not None:
        _need(v, ['webm', 'mp4', 'poster', 'credit', 'pause_label', 'play_label'], 'hero.video')
        media = (f'<div class="dk-hero-media"><video muted loop playsinline autoplay preload="metadata" '
                 f'poster="{E(v["poster"])}" aria-hidden="true">'
                 f'<source src="{E(v["webm"])}" type="video/webm">'
                 f'<source src="{E(v["mp4"])}" type="video/mp4"></video></div>'
                 f'<button type="button" class="dk-hero-pause" aria-pressed="false" '
                 f'data-pause="{E(v["pause_label"])}" data-play="{E(v["play_label"])}">'
                 f'<span class="dk-i-pause">{icon("pause")}</span><span class="dk-i-play">{icon("play")}</span>'
                 f'<span class="dk-hero-pause-t">{E(v["pause_label"])}</span></button>'
                 f'<span class="dk-hero-credit">{E(v["credit"])}</span>')
    return (f'<section class="dk-hero" data-dk-hero>{media}<div class="dk-hero-scrim"></div>'
            f'<div class="dk-hero-body"><p class="dk-eyebrow">{E(d["eyebrow"])}</p>'
            f'<{tag} class="dk-hero-title">{E(d["title"])}</{tag}>'
            f'<p class="dk-hero-lede">{E(d["lede"])}</p><div class="dk-actions">{acts}</div></div></section>')


def feature_grid(items):
    """[{icon, title, body}]"""
    out = []
    for it in items:
        _need(it, ['icon', 'title', 'body'], 'feature_grid')
        out.append(f'<article class="dk-feature"><span class="dk-feature-icon">{icon(it["icon"])}</span>'
                   f'<h3>{E(it["title"])}</h3><p>{E(it["body"])}</p></article>')
    return f'<div class="dk-grid">{"".join(out)}</div>'


def stat_band(stats):
    """[{value, label, source}] - value is a figure the CALLER computed from a
    registry; source names that registry, and is shown."""
    out = []
    for s in stats:
        _need(s, ['value', 'label', 'source'], 'stat_band')
        out.append(f'<div class="dk-stat"><span class="dk-stat-v">{E(str(s["value"]))}</span>'
                   f'<span class="dk-stat-l">{E(s["label"])}</span>'
                   f'<span class="dk-stat-src">{E(s["source"])}</span></div>')
    return f'<div class="dk-stats">{"".join(out)}</div>'


def split(d):
    """{media_html, eyebrow, title, body, action|None, reverse}"""
    _need(d, ['media_html', 'eyebrow', 'title', 'body', 'action', 'reverse'], 'split')
    act = ''
    if d['action'] is not None:
        a = d['action']
        act = f'<div class="dk-actions">{button(a["text"], a["href"], a["kind"], "arrow-right")}</div>'
    rev = ' dk-split-rev' if d['reverse'] else ''
    return (f'<div class="dk-split{rev}"><div class="dk-split-media">{d["media_html"]}</div>'
            f'<div><p class="dk-eyebrow">{E(d["eyebrow"])}</p><h2>{E(d["title"])}</h2>'
            f'<p>{E(d["body"])}</p>{act}</div></div>')


def timeline(steps):
    """[{title, body}] - numbered by CSS counters, so no digit is typed."""
    out = []
    for s in steps:
        _need(s, ['title', 'body'], 'timeline')
        out.append(f'<li class="dk-step"><h3>{E(s["title"])}</h3><p>{E(s["body"])}</p></li>')
    return f'<ol class="dk-steps">{"".join(out)}</ol>'


def cta(d):
    """{title, body, action:{text,href,kind}}"""
    _need(d, ['title', 'body', 'action'], 'cta')
    a = d['action']
    return (f'<div class="dk-cta"><div><h2>{E(d["title"])}</h2><p>{E(d["body"])}</p></div>'
            f'{button(a["text"], a["href"], a["kind"], "arrow-right")}</div>')


def callout(d):
    """{kind: 'note'|'limit', title, body} - 'limit' is the box a page uses to
    state what something is NOT (unverified, schematic, play-only)."""
    _need(d, ['kind', 'title', 'body'], 'callout')
    if d['kind'] not in ('note', 'limit'):
        raise KeyError(f"design_kit.callout: kind {d['kind']!r} is not note|limit")
    ic = icon('circle-alert' if d['kind'] == 'limit' else 'info')
    role = ' role="note"'
    return (f'<aside class="dk-callout dk-callout-{d["kind"]}"{role}>{ic}<div><strong>{E(d["title"])}</strong>'
            f'<p>{E(d["body"])}</p></div></aside>')


def badge(text, tone):
    if tone not in ('steel', 'amber', 'muted', 'ok'):
        raise KeyError(f'design_kit.badge: tone {tone!r} is not steel|amber|muted|ok')
    return f'<span class="dk-badge dk-badge-{tone}">{E(text)}</span>'


def card(d):
    """{icon, title, body, badge:(text,tone)|None, href|None, go|None}"""
    _need(d, ['icon', 'title', 'body', 'badge', 'href', 'go'], 'card')
    b = badge(*d['badge']) if d['badge'] is not None else ''
    head = f'<div class="dk-card-head">{icon(d["icon"])}{b}</div>'
    inner = f'{head}<h3>{E(d["title"])}</h3><p>{E(d["body"])}</p>'
    if d['href'] is None:
        return f'<article class="dk-card">{inner}</article>'
    return (f'<a class="dk-card" href="{E(d["href"])}">{inner}'
            f'<span class="dk-card-go">{E(d["go"])}{icon("chevron-right")}</span></a>')


def breadcrumb(items, label):
    """[(text, href|None)] - the last item is the current page."""
    out = []
    for i, (text, href) in enumerate(items):
        if i == len(items) - 1:
            out.append(f'<li><span aria-current="page">{E(text)}</span></li>')
        else:
            out.append(f'<li><a href="{E(href)}">{E(text)}</a></li>')
    return f'<nav class="dk-crumbs" aria-label="{E(label)}"><ol>{"".join(out)}</ol></nav>'


def footer(cols, note):
    """[{title, links:[(text, href)]}], note"""
    out = []
    for c in cols:
        _need(c, ['title', 'links'], 'footer')
        lis = ''.join(f'<li><a href="{E(h)}">{E(t)}</a></li>' for t, h in c['links'])
        out.append(f'<div><h3>{E(c["title"])}</h3><ul>{lis}</ul></div>')
    return (f'<footer class="dk-footer"><div class="dk-footer-cols">{"".join(out)}</div>'
            f'<p class="dk-footer-note">{E(note)}</p></footer>')


def contrast(fg, bg):
    """WCAG 2.x contrast ratio of two #RRGGBB colours."""
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    a, b = sorted((lum(fg), lum(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)
