# The surface finishes

Every room in every hall stands on a named floor and inside named walls.
The catalogue is **84 floor finishes** and **51 wall
finishes** — 135 rows — carrying renderer-ready colour,
roughness, metalness, tile size and the reason each one exists, over
32 patterns. They are resolved onto all 1,221 room
floors and 1,221 room walls in the 111 halls, and every
row earns its place: 84 of the 84 floor finishes and
51 of the 51 wall finishes stand somewhere, leaving
0 floor rows and
0 wall rows unplaced.

**And the colours are not measurements.** Every colour, roughness and metalness in both catalogues is AUTHORED - chosen by eye against what the material is, and never sampled from a photograph, a measured swatch or a supplier's data. What is DERIVED is only which hall stands on which, read from the trade's own words.

That limit is the whole of what this pack claims about appearance. What it
claims about placement is a different tier, and the table at the foot of this
page keeps the two apart.

## The catalogue grew and the scene did not

A hall builds **one material per room**, not one per catalogue row.
`web/build_3d.py` calls `finishMat()` once for each of the 11 room
floors inside its `for (const r of h.rooms)` loop and `wallMat()` once for
that room's partitions, plus one for the hall shell — so the busiest hall in
the bundle builds 11 floor materials and 10
partition-wall materials whatever the catalogue holds. The floor mesh and the
partition mesh exist either way; a finish changes what they wear, never how
many of them there are.

Underneath, `surfaceMaps()` caches a painted canvas and its normal map on
`pattern + colour + size`, so the 135 rows collapse to
134 distinct texture keys across the whole catalogue, and only the
ones a walker actually reaches are ever painted. **A finish is a cached
texture. It is not a draw call.** That is why the catalogue could grow without
the hall view's draw-call budget moving at all.

The same argument says why no pattern was added. A pattern is not decoration —
it is the key the page's own `PATTERN_RELIEF` table is keyed on, and
`web/build_3d.py` reads that table out of its own source at build time and
asserts that every pattern in this registry has a relief declared and that no
declaration is orphaned. A new pattern is therefore a change to the page, not
a row in a registry: it would land looking like grey noise and the build
refuses it instead. 32 patterns, every one declared.

| Pattern | What it paints | Finishes using it |
|---|---|---|
| `slab` | one large pour with its construction joints at the edges | 5 |
| `tile` | a square modular tile with a grouted joint on every side | 12 |
| `brick` | a stretcher bond with a raked mortar course | 11 |
| `plank` | parallel board joints running one way | 14 |
| `block` | a coursed unit face, wider than it is tall | 5 |
| `checker` | raised two-way bars, the classic plate tread | 2 |
| `grate` | bearing bars with open slots between them | 2 |
| `broom` | fine combed striations dragged across a green slab | 1 |
| `smooth` | no joint at all: a poured film with nothing to catch | 23 |
| `speckle` | loose aggregate scattered through the surface | 7 |
| `panel` | a ribbed sheet with a seam where two sheets meet | 4 |
| `plywood` | sheet edges with the long grain running with them | 2 |
| `board` | a flat drawn-on face with a single joint line | 2 |
| `fabric` | a fine two-way weave with no hard edges | 3 |
| `screen` | a heavy frame with a light infill inside it | 2 |
| `mesh` | woven wire you can see through, the wire catching the light | 1 |
| `diamond` | raised lozenges in offset rows, the tread of a vehicle deck | 2 |
| `plate` | flat plate with a ground weld seam every sheet width | 4 |
| `terrazzo` | chip suspended in matrix, divided by a strip on a grid | 3 |
| `flake` | irregular colour flake broadcast into a wet resin film | 2 |
| `trench` | a floor laid to falls with a slotted drain running the bay | 2 |
| `sand` | rammed granular floor, raked and rolled rather than laid | 2 |
| `ballast` | crossed sleepers bedded in angular stone | 1 |
| `perf` | a modular tile drilled through on a close grid | 4 |
| `tslot` | a machined grid of T-slots in a heavy cast face | 1 |
| `polish` | saw-cut control joints in a ground face with the aggregate up | 3 |
| `ashlar` | squared stone in regular courses with fine joints | 2 |
| `glazing` | a glazed bay divided by its transoms and mullions | 2 |
| `corrugate` | deep profiled sheet, the ribs running full height | 2 |
| `gunite` | sprayed material, lumpy where the nozzle laid it | 5 |
| `sheet` | taped polythene sheeting with a lap seam every sheet width | 2 |
| `cabinet` | a row of cubicle doors with a handle and a vent on each | 2 |

## How a surface is chosen

Selection runs most-specific-first: the trade's **hazard**, then the trade's
**craft**, then the room's **function**. The record says which rule placed each
one, so the derivation can be read back rather than trusted.

| Placed by | Floors | Walls |
|---|---|---|
| hazard | 104 | 78 |
| craft | 389 | 247 |
| function | 728 | 896 |

The craft layer is the one that carries the growth. **30
crafts** are in use across the network and **0 halls
match none of them** — every trade in the bundle is dressed by its own work,
not by a fallback. A craft is read from the trade's own words; nothing here
assigns a hall to a craft by hand.

| Craft | Halls | Floor rules | Wall rules |
|---|---|---|---|
| `battery-craft` | 1 | machines → `esd-rubber`, materials → `vct-tile` | — (function default) |
| `blast-craft` | 1 | machines → `quartz-graphite`, tools → `alu-tread` | — (function default) |
| `buried-utility` | 3 | materials → `interlock-paver`, layout → `interlock-paver`, tools → `clay-paver` | materials → `engineering-brick` |
| `clean-process` | 2 | machines → `welded-vinyl`, materials → `welded-vinyl`, inspection → `stainless-deck`, documentation → `vct-tile` | machines → `stainless-splash`, materials → `stainless-splash`, inspection → `metro-tile-white` |
| `coatings` | 4 | machines → `flake-resin`, inspection → `flake-resin`, materials → `flake-terracotta`, tools → `blast-grit-bed` | machines → `chem-tile`, materials → `epoxy-wall-coat` |
| `concrete-craft` | 4 | procedure → `polished-slab`, machines → `broom-concrete`, materials → `granolithic-screed`, leadership → `polished-black` | materials → `fair-face-concrete`, leadership → `board-marked-concrete` |
| `containment-craft` | 7 | materials → `spill-berm`, tools → `welded-vinyl`, inspection → `mma-fast-cure`, coordination → `linoleum-sheet` | materials → `coved-white`, tools → `coved-white`, inspection → `clear-sheet-curtain` |
| `demolition-craft` | 1 | materials → `dry-shake-topping`, machines → `galv-checker`, coordination → `anhydrite-screed` | — (function default) |
| `digital-systems` | 10 | procedure → `access-perf`, machines → `esd-vinyl`, troubleshooting → `esd-vinyl`, materials → `perf-alu-tile` | procedure → `switchgear-lineup`, troubleshooting → `switchgear-lineup`, coordination → `plaster-slate` |
| `earthmoving-craft` | 4 | layout → `urethane-aisle-yellow`, tools → `larch-decking` | — (function default) |
| `finish-trade` | 4 | procedure → `terrazzo-divider`, inspection → `polished-slab`, coordination → `bamboo-strand`, documentation → `terrazzo-marble`, materials → `terrazzo-glass`, leadership → `porcelain-charcoal` | materials → `ply-lined`, coordination → `plaster-sage`, documentation → `perforated-ply` |
| `glass-envelope` | 3 | procedure → `polished-slab`, materials → `timber-plank`, coordination → `porcelain-sand` | procedure → `glazed-curtain`, inspection → `glazed-curtain`, leadership → `copper-panel`, machines → `anodised-alu-panel` |
| `hard-standing` | 2 | procedure → `asphalt-apron`, machines → `interlock-paver`, materials → `clay-paver`, layout → `granite-sett` | procedure → `corrugated-steel` |
| `hot-shop` | 3 | tools → `steel-plate`, troubleshooting → `steel-diamond`, layout → `dry-shake-topping`, leadership → `granolithic-screed` | tools → `gunned-castable`, troubleshooting → `gunned-insulating` |
| `lifting-gear` | 4 | tools → `steel-plate`, machines → `steel-diamond`, troubleshooting → `alu-tread` | machines → `mesh-guard` |
| `marine-craft` | 4 | machines → `steel-plate`, materials → `marine-deck`, tools → `iroko-bench-deck`, inspection → `polyurea-deck`, leadership → `teak-deck` | machines → `tank-plate` |
| `masonry-stone` | 4 | procedure → `broom-concrete`, materials → `crushed-stone`, tools → `quarry-tile`, coordination → `slate-flag`, leadership → `limestone-flag` | procedure → `ashlar-stone`, layout → `brick-common`, coordination → `limewashed-brick`, leadership → `plaster-ochre`, materials → `ashlar-grey` |
| `power-network` | 9 | machines → `crushed-stone`, materials → `crushed-stone`, procedure → `epoxy-slate-blue` | machines → `switchgear-lineup`, troubleshooting → `switchgear-lineup`, materials → `motor-control-face` |
| `precision-metal` | 3 | inspection → `tooling-plate`, layout → `tooling-plate`, machines → `steel-diamond`, troubleshooting → `beech-block`, documentation → `vct-tile` | machines → `perf-acoustic`, layout → `marker-glass` |
| `process-fluid` | 10 | procedure → `trench-drain`, machines → `resin-screed`, safety → `safety-vinyl-grit`, materials → `epoxy-plant-green`, tools → `alu-bar-grating` | machines → `liner-panel`, materials → `glazed-brick`, tools → `quarry-tile-wall` |
| `rail-craft` | 3 | procedure → `rail-ballast`, machines → `rail-ballast`, materials → `rail-timber-waybeam` | procedure → `mesh-guard`, machines → `mesh-guard` |
| `rescue-craft` | 1 | safety → `rubber-sheet-safety`, materials → `polyurea-deck` | — (function default) |
| `rope-access` | 3 | tools → `alu-tread`, documentation → `vct-tile` | coordination → `acoustic-rust`, materials → `brass-screen` |
| `sheet-membrane` | 8 | machines → `steel-plate`, materials → `steel-diamond`, procedure → `anhydrite-screed` | procedure → `corrugated-steel`, materials → `corrugated-steel`, leadership → `terracotta-rainscreen`, tools → `zinc-standing-seam` |
| `structural-steel` | 5 | materials → `steel-plate`, layout → `tooling-plate`, troubleshooting → `oak-end-block`, machines → `dry-shake-topping` | materials → `corrugated-steel` |
| `survey-control` | 3 | inspection → `polished-slab`, machines → `sealed-slab`, documentation → `linoleum-sheet` | coordination → `plaster-cream`, documentation → `acoustic-oat` |
| `timber-craft` | 2 | coordination → `oak-strip`, documentation → `ash-board`, leadership → `heart-pine-reclaimed`, tools → `maple-strip`, materials → `douglas-fir-plank` | leadership → `oak-panelled`, coordination → `pine-boarded`, tools → `birch-ply-lined` |
| `underground` | 3 | safety → `shotcrete-invert`, tools → `shotcrete-invert`, machines → `sprayed-fibrecrete` | safety → `rock-face`, tools → `rock-face` |
| `vehicle-shop` | 3 | machines → `trench-drain`, materials → `steel-diamond`, procedure → `slot-drain-resin`, tools → `epoxy-oxide-red` | machines → `liner-panel` |
| `weld-shop` | 2 | machines → `galv-checker`, materials → `anhydrite-screed` | — (function default) |

24 of the 30 crafts also carry a wall rule; the rest
leave their walls to the room's function default below.

## The hazard layer

A hazard is recorded only where it **changed** the outcome, which is why the
48 halls whose trade names no
finish-driving hazard and the
58 whose trade names no wall-driving one
say so explicitly instead of leaving a blank.

| Hazard | Halls | Floor rules | Wall rules |
|---|---|---|---|
| `confined-space` | 2 | procedure → `steel-plate`, machines → `steel-plate` | procedure → `tank-plate`, machines → `tank-plate` |
| `contaminant` | 8 | procedure → `spill-berm` | procedure → `coved-white` |
| `corrosive` | 7 | procedure → `acid-brick` | procedure → `chem-tile` |
| `explosives` | 1 | procedure → `conductive-tile`, materials → `conductive-tile` | — (function default) |
| `flammable-atmosphere` | 2 | procedure → `conductive-tile` | — (function default) |
| `hot-work` | 8 | procedure → `bare-slab` | procedure → `weld-screen` |
| `immersion` | 4 | procedure → `marine-deck` | procedure → `chem-tile` |
| `ionising-radiation` | 1 | procedure → `strippable-coat`, inspection → `strippable-coat` | procedure → `poly-enclosure`, inspection → `poly-enclosure` |
| `live-electrical` | 6 | procedure → `rubber-dielectric`, troubleshooting → `rubber-dielectric` | — (function default) |
| `mobile-plant` | 7 | procedure → `crushed-stone`, machines → `broom-concrete`, materials → `asphalt-apron` | procedure → `mesh-guard`, machines → `mesh-guard` |
| `molten-metal` | 4 | procedure → `firebrick-hearth`, machines → `firebrick-hearth`, materials → `foundry-sand` | procedure → `firebrick-face`, machines → `firebrick-face`, materials → `gunned-castable` |
| `particulate` | 1 | procedure → `welded-vinyl`, inspection → `welded-vinyl` | procedure → `coved-white`, inspection → `coved-white` |
| `rotating-machinery` | 5 | procedure → `epoxy-quartz`, machines → `steel-diamond` | machines → `perf-acoustic` |
| `stored-energy` | 3 | procedure → `esd-vinyl` | — (function default) |
| `suspended-load` | 7 | materials → `steel-plate` | materials → `mesh-guard` |
| `timber-trade` | 3 | procedure → `timber-plank` | procedure → `ply-lined` |
| `wet-process` | 6 | procedure → `steel-grate`, machines → `trench-drain` | procedure → `chem-tile` |
| `work-at-height` | 4 | procedure → `impact-mat`, safety → `impact-mat` | procedure → `impact-block`, safety → `impact-block` |

## The function defaults

Every room falls back to what the room is for. These are the 11 rooms
of `web/interiors.py`, and the strand list is imported from it rather than
retyped here.

| Room | Floor | Wall |
|---|---|---|
| Induction & PPE | `epoxy-smooth` | `painted-block` |
| Practice Bays | `sealed-slab` | `liner-panel` |
| Equipment Bay | `steel-checker` | `impact-block` |
| Tool Crib | `end-grain-block` | `ply-lined` |
| Materials Store | `sealed-slab` | `impact-block` |
| Layout Floor | `bare-slab` | `whiteboard-panel` |
| Inspection Bench | `epoxy-smooth` | `matte-board` |
| Diagnostic Bench | `anti-fatigue` | `ply-lined` |
| Briefing Room | `terrazzo-ground` | `acoustic-panel` |
| Records | `raised-access` | `acoustic-panel` |
| Classroom | `porcelain-tile` | `acoustic-panel` |

## The 84 floor finishes

| Finish | Key | Pattern | Tile | Roughness | Metalness | Why it exists |
|---|---|---|---|---|---|---|
| **Power-floated bare slab** | `bare-slab` | `slab` | 3.0 m | 0.92 | 0.02 | non-combustible with nothing underfoot to carry flame or spark |
| **Sealed concrete slab** | `sealed-slab` | `slab` | 3.0 m | 0.75 | 0.03 | dust-proofed general working floor that survives point loads |
| **Broom-finish concrete** | `broom-concrete` | `broom` | 3.0 m | 0.97 | 0.02 | traction outdoors and on wash-down ramps |
| **Smooth epoxy resin** | `epoxy-smooth` | `smooth` | 2.4 m | 0.35 | 0.05 | wipe-clean and chemical-resistant for controlled rooms |
| **Quartz-broadcast epoxy** | `epoxy-quartz` | `speckle` | 2.4 m | 0.6 | 0.04 | keeps grip when the process runs wet or oily |
| **Bermed epoxy with coved edge** | `spill-berm` | `smooth` | 2.4 m | 0.45 | 0.04 | contains a spill at the room boundary until it is recovered |
| **Welded sheet vinyl** | `welded-vinyl` | `smooth` | 1.8 m | 0.3 | 0.02 | particulates collect in joints, so the floor has none |
| **Static-dissipative vinyl** | `esd-vinyl` | `tile` | 0.6 m | 0.4 | 0.06 | bleeds charge to ground before it can find a spark path |
| **Dielectric rubber matting** | `rubber-dielectric` | `smooth` | 1.0 m | 0.9 | 0.0 | insulates the person standing at live equipment |
| **Anti-fatigue matting** | `anti-fatigue` | `smooth` | 1.0 m | 0.92 | 0.0 | long standing bench work punishes joints on hard floor |
| **Firebrick hearth** | `firebrick-hearth` | `brick` | 0.23 m | 0.95 | 0.02 | it will be spilled on, and must take molten metal |
| **Acid-resistant brick** | `acid-brick` | `brick` | 0.23 m | 0.8 | 0.02 | shrugs off the chemistry a plating or wash-down bay throws |
| **Checkerplate steel** | `steel-checker` | `checker` | 0.3 m | 0.45 | 0.85 | grip where machines drip oil, and it can be hosed |
| **Open steel grating** | `steel-grate` | `grate` | 0.3 m | 0.5 | 0.8 | the floor drains itself where water is the work |
| **Non-skid marine deck** | `marine-deck` | `speckle` | 1.2 m | 0.85 | 0.3 | grip that survives immersion and salt |
| **End-grain wood block** | `end-grain-block` | `block` | 0.1 m | 0.85 | 0.0 | kind to a dropped edge tool, and quiet underfoot |
| **Heavy timber planking** | `timber-plank` | `plank` | 0.14 m | 0.9 | 0.0 | the substrate formwork and carpentry actually fasten into |
| **Raised access floor** | `raised-access` | `tile` | 0.6 m | 0.5 | 0.15 | the services run under the floor, not across it |
| **Ground terrazzo** | `terrazzo-ground` | `speckle` | 1.2 m | 0.4 | 0.03 | a finish trade shows its own craft where people gather |
| **Porcelain tile** | `porcelain-tile` | `tile` | 0.6 m | 0.35 | 0.02 | hard, flat and truthful under a straightedge |
| **Compacted crushed stone** | `crushed-stone` | `speckle` | 1.5 m | 0.98 | 0.0 | the ground plant actually digs, piles and tracks on |
| **Asphalt apron** | `asphalt-apron` | `speckle` | 3.0 m | 0.96 | 0.02 | the yard running surface between door and stockpile |
| **Ground and polished slab** | `polished-slab` | `polish` | 2.4 m | 0.18 | 0.04 | a concrete trade grinds its own floor back to the aggregate to show what it put down |
| **Diamond tread plate** | `steel-diamond` | `diamond` | 0.4 m | 0.42 | 0.88 | a raised lozenge holds a boot on a deck a machine leaks onto |
| **Sealed steel plate deck** | `steel-plate` | `plate` | 1.2 m | 0.38 | 0.9 | a welded deck spreads a point load and can be cut and let back in |
| **Divider-strip terrazzo** | `terrazzo-divider` | `terrazzo` | 1.2 m | 0.35 | 0.05 | the strip is where the pour stops and the next one starts, and setting it out is the whole of the craft |
| **Broadcast flake resin** | `flake-resin` | `flake` | 2.0 m | 0.55 | 0.04 | flake hides the drip and the scuff a coating bay makes daily |
| **Heavy-duty resin screed** | `resin-screed` | `smooth` | 2.0 m | 0.62 | 0.03 | takes steam and cold water an hour apart without lifting |
| **Conductive floor tile** | `conductive-tile` | `tile` | 0.6 m | 0.45 | 0.1 | charge has to reach earth faster than the atmosphere can find a spark |
| **Floor to falls with trench drain** | `trench-drain` | `trench` | 2.4 m | 0.7 | 0.06 | the wash water leaves by a route somebody chose |
| **Rammed moulding-sand floor** | `foundry-sand` | `sand` | 1.6 m | 0.99 | 0.0 | the floor and the mould are the same material, and the pour goes into both |
| **Ballasted track bed** | `rail-ballast` | `ballast` | 1.4 m | 0.98 | 0.02 | the track is only as true as the stone under it, so the stone is the floor |
| **Interlocking concrete paving** | `interlock-paver` | `brick` | 0.45 m | 0.88 | 0.02 | a buried-service trade has to lift the surface and put it back the same afternoon |
| **Perforated access floor tile** | `access-perf` | `perf` | 0.6 m | 0.48 | 0.18 | the cold air arrives through the floor, and which tile is open is a decision somebody logs |
| **Shotcrete invert** | `shotcrete-invert` | `gunite` | 2.0 m | 0.96 | 0.02 | the floor of a heading is sprayed the same hour the roof is |
| **T-slotted cast-iron floor plate** | `tooling-plate` | `tslot` | 0.9 m | 0.4 | 0.8 | a workpiece is only square to what it is clamped to |
| **Strippable decontamination coating** | `strippable-coat` | `smooth` | 2.4 m | 0.3 | 0.02 | the contamination leaves with the coating instead of with the person |
| **Impact-absorbing mat** | `impact-mat` | `smooth` | 1.2 m | 0.94 | 0.0 | a fall-arrest demonstration ends on the floor, and this is the floor it should end on |
| **White oak strip floor** | `oak-strip` | `plank` | 0.12 m | 0.78 | 0.0 | the hardwood a joinery trade lays in its own meeting room, because the room is the first thing it is judged on |
| **Ash board floor** | `ash-board` | `plank` | 0.16 m | 0.82 | 0.0 | pale, straight-grained and cheap to lift when the cable under the record room floor has to be got at |
| **Reclaimed heart pine** | `heart-pine-reclaimed` | `plank` | 0.18 m | 0.86 | 0.0 | lifted out of an old mill floor and laid again: the board room of a trade that argues for reuse should be made of it |
| **Hard maple strip floor** | `maple-strip` | `plank` | 0.1 m | 0.7 | 0.0 | the hardest of the common shop timbers, and the one a bench room floor survives a dropped chisel on |
| **Douglas fir plank** | `douglas-fir-plank` | `plank` | 0.2 m | 0.88 | 0.0 | the stock a framing trade racks, laid as the floor of the room it is racked in |
| **Beech end-grain block** | `beech-block` | `block` | 0.08 m | 0.8 | 0.0 | end grain takes a blade point-first and closes behind it, which is why a cutting bench stands on it |
| **Laid teak deck** | `teak-deck` | `plank` | 0.09 m | 0.8 | 0.0 | the deck a shipwright lays and caulks, and the one piece of their work anybody outside the yard ever walks on |
| **Iroko bench decking** | `iroko-bench-deck` | `plank` | 0.15 m | 0.84 | 0.0 | oily enough to sit in salt water and not move, which is the whole reason a fitting-out bench is built of it |
| **Strand-woven bamboo** | `bamboo-strand` | `plank` | 0.13 m | 0.72 | 0.0 | a floor-laying trade keeps a bay of the newest substrate it is asked to lay over, and this is currently that |
| **Oak end-grain block** | `oak-end-block` | `block` | 0.09 m | 0.86 | 0.0 | a fitter kneels at a stripped machine for an hour, and oak end grain is kinder to a knee than steel and harder than a mat |
| **Open larch decking** | `larch-decking` | `plank` | 0.14 m | 0.92 | 0.0 | slatted and laid clear of the ground, so a store where everything arrives wet drains instead of rotting |
| **Timber waybeam** | `rail-timber-waybeam` | `plank` | 0.3 m | 0.92 | 0.0 | the longitudinal timber a rail sits on where there is no ballast to sit in, and the thing a signals hall racks |
| **Welded linoleum sheet** | `linoleum-sheet` | `smooth` | 2.0 m | 0.55 | 0.01 | linseed oil and cork dust on jute: warm underfoot, and it takes a dropped instrument without chipping |
| **Welded rubber sheet** | `rubber-sheet-safety` | `smooth` | 1.6 m | 0.88 | 0.0 | a rescue drill puts people on the floor repeatedly, and rubber sheet is what stops that becoming the injury |
| **Vinyl composition tile** | `vct-tile` | `tile` | 0.3 m | 0.45 | 0.01 | cheap, replaceable one tile at a time, and the reason a record room floor can be repaired on a Friday afternoon |
| **Grit-grip safety vinyl** | `safety-vinyl-grit` | `speckle` | 1.8 m | 0.65 | 0.02 | carborundum through the wear layer, for the floor between a wet plant room and a dry corridor |
| **Static-dissipative rubber** | `esd-rubber` | `smooth` | 1.4 m | 0.86 | 0.04 | bleeds a charge away slowly enough not to be a shock path and fast enough not to let one build at a cell rack |
| **Oxide-red epoxy coating** | `epoxy-oxide-red` | `smooth` | 2.4 m | 0.38 | 0.03 | red reads as the working bay in every yard that uses colour at all, and a trainee learns the convention by walking it |
| **Plant-room green epoxy** | `epoxy-plant-green` | `smooth` | 2.4 m | 0.36 | 0.03 | green is the safe route through a plant room, and the floor is where the route is drawn |
| **Slate-blue epoxy coating** | `epoxy-slate-blue` | `smooth` | 2.4 m | 0.34 | 0.03 | a cold blue under array work makes a dropped washer visible instead of lost |
| **Aisle-yellow urethane coat** | `urethane-aisle-yellow` | `smooth` | 1.2 m | 0.4 | 0.03 | the aisle is the drawing: a plant yard is set out in yellow before it is set out on paper |
| **Fast-cure acrylic coating** | `mma-fast-cure` | `smooth` | 2.2 m | 0.3 | 0.03 | goes down and is walked on the same shift, which is the only reason a room in use can be recoated at all |
| **Polyurea deck coating** | `polyurea-deck` | `smooth` | 2.0 m | 0.48 | 0.04 | sprayed thick over a steel deck and flexible enough to stay stuck to it while the deck works |
| **Terracotta flake resin** | `flake-terracotta` | `flake` | 2.0 m | 0.58 | 0.03 | warm flake hides the overspray a coating bay makes every day without hiding a spill |
| **Graphite quartz broadcast** | `quartz-graphite` | `speckle` | 2.4 m | 0.62 | 0.04 | dark and hard: a shot-loading bench wants grip and wants nothing that sparks |
| **Unglazed quarry tile** | `quarry-tile` | `brick` | 0.2 m | 0.7 | 0.02 | fired through, so it wears to the same colour it started and a chipped corner is not a pale scar |
| **Charcoal porcelain tile** | `porcelain-charcoal` | `tile` | 0.6 m | 0.32 | 0.02 | a dark, flat floor is the fairest ground to judge a light finish sample against |
| **Sand porcelain tile** | `porcelain-sand` | `tile` | 0.6 m | 0.34 | 0.02 | warm and low-contrast, so a glazing trade reads the light coming through a bay rather than the floor bouncing it |
| **Riven slate flag** | `slate-flag` | `tile` | 0.5 m | 0.8 | 0.02 | split rather than sawn, so no two flags are the same thickness and bedding them is the skill |
| **Limestone flag** | `limestone-flag` | `tile` | 0.6 m | 0.76 | 0.02 | the stone the banker shop cuts, laid whole where the hall wants to show what it cuts |
| **Granite sett paving** | `granite-sett` | `brick` | 0.12 m | 0.9 | 0.02 | small, square and laid to a cambered fall: the paving a crew still sets by eye and a string line |
| **Clay paver floor** | `clay-paver` | `brick` | 0.22 m | 0.86 | 0.02 | lifted, stacked and relaid the same afternoon, which is the whole argument for a paved surface over a poured one |
| **Marble-chip terrazzo** | `terrazzo-marble` | `terrazzo` | 1.2 m | 0.38 | 0.03 | the chip is the finish: what is ground back decides the floor, and choosing it is the trade |
| **Recycled-glass terrazzo** | `terrazzo-glass` | `terrazzo` | 1.2 m | 0.36 | 0.04 | crushed glass in the matrix instead of stone, which grinds differently and is the argument a sample bay exists to settle |
| **Granolithic screed** | `granolithic-screed` | `polish` | 2.0 m | 0.84 | 0.02 | a wearing topping laid monolithic with the slab under it, and the thing a stock bay actually needs |
| **Black-pigmented polished slab** | `polished-black` | `polish` | 2.4 m | 0.16 | 0.04 | pigment through the pour and ground back: the finish a concrete trade puts in its own board room to end the argument |
| **Aluminium tread plate** | `alu-tread` | `diamond` | 0.4 m | 0.4 | 0.7 | a magazine tool store wants a floor that cannot strike a spark off a dropped steel tool |
| **Galvanised checkerplate** | `galv-checker` | `checker` | 0.3 m | 0.48 | 0.78 | the zinc is why it can stand under a weld bay that gets hosed out and still be there in ten years |
| **Stainless plate deck** | `stainless-deck` | `plate` | 1.2 m | 0.3 | 0.82 | wiped down every shift and never rusts into the wipe, which is what a controlled room means by cleanable |
| **Aluminium bar grating** | `alu-bar-grating` | `grate` | 0.3 m | 0.45 | 0.65 | light enough that one person lifts a panel to get at the pipework the grating is there to cover |
| **Perforated aluminium tile** | `perf-alu-tile` | `perf` | 0.6 m | 0.42 | 0.6 | open area, in a floor whose whole job is to hand cold air upward where somebody decided it should go |
| **Resin floor to falls with slot drain** | `slot-drain-resin` | `trench` | 2.4 m | 0.55 | 0.04 | a wash bay is a floor with a decision in it: where the water goes, and how fast |
| **Sprayed fibre-reinforced concrete** | `sprayed-fibrecrete` | `gunite` | 2.0 m | 0.95 | 0.02 | fibre instead of mesh, so the invert of a heading can be sprayed in one pass behind the face |
| **Metallic dry-shake topping** | `dry-shake-topping` | `slab` | 3.0 m | 0.7 | 0.12 | iron aggregate floated into the green slab: the hardest wearing surface a demolition yard can put under tracked plant |
| **Anhydrite flowing screed** | `anhydrite-screed` | `slab` | 3.0 m | 0.8 | 0.02 | poured level by its own weight, which is why a long shop floor can be flat without anyone tamping it |
| **Blast-grit floor** | `blast-grit-bed` | `sand` | 1.6 m | 0.97 | 0.03 | the spent grit IS the floor of a blast bay until it is swept and screened, and it is walked on in that state |

## The 51 wall finishes

| Finish | Key | Pattern | Tile | Roughness | Metalness | Why it exists |
|---|---|---|---|---|---|---|
| **Painted concrete block** | `painted-block` | `block` | 0.4 m | 0.88 | 0.02 | the general working wall: takes a knock, takes a repaint |
| **Impact-faced block with kerb** | `impact-block` | `block` | 0.4 m | 0.9 | 0.02 | stock and plant hit this wall, so the bottom of it is the part that is built to be hit |
| **Washable liner panel** | `liner-panel` | `panel` | 0.9 m | 0.55 | 0.12 | a practice bay gets hosed out, and a lined wall sheds water instead of soaking it |
| **Plywood-lined shop wall** | `ply-lined` | `plywood` | 1.2 m | 0.85 | 0.0 | you hang tools, jigs and a cut list off a wall you can screw into |
| **Full-height marker panel** | `whiteboard-panel` | `board` | 1.2 m | 0.22 | 0.04 | setting out is drawn before it is built, and the wall is the first place it gets drawn |
| **Matte low-glare board** | `matte-board` | `board` | 1.2 m | 0.82 | 0.02 | inspection reads surfaces at a raking angle, and a shiny wall throws the light back into the work |
| **Fabric-faced acoustic panel** | `acoustic-panel` | `fabric` | 0.6 m | 0.95 | 0.0 | a room where people talk over each other is a room where the decision gets made twice |
| **Firebrick wall face** | `firebrick-face` | `brick` | 0.23 m | 0.95 | 0.02 | the wall beside a pour takes the same spatter the hearth does |
| **Non-combustible screened bay** | `weld-screen` | `screen` | 0.8 m | 0.92 | 0.05 | the arc is not only the welder's problem: the bay walls stop the flash reaching the next bay |
| **Glazed chemical-resistant tile** | `chem-tile` | `tile` | 0.3 m | 0.3 | 0.03 | what the floor shrugs off, the splash-back has to shrug off too |
| **Coved cleanable wall** | `coved-white` | `smooth` | 1.5 m | 0.35 | 0.02 | a square corner is somewhere particulate can sit, so the room has no square corners |
| **Guarded mesh partition** | `mesh-guard` | `mesh` | 0.35 m | 0.7 | 0.55 | you have to see into a bay you are not allowed to walk into |
| **Common brick wall** | `brick-common` | `brick` | 0.23 m | 0.92 | 0.02 | a bricklaying hall is judged on a wall, so the hall has one to be judged against |
| **Coursed ashlar stone** | `ashlar-stone` | `ashlar` | 0.6 m | 0.88 | 0.02 | the banker shop matches an existing course, and the course has to be on the wall to be matched |
| **Glazed curtain wall bay** | `glazed-curtain` | `glazing` | 1.5 m | 0.12 | 0.35 | a glazing trade tests against a real bay, because a sealed joint only fails where the light gets in |
| **Profiled steel cladding** | `corrugated-steel` | `corrugate` | 0.7 m | 0.6 | 0.5 | the cladding trade fixes to the wall it also makes, and the rib spacing is the whole argument |
| **Stainless splash-back** | `stainless-splash` | `plate` | 1.0 m | 0.28 | 0.75 | a wall that is wiped down every shift should not be made of something that minds being wiped down |
| **Gunned refractory castable** | `gunned-castable` | `gunite` | 0.8 m | 0.96 | 0.02 | a lining is sprayed, not laid, and what it looks like wet is what it looks like for the next four years |
| **Sheeted negative-pressure enclosure** | `poly-enclosure` | `sheet` | 1.2 m | 0.4 | 0.02 | the room is built the morning the work starts and binned the evening it clears |
| **Switchgear lineup face** | `switchgear-lineup` | `cabinet` | 0.9 m | 0.35 | 0.45 | in an electrical room the wall IS the equipment, and the labels on it are the only map anyone has |
| **Perforated metal acoustic liner** | `perf-acoustic` | `perf` | 0.6 m | 0.7 | 0.4 | a machine hall is loud because the walls give it all back, unless the walls are built not to |
| **Shotcreted rock face** | `rock-face` | `gunite` | 1.0 m | 0.97 | 0.02 | underground the wall is the ground, and what holds it up is sprayed onto it |
| **Lapped tank plate** | `tank-plate` | `plate` | 1.2 m | 0.78 | 0.55 | you enter a vessel through a shell you can read: the laps, the seams and where the primer has gone |
| **Oak-panelled board room** | `oak-panelled` | `plank` | 0.6 m | 0.78 | 0.0 | the room where the trade argues about its own standards is panelled to that standard, and everyone in it can see the joint |
| **Whitewood board lining** | `pine-boarded` | `plank` | 0.5 m | 0.85 | 0.0 | a boarded wall can be cut into, patched and boarded again, which is what a room used for practice needs |
| **Birch ply lining** | `birch-ply-lined` | `plywood` | 1.2 m | 0.8 | 0.0 | the face veneer is good enough to leave unpainted, so the wall shows every screw somebody put in it |
| **Limewashed brick** | `limewashed-brick` | `brick` | 0.23 m | 0.9 | 0.02 | lime lets the brick behind it dry out, which is the argument a restoration trade has with paint every week |
| **Blue engineering brick** | `engineering-brick` | `brick` | 0.23 m | 0.8 | 0.02 | dense enough not to take up water, which is why it is the brick below ground and in a chamber that floods |
| **Glazed white brick** | `glazed-brick` | `brick` | 0.23 m | 0.28 | 0.02 | a fired glaze on a structural unit: it washes down like tile and takes a knock like brick |
| **Fair-faced concrete** | `fair-face-concrete` | `slab` | 0.9 m | 0.86 | 0.02 | the pour is the finish, so the formwork, the release agent and the vibration are all on show and cannot be made good later |
| **Board-marked concrete** | `board-marked-concrete` | `plank` | 0.8 m | 0.88 | 0.02 | sawn boards used as form face leave their grain in the concrete, and setting them out is the whole of the work |
| **Painted plaster, cream** | `plaster-cream` | `smooth` | 1.5 m | 0.82 | 0.01 | a warm near-white throws light back into a room people read drawings in without glaring off the paper |
| **Painted plaster, sage** | `plaster-sage` | `smooth` | 1.5 m | 0.84 | 0.01 | a muted green is the one wall colour a finish sample can be held against without the wall deciding the answer |
| **Painted plaster, slate** | `plaster-slate` | `smooth` | 1.5 m | 0.84 | 0.01 | dark walls stop a screen-lit room reflecting itself back at the people reading the screens |
| **Painted plaster, ochre** | `plaster-ochre` | `smooth` | 1.5 m | 0.84 | 0.01 | earth pigment on lime plaster is the oldest painted wall the trade still makes, and the one it is asked to match |
| **Epoxy-coated wall** | `epoxy-wall-coat` | `smooth` | 1.5 m | 0.35 | 0.03 | the coating a coatings trade puts on everyone else's walls, on its own, where the failures can be left up and looked at |
| **Perforated ply acoustic lining** | `perforated-ply` | `perf` | 0.6 m | 0.75 | 0.0 | holes and a void behind them: the cheapest honest way to stop a hard room ringing, and visible enough to teach from |
| **Terracotta rainscreen** | `terracotta-rainscreen` | `panel` | 0.7 m | 0.7 | 0.05 | extruded and fired, hung on rails with an open joint, so the cavity behind it does the waterproofing |
| **Zinc standing seam** | `zinc-standing-seam` | `corrugate` | 0.7 m | 0.55 | 0.45 | the seam is folded on site and is the only thing holding the weather out, which is why it is practised indoors first |
| **Copper panel** | `copper-panel` | `panel` | 0.7 m | 0.45 | 0.6 | it changes colour for thirty years after it is fixed, so a sample wall is the only way to argue about the finish |
| **Anodised aluminium panel** | `anodised-alu-panel` | `panel` | 0.7 m | 0.35 | 0.55 | the colour is grown into the oxide rather than painted on, and a scratch cannot be touched in |
| **Acoustic panel, oatmeal** | `acoustic-oat` | `fabric` | 0.6 m | 0.95 | 0.0 | a quiet room in a warm colour, because a room people write in all day should not feel like a booth |
| **Acoustic panel, rust** | `acoustic-rust` | `fabric` | 0.6 m | 0.95 | 0.0 | the absorber has to be somewhere people look, so it is worth it being a colour they do not mind looking at |
| **Glazed white wall tile** | `metro-tile-white` | `tile` | 0.3 m | 0.25 | 0.02 | a small glazed tile has a lot of grout in it, and keeping that grout sound is the discipline the room is teaching |
| **Green quarry tile** | `quarry-tile-wall` | `tile` | 0.3 m | 0.35 | 0.02 | the splash-back behind a wet bench, in a colour that does not show every drip and does show a crack |
| **Glass marker wall** | `marker-glass` | `glazing` | 1.5 m | 0.1 | 0.2 | you can set out full size on glass, wipe it, and see the work through it while you do |
| **Grey ashlar course** | `ashlar-grey` | `ashlar` | 0.6 m | 0.88 | 0.02 | a second stone to match against, because matching one existing course teaches nothing about matching a different one |
| **Brass-infilled screen** | `brass-screen` | `screen` | 0.8 m | 0.55 | 0.5 | rope and hardware have to be visible from outside the store without the store being open |
| **Motor control centre face** | `motor-control-face` | `cabinet` | 0.9 m | 0.4 | 0.4 | a wall of starters and their labels: the room is the equipment, and reading it is the lesson |
| **Clear sheeted curtain** | `clear-sheet-curtain` | `sheet` | 1.2 m | 0.3 | 0.02 | you can watch a containment being used without being inside it, which is the only safe way to assess one |
| **Gunned insulating lining** | `gunned-insulating` | `gunite` | 0.8 m | 0.96 | 0.02 | a practice lining, gunned onto a wall so it can be cut into, read and gunned again next week |

## Provenance, and what this is not

| Field | Tier |
|---|---|
| geometry | SCHEMATIC |
| finish | DERIVED |
| wall | DERIVED |
| catalogue | AUTHORED |
| placement | DERIVED |
| conditions | DERIVED |
| discipline | RECORDED/DERIVED/SCHEMATIC tagging after the Locator.X rooms module (Apache-2.0) |

- **Not a code reference.** General good practice, not a code reference; no figure is read from any jurisdiction's standard and no surface names a product, brand, fire rating or specification number. A real deployment replaces these with the local standard.
- **Not sampled.** Every colour, roughness and metalness in both catalogues is AUTHORED - chosen by eye against what the material is, and never sampled from a photograph, a measured swatch or a supplier's data. What is DERIVED is only which hall stands on which, read from the trade's own words.
- **Not a survey.** A finish records what a room is for and what its trade
  does. It records nothing about any real building, and no floor plan in this
  bundle has collected an address.

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
