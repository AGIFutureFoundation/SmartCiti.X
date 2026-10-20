#!/usr/bin/env bash
# One browser round over a frozen tree.
# usage: browser_round.sh <tree> <outdir> <port> [runs-file]
#   <tree>      the frozen copy to serve and test
#   <outdir>    where each run's log, round.txt and server.log go
#   <port>      a free local port for the static server
#   runs-file   a file of `run <name> <timeout-seconds> <command...>` lines;
#               default: tools/landing/browser_runs.sh beside this script
# Every run takes ONE chromium lock (CHROMIUM_LOCK, or $TMPDIR/chromium.lock),
# so two browser jobs never share the machine. $B is the base URL, $T the tree.
HERE=$(cd "$(dirname "$0")" && pwd)
LOCK=${CHROMIUM_LOCK:-${TMPDIR:?set TMPDIR or CHROMIUM_LOCK}/chromium.lock}
T=$1; O=$2; P=$3; RUNS=${4:-$HERE/browser_runs.sh}; mkdir -p $O; B=http://127.0.0.1:$P
cd $T; python3 -m http.server $P --bind 127.0.0.1 > $O/server.log 2>&1 & SRV=$!
sleep 2
run() { # name timeout cmd...
  local n=$1 to=$2; shift 2
  exec 9>$LOCK; flock 9
  local S=$(date +%s); echo "$(date -u +%T) start $n load $(cut -d' ' -f1-3 /proc/loadavg)" >> $O/round.txt
  (cd $T && timeout $to "$@") > $O/$n.log 2>&1; local rc=$?
  flock -u 9; exec 9>&-
  local ok=$(grep -c '^ *ok' $O/$n.log) fl=$(grep -c '^FAIL' $O/$n.log)
  echo "$(date -u +%T) $n rc=$rc ok=$ok FAIL=$fl secs=$(( $(date +%s)-S )) load_after $(cut -d' ' -f1-3 /proc/loadavg)" >> $O/round.txt
}
. "$RUNS"
kill $SRV
echo DONE >> $O/round.txt
