# loop/ — the two-hour agent loop

SmartCiti.X : Trade Craft Academy runs its roadmap work as a loop: eight
scoped agents, five cycles of 30 minutes, a checkpoint at the end of each
cycle. This directory is the machinery that makes a checkpoint mean
something — a liveness probe, nine executed eval gates, and a ledger that
records what each cycle actually ran and shipped. Nothing here is deployed;
the loop works on a branch and a human merges.

## Commands

    node loop/heartbeat.mjs                 # < 3 s liveness probe
    node loop/evals.mjs                     # run gates EV-01..EV-09 (~10 s; EV-01 runs verify_all.sh)
    node loop/cycle.mjs show                # print and validate the ledger
    node loop/cycle.mjs add --json c.json   # validate and append one cycle
    node loop/test.mjs                      # tests for all of the above (does not run verify_all.sh)

## Files

| Path | What it is |
|---|---|
| `heartbeat.mjs` | git branch and dirty count, every registry `pack_version` against `pack/manifest.json`, `node`/`python3`/`ffmpeg` on PATH, age of the last cycle and the last eval run. Appends `{ts, ok, checks}` to `state/heartbeat.jsonl`. Exits 1 only on a hard failure. |
| `evals.mjs` | The nine gates, below. Writes `state/evals_latest.json`, appends to `state/evals.jsonl`, exits 1 if any gate fails. |
| `cycle.mjs` | Ledger validator and writer. Fills gates, check count and heartbeat from `state/` when the input omits them. |
| `registry/cycles.json` | The cycle ledger. |
| `METAPROMPT.md` | Orchestrator meta-prompt and one role prompt per agent, each with the one directory it may write. |
| `honesty.json`, `honesty.mjs` | The one honesty vocabulary and scanner, used by EV-05 and `courses/test.mjs`; `courses/build.py` loads the same JSON. |
| `registry/honesty_fixtures.json` | The scanner corpus (flag / clean). `loop/test.mjs` and `courses/test.mjs` run it; `courses/test.mjs` also runs `python3 courses/build.py --scan-fixtures` and requires identical verdicts. |
| `patch_cycle.mjs` | Refresh a logged cycle's gates from `state/` and attach its video by bare file name; validates the ledger before writing. |
| `registry/*_draft.json` | Planning drafts the loop was adapted from. A `built-elsewhere` status means built in another project and not verified here. |

## Gates

| Gate | Executes | Absent when |
|---|---|---|
| EV-01 | `./verify_all.sh`; records total checks and failing suites | — |
| EV-02 | `node courses/test.mjs` | the file does not exist yet |
| EV-03 | `node brand/lint.mjs .` | — |
| EV-04 | `node brand/figures.mjs .` | — |
| EV-05 | honesty lint over files changed vs `origin/main` plus untracked | — |
| EV-06 | `ffprobe` on the latest cycle's review video; outside 120 ± 0.5 s is a **warn**, a machine path in the ledger or an unreadable file is a fail | no cycle or no video yet |
| EV-07 | ledger schema, including `pack_version` against the manifest | — |
| EV-08 | secret patterns in the diff and untracked files | — |
| EV-09 | pilot precondition: fails if a cycle sets `pilot.real_learners` without a non-empty `partner` and `consent_plan_ref`, or if its shipped, notes or agent result text mentions a pilot with learners, students or a cohort without such a record | — (passes as "no pilot recorded") |

EV-05 flags a clause that uses claim language (the verbs and nouns listed
in `loop/honesty.json`, from `accredited` to `partnership with`) unless a
negation or qualifier (no, not, none, never, nothing, zero, neither, nor,
n't, planned, proposed) comes EARLIER in the same clause. Clauses end at . ! ? ; and at ", but" / ", not". Abbreviations
(e.g., i.e., Art. 5, No. 5) neither negate nor end a sentence. Fenced blocks
and code spans are quoting, not claiming; a claim inside a regex alternation
(`a|b`, pipes tight on a side) is a rule table, not a claim.

## What a checkpoint does

Every 30 minutes from `loop.started`:

1. Run the heartbeat. A hard failure stops the cycle until it is fixed.
2. Run the evals. Any `fail` stops the release: nothing is committed.
3. Record the cycle with `cycle.mjs add` — sprint, what shipped, each
   agent's task and result, the gates as executed, the review video if one
   was made. The ledger refuses a cycle that records a commit alongside a
   failing gate.
4. The Orchestrator posts one line: done, blocked, next.

`state/` is the loop's working output (heartbeat and eval history); the
ledger is the record.
