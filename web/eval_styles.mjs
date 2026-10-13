#!/usr/bin/env node
/**
 * Style audit: text contrast on EVERY page, in EVERY site style, in BOTH schemes,
 * measured in a real browser from the colours the page actually renders.
 *
 * Why: design_kit.STYLES asserts the style TOKENS (ink/plate, ink/panel, ...) at
 * import, and web/test_nav.mjs recomputes the nav from shipped CSS. Neither loads a
 * page. A token can pass while a page paints text with a literal, an inherited
 * colour, an opacity or a translucent panel that the token table never sees
 * (wave 3 smoke found a nav at 1:1 in light mode, a Launch button at 1.02:1 and
 * badges at 4.21:1). This eval renders each page and measures what is there.
 *
 *   node web/eval_styles.mjs --base=http://127.0.0.1:<port> [--root=<tree>]
 *        [--pages=<a,b>] [--styles=<a,b>] [--schemes=dark,light] [--json=<file>]
 *
 * --base    the server holding a FROZEN tree (`git archive HEAD | tar -x`); this
 *           script serves nothing itself.
 * --root    tree the page list is read from (web/sitenav.py PAGES); default this repo.
 * --pages   only pages whose path contains one of these substrings (split a full
 *           sweep across runs; each run reuses ONE browser).
 * --json    write the report here (merged by key with any report already there, so
 *           split runs accumulate into one file).
 *
 * How the style is set: before any page script runs, an init script writes
 * localStorage['tc-style'] (the switcher's storage key, THEME_CONTRACT 6) and the
 * context emulates prefers-color-scheme. Pages that carry the Style menu but not
 * STYLE_HEAD_JS (verify, signin - by design) do not read storage; for those the
 * eval checks the menu's radio, which is exactly what a visitor does, and the
 * report says `applied: "radio"`.
 *
 * What is measured: every visible, non-clipped element that owns a text node.
 * Foreground = computed color (alpha composited over its background). Background =
 * computed background-color composited walking UP the tree until opaque; a
 * gradient-only background-image uses that element's background-color. When the
 * walk meets a video / img / canvas / url() image behind the text:
 *   - inside a pagehero band (.ph) the scrim is the plate: --st-scrim at
 *     --st-scrim-a (the contract's weakest text alpha) over the WORST media pixel;
 *   - elsewhere any translucent plate already composited is laid over the WORST
 *     media pixel;
 *   - text with no plate at all over media cannot be measured without the pixels
 *     and is counted as `unplated`, listed, and NOT failed.
 * "Worst media pixel" = whichever of pure black / pure white gives the lower ratio
 * (the report's `basis` says `media-worst`).
 * Threshold: WCAG AA, 4.5:1 normal, 3:1 large (>= 24px, or >= 18.66px bold).
 *
 * Output: one line per page x style x scheme (`ok` or `FAIL`), with the worst ratio
 * and its element, the count below threshold, page errors; exit 1 on any FAIL.
 * No threshold here is tuned to a page; they are WCAG's.
 */
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const arg = (k, d) => { const h = args.find((a) => a.startsWith(`--${k}=`)); return h ? h.slice(k.length + 3) : d; };
const BASE = arg('base', '').replace(/\/$/, '');
if (!BASE) { console.log('FAIL usage: --base=http://127.0.0.1:<port> is required (this eval serves nothing)'); process.exit(2); }
const ROOT = resolve(arg('root', join(HERE, '..')));
const list = (k, d) => arg(k, d).split(',').map((x) => x.trim()).filter(Boolean);
const ONLY = list('pages', '');
const JSON_PATH = arg('json', '');
const CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const CONCURRENCY = Number(arg('concurrency', '6'));
/* the browser lock is shared: stop STARTING jobs after --budget seconds; any job not
   measured is reported by name and fails the run (unmeasured is not a pass) */
const BUDGET = Number(arg('budget', '80'));

/* page list and style ids come from the builders' own truth, not a copy */
const py = spawnSync('python3', ['-c', [
  'import sys, json; sys.path.insert(0, "web")',
  'import sitenav, design_kit',
  'print(json.dumps({"pages": list(sitenav.PAGES), "styles": [s["id"] for s in design_kit.STYLES], "key": design_kit.STYLE_KEY}))',
].join('\n')], { cwd: ROOT, encoding: 'utf8' });
if (py.status !== 0) { console.log(`FAIL page list: python sitenav/design_kit import failed: ${py.stderr.trim().split('\n').pop()}`); process.exit(2); }
const TRUTH = JSON.parse(py.stdout);
const PAGES = TRUTH.pages.filter((p) => !ONLY.length || ONLY.some((o) => p.includes(o)));
const STYLES = list('styles', TRUTH.styles.join(','));
const SCHEMES = list('schemes', 'dark,light');
for (const s of STYLES) if (!TRUTH.styles.includes(s)) { console.log(`FAIL styles: unknown style ${s} (design_kit.STYLES: ${TRUTH.styles})`); process.exit(2); }
if (!PAGES.length) { console.log(`FAIL pages: --pages=${ONLY} matches no page in sitenav.PAGES`); process.exit(2); }

/* ---------------------------------------------------------- in-page audit */
const MEASURE = () => {
  const cssPath = (e) => {
    const parts = [];
    for (let a = e; a && a.nodeType === 1 && parts.length < 4; a = a.parentElement) {
      let s = a.tagName.toLowerCase();
      if (a.id) { parts.unshift(`${s}#${a.id}`); break; }
      if (typeof a.className === 'string' && a.className.trim()) s += '.' + a.className.trim().split(/\s+/).slice(0, 2).join('.');
      parts.unshift(s);
    }
    return parts.join('>');
  };
  const kind = (e) => {
    if (e.closest('nav, .sitenav, [role=navigation]')) return 'nav';
    if (e.closest('h1')) return 'h1';
    if (e.closest('button, .tc-btn, .dk-btn, [role=button], summary')) return 'button';
    if (e.closest('[class*="badge"], .chip, .tag, .pill')) return 'badge';
    if (e.closest('a[href]')) return 'link';
    if (e.closest('.ph')) return 'hero';
    if (e.closest('[class*="panel"], [class*="card"], aside, dialog')) return 'panel';
    return 'text';
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
  const clipped = (e) => {
    for (let a = e; a && a.nodeType === 1; a = a.parentElement) {
      const cs = getComputedStyle(a);
      if ((cs.clip && cs.clip !== 'auto') || (cs.clipPath && cs.clipPath.startsWith('inset(50%'))) return true;
      const r = a.getBoundingClientRect();
      if (r.width <= 1 && r.height <= 1 && cs.overflow === 'hidden') return true;
    }
    return false;
  };
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
  const ratioOf = (fg, bg) => { const f = fg[3] < 1 ? over(fg, bg) : fg; const L1 = lum(f), L2 = lum(bg);
    return (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05); };
  const hex = (c) => '#' + c.slice(0, 3).map((v) => Math.round(v).toString(16).padStart(2, '0')).join('');
  const media = [...document.querySelectorAll('canvas, video, img, iframe, picture')].filter((m) => { const r = m.getBoundingClientRect(); return r.width > 40 && r.height > 20; });
  const rootCs = getComputedStyle(document.documentElement);
  const rows = []; let checked = 0; const unplated = [];
  const done = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    if (!n.nodeValue.trim()) continue;
    const e = n.parentElement;
    if (!e || done.has(e)) continue; done.add(e);
    if (/^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE|OPTION|TITLE)$/.test(e.tagName) || e.closest('svg')) continue;
    if (!shown(e) || clipped(e)) continue;
    const cs = getComputedStyle(e);
    const fg = rgba(cs.color);
    if (fg[3] === 0) continue;
    const r = e.getBoundingClientRect(), mx = r.left + r.width / 2, my = r.top + r.height / 2;
    let bg = [0, 0, 0, 0], behind = null, anc = e, inner = [0, 0, 0, 0];
    for (; anc; anc = anc.parentElement) {
      inner = bg; // everything composited ABOVE this ancestor
      const as = getComputedStyle(anc);
      const bi = as.backgroundImage;
      /* a url() image paints OVER its own background-color: the text sits on the image */
      if (bi && bi !== 'none' && /url\(/.test(bi)) { behind = `bg-image:${cssPath(anc)}`; break; }
      bg = over(bg, rgba(as.backgroundColor));
      if (bg[3] >= 0.99) break;
    }
    const ctxEl = anc || document.documentElement;
    if (!behind) {
      const m = media.find((m) => !e.contains(m) && ctxEl.contains(m) && !m.contains(e) && (() => { const q = m.getBoundingClientRect(); return mx >= q.left && mx <= q.right && my >= q.top && my <= q.bottom; })());
      if (m) { behind = m.tagName.toLowerCase(); bg = anc ? inner : bg; } // ctxEl's own fill is BEHIND the media
    }
    let basis = 'rendered', ratio;
    if (behind) {
      /* the plate between the text and the media */
      let plate = bg;
      const ph = e.closest('.ph');
      if (ph && ph.querySelector('.ph-scrim')) {
        const pcs = getComputedStyle(ph);
        const sc = (pcs.getPropertyValue('--st-scrim') || pcs.getPropertyValue('--ph-plate')).trim();
        const sa = parseFloat(pcs.getPropertyValue('--st-scrim-a')) || 0.72; // THEME_CONTRACT 1: 0.72 plate
        if (sc) { const c = rgba(sc); plate = over(bg[3] < 0.99 ? bg : [0, 0, 0, 0], [c[0], c[1], c[2], sa]); }
        basis = 'scrim/media-worst';
      } else {
        basis = 'plate/media-worst';
        /* a scrim element over the media (any class containing "scrim"): its weakest stop */
        const scr = [...ctxEl.querySelectorAll('[class*="scrim"]')].find((x) => !x.contains(e) && (() => { const q = x.getBoundingClientRect(); return mx >= q.left && mx <= q.right && my >= q.top && my <= q.bottom; })());
        if (scr) {
          const scs = getComputedStyle(scr);
          const stops = [...`${scs.backgroundImage} ${scs.backgroundColor}`.matchAll(/rgba?\([^)]*\)/g)].map((x) => rgba(x[0])).filter((c) => c[3] > 0);
          if (stops.length) { const weakest = stops.sort((a, b) => a[3] - b[3])[0]; plate = over(plate, weakest); basis = 'scrim/media-worst'; }
        }
      }
      if (plate[3] < 0.05) { unplated.push(`${cssPath(e)} over ${behind}`); continue; }
      ratio = Math.min(ratioOf(fg, over(plate, [0, 0, 0, 1])), ratioOf(fg, over(plate, [255, 255, 255, 1])));
      bg = over(plate, [255, 255, 255, 1]);
    } else {
      if (bg[3] < 0.99) bg = over(bg, [255, 255, 255, 1]); // canvas default
      ratio = ratioOf(fg, bg);
    }
    const px = parseFloat(cs.fontSize), bold = Number(cs.fontWeight) >= 700;
    const large = px >= 24 || (bold && px >= 18.66);
    const need = large ? 3 : 4.5;
    checked++;
    rows.push({ sel: cssPath(e), kind: kind(e), text: (e.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 32),
      ratio: Math.round(ratio * 100) / 100, need, fg: hex(fg[3] < 1 ? over(fg, bg) : fg), bg: hex(bg), px, basis,
      low: ratio + 0.005 < need });
  }
  return { checked, rows, unplated, style: document.documentElement.getAttribute('data-style') };
};

/* ------------------------------------------------------------------ run */
const t0 = Date.now();
const browser = await chromium.launch({ executablePath: CHROME, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'] });
const jobs = [];
for (const scheme of SCHEMES) for (const style of STYLES) for (const page of PAGES) jobs.push({ page, style, scheme });
const contexts = new Map();
const ctxFor = async (style, scheme) => {
  const k = `${style}|${scheme}`;
  if (!contexts.has(k)) contexts.set(k, (async () => {
    const c = await browser.newContext({ viewport: { width: 1280, height: 800 }, colorScheme: scheme, reducedMotion: 'reduce' });
    await c.addInitScript(([key, v]) => { try { localStorage.setItem(key, v); } catch (e) { /* storage blocked */ } }, [TRUTH.key, style]);
    return c;
  })());
  return contexts.get(k);
};
const results = [];
const runJob = async ({ page, style, scheme }) => {
  const errors = [];
  const res = { page, style, scheme, applied: null, checked: 0, below: 0, worst: null, low: [], unplated: [], errors };
  let p = null;
  try {
    const ctx = await ctxFor(style, scheme);
    p = await ctx.newPage();
    p.on('pageerror', (e) => errors.push(String(e.message || e).slice(0, 160)));
    /* the DOM text is what is measured: wait for DOMContentLoaded, then give the page
       up to 8 s more to finish loading (heavy WebGL pages under SwiftShader) */
    await p.goto(`${BASE}/${page}`, { waitUntil: 'domcontentloaded', timeout: 20000 });
    await p.waitForLoadState('load', { timeout: 8000 }).catch(() => {});
    await p.waitForTimeout(page.match(/3d|wilds|geomap|interactive|map\.html/) ? 700 : 200);
    let applied = await p.evaluate((s) => document.documentElement.getAttribute('data-style') === s, style);
    if (applied) res.applied = 'storage';
    else {
      applied = await p.evaluate((s) => { const i = document.querySelector(`input[name="tc-style"][value="${s}"]`);
        if (!i) return false; i.checked = true; i.dispatchEvent(new Event('change', { bubbles: true })); return true; }, style);
      res.applied = applied ? 'radio' : 'none';
      await p.waitForTimeout(50);
    }
    const m = await p.evaluate(MEASURE);
    res.checked = m.checked;
    const low = m.rows.filter((r) => r.low).sort((a, b) => a.ratio / a.need - b.ratio / b.need);
    res.below = low.length;
    res.low = low.slice(0, 12);
    const all = [...m.rows].sort((a, b) => a.ratio / a.need - b.ratio / b.need);
    res.worst = all[0] || null;
    res.unplated = m.unplated.slice(0, 8);
    res.unplatedCount = m.unplated.length;
  } catch (e) { errors.push(`load: ${String(e.message || e).split('\n')[0].slice(0, 160)}`); }
  if (p) await p.close().catch(() => {});
  res.fail = res.below > 0 || errors.length > 0 || res.applied === 'none';
  results.push(res);
  const w = res.worst ? `worst ${res.worst.ratio}:1<${res.worst.need}? ${res.worst.kind} ${res.worst.sel} "${res.worst.text}"` : 'no text';
  console.log(`${res.fail ? 'FAIL' : 'ok'} ${page} [${style}/${scheme}] via=${res.applied} checked=${res.checked} below=${res.below} unplated=${res.unplatedCount ?? 0} errors=${errors.length} ${w}${errors.length ? ' | ' + errors[0] : ''}`);
};
const queue = [...jobs];
await Promise.all(Array.from({ length: Math.min(CONCURRENCY, queue.length) }, async () => {
  while (queue.length && (Date.now() - t0) / 1000 < BUDGET) await runJob(queue.shift());
}));
for (const j of queue) { console.log(`FAIL ${j.page} [${j.style}/${j.scheme}] not measured: --budget=${BUDGET}s spent`); }
await browser.close();
const secs = Math.round((Date.now() - t0) / 100) / 10;

const failed = results.filter((r) => r.fail);
console.log(`\n${queue.length} not measured (budget). ${results.length} page x style x scheme measured (${PAGES.length} pages x ${STYLES.length} styles x ${SCHEMES.length} schemes) in ${secs}s; ${failed.length} FAIL`);
if (JSON_PATH) {
  let prev = { runs: [], results: {} };
  if (existsSync(JSON_PATH)) { try { prev = JSON.parse(readFileSync(JSON_PATH, 'utf8')); } catch (e) { prev = { runs: [], results: {} }; } }
  for (const r of results) prev.results[`${r.page}|${r.style}|${r.scheme}`] = r;
  prev.runs.push({ base: BASE, pages: PAGES, styles: STYLES, schemes: SCHEMES, seconds: secs, n: results.length, fail: failed.length, at: new Date().toISOString() });
  prev.thresholds = { normal: 4.5, large: 3, large_def: '>=24px or >=18.66px bold', media: 'plate or scrim over worst of black/white; unplated text over media is listed, not failed' };
  writeFileSync(JSON_PATH, JSON.stringify(prev, null, 1));
}
process.exit(failed.length || queue.length ? 1 : 0);
