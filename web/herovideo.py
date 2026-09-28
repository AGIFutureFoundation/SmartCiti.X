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


def _hero_clip():
    import hashlib
    import json
    reg = json.loads((ROOT / MEDIA_PATH).read_text(encoding='utf-8'))
    hits = [c for c in reg['clips'] if c['id'] == HERO_CLIP_ID]
    assert len(hits) == 1, f'herovideo: {MEDIA_PATH} holds {len(hits)} clips with id {HERO_CLIP_ID!r}'
    clip = hits[0]
    assert clip['hero'] is True, f'herovideo: {MEDIA_PATH}#{HERO_CLIP_ID} is not registered hero=true'
    out = {}
    for k in ('webm', 'mp4', 'poster'):
        f = clip['files'][k]
        data = (ROOT / f['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == f['sha256'], \
            f'herovideo: {f["path"]} no longer matches {MEDIA_PATH}#{HERO_CLIP_ID}.files.{k}.sha256'
        out[k] = f['path']
    out['source_page'] = clip['source']['page']
    out['provenance'] = clip['provenance']
    return out


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
