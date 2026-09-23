# The room props

108 props in 12 families that stand inside a hall room,
from the bench a trade is learned at to the safety fixtures a room's own record
asks for. Placed by rule across 111 halls and 1,221 rooms,
that is 8,448 instances.

**They are standing now.** BUILT. web/build_3d.py reads this registry and stands its props: placeRoomProps() lays them against the partitions buildHall() has just cut, pooled into one mesh per material for the whole hall and one InstancedMesh per safety fixture, and window.__tc3dProps() reports what was drawn beside what the count rule here wanted. The count rule knows nothing of doorways or of the tool crib, so a room stands fewer than it predicts; the probe names each prop that found no wall and why.

## What a prop is

SCHEMATIC: every piece in this pack is a handful of boxes and cylinders built in the browser from the recipe printed here. No mesh is loaded, no model is vendored, no texture is fetched, and nothing is generated at view time.

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

## Placement is derived, never placed by hand

No piece is placed by hand. A shop piece stands in a strand because a word it declares appears in that strand's own purpose line in web/interiors.py; a conditions piece stands in a room because that room's own record in surfaces/registry/finishes.json asks for the protective equipment it is keyed to, and the same registry's hazard table says which kind of work adds that equipment; a district piece belongs to the district whose crib carries the tool it names, read from tools/registry/toolcribs.json. The build fails if a room requiring PPE gets no PPE prop.

The registry records the word that matched, so the derivation can be read back:
60 placements over all 11 of the
11 strands.

| Strand | Room | Props, and the word that admitted each |
|---|---|---|
| **safety** | Induction & PPE | Gowning bench (`gowning`), Permit board (`permit`), Boot change step (`gowning`), Atmospheric check post (`atmospheric`), Induction lectern (`checks`) |
| **procedure** | Practice Bays | Work trestle (`floor`), Learner stool (`learned`), Practice bench (`floor`), Task board (`learned`), Bay tool tree (`floor`), Demonstration table (`learned`), Bar stock cradle (`floor`) |
| **machines** | Equipment Bay | Plant checkout board (`checked out`), Bay guard rail (`training area`), Plant service bench (`plant`), Lubricant store (`plant`), Chock and block bin (`plant`), Machine log desk (`checked out`), Sheet stock rack (`plant`) |
| **tools** | Tool Crib | Issue counter (`issue`), Calibration cabinet (`calibration`), Return bin (`return`), Tool pegboard (`issue`), Battery charge shelf (`issue`), Gauge drawers (`calibration`) |
| **materials** | Materials Store | Stock rack (`stock`), Sheet stock rack (`stock`), Bar stock cradle (`stock`), Offcut bin (`offcuts`), Consumables shelf (`consumables`), Consumable drum stand (`consumables`) |
| **layout** | Layout Floor | Layout table (`setting`), Control point pillar (`control point`), Marking media shelf (`marking`), Template rack (`marking`), Setting-out line reel (`setting`) |
| **inspection** | Inspection Bench | Gauge drawers (`acceptance`), Acceptance gauge stand (`acceptance`), Sign-off desk (`sign-off`), Sample cabinet (`acceptance`), Surface plate table (`acceptance`) |
| **troubleshooting** | Diagnostic Bench | Live rig frame (`rigs`), Fault-finding bench (`fault-finding`), Instrument cabinet (`fault-finding`), Fault log board (`rigs`), Isolation post (`live`) |
| **coordination** | Briefing Room | Shift board (`shift`), Hand-off table (`hand-offs`), Crew bench (`shift`), Drawing easel (`cross-trade`), Plan rack (`hand-offs`) |
| **documentation** | Records | Permit board (`permit`), Records cabinet (`certificates`), As-built drawing chest (`as-builts`), Permit file rack (`permits`) |
| **leadership** | Classroom | Exam desk (`tests`), Instructor lectern (`instructor`), Classroom stool (`tests`), Progress board (`track`), Reference shelf (`level`) |

A prop is anchored against the room rectangle the page already computes, never
against a coordinate typed here:

| Anchor | Where it stands |
|---|---|
| `side-wall` | stands on the floor along a left or right partition |
| `back-corner` | stands on the floor in one back corner, clear of the fixture bench band |
| `wall-mounted` | hangs on a left or right partition, its top no higher than the partition itself |

## The hazard props

A hazard prop stands in a room when THAT ROOM'S own conditions record names protective equipment the prop is keyed to, and the same registry's hazard table says which kind of work adds that equipment. No hazard prop is placed by hand anywhere.

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
| **Electrode rod oven** | a room gets this when its own conditions.ppe names any of welding hood | 8 |
| **Welding screen** | a room gets this when its own conditions.ppe names any of welding hood | 8 |
| **Electrode stub bin** | a room gets this when its own conditions.ppe names any of welding hood | 8 |
| **Fire blanket cabinet** | a room gets this when its own conditions.ppe names any of flame-resistant clothing | 20 |
| **Quench tank** | a room gets this when its own conditions.ppe names any of flame-resistant clothing | 20 |
| **Fire watch post** | a room gets this when its own conditions.ppe names any of flame-resistant clothing | 20 |
| **Splash screen** | a room gets this when its own conditions.ppe names any of face shield | 32 |
| **Face shield shelf** | a room gets this when its own conditions.ppe names any of face shield | 32 |
| **Rubber goods rack** | a room gets this when its own conditions.ppe names any of dielectric gloves | 12 |
| **Insulating mat roll stand** | a room gets this when its own conditions.ppe names any of dielectric gloves | 12 |
| **Hot stick cradle** | a room gets this when its own conditions.ppe names any of dielectric gloves | 12 |
| **Lockout station** | a room gets this when its own conditions.ppe names any of arc-flash face shield | 12 |
| **Arc-rated garment locker** | a room gets this when its own conditions.ppe names any of arc-flash face shield | 12 |
| **Decant stand** | a room gets this when its own conditions.ppe names any of chemical gloves | 7 |
| **Drip tray stand** | a room gets this when its own conditions.ppe names any of chemical gloves | 7 |
| **Apron rail** | a room gets this when its own conditions.ppe names any of apron | 7 |
| **Wash trough** | a room gets this when its own conditions.ppe names any of apron | 7 |
| **Boot wash trough** | a room gets this when its own conditions.ppe names any of waterproof boots | 12 |
| **Duckboard stack** | a room gets this when its own conditions.ppe names any of waterproof boots | 12 |
| **Immersion suit rack** | a room gets this when its own conditions.ppe names any of immersion suit | 4 |
| **Tender line post** | a room gets this when its own conditions.ppe names any of immersion suit | 4 |
| **Coverall hamper** | a room gets this when its own conditions.ppe names any of coveralls | 11 |
| **Dirty side bench** | a room gets this when its own conditions.ppe names any of coveralls | 11 |
| **Filter cabinet** | a room gets this when its own conditions.ppe names any of respirator | 9 |
| **Fit test bench** | a room gets this when its own conditions.ppe names any of respirator | 9 |
| **Spent cartridge bin** | a room gets this when its own conditions.ppe names any of respirator | 9 |
| **Survey meter bench** | a room gets this when its own conditions.ppe names any of dosimeter | 2 |
| **Glove and mask dispenser** | a room gets this when its own conditions.ppe names any of gowning | 2 |
| **Dosimeter rack** | a room gets this when its own conditions.ppe names any of dosimeter | 2 |
| **Gowning locker** | a room gets this when its own conditions.ppe names any of gowning | 2 |
| **Tack mat stand** | a room gets this when its own conditions.ppe names any of gowning | 2 |
| **Extraction trunk stand** | a room gets this when its own conditions.ppe names any of dust mask | 3 |
| **Sweep-up cart** | a room gets this when its own conditions.ppe names any of dust mask | 3 |
| **Ear plug dispenser** | a room gets this when its own conditions.ppe names any of hearing protection | 135 |
| **Acoustic screen** | a room gets this when its own conditions.ppe names any of hearing protection | 135 |
| **Bonding lead reel** | a room gets this when its own conditions.ppe names any of anti-static clothing | 4 |
| **Earth point post** | a room gets this when its own conditions.ppe names any of anti-static clothing | 4 |
| **Calibration gas rack** | a room gets this when its own conditions.ppe names any of gas monitor | 6 |
| **Purge fan stand** | a room gets this when its own conditions.ppe names any of gas monitor | 6 |
| **Entry tripod** | a room gets this when its own conditions.ppe names any of rescue harness | 4 |
| **Retrieval winch post** | a room gets this when its own conditions.ppe names any of rescue harness | 4 |
| **Harness inspection rail** | a room gets this when its own conditions.ppe names any of full-body harness | 8 |
| **Lanyard locker** | a room gets this when its own conditions.ppe names any of full-body harness | 8 |
| **Helmet shelf** | a room gets this when its own conditions.ppe names any of chinstrap helmet | 8 |
| **Edge protection stack** | a room gets this when its own conditions.ppe names any of chinstrap helmet | 8 |
| **Machine guard store** | a room gets this when its own conditions.ppe names any of close-fitting clothing | 10 |
| **Swarf bin** | a room gets this when its own conditions.ppe names any of close-fitting clothing | 10 |

None of these is evidence that any equipment has been provided anywhere, and a
learner who has walked past one has not been trained on it.

## The measured band

The triangle band is taken from a measurement of six reference models made before anything here was drawn: the blocks that read as real places have a median mesh of 46 and 104 triangles. Nothing from those files is vendored, copied or named — what was taken is the finding that a place is made of many small distinct pieces rather than of dense ones.

The measurement is recorded in
[`assets/REFERENCE.md`](../assets/REFERENCE.md). What was not taken:
no geometry, no texture, no material, no name and no shape; two of the reference files are somebody else's copyrighted assets and nothing from any of them is vendored here.

Props run 60 to 188 triangles, median
96, 10,600 for the whole vocabulary, out of
673 box parts and 75 cylinder parts. Every
dimension they are set against is parsed out of the page rather than typed
here — body radius 0.45 m, eye height
1.7 m, grid unit 3.0 m, floor top
0.41 m, partition top 1.45 m, bench
setback 0.8 m, all from `web/build_3d.py`.

| Prop | Family | Triangles | Size | Material | Merge | Anchor | Why it is in the room |
|---|---|---|---|---|---|---|---|
| **PPE station** | safety-fixture | 132 | 1.0 × 1.0 × 0.12 m | `paint` | instanced | wall-mounted | the room record already says what this room requires of you and the page already hangs that list on the door; this is a schematic — a shape standing where a room record asks for it, not a fixture specification and not evidence that anything has been provided. It issues nothing and holds nothing |
| **Eyewash stand** | safety-fixture | 96 | 0.32 × 1.22 × 0.32 m | `post` | instanced | back-corner | a shape standing where a room record says something can get in your eyes: schematic — a shape standing where a room record asks for it, not a fixture specification and not evidence that anything has been provided |
| **Extinguisher bracket** | safety-fixture | 60 | 0.24 × 0.62 × 0.22 m | `cone` | instanced | wall-mounted | a shape standing where a room record asks for flame-resistant or anti-static clothing: schematic — a shape standing where a room record asks for it, not a fixture specification and not evidence that anything has been provided, and not a rated appliance |
| **Spill kit cabinet** | safety-fixture | 72 | 0.62 × 0.88 × 0.38 m | `cone` | instanced | back-corner | a shape standing where a room record says something can be spilled: schematic — a shape standing where a room record asks for it, not a fixture specification and not evidence that anything has been provided. It contains nothing |
| **Gas monitor dock** | safety-fixture | 72 | 0.42 × 0.46 × 0.14 m | `metal` | instanced | wall-mounted | a shape standing where a room record asks the person to carry a gas monitor: schematic — a shape standing where a room record asks for it, not a fixture specification and not evidence that anything has been provided. It docks nothing and measures nothing |
| **Electrode rod oven** | machine | 144 | 0.52 × 1.1 × 0.46 m | `steel` | pooled | side-wall | electrodes that have drunk the air do not run, so a room where arcs are struck keeps them warm and dry in a cabinet by the bay |
| **Welding screen** | screen | 124 | 1.5 × 1.75 × 0.22 m | `part` | pooled | side-wall | the flash off an arc burns the eyes of somebody who never looked at it, so the bay is screened from the rest of the room |
| **Electrode stub bin** | waste | 84 | 0.48 × 0.7 × 0.48 m | `metal` | pooled | back-corner | a welder drops a stub every ninety seconds and they land hot; the bin for them is metal and it stands at the bay, not by the door |
| **Fire blanket cabinet** | safety-fixture | 72 | 0.42 × 0.48 × 0.18 m | `cone` | pooled | wall-mounted | a shape hanging where a room record asks for flame-resistant clothing: schematic — a shape standing where a room record asks for it, not a fixture specification and not evidence that anything has been provided |
| **Quench tank** | vessel | 140 | 0.68 × 0.95 × 0.68 m | `steel` | pooled | back-corner | hot metal has to go somewhere between the torch and the hand, and in a shop that somewhere is a tank of water on legs |
| **Fire watch post** | stand | 96 | 0.36 × 1.3 × 0.36 m | `post` | pooled | side-wall | hot work is watched while it is done and for a while after it stops, and the watch stands at a post with the clock on it |
| **Splash screen** | screen | 112 | 1.2 × 1.6 × 0.22 m | `part` | pooled | side-wall | what comes off the work at face height comes off it sideways too, and the person at the next bench did not put a shield on |
| **Face shield shelf** | storage | 72 | 0.9 × 0.55 × 0.26 m | `wood` | pooled | wall-mounted | a shield kept in a locker is a shield nobody fetches; it lives on an open shelf at the door of the room that calls for it |
| **Rubber goods rack** | storage | 108 | 1.0 × 1.55 × 0.45 m | `metal` | pooled | side-wall | insulating gloves and sleeves are stored flat, unfolded and out of the light, and they are re-tested on a date somebody can read |
| **Insulating mat roll stand** | stock | 108 | 1.1 × 1.05 × 0.52 m | `part` | pooled | side-wall | the mat that goes down in front of a live panel is kept rolled on a stand, because a folded one keeps the fold |
| **Hot stick cradle** | storage | 60 | 1.3 × 0.4 × 0.22 m | `wood` | pooled | wall-mounted | a live-line stick is only as good as its surface, so it hangs straight on brackets and never leans in a corner |
| **Lockout station** | safety-fixture | 108 | 1.0 × 0.8 × 0.06 m | `paint` | pooled | wall-mounted | a shape hanging where a room record asks for arc-rated protection: schematic — a shape standing where a room record asks for it, not a fixture specification and not evidence that anything has been provided. It locks nothing out |
| **Arc-rated garment locker** | storage | 96 | 1.05 × 1.7 × 0.5 m | `steel` | pooled | side-wall | arc-rated clothing is issued by size and returned to the same hook, and a heap on a bench is nobody's size |
| **Decant stand** | bench | 84 | 1.1 × 0.8 × 0.6 m | `part` | pooled | side-wall | pouring from a drum into a jug is done on a low bench with a lip, over a tray, at a height where the pour can be watched |
| **Drip tray stand** | vessel | 84 | 1.0 × 0.32 × 0.7 m | `part` | pooled | side-wall | a container that has been decanted from drips for an hour afterwards, and the floor is not where that is caught |
| **Apron rail** | storage | 96 | 1.0 × 1.6 × 0.4 m | `metal` | pooled | side-wall | an apron worn against a splash is hung wet, outside the locker, where the next person can see whether it is dry |
| **Wash trough** | vessel | 128 | 1.2 × 1.29 × 0.55 m | `part` | pooled | side-wall | the first thing done after chemical work is done at a trough, and a trough is a basin on legs with a tap over it |
| **Boot wash trough** | vessel | 128 | 0.95 × 0.94 × 0.6 m | `part` | pooled | side-wall | wet-process work walks out of the room on the boots unless there is somewhere low to wash them at the threshold |
| **Duckboard stack** | stock | 120 | 1.2 × 0.42 × 0.7 m | `wood` | pooled | side-wall | standing all day on a wet floor is what duckboards are for, and the spares stack flat by the door |
| **Immersion suit rack** | storage | 108 | 1.3 × 1.7 × 0.4 m | `metal` | pooled | side-wall | a suit put away damp is a suit nobody will wear next week, so it hangs open on bars with a tray under it |
| **Tender line post** | stand | 96 | 0.4 × 1.35 × 0.4 m | `post` | pooled | side-wall | somebody on the surface holds the line and writes the time down, and that person stands at a post rather than in the way |
| **Coverall hamper** | waste | 96 | 0.9 × 1.0 × 0.6 m | `part` | pooled | side-wall | what came off the dirty side does not go back in the locker; it goes in a lidded hamper on the line between the two sides |
| **Dirty side bench** | bench | 84 | 1.6 × 0.86 × 0.7 m | `part` | pooled | side-wall | a room with a clean side and a dirty side needs a bench on the dirty one, or the line is a line nobody can keep |
| **Filter cabinet** | storage | 96 | 0.9 × 1.45 × 0.45 m | `steel` | pooled | side-wall | cartridges are dated, sized and issued as a pair, and a cabinet is what keeps them out of the air they are meant to filter |
| **Fit test bench** | bench | 72 | 1.4 × 0.88 × 0.65 m | `wood` | pooled | side-wall | a mask that has not been fitted to the face in front of it is jewellery, and fitting one is a seated job at a bench |
| **Spent cartridge bin** | waste | 84 | 0.44 × 0.66 × 0.44 m | `metal` | pooled | back-corner | a used cartridge is contaminated waste and it is kept apart from the general bin in the room it came off in |
| **Survey meter bench** | bench | 72 | 1.3 × 0.88 × 0.65 m | `part` | pooled | side-wall | a reading taken and written down is the whole of radiological work, and it is taken at a bench with the log on it |
| **Glove and mask dispenser** | storage | 72 | 0.84 × 0.55 × 0.22 m | `paint` | pooled | wall-mounted | the last thing put on before the clean side is taken from a box on the wall, one pair at a time, by somebody already gowned |
| **Dosimeter rack** | storage | 72 | 0.8 × 0.5 × 0.18 m | `metal` | pooled | wall-mounted | badges are issued to a name, read on a date and hung back in the same slot, which is why the rack is on the wall by the door |
| **Gowning locker** | storage | 120 | 1.2 × 1.7 × 0.48 m | `paint` | pooled | side-wall | the point of a gowning room is that what you walked in wearing stays on one side of it |
| **Tack mat stand** | stand | 96 | 0.9 × 0.3 × 0.7 m | `part` | pooled | back-corner | the last thing between a corridor and a clean room is a mat that takes the floor off your boots, and it lies at the threshold |
| **Extraction trunk stand** | machine | 96 | 0.44 × 1.45 × 0.44 m | `metal` | pooled | side-wall | dust taken off at the cut never reaches the lungs across the room, and the trunk that takes it stands beside the bench |
| **Sweep-up cart** | trolley | 188 | 0.8 × 0.95 × 0.52 m | `wood` | pooled | back-corner | shavings are swept up at the end of every session rather than at the end of the week, and the cart for it lives in the room |
| **Ear plug dispenser** | safety-fixture | 72 | 0.5 × 0.4 × 0.16 m | `paint` | pooled | wall-mounted | a shape hanging where a room record asks for hearing protection: schematic — a shape standing where a room record asks for it, not a fixture specification and not evidence that anything has been provided. It dispenses nothing |
| **Acoustic screen** | screen | 136 | 1.6 × 1.7 × 0.22 m | `part` | pooled | side-wall | noise is cut at the machine or it is not cut at all, and a screen around the loud corner is what lets the rest of the room talk |
| **Bonding lead reel** | storage | 168 | 0.55 × 1.05 × 0.52 m | `metal` | pooled | side-wall | two vessels at different potentials are what makes the spark, and the lead that ties them together is kept on a reel, not coiled |
| **Earth point post** | stand | 96 | 0.36 × 1.15 × 0.36 m | `post` | pooled | back-corner | an earth point is a place, not a wire; it is marked, it is fixed and it is where every lead in the room comes back to |
| **Calibration gas rack** | storage | 96 | 0.9 × 1.4 × 0.4 m | `metal` | pooled | side-wall | a monitor that has not been bumped against a known gas is a monitor nobody should trust, and the cylinders for it are racked |
| **Purge fan stand** | machine | 96 | 0.52 × 1.3 × 0.52 m | `metal` | pooled | back-corner | a space is ventilated before it is entered and while it is occupied, and the fan that does it stands by the opening |
| **Entry tripod** | stand | 140 | 0.68 × 1.7 × 0.68 m | `metal` | pooled | back-corner | nobody goes into a hole without a way of being pulled out of it, and the frame that does the pulling stands over the opening |
| **Retrieval winch post** | machine | 96 | 0.4 × 1.25 × 0.4 m | `steel` | pooled | side-wall | the line from the tripod goes somewhere, and where it goes is a winch on a post that somebody can crank without letting go |
| **Harness inspection rail** | storage | 96 | 1.4 × 1.65 × 0.4 m | `metal` | pooled | side-wall | a harness is looked at stitch by stitch before it is worn, and that is done hanging at eye height, not out of a bag |
| **Lanyard locker** | storage | 72 | 1.0 × 1.6 × 0.45 m | `steel` | pooled | side-wall | lanyards are issued in pairs, logged against a serial and taken out of service on a date; the locker is where that happens |
| **Helmet shelf** | storage | 72 | 1.0 × 0.6 × 0.3 m | `wood` | pooled | wall-mounted | a helmet with a chinstrap is a different helmet, and it is kept where the people who need one can see there are enough |
| **Edge protection stack** | stock | 84 | 1.2 × 0.85 × 0.55 m | `part` | pooled | back-corner | the boards and clips that make an edge safe are stacked in the room that teaches working at one, ready to be carried out |
| **Machine guard store** | storage | 96 | 1.4 × 1.55 × 0.5 m | `steel` | pooled | side-wall | a guard taken off for a job is a guard that has to go back on, and it waits on a rack with the machine's number on it |
| **Swarf bin** | waste | 84 | 0.6 × 0.74 × 0.6 m | `metal` | pooled | back-corner | turnings come off sharp, hot and in a long ribbon, and they are not swept up with a brush into a cardboard box |
| **Gowning bench** | seat | 72 | 1.6 × 0.48 × 0.5 m | `wood` | pooled | side-wall | you change at it before you cross the stripe the page already paints across a safety room doorway |
| **Permit board** | board | 96 | 1.14 × 0.8 × 0.06 m | `paint` | pooled | wall-mounted | the board the safety room is named after, and the one the records room files afterwards |
| **Boot change step** | seat | 60 | 1.0 × 0.46 × 0.5 m | `wood` | pooled | side-wall | boots come off sitting down and go on standing up, and the step that makes both possible is the width of two people |
| **Atmospheric check post** | stand | 96 | 0.32 × 1.36 × 0.32 m | `metal` | pooled | side-wall | the room says atmospheric checks happen here, so the thing they are made on stands in it |
| **Induction lectern** | stand | 96 | 0.7 × 1.2 × 0.44 m | `wood` | pooled | back-corner | nobody crosses the stripe without being told what is on the other side of it, and that is said standing at something |
| **Work trestle** | stand | 84 | 1.8 × 0.9 × 0.5 m | `wood` | pooled | side-wall | the bay is the floor a trade is learned on, and a trestle is what the work is held at height on while it is |
| **Learner stool** | seat | 96 | 0.44 × 0.62 × 0.44 m | `metal` | pooled | side-wall | nobody stands for six hours; a bay with no seat in it is a rendering of a bay |
| **Practice bench** | bench | 144 | 1.7 × 1.2 × 0.7 m | `steel` | pooled | side-wall | the first thing a trade puts in a bay is a bench with a vice on it, because that is where a hand learns to hold something still |
| **Task board** | board | 120 | 1.3 × 0.85 × 0.08 m | `paint` | pooled | wall-mounted | a bay runs to a task list that changes every session, and the list hangs where the person doing it can reach a marker |
| **Bay tool tree** | stand | 140 | 0.64 × 1.55 × 0.64 m | `metal` | pooled | back-corner | what is in use this session hangs in the middle of the bay where four people can reach it, not in a crib down the corridor |
| **Demonstration table** | bench | 84 | 1.35 × 0.84 × 0.85 m | `wood` | pooled | side-wall | an instructor does it once slowly at a table everybody can stand around before anybody does it fast at a bench |
| **Plant checkout board** | board | 132 | 1.34 × 0.9 × 0.06 m | `paint` | pooled | wall-mounted | plant is CHECKED OUT to this room, and a checkout that is not written down anywhere did not happen |
| **Bay guard rail** | screen | 112 | 2.0 × 1.1 × 0.22 m | `post` | pooled | side-wall | a training AREA is an area because something marks where it stops |
| **Plant service bench** | bench | 84 | 1.8 × 0.9 × 0.75 m | `steel` | pooled | side-wall | the machine is not the only thing in an equipment bay; the greasy end of looking after it happens at a bench beside it |
| **Lubricant store** | storage | 96 | 0.95 × 1.3 × 0.5 m | `cone` | pooled | back-corner | oils, greases and the pump that moves them are kept together, bunded and closed, and not on the floor by the machine |
| **Chock and block bin** | vessel | 84 | 0.9 × 0.6 × 0.6 m | `wood` | pooled | back-corner | nothing heavy is left standing on its own weight alone, and what stops it rolling lives in a bin at the bay mouth |
| **Machine log desk** | bench | 84 | 1.1 × 0.8 × 0.6 m | `wood` | pooled | side-wall | hours, faults and the last service are written down at the machine, in the room, by the person who ran it |
| **Issue counter** | bench | 84 | 1.8 × 0.86 × 0.6 m | `wood` | pooled | side-wall | the crib the page already builds hands tools ACROSS something, and until now it handed them across nothing |
| **Calibration cabinet** | storage | 96 | 0.94 × 1.36 × 0.54 m | `steel` | pooled | side-wall | calibration is the middle word of this room's purpose and it is the one that needs a locked box |
| **Return bin** | vessel | 84 | 0.6 × 0.78 × 0.6 m | `part` | pooled | back-corner | things come BACK to a crib, and a crib with nowhere to put them back is a counter with a queue |
| **Tool pegboard** | board | 156 | 1.2 × 0.95 × 0.12 m | `paint` | pooled | wall-mounted | a crib is read at a glance: a shadow board says what is out by the shape of the hole it left |
| **Battery charge shelf** | storage | 84 | 1.0 × 0.7 × 0.28 m | `metal` | pooled | wall-mounted | cordless plant is only issued charged, so the shelf that charges it is inside the crib rather than behind it |
| **Gauge drawers** | storage | 132 | 0.9 × 1.1 × 0.5 m | `steel` | pooled | side-wall | measuring kit is kept flat, apart and in a drawer with its own name on it, because a gauge in a heap is a gauge out of true |
| **Stock rack** | storage | 96 | 1.8 × 1.7 × 0.7 m | `metal` | pooled | side-wall | STOCK is the first word of this room's purpose and stock is kept on something |
| **Sheet stock rack** | stock | 72 | 1.4 × 1.6 × 0.6 m | `steel` | pooled | side-wall | flat stock leans; it does not stack, and a rack that lets it lean against something is what stops it bowing |
| **Bar stock cradle** | stock | 72 | 1.25 × 0.8 × 0.48 m | `metal` | pooled | side-wall | long stock is stored where it can be pulled out by one person without pulling the rest of the rack down with it |
| **Offcut bin** | waste | 84 | 0.9 × 0.66 × 0.6 m | `wood` | pooled | back-corner | OFFCUTS is the second word, and the difference between a trade shop and a warehouse is that the offcuts are kept |
| **Consumables shelf** | storage | 84 | 0.86 × 0.9 × 0.3 m | `wood` | pooled | wall-mounted | CONSUMABLES is the third word; they are small, they go at hand height, and they do not belong on the stock rack |
| **Consumable drum stand** | vessel | 84 | 0.64 × 0.9 × 0.64 m | `part` | pooled | back-corner | what is bought by the drum is drawn off by the litre, and the drum stands where the spillage can be seen |
| **Layout table** | bench | 84 | 2.0 × 0.8 × 0.9 m | `steel` | pooled | side-wall | setting out and marking are done flat, at waist height, on something that does not move |
| **Control point pillar** | stand | 96 | 0.4 × 1.28 × 0.4 m | `metal` | pooled | back-corner | a CONTROL POINT is a thing you can put an instrument over twice and get the same answer; a painted cross is not one |
| **Marking media shelf** | storage | 72 | 0.86 × 0.65 × 0.26 m | `wood` | pooled | wall-mounted | chalk, soapstone, paint and a wet rag are the whole of marking out, and they live at the table rather than in the crib |
| **Template rack** | storage | 108 | 1.2 × 1.45 × 0.45 m | `wood` | pooled | side-wall | a template that has been cut once is worth more than the drawing it came off, so it is hung flat and kept |
| **Setting-out line reel** | storage | 168 | 0.6 × 1.0 × 0.52 m | `metal` | pooled | side-wall | a line pulled off a reel is straight; a line pulled out of a pocket has a memory of the pocket |
| **Acceptance gauge stand** | stand | 96 | 0.36 × 1.26 × 0.36 m | `metal` | pooled | side-wall | ACCEPTANCE CRITERIA is a number somebody reads off something |
| **Sign-off desk** | bench | 84 | 1.4 × 0.8 × 0.7 m | `wood` | pooled | side-wall | SIGN-OFF is a person writing on paper at a desk, and the second half of what this room is for |
| **Sample cabinet** | storage | 96 | 1.0 × 1.4 × 0.45 m | `wood` | pooled | side-wall | an acceptance standard that can be held in the hand settles an argument a written one starts |
| **Surface plate table** | bench | 84 | 1.1 × 0.88 × 0.75 m | `steel` | pooled | side-wall | a flat reference is the one thing in an inspection room that everything else is measured against, and it is heavy on purpose |
| **Live rig frame** | stand | 72 | 1.5 × 1.66 × 0.35 m | `metal` | pooled | side-wall | a LIVE RIG is a frame with something wired to it that can be made to fail on purpose |
| **Fault-finding bench** | bench | 72 | 1.5 × 0.88 × 0.7 m | `steel` | pooled | side-wall | FAULT-FINDING happens with instruments on a surface, facing the rig |
| **Instrument cabinet** | storage | 72 | 0.85 × 1.3 × 0.45 m | `steel` | pooled | side-wall | test kit is the most stolen and most dropped thing in a shop, and it goes back in a case in a cupboard every time |
| **Fault log board** | board | 132 | 0.86 × 0.8 × 0.08 m | `paint` | pooled | wall-mounted | the same fault gets found twice unless the first person wrote on the board what it turned out to be |
| **Isolation post** | stand | 96 | 0.36 × 1.2 × 0.36 m | `post` | pooled | back-corner | a rig that can be made live has to be made dead from one place that everybody in the room can see is dead |
| **Shift board** | board | 120 | 1.64 × 0.95 × 0.08 m | `paint` | pooled | wall-mounted | a SHIFT START is people standing in front of a board that says who is doing what |
| **Hand-off table** | bench | 84 | 1.6 × 0.78 × 0.8 m | `wood` | pooled | side-wall | a HAND-OFF is two crews around one table with the drawing on it |
| **Crew bench** | seat | 60 | 1.7 × 0.46 × 0.45 m | `wood` | pooled | side-wall | a shift start is fifteen people in a room, and half of them have been on their feet since six |
| **Drawing easel** | board | 96 | 0.9 × 1.35 × 0.44 m | `wood` | pooled | back-corner | cross-trade means two trades looking at the same sheet, which means the sheet has to stand up where both can reach it |
| **Plan rack** | storage | 96 | 1.1 × 1.4 × 0.4 m | `metal` | pooled | side-wall | drawings roll, and a roll on a table is a roll on the floor; the rack is what keeps the set in order between hand-offs |
| **Records cabinet** | storage | 132 | 1.0 × 1.39 × 0.57 m | `steel` | pooled | side-wall | CERTIFICATES and AS-BUILTS are paper, and paper that matters lives in a drawer somebody can find |
| **As-built drawing chest** | storage | 108 | 1.2 × 0.95 × 0.7 m | `wood` | pooled | side-wall | an as-built is a big sheet and it is kept flat, because a folded one is read wrong for the next thirty years |
| **Permit file rack** | storage | 108 | 1.0 × 1.5 × 0.38 m | `metal` | pooled | side-wall | a permit is only evidence while it can be found, and it is found by date on a shelf rather than by memory |
| **Exam desk** | bench | 84 | 1.2 × 0.76 × 0.6 m | `wood` | pooled | side-wall | LEVEL TESTS are sat at a desk, and a classroom with no desks is a corridor |
| **Instructor lectern** | stand | 96 | 0.75 × 1.25 × 0.44 m | `wood` | pooled | back-corner | the INSTRUCTOR TRACK has an instructor in it and the instructor stands somewhere |
| **Classroom stool** | seat | 96 | 0.4 × 0.58 × 0.4 m | `wood` | pooled | side-wall | a desk without a stool is a shelf, and a level test takes two hours |
| **Progress board** | board | 144 | 0.86 × 0.9 × 0.08 m | `paint` | pooled | wall-mounted | a TRACK is something you can see yourself moving along, which means it is drawn on a wall where the cohort can read it |
| **Reference shelf** | storage | 84 | 0.86 × 0.8 × 0.28 m | `wood` | pooled | wall-mounted | a level test is against a standard, and the standard is a book somebody has to be able to take down and open |

## What it would cost

A hall interior is draw-call bound, not triangle bound. Every piece here pools or instances, none takes a mesh of its own, and every one of the three hundred names one of seven materials the page already builds — so the catalogue grew more than tenfold for no new material and no new draw call at all. The budget block refuses a design that would change that.

The ceiling comes from `web/eval_scene.mjs`: it is the only file in this repo that states what a rendered hall costs and what it may cost, and it states both with a reason; the multipliers are read from it too, so its policy moving moves this ceiling with it.

The measured baseline is quoted here for one reason:
it says which currency is scarce. A hall spends 157 of 196 permitted draw calls and 3,806 of 15,224 permitted triangles, so the draw call is the expensive one and the triangle is not. That measurement is
MEASURED-ELSEWHERE: measured 2026-09-22 in Chromium/SwiftShader at 1280x800 on quality rung high, by the eval this builder reads but does not run — verify_all.sh opens no browser and neither does this file. It leaves
39 draw calls and 11,418 triangles
unspent.

This pack takes half of that headroom and leaves half:
39 draw calls and
11,418 triangles a hall.
The worst hall stands 84 props in eleven rooms and pays 11 draw calls for all of them — 7% on top of what the hall already draws, for 218% more triangles.

| | Min | Median | Max |
|---|---|---|---|
| Props in a hall | 74 | 75 | 84 |
| Triangles | 7,452 | 7,496 | 8,316 |
| Draw calls | 8 | — | 11 |

One per pooled material for the whole hall plus one per instanced prop type; never one per prop. Across the bundle that is
8,448 props in 1,221 rooms
for 849,656 triangles — a prediction of what the rules
would place, not a measurement of anything drawn.

## What a prop is not

- **Not a specification.** These are shapes in a training environment. The eyewash stand is a cylinder and a bowl standing where a room record says corrosives are handled; the extinguisher is a cylinder on a plate; the press is a bed, a ram and a box with a dial on it. They are not fixture specifications, not rated appliances, not machine specifications, not compliance artefacts, and not evidence that any equipment has been provided anywhere. Nothing in this pack should be read as a safety-equipment specification, and a learner who has walked past one has not been trained on it.
- **Not reviewed.** The vocabulary is AUTHORED — a judgement about what a trade-training room contains — and no journey-level practitioner has reviewed it. The sentence each district piece gives for itself is DERIVED from the crib's own use line for the tool it names, which makes it accurate about the tool and no more authoritative about the furniture.
- **Not a second copy.** No room label, purpose, footprint, illuminance figure, hazard, PPE item, tool name or tool use sentence is typed in this pack. The room table is imported from web/interiors.py, the conditions are read from surfaces/registry/finishes.json, the tools are read from tools/registry/toolcribs.json and the district of a hall from unions/registry/unions.json. The page's body radius, eye height, grid unit, floor height, partition height, room-label height and bench setback are parsed out of web/build_3d.py, so a piece cannot be sized against a constant the page does not use.

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
