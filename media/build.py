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
BUDGET = 3 * 1024 * 1024
KINDS = [('webm', '.webm', 'video/webm; codecs=vp9'), ('mp4', '.mp4', 'video/mp4; codecs=avc1'),
         ('poster', '-poster.jpg', 'image/jpeg'), ('preview', '-480.webm', 'video/webm; codecs=vp9')]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


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
    stamp_src = b''.join((HERE / f).read_bytes() for f in ('shots.json', 'record.mjs', 'encode.py', 'build.py'))
    doc = {
        'what': 'The b-roll library: house-made footage filmed frame by frame from this build\'s own 3D '
                'campus and globe map. No third-party stock; every clip is first-party.',
        'how': 'media/record.mjs (virtual clock, camera driven through the page hook, one screenshot per '
               'frame) -> media/encode.py (grade, VP9 + H.264, poster, 480 px preview) -> media/build.py',
        'budget_bytes': BUDGET, 'fps': SHOTS['fps'],
        'source_stamp': hashlib.sha256(stamp_src).hexdigest(),
        'clips': clips, 'pending': pending,
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
    print(f'media: {len(clips)} clips, {len(pending)} pending, stamp {doc["source_stamp"][:16]}')
    for c in clips:
        print(f"  {c['id']:24} {c['duration_s']:>3}s  webm {c['files']['webm']['bytes']:>8}  mp4 {c['files']['mp4']['bytes']:>8}")


if __name__ == '__main__':
    build()
