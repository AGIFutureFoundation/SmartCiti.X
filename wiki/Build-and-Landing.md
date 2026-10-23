# Build and landing

How a batch of work gets from a working tree onto `main` without anyone having
to trust a build that has not been checked. The scripts live in
[`tools/landing/`](../tools/landing/README.md); this page is generated from them.

## The protocol, in plain words

1. **Freeze the tree.** Copy the working tree to a separate directory. Every
   later step runs on the copy, so nothing that is still being edited can
   change what is being checked.
2. **Rebuild twice.** Run `rebuild_all.sh` on the copy, then run it again. The
   first pass builds every registry and page in dependency order; the second
   settles the files that stamp one another, so a third rebuild would change
   nothing.
3. **Verify.** Run `verify_all.sh` in the copy and keep what it prints: one
   line per suite with its check count, and one total.
4. **Fix the README counts in the frozen copy only.** The README types a count
   beside every suite and a headline total. `readme_fix.py` moves each to the
   count the verify run printed. It is run on the copy, never on the live
   tree, so the working tree is not rewritten under whoever is editing it.
5. **Browser round, under one chromium lock.** `browser_round.sh` serves the
   copy locally and runs the browser suites one after another, each holding
   the same lock, so two browser jobs never compete for the machine and a
   timing is not an accident of load.
6. **Byte-compare the archive.** What is going to be committed is compared,
   file for file, with the frozen copy that was verified.
7. **Scan.** The change is searched for secrets, for model identifiers and for
   machine-local paths. Any hit stops the landing.
8. **Commit, push.** Only the person landing the work runs git; builders,
   suites and agents never commit.

## The team token rules

- **Read by line range.** Find the lines with `grep -n`, then read only those
  with `sed -n a,bp`. Never print a built page: they run from 0.1 to 3 MB.
- **Single suites while iterating.** Run the one suite for the file you
  changed. `verify_all.sh` and `rebuild_all.sh` are for whoever lands.
- **At most four browser runs** per agent, each under the lock and within 90
  seconds; plan each run to collect everything it can.
- **Hand back in under 400 words:** files changed, suites and counts,
  mutations, the measured numbers, and what is still open.

## The scripts

| Script | Usage, or what it says of itself |
|---|---|
| [`rebuild_all.sh`](../tools/landing/rebuild_all.sh) | usage: rebuild_all.sh &lt;tree&gt; |
| [`browser_round.sh`](../tools/landing/browser_round.sh) | usage: browser_round.sh &lt;tree&gt; &lt;outdir&gt; &lt;port&gt; [runs-file] |
| [`browser_runs.sh`](../tools/landing/browser_runs.sh) | The default browser round: one `run &lt;name&gt; &lt;timeout-seconds&gt; &lt;command...&gt;` per line, |
| [`readme_fix.py`](../tools/landing/readme_fix.py) | usage: readme_fix.py &lt;tree&gt; &lt;verify_all-output-file&gt; [rows.json] |
| [`geomap_hillshade_probe.mjs`](../tools/landing/geomap_hillshade_probe.mjs) | One browser probe for the geomap hillshade, run as one line of the landing browser round. |
| [`test.mjs`](../tools/landing/test.mjs) | tools/landing/test.mjs - the landing tooling cannot drift from the repository. |

## The rebuild order

`rebuild_all.sh` runs these builders in this order (102 entries, read
from the script; `web/build_*.py` stands for the loop over every web page
builder):

```
unions/build.py
pack/build.py
geo/build.py
sims/build.py
tools/build.py
stations/build.py
surfaces/build.py
avatars/build.py
kit/build.py
props/build.py
terrain/build.py
sky/build.py
world/build.py
labels/build.py
agents/build.py
training/build.py
guide/build.py
restoration/build.py
roadmap/build.py
orbis/build.py
meta/build.py
spatial/build.py
xr/build.py
parcels/build.py
ei/build.py
respond/build.py
venue/build.py
protocols/build.py
auth/build.py
spaces/build.py
spatial/sneeze_kit/ingest.py
lessons/build.py
schools/build.py
courses/build.py
courses_roadmap/build.py
wilds/build.py
restoration/scenarios.py
completion/build.py
compliance/build.py
evals/build.py
bundles/build.py
sessions/build.py
contrib/build.py
worksites/build.py
media/build.py
tasks/build.py
geo3d/build.py
parishes/build.py
bayarea/build.py
parishes/build_atlas.py
elevation/build.py
elevation/hillshade.py
landcover/build.py
underwater/build.py
economy/build.py
ambient/build.py
physics/build.py
fleet/build.py
layers/build.py
seasons/build.py
outdoors/build.py
wildlife/build.py
wildlife/make_eggs.py
smiles/build.py
flora/build.py
quests/build.py
geoplay/build.py
npcs/build.py
hive/build.py
unionpaths/build.py
cognitionx/build.py
classroom/build.py
programs/build.py
reactor/build.py
campusplan/build.py
robotics/build.py
robotics/arena/build.py
robotics/claw/build.py
training/build.py
robotics/ros/build.py
swarm/build.py
modules/build.py
contrib/build.py
datashare/build.py
facades/build.py
payments/build.py
cloudflare/build.py
security/build_sbom.py
web/build_*.py
web/build_bayworld.py
web/build_classroom.py
console/build_app.py
holodeck/build.py
web/build_packs.py
compliance/build.py
evals/build.py
web/build_home.py
rnd/build.py
web/build_whitepaper.py
web/build_seo.py
i18n/build_review.py
wiki/build_wiki.py
```

## The browser round

The default round, as `browser_runs.sh` lists it. Every run is one line: a name,
a timeout and a command, and `$B` is the local base URL.

| Run | Timeout | Command |
|---|---|---|
| `smoke` | 900 s | `node web/smoke.mjs "--base=$B" "--root=$T"` |
| `test_robotics` | 180 s | `node web/test_robotics.mjs "--browser=$B/web"` |
| `test_hudkit` | 180 s | `env "HUD_BASE=$B/web/" node web/test_hudkit.mjs --browser` |
| `relief_parish` | 120 s | `node web/eval_relief.mjs "$B/web/trade_craft_parishes.html" --name=parish` |
| `relief_bay` | 120 s | `node web/eval_relief.mjs "$B/web/trade_craft_bay.html" --name=bay` |
| `eval_parishes` | 240 s | `env "PARISHES_URL=$B/web/trade_craft_parishes.html" node web/eval_parishes.mjs` |
| `eval_bayworld` | 180 s | `env "BAY_URL=$B/web/trade_craft_bay.html" node web/eval_bayworld.mjs` |
| `eval_wilds` | 180 s | `env "WILDS_URL=$B/web/trade_craft_wilds.html" node web/eval_wilds.mjs` |
| `eval_look` | 120 s | `env "LOOK_BASE=$B" node web/eval_look.mjs` |
| `spaces_a` | 90 s | `node web/browser_spaces.mjs "$B/web/trade_craft_3d.html" --pairs=0-1 --halltest=crane-sim-bay:riggers` |
| `spaces_b` | 90 s | `node web/browser_spaces.mjs "$B/web/trade_craft_3d.html" --deep=electrical-lab --pairs=2-4 --halltest=flipped-classroom:carpenters,flipped-classroom:electricians` |
| `spaces_c` | 90 s | `node web/browser_spaces.mjs "$B/web/trade_craft_3d.html" --deep=rigging-yard --pairs=5-6 --halltest=rigging-yard:ironworkers` |
| `spaces_d` | 90 s | `node web/browser_spaces.mjs "$B/web/trade_craft_3d.html" --deep=scaffold-court --pairs=7-9 --halltest=scaffold-court:carpenters,welding-bay:welders` |
| `relief_stream` | 120 s | `node web/eval_relief.mjs "$B/web/trade_craft_bay.html" --name=bay --stream` |
| `geomap_probe` | 90 s | `node tools/landing/geomap_hillshade_probe.mjs "$B/web/trade_craft_geomap.html" "$O/geomap.png"` |
| `eval_styles` | 600 s | `node web/eval_styles.mjs "--base=$B" "--root=$T"` |

## What keeps it honest

`node tools/landing/test.mjs` fails when a builder exists that the rebuild does
not run, when a script holds a path that only works on one machine, when a
script is not executable, or when the README fixer stops doing what is said
above. The builders it deliberately does not require in the script, each with
its reason:

| Builder | Why it is not a line of the script |
|---|---|
| `assets/overview/build_overview.py` | cuts a promotional overview from frames captured from the running app (assets/overview/shots.mjs); a media job, not part of the build the registries depend on |
| `console/build_slice.py` | writes console/app_slice.json, a committed input that console/build_app.py reads; console/check_console.py holds the two to one contract, and the data rebuilds do not change it |
| `parishes/build_world.py` | the parish world layer, imported and run by parishes/build.py itself (its main() is called there), so the script runs it through that builder |

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
