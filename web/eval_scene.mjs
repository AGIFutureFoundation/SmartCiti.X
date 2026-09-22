/**
 * A scorecard for the scene, measured in a real browser.
 *
 * verify_all.sh reaches no network and opens no browser, and that is right:
 * a suite that needs Chromium is a suite people stop running. But some
 * questions cannot be answered from the source at all - how many draw calls
 * a view actually costs, how many distinct pieces are standing in it,
 * whether a texture budget is met - and "it looked fine when I loaded it"
 * is not an answer to any of them.
 *
 * So this is a separate, opt-in eval. It drives the page through every view
 * and scores what it finds against targets that are DECLARED here with
 * their reasons, so a regression shows up as a number crossing a line
 * rather than as somebody's impression that the campus feels emptier.
 *
 * Run:  python3 -m http.server 8811  (from the repo root)
 *       node web/eval_scene.mjs [--json]
 *
 * The targets come from two places and each says which:
 *   MEASURED-HERE  - a number this page already achieves, recorded so it
 *                    cannot quietly get worse.
 *   REFERENCE      - a characteristic taken from the reference models in
 *                    assets/REFERENCE.md, where the question is whether
 *                    this scene has enough distinct pieces to read as a
 *                    place rather than whether it is cheap enough.
 */
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';

const URL_BASE = process.env.TC_URL ?? 'http://127.0.0.1:8811/web/trade_craft_3d.html';
const CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const JSON_OUT = process.argv.includes('--json');

/* Each view, how to get there, and what it is held to.

   The ceilings are the MEASURED baseline plus stated headroom, not round
   numbers picked by eye. A ceiling loose enough never to fire is not a
   ceiling: the first draft of this file allowed 400 draw calls on a view
   that costs 249, and 900,000 triangles on one that costs 4,508, which
   would have let the campus double in cost twice over without a word.

   Baseline measured 2026-09-22, Chromium/SwiftShader, 1280x800, quality
   rung `high`. Headroom is 25% on draw calls - the expensive currency -
   and 4x on triangles, which are nearly free here and which the kit and
   props packs are expected to spend heavily.

   `minMeshes` is a FLOOR, and it asks a different question: are there
   enough separate things standing in this view for it to read as a place
   rather than a diagram? See assets/REFERENCE.md. */
const BASE = {
  region: { calls: 249, tris: 4_508, meshes: 80 },
  campus: { calls: 273, tris: 15_850, meshes: 250 },
  hall:   { calls: 157, tris: 3_806, meshes: 137 },
};
const CALL_HEADROOM = 1.25;     // draw calls are the scarce currency
const TRI_HEADROOM = 4;         // triangles are not, and are meant to grow
const MESH_FLOOR = 0.9;         // losing a tenth of the visible pieces is a regression

const ceil = (id) => ({
  maxCalls: Math.round(BASE[id].calls * CALL_HEADROOM),
  maxTris: BASE[id].tris * TRI_HEADROOM,
  minMeshes: Math.round(BASE[id].meshes * MESH_FLOOR),
});

const VIEWS = [
  { id: 'region', go: null, ...ceil('region'),
    why: 'the opening board: ten campus plates and their labels' },
  { id: 'campus', go: (p) => p.evaluate(() => window.__tc3dDo('view', 'campus:treasure-island')),
    ...ceil('campus'),
    why: 'a campus green with its halls, yard seats, roads and beacons' },
  { id: 'hall', go: (p) => p.evaluate(() => window.__tc3dDo('view', 'hall')),
    ...ceil('hall'),
    why: 'one hall interior: eleven rooms, their partitions and lamps' },
];

const pct = (v, lim) => `${((v / lim) * 100).toFixed(0)}%`;

async function main() {
  const b = await chromium.launch({
    executablePath: CHROME,
    args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'],
  });
  const pg = await b.newPage({ viewport: { width: 1280, height: 800 } });
  const errs = [];
  pg.on('pageerror', (e) => errs.push(e.message));
  pg.on('console', (m) => { if (m.type() === 'error') errs.push('console: ' + m.text().slice(0, 200)); });

  await pg.goto(URL_BASE, { waitUntil: 'load' });
  await pg.waitForFunction(() => window.__tc3d, null, { timeout: 90_000 });
  await pg.waitForTimeout(3000);

  const rows = [];
  for (const v of VIEWS) {
    if (v.go) { await v.go(pg).catch(() => {}); await pg.waitForTimeout(1800); }
    // a frame is rendered before reading renderer.info: the counters are
    // filled by the last draw, so reading them without one reports the
    // previous view's cost under this view's name
    await pg.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
    const m = await pg.evaluate(() => {
      const d = window.__tc3d();
      let meshes = 0, mats = new Set();
      // only what is actually VISIBLE: a hidden group is not a place
      const walk = (o) => {
        if (!o.visible) return;
        if (o.isMesh) { meshes++; if (o.material) mats.add(o.material.uuid); }
        for (const c of o.children) walk(c);
      };
      walk(window.__tc3dScene());
      return { view: d.view, calls: d.perf.calls, tris: d.perf.tris,
               tex: d.perf.tex, geoms: d.perf.geoms, quality: d.quality,
               meshes, materials: mats.size };
    });
    rows.push({ ...v, ...m });
  }
  await b.close();

  let bad = 0;
  const line = [];
  for (const r of rows) {
    const fails = [];
    if (r.calls > r.maxCalls) fails.push(`draw calls ${r.calls} > ${r.maxCalls}`);
    if (r.tris > r.maxTris) fails.push(`triangles ${r.tris.toLocaleString()} > ${r.maxTris.toLocaleString()}`);
    if (r.meshes < r.minMeshes) fails.push(`only ${r.meshes} visible meshes, floor is ${r.minMeshes}`);
    if (fails.length) bad++;
    line.push({ ...r, fails });
  }

  if (JSON_OUT) {
    console.log(JSON.stringify({ rows: line, errors: errs, failing: bad }, null, 1));
  } else {
    console.log('\nscene eval — measured in Chromium, one frame per view\n');
    console.log(`${'view'.padEnd(9)} ${'calls'.padStart(6)} ${'of'.padStart(5)} `
      + `${'triangles'.padStart(11)} ${'of'.padStart(5)} ${'meshes'.padStart(7)} `
      + `${'floor'.padStart(6)} ${'mats'.padStart(5)} ${'tex'.padStart(5)}  rung`);
    for (const r of line) {
      console.log(`${r.view.padEnd(9)} ${String(r.calls).padStart(6)} ${pct(r.calls, r.maxCalls).padStart(5)} `
        + `${r.tris.toLocaleString().padStart(11)} ${pct(r.tris, r.maxTris).padStart(5)} `
        + `${String(r.meshes).padStart(7)} ${String(r.minMeshes).padStart(6)} `
        + `${String(r.materials).padStart(5)} ${String(r.tex).padStart(5)}  ${r.quality}`
        + (r.fails.length ? '   <<< ' + r.fails.join('; ') : ''));
    }
    for (const r of line) console.log(`  ${r.view}: ${r.why}`);
    if (errs.length) {
      console.log('\npage errors:');
      for (const e of errs.slice(0, 6)) console.log('  ' + e);
    }
    console.log(`\n${line.length} views scored, ${bad} over a declared limit`
      + `${errs.length ? `, ${errs.length} page error(s)` : ', no page errors'}`);
  }
  process.exit(bad || errs.length ? 1 : 0);
}
main();
