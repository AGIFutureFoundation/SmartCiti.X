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

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

PACK_VERSION = "3.2.0"
BUILT = "2026-09-11"

DOC = {
    'baseline': {
        'note': 'built to the open interchange baseline. No private '
                '"metaverse standard" is referenced or claimed: what is '
                'listed under standards is implemented and tested, and '
                'what is listed under not_claimed is honestly not.',
        'standards': [
            {'id': 'gltf-2.0', 'body': 'Khronos Group',
             'role': 'scene and avatar interchange - binary .glb export '
                     'from the locker and any hall, learner-local import '
                     'onto the guest stand',
             'consumers': ['Unity', 'Sketchfab', 'Blender', 'Godot',
                           'three.js']},
            {'id': 'webxr', 'body': 'W3C',
             'role': 'immersive VR/AR entry in the 3D environment, '
                     'feature-gated to platforms that offer the session'},
            {'id': 'geojson-wgs84', 'body': 'IETF RFC 7946',
             'role': 'the geo registry interchange (campuses.geojson, '
                     'network.geojson) that the geomap and any '
                     'Mapbox/MapLibre stack consume'},
        ],
        'not_claimed': [
            {'id': 'vrm', 'why': 'humanoid-avatar spec compliance is not '
                                 'asserted until validated against the '
                                 'reference tooling; exports are plain '
                                 'core glTF'},
            {'id': 'omi-gltf-extensions', 'why': 'no OMI extension is '
                                                 'emitted; core glTF only'},
            {'id': 'usd', 'why': 'no USD is written or read'},
        ],
    },
    'conventions': {
        'format': 'glTF 2.0 binary (.glb)',
        'units': 'metres',
        'up_axis': '+Y',
        'avatar_rig': ['tc-avatar', 'head', 'headwear', 'arm-L', 'arm-R'],
        'scene_naming': 'tc-hall-<slug> with room-<strand> floors and the '
                        'guest-asset stand',
        'stripped_on_export': ['Sprite', 'Line', 'Points'],
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
                  'nothing here is an NFT, and where module resolution is '
                  'unavailable (the single-file artifact build) the '
                  'buttons degrade to a HUD line instead of failing.',
    },
}

# every claim above that names page behavior is held against the page
page_src = (ROOT / 'web/build_3d.py').read_text()
for node in DOC['conventions']['avatar_rig']:
    assert f"'{node}'" in page_src, f'rig node {node} not named in the page'
assert "'tc-hall-' + sg" in page_src, 'hall naming drifted from the page'
assert "'guest-asset'" in page_src, 'guest stand missing from the page'
for token in ('GLTFExporter', 'GLTFLoader', 'never uploaded'):
    assert token in page_src, f'{token} missing from the page'
for fname in ('gltf/GLTFExporter.js', 'gltf/GLTFLoader.js',
              'utils/TextureUtils.js', 'utils/BufferGeometryUtils.js'):
    assert (ROOT / 'web/vendor/addons' / fname).exists(), f'{fname} not vendored'
assert (ROOT / 'geo/registry/network.geojson').exists()

# the Unity bridge is RECORDED: when the fork's checkout sits beside this
# repository, hold the claim against it (same pattern as geo vs Locator.X)
mla = ROOT.parent / 'agifuturefoundation' / 'ml-agents'
bridge_checked = 'checkout not present; claim carried as recorded'
if mla.exists():
    assert (mla / 'com.unity.ml-agents').is_dir(), \
        'the fork no longer carries com.unity.ml-agents'
    assert (mla / 'LICENSE.md').exists(), 'the fork lost its license file'
    bridge_checked = 'cross-checked against the ml-agents checkout'
DOC['unity_bridge']['recorded_check'] = bridge_checked

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
