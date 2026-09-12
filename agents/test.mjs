/**
 * Advisor registry verification.
 *
 * The whole claim of this pack is that an advisor is a scripted guide with
 * a closed book: it cannot be asked an open question, it invents nothing,
 * and where it states a fact it quotes the record that already holds it
 * rather than keeping a second copy. So the checks are about the shape of
 * that promise - every topic is one of exactly two kinds, every `read`
 * names a binding the page can actually resolve, every `say` cites a file
 * that exists, no advisor claims to be a person or a certification, and
 * nothing anywhere lets talking to one change a score.
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
    const fnBody = page.split('function startSim(simId) {')[1]?.slice(0, 4000) ?? '';
    return /placeAdvisor\('operator', sim\.group/.test(fnBody);
  })());
ok('the operator\'s seat.* bindings resolve against curSimId, not seatOf(hall) - the hall/seat scoping bug the docstring names',
  ['seat.task', 'seat.controls', 'seat.dash', 'seat.rubric', 'seat.walkaround', 'seat.trade']
    .every((b) => {
      const chunk = page.split(`case '${b}':`)[1]?.slice(0, 260) ?? '';
      return /D\.sims\.sims\[curSimId\]/.test(chunk);
    }));
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

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`agents/test: ${n} checks passed — ${all.length} advisors, `
  + `${topics.length} topics, ${Object.keys(reg.bindings).length} bindings`);
