/**
 * Advisor and crew registry verification.
 *
 * The whole claim of this pack is that an advisor is a scripted guide with
 * a closed book: it cannot be asked an open question, it invents nothing,
 * and where it states a fact it quotes the record that already holds it
 * rather than keeping a second copy. So the checks are about the shape of
 * that promise - every topic is one of exactly two kinds, every `read`
 * names a binding the page can actually resolve, every `say` cites a file
 * that exists, no advisor claims to be a person or a certification, and
 * nothing anywhere lets talking to one change a score.
 *
 * The crews are the same promise applied to a team rather than a person.
 * A crew names a seat, a room, a set of halls and a set of bindings that
 * other registries already declare, so the checks below are mostly about
 * resolution: nothing a crew points at may be something this pack made up.
 * The structural check is the one worth reading twice - every role has to
 * appear at BOTH ends of its crew's run, because a role nobody hands to
 * and that hands to nobody is a job title rather than a job.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const reg = JSON.parse(readFileSync(new URL('./registry/advisors.json', import.meta.url)));
const page = readFileSync(new URL('../web/trade_craft_3d.html', import.meta.url), 'utf8');
const surf = JSON.parse(readFileSync(
  new URL('../surfaces/registry/finishes.json', import.meta.url)));
const av = JSON.parse(readFileSync(
  new URL('../avatars/registry/avatars.json', import.meta.url)));
const who = reg.advisors;
const all = Object.entries(who);
const topics = all.flatMap(([id, a]) => a.topics.map((t) => [id, t]));

/* ------------------------------------------------------------ the shape --- */
ok('every advisor has a name, a role, a place to stand, a glyph and a greeting',
  all.every(([, a]) => a.name.length > 3 && a.role.length > 10
    && a.stands_in && a.glyph && a.greeting.length > 20));
ok('every advisor stands somewhere real: a room strand, the door, the campus green, or a sim\'s own yard',
  all.every(([, a]) => a.stands_in in surf.base_conditions
    || ['door', 'green', 'yard'].includes(a.stands_in)));
ok('no two advisors stand in the same place - one voice per room',
  new Set(all.map(([, a]) => a.stands_in)).size === all.length);
ok('every topic is a question, and every topic id is unique within its advisor',
  all.every(([, a]) => a.topics.every((t) => t.ask.endsWith('?'))
    && new Set(a.topics.map((t) => t.id)).size === a.topics.length));
ok('a topic is one of exactly two kinds, and nothing else',
  topics.every(([, t]) => t.kind === 'say' || t.kind === 'read'));

/* ------------------------------------------------------- quote, not copy --- */
ok('every `read` topic names a declared binding rather than carrying an answer',
  topics.filter(([, t]) => t.kind === 'read')
    .every(([, t]) => t.bind in reg.bindings && !('say' in t)));
ok('every declared binding is actually used by some advisor - no dead contract',
  Object.keys(reg.bindings).every((b) =>
    topics.some(([, t]) => t.bind === b)));
ok('the page can resolve every binding the registry declares',
  Object.keys(reg.bindings).every((b) => page.includes(`case '${b}'`)));
ok('every `say` topic carries words and names the record it comes from',
  topics.filter(([, t]) => t.kind === 'say')
    .every(([, t]) => t.say.length > 40 && /\.(py|json)$/.test(t.cites)));
ok('the counts the registry publishes are the counts it actually holds',
  reg.counts.advisors === all.length && reg.counts.topics === topics.length
  && reg.counts.read_bindings === Object.keys(reg.bindings).length
  && reg.counts.say_topics
     === topics.filter(([, t]) => t.kind === 'say').length);

/* --------------------------------------------------------------- honesty --- */
ok('the status line refuses the obvious misreading: scripted, no model, no network',
  /not an instructor and not an AI/.test(reg.honesty.status)
  && /no model runs behind one/.test(reg.honesty.status)
  && /no network is reached/.test(reg.honesty.status));
ok('an advisor is not advice: not a certification, a permit or a code ruling',
  /is a certification, a permit, a code ruling/.test(reg.honesty.not_advice)
  && /qualified person on site/.test(reg.honesty.not_advice)
  && /not as any jurisdiction/.test(reg.honesty.not_advice));
ok('an advisor is not a person: no real worker, officer or union local is represented',
  /represents no real worker/.test(reg.honesty.not_a_person)
  && /no real union local is named/.test(reg.honesty.not_a_person));
ok('the book is closed, and says so: the topics listed are all there are',
  /cannot be asked an open question/.test(reg.honesty.closed_book));
ok('no advisor names a real union local, employer or person anywhere in its words',
  !/\bLocal\s+\d|\bIBEW\b|\bUA\s+\d|\bLiUNA\b/i.test(JSON.stringify(reg)));

/* ------------------------------------------------------------ not scored --- */
ok('talking to an advisor changes no score, and the registry states it',
  /changes no score and unlocks nothing/.test(reg.honesty.not_scored)
  && /no grader reads advisor state/.test(reg.honesty.not_scored));
ok('the page never lets advisor state reach a grader',
  page.split(/function (?:score|grade)/).slice(1)
    .every((chunk) => !/advisor/i.test(chunk.slice(0, 2500))));
ok('no topic can gate another: the schema has no field that could express it',
  topics.every(([, t]) => !('requires' in t) && !('unlocks' in t)
    && !('after' in t) && !('score' in t) && !('points' in t)));
ok('and every sentence that mentions locking is one denying that anything is',
  JSON.stringify(reg).split(/(?<=\.)\s|\\n/)
    .filter((s) => /lock/i.test(s))
    .every((s) => /\b(no|not|nothing|never)\b/i.test(s)));

/* ----------------------------------------------------------- the figures --- */
ok('every advisor wears locker options only - a look a learner could also choose',
  all.every(([, a]) => Object.entries(a.crew).every(([sec, pick]) => {
    const s = av.sections.find((x) => x.id === sec);
    return s && s.options.some((o) => o.id === pick);
  })));
ok('the page builds them, places them, and lets them be asked',
  ['function placeAdvisor(', 'function spawnHallAdvisors(',
    'function spawnCampusAdvisors(', 'function openAdvisor(',
    'function advisorNear('].every((f) => page.includes(f)));
ok('every advisor the registry declares actually reaches the page',
  all.every(([id]) => page.includes(`"${id}"`)));

/* --------------------------------------------------------- the operator --- */
// The ninth advisor stands in a simulator's own yard, not a hall room, and
// its topics resolve against the ACTUAL running seat rather than the
// hall's first bound one - the gap the module docstring names by hand.
ok('the operator stands in a sim\'s own yard, a place no other advisor uses',
  who.operator?.stands_in === 'yard'
  && all.filter(([, a]) => a.stands_in === 'yard').length === 1);
ok('every one of the operator\'s topics binds to a seat.* key, never a sim.* one',
  who.operator.topics.every((t) => t.kind === 'read' && t.bind.startsWith('seat.')));
ok('every seat.* binding is used only by the operator - no other advisor reaches into a running seat',
  Object.keys(reg.bindings).filter((b) => b.startsWith('seat.')).every((b) =>
    topics.filter(([, t]) => t.bind === b).every(([id]) => id === 'operator')));
ok('the page places the operator inside startSim(), not spawnHallAdvisors()',
  (() => {
    const fnBody = page.split('function startSim(simId, scenarioId) {')[1]?.slice(0, 4000) ?? '';
    return /placeAdvisor\('operator', sim\.group/.test(fnBody);
  })());
ok('the operator\'s seat.* bindings resolve against curSimId, not seatOf(hall) - the hall/seat scoping bug the docstring names',
  ['seat.task', 'seat.controls', 'seat.dash', 'seat.rubric', 'seat.walkaround', 'seat.trade',
    'seat.procedure']
    .every((b) => {
      const chunk = page.split(`case '${b}':`)[1]?.slice(0, 260) ?? '';
      return /D\.sims\.sims\[curSimId\]/.test(chunk);
    }));
ok('the operator quotes the scripted reference procedure the sims registry declares - the same step list the page\'s policy is written around, never a copy',
  who.operator.topics.some((t) => t.bind === 'seat.procedure')
  && /scripted reference operator/.test(reg.bindings['seat.procedure'])
  && (() => {
    const chunk = page.split("case 'seat.procedure':")[1]?.slice(0, 900) ?? '';
    return /op\.procedure\.map/.test(chunk) && /D\.sims\.operatorHonesty/.test(chunk);
  })());
ok('the operator button only ever shows while a seat is actually running',
  /getElementById\('opBtn'\)/.test(page)
  && /getElementById\('opBtn'\)\.style\.display = 'none'/.test(page));
ok('leaving the seat drops the operator\'s mesh so it never lingers into hall or campus view',
  /function clearOperatorAdvisor/.test(page)
  && page.split('function teardownSim()')[1]?.slice(0, 200)
      .includes('clearOperatorAdvisor()'));

/* ------------------------------------------------------------- the walk --- */
const geo = JSON.parse(readFileSync(
  new URL('../geo/registry/campuses_geo.json', import.meta.url)));
ok('the on-foot answer is measured against RECORDED bands, not invented ones',
  geo.walk.bands_m.ten_minute === 800 && geo.walk.bands_m.fifteen_minute === 1200
  && /Locator\.X src\/walk\.js/.test(geo.walk.provenance));
ok('and it carries the caveat that makes the number honest',
  /not Walk Score/.test(geo.walk.honesty.not_a_score)
  && /straight-line/.test(geo.walk.honesty.straight_line)
  && /Walk the block before you believe/.test(geo.walk.honesty.straight_line)
  && /holds no shop records/.test(geo.walk.honesty.what_it_counts));

/* ------------------------------------------------------------- the crews --- */
// An advisor is one voice in a room; a crew is a team running a task that no
// one person is allowed to run alone. The claim being checked here is that a
// crew invents nothing: the seat it works at, the room it musters in, the
// halls it reaches and every binding it reads are all things some other
// registry already declares. The other claim is structural - a role with no
// place in the run is decoration, and the suite refuses one.
const crewReg = JSON.parse(readFileSync(new URL('./registry/crews.json', import.meta.url)));
const sims = JSON.parse(readFileSync(
  new URL('../sims/registry/sims.json', import.meta.url)));
const unions = JSON.parse(readFileSync(
  new URL('../unions/registry/unions.json', import.meta.url)));
const hallSlugs = new Set(unions.unions.map((u) => u.slug));
const crews = Object.entries(crewReg.crews);
const roles = crews.flatMap(([cid, c]) => Object.entries(c.roles)
  .map(([rid, r]) => [cid, rid, r, c]));
const crewTopics = roles.flatMap(([cid, rid, r]) => r.topics.map((t) => [cid, rid, t]));

ok('every crew works at a seat the simulator registry actually declares',
  crews.length > 0 && crews.every(([, c]) => c.seat in sims.sims));
ok('every crew musters in a room strand the surfaces registry actually declares',
  crews.every(([, c]) => c.muster in surf.base_conditions));
ok('the halls a crew reaches are its seat\'s own halls, read rather than retyped',
  crews.every(([, c]) => c.halls.length === sims.sims[c.seat].halls.length
    && c.halls.every((h, i) => h === sims.sims[c.seat].halls[i])));
ok('every hall a crew reaches is a hall the union registry declares',
  crews.every(([, c]) => c.halls.length > 0 && c.halls.every((h) => hallSlugs.has(h))));
ok('no crew id collides with an advisor id, and every role carries its own computed crew:role key',
  crews.every(([cid]) => !(cid in who))
  && roles.every(([cid, rid, r]) => r.key === `${cid}:${rid}`)
  && new Set(roles.map(([, , r]) => r.key)).size === roles.length);
ok('every role states a job, a glyph, a greeting, and a standing this registry declares',
  roles.every(([, , r]) => r.job.length > 15 && r.glyph && r.greeting.length > 20
    && r.standing in crewReg.standing));
ok('every role stops the work for a condition no other role on any crew owns',
  new Set(roles.map(([, , r]) => r.stops)).size === roles.length);
ok('every crew has at least one role general practice commonly treats as required',
  crews.every(([, c]) => Object.values(c.roles)
    .some((r) => r.standing === 'commonly-required')));
ok('every crew role wears locker options only - a look a learner could also choose',
  roles.every(([, , r]) => Object.entries(r.wears).every(([sec, pick]) => {
    const s = av.sections.find((x) => x.id === sec);
    return s && s.options.some((o) => o.id === pick);
  })));
ok('a crew topic is one of exactly two kinds, is a question, and is unique within its role',
  crewTopics.every(([, , t]) => (t.kind === 'say' || t.kind === 'read')
    && t.ask.endsWith('?'))
  && roles.every(([, , r]) => new Set(r.topics.map((t) => t.id)).size === r.topics.length));
ok('every crew `read` topic names a seat.* binding the advisor registry already declares',
  crewTopics.filter(([, , t]) => t.kind === 'read')
    .every(([, , t]) => t.bind in reg.bindings && t.bind.startsWith('seat.')
      && !('say' in t)));
ok('the page already resolves every binding a crew reaches for - crews need no new binding',
  crewTopics.filter(([, , t]) => t.kind === 'read')
    .every(([, , t]) => page.includes(`case '${t.bind}'`)));
ok('every crew `say` carries words and cites a file, and never restates its seat\'s own task',
  crewTopics.filter(([, , t]) => t.kind === 'say')
    .every(([cid, , t]) => t.say.length > 40 && /\.(py|json)$/.test(t.cites)
      && !t.say.includes(sims.sims[crewReg.crews[cid].seat].task)));
ok('every role appears at both ends of its crew\'s run - no role is decoration',
  crews.every(([, c]) => {
    const by = new Set(c.run.map((s) => s.by)), to = new Set(c.run.map((s) => s.to));
    return Object.keys(c.roles).every((rid) => by.has(rid) && to.has(rid));
  }));
ok('every hand-off names two different roles on that same crew, and says what passes',
  crews.every(([, c]) => c.run.every((s) => s.by in c.roles && s.to in c.roles
    && s.by !== s.to && s.step.length > 25)));
ok('a crew is at least three roles and at least four hand-offs - a pair is not a crew',
  crews.every(([, c]) => Object.keys(c.roles).length >= 3 && c.run.length >= 4));
ok('two crews may share a seat, but never a seat and the room they brief in',
  new Set(crews.map(([, c]) => `${c.seat}/${c.muster}`)).size === crews.length);
ok('no two roles on a crew stand in the same spot, and every post is inside the yard ring',
  crews.every(([, c]) => {
    const degs = Object.values(c.roles).map((r) => r.post.deg);
    return new Set(degs).size === degs.length;
  }) && roles.every(([, , r]) => r.post.r >= 3 && r.post.r <= 9
    && r.post.deg >= 0 && r.post.deg < 360));
ok('the counts the crew registry publishes are the counts it actually holds',
  crewReg.counts.crews === crews.length
  && crewReg.counts.roles === roles.length
  && crewReg.counts.topics === crewTopics.length
  && crewReg.counts.read_topics === crewTopics.filter(([, , t]) => t.kind === 'read').length
  && crewReg.counts.say_topics === crewTopics.filter(([, , t]) => t.kind === 'say').length
  && crewReg.counts.handoffs === crews.reduce((a, [, c]) => a + c.run.length, 0)
  && crewReg.counts.seats === new Set(crews.map(([, c]) => c.seat)).size
  && crewReg.counts.halls_reached
     === new Set(crews.flatMap(([, c]) => c.halls)).size);

/* ------------------------------------------------- what a crew admits to --- */
ok('the crew pack carries the SCRIPTED provenance word and never borrows orbis\'s',
  /^SCRIPTED: /.test(crewReg.honesty.status)
  && /No model runs behind one/.test(crewReg.honesty.status)
  && /no network is reached/.test(crewReg.honesty.status)
  && !/AI-SYNTHESIZED/.test(JSON.stringify(crewReg)));
ok('the crew content admits it is unverified general practice pending journey-level authoring',
  /unverified general practice/.test(crewReg.honesty.unverified)
  && /journey-level practitioners/.test(crewReg.honesty.unverified)
  && /not a reading of any jurisdiction/.test(crewReg.honesty.unverified));
ok('a crew role issues nothing: not a permit, an entry authorisation, a tag or a certificate',
  /is a permit, an entry authorisation, a tag, a certificate/.test(crewReg.honesty.not_a_permit)
  && /this bundle issues none of them/.test(crewReg.honesty.not_a_permit));
ok('a crew role is not a person, and no real union local is named anywhere in the crews',
  /represents no real worker/.test(crewReg.honesty.not_a_person)
  && !/\bLocal\s+\d|\bIBEW\b|\bUA\s+\d|\bLiUNA\b/i.test(JSON.stringify(crewReg)));
ok('standing in a crew is not a gate: no field could express one, and no grader reads one',
  /changes no score and unlocks nothing/.test(crewReg.honesty.not_scored)
  && crewTopics.every(([, , t]) => !('requires' in t) && !('unlocks' in t)
    && !('after' in t) && !('score' in t) && !('points' in t))
  && page.split(/function (?:score|grade)/).slice(1)
    .every((chunk) => !/D\.crews/.test(chunk.slice(0, 2500))));
ok('the page contract names every piece of wiring a crew needs and nothing it does not',
  ['data', 'place', 'ask', 'run', 'episode']
    .every((k) => typeof crewReg.page_contract[k] === 'string'
      && crewReg.page_contract[k].length > 30));
ok('the crew registry was built from the same builder source as the advisors',
  crewReg.source_stamp === reg.source_stamp
  && crewReg.pack_version === reg.pack_version);

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`agents/test: ${n} checks passed — ${all.length} advisors, `
  + `${topics.length} topics, ${Object.keys(reg.bindings).length} bindings; `
  + `${crews.length} crews, ${roles.length} roles, ${crewTopics.length} crew topics, `
  + `${crewReg.counts.handoffs} hand-offs`);
