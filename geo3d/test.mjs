/**
 * geo3d verification: the 3D campus layout on the Earth, held to the
 * registries and to the 3D page's own data.
 *
 *   [registry]  geo3d/registry/geo3d.json against the registries it reads
 *   [mirror]    the layout recomputed HERE, in JavaScript, from the site
 *               plan the 3D page itself embeds (web/trade_craft_3d.html
 *               D.campusplan lots: w_m x d_m turned by rot_y about the lot
 *               building centre) - an independent second implementation,
 *               agreeing to <= 0.01 m (LAYOUT_CONTRACT v2)
 *   [plan]      every hall footprint IS its campusplan/registry lot's
 *               building footprint, every district outline its block
 *   [geometry]  closed rings, no overlap within a district, the projection
 *               formula re-applied to every corner
 *
 *   node geo3d/test.mjs
 *   node geo3d/test.mjs --root=<sandbox copy of the repo>   (mutation tests)
 */
import { createHash } from 'node:crypto';
import { readFileSync, existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const rootArg = process.argv.slice(2).find((a) => a.startsWith('--root='));
const ROOT = resolve(rootArg ? rootArg.slice(7) : join(HERE, '..'));
let n = 0, failed = 0;
const ok = (m, c) => { if (c) { n++; console.log('  ok ', m); } else { failed++; console.error(`FAIL ${m}`); } };
function need(o, k, where) {
  if (o === null || typeof o !== 'object' || !(k in o)) throw new Error(`geo3d/test: ${where} has no field '${k}'`);
  return o[k];
}
const rd = (p) => readFileSync(join(ROOT, p));
const js = (p) => JSON.parse(rd(p).toString('utf8'));

const reg = js('geo3d/registry/geo3d.json');
const campuses = need(js('unions/registry/campuses.json'), 'campuses', 'campuses.json');
const districts = need(js('unions/registry/districts.json'), 'districts', 'districts.json');
const halls = need(js('pack/registry/halls.json'), 'halls', 'halls.json');
const geo = need(js('geo/registry/campuses_geo.json'), 'campuses', 'campuses_geo.json');
const G = need(reg, 'campuses', 'geo3d.json');

/* ------------------------------------------------------------- stamps --- */
ok('[registry] source_stamp is sha256(geo3d/build.py)[:16]',
  reg.source_stamp === createHash('sha256').update(rd('geo3d/build.py')).digest('hex').slice(0, 16));
const inH = createHash('sha256');
for (const p of need(reg, 'inputs', 'geo3d.json')) inH.update(rd(p));
const b3d = rd('web/build_3d.py').toString('utf8');
const styleBlock = b3d.match(/const STYLE_OF = \{([\s\S]*?)\};/);
ok('[registry] web/build_3d.py still carries the `const STYLE_OF = {...};` block the rooflines are read from', styleBlock !== null);
inH.update(Buffer.from(styleBlock[0], 'utf8'));
ok('[registry] inputs_stamp is sha256 over every input registry and module, in listed order, plus the STYLE_OF block (a registry edit without a rebuild fails here)',
  reg.inputs_stamp === inH.digest('hex').slice(0, 16));
ok('[registry] inputs name the five registries (campusplan\'s site plans included) and two modules the layout reads',
  JSON.stringify(reg.inputs) === JSON.stringify(['unions/registry/campuses.json', 'unions/registry/districts.json',
    'pack/registry/halls.json', 'geo/registry/campuses_geo.json', 'web/interiors.py', 'web/mapdata.py',
    'campusplan/registry/campusplan.json']));

/* ------------------------------------------------------------ honesty --- */
ok('[registry] provenance is SCHEMATIC and the placement sentence says north-up, no heading or survey, 3D-campus scale',
  reg.provenance === 'SCHEMATIC' && reg.placement === 'SCHEMATIC: north-up about the campus centroid; no heading or site survey is recorded; scale as drawn in the 3D campus');
ok('[registry] the projection formula is stated (local tangent plane, R = 6371008.8 m, north = -Z)',
  /R = 6371008\.8 m/.test(reg.projection) && /north_m = -z/.test(reg.projection));
const builder = rd('geo3d/build.py').toString('utf8');
ok('[generator] geo3d/build.py fails closed: no `.get(` and no `??` on registry data',
  !/\.get\(/.test(builder) && !builder.includes('??'));

/* ------------------------------------------------------------- counts --- */
const withHalls = Object.keys(campuses).filter((k) => campuses[k].halls.length > 0);
ok(`[registry] one entry per campus of unions/registry/campuses.json (${Object.keys(campuses).length})`,
  JSON.stringify(Object.keys(G).sort()) === JSON.stringify(Object.keys(campuses).sort()));
ok(`[registry] counts recomputed: ${withHalls.length} campuses with halls, ${Object.keys(campuses).length - withHalls.length} without`,
  reg.counts.campuses === Object.keys(campuses).length && reg.counts.campuses_with_halls === withHalls.length
  && reg.counts.campuses_without_halls === Object.keys(campuses).length - withHalls.length);
const allPlaced = Object.values(G).flatMap((c) => c.halls.map((h) => h.slug));
const allListed = Object.values(campuses).flatMap((c) => c.halls);
ok(`[registry] every hall a campus lists is placed exactly once (${allListed.length}), and nothing else is placed`,
  allPlaced.length === allListed.length && new Set(allPlaced).size === allPlaced.length
  && JSON.stringify([...allPlaced].sort()) === JSON.stringify([...allListed].sort())
  && reg.counts.halls === allPlaced.length);
ok('[registry] district count recomputed from the campuses\' own district lists',
  reg.counts.districts === Object.values(campuses).reduce((a, c) => a + c.districts.length, 0));
for (const k of Object.keys(campuses).filter((x) => !withHalls.includes(x)))
  ok(`[registry] ${k}: no halls in the registry -> no district, no building, and a note saying none is invented`,
    G[k].halls.length === 0 && G[k].districts.length === 0 && G[k].halls_count === 0
    && /no building is invented/.test(need(G[k], 'note', `geo3d ${k}`)));
for (const k of withHalls)
  ok(`[registry] ${k}: centroid is geo/registry/campuses_geo.json's own point`,
    G[k].centroid.lat === geo[k].lat && G[k].centroid.lng === geo[k].lng && G[k].centroid.provenance === geo[k].provenance);

/* ------------------------------------------------------- the JS mirror --- */
const page3d = rd('web/trade_craft_3d.html').toString('utf8');
const m = page3d.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/);
ok('[mirror] web/trade_craft_3d.html embeds its data JSON', m !== null);
const D = JSON.parse(m[1]);
const STYLE = Object.fromEntries([...styleBlock[1].matchAll(/(\w+):\s*'(\w+)'/g)].map((x) => [x[1], x[2]]));
ok('[mirror] the page embeds the campus site plan it builds from (D.campusplan, one lot per hall of every hall campus)',
  withHalls.every((k) => D.campusplan && D.campusplan[k] && D.campusplan[k].lots.length === campuses[k].halls.length));
let worst = 0, compared = 0;
const expect = {};
for (const key of withHalls) {
  for (const lot of D.campusplan[key].lots) {
    const b = lot.b, h = D.halls.find((x) => x.slug === lot.hall);
    // the building's own w_m x d_m box turned by rot_y (three.js rotation.y) about its centre
    const c = Math.cos(b.rot_y), s2 = Math.sin(b.rot_y);
    const ex = Math.abs(b.w_m / 2 * c) + Math.abs(b.d_m / 2 * s2), ez = Math.abs(b.w_m / 2 * s2) + Math.abs(b.d_m / 2 * c);
    expect[lot.hall] = { key, district: lot.district, x: b.x, z: b.z, x0: b.x - ex, x1: b.x + ex, z0: b.z - ez, z1: b.z + ez,
      w: 36, d: h.depth * 3, h: h.clear + .35, rot: b.rot_y, roof: STYLE[lot.district] };
  }
}
const tol = 0.01;
const bad = [];
for (const [k, c] of Object.entries(G)) {
  for (const h of c.halls) {
    const e = expect[h.slug];
    const xs = h.corners_m.map((q) => q[0]), zs = h.corners_m.map((q) => q[1]);
    const dd = e && e.key === k && e.district === h.district && e.roof === h.roof
      ? Math.max(Math.hypot(e.x - h.x, e.z - h.z), Math.abs(e.w - h.w), Math.abs(e.d - h.d), Math.abs(e.h - h.h),
        Math.abs(e.rot - h.rot) * 200, Math.abs(Math.min(...xs) - e.x0), Math.abs(Math.max(...xs) - e.x1),
        Math.abs(Math.min(...zs) - e.z0), Math.abs(Math.max(...zs) - e.z1))
      : Infinity;
    worst = Math.max(worst, dd); compared++;
    if (!(dd <= tol)) bad.push(h.slug);
  }
}
ok(`[mirror] every hall centre, footprint corners (36 x 3*depth m turned by its facing), wall height (clear + .35 slab), facing and roofline agrees with the site plan the 3D page embeds to <= ${tol} m (${compared} compared, worst ${worst.toExponential(2)} m${bad.length ? '; off: ' + bad.slice(0, 5).join(', ') : ''})`,
  bad.length === 0 && compared === reg.counts.halls);

/* ----------------------------------------------- the plan's own lots --- */
const CP = need(js('campusplan/registry/campusplan.json'), 'campuses', 'campusplan.json');
const lotOff = [];
let lotN = 0;
for (const key of withHalls) {
  const lots = need(need(CP, key, 'campusplan'), 'lots', `campusplan ${key}`);
  const byHall = Object.fromEntries(G[key].halls.map((h) => [h.slug, h]));
  if (lots.length !== G[key].halls.length) lotOff.push(`${key}: ${lots.length} lots vs ${G[key].halls.length} halls`);
  for (const l of lots) {
    const h = byHall[l.hall], a = l.building.aabb; lotN++;
    const want = [[a.x - a.w / 2, a.z - a.d / 2], [a.x + a.w / 2, a.z - a.d / 2], [a.x + a.w / 2, a.z + a.d / 2], [a.x - a.w / 2, a.z + a.d / 2]];
    const same = h && h.lot === l.id && h.district === l.district
      && h.corners_m.every(([x, z], i) => Math.abs(x - want[i][0]) <= 1e-3 && Math.abs(z - want[i][1]) <= 1e-3)
      && Math.abs(h.x - l.building.x) <= 1e-9 && Math.abs(h.z - l.building.z) <= 1e-9
      && h.door.x === l.building.door.x && h.door.z === l.building.door.z && h.facing === l.building.facing;
    if (!same) lotOff.push(l.hall);
  }
}
ok(`[plan] every globe hall footprint is its campusplan/registry/campusplan.json lot building (aabb corners, centre, door, facing, lot id; ${lotN} lots)${lotOff.length ? ' - off: ' + lotOff.slice(0, 5).join(', ') : ''}`,
  lotOff.length === 0 && lotN === reg.counts.halls);
const blkOff = [];
for (const key of withHalls) for (const d of G[key].districts) {
  const dp = CP[key].districts_plan.find((x) => x.key === d.key);
  const b = dp && dp.block;
  const xs = d.corners_m.map((q) => q[0]), zs = d.corners_m.map((q) => q[1]);
  if (!b || Math.abs(Math.min(...xs) - (b.x - b.w / 2)) > 1e-3 || Math.abs(Math.max(...xs) - (b.x + b.w / 2)) > 1e-3
    || Math.abs(Math.min(...zs) - (b.z - b.d / 2)) > 1e-3 || Math.abs(Math.max(...zs) - (b.z + b.d / 2)) > 1e-3) blkOff.push(`${key}/${d.key}`);
}
ok(`[plan] every globe district outline is its campusplan districts_plan block${blkOff.length ? ' - off: ' + blkOff.join(', ') : ''}`,
  blkOff.length === 0 && reg.counts.districts === withHalls.reduce((n2, k) => n2 + CP[k].districts_plan.length, 0));
ok('[plan] each hall footprint sits inside its own district block and inside the campus site',
  withHalls.every((k) => G[k].halls.every((h) => {
    const b = CP[k].districts_plan.find((x) => x.key === h.district).block, st = CP[k].site;
    return h.corners_m.every(([x, z]) => x >= b.x - b.w / 2 - 1e-6 && x <= b.x + b.w / 2 + 1e-6 && z >= b.z - b.d / 2 - 1e-6
      && z <= b.z + b.d / 2 + 1e-6 && x >= st.x0 - 1e-6 && x <= st.x1 + 1e-6 && z >= st.z0 - 1e-6 && z <= st.z1 + 1e-6);
  })));

/* ------------------------------------------------------------ geometry --- */
const RE = 6371008.8, rad = (x) => x * Math.PI / 180, deg = (x) => x * 180 / Math.PI;
let ringsOk = true, projWorst = 0;
for (const [k, c] of Object.entries(G)) {
  for (const f of [...c.halls, ...c.districts]) {
    const p = f.polygon;
    if (!(p.length === 5 && p[0][0] === p[4][0] && p[0][1] === p[4][1])) ringsOk = false;
    f.corners_m.forEach(([x, z], i) => {
      const lat = c.centroid.lat + deg(-z / RE);
      const lng = c.centroid.lng + deg(x / (RE * Math.cos(rad(c.centroid.lat))));
      const dm = Math.hypot((lng - p[i][0]) * RE * Math.cos(rad(c.centroid.lat)) * Math.PI / 180, (lat - p[i][1]) * RE * Math.PI / 180);
      projWorst = Math.max(projWorst, dm);
    });
  }
}
ok('[geometry] every hall and district polygon is a closed 4-corner ring (5 positions, first == last)', ringsOk);
ok(`[geometry] every polygon corner is its scene corner re-projected by the stated formula (worst ${projWorst.toExponential(2)} m <= 0.01 m)`, projWorst <= 0.01);
// separating-axis test for two convex quads (scene metres)
function overlap(a, b) {
  for (const poly of [a, b]) for (let i = 0; i < 4; i++) {
    const [x1, z1] = poly[i], [x2, z2] = poly[(i + 1) % 4];
    const nx = z2 - z1, nz = x1 - x2;
    const pa = a.map(([x, z]) => x * nx + z * nz), pb = b.map(([x, z]) => x * nx + z * nz);
    if (Math.max(...pa) <= Math.min(...pb) + 1e-9 || Math.max(...pb) <= Math.min(...pa) + 1e-9) return false;
  }
  return true;
}
const overlaps = [];
for (const c of Object.values(G)) for (const d of c.districts) {
  const hs = c.halls.filter((h) => h.district === d.key);
  for (let i = 0; i < hs.length; i++) for (let j = i + 1; j < hs.length; j++)
    if (overlap(hs[i].corners_m, hs[j].corners_m)) overlaps.push(`${hs[i].slug}/${hs[j].slug}`);
}
ok(`[geometry] no two hall footprints overlap within a district${overlaps.length ? ' (' + overlaps.slice(0, 4).join(', ') + ')' : ''}`, overlaps.length === 0);
const distOver = [];
for (const [k, c] of Object.entries(G)) for (let i = 0; i < c.districts.length; i++)
  for (let j = i + 1; j < c.districts.length; j++)
    if (overlap(c.districts[i].corners_m, c.districts[j].corners_m)) distOver.push(`${k}:${c.districts[i].key}/${c.districts[j].key}`);
ok(`[geometry] no two district outlines on a campus overlap${distOver.length ? ' (' + distOver.join(', ') + ')' : ''}`, distOver.length === 0);
ok('[geometry] every hall has a positive height and the walkable interior\'s own 36 x 3*depth m footprint',
  Object.values(G).every((c) => c.halls.every((h) => h.h > 0 && h.w === 36 && h.d === h.depth_units * 3 && h.d >= 5)));
ok('[registry] the placement says the site plan is AUTHORED and the archetype roof is not mirrored (top is the wall box)',
  /AUTHORED/.test(reg.honesty.site_plan) && /not mirrored/.test(reg.mirrors)
  && Object.values(G).every((c) => c.halls.every((h) => h.top === h.h)));
ok('[registry] each hall\'s district lists it, and its name is pack/registry/halls.json\'s own',
  Object.values(G).every((c) => c.halls.every((h) => districts[h.district].halls.includes(h.slug)
    && halls.find((x) => x.slug === h.slug).name === h.name)));

if (failed) { console.error(`FAIL geo3d/test: ${failed} of ${n + failed} checks failed`); process.exit(1); }
console.log(`geo3d/test: ${n} checks passed`);
