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
 *
 * It also scores LEGIBILITY, for the same reason it scores draw calls. A
 * screenshot of the default hall showed the Classroom plate, three
 * training-ladder plates and seven advisor bubbles collapsed into stacks
 * you could not read a word of, and nothing in the bundle could say so: a
 * harness outside the page had no way to find out where a sign lands on
 * the screen, so the only evidence was somebody opening a picture. A fault
 * you can only see and never count comes back. The page now reports each
 * on-screen sign's rectangle through __tc3dLabelRects(), and the two
 * numbers below are scored against declared limits at both ends -
 * overlapping pairs at the top, signs standing at the bottom, because
 * legibility bought by taking signage away is not legibility.
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
  /* The same hall as the row above, from inside it. Measured 2026-09-24,
     same browser, same viewport, same rung. */
  'hall-eye': { calls: 123, tris: 12_146, meshes: 223 },
};
const CALL_HEADROOM = 1.25;     // draw calls are the scarce currency
const TRI_HEADROOM = 4;         // triangles are not, and are meant to grow
const MESH_FLOOR = 0.9;         // losing a tenth of the visible pieces is a regression

/* LEGIBILITY, per row, and held at BOTH ends.

   `pairs` is how many PAIRS of on-screen sign rectangles overlap each
   other at all, counted from __tc3dLabelRects(). `signs` is how many signs
   are on the screen to begin with. Both are measured, not chosen, and they
   are scored in opposite directions on purpose:

     * a rising `pairs` is signage collapsing back into the piles this was
       written after - the default hall ran 15 overlapping pairs of 22
       signs, five of them covering more than half the smaller plate;
     * a falling `signs` is the cheat that would make `pairs` look good.
       Hiding signage until none of it collides scores a perfect zero and
       leaves a building with nothing written on it, so the sign count has
       a floor exactly as the visible-mesh count does.

   The headroom on pairs is small - a quarter, and never fewer than one
   extra pair, so a view that measures none is not held to a limit it
   cannot round below. Signs are held to the same tenth the meshes are. */
const LEGIBLE = {
  region:       { signs: 32, pairs: 12 },
  campus:       { signs: 26, pairs: 3 },
  hall:         { signs: 15, pairs: 2 },
  'hall-worst': { signs: 15, pairs: 2 },
  /* Standing on the floor of a hall. These two numbers are the reason the
     row below exists, and they are worth writing down in the order they
     were measured:

       15 signs / 10 pairs   the view as the declutter work left it. Six of
                             the ten pairs were against two PPE placards
                             670 and 678 px wide on a 1280 px screen - a
                             sign fourteen metres wide in the world.
       14 signs /  5 pairs   the placard redrawn as a stacked board. Pairs
                             halved, but a sign was LOST: the board hung
                             beside a doorway chosen by one measure and a
                             jamb chosen by another, which put it 21.2 m
                             from the eye, past the 20 m the label registry
                             says a placard is read from.
       16 signs /  6 pairs   the placement rule made one measure throughout.
                             Both of those boards come back, and a third
                             that was never on screen before.

     So the floor is set from SIXTEEN, one more than the view carried
     before any of this - which is the only shape of this result worth
     accepting. A pair count that falls while the sign count falls with it
     is signage being taken away, and the floor below is what says so. */
  'hall-eye':   { signs: 16, pairs: 6 },
};
const PAIR_HEADROOM = 1.25;
const SIGN_FLOOR = 0.9;

const ceil = (id, leg = id) => {
  const g = LEGIBLE[leg];
  if (!g) throw new Error(`LEGIBLE declares no sign baseline for the "${leg}" `
    + 'row, so its legibility would be scored against nothing');
  return {
    maxCalls: Math.round(BASE[id].calls * CALL_HEADROOM),
    maxTris: BASE[id].tris * TRI_HEADROOM,
    minMeshes: Math.round(BASE[id].meshes * MESH_FLOOR),
    maxPairs: Math.max(g.pairs + 1, Math.round(g.pairs * PAIR_HEADROOM)),
    minSigns: Math.round(g.signs * SIGN_FLOOR),
  };
};

const VIEWS = [
  { id: 'region', go: null, ...ceil('region'),
    why: 'the opening board: ten campus plates and their labels' },
  { id: 'campus', go: (p) => p.evaluate(() => window.__tc3dDo('view', 'campus:treasure-island')),
    ...ceil('campus'),
    why: 'a campus green with its halls, yard seats, roads and beacons' },
  { id: 'hall', go: (p) => p.evaluate(() => window.__tc3dDo('view', 'hall')),
    ...ceil('hall'),
    why: 'one hall interior: eleven rooms, their partitions and lamps' },
  /* The SAME view, opened on the most expensive hall in the network rather
     than the one that happens to be first.

     This row exists because scoring `hall` alone was scoring ironworkers and
     nothing else: it costs 164 calls and sits almost exactly at the median of
     111, so it reported comfortable headroom while 11 halls were over the
     ceiling, the worst at 238 (121%). A budget checked only against the
     median case is not a budget. The sweep below finds the worst hall by
     measuring every one, so this row cannot go stale as content changes. */
  /* THE VIEW A LEARNER IS ACTUALLY IN.

     Every row above is an orbit view: a board, a green, and a building seen
     from outside it. None of them is where somebody using this spends their
     time, which is standing on the floor of a hall looking down it - and
     that view was not scored, so the declutter pass that cleaned up the
     four orbit views left the one people use holding fifteen signs with ten
     overlapping pairs. A guard that measures every view except the one the
     work is for is not measuring the work.

     1.7 m is a standing eye. (0, 1.7, 14) is on the hall's own centre line,
     back from the middle, looking down the aisle towards the open front -
     the way the building is entered and the way its rooms are addressed.
     The camera is placed through the page's own `cam` hook for the same
     reason every other row moves through `view`: a harness that got there
     by dragging would be scoring wherever the drag happened to stop. */
  { id: 'hall-eye', go: async (p) => {
      await p.evaluate(() => window.__tc3dDo('view', 'hall'));
      await p.waitForTimeout(1400);
      await p.evaluate(() => window.__tc3dDo('cam', '0,1.7,14|0,1.7,0'));
    },
    ...ceil('hall-eye'),
    why: 'standing on the floor of a hall at eye level, looking down the aisle' },
  { id: 'hall-worst', worst: true, ...ceil('hall', 'hall-worst'),
    why: 'the most expensive of the 111 hall interiors, found by measuring them all' },
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
    if (v.worst) {
      // Measure every hall, then leave the view standing on the dearest one
      // so the block below scores it exactly like any other row.
      const slugs = await pg.evaluate(() => window.__tc3d().hallSlugs);
      let worst = null;
      for (const s of slugs) {
        await pg.evaluate((x) => window.__tc3dDo('view', 'hall:' + x), s);
        await pg.waitForTimeout(600);
        await pg.evaluate(() => new Promise((r) =>
          requestAnimationFrame(() => requestAnimationFrame(r))));
        const c = await pg.evaluate(() => window.__tc3d().perf.calls);
        if (!worst || c > worst.calls) worst = { slug: s, calls: c };
      }
      v.why = `the dearest of ${slugs.length} halls: ${worst.slug}`;
      await pg.evaluate((x) => window.__tc3dDo('view', 'hall:' + x), worst.slug);
      await pg.waitForTimeout(1200);
    } else if (v.go) { await v.go(pg).catch(() => {}); await pg.waitForTimeout(1800); }
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
      /* Where every sign actually landed this frame. The page projects its
         own sprites - see lblRect() in web/build_3d.py - because a second
         copy of that projection written here could disagree with the one
         the renderer used, and then this would be scoring a picture the
         page never drew. What is decided HERE is only what counts as an
         overlap, which is the harness's question and not the page's. */
      if (typeof window.__tc3dLabelRects !== 'function')
        throw new Error('the page exposes no __tc3dLabelRects(), so where its '
          + 'signs land on the screen cannot be measured from out here and '
          + 'legibility would be a matter of opinion again');
      const rects = window.__tc3dLabelRects();
      let pairs = 0, worstCover = 0, worstPair = null;
      for (let i = 0; i < rects.length; i++)
        for (let j = i + 1; j < rects.length; j++) {
          const a = rects[i], b2 = rects[j];
          const w = Math.min(a.x + a.w, b2.x + b2.w) - Math.max(a.x, b2.x);
          const h = Math.min(a.y + a.h, b2.y + b2.h) - Math.max(a.y, b2.y);
          if (w <= 0 || h <= 0) continue;
          pairs++;
          // as a fraction of the SMALLER plate, so a small sign swallowed
          // whole by a big one reads as covered rather than as a nibble
          const cover = w * h / Math.min(a.w * a.h, b2.w * b2.h);
          if (cover > worstCover) {
            worstCover = cover;
            worstPair = `${a.kind}:"${a.text}" / ${b2.kind}:"${b2.text}"`;
          }
        }
      return { view: d.view, calls: d.perf.calls, tris: d.perf.tris,
               tex: d.perf.tex, geoms: d.perf.geoms, quality: d.quality,
               meshes, materials: mats.size,
               signs: rects.length, pairs,
               worstCover: Math.round(worstCover * 100), worstPair };
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
    if (r.pairs > r.maxPairs) fails.push(`${r.pairs} overlapping label pairs > ${r.maxPairs}`
      + (r.worstPair ? ` (worst ${r.worstCover}%: ${r.worstPair})` : ''));
    if (r.signs < r.minSigns) fails.push(`only ${r.signs} signs on screen, floor is ${r.minSigns}`
      + ' - legibility bought by taking signage away is not legibility');
    if (fails.length) bad++;
    line.push({ ...r, fails });
  }

  if (JSON_OUT) {
    console.log(JSON.stringify({ rows: line, errors: errs, failing: bad }, null, 1));
  } else {
    console.log('\nscene eval — measured in Chromium, one frame per view\n');
    console.log(`${'view'.padEnd(9)} ${'calls'.padStart(6)} ${'of'.padStart(5)} `
      + `${'triangles'.padStart(11)} ${'of'.padStart(5)} ${'meshes'.padStart(7)} `
      + `${'floor'.padStart(6)} ${'signs'.padStart(6)} ${'floor'.padStart(6)} `
      + `${'pairs'.padStart(6)} ${'of'.padStart(4)} `
      + `${'mats'.padStart(5)} ${'tex'.padStart(5)}  rung`);
    for (const r of line) {
      console.log(`${r.id.padEnd(11)} ${String(r.calls).padStart(6)} ${pct(r.calls, r.maxCalls).padStart(5)} `
        + `${r.tris.toLocaleString().padStart(11)} ${pct(r.tris, r.maxTris).padStart(5)} `
        + `${String(r.meshes).padStart(7)} ${String(r.minMeshes).padStart(6)} `
        + `${String(r.signs).padStart(6)} ${String(r.minSigns).padStart(6)} `
        + `${String(r.pairs).padStart(6)} ${String(r.maxPairs).padStart(4)} `
        + `${String(r.materials).padStart(5)} ${String(r.tex).padStart(5)}  ${r.quality}`
        + (r.fails.length ? '   <<< ' + r.fails.join('; ') : ''));
    }
    // the worst pair per view, named, so a number crossing a line comes
    // with the two signs that did it rather than sending somebody hunting
    for (const r of line)
      if (r.worstPair)
        console.log(`  ${r.id}: worst overlap ${r.worstCover}% of the smaller `
          + `plate - ${r.worstPair}`);
    for (const r of line) console.log(`  ${r.id}: ${r.why}`);
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
