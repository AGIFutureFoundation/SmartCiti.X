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

<!-- L10N BEGIN -->
## Native-speaker review (how a verdict gets back into the catalogs)

All seven non-English catalogs are machine drafts and stay `machine-drafted,
pending native review` until a person says otherwise, key by key. Nothing is
marked reviewed today: no reviewer has been named.

```
python3 i18n/build_review.py          # writes dist/review/<locale>.csv and .html, i18n/review/summary.json
python3 i18n/build_review.py --check  # fails if summary.json is stale (source_stamp over every file read)
python3 i18n/ingest_review.py dist/review/de.csv --reviewer "AB"   # take a filled sheet back
python3 i18n/ingest_review.py --sync de                             # restate a catalog's status from its ledger
node i18n/test_review.mjs                                           # the contract, with a round-trip fixture
```

- **The sheet** has one row per catalog key (`strings.*`, district names and
  taglines, tracks, strands, tiers, bands, modalities, states): `key, english,
  draft, appears_in, priority, why, status, verdict, corrected, notes`. The CSV
  is UTF-8 with a BOM and opens in a spreadsheet; the HTML page (right-to-left
  for Arabic) lets the reviewer fill the same columns in a browser and download
  the same CSV. Both start with English instructions and the glossary.
- **Priority** is derived by `i18n/review_rules.json`, never by hand: 1 =
  safety and honesty lines (key names such as `honesty`, `disclaimer`,
  `slowNotice`; English that carries a provenance label, says what is not a
  credential, whether an AI model is involved, what stays on the device, a
  notice); 2 = interface labels and the Academy vocabulary; 3 = page copy.
- **`appears_in`** is derived from the built pages and the builder sources: a
  page is listed when it ships the key in an embedded catalogue or renders the
  English text; a source file when it names the key as a literal (or as a
  dynamic prefix/template, marked `dynamic`). A page that embeds the whole
  catalogue is listed only where it uses the key. A key nothing names says so.
- **Glossary.** SCRIPTED, AUTHORED, RECORDED, DERIVED, MOCKED, PROPOSED (and
  SCHEMATIC) are fixed labels shared with the data, the other pages and the
  tests: they **stay in English, in capitals**; the sentence around them is
  translated. Ingest refuses a correction that drops one the English carries.
- **Why the sheets are not committed.** They are views of the catalogs, the
  built pages and the ledger, stale after the next key anyone adds, and about
  10 MB for seven locales. They go to `dist/` (gitignored). What is committed
  is what must survive: the verdicts, in `i18n/review/<locale>.ledger.json`
  (per key: verdict, `reviewed_by`, `reviewed_at`, sha256 of the English source
  and of the text), the corrected text in the catalog, and `summary.json`.
- **Ingest** is all-or-nothing. A row with no verdict, corrected text or notes is
  untouched (not reviewed). It refuses: an unknown or repeated key; a verdict
  other than `ok`/`fix`; corrected text or notes without a verdict; `ok` with
  corrected text; `fix` with no text, text equal to the draft, or text equal to
  the English; a lost or invented `{placeholder}` or changed `<tag>`; a
  dropped glossary label; a sheet whose `english`/`draft` no longer match the
  catalog; a reviewer containing `@` or a link, or a date in the future. The
  reviewer is a name or initials: no email address is published.
- **`translation_status` is derived from the ledger**, never typed: no
  current verdict = `machine-drafted, pending native review`; N of M =
  `machine-drafted; N of M keys checked by a native speaker, S of P safety and
  honesty lines` (with `reviewer` and `reviewed_at` in the catalog; P is the
  number of priority-1 keys under `review_rules.json`, S how many of them hold
  a current verdict, so a catalog whose interface labels were checked but not
  its safety lines says `0 of P`); every key = `reviewed`. A verdict counts only
  while the English source and the reviewed text are unchanged, so a later edit
  makes it "out of date" and the count drops. When keys are added to a catalog
  that already holds verdicts, run `ingest_review.py --sync <locale>` so M is
  restated. The part-checked wording avoids the word "reviewed" on purpose:
  `rnd/` counts a catalog as a reviewed locale when its status contains it.
- After an ingest, run the page builders again: the pages embed the catalogs.

### Manual steps today (there is no hosted download)

1. A maintainer runs `python3 i18n/build_review.py` and takes
   `dist/review/<locale>.csv` (or `.html`) from the working tree: `dist/` is
   not published, so nothing links to these files.
2. The maintainer sends the file to the reviewer by hand and gets the filled
   file back by hand.
3. The maintainer runs `python3 i18n/ingest_review.py <file> --reviewer "<name or
   initials the reviewer gave>"`, rebuilds, and commits the corrected catalog,
   the ledger and `summary.json`.

### Open decision: who confirms a reviewer is a native speaker

Not decided. Before any catalog may read `reviewed`, the project must decide
who confirms that a reviewer is a native speaker of that language, and how that
confirmation is recorded. Until then a verdict records only the name or
initials the reviewer gives and the date: it is not evidence of the reviewer's
language, qualification or identity, and the wording "checked by a native
speaker" describes what the reviewer says they are, not something the
repository has verified.
<!-- L10N END -->
