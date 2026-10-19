/**
 * Courses pack verification.
 *
 * The twelve courses are a PLANNED draft mapped onto machinery this
 * repository ships. Every mapping is a claim - a hall exists, a simulator
 * binds that hall, a station stands in it, a wired module runs on a real
 * site - and every one is proven here against the pack that owns it. The
 * draft's own honesty is held to account too: a course that claims credit,
 * an accrediting body or a partner it does not have fails its build.
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
const cribs = read('../tools/registry/toolcribs.json');

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
  && C.filter((c) => c.floor_sims.length).every((c) => /all four stages/.test(c.delivery_status))
  && C.filter((c) => !c.roster_note).every((c) => !/all four stages/.test(c.delivery_status) || c.floor_sims.length > 0));
ok('a course with class stations but no floor sim (TCA-410) is station-only, not "all four stages"',
  C.filter((c) => !c.floor_sims.length && c.class_stations.length).map((c) => c.code).join() === 'TCA-410'
  && /class stations are bound but no floor simulator/.test(byCode['TCA-410'].delivery_status)
  && byCode['TCA-410'].catalog_section === 'home-and-class');
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
const WIRED_SET = 'TCA-110#1,TCA-120#4,TCA-130#1,TCA-140#1,TCA-140#2,TCA-150#1';
ok(`exactly ${WIRED_SET} are wired; every other module is wired:false with no sites`,
  wired.map(([k, m]) => `${k}#${m.n}`).join() === WIRED_SET
  && C.every((c) => c.modules.every((m) => typeof m.wired === 'boolean' && (m.wired || !('sites' in m)))));
const siteResolves = (code, s) => {
  const halls = byCode[code].halls;
  if (s.kind === 'sim') return !!sims.sims[s.id] && halls.some((h) => (sims.hall_bindings[h] || []).some((b) => b.sim === s.id));
  if (s.kind === 'station') return stationHall.has(s.id) && halls.includes(stationHall.get(s.id));
  if (s.kind === 'lesson') return !!lessons[s.id] && halls.includes(lessons[s.id].hall);
  if (s.kind === 'crib') return !!cribs.cribs[s.id]
    && halls.some((h) => cribs.hall_bindings[h] && cribs.hall_bindings[h].district === s.id)
    && cribs.cribs[s.id].tools.some((t) => t.id === s.tool)
    && cribs.drills[s.id].some((d) => d.tool === s.tool);
  return false;
};
ok('every site id of every wired module resolves in the registry that owns it and binds a course hall',
  wired.length > 0 && wired.every(([k, m]) => m.sites.length > 0 && m.sites.every((s) => siteResolves(k, s))));
ok('the welding slice still runs on the weld-bead sim',
  wired.filter(([k]) => k === 'TCA-140').every(([, m]) => m.sites.some((s) => s.kind === 'sim' && s.id === 'weld-bead')));
ok('every wired module explains its match in a wiring_note; unwired modules carry none',
  C.every((c) => c.modules.every((m) => (m.wired ? typeof m.wiring_note === 'string' && m.wiring_note.length > 30 : !('wiring_note' in m)))));
ok('TCA-110 m1 is matched to the multimeter drill pick and TCA-130 m1 to the manifold gauge and the hvacr lesson',
  byCode['TCA-110'].modules[0].sites.some((s) => s.kind === 'crib' && s.tool === 'multimeter')
  && /multimeter|meter/i.test(byCode['TCA-110'].modules[0].title)
  && byCode['TCA-130'].modules[0].sites.some((s) => s.kind === 'crib' && s.tool === 'manifold-gauge')
  && byCode['TCA-130'].modules[0].sites.some((s) => s.kind === 'lesson' && s.id === 'hvacr-prove-the-sequence')
  && byCode['TCA-130'].modules[0].stages.some((st) => /manifold gauges/.test(st.text)));
ok('TCA-110 and TCA-130 each state a wiring_gap naming what is missing for their unwired modules',
  ['TCA-110', 'TCA-130'].every((k) => typeof byCode[k].wiring_gap === 'string'
    && byCode[k].modules.some((m) => !m.wired) && /modules 2-5 are unwired/.test(byCode[k].wiring_gap))
  && /no hvacr simulator or class station exists/.test(byCode['TCA-130'].wiring_gap)
  && !sims.hall_bindings.hvacr && !stationsReg.some((s) => s.hall === 'hvacr'));

ok('S4: TCA-120 m4 is matched to the pipe-wrench pick, TCA-150 m1 to the chalk-line pick and the carpenters crib lesson',
  byCode['TCA-120'].modules[3].sites.length === 1
  && byCode['TCA-120'].modules[3].sites.some((s) => s.kind === 'crib' && s.id === 'systems' && s.tool === 'pipe-wrench')
  && /sediment trap/.test(byCode['TCA-120'].modules[3].stages[2].text)
  && byCode['TCA-150'].modules[0].sites.some((s) => s.kind === 'crib' && s.id === 'envelope' && s.tool === 'chalk-line')
  && byCode['TCA-150'].modules[0].sites.some((s) => s.kind === 'lesson' && s.id === 'carpenters-return-it-the-same')
  && /chalk line|snap wall lines/i.test(byCode['TCA-150'].modules[0].stages.map((x) => x.text).join(' ')));
ok('S4: TCA-120, TCA-150 and TCA-220 each state a wiring_gap; TCA-220 (coming-soon) has no wired module',
  ['TCA-120', 'TCA-150', 'TCA-220'].every((k) => typeof byCode[k].wiring_gap === 'string' && byCode[k].wiring_gap.length > 60)
  && /modules 1-3 are unwired/.test(byCode['TCA-120'].wiring_gap) && /modules 2-5 are unwired/.test(byCode['TCA-150'].wiring_gap)
  && /scaffold-bay/.test(byCode['TCA-150'].wiring_gap)
  && byCode['TCA-220'].modules.every((m) => !m.wired) && /no module is wired/.test(byCode['TCA-220'].wiring_gap)
  && !sims.hall_bindings.pipefitters && !stationsReg.some((s) => s.hall === 'pipefitters'));
// The Wave 16 lessons ladder now carries one pipefitters lesson; the roadmap pack's
// TCA-120 wiring has not been re-reviewed against it, so no claim is made either way here.


/* ------------------------------------------------------------- catalog --- */
const SECTIONS = ['available', 'home-and-class', 'coming-soon'];
ok('every course has a catalog_section from the closed set available / home-and-class / coming-soon',
  C.every((c) => SECTIONS.includes(c.catalog_section)));
ok('catalog_section follows the bundle: available iff a floor sim is bound, home-and-class otherwise, outside beauty',
  C.filter((c) => !c.roster_note).every((c) => c.catalog_section
    === (c.floor_sims.length ? 'available' : 'home-and-class'))
  && C.filter((c) => c.catalog_section === 'available').every((c) => /all four stages/.test(c.delivery_status))
  && C.filter((c) => c.catalog_section === 'home-and-class').every((c) => /no floor simulator/.test(c.delivery_status)));
ok('coming-soon is exactly TCA-210/220/230, held out of the main catalog until a sprint commits to Beauty School, nothing deleted',
  C.filter((c) => c.catalog_section === 'coming-soon').map((c) => c.code).join() === 'TCA-210,TCA-220,TCA-230'
  && ['TCA-210', 'TCA-220', 'TCA-230'].every((k) => /held out of the main catalog until a sprint commits to Beauty School/.test(byCode[k].catalog_note)
    && /nothing is deleted/.test(byCode[k].catalog_note) && byCode[k].modules.length > 0)
  && C.filter((c) => c.catalog_section !== 'coming-soon').every((c) => !('catalog_note' in c)));
ok('plumbing mapping carries mapping_review 2026-10-12 and a re-review-on-roster-change note',
  byCode['TCA-120'].mapping_review === '2026-10-12'
  && /re-reviewed whenever the hall roster/.test(byCode['TCA-120'].mapping_review_note));

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
const noStatus = (xs) => xs.map(({ status, ...k }) => k);
ok('teacher_kit, student_kit and agent_assist copied verbatim from the draft (kits add only a status field)',
  JSON.stringify(noStatus(reg.teacher_kit)) === JSON.stringify(draft.teacher_kit)
  && JSON.stringify(noStatus(reg.student_kit)) === JSON.stringify(draft.student_kit)
  && JSON.stringify(reg.agent_assist) === JSON.stringify(draft.agent_assist));

ok('every teacher and student kit item carries a status; only items with code here are called built, and synthetic ones say so',
  [...reg.teacher_kit, ...reg.student_kit].every((k) => typeof k.status === 'string'
    && (k.status === 'planned' || /built/.test(k.status)))
  && [...reg.teacher_kit, ...reg.student_kit].filter((k) => /dashboard|skill map/i.test(k.name)).every((k) => /SYNTHETIC/.test(k.status))
  && [...reg.teacher_kit, ...reg.student_kit].filter((k) => k.status !== 'planned').length === 4);

/* -------------------------------------------------------------- sprints --- */
const day = 86400000;
ok('sprints S1..S8 are contiguous 14-day windows starting 2026-10-12',
  reg.sprints.map((s) => s.sprint).join() === 'S1,S2,S3,S4,S5,S6,S7,S8'
  && reg.sprints[0].start === '2026-10-12'
  && reg.sprints.every((s, i) => (Date.parse(s.end) - Date.parse(s.start)) / day === 13
    && (i === 0 || (Date.parse(s.start) - Date.parse(reg.sprints[i - 1].end)) / day === 1)));
ok('sprint status comes from a closed set; a sprint whose gate ran states its result and what is and is not built; none is "shipped" before its window closes',
  reg.sprints.every((s) => ['planned', 'in-progress', 'gate-run-early', 'shipped', 'slipped', 'cancelled'].includes(s.status))
  // A gate run is recorded by in-progress, gate-run-early and shipped; those need a result and build lists.
  // planned never has one; slipped or cancelled may or may not, depending on whether a gate ran first.
  && reg.sprints.every((s) => {
    const ran = typeof s.gate_result === 'string' && s.gate_result.length > 10;
    if (['in-progress', 'gate-run-early', 'shipped'].includes(s.status)) return ran && Array.isArray(s.built) && s.built.length > 0 && Array.isArray(s.not_built);
    if (s.status === 'planned') return s.gate_result === null && !('built' in s);
    return !ran || (Array.isArray(s.built) && Array.isArray(s.not_built));
  })
  && reg.sprints.every((s) => s.status !== 'shipped' || (Date.parse(s.end) < Date.parse(reg.built) && s.not_built.length === 0))
  && reg.sprints.every((s) => s.status !== 'gate-run-early' || Date.parse(s.start) > Date.parse('2026-10-12'))
  && /held-out/.test(reg.sprints.find((s) => s.sprint === 'S2').gate_result)
  && /do not generalise/.test(reg.sprints.find((s) => s.sprint === 'S2').gate_result)
  && /1,342 of 1,342/.test(reg.sprints.find((s) => s.sprint === 'S3').gate_result));
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
console.log(`courses_roadmap/test: ${n} checks passed — ${C.length} planned courses, ${nMods} modules, `
  + `${wired.length} wired, ${reg.sprints.length} sprints`);
