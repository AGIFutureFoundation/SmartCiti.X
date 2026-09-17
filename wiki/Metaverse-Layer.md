# The metaverse layer

built to the open interchange baseline. No private "metaverse standard" is referenced or claimed: what is listed under standards is implemented and tested, and what is listed under not_claimed is honestly not. The Open Metaverse Browser Initiative (OMBI) is an open initiative, but its spatial-fabric, SOM and RMAP shapes are unverified against any normative text this build could read, so they sit under not_claimed, not standards.

The contract in one line: **standard files out, the learner's own files
in.** No service, no account, no token, no blockchain — and
`meta/test.mjs` holds every claim on this page against the page source
that implements it.

## Standards claimed

| Standard | Body | Role here |
|---|---|---|
| `gltf-2.0` | Khronos Group | scene and avatar interchange - binary .glb export from the locker and any hall, learner-local import onto the guest stand |
| `webxr` | W3C | immersive VR/AR entry in the 3D environment, feature-gated to platforms that offer the session, and experimental: a viewpoint, not a second world. What exists - an XR rig the headset rides in (the camera's parent; walking, seat poses and turns move the rig, never the camera), a local-floor reference space with a plain local fallback (rig lifted 1.6 m, said in the hint), AR passthrough (the drawn sky, ground, grid and fog banks suppressed, clear alpha 0), controller input - thumbsticks, trigger, grip and the two face buttons - landing in the same key state a keyboard fills through each seat's declared xr mapping, snap-turn locomotion (30 degrees, no smooth rotation) with the same wall clamps a desktop walk has, a wrist panel of readout signs off the same gauges the dash shows, the scripted reference operator watchable in-session, and every one of the eleven simulators operable in a session. The quality ladder is honest about three.js r160: fixed foveation and the fog banks step live, the framebuffer scale (1.0 / 0.8 / 0.65) is recorded in-session and applied at the next session start. What does NOT exist: hand tracking, rendered hands or a body beyond two schematic controllers, and any run on a physical headset - this build verified the layer against a mocked WebXR session in headless Chromium (three.js's own WebXRManager driven by a fake session, frame and input sources) only. |
| `geojson-wgs84` | IETF RFC 7946 | the geo registry interchange (campuses.geojson, network.geojson) that the geomap and any Mapbox/MapLibre stack consume |
| `geopose-1.0` | Open Geospatial Consortium (OGC 21-056r11) | Basic-YPR poses for every campus, institution anchor and pinned restoration site (spatial/registry/geopose.json), horizontal position at its source provenance, height and heading honestly zero-with-UNKNOWN |

The glTF exports open directly in Unity, Sketchfab, Blender, Godot, three.js.

## Honestly not claimed

| Standard | Why not |
|---|---|
| `vrm` | humanoid-avatar spec compliance is not asserted until validated against the reference tooling; exports are plain core glTF |
| `omi-gltf-extensions` | no OMI extension is emitted; core glTF only |
| `usd` | no USD is written or read |
| `ombi-spatial-fabric` | the OMBI fabric manifest (spatial/registry/fabric.json) is shaped after the public deck and press, Q3 2026 - no normative specification was reachable from this build, so the shape is unvalidated, and it has not been loaded in Sneeze, Artemis or any other metaverse browser |
| `ombi-som` | the Scene Object Model (spatial/registry/som.json) is SOM-shaped - a multi-origin scene graph with per-branch ownership, authored from the deck's vocabulary - not conformant to a specification this build could read, and unverified in any browser |
| `rmap` | no RMAP endpoint, server or protocol is implemented: the fabric is static files, every service runs in-page with no network, and no DID is minted |

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
