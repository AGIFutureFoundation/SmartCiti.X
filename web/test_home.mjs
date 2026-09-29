/**
 * The front door and the course page, held to the registries they claim to read.
 *
 * `web/build_home.py` writes `index.html` and `web/build_lessons.py` writes
 * `web/trade_craft_lessons.html`. Between them they now make one promise a
 * visitor can act on: here is what you can do, here is one lesson to start
 * with, and here is your trade's course - every lesson that stands in your
 * hall, in the order this bundle's own ladder puts them, with each step
 * linking to the simulator seat it opens and saying so where it opens none.
 * Every part of that promise is a claim about a registry. This suite
 * recomputes each claim from the registry that owns it and holds the SHIPPED
 * PAGES to the answer.
 *
 * WHICH FILE EACH CHECK READS is in its message, always, because this bundle
 * has been bitten by a check that matched a GENERATOR's comment quoting the
 * string it was hunting for in the PAGE:
 *
 *   [registry]  the registries only - no page involved
 *   [shipped]   the built HTML, and the data attributes embedded in it
 *   [generator] the two generators' own source, comments stripped
 *   [browser]   the rendered DOM in headless Chromium (--browser only)
 *
 * MATCH STRUCTURE, NEVER A SENTENCE. Every check below reads an element, an
 * id, an href or a data attribute: `data-fig`, `data-tier`, `data-limit`,
 * `data-hall`, `data-course-step`, `data-seat`, `data-cell-seat`,
 * `data-start-lesson`. A check that searched the prose would match the
 * pages' own honest explanations - one in this bundle flagged the word
 * AI-SYNTHESIZED inside a sentence explaining that the word belongs to
 * another pack, and flagged the trade acronym HVAC as a provenance tier. So
 * the provenance check here reads `data-tier` attributes and nothing else,
 * and the figure checks read the text of a keyed `data-fig` and nothing else.
 *
 * NO BROWSER BY DEFAULT. verify_all.sh reaches no network and opens no
 * browser, so the default run is static. `--browser` adds the DOM checks
 * against a served copy; it needs a server on the pages' origin and
 * playwright, and it says so if it cannot reach one.
 *
 *   node web/test_home.mjs
 *   node web/test_home.mjs --browser [--origin=http://127.0.0.1:8811]
 *   node web/test_home.mjs --home=/tmp/broken.html --root=/tmp/broken-root
 *
 * `--home`, `--lessons` and `--root` exist for the mutation tests: point the
 * suite at a broken copy of a page, or at a broken copy of the registries,
 * and watch the check that covers that fault fail by name. A check nobody
 * has watched fail is not a check.
 */
import { readFileSync, statSync, existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const arg = (name) => {
  const hit = args.find((a) => a.startsWith(`--${name}=`));
  return hit === undefined ? null : hit.slice(name.length + 3);
};
const ROOT = resolve(arg('root') !== null ? arg('root') : join(HERE, '..'));
const HOME = resolve(arg('home') !== null ? arg('home') : join(ROOT, 'index.html'));
const LESSON_PAGE = resolve(arg('lessons') !== null ? arg('lessons')
  : join(HERE, 'trade_craft_lessons.html'));
const HOME_GEN = join(HERE, 'build_home.py');
const LESSON_GEN = join(HERE, 'build_lessons.py');
const ORIGIN = arg('origin') !== null ? arg('origin') : 'http://127.0.0.1:8811';
const WANT_BROWSER = args.includes('--browser');

let n = 0, bad = 0;
const ok = (m, c, evidence = []) => {
  if (c) { n++; console.log('  ok  ' + m); return; }
  bad++;
  console.log('FAIL  ' + m);
  for (const e of evidence) console.log('      ' + e);
};

const readJSON = (rel) => JSON.parse(readFileSync(join(ROOT, rel), 'utf8'));
const home = readFileSync(HOME, 'utf8');
const learner = readFileSync(LESSON_PAGE, 'utf8');

/* ------------------------------------------------------------ registries -- */
const LESSONS_PATH = 'lessons/registry/lessons.json';
const SIMS_PATH = 'sims/registry/sims.json';
const SKILLS_PATH = 'pack/registry/skills.json';
const HALLS_PATH = 'pack/registry/halls.json';
const UNIONS_PATH = 'unions/registry/unions.json';
const SIGNOFF_PATH = 'pack/hall_signoff.mjs';

const lessonsReg = readJSON(LESSONS_PATH);
const simsReg = readJSON(SIMS_PATH);
const skillsReg = readJSON(SKILLS_PATH);
const hallsReg = readJSON(HALLS_PATH);
const unionsReg = readJSON(UNIONS_PATH);
const { claimsHallSignoff } = await import(pathToFileURL(join(ROOT, SIGNOFF_PATH)).href);

const LESSONS = lessonsReg.lessons;
const LIDS = Object.keys(LESSONS);
const KINDS = lessonsReg.step_kinds;
const PREREQS = lessonsReg.ladder.prerequisites;
const LAYERS = lessonsReg.ladder.layers;
const BINDINGS = simsReg.hall_bindings;
const SIMS = simsReg.sims;

/* Everything the pages claim, recomputed here from the registries - a second,
   independent count, written without looking at either generator's arithmetic. */

/* Which KINDS of step reach a seat. Derived the same way the generators
   derive it and for the same reason: `step_kinds` declares the file each kind
   reads, and the kinds that read the simulator registry are the kinds that
   stand a learner in a seat. A list typed here would agree with a list typed
   there and both could be wrong together. */
const SEAT_KINDS = new Set(Object.entries(KINDS)
  .filter(([, spec]) => spec.reads === SIMS_PATH).map(([k]) => k));
const seatOf = (s) => (SEAT_KINDS.has(s.kind) ? s.sim : null);

/* The courses: one per hall a lesson stands in, its lessons in ladder-layer
   order with the registry's own key order breaking ties. */
const LAYER_OF = new Map();
for (const [depth, ids] of Object.entries(LAYERS)) for (const id of ids) LAYER_OF.set(id, Number(depth));
const KEY_ORDER = new Map(LIDS.map((id, i) => [id, i]));
const courseOf = new Map();
for (const id of LIDS) {
  const hall = LESSONS[id].hall;
  if (!courseOf.has(hall)) courseOf.set(hall, []);
  courseOf.get(hall).push(id);
}
for (const ids of courseOf.values()) {
  ids.sort((a, b) => (LAYER_OF.get(a) - LAYER_OF.get(b)) || (KEY_ORDER.get(a) - KEY_ORDER.get(b)));
}
const HALL_NAME = new Map(hallsReg.halls.map((h) => [h.slug, h.name]));
const COURSE_HALLS = lessonsReg.spread.halls;
const COURSES = COURSE_HALLS.map((hall) => {
  const ids = courseOf.get(hall);
  const steps = ids.flatMap((id) => LESSONS[id].steps);
  return {
    hall,
    name: HALL_NAME.get(hall),
    ids,
    lessons: ids.length,
    steps: steps.length,
    seatSteps: steps.filter((s) => seatOf(s) !== null).length,
  };
});

const HALLS = unionsReg.count;
const CAMPUSES = Object.keys(readJSON('geo/registry/campuses_geo.json').campuses).length;
const SEATS = Object.keys(SIMS).length;
const COURSE_COUNT = COURSES.length;
const HALLS_WITHOUT_COURSE = HALLS - COURSE_COUNT;
const COURSES_WITH_A_SEAT = COURSES.filter((c) => c.seatSteps > 0).length;
const COURSES_WITHOUT_A_SEAT = COURSE_COUNT - COURSES_WITH_A_SEAT;
const HALLS_SIGNED_OFF = hallsReg.halls.filter((h) => claimsHallSignoff(h.content_status)).length;

/* The ladder's rungs, the rungs a seat stands on, and - recomputed rather
   than read from the block it is compared against - how many of those sit on
   a prerequisite chain that carries no seat at all. Fails closed on a
   dangling prerequisite: an unresolvable chain is not an empty chain. */
const CELLS_TOTAL = skillsReg.count;
const CELL = new Map(skillsReg.skills.map((s) => [s.skill_id, s]));
const CELLS_WITH_SEAT = new Set(Object.values(BINDINGS).flat().map((b) => b.skill_id));
const closure = (cell) => {
  const seen = new Set(); const stack = [cell];
  while (stack.length) {
    const row = CELL.get(stack.pop());
    if (!row) return null;
    for (const r of row.requires) if (!seen.has(r)) { seen.add(r); stack.push(r); }
  }
  return seen;
};
const UNREACHED = [...CELLS_WITH_SEAT].filter((c) => {
  const pre = closure(c);
  return pre !== null && ![...pre].some((p) => CELLS_WITH_SEAT.has(p));
});

/* The one lesson the front door sends a first-time visitor to: the first in
   the registry's own order that stands at the foot of the ladder and whose
   steps reach a seat. */
const START = LIDS.find((id) => PREREQS[id].length === 0
  && LESSONS[id].steps.some((s) => seatOf(s) !== null));

/* ---------------------------------------------------------- tiny HTML -- */
/* Attribute readers. Structural: they match a tag and pull an attribute or
   the text of a keyed element. Nothing here reads a sentence. */
const attrAll = (html, attr) =>
  [...html.matchAll(new RegExp(`\\b${attr}="([^"]*)"`, 'g'))].map((m) => m[1]);
const figOf = (html, key) => {
  const m = html.match(new RegExp(`<b class="fig" data-fig="${key}">([^<]*)</b>`));
  return m === null ? null : m[1].replace(/,/g, '');
};
const hrefsTo = (html, prefix) =>
  [...html.matchAll(/href="([^"]*)"/g)].map((m) => m[1]).filter((h) => h.startsWith(prefix));
/* One course section, start tag to the start of the next - enough to read
   the attributes and the elements inside it without parsing HTML. */
const courseBlocks = (html) => {
  const out = new Map();
  const starts = [...html.matchAll(/<section class="course" id="course-([a-z0-9-]+)"[^>]*>/g)];
  starts.forEach((m, i) => {
    const end = i + 1 < starts.length ? starts[i + 1].index : html.length;
    out.set(m[1], html.slice(m.index, end));
  });
  return out;
};

/* =========================================================== [registry] === */
ok('[registry] every hall a lesson stands in is a hall pack/registry/halls.json holds, and '
  + `lessons/registry/lessons.json's own spread.halls names exactly those ${COURSE_COUNT} halls`,
  COURSE_HALLS.every((h) => HALL_NAME.has(h))
  && JSON.stringify([...courseOf.keys()].sort()) === JSON.stringify([...COURSE_HALLS].sort()),
  [`spread ${COURSE_HALLS.length}, lessons stand in ${courseOf.size}`]);

ok('[registry] the ladder layers place every lesson exactly once, so a course has one order and '
  + 'not a choice of orders',
  LIDS.every((id) => LAYER_OF.has(id))
  && Object.values(LAYERS).flat().length === LIDS.length
  && new Set(Object.values(LAYERS).flat()).size === LIDS.length,
  [`${Object.values(LAYERS).flat().length} placements for ${LIDS.length} lessons`]);

ok('[registry] which steps reach a seat is decided by the step kind\'s own declared `reads`, not '
  + `by a list: the ${SEAT_KINDS.size} kinds that read ${SIMS_PATH} are exactly the kinds whose `
  + 'steps carry a seat, and no other step carries one',
  SEAT_KINDS.size > 0
  && LIDS.every((id) => LESSONS[id].steps.every((s) => (SEAT_KINDS.has(s.kind)
    ? typeof s.sim === 'string' && s.sim in SIMS
    : !('sim' in s)))),
  [`seat kinds=[${[...SEAT_KINDS]}]`]);

ok('[registry] the courses hold every step the registry holds and no step twice: '
  + `${COURSES.reduce((a, c) => a + c.steps, 0)} across ${COURSE_COUNT} courses`,
  COURSES.reduce((a, c) => a + c.steps, 0) === lessonsReg.counts.steps
  && COURSES.reduce((a, c) => a + c.lessons, 0) === LIDS.length,
  [`courses ${COURSES.reduce((a, c) => a + c.steps, 0)}, registry ${lessonsReg.counts.steps}`]);

ok('[registry] the seats stand on a thin slice of the ladder, and this suite walks the '
  + `prerequisite chains itself to say so: ${CELLS_WITH_SEAT.size} of ${CELLS_TOTAL} rungs carry a `
  + `seat and all ${UNREACHED.length} of those sit on a chain with no seat anywhere in it`,
  UNREACHED.length === simsReg.coverage.unreachable_seat_cells.length
  && UNREACHED.length === CELLS_WITH_SEAT.size && CELLS_WITH_SEAT.size > 0,
  [`recomputed ${UNREACHED.length}, registry ${simsReg.coverage.unreachable_seat_cells.length}, `
   + `covered ${CELLS_WITH_SEAT.size}`]);

ok(`[registry] ${HALLS_SIGNED_OFF} of ${HALLS} halls claim a practitioner sign-off, decided by `
  + `${SIGNOFF_PATH}'s own claimsHallSignoff() rather than by this suite matching a status string`,
  HALLS_SIGNED_OFF === 0 && hallsReg.halls.length === HALLS,
  [`signed off ${HALLS_SIGNED_OFF}, halls ${hallsReg.halls.length}, roster ${HALLS}`]);

ok('[registry] a first step exists to send a visitor to at all: some lesson stands at the foot of '
  + 'the ladder and reaches a seat',
  START !== undefined && PREREQS[START].length === 0
  && LESSONS[START].steps.some((s) => seatOf(s) !== null),
  [`start=${START}`]);

/* ============================================================ [shipped] === */
/* ---- the front door -------------------------------------------------- */
{
  const want = {
    courses: COURSE_COUNT, halls: HALLS, halls_without_course: HALLS_WITHOUT_COURSE,
    halls_walkable: HALLS, campuses: CAMPUSES, seats: SEATS,
    courses_with_a_seat: COURSES_WITH_A_SEAT, courses_listed: COURSE_COUNT,
    courses_without_a_seat: COURSES_WITHOUT_A_SEAT,
    halls_signed_off: HALLS_SIGNED_OFF, halls_signoff_total: HALLS,
    cells_with_seat: CELLS_WITH_SEAT.size, cells_total: CELLS_TOTAL,
    cells_with_seat_unreached: UNREACHED.length,
  };
  const wrong = Object.entries(want)
    .filter(([k, v]) => figOf(home, k) !== String(v))
    .map(([k, v]) => `${k}: page=${figOf(home, k)} registry=${v}`);
  ok(`[shipped] index.html: every one of the ${Object.keys(want).length} figures the way-in section `
    + 'states sits in its own data-fig slot and equals the registry figure it names'
    + (wrong.length ? ` - ${wrong.slice(0, 4).join('; ')}` : ''),
    wrong.length === 0, wrong);
  ok('[shipped] index.html: and no data-fig slot on the page is one this suite does not check, so '
    + 'a figure cannot be added to the way-in section without a check arriving with it',
    attrAll(home, 'data-fig').every((k) => k in want)
    && attrAll(home, 'data-fig').length === Object.keys(want).length,
    [`page slots=[${attrAll(home, 'data-fig')}]`]);
}

{
  const m = home.match(/<a class="card lead start" id="start-here" data-start-lesson="([^"]*)" '?'?data-start-hall="([^"]*)" href="([^"]*)"/)
    || home.match(/data-start-lesson="([^"]*)"[^>]*data-start-hall="([^"]*)"[^>]*href="([^"]*)"/);
  ok('[shipped] index.html: the start card names the lesson the registry\'s own order picks - the '
    + 'first root lesson that reaches a seat - and opens that lesson\'s own hall course through '
    + '?hall=, the deep link the rest of this bundle already answers to',
    m !== null && m[1] === START && m[2] === LESSONS[START].hall
    && m[3] === `web/trade_craft_lessons.html?hall=${LESSONS[START].hall}`,
    m === null ? ['no start card with data-start-lesson on the page']
      : [`card lesson=${m[1]} hall=${m[2]} href=${m[3]}`, `registry start=${START}`]);
}

{
  const links = [...home.matchAll(
    /<a class="trade" data-hall="([^"]*)" data-course-lessons="(\d+)" data-course-steps="(\d+)" data-course-seat-steps="(\d+)" href="([^"]*)"/g)];
  const bySlug = new Map(links.map((m) => [m[1], m]));
  const wrong = COURSES.filter((c) => {
    const m = bySlug.get(c.hall);
    return !m || Number(m[2]) !== c.lessons || Number(m[3]) !== c.steps
      || Number(m[4]) !== c.seatSteps
      || m[5] !== `web/trade_craft_lessons.html?hall=${c.hall}`;
  }).map((c) => `${c.hall}: registry ${c.lessons}/${c.steps}/${c.seatSteps}`);
  ok(`[shipped] index.html: one trade link per course and not one more - ${COURSE_COUNT} links, no `
    + 'slug twice, none naming a hall with no course',
    links.length === COURSE_COUNT && bySlug.size === COURSE_COUNT
    && COURSES.every((c) => bySlug.has(c.hall)),
    [`page ${links.length} links, ${bySlug.size} distinct; registry ${COURSE_COUNT}`]);
  ok('[shipped] index.html: and each trade link carries that course\'s own lesson, step and '
    + 'seat-step counts, read from the lessons registry rather than typed beside it'
    + (wrong.length ? ` - ${wrong.slice(0, 3).join('; ')}` : ''),
    wrong.length === 0, wrong);
}

ok('[shipped] index.html: the front door invents no second deep-link scheme - every link into the '
  + 'lessons page carries ?hall= and nothing else',
  hrefsTo(home, 'web/trade_craft_lessons.html').length > 0
  && hrefsTo(home, 'web/trade_craft_lessons.html')
    .every((h) => h === 'web/trade_craft_lessons.html'
      || /^web\/trade_craft_lessons\.html\?hall=[a-z0-9-]+$/.test(h)),
  hrefsTo(home, 'web/trade_craft_lessons.html').filter(
    (h) => !/^web\/trade_craft_lessons\.html(\?hall=[a-z0-9-]+)?$/.test(h)).slice(0, 4));

{
  const limits = attrAll(home, 'data-limit');
  const startSection = home.slice(home.indexOf('<section id="start">'),
    home.indexOf('<section id="surfaces">'));
  ok('[shipped] index.html: the limits are stated once and where a visitor meets them - five keyed '
    + 'limit blocks, every one of them inside the way-in section and none of them repeated further '
    + 'down the page',
    limits.length === 5 && new Set(limits).size === 5
    && attrAll(startSection, 'data-limit').length === 5,
    [`page=[${limits}] in the way-in section=${attrAll(startSection, 'data-limit').length}`]);
  ok('[shipped] index.html: the certification limit and the coverage limit are among them, so the '
    + 'two things a training coordinator must not miss cannot be dropped silently',
    limits.includes('certification') && limits.includes('coverage')
    && limits.includes('signoff'),
    [`page=[${limits}]`]);
}

{
  const TIERS = ['RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED', 'SCRIPTED'];
  const tiers = attrAll(home, 'data-tier');
  ok('[shipped] index.html: every word rendered AS a provenance tier is one of the five, read from '
    + 'data-tier slots and nowhere else - AI-SYNTHESIZED belongs to orbis/ and is not among them',
    tiers.length === TIERS.length && tiers.every((t) => TIERS.includes(t))
    && new Set(tiers).size === TIERS.length,
    [`page=[${tiers}]`]);
}

/* ---- the course page ------------------------------------------------- */
const blocks = courseBlocks(learner);
ok(`[shipped] trade_craft_lessons.html: one course section per hall a lesson stands in - `
  + `${COURSE_COUNT} sections, keyed by hall slug, none missing and none invented`,
  blocks.size === COURSE_COUNT && COURSES.every((c) => blocks.has(c.hall)),
  [`page ${blocks.size}, registry ${COURSE_COUNT}`,
    `missing=[${COURSES.filter((c) => !blocks.has(c.hall)).map((c) => c.hall)}]`]);

{
  const wrong = COURSES.filter((c) => {
    const b = blocks.get(c.hall);
    if (!b) return true;
    const a = (k) => (b.match(new RegExp(`^<section[^>]*\\b${k}="([^"]*)"`)) || [])[1];
    return a('data-lessons') !== String(c.lessons) || a('data-steps') !== String(c.steps)
      || a('data-seat-steps') !== String(c.seatSteps);
  }).map((c) => `${c.hall}: registry ${c.lessons}/${c.steps}/${c.seatSteps}`);
  ok('[shipped] trade_craft_lessons.html: each course states its own lesson, step and seat-step '
    + 'counts, and each equals the count over the lessons that hall actually holds'
    + (wrong.length ? ` - ${wrong.slice(0, 3).join('; ')}` : ''),
    wrong.length === 0, wrong);
}

{
  const wrong = [];
  for (const c of COURSES) {
    // A hall the registry gives a course but the built page has no block for
    // is a named failure, not a crash - the page is stale against the registry.
    if (!blocks.has(c.hall)) { wrong.push(`${c.hall}: no course block on the page`); continue; }
    const got = [...blocks.get(c.hall).matchAll(/<article class="lesson" id="lesson-([^"]+)"/g)]
      .map((m) => m[1]);
    if (JSON.stringify(got) !== JSON.stringify(c.ids)) wrong.push(`${c.hall}: [${got}] != [${c.ids}]`);
  }
  ok('[shipped] trade_craft_lessons.html: every lesson sits inside its own hall\'s course and in '
    + 'the order the ladder layers put it - not the registry\'s key order dressed as a sequence'
    + (wrong.length ? ` - ${wrong.slice(0, 3).join('; ')}` : ''),
    wrong.length === 0, wrong);
}

{
  const wrong = [];
  for (const c of COURSES) {
    const got = [...blocks.get(c.hall).matchAll(/data-course-step="(\d+)"/g)].map((m) => Number(m[1]));
    const want = Array.from({ length: c.steps }, (_, i) => i + 1);
    if (JSON.stringify(got) !== JSON.stringify(want)) wrong.push(`${c.hall}: ${got.length} steps`);
  }
  ok('[shipped] trade_craft_lessons.html: the steps of a course are numbered straight through from '
    + '1 to its own step count, in order, with no gap and no restart at a lesson boundary'
    + (wrong.length ? ` - ${wrong.slice(0, 3).join('; ')}` : ''),
    wrong.length === 0, wrong);
}

{
  const wrong = [];
  for (const c of COURSES) {
    const b = blocks.get(c.hall);
    const seats = [...b.matchAll(/<p class="sseat">(.*?)<\/p>/g)].map((m) => m[1]);
    const want = c.ids.flatMap((id) => LESSONS[id].steps.map((s) => seatOf(s)));
    if (seats.length !== want.length) { wrong.push(`${c.hall}: ${seats.length} seat lines, ${want.length} steps`); continue; }
    want.forEach((sim, i) => {
      const line = seats[i];
      if (sim === null) {
        if (!line.includes('data-seat="none"')) wrong.push(`${c.hall} step ${i + 1}: no data-seat="none"`);
      } else {
        const href = `href="trade_craft_3d.html?hall=${c.hall}&amp;sim=${sim}"`;
        if (!line.includes(href) || !line.includes(`data-seat="${sim}"`)) {
          wrong.push(`${c.hall} step ${i + 1}: expected ${href}`);
        }
      }
    });
  }
  ok('[shipped] trade_craft_lessons.html: every step says whether a seat stands in it - the ones '
    + 'that reach a seat link into that seat through ?hall=&sim=, and the ones that do not carry '
    + 'data-seat="none" rather than leaving a reader to assume a machine is behind every step'
    + (wrong.length ? ` - ${wrong.slice(0, 3).join('; ')}` : ''),
    wrong.length === 0, wrong);
}

{
  const wrong = [];
  for (const c of COURSES) {
    for (const id of c.ids) {
      const b = blocks.get(c.hall);
      const art = b.slice(b.indexOf(`id="lesson-${id}"`));
      const head = art.slice(0, art.indexOf('</header>'));
      if (!head.includes(`href="trade_craft_ladder.html?hall=${c.hall}"`)) {
        wrong.push(`${id}: no ladder deep link for ${c.hall}`);
      }
      /* Read the attribute off EACH element that carries it, and require both
         to agree with the registry. The header states it twice - once on the
         article, once on the visible marker - and an earlier version of this
         check asked only whether the right value appeared SOMEWHERE in the
         header. That passes while the two disagree, which is the shape of a
         check that goes green forever while the thing it guards rots: a
         mutation that flipped the article's value alone did not trip it. */
      const want = CELLS_WITH_SEAT.has(LESSONS[id].skill_id) ? 'yes' : 'no';
      const onArticle = (head.match(/^[^>]*\bdata-cell-seat="([^"]*)"/) || [])[1];
      const onMarker = (head.match(/<span class="cellseat" data-cell-seat="([^"]*)"/) || [])[1];
      if (onArticle !== want) wrong.push(`${id}: article cell-seat=${onArticle}, want ${want}`);
      if (onMarker !== want) wrong.push(`${id}: marker cell-seat=${onMarker}, want ${want}`);
    }
  }
  ok('[shipped] trade_craft_lessons.html: every lesson links through to its own trade\'s ladder and '
    + 'marks whether a seat stands on the rung it teaches - yes for exactly the '
    + `${LIDS.filter((id) => CELLS_WITH_SEAT.has(LESSONS[id].skill_id)).length} lessons `
    + 'hall_bindings binds a seat to that cell, no for the rest'
    + (wrong.length ? ` - ${wrong.slice(0, 3).join('; ')}` : ''),
    wrong.length === 0, wrong);
}

{
  const opts = [...learner.matchAll(/<option value="([a-z0-9-]+)">/g)].map((m) => m[1]);
  ok('[shipped] trade_craft_lessons.html: the course picker offers exactly the courses that exist, '
    + 'so a reader cannot be offered a trade with nothing behind it',
    JSON.stringify(opts) === JSON.stringify(COURSES.map((c) => c.hall)),
    [`picker=[${opts.slice(0, 4)}...] (${opts.length})`, `registry ${COURSE_COUNT}`]);
}

ok('[shipped] trade_craft_lessons.html: the course page invents no deep-link scheme either - every '
  + 'query string it emits is ?hall=, ?sim= or the two together',
  [...learner.matchAll(/href="([^"]*\?[^"]*)"/g)].map((m) => m[1])
    .every((h) => /\?hall=[a-z0-9-]+(&amp;sim=[a-z0-9-]+)?$/.test(h) || /\?sim=[a-z0-9-]+$/.test(h)),
  [...learner.matchAll(/href="([^"]*\?[^"]*)"/g)].map((m) => m[1])
    .filter((h) => !/\?hall=[a-z0-9-]+(&amp;sim=[a-z0-9-]+)?$/.test(h) && !/\?sim=[a-z0-9-]+$/.test(h))
    .slice(0, 4));

/* ========================================================== [generator] === */
{
  const strip = (src) => src.replace(/"""[\s\S]*?"""/g, ' ').replace(/^\s*#.*$/gm, ' ');
  const hs = strip(readFileSync(HOME_GEN, 'utf8'));
  const ls = strip(readFileSync(LESSON_GEN, 'utf8'));
  ok('[generator] neither generator substitutes a default for a missing registry field: no bare `??`, '
    + 'no `.get(` with a fallback - a missing field fails the build naming the path instead',
    !/\?\?/.test(hs) && !/\?\?/.test(ls)
    && !/\.get\([^)]*,/.test(hs) && !/\.get\([^)]*,/.test(ls),
    [`build_home.py .get hits: ${(hs.match(/\.get\([^)]*,/g) || []).length}`,
      `build_lessons.py .get hits: ${(ls.match(/\.get\([^)]*,/g) || []).length}`]);
  ok('[generator] both generators name, as literal strings, every registry they read a course figure '
    + 'out of - so a scan for the readers of a registry finds them',
    [LESSONS_PATH, SIMS_PATH, SKILLS_PATH, HALLS_PATH].every((p) => hs.includes(p))
    && [LESSONS_PATH, SIMS_PATH, SKILLS_PATH].every((p) => ls.includes(p)),
    [`build_home.py names ${[LESSONS_PATH, SIMS_PATH, SKILLS_PATH, HALLS_PATH]
      .filter((p) => hs.includes(p)).length}/4`]);
  ok('[generator] and each reads the required field through a need() that fails by name, rather '
    + 'than indexing a registry blind',
    /def need\(/.test(hs) && /def need\(/.test(ls)
    && (hs.match(/need\(/g) || []).length > 20 && (ls.match(/need\(/g) || []).length > 20,
    [`need() calls: home ${(hs.match(/need\(/g) || []).length}, `
     + `lessons ${(ls.match(/need\(/g) || []).length}`]);
}

/* ================================================== [declared surfaces] === */
/* The floor plans, the contribution page and the site plans. Each card on the
   front door is READ from that surface's own registry: the body, the limit and
   the badge name the field they came from in `data-from`, and this block opens
   that registry and holds the shipped text to the field verbatim - so a
   description typed into the generator, however plausible, fails here. */
{
  const DECLARED = {
    'web/trade_craft_spaces.html': 'spaces/registry/spaces.json',
    'web/trade_craft_contribute.html': 'contrib/registry/contrib.json',
    'web/trade_craft_worksites.html': 'worksites/registry/worksites.json',
  };
  const escLike = (t) => String(t).split(/\s+/).join(' ').trim()
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const resolveField = (reg, path) => {
    let node = reg;
    for (const part of path.split('.')) {
      const m = /^([^[]+)((?:\[\d+\])*)$/.exec(part);
      if (!m || node === null || typeof node !== 'object' || !(m[1] in node)) return undefined;
      node = node[m[1]];
      for (const [, i] of m[2].matchAll(/\[(\d+)\]/g)) node = Array.isArray(node) ? node[Number(i)] : undefined;
    }
    return node;
  };
  const cardRe = /<a class="card(?: lead)?" href="([^"]*)"(?: data-declared="([^"]*)")?>([\s\S]*?)<\/a>/g;
  const cards = new Map([...home.matchAll(cardRe)].map((m) => [m[1], { declared: m[2], inner: m[3] }]));
  const { existsSync } = await import('node:fs');
  const missing = Object.keys(DECLARED).filter((h) => !cards.has(h));
  const dangling = Object.keys(DECLARED).filter((h) => !existsSync(join(ROOT, h)));
  ok('[shipped] index.html: the front door links the floor plans, the contribution page and the site '
    + 'plans as cards, and each href resolves to a built page under the bundle root',
    missing.length === 0 && dangling.length === 0,
    [...missing.map((h) => `no card for ${h}`), ...dangling.map((h) => `${h} does not exist under ${ROOT}`)]);

  const wrong = [];
  const slots = [];
  for (const [href, regPath] of Object.entries(DECLARED)) {
    const c = cards.get(href);
    if (!c) { wrong.push(`${href}: no card`); continue; }
    if (c.declared !== regPath) wrong.push(`${href}: data-declared=${c.declared}, want ${regPath}`);
    let reg;
    try { reg = readJSON(regPath); } catch (e) { wrong.push(`${href}: cannot read ${regPath}`); continue; }
    const found = [...c.inner.matchAll(/<(span|p)( class="[^"]*")?( data-badge)? data-from="([^"]*)"[^>]*>([\s\S]*?)<\/\1>/g)];
    const byKind = { badge: null, body: null, limit: null };
    for (const m of found) {
      const kind = m[3] ? 'badge' : /class="limit"/.test(m[2] || '') ? 'limit' : 'body';
      byKind[kind] = { from: m[4], text: m[5].replace(/<span class="limit-tag">[^<]*<\/span>/, '') };
    }
    for (const kind of ['badge', 'body', 'limit']) {
      const s = byKind[kind];
      if (!s) { wrong.push(`${href}: no ${kind} slot with data-from`); continue; }
      const [file, field] = s.from.split('#');
      if (file !== regPath || !field) { wrong.push(`${href} ${kind}: data-from=${s.from} is not a field of ${regPath}`); continue; }
      const value = resolveField(reg, field);
      if (typeof value !== 'string' || !value.trim()) { wrong.push(`${href} ${kind}: ${s.from} is not a non-empty string in the registry`); continue; }
      const want = escLike(kind === 'badge' ? value.split(':')[0] : value);
      if (s.text !== want) wrong.push(`${href} ${kind}: shipped "${s.text.slice(0, 60)}..." != ${s.from} "${want.slice(0, 60)}..."`);
      slots.push({ href, kind, value });
    }
  }
  ok('[shipped] index.html: each of the three cards\' badge, body and limit names the registry field it '
    + 'was read from (data-from="<registry>#<field>") and the shipped text IS that field verbatim - the '
    + 'badge its head clause before the first colon, the body and limit the whole sentence',
    wrong.length === 0 && slots.length === 9, wrong);

  const strip = (src) => src.replace(/"""[\s\S]*?"""/g, ' ').replace(/^\s*#.*$/gm, ' ');
  const hs = strip(readFileSync(HOME_GEN, 'utf8'));
  const typed = slots.filter((s) => hs.includes(s.value.slice(0, 48)));
  ok('[generator] build_home.py names the three registries as literal paths and types none of the nine '
    + 'sentences it ships for them - the registry, not the generator, is where every one lives',
    Object.values(DECLARED).every((p) => hs.includes(p)) && typed.length === 0 && slots.length === 9,
    typed.map((s) => `${s.href} ${s.kind} appears verbatim in build_home.py`));
}

/* index.html's escaping, as build_home.py's esc() does it: whitespace
   collapsed, then & < > escaped. */
const escLikeHome = (t) => String(t).split(/\s+/).join(' ').trim()
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/* ====================================================== [front door] === */
/* The structure the front door was rebuilt around: one h1 and an outline
   that never skips a level; hero figures that each name the registry they
   were counted from; two calls to action and five audience paths that land
   on built pages; the learner loop drawn from web/sitenav.py's own LOOP with
   pictures that ship; and what a record proves, word for word from the
   registry the verifier is built on. Every check reads markup, never prose. */
{
  const { existsSync, readFileSync: rf, readdirSync } = await import('node:fs');
  const { execFileSync } = await import('node:child_process');
  const bare = home.replace(/<script\b[\s\S]*?<\/script>/g, '');

  /* -- one h1, and an outline that never skips a level ------------------ */
  const levels = [...bare.matchAll(/<h([1-6])\b/g)].map((m) => Number(m[1]));
  const skips = levels.map((l, i) => (i && l > levels[i - 1] + 1 ? `h${levels[i - 1]} -> h${l}` : null))
    .filter(Boolean);
  ok('[shipped] index.html: exactly one <h1>, it is the first heading, and no heading skips a level '
    + `on the way down (${levels.length} headings)`,
    levels.filter((l) => l === 1).length === 1 && levels[0] === 1 && skips.length === 0,
    [`h1 count=${levels.filter((l) => l === 1).length} first=h${levels[0]}`, ...skips.slice(0, 4)]);

  /* -- the hero figures: each one names its registry and equals a recount - */
  const finishes = readJSON('surfaces/registry/finishes.json');
  const readme = rf(join(ROOT, 'README.md'), 'utf8');
  const STAT_RULES = {
    halls: ['unions/registry/unions.json#count', () => unionsReg.count],
    campuses: ['geo/registry/campuses_geo.json#campuses', () => CAMPUSES],
    seats: ['sims/registry/sims.json#sims', () => SEATS],
    lessons: ['lessons/registry/lessons.json#counts.lessons',
      () => (lessonsReg.counts.lessons === LIDS.length ? LIDS.length : NaN)],
    steps: ['lessons/registry/lessons.json#counts.steps',
      () => (lessonsReg.counts.steps === LIDS.reduce((a, id) => a + LESSONS[id].steps.length, 0)
        ? lessonsReg.counts.steps : NaN)],
    modules: ['README.md', null],
    surfaces: ['surfaces/registry/finishes.json#catalogue+wall_catalogue',
      () => Object.keys(finishes.catalogue).length + Object.keys(finishes.wall_catalogue).length],
    locales: ['i18n/locales/*.json',
      () => readdirSync(join(ROOT, 'i18n/locales')).filter((f) => f.endsWith('.json')).length],
  };
  const stats = [...home.matchAll(
    /<div class="stat" data-stat="([^"]*)" data-src="([^"]*)"><dt>[^<]*<\/dt><dd>([^<]*)<\/dd><\/div>/g)]
    .map((m) => ({ key: m[1], src: m[2], shown: m[3] }));
  const statWrong = [];
  for (const s of stats) {
    const rule = STAT_RULES[s.key];
    if (!rule) { statWrong.push(`${s.key}: no rule in this suite`); continue; }
    if (s.src !== rule[0]) statWrong.push(`${s.key}: data-src=${s.src}, want ${rule[0]}`);
    if (rule[1] === null) {
      // the one figure that is a headline, not a length: the bundle's own
      // README must state it in exactly the form the page prints
      if (!/^\d{1,3}(,\d{3})+$/.test(s.shown) || !readme.includes(s.shown)) {
        statWrong.push(`${s.key}: ${s.shown} is not stated in README.md`);
      }
    } else if (s.shown.replace(/,/g, '') !== String(rule[1]())) {
      statWrong.push(`${s.key}: page=${s.shown} registry=${rule[1]()}`);
    }
  }
  const statKeys = stats.map((s) => s.key);
  ok(`[shipped] index.html: every hero figure (${stats.length}) names in data-src the registry it was `
    + 'counted from, and equals this suite\'s own recount of that registry',
    stats.length > 0 && statWrong.length === 0, statWrong);
  ok('[shipped] index.html: and the hero figures are exactly the set this suite recounts - no stat '
    + 'slot missing, repeated, or added without a rule, and none outside the data-stat grid',
    JSON.stringify([...statKeys].sort()) === JSON.stringify(Object.keys(STAT_RULES).sort())
    && new Set(statKeys).size === statKeys.length
    && attrAll(home, 'data-stat').length === stats.length,
    [`page=[${statKeys}] slots=${attrAll(home, 'data-stat').length}`]);

  /* -- the calls to action ----------------------------------------------- */
  const cta = Object.fromEntries([...home.matchAll(/<a class="btn [^"]*" data-cta="([^"]*)" href="([^"]*)"/g)]
    .map((m) => [m[1], m[2]]));
  ok('[shipped] index.html: the hero carries exactly two calls to action - "primary" into the lessons '
    + 'and "secondary" into the walkable campus - as real links to built pages',
    attrAll(home, 'data-cta').length === 2
    && cta.primary === 'web/trade_craft_lessons.html' && cta.secondary === 'web/trade_craft_3d.html'
    && existsSync(join(ROOT, cta.primary)) && existsSync(join(ROOT, cta.secondary)),
    [`ctas=${JSON.stringify(cta)}`]);

  /* -- the audience paths ------------------------------------------------ */
  const WANT_PATHS = ['learners', 'instructors', 'schools', 'employers', 'partners'];
  const pathBlocks = [...bare.matchAll(/<article class="path" data-path="([^"]*)">([\s\S]*?)<\/article>/g)];
  const pathWrong = [];
  for (const [, k, inner] of pathBlocks) {
    const hrefs = [...inner.matchAll(/href="([^"]*)"/g)].map((m) => m[1]);
    if (!/<h3>[^<]+<\/h3>/.test(inner)) pathWrong.push(`${k}: no h3`);
    if (!hrefs.length) pathWrong.push(`${k}: no link`);
    for (const h of hrefs) if (!existsSync(join(ROOT, h.split(/[?#]/)[0]))) pathWrong.push(`${k}: ${h} is not a file`);
  }
  ok('[shipped] index.html: five audience paths - learners, instructors, schools, employers, partners - in that '
    + 'order, each with a heading and at least one link, every link a built page',
    JSON.stringify(pathBlocks.map((m) => m[1])) === JSON.stringify(WANT_PATHS) && pathWrong.length === 0,
    [`paths=[${pathBlocks.map((m) => m[1])}]`, ...pathWrong]);
  // the play and schools pages are reachable from the door, and play is never sold as a record
  const PLAY = ['web/trade_craft_quests.html', 'web/trade_craft_wilds.html'];
  const surfaced = new Set(pathBlocks.flatMap(([, , inner]) => [...inner.matchAll(/href="([^"]*)"/g)].map((m) => m[1])));
  const surfWrong = [...PLAY, 'web/trade_craft_schools.html'].filter((p) => !surfaced.has(p)).map((p) => `${p}: in no audience path`);
  for (const [, k, inner] of pathBlocks) {
    if (PLAY.some((p) => inner.includes(`href="${p}"`)) && !/<p>[^<]*nothing you do there enters a record[^<]*<\/p>/.test(inner))
      surfWrong.push(`${k}: links a play page without saying play enters no record`);
    if (/\b(certif|accredit)/i.test(inner.replace(/<[^>]*>/g, '').replace(/\bis not an? (certification|accreditation)\b/gi, ''))) surfWrong.push(`${k}: names a certification`);
  }
  const pathsH2 = (bare.match(/<section id="paths">[\s\S]*?<h2>([^<]*)<\/h2>/) || [])[1] || '';
  if (!pathsH2.startsWith(`${pathBlocks.length} ways in`)) surfWrong.push(`heading "${pathsH2}" does not count the ${pathBlocks.length} paths`);
  ok('[shipped] index.html: the audience paths surface quests, wilds and schools, and a path that links a play page '
    + 'says in its own prose that nothing done there enters a record',
    surfWrong.length === 0, surfWrong);

  /* -- the learner loop, from the one declaration ------------------------ */
  const LOOP_DECL = JSON.parse(execFileSync('python3', ['-c', [
    'import json, sys', `sys.path.insert(0, ${JSON.stringify(HERE)})`,
    'import sitenav as s', 'print(json.dumps(s.LOOP))'].join('\n')], { encoding: 'utf8' }));
  const en = readJSON('i18n/locales/en.json').strings;
  const steps = [...bare.matchAll(/<li class="step" data-loop-step="([^"]*)">([\s\S]*?)<\/li>/g)];
  const loopWrong = [];
  if (steps.length !== LOOP_DECL.length) loopWrong.push(`page ${steps.length} steps, sitenav.LOOP ${LOOP_DECL.length}`);
  LOOP_DECL.forEach(([page, key], i) => {
    const s = steps[i];
    if (!s) return;
    const [, k, inner] = s;
    if (k !== key.split('.').pop()) loopWrong.push(`step ${i + 1}: data-loop-step=${k}, want ${key.split('.').pop()}`);
    const href = (inner.match(/<a class="step-link" href="([^"]*)"/) || [])[1];
    if (href !== page) loopWrong.push(`step ${i + 1}: href=${href}, want ${page}`);
    const h3 = (inner.match(/<h3>([^<]*)<\/h3>/) || [])[1];
    if (h3 !== escLikeHome(en[key])) loopWrong.push(`step ${i + 1}: label "${h3}" is not the catalog's "${en[key]}"`);
    const img = inner.match(/<img src="([^"]*)" alt="([^"]*)"/);
    const ph = /<div class="shot-ph" data-placeholder><span>Placeholder<\/span>[^<]+<\/div>/.test(inner);
    if (!img && !ph) loopWrong.push(`step ${i + 1}: neither a screenshot nor a labelled placeholder`);
    if (img && !/^wiki\/img\/process-[a-z0-9-]+\.png$/.test(img[1])) loopWrong.push(`step ${i + 1}: ${img[1]} is not a shipped process shot`);
  });
  ok('[shipped] index.html: the learner loop is web/sitenav.py\'s LOOP, step for step - same order, same '
    + 'pages, each named by its own catalog label - and each step shows a shipped wiki/img/process-*.png '
    + 'or a placeholder labelled as one',
    loopWrong.length === 0, loopWrong);

  /* -- wave 8: the classroom band (CLASS) --------------------------------- */
  {
    const reg = JSON.parse(rf(join(ROOT, 'classroom/registry/classroom.json'), 'utf8'));
    const en8 = JSON.parse(rf(join(ROOT, 'i18n/locales/en.json'), 'utf8')).strings;
    const e8 = (x) => x.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
    const band = (home.match(/<section id="classroom" class="cl-band"[\s\S]*?<\/section>/) || [''])[0];
    const want = { modules: reg.modules.length + reg.cognitionx.modules.length, moments: reg.moments.length + reg.cognitionx.moments.length, places: reg.places.length };
    const got = Object.fromEntries([...band.matchAll(/data-cl-stat="([^"]+)"[^>]*><dt>[^<]*<\/dt><dd>([^<]*)<\/dd>/g)]
      .map((m) => [m[1], Number(m[2].replace(/,/g, ''))]));
    ok(`[shipped] index.html: exactly one classroom band, its figures recounted from classroom/registry/classroom.json (${JSON.stringify(want)})`,
      (home.match(/<section id="classroom"/g) || []).length === 1 && JSON.stringify(got) === JSON.stringify(want), [JSON.stringify(got)]);
    ok('[shipped] index.html: the classroom band links the classroom page and says play / not access control / no data leaves',
      band.includes('href="web/trade_craft_classroom.html"') && [['cl-play', 'class.h.play'], ['cl-plan', 'class.h.plan'], ['cl-data', 'class.h.data']].every(([h, k]) => band.includes('<li data-honest="' + h + '">' + e8(en8[k]) + '</li>')));
  }

  /* -- wave 7: the holodeck packs band (PACKS) ---------------------------- */
  {
    const reg = JSON.parse(rf(join(ROOT, 'holodeck/registry/packs.json'), 'utf8'));
    const en7 = JSON.parse(rf(join(ROOT, 'i18n/locales/en.json'), 'utf8')).strings;
    const e7 = (x) => x.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
    const band = (home.match(/<section id="packs" class="pk-band"[\s\S]*?<\/section>/) || [''])[0];
    const all = home.match(/<section id="packs"/g) || [];
    const want = { packs: reg.packs.length, shipping: reg.packs.filter((p) => p.status === 'SHIPPING').length,
      proposed: reg.packs.filter((p) => p.status === 'PROPOSED').length };
    const got = Object.fromEntries([...band.matchAll(/data-pk-stat="([^"]+)"[^>]*><dt>[^<]*<\/dt><dd>([^<]*)<\/dd>/g)]
      .map((m) => [m[1], Number(m[2].replace(/,/g, ''))]));
    ok(`[shipped] index.html: exactly one holodeck packs band, its figures recounted from holodeck/registry/packs.json (${JSON.stringify(want)})`,
      all.length === 1 && JSON.stringify(got) === JSON.stringify(want), [JSON.stringify(got)]);
    const kinds = Object.fromEntries([...band.matchAll(/data-pk-kind="([^"]+)"><b>([^<]+)<\/b>/g)].map((m) => [m[1], Number(m[2])]));
    const wantK = Object.fromEntries(reg.kinds.map((k) => [k, reg.packs.filter((p) => p.kind === k).length]));
    ok('[shipped] index.html: the packs band counts each kind (union / K-12 / path / world / system) from the registry',
      JSON.stringify(kinds) === JSON.stringify(wantK), [JSON.stringify(kinds)]);
    ok('[shipped] index.html: the packs band names the series exactly "SmartCiti.X Powered by AGI Corp" and links the packs catalogue page',
      reg.series === 'SmartCiti.X Powered by AGI Corp' && band.includes('<b>SmartCiti.X Powered by AGI Corp</b>')
        && band.includes('href="web/trade_craft_packs.html"') && existsSync(join(ROOT, 'web/trade_craft_packs.html')));
    const txt = band.replace(/<[^>]+>/g, ' ');
    ok('[shipped] index.html: the packs band says SHIPPING vs PROPOSED and no price, and shows no currency or purchase',
      band.includes(e7(en7['packs.honest.status'])) && band.includes(e7(en7['packs.honest.price']))
        && !/[$€£¥₹]\s?\d|\bbuy\b|\bpurchase\b|\bdownload\b/i.test(txt));
  }

  /* -- wave 6: the New Orleans parishes band ----------------------------- */
  {
    const J = (p) => JSON.parse(rf(join(ROOT, p), 'utf8'));
    const par = J('parishes/registry/parishes.json');
    const fleet = J('fleet/registry/fleet.json').fleet;
    const npcs = J('npcs/registry/npcs.json').npcs;
    const lay = J('layers/registry/layers.json');
    const pay = J('payments/registry/catalog.json');
    const units = J('schools/registry/schools.json').units;
    const band = (home.match(/<section id="parishes" class="pw-band"[\s\S]*?<\/section>/) || [''])[0];
    const stations = lay.parishes.reduce((a, p) => a + p.stations.length, 0);
    const want = { parishes: Object.keys(par.parishes).length, vehicles: fleet.length, guides: npcs.length, stations };
    const got = Object.fromEntries([...band.matchAll(/data-pw-stat="([^"]+)"[^>]*><dt>[^<]*<\/dt><dd>([^<]*)<\/dd>/g)]
      .map((m) => [m[1], Number(m[2].replace(/,/g, ''))]));
    ok(`[shipped] index.html: the parishes band's figures are recounted from the registries' lists (${JSON.stringify(want)}), never typed`,
      band !== '' && JSON.stringify(got) === JSON.stringify(want), [JSON.stringify(got)]);
    const prev = par.parishes['22071'].map.preview;
    ok('[shipped] index.html: the band shows the committed Orleans preview named by the parish registry, and a file in the bundle',
      band.includes(`src="${prev}"`) && existsSync(join(ROOT, prev)) && /parishes\/maps\/22071-512\.webp/.test(prev), [prev]);
    ok('[shipped] index.html: the band says outlines RECORDED, fabric AUTHORED, satellite view-time only and no real elevation, '
      + 'and the registry still backs each word',
      /data-honest="outline"><b>Outlines RECORDED<\/b>/.test(band) && /data-honest="fabric"><b>Street fabric AUTHORED<\/b>/.test(band)
        && /data-honest="satellite"><b>Satellite view-time only<\/b>/.test(band) && /data-honest="elevation">/.test(band)
        && par.provenance.outline.startsWith('RECORDED') && par.parishes['22071'].map.fabric.startsWith('AUTHORED')
        && par.satellite.fetched_at_build === false && par.satellite.stored === false);
    const card = (k) => (band.match(new RegExp(`<article class="path pw-card" data-pw="${k}">([\\s\\S]*?)</article>`)) || ['', ''])[1];
    ok('[shipped] index.html: the Plans card says payments are not live in the catalog\'s own words, shows no price, and links the plans page',
      pay.live === false && card('plans').includes(pay.status) && card('plans').includes('href="web/trade_craft_plans.html"')
        && !/[$€£]\s*\d/.test(card('plans')) && pay.plans.every((p) => p.price === null));
    const land = fleet.filter((v) => v.medium === 'land').length;
    ok('[shipped] index.html: the fleet showroom card counts land and water from the fleet registry and links the showroom',
      card('fleet').includes(`${land} vehicles and ${fleet.length - land} watercraft`) && card('fleet').includes('href="web/trade_craft_fleet.html"'));
    const k12st = lay.parishes.reduce((a, p) => a + p.stations.filter((s) => s.layer === 'k12-unit').length, 0);
    ok('[shipped] index.html: the K-12 path is named "Cognition.X K-12" as the user asked, its content is the schools/ pack '
      + `(${units.length} units, ${k12st} stations), and districts are PROPOSED partners`,
      lay.layers['k12-unit'].label === 'Cognition.X K-12' && /<h3>Cognition\.X K-12<\/h3>/.test(card('k12'))
        && card('k12').includes(`the schools/ pack (${units.length} units)`) && card('k12').includes(`${k12st} stations`)
        && /PROPOSED partner/.test(card('k12')) && card('k12').includes('href="web/trade_craft_schools.html"'));
  }

  {
    const land6 = rf(join(ROOT, 'web/trade_craft_landing.html'), 'utf8');
    const sec = (land6.match(/<section id="parishes">[\s\S]*?<\/section>/) || [''])[0];
    const pay6 = JSON.parse(rf(join(ROOT, 'payments/registry/catalog.json'), 'utf8'));
    const keys = [...sec.matchAll(/data-pw="([^"]+)"/g)].map((m) => m[1]).join(',');
    ok('[shipped] web/trade_craft_landing.html: a parishes section links the parish world, fleet showroom, Cognition.X K-12 path and plans, '
      + 'and the Plans card quotes the catalog: payments are not live',
      keys === 'parishes,fleet,k12,plans' && sec.includes('href="trade_craft_parishes.html"') && sec.includes('href="trade_craft_fleet.html"')
        && sec.includes('href="trade_craft_plans.html"') && /<h3>Cognition\.X K-12<\/h3>/.test(sec)
        && pay6.live === false && sec.includes(pay6.status), [keys]);
  }

  /* -- every picture: alt text, a file that ships, its real size ---------- */
  const imgs = [...bare.matchAll(/<img\b([^>]*)>/g)].map((m) => m[1]);
  const imgWrong = [];
  for (const a of imgs) {
    const src = (a.match(/\bsrc="([^"]*)"/) || [])[1];
    const alt = (a.match(/\balt="([^"]*)"/) || [])[1];
    const w = Number((a.match(/\bwidth="(\d+)"/) || [])[1]);
    const h = Number((a.match(/\bheight="(\d+)"/) || [])[1]);
    if (!alt || !alt.trim()) imgWrong.push(`${src}: no alt text`);
    if (!src || !existsSync(join(ROOT, src))) { imgWrong.push(`${src}: not a file under the bundle root`); continue; }
    const buf = rf(join(ROOT, src));
    // PNG: IHDR width/height at 16/20. WebP (RIFF....WEBP): VP8X 24-bit
    // canvas-1 at 24/27, VP8L 14-bit packed at 21, VP8 16-bit at 26/28.
    let fw = buf.readUInt32BE(16), fh = buf.readUInt32BE(20);
    if (buf.toString('ascii', 0, 4) === 'RIFF' && buf.toString('ascii', 8, 12) === 'WEBP') {
      const ch = buf.toString('ascii', 12, 16);
      if (ch === 'VP8X') { fw = buf.readUIntLE(24, 3) + 1; fh = buf.readUIntLE(27, 3) + 1; }
      else if (ch === 'VP8L') { const b = buf.readUInt32LE(21); fw = (b & 0x3fff) + 1; fh = ((b >> 14) & 0x3fff) + 1; }
      else if (ch === 'VP8 ') { fw = buf.readUInt16LE(26) & 0x3fff; fh = buf.readUInt16LE(28) & 0x3fff; }
      else { fw = NaN; fh = NaN; }
    }
    if (fw !== w || fh !== h) {
      imgWrong.push(`${src}: width/height ${w}x${h}, file is ${fw}x${fh}`);
    }
  }
  ok(`[shipped] index.html: every <img> (${imgs.length}) has alt text, a src that is a file in the bundle, `
    + 'and width/height equal to that file\'s own PNG or WebP header, so the page does not jump as it loads',
    imgs.length > 0 && imgWrong.length === 0, imgWrong);

  /* -- no dead link: every local href and src lands on a file or an id ---- */
  const ids = new Set(attrAll(bare, 'id'));
  const dead = [];
  for (const [, attr, v] of bare.matchAll(/(?<![\w-])(href|src)="([^"]*)"/g)) {
    if (/^(https?:|data:|mailto:)/.test(v)) continue;
    if (v.startsWith('#')) { if (!ids.has(v.slice(1))) dead.push(`${attr}=${v}: no such id`); continue; }
    const file = v.replace(/&amp;/g, '&').split(/[?#]/)[0];
    if (!existsSync(join(ROOT, file))) dead.push(`${attr}=${v}: no such file`);
  }
  ok('[shipped] index.html: no dead link - every local href and src resolves to a file under the bundle '
    + 'root, and every in-page #fragment to an id the page carries',
    dead.length === 0, dead.slice(0, 6));

  /* -- what a record proves, word for word ------------------------------- */
  const COMPLETION = 'completion/registry/completion.json';
  const comp = readJSON(COMPLETION).honesty;
  const recs = [...bare.matchAll(/<(li|p)(?: class="[^"]*")? data-from="completion\/registry\/completion\.json#honesty\.([a-z_]+)(?:\[(\d+)\])?">([^<]*)<\/\1>/g)];
  const recWrong = [];
  const seen = { proves: [], does_not_prove: [], accreditation: [] };
  for (const [, , fieldName, idx, text] of recs) {
    const v = idx === undefined ? comp[fieldName] : (comp[fieldName] || [])[Number(idx)];
    if (typeof v !== 'string') { recWrong.push(`${fieldName}[${idx}]: not a sentence in ${COMPLETION}`); continue; }
    if (text !== escLikeHome(v)) recWrong.push(`${fieldName}[${idx}]: shipped "${text.slice(0, 50)}..." != registry`);
    if (seen[fieldName]) seen[fieldName].push(idx === undefined ? 0 : Number(idx));
  }
  const whole = (k) => JSON.stringify(seen[k]) === JSON.stringify(comp[k].map((_, i) => i));
  ok('[shipped] index.html: what a record proves and does not prove is the verifier registry\'s own '
    + `sentences, verbatim and complete - ${comp.proves.length} proves, ${comp.does_not_prove.length} `
    + 'does-not-prove, and the accreditation line - each naming its field in data-from',
    recWrong.length === 0 && whole('proves') && whole('does_not_prove') && seen.accreditation.length === 1,
    [...recWrong, `proves=[${seen.proves}] not=[${seen.does_not_prove}] accred=${seen.accreditation.length}`]);
}

{
  /* The fail-closed rule, held against the whole generator - its f-string
     page template included. The older check strips triple-quoted strings,
     and the footer's `.get('honesty.modules', '')` sat inside one, unseen. */
  /* Docstrings go (they quote the very idioms they forbid); f-string
     templates stay, because a default inside one ships. Triple quotes are
     paired in order, and a pair whose opener is prefixed f is a template. */
  const src = readFileSync(HOME_GEN, 'utf8');
  const q = [...src.matchAll(/"""/g)].map((m) => m.index);
  let raw = '', at = 0;
  for (let i = 0; i + 1 < q.length; i += 2) {
    const isF = /[fF][rR]?$|[rR][fF]$/.test(src.slice(Math.max(0, q[i] - 2), q[i]));
    raw += src.slice(at, q[i]) + (isF ? src.slice(q[i], q[i + 1] + 3) : ' ');
    at = q[i + 1] + 3;
  }
  raw = (raw + src.slice(at)).replace(/^\s*#.*$/gm, ' ');
  const hits = raw.match(/\.get\([^)]*,[^)]*\)|\?\?/g) || [];
  ok('[generator] build_home.py substitutes no default anywhere, page template included: no `.get(k, '
    + 'default)` and no `??`, inside or outside a triple-quoted string',
    hits.length === 0, hits.slice(0, 4));
}

{
  /* The programme page is a front door too. Without a viewport meta a phone
     lays it out at 980 px and shrinks it, which QA measured as a 1032 px
     scroll width at 390. */
  const landing = readFileSync(join(HERE, 'trade_craft_landing.html'), 'utf8');
  ok('[shipped] index.html and trade_craft_landing.html each declare a device-width viewport, so a phone '
    + 'lays them out at its own width rather than a desktop one scaled down',
    [home, landing].every((h) => /<meta name="viewport" content="width=device-width, initial-scale=1">/.test(h)),
    [`index=${/name="viewport"/.test(home)} landing=${/name="viewport"/.test(landing)}`]);
}

{
  /* The hero's background footage (web/herovideo.py). Decoration that must
     never cost a reader anything: muted, hidden from assistive tech, sources
     attached only after first paint (data-src, no src), WebM first for the
     browsers that decode it and MP4 second, each within budget, a poster
     that exists, a visible Pause/Play control, and one line saying where
     the footage came from. */
  const hdr = home.slice(home.indexOf('<header class="top"'), home.indexOf('</header>'));
  // wave 3: the hero holds exactly one <video>; every other <video> on the
  // page is section footage, held to the same rules by its own check below
  const vids = [...hdr.matchAll(/<video\b([^>]*)>([\s\S]*?)<\/video>/g)];
  const v = vids.length === 1 ? vids[0] : null;
  const attrs = v ? v[1] : '';
  const need = ['autoplay', 'muted', 'loop', 'playsinline', 'preload="metadata"', 'aria-hidden="true"'];
  ok('[shipped] index.html: exactly one <video> inside the hero, muted, looping, inline, preload=metadata, '
    + 'aria-hidden, with a poster',
    v !== null && hdr.includes('<video') && need.every((a) => new RegExp(`(^|\\s)${a}(\\s|$)`).test(attrs))
      && /\sposter="[^"]+"/.test(attrs),
    [attrs.slice(0, 200)]);
  const srcs = v ? [...v[2].matchAll(/<source\b([^>]*)>/g)].map((m) => m[1]) : [];
  const ds = srcs.map((a) => (a.match(/data-src="([^"]+)"/) || [])[1]);
  const types = srcs.map((a) => (a.match(/type="([^"]+)"/) || [])[1]);
  const MAXB = 3 * 1024 * 1024;
  const sizes = ds.map((f) => { try { return statSync(join(ROOT, f)).size; } catch { return -1; } });
  ok('[shipped] index.html: the footage is WebM first and MP4 second, each a file in the bundle of at most '
    + '3 MB, and neither is attached until script runs (data-src, no src)',
    srcs.length === 2 && types[0] === 'video/webm' && types[1] === 'video/mp4'
      && /\.webm$/.test(ds[0]) && /\.mp4$/.test(ds[1])
      && sizes.every((b) => b > 0 && b <= MAXB) && srcs.every((a) => !/(^|\s)src="/.test(a)),
    [JSON.stringify({ types, ds, sizes })]);
  const poster = (attrs.match(/\sposter="([^"]+)"/) || [])[1];
  ok('[shipped] index.html: the poster is a JPEG in the bundle',
    !!poster && /\.jpe?g$/.test(poster) && existsSync(join(ROOT, poster)), [poster]);
  // the footage is MEDIA's registered hero b-roll, byte for byte, never a placeholder or a hero=false clip
  {
    const { createHash } = await import('node:crypto');
    const hvSrc = readFileSync(join(ROOT, 'web/herovideo.py'), 'utf8');
    const clipId = (hvSrc.match(/^HERO_CLIP_ID = '([^']+)'/m) || [])[1];
    const reg = JSON.parse(readFileSync(join(ROOT, 'media/registry/media.json'), 'utf8'));
    const clip = reg.clips.find((c) => c.id === clipId);
    const shipped = [...attrs.matchAll(/\sposter="([^"]+)"/g)].map((m) => m[1])
      .concat([...hdr.matchAll(/<source data-src="([^"]+)"/g)].map((m) => m[1]));
    const why = [];
    if (!clip) why.push(`no clip ${clipId} in media/registry/media.json`);
    else {
      if (clip.hero !== true) why.push(`${clipId} is not registered hero=true`);
      const want = [clip.files.poster.path, clip.files.webm.path, clip.files.mp4.path];
      if (JSON.stringify(shipped) !== JSON.stringify(want)) why.push(`shipped ${shipped} != registry ${want}`);
      for (const k of ['poster', 'webm', 'mp4']) {
        const f = clip.files[k];
        if (!existsSync(join(ROOT, f.path))) { why.push(`${f.path} missing`); continue; }
        if (createHash('sha256').update(readFileSync(join(ROOT, f.path))).digest('hex') !== f.sha256) why.push(`${f.path}: sha256 differs from the registry`);
      }
    }
    ok('[shipped] index.html: the hero footage is the b-roll herovideo.HERO_CLIP_ID names in media/registry/media.json - '
      + 'registered hero=true, poster/WebM/MP4 exactly its files, each still matching its registered sha256', why.length === 0, why);
  }
  const js = (home.match(/<script id="hv-js">([\s\S]*?)<\/script>/) || [])[1] || '';
  ok('[shipped] index.html: the footage script declines to autoplay under prefers-reduced-motion, under '
    + 'Save-Data and on a small screen, and starts only after the load event',
    /matchMedia\('\(prefers-reduced-motion: reduce\)'\)/.test(js) && /navigator\.connection\.saveData/.test(js)
      && /matchMedia\('\(max-width: \d+px\)'\)/.test(js) && /addEventListener\('load'/.test(js)
      && /removeAttribute\('autoplay'\)/.test(js));
  const btn = hdr.match(/<button\b[^>]*data-hero-video-toggle[^>]*>([\s\S]*?)<\/button>/);
  ok('[shipped] index.html: a visible Pause/Play button for the footage (WCAG 2.2.2), with aria-pressed, '
    + 'and a caption saying the footage is recorded from this build',
    !!btn && /aria-pressed="(true|false)"/.test(btn[0]) && /Pause background video/.test(btn[1])
      && /<p class="hv-cap">[^<]*(recorded|filmed frame by frame) from this build/.test(hdr));
  ok('[shipped] index.html: the footage sits absolutely behind the hero (no layout shift) under a scrim',
    /\.hv\{position:absolute;inset:0;z-index:-1/.test(home) && /\.hv-scrim\{position:absolute;inset:0;background:rgba\(/.test(home));
  ok('[shipped] index.html: a <main id="main"> holds the page\'s one <h1>, the target for skip links',
    /<main id="main" tabindex="-1">[\s\S]*<h1>[\s\S]*<\/main>/.test(home) && (home.match(/<main\b/g) || []).length === 1);
}

{
  /* Wave 3: the enterprise layer. Section footage (showcase rows and bands
     over MEDIA's registered clips), the count-up over the hero figures, the
     globe and simulated-task teasers, and MEDIA's pagehero band on the ten
     document pages HOMEUX adopted it on. Every clip is held to the hero's
     rules; every figure stays the registry's own text in the DOM. */
  const { createHash } = await import('node:crypto');
  const { execFileSync } = await import('node:child_process');
  const esc3 = (t) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
  const reg = JSON.parse(readFileSync(join(ROOT, 'media/registry/media.json'), 'utf8'));
  const CLIP = Object.fromEntries(reg.clips.map((c) => [c.id, c]));
  const landingW3 = readFileSync(join(HERE, 'trade_craft_landing.html'), 'utf8');
  const sha = (p) => createHash('sha256').update(readFileSync(join(ROOT, p))).digest('hex');
  const clipWrong = [];
  let clipCount = 0;
  for (const [name, page, base] of [['index.html', home, ''], ['trade_craft_landing.html', landingW3, 'web/']]) {
    const heroEnd = page.indexOf('</header>');
    const blocks = [...page.matchAll(/<(figure|div) class="(sv-media|vband[^"]*)"[^>]*data-clip="([^"]+)">([\s\S]*?)(?=<(?:figure|div) class="(?:sv-media|vband)|<\/main>)/g)];
    const allVids = [...page.matchAll(/<video\b([^>]*)>([\s\S]*?)<\/video>/g)];
    const outside = allVids.filter((m) => m.index > heroEnd);
    if (outside.length !== blocks.length) clipWrong.push(`${name}: ${outside.length} videos past the hero, ${blocks.length} [data-clip] blocks`);
    for (const [, , kind, id, inner] of blocks) {
      clipCount++;
      const c = CLIP[id];
      if (!c) { clipWrong.push(`${name}: ${id} is not a registered clip`); continue; }
      const v = inner.match(/<video\b([^>]*)>([\s\S]*?)<\/video>/);
      if (!v) { clipWrong.push(`${name} ${id}: no <video>`); continue; }
      const a = v[1];
      for (const need of ['muted', 'loop', 'playsinline', 'preload="none"', 'aria-hidden="true"'])
        if (!new RegExp(`(^|\\s)${need}(\\s|$)`).test(a)) clipWrong.push(`${name} ${id}: <video> lacks ${need}`);
      if (/(^|\s)autoplay(\s|$|=)/.test(a)) clipWrong.push(`${name} ${id}: section footage must never carry autoplay`);
      if (!/class="(sv-video|vb-video)"/.test(a)) clipWrong.push(`${name} ${id}: not a section-footage class`);
      const poster = (a.match(/\sposter="([^"]+)"/) || [])[1];
      const srcs = [...v[2].matchAll(/<source\b([^>]*)>/g)].map((m) => m[1]);
      const ds = srcs.map((s) => (s.match(/data-src="([^"]+)"/) || [])[1]);
      const types = srcs.map((s) => (s.match(/type="([^"]+)"/) || [])[1]);
      if (srcs.some((s) => /(^|\s)src="/.test(s))) clipWrong.push(`${name} ${id}: a source is attached before script runs`);
      if (JSON.stringify(types) !== '["video/webm","video/mp4"]') clipWrong.push(`${name} ${id}: sources ${types}`);
      const shipped = [poster, ...ds].map((p) => (p ? join(base, p).replace(/\\/g, '/') : p));
      const want = [c.files.poster.path, c.files.webm.path, c.files.mp4.path];
      if (JSON.stringify(shipped) !== JSON.stringify(want)) clipWrong.push(`${name} ${id}: shipped ${shipped} != registry ${want}`);
      for (const k of ['poster', 'webm', 'mp4']) if (!existsSync(join(ROOT, c.files[k].path)) || sha(c.files[k].path) !== c.files[k].sha256) clipWrong.push(`${name} ${id}: ${k} sha256 differs from the registry`);
      const btn = inner.match(/<button\b[^>]*data-clip-toggle[^>]*>/);
      if (!btn || !/aria-pressed="(true|false)"/.test(btn[0]) || !/data-label-pause="[^"]+"/.test(btn[0])) clipWrong.push(`${name} ${id}: no Pause/Play button of its own`);
      if (!inner.includes(`${c.title}. ${c.provenance}.`)) clipWrong.push(`${name} ${id}: no caption naming its registry title and provenance`);
    }
  }
  ok(`[shipped] index.html and trade_craft_landing.html: every <video> past the hero (${clipCount}) is section footage - a registered `
    + 'clip byte for byte (sha256), muted, looping, inline, preload=none, aria-hidden, never autoplay, sources attached only by script, '
    + 'with its own Pause/Play button and a caption naming the clip and its provenance', clipCount >= 3 && clipWrong.length === 0, clipWrong);

  const sv = (home.match(/<script id="sv-js">([\s\S]*?)<\/script>/) || [])[1] || '';
  ok('[shipped] index.html: the section-footage script declines under prefers-reduced-motion, Save-Data and a small screen, '
    + 'starts a clip only while it is in view, and honours a stored pause',
    /matchMedia\('\(prefers-reduced-motion: reduce\)'\)/.test(sv) && /navigator\.connection\.saveData/.test(sv)
      && /matchMedia\('\(max-width: \d+px\)'\)/.test(sv) && /IntersectionObserver/.test(sv)
      && /if \(reduce \|\| saveData \|\| small/.test(sv) && /pref\(\) !== 'paused'/.test(sv)
      && landingW3.includes('<script id="sv-js">'));

  const cu = (home.match(/<script id="countup-js">([\s\S]*?)<\/script>/) || [])[1] || '';
  const cuBody = cu.slice(cu.indexOf('(function'));
  ok('[shipped] index.html: the count-up animates only the registry figures already in the hero (<dl class="stats" data-countup>), '
    + 'returns before touching the DOM under prefers-reduced-motion, and writes the built text back at the end',
    /<dl class="stats" data-countup>/.test(home) && (home.replace(/<script\b[\s\S]*?<\/script>/g, '').match(/data-countup/g) || []).length === 1
      && /^\(function \(\) \{\s*if \(window\.matchMedia\('\(prefers-reduced-motion: reduce\)'\)\.matches\) return;/.test(cuBody)
      && /var fin = el\.textContent;/.test(cu) && /el\.textContent = fin;/.test(cu)
      && /querySelectorAll\('\[data-countup\] dd'\)/.test(cu));

  const teaser = (k) => (home.match(new RegExp(`<div class="sv-row" data-teaser="${k}">([\\s\\S]*?)</div></div>`)) || [])[1] || '';
  const tWrong = [];
  const g = teaser('globe'); const t = teaser('tasks');
  if (!g.includes('href="web/trade_craft_geomap.html"')) tWrong.push('globe teaser does not link the geomap');
  if (!/SCHEMATIC/.test(g)) tWrong.push('globe teaser does not say what is SCHEMATIC');
  for (const h of ['web/trade_craft_map.html', 'web/trade_craft_interactive.html']) if (!t.includes(`href="${h}"`)) tWrong.push(`tasks teaser does not link ${h}`);
  if (!/not a certification/.test(t)) tWrong.push('tasks teaser does not say a simulated run is not a certification');
  for (const h of [...g.matchAll(/href="([^"]+)"/g), ...t.matchAll(/href="([^"]+)"/g)].map((m) => m[1])) if (!existsSync(join(ROOT, h))) tWrong.push(`${h} is not built`);
  ok('[shipped] index.html: a globe teaser linking the geomap (saying what is SCHEMATIC) and a simulated-tasks teaser linking both maps '
    + '(saying a run is practice, not a certification), every link a built page', tWrong.length === 0, tWrong);

  // MEDIA's pagehero band on the ten document pages (herovideo.DOC_HERO_PAGES)
  const DOC = JSON.parse(execFileSync('python3', ['-c', [
    'import json, sys', `sys.path.insert(0, ${JSON.stringify(HERE)})`, 'import sitenav', 'import herovideo as h',
    'print(json.dumps({k: [v[0], v[1], h.STYLE_MEMORY[k]] for k, v in h.DOC_HERO_PAGES.items()}))'].join('\n')], { encoding: 'utf8' }));
  const enS = readJSON('i18n/locales/en.json').strings;
  const ANCHOR = '<span id="tc-main" class="sitenav-skip-target" tabindex="-1"></span>';
  const dWrong = [];
  const clipsUsed = new Set();
  for (const [k, [path, clip, mem]] of Object.entries(DOC)) {
    const h = readFileSync(join(ROOT, path), 'utf8');
    // the style switcher's memory, per page contract (herovideo.STYLE_MEMORY)
    const headPart = h.slice(0, h.indexOf('</head>'));
    const headJs = headPart.indexOf('<script id="style-head-js">'); const firstStyle = headPart.indexOf('<style');
    const tailJs = h.includes('<script id="style-js">');
    if (mem === 'full' && !(headJs > 0 && headJs < firstStyle && tailJs)) dWrong.push(`${k}: style memory 'full' but head/tail scripts are not in place`);
    if (mem === 'tail' && (headJs >= 0 || !tailJs)) dWrong.push(`${k}: style memory 'tail' must carry only the tail script`);
    if (mem === 'none' && (headJs >= 0 || tailJs)) dWrong.push(`${k}: style memory 'none' but a style script ships`);
    if (!['full', 'tail', 'none'].includes(mem)) dWrong.push(`${k}: unknown style memory ${mem}`);
    const bands = h.match(/<section class="ph" data-ph data-ph-clip="([^"]+)"[^>]*data-ph-contrast-min="([\d.]+)"/g) || [];
    if (bands.length !== 1) { dWrong.push(`${k}: ${bands.length} pagehero bands`); continue; }
    const [, id, min] = bands[0].match(/data-ph-clip="([^"]+)"[^>]*data-ph-contrast-min="([\d.]+)"/);
    clipsUsed.add(id);
    if (id !== clip || !CLIP[id]) dWrong.push(`${k}: band clip ${id}, declared ${clip}`);
    if (!(Number(min) >= 4.5)) dWrong.push(`${k}: measured contrast min ${min} < 4.5`);
    if (!h.includes(ANCHOR + '<section class="ph" data-ph')) dWrong.push(`${k}: the band is not right after the nav's skip target`);
    if ((h.match(/<h1[\s>]/g) || []).length !== 1) dWrong.push(`${k}: not exactly one <h1>`);
    for (const part of ['kicker', 'lede']) if (!h.includes(esc3(enS[`hero.${k}.${part}`]))) dWrong.push(`${k}: hero.${k}.${part} not on the page`);
    if (!/^<!doctype html>\s*<html lang="en" data-theme="dark">/i.test(h)) dWrong.push(`${k}: <html> does not declare the dark palette`);
    if (!/<body class="tc-theme[" ]/.test(h)) dWrong.push(`${k}: <body> lacks tc-theme`);
    const scripts = [...h.matchAll(/<script\b[^>]*>/g)].map((m) => m[0]);
    const iPh = scripts.findIndex((s) => /id="ph-js"/.test(s)); const iLd = scripts.findIndex((s) => /ld\+json/.test(s));
    if (iPh < 0 || (iLd >= 0 && iPh > iLd)) dWrong.push(`${k}: the band script is missing or after the JSON-LD`);
    if (/<section class="ph"[\s\S]*?<\/section>/.exec(h)[0].match(/https?:\/\//)) dWrong.push(`${k}: the band names an http(s) URL`);
  }
  ok(`[shipped] the ${Object.keys(DOC).length} document pages each carry one pagehero band right after the nav, on a registered clip `
    + 'whose measured contrast is at least 4.5, with the catalog\'s hero.<page>.* words, still one <h1>, the dark palette, '
    + 'the theme body class, and the band script ahead of the JSON-LD', Object.keys(DOC).length === 10 && dWrong.length === 0, dWrong);
  ok(`[shipped] the document pages share out the registered clips rather than all taking one (${clipsUsed.size} in use)`,
    clipsUsed.size >= 3, [...clipsUsed]);
}

{
  /* The site search (web/sitesearch.py): its index is built from the same
     registries this suite reads, so it is recounted here - every nav page,
     every lesson, every hall, every seat - and every URL in it must land on
     a page in the bundle using a link scheme a page already honours. */
  const m = home.match(/<script type="application\/json" id="ss-index" data-prefix="([^"]*)">([\s\S]*?)<\/script>/);
  let idx = null;
  try { idx = m ? JSON.parse(m[2]) : null; } catch { idx = null; }
  const by = (t) => (idx || []).filter((e) => e.t === t);
  const hallsReg = JSON.parse(readFileSync(join(ROOT, 'pack/registry/halls.json'), 'utf8')).halls;
  const simsReg = JSON.parse(readFileSync(join(ROOT, 'sims/registry/sims.json'), 'utf8')).sims;
  const navSrc = readFileSync(join(ROOT, 'web/sitenav.py'), 'utf8');
  const navPages = ['index.html', ...[...navSrc.slice(navSrc.indexOf('GROUPS = ['), navSrc.indexOf('# Every page: path'))
    .matchAll(/\('(web\/[^']+\.html)', 'nav\.page\./g)].map((x) => x[1])];
  ok(`[shipped] index.html: the search index parses and holds every nav page (${navPages.length}), `
    + `every lesson (${Object.keys(LESSONS).length}), every hall (${hallsReg.length}) and every seat `
    + `(${Object.keys(simsReg).length}), recounted from the registries`,
    idx !== null && m[1] === ''
      && JSON.stringify(by('page').map((e) => e.u)) === JSON.stringify(navPages)
      && by('lesson').length === Object.keys(LESSONS).length
      && by('hall').length === hallsReg.length && by('seat').length === Object.keys(simsReg).length,
    idx ? [`pages ${by('page').length} lessons ${by('lesson').length} halls ${by('hall').length} seats ${by('seat').length}`] : ['no index']);
  const badU = (idx || []).filter((e) => !existsSync(join(ROOT, e.u.split('?')[0]))
    || !(/^[a-z0-9_/.-]+\.html$/.test(e.u) || /^web\/trade_craft_lessons\.html\?hall=[a-z0-9-]+$/.test(e.u)
      || /^web\/trade_craft_3d\.html\?(sim|hall)=[a-z0-9-]+$/.test(e.u)));
  ok('[shipped] index.html: every search result links to a file in the bundle, into the lessons page only '
    + 'by ?hall= and into the 3D page only by ?sim= or ?hall=', idx !== null && badU.length === 0,
    badU.slice(0, 4).map((e) => e.u));
  const lessonsWrong = Object.values(LESSONS).filter((l) => !by('lesson').some((e) => e.n === l.title
    && e.u === `web/trade_craft_lessons.html?hall=${l.hall}`));
  ok('[shipped] index.html: each lesson in the search opens its own hall\'s course', lessonsWrong.length === 0,
    lessonsWrong.slice(0, 3).map((l) => l.id));
  const qPath = join(ROOT, 'quests/registry/quests.json');
  const hidden = existsSync(qPath) ? JSON.parse(readFileSync(qPath, 'utf8')).quests
    .filter((q) => q.kind === 'egg' || q.kind === 'treasure').map((q) => q.title) : [];
  /* Wave 6: the parish world in the search - every parish, every landmark
     and every guide role, recounted from the registries, each resolving to
     the parish world page (a file in the bundle, and a nav page). */
  {
    const parReg = JSON.parse(readFileSync(join(ROOT, 'parishes/registry/parishes.json'), 'utf8')).parishes;
    const npcReg = JSON.parse(readFileSync(join(ROOT, 'npcs/registry/npcs.json'), 'utf8')).npcs;
    const PP = 'web/trade_craft_parishes.html';
    const miss = [];
    for (const p of Object.values(parReg)) {
      if (!by('parish').some((e) => e.n === p.full_name && e.u === PP)) miss.push(`parish ${p.full_name}`);
      for (const lm of p.landmarks) {
        if (!by('landmark').some((e) => e.n === lm.name && e.u === PP && e.d.startsWith(p.full_name))) miss.push(`landmark ${lm.name}`);
      }
    }
    const roles = [...new Set(npcReg.map((g) => g.role))];
    for (const r of roles) if (!by('guide').some((e) => e.d.startsWith(`${r} · `) && e.u === PP)) miss.push(`guide role ${r}`);
    const nLm = Object.values(parReg).reduce((a, p) => a + p.landmarks.length, 0);
    ok(`[shipped] index.html: the search holds every parish (${Object.keys(parReg).length}), every landmark (${nLm}) and `
      + `every guide role (${roles.length}) from the registries, each resolving to the parish world page`,
      idx !== null && miss.length === 0 && by('parish').length === Object.keys(parReg).length
        && by('landmark').length === nLm && by('guide').length === roles.length
        && existsSync(join(ROOT, PP)), miss.slice(0, 5));
    const w5 = ['web/trade_craft_parishes.html', 'web/trade_craft_fleet.html', 'web/trade_craft_plans.html'];
    const w5miss = w5.filter((u) => !by('page').some((e) => e.u === u) || !existsSync(join(ROOT, u)));
    ok('[shipped] index.html: the search indexes the parishes, fleet and plans pages, and each resolves to a file',
      idx !== null && w5miss.length === 0, w5miss);
  }
  ok('[shipped] index.html: the search lists no treasure or easter egg - those are for finding',
    idx !== null && by('quest').every((e) => !hidden.includes(e.n)), by('quest').filter((e) => hidden.includes(e.n)).map((e) => e.n));
  const openBtn = home.match(/<button\b[^>]*data-search-open[^>]*>/);
  // every other page reaches the palette through sitesearch.search_trigger(): a plain link to index.html#search
  const TRIG = JSON.parse((await import("node:child_process")).execFileSync('python3', ['-c', [
    'import json, sys', `sys.path.insert(0, ${JSON.stringify(HERE)})`,
    'import sitesearch as s, sitenav as n',
    'print(json.dumps({p: s.search_trigger(p) for p in n.PAGES}))'].join('\n')], { encoding: 'utf8' }));
  const trigWrong = [];
  for (const [p, a] of Object.entries(TRIG)) {
    const href = (a.match(/^<a class="ss-go" href="([^"]+)" data-search-go[^>]*>/) || [])[1];
    if (/<script/i.test(a)) trigWrong.push(`${p}: trigger carries a script`);
    if (!href || !href.endsWith('#search')) { trigWrong.push(`${p}: href=${href}`); continue; }
    const file = href.split('#')[0];
    const target = file ? join(ROOT, dirname(p), file) : join(ROOT, p);
    if (resolve(target) !== resolve(join(ROOT, 'index.html'))) trigWrong.push(`${p}: ${href} does not land on index.html`);
  }
  const ssjs = (home.match(/<script id="ss-js">([\s\S]*?)<\/script>/) || [])[1] || '';
  if (!/location\.hash !== '#search'/.test(ssjs) || !/addEventListener\('hashchange', fromHash\)/.test(ssjs)
      || !/\bfromHash\(\);/.test(ssjs)) trigWrong.push('index.html: palette script does not open on #search (load + hashchange)');
  if (!/history\.replaceState/.test(ssjs)) trigWrong.push('index.html: #search is not cleared, a reload would reopen the palette');
  ok('[shipped] every nav page\'s search_trigger() is a script-free link that lands on index.html#search, and the '
    + 'front door opens its palette on #search (on load and on hashchange) then clears the hash',
    trigWrong.length === 0, trigWrong);
  ok('[shipped] index.html: a visible search button (Ctrl/Cmd+K advertised) opens a labelled dialog whose '
    + 'input is a combobox driving a listbox, with a polite live status',
    !!openBtn && /aria-keyshortcuts="Control\+K Meta\+K"/.test(openBtn[0]) && /aria-controls="ss-dlg"/.test(openBtn[0])
      && /<dialog id="ss-dlg"[^>]*aria-labelledby="ss-title"/.test(home)
      && /<label class="ss-lbl" for="ss-q">/.test(home)
      && /<input id="ss-q"[^>]*role="combobox"[^>]*aria-controls="ss-list"/.test(home)
      && /<ul id="ss-list"[^>]*role="listbox"/.test(home) && /role="status" aria-live="polite"/.test(home));
}

{
  /* The programme page's hero carries the same footage (web/herovideo.py),
     its button words and caption from the locale catalog. */
  const landing = readFileSync(join(HERE, 'trade_craft_landing.html'), 'utf8');
  const en = JSON.parse(readFileSync(join(ROOT, 'i18n/locales/en.json'), 'utf8')).strings;
  const v = landing.match(/<video\b([^>]*)>([\s\S]*?)<\/video>/);
  const ds = v ? [...v[2].matchAll(/<source data-src="([^"]+)" type="([^"]+)">/g)].map((m) => [m[1], m[2]]) : [];
  const poster = v ? (v[1].match(/\sposter="([^"]+)"/) || [])[1] : null;
  const esc = (t) => t.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/'/g, '&#x27;');
  ok('[shipped] trade_craft_landing.html: the hero carries the footage (WebM then MP4, files beside the page, a '
    + 'poster), a Pause/Play button whose words are the catalog\'s landing.video.* strings, and the caption',
    !!v && /muted/.test(v[1]) && /aria-hidden="true"/.test(v[1]) && ds.length === 2 && ds[0][1] === 'video/webm'
      && ds[1][1] === 'video/mp4' && ds.every(([f]) => existsSync(join(HERE, f))) && !!poster && existsSync(join(HERE, poster))
      && landing.includes(`data-label-pause="${esc(en['landing.video.pause'])}" data-label-play="${esc(en['landing.video.play'])}"`)
      && landing.includes(`<p class="hv-cap">${esc(en['landing.video.caption'])}</p>`)
      && /<script id="hv-js">/.test(landing),
    [JSON.stringify({ ds, poster })]);
}

/* ============================================================ [browser] === */
if (WANT_BROWSER) {
  let chromium;
  try { ({ chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs')); }
  catch { console.log('FAIL  [browser] playwright is not importable; run without --browser'); bad++; }
  if (chromium) {
    const browser = await chromium.launch({
      executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
    const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
    const errs = [];
    page.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
    page.on('console', (m) => { if (m.type() === 'error') errs.push('console: ' + m.text()); });
    const LESSON_URL = `${ORIGIN}/web/trade_craft_lessons.html`;

    /* the course route, from the front door's own link */
    await page.goto(`${ORIGIN}/index.html`, { waitUntil: 'load' });
    const startHref = await page.getAttribute('#start-here', 'href');
    await page.goto(new URL(startHref, `${ORIGIN}/index.html`).href, { waitUntil: 'load' });
    const shown = await page.$$eval('section.course:not([hidden])', (es) => es.map((e) => e.dataset.hall));
    ok('[browser] the front door\'s start link lands on exactly one course - the course of the hall '
      + `the start lesson stands in (${LESSONS[START].hall}) - and hides the other courses rather `
      + 'than removing them',
      JSON.stringify(shown) === JSON.stringify([LESSONS[START].hall])
      && (await page.$$('section.course')).length === COURSE_COUNT,
      [`href=${startHref} shown=[${shown}]`]);

    /* every trade link the front door offers opens the course it names */
    {
      await page.goto(`${ORIGIN}/index.html`, { waitUntil: 'load' });
      const slugs = await page.$$eval('a.trade', (as) => as.map((a) => a.dataset.hall));
      const wrong = [];
      for (const slug of slugs) {
        await page.goto(`${LESSON_URL}?hall=${slug}`, { waitUntil: 'load' });
        const vis = await page.$$eval('section.course:not([hidden])', (es) => es.map((e) => e.dataset.hall));
        const steps = await page.$$eval('section.course:not([hidden]) li.step', (es) => es.length);
        const want = COURSES.find((c) => c.hall === slug);
        if (JSON.stringify(vis) !== JSON.stringify([slug]) || steps !== want.steps) {
          wrong.push(`${slug}: visible=[${vis}] steps=${steps} want ${want.steps}`);
        }
      }
      ok(`[browser] every one of the ${slugs.length} trades the front door offers opens its own `
        + 'course and only its own, with the step count the registry holds for it'
        + (wrong.length ? ` - ${wrong.slice(0, 3).join('; ')}` : ''),
        slugs.length === COURSE_COUNT && wrong.length === 0, wrong);
    }

    /* a hall with no course is said, not guessed at */
    {
      const noCourse = hallsReg.halls.map((h) => h.slug).find((s) => !courseOf.has(s));
      await page.goto(`${LESSON_URL}?hall=${noCourse}`, { waitUntil: 'load' });
      const vis = await page.$$eval('section.course:not([hidden])', (es) => es.length);
      const note = await page.$eval('#course-note', (e) => e.textContent);
      ok(`[browser] a hall with no course (${noCourse}) is not silently swapped for a near miss: `
        + `the page says so and shows all ${COURSE_COUNT} courses rather than none`,
        vis === COURSE_COUNT && note.includes(noCourse),
        [`visible=${vis} note=${JSON.stringify(note)}`]);
    }

    /* a step's seat link really opens that seat */
    {
      const c = COURSES.find((x) => x.seatSteps > 0);
      await page.goto(`${LESSON_URL}?hall=${c.hall}`, { waitUntil: 'load' });
      const href = await page.getAttribute('section.course:not([hidden]) a.seatlink', 'href');
      const target = new URL(href, `${LESSON_URL}?hall=${c.hall}`).href;
      const seat = new URL(target).searchParams.get('sim');
      const resp = await page.goto(target, { waitUntil: 'load' });
      let opened = null;
      try {
        await page.waitForFunction(
          (want) => window.__tc3d && window.__tc3d().sim === want, seat, { timeout: 30000 });
        opened = await page.evaluate(() => window.__tc3d().sim);
      } catch { opened = await page.evaluate(() => (window.__tc3d ? window.__tc3d().sim : 'no hook')); }
      ok(`[browser] a course step that names a seat opens it: the ${c.hall} course's first seat `
        + `link stands up seat ${seat} in the walkable world`,
        resp.ok() && opened === seat, [target, `status=${resp.status()} seat open=${opened}`]);
    }

    /* marking a step records nothing, anywhere */
    {
      await page.goto(`${LESSON_URL}?hall=${COURSES[0].hall}`, { waitUntil: 'load' });
      const before = await page.evaluate(() => [localStorage.length, sessionStorage.length]);
      await page.click('section.course:not([hidden]) input.mark');
      const after = await page.evaluate(() => [localStorage.length, sessionStorage.length]);
      const done = await page.$eval('section.course:not([hidden]) .done', (e) => e.textContent);
      ok('[browser] marking a course step is a tally in the open tab and nothing else: it writes no '
        + 'key to localStorage or sessionStorage, and the page contract says a lesson is nobody\'s '
        + 'episode',
        JSON.stringify(before) === JSON.stringify(after) && /1 of \d+ marked/.test(done),
        [`storage before=${before} after=${after} tally=${JSON.stringify(done)}`]);
    }

    /* the front door itself, as a reader meets it: on a phone and a desk, in
       both colour schemes - no sideways scroll, body text at WCAG AA against
       the surface actually behind it (alpha composited, measured with
       getComputedStyle rather than guessed), and both calls to action
       reachable from the keyboard alone. */
    {
      const wrong = [];
      for (const target of ['index.html', 'web/trade_craft_landing.html']) {
      for (const [w, h] of [[390, 844], [1440, 900]]) {
        for (const scheme of ['light', 'dark']) {
          const ctx = await browser.newContext({ viewport: { width: w, height: h }, colorScheme: scheme });
          const p = await ctx.newPage();
          const tag = `${target} ${w} ${scheme}`;
          p.on('pageerror', (e) => errs.push(`pageerror (${tag}): ${e.message}`));
          p.on('console', (m) => { if (m.type() === 'error') errs.push(`console (${tag}): ${m.text()}`); });
          await p.goto(`${ORIGIN}/${target}`, { waitUntil: 'load' });
          const r = await p.evaluate(() => {
            // measure what a reader can open, not only what is open
            document.querySelectorAll('details:not([data-sitenav-menu])').forEach((d) => { d.open = true; });
            const rgba = (c) => { const v = (c.match(/[\d.]+/g) || []).map(Number); return [v[0], v[1], v[2], v.length > 3 ? v[3] : 1]; };
            const over = (top, bot) => [0, 1, 2].map((i) => top[i] * top[3] + bot[i] * (1 - top[3])).concat(1);
            const behind = (el) => {
              const stack = [];
              for (let e = el; e; e = e.parentElement) {
                const b = rgba(getComputedStyle(e).backgroundColor);
                if (b[3] > 0) { stack.push(b); if (b[3] >= 1) break; }
              }
              let acc = [255, 255, 255, 1];
              for (let i = stack.length - 1; i >= 0; i--) acc = over(stack[i], acc);
              return acc;
            };
            const lum = (c) => { const [r, g, b] = c.slice(0, 3).map((x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
            const low = [];
            for (const el of document.querySelectorAll('p, li, a, span, b, dt, dd, h1, h2, h3, h4, summary, button, kbd, code, figcaption')) {
              if (el.closest('svg') || !el.getClientRects().length) continue;
              if (![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) continue;
              const cs = getComputedStyle(el);
              if (cs.visibility === 'hidden') continue;
              const bg = behind(el);
              const fg = over(rgba(cs.color), bg);
              const [a, b] = [lum(fg), lum(bg)].sort((x, y) => y - x);
              const ratio = (a + 0.05) / (b + 0.05);
              const size = parseFloat(cs.fontSize);
              const large = size >= 24 || (size >= 18.66 && Number(cs.fontWeight) >= 700);
              if (ratio < (large ? 3 : 4.5)) low.push(`${el.tagName.toLowerCase()}.${el.className} ${ratio.toFixed(2)}`);
            }
            // every control a finger has to hit: 24 CSS px tall at least
            const small = [...document.querySelectorAll('a[href], button, summary')]
              .filter((e) => !e.closest('svg') && e.getClientRects().length
                && getComputedStyle(e).visibility !== 'hidden')
              .map((e) => [e, e.getBoundingClientRect()])
              .filter(([, r]) => r.width > 0 && r.height < 24)
              .map(([e, r]) => `${e.tagName.toLowerCase()}.${e.className} "${e.textContent.trim().slice(0, 24)}" ${r.height.toFixed(1)}px`);
            return { sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, low, small };
          });
          if (r.sw > r.cw) wrong.push(`${tag}: scrollWidth ${r.sw} > ${r.cw}`);
          for (const l of r.low.slice(0, 3)) wrong.push(`${tag}: contrast ${l}`);
          for (const l of r.small.slice(0, 3)) wrong.push(`${tag}: tap target ${l}`);
          if (w === 390 && target === 'index.html') {
            const reached = new Set();
            for (let i = 0; i < 40 && reached.size < 2; i++) {
              await p.keyboard.press('Tab');
              const c = await p.evaluate(() => document.activeElement && document.activeElement.dataset.cta);
              if (c) reached.add(c);
            }
            if (reached.size !== 2) wrong.push(`${tag}: Tab reached only [${[...reached]}] of the two calls to action`);
          }
          await ctx.close();
        }
      }
      }
      ok('[browser] index.html and trade_craft_landing.html at 390 and 1440 px, light and dark: no '
        + 'horizontal scroll, every text node '
        + 'at WCAG AA contrast against the surface behind it, every link, button and summary at least '
        + '24px tall, and both calls to action reachable by Tab',
        wrong.length === 0, wrong.slice(0, 8));
    }

    /* The site header is web/sitenav.py's, and it sits on every page, over
       every page's own palette. Its text is held to AA and its links to the
       24px tap minimum on each of them, in both schemes, at both widths -
       the menu opened, so the links a phone reader reaches are measured too. */
    {
      const { readdirSync } = await import('node:fs');
      const pages = ['index.html', ...readdirSync(HERE).filter((f) => f.endsWith('.html')).sort().map((f) => `web/${f}`)];
      const wrong = [];
      for (const scheme of ['light', 'dark']) {
        for (const w of [1440, 390]) {
          const ctx = await browser.newContext({ viewport: { width: w, height: 800 }, colorScheme: scheme });
          const p = await ctx.newPage();
          for (const pg of pages) {
            await p.goto(`${ORIGIN}/${pg}`, { waitUntil: 'domcontentloaded' });
            const r = await p.evaluate(() => {
              const nav = document.querySelector('[data-sitenav]');
              if (!nav) return { bad: ['no site nav'] };
              nav.querySelectorAll('details').forEach((d) => { d.open = true; });
              const rgba = (c) => { const v = (c.match(/[\d.]+/g) || []).map(Number); return [v[0], v[1], v[2], v.length > 3 ? v[3] : 1]; };
              const over = (t, b) => [0, 1, 2].map((i) => t[i] * t[3] + b[i] * (1 - t[3])).concat(1);
              const behind = (el) => {
                const st = [];
                for (let e = el; e; e = e.parentElement) { const x = rgba(getComputedStyle(e).backgroundColor); if (x[3] > 0) { st.push(x); if (x[3] >= 1) break; } }
                let a = [255, 255, 255, 1];
                for (let i = st.length - 1; i >= 0; i--) a = over(st[i], a);
                return a;
              };
              const lum = (c) => { const [r, g, b] = c.slice(0, 3).map((x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
              const bad = [];
              for (const el of nav.querySelectorAll('a, span, summary')) {
                if (!el.getClientRects().length) continue;
                const bg = behind(el);
                const fg = over(rgba(getComputedStyle(el).color), bg);
                const [a, c] = [lum(fg), lum(bg)].sort((x, y) => y - x);
                const ratio = (a + 0.05) / (c + 0.05);
                if (ratio < 4.5) bad.push(`"${el.textContent.trim().slice(0, 18)}" ${ratio.toFixed(2)}:1`);
                const h = el.getBoundingClientRect().height;
                if (el.tagName !== 'SPAN' && h < 24) bad.push(`"${el.textContent.trim().slice(0, 18)}" ${h.toFixed(1)}px tall`);
              }
              return { bad };
            });
            for (const b of r.bad.slice(0, 2)) wrong.push(`${pg} ${w} ${scheme}: ${b}`);
          }
          await ctx.close();
        }
      }
      ok(`[browser] the site header on every page (${pages.length}), light and dark, 1440 and 390 px: `
        + 'every label at WCAG AA against the page\'s own surface and every link at least 24px tall',
        wrong.length === 0, wrong.slice(0, 8));
    }

    {
      /* The hero footage and the search palette, driven the way a visitor
         drives them. Contrast is MEASURED: for frames sampled across the
         clip, the frame is drawn the way object-fit:cover draws it, the
         scrim is composited over every pixel under each hero text element
         that has no background of its own, and the element's text colour
         must reach WCAG AA against the worst of those pixels. */
      const hv = [];
      const measure = async (scheme, page = 'index.html', sel = '.hero-copy *', style = null) => {
        const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: scheme });
        const pg = await ctx.newPage();
        pg.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
        await pg.goto(`${ORIGIN}/${page}`, { waitUntil: 'load' });
        if (style) await pg.evaluate((s) => document.documentElement.setAttribute('data-style', s), style);
        await pg.waitForFunction(() => { const v = document.querySelector('.hv-video'); return v && v.readyState >= 2 && v.currentTime > 0.3; }, null, { timeout: 20000 }).catch(() => {});
        const r = await pg.evaluate(async (sel) => {
          const v = document.querySelector('.hv-video');
          const host = document.querySelector('[data-hero-host]');
          const out = { playing: !v.paused && v.currentTime > 0.3, src: v.currentSrc, worst: [], frames: 0 };
          v.pause();
          const rgb = (c) => c.match(/[\d.]+/g).map(Number);
          const lin = (x) => { x /= 255; return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; };
          const L = (r, g, b) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
          const scrim = rgb(getComputedStyle(document.querySelector('.hv-scrim')).backgroundColor);
          const a = scrim.length > 3 ? scrim[3] : 1;
          const hr = host.getBoundingClientRect();
          const cv = document.createElement('canvas'); cv.width = Math.round(hr.width); cv.height = Math.round(hr.height);
          const g = cv.getContext('2d', { willReadFrequently: true });
          const scale = Math.max(hr.width / v.videoWidth, hr.height / v.videoHeight);
          const dw = v.videoWidth * scale; const dh = v.videoHeight * scale;
          const opaque = (el) => { for (let e = el; e && e !== host; e = e.parentElement) { const b = getComputedStyle(e).backgroundColor; if (b !== 'rgba(0, 0, 0, 0)' && b !== 'transparent') return true; } return false; };
          const els = [...host.querySelectorAll(sel)].filter((e) => [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())
            && !opaque(e) && e.getBoundingClientRect().width > 0);
          const worst = new Map();
          for (const f of [0.05, 0.25, 0.45, 0.65, 0.85]) {
            v.currentTime = f * v.duration;
            await new Promise((res) => v.addEventListener('seeked', res, { once: true }));
            g.drawImage(v, (hr.width - dw) / 2, (hr.height - dh) / 2, dw, dh);
            out.frames++;
            for (const el of els) {
              const er = el.getBoundingClientRect();
              const x = Math.max(0, Math.floor(er.left - hr.left)); const y = Math.max(0, Math.floor(er.top - hr.top));
              const w = Math.min(cv.width - x, Math.ceil(er.width)); const h = Math.min(cv.height - y, Math.ceil(er.height));
              if (w <= 0 || h <= 0) continue;
              const d = g.getImageData(x, y, w, h).data;
              let lo = 1; let hi = 0;
              for (let i = 0; i < d.length; i += 4) {
                const l = L(a * scrim[0] + (1 - a) * d[i], a * scrim[1] + (1 - a) * d[i + 1], a * scrim[2] + (1 - a) * d[i + 2]);
                if (l < lo) lo = l; if (l > hi) hi = l;
              }
              const tc = rgb(getComputedStyle(el).color); const lt = L(tc[0], tc[1], tc[2]);
              const cr = (p, q) => (Math.max(p, q) + 0.05) / (Math.min(p, q) + 0.05);
              const ratio = Math.min(cr(lt, lo), cr(lt, hi));
              const cs = getComputedStyle(el); const px = parseFloat(cs.fontSize); const bold = +cs.fontWeight >= 700;
              const need = px >= 24 || (bold && px >= 18.66) ? 3 : 4.5;
              const key = el.tagName.toLowerCase() + '.' + (el.className || '') + ' "' + el.textContent.trim().slice(0, 24) + '"';
              const prev = worst.get(key);
              if (!prev || ratio < prev.ratio) worst.set(key, { ratio: +ratio.toFixed(2), need });
            }
          }
          out.worst = [...worst].map(([k, w]) => ({ k, ...w }));
          return out;
        }, sel);
        await ctx.close();
        return r;
      };
      const dark = await measure('dark');
      const light = await measure('light');
      const fails = [...dark.worst.map((w) => ({ ...w, s: 'dark' })), ...light.worst.map((w) => ({ ...w, s: 'light' }))].filter((w) => w.ratio < w.need);
      const minOf = (r) => Math.min(...r.worst.map((w) => w.ratio));
      ok(`[browser] over ${dark.frames} sampled frames of the footage, light and dark, every hero text without its own `
        + `background holds WCAG AA against the worst scrimmed pixel under it (lowest: dark ${minOf(dark)}, light ${minOf(light)})`,
        dark.frames >= 5 && light.frames >= 5 && dark.worst.length > 5 && fails.length === 0,
        fails.slice(0, 6).map((f) => `${f.s} ${f.k} ${f.ratio} < ${f.need}`));
      // the landing hero carries the same footage under its own copy (lede-2 is --muted): measured the same way
      const ldark = await measure('dark', 'web/trade_craft_landing.html', ':scope > :not(.hv) , :scope > :not(.hv) *');
      const llight = await measure('light', 'web/trade_craft_landing.html', ':scope > :not(.hv) , :scope > :not(.hv) *');
      const lfails = [...ldark.worst.map((w) => ({ ...w, s: 'dark' })), ...llight.worst.map((w) => ({ ...w, s: 'light' }))].filter((w) => w.ratio < w.need);
      ok(`[browser] trade_craft_landing.html: over ${ldark.frames} sampled frames, light and dark, every hero text without its own `
        + `background holds WCAG AA against the worst scrimmed pixel under it (lowest: dark ${minOf(ldark)}, light ${minOf(llight)})`,
        ldark.frames >= 5 && llight.frames >= 5 && ldark.worst.length >= 3 && lfails.length === 0,
        lfails.slice(0, 6).map((f) => `${f.s} ${f.k} ${f.ratio} < ${f.need}`));
      // the five site-wide styles (design_kit.STYLES, MEDIA's nav Style menu): the hero is measured in each
      {
        const { execFileSync: ef } = await import('node:child_process');
        const STY = JSON.parse(ef('python3', ['-c', ['import json, sys', `sys.path.insert(0, ${JSON.stringify(HERE)})`,
          'import design_kit as K', 'print(json.dumps([s["id"] for s in K.STYLES]))'].join('\n')], { encoding: 'utf8' }));
        const per = []; const sfails = [];
        for (const st of STY) {
          const hi = await measure('dark', 'index.html', '.hero-copy *', st);
          const hl = await measure('dark', 'web/trade_craft_landing.html', ':scope > :not(.hv) , :scope > :not(.hv) *', st);
          per.push(`${st}: index ${minOf(hi)}, landing ${minOf(hl)}`);
          for (const [nm, r] of [['index', hi], ['landing', hl]]) {
            if (r.frames < 5 || r.worst.length < 3) sfails.push(`${st} ${nm}: ${r.frames} frames, ${r.worst.length} texts`);
            for (const w of r.worst) if (w.ratio < w.need) sfails.push(`${st} ${nm} ${w.k} ${w.ratio} < ${w.need}`);
          }
        }
        console.log('      hero contrast per style:', per.join(' | '));
        ok(`[browser] in each of the ${STY.length} site styles, the hero text on index.html and trade_craft_landing.html holds WCAG AA `
          + `against the worst scrimmed pixel over 5 sampled frames (${per.join('; ')})`, STY.length === 5 && sfails.length === 0, sfails.slice(0, 6));
      }
      ok('[browser] at 1440 px with motion welcome the footage plays after load, from the WebM source',
        dark.playing && /\.webm$/.test(dark.src), [JSON.stringify({ playing: dark.playing, src: dark.src })]);

      const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
      const pg = await ctx.newPage();
      await pg.goto(`${ORIGIN}/index.html`, { waitUntil: 'load' });
      await pg.waitForTimeout(1500);
      const rm = await pg.evaluate(() => { const v = document.querySelector('.hv-video'); const b = document.querySelector('[data-hero-video-toggle]');
        return { paused: v.paused, src: v.currentSrc, hidden: b.hidden, pressed: b.getAttribute('aria-pressed'), label: b.textContent.trim() }; });
      ok('[browser] under prefers-reduced-motion the footage is never fetched or started: poster only, and the '
        + 'visible button offers Play', rm.paused && rm.src === '' && !rm.hidden && rm.pressed === 'true'
          && /Play background video/.test(rm.label), [JSON.stringify(rm)]);
      await ctx.close();

      const c2 = await browser.newContext({ viewport: { width: 1440, height: 900 } });
      const p2 = await c2.newPage();
      await p2.goto(`${ORIGIN}/index.html`, { waitUntil: 'load' });
      const h1a = await p2.$eval('h1', (e) => JSON.stringify(e.getBoundingClientRect()));
      await p2.waitForFunction(() => { const v = document.querySelector('.hv-video'); return v && !v.paused && v.currentTime > 0.3; }, null, { timeout: 20000 }).catch(() => {});
      const h1b = await p2.$eval('h1', (e) => JSON.stringify(e.getBoundingClientRect()));
      await p2.click('[data-hero-video-toggle]');
      const afterPause = await p2.evaluate(() => { const v = document.querySelector('.hv-video'); const b = document.querySelector('[data-hero-video-toggle]');
        const t = v.currentTime; return { paused: v.paused, pressed: b.getAttribute('aria-pressed'), label: b.textContent.trim(), t }; });
      await p2.waitForTimeout(600);
      const t2 = await p2.evaluate(() => document.querySelector('.hv-video').currentTime);
      ok('[browser] the Pause button stops the footage and says Play; starting the footage moved nothing on the page',
        afterPause.paused && afterPause.pressed === 'true' && /Play background video/.test(afterPause.label)
          && Math.abs(t2 - afterPause.t) < 0.01 && h1a === h1b, [JSON.stringify(afterPause), h1a === h1b ? 'no shift' : `${h1a} -> ${h1b}`]);

      await p2.keyboard.press('Control+k');
      const open1 = await p2.evaluate(() => ({ open: document.getElementById('ss-dlg').open, focus: document.activeElement && document.activeElement.id }));
      await p2.keyboard.type('crane');
      await p2.waitForTimeout(100);
      const res = await p2.evaluate(() => ({ n: document.querySelectorAll('#ss-list [role="option"]').length,
        act: document.getElementById('ss-q').getAttribute('aria-activedescendant'),
        sel: document.querySelectorAll('#ss-list [aria-selected="true"]').length,
        first: (document.querySelector('#ss-list [role="option"]') || { textContent: '' }).textContent,
        status: document.getElementById('ss-status').textContent }));
      await p2.keyboard.press('ArrowDown');
      const act2 = await p2.evaluate(() => document.getElementById('ss-q').getAttribute('aria-activedescendant'));
      await p2.keyboard.press('Escape');
      const closed = await p2.evaluate(() => ({ open: document.getElementById('ss-dlg').open }));
      ok('[browser] Ctrl+K opens the search with focus in the box; typing "crane" lists matches with one active '
        + 'option announced in the status; ArrowDown moves it; Esc closes',
        open1.open && open1.focus === 'ss-q' && res.n > 0 && res.act === 'ss-o0' && res.sel === 1
          && /crane/i.test(res.first) && /result/.test(res.status) && act2 === 'ss-o1' && !closed.open,
        [JSON.stringify({ open1, res, act2, closed })]);
      await p2.click('[data-search-open]');
      await p2.keyboard.type('verify a record');
      await p2.waitForTimeout(100);
      const [nav] = await Promise.all([p2.waitForNavigation({ waitUntil: 'load' }), p2.keyboard.press('Enter')]);
      ok('[browser] the visible search button opens it too, and Enter follows the active result to a page that loads',
        !!nav && nav.ok() && /trade_craft_verify\.html$/.test(p2.url()), [p2.url()]);
      await c2.close();

      const c3 = await browser.newContext({ viewport: { width: 390, height: 844 } });
      const p3 = await c3.newPage();
      await p3.goto(`${ORIGIN}/index.html`, { waitUntil: 'load' });
      await p3.waitForTimeout(1200);
      const small = await p3.evaluate(() => { const v = document.querySelector('.hv-video'); return { paused: v.paused, src: v.currentSrc, sw: document.documentElement.scrollWidth }; });
      ok('[browser] at 390 px the footage does not autoplay (poster only) and the page does not scroll sideways',
        small.paused && small.src === '' && small.sw <= 390, [JSON.stringify(small)]);
      await c3.close();
    }

    {
      /* Wave 3: the section footage and the count-up, driven in the browser.
         A band's words sit over its clip, so they are MEASURED like the
         hero's: the band is scrolled into view, its clip starts, frames are
         sampled, the band's scrim is composited over every pixel under each
         text element with no background of its own, and the text must reach
         WCAG AA against the worst of them. */
      const measureBand = async (scheme, page) => {
        const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: scheme });
        const pg = await ctx.newPage();
        pg.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
        await pg.goto(`${ORIGIN}/${page}`, { waitUntil: 'load' });
        await pg.$eval('[data-band-host]', (e) => e.scrollIntoView({ block: 'center' }));
        await pg.waitForFunction(() => { const v = document.querySelector('[data-band-host] .vb-video'); return v && v.readyState >= 2 && v.currentTime > 0.3; }, null, { timeout: 20000 }).catch(() => {});
        const r = await pg.evaluate(async () => {
          const host = document.querySelector('[data-band-host]');
          const v = host.querySelector('.vb-video');
          const out = { playing: !v.paused && v.currentTime > 0.3, src: v.currentSrc, worst: [], frames: 0 };
          v.pause();
          const rgb = (c) => c.match(/[\d.]+/g).map(Number);
          const lin = (x) => { x /= 255; return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; };
          const L = (r, g, b) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
          const scrim = rgb(getComputedStyle(host.querySelector('.vb-scrim')).backgroundColor);
          const a = scrim.length > 3 ? scrim[3] : 1;
          const hr = host.getBoundingClientRect();
          const cv = document.createElement('canvas'); cv.width = Math.round(hr.width); cv.height = Math.round(hr.height);
          const g = cv.getContext('2d', { willReadFrequently: true });
          const scale = Math.max(hr.width / v.videoWidth, hr.height / v.videoHeight);
          const dw = v.videoWidth * scale; const dh = v.videoHeight * scale;
          const opaque = (el) => { for (let e = el; e && e !== host; e = e.parentElement) { const b = getComputedStyle(e).backgroundColor; if (b !== 'rgba(0, 0, 0, 0)' && b !== 'transparent') return true; } return false; };
          const els = [...host.querySelectorAll('.vb-inner *')].filter((e) => [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())
            && !opaque(e) && e.getBoundingClientRect().width > 0);
          const worst = new Map();
          for (const f of [0.05, 0.25, 0.45, 0.65, 0.85]) {
            v.currentTime = f * v.duration;
            await new Promise((res) => v.addEventListener('seeked', res, { once: true }));
            const hr2 = host.getBoundingClientRect();
            g.drawImage(v, (hr2.width - dw) / 2, (hr2.height - dh) / 2, dw, dh);
            out.frames++;
            for (const el of els) {
              const er = el.getBoundingClientRect();
              const x = Math.max(0, Math.floor(er.left - hr2.left)); const y = Math.max(0, Math.floor(er.top - hr2.top));
              const w = Math.min(cv.width - x, Math.ceil(er.width)); const h = Math.min(cv.height - y, Math.ceil(er.height));
              if (w <= 0 || h <= 0) continue;
              const d = g.getImageData(x, y, w, h).data;
              let lo = 1; let hi = 0;
              for (let i = 0; i < d.length; i += 4) {
                const l = L(a * scrim[0] + (1 - a) * d[i], a * scrim[1] + (1 - a) * d[i + 1], a * scrim[2] + (1 - a) * d[i + 2]);
                if (l < lo) lo = l; if (l > hi) hi = l;
              }
              const tc = rgb(getComputedStyle(el).color); const lt = L(tc[0], tc[1], tc[2]);
              const cr = (p, q) => (Math.max(p, q) + 0.05) / (Math.min(p, q) + 0.05);
              const ratio = Math.min(cr(lt, lo), cr(lt, hi));
              const cs = getComputedStyle(el); const px = parseFloat(cs.fontSize); const bold = +cs.fontWeight >= 700;
              const need = px >= 24 || (bold && px >= 18.66) ? 3 : 4.5;
              const key = el.tagName.toLowerCase() + '.' + (el.className && el.className.baseVal === undefined ? el.className : '') + ' "' + el.textContent.trim().slice(0, 24) + '"';
              const prev = worst.get(key);
              if (!prev || ratio < prev.ratio) worst.set(key, { ratio: +ratio.toFixed(2), need });
            }
          }
          out.worst = [...worst].map(([k, w]) => ({ k, ...w }));
          return out;
        });
        await ctx.close();
        return r;
      };
      const minOf = (r) => (r.worst.length ? Math.min(...r.worst.map((w) => w.ratio)) : NaN);
      const bandRes = {};
      for (const page of ['index.html', 'web/trade_craft_landing.html']) {
        const d = await measureBand('dark', page); const l = await measureBand('light', page);
        bandRes[page] = { d, l };
        const f = [...d.worst.map((w) => ({ ...w, s: 'dark' })), ...l.worst.map((w) => ({ ...w, s: 'light' }))].filter((w) => w.ratio < w.need);
        ok(`[browser] ${page}: the band's clip plays once scrolled into view, and over ${d.frames} sampled frames, light and dark, every band `
          + `text without its own background holds WCAG AA against the worst scrimmed pixel (lowest: dark ${minOf(d)}, light ${minOf(l)})`,
          d.playing && /\.webm$/.test(d.src) && d.frames >= 5 && l.frames >= 5 && d.worst.length >= 3 && f.length === 0,
          [JSON.stringify({ playing: d.playing, src: d.src }), ...f.slice(0, 6).map((x) => `${x.s} ${x.k} ${x.ratio} < ${x.need}`)]);
      }
      console.log('      band contrast:', JSON.stringify(Object.fromEntries(Object.entries(bandRes).map(([k, v]) => [k, { dark: minOf(v.d), light: minOf(v.l) }]))));

      // count-up: the built text is the final text; with motion it animates and lands on it, under reduced motion it never changes
      const built = [...home.matchAll(/<div class="stat" data-stat="([^"]*)"[^>]*><dt>[^<]*<\/dt><dd>([^<]*)<\/dd><\/div>/g)].map((m) => m[2]);
      const cuRun = async (reduced) => {
        const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: reduced ? 'reduce' : 'no-preference' });
        const pg = await ctx.newPage();
        pg.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
        await pg.goto(`${ORIGIN}/index.html`, { waitUntil: 'load' });
        const seen = await pg.evaluate(() => new Promise((res) => {
          const dds = [...document.querySelectorAll('[data-countup] dd')];
          const samples = []; const t0 = performance.now();
          (function tick() { samples.push(dds.map((d) => d.textContent)); if (performance.now() - t0 < 1600) requestAnimationFrame(tick); else res(samples); }());
        }));
        await ctx.close();
        return seen;
      };
      const moving = await cuRun(false); const still = await cuRun(true);
      const last = moving[moving.length - 1];
      const animated = moving.some((s) => s.some((t, i) => t !== built[i]));
      const stillChanged = still.filter((s) => JSON.stringify(s) !== JSON.stringify(built)).length;
      ok(`[browser] index.html: the hero figures count up with motion welcome and land on exactly the built registry text (${built.length} figures); `
        + `under prefers-reduced-motion not one of ${still.length} sampled frames shows anything but the built text`,
        built.length >= 6 && animated && JSON.stringify(last) === JSON.stringify(built) && stillChanged === 0,
        [`animated=${animated}`, `last=${JSON.stringify(last)}`, `built=${JSON.stringify(built)}`, `reduced frames changed=${stillChanged}`]);
    }

    ok('[browser] neither page raised an uncaught error nor logged a console error while every '
      + 'course was opened and a seat followed',
      errs.length === 0, errs.slice(0, 4));
    await browser.close();
  }
}

console.log(`\nhome: ${n} checks, ${bad} failure${bad === 1 ? '' : 's'}`);
process.exit(bad ? 1 : 0);
