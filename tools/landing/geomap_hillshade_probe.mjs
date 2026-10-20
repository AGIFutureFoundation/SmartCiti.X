// One browser probe for the geomap hillshade, run as one line of the landing browser round.
// Serve a copy of the tree, then:  timeout 90 node tools/landing/geomap_hillshade_probe.mjs http://127.0.0.1:<port>/web/trade_craft_geomap.html <shot.png>
// (under the chromium lock, like every browser run - tools/landing/browser_round.sh does that).
// No machine path is written here: Playwright is PLAYWRIGHT_MODULE, else the local package, else the
// global one (`npm root -g`); the browser is CHROMIUM_PATH, else the one Playwright finds itself.
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
async function loadPlaywright() {
  if (process.env.PLAYWRIGHT_MODULE) return import(process.env.PLAYWRIGHT_MODULE);
  try { return await import('playwright'); } catch { /* not installed locally: try the global package */ }
  const root = execFileSync('npm', ['root', '-g'], { encoding: 'utf8' }).trim();
  return import(pathToFileURL(join(root, 'playwright', 'index.mjs')).href);
}
const { chromium } = await loadPlaywright();
const [url, shot] = process.argv.slice(2);
const b = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const p = await b.newPage({ viewport: { width: 1280, height: 800 } }); const errs = [], reqs = [];
p.on('pageerror', (e) => errs.push(e.message)); p.on('request', (r) => { if (/hillshade_/.test(r.url())) reqs.push(r.url()); });
await p.goto(url, { waitUntil: 'load' }); await p.waitForFunction(() => window.__geomap && window.__geomap().loaded, null, { timeout: 30000 });
await p.waitForTimeout(1500); const before = await p.evaluate(() => window.__geomap().hillshade);
// fly the way a reader does: the 'Fly to a campus' select (Oakland is inside the Bay hillshade region)
await p.selectOption('#flySel', 'oakland'); await p.waitForTimeout(9000);
await p.waitForTimeout(3000); const after = await p.evaluate(() => window.__geomap());
console.log(JSON.stringify({ before, after: after.hillshade, zoom: after.zoom, center: after.center, reqs, errs }));
if (shot) await p.screenshot({ path: shot }); await b.close();
// the round reads rc and FAIL lines, so a page error or a hillshade that never loads must fail the run
const fail = (why) => { console.log(`FAIL geomap_probe: ${why}`); process.exitCode = 1; };
if (errs.length) fail(`${errs.length} page error(s)`);
if (!reqs.length) fail('no hillshade file was requested after the fly');
if (!(after.hillshade && after.hillshade.added && after.hillshade.added.length)) fail('no hillshade layer was added after the fly');
if (!process.exitCode) console.log('  ok geomap_probe: hillshade loaded after the fly, no page errors');
