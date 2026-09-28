/**
 * The interactive campus map's lesson layer, held to the registries it reads.
 *
 * `web/build_interactive_map.py` writes `web/trade_craft_interactive.html`
 * with lessons/registry/lessons.json and completion/registry/completion.json
 * embedded whole. Every claim the page can make about a lesson - where a
 * step stands, what a step kind can evidence, which edge the ladder draws,
 * which lesson can be completed - is recomputed here from the registry that
 * owns it and the SHIPPED PAGE is held to the answer. Static: no browser.
 *
 *   [registry]  the registries only
 *   [shipped]   the built HTML and the data embedded in it
 *   [renderer]  the page's own script, comments stripped, matched by structure
 *
 *   node web/test_interactive.mjs
 *   node web/test_interactive.mjs --page=/tmp/broken.html --root=/tmp/root
 */
import { readFileSync, existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const arg = (name) => {
  const hit = args.find((a) => a.startsWith(`--${name}=`));
  return hit === undefined ? null : hit.slice(name.length + 3);
};
const ROOT = resolve(arg('root') !== null ? arg('root') : join(HERE, '..'));
const PAGE = resolve(arg('page') !== null ? arg('page') : join(HERE, 'trade_craft_interactive.html'));
const WEB = dirname(PAGE);

let n = 0, bad = 0;
const ok = (m, c, evidence = []) => {
  if (c) { n++; console.log('  ok  ' + m); return; }
  bad++;
  console.error('FAIL  ' + m);
  for (const e of evidence) console.error('      ' + e);
};
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const readJSON = (rel) => JSON.parse(readFileSync(join(ROOT, rel), 'utf8'));
const must = (o, k, where) => {
  if (o === null || typeof o !== 'object' || !(k in o)) throw new Error(`${where}: no field ${k}`);
  return o[k];
};

/* ---------------------------------------------------------- registries -- */
const LESSONS_PATH = 'lessons/registry/lessons.json';
const COMPLETION_PATH = 'completion/registry/completion.json';
const HALLS_PATH = 'pack/registry/halls.json';
const lessonsReg = readJSON(LESSONS_PATH);
const completionReg = readJSON(COMPLETION_PATH);
const hallsReg = readJSON(HALLS_PATH);
const HALL = new Map(hallsReg.halls.map((h) => [h.slug, h]));
const LESSONS = must(lessonsReg, 'lessons', LESSONS_PATH);
const STEP_KINDS = must(lessonsReg, 'step_kinds', LESSONS_PATH);
const OFF_ROOM = must(lessonsReg, 'off_room_places', LESSONS_PATH);
const EDGES = must(must(lessonsReg, 'ladder', LESSONS_PATH), 'edges', `${LESSONS_PATH}#ladder`);
const EV_RULE = must(completionReg, 'evidence_rule', COMPLETION_PATH);
const EV_CLASSES = must(completionReg, 'evidence_classes', COMPLETION_PATH);
const C_LESSONS = must(completionReg, 'lessons', COMPLETION_PATH);
const C_COUNTS = must(completionReg, 'counts', COMPLETION_PATH);

/* ------------------------------------------------------------- shipped -- */
const html = readFileSync(PAGE, 'utf8');
const dataM = html.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/);
ok(`[shipped] the page embeds its data block`, dataM !== null);
const D = dataM ? JSON.parse(dataM[1]) : {};
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
ok(`[shipped] the page has exactly one renderer script`, scripts.length === 1);
const JS = (scripts[0] !== undefined ? scripts[0] : '')
  .replace(/\/\*[\s\S]*?\*\//g, '')
  .replace(/^\s*\/\/.*$/gm, '');
const outside = html.replace(/<script id="data"[\s\S]*?<\/script>/, '');

/* 1. the registries arrive whole and verbatim */
ok(`[shipped] D.lessons equals ${LESSONS_PATH} verbatim`, same(D.lessons, lessonsReg));
ok(`[shipped] D.lessons.lessons, .ladder, .step_kinds equal the registry`,
  same(must(D, 'lessons', 'D').lessons, LESSONS) && same(D.lessons.ladder, lessonsReg.ladder)
  && same(D.lessons.step_kinds, STEP_KINDS));
ok(`[shipped] D.completion equals ${COMPLETION_PATH} verbatim`, same(D.completion, completionReg));

/* 2. every step's hall and room resolve */
const roomsOf = (h) => must(D, 'layouts', 'D')[h.lay].map((r) => ({
  ...r, label: must(must(D, 'roomDefs', 'D'), r.strand, 'D.roomDefs').label }));
const dHall = new Map((D.halls !== undefined ? D.halls : []).map((h) => [h.slug, h]));
{
  const faults = [];
  for (const [lid, les] of Object.entries(must(D.lessons, 'lessons', 'D.lessons'))) {
    const w = `lessons.${lid}`;
    if (!HALL.has(les.hall)) { faults.push(`${w}: hall ${les.hall} is not in ${HALLS_PATH}`); continue; }
    if (!dHall.has(les.hall)) { faults.push(`${w}: hall ${les.hall} is not a tile on the page`); continue; }
    const rooms = roomsOf(dHall.get(les.hall));
    const room = rooms.find((r) => r.strand === les.strand);
    if (!room) faults.push(`${w}: strand ${les.strand} has no room in hall ${les.hall}`);
    else if (room.label !== les.room_label) faults.push(`${w}: room_label ${les.room_label} is not ${room.label}`);
    les.steps.forEach((st, i) => {
      if (!rooms.some((r) => r.strand === st.where) && !(st.where in OFF_ROOM))
        faults.push(`${w}.steps[${i}]: where ${st.where} is neither a room of ${les.hall} nor an off-room place`);
      if (!(st.kind in STEP_KINDS)) faults.push(`${w}.steps[${i}]: kind ${st.kind} is not a step kind`);
      if (st.n !== i + 1) faults.push(`${w}.steps[${i}]: n=${st.n}`);
    });
    if (!dHall.get(les.hall).lessonIds.includes(lid)) faults.push(`${w}: not on hall ${les.hall}'s lessonIds`);
  }
  for (const h of dHall.values()) for (const lid of h.lessonIds)
    if (!(lid in LESSONS) || LESSONS[lid].hall !== h.slug) faults.push(`halls.${h.slug}.lessonIds: ${lid} does not stand there`);
  ok(`[shipped] every step's hall is in ${HALLS_PATH} and its room or place resolves on the page`, faults.length === 0, faults);
}
const nSteps = Object.values(LESSONS).reduce((a, l) => a + l.steps.length, 0);
ok(`[registry] lessons/steps counts recompute (${Object.keys(LESSONS).length} lessons, ${nSteps} steps)`,
  Object.keys(LESSONS).length === lessonsReg.counts.lessons && nSteps === lessonsReg.counts.steps
  && Object.keys(STEP_KINDS).length === lessonsReg.counts.step_kinds);

/* 3. the three evidence classes, exactly as completion.json names them */
{
  const classOf = (kind) => must(must(EV_RULE, kind, 'evidence_rule'), 'class', `evidence_rule.${kind}`);
  const faults = [];
  const expectedClasses = new Set(Object.keys(EV_CLASSES));
  for (const kind of Object.keys(STEP_KINDS)) {
    const cls = classOf(kind);
    if (!expectedClasses.has(cls)) faults.push(`evidence_rule.${kind}: class ${cls} unknown`);
    if ((STEP_KINDS[kind].records !== null) !== (cls === 'episode-backed'))
      faults.push(`step_kinds.${kind}: records=${STEP_KINDS[kind].records} but class ${cls}`);
    if (EV_RULE[kind].records !== STEP_KINDS[kind].records) faults.push(`evidence_rule.${kind}: records disagrees`);
  }
  ok(`[registry] episode-backed <=> records != null, over every step kind`, faults.length === 0, faults);
  const byClass = {};
  for (const cls of expectedClasses) byClass[cls] = 0;
  for (const st of Object.values(D.lessons.lessons).flatMap((l) => l.steps)) byClass[classOf(st.kind)] += 1;
  ok(`[shipped] evidence class counts recompute from the embedded steps and equal completion.json counts`,
    byClass['episode-backed'] === C_COUNTS.episode_backed_steps && byClass['device-mark'] === C_COUNTS.device_mark_steps
    && byClass['self-reported'] === C_COUNTS.self_reported_steps
    && Object.values(byClass).reduce((a, b) => a + b, 0) === nSteps,
    [JSON.stringify(byClass)]);
  const shippedClasses = Object.keys(D.completion.evidence_classes);
  ok(`[shipped] the page's evidence classes are completion.json's three, no more`,
    same([...shippedClasses].sort(), [...expectedClasses].sort()) && shippedClasses.length === 3);
  const embeddedRule = D.completion.evidence_rule;
  const reclassed = Object.keys(STEP_KINDS).filter((k) => embeddedRule[k].class !== classOf(k)
    || (D.lessons.step_kinds[k].records !== null) !== (embeddedRule[k].class === 'episode-backed'));
  ok(`[shipped] no step kind is reclassed on the page`, reclassed.length === 0, reclassed);
}

/* 4. the ladder */
{
  const faults = [];
  for (const [i, e] of EDGES.entries()) for (const side of ['lesson', 'needs'])
    if (!(e[side] in LESSONS)) faults.push(`ladder.edges[${i}].${side}=${e[side]} is not a lesson`);
  const reasons = [...new Set(EDGES.map((e) => e.because))];
  ok(`[registry] ladder edges recompute: ${EDGES.length} edges, ${reasons.length} reasons (${reasons.join(', ')})`,
    faults.length === 0 && EDGES.length === lessonsReg.counts.prerequisite_edges
    && reasons.length === lessonsReg.counts.edge_reasons && EDGES.length === C_COUNTS.ladder_edges, faults);
  ok(`[shipped] the embedded ladder equals the registry edges and completion.json#ladder`,
    same(D.lessons.ladder.edges, EDGES) && same(D.completion.ladder, EDGES)
    && D.lessons.ladder.edges.length === EDGES.length);
}

/* 5. completable */
{
  const cannot = (lid) => LESSONS[lid].steps.some((st) => must(EV_RULE, st.kind, 'evidence_rule').evidenceable === false);
  const faults = [];
  for (const lid of Object.keys(LESSONS)) {
    const c = must(D.completion.lessons, lid, 'D.completion.lessons');
    if (c.completable !== !cannot(lid)) faults.push(`completion.lessons.${lid}.completable=${c.completable}`);
    if (c.completable !== (c.not_completable_why === null)) faults.push(`completion.lessons.${lid}: why/flag disagree`);
    if (c.hall !== LESSONS[lid].hall) faults.push(`completion.lessons.${lid}.hall`);
  }
  const yes = Object.keys(LESSONS).filter((lid) => C_LESSONS[lid].completable).length;
  ok(`[shipped] completable recomputes per lesson from evidence_rule.evidenceable: ${yes} can, ${Object.keys(LESSONS).length - yes} cannot`,
    faults.length === 0 && yes === C_COUNTS.lessons_completable
    && Object.keys(LESSONS).length - yes === C_COUNTS.lessons_not_completable
    && Object.keys(D.completion.lessons).length === Object.keys(LESSONS).length, faults);
}

/* 6. no typed count outside the JSON */
{
  const counts = new Set([Object.keys(LESSONS).length, nSteps, EDGES.length, C_COUNTS.lessons_completable,
    C_COUNTS.lessons_not_completable, C_COUNTS.episode_backed_steps, C_COUNTS.device_mark_steps,
    C_COUNTS.self_reported_steps, C_COUNTS.recording_steps, C_COUNTS.silent_steps].map(String));
  const fnBody = (name) => {
    const i = JS.indexOf(`function ${name}(`);
    if (i < 0) return null;
    let depth = 0, j = JS.indexOf('{', i);
    for (; j < JS.length; j++) { if (JS[j] === '{') depth++; else if (JS[j] === '}' && --depth === 0) break; }
    return JS.slice(i, j + 1);
  };
  const lessonJS = ['ladderEdges', 'lessonPaths', 'lessonCards', 'evClassCounts', 'render'].map(fnBody);
  ok(`[renderer] the lesson renderer functions exist`, lessonJS.every((b) => b !== null));
  const figs = [...JS.matchAll(/data-fig="[a-z]+"><b>\$\{([^}]*)\}<\/b>/g)].map((m) => m[1]);
  const evLegend = JS.match(/data-evclass="\$\{cls\}"[^`]*<b>\$\{n\}<\/b>/);
  const typed = [...(lessonJS.join('\n') + '\n' + figs.join('\n')).matchAll(/(?<![\w.$])(\d+)(?![\w.])/g)]
    .map((m) => m[1]).filter((v) => counts.has(v));
  ok(`[renderer] the lesson figures are computed at render, not typed (${figs.length} figures, evidence legend from counts)`,
    figs.length >= 3 && figs.every((f) => /\.length|nCompletable\(\)/.test(f)) && evLegend !== null && typed.length === 0,
    typed.map((v) => `literal ${v}`));
  const outsideJS = outside.replace(/<script>[\s\S]*?<\/script>/, '');
  const pre = [...outsideJS.matchAll(/<b>(\d+)<\/b>/g)].map((m) => m[1]).filter((v) => counts.has(v));
  ok(`[shipped] no lesson count is pre-rendered into the static HTML`, pre.length === 0, pre);
}

/* 7. hrefs */
{
  const hrefs = [...new Set([...JS.matchAll(/href="([^"$?#]+)/g)].map((m) => m[1]))];
  const missing = hrefs.filter((h) => !existsSync(join(WEB, h)));
  ok(`[shipped] every relative href in the renderer resolves under web/ (${hrefs.join(', ')})`,
    hrefs.length > 0 && missing.length === 0, missing);
  const lessonsPage = join(WEB, 'trade_craft_lessons.html');
  const lp = existsSync(lessonsPage) ? readFileSync(lessonsPage, 'utf8') : '';
  const anchorTpl = /href="trade_craft_lessons\.html#lesson-\$\{(lid|e\.needs|e\.lesson)\}"/g;
  const tpls = [...JS.matchAll(anchorTpl)].map((m) => m[0]);
  const noAnchor = Object.keys(LESSONS).filter((lid) => !lp.includes(`id="lesson-${lid}"`));
  ok(`[shipped] the lesson deep link uses the lessons page's own anchor and every lesson has one`,
    tpls.length >= 1 && noAnchor.length === 0, noAnchor);
  ok(`[shipped] the 3D hall deep link carries the lesson's hall`,
    /href="trade_craft_3d\.html\?hall=\$\{les\.hall\}/.test(JS) && existsSync(join(WEB, 'trade_craft_3d.html')));
}

/* 8. renderer structure */
{
  const paths = fnSlice('lessonPaths');
  ok(`[renderer] lessonPaths draws one <g data-lesson> with a path per lesson of the hall, one mark per step`,
    /h\.lessonIds\.map\(/.test(paths) && /data-lesson="\$\{lid\}"/.test(paths) && /<path d="\$\{line\}"/.test(paths)
    && /les\.steps\.map\(/.test(paths) && /data-step="\$\{st\.n\}" data-kind="\$\{st\.kind\}" data-class="\$\{cls\}"/.test(paths));
  const edges = fnSlice('ladderEdges');
  ok(`[renderer] ladderEdges draws one <path data-edge data-because> per D.lessons.ladder.edges with the reason as its title`,
    /LADDER\.map\(/.test(edges) && /const LADDER = D\.lessons\.ladder\.edges;/.test(JS)
    && /data-edge="\$\{e\.lesson\}>\$\{e\.needs\}" data-because="\$\{e\.because\}"/.test(edges)
    && /<title>[^<]*\$\{e\.because\}<\/title>/.test(edges));
  const cards = fnSlice('lessonCards');
  ok(`[renderer] lessonCards states completable and not_completable_why from D.completion`,
    /data-completable="\$\{c\.completable\}"/.test(cards) && /c\.not_completable_why/.test(cards)
    && /const completion = \(lid\) => must\(D\.completion\.lessons, lid/.test(JS));
  ok(`[renderer] the evidence class of a step kind is read from D.completion.evidence_rule, never typed`,
    /const evClass = \(kind\) => must\(must\(EV_RULE, kind/.test(JS) && /const EV_RULE = D\.completion\.evidence_rule;/.test(JS));
  ok(`[renderer] the lessons layer is a toggle and the legend lists the evidence classes from D.completion.evidence_classes`,
    /\['lessons','interactive\.lessons'\]/.test(JS) && /const EV_CLASSES = Object\.keys\(D\.completion\.evidence_classes\);/.test(JS)
    && /body\.L-lessons #ladder\{display:block\}/.test(html));
}

/* 9. the lesson layer's labels come from the catalog, not from English literals */
{
  const KEYS = ['interactive.lessons', 'interactive.lessonsInRooms', 'interactive.lessonsHere',
    'interactive.steps', 'interactive.completable', 'interactive.notCompletable'];
  const { readdirSync } = await import('node:fs');
  const locDir = join(ROOT, 'i18n', 'locales');
  const locales = readdirSync(locDir).filter((f) => f.endsWith('.json')).map((f) => f.replace(/\.json$/, ''));
  const gaps = [];
  for (const l of locales) {
    const disk = JSON.parse(readFileSync(join(locDir, `${l}.json`), 'utf8')).strings;
    const shipped = D.i18n !== undefined && D.i18n[l] !== undefined ? D.i18n[l].strings : {};
    for (const k of KEYS) {
      if (typeof disk[k] !== 'string' || !disk[k].trim()) gaps.push(`${l}: ${k} missing on disk`);
      else if (shipped[k] !== disk[k]) gaps.push(`${l}: ${k} embedded != disk`);
    }
  }
  ok(`[shipped] every one of the ${locales.length} locales carries the six interactive.* labels on disk and embedded in D.i18n, equal`,
    locales.length === 8 && gaps.length === 0, gaps);
  const lookups = {
    'interactive.lessons': /\['lessons','interactive\.lessons'\]/.test(JS) && /\$\{t\(lk\)\}<\/label>/.test(JS),
    'interactive.lessonsInRooms': /data-fig="lessons"><b>\$\{Object\.keys\(LESSONS\)\.length\}<\/b> \$\{t\('interactive\.lessonsInRooms'\)\}<\/span>/.test(JS),
    'interactive.steps': /data-fig="steps"><b>\$\{allSteps\(\)\.length\}<\/b> \$\{t\('interactive\.steps'\)\}<\/span>/.test(JS),
    'interactive.completable': /data-fig="completable"><b>\$\{nCompletable\(\)\}<\/b> \/ \$\{Object\.keys\(LESSONS\)\.length\} \$\{t\('interactive\.completable'\)\}<\/span>/.test(JS),
    'interactive.lessonsHere': /<h3>\$\{t\('interactive\.lessonsHere'\)\} \(\$\{h\.lessonIds\.length\}\)<\/h3>/.test(JS),
    'interactive.notCompletable': /<p class="nc">\$\{t\('interactive\.notCompletable'\)\}: \$\{c\.not_completable_why\}<\/p>/.test(JS),
  };
  const notLooked = Object.entries(lookups).filter(([, v]) => !v).map(([k]) => k);
  const LITERALS = ["'Lessons'", '"Lessons"', 'Lessons standing here', '</b> steps</span>', '} completable</span>',
    'not completable:', 'lessons standing in rooms', "lk === null ? 'Lessons'"];
  const remain = LITERALS.filter((s) => JS.includes(s));
  ok(`[renderer] the lesson layer's six labels are t('interactive.*') lookups through the page's own t(), and no English literal remains for them`,
    notLooked.length === 0 && remain.length === 0,
    [...notLooked.map((k) => `no lookup for ${k}`), ...remain.map((s) => `literal remains: ${s}`)]);
}
function fnSlice(name) {
  const i = JS.indexOf(`function ${name}(`);
  if (i < 0) return '';
  let depth = 0, j = JS.indexOf('{', i);
  for (; j < JS.length; j++) { if (JS[j] === '{') depth++; else if (JS[j] === '}' && --depth === 0) break; }
  return JS.slice(i, j + 1);
}

ok('[shipped] the campus grid tracks shrink to the screen (min(430px,100%)), so a 390px screen does not scroll sideways',
  /\.campusbody\{[^}]*minmax\(min\(430px,100%\),1fr\)/.test(html));


/* ---- simulated tasks (TASKS, wave 3): boards come from tasks/registry/tasks.json only ---- */
const TK = JSON.parse(readFileSync(new URL('../tasks/registry/tasks.json', import.meta.url), 'utf8'));
const tkRel = (h) => h === null ? null : (h.startsWith('web/') ? h.slice(4) : '../' + h);
const tkHall = (slug) => TK.tasks.filter((t) => t.place.kind === 'hall' && t.place.id === slug);
{
  const miss = D.halls.filter((h) => JSON.stringify((D.tasks[h.slug] || []).map((t) => [t.id, t.href]))
    !== JSON.stringify(tkHall(h.slug).map((t) => [t.id, tkRel(t.launch.href)]))).map((h) => h.slug);
  ok('[tasks] D.tasks holds, per hall, exactly the registry\'s tasks at that hall with hrefs made relative to web/', miss.length === 0, miss);
  ok('[tasks] linked lessons carry the registry\'s lesson titles', D.halls.every((h) => D.tasks[h.slug].every((t) =>
    t.requires.every((l) => D.lessons.lessons[l.id] && D.lessons.lessons[l.id].title === l.title))));
  ok('[tasks] the hall panel renders the board through taskkit\'s tcTaskBoard in the viewer\'s locale (t(\'tasks.*\'))',
    scripts.length === 1 && scripts[0].includes('function tcTaskBoard(') && scripts[0].includes("tcTaskBoard(D.tasks[h.slug], t('tasks.here'), (k) => t('tasks.' + k)"));
  const campMiss = Object.keys(D.campuses).filter((ck) => JSON.stringify((D.campusTasks[ck] || []).map((t) => t.id))
    !== JSON.stringify(TK.tasks.filter((t) => t.place.campus === ck && t.place.kind !== 'hall').map((t) => t.id)));
  ok('[tasks] D.campusTasks holds, per campus, exactly the registry\'s non-hall tasks there (restoration walks, crew hand-offs, wilds site walks, unlinked scenarios)', campMiss.length === 0, campMiss);
  ok('[tasks] every campus with such tasks renders a collapsible campus board through tcTaskBoard', scripts[0].includes("tcTaskBoard(D.campusTasks[ck]"));
  const keys = ['tasks.here', 'tasks.launch', 'tasks.linked', 'tasks.summary', 'tasks.honesty', 'tasks.lands.seat', 'tasks.kind.crib-drill'];
  ok('[tasks] every locale embedded carries the tasks.* labels the board reads', Object.values(D.i18n).every((c) => keys.every((k) => typeof c.strings[k] === 'string')));
}

if (bad) { console.error(`web/test_interactive: ${bad} FAILED, ${n} passed`); process.exit(1); }
console.log(`web/test_interactive: ${n} checks passed`);
