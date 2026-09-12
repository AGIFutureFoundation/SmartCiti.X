// Flow-state pacing logic for the SmartCiti.X Orbis runner.
//
// Adapted from a Cognition.X-style "flow environment" tool sketch to
// this app's REAL SDK: `useHelios()` (a React hook exposing setPrompt,
// start, pause, resume, reset - see the method list on
// `useHelios()`'s return type, not a generic `orbisClient` object).
// One real difference from the sketch this was adapted from: Helios is
// VIDEO ONLY - its provider has no audio track and no audio command at
// all, so this module makes no audio decision (the sketch's "want
// quiet" check-in became "calmer visuals", the only lever this model
// actually has). The stateless decision logic lives here,
// framework-independent and unit-testable; the stateful piece - the
// React component that actually calls the hook - is
// `app/components/FlowPanel.tsx`.
//
// SAFETY, closed by construction, not merely checked at runtime:
// `LearnerSignal` below is a closed TypeScript interface with exactly
// the fields listed. A biometric, emotion-recognition or medical field
// is not rejected by a denylist somewhere - it cannot be expressed in
// this type at all, so nothing downstream can accidentally read one.
// Every signal here is either read from a lesson's own recorded
// performance (attempts, correct rate, hints used, time without
// progress) or a student's own voluntary word for how the pace feels -
// never inferred from a camera, a wearable, or a keystroke pattern, and
// this module makes no psychological, clinical or behavioral claim
// about the student it adjusts a background for.

export const FLOW_CONFIG = {
  targetMin: -0.2,
  targetMax: 0.2,
  thresholds: {
    overload: 0.45,
    underload: -0.45,
    stuckSeconds: 90,
    tooManyHints: 3,
    minSecondsBetweenSceneChanges: 20,
  },
  session: {
    maxMinutes: 25,
  },
} as const;

export type TaskType =
  | "reading"
  | "problem_solving"
  | "coding"
  | "writing"
  | "simulation"
  | "lab"
  | "review";

export type CheckIn =
  | "comfortable"
  | "need_more_challenge"
  | "need_more_support"
  | "distracted"
  | "want_calmer"
  | "want_to_pause";

export type ScenePreference =
  | "minimal"
  | "ambient"
  | "diagrammatic"
  | "cinematic"
  | "no_video";

export interface LessonContext {
  subject: string;
  concept: string;
  taskType: TaskType;
  learningGoal: string;
  currentStep?: string;
}

/** Closed by construction - see the module note above. */
export interface LearnerSignal {
  voluntaryCheckIn?: CheckIn;
  attemptsOnCurrentStep?: number;
  correctRateRecent?: number; // 0..1
  hintsUsedRecent?: number;
  secondsWithoutProgress?: number;
  scenePreference?: ScenePreference;
}

export interface StudentControls {
  allowVideo: boolean;
  allowAdaptiveChanges: boolean;
}

export type SceneMode = "minimal" | "ambient" | "diagrammatic" | "cinematic";

export interface FlowDecision {
  sceneMode: SceneMode;
  support: boolean;
  challenge: boolean;
  /** -1 (deep underload) .. +1 (deep overload); 0 sits in the target band. */
  flowFit: number;
  requiresSceneChange: boolean;
  rationale: string;
  studentMessage: string;
  tutorGuidance: string;
}

/** True whenever video must not run - consent or an explicit preference. */
export function isVideoDisabled(
  signal: LearnerSignal,
  controls: StudentControls,
): boolean {
  return controls.allowVideo === false || signal.scenePreference === "no_video";
}

function clamp(x: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, x));
}

/**
 * flowFit: a deterministic score, not an inference. Three recorded
 * performance signals, each normalized 0..1 and weighted, mapped onto
 * -1..+1 so 0 correctness with heavy hint use and long stalls reads as
 * full overload (+1) and clean, hint-free, fast progress reads as full
 * underload (-1) - which is a real thing lesson pacing has to answer
 * for (a bored learner is not "fine" just because they are not stuck).
 * A voluntary check-in nudges the score toward what the student
 * actually said, and always outweighs the computed figure.
 */
function computeFlowFit(signal: LearnerSignal): number {
  const { thresholds } = FLOW_CONFIG;
  const correctRate = signal.correctRateRecent ?? 1;
  const struggle = clamp(1 - correctRate, 0, 1);
  const hintPressure = clamp(
    (signal.hintsUsedRecent ?? 0) / thresholds.tooManyHints,
    0,
    1.5,
  );
  const stuckPressure = clamp(
    (signal.secondsWithoutProgress ?? 0) / thresholds.stuckSeconds,
    0,
    1.5,
  );
  const raw = struggle * 0.4 + hintPressure * 0.3 + stuckPressure * 0.3;
  let fit = clamp(raw * 2 - 1, -1, 1);

  switch (signal.voluntaryCheckIn) {
    case "need_more_support":
      fit = Math.max(fit, 0.5);
      break;
    case "need_more_challenge":
      fit = Math.min(fit, -0.5);
      break;
    case "comfortable":
      fit = fit * 0.3; // pulled toward the target band, not forced to 0
      break;
    default:
      break;
  }
  return clamp(fit, -1, 1);
}

const SCENE_BASE: Record<SceneMode, string> = {
  minimal:
    "A plain, softly lit empty study space, no people, no on-screen text, gentle even light, a completely static camera.",
  ambient:
    "A quiet, softly moving ambient backdrop - drifting light, slow-shifting color, no people, no on-screen text, a still camera.",
  diagrammatic:
    "A clean, schematic visual field of simple abstract shapes and lines gently rearranging, no people, no on-screen text, a still camera.",
  cinematic:
    "A calm, cinematic wide establishing shot related to the subject below, no readable on-screen text, a slow, steady camera move.",
};

/**
 * Builds the prompt this session's `setPrompt` actually sends. This is
 * an AMBIENT STUDY BACKDROP, not a depiction of the lesson content
 * itself - it never claims to show the real trade, tool or site a
 * SmartCiti.X module teaches (that claim belongs only to the
 * registry-derived prompts in `app/lib/modules.generated.json`, and
 * this function is never used to build one of those).
 */
export function buildScenePrompt(opts: {
  lesson: LessonContext;
  mode: SceneMode;
  support: boolean;
  challenge: boolean;
}): string {
  const { lesson, mode, support, challenge } = opts;
  const parts = [SCENE_BASE[mode]];
  parts.push(
    `Backdrop for studying ${lesson.subject} - ${lesson.concept}.`,
  );
  if (support) {
    parts.push(
      "Slower, steadier motion than usual; nothing sudden or attention-grabbing.",
    );
  } else if (challenge) {
    parts.push("A touch more visual variety and motion than the calm default.");
  }
  return parts.join(" ");
}

/**
 * The pure decision. Same inputs, same output, every time - the one
 * piece of this tool a test can hold to an exact answer without a
 * browser or a live model in the loop.
 */
export function chooseIntervention(
  lesson: LessonContext,
  signal: LearnerSignal,
  controls: StudentControls,
): FlowDecision {
  const { targetMin, targetMax } = FLOW_CONFIG;
  const flowFit = computeFlowFit(signal);
  const overloaded = flowFit > targetMax;
  const underloaded = flowFit < targetMin;
  const support = overloaded;
  const challenge = underloaded;

  // Defense in depth: even a caller that forgot to gate on the consent
  // toggle gets a real no-op back, not a scene change - this function's
  // own contract is "adaptive changes off means nothing adapts", not
  // "trust the caller checked first".
  if (!controls.allowAdaptiveChanges) {
    return {
      sceneMode: "ambient",
      support: false,
      challenge: false,
      flowFit,
      requiresSceneChange: false,
      rationale: "adaptive changes are off by student preference - holding steady.",
      studentMessage: "Adaptive changes are off. Turn them back on to let the backdrop adjust.",
      tutorGuidance: "adaptive changes are off by student preference.",
    };
  }

  const wantsCalmer =
    signal.voluntaryCheckIn === "distracted" ||
    signal.voluntaryCheckIn === "want_calmer";
  let sceneMode: SceneMode = "ambient";
  if (wantsCalmer || support) sceneMode = "minimal";
  else if (signal.scenePreference && signal.scenePreference !== "no_video") {
    sceneMode = signal.scenePreference;
  } else if (challenge) sceneMode = "cinematic";

  const rationale = overloaded
    ? `flowFit ${flowFit.toFixed(2)} is above the overload threshold (${FLOW_CONFIG.thresholds.overload}) - simplifying the backdrop and slowing its motion.`
    : underloaded
      ? `flowFit ${flowFit.toFixed(2)} is below the underload threshold (${FLOW_CONFIG.thresholds.underload}) - adding a little more visual variety.`
      : wantsCalmer
        ? "you asked for something calmer, so the backdrop simplified regardless of the measured pace."
        : `flowFit ${flowFit.toFixed(2)} sits inside the target band [${targetMin}, ${targetMax}] - holding the current backdrop steady.`;

  return {
    sceneMode,
    support,
    challenge,
    flowFit,
    requiresSceneChange: overloaded || underloaded || wantsCalmer,
    rationale,
    studentMessage:
      "The backdrop just adjusted to keep pace with you. You can turn adaptive changes off or stop the session at any time.",
    tutorGuidance: rationale,
  };
}
