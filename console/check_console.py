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
from console_sources import console_html, repo_root, source_stamp

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

# The slice contract: every `SLICE.a.b.c` path the console's JS reads must
# exist in app_slice.json, and every lesson-row field the boot-time rule
# check compares must be on the sample rows. The page used to throw on its
# first line (`SLICE.lessons[UNION].tracks` against a slice that carried a
# list) with this check reporting "current", because a stamp only knows
# whether the sources changed, not whether the producer and the consumer
# still agree on a shape. A bug becomes a check.
import json
root = repo_root()
slice_doc = json.loads((root / 'console' / 'app_slice.json').read_text())
app_src = (root / 'console' / 'build_app.py').read_text()
paths = sorted(set(re.findall(r'\bSLICE((?:\.[A-Za-z_][A-Za-z0-9_]*)+)', app_src)))
missing = []
for dotted in paths:
    node = slice_doc
    for key in dotted.strip('.').split('.'):
        if not isinstance(node, dict):
            break                       # a JS method on a list or a number, not a data path
        if key not in node:
            missing.append('SLICE' + dotted); break
        node = node[key]
if missing:
    print('BROKEN: the console reads slice paths the slice does not carry:')
    for m2 in missing: print('       ', m2)
    print('       fix console/build_slice.py or console/build_app.py to one contract')
    sys.exit(1)
served = re.search(r"const UNION = '([a-z-]+)'", app_src).group(1)
if served not in {u['slug'] for u in slice_doc['unions']}:
    print(f'BROKEN: the console serves {served!r}, which the slice does not carry'); sys.exit(1)
row_keys = {'lesson_id', 'skill_id', 'form', 'base_difficulty', 'state', 'level_test', 'final_exam', 'union'}
if not isinstance(slice_doc['lessons'], list) or not slice_doc['lessons'] \
        or any(row_keys - set(r) for r in slice_doc['lessons']):
    print('BROKEN: slice.lessons must be a list of generated sample rows carrying', sorted(row_keys)); sys.exit(1)
union_keys = {'slug', 'name', 'index', 'lessons'}
if any(union_keys - set(u) for u in slice_doc['unions']):
    print('BROKEN: every slice.unions row must carry', sorted(union_keys)); sys.exit(1)
# and the page must embed the slice it was built from - the stamp hashes
# the protocol sources, not the slice, so a rebuilt slice with an unbuilt
# page would otherwise pass
m2 = re.search(r'^const SLICE = (.*);$', html, re.M)
if not m2 or json.loads(m2.group(1)) != slice_doc:
    print('STALE: the console embeds a different slice than console/app_slice.json')
    print('       run: python3 console/build_app.py'); sys.exit(1)
print(f'console is current (source stamp {have}; {len(paths)} slice paths read, all present; '
      f'{len(slice_doc["lessons"])} sample rows; slice embedded as built)')
