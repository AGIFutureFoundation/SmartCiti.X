/**
 * Surface registry verification (spec §24).
 *
 * The finishes are claims about rooms that other packs own, so every claim
 * is checked against those packs: the halls against the union roster, the
 * rooms against the interiors programme, the placement rule against §24.1's
 * discipline (a hazard is recorded only where it changed something), and
 * the §24.3 honesty — no product, brand or specification number anywhere in
 * the surface data — asserted rather than trusted.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const reg = JSON.parse(readFileSync(new URL('./registry/finishes.json', import.meta.url)));
const unions = JSON.parse(readFileSync(new URL('../unions/registry/unions.json', import.meta.url)));

const ROOM_STRANDS = ['safety', 'procedure', 'machines', 'tools', 'materials',
  'layout', 'inspection', 'troubleshooting', 'coordination', 'documentation',
  'leadership'];
const FUNCTION_DEFAULT = {
  safety: 'epoxy-smooth', procedure: 'sealed-slab', machines: 'steel-checker',
  tools: 'end-grain-block', materials: 'sealed-slab', layout: 'bare-slab',
  inspection: 'epoxy-smooth', troubleshooting: 'anti-fatigue',
  coordination: 'terrazzo-ground', documentation: 'raised-access',
  leadership: 'porcelain-tile',
};

/* ----------------------------------------------------------- catalogue --- */
const cat = reg.catalogue;
ok('the catalogue holds 22 finishes, each named with a reason',
  Object.keys(cat).length === 22
  && Object.values(cat).every((s) => s.name && s.why?.length > 10));
ok('every finish carries renderer-ready parameters in range',
  Object.values(cat).every((s) => /^#[0-9a-f]{6}$/i.test(s.color)
    && s.roughness >= 0 && s.roughness <= 1
    && s.metalness >= 0 && s.metalness <= 1
    && s.tile_m > 0 && s.tile_m <= 4 && s.pattern));
ok('§24.3 holds: no surface names a standard, product, brand or spec number',
  !/\b(ASTM|ANSI|ISO|EN|DIN|UL|NFPA)[\s-]?\d|®|™|\bclass\s+[A-Z0-9]\b/i
    .test(JSON.stringify(cat)));

/* ------------------------------------------------------------- coverage --- */
const halls = reg.halls;
ok('every hall in the union roster is resolved, and no other',
  JSON.stringify(Object.keys(halls).sort())
  === JSON.stringify(unions.unions.map((u) => u.slug).sort()));
ok('every hall resolves all 11 rooms of the interiors programme',
  Object.values(halls).every((h) =>
    JSON.stringify(Object.keys(h.rooms).sort())
    === JSON.stringify([...ROOM_STRANDS].sort())));
ok('every placed finish exists in the catalogue',
  Object.values(halls).every((h) =>
    Object.values(h.rooms).every((r) => cat[r.surface])));

/* -------------------------------------------------- placement discipline --- */
const all = Object.values(halls).flatMap((h) => Object.values(h.rooms));
ok('every placement names its rule: hazard or function, nothing else',
  all.every((r) => r.placed_by === 'hazard'
    ? typeof r.hazard === 'string' && r.hazard.length > 0
    : r.placed_by === 'function' && r.hazard === undefined));
ok('§24.1 holds: a hazard is recorded only where it changed the outcome',
  Object.values(halls).every((h) => Object.entries(h.rooms)
    .every(([strand, r]) => r.placed_by !== 'hazard'
      || r.surface !== FUNCTION_DEFAULT[strand])));
ok('function placements are exactly the function defaults',
  Object.values(halls).every((h) => Object.entries(h.rooms)
    .every(([strand, r]) => r.placed_by !== 'function'
      || r.surface === FUNCTION_DEFAULT[strand])));
ok('the hazard-placed count in the header matches the rows',
  reg.hazard_placed_finishes === all.filter((r) => r.placed_by === 'hazard').length);

/* -------------------------------------------------- §24.1 worked examples --- */
ok('a welding bay floor is a bare non-combustible slab (hot work)',
  halls.welders.rooms.procedure.surface === 'bare-slab'
  && halls.welders.rooms.procedure.hazard === 'hot-work');
ok('a cleanroom floor is welded sheet vinyl (particulates collect in joints)',
  halls.cleanroom.rooms.procedure.surface === 'welded-vinyl');
ok('a smelter stands on a firebrick hearth (it will be spilled on)',
  halls.smelter.rooms.procedure.surface === 'firebrick-hearth'
  && halls.smelter.rooms.machines.surface === 'firebrick-hearth');
ok('a contaminant trade\'s induction room reads as the function choice (§24.1)',
  halls.hazmat.rooms.safety.placed_by === 'function'
  && halls.hazmat.rooms.safety.surface === 'epoxy-smooth');

/* --------------------------------------------------- the "none" answer --- */
ok('halls with no finish-driving hazard say so explicitly, and the list is real',
  Array.isArray(reg.no_finish_driving_hazard)
  && reg.no_finish_driving_hazard.every((s) => halls[s] && halls[s].hazard === null)
  && Object.entries(halls).every(([s, h]) =>
      (h.hazard === null) === reg.no_finish_driving_hazard.includes(s)));

/* ---------------------------------------------------- conditions (§24.2) --- */
const BASE = reg.base_conditions, HAZC = reg.hazard_conditions;
ok('every hall carries conditions for all 11 rooms, in sane ranges',
  Object.values(halls).every((h) => ROOM_STRANDS.every((st) => {
    const c = h.conditions[st];
    return c && c.lux >= 100 && c.lux <= 1500 && c.ach >= 2 && c.ach <= 40
      && c.noise_db >= 35 && c.noise_db <= 100
      && c.temp_c[0] < c.temp_c[1] && Array.isArray(c.ppe)
      && Array.isArray(c.hazards);
  })));
ok('§24.2 holds: the more demanding value wins on every axis, so a second '
  + 'hazard can never cancel the first',
  Object.values(halls).every((h) => ROOM_STRANDS.every((st) => {
    const c = h.conditions[st], b = BASE[st];
    const parts = [b, ...c.hazards.map((k) => HAZC[k])];
    return parts.every((p) => c.lux >= p.lux && c.ach >= p.ach
      && c.noise_db >= p.noise_db
      && c.temp_c[0] >= (p === b ? b.temp_c[0] : p.temp_c[0]) - 1e9  // lower bound rises
      && c.temp_c[0] >= b.temp_c[0] && c.temp_c[1] <= b.temp_c[1])
      && c.hazards.every((k) => c.temp_c[0] >= HAZC[k].temp_c[0]
        && c.temp_c[1] <= HAZC[k].temp_c[1])
      && parts.every((p) => p.ppe.every((x) =>
        p === b || !c.hazards.length ? true : c.ppe.includes(x)))
      && c.hazards.every((k) => HAZC[k].ppe.every((x) => c.ppe.includes(x)))
      && b.ppe.every((x) => c.ppe.includes(x));
  })));
ok('multi-hazard trades exist and merge every governing hazard (divers: '
  + 'hot work + immersion)',
  halls.divers.conditions.procedure.hazards.length >= 2
  && halls.divers.conditions.procedure.ppe.includes('welding hood')
  && halls.divers.conditions.procedure.ppe.includes('immersion suit'));
ok('the answer "none" is explicit: unhazarded office rooms carry an empty '
  + 'PPE list, not a blank',
  Object.values(halls).every((h) =>
    ['coordination', 'documentation', 'leadership'].every((st) =>
      Array.isArray(h.conditions[st].ppe)))
  && halls.surveyors.conditions.coordination.ppe.length === 0);
ok('the hazards list is consistent with the finish provenance (first match)',
  Object.values(halls).every((h) =>
    (h.hazard === null && h.hazards.length === 0)
    || h.hazards[0] === h.hazard));
ok('§24.3 still holds over the conditions: no standard or spec number',
  !/\b(ASTM|ANSI|ISO|EN|DIN|UL|NFPA)[\s-]?\d|®|™/i
    .test(JSON.stringify({ b: BASE, h: HAZC })));

/* ---------------------------------------------------------------- walls --- */
/* The floors had twenty-two entries and the walls had none, so every room of
   every hall was drawn on one flat slab colour. These checks hold the wall
   catalogue to the same contract the floor catalogue has always been held
   to — including §24.3, which is the reason the walls describe what the work
   does to a surface and never what a standard calls it. */
const wcat = reg.wall_catalogue;
const WALL_DEFAULT = {
  safety: 'painted-block', procedure: 'liner-panel', machines: 'impact-block',
  tools: 'ply-lined', materials: 'impact-block', layout: 'whiteboard-panel',
  inspection: 'matte-board', troubleshooting: 'ply-lined',
  coordination: 'acoustic-panel', documentation: 'acoustic-panel',
  leadership: 'acoustic-panel',
};
ok('the wall catalogue holds 12 walls, each named with a reason',
  Object.keys(wcat).length === 12
  && Object.values(wcat).every((w) => w.name && w.why?.length > 10));
ok('every wall carries renderer-ready parameters in range, wainscot included',
  Object.values(wcat).every((w) => /^#[0-9a-f]{6}$/i.test(w.color)
    && /^#[0-9a-f]{6}$/i.test(w.wainscot)
    && w.roughness >= 0 && w.roughness <= 1
    && w.metalness >= 0 && w.metalness <= 1
    && w.tile_m > 0 && w.tile_m <= 4 && w.pattern
    && w.wainscot_m >= 0 && w.wainscot_m <= 2.4));
ok('§24.3 holds over the walls too: no standard, product, brand or spec number',
  !/\b(ASTM|ANSI|ISO|EN|DIN|UL|NFPA)[\s-]?\d|®|™|\bclass\s+[A-Z0-9]\b/i
    .test(JSON.stringify(wcat)));
ok('the wall defaults are one per room strand, exactly, and all in the catalogue',
  ROOM_STRANDS.every((st) => reg.wall_defaults[st] === WALL_DEFAULT[st])
  && Object.keys(reg.wall_defaults).length === ROOM_STRANDS.length
  && Object.values(reg.wall_defaults).every((w) => w in wcat));
ok('every hall carries a wall for every room, drawn from the catalogue',
  Object.values(halls).every((h) =>
    ROOM_STRANDS.every((st) => h.walls[st] && h.walls[st].wall in wcat)));

/* §24.1's discipline, applied to walls: a hazard is recorded as the placer
   only where it CHANGED the answer. A wall recorded as hazard-placed whose
   wall equals the function default would be a hazard taking credit for a
   decision the room's function had already made. */
ok('a wall is recorded as hazard-placed only where the hazard changed it',
  Object.values(halls).every((h) => ROOM_STRANDS.every((st) => {
    const w = h.walls[st];
    return w.placed_by === 'function'
      ? w.wall === WALL_DEFAULT[st] && w.hazard === undefined
      : w.wall !== WALL_DEFAULT[st] && h.hazards.includes(w.hazard);
  })));
ok('the hazard-placed wall count is the count that is actually in the records',
  reg.hazard_placed_walls === Object.values(halls)
    .reduce((a, h) => a + ROOM_STRANDS
      .filter((st) => h.walls[st].placed_by === 'hazard').length, 0));
ok('no_wall_driving_hazard names exactly the halls whose walls are all function-placed',
  JSON.stringify(reg.no_wall_driving_hazard) === JSON.stringify(
    Object.entries(halls)
      .filter(([, h]) => ROOM_STRANDS.every((st) => h.walls[st].placed_by === 'function'))
      .map(([s2]) => s2).sort()));

/* A wall resolves against EVERY hazard the trade carries, not only the one
   that drove its floor — which is why these two counts differ, and why a
   hall can have a hazard-placed wall in a room whose floor the function
   placed. This asserts the wider net rather than leaving it implied. */
ok('a wall can be hazard-placed in a room whose floor was function-placed '
  + '(the wall answers every hazard, not just the finish-driving one)',
  Object.values(halls).some((h) => ROOM_STRANDS.some((st) =>
    h.walls[st].placed_by === 'hazard' && h.rooms[st].placed_by === 'function')));

/* Hazards that a wall does not answer are ABSENT from the override table,
   not present with the default copied in. live-electrical and stored-energy
   are answered underfoot by matting; if either ever appears as a wall
   placer, someone has made the record claim more than it should. */
ok('a hazard answered underfoot never appears as a wall placer',
  Object.values(halls).every((h) => ROOM_STRANDS.every((st) =>
    !['live-electrical', 'stored-energy'].includes(h.walls[st].hazard))));

ok('walls are DERIVED, like the finishes and conditions beside them',
  reg.provenance.wall === 'DERIVED');

/* ------------------------------------------------------------ freshness --- */
const src = readFileSync(new URL('./surfaces.py', import.meta.url));
ok('the registry was built from the current catalogue source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));
ok('the registry declares §24.3 honesty: practice, not a code reference',
  /not a code reference/.test(reg.honesty.status)
  && /local standard/.test(reg.honesty.status));

ok('provenance is tagged and honest: SCHEMATIC geometry, DERIVED finish '
  + 'and conditions, nothing RECORDED (nothing was surveyed)',
  reg.provenance.geometry === 'SCHEMATIC'
  && reg.provenance.finish === 'DERIVED'
  && reg.provenance.conditions === 'DERIVED'
  && /Locator\.X/.test(reg.provenance.discipline)
  && !Object.values(reg.provenance).includes('RECORDED'));

console.log(`surfaces/test: ${n} checks passed — ${Object.keys(cat).length} finishes, `
  + `${Object.keys(wcat).length} walls, ${Object.keys(halls).length} halls, `
  + `${reg.hazards_in_use.length} hazard classes`);
