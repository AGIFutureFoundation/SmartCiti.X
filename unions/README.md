# `unions/` — the union registry pack

The roster of the 111 trade halls and the eight districts that group them,
separated from the module registry it used to live inside.

## Why this is its own pack

The taxonomy (who the trades are) and the module skeleton (what the Academy
generates for them) are different truths with different change rates: the
roster changes when the network adds a trade, the skeleton changes when the
curriculum shape changes. Keeping them in one directory coupled every roster
edit to a module rebuild and left nothing able to check one against the
other — a file agrees with itself by definition.

The split follows the bundle's own rule (v2.6 defect 12, spec §23.5): one
declaration of one truth, and where two artefacts must agree, a verifier that
proves it rather than a convention that hopes for it.

```
unions/
  unions111.py            # the authored taxonomy: 33 existing + 78 new halls
  build.py                # emits registry/ from the taxonomy
  registry/unions.json    # the roster: index, slug, name, focus, district, cohort
  registry/districts.json # the eight districts and their member halls
  verify.mjs              # 14 checks, including agreement with pack/
```

## Consumers

- `pack/build.py` — reads the roster to generate the module skeleton
- `web/build_map.py` — reads the districts for the campus map
- `unions/verify.mjs` — proves `pack/registry/halls.json` matches the roster
  index for index, name for name

## Running it

```bash
python3 unions/build.py    # regenerate registry/ after editing unions111.py
node unions/verify.mjs     # verify the roster, districts, and pack agreement
```

The registry carries a `source_stamp` (a hash of `unions111.py`), so a stale
build fails verification instead of shipping quietly — the same shape as the
console's staleness guard.

## Honesty note

This is a **taxonomy of skilled trades, not a roster of chartered locals**.
No union has reviewed it, no local is named, and the grouping is ours. Where
a name matches a real trade classification that is because the trade is
real, not because any organisation has endorsed anything.
