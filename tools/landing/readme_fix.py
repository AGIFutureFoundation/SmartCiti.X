#!/usr/bin/env python3
"""Sync README.md's typed counts to a verify_all.sh output, in a frozen copy.

usage: readme_fix.py <tree> <verify_all-output-file> [rows.json]

  - every suite row `node <suite>   # N - ...` whose N differs from the
    `ok <suite> N checks` line the run printed gets the run's N;
  - the headline `**N checks, all passing` gets the run's total;
  - rows.json (optional) is a JSON object {suite: row-text}: each row of the
    README that starts `node <suite>` is replaced by its text, with the first
    `%s` in it filled by the run's count for that suite; a suite with no row
    yet is inserted after the last `node ` row and a missing run line stops
    the script. One-off wording for a wave lives in that file, never in here.

The README of the live tree is not touched by the landing protocol: run this on
the frozen copy only, then commit that copy (see wiki/Build-and-Landing.md).
"""
import json
import re
import sys

root = sys.argv[1]
verify = open(sys.argv[2]).read()
p = root + '/README.md'
s = open(p).read()
ran = dict(re.findall(r'^ok +(\S+) +(\d+) checks', verify, re.M))
for suite, n in ran.items():
    m = re.search(r'^node ' + re.escape(suite) + r' +# (\d+) ', s, re.M)
    if m and m.group(1) != n:
        s = s[:m.start(1)] + n + s[m.end(1):]
if len(sys.argv) > 3:
    for suite, text in json.load(open(sys.argv[3])).items():
        assert suite in ran, 'no ok line for ' + suite + ' in the verify output'
        text = text.replace('%s', ran[suite], 1)
        m = re.search(r'^node ' + re.escape(suite) + r' +#[^\n]*$', s, re.M)
        if m:
            s = s[:m.start()] + text + s[m.end():]
        else:
            last = list(re.finditer(r'^node [^\n]*\n', s, re.M))[-1]
            s = s[:last.end()] + text + '\n' + s[last.end():]
total = re.search(r'^(\d+) checks, \d+ failing suites', verify, re.M).group(1)
s = re.sub(r'^\*\*[\d,]+ checks, all passing', '**{:,} checks, all passing'.format(int(total)), s, count=1, flags=re.M)
open(p, 'w').write(s)
print('readme fixed, total', total)
