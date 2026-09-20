/**
 * Lessons registry verification.
 *
 * The claim of this pack is small enough to check completely: a lesson is
 * a walk you can actually take, every step of it names something that
 * already exists somewhere else in this bundle, and nothing it says about
 * itself is bigger than what it did. So most of what follows is
 * RESOLUTION - a station id that names no station, a seat a hall does not
 * train on, a scenario that belongs to another campus, an advisor asked in
 * a room they do not stand in, a prerequisite pointing at a lesson that
 * was never written, and a count that has drifted from the thing it counts
 * are all the same bug in different clothes.
 *
 * Four of these are worth reading twice.
 *
 * NAMES ARE RE-READ, NEVER COMPARED TO A COPY. Every display name a step's
 * instruction line uses - the room label, the station name, the seat name,
 * the scenario name, the walkaround point, the advisor and crew role names
 * and the exact wording of a topic - is fetched here from the registry
 * that OWNS it and required to appear verbatim in the line. The room label
 * is parsed back out of `web/interiors.py`, which is where hall interiors
 * are actually laid out from. A lesson that retyped a name instead of
 * reading it would pass a spell-check and fail this.
 *
 * THE LADDER'S REASONS ARE CHECKED, NOT READ. Each prerequisite edge says
 * why it exists - same hall, same seat, same district crib - and each of
 * those is re-derived here from halls, sims and toolcribs. An edge whose
 * stated reason is not true in the registries is a sequencing opinion
 * wearing a justification, and the graph is then walked for cycles rather
 * than trusted to be a tree.
 *
 * WHAT A STEP RECORDS IS CHECKED AGAINST TRAINING/. Four of the eight step
 * kinds write an episode; the four that write nothing must say so with an
 * explicit null AND give the reason they write nothing. No kind may name
 * an episode kind `training/registry/training.json` does not already
 * declare, because a lesson pack that invented a fifth one would have
 * quietly changed what this bundle records about people.
 *
 * AND NOTHING CERTIFIES ANYBODY. Every CLAUSE in the payload that claims
 * a ticket is re-scanned here - questions excluded, because an advisor
 * topic that ASKS whether a pass certifies anyone is the opposite of a
 * claim - and each one must carry its denial in the same breath. The split
 * is on clause punctuation rather than sentence punctuation on purpose: a
 * denial two clauses downstream reads as a disclaimer and lands after the
 * belief the claim already created.
 */
import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const url = (p) => new URL(p, import.meta.url);
const reg = JSON.parse(readFileSync(url('./registry/lessons.json')));
const manifest = JSON.parse(readFileSync(url('../pack/manifest.json')));
const halls = JSON.parse(readFileSync(url('../pack/registry/halls.json'))).halls;
const skills = JSON.parse(readFileSync(url('../pack/registry/skills.json'))).skills;
const stationsReg = JSON.parse(readFileSync(url('../stations/registry/stations.json')));
const sims = JSON.parse(readFileSync(url('../sims/registry/sims.json')));
const training = JSON.parse(readFileSync(url('../training/registry/training.json')));
const schools = JSON.parse(readFileSync(url('../schools/registry/schools.json')));
const finishes = JSON.parse(readFileSync(url('../surfaces/registry/finishes.json')));
const advisors = JSON.parse(readFileSync(url('../agents/registry/advisors.json'))).advisors;
const crews = JSON.parse(readFileSync(url('../agents/registry/crews.json'))).crews;
const cribs = JSON.parse(readFileSync(url('../tools/registry/toolcribs.json')));
const labels = JSON.parse(readFileSync(url('../labels/registry/labels.json')));
const campuses = JSON.parse(readFileSync(url('../unions/registry/campuses.json'))).campuses;
const page = readFileSync(url('../web/build_3d.py'), 'utf8');
const interiors = readFileSync(url('../web/interiors.py'), 'utf8');
const ROOT = fileURLToPath(url('../'));

/* the room label a strand requires, parsed back out of the module that
   actually lays every hall interior out - not out of this registry */
const ROOM_LABEL = (() => {
  const block = interiors.slice(interiors.indexOf('ROOMS = ['),
    interiors.indexOf(']', interiors.indexOf('ROOMS = [')));
  const m = {};
  for (const r of block.matchAll(/\(\s*"([a-z]+)",\s*"([^"]+)"/g)) m[r[1]] = r[2];
  return m;
})();
const HALL_NAME = Object.fromEntries(halls.map((h) => [h.slug, h.name]));
const HALL_STRANDS = {};
const SKILL_IDS = new Set();
for (const s of skills) {
  SKILL_IDS.add(s.skill_id);
  (HALL_STRANDS[s.union] ??= new Set()).add(s.strand);
}
const HALL_CAMPUS = {};
for (const [k, c] of Object.entries(campuses)) for (const h of c.halls) HALL_CAMPUS[h] = k;
const STATION = Object.fromEntries(stationsReg.stations.map((s) => [s.station_id, s]));

const lessons = Object.entries(reg.lessons);
const steps = lessons.flatMap(([lid, L]) => L.steps.map((s) => [lid, L, s]));
const stepsOf = (k) => steps.filter(([, , s]) => s.kind === k);
const edges = reg.ladder.edges;

/* ------------------------------------------------------------ the shape --- */
ok('the pack carries the same header every pack in this bundle carries',
  reg.pack === 'smartcitix-trade-craft-academy-lessons'
  && reg.pack_version === manifest.pack_version
  && /^\d{4}-\d{2}-\d{2}$/.test(reg.built) && reg.source_stamp.length === 16);
ok('every lesson is keyed by its own id, and no two lessons share one',
  lessons.every(([lid, L]) => L.id === lid) && new Set(lessons.map(([l]) => l)).size === lessons.length);
ok('every lesson stands in a real hall and names that hall\'s own name, read not retyped',
  lessons.every(([, L]) => L.hall in HALL_NAME && L.hall_name === HALL_NAME[L.hall]));
ok('every lesson\'s strand is one its hall actually teaches, and the skill id exists',
  lessons.every(([, L]) => HALL_STRANDS[L.hall].has(L.strand)
    && L.skill_id === `${L.hall}.${L.strand}.${L.tier}` && SKILL_IDS.has(L.skill_id)));
ok('every lesson stands in a ROOM: the surfaces record has that room and what it is held to',
  lessons.every(([, L]) => L.strand in finishes.halls[L.hall].rooms
    && L.strand in finishes.halls[L.hall].conditions));
ok('every room label is the label web/interiors.py gives that strand, not a second copy',
  Object.keys(ROOM_LABEL).length === 11
  && lessons.every(([, L]) => L.room_label === ROOM_LABEL[L.strand]));
ok('every lesson names the campus its hall is actually sited on',
  lessons.every(([, L]) => L.campus === HALL_CAMPUS[L.hall]));
ok('a lesson starts by walking into the room it stands in, and every step is somewhere real in that hall',
  lessons.every(([, L]) => L.steps.length > 0
    && L.steps[0].kind === 'walk' && L.steps[0].where === L.strand
    && L.steps.every((s) => s.where in finishes.halls[L.hall].rooms
      || s.where in reg.off_room_places))
  && lessons.every(([, L]) => L.steps.every((s, i) => s.n === i + 1)));

/* -------------------------------------------- every reference resolves ---- */
ok('every step is one of the declared kinds, and the kind table is closed',
  steps.every(([, , s]) => s.kind in reg.step_kinds)
  && Object.keys(reg.step_kinds).length === reg.counts.step_kinds);
ok('a step records what its KIND records - no lesson quietly reclassifies a step',
  steps.every(([, , s]) => s.records === reg.step_kinds[s.kind].records
    && s.stage === reg.step_kinds[s.kind].stage
    && s.reads === reg.step_kinds[s.kind].reads));
ok('every station step resolves, stands in that station\'s own room, and belongs to this hall',
  stepsOf('station').every(([, L, s]) => s.station in STATION
    && STATION[s.station].hall === L.hall && s.where === STATION[s.station].strand
    && s.do.includes(STATION[s.station].name) && s.do.includes(ROOM_LABEL[s.where])));
ok('every seat step names a seat this hall actually trains on, at the yard',
  [...stepsOf('sim'), ...stepsOf('walkaround')].every(([, L, s]) =>
    s.sim in sims.sims && sims.sims[s.sim].halls.includes(L.hall)
    && s.where === 'yard' && s.do.includes(sims.sims[s.sim].name)));
ok('every scenario is the one that seat holds for this hall\'s own campus, named verbatim',
  stepsOf('sim').every(([, L, s]) => {
    const mine = sims.sims[s.sim].scenarios.filter((x) => x.campus === HALL_CAMPUS[L.hall]);
    return mine.length === 1 && mine[0].id === s.scenario && s.campus === HALL_CAMPUS[L.hall]
      && s.do.includes(mine[0].name);
  }));
ok('every walkaround point is a point that seat declares, quoted as the sims registry wrote it',
  stepsOf('walkaround').every(([, , s]) => {
    const p = sims.sims[s.sim].walkaround.find((x) => x.id === s.point);
    return !!p && s.do.includes(p.point) && s.do.includes(p.check);
  }));
ok('every advisor step asks a real advisor a real topic, in the room that advisor stands in',
  stepsOf('advisor').every(([, , s]) => {
    const a = advisors[s.advisor];
    if (!a || a.stands_in !== s.where) return false;
    const t = a.topics.find((x) => x.id === s.topic);
    return !!t && s.do.includes(a.name) && s.do.includes(t.ask) && s.answer_kind === t.kind;
  }));
ok('every crew step asks a real role a real topic, and that crew stands for this hall',
  stepsOf('crew').every(([, L, s]) => {
    const c = crews[s.crew];
    if (!c || !c.halls.includes(L.hall) || s.seat !== c.seat || s.muster !== c.muster) return false;
    const r = c.roles[s.role];
    if (!r) return false;
    const t = r.topics.find((x) => x.id === s.topic);
    return !!t && s.do.includes(c.name) && s.do.includes(r.name) && s.do.includes(t.ask);
  }));
ok('a crew only stands while its own seat runs, so its lesson goes to that seat',
  stepsOf('crew').every(([, L, s]) =>
    L.steps.some((x) => x.sim === crews[s.crew].seat)));
ok('every crib step runs the drill of the district this hall actually draws from',
  stepsOf('crib').every(([, L, s]) => s.crib === cribs.hall_bindings[L.hall].district
    && s.where === 'tools' && cribs.drills[s.crib].length === cribs.drill.picks
    && s.do.includes(cribs.cribs[s.crib].name) && s.do.includes(cribs.drill.name)));
ok('the placard step reads a sign kind the labels pack still draws',
  'placard' in labels.kinds
  && stepsOf('placard').every(([, , s]) => s.label_kind === 'placard'
    && s.do.includes(ROOM_LABEL[s.where])));

/* ------------------------------------------------- one truth per fact ---- */
ok('every name a step uses is one it READ, and the registry lists exactly those names',
  steps.every(([, L, s]) => {
    const want = [];
    if (s.kind === 'walk' || s.kind === 'placard') want.push(ROOM_LABEL[s.where]);
    if (s.kind === 'station') want.push(STATION[s.station].name, ROOM_LABEL[s.where]);
    if (s.kind === 'crib') want.push(cribs.cribs[s.crib].name, cribs.drill.name, ROOM_LABEL.tools);
    if (s.kind === 'walkaround') want.push(sims.sims[s.sim].name,
      sims.sims[s.sim].walkaround.find((x) => x.id === s.point).point);
    if (s.kind === 'sim') want.push(sims.sims[s.sim].name,
      sims.sims[s.sim].scenarios.find((x) => x.id === s.scenario).name);
    if (s.kind === 'advisor') {
      const a = advisors[s.advisor];
      if (a.stands_in in ROOM_LABEL) want.push(ROOM_LABEL[a.stands_in]);
      want.push(a.name, a.topics.find((x) => x.id === s.topic).ask);
    }
    if (s.kind === 'crew') {
      const c = crews[s.crew];
      want.push(c.name, c.roles[s.role].name,
        c.roles[s.role].topics.find((x) => x.id === s.topic).ask);
    }
    return JSON.stringify([...s.names_read].sort()) === JSON.stringify(want.sort());
  }));
ok('no authored line repeats a name the registries already own - a second copy is the defect',
  steps.every(([, L, s]) => s.names_read.every((x) =>
    !s.note.includes(x) && !L.title.includes(x) && !L.why.includes(x))));
ok('nothing in the payload is a URL: this pack fetches nothing and links nowhere',
  !/https?:\/\//.test(JSON.stringify(reg)));
ok('every file a step kind reads exists in this repo',
  reg.reads.length > 0 && reg.reads.every((f) => existsSync(ROOT + f))
  && JSON.stringify(reg.reads)
     === JSON.stringify([...new Set(steps.map(([, , s]) => s.reads))].sort()));

/* ------------------------------------------------- what gets recorded ---- */
ok('no step writes an episode kind training/ does not already declare, and no new kind is added',
  steps.every(([, , s]) => s.records === null || s.records in training.episode_kinds)
  && reg.counts.new_episode_kinds === 0
  && Object.keys(reg.step_kinds).every((k) => reg.step_kinds[k].records === null
    || reg.step_kinds[k].records in training.episode_kinds));
ok('a step that records nothing says so with an explicit null AND says why',
  Object.entries(reg.step_kinds).every(([, k]) => k.records === null
    ? typeof k.why_no_episode === 'string' && k.why_no_episode.length > 60
    : k.why_no_episode === null));
ok('every lesson writes at least one episode, and the set exercises all four kinds',
  lessons.every(([, L]) => L.records.length > 0
    && L.records.every((k) => k in training.episode_kinds))
  && JSON.stringify([...new Set(lessons.flatMap(([, L]) => L.records))].sort())
     === JSON.stringify(Object.keys(training.episode_kinds).sort()));
ok('this pack claims no storage key of its own - it writes through the recorder that exists',
  !JSON.stringify(reg).includes('tc-lessons')
  && !JSON.stringify(reg).includes(training.storage.key + '-'));

/* ------------------------------------------------------ the flipped loop -- */
ok('every stage a step belongs to is a stage schools/ already declares',
  (() => {
    const declared = schools.model.stages.map((s) => s.stage);
    return reg.plugs_into.stages_used.every((s) => declared.includes(s))
      && JSON.stringify(reg.plugs_into.stages_used)
         === JSON.stringify([...new Set(steps.map(([, , s]) => s.stage))].sort());
  })());
ok('no lesson stands in the gate, the one stage schools/ leaves deliberately ungamified',
  !reg.plugs_into.stages_used.includes('gate')
  && !reg.plugs_into.stages_used.includes('home')
  && reg.plugs_into.stages_left_alone.includes('gate')
  && reg.plugs_into.loop === schools.model.loop);

/* ---------------------------------------------------------- the breadth --- */
ok('the spread is over the trades, not down one: every strand is stood in and no hall is over the ceiling',
  reg.spread.strands.length === 11
  && JSON.stringify(reg.spread.strands)
     === JSON.stringify([...new Set(lessons.map(([, L]) => L.strand))].sort())
  && JSON.stringify(reg.spread.halls)
     === JSON.stringify([...new Set(lessons.map(([, L]) => L.hall))].sort())
  && reg.spread.halls.length >= 20);
ok('the top hall\'s share is computed from the set, not typed, and is under the declared ceiling',
  (() => {
    const per = {};
    for (const [, L] of lessons) per[L.hall] = (per[L.hall] ?? 0) + 1;
    const top = Math.max(...Object.values(per));
    return top === reg.counts.max_lessons_in_one_hall
      && Math.abs(reg.spread.max_hall_share - top / lessons.length) < 1e-9
      && reg.spread.max_hall_share <= reg.spread.max_hall_share_ceiling;
  })());

/* ----------------------------------------------------------- the ladder --- */
ok('every prerequisite names a lesson that exists, and nothing is its own prerequisite',
  edges.every((e) => e.lesson in reg.lessons && e.needs in reg.lessons && e.lesson !== e.needs)
  && Object.entries(reg.ladder.prerequisites).every(([lid, es]) => lid in reg.lessons
    && es.every((e) => e.needs in reg.lessons)));
ok('every edge names a declared reason, and the reason is actually TRUE in the registries',
  edges.every((e) => {
    if (!(e.because in reg.ladder.reasons)) return false;
    const A = reg.lessons[e.needs], B = reg.lessons[e.lesson];
    if (e.because === 'same-hall') return A.hall === B.hall;
    if (e.because === 'same-seat') {
      const sa = new Set(A.steps.filter((s) => s.sim).map((s) => s.sim));
      return B.steps.some((s) => s.sim && sa.has(s.sim));
    }
    if (e.because === 'same-district-crib')
      return cribs.hall_bindings[A.hall].district === cribs.hall_bindings[B.hall].district;
    return false;
  }));
ok('a prerequisite never sits at a higher tier than the lesson it gates',
  (() => {
    const rank = { fundamentals: 0, applied: 1, mastery: 2 };
    return edges.every((e) => rank[reg.lessons[e.needs].tier] <= rank[reg.lessons[e.lesson].tier]);
  })());
ok('the graph is acyclic, walked here rather than taken on trust',
  (() => {
    const pre = reg.ladder.prerequisites, state = {};
    const visit = (x) => {
      if (state[x] === 2) return true;
      if (state[x] === 1) return false;
      state[x] = 1;
      for (const e of pre[x]) if (!visit(e.needs)) return false;
      state[x] = 2;
      return true;
    };
    return Object.keys(pre).every(visit) && reg.ladder.acyclic === true;
  })());
ok('the roots, depths and layers are re-derived from the edges, not published from memory',
  (() => {
    const pre = reg.ladder.prerequisites, d = {};
    const depth = (x) => d[x] ??= 1 + Math.max(0, ...pre[x].map((e) => depth(e.needs)));
    for (const k of Object.keys(pre)) depth(k);
    const roots = Object.keys(pre).filter((k) => pre[k].length === 0).sort();
    const layers = {};
    for (const [k, v] of Object.entries(d)) (layers[v] ??= []).push(k);
    for (const k of Object.keys(layers)) layers[k].sort();
    return JSON.stringify(roots) === JSON.stringify(reg.ladder.roots)
      && JSON.stringify(d) === JSON.stringify(reg.ladder.depth)
      && JSON.stringify(layers) === JSON.stringify(reg.ladder.layers)
      && reg.counts.ladder_depth === Math.max(...Object.values(d));
  })());
ok('the ladder locks nothing: it says so, and no lesson or step carries a field that could gate one',
  /not a permission system/.test(reg.ladder.enforcement)
  && steps.every(([, , s]) => !('requires' in s) && !('unlocks' in s)
    && !('score' in s) && !('points' in s) && !('pass' in s))
  && lessons.every(([, L]) => !('unlocks' in L) && !('score' in L) && !('gate' in L)));

/* ---------------------------------------------------- what it admits to --- */
ok('the pack carries the AUTHORED provenance word and never borrows orbis\'s',
  /^AUTHORED: /.test(reg.honesty.status)
  && /AI-SYNTHESIZED belongs to orbis\//.test(reg.honesty.status)
  && lessons.every(([, L]) => L.provenance.steps === 'AUTHORED'
    && L.provenance.names === 'READ'));
ok('AI-SYNTHESIZED appears nowhere but the sentence disclaiming it',
  JSON.stringify({ ...reg, honesty: { ...reg.honesty, status: '' } })
    .indexOf('AI-SYNTHESIZED') === -1);
ok('the content is admitted to be unverified general practice pending the halls\' own practitioners',
  /unverified general practice/.test(reg.honesty.content)
  && /journey-level practitioners/.test(reg.honesty.content)
  && /corrected and replaced/.test(reg.honesty.content));
ok('the pack says plainly that it certifies nobody and gates nothing',
  /no lesson here certifies anybody/.test(reg.honesty.not_certification)
  && /this bundle is none of those/.test(reg.honesty.not_certification)
  && /unlocks nothing/.test(reg.honesty.not_a_gate)
  && /unaided verification run/.test(reg.honesty.not_a_gate));
ok('no clause in the payload claims a ticket without denying it in the same breath',
  (() => {
    const claim = /\b(certif(y|ies|ied|ying|ication|ications)|qualif(y|ies|ied|ication|ications)|licen[cs]e[sd]?|licensing|ticketed)\b/i;
    const denial = /\b(not|no|nothing|nobody|never|none|without)\b/i;
    const bad = [];
    for (const [lid, L] of lessons)
      for (const f of [L.title, L.why, L.limits,
        ...L.steps.map((s) => s.note), ...L.steps.map((s) => s.do)])
        for (const s of f.split(/(?<=[.!?;:])\s+/))
          if (!s.includes('?') && claim.test(s) && !denial.test(s)) bad.push(lid + ': ' + s);
    return bad.length === 0;
  })());
ok('every lesson says what it does NOT mean, and says it by denying something',
  lessons.every(([, L]) => L.limits.length > 120 && L.limits.length <= 400
    && /\b(not|no|nothing|nobody|never)\b/i.test(L.limits)));
ok('every `why` is one plain sentence, and every note is one useful line',
  lessons.every(([, L]) => L.why.endsWith('.') && !L.why.includes('. ')
    && L.why.length > 60 && L.why.length <= 240)
  && steps.every(([, , s]) => s.note.length >= 50 && s.note.length <= 200));
ok('no real union local, employer or person is named anywhere in the lessons',
  !/\bLocal\s+\d|\bIBEW\b|\bUA\s+\d|\bLiUNA\b/i.test(JSON.stringify(reg)));

/* ------------------------------------------------------ the page contract -- */
ok('the page contract names every piece of wiring this pack needs and nothing it does not',
  ['data', 'hall', 'room', 'hud', 'reads', 'steps', 'records', 'ladder', 'limits', 'episode']
    .every((k) => typeof reg.page_contract[k] === 'string' && reg.page_contract[k].length > 60)
  && Object.keys(reg.page_contract).length === 10);
ok('the contract is grounded in what the page actually does today, not in what it might do',
  ['curRoom', 'hfocus', 'hint', "view = 'hall'", 'condLine', 'condOf']
    .every((t) => page.includes(t))
  && !page.includes('D.lessons'));
ok('the contract tells the page to READ the names and to record nothing for opening a lesson',
  /READ and never copy/.test(reg.page_contract.reads)
  && /stores ids for all of those on purpose/.test(reg.page_contract.reads)
  && /nothing about opening, reading or abandoning a lesson is recorded/i.test(reg.page_contract.episode)
  && /must not invent an episode/.test(reg.page_contract.records));

/* -------------------------------------------------------------- the counts --- */
ok('the counts the registry publishes are the counts it actually holds',
  reg.counts.lessons === lessons.length
  && reg.counts.steps === steps.length
  && reg.counts.halls_covered === new Set(lessons.map(([, L]) => L.hall)).size
  && reg.counts.halls_total === halls.length
  && reg.counts.strands_covered === new Set(lessons.map(([, L]) => L.strand)).size
  && reg.counts.strands_total === 11
  && reg.counts.rooms_stood_in === new Set(lessons.map(([, L]) => L.hall + '/' + L.strand)).size
  && reg.counts.campuses_covered === new Set(lessons.map(([, L]) => L.campus)).size
  && reg.counts.recording_steps === steps.filter(([, , s]) => s.records !== null).length
  && reg.counts.silent_steps === steps.filter(([, , s]) => s.records === null).length
  && reg.counts.recording_steps + reg.counts.silent_steps === reg.counts.steps
  && reg.counts.episode_kinds_declared === Object.keys(training.episode_kinds).length
  && reg.counts.files_read === reg.reads.length);
ok('the per-kind tallies are re-derived from the steps themselves, not typed beside them',
  (() => {
    const byKind = {}, byEp = {};
    for (const [, , s] of steps) {
      byKind[s.kind] = (byKind[s.kind] ?? 0) + 1;
      if (s.records !== null) byEp[s.records] = (byEp[s.records] ?? 0) + 1;
    }
    const sorted = (o) => Object.fromEntries(Object.entries(o).sort(([a], [b]) => a < b ? -1 : 1));
    return JSON.stringify(reg.counts.steps_by_kind) === JSON.stringify(sorted(byKind))
      && JSON.stringify(reg.counts.episodes_by_kind) === JSON.stringify(sorted(byEp))
      && reg.counts.episode_kinds_used === Object.keys(byEp).length;
  })());
ok('the registry tallies are the distinct things actually cited, not round numbers',
  reg.counts.stations_used === new Set(stepsOf('station').map(([, , s]) => s.station)).size
  && reg.counts.stations_total === stationsReg.count
  && reg.counts.sims_used === new Set([...stepsOf('sim'), ...stepsOf('walkaround')]
    .map(([, , s]) => s.sim)).size
  && reg.counts.sims_total === Object.keys(sims.sims).length
  && reg.counts.scenarios_used === new Set(stepsOf('sim').map(([, , s]) => s.sim + '/' + s.scenario)).size
  && reg.counts.scenarios_total === Object.values(sims.sims).reduce((a, s) => a + s.scenarios.length, 0)
  && reg.counts.walkaround_points_used
     === new Set(stepsOf('walkaround').map(([, , s]) => s.sim + '/' + s.point)).size
  && reg.counts.walkaround_points_total
     === Object.values(sims.sims).reduce((a, s) => a + s.walkaround.length, 0)
  && reg.counts.advisors_used === new Set(stepsOf('advisor').map(([, , s]) => s.advisor)).size
  && reg.counts.advisor_topics_used
     === new Set(stepsOf('advisor').map(([, , s]) => s.advisor + '/' + s.topic)).size
  && reg.counts.crews_used === new Set(stepsOf('crew').map(([, , s]) => s.crew)).size
  && reg.counts.crew_roles_used === new Set(stepsOf('crew').map(([, , s]) => s.crew + '/' + s.role)).size
  && reg.counts.cribs_used === new Set(stepsOf('crib').map(([, , s]) => s.crib)).size);
ok('the ladder counts are re-derived from the edges the registry publishes',
  reg.counts.prerequisite_edges === edges.length
  && reg.counts.ladder_roots === Object.values(reg.ladder.prerequisites).filter((e) => e.length === 0).length
  && reg.counts.ladder_layers === Object.keys(reg.ladder.layers).length
  && reg.counts.edge_reasons === Object.keys(reg.ladder.reasons).length
  && reg.counts.ladder_roots + new Set(edges.map((e) => e.lesson)).size === reg.counts.lessons);

const src = readFileSync(url('./build.py'));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`lessons/test: ${n} checks passed — ${reg.counts.lessons} walkable lessons, `
  + `${reg.counts.steps} steps in ${reg.counts.step_kinds} kinds, standing in `
  + `${reg.counts.rooms_stood_in} rooms across ${reg.counts.halls_covered} of `
  + `${reg.counts.halls_total} halls and ${reg.counts.strands_covered} of `
  + `${reg.counts.strands_total} strands (top hall `
  + `${(reg.spread.max_hall_share * 100).toFixed(2)}% of the set); `
  + `${reg.counts.recording_steps} steps write one of the `
  + `${reg.counts.episode_kinds_declared} episode kinds training/ already has, `
  + `${reg.counts.silent_steps} write nothing and say why; ladder `
  + `${reg.counts.prerequisite_edges} edges over ${reg.counts.ladder_roots} roots, `
  + `depth ${reg.counts.ladder_depth}, acyclic; certifies nobody`);
