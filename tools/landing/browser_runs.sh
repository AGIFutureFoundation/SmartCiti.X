# The default browser round: one `run <name> <timeout-seconds> <command...>` per line,
# sourced by browser_round.sh (so $B, $T and $O are in scope). Edit a copy and pass it as
# the fourth argument to run a different round. (The four-run limit in the team rules is for
# an agent's own runs; the landing round is the lead's and runs the whole list.)
run smoke 900 node web/smoke.mjs "--base=$B" "--root=$T"
run test_robotics 180 node web/test_robotics.mjs "--browser=$B/web"
run test_hudkit 180 env "HUD_BASE=$B/web/" node web/test_hudkit.mjs --browser
run relief_parish 120 node web/eval_relief.mjs "$B/web/trade_craft_parishes.html" --name=parish
run relief_bay 120 node web/eval_relief.mjs "$B/web/trade_craft_bay.html" --name=bay
run eval_parishes 240 env "PARISHES_URL=$B/web/trade_craft_parishes.html" node web/eval_parishes.mjs
run eval_bayworld 180 env "BAY_URL=$B/web/trade_craft_bay.html" node web/eval_bayworld.mjs
run eval_wilds 180 env "WILDS_URL=$B/web/trade_craft_wilds.html" node web/eval_wilds.mjs
run eval_look 120 env "LOOK_BASE=$B" node web/eval_look.mjs
run spaces_a 90 node web/browser_spaces.mjs "$B/web/trade_craft_3d.html" --pairs=0-1 --halltest=crane-sim-bay:riggers
run spaces_b 90 node web/browser_spaces.mjs "$B/web/trade_craft_3d.html" --deep=electrical-lab --pairs=2-4 --halltest=flipped-classroom:carpenters,flipped-classroom:electricians
run spaces_c 90 node web/browser_spaces.mjs "$B/web/trade_craft_3d.html" --deep=rigging-yard --pairs=5-6 --halltest=rigging-yard:ironworkers
run spaces_d 90 node web/browser_spaces.mjs "$B/web/trade_craft_3d.html" --deep=scaffold-court --pairs=7-9 --halltest=scaffold-court:carpenters,welding-bay:welders
run relief_stream 120 node web/eval_relief.mjs "$B/web/trade_craft_bay.html" --name=bay --stream
run geomap_probe 90 node tools/landing/geomap_hillshade_probe.mjs "$B/web/trade_craft_geomap.html" "$O/geomap.png"
run eval_styles 600 node web/eval_styles.mjs "--base=$B" "--root=$T"
