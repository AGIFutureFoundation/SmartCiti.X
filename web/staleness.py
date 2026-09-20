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


def _shown(out):
    """The path as a reader would type it, not a guess.

    Every builder under web/ used to write into web/, so the name was
    prefixed with 'web/' literally. build_home.py writes index.html at the
    repo root, and a staleness message that points at web/index.html sends
    a reader to a file that does not exist. So the displayed path is derived
    from where the file actually is, relative to the repo root.
    """
    root = pathlib.Path(__file__).resolve().parent.parent
    try:
        return out.resolve().relative_to(root).as_posix()
    except ValueError:
        return out.name


def emit(out, page, summary='', encoding=None):
    out = pathlib.Path(out)
    builder = pathlib.Path(sys.argv[0]).name
    shown = _shown(out)
    if '--check' in sys.argv:
        have = out.read_text(encoding=encoding) if out.exists() else None
        if have != page:
            print(f'STALE: {shown}')
            print(f'       run: python3 web/{builder}')
            sys.exit(1)
        print(f'{shown} is current')
        return
    out.write_text(page, encoding=encoding)
    print(f'written: {len(page):,} bytes' + (f' | {summary}' if summary else ''))
