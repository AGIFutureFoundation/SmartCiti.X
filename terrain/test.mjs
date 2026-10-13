/* terrain/test.mjs — the ground under the ten campuses, checked.
 *
 * The rule this suite follows: never confirm a number by reading it. Every
 * figure the registry publishes is recomputed here, in JavaScript, from the
 * vendored GeoJSON — a second implementation of the same question, written
 * against the source rather than against the answer. Where that is not
 * possible (a hash), the check is against the file on disk.
 *
 * Point-in-polygon in particular is deliberately re-implemented rather than
 * ported: an even-odd test copied from the builder would agree with the
 * builder about a bug.
 */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok ' + m); }
                       else { fail++; console.log('  FAIL ' + m); } };

const read = (p) => readFileSync(join(ROOT, p), 'utf8');
const J = (p) => JSON.parse(read(p));

const T = J('terrain/registry/terrain.json');
const MAN = J('terrain/vendor/manifest.json');
const GEO = J('geo/registry/campuses_geo.json');
const C = T.campuses;
const KEYS = Object.keys(C).sort();

console.log('terrain/test.mjs');

/* ---- provenance and licence --------------------------------------- */
ok(T.pack === 'terrain', 'the registry names its own pack');
ok(T.honesty.status.startsWith('DERIVED:'),
   'the honesty block opens with the provenance tier, and it is DERIVED');
ok(!JSON.stringify(T).includes('AI-SYNTHESIZED'),
   'the reserved provenance word does not appear here — it belongs to orbis/');
ok(!/https?:\/\//.test(JSON.stringify(T)),
   'no URL is in the payload, because nothing here is fetched at run time');

{
  const body = readFileSync(join(HERE, 'vendor/NATURAL_EARTH_LICENSE.md'));
  const got = createHash('sha256').update(body).digest('hex');
  ok(got === T.licence_sha256,
     'the licence hash the registry publishes is the licence file on disk');
  ok(T.licence === MAN.licence && T.source === MAN.source,
     'the licence and source strings are the vendor manifest\'s own words');
}

{
  const src = Buffer.concat([readFileSync(join(HERE, 'build.py')),
                             readFileSync(join(HERE, 'vendor/manifest.json'))]);
  ok(createHash('sha256').update(src).digest('hex').slice(0, 16)
     === T.source_stamp,
     'the registry was built from the current builder and the current '
     + 'vendor manifest (stamp check)');
}

/* ---- the vendored files are the ones that were vendored ------------ */
const LAYERS = ['coastline', 'land', 'lakes', 'rivers'];
const RAW = {};
for (const layer of LAYERS) {
  const name = `ne_${layer}.json`;
  const body = readFileSync(join(HERE, 'vendor', name));
  ok(createHash('sha256').update(body).digest('hex') === MAN.files[name].sha256,
     `${name} hashes to what the vendor manifest recorded`);
  RAW[layer] = JSON.parse(body);
}

/* ---- the campus set ------------------------------------------------ */
ok(KEYS.length === 10, 'all ten campuses have ground');
ok(KEYS.join() === [...MAN.campuses].sort().join(),
   'the campus set is exactly the set the vendor fetch clipped for');
ok(KEYS.join() === Object.keys(GEO.campuses).sort().join(),
   'and exactly the set the geo pack publishes — no eleventh, no missing one');

for (const k of KEYS) {
  const g = GEO.campuses[k];
  if (C[k].anchor.lat !== g.lat || C[k].anchor.lng !== g.lng) {
    ok(false, `${k}: the anchor is the geo pack's own centroid, not a copy`);
  }
}
ok(KEYS.every(k => C[k].anchor.lat === GEO.campuses[k].lat
                && C[k].anchor.lng === GEO.campuses[k].lng),
   'every anchor equals the geo pack\'s campus centroid exactly — this pack '
   + 'holds no second opinion about where a campus is');

/* ---- geometry: recomputed, not read -------------------------------- */
const M_PER_DEG = 111320;
const toLocal = (lng, lat, lat0, lng0) => [
  (lng - lng0) * M_PER_DEG * Math.cos(lat0 * Math.PI / 180),
  (lat - lat0) * M_PER_DEG];

const ringsOf = (f) => {
  const g = f.geometry;
  if (g.type === 'Polygon') return g.coordinates;
  if (g.type === 'MultiPolygon') return g.coordinates.flat();
  throw new Error('unexpected ' + g.type);
};

/* A winding-number test. The builder uses even-odd ray casting; this is a
 * different algorithm reaching the same answer, so agreement means the
 * answer is right rather than that the code was copied. */
const windingInside = (x, y, rings) => {
  let w = 0;
  for (const r of rings) {
    for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
      const [xi, yi] = r[i], [xj, yj] = r[j];
      if (yj <= y) {
        if (yi > y && ((xi - xj) * (y - yj) - (x - xj) * (yi - yj)) > 0) w++;
      } else if (yi <= y
                 && ((xi - xj) * (y - yj) - (x - xj) * (yi - yj)) < 0) w--;
    }
  }
  return w !== 0;
};

let maskCellsChecked = 0, maskDisagreements = 0;
let windowViolations = 0, shortRuns = 0, dupPoints = 0;
let landShareBad = 0, waterCellBad = 0, boundaryBad = 0, anchorBad = 0;
let edgeBad = 0, coastKmBad = 0, cellNearBad = 0;

for (const k of KEYS) {
  const c = C[k];
  const { lat: lat0, lng: lng0 } = c.anchor;
  const half = c.local.half_m;
  const n = c.mask.n, step = 2 * half / n;

  const landRings = RAW.land.campuses[k].features.flatMap(ringsOf)
    .map(r => r.map(p => toLocal(p[0], p[1], lat0, lng0)));
  const lakeRings = RAW.lakes.campuses[k].features.flatMap(ringsOf)
    .map(r => r.map(p => toLocal(p[0], p[1], lat0, lng0)));

  /* Every drawn point is inside the window it claims to be inside. */
  for (const line of [...c.local.coast, ...c.local.rivers, ...c.local.lakes]) {
    if (line.length < 2) shortRuns++;
    for (let i = 0; i < line.length; i++) {
      const [x, y] = line[i];
      if (Math.abs(x) > half + 0.05 || Math.abs(y) > half + 0.05) {
        windowViolations++;
      }
      if (i && line[i][0] === line[i - 1][0] && line[i][1] === line[i - 1][1]) {
        dupPoints++;
      }
    }
  }

  /* The mask, recomputed by a different algorithm, on a sampled lattice.
   * Every 5th cell in each direction: ~370 per campus, 3,700 in all, which
   * is enough to catch an off-by-one in the row packing or a flipped bit
   * order and fast enough to run in a suite. */
  let waterSeen = 0, landSeen = 0;
  for (let j = 0; j < n; j++) {
    const bits = BigInt('0x' + c.mask.rows[j]);
    const y = -half + (j + 0.5) * step;
    for (let i = 0; i < n; i++) {
      const bit = (bits >> BigInt(i)) & 1n;
      if (bit) landSeen++; else waterSeen++;
      if (j % 5 || i % 5) continue;
      const x = -half + (i + 0.5) * step;
      const want = windingInside(x, y, landRings)
                && !windingInside(x, y, lakeRings);
      maskCellsChecked++;
      if (want !== (bit === 1n)) maskDisagreements++;
    }
  }
  if (Math.abs(landSeen / (n * n) - c.mask.land_share) > 5e-5) landShareBad++;
  if (waterSeen !== c.facts.water_cells) waterCellBad++;

  const mid = n >> 1;
  const anchorLand = ((BigInt('0x' + c.mask.rows[mid]) >> BigInt(mid)) & 1n)
                     === 1n;
  if (anchorLand !== c.facts.anchor_on_land) anchorBad++;

  /* Nearest disagreeing cell and nearest water cell, both recomputed. */
  let bnd = null, nearCell = null;
  for (let j = 0; j < n; j++) {
    const bits = BigInt('0x' + c.mask.rows[j]);
    const y = -half + (j + 0.5) * step;
    for (let i = 0; i < n; i++) {
      const land = ((bits >> BigInt(i)) & 1n) === 1n;
      const x = -half + (i + 0.5) * step;
      const d = Math.hypot(x, y);
      if (land !== anchorLand && (bnd === null || d < bnd)) bnd = d;
      if (!land && (nearCell === null || d < nearCell)) nearCell = d;
    }
  }
  const close = (a, b) => (a === null) === (b === null)
    && (a === null || Math.abs(a - b) < 0.15);
  if (!close(bnd, c.facts.anchor_to_mask_boundary_m)) boundaryBad++;
  if (!close(nearCell, c.facts.nearest_water_cell_m)) cellNearBad++;

  /* Nearest water EDGE, point-to-segment, recomputed from the published
   * polylines. This is the figure the first draft got wrong. */
  let near = null;
  for (const line of [...c.local.coast, ...c.local.lakes,
                      ...c.local.rivers]) {
    for (let i = 1; i < line.length; i++) {
      const [ax, ay] = line[i - 1], [bx, by] = line[i];
      const dx = bx - ax, dy = by - ay, den = dx * dx + dy * dy;
      const t = den === 0 ? 0
        : Math.max(0, Math.min(1, (-ax * dx - ay * dy) / den));
      const d = Math.hypot(ax + t * dx, ay + t * dy);
      if (near === null || d < near) near = d;
    }
  }
  if (!close(near, c.facts.nearest_water_edge_m)) edgeBad++;

  let km = 0;
  for (const line of c.local.coast) {
    for (let i = 1; i < line.length; i++) {
      km += Math.hypot(line[i][0] - line[i - 1][0],
                       line[i][1] - line[i - 1][1]);
    }
  }
  if (Math.abs(km / 1000 - c.facts.coast_km_in_window) > 0.02) coastKmBad++;
}

ok(windowViolations === 0,
   'no drawn point sits outside the local window its campus publishes');
ok(shortRuns === 0, 'no polyline has fewer than two points to draw between');
ok(dupPoints === 0,
   'no polyline repeats a point — a zero-length segment renders as nothing '
   + 'and costs the same as a real one');
ok(maskDisagreements === 0,
   `the mask is right: ${maskCellsChecked} sampled cells recomputed here by `
   + 'winding number agree with the builder\'s even-odd test');
ok(maskCellsChecked > 3000,
   'and the sample is large enough to mean something (' + maskCellsChecked
   + ' cells)');
ok(landShareBad === 0,
   'every published land_share is the popcount of that campus\'s own rows');
ok(waterCellBad === 0, 'every water_cells count is that popcount\'s complement');
ok(anchorBad === 0,
   'every anchor_on_land flag is the bit under the campus, read back out');
ok(boundaryBad === 0,
   'every anchor_to_mask_boundary_m is the nearest cell that disagrees '
   + 'with the anchor');
ok(cellNearBad === 0, 'every nearest_water_cell_m is the nearest water cell');
ok(edgeBad === 0,
   'every nearest_water_edge_m is a point-to-SEGMENT distance — the first '
   + 'draft measured to the nearest vertex and put an island 3,195 m from '
   + 'the sea');
ok(coastKmBad === 0,
   'every coast_km_in_window is the summed length of that campus\'s own runs');

/* ---- the two-signal design ----------------------------------------- */
{
  const lineOnly = KEYS.filter(k => C[k].facts.nearest_water_edge_m !== null
                                 && C[k].facts.nearest_water_cell_m === null);
  const maskOnly = KEYS.filter(k => C[k].facts.nearest_water_edge_m === null
                                 && C[k].facts.nearest_water_cell_m !== null);
  ok(lineOnly.length > 0 && maskOnly.length > 0,
     'the two water signals genuinely disagree in both directions — '
     + lineOnly.join('/') + ' have a water line and a dry mask, '
     + maskOnly.join('/') + ' the reverse. Publishing one figure would have '
     + 'been wrong about one of them');
  ok(maskOnly.includes('chicago'),
     'Chicago is the mask-only case: Lake Michigan is where the land '
     + 'polygon stops, not a drawn water feature');
  ok(lineOnly.includes('new-orleans'),
     'New Orleans is the line-only case: a river in this source is a line '
     + 'with no width, so it can never darken a cell');
  ok(KEYS.every(k => C[k].facts.waterfront
     === (C[k].facts.nearest_water_edge_m !== null
          || C[k].facts.nearest_water_cell_m !== null)),
     'waterfront is true when EITHER signal fires, and only then');
}

/* ---- the honesty block earns its claims ---------------------------- */
{
  const wet = KEYS.filter(k => !C[k].facts.anchor_on_land).sort();
  ok(wet.length === T.counts.anchors_in_water,
     'the count of anchors standing on water is the number of campuses '
     + 'standing on water');
  ok(wet.length === 2 && wet.join(', ') === 'detroit, miami',
     'two of the ten are: ' + wet.join(', '));
  for (const k of wet) {
    ok(T.honesty.the_anchors_in_water.includes(k),
       `the honesty block names ${k} rather than saying "some campuses"`);
  }
  ok(T.honesty.the_anchors_in_water.includes(String(wet.length)),
     'and states the count in the same sentence it names them in');
  ok(T.honesty.resolution.includes(String(Math.round(T.counts.cell_m))),
     'the resolution note quotes the cell size this build actually used');
  ok(/no street, address or parcel/i.test(T.honesty.no_addresses),
     'the pack says outright that it carries no address — the checkout that '
     + 'has them keeps them out of git, and this pack does not pretend '
     + 'otherwise');
  ok(/PII/.test(T.honesty.no_addresses),
     'and gives that checkout\'s own stated reason rather than inventing one');
  ok(/no height|outline set/i.test(T.honesty.no_elevation),
     'and says there is no elevation in here, because there is not');
}

/* ---- counts ---------------------------------------------------------- */
{
  const sum = (f) => KEYS.reduce((a, k) => a + f(C[k]), 0);
  ok(T.counts.campuses === KEYS.length, 'counts.campuses is the campus count');
  ok(T.counts.coast_runs === sum(c => c.local.coast.length),
     'counts.coast_runs is the runs, counted');
  ok(T.counts.river_runs === sum(c => c.local.rivers.length),
     'counts.river_runs is the runs, counted');
  ok(T.counts.lake_rings === sum(c => c.local.lakes.length),
     'counts.lake_rings is the rings, counted');
  ok(T.counts.coast_points
     === sum(c => c.local.coast.reduce((a, l) => a + l.length, 0)),
     'counts.coast_points is the points, counted');
  ok(T.counts.mask_cells === KEYS.length * T.counts.mask_n ** 2,
     'counts.mask_cells is n squared per campus');
  ok(T.counts.mask_water_cells === sum(c => c.facts.water_cells),
     'counts.mask_water_cells is the per-campus water counts, added up');
  ok(T.counts.waterfront === KEYS.filter(k => C[k].facts.waterfront).length
     && T.counts.inland === KEYS.length - T.counts.waterfront,
     'waterfront and inland partition the ten — every campus is one or the '
     + 'other and none is both');
  ok(T.counts.cell_m === Math.round(2 * T.counts.local_half_m
                                    / T.counts.mask_n * 100) / 100,
     'counts.cell_m follows from the window and the grid, and is not typed');
  ok(KEYS.every(k => C[k].mask.n === T.counts.mask_n
                  && C[k].mask.cell_m === T.counts.cell_m
                  && C[k].local.half_m === T.counts.local_half_m),
     'every campus uses the one grid the counts describe — no campus has '
     + 'a private resolution');
}

/* ---- simplification is stable -------------------------------------- */
{
  const segDist = (p, a, b) => {
    const dx = b[0] - a[0], dy = b[1] - a[1], den = dx * dx + dy * dy;
    if (!den) return Math.hypot(p[0] - a[0], p[1] - a[1]);
    const t = Math.max(0, Math.min(1,
      ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / den));
    return Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy));
  };
  let removable = 0, lines = 0;
  for (const k of KEYS) {
    for (const line of [...C[k].local.coast, ...C[k].local.rivers]) {
      lines++;
      for (let i = 1; i < line.length - 1; i++) {
        if (segDist(line[i], line[i - 1], line[i + 1]) < 1) removable++;
      }
    }
  }
  ok(lines > 0, 'there are lines to check (' + lines + ')');
  ok(removable === 0,
     'no published vertex is collinear with its neighbours to within a '
     + 'metre — simplification already ran, and running it again would '
     + 'change nothing');
}

/* ---- the numbers are not decorative -------------------------------- */
ok(KEYS.some(k => C[k].facts.coast_km_in_window > 5),
   'at least one campus has real coastline in its window, so the pack is '
   + 'drawing something');
ok(KEYS.some(k => !C[k].facts.waterfront),
   'and at least one has none — a dry campus gets no decorative shoreline');
ok(new Set(KEYS.map(k => C[k].mask.land_share)).size >= 7,
   'the ten land shares are not one number repeated: the masks differ');
ok(KEYS.every(k => C[k].mask.rows.length === C[k].mask.n
   && C[k].mask.rows.every(r => r.length === C[k].mask.n / 4
                             && /^[0-9a-f]+$/.test(r))),
   'every mask is n rows of exactly n/4 lowercase hex digits');

console.log(`\n${pass} ok, ${fail} failed`);
process.exit(fail ? 1 : 0);
