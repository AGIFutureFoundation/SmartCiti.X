# The furniture

300 pieces of furniture in 12 families, every one cut
from one of 36 forms and built in the browser out of boxes and
cylinders. 108 of them are standing in halls today — that is
[Room-Props](Room-Props.md)'s page. The other 192 are the district
catalogue, and they are built, measured, priced and **not drawn**.

**Nothing here is a model of anything.** SCHEMATIC: every piece in this pack is a handful of boxes and cylinders built in the browser from the recipe printed here. No mesh is loaded, no model is vendored, no texture is fetched, and nothing is generated at view time.

These are shapes in a training environment. The eyewash stand is a cylinder and a bowl standing where a room record says corrosives are handled; the extinguisher is a cylinder on a plate; the press is a bed, a ram and a box with a dial on it. They are not fixture specifications, not rated appliances, not machine specifications, not compliance artefacts, and not evidence that any equipment has been provided anywhere. Nothing in this pack should be read as a safety-equipment specification, and a learner who has walked past one has not been trained on it.

Read one off the registry rather than take that on trust. The first piece in
the district catalogue is **Connection bolt-up bench**: 10 boxes
and 1 cylinder cut from the
`vice-bench` form, 144 triangles at
1.45 × 1.2 × 0.7 m, standing there because the
Structural crib issues the spud wrench,
which aligns bolt holes and pins the steel connection. That is the *shape* of the work the tool is done at. It is not any manufacturer's model, it carries no
rating, and it is not evidence that any hall has one.

## Fitted from what the union actually issues

The district catalogue is derived from the real tools the district cribs carry.
96 tools across 8 cribs, read from
`tools/registry/toolcribs.json cribs[*].tools` — the same registry [Toolrooms](Toolrooms.md) draws — at
2 pieces a tool. One piece for the work the tool is done at and one for where the tool lives, for every tool in every district crib. A piece's district is the district of the crib that carries its tool and is never typed on the piece.

So a hall is fitted from its own union's issue list rather than from a generic
shop. 195 of the 300 pieces name a
tool, and 96 of the 96 tools in the
cribs are named by at least one piece.

| District | Crib | Tools | Halls | Pieces |
|---|---|---|---|---|
| **Survey, Safety & Environment** | Survey, safety & environment tool crib | 12 | 11 | 24 |
| **Earthworks & Plant** | Earthworks & plant tool crib | 12 | 12 | 24 |
| **Energy & Utilities** | Energy & utilities tool crib | 12 | 17 | 24 |
| **Envelope & Finish** | Envelope & finish tool crib | 12 | 21 | 24 |
| **Heavy Industry** | Heavy-industry tool crib | 12 | 10 | 24 |
| **Structural** | Structural tool crib | 12 | 12 | 24 |
| **Building Systems** | Building-systems tool crib | 12 | 18 | 24 |
| **Transport & Mobility** | Transport & mobility tool crib | 12 | 10 | 24 |

## Why they are not standing

The 192 district pieces are NOT standing in any hall. placeRoomProps() chooses a room's furniture from D.props.by_strand[r.strand] and from that room's own PPE list, and neither of those has a hall in it — the eleven rooms are the same eleven rooms in all 111 halls. Putting a glazier's suction-cup rack in the strand table would stand it in every ironworkers' hall too, so it is not there. What is published instead is the fit-out computed per district and per room, its geometry, and its cost priced against the same ceiling as the drawn set. It waits on one change this pack does not own: a hall dimension on the furniture lookup in web/build_3d.py.

## The forms

Three hundred hand-placed part lists would be three hundred chances to put a shelf through a leg. Every piece is cut from one of these forms at its own dimensions and its own part counts, and the form it was cut from is published with it. The forms are read from `props/build.py`:

`bench` · `bin` · `cabinet` · `cantilever` · `cart` · `cradle` · `crates` · `drawers` · `drum` · `drying-rack` · `easel` · `gang-box` · `hopper` · `locker` · `oven` · `pallet` · `pedestal` · `pipe-rack` · `press` · `rack` · `reel` · `screen` · `sink` · `spool` · `stool` · `table` · `tank` · `tree` · `trestle` · `vice-bench` · `wall-board` · `wall-cabinet` · `wall-cradle` · `wall-peg` · `wall-reel` · `wall-shelf`

6 of those hang on a wall rather than stand on the floor.

| Family | What it is |
|---|---|
| **bench** | a horizontal surface work happens on top of |
| **storage** | something that holds what a room keeps between sessions |
| **board** | a vertical surface a room reads from |
| **seat** | something a person is off their feet on |
| **vessel** | an open container things go into and come out of |
| **stand** | a freestanding upright a piece of apparatus lives on |
| **stock** | the material a trade works on, held the way that trade holds it before it is cut, bent, spliced or set |
| **waste** | what the work leaves behind, kept where the trade keeps it rather than swept out of the render |
| **machine** | a schematic device the work is driven through — a shape with a bed, a head and a control, not a machine specification and not any manufacturer's model |
| **screen** | a vertical barrier that stops an arc, a spark, a splash or a line of sight |
| **trolley** | something the work is moved on rather than carried |
| **safety-fixture** | a schematic shape standing where a room record asks for protective equipment — not a specification |

## Distinct, and honestly repeated

247 of the 300 pieces are geometrically distinct and
53 repeat an earlier part list exactly. A bin is a bin. Where two pieces of furniture really are the same solid — a bolt bin and a shackle bin, two four-shelf racks of the same span — this pack builds the same part list twice rather than nudging a dimension to make the count look better. The number of those is published beside the number of distinct ones so a reader can judge it.
The key that decides it is the recipe's part list exactly as it ships, positions, sizes and counts included.

## What the whole catalogue would cost

A hall interior is draw-call bound, not triangle bound. Every piece here pools, none takes a mesh of its own, none is instanced any more, and every one of the three hundred names one of seven materials the page already builds — so the catalogue grew more than tenfold while the draw calls it costs went DOWN, from one per pooled material plus one per instanced fixture to one per pooled material. The budget block refuses a design that would change that.

The ceiling is read from `web/eval_scene.mjs` (hall view):
157 draw calls measured against 196 permitted,
3,806 triangles against 15,224.

What a hall would cost if the district catalogue were drawn too — the same rooms, the same walls, the same pool, with each hall offered its own district's pieces between its conditions fixtures and its shop furniture.

| | Median | Max |
|---|---|---|
| Pieces in a hall | 81 | 93 |
| Triangles | 8,292 | 9,136 |
| Draw calls | — | 7 |

New materials: **0**. New draw calls over the drawn set:
**0**. The whole catalogue in every hall costs 0 more draw calls than the drawn set, because the pieces share its seven materials and a room's walls hold what they hold.

Every prop in this pack names one of seven keys of the page's own shared material table. A pooled prop of a material the pack already uses is free at the draw call; the first prop to name an eighth material would add one merged mesh to every hall in the bundle. The vocabulary grew from twenty-nine pieces to three hundred without naming one.

## The wall is the budget

A room has two partitions and about three metres of usable run on each, and that — not the GPU — is what decides how much furniture stands in it. The fit-out below is simulated against those metres with the run SHARED between pieces, the way the page shares it, so the triangle figure is what the walls hold rather than what the catalogue offers.

The room's two partitions are filled from the doorway end in the order the page fills them — the room's own conditions fixtures first, then its shop furniture — with the run SHARED between pieces, one interval list per partition and one back corner per side. Counted independently a piece always fits, because nothing else is standing there. Counted together they run out of wall, and the wall is what the hall actually costs. And it is an upper bound:
the page cuts doorways out of these runs and reserves the tools room's right partition for the district crib it already draws, so it stands fewer than this. window.__tc3dProps() reports the difference per prop.

| | Per hall | Per room |
|---|---|---|
| Pieces offered (median) | 72 | 6 |
| Instances stood (median) | 75 | 6 |

## The 192 district pieces

Each row names the tool that admitted it and the district whose crib carries
that tool. Neither is typed on the piece.

| Piece | Form | Triangles | Size | Material | From the tool | District |
|---|---|---|---|---|---|---|
| **Connection bolt-up bench** | `vice-bench` | 144 | 1.45 × 1.2 × 0.7 m | `steel` | Spud wrench | Structural |
| **Bolt and drift bin** | `bin` | 84 | 0.85 × 0.55 × 0.55 m | `metal` | Spud wrench | Structural |
| **Beam alignment trestle** | `trestle` | 84 | 1.45 × 0.95 × 0.55 m | `steel` | Sleever bar | Structural |
| **Sleever bar cradle** | `wall-cradle` | 60 | 1.35 × 0.38 × 0.22 m | `metal` | Sleever bar | Structural |
| **Hole alignment jig table** | `table` | 84 | 1.4 × 0.8 × 0.8 m | `steel` | Bull pin | Structural |
| **Pin and wedge drawers** | `drawers` | 132 | 0.8 × 1.05 × 0.5 m | `steel` | Bull pin | Structural |
| **Torque check bench** | `bench` | 72 | 1.4 × 0.88 × 0.65 m | `wood` | Torque wrench | Structural |
| **Torque wrench cradle** | `wall-cradle` | 60 | 1.0 × 0.34 × 0.22 m | `wood` | Torque wrench | Structural |
| **Rigging lay-down table** | `table` | 84 | 1.45 × 0.7 × 1.0 m | `wood` | Rigging shackle | Structural |
| **Shackle and pin bin** | `bin` | 84 | 0.75 × 0.5 × 0.55 m | `metal` | Rigging shackle | Structural |
| **Sling inspection rail** | `drying-rack` | 108 | 1.4 × 1.65 × 0.4 m | `metal` | Wire-rope sling | Structural |
| **Sling storage tree** | `tree` | 152 | 0.68 × 1.6 × 0.68 m | `metal` | Wire-rope sling | Structural |
| **Hoist proof frame** | `cantilever` | 72 | 1.4 × 1.7 × 0.4 m | `steel` | Lever hoist | Structural |
| **Chain hoist rack** | `rack` | 96 | 1.2 × 1.55 × 0.5 m | `metal` | Lever hoist | Structural |
| **Trial flange beam** | `cradle` | 72 | 1.45 × 0.85 × 0.5 m | `steel` | Beam clamp | Structural |
| **Beam clamp drawers** | `drawers` | 108 | 0.85 × 1.0 × 0.48 m | `steel` | Beam clamp | Structural |
| **Plumbing-up post** | `pedestal` | 96 | 0.36 × 1.3 × 0.36 m | `metal` | Plumb bob | Structural |
| **Line and bob shelf** | `wall-shelf` | 72 | 0.8 × 0.6 × 0.24 m | `wood` | Plumb bob | Structural |
| **Layout punch bench** | `bench` | 84 | 1.45 × 0.9 × 0.7 m | `steel` | Center punch | Structural |
| **Punch and chisel board** | `wall-peg` | 156 | 1.1 × 0.9 × 0.12 m | `paint` | Center punch | Structural |
| **Bolt gauge station** | `table` | 84 | 1.2 × 0.82 × 0.7 m | `steel` | Bolt gauge | Structural |
| **Fastener sample cabinet** | `cabinet` | 96 | 0.95 × 1.35 × 0.42 m | `wood` | Bolt gauge | Structural |
| **Impact wrench service bench** | `bench` | 84 | 1.45 × 0.9 × 0.7 m | `steel` | Impact wrench | Structural |
| **Socket and anvil drawers** | `drawers` | 132 | 0.9 × 1.0 × 0.52 m | `metal` | Impact wrench | Structural |
| **Board trimming bench** | `bench` | 84 | 1.45 × 0.88 × 0.8 m | `wood` | Utility knife | Envelope & Finish |
| **Spent blade bin** | `drum` | 84 | 0.4 × 0.6 × 0.4 m | `metal` | Utility knife | Envelope & Finish |
| **Taping trestle** | `trestle` | 84 | 1.45 × 0.95 × 0.5 m | `wood` | Taping knife | Envelope & Finish |
| **Knife and hawk shelf** | `wall-shelf` | 84 | 1.0 × 0.7 × 0.26 m | `wood` | Taping knife | Envelope & Finish |
| **Mortar board bench** | `bench` | 72 | 1.45 × 0.84 × 0.75 m | `part` | Brick trowel | Envelope & Finish |
| **Trowel wash tank** | `tank` | 140 | 0.64 × 0.95 × 0.64 m | `part` | Brick trowel | Envelope & Finish |
| **Pointing practice table** | `table` | 84 | 1.4 × 0.8 × 0.8 m | `wood` | Brick jointer | Envelope & Finish |
| **Jointer and raker rack** | `rack` | 108 | 1.0 × 1.35 × 0.38 m | `metal` | Brick jointer | Envelope & Finish |
| **Tile setting bench** | `bench` | 84 | 1.45 × 0.86 × 0.75 m | `wood` | Grout float | Envelope & Finish |
| **Grout mixing bin** | `bin` | 84 | 0.8 × 0.6 × 0.6 m | `part` | Grout float | Envelope & Finish |
| **Glass handling stand** | `cantilever` | 72 | 1.3 × 1.55 × 0.5 m | `part` | Glass suction cup | Envelope & Finish |
| **Glazing cup rack** | `rack` | 96 | 1.0 × 1.3 × 0.4 m | `metal` | Glass suction cup | Envelope & Finish |
| **Sealant run bench** | `bench` | 72 | 1.4 × 0.88 × 0.65 m | `part` | Caulking gun | Envelope & Finish |
| **Cartridge shelf** | `wall-shelf` | 84 | 1.1 × 0.8 × 0.28 m | `wood` | Caulking gun | Envelope & Finish |
| **Snap line layout table** | `table` | 84 | 1.45 × 0.8 × 0.95 m | `wood` | Chalk line | Envelope & Finish |
| **Chalk line reel stand** | `reel` | 168 | 0.55 × 0.95 × 0.48 m | `metal` | Chalk line | Envelope & Finish |
| **Squaring bench** | `bench` | 84 | 1.45 × 0.88 × 0.8 m | `wood` | Framing square | Envelope & Finish |
| **Square and bevel board** | `wall-peg` | 132 | 1.2 × 0.95 × 0.12 m | `paint` | Framing square | Envelope & Finish |
| **Trimming and planing bench** | `vice-bench` | 144 | 1.45 × 1.2 × 0.75 m | `wood` | Block plane | Envelope & Finish |
| **Shaving hopper** | `hopper` | 108 | 0.9 × 1.0 × 0.6 m | `wood` | Block plane | Envelope & Finish |
| **Bedding and glazing bench** | `bench` | 72 | 1.45 × 0.86 × 0.7 m | `wood` | Putty knife | Envelope & Finish |
| **Putty and pane crates** | `crates` | 84 | 1.1 × 0.8 × 0.55 m | `wood` | Putty knife | Envelope & Finish |
| **Membrane seam table** | `table` | 84 | 1.45 × 0.78 × 1.0 m | `part` | Seam roller | Envelope & Finish |
| **Membrane roll stand** | `spool` | 108 | 1.2 × 1.1 × 0.56 m | `part` | Seam roller | Envelope & Finish |
| **Meter test bench** | `bench` | 72 | 1.45 × 0.88 × 0.7 m | `steel` | Multimeter | Building Systems |
| **Meter and lead cabinet** | `cabinet` | 72 | 0.85 × 1.3 × 0.42 m | `steel` | Multimeter | Building Systems |
| **Termination bench** | `bench` | 84 | 1.45 × 0.9 × 0.65 m | `part` | Wire strippers | Building Systems |
| **Copper offcut bin** | `bin` | 84 | 0.7 × 0.5 × 0.5 m | `metal` | Wire strippers | Building Systems |
| **Fish tape reel stand** | `reel` | 168 | 0.6 × 1.05 × 0.6 m | `metal` | Fish tape | Building Systems |
| **Conduit pull frame** | `cantilever` | 72 | 1.45 × 1.65 × 0.4 m | `metal` | Fish tape | Building Systems |
| **Conduit bending bench** | `vice-bench` | 144 | 1.45 × 1.2 × 0.7 m | `steel` | Conduit bender | Building Systems |
| **Conduit stock rack** | `pipe-rack` | 212 | 1.3 × 1.7 × 0.45 m | `metal` | Conduit bender | Building Systems |
| **Tube cutting bench** | `vice-bench` | 144 | 1.45 × 1.2 × 0.65 m | `steel` | Tubing cutter | Building Systems |
| **Tube offcut hopper** | `hopper` | 108 | 0.85 × 1.0 × 0.55 m | `metal` | Tubing cutter | Building Systems |
| **Pipe vice stand** | `pedestal` | 96 | 0.52 × 1.2 × 0.52 m | `steel` | Pipe wrench | Building Systems |
| **Wrench size rack** | `rack` | 108 | 1.2 × 1.4 × 0.4 m | `metal` | Pipe wrench | Building Systems |
| **Lug crimping bench** | `bench` | 72 | 1.4 × 0.88 × 0.65 m | `part` | Crimping tool | Building Systems |
| **Die and lug drawers** | `drawers` | 132 | 0.85 × 1.0 × 0.48 m | `steel` | Crimping tool | Building Systems |
| **Refrigerant charging rig** | `cantilever` | 72 | 1.2 × 1.6 × 0.45 m | `metal` | Manifold gauge set | Building Systems |
| **Gauge set cabinet** | `cabinet` | 72 | 0.8 × 1.2 × 0.4 m | `steel` | Manifold gauge set | Building Systems |
| **Grade setting table** | `table` | 84 | 1.45 × 0.8 × 0.8 m | `wood` | Torpedo level | Building Systems |
| **Level and plumb shelf** | `wall-shelf` | 72 | 0.9 × 0.65 × 0.24 m | `wood` | Torpedo level | Building Systems |
| **Prove-dead post** | `pedestal` | 96 | 0.36 × 1.22 × 0.36 m | `post` | Non-contact tester | Building Systems |
| **Tester issue board** | `wall-peg` | 132 | 1.0 × 0.85 × 0.12 m | `paint` | Non-contact tester | Building Systems |
| **Service fitting bench** | `vice-bench` | 144 | 1.45 × 1.2 × 0.7 m | `steel` | Tongue-and-groove pliers | Building Systems |
| **Plier wall board** | `wall-peg` | 180 | 1.2 × 0.9 × 0.12 m | `paint` | Tongue-and-groove pliers | Building Systems |
| **Panel build bench** | `bench` | 84 | 1.45 × 0.88 × 0.7 m | `steel` | Nut driver set | Building Systems |
| **Driver and screw drawers** | `drawers` | 132 | 0.9 × 1.05 × 0.45 m | `metal` | Nut driver set | Building Systems |
| **Overhead framing bench** | `vice-bench` | 144 | 1.45 × 1.2 × 0.75 m | `steel` | Lineman pliers | Energy & Utilities |
| **Hand tool board** | `wall-peg` | 180 | 1.2 × 0.95 × 0.12 m | `paint` | Lineman pliers | Energy & Utilities |
| **Live-line stick rack** | `pipe-rack` | 168 | 1.2 × 1.7 × 0.45 m | `wood` | Hot stick | Energy & Utilities |
| **Live-line practice frame** | `cantilever` | 72 | 1.45 × 1.7 × 0.4 m | `wood` | Hot stick | Energy & Utilities |
| **Cable cutting bench** | `vice-bench` | 144 | 1.45 × 1.2 × 0.8 m | `steel` | Cable cutter | Energy & Utilities |
| **Cable offcut bin** | `bin` | 84 | 0.9 × 0.6 × 0.6 m | `metal` | Cable cutter | Energy & Utilities |
| **Load reading bench** | `bench` | 72 | 1.4 × 0.88 × 0.65 m | `part` | Clamp meter | Energy & Utilities |
| **Meter calibration cabinet** | `cabinet` | 72 | 0.85 × 1.3 × 0.42 m | `steel` | Clamp meter | Energy & Utilities |
| **Insulation test rig** | `cantilever` | 72 | 1.3 × 1.6 × 0.45 m | `metal` | Insulation tester | Energy & Utilities |
| **Test set drawers** | `drawers` | 108 | 0.85 × 1.0 × 0.5 m | `steel` | Insulation tester | Energy & Utilities |
| **Leak survey post** | `pedestal` | 96 | 0.36 × 1.25 × 0.36 m | `post` | Gas detector | Energy & Utilities |
| **Detector charge shelf** | `wall-shelf` | 72 | 0.9 × 0.6 × 0.24 m | `metal` | Gas detector | Energy & Utilities |
| **Valve operating stand** | `pedestal` | 96 | 0.48 × 1.15 × 0.48 m | `steel` | Valve key | Energy & Utilities |
| **Valve key cradle** | `wall-cradle` | 60 | 1.3 × 0.36 × 0.22 m | `metal` | Valve key | Energy & Utilities |
| **Trace and mark table** | `table` | 84 | 1.45 × 0.8 × 0.85 m | `wood` | Line locator | Energy & Utilities |
| **Locator set cabinet** | `cabinet` | 72 | 0.8 × 1.25 × 0.42 m | `steel` | Line locator | Energy & Utilities |
| **Terminal torque bench** | `bench` | 72 | 1.3 × 0.88 × 0.6 m | `part` | Torque screwdriver | Energy & Utilities |
| **Bit and driver drawers** | `drawers` | 108 | 0.8 × 0.95 × 0.45 m | `metal` | Torque screwdriver | Energy & Utilities |
| **Splice build bench** | `bench` | 84 | 1.45 × 0.9 × 0.7 m | `steel` | Splice shell set | Energy & Utilities |
| **Splice shell crates** | `crates` | 84 | 1.0 × 0.8 × 0.55 m | `part` | Splice shell set | Energy & Utilities |
| **Long handle tool rack** | `pipe-rack` | 212 | 1.3 × 1.7 × 0.45 m | `wood` | Sharpshooter spade | Energy & Utilities |
| **Backfill sample crates** | `crates` | 84 | 1.1 × 0.75 × 0.55 m | `part` | Sharpshooter spade | Energy & Utilities |
| **Earthing practice frame** | `cantilever` | 72 | 1.4 × 1.65 × 0.4 m | `metal` | Grounding cluster | Energy & Utilities |
| **Earth lead reel** | `reel` | 168 | 0.6 × 1.05 × 0.56 m | `metal` | Grounding cluster | Energy & Utilities |
| **Grade rod rack** | `pipe-rack` | 168 | 1.2 × 1.7 × 0.4 m | `wood` | Grade rod | Earthworks & Plant |
| **Level book table** | `table` | 84 | 1.2 × 0.8 × 0.7 m | `wood` | Grade rod | Earthworks & Plant |
| **Instrument tripod stand** | `tree` | 140 | 0.72 × 1.5 × 0.72 m | `metal` | Rotary laser | Earthworks & Plant |
| **Instrument case cabinet** | `cabinet` | 96 | 0.9 × 1.3 × 0.5 m | `steel` | Rotary laser | Earthworks & Plant |
| **Hand digging tool rack** | `pipe-rack` | 212 | 1.3 × 1.65 × 0.45 m | `wood` | Pick mattock | Earthworks & Plant |
| **Ground condition crates** | `crates` | 84 | 1.1 × 0.8 × 0.55 m | `part` | Pick mattock | Earthworks & Plant |
| **Spoil bin** | `bin` | 84 | 1.0 × 0.7 × 0.65 m | `metal` | Round-point shovel | Earthworks & Plant |
| **Bedding material stack** | `pallet` | 120 | 1.3 × 0.5 × 0.75 m | `wood` | Round-point shovel | Earthworks & Plant |
| **Greasing bench** | `bench` | 84 | 1.45 × 0.88 × 0.7 m | `part` | Grease gun | Earthworks & Plant |
| **Grease and nipple cabinet** | `cabinet` | 84 | 0.85 × 1.25 × 0.45 m | `cone` | Grease gun | Earthworks & Plant |
| **Pry bar cradle** | `wall-cradle` | 60 | 1.4 × 0.38 × 0.22 m | `metal` | Pry bar | Earthworks & Plant |
| **Pipe laying trestle** | `trestle` | 84 | 1.45 × 0.9 × 0.55 m | `wood` | Pry bar | Earthworks & Plant |
| **Compaction plate stand** | `pedestal` | 96 | 0.52 × 1.1 × 0.52 m | `metal` | Hand tamper | Earthworks & Plant |
| **Compaction test crates** | `crates` | 84 | 1.0 × 0.75 × 0.55 m | `part` | Hand tamper | Earthworks & Plant |
| **Line and peg reel** | `reel` | 168 | 0.55 × 0.95 × 0.48 m | `metal` | String line | Earthworks & Plant |
| **Offset peg post** | `pedestal` | 96 | 0.36 × 1.2 × 0.36 m | `post` | String line | Earthworks & Plant |
| **Service marking cart** | `cart` | 188 | 0.9 × 1.0 × 0.55 m | `part` | Marking wand | Earthworks & Plant |
| **Marking paint shelf** | `wall-shelf` | 84 | 1.0 × 0.7 × 0.26 m | `cone` | Marking wand | Earthworks & Plant |
| **Plant fitting bench** | `vice-bench` | 144 | 1.45 × 1.2 × 0.75 m | `steel` | Socket set | Earthworks & Plant |
| **Socket gang box** | `gang-box` | 84 | 1.2 × 0.85 × 0.6 m | `steel` | Socket set | Earthworks & Plant |
| **Pin and bush bench** | `bench` | 84 | 1.45 × 0.9 × 0.7 m | `steel` | Pin punch | Earthworks & Plant |
| **Punch and pin drawers** | `drawers` | 132 | 0.85 × 1.0 × 0.45 m | `metal` | Pin punch | Earthworks & Plant |
| **Tyre inflation stand** | `pedestal` | 96 | 0.44 × 1.15 × 0.44 m | `metal` | Tire pressure gauge | Earthworks & Plant |
| **Pressure chart board** | `wall-board` | 108 | 1.1 × 0.8 × 0.06 m | `paint` | Tire pressure gauge | Earthworks & Plant |
| **Weld dressing bench** | `vice-bench` | 144 | 1.45 × 1.2 × 0.75 m | `steel` | Chipping hammer | Heavy Industry |
| **Slag and scale bin** | `drum` | 84 | 0.56 × 0.7 × 0.56 m | `metal` | Chipping hammer | Heavy Industry |
| **Flange break rig** | `cantilever` | 60 | 1.4 × 1.55 × 0.5 m | `steel` | Flange spreader | Heavy Industry |
| **Gasket and stud crates** | `crates` | 84 | 1.0 × 0.8 × 0.55 m | `part` | Flange spreader | Heavy Industry |
| **Flange alignment table** | `table` | 84 | 1.45 × 0.8 × 0.9 m | `steel` | Flange alignment pins | Heavy Industry |
| **Alignment pin drawers** | `drawers` | 108 | 0.8 × 0.95 × 0.45 m | `steel` | Flange alignment pins | Heavy Industry |
| **Clearance check bench** | `bench` | 72 | 1.3 × 0.88 × 0.65 m | `part` | Feeler gauge | Heavy Industry |
| **Feeler and shim shelf** | `wall-shelf` | 72 | 0.85 × 0.6 × 0.22 m | `metal` | Feeler gauge | Heavy Industry |
| **Metrology bench** | `bench` | 84 | 1.4 × 0.9 × 0.8 m | `steel` | Micrometer | Heavy Industry |
| **Micrometer set cabinet** | `cabinet` | 72 | 0.8 × 1.25 × 0.4 m | `wood` | Micrometer | Heavy Industry |
| **Filing and fitting bench** | `vice-bench` | 144 | 1.45 × 1.2 × 0.7 m | `wood` | File set | Heavy Industry |
| **File and rasp board** | `wall-peg` | 180 | 1.1 × 0.9 × 0.12 m | `paint` | File set | Heavy Industry |
| **Deburring bench** | `bench` | 84 | 1.4 × 0.88 × 0.65 m | `part` | Deburring tool | Heavy Industry |
| **Swarf and burr hopper** | `hopper` | 108 | 0.85 × 1.0 × 0.55 m | `metal` | Deburring tool | Heavy Industry |
| **Shaft runout stand** | `pedestal` | 96 | 0.4 × 1.25 × 0.4 m | `metal` | Dial indicator | Heavy Industry |
| **Indicator and base drawers** | `drawers` | 108 | 0.8 × 0.95 × 0.45 m | `steel` | Dial indicator | Heavy Industry |
| **Bearing press** | `press` | 120 | 1.2 × 1.7 × 0.6 m | `steel` | Bearing puller | Heavy Industry |
| **Puller and leg rack** | `rack` | 96 | 1.1 × 1.35 × 0.45 m | `steel` | Bearing puller | Heavy Industry |
| **Plate marking table** | `table` | 84 | 1.45 × 0.8 × 0.95 m | `steel` | Soapstone holder | Heavy Industry |
| **Soapstone and scribe shelf** | `wall-shelf` | 72 | 0.8 × 0.6 × 0.22 m | `wood` | Soapstone holder | Heavy Industry |
| **Weld profile bench** | `bench` | 72 | 1.3 × 0.88 × 0.7 m | `steel` | Fillet weld gauge | Heavy Industry |
| **Weld sample cabinet** | `cabinet` | 96 | 0.95 × 1.35 × 0.42 m | `wood` | Fillet weld gauge | Heavy Industry |
| **Roller pipe stand** | `pedestal` | 96 | 0.52 × 1.05 × 0.52 m | `metal` | Chain tongs | Heavy Industry |
| **Pipe stock rack** | `pipe-rack` | 212 | 1.4 × 1.7 × 0.5 m | `metal` | Chain tongs | Heavy Industry |
| **Rail fastening bench** | `vice-bench` | 144 | 1.45 × 1.2 × 0.75 m | `steel` | Track wrench | Transport & Mobility |
| **Track wrench cradle** | `wall-cradle` | 60 | 1.4 × 0.38 × 0.22 m | `metal` | Track wrench | Transport & Mobility |
| **Sleeper work trestle** | `trestle` | 84 | 1.45 × 0.8 × 0.6 m | `wood` | Spike puller | Transport & Mobility |
| **Spike and clip bin** | `bin` | 84 | 0.85 × 0.55 × 0.55 m | `metal` | Spike puller | Transport & Mobility |
| **Gauge and cant table** | `table` | 84 | 1.45 × 0.8 × 0.9 m | `steel` | Track gauge | Transport & Mobility |
| **Track gauge cabinet** | `cabinet` | 96 | 0.9 × 1.3 × 0.42 m | `steel` | Track gauge | Transport & Mobility |
| **High torque bench** | `bench` | 84 | 1.45 × 0.9 × 0.75 m | `steel` | Torque multiplier | Transport & Mobility |
| **Multiplier and socket drawers** | `drawers` | 132 | 0.9 × 1.05 × 0.5 m | `steel` | Torque multiplier | Transport & Mobility |
| **Engine test rig** | `cantilever` | 72 | 1.4 × 1.6 × 0.5 m | `metal` | Compression tester | Transport & Mobility |
| **Tester adaptor cabinet** | `cabinet` | 72 | 0.8 × 1.2 × 0.4 m | `steel` | Compression tester | Transport & Mobility |
| **Brake overhaul bench** | `bench` | 84 | 1.45 × 0.9 × 0.75 m | `part` | Brake spring tool | Transport & Mobility |
| **Brake shoe crates** | `crates` | 84 | 1.0 × 0.8 × 0.55 m | `part` | Brake spring tool | Transport & Mobility |
| **Chock stack** | `crates` | 84 | 0.9 × 0.7 × 0.55 m | `wood` | Wheel chock pair | Transport & Mobility |
| **Securing chart board** | `wall-board` | 108 | 1.1 × 0.8 × 0.06 m | `paint` | Wheel chock pair | Transport & Mobility |
| **Signal circuit frame** | `cantilever` | 72 | 1.4 × 1.65 × 0.4 m | `metal` | Signal test set | Transport & Mobility |
| **Relay test bench** | `bench` | 72 | 1.45 × 0.88 × 0.7 m | `steel` | Signal test set | Transport & Mobility |
| **Alignment bar cradle** | `cradle` | 72 | 1.45 × 0.8 × 0.45 m | `steel` | Alignment bar | Transport & Mobility |
| **Coupling alignment table** | `table` | 84 | 1.45 × 0.8 × 0.85 m | `steel` | Alignment bar | Transport & Mobility |
| **Wheel service bench** | `bench` | 84 | 1.45 × 0.9 × 0.75 m | `steel` | Impact gun | Transport & Mobility |
| **Air hose reel** | `wall-reel` | 144 | 0.42 × 0.6 × 0.54 m | `metal` | Impact gun | Transport & Mobility |
| **Creeper and light rack** | `rack` | 96 | 1.2 × 1.3 × 0.5 m | `metal` | Inspection lamp | Transport & Mobility |
| **Under-vehicle cart** | `cart` | 188 | 0.95 × 0.95 × 0.55 m | `part` | Inspection lamp | Transport & Mobility |
| **Height stick rack** | `pipe-rack` | 168 | 1.2 × 1.7 × 0.4 m | `wood` | Height stick | Transport & Mobility |
| **Contact wire height post** | `pedestal` | 96 | 0.36 × 1.3 × 0.36 m | `post` | Height stick | Transport & Mobility |
| **Prism pole rack** | `pipe-rack` | 168 | 1.1 × 1.7 × 0.4 m | `metal` | Prism pole | Survey, Safety & Environment |
| **Backsight target post** | `pedestal` | 96 | 0.36 × 1.3 × 0.36 m | `post` | Prism pole | Survey, Safety & Environment |
| **Booking and reduction table** | `table` | 84 | 1.4 × 0.8 × 0.8 m | `wood` | Auto level | Survey, Safety & Environment |
| **Level instrument cabinet** | `cabinet` | 96 | 0.9 × 1.3 × 0.5 m | `steel` | Auto level | Survey, Safety & Environment |
| **Tripod stand** | `tree` | 140 | 0.72 × 1.45 × 0.72 m | `wood` | Field tripod | Survey, Safety & Environment |
| **Tripod and staff rack** | `rack` | 96 | 1.2 × 1.45 × 0.45 m | `wood` | Field tripod | Survey, Safety & Environment |
| **Bump test bench** | `bench` | 72 | 1.3 × 0.88 × 0.65 m | `part` | Four-gas monitor | Survey, Safety & Environment |
| **Entry equipment crates** | `crates` | 84 | 1.0 × 0.8 × 0.55 m | `part` | Four-gas monitor | Survey, Safety & Environment |
| **Air sampling bench** | `bench` | 84 | 1.4 × 0.88 × 0.7 m | `part` | Air sampling pump | Survey, Safety & Environment |
| **Sample media cabinet** | `cabinet` | 96 | 0.85 × 1.3 × 0.4 m | `cone` | Air sampling pump | Survey, Safety & Environment |
| **Decontamination tank** | `tank` | 140 | 0.68 × 1.0 × 0.68 m | `part` | Decon sprayer | Survey, Safety & Environment |
| **Decon solution shelf** | `wall-shelf` | 84 | 1.0 × 0.7 × 0.26 m | `cone` | Decon sprayer | Survey, Safety & Environment |
| **Filtered vacuum stand** | `pedestal` | 96 | 0.52 × 1.2 × 0.52 m | `metal` | HEPA vacuum | Survey, Safety & Environment |
| **Filter stock crates** | `crates` | 84 | 0.95 × 0.75 × 0.5 m | `part` | HEPA vacuum | Survey, Safety & Environment |
| **Air flow survey post** | `pedestal` | 96 | 0.36 × 1.28 × 0.36 m | `metal` | Anemometer | Survey, Safety & Environment |
| **Flow instrument shelf** | `wall-shelf` | 72 | 0.9 × 0.65 × 0.24 m | `metal` | Anemometer | Survey, Safety & Environment |
| **Noise survey bench** | `bench` | 72 | 1.3 × 0.88 × 0.65 m | `part` | Sound level meter | Survey, Safety & Environment |
| **Acoustic calibrator cabinet** | `cabinet` | 72 | 0.75 × 1.2 × 0.4 m | `steel` | Sound level meter | Survey, Safety & Environment |
| **Illuminance survey table** | `table` | 84 | 1.2 × 0.8 × 0.7 m | `wood` | Light meter | Survey, Safety & Environment |
| **Photometry shelf** | `wall-shelf` | 72 | 0.85 × 0.6 × 0.22 m | `metal` | Light meter | Survey, Safety & Environment |
| **Moisture survey bench** | `bench` | 84 | 1.3 × 0.88 × 0.7 m | `wood` | Moisture meter | Survey, Safety & Environment |
| **Reference sample crates** | `crates` | 84 | 1.0 × 0.75 × 0.5 m | `wood` | Moisture meter | Survey, Safety & Environment |
| **Fall arrest practice frame** | `cantilever` | 72 | 1.4 × 1.7 × 0.4 m | `metal` | Rope grab | Survey, Safety & Environment |
| **Rope and grab rack** | `rack` | 96 | 1.1 × 1.45 × 0.45 m | `metal` | Rope grab | Survey, Safety & Environment |

## What this is not

- **Not a specification.** These are shapes in a training environment. The eyewash stand is a cylinder and a bowl standing where a room record says corrosives are handled; the extinguisher is a cylinder on a plate; the press is a bed, a ram and a box with a dial on it. They are not fixture specifications, not rated appliances, not machine specifications, not compliance artefacts, and not evidence that any equipment has been provided anywhere. Nothing in this pack should be read as a safety-equipment specification, and a learner who has walked past one has not been trained on it.
- **Not reviewed.** The vocabulary is AUTHORED — a judgement about what a trade-training room contains — and no journey-level practitioner has reviewed it. The sentence each district piece gives for itself is DERIVED from the crib's own use line for the tool it names, which makes it accurate about the tool and no more authoritative about the furniture.
- **Not standing.** The 192 district pieces are NOT standing in any hall. placeRoomProps() chooses a room's furniture from D.props.by_strand[r.strand] and from that room's own PPE list, and neither of those has a hall in it — the eleven rooms are the same eleven rooms in all 111 halls. Putting a glazier's suction-cup rack in the strand table would stand it in every ironworkers' hall too, so it is not there. What is published instead is the fit-out computed per district and per room, its geometry, and its cost priced against the same ceiling as the drawn set. It waits on one change this pack does not own: a hall dimension on the furniture lookup in web/build_3d.py.
- **Not a second copy.** No room label, purpose, footprint, illuminance figure, hazard, PPE item, tool name or tool use sentence is typed in this pack. The room table is imported from web/interiors.py, the conditions are read from surfaces/registry/finishes.json, the tools are read from tools/registry/toolcribs.json and the district of a hall from unions/registry/unions.json. The page's body radius, eye height, grid unit, floor height, partition height, room-label height and bench setback are parsed out of web/build_3d.py, so a piece cannot be sized against a constant the page does not use.

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
