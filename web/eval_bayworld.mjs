/**
 * A scorecard for the walkable Bay world (web/trade_craft_bay.html), measured in a real browser - the same opt-in
 * kind of eval as web/eval_parishes.mjs, through the page's own window.__parishes hooks (the Bay page IS the parish
 * page machinery with the Bay registries swapped in by web/build_bayworld.py).
 *
 * Run:  python3 -m http.server <port> --bind 127.0.0.1   (from the repo root)
 *       BAY_URL=http://127.0.0.1:<port>/web/trade_craft_bay.html flock $SP/chromium.lock node web/eval_bayworld.mjs [--measure] [--json] [--shots=<dir>]
 *
 * Probed counties: 06075 San Francisco (the start), 06001 Alameda (Oakland campus), 06081 San Mateo.
 * Views origin / border / overview per probed county; rows must hold: nothing pending, chunks = (2R+1)^2 in walk
 * views, land meshes = loaded counties, every land vertex at y = 0, zero fabric in the overview, zero page errors.
 * cross: every shared border touching a probed county is walked; the neighbour streams in before the step over.
 *
 * TARGETS (BASE, below) are the FIRST clean measured run (--measure, 02:47 UTC) on this machine, set BEFORE any optimisation, with the
 * parish eval's declared headroom rules unchanged: draw calls x1.25 (the scarce currency), triangles x1.5
 * (instance caps bound them), frame time x2 (software GL, shared machine), fabric floor x0.9. Never loosened.
 */
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';

const URL_BASE = process.env.BAY_URL ?? 'http://127.0.0.1:8841/web/trade_craft_bay.html';
const CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const JSON_OUT = process.argv.includes('--json');
const MEASURE_ONLY = process.argv.includes('--measure');
const shotArg = process.argv.find((a) => a.startsWith('--shots='));
const SHOTS = shotArg ? shotArg.slice(8) : null;
if (SHOTS) mkdirSync(SHOTS, { recursive: true });
const PROBE = ['06075', '06001', '06081'];
const CALL_HEADROOM = 1.25, TRI_HEADROOM = 1.5, MS_HEADROOM = 2, FABRIC_FLOOR = 0.9;
/* BASE: the FIRST clean measured run (--measure), 2026-09-29 02:47:56 UTC, BEFORE any optimisation: main-tree page
   web/trade_craft_bay.html (build_bayworld, 9 counties), Chromium/SwiftShader 1280x800, ready in 4513 ms, 0 page errors,
   machine shared by ~10 agents: load average 11.75 / 6.77 / 5.28 before and 10.44 / 6.87 / 5.35 after (log:
   scratchpad bay_eval_m2.json/.err). Why the numbers look like this: ~35-38 draw calls in walk views are mostly the
   FLEET kit's one InstancedMesh per vehicle family (54 vehicles parked) plus land, water, blocks, trees, borders and
   the pin families; overviews are 4-6 calls (fabric and fleet hidden by design). Frame times are 116-167 ms in walk
   views under that load, so MS_HEADROOM 2 is the declared allowance for a loaded software-GL machine - not a claim
   about real hardware. Targets = these rows x the parish eval's headroom rules (calls x1.25, tris x1.5, ms x2,
   fabric floor x0.9). Never loosened; a failing row is a regression or a heavier machine - re-measure, say which. */
const BASE = {
  '06075': {
    origin: { calls: 36, tris: 81_347, ms: 166.6, chunks: 49, fabric: 2_612 },
    border: { calls: 38, tris: 42_691, ms: 66.6, chunks: 49, fabric: 927 },
    overview: { calls: 6, tris: 2_945, ms: 16.7, chunks: 49, fabric: null },
  },
  '06001': {
    origin: { calls: 37, tris: 92_212, ms: 166.6, chunks: 49, fabric: 3_288 },
    border: { calls: 38, tris: 88_225, ms: 166.7, chunks: 49, fabric: 3_147 },
    overview: { calls: 6, tris: 3_295, ms: 16.7, chunks: 49, fabric: null },
  },
  '06081': {
    origin: { calls: 35, tris: 86_312, ms: 116.7, chunks: 49, fabric: 3_064 },
    border: { calls: 37, tris: 84_687, ms: 133.3, chunks: 49, fabric: 3_195 },
    overview: { calls: 4, tris: 1_320, ms: 16.7, chunks: 49, fabric: null },
  },
};
/* KNOWN water crossing (declared from the same first run, not a loosened target): the 06001|06075 shared arc is
   0.4 km of the coarse 1:10m outline lying in open bay (registry borders_note: "treat it as a water crossing ...
   not a road"). A walker from 40 m inside Alameda stays in 06001 - reported as its own row, not counted as a land
   crossing and not counted as a pass. Every other shared border must be walked across. */
const WATER_CROSSINGS = ['06001|06075'];

const browser = await chromium.launch({ executablePath: CHROME, args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const errors = [];
const EXPECTED_FAIL = [/basemap\.nationalmap\.gov/, /\/config\/runtime\.json/];
page.on('pageerror', (e) => errors.push(String(e)));
page.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push(m.text()); });
page.on('requestfailed', (r) => { if (!EXPECTED_FAIL.some((re) => re.test(r.url()))) errors.push('request failed: ' + r.url()); });
page.on('response', (r) => { if (r.status() >= 400 && !EXPECTED_FAIL.some((re) => re.test(r.url()))) errors.push(`HTTP ${r.status()} ${r.url()}`); });
const t0 = Date.now();
await page.goto(URL_BASE, { waitUntil: 'load' });
const ready = await page.waitForFunction(() => document.documentElement.dataset.parishesReady === '1', null, { timeout: 45000 }).then(() => true, () => false);
if (!ready) {
  console.log('FAIL  page never became ready (dataset.parishesReady) | errors: ' + (errors.join(' || ') || 'none captured'));
  await browser.close();
  process.exit(1);
}
const readyMs = Date.now() - t0;

const rows = [];
let bad = 0;
const fail = (row, msg) => { row.fails.push(msg); };
for (const pid of PROBE) {
  for (const v of ['origin', 'border', 'overview']) {
    await page.evaluate(([name, id]) => window.__parishes.view(name, id), [v, pid]);
    await page.waitForFunction(() => window.__parishes.stats().pending === 0, null, { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(300);
    const times = await page.evaluate(() => window.__parishes.frameTimes(6));
    const st = await page.evaluate(() => window.__parishes.stats());
    times.sort((a, b) => a - b);
    const ms = +times[Math.floor(times.length / 2)].toFixed(1);
    const fabric = st.instances.block + st.instances.tree;
    const row = { county: pid, view: v, calls: st.calls, tris: st.triangles, ms, chunks: st.chunks, pending: st.pending, fabric, loaded: st.loaded.length, fails: [] };
    if (st.pending !== 0) fail(row, `${st.pending} chunks still pending`);
    if (!st.groundY) fail(row, 'a land mesh vertex is not at y = 0 (flat AUTHORED ground)');
    if (st.landMeshes !== st.loaded.length) fail(row, `${st.landMeshes} land meshes for ${st.loaded.length} loaded counties`);
    if (v !== 'overview' && st.chunks !== (2 * st.radius + 1) ** 2) fail(row, `${st.chunks} chunks, expected ${(2 * st.radius + 1) ** 2}`);
    if (v === 'overview' && fabric !== 0) fail(row, `${fabric} fabric instances drawn in the overview`);
    if (v !== 'overview' && fabric === 0) fail(row, 'no AUTHORED fabric (blocks/trees) stands in a walk view');
    const base = BASE && BASE[pid] && BASE[pid][v];
    if (!MEASURE_ONLY && !base) fail(row, `no declared target for ${pid} ${v}`);
    if (!MEASURE_ONLY && base) {
      if (st.calls > Math.ceil(base.calls * CALL_HEADROOM)) fail(row, `calls ${st.calls} > ${Math.ceil(base.calls * CALL_HEADROOM)}`);
      if (st.triangles > base.tris * TRI_HEADROOM) fail(row, `tris ${st.triangles} > ${Math.round(base.tris * TRI_HEADROOM)}`);
      if (ms > base.ms * MS_HEADROOM) fail(row, `frame ${ms} ms > ${(base.ms * MS_HEADROOM).toFixed(1)}`);
      if (base.fabric !== null && fabric < base.fabric * FABRIC_FLOOR) fail(row, `fabric ${fabric} < floor ${Math.round(base.fabric * FABRIC_FLOOR)}`);
    }
    if (SHOTS && v !== 'border') await page.screenshot({ path: `${SHOTS}/BAY-${pid}-${v}.png` });
    if (row.fails.length) bad++;
    rows.push(row);
  }
}
const pairs = await page.evaluate(() => window.__parishes.pairs());
const cross = [];
for (const [a, b] of pairs.filter(([a, b]) => PROBE.includes(a) || PROBE.includes(b))) {
  const r = await page.evaluate(([x, y]) => window.__parishes.cross(x, y), [a, b]);
  const row = { probe: 'cross', pair: `${a}|${b}`, steps: r.steps, fails: [] };
  if (WATER_CROSSINGS.includes([a, b].sort().join('|'))) { row.known = 'water crossing (open bay, not walkable)'; row.after = r.after.current; cross.push(row); continue; }
  if (r.after.current !== b) fail(row, `after ${r.steps} steps the current county is ${r.after.current}, not ${b}`);
  if (!r.before.loaded.includes(b)) fail(row, `neighbour ${b} was not streamed in before the border`);
  if (row.fails.length) bad++;
  cross.push(row);
}
const fleet = await page.evaluate(() => window.__parishes.fleet());
const fleetRow = { probe: 'fleet', parked: fleet.parked, land: fleet.land, water: fleet.water, wrongMedium: fleet.wrongMedium.length, fails: [] };
if (fleet.wrongMedium.length) fail(fleetRow, `parked on the wrong medium: ${fleet.wrongMedium.join(', ')}`);
if (fleetRow.fails.length) bad++;
const errRow = { probe: 'errors', count: errors.length, first: errors.slice(0, 3), readyMs, fails: [] };
if (errors.length) { fail(errRow, `${errors.length} page errors`); bad++; }
await browser.close();
const out = { page: URL_BASE, measure: MEASURE_ONLY, rows, cross, fleet: fleetRow, errors: errRow, bad };
if (JSON_OUT) console.log(JSON.stringify(out, null, 1));
else {
  for (const r of rows) console.log(`${r.fails.length ? 'FAIL' : '  ok'}  ${r.county} ${r.view.padEnd(8)} calls ${r.calls} tris ${r.tris} ${r.ms} ms chunks ${r.chunks} fabric ${r.fabric} loaded ${r.loaded}${r.fails.length ? ' | ' + r.fails.join('; ') : ''}`);
  for (const r of cross) console.log(`${r.known ? 'KNOWN' : r.fails.length ? 'FAIL' : '  ok'}  cross ${r.pair} (${r.steps} steps)${r.known ? ' | ' + r.known + ', ended in ' + r.after : ''}${r.fails.length ? ' | ' + r.fails.join('; ') : ''}`);
  console.log(`${fleetRow.fails.length ? 'FAIL' : '  ok'}  fleet parked ${fleetRow.parked} (land ${fleetRow.land}, water ${fleetRow.water})`);
  console.log(`${errRow.fails.length ? 'FAIL' : '  ok'}  page errors ${errRow.count}, ready in ${readyMs} ms ${errRow.first.join(' || ')}`);
  console.log(`\n${bad ? bad + ' rows FAIL' : 'all rows hold'}${MEASURE_ONLY ? ' (measure mode: no targets applied)' : ''}`);
}
process.exit(bad ? 1 : 0);
