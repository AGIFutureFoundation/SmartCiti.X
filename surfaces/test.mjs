/**
 * Surface registry verification (spec §24).
 *
 * The finishes are claims about rooms that other packs own, so every claim
 * is checked against those packs: the halls against the union roster, the
 * rooms against the interiors programme, the placement rule against §24.1's
 * discipline (a rule is recorded only where it changed something), and
 * the §24.3 honesty — no product, brand or specification number anywhere in
 * the surface data — asserted rather than trusted.
 *
 * §24.1 now resolves three tiers — hazard, craft, function — so the tests
 * that used to say "hazard or function, nothing else" say "hazard, craft or
 * function", and a new set holds the craft tier to exactly the discipline
 * the hazard tier has always been held to: it may only be recorded where it
 * changed the answer, and it may never overrule a hazard.
 *
 * The defaults are no longer restated here. They are in the registry, which
 * is where they are decided; a copy in this file would be a second truth
 * that could disagree with the first and still pass.
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
const FUNCTION_DEFAULT = reg.function_defaults;
const WALL_DEFAULT = reg.wall_defaults;

/* How far a colour sits from neutral grey, and which way it leans. The same
   two sums the catalogue module makes, because the palette rule is the one
   claim in this pack that is about what the thing LOOKS like, and a test
   that could not measure it could not hold it. */
const rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const chroma = (h) => { const c = rgb(h); return Math.max(...c) - Math.min(...c); };
const warm = (h) => { const c = rgb(h); return c[0] > c[2]; };
const median = (xs) => { const a = [...xs].sort((x, y) => x - y);
  return a.length % 2 ? a[(a.length - 1) / 2]
    : (a[a.length / 2 - 1] + a[a.length / 2]) / 2; };

/* ----------------------------------------------------------- catalogue --- */
const cat = reg.catalogue;
ok('every finish in the catalogue is named and carries its reason',
  Object.keys(cat).length > 0
  && Object.values(cat).every((s) => s.name && s.why?.length > 10)
  && new Set(Object.values(cat).map((s) => s.name)).size
     === Object.keys(cat).length);
ok('every finish carries renderer-ready parameters in range',
  Object.values(cat).every((s) => /^#[0-9a-f]{6}$/i.test(s.color)
    && s.roughness >= 0 && s.roughness <= 1
    && s.metalness >= 0 && s.metalness <= 1
    && s.tile_m > 0 && s.tile_m <= 4 && s.pattern));
ok('§24.3 holds: no surface names a standard, product, brand or spec number',
  !/\b(ASTM|ANSI|ISO|EN|DIN|UL|NFPA)[\s-]?\d|®|™|\bclass\s+[A-Z0-9]\b/i
    .test(JSON.stringify(cat)));

/* Two surfaces the same colour are two surfaces nobody can tell apart from
   standing height, which is the whole of what this catalogue is for. */
ok('no two finishes and no two walls are given the same colour',
  new Set(Object.values(cat).map((s) => s.color.toLowerCase())).size
    === Object.keys(cat).length
  && new Set(Object.values(reg.wall_catalogue).map((w) => w.color.toLowerCase())).size
    === Object.keys(reg.wall_catalogue).length);

/* The first catalogue had a median chroma of 9 out of 255 across the floors
   and 12 across the walls - a working building rendered in twenty-two
   shades of the same grey. These two are the floor that stops it drifting
   back, and they are checked here as well as in the builder because a
   palette is the one thing in this pack a reader judges before they read a
   word of it. */
ok('the palette has not gone grey: both catalogues carry real chroma',
  median(Object.values(cat).map((s) => chroma(s.color))) >= 19
  && median(Object.values(reg.wall_catalogue).map((w) => chroma(w.color))) >= 19);
ok('the palette carries both temperatures, not one leaning family',
  [cat, reg.wall_catalogue].every((t) => {
    const cols = Object.values(t).map((x) => x.color);
    const w = cols.filter(warm).length;
    return w >= cols.length / 4 && cols.length - w >= cols.length / 4;
  }));

/* The pattern vocabulary is closed in BOTH directions. A finish naming a
   pattern nothing declares would render as whatever the page falls back to,
   silently; a pattern declared and never used is a recipe for a surface
   that does not exist. */
const pats = reg.patterns;
const patsUsed = new Set([...Object.values(cat).map((s) => s.pattern),
  ...Object.values(reg.wall_catalogue).map((w) => w.pattern)]);
ok('every pattern a surface names is declared, and every declared pattern is used',
  [...patsUsed].every((p) => typeof pats[p] === 'string' && pats[p].length > 10)
  && Object.keys(pats).every((p) => patsUsed.has(p)));
ok('§24.3 holds over the pattern vocabulary too',
  !/\b(ASTM|ANSI|ISO|EN|DIN|UL|NFPA)[\s-]?\d|®|™/i.test(JSON.stringify(pats)));

/* ------------------------------------------- the page's own two closed sets --
   A finish costs a TEXTURE, never a material: the page runs one surface
   engine (surfaceMaps) that paints a pattern onto a canvas and reads a
   normal map off the height field, and a room draws one floor mesh and one
   merged partition per wall whatever the catalogue holds. That is only true
   while every pattern this catalogue names is one the page already has a
   recipe for, and the page closes two sets to keep it true:

     PATTERN_RELIEF  - the relief depth per pattern. A pattern missing from
                       it renders FLAT, and the page's build refuses it.
     FLOOR_STEP      - the footfall family per FLOOR pattern. A floor
                       pattern missing from it has no sound, and the page's
                       build refuses that too.

   Both live in web/build_3d.py, which this pack does not own. Finding out
   from a failed page build that the vocabulary was closed is finding out
   too late, so the two sets are read here, structurally, and the catalogue
   is held to them in the pack that would have to change. `fabric` is the
   worked example: the weave is declared for walls and has no floor step
   family, so a broadloom carpet cannot be a floor in this engine today. */
const pageSrc = readFileSync(new URL('../web/build_3d.py', import.meta.url), 'utf8');
const declBlock = (re, keyRe, strip) => {
  const m = pageSrc.match(re);
  if (!m) return null;
  return new Set([...m[1].replace(strip, '').matchAll(keyRe)].map((x) => x[1]));
};
const RELIEF = declBlock(/const PATTERN_RELIEF = \{([\s\S]*?)\n\};/,
  /(\w[\w-]*)\s*:/g, /\/\/[^\n]*/g);
const STEP = declBlock(/\nFLOOR_STEP = \{([\s\S]*?)\n\}/,
  /'([\w-]+)':/g, /#[^\n]*/g);
const floorPats = new Set(Object.values(cat).map((s) => s.pattern));

ok('every pattern this catalogue names is one the page already declares a '
  + 'relief for, so a finish added here costs a texture and never a material',
  RELIEF !== null && RELIEF.size > 0
  && [...patsUsed].every((p) => RELIEF.has(p)));
ok('every FLOOR pattern is one the page has a footfall family for - the '
  + 'wall-only patterns (the weave among them) stay off the floor',
  STEP !== null && STEP.size > 0
  && [...floorPats].every((p) => STEP.has(p))
  && !STEP.has('fabric') && !floorPats.has('fabric'));

/* ----------------------------------------------- what a surface is made of --
   A catalogue this size is only worth having if the entries differ in the
   properties the renderer actually READS. Two of those are decided by the
   material and not by taste, so they are checked rather than trusted:
   metalness, which a pattern that can only be pressed or cast out of metal
   must carry and one that is fired, cast or ground out of mineral must not;
   and roughness, which is how a floor of one pattern differs from the next
   floor of the same pattern. A pattern whose every finish shares one
   roughness is one material in several colours, which is the failure this
   whole pass was meant to avoid. */
const METAL_PATTERNS = ['checker', 'diamond', 'plate', 'grate', 'tslot'];
const MINERAL_PATTERNS = ['brick', 'ashlar', 'terrazzo', 'sand', 'ballast'];
const both = { ...cat, ...reg.wall_catalogue };
ok('a pattern that can only be metal is metal, and one that is fired, cast '
  + 'or ground out of mineral carries no metalness worth the name',
  Object.values(both).filter((s) => METAL_PATTERNS.includes(s.pattern))
    .every((s) => s.metalness >= .3)
  && Object.values(both).filter((s) => MINERAL_PATTERNS.includes(s.pattern))
    .every((s) => s.metalness < .1));

const byPattern = {};
for (const f of Object.values(cat)) (byPattern[f.pattern] ??= []).push(f.roughness);
ok('no pattern is one material repainted: where more than one floor names a '
  + 'pattern, they do not all share a roughness',
  Object.values(byPattern).every((rs) => rs.length < 2
    || new Set(rs).size > 1));
ok('the catalogue spreads across its vocabulary: no single pattern carries '
  + 'more than a quarter of the floors',
  Object.values(byPattern).every((rs) => rs.length <= Object.keys(cat).length / 4));

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
ok('every placement names its rule: hazard, craft or function, nothing else',
  all.every((r) => {
    if (r.placed_by === 'hazard') return typeof r.hazard === 'string'
      && r.hazard.length > 0 && r.craft === undefined;
    if (r.placed_by === 'craft') return typeof r.craft === 'string'
      && r.craft.length > 0 && r.hazard === undefined;
    return r.placed_by === 'function'
      && r.hazard === undefined && r.craft === undefined;
  }));
ok('§24.1 holds: a hazard is recorded only where it changed the outcome',
  Object.values(halls).every((h) => Object.entries(h.rooms)
    .every(([strand, r]) => r.placed_by !== 'hazard'
      || r.surface !== FUNCTION_DEFAULT[strand])));
ok('§24.1 holds for the craft tier on the same terms',
  Object.values(halls).every((h) => Object.entries(h.rooms)
    .every(([strand, r]) => r.placed_by !== 'craft'
      || (r.surface !== FUNCTION_DEFAULT[strand]
          && h.crafts.includes(r.craft)))));

/* The tiers are ordered, and the order is the whole point: a hazard is what
   the work can do to a person and a craft is what the trade does all day.
   Because the registry publishes the rule tables, this does not spot-check
   the order - it re-derives every one of the 1,221 floors and 1,221 walls
   from the rules and the hall's own hazard and craft lists, and demands the
   record match. A craft resolved ahead of a hazard, a hazard whose override
   was dropped, or a tier silently skipped all fail here. */
const R = reg.rules;
const deriveFloor = (h, st) => {
  const want = h.hazard === null ? undefined : R.hazard_rooms[h.hazard]?.[st];
  if (want !== undefined) {
    return want !== FUNCTION_DEFAULT[st]
      ? { surface: want, placed_by: 'hazard', hazard: h.hazard }
      : { surface: FUNCTION_DEFAULT[st], placed_by: 'function' };
  }
  for (const ck of h.crafts) {
    const c = R.craft_rooms[ck]?.[st];
    if (c && c !== FUNCTION_DEFAULT[st]) {
      return { surface: c, placed_by: 'craft', craft: ck };
    }
  }
  return { surface: FUNCTION_DEFAULT[st], placed_by: 'function' };
};
const deriveWall = (h, st) => {
  for (const hz of h.hazards) {
    const want = R.hazard_walls[hz]?.[st];
    if (want && want !== WALL_DEFAULT[st]) {
      return { wall: want, placed_by: 'hazard', hazard: hz };
    }
    if (want) return { wall: WALL_DEFAULT[st], placed_by: 'function' };
  }
  for (const ck of h.crafts) {
    const want = R.craft_walls[ck]?.[st];
    if (want && want !== WALL_DEFAULT[st]) {
      return { wall: want, placed_by: 'craft', craft: ck };
    }
  }
  return { wall: WALL_DEFAULT[st], placed_by: 'function' };
};
ok('every floor and wall in the registry is exactly what the published '
  + 'rules say, hazard before craft before function',
  Object.values(halls).every((h) => ROOM_STRANDS.every((st) =>
    JSON.stringify(h.rooms[st]) === JSON.stringify(deriveFloor(h, st))
    && JSON.stringify(h.walls[st]) === JSON.stringify(deriveWall(h, st)))));

/* The rule tables have to be about rooms and surfaces that exist, or the
   check above would be re-deriving the registry from nonsense and agreeing
   with itself. */
ok('every rule names a real room strand and a real surface',
  Object.values(R.hazard_rooms).concat(Object.values(R.craft_rooms))
    .every((m) => Object.entries(m).every(([st, f]) =>
      ROOM_STRANDS.includes(st) && f in cat))
  && Object.values(R.hazard_walls).concat(Object.values(R.craft_walls))
    .every((m) => Object.entries(m).every(([st, w]) =>
      ROOM_STRANDS.includes(st) && w in reg.wall_catalogue))
  && Object.keys(R.hazard_rooms).every((k) => k in reg.hazard_conditions)
  && Object.keys(R.hazard_walls).every((k) => k in reg.hazard_conditions));

/* A craft that names a room and picks that room's own function default has
   changed nothing, and would teach the record to claim a reason that did no
   work (§24.1). Hazards are exempt - hot work confirming a default on
   purpose is the case §24.1 was written about - crafts are not. */
ok('no craft rule restates a default it could not change',
  Object.values(R.craft_rooms).every((m) =>
    Object.entries(m).every(([st, f]) => f !== FUNCTION_DEFAULT[st]))
  && Object.values(R.craft_walls).every((m) =>
    Object.entries(m).every(([st, w]) => w !== WALL_DEFAULT[st])));
ok('the craft-placed count in the header matches the rows',
  reg.craft_placed_finishes
    === all.filter((r) => r.placed_by === 'craft').length
  && reg.craft_placed_walls === Object.values(halls)
    .reduce((a, h) => a + ROOM_STRANDS
      .filter((st) => h.walls[st].placed_by === 'craft').length, 0));
ok('no_craft names exactly the halls whose trade matches no craft',
  JSON.stringify(reg.no_craft) === JSON.stringify(
    Object.entries(halls).filter(([, h]) => h.crafts.length === 0)
      .map(([s2]) => s2).sort())
  && Object.values(halls).every((h) =>
    (h.craft === null) === (h.crafts.length === 0)
    && (h.crafts.length === 0 || h.craft === h.crafts[0])));

/* A craft places surfaces and nothing else. It is deliberately absent from
   the conditions record, because what a trade does all day is not something
   lighting, air changes or PPE answer - and the day somebody promotes a
   craft to a hazard by hand, this is what says so. */
const CRAFT_KEYS = new Set(reg.crafts_in_use);
ok('a craft never appears in a conditions record: conditions answer hazards',
  Object.values(halls).every((h) => ROOM_STRANDS.every((st) =>
    h.conditions[st].hazards.every((k) => !CRAFT_KEYS.has(k)
      && k in reg.hazard_conditions))));

/* A finish or a wall nobody stands on is a preference, and §24.1 says this
   catalogue holds none. The builder asserts it; this proves the emitted
   lists are the real ones rather than two empty arrays nobody computed. */
ok('nothing sits in either catalogue that no rule ever places',
  JSON.stringify(reg.unplaced_finishes) === JSON.stringify(
    Object.keys(cat).filter((f) => !Object.values(halls)
      .some((h) => Object.values(h.rooms).some((r) => r.surface === f))).sort())
  && JSON.stringify(reg.unplaced_walls) === JSON.stringify(
    Object.keys(reg.wall_catalogue).filter((w) => !Object.values(halls)
      .some((h) => Object.values(h.walls).some((x) => x.wall === w))).sort())
  && reg.unplaced_finishes.length === 0 && reg.unplaced_walls.length === 0);
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
ok('every wall in the catalogue is named and carries its reason',
  Object.keys(wcat).length > 0
  && Object.values(wcat).every((w) => w.name && w.why?.length > 10)
  && new Set(Object.values(wcat).map((w) => w.name)).size
     === Object.keys(wcat).length);
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
ok('the defaults are one per room strand, exactly, and all in the catalogue',
  Object.keys(reg.wall_defaults).length === ROOM_STRANDS.length
  && Object.keys(reg.function_defaults).length === ROOM_STRANDS.length
  && ROOM_STRANDS.every((st) => reg.wall_defaults[st] in wcat
    && reg.function_defaults[st] in cat));
ok('every hall carries a wall for every room, drawn from the catalogue',
  Object.values(halls).every((h) =>
    ROOM_STRANDS.every((st) => h.walls[st] && h.walls[st].wall in wcat)));

/* §24.1's discipline, applied to walls: a hazard is recorded as the placer
   only where it CHANGED the answer. A wall recorded as hazard-placed whose
   wall equals the function default would be a hazard taking credit for a
   decision the room's function had already made. */
ok('a wall is recorded as hazard- or craft-placed only where that rule changed it',
  Object.values(halls).every((h) => ROOM_STRANDS.every((st) => {
    const w = h.walls[st];
    if (w.placed_by === 'function') {
      return w.wall === WALL_DEFAULT[st]
        && w.hazard === undefined && w.craft === undefined;
    }
    if (w.placed_by === 'hazard') {
      return w.wall !== WALL_DEFAULT[st] && h.hazards.includes(w.hazard)
        && w.craft === undefined;
    }
    return w.placed_by === 'craft' && w.wall !== WALL_DEFAULT[st]
      && h.crafts.includes(w.craft) && w.hazard === undefined;
  })));
ok('the hazard-placed wall count is the count that is actually in the records',
  reg.hazard_placed_walls === Object.values(halls)
    .reduce((a, h) => a + ROOM_STRANDS
      .filter((st) => h.walls[st].placed_by === 'hazard').length, 0));
/* The field says "no wall-driving HAZARD", and that is narrower than "no
   rule moved a wall" now that a craft can move one. It is computed the
   narrow way it is named. */
ok('no_wall_driving_hazard names exactly the halls no hazard moved a wall in',
  JSON.stringify(reg.no_wall_driving_hazard) === JSON.stringify(
    Object.entries(halls)
      .filter(([, h]) => ROOM_STRANDS.every((st) => h.walls[st].placed_by !== 'hazard'))
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

/* --------------------------------------------- §24.1 worked examples, II --- */
/* Three halls the first vocabulary read wrong, each because a word was
   standing in for a meaning it does not always carry. The terrazzo hall's
   focus line says "pours" and it was given a firebrick hearth; the water
   hall "taps" mains and was given one too; the window hall fits blast
   glazing and was handed a mobile-plant floor. They are the cheapest kind
   of error to reintroduce, so each is nailed down by name. */
ok('a terrazzo hall lays terrazzo: "pours" is not a molten pour',
  halls.terrazzo.hazard !== 'molten-metal'
  && halls.terrazzo.rooms.procedure.surface === 'terrazzo-divider'
  && halls.terrazzo.rooms.procedure.placed_by === 'craft');
ok('a water-distribution hall taps mains: "tapping" is not furnace tapping',
  halls['water-distrib'].hazard !== 'molten-metal'
  && !Object.values(halls['water-distrib'].rooms)
    .some((r) => r.surface === 'firebrick-hearth'));
ok('a window hall fits blast glazing and does not thereby run mobile plant',
  !halls['window-glazing'].hazards.includes('mobile-plant')
  && halls['window-glazing'].crafts.includes('glass-envelope'));

/* The craft tier exists because sixty-one halls drew the same eleven floors
   as each other. This measures the thing it was built for rather than
   trusting that more rules means more variety. */
const sig = (h) => JSON.stringify([ROOM_STRANDS.map((st) => h.rooms[st].surface),
  ROOM_STRANDS.map((st) => h.walls[st].wall)]);
const sigs = new Set(Object.values(halls).map(sig));
const sigsNoCraft = new Set(Object.values(halls).map((h) => JSON.stringify([
  ROOM_STRANDS.map((st) => (h.rooms[st].placed_by === 'craft'
    ? FUNCTION_DEFAULT[st] : h.rooms[st].surface)),
  ROOM_STRANDS.map((st) => (h.walls[st].placed_by === 'craft'
    ? WALL_DEFAULT[st] : h.walls[st].wall))])));
ok('the craft tier earns its place: it more than doubles the number of halls '
  + 'that read as different rooms',
  sigs.size >= sigsNoCraft.size * 2 && sigs.size >= 50);

/* ------------------------------------------------------------ freshness --- */
const src = readFileSync(new URL('./surfaces.py', import.meta.url));
ok('the registry was built from the current catalogue source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));
ok('the registry declares §24.3 honesty: practice, not a code reference',
  /not a code reference/.test(reg.honesty.status)
  && /local standard/.test(reg.honesty.status));

/* A colour chosen by eye is AUTHORED, and the pack that chose it has to say
   so in its own words - the sky pack's `colours_are_authored` is the
   precedent. The catalogue's colours, roughnesses and metalnesses are all of
   that kind, and growing the catalogue does not make any of them measured.
   The field is read by name; a missing one reads as undefined and fails. */
ok('the palette says what it is: chosen by eye, never sampled, and AUTHORED '
  + 'in the pack that chose it',
  /chosen by\s+eye/.test(reg.honesty.colours_are_authored)
  && /never sampled/.test(reg.honesty.colours_are_authored)
  && reg.provenance.catalogue === 'AUTHORED');

ok('provenance is tagged and honest: SCHEMATIC geometry, DERIVED finish '
  + 'and conditions, nothing RECORDED (nothing was surveyed)',
  reg.provenance.geometry === 'SCHEMATIC'
  && reg.provenance.finish === 'DERIVED'
  && reg.provenance.conditions === 'DERIVED'
  && /Locator\.X/.test(reg.provenance.discipline)
  && !Object.values(reg.provenance).includes('RECORDED'));

/* The catalogue and its placement are two different claims and were being
   told as one. Somebody WROTE each colour, roughness and reason - that is
   AUTHORED - and the rules then DERIVED which hall stands on which, out of
   the trade's own words. Collapsing them would let an authored colour ride
   in under a provenance word it has not earned. */
ok('the catalogue is AUTHORED and only its placement is DERIVED',
  reg.provenance.catalogue === 'AUTHORED'
  && reg.provenance.placement === 'DERIVED');

/* The provenance vocabulary is four words, and the fourth belongs to
   another pack. Surfaces are written or derived; nothing here was generated
   by a model, and a tag claiming otherwise would be a claim this pack
   cannot support. */
ok('every provenance tag is one of the four words, and none is the orbis '
  + 'pack\u2019s',
  Object.entries(reg.provenance)
    .filter(([k]) => k !== 'discipline')
    .every(([, v]) => ['RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED'].includes(v))
  && !/AI[-\s]?SYNTH/i.test(JSON.stringify(reg)));

/* A wainscot the same colour as the wall above it is not a band, it is a
   field with a name. The point of the band is that you can see where the
   work reaches. */
ok('every wainscot reads as a band: it differs from the wall it sits under',
  Object.values(wcat).every((w) => w.wainscot_m === 0
    || w.wainscot.toLowerCase() !== w.color.toLowerCase()));

/* Every hazard the rules or the records name must carry its condition
   demands, or §24.2's merge is reading an absent row and quietly agreeing
   with itself. */
ok('every hazard named anywhere carries its condition demands',
  [...new Set([...Object.keys(R.hazard_rooms), ...Object.keys(R.hazard_walls),
    ...Object.values(halls).flatMap((h) => h.hazards)])]
    .every((k) => k in reg.hazard_conditions));

/* ------------------------------------------------------------ legibility ---
   The honesty block says every colour was chosen by eye; this is what
   measures whether a sign can be read against them. The registry's numbers
   are recomputed here from the catalogues and the labels palette with an
   implementation written independently of the builder's (WCAG 2.x, sRGB
   D65), and must agree to three decimals; every count is counted, never
   read back; every failing pair is checked to really be under its
   threshold; and the cross-read of the labels registry is stamped so a
   palette that moved after this was built fails here. */
const labels = JSON.parse(readFileSync(new URL('../labels/registry/labels.json', import.meta.url)));
const LEG = reg.legibility;
const parseC = (c) => {
  if (/^#[0-9a-f]{6}$/i.test(c)) return [...rgb(c), 1];
  const m = /^rgba\((\d+),(\d+),(\d+),(\d*\.?\d+)\)$/.exec(c.trim());
  if (!m) throw new Error(`unreadable colour ${c}`);
  return [+m[1], +m[2], +m[3], +m[4]];
};
const chan = (v) => { const x = v / 255; return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; };
const Y = (c) => 0.2126 * chan(c[0]) + 0.7152 * chan(c[1]) + 0.0722 * chan(c[2]);
const contrast = (a, b) => { const p = Y(a), q = Y(b); return (Math.max(p, q) + 0.05) / (Math.min(p, q) + 0.05); };
const blend = (fg, bg) => [0, 1, 2].map((i) => fg[i] * fg[3] + bg[i] * (1 - fg[3])).concat([1]);
const near3 = (a, b) => Math.abs(a - b) < 0.0006;
const fam = {
  floor: Object.fromEntries(Object.entries(cat).map(([id, f]) => [id, f.color])),
  wall: Object.fromEntries(Object.entries(wcat).map(([id, w]) => [id, w.color])),
  wainscot: Object.fromEntries(Object.entries(wcat).filter(([, w]) => w.wainscot_m > 0)
    .map(([id, w]) => [id, w.wainscot])),
};
const roleOf = Object.fromEntries(Object.entries(labels.palette_roles)
  .flatMap(([role, keys]) => keys.map((k) => [k, role])));
ok('the legibility block reads the labels palette with its roles, and every palette key it read is the labels registry’s own',
  Object.keys(LEG.palette_read).sort().join() === Object.keys(labels.palette).sort().join()
  && Object.entries(LEG.palette_read).every(([k, v]) => v.color === labels.palette[k]
    && v.role === roleOf[k])
  && Object.keys(roleOf).sort().join() === Object.keys(labels.palette).sort().join());
ok('every floor, wall and wainscot carries a WCAG relative luminance that recomputes to 3 decimals',
  Object.entries(fam).every(([f, cols]) => Object.keys(LEG.luminance[f]).length === Object.keys(cols).length
    && Object.entries(cols).every(([id, c]) => near3(LEG.luminance[f][id], Y(parseC(c)))))
  && Object.entries(LEG.families).every(([f, k]) => k === Object.keys(fam[f]).length));
/* the whole matrix, recomputed: a translucent plate composited over the
   finish and compared with it, an opaque colour straight on the finish */
const mine = {};
const cnt = { at_or_above_4_5: 0, from_3_below_4_5: 0, below_3: 0, pairs: 0 };
const fails = [];
for (const [f, cols] of Object.entries(fam)) {
  mine[f] = {};
  for (const [id, c] of Object.entries(cols)) {
    const bg = parseC(c); mine[f][id] = {};
    for (const [k, lc] of Object.entries(labels.palette)) {
      const fg = parseC(lc);
      const r = fg[3] < 1 ? contrast(blend(fg, bg), bg) : contrast(fg, bg);
      mine[f][id][k] = r; cnt.pairs++;
      if (r >= 4.5) cnt.at_or_above_4_5++; else if (r >= 3) cnt.from_3_below_4_5++; else cnt.below_3++;
      const thr = LEG.thresholds.fails_under[roleOf[k]];
      if (r < thr) fails.push(`${f}|${id}|${k}`);
    }
  }
}
ok(`every finish x label colour pair recomputes to 3 decimals (${cnt.pairs} pairs)`,
  Object.entries(mine).every(([f, rows]) => Object.entries(rows).every(([id, row]) =>
    Object.entries(row).every(([k, r]) => near3(LEG.pairs[f][id][k], r)))));
ok(`the three counts are counted, not typed: ${cnt.at_or_above_4_5} at 4.5+, ${cnt.from_3_below_4_5} from 3, ${cnt.below_3} under 3`,
  ['at_or_above_4_5', 'from_3_below_4_5', 'below_3', 'pairs'].every((k) => LEG.counts[k] === cnt[k])
  && cnt.at_or_above_4_5 + cnt.from_3_below_4_5 + cnt.below_3 === cnt.pairs);
ok('text fails under 4.5, a plate or an accent under 3, and the thresholds say so',
  LEG.thresholds.normal_text === 4.5 && LEG.thresholds.large_text === 3
  && LEG.thresholds.fails_under.text === 4.5 && LEG.thresholds.fails_under.plate === 3
  && LEG.thresholds.fails_under.accent === 3);
ok(`every failing pair listed is really under its threshold, and no failing pair is missing (${fails.length})`,
  LEG.failing.every((x) => mine[x.family][x.finish][x.role] < x.threshold
    && x.threshold === LEG.thresholds.fails_under[roleOf[x.role]] && x.kind === roleOf[x.role]
    && near3(x.ratio, mine[x.family][x.finish][x.role]))
  && LEG.failing.map((x) => `${x.family}|${x.finish}|${x.role}`).sort().join('\n') === fails.sort().join('\n')
  && Object.entries(LEG.failing_by_kind).every(([k, v]) => v === LEG.failing.filter((x) => x.kind === k).length));
/* the rule with teeth: the text the page paints on a plate, over every
   finish, recomputed from the labels registry's paint contract */
const topPairs = new Set();
for (const p of Object.values(labels.paint)) for (const line of ['title', 'sub'])
  if (p[line] in labels.palette && p.plate in labels.palette) topPairs.add(`${p[line]} on ${p.plate}`);
ok(`the text-on-plate pairs the page paints are exactly the ones measured (${topPairs.size}), and each clears 4.5:1 over every finish`,
  [...topPairs].sort().join() === Object.keys(LEG.text_on_plate).sort().join()
  && [...topPairs].every((key) => {
    const [t, pl] = key.split(' on ');
    const fg = parseC(labels.palette[t]), plate = parseC(labels.palette[pl]);
    let worst = Infinity;
    for (const [f, cols] of Object.entries(fam)) {
      let fw = Infinity, fid = null;
      for (const [id, c] of Object.entries(cols)) {
        const r = contrast(fg, blend(plate, parseC(c)));
        if (r < fw) { fw = r; fid = id; }
      }
      if (!near3(LEG.text_on_plate[key].per_family[f].ratio, fw)
        || LEG.text_on_plate[key].per_family[f].finish !== fid) return false;
      worst = Math.min(worst, fw);
    }
    return worst >= 4.5 && near3(LEG.text_on_plate[key].worst.ratio, worst);
  }));
ok('no finish was recoloured for a pair it cannot own, and the rule says why',
  Array.isArray(LEG.finishes_changed) && LEG.finishes_changed.length === 0
  && /a colour here is what the material is/.test(LEG.rule));
/* ---------------------------------------------------------------- palette --- */
const PAL = reg.palette;
const hsl = (c) => {
  const r = c[0] / 255, g = c[1] / 255, b = c[2] / 255;
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2;
  if (mx === mn) return [0, 0, l * 100];
  const d = mx - mn, s = l > .5 ? d / (2 - mx - mn) : d / (mx + mn);
  let h = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h * 60, s * 100, l * 100];
};
const lab = (c) => {
  const [r, g, b] = [chan(c[0]), chan(c[1]), chan(c[2])];
  const x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047;
  const y = (0.2126729 * r + 0.7151522 * g + 0.0721750 * b);
  const z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883;
  const f = (t) => (t > 216 / 24389 ? Math.cbrt(t) : (841 / 108) * t + 4 / 29);
  return [116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))];
};
const dE = (a, b) => Math.hypot(...lab(a).map((v, i) => v - lab(b)[i]));
ok('the hue distribution is counted in 30-degree buckets per family, and the buckets sum to the family',
  Object.entries(fam).every(([f, cols]) => {
    const hb = {}; for (const c of Object.values(cols)) {
      const [h, s] = hsl(parseC(c));
      const key = s === 0 ? 'grey' : `${String(Math.floor(h / 30) * 30).padStart(3, '0')}-${String(Math.floor(h / 30) * 30 + 29).padStart(3, '0')}`;
      hb[key] = (key in hb ? hb[key] : 0) + 1;
    }
    const got = PAL.hue_buckets_deg[f];
    return Object.keys(got).length === 13 && Object.values(got).reduce((a, x) => a + x, 0) === Object.keys(cols).length
      && Object.entries(got).every(([k, v]) => v === (k in hb ? hb[k] : 0));
  }));
ok('saturation and lightness ranges per family recompute to a tenth of a percent',
  Object.entries(fam).every(([f, cols]) => {
    const ss = Object.values(cols).map((c) => hsl(parseC(c))[1]);
    const ls = Object.values(cols).map((c) => hsl(parseC(c))[2]);
    const R = PAL.ranges[f];
    return R.count === ss.length
      && Math.abs(R.saturation_pct[0] - Math.min(...ss)) < .06 && Math.abs(R.saturation_pct[1] - Math.max(...ss)) < .06
      && Math.abs(R.lightness_pct[0] - Math.min(...ls)) < .06 && Math.abs(R.lightness_pct[1] - Math.max(...ls)) < .06;
  }));
const ND = PAL.near_duplicates;
const allC = Object.entries(fam).flatMap(([f, cols]) => Object.entries(cols).map(([id, c]) => [`${f}:${id}`, parseC(c)]));
const myNear = [];
for (let i = 0; i < allC.length; i++) for (let j = i + 1; j < allC.length; j++) {
  const d = dE(allC[i][1], allC[j][1]); if (d < ND.delta_e_threshold) myNear.push([allC[i][0], allC[j][0], d]);
}
ok(`near-duplicate colours are counted under a declared CIE76 threshold with its reason (${myNear.length} under ${ND.delta_e_threshold})`,
  ND.delta_e_threshold > 2.3 && ND.delta_e_threshold <= 10 && /just-noticeable/.test(ND.why)
  && ND.count === myNear.length && ND.pairs.length === myNear.length
  && ND.pairs.every((p) => myNear.some(([a, b, d]) => a === p.a && b === p.b && near3(d, p.delta_e)))
  && Object.entries(ND.within_family).every(([f, v]) => v === myNear.filter(([a, b]) => a.startsWith(f + ':') && b.startsWith(f + ':')).length)
  && ND.across_families === myNear.filter(([a, b]) => a.split(':')[0] !== b.split(':')[0]).length);
/* staleness: the labels palette this was measured against is the one in
   the labels registry now, by its source stamp and by the bytes read */
const canon = (v) => Array.isArray(v) ? `[${v.map(canon).join(', ')}]`
  : v && typeof v === 'object' ? `{${Object.keys(v).sort().map((k) => `${JSON.stringify(k)}: ${canon(v[k])}`).join(', ')}}`
    : JSON.stringify(v);
ok('the labels palette was read from the labels registry as it stands now (cross-read stamp)',
  LEG.labels_stamp === labels.source_stamp
  && LEG.palette_sha === createHash('sha256').update(canon([labels.palette, labels.palette_roles, labels.paint])).digest('hex').slice(0, 16));

console.log(`surfaces/test: ${n} checks passed — ${Object.keys(cat).length} finishes, `
  + `${Object.keys(wcat).length} walls, ${Object.keys(pats).length} patterns, `
  + `${Object.keys(halls).length} halls, `
  + `${reg.hazards_in_use.length} hazard classes, `
  + `${reg.crafts_in_use.length} crafts, ${sigs.size} halls that read apart`);
