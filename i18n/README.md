# `i18n/` — the locale catalogs

The Academy's vocabulary in eight languages: English (the source), Spanish,
French, German, Portuguese, Chinese (Simplified), Hindi and Arabic.

```
i18n/
  locales/en.json   # the source catalog — every other locale mirrors its structure
  locales/{es,fr,de,pt,zh,hi,ar}.json
  catalog.mjs       # loader: LOCALES, load(), t(), fmt()
  test.mjs          # 16 checks: parity, placeholders, pack agreement, honesty
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

## Surfaces

`web/build_languages.py` renders `web/trade_craft_languages.html` — the
Academy overview in every locale, direction-aware, with figures read from
the manifest and districts from the union registry so the page cannot
disagree with either.

## Adding a locale

1. Copy `locales/en.json`, translate every value, set `locale`, `language`,
   `english_name`, `dir`, and an honest `translation_status`.
2. `node i18n/test.mjs` — the parity checks tell you what is missing.
3. `python3 web/build_languages.py` — the page picks up the new locale by
   discovery; there is no second list to update.
