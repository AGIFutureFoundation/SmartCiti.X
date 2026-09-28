/**
 * A scorecard for the wilds, measured in a real browser - the same kind of
 * opt-in eval as web/eval_scene.mjs, for the same reason: how many draw
 * calls a view costs, how many trees are standing in it and how long a frame
 * takes cannot be read from the source.
 *
 * Run:  python3 -m http.server 8812 --bind 127.0.0.1   (from the repo root)
 *       flock $SP/chromium.lock node web/eval_wilds.mjs [--json] [--shots=<dir>]
 *
 * Every world is driven through four views by the page's own __wilds hooks:
 *   overview  the whole world as one low-resolution mesh from above
 *   trail     standing at the trailhead, looking up the first trail leg
 *   dense     standing where the biome grows the most trees
 *   summit    standing on the highest ground the seed makes
 *
 * Targets are DECLARED here with their reasons. All of them are
 * MEASURED-HERE: a number this page achieved in this sandbox's Chromium
 * (SwiftShader, software GL, 1280x800), recorded with stated headroom so it
 * cannot quietly get worse. Draw calls get 25% (the scarce currency, as in
 * eval_scene.mjs); triangles 1.5x (the terrain LOD and the instance caps
 * already bound them, so a big jump means one of those broke); frame time
 * 2x (software GL on a shared machine is noisy, and it is the number a
 * learner feels). Visible instances are held to a FLOOR of 0.9x the
 * measured count in the views meant to be wooded - a forest bought cheap by
 * growing nothing is not a forest. Chunk counts are held exactly: they are
 * fixed by RADIUS and the world edge, so any other number is a streaming bug.
 */
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';

const URL_BASE = process.env.WILDS_URL ?? 'http://127.0.0.1:8812/web/trade_craft_wilds.html';
const CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const JSON_OUT = process.argv.includes('--json');
const shotArg = process.argv.find((a) => a.startsWith('--shots='));
const SHOTS = shotArg ? shotArg.slice(8) : null;
if (SHOTS) mkdirSync(SHOTS, { recursive: true });

/* Baselines measured 2026-09-28 in this sandbox (see the header). `veg` is
   the visible-instance floor's base; null where a view is not meant to be
   wooded (the overview hides vegetation by design: at that scale a tree is
   under a pixel, and the whole-world mesh's colours carry the forest). */
const BASE = {
  /* `bb` (wave 3): the tree-billboard floor, a NEW row measured 2026-09-28
     08:25 UTC on a frozen copy (scratchpad wilds_w3_measure2.log), held like
     `veg` to 0.9x: the cards past VEG_R are what make a wooded view read as
     a forest to the horizon. null where a view is not meant to be wooded
     (overview: cards are hidden there by design; summit: not a wooded view,
     as for veg).
     The calls/tris/ms rows were NOT re-declared: billboards cost +2 calls and
     at most ~22k triangles per walk view, measured inside the existing
     headroom (forest dense: 12 calls against a 12-call limit). */
  /* measured 2026-09-28 06:1x UTC, Chromium/SwiftShader 1280x800, with other
     agents' browsers sharing the machine (frame times are the noisy row) */
  mountain: {
    overview: { calls: 4, tris: 38_376, ms: 33.6, chunks: 1, veg: null, bb: null },
    trail: { calls: 25, tris: 108_800, ms: 127.1, chunks: 49, veg: 2_041, bb: 587 },
    dense: { calls: 21, tris: 138_914, ms: 190.8, chunks: 49, veg: 3_081, bb: 1734 },
    summit: { calls: 24, tris: 76_046, ms: 97.4, chunks: 49, veg: null, bb: null },
  },
  forest: {
    overview: { calls: 4, tris: 38_076, ms: 70.2, chunks: 1, veg: null, bb: null },
    trail: { calls: 33, tris: 277_976, ms: 197.3, chunks: 49, veg: 6_137, bb: 5615 },
    dense: { calls: 9, tris: 241_360, ms: 252.4, chunks: 25, veg: 6_018, bb: 5320 },
    summit: { calls: 26, tris: 256_458, ms: 251.7, chunks: 49, veg: null, bb: null },
  },
  canyon: {
    overview: { calls: 4, tris: 36_992, ms: 71.5, chunks: 1, veg: null, bb: null },
    trail: { calls: 27, tris: 51_848, ms: 124.2, chunks: 49, veg: 485, bb: 120 },
    dense: { calls: 26, tris: 54_668, ms: 105.3, chunks: 49, veg: 594, bb: 154 },
    summit: { calls: 24, tris: 45_800, ms: 79.4, chunks: 42, veg: null, bb: null },
  },
  /* delta (wave 2): measured 2026-09-28 07:03 UTC, same machine and settings,
     in the verification run that checked the three rows above (log:
     scratchpad wilds_w2_eval.log). A marsh world is sparsely wooded by
     design, so its veg floors are low; the summit view is not meant to be
     wooded, as elsewhere. */
  delta: {
    overview: { calls: 4, tris: 39_224, ms: 49.5, chunks: 1, veg: null, bb: null },
    trail: { calls: 26, tris: 51_390, ms: 55, chunks: 49, veg: 468, bb: 89 },
    dense: { calls: 17, tris: 53_222, ms: 52.3, chunks: 35, veg: 666, bb: 321 },
    summit: { calls: 23, tris: 56_030, ms: 75.3, chunks: 49, veg: null, bb: null },
  },
};
const CALL_HEADROOM = 1.25, TRI_HEADROOM = 1.5, MS_HEADROOM = 2, VEG_FLOOR = 0.9;
const MEASURE_ONLY = process.argv.includes('--measure');

const browser = await chromium.launch({ executablePath: CHROME, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const errors = [];
page.on('pageerror', (e) => errors.push(String(e)));
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
await page.goto(URL_BASE, { waitUntil: 'load' });
await page.waitForFunction(() => document.documentElement.dataset.wildsReady === '1', null, { timeout: 60000 });

const worlds = await page.evaluate(() => window.__wilds.worlds());
const rows = [];
let bad = 0;
for (const w of worlds) {
  await page.evaluate((id) => window.__wilds.load(id), w);
  for (const v of ['overview', 'trail', 'dense', 'summit']) {
    await page.evaluate((name) => window.__wilds.view(name), v);
    await page.waitForTimeout(400);
    const times = await page.evaluate(() => window.__wilds.frameTimes(6));
    const st = await page.evaluate(() => window.__wilds.stats());
    times.sort((a, b) => a - b);
    const ms = +times[Math.floor(times.length / 2)].toFixed(1);
    const vegN = st.instances.conifer + st.instances.deciduous + st.instances.rock;
    const bbN = st.billboards.conifer + st.billboards.deciduous;
    const row = { world: w, view: v, calls: st.calls, tris: st.triangles, ms, chunks: st.chunks, pending: st.pending, veg: vegN, bb: bbN, instanced: st.instanced };
    const base = BASE[w] && BASE[w][v];
    row.fails = [];
    if (st.pending !== 0) row.fails.push(`${st.pending} chunks still pending`);
    if (!st.instanced) row.fails.push('vegetation is not InstancedMesh');
    /* tree billboards (wave 3): one InstancedMesh per species, only past the
       full-tree radius, never drawn in the overview */
    if (!st.billboardsInstanced) row.fails.push('billboards are not InstancedMesh');
    if (st.billboardMeshes !== 1) row.fails.push(`${st.billboardMeshes} billboard meshes; wave 4 draws every species in ONE InstancedMesh`);
    if (bbN > 0 && !(st.billboardMinR >= st.vegR)) row.fails.push(`a billboard stands ${st.billboardMinR} m out, inside VEG_R ${st.vegR}`);
    if (v === 'overview' && bbN !== 0) row.fails.push(`${bbN} billboards drawn in the overview`);
    if (!MEASURE_ONLY) {
      if (!base) row.fails.push('no declared target for this view');
      else {
        if (st.calls > Math.ceil(base.calls * CALL_HEADROOM)) row.fails.push(`calls ${st.calls} > ${Math.ceil(base.calls * CALL_HEADROOM)}`);
        if (st.triangles > Math.ceil(base.tris * TRI_HEADROOM)) row.fails.push(`tris ${st.triangles} > ${Math.ceil(base.tris * TRI_HEADROOM)}`);
        if (ms > base.ms * MS_HEADROOM) row.fails.push(`frame ${ms} ms > ${base.ms * MS_HEADROOM}`);
        if (st.chunks !== base.chunks) row.fails.push(`chunks ${st.chunks} != ${base.chunks}`);
        if (base.veg !== null && vegN < Math.floor(base.veg * VEG_FLOOR)) row.fails.push(`visible instances ${vegN} < ${Math.floor(base.veg * VEG_FLOOR)}`);
        if (!('bb' in base)) row.fails.push('no declared billboard floor (bb) for this view');
        else if (base.bb !== null && bbN < Math.floor(base.bb * VEG_FLOOR)) row.fails.push(`billboards ${bbN} < ${Math.floor(base.bb * VEG_FLOOR)}`);
      }
    }
    if (row.fails.length) bad++;
    rows.push(row);
    if (SHOTS) await page.locator('#stage').screenshot({ path: `${SHOTS}/WILDS-${w}-${v}.png` });
    if (!JSON_OUT) console.log(`${row.fails.length ? 'FAIL' : '  ok'}  ${w.padEnd(9)} ${v.padEnd(9)} calls ${String(st.calls).padStart(4)}  tris ${String(st.triangles).padStart(7)}  inst ${String(vegN).padStart(5)}  bb ${String(bbN).padStart(5)}  chunks ${String(st.chunks).padStart(3)}  frame ${String(ms).padStart(6)} ms${row.fails.length ? '  ' + row.fails.join('; ') : ''}`);
  }
}
/* deep links (wave 4): every wilds-site-walk task in tasks/registry/tasks.json
   launches at web/trade_craft_wilds.html#<world>/<site>; following the link must
   put the eye within that site's pad_m (horizontal) with its panel open. */
const { readFileSync } = await import('node:fs');
const TASKS = JSON.parse(readFileSync(new URL('../tasks/registry/tasks.json', import.meta.url), 'utf8'));
const REGW = JSON.parse(readFileSync(new URL('../wilds/registry/wilds.json', import.meta.url), 'utf8'));
const walks = TASKS.tasks.filter((t) => t.kind === 'wilds-site-walk');
const linkBad = [];
if (walks.length === 0) linkBad.push('no wilds-site-walk task in tasks/registry');
for (const t of walks) {
  const href = t.launch.href;
  const m = href && href.match(/^web\/trade_craft_wilds\.html#([a-z0-9-]+)\/([a-z0-9-]+)$/);
  if (!m) { linkBad.push(`${t.id}: launch ${href} is not #world/site`); continue; }
  const site = REGW.worlds.find((w) => w.id === m[1]).sites.find((s) => s.id === m[2]);
  await page.goto(new URL(href.slice(4), URL_BASE).href, { waitUntil: 'load' });
  await page.waitForFunction((sid) => { const p = document.getElementById('panel'); return p && !p.hidden && !!p.querySelector(`[data-site="${sid}"]`); }, m[2], { timeout: 8000 }).catch(() => {});
  const got = await page.evaluate((sid) => ({ eye: window.__wilds.eye(), open: !document.getElementById('panel').hidden && !!document.getElementById('panel').querySelector(`[data-site="${sid}"]`) }), m[2]);
  const d = Math.hypot(got.eye.x - site.x, got.eye.z - site.z);
  if (!(d <= site.pad_m) || !got.open) linkBad.push(`${t.id}: eye ${d.toFixed(1)} m from ${m[2]} (pad_m ${site.pad_m}), panel ${got.open ? 'open' : 'closed'}`);
}
if (linkBad.length) bad++;
console.log(`${linkBad.length ? 'FAIL' : '  ok'}  deep links: ${walks.length} site-walk task links land within the site's pad_m with its panel open${linkBad.length ? '  ' + linkBad.slice(0, 4).join('; ') : ''}`);
/* run-time locale (wave 4): ?lang=ar renders the chrome in Arabic, right to left */
const pa = await browser.newPage({ viewport: { width: 1280, height: 800 } });
pa.on('pageerror', (e) => errors.push('ar: ' + String(e)));
await pa.goto(URL_BASE + '?lang=ar', { waitUntil: 'load' });
await pa.waitForFunction(() => document.documentElement.dataset.wildsReady === '1', null, { timeout: 60000 });
const AR = JSON.parse(readFileSync(new URL('../i18n/locales/ar.json', import.meta.url), 'utf8')).strings;
const ar = await pa.evaluate(() => ({ dir: document.dir, lang: document.documentElement.lang, help: document.querySelector('[data-i18n="wilds.help"]').textContent,
  ctl: (() => { const c = document.querySelector('#stage .ctl').getBoundingClientRect(), s = document.getElementById('stage').getBoundingClientRect(); return { right: s.right - c.right, left: c.left - s.left }; })(),
  mini: (() => { const c = document.getElementById('minimap').getBoundingClientRect(), s = document.getElementById('stage').getBoundingClientRect(); return c.left - s.left; })(),
  overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth }));
const arOk = ar.dir === 'rtl' && ar.lang === 'ar' && ar.help === AR['wilds.help'] && ar.ctl.right < 20 && ar.mini < 20 && !ar.overflow;
if (!arOk) bad++;
console.log(`${arOk ? '  ok' : 'FAIL'}  locale: ?lang=ar renders the chrome in ar, dir rtl, controls mirrored to the inline start (right), minimap to the inline end (left), no page overflow  ${JSON.stringify(ar.ctl)} mini ${ar.mini}`);
await pa.close();
if (errors.length) { bad++; console.log('FAIL  page errors: ' + errors.join(' | ')); }
await browser.close();
if (JSON_OUT) console.log(JSON.stringify({ rows, errors }, null, 1));
console.log(bad ? `wilds eval: ${bad} failing` : `wilds eval: all ${rows.length} views within target`);
process.exit(bad ? 1 : 0);
