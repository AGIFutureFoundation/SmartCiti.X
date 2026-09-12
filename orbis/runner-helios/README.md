# SmartCiti.X Orbis runner (Helios)

A real, runnable companion to **SmartCiti.X : Trade Craft Academy** — not
a demo, and not part of that project's static site. This is a genuine
Next.js + TypeScript frontend for **Helios**, Reactor's real-time
prompt-steerable video model, scaffolded from Reactor's own
[`create-reactor-app`](https://github.com/reactor-team/create-reactor-app)
template (Apache-2.0 — see `LICENSE` and `NOTICE` in this directory),
customized in two places: its scene library, and an added, optional
pacing-adaptation panel.

## What's actually different from the stock template

Everything else is the unmodified Helios reference frontend. The real
customizations:

- **`app/lib/prompts.ts`** no longer hand-authors four illustrative scenes
  (a lion, a man in the rain, a flower, a birthday party). It imports
  **`app/lib/modules.generated.json`** — a machine-generated file written
  by `orbis/build.py` in the parent SmartCiti.X repo, straight from that
  project's own union registry (111 trade halls across 8 districts). Every
  preset in this app's "Try a prompt" dropdown is one of those 111 real
  union modules — the same trades, names and focus lines the static site
  itself teaches, run through one deterministic template. Regenerate it
  with `python3 orbis/build.py` from the SmartCiti.X repo root; never
  hand-edit `modules.generated.json`.
- **`app/components/PromptComposer.tsx`** renders those 111 presets as a
  district-grouped `<select>` instead of the stock template's four-button
  grid, which only reads well at a handful of items.
- **`app/components/EvolveScene.tsx`** hides itself when a scene has no
  evolutions — every generated module has `evolutions: []`, because a
  real continuation prompt would mean inventing a second beat this
  project has no record of, and SmartCiti.X's whole discipline is never
  stating a fact a source doesn't support.
- The curated example-image cards are empty (SmartCiti.X ships no
  reference photos, only procedurally generated scenes) — uploading your
  own image still works exactly as the stock template does.
- **`app/components/FlowPanel.tsx`** (new) — an optional, off-by-one-toggle
  pacing panel that appears once a session is running. Whoever is
  watching (the student, or a teacher sitting with them) can log a
  voluntary check-in ("too easy", "too much", "distracted") plus real
  lesson-performance numbers (attempts, correct rate, hints used, time
  without progress), and the panel asks the backdrop — never the
  module content — to adapt: calmer and simpler under load, a touch
  more visual variety when the pace is clearly too easy. The decision
  logic lives in **`app/lib/flow.ts`**, a pure, dependency-free module
  with its own test (`flow.test.mjs`, run it with
  `node flow.test.mjs` once you have a Node new enough for built-in
  TypeScript support). See its header comment for the full safety
  design: no biometric, emotion-recognition or medical signal can even
  be expressed in its types, every adaptation is logged in that tab
  only and never saved, and the toggle that turns it off is checked
  inside the pure decision function itself, not just by whichever
  component happens to call it.

Every prompt this app offers by default is therefore short and factual
("A Structural apprentice practicing Ironworkers: Structural steel, rebar,
rigging and connecting. Training-yard setting…"), not the long
scene-setting paragraph Helios's own prompt guide recommends for the
smoothest mid-stream morphs. That's a deliberate trade-off, not an
oversight — see the honesty note below. Nothing stops you from writing a
richer prompt yourself in the free-text box.

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
cd orbis/runner-helios
cp .env.example .env.local
# edit .env.local yourself: REACTOR_API_KEY=rk_...
pnpm install
pnpm dev
```

Open <http://localhost:3000>, click **Connect**, pick a trade from the
dropdown (or write your own prompt), and watch it generate.

## Code tour

Unchanged from the stock template except where noted above. See
[`skill/SKILL.md`](skill/SKILL.md) for the full Helios SDK guide the
original template ships with, and
[`github.com/reactor-team/create-reactor-app`](https://github.com/reactor-team/create-reactor-app)
for the upstream project this was scaffolded from.

| File | What's in it |
| --- | --- |
| `app/lib/modules.generated.json` | **Generated by `orbis/build.py`.** The 111-module scene source. Never hand-edit. |
| `app/lib/prompts.ts` | Maps the generated modules into the `Scene[]` shape every other component reads. |
| `app/components/PromptComposer.tsx` | Setup phase. District-grouped module picker + free-text input → `setPrompt` + `start`. |
| `app/components/ImageStarter.tsx` | Setup phase. Custom image upload → `setImage` (curated image cards are empty here). |
| `app/components/EvolveScene.tsx` | Live phase. Hidden for every generated module (no evolutions authored). |
| `app/lib/flow.ts` | Pure pacing-decision logic for `FlowPanel` - config, the flowFit formula, prompt building. No SDK import; test it with `node flow.test.mjs`. |
| `app/components/FlowPanel.tsx` | Live phase. Optional pacing check-in → calls `setPrompt` on the ambient backdrop only. |
| `app/api/reactor/token/route.ts` | Mints a session-scoped JWT pinned to `reactor/helios`, server-side only. |
| everything else | Unmodified from `create-reactor-app --model=helios`. |

## Licence

Apache-2.0, inherited from `create-reactor-app` (Reactor Technologies,
Inc.) — see `LICENSE` and `NOTICE`. `app/lib/modules.generated.json` is
generated content from SmartCiti.X's own union registry, licensed the
same as the parent repo.
