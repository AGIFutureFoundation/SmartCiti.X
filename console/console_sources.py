"""The single declaration of what the console inlines.

Both the builder and the freshness check import this. They used to declare the
list separately, and the two copies drifted the moment the bus pack was added:
the checker hashed a stale set and reported the wrong stamp. That is defect 11's
shape again — a freshness check is only as good as its idea of what "the
sources" are — so there is now exactly one idea of it.
"""
import hashlib
import pathlib

SOURCES = [
    'control/lpa.mjs', 'control/dial.mjs', 'control/graph.mjs',
    'control/hints.mjs', 'control/sequencer.mjs', 'control/gates.mjs',
    'fabric/agent.mjs', 'fabric/stubs.mjs',
    'bus/bus.mjs', 'bus/audit.mjs', 'bus/telemetry.mjs', 'bus/safeguards.mjs', 'bus/session.mjs',
]

def repo_root():
    """The directory that holds the protocol packs.

    Resolved by walking up from this file rather than trusting the working
    directory: the builder sits beside the console in the packaged bundle but
    at the top level in the working tree, and a stamp keyed to cwd silently
    hashes the wrong files (or none) from the other layout. Same shape as the
    v2.6 registry-path defect — a path that only resolves from one directory.
    """
    here = pathlib.Path(__file__).resolve().parent
    for cand in (here, *here.parents):
        if (cand / 'control').is_dir() and (cand / 'bus').is_dir():
            return cand
    raise RuntimeError('cannot locate the pack root from ' + str(here))


def console_html():
    """The built console page, wherever this checkout keeps it."""
    root = repo_root()
    for cand in (root / 'console' / 'trade_craft_console.html',
                 root / 'trade_craft_console.html'):
        if cand.exists():
            return cand
    raise FileNotFoundError('trade_craft_console.html not found under ' + str(root))


def source_stamp(root=None):
    root = pathlib.Path(root) if root else repo_root()
    h = hashlib.sha256()
    for f in SOURCES:
        h.update((root / f).read_bytes())
    return h.hexdigest()[:16]
