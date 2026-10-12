/**
 * Courses pack verification.
 *
 * The twelve courses are a PLANNED draft mapped onto machinery this
 * repository ships. Every mapping is a claim - a hall exists, a simulator
 * binds that hall, a station stands in it, a wired module runs on a real
 * site - and every one is proven here against the pack that owns it. The
 * draft's own honesty is held to account too: a course that claims credit,
 * accreditation or a partner it does not have fails its build.
 */
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { claimHits, verdict } from '../loop/honesty.mjs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const read = (p) => JSON.parse(readFileSync(new URL(p, import.meta.url)));
const regPath = new URL('./registry/courses.json', import.meta.url);
const regBytes = readFileSync(regPath, 'utf8');
const reg = JSON.parse(regBytes);
const manifest = read('../pack/manifest.json');
const draft = read('./draft/curriculum_2026q4.json');
const slugs = new Set(read('../unions/registry/unions.json').unions.map((u) => u.slug));
const sims = read('../sims/registry/sims.json');
const stationsReg = read('../stations/registry/stations.json').stations;
const stationHall = new Map(stationsReg.map((s) => [s.station_id, s.hall]));
const lessons = read('../lessons/registry/lessons.json').lessons;

const C = reg.courses;
const byCode = Object.fromEntries(C.map((c) => [c.code, c]));
const MENTORS = new Set(['Chris', 'Joyce', 'Tessa', 'Gemma', 'Iris', 'Dana', 'Sam']);
const NEG = /\b(?:no|not|none|nothing|never|neither|nor)\b/i;
const sentences = (t) => t.replace(/\b(e\.g|i\.e|Art|No)\./g, '$1').split(/(?<=[.!?])\s+/);
function* strings(o) {
  if (typeof o === 'string') yield o;
  else if (Array.isArray(o)) for (const v of o) yield* strings(v);
  else if (o && typeof o === 'object') for (const v of Object.values(o)) yield* strings(v);
}

/* ------------------------------------------------------------- envelope --- */
ok('registry envelope: pack, product, built, source_stamp present',
  reg.pack === 'smartcitix-trade-craft-academy-courses'
  && reg.product === 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)'
  && /^\d{4}-\d{2}-\d{2}$/.test(reg.built) && /^[0-9a-f]{16}$/.test(reg.source_stamp));
ok(`pack_version equals the manifest (${manifest.pack_version})`,
  reg.pack_version === manifest.pack_version);
ok('honesty block present and refuses status, credit, marks and mapping overclaims',
  /PLANNED DRAFT/.test(reg.honesty.status) && /never count toward/.test(reg.honesty.credit)
  && /no course is accredited/.test(reg.honesty.marks) && /not that the course content was reviewed/.test(reg.honesty.mapping));

/* -------------------------------------------------------------- courses --- */
ok('12 courses with unique TCA codes, matching the draft one to one',
  C.length === 12 && new Set(C.map((c) => c.code)).size === 12
  && C.every((c) => /^TCA-\d{3}$/.test(c.code))
  && draft.courses.map((d) => d.code).join() === C.map((c) => c.code).join());
ok('every course status is "planned draft"', C.every((c) => c.status === 'planned draft'));
ok('module count and titles carried verbatim from the draft',
  draft.courses.every((d) => {
    const c = byCode[d.code];
    return c.modules.length === d.modules.length
      && d.modules.every((m, i) => c.modules[i].title === m.title && c.modules[i].n === i + 1);
  }));
ok('every module has all four stages in order home,class,floor,gate with non-empty text',
  C.every((c) => c.modules.every((m) => m.stages.map((s) => s.stage).join() === 'home,class,floor,gate'
    && m.stages.every((s) => typeof s.text === 'string' && s.text.trim().length > 10))));
ok('stage text is the authored phase text: prepare->home, analyze->class, practice->floor, verify->gate',
  draft.courses.every((d) => d.modules.every((m, i) => byCode[d.code].modules[i].stages
    .every((s) => s.text === m.flipped[s.phase]
      && { prepare: 'home', analyze: 'class', practice: 'floor', verify: 'gate' }[s.phase] === s.stage))));

/* ---------------------------------------------------------------- halls --- */
ok('every hall slug resolves in unions/registry/unions.json',
  C.every((c) => c.halls.every((h) => slugs.has(h))));
ok('every trade course outside beauty names at least one hall',
  C.filter((c) => !c.roster_note).every((c) => c.halls.length > 0));
ok('core trade mapping: electricians, hvacr, welders, carpenters, heavy-equip as planned',
  byCode['TCA-110'].halls.includes('electricians') && byCode['TCA-130'].halls.includes('hvacr')
  && byCode['TCA-140'].halls.includes('welders') && byCode['TCA-150'].halls.includes('carpenters')
  && ['heavy-equip', 'operating-eng', 'survey-drone'].every((h) => byCode['TCA-160'].halls.includes(h))
  && ['TCA-310', 'TCA-320'].every((k) => byCode[k].halls.includes('robotics')));
ok('plumbing maps to pipefitters and carries a mapping_note that no plumbers hall exists',
  byCode['TCA-120'].halls.join() === 'pipefitters' && !slugs.has('plumbers')
  && /no plumbers hall/.test(byCode['TCA-120'].mapping_note));
ok('cosmetology, nail and esthetics courses have empty halls AND a Beauty School roster_note',
  ['TCA-210', 'TCA-220', 'TCA-230'].every((k) => byCode[k].halls.length === 0
    && byCode[k].floor_sims.length === 0 && byCode[k].class_stations.length === 0
    && /outside the 111-hall roster/.test(byCode[k].roster_note) && /Beauty School/.test(byCode[k].roster_note))
  && C.filter((c) => c.roster_note).length === 3);
ok('every course states what can run in this bundle; an empty floor is never silent',
  C.every((c) => typeof c.delivery_status === 'string' && c.delivery_status.length > 20)
  && ['TCA-210', 'TCA-220', 'TCA-230'].every((k) => /not part of this repository/.test(byCode[k].delivery_status))
  && C.filter((c) => !c.roster_note && !c.floor_sims.length && !c.class_stations.length)
      .every((c) => /no floor simulator/.test(c.delivery_status))
  && C.filter((c) => c.floor_sims.length || c.class_stations.length).every((c) => /all four stages/.test(c.delivery_status)));
ok('leadership is cross_hall with a stated reason',
  byCode['TCA-410'].cross_hall === true && byCode['TCA-410'].cross_hall_reason.length > 30);

/* ------------------------------------------------------- sims, stations --- */
ok('every floor_sim exists in sims.json and binds one of the course halls',
  C.every((c) => c.floor_sims.every((id) => sims.sims[id]
    && c.halls.some((h) => (sims.hall_bindings[h] || []).some((b) => b.sim === id)))));
ok('floor_sims are complete: every sim bound to a mapped hall is listed',
  C.every((c) => c.halls.every((h) => (sims.hall_bindings[h] || []).every((b) => c.floor_sims.includes(b.sim)))));
ok('every class_station exists in stations.json and stands in a mapped hall',
  C.every((c) => c.class_stations.every((id) => stationHall.has(id) && c.halls.includes(stationHall.get(id)))));
ok('class_stations are complete: every station in a mapped hall is listed',
  stationsReg.every((s) => C.every((c) => !c.halls.includes(s.hall) || c.class_stations.includes(s.station_id))));

/* ---------------------------------------------------------------- wired --- */
const wired = C.flatMap((c) => c.modules.filter((m) => m.wired).map((m) => [c.code, m]));
ok('exactly TCA-140 modules 1-2 are wired; every other module is wired:false',
  wired.map(([k, m]) => `${k}#${m.n}`).join() === 'TCA-140#1,TCA-140#2'
  && C.every((c) => c.modules.every((m) => typeof m.wired === 'boolean' && (m.wired || !('sites' in m)))));
ok('each wired module names at least one real site, and the weld-bead sim is among them',
  wired.every(([, m]) => m.sites.length > 0
    && m.sites.some((s) => s.kind === 'sim' && s.id === 'weld-bead')
    && m.sites.every((s) => (s.kind === 'sim' && sims.sims[s.id])
      || (s.kind === 'station' && stationHall.has(s.id))
      || (s.kind === 'lesson' && lessons[s.id] && byCode['TCA-140'].halls.includes(lessons[s.id].hall)))));

/* -------------------------------------------------------------- honesty --- */
ok('every course carries a licensure_note that does not claim credit',
  C.every((c) => typeof c.licensure_note === 'string' && c.licensure_note.length > 20
    && sentences(c.licensure_note).every((s) => !/counts? toward licen/i.test(s) || NEG.test(s))
    && /planned|no |not|nothing/i.test(c.licensure_note)));
ok('no forbidden claim anywhere in the registry (shared loop/honesty.json vocabulary, positional negation)',
  [...strings(reg)].every((t) => claimHits(t).length === 0));
{
  const fx = read('../loop/registry/honesty_fixtures.json').cases;
  ok(`the shared honesty scanner returns the expected verdict on all ${fx.length} corpus cases`,
    fx.length >= 16 && fx.every((c) => verdict(c.text) === c.expect));
  const py = JSON.parse(execFileSync('python3', [fileURLToPath(new URL('./build.py', import.meta.url)), '--scan-fixtures'],
    { encoding: 'utf8' }));
  ok('the Python scanner (build.py --scan-fixtures) gives the identical verdict on every corpus case',
    py.length === fx.length && py.every((v, i) => v === verdict(fx[i].text) && v === fx[i].expect));
}
ok('brand spelling: SmartCiti with an i, no SmartCity anywhere in the registry or builder',
  !/SmartCity/i.test(regBytes) && !/SmartCity/i.test(readFileSync(new URL('./build.py', import.meta.url), 'utf8'))
  && regBytes.includes('SmartCiti.X : Trade Craft Academy'));

/* -------------------------------------------------------------- mentors --- */
ok('mentors drawn only from {Chris, Joyce, Tessa, Gemma, Iris, Dana, Sam}, every course has one',
  C.every((c) => c.mentors.length > 0 && c.mentors.every((m) => MENTORS.has(m)))
  && reg.agent_assist.every((a) => MENTORS.has(a.agent))
  && [...reg.teacher_kit, ...reg.student_kit].every((k) =>
    (k.agent.match(/[A-Z][a-z]+/g) || []).every((m) => MENTORS.has(m))));
ok('teacher_kit, student_kit and agent_assist copied verbatim from the draft',
  JSON.stringify(reg.teacher_kit) === JSON.stringify(draft.teacher_kit)
  && JSON.stringify(reg.student_kit) === JSON.stringify(draft.student_kit)
  && JSON.stringify(reg.agent_assist) === JSON.stringify(draft.agent_assist));

/* -------------------------------------------------------------- sprints --- */
const day = 86400000;
ok('sprints S1..S8 are contiguous 14-day windows starting 2026-10-12',
  reg.sprints.map((s) => s.sprint).join() === 'S1,S2,S3,S4,S5,S6,S7,S8'
  && reg.sprints[0].start === '2026-10-12'
  && reg.sprints.every((s, i) => (Date.parse(s.end) - Date.parse(s.start)) / day === 13
    && (i === 0 || (Date.parse(s.start) - Date.parse(reg.sprints[i - 1].end)) / day === 1)));
ok('sprint status comes from a closed set; a shipped sprint states its gate result, a planned one does not',
  reg.sprints.every((s) => ['planned', 'in-progress', 'shipped', 'slipped', 'cancelled'].includes(s.status))
  && reg.sprints.every((s) => (s.status === 'shipped') === (typeof s.gate_result === 'string' && s.gate_result.length > 10))
  && /^not met/.test(reg.sprints.find((s) => s.sprint === 'S2').gate_result));
ok('the S8 pilot carries its preconditions as a field, naming a partner, a consent plan and EV-09',
  (() => { const p = reg.sprints.find((s) => s.sprint === 'S8').preconditions || [];
    return p.some((x) => /partner/.test(x)) && p.some((x) => /consent/.test(x)) && p.some((x) => /EV-09/.test(x)); })());
ok('every sprint carries its authored ship line and eval gate',
  reg.sprints.every((s, i) => s.ship === draft.rapid_roadmap[i].ship
    && s.eval_gate === draft.rapid_roadmap[i].eval_gate));

/* -------------------------------------------------------------- rebuild --- */
const here = fileURLToPath(new URL('.', import.meta.url));
const src = Buffer.concat([readFileSync(new URL('./build.py', import.meta.url)),
  readFileSync(new URL('./draft/curriculum_2026q4.json', import.meta.url))]);
ok('the registry was built from the current builder and draft (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));
const fresh = execFileSync('python3', [here + 'build.py', '--stdout'], { encoding: 'utf8' });
ok('the registry is byte-identical to a fresh build', fresh === regBytes);

const nMods = C.reduce((a, c) => a + c.modules.length, 0);
console.log(`courses/test: ${n} checks passed — ${C.length} planned courses, ${nMods} modules, `
  + `${wired.length} wired, ${reg.sprints.length} sprints`);
