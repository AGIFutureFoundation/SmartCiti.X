/**
 * Props registry verification.
 *
 * The claim of this pack is that 1,221 rooms stop being empty boxes without
 * the scene costing anything it does not have. That is two claims and they
 * are checked separately.
 *
 * THE GEOMETRY IS NOT TAKEN ON TRUST. Every prop states a triangle count and
 * a formula. This file does not re-derive the formula from the same
 * arithmetic the builder used - it imports the VENDORED three.js the page
 * actually runs, builds the real BoxGeometry and CylinderGeometry of every
 * part of every prop, counts their indices, and compares. If three.js ever
 * changes how it triangulates a cylinder cap, this file fails and the
 * budget below is known to be wrong before anybody renders it.
 *
 * THE PLACEMENT IS NOT TAKEN ON TRUST EITHER. A prop claims it stands in a
 * strand because a word it declares appears in that strand's purpose. The
 * purpose lives in web/interiors.py and nowhere else, so this file parses
 * the ROOMS table out of that module's source and checks every match
 * against it. A hazard prop claims it stands in a room because that room's
 * conditions record asks for protective equipment it holds; this file
 * recomputes that over all 1,221 rooms of surfaces/registry/finishes.json
 * and compares the totals. Neither list may be a second copy of anything.
 *
 * AND THE BUDGET IS THE REPO'S, NOT THE PACK'S. web/eval_scene.mjs measures
 * what a hall costs in a browser and states what it may cost. This file
 * re-reads that file's baseline AND its headroom multipliers, recomputes
 * the ceilings the way the eval computes them, and holds the props to what
 * is left over - so the props pack cannot quietly raise its own ceiling.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const url = (p) => new URL(p, import.meta.url);
const reg = JSON.parse(readFileSync(url('./registry/props.json')));
const manifest = JSON.parse(readFileSync(url('../pack/manifest.json')));
const finishes = JSON.parse(readFileSync(url('../surfaces/registry/finishes.json')));
const stations = JSON.parse(readFileSync(url('../stations/registry/stations.json')));
const page = readFileSync(url('../web/build_3d.py'), 'utf8');
const interiors = readFileSync(url('../web/interiors.py'), 'utf8');
const evalsrc = readFileSync(url('../web/eval_scene.mjs'), 'utf8');
const THREE = await import('../web/vendor/three.module.min.js');

const props = reg.props;
const byId = Object.fromEntries(props.map((p) => [p.id, p]));
const strandProps = props.filter((p) => p.derive.from === 'room.purpose');
const hazardProps = props.filter((p) => p.derive.from !== 'room.purpose');

/* The room table, parsed out of the module that OWNS it. Nothing below
   compares a label or a purpose against a string typed in this file. */
const ROOMS = [...interiors.matchAll(
  /\("([a-z]+)",\s*"([^"]+)",\s*(\d+),\s*(\d+),\s*"([^"]+)"\),/g)]
  .map((m) => ({ strand: m[1], label: m[2], w: +m[3], h: +m[4], purpose: m[5] }));
const roomOf = Object.fromEntries(ROOMS.map((r) => [r.strand, r]));

/* Every room in the bundle, read from the registry that owns conditions. */
const allRooms = Object.entries(finishes.halls).flatMap(([slug, h]) =>
  Object.entries(h.conditions).map(([strand, c]) => ({ slug, strand, c })));
const ppeVocab = new Set(allRooms.flatMap((r) => r.c.ppe));

const pageNum = (re) => { const m = page.match(re); return m ? +m[1] : NaN; };
const BODY_R = pageNum(/const BODY_R = ([\d.]+);/);
const U_M = pageNum(/const U = (\d+);/);
const FLOOR_INSET = pageNum(/boxGeo\(rw - ([\d.]+), [\d.]+, rd - [\d.]+\), fmat\)/);
const FLOOR_TOP = pageNum(/floor\.position\.set\(rx, ([\d.]+), rz\)/)
  + pageNum(/boxGeo\(rw - [\d.]+, ([\d.]+), rd - [\d.]+\), fmat\)/) / 2;
const PART_TOP = pageNum(/push\(pmat, slab\(len, [\d.]+, [\d.]+, c, ([\d.]+), zz\)\)/)
  + pageNum(/push\(pmat, slab\(len, ([\d.]+), [\d.]+, c, [\d.]+, zz\)\)/) / 2;
const LABEL_Y = pageNum(/lab\.position\.set\(rx, ([\d.]+), rz\);/);
const near = (a, b) => Math.abs(a - b) < 1e-6;

/* ------------------------------------------------------------ the shape --- */
ok('the pack carries the same header every pack in this bundle carries',
  reg.pack === 'smartcitix-trade-craft-academy-props'
  && reg.pack_version === manifest.pack_version
  && /^\d{4}-\d{2}-\d{2}$/.test(reg.built) && reg.source_stamp.length === 16);
ok('every prop names a family, an anchor and a merge mode this registry declares, and no prop invents one',
  props.length > 0 && props.every((p) => p.family in reg.families
    && p.layout.anchor in reg.anchors && p.merges in reg.merge_modes
    && p.layout.anchor_is === reg.anchors[p.layout.anchor])
  && Object.keys(reg.families).every((f) => props.some((p) => p.family === f)));
ok('every prop id is unique and every prop says what it is for and why it merges the way it does',
  new Set(props.map((p) => p.id)).size === props.length
  && props.every((p) => p.why.length > 30 && p.merges_why.length > 30
    && p.name.length > 3));
ok('provenance is SCHEMATIC geometry over an AUTHORED vocabulary with DERIVED placement - never orbis\'s word',
  props.every((p) => p.provenance.geometry === 'SCHEMATIC'
    && p.provenance.vocabulary === 'AUTHORED'
    && p.provenance.placement === 'DERIVED')
  && !JSON.stringify(reg).includes('AI-SYNTHESIZED'));
ok('nothing in the payload is a URL - this pack fetches nothing and links nowhere',
  !/https?:\/\//.test(JSON.stringify(reg)));

/* ------------------------------------------- the geometry, against three --- */
ok('every recipe is boxes and cylinders only - this bundle loads no mesh and this pack adds none',
  props.every((p) => p.recipe.loads_no_mesh === true
    && p.recipe.parts.every((q) => ['box', 'cylinder'].includes(q.prim))));
ok('every declared triangle count is the count the VENDORED three.js actually produces for that recipe',
  props.every((p) => {
    const real = p.recipe.parts.reduce((a, q) => {
      const g = q.prim === 'box'
        ? new THREE.BoxGeometry(...q.size)
        : new THREE.CylinderGeometry(q.r, q.r, q.h, q.radial_segments, 1, !q.capped);
      return a + (g.index.count / 3) * q.count;
    }, 0);
    return real === p.recipe.tris && real === p.tri_budget.tris;
  }));
ok('the stated formula is the arithmetic it claims: 12 per box, 4N per capped cylinder, 2N per open one',
  props.every((p) => {
    const boxes = p.recipe.parts.filter((q) => q.prim === 'box')
      .reduce((a, q) => a + q.count, 0);
    const cyl = p.recipe.parts.filter((q) => q.prim === 'cylinder')
      .reduce((a, q) => a + (q.capped ? 4 : 2) * q.radial_segments * q.count, 0);
    return boxes === p.recipe.box_count
      && p.recipe.formula.startsWith(`12 x ${boxes} box`)
      && p.recipe.formula.endsWith(`= ${p.recipe.tris}`)
      && boxes * 12 + cyl === p.recipe.tris;
  }));
ok('every prop sits in the measured band, and the band cites the reference medians rather than a round number',
  props.every((p) => p.tri_budget.tris >= p.tri_budget.floor
    && p.tri_budget.tris <= p.tri_budget.ceiling
    && p.tri_budget.why.includes('46-104')
    && p.tri_budget.why.includes('median'))
  && JSON.stringify(reg.measured.reference_median_tris) === '[46,104]');
ok('the pack says plainly that nothing was vendored from the reference models it measured',
  /no geometry, no texture, no material, no name/.test(reg.measured.what_was_not_taken)
  && /copyrighted/.test(reg.measured.what_was_not_taken)
  && !/grove|sams|gta|rockstar/i.test(JSON.stringify(reg)));

/* ------------------------------------------ read from interiors, not typed --- */
ok('the room table parsed out of web/interiors.py is the eleven strands this pack publishes',
  ROOMS.length === 11 && new Set(ROOMS.map((r) => r.strand)).size === 11
  && JSON.stringify(Object.keys(reg.by_strand)) === JSON.stringify(ROOMS.map((r) => r.strand)));
ok('every room label this pack prints is interiors.py\'s own label, character for character',
  ROOMS.every((r) => reg.by_strand[r.strand].label === r.label
    && reg.by_strand[r.strand].source === 'web/interiors.py ROOMS'));
ok('every placement names a word that really is in THAT strand\'s own purpose line',
  Object.entries(reg.by_strand).every(([s, v]) => v.props.every((m) =>
    m.in === 'purpose'
    && roomOf[s].purpose.toLowerCase().includes(m.matched)
    && byId[m.prop].derive.tokens.includes(m.matched))));
ok('a prop lands in exactly the strands whose purpose supports it - no more, and none missing',
  strandProps.every((p) => {
    const want = ROOMS.filter((r) => p.derive.tokens
      .some((t) => r.purpose.toLowerCase().includes(t))).map((r) => r.strand);
    const got = ROOMS.filter((r) => reg.by_strand[r.strand].props
      .some((m) => m.prop === p.id)).map((r) => r.strand);
    return JSON.stringify(want) === JSON.stringify(got) && want.length > 0;
  }));
ok('every one of the eleven strands gets at least one prop - no room is left an empty box',
  ROOMS.every((r) => reg.by_strand[r.strand].props.length >= 1)
  && reg.counts.strands_covered === 11 && reg.counts.strands === 11);
ok('no token is dead vocabulary: every word a prop answers to appears in some room purpose',
  strandProps.every((p) => p.derive.tokens.every((t) =>
    ROOMS.some((r) => r.purpose.toLowerCase().includes(t)))));
ok('no prop name is a room label or a station name wearing a different key',
  (() => {
    const taken = new Set([...ROOMS.map((r) => r.label.toLowerCase()),
      ...stations.stations.map((s) => s.name.toLowerCase())]);
    return props.every((p) => !taken.has(p.name.toLowerCase()));
  })());

/* --------------------------------- hazard props, derived from the record --- */
ok('every PPE token a hazard prop triggers on is equipment the surfaces registry actually asks for',
  hazardProps.length > 0 && hazardProps.every((p) =>
    p.derive.from === 'room.conditions.ppe'
    && p.derive.ppe_any.every((t) => t === '*any*' || ppeVocab.has(t))));
ok('the PPE and hazard vocabularies published here are the registry\'s own, recomputed',
  JSON.stringify(reg.hazard_props.ppe_vocabulary) === JSON.stringify([...ppeVocab].sort())
  && JSON.stringify(reg.hazard_props.hazard_vocabulary)
     === JSON.stringify([...new Set(allRooms.flatMap((r) => r.c.hazards))].sort()));
ok('the number of rooms each hazard prop stands in is the number the rule produces over all 1,221 rooms',
  hazardProps.every((p) => {
    const want = p.derive.ppe_any;
    const hit = allRooms.filter((r) => want[0] === '*any*'
      ? r.c.ppe.length > 0 : r.c.ppe.some((x) => want.includes(x))).length;
    return reg.hazard_props.props[p.id].rooms === hit && hit > 0;
  }));
ok('a room that requires PPE gets a PPE station, and a room that requires none gets none',
  (() => {
    const need = allRooms.filter((r) => r.c.ppe.length > 0).length;
    return need === reg.hazard_props.rooms_requiring_ppe
      && need === reg.counts.rooms_requiring_ppe
      && reg.hazard_props.props['ppe-station'].rooms === need
      && need < allRooms.length;      // or the check proves nothing
  })());
ok('the hazards each prop is triggered by are the hazards whose own record adds that equipment',
  hazardProps.every((p) => {
    const want = new Set(p.derive.ppe_any);
    const got = Object.entries(finishes.hazard_conditions)
      .filter(([, hc]) => hc.ppe.some((x) => want.has(x)))
      .map(([h]) => h).sort();
    return JSON.stringify(reg.hazard_props.props[p.id].triggered_by_hazards)
      === JSON.stringify(got);
  }));
ok('the hazard block says plainly that nothing here is placed by hand',
  /No hazard prop is placed by hand/.test(reg.hazard_props.rule)
  && reg.hazard_props.source === 'surfaces/registry/finishes.json halls[*].conditions');

/* -------------------------------- the page\'s own numbers, read not copied --- */
ok('the page constants this pack sized itself against are the ones web/build_3d.py still states',
  near(reg.measured.page_constants_read.body_radius_m, BODY_R)
  && near(reg.measured.page_constants_read.grid_unit_m, U_M)
  && near(reg.measured.page_constants_read.floor_top_m, FLOOR_TOP)
  && near(reg.measured.page_constants_read.partition_top_m, PART_TOP)
  && near(reg.measured.page_constants_read.room_label_m, LABEL_Y)
  && near(reg.measured.page_constants_read.eye_height_m, pageNum(/EYE_H = ([\d.]+)/))
  && reg.measured.page_constants_read.source === 'web/build_3d.py');
ok('every material a prop names is a key of the material table the page already builds',
  (() => {
    const block = page.match(/const mat = \{([\s\S]*?)\n\};/);
    const keys = new Set([...block[1].matchAll(/^ {2}(\w+):/gm)].map((m) => m[1]));
    return props.every((p) => keys.has(p.material))
      && reg.counts.materials_used === new Set(props.map((p) => p.material)).size;
  })());
ok('no prop id collides with the page\'s EXISTING outdoor yard prop table, and the contract\'s symbol is free',
  (() => {
    const block = page.match(/const PROPS = \{([\s\S]*?)\n\};/);
    const yard = new Set([...block[1].matchAll(/^ {2}(\w+):/gm)].map((m) => m[1]));
    return yard.size > 5 && props.every((p) => !yard.has(p.id))
      && !page.includes('ROOM_PROPS') && reg.page_contract.symbol.includes('ROOM_PROPS');
  })());
ok('every page function the contract leans on is one the page actually has',
  /function flushParts\(pool, g[,)]/.test(page) && page.includes('function wallRect(')
  && page.includes('function boxGeo(') && page.includes('function buildHall(')
  && page.includes('function condOf(') && page.includes('mergeGeometries')
  && ['pooling', 'instancing', 'geometry', 'materials', 'solidity',
      'clearance', 'read_not_copied', 'where'].every((k) =>
    typeof reg.page_contract[k] === 'string' && reg.page_contract[k].length > 40));
/* This check used to assert that the pack admitted the page did NOT read
   it. The page reads it now, so the sentence it guarded had to change and
   this check had to change with it. What it guards instead is that the
   claim is CHECKABLE: the field is no longer called not_built_yet (a key
   of that name holding the word BUILT is a contradiction a reader has to
   resolve), it names the functions that do the drawing, and it states the
   shortfall rather than implying every declared prop is standing. */
ok('the pack says it is built, names the functions that build it, and does '
  + 'not carry a key called not_built_yet while saying so',
  !('not_built_yet' in reg.honesty)
  && /^BUILT\./.test(reg.honesty.built)
  && /placeRoomProps\(\)/.test(reg.honesty.built)
  && /__tc3dProps\(\)/.test(reg.honesty.built));
ok('and it states the shortfall instead of implying every declared prop is '
  + 'standing: the count rule knows nothing of doorways or the tool crib, '
  + 'so a room stands fewer than it predicts',
  /stands fewer than it predicts/.test(reg.honesty.built)
  && /names each prop that found no wall/.test(reg.honesty.built));

/* ------------------------------------------------------------- the layout --- */
ok('clearance is the page\'s own body radius, doubled, plus half again for anything you stand at',
  props.every((p) => near(p.clearance_m, 2 * BODY_R + (p.approach ? BODY_R : 0))));
ok('nothing standing on the floor stands anywhere but on the floor, or rises past the room sign',
  props.filter((p) => p.layout.anchor !== 'wall-mounted').every((p) =>
    near(p.layout.base_y_m, FLOOR_TOP)
    && near(p.layout.top_m, p.layout.base_y_m + p.size_m[1])
    && p.layout.top_m <= LABEL_Y));
ok('nothing hangs above the partition it hangs on, or through the floor below it',
  props.filter((p) => p.layout.anchor === 'wall-mounted').every((p) =>
    near(p.layout.top_m, p.layout.base_y_m + p.size_m[1] / 2)
    && p.layout.top_m <= PART_TOP
    && p.layout.base_y_m - p.size_m[1] / 2 >= FLOOR_TOP));
ok('every prop fits the smallest room that admits it, along the wall it stands on',
  props.every((p) => {
    const [wu, hu] = p.layout.smallest_room.units;
    const dM = hu * U_M - FLOOR_INSET;
    const nFit = p.layout.smallest_room.fits;
    if (nFit < 1) return false;
    if (p.layout.anchor === 'back-corner') return nFit <= p.layout.walls.length;
    const perWall = Math.ceil(nFit / p.layout.walls.length);
    const need = perWall * p.size_m[0] + (perWall - 1) * p.layout.gap_m;
    return need <= dM - p.layout.front_clear_m - p.layout.back_reserve_m + 1e-9
      && nFit <= p.layout.max_per_room;
  }));
ok('and leaves a walker a whole body width of floor between the two walls it lines',
  props.every((p) => {
    const wM = p.layout.smallest_room.units[0] * U_M - FLOOR_INSET;
    return wM - 2 * (p.size_m[2] + p.clearance_m) >= 2 * BODY_R;
  }));
ok('the smallest room a prop is fitted to is never smaller than interiors.py\'s own footprint for it',
  props.every((p) => {
    const adm = p.layout.admitted_by;
    return adm.length > 0 && adm.every((s) => s in roomOf)
      && p.layout.smallest_room.units[0] >= Math.min(...adm.map((s) => roomOf[s].w))
      && p.layout.smallest_room.units[1] === Math.min(...adm.map((s) => roomOf[s].h));
  }));
ok('the doorway side of a room stays clear by a body width, and the back band belongs to the benches the page already draws there',
  props.every((p) => near(p.layout.front_clear_m, 2 * BODY_R)
    && near(p.layout.back_reserve_m,
      pageNum(/const bz = rz \+ rd\/2 - ([\d.]+);/)
      + pageNum(/wallRect\(bx, bz, [\d.]+, ([\d.]+)\);/) + p.layout.gap_m)));

/* ------------------------------------------------------------- the budget --- */
ok('the ceiling is web/eval_scene.mjs\'s own, recomputed from its measured baseline and its own headroom',
  (() => {
    const b = evalsrc.match(/hall:\s*\{ calls: ([\d_]+), tris: ([\d_]+), meshes: ([\d_]+) \}/);
    const num = (re) => +evalsrc.match(re)[1];
    const calls = +b[1].replace(/_/g, ''), tris = +b[2].replace(/_/g, '');
    const meshes = +b[3].replace(/_/g, '');
    const s = reg.budget.ceiling_source;
    return s.measured_calls === calls && s.measured_tris === tris
      && s.measured_meshes === meshes
      && s.call_headroom_x === num(/const CALL_HEADROOM = ([\d.]+);/)
      && s.tri_headroom_x === num(/const TRI_HEADROOM = ([\d.]+);/)
      && s.mesh_floor_x === num(/const MESH_FLOOR = ([\d.]+);/)
      && s.max_calls === Math.round(calls * s.call_headroom_x)
      && s.max_tris === tris * s.tri_headroom_x
      && s.min_meshes === Math.round(meshes * s.mesh_floor_x)
      && s.headroom_calls === s.max_calls - calls
      && s.headroom_tris === s.max_tris - tris
      && reg.budget.baseline.draw_calls === calls
      && reg.budget.baseline.provenance === 'MEASURED-ELSEWHERE';
  })());
ok('this pack takes the whole unspent headroom of the HALL view, and the sibling pack the eval names for it budgets the CAMPUS view instead',
  (() => {
    const b = evalsrc.match(/campus:\s*\{ calls: ([\d_]+), tris: ([\d_]+), meshes: [\d_]+ \}/);
    const calls = +b[1].replace(/_/g, ''), tris = +b[2].replace(/_/g, '');
    const s = reg.budget.ceiling_source, k = reg.budget.self_imposed.kit_budgets;
    const kit = JSON.parse(readFileSync(url('../kit/registry/kit.json')));
    return reg.budget.self_imposed.calls_per_hall === s.headroom_calls
      && reg.budget.self_imposed.tris_per_hall === s.headroom_tris
      && k.view === 'campus'
      && k.campus_call_headroom === Math.round(calls * s.call_headroom_x) - calls
      && k.campus_tri_headroom === tris * s.tri_headroom_x - tris
      && k.its_call_ceiling === kit.budget.draw_call_ceiling
      && k.its_tri_headroom === kit.budget.triangle_headroom_total
      && k.its_call_ceiling === k.campus_call_headroom
      && k.its_tri_headroom === k.campus_tri_headroom;
  })());
ok('the worst hall stays under both self-imposed ceilings with a tenth of each still free',
  reg.budget.per_hall.calls_max <= reg.budget.self_imposed.calls_per_hall * 0.9
  && reg.budget.per_hall.tris_max <= reg.budget.self_imposed.tris_per_hall * 0.9);
ok('and with the measured baseline added, a hall still fits under the eval\'s published ceiling',
  reg.budget.delta.draw_calls_after
    === reg.budget.baseline.draw_calls + reg.budget.per_hall.calls_max
  && reg.budget.delta.draw_calls_after <= reg.budget.ceiling_source.max_calls
  && reg.budget.delta.triangles_after
    === reg.budget.baseline.triangles + reg.budget.per_hall.tris_max
  && reg.budget.delta.triangles_after <= reg.budget.ceiling_source.max_tris
  && reg.budget.delta.draw_calls_headroom
    === reg.budget.ceiling_source.max_calls - reg.budget.delta.draw_calls_after);
ok('a hall pays for its props in merged draws, never one draw per prop',
  reg.budget.per_hall.calls_max < reg.budget.per_hall.props_min
  && reg.budget.delta.props_per_draw_call > 1
  && props.every((p) => p.merges === 'pooled' || p.merges === 'instanced')
  && reg.counts.own_mesh === 0);
ok('own-mesh stays a reserved mode: it is declared, it says why, and nothing claims it',
  'own-mesh' in reg.merge_modes && /RESERVED/.test(reg.merge_modes['own-mesh'])
  && /raycast/.test(reg.merge_modes['own-mesh'])
  && props.filter((p) => p.merges === 'own-mesh').length === 0);
ok('the whole-bundle arithmetic is the per-hall arithmetic times the halls it was computed over',
  reg.budget.bundle.halls === Object.keys(finishes.halls).length
  && reg.budget.bundle.rooms === allRooms.length
  && reg.budget.bundle.rooms === reg.budget.bundle.halls * 11
  && reg.budget.bundle.prop_instances === reg.counts.prop_instances
  && reg.budget.bundle.prop_instances
     >= reg.budget.per_hall.props_min * reg.budget.bundle.halls
  && reg.budget.bundle.prop_instances
     <= reg.budget.per_hall.props_max * reg.budget.bundle.halls);

/* ------------------------------------------------------ what it will not say --- */
ok('the pack says in its own words that a schematic safety shape is not a safety specification',
  /^SCHEMATIC: /.test(reg.honesty.status)
  && /not fixture specifications/.test(reg.honesty.not_a_specification)
  && /not compliance artefacts/.test(reg.honesty.not_a_specification)
  && /not evidence that any equipment has been provided/
    .test(reg.honesty.not_a_specification)
  && /should be read as a safety-equipment specification/
    .test(reg.honesty.not_a_specification));
ok('every safety-fixture prop repeats that limit where somebody reading one record would see it',
  props.filter((p) => p.family === 'safety-fixture')
    .every((p) => /schematic|NOT a fixture specification|measures nothing|contains nothing/
      .test(p.why))
  && /not a specification/i.test(reg.families['safety-fixture']));
ok('no real union local, employer or person is named anywhere in the pack',
  !/\bLocal\s+\d|\bIBEW\b|\bUA\s+\d|\bLiUNA\b/i.test(JSON.stringify(reg)));

/* -------------------------------------------------------------- the counts --- */
ok('the counts the registry publishes are the counts it actually holds',
  reg.counts.props === props.length
  && reg.counts.families === Object.keys(reg.families).length
  && reg.counts.anchors === Object.keys(reg.anchors).length
  && reg.counts.merge_modes === Object.keys(reg.merge_modes).length
  && reg.counts.strand_props === strandProps.length
  && reg.counts.hazard_props === hazardProps.length
  && reg.counts.props === reg.counts.strand_props + reg.counts.hazard_props
  && reg.counts.placements
     === Object.values(reg.by_strand).reduce((a, v) => a + v.props.length, 0)
  && reg.counts.pooled === props.filter((p) => p.merges === 'pooled').length
  && reg.counts.instanced === props.filter((p) => p.merges === 'instanced').length
  && reg.counts.ppe_vocabulary === ppeVocab.size
  && reg.counts.halls === Object.keys(finishes.halls).length
  && reg.counts.rooms === allRooms.length);
ok('the triangle counts are the ones the recipes add up to, not a typed summary',
  reg.counts.vocabulary_tris === props.reduce((a, p) => a + p.recipe.tris, 0)
  && reg.counts.tris_min === Math.min(...props.map((p) => p.recipe.tris))
  && reg.counts.tris_max === Math.max(...props.map((p) => p.recipe.tris))
  && reg.counts.box_parts === props.reduce((a, p) => a + p.recipe.box_count, 0)
  && reg.counts.cylinder_parts
     === props.reduce((a, p) => a + p.recipe.cylinder_count, 0));

/* ------------------------------------------ the catalogue and the crib --- */
const cribs = JSON.parse(readFileSync(url('../tools/registry/toolcribs.json')));
const unions = JSON.parse(readFileSync(url('../unions/registry/unions.json')));
const kitPieces = reg.crib_furniture.pieces;
const everything = [...props, ...kitPieces];
const toolOf = new Map();
for (const [d, crib] of Object.entries(cribs.cribs))
  for (const t of crib.tools) toolOf.set(t.id, { ...t, district: d, crib: crib.name });

ok('the catalogue is what the pack says it is: the pieces the page stands plus the district pieces it cannot, and nothing counted twice',
  reg.counts.furniture === everything.length
  && reg.counts.props === props.length
  && reg.counts.crib_furniture === kitPieces.length
  && new Set(everything.map((p) => p.id)).size === everything.length
  && props.every((p) => p.catalogue === 'hall')
  && kitPieces.every((p) => p.catalogue === 'district'));
ok('NO PROP NAMES A TOOL THE CRIB DOES NOT CARRY: every tool id, name, district and use line a piece prints is the tool crib\'s own',
  everything.filter((p) => p.crib).length === reg.counts.furniture_with_crib_link
  && reg.counts.furniture_with_crib_link > 0
  && everything.filter((p) => p.crib).every((p) => p.crib.tools.length > 0
    && p.crib.source === 'tools/registry/toolcribs.json'
    && p.crib.tools.every((t) => toolOf.has(t.id)
      && toolOf.get(t.id).name === t.name
      && toolOf.get(t.id).use === t.use
      && toolOf.get(t.id).district === t.district
      && toolOf.get(t.id).crib === t.crib)));
ok('a district piece belongs to the district whose crib carries its tool - the district is read, never typed beside it',
  kitPieces.every((p) => p.district && p.crib
    && p.crib.tools.every((t) => toolOf.get(t.id).district === p.district))
  && new Set(kitPieces.map((p) => p.district)).size === Object.keys(cribs.cribs).length
  && new Set(kitPieces.map((p) => p.district)).size === reg.counts.districts);
ok('the district catalogue covers every tool in every crib, the same number of pieces each, and names no tool twice over',
  (() => {
    const per = new Map();
    for (const p of kitPieces) for (const t of p.crib.tools)
      per.set(t.id, (per.get(t.id) ?? 0) + 1);
    return per.size === toolOf.size && per.size === reg.counts.crib_tools
      && reg.counts.crib_tools_referenced === toolOf.size
      && [...per.values()].every((n) => n === reg.crib_furniture.pieces_per_tool)
      && reg.crib_furniture.pieces_per_tool * toolOf.size === kitPieces.length;
  })());
ok('the sentence a district piece gives for itself is the crib\'s own use line for its tool, not a second opinion about the tool',
  kitPieces.every((p) => p.crib.tools.every((t) =>
    p.why.includes(t.use) && p.why.includes(t.name.toLowerCase()))));
ok('every district a hall belongs to is a district the catalogue fits out, read from the unions roster',
  (() => {
    const halls = unions.unions;
    const covered = new Set(Object.keys(reg.crib_furniture.districts));
    return halls.length === reg.counts.halls
      && halls.every((h) => covered.has(h.district))
      && Object.entries(reg.crib_furniture.districts).every(([d, v]) =>
        v.halls === halls.filter((h) => h.district === d).length
        && v.pieces === kitPieces.filter((p) => p.district === d).length
        && v.crib === cribs.cribs[d].name);
  })());
ok('the district catalogue is not in the strand table the page reads, because the page has no hall to choose it with',
  (() => {
    const placed = new Set(Object.values(reg.by_strand)
      .flatMap((v) => v.props.map((m) => m.prop)));
    return kitPieces.every((p) => !placed.has(p.id))
      && reg.crib_furniture.drawn === false
      && /by_strand\[r\.strand\]/.test(reg.honesty.district_catalogue_is_not_drawn)
      && page.includes('const ids = Pk.by_strand[r.strand];')
      && !/by_district/.test(page);
  })());

/* ---------------------------------------- the draw-call argument, checked - */
ok('the whole catalogue of three hundred names the SAME seven materials the pack started with - no new material and no new draw call',
  (() => {
    const block = page.match(/const mat = \{([\s\S]*?)\n\};/);
    const keys = new Set([...block[1].matchAll(/^ {2}(\w+):/gm)].map((m) => m[1]));
    const used = new Set(everything.map((p) => p.material));
    return used.size === reg.materials.allowed.length
      && [...used].every((m) => keys.has(m) && reg.materials.allowed.includes(m))
      && reg.materials.new_materials === 0 && reg.materials.new_draw_calls === 0
      && reg.counts.materials_in_catalogue === used.size
      && JSON.stringify(reg.materials.used_by_catalogue) === JSON.stringify([...used].sort());
  })());
ok('and standing the district catalogue too would add no draw call either, because a hall pays per material and per instanced type, never per piece',
  reg.budget.district_plan.new_draw_calls_over_drawn === 0
  && reg.budget.district_plan.new_materials_over_drawn === 0
  && reg.budget.district_plan.calls_max === reg.budget.per_hall.calls_max
  && reg.budget.district_plan.tris_max > reg.budget.per_hall.tris_max
  && reg.budget.district_plan.draw_calls_after <= reg.budget.ceiling_source.max_calls
  && reg.budget.district_plan.triangles_after <= reg.budget.ceiling_source.max_tris);

ok('instancing is a reserved mode too now, and the pack says why it stopped using it: an instanced type is a draw call and a pooled piece of a material the hall already merges is not',
  reg.counts.instanced === 0 && reg.counts.own_mesh === 0
  && reg.counts.pooled === props.length
  && everything.every((p) => p.merges === 'pooled')
  && /RESERVED/.test(reg.merge_modes.instanced)
  && /saves five calls/.test(reg.merge_modes.instanced)
  && /never one per prop/.test(reg.budget.per_hall.calls_are)
  && reg.budget.per_hall.calls_max <= reg.materials.allowed.length);

/* ------------------------------------------------- the forms and the fit - */
ok('every piece is cut from a form this pack declares, and every form it declares has something cut from it',
  (() => {
    const names = new Set(reg.forms.names);
    const used = new Set(everything.map((p) => p.form));
    return names.size === reg.forms.count && reg.forms.used === used.size
      && used.size === names.size
      && everything.every((p) => names.has(p.form))
      && reg.forms.wall_forms.every((f) => names.has(f))
      && everything.filter((p) => p.layout.anchor === 'wall-mounted')
        .every((p) => reg.forms.wall_forms.includes(p.form))
      && everything.filter((p) => p.layout.anchor !== 'wall-mounted')
        .every((p) => !reg.forms.wall_forms.includes(p.form));
  })());
ok('the pack counts how many of the three hundred are really a different solid, and publishes the repeats rather than nudging a dimension to hide them',
  (() => {
    const key = (p) => JSON.stringify(p.recipe.parts);
    const distinct = new Set(everything.map(key)).size;
    return reg.geometry_spread.distinct === distinct
      && reg.geometry_spread.of === everything.length
      && reg.geometry_spread.repeated === everything.length - distinct
      && reg.counts.distinct_geometries === distinct
      && reg.counts.repeated_geometries === everything.length - distinct
      && distinct > everything.length * 0.75
      && /a bin is a bin/.test(reg.geometry_spread.what_repeats);
  })());
ok('NOTHING IN THE CATALOGUE IS PADDING: every one of the three hundred stands in at least one real room of one real hall',
  everything.every((p) => p.fit_out.rooms >= 1 && p.fit_out.instances >= p.fit_out.rooms)
  && props.every((p) => p.fit_out.from === 'the fit-out the page runs today')
  && kitPieces.every((p) => p.fit_out.from
    === 'the district plan, which the page cannot run yet'));
ok('the instances the budget adds up are the instances the pieces themselves report standing',
  props.reduce((a, p) => a + p.fit_out.instances, 0) === reg.counts.prop_instances
  && reg.budget.bundle.prop_instances === reg.counts.prop_instances);
ok('a room is offered more furniture than its walls hold, and the pack publishes both numbers rather than the flattering one',
  reg.fit_out.offered_pieces_per_room_median
    >= reg.fit_out.stood_instances_per_room_median
  && reg.fit_out.stood_instances_per_hall_median > 0
  && /SHARED/.test(reg.fit_out.how)
  && /upper bound|stands fewer/.test(reg.fit_out.is_an_upper_bound));
ok('every piece names the partition it would rather have and the other one after it, so a later piece stands across the room instead of nowhere',
  everything.every((p) => p.layout.walls.length === 2
    && p.layout.walls[0] !== p.layout.walls[1]
    && p.layout.walls.every((w) => w === 'left' || w === 'right')));
ok('a wall-hung piece hangs at the midpoint between the floor the page draws and the top of the partition it hangs on',
  (() => {
    const hang = reg.measured.page_constants_read.hang_height_m;
    return near(hang, (FLOOR_TOP + PART_TOP) / 2)
      && everything.filter((p) => p.layout.anchor === 'wall-mounted')
        .every((p) => near(p.layout.base_y_m, hang));
  })());
ok('the order the strand table publishes is the order the props array declares, because that order is what the page fills a wall in',
  (() => {
    const rank = new Map(props.map((p, i) => [p.id, i]));
    return Object.values(reg.by_strand).every((v) => v.props
      .every((m, i) => i === 0 || rank.get(v.props[i - 1].prop) < rank.get(m.prop)));
  })());
ok('no two pieces of furniture in three hundred share a name',
  new Set(everything.map((p) => p.name.toLowerCase())).size === everything.length);
ok('every family and every form the pack declares is described, and a family nothing stands in is not declared',
  Object.values(reg.families).every((d) => d.length > 25)
  && Object.keys(reg.families).every((f) => props.some((p) => p.family === f))
  && everything.every((p) => p.family in reg.families)
  && reg.counts.families === Object.keys(reg.families).length);
ok('the pack says plainly that the district catalogue is not standing anywhere and names the one page change it waits on',
  /NOT standing in any hall/.test(reg.honesty.district_catalogue_is_not_drawn)
  && /placeRoomProps\(\)/.test(reg.honesty.district_catalogue_is_not_drawn)
  && /h\.district/.test(reg.page_contract.what_the_district_catalogue_needs)
  && reg.crib_furniture.why_not_drawn
    === reg.honesty.district_catalogue_is_not_drawn);
ok('the conditions furniture - the part that makes one hall look unlike the next - states the same rule on the piece and in the hazard block, and keys on most of the kinds of work the surfaces registry knows',
  hazardProps.length > 5
  && hazardProps.every((p) => reg.hazard_props.props[p.id].rule === p.derive.rule
    && (p.derive.ppe_any[0] === '*any*'
      || p.derive.ppe_any.every((x) => p.derive.rule.includes(x))))
  && new Set(hazardProps.flatMap((p) => p.derive.triggered_by_hazards)).size
     >= Object.keys(finishes.hazard_conditions).length - 2);

const src = readFileSync(url('./build.py'));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));


/* -------------------------------------------- the reference count -------- */
// This pack quoted "five downloaded reference models" while
// assets/REFERENCE.md, which is the record of the measurement, tables SIX.
// The five came from the brief that commissioned the pack, not from the
// measurement, and it sat in the registry as a provenance claim - the one
// kind of string that must not be approximately right. A number about where
// evidence came from is checked against the evidence.
{
  const NUM = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6,
               seven: 7, eight: 8, nine: 9, ten: 10 };
  const note = readFileSync(new URL('../assets/REFERENCE.md', import.meta.url), 'utf8');
  const rows = [...note.matchAll(/^\| `[^`]+\.glb` \|/gm)].length;
  const said = reg.honesty.measured_not_guessed.match(/\b(one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:downloaded\s+)?reference/i);
  ok('the number of reference models this pack names is the number '
    + `assets/REFERENCE.md actually tables (${rows})`,
    rows > 0 && said !== null && NUM[said[1].toLowerCase()] === rows);
}

console.log(`props/test: ${n} checks passed — ${reg.counts.furniture} pieces of `
  + `furniture (${reg.counts.crib_furniture} of them district pieces cross-linked `
  + `to ${reg.counts.crib_tools_referenced} real crib tools and not yet drawn), `
  + `${reg.counts.props} props in `
  + `${reg.counts.families} families, ${reg.counts.tris_min}-${reg.counts.tris_max} tri `
  + `(median ${reg.counts.tris_median}) verified against the vendored three.js; `
  + `${reg.counts.placements} placements derived from interiors.py purposes over `
  + `${reg.counts.strands_covered}/${reg.counts.strands} strands, `
  + `${reg.counts.hazard_props} hazard props derived from `
  + `${reg.counts.rooms_requiring_ppe} PPE-requiring rooms; a hall pays `
  + `${reg.budget.per_hall.calls_max} draw calls and `
  + `${reg.budget.per_hall.tris_max.toLocaleString('en-US')} triangles for `
  + `${reg.budget.per_hall.props_max} props, against `
  + `${reg.budget.self_imposed.calls_per_hall} and `
  + `${reg.budget.self_imposed.tris_per_hall.toLocaleString('en-US')} read from `
  + `web/eval_scene.mjs`);
