/* seasons/test.mjs - the AUTHORED game calendar, checked. Browser-free, network-free.
 * Recompute, never re-read: the stamp over the build inputs, the month board from the tasks, every plot point
 * against the RECORDED outline and the lot / district it claims to sit on. Prints `  ok ` per check, FAIL at col 0.
 */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m); } };
const read = (p) => readFileSync(join(ROOT, p), 'utf8');
const J = (p) => JSON.parse(read(p));

const R = J('seasons/registry/seasons.json');
const SRC = read('seasons/build.py');
const ECON = J('economy/registry/economy.json');
const BAY = J('bayarea/registry/bayarea.json');
const PAR = J('parishes/registry/parishes.json');
const CAL = 'approximate, game calendar';
console.log('seasons/test.mjs');

/* ---- provenance ---- */
{
  const h = createHash('sha256'); for (const p of R.inputs) h.update(readFileSync(join(ROOT, p)));
  const full = h.digest('hex');
  ok(R.pack === 'seasons' && full === R.source_stamp_sha256 && full.slice(0, 16) === R.source_stamp,
     'stamp: sha256 over the build inputs matches the registry (rebuild after any input change)');
}
ok(R.pack_version === J('pack/manifest.json').pack_version, 'pack_version is read from the manifest');
ok(!/\?\?|\.get\(/.test(SRC), 'fail closed: the builder has no ?? and no .get(k, default)');
ok(R.tasks.every((t) => t.provenance === 'AUTHORED') && R.rotations.every((r) => r.provenance === 'AUTHORED')
   && Object.values(R.plots).every((w) => w.plots.every((p) => p.provenance === 'AUTHORED')),
   'every task, rotation and plot is AUTHORED');

/* ---- honesty ---- */
const H = R.honesty;
ok(/PLAY/.test(H.play) && /never a completion record/.test(H.play) && /never money/.test(H.play), 'honesty: play, device-local, never a record, never money');
ok(H.calendar.includes(CAL) && H.rules.includes('Louisiana Department of Wildlife and Fisheries')
   && H.rules.includes('California Department of Fish and Wildlife'), 'honesty: game-calendar label and the state-rules line with both agencies');
ok(Object.values(R.calendar).every((c) => c.label === CAL) && R.tasks.every((t) => t.calendar === CAL),
   'label: every calendar and task carries "approximate, game calendar"');

/* ---- calendar recomputed ---- */
ok(Object.keys(R.calendar).sort().join() === 'bay,louisiana', 'calendar: one per region (bay, louisiana)');
let calOk = true;
for (const [rid, c] of Object.entries(R.calendar)) {
  if (c.months.map((m) => m.month).join() !== '1,2,3,4,5,6,7,8,9,10,11,12') calOk = false;
  for (const m of c.months) {
    const want = R.tasks.filter((t) => t.region === rid && t.months.includes(m.month)).map((t) => t.id).join();
    if (m.in_season.join() !== want) calOk = false;
  }
}
ok(calOk, 'calendar: 12 months per region, each month\'s in-season list recomputed from the tasks');
ok(R.tasks.every((t) => t.months.length > 0 && new Set(t.months).size === t.months.length && t.months.every((m) => Number.isInteger(m) && m >= 1 && m <= 12)),
   'months: every task has unique months in 1..12');

/* ---- the asked-for content ---- */
const T = Object.fromEntries(R.tasks.map((t) => [t.id, t]));
const need = ['rice', 'sugarcane-harvest', 'strawberry-picking', 'citrus-harvest', 'pecan-gathering', 'garden-plot',
              'orchard', 'vineyard-harvest', 'community-garden', 'shoreline-cleanup', 'parade-season', 'festival-day',
              'storm-drill', 'back-to-school'];
ok(need.every((k) => T[k]), `content: all asked tasks present (${need.length})`);
ok(T.rice && T.rice.stages.map((s) => s.id).join() === 'field-prep,flooding,planting,growth,draining,harvest',
   'rice: field prep, flooding, planting, growth, draining, harvest - in order');
const ROT = R.rotations.find((r) => r.id === 'rice-crawfish-rotation');
ok(ROT && T.rice.rotation === ROT.id && /general terms/.test(ROT.text) && /FISH/.test(ROT.crawfish_trapping),
   'rotation: stable id rice-crawfish-rotation, linked from rice, general terms, trapping left to FISH');
ok(R.tasks.filter((t) => t.region === 'bay').length >= 4 && R.tasks.filter((t) => t.region === 'louisiana').length >= 6,
   'regions: Louisiana and Bay each carry their own tasks');
const DENY = ['mardi gras', 'jazz fest', 'jazz & heritage', 'coastal cleanup day', 'festival international', 'essence',
              'strawberry festival', 'rice festival', 'sugar cane festival', 'crawfish festival', 'rex', 'zulu', 'bacchus',
              'endymion', 'fleet week', 'outside lands', 'bottlerock']; // a partial list of real named events
ok(R.tasks.every((t) => !DENY.some((d) => (t.label + ' ' + t.fact).toLowerCase().includes(d))),
   'events are named generically: no label or fact matches the (partial) denylist of real event names');

/* ---- informative, never invented ---- */
ok(R.tasks.every((t) => /\(source kind: [a-z ]+\)\.$/.test(t.fact)), 'facts: every task has one general line naming the kind of source');
ok(R.tasks.every((t) => !/\d/.test(t.fact)) && !/\d/.test(ROT.text.replace('Months here', '')),
   'facts: no number appears in any fact (no yields, dates, sizes or quotas)');
ok(R.tasks.every((t) => t.safety.length > 0 && t.safety.every((s) => typeof R.safety[s] === 'string')),
   'safety: every task has at least one note and every note resolves');
ok(['heat', 'water', 'tools'].every((k) => R.safety[k]) && T.rice.safety.includes('water') && /alligator/.test(R.safety.water),
   'safety: heat, water and tools notes exist; rice carries water safety with the wildlife rule');

/* ---- stages and windows ---- */
const PH = new Set(['prepare', 'plant', 'tend', 'harvest']);
ok(R.tasks.every((t) => t.stages.length >= 2 && t.stages.every((s) => PH.has(s.phase) && s.window_days.length === 2
   && s.window_days[0] >= 0 && s.window_days[0] <= s.window_days[1])),
   'stages: every stage has a phase in prepare|plant|tend|harvest and a window 0 <= lo <= hi');
ok(R.tasks.every((t) => t.stages.some((s) => s.phase === 'harvest')), 'stages: every task ends in something to harvest or finish');
ok(R.tasks.every((t) => !('band' in t) || ['K-5', '6-8', '9-10', '11-12'].includes(t.band)), 'bands: K-12 bands only');
const clk = R.game_clock;
ok(clk.days_per_month > 0 && clk.start_month >= 1 && clk.start_month <= 12 && clk.speeds.some((s) => s.id === 'pause' && s.s_per_day === 0)
   && clk.speeds.filter((s) => s.s_per_day > 0).length >= 3, 'clock: game clock with pause and at least three speeds');

/* ---- plots on AUTHORED land use, inside the RECORDED outline ---- */
function inside(pt, polys) {
  const [x, y] = pt; let hit = false;
  for (const poly of polys) for (const ring of poly) for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) hit = !hit;
  }
  return hit;
}
const want = [...Object.keys(ECON.parishes), ...Object.keys(BAY.counties)].sort();
ok(Object.keys(R.plots).sort().join() === want.join(), `plots: one entry per economy parish and Bay county (${want.length})`);
let inOk = true, onOk = true, frameOk = true, ids = new Set(), dup = false;
for (const [f, w] of Object.entries(R.plots)) {
  const outline = w.region === 'louisiana' ? PAR.parishes[f].outline_local_m : BAY.counties[f].outline_local_m;
  if (w.plots.length !== 3) inOk = false;
  for (const p of w.plots) {
    if (ids.has(p.id)) dup = true; ids.add(p.id);
    if (!inside(p.local_m, outline)) inOk = false;
    if (p.x !== p.local_m[0] || p.z !== -p.local_m[1]) frameOk = false;
    if (w.region === 'louisiana') {
      const lot = ECON.parishes[f].lots.find((l) => l.id === p.on);
      if (!lot || lot.zone !== 'residential' || lot.local_m.join() !== p.local_m.join()) onOk = false;
    } else {
      const d = BAY.counties[f].districts.find((q) => q.id === p.on);
      if (!d || d.provenance !== 'AUTHORED' || !['park', 'residential'].includes(d.use) || d.use !== p.land_use
          || d.seed_local_m.join() !== p.local_m.join()) onOk = false;
    }
  }
}
ok(inOk, 'plots: 3 per world, every point inside the RECORDED coarse outline (point in polygon, recomputed)');
ok(onOk, 'plots: each sits on the economy residential lot / AUTHORED Bay district it names, at the same point');
ok(frameOk && !dup, 'plots: unique ids; scene convention x = east_m, z = -north_m');
ok(Object.values(R.plots).filter((w) => w.region === 'bay').every((w) => w.plots.some((p) => p.land_use === 'park')),
   'plots: every Bay county has at least one park-district plot');

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
