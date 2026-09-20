#!/usr/bin/env bash
# Runs every suite in the bundle from the bundle root. Exits non-zero on any
# failure. Paths inside the packs resolve against their own module location,
# so this works from any working directory.
set -uo pipefail
cd "$(dirname "$0")"
total=0; fail=0
# README.md's suite table types a count beside every suite, and the headline
# types the total. Three PRs in a row fixed some of them by hand; a typed
# count is a claim, so each is held to the count that actually ran.
readme_says() { grep -F "node $1 " README.md | head -1 | sed -nE 's/^node [^#]*# *([0-9]+) .*/\1/p'; }
for t in control/test.mjs control/test_graph.mjs control/test_hints.mjs \
         control/fuzz.mjs control/soak.mjs fabric/test.mjs \
         bus/test.mjs bus/test_safeguards.mjs security/test.mjs security/test_sbom.mjs \
         ops/test.mjs ops/fuzz.mjs ops/rehearsal.mjs brand/test.mjs unions/verify.mjs \
         pack/verify.mjs i18n/test.mjs stations/test.mjs surfaces/test.mjs \
         geo/test.mjs sims/test.mjs tools/test.mjs schools/test.mjs \
         avatars/test.mjs parcels/test.mjs meta/test.mjs \
         agents/test.mjs world/test.mjs labels/test.mjs training/test.mjs \
         roadmap/test.mjs orbis/test.mjs restoration/test.mjs \
         spatial/test.mjs web/test_3d.mjs web/test_rtl.mjs; do
  out=$(node "$t" 2>&1); rc=$?
  n=$(printf '%s\n' "$out" | grep -c '^  ok ')
  total=$((total + n))
  want=$(readme_says "$t")
  if [ -n "$want" ] && [ "$want" != "$n" ]; then
    fail=$((fail + 1)); printf 'DRIFT %-26s README.md says %s checks, the suite ran %s\n' "$t" "$want" "$n"
  fi
  if [ $rc -ne 0 ]; then
    fail=$((fail + 1)); printf 'FAIL  %-26s\n' "$t"; printf '%s\n' "$out" | tail -6
  else
    printf 'ok    %-26s %3d checks\n' "$t" "$n"
  fi
done
python3 console/check_console.py || fail=$((fail + 1))
python3 wiki/build_wiki.py --check || fail=$((fail + 1))
python3 web/build_page.py --check || fail=$((fail + 1))
python3 web/build_dashboard.py --check || fail=$((fail + 1))
python3 web/build_interactive_map.py --check || fail=$((fail + 1))
python3 web/build_map.py --check || fail=$((fail + 1))
python3 web/build_geomap.py --check || fail=$((fail + 1))
python3 web/build_languages.py --check || fail=$((fail + 1))
python3 web/build_landing.py --check || fail=$((fail + 1))
python3 web/build_3d.py --check || fail=$((fail + 1))
python3 web/build_home.py --check || fail=$((fail + 1))
iout=$(python3 web/test_interiors.py 2>&1) || fail=$((fail + 1))
printf '%s\n' "$iout" | tail -1
total=$((total + $(printf '%s\n' "$iout" | grep -c '^  ok ')))
node brand/lint.mjs . || fail=$((fail + 1))
node brand/figures.mjs . || fail=$((fail + 1))
node i18n/lint_hardcoded.mjs || fail=$((fail + 1))
node web/lint_external.mjs || fail=$((fail + 1))
headline=$(sed -nE 's/^\*\*([0-9,]+) checks, all passing.*/\1/p' README.md | tr -d ,)
if [ "$headline" != "$total" ]; then
  fail=$((fail + 1)); echo "DRIFT README.md headline says $headline checks, this run counted $total"
fi
echo "----"
echo "$total checks, $fail failing suites"
[ $fail -eq 0 ] || exit 1
