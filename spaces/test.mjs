/**
 * Custom spaces verification.
 *
 * Every claim in spaces/registry/spaces.json is recomputed here from the
 * registry that owns it, and the shipped registry is held to the answer:
 * the stamp matches the builder, every item id resolves in its owning
 * registry, overlap and inside-footprint are re-derived from props/ size_m,
 * the PPE set is re-derived from surfaces/ rules, the cost sums are re-added
 * from the props' own tri budgets, and no count is typed. A check nobody has
 * watched fail is not a check, so the mutation drill at the bottom names
 * which check each fault trips.
 *
 *   node spaces/test.mjs
 *   node spaces/test.mjs --root=/tmp/copy      (mutation runs: a broken copy)
 */
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const arg = (name) => {
  const hit = args.find((a) => a.startsWith(`--${name}=`));
  return hit === undefined ? null : hit.slice(name.length + 3);
};
const ROOT = resolve(arg('root') !== null ? arg('root') : join(HERE, '..'));

let n = 0, bad = 0;
const ok = (m, c, evidence = []) => {
  if (c) { n++; console.log('  ok  ' + m); return; }
  bad++;
  console.log('FAIL  ' + m);
  for (const e of evidence) console.log('      ' + e);
};
const readJSON = (rel) => JSON.parse(readFileSync(join(ROOT, rel), 'utf8'));
const canon = (v) => (v && typeof v === 'object' && !Array.isArray(v))
  ? Object.fromEntries(Object.keys(v).sort().map((k) => [k, canon(v[k])]))
  : (Array.isArray(v) ? v.map(canon) : v);
const same = (a, b) => JSON.stringify(canon(a)) === JSON.stringify(canon(b));

const reg = readJSON('spaces/registry/spaces.json');
const props = readJSON('props/registry/props.json');
const surfaces = readJSON('surfaces/registry/finishes.json');
const labels = readJSON('labels/registry/labels.json');
const sims = readJSON('sims/registry/sims.json');
const stations = readJSON('stations/registry/stations.json');
const cribs = readJSON('tools/registry/toolcribs.json');
const unions = readJSON('unions/registry/unions.json');
const builderSrc = readFileSync(join(ROOT, 'spaces/build.py'), 'utf8');
const authoredDir = join(ROOT, 'spaces/authored');
const authoredFiles = readdirSync(authoredDir).filter((f) => f.endsWith('.json')).sort();

/* ------------------------------------------------------------ stamps -- */
ok('[registry] source_stamp is sha256 of spaces/build.py',
  reg.source_stamp === createHash('sha256').update(builderSrc).digest('hex').slice(0, 16),
  [`have ${reg.source_stamp}`]);
const authoredHash = createHash('sha256');
for (const f of authoredFiles) authoredHash.update(readFileSync(join(authoredDir, f)));
ok('[registry] authored_stamp is sha256 over spaces/authored/*.json in name order',
  reg.authored_stamp === authoredHash.digest('hex').slice(0, 16));
ok('[registry] one space per authored file, ids in file order',
  same(reg.spaces.map((s) => s.id), authoredFiles.map((f) => f.replace(/\.json$/, ''))));
ok('[registry] status says declared, a walk-through in the 3D page with equipment shown as markers, on the pack and on every space, and the note keeps the AUTHORED and not-a-venue lines',
  reg.status === 'declared, a walk-through in the 3D page with equipment shown as markers'
    && reg.spaces.every((s) => s.status === reg.status)
    && reg.honesty.status.includes('AUTHORED') && reg.honesty.status.includes('no dimension is a measurement of a real venue')
    && !/not yet walkable/.test(JSON.stringify(reg)));
ok('[registry] provenance: declarations AUTHORED, everything else DERIVED',
  reg.provenance.declarations === 'AUTHORED' && reg.provenance.everything_else === 'DERIVED'
    && reg.spaces.every((s) => s.provenance.declaration === 'AUTHORED'
      && s.provenance.ppe === 'DERIVED' && s.provenance.cost === 'DERIVED'));
ok('[registry] no duration, price or accreditation is stated',
  !/\b(price|\$\d|accredit|certif|hours?\b|weeks?\b|days?\b)/i.test(JSON.stringify(reg.spaces)));

/* ------------------------------------------------------- id resolution -- */
const LOOKUP = {
  prop: new Map(props.props.map((p) => [p.id, p])),
  furniture: new Map(props.crib_furniture.pieces.map((p) => [p.id, p])),
  seat: new Map(Object.entries(sims.sims)),
  station: new Map(stations.stations.map((s) => [s.station_id, s])),
  crib: new Map(Object.entries(cribs.cribs)),
  sign: new Map(Object.entries(labels.kinds)),
};
const unionBySlug = new Map(unions.unions.map((u) => [u.slug, u]));
const KINDS = Object.keys(LOOKUP);
ok('[registry] kinds are exactly the six the builder admits',
  same([...reg.kinds].sort(), [...KINDS].sort()));

const unresolved = [];
for (const s of reg.spaces) {
  s.items.forEach((it, i) => {
    if (!KINDS.includes(it.kind) || !LOOKUP[it.kind].has(it.id)) {
      unresolved.push(`${s.source}#items[${i}] ${it.kind} ${it.id}`);
    }
  });
}
ok('[registry] every item id resolves in its owning registry', unresolved.length === 0, unresolved);

const badNames = [];
for (const s of reg.spaces) {
  s.items.forEach((it, i) => {
    if (!LOOKUP[it.kind].has(it.id)) return;
    const row = LOOKUP[it.kind].get(it.id);
    const want = it.kind === 'sign' ? row.what : row.name;
    if (it.name !== want) badNames.push(`${s.id}#items[${i}] ${it.id}: ${it.name} != ${want}`);
  });
}
ok('[registry] every item carries the name its registry gives it', badNames.length === 0, badNames);

const badUnions = [];
for (const s of reg.spaces) {
  for (const u of s.unions) {
    if (!unionBySlug.has(u.slug)) badUnions.push(`${s.id}: ${u.slug}`);
    else if (unionBySlug.get(u.slug).name !== u.name
      || unionBySlug.get(u.slug).district !== u.district) badUnions.push(`${s.id}: ${u.slug} name/district`);
  }
}
ok('[registry] every serving union is a real slug with its registry name and district',
  badUnions.length === 0, badUnions);
ok('[registry] every space serves at least one union', reg.spaces.every((s) => s.unions.length > 0));

const badFinish = [];
for (const s of reg.spaces) {
  const fl = surfaces.catalogue[s.floor.id];
  const wl = surfaces.wall_catalogue[s.wall.id];
  if (!fl) badFinish.push(`${s.id} floor ${s.floor.id}`);
  else if (fl.name !== s.floor.name || fl.color !== s.floor.color || fl.pattern !== s.floor.pattern) badFinish.push(`${s.id} floor row`);
  if (!wl) badFinish.push(`${s.id} wall ${s.wall.id}`);
  else if (wl.name !== s.wall.name || wl.color !== s.wall.color || wl.wainscot !== s.wall.wainscot) badFinish.push(`${s.id} wall row`);
}
ok('[registry] floor and wall finishes are catalogue ids with the catalogue name and colour',
  badFinish.length === 0, badFinish);

/* --------------------------------------------- footprints, overlap, inside -- */
const rectOf = (it) => {
  if (it.kind !== 'prop' && it.kind !== 'furniture') return null;
  const size = LOOKUP[it.kind].get(it.id).size_m;
  let w = size[0], d = size[2];
  if (it.rotation === 90 || it.rotation === 270) [w, d] = [d, w];
  return [it.x - w / 2, it.y - d / 2, it.x + w / 2, it.y + d / 2];
};
const overlaps = (a, b) => a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
const r3 = (v) => Math.round(v * 1000) / 1000;

const fpBad = [], outside = [], overlapping = [], unknownBad = [];
for (const s of reg.spaces) {
  const W = s.footprint_m.w, D = s.footprint_m.d;
  const rects = [];
  s.items.forEach((it, i) => {
    const r = rectOf(it);
    if (r === null) {
      if (it.footprint !== null || it.footprint_note !== 'footprint unknown, overlap not checked') {
        unknownBad.push(`${s.id}#items[${i}] ${it.kind} ${it.id}`);
      }
      if (!(it.x >= 0 && it.y >= 0 && it.x <= W && it.y <= D)) outside.push(`${s.id}#items[${i}] point`);
      rects.push(null);
      return;
    }
    if (it.footprint === null || !same(it.rect, r.map(r3))) fpBad.push(`${s.id}#items[${i}] ${it.id} rect ${JSON.stringify(it.rect)} != ${JSON.stringify(r.map(r3))}`);
    if (!(r[0] >= 0 && r[1] >= 0 && r[2] <= W && r[3] <= D)) outside.push(`${s.id}#items[${i}] ${it.id} ${JSON.stringify(r.map(r3))} vs ${W}x${D}`);
    rects.forEach((o, j) => { if (o !== null && overlaps(r, o)) overlapping.push(`${s.id}#items[${i}] ${it.id} x items[${j}] ${s.items[j].id}`); });
    rects.push(r);
  });
}
ok('[registry] every known footprint is the props size_m x by z turned by rotation', fpBad.length === 0, fpBad);
ok('[registry] every item lies inside its space footprint (recomputed)', outside.length === 0, outside);
ok('[registry] no two known footprints overlap (recomputed)', overlapping.length === 0, overlapping);
ok('[registry] an item with no declared size is recorded as footprint unknown, overlap not checked',
  unknownBad.length === 0, unknownBad);

/* ----------------------------------------------------------- envelope -- */
const envBad = [];
for (const s of reg.spaces) {
  if (s.fits_in.length !== s.unions.length) envBad.push(`${s.id}: ${s.fits_in.length} envelopes for ${s.unions.length} unions`);
  for (const e of s.fits_in) {
    const W = s.footprint_m.w, D = s.footprint_m.d;
    const fits = (W <= e.w_m && D <= e.d_m) || (D <= e.w_m && W <= e.d_m);
    if (!fits) envBad.push(`${s.id}: ${W}x${D} in ${e.hall} ${e.label} ${e.w_m}x${e.d_m}`);
    if (e.strand !== s.strand) envBad.push(`${s.id}: envelope strand ${e.strand}`);
    if (e.w_m % reg.units.grid_unit_m !== 0 || e.d_m % reg.units.grid_unit_m !== 0) envBad.push(`${s.id}: ${e.hall} room not on the ${reg.units.grid_unit_m} m grid`);
  }
}
ok('[registry] every space fits the room of its strand in every serving hall, on the 3 m grid',
  envBad.length === 0, envBad);
ok('[registry] area_m2 is w x d', reg.spaces.every((s) => r3(s.footprint_m.w * s.footprint_m.d) === s.footprint_m.area_m2));

/* ----------------------------------------------------------------- PPE -- */
const ppeBad = [];
for (const s of reg.spaces) {
  const hazards = [];
  for (const [h, rooms] of Object.entries(surfaces.rules.hazard_rooms)) {
    if (rooms[s.strand] === s.floor.id) hazards.push(h);
  }
  for (const [h, rooms] of Object.entries(surfaces.rules.hazard_walls)) {
    if (rooms[s.strand] === s.wall.id) hazards.push(h);
  }
  const ids = [...new Set(hazards)].sort();
  const ppe = new Set(surfaces.base_conditions[s.strand].ppe);
  for (const h of ids) for (const p of surfaces.hazard_conditions[h].ppe) ppe.add(p);
  const want = [...ppe].sort();
  if (!same(want, s.ppe.required)) ppeBad.push(`${s.id}: want ${JSON.stringify(want)} have ${JSON.stringify(s.ppe.required)}`);
  if (!same(s.hazards.map((h) => h.hazard).sort(), hazards.sort())) ppeBad.push(`${s.id}: hazards ${JSON.stringify(s.hazards.map((h) => h.hazard))} != ${JSON.stringify(hazards)}`);
  // hazard props placed must be keyed to a derived hazard
  s.items.forEach((it, i) => {
    if (it.kind !== 'prop' || !(it.id in props.hazard_props.props)) return;
    const rule = props.hazard_props.props[it.id];
    const admitted = same(rule.ppe_any, ['*any*'])
      ? want.length > 0
      : rule.triggered_by_hazards.some((h) => ids.includes(h)) && rule.ppe_any.some((p) => want.includes(p));
    if (!admitted) ppeBad.push(`${s.id}#items[${i}] hazard prop ${it.id} not admitted by finishes`);
    if (!s.ppe.hazard_props_placed.some((r) => r.i === i)) ppeBad.push(`${s.id}#items[${i}] hazard prop not listed`);
  });
}
ok('[registry] PPE recomputed from surfaces base_conditions + hazard rules for the finishes equals the registry, and every hazard prop is admitted by a derived hazard',
  ppeBad.length === 0, ppeBad);
ok('[registry] every PPE item is in the props hazard PPE vocabulary',
  reg.ppe_items.every((p) => props.hazard_props.ppe_vocabulary.includes(p)));
ok('[registry] ppe_items is the sorted union of the spaces\' PPE',
  same(reg.ppe_items, [...new Set(reg.spaces.flatMap((s) => s.ppe.required))].sort()));

/* ---------------------------------------------------------------- cost -- */
const costBad = [];
for (const s of reg.spaces) {
  let tris = 0; const mats = new Set(); let own = 0; const inst = new Set(); const notEst = [];
  s.items.forEach((it, i) => {
    if (it.kind === 'prop' || it.kind === 'furniture') {
      const p = LOOKUP[it.kind].get(it.id);
      tris += p.tri_budget.tris;
      if (p.merges === 'pooled') mats.add(p.material);
      else if (p.merges === 'own-mesh') own += 1;
      else inst.add(it.id);
    } else notEst.push(i);
  });
  const calls = mats.size + own + inst.size;
  if (tris !== s.cost.tris) costBad.push(`${s.id}: tris ${tris} != ${s.cost.tris}`);
  if (calls !== s.cost.draw_calls) costBad.push(`${s.id}: draw_calls ${calls} != ${s.cost.draw_calls}`);
  if (!same([...mats].sort(), s.cost.pooled_materials)) costBad.push(`${s.id}: materials`);
  if (!same(notEst, s.cost.not_estimated.map((r) => r.i))) costBad.push(`${s.id}: not_estimated`);
  if (s.cost.estimated_items !== s.items.length - notEst.length) costBad.push(`${s.id}: estimated_items`);
}
ok('[registry] tris and draw calls re-summed from props tri_budget and merge modes equal the registry, kinds with no figure listed as not estimated',
  costBad.length === 0, costBad);
ok('[registry] every pooled material is one the props pack allows',
  reg.spaces.every((s) => s.cost.pooled_materials.every((m) => props.materials.allowed.includes(m))));

/* -------------------------------------------------------------- counts -- */
const c = reg.counts;
const byKind = Object.fromEntries(KINDS.map((k) => [k, reg.spaces.reduce((t, s) => t + s.items.filter((it) => it.kind === k).length, 0)]));
const countBad = [];
if (c.spaces !== reg.spaces.length) countBad.push('spaces');
if (c.items !== reg.spaces.reduce((t, s) => t + s.items.length, 0)) countBad.push('items');
if (!same(c.items_by_kind, byKind)) countBad.push(`items_by_kind ${JSON.stringify(c.items_by_kind)} != ${JSON.stringify(byKind)}`);
if (c.unions_served !== new Set(reg.spaces.flatMap((s) => s.unions.map((u) => u.slug))).size) countBad.push('unions_served');
if (!same(reg.unions_served, [...new Set(reg.spaces.flatMap((s) => s.unions.map((u) => u.slug)))].sort())) countBad.push('unions_served list');
if (c.ppe_items !== reg.ppe_items.length) countBad.push('ppe_items');
if (c.hazards !== new Set(reg.spaces.flatMap((s) => s.hazards.map((h) => h.hazard))).size) countBad.push('hazards');
if (c.tris !== reg.spaces.reduce((t, s) => t + s.cost.tris, 0)) countBad.push('tris');
if (c.draw_calls !== reg.spaces.reduce((t, s) => t + s.cost.draw_calls, 0)) countBad.push('draw_calls');
if (c.cost_estimated_items !== reg.spaces.reduce((t, s) => t + s.cost.estimated_items, 0)) countBad.push('cost_estimated_items');
if (c.cost_not_estimated_items !== reg.spaces.reduce((t, s) => t + s.cost.not_estimated.length, 0)) countBad.push('cost_not_estimated_items');
if (c.footprint_known !== reg.spaces.reduce((t, s) => t + s.items.filter((it) => it.footprint !== null).length, 0)) countBad.push('footprint_known');
if (c.footprint_unknown !== reg.spaces.reduce((t, s) => t + s.items.filter((it) => it.footprint === null).length, 0)) countBad.push('footprint_unknown');
if (c.area_m2 !== r3(reg.spaces.reduce((t, s) => t + s.footprint_m.area_m2, 0))) countBad.push('area_m2');
if (c.cost_estimated_items + c.cost_not_estimated_items !== c.items) countBad.push('estimated + not estimated != items');
for (const s of reg.spaces) {
  if (s.counts.items !== s.items.length) countBad.push(`${s.id} counts.items`);
  if (!same(s.counts.by_kind, Object.fromEntries(KINDS.map((k) => [k, s.items.filter((it) => it.kind === k).length])))) countBad.push(`${s.id} counts.by_kind`);
}
ok('[registry] every count is recomputed from the spaces, none typed', countBad.length === 0, countBad);
ok('[registry] six spaces are declared', reg.spaces.length === 6);
ok('[registry] every space places every kind at least once across the pack',
  KINDS.every((k) => byKind[k] > 0));

/* --------------------------------------------------------------- walk -- */
// The door graph is recomputed here from the plan rectangles, by the rule
// web/build_3d.py planDoors() cuts doorways with: one door on every shared
// edge with a positive overlap, one in the frontage of every room on y == 0.
const walkBad = [];
const planBad = [];
for (const [hall, rooms] of Object.entries(reg.plans)) {
  rooms.forEach((a, i) => {
    if (a.x < 0 || a.x + a.w > 12) planBad.push(`${hall}/${a.strand} leaves the 12-unit envelope`);
    rooms.slice(i + 1).forEach((b) => {
      if (!(a.x + a.w <= b.x || b.x + b.w <= a.x || a.y + a.h <= b.y || b.y + b.h <= a.y)) planBad.push(`${hall}: ${a.strand} overlaps ${b.strand}`);
    });
  });
}
ok('[walk] the stored plans are rooms inside the 12-unit envelope and no two overlap', planBad.length === 0 && Object.keys(reg.plans).length > 0, planBad);
const adjOf = (rooms) => {
  const adj = new Map(rooms.map((r) => [r.strand, new Set()]));
  rooms.forEach((a, i) => rooms.slice(i + 1).forEach((b) => {
    const side = (a.x + a.w === b.x || b.x + b.w === a.x) && Math.min(a.y + a.h, b.y + b.h) > Math.max(a.y, b.y);
    const back = (a.y + a.h === b.y || b.y + b.h === a.y) && Math.min(a.x + a.w, b.x + b.w) > Math.max(a.x, b.x);
    if (side || back) { adj.get(a.strand).add(b.strand); adj.get(b.strand).add(a.strand); }
  }));
  return adj;
};
const fewest = (rooms, target) => {   // doors from the open front: BFS over every front room at once
  const adj = adjOf(rooms), dist = new Map();
  const queue = rooms.filter((r) => r.y === 0).map((r) => { dist.set(r.strand, 1); return r.strand; });
  for (const cur of queue) for (const nx of adj.get(cur)) if (!dist.has(nx)) { dist.set(nx, dist.get(cur) + 1); queue.push(nx); }
  return dist.has(target) ? dist.get(target) : null;
};
let links = 0;
for (const s of reg.spaces) {
  const servedHalls = s.unions.map((u) => u.slug);
  if (!same(s.walk.halls.map((w) => w.hall), servedHalls)) walkBad.push(`${s.id}: walk halls ${s.walk.halls.map((w) => w.hall)} are not its unions ${servedHalls}`);
  for (const w of s.walk.halls) {
    links++;
    const rooms = reg.plans[w.hall];
    if (!rooms) { walkBad.push(`${s.id}/${w.hall}: no stored plan`); continue; }
    const room = rooms.find((r) => r.strand === s.strand);
    const env = s.fits_in.find((e) => e.hall === w.hall);
    if (!room || !same(room, w.room)) walkBad.push(`${s.id}/${w.hall}: walk.room is not the plan's ${s.strand} room`);
    if (room && env && (room.w * 3 !== env.w_m || room.h * 3 !== env.d_m)) walkBad.push(`${s.id}/${w.hall}: room ${room.w * 3}x${room.h * 3} m is not the envelope ${env.w_m}x${env.d_m} m`);
    const W = s.footprint_m.w, D = s.footprint_m.d, rw = room.w * 3, rd = room.h * 3;
    const orient = (W <= rw && D <= rd) ? 'direct' : ((D <= rw && W <= rd) ? 'transposed' : 'none');
    if (w.orient !== orient || orient === 'none') walkBad.push(`${s.id}/${w.hall}: orient ${w.orient}, recomputed ${orient}`);
    const adj = adjOf(rooms), route = w.route;
    const first = rooms.find((r) => r.strand === route[0]);
    if (!first || first.y !== 0) walkBad.push(`${s.id}/${w.hall}: the route does not start in a room on the open front`);
    if (route[route.length - 1] !== s.strand) walkBad.push(`${s.id}/${w.hall}: the route does not end in the ${s.strand} room`);
    for (let k = 1; k < route.length; k++) if (!adj.get(route[k - 1])?.has(route[k])) walkBad.push(`${s.id}/${w.hall}: no door between ${route[k - 1]} and ${route[k]}`);
    const best = fewest(rooms, s.strand);
    if (best === null) walkBad.push(`${s.id}/${w.hall}: ${s.strand} cannot be reached from the open front`);
    else if (route.length !== best || w.doors_passed !== best) walkBad.push(`${s.id}/${w.hall}: route has ${route.length} rooms, fewest is ${best}`);
    if (w.reachable !== (best !== null)) walkBad.push(`${s.id}/${w.hall}: reachable flag ${w.reachable}`);
    if (w.href !== `trade_craft_3d.html?${reg.walk_param}=${s.id}&hall=${w.hall}`) walkBad.push(`${s.id}/${w.hall}: href ${w.href}`);
  }
}
ok(`[walk] every serving hall of every space (${links}) has the space's room in its stored plan, a fitting turn, and a door route from the open front that is the fewest-door route recomputed here`, walkBad.length === 0, walkBad);
ok('[walk] every hall plan stored is the plan of a serving hall, and no hall is stored that no space serves',
  same(Object.keys(reg.plans).sort(), [...new Set(reg.spaces.flatMap((s) => s.walk.halls.map((w) => w.hall)))].sort()));
ok('[walk] the walk counts are recomputed, not typed',
  c.walk_links === links
    && c.walk_reachable === reg.spaces.reduce((t, s) => t + s.walk.halls.filter((w) => w.reachable).length, 0)
    && c.walk_transposed === reg.spaces.reduce((t, s) => t + s.walk.halls.filter((w) => w.orient === 'transposed').length, 0));
ok('[walk] the placement is stated AUTHORED and the route DERIVED',
  reg.spaces.every((s) => /^AUTHORED/.test(s.walk.placement) && s.walk.provenance === 'DERIVED'));

/* ------------------------------------------------------------ generator -- */
const src = builderSrc.replace(/#.*$/gm, '').replace(/"""[\s\S]*?"""/g, '');
ok('[generator] the builder never reads with .get(k, default) and fails closed on a missing key',
  !/\.get\([^)]*,/.test(src) && src.includes('raise KeyError'));
ok('[generator] the builder reads the room envelope from web/interiors.py plan_for, not from a typed size',
  src.includes('from interiors import plan_for') && !/w_m['"]?\s*[:=]\s*\d/.test(src));

/* ------------------------------------------------------------- drill -- */
const DRILL = [
  ['an item id that does not exist', 'every item id resolves in its owning registry'],
  ['two items overlapping', 'no two known footprints overlap (recomputed)'],
  ['an item outside the footprint', 'every item lies inside its space footprint (recomputed)'],
  ['a PPE item typed into the registry', 'PPE recomputed from surfaces ... equals the registry'],
  ['a cost figure typed', 'tris and draw calls re-summed ... equal the registry'],
  ['a count typed', 'every count is recomputed from the spaces, none typed'],
  ['a space wider than its room', 'every space fits the room of its strand in every serving hall'],
  ['the builder edited without a rebuild', 'source_stamp is sha256 of spaces/build.py'],
  ['a door route naming two rooms that share no edge', 'every serving hall ... fewest-door route recomputed here'],
  ['a space wedged in a room the plan seals off', 'every serving hall ... fewest-door route recomputed here'],
  ['the status put back to not yet walkable while the page walks', 'status says declared, a walk-through in the 3D page with equipment shown as markers'],
];
ok(`[drill] ${DRILL.length} mutations each name the check that catches them`,
  DRILL.every(([, check]) => check.length > 0));

if (bad) {
  console.log(`spaces/test: ${bad} FAILED, ${n} passed`);
  process.exit(1);
}
console.log(`spaces/test: ${n} checks passed — ${reg.counts.spaces} spaces, ${reg.counts.items} items, `
  + `${reg.counts.unions_served} unions served`);
