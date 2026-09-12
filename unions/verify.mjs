/**
 * Union registry verification.
 *
 * The roster and the module pack used to live in one directory, so nothing
 * could check them against each other — a file agrees with itself by
 * definition. Now that they are separate packs, this suite proves the
 * separation did not break the one property that matters: the module
 * registry in `pack/` and the union registry here describe the SAME 111
 * halls, in the same order, with the same identities.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const unions = JSON.parse(readFileSync(new URL('./registry/unions.json', import.meta.url)));
const districts = JSON.parse(readFileSync(new URL('./registry/districts.json', import.meta.url)));
const campuses = JSON.parse(readFileSync(new URL('./registry/campuses.json', import.meta.url)));
const halls = JSON.parse(readFileSync(new URL('../pack/registry/halls.json', import.meta.url)));
const manifest = JSON.parse(readFileSync(new URL('../pack/manifest.json', import.meta.url)));

/* ----------------------------------------------------------- the roster --- */
ok('the roster holds exactly 111 unions', unions.count === 111 && unions.unions.length === 111);
ok('the cohorts split 33 + 78, preserving every 33-hall union index',
  unions.cohorts['existing-33'] === 33 && unions.cohorts['new-78'] === 78
  && unions.unions.slice(0, 33).every((u) => u.cohort === 'existing-33')
  && unions.unions.slice(33).every((u) => u.cohort === 'new-78'));
ok('every slug is unique, lower-case and space-free',
  new Set(unions.unions.map((u) => u.slug)).size === 111
  && unions.unions.every((u) => u.slug === u.slug.toLowerCase() && !u.slug.includes(' ')));
ok('indices are dense: union i sits at position i',
  unions.unions.every((u, i) => u.index === i));
ok('every union carries a name and a focus line',
  unions.unions.every((u) => u.name && u.focus));

/* -------------------------------------------------------- the districts --- */
const memberLists = Object.values(districts.districts).map((d) => d.halls);
const assigned = memberLists.flat();
ok('eight districts, none empty', districts.count === 8
  && memberLists.length === 8 && memberLists.every((m) => m.length > 0));
ok('the districts partition the roster: every hall in exactly one district',
  assigned.length === 111 && new Set(assigned).size === 111
  && new Set(assigned).size === new Set(unions.unions.map((u) => u.slug)).size
  && assigned.every((s) => unions.unions.some((u) => u.slug === s)));
ok("each union's district field agrees with the district member lists",
  unions.unions.every((u) => districts.districts[u.district]?.halls.includes(u.slug)));

/* --------------------------------- agreement with the module pack -------- */
ok('the module pack authors the same number of halls as the roster',
  halls.count === unions.count && halls.halls.length === 111);
ok('hall order matches the roster index for index',
  halls.halls.every((h, i) => h.index === i && h.slug === unions.unions[i].slug));
ok('hall names and focus lines match the roster exactly',
  halls.halls.every((h, i) => h.name === unions.unions[i].name
    && h.focus === unions.unions[i].focus));
ok('the module manifest ledger agrees on the hall count',
  manifest.ledger.halls === unions.count);

/* ---------------------------------------------------------- the campuses --- */
const clists = Object.values(campuses.campuses);
ok('four campuses, each with a name, city, region and tagline',
  campuses.count === 4 && clists.length === 4
  && clists.every((c) => c.name && c.city && c.region && c.tagline));
ok('exactly one campus is a hub: no home districts, no home halls',
  clists.filter((c) => c.districts.length === 0).length === 1
  && clists.filter((c) => c.districts.length === 0)
      .every((c) => c.halls.length === 0));
ok('the campuses partition the districts: every district trains at exactly one',
  (() => {
    const hosted = clists.flatMap((c) => c.districts);
    return hosted.length === districts.count && new Set(hosted).size === hosted.length
      && hosted.every((d) => districts.districts[d]);
  })());
ok("each campus's hall list is exactly its districts' halls, in district order",
  clists.every((c) => JSON.stringify(c.halls)
    === JSON.stringify(c.districts.flatMap((d) => districts.districts[d].halls))));
ok('the campus hall lists cover the whole roster exactly once',
  (() => {
    const all = clists.flatMap((c) => c.halls);
    return all.length === 111 && new Set(all).size === 111;
  })());
ok('the campus registry declares its siting honesty (planned, not surveyed)',
  /planned/.test(campuses.honesty.siting) && /no site has been surveyed/.test(campuses.honesty.siting));

/* ------------------------------------------------------------- chapters --- */
const chapters = JSON.parse(readFileSync(new URL('./registry/chapters.json', import.meta.url)));
ok('every union holds a home seat plus a regional chapter at each other campus',
  Object.keys(chapters.chapters).length === 111
  && chapters.count === 111 * 4
  && Object.values(chapters.chapters).every((c) =>
      Object.keys(c.regional).length === 3 && !(c.home in c.regional)));
ok('the hub campus is a regional chapter destination for every one of the 111 halls',
  (() => {
    const hub = Object.entries(campuses.campuses)
      .find(([, c]) => c.districts.length === 0)[0];
    return Object.values(chapters.chapters)
      .every((c) => hub in c.regional && c.home !== hub);
  })());
ok("each union's home campus is where its district actually trains",
  unions.unions.every((u) => {
    const camp = Object.entries(campuses.campuses)
      .find(([, c]) => c.districts.includes(u.district))[0];
    return chapters.chapters[u.slug].home === camp;
  }));
ok('chapter codes are unique across the whole network',
  (() => {
    const codes = Object.values(chapters.chapters).flatMap((c) =>
      [c.home_code, ...Object.values(c.regional).map((r) => r.code)]);
    return codes.length === 444 && new Set(codes).size === 444;
  })());
ok('hosted counts balance: a campus hosts every union it does not home',
  Object.entries(chapters.hosted).every(([ck, nHosted]) =>
    nHosted === 111 - campuses.campuses[ck].halls.length));
ok('the chapter honesty stands: an Academy structure, no local named',
  /not a claim/.test(chapters.honesty.chapters)
  && /no local\s+is named/.test(chapters.honesty.chapters));

/* ------------------------------------------------------------ freshness --- */
const src = readFileSync(new URL('./unions111.py', import.meta.url));
const stamp = createHash('sha256').update(src).digest('hex').slice(0, 16);
ok(`the registry was built from the current taxonomy (source stamp ${stamp})`,
  unions.source_stamp === stamp && districts.source_stamp === stamp
  && campuses.source_stamp === stamp && chapters.source_stamp === stamp);
ok('all four registry files came from the same build',
  unions.pack_version === districts.pack_version && unions.built === districts.built
  && campuses.pack_version === unions.pack_version && campuses.built === unions.built
  && chapters.pack_version === unions.pack_version && chapters.built === unions.built);

console.log(`unions/verify: ${n} checks passed — ${unions.count} unions, `
  + `${districts.count} districts, ${campuses.count} campuses, `
  + `${chapters.count} chapter seats`);
