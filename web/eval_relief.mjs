/**
 * ELEV w14 relief row (web/terrainkit.py mounted in build_parishes; the Bay page shares it) - a NEW eval row, used by
 * web/eval_parishes.mjs and web/eval_bayworld.mjs, and runnable alone for one page pair:
 *     flock $SP/chromium.lock node web/eval_relief.mjs <page url> [--shots=<dir> --name=<tag>]
 * The row opens the page twice, with ?relief=off and with ?relief=on (GROUND w16: explicit on both sides, whatever the
 * page default). The row holds:
 *   provenance  the RECORDED USGS 3DEP grid loaded (sha256-pinned, gunzipped in the browser), a finite median reference;
 *   present     the patch has quads and some drawn ground stands >= 0.3 m above the reference near a relief spot;
 *   slope       the drawn surface's max slope around the eye <= the page's declared max_slope;
 *   floating    N sampled kit buildings (as drawn), lots, trees, lamps and parked land vehicles: base within 0.1 m of
 *               the ground under it (lowest footprint point) and never above the ground at its centre;
 *   calls       draw calls at the same start view with relief on == with relief off (the patch rides the land mesh);
 *   water       the water plane and the world water level are unchanged.
 */
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { loadavg } from 'node:os';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

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

/* RELIEF_URLS:BEGIN GROUND w16: both sides name their switch explicitly (relief=off / relief=on); any relief= already in
   the given url is dropped first, so the row compares off with on whatever the page default is and whatever url the
   caller passes (eval_parishes / eval_bayworld may be pointed at ?relief=on). web/test_terrainkit.mjs checks it. */
export function reliefUrls(url) {
  const bare = url.replace(/([?&])relief=[^&#]*&?/g, '$1').replace(/[?&]$/, '');
  const w = (v) => bare + (bare.includes('?') ? '&' : '?') + 'relief=' + v;
  return { off: w('off'), on: w('on') };
}
/* RELIEF_URLS:END */
export async function reliefRow(browser, url, opts = {}) {
  const N = opts.n || 200, errors = [], row = { probe: 'relief', url: url.replace(/^.*\/web\//, 'web/'), fails: [] };
  const fail = (m) => row.fails.push(m);
  const U = reliefUrls(url);
  row.load = loadavg().map((v) => +v.toFixed(2));   // GROUND w16: patchMs is a time - the load average is printed beside it
  const off = await openAt(browser, U.off, errors); await sleep(1500);
  row.callsOff = await calls(off); await off.close();
  const on = await openAt(browser, U.on, errors);
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

/* RELIEF_AWARE:BEGIN wave 22 - the relief-aware ground rule, added BESIDE the flat-ground rule (the eval_parishes /
   eval_bayworld rows that read stats().groundY are untouched). Every view of the page is opened with ?relief=off and with
   ?relief=on and judged by the rule that fits its side:
     off  the FLAT rule, verbatim in meaning: stats().groundY (every land vertex at y = 0) and the audit finds no patch;
     on   the RELIEF-AWARE rule: land vertices that are not patch stand at y = 0, patch vertices stand on the relief lattice
          at height + lift (+- 2 mm) and never under 0 (elev.groundAudit); the drawn camera stands the declared eye height
          above the ground under it (elev.eyeAudit); the overview parks the patch, so there the flat rule holds again;
     both draw calls and triangles inside the page's own declared BASE ceilings (read from the sibling eval's source, never
          copied or retuned): the Bay overview triangle rows are among them.
   Frame time is printed beside the load average and is information here (a software-rendered frame is load-bound; the
   sibling eval keeps judging it). */
export function declaredBase(url) {
  const bay = /trade_craft_bay/.test(url);
  const src = readFileSync(fileURLToPath(new URL(bay ? './eval_bayworld.mjs' : './eval_parishes.mjs', import.meta.url)), 'utf8');
  const grab = (re, what) => { const m = src.match(re); if (!m) throw new Error('eval_relief: cannot read ' + what + ' from the sibling eval'); return m[1]; };
  const BASE = new Function('return (' + grab(/^const BASE = (\{[\s\S]*?^\});/m, 'BASE') + ')')();
  const PROBE = new Function('return ' + grab(/^const PROBE = (\[[^\]]*\])/m, 'PROBE'))();
  const H = grab(/^const (CALL_HEADROOM[^;]*);/m, 'headroom constants');
  const [ch, th, mh] = ['CALL_HEADROOM', 'TRI_HEADROOM', 'MS_HEADROOM'].map((k) => +H.match(new RegExp(k + ' = ([0-9.]+)'))[1]);
  return { BASE, PROBE, CALL_HEADROOM: ch, TRI_HEADROOM: th, MS_HEADROOM: mh, bay };
}
export async function reliefAwareRow(browser, url, opts = {}) {
  const errors = [], U = reliefUrls(url), B = declaredBase(url);
  const row = { probe: 'relief-aware', url: url.replace(/^.*\/web\//, 'web/'), probes: B.PROBE, off: [], on: [], fails: [], load: loadavg().map((v) => +v.toFixed(2)) };
  const fail = (m) => row.fails.push(m);
  for (const side of ['off', 'on']) {
    const page = await openAt(browser, U[side], errors);
    if (side === 'on') await page.waitForFunction(() => { const p = window.__parishes.elev.probe(1); return p.demLoaded || p.demFailed; }, null, { timeout: 25000 }).catch(() => {});
    for (const pid of B.PROBE) for (const v of ['origin', 'border', 'overview']) {
      await page.evaluate(([name, id]) => window.__parishes.view(name, id), [v, pid]);
      await page.waitForFunction(() => window.__parishes.stats().pending === 0, null, { timeout: 15000 }).catch(() => {});
      await sleep(side === 'on' ? 900 : 350);
      const times = (await page.evaluate(() => window.__parishes.frameTimes(6))).sort((a, b) => a - b);
      const r = await page.evaluate(() => { const P = window.__parishes, st = P.stats(); return { st: { calls: st.calls, tris: st.triangles, groundY: st.groundY, pending: st.pending, landMeshes: st.landMeshes, loaded: st.loaded.length }, ga: P.elev.groundAudit(), ea: P.elev.eyeAudit() }; });
      const base = B.BASE[pid] && B.BASE[pid][v], ms = +times[Math.floor(times.length / 2)].toFixed(1);
      const o = { id: pid, view: v, calls: r.st.calls, tris: r.st.tris, ms, load1: +loadavg()[0].toFixed(2), flatRule: r.st.groundY, merged: r.ga.merged, patchVerts: r.ga.patchVerts, flatBad: r.ga.flatBad, patchBad: r.ga.patchBad, held: r.ga.held.held, heldBad: r.ga.heldBad, heldPatchVerts: r.ga.held.patchVerts, heldBytes: r.ga.held.bytes, offLattice: r.ga.offLattice, below: r.ga.below, maxDev: r.ga.maxDev, eye: v === 'overview' ? null : r.ea.above, fails: [] };
      const f = (m) => o.fails.push(m);
      if (!base) f('no declared target for ' + pid + ' ' + v);
      else {
        if (r.st.calls > Math.ceil(base.calls * B.CALL_HEADROOM)) f(`calls ${r.st.calls} > ${Math.ceil(base.calls * B.CALL_HEADROOM)}`);
        if (r.st.tris > base.tris * B.TRI_HEADROOM) f(`tris ${r.st.tris} > ${Math.round(base.tris * B.TRI_HEADROOM)}`);
        o.msCeiling = +(base.ms * B.MS_HEADROOM).toFixed(1); o.msOver = ms > o.msCeiling;   // information: load-bound, judged by the sibling eval
      }
      if (r.st.pending !== 0) f(`${r.st.pending} chunks pending`);
      if (r.st.landMeshes !== r.st.loaded) f(`${r.st.landMeshes} land meshes for ${r.st.loaded} loaded`);
      if (r.ga.flatBad || r.ga.patchBad || r.ga.offLattice || r.ga.below) f(`ground audit: flat-bad ${r.ga.flatBad}, patch-bad ${r.ga.patchBad}, off-lattice ${r.ga.offLattice}, under-0 ${r.ga.below}, max dev ${r.ga.maxDev} m ${JSON.stringify(r.ga.bad)}`);
      if (r.ga.heldBad) f(`held-but-not-in-scene land meshes: ${r.ga.held.merged} merged, ${r.ga.held.parked} parked, ${r.ga.held.stale} stale, ${r.ga.held.nonFlat} not flat, ${r.ga.held.patchVerts} stale patch vertices ${JSON.stringify(r.ga.held.list)}`);   // wave 23: a streamed-out parish keeps no relief patch
      if (side === 'off') {
        if (!r.st.groundY) f('FLAT rule: a land mesh vertex is not at y = 0 with relief off');
        if (r.ga.patchVerts) f(`relief off but ${r.ga.patchVerts} patch vertices exist`);
        if (v !== 'overview' && Math.abs(r.ea.above - r.ea.eyeH) > 0.01) f(`camera ${r.ea.above} m above flat ground, want ${r.ea.eyeH}`);
      } else if (v === 'overview') {
        if (!r.ga.overview || r.ga.merged || !r.st.groundY) f(`overview must draw the flat land (parked ${r.ga.overview}, merged meshes ${r.ga.merged}, flat rule ${r.st.groundY})`);
      } else if (!r.ea.riding && Math.abs(r.ea.above - r.ea.eyeH) > 0.15) f(`camera ${r.ea.above} m above the ground under it, want ${r.ea.eyeH} +- 0.15`);
      if (o.fails.length) fail(`${side} ${pid} ${v}: ${o.fails.join('; ')}`);
      row[side].push(o);
    }
    await page.close();
  }
  const drawn = row.on.filter((o) => o.view !== 'overview' && o.patchVerts > 0);
  if (!drawn.length) fail('no walk view drew a relief patch with relief on (nothing was judged by the relief-aware rule)');
  row.patchViews = drawn.length; row.load2 = loadavg().map((v) => +v.toFixed(2));
  if (errors.length) fail(`page errors: ${errors.slice(0, 3).join(' | ')}`);
  row.errors = errors.length;
  return row;
}
/* RELIEF_AWARE:END */

/* RELIEF_STREAM:BEGIN wave 23 - stream a parish out and back in with ?relief=on and audit EVERY held land mesh (in the scene
   or not). Per step: the held-mesh audit (each held mesh not in the scene must be flat: no merged patch, nothing parked, no
   stale reference), the in-scene relief-aware audit, geometry bytes held, vertices of patch still held, JS heap (information).
   The A parish is walked to, then a probe that is NOT its neighbour, then back, for `cycles` rounds. */
export async function reliefStreamRow(browser, url, opts = {}) {
  const errors = [], U = reliefUrls(url), B = declaredBase(url), cycles = opts.cycles || 2;
  const row = { probe: 'relief-stream', url: url.replace(/^.*\/web\//, 'web/'), steps: [], fails: [], load: loadavg().map((v) => +v.toFixed(2)) };
  const fail = (m) => row.fails.push(m);
  const page = await openAt(browser, U.on, errors);
  await page.waitForFunction(() => { const p = window.__parishes.elev.probe(1); return p.demLoaded || p.demFailed; }, null, { timeout: 25000 }).catch(() => {});
  const settle = async () => { await page.waitForFunction(() => window.__parishes.stats().pending === 0, null, { timeout: 15000 }).catch(() => {}); await sleep(900); };
  const snap = async (label, pid) => {
    const r = await page.evaluate(([l]) => { const P = window.__parishes; P.elev.refresh(); const ga = P.elev.groundAudit(), st = P.stats(), h = performance.memory ? performance.memory.usedJSHeapSize : null;
      return { label: l, loaded: st.loaded, landMeshes: st.landMeshes, ga, heap: h }; }, [label]);
    const o = { label, pid, loaded: r.loaded.length, inScene: r.ga.merged + r.ga.flatOnly, held: r.ga.held.held, heldMerged: r.ga.held.merged, heldParked: r.ga.held.parked, heldStale: r.ga.held.stale, heldNonFlat: r.ga.held.nonFlat,
      heldPatchVerts: r.ga.held.patchVerts, heldBytes: r.ga.held.bytes, released: r.ga.released, releasedVerts: r.ga.releasedVerts, mergedInScene: r.ga.merged, patchVertsInScene: r.ga.patchVerts, flatBad: r.ga.flatBad, patchBad: r.ga.patchBad, offLattice: r.ga.offLattice, below: r.ga.below, maxDev: r.ga.maxDev, heapMB: r.heap === null ? null : +(r.heap / 1048576).toFixed(1), loadedIds: r.loaded };
    if (r.ga.heldBad) fail(`${label}: ${r.ga.held.merged} merged + ${r.ga.held.parked} parked + ${r.ga.held.stale} stale + ${r.ga.held.nonFlat} not-flat held meshes, ${r.ga.held.patchVerts} stale patch vertices ${JSON.stringify(r.ga.held.list)}`);
    if (r.ga.flatBad || r.ga.patchBad || r.ga.offLattice || r.ga.below) fail(`${label}: in-scene audit flat-bad ${r.ga.flatBad}, patch-bad ${r.ga.patchBad}, off-lattice ${r.ga.offLattice}, under-0 ${r.ga.below}, max dev ${r.ga.maxDev} m ${JSON.stringify(r.ga.bad)}`);
    row.steps.push(o); return o;
  };
  const go = async (pid) => { await page.evaluate((id) => window.__parishes.view('origin', id), pid); await settle(); };
  const A = B.PROBE[0];
  await go(A); const s0 = await snap('A first visit', A);
  if (!s0.mergedInScene) fail('the A parish drew no relief patch (nothing to stream out)');
  let other = null;
  const ids = await page.evaluate(() => window.__parishes.ids());   // the declared probes first, then any other parish of the page
  for (const c of [...B.PROBE.slice(1), ...ids.filter((i) => !B.PROBE.includes(i))]) { await go(c); const t = await page.evaluate((a) => window.__parishes.stats().loaded.includes(a), A); if (!t) { other = c; break; } }
  if (!other) { fail('no probe parish streams ' + A + ' out'); row.other = null; row.peakHeldPatchVerts = 0; row.peakHeldBytes = 0; row.releasedVerts = 0; row.errors = errors.length; await page.close(); return row; }
  row.A = A; row.other = other;
  for (let k = 1; k <= cycles; k++) {
    await go(other); await snap(`cycle ${k}: ${other} (A streamed out)`, other);
    await go(A); const back = await snap(`cycle ${k}: back in ${A}`, A);
    if (!back.mergedInScene) fail(`cycle ${k}: re-entry drew no relief patch for ${A}`);
  }
  const outs = row.steps.filter((o) => /streamed out/.test(o.label)); row.peakHeldPatchVerts = Math.max(0, ...row.steps.map((o) => o.heldPatchVerts)); row.peakHeldBytes = Math.max(0, ...row.steps.map((o) => o.heldBytes));
  row.releasedVerts = row.steps[row.steps.length - 1].releasedVerts;
  if (!outs.some((o) => o.held > 0)) fail('no land mesh was held out of the scene after streaming out (nothing was audited)');
  if (errors.length) fail(`page errors: ${errors.slice(0, 3).join(' | ')}`);
  row.errors = errors.length; await page.close();
  return row;
}
/* RELIEF_STREAM:END */

if (process.argv[1] && process.argv[1].endsWith('eval_relief.mjs')) {
  const url = process.argv[2], shots = (process.argv.find((a) => a.startsWith('--shots=')) || '').slice(8) || null;
  const name = (process.argv.find((a) => a.startsWith('--name=')) || '--name=page').slice(7);
  const browser = await chromium.launch({ executablePath: CHROME, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--enable-precise-memory-info'] });
  if (process.argv.includes('--stream')) {   // wave 23: only the stream-out / back-in row
    const sr = await reliefStreamRow(browser, url, { name }); await browser.close();
    for (const o of sr.steps) console.log(`${'  ok'} stream ${o.label}: loaded ${o.loaded} [${o.loadedIds.join(',')}] in-scene merged ${o.mergedInScene} patchVerts ${o.patchVertsInScene} | held ${o.held} merged ${o.heldMerged} parked ${o.heldParked} stale ${o.heldStale} nonFlat ${o.heldNonFlat} heldPatchVerts ${o.heldPatchVerts} heldBytes ${o.heldBytes} | released ${o.released} (${o.releasedVerts} verts) | patchBad ${o.patchBad} dev ${o.maxDev} | heap ${o.heapMB} MB`);
    console.log(`  -- A ${sr.A} other ${sr.other} peak held patch vertices ${sr.peakHeldPatchVerts}, peak held geometry bytes ${sr.peakHeldBytes}, load ${sr.load.join('/')}`);
    for (const f of sr.fails) console.log('FAIL relief-stream ' + f);
    console.log(sr.fails.length ? `FAIL relief-stream (${name}): ${sr.fails.length}` : `  ok relief-stream (${name})`);
    process.exit(sr.fails.length ? 1 : 0);
  }
  const T0 = Date.now(), row = await reliefRow(browser, url, { shots, name }), T1 = Date.now();
  const aware = process.argv.includes('--no-aware') ? null : await reliefAwareRow(browser, url, { name });
  await browser.close();
  console.log(JSON.stringify(row, null, 1));
  if (aware) for (const k of ['off', 'on']) for (const o of aware[k]) console.log(`${o.fails.length ? 'FAIL' : '  ok'} relief-aware ${k} ${o.id} ${o.view}: calls ${o.calls} tris ${o.tris} held ${o.held} heldBad ${o.heldBad} ms ${o.ms}${o.msOver ? ' (over ' + o.msCeiling + ', load-bound info)' : ''} load1 ${o.load1} flatRule ${o.flatRule} merged ${o.merged} patchVerts ${o.patchVerts} flatBad ${o.flatBad} patchBad ${o.patchBad} dev ${o.maxDev} eye ${o.eye}${o.fails.length ? ' :: ' + o.fails.join('; ') : ''}`);
  console.log(`  -- browser time: relief row ${((T1 - T0) / 1000).toFixed(0)} s, relief-aware row ${((Date.now() - T1) / 1000).toFixed(0)} s (each run under the 90 s allowance only if the sum is <= 90)`);
  if (aware) console.log(`  -- relief-aware load ${aware.load.join('/')} -> ${aware.load2.join('/')}, walk views with a patch ${aware.patchViews}, page errors ${aware.errors}`);
  const nfail = row.fails.length + (aware ? aware.fails.length : 0);
  console.log(row.fails.length ? `FAIL relief (${name}): ${row.fails.length}` : `  ok relief (${name})`);
  if (aware) console.log(aware.fails.length ? `FAIL relief-aware (${name}): ${aware.fails.length}` : `  ok relief-aware (${name})`);
  process.exit(nfail ? 1 : 0);
}
