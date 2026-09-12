# SmartCiti.X Orbis runner (Visko Orbis Stable)

A real, runnable companion to **SmartCiti.X : Trade Craft Academy** — not
a demo, and not part of that project's static site. This is a genuine
Next.js + TypeScript frontend for **Visko Orbis Stable**, Reactor's
real-time, steerable video model with a real audio track, scaffolded
from Reactor's own
[`create-reactor-app`](https://github.com/reactor-team/create-reactor-app)
template (Apache-2.0 — see `LICENSE` and `NOTICE` in this directory),
customized in the same places as its sibling
[`../runner-helios`](../runner-helios) runner: its scene library, and an
added, optional pacing-adaptation panel.

## What's actually different from the stock template

Everything else is the unmodified Visko Orbis Stable reference frontend.
The real customizations:

- **`app/lib/prompts.ts`** no longer ships the four illustrative
  reference-image presets (drums, a fisherman, a greenhouse, underwater —
  their image files are deleted, since SmartCiti.X ships no reference
  photos). It imports **`app/lib/modules.generated.json`** — a
  machine-generated file written by `orbis/build.py` in the parent
  SmartCiti.X repo, straight from that project's own union registry (111
  trade halls across 8 districts) — the same generated file the Helios
  runner imports too. Regenerate it with `python3 orbis/build.py` from
  the SmartCiti.X repo root; never hand-edit `modules.generated.json`.
- **`app/components/PromptComposer.tsx`** reintroduces a district-grouped
  `<select>` of those 111 presets. The stock template removed curated
  T2V presets entirely "per launch direction" (its own demo now leads
  image-anchored, via `ImageStarter`) — this app diverges on purpose,
  because the presets serve a different job here: offering SmartCiti.X's
  own union modules as ready prompts, not a general-purpose gallery. The
  free-text box and the `hasImage`-aware button label are unchanged from
  the template.
- **`app/components/EvolveScene.tsx`** is untouched. Unlike Helios's
  template, this one already keeps its "steer the scene live" text box
  visible even when a scene carries no curated evolutions (which every
  generated module here does not — see below) — an empty evolutions grid
  just renders an empty, harmless `<div>`, not a broken-looking section.
- Every generated module carries `evolutions: []`, same reasoning as the
  Helios runner: a real continuation prompt would mean inventing a second
  beat this project has no record of, and SmartCiti.X's whole discipline
  is never stating a fact a source doesn't support.
- **`app/components/FlowPanel.tsx`** (new) — an optional, off-by-one-toggle
  pacing panel that appears once a session is running, mirroring the
  Helios runner's panel of the same name. Whoever is watching (the
  student, or a teacher sitting with them) can log a voluntary check-in
  ("too easy", "too much", "distracted") plus real lesson-performance
  numbers (attempts, correct rate, hints used, time without progress),
  and the panel asks the backdrop — never the module content, never
  audio — to adapt: calmer and simpler under load, a touch more visual
  variety when the pace is clearly too easy. The decision logic lives in
  **`app/lib/flow.ts`**, a pure, dependency-free module ported from the
  Helios runner's, with its own test (`flow.test.mjs`, run it with
  `node flow.test.mjs`). See its header comment for the full safety
  design, and for why it deliberately does *not* touch this model's real
  audio commands even though they exist (short version: `set_audio_enabled`
  only arms the *next* `start`, and `set_audio_prompt` is measured to make
  the audio worse — both already excluded from `AudioPanel.tsx` for the
  same reason, this panel just holds to the same rule).
- **`app/components/Header.tsx`** carries the same SmartCiti.X branding
  and AI-SYNTHESIZED subtitle as the Helios runner's, for consistency
  between the two.

Every prompt this app offers by default is therefore short and factual
("A Structural apprentice practicing Ironworkers: Structural steel, rebar,
rigging and connecting. Training-yard setting…"), not the longer
scene-setting paragraph this model's own prompt guide recommends for the
smoothest mid-stream morphs. That's a deliberate trade-off, not an
oversight — see the honesty note below. Nothing stops you from writing a
richer prompt yourself in the free-text box.

**Audio stays exactly as the stock template ships it** — `AudioPanel.tsx`
is unmodified: a real `set_audio_enabled` toggle (applies at the next
`start`), no audio-prompt box (the template's own measured guidance is
that filling one in makes the audio *worse* than leaving it unset). This
app doesn't add a richer audio story than the template already has one
for.

## What this is not

- **Not part of the static site.** `web/trade_craft_3d.html` — the actual
  learner-facing SmartCiti.X page — never loads this app, never calls
  Reactor, and never holds a key. This is a separate tool you run
  yourself.
- **Not run by SmartCiti.X's own build.** `verify_all.sh` and
  `orbis/build.py` never install this app's dependencies, never start it,
  and never request a `REACTOR_API_KEY`. The parent build only keeps
  `modules.generated.json` in sync with the union registry.
- **A generated clip is AI-SYNTHESIZED synthetic video, not footage of any real trade, worker or site.**
  It is a separate stream from SmartCiti.X's real, schematic
  training-episode log (`training/registry/training.json`) — which
  records an actual learner's actual interactions and claims nothing
  synthetic.

## Quick start

You'll need your own Reactor API key — generate one at
[reactor.inc/account/api-keys](https://www.reactor.inc/account/api-keys)
(it starts with `rk_`). **Never paste a real key into a chat, an issue, a
commit message, or any file this repo tracks** — `.env` and `.env.local`
are already in `.gitignore`, and `orbis/build.py` fails the build if
either is ever checked in.

```bash
cd orbis/runner-visko-orbis-stable
cp .env.example .env.local
# edit .env.local yourself: REACTOR_API_KEY=rk_...
pnpm install
pnpm dev
```

Open the URL the dev server prints, click **Connect**, pick a trade from
the dropdown (or write your own prompt), and watch it generate.

## Code tour

Unchanged from the stock template except where noted above. See
[`github.com/reactor-team/create-reactor-app`](https://github.com/reactor-team/create-reactor-app)
for the upstream project this was scaffolded from.

| File | What's in it |
| --- | --- |
| `app/lib/modules.generated.json` | **Generated by `orbis/build.py`.** The 111-module scene source, shared with the Helios runner. Never hand-edit. |
| `app/lib/prompts.ts` | Maps the generated modules into the `Scene[]` shape every other component reads. |
| `app/components/PromptComposer.tsx` | Setup phase. District-grouped module picker + free-text input → `setPrompt` + `start`. |
| `app/components/ImageStarter.tsx` | Setup phase. Unmodified — image upload → `setImage` (curated image cards are empty here; no reference photos shipped). |
| `app/components/EvolveScene.tsx` | Live phase. Unmodified — always shows the live free-text steering box; no evolutions authored for any generated module. |
| `app/components/SessionOptions.tsx`, `AudioPanel.tsx` | Setup phase. Unmodified — resolution/seed/audio toggle, all idle-only knobs armed at the next `start`. |
| `app/lib/flow.ts` | Pure pacing-decision logic for `FlowPanel` — config, the flowFit formula, prompt building. No SDK import; test it with `node flow.test.mjs`. |
| `app/components/FlowPanel.tsx` | Live phase. Optional pacing check-in → calls `setPrompt` on the ambient backdrop only. |
| `app/api/reactor/token/route.ts` | Mints a session-scoped JWT pinned to `reactor/visko-orbis-stable`, server-side only. |
| everything else | Unmodified from `create-reactor-app --model=visko-orbis-stable`. |

## Licence

Apache-2.0, inherited from `create-reactor-app` (Reactor Technologies,
Inc.) — see `LICENSE` and `NOTICE`. `app/lib/modules.generated.json` is
generated content from SmartCiti.X's own union registry, licensed the
same as the parent repo.
