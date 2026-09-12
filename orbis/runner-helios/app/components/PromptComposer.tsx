"use client";

import { useEffect, useState } from "react";
import {
  useHelios,
  useHeliosState,
  type HeliosStateMessage,
} from "@reactor-models/helios";
import { DISTRICTS, TEXT_SCENES } from "../lib/prompts";

// Setup-phase panel. Lets the user pick a preset or write their own
// prompt and kicks off generation with `set_prompt` → `start`.
//
// TEXT_SCENES here is all 111 SmartCiti.X union modules, not a handful
// of curated demo scenes - so presets render as one <select> grouped by
// district (the union registry's own grouping) rather than the original
// template's button grid, which only reads well at a handful of items.
//
// Renders null once generation has started — the user-facing surface
// switches to <NowPlaying> from there. Mid-stream prompt switching
// (a Helios capability) is intentionally NOT exposed in this tutorial
// to keep the lesson tight.
export function PromptComposer() {
  const { status, setPrompt, start } = useHelios();
  const [text, setText] = useState("");
  const [moduleId, setModuleId] = useState("");
  const [snapshot, setSnapshot] = useState<HeliosStateMessage | null>(null);

  useHeliosState((msg) => setSnapshot(msg));

  useEffect(() => {
    if (status !== "ready") setSnapshot(null);
  }, [status]);

  // Hide once we're generating — but keep rendering (in disabled form)
  // when the user is just not connected, so the page doesn't go blank
  // after disconnect.
  if (status === "ready" && snapshot?.started) return null;

  const ready = status === "ready";

  async function send(prompt: string) {
    if (!ready || !prompt.trim()) return;
    await setPrompt({ prompt: prompt.trim() });
    await start();
  }

  const selected = TEXT_SCENES.find((s) => s.id === moduleId);

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
            {TEXT_SCENES.filter((s) => s.district === d).map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
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
        Start generating
      </button>

      <label className="mt-4 block text-[10px] uppercase tracking-wider text-zinc-500">
        Or write your own
      </label>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Describe the scene you want to generate…"
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
        Start generating
      </button>
    </div>
  );
}
