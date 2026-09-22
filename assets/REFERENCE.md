# Reference models: what was measured, what was concluded

Six `.glb` models were uploaded as visual references for the 3D
environment. They were opened by a script, measured, and closed. This
note records the measurements and the two conclusions drawn from them.

## What was looked at, and what was not done with it

The six files were read to learn a technique: how a scene that reads as
a place is actually built, in triangles, meshes and textures. None of
them was vendored into this repository and none ever will be.

Two are assets from Grand Theft Auto: San Andreas
(`gtasa__grove_street.glb`, `gtasa-_samshaus.glb`). That geometry and
those textures are Rockstar Games' copyright, and redistributing them
is not something this bundle can do. The other four carry no stated
copyright at all — the `copyright` field of every one of the six reads
"(none stated)" — so their licence is unknown, and unknown is itself a
reason not to ship them. This repository commits the full SIL Open Font
License beside every typeface it serves (`THIRD_PARTY.md`, the web
fonts row). Ripped game geometry cannot meet that bar, and neither can a
file whose licence nobody wrote down.

Reading a file to learn how it was made is not the same as
redistributing it. Both halves are true: the files were read, and the
files are not here.

## Measurements

Taken from the glTF containers directly, not from a viewer. File size is
the `.glb` on disk; texture MB is the sum of the embedded images.

| Model | File (MB) | Triangles | Meshes | Materials | Images | Textures (MB) | Animations |
|---|---|---|---|---|---|---|---|
| `frickies_yacht.glb` | 6.31 | 70,770 | 45 | 44 | 43 | 2.58 | 0 |
| `construction_worker_in_safety_gear.glb` | 25.41 | 222,507 | 3 | 1 | 4 | 12.32 | 0 |
| `gtasa__grove_street.glb` | 7.11 | 21,893 | 93 | 93 | 93 | 5.72 | 0 |
| `uploads_files_3484000_BoredApeLP_1.glb` | 0.31 | 13,142 | 1 | 7 | 0 | 0.00 | 0 |
| `crop_harvestor.glb` | 1.59 | 7,067 | 9 | 4 | 3 | 1.26 | 1 |
| `gtasa-_samshaus.glb` | 3.81 | 26,411 | 70 | 70 | 76 | 2.02 | 0 |

## The finding that matters

Grove Street is a whole residential block — houses, fences, street,
yards — and it reads convincingly as a place. It does that in 21,893
triangles over 93 meshes. The median mesh is 104 triangles; the smallest
is 2. Its commonest texture is 128×128 pixels: 39 of its 93 images are
that size, and a further 31 are 256×256.

Sam's House, a single interior from the same game, is 26,411 triangles
over 70 meshes with a median mesh of 46 triangles. 40 of its 76 textures
are 128×128.

Against that, the single construction-worker figure is 222,507
triangles in 3 meshes, with four 2048×2048 maps totalling 12.32 MB. One
character carries ten times the triangles of a whole block and more
than twice its texture bytes, and stands nowhere.

The conclusion is that a place reads as a place because of many small
distinct pieces carrying many small distinct textures, not because of
geometry density. Ninety-three things of about a hundred triangles each,
every one with its own 128-pixel image, make a street. Two hundred
thousand triangles under four 2048-pixel maps make one figure.

The scale matters for this project in particular. The entire 3D page,
`web/trade_craft_3d.html`, is about 1.15 MB. The character model's
textures alone are roughly ten times the size of the whole application;
the file as a whole is more than twenty times.

## The anti-pattern in the same data

Grove Street pays 93 materials for its 93 meshes: one material, one
image and one draw call per piece. That is how Sketchfab exports a scene
that was never merged, not how it was rendered in the game, and it is
not good practice. Sam's House is the same: 70 materials for 70 meshes.

This bundle already does the merging. Decoration is pooled into one
merged mesh per material per district, and the beacons are instanced.
Nothing measured here argues against that. The lesson is to take the
piece vocabulary — small, distinct, cheaply textured — and keep the
merging.

## What this changed here

Two packs are being built from this finding.

`kit/` holds small modular exterior pieces: the walls, fences, steps,
awnings and street furniture from which a block is assembled. It
declares a per-piece triangle budget citing the Grove Street median of
104 triangles per mesh.

`props/` holds interior props, one strand per room type. It declares a
per-prop triangle budget citing the Sam's House median of 46 triangles
per mesh.

Both budgets are stated as measured medians of a scene that is known to
read well, not as targets chosen for their roundness.

## Provenance

RECORDED. Every figure above was taken from the six files by a script,
`/tmp/claude-0/glb/inspect.py`, which walks the glTF JSON and the binary
image chunks. It is a scratch script and is not committed.
