/**
 * Metaverse-layer registry verification.
 *
 * The layer is a set of interchange claims, and a claim is only as good
 * as the code that implements it: every standard listed must be the one
 * the page actually speaks, every rig node must be named in the page
 * source, the vendored modules must exist, and the not-claimed list must
 * stay honest — VRM stays unclaimed until validated, and nothing here
 * may drift toward tokens, uploads or a private standard.
 */
import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const reg = JSON.parse(readFileSync(new URL('./registry/metaverse.json', import.meta.url)));
const page = readFileSync(new URL('../web/build_3d.py', import.meta.url), 'utf8');

ok('the baseline is the open one, and says no private standard governs the layer',
  /open interchange baseline/.test(reg.baseline.note)
  && /No private/.test(reg.baseline.note));
ok('three standards are claimed - glTF 2.0, WebXR, GeoJSON - each with its body and role',
  reg.baseline.standards.length === 3
  && ['gltf-2.0', 'webxr', 'geojson-wgs84'].every((id) =>
      reg.baseline.standards.some((s) => s.id === id && s.body && s.role))
  && reg.baseline.standards.find((s) => s.id === 'gltf-2.0')
      .consumers.includes('Unity'));
ok('the not-claimed list stays honest: VRM, OMI extensions and USD are unclaimed with reasons',
  ['vrm', 'omi-gltf-extensions', 'usd'].every((id) =>
    reg.baseline.not_claimed.some((x) => x.id === id && x.why.length > 20)));

/* --------------------------------------------------------- conventions --- */
ok('conventions are complete: .glb, metres, +Y up, a named rig, named scenes',
  reg.conventions.format === 'glTF 2.0 binary (.glb)'
  && reg.conventions.units === 'metres' && reg.conventions.up_axis === '+Y'
  && reg.conventions.avatar_rig.length === 19
  && /tc-hall-<slug>/.test(reg.conventions.scene_naming));
ok('the two non-bone rig nodes are named in the page, and the bones are built by name',
  ['tc-avatar', 'headwear'].every((node) => page.includes(`'${node}'`))
  && reg.conventions.avatar_rig.filter((x) =>
      !['tc-avatar', 'headwear'].includes(x)).length === 17);
ok('the host-mediated save door is declared and implemented: a confirmed .zip carrying the unchanged .glb',
  /\.zip/.test(reg.conventions.host_mediated_save)
  && /unchanged/.test(reg.conventions.host_mediated_save)
  && /zipOne/.test(page) && /downloads/.test(page));
ok('the export stripper is declared and implemented: sprites, lines, points never ship',
  ['Sprite', 'Line', 'Points'].every((k) =>
    reg.conventions.stripped_on_export.includes(k))
  && /isSprite \|\| o\.isLine \|\| o\.isPoints/.test(page));

ok('three Unity avatar systems were reviewed from their own checkouts, each MIT, each with a verdict',
  reg.avatar_systems_reviewed.length === 3
  && ['vrm-c/UniVRM', 'microsoft/Microsoft-Rocketbox',
      'readyplayerme/rpm-unity-sdk-core'].every((r) =>
      reg.avatar_systems_reviewed.some((x) => x.repo === r
        && x.licence === 'MIT' && x.holder && x.what.length > 40
        && /^(ADOPTED|NOT)/.test(x.verdict)))
  && /cross-checked|carried as recorded/.test(reg.avatar_review_check));
ok('the review adopts VRM only as a vocabulary, and bundles no third-party avatar',
  /ADOPTED IN PART/.test(reg.avatar_systems_reviewed
    .find((x) => x.repo === 'vrm-c/UniVRM').verdict)
  && /vendor none of its code/.test(reg.avatar_systems_reviewed
    .find((x) => x.repo === 'vrm-c/UniVRM').verdict)
  && /NOT BUNDLED/.test(reg.avatar_systems_reviewed
    .find((x) => /Rocketbox/.test(x.repo)).verdict)
  && /must not require an account/.test(reg.avatar_systems_reviewed
    .find((x) => /readyplayerme/.test(x.repo)).verdict));
// VRM 1.0 requires these fifteen of a humanoid; the rig now carries all
// of them, plus the two optional torso bones, as real nested nodes
const VRM_REQUIRED = ['hips', 'spine', 'head',
  'leftUpperArm', 'leftLowerArm', 'leftHand',
  'rightUpperArm', 'rightLowerArm', 'rightHand',
  'leftUpperLeg', 'leftLowerLeg', 'leftFoot',
  'rightUpperLeg', 'rightLowerLeg', 'rightFoot'];
ok('the rig carries every bone VRM requires of a humanoid, and the registry claims exactly that',
  reg.conventions.rig_vocabulary.standard.includes('VRM')
  && reg.conventions.rig_vocabulary.required_complete === true
  && VRM_REQUIRED.every((b) => reg.conventions.rig_vocabulary.exposed.includes(b))
  && reg.conventions.rig_vocabulary.exposed.length === 17);
ok('the bones it leaves out are VRM OPTIONAL ones, and it says why',
  reg.conventions.rig_vocabulary.not_exposed
    .every((b) => !VRM_REQUIRED.includes(b))
  && ['upperChest', 'leftShoulder', 'leftToes', 'jaw']
    .every((b) => reg.conventions.rig_vocabulary.not_exposed.includes(b))
  && /VRM OPTIONAL/.test(reg.conventions.rig_vocabulary.why)
  && /cannot move/.test(reg.conventions.rig_vocabulary.why));
ok('every claimed bone is actually built by the page, and no unclaimed one is',
  reg.conventions.rig_vocabulary.exposed.every((b) => {
    const limb = b.startsWith('left') ? b.slice(4)
      : b.startsWith('right') ? b.slice(5) : null;
    return page.includes(`bone('${b}'`)
      || (limb && page.includes(`bone(side + '${limb}'`));
  })
  && reg.conventions.rig_vocabulary.not_exposed
    .every((b) => !page.includes(`bone('${b}'`)));
ok('the bones are driven, not decorative: the page implements the gait the registry describes',
  /walk cycle/.test(reg.conventions.rig_vocabulary.articulation)
  && /Reduced-motion/.test(reg.conventions.rig_vocabulary.articulation)
  && /function gait\(/.test(page) && /function gaitRest\(/.test(page)
  && /function idleBreath\(/.test(page)
  && /if \(!b \|\| reduced\) return;/.test(page));
ok('the head-turn is bounded to the human range the registry states, and the page enforces it',
  /neck 0\.6 rad, head 0\.4 rad/.test(reg.conventions.rig_vocabulary.articulation)
  && /const NECK_MAX = \.6, HEAD_MAX = \.4;/.test(page)
  && /Math\.max\(-NECK_MAX, Math\.min\(NECK_MAX/.test(page)
  && /Math\.max\(-HEAD_MAX, Math\.min\(HEAD_MAX/.test(page));
ok('the motion is frame-rate independent by construction, as claimed: distance-keyed gait, per-second settle',
  /look the same at\s+any frame rate/.test(reg.conventions.rig_vocabulary.articulation)
  && /const ph = dist \* 2\.2;/.test(page)
  && /Math\.exp\(-11 \* Math\.min\(dt/.test(page));
ok('no animation clip is exported - the .glb carries the rest-pose skeleton only',
  /no animation clip is exported/
    .test(reg.conventions.rig_vocabulary.no_animation_track)
  && /retarget its own clips/
    .test(reg.conventions.rig_vocabulary.no_animation_track)
  && !/animations:/.test(page));
ok('VRM stays honestly unclaimed as a spec even though its vocabulary is adopted',
  reg.baseline.not_claimed.some((x) => x.id === 'vrm'));

/* ------------------------------------------------------------- exchange --- */
ok('both exports are declared with their trigger and file, and the page exports them',
  reg.exports.length === 2
  && reg.exports.some((e) => e.file === 'tc-avatar.glb')
  && reg.exports.some((e) => e.file === 'tc-hall-<slug>.glb')
  && /tc-avatar\.glb/.test(page) && /'tc-hall-' \+ slug \+ '\.glb'/.test(page));
ok('the import policy is learner-local with the licence duty stated, and the page says never uploaded',
  /learner-local only/.test(reg.imports.policy)
  && /never uploads anywhere/.test(reg.imports.policy)
  && /CC-BY/.test(reg.imports.policy)
  && /never uploaded/.test(page));
ok('the vendored glTF modules exist beside the controls',
  ['gltf/GLTFExporter.js', 'gltf/GLTFLoader.js', 'utils/TextureUtils.js',
   'utils/BufferGeometryUtils.js'].every((f) =>
    existsSync(new URL('../web/vendor/addons/' + f, import.meta.url))));
ok('the geographic interchange the registry claims is the one geo/ actually ships',
  existsSync(new URL('../geo/registry/network.geojson', import.meta.url))
  && existsSync(new URL('../geo/registry/campuses.geojson', import.meta.url)));

ok('the Unity bridge is declared and stays honest: the org fork named, export-ready, nothing trained claimed',
  reg.unity_bridge.repo === 'AGIFutureFoundation/ml-agents'
  && /Unity ML-Agents Toolkit/.test(reg.unity_bridge.upstream)
  && /Apache-2.0/.test(reg.unity_bridge.upstream)
  && /export-ready/.test(reg.unity_bridge.status)
  && /No\s+trained agent/.test(reg.unity_bridge.status)
  && /RECORDED/.test(reg.unity_bridge.provenance)
  && /checked|carried as recorded/.test(reg.unity_bridge.recorded_check));

/* -------------------------------------------------------------- honesty --- */
ok('the honesty line refuses the hype: files not a place, no tokens, no upload, graceful degrade',
  /file formats and honesty, not a\s+place/.test(reg.honesty.status)
  && /no\s+service, account, token or blockchain/.test(reg.honesty.status)
  && /nothing here is an NFT/.test(reg.honesty.status)
  && /degrade to a HUD line/.test(reg.honesty.status));

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`meta/test: ${n} checks passed — ${reg.baseline.standards.length} standards `
  + `claimed, ${reg.baseline.not_claimed.length} honestly not`);
