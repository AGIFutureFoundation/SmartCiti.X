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
 * --pages=<a,b>  only the pages whose path contains one of these substrings
 *                (sections 1 and 1b; for iterating on a few pages)
 * --audit-only   run only section 1b, the two-viewport audit, and skip the rest
 * --no-audit     skip section 1b
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
const ONLY = arg('pages', '').split(',').map((x) => x.trim()).filter(Boolean);
const AUDIT_ONLY = args.includes('--audit-only');
const NO_AUDIT = args.includes('--no-audit');
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
  'console/trade_craft_console.html'].filter((u) => !ONLY.length || ONLY.some((o) => u.includes(o)));
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
for (const url of AUDIT_ONLY ? [] : PAGES) {
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

/* ============================== 1b. every page, audited at two viewports
   Named checks, each one line per page per viewport:
     overflow   no horizontal scroll (documentElement.scrollWidth > clientWidth)
     tap        links/buttons in the main content at least 24x24 CSS px
                (WCAG 2.5.8: inline links inside a sentence are exempt, and so is
                an undersized target whose centred 24x24 box touches no other target)
     focus      the first 10 elements reached with the Tab key show a focus
                indicator: computed outline or box-shadow differs from unfocused
     img-alt    every <img>/<input type=image>/<area> carries an alt attribute
     contrast   text meets WCAG AA (4.5:1 normal, 3:1 large = 24px, or 18.66px bold)
                against the effective background, composited walking up the tree;
                text over a canvas, video, image or background-image is skipped and
                the count of skipped runs is printed
     ids        no duplicate id attribute values
     names      every link/button has an accessible name
     warnings   no console warning (errors are already the "no page/console error" check);
                the headless software GPU's own "GL Driver Message" performance notes are
                counted and printed, not failed: they describe the test machine
     viewport   at the phone size the layout viewport is the device width (a page with
                no <meta name=viewport> lays out at 980px and is shrunk to fit)
   ids, names and img-alt do not depend on the viewport and run at the desktop size only. */
const VIEWPORTS = [['mobile', 390, 844], ['desktop', 1440, 900]];
const AUDIT_JS = () => {
  const out = {};
  const vw = document.documentElement.clientWidth;
  const desc = (e) => {
    if (!e || !e.tagName) return '?';
    let s = e.tagName.toLowerCase();
    if (e.id) s += '#' + e.id;
    else if (typeof e.className === 'string' && e.className.trim()) s += '.' + e.className.trim().split(/\s+/).slice(0, 2).join('.');
    const t = (e.getAttribute('aria-label') || e.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 28);
    return t ? `${s}"${t}"` : s;
  };
  const shown = (e) => {
    const r = e.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    for (let a = e; a && a.nodeType === 1; a = a.parentElement) {
      const cs = getComputedStyle(a);
      if (cs.visibility === 'hidden' || cs.display === 'none' || Number(cs.opacity) === 0) return false;
      if (a.getAttribute('aria-hidden') === 'true') return false;
    }
    return true;
  };
  const clipped = (e) => { // visually-hidden (sr-only) text
    for (let a = e; a && a.nodeType === 1; a = a.parentElement) {
      const cs = getComputedStyle(a);
      if ((cs.clip && cs.clip !== 'auto') || (cs.clipPath && cs.clipPath.startsWith('inset(50%'))) return true;
      const r = a.getBoundingClientRect();
      if (r.width <= 1 && r.height <= 1 && cs.overflow === 'hidden') return true;
    }
    return false;
  };
  /* overflow: the widest elements that stick out past the right edge */
  const sw = document.documentElement.scrollWidth;
  const wide = [];
  if (sw > vw) {
    for (const e of document.body.querySelectorAll('*')) {
      const r = e.getBoundingClientRect();
      if (r.right > vw + 1 && r.width > 0) {
        let inScroller = false;
        for (let a = e.parentElement; a && a !== document.body; a = a.parentElement) {
          const ox = getComputedStyle(a).overflowX;
          if (ox !== 'visible') { inScroller = true; break; }
        }
        if (!inScroller && !(e.parentElement && e.parentElement.getBoundingClientRect().right > vw + 1)) wide.push(`${desc(e)} right=${Math.round(r.right)}`);
      }
    }
  }
  out.overflow = { sw, vw, wide: wide.slice(0, 4) };
  /* tap targets */
  const root = document.querySelector('main') || document.body;
  const TSEL = 'a[href], button, [role=button], [role=link], summary, input[type=checkbox], input[type=radio], input[type=button], input[type=submit], select';
  const inChrome = (e) => !document.querySelector('main') && e.closest('nav, header, footer, [role=navigation]');
  const tgt = [...root.querySelectorAll(TSEL)].filter((e) => shown(e) && !inChrome(e)).map((e) => {
    const lab = (e.tagName === 'INPUT') && e.closest('label');
    const box = (lab && shown(lab) ? lab : e).getBoundingClientRect();
    return { e, box };
  });
  const inline = (e) => {
    if (e.tagName !== 'A') return false;
    const cs = getComputedStyle(e);
    if (!cs.display.startsWith('inline') || cs.display === 'inline-block' || cs.display === 'inline-flex') return false;
    const p = e.parentElement; if (!p) return false;
    const own = e.textContent.trim().length, all = p.textContent.trim().length;
    return all > own + 3; // sits inside running text
  };
  const sq = (b) => { const cx = b.left + b.width / 2, cy = b.top + b.height / 2;
    return { l: Math.min(b.left, cx - 12), r: Math.max(b.right, cx + 12), t: Math.min(b.top, cy - 12), b: Math.max(b.bottom, cy + 12) }; };
  const hit = (a, b) => a.l < b.r && b.l < a.r && a.t < b.b && b.t < a.b;
  const small = [];
  for (const x of tgt) {
    const b = x.box;
    if (b.width >= 24 && b.height >= 24) continue;
    if (inline(x.e)) continue;
    const me = sq(b);
    const crowd = tgt.some((y) => y !== x && !y.e.contains(x.e) && !x.e.contains(y.e) && hit(me, (y.box.width < 24 || y.box.height < 24) ? sq(y.box) : { l: y.box.left, r: y.box.right, t: y.box.top, b: y.box.bottom }));
    if (crowd) small.push(`${desc(x.e)} ${Math.round(b.width)}x${Math.round(b.height)}`);
  }
  out.tap = { n: tgt.length, small };
  /* images */
  out.imgAlt = [...document.querySelectorAll('img, input[type=image], area')].filter((e) => !e.hasAttribute('alt')).map(desc);
  /* duplicate ids */
  const seen = new Map();
  for (const e of document.querySelectorAll('[id]')) seen.set(e.id, (seen.get(e.id) || 0) + 1);
  out.ids = [...seen].filter(([, n]) => n > 1).map(([k, n]) => `#${k} x${n}`);
  /* accessible names */
  const nameOf = (e) => {
    const lb = e.getAttribute('aria-labelledby');
    if (lb) { const t = lb.split(/\s+/).map((i) => document.getElementById(i)?.textContent || '').join(' ').trim(); if (t) return t; }
    const al = (e.getAttribute('aria-label') || '').trim(); if (al) return al;
    if (e.tagName === 'INPUT') { if ((e.value || '').trim()) return e.value; if (e.labels && [...e.labels].some((l) => l.textContent.trim())) return 'label'; }
    const tx = (e.innerText || e.textContent || '').trim(); if (tx) return tx;
    const im = [...e.querySelectorAll('img[alt], svg title, [aria-label]')].map((i) => (i.getAttribute('alt') || i.getAttribute('aria-label') || i.textContent || '').trim()).join('');
    if (im) return im;
    return (e.getAttribute('title') || '').trim();
  };
  out.names = [...document.querySelectorAll('a[href], button, [role=button], [role=link], input[type=button], input[type=submit], input[type=reset]')]
    .filter((e) => e.getClientRects().length && !e.closest('[aria-hidden=true]') && !nameOf(e)).map(desc);
  /* contrast */
  const cv = document.createElement('canvas'); cv.width = cv.height = 1;
  const cx = cv.getContext('2d', { willReadFrequently: true });
  const cache = new Map();
  const rgba = (s) => { if (cache.has(s)) return cache.get(s);
    cx.clearRect(0, 0, 1, 1); cx.fillStyle = '#000'; cx.fillStyle = s; cx.fillRect(0, 0, 1, 1);
    const d = cx.getImageData(0, 0, 1, 1).data; const v = [d[0], d[1], d[2], d[3] / 255]; cache.set(s, v); return v; };
  const over = (top, bot) => { const a = top[3] + bot[3] * (1 - top[3]);
    if (a === 0) return [0, 0, 0, 0];
    return [0, 1, 2].map((i) => (top[i] * top[3] + bot[i] * bot[3] * (1 - top[3])) / a).concat(a); };
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const media = [...document.querySelectorAll('canvas, video, img, iframe')].filter((m) => { const r = m.getBoundingClientRect(); return r.width > 40 && r.height > 20; });
  const low = []; let checked = 0, skipped = 0;
  const done = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    if (!n.nodeValue.trim()) continue;
    const e = n.parentElement;
    if (!e || done.has(e)) continue; done.add(e);
    if (/^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE|OPTION|TITLE)$/.test(e.tagName) || e.closest('svg')) continue;
    if (!shown(e) || clipped(e)) continue;
    const cs = getComputedStyle(e);
    let fg = rgba(cs.color);
    if (fg[3] === 0) continue;
    const r = e.getBoundingClientRect(), mx = r.left + r.width / 2, my = r.top + r.height / 2;
    let bg = [0, 0, 0, 0], behind = null, anc = e;
    for (; anc; anc = anc.parentElement) {
      const as = getComputedStyle(anc);
      if (as.backgroundImage && as.backgroundImage !== 'none') { behind = `background-image on ${desc(anc).slice(0, 40)}`; break; }
      bg = over(bg, rgba(as.backgroundColor));
      if (bg[3] >= 0.99) break;
    }
    if (!behind) {
      const ctxEl = anc || document.documentElement;
      const m = media.find((m) => !e.contains(m) && ctxEl.contains(m) && !m.contains(e) && (() => { const q = m.getBoundingClientRect(); return mx >= q.left && mx <= q.right && my >= q.top && my <= q.bottom; })());
      if (m) behind = m.tagName.toLowerCase();
    }
    if (behind) { skipped++; continue; }
    if (bg[3] < 0.99) bg = over(bg, [255, 255, 255, 1]); // the canvas default
    if (fg[3] < 1) fg = over(fg, bg);
    const L1 = lum(fg), L2 = lum(bg), ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const px = parseFloat(cs.fontSize), bold = Number(cs.fontWeight) >= 700;
    const large = px >= 24 || (bold && px >= 18.66);
    const need = large ? 3 : 4.5;
    checked++;
    if (ratio + 0.005 < need) {
      const hex = (c) => '#' + c.slice(0, 3).map((v) => Math.round(v).toString(16).padStart(2, '0')).join('');
      low.push(`${desc(e)} ${ratio.toFixed(2)}:1<${need} (${hex(fg)} on ${hex(bg)}, ${px}px)`);
    }
  }
  out.contrast = { checked, skipped, low };
  /* focus: remember every tabbable element's unfocused outline and shadow */
  const TAB = 'a[href], button:not([disabled]), input:not([disabled]):not([type=hidden]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"]), iframe, [contenteditable=""], [contenteditable=true]';
  const style = (e) => { const s = getComputedStyle(e); return { o: s.outlineStyle === 'none' || parseFloat(s.outlineWidth) === 0 ? 'none' : `${s.outlineStyle} ${s.outlineWidth} ${s.outlineColor}`, b: s.boxShadow }; };
  window.__auditFocusBase = new Map([...document.querySelectorAll(TAB)].slice(0, 80).map((e) => [e, style(e)]));
  window.__auditStyle = style; window.__auditDesc = desc;
  return out;
};
const FOCUS_STEP = () => {
  const e = document.activeElement;
  if (!e || e === document.body) return null;
  const base = window.__auditFocusBase.get(e);
  const now = window.__auditStyle(e);
  const d = window.__auditDesc(e);
  if (!base) return { d, ok: now.o !== 'none' || (now.b !== 'none'), unknown: true };
  const ok = (now.o !== 'none' && now.o !== base.o) || now.b !== base.b;
  return { d, ok };
};
const clip = (a, n = 3) => a.slice(0, n).join('; ') + (a.length > n ? ` (+${a.length - n} more)` : '');
async function auditPage(url) {
  for (const [vname, w, h] of VIEWPORTS) {
    const tag = `${url} @${vname} ${w}x${h}`;
    let ctx;
    try {
      ctx = await browser.newContext({ viewport: { width: w, height: h }, isMobile: vname === 'mobile', hasTouch: false });
      const page = await ctx.newPage();
      const warns = []; let driver = 0;
      page.on('console', (m) => { if (m.type() !== 'warning') return;
        if (/GL Driver Message/.test(m.text())) driver++; else warns.push(m.text().slice(0, 140)); });
      await page.goto(`${BASE}/${url}`, { waitUntil: 'load', timeout: 60000 });
      await page.waitForTimeout(url.includes('3d') || url.includes('geomap') ? 3000 : 700);
      const a = await page.evaluate(AUDIT_JS);
      if (vname === 'mobile') check(`${tag} viewport`, a.overflow.vw === w,
        `layout viewport is ${a.overflow.vw}px on a ${w}px phone: no working <meta name="viewport" content="width=device-width">`);
      check(`${tag} overflow`, a.overflow.sw <= a.overflow.vw,
        `scrollWidth ${a.overflow.sw} > clientWidth ${a.overflow.vw}; sticking out: ${clip(a.overflow.wide) || '(no single element found)'}`);
      check(`${tag} tap (${a.tap.n} targets)`, a.tap.small.length === 0, `${a.tap.small.length} under 24x24 and crowded: ${clip(a.tap.small)}`);
      check(`${tag} contrast (${a.contrast.checked} text runs, ${a.contrast.skipped} over canvas/image skipped)`, a.contrast.low.length === 0,
        `${a.contrast.low.length} below AA: ${clip(a.contrast.low)}`);
      // AUDIT row 9 (UX): on a phone every visible site-nav control and every world mode button (.ctl .tc-btn) is a
      // 44 px tall tap target (comfort size, stricter than the 24 px rule above). 0.5 px tolerance for sub-pixel layout.
      if (vname === 'mobile') {
        const t44 = await page.evaluate(() => [...document.querySelectorAll('.sitenav a:not(.skip), .sitenav summary, .ctl .tc-btn')]
          .filter((e) => { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e);
            return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && !e.closest('[hidden],details:not([open])>:not(summary)'); })
          .map((e) => ({ d: window.__auditDesc ? window.__auditDesc(e) : e.tagName, h: e.getBoundingClientRect().height }))
          .filter((x) => x.h < 43.5).map((x) => `${x.d} ${Math.round(x.h)}px`));
        check(`${tag} tap44 (nav + world mode buttons)`, t44.length === 0, `${t44.length} under 44 px tall: ${clip(t44)}`);
      }
      if (vname === 'desktop') {
        check(`${tag} img-alt`, a.imgAlt.length === 0, `${a.imgAlt.length} without alt: ${clip(a.imgAlt)}`);
        check(`${tag} ids`, a.ids.length === 0, `duplicate ids: ${clip(a.ids, 6)}`);
        check(`${tag} names`, a.names.length === 0, `${a.names.length} links/buttons without an accessible name: ${clip(a.names)}`);
      }
      const noRing = []; const seenF = new Set(); let reached = 0;
      await page.evaluate(() => { document.activeElement && document.activeElement.blur && document.activeElement.blur(); window.scrollTo(0, 0); });
      for (let i = 0; i < 10; i++) {
        await page.keyboard.press('Tab');
        const f = await page.evaluate(FOCUS_STEP);
        if (!f || seenF.has(f.d)) continue;
        seenF.add(f.d); reached++;
        if (!f.ok) noRing.push(f.d);
      }
      check(`${tag} focus (${reached} tab stops)`, noRing.length === 0, `${noRing.length} with no outline/box-shadow change on focus: ${clip(noRing)}`);
      check(`${tag} warnings${driver ? ` (${driver} software-GPU driver notes not counted)` : ''}`, warns.length === 0, `${warns.length} console warning(s): ${clip([...new Set(warns)], 2)}`);
      // AUDIT row 12 (UX): a style saved on another page is applied here on load (<html data-style>).
      // Only pages that carry the nav's Style menu promise to remember a style (the console app has none).
      if (vname === 'desktop' && await page.evaluate(() => !!document.querySelector('[data-sitenav-style]'))) {
        await page.evaluate(() => { try { localStorage.setItem('tc-style', 'midnight'); } catch (e) { /* storage blocked */ } });
        await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 });
        const ds = await page.evaluate(() => document.documentElement.getAttribute('data-style'));
        check(`${tag} saved style applies (tc-style=midnight -> data-style)`, ds === 'midnight', `data-style is ${ds}`);
      }
    } catch (e) { fail(`${tag} audit runs`, e.message.split('\n')[0]); }
    finally { if (ctx) await ctx.close(); }
  }
}
if (!NO_AUDIT) for (const url of PAGES) await auditPage(url);

if (!AUDIT_ONLY) {
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
      const by = (e.message.match(/<(?:div|button|span|a)\b[^>]*class="([^"]*)"[^>]*>([^<]*)<\/(?:div|button|span|a)> intercepts pointer events/) || []);
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

} // !AUDIT_ONLY

await browser.close();
const bad = results.filter((r) => !r.ok);
console.log(`\n${results.length - bad.length} ok, ${bad.length} FAIL (work files in ${WORK})`);
if (JSON_OUT) console.log(JSON.stringify({ base: BASE, root: ROOT, results }, null, 1));
process.exit(bad.length ? 1 : 0);
