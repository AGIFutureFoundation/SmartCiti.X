/**
 * geo3d browser agreement: the Python mirror (geo3d/registry/geo3d.json)
 * against what the 3D page actually BUILT - window.__tc3dLayout() in
 * web/trade_craft_3d.html reads every district group and hall wall-box back
 * off the scene (LAYOUT_CONTRACT v1). Every district centre and rotation and
 * every hall centre, size, wall height, roof top and roofline must agree to
 * <= 0.01 m, and the hall sets must be identical.
 *
 * Needs a browser, so it is NOT part of verify_all's static run:
 *   python3 -m http.server <port> --bind 127.0.0.1   (from the repo root)
 *   flock $SP/chromium.lock node geo3d/browser.mjs --port=<port> [--campuses=a,b] [--chrome=<path>]
 */
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const arg = (k) => { const a = process.argv.slice(2).find((x) => x.startsWith(`--${k}=`)); return a ? a.slice(k.length + 3) : null; };
const port = arg('port');
if (!port) { console.error('FAIL geo3d/browser: --port=<port of a server at the repo root> is required'); process.exit(2); }
const { chromium } = await import(arg('playwright') || '/opt/node22/lib/node_modules/playwright/index.mjs');
const reg = JSON.parse(readFileSync(join(HERE, 'registry/geo3d.json'), 'utf8'));
const withHalls = Object.keys(reg.campuses).filter((k) => reg.campuses[k].halls.length);
const hub = Object.keys(reg.campuses).find((k) => !reg.campuses[k].halls.length);
const list = arg('campuses') ? arg('campuses').split(',') : [...withHalls, hub];
let n = 0, failed = 0;
const ok = (m, c) => { if (c) { n++; console.log('  ok ', m); } else { failed++; console.error(`FAIL ${m}`); } };
const TOL = 0.01;
const browser = await chromium.launch({ executablePath: arg('chrome') || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
for (const k of list) {
  const page = await browser.newPage({ viewport: { width: 900, height: 600 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto(`http://127.0.0.1:${port}/web/trade_craft_3d.html?campus=${k}`, { waitUntil: 'load' });
  let L = null;
  try {
    await page.waitForFunction((kk) => typeof window.__tc3dLayout === 'function' && window.__tc3dLayout()
      && window.__tc3dLayout().campus === kk, k, { timeout: 45000 });
    L = await page.evaluate(() => window.__tc3dLayout());
  } catch (e) { errors.push('no layout: ' + String(e).split('\n')[0]); }
  const G = reg.campuses[k];
  if (L === null) { ok(`[browser] ${k}: window.__tc3dLayout() reports the built campus`, false); await page.close(); continue; }
  const pyH = Object.fromEntries(G.halls.map((h) => [h.slug, h]));
  const jsH = Object.fromEntries(L.halls.map((h) => [h.slug, h]));
  ok(`[browser] ${k}: the page built exactly the halls geo3d places (${L.halls.length})`,
    JSON.stringify(Object.keys(pyH).sort()) === JSON.stringify(Object.keys(jsH).sort()));
  let worst = 0; const off = [];
  for (const d of G.districts) {
    const j = L.districts.find((x) => x.key === d.key);
    const dd = j ? Math.max(Math.hypot(j.cx - d.cx, j.cz - d.cz), Math.abs(((j.psi - d.psi + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI) * 200) : Infinity;
    worst = Math.max(worst, dd); if (!(dd <= TOL)) off.push(d.key);
  }
  for (const h of G.halls) {
    const j = jsH[h.slug];
    const dd = j && j.district === h.district && j.roof === h.roof
      ? Math.max(Math.hypot(j.x - h.x, j.z - h.z), Math.abs(j.w - h.w), Math.abs(j.d - h.d), Math.abs(j.h - h.h),
                 Math.abs(j.top - h.top), Math.abs(((j.psi - h.psi + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI) * 200)
      : Infinity;
    worst = Math.max(worst, dd); if (!(dd <= TOL)) off.push(h.slug);
  }
  ok(`[browser] ${k}: every district and hall agrees with the built scene to <= ${TOL} m (worst ${worst.toExponential(2)} m${off.length ? '; off: ' + off.slice(0, 6).join(', ') : ''})`,
    off.length === 0 && L.districts.length === G.districts.length);
  ok(`[browser] ${k}: the frame is north = -Z, east = +X, metres`, L.frame.north === '-Z' && L.frame.east === '+X' && L.frame.units === 'm');
  ok(`[browser] ${k}: no page error while building the campus${errors.length ? ' (' + errors[0].slice(0, 120) + ')' : ''}`, errors.length === 0);
  await page.close();
}
await browser.close();
if (failed) { console.error(`FAIL geo3d/browser: ${failed} of ${n + failed} checks failed`); process.exit(1); }
console.log(`geo3d/browser: ${n} checks passed`);
