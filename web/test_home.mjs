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
import { readFileSync } from 'node:fs';
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

    ok('[browser] neither page raised an uncaught error nor logged a console error while every '
      + 'course was opened and a seat followed',
      errs.length === 0, errs.slice(0, 4));
    await browser.close();
  }
}

console.log(`\nhome: ${n} checks, ${bad} failure${bad === 1 ? '' : 's'}`);
process.exit(bad ? 1 : 0);
