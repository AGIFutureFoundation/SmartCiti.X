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

/* ------------------------------------------------------------ freshness --- */
const src = readFileSync(new URL('./unions111.py', import.meta.url));
const stamp = createHash('sha256').update(src).digest('hex').slice(0, 16);
ok(`the registry was built from the current taxonomy (source stamp ${stamp})`,
  unions.source_stamp === stamp && districts.source_stamp === stamp);
ok('both registry files came from the same build',
  unions.pack_version === districts.pack_version && unions.built === districts.built);

console.log(`unions/verify: ${n} checks passed — ${unions.count} unions, ${districts.count} districts`);
