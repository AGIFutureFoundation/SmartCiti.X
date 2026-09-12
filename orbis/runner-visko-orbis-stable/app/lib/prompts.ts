// The scene library for SmartCiti.X : Trade Craft Academy's Visko Orbis
// Stable runner.
//
// Every scene here is GENERATED, not authored in this file: it comes
// straight from `orbis/build.py` in the parent SmartCiti.X repo, which
// writes `modules.generated.json` from the SAME union registry every
// other fact in that project comes from (111 halls, 8 districts) through
// one deterministic template - the same generated file the Helios
// runner (`orbis/runner-helios/`) imports too. Regenerate it by running
// `python3 orbis/build.py` from the repo root; never hand-edit
// `modules.generated.json` directly, and never hand-author a "richer"
// prompt here - a fabricated cinematic description would be a fact this
// template's own honesty checks don't cover.
//
// AUDIO stays absent from every generated prompt, matching this
// template's own measured guidance (see app/lib/visko.ts): feeding a
// scene description into `set_audio_prompt` measures WORSE than leaving
// audio unset, so nothing here sets one by default.
//
// Every module is text-only (no reference image - this repo ships none)
// and carries no `evolutions`: a real continuation prompt would have to
// invent a second beat this project has no record of, so none is
// offered. The always-present free-text "steer the scene live" box in
// `EvolveScene.tsx` covers live morphing regardless.
import modules from "./modules.generated.json";

export interface Prompt {
  /** Short headline used as the button label in the UI. */
  title: string;
  /** Full text sent to the model. */
  text: string;
}

export interface Scene {
  id: string;
  label: string;
  district: string;
  initial: Prompt;
  evolutions: ReadonlyArray<Prompt>;
  /** Reference image URL. Present only on image-backed scenes - none are. */
  imageUrl?: string;
}

interface GeneratedModule {
  id: string;
  label: string;
  district: string;
  text: string;
}

export const SCENES: ReadonlyArray<Scene> = (
  modules as GeneratedModule[]
).map((m) => ({
  id: m.id,
  label: m.label,
  district: m.district,
  initial: { title: m.label, text: m.text },
  evolutions: [],
}));

/** Text-only scenes - the district-grouped picker in PromptComposer reads these. */
export const TEXT_SCENES: ReadonlyArray<Scene> = SCENES.filter(
  (s) => !s.imageUrl,
);

/** Image-backed scenes - used as example cards in setup. Always empty here. */
export const IMAGE_SCENES: ReadonlyArray<Scene & { imageUrl: string }> =
  SCENES.filter((s): s is Scene & { imageUrl: string } => !!s.imageUrl);

/** Every district name, in the order modules.generated.json lists them. */
export const DISTRICTS: ReadonlyArray<string> = [
  ...new Set(SCENES.map((s) => s.district)),
];

/**
 * Look up which scene a given prompt belongs to. Returns the matching
 * scene if `prompt` is either the scene's `initial.text` or one of
 * its `evolutions[].text`; otherwise null (the user has typed or
 * morphed to a prompt we don't have a curated continuation for).
 */
export function findSceneForPrompt(
  prompt: string | null | undefined,
): Scene | null {
  if (!prompt) return null;
  return (
    SCENES.find(
      (s) =>
        s.initial.text === prompt ||
        s.evolutions.some((e) => e.text === prompt),
    ) ?? null
  );
}
