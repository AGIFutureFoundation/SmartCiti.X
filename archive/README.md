# `archive/` — superseded data kept for provenance

Nothing in this directory is consumed by any builder or test suite. Files
land here when they stop being a truth and start being history: deleting
them would lose the record of what the network grew from, but leaving them
in place would be a second copy of a live fact — the defect class the rest
of this bundle is built to prevent.

The figures lint (`brand/figures.mjs`) deliberately skips this directory:
an archived file correctly states the figures of its own era, which are
wrong everywhere else.

| File | Provenance |
|---|---|
| `map_union_states_33hall.json` | The campus map's per-union module-state data from the 33-hall era, orphaned when the map began computing state from the pack's own position function. Its 33 entries and per-union counts are the superseded scale, preserved verbatim. |

See `wiki/Provenance.md` for the full story.
