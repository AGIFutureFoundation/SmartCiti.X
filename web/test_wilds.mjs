/**
 * The wilds page, read as a file: structure, nav, controls, instancing,
 * honesty, the terrain core carried byte-for-byte, and the quest hooks.
 * The browser half (draw calls, frame time, page errors) is
 * web/eval_wilds.mjs; this half runs anywhere node does.
 *
 *   node web/test_wilds.mjs
 *   node web/test_wilds.mjs --root=/tmp/copy      (mutation runs)
 */
import { readFileSync, existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const HERE = dirname(fileURLToPath(import.meta.url));
const hit = process.argv.slice(2).find((a) => a.startsWith('--root='));
const ROOT = resolve(hit ? hit.slice(7) : join(HERE, '..'));
let n = 0, bad = 0;
const ok = (m, c, evidence = []) => {
  if (c) { n++; console.log('  ok  ' + m); return; }
  bad++; console.log('FAIL  ' + m);
  for (const e of evidence.slice(0, 6)) console.log('      ' + e);
};
const canon = (v) => (v && typeof v === 'object' && !Array.isArray(v))
  ? Object.fromEntries(Object.keys(v).sort().map((k) => [k, canon(v[k])]))
  : (Array.isArray(v) ? v.map(canon) : v);
const same = (a, b) => JSON.stringify(canon(a)) === JSON.stringify(canon(b));
const read = (rel) => readFileSync(join(ROOT, rel), 'utf8');
const html = read('web/trade_craft_wilds.html');
const reg = JSON.parse(read('wilds/registry/wilds.json'));
const coreSrc = read('wilds/core.mjs');
const builder = read('web/build_wilds.py');
const halls = new Set(JSON.parse(read('pack/registry/halls.json')).halls.map((h) => h.slug));
const lessons = JSON.parse(read('lessons/registry/lessons.json')).lessons;
const main = (html.match(/<script type="module" id="wilds-main">([\s\S]*?)<\/script>/) || [, ''])[1];

/* ------------------------------------------------------------- build -- */
const chk = spawnSync('python3', [join(ROOT, 'web/build_wilds.py'), '--check'], { cwd: ROOT, encoding: 'utf8' });
ok('[build] the page is what web/build_wilds.py writes (not stale, not hand-edited)', chk.status === 0, [chk.stdout, chk.stderr]);

/* --------------------------------------------------------- structure -- */
ok('[page] exactly one <h1>', (html.match(/<h1[\s>]/g) || []).length === 1);
ok('[page] lang, viewport and title', /<html lang="en">/.test(html) && /name="viewport"/.test(html) && /<title>[^<]+<\/title>/.test(html));
const sitenav = read('web/sitenav.py');
const wired = sitenav.includes("'web/trade_craft_wilds.html'");
ok('[nav] the site nav is carried and marks this page current',
  /<nav class="sitenav" data-sitenav/.test(html) && /href="trade_craft_wilds\.html" aria-current="page"/.test(html));
ok('[nav] web/sitenav.py lists this page (so every other page links here)', wired);
ok('[page] the registry is embedded verbatim',
  (() => { const m = html.match(/<script type="application\/json" id="wilds-registry">([\s\S]*?)<\/script>/); return m && same(JSON.parse(m[1].replace(/<\\\//g, '</')), reg); })());
const B = '/* WILDS_CORE:BEGIN */', E = '/* WILDS_CORE:END */';
const core = coreSrc.slice(coreSrc.indexOf(B), coreSrc.indexOf(E) + E.length);
ok('[page] the terrain core is carried byte-for-byte from wilds/core.mjs', main.includes(core) && main.split(B).length === 2);
const switchIds = [...html.matchAll(/<div id="switch"[^>]*>([\s\S]*?)<\/div>/g)].flatMap((m) => [...m[1].matchAll(/data-world="([^"]+)"/g)].map((x) => x[1]));
ok('[page] the world switcher offers every registry world, in order', JSON.stringify(switchIds) === JSON.stringify(reg.worlds.map((w) => w.id)), switchIds);
ok('[page] intro figures are the registry counts',
  [['worlds', reg.counts.worlds], ['area', reg.counts.area_km2], ['sites', reg.counts.sites], ['halls', reg.counts.halls_linked], ['lessons', reg.counts.lessons_linked]]
    .every(([k, v]) => { const m = html.match(new RegExp(`<b data-fig="${k}">([0-9.]+)</b>`)); return m !== null && Number(m[1]) === v; }));

/* ---------------------------------------------------------- three.js -- */
const im = html.match(/<script type="importmap">([\s\S]*?)<\/script>/);
const imports = im ? JSON.parse(im[1]).imports : {};
ok('[three] the importmap points at the vendored three and addons, which exist',
  imports.three === './vendor/three.module.min.js' && existsSync(join(ROOT, 'web/vendor/three.module.min.js'))
  && existsSync(join(ROOT, 'web/vendor/addons/controls/OrbitControls.js')) && existsSync(join(ROOT, 'web/vendor/addons/utils/BufferGeometryUtils.js')));
ok('[three] no script or stylesheet is fetched from another origin', !/<(script|link)[^>]+(src|href)="https?:/.test(html));
ok('[draw calls] vegetation is instanced: one InstancedMesh per species, refilled in place',
  /new THREE\.InstancedMesh\(/.test(main) && /setMatrixAt\(/.test(main) && /for \(const \[k, g\] of Object\.entries\(SPECIES\)\)/.test(main));
ok('[draw calls] props, caches and species geometry are merged (mergeGeometries)', (main.match(/mergeGeometries\(/g) || []).length >= 3);
ok('[draw calls] terrain streams in chunks with LOD rings and skirts', /const RING_SEGS = \[/.test(main) && /SKIRT/.test(main) && /function updateChunks/.test(main));
ok('[view] far horizon: a coarse whole-world mesh shown in walk mode, discarded inside the streamed chunk square, sunk below the chunks',
  /horizonMesh = worldMesh\(HORIZON_SEGS, matHorizon, HORIZON_SINK_M\)/.test(main) && /horizonMesh\.visible = walkOn/.test(main)
  && /uBox\.w\) discard;/.test(main) && /function updateChunks\(all\) \{\s*setHorizonBox\(\);/.test(main)
  && /HORIZON_SINK_M = [1-9]/.test(main));
ok('[hooks] a camera hook for filming (window.__wilds.cam) that refuses malformed input',
  /cam\(arg\) \{/.test(main) && /throw new Error\('wilds cam: expected/.test(main));
ok('[view] distance fog and an overview camera', /new THREE\.Fog\(/.test(main) && /new OrbitControls\(/.test(main) && /function buildOverview/.test(main));
ok('[view] water where the world has it, and a minimap', /function buildWater/.test(main) && /id="minimap"/.test(html) && /function drawMinimap/.test(main));

ok('[draw calls] tree billboards past VEG_R: ONE InstancedMesh for every species (w4: merged cards, per-instance bbKind, the other card collapsed in the vertex shader), never inside VEG_R, hidden in the overview',
  /const BB_R = \d+, BB_CELL = \d+;/.test(main) && (main.match(/new THREE\.InstancedMesh\(bbGeo, matBB, BB_TOTAL\)/g) || []).length === 1
  && !/Object\.entries\(BB_SHAPES\)\) \{\s*const m = new THREE\.InstancedMesh/.test(main)
  && /transformed \*= step\(abs\(bbPart - bbKind\), 0\.5\);/.test(main) && /bbKind\.setX\(at \+ n, kind\)/.test(main)
  && /if \(d2 <= VEG_R \* VEG_R \|\| d2 > BB_R \* BB_R/.test(main) && /refillBillboards\(\);\s*\}/.test(main)
  && /bbMesh\.visible = walkOn;/.test(main) && Number((main.match(/const BB_R = (\d+)/) || [, 0])[1]) > Number((main.match(/const VEG_R = (\d+)/) || [, 1e9])[1]));
ok('[hooks] a flyover path for filming: DERIVED keyframes (trailhead + sites in trail order), flyover(t) refuses t outside [0,1], a Flyover button',
  /flyoverPath\(\) \{/.test(main) && /flyover\(t\) \{/.test(main) && /const order = \['trailhead', \.\.\.W\.trails\.map\(\(l\) => l\.to\)\]/.test(main)
  && /throw new Error\('wilds flyover: t must be in \[0, 1\]/.test(main) && /<button type="button" class="tc-btn tc-btn-ghost" id="fly" aria-pressed="false">/.test(html)
  && /_fe\.y = Math\.max\(_fe\.y, T\.height\(_fe\.x, _fe\.z\) \+ FLY_CLEAR_M\)/.test(main));
ok('[hooks] deep links: #<world> and #<world>/<site> open the world (and stand at the site), also on hashchange',
  /async function fromHash\(\)/.test(main) && /addEventListener\('hashchange'/.test(main) && /if \(sid\) goSite\(sid\);/.test(main));

/* ---------------------------------------------------------- controls -- */
const keysNeeded = ['KeyW', 'KeyA', 'KeyS', 'KeyD', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ShiftLeft', 'KeyO'];
ok('[controls] keyboard: WASD, arrows, Shift run, O overview', keysNeeded.every((k) => main.includes(k)), keysNeeded.filter((k) => !main.includes(k)));
ok('[controls] touch: an on-screen stick and pointer-drag look', /id="stick"/.test(html) && /stick\.addEventListener\('pointerdown'/.test(main) && /canvas\.addEventListener\('pointermove'/.test(main) && /touch-action:none/.test(html));
ok('[controls] the canvas is focusable and labelled', /<canvas id="view" tabindex="0" aria-label="[^"]+"/.test(html));

/* ------------------------------------------------------------- sites -- */
const siteMiss = [];
for (const w of reg.worlds) for (const s of w.sites) {
  const card = (html.match(new RegExp(`<article class="site" id="site-${s.id}"[\\s\\S]*?</article>`)) || [''])[0];
  if (!card) { siteMiss.push(`${s.id}: no card`); continue; }
  for (const h of s.halls) if (!card.includes(`href="trade_craft_3d.html?hall=${h.id}"`) || !halls.has(h.id)) siteMiss.push(`${s.id}: hall ${h.id}`);
  for (const l of s.lessons) if (!card.includes(`href="trade_craft_lessons.html#lesson-${l.id}"`) || !lessons[l.id]) siteMiss.push(`${s.id}: lesson ${l.id}`);
  if (!card.includes('SCHEMATIC')) siteMiss.push(`${s.id}: no SCHEMATIC label`);
}
ok('[sites] every site has a card linking each of its halls (3D hall) and lessons, labelled SCHEMATIC', siteMiss.length === 0, siteMiss);

/* ----------------------------------------------------------- honesty -- */
ok('[honesty] the footer says authored landscape, not a survey', /<footer data-honesty>Authored landscape, not a survey/.test(html));
ok('[honesty] play is said plainly once: never enters a completion record, never certifies',
  /never enter a completion record and never certify anything/.test(html));
ok('[honesty] every world card says inspiration only, not real elevation',
  reg.worlds.every((w) => new RegExp(`data-world-card="${w.id}"[\\s\\S]*?inspiration only; the terrain is AUTHORED, not real elevation`).test(html)));
ok('[honesty] the altitude readout is labelled authored', /\(authored height\)/.test(main));
ok('[rules] no model identifiers in the page or builder', !/\b(gpt-|claude-|opus|sonnet|haiku)\b/i.test(html + builder));
ok('[rules] fail closed: no ?? defaults in the page script, no .get(k, default) in the builders',
  !/\?\?/.test(main) && !/\.get\([^)]*,[^)]*\)/.test(builder + read('wilds/build.py')));

/* ------------------------------------------------------------- theme -- */
ok('[theme] the canvas theme layer (MEDIA pagehero.theme("canvas")) is adopted: body class, its CSS in the head, panel/buttons/badges use it, and NO hero band over the world',
  /<body class="tc-theme-canvas">/.test(html) && /<style data-tc-theme="canvas">body\.tc-theme-canvas\{/.test(html)
  && /<aside id="panel" class="tc-panel"/.test(html) && /class="tc-btn tc-btn-ghost" id="mode"/.test(html) && /class="go tc-btn tc-btn-primary"/.test(html)
  && !/data-ph[\s>=]|class="ph"/.test(html) && /from pagehero import theme/.test(builder) && /theme\('canvas'\)/.test(builder));

{
  const own = (html.match(/<style>\s*(\/\* UI colours come ONLY[\s\S]*?)<\/style>/) || [, ''])[1];
  const hexes = own.match(/#[0-9A-Fa-f]{3,8}\b|rgba?\(/g) || [];
  const miniHex = (main.slice(main.indexOf('function drawMinimap'), main.indexOf('function drawMinimap') + 1400).match(/'#[0-9A-Fa-f]{3,8}'/g) || []);
  ok('[theme] the page\'s UI colours come only from the theme tokens (--tc-*): no hex or rgba in its own style, minimap marks read the tokens (Style switcher applies)',
    own.length > 0 && hexes.length === 0 && miniHex.length === 0 && /--plate:var\(--tc-plate\)/.test(own) && /tok\('--tc-amber'\)/.test(main),
    [...hexes, ...miniHex]);
}

/* ------------------------------------------------------------- globe -- */
ok('[geo] every world card states its geolocation label verbatim from the registry (not on the globe, AUTHORED)',
  reg.worlds.every((w) => w.geolocation.on_globe === false
    && new RegExp(`data-world-card="${w.id}"[\\s\\S]*?<p class="geo" data-geolocation="${w.id}"><span class="prov tc-badge tc-badge-muted">AUTHORED</span> ${w.geolocation.label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}</p>`).test(html)),
  reg.worlds.map((w) => w.geolocation.label));

/* -------------------------------------------------------------- i18n -- */
const en = JSON.parse(read('i18n/locales/en.json')).strings;
const usedKeys = [...new Set([...builder.matchAll(/T(?:RAW|S|A)?\("(wilds\.[a-z_.]+)"\)|TRAW\('wilds\.' \+ k\)/g)].map((m) => m[1]).filter(Boolean))];
const locs = ['es', 'fr', 'de', 'pt', 'zh', 'hi', 'ar'].map((l) => JSON.parse(read(`i18n/locales/${l}.json`)).strings);
const i18nBad = [];
for (const k of usedKeys) {
  if (typeof en[k] !== 'string' || !en[k].trim()) i18nBad.push(`${k}: not in en`);
  for (const [i, L] of locs.entries()) if (typeof L[k] !== 'string' || !L[k].trim()) i18nBad.push(`${k}: missing in locale #${i}`);
}
const esc = (t) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
for (const k of ['wilds.lede', 'wilds.help', 'wilds.site.go', 'wilds.site.halls', 'wilds.h.quests', 'wilds.flyover', 'wilds.legend']) if (!html.includes(esc(en[k]))) i18nBad.push(`${k}: English text not on the page`);
for (const lit of ['>Go to this site<', '>Union halls<', 'Side quest: ', '>Treasure riddles<', "'Fast travel'", '>Overview<']) if (builder.includes(lit)) i18nBad.push(`builder still hard-codes ${lit}`);
ok(`[i18n] page chrome comes from ${usedKeys.length} wilds.* keys present in all 8 locales; no hard-coded chrome left in the builder`,
  usedKeys.length >= 20 && i18nBad.length === 0, i18nBad);

/* ------------------------------------------------ run-time locale (w4) -- */
// the chrome renders in the reader's locale at run time: ?lang=<code> first
// (as the campus page does), then navigator.languages, then en; the catalogue
// embedded in the page carries every key the page marks, for all 8 locales,
// and a missing key throws by name rather than falling back to English
const cat = JSON.parse((html.match(/<script type="application\/json" id="wilds-i18n">([\s\S]*?)<\/script>/) || [, '{}'])[1]);
const localeFiles = ['en', 'es', 'fr', 'de', 'pt', 'zh', 'hi', 'ar'].map((l) => JSON.parse(read(`i18n/locales/${l}.json`)));
const marked = [...new Set([...html.matchAll(/data-i18n(?:-aria)?="(wilds\.[a-z_.]+)"/g)].map((m) => m[1]))];
const jsKeys = Object.keys(JSON.parse((html.match(/<script type="application\/json" id="wilds-labels">([\s\S]*?)<\/script>/) || [, '{}'])[1])).map((k) => 'wilds.' + k);
const rtBad = [];
for (const f of localeFiles) {
  const c = cat[f.locale];
  if (!c) { rtBad.push(`${f.locale}: not in the page catalogue`); continue; }
  if (c.dir !== f.dir) rtBad.push(`${f.locale}: dir ${c.dir} != catalog ${f.dir}`);
  for (const k of [...marked, ...jsKeys]) if (c.strings[k] !== f.strings[k]) rtBad.push(`${f.locale}: ${k} differs from i18n/locales or missing`);
}
if (Object.keys(cat).length !== 8) rtBad.push(`catalogue has ${Object.keys(cat).length} locales`);
if (marked.length < 25) rtBad.push(`only ${marked.length} marked chrome keys`);
ok(`[i18n-rt] the page embeds a run-time catalogue: ${Object.keys(cat).length} locales x ${marked.length + jsKeys.length} chrome keys (marked + JS), each equal to i18n/locales and carrying the locale's own dir`,
  rtBad.length === 0, rtBad);
const pick = main.slice(main.indexOf('function pickLocale()'), main.indexOf('const LOC = pickLocale();'));
ok('[i18n-rt] the locale is picked from ?lang= (when the catalogue has it), then navigator.languages, then en; renderChrome sets <html lang> and dir from the catalogue and re-renders every [data-i18n] and [data-i18n-aria]',
  /searchParams|new URLSearchParams\(location\.search\)\.get\('lang'\)/.test(pick) && /Object\.hasOwn\(I18N, q\)/.test(pick)
  && /navigator\.languages/.test(pick) && /return 'en';\s*\}$/.test(pick.trim() + '}'.slice(1))
  && /document\.documentElement\.lang = LOC;/.test(main) && /document\.documentElement\.dir = I18N\[LOC\]\.dir;/.test(main)
  && /querySelectorAll\('\[data-i18n\]'\)/.test(main) && /querySelectorAll\('\[data-i18n-aria\]'\)/.test(main)
  && main.indexOf('renderChrome();') > -1 && main.indexOf('renderChrome();') < main.indexOf('await fromHash()'));
// behaviour, not just text: pickLocale() run with a stand-in location/navigator
const pickRun = (search, languages, language) => {
  try { return new Function('I18N', 'location', 'navigator', pick + '\nreturn pickLocale();')(cat, { search }, { languages, language }); }
  catch (e) { return 'threw ' + e.message; }
};
const pickCases = [['?lang=ar', ['en-US'], 'en-US', 'ar'], ['?lang=xx', ['fr-CA'], 'fr-CA', 'fr'], ['', ['ja', 'de-DE'], 'ja', 'de'],
  ['', [], 'pt-BR', 'pt'], ['', ['ja'], 'ja', 'en'], ['?lang=toString', ['ko'], 'ko', 'en']];
const pickBad = pickCases.map(([q, ls, l, want]) => [q, ls, pickRun(q, ls, l), want]).filter(([, , got, want]) => got !== want).map((r) => JSON.stringify(r));
ok('[i18n-rt] pickLocale() behaves: ?lang=ar -> ar; an unknown ?lang falls through to navigator.languages (fr-CA -> fr, [ja, de-DE] -> de, navigator.language pt-BR -> pt); nothing known -> en; a prototype key is not a locale',
  pickBad.length === 0, pickBad);
const trFn = main.slice(main.indexOf('function tr(k)'), main.indexOf('function renderChrome()'));
ok('[i18n-rt] no silent English fallback: tr() throws by name on a missing key (no ?? / || default), JS labels come from tr(), and the build fails naming locale + key',
  /throw new Error\(`wilds i18n: locale \$\{LOC\} has no \$\{k\}`\)/.test(trFn) && !/\?\?|\|\|/.test(trFn)
  && /const L = Object\.fromEntries\(Object\.keys\(L_EN\)\.map\(\(k\) => \[k, tr\('wilds\.' \+ k\)\]\)\);/.test(main)
  && /raise SystemExit\(f'build_wilds: locale \{_c\["locale"\]\} has no wilds chrome key \{_k!r\}'\)/.test(builder));
// RTL: the page's own CSS mirrors under dir="rtl" - no physical-direction
// declaration outside the three rules positioned by projection/centring
const css = (html.match(/<style>\n\/\* UI colours[\s\S]*?<\/style>/) || [''])[0];
const ALLOWED_PHYS = ['.lbl{', '#stick i{', '#toast{'];
const physBad = css.split('\n').filter((l) => /(margin|padding|border)-(left|right)\s*:|text-align\s*:\s*(left|right)|(^|[{;])\s*(left|right)\s*:|float\s*:\s*(left|right)/.test(l)
  && !ALLOWED_PHYS.some((a) => l.startsWith(a)));
ok('[rtl] the wilds CSS uses logical properties (inset-inline-*, padding-inline-*, float:inline-end); physical left/right only in the projection-placed label, the centred stick knob and the centred toast',
  css.length > 1000 && physBad.length === 0 && /inset-inline-start:10px/.test(css) && /inset-inline-end:10px/.test(css), physBad);

// deep links (w4): a task's #world/site link must land ON the site's pad; the
// page teleports inside pad_m and the browser eval holds every site-walk link to it
const goS = main.slice(main.indexOf('function goSite(id)'), main.indexOf('async function fromHash()'));
const padK = +((goS.match(/teleport\(s\.x, s\.z \+ s\.pad_m \* ([\d.]+), 0\)/) || [, NaN])[1]);
const evSrc = read('web/eval_wilds.mjs');
ok(`[deep link] goSite lands ${padK} x pad_m from the site centre (inside the pad), and eval_wilds follows every wilds-site-walk task link and fails unless the eye is within pad_m with the panel open`,
  padK > 0 && padK < 1 && /t\.kind === 'wilds-site-walk'/.test(evSrc) && /if \(!\(d <= site\.pad_m\) \|\| !got\.open\) linkBad\.push/.test(evSrc)
  && /\?lang=ar/.test(evSrc) && /billboardMeshes !== 1/.test(evSrc));

// prose that has no catalogue key yet stays English on purpose and says so
// (lang="en" dir="ltr"), so an RTL reader gets it laid out and voiced as English
ok('[rtl] untranslated English prose (intro, play line, honesty list) is marked lang="en" dir="ltr" so it does not flip under dir="rtl"',
  /<p class="intro" lang="en" dir="ltr">Walk/.test(html) && /<p class="help" lang="en" dir="ltr">Caches, side quests/.test(html)
  && /<ul class="honesty" lang="en" dir="ltr">/.test(html));

/* ------------------------------------------------------------- tasks -- */
const tpath = join(ROOT, 'tasks/registry/tasks.json');
if (!existsSync(tpath) || !existsSync(join(ROOT, 'web/taskkit.py'))) {
  ok('[tasks] no task registry yet, and the page says simulated tasks are not wired (integration point)',
    /data-tasks-pending/.test(html) && !/data-task-launch=/.test(html));
} else {
  const treg = JSON.parse(readFileSync(tpath, 'utf8'));
  const siteWorld = new Map(reg.worlds.flatMap((w) => w.sites.map((s) => [s.id, w.id])));
  const taskBad = [];
  let shown = 0;
  for (const w of reg.worlds) for (const s of w.sites) {
    const card = (html.match(new RegExp(`<article class="site" id="site-${s.id}"[\\s\\S]*?</article>`)) || [''])[0];
    const want = treg.tasks.filter((t) => t.place.kind === 'wilds-site' && t.place.id === s.id);
    const own = (card.match(/<ul class="tasks">([\s\S]*?)<\/ul>/) || [, ''])[1];
    const have = [...own.matchAll(/<li data-task="([^"]+)"/g)].map((m) => m[1]);
    if (JSON.stringify(have) !== JSON.stringify(want.map((t) => t.id))) taskBad.push(`${s.id}: card lists ${JSON.stringify(have)}, registry ${JSON.stringify(want.map((t) => t.id))}`);
    for (const t of want) {
      shown++;
      if (t.place.world !== w.id) taskBad.push(`${t.id}: world ${t.place.world} != ${w.id}`);
      const href = t.launch.href === null ? null : (t.launch.href.startsWith('web/') ? t.launch.href.slice(4) : '../' + t.launch.href);
      if (href !== null && !card.includes(`href="${esc(href)}" data-task-launch="${t.id}"`)) taskBad.push(`${t.id}: no launch link ${href}`);
      for (const l of t.requires) if (!card.includes(`href="trade_craft_lessons.html#lesson-${l}"`) || !lessons[l]) taskBad.push(`${t.id}: lesson ${l} not linked`);
    }
    const hallWant = s.halls.flatMap((h) => treg.tasks.filter((t) => t.place.kind === 'hall' && t.place.id === h.id)).map((t) => t.id);
    const hb = (card.match(new RegExp(`<div class="halltasks" data-hall-tasks="${s.id}">([\\s\\S]*?)</div>`)) || [, ''])[1];
    const hallHave = [...hb.matchAll(/<li data-task="([^"]+)"/g)].map((m) => m[1]);
    if (JSON.stringify(hallHave) !== JSON.stringify(hallWant)) taskBad.push(`${s.id}: hall tasks ${JSON.stringify(hallHave)} != ${JSON.stringify(hallWant)}`);
    shown += hallHave.length;
  }
  const strays = treg.tasks.filter((t) => t.place.kind === 'wilds-site' && !siteWorld.has(t.place.id)).map((t) => t.id);
  if (strays.length) taskBad.push(`tasks name wilds sites that do not exist: ${strays.join(', ')}`);
  const counts = JSON.parse((html.match(/<script type="application\/json" id="wilds-tasks">([\s\S]*?)<\/script>/) || [, '{}'])[1]);
  for (const [sid] of siteWorld) if (counts[sid] !== treg.tasks.filter((t) => t.place.kind === 'wilds-site' && t.place.id === sid).length) taskBad.push(`${sid}: in-page count ${counts[sid]}`);
  ok(`[tasks] every site card lists exactly its registry tasks (${shown}) with launch link and linked lessons, plus the tasks of every hall working there; in-page counts match; no stray site`,
    taskBad.length === 0, taskBad);
  ok('[tasks] sites with tasks are marked on the minimap (ring) and in their labels; the practice honesty line is the registry\'s',
    /if \(SITE_TASKS\[s\.id\] > 0\) \{ const p = toMini/.test(main) && /b\.classList\.add\('has-tasks'\)/.test(main)
    && html.includes(`<p class="help" data-tasks-honesty>${esc(treg.honesty.practice)}</p>`));
}

/* ------------------------------------------------------------ quests -- */
const qpath = join(ROOT, 'quests/registry/quests.json');
const wq = existsSync(qpath) ? JSON.parse(readFileSync(qpath, 'utf8')).quests.filter((q) => q.world.startsWith('wilds:')) : [];
if (wq.length === 0) {
  ok('[quests] no wilds quests are registered yet, and the page says the quest log is not wired (integration point)',
    /data-quests-pending/.test(html) && !/data-tc-(egg|quest)=/.test(html));
} else {
  const places = new Map(reg.worlds.map((w) => [w.id, new Set(['trailhead', ...w.sites.map((s) => s.id), ...w.caches.map((c) => c.id)])]));
  const miss = [];
  for (const q of wq) {
    const wid = q.world.split(':')[1];
    const attr = q.kind === 'treasure' || q.kind === 'egg' ? 'data-tc-egg' : 'data-tc-quest';
    if (!html.includes(`${attr}="${q.id}"`)) miss.push(`${q.id}: no ${attr} hook`);
    if (!places.has(wid) || !places.get(wid).has(q.place)) miss.push(`${q.id}: place ${q.place} not in ${wid}`);
  }
  ok('[quests] every wilds quest has its hook and its place resolves to a site, cache or trailhead of its world', miss.length === 0, miss);
  const qi = html.indexOf('<script', html.indexOf('id="wilds-main"') + 1);
  ok('[quests] the quest script comes after the page\'s own main script', html.indexOf('id="wilds-main"') > 0 && qi > html.indexOf('id="wilds-main"'));
  ok('[quests] a quest log is on the page', /<div data-tc-questlog><\/div>/.test(html));
}

/* -------------------------------------------------------------- eval -- */
{
  const evs = readFileSync(join(ROOT, 'web/eval_wilds.mjs'), 'utf8');
  const bl = evs.slice(evs.indexOf('const BASE = {'), evs.indexOf('const CALL_HEADROOM'));
  const rows = [...bl.matchAll(/(overview|trail|dense|summit): \{([^}]*)\}/g)];
  const noBB = rows.filter((m) => !/\bbb: (null|\d+)/.test(m[2])).map((m) => m[1]);
  const woodedNull = rows.filter((m) => /veg: [\d_]+/.test(m[2]) && /\bbb: null/.test(m[2])).map((m) => m[1]);
  ok('[eval] every declared view carries a billboard floor (bb), measured for every view meant to be wooded; the eval checks cards stay past VEG_R and out of the overview',
    rows.length === reg.worlds.length * 4 && noBB.length === 0 && woodedNull.length === 0
    && /inside VEG_R/.test(evs) && /billboards drawn in the overview/.test(evs), [...noBB, ...woodedNull]);
}
const ev = read('web/eval_wilds.mjs');
const baseBlock = ev.slice(ev.indexOf('const BASE = {'), ev.indexOf('const CALL_HEADROOM'));
ok('[eval] web/eval_wilds.mjs declares a target for every world and all four views',
  reg.worlds.every((w) => new RegExp(`\\b${w.id}: \\{[\\s\\S]*?overview:[\\s\\S]*?trail:[\\s\\S]*?dense:[\\s\\S]*?summit:`).test(baseBlock)),
  reg.worlds.map((w) => w.id));

/* [class] wave 8: the class session kit (web/classkit.py) at wilds sites - play only, no network */
{
  const page = read('web/trade_craft_wilds.html');
  const js = (id) => { const m = page.match(new RegExp('<script type="application/json" id="' + id + '">([\\s\\S]*?)</script>')); return m ? JSON.parse(m[1]) : null; };
  const cd = js('class-data'), ci = js('class-i18n'), wreg = JSON.parse(read('wilds/registry/wilds.json'));
  const creg = JSON.parse(read('classroom/registry/classroom.json'));
  const sites = new Set(wreg.worlds.flatMap((w) => w.sites.map((s) => 'wilds:' + w.id + '/' + s.id)));
  ok('[class] class data embedded for the wilds world only, stamp = classroom registry', !!cd && cd.stamp === creg.source_stamp
    && cd.worlds.join() === 'wilds' && cd.places.length > 0 && cd.places.every((p) => p.world === 'wilds'));
  ok('[class] every wilds place in the class data is a real wilds site', !!cd && cd.places.every((p) => sites.has(p.id)));
  ok('[class] opening a site tells the class kit it was reached (wilds:<world>/<site id>)',
    page.includes("if (window.TCClass) window.TCClass.reach('wilds:' + W.id + '/' + id);"));
  const kit = (page.match(/<script id="class-kit">([\s\S]*?)<\/script>/) || [, ''])[1];
  ok('[class] class kit mounted folded, 8 locales, no network, stores only tc-class-* keys', /TCClass\.mount\(\{ compact: true \}\);/.test(kit)
    && !!ci && Object.keys(ci).length === 8 && !/\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket/.test(kit)
    && /PROG_KEY = 'tc-class-progress', PLAN_KEY = 'tc-class-plan'/.test(kit));
}

console.log(bad ? `wilds page: ${bad} FAILED, ${n} ok` : `wilds page: all ${n} checks ok`);
process.exit(bad ? 1 : 0);
