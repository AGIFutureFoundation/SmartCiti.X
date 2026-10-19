/* web/test_courses.mjs - the course catalogue page (web/trade_craft_courses.html), checked against courses/registry/courses.json
 * and the pages it links to. Browser-free by default. Recompute, never re-read: counts are recounted from the registry, the
 * embedded supplements are compared to the registry whole, every chrome key is looked up in all 8 locales, and the page's
 * own supplement renderer (supHTML, extracted between its markers) is run here for every lesson in every locale.
 * --browser (or --browser=<base url>) also drives the page in Chromium; without a url it serves web/ itself on 127.0.0.1
 * and stops only the server it started. Run it under flock $SP/chromium.lock. */
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (m, c, why) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m + (why !== undefined ? ' :: ' + JSON.stringify(why).slice(0, 400) : '')); } };
const page = readFileSync(join(HERE, 'trade_craft_courses.html'), 'utf8');
const reg = JSON.parse(readFileSync(join(ROOT, 'courses/registry/courses.json'), 'utf8'));
const lessonsPage = readFileSync(join(HERE, 'trade_craft_lessons.html'), 'utf8');
const blob = (id) => JSON.parse(page.split(`<script type="application/json" id="${id}">`)[1].split('</script>')[0]);
const data = blob('course-data'), I = blob('course-i18n');
const C = reg.courses, CV = Object.values(C), SUP = reg.supplements, LIDS = Object.keys(SUP);
const canon = (v) => Array.isArray(v) ? v.map(canon) : v && typeof v === 'object' ? Object.fromEntries(Object.keys(v).sort().map((k) => [k, canon(v[k])])) : v;
const unesc = (s) => s.replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');

ok('exactly one <h1>, and it is the translated page title', (page.match(/<h1[\s>]/g) || []).length === 1
  && /<h1 class="tc-page-title" data-i18n="course.title">/.test(page));
ok('the site nav is present and marks this page current', /href="trade_craft_courses.html" aria-current="page"/.test(page));
ok('the saved-style head script runs before paint', page.indexOf('id="style-head-js"') > 0 && page.indexOf('id="style-head-js"') < page.indexOf('</head>'));
ok('the embedded data is the registry: same stamp, every supplement whole', data.stamp === reg.source_stamp
  && JSON.stringify(canon(data.supplements)) === JSON.stringify(canon(SUP)));
ok('the figures are recounted from the registry (courses, trade, strand, lessons, steps, questions, glossary terms)',
  [['courses', CV.length], ['trade_courses', CV.filter((c) => c.kind === 'trade').length], ['strand_courses', CV.filter((c) => c.kind === 'strand').length],
    ['lessons', LIDS.length], ['steps', LIDS.reduce((a, k) => a + SUP[k].worksheet.length, 0)],
    ['questions', LIDS.reduce((a, k) => a + SUP[k].questions.length, 0)], ['glossary_terms', LIDS.reduce((a, k) => a + SUP[k].glossary.length, 0)]]
    .every(([k, v]) => page.includes(`data-course-count="${k}">${v}<`)));
const cardOf = (id) => { const a = page.indexOf(`data-course="${id}"`); return a < 0 ? '' : page.slice(a, page.indexOf('</details>', a)); };
ok(`every course in the registry has exactly one card (${CV.length})`, CV.every((c) => page.split(`data-course="${c.id}"`).length === 2));
ok('every trade card sits under its district heading, in the registry order',
  reg.districts.every((d) => { const a = page.indexOf(`data-district="${d.district}"`), b = page.indexOf('</section>', a), sec = page.slice(a, b);
    const at = d.courses.map((cid) => sec.indexOf(`data-course="${cid}"`)); return a > 0 && at.every((x) => x > 0) && at.every((x, i) => i === 0 || x > at[i - 1]); }));
ok('every card lists its outline in the registry order, each lesson linked to its anchor on the lessons page and to its supplement',
  CV.every((c) => { const card = cardOf(c.id); const at = c.lessons.map((l) => card.indexOf(`data-lesson="${l}"`));
    return at.every((x, i) => x > 0 && (i === 0 || x > at[i - 1])) && c.lessons.every((l) => card.includes(`href="trade_craft_lessons.html#lesson-${l}"`)
      && card.includes(`data-sup="${l}"`)); }));
ok(`every lesson anchor a card links to exists on the lessons page (${LIDS.length})`, LIDS.every((l) => lessonsPage.includes(`id="lesson-${l}"`)));
ok('every card shows its lesson and step counts from the registry, and its seat counts when a seat binds',
  CV.every((c) => { const card = cardOf(c.id), st = c.seat_time;
    return card.includes(`<b data-count="lessons">${c.counts.lessons}</b>`) && card.includes(`<b data-count="steps">${c.counts.steps}</b>`)
      && ((st.seats_bound.length || st.seats_in_lessons.length) ? card.includes(`<b data-seat="runs">${st.sim_runs}</b>`) && card.includes('data-i18n="course.c.nominutes"')
        : card.includes('data-i18n="course.c.noseat"')); }));
ok('every card names its K-12 bands from the registry (and only those)',
  CV.every((c) => { const card = cardOf(c.id); return JSON.stringify([...card.matchAll(/data-band="([^"]+)"/g)].map((m) => m[1])) === JSON.stringify(c.bands)
    && page.includes(`data-course="${c.id}" data-kind="${c.kind}" data-bands="${c.bands.join(' ')}"`); }));
ok('prerequisites from outside a course are shown as named links with the edge reason; a course without any says so',
  CV.every((c) => { const card = cardOf(c.id); return c.prerequisites_outside.length
    ? c.prerequisites_outside.every((p) => card.includes(`data-sup="${p.needs}"`) && card.includes(`data-i18n="course.r.${p.because}"`))
    : card.includes('data-i18n="course.c.nothing"'); }));
ok('no card disables, locks or hides a lesson behind its prerequisites (no disabled or locked marker on the page)',
  !/\bdisabled\b|data-locked|aria-disabled/.test(page.replace(/<script[\s\S]*?<\/script>/g, '')));
ok('every registry honesty line is printed verbatim, plus the four translated honesty lines',
  Object.entries(reg.honesty).every(([k, v]) => page.includes(`data-honesty="${k}" lang="en">${v.replace(/&/g, '&amp;').replace(/'/g, '&#x27;').replace(/"/g, '&quot;')}<`)
    || unesc(page).includes(v)) && ['course.hon.cert', 'course.hon.gate', 'course.hon.bands', 'course.hon.time'].every((k) => page.includes(`data-i18n="${k}"`)));
const keys = [...new Set([...page.matchAll(/data-i18n="([^"]+)"/g)].map((m) => m[1]))];
ok(`every chrome key on the page (${keys.length}) and every course.* key the renderer uses exists, non-empty, in exactly the 8 shipped locales; Arabic is right-to-left`,
  JSON.stringify(Object.keys(I).sort()) === JSON.stringify(readdirSync(join(ROOT, 'i18n/locales')).filter((f) => f.endsWith('.json')).map((f) => f.slice(0, -5)).sort())
  && Object.keys(I).length === 8 && [...keys, ...Object.keys(I.en.strings)].every((k) => Object.values(I).every((L) => typeof L.strings[k] === 'string' && L.strings[k].trim()))
  && I.ar.dir === 'rtl');
ok('the non-English chrome is translated, not copied (under 10% identical to English, every locale)', Object.entries(I).filter(([l]) => l !== 'en').every(([, L]) =>
  Object.keys(L.strings).filter((k) => L.strings[k] === I.en.strings[k]).length < Object.keys(L.strings).length * 0.1));
ok('every placeholder in an English template survives in every locale ({n}, {room}, {ask}, ...)',
  Object.entries(I.en.strings).every(([k, v]) => (v.match(/\{\w+\}/g) || []).every((ph) => Object.values(I).every((L) => L.strings[k].includes(ph)))));
ok('strand and tier names come from each locale\'s own blocks', Object.values(I).every((L) => reg.strands.every((s) => L.strands[s.strand]) && reg.tiers.every((t) => L.tiers[t])));

/* the page's own renderer, run here for every lesson in every locale */
const src = page.split('/* SUP_RENDER:BEGIN */')[1]?.split('/* SUP_RENDER:END */')[0];
ok('the supplement renderer is a marked, DOM-free block', !!src && !/document\.|window\./.test(src));
const R = src ? new Function(src + '; return { supHTML: supHTML, supEsc: supEsc };')() : null;
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
{ const bad = []; let n = 0;
  for (const [loc, L] of Object.entries(I)) for (const id of LIDS) {
    const s = SUP[id]; let h = '';
    try { h = R.supHTML(s, L); } catch (e) { bad.push(`${loc} ${id}: throws ${e.message}`); continue; }
    n++;
    if (/undefined|\{\w+\}|NaN/.test(h.replace(/<code>[^<]*<\/code>/g, ''))) bad.push(`${loc} ${id}: an unfilled value`);
    if (!s.glossary.every((g) => h.includes(esc(g.term)))) bad.push(`${loc} ${id}: a glossary term is missing`);
    if (!s.safety.placards.every((p) => h.includes(`<blockquote lang="en" data-quote>${esc(p.quote)}</blockquote>`))) bad.push(`${loc} ${id}: a placard is not quoted verbatim`);
    if (!h.includes(esc(L.strings['course.sup.unverified'])) || !h.includes(esc(s.safety.limits))) bad.push(`${loc} ${id}: the safety label or the limits are missing`);
    if (h.indexOf('data-sec="safety"') > h.indexOf('data-sec="questions"')) bad.push(`${loc} ${id}: safety comes after the questions`);
    if ((h.match(/<fieldset data-q=/g) || []).length !== s.questions.length) bad.push(`${loc} ${id}: question count`);
    if (!s.questions.every((q) => q.options.every((o) => h.includes(`value="${esc(o.id)}"`)))) bad.push(`${loc} ${id}: an option is missing`);
    if ((h.match(/<li data-ws=/g) || []).length !== s.worksheet.length || !s.worksheet.every((w) => h.includes(esc(w.do)))) bad.push(`${loc} ${id}: worksheet lines`);
    if (!h.includes(`href="${esc(s.where.links.lesson.slice(4))}"`) || !h.includes(esc(s.where.crib.name))) bad.push(`${loc} ${id}: where-to-go`);
    if (!s.concepts.every((c) => h.includes(esc(c.text)))) bad.push(`${loc} ${id}: a key concept is missing`);
  }
  ok(`the supplement renders for every lesson in every locale (${n} renders): every glossary term, placard quote (verbatim), concept, question option and worksheet line, safety first, no unfilled value`,
    bad.length === 0 && n === LIDS.length * 8, bad.slice(0, 6)); }
ok('every supplement link the renderer builds points at a real page (lessons, 3D, ladder)',
  ['trade_craft_lessons.html', 'trade_craft_3d.html', 'trade_craft_ladder.html'].every((f) => existsSync(join(HERE, f))));
{ const own = ['course-render', 'course-page'].map((id) => (page.split(`<script id="${id}">`)[1] || 'MISSING').split('</script>')[0]).join('\n');
  ok('the page\'s own scripts save nothing and send nothing: no storage, no request, no print or download call, no alert',
    !own.includes('MISSING') && !/localStorage|sessionStorage|indexedDB|fetch\(|XMLHttpRequest|sendBeacon|window\.print|\.download\s*=|alert\(/.test(own)); }
ok('the worksheet prints without a print button: a print stylesheet hides the catalogue and keeps the supplement',
  /@media print\{[^}]*#course-trade[^}]*display:none/.test(page) && !/print\(/.test(page));
ok('links to the lessons, ladder, 3D campus and classroom pages, each a real file',
  ['trade_craft_lessons.html', 'trade_craft_ladder.html', 'trade_craft_3d.html', 'trade_craft_classroom.html'].every((f) => page.includes(`href="${f}"`) && existsSync(join(HERE, f))));
ok('no internal reference on the page (no scratchpad or /tmp path, no memory/ or console mention, no agent codename)',
  !/\/tmp\/|scratchpad|memory\/|\bconsoles?\b|\bCOURSE\b|\bHIVE\b|\bBUILD\b/.test(page));
ok('no model identifier and no claim of certification on the page', !/claude-|gpt-|\bopus\b|\bsonnet\b/i.test(page)
  && !/\b(is|are) (certified|accredited)\b|\bcertified by\b|\baccredited by\b/i.test(page));

/* ---- C3: the supplements are reachable from the 3D hall lesson flow and from the classroom ---- */
{ const p3 = readFileSync(join(HERE, 'trade_craft_3d.html'), 'utf8');
  const D3 = JSON.parse((p3.split('<script id="data" type="application/json">')[1] || 'null</script>').split('</script>')[0]);
  ok('the 3D hall roster puts a supplement link after every lesson chip, to trade_craft_courses.html?lesson=<id>#course-sup, labelled by course.c.supp',
    p3.includes("s.href = 'trade_craft_courses.html?lesson=' + encodeURIComponent(a.dataset.lesson) + '#course-sup';")
    && p3.includes("s.textContent = t('course.c.supp');") && /#hud \.lsup\{/.test(p3));
  ok('course.c.supp rides the 3D page\'s i18n wire in all 8 locales, with this page\'s own value',
    !!D3 && Object.keys(D3.i18n).length === 8 && Object.entries(D3.i18n).every(([l, c]) => c.strings['course.c.supp'] === I[l].strings['course.c.supp']));
  ok('every lesson the 3D roster can chip has a supplement to land on', !!D3 && Object.keys(D3.lessons.lessons).every((k) => SUP[k])); }
{ const pc = readFileSync(join(HERE, 'trade_craft_classroom.html'), 'utf8');
  const CR = JSON.parse(readFileSync(join(ROOT, 'classroom/registry/classroom.json'), 'utf8'));
  const want = CR.modules.flatMap((m) => m.lessons);
  const got = [...pc.matchAll(/href="trade_craft_courses\.html\?lesson=([^"#]+)#course-sup" data-sup-lesson="([^"]+)"/g)].filter((m) => m[1] === m[2]).map((m) => m[1]);
  ok(`the classroom lists every module lesson (${want.length}) with a link to its supplement, titled from the lessons registry`,
    JSON.stringify(got) === JSON.stringify(want) && got.every((k) => SUP[k] && pc.includes(`data-sup-lesson="${k}">${esc(SUP[k].title).replace(/'/g, '&#x27;')}</a>`)));
  ok('the classroom supplement list carries the no-certification line and translated headings (course.* keys in its catalogue)',
    pc.includes('data-i18n="course.h.sup"') && pc.includes('data-i18n="course.hon.cert"')); }

/* ---- browser (opt-in) ---- */
const barg = process.argv.find((a) => a === '--browser' || a.startsWith('--browser='));
if (barg) {
  const { spawn } = await import('node:child_process');
  let base = barg.includes('=') ? barg.split('=').slice(1).join('=') : null, srv = null;
  if (!base) { const port = 18900 + (process.pid % 90); srv = spawn('python3', ['-m', 'http.server', String(port), '--bind', '127.0.0.1'], { cwd: HERE, stdio: 'ignore' });
    base = `http://127.0.0.1:${port}`; await new Promise((r) => setTimeout(r, 900)); }
  const { chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs');
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const errs = [];
  try {
    for (const vp of [{ width: 1440, height: 900, n: 'desktop' }, { width: 390, height: 844, n: 'phone' }]) {
      const ctx = await b.newContext({ viewport: { width: vp.width, height: vp.height } }), pg = await ctx.newPage();
      pg.on('pageerror', (e) => errs.push(vp.n + ': ' + e.message)); pg.on('console', (m) => { if (m.type() === 'error') errs.push(vp.n + ' console: ' + m.text()); });
      const reqs = []; pg.on('request', (r) => { if (!r.url().startsWith(base)) reqs.push(r.url()); });
      await pg.goto(base + '/trade_craft_courses.html?lang=en', { waitUntil: 'load' }); await pg.waitForFunction(() => window.__coursePage);
      const f = await pg.evaluate(() => { const P = window.__coursePage, all = P.filter(); document.getElementById('course-search').value = 'riggers'; const one = P.filter();
        document.getElementById('course-search').value = ''; document.getElementById('course-band').value = 'K-5'; const k5 = P.filter();
        document.getElementById('course-band').value = ''; P.filter(); return { all, one, k5, shown: document.getElementById('course-shown').textContent }; });
      const k5 = CV.filter((c) => c.bands.includes('K-5')).length, rig = CV.filter((c) => [c.title, c.hall || '', ...c.outline.map((o) => o.title + ' ' + o.hall_name)].join(' ').toLowerCase().includes('riggers')).length;
      ok(`browser ${vp.n}: the filter shows all ${f.all} courses, ${f.one} for "riggers", ${f.k5} for band K-5 (registry: ${CV.length}, >=${rig}, ${k5})`,
        f.all === CV.length && f.one >= 1 && f.one < CV.length && f.k5 === k5 && /\d/.test(f.shown));
      const lid = 'riggers-first-card', s = SUP[lid];
      await pg.click(`details.course[data-course="trade.riggers"] summary`);
      await pg.click(`details.course[data-course="trade.riggers"] a[data-sup="${lid}"]`);
      const v = await pg.evaluate(() => ({ cur: window.__coursePage.current(), q: document.querySelectorAll('#sup-view fieldset[data-q]').length,
        pl: document.querySelectorAll('#sup-view [data-quote]').length, url: location.search }));
      ok(`browser ${vp.n}: the Supplement link opens ${lid} in place (${v.q} questions, ${v.pl} placard quotes, ?lesson in the URL)`,
        v.cur === lid && v.q === s.questions.length && v.pl === s.safety.placards.length && v.url.includes('lesson=' + lid));
      for (const q of s.questions) await pg.check(`#sup-view fieldset[data-q="${q.id}"] input[value="${q.answer.id}"]`);
      await pg.click('#sup-view [data-check]');
      const sc = await pg.evaluate(() => ({ t: document.querySelector('#sup-view .score').textContent, right: document.querySelectorAll('#sup-view fieldset[data-result="right"]').length }));
      ok(`browser ${vp.n}: answering with the registry ids scores ${sc.right} of ${s.questions.length} ("${sc.t}")`, sc.right === s.questions.length && sc.t.includes(String(s.questions.length)));
      ok(`browser ${vp.n}: no request leaves the page's origin (${reqs.length})`, reqs.filter((u) => !/fonts\.(googleapis|gstatic)\.com/.test(u)).length === 0, reqs);
      const ov = await pg.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      ok(`browser ${vp.n}: no horizontal scroll with a supplement open (${ov} px)`, ov <= 0);
      await ctx.close();
    }
    const ctx = await b.newContext({ viewport: { width: 390, height: 844 } }), pg = await ctx.newPage();
    pg.on('pageerror', (e) => errs.push('ar: ' + e.message));
    await pg.goto(base + '/trade_craft_courses.html?lang=ar&lesson=scaffold-read-the-tag', { waitUntil: 'load' }); await pg.waitForFunction(() => window.__coursePage);
    const ar = await pg.evaluate(() => ({ dir: document.documentElement.dir, cur: window.__coursePage.current(), h: document.querySelector('[data-i18n="course.h.sup"]').textContent,
      ov: document.documentElement.scrollWidth - window.innerWidth, ws: document.querySelectorAll('#sup-view li[data-ws]').length }));
    ok(`browser ar: right-to-left, ?lesson= opens the supplement (${ar.cur}, ${ar.ws} worksheet lines), translated headings, no horizontal scroll (${ar.ov} px)`,
      ar.dir === 'rtl' && ar.cur === 'scaffold-read-the-tag' && ar.ws === SUP['scaffold-read-the-tag'].worksheet.length && ar.h === I.ar.strings['course.h.sup'] && ar.ov <= 0);
    await ctx.close();
    { /* C3 in the browser: the 3D hall roster and the classroom reach the supplements */
      const ctx3 = await b.newContext({ viewport: { width: 1280, height: 800 } }), p3 = await ctx3.newPage();
      p3.on('pageerror', (e) => errs.push('3d: ' + e.message));
      await p3.goto(base + '/trade_craft_3d.html?hall=riggers&lang=de', { waitUntil: 'load' });
      await p3.waitForFunction(() => window.__tc3d && document.querySelectorAll('#hlessons .lsup').length > 0, null, { timeout: 45000 });
      const r3 = await p3.evaluate(() => [...document.querySelectorAll('#hlessons .lsup')].map((a) => ({ for: a.dataset.supFor, href: a.getAttribute('href'), text: a.textContent,
        prev: a.previousElementSibling && a.previousElementSibling.dataset.lesson })));
      const want3 = Object.values(SUP).filter((x) => x.hall === 'riggers').map((x) => x.lesson);
      ok(`browser 3d (de): the riggers hall roster shows ${r3.length} supplement links, one right after each lesson chip, to ?lesson=<id>#course-sup, labelled "${r3[0] && r3[0].text}"`,
        JSON.stringify(r3.map((x) => x.for).sort()) === JSON.stringify(want3.sort()) && r3.every((x) => x.prev === x.for
          && x.href === `trade_craft_courses.html?lesson=${encodeURIComponent(x.for)}#course-sup` && x.text === I.de.strings['course.c.supp']), r3);
      await ctx3.close();
      const ctxc = await b.newContext({ viewport: { width: 390, height: 844 } }), pc = await ctxc.newPage();
      pc.on('pageerror', (e) => errs.push('classroom: ' + e.message));
      await pc.goto(base + '/trade_craft_classroom.html?lang=fr', { waitUntil: 'load' });
      const rc = await pc.evaluate(() => ({ n: document.querySelectorAll('#cl-sup a[data-sup-lesson]').length, h: document.getElementById('cl-h-sup').textContent,
        ov: document.documentElement.scrollWidth - window.innerWidth }));
      const wantc = JSON.parse(readFileSync(join(ROOT, 'classroom/registry/classroom.json'), 'utf8')).modules.flatMap((m) => m.lessons).length;
      ok(`browser classroom (fr, phone): ${rc.n} supplement links (registry: ${wantc}), heading "${rc.h}", no horizontal scroll (${rc.ov} px)`,
        rc.n === wantc && rc.h === I.fr.strings['course.h.sup'] && rc.ov <= 0);
      await ctxc.close(); }
  } finally { await b.close(); if (srv) srv.kill(); }
  ok('browser: zero page errors', errs.length === 0, errs);
}

console.log(`test_courses: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
