# The building kit

18 pieces in 15 families that hang on the outside of a
hall — a stoop, a gutter, a downpipe, a parapet coping, a bollard — so a campus
of building envelopes reads as built rather than as diagrammed.

**None of it is drawn yet.** The whole-campus arithmetic is a PREDICTION, not a measurement. It counts what the placement rules would place and what those pieces would cost if they merge as declared. web/build_3d.py now DRAWS them - kitDress() hangs every admitted piece on the envelope building() just drew, through the district pool it fills, and flushKit() instances the two instanced families per campus - and window.__tc3dKit() reports the pieces, triangles and draw calls actually built beside the figures predicted here, so the prediction can be checked against the drawing from a browser. Only running web/eval_scene.mjs against the page says whether the campus stays under its ceilings - and the baseline it is measured against is one campus, treasure-island, so the other nine are unmeasured ground.

## What a piece is

SCHEMATIC: every piece here is the SHAPE of a thing, not a measurement of one. A downpipe is a cylinder and two brackets at a plausible size; a meter box is two boxes. No dimension was taken off a real component, no product was consulted, and no standard is referenced.

This kit loads no mesh, no texture, no model and no file. Every piece is built in the browser from THREE.BoxGeometry and THREE.CylinderGeometry, which is why a triangle budget can be checked against a recipe at all. Nothing was vendored from the reference measurement and nothing from it is reproduced here.

No hall is named in this pack. A piece is admitted by roofline and facade pattern, both of which are read from the registries that own them - web/build_3d.py's STYLE_OF for the district roofline, world/registry/world.json's fabric for the city's, and surfaces/registry/finishes.json for the pattern vocabulary those facades must already belong to.

## The measured reference

The triangle budgets below are held against a measurement made outside this
repository and recorded in
[`assets/REFERENCE.md`](../assets/REFERENCE.md): a glTF 2.0 inspection of six downloaded reference models, run outside this repository on files it does not contain. This build cannot re-run it and does not try to: the figures below are quoted, not verified here.

No mesh, texture, name, shape or layout from any measured file is reproduced in this pack or anywhere in this bundle. Two of the five are third-party copyrighted work. What was taken is a distribution.

- One residential city block that reads convincingly as a place:
  21,893 triangles over 93 meshes,
  median mesh 104 triangles.
- One interior from the same era: 70 meshes, median
  46 triangles.
- One modern character figure: 222,507 triangles in
  3 meshes behind 12.3 MB of
  texture — ten times this whole page.

The block pays 93 materials for 93 meshes, which is 93 draw calls for one street. That is an export artefact, not a design, and this kit is held to the opposite arrangement by its own draw-call check.

The reference figures were measured outside this repository on files it does not contain, and this build cannot re-run that inspection. They are quoted, not verified here. The scene costs are different: they come from web/eval_scene.mjs, which does run against this page, and they are read out of that file rather than restated.

## The 18 pieces

43 primitives in all — 36 boxes and
7 cylinders — between 12 and
72 triangles a piece, median 34,
556 for the whole vocabulary. The median mesh of the
measured block is 104 triangles, so every piece here is
smaller than the thing it is meant to read as.

| Piece | Family | Triangles | Size | Material | Merge | What it is made of |
|---|---|---|---|---|---|---|
| **Entrance stoop** | stoop | 36 | 2.6 × 0.45 × 1.4 m | `mat.slab` | pooled | 3× box — the pad, the riser below it, one cheek wall |
| **Entrance tread** | step | 12 | 2.4 × 0.15 × 0.34 m | `mat.slab` | pooled | 1× box — one tread |
| **Kerb run** | kerb | 12 | 4.0 × 0.14 × 0.3 m | `mat.slab` | pooled | 1× box — four metres of kerb |
| **Parapet coping run** | parapet | 12 | 6.0 × 0.18 × 0.6 m | `fabric.roof` | pooled | 1× box — six metres of coping |
| **Parapet corner block** | parapet | 12 | 0.7 × 0.26 × 0.7 m | `fabric.roof` | pooled | 1× box — the returned corner |
| **Eaves gutter** | gutter | 24 | 4.0 × 0.16 × 0.18 m | `mat.metal` | pooled | 1× box — the trough; 1× cylinder — the rolled front bead |
| **Downpipe run** | downpipe | 40 | 0.14 × 5.4 × 0.14 m | `mat.metal` | pooled | 1× cylinder — the pipe, open at both ends; 2× box — two wall brackets |
| **Downpipe shoe** | downpipe | 24 | 0.2 × 0.3 × 0.4 m | `mat.metal` | pooled | 1× cylinder — the spill at the bottom |
| **Wall vent hood** | vent | 40 | 0.5 × 0.5 × 0.36 m | `mat.metal` | pooled | 2× box — the back plate and the hood; 1× cylinder — the spigot through the wall |
| **Louvred vent panel** | vent | 24 | 0.9 × 0.6 × 0.12 m | `mat.metal` | pooled | 2× box — the frame and the blade face |
| **Door awning** | awning | 36 | 2.4 × 0.34 × 1.1 m | `fabric.trim` | pooled | 3× box — the canopy and two struts |
| **Bollard** | bollard | 32 | 0.22 × 0.95 × 0.22 m | `mat.post` | instanced | 1× cylinder — the post, capped |
| **Wall-mounted hand rail** | rail | 36 | 2.4 × 0.08 × 0.14 m | `mat.metal` | pooled | 1× cylinder — the rail itself; 2× box — two brackets |
| **Sign bracket** | sign-bracket | 36 | 0.95 × 0.7 × 0.14 m | `mat.metal` | pooled | 3× box — the arm, the stay and the wall plate |
| **Surface conduit run** | conduit | 36 | 0.08 × 4.2 × 0.08 m | `mat.metal` | pooled | 1× cylinder — the conduit; 2× box — two saddles |
| **Meter box** | meter-box | 24 | 0.55 × 0.75 × 0.26 m | `mat.metal` | pooled | 2× box — the enclosure and its door |
| **Planter tub** | planter | 48 | 1.2 × 0.55 × 1.2 m | `mat.slab` | instanced | 4× box — the tub as four sides; no soil box, the top is never seen from a walker's eye |
| **Caged roof ladder** | cage-ladder | 72 | 0.52 × 5.0 × 0.16 m | `mat.metal` | pooled | 6× box — two stiles and four rungs; the cage hoops are the one thing here a texture cannot fake and are still left out, because six boxes reads as a ladder and eighteen does not |

The 5 materials named above all already exist in the page,
and 2 of them are already pooled per district, so pieces
wearing those cost no new draw call at all. A piece that named a colour of its
own would be a second opinion about a colour `world/` owns; this registry
publishes none.

## Where a piece is admitted

A piece is admitted by roofline and facade pattern, both read from the
registries that own them, never from a table in this pack. The envelope it
hangs on is the page's own: 12.0 m wide,
`6 + (depth % 3) * 0.7` high, door toward
local -z — read out of the page, not restated: change the page and this build fails rather than describing a building that is no longer drawn.

| Family | Wall | Run | Datum | Rooflines | Facades | Why there |
|---|---|---|---|---|---|---|
| **stoop** | front | `frontage` | grade | flat, gable, saw | 5 of 5 | the page builds every hall with its door toward local -z, so the front is the one wall whose position is guaranteed; a threshold sits on the ground in front of it whatever the city is built of |
| **step** | front | `frontage` | grade | flat, gable, saw | 5 of 5 | a tread in front of the threshold, for the same reason and at the same wall |
| **kerb** | ground | `frontage` | grade | flat, gable, saw | 5 of 5 | buildCampus() already lays a driveway to every door; a kerb is the edge that driveway meets, and it belongs to the ground rather than to any wall |
| **parapet** | roofline | `roof_perimeter` | eaves | flat | 5 of 5 | a parapet is what a flat roof has instead of an eaves. The page draws the flat roofline as a rooftop unit and nothing else, so the top of a flat hall is the one edge with nothing on it |
| **gutter** | roofline | `eaves_run` | eaves | gable | 5 of 5 | a gutter needs an eaves to hang off, and the page gives an eaves only to the gable roofline - its two pitched slabs run along the depth, so the gutter does too |
| **downpipe** | side | `both_sides` | wall | flat, gable, saw | 5 of 5 | water comes off every roofline this page draws, and it comes down a side wall rather than across the door |
| **vent** | side | `both_sides` | wall | flat, gable, saw | 5 of 5 | every hall in this bundle has plant in it; the side wall is where a hall puts what it does not want on its front |
| **awning** | front | `front_width` | wall | flat, gable | 5 of 5 | shade over the entrance. A sawtooth hall's front is a goods opening rather than a door people gather at, so it is not given one |
| **bollard** | ground | `frontage` | grade | flat, gable, saw | 5 of 5 | the driveway runs to the door; something has to stop it running through the door |
| **rail** | front | `front_width` | wall | flat, gable, saw | 5 of 5 | a hand hold beside the threshold, on the wall the door is in. Every hall has a stoop and a tread, so every hall has the small change of level a rail exists for |
| **sign-bracket** | front | `front_width` | wall | flat, gable, saw | 5 of 5 | the page already hangs a district-hued fascia on the hall; the bracket is the ironwork that arm would need, and it carries nothing itself - the label sprite is the page's |
| **conduit** | back | `back_width` | wall | flat, saw | 5 of 5 | surface conduit runs up the back of a building to the roof plant. On a gable there is no roof deck to run to, so the gable rooflines do not admit it |
| **meter-box** | back | `back_width` | wall | flat, gable, saw | 5 of 5 | the service entry goes on the wall nobody arrives at, which on this page is the wall away from the plaza - the page points every door at local -z, so the back is knowable |
| **planter** | ground | `frontage` | grade | flat, gable, saw | 5 of 5 | the campus already has a green ring and a walkway; a tub at the frontage is the same idea at building scale |
| **cage-ladder** | back | `back_width` | wall | flat, saw | 3 of 5 | roof access reaches a flat deck or a sawtooth valley, never a pitch. It also needs a facade that takes a fixing: the plywood and smooth-stucco cities do not get one |

## How many get placed

12 pieces are counted per hall and
6 per metre of run:

| Piece | Rate |
|---|---|
| `entry-stoop` | 1 per hall |
| `entry-step` | 1 per hall |
| `kerb-run` | one every 6.0 m of run |
| `parapet-coping` | one every 16.0 m of run |
| `parapet-corner` | 2 per hall |
| `eaves-gutter` | one every 6.0 m of run |
| `downpipe-run` | 2 per hall |
| `downpipe-shoe` | 1 per hall |
| `wall-vent` | one every 26.0 m of run |
| `louvre-vent` | 1 per hall |
| `door-awning` | 1 per hall |
| `bollard` | one every 12.0 m of run |
| `wall-rail` | 1 per hall |
| `sign-bracket` | 1 per hall |
| `conduit-run` | one every 12.0 m of run |
| `meter-box` | 1 per hall |
| `planter-tub` | 1 per hall |
| `cage-ladder` | 1 per hall |

## What a campus would cost

The campus view costs 273 draw calls and 15,850 triangles: the whole fifty-one-hall campus is smaller in triangles than one reference street block. This page is draw-call bound with an unused triangle budget, so the draw-call ceiling is the one that governs and the triangle ceiling is a courtesy to the pack that spends next.

The ceiling is read from `web/eval_scene.mjs` rather than chosen here:
web/eval_scene.mjs measured the campus view at 273 draw calls and holds it to 1.25x that, so 68 is what is left for everything added after the measurement. It is read from that file, not typed here. web/eval_scene.mjs allows the campus view four times its measured 15,850 triangles and says in its own comment that the kit and props packs are expected to spend it. Two packs cannot each spend all of it. This kit takes 70 per cent of the headroom because it clothes every one of the fifty-one building envelopes on the campus, and leaves 30 per cent for the props that stand on the ground between them.

| Campus | Halls | Districts | Facade | Pieces | Triangles | Draw calls |
|---|---|---|---|---|---|---|
| **Treasure Island Campus** | 51 | 3 | `panel` | 1,117 | 31,392 | 8 |
| **Oakland Waterfront Campus** | 32 | 3 | `brick` | 529 | 17,448 | 8 |
| **Crescent Works Campus** | 28 | 2 | `smooth` | 598 | 16,128 | 6 |

At Treasure Island Campus — the campus the scene harness actually drives to, so the baseline the arithmetic is added to is a measurement of this campus and not of a campus nobody scored —
that is 1,117 pieces for 8 draw calls:
6 merged per district and 2
instanced, 139.6 pieces to a call, against the ceiling of
68. Its 31,392 triangles fit inside the
33,285 this kit claims — 70%
of the 47,550 the eval leaves unspent, with the
rest left for the props that stand on the ground between the buildings.

Every one of those figures is arithmetic over the placement rules above:
nothing has been drawn, so nothing has been measured.

## What this is not

- **Not a construction detail.** Nothing in this registry is a construction detail and nobody should build anything from it. There are no gauges, no fixing centres, no material specifications, no loads, no falls and no clearances. A size here is the size something reads as from across a campus green, chosen so a fifty-one-building campus looks built rather than diagrammed.
- **Not a measurement.** The whole-campus arithmetic is a PREDICTION, not a measurement. It counts what the placement rules would place and what those pieces would cost if they merge as declared. web/build_3d.py now DRAWS them - kitDress() hangs every admitted piece on the envelope building() just drew, through the district pool it fills, and flushKit() instances the two instanced families per campus - and window.__tc3dKit() reports the pieces, triangles and draw calls actually built beside the figures predicted here, so the prediction can be checked against the drawing from a browser. Only running web/eval_scene.mjs against the page says whether the campus stays under its ceilings - and the baseline it is measured against is one campus, treasure-island, so the other nine are unmeasured ground.
- **Not a kit of parts.** The word kit is the modelling sense: a small set of repeated pieces that assemble into variety. It is not a construction kit of parts, not a specification, not a schedule and not a takeoff.
- **Provenance.** SCHEMATIC for the shapes and sizes; AUTHORED for the placement rates, which are somebody's judgement about how often a thing appears on a wall. MEASURED-ELSEWHERE for the nine reference figures in `reference`, and for the scene costs read out of web/eval_scene.mjs.

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
