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
const page = readFileSync(new URL('../web/trade_craft_3d.html', import.meta.url), 'utf8');
const campuses = JSON.parse(readFileSync(new URL('../unions/registry/campuses.json', import.meta.url))).campuses;
const sims = JSON.parse(readFileSync(new URL('../sims/registry/sims.json', import.meta.url)));
const stations = new Set(JSON.parse(readFileSync(
  new URL('../stations/registry/stations.json', import.meta.url))).stations.map((s) => s.station_id));
const slugs = new Set(JSON.parse(readFileSync(
  new URL('../unions/registry/unions.json', import.meta.url))).unions.map((u) => u.slug));
const tools = JSON.parse(readFileSync(
  new URL('../tools/registry/toolcribs.json', import.meta.url)));

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
ok("the class stage carries the crib drill, and every unit's drill is its own district's",
  /crib drill/.test(reg.model.stages.find((s) => s.stage === 'class').what)
  && reg.units.every((u) => u.class_drill === tools.hall_bindings[u.hall].district
      && u.class_drill in tools.cribs));
ok('every unit gate demands the unaided run',
  reg.units.every((u) => /unaided/.test(u.gate) && /no sim hour counts/.test(u.gate)));

/* ------------------------------------------------------------- the page --- */
// this pack used to have zero presence in the live app - only the wiki
// ever showed it. These checks are the drift guard: every district, every
// flipped unit and the honesty text this registry declares must actually
// reach the Schools panel, and each unit must click through to its hall.
ok('the page builds the Schools panel and trims the registry into D.schools',
  page.includes('function openSchools(') && page.includes('"schools":{'));
ok('every proposed district is named in the page, with its status verbatim',
  reg.districts.every((d) => page.includes(d.district))
  && page.includes(reg.districts[0].status));
ok('the flipped-unit rows build a working hall click-through, and every unit reaches D.schools',
  page.includes('data-hall-goto="${esc(u.hall)}"')
  && page.includes('showHall(hg.dataset.hallGoto)')
  && reg.units.every((u) => page.includes(`"hall":"${u.hall}"`)));
ok('the schools honesty text reaches the page verbatim',
  page.includes(reg.honesty.districts) && page.includes(reg.honesty.certification));
ok('the reverse direction is wired too: a hall panel links back to its own flipped unit',
  page.includes('D.schools.units.find((u) => u.hall === sg)')
  && page.includes('data-schools-hall="${esc(sg)}"')
  && page.includes('openSchools(sh.dataset.schoolsHall)'));

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`schools/test: ${n} checks passed — ${reg.model.stages.length}-stage model, `
  + `${reg.districts.length} proposed districts, ${reg.units.length} flipped units`);
