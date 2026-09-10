/**
 * Schools pack verification.
 *
 * The flipped-classroom model is a set of claims about machinery this
 * repository actually ships, and the district records are claims about
 * the real world. Both are held to account: every stage must name a
 * subsystem that exists, every unit reference must resolve in the pack
 * that owns it, and every district record must carry the proposed-partner
 * honesty in full — a school program that overclaims fails its build.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { existsSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const reg = JSON.parse(readFileSync(new URL('./registry/schools.json', import.meta.url)));
const campuses = JSON.parse(readFileSync(new URL('../unions/registry/campuses.json', import.meta.url))).campuses;
const sims = JSON.parse(readFileSync(new URL('../sims/registry/sims.json', import.meta.url)));
const stations = new Set(JSON.parse(readFileSync(
  new URL('../stations/registry/stations.json', import.meta.url))).stations.map((s) => s.station_id));
const slugs = new Set(JSON.parse(readFileSync(
  new URL('../unions/registry/unions.json', import.meta.url))).unions.map((u) => u.slug));

/* ---------------------------------------------------------------- model --- */
ok('the flipped loop has its four stages in teaching order: home, class, floor, gate',
  reg.model.stages.map((s) => s.stage).join() === 'home,class,floor,gate'
  && /circulates instead of lecturing/.test(reg.model.loop));
ok('every stage names the subsystem that implements it, and that subsystem exists',
  reg.model.stages.every((s) => s.implemented_by.length > 5)
  && ['pack/', 'stations/', 'sims/'].every((dir) =>
      reg.model.stages.some((s) => s.implemented_by.includes(dir))
      && existsSync(new URL('../' + dir, import.meta.url))));
ok('the gate stage is deliberately ungamified, and says so',
  (() => { const g = reg.model.stages.find((s) => s.stage === 'gate');
    return /unaided/.test(g.what) && /ungamified/.test(g.gamified); })());

/* ---------------------------------------------------------------- bands --- */
ok('four grade bands in the Cognition.X vocabulary, Explorer through Lead',
  reg.bands.map((b) => b.level).join() === 'Explorer,Builder,Practitioner,Lead');
ok('Explorer is awareness-only: no machine seats below grade 6',
  (() => { const e = reg.bands.find((b) => b.level === 'Explorer');
    return e.tier === null && /no machine seats/.test(e.offer); })());
ok('the upper bands map onto real Academy tiers',
  reg.bands.filter((b) => b.tier !== null)
    .every((b) => ['fundamentals', 'applied', 'mastery'].includes(b.tier)));

/* ------------------------------------------------------------ districts --- */
ok('district records cover all three campus regions',
  new Set(reg.districts.map((d) => d.campus)).size === 3
  && reg.districts.every((d) => d.campus in campuses));
ok('every district is a PROPOSED partner and says so verbatim, with provenance',
  reg.districts.every((d) => /proposed partner/.test(d.status)
    && /no district has reviewed or agreed/.test(d.status)
    && /no agreement exists/.test(d.status)
    && /public record \(name only\)/.test(d.provenance)));
ok('the pack honesty refuses adoption and certification claims',
  /no agreement exists/.test(reg.honesty.districts)
  && /never\s+count toward certification/.test(reg.honesty.certification));

/* ---------------------------------------------------------------- units --- */
ok('one flipped unit per simulator-bound hall, exactly',
  reg.units.length === Object.keys(sims.hall_bindings).length
  && reg.units.every((u) => slugs.has(u.hall) && u.hall in sims.hall_bindings));
ok('every unit floor sim resolves in the sims registry and binds that hall',
  reg.units.every((u) => u.floor_sims.length > 0
    && u.floor_sims.every((id) => sims.sims[id]
      && sims.hall_bindings[u.hall].some((b) => b.sim === id))));
ok('every unit class station resolves in the stations registry',
  reg.units.every((u) => u.class_stations.every((id) => stations.has(id))));
ok('every unit gate demands the unaided run',
  reg.units.every((u) => /unaided/.test(u.gate) && /no sim hour counts/.test(u.gate)));

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`schools/test: ${n} checks passed — ${reg.model.stages.length}-stage model, `
  + `${reg.districts.length} proposed districts, ${reg.units.length} flipped units`);
