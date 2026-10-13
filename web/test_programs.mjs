/* web/test_programs.mjs - the Programs page (web/trade_craft_programs.html) checked against programs/registry/programs.json,
 * the hive and the i18n catalogs. Static by default; --browser (or --browser=<base url>) also drives the page in
 * Chromium at desktop and 390 px phone width and in Arabic right-to-left. Without a url it serves web/ itself on
 * 127.0.0.1 and stops only the server it started. Run it under flock $SP/chromium.lock. */
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { execFileSync } from 'node:child_process';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (m, c, why) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m + (why !== undefined ? ' :: ' + JSON.stringify(why).slice(0, 500) : '')); } };
const J = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');

const reg = J('programs/registry/programs.json'), HV = J('hive/registry/hive.json'), SM = J('smiles/registry/smiles.json'), PA = J('layers/registry/paths.json');
const AG = Object.fromEntries(HV.agents.map((a) => [a.id, a]));
const page = readFileSync(join(HERE, 'trade_craft_programs.html'), 'utf8');
const scr = (id) => { const m = page.match(new RegExp(`<script[^>]*id="${id}"[^>]*>([\\s\\S]*?)</script>`)); return m ? m[1] : null; };
const I = JSON.parse(scr('prog-i18n').replace(/<\\\//g, '</'));
const LOCALES = readdirSync(join(ROOT, 'i18n/locales')).filter((f) => f.endsWith('.json')).map((f) => f.slice(0, -5)).sort();
const CAT = Object.fromEntries(LOCALES.map((l) => [l, J(`i18n/locales/${l}.json`)]));

/* ---- build and shell ---- */
let current = false; try { execFileSync('python3', [join(HERE, 'build_programs.py'), '--check'], { stdio: 'pipe' }); current = true; } catch { current = false; }
ok('the page is current with its builder and the registry (build_programs.py --check)', current);
ok('the page carries the registry stamp it was built from', page.includes(`<code data-stamp>${reg.source_stamp}</code>`));
ok('exactly one <h1>, and it is the translated page title', (page.match(/<h1[\s>]/g) || []).length === 1 && page.includes('<h1 data-i18n="prog.title">'));
ok('the site nav is present and marks this page current', /href="trade_craft_programs.html" aria-current="page"/.test(page));
ok('the saved-style head script runs before paint', page.indexOf('id="style-head-js"') > 0 && page.indexOf('id="style-head-js"') < page.indexOf('</head>'));

/* ---- honesty, up front ---- */
const hon = (page.match(/<section class="box honesty"[\s\S]*?<\/section>/) || [''])[0];
ok('the honesty box comes before the pathways and carries the five translated notes',
  page.indexOf('id="prog-honesty"') < page.indexOf('id="prog-k12"') && ['prog.honesty.proposed', 'prog.honesty.un', 'prog.honesty.accredited', 'prog.honesty.play', 'prog.honesty.derived'].every((k) => hon.includes(`data-i18n="${k}"`)));
const EN = I.en.strings;
ok('it states: districts, programmes and organisations are PROPOSED (no agreement, grant or funding)', /PROPOSED/.test(EN['prog.honesty.proposed']) && /no agreement, grant or funding exists/.test(EN['prog.honesty.proposed']) && hon.includes(esc(EN['prog.honesty.proposed'])));
ok('it states: the UN path is PROPOSED and not affiliated with or endorsed by the United Nations', /PROPOSED/.test(EN['prog.honesty.un']) && /not affiliated with or endorsed by the United Nations/.test(EN['prog.honesty.un']) && hon.includes(esc(EN['prog.honesty.un'])));
ok('it states: nothing is accredited; lessons are unverified general practice', /Nothing here is accredited/.test(EN['prog.honesty.accredited']) && /unverified general practice/.test(EN['prog.honesty.accredited']) && hon.includes(esc(EN['prog.honesty.accredited'])));
ok('it states: games, coins and badges are play', /^Games, coins and badges are play/.test(EN['prog.honesty.play']) && hon.includes(esc(EN['prog.honesty.play'])));
ok('every proposed district is shown with its registry status, verbatim', reg.districts.every((d) => hon.includes(esc(d.district)) && hon.includes(esc(d.status))));

/* ---- K-12 pathways ---- */
const bandSec = (b) => (page.match(new RegExp(`<section class="band box" data-band="${b}"[\\s\\S]*?</section>`)) || [''])[0];
ok('one pathway section per band, in the schools order', JSON.stringify([...page.matchAll(/<section class="band box" data-band="([^"]+)"/g)].map((m) => m[1])) === JSON.stringify(reg.bands.map((b) => b.band)));
ok('each band quotes its offer verbatim and counts from the registry', reg.bands.every((b) => { const s = bandSec(b.band);
  return s.includes(esc(b.offer)) && s.includes(`data-i18n-n="prog.count.courses" data-n="${b.counts.courses}"`) && s.includes(`data-i18n-n="prog.count.lessons" data-n="${b.counts.lessons}"`)
    && s.includes(`data-i18n-n="prog.count.blocks" data-n="${b.counts.blocks}"`) && s.includes(`data-i18n-n="prog.count.cards" data-n="${b.counts.cards}"`); }));
ok('the four program steps run in order in every band: meet, courses, modules, Cognition.X', reg.bands.every((b) => { const s = bandSec(b.band);
  const at = ['prog.step.meet', 'prog.step.courses', 'prog.step.modules', 'prog.step.cx'].map((k) => s.indexOf(`data-i18n="${k}"`)); return at.every((x, i) => x > 0 && (i === 0 || x > at[i - 1])); }));
ok('every band lists its courses, modules and Cognition.X modules in the registry order', reg.bands.every((b) => { const s = bandSec(b.band);
  const got = (re) => [...s.matchAll(re)].map((m) => m[1]);
  return JSON.stringify(got(/data-course="([^"]+)"/g)) === JSON.stringify(b.courses.map((c) => c.course)) && JSON.stringify(got(/data-module="([^"]+)"/g)) === JSON.stringify(b.modules.map((m) => m.module))
    && JSON.stringify(got(/data-cx="([^"]+)"/g)) === JSON.stringify(b.cognitionx.map((x) => x.cx_module)); }));
ok('every pathway lesson links to its supplement on the Courses page', reg.bands.every((b) => b.courses.every((c) => c.lessons.every((l) => bandSec(b.band).includes(`href="trade_craft_courses.html?lesson=${l.id}#course-sup"`)))));
ok('the meet step names the allow-listed advisors and counts the parish figures by role', reg.bands.every((b) => { const s = bandSec(b.band);
  return b.agents.filter((a) => AG[a].kind === 'advisor').every((a) => s.includes(esc(AG[a].name))) && s.includes(`data-n="${b.agents.length}"`); }));
ok('Cognition.X blocks are quoted verbatim (theme and transfer check) with the CC BY 4.0 attribution', reg.bands.every((b) => b.cognitionx.every((x) => bandSec(b.band).includes(esc(x.first.theme)) && bandSec(b.band).includes(esc(x.first.transfer_check))))
  && page.includes(esc(reg.attribution.license_url)) && page.includes(esc(reg.attribution.text)) && reg.bands.every((b) => bandSec(b.band).includes('data-i18n="prog.cx.attr"')));

/* ---- teacher program cards ---- */
const cards = [...page.matchAll(/<article class="pcard" data-card="([^"]+)" data-band="([^"]+)">([\s\S]*?)<\/article>/g)];
ok(`one card per registry card, in order (${reg.cards.length})`, JSON.stringify(cards.map((m) => m[1])) === JSON.stringify(reg.cards.map((c) => c.id)));
const CARD = Object.fromEntries(cards.map((m) => [m[1], m[3]]));
ok('every card shows what the class does, verbatim from the registry', reg.cards.every((c) => c.does.every((d) => CARD[c.id].includes(esc(d.text)))));
ok('every card names its greeter and quotes the greeter\'s play-safe line verbatim', reg.cards.every((c) => CARD[c.id].includes(`data-agent="${c.greeter.id}"`) && CARD[c.id].includes(esc(c.greeter.opener.text)) && AG[c.greeter.id].k12));
ok('every card links to the Hive in classroom mode, where the voice starts muted; the page says so', reg.cards.every((c) => CARD[c.id].includes('href="trade_craft_hive.html?classroom=1"'))
  && /starts muted/.test(EN['prog.card.muted']) && page.includes('data-i18n="prog.card.muted"'));
ok('every card place links to a real page, and K-5 / 6-8 cards show no simulator seat', reg.cards.every((c) => c.where.every((w) => CARD[c.id].includes(`href="${esc(w.href.slice(4))}"`) && existsSync(join(HERE, w.href.slice(4).split('?')[0]))))
  && cards.filter((m) => m[2] === 'K-5' || m[2] === '6-8').every((m) => !/[?&]sim=/.test(m[3])));

/* ---- sectors ---- */
const secs = [...page.matchAll(/<article class="sector box" data-sector="([^"]+)">([\s\S]*?)<\/article>/g)];
const SEC = Object.fromEntries(secs.map((m) => [m[1], m[2]]));
ok('four sector cards in the registry order, each tagged PROPOSED', JSON.stringify(secs.map((m) => m[1])) === JSON.stringify(reg.sectors.map((s) => s.id)) && secs.every((m) => m[2].includes('data-i18n="prog.sec.status"')) && EN['prog.sec.status'] === 'PROPOSED');
ok('community health keeps "not medical or dental advice", quoted from the Smiles registry', (SEC['community-health'] || '').includes(esc(SM.disclaimer)) && /not medical or dental advice/.test(SM.disclaimer));
const SMILES_OK = [SM.place_note, SM.name, ...SM.programmes.map((p) => p.name), CAT.en.strings['nav.page.smiles']].map(esc).sort((a, b) => b.length - a.length);
{ let rest = page; for (const s of SMILES_OK) rest = rest.split(s).join('');
  ok('Unspoken Smiles is named only as the existing pages describe it (every mention is a Smiles registry string or the site nav label)', !/Unspoken Smiles/i.test(rest) && page.includes(esc(SM.place_note))); }
ok('humanitarian training quotes the UN disclaimer and shows the UN path as PROPOSED', (SEC['humanitarian-training'] || '').includes(esc(PA.un_disclaimer))
  && (SEC['humanitarian-training'] || '').includes(esc(reg.sectors[2].paths[0].label)) && reg.sectors[2].paths[0].status === 'PROPOSED' && (SEC['humanitarian-training'] || '').includes('>PROPOSED<'));
ok('every sector lists its scenarios, halls, agents and worlds from the registry; an empty list states its rule', reg.sectors.every((s) => {
  const h = SEC[s.id] || '';
  return s.scenarios.every((x) => h.includes(esc(x.title || x.id))) && s.halls.every((x) => h.includes(esc(x.hall_name))) && s.agents.every((a) => h.includes(esc(AG[a].name)))
    && s.worlds.every((w) => h.includes(`href="${esc(w.href)}"`) && existsSync(join(HERE, w.href)))
    && Object.values(s.empty_why || {}).every((why) => h.includes(esc(why)));
}));
ok('restoration organisations are shown verbatim and the not-affiliated note is quoted', reg.sectors[3].sites.every((x) => (SEC['environmental-restoration'] || '').includes(esc(x.org)))
  && (SEC['environmental-restoration'] || '').includes(esc(reg.sectors[3].quotes[0].text)));

/* ---- i18n ---- */
const keys = [...new Set([...page.matchAll(/data-i18n(?:-n)?="([^"]+)"/g)].map((m) => m[1]))];
ok(`every chrome key on the page (${keys.length}) exists, non-empty, in all 8 shipped locales; Arabic is right-to-left`,
  LOCALES.length === 8 && keys.every((k) => LOCALES.every((l) => typeof I[l].strings[k] === 'string' && I[l].strings[k].trim() && CAT[l].strings[k] === I[l].strings[k])) && I.ar.dir === 'rtl',
  keys.filter((k) => !LOCALES.every((l) => I[l] && I[l].strings[k])));
ok('the nav label nav.page.programs exists in all 8 locales', LOCALES.every((l) => typeof CAT[l].strings['nav.page.programs'] === 'string' && CAT[l].strings['nav.page.programs'].trim()));
ok('the non-English chrome is translated, not copied (under 15% identical to English, every locale)', LOCALES.filter((l) => l !== 'en').every((l) => keys.filter((k) => I[l].strings[k] === EN[k]).length / keys.length < 0.15));
ok('every {n} placeholder survives in every locale', Object.keys(EN).filter((k) => EN[k].includes('{n}')).every((k) => LOCALES.every((l) => I[l].strings[k].includes('{n}'))));
ok('every translated honesty note keeps PROPOSED-strength wording (no locale drops the UN or proposed note)', LOCALES.every((l) => ['prog.honesty.proposed', 'prog.honesty.un', 'prog.honesty.accredited', 'prog.honesty.play'].every((k) => I[l].strings[k].length > 20)));

/* ---- what the page does not do ---- */
const own = scr('prog-page') || 'MISSING';
ok('the page\'s own script saves nothing, sends nothing and speaks nothing', !own.includes('MISSING') && !/localStorage|sessionStorage|indexedDB|fetch\(|XMLHttpRequest|sendBeacon|speechSynthesis|SpeechSynthesisUtterance|\.play\(/.test(own));
ok('no internal reference on the page (no scratchpad or /tmp path, no memory/ or console mention, no team codename)',
  !/\/tmp\/|scratchpad|memory\/|\bconsoles?\b|\bPROGRAMS\b|\bPATHWAYS\b|\bRESTORE\b|\bCOURSE\b|\bHIVE\b|\bAVATAR\b|\bK-12·|PROGRAMS·/.test(page));
ok('no model identifier and no claim of certification, accreditation or affiliation on the page', !/claude-|gpt-|\bopus\b|\bsonnet\b/i.test(page)
  && !/\b(is|are) (certified|accredited|affiliated)\b|\bcertified by\b|\baccredited by\b|\bin partnership with\b|\bfunded by\b/i.test(page.replace(/not affiliated|not accredited|Nothing here is accredited/gi, '')));
ok('links to the schools, classroom, courses, Hive, Smiles, parish and Bay pages, each a real file',
  ['trade_craft_schools.html', 'trade_craft_classroom.html', 'trade_craft_courses.html', 'trade_craft_hive.html', 'trade_craft_smiles.html', 'trade_craft_parishes.html', 'trade_craft_bay.html'].every((f) => page.includes(`href="${f}"`) && existsSync(join(HERE, f))));

/* ---- browser (opt-in) ---- */
const barg = process.argv.find((a) => a === '--browser' || a.startsWith('--browser='));
if (barg) {
  const { spawn } = await import('node:child_process');
  let base = barg.includes('=') ? barg.split('=').slice(1).join('=') : null, srv = null;
  if (!base) { const port = 18700 + (process.pid % 90); srv = spawn('python3', ['-m', 'http.server', String(port), '--bind', '127.0.0.1'], { cwd: HERE, stdio: 'ignore' });
    base = `http://127.0.0.1:${port}`; await new Promise((r) => setTimeout(r, 900)); }
  const { chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs');
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const errs = [];
  try {
    for (const vp of [{ width: 1440, height: 900, n: 'desktop' }, { width: 390, height: 844, n: 'phone' }]) {
      const ctx = await b.newContext({ viewport: { width: vp.width, height: vp.height } }), pg = await ctx.newPage();
      pg.on('pageerror', (e) => errs.push(vp.n + ': ' + e.message)); pg.on('console', (m) => { if (m.type() === 'error') errs.push(vp.n + ' console: ' + m.text()); });
      const reqs = []; pg.on('request', (r) => { if (!r.url().startsWith(base)) reqs.push(r.url()); });
      await pg.goto(base + '/trade_craft_programs.html?lang=en', { waitUntil: 'load' }); await pg.waitForFunction(() => window.__programsPage);
      const vis = () => [...document.querySelectorAll('article.pcard')].filter((c) => !c.hidden && c.getClientRects().length).length;
      const f = await pg.evaluate((vs) => { const vis = new Function('return (' + vs + ')()'); const P = window.__programsPage; P.show(''); const all = vis(); P.show('K-5'); const k5 = vis(), bandsShown = [...document.querySelectorAll('section.band')].filter((s) => !s.hidden).length;
        const n = document.querySelector('section.band[data-band="K-5"] [data-i18n-n="prog.count.cards"]').textContent; P.show(''); return { all, k5, bandsShown, n, P: { cards: P.cards, sectors: P.sectors, bands: P.bands } }; }, vis.toString());
      ok(`browser ${vp.n}: the band filter shows all ${f.all} cards, ${f.k5} for K-5 and one pathway ("${f.n}")`,
        f.all === reg.cards.length && f.k5 === reg.counts.cards_by_band['K-5'] && f.bandsShown === 1 && f.P.sectors === 4 && f.P.bands === 4 && f.n === `${reg.counts.cards_by_band['K-5']} cards`);
      ok(`browser ${vp.n}: no request leaves the page's origin (${reqs.length})`, reqs.filter((u) => !/fonts\.(googleapis|gstatic)\.com/.test(u)).length === 0, reqs);
      const ov = await pg.evaluate(() => { let o = document.documentElement.scrollWidth - window.innerWidth;
        document.querySelectorAll('#main *').forEach((el) => { const r = el.getBoundingClientRect(); if (r.width) o = Math.max(o, Math.round(r.right - window.innerWidth), Math.round(-r.left)); }); return o; });
      ok(`browser ${vp.n}: no horizontal scroll and nothing in the page body past the viewport edge (${ov} px)`, ov <= 0);
      await ctx.close();
    }
    const ctx = await b.newContext({ viewport: { width: 390, height: 844 } }), pg = await ctx.newPage();
    pg.on('pageerror', (e) => errs.push('ar: ' + e.message));
    await pg.goto(base + '/trade_craft_programs.html?lang=ar&band=9-10', { waitUntil: 'load' }); await pg.waitForFunction(() => window.__programsPage);
    const ar = await pg.evaluate(() => ({ dir: document.documentElement.dir, lang: document.documentElement.lang, h: document.querySelector('[data-i18n="prog.h.sectors"]').textContent,
      un: document.querySelector('[data-i18n="prog.honesty.un"]').textContent, band: document.getElementById('prog-band').value,
      shown: [...document.querySelectorAll('article.pcard')].filter((c) => !c.hidden && c.getClientRects().length).length, cnt: document.querySelector('section.band[data-band="9-10"] [data-i18n-n="prog.count.cards"]').textContent,
      ov: (() => { let o = document.documentElement.scrollWidth - window.innerWidth; document.querySelectorAll('#main *').forEach((el) => { const r = el.getBoundingClientRect(); if (r.width) o = Math.max(o, Math.round(r.right - window.innerWidth), Math.round(-r.left)); }); return o; })() }));
    ok(`browser ar (phone): right-to-left, translated headings and honesty, ?band=9-10 shows ${ar.shown} cards ("${ar.cnt}"), no horizontal scroll (${ar.ov} px)`,
      ar.dir === 'rtl' && ar.lang === 'ar' && ar.h === I.ar.strings['prog.h.sectors'] && ar.un === I.ar.strings['prog.honesty.un'] && ar.band === '9-10'
      && ar.shown === reg.counts.cards_by_band['9-10'] && ar.cnt === I.ar.strings['prog.count.cards'].replace('{n}', String(reg.counts.cards_by_band['9-10'])) && ar.ov <= 0, ar);
    await ctx.close();
  } finally { await b.close(); if (srv) srv.kill(); }
  ok('browser: zero page errors', errs.length === 0, errs);
}

console.log(`  (measured) page ${Math.round(page.length / 1024)} KB; ${reg.bands.length} pathways, ${cards.length} cards, ${secs.length} sectors; ${keys.length} chrome keys x ${LOCALES.length} locales`);
console.log(`web/test_programs: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
