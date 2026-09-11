# The toolrooms

One **tool crib per district** — 8 cribs, 96
generic hand tools — hung on a pegboard in every hall's tools room in the
[3D environment](Campus-Map.md) and listed on every hall panel of the
interactive map. Every hall binds through its district to a real
`tools.applied` skill in the graph, and `tools/test.mjs` proves all
111 bindings.

**The Crib check.** deterministic: a pick is right or wrong against the crib record; the option order is index arithmetic, not chance; nothing narrative can change a score. The suite
re-runs the derivation and requires a byte-identical result.

## Structural tool crib (Structural)

| Tool | What it is for | Render shape |
|---|---|---|
| 🔧 **Spud wrench** | aligns bolt holes and pins the steel connection | `wrench` |
| ⚒️ **Sleever bar** | levers heavy steel the last inch into place | `bar` |
| 📍 **Bull pin** | holds two aligned holes while the bolts go in | `cyl` |
| 🔩 **Torque wrench** | tightens a bolt to its specified torque, no further | `wrench` |
| ⛓️ **Rigging shackle** | closes the load path between sling and pick point | `hook` |
| ➰ **Wire-rope sling** | wraps the load and carries it to the hook | `coil` |
| ⚙️ **Lever hoist** | pulls a load in tight where no crane can reach | `case` |
| 🗜️ **Beam clamp** | grips a flange to make a temporary pick point | `hook` |
| 📏 **Plumb bob** | drops a true vertical line off a point above | `cone` |
| ✒️ **Center punch** | dimples the layout mark so the drill cannot wander | `cyl` |
| 📐 **Bolt gauge** | reads a bolt diameter and thread in one check | `blade` |
| 🛠️ **Impact wrench** | runs structural bolts down fast before the torque pass | `case` |

<details><summary>The Crib check for this crib (5 picks)</summary>

| # | Ask | Answer |
|---|---|---|
| 1 | Pick the tool that holds two aligned holes while the bolts go in | `bull-pin` |
| 2 | Pick the tool that grips a flange to make a temporary pick point | `beam-clamp` |
| 3 | Pick the tool that aligns bolt holes and pins the steel connection | `spud-wrench` |
| 4 | Pick the tool that wraps the load and carries it to the hook | `wire-sling` |
| 5 | Pick the tool that reads a bolt diameter and thread in one check | `bolt-gauge` |

</details>
## Envelope & finish tool crib (Envelope & Finish)

| Tool | What it is for | Render shape |
|---|---|---|
| 🔪 **Utility knife** | scores and cuts sheet goods to the line | `blade` |
| 🎨 **Taping knife** | lays and feathers joint compound over the seam | `blade` |
| 🧱 **Brick trowel** | butters and beds the mortar under each course | `blade` |
| 〰️ **Brick jointer** | strikes the mortar joint to a weathertight profile | `bar` |
| ⬜ **Grout float** | presses grout into tile joints and pulls the excess | `case` |
| 🪟 **Glass suction cup** | grips a glass lite so it can be walked and set | `cyl` |
| 🧴 **Caulking gun** | drives a steady sealant bead along the joint | `cyl` |
| 📏 **Chalk line** | snaps a straight layout line across the field | `case` |
| 📐 **Framing square** | checks and lays out a true right angle | `blade` |
| 🪵 **Block plane** | shaves a door or trim edge to the exact fit | `case` |
| 🖌️ **Putty knife** | presses filler into small defects before paint | `blade` |
| 🎯 **Seam roller** | sets a membrane seam with even rolling pressure | `cyl` |

<details><summary>The Crib check for this crib (5 picks)</summary>

| # | Ask | Answer |
|---|---|---|
| 1 | Pick the tool that butters and beds the mortar under each course | `brick-trowel` |
| 2 | Pick the tool that snaps a straight layout line across the field | `chalk-line` |
| 3 | Pick the tool that scores and cuts sheet goods to the line | `utility-knife` |
| 4 | Pick the tool that grips a glass lite so it can be walked and set | `suction-cup` |
| 5 | Pick the tool that presses filler into small defects before paint | `putty-knife` |

</details>
## Building-systems tool crib (Building Systems)

| Tool | What it is for | Render shape |
|---|---|---|
| 🔋 **Multimeter** | reads voltage, current and resistance in one instrument | `meter` |
| ✂️ **Wire strippers** | strips insulation to length without nicking the conductor | `wrench` |
| 🎣 **Fish tape** | pulls conductors through a finished conduit run | `coil` |
| 📐 **Conduit bender** | sweeps a conduit offset to the marked angle | `bar` |
| ⚙️ **Tubing cutter** | cuts copper tube square with a rolled wheel | `hook` |
| 🔧 **Pipe wrench** | grips and turns threaded pipe by its jaw bite | `wrench` |
| 🧲 **Crimping tool** | closes a connector onto its conductor gas-tight | `wrench` |
| 🌡️ **Manifold gauge set** | reads both sides of a refrigeration circuit at once | `meter` |
| 📏 **Torpedo level** | levels short runs where a full level cannot fit | `bar` |
| ⚡ **Non-contact tester** | proves a circuit dead before any hand touches it | `cyl` |
| 🦀 **Tongue-and-groove pliers** | adjusts its jaw span to grip what the job presents | `wrench` |
| 🔩 **Nut driver set** | seats panel screws and small hex hardware cleanly | `cyl` |

<details><summary>The Crib check for this crib (5 picks)</summary>

| # | Ask | Answer |
|---|---|---|
| 1 | Pick the tool that pulls conductors through a finished conduit run | `fish-tape` |
| 2 | Pick the tool that reads both sides of a refrigeration circuit at once | `manifold-gauge` |
| 3 | Pick the tool that reads voltage, current and resistance in one instrument | `multimeter` |
| 4 | Pick the tool that grips and turns threaded pipe by its jaw bite | `pipe-wrench` |
| 5 | Pick the tool that adjusts its jaw span to grip what the job presents | `channel-locks` |

</details>
## Energy & utilities tool crib (Energy & Utilities)

| Tool | What it is for | Render shape |
|---|---|---|
| 🦷 **Lineman pliers** | cuts, twists and pulls conductor in one grip | `wrench` |
| 🦯 **Hot stick** | operates energized gear from an insulated distance | `bar` |
| ✂️ **Cable cutter** | shears large cable clean without crushing the strands | `wrench` |
| 🧲 **Clamp meter** | reads current through a conductor without breaking it | `meter` |
| 🔋 **Insulation tester** | proves insulation resistance before energizing | `meter` |
| 🚨 **Gas detector** | sniffs the trench and vault air before entry | `meter` |
| 🔑 **Valve key** | reaches and turns a buried curb valve from grade | `bar` |
| 📡 **Line locator** | traces the buried line before the first dig | `meter` |
| 🔩 **Torque screwdriver** | lands terminal screws at their exact rating | `cyl` |
| 🧰 **Splice shell set** | rebuilds and seals a cable joint against water | `case` |
| ⛏️ **Sharpshooter spade** | opens a narrow potholing cut over a marked line | `blade` |
| ⛓️ **Grounding cluster** | bonds the dead line to earth before work begins | `coil` |

<details><summary>The Crib check for this crib (5 picks)</summary>

| # | Ask | Answer |
|---|---|---|
| 1 | Pick the tool that shears large cable clean without crushing the strands | `cable-cutter` |
| 2 | Pick the tool that traces the buried line before the first dig | `pipe-locator` |
| 3 | Pick the tool that cuts, twists and pulls conductor in one grip | `lineman-pliers` |
| 4 | Pick the tool that sniffs the trench and vault air before entry | `gas-detector` |
| 5 | Pick the tool that opens a narrow potholing cut over a marked line | `sharpshooter` |

</details>
## Earthworks & plant tool crib (Earthworks & Plant)

| Tool | What it is for | Render shape |
|---|---|---|
| 📏 **Grade rod** | reads cut and fill against the laser plane | `bar` |
| 🔦 **Rotary laser** | spins one level datum across the whole site | `meter` |
| ⛏️ **Pick mattock** | breaks hard ground the shovel cannot start | `wrench` |
| 🧹 **Round-point shovel** | moves loose spoil and shapes the cut by hand | `blade` |
| 🧴 **Grease gun** | feeds every zerk on the machine its daily grease | `cyl` |
| 🦴 **Pry bar** | levers pins, plates and stubborn iron apart | `bar` |
| 🔨 **Hand tamper** | compacts backfill in lifts where plate compactors cannot go | `bar` |
| 🧵 **String line** | carries line and grade between the offset stakes | `coil` |
| 🖌️ **Marking wand** | paints the locate colors onto the ground | `cyl` |
| 🧰 **Socket set** | services the plant with the right drive size | `case` |
| ✒️ **Pin punch** | drives track and bucket pins in and out true | `cyl` |
| 🌡️ **Tire pressure gauge** | checks plant tires to the loading chart | `meter` |

<details><summary>The Crib check for this crib (5 picks)</summary>

| # | Ask | Answer |
|---|---|---|
| 1 | Pick the tool that breaks hard ground the shovel cannot start | `mattock` |
| 2 | Pick the tool that carries line and grade between the offset stakes | `string-line` |
| 3 | Pick the tool that reads cut and fill against the laser plane | `grade-rod` |
| 4 | Pick the tool that levers pins, plates and stubborn iron apart | `pry-bar` |
| 5 | Pick the tool that drives track and bucket pins in and out true | `pin-punch` |

</details>
## Heavy-industry tool crib (Heavy Industry)

| Tool | What it is for | Render shape |
|---|---|---|
| ⚒️ **Chipping hammer** | knocks slag off the cooled weld for inspection | `wrench` |
| 🔩 **Flange spreader** | opens a bolted flange safely against its spring | `wrench` |
| 📍 **Flange alignment pins** | draw two flanges into bolt-hole alignment | `cyl` |
| 📐 **Feeler gauge** | measures the gap a caliper cannot enter | `blade` |
| ⚙️ **Micrometer** | reads a machined diameter to the thousandth | `hook` |
| 🧰 **File set** | dresses an edge or fit by controlled strokes | `case` |
| ✒️ **Deburring tool** | breaks the sharp edge every cut leaves behind | `cyl` |
| 🌡️ **Dial indicator** | reads runout and lift as the shaft turns | `meter` |
| 🧲 **Bearing puller** | draws a bearing off its seat without damage | `hook` |
| 🖌️ **Soapstone holder** | marks hot steel where ink and chalk fail | `bar` |
| 📏 **Fillet weld gauge** | measures a finished weld against its called size | `blade` |
| ⛓️ **Chain tongs** | turns large pipe by wrapping it, not biting it | `wrench` |

<details><summary>The Crib check for this crib (5 picks)</summary>

| # | Ask | Answer |
|---|---|---|
| 1 | Pick the tool that draw two flanges into bolt-hole alignment | `alignment-pins` |
| 2 | Pick the tool that reads runout and lift as the shaft turns | `dial-indicator` |
| 3 | Pick the tool that knocks slag off the cooled weld for inspection | `chipping-hammer` |
| 4 | Pick the tool that dresses an edge or fit by controlled strokes | `file-set` |
| 5 | Pick the tool that measures a finished weld against its called size | `weld-gauge` |

</details>
## Transport & mobility tool crib (Transport & Mobility)

| Tool | What it is for | Render shape |
|---|---|---|
| 🔧 **Track wrench** | runs rail bolts down through the joint bars | `wrench` |
| 🦴 **Spike puller** | draws a rail spike without splitting the tie | `bar` |
| 📏 **Track gauge** | holds the rails at their exact set apart | `blade` |
| ⚙️ **Torque multiplier** | multiplies hand torque for the largest fasteners | `case` |
| 🌡️ **Compression tester** | reads each diesel cylinder against its siblings | `meter` |
| 🧲 **Brake spring tool** | seats and releases brake springs under control | `wrench` |
| ⛔ **Wheel chock pair** | holds the vehicle still before anyone goes under | `case` |
| 📡 **Signal test set** | proves the circuit sees the aspect it should | `meter` |
| 📍 **Alignment bar** | walks bolt holes into line on heavy assemblies | `bar` |
| 🛠️ **Impact gun** | breaks and runs lug and frame hardware fast | `case` |
| 🔦 **Inspection lamp** | lights the underside where the fault hides | `cyl` |
| 🦯 **Height stick** | measures wire height above the rail head safely | `bar` |

<details><summary>The Crib check for this crib (5 picks)</summary>

| # | Ask | Answer |
|---|---|---|
| 1 | Pick the tool that holds the rails at their exact set apart | `rail-gauge` |
| 2 | Pick the tool that proves the circuit sees the aspect it should | `signal-tester` |
| 3 | Pick the tool that runs rail bolts down through the joint bars | `track-wrench` |
| 4 | Pick the tool that seats and releases brake springs under control | `brake-tool` |
| 5 | Pick the tool that lights the underside where the fault hides | `creeper-light` |

</details>
## Survey, safety & environment tool crib (Survey, Safety & Environment)

| Tool | What it is for | Render shape |
|---|---|---|
| 📍 **Prism pole** | holds the survey prism plumb over the point | `bar` |
| 🔭 **Auto level** | reads elevation differences through a leveled scope | `meter` |
| 📐 **Field tripod** | plants the instrument rigid over the station | `bar` |
| 🚨 **Four-gas monitor** | watches the air for the four killers continuously | `meter` |
| 🌬️ **Air sampling pump** | draws a metered air volume through the media | `case` |
| 🧴 **Decon sprayer** | washes contamination down at the exit line | `cyl` |
| 🌪️ **HEPA vacuum** | captures fine hazard dust instead of scattering it | `case` |
| 💨 **Anemometer** | reads air speed across the containment face | `meter` |
| 🔊 **Sound level meter** | measures noise dose where hearing is on the line | `meter` |
| 🔦 **Light meter** | proves the task lighting meets its required lux | `meter` |
| 💧 **Moisture meter** | finds the wet wall behind the dry paint | `meter` |
| ⛓️ **Rope grab** | arrests a fall on the lifeline the moment it starts | `hook` |

<details><summary>The Crib check for this crib (5 picks)</summary>

| # | Ask | Answer |
|---|---|---|
| 1 | Pick the tool that plants the instrument rigid over the station | `field-tripod` |
| 2 | Pick the tool that reads air speed across the containment face | `anemometer` |
| 3 | Pick the tool that holds the survey prism plumb over the point | `prism-pole` |
| 4 | Pick the tool that washes contamination down at the exit line | `decon-sprayer` |
| 5 | Pick the tool that finds the wet wall behind the dry paint | `moisture-meter` |

</details>

## What a crib is not

a schematic training aid for tool identification and tool-crib discipline - not an inventory of any real toolroom, not tool competency certification, and no manufacturer or brand is named or drawn.

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
