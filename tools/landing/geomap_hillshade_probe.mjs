// One browser probe for the geomap hillshade, run as one line of the landing browser round.
// Serve a copy of the tree, then:  timeout 90 node tools/landing/geomap_hillshade_probe.mjs http://127.0.0.1:<port>/web/trade_craft_geomap.html <shot.png>
// (under the chromium lock, like every browser run - tools/landing/browser_round.sh does that).
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
const [url, shot] = process.argv.slice(2);
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const p = await b.newPage({ viewport: { width: 1280, height: 800 } }); const errs = [], reqs = [];
p.on('pageerror', (e) => errs.push(e.message)); p.on('request', (r) => { if (/hillshade_/.test(r.url())) reqs.push(r.url()); });
await p.goto(url, { waitUntil: 'load' }); await p.waitForFunction(() => window.__geomap && window.__geomap().loaded, null, { timeout: 30000 });
await p.waitForTimeout(1500); const before = await p.evaluate(() => window.__geomap().hillshade);
// fly the way a reader does: the 'Fly to a campus' select (Oakland is inside the Bay hillshade region)
await p.selectOption('#flySel', 'oakland'); await p.waitForTimeout(9000);
await p.waitForTimeout(3000); const after = await p.evaluate(() => window.__geomap());
console.log(JSON.stringify({ before, after: after.hillshade, zoom: after.zoom, center: after.center, reqs, errs }));
if (shot) await p.screenshot({ path: shot }); await b.close();
