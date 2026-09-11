# The metaverse layer

built to the open interchange baseline. No private "metaverse standard" is referenced or claimed: what is listed under standards is implemented and tested, and what is listed under not_claimed is honestly not.

The contract in one line: **standard files out, the learner's own files
in.** No service, no account, no token, no blockchain — and
`meta/test.mjs` holds every claim on this page against the page source
that implements it.

## Standards claimed

| Standard | Body | Role here |
|---|---|---|
| `gltf-2.0` | Khronos Group | scene and avatar interchange - binary .glb export from the locker and any hall, learner-local import onto the guest stand |
| `webxr` | W3C | immersive VR/AR entry in the 3D environment, feature-gated to platforms that offer the session |
| `geojson-wgs84` | IETF RFC 7946 | the geo registry interchange (campuses.geojson, network.geojson) that the geomap and any Mapbox/MapLibre stack consume |

The glTF exports open directly in Unity, Sketchfab, Blender, Godot, three.js.

## Honestly not claimed

| Standard | Why not |
|---|---|
| `vrm` | humanoid-avatar spec compliance is not asserted until validated against the reference tooling; exports are plain core glTF |
| `omi-gltf-extensions` | no OMI extension is emitted; core glTF only |
| `usd` | no USD is written or read |

## The Unity avatar systems, reviewed

Three MIT-licensed Unity avatar systems were read from their own
checkouts before choosing (checkouts not present; review carried as recorded):

| Repository | Licence | What it is | Verdict |
|---|---|---|---|
| [`vrm-c/UniVRM`](https://github.com/vrm-c/UniVRM) | MIT | the reference Unity implementation of VRM - a humanoid avatar profile layered on glTF 2.0, with a fixed bone vocabulary (hips, spine, chest, neck, head, left/rightUpperArm, LowerArm, Hand, UpperLeg, Foot) and the MToon stylised shader | ADOPTED IN PART - the bone vocabulary only. We name the bones our rig actually exposes with VRM names so Unity and VRM importers map them automatically; we vendor none of its code and do not claim VRM compliance. |
| [`microsoft/Microsoft-Rocketbox`](https://github.com/microsoft/Microsoft-Rocketbox) | MIT | a library of rigged, animated human avatars for Unity, organised as Adults, Children and Professions, with an animation set - the closest thing to an off-the-shelf realistic trades crew | NOT BUNDLED, available to the learner - its licence would permit redistribution, but the Academy ships its own original avatars and this bundle stays free of third-party artwork. A learner may load any Rocketbox avatar through the locker's guest stand, where the .glb import already works. |
| [`readyplayerme/rpm-unity-sdk-core`](https://github.com/readyplayerme/rpm-unity-sdk-core) | MIT | a Unity SDK that fetches a hosted, service-generated avatar as glTF at runtime | NOT ADOPTED - it is a client for an external avatar service, and this layer holds that a learner's avatar must not require an account or leave the device. The same .glb it produces still imports through the guest stand. |

**The rig.** VRM / Unity humanoid bone names (vrm-c/UniVRM, MIT) — and the
hierarchy now carries **every bone VRM requires of a humanoid**, nested as
the spec nests them, as real transform nodes in rest pose:

```
hips ── spine ── chest ── neck ── head
 │                 └───── left/rightUpperArm ── LowerArm ── Hand
 └─── left/rightUpperLeg ── LowerLeg ── Foot
```

Deliberately absent (all VRM *optional*):
`upperChest`, `leftShoulder`, `rightShoulder`, `leftToes`, `rightToes`, `leftEye`, `rightEye`, `jaw` —
the hierarchy carries every bone VRM requires of a humanoid, nested as the spec nests them, so a Unity Humanoid or VRM importer maps the whole skeleton. The bones left out are VRM OPTIONAL ones the capsule body has no articulation for - naming them would claim joints that cannot move.

**And they move.** the bones are driven, not decorative: the walk cycle swings the legs in opposition with the knees bending only on the return, the arms counter-swing at the elbow, the locker idle breathes through the spine, and the neck and head turn toward the viewer within a human range (neck 0.6 rad, head 0.4 rad). The gait is keyed to distance covered and the settle decays per second, so both look the same at any frame rate. Reduced-motion viewers keep the rest pose.

**What the export carries.**
the motion is computed at view time and no animation clip is exported: the .glb carries the rest-pose skeleton only, which is what a Unity Humanoid or VRM import needs to retarget its own clips.

## Conventions

glTF 2.0 binary (.glb) · metres ·
up axis +Y · scenes named
`tc-hall-<slug> with room-<strand> floors and the guest-asset stand` ·
`Sprite`, `Line`, `Points`
stripped on export. The avatar rig: `tc-avatar` → `hips` → `spine` → `chest` → `neck` → `head` → `leftUpperArm` → `leftLowerArm` → `leftHand` → `rightUpperArm` → `rightLowerArm` → `rightHand` → `leftUpperLeg` → `leftLowerLeg` → `leftFoot` → `rightUpperLeg` → `rightLowerLeg` → `rightFoot` → `headwear`.

## Exports

| File | From | Content |
|---|---|---|
| `tc-avatar.glb` | the locker view (the .glb button) | the learner's configured avatar - the Academy's own original capsule-humanoid meshes and canvas textures |
| `tc-hall-<slug>.glb` | any hall view (the .glb button) | the hall interior - slab, rooms, fixtures, crib - as named nodes |

## Imports

learner-local only: a .glb or .gltf chosen from the device renders on the locker's guest stand, fitted to 1.3 m, and never uploads anywhere. This repository ships no third-party model, and the learner remains responsible for the licence of any asset they load - a free Sketchfab download under CC-BY, for example, carries its attribution duty with it.

## The Unity bridge

[`AGIFutureFoundation/ml-agents`](https://github.com/AGIFutureFoundation/ml-agents)
— Unity ML-Agents Toolkit (Unity Technologies, Apache-2.0), carried as com.unity.ml-agents. the declared Unity-side consumer: exported tc-hall-<slug>.glb scenes and tc-avatar.glb rigs import into a Unity project as training environments and agent bodies for ML-Agents.
**Status:** export-ready: the .glb files open in Unity today. No trained agent, scene integration or benchmark is claimed until it exists in that repository.
(cross-checked against the ml-agents checkout.)

## What this layer is not

a metaverse layer is file formats and honesty, not a place: exports are plain Khronos glTF of this bundle's own original meshes; imports never leave the device; no service, account, token or blockchain is involved, nothing here is an NFT. The single-file artifact build carries the exporter and loader inline and delivers exports as a viewer-confirmed .zip; only where neither door exists do the buttons degrade to a HUD line instead of failing.

---

*Generated by `wiki/build_wiki.py` from the verified registries — edit the sources, not this page. Adaptive Stack v3.2 · pack 3.2.0.*
