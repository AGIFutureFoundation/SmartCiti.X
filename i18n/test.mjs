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
import {
  LOCALES, load, t, fmt, STATUSES, claimsReview, validateCatalog,
  hallNameLocales, loadHallNames, validateHallNames,
} from './catalog.mjs';

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

/* ------------------------------------------------- reviewer attribution -- *
 * v3.3 exit criterion 1: a catalog claiming `reviewed` status names its
 * reviewer; a hall-name catalog is complete or absent, never partial. Both
 * rules live once, in i18n/catalog.mjs (validateCatalog / validateHallNames),
 * so this suite, catalog.mjs's own load(), and i18n/validate.mjs (which
 * web/build_languages.py calls, so a bad catalog fails that build too, not
 * only this suite) all enforce the same rule rather than three copies of it.
 */
ok('translation_status is drawn from a closed set (no free text, no fourth state)',
  STATUSES.length === 3 && STATUSES.includes('source language')
  && STATUSES.includes('machine-drafted, pending native review') && STATUSES.includes('reviewed')
  && LOCALES.every((l) => STATUSES.includes(load(l).translation_status)));
ok('every non-source locale still declares the honest pending-review caveat today — '
  + 'this run changes no catalog to reviewed',
  LOCALES.filter((l) => l !== 'en')
    .every((l) => load(l).translation_status === 'machine-drafted, pending native review')
  && en.translation_status === 'source language');
ok('claimsReview() reads "reviewed" as a review claim and the pending-review caveat as honestly not one',
  claimsReview('reviewed') === true
  && claimsReview('reviewed, spot-checked') === true
  && claimsReview('machine-drafted, pending native review') === false
  && claimsReview('source language') === false);
ok('every shipped catalog validates clean today (none claims review, so none needs a reviewer yet)',
  LOCALES.every((l) => validateCatalog(l, load(l)).length === 0));

// Self-test the guard itself, the way training/build.py's balanced-paren
// reader and security/test_sbom.mjs's hash check prove themselves: construct
// the exact bad catalog the rule exists to catch, in memory, and assert the
// validator rejects it. A guard nobody has watched fail is not proven.
{
  const claimsButNoReviewer = { ...en, translation_status: 'reviewed' }; // no `reviewer`, no `reviewed_at`
  const p1 = validateCatalog('fixture', claimsButNoReviewer);
  ok('self-test: a catalog claiming reviewed status with no reviewer field is REJECTED',
    p1.some((m) => /names no reviewer/.test(m)));

  const namedButNoDate = { ...en, translation_status: 'reviewed', reviewer: 'Jordan Alvarez' };
  const p2 = validateCatalog('fixture', namedButNoDate);
  ok('self-test: a catalog claiming reviewed status with a reviewer but no reviewed_at date is REJECTED',
    p2.some((m) => /reviewed_at is missing/.test(m)));

  const clean = {
    ...en, translation_status: 'reviewed', reviewer: 'Jordan Alvarez', reviewed_at: '2026-09-18',
  };
  ok('self-test: the same catalog WITH a named reviewer and a reviewed_at date passes',
    validateCatalog('fixture', clean).length === 0);

  const typo = { ...en, translation_status: 'reviewed (spot check)' };
  ok('self-test: a status the closed set does not recognise is REJECTED even if it reads as a review claim',
    validateCatalog('fixture', typo).some((m) => /not one of/.test(m)));
}

/* ------------------------------------------------ hall-name catalogs ----- */
const halls = JSON.parse(readFileSync(new URL('../pack/registry/halls.json', import.meta.url))).halls;
const hallSlugs = halls.map((h) => h.slug);
ok('the pack names 111 halls to check any hall-name catalog against',
  hallSlugs.length === 111 && new Set(hallSlugs).size === 111);
ok('no hall-name catalog ships today (ws2 has not run) — the complete-or-absent rule holds vacuously',
  hallNameLocales().length === 0);
ok('every hall-name catalog that DOES exist validates as complete (all 111) and reviewed',
  hallNameLocales().every((l) => validateHallNames(l, loadHallNames(l), hallSlugs).length === 0));

// Self-test: the 110-of-111 catalog the rule exists to catch, plus the
// complete-but-unreviewed catalog the "never partial" wording alone would miss.
{
  const complete111 = Object.fromEntries(hallSlugs.map((s, i) => [s, `Fixture Name ${i}`]));
  const partial110 = { ...complete111 };
  delete partial110[hallSlugs[0]];
  const partialDoc = {
    ...en, translation_status: 'reviewed', reviewer: 'Jordan Alvarez', reviewed_at: '2026-09-18',
    halls: partial110,
  };
  const pPartial = validateHallNames('fixture', partialDoc, hallSlugs);
  ok('self-test: a hall-name catalog covering 110 of 111 halls is REJECTED — never partial',
    pPartial.some((m) => /must be complete/.test(m) && /missing: 1/.test(m)));

  const extraDoc = {
    ...en, translation_status: 'reviewed', reviewer: 'Jordan Alvarez', reviewed_at: '2026-09-18',
    halls: { ...complete111, 'not-a-real-hall': 'Ghost' },
  };
  ok('self-test: a hall-name catalog with an extra, unrecognised slug is REJECTED too',
    validateHallNames('fixture', extraDoc, hallSlugs).some((m) => /extra: 1/.test(m)));

  const unreviewedDoc = { ...en, translation_status: 'machine-drafted, pending native review', halls: complete111 };
  ok('self-test: a COMPLETE 111-hall catalog that is not status "reviewed" is still REJECTED',
    validateHallNames('fixture', unreviewedDoc, hallSlugs)
      .some((m) => /is not status "reviewed"/.test(m)));

  const cleanDoc = {
    ...en, translation_status: 'reviewed', reviewer: 'Jordan Alvarez', reviewed_at: '2026-09-18',
    halls: complete111,
  };
  ok('self-test: a complete, reviewed, named 111-hall catalog passes',
    validateHallNames('fixture', cleanDoc, hallSlugs).length === 0);
}

/* ------------------------------------------------------------- loader ---- */
ok("t() resolves dotted keys and fmt() fills placeholders",
  t('es', 'strings.nav.campus') === 'Mapa del campus'
  && fmt(t('de', 'strings.figures.halls'), { n: '111' }) === '111 Gewerkschaftshallen');
ok('strict lookup throws on a missing key instead of falling back silently',
  (() => { try { t('es', 'strings.does.not.exist'); return false; } catch { return true; } })());

console.log(`i18n/test: ${n} checks passed — ${LOCALES.length} locales`);
