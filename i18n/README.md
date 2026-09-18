# `i18n/` — the locale catalogs

The Academy's vocabulary in eight languages: English (the source), Spanish,
French, German, Portuguese, Chinese (Simplified), Hindi and Arabic.

```
i18n/
  locales/en.json     # the source catalog — every other locale mirrors its structure
  locales/{es,fr,de,pt,zh,hi,ar}.json
  hall-names/         # per-locale hall-name catalogs — none ship yet (ws2, below)
  catalog.mjs         # loader + validator: LOCALES, load(), t(), fmt(), STATUSES,
                       # claimsReview(), validateCatalog(), validateHallNames()
  validate.mjs        # CLI wrapper around the validator, for a non-JS build to call
  test.mjs            # 31 checks: parity, placeholders, pack agreement, honesty,
                       # the reviewer-attribution rule (self-tested against fixtures)
  lint_hardcoded.mjs  # fails on any hard-coded English string in the landing, map
                       # or languages page generators (self-tested against fixtures)
```

## What is translated, and what deliberately is not

Translated: the UI strings, the eight district names and taglines, the
ten-track level ladder, the eleven skill strands, tiers, bands, modalities
and pipeline states — the Academy's own vocabulary.

**Not translated: the 111 hall names.** Trade names are load-bearing
identity, and a machine-drafted "Boilermakers" in eight languages is exactly
the kind of confidently wrong surface the rest of this bundle exists to
prevent. Every locale carries an honesty note saying so
(`honesty.translation`), and the roadmap tracks reviewed trade-name
translations as its own milestone.

Every non-English catalog declares `"translation_status":
"machine-drafted, pending native review"` — the same honesty rule as the
curriculum content, applied to language.

## The rules `test.mjs` enforces

- **Structural parity** — every locale carries exactly the source catalog's
  key structure. A missing translation fails the suite; there is no silent
  fallback in a shipped catalog.
- **Placeholder survival** — every `{n}` in a source string appears in every
  translation of it.
- **Pack agreement** — district keys and names match `unions/registry/`,
  strand keys match the skill graph, modality/band keys match the variant
  registry, state keys match the manifest census. A vocabulary rename that
  misses the catalogs fails here.
- **Direction** — every locale declares `ltr` or `rtl`; Arabic is `rtl`.
- **Honesty** — all four honesty notes exist, translated, in every locale.
- **Reviewer attribution (v3.3 exit criterion).** `translation_status` is
  drawn from a closed set — `source language` | `machine-drafted, pending
  native review` | `reviewed` — so a typo cannot silently invent a fourth
  state. A status that claims review (`reviewed`, or any future status
  `claimsReview()` reads as one — see `catalog.mjs`) must carry a non-empty
  `reviewer` naming a person and a `reviewed_at` date (`YYYY-MM-DD`); a
  catalog that claims review without both fails. This is enforced three
  times over, on purpose, not as three copies of the rule: `catalog.mjs`'s
  `load()` validates every catalog the moment anything in JS reads it;
  `i18n/test.mjs` asserts the rule directly and self-tests it against
  fixtures (a `reviewed` catalog with no reviewer, one with a reviewer but
  no date); and `i18n/validate.mjs` runs the same `catalog.mjs` validator as
  a CLI so `web/build_landing.py`, `web/build_map.py` and
  `web/build_languages.py` (Python, so they never go through `catalog.mjs`
  otherwise) fail their own build on a bad catalog too, not only the suite.
- **Hall-name catalogs, complete or absent, never partial.** Convention:
  `i18n/hall-names/<locale>.json`, one file per locale that ships hall
  names, shaped `{ locale, translation_status, reviewer, reviewed_at, halls:
  { <slug>: <name>, ... one entry per hall in pack/registry/halls.json } }`.
  A hall-name catalog must be `reviewed` (with reviewer + date, same rule as
  above) AND cover every one of the 111 halls — missing even one, or naming
  one that is not a real hall slug, fails. No hall-name catalog exists yet
  (ws2 has not run), so this rule holds vacuously today; `i18n/test.mjs`
  proves it bites the moment one appears, with a 110-of-111 fixture the
  validator must reject.

## The hard-coded-English lint

`i18n/lint_hardcoded.mjs` reads `web/build_landing.py`, `web/build_map.py`
and `web/build_languages.py` — the GENERATOR source, not the built HTML, the
same distinction `brand/lint.mjs` draws — and fails on any user-visible text
(a text node, or an `alt`/`title`/`placeholder`/`aria-label` attribute) that
is not sourced from a catalog lookup (`S('key')` in these three builders).
Exempt: the brand name and its parts — proper nouns, the same class of
exemption as the 111 untranslated hall names above, not translatable UI
copy. (`build_map.py` once also exempted two "planned-campus place names",
`Oakland Training Yard` and `SF Bridgehead`, drawn on the campus plan as
dashed `PLANNED · NOT BUILT` parcels; Oakland is a real, built, 32-hall
campus, and both the parcels and the exemption are gone — see
`brand/figures.mjs`'s built-campus rule.) The lint's own file header
documents exactly what counts as in scope and why, and its self-test proves
the rule catches a hard-coded sentence, a hard-coded `alt` attribute and a
hard-coded JS string literal before trusting it clean.

## Surfaces

`web/build_languages.py` renders `web/trade_craft_languages.html` — the
Academy overview in every locale, direction-aware, with figures read from
the manifest and districts from the union registry so the page cannot
disagree with either. Its locale switcher mirrors the shown section's `dir`
onto `<html>` itself (`document.documentElement.dir`), not just the inner
`<section>` — the gap v3.3's RTL exit criterion found and closed; before
that fix, the page chrome (nav tabs, header) stayed `dir="ltr"` no matter
which language was showing.

`web/build_landing.py` and `web/build_map.py` render entirely in English —
they have no locale switch of their own — but their user-visible text now
comes from `en.json` (via the `S('key')` helper each builder defines) rather
than being typed as Python literals, and their CSS uses logical properties
(`margin-inline-start`, `border-inline-end`, `text-align:start`, …) instead
of hard-coded `left`/`right`, so the layout would mirror correctly if either
page ever gained a real RTL rendering path. `web/test_rtl.mjs` holds both
facts at the source; see the v3.3 entry in `ROADMAP.md` for the headless
Chromium proof that the CSS actually does mirror when `dir="rtl"` is set.

## Adding a locale

1. Copy `locales/en.json`, translate every value, set `locale`, `language`,
   `english_name`, `dir`, and an honest `translation_status`.
2. `node i18n/test.mjs` — the parity checks tell you what is missing.
3. `python3 web/build_languages.py` — the page picks up the new locale by
   discovery; there is no second list to update.
