#!/usr/bin/env bash
# Full rebuild of every generated file, in dependency order.
# usage: rebuild_all.sh <tree>
# Run it TWICE: the second pass settles the registries that stamp one another.
# Prints REBUILT when the last builder returns. Any builder that fails stops it.
# tools/landing/test.mjs fails if a builder that exists is neither named here
# nor on that suite's reasoned skip list.
set -e
cd "$1"
for p in unions pack geo sims tools stations surfaces avatars kit props terrain sky world labels agents training guide restoration roadmap orbis meta spatial xr parcels ei respond venue protocols auth spaces; do python3 $p/build.py >/dev/null; done
python3 lessons/build.py >/dev/null
python3 schools/build.py >/dev/null
python3 courses/build.py >/dev/null
python3 courses_roadmap/build.py >/dev/null
python3 wilds/build.py >/dev/null
python3 restoration/scenarios.py >/dev/null
for p in completion compliance evals bundles sessions contrib worksites media; do python3 $p/build.py >/dev/null; done
python3 tasks/build.py >/dev/null
python3 geo3d/build.py >/dev/null
python3 parishes/build.py >/dev/null
python3 bayarea/build.py >/dev/null
python3 parishes/build_atlas.py >/dev/null
python3 elevation/build.py >/dev/null; python3 elevation/hillshade.py >/dev/null; python3 landcover/build.py >/dev/null
python3 underwater/build.py >/dev/null
python3 economy/build.py >/dev/null
python3 ambient/build.py >/dev/null
python3 physics/build.py >/dev/null
python3 fleet/build.py >/dev/null
python3 layers/build.py >/dev/null
python3 seasons/build.py >/dev/null
python3 outdoors/build.py >/dev/null
python3 wildlife/build.py >/dev/null; python3 wildlife/make_eggs.py >/dev/null
python3 smiles/build.py >/dev/null
python3 flora/build.py >/dev/null
python3 quests/build.py >/dev/null
python3 geoplay/build.py >/dev/null
python3 npcs/build.py >/dev/null
python3 hive/build.py >/dev/null
python3 unionpaths/build.py >/dev/null
python3 cognitionx/build.py --vendored >/dev/null
python3 classroom/build.py >/dev/null
python3 programs/build.py >/dev/null
python3 reactor/build.py >/dev/null
python3 campusplan/build.py >/dev/null
python3 robotics/build.py >/dev/null; [ -f robotics/arena/build.py ] && python3 robotics/arena/build.py >/dev/null; [ -f robotics/claw/build.py ] && python3 robotics/claw/build.py >/dev/null; python3 training/build.py >/dev/null; python3 robotics/ros/build.py >/dev/null
python3 swarm/build.py >/dev/null
[ -f modules/build.py ] && python3 modules/build.py >/dev/null
python3 contrib/build.py >/dev/null; python3 datashare/build.py >/dev/null
python3 facades/build.py >/dev/null
python3 payments/build.py >/dev/null
python3 cloudflare/build.py >/dev/null
python3 security/build_sbom.py >/dev/null
for b in web/build_*.py; do case $b in *build_bayworld.py) continue;; esac; python3 $b >/dev/null; done
python3 web/build_bayworld.py >/dev/null
python3 web/build_classroom.py >/dev/null
python3 console/build_app.py >/dev/null
python3 holodeck/build.py >/dev/null
python3 web/build_packs.py >/dev/null
python3 compliance/build.py >/dev/null; python3 evals/build.py >/dev/null
python3 web/build_home.py >/dev/null
python3 rnd/build.py >/dev/null
[ -f web/build_whitepaper.py ] && python3 web/build_whitepaper.py >/dev/null && python3 web/build_seo.py >/dev/null
python3 wiki/build_wiki.py >/dev/null
echo REBUILT
