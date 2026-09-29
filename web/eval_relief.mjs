/**
 * ELEV w14 relief row (web/terrainkit.py mounted in build_parishes; the Bay page shares it) - a NEW eval row, used by
 * web/eval_parishes.mjs and web/eval_bayworld.mjs, and runnable alone for one page pair:
 *     flock $SP/chromium.lock node web/eval_relief.mjs <page url> [--shots=<dir> --name=<tag>]
 * Relief is default OFF (the eval 'ground' row holds the flat world); ?relief=on turns it on. The row holds:
 *   provenance  the RECORDED USGS 3DEP grid loaded (sha256-pinned, gunzipped in the browser), a finite median reference;
 *   present     the patch has quads and some drawn ground stands >= 0.3 m above the reference near a relief spot;
 *   slope       the drawn surface's max slope around the eye <= the page's declared max_slope;
 *   floating    N sampled kit buildings (as drawn), lots, trees, lamps and parked land vehicles: base within 0.1 m of
 *               the ground under it (lowest footprint point) and never above the ground at its centre;
 *   calls       draw calls at the same start view with relief on == with relief off (the patch rides the land mesh);
 *   water       the water plane and the world water level are unchanged.
 */
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';

const CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function openAt(browser, url, errors) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(url, { waitUntil: 'load' });
  await page.waitForFunction(() => window.__parishes && window.__parishes.elev, null, { timeout: 20000 });
  await page.waitForFunction(() => { const s = window.__parishes.stats(); return s.pending === 0 && s.loaded.every((id) => s.ground.ready.includes(id)); }, null, { timeout: 20000 }).catch(() => {});
  return page;
}
const calls = (page) => page.evaluate(async () => { const out = []; for (let i = 0; i < 6; i++) { await new Promise((r) => requestAnimationFrame(r)); out.push(window.__parishes.stats().calls); } return Math.max(...out); });

export async function reliefRow(browser, url, opts = {}) {
  const N = opts.n || 200, errors = [], row = { probe: 'relief', url: url.replace(/^.*\/web\//, 'web/'), fails: [] };
  const fail = (m) => row.fails.push(m);
  const off = await openAt(browser, url, errors); await sleep(1500);
  row.callsOff = await calls(off); await off.close();
  const on = await openAt(browser, url + (url.includes('?') ? '&' : '?') + 'relief=on', errors);
  await on.waitForFunction(() => { const p = window.__parishes.elev.probe(1); return p.demLoaded || p.demFailed; }, null, { timeout: 25000 }).catch(() => {});
  await on.waitForFunction(() => window.__parishes.stats().pending === 0, null, { timeout: 15000 }).catch(() => {});
  await sleep(1200);
  row.callsOn = await calls(on);
  row.spot = await on.evaluate(() => window.__parishes.elev.goRelief(0.6, 3000));
  await on.waitForFunction(() => window.__parishes.stats().pending === 0, null, { timeout: 15000 }).catch(() => {});
  await sleep(1500);
  const p = await on.evaluate((n) => { window.__parishes.elev.refresh(); return window.__parishes.elev.probe(n); }, N);
  const legend = await on.evaluate(() => { const e = document.querySelector('[data-legend="relief"]'); return e ? { hidden: e.hidden, text: e.textContent } : null; });
  Object.assign(row, { provenance: p.provenance, demLoaded: p.demLoaded, demFailed: p.demFailed, ref: p.ref, refN: p.refN, noneCells: p.noneCells, recCells: p.recCells,
    hmax: p.hmax, quads: p.quads, slope: p.slope, maxSlope: p.maxSlopeCap, patchMs: p.ms,
    audit: Object.fromEntries(['buildings', 'lots', 'trees', 'lamps', 'vehicles'].map((k) => [k, { n: p[k].n, bad: p[k].bad.length, maxGap: p[k].maxGap, maxFloat: p[k].maxFloat }])),
    avatar: p.avatar, water: [p.waterY, p.waterPlaneY], legend: legend ? legend.text.slice(0, 80) : null });
  if (p.provenance !== 'RECORDED' || !p.demLoaded || !Number.isFinite(p.ref)) fail(`RECORDED grid not in use (provenance ${p.provenance}, loaded ${p.demLoaded}, failed ${p.demFailed})`);
  if (!legend || legend.hidden || !/USGS 3DEP \(RECORDED\), shown relative to local median land; water level AUTHORED/.test(legend.text)) fail('relief legend line missing or hidden');
  if (!row.spot || p.quads < 1 || p.hmax < 0.3) fail(`no relief present (spot ${JSON.stringify(row.spot)}, quads ${p.quads}, hmax ${p.hmax})`);
  if (!(p.slope <= p.maxSlopeCap)) fail(`max slope ${p.slope} > declared ${p.maxSlopeCap} at ${JSON.stringify(p.slopeAt)}`);
  for (const k of ['buildings', 'lots', 'trees', 'lamps', 'vehicles']) if (p[k].bad.length) fail(`${k}: ${p[k].bad.length} of ${p[k].n} not on the ground within 0.1 m (${JSON.stringify(p[k].bad.slice(0, 3))})`);
  if (p.buildings.n < 50) fail(`only ${p.buildings.n} buildings sampled`);
  if (row.callsOn !== row.callsOff) fail(`draw calls ${row.callsOn} with relief on vs ${row.callsOff} off (want equal)`);
  if (p.waterY !== null && p.waterPlaneY !== -0.4) fail(`water plane moved to ${p.waterPlaneY}`);
  if (p.avatar && Math.abs(p.avatar.y - p.avatar.ground) > 0.1) fail(`walker at ${p.avatar.y} vs ground ${p.avatar.ground}`);
  if (opts.shots) {
    await on.screenshot({ path: `${opts.shots}/ELEV-${opts.name}-relief.png` });
    await on.evaluate(() => window.__parishes.elev.sun(0.12)); await sleep(500);
    await on.screenshot({ path: `${opts.shots}/ELEV-${opts.name}-relief-lowsun.png` });
  }
  await on.close();
  if (errors.length) fail(`page errors: ${errors.slice(0, 3).join(' | ')}`);
  row.errors = errors.length;
  return row;
}

if (process.argv[1] && process.argv[1].endsWith('eval_relief.mjs')) {
  const url = process.argv[2], shots = (process.argv.find((a) => a.startsWith('--shots=')) || '').slice(8) || null;
  const name = (process.argv.find((a) => a.startsWith('--name=')) || '--name=page').slice(7);
  const browser = await chromium.launch({ executablePath: CHROME, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const row = await reliefRow(browser, url, { shots, name });
  await browser.close();
  console.log(JSON.stringify(row, null, 1));
  console.log(row.fails.length ? `FAIL relief (${name}): ${row.fails.length}` : `  ok relief (${name})`);
  process.exit(row.fails.length ? 1 : 0);
}
