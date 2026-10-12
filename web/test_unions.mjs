/* web/test_unions.mjs - the union hall directory (web/trade_craft_unions.html), checked against
 * unionpaths/registry/union_paths.json, the hive registry, the eight locales and the pages it links to; plus the two
 * link-ins it adds to the Courses and Hive pages. Browser-free by default. Recompute, never re-read: every count is
 * recounted from the registry, every link target is looked up on the page it names, every voice line is compared with
 * hive/registry/hive.json. --browser (or --browser=<base url>) also drives the pages in Chromium with the device's
 * speech synthesis replaced by a recorder; without a url it serves web/ itself on 127.0.0.1 and stops only the server
 * it started. Run it under flock $SP/chromium.lock. */
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (m, c, why) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m + (why !== undefined ? ' :: ' + JSON.stringify(why).slice(0, 400) : '')); } };
const J = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));
const page = readFileSync(join(HERE, 'trade_craft_unions.html'), 'utf8');
const coursesPage = readFileSync(join(HERE, 'trade_craft_courses.html'), 'utf8');
const hivePage = readFileSync(join(HERE, 'trade_craft_hive.html'), 'utf8');
const lessonsPage = readFileSync(join(HERE, 'trade_craft_lessons.html'), 'utf8');
const reg = J('unionpaths/registry/union_paths.json'), H = reg.halls, CNT = reg.counts;
const HIVE = Object.fromEntries(J('hive/registry/hive.json').agents.map((a) => [a.id, a]));
const LOC = Object.fromEntries(['en', 'es', 'fr', 'de', 'pt', 'zh', 'hi', 'ar'].map((l) => [l, J(`i18n/locales/${l}.json`)]));
const blob = (pg, id) => JSON.parse(pg.split(`<script type="application/json" id="${id}">`)[1].split('</script>')[0]);
const script = (pg, id) => pg.split(`<script id="${id}">`)[1].split('</script>')[0];
const data = blob(page, 'union-data'), I = blob(page, 'union-i18n'), HV = blob(page, 'union-voice');
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
const cardOf = (slug) => { const a = page.indexOf(`<article class="uh" id="hall-${slug}"`); return a < 0 ? '' : page.slice(a, page.indexOf('</article>', a)); };
const section = (id) => { const a = page.indexOf(`<section class="box${id === 'union-links' ? ' links' : ''}" id="${id}"`); return a < 0 ? '' : page.slice(a, page.indexOf('</section>', a)); };

/* ---- shell ---- */
ok('exactly one <h1>, and it is the translated page title', (page.match(/<h1[\s>]/g) || []).length === 1
  && /<h1 class="tc-page-title" data-i18n="union.title">/.test(page));
ok('the site nav is present and marks this page current', /href="trade_craft_unions.html" aria-current="page"/.test(page));
ok('the saved-style head script runs before paint', page.indexOf('id="style-head-js"') > 0 && page.indexOf('id="style-head-js"') < page.indexOf('</head>'));
ok('the embedded data is the registry: same stamp, same counts', data.stamp === reg.source_stamp && JSON.stringify(data.counts) === JSON.stringify(CNT));
ok('the figures are recounted from the registry (halls, districts, lessons, path steps, halls with seats, halls with crews)',
  [['halls', H.length], ['districts', new Set(H.map((h) => h.district)).size], ['lessons', H.reduce((a, h) => a + h.lessons.length, 0)],
    ['path_steps', H.reduce((a, h) => a + h.path.length, 0)], ['halls_with_seats', H.filter((h) => h.seats.length).length],
    ['halls_with_crews', H.filter((h) => h.crews.length).length]].every(([k, v]) => page.includes(`data-union-count="${k}">${v}<`)));

/* ---- one card per hall, its path in order ---- */
const at = H.map((h) => page.indexOf(`<article class="uh" id="hall-${h.hall}"`));
ok(`one card per union hall, in the union registry order, each with a #hall-<slug> anchor (${H.length})`,
  (page.match(/<article class="uh"/g) || []).length === H.length && at.every((x, i) => x > 0 && (i === 0 || x > at[i - 1])));
ok('each card carries its hall\'s district and cohort for the filters, and its name, focus and campus',
  H.every((h) => page.includes(`id="hall-${h.hall}" data-hall="${h.hall}" data-district="${h.district}" data-cohort="${h.cohort}"`)
    && cardOf(h.hall).includes(`<h3>${esc(h.name)}</h3>`) && cardOf(h.hall).includes(esc(h.focus)) && cardOf(h.hall).includes(esc(h.campus_name))));
const STEPS = ['course', 'lessons', 'seats', 'crib', 'advisor', 'crews'];
ok('each card shows the path in its fixed order: course, lessons, seats, crib, advisor, crews, with the registry\'s step count',
  H.every((h) => { const c = cardOf(h.hall), p = STEPS.map((s) => c.indexOf(`data-step="${s}"`));
    return p.every((x, i) => x > 0 && (i === 0 || x > p[i - 1])) && c.includes(`data-path-steps="${h.path.length}"`); }));
ok('each card links its trade course (?course=<id>), and the Courses page has that course card',
  H.every((h) => cardOf(h.hall).includes(`data-link="course" href="trade_craft_courses.html?course=${h.course}#course-trade"`)
    && coursesPage.includes(`data-course="${h.course}"`)));
ok('each card lists its lessons in ladder order, each linked to the lessons page anchor and to its supplement',
  H.every((h) => { const c = cardOf(h.hall), p = h.lessons.map((l) => c.indexOf(`data-lesson="${l.lesson}"`));
    return p.every((x, i) => x > 0 && (i === 0 || x > p[i - 1])) && h.lessons.every((l) => c.includes(`href="trade_craft_lessons.html#lesson-${l.lesson}"`)
      && c.includes(`data-link="supp" href="trade_craft_courses.html?lesson=${l.lesson}#course-sup"`) && lessonsPage.includes(`id="lesson-${l.lesson}"`)); }));
ok('every supplement a card links to is embedded on the Courses page (139 lessons)',
  H.every((h) => h.lessons.every((l) => coursesPage.includes(`<option value="${l.lesson}">`))) && H.reduce((a, h) => a + h.lessons.length, 0) === CNT.lessons);
ok('each card links every bound seat into its hall in 3D (?hall=&sim=), or says no seat is bound',
  H.every((h) => { const c = cardOf(h.hall); return h.seats.length ? h.seats.every((s) => c.includes(`href="trade_craft_3d.html?hall=${h.hall}&amp;sim=${s.sim}">${esc(s.name)}</a>`))
    && (c.match(/data-link="seat"/g) || []).length === h.seats.length : c.includes('data-i18n="union.p.noseat"'); }));
ok('each card names its tool crib by the crib registry name and id', H.every((h) => cardOf(h.hall).includes(`${esc(h.crib.name)} <code>${h.crib.crib}</code>`)));
ok('each card links its advisor to the Hive page (?agent=<id>), which has that agent\'s card; a door guide says why',
  H.every((h) => { const c = cardOf(h.hall);
    return c.includes(`data-link="advisor" href="trade_craft_hive.html?agent=${h.advisor.id}"`) && hivePage.includes(`data-agent="${h.advisor.id}"`)
      && c.includes(`data-speak="${h.advisor.id}"`) && c.includes(esc(HIVE[h.advisor.id].name)) && c.includes('data-door="1"') === (h.advisor.rule === 'door'); }));
ok('each card lists its crews, every role by its Hive name and linked to its own card on the Hive page, or says no crew runs a seat here',
  H.every((h) => { const c = cardOf(h.hall); return h.crews.length ? h.crews.every((cr) => c.includes(`data-crew="${cr.crew}"`)
    && cr.roles.every((r) => c.includes(`href="trade_craft_hive.html?agent=${r}">${esc(HIVE[r].name)}</a>`) && hivePage.includes(`data-agent="${r}"`))) : c.includes('data-i18n="union.p.nocrew"'); }));
ok('each card names the other advisors its lessons send a learner to, each by its Hive name and linked to its Hive card',
  H.every((h) => { const c = cardOf(h.hall); return c.includes('data-also="1"') === (h.advisor.also.length > 0)
    && h.advisor.also.every((x) => c.includes(`data-link="advisor-also" href="trade_craft_hive.html?agent=${x}">${esc(HIVE[x].name)}</a>`) && hivePage.includes(`data-agent="${x}"`)); }));
ok('each card links the hall in 3D, its course and its ladder, each a real page',
  H.every((h) => { const c = cardOf(h.hall); return c.includes(`data-link="hall3d" href="trade_craft_3d.html?hall=${h.hall}"`)
    && c.includes(`data-link="ladder" href="trade_craft_ladder.html?hall=${h.hall}"`); })
  && ['trade_craft_3d.html', 'trade_craft_ladder.html', 'trade_craft_courses.html', 'trade_craft_hive.html', 'trade_craft_lessons.html'].every((f) => existsSync(join(HERE, f))));

/* ---- filters and rollups ---- */
const opts = (id) => [...page.split(`id="${id}">`)[1].split('</select>')[0].matchAll(/<option value="([^"]*)"/g)].map((m) => m[1]);
ok(`the filters: a focus search, a district list (${reg.districts.length}) and a cohort list (${reg.cohorts.length}), each with "any" first`,
  page.includes('<input type="search" id="union-q"') && JSON.stringify(opts('union-district')) === JSON.stringify(['', ...reg.districts])
  && JSON.stringify(opts('union-cohort')) === JSON.stringify(['', ...reg.cohorts]));
const rowOf = (table, key) => { const t = page.split(`<table id="${table}">`)[1].split('</table>')[0]; const a = t.indexOf(`<tr data-rollup="${key}">`); return a < 0 ? '' : t.slice(a, t.indexOf('</tr>', a)); };
const nums = (r) => Object.fromEntries([...r.matchAll(/<td data-n="([a-z]+)">(\d+)<\/td>/g)].map((m) => [m[1], +m[2]]));
const want = (hs) => ({ halls: hs.length, lessons: hs.reduce((a, h) => a + h.lessons.length, 0), seats: hs.filter((h) => h.seats.length).length,
  crews: hs.filter((h) => h.crews.length).length, door: hs.filter((h) => h.advisor.rule === 'door').length, advisors: new Set(hs.map((h) => h.advisor.id)).size });
ok('the district rollup is recounted here from the hall cards\' registry: one row per district, each linking its filter',
  reg.districts.every((d) => JSON.stringify(nums(rowOf('union-by-district', d))) === JSON.stringify(want(H.filter((h) => h.district === d)))
    && rowOf('union-by-district', d).includes(`href="?district=${d}#union-halls"`)) && JSON.stringify(nums(rowOf('union-by-district', 'all'))) === JSON.stringify(want(H)));
ok('the cohort rollup is recounted here: one row per cohort, each linking its filter',
  reg.cohorts.every((c) => JSON.stringify(nums(rowOf('union-by-cohort', c))) === JSON.stringify(want(H.filter((h) => h.cohort === c)))
    && rowOf('union-by-cohort', c).includes(`href="?cohort=${c}#union-halls"`)));

/* ---- honesty ---- */
const hon = section('union-honesty');
ok('the honesty block says, in every locale, that no union named is a partner or affiliate, nothing is invented and real programmes stay PROPOSED',
  ['union.hon.partner', 'union.hon.invented', 'union.hon.proposed', 'union.hon.lessons', 'union.hon.voice'].every((k) => hon.includes(`data-i18n="${k}"`))
  && /not a partner, sponsor or affiliate/.test(LOC.en.strings['union.hon.partner']) && /PROPOSED/.test(LOC.en.strings['union.hon.proposed'])
  && Object.values(LOC).every((l) => /PROPOSED|PROPUESTO|PROPOSÉ|VORGESCHLAGEN|PROPOSTO/.test(l.strings['union.hon.proposed'])));
ok(`the registries' own honesty lines are quoted verbatim with their sources (${reg.honesty_quoted.length}), and the registry's own block follows`,
  reg.honesty_quoted.every((q) => hon.includes(`data-quote-src="${esc(q.source)}" lang="en"><q>${esc(q.text)}</q>`))
  && Object.entries(reg.honesty).every(([k, v]) => hon.includes(`data-union-honesty="${k}" lang="en">${esc(v)}</li>`)));
const FORBID = /\b(hours?|wages?|salar(y|ies)|pay rate|per hour|credential(s|ed)?|certif\w*|membership|affiliat\w*|apprenticeship|journeyman|journeyworker|union dues|local \d+)\b|\$\s?\d/i;
const visible = page.replace(/<script[\s\S]*?<\/script>/g, '').replace(/<style[\s\S]*?<\/style>/g, '').replace(hon, '').replace(/<head>[\s\S]*?<\/head>/, '');
const vhits = (visible.replace(/<[^>]+>/g, ' ').match(new RegExp(FORBID.source, 'gi')) || []);
ok('outside the honesty block the page states no apprenticeship hours, wages, credentials, membership or affiliation', vhits.length === 0, vhits.slice(0, 5));
ok('no internal reference on the page (no scratchpad or /tmp path, no memory/ or console mention, no team codename)',
  !/\/tmp\/|scratchpad|memory\/|\bconsoles?\b|\bPATHWAYS\b|\bPROGRAMS\b|\bRESTORE\b|\bCOURSE\b|\bHIVE\b|\bBUILD\b/.test(page));
ok('the page markers are neutral (UNION-PATH) on all three pages that carry this work',
  page.includes('UNION-PATH') && coursesPage.includes('/* UNION-PATH: ?course=') && hivePage.includes('/* UNION-PATH: ?agent='));
ok('no model identifier and no claim of certification on the page', !/claude-|gpt-|\bopus\b|\bsonnet\b/i.test(page)
  && !/\b(is|are) (certified|accredited)\b|\bcertified by\b|\baccredited by\b/i.test(page));

/* ---- strings ---- */
const keys = [...new Set([...page.matchAll(/data-i18n="([^"]+)"/g)].map((m) => m[1]))];
ok(`every chrome key on the page (${keys.length}) is embedded for all 8 locales and equals each locale file`,
  Object.keys(I).length === 8 && keys.every((k) => Object.entries(I).every(([l, v]) => typeof v.strings[k] === 'string' && v.strings[k] === LOC[l].strings[k] && v.strings[k].trim())));
ok('every locale translates the district names and tiers from its own blocks, and Arabic is right-to-left',
  Object.entries(I).every(([l, v]) => reg.districts.every((d) => v.districts[d] === LOC[l].districts[d].name) && JSON.stringify(v.tiers) === JSON.stringify(LOC[l].tiers))
  && I.ar.dir === 'rtl' && I.en.dir === 'ltr');
ok('the nav names the page in every locale (nav.page.unions)', Object.values(LOC).every((l) => typeof l.strings['nav.page.unions'] === 'string' && l.strings['nav.page.unions'].trim()));

/* ---- voice: SCRIPTED, quoted, on a click ---- */
const advIds = [...new Set(H.map((h) => h.advisor.id))].sort();
ok(`the voice block carries exactly the advisors the paths name (${advIds.length}), each line quoted from hive.json with its source`,
  JSON.stringify(HV.agents.map((a) => a.id).sort()) === JSON.stringify(advIds)
  && HV.agents.every((a) => a.lines.every((ln, i) => HV.texts[ln.t][0] === HIVE[a.id].lines[i].text && HV.texts[ln.t][1] === HIVE[a.id].lines[i].source))
  && HV.agents.every((a) => a.pitch === HIVE[a.id].voice.pitch && a.rate === HIVE[a.id].voice.rate));
ok('each advisor\'s opening line exists (the line a Speak button says), and its classroom line is play-safe',
  HV.agents.every((a) => a.lines[a.o] && (a.o12 === null || a.o12 === undefined || a.o12 < 0 || a.lines[a.o12].safe === 1)));
const pjs = script(page, 'union-page');
ok('speech happens only inside the click handler: one HiveVoice.speak call, after the click listener, none at load',
  (pjs.match(/HiveVoice\.speak\(/g) || []).length === 1 && pjs.indexOf("addEventListener('click', function (ev)") > 0
  && pjs.indexOf('HiveVoice.speak(') > pjs.indexOf("getElementById('union-halls').addEventListener('click'") && !/autoplay|speechSynthesis\.speak/.test(pjs));
ok('the page script stores nothing and sends nothing (no storage, no request, no beacon)', !/localStorage|sessionStorage|indexedDB|fetch\(|XMLHttpRequest|sendBeacon|WebSocket/.test(pjs));
ok('the voice kit is the Hive page\'s own, byte for byte', script(page, 'hive-kit') === hivePage.split('<script id="hive-kit">')[1].split('</script>')[0]);

/* ---- the link-ins on the Courses and Hive pages ---- */
ok('every trade course card on the Courses page links to its hall in the directory and to its Hive advisor',
  H.every((h) => { const a = coursesPage.indexOf(`data-course="${h.course}"`), c = coursesPage.slice(a, coursesPage.indexOf('</details>', a));
    return c.includes(`<a href="trade_craft_unions.html#hall-${h.hall}">`) && c.includes(`href="trade_craft_hive.html?agent=${h.advisor.id}" data-union-advisor="${h.advisor.id}"`); })
  && (coursesPage.match(/class="union-path-links"/g) || []).length === H.length);
ok('the Courses page opens a ?course= card and the Hive page focuses a ?agent= card; the Hive focus never speaks',
  /var want = q\.get\('course'\)[\s\S]{0,200}el\.open = true/.test(coursesPage)
  && (() => { const blk = hivePage.split('/* UNION-PATH: ?agent=')[1].split('})();')[0]; return /q\.get\('agent'\)/.test(blk) && !/speak\(/.test(blk); })());
ok('the Courses page carries the two link keys in all 8 locales', (() => { const CI = blob(coursesPage, 'course-i18n');
  return Object.keys(CI).length === 8 && Object.entries(CI).every(([l, v]) => v.strings['union.c.hall'] === LOC[l].strings['union.c.hall'] && v.strings['union.c.advisor'] === LOC[l].strings['union.c.advisor']); })());
ok('the related-page links are real files', ['trade_craft_courses.html', 'trade_craft_hive.html', 'trade_craft_3d.html', 'trade_craft_ladder.html']
  .every((f) => section('union-links').includes(`href="${f}"`) && existsSync(join(HERE, f))));

/* ---- browser (opt-in) ---- */
const barg = process.argv.find((a) => a === '--browser' || a.startsWith('--browser='));
if (barg) {
  const { spawn } = await import('node:child_process');
  let base = barg.includes('=') ? barg.split('=').slice(1).join('=') : null, srv = null;
  if (!base) { const port = 18800 + (process.pid % 90); srv = spawn('python3', ['-m', 'http.server', String(port), '--bind', '127.0.0.1'], { cwd: HERE, stdio: 'ignore' });
    base = `http://127.0.0.1:${port}`; await new Promise((r) => setTimeout(r, 900)); }
  const { chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs');
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  /* the device voice, replaced by a recorder: one local English voice; every utterance is kept, nothing is played */
  const RECORDER = () => { window.__said = [];
    const v = { name: 'rec', lang: 'en-US', localService: true, default: true, voiceURI: 'rec' };
    window.SpeechSynthesisUtterance = function (t) { this.text = t; };
    Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: { getVoices: () => [v], cancel() {}, speak(u) { window.__said.push({ text: u.text, pitch: u.pitch, rate: u.rate }); } } }); };
  const errs = [], away = [];
  const open = async (ctx, url) => { const pg = await ctx.newPage(); pg.on('pageerror', (e) => errs.push(url + ': ' + e.message));
    pg.on('console', (m) => { if (m.type() === 'error') errs.push(url + ' console: ' + m.text()); }); pg.on('request', (r) => { if (!r.url().startsWith(base)) away.push(r.url()); });
    await pg.goto(base + '/' + url, { waitUntil: 'load' }); return pg; };
  try {
    for (const vp of [{ width: 1440, height: 900, n: 'desktop' }, { width: 360, height: 800, n: 'phone' }]) {
      const ctx = await b.newContext({ viewport: { width: vp.width, height: vp.height } }); await ctx.addInitScript(RECORDER);
      const pg = await open(ctx, 'trade_craft_unions.html?lang=en'); await pg.waitForFunction(() => window.__unionPage);
      const f = await pg.evaluate(() => { const P = window.__unionPage, all = P.filter(), d = document.getElementById('union-district'), c = document.getElementById('union-cohort'), s = document.getElementById('union-q');
        d.value = 'structural'; const st = P.filter(); c.value = 'new-78'; const both = P.filter(); d.value = ''; const nw = P.filter(); c.value = '';
        s.value = 'weld'; const weld = P.filter(); const wv = [...document.querySelectorAll('article.uh:not([hidden])')].every((el) => el.dataset.text.includes('weld')); s.value = ''; P.filter();
        return { all, st, both, nw, weld, wv, said: window.__said.length, ov: document.documentElement.scrollWidth - window.innerWidth }; });
      const n = (fn) => H.filter(fn).length;
      ok(`browser ${vp.n}: the filters show ${f.all} halls, ${f.st} structural, ${f.both} structural new-78, ${f.nw} new-78, ${f.weld} for "weld" (registry: ${H.length}, ${n((h) => h.district === 'structural')}, ${n((h) => h.district === 'structural' && h.cohort === 'new-78')}, ${n((h) => h.cohort === 'new-78')})`,
        f.all === H.length && f.st === n((h) => h.district === 'structural') && f.both === n((h) => h.district === 'structural' && h.cohort === 'new-78')
        && f.nw === n((h) => h.cohort === 'new-78') && f.weld > 0 && f.wv);
      ok(`browser ${vp.n}: nothing is spoken at load, and the page does not scroll sideways (${f.ov} px)`, f.said === 0 && f.ov <= 0);
      const h0 = H.find((h) => h.advisor.rule === 'lessons'), a0 = HV.agents.find((a) => a.id === h0.advisor.id);
      await pg.click(`#hall-${h0.hall} [data-speak]`);
      const sp = await pg.evaluate(() => ({ said: window.__said.slice(), shown: document.querySelector('#union-said q').textContent, src: document.querySelector('#union-said code').textContent }));
      const line = HV.texts[a0.lines[a0.o].t];
      ok(`browser ${vp.n}: a click on Speak says the advisor's quoted opening line once, at its registry pitch and rate, and shows its source`,
        sp.said.length === 1 && sp.said[0].text === line[0] && sp.shown === line[0] && sp.src === line[1] && Math.abs(sp.said[0].pitch - a0.pitch) < 1e-9);
      await ctx.close();
    }
    const ctx = await b.newContext({ viewport: { width: 1280, height: 800 } }); await ctx.addInitScript(RECORDER);
    const pc = await open(ctx, 'trade_craft_unions.html?classroom&lang=en'); await pc.waitForFunction(() => window.__unionPage);
    await pc.click(`#hall-${H[0].hall} [data-speak]`);
    const cm = await pc.evaluate(() => ({ said: window.__said.length, st: document.getElementById('union-status').textContent, k12: window.__unionPage.k12 }));
    ok(`browser classroom: voice starts muted, so a Speak click says nothing ("${cm.st}")`, cm.k12 && cm.said === 0 && cm.st === I.en.strings['hive.v.muted']);
    const pd = await open(ctx, 'trade_craft_unions.html?district=systems&cohort=existing-33&lang=ar'); await pd.waitForFunction(() => window.__unionPage);
    const dd = await pd.evaluate(() => ({ n: document.querySelectorAll('article.uh:not([hidden])').length, dir: document.documentElement.dir, h1: document.querySelector('h1').textContent }));
    ok(`browser: ?district=&cohort= preset the filters (${dd.n}), and Arabic renders right-to-left with its own title`,
      dd.n === H.filter((h) => h.district === 'systems' && h.cohort === 'existing-33').length && dd.dir === 'rtl' && dd.h1 === I.ar.strings['union.title']);
    for (const l of Object.keys(I)) { const pl = await open(ctx, `trade_craft_unions.html?lang=${l}`); await pl.waitForFunction(() => window.__unionPage); await pl.close(); }
    ok('browser: all 8 locales load without a page error', !errs.some((e) => /lang=/.test(e)), errs);
    const tgt = H[H.length - 1];
    const ph = await open(ctx, `trade_craft_unions.html?lang=en#hall-${tgt.hall}`); await ph.waitForFunction(() => window.__unionPage);
    const inView = await ph.evaluate((id) => { const r = document.getElementById(id).getBoundingClientRect(); return r.top < window.innerHeight && r.bottom > 0; }, 'hall-' + tgt.hall);
    ok(`browser: #hall-${tgt.hall} lands on that hall's card`, inView);
    const pco = await open(ctx, `trade_craft_courses.html?course=${H[1].course}&lang=en`); await pco.waitForFunction(() => window.__coursePage);
    const co = await pco.evaluate((id) => { const el = document.querySelector(`details.course[data-course="${id}"]`); const r = el.getBoundingClientRect(); return { open: el.open, inView: r.top < window.innerHeight && r.bottom > 0 }; }, H[1].course);
    ok(`browser: the Courses page opens ?course=${H[1].course} and scrolls to it`, co.open && co.inView);
    const adv = H.find((h) => h.advisor.rule === 'lessons').advisor.id;
    const phv = await open(ctx, `trade_craft_hive.html?agent=${encodeURIComponent(adv)}&lang=en`); await phv.waitForTimeout(400);
    const hv = await phv.evaluate((id) => { const el = document.querySelector(`.hv-card[data-agent="${id}"]`); const r = el.getBoundingClientRect();
      return { focus: el.getAttribute('data-focus'), hidden: el.hidden, inView: r.top < window.innerHeight && r.bottom > 0, said: window.__said.length }; }, adv);
    ok(`browser: the Hive page brings ?agent=${adv} into view and marks it, and says nothing until a click`, hv.focus === '1' && !hv.hidden && hv.inView && hv.said === 0);
    await ctx.close();
  } finally { await b.close(); if (srv) srv.kill(); }
  ok('browser: zero page errors and no request leaves the page\'s own origin', errs.length === 0 && away.length === 0, [...errs, ...away].slice(0, 6));
}

console.log(`test_unions: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
