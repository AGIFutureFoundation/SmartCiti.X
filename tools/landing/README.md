# Landing tools

The scripts used to land a batch of work on `main` with as little waiting and
as few tokens as possible. They contain no path from any one machine: every
location is an argument or an environment variable. The protocol they serve is
written out in plain words on the wiki page
[Build-and-Landing](../../wiki/Build-and-Landing.md), which is generated from
these files.

| File | What it does |
|---|---|
| `rebuild_all.sh <tree>` | Runs every builder of the tree, in dependency order, and prints `REBUILT`. Run it **twice**. A builder that exists but is not named in it fails `test.mjs`, unless the suite lists it with a reason. |
| `browser_round.sh <tree> <outdir> <port> [runs-file]` | Serves the tree on a local port and runs the browser suites one at a time, each under one chromium lock (`CHROMIUM_LOCK`, or `$TMPDIR/chromium.lock`). Writes one log per run and a `round.txt` summary into `<outdir>`. |
| `browser_runs.sh` | The default round: one `run <name> <timeout-seconds> <command...>` line per run, sourced by `browser_round.sh`. Copy it, edit it, and pass the copy as the fourth argument for a different round. |
| `geomap_hillshade_probe.mjs` | The one-page probe the default round runs on the geomap (flies to a campus, reports which hillshade files loaded). |
| `readme_fix.py <tree> <verify-output> [rows.json]` | Moves every count typed in `README.md` (each suite row and the headline) to the count a `verify_all.sh` run printed. `rows.json` is optional one-off wording: `{ "<suite>": "<row text with %s for the count>" }`. |
| `test.mjs` | The drift guard: `node tools/landing/test.mjs`. |

## The protocol in eight lines

1. **Freeze** a copy of the working tree. Everything below runs on the copy.
2. **Rebuild twice**: `tools/landing/rebuild_all.sh <frozen>`, then again.
3. **Verify**: run `verify_all.sh` in the copy and keep its output.
4. **Fix the README counts in the copy only**: `python3 tools/landing/readme_fix.py <frozen> <verify-output>`.
5. **Browser round** under the one lock: `tools/landing/browser_round.sh <frozen> <outdir> <port>`.
6. **Byte-compare** what will be committed with the frozen copy.
7. **Scan** the change for key material, model identifiers and machine-local paths.
8. **Commit and push** from the person landing the work; nobody else runs git.

## The drift guard

`node tools/landing/test.mjs` prints `  ok <name>` per check and `FAIL <name>` at
column 0. It fails when

- a builder (`*/build.py`, `*/*/build.py`, `*/build_*.py`, `web/build_*.py`) exists on disk but is not run by `rebuild_all.sh` and is not on the skip list, each entry of which carries its reason;
- the script names a builder that no longer exists, or the order it relies on (the wiki last, the SBOM before the pages) is changed;
- a file under `tools/` holds a machine-local path (a scratch directory, a temporary directory, a home directory);
- a script is not executable or does not parse;
- `readme_fix.py` stops doing what is written above, tested on a copy.

## Team token rules

Read files by line range (`grep -n`, then `sed -n a,bp`), never whole built
pages (`web/trade_craft_*.html` run from 0.1 to 3 MB). Run single suites while
iterating and leave `verify_all.sh` and `rebuild_all.sh` to whoever lands. At
most four browser runs per agent, each under the lock and within 90 seconds.
A handback report is under 400 words.
