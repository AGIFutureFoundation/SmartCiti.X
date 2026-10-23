# Checking the world tiles in Sneeze or Artemis

**Status today: nobody has done this.** No tile and no manifest from this repository has been opened in Sneeze or Artemis, so every page says "not loaded". This checklist is for the first person who can. It takes about 30 minutes for the nine manifests; the first campus alone takes about 5.

You do not need to be an expert. You need the repository, Python 3.8 or newer, Node.js (the tile build uses it), and one of:

- **Artemis**, RP1's native browser built on Sneeze (download link: the "Install" step of Example 01 in the Sneeze docs, <https://raw.githubusercontent.com/MetaversalCorp/SneezeDoc/main/docs/examples/01-stool.md>), or
- **Sneeze** built from <https://github.com/MetaversalCorp/Sneeze> inside some host application you already have. Sneeze is an engine library, not an app; how your host accepts a fabric address is up to the host.

**An observed run is a statement by a named person; its screenshots stay with that person and are recorded here only by hash, so a reader cannot see them from this repository.** Everything you report is recorded as *reported by you*, with your name, the date and the engine version. Say "untested" or "fail" whenever that is what happened. A run full of "fail" is as useful as a run full of "pass".

## 1. Build the tiles

```
python3 spatial/build.py
```

This writes `dist/sneeze/` (29 `.glb` tiles and 9 manifests, about 7 MB). It takes under a minute. It does not change any committed file; `git status` should stay clean.

## 2. Run the pre-flight (no Sneeze needed)

```
python3 spatial/sneeze_kit/preflight.py --out preflight.json
```

It serves the folder for a moment and checks, over real web requests, that every manifest and tile is what the registry records, is served with the right type, and follows the manifest shape the Sneeze example docs show. **Every line must say `ok`.** If one says `FAIL`, stop and tell us which; do not test a broken build.

## 3. Make your results file and the expectation table

```
python3 spatial/sneeze_kit/template.py --preflight preflight.json --out my-run.json
python3 spatial/sneeze_kit/template.py --guide > expected.md
```

`expected.md` lists, for every tile, how wide it should be (east-west and north-south, in km), how tall, and where it should sit relative to the first tile of its manifest. Keep it open; you will compare against it.

## 4. Serve the files

```
python3 spatial/sneeze_kit/serve.py --log requests.jsonl
```

It prints the nine manifest addresses, for example `http://127.0.0.1:8765/campus-oakland.json`. Leave it running. It serves only the `dist/sneeze/` folder, with the right file types, open CORS and byte-range support (the Sneeze docs do not say whether the engine uses ranges; they are there in case). When you stop it with Ctrl-C it prints how many tiles the viewer actually asked for and which it never asked for. Copy that sentence into `notes`.

**If the engine cannot reach RP1's server for the module:** the manifests name the stock `map.wasm` on RP1's CDN (`https://cdn.rp1.com/sneeze/examples/wasm/map.wasm`). That module reads `Data.Scene` and builds the nodes; the Sneeze docs say to host your own copy rather than depend on RP1's server. Download it as Example 01 step 1 shows, then restart with `serve.py --map-wasm path/to/map.wasm`. It prints a second list of `<id>.local.json` manifests that point at your copy; use those, and set `serve.map_module` to `"local"`, `serve.manifest_variant` to `"local-module"` and `serve.map_module_sha256` to the hash `serve.py` prints. (The repository could not fetch that file itself, so it has never been hashed here.)

## 5. Open the manifests, smallest first

In Artemis, type the full address into the address bar (Example 01 step 3). In your own host, hand the address to the engine however the host does. Go in this order, because the first ones are small and tell you quickly whether anything works:

1. `campus-oakland` (19 KB), then `campus-treasure-island`, `campus-new-orleans`
2. `wilds-mountain`, `wilds-forest`, `wilds-canyon`, `wilds-delta`
3. `bayarea` (9 counties), then `parishes` (13 parishes, the largest, about 4 MB)

Note the engine's own log or console if it has one: a message about a refused unsigned manifest, a missing module or a bad model is the most useful thing you can report. The Sneeze docs say unsigned plain-JSON manifests "work today" but may stop working; these are unsigned.

## 6. What to look at, for each manifest

Fill these into `my-run.json` under `manifests[]`. Use `pass`, `fail`, `untested` or `not_applicable`.

| Field | Ask yourself | Write `pass` when |
|---|---|---|
| `loaded` (`yes`/`partial`/`no`/`untested`) | Did the manifest open at all? | `yes` when every tile of it showed; `partial` when some did; `no` when nothing did. |
| `appears` (per tile) | Is there a solid coloured shape for this tile, with no error in the log? | You can see it. |
| `orientation` (per tile) | **Right way up after Sneeze's own Y-up to Z-up conversion.** The tiles are glTF files (Y is up); the Sneeze docs say it converts to its Z-up world on import. Region tiles are thin sheets (see the height column in `expected.md`: 4.5 m across tens of km), so they must lie flat like a map, not stand on an edge, not be upside down, not be mirrored. | Looking down from above you see the region as on a map; looking from the side you see a thin flat sheet. Authored wilds have hills that point up at the sky. Campus halls stand up from the ground. |
| `scale` (per tile) | Is it the size `expected.md` says? If the engine has a ruler or shows coordinates, measure one tile. If not, judge the *ratios*: Plaquemines is about 3 times as wide as St. James, and St. Bernard about 3 times as wide as St. Charles. | Sizes match the table to within about 10%, or the ratios do. |
| `child_position` (per tile except the first) | Does it sit where the table says relative to the first tile? In the parish and county sets, neighbours should *touch along their borders* the way they do on a map (the outlines are coarse, so thin gaps are normal). Overlaps or large gaps mean the offsets are not read as metres east/north. | Directions and rough distances match; neighbours meet. Use `not_applicable` for the first tile and for single-tile manifests. |
| `smooth` (per tile) | Can you move the camera and zoom around it without freezes? | It stays usable. Write what machine and what frame rate in `notes` if the app shows one. |
| `geopose_anchor_read` (per manifest) | Does the engine visibly *use* `Data.Anchors`: place the world at its latitude/longitude, show the coordinates, or log a message naming it? **The Sneeze docs say nothing about it**, so "no" is the expected answer and a perfectly good one. | `yes` only if you saw it do something with the anchor. |

If a manifest does not load, mark the tiles `fail` or `untested` and put what the log said in `notes`. Do not mark `pass` for anything you did not see.

## 7. The eight proposed fields

`my-run.json` has a `fields[]` list with the eight things the registry marks **proposed** (nothing primary documents them). Leave a field `untested` unless you actually looked. To say `observed` you must write what you saw in `evidence` (at least a sentence) and give at least one screenshot hash. The recorder also checks that your tile observations support it; if they do not, the field stays proposed and the run says why.

| Field | What `observed` will mean |
|---|---|
| Data.Anchors sidecar | The engine loaded a manifest carrying that block without error (not that it uses it). |
| Data.Provenance sidecar | The same, for the provenance block. |
| Horizontal axes are east/north | A loaded multi-tile manifest (`bayarea` or `parishes`) with every tile appearing and every `child_position` a `pass`. |
| GeoPose anchor consumed | You saw the engine use `Data.Anchors` (`geopose_anchor_read: yes`). |
| Attaching one manifest to another | Cannot be shown with these files; leave `untested`. |
| Camera and render scale at 10-100 km | A tile at least 10 km across appeared and its scale was a `pass`. |
| Largest tile inside the frame budget | The largest tile (Lafourche Parish, 592 KB) appeared and was `smooth`, on your machine in this run. |
| Signing | Cannot be shown with these files; leave `untested`. |

`contradicted` is for when you saw the opposite (for example, north is clearly not +Y): same evidence rule. That is as valuable as `observed`.

## 8. Screenshots

Take at least one per manifest you opened, plus one per `observed` field. Get each file's SHA-256 hash:

- Linux: `sha256sum shot.png`
- macOS: `shasum -a 256 shot.png`
- Windows: `certutil -hashfile shot.png SHA256`

List them in `screenshots[]` (`sha256` and a one-line `caption`), and refer to the hash from the tile, manifest or field they support. The images themselves are **not** stored in the repository; send them separately to whoever ingests the run. If you publish them somewhere (a gist, a repository, a web page), put the `https://` address in `screenshots_url` and it is shown beside the result; without it nobody reading this repository can look at them. Never put an email address there.

## 9. Fill in who, when, what

In `my-run.json` replace every `FILL IN`: your name or public handle (**not** an email address), the date (`YYYY-MM-DD`), the engine (`Sneeze` or `Artemis`), its version, the commit hash if you built it (Sneeze has no published release when last read, so give the commit), where you got it, your operating system and version, and the commit of this repository you built from (`git rev-parse HEAD`). A run with no person, no version or commit, or a placeholder is refused.

## 10. Record it

```
python3 spatial/sneeze_kit/ingest.py my-run.json --dry-run
python3 spatial/sneeze_kit/ingest.py my-run.json --screens folder-with-your-screenshots
```

The first shows what would happen and writes nothing. The second writes `spatial/registry/sneeze_runs.json`. It refuses an incomplete run, a run of a different build, a field marked `observed` without evidence, and the same run twice. For each field it either flips it from `proposed` to `observed in <engine> <version>`, or leaves it proposed and says why. It never writes any stronger word.

Then open a pull request with the changed `sneeze_runs.json` (or send `my-run.json` and your screenshots to whoever maintains the repository). The pages keep saying "not loaded in Sneeze or Artemis" until their builders are changed to read that file; that change is made by a person, deliberately, after reading the run.

## A results sheet to fill in by hand as you go

| Manifest | loaded | GeoPose read | Notes |
|---|---|---|---|
| campus-oakland | | | |
| campus-treasure-island | | | |
| campus-new-orleans | | | |
| wilds-mountain | | | |
| wilds-forest | | | |
| wilds-canyon | | | |
| wilds-delta | | | |
| bayarea | | | |
| parishes | | | |

For each tile: appears / orientation / scale / child position / smooth = pass, fail, untested or not applicable. Then copy it into `my-run.json`.

## What this does not establish

A passing pre-flight shows the files are what the registry records and are served as the docs expect. Only a run in Sneeze or Artemis can show the engine loads them. One run, on one machine, shows that and nothing more: not that every version works, not that signed fabrics work, and not that anything here is an OMBI or MSF standard.
