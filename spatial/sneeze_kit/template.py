#!/usr/bin/env python3
"""
Make the results file for a run, pre-filled from a passing pre-flight report, or print the
checklist's expectation table.

  python3 spatial/sneeze_kit/preflight.py --out preflight.json
  python3 spatial/sneeze_kit/template.py --preflight preflight.json --out my-run.json
  python3 spatial/sneeze_kit/template.py --guide            # what each tile should look like (sizes, directions)

The template carries "FILL IN" placeholders and every observation set to "untested". ingest.py
refuses a file that still has a placeholder where a person, version, date or OS belongs, so an
unfilled template can never be recorded. Observations you did not make stay "untested".
"""
import argparse
import json
import pathlib
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _common as C  # noqa: E402


def compass(dx, dy):
    ew = 'east' if dx >= 0 else 'west'
    ns = 'north' if dy >= 0 else 'south'
    return f'{abs(dx) / 1000:.1f} km {ew}, {abs(dy) / 1000:.1f} km {ns}'


def build_template(tiles, preflight, repo_commit=None, only=None):
    ids = [m['id'] for m in tiles['manifests'] if not only or m['id'] in only]
    mans = []
    for m in tiles['manifests']:
        if m['id'] not in ids:
            continue
        n = len(m['tiles'])
        obs = []
        for tid in m['tiles']:
            obs.append({'tile': tid, 'appears': 'untested', 'orientation': 'untested', 'scale': 'untested',
                        'child_position': 'not_applicable' if n == 1 else 'untested', 'smooth': 'untested', 'notes': '', 'screenshots': []})
        mans.append({'id': m['id'], 'loaded': 'untested', 'geopose_anchor_read': 'untested', 'notes': '', 'screenshots': [], 'tiles': obs})
    return {
        'schema': 'smartcitix-sneeze-run/1',
        'person': {'name': 'FILL IN your name or public handle'},
        'date': 'FILL IN YYYY-MM-DD',
        'engine': {'name': 'FILL IN Sneeze or Artemis', 'version': 'FILL IN (Artemis release, or Sneeze build)',
                   'commit': 'FILL IN the Sneeze git commit hash (or delete this line)', 'installed_from': 'FILL IN source/installer/package/other'},
        'os': {'name': 'FILL IN e.g. Windows / macOS / Ubuntu', 'version': 'FILL IN', 'arch': '', 'gpu': ''},
        'build': {'repo_commit': repo_commit or 'FILL IN git rev-parse HEAD of this repository', 'tiles_source_stamp': tiles['source_stamp']},
        'preflight': {'passed': bool(preflight.get('passed')), 'tiles_source_stamp': preflight.get('tiles_source_stamp'),
                      'manifest_sha256': {k: v for k, v in sorted(preflight.get('manifest_sha256', {}).items()) if k in ids},
                      'tile_sha256': dict(sorted(preflight.get('tile_sha256', {}).items()))},
        'serve': {'map_module': 'rp1-cdn', 'manifest_variant': 'as-built'},
        'manifests': mans,
        'fields': [{'field': r['field'], 'verdict': 'untested', 'evidence': '', 'screenshots': []}
                   for r in tiles['field_status'] if r['status'] == 'proposed'],
        'screenshots': [],
        'notes': '',
    }


def guide(tiles):
    by = {t['id']: t for t in tiles['tiles']}
    out = ['# What each tile should look like (computed from spatial/registry/tiles.json)', '',
           'Sizes are the recorded tile bounding box. Directions assume the usual map layout (east to the right, north up the screen when you look down from above); whether Sneeze\'s own axes agree is exactly what the checklist asks you to observe.', '']
    for m in tiles['manifests']:
        out += [f'## {m["id"]}  ({m["title"]})', '',
                'tile | name | east-west km | north-south km | height m | sits (relative to first tile) | bytes',
                '--- | --- | ---: | ---: | ---: | --- | ---']
        r0 = by[m['tiles'][0]].get('world_m')
        for i, tid in enumerate(m['tiles']):
            t = by[tid]
            e, u, n = C.kilometres(t)
            if r0 and t.get('world_m'):
                sits = 'first tile (its recorded position is ' + compass(*t['world_m']) + ' of the world origin)' if i == 0 else compass(t['world_m'][0] - r0[0], t['world_m'][1] - r0[1])
            else:
                sits = 'alone, at the origin'
            out.append(f'{tid} | {t["name"]} | {e:.1f} | {n:.1f} | {u * 1000:.1f} | {sits} | {t["bytes"]:,}')
        out.append('')
    return '\n'.join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Pre-filled results file, or the expectation table.')
    ap.add_argument('--registry', default=None)
    ap.add_argument('--preflight', default=None, help='the JSON written by preflight.py --out')
    ap.add_argument('--manifests', default=None, help='comma-separated manifest ids to include (default: all)')
    ap.add_argument('--repo-commit', default=None, help='your checkout\'s commit hash (default: asks git, else FILL IN)')
    ap.add_argument('--out', default=None, help='write here instead of stdout')
    ap.add_argument('--guide', action='store_true', help='print the expectation table and stop')
    a = ap.parse_args(argv)
    tiles = C.load_tiles(a.registry)
    if a.guide:
        print(guide(tiles))
        return 0
    if not a.preflight:
        print('template.py: give --preflight <file> (run preflight.py --out <file> first); a run is only recordable from a passing pre-flight', file=sys.stderr)
        return 2
    pf = C.load_json(a.preflight)
    if not pf.get('passed'):
        print('template.py: that pre-flight did not pass; fix the build (python3 spatial/build.py) and run preflight.py again', file=sys.stderr)
        return 1
    if pf.get('tiles_source_stamp') != tiles['source_stamp']:
        print('template.py: the pre-flight was made against a different build than spatial/registry/tiles.json; run it again', file=sys.stderr)
        return 1
    commit = a.repo_commit
    if not commit:
        try:
            commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=C.ROOT, capture_output=True, text=True, timeout=10).stdout.strip() or None
        except (OSError, subprocess.SubprocessError):
            commit = None
    only = set(a.manifests.split(',')) if a.manifests else None
    doc = build_template(tiles, pf, commit, only)
    text = json.dumps(doc, indent=2) + '\n'
    if a.out:
        pathlib.Path(a.out).write_text(text)
        print(f'wrote {a.out}: fill in the FILL IN lines and your observations, then: python3 spatial/sneeze_kit/ingest.py {a.out}', file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
