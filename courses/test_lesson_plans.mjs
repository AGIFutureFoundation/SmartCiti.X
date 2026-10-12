/**
 * Teacher Lesson Planner v1 verification.
 *
 * Every plan is a PLANNED DRAFT derived from courses/registry/courses.json.
 * This proves the derivation: one plan per course and module, the four
 * stages in order, the minute arithmetic, every floor reference against the
 * registry that owns it, the beauty-course delivery status, the honesty
 * wording, and a byte-identical rebuild.
 */
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { FORBIDDEN } from '../brand/identity.mjs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const read = (p) => JSON.parse(readFileSync(new URL(p, import.meta.url)));
const regPath = new URL('./registry/lesson_plans.json', import.meta.url);
const regBytes = readFileSync(regPath, 'utf8');
const reg = JSON.parse(regBytes);
const courses = read('./registry/courses.json').courses;
const manifest = read('../pack/manifest.json');
const simIds = new Set(Object.keys(read('../sims/registry/sims.json').sims));
const stationIds = new Set(read('../stations/registry/stations.json').stations.map((s) => s.station_id));

const P = reg.plans;
const byCode = Object.fromEntries(P.map((p) => [p.code, p]));
const courseByCode = Object.fromEntries(courses.map((c) => [c.code, c]));
const STAGES = 'home,class,floor,gate';
const NO_FLOOR = 'no floor simulator is bound in this bundle yet — run the practice as a paper or demo exercise and record it as such';
const BEAUTY = 'home and class only in this bundle: the floor and gate stages need the separate Beauty School simulator, which is not part of this repository';
const NEG = /\b(?:no|not|none|nothing|never|neither|nor)\b/i;
const CLAIM = /accredited|endorsed|certified by|partnered with/i;
const sentences = (t) => t.replace(/\b(e\.g|i\.e|Art|No)\./g, '$1').split(/(?<=[.!?])\s+/);
function* strings(o) {
  if (typeof o === 'string') yield o;
  else if (Array.isArray(o)) for (const v of o) yield* strings(v);
  else if (o && typeof o === 'object') for (const v of Object.values(o)) yield* strings(v);
}
const weeks = P.flatMap((p) => p.weeks.map((w) => ({ p, w })));
const floorOf = (w) => w.stages.find((s) => s.stage === 'floor');

/* ------------------------------------------------------------- envelope --- */
ok('envelope: pack, product, built, source_stamp present',
  reg.pack === 'smartcitix-trade-craft-academy-lesson-plans'
  && reg.product === 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)'
  && /^\d{4}-\d{2}-\d{2}$/.test(reg.built) && /^[0-9a-f]{16}$/.test(reg.source_stamp));
ok(`pack_version equals the manifest (${manifest.pack_version})`, reg.pack_version === manifest.pack_version);
ok('honesty block says planned draft, not reviewed by a qualified instructor',
  /PLANNED DRAFT/.test(reg.honesty.status) && /reviewed by a qualified/.test(reg.honesty.status)
  && /no plan is accredited/.test(reg.honesty.marks));

/* ---------------------------------------------------------------- plans --- */
ok(`one plan per course (${courses.length}), same codes in the same order`,
  P.length === courses.length && P.map((p) => p.code).join() === courses.map((c) => c.code).join());
ok('one week per module: week n = module n, titles carried verbatim',
  courses.every((c) => {
    const p = byCode[c.code];
    return p.weeks.length === c.modules.length
      && c.modules.every((m, i) => p.weeks[i].week === i + 1 && p.weeks[i].module === m.n && p.weeks[i].title === m.title);
  }));
ok('every week has the four stages in order home,class,floor,gate',
  weeks.every(({ w }) => w.stages.map((s) => s.stage).join() === STAGES));
ok('assign text is the module stage text verbatim (no invented content)',
  courses.every((c) => c.modules.every((m, i) => byCode[c.code].weeks[i].stages
    .every((s) => s.assign === m.stages.find((x) => x.stage === s.stage).text))));
ok('mentor agents on every stage are exactly the course mentors from the registry',
  courses.every((c) => byCode[c.code].weeks.every((w) => w.stages
    .every((s) => s.mentors.join() === c.mentors.join() && s.mentors.length > 0))));

/* -------------------------------------------------------------- minutes --- */
ok('every minutes value is a non-negative integer',
  weeks.every(({ w }) => Number.isInteger(w.minutes) && w.stages.every((s) => Number.isInteger(s.minutes) && s.minutes >= 0)));
ok('stage minutes sum exactly to each module total',
  weeks.every(({ w }) => w.stages.reduce((a, s) => a + s.minutes, 0) === w.minutes));
ok('module minutes sum exactly to round(hours_planned*60) per course',
  courses.every((c) => {
    const p = byCode[c.code]; const t = Math.round(c.hours_planned * 60);
    return p.minutes_total === t && p.weeks.reduce((a, w) => a + w.minutes, 0) === t;
  }));
ok('module and stage splits are within one minute of the even / 20-30-35-15 shares',
  weeks.every(({ p, w }) => Math.abs(w.minutes - p.minutes_total / p.weeks.length) < 1
    && w.stages.every((s, i) => Math.abs(s.minutes - w.minutes * [20, 30, 35, 15][i] / 100) < 1)));

/* ---------------------------------------------------------------- floor --- */
ok('floor stage names only sims in sims.json and stations in stations.json, matching the course binding',
  courses.every((c) => byCode[c.code].weeks.every((w) => {
    const f = floorOf(w);
    return f.floor_sims.every((s) => simIds.has(s)) && f.class_stations.every((s) => stationIds.has(s))
      && f.floor_sims.join() === c.floor_sims.join() && f.class_stations.join() === c.class_stations.join()
      && f.floor_sims.every((s) => f.teacher_role.includes(s)) && f.class_stations.every((s) => f.teacher_role.includes(s));
  })));
ok('floor role uses the exact "no floor simulator" wording when nothing is bound, and only then',
  weeks.every(({ w }) => {
    const f = floorOf(w); const none = !f.floor_sims.length && !f.class_stations.length;
    return none ? f.teacher_role === NO_FLOOR : !f.teacher_role.includes('no floor simulator');
  }));
ok('gate role is unaided verification and not gamified',
  weeks.every(({ w }) => { const g = w.stages[3].teacher_role; return /unaided/.test(g) && /not gamified/.test(g); }));
ok('home role checks the prepare check; class role runs the analyze case',
  weeks.every(({ w }) => /prepare check/.test(w.stages[0].teacher_role) && /analyze case/.test(w.stages[1].teacher_role)));

/* ------------------------------------------------------- beauty courses --- */
const beauty = courses.filter((c) => c.halls.length === 0).map((c) => c.code);
ok(`hall-less courses are exactly TCA-210/220/230 and carry the beauty delivery_status (${beauty.join(', ')})`,
  beauty.join() === 'TCA-210,TCA-220,TCA-230' && beauty.every((k) => byCode[k].delivery_status === BEAUTY)
  && P.filter((p) => !beauty.includes(p.code)).every((p) => p.delivery_status !== BEAUTY));

/* -------------------------------------------------------------- honesty --- */
ok('catalog_section copied from the courses registry; coming-soon is exactly the hall-less beauty courses',
  P.every((p) => p.catalog_section === courseByCode[p.code].catalog_section)
  && P.filter((p) => p.catalog_section === 'coming-soon').map((p) => p.code).join() === beauty.join());
ok('wired weeks carry the module sites and wiring_note verbatim; unwired weeks carry neither',
  P.every((p) => p.weeks.every((w) => {
    const m = courseByCode[p.code].modules[w.module - 1];
    return w.wired === m.wired && (m.wired
      ? JSON.stringify(w.sites) === JSON.stringify(m.sites) && w.wiring_note === m.wiring_note
      : !('sites' in w) && !('wiring_note' in w));
  })));
ok('every plan carries a teacher_note marking it a planned draft not reviewed by a qualified instructor',
  P.every((p) => typeof p.teacher_note === 'string' && /planned draft/.test(p.teacher_note)
    && /not reviewed by a qualified instructor/.test(p.teacher_note) && p.status === 'planned draft'));
ok('no unnegated claim word (accredited|endorsed|certified by|partnered with) anywhere',
  [...strings(reg)].every((t) => sentences(t).every((s) => !CLAIM.test(s) || NEG.test(s))));
ok('brand spelled SmartCiti.X : Trade Craft Academy; no forbidden spellings',
  FORBIDDEN.every((f) => !regBytes.includes(f.wrong)) && regBytes.includes('SmartCiti.X : Trade Craft Academy'));

/* -------------------------------------------------------------- rebuild --- */
const here = fileURLToPath(new URL('.', import.meta.url));
const fresh = execFileSync('python3', [here + 'lesson_plans.py', '--stdout'], { encoding: 'utf8' });
ok('a fresh build (--stdout) is byte-identical to the committed registry', fresh === regBytes);

console.log(`lesson plans: ${n} checks passed`);
