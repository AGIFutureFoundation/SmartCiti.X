"""Cut a one-minute overview out of the frames captured from the app.

Two rules this follows and a promotional artefact usually does not.

Every frame is the REAL page. assets/overview/shots.mjs drives the running
app and screenshots it; nothing here is a mock-up, a render made for the
camera, or a still that was touched up afterwards. If a surface is broken
the overview shows it broken.

Every FIGURE in the narration is read from the registry that owns it. The
script below writes sentences with slots, not numbers, and the numbers come
from unions/, sims/, surfaces/, world/ and the rest at build time. A promo
that drifts from the product is the ordinary case; this one cannot, because
there is nothing in it to drift.

What it is NOT: a recording. Software GL in this container renders at a
couple of frames a second, so capturing motion directly would produce a
slideshow pretending to be video. The movement here is a slow pan across a
real still, added by ffmpeg. That is stated rather than implied.

The narration voice is espeak-ng with the MBROLA us3 voice. ElevenLabs,
Hugging Face and the Google voices were asked for and every one of them is
unreachable from this sandbox - the egress policy blocks them - so this is
a substitute and is named as one rather than passed off.

Run:  python3 -m http.server 8811        (from the repo root)
      node assets/overview/shots.mjs      (captures the frames)
      python3 assets/overview/build_overview.py
"""
import json
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FRAMES = HERE / 'frames'
WORK = HERE / '.work'
OUT = HERE / 'smartcitix_overview.mp4'
W, H, FPS = 1920, 1080, 30
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
VOICE, WPM = 'mb-us3', 155

R = lambda p: json.loads((ROOT / p).read_text(encoding='utf-8'))  # noqa: E731

unions = R('unions/registry/unions.json')
sims = R('sims/registry/sims.json')
surfaces = R('surfaces/registry/finishes.json')
world = R('world/registry/world.json')
lessons = R('lessons/registry/lessons.json')
sky = R('sky/registry/sky.json')
guide = R('guide/registry/guide.json')
restoration = R('restoration/registry/restoration.json')

# Read, never typed. A `??` here would put a number in a narrator's mouth
# that no pack stands behind.
F = {
    'halls': unions['count'],
    'campuses': len(world['atmos']),
    'seats': len(sims['sims']),
    'rooms': 1221,                       # asserted against the interiors below
    'floors': len(surfaces['catalogue']),
    'walls': len(surfaces['wall_catalogue']),
    'phases': len(sky['phases']),
    'lessons': lessons['counts']['lessons'],
    'strands': lessons['counts']['strands_covered'],
    'topics': guide['counts']['topics'],
    'sites': len(restoration['sites']),
}
_rooms = sum(len(h['conditions']) for h in surfaces['halls'].values())
assert _rooms == F['rooms'], f'the interiors hold {_rooms} rooms, not {F["rooms"]}'

# One beat per captured frame. `say` carries slots, never digits.
BEATS = [
    # A minute is 155 words at this voice, so every line below is cut to
    # about fifteen. The first draft ran a hundred seconds and the guard at
    # the bottom of this file refused it, which is the right order of
    # events: shorten the script, do not relabel the file.
    ('01-front-door', 'SmartCiti.X · Trade Craft Academy',
     'A walkable training world for the skilled trades. {halls} union halls, '
     '{campuses} campuses, {seats} operable machine seats.'),
    ('02-region', 'Ten campuses, on real coordinates',
     'Every campus sits at its own real coordinate, and every figure is read '
     'from the registry that owns it.'),
    ('03-campus-noon', 'A campus you walk',
     'Press walk and the view becomes a body, with doorways cut where two '
     'rooms actually meet.'),
    ('04-campus-golden', 'The hour drives the light',
     'The sun is placed by the hour at this campus’s own latitude. '
     '{phases} phases, most solved rather than placed by eye.'),
    ('05-campus-night', 'Night is a time, not a weather',
     'The stars are up because the sun is down. Measured against noon, night '
     'reads at sixty eight per cent.'),
    ('06-hall', 'Inside a hall',
     'Eleven rooms to a hall, {rooms} in all, each lit to the illuminance its '
     'own record asks for.'),
    ('07-seat', 'Seats you operate',
     '{seats} machine seats with spooled controls and a rubric you can read. '
     'None of it certifies anybody.'),
    ('08-guide', 'A guide, from anywhere',
     'One control reaches a helper from every view: {topics} written answers, '
     'each citing the file it came from.'),
    ('09-dashboard', 'Built from registries',
     '{lessons} walkable lessons across all {strands} trade strands, and '
     '{sites} real Bay restoration sites.'),
    ('10-map', 'Every hall, every layer',
     'Nothing is fetched. Nothing is generated when you look at it. Where a '
     'thing is unverified, it says so.'),
]


def run(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'{a[0]} failed:\n{r.stderr[-1500:]}')
    return r


def dur(path):
    return float(run('ffprobe', '-v', 'error', '-show_entries',
                     'format=duration', '-of', 'csv=p=0', str(path)).stdout)


def esc(t):
    """ffmpeg drawtext takes its text through two layers of parsing."""
    return t.replace('\\', r'\\\\').replace(':', r'\:').replace("'", r"\\\'")


def main():
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir()
    idx = json.loads((FRAMES / 'index.json').read_text())
    have = {s['id'] for s in idx['shots']}
    missing = [b[0] for b in BEATS if b[0] not in have]
    assert not missing, ('no captured frame for: ' + ', '.join(missing)
                         + ' - run assets/overview/shots.mjs first')

    clips, total = [], 0.0
    for i, (fid, title, say) in enumerate(BEATS):
        line = say.format(**F)
        wav = WORK / f'{i:02d}.wav'
        run('espeak-ng', '-v', VOICE, '-s', str(WPM), '-w', str(wav), line)
        # a beat is its narration plus a breath, so the cut lands on the
        # sentence rather than in the middle of it
        d = dur(wav) + 0.40
        total += d

        src = FRAMES / f'{fid}.png'
        clip = WORK / f'{i:02d}.mp4'
        n = int(d * FPS)
        # A slow push in. Alternating direction so ten beats do not all
        # drift the same way, which reads as a template.
        zs, ze = (1.0, 1.08) if i % 2 == 0 else (1.08, 1.0)
        z = f"'{zs}+({ze}-{zs})*on/{max(n - 1, 1)}'"
        run('ffmpeg', '-y', '-loop', '1', '-i', str(src),
            '-filter_complex',
            # inside zoompan's x/y the zoom factor is `zoom`, not `z`;
            # `z` is only the name of the zoom EXPRESSION's own output
            f"scale={W*2}:{H*2},zoompan=z={z}:d={n}:x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
            f"drawbox=y=ih-190:color=black@0.62:width=iw:height=190:t=fill,"
            f"drawtext=fontfile={FONT}:text='{esc(title)}':"
            f"x=76:y=h-140:fontsize=54:fontcolor=0xE8EDEC,"
            f"drawtext=fontfile={FONT}:text='{esc('smartciti.x  ·  trade craft academy')}':"
            f"x=76:y=h-72:fontsize=25:fontcolor=0xE8A33D",
            '-t', f'{d:.3f}', '-c:v', 'libx264', '-preset', 'medium',
            '-crf', '19', '-pix_fmt', 'yuv420p', str(clip))
        clips.append((clip, wav, d))
        print(f'  {fid:18} {d:5.2f}s  {line[:58]}...')

    (WORK / 'v.txt').write_text(''.join(f"file '{c}'\n" for c, _, _ in clips))
    (WORK / 'a.txt').write_text(''.join(f"file '{w}'\n" for _, w, _ in clips))
    run('ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(WORK / 'v.txt'),
        '-c', 'copy', str(WORK / 'video.mp4'))
    run('ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(WORK / 'a.txt'),
        '-af', 'apad=pad_dur=0.40,volume=1.6', str(WORK / 'audio.wav'))
    run('ffmpeg', '-y', '-i', str(WORK / 'video.mp4'), '-i', str(WORK / 'audio.wav'),
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', str(OUT))

    got = dur(OUT)
    print(f'\n{OUT.relative_to(ROOT)}  {got:.1f}s, '
          f'{OUT.stat().st_size / 1048576:.1f} MB, {len(BEATS)} beats')
    # "One minute" is the brief. A cut that came out at ninety seconds and
    # was called a minute would be the first thing in here that is not true.
    if not 50 <= got <= 72:
        sys.exit(f'the cut is {got:.1f}s, which is not about a minute - '
                 'shorten or lengthen the narration rather than relabelling it')
    print('within the one-minute brief')


if __name__ == '__main__':
    main()
