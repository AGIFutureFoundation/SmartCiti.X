# The measured venue

*measurements taken off a recorded 3D model of a real multi-salon event building, published as proportions the generated halls can be held against - and published in model units, because the file does not establish metres*

A real multi-salon event building was read, measured and left where it was.
Nothing of it is in this repository: 1,008 meshes and
575,792 triangles of it, 28,210,940 bytes in one file
that stays outside the tree. What this pack publishes is the measurement.

## Measured, not imported

The mesh count is the reason. The hall view of this bundle runs at 164 draw calls against a ceiling of 196; this one model is roughly five times that whole ceiling by itself. It is also a Paris conference venue and not a union training hall. It is measured, not imported.

The arithmetic is worth stating plainly: 1,008 meshes against the
196 draw calls a hall view is permitted by `web/eval_scene.mjs` is
**5.1×** the entire ceiling, in one model,
before a single hall is drawn. So it never enters the scene, and it never
enters the scene tree. It is a reference, and a reference is read once.

No geometry and no texture from the source is in this tree. The registry holds numbers about it and the four attribution fields the licence requires.

## Attribution

The licence is Creative Commons Attribution 4.0 International (`CC-BY-4.0`), which requires
attribution, a link to the work, a link to the licence and an indication of
what was changed. Those are fields in the registry rather than a sentence
somewhere, so a check can fail on a missing one — and `venue/test.mjs` does.

| | |
|---|---|
| **Title** | R+5_Salons Rive Gauche_Maison de la Mutualité |
| **Author** | [GL events Paris Venues](https://sketchfab.com/GLeventsParisVenues) |
| **Source** | <https://sketchfab.com/3d-models/r5-salons-rive-gauche-maison-de-la-mutualite-e9e40a09c82e42e8a145afa679ffac28> |
| **Licence** | [Creative Commons Attribution 4.0 International](http://creativecommons.org/licenses/by/4.0/) |
| **Changes made** | yes |
| **Indication of changes** | The work itself was NOT modified and is NOT redistributed here. No geometry, no texture and no part of the file is copied into this repository. What this pack publishes is measurement derived from the work - dimensions, areas, counts and ratios computed by reading it - which is a change from the work in the sense the licence asks about, so it is declared as one rather than argued about. |
| **Redistribution** | none. The source file stays outside this repository, at the upload path recorded beside this block, and the bundle ships no derivative of its geometry. |
| **Tier** | RECORDED — read verbatim out of the file's own asset.extras block; nothing here is typed by this build |

CC-BY-4.0 requires attribution, a link to the work, a link to the licence and an indication of changes. Those four are fields here rather than a sentence somewhere, so a check can fail on a missing one - and venue/test.mjs does.

## The unit question has no answer, and that is the answer

This is the most interesting thing on the page, so it goes here rather than in
a footnote.

The file carries exactly one unit statement: a uniform scale of
0.009999999776482582 on the node named
`8f103d18d47d4d9780948232f9f3e61c.fbx` — the conventional centimetre-to-metre factor an FBX exporter writes. It is the ONLY unit statement in the file.
Follow it and the whole building is
19 cm across — a multi-salon building 0.19 across. Not metres. Undo
it and the plan is 18.635 by
15.657 with a clear storey of
1.35 — a plan 18.635 by 15.657 with a 1.35 clear storey. Read as metres that is a room wider than a house with a ceiling nobody could stand under, so this is not metres either.

Neither reading survives, and the reason is a ratio rather than a preference:
The file does not establish a metre scale and this pack does not invent one. Every dimension published here is in model units. The plan-to-height ratio is the decisive evidence: the building is 13.8 times wider than its clear storey is high, and no reading of the file in which one unit is one metre survives that.

So the registry publishes `unit_scale.resolution` as **UNRESOLVED** and
every dimension on this page is in model unit (mu), symbol
`mu` — one unit of the authored geometry with the exporter node's 0.009999999776482582 scale undone. NOT a metre. See unit_scale.

If somebody needs metres: multiply by a single uniform factor and say where the factor came from. The panel family below is the only anchor in the file with a conventional real size: if those panels are door leaves of 1.8 to 2.3 metres, the factor falls between 2.44 and 3.11, which would put the clear storey between 3.29 and 4.2 metres. That is an ESTIMATE resting on an assumption about what the panels are, it is not a measurement, and nothing in this registry is computed from it.

## The ratios are the deliverable

A ratio does not care what the unit is. The unit of this file is not established, so the proportions are the part of the measurement that transfers to a hall at any scale - and proportion is what the generated halls lack, not size.

Take a hall's short plan dimension as the one number you own, and the rest follow. A room proportioned like this one is roughly 0.233 times as high as it is narrow, opens through gaps about 0.527 of its height across, and carries loose contents over about 0.283 of its floor. None of that is a rule; it is what one real building did.

Each ratio is two of the DERIVED figures above divided by one another; nothing new is measured here and nothing is typed. Tier: DERIVED.

| Ratio | Value |
|---|---|
| `building_plan_aspect` | 1.19 |
| `clear_run_median_over_clear_storey` | 0.6667 |
| `clear_storey_over_building_short_side` | 0.0862 |
| `clear_storey_over_largest_plate_short_side` | 0.2328 |
| `datum_step_over_clear_storey` | 0.2267 |
| `floor_plate_fill_of_its_own_bbox` | 0.817 |
| `furniture_occupancy_of_floor_plate` | 0.283 |
| `largest_floor_plate_aspect` | 1.603 |
| `modelled_floor_over_building_footprint` | 0.561 |
| `opening_height_over_clear_storey` | 0.5474 |
| `opening_width_over_clear_storey` | 0.5267 |

## What was measured

The building box is 18.635 × 2.238 ×
15.657 mu over a plan footprint of 291.77 mu²
at aspect 1.19, split into 5
fabric meshes and 1,003 contents meshes.
Every mesh's POSITION accessor bounds, transformed by the node chain above it and unioned. This is a BOUNDING BOX over a model, not a surveyed building dimension: it includes whatever sticks out furthest and it is not wall-to-wall anything.

- **Clear storey.** Modal 1.35 mu over
  1,104 measured plan cells, carrying
  0.975 of them. The distribution is narrow, not a spread: the modal height carries 0.975 of the measured cells and both floor datums return the same clear height, which is why this pack is willing to call it a storey height at all.
- **Circulation.** 6,119 clear cells against
  2,411 occupied, out of 8,530 floor cells —
  occupancy 0.283, median clear run 0.9 mu.
  A clear run is not a corridor. It is the distance across unfurnished floor in one of the two plan axes, which is what circulation width means in a room laid out with loose seating and nothing else. It says nothing about a walled corridor, because this model has no walled corridors to measure.
- **Openings.** 12 panels at 0.739 mu high and
  0.09 mu thick, widths 0.513 to
  0.882 mu, median 0.711.
  INFERRED FROM SHAPE, NOT LABELLED IN THE FILE. 12 of 12 sit with modelled floor within 0.35 mu on BOTH sides. A partition or a screen has floor on one side or none; a doorway has it on both. That supports the reading and does not prove it - a glazed bay between two furnished areas would pass the same test. What would settle it:
  a named object, a door material, or a hole in the wall mesh at the same place. The file has none of the three: the walls are one shell mesh and the panel family carries a flat black material with no name beyond its index.
- **Contents clusters.** 15 clusters at a
  gap of 0.2 mu with at least 8 members.

The cluster count has no natural answer, so the sensitivity is published beside
it. Single-linkage clustering has no natural answer; the count depends on the gap. The sensitivity table is published beside the clusters for exactly that reason, and it moves from 145 clusters to 31 across the probed range.

| Gap | Clusters | At or above the minimum |
|---|---|---|
| 0.1 mu | 145 | 26 |
| 0.15 mu | 55 | 15 |
| 0.2 mu | 52 | 15 |
| 0.3 mu | 41 | 10 |
| 0.4 mu | 31 | 8 |

## What the file says about itself

The file's own bytes and its own JSON chunk; every number below is read, none is typed. Tier: RECORDED.

| | |
|---|---|
| accessors | 4,079 |
| animations | 1 |
| bufferViews | 16 |
| buffers | 1 |
| images | 10 |
| materials | 70 |
| meshes | 1,008 |
| nodes | 1,542 |
| samplers | 1 |
| scenes | 1 |
| textures | 10 |
| generator | Sketchfab-16.16.0 |
| glTF version | 2.0 (container 2) |
| file bytes | 28,210,940 |
| sha256 | `b3b850ee49c5c5b8657fc1872e34b97456431934aebfcd87cb551929f5f26838` |

## The parameters every measurement depends on

| Parameter | Value | What it means |
|---|---|---|
| `plan_grid` | 0.1 | the cell size, in model units, that floor triangles and object footprints are rasterised onto |
| `cluster_gap` | 0.2 | two contents meshes join one cluster when their plan bounding boxes are within this many model units of each other on both plan axes |
| `fabric_footprint_threshold` | 9.0 | a mesh whose world bounding box covers more than this many square model units in plan is treated as building fabric rather than contents |
| `horizontal_tolerance` | 0.002 | a triangle counts as horizontal when its three vertices lie within this many model units of one height |

## What this is not

- **Not a survey.** The building extent and every cluster dimension is an axis-aligned BOUNDING BOX over a set of meshes. It is not a wall-to-wall room dimension, it includes anything that sticks out, and no record here calls it a survey. The floor plates come closer - they are the actual extent of modelled floor - but their width and depth are still the box around a floor patch.
- **Not whole.** Fabric geometry covers only part of the plan: 1104 plan cells carry a measurable height above a floor datum, out of 8530 cells of modelled floor on the upper datum alone. The clear-height figure is a measurement of where there is a roof, not of the whole building.
- **Not labelled.** The openings are inferred from shape, not labelled in the file.
- **Not metres.** The file does not establish a metre scale and this pack does not invent one. Every dimension published here is in model units. The plan-to-height ratio is the decisive evidence: the building is 13.8 times wider than its clear storey is high, and no reading of the file in which one unit is one metre survives that.
- **Not redistributed.** No geometry and no texture from the source is in this tree. The registry holds numbers about it and the four attribution fields the licence requires.
- **Recorded.** The asset block, the counts, the byte length and the digest. That is all. Those are statements the file makes about itself and this build copies them.
- **Derived.** Every dimension, area, height and ratio. They are computed here from the node transforms and the vertex buffer, and a computation from recorded geometry is DERIVED however careful it is.

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
