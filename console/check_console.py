#!/usr/bin/env python3
"""Fail if the built console is behind the protocol modules it inlines.

The console embeds a snapshot of the control plane, the fabric guards and the
bus. A snapshot goes stale silently — the page keeps working, just with
yesterday's protocol — so this compares the stamp baked into the built HTML
against a fresh hash of the sources.

The source list lives in console_sources.py and is shared with the builder. An
earlier version declared its own copy, which drifted the moment a new pack was
added and made the checker report a confidently wrong answer.
"""
import pathlib
import re
import sys

import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from console_sources import console_html, source_stamp

want = source_stamp()
html = console_html().read_text()
m = re.search(r'control-plane-source-stamp: ([0-9a-f]{16})', html)
if not m:
    print('STALE: the console carries no source stamp — rebuild with build_app.py')
    sys.exit(1)
have = m.group(1)
if have != want:
    print(f'STALE: console was built from {have}, sources are now {want}')
    print('       run: python3 build_app.py')
    sys.exit(1)
print(f'console is current (source stamp {have})')
