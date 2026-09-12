/**
 * Flow-pacing logic verification (app/lib/flow.ts).
 *
 * The pure decision function is the one piece of the flow panel that
 * can be held to an exact answer without a browser or a live model in
 * the loop, so that is what this checks: the flowFit arithmetic is
 * deterministic and matches hand-computed values, a voluntary check-in
 * always wins over the computed figure, the consent gate is a real
 * no-op (not just a caller convention), and - the type-level safety
 * claim in the header comment - no biometric, emotion or medical field
 * name appears anywhere in the source. It also checks the one thing
 * that differs from the sibling Helios runner's copy of this file: this
 * model has real audio commands, and the module (and its panel) must
 * document, and never exercise, why they stay out of live adaptation.
 *
 * Deliberately NOT wired into the parent repo's verify_all.sh: this
 * script imports a .ts file directly via Node's built-in TypeScript
 * type-stripping (unflagged since Node 22.6-ish), which an older Node
 * does not have. Run it with `node flow.test.mjs` from this directory
 * once you have a Node new enough to support that; on an older Node it
 * prints why it skipped and exits 0 rather than failing the world.
 */
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

let flow;
try {
  flow = await import('./app/lib/flow.ts');
} catch (e) {
  console.log('SKIP: this Node cannot import a .ts file directly '
    + '(no built-in TypeScript type-stripping) - ' + e.message);
  process.exit(0);
}
const { FLOW_CONFIG, chooseIntervention, buildScenePrompt, isVideoDisabled } = flow;

const lesson = { subject: 'Welding', concept: 'Arc gap', taskType: 'simulation', learningGoal: 'A clean bead' };
const controlsOn = { allowVideo: true, allowAdaptiveChanges: true };

/* ------------------------------------------------------------ flowFit --- */
ok('perfect performance (no errors, no hints, no stall) reads full underload',
  chooseIntervention(lesson, { correctRateRecent: 1 }, controlsOn).flowFit === -1);
ok('total failure with heavy hints and a long stall reads full overload',
  chooseIntervention(
    lesson,
    { correctRateRecent: 0, hintsUsedRecent: 10, secondsWithoutProgress: 999 },
    controlsOn,
  ).flowFit === 1);
ok('a mixed but manageable performance (50% correct, 3 hints, no stall) computes to exactly 0.00 and sits in-band',
  (() => {
    const d = chooseIntervention(
      lesson, { correctRateRecent: 0.5, hintsUsedRecent: 3 }, controlsOn);
    return d.flowFit === 0
      && d.flowFit > FLOW_CONFIG.targetMin && d.flowFit < FLOW_CONFIG.targetMax
      && !d.requiresSceneChange;
  })());

/* ------------------------------------------------- voluntary check-in --- */
ok('"need_more_support" always reads as overloaded, regardless of the numbers',
  chooseIntervention(
    lesson,
    { correctRateRecent: 1, voluntaryCheckIn: 'need_more_support' },
    controlsOn,
  ).support === true);
ok('"need_more_challenge" always reads as underloaded, regardless of the numbers',
  chooseIntervention(
    lesson,
    { correctRateRecent: 0, hintsUsedRecent: 10, voluntaryCheckIn: 'need_more_challenge' },
    controlsOn,
  ).challenge === true);
ok('"distracted" and "want_calmer" both force the minimal scene, needing a change',
  ['distracted', 'want_calmer'].every((c) => {
    const d = chooseIntervention(lesson, { correctRateRecent: 1, voluntaryCheckIn: c }, controlsOn);
    return d.sceneMode === 'minimal' && d.requiresSceneChange === true;
  }));

/* ------------------------------------------------------- the consent gate --- */
ok('adaptive changes off is a real no-op inside the pure function itself, not just a caller convention',
  (() => {
    const d = chooseIntervention(
      lesson,
      { correctRateRecent: 0, hintsUsedRecent: 10, secondsWithoutProgress: 999 },
      { allowVideo: true, allowAdaptiveChanges: false },
    );
    return d.requiresSceneChange === false && d.sceneMode === 'ambient';
  })());
ok('a "no_video" scene preference disables video regardless of the allowVideo flag',
  isVideoDisabled({ scenePreference: 'no_video' }, { allowVideo: true, allowAdaptiveChanges: true }));
ok('allowVideo:false disables video regardless of any scene preference',
  isVideoDisabled({}, { allowVideo: false, allowAdaptiveChanges: true }));

/* -------------------------------------------------------------- prompts --- */
ok('the scene prompt names the subject and concept, never the union-module honesty label',
  (() => {
    const p = buildScenePrompt({ lesson, mode: 'ambient', support: false, challenge: false });
    return p.includes('Welding') && p.includes('Arc gap') && !p.includes('AI-SYNTHESIZED');
  })());
ok('the prompt never claims to depict a real trade, tool or site - it only ever describes a backdrop',
  ['minimal', 'ambient', 'diagrammatic', 'cinematic'].every((mode) =>
    !/PPE|apprentice|training-yard/i.test(
      buildScenePrompt({ lesson, mode, support: false, challenge: false }),
    )));

/* -------------------------------------------------------------- honesty --- */
const src = readFileSync(new URL('./app/lib/flow.ts', import.meta.url), 'utf8');
const panelSrc = readFileSync(
  new URL('./app/components/FlowPanel.tsx', import.meta.url), 'utf8');
// strip // comments only (neither file uses /* */ blocks) so the module's
// own honesty prose - which names these words on purpose, to disclaim
// them - doesn't trip the check meant to catch them as actual CODE
const stripComments = (s) => s.split('\n')
  .map((line) => line.replace(/\/\/.*/, '')).join('\n');
const codeOnly = stripComments(src) + stripComments(panelSrc);
ok('no biometric, emotion-recognition or medical field name appears in the actual code (comments may disclaim them)',
  ['heart_rate', 'heartRate', 'facial', 'camera_emotion', 'cameraEmotion',
    'mental_health', 'mentalHealth', 'keystroke', 'biometric', 'webcam',
    'eye_tracking', 'eyeTracking'].every((banned) => !codeOnly.includes(banned)));
ok('the module states its own safety claim: a closed type, not a runtime denylist',
  /closed by construction/.test(src) && /LearnerSignal/.test(src));
ok('the module explains this model DOES have real audio, unlike Helios, and why FlowPanel still never uses it',
  /main_audio/.test(src) && /idle-only/.test(src) && /WORSE/.test(src));
ok('the panel never sends an audio command - not because the model lacks one (it does), but by this panel\'s own design',
  !/sendSetAudioPrompt\(/.test(codeOnly) && !/sendSetAudioEnabled\(/.test(codeOnly));

console.log(`flow.test: ${n} checks passed`);
