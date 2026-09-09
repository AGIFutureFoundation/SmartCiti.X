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

/** Every locale shipped, discovered rather than listed (one truth). */
export const LOCALES = readdirSync(DIR)
  .filter((f) => f.endsWith('.json'))
  .map((f) => f.replace(/\.json$/, ''))
  .sort();

const cache = new Map();

export function load(locale) {
  if (!cache.has(locale)) {
    cache.set(locale, JSON.parse(readFileSync(new URL(`${locale}.json`, DIR))));
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
