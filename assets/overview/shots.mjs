/**
 * Capture the stills the overview is cut from, out of the RUNNING app.
 *
 * Not mock-ups and not renders made for the camera: every frame below is
 * the real page, driven to a real view, screenshotted. If a surface is
 * broken the overview shows it broken, which is the only way a promotional
 * artefact is worth anything to the people building the thing.
 *
 * Software GL in this container renders at a couple of frames a second, so
 * capturing motion directly would produce a slideshow pretending to be
 * video. Stills are captured here and the movement is added in post by
 * assets/overview/build_overview.py, which is honest about what it is: a
 * pan across a real frame rather than a recording of a smooth one.
 *
 * Run:  python3 -m http.server 8811    (from the repo root)
 *       node assets/overview/shots.mjs
 */
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = join(HERE, 'frames');
const BASE = process.env.TC_URL ?? 'http://127.0.0.1:8811';
const APP = `${BASE}/web/trade_craft_3d.html`;
const W = 1920, H = 1080;

/* Each shot: where it comes from, and how to get the page there.
   `settle` is how long the view is given before the shutter - a campus
   builds its fabric, its roads and its beacons on arrival, and a frame
   taken too early shows a half-built place. */
const SHOTS = [
  { id: '01-front-door', url: `${BASE}/index.html`, settle: 2500, full: false,
    what: 'the generated front door, with the campus network drawn from real coordinates' },
  { id: '02-region', url: APP, settle: 4000,
    what: 'the region board: ten campuses as plates on a map' },
  { id: '03-campus-noon', url: APP, settle: 4000,
    go: async (p) => { await p.evaluate(() => window.__tc3dDo('view', 'campus:treasure-island')); },
    what: 'a campus green at noon' },
  // Standing on the ground and looking at the horizon, because that is
  // where the dome is. From the overhead orbit the campus fills the frame
  // and the sky barely appears, so an hour change reads only in the
  // lighting - true, and the wrong shot for showing a sky.
  { id: '04-campus-golden', url: null, settle: 2500,
    go: async (p) => {
      await p.evaluate(() => window.__tc3dPhase('golden-hour'));
      await p.evaluate(() => window.__tc3dLook(0, 2.2, 60, 0, 14, -200));
    },
    what: 'golden hour from the ground - the sun placed by its solved elevation' },
  { id: '05-campus-night', url: null, settle: 2500,
    go: async (p) => {
      await p.evaluate(() => window.__tc3dPhase('night'));
      await p.evaluate(() => window.__tc3dLook(0, 2.2, 60, 0, 14, -200));
    },
    what: 'and the same view at night, the stars up because the sun is down' },
  { id: '06-hall', url: null, settle: 3500,
    go: async (p) => {
      await p.evaluate(() => window.__tc3dPhase('noon'));
      await p.evaluate(() => window.__tc3dDo('view', 'hall'));
    },
    what: 'inside a hall: eleven rooms, each with its own finish and light' },
  { id: '07-seat', url: null, settle: 3500,
    go: async (p) => { await p.evaluate(() => window.__tc3dSim.start('crane-lift')); },
    what: 'a training seat, operable and scored' },
  { id: '08-guide', url: null, settle: 2000,
    go: async (p) => {
      await p.evaluate(() => window.__tc3dGuide());
    },
    what: 'the guide, reachable from every view' },
  { id: '09-dashboard', url: `${BASE}/web/trade_craft_dashboard.html`, settle: 2500, full: false,
    what: 'the network dashboard, every figure read from the pack that owns it' },
  { id: '10-map', url: `${BASE}/web/trade_craft_interactive.html`, settle: 3000, full: false,
    what: 'the interactive campus map, all 111 halls with switchable layers' },
];

mkdirSync(OUT, { recursive: true });
const b = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'],
});
const pg = await b.newPage({ viewport: { width: W, height: H } });
const errs = [];
pg.on('pageerror', (e) => errs.push(e.message));

const taken = [];
for (const s of SHOTS) {
  if (s.url) {
    await pg.goto(s.url, { waitUntil: 'load' });
    if (s.url === APP) {
      await pg.waitForFunction(() => window.__tc3d, null, { timeout: 90_000 });
    }
  }
  if (s.go) await s.go(pg);
  await pg.waitForTimeout(s.settle);
  const file = join(OUT, s.id + '.png');
  await pg.screenshot({ path: file, fullPage: !!s.full });
  taken.push({ id: s.id, what: s.what, file });
  console.log(`  ${s.id.padEnd(18)} ${s.what}`);
}
writeFileSync(join(OUT, 'index.json'),
  JSON.stringify({ captured: new Date().toISOString().slice(0, 10),
                   viewport: [W, H], shots: taken }, null, 1) + '\n');
await b.close();

// A page error during capture means the overview is showing a broken app.
// It is not a warning; it fails the capture.
if (errs.length) {
  console.error(`\n${errs.length} page error(s) during capture:`);
  for (const e of errs.slice(0, 6)) console.error('  ' + e);
  process.exit(1);
}
console.log(`\n${taken.length} frames captured into assets/overview/frames/, no page errors`);
