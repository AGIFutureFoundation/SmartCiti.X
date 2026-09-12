"use client";

import { useEffect, useRef, useState } from "react";
import {
  useHelios,
  useHeliosState,
  type HeliosStateMessage,
} from "@reactor-models/helios";
import {
  FLOW_CONFIG,
  buildScenePrompt,
  chooseIntervention,
  isVideoDisabled,
  type CheckIn,
  type FlowDecision,
  type LearnerSignal,
  type LessonContext,
  type TaskType,
} from "../lib/flow";

// Helios is video only - no audio track, no audio command (see the
// header note in ../lib/flow.ts) - so this panel only ever calls
// setPrompt. Nothing here claims to mute or quiet a sound this model
// never generates.

// Optional, student-controlled pacing panel. Once a session is running
// (started via <PromptComposer />), this lets whoever is watching -
// the student themselves, or a teacher sitting with them - log a
// voluntary check-in and real lesson-performance numbers, and asks the
// backdrop to adapt: a calmer, simpler scene under load, a touch more
// motion when the pace is clearly too easy. It changes the ambient
// backdrop only - never the union-module prompt itself, never anything
// framed as a claim about the student.
//
// SAFETY, enforced here at the UI boundary too (see app/lib/flow.ts for
// why the underlying type already makes this the only path):
//   - Every field is either the lesson's own recorded performance or
//     the student's own voluntary word - nothing inferred from a
//     camera, a wearable, or typing rhythm, and none is offered here.
//   - Adaptive changes default ON but are one toggle from OFF, and OFF
//     makes Adapt a no-op - never disabled by hiding the toggle.
//   - Every adaptation is logged, in-memory, for this session only -
//     never written to localStorage, never sent anywhere, and cleared
//     on refresh. This is an audit trail, not a behavioral profile.
export function FlowPanel() {
  const { status, setPrompt } = useHelios();
  const [snapshot, setSnapshot] = useState<HeliosStateMessage | null>(null);
  useHeliosState((msg) => setSnapshot(msg));
  useEffect(() => {
    if (status !== "ready") setSnapshot(null);
  }, [status]);

  const [adaptiveOn, setAdaptiveOn] = useState(true);
  const [subject, setSubject] = useState("");
  const [concept, setConcept] = useState("");
  const [taskType, setTaskType] = useState<TaskType>("simulation");
  const [learningGoal, setLearningGoal] = useState("");
  const [checkIn, setCheckIn] = useState<CheckIn | "">("");
  const [attempts, setAttempts] = useState("");
  const [correctRate, setCorrectRate] = useState("");
  const [hintsUsed, setHintsUsed] = useState("");
  const [stuckSeconds, setStuckSeconds] = useState("");

  const [log, setLog] = useState<
    { at: number; decision: FlowDecision }[]
  >([]);
  const lastChangeAt = useRef(0);
  const [, forceTick] = useState(0);

  // Re-render once a second while a cooldown is active, purely so the
  // "wait Ns" label counts down instead of sitting stale.
  useEffect(() => {
    const id = setInterval(() => forceTick((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, []);

  if (status !== "ready" || !snapshot?.started) return null;

  const cooldownLeft = Math.max(
    0,
    FLOW_CONFIG.thresholds.minSecondsBetweenSceneChanges -
      (Date.now() - lastChangeAt.current) / 1000,
  );

  async function adapt() {
    if (!adaptiveOn || cooldownLeft > 0) return;

    const lesson: LessonContext = {
      subject: subject.trim() || "this session",
      concept: concept.trim() || "the current step",
      taskType,
      learningGoal: learningGoal.trim() || "steady, comfortable progress",
    };
    const signal: LearnerSignal = {
      voluntaryCheckIn: checkIn || undefined,
      attemptsOnCurrentStep: attempts ? Number(attempts) : undefined,
      correctRateRecent: correctRate ? Number(correctRate) / 100 : undefined,
      hintsUsedRecent: hintsUsed ? Number(hintsUsed) : undefined,
      secondsWithoutProgress: stuckSeconds ? Number(stuckSeconds) : undefined,
    };
    // Video consent lives on the module-selection screen (this panel
    // only ever touches the ambient backdrop of an already-running,
    // already-consented session) - allowVideo is always true here.
    const controls = { allowVideo: true, allowAdaptiveChanges: adaptiveOn };
    if (isVideoDisabled(signal, controls)) return;

    const decision = chooseIntervention(lesson, signal, controls);
    if (!decision.requiresSceneChange) {
      setLog((l) => [{ at: Date.now(), decision }, ...l].slice(0, 20));
      return;
    }

    const prompt = buildScenePrompt({
      lesson,
      mode: decision.sceneMode,
      support: decision.support,
      challenge: decision.challenge,
    });
    await setPrompt({ prompt });

    lastChangeAt.current = Date.now();
    setLog((l) => [{ at: Date.now(), decision }, ...l].slice(0, 20));
  }

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3">
      <div className="flex items-center justify-between">
        <label className="text-[10px] uppercase tracking-wider text-zinc-500">
          Pacing check-in
        </label>
        <label className="flex cursor-pointer items-center gap-1.5 text-[11px] text-zinc-500">
          <input
            type="checkbox"
            checked={adaptiveOn}
            onChange={(e) => setAdaptiveOn(e.target.checked)}
          />
          adaptive backdrop
        </label>
      </div>

      <p className="mt-1 text-[11px] leading-snug text-zinc-500">
        Optional. Adjusts only the ambient backdrop's calm/motion level -
        never the module content, never a claim about you.
      </p>

      <div className="mt-2 grid grid-cols-2 gap-1.5">
        <input
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          placeholder="Subject"
          disabled={!adaptiveOn}
          className="rounded-md border border-zinc-800 bg-zinc-950 p-1.5 text-xs text-zinc-100 placeholder:text-zinc-600 disabled:opacity-40"
        />
        <input
          value={concept}
          onChange={(e) => setConcept(e.target.value)}
          placeholder="Concept / step"
          disabled={!adaptiveOn}
          className="rounded-md border border-zinc-800 bg-zinc-950 p-1.5 text-xs text-zinc-100 placeholder:text-zinc-600 disabled:opacity-40"
        />
      </div>

      <select
        value={checkIn}
        disabled={!adaptiveOn}
        onChange={(e) => setCheckIn(e.target.value as CheckIn)}
        className="mt-1.5 w-full rounded-md border border-zinc-800 bg-zinc-950 p-1.5 text-xs text-zinc-100 disabled:opacity-40"
      >
        <option value="">How's the pace? (optional, your own word)</option>
        <option value="comfortable">Comfortable</option>
        <option value="need_more_challenge">Too easy - want more challenge</option>
        <option value="need_more_support">Too much - want more support</option>
        <option value="distracted">Distracted</option>
        <option value="want_calmer">Want something calmer</option>
      </select>

      <div className="mt-1.5 grid grid-cols-3 gap-1.5">
        <input
          value={attempts}
          onChange={(e) => setAttempts(e.target.value)}
          placeholder="Attempts"
          type="number"
          min={0}
          disabled={!adaptiveOn}
          className="rounded-md border border-zinc-800 bg-zinc-950 p-1.5 text-xs text-zinc-100 placeholder:text-zinc-600 disabled:opacity-40"
        />
        <input
          value={correctRate}
          onChange={(e) => setCorrectRate(e.target.value)}
          placeholder="Correct %"
          type="number"
          min={0}
          max={100}
          disabled={!adaptiveOn}
          className="rounded-md border border-zinc-800 bg-zinc-950 p-1.5 text-xs text-zinc-100 placeholder:text-zinc-600 disabled:opacity-40"
        />
        <input
          value={hintsUsed}
          onChange={(e) => setHintsUsed(e.target.value)}
          placeholder="Hints used"
          type="number"
          min={0}
          disabled={!adaptiveOn}
          className="rounded-md border border-zinc-800 bg-zinc-950 p-1.5 text-xs text-zinc-100 placeholder:text-zinc-600 disabled:opacity-40"
        />
      </div>

      <button
        disabled={!adaptiveOn || cooldownLeft > 0}
        onClick={adapt}
        className="mt-2 w-full rounded-md bg-brand px-3 py-1.5 text-sm font-medium text-brand-fg hover:opacity-90 disabled:opacity-40"
      >
        {cooldownLeft > 0 ? `Wait ${Math.ceil(cooldownLeft)}s` : "Check in"}
      </button>

      {log.length > 0 && (
        <div className="mt-3 border-t border-zinc-800 pt-2">
          <span className="text-[10px] uppercase tracking-wider text-zinc-500">
            Session log (this tab only, never saved)
          </span>
          <ul className="mt-1 space-y-1">
            {log.map((entry) => (
              <li key={entry.at} className="text-[11px] leading-snug text-zinc-500">
                <span className="text-zinc-600">
                  {new Date(entry.at).toLocaleTimeString()} ·{" "}
                </span>
                {entry.decision.rationale}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
