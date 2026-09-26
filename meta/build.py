#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the metaverse-layer registry builder.

A metaverse layer is file formats and honesty, not a place. This registry
declares exactly what the Academy's 3D environment exchanges with the
world outside it — which open standards, under which conventions, through
which page controls — and what is deliberately NOT claimed. No private or
proprietary standard governs this layer: no such spec exists in this
bundle, and what is claimed is exactly what the suites test.

The contract in one line: standard files out (glTF 2.0, the Khronos
interchange Unity, Sketchfab, Blender, Godot and three.js all consume;
GeoJSON for the geographic layer; WebXR for immersive entry) and the
LEARNER'S OWN files in (a .glb chosen from the device renders on the
locker's guest stand and never uploads anywhere). No service, no account,
no token, no blockchain — and meta/test.mjs holds every claim here
against the page source that implements it.
"""
import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

# the simulator roster the WebXR role counts - read from sims/, never typed
_n_sims = len(json.load(open(ROOT / 'sims/registry/sims.json'))['sims'])

# One bundle version, read from the manifest rather than typed here (this
# pack had drifted to 3.3.0 while ROADMAP said 3.2.0 was unified everywhere).
PACK_VERSION = json.load(open(ROOT / 'pack/manifest.json'))['pack_version']
BUILT = "2026-09-17"

DOC = {
    'baseline': {
        'note': 'built to the open interchange baseline. No private '
                '"metaverse standard" is referenced or claimed: what is '
                'listed under standards is implemented and tested, and '
                'what is listed under not_claimed is honestly not. The '
                'Open Metaverse Browser Initiative (OMBI) is an open '
                'initiative, but its spatial-fabric, SOM and RMAP shapes '
                'are unverified against any normative text this build '
                'could read, so they sit under not_claimed, not standards.',
        'standards': [
            {'id': 'gltf-2.0', 'body': 'Khronos Group',
             'role': 'scene and avatar interchange - binary .glb export '
                     'from the locker and any hall, learner-local import '
                     'onto the guest stand',
             'consumers': ['Unity', 'Sketchfab', 'Blender', 'Godot',
                           'three.js']},
            {'id': 'webxr', 'body': 'W3C',
             'role': 'immersive VR/AR entry in the 3D environment, '
                     'feature-gated to platforms that offer the session, '
                     'and experimental: a viewpoint, not a second world. '
                     'What exists - an XR rig the headset rides in (the '
                     'camera\'s parent; walking, seat poses and turns move '
                     'the rig, never the camera), a local-floor reference '
                     'space with a plain local fallback (rig lifted 1.6 m, '
                     'said in the hint), AR passthrough (the drawn sky, '
                     'ground, grid and fog banks suppressed, clear alpha 0), '
                     'controller input - thumbsticks, trigger, grip and the '
                     'two face buttons - landing in the same key state a '
                     'keyboard fills through each seat\'s declared xr '
                     'mapping, snap-turn locomotion (30 degrees, no smooth '
                     'rotation) with the same wall clamps a desktop walk '
                     'has, a wrist panel of readout signs off the same '
                     'gauges the dash shows, the scripted reference '
                     'operator watchable in-session, and every one of the '
                     f'{_n_sims} simulators operable in a session. The quality '
                     'ladder is honest about three.js r160: fixed foveation '
                     'and the fog banks step live, the framebuffer scale '
                     '(1.0 / 0.8 / 0.65) is recorded in-session and applied '
                     'at the next session start. What does NOT exist: hand '
                     'tracking, rendered hands or a body beyond two '
                     'schematic controllers, and any run on a physical '
                     'headset - this build verified the layer against a '
                     'mocked WebXR session in headless Chromium (three.js\'s '
                     'own WebXRManager driven by a fake session, frame and '
                     'input sources) only.'},
            {'id': 'geojson-wgs84', 'body': 'IETF RFC 7946',
             'role': 'the geo registry interchange (campuses.geojson, '
                     'network.geojson) that the geomap and any '
                     'Mapbox/MapLibre stack consume'},
            {'id': 'geopose-1.0',
             'body': 'Open Geospatial Consortium (OGC 21-056r11)',
             'role': 'Basic-YPR poses for every campus, institution anchor '
                     'and pinned restoration site '
                     '(spatial/registry/geopose.json), horizontal position '
                     'at its source provenance, height and heading '
                     'honestly zero-with-UNKNOWN',
             'consumers': ['any application/geopose+json reader',
                           'OSCP GeoPose Protocol clients']},
        ],
        'not_claimed': [
            {'id': 'vrm', 'why': 'humanoid-avatar spec compliance is not '
                                 'asserted until validated against the '
                                 'reference tooling; exports are plain '
                                 'core glTF'},
            {'id': 'omi-gltf-extensions', 'why': 'no OMI extension is '
                                                 'emitted; core glTF only'},
            {'id': 'usd', 'why': 'no USD is written or read'},
            {'id': 'ombi-spatial-fabric',
             'why': 'the OMBI fabric manifest (spatial/registry/fabric.json) '
                    'is shaped after the public deck and press, Q3 2026 - '
                    'no normative specification was reachable from this '
                    'build, so the shape is unvalidated, and it has not '
                    'been loaded in Sneeze, Artemis or any other metaverse '
                    'browser'},
            {'id': 'ombi-som',
             'why': 'the Scene Object Model (spatial/registry/som.json) is '
                    'SOM-shaped - a multi-origin scene graph with '
                    'per-branch ownership, authored from the deck\'s '
                    'vocabulary - not conformant to a specification this '
                    'build could read, and unverified in any browser'},
            {'id': 'rmap',
             'why': 'no RMAP endpoint, server or protocol is implemented: '
                    'the fabric is static files, every service runs '
                    'in-page with no network, and no DID is minted'},
        ],
    },
    # Reviewed on the Unity side before choosing: three MIT-licensed avatar
    # systems, each read from its own checkout rather than its marketing.
    # The decision is the last row - we adopt the VRM humanoid VOCABULARY
    # for our exported rig, which costs nothing, ships no third-party code,
    # and makes our .glb land in Unity Humanoid and VRM tooling as itself.
    'avatar_systems_reviewed': [
        {'repo': 'vrm-c/UniVRM', 'licence': 'MIT',
         'holder': 'VRM Consortium (MToon: Masataka SUMI)',
         'what': 'the reference Unity implementation of VRM - a humanoid '
                 'avatar profile layered on glTF 2.0, with a fixed bone '
                 'vocabulary (hips, spine, chest, neck, head, '
                 'left/rightUpperArm, LowerArm, Hand, UpperLeg, Foot) and '
                 'the MToon stylised shader',
         'verdict': 'ADOPTED IN PART - the bone vocabulary only. We name '
                    'the bones our rig actually exposes with VRM names so '
                    'Unity and VRM importers map them automatically; we '
                    'vendor none of its code and do not claim VRM '
                    'compliance.'},
        {'repo': 'microsoft/Microsoft-Rocketbox', 'licence': 'MIT',
         'holder': 'Microsoft',
         'what': 'a library of rigged, animated human avatars for Unity, '
                 'organised as Adults, Children and Professions, with an '
                 'animation set - the closest thing to an off-the-shelf '
                 'realistic trades crew',
         'verdict': 'NOT BUNDLED, available to the learner - its licence '
                    'would permit redistribution, but the Academy ships '
                    'its own original avatars and this bundle stays free '
                    'of third-party artwork. A learner may load any '
                    'Rocketbox avatar through the locker\'s guest stand, '
                    'where the .glb import already works.'},
        {'repo': 'readyplayerme/rpm-unity-sdk-core', 'licence': 'MIT',
         'holder': 'Ready Player Me',
         'what': 'a Unity SDK that fetches a hosted, service-generated '
                 'avatar as glTF at runtime',
         'verdict': 'NOT ADOPTED - it is a client for an external avatar '
                    'service, and this layer holds that a learner\'s '
                    'avatar must not require an account or leave the '
                    'device. The same .glb it produces still imports '
                    'through the guest stand.'},
    ],
    'conventions': {
        'format': 'glTF 2.0 binary (.glb)',
        'units': 'metres',
        'up_axis': '+Y',
        'rig_vocabulary': {
            'standard': 'VRM / Unity humanoid bone names (vrm-c/UniVRM, MIT)',
            # every bone VRM REQUIRES of a humanoid, plus the two optional
            # torso bones, each a real nested transform node in rest pose
            'required_complete': True,
            'exposed': ['hips', 'spine', 'chest', 'neck', 'head',
                        'leftUpperArm', 'leftLowerArm', 'leftHand',
                        'rightUpperArm', 'rightLowerArm', 'rightHand',
                        'leftUpperLeg', 'leftLowerLeg', 'leftFoot',
                        'rightUpperLeg', 'rightLowerLeg', 'rightFoot'],
            'not_exposed': ['upperChest', 'leftShoulder', 'rightShoulder',
                            'leftToes', 'rightToes', 'leftEye', 'rightEye',
                            'jaw'],
            'why': 'the hierarchy carries every bone VRM requires of a '
                   'humanoid, nested as the spec nests them, so a Unity '
                   'Humanoid or VRM importer maps the whole skeleton. The '
                   'bones left out are VRM OPTIONAL ones the capsule body '
                   'has no articulation for - naming them would claim '
                   'joints that cannot move.',
            'articulation': 'the bones are driven, not decorative: the '
                            'walk cycle swings the legs in opposition with '
                            'the knees bending only on the return, the '
                            'arms counter-swing at the elbow, the locker '
                            'idle breathes through the spine, and the neck '
                            'and head turn toward the viewer within a human '
                            'range (neck 0.6 rad, head 0.4 rad). The gait '
                            'is keyed to distance covered and the settle '
                            'decays per second, so both look the same at '
                            'any frame rate. Reduced-motion viewers keep '
                            'the rest pose.',
            'no_animation_track': 'the motion is computed at view time and '
                                  'no animation clip is exported: the .glb '
                                  'carries the rest-pose skeleton only, '
                                  'which is what a Unity Humanoid or VRM '
                                  'import needs to retarget its own clips.',
        },
        'avatar_rig': ['tc-avatar', 'hips', 'spine', 'chest', 'neck', 'head',
                       'leftUpperArm', 'leftLowerArm', 'leftHand',
                       'rightUpperArm', 'rightLowerArm', 'rightHand',
                       'leftUpperLeg', 'leftLowerLeg', 'leftFoot',
                       'rightUpperLeg', 'rightLowerLeg', 'rightFoot',
                       'headwear'],
        'scene_naming': 'tc-hall-<slug> with room-<strand> floors and the '
                        'guest-asset stand',
        'stripped_on_export': ['Sprite', 'Line', 'Points'],
        'host_mediated_save': 'where the hosting page mediates file saves '
                              '(the published artifact), the export is '
                              'offered as <file>.zip (STORE method, the '
                              '.glb inside unchanged) through a viewer '
                              'confirmation - .zip is on the host '
                              'allowlist, .glb is not',
    },
    'exports': [
        {'id': 'avatar-glb', 'from': 'the locker view (the .glb button)',
         'file': 'tc-avatar.glb',
         'content': 'the learner\'s configured avatar - the Academy\'s own '
                    'original capsule-humanoid meshes and canvas textures'},
        {'id': 'hall-glb', 'from': 'any hall view (the .glb button)',
         'file': 'tc-hall-<slug>.glb',
         'content': 'the hall interior - slab, rooms, fixtures, crib - as '
                    'named nodes'},
    ],
    'imports': {
        'policy': 'learner-local only: a .glb or .gltf chosen from the '
                  'device renders on the locker\'s guest stand, fitted to '
                  '1.3 m, and never uploads anywhere. This repository '
                  'ships no third-party model, and the learner remains '
                  'responsible for the licence of any asset they load - '
                  'a free Sketchfab download under CC-BY, for example, '
                  'carries its attribution duty with it.',
    },
    'unity_bridge': {
        'repo': 'AGIFutureFoundation/ml-agents',
        'upstream': 'Unity ML-Agents Toolkit (Unity Technologies, '
                    'Apache-2.0), carried as com.unity.ml-agents',
        'role': 'the declared Unity-side consumer: exported '
                'tc-hall-<slug>.glb scenes and tc-avatar.glb rigs import '
                'into a Unity project as training environments and agent '
                'bodies for ML-Agents',
        'status': 'export-ready: the .glb files open in Unity today. No '
                  'trained agent, scene integration or benchmark is '
                  'claimed until it exists in that repository.',
        'provenance': 'RECORDED - the fork exists in the organization and '
                      'carries the upstream toolkit; cross-checked against '
                      'the checkout when present',
    },
    'honesty': {
        'status': 'a metaverse layer is file formats and honesty, not a '
                  'place: exports are plain Khronos glTF of this bundle\'s '
                  'own original meshes; imports never leave the device; no '
                  'service, account, token or blockchain is involved, '
                  'nothing here is an NFT. The single-file artifact build '
                  'carries the exporter and loader inline and delivers '
                  'exports as a viewer-confirmed .zip; only where neither '
                  'door exists do the buttons degrade to a HUD line '
                  'instead of failing.',
    },
}

# The export is VALIDATED, structurally, by web/test_gltf.mjs: it captures
# the .glb the built page hands the learner and holds the bytes to the glTF
# 2.0 container rules and referential integrity. ONE TRUTH: the rule list
# is that file's RULES table, read out of it here - never retyped - and
# meta/test.mjs holds the two equal. What the check does NOT cover is said
# here, once, and printed by the suite on every run. No count is recorded:
# the registry is built without a browser, so bytes, accessors and nodes
# are facts of a capture and live only in the suite's output.
_gltf_suite = (ROOT / 'web/test_gltf.mjs').read_text()
_rules_src = _gltf_suite.split('const RULES = [', 1)[1].split('\n];', 1)[0]
_rules = [{'id': m.group(1), 'what': m.group(2)} for m in
          re.finditer(r"\{ id: '([^']+)', what: '([^']+)' \}", _rules_src)]
assert len(_rules) >= 10, 'web/test_gltf.mjs RULES table not readable'
# every entry of the table must have been read: a `what` the regex cannot
# take (an apostrophe) would drop a rule from the registry silently
assert len(_rules) == _rules_src.count("{ id: '"), \
    'a RULES entry in web/test_gltf.mjs was not readable by the builder regex'
assert len({r['id'] for r in _rules}) == len(_rules), 'duplicate rule id in web/test_gltf.mjs'
DOC['structural_validation'] = {
    'suite': 'web/test_gltf.mjs',
    'scope': 'a container-and-references check of the exported .glb, '
             'written from the glTF 2.0 rules the suite states: the GLB '
             'header, chunk lengths and alignment, the JSON chunk, and every '
             'index one glTF object holds to another. It is not Khronos '
             'conformance. Static mode holds the export path in the built '
             'page and proves the validator on a synthetic file, and says '
             'that no export was captured; --browser captures the bytes the '
             'page produces for one hall (the first of its roster, or '
             '--hall=<slug>) and for the locker avatar at '
             'URL.createObjectURL, validates each, and watches every rule '
             'fail by name on the real bytes; --all drives every hall of '
             'the roster before the locker.',
    'rules': _rules,
    'not_covered': [
        'the Khronos glTF 2.0 JSON schema: not reachable from the build '
        'that wrote this (network blocked), so no schema validation is applied',
        'Khronos gltf-validator conformance: the official validator was not '
        'reachable, so no conformance is claimed',
        'material and texture semantics: PBR factors, sampler settings and '
        'the decoded image bytes are not inspected, only their references',
        'animation, skins and morph targets: none is exported (the rule only '
        'asserts the animations array is absent), so nothing is validated',
        'accessor min/max against the data, normal unit length and other '
        'geometry semantics beyond index range',
        'a run on a physical consumer: no Unity, Blender, Godot or Sketchfab '
        'import of a captured file was performed by the build',
    ],
    'counts': 'never recorded here: bytes, chunk lengths, accessors, nodes '
              'and per-rule checked counts are facts of a capture and live '
              'in the output of node web/test_gltf.mjs --browser',
}

# every claim above that names page behavior is held against the page
page_src = (ROOT / 'web/build_3d.py').read_text()
for node in ('tc-avatar', 'headwear'):
    assert f"'{node}'" in page_src, f'rig node {node} not named in the page'
_rig = DOC['conventions']['rig_vocabulary']
for b in _rig['exposed']:
    limb = b[4:] if b.startswith('left') else (
        b[5:] if b.startswith('right') else None)
    assert (f"bone('{b}'" in page_src
            or (limb and f"bone(side + '{limb}'" in page_src)), \
        f'VRM bone {b} is not built by the page'
for b in _rig['not_exposed']:
    assert f"bone('{b}'" not in page_src, f'{b} is claimed absent but built'
# the articulation claim is only worth making if the page enforces it
assert 'const NECK_MAX = .6, HEAD_MAX = .4;' in page_src, \
    'the head-turn limits drifted from the range the registry states'
for fn in ('function gait(', 'function gaitRest(', 'function idleBreath('):
    assert fn in page_src, f'{fn} is claimed by the registry but not built'
assert 'animations:' not in page_src, \
    'the export claims no animation track; the page must not write one'
assert "'tc-hall-' + sg" in page_src, 'hall naming drifted from the page'
assert "'guest-asset'" in page_src, 'guest stand missing from the page'
for token in ('GLTFExporter', 'GLTFLoader', 'never uploaded', 'zipOne'):
    assert token in page_src, f'{token} missing from the page'
# the WebXR role names page behaviour; every named piece must be built
for token in ("const xrRig = new THREE.Group()", 'function seatPose(',
              "setReferenceSpaceType(xrFloor ? 'local-floor' : 'local')",
              'renderer.setClearAlpha(0)', 'function xrInput(', 'function xrSnap(',
              'function setXRDash(', 'function xrWatchToggle(',
              'setFramebufferScaleFactor(XR_SCALES[xrScaleIdx])', 'setFoveation(xrFov)'):
    assert token in page_src, f'WebXR role claims {token!r} but the page lacks it'
_xr_role = next(s for s in DOC['baseline']['standards'] if s['id'] == 'webxr')['role']
assert 'mocked WebXR session' in _xr_role and 'physical' in _xr_role, \
    'the WebXR role must say how it was verified, and what it was not'
for fname in ('gltf/GLTFExporter.js', 'gltf/GLTFLoader.js',
              'utils/TextureUtils.js', 'utils/BufferGeometryUtils.js'):
    assert (ROOT / 'web/vendor/addons' / fname).exists(), f'{fname} not vendored'
assert (ROOT / 'geo/registry/network.geojson').exists()
# the GeoPose claim is only worth making if spatial/ actually emits it
_geopose = json.load(open(ROOT / 'spatial/registry/geopose.json'))
assert _geopose['encoding'].startswith('OGC GeoPose 1.0 Basic-YPR, OGC 21-056r11'), \
    'spatial/ no longer emits the GeoPose encoding meta/ claims'
assert _geopose['counts']['total'] > 0
for _oid in ('ombi-spatial-fabric', 'ombi-som', 'rmap'):
    assert not any(s['id'] == _oid for s in DOC['baseline']['standards']), \
        f'{_oid} must never be claimed as a standard'

# The avatar review is RECORDED from checkouts, not from marketing: where
# those checkouts sit beside this repo, hold each licence claim against the
# licence file that repository actually ships.
import os
rev = pathlib.Path(os.environ.get('TC_AVATAR_REVIEW', '')) if os.environ.get(
    'TC_AVATAR_REVIEW') else None
if rev and rev.is_dir():
    for sysrec in DOC['avatar_systems_reviewed']:
        d = rev / sysrec['repo'].split('/')[1]
        if not d.is_dir():
            continue
        lic = next((f for f in d.glob('LICENSE*')), None)
        assert lic, f"{sysrec['repo']}: no licence file in the checkout"
        assert 'MIT' in lic.read_text()[:400], \
            f"{sysrec['repo']}: licence drifted from MIT"
    print('cross-check: TC_AVATAR_REVIEW checkouts present, licences held')
else:
    print('cross-check: TC_AVATAR_REVIEW not set, avatar review cross-check skipped')
# the committed field is the contract, byte-stable across machines (see
# geo/build.py); meta/test.mjs repeats the comparison on every run
DOC['avatar_review_check'] = {
    'contract': 'cross-checked against the reviewed checkouts when '
                'TC_AVATAR_REVIEW names the directory that holds them',
    'checkout': '$TC_AVATAR_REVIEW/<repo name>',
    'held': ['each reviewed repository still ships an MIT licence file'],
    'where': 'meta/build.py asserts at build time; meta/test.mjs repeats the '
             'comparison on every run and says so when the checkouts are absent',
}

# the Unity bridge is RECORDED: when the fork's checkout sits beside this
# repository, hold the claim against it (same pattern as geo vs Locator.X)
mla = ROOT.parent / 'agifuturefoundation' / 'ml-agents'
if mla.exists():
    assert (mla / 'com.unity.ml-agents').is_dir(), \
        'the fork no longer carries com.unity.ml-agents'
    assert (mla / 'LICENSE.md').exists(), 'the fork lost its license file'
    print('cross-check: ml-agents checkout present, bridge claim held')
else:
    print('cross-check: ml-agents checkout not present, cross-check skipped')
DOC['unity_bridge']['recorded_check'] = {
    'contract': 'cross-checked against the ml-agents checkout when it is '
                'present beside this repository',
    'checkout': '../agifuturefoundation/ml-agents',
    'held': ['the fork carries com.unity.ml-agents', 'the fork ships LICENSE.md'],
    'where': 'meta/build.py asserts at build time; meta/test.mjs repeats the '
             'comparison on every run and says so when the checkout is absent',
}

# the network dashboard names its own contributing pack for every other
# platform-wide fact but used to say nothing about this one - the drift
# guard for that gap
BOOTSTRAP = '--bootstrap' in __import__('sys').argv
if not BOOTSTRAP:
    dash = (ROOT / 'web/trade_craft_dashboard.html').read_text()
    assert str(len(DOC['avatar_systems_reviewed'])) in dash, \
        'the dashboard does not render the Unity-avatar-systems-reviewed count'
    assert DOC['honesty']['status'] in dash, \
        'the dashboard does not carry the metaverse-layer honesty line'

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

doc = {
    'pack': 'smartcitix-trade-craft-academy-metaverse-layer',
    'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
    'pack_version': PACK_VERSION,
    'built': BUILT,
    'source_stamp': stamp,
    **DOC,
}

OUT = HERE / 'registry'
OUT.mkdir(exist_ok=True)
(OUT / 'metaverse.json').write_text(json.dumps(doc, indent=1) + '\n')
print(f"metaverse layer: {len(DOC['baseline']['standards'])} standards "
      f"claimed, {len(DOC['baseline']['not_claimed'])} honestly not, "
      f"{len(DOC['exports'])} exports (source stamp {stamp})")
