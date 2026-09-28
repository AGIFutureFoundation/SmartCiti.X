/**
 * A scorecard for the parish world (web/trade_craft_parishes.html), measured
 * in a real browser - the same kind of opt-in eval as web/eval_wilds.mjs, for
 * the same reason: draw calls, instance counts, streaming and frame time
 * cannot be read from the source.
 *
 * Run:  python3 -m http.server 8813 --bind 127.0.0.1   (from the repo root)
 *       flock $SP/chromium.lock node web/eval_parishes.mjs [--json] [--measure] [--shots=<dir>]
 *
 * Views, driven by the page's own window.__parishes hooks:
 *   origin    the start spot: 90 m south of the parish's first landmark, facing it (else the frame origin)
 *   border    40 m inside the parish from the middle of its longest shared border
 *   overview  the whole parish from above (fabric hidden by design)
 * Behaviour probes (each a named row that must hold, not a budget):
 *   cross     walking over every shared border of the probed parishes changes the current parish, the neighbour
 *             is loaded BEFORE the step over, and a border marker names both parishes;
 *   ride      a land vehicle drives and never leaves land, a boat moves and never leaves water (FLEET);
 *   satellite the toggle requests USGS imagery in the browser only and shows the Mapbox refusal text verbatim
 *             when no operator token exists;
 *   ground    every loaded land mesh lies at exactly y = 0 (flat AUTHORED ground, no real elevation).
 *
 * Targets are DECLARED with reasons, MEASURED-HERE like eval_wilds: draw calls get 25% headroom (the scarce
 * currency), triangles 1.5x (instance caps bound them), frame time 2x (software GL on a shared machine).
 * Chunks are held exactly: 49 is (2*RADIUS+1)^2 with RADIUS 3 - any other number in a walk view is a streaming bug.
 * Fabric instances are held to a FLOOR of 0.9x in the walk views - a city bought cheap by building nothing is not
 * a city. Fleet draw calls are held to <= the number of families (one InstancedMesh per family, FLEET contract).
 */
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';

const URL_BASE = process.env.PARISHES_URL ?? 'http://127.0.0.1:8813/web/trade_craft_parishes.html';
const CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const JSON_OUT = process.argv.includes('--json');
const MEASURE_ONLY = process.argv.includes('--measure');
const shotArg = process.argv.find((a) => a.startsWith('--shots='));
const SHOTS = shotArg ? shotArg.slice(8) : null;
if (SHOTS) mkdirSync(SHOTS, { recursive: true });

/* Parishes probed: Orleans (the start), Jefferson and St. Tammany (the largest water crossings). */
const PROBE = ['22071', '22051', '22103'];
/* BASE: measured 2026-09-28 18:52 UTC on a frozen copy (page 5073dc4e0aeeb6b7; log scratchpad
   parishes_w5_eval_measure.log), Chromium/SwiftShader 1280x800, other agents sharing the machine.
   Why the calls are ~40: 34 of them are the FLEET contract's one InstancedMesh per vehicle family (all 70 vehicles
   parked across the 13 parishes, drawn by family whatever their count); the rest are the land meshes of the loaded
   parishes, water, blocks, trees, border markers and the 5 landmark families. fabric = blocks + trees standing
   (floor 0.9x; null in the overview, where fabric is hidden by design). */
const BASE = {
  '22071': {
    origin: { calls: 42, tris: 73_181, ms: 100, chunks: 49, fabric: 2_585 },
    border: { calls: 42, tris: 72_815, ms: 100, chunks: 49, fabric: 2_548 },
    overview: { calls: 40, tris: 14_549, ms: 16.7, chunks: 49, fabric: null },
  },
  '22051': {
    origin: { calls: 39, tris: 73_432, ms: 100.1, chunks: 49, fabric: 2_605 },
    border: { calls: 40, tris: 72_749, ms: 83.3, chunks: 49, fabric: 2_567 },
    overview: { calls: 37, tris: 14_045, ms: 33.4, chunks: 49, fabric: null },
  },
  '22103': {
    origin: { calls: 39, tris: 72_515, ms: 100.1, chunks: 49, fabric: 2_563 },
    border: { calls: 41, tris: 73_761, ms: 83.4, chunks: 49, fabric: 2_606 },
    overview: { calls: 39, tris: 13_993, ms: 33.3, chunks: 49, fabric: null },
  },
};
/* the overview's 16.7 ms (Orleans) is one vsync interval; its 2x budget (33.4 ms) is two - held as measured */
const CALL_HEADROOM = 1.25, TRI_HEADROOM = 1.5, MS_HEADROOM = 2, FABRIC_FLOOR = 0.9;

const browser = await chromium.launch({ executablePath: CHROME, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const errors = [];
/* the only request allowed to fail: the USGS tile (this sandbox blocks the host) and the absent operator config */
const EXPECTED_FAIL = [/basemap\.nationalmap\.gov/, /\/config\/runtime\.json/];
page.on('pageerror', (e) => errors.push(String(e)));
page.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push(m.text()); });
page.on('requestfailed', (r) => { if (!EXPECTED_FAIL.some((re) => re.test(r.url()))) errors.push('request failed: ' + r.url()); });
page.on('response', (r) => { if (r.status() >= 400 && !EXPECTED_FAIL.some((re) => re.test(r.url()))) errors.push(`HTTP ${r.status()} ${r.url()}`); });
await page.goto(URL_BASE, { waitUntil: 'load' });
await page.waitForFunction(() => document.documentElement.dataset.parishesReady === '1', null, { timeout: 60000 });

const rows = [];
let bad = 0;
const fail = (row, msg) => { row.fails.push(msg); };
for (const pid of PROBE) {
  for (const v of ['origin', 'border', 'overview']) {
    await page.evaluate(([name, id]) => window.__parishes.view(name, id), [v, pid]);
    await page.waitForTimeout(350);
    const times = await page.evaluate(() => window.__parishes.frameTimes(6));
    const st = await page.evaluate(() => window.__parishes.stats());
    times.sort((a, b) => a - b);
    const ms = +times[Math.floor(times.length / 2)].toFixed(1);
    const fabric = st.instances.block + st.instances.tree;
    const row = { parish: pid, view: v, calls: st.calls, tris: st.triangles, ms, chunks: st.chunks, pending: st.pending, fabric, loaded: st.loaded.length, fails: [] };
    if (st.pending !== 0) fail(row, `${st.pending} chunks still pending`);
    if (!st.instancedFamilies) fail(row, 'an asset family is not an InstancedMesh');
    if (st.fabricMeshes !== 2) fail(row, `${st.fabricMeshes} fabric meshes; blocks and trees are ONE InstancedMesh each`);
    if (!st.groundY) fail(row, 'a land mesh vertex is not at y = 0 (flat AUTHORED ground)');
    if (st.landMeshes !== st.loaded.length) fail(row, `${st.landMeshes} land meshes for ${st.loaded.length} loaded parishes`);
    if (v !== 'overview' && st.chunks !== (2 * st.radius + 1) ** 2) fail(row, `${st.chunks} chunks, expected ${(2 * st.radius + 1) ** 2}`);
    if (v === 'overview' && fabric !== 0) fail(row, `${fabric} fabric instances drawn in the overview`);
    const base = BASE[pid] && BASE[pid][v];
    if (!MEASURE_ONLY && !base) fail(row, `no declared target for ${pid} ${v}`);
    if (!MEASURE_ONLY && base) {
      if (st.calls > Math.ceil(base.calls * CALL_HEADROOM)) fail(row, `calls ${st.calls} > ${Math.ceil(base.calls * CALL_HEADROOM)}`);
      if (st.triangles > base.tris * TRI_HEADROOM) fail(row, `tris ${st.triangles} > ${Math.round(base.tris * TRI_HEADROOM)}`);
      if (ms > base.ms * MS_HEADROOM) fail(row, `frame ${ms} ms > ${(base.ms * MS_HEADROOM).toFixed(1)}`);
      if (base.fabric !== null && fabric < base.fabric * FABRIC_FLOOR) fail(row, `fabric ${fabric} < floor ${Math.round(base.fabric * FABRIC_FLOOR)}`);
    }
    if (SHOTS && v !== 'border') await page.screenshot({ path: `${SHOTS}/WILDS-w5-${pid}-${v}.png` });
    if (row.fails.length) bad++;
    rows.push(row);
  }
}

/* cross: every shared border touching a probed parish, walked from 40 m inside */
const pairs = await page.evaluate(() => window.__parishes.pairs());
const cross = [];
for (const [a, b] of pairs.filter(([a, b]) => PROBE.includes(a) || PROBE.includes(b))) {
  const r = await page.evaluate(([x, y]) => window.__parishes.cross(x, y), [a, b]);
  const row = { probe: 'cross', pair: `${a}|${b}`, steps: r.steps, fails: [] };
  if (r.after.current !== b) fail(row, `after walking ${r.steps} steps the current parish is ${r.after.current}, not ${b}`);
  if (!r.before.loaded.includes(b)) fail(row, `neighbour ${b} was not streamed in before the border`);
  if (!r.marker.includes([a, b].sort().join('|'))) fail(row, `no border marker names ${a}|${b}`);
  if (row.fails.length) bad++;
  cross.push(row);
}

/* ride: FLEET vehicles on their own medium */
const fleet = await page.evaluate(() => window.__parishes.fleet());
const rideRows = [];
{
  const row = { probe: 'fleet', parked: fleet.parked, land: fleet.land, water: fleet.water, drawCalls: fleet.drawCalls, fails: [] };
  if (fleet.wrongMedium.length) fail(row, `parked on the wrong medium: ${fleet.wrongMedium.join(', ')}`);
  if (fleet.land < 1 || fleet.water < 1) fail(row, 'the world parks no land vehicle or no boat');
  if (row.fails.length) bad++;
  rideRows.push(row);
  for (const medium of ['land', 'water']) {
    const r = await page.evaluate((m) => { const o = window.__parishes.ride(m, 4); return o; }, medium);
    await page.waitForTimeout(250);
    if (SHOTS) await page.screenshot({ path: `${SHOTS}/WILDS-w5-ride-${medium}.png` });
    const out = await page.evaluate(() => window.__parishes.exit());
    const rr = { probe: 'ride', medium, id: r.id, moved: +r.moved.toFixed(1), wrongMediumSteps: r.wrongMediumSteps, exited: out.ok, fails: [] };
    if (r.moved < 1) fail(rr, `${r.id} moved ${r.moved.toFixed(2)} m under full throttle`);
    if (r.wrongMediumSteps) fail(rr, `${r.id} spent ${r.wrongMediumSteps} steps on the wrong medium`);
    if (rr.fails.length) bad++;
    rideRows.push(rr);
  }
}

/* npcs: a guide in Orleans answers with a line quoted verbatim from its registry entry */
const npcInfo = await page.evaluate(() => window.__parishes.npcs());
const npcRow = { probe: 'npcs', count: npcInfo && npcInfo.count, fails: [] };
if (!npcInfo || npcInfo.count < 1) fail(npcRow, 'no NPC guide placed');
else {
  const t = await page.evaluate(() => window.__parishes.talkIn('22071'));
  const reg = await page.evaluate(() => JSON.parse(document.getElementById('parish-npcs').textContent).npcs);
  const me = reg.find((n) => n.id === t.id);
  npcRow.id = t.id; npcRow.source = t.source;
  if (!t.open) fail(npcRow, 'the dialogue panel did not open');
  if (!me || !me.knowledge.some((k) => k.text === t.line && k.source === t.source)) fail(npcRow, `line ${JSON.stringify(t.line)} is not a verbatim registry quote with its source`);
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/WILDS-w5-npc.png` });
  await page.keyboard.press('Escape');
}
if (npcRow.fails.length) bad++;

/* satellite: view-time only, refusal text verbatim without a token */
await page.evaluate(() => window.__parishes.view('origin', '22071'));
const sat = await page.evaluate(() => window.__parishes.satellite(true));
await page.waitForTimeout(1500);
const sat2 = await page.evaluate(() => window.__parishes.satState());
const satRow = { probe: 'satellite', src: sat.src, token: sat.token, msg: sat2.msg, fails: [] };
if (!/^https:\/\/basemap\.nationalmap\.gov\//.test(sat.src || '')) fail(satRow, `satellite requested ${sat.src}, not USGS`);
if (!sat.token && !sat2.msg.includes('Mapbox satellite: off - no token configured')) fail(satRow, 'the Mapbox refusal text is missing');
if (SHOTS) await page.screenshot({ path: `${SHOTS}/WILDS-w5-satellite.png` });
await page.evaluate(() => window.__parishes.satellite(false));
if (satRow.fails.length) bad++;

/* styles: the panels follow the Style switcher (tokens only) */
if (SHOTS) {
  for (const s of ['hivis', 'enterprise']) {
    await page.evaluate((id) => document.documentElement.setAttribute('data-style', id), s);
    await page.waitForTimeout(300);
    await page.screenshot({ path: `${SHOTS}/WILDS-w5-style-${s}.png` });
  }
}
await browser.close();

const out = { rows, cross, ride: rideRows, npcs: npcRow, satellite: satRow, errors, bad: bad + errors.length };
if (JSON_OUT) console.log(JSON.stringify(out, null, 1));
else {
  for (const r of rows) console.log(`${r.fails.length ? 'FAIL' : '  ok'} ${r.parish} ${r.view.padEnd(8)} calls ${r.calls} tris ${r.tris} ms ${r.ms} chunks ${r.chunks} fabric ${r.fabric} loaded ${r.loaded}${r.fails.length ? ' :: ' + r.fails.join('; ') : ''}`);
  for (const r of cross) console.log(`${r.fails.length ? 'FAIL' : '  ok'} cross ${r.pair} steps ${r.steps}${r.fails.length ? ' :: ' + r.fails.join('; ') : ''}`);
  for (const r of rideRows) console.log(`${r.fails.length ? 'FAIL' : '  ok'} ${r.probe} ${JSON.stringify(Object.fromEntries(Object.entries(r).filter(([k]) => k !== 'fails' && k !== 'probe')))}${r.fails.length ? ' :: ' + r.fails.join('; ') : ''}`);
  console.log(`${npcRow.fails.length ? 'FAIL' : '  ok'} npcs ${npcRow.count} ${npcRow.id} ${npcRow.source}${npcRow.fails.length ? ' :: ' + npcRow.fails.join('; ') : ''}`);
  console.log(`${satRow.fails.length ? 'FAIL' : '  ok'} satellite ${satRow.src} :: ${satRow.msg}${satRow.fails.length ? ' :: ' + satRow.fails.join('; ') : ''}`);
  for (const e of errors) console.log('FAIL page error: ' + e);
  console.log(bad + errors.length ? `eval_parishes: ${bad + errors.length} FAIL` : 'eval_parishes: all rows within target');
}
process.exit(bad + errors.length ? 1 : 0);
