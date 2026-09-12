"use client";

import { useEffect, useState } from "react";
import {
  useViskoOrbisStable,
  useViskoState,
  sendSetPrompt,
  sendStart,
  type StateMessage,
} from "../lib/visko";
import { DISTRICTS, TEXT_SCENES } from "../lib/prompts";

// Setup-phase panel. Lets the user pick a union module or write their
// own prompt, and kicks off generation with `set_prompt` → `start`.
//
// The stock template removed curated T2V presets here "per launch
// direction" (its own demo leads image-anchored). This app's presets
// serve a different job - offering SmartCiti.X's own 111 real union
// modules as ready prompts - so they stay, rendered as a
// district-grouped <select> (111 items reads badly as a button grid)
// rather than reintroduced as the stock four-button layout.
//
// Unlike Lingbot, Visko Orbis Stable can start from TEXT ALONE
// (pure text-to-video). An image (set via <ImageStarter>) is optional
// conditioning — if present it anchors the first chunk; if absent the
// model invents the opening frame from the prompt.
//
// Renders null once generation has started — the surface switches to
// <NowPlaying> + <EvolveScene> (live steering) from there.
export function PromptComposer() {
  const s = useViskoOrbisStable();
  const status = s.status;
  const [text, setText] = useState("");
  const [moduleId, setModuleId] = useState("");
  const [snapshot, setSnapshot] = useState<StateMessage | null>(null);

  useViskoState((msg: StateMessage) => setSnapshot(msg));

  useEffect(() => {
    if (status !== "ready") setSnapshot(null);
  }, [status]);

  // Hide once we're generating — but keep rendering (in disabled form)
  // when the user is just not connected, so the page doesn't go blank
  // after disconnect.
  if (status === "ready" && snapshot?.started) return null;

  const ready = status === "ready";
  const hasImage = snapshot?.has_image === true;
  const selected = TEXT_SCENES.find((sc) => sc.id === moduleId);

  async function send(prompt: string) {
    if (!ready || !prompt.trim()) return;
    await sendSetPrompt(s, prompt.trim());
    await sendStart(s);
  }

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3">
      <label className="text-[10px] uppercase tracking-wider text-zinc-500">
        A union module ({TEXT_SCENES.length})
      </label>

      <select
        value={moduleId}
        disabled={!ready}
        onChange={(e) => setModuleId(e.target.value)}
        className="mt-2 w-full rounded-md border border-zinc-800 bg-zinc-950 p-2 text-sm text-zinc-100 focus:border-brand focus:outline-none disabled:opacity-40"
      >
        <option value="">Pick a trade to practice…</option>
        {DISTRICTS.map((d) => (
          <optgroup key={d} label={d}>
            {TEXT_SCENES.filter((sc) => sc.district === d).map((sc) => (
              <option key={sc.id} value={sc.id}>
                {sc.label}
              </option>
            ))}
          </optgroup>
        ))}
      </select>

      {selected && (
        <p
          className="mt-2 line-clamp-3 text-[11px] leading-snug text-zinc-500"
          title={selected.initial.text}
        >
          {selected.initial.text}
        </p>
      )}

      <button
        disabled={!ready || !selected}
        onClick={() => selected && send(selected.initial.text)}
        className="mt-2 w-full rounded-md bg-brand px-3 py-1.5 text-sm font-medium text-brand-fg hover:opacity-90 disabled:opacity-40"
      >
        {hasImage ? "Start from your image" : "Start generating"}
      </button>

      <label className="mt-4 block text-[10px] uppercase tracking-wider text-zinc-500">
        Or write your own
      </label>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Describe one continuous scene — setting, light, motion, camera. A single unbroken take, not a montage."
        disabled={!ready}
        rows={3}
        className="mt-2 w-full resize-none rounded-md border border-zinc-800 bg-zinc-950 p-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-brand focus:outline-none disabled:opacity-40"
      />

      <button
        disabled={!ready || !text.trim()}
        onClick={async () => {
          await send(text);
          setText("");
        }}
        className="mt-2 w-full rounded-md bg-brand px-3 py-1.5 text-sm font-medium text-brand-fg hover:opacity-90 disabled:opacity-40"
      >
        {hasImage ? "Start from your image" : "Start generating"}
      </button>
    </div>
  );
}
