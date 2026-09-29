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
/* WORLDS (wave 10): offshore restoration pins (record pin:true, point outside every coarse outline) stand in open water
   at their RECORDED point: not standable on foot, boat-standable, labelled in the 06075 walk view, and the pin costs no
   extra draw call beyond the view's declared BASE headroom (it rides the existing 'other' landmark family) */
const off = await page.evaluate(async () => {
  const D = JSON.parse(document.getElementById('parishes-data').textContent);
  const pins = D.parishes.flatMap((p) => p.landmarks.filter((l) => l.kind === 'restoration site (offshore pin)').map((l) => ({ id: l.id, x: l.x, z: l.z, county: p.id })));
  const P = window.__parishes; const out = [];
  for (const l of pins) {
    P.view('origin', l.county); await new Promise((r) => setTimeout(r, 400));
    out.push({ id: l.id, walk: P.canStand('walk', l.x, l.z), boat: P.canStand('boat', l.x, l.z), label: !!document.querySelector(`.lbl.lm[data-landmark="${l.id}"]`), calls: P.stats().calls });
  }
  return out;
});
const offRow = { probe: 'offshore', pins: off, fails: [] };
if (SHOTS && off.length) { await page.evaluate(() => window.__parishes.view('overview', '06075')); await page.waitForTimeout(500); await page.screenshot({ path: `${SHOTS}/WORLDS-bay-offshore-overview.png` }); }
if (off.length !== 1) fail(offRow, `${off.length} offshore pins, expected 1 (treasure-island-nsti)`);
for (const o of off) {
  if (o.walk !== false || o.boat !== true) fail(offRow, `${o.id} walk ${o.walk} boat ${o.boat}: an offshore pin stands in open water`);
  if (!o.label) fail(offRow, `${o.id} has no in-world label in its county's walk view`);
  if (!MEASURE_ONLY && BASE && o.calls > Math.ceil(BASE['06075'].origin.calls * CALL_HEADROOM)) fail(offRow, `${o.calls} calls with the pin > the 06075 origin headroom`);
}
if (offRow.fails.length) bad++;
/* WORLDS w13 (ADDED row; no target changed): FIELDS' AUTHORED plots (seasons/registry/seasons.json) stay free of
   generated fabric. The page builds each plot's covering chunks fresh (__parishes.plotProbe, pure, not drawn) with its plot
   clearance on - and off, to measure what the rule removes; THIS eval judges overlap with its own geometry: an oriented
   building box vs the plot rectangle (separating axes), a tree crown disc vs the rectangle, a lamp point in the bed. */
const plotD = await page.evaluate(() => ({ probe: window.__parishes.plotProbe(), n: JSON.parse(document.getElementById('parishes-data').textContent).plots_clear.length }));
function plotHits(p, f) {
  const box = ([x, z, w, , d, , yaw]) => { const u = [Math.cos(yaw), -Math.sin(yaw)], v = [Math.sin(yaw), Math.cos(yaw)], c = [x - p.x, z - p.z];
    return [[1, 0], [0, 1], u, v].every((a) => Math.abs(c[0] * a[0] + c[1] * a[1]) < p.hw * Math.abs(a[0]) + p.hd * Math.abs(a[1]) + (w / 2) * Math.abs(u[0] * a[0] + u[1] * a[1]) + (d / 2) * Math.abs(v[0] * a[0] + v[1] * a[1])); };
  const disc = ([x, z, s]) => Math.hypot(Math.max(0, Math.abs(x - p.x) - p.hw), Math.max(0, Math.abs(z - p.z) - p.hd)) < 2.2 * s;
  const pt = ([x, z]) => Math.abs(x - p.x) < p.hw + 0.5 && Math.abs(z - p.z) < p.hd + 0.5;
  return { b: f.block.filter(box).length, t: f.tree.filter(disc).length, l: f.lamp.filter(pt).length };
}
const plotRow = { probe: 'plots', plots: plotD.probe.length, onLand: plotD.probe.filter((p) => p.land).length, buildingsOn: 0, treesOn: 0, lampsOn: 0, plotsWithBuildingWithoutRule: 0, buildingsWithoutRule: 0, fails: [] };
for (const p of plotD.probe) {
  const on = plotHits(p, p.on), off = plotHits(p, p.off);
  plotRow.buildingsOn += on.b; plotRow.treesOn += on.t; plotRow.lampsOn += on.l; plotRow.buildingsWithoutRule += off.b; if (off.b) plotRow.plotsWithBuildingWithoutRule++;
  if (on.b + on.t + on.l) fail(plotRow, `${p.id}: ${on.b} buildings, ${on.t} trees, ${on.l} lamps stand on the plot bed`);
}
if (!(plotD.n > 0 && plotD.probe.length === plotD.n)) fail(plotRow, `${plotD.probe.length} plots probed of ${plotD.n} embedded`);
if (plotRow.fails.length) bad++;
/* BEGIN VEG w14 (VEG·Vegetation & Detail; ADDED row, no target changed): regional vegetation and street detail
   (web/florakit.py, flora/registry/flora.json) in the 06075 origin walk view: families present with instances > 0, the kit's own
   draw calls (page calls with flora on minus off, same frame) <= the registry's draw_calls_max and its triangles <= tris_max;
   in the overview the kit draws 0 calls and the page's calls are the same with flora on and off. The view rows above
   already judge the page's calls/tris WITH flora mounted (it is on by default). */
const vegD = await page.evaluate(async () => {
  const P = window.__parishes, F = window.__flora, sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const frames = (k) => new Promise((res) => { let i = 0; const f = () => (++i >= k ? res() : requestAnimationFrame(f)); requestAnimationFrame(f); });
  if (!F) return null;
  for (let i = 0; i < 100 && window.__floraLC && window.__floraLC() === 'loading'; i++) await sleep(100);   // RECORDED land cover (VEG w14)
  P.view('origin', '06075');
  for (let i = 0; i < 80; i++) { if (P.stats().pending === 0 && F.stats().queue === 0 && i > 5) break; await sleep(150); }
  await frames(4); const on = P.stats(), fs = F.stats(); F.setEnabled(false); await frames(4); const off = P.stats(); F.setEnabled(true); await frames(4);
  P.view('overview', '06075'); await sleep(600); await frames(4); const ovOn = P.stats(), fo = F.stats(); F.setEnabled(false); await frames(4); const ovOff = P.stats(); F.setEnabled(true);
  P.view('origin', '06075'); await sleep(300);
  return { lcState: window.__floraLC ? window.__floraLC() : 'not mounted', on: on.calls, off: off.calls, trisOn: on.triangles, trisOff: off.triangles, fs, ovCalls: fo.drawCalls, ovOn: ovOn.calls, ovOff: ovOff.calls, budgets: F.budgets };
});
const vegRow = { probe: 'vegetation', view: '06075 origin', fails: [] };
if (!vegD) fail(vegRow, 'window.__flora is not mounted');
else {
  Object.assign(vegRow, { families: Object.fromEntries(Object.entries(vegD.fs.families).filter(([, c]) => c > 0)), species: vegD.fs.species, kitCalls: vegD.on - vegD.off,
    kitTris: vegD.trisOn - vegD.trisOff, floraTris: vegD.fs.tris, overviewKitCalls: vegD.ovCalls, overviewCalls: `${vegD.ovOn}/${vegD.ovOff}` });
  vegRow.landcover = { grid: vegD.lcState, ...vegD.fs.landcover };   // share of drawn plants placed by a RECORDED WorldCover class; the rest AUTHORED (counted)
  if (vegD.lcState !== 'RECORDED') fail(vegRow, `RECORDED land cover not loaded: ${vegD.lcState}`);

  const fam = Object.keys(vegRow.families);
  /* Bay 06075 origin: RECORDED WorldCover says built-up (50) around the San Francisco frame origin, where the flora rules draw
     street details only (plants: street trees of the page's own AUTHORED fabric) - so plants are reported, not required here */
  if (fam.length < 1) fail(vegRow, `flora families present ${JSON.stringify(vegD.fs.families)} (want >= 1 with instances)`);
  if (vegRow.kitCalls < 1 || vegRow.kitCalls > vegD.budgets.draw_calls_max) fail(vegRow, `flora draw calls ${vegRow.kitCalls} (want 1..${vegD.budgets.draw_calls_max})`);
  if (vegD.fs.tris > vegD.budgets.tris_max) fail(vegRow, `flora triangles ${vegD.fs.tris} > tris_max ${vegD.budgets.tris_max}`);
  if (vegD.ovCalls !== 0 || vegD.ovOn !== vegD.ovOff) fail(vegRow, `overview: flora calls ${vegD.ovCalls}, page calls on/off ${vegD.ovOn}/${vegD.ovOff}`);
}
if (vegRow.fails.length) bad++;
/* END VEG w14 */
/* BEGIN ELEV w14 relief row (web/eval_relief.mjs, NEW): ?relief=on - RECORDED USGS 3DEP in use with its legend, relief present,
   max slope <= the page's declared max_slope, N buildings/lots/trees/lamps/parked vehicles on the ground within 0.1 m, draw calls
   equal to relief off at the start view, water level unchanged. Relief is default OFF, so every row above judges the flat page. */
const { reliefRow } = await import('./eval_relief.mjs');
const elevRow = await reliefRow(browser, URL_BASE, { shots: SHOTS, name: 'bay' });
if (elevRow.fails.length) bad++;
if (!JSON_OUT) console.log(`${elevRow.fails.length ? 'FAIL' : '  ok'} relief ${JSON.stringify(Object.fromEntries(Object.entries(elevRow).filter(([k]) => k !== 'fails' && k !== 'probe')))}${elevRow.fails.length ? ' :: ' + elevRow.fails.join('; ') : ''}`);
/* END ELEV w14 */
const errRow = { probe: 'errors', count: errors.length, first: errors.slice(0, 3), readyMs, fails: [] };
if (errors.length) { fail(errRow, `${errors.length} page errors`); bad++; }
await browser.close();
const out = { page: URL_BASE, measure: MEASURE_ONLY, plots: plotRow, rows, cross, fleet: fleetRow, offshore: offRow, errors: errRow, bad };
if (JSON_OUT) console.log(JSON.stringify(out, null, 1));
else {
  for (const r of rows) console.log(`${r.fails.length ? 'FAIL' : '  ok'}  ${r.county} ${r.view.padEnd(8)} calls ${r.calls} tris ${r.tris} ${r.ms} ms chunks ${r.chunks} fabric ${r.fabric} loaded ${r.loaded}${r.fails.length ? ' | ' + r.fails.join('; ') : ''}`);
  for (const r of cross) console.log(`${r.known ? 'KNOWN' : r.fails.length ? 'FAIL' : '  ok'}  cross ${r.pair} (${r.steps} steps)${r.known ? ' | ' + r.known + ', ended in ' + r.after : ''}${r.fails.length ? ' | ' + r.fails.join('; ') : ''}`);
  console.log(`${fleetRow.fails.length ? 'FAIL' : '  ok'}  fleet parked ${fleetRow.parked} (land ${fleetRow.land}, water ${fleetRow.water})`);
  console.log(`${offRow.fails.length ? 'FAIL' : '  ok'}  offshore ${JSON.stringify(offRow.pins)}${offRow.fails.length ? ' | ' + offRow.fails.join('; ') : ''}`);
  console.log(`${errRow.fails.length ? 'FAIL' : '  ok'}  page errors ${errRow.count}, ready in ${readyMs} ms ${errRow.first.join(' || ')}`);
  console.log(`${plotRow.fails.length ? 'FAIL' : '  ok'}  plots ${JSON.stringify(Object.fromEntries(Object.entries(plotRow).filter(([k]) => k !== 'fails' && k !== 'probe')))}${plotRow.fails.length ? ' | ' + plotRow.fails.join('; ') : ''}`);
  /* BEGIN VEG w14 */ console.log(`${vegRow.fails.length ? 'FAIL' : '  ok'} ${vegRow.probe} ${JSON.stringify(Object.fromEntries(Object.entries(vegRow).filter(([k]) => k !== 'fails' && k !== 'probe')))}${vegRow.fails.length ? ' :: ' + vegRow.fails.join('; ') : ''}`); /* END VEG w14 */
  console.log(`\n${bad ? bad + ' rows FAIL' : 'all rows hold'}${MEASURE_ONLY ? ' (measure mode: no targets applied)' : ''}`);
}
process.exit(bad ? 1 : 0);
