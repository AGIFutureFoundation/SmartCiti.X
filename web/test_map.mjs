/**
 * The layered campus map, held to the registries it says it draws.
 *
 * `web/build_map.py` writes `web/trade_craft_map.html`: the hall pads by
 * district, and since this suite exists, six training layers on top of
 * them - lessons, simulator seats, flipped-classroom units, practitioner
 * sign-off, completable and not-completable lessons - each read at render
 * from a verbatim copy of the registry that owns it, carried in
 * `<script id="data" type="application/json">`. Every count in the legend
 * is computed by the page from that payload. This suite re-reads the same
 * registries, recomputes every per-hall figure, and holds the SHIPPED PAGE
 * to the answer: the payload is the registry byte-for-byte after parsing,
 * the renderer derives its figures from the payload by the STRUCTURE this
 * file greps for in the script (comments stripped), no legend figure is
 * typed into the markup or the script, every link resolves to a file in
 * web/, and the sign-off layer can only ever say what pack/hall_signoff.mjs
 * says - nobody, today.
 *
 * MATCH STRUCTURE, NEVER A SENTENCE: the checks below read the JSON block,
 * data attributes, ids and the renderer's own expressions. Static, node
 * ESM, no browser, no network.
 *
 *   node web/test_map.mjs
 *   node web/test_map.mjs --page=/tmp/broken.html --root=/tmp/broken-root
 *
 * `--page` and `--root` exist for the mutation tests: point the suite at a
 * broken copy and watch the check that covers that fault fail by name.
 */
import { readFileSync, existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const arg = (name) => {
  const hit = args.find((a) => a.startsWith(`--${name}=`));
  return hit === undefined ? null : hit.slice(name.length + 3);
};
const ROOT = arg('root') ? resolve(arg('root')) : resolve(HERE, '..');
const PAGE = arg('page') ? resolve(arg('page')) : join(ROOT, 'web', 'trade_craft_map.html');
const WEB = dirname(PAGE);

let passed = 0;
const failures = [];
function ok(text, cond) {
  if (cond) { passed += 1; console.log(`  ok  ${text}`); }
  else failures.push(text);
}
function fail(text) { ok(text, false); }

const html = readFileSync(PAGE, 'utf8');
const reg = (rel) => JSON.parse(readFileSync(join(ROOT, rel), 'utf8'));
const canon = (v) => JSON.stringify(v);

// ------------------------------------------------------------ the payload
const dataM = /<script id="data" type="application\/json">([\s\S]*?)<\/script>/.exec(html);
ok('[shipped] the page carries exactly one <script id="data" type="application/json"> block',
  dataM !== null && (html.match(/<script id="data"/g) || []).length === 1);
const D = dataM ? JSON.parse(dataM[1]) : null;
if (!D) { fail('[shipped] the data block parses as JSON'); }
const SOURCES = D ? D.sources : {};
const R = D ? D.reg : {};

const REGS = {
  halls: 'pack/registry/halls.json',
  lessons: 'lessons/registry/lessons.json',
  sims: 'sims/registry/sims.json',
  schools: 'schools/registry/schools.json',
  completion: 'completion/registry/completion.json',
};
ok('[shipped] the payload names the five registries it carries, by path',
  D && canon(SOURCES) === canon(REGS));
for (const [k, rel] of Object.entries(REGS)) {
  const disk = reg(rel);
  ok(`[shipped] payload reg.${k} is ${rel} verbatim (parsed and re-serialised, key order included)`,
    D && canon(R[k]) === canon(disk));
}

// ---------------------------------------------------------- the renderer
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
const js = scripts.join('\n')
  .replace(/\/\*[\s\S]*?\*\//g, ' ')
  .replace(/^\s*\/\/.*$/gm, ' ');
ok('[shipped] the renderer parses the data block once: const DATA = JSON.parse(document.getElementById(\'data\').textContent)',
  /const DATA = JSON\.parse\(document\.getElementById\('data'\)\.textContent\)/.test(js)
  && /const REG = DATA\.reg;/.test(js));

const STRUCT = {
  lessons: /lessons: \{ src: DATA\.sources\.lessons \+ '#lessons'[\s\S]*?of: \(h\) => Object\.values\(REG\.lessons\.lessons\)\.filter\(\(l\) => l\.hall === h\.slug\)\.map\(\(l\) => l\.id\),\s*published: \(\) => REG\.lessons\.counts\.halls_covered/,
  seats: /seats: \{ src: DATA\.sources\.sims \+ '#hall_bindings'[\s\S]*?of: \(h\) => hasOwn\(REG\.sims\.hall_bindings, h\.slug\) \? REG\.sims\.hall_bindings\[h\.slug\]\.map\(\(b\) => b\.sim\) : \[\],\s*published: \(\) => REG\.sims\.coverage\.halls\.with_a_seat/,
  units: /units: \{ src: DATA\.sources\.schools \+ '#units'[\s\S]*?of: \(h\) => REG\.schools\.units\.filter\(\(u\) => u\.hall === h\.slug\)\.map\(\(u\) => u\.class_drill\),\s*published: \(\) => REG\.schools\.units\.length/,
  signoff: /signoff: \{ src: DATA\.signoff\.rule[\s\S]*?of: \(h\) => DATA\.signoff\.halls\[h\.slug\] === true \? \[DATA\.signoff\.claiming\] : \[\],\s*published: \(\) => DATA\.signoff\.signed/,
  completable: /completable: \{ src: DATA\.sources\.completion \+ '#lessons\.completable'[\s\S]*?of: \(h\) => Object\.entries\(REG\.completion\.lessons\)\.filter\(\(\[, c\]\) => c\.hall === h\.slug && c\.completable === true\)\.map\(\(\[id\]\) => id\),\s*published: \(\) => REG\.completion\.counts\.lessons_completable/,
  blocked: /blocked: \{ src: DATA\.sources\.completion \+ '#lessons\.not_completable_why'[\s\S]*?of: \(h\) => Object\.entries\(REG\.completion\.lessons\)\.filter\(\(\[, c\]\) => c\.hall === h\.slug && c\.completable === false\)\.map\(\(\[id\]\) => id\),\s*published: \(\) => REG\.completion\.counts\.lessons_not_completable/,
};
for (const [k, re] of Object.entries(STRUCT)) {
  ok(`[shipped] LAYERS.${k} derives its per-hall rows from the payload and names the published count it is held to`, re.test(js));
}
ok('[shipped] the legend count is computed per layer from the rows and thrown on disagreement with the published count',
  /const rows = DATA\.halls\.map\(\(h\) => L\.of\(h\)\.length\);/.test(js)
  && /const halls = rows\.filter\(\(n\) => n > 0\)\.length, items = rows\.reduce\(\(a, b\) => a \+ b, 0\);/.test(js)
  && /if \(got !== L\.published\(\)\) throw new Error\(/.test(js)
  && /data-count="\$\{k\}">\$\{F\(COUNTS\[k\]\.halls\)\} \$\{I18N\.of\} \$\{F\(DATA\.halls\.length\)\}/.test(js));
ok('[shipped] every hall pad carries one data-<layer> count per layer, written from LAYERS at render',
  /const marks = Object\.entries\(LAYERS\)\.map\(\(\[k, L\]\) => `data-\$\{k\}="\$\{L\.of\(h\)\.length\}"`\)\.join\(' '\);/.test(js)
  && /<g class="hall" data-s="\$\{h\.slug\}" data-d="\$\{h\.district\}" \$\{marks\}/.test(js)
  && /<circle class="lm" data-layer="\$\{k\}"/.test(js));
ok('[shipped] the layer legend is toggleable (checkbox per layer feeds svg.map[data-off]) and each layer can focus the map',
  /<input type="checkbox" data-toggle="\$\{k\}" checked>/.test(js)
  && /dataset\.off = \[\.\.\.off\]\.join\(' '\);/.test(js)
  && /<button class="lfocus" data-focus="\$\{k\}"/.test(js)
  && /\(!focus \|\| g\.dataset\[focus\] !== '0'\)/.test(js)
  && /svg\.map\[data-off~="lessons"\] \.lm\[data-layer="lessons"\]/.test(html));

// ------------------------------------------------------- layer labels
// The six training layers' prose labels come from the locale catalog
// (map.layer.lessons .. map.layer.blocked), carried into the page as
// I18N.layerLabels and read at render beside the registry field path -
// never typed into the renderer, and never the bare key.
const en = JSON.parse(readFileSync(join(ROOT, 'i18n', 'locales', 'en.json'), 'utf8')).strings;
const LAYER_KEYS = ['lessons', 'seats', 'units', 'signoff', 'completable', 'blocked'];
const i18nM = /const I18N = (\{[\s\S]*?\});\nconst fillTokens/.exec(js);
let I18N = null;
try { I18N = i18nM ? JSON.parse(i18nM[1]) : null; } catch { I18N = null; }
ok('[shipped] I18N.layerLabels carries the six layer labels and each IS i18n/locales/en.json\'s map.layer.<k> verbatim',
  I18N !== null && I18N.layerLabels !== undefined
  && LAYER_KEYS.every((k) => typeof en[`map.layer.${k}`] === 'string' && en[`map.layer.${k}`].trim().length > 0
    && I18N.layerLabels[k] === en[`map.layer.${k}`])
  && canon(Object.keys(I18N.layerLabels).sort()) === canon([...LAYER_KEYS].sort()));
ok('[shipped] every LAYERS entry takes its label from I18N.layerLabels.<k>, and the legend, the focus button and the hall panel row print L.label beside L.src',
  LAYER_KEYS.every((k) => new RegExp(`\\b${k}: \\{ src: [^\\n]*label: I18N\\.layerLabels\\.${k},`).test(js))
  && /<span class="lname">\$\{L\.label\}<code title="\$\{L\.src\}">\$\{L\.src\}<\/code><\/span>/.test(js)
  && /<button class="lfocus" data-focus="\$\{k\}" aria-pressed="false">\$\{L\.label\}<\/button>/.test(js)
  && /<span class="hp-k">\$\{LAYERS\[k\]\.label\}<code>\$\{LAYERS\[k\]\.src\}<\/code><\/span>/.test(js)
  && /<span class="hp-k">\$\{I18N\.layerLabels\.signoff\}<code>\$\{DATA\.signoff\.rule\}<\/code><\/span>/.test(js));
{
  const jsNoI18n = i18nM ? js.replace(i18nM[1], ' ') : js;
  const literal = LAYER_KEYS.map((k) => en[`map.layer.${k}`]).filter((v) => typeof v === 'string'
    && (jsNoI18n.includes(`'${v}'`) || jsNoI18n.includes(`"${v}"`) || jsNoI18n.includes(`>${v}<`)));
  ok('[shipped] no English literal stands in for a layer label: none of the six catalog values is typed in the renderer outside I18N, and no layer is labelled by its bare key any more',
    I18N !== null && literal.length === 0 && !/aria-pressed="false">\$\{k\}<\/button>/.test(js));
  if (literal.length) console.error('  typed: ' + literal.join(' | '));
}
{
  const { readdirSync } = await import('node:fs');
  const locDir = join(ROOT, 'i18n', 'locales');
  const locales = readdirSync(locDir).filter((f) => f.endsWith('.json')).map((f) => f.replace(/\.json$/, ''));
  const gaps = [];
  for (const l of locales) {
    const strings = JSON.parse(readFileSync(join(locDir, `${l}.json`), 'utf8')).strings;
    for (const k of LAYER_KEYS) if (typeof strings[`map.layer.${k}`] !== 'string' || !strings[`map.layer.${k}`].trim()) gaps.push(`${l}: map.layer.${k}`);
  }
  ok(`[registry] every one of the ${locales.length} locale catalogs carries all six map.layer.<k> labels, non-empty`,
    locales.length === 8 && gaps.length === 0);
  if (gaps.length) console.error('  missing: ' + gaps.join(', '));
}

// ---------------------------------------------------- per-hall recompute
const halls = reg(REGS.halls).halls;
const L = reg(REGS.lessons), S = reg(REGS.sims), H = reg(REGS.schools), C = reg(REGS.completion);
const perHall = {};
for (const h of halls) {
  perHall[h.slug] = {
    lessons: Object.values(L.lessons).filter((l) => l.hall === h.slug).map((l) => l.id),
    seats: Object.prototype.hasOwnProperty.call(S.hall_bindings, h.slug) ? S.hall_bindings[h.slug].map((b) => b.sim) : [],
    units: H.units.filter((u) => u.hall === h.slug).map((u) => u.class_drill),
    completable: Object.entries(C.lessons).filter(([, c]) => c.hall === h.slug && c.completable === true).map(([id]) => id),
    blocked: Object.entries(C.lessons).filter(([, c]) => c.hall === h.slug && c.completable === false).map(([id]) => id),
  };
}
const count = (k, by) => {
  const rows = halls.map((h) => perHall[h.slug][k].length);
  return by === 'items' ? rows.reduce((a, b) => a + b, 0) : rows.filter((n) => n > 0).length;
};
ok(`[registry] lessons: ${count('lessons')} of ${halls.length} halls hold a lesson, the count lessons.json#counts.halls_covered publishes`,
  count('lessons') === L.counts.halls_covered && L.counts.halls_total === halls.length);
ok(`[registry] seats: ${count('seats')} of ${halls.length} halls bind a simulator seat, the count sims.json#coverage.halls.with_a_seat publishes`,
  count('seats') === S.coverage.halls.with_a_seat && S.coverage.halls.total === halls.length);
ok(`[registry] units: ${count('units')} halls carry a flipped-classroom unit, one per unit in schools.json#units`,
  count('units') === H.units.length);
ok(`[registry] completability: ${count('completable', 'items')} completable and ${count('blocked', 'items')} not, the counts completion.json#counts publishes`,
  count('completable', 'items') === C.counts.lessons_completable
  && count('blocked', 'items') === C.counts.lessons_not_completable
  && count('completable', 'items') + count('blocked', 'items') === Object.keys(C.lessons).length);
// The same recompute over the PAYLOAD: what the renderer will show equals what the registry says.
const perHallPage = {};
if (D) {
  for (const h of D.halls) {
    perHallPage[h.slug] = {
      lessons: Object.values(R.lessons.lessons).filter((l) => l.hall === h.slug).map((l) => l.id),
      seats: Object.prototype.hasOwnProperty.call(R.sims.hall_bindings, h.slug) ? R.sims.hall_bindings[h.slug].map((b) => b.sim) : [],
      units: R.schools.units.filter((u) => u.hall === h.slug).map((u) => u.class_drill),
      completable: Object.entries(R.completion.lessons).filter(([, c]) => c.hall === h.slug && c.completable === true).map(([id]) => id),
      blocked: Object.entries(R.completion.lessons).filter(([, c]) => c.hall === h.slug && c.completable === false).map(([id]) => id),
    };
  }
}
const bySlug = (o) => Object.fromEntries(Object.keys(o).sort().map((k) => [k, o[k]]));
ok('[shipped] the per-hall rows the renderer derives from the payload equal the rows recomputed from the registries, hall by hall',
  D && D.halls.length === halls.length && canon(bySlug(perHallPage)) === canon(bySlug(perHall)));
ok('[shipped] the geometry roster and the registry roster name the same halls, each exactly once',
  D && canon(D.halls.map((h) => h.slug).sort()) === canon(R.halls.halls.map((h) => h.slug).sort())
  && halls.length === new Set(halls.map((h) => h.slug)).size);

// Lessons per hall: steps count and the ladder prerequisite, as the panel shows them.
const edges = L.ladder.edges;
const preOf = (id) => edges.filter((e) => e.lesson === id).map((e) => ({ needs: e.needs, because: e.because }));
ok('[registry] every ladder edge names two lessons and completion.json#lessons[].needs mirrors the edge list',
  edges.every((e) => e.lesson in L.lessons && e.needs in L.lessons && typeof e.because === 'string')
  && Object.keys(L.lessons).every((id) => canon(preOf(id).map((p) => p.needs).sort()) === canon([...C.lessons[id].needs].sort()))
  && C.counts.ladder_edges === edges.length && L.counts.prerequisite_edges === edges.length);
ok('[shipped] the prerequisites the panel will show (payload ladder.edges by lesson) equal the registry edges, lesson by lesson',
  D && Object.keys(L.lessons).every((id) =>
    canon(R.lessons.ladder.edges.filter((e) => e.lesson === id).map((e) => ({ needs: e.needs, because: e.because }))) === canon(preOf(id))));
ok('[shipped] the steps count the panel shows is the length of each lesson\'s steps in the payload, and completion.json agrees per lesson',
  D && Object.keys(L.lessons).every((id) => R.lessons.lessons[id] !== undefined && R.lessons.lessons[id].steps.length === L.lessons[id].steps.length
    && C.lessons[id].steps === L.lessons[id].steps.length)
  && /<span class="lc">steps: \$\{L\.steps\.length\}/.test(js)
  && /const pre = REG\.lessons\.ladder\.edges\.filter\(\(e\) => e\.lesson === id\);/.test(js)
  && /<em data-needs="\$\{e\.needs\}">needs: \$\{e\.needs\} \(\$\{esc\(e\.because\)\}\)<\/em>/.test(js)
  && /C\.completable === true \? `<em class="yes">completable: true<\/em>`\s*: `<em class="no">not_completable_why: \$\{esc\(C\.not_completable_why\)\}<\/em>`/.test(js));

// ------------------------------------------------------------- sign-off
const signoffMod = await import(pathToFileURL(join(ROOT, 'pack', 'hall_signoff.mjs')).href);
const signedDisk = Object.fromEntries(halls.map((h) => [h.slug, signoffMod.claimsHallSignoff(h.content_status)]));
const nSigned = Object.values(signedDisk).filter(Boolean).length;
ok(`[registry] pack/hall_signoff.mjs signs off ${nSigned} of ${halls.length} halls today`,
  nSigned === 0 && Object.keys(signedDisk).length === halls.length);
ok('[shipped] the sign-off payload is pack/hall_signoff.mjs applied to every hall, and says 0 of 111 in the registry\'s own numbers',
  D && canon(D.signoff.halls) === canon(signedDisk)
  && D.signoff.signed === nSigned && D.signoff.of === halls.length
  && D.signoff.rule === 'pack/hall_signoff.mjs'
  && canon(D.signoff.statuses) === canon(signoffMod.HALL_CONTENT_STATUSES)
  && signoffMod.claimsHallSignoff(D.signoff.claiming)
  && D.signoff.caveat === reg('pack/manifest.json').honesty.content);
ok('[shipped] the sign-off layer cannot show a signed hall while the pack signs none: its rows come only from DATA.signoff.halls[slug] === true',
  D && Object.values(D.signoff.halls).every((v) => v === false)
  && STRUCT.signoff.test(js)
  && /if \(COUNTS\.signoff\.halls !== Object\.values\(DATA\.signoff\.halls\)\.filter\(\(v\) => v === true\)\.length\)\s*throw new Error/.test(js)
  && /data-panel="signoff" data-signed="\$\{signed\}"/.test(js)
  && /const signed = DATA\.signoff\.halls\[h\.slug\] === true;/.test(js)
  && !/data-signed="true"/.test(html));

// -------------------------------------------------------- typed figures
const FIGS = [
  L.counts.halls_covered, S.coverage.halls.with_a_seat, C.counts.lessons_completable,
  C.counts.lessons_not_completable, halls.length,
];
const legendM = /<div class="layers" id="layers">([\s\S]*?)<\/div>/.exec(html);
const layersJs = js.slice(js.indexOf('const LAYERS = {'), js.indexOf("const dlist = document.getElementById('dlist');"));
const panelJs = js.slice(js.indexOf('function hallPanel(h)'), js.indexOf('function apply()'));
const typed = (text) => FIGS.filter((n) => new RegExp(`(^|[^\\w.])${n}(?![\\w.])`).test(text));
ok(`[shipped] no legend figure is typed: ${FIGS.join(', ')} appear nowhere in the legend markup, the layer script or the panel script`,
  legendM !== null && typed(legendM[1]).length === 0 && typed(layersJs).length === 0 && typed(panelJs).length === 0
  && layersJs.length > 0 && panelJs.length > 0);

// ---------------------------------------------------------------- links
const hrefs = new Set();
for (const m of html.matchAll(/href="([^"]*)"/g)) hrefs.add(m[1]);
for (const m of js.matchAll(/href="([^"]*)"/g)) hrefs.add(m[1]);
if (D) for (const f of Object.values(D.links)) hrefs.add(f);
const unresolved = [];
for (const raw of hrefs) {
  let h = raw.replace(/\$\{DATA\.links(?:\.(\w+)|\['(\w+)'\])\}/g, (m, a, b) => (D ? D.links[a || b] : ''))
    .replace(/\$\{[^}]*\}/g, '');
  if (h === '' || h.startsWith('#') || h.startsWith('data:')) continue;
  h = h.split('?')[0].split('#')[0];
  if (h === '' || !existsSync(join(WEB, h))) unresolved.push(raw);
}
ok(`[shipped] every href on the page and in its renderer resolves to a file under web/ (${hrefs.size} distinct hrefs)`,
  unresolved.length === 0 && hrefs.size >= 10);
if (unresolved.length) console.error('  unresolved: ' + unresolved.join(', '));
ok('[shipped] the hall panel deep-links by the target pages\' own parameter shapes: 3D/ladder/progress ?hall=<slug>, lessons #lesson-<id>',
  D && canon(Object.keys(D.links).sort()) === canon(['3d', 'ladder', 'lessons', 'progress'])
  && /href="\$\{DATA\.links\['3d'\]\}\?hall=\$\{h\.slug\}"/.test(js)
  && /href="\$\{DATA\.links\.ladder\}\?hall=\$\{h\.slug\}"/.test(js)
  && /href="\$\{DATA\.links\.progress\}\?hall=\$\{h\.slug\}"/.test(js)
  && /href="\$\{DATA\.links\.lessons\}#lesson-\$\{id\}"/.test(js));
const lessonsPage = existsSync(join(WEB, 'trade_craft_lessons.html')) ? readFileSync(join(WEB, 'trade_craft_lessons.html'), 'utf8') : '';
ok('[shipped] every lesson anchor the panel can emit exists on the lessons page',
  Object.keys(L.lessons).every((id) => lessonsPage.includes(`id="lesson-${id}"`)));

// ------------------------------------------------------------ the panel
ok('[shipped] the hall panel structure exists: section[data-hall-panel] with a row per layer and the sign-off caveat',
  /<section class="hallpanel" data-hall-panel="\$\{h\.slug\}">/.test(js)
  && /\$\{row\('lessons', lessons\)\}/.test(js) && /\$\{row\('seats', seats\)\}/.test(js)
  && /\$\{row\('units', units\)\}/.test(js)
  && /<div data-lesson="\$\{id\}" data-completable="\$\{C\.completable\}">/.test(js)
  && /data-seat="\$\{sim\}">\$\{esc\(REG\.sims\.sims\[sim\]\.name\)\}/.test(js)
  && /data-unit="\$\{esc\(u\.class_drill\)\}"/.test(js)
  && /<p class="caveat">\$\{esc\(DATA\.signoff\.caveat\)\}<\/p>/.test(js)
  && /\$\{hallPanel\(h\)\}`;/.test(js)
  && /<div class="layers" id="layers">/.test(html));

// --------------------------------------------------- existing behaviour
ok('[shipped] the district map is intact: every hall pad, district band and the detail card still render from the same payload',
  D && D.halls.length === halls.length && D.districts.length > 0
  && /hallsG\.innerHTML = DATA\.halls\.map/.test(js) && /function renderDetail\(slug\)/.test(js)
  && (html.match(/<g class="band" data-d="/g) || []).length === D.districts.length
  && /<g id="halls"><\/g>/.test(html) && /<div class="detail" id="detail"><\/div>/.test(html));

// ---------------------------------------------------------------- report
// a hall click must SHOW what it opened: the panel lies far below the plan on most
// screens, so the handler that fills it must also bring it into view and focus it
{
  const js = html.replace(/\/\*[\s\S]*?\*\//g, '');
  const click = js.match(/hallsG\.addEventListener\('click'[\s\S]*?\}\);/);
  const key = js.match(/hallsG\.addEventListener\('keydown'[\s\S]*?\}\);/);
  ok('[shipped] a hall opened by click or by key is brought into view and focused: both handlers call showDetail(), which scrolls #detail to the top of the view and moves focus to it',
    !!click && !!key && /showDetail\(\)/.test(click[0]) && /showDetail\(\)/.test(key[0])
    && /function showDetail\(\)\s*\{[^}]*scrollIntoView\([^)]*\)[^}]*\.focus\(/.test(js)
    && /detailEl\.setAttribute\('tabindex', '-1'\)/.test(js));
  ok('[shipped] the page has exactly one <h1>, and it names the page',
    (html.match(/<h1[\s>]/g) || []).length === 1 && /<h1 class="vh">[^<]+<\/h1>/.test(html));
}
{
  // narrow screens: the page declares a device viewport, and no grid track
  // takes its min-content width (the 940px plan used to push the page sideways)
  ok('[shipped] the page declares a device-width viewport', /<meta name="viewport" content="width=device-width, initial-scale=1">/.test(html));
  ok('[shipped] the shell, plan, detail and hall-panel grids are minmax(0,1fr), so a 390px screen does not scroll sideways',
    /@media\(max-width:900px\)\{\.shell\{grid-template-columns:minmax\(0,1fr\)\}\}/.test(html)
    && /\.plan\{[^}]*grid-template-columns:minmax\(0,1fr\)/.test(html)
    && /\.detail\{[^}]*grid-template-columns:minmax\(0,1fr\)/.test(html)
    && /\.hallpanel \.hp-row\{[^}]*grid-template-columns:auto minmax\(0,1fr\)/.test(html));
  ok('[shipped] the layer focus buttons are at least 24px tall and wide (touch target)',
    /\.layers \.lfocus\{[^}]*min-height:24px;min-width:24px/.test(html));
  ok('[shipped] the hall heading is ink on the panel; the district colour is a swatch and a rule, never the text colour',
    !/style="color:\$\{h\.chip\}"/.test(html) && !/[";\s`']color:\$\{[^}]*h\.chip/.test(html) && /<h2 class="dname" style="border-inline-start-color:\$\{h\.chip\}">/.test(html)
    && /<i class="dsw" style="background:\$\{h\.chip\}"><\/i>/.test(html) && /\.detail h2\.dname\{color:var\(--ink\)/.test(html));
}

/* ---- simulated tasks (TASKS, wave 3): boards come from tasks/registry/tasks.json only ---- */
const TK = JSON.parse(readFileSync(new URL('../tasks/registry/tasks.json', import.meta.url), 'utf8'));
const tkRel = (h) => h === null ? null : (h.startsWith('web/') ? h.slice(4) : '../' + h);
const tkEsc = (h) => h.replace(/&/g, "&amp;");
const tkCards = (s) => s.split('<article class="tk-card" data-task="').slice(1).map((c) => {
  const id = c.slice(0, c.indexOf('"')); const m = c.match(/<a class="tk-go" href="([^"]+)"/);
  return [id, m && c.indexOf(m[0]) < c.indexOf('</article>') ? m[1] : null]; });
const tkWant = (ts) => ts.map((t) => [t.id, t.launch.href === null ? null : tkEsc(tkRel(t.launch.href))]);
const tkHall = (slug) => TK.tasks.filter((t) => t.place.kind === 'hall' && t.place.id === slug);
{
  const miss = [];
  for (const h of D.halls) {
    const b = D.taskBoards[h.slug], want = tkHall(h.slug);
    if (typeof b !== 'string') { miss.push(`${h.slug}: no board`); continue; }
    const got = [...b.matchAll(/data-task="([^"]+)"/g)].map((m) => m[1]);
    if (got.join() !== want.map((t) => t.id).join() || !b.includes(`data-total="${want.length}"`)) miss.push(`${h.slug}: ${got.join(',')}`);
    if (JSON.stringify(tkCards(b)) !== JSON.stringify(tkWant(want))) miss.push(`${h.slug}: card launch hrefs differ from the registry`);
    if (/trade_craft_lessons\.html#(?!lesson-)/.test(b)) miss.push(`${h.slug}: a lesson link misses #lesson-`);
  }
  ok('[tasks] every hall panel carries its Simulated tasks board, cards and totals exactly the registry\'s tasks at that hall, hrefs verbatim', miss.length === 0 && D.halls.length === 111);
  if (miss.length) console.error(miss.slice(0, 6).join('\n'));
  ok('[tasks] the hall panel renders the board and the chip filter is one delegated listener',
    html.includes('${DATA.taskBoards[h.slug]}') && /data-tk-filter/.test(html) && /closest\('\[data-tk-board\]'\)/.test(html));
}

// QA wave 4: a site style re-declares plate/panel, so status colours must follow it
// (--tc-ok/--tc-warn on body while a style is on, else the page's own values)
ok('[style] status colours (--good/--warn/--crit) follow the active site style via --tc-ok/--tc-warn on body, falling back to the page\'s own',
  html.includes(':root{--pg-good:var(--good);--pg-warn:var(--warn);--pg-crit:var(--crit)}')
  && html.includes('body{--good:var(--tc-ok,var(--pg-good));--warn:var(--tc-warn,var(--pg-warn));--crit:var(--tc-warn,var(--pg-crit))}')
  && html.includes('--tc-warn:') && html.includes('--tc-ok:'));
if (failures.length) {
  for (const f of failures) console.error(`FAIL ${f}`);
  console.error(`web/test_map: ${failures.length} of ${passed + failures.length} checks FAILED`);
  process.exit(1);
}
console.log(`web/test_map: ${passed} checks passed`);
