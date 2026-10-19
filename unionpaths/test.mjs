/* unionpaths/test.mjs - one ordered path per union hall, checked against the registries it is derived from.
 * Browser-free, network-free. Recompute, never re-read: every hall's lessons are regathered from lessons.json and
 * re-sorted by the ladder, its seats, crib, advisor and crews are re-derived from their own registries, the rollups are
 * recounted, and the honesty lines are compared verbatim with the registries that wrote them. */
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (m, c, why) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m + (why !== undefined ? ' :: ' + JSON.stringify(why).slice(0, 500) : '')); } };
const J = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));
const sha = (b) => createHash('sha256').update(b).digest('hex').slice(0, 16);
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

const reg = J('unionpaths/registry/union_paths.json');
const UREG = J('unions/registry/unions.json'), U = UREG.unions, DIST = J('unions/registry/districts.json').districts;
const CH = J('unions/registry/chapters.json'), CAMP = J('unions/registry/campuses.json');
const CREG = J('courses/registry/courses.json'), C = CREG.courses, SUP = CREG.supplements;
const LES = J('lessons/registry/lessons.json'), LORDER = Object.keys(LES.lessons), DEPTH = LES.ladder.depth;
const CRIBS = J('tools/registry/toolcribs.json'), ADV = J('agents/registry/advisors.json').advisors, CREWS = J('agents/registry/crews.json').crews;
const AG = Object.fromEntries(J('hive/registry/hive.json').agents.map((a) => [a.id, a]));
const H = reg.halls, HBY = Object.fromEntries(H.map((h) => [h.hall, h]));

/* ---- provenance ---- */
ok('the registry is the union-paths pack, schema tc-union-paths/1, its stamp is sha256(unionpaths/build.py)',
  reg.pack === 'smartcitix-union-paths' && reg.schema === 'tc-union-paths/1' && reg.source_stamp === sha(readFileSync(join(HERE, 'build.py'))));
ok(`every source is stamped with its current sha256 (${reg.sources.length} sources: unions, courses, cribs, advisors, crews, hive)`,
  reg.sources.length === 9 && reg.sources.every((s) => existsSync(join(ROOT, s.path)) && s.sha256 === sha(readFileSync(join(ROOT, s.path)))),
  reg.sources.filter((s) => !existsSync(join(ROOT, s.path)) || s.sha256 !== sha(readFileSync(join(ROOT, s.path)))).map((s) => s.path));

/* ---- one path per hall ---- */
ok(`one path per union hall, in the union registry order (${U.length})`, H.length === U.length && U.length === UREG.count && H.every((h, i) => h.hall === U[i].slug && h.index === U[i].index));
ok('each hall carries the union registry\'s own name, focus, district and cohort (READ)',
  H.every((h, i) => h.name === U[i].name && h.focus === U[i].focus && h.district === U[i].district && h.cohort === U[i].cohort
    && h.district_name === DIST[h.district].name), H.filter((h, i) => h.name !== U[i].name || h.district !== U[i].district).map((h) => h.hall));
ok('each path starts at the hall\'s own trade course, which names the hall (111 trade courses, each used once)',
  H.every((h) => h.path[0].kind === 'course' && h.path[0].ref === h.course && C[h.course] && C[h.course].kind === 'trade' && C[h.course].hall === h.hall)
  && new Set(H.map((h) => h.course)).size === Object.values(C).filter((c) => c.kind === 'trade').length);
const ladder = (slug) => LORDER.filter((id) => LES.lessons[id].hall === slug)
  .sort((a, b) => DEPTH[a] - DEPTH[b] || LORDER.indexOf(a) - LORDER.indexOf(b));
const badL = H.filter((h) => !eq(h.lessons.map((l) => l.lesson), ladder(h.hall)));
ok('each hall\'s lessons are every lesson standing in it, re-sorted here by ladder depth then the lessons registry order', badL.length === 0, badL.map((h) => h.hall));
ok(`every lesson appears in exactly one hall path and has a supplement (${LORDER.length} lessons)`,
  H.flatMap((h) => h.lessons.map((l) => l.lesson)).sort().join() === [...LORDER].sort().join() && H.every((h) => h.lessons.every((l) => SUP[l.lesson])));
ok('each lesson row reads its title, room, tier, depth and step count from the lessons registry',
  H.every((h) => h.lessons.every((l) => { const L = LES.lessons[l.lesson];
    return l.title === L.title && l.room_label === L.room_label && l.tier === L.tier && l.strand === L.strand && l.depth === DEPTH[l.lesson] && l.steps === L.steps.length; })));
ok('each hall\'s seats are its course\'s bound seats in registry order, and every seat a lesson uses is among them',
  H.every((h) => { const st = C[h.course].seat_time; return eq(h.seats.map((s) => s.sim), st.seats_bound)
    && st.seats_in_lessons.every((s) => st.seats_bound.includes(s)) && h.seats.every((s) => s.name === st.seat_names[s.sim]); }));
ok('each hall\'s tool crib is the one toolcribs.json binds it to, and it is the hall\'s own district crib',
  H.every((h) => h.crib.crib === CRIBS.hall_bindings[h.hall].district && h.crib.crib === h.district
    && h.crib.name === CRIBS.cribs[h.crib.crib].name && h.crib.skill_id === CRIBS.hall_bindings[h.hall].skill_id));
const advOf = (h) => { const named = [];
  ladder(h.hall).forEach((l) => SUP[l].where.advisors.forEach((a) => { if (!named.includes(a.id)) named.push(a.id); }));
  return named.length ? { id: 'advisor:' + named[0], rule: 'lessons', also: named.slice(1).map((a) => 'advisor:' + a) } : { id: 'advisor:guide', rule: 'door', also: [] }; };
const badA = H.filter((h) => { const a = advOf(h); return h.advisor.id !== a.id || h.advisor.rule !== a.rule || !eq(h.advisor.also, a.also); });
ok('each hall\'s advisor is the first one its lessons send a learner to, in ladder order; with none, the door guide', badA.length === 0, badA.map((h) => h.hall));
ok('the door guide really stands at the door (advisors.json), and every advisor named is an Omega Hive advisor with that name',
  ADV.guide.stands_in === 'door' && H.every((h) => AG[h.advisor.id] && AG[h.advisor.id].kind === 'advisor' && AG[h.advisor.id].name === h.advisor.name
    && h.advisor.also.every((a) => AG[a] && AG[a].kind === 'advisor')));
const crewsOf = (slug) => Object.entries(CREWS).filter(([, v]) => v.halls.includes(slug)).map(([k]) => k);
ok('each hall\'s crews are every crew whose halls list names it, in registry order, each running a seat the hall has bound',
  H.every((h) => eq(h.crews.map((c) => c.crew), crewsOf(h.hall)) && h.crews.every((c) => c.seat === CREWS[c.crew].seat && h.seats.some((s) => s.sim === c.seat))));
ok('each crew lists its roles as Omega Hive crew-role ids, in the crew registry\'s roster order',
  H.every((h) => h.crews.every((c) => eq(c.roles, Object.keys(CREWS[c.crew].roles).map((r) => `crew:${c.crew}:${r}`))
    && c.roles.every((r) => AG[r] && AG[r].kind === 'crew-role' && AG[r].crew === c.crew))));
const SHAPE = /^course(,lesson)+(,seat)*,crib,advisor(,crew)*$/;
ok('each path runs course, lessons, seats, crib, advisor, crews - numbered 1..n, each ref the hall\'s own record',
  H.every((h) => SHAPE.test(h.path.map((p) => p.kind).join(',')) && h.path.every((p, i) => p.step === i + 1)
    && eq(h.path.map((p) => p.ref), [h.course, ...h.lessons.map((l) => l.lesson), ...h.seats.map((s) => s.sim), h.crib.crib, h.advisor.id, ...h.crews.map((c) => c.crew)])),
  H.filter((h) => !SHAPE.test(h.path.map((p) => p.kind).join(','))).map((h) => h.hall));
ok('each hall\'s counts are recounted from its own path',
  H.every((h) => h.counts.lessons === h.lessons.length && h.counts.seats === h.seats.length && h.counts.crews === h.crews.length
    && h.counts.steps === h.lessons.reduce((a, l) => a + l.steps, 0) && h.counts.crew_roles === h.crews.reduce((a, c) => a + c.roles.length, 0)
    && h.counts.path_steps === h.path.length));
ok('each hall links to its hall in 3D, its course, one supplement per lesson, its advisor on the Hive page and its ladder - all real pages',
  H.every((h) => h.links.hall3d === `web/trade_craft_3d.html?hall=${h.hall}` && h.links.course === `web/trade_craft_courses.html?course=${h.course}#course-trade`
    && eq(h.links.supplements, h.lessons.map((l) => `web/trade_craft_courses.html?lesson=${l.lesson}#course-sup`))
    && h.links.advisor === `web/trade_craft_hive.html?agent=${h.advisor.id}` && h.links.ladder === `web/trade_craft_ladder.html?hall=${h.hall}`)
  && ['trade_craft_3d.html', 'trade_craft_courses.html', 'trade_craft_hive.html', 'trade_craft_ladder.html'].every((f) => existsSync(join(ROOT, 'web', f))));

/* ---- rollups ---- */
const firsts = (xs) => xs.filter((x, i) => xs.indexOf(x) === i);
const roll = (hs) => ({ halls: hs.map((h) => h.hall), count: hs.length, lessons: hs.reduce((a, h) => a + h.lessons.length, 0),
  steps: hs.reduce((a, h) => a + h.counts.steps, 0), halls_with_seats: hs.filter((h) => h.seats.length).length,
  halls_with_crews: hs.filter((h) => h.crews.length).length, halls_door_advisor: hs.filter((h) => h.advisor.rule === 'door').length,
  seats: firsts(hs.flatMap((h) => h.seats.map((s) => s.sim))), crews: firsts(hs.flatMap((h) => h.crews.map((c) => c.crew))),
  advisors: firsts(hs.map((h) => h.advisor.id)) });
const sub = (r) => Object.fromEntries(['halls', 'count', 'lessons', 'steps', 'halls_with_seats', 'halls_with_crews', 'halls_door_advisor', 'seats', 'crews', 'advisors'].map((k) => [k, r[k]]));
ok(`one rollup per district, in districts.json order, its halls the district's own (${Object.keys(DIST).length})`,
  eq(reg.by_district.map((d) => d.district), Object.keys(DIST)) && reg.by_district.every((d) => eq([...d.halls].sort(), [...DIST[d.district].halls].sort()) && d.name === DIST[d.district].name));
ok('each district rollup is recounted here: halls, lessons, steps, seats, crews, door guides, advisors and cohorts',
  reg.by_district.every((d) => { const hs = H.filter((h) => h.district === d.district);
    return eq(sub(d), roll(hs)) && eq(d.cohorts, Object.fromEntries(Object.keys(UREG.cohorts).map((k) => [k, hs.filter((h) => h.cohort === k).length])))
      && Object.values(d.advisor_halls).reduce((a, n) => a + n, 0) === hs.length; }),
  reg.by_district.filter((d) => !eq(sub(d), roll(H.filter((h) => h.district === d.district)))).map((d) => d.district));
ok(`one rollup per cohort, each hall count equal to unions.json#cohorts (${Object.entries(UREG.cohorts).map(([k, n]) => k + ' ' + n).join(', ')})`,
  eq(reg.by_cohort.map((c) => c.cohort), Object.keys(UREG.cohorts)) && reg.by_cohort.every((c) => c.count === UREG.cohorts[c.cohort]));
ok('each cohort rollup is recounted here, with its per-district split',
  reg.by_cohort.every((c) => { const hs = H.filter((h) => h.cohort === c.cohort);
    return eq(sub(c), roll(hs)) && eq(c.districts, Object.fromEntries(Object.keys(DIST).map((d) => [d, hs.filter((h) => h.district === d).length]))); }));
const T = reg.counts;
ok(`the totals are recounted (${T.halls} halls, ${T.lessons} lessons, ${T.path_steps} path steps, ${T.halls_with_seats} with seats, ${T.halls_with_crews} with crews, ${T.halls_door_advisor} door guides)`,
  T.halls === H.length && T.lessons === LORDER.length && T.path_steps === H.reduce((a, h) => a + h.path.length, 0)
  && T.halls_with_seats === H.filter((h) => h.seats.length).length && T.halls_with_crews === H.filter((h) => h.crews.length).length
  && T.halls_door_advisor === H.filter((h) => h.advisor.rule === 'door').length && T.halls_lesson_advisor + T.halls_door_advisor === H.length
  && T.steps === H.reduce((a, h) => a + h.counts.steps, 0) && T.districts === reg.by_district.length && T.cohorts === reg.by_cohort.length);

/* ---- honesty ---- */
const want = [...Object.entries(UREG.honesty).map(([k, v]) => ['unions/registry/unions.json#honesty.' + k, v]),
  ...Object.entries(CH.honesty).map(([k, v]) => ['unions/registry/chapters.json#honesty.' + k, v]),
  ...Object.entries(CAMP.honesty).map(([k, v]) => ['unions/registry/campuses.json#honesty.' + k, v]),
  ['courses/registry/courses.json#honesty.content', CREG.honesty.content], ['courses/registry/courses.json#honesty.not_certification', CREG.honesty.not_certification]];
ok(`the registries' own honesty lines are quoted verbatim with their source paths (${want.length})`, eq(reg.honesty_quoted.map((q) => [q.source, q.text]), want));
ok('the pack says no union named is a partner or affiliate, nothing is invented, and real programmes stay PROPOSED',
  /not a partner, sponsor or affiliate/.test(reg.honesty.not_partner) && /no real local is named/.test(reg.honesty.not_partner)
  && /No apprenticeship hours, wages, credentials, membership or affiliation/.test(reg.honesty.nothing_invented)
  && /PROPOSED/.test(reg.honesty.programmes) && /no agreement exists/.test(reg.honesty.programmes) && /SCRIPTED: no AI model/.test(reg.honesty.voice));
const FORBID = /\b(hours?|wages?|salar(y|ies)|pay rate|per hour|credential(s|ed)?|certif\w*|membership|affiliat\w*|apprenticeship|journeyman|journeyworker|union dues|local \d+)\b|\$\s?\d/i;
const strs = (x) => typeof x === 'string' ? [x] : Array.isArray(x) ? x.flatMap(strs) : x && typeof x === 'object' ? Object.entries(x).flatMap(([k, v]) => [k.replace(/[_-]/g, ' '), ...strs(v)]) : [];
const hits = [...H, ...reg.by_district, ...reg.by_cohort].flatMap((r) => strs(r).filter((s) => FORBID.test(s)).map((s) => (r.hall || r.district || r.cohort) + ': ' + s));
ok('no hall or rollup states apprenticeship hours, wages, credentials, membership or affiliation (no such word or key)', hits.length === 0, hits);
ok('the totals record no hours, wages or credentials (null) and no affiliation (0)', T.hours === null && T.wages === null && T.credentials === null && T.affiliations === 0);
ok('every path is DERIVED and every name READ; agents are SCRIPTED', H.every((h) => h.provenance.path === 'DERIVED' && h.provenance.order === 'DERIVED' && h.provenance.names === 'READ' && h.provenance.agents === 'SCRIPTED'));

console.log(`\n${pass} ok, ${fail} failing`);
process.exit(fail ? 1 : 0);
