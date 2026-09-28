#!/usr/bin/env python3
"""Grade and encode rendered frames into the b-roll files.

  python3 media/encode.py --frames <dir-of-clip-dirs> --commit <sha> --source archive|worktree [ids...]

For each clip in media/shots.json whose frames are all present
(<frames>/<id>/f0000.png ...), writes into web/media/broll/:

  <id>.webm         VP9, full size, the file browsers here can play
  <id>.mp4          H.264 (High, yuv420p, faststart), the same picture
  <id>-poster.jpg   the middle frame, graded, for the <video poster>
  <id>-480.webm     a 480 px wide preview

The grade is the same on every clip and deliberately gentle: a soft
S-curve, a touch of saturation, and a subtle vignette. Each full-size file
must come in at or under BUDGET bytes; the encoder steps its quality down
until it does, and stops the build by name if it cannot.

It also records, per clip, the commit the frames were rendered from in
media/renders.json - media/build.py reads that for the provenance line.
"""
import argparse
import json
import pathlib
import subprocess
import datetime

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / 'web' / 'media' / 'broll'
SHOTS = json.loads((HERE / 'shots.json').read_text())
BUDGET = 3 * 1024 * 1024
GRADE = ("curves=m='0/0 0.22/0.19 0.5/0.5 0.78/0.82 1/1',"
         "eq=saturation=1.07:contrast=1.03,vignette=angle=PI/6")


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f'ffmpeg failed: {" ".join(cmd[:6])} ...\n{r.stderr[-800:]}')


def enc(src, fps, out, codec, q, scale=None):
    vf = GRADE + (f',scale={scale}:-2:flags=lanczos' if scale else '')
    base = ['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(fps), '-i', str(src / 'f%04d.png'),
            '-vf', vf, '-an']
    if codec == 'vp9':
        base += ['-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', str(q), '-row-mt', '1',
                 '-deadline', 'good', '-cpu-used', '2', '-pix_fmt', 'yuv420p']
    else:
        base += ['-c:v', 'libx264', '-crf', str(q), '-preset', 'slow', '-profile:v', 'high',
                 '-pix_fmt', 'yuv420p', '-movflags', '+faststart']
    run(base + [str(out)])


def fit(src, fps, out, codec, q0, step, qmax):
    q = q0
    while True:
        enc(src, fps, out, codec, q)
        if out.stat().st_size <= BUDGET:
            return q
        q += step
        if q > qmax:
            raise SystemExit(f'{out.name}: cannot fit {BUDGET} bytes even at q={qmax}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--frames', required=True)
    ap.add_argument('--commit', required=True)
    ap.add_argument('--source', required=True, choices=['archive', 'worktree'],
                    help='frames shot from a git archive of --commit, or from the working tree')
    ap.add_argument('ids', nargs='*')
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rpath = HERE / 'renders.json'
    renders = json.loads(rpath.read_text()) if rpath.exists() else {}
    fps = SHOTS['fps']
    for c in SHOTS['clips']:
        if a.ids and c['id'] not in a.ids:
            continue
        n = round(c['seconds'] * fps)
        src = pathlib.Path(a.frames) / c['id']
        have = sorted(src.glob('f*.png')) if src.is_dir() else []
        if len(have) != n:
            print(f'skip {c["id"]}: {len(have)}/{n} frames')
            continue
        qv = fit(src, fps, OUT / f'{c["id"]}.webm', 'vp9', 34, 3, 52)
        qh = fit(src, fps, OUT / f'{c["id"]}.mp4', 'h264', 24, 2, 36)
        mid = have[len(have) // 2]
        run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(mid), '-vf', GRADE, '-q:v', '3',
             str(OUT / f'{c["id"]}-poster.jpg')])
        enc(src, fps, OUT / f'{c["id"]}-480.webm', 'vp9', 38, scale=480)
        renders[c['id']] = {'commit': a.commit, 'source': a.source, 'frames': n, 'vp9_crf': qv, 'h264_crf': qh,
                            'encoded': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')}
        sizes = {k: (OUT / f'{c["id"]}{k}').stat().st_size for k in ('.webm', '.mp4', '-poster.jpg', '-480.webm')}
        print(c['id'], sizes)
    rpath.write_text(json.dumps(renders, indent=1, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
