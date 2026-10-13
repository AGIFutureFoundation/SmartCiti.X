/**
 * The WORLD-TEX eval (wave 17, NEW): device-tier surface detail on the walkable worlds (web/worldtexkit.py, used by
 * web/build_parishes.py - the Bay page inherits it - and web/build_wilds.py). Its own script, so the world evals' parts
 * keep their <= 90 s budgets (eval_parishes part 3 alone already reaches 90 s above load 3.5):
 *
 *   python3 -m http.server <port> --bind 127.0.0.1    (from the repo root)
 *   WT_URL=http://127.0.0.1:<port>/web/ flock $SP/chromium.lock node web/eval_worldtex.mjs [--pages=parishes,bay,wilds] [--shots=<dir>]
 *
 * One row per page: parishes at the 22071 origin walk view, bay at 06075, wilds on the canyon summit (steep walls: rock).
 *
 *   auto   what this machine is given. A software rasteriser (SwiftShader, llvmpipe) MUST get base, and base changes
 *          nothing: the WORLD-TEX shader patch is off and no texture is painted.
 *   high / ultra   forced through window.__worldTexDo(tier), which paints the whole set at once (a harness measures it):
 *          draw calls and triangles EQUAL to base (textures add none), every surface painted or skipped by the budget,
 *          texture memory within the tier's budget, mipmapped, anisotropic, no shader error, and the frame on screen
 *          differs from base (the detail is really drawn).
 *   Frame time at every tier is MEASURED and printed with the 1-minute load average. It is not judged here: a
 *   software rasteriser pays per texel tap and the tier picker never gives it high or ultra.
 * The row leaves the page on base.
 */
import { readFileSync } from 'node:fs';

const load1 = () => { try { return +readFileSync('/proc/loadavg', 'utf8').split(' ')[0]; } catch (e) { return null; } };

export async function worldTexRow(page, { id, shots = null, name = 'world', hooks = '__parishes', view = ['origin', id] }) {
  const row = { probe: 'world-tex', view: view.join(' '), fails: [] };
  const fail = (m) => row.fails.push(m);
  const meas = async () => {
    const t = (await page.evaluate((h) => window[h].frameTimes(6), hooks)).sort((a, b) => a - b);
    const s = await page.evaluate((h) => window[h].stats(), hooks);
    return { calls: s.calls, tris: s.triangles, ms: +t[Math.floor(t.length / 2)].toFixed(1) };
  };
  await page.evaluate(([h, v]) => window[h].view(...v), [hooks, view]);
  await page.waitForTimeout(900);
  // streaming settles first: the tiers are compared on the same chunks
  await page.waitForFunction((h) => window[h].stats().pending === 0, hooks, { timeout: 15000 }).catch(() => fail('streaming never settled (pending > 0)'));
  const auto = await page.evaluate(() => {
    const W = window.__worldTex();
    let who = '';
    try { const gl = document.createElement('canvas').getContext('webgl2'); const e = gl.getExtension('WEBGL_debug_renderer_info'); who = e ? String(gl.getParameter(e.UNMASKED_RENDERER_WEBGL)) : ''; } catch (e) { who = ''; }
    return { ...W, soft: /swiftshader|llvmpipe|softpipe|software/i.test(who) };
  });
  row.auto = auto.tier; row.soft = auto.soft;
  if (typeof auto.tier !== 'string') { fail('window.__worldTex() is missing'); return row; }
  if (auto.soft && auto.asked === 'auto' && auto.tier !== 'base') fail(`a software rasteriser got the ${auto.tier} tier, not base`);
  if (auto.tier === 'base' && (auto.on || auto.painted)) fail('base painted textures or patched the shaders');
  await page.evaluate(() => window.__worldTexDo('base'));
  await page.waitForTimeout(300);
  const b = await meas();
  row.base = { ...b, load: load1() };
  const shotBase = await page.locator('canvas').first().screenshot().catch(() => null);
  if (shots && shotBase) (await import('node:fs')).writeFileSync(`${shots}/${name}_tex_base.png`, shotBase);
  for (const tier of ['high', 'ultra']) {
    const st = await page.evaluate((t) => window.__worldTexDo(t), tier);
    await page.waitForTimeout(400);
    const m = await meas();
    const shot = await page.locator('canvas').first().screenshot().catch(() => null);
    if (shots && shot) (await import('node:fs')).writeFileSync(`${shots}/${name}_tex_${tier}.png`, shot);
    row[tier] = { ...m, load: load1(), mb: st.mb, budgetMb: st.budgetMb, painted: st.painted, skipped: st.skipped, paintMs: st.paintMs,
      aniso: st.aniso, sizes: st.sizes.map(([s, px]) => `${s}:${px}`).join(' ') };
    if (st.err) fail(`${tier}: ${st.err}`);
    if (!st.on) fail(`${tier}: the shader patch is not on after painting`);
    if (st.painted + st.skipped !== st.surfaces || st.pending) fail(`${tier}: ${st.painted} painted + ${st.skipped} skipped of ${st.surfaces} (pending ${st.pending})`);
    if (!(st.mb <= st.budgetMb)) fail(`${tier}: texture memory ${st.mb} MB > budget ${st.budgetMb} MB`);
    if (!st.mipmaps) fail(`${tier}: textures are not mipmapped (LinearMipmapLinear)`);
    if (!(st.aniso >= 1)) fail(`${tier}: anisotropy ${st.aniso}`);
    if (m.calls !== b.calls) fail(`${tier}: draw calls ${m.calls} != base ${b.calls}`);
    if (m.tris !== b.tris) fail(`${tier}: triangles ${m.tris} != base ${b.tris}`);
    if (shot && shotBase && shot.equals(shotBase)) fail(`${tier}: the frame is pixel-identical to base (no detail drawn)`);
  }
  const back = await page.evaluate(() => window.__worldTexDo('base'));
  if (back.on || back.painted) fail('the page did not return to base');
  return row;
}

/* ---- the script: one browser, one row per page; page errors (a shader that does not compile logs one) fail the page */
const ME = new URL(import.meta.url).pathname;
if (process.argv[1] && new URL('file://' + process.argv[1]).pathname === ME) {
  const { chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs');
  const { mkdirSync } = await import('node:fs');
  const BASE = process.env.WT_URL ?? 'http://127.0.0.1:8891/web/';
  const pagesArg = process.argv.find((a) => a.startsWith('--pages='));
  const shotArg = process.argv.find((a) => a.startsWith('--shots='));
  const SHOTS = shotArg ? shotArg.slice(8) : null;
  if (SHOTS) mkdirSync(SHOTS, { recursive: true });
  const PAGES = {
    parishes: { file: 'trade_craft_parishes.html', ready: 'parishesReady', opt: { id: '22071' } },
    bay: { file: 'trade_craft_bay.html', ready: 'parishesReady', opt: { id: '06075' } },
    wilds: { file: 'trade_craft_wilds.html', ready: 'wildsReady', world: 'canyon', opt: { id: 'canyon', hooks: '__wilds', view: ['summit'] } },
  };
  const want = pagesArg ? pagesArg.slice(8).split(',') : Object.keys(PAGES);
  const unknown = want.filter((k) => !(k in PAGES));
  if (unknown.length) { console.log(`FAIL --pages: no page called ${unknown.join(', ')}; the pages are ${Object.keys(PAGES).join(', ')}`); process.exit(2); }
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  let bad = 0;
  for (const k of want) {
    const P = PAGES[k], page = await browser.newPage({ viewport: { width: 1280, height: 800 } }), errors = [];
    page.on('pageerror', (e) => errors.push(String(e)));
    page.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push(m.text().slice(0, 300)); });
    await page.goto(BASE + P.file, { waitUntil: 'load' });
    const ok = await page.waitForFunction((r) => document.documentElement.dataset[r] === '1', P.ready, { timeout: 45000 }).then(() => true, () => false);
    let row = { probe: 'world-tex', fails: ok ? [] : ['the page never became ready'] };
    if (ok) { if (P.world) await page.evaluate((id) => window.__wilds.load(id), P.world); row = await worldTexRow(page, { ...P.opt, name: k, shots: SHOTS }); }
    for (const e of errors) row.fails.push('page error: ' + e);
    if (row.fails.length) bad++;
    console.log(`${row.fails.length ? 'FAIL' : '  ok'} world-tex ${k} ${JSON.stringify(Object.fromEntries(Object.entries(row).filter(([x]) => x !== 'fails' && x !== 'probe')))}${row.fails.length ? ' :: ' + row.fails.join('; ') : ''}`);
    await page.close();
  }
  await browser.close();
  console.log(bad ? `eval_worldtex: ${bad} FAIL` : `eval_worldtex: all ${want.length} pages within target`);
  process.exit(bad ? 1 : 0);
}
