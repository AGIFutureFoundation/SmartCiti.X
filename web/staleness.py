"""One staleness guard for every page a builder under web/ writes.

`--check` composes the page exactly as a build would, compares it with the
file the last build wrote, and fails on any difference; without the flag the
builder writes. The Pages workflow deploys committed pages and builds
nothing, so a committed page that lags its registry is precisely what would
ship: the interactive map carried nine campuses for a build that emitted
ten until this guard existed. Same rule as wiki/build_wiki.py --check, held
in one place rather than copied into eight builders.
"""
import pathlib
import sys


def emit(out, page, summary='', encoding=None):
    out = pathlib.Path(out)
    builder = pathlib.Path(sys.argv[0]).name
    if '--check' in sys.argv:
        have = out.read_text(encoding=encoding) if out.exists() else None
        if have != page:
            print(f'STALE: web/{out.name}')
            print(f'       run: python3 web/{builder}')
            sys.exit(1)
        print(f'web/{out.name} is current')
        return
    out.write_text(page, encoding=encoding)
    print(f'written: {len(page):,} bytes' + (f' | {summary}' if summary else ''))
