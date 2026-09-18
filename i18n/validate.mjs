#!/usr/bin/env node
/**
 * i18n catalog validation as a standalone exit code, for a non-JS build to
 * call. `i18n/catalog.mjs`'s `load()` already validates every catalog it
 * reads, so any JS surface fails the moment it loads a bad one — but
 * `web/build_languages.py` reads the locale JSON directly (it is Python;
 * there is no JS runtime inside it to import `catalog.mjs`), so without
 * this it could render a catalog `i18n/test.mjs` would reject. This script
 * is the one thing both runtimes can share: `catalog.mjs`'s rules, run here,
 * called from the Python build so a bad catalog fails that build too, not
 * only the suite.
 *
 *   node i18n/validate.mjs
 *
 * Exits non-zero and prints every problem found, across every locale
 * catalog and every hall-name catalog, rather than stopping at the first.
 */
import { readFileSync } from 'node:fs';
import {
  LOCALES, load, validateCatalog, hallNameLocales, loadHallNames, validateHallNames,
} from './catalog.mjs';

const problems = [];

for (const locale of LOCALES) {
  let doc;
  try {
    doc = load(locale); // load() itself throws on a bad catalog; catch it here to keep going
  } catch (e) {
    problems.push(String(e.message ?? e));
    continue;
  }
  problems.push(...validateCatalog(locale, doc));
}

const halls = JSON.parse(readFileSync(new URL('../pack/registry/halls.json', import.meta.url)));
const hallSlugs = halls.halls.map((h) => h.slug);
for (const locale of hallNameLocales()) {
  const doc = loadHallNames(locale);
  problems.push(...validateHallNames(locale, doc, hallSlugs));
}

if (problems.length) {
  console.error(`i18n/validate: ${problems.length} problem(s)`);
  for (const p of problems) console.error(`  - ${p}`);
  process.exit(1);
}
console.log(`i18n/validate: ${LOCALES.length} locale catalogs and `
  + `${hallNameLocales().length} hall-name catalogs clean`);
