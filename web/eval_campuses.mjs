/* Every campus, scored in a real browser - not only the one that happens
 * to be first.
 *
 * web/eval_scene.mjs scores the `campus` view on treasure-island alone, and
 * rnd/ has recorded that as a gap since the row was added: "campuses the
 * scene harness has ever driven to: 1 of 10". This harness drives the page
 * to every campus the unions registry declares and measures each with the
 * same instruments - draw calls, triangles, visible meshes, signs on screen
 * and overlapping sign pairs - and holds each to the SAME caps
 * eval_scene.mjs uses (draw calls, triangles, overlapping pairs), READ from
 * that file's source rather than copied here, so there is one campus
 * budget in this bundle, not two that could drift apart.
 *
 * The FLOORS (visible meshes, signs on screen) are a different matter. They
 * were calibrated on the flagship, which hosts 51 of the 111 halls; the
 * seven hubs host none by design (unions/registry/campuses.json). Holding a
 * hub with no halls to a floor set by fifty-one of them would be a quantity
 * standing in for a different quantity, and the first run of this harness
 * did exactly that: nine of ten "failing". So the floors are applied only
 * to the campus they were measured on, and every other campus is MEASURED
 * and reported beside its own declared hall count, not judged.
 *
 * THE DENOMINATOR, and what the first framing got wrong. The first draft
 * of this file printed signs beside halls and invited the reader to ask
 * why one campus showed nine signs for twenty-eight halls while another
 * showed twenty-one for thirty-two. Measured 2026-09-26 by KIND, through
 * the same __tc3dLabelRects() hook: in every one of the ten campus views
 * there were ZERO hall-kind signs. A hall was named only from inside it.
 * What a campus view carried was its plaza marquee, its district banners,
 * and the city's anchors and site tags - New Orleans places 3 anchors and
 * 1 tag (9 signs), Oakland 12 and 3 (21) - so the sign count followed the
 * anchors a city records, not the halls a campus hosts, and "signs per
 * hall" was one quantity standing beside a different one. Halls were the
 * wrong denominator for what was on the screen. The table now prints the
 * signs by kind - how many are hall signs, how many anchors and site tags,
 * how many the rest (the marquee and the banners) - beside the halls the
 * campus declares, so a hall count and a hall-sign count sit in the same
 * row and the reader can see whether a campus names its buildings at all,
 * and how many of those names the declutter let stand. The kinds are read
 * off each rectangle's `kind` field rather than re-derived from the geo
 * and restoration registries, because the page filters both before it
 * places anything and a second copy of that filter here would be the
 * second budget this file already refuses to be.
 *
 *   node web/eval_campuses.mjs [--json]      needs a static server on
 *   TC_URL (default http://127.0.0.1:8811/web/trade_craft_3d.html) and the
 *   one Chromium this container can afford; verify_all.sh never runs it.
 */
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL_BASE = process.env.TC_URL ?? 'http://127.0.0.1:8811/web/trade_craft_3d.html';
const JSON_OUT = process.argv.includes('--json');

/* the budget, read from eval_scene.mjs by structure - a number typed here
   would be a second budget */
const SRC = readFileSync(path.join(HERE, 'eval_scene.mjs'), 'utf8');
const num = (re, what) => {
  const m = SRC.match(re);
  if (!m) throw new Error(`eval_scene.mjs no longer declares ${what}; this harness has no budget to judge by`);
  return Number(m[1].replace(/_/g, ''));
};
const BASE = {
  calls: num(/^\s*campus:\s*\{\s*calls:\s*([\d_]+)/m, 'BASE.campus.calls'),
  tris: num(/^\s*campus:\s*\{\s*calls:\s*[\d_]+,\s*tris:\s*([\d_]+)/m, 'BASE.campus.tris'),
  meshes: num(/^\s*campus:\s*\{\s*calls:\s*[\d_]+,\s*tris:\s*[\d_]+,\s*meshes:\s*([\d_]+)/m, 'BASE.campus.meshes'),
  signs: num(/^\s*campus:\s*\{\s*signs:\s*([\d_]+)/m, 'LEGIBLE.campus.signs'),
  pairs: num(/^\s*campus:\s*\{\s*signs:\s*[\d_]+,\s*pairs:\s*([\d_]+)/m, 'LEGIBLE.campus.pairs'),
};
const H = {
  calls: num(/^const CALL_HEADROOM = ([\d.]+)/m, 'CALL_HEADROOM'),
  tris: num(/^const TRI_HEADROOM = ([\d.]+)/m, 'TRI_HEADROOM'),
  mesh: num(/^const MESH_FLOOR = ([\d.]+)/m, 'MESH_FLOOR'),
  pair: num(/^const PAIR_HEADROOM = ([\d.]+)/m, 'PAIR_HEADROOM'),
  sign: num(/^const SIGN_FLOOR = ([\d.]+)/m, 'SIGN_FLOOR'),
};
const CEIL = {
  maxCalls: Math.round(BASE.calls * H.calls),
  maxTris: BASE.tris * H.tris,
  minMeshes: Math.round(BASE.meshes * H.mesh),
  maxPairs: Math.max(BASE.pairs + 1, Math.round(BASE.pairs * H.pair)),
  minSigns: Math.round(BASE.signs * H.sign),
};

const CAMPUSES = JSON.parse(readFileSync(path.join(ROOT, 'unions/registry/campuses.json'), 'utf8')).campuses;
const SLUGS = Object.keys(CAMPUSES);
if (SLUGS.length === 0) throw new Error('unions/registry/campuses.json declares no campuses');

async function main() {
  const b = await chromium.launch({ executablePath: CHROME,
    args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const pg = await b.newPage({ viewport: { width: 1280, height: 800 } });
  const errs = [];
  pg.on('pageerror', (e) => errs.push(e.message));
  pg.on('console', (m) => { if (m.type() === 'error') errs.push('console: ' + m.text().slice(0, 200)); });
  await pg.goto(URL_BASE, { waitUntil: 'load' });
  await pg.waitForFunction(() => window.__tc3d, null, { timeout: 90_000 });
  await pg.waitForTimeout(3000);

  const rows = [];
  for (const slug of SLUGS) {
    await pg.evaluate((s) => window.__tc3dDo('view', 'campus:' + s), slug).catch(() => {});
    await pg.waitForTimeout(1800);
    await pg.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
    const m = await pg.evaluate(() => {
      const d = window.__tc3d();
      let meshes = 0; const mats = new Set();
      const walk = (o) => { if (!o.visible) return; if (o.isMesh) { meshes++; if (o.material) mats.add(o.material.uuid); } for (const c of o.children) walk(c); };
      walk(window.__tc3dScene());
      if (typeof window.__tc3dLabelRects !== 'function') throw new Error('the page exposes no __tc3dLabelRects()');
      const rects = window.__tc3dLabelRects();
      let pairs = 0, worstCover = 0, worstPair = null;
      for (let i = 0; i < rects.length; i++) for (let j = i + 1; j < rects.length; j++) {
        const a = rects[i], b2 = rects[j];
        const w = Math.min(a.x + a.w, b2.x + b2.w) - Math.max(a.x, b2.x);
        const h = Math.min(a.y + a.h, b2.y + b2.h) - Math.max(a.y, b2.y);
        if (w <= 0 || h <= 0) continue;
        pairs++;
        const cover = w * h / Math.min(a.w * a.h, b2.w * b2.h);
        if (cover > worstCover) { worstCover = cover; worstPair = `${a.kind}:"${a.text}" / ${b2.kind}:"${b2.text}"`; }
      }
      // the signs BY KIND, off the rectangles the page reports: `hall` is
      // a building's own name; `anchor` and `schematic` are the city's
      // recorded anchors and the site tags (buildCity(), the restoration
      // sites); what is left is the plaza marquee and the district banners
      const byKind = {};
      for (const r of rects) byKind[r.kind] = (byKind[r.kind] ?? 0) + 1;
      const hallSigns = byKind.hall ?? 0;
      const anchorTagSigns = (byKind.anchor ?? 0) + (byKind.schematic ?? 0);
      return { view: d.view, calls: d.perf.calls, tris: d.perf.tris, tex: d.perf.tex, quality: d.quality,
        meshes, materials: mats.size, signs: rects.length, hallSigns, anchorTagSigns,
        otherSigns: rects.length - hallSigns - anchorTagSigns, byKind,
        pairs, worstCover: Math.round(worstCover * 100), worstPair };
    });
    const fails = [];
    const halls = CAMPUSES[slug].halls.length;
    const flagship = CAMPUSES[slug].flagship === true;
    if (m.view !== 'campus:' + slug && m.view !== 'campus') fails.push(`the page reports view "${m.view}", not this campus`);
    if (m.calls > CEIL.maxCalls) fails.push(`draw calls ${m.calls} > ${CEIL.maxCalls}`);
    if (m.tris > CEIL.maxTris) fails.push(`triangles ${m.tris} > ${CEIL.maxTris}`);
    if (m.pairs > CEIL.maxPairs) fails.push(`${m.pairs} overlapping label pairs > ${CEIL.maxPairs}` + (m.worstPair ? ` (worst ${m.worstCover}%: ${m.worstPair})` : ''));
    // the floors were calibrated on the flagship and are applied to it alone
    if (flagship && m.meshes < CEIL.minMeshes) fails.push(`only ${m.meshes} visible meshes, floor is ${CEIL.minMeshes}`);
    if (flagship && m.signs < CEIL.minSigns) fails.push(`only ${m.signs} signs on screen, floor is ${CEIL.minSigns}`);
    rows.push({ campus: slug, halls, flagship, floors_judged: flagship, ...m, fails });
  }
  await b.close();
  const bad = rows.filter((r) => r.fails.length).length;
  if (JSON_OUT) {
    console.log(JSON.stringify({ ceiling: CEIL, base: BASE, rows, errors: errs, failing: bad, campuses: SLUGS.length }, null, 1));
  } else {
    console.log(`\ncampus eval - every campus in unions/registry/campuses.json, measured in Chromium against eval_scene.mjs's campus ceiling\n`);
    console.log('signs are counted by kind off __tc3dLabelRects(): hall = a building\'s own name, anch+tag = the city\'s recorded anchors and site tags, other = the plaza marquee and district banners\n');
    console.log(`${'campus'.padEnd(16)} ${'halls'.padStart(5)} ${'calls'.padStart(6)} ${'of'.padStart(5)} ${'triangles'.padStart(10)} ${'of'.padStart(5)} ${'meshes'.padStart(7)} ${'signs'.padStart(6)} ${'hall'.padStart(5)} ${'anch+tag'.padStart(8)} ${'other'.padStart(5)} ${'pairs'.padStart(6)} ${'of'.padStart(4)}  floors`);
    for (const r of rows) console.log(`${r.campus.padEnd(16)} ${String(r.halls).padStart(5)} ${String(r.calls).padStart(6)} ${((r.calls / CEIL.maxCalls) * 100).toFixed(0).padStart(4)}% ${String(r.tris).padStart(10)} ${((r.tris / CEIL.maxTris) * 100).toFixed(0).padStart(4)}% ${String(r.meshes).padStart(7)} ${String(r.signs).padStart(6)} ${String(r.hallSigns).padStart(5)} ${String(r.anchorTagSigns).padStart(8)} ${String(r.otherSigns).padStart(5)} ${String(r.pairs).padStart(6)} ${String(CEIL.maxPairs).padStart(4)}  ${r.floors_judged ? `judged (meshes >= ${CEIL.minMeshes}, signs >= ${CEIL.minSigns})` : 'measured, not judged: floors were calibrated on the flagship'}` + (r.fails.length ? '   <<< ' + r.fails.join('; ') : ''));
    console.log(`\n${SLUGS.length} campuses scored, ${bad} over a cap or, on the flagship, under a floor` + (errs.length ? `, ${errs.length} page error(s)` : ', no page errors'));
    for (const e of errs.slice(0, 5)) console.log('  page error: ' + e);
  }
  process.exit(bad || errs.length ? 1 : 0);
}
main();
