#!/usr/bin/env python3
"""Build the b-roll registry — media/registry/media.json.

The library is house-made: every clip is RENDERED FROM THIS BUILD's own
pages (media/record.mjs drives the page's camera hook frame by frame;
media/encode.py grades and encodes). Nothing is stock from elsewhere, so
the licence of every clip is first-party.

Each registry entry names the clip, what it shows, the page and view it
was filmed on, the camera move, its duration and resolution, every file's
bytes and sha256, and a provenance line carrying the commit the frames
were rendered from (media/renders.json, written by the encoder). A clip
filmed from the working tree rather than a git archive of a commit is
marked "work in progress": the render record states which (`source`:
"archive" or "worktree"), so the build reads a fact written when the frames
were shot instead of asking git, and gives the same bytes in any checkout.

Beside the clips the registry holds the stills and the explainer video, whose
facts are authored in media/library.json (capture commit and viewport, the
page and view each still shows, the explainer's duration and provenance).
Every file is hashed; the capture is RECORDED and the explainer is composed
from that footage (DERIVED); both say so in the registry and the test holds
the sentences exactly.

Fail closed: a clip in shots.json with any file missing is not silently
left out - it is listed under `pending` with the reason, and test.mjs
decides whether that is allowed (it is not for a hero clip).
"""
import hashlib
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
BROLL = ROOT / 'web' / 'media' / 'broll'
SHOTS = json.loads((HERE / 'shots.json').read_text())
RENDERS_P = HERE / 'renders.json'
RENDERS = json.loads(RENDERS_P.read_text()) if RENDERS_P.exists() else {}
LIB = json.loads((HERE / 'library.json').read_text())
STILLS = ROOT / 'web' / 'media' / 'stills'
EXPLAINER = ROOT / 'web' / 'media' / 'explainer'
BUDGET = 3 * 1024 * 1024
KINDS = [('webm', '.webm', 'video/webm; codecs=vp9'), ('mp4', '.mp4', 'video/mp4; codecs=avc1'),
         ('poster', '-poster.jpg', 'image/jpeg'), ('preview', '-480.webm', 'video/webm; codecs=vp9')]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def jpeg_size(p):
    """(width, height) read from the JPEG's own SOF marker; refuses a non-JPEG."""
    b = p.read_bytes()
    if b[:2] != b'\xff\xd8' or b[-2:] != b'\xff\xd9':
        raise SystemExit(f'media/build.py: {p.name} is not a JPEG')
    i = 2
    while i + 9 < len(b):
        if b[i] != 0xFF:
            raise SystemExit(f'media/build.py: {p.name} has a malformed JPEG header')
        m = b[i + 1]
        n = int.from_bytes(b[i + 2:i + 4], 'big')
        if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
            return int.from_bytes(b[i + 7:i + 9], 'big'), int.from_bytes(b[i + 5:i + 7], 'big')
        i += 2 + n
    raise SystemExit(f'media/build.py: {p.name} has no frame header')


def mp4_seconds(p):
    """Duration in seconds from the movie header (moov/mvhd) of an MP4."""
    b = p.read_bytes()
    k = b.find(b'mvhd')
    if k < 4:
        raise SystemExit(f'media/build.py: {p.name} has no movie header')
    o = k + 4
    ver = b[o]
    if ver == 1:
        scale, dur = int.from_bytes(b[o + 20:o + 24], 'big'), int.from_bytes(b[o + 24:o + 32], 'big')
    else:
        scale, dur = int.from_bytes(b[o + 12:o + 16], 'big'), int.from_bytes(b[o + 16:o + 20], 'big')
    if not scale:
        raise SystemExit(f'media/build.py: {p.name} has a zero timescale')
    return round(dur / scale, 3)


def lib_need(d, keys, where):
    for k in keys:
        if k not in d:
            raise SystemExit(f'media/library.json: {where} lacks {k}')


def library():
    """The stills and the explainer, from media/library.json and the files."""
    lib_need(LIB, ('capture', 'stills', 'explainer'), 'the file')
    cap = LIB['capture']
    lib_need(cap, ('commit', 'viewport', 'tool', 'provenance'), 'capture')
    stills = []
    for s in LIB['stills']:
        lib_need(s, ('id', 'file', 'page', 'view', 'caption'), 'a still')
        p = STILLS / s['file']
        if not p.is_file():
            raise SystemExit(f"media/build.py: still {s['id']} has no file web/media/stills/{s['file']}")
        w, h = jpeg_size(p)
        stills.append({'id': s['id'], 'source': {'page': s['page'], 'view': s['view']}, 'caption': s['caption'],
                       'file': {'path': f"web/media/stills/{p.name}", 'bytes': p.stat().st_size,
                                'sha256': sha(p), 'type': 'image/jpeg', 'width': w, 'height': h},
                       'provenance': cap['provenance'], 'licence': 'first-party'})
    on_disk = sorted(q.name for q in STILLS.iterdir())
    named = sorted(s['file'] for s in LIB['stills'])
    if on_disk != named:
        raise SystemExit('media/build.py: web/media/stills holds files library.json does not name: '
                         + ', '.join(sorted(set(on_disk) ^ set(named))))
    e = LIB['explainer']
    lib_need(e, ('id', 'title', 'seconds', 'resolution', 'fps', 'audio', 'provenance', 'composition',
                 'files', 'budget_bytes', 'format_note', 'figures_note'), 'explainer')
    lib_need(e['files'], ('mp4', 'poster', 'captions'), 'explainer.files')
    files = {}
    for kind, mime in (('mp4', 'video/mp4; codecs=avc1'), ('poster', 'image/jpeg'), ('captions', 'text/plain; charset=utf-8')):
        p = EXPLAINER / e['files'][kind]
        if not p.is_file():
            raise SystemExit(f"media/build.py: explainer {kind} is missing: web/media/explainer/{e['files'][kind]}")
        files[kind] = {'path': f"web/media/explainer/{p.name}", 'bytes': p.stat().st_size, 'sha256': sha(p), 'type': mime}
    if sorted(q.name for q in EXPLAINER.iterdir()) != sorted(e['files'].values()):
        raise SystemExit('media/build.py: web/media/explainer holds files library.json does not name')
    lines = [x for x in (EXPLAINER / e['files']['captions']).read_text().splitlines() if x.strip()]
    ex = {k: e[k] for k in ('id', 'title', 'fps', 'audio', 'provenance', 'composition', 'budget_bytes',
                            'format_note', 'figures_note')}
    ex.update({'duration_s': e['seconds'], 'measured_duration_s': mp4_seconds(EXPLAINER / e['files']['mp4']),
               'resolution': e['resolution'], 'caption_lines': len(lines), 'files': files,
               'licence': 'first-party'})
    return cap, stills, ex


MEASURE_W = 400


def brightest(webm):
    """The channel-wise maximum over EVERY pixel of EVERY frame of the clip
    (decoded at MEASURE_W px wide) - an upper bound on any colour a scrim
    will ever sit over. web/pagehero.py composites its scrim over this and
    asserts the text contrast against the result, so the check is measured
    from the footage itself, not assumed."""
    r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', str(webm), '-vf', f'scale={MEASURE_W}:-2',
                        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True)
    if r.returncode != 0 or not r.stdout:
        raise SystemExit(f'media/build.py: cannot decode {webm.name} to measure it')
    mx = [0, 0, 0]
    data = r.stdout
    for ch in range(3):
        mx[ch] = max(data[ch::3])
    frames = len(data) // 3
    return '#%02X%02X%02X' % tuple(mx), frames


def build():
    clips, pending = [], []
    for c in SHOTS['clips']:
        for k in ('id', 'title', 'shows', 'page', 'view', 'move', 'seconds', 'hero', 'known_issue'):
            if k not in c:
                raise SystemExit(f'shots.json: clip lacks {k}')
        files = {}
        missing = []
        for kind, suf, mime in KINDS:
            p = BROLL / f"{c['id']}{suf}"
            if not p.exists():
                missing.append(p.name)
                continue
            files[kind] = {'path': f"web/media/broll/{p.name}", 'bytes': p.stat().st_size,
                           'sha256': sha(p), 'type': mime}
        if missing or c['id'] not in RENDERS:
            pending.append({'id': c['id'], 'why': 'not rendered yet: ' + ', '.join(missing or ['no render record'])})
            continue
        r = RENDERS[c['id']]
        if 'source' not in r or r['source'] not in ('archive', 'worktree'):
            raise SystemExit(f"media/renders.json: {c['id']} lacks source (archive|worktree)")
        wip = r['source'] == 'worktree'
        bright, px = brightest(BROLL / f"{c['id']}.webm")
        prov = f"RECORDED from this build (commit {r['commit'][:12]})"
        if wip:
            prov = f"RECORDED from the working tree, work in progress (page not committed; base commit {r['commit'][:12]})"
        clips.append({
            'id': c['id'], 'title': c['title'], 'shows': c['shows'],
            'source': {'page': c['page'], 'view': c['view']},
            'camera_move': c['move'], 'duration_s': c['seconds'], 'fps': SHOTS['fps'],
            'frames': r['frames'], 'resolution': [SHOTS['width'], SHOTS['height']],
            'preview_width': 480, 'hero': c['hero'], 'known_issue': c['known_issue'], 'status': 'work in progress' if wip else 'committed source',
            'files': files, 'provenance': prov, 'licence': 'first-party',
            'grade': 'soft S-curve, saturation 1.07, contrast 1.03, vignette PI/6 (media/encode.py GRADE)',
            'encoded': r['encoded'],
            'measured': {'brightest_rgb': bright, 'pixels': px,
                         'how': f'channel-wise max over every pixel of every frame of the webm, decoded at {MEASURE_W} px wide'},
        })
    cap, stills, ex = library()
    stamp_src = b''.join((HERE / f).read_bytes() for f in ('shots.json', 'record.mjs', 'encode.py', 'build.py', 'library.json'))
    doc = {
        'what': 'The b-roll library: house-made footage filmed frame by frame from this build\'s own 3D '
                'campus and globe map. No third-party stock; every clip is first-party.',
        'how': 'media/record.mjs (virtual clock, camera driven through the page hook, one screenshot per '
               'frame) -> media/encode.py (grade, VP9 + H.264, poster, 480 px preview) -> media/build.py',
        'budget_bytes': BUDGET, 'fps': SHOTS['fps'],
        'source_stamp': hashlib.sha256(stamp_src).hexdigest(),
        'clips': clips, 'pending': pending,
        'capture': cap, 'stills': stills, 'explainer': ex,
    }
    out = HERE / 'registry' / 'media.json'
    out.parent.mkdir(exist_ok=True)
    text = json.dumps(doc, indent=1) + '\n'
    if '--check' in sys.argv:
        if not out.exists() or out.read_text() != text:
            raise SystemExit('STALE: media/registry/media.json - run python3 media/build.py')
        print('media/registry/media.json is current')
        return
    out.write_text(text)
    print(f'media: {len(clips)} clips, {len(pending)} pending, {len(stills)} stills, 1 explainer, stamp {doc["source_stamp"][:16]}')
    for c in clips:
        print(f"  {c['id']:24} {c['duration_s']:>3}s  webm {c['files']['webm']['bytes']:>8}  mp4 {c['files']['mp4']['bytes']:>8}")


if __name__ == '__main__':
    build()
