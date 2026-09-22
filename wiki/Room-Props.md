# The room props

29 props in 7 families that stand inside a hall room,
from the bench a trade is learned at to the safety fixtures a room's own record
asks for. Placed by rule across 111 halls and 1,221 rooms,
that is 5,082 instances.

**Not one of them is standing anywhere yet.** This registry is a declaration. web/build_3d.py does not read it yet: no prop declared here is standing in any room in the shipped page. The page_contract block states exactly what wiring is outstanding.

## What a prop is

SCHEMATIC: every prop in this pack is a handful of boxes and cylinders built in the browser from the recipe printed here. No mesh is loaded, no model is vendored, no texture is fetched, and nothing is generated at view time.

| Family | What it is |
|---|---|
| **bench** | a horizontal surface work happens on top of |
| **storage** | something that holds what a room keeps between sessions |
| **board** | a vertical surface a room reads from |
| **seat** | something a person is off their feet on |
| **vessel** | an open container things go into and come out of |
| **stand** | a freestanding upright a piece of apparatus lives on |
| **safety-fixture** | a schematic shape standing where a room record asks for protective equipment — not a specification |

## Placement is derived, never placed by hand

No prop is placed by hand. A prop stands in a strand because a word it declares appears in that strand's own purpose line in web/interiors.py, and a hazard prop stands in a room because that room's own conditions record in surfaces/registry/finishes.json asks for the protective equipment it holds. The build fails if a room requiring PPE gets no PPE prop.

The registry records the word that matched, so the derivation can be read back:
25 placements over all 11 of the
11 strands.

| Strand | Room | Props, and the word that admitted each |
|---|---|---|
| **safety** | Induction & PPE | Gowning bench (`gowning`), Permit board (`permit`), Atmospheric check post (`atmospheric`) |
| **procedure** | Practice Bays | Work trestle (`floor`), Learner stool (`learned`) |
| **machines** | Equipment Bay | Plant checkout board (`checked out`), Bay guard rail (`training area`) |
| **tools** | Tool Crib | Issue counter (`issue`), Calibration cabinet (`calibration`), Return bin (`return`) |
| **materials** | Materials Store | Stock rack (`stock`), Offcut bin (`offcuts`), Consumables shelf (`consumables`) |
| **layout** | Layout Floor | Layout table (`setting`), Control point pillar (`control point`) |
| **inspection** | Inspection Bench | Acceptance gauge stand (`acceptance`), Sign-off desk (`sign-off`) |
| **troubleshooting** | Diagnostic Bench | Live rig frame (`rigs`), Fault-finding bench (`fault-finding`) |
| **coordination** | Briefing Room | Shift board (`shift`), Hand-off table (`hand-offs`) |
| **documentation** | Records | Permit board (`permit`), Records cabinet (`certificates`) |
| **leadership** | Classroom | Exam desk (`tests`), Instructor lectern (`instructor`) |

A prop is anchored against the room rectangle the page already computes, never
against a coordinate typed here:

| Anchor | Where it stands |
|---|---|
| `side-wall` | stands on the floor along a left or right partition |
| `back-corner` | stands on the floor in one back corner, clear of the fixture bench band |
| `wall-mounted` | hangs on a left or right partition, its top no higher than the partition itself |

## The hazard props

A hazard prop stands in a room when THAT ROOM'S own conditions record names protective equipment the prop holds. No hazard prop is placed by hand anywhere.

The trigger is the room's own conditions record — the same record the door
placard is drawn from — read against a PPE vocabulary of 26
items and a hazard vocabulary of 18.
888 of the 1,221 rooms require protective
equipment, and the build fails if one of them gets no PPE prop.

| Prop | Stands in a room when | Rooms |
|---|---|---|
| **PPE station** | a room gets this when its own conditions.ppe is non-empty | 888 |
| **Eyewash stand** | a room gets this when its own conditions.ppe names any of apron, chemical gloves, face shield | 32 |
| **Extinguisher bracket** | a room gets this when its own conditions.ppe names any of anti-static clothing, flame-resistant clothing, welding hood | 24 |
| **Spill kit cabinet** | a room gets this when its own conditions.ppe names any of chemical gloves, coveralls, waterproof boots | 25 |
| **Gas monitor dock** | a room gets this when its own conditions.ppe names any of gas monitor | 6 |

None of these is evidence that any equipment has been provided anywhere, and a
learner who has walked past one has not been trained on it.

## The measured band

The triangle band is taken from a measurement of six reference models made before anything here was drawn: the blocks that read as real places have a median mesh of 46 and 104 triangles. Nothing from those files is vendored, copied or named — what was taken is the finding that a place is made of many small distinct pieces rather than of dense ones.

The measurement is recorded in
[`assets/REFERENCE.md`](../assets/REFERENCE.md). What was not taken:
no geometry, no texture, no material, no name and no shape; two of the reference files are somebody else's copyrighted assets and nothing from any of them is vendored here.

Props run 48 to 132 triangles, median
96, 2,684 for the whole vocabulary, out of
173 box parts and 17 cylinder parts. Every
dimension they are set against is parsed out of the page rather than typed
here — body radius 0.45 m, eye height
1.7 m, grid unit 3.0 m, floor top
0.41 m, partition top 1.45 m, bench
setback 0.8 m, all from `web/build_3d.py`.

| Prop | Family | Triangles | Size | Material | Merge | Anchor | Why it is in the room |
|---|---|---|---|---|---|---|---|
| **Gowning bench** | seat | 84 | 1.6 × 0.95 × 0.55 m | `wood` | pooled | side-wall | you change at it before you cross the stripe the page already paints across a safety room doorway |
| **Permit board** | board | 96 | 1.14 × 0.8 × 0.06 m | `paint` | pooled | wall-mounted | the board the safety room is named after, and the one the records room files afterwards |
| **Atmospheric check post** | stand | 96 | 0.32 × 1.36 × 0.32 m | `metal` | pooled | side-wall | the room says atmospheric checks happen here, so the thing they are made on stands in it |
| **Work trestle** | stand | 84 | 1.8 × 0.9 × 0.5 m | `wood` | pooled | side-wall | the bay is the floor a trade is learned on, and a trestle is what the work is held at height on while it is |
| **Learner stool** | seat | 96 | 0.44 × 0.62 × 0.44 m | `metal` | pooled | side-wall | nobody stands for six hours; a bay with no seat in it is a rendering of a bay |
| **Plant checkout board** | board | 108 | 1.34 × 0.9 × 0.06 m | `paint` | pooled | wall-mounted | plant is CHECKED OUT to this room, and a checkout that is not written down anywhere did not happen |
| **Bay guard rail** | stand | 112 | 2.0 × 1.06 × 0.2 m | `post` | pooled | side-wall | a training AREA is an area because something marks where it stops |
| **Issue counter** | bench | 72 | 1.8 × 0.86 × 0.6 m | `wood` | pooled | side-wall | the crib the page already builds hands tools ACROSS something, and until now it handed them across nothing |
| **Calibration cabinet** | storage | 84 | 0.94 × 1.36 × 0.54 m | `steel` | pooled | side-wall | calibration is the middle word of this room's purpose and it is the one that needs a locked box |
| **Return bin** | vessel | 84 | 0.6 × 0.78 × 0.6 m | `part` | pooled | back-corner | things come BACK to a crib, and a crib with nowhere to put them back is a counter with a queue |
| **Stock rack** | storage | 96 | 1.8 × 1.7 × 0.7 m | `metal` | pooled | side-wall | STOCK is the first word of this room's purpose and stock is kept on something |
| **Offcut bin** | vessel | 84 | 0.9 × 0.66 × 0.6 m | `wood` | pooled | back-corner | OFFCUTS is the second word, and the difference between a trade shop and a warehouse is that the offcuts are kept |
| **Consumables shelf** | storage | 72 | 1.2 × 0.9 × 0.3 m | `wood` | pooled | wall-mounted | CONSUMABLES is the third word; they are small, they go at hand height, and they do not belong on the stock rack |
| **Layout table** | bench | 96 | 2.0 × 0.8 × 0.9 m | `steel` | pooled | side-wall | setting out and marking are done flat, at waist height, on something that does not move |
| **Control point pillar** | stand | 104 | 0.4 × 1.28 × 0.4 m | `metal` | pooled | back-corner | a CONTROL POINT is a thing you can put an instrument over twice and get the same answer; a painted cross is not one |
| **Acceptance gauge stand** | stand | 108 | 0.4 × 1.28 × 0.4 m | `metal` | pooled | side-wall | ACCEPTANCE CRITERIA is a number somebody reads off something |
| **Sign-off desk** | bench | 96 | 1.4 × 0.8 × 0.7 m | `wood` | pooled | side-wall | SIGN-OFF is a person writing on paper at a desk, and the second half of what this room is for |
| **Live rig frame** | stand | 108 | 1.5 × 1.66 × 0.25 m | `metal` | pooled | side-wall | a LIVE RIG is a frame with something wired to it that can be made to fail on purpose |
| **Fault-finding bench** | bench | 108 | 1.5 × 1.1 × 0.7 m | `steel` | pooled | side-wall | FAULT-FINDING happens with instruments on a surface, facing the rig |
| **Shift board** | board | 96 | 1.64 × 0.95 × 0.08 m | `paint` | pooled | wall-mounted | a SHIFT START is people standing in front of a board that says who is doing what |
| **Hand-off table** | bench | 72 | 1.6 × 0.78 × 0.8 m | `wood` | pooled | side-wall | a HAND-OFF is two crews around one table with the drawing on it |
| **Records cabinet** | storage | 132 | 1.0 × 1.39 × 0.57 m | `steel` | pooled | side-wall | CERTIFICATES and AS-BUILTS are paper, and paper that matters lives in a drawer somebody can find |
| **Exam desk** | bench | 72 | 1.2 × 0.76 × 0.6 m | `wood` | pooled | side-wall | LEVEL TESTS are sat at a desk, and a classroom with no desks is a corridor |
| **Instructor lectern** | stand | 48 | 0.7 × 1.16 × 0.5 m | `wood` | pooled | back-corner | the INSTRUCTOR TRACK has an instructor in it and the instructor stands somewhere |
| **PPE station** | safety-fixture | 108 | 1.0 × 1.0 × 0.24 m | `paint` | instanced | wall-mounted | the room record already says what this room requires of you, and the page already hangs that list on the door as a placard; this is a schematic rack standing where the placard points — it issues nothing and holds nothing |
| **Eyewash stand** | safety-fixture | 128 | 0.4 × 1.24 × 0.4 m | `post` | instanced | back-corner | a shape standing where a room record says something can get in your eyes — NOT a fixture specification and not evidence that anything has been installed |
| **Extinguisher bracket** | safety-fixture | 108 | 0.22 × 0.7 × 0.2 m | `cone` | instanced | wall-mounted | a shape standing where a room record asks for flame-resistant or anti-static clothing — schematic, not a rated appliance |
| **Spill kit cabinet** | safety-fixture | 60 | 0.6 × 0.88 × 0.37 m | `cone` | instanced | back-corner | a shape standing where a room record says something can be spilled — schematic, and it contains nothing |
| **Gas monitor dock** | safety-fixture | 72 | 0.35 × 0.45 × 0.12 m | `metal` | instanced | wall-mounted | a shape standing where a room record asks the person to carry a gas monitor — it docks nothing and measures nothing |

## What it would cost

A hall interior is draw-call bound, not triangle bound. Every prop here pools or instances; none takes a mesh of its own, and the budget block refuses a design that would.

The ceiling comes from `web/eval_scene.mjs`: it is the only file in this repo that states what a rendered hall costs and what it may cost, and it states both with a reason; the multipliers are read from it too, so its policy moving moves this ceiling with it.

The measured baseline is quoted here for one reason:
it says which currency is scarce. A hall spends 157 of 196 permitted draw calls and 3,806 of 15,224 permitted triangles, so the draw call is the expensive one and the triangle is not. That measurement is
MEASURED-ELSEWHERE: measured 2026-09-22 in Chromium/SwiftShader at 1280x800 on quality rung high, by the eval this builder reads but does not run — verify_all.sh opens no browser and neither does this file. It leaves
39 draw calls and 11,418 triangles
unspent.

This pack takes half of that headroom and leaves half:
19 draw calls and
5,709 triangles a hall.
The worst hall stands 52 props in eleven rooms and pays 10 draw calls for all of them — 6% on top of what the hall already draws, for 132% more triangles.

| | Min | Median | Max |
|---|---|---|---|
| Props in a hall | 45 | 45 | 52 |
| Triangles | 4,264 | 4,264 | 5,032 |
| Draw calls | 7 | — | 10 |

One per pooled material for the whole hall plus one per instanced prop type; never one per prop. Across the bundle that is
5,082 props in 1,221 rooms
for 481,924 triangles — a prediction of what the rules
would place, not a measurement of anything drawn.

## What a prop is not

- **Not a specification.** These are shapes in a training environment. The eyewash stand is a cylinder and a bowl standing where a room record says corrosives are handled; the extinguisher is a cylinder on a plate. They are not fixture specifications, not rated appliances, not compliance artefacts, and not evidence that any equipment has been provided anywhere. Nothing in this pack should be read as a safety-equipment specification, and a learner who has walked past one has not been trained on it.
- **Not reviewed.** The vocabulary is AUTHORED — a judgement about what a trade-training room contains — and no journey-level practitioner has reviewed it.
- **Not wired.** This registry is a declaration. web/build_3d.py does not read it yet: no prop declared here is standing in any room in the shipped page. The page_contract block states exactly what wiring is outstanding.
- **Not a second copy.** No room label, purpose, footprint, illuminance figure, hazard or PPE item is typed in this pack. The room table is imported from web/interiors.py and the conditions are read from surfaces/registry/finishes.json. The page's body radius, eye height, grid unit, floor height, partition height, room-label height and bench setback are parsed out of web/build_3d.py, so a prop cannot be sized against a constant the page does not use.

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
