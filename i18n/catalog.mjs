/**
 * SmartCiti.X : Trade Craft Academy — the locale catalog.
 *
 * One loader, consumed by every surface that renders in a viewer's language.
 * English (`locales/en.json`) is the source catalog; every other locale must
 * carry exactly the same key structure — `i18n/test.mjs` proves it, so a
 * missing translation fails the build instead of falling back silently in
 * production. Fallback here exists only for forward-compatibility while a
 * key is in review, and it is deliberately loud: `t()` throws in strict mode.
 *
 * Hall NAMES are not in the catalogs: trade names are load-bearing identity
 * and stay in English until reviewed trade-name translations exist (each
 * locale says so in `honesty.translation`). Districts, tracks, strands,
 * tiers, bands, modalities and pipeline states are translated — they are
 * the Academy's own vocabulary, not the trades'.
 */
import { readFileSync, readdirSync } from 'node:fs';

const DIR = new URL('./locales/', import.meta.url);
const HALL_NAMES_DIR = new URL('./hall-names/', import.meta.url);

/**
 * The closed set of `translation_status` values a catalog may declare.
 * Free text here is how a typo becomes a fourth, unnoticed state ("reviewd",
 * "reviewed (draft)", "pending review" with the caveat dropped) — every
 * value a catalog can carry is named here and nowhere else decides.
 */
export const STATUSES = Object.freeze([
  'source language',
  'machine-drafted, pending native review',
  'reviewed',
]);

/**
 * True for any status that CLAIMS a human reviewed the translation — i.e.
 * every status but the two honest non-claims. Written as "contains 'reviewed'
 * and is not the pending-native-review caveat" per the roadmap's own wording,
 * rather than just `=== 'reviewed'`, so that if the closed set above ever
 * grows a second reviewed-ish state, this still catches it: the STATUSES
 * closed set stops a stray string from being ACCEPTED, this stops a status
 * that reads as a review claim from being accepted WITHOUT a reviewer.
 */
export function claimsReview(status) {
  return typeof status === 'string'
    && /reviewed/i.test(status)
    && status !== 'machine-drafted, pending native review';
}

/**
 * Validate one locale catalog's honesty fields. Returns an array of problem
 * strings — empty means clean. Never throws, so a caller can collect every
 * problem across every locale before failing, and `load()` below can use it
 * to fail loudly at the moment a bad catalog is read, not only when the
 * suite happens to check it.
 */
export function validateCatalog(locale, doc) {
  const problems = [];
  const status = doc?.translation_status;
  if (!STATUSES.includes(status)) {
    problems.push(`${locale}: translation_status ${JSON.stringify(status)} is not one of `
      + `the closed set (${STATUSES.join(' | ')})`);
    // Still worth checking the reviewer rule below even on an unrecognised
    // status — an invented "reviewed-ish" string must not dodge it just
    // because it also fails the closed-set check.
  }
  if (claimsReview(status)) {
    const reviewer = doc?.reviewer;
    if (typeof reviewer !== 'string' || reviewer.trim().length === 0) {
      problems.push(`${locale}: translation_status ${JSON.stringify(status)} claims review `
        + 'but names no reviewer');
    }
    const reviewedAt = doc?.reviewed_at;
    if (typeof reviewedAt !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(reviewedAt)) {
      problems.push(`${locale}: translation_status ${JSON.stringify(status)} claims review `
        + `but reviewed_at is missing or not an ISO date (got ${JSON.stringify(reviewedAt)})`);
    }
  }
  return problems;
}

/**
 * Validate one hall-name catalog (`i18n/hall-names/<locale>.json`) against
 * the pack's own hall roster. ws2's rule: a locale ships the 111 hall names
 * only when all 111 are reviewed — so this is complete (every slug present,
 * every name non-empty, status `reviewed` with a named reviewer) or the
 * file must not exist at all. There is no "partial" shape to validate
 * against; a catalog missing even one slug, or carrying an extra one, fails.
 */
export function validateHallNames(locale, doc, hallSlugs) {
  const problems = [...validateCatalog(locale, doc)];
  if (doc?.translation_status !== 'reviewed') {
    problems.push(`${locale}: a hall-name catalog exists but is not status "reviewed" — `
      + 'a locale ships hall names only once all 111 are reviewed, never as a draft');
  }
  const have = doc && typeof doc.halls === 'object' && doc.halls !== null
    ? Object.keys(doc.halls) : [];
  const haveSet = new Set(have);
  const wantSet = new Set(hallSlugs);
  const missing = hallSlugs.filter((s) => !haveSet.has(s));
  const extra = have.filter((s) => !wantSet.has(s));
  if (missing.length || extra.length) {
    problems.push(`${locale}: hall-name catalog covers ${have.length} of ${hallSlugs.length} halls `
      + `(missing: ${missing.length}, extra: ${extra.length}) — must be complete (all `
      + `${hallSlugs.length}) or the file must not exist, never partial`);
  }
  for (const slug of have) {
    const v = doc.halls[slug];
    if (typeof v !== 'string' || v.trim().length === 0) {
      problems.push(`${locale}: hall-name catalog's "${slug}" is empty or not a string`);
    }
  }
  return problems;
}

/** Every hall-name catalog shipped, discovered the same way LOCALES is. */
export function hallNameLocales() {
  let entries;
  try { entries = readdirSync(HALL_NAMES_DIR); } catch { return []; }
  return entries.filter((f) => f.endsWith('.json')).map((f) => f.replace(/\.json$/, '')).sort();
}

export function loadHallNames(locale) {
  return JSON.parse(readFileSync(new URL(`${locale}.json`, HALL_NAMES_DIR)));
}

/** Every locale shipped, discovered rather than listed (one truth). */
export const LOCALES = readdirSync(DIR)
  .filter((f) => f.endsWith('.json'))
  .map((f) => f.replace(/\.json$/, ''))
  .sort();

const cache = new Map();

export function load(locale) {
  if (!cache.has(locale)) {
    const doc = JSON.parse(readFileSync(new URL(`${locale}.json`, DIR)));
    // Validated the moment anything reads a catalog, not only when the
    // suite happens to check it — a bad catalog fails whatever build asked
    // for it, loudly, here, rather than shipping and waiting for a test run.
    const problems = validateCatalog(locale, doc);
    if (problems.length) throw new Error(`i18n: invalid catalog\n${problems.join('\n')}`);
    cache.set(locale, doc);
  }
  return cache.get(locale);
}

/** Look up a dotted key, e.g. t('es', 'strings.nav.campus'). */
export function t(locale, key, { strict = true } = {}) {
  const probe = (loc) => {
    let cur = load(loc);
    // strings.* keys contain dots of their own ("nav.campus"), so resolve the
    // top-level section first and then the literal remainder.
    const [head, ...rest] = key.split('.');
    cur = cur?.[head];
    if (rest.length === 0) return cur;
    if (cur && typeof cur === 'object' && rest.join('.') in cur) return cur[rest.join('.')];
    return rest.reduce((o, k) => (o && typeof o === 'object' ? o[k] : undefined), cur);
  };
  const hit = probe(locale);
  if (hit !== undefined) return hit;
  if (strict) throw new Error(`i18n: no ${locale} value for ${key}`);
  return probe('en');
}

/** Interpolate {n}-style placeholders. */
export function fmt(s, vars) {
  return s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m));
}
