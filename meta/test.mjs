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
  && reg.conventions.avatar_rig.length === 5
  && /tc-hall-<slug>/.test(reg.conventions.scene_naming));
ok('every declared rig node is actually named in the page source',
  reg.conventions.avatar_rig.every((node) => page.includes(`'${node}'`)));
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
ok('the rig names exactly the VRM bones it really has, and says which it does not',
  reg.conventions.rig_vocabulary.standard.includes('VRM')
  && JSON.stringify(reg.conventions.rig_vocabulary.exposed)
    === JSON.stringify(['head', 'leftUpperArm', 'rightUpperArm'])
  && reg.conventions.rig_vocabulary.not_exposed.includes('hips')
  && /baked\s+geometry/.test(reg.conventions.rig_vocabulary.why)
  && reg.conventions.rig_vocabulary.exposed.every((b) =>
      page.includes(`name = '${b}'`))
  && reg.conventions.rig_vocabulary.not_exposed.every((b) =>
      !page.includes(`name = '${b}'`)));
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
