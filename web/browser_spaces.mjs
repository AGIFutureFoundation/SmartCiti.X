/**
 * The custom spaces in a browser: one run, every claim measured in the page.
 *
 *   timeout 90 node web/browser_spaces.mjs <3d page url> [--shot=<png>] [--deep=<space id>] [--pairs=<a>-<b>] [--halltest=<id>:<hall>,...]
 *
 * One run opens the page with ?space=<deep id> (default: the first space), then drives the (space, hall) pairs of
 * the registry numbered a..b in registry order (default: all of them), and runs the page's hall test on the
 * deep-linked space and on each pair named in --halltest. A run is kept under 90 s by splitting the pairs.
 *
 * (serve the tree first; run under the chromium lock like every browser run).
 * Playwright is PLAYWRIGHT_MODULE, else the local package, else the global one;
 * the browser is CHROMIUM_PATH, else the one Playwright finds itself. No machine
 * path is written here.
 *
 * What it proves, with the page's own code and nothing mocked:
 *   1. the deep link ?space=<id> (no hall named) opens the first serving hall, draws the
 *      space in the room of its strand, and shows the panel that says it is AUTHORED;
 *   2. a walker - driven through the page's walkStep, from the spot outside the open front,
 *      over a route found across the hall's real solids, space items included - ends in the
 *      room of the space, and passes through the rooms the registry's door route names;
 *   3. the hall test (every room reachable on foot, 36 headings out of the doorway, no step
 *      inside a wall) still holds with the space standing in it;
 *   4. the same for every other (space, hall) pair the registry declares.
 * Prints `  ok <name>` per check and `FAIL <name>` at column 0; exits non-zero on failure.
 */
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const reg = JSON.parse(readFileSync(join(HERE, '..', 'spaces/registry/spaces.json'), 'utf8'));
// A walker may take any fewest-or-longer chain of doorways; the registry names ONE fewest chain. What must hold of
// the rooms the walker entered, in order: the first is on the open front, each shares a doorway with the one before
// (the plan's own adjacency, recomputed from the stored rectangles), and the last is the space's room.
const adjacent = (a, b) => (a.x + a.w === b.x || b.x + b.w === a.x) && Math.min(a.y + a.h, b.y + b.h) > Math.max(a.y, b.y)
  || (a.y + a.h === b.y || b.y + b.h === a.y) && Math.min(a.x + a.w, b.x + b.w) > Math.max(a.x, b.x);
const chainOk = (hall, rooms, strand, fewest) => {
  const plan = reg.plans[hall], at = (st) => plan.find((r) => r.strand === st);
  if (!rooms || rooms.length < fewest || rooms[rooms.length - 1] !== strand || !at(rooms[0]) || at(rooms[0]).y !== 0) return false;
  for (let k = 1; k < rooms.length; k++) if (!at(rooms[k]) || !adjacent(at(rooms[k - 1]), at(rooms[k]))) return false;
  return true;
};
async function loadPlaywright() {
  if (process.env.PLAYWRIGHT_MODULE) return import(process.env.PLAYWRIGHT_MODULE);
  try { return await import('playwright'); } catch { /* not installed locally: try the global package */ }
  const root = execFileSync('npm', ['root', '-g'], { encoding: 'utf8' }).trim();
  return import(pathToFileURL(join(root, 'playwright', 'index.mjs')).href);
}
const { chromium } = await loadPlaywright();
const url = process.argv[2];
const opt = (k) => { const a = process.argv.slice(3).find((x) => x.startsWith(`--${k}=`)); return a === undefined ? null : a.slice(k.length + 3); };
if (!url || url.startsWith('--')) { console.log('FAIL usage: node web/browser_spaces.mjs <3d page url> [--shot=png] [--deep=id] [--pairs=a-b] [--halltest=id:hall,...]'); process.exit(2); }
const shot = opt('shot');
const allPairs = reg.spaces.flatMap((s) => s.walk.halls.map((w) => ({ s, w })));
const [pa, pb] = (opt('pairs') ?? `0-${allPairs.length - 1}`).split('-').map(Number);
const hallTests = new Set((opt('halltest') ?? '').split(',').filter(Boolean));

let n = 0, bad = 0;
const ok = (name, cond, detail) => {
  if (cond) { n++; console.log('  ok ' + name); return; }
  bad++; console.log('FAIL ' + name); if (detail !== undefined) console.log('     ' + JSON.stringify(detail));
};

const t0 = Date.now();
const b = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await b.newPage({ viewport: { width: 1280, height: 800 } });
const errs = [];
page.on('pageerror', (e) => errs.push(e.message));
const first = reg.spaces.find((x) => x.id === (opt('deep') ?? reg.spaces[0].id));
await page.goto(`${url}?space=${first.id}`, { waitUntil: 'load', timeout: 60000 });
await page.waitForFunction(() => window.__tc3d && window.__tc3dSpace && window.__tc3dSpace(), null, { timeout: 40000 });
await page.waitForTimeout(800);

/* 1. the deep link */
const st = await page.evaluate(() => window.__tc3dSpace());
const panel = await page.evaluate(() => { const el = document.getElementById('spacePanel'); return el && getComputedStyle(el).display !== 'none' ? el.textContent : null; });
ok(`deep link ?space=${first.id} opens ${first.walk.halls[0].hall}, the first hall that serves it`,
  st && st.id === first.id && st.hall === first.walk.halls[0].hall, st && { id: st.id, hall: st.hall });
ok('the space stands in the room of its strand', st && st.strand === first.strand, st && st.strand);
const items = first.items;
const want = { prop: items.filter((i) => i.kind === 'prop').length, furniture: items.filter((i) => i.kind === 'furniture').length };
const markers = items.filter((i) => !['prop', 'furniture'].includes(i.kind)).length;
ok('every prop and furniture piece is drawn and every other item stands as a marker', st && st.drawn.prop === want.prop && st.drawn.furniture === want.furniture && st.markers === markers, st && { drawn: st.drawn, markers: st.markers, want, markers_want: markers });
ok('the panel says AUTHORED and links the spaces page', !!panel && /AUTHORED space/.test(panel) && /not a measured venue/.test(panel), panel);
ok('the footprint lies inside the room', st && st.footprint.x0 >= st.room.x0 - 1e-6 && st.footprint.x1 <= st.room.x1 + 1e-6 && st.footprint.z0 >= st.room.z0 - 1e-6 && st.footprint.z1 <= st.room.z1 + 1e-6, st && { f: st.footprint, r: st.room });

/* 2 + 3. a walker, then the hall test, on the deep-linked space */
const w0 = await page.evaluate(() => window.__tc3dSpaceWalk());
ok(`a walker from outside the open front reaches the ${first.strand} room (${st.ghosts} of the pieces stand in a doorway lane and are not solid)`, w0.reached === true && w0.end === first.strand, w0);
ok('the rooms the walker entered, in order, run from the open front to the space\'s room through doorways the plan cuts, in no fewer rooms than the registry\'s fewest-door route',
  chainOk(first.walk.halls[0].hall, w0.rooms, first.strand, first.walk.halls[0].route.length), { walked: w0.rooms, route: first.walk.halls[0].route });
ok('the walk never stood inside a wall or a space item', w0.breaches === 0, w0);
const ht = await page.evaluate(() => window.__tc3dHallTest());
ok('hall test with the space standing: no room unreachable, no step inside a wall', ht.unreachable.length === 0 && ht.breaches === 0 && ht.reached > 0, ht);
if (shot) await page.screenshot({ path: shot });

/* 4. the (space, hall) pairs a..b */
const rows = [];
const slice = allPairs.slice(pa, pb + 1);
for (const { s, w } of slice) {
  const t1 = Date.now();
  const row = await page.evaluate(([id, hall, hallTest]) => {
    const st2 = window.__tc3dSpaceLoad(id, hall);
    const wk = window.__tc3dSpaceWalk();
    const ht2 = hallTest ? window.__tc3dHallTest() : null;
    return { id, hall, strand: st2.strand, drawn: st2.drawn, markers: st2.markers, solids: st2.solids, ghosts: st2.ghosts, lanes: st2.lanes,
             reached: wk.reached, end: wk.end, rooms: wk.rooms, why: wk.why, breaches: wk.breaches, seconds: wk.seconds, at: wk.at, margin: wk.margin, flooded: wk.flooded, waypoints: wk.waypoints, x: wk.x, z: wk.z, ht: ht2 };
  }, [s.id, w.hall, hallTests.has(`${s.id}:${w.hall}`)]);
  rows.push({ ...row, route: w.route, items: s.items, ms: Date.now() - t1 });
}
ok(`pairs ${pa}-${pb} (${slice.length}) were driven`, rows.length === slice.length && slice.length > 0, { driven: rows.length });
for (const r of rows) {
  const want2 = { prop: r.items.filter((i) => i.kind === 'prop').length, furniture: r.items.filter((i) => i.kind === 'furniture').length };
  const passes = chainOk(r.hall, r.rooms, r.strand, r.route.length);
  ok(`${r.id} in ${r.hall}: drawn as declared, a walker reaches the ${r.strand} room through doorways the plan cuts, no step inside a wall (${r.ghosts} ghost, ${r.solids} solid, route margin ${r.margin} m, ${r.ms} ms)`,
    r.drawn.prop === want2.prop && r.drawn.furniture === want2.furniture && r.reached === true && r.end === r.strand && r.breaches === 0 && passes,
    { why: r.why, end: r.end, rooms: r.rooms, route: r.route, drawn: r.drawn, breaches: r.breaches, at: r.at, margin: r.margin, flooded: r.flooded, waypoints: r.waypoints, x: r.x, z: r.z, seconds: r.seconds });
  if (r.ht) ok(`${r.id} in ${r.hall}: hall test with the space standing - every room reachable on foot, no step inside a wall`,
    r.ht.unreachable.length === 0 && r.ht.breaches === 0 && r.ht.reached > 0, r.ht);
}
ok('no page error', errs.length === 0, errs.slice(0, 3));
await b.close();
console.log(`browser_spaces: ${n} ok, ${bad} failed, ${Date.now() - t0} ms`);
if (bad) process.exit(1);
