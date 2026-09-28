"""The hero's background footage: markup, style and the small script that
starts it, for the front door and the landing page.

The footage is this product, recorded from a served build of it - never a
stock clip and never generated - and the page says so in one line beside
the control. The rules it holds:

  - two sources, VP9 WebM first and H.264 MP4 second, each at most
    MAX_BYTES, plus a JPEG poster; the build stops if a file is missing or
    over budget;
  - the <video> is decoration: aria-hidden, muted, no text burned in;
  - it never starts on its own under prefers-reduced-motion, under
    Save-Data, or on a screen narrower than SMALL_PX - there the poster
    stands, and the Play control lets a visitor start it by choice;
  - it starts after the page's first paint (the sources are attached by
    script on `load`, so the first paint never waits on video bytes);
  - it sits absolutely behind the hero, so it can never shift the layout;
  - a visible Pause/Play control (WCAG 2.2.2), remembered on this device;
  - a scrim of the page's own plate colour at SCRIM_DARK / SCRIM_LIGHT
    opacity sits between footage and text. test_home.mjs --browser samples
    frames and measures every hero text colour against the worst composited
    pixel under it, so the scrim's number is held to a measured contrast.

CLIP is the one place the footage is chosen: HERO_CLIP_ID names a clip in
MEDIA's b-roll registry (media/registry/media.json), which supplies its
files and their sha256.
"""
import html
import pathlib
import posixpath

ROOT = pathlib.Path(__file__).resolve().parent.parent

MAX_BYTES = 3 * 1024 * 1024
SMALL_PX = 560
SCRIM_DARK = 0.86
SCRIM_LIGHT = 0.90

# The footage is MEDIA's b-roll, chosen by id and read from its registry:
# the paths, and the sha256 each file must still have, come from
# media/registry/media.json, never typed here. A clip not registered
# hero=true, or a file whose bytes changed since MEDIA registered it, stops
# the build by name.
MEDIA_PATH = 'media/registry/media.json'
HERO_CLIP_ID = 'campus-green-low-dolly'


def clip_files(clip_id, need_hero):
    """One registered clip's files, verified: {webm, mp4, poster, source_page,
    provenance, title}. The paths and the sha256 each file must still have
    come from MEDIA's registry; an unknown id, a changed file, or (for the
    hero) a clip not registered hero=true stops the build by name."""
    import hashlib
    import json
    reg = json.loads((ROOT / MEDIA_PATH).read_text(encoding='utf-8'))
    hits = [c for c in reg['clips'] if c['id'] == clip_id]
    assert len(hits) == 1, f'herovideo: {MEDIA_PATH} holds {len(hits)} clips with id {clip_id!r}'
    clip = hits[0]
    if need_hero:
        assert clip['hero'] is True, f'herovideo: {MEDIA_PATH}#{clip_id} is not registered hero=true'
    out = {}
    for k in ('webm', 'mp4', 'poster'):
        f = clip['files'][k]
        data = (ROOT / f['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == f['sha256'], \
            f'herovideo: {f["path"]} no longer matches {MEDIA_PATH}#{clip_id}.files.{k}.sha256'
        out[k] = f['path']
    out['source_page'] = clip['source']['page']
    out['provenance'] = clip['provenance']
    out['title'] = clip['title']
    out['id'] = clip_id
    return out


def _hero_clip():
    return clip_files(HERO_CLIP_ID, need_hero=True)


CLIP = _hero_clip()
CLIP['caption'] = ('Background: a low dolly across the Treasure Island campus green, '
                   'filmed frame by frame from this build’s 3D campus.')


def _checked(rel, maxb):
    p = ROOT / rel
    assert p.is_file(), f'herovideo: {rel} does not exist'
    size = p.stat().st_size
    assert 0 < size <= maxb, f'herovideo: {rel} is {size} bytes; the budget is {maxb}'
    return rel


def hero_video_html(page_path='index.html'):
    """The <video> and scrim; paths are written relative to `page_path`
    (the page's own path from the bundle root)."""
    base = posixpath.dirname(page_path) or '.'
    rel = lambda p: posixpath.relpath(p, base)  # noqa: E731
    webm = _checked(CLIP['webm'], MAX_BYTES)
    mp4 = _checked(CLIP['mp4'], MAX_BYTES)
    poster = _checked(CLIP['poster'], MAX_BYTES)
    E = lambda s: html.escape(s, quote=True)  # noqa: E731
    return (
        '<div class="hv" data-hero-video>'
        f'<video class="hv-video" autoplay muted loop playsinline preload="metadata" '
        f'poster="{E(rel(poster))}" aria-hidden="true" tabindex="-1" disablepictureinpicture>'
        f'<source data-src="{E(rel(webm))}" type="video/webm">'
        f'<source data-src="{E(rel(mp4))}" type="video/mp4">'
        '</video><div class="hv-scrim"></div></div>')


EN_LABELS = {'pause': 'Pause background video', 'play': 'Play background video',
             'caption': CLIP['caption']}


def hero_video_control(labels=None):
    """The control and the provenance line, placed in the hero's flow.
    `labels` ({pause, play, caption}) lets a catalog-driven page supply its
    own words; the script reads both button labels from data attributes, so
    it carries no prose of its own."""
    L = EN_LABELS if labels is None else labels
    for k in ('pause', 'play', 'caption'):
        assert isinstance(L[k], str) and L[k].strip(), f'herovideo: label {k} is empty'
    E = lambda s: html.escape(s, quote=True)  # noqa: E731
    return (
        '<div class="hv-bar">'
        '<button type="button" class="hv-btn" data-hero-video-toggle hidden aria-pressed="false" '
        f'data-label-pause="{E(L["pause"])}" data-label-play="{E(L["play"])}">'
        '<span class="hv-ico" aria-hidden="true"></span>'
        f'<span class="hv-txt">{E(L["pause"])}</span></button>'
        f'<p class="hv-cap">{E(L["caption"])}</p></div>')


HERO_VIDEO_CSS = f"""
[data-hero-host]{{position:relative;isolation:isolate;overflow:hidden}}
.hv{{position:absolute;inset:0;z-index:-1;pointer-events:none;background:var(--plate)}}
.hv-video{{position:absolute;inset:0;inline-size:100%;block-size:100%;object-fit:cover;display:block}}
.hv-scrim{{position:absolute;inset:0;background:rgba(13,19,22,{SCRIM_DARK})}}
@media (prefers-color-scheme:light){{:root:not([data-theme="dark"]) .hv-scrim{{background:rgba(244,246,245,{SCRIM_LIGHT})}}}}
:root[data-theme="light"] .hv-scrim{{background:rgba(244,246,245,{SCRIM_LIGHT})}}
.hv-bar{{display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px;margin-block-start:var(--s4,16px)}}
.hv-btn{{display:inline-flex;align-items:center;gap:8px;min-block-size:44px;padding-block:0;
  padding-inline:12px;border-radius:8px;border:1px solid var(--rule-2);background:var(--panel);
  color:var(--ink);font:600 14px/1 var(--font,inherit);cursor:pointer}}
.hv-btn[hidden]{{display:none}}
.hv-btn:hover{{border-color:var(--mark)}}
.hv-btn:focus-visible{{outline:none;box-shadow:var(--focus)}}
.hv-ico{{inline-size:12px;block-size:12px;border-inline:4px solid currentColor;box-sizing:border-box}}
.hv-btn[aria-pressed="true"] .hv-ico{{border-inline:0;border-block:6px solid transparent;
  border-inline-start:11px solid currentColor;block-size:12px;inline-size:11px}}
.hv-cap{{margin:0;font-size:12.5px;color:var(--muted);max-inline-size:60ch}}
"""

HERO_VIDEO_JS = f"""<script id="hv-js">
/* Background footage. Sources are attached only after the page has painted
   and only when motion is welcome: not under prefers-reduced-motion, not
   under Save-Data, not below {SMALL_PX}px - there the poster stands and the
   button offers Play instead. The choice to pause is remembered on this
   device only. */
(function () {{
  var host = document.querySelector('[data-hero-video]');
  var btn = document.querySelector('[data-hero-video-toggle]');
  if (!host || !btn) return;
  var v = host.querySelector('video');
  var txt = btn.querySelector('.hv-txt');
  var KEY = 'tc-hero-video';
  function pref() {{ try {{ return localStorage.getItem(KEY); }} catch (e) {{ return null; }} }}
  function save(x) {{ try {{ localStorage.setItem(KEY, x); }} catch (e) {{}} }}
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var saveData = !!(navigator.connection && navigator.connection.saveData);
  var small = window.matchMedia('(max-width: {SMALL_PX - 1}px)').matches;
  var loaded = false;
  function attach() {{
    if (loaded) return; loaded = true;
    v.querySelectorAll('source[data-src]').forEach(function (s) {{ s.src = s.getAttribute('data-src'); }});
    v.load();
  }}
  function show(playing) {{
    btn.setAttribute('aria-pressed', playing ? 'false' : 'true');
    txt.textContent = btn.getAttribute(playing ? 'data-label-pause' : 'data-label-play');
    host.setAttribute('data-state', playing ? 'playing' : 'paused');
  }}
  function play() {{
    attach();
    var p = v.play(); show(true);
    if (p && p.catch) p.catch(function () {{ show(false); }});
  }}
  function pause() {{ v.pause(); show(false); }}
  btn.hidden = false;
  btn.addEventListener('click', function () {{
    if (v.paused) {{ save('play'); play(); }} else {{ save('paused'); pause(); }}
  }});
  var auto = !reduce && !saveData && !small && pref() !== 'paused';
  if (!auto) {{ v.removeAttribute('autoplay'); show(false); return; }}
  function go() {{ requestAnimationFrame(function () {{ setTimeout(play, 0); }}); }}
  if (document.readyState === 'complete') go(); else window.addEventListener('load', go);
}}());
</script>"""


# ------------------------------------------------------ section footage ---
# Below the hero, the front door and the landing page carry more of MEDIA's
# registered b-roll in two shapes borrowed (as layout only, re-expressed in
# this page's tokens; no CSS copied) from the Start Bootstrap "Landing Page"
# kit (MIT): a showcase row, where the clip fills one half and the words sit
# beside it on the page's own plate, and a call-to-action band, where the
# words sit over the clip under the same measured scrim as the hero.
# Every clip is chosen by id, verified by sha256 against the registry, and
# named in a caption with its registry title and provenance. The same rules
# as the hero hold: muted, aria-hidden, sources attached by script only when
# the clip scrolls into view, never under reduced motion / Save-Data / a
# narrow screen, and every clip carries its own Pause/Play button.

def _clip_video(c, page_path, cls):
    base = posixpath.dirname(page_path) or '.'
    rel = lambda p: posixpath.relpath(p, base)  # noqa: E731
    E = lambda s: html.escape(s, quote=True)  # noqa: E731
    for k in ('webm', 'mp4', 'poster'):
        _checked(c[k], MAX_BYTES)
    return (f'<video class="{cls}" muted loop playsinline preload="none" '
            f'poster="{E(rel(c["poster"]))}" aria-hidden="true" tabindex="-1" disablepictureinpicture>'
            f'<source data-src="{E(rel(c["webm"]))}" type="video/webm">'
            f'<source data-src="{E(rel(c["mp4"]))}" type="video/mp4"></video>')


def _clip_toggle(labels):
    """A clip's own Pause/Play button; `labels` is {pause, play} from the page's catalog."""
    L = EN_LABELS if labels is None else labels
    for k in ('pause', 'play'):
        assert isinstance(L[k], str) and L[k].strip(), f'herovideo: clip label {k} is empty'
    E = lambda s: html.escape(s, quote=True)  # noqa: E731
    return ('<button type="button" class="hv-btn sv-btn" data-clip-toggle hidden aria-pressed="true" '
            f'data-label-pause="{E(L["pause"])}" data-label-play="{E(L["play"])}">'
            '<span class="hv-ico" aria-hidden="true"></span>'
            f'<span class="hv-txt">{E(L["play"])}</span></button>')


def clip_caption(c):
    return f'{c["title"]}. {c["provenance"]}.'


def showcase_media(clip_id, page_path, labels=None):
    """The media half of a showcase row: the clip, its Pause/Play button and
    a caption naming it from the registry. No text sits over the footage."""
    c = clip_files(clip_id, need_hero=False)
    E = lambda s: html.escape(s, quote=True)  # noqa: E731
    return (f'<figure class="sv-media" data-clip="{E(clip_id)}">'
            f'<div class="sv-frame">{_clip_video(c, page_path, "sv-video")}</div>'
            f'<figcaption class="sv-cap">{_clip_toggle(labels)}'
            f'<span>{E(clip_caption(c))}</span></figcaption></figure>')


BAND_SCRIM_DARK = 0.88
BAND_SCRIM_LIGHT = 0.92
BAND_CLOSE = '</div></div>'


def band_open(clip_id, page_path, cls=''):
    """Opens a band over a clip; close it with BAND_CLOSE. Words inside sit
    over the footage under a scrim at BAND_SCRIM_DARK / BAND_SCRIM_LIGHT, and
    test_home.mjs --browser measures them over sampled frames like the hero."""
    c = clip_files(clip_id, need_hero=False)
    E = lambda s: html.escape(s, quote=True)  # noqa: E731
    return (f'<div class="vband {E(cls)}" data-band-host data-clip="{E(clip_id)}">'
            f'<div class="hv vb-bg">{_clip_video(c, page_path, "vb-video")}'
            '<div class="hv-scrim vb-scrim"></div></div><div class="vb-inner">')


def band_caption(clip_id, labels=None):
    c = clip_files(clip_id, need_hero=False)
    E = lambda s: html.escape(s, quote=True)  # noqa: E731
    return (f'<div class="hv-bar vb-bar">{_clip_toggle(labels)}'
            f'<p class="hv-cap">{E(clip_caption(c))}</p></div>')


SECTION_VIDEO_CSS = f"""
[data-band-host]{{position:relative;isolation:isolate;overflow:hidden}}
.vb-scrim{{background:rgba(13,19,22,{BAND_SCRIM_DARK})}}
@media (prefers-color-scheme:light){{:root:not([data-theme="dark"]) .vb-scrim{{background:rgba(244,246,245,{BAND_SCRIM_LIGHT})}}}}
:root[data-theme="light"] .vb-scrim{{background:rgba(244,246,245,{BAND_SCRIM_LIGHT})}}
.vband{{margin-block:var(--s8,72px) 0;border-block:1px solid var(--rule)}}
.vb-inner{{max-inline-size:1200px;margin-inline:auto;padding:clamp(48px,8vw,112px) var(--s5,24px);
  text-align:center;display:flex;flex-direction:column;align-items:center;gap:var(--s3,12px)}}
.vb-video,.sv-video{{position:absolute;inset:0;inline-size:100%;block-size:100%;object-fit:cover;display:block}}
.vb-bar{{justify-content:center}}
.showcase{{display:grid;gap:0;border:1px solid var(--rule);border-radius:var(--r-lg,16px);overflow:hidden;
  background:var(--panel)}}
.sv-row{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);align-items:stretch}}
.sv-row + .sv-row{{border-block-start:1px solid var(--rule)}}
.sv-row:nth-child(even) .sv-media{{order:2}}
.sv-media{{margin:0;display:flex;flex-direction:column;background:var(--sunk)}}
.sv-frame{{position:relative;flex:1;min-block-size:clamp(220px,26vw,340px);overflow:hidden;background:var(--sunk)}}
.sv-video{{transition:transform 1.2s cubic-bezier(.2,.7,.3,1)}}
.sv-row:hover .sv-video{{transform:scale(1.035)}}
.sv-cap{{display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px;padding:10px 14px;
  font-size:12.5px;color:var(--muted);border-block-start:1px solid var(--rule)}}
.sv-text{{padding:clamp(24px,4vw,56px);display:flex;flex-direction:column;gap:var(--s3,12px);justify-content:center}}
@media (max-width:800px){{.sv-row{{grid-template-columns:1fr}}.sv-row:nth-child(even) .sv-media{{order:0}}}}
@media (prefers-reduced-motion:reduce){{.sv-video{{transition:none}}.sv-row:hover .sv-video{{transform:none}}}}
"""

SECTION_VIDEO_JS = f"""<script id="sv-js">
/* Section footage. Each clip's sources are attached only when it scrolls
   into view and only when motion is welcome (not under reduced motion, not
   under Save-Data, not below {SMALL_PX}px, not after this reader paused the
   footage on this device); a clip that leaves the view is paused. Every clip
   has its own Pause/Play button, which also records the choice. */
(function () {{
  var clips = [].slice.call(document.querySelectorAll('[data-clip]'));
  if (!clips.length) return;
  var KEY = 'tc-hero-video';
  function pref() {{ try {{ return localStorage.getItem(KEY); }} catch (e) {{ return null; }} }}
  function save(x) {{ try {{ localStorage.setItem(KEY, x); }} catch (e) {{}} }}
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var saveData = !!(navigator.connection && navigator.connection.saveData);
  var small = window.matchMedia('(max-width: {SMALL_PX - 1}px)').matches;
  function parts(el) {{ return {{ v: el.querySelector('video'), b: el.querySelector('[data-clip-toggle]') }}; }}
  function show(el, playing) {{
    var p = parts(el);
    p.b.setAttribute('aria-pressed', playing ? 'false' : 'true');
    p.b.querySelector('.hv-txt').textContent = p.b.getAttribute(playing ? 'data-label-pause' : 'data-label-play');
    el.setAttribute('data-state', playing ? 'playing' : 'paused');
  }}
  function play(el) {{
    var v = parts(el).v;
    if (!v.getAttribute('data-attached')) {{
      v.setAttribute('data-attached', '1');
      v.querySelectorAll('source[data-src]').forEach(function (s) {{ s.src = s.getAttribute('data-src'); }});
      v.load();
    }}
    var p = v.play(); show(el, true);
    if (p && p.catch) p.catch(function () {{ show(el, false); }});
  }}
  function pause(el) {{ parts(el).v.pause(); show(el, false); }}
  var seen = new Map();
  clips.forEach(function (el) {{
    var b = parts(el).b; b.hidden = false; show(el, false);
    b.addEventListener('click', function () {{
      if (parts(el).v.paused) {{ save('play'); play(el); }} else {{ save('paused'); pause(el); }}
    }});
  }});
  if (reduce || saveData || small || !('IntersectionObserver' in window)) return;
  var io = new IntersectionObserver(function (es) {{
    es.forEach(function (e) {{
      if (e.isIntersecting && pref() !== 'paused') play(e.target);
      else if (!e.isIntersecting && !parts(e.target).v.paused) {{ parts(e.target).v.pause(); }}
    }});
  }}, {{ threshold: 0.35 }});
  clips.forEach(function (el) {{ io.observe(el); }});
}}());
</script>"""


# ------------------------------------------------------------ motion ----
# Two small interactions, both honest by construction:
#  - count-up: each figure in a [data-countup] list is already in the page as
#    its final, registry-read value. The script only animates up to that very
#    text and writes the original string back at the end; under reduced
#    motion, or without IntersectionObserver, it never touches the DOM.
#  - scroll reveal: pure CSS (a view() timeline), translate/scale only - no
#    opacity, so nothing is ever hidden from a reader, a screenshot or a
#    check; under reduced motion, or where view() is unsupported, nothing moves.
MOTION_CSS = """
@supports (animation-timeline: view()){@media (prefers-reduced-motion:no-preference){
  .rv{animation:rv-in linear both;animation-timeline:view();animation-range:entry 0% entry 55%}
  @keyframes rv-in{from{translate:0 26px;scale:.985}to{translate:0 0;scale:1}}
}}
"""

COUNTUP_JS = """<script id="countup-js">
/* Count-up for figures that are already on the page. The final value is the
   text the build wrote; this only animates toward it and restores it. */
(function () {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  if (!('IntersectionObserver' in window)) return;
  var els = [].slice.call(document.querySelectorAll('[data-countup] dd'));
  function run(el) {
    var fin = el.textContent;
    if (!/^\\s*\\d[\\d,]*\\s*$/.test(fin)) return;
    var n = +fin.replace(/[,\\s]/g, '');
    if (!isFinite(n) || n < 2) return;
    var t0 = null, D = 900;
    el.setAttribute('data-counting', '');
    function step(ts) {
      if (t0 === null) t0 = ts;
      var k = Math.min(1, (ts - t0) / D), e = 1 - Math.pow(1 - k, 3);
      if (k < 1) { el.textContent = Math.round(n * e).toLocaleString('en-US'); requestAnimationFrame(step); }
      else { el.textContent = fin; el.removeAttribute('data-counting'); }
    }
    requestAnimationFrame(step);
  }
  var io = new IntersectionObserver(function (es) {
    es.forEach(function (e) { if (e.isIntersecting) { io.unobserve(e.target); run(e.target); } });
  }, { threshold: 0.6 });
  els.forEach(function (el) { io.observe(el); });
}());
</script>"""


# -------------------------------------------------- document page heroes ---
# MEDIA's pagehero band on the document pages HOMEUX adopts it on. Every word
# comes from the catalog (hero.<page>.*, hero.credit.<clip>, the landing
# page's pause/play labels, and the linked page's own nav label), so a page
# builder passes keys and a clip id, never prose. The page keeps its own <h1>:
# the band's title is a display line (as_h1=False). These pages are
# dark-only, so they opt into the theme's dark palette on <html>.
DOC_HERO_PAGES = {
    # page key: (page path, clip id, (action nav key, href relative to page, kind))
    'lessons': ('web/trade_craft_lessons.html', 'hall-orbit', ('nav.page.campus', 'trade_craft_3d.html', 'primary')),
    'progress': ('web/trade_craft_progress.html', 'region-board-orbit', ('nav.page.lessons', 'trade_craft_lessons.html', 'ghost')),
    'schools': ('web/trade_craft_schools.html', 'campus-green-low-dolly', ('nav.page.lessons', 'trade_craft_lessons.html', 'ghost')),
    'quests': ('web/trade_craft_quests.html', 'wilds-mountain-flyover', ('nav.page.wilds', 'trade_craft_wilds.html', 'primary')),
    'spaces': ('web/trade_craft_spaces.html', 'hall-orbit', ('nav.page.worksites', 'trade_craft_worksites.html', 'ghost')),
    'contribute': ('web/trade_craft_contribute.html', 'campus-green-low-dolly', ('nav.page.landing', 'trade_craft_landing.html', 'ghost')),
    'dashboard': ('web/trade_craft_dashboard.html', 'region-board-orbit', ('nav.page.map', 'trade_craft_map.html', 'ghost')),
    'fabric': ('web/trade_craft_fabric.html', 'globe-flyover', ('nav.page.geomap', 'trade_craft_geomap.html', 'ghost')),
    'ladder': ('web/trade_craft_ladder.html', 'hall-orbit', ('nav.page.lessons', 'trade_craft_lessons.html', 'primary')),
    'languages': ('web/trade_craft_languages.html', 'campus-green-low-dolly', ('nav.page.landing', 'trade_craft_landing.html', 'ghost')),
}


# How each page remembers the reader's style (THEME_CONTRACT section 6):
#   full - STYLE_HEAD_JS in <head> before any <style>, STYLE_JS after the page's scripts
#   tail - STYLE_JS only: the page's suite reads its FIRST <script> as its own
#          registry payload (web/test_fabric.mjs, web/test_ladder.mjs), so no
#          script may precede it; the stored style is applied once the page loads
#   none - the page's contract forbids any browser storage: the style applies
#          for the visit only. (lessons/test.mjs and web/test_schools.mjs carry a
#          narrow, lead-approved carve-out for localStorage['tc-style'] only.)
STYLE_MEMORY = {'lessons': 'full', 'schools': 'full', 'fabric': 'tail', 'ladder': 'tail',
                'progress': 'full', 'quests': 'full', 'spaces': 'full', 'contribute': 'full',
                'dashboard': 'full', 'languages': 'full'}
assert set(STYLE_MEMORY) == set(DOC_HERO_PAGES), 'herovideo: every document page needs a STYLE_MEMORY entry'


def _catalog_strings(lang):
    import json
    p = ROOT / 'i18n' / 'locales' / f'{lang}.json'
    return json.loads(p.read_text(encoding='utf-8'))['strings']


def doc_hero(key, lang='en', body_class=True):
    """(head_css, hero_html, body_js) for one document page: the pagehero band
    plus the theme('doc') layer. A missing catalog key stops the build."""
    from pagehero import pagehero, theme
    page, clip, (akey, ahref, akind) = DOC_HERO_PAGES[key]
    S = _catalog_strings(lang)

    def s(k):
        if k not in S or not isinstance(S[k], str) or not S[k].strip():
            raise KeyError(f'herovideo.doc_hero({key!r}): i18n/locales/{lang}.json has no string {k!r}')
        return S[k]
    assert (ROOT / 'web' / ahref).is_file(), f'herovideo.doc_hero({key!r}): action target web/{ahref} is not built'
    head_css, hero_html, js = pagehero(page, {
        'clip': clip,
        'kicker': s(f'hero.{key}.kicker'),
        'title': s(f'hero.{key}.title'),
        'accent': s(f'hero.{key}.accent'),
        'accent_style': 'gradient',
        'lede': s(f'hero.{key}.lede'),
        'actions': [{'text': s(akey), 'href': ahref, 'kind': akind}],
        'as_h1': False,
        'labels': {'pause': s('landing.video.pause'), 'play': s('landing.video.play')},
        'credit': s('hero.credit.' + clip.replace('-', '_')),
    })
    tcss, tjs = theme('doc') if body_class else ('', '')
    # an inline <svg> in HTML needs no xmlns; dropping it keeps the pages
    # whose suites forbid any http(s):// text free of one
    hero_html = hero_html.replace(' xmlns="http://www.w3.org/2000/svg"', '')
    return (head_css + '\n' + tcss, hero_html,
            '<script id="ph-js">' + js + '\n' + tjs + '</script>')


def adopt_doc_hero(key, page_html, lang='en', body_class=True):
    """Put the band into an already-assembled page: theme CSS at the end of
    <head>, `tc-theme` on <body> and the dark palette on <html>, the band
    right after the site nav's `#tc-main` skip target, the script before
    </body> (or before the JSON-LD block, which must never be a page's first
script). Each anchor must occur exactly once, or the build stops.
    body_class=False leaves <body> bare (a page whose suite pins `<body>`):
    the band still comes, the theme('doc') layer does not."""
    head_css, hero_html, js = doc_hero(key, lang, body_class)
    import re as _re

    def once(pat, s):
        n = len(_re.findall(pat, s))
        assert n == 1, f'herovideo.adopt_doc_hero({key!r}): {pat!r} occurs {n} times'
    once(r'<html lang="[a-z-]+"', page_html)
    once(r'</head>', page_html)
    once(r'<body\b', page_html)
    once(r'</body>', page_html)
    anchor = '<span id="tc-main" class="sitenav-skip-target" tabindex="-1"></span>'
    assert page_html.count(anchor) == 1, f'herovideo.adopt_doc_hero({key!r}): the site nav skip target is not there exactly once'
    page_html = _re.sub(r'<html lang="([a-z-]+)"', r'<html lang="\1" data-theme="dark"', page_html, count=1)
    page_html = page_html.replace('</head>', f'<style id="ph-css">{head_css}</style>\n</head>', 1)
    # MEDIA's style switcher (THEME_CONTRACT section 6). The nav's radio applies
    # a style for the visit with no script at all; remembering it needs
    # localStorage, which some page contracts forbid - see STYLE_MEMORY.
    from design_kit import STYLE_HEAD_JS
    from sitenav import STYLE_JS
    mem = STYLE_MEMORY[key]
    if mem == 'full':
        head_end = page_html.index('</head>')
        first_style = page_html.find('<style', 0, head_end)
        assert first_style > 0, f'herovideo.adopt_doc_hero({key!r}): no <style> in <head>'
        page_html = (page_html[:first_style] + f'<script id="style-head-js">{STYLE_HEAD_JS}</script>\n'
                     + page_html[first_style:])
    if mem in ('full', 'tail'):
        js = js + f'\n<script id="style-js">{STYLE_JS}</script>'
    if body_class:
        m = _re.search(r'<body\b([^>]*)>', page_html)
        attrs = m.group(1)
        if 'class="' in attrs:
            attrs = attrs.replace('class="', 'class="tc-theme ', 1)
        else:
            attrs += ' class="tc-theme"'
        page_html = page_html[:m.start()] + f'<body{attrs}>' + page_html[m.end():]
    page_html = page_html.replace(anchor, anchor + hero_html, 1)
    ld = '<script type="application/ld+json"'
    n_ld = page_html.count(ld)
    assert n_ld <= 1, f'herovideo.adopt_doc_hero({key!r}): {n_ld} JSON-LD blocks'
    at = ld if n_ld else '</body>'
    return page_html.replace(at, js + '\n' + at, 1)


# ------------------------------------------------------------- styles ----
# The five site-wide styles (design_kit.STYLES, switched from the nav by
# MEDIA's style menu) re-declare the common page tokens (--plate, --panel,
# --ink, --muted, --mark, --steel, ...) with !important on <html>. This
# bridge makes the front door's and the landing page's remaining token
# names follow them, and puts every scrim these pages draw over footage on
# the chosen style's own plate - so a light style gets a light scrim under
# its dark ink and a dark style a dark one. test_home.mjs --browser measures
# the hero text over sampled frames in each of the five styles.
STYLE_SCRIM_DARK = 0.88
STYLE_SCRIM_LIGHT = 0.93


def _style_bridge_css():
    import design_kit as K
    out = []
    for s in K.STYLES:
        i, t = s['id'], s['tokens']
        scopes = [f'html[data-style="{i}"]', f'html:has(input[name="{K.STYLE_KEY}"][value="{i}"]:checked)']
        light = K.contrast(t['plate'], '#FFFFFF') < 2
        r, g, b = (int(t['plate'][k:k + 2], 16) for k in (1, 3, 5))
        a = STYLE_SCRIM_LIGHT if light else STYLE_SCRIM_DARK
        out.append(','.join(scopes) + '{--raise:var(--raised)!important;--dim:var(--muted)!important;'
                   '--rule-2:var(--line)!important;--btn:var(--mark)!important;--btn-ink:var(--mark-ink)!important;'
                   '--btn2:var(--panel)!important;--btn2-ink:var(--ink)!important;--hero:var(--plate)!important;'
                   '--steel-ink:var(--link)!important;--focus:0 0 0 3px var(--plate),0 0 0 5px var(--link)!important;'
                   f'color-scheme:{"light" if light else "dark"}}}')
        out.append(','.join(f'{sc} :is(.hv-scrim,.vb-scrim)' for sc in scopes)
                   + f'{{background:rgba({r},{g},{b},{a})!important}}')
    return '\n'.join(out) + '\n'


STYLE_BRIDGE_CSS = _style_bridge_css()
