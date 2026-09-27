#!/usr/bin/env node
/**
 * Browser smoke: every page as a user meets it, and the round trips between
 * the pages and the command-line verifiers.
 *
 *   node web/smoke.mjs [--base=http://127.0.0.1:8821] [--root=<tree>] [--shots=<dir>] [--json]
 *
 * --base   the server holding the tree (serve a FROZEN copy: `git archive HEAD | tar -x`)
 * --root   the tree the verifiers run from and the page list is read from
 *          (default: this repo). Point it at the frozen copy the server serves.
 * --shots  write the wiki screenshots (wiki/img/process-*.png names) into this dir
 * --json   print one JSON summary at the end as well
 *
 * Every step prints one line, `ok <what>` or `FAIL <what>: <reason>`, and the
 * process exits 1 on any FAIL. Nothing here fixes a page; it reports.
 *
 * The data injected into localStorage is SYNTHETIC. It is the fixture log
 * sessions/fixture/log.json (a tc-training array exactly as web/build_3d.py's
 * recordEpisode() writes it), a tc-progress record shaped as build_3d.py's
 * saveProg() writes it, and a tc-identity label record shaped as
 * web/build_auth.py's writeIdentity() writes it, labelled
 * "smoke - not a learner". No learner did any of it.
 */
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { readFileSync, writeFileSync, readdirSync, mkdirSync, existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { mkdtempSync } from 'node:fs';

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const arg = (k, d) => { const h = args.find((a) => a.startsWith(`--${k}=`)); return h ? h.slice(k.length + 3) : d; };
const BASE = arg('base', 'http://127.0.0.1:8821').replace(/\/$/, '');
const ROOT = resolve(arg('root', join(HERE, '..')));
const SHOTS = arg('shots', null);
const JSON_OUT = args.includes('--json');
const CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const LABEL = 'smoke - not a learner';
const WORK = mkdtempSync(join(tmpdir(), 'tc-smoke-'));
if (SHOTS) mkdirSync(SHOTS, { recursive: true });

const results = [];
const ok = (what) => { results.push({ ok: true, what }); console.log(`ok ${what}`); };
const fail = (what, why) => { results.push({ ok: false, what, why }); console.log(`FAIL ${what}: ${why}`); };
const check = (what, cond, why) => (cond ? ok(what) : fail(what, why));

/* ------------------------------------------------------------- the pages */
const PAGES = ['index.html',
  ...readdirSync(join(ROOT, 'web')).filter((f) => f.endsWith('.html')).sort().map((f) => `web/${f}`),
  'console/trade_craft_console.html'];
/* pages allowed to carry no single <h1>, each with its reason. Empty: none has
   documented one, so every page is held to exactly one. */
const H1_EXEMPT = {};

/* -------------------------------------------------------- synthetic data */
const reg = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));
const TRAINING_KEY = reg('training/registry/training.json').storage.key;
const IDENTITY_KEY = reg('auth/registry/auth.json').storage.identity_key;
const PROGRESS_KEY = 'tc-progress'; // web/build_3d.py PROG_KEY
const fixture = reg('sessions/fixture/log.json');
const TRAINING = fixture.episodes; // the bare array recordEpisode() keeps
const firstSim = TRAINING.find((e) => e.kind === 'sim' && e.actor === 'human');
const PROGRESS = { // saveProg(): { stations, sims: {id: {runs, passed, best}}, tools, walk }
  stations: [],
  sims: { [firstSim.sim]: { runs: 2, passed: true, best: 61.5 } },
  tools: {},
  walk: { [firstSim.sim]: 1 },
};
// build_auth.py writeIdentity(): { v, method, label, set_at, authenticates: false }; the one
// configured method of kind local-label in auth/registry/auth.json
const IDENTITY_METHOD = Object.entries(reg('auth/registry/auth.json').methods)
  .find(([, v]) => v.kind === 'local-label' && v.configured === true)[0];
const IDENTITY = { v: 1, method: IDENTITY_METHOD, label: LABEL, set_at: '2026-09-27T00:00:00.000Z', authenticates: false };
const seed = (page, store) => page.addInitScript((s) => {
  if (sessionStorage.getItem('__smoke_seeded')) return;
  localStorage.clear();
  for (const [k, v] of Object.entries(s)) localStorage.setItem(k, v);
  sessionStorage.setItem('__smoke_seeded', '1');
}, store);
const STORE = { [TRAINING_KEY]: JSON.stringify(TRAINING), [PROGRESS_KEY]: JSON.stringify(PROGRESS), [IDENTITY_KEY]: JSON.stringify(IDENTITY) };

/* ----------------------------------------------------------- the browser */
const browser = await chromium.launch({ executablePath: CHROME, args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
async function open(url, { store = null, settle = 1500 } = {}) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 }, acceptDownloads: true });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console.error: ' + m.text() + (m.location()?.url ? ' @ ' + m.location().url : '')); });
  page.on('requestfailed', (r) => { if (r.url().startsWith(BASE)) errors.push('requestfailed: ' + r.url() + ' ' + (r.failure()?.errorText || '')); });
  if (store) await seed(page, store);
  await page.goto(`${BASE}/${url}`, { waitUntil: 'load', timeout: 60000 });
  await page.waitForTimeout(settle);
  return { ctx, page, errors };
}
const errLine = (errors) => errors.slice(0, 4).join(' | ') + (errors.length > 4 ? ` (+${errors.length - 4} more)` : '');
const shot = async (name, target, full = false) => {
  if (!SHOTS) return;
  const path = join(SHOTS, name);
  if (target.screenshot && target.goto === undefined) await target.screenshot({ path });
  else await target.screenshot({ path, fullPage: full });
  console.log(`   shot ${name}`);
};

/* ================================================== 1. every page, loaded */
const fetched = new Map();
for (const url of PAGES) {
  let o;
  try { o = await open(url, { settle: url.includes('3d') || url.includes('geomap') ? 4000 : 1500 }); }
  catch (e) { fail(`${url} loads`, e.message); continue; }
  const { page, errors, ctx } = o;
  const meta = await page.evaluate(() => ({
    lang: document.documentElement.getAttribute('lang'),
    title: document.title.trim(),
    h1: document.querySelectorAll('h1').length,
    refs: [...document.querySelectorAll('[href],[src]')].map((e) => e.getAttribute(e.hasAttribute('src') ? 'src' : 'href'))
      .filter((r) => r && !/^(#|mailto:|javascript:|data:|blob:|tel:)/.test(r))
      .map((r) => { try { return new URL(r, location.href).href; } catch (e) { return null; } }).filter(Boolean),
  }));
  check(`${url} lang`, !!meta.lang, '<html> has no lang attribute');
  check(`${url} title`, !!meta.title, 'empty <title>');
  check(`${url} one h1`, meta.h1 === 1 || url in H1_EXEMPT, `${meta.h1} <h1> elements and no documented reason`);
  const local = [...new Set(meta.refs.filter((r) => r.startsWith(BASE + '/')).map((r) => r.split('#')[0].split('?')[0]))];
  const bad = [];
  for (const r of local) {
    if (!fetched.has(r)) { let s; try { s = (await fetch(r)).status; } catch (e) { s = String(e.message); } fetched.set(r, s); }
    if (fetched.get(r) !== 200) bad.push(`${r.slice(BASE.length + 1)} -> ${fetched.get(r)}`);
  }
  check(`${url} local links (${local.length})`, bad.length === 0, bad.join(', '));
  if (url === 'web/trade_craft_3d.html') {
    const hasHook = await page.evaluate(() => typeof window.__tc3dDo === 'function');
    check(`${url} __tc3dDo hook present`, hasHook, 'window.__tc3dDo is not a function');
    for (const v of ['region', 'campus', 'hall', 'avatar', 'sim', 'restoration']) {
      const before = errors.length;
      let thrown = null;
      try { await page.evaluate((v) => window.__tc3dDo('view', v), v); await page.waitForTimeout(2500); }
      catch (e) { thrown = e.message.split('\n')[0]; }
      const nu = errors.slice(before);
      check(`${url} view ${v}`, thrown === null && nu.length === 0, thrown || errLine(nu));
      if (v === 'region') errors.length = before; // counted under the view line
      if (v === 'restoration') await shot('process-3d-restoration.png', page);
      if (v === 'sim') await shot('process-3d-sim.png', page);
    }
  }
  if (url === 'index.html') await shot('process-front-door.png', page); // the first screen; the full page is 10k px tall
  check(`${url} no page/console error`, errors.length === 0, errLine(errors));
  await ctx.close();
}

/* ================================== 2. end-to-end: pages <-> the verifiers */
const node = (script, file) => {
  const r = spawnSync(process.execPath, [join(ROOT, script), file], { cwd: ROOT, encoding: 'utf8' });
  return { code: r.status, out: (r.stdout || '') + (r.stderr || '') };
};
const failLines = (out) => out.split('\n').filter((l) => l.startsWith('FAIL')).slice(0, 3).join(' | ');

// (a) progress -> completion/verify.mjs
{
  const { ctx, page, errors } = await open('web/trade_craft_progress.html', { store: STORE, settle: 2500 });
  const idText = await page.evaluate((L) => document.body.innerText.includes(L), LABEL);
  check('(a) progress page shows the synthetic label visibly', idText, `"${LABEL}" not in the page text`);
  const btn = page.locator('#expRecord');
  const enabled = await btn.count() && await btn.isEnabled();
  check('(a) progress completion export is enabled on the injected record', enabled, '#expRecord missing or disabled');
  if (enabled) {
    /* the sticky hall picker (.toolbar, position:sticky) lies over the top
       of any element crop; unstick it for the two section captures only */
    await page.addStyleTag({ content: '.toolbar{position:static !important}' });
    await page.locator('#completion').scrollIntoViewIfNeeded();
    await shot('process-progress-completion.png', page.locator('#completion'));
    const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 15000 }), btn.click()]);
    const file = join(WORK, dl.suggestedFilename());
    await dl.saveAs(file);
    const rec = JSON.parse(readFileSync(file, 'utf8'));
    check('(a) completion record carries the synthetic label', rec.identity && rec.identity.claimed === LABEL,
      `identity.claimed = ${JSON.stringify(rec.identity && rec.identity.claimed)}`);
    const v = node('completion/verify.mjs', file);
    check('(a) node completion/verify.mjs <export> exits 0', v.code === 0, `exit ${v.code}: ${failLines(v.out)}`);
    const hex = rec.digest.hex;
    rec.digest.hex = (hex[0] === '0' ? '1' : '0') + hex.slice(1);
    const bent = join(WORK, 'completion-bent.json');
    writeFileSync(bent, JSON.stringify(rec, null, 1));
    const vb = node('completion/verify.mjs', bent);
    check('(a) one flipped digest byte: verify exits 1 naming digest', vb.code === 1 && /FAIL[^\n]*digest/.test(vb.out),
      `exit ${vb.code}: ${failLines(vb.out) || 'no FAIL line names digest'}`);
  }
  // (c) sessions on the same page
  const sess = await page.evaluate(() => ({
    state: document.querySelector('#sessions')?.getAttribute('data-sessions'),
    rows: document.querySelectorAll('#sessions [data-session]').length,
    table: !!document.querySelector('#sessions table'),
  }));
  check('(c) sessions section renders a table from the injected log', sess.state === 'read' && sess.table && sess.rows > 0,
    `data-sessions=${sess.state}, table=${sess.table}, rows=${sess.rows}`);
  const logFile = join(WORK, 'tc-training.json');
  writeFileSync(logFile, JSON.stringify(TRAINING));
  const vs = node('sessions/verify.mjs', logFile);
  const m = vs.out.match(/rollups: (\d+) session/);
  const cli = m ? Number(m[1]) : null;
  check('(c) node sessions/verify.mjs on the same log exits 0', vs.code === 0, `exit ${vs.code}: ${failLines(vs.out)}`);
  check(`(c) page session rows (${sess.rows}) == sessions/verify.mjs count (${cli})`, cli === sess.rows, 'counts differ');
  await page.locator('#sessions').scrollIntoViewIfNeeded();
  await shot('process-progress-sessions.png', page.locator('#sessions'));
  check('(a/c) progress page: no page/console error with the injected record', errors.length === 0, errLine(errors));
  await ctx.close();
}

// (b) contribute -> contrib/verify.mjs
{
  const { ctx, page, errors } = await open('web/trade_craft_contribute.html', { store: STORE, settle: 2000 });
  const idText = await page.evaluate((L) => document.body.innerText.includes(L), LABEL);
  check('(b) contribute page shows the synthetic label visibly', idText, `"${LABEL}" not in the page text`);
  const boxes = page.locator('input[data-scope]');
  const n = await boxes.count();
  check(`(b) contribute page offers consent scopes (${n})`, n > 0, 'no input[data-scope]');
  if (n > 0) {
    const scope = await boxes.first().getAttribute('data-scope');
    await boxes.first().check();
    await page.waitForTimeout(300);
    const btn = page.locator('#expPackage');
    const enabled = await btn.isEnabled();
    check('(b) export enabled with one scope ticked', enabled, '#expPackage stays disabled');
    await page.evaluate(() => document.querySelector('#consent').scrollIntoView({ block: 'start' }));
    await page.waitForTimeout(300);
    await shot('process-contribute.png', page);
    if (enabled) {
      const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 15000 }), btn.click()]);
      const file = join(WORK, dl.suggestedFilename());
      await dl.saveAs(file);
      const pkg = JSON.parse(readFileSync(file, 'utf8'));
      const v = node('contrib/verify.mjs', file);
      check(`(b) node contrib/verify.mjs <export, scope ${scope}> exits 0`, v.code === 0, `exit ${v.code}: ${failLines(v.out)}`);
      const all = await boxes.evaluateAll((bs) => bs.map((b) => b.getAttribute('data-scope')));
      const path = JSON.stringify(pkg).includes('"scope"') ? 'consent.scope' : null;
      if (pkg.consent && Array.isArray(pkg.consent.scope) && all.length > 1) {
        pkg.consent.scope = all;
        const wide = join(WORK, 'contrib-widened.json');
        writeFileSync(wide, JSON.stringify(pkg, null, 1));
        const vw = node('contrib/verify.mjs', wide);
        check('(b) scope widened without re-digesting: verify fails by name', vw.code === 1 && /^FAIL \S+/m.test(vw.out),
          `exit ${vw.code}: ${failLines(vw.out) || 'no FAIL line'}`);
        if (vw.code === 1) console.log(`   named: ${failLines(vw.out)}`);
      } else fail('(b) widen the scope', `package has no consent.scope array (found ${path}) or only one scope exists`);
    }
  }
  check('(b) contribute page: no page/console error with the injected record', errors.length === 0, errLine(errors));
  await ctx.close();
}

// (d) worksites and spaces draw every plan in their registry
for (const [url, regPath, list, name] of [
  ['web/trade_craft_worksites.html', 'worksites/registry/worksites.json', 'sites', 'process-worksites.png'],
  ['web/trade_craft_spaces.html', 'spaces/registry/spaces.json', 'spaces', 'process-spaces.png']]) {
  const { ctx, page, errors } = await open(url);
  const want = reg(regPath)[list].length;
  const got = await page.evaluate(() => [...document.querySelectorAll('svg.plan')].filter((s) => s.getBoundingClientRect().width > 0).length);
  check(`(d) ${url} renders every plan (${got} visible svg.plan of ${want} in ${regPath})`, got === want, `${got} != ${want}`);
  check(`(d) ${url} no page/console error`, errors.length === 0, errLine(errors));
  /* show a plan, not the header: bring the first plan's own card to the top */
  await page.evaluate(() => { const sv = document.querySelector('svg.plan');
    (sv.closest('section, article, details') || sv).scrollIntoView({ block: 'start' }); });
  await page.waitForTimeout(400);
  await shot(name, page, false);
  await ctx.close();
}

/* =============================================== 3. the remaining shots */
{
  const { ctx, page, errors } = await open('web/trade_craft_map.html');
  const hall = page.locator('.hall').first();
  if (await hall.count()) {
    await hall.click();
    await page.waitForTimeout(800);
    const det = await page.evaluate(() => {
      const d = document.querySelector('#detail'); if (!d) return null;
      const r = d.getBoundingClientRect();
      return { text: d.innerText.trim().length, top: Math.round(r.top), vh: innerHeight };
    });
    check('map: first hall click fills the #detail training panel', det && det.text > 0, `#detail ${JSON.stringify(det)}`);
    check('map: the panel the click opened is in view', det && det.top < det.vh,
      `#detail starts at y=${det && det.top}, below the ${det && det.vh}px viewport: the click shows nothing but an outline`);
    await page.evaluate(() => document.querySelector('#detail').scrollIntoView({ block: 'start' }));
    await page.waitForTimeout(400);
    await shot('process-map-layers.png', page);
  } else fail('map: first hall clicks', 'no .hall element');
  check('map: no error after hall click', errors.length === 0, errLine(errors));
  await ctx.close();
}
{
  const { ctx, page, errors } = await open('web/trade_craft_interactive.html');
  const t = page.locator('input[data-l="lessons"]');
  if (await t.count()) {
    if (!(await t.isChecked())) await t.check();
    await page.waitForTimeout(600);
    const on = await page.evaluate(() => document.body.classList.contains('L-lessons'));
    check('interactive: lessons layer on', on, 'body lacks L-lessons after ticking');
    await shot('process-interactive-lessons.png', page);
  } else fail('interactive: lessons layer toggle', 'no input[data-l="lessons"]');
  check('interactive: no error with lessons on', errors.length === 0, errLine(errors));
  await ctx.close();
}
{
  const { ctx, page, errors } = await open('web/trade_craft_geomap.html', { settle: 6000 });
  const drawn = await page.evaluate(() => {
    const c = document.querySelector('canvas.maplibregl-canvas') || document.querySelector('canvas');
    if (!c) return 'no canvas';
    const gl = c.getContext('webgl2') || c.getContext('webgl');
    return gl ? 'webgl' : 'no gl context';
  });
  /* a user clicks what is on top: try each campus marker with a real click,
     and name every one another marker covers */
  const markers = page.locator('.campus-marker');
  const nm = await markers.count();
  const covered = [];
  let opened = null;
  for (let i = 0; i < nm && opened === null; i++) {
    const mk = markers.nth(i);
    const name = (await mk.textContent()).trim();
    try { await mk.click({ timeout: 3000 }); }
    catch (e) {
      const by = (e.message.match(/<div[^>]*class="([^"]*)"[^>]*>([^<]*)<\/div> intercepts pointer events/) || []);
      covered.push(`${name} (covered by .${(by[1] || '?').split(' ')[0]} "${(by[2] || '').slice(0, 40)}")`);
      continue;
    }
    await page.waitForTimeout(1200);
    if (await page.locator('.maplibregl-popup').count()) opened = name;
  }
  check(`geomap: every campus marker is clickable (${nm - covered.length}/${nm})`, covered.length === 0, covered.join('; '));
  check('geomap: a campus marker click opens a popup', opened !== null, `no .maplibregl-popup after clicking campus markers (canvas: ${drawn})`);
  if (opened !== null) { console.log(`   popup: ${opened}`); await shot('process-geomap-rollups.png', page); }
  check('geomap: no error', errors.length === 0, errLine(errors));
  await ctx.close();
}

await browser.close();
const bad = results.filter((r) => !r.ok);
console.log(`\n${results.length - bad.length} ok, ${bad.length} FAIL (work files in ${WORK})`);
if (JSON_OUT) console.log(JSON.stringify({ base: BASE, root: ROOT, results }, null, 1));
process.exit(bad.length ? 1 : 0);
