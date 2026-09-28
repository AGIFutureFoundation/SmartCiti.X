"""The page hero band and the enterprise theme layer for document pages.

    from pagehero import pagehero, theme, clip_ids, PATTERNS
    head_css, hero_html, js = pagehero('web/trade_craft_lessons.html', {...})
    theme_css, theme_js = theme('doc')      # or theme('canvas')

pagehero(page_path, d) -> (head_css, hero_html, js)
    A video-style header band: the clip's poster <img> (fixed 16:9 source,
    band has a fixed min-height, so nothing shifts when media arrives) and a
    muted, looping, aria-hidden <video> that JS starts ONLY when the reader
    has not asked for reduced motion and has not turned on Save-Data; phones
    (<= 640 px) get the 480 px preview webm. A real pause/play <button>
    (WCAG 2.2.2) appears once motion starts. The scrim's text contrast is
    MEASURED: media/build.py records the brightest colour of every pixel of
    every frame of the clip (`measured.brightest_rgb`), this module
    composites the scrim's weakest text-zone alpha over it and asserts every
    text colour the band sets clears 4.5:1 with design_kit.contrast - a
    clip too bright for the scrim stops the build by name.
    head_css is CSS text (no <style> tag); js is script text (no <script>
    tag); the builder puts each in its own <style>/<script>. hero_html goes
    right after the site nav (inside or before <main>).

    d (every key required - fail closed, KeyError names the missing one):
      clip      id from media/registry/media.json clips[] (unknown id: error)
      kicker    small uppercase label above the title
      title     display title text
      accent    a substring of title rendered as the accent word
      accent_style  'gradient' | 'outline'
      lede      one or two sentences
      actions   [{text, href, kind: 'primary'|'ghost'}] (design_kit.button)
      as_h1     True if the title is the page's one <h1>, else a <p>
      labels    {pause, play} button text (from the page's locale)
      credit    footage credit line (from the page's locale)

theme(mode) -> (css, js)
    The enterprise layer, opt-in by a body class:
      mode 'doc'    -> <body class="tc-theme">        document pages
      mode 'canvas' -> <body class="tc-theme-canvas"> full-screen canvas
                       pages (3D, wilds, geomap): panel/button/badge and
                       focus styling only - no page background, no reveal.
    Tokens are design_kit.TOKENS (dark + light palettes) as --tc-* custom
    properties. Components: .tc-card (a.tc-card lifts on hover), .tc-panel
    (glass with a solid fallback), .tc-btn(-primary|-ghost), .tc-table,
    .tc-badge(-ok|-warn|-info|-muted), .tc-kicker, .tc-page-title,
    .tc-stat, .tc-grid; [data-tc-reveal] fades an element in on scroll
    (IntersectionObserver; content is visible without JS and under
    reduced motion).

PATTERNS  which MIT template kit each pattern re-expresses (layout, spacing
          and type scale only - no kit CSS, image or copy is vendored).
"""
import html
import json
import pathlib
import posixpath
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import design_kit as K  # noqa: E402

E = html.escape
MEDIA = json.loads((ROOT / 'media' / 'registry' / 'media.json').read_text(encoding='utf-8'))
CLIPS = {c['id']: c for c in MEDIA['clips']}
PAL = K.TOKENS['palette']

# The scrim: plate at SCRIM_TEXT_ALPHA or more everywhere text can sit.
# The CSS below is written from these constants, never typed twice.
SCRIM_TEXT_ALPHA = 0.72
SCRIM_EDGE_ALPHA = 0.88   # the reading edge (inline-start)
SCRIM_FAR_ALPHA = 0.30    # the far edge on wide screens, where no text sits
MIN_RATIO = 4.5
GHOST_FILL = 0.06        # the ghost button's white fill alpha

# every colour the band sets as text over the scrim (the primary button
# carries its own amber fill; its pair is held by design_kit CONTRAST_PAIRS)
HERO_TEXT = {
    'title': '#F4F7F6',
    'lede': '#D3DCDB',
    'kicker': '#FAD08C',
    'accent-from': '#FFD58F',
    'accent-to': '#8FE9F2',
    'ghost-button': '#F4F7F6',
    'credit': '#D3DCDB',
}

PATTERNS = [
    {'pattern': 'hero band: full-bleed media, scrim, bottom-aligned display type',
     'kit': 'Start Bootstrap Creative 7.0.7 (masthead)', 'license': 'MIT'},
    {'pattern': 'hero kicker + oversized heading rhythm',
     'kit': 'Start Bootstrap Agency 7.0.12 (masthead)', 'license': 'MIT'},
    {'pattern': 'page header: pretitle (kicker) over page title',
     'kit': 'Tabler 1.6.0 (page-pretitle, page-title)', 'license': 'MIT'},
    {'pattern': 'card, card-table, tinted badges, stat tile',
     'kit': 'Tabler 1.6.0 (card, card-table, badge -lt, card-sm)', 'license': 'MIT'},
    {'pattern': 'icon feature rows, alternating showcase rows',
     'kit': 'Start Bootstrap Landing Page 6.0.6 (features-icons, showcase)', 'license': 'MIT'},
]


class PageHeroError(KeyError):
    pass


def _need(d, keys, what):
    for k in keys:
        if k not in d:
            raise PageHeroError(f'pagehero.{what}: missing field {k!r}')


def _rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def _hex(c):
    return '#%02X%02X%02X' % tuple(max(0, min(255, round(x))) for x in c)


def composite(top, alpha, under):
    """`top` at `alpha` over `under` (sRGB, as the browser blends)."""
    t, u = _rgb(top), _rgb(under)
    return _hex([alpha * a + (1 - alpha) * b for a, b in zip(t, u)])


def clip_ids():
    return sorted(CLIPS)


def measure(clip_id):
    """Contrast of every hero text colour over the scrim at its weakest
    text-zone alpha composited over the clip's measured brightest colour.
    Returns {'under': hex, 'ratios': {name: ratio}, 'min': ratio}; raises
    PageHeroError if any ratio is below MIN_RATIO."""
    if clip_id not in CLIPS:
        raise PageHeroError(f'pagehero: unknown clip id {clip_id!r} (have {clip_ids()})')
    c = CLIPS[clip_id]
    if 'measured' not in c or 'brightest_rgb' not in c['measured']:
        raise PageHeroError(f'pagehero: clip {clip_id!r} has no measured.brightest_rgb (run media/build.py)')
    under = composite(PAL['dark']['plate'], SCRIM_TEXT_ALPHA, c['measured']['brightest_rgb'])
    ratios = {k: round(K.contrast(v, under), 2) for k, v in HERO_TEXT.items()}
    # the ghost button's own translucent fill lightens what its label sits on
    ratios['ghost-button'] = round(K.contrast(HERO_TEXT['ghost-button'], composite('#FFFFFF', GHOST_FILL, under)), 2)
    low = {k: r for k, r in ratios.items() if r < MIN_RATIO}
    if low:
        raise PageHeroError(f'pagehero: clip {clip_id!r} too bright for the scrim - {low} < {MIN_RATIO}')
    return {'under': under, 'ratios': ratios, 'min': min(ratios.values())}


def _rel(page_path, target):
    base = posixpath.dirname(page_path) or '.'
    return posixpath.relpath(target, base)


# the two display faces the band uses, from the vendored fonts.css, with
# their urls rewritten relative to the page (inline CSS resolves urls
# against the document)
_FONTS_CSS = (HERE / 'vendor' / 'fonts' / 'fonts.css').read_text(encoding='utf-8')
_FACES = [('Barlow Condensed', '700'), ('Archivo', '600')]


def _font_faces(page_path):
    out = []
    for block in re.findall(r'@font-face\s*\{[^}]*\}', _FONTS_CSS):
        fam = re.search(r"font-family:\s*'([^']+)'", block).group(1)
        wt = re.search(r'font-weight:\s*(\d+)', block).group(1)
        if (fam, wt) not in _FACES:
            continue
        url = re.search(r'url\(\./([^)]+)\)', block).group(1)
        block = block.replace(f'url(./{url})', f'url({_rel(page_path, "web/vendor/fonts/" + url)})')
        out.append(re.sub(r'\s*\n\s*', '', block))
    found = {(re.search(r"font-family:\s*'([^']+)'", b).group(1),
              re.search(r'font-weight:\s*(\d+)', b).group(1)) for b in out}
    if found != set(_FACES):
        raise PageHeroError(f'pagehero: vendored fonts.css lacks {set(_FACES) - found}')
    return ''.join(out)


def _a(alpha):
    r, g, b = _rgb(PAL['dark']['plate'])
    return f'rgb({r} {g} {b} / {alpha})'


def hero_css(page_path):
    T, S = HERO_TEXT, K.TOKENS
    return (_font_faces(page_path) + f"""
.ph{{--ph-plate:{PAL['dark']['plate']};position:relative;isolation:isolate;overflow:hidden;display:grid;align-items:end;
min-block-size:clamp(380px,62vh,600px);background:var(--ph-plate);color:{T['title']};
border-block-end:1px solid rgb(255 255 255 / .08);font-family:{S['font']['body']}}}
.ph *{{box-sizing:border-box}}
.ph-media{{position:absolute;inset:0;z-index:-2;overflow:hidden}}
.ph-media img,.ph-media video{{position:absolute;inset:0;inline-size:100%;block-size:100%;object-fit:cover;display:block}}
.ph-media video{{opacity:0;transition:opacity .8s ease}}
.ph[data-ph-state="playing"] .ph-media video,.ph[data-ph-state="paused"] .ph-media video{{opacity:1}}
.ph-scrim{{position:absolute;inset:0;z-index:-1;pointer-events:none;
background:linear-gradient(0deg,{_a(SCRIM_EDGE_ALPHA)} 0%,{_a(SCRIM_TEXT_ALPHA)} 45%,{_a(SCRIM_TEXT_ALPHA)} 100%)}}
@media (min-width:900px){{.ph-scrim{{background:
linear-gradient(90deg,{_a(SCRIM_EDGE_ALPHA)} 0%,{_a(SCRIM_TEXT_ALPHA)} 58%,{_a(SCRIM_FAR_ALPHA)} 100%)}}
.ph-body{{max-inline-size:min(760px,56%)}}}}
[dir="rtl"] .ph-scrim{{transform:scaleX(-1)}}
.ph-scrim::after{{content:"";position:absolute;inset:0;background:radial-gradient(120% 80% at 0% 100%,rgb(65 196 212 / .10),transparent 60%)}}
.ph-body{{position:relative;padding-block:clamp(56px,10vh,112px) clamp(32px,6vh,64px);padding-inline:clamp(16px,5vw,64px)}}
.ph-kicker{{display:inline-flex;align-items:center;gap:10px;margin:0 0 14px;color:{T['kicker']};
font:600 .78rem/1 {S['font']['mono']};letter-spacing:.18em;text-transform:uppercase}}
.ph-kicker::before{{content:"";inline-size:28px;block-size:2px;background:currentColor;border-radius:2px}}
.ph-title{{margin:0 0 16px;font-family:'Barlow Condensed','Archivo',system-ui,sans-serif;font-weight:700;
font-size:clamp(2.4rem,1.2rem + 5vw,4.6rem);line-height:.98;letter-spacing:.005em;text-transform:none;
color:{T['title']};text-wrap:balance;overflow-wrap:anywhere}}
.ph-accent{{color:{T['accent-from']}}}
.ph-accent-gradient{{background:linear-gradient(95deg,{T['accent-from']},{T['accent-to']});
-webkit-background-clip:text;background-clip:text;color:transparent}}
@supports not ((-webkit-background-clip:text) or (background-clip:text)){{.ph-accent-gradient{{color:{T['accent-from']}}}}}
.ph-accent-outline{{color:transparent;-webkit-text-stroke:2px {T['accent-from']};paint-order:stroke fill}}
@supports not (-webkit-text-stroke:2px black){{.ph-accent-outline{{color:{T['accent-from']}}}}}
@media (forced-colors:active){{.ph-accent-gradient,.ph-accent-outline{{color:CanvasText;background:none;-webkit-text-stroke:0}}}}
.ph-lede{{margin:0;max-inline-size:60ch;color:{T['lede']};font-size:clamp(1.02rem,.95rem + .35vw,1.2rem);line-height:1.55}}
.ph-actions{{display:flex;flex-wrap:wrap;gap:12px;margin-block-start:24px}}
.ph .dk-btn{{display:inline-flex;align-items:center;gap:8px;padding:12px 22px;border-radius:10px;min-block-size:44px;
font:600 1rem/1.1 {S['font']['body']};text-decoration:none;border:1px solid transparent;transition:transform .15s,box-shadow .15s,background .15s}}
.ph .dk-btn-primary{{background:{PAL['dark']['amber']};color:{PAL['dark']['amber-ink']};box-shadow:0 8px 24px -8px rgb(232 163 61 / .6)}}
.ph .dk-btn-ghost{{background:rgb(255 255 255 / {GHOST_FILL});color:{T['ghost-button']};border-color:rgb(244 247 246 / .45);
-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px)}}
.ph .dk-btn:hover{{transform:translateY(-1px)}}
.ph .dk-btn-ghost:hover{{border-color:{PAL['dark']['steel']}}}
.ph .dk-icon{{inline-size:1.15em;block-size:1.15em;flex:none}}
.ph :focus-visible{{outline:3px solid {PAL['dark']['steel']};outline-offset:3px;border-radius:10px}}
.ph-toggle{{position:absolute;inset-block-start:14px;inset-inline-end:14px;display:inline-flex;align-items:center;gap:8px;
min-block-size:40px;min-inline-size:40px;padding:6px 14px;border-radius:999px;cursor:pointer;
background:rgb(18 24 27 / .78);color:{T['title']};border:1px solid rgb(244 247 246 / .35);font:500 .8rem/1 {S['font']['body']}}}
.ph-toggle[hidden]{{display:none}}
.ph-toggle .ph-i-play{{display:none}}
.ph-toggle[aria-pressed="true"] .ph-i-play{{display:inline-flex}}
.ph-toggle[aria-pressed="true"] .ph-i-pause{{display:none}}
.ph-toggle .dk-icon{{inline-size:16px;block-size:16px}}
.ph-credit{{position:absolute;inset-block-end:8px;inset-inline-end:14px;margin:0;font:500 .7rem/1.2 {S['font']['mono']};
letter-spacing:.04em;color:{T['credit']};background:rgb(18 24 27 / .78);padding:3px 8px;border-radius:6px;max-inline-size:calc(100% - 28px)}}
@media (max-width:640px){{.ph-credit{{position:static;margin:0 clamp(16px,5vw,64px) 12px;justify-self:start;inset:auto}}}}
@media (prefers-reduced-motion:reduce){{.ph-media video{{display:none}}.ph .dk-btn{{transition:none}}.ph .dk-btn:hover{{transform:none}}}}
""")


HERO_JS = r"""(() => {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  const conn = navigator.connection;
  const saveData = !!(conn && conn.saveData);
  for (const band of document.querySelectorAll('[data-ph]')) {
    if (band.dataset.phInit) continue;
    band.dataset.phInit = '1';
    const v = band.querySelector('video');
    const b = band.querySelector('.ph-toggle');
    const t = b.querySelector('.ph-toggle-t');
    const state = (s) => {
      band.dataset.phState = s;
      b.hidden = s === 'poster';
      b.setAttribute('aria-pressed', String(s === 'paused'));
      t.textContent = s === 'paused' ? b.dataset.play : b.dataset.pause;
    };
    band.dataset.phReason = reduce.matches ? 'reduced-motion' : saveData ? 'save-data' : '';
    if (reduce.matches || saveData) { state('poster'); continue; }
    const small = matchMedia('(max-width: 640px)').matches;
    const webm = v.canPlayType('video/webm; codecs="vp9"') !== '';
    v.src = webm ? (small ? v.dataset.webm480 : v.dataset.webm) : v.dataset.mp4;
    band.dataset.phSrc = webm ? (small ? '480' : 'webm') : 'mp4';
    let wanted = true;
    const play = () => v.play().then(() => state('playing'), () => state(v.readyState ? 'paused' : 'poster'));
    b.addEventListener('click', () => {
      if (v.paused) { wanted = true; play(); } else { wanted = false; v.pause(); state('paused'); }
    });
    reduce.addEventListener('change', (e) => { if (e.matches) { wanted = false; v.pause(); state('poster'); } });
    if ('IntersectionObserver' in window) {
      new IntersectionObserver((es) => {
        for (const e of es) {
          if (e.isIntersecting && wanted && v.paused) play();
          else if (!e.isIntersecting && !v.paused) v.pause();
        }
      }).observe(band);
    } else play();
  }
})();"""


def pagehero(page_path, d):
    _need(d, ['clip', 'kicker', 'title', 'accent', 'accent_style', 'lede', 'actions', 'as_h1',
              'labels', 'credit'], 'd')
    m = measure(d['clip'])
    c = CLIPS[d['clip']]
    _need(d['labels'], ['pause', 'play'], 'labels')
    if d['accent_style'] not in ('gradient', 'outline'):
        raise PageHeroError(f"pagehero: accent_style {d['accent_style']!r} is not gradient|outline")
    if not d['accent'] or d['accent'] not in d['title']:
        raise PageHeroError(f"pagehero: accent {d['accent']!r} is not part of the title")
    for f in ('webm', 'mp4', 'poster', 'preview'):
        if f not in c['files']:
            raise PageHeroError(f"pagehero: clip {d['clip']!r} lacks files.{f}")
    acts = []
    for a in d['actions']:
        _need(a, ['text', 'href', 'kind'], 'actions[]')
        if a['kind'] not in ('primary', 'ghost'):
            raise PageHeroError(f"pagehero: action kind {a['kind']!r} is not primary|ghost")
        acts.append(K.button(a['text'], a['href'], a['kind'], 'arrow-right' if a['kind'] == 'primary' else None))
    rel = lambda k: E(_rel(page_path, c['files'][k]['path']))
    head, tail = d['title'].split(d['accent'], 1)
    tag = 'h1' if d['as_h1'] else 'p'
    w, h = c['resolution']
    ratios = ' '.join(f'{k}={v}' for k, v in m['ratios'].items())
    hero = (
        f'<section class="ph" data-ph data-ph-clip="{E(c["id"])}" data-ph-state="poster" '
        f'data-ph-contrast-min="{m["min"]}" data-ph-contrast="{E(ratios)}" data-ph-under="{m["under"]}">'
        f'<div class="ph-media" aria-hidden="true">'
        f'<img src="{rel("poster")}" alt="" width="{w}" height="{h}" decoding="async" fetchpriority="high">'
        f'<video muted loop playsinline preload="none" disablepictureinpicture tabindex="-1" aria-hidden="true" '
        f'data-webm="{rel("webm")}" data-webm480="{rel("preview")}" data-mp4="{rel("mp4")}"></video></div>'
        f'<div class="ph-scrim"></div>'
        f'<div class="ph-body"><p class="ph-kicker">{E(d["kicker"])}</p>'
        f'<{tag} class="ph-title">{E(head)}<span class="ph-accent ph-accent-{d["accent_style"]}">'
        f'{E(d["accent"])}</span>{E(tail)}</{tag}>'
        f'<p class="ph-lede">{E(d["lede"])}</p>'
        + (f'<div class="ph-actions">{"".join(acts)}</div>' if acts else '') + '</div>'
        f'<button type="button" class="ph-toggle" aria-pressed="false" hidden '
        f'data-pause="{E(d["labels"]["pause"])}" data-play="{E(d["labels"]["play"])}">'
        f'<span class="ph-i-pause">{K.icon("pause")}</span><span class="ph-i-play">{K.icon("play")}</span>'
        f'<span class="ph-toggle-t">{E(d["labels"]["pause"])}</span></button>'
        f'<p class="ph-credit">{E(d["credit"])}</p></section>')
    return hero_css(page_path), hero, HERO_JS


# ---------------------------------------------------------------- theme layer

def _tc_vars(theme_name):
    p = PAL[theme_name]
    return ''.join(f'--tc-{k}:{v};' for k, v in p.items())


def theme(mode):
    if mode not in ('doc', 'canvas'):
        raise PageHeroError(f'pagehero.theme: mode {mode!r} is not doc|canvas')
    for fg, bg, need in K.CONTRAST_PAIRS:
        for name in ('dark', 'light'):
            r = K.contrast(PAL[name][fg], PAL[name][bg])
            if r < need:
                raise PageHeroError(f'pagehero.theme: {name} {fg} on {bg} is {r:.2f} < {need}')
    S = K.TOKENS
    base = ''.join(f'--tc-r-{k}:{v};' for k, v in S['radius'].items())
    base += ''.join(f'--tc-e-{k}:{v};' for k, v in S['elevation'].items())
    sel = 'body.tc-theme' if mode == 'doc' else 'body.tc-theme-canvas'
    dark, light = _tc_vars('dark'), _tc_vars('light')
    if mode == 'doc':
        scheme = (f'{sel}{{{base}{dark}}}\n'
                  f'@media (prefers-color-scheme: light){{:root:not([data-theme="dark"]) {sel}{{{light}}}}}\n'
                  f'[data-theme="dark"] {sel},{sel}[data-theme="dark"]{{{dark}}}\n'
                  f'[data-theme="light"] {sel},{sel}[data-theme="light"]{{{light}}}\n'
                  # a block inside the page can force either palette (the style guide shows both)
                  f'{sel} [data-theme="dark"]{{{dark}}}\n{sel} [data-theme="light"]{{{light}}}\n')
    else:  # canvas pages are dark scenes: their panels stay dark
        scheme = f'{sel}{{{base}{dark}}}\n'
    css = scheme + f"""{sel} .tc-panel{{background:var(--tc-panel);color:var(--tc-ink);border:1px solid var(--tc-line);border-radius:var(--tc-r-lg);box-shadow:var(--tc-e-2)}}
@supports ((-webkit-backdrop-filter:blur(1px)) or (backdrop-filter:blur(1px))){{{sel} .tc-panel{{background:color-mix(in srgb,var(--tc-panel) 86%,transparent);-webkit-backdrop-filter:blur(12px) saturate(1.2);backdrop-filter:blur(12px) saturate(1.2)}}}}
{sel} .tc-btn{{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-block-size:44px;padding:10px 18px;border-radius:10px;font:600 .95rem/1.1 {S['font']['body']};text-decoration:none;border:1px solid transparent;cursor:pointer;transition:transform .15s,box-shadow .15s,border-color .15s}}
{sel} .tc-btn-primary{{background:var(--tc-amber);color:var(--tc-amber-ink)}}
{sel} .tc-btn-primary:hover{{box-shadow:0 8px 22px -10px var(--tc-amber);transform:translateY(-1px)}}
{sel} .tc-btn-ghost{{background:transparent;color:var(--tc-ink);border-color:var(--tc-line)}}
{sel} .tc-btn-ghost:hover{{border-color:var(--tc-steel)}}
{sel} .tc-badge{{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:999px;font:600 .72rem/1.5 {S['font']['mono']};letter-spacing:.05em;text-transform:uppercase;color:var(--tc-ink);background:transparent;border:1px solid color-mix(in srgb,var(--tc-muted) 40%,transparent)}}
{sel} .tc-badge-ok{{color:var(--tc-ok);background:transparent;border-color:color-mix(in srgb,var(--tc-ok) 45%,transparent)}}
{sel} .tc-badge-warn{{color:var(--tc-warn);background:transparent;border-color:color-mix(in srgb,var(--tc-warn) 45%,transparent)}}
{sel} .tc-badge-info{{color:var(--tc-steel);background:transparent;border-color:color-mix(in srgb,var(--tc-steel) 45%,transparent)}}
{sel} .tc-badge-muted{{color:var(--tc-muted)}}
{sel} :focus-visible{{outline:3px solid var(--tc-steel);outline-offset:2px}}
@media (prefers-reduced-motion:reduce){{{sel} .tc-btn{{transition:none}}{sel} .tc-btn:hover{{transform:none}}}}
"""
    if mode == 'doc':
        css += f"""{sel}{{background:radial-gradient(1200px 500px at 100% -10%,color-mix(in srgb,var(--tc-steel) 7%,transparent),transparent 70%),var(--tc-plate);color:var(--tc-ink);-webkit-font-smoothing:antialiased}}
{sel} .tc-kicker{{margin:0 0 6px;font:600 .75rem/1 {S['font']['mono']};letter-spacing:.14em;text-transform:uppercase;color:var(--tc-amber)}}
{sel} .tc-page-title{{margin:0;font:700 {S['type']['3xl']}/1.05 {S['font']['display']};color:var(--tc-ink)}}
{sel} .tc-grid{{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr))}}
{sel} .tc-card{{display:flex;flex-direction:column;gap:8px;padding:20px;background:var(--tc-panel);color:var(--tc-ink);border:1px solid var(--tc-line);border-radius:var(--tc-r-lg);box-shadow:var(--tc-e-1);text-decoration:none;transition:transform .2s,box-shadow .2s,border-color .2s}}
{sel} .tc-card p{{margin:0;color:var(--tc-muted)}}
{sel} a.tc-card:hover,{sel} .tc-card[data-tc-lift]:hover{{transform:translateY(-3px);box-shadow:var(--tc-e-3);border-color:var(--tc-steel)}}
{sel} .tc-stat{{padding:16px 20px;background:var(--tc-panel);border:1px solid var(--tc-line);border-radius:var(--tc-r-lg)}}
{sel} .tc-stat-v{{display:block;font:700 {S['type']['3xl']}/1 {S['font']['display']};color:var(--tc-ink);font-variant-numeric:tabular-nums}}
{sel} .tc-stat-l{{display:block;margin-block-start:4px;font-size:.85rem;color:var(--tc-muted)}}
{sel} .tc-table{{inline-size:100%;border-collapse:separate;border-spacing:0;background:var(--tc-panel);border:1px solid var(--tc-line);border-radius:var(--tc-r-lg);overflow:hidden;font-variant-numeric:tabular-nums}}
{sel} .tc-table th{{text-align:start;font:600 .72rem/1.2 {S['font']['mono']};letter-spacing:.08em;text-transform:uppercase;color:var(--tc-muted);background:var(--tc-raised);padding:10px 16px;border-block-end:1px solid var(--tc-line)}}
{sel} .tc-table td{{padding:12px 16px;border-block-end:1px solid var(--tc-line);color:var(--tc-ink)}}
{sel} .tc-table tbody tr:last-child td{{border-block-end:0}}
{sel} .tc-table tbody tr:hover td{{background:color-mix(in srgb,var(--tc-steel) 6%,transparent)}}
html.tc-reveal-on {sel} [data-tc-reveal]{{opacity:0;transform:translateY(14px);transition:opacity .6s ease,transform .6s ease}}
html.tc-reveal-on {sel} [data-tc-reveal].tc-in{{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){{{sel} .tc-card{{transition:none}}{sel} a.tc-card:hover,{sel} .tc-card[data-tc-lift]:hover{{transform:none}}html.tc-reveal-on {sel} [data-tc-reveal]{{opacity:1;transform:none;transition:none}}}}
"""
    js = '' if mode == 'canvas' else THEME_JS
    return css, js


# Scroll reveal. Nothing is hidden unless this ran, IntersectionObserver
# exists and the reader did not ask for reduced motion; anything already on
# screen is revealed at once, and a 2.5 s safety net reveals the rest.
THEME_JS = r"""(() => {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches || !('IntersectionObserver' in window)) return;
  const els = document.querySelectorAll('[data-tc-reveal]');
  if (!els.length) return;
  document.documentElement.classList.add('tc-reveal-on');
  const io = new IntersectionObserver((es) => {
    for (const e of es) if (e.isIntersecting) { e.target.classList.add('tc-in'); io.unobserve(e.target); }
  }, { rootMargin: '0px 0px -8% 0px' });
  els.forEach((el) => io.observe(el));
  setTimeout(() => els.forEach((el) => el.classList.add('tc-in')), 2500);
})();"""


if __name__ == '__main__':
    for cid in clip_ids():
        m = measure(cid)
        print(f"{cid:24} hero={CLIPS[cid]['hero']!s:5} under {m['under']} min {m['min']}  {m['ratios']}")
