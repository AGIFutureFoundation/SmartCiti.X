#!/usr/bin/env bash
# Render every clip in media/shots.json frame by frame, in short locked runs
# (each run stops itself before ~200 s and the next resumes where it stopped).
# usage: SP=<scratchpad> MEDIA_BASE=http://127.0.0.1:<port>/ media/render_all.sh [clip ids...]
set -euo pipefail
cd "$(dirname "$0")/.."
: "${SP:?SP is not set}"; : "${MEDIA_BASE:?MEDIA_BASE is not set}"
ids=("$@")
if [ ${#ids[@]} -eq 0 ]; then
  mapfile -t ids < <(python3 -c "import json;[print(c['id']) for c in json.load(open('media/shots.json'))['clips']]")
fi
for id in "${ids[@]}"; do
  n=$(python3 -c "import json,sys;s=json.load(open('media/shots.json'));c=[c for c in s['clips'] if c['id']=='$id'][0];print(round(c['seconds']*s['fps']))")
  for try in 1 2 3 4 5 6 7 8; do
    have=$(ls "$SP/media_work/frames/$id" 2>/dev/null | grep -c '\.png$' || true)
    [ "$have" -ge "$n" ] && break
    first=$(python3 -c "import os;d='$SP/media_work/frames/$id';h=set(os.listdir(d)) if os.path.isdir(d) else set();print(next(i for i in range($n) if 'f%04d.png'%i not in h))")
    echo "$(date -u +%T) $id: $have/$n frames, resuming at $first"
    flock "$SP/chromium.lock" timeout 240 node media/record.mjs "$id" "$SP/media_work/frames/$id" "$first" || echo "run exit $?"
  done
done
