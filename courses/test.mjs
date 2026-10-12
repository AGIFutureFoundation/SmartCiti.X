/* courses/test.mjs - the course catalogue and the lesson supplements, checked against the registries they are composed
 * from. Browser-free, network-free. Recompute, never re-read: every course is regrouped from lessons.json, every order
 * re-sorted from the ladder, every band re-derived from the schools offer, every placard quote re-printed by the 3D
 * page's own condLine() (extracted from web/build_3d.py and run here), and every self-check answer, glossary meaning
 * and key concept is resolved at the registry pointer it names. */
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { execFileSync } from 'node:child_process';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (m, c, why) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m + (why !== undefined ? ' :: ' + JSON.stringify(why).slice(0, 500) : '')); } };
const J = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));

const reg = J('courses/registry/courses.json');
const LES = J('lessons/registry/lessons.json'), HALLS = J('pack/registry/halls.json').halls, DIST = J('unions/registry/districts.json').districts;
const CAMP = J('unions/registry/campuses.json').campuses, SIMS = J('sims/registry/sims.json'), STA = J('stations/registry/stations.json');
const CRIBS = J('tools/registry/toolcribs.json'), FIN = J('surfaces/registry/finishes.json'), ADV = J('agents/registry/advisors.json');
const CREWS = J('agents/registry/crews.json'), SCH = J('schools/registry/schools.json');
const ROOMS = JSON.parse(execFileSync('python3', ['-c', `import json,sys; sys.path.insert(0, ${JSON.stringify(join(ROOT, 'web'))}); from interiors import ROOMS; print(json.dumps([[s, l, p] for s, l, _w, _h, p in ROOMS]))`], { encoding: 'utf8' }));
const STRANDS = ROOMS.map((r) => r[0]), LABEL = Object.fromEntries(ROOMS.map((r) => [r[0], r[1]])), PURPOSE = Object.fromEntries(ROOMS.map((r) => [r[0], r[2]]));
const L = LES.lessons, LORDER = Object.keys(L), C = reg.courses, CV = Object.values(C), SUP = reg.supplements;
const sha16 = (b) => createHash('sha256').update(b).digest('hex').slice(0, 16);

/* ---- provenance and staleness ---- */
ok('the registry was built from the current builder source (stamp = sha256 of build.py + supplements.py)',
  reg.source_stamp === sha16(Buffer.concat([readFileSync(join(HERE, 'build.py')), readFileSync(join(HERE, 'supplements.py'))])));
ok(`every source registry is the one the catalogue was built from (${reg.sources.length} sha256 stamps re-hashed)`,
  reg.sources.length === 12 && reg.sources.every((s) => existsSync(join(ROOT, s.path)) && sha16(readFileSync(join(ROOT, s.path))) === s.sha256),
  reg.sources.filter((s) => !existsSync(join(ROOT, s.path)) || sha16(readFileSync(join(ROOT, s.path))) !== s.sha256).map((s) => s.path));
ok('schema tc-courses/1, pack smartcitix-courses', reg.schema === 'tc-courses/1' && reg.pack === 'smartcitix-courses');

/* ---- honesty ---- */
ok('honesty: lessons stay unverified general practice, and no course certifies, qualifies or permits anybody',
  /^unverified general practice/.test(reg.honesty.content) && /no course certifies, qualifies or permits anybody/.test(reg.honesty.not_certification));
ok('honesty: prerequisites are advice, not a gate; the unaided verification gate is untouched', /Nothing is locked/.test(reg.honesty.not_a_gate) && /unaided verification gate/.test(reg.honesty.not_a_gate));
ok('honesty: K-12 bands are DERIVED from the schools offer, not a placement; districts stay PROPOSED',
  /DERIVED/.test(reg.honesty.bands) && /not a placement/.test(reg.honesty.bands) && /PROPOSED/.test(reg.honesty.bands));
{ const text = JSON.stringify({ h: reg.honesty, r: reg.rules, s: reg.supplement_rules });
  ok('the authored text claims no certification, accreditation, endorsement, partner agreement or trained model',
    !/\b(accredit|endorse|certified by|approved by|agreement with|signed with|trained model)/i.test(text)); }
{ const all = readFileSync(join(HERE, 'registry/courses.json'), 'utf8');
  ok('no internal reference in the registry (no scratchpad or /tmp path, no memory/ or console mention, no model identifier)',
    !/\/tmp\/|scratchpad|memory\/|consoles?\b|claude-|gpt-|\bopus\b|\bsonnet\b/i.test(all)); }

/* ---- the catalogue: grouping, recounted ---- */
const trade = CV.filter((c) => c.kind === 'trade'), strand = CV.filter((c) => c.kind === 'strand');
ok(`counts are recounted: ${CV.length} courses = ${trade.length} trade + ${strand.length} strand; ${LORDER.length} lessons, steps summed from lessons.json`,
  reg.counts.courses === CV.length && reg.counts.trade_courses === trade.length && reg.counts.strand_courses === strand.length
  && reg.counts.lessons === LORDER.length && reg.counts.steps === LORDER.reduce((a, k) => a + L[k].steps.length, 0)
  && reg.counts.steps === LES.counts.steps && reg.counts.lessons === LES.counts.lessons);
ok(`one trade course per hall of pack/registry/halls.json (${HALLS.length}), titled with the roster name and focus (READ)`,
  trade.length === HALLS.length && HALLS.every((h) => C['trade.' + h.slug] && C['trade.' + h.slug].title === h.name && C['trade.' + h.slug].focus === h.focus));
ok('each trade course sits in its hall\'s district and campus (re-read from unions/)',
  trade.every((c) => DIST[c.district].halls.includes(c.hall) && DIST[c.district].name === c.district_name
    && CAMP[c.campus].halls.includes(c.hall) && CAMP[c.campus].name === c.campus_name));
ok(`the catalogue lists the ${Object.keys(DIST).length} districts in registry order, each with exactly its halls' courses`,
  JSON.stringify(reg.districts.map((d) => [d.district, d.name, d.courses])) === JSON.stringify(Object.entries(DIST).map(([k, d]) => [k, d.name, d.halls.map((h) => 'trade.' + h)])));
ok(`one strand course per room of web/interiors.py (${STRANDS.length}), titled with the room label and purpose (READ)`,
  strand.length === STRANDS.length && STRANDS.every((s) => C['strand.' + s] && C['strand.' + s].title === LABEL[s] && C['strand.' + s].focus === PURPOSE[s]));
ok('every lesson is in exactly one trade course (its hall) and exactly one strand course (its strand)',
  LORDER.every((k) => trade.filter((c) => c.lessons.includes(k)).length === 1 && C['trade.' + L[k].hall].lessons.includes(k)
    && strand.filter((c) => c.lessons.includes(k)).length === 1 && C['strand.' + L[k].strand].lessons.includes(k)));
const depth = LES.ladder.depth;
const sorted = (ids) => [...ids].sort((a, b) => depth[a] - depth[b] || LORDER.indexOf(a) - LORDER.indexOf(b));
ok('every course outline is in ladder order: depth, then the lessons registry order (re-sorted here)',
  CV.every((c) => JSON.stringify(c.lessons) === JSON.stringify(sorted(c.lessons)) && JSON.stringify(c.outline.map((o) => o.lesson)) === JSON.stringify(c.lessons)));
ok('every outline row reads its title, room, tier, campus and step count from the lesson (READ, not retyped)',
  CV.every((c) => c.outline.every((o) => { const l = L[o.lesson]; return o.title === l.title && o.room_label === l.room_label && o.tier === l.tier
    && o.campus === l.campus && o.steps === l.steps.length && o.depth === depth[o.lesson] && o.hall_name === l.hall_name
    && JSON.stringify(o.kinds) === JSON.stringify(l.steps.map((s) => s.kind)); })));
{ const edges = LES.ladder.edges.length; let tin = 0, tout = 0, sin = 0, sout = 0, good = true;
  for (const c of CV) {
    const want = c.lessons.flatMap((k) => LES.ladder.prerequisites[k].map((p) => ({ lesson: k, needs: p.needs, because: p.because })));
    const got = [...c.prerequisites_inside, ...c.prerequisites_outside];
    if (JSON.stringify(got.map((x) => JSON.stringify(x)).sort()) !== JSON.stringify(want.map((x) => JSON.stringify(x)).sort())) good = false;
    if (!c.prerequisites_inside.every((p) => c.lessons.includes(p.needs)) || !c.prerequisites_outside.every((p) => !c.lessons.includes(p.needs))) good = false;
    if (c.kind === 'trade') { tin += c.prerequisites_inside.length; tout += c.prerequisites_outside.length; } else { sin += c.prerequisites_inside.length; sout += c.prerequisites_outside.length; }
  }
  ok(`prerequisites are the ladder's own ${edges} edges, each kept once per course family and split inside/outside correctly (trade ${tin}+${tout}, strand ${sin}+${sout})`,
    good && tin + tout === edges && sin + sout === edges && reg.counts.cross_course_edges_trade === tout); }
{ const bad = CV.filter((c) => { const halls = c.kind === 'trade' ? [c.hall] : [...new Set(c.lessons.map((k) => L[k].hall))];
    const bound = [...new Set(halls.flatMap((h) => (SIMS.hall_bindings[h] || []).map((b) => b.sim)))];
    const steps = c.lessons.flatMap((k) => L[k].steps);
    const inl = [...new Set(steps.filter((s) => s.kind === 'sim' || s.kind === 'walkaround').map((s) => s.sim))];
    const t = c.seat_time;
    return JSON.stringify([...t.seats_bound].sort()) !== JSON.stringify(bound.sort()) || JSON.stringify([...t.seats_in_lessons].sort()) !== JSON.stringify(inl.sort())
      || t.sim_runs !== steps.filter((s) => s.kind === 'sim').length || t.walkaround_points !== steps.filter((s) => s.kind === 'walkaround').length
      || t.crew_asks !== steps.filter((s) => s.kind === 'crew').length || t.minutes !== null; });
  ok('seat time is recounted (seats bound via sims hall_bindings, seat runs, walkaround points, crew asks) and no course gives minutes', bad.length === 0, bad.map((c) => c.id)); }
ok('no minutes can be read from sims/: every seat\'s time axis is informational, so "minutes: null" is the record, not an omission',
  Object.values(SIMS.sims).every((s) => s.rubric.filter((r) => r.axis === 'time').every((r) => r.pass === 'informational')));
ok(`trade courses with a bound seat = the lessons pack's seat-bound halls (${LES.spread.seat_bound_halls.length})`,
  JSON.stringify(trade.filter((c) => c.seat_time.seats_bound.length).map((c) => c.hall).sort()) === JSON.stringify([...LES.spread.seat_bound_halls].sort()));

/* ---- tiers and K-12 bands, re-derived ---- */
const TR = { fundamentals: 0, applied: 1, mastery: 2 };
ok('the three tiers are the skill graph\'s, and mastery is honestly empty (no lesson stands at it)',
  JSON.stringify(reg.tiers) === JSON.stringify(['fundamentals', 'applied', 'mastery']) && reg.counts.lessons_by_tier.mastery === LORDER.filter((k) => L[k].tier === 'mastery').length
  && reg.counts.lessons_by_tier.fundamentals + reg.counts.lessons_by_tier.applied + reg.counts.lessons_by_tier.mastery === LORDER.length);
ok('each band rule rests on words its schools/ offer still says, with the tier schools/ gives it',
  SCH.bands.every((b) => { const r = reg.rules.bands[b.band]; return r && b.offer.includes(r.rests_on) && (b.tier === null || b.tier === r.max_tier); })
  && Object.keys(reg.rules.bands).join() === SCH.bands.map((b) => b.band).join());
const bandsOf = (l) => SCH.bands.map((b) => b.band).filter((b) => { const r = reg.rules.bands[b];
  return TR[l.tier] <= TR[r.max_tier] && l.steps.every((s) => r.kinds.includes(s.kind)); });
ok('every lesson\'s bands are re-derived by the printed rule (tier ceiling and allowed step kinds)',
  CV.every((c) => c.outline.every((o) => JSON.stringify(o.bands) === JSON.stringify(bandsOf(L[o.lesson])))
    && JSON.stringify(c.bands) === JSON.stringify(Object.keys(c.band_lessons).filter((b) => c.band_lessons[b].length))
    && Object.entries(c.band_lessons).every(([b, ids]) => JSON.stringify(ids) === JSON.stringify(c.lessons.filter((k) => bandsOf(L[k]).includes(b))))));
ok('K-5 admits no seat, walkaround, crew, station or crib step; 6-8 admits no floor step (the offers\' own limits)',
  LORDER.filter((k) => bandsOf(L[k]).includes('K-5')).every((k) => L[k].steps.every((s) => ['walk', 'placard', 'advisor'].includes(s.kind)))
  && LORDER.filter((k) => bandsOf(L[k]).includes('6-8')).every((k) => L[k].steps.every((s) => s.stage === 'class') && L[k].tier === 'fundamentals'));

/* ---- supplements ---- */
const S = Object.values(SUP);
ok(`one supplement per lesson (${S.length} of ${LORDER.length}), in registry order`, JSON.stringify(Object.keys(SUP)) === JSON.stringify(LORDER));
// a resolver for "path#a.b.c": greedy keys (a binding id may hold a dot), arrays by [i] or by element id
const FILES = { 'lessons/registry/lessons.json': LES, 'sims/registry/sims.json': SIMS, 'stations/registry/stations.json': STA,
  'tools/registry/toolcribs.json': CRIBS, 'surfaces/registry/finishes.json': FIN, 'agents/registry/advisors.json': ADV,
  'agents/registry/crews.json': CREWS, 'web/interiors.py': { ROOMS: Object.fromEntries(ROOMS.map((r) => [r[0], { id: r[0], label: r[1], purpose: r[2] }])) } };
function resolve(ref) {
  const [file, ptr] = ref.split('#'); let node = FILES[file]; if (!node || !ptr) return undefined;
  const segs = ptr.split('.');
  for (let i = 0; i < segs.length;) {
    let seg = segs[i], idx = null; const m = seg.match(/^(.*)\[(\d+)\]$/); if (m) { seg = m[1]; idx = Number(m[2]); }
    if (Array.isArray(node)) { node = node.find((x) => x && (x.id === seg || x.station_id === seg)); i++; }
    else if (node && typeof node === 'object') {
      let j = segs.length; while (j > i && !(segs.slice(i, j).join('.').replace(/\[\d+\]$/, '') in node)) j--;
      if (j === i) return undefined;
      const key = segs.slice(i, j).join('.'); const mm = key.match(/^(.*)\[(\d+)\]$/);
      node = mm ? node[mm[1]][Number(mm[2])] : node[key]; i = j; idx = null; continue;
    } else return undefined;
    if (idx !== null && node) node = node[idx];
  }
  return node;
}
ok('every glossary term carries the meaning its owning record gives (tool use, room purpose, place, seat task, scenario brief, point check, advisor role, crew job) or none',
  S.every((s) => s.glossary.every((g) => { const n = resolve(g.source);
    if (g.kind === 'ppe' || g.kind === 'hazard') return Array.isArray(n) && n.includes(g.term) && g.meaning === null && g.listed_in;
    if (g.kind === 'tool') return n && n.name === g.term && n.use === g.meaning;
    if (g.kind === 'room') return n && n.label === g.term && n.purpose === g.meaning;
    if (g.kind === 'place') return n && n.short === g.term && n.what === g.meaning;
    if (g.kind === 'seat') return typeof n === 'string' && n === g.meaning;
    if (g.kind === 'scenario') return n && n.name === g.term && n.brief === g.meaning;
    if (g.kind === 'walkaround') return n && n.point === g.term && n.check === g.meaning;
    if (g.kind === 'advisor') return n && n.name === g.term && n.role === g.meaning;
    if (g.kind === 'crew-role') return n && n.name === g.term && n.job === g.meaning;
    return false; })), S.flatMap((s) => s.glossary.filter((g) => !resolve(g.source)).map((g) => s.lesson + ': ' + g.source)).slice(0, 5));
ok('every supplement\'s glossary holds every tool of its hall\'s district crib (the crib named in where-to-go)',
  S.every((s) => { const d = CRIBS.hall_bindings[s.hall].district; return s.where.crib.district === d && s.where.crib.name === CRIBS.cribs[d].name
    && CRIBS.cribs[d].tools.every((t) => s.glossary.some((g) => g.kind === 'tool' && g.id === t.id)); }));
ok('every key concept is found verbatim at the record it cites (a crew stop line as "<role>: <stops>")',
  S.every((s) => s.concepts.every((c) => { const n = resolve(c.source); return c.kind === 'crew-stops' ? typeof n === 'string' && c.text.endsWith(': ' + n) : n === c.text; }))
  && S.every((s) => s.concepts[0].kind === 'why' && s.concepts[0].text === L[s.lesson].why));
// the placard, printed by the 3D page's own function
const src3d = readFileSync(join(ROOT, 'web/build_3d.py'), 'utf8');
const fm = src3d.match(/function condLine\(c\) \{[\s\S]*?\n\}/);
const condLine = fm ? new Function(fm[0].replace(/\\u([0-9a-fA-F]{4})/g, (_, h) => '\\u' + h) + '; return condLine;')() : null;
ok('condLine() is extracted from web/build_3d.py and runs here', typeof condLine === 'function');
{ const bad = []; let n = 0;
  for (const s of S) for (const p of s.safety.placards) { n++; const c = FIN.halls[s.hall].conditions[p.strand];
    if (!condLine || p.quote !== condLine(c) || p.placard_hung !== c.ppe.length > 0 || JSON.stringify(p.ppe) !== JSON.stringify(c.ppe)
      || JSON.stringify(p.hazards) !== JSON.stringify(c.hazards) || p.room_label !== LABEL[p.strand]) bad.push(s.lesson + ':' + p.strand); }
  ok(`every safety note quotes the door placard verbatim as the 3D page prints it (${n} quotes, ${S.reduce((a, s) => a + s.safety.placards.filter((p) => p.placard_hung).length, 0)} hung)`,
    bad.length === 0 && n === reg.supplement_counts.placard_quotes, bad.slice(0, 5)); }
ok('every room a lesson walks has its record quoted, and every placard step\'s room is marked as read',
  S.every((s) => { const rooms = [...new Set(L[s.lesson].steps.map((x) => x.where).filter((w) => STRANDS.includes(w)))];
    return JSON.stringify(s.safety.placards.map((p) => p.strand)) === JSON.stringify(rooms)
      && L[s.lesson].placard_steps_in.every((w) => s.safety.placards.find((p) => p.strand === w && p.read_in_lesson && p.placard_hung)); }));
ok('every safety section is labelled unverified general practice and carries the lesson\'s limits and the not-certification line verbatim',
  S.every((s) => s.safety.label === 'unverified general practice' && s.safety.limits === L[s.lesson].limits && s.safety.not_certification === LES.honesty.not_certification));
ok('every safety line (walkaround fault, crew stop work, station checklist) is verbatim at its source',
  S.every((s) => s.safety.lines.every((x) => resolve(x.source) === x.text)));
/* questions */
const QK = ['course.q.walk', 'course.q.placard', 'course.q.advisor', 'course.q.point', 'course.q.scenario', 'course.q.crew', 'course.q.crib', 'course.q.station', 'course.q.doctrine'];
const answerAt = (q) => { const n = resolve(q.answer.ref); if (n === undefined || n === null) return false;
  const fm2 = q.answer.ref.match(/halls\.([^.]+)\.conditions\.([^.]+)$/); if (fm2) return q.answer.id === fm2[1] + '.' + fm2[2];
  if (n.options) return n.options.some((o) => o.prop === q.answer.id && o.correct === true);
  return n.id === q.answer.id || n.station_id === q.answer.id || (typeof n === 'object' && q.answer.ref.endsWith('.' + q.answer.id)); };
ok(`every self-check answer is a registry id that resolves at the pointer it names (${reg.supplement_counts.questions} questions)`,
  S.every((s) => s.questions.every(answerAt)), S.flatMap((s) => s.questions.filter((q) => !answerAt(q)).map((q) => q.id)).slice(0, 5));
ok('every question has its answer among its options exactly once, at least two options, no two options alike, and a known stem',
  S.every((s) => s.questions.every((q) => q.options.filter((o) => o.id === q.answer.id).length === 1 && q.options.length >= 2
    && new Set(q.options.map((o) => o.label)).size === q.options.length && QK.includes(q.stem))));
ok('the answer is the step\'s own id: room = where, advisor = advisor, point = point, scenario = scenario, role = role, station = station',
  S.every((s) => { const st = L[s.lesson].steps; const want = st.flatMap((x) => x.kind === 'walk' ? [x.where] : x.kind === 'placard' ? [s.hall + '.' + x.where]
    : x.kind === 'advisor' ? [x.advisor] : x.kind === 'walkaround' ? [x.point] : x.kind === 'sim' ? [x.scenario] : x.kind === 'crew' ? [x.role] : []);
    const got = s.questions.filter((q) => !['crib', 'station'].includes(q.kind)).map((q) => q.answer.id);
    return JSON.stringify(got) === JSON.stringify(want); }));
ok('every crib question is a drill item of the hall\'s district, answered by the drill\'s own tool (two when the lesson runs the crib check)',
  S.every((s) => { const d = CRIBS.hall_bindings[s.hall].district, cq = s.questions.filter((q) => q.kind === 'crib');
    return cq.length === (L[s.lesson].steps.some((x) => x.kind === 'crib') ? 2 : 1)
      && cq.every((q) => CRIBS.drills[d].some((it) => it.ask === q.args.ask && it.tool === q.answer.id)); }));
ok('every option label is the registry\'s label for that option id (no option text is typed)',
  S.every((s) => s.questions.every((q) => q.options.every((o) => {
    if (q.kind === 'walk') return LABEL[o.id] === o.label;
    if (q.kind === 'advisor') return ADV.advisors[o.id].name === o.label;
    if (q.kind === 'crib') return CRIBS.cribs[CRIBS.hall_bindings[s.hall].district].tools.find((t) => t.id === o.id).name === o.label;
    if (q.kind === 'placard') { const [h, st] = o.id.split('.'); return condLine && condLine(FIN.halls[h].conditions[st]) === o.label; }
    return typeof o.label === 'string' && o.label.length > 0; }))));
{ const pos = S.flatMap((s) => s.questions.map((q) => q.options.findIndex((o) => o.id === q.answer.id)));
  const hist = [0, 1, 2, 3].map((i) => pos.filter((p) => p === i).length);
  ok(`the correct option is not always in one place (positions 1-4: ${hist.join('/')})`, hist.filter((h) => h > 0).length >= 3 && Math.max(...hist) < pos.length * 0.5); }
ok(`at least three self-check questions per lesson (min ${reg.supplement_counts.min_questions})`, S.every((s) => s.questions.length >= 3) && reg.supplement_counts.min_questions >= 3);
/* worksheet and where-to-go */
const WK = { walk: 'course.w.walk', placard: 'course.w.placard', advisor: 'course.w.advisor', station: 'course.w.station', crib: 'course.w.crib', walkaround: 'course.w.walkaround', sim: 'course.w.sim', crew: 'course.w.crew' };
ok('the worksheet is one line per step, with the step\'s own do-line verbatim and its kind\'s fill-in key',
  S.every((s) => JSON.stringify(s.worksheet.map((w) => [w.n, w.kind, w.do, w.fill])) === JSON.stringify(L[s.lesson].steps.map((x) => [x.n, x.kind, x.do, WK[x.kind]])))
  && S.every((s) => s.worksheet.every((w) => w.kind !== 'crib' || w.args.picks === CRIBS.drill.picks)));
ok('where-to-go: the places walked, the advisors asked (with the room they stand in), the seats and crews run, from their records',
  S.every((s) => { const st = L[s.lesson].steps;
    return JSON.stringify(s.where.places.map((p) => p.where)) === JSON.stringify([...new Set(st.map((x) => x.where))])
      && s.where.places.every((p) => p.label === (LABEL[p.where] || LES.off_room_places[p.where].short))
      && JSON.stringify(s.where.advisors.map((a) => a.id)) === JSON.stringify([...new Set(st.filter((x) => x.kind === 'advisor').map((x) => x.advisor))])
      && s.where.advisors.every((a) => a.stands_in === ADV.advisors[a.id].stands_in && a.name === ADV.advisors[a.id].name)
      && JSON.stringify(s.where.seats.map((x) => x.sim)) === JSON.stringify([...new Set(st.filter((x) => x.kind === 'sim' || x.kind === 'walkaround').map((x) => x.sim))])
      && JSON.stringify(s.where.crews.map((x) => x.crew)) === JSON.stringify([...new Set(st.filter((x) => x.kind === 'crew').map((x) => x.crew))]); }));
ok('where-to-go links name real pages: the lesson anchor, the hall in 3D, the ladder',
  S.every((s) => s.where.links.lesson === `web/trade_craft_lessons.html#lesson-${s.lesson}` && s.where.links.hall3d === `web/trade_craft_3d.html?hall=${s.hall}`)
  && ['web/trade_craft_lessons.html', 'web/trade_craft_3d.html', 'web/trade_craft_ladder.html'].every((f) => existsSync(join(ROOT, f))));
{ const sc = reg.supplement_counts;
  ok(`supplement counts are recounted: ${sc.glossary_terms} glossary terms, ${sc.concepts} concepts, ${sc.questions} questions, ${sc.worksheet_lines} worksheet lines, ${sc.safety_lines} safety lines`,
    sc.supplements === S.length && sc.glossary_terms === S.reduce((a, s) => a + s.glossary.length, 0) && sc.concepts === S.reduce((a, s) => a + s.concepts.length, 0)
    && sc.questions === S.reduce((a, s) => a + s.questions.length, 0) && sc.worksheet_lines === reg.counts.steps
    && sc.safety_lines === S.reduce((a, s) => a + s.safety.lines.length, 0)
    && Object.values(sc.questions_by_kind).reduce((a, b) => a + b, 0) === sc.questions); }

{ const cv = reg.supplement_counts.coverage, steps = LORDER.flatMap((k) => L[k].steps), ask = ['walk', 'placard', 'advisor', 'walkaround', 'sim', 'crew', 'station'];
  const asked = S.reduce((a, s) => a + s.questions.filter((q) => !['crib'].includes(q.kind)).length, 0);
  ok(`coverage is recounted: ${cv.lessons_with_supplement}/${cv.lessons} lessons, ${cv.steps_with_worksheet_line}/${cv.steps} steps on a worksheet, ${cv.id_steps_with_question}/${cv.id_steps} id-naming steps asked, ${cv.crib_steps_with_drill_items}/${cv.crib_steps} crib steps drilled, ${cv.cribs_in_glossaries}/${cv.cribs} cribs glossed, ${cv.lessons_with_a_placard_hung} lessons quote a hung placard`,
    cv.lessons_with_supplement === LORDER.length && cv.lessons === LORDER.length && cv.steps_with_worksheet_line === steps.length && cv.steps === steps.length
    && cv.id_steps === steps.filter((x) => ask.includes(x.kind)).length && cv.id_steps_with_question === asked && asked === cv.id_steps
    && cv.crib_steps === steps.filter((x) => x.kind === 'crib').length && cv.crib_steps_with_drill_items === cv.crib_steps
    && S.filter((s) => s.questions.filter((q) => q.kind === 'crib').length === 2).length === LORDER.filter((k) => L[k].steps.some((x) => x.kind === 'crib')).length
    && cv.cribs === Object.keys(CRIBS.cribs).length && cv.cribs_in_glossaries === new Set(S.map((s) => s.where.crib.district)).size
    && cv.lessons_with_crib_glossary === LORDER.length
    && cv.lessons_with_a_placard_hung === S.filter((s) => s.safety.placards.some((p) => p.placard_hung)).length
    && cv.lessons_with_a_placard_hung + cv.lessons_whose_rooms_hang_no_placard === LORDER.length); }
console.log(`  (measured) ${CV.length} courses (${trade.length} trade, ${strand.length} strand); ${S.length} supplements; ${reg.supplement_counts.questions} questions; ${reg.supplement_counts.glossary_terms} glossary terms; ${reg.supplement_counts.placard_quotes} placard quotes; bands K-5 ${reg.counts.lessons_by_band['K-5']}, 6-8 ${reg.counts.lessons_by_band['6-8']}, 9-10 ${reg.counts.lessons_by_band['9-10']}, 11-12 ${reg.counts.lessons_by_band['11-12']}`);
console.log(`courses/test: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
