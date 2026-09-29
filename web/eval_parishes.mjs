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
 * The overview renders at OVERVIEW_PR 0.6 of the walk pixel ratio (wave 5b): with 12 draws and ~10k triangles
 * it is fill-bound under SwiftShader, and at overview altitude one pixel is already tens of metres of flat
 * ground. The DIAG row measures the Orleans overview at full and at 0.6 scale in the same run to show the cost
 * is per-pixel; it is a diagnosis, not a target. No target was changed.
 * Wave 6: DIAG 5b 33.3 vs 33.3 ms, w6 run 1 49.9 vs 50.0 ms, w6 run 2 (draped ground texture) 49.9 vs 33.3 ms:
 * scale 1 was slower once the ground is textured, so OVERVIEW_PR stays 0.6.
 * Chunks are held exactly: 49 is (2*RADIUS+1)^2 with RADIUS 3 - any other number in a walk view is a streaming bug.
 * Fabric instances are held to a FLOOR of 0.9x in the walk views - a city bought cheap by building nothing is not
 * a city. Fleet draw calls are held to <= the number of families (one InstancedMesh per family, FLEET contract).
 *
 * Wave 6 (realism) adds MEASURED rows with reasons; no existing target changed:
 *   kit        the AUTHORED building kit - house (gable + porch), midrise (flat roof; also industrial shells) - each ONE
 *              InstancedMesh: every walk view measures the draw calls per fabric family as (calls with all) minus
 *              (calls with that family hidden) and holds each to <= 1. Windows are a shader pattern (0 triangles);
 *              the kit's roofs and porches are paid for by open-ended trees (14 triangles, was 32).
 *   ground     PARISH v1.3 label-free ground tiles, 16 per parish composed into ONE texture per loaded parish (the
 *              land stays one mesh, one draw call, exactly y = 0): every loaded parish's tiles load, none fails.
 *   atmosphere the sky is a CSS gradient behind a transparent canvas (0 draw calls), the fog is its horizon colour,
 *              a declared sun direction; water gets a fresnel sky reflection + ripple on its one material.
 *   satrace    REVIEW wave 6: toggling satellite on -> off -> on during the config fetch leaves exactly one image.
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
    /* wave 5b headroom: vehicles and guides are sub-pixel from overview altitude and are not drawn there */
    if (v === 'overview' && st.fleetVisible !== false) fail(row, 'the fleet is drawn in the overview');
    if (v !== 'overview' && st.fleetVisible === false) fail(row, 'the fleet is hidden in a walk view');
    row.lamps = st.instances.lamp;
    if (v !== 'overview') {
      const fc = await page.evaluate(() => window.__parishes.familyCalls());
      row.kit = st.kit; row.familyCalls = fc;
      for (const [k, c] of Object.entries(fc)) if (c > 1) fail(row, `fabric family ${k} costs ${c} draw calls (one InstancedMesh = 1)`);
      if (!(st.kit.house > 0 && st.kit.midrise > 0)) fail(row, `building kit families empty: ${JSON.stringify(st.kit)}`);
    }
    const base = BASE[pid] && BASE[pid][v];
    if (!MEASURE_ONLY && !base) fail(row, `no declared target for ${pid} ${v}`);
    if (!MEASURE_ONLY && base) {
      if (st.calls > Math.ceil(base.calls * CALL_HEADROOM)) fail(row, `calls ${st.calls} > ${Math.ceil(base.calls * CALL_HEADROOM)}`);
      if (st.triangles > base.tris * TRI_HEADROOM) fail(row, `tris ${st.triangles} > ${Math.round(base.tris * TRI_HEADROOM)}`);
      if (ms > base.ms * MS_HEADROOM) fail(row, `frame ${ms} ms > ${(base.ms * MS_HEADROOM).toFixed(1)}`);
      if (base.fabric !== null && fabric < base.fabric * FABRIC_FLOOR) fail(row, `fabric ${fabric} < floor ${Math.round(base.fabric * FABRIC_FLOOR)}`);
    }
    if (SHOTS && v !== 'border') await page.screenshot({ path: `${SHOTS}/WILDS-w6-${pid}-${v}.png` });
    if (row.fails.length) bad++;
    rows.push(row);
  }
}

/* DIAG: Orleans overview at full vs overview render scale (per-pixel cost), median of 9 frames each */
const diag = {};
await page.evaluate(() => window.__parishes.view('overview', '22071'));
for (const k of [1, 0.6]) {
  await page.evaluate((s) => window.__parishes.renderScale(s), k);
  await page.waitForTimeout(300);
  const t = (await page.evaluate(() => window.__parishes.frameTimes(9))).sort((a, b) => a - b);
  diag[k] = +t[4].toFixed(1);
}
await page.evaluate(() => window.__parishes.renderScale(0.6));
const prOk = await page.evaluate(() => window.__parishes.renderScale().prScale);
if (prOk !== 0.6) { bad++; errors.push('overview render scale is ' + prOk + ', expected 0.6'); }

/* ground + atmosphere (wave 6) */
await page.evaluate(() => window.__parishes.view('origin', '22071'));
const gOk = await page.waitForFunction(() => { const s = window.__parishes.stats(); return s.loaded.every((id) => s.ground.ready.includes(id)) || s.ground.failed.length; }, null, { timeout: 20000 }).then(() => true, () => false);
const gst = await page.evaluate(() => window.__parishes.stats());
const groundRow = { probe: 'ground', ready: gst.ground.ready, loaded: gst.loaded, failed: gst.ground.failed, px: gst.ground.px, fails: [] };
if (!gOk) fail(groundRow, 'ground tiles did not finish loading within 20 s');
if (gst.ground.failed.length) fail(groundRow, `ground tiles failed: ${gst.ground.failed.join(', ')}`);
if (!gst.loaded.every((id) => gst.ground.ready.includes(id))) fail(groundRow, `loaded ${gst.loaded} but draped ${gst.ground.ready}`);
if (!gst.groundY) fail(groundRow, 'draped ground is not at y = 0');
const label = await page.evaluate(() => (document.querySelector('[data-ground-label]') || {}).textContent || '');
if (!/carries no text/.test(label)) fail(groundRow, `ground label next to the view is ${JSON.stringify(label)}`);
if (groundRow.fails.length) bad++;
const atm = gst.atmosphere;
const atmRow = { probe: 'atmosphere', ...atm, fails: [] };
if (!atm.skyCss) fail(atmRow, 'the sky gradient is not on the canvas');
if (atm.clearAlpha !== 0) fail(atmRow, `walk clear alpha ${atm.clearAlpha}; the CSS sky would be hidden`);
if (atm.fog !== atm.horizon) fail(atmRow, 'fog colour is not the horizon colour');
if (atmRow.fails.length) bad++;

/* cross: every shared border touching a probed parish, walked from 40 m inside */
const pairs = await page.evaluate(() => window.__parishes.pairs());
const FINDS = await page.evaluate(() => JSON.parse(document.getElementById('parish-finds').textContent));
const cross = [];
for (const [a, b] of pairs.filter(([a, b]) => PROBE.includes(a) || PROBE.includes(b))) {
  const r = await page.evaluate(([x, y]) => window.__parishes.cross(x, y), [a, b]);
  const row = { probe: 'cross', pair: `${a}|${b}`, steps: r.steps, fails: [] };
  if (r.after.current !== b) fail(row, `after walking ${r.steps} steps the current parish is ${r.after.current}, not ${b}`);
  if (!r.before.loaded.includes(b)) fail(row, `neighbour ${b} was not streamed in before the border`);
  if (!r.marker.includes([a, b].sort().join('|'))) fail(row, `no border marker names ${a}|${b}`);
  const want = FINDS.border[[a, b].sort().join('|')];
  if (want && !(await page.evaluate(() => window.__parishes.stats().finds)).includes(want)) fail(row, `crossing did not find ${want}`);
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
    if (SHOTS) await page.screenshot({ path: `${SHOTS}/WILDS-w6-ride-${medium}.png` });
    const out = await page.evaluate(() => window.__parishes.exit());
    const fnd = await page.evaluate(() => window.__parishes.stats().finds);
    const rr = { probe: 'ride', medium, id: r.id, moved: +r.moved.toFixed(1), wrongMediumSteps: r.wrongMediumSteps, exited: out.ok, fails: [] };
    if (r.moved < 1) fail(rr, `${r.id} moved ${r.moved.toFixed(2)} m under full throttle`);
    if (FINDS.ride[medium] && !fnd.includes(FINDS.ride[medium])) fail(rr, `boarding did not find ${FINDS.ride[medium]}`);
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
  /* the dialogue footer carries the registry's honesty.scripted line (5a shipped 'undefined' here) */
  const foot = await page.evaluate(() => { const e = document.querySelector('#npcpanel .npc-honesty'); return e ? e.textContent : ''; });
  const scripted = await page.evaluate(() => JSON.parse(document.getElementById('parish-npcs').textContent).honesty.scripted);
  npcRow.footer = foot.slice(0, 60);
  if (!foot.includes(scripted) || /undefined/.test(foot)) fail(npcRow, `dialogue footer is ${JSON.stringify(foot)}`);
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/WILDS-w6-npc.png` });
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
if (SHOTS) await page.screenshot({ path: `${SHOTS}/WILDS-w6-satellite.png` });
await page.evaluate(() => window.__parishes.satellite(false));
if (satRow.fails.length) bad++;
/* satrace (REVIEW wave 6): on -> off -> on without waiting leaves exactly one image and the box shown */
const race = await page.evaluate(async () => { const P = window.__parishes; const a = P.satellite(true); P.satellite(false); const c = P.satellite(true); await Promise.all([a, c]); return { imgs: document.querySelectorAll('#satbox img').length, box: !document.getElementById('satbox').hidden }; });
const raceRow = { probe: 'satrace', ...race, fails: [] };
if (race.imgs !== 1 || !race.box) fail(raceRow, `after on/off/on: ${race.imgs} images, box shown ${race.box}`);
await page.evaluate(() => window.__parishes.satellite(false));
if (raceRow.fails.length) bad++;
/* ridemode + keys (REVIEW wave 6): ride, go to the overview, a mode button returns to the ride, exiting from the
   overview leaves a normal walk view (full scale, fabric drawn, Overview not pressed); E with repeat/Ctrl does nothing */
const rm = await page.evaluate(async () => {
  const P = window.__parishes; P.view('origin', '22071'); P.ride('land', 1);
  P.setMode('overview'); const back = P.setMode('walk'); const m1 = P.stats().mode;
  P.setMode('overview'); P.exit(); await new Promise((r) => setTimeout(r, 400));
  const s = P.stats();
  const out = { back, m1, mode: s.mode, pr: P.renderScale().prScale, block: s.instances.block, ovPressed: document.querySelector('[data-mode="overview"]').getAttribute('aria-pressed') };
  P.ride('land', 0.1); P.exit();
  for (const o of [{ repeat: true }, { ctrlKey: true }]) dispatchEvent(new KeyboardEvent('keydown', { key: 'e', ...o }));
  out.afterChordMode = P.stats().mode; return out;
});
const rmRow = { probe: 'ridemode', ...rm, fails: [] };
if (!rm.back || rm.m1 !== 'drive') fail(rmRow, `from the overview while riding, Walk gave ${rm.back}/${rm.m1}, not the ride`);
if (rm.mode !== 'walk' || rm.pr !== 1 || !(rm.block > 0) || rm.ovPressed !== 'false') fail(rmRow, `after exiting from the overview: ${JSON.stringify(rm)}`);
if (rm.afterChordMode !== 'walk') fail(rmRow, `E with repeat/Ctrl changed the mode to ${rm.afterChordMode}`);
if (rmRow.fails.length) bad++;

/* wave 7 world layer (NEW rows; every BASE target above is unchanged and is applied here too, AFTER the parish's
   PARISH v1.4 streets and water have arrived): meshed streets replace the painted grid, AUTHORED water is cut out of
   the land, buildings are solid (physkit), the avatar wades/swims, and the Living world (ambientkit) is measured ON */
const worldRows = [];
for (const pid of PROBE) {
  await page.evaluate((id) => window.__parishes.view('origin', id), pid);
  await page.waitForFunction((id) => { const s = window.__parishes.stats(); return (s.roads.ready.includes(id) || s.roads.failed.length > 0) && s.pending === 0; }, pid, { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(700);
  const times = (await page.evaluate(() => window.__parishes.frameTimes(6))).sort((a, b) => a - b);
  const st = await page.evaluate(() => window.__parishes.stats());
  const wall = await page.evaluate(() => window.__parishes.physWall());
  const wet = await page.evaluate(() => window.__parishes.physWater());
  const row = { probe: 'world', parish: pid, calls: st.calls, tris: st.triangles, ms: +times[Math.floor(times.length / 2)].toFixed(1), roadSegs: st.roads.segs, roadTris: st.roads.tris,
    waterFeats: st.water.feats[pid], boxes: st.phys.boxes, curbs: st.phys.curbs, wall, wet, fails: [] };
  const base = BASE[pid].origin;
  if (!st.roads.ready.includes(pid)) fail(row, `streets not meshed for ${pid} (failed: ${JSON.stringify(st.roads.failed)})`);
  if (st.roads.failed.length || st.water.failed.length) fail(row, `world fetch failed: ${JSON.stringify([st.roads.failed, st.water.failed])}`);
  if (!st.roads.gridOff.includes(pid)) fail(row, 'the painted grid still shows where the streets are meshed');
  if (!(st.roads.segs > 0 && st.roads.visible)) fail(row, 'no meshed street segment drawn');
  if (!st.water.cut.includes(pid)) fail(row, 'AUTHORED water not cut out of the land');
  if (!st.phys.on || !(st.phys.boxes > 0)) fail(row, `physics off or no boxes (${st.phys.boxes})`);
  if (st.calls > Math.ceil(base.calls * CALL_HEADROOM)) fail(row, `calls ${st.calls} > ${Math.ceil(base.calls * CALL_HEADROOM)}`);
  if (st.triangles > base.tris * TRI_HEADROOM) fail(row, `tris ${st.triangles} > ${Math.round(base.tris * TRI_HEADROOM)}`);
  if (row.ms > base.ms * MS_HEADROOM) fail(row, `frame ${row.ms} ms > ${(base.ms * MS_HEADROOM).toFixed(1)}`);
  if (wall.inside) fail(row, `the avatar walked into a building (${JSON.stringify(wall)})`);
  if (wet.feats > 0 && (wet.water === 'dry' || !wet.events.includes('enter-water'))) fail(row, `dropped into ${wet.kind}: ${JSON.stringify(wet)}`);
  if (row.fails.length) bad++;
  worldRows.push(row);
}
/* Living world ON (default OFF): ambientkit's budget is <= 8 draw calls (AMBIENT_CONTRACT); measured, and hidden in the overview */
const ambRow = await page.evaluate(async () => {
  const P = window.__parishes; P.view('origin', '22071'); await new Promise((r) => setTimeout(r, 400));
  const off = P.stats().calls; const a = P.ambient(true); await new Promise((r) => setTimeout(r, 900));
  const s = P.stats(); P.view('overview', '22071'); await new Promise((r) => setTimeout(r, 400));
  const ov = P.stats(); P.ambient(false); P.view('origin', '22071');
  return { probe: 'ambient-on', callsOff: off, callsOn: s.calls, kitCalls: s.ambient ? s.ambient.drawCalls : null, instances: s.ambient ? s.ambient.instances : null, overviewCalls: ov.calls, fails: [] };
});
if (ambRow.kitCalls === null || ambRow.kitCalls > 8) fail(ambRow, `ambient draw calls ${ambRow.kitCalls} (budget 8)`);
if (ambRow.overviewCalls > Math.ceil(BASE['22071'].overview.calls * CALL_HEADROOM)) fail(ambRow, `overview with ambient on: ${ambRow.overviewCalls} calls`);
if (ambRow.fails.length) bad++;

/* wave 8 (ENV) NEW rows; no target above changed. Street detail rides in the ONE street mesh (crossings with cut sidewalks,
   furniture, shoreline edging: 0 new draw calls - the walk views above already carry it inside their BASE call/tris
   targets); the flat land is lit by a baked constant (unlit material, drawn first); facades carry the AUTHORED land use. */
const DETAIL_TRIS = 4000;   // declared budget for crosswalks + furniture + shoreline, paid by the dropped house wall tops (2 per house)
const detRow = await page.evaluate(async () => {
  const P = window.__parishes; P.view('origin', '22071'); await new Promise((r) => setTimeout(r, 600));
  const s = P.stats(), d = P.detailProbe('street');
  return { probe: 'detail', parish: '22071', junctions: d.junctions, crosswalks: d.crosswalks, cuts: d.cuts, furniture: d.furniture, dropped: d.dropped, tris: d.tris,
    landLit: s.landLit, kitUse: s.kitUse, kit: s.kit, fails: [] };
});
{
  const sumT = Object.values(detRow.tris).reduce((a, b) => a + b, 0), furn = Object.values(detRow.furniture).reduce((a, b) => a + b, 0);
  if (!(detRow.junctions > 0 && detRow.crosswalks > 0 && detRow.cuts > 0)) fail(detRow, `no crossing near the Orleans start (${detRow.junctions} junctions, ${detRow.crosswalks} crosswalks, ${detRow.cuts} cuts)`);
  if (!(furn > 0)) fail(detRow, 'no street furniture near the Orleans start');
  if (sumT > DETAIL_TRIS) fail(detRow, `detail triangles ${sumT} > ${DETAIL_TRIS}`);
  if (detRow.dropped) fail(detRow, `${detRow.dropped} detail pieces dropped (street buffer full)`);
  if (!detRow.landLit) fail(detRow, 'a land mesh is not the baked-light unlit material drawn first');
  const ku = detRow.kitUse;
  if (!(ku.house[0] === detRow.kit.house && ku.house[1] + ku.house[2] === 0)) fail(detRow, `houses must be residential: ${JSON.stringify(ku.house)}`);
  if (!(ku.midrise[0] === 0 && ku.midrise[1] + ku.midrise[2] === detRow.kit.midrise && ku.midrise[1] > 0)) fail(detRow, `midrises must be commercial/industrial: ${JSON.stringify(ku.midrise)}`);
  if (SHOTS) { await page.evaluate(() => window.__parishes.detailProbe('crossing')); await page.waitForTimeout(900); await page.screenshot({ path: `${SHOTS}/ENV-crossing.png` }); }
  const sh = await page.evaluate(() => window.__parishes.detailProbe('shore'));
  detRow.shore = sh ? sh.shore : null; detRow.shoreTris = sh ? sh.tris.shore : null;
  if (!(sh && sh.shore > 0)) fail(detRow, `no shoreline edging around the Orleans pond: ${JSON.stringify(sh)}`);
  if (SHOTS) { await page.waitForTimeout(900); await page.screenshot({ path: `${SHOTS}/ENV-shore.png` }); }
  if (detRow.fails.length) bad++;
}
/* DEEP_ROW:BEGIN wave 9 (DEEP) NEW row; no target above changed. Underwater regions (web/deepkit.py) in the Lake
   Pontchartrain stand-in (AUTHORED depth grid): the kit's DECLARED budget (<= 4 draw calls under water, 0 above the surface,
   0 in the overview) - and the 22103 overview with the kit mounted stays inside its existing BASE call headroom. */
const deepProbe = async () => {
  const P = window.__parishes; P.view('origin', '22103'); P.teleport(-902.55, -22795.1, 0); await new Promise((r) => setTimeout(r, 2500));
  const above = P.stats().calls; document.getElementById('deep-rov').click();
  for (let i = 0; i < 100 && !window.__deep; i++) await new Promise((r) => setTimeout(r, 100));
  if (!window.__deep) return { probe: 'underwater', error: window.__deepError || 'kit not mounted', fails: [] };
  await new Promise((r) => setTimeout(r, 500));
  const d = window.__deep.stats(), under = P.stats().calls, hud = window.__deep.hud();
  const ft = await P.frameTimes(10); ft.sort((a, b) => a - b);
  document.getElementById('deep-rov').click(); await new Promise((r) => setTimeout(r, 300));
  const offCalls = window.__deep.stats().calls;
  P.view('overview', '22103'); await new Promise((r) => setTimeout(r, 400));
  const ov = P.stats().calls, dov = window.__deep.stats().calls; P.view('origin', '22071');
  return { probe: 'underwater', parish: '22103', body: hud ? hud.body : null, mode: d.mode, callsAbove: above, callsUnder: under, deepCalls: d.calls, deepProps: d.props,
    msUnder: +ft[Math.floor(ft.length / 2)].toFixed(1), deepOffCalls: offCalls, overviewCalls: ov, deepOverviewCalls: dov, fails: [] };
};
/* DEEP_ROW:END */
const deepRow = await page.evaluate(deepProbe);
if (deepRow.error) fail(deepRow, 'underwater kit: ' + deepRow.error);
else {
  if (deepRow.body !== '22103-lake-0' || deepRow.mode !== 'rov') fail(deepRow, `ROV not in the lake stand-in: ${deepRow.body} ${deepRow.mode}`);
  if (!(deepRow.deepCalls >= 1 && deepRow.deepCalls <= 4)) fail(deepRow, `deep draw calls under water ${deepRow.deepCalls} (declared budget 1..4)`);
  if (deepRow.callsUnder - deepRow.callsAbove > 4) fail(deepRow, `page calls grew by ${deepRow.callsUnder - deepRow.callsAbove} under water (> 4)`);
  if (deepRow.deepOffCalls !== 0 || deepRow.deepOverviewCalls !== 0) fail(deepRow, `deep calls off ${deepRow.deepOffCalls} / overview ${deepRow.deepOverviewCalls} (must be 0)`);
  if (deepRow.overviewCalls > Math.ceil(BASE['22103'].overview.calls * CALL_HEADROOM)) fail(deepRow, `22103 overview with the kit mounted: ${deepRow.overviewCalls} calls`);
}
if (deepRow.fails.length) bad++;
/* DIAG (not a target): lots NOT built in the 22103 border view because they stand in AUTHORED water (the w7 lake stand-in);
   the w5 fabric floor for that view was measured when such lots still stood on the lake */
const lakeDiag = await page.evaluate(async () => {
  const P = window.__parishes, a = P.stats().skipped.water; P.view('border', '22103'); await new Promise((r) => setTimeout(r, 900));
  const s = P.stats(); return { skippedWater: s.skipped.water - a, fabric: s.instances.block + s.instances.tree, pending: s.pending };
});

/* styles: the panels follow the Style switcher (tokens only) */
if (SHOTS) {
  for (const s of ['hivis', 'enterprise']) {
    await page.evaluate((id) => document.documentElement.setAttribute('data-style', id), s);
    await page.waitForTimeout(300);
    await page.screenshot({ path: `${SHOTS}/WILDS-w6-style-${s}.png` });
  }
}
await browser.close();

const out = { rows, cross, ride: rideRows, npcs: npcRow, satellite: satRow, ground: groundRow, atmosphere: atmRow, satrace: raceRow, ridemode: rmRow, world: worldRows, ambient: ambRow, detail: detRow, underwater: deepRow, errors, bad: bad + errors.length };
if (JSON_OUT) console.log(JSON.stringify(out, null, 1));
else {
  for (const r of rows) console.log(`${r.fails.length ? 'FAIL' : '  ok'} ${r.parish} ${r.view.padEnd(8)} calls ${r.calls} tris ${r.tris} ms ${r.ms} chunks ${r.chunks} fabric ${r.fabric} lamps ${r.lamps} loaded ${r.loaded}${r.fails.length ? ' :: ' + r.fails.join('; ') : ''}`);
  for (const r of cross) console.log(`${r.fails.length ? 'FAIL' : '  ok'} cross ${r.pair} steps ${r.steps}${r.fails.length ? ' :: ' + r.fails.join('; ') : ''}`);
  for (const r of rideRows) console.log(`${r.fails.length ? 'FAIL' : '  ok'} ${r.probe} ${JSON.stringify(Object.fromEntries(Object.entries(r).filter(([k]) => k !== 'fails' && k !== 'probe')))}${r.fails.length ? ' :: ' + r.fails.join('; ') : ''}`);
  console.log(`${npcRow.fails.length ? 'FAIL' : '  ok'} npcs ${npcRow.count} ${npcRow.id} ${npcRow.source}${npcRow.fails.length ? ' :: ' + npcRow.fails.join('; ') : ''}`);
  console.log(`${satRow.fails.length ? 'FAIL' : '  ok'} satellite ${satRow.src} :: ${satRow.msg}${satRow.fails.length ? ' :: ' + satRow.fails.join('; ') : ''}`);
  for (const r of rows.filter((x) => x.kit)) console.log(`${r.fails.length ? 'FAIL' : '  ok'} kit ${r.parish} ${r.view.padEnd(8)} buildings ${JSON.stringify(r.kit)} calls/family ${JSON.stringify(r.familyCalls)}`);
  for (const r of [groundRow, atmRow, raceRow, rmRow]) console.log(`${r.fails.length ? 'FAIL' : '  ok'} ${r.probe} ${JSON.stringify(Object.fromEntries(Object.entries(r).filter(([k]) => k !== 'fails' && k !== 'probe')))}${r.fails.length ? ' :: ' + r.fails.join('; ') : ''}`);
  for (const r of [...worldRows, ambRow, detRow, deepRow]) console.log(`${r.fails.length ? 'FAIL' : '  ok'} ${r.probe} ${JSON.stringify(Object.fromEntries(Object.entries(r).filter(([k]) => k !== 'fails' && k !== 'probe')))}${r.fails.length ? ' :: ' + r.fails.join('; ') : ''}`);
  console.log(`  -- DIAG 22103 border: ${lakeDiag.skippedWater} lots not built in AUTHORED water while building this view (fabric ${lakeDiag.fabric}, pending ${lakeDiag.pending}) - diagnosis, not a target`);
  console.log(`  -- DIAG 22071 overview median frame: scale 1 ${diag[1]} ms, scale 0.6 ${diag[0.6]} ms (diagnosis, not a target)`);
  for (const e of errors) console.log('FAIL page error: ' + e);
  console.log(bad + errors.length ? `eval_parishes: ${bad + errors.length} FAIL` : 'eval_parishes: all rows within target');
}
process.exit(bad + errors.length ? 1 : 0);
