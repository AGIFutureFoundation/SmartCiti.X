/**
 * Locale catalog verification.
 *
 * The catalogs are one more set of surfaces that can disagree — with each
 * other (a key translated in five languages and missing in the sixth) and
 * with the pack (a district renamed in the roster but not in the strings).
 * Both failure classes are the bundle's oldest defect shape, so both are
 * checked here rather than trusted.
 */
import { readFileSync } from 'node:fs';
import { LOCALES, load, t, fmt } from './catalog.mjs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const en = load('en');
const districts = JSON.parse(readFileSync(new URL('../unions/registry/districts.json', import.meta.url)));
const variants = JSON.parse(readFileSync(new URL('../pack/registry/variants.json', import.meta.url)));
const manifest = JSON.parse(readFileSync(new URL('../pack/manifest.json', import.meta.url)));
const skills = JSON.parse(readFileSync(new URL('../pack/registry/skills.json', import.meta.url))).skills;

/* -------------------------------------------------------------- roster --- */
ok(`eight locales ship: ${LOCALES.join(', ')}`,
  LOCALES.length === 8 && LOCALES.includes('en'));
ok('every locale file names itself correctly and declares a direction',
  LOCALES.every((l) => load(l).locale === l && ['ltr', 'rtl'].includes(load(l).dir)));
ok('Arabic is right-to-left; every other shipped locale is left-to-right',
  load('ar').dir === 'rtl' && LOCALES.filter((l) => l !== 'ar').every((l) => load(l).dir === 'ltr'));
ok('every non-source locale declares its review status honestly',
  LOCALES.filter((l) => l !== 'en').every((l) => /pending .*review/.test(load(l).translation_status))
  && en.translation_status === 'source language');

/* ------------------------------------------------- structural parity ----- */
function keyset(obj, prefix = '') {
  if (Array.isArray(obj)) return [`${prefix}[]:${obj.length}`];
  if (obj && typeof obj === 'object') {
    return Object.keys(obj).sort().flatMap((k) => keyset(obj[k], `${prefix}.${k}`));
  }
  return [prefix];
}
const ref = JSON.stringify(keyset({ ...en, locale: 0, language: 0, english_name: 0, dir: 0, translation_status: 0 }));
ok('every locale carries exactly the source catalog structure — no missing or extra keys',
  LOCALES.every((l) => {
    const c = load(l);
    return JSON.stringify(keyset({ ...c, locale: 0, language: 0, english_name: 0, dir: 0, translation_status: 0 })) === ref;
  }));
const leaves = (o) => (o && typeof o === 'object' ? Object.values(o).flatMap(leaves) : [o]);
ok('no locale ships an empty or non-string value',
  LOCALES.every((l) => leaves(load(l).strings).every((v) => typeof v === 'string' && v.trim().length > 0)));
ok('placeholders survive translation: every {n} in the source appears in every locale',
  LOCALES.every((l) => Object.entries(en.strings).every(([k, v]) => {
    const ph = (v.match(/\{\w+\}/g) ?? []).sort().join();
    const th = ((t(l, `strings.${k}`).match(/\{\w+\}/g)) ?? []).sort().join();
    return ph === th;
  })));

/* ----------------------------------------------- agreement with packs ---- */
ok('district keys match the union registry exactly, in every locale',
  LOCALES.every((l) => JSON.stringify(Object.keys(load(l).districts).sort())
    === JSON.stringify(Object.keys(districts.districts).sort())));
ok('the English district names ARE the union registry names — one truth',
  Object.entries(en.districts).every(([k, d]) => d.name === districts.districts[k].name
    && d.tagline === districts.districts[k].tagline));
ok('ten track names in every locale, and the English ones match the pack ladder',
  LOCALES.every((l) => load(l).tracks.length === 10)
  && JSON.stringify(en.tracks)
    === JSON.stringify(['Orientation', 'Pre-Apprentice', 'Apprentice I', 'Apprentice II',
      'Apprentice III', 'Journey', 'Journey Advanced', 'Specialist', 'Master', 'Instructor']));
ok('strand keys match the skill graph vocabulary, in every locale',
  (() => {
    const want = JSON.stringify([...new Set(skills.map((s) => s.strand))].sort());
    return LOCALES.every((l) => JSON.stringify(Object.keys(load(l).strands).sort()) === want);
  })());
ok('tier, band and modality keys match the variant registry, in every locale',
  LOCALES.every((l) => {
    const c = load(l);
    return JSON.stringify(Object.keys(c.modalities).sort()) === JSON.stringify([...variants.modalities].sort())
      && JSON.stringify(Object.keys(c.bands).sort()) === JSON.stringify([...variants.bands].sort())
      && JSON.stringify(Object.keys(c.tiers).sort()) === JSON.stringify(['applied', 'fundamentals', 'mastery']);
  }));
ok('pipeline state keys match the manifest census, in every locale',
  LOCALES.every((l) => JSON.stringify(Object.keys(load(l).states).sort())
    === JSON.stringify(Object.keys(manifest.by_state).sort())));

/* ----------------------------------------------------------- honesty ----- */
ok('every locale carries all four honesty notes, translated',
  LOCALES.every((l) => ['honesty.taxonomy', 'honesty.modules', 'honesty.content', 'honesty.translation']
    .every((k) => load(l).strings[k]?.trim().length > 0)));

/* ------------------------------------------------------------- loader ---- */
ok("t() resolves dotted keys and fmt() fills placeholders",
  t('es', 'strings.nav.campus') === 'Mapa del campus'
  && fmt(t('de', 'strings.figures.halls'), { n: '111' }) === '111 Gewerkschaftshallen');
ok('strict lookup throws on a missing key instead of falling back silently',
  (() => { try { t('es', 'strings.does.not.exist'); return false; } catch { return true; } })());

console.log(`i18n/test: ${n} checks passed — ${LOCALES.length} locales`);
