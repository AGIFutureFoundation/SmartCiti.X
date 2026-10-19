/**
 * Campus site plan verification (CAMPUSPLAN_CONTRACT v1).
 *
 * Every claim in campusplan/registry/campusplan.json is re-derived here from
 * something the registry did not write: lot counts and order from the union
 * registry AND from the 3D page's own embedded data (D.campuses/D.districts),
 * footprints and clear heights from the page's D.halls, roof styles and the
 * city-layer scale from the page source, the coordinate from the geo
 * registry, the Orleans parish metres from the parishes registry formula.
 * Geometry (overlap, containment, walkway contact, reachability from the
 * gate) is recomputed from the rects, not trusted.
 *
 *   node campusplan/test.mjs
 *   node campusplan/test.mjs --root=/tmp/copy      (mutation runs: a broken copy)
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const hit = args.find((a) => a.startsWith('--root='));
const ROOT = resolve(hit ? hit.slice(7) : join(HERE, '..'));

let n = 0, bad = 0;
const ok = (m, c, evidence = []) => {
  if (c) { n++; console.log('  ok  ' + m); return; }
  bad++;
  console.log('FAIL  ' + m);
  for (const e of evidence.slice(0, 6)) console.log('      ' + e);
};
const read = (rel) => readFileSync(join(ROOT, rel));
const readJSON = (rel) => JSON.parse(read(rel).toString('utf8'));
const sha = (rel) => createHash('sha256').update(read(rel)).digest('hex');

const reg = readJSON('campusplan/registry/campusplan.json');
const campusesReg = readJSON('unions/registry/campuses.json').campuses;
const districtsReg = readJSON('unions/registry/districts.json').districts;
const geo = readJSON('geo/registry/campuses_geo.json');
const parishes = readJSON('parishes/registry/parishes.json');
const page = read('web/trade_craft_3d.html').toString('utf8');
const m = page.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/);
if (!m) { console.log('FAIL  the 3D page carries its data block'); process.exit(1); }
const D = JSON.parse(m[1]);
const hallOf = Object.fromEntries(D.halls.map((h) => [h.slug, h]));
const U = Number(page.match(/const U = (\d+);/)[1]);
const CITY_S = Number(page.match(/const CITY_S = ([\d.]+);/)[1]);
const STYLE_OF = Object.fromEntries([...page.match(/const STYLE_OF = \{([\s\S]*?)\};/)[1]
  .matchAll(/(\w+):\s*'(\w+)'/g)].map((x) => [x[1], x[2]]));
const sortDeep = (v) => (v && typeof v === 'object' && !Array.isArray(v))
  ? Object.fromEntries(Object.keys(v).sort().map((k) => [k, sortDeep(v[k])]))
  : (Array.isArray(v) ? v.map(sortDeep) : v);
const canon = (v) => JSON.stringify(sortDeep(v));
const TIERS = ['RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED', 'SCRIPTED'];
const EPS = 1e-6;
const keys = Object.keys(campusesReg);
const C = reg.campuses;

// ------------------------------------------------------------ geometry --
const bnd = (r) => [r.x - r.w / 2, r.z - r.d / 2, r.x + r.w / 2, r.z + r.d / 2];
const overlap = (a, b) => {
  const [a0, a1, a2, a3] = bnd(a), [b0, b1, b2, b3] = bnd(b);
  return Math.min(a2, b2) - Math.max(a0, b0) > EPS && Math.min(a3, b3) - Math.max(a1, b1) > EPS;
};
const touch = (a, b) => {
  const [a0, a1, a2, a3] = bnd(a), [b0, b1, b2, b3] = bnd(b);
  const ox = Math.min(a2, b2) - Math.max(a0, b0), oz = Math.min(a3, b3) - Math.max(a1, b1);
  return ox >= -EPS && oz >= -EPS && Math.max(ox, oz) > EPS;
};
const inside = (i, o) => {
  const [i0, i1, i2, i3] = bnd(i), [o0, o1, o2, o3] = bnd(o);
  return i0 >= o0 - EPS && i1 >= o1 - EPS && i2 <= o2 + EPS && i3 <= o3 + EPS;
};

// ------------------------------------------------------------- 1 stamp --
ok('pack header: campusplan, CAMPUSPLAN_CONTRACT v1, units m',
  reg.pack === 'campusplan' && reg.contract === 'CAMPUSPLAN_CONTRACT v1' && reg.units === 'm');
{
  // a `part` input (the builder lines campusplan reads) is re-read by the
  // fresh-build check at the bottom; whole files are hashed here
  const stale = reg.inputs.filter((i) => !i.part && sha(i.path).slice(0, 16) !== i.sha256_16);
  const want = createHash('sha256').update(reg.inputs.map((i) => i.path + i.sha256_16).join(''))
    .digest('hex');
  ok('inputs fresh: every input sha256 matches and source_stamp is their digest',
    !stale.length && reg.source_stamp_sha256 === want && reg.source_stamp === want.slice(0, 16)
    && reg.inputs.some((i) => i.path === 'campusplan/build.py'),
    stale.map((i) => `${i.path} changed since the build`));
}

// ------------------------------------------------------------ 2 counts --
{
  const errs = [];
  ok('every campus of the union registry has a plan, and no other',
    JSON.stringify(Object.keys(C).sort()) === JSON.stringify([...keys].sort()));
  for (const k of keys) {
    const want = campusesReg[k].districts.flatMap((d) => districtsReg[d].halls);
    const page3d = D.campuses[k].districts.flatMap((d) => D.districts[d].halls);
    const got = C[k].lots.map((l) => l.hall);
    if (JSON.stringify(got) !== JSON.stringify(want) || JSON.stringify(got) !== JSON.stringify(page3d))
      errs.push(`${k}: ${got.length} lots vs ${want.length} registry / ${page3d.length} page halls`);
    if (reg.counts[k] !== got.length) errs.push(`${k}: counts ${reg.counts[k]} typed != ${got.length}`);
    if (JSON.stringify(C[k].districts) !== JSON.stringify(D.campuses[k].districts))
      errs.push(`${k}: district keys/order differ from the page`);
    if (new Set(got).size !== got.length) errs.push(`${k}: a hall has two lots`);
  }
  ok('lot count == halls per campus in the builder data (registry and page D), same order, one lot each',
    !errs.length, errs);
  const total = keys.reduce((s, k) => s + C[k].lots.length, 0);
  ok(`every union hall on a campus has its own lot (${total} lots)`,
    total === keys.reduce((s, k) => s + D.campuses[k].districts
      .reduce((t, d) => t + D.districts[d].halls.length, 0), 0) && total > 0);
}

// -------------------------------------------------- 3 envelope numbers --
{
  const errs = [];
  for (const k of keys) for (const l of C[k].lots) {
    const h = hallOf[l.hall], b = l.building;
    if (b.d_m !== h.depth * U) errs.push(`${l.id}: d_m ${b.d_m} != page depth ${h.depth} x U ${U}`);
    if (b.w_m !== l.envelope.w * l.envelope.unit_m || l.envelope.unit_m !== U || l.envelope.d !== h.depth)
      errs.push(`${l.id}: envelope ${JSON.stringify(l.envelope)} != page`);
    if (b.height_m !== h.clear || l.clear_height_m !== h.clear)
      errs.push(`${l.id}: height ${b.height_m} != page clear ${h.clear}`);
    if (l.roof_style !== STYLE_OF[l.district]) errs.push(`${l.id}: roof ${l.roof_style} != STYLE_OF`);
    const [aw, ad] = (b.facing === 'E' || b.facing === 'W') ? [b.d_m, b.w_m] : [b.w_m, b.d_m];
    if (b.aabb.w !== aw || b.aabb.d !== ad) errs.push(`${l.id}: aabb not the turned envelope`);
  }
  ok('footprint, clear height and roof style equal the page\'s own D.halls / STYLE_OF (never restated)',
    !errs.length, errs);
}

// ----------------------------------------------------- 4 orientation --
{
  const ROT = { N: 0, S: Math.PI, E: -Math.PI / 2, W: Math.PI / 2 };
  const errs = [];
  for (const k of keys) for (const l of C[k].lots) {
    const b = l.building, [x0, z0, x1, z1] = bnd(b.aabb);
    if (Math.abs(b.rot_y - ROT[b.facing]) > 1e-9) errs.push(`${l.id}: rot_y ${b.rot_y} for ${b.facing}`);
    const want = { N: [b.aabb.x, z0], S: [b.aabb.x, z1], E: [x1, b.aabb.z], W: [x0, b.aabb.z] }[b.facing];
    if (Math.abs(b.door.x - want[0]) > .002 || Math.abs(b.door.z - want[1]) > .002)
      errs.push(`${l.id}: door not on the ${b.facing} face`);
    // the door looks at the walkway it fronts
    const w = C[k].walkways.find((x) => x.id === l.walkway);
    const dir = { N: [0, -1], S: [0, 1], E: [1, 0], W: [-1, 0] }[b.facing];
    if (!w || (w.x - b.aabb.x) * dir[0] + (w.z - b.aabb.z) * dir[1] <= 0)
      errs.push(`${l.id}: door faces away from ${l.walkway}`);
  }
  ok('rot_y matches facing, the door sits on that face and faces the lot\'s walkway', !errs.length, errs);
}

// --------------------------------------------------------- 5 overlaps --
{
  const errs = [];
  for (const k of keys) {
    const p = C[k];
    const parcels = [...p.lots, ...p.parking, p.commons, p.gate, p.sims_yard];
    for (let i = 0; i < parcels.length; i++)
      for (let j = i + 1; j < parcels.length; j++)
        if (overlap(parcels[i], parcels[j])) errs.push(`${k}: ${parcels[i].id} overlaps ${parcels[j].id}`);
    ok(`${k}: no two lots/parcels overlap (${parcels.length} parcels)`, !errs.length, errs);
    errs.length = 0;
    for (const a of parcels) for (const c of [...p.streets, ...p.walkways])
      if (overlap(a, c)) errs.push(`${k}: ${a.id} overlaps ${c.id}`);
    ok(`${k}: no parcel overlaps a street or walkway`, !errs.length, errs);
    errs.length = 0;
    for (const l of p.lots) {
      if (!inside(l.building.aabb, l)) errs.push(`${l.id}: building leaves the lot`);
      if (l.yard && (!inside(l.yard, l) || overlap(l.yard, l.building.aabb)))
        errs.push(`${l.id}: yard leaves the lot or runs under the building`);
      const sb = l.setbacks, [bx0, bz0, bx1, bz1] = bnd(l.building.aabb), [lx0, lz0, lx1, lz1] = bnd(l);
      const front = { N: bz0 - lz0, S: lz1 - bz1, E: lx1 - bx1, W: bx0 - lx0 }[l.building.facing];
      if (Math.abs(front - sb.front) > .002) errs.push(`${l.id}: front setback ${front} != ${sb.front}`);
    }
    ok(`${k}: every building and yard inside its lot, front setback as declared`, !errs.length, errs);
    errs.length = 0;
  }
}

// ------------------------------------------------ 6 walkway + reach --
for (const k of keys) {
  const p = C[k];
  const errs = [];
  for (const l of p.lots) {
    const w = p.walkways.find((x) => x.id === l.walkway);
    if (!w || !touch(l, w)) errs.push(`${l.id}: does not touch ${l.walkway}`);
  }
  ok(`${k}: every lot touches a walkway`, !errs.length, errs);
  // circulation graph from the gate: rects that touch or overlap
  const nodes = [p.gate, p.commons, ...p.streets, ...p.walkways];
  const seen = new Set([0]), todo = [0];
  while (todo.length) {
    const i = todo.pop();
    nodes.forEach((nd, j) => {
      if (!seen.has(j) && (touch(nodes[i], nd) || overlap(nodes[i], nd))) { seen.add(j); todo.push(j); }
    });
  }
  const reach = new Set([...seen].map((i) => nodes[i].id));
  const lost = p.lots.filter((l) => !p.walkways.some((w) => reach.has(w.id) && touch(l, w)));
  const strayP = p.parking.filter((q) => ![...p.streets].some((s) => reach.has(s.id) && touch(q, s)));
  ok(`${k}: every hall reachable from the gate (graph over ${nodes.length} circulation rects)`
    + ` and the commons too`, !lost.length && reach.has('commons') && reach.has('gate'),
  lost.map((l) => `${l.id} unreachable`));
  ok(`${k}: every parking lot opens onto a street reachable from the gate`, !strayP.length,
    strayP.map((q) => q.id));
}

// ------------------------------------------- 6b streets and blocks --
{
  const errs = [];
  for (const k of keys) {
    const p = C[k];
    for (const l of p.lots) {
      const st = p.streets.find((x) => x.id === l.street);
      const w = p.walkways.find((x) => x.id === l.walkway);
      if (!st || !w || !touch(st, w)) errs.push(`${l.id}: street ${l.street} missing or not beside ${l.walkway}`);
      const blk = p.districts_plan.find((x) => x.key === l.district);
      if (!blk || !inside(l, blk.block)) errs.push(`${l.id}: outside the ${l.district} block`);
    }
    const slots = p.districts_plan.map((x) => x.key).join();
    if (slots !== p.districts.join()) errs.push(`${k}: district blocks not in registry order`);
  }
  ok('every lot sits in its own district block and fronts a walkway that runs beside its named street',
    !errs.length, errs);
}

// ------------------------------------------------ 7 heavy-trade yards --
{
  const words = reg.rules.yard_words.map((w) => w.toLowerCase());
  const errs = [];
  let yards = 0;
  for (const k of keys) for (const l of C[k].lots) {
    const h = hallOf[l.hall];
    const text = [...Object.values(h.fixtures).flat(), h.name, h.focus].join(' | ').toLowerCase();
    const want = words.find((w) => text.includes(w)) ?? null;
    const got = l.yard ? l.yard.because.toLowerCase() : null;
    if (want !== got) errs.push(`${l.id}: yard because ${got} but the rule gives ${want}`);
    if (l.yard) yards++;
  }
  ok(`outdoor training yards exactly where rules.yard_words meet the hall's own fixtures (${yards} yards)`,
    !errs.length && yards > 0, errs);
  const heavy = ['crane-ops', 'ironworkers', 'operating-eng'];
  ok('crane operators, ironworkers and operating engineers each have a yard',
    heavy.every((s) => keys.some((k) => C[k].lots.some((l) => l.hall === s && l.yard))));
}

// ---------------------------------------------------- 8 provenance tags --
{
  const errs = [];
  const tagged = (v) => typeof v === 'string' && TIERS.some((t) => v.startsWith(t));
  for (const k of keys) {
    const p = C[k];
    for (const l of p.lots) for (const f of ['footprint', 'height', 'roof_style', 'position', 'setbacks', 'yard'])
      if (!tagged(l.prov[f])) errs.push(`${l.id}: prov.${f} = ${l.prov[f]}`);
    for (const l of p.lots) {
      if (!l.prov.footprint.startsWith('DERIVED') || !l.prov.height.startsWith('DERIVED'))
        errs.push(`${l.id}: footprint/height must be DERIVED`);
      if (!l.prov.position.startsWith('AUTHORED')) errs.push(`${l.id}: position must be AUTHORED`);
    }
    for (const f of ['layout', 'gate', 'commons', 'parking', 'streets', 'walkways', 'sims_yard'])
      if (!tagged(p.prov[f])) errs.push(`${k}: prov.${f}`);
    for (const d of p.districts_plan) if (!tagged(d.prov)) errs.push(`${k}/${d.key}: prov`);
    const pl = p.placement;
    if (!tagged(pl.city_layer.prov)) errs.push(`${k}: city_layer.prov`);
    if (pl.parish && !tagged(pl.parish.prov)) errs.push(`${k}: parish.prov`);
  }
  ok('provenance: every lot field, layout piece and placement carries a tier tag;'
    + ' footprint/height DERIVED, positions AUTHORED', !errs.length, errs);
  ok('rules are AUTHORED and copied verbatim from campusplan/authored/rules.json',
    canon(reg.rules) === canon(readJSON('campusplan/authored/rules.json'))
    && reg.rules.provenance.startsWith('AUTHORED'));
}

// ----------------------------------------------------- 9 placement --
{
  const errs = [];
  for (const k of keys) {
    const g = geo.campuses[k], pl = C[k].placement;
    for (const f of ['lat', 'lng', 'provenance', 'source'])
      if (pl.geo[f] !== g[f]) errs.push(`${k}: geo.${f} ${pl.geo[f]} != registry ${g[f]}`);
    const cl = pl.city_layer;
    if (cl.x !== 0 || cl.z !== 0 || cl.rot_y !== 0 || cl.units_per_km !== CITY_S)
      errs.push(`${k}: city layer origin/scale`);
    if (cl.log_radial !== geo.anchors[k].some((a) => a.km > 15)) errs.push(`${k}: log_radial`);
    if (cl.anchors.length !== geo.anchors[k].length) errs.push(`${k}: anchors`);
    if (k !== 'new-orleans' && pl.parish !== null) errs.push(`${k}: parish placement outside Louisiana`);
  }
  ok('placement.geo is the geo registry\'s coordinate and its OWN provenance tag, copied; city layer at the'
    + ' campus origin at the page\'s CITY_S', !errs.length, errs);
  const pp = C['new-orleans'].placement.parish;
  const fr = parishes.frames, orl = parishes.parishes['22071'];
  const ltp = (lat, lng, o) => [fr.R_m * Math.cos(lat0(o)) * rad(lng - o.lng), fr.R_m * rad(lat - o.lat)];
  function rad(v) { return v * Math.PI / 180; }
  function lat0(o) { return rad(o.lat); }
  const g = geo.campuses['new-orleans'];
  const [le, ln] = ltp(g.lat, g.lng, orl.frame.origin);
  const [we, wn] = ltp(g.lat, g.lng, fr.world.origin);
  ok('new-orleans: Orleans parish (22071) local and world metres re-derived from the parishes ltp_formula',
    pp && pp.fips === '22071' && Math.abs(pp.local_m[0] - le) < .01 && Math.abs(pp.local_m[1] - ln) < .01
    && Math.abs(pp.scene.x - le) < .01 && Math.abs(pp.scene.z + ln) < .01
    && Math.abs(pp.world_m[0] - we) < .01 && Math.abs(pp.world_m[1] - wn) < .01
    && Math.abs(pp.world_scene.z + wn) < .01 && pp.rot_y === 0,
  [JSON.stringify(pp && pp.local_m), `want ${le.toFixed(3)}, ${ln.toFixed(3)}`]);
  // local + origin_in_world_m == world (the parishes registry's own relation, loosely: LTP is per-origin)
  const ow = orl.frame.origin_in_world_m;
  ok('new-orleans: the campus point lies inside the Orleans outline, and local + origin_in_world is within'
    + ' 0.5% of world', pp.inside_outline === true
    && Math.hypot(le + ow[0] - we, ln + ow[1] - wn) < .005 * Math.hypot(we, wn) + 50);
}

// ---------------------------------------------------------- 10 site --
{
  const errs = [];
  for (const k of keys) {
    const p = C[k], s = p.site;
    const all = [...p.lots, ...p.parking, ...p.streets, ...p.walkways, p.commons, p.gate, p.sims_yard];
    const bx = all.map(bnd);
    const x0 = Math.min(...bx.map((b) => b[0])), z0 = Math.min(...bx.map((b) => b[1]));
    const x1 = Math.max(...bx.map((b) => b[2])), z1 = Math.max(...bx.map((b) => b[3]));
    const r = Math.max(...[x0, x1].flatMap((x) => [z0, z1].map((z) => Math.hypot(x, z))));
    if (Math.abs(s.x0 - x0) > .002 || Math.abs(s.z1 - z1) > .002 || Math.abs(s.radius_m - r) > .002)
      errs.push(`${k}: site bbox/radius not the extent of its pieces`);
    const reach = Math.max(...bx.flatMap((b) => [[b[0], b[1]], [b[0], b[3]], [b[2], b[1]], [b[2], b[3]]]
      .map(([x, z]) => Math.hypot(x, z))));
    if (Math.abs(s.reach_m - reach) > .002 || s.reach_m > s.radius_m + EPS)
      errs.push(`${k}: reach_m ${s.reach_m} is not the farthest laid-out corner ${reach.toFixed(3)}`);
    const Rb = p.districts.length === 2 ? reg.builder.campus_R[0] : reg.builder.campus_R[1];
    if (s.builder.campus_R_m !== Rb || s.fits_builder_radius !== (r <= Rb + reg.builder.walk_pad_m))
      errs.push(`${k}: builder radius comparison`);
    const gb = bnd(p.gate);
    if (Math.abs(gb[3] - z1) > .002) errs.push(`${k}: the gate is not on the site's south edge`);
    if (Math.abs(p.commons.x) > EPS || Math.abs(p.commons.z) > EPS) errs.push(`${k}: commons off origin`);
  }
  ok('site bbox, radius and reach are the extent of the plan; the gate is on the south edge; commons at origin;'
    + ' fits_builder_radius honest', !errs.length, errs);
  const pageR = page.match(/const R = dk\.length === 2 \? (\d+) : (\d+);/);
  ok('builder campus R read from the page matches the registry\'s builder block',
    pageR && Number(pageR[1]) === reg.builder.campus_R[0] && Number(pageR[2]) === reg.builder.campus_R[1]);
}

// ------------------------------------------------- 11 builder facts --
{
  const yr = Number(page.match(/const YR = Math\.min\((\d+), Math\.max/)[1]);
  const bad2 = keys.filter((k) => C[k].sims_yard.w !== 2 * yr || C[k].sims_yard.d !== 2 * yr);
  ok('the reserved sims-yard parcel is 2 x the page\'s own maximum yard radius', !bad2.length, bad2);
}
{
  let fresh = '';
  try {
    fresh = execFileSync('python3', [join(ROOT, 'campusplan/build.py'), '--stdout'],
      { cwd: ROOT, maxBuffer: 64 << 20 }).toString('utf8');
  } catch (e) { fresh = 'build failed: ' + String(e.stderr || e).slice(0, 200); }
  ok('deterministic: a fresh build equals the shipped registry byte for byte',
    fresh === read('campusplan/registry/campusplan.json').toString('utf8'), [fresh.slice(0, 120)]);
}

if (bad) {
  console.log(`campusplan/test: ${bad} FAILED, ${n} passed`);
  process.exit(1);
}
console.log(`campusplan/test: ${n} checks passed — ${keys.length} campuses, `
  + `${keys.reduce((s, k) => s + C[k].lots.length, 0)} hall lots`);
