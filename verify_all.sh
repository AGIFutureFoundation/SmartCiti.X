#!/usr/bin/env bash
# Runs every suite in the bundle from the bundle root. Exits non-zero on any
# failure. Paths inside the packs resolve against their own module location,
# so this works from any working directory.
set -uo pipefail
cd "$(dirname "$0")"
total=0; fail=0
for t in control/test.mjs control/test_graph.mjs control/test_hints.mjs \
         control/fuzz.mjs control/soak.mjs fabric/test.mjs \
         bus/test.mjs bus/test_safeguards.mjs security/test.mjs \
         ops/test.mjs ops/fuzz.mjs brand/test.mjs unions/verify.mjs \
         pack/verify.mjs i18n/test.mjs stations/test.mjs surfaces/test.mjs \
         geo/test.mjs sims/test.mjs schools/test.mjs avatars/test.mjs; do
  out=$(node "$t" 2>&1); rc=$?
  n=$(printf '%s\n' "$out" | grep -c '^  ok ')
  total=$((total + n))
  if [ $rc -ne 0 ]; then
    fail=$((fail + 1)); printf 'FAIL  %-26s\n' "$t"; printf '%s\n' "$out" | tail -6
  else
    printf 'ok    %-26s %3d checks\n' "$t" "$n"
  fi
done
python3 console/check_console.py || fail=$((fail + 1))
python3 wiki/build_wiki.py --check || fail=$((fail + 1))
iout=$(python3 web/test_interiors.py 2>&1) || fail=$((fail + 1))
printf '%s\n' "$iout" | tail -1
total=$((total + $(printf '%s\n' "$iout" | grep -c '^  ok ')))
node brand/lint.mjs . || fail=$((fail + 1))
node brand/figures.mjs . || fail=$((fail + 1))
echo "----"
echo "$total checks, $fail failing suites"
[ $fail -eq 0 ] || exit 1
