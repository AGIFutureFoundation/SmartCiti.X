/**
 * Exterior kit registry verification.
 *
 * The claim of this pack is arithmetic, so most of it is checkable without
 * rendering anything.
 *
 * THE TRIANGLE BUDGETS ARE RECOMPUTED, not trusted. Every piece publishes a
 * primitive recipe and a formula for what a primitive costs; this file
 * applies the formula to the recipe and requires the answer to be the
 * number the piece declares. A budget nobody can derive is a wish.
 *
 * THE MATERIALS ARE RESOLVED AGAINST THE PAGE. Every `material` value must
 * name something `web/build_3d.py` actually declares - a `mat.*` singleton
 * or a key of what `fabricOf()` returns - because a kit that invents a
 * material has quietly added a draw call per district and a second place
 * where a colour lives.
 *
 * THE DRAW-CALL CEILING IS READ, NOT TYPED. `web/eval_scene.mjs` measured
 * the campus view at 273 draw calls and holds it to 1.25x that. This file
 * re-reads both numbers and re-derives the ceiling, so the kit cannot pass
 * by publishing a ceiling of its own choosing. The same goes for the
 * triangle headroom and for the campus the harness actually drives to.
 *
 * AND THE ANTI-PATTERN IS CHECKED BY ARITHMETIC. The reference block that
 * prompted this pack paid one material, and therefore one draw call, per
 * mesh: 93 for one street. A kit that did that here would place 1,117
 * pieces for 1,117 draw calls. The check below requires at least fifty
 * pieces per draw call, which no per-piece-mesh design can reach.
 *
 * The last group is about what is NOT here. No hall is named, because
 * placement is derived from rooflines and facade patterns the registries
 * already own. No URL is named. No third party's work is named. And the
 * honesty block has to say, in its own words, that the whole-campus
 * arithmetic is a prediction rather than a measurement - because nothing
 * in this pack has been drawn yet.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const url = (p) => new URL(p, import.meta.url);
const reg = JSON.parse(readFileSync(url('./registry/kit.json')));
const manifest = JSON.parse(readFileSync(url('../pack/manifest.json')));
const page = readFileSync(url('../web/build_3d.py'), 'utf8');
const evalSrc = readFileSync(url('../web/eval_scene.mjs'), 'utf8');
const world = JSON.parse(readFileSync(url('../world/registry/world.json')));
const districts = JSON.parse(readFileSync(url('../unions/registry/districts.json'))).districts;
const campuses = JSON.parse(readFileSync(url('../unions/registry/campuses.json'))).campuses;
const finishes = JSON.parse(readFileSync(url('../surfaces/registry/finishes.json')));
const unions = JSON.parse(readFileSync(url('../unions/registry/unions.json'))).unions;

const pieces = Object.entries(reg.pieces);
const place = Object.entries(reg.placement);
const budgets = Object.entries(reg.budget.campuses);
const main = reg.budget.campuses[reg.budget.budgeted_campus];
const payload = JSON.stringify(reg);

const one = (re, s) => { const m = s.match(re); return m ? m : null; };

/* ------------------------------------------------------------- the shape --- */
ok('the pack carries the same header every pack in this bundle carries',
  reg.pack === 'smartcitix-trade-craft-academy-kit'
  && reg.pack_version === manifest.pack_version
  && /^\d{4}-\d{2}-\d{2}$/.test(reg.built) && reg.source_stamp.length === 16);
ok('the family set is closed, every family has at least one piece, and no piece invents one',
  new Set(reg.vocabulary.families).size === reg.vocabulary.families.length
  && pieces.every(([, p]) => reg.vocabulary.families.includes(p.family))
  && reg.vocabulary.families.every((f) =>
    pieces.some(([, p]) => p.family === f)));
ok('every piece is a name, a size in three metres, a family and a recipe',
  pieces.every(([, p]) => p.name.length > 3 && p.size_m.length === 3
    && p.size_m.every((v) => typeof v === 'number' && v >= 0.05 && v <= 16)
    && Array.isArray(p.primitives) && p.primitives.length > 0
    && p.primitives.every((q) => q.note && q.note.length > 8)));

/* ------------------------------------------------ the budgets, recomputed --- */
const cost = (prims) => prims.reduce((a, q) => {
  if (q.shape === 'box') return a + 12 * q.n;
  if (q.shape === 'cylinder') return a + q.n * (q.capped ? 4 * q.segments : 2 * q.segments);
  return NaN;                       // an unknown shape poisons the sum
}, 0);
ok('every declared tri_budget is exactly what its own primitive recipe costs under the published formula',
  pieces.every(([, p]) => cost(p.primitives) === p.tri_budget));
ok('the published formula is the one applied: a box is 12, a capped cylinder 4N, an open one 2N',
  /six quads.*12 triangles/.test(reg.tri_formula.box)
  && /4N triangles/.test(reg.tri_formula.cylinder_capped)
  && /2N triangles/.test(reg.tri_formula.cylinder_open));
ok('no piece is built from a primitive this bundle cannot make in the browser',
  pieces.every(([, p]) => p.primitives.every((q) =>
    (q.shape === 'box') || (q.shape === 'cylinder' && q.segments >= 4 && q.segments <= 12))));
ok('every piece sits under the measured reference block\'s 104-triangle median mesh',
  reg.reference.block_median_tris === 104
  && pieces.every(([, p]) => p.tri_budget <= reg.reference.block_median_tris));
ok('every tri_budget carries a why, and every why cites that measured median',
  pieces.every(([, p]) => p.tri_why.length > 40
    && (p.tri_why.includes('median') || p.tri_why.includes('104'))));

/* --------------------------------------------- materials the page already has --- */
const matKeys = [...one(/\nconst mat = \{([\s\S]*?)\n\};/, page)[1]
  .matchAll(/^ {2}(\w+):/gm)].map((m) => m[1]);
const fabKeys = [...one(/\n {2}fabMats = \{([\s\S]*?)\n {2}\};/, page)[1]
  .matchAll(/^ {4}(\w+)[:,]/gm)].map((m) => m[1]);
const vocab = new Set([...matKeys.map((k) => `mat.${k}`),
  ...fabKeys.map((k) => `fabric.${k}`), 'district-hue']);
ok('every material a piece wears is one web/build_3d.py ALREADY declares - this pack invents none',
  pieces.every(([, p]) => vocab.has(p.material))
  && reg.vocabulary.materials.every((m) => vocab.has(m))
  && reg.vocabulary.materials.length === vocab.size);
ok('no piece wears the district hue: that colour belongs to the hall envelope band, not to a prop on it',
  pieces.every(([, p]) => p.material !== 'district-hue'));
ok('this pack publishes no colour of its own - every colour stays in the registry that owns it',
  !/#[0-9a-fA-F]{6}/.test(payload)
  && !/\b(rgb|hsl)\(/.test(payload) && !/0x[0-9a-fA-F]{6}/.test(payload));

/* ------------------------------------------------------- how it gets drawn --- */
ok('every piece declares how it reaches the screen, from a closed set, with a reason',
  pieces.every(([, p]) => reg.vocabulary.merges.includes(p.merges)
    && p.merge_why.length > 30));
ok('nothing takes its own mesh, and the policy says what would earn one',
  pieces.filter(([, p]) => p.merges === 'own-mesh').length === 0
  && reg.counts.own_mesh_pieces === 0
  && /raycast/.test(reg.vocabulary.own_mesh_policy)
  && /userData\.slug/.test(reg.vocabulary.own_mesh_policy));
const bld = one(/function building\(h, style, g, pool, ox = 0, oz = 0\) \{([\s\S]*?)\n\}\n/, page)[1];
const pooledByPage = new Set([...bld.matchAll(/\badd\(([A-Za-z_][\w.]*),/g)]
  .map((m) => ({ hueMat: 'district-hue', 'fab.trim': 'fabric.trim', 'fab.roof': 'fabric.roof', 'fab.wall': 'fabric.wall' })[m[1]] ?? m[1]));
ok('the materials this pack gets for free are exactly the ones building() already pools - read from the page, not listed here',
  reg.vocabulary.already_pooled.length === pooledByPage.size
  && reg.vocabulary.already_pooled.every((m) => pooledByPage.has(m)));
ok('the free materials really are free: every district charges only for the pooled materials the page was not already carrying',
  budgets.every(([, b]) => Object.values(b.per_district).every((d) =>
    d.new_draw_calls === d.pooled_materials
      .filter((m) => !reg.vocabulary.already_pooled.includes(m)).length
    && d.free_materials.every((m) => reg.vocabulary.already_pooled.includes(m)))));

/* ------------------------------------------------- placement, derived not typed --- */
const roofVocab = new Set([...Object.values(
  Object.fromEntries([...one(/const STYLE_OF = \{([\s\S]*?)\};/, page)[1]
    .matchAll(/(\w[\w-]*):\s*'([a-z]+)'/g)].map((m) => [m[1], m[2]]))),
...Object.values(world.fabric).map((f) => f.roof)]);
const faceVocab = new Set(Object.values(world.fabric).map((f) => f.facade));
ok('the roofline vocabulary is the page\'s STYLE_OF plus the world registry\'s, and nothing else',
  reg.vocabulary.rooflines.length === roofVocab.size
  && reg.vocabulary.rooflines.every((r) => roofVocab.has(r)));
ok('the facade vocabulary is the world registry\'s, and every one of them is a pattern surfaces/ already declares',
  reg.vocabulary.facades.length === faceVocab.size
  && reg.vocabulary.facades.every((f) => faceVocab.has(f) && f in finishes.patterns));
ok('every family attaches to a wall from the closed set, measured by a run that wall actually has',
  place.length === reg.vocabulary.families.length
  && place.every(([f, r]) => reg.vocabulary.families.includes(f)
    && reg.vocabulary.walls.includes(r.wall)
    && reg.vocabulary.run_of_wall[r.wall].includes(r.run)
    && r.run in reg.vocabulary.runs));
ok('every family names a datum and an offset that datum allows',
  place.every(([, r]) => reg.vocabulary.datums.includes(r.datum)
    && (r.datum === 'grade' ? r.offset_m === 0
      : r.datum === 'eaves' ? Math.abs(r.offset_m) <= 0.5
        : r.offset_m >= 0 && r.offset_m <= reg.envelope.shortest_hall_m)));
ok('every family admits a non-empty subset of the real rooflines and the real facades, and says why it goes there',
  place.every(([, r]) => r.rooflines.length && r.facades.length
    && r.rooflines.every((x) => roofVocab.has(x))
    && r.facades.every((x) => faceVocab.has(x))
    && r.why.length > 60));
ok('every roofline and every facade this world can build is admitted by something - no city gets bare buildings',
  [...roofVocab].every((x) => place.some(([, r]) => r.rooflines.includes(x)))
  && [...faceVocab].every((x) => place.some(([, r]) => r.facades.includes(x))));
ok('NO HALL IS NAMED anywhere in this pack: placement is derived from roofline and facade, never typed per building',
  unions.every((h) => !new RegExp(`"[^"]*\\b${h.slug}\\b[^"]*"`).test(payload)));
ok('the roofline this pack budgets each district at is the one the page itself resolves for it',
  budgets.every(([ck, b]) => Object.entries(b.per_district).every(([k, d]) => {
    const styled = [...one(/const STYLE_OF = \{([\s\S]*?)\};/, page)[1]
      .matchAll(/(\w[\w-]*):\s*'([a-z]+)'/g)].find((m) => m[1] === k);
    return d.roofline === (styled ? styled[2] : world.fabric[ck].roof);
  })));

/* ------------------------------------------------ the envelope, read from the page --- */
const env = one(/const dep = Math\.max\(h\.depth, ([\d.]+)\), wid = ([\d.]+);/, page);
const hf = one(/const hgt = ([\d.]+) \+ \(h\.depth % (\d+)\) \* (\.[\d]+);/, page);
ok('the envelope this kit hangs on is the page\'s own, re-read here rather than restated',
  reg.envelope.depth_floor_m === Number(env[1]) && reg.envelope.width_m === Number(env[2])
  && reg.envelope.height_formula === `${Number(hf[1])} + (depth % ${Number(hf[2])}) * ${Number('0' + hf[3])}`
  && reg.envelope.shortest_hall_m === Number(hf[1]));
ok('nothing mounted on a wall reaches over the top of the shortest wall the page builds',
  pieces.every(([, p]) => reg.placement[p.family].datum !== 'wall'
    || reg.placement[p.family].offset_m + p.size_m[1] <= reg.envelope.shortest_hall_m));
ok('every run measure resolves to metres of a real wall: nothing is measured against a dimension the envelope lacks',
  Object.keys(reg.vocabulary.runs).every((r) =>
    Object.values(reg.vocabulary.run_of_wall).some((l) => l.includes(r)))
  && Object.values(reg.vocabulary.run_of_wall).flat()
    .every((r) => r in reg.vocabulary.runs));

/* ------------------------------------------------------------- the budget --- */
const base = Object.fromEntries([...one(/const BASE = \{([\s\S]*?)\n\};/, evalSrc)[1]
  .matchAll(/(\w+):\s*\{\s*calls:\s*([\d_]+),\s*tris:\s*([\d_]+),\s*meshes:\s*([\d_]+)\s*\}/g)]
  .map((m) => [m[1], { calls: +m[2].replace(/_/g, ''), tris: +m[3].replace(/_/g, ''), meshes: +m[4].replace(/_/g, '') }]));
const callHead = Number(one(/const CALL_HEADROOM = ([\d.]+);/, evalSrc)[1]);
const triHead = Number(one(/const TRI_HEADROOM = ([\d.]+);/, evalSrc)[1]);
ok('the measured baseline in this pack is the harness\'s own, view for view',
  JSON.stringify(reg.budget.measured_baseline.views) === JSON.stringify(base)
  && reg.budget.measured_baseline.call_headroom === callHead
  && reg.budget.measured_baseline.tri_headroom === triHead);
ok('the campus budgeted is the campus the harness actually drives to, so the baseline is a measurement of THIS campus',
  reg.budget.budgeted_campus
    === one(/__tc3dDo\('view', 'campus:([a-z-]+)'\)/, evalSrc)[1]
  && reg.budget.budgeted_campus in campuses);
ok('the draw-call ceiling is derived from the harness, not published by this pack',
  reg.budget.draw_call_ceiling === Math.round(base.campus.calls * callHead) - base.campus.calls
  && reg.budget.triangle_headroom_total === Math.trunc(base.campus.tris * triHead) - base.campus.tris
  && reg.budget.triangle_ceiling
     === Math.trunc(reg.budget.triangle_headroom_total * reg.budget.triangle_share));
ok('the whole kit at the budgeted campus stays inside that draw-call ceiling, and so does the worst campus',
  main.draw_calls <= reg.budget.draw_call_ceiling
  && reg.budget.worst_campus_draw_calls
     === Math.max(...budgets.map(([, b]) => b.draw_calls))
  && reg.budget.worst_campus_draw_calls <= reg.budget.draw_call_ceiling);
ok('and inside the declared share of the triangle headroom, which is a split somebody decided rather than a leftover',
  main.triangles <= reg.budget.triangle_ceiling
  && reg.budget.triangle_share > 0 && reg.budget.triangle_share < 1
  && /props/.test(reg.budget.triangle_ceiling_why));
ok('the draw-call total is the pooled materials per district plus one per instanced family, and nothing else',
  budgets.every(([, b]) => b.draw_calls
    === Object.values(b.per_district).reduce((a, d) => a + d.new_draw_calls, 0)
      + b.instanced_families.length
    && b.own_mesh_draw_calls === 0
    && b.instanced_draw_calls === b.instanced_families.length
    && b.pooled_draw_calls + b.instanced_draw_calls === b.draw_calls));
ok('THE ANTI-PATTERN IS REFUSED BY ARITHMETIC: a draw call per piece could never reach fifty pieces per call',
  main.pieces / main.draw_calls >= 50
  && reg.counts.pieces_per_draw_call === Math.round(main.pieces / main.draw_calls * 10) / 10
  && reg.reference.block_materials === reg.reference.block_meshes
  && /export artefact/.test(reg.reference.anti_pattern));
ok('every campus budget adds up: its districts\' pieces and triangles are its own',
  budgets.every(([, b]) =>
    b.pieces === Object.values(b.per_district).reduce((a, d) => a + d.pieces, 0)
    && b.triangles === Object.values(b.per_district).reduce((a, d) => a + d.triangles, 0)
    && b.pieces === Object.values(b.by_family).reduce((a, v) => a + v, 0)
    && b.halls === Object.values(b.per_district).reduce((a, d) => a + d.halls, 0)));
ok('every district budgeted holds the halls the union registry gives it, and every campus its own districts',
  budgets.every(([ck, b]) => {
    const ks = campuses[ck].districts;
    return ks.length === b.districts && ks.length === Object.keys(b.per_district).length
      && ks.every((k) => b.per_district[k].halls === districts[k].halls.length);
  }));
ok('the per-hall loadout VARIES - a kit that put the same pieces on every hall would add detail without adding identity',
  main.distinct_hall_loadouts > 1
  && main.pieces_per_hall_min * main.halls <= main.pieces
  && main.pieces <= main.pieces_per_hall_max * main.halls
  && new Set(Object.values(main.per_district).map((d) => d.roofline)).size > 1);
ok('every family this pack declares actually lands somewhere on some campus',
  reg.vocabulary.families.every((f) =>
    budgets.some(([, b]) => b.by_family[f] > 0)));
ok('the count rules are two modes and no third, and a rate is resolved by a stated policy rather than a hidden minimum',
  Object.entries(reg.counts_rules).every(([pid, c]) => pid in reg.pieces
    && ((c.mode === 'per_hall' && c.n >= 1 && c.n <= 8)
      || (c.mode === 'per_run_m' && c.every_m >= 1 && c.every_m <= 40)))
  && Object.keys(reg.counts_rules).length === pieces.length
  && /ceil/.test(reg.vocabulary.count_policy)
  && /no third mode/.test(reg.vocabulary.count_policy));

/* -------------------------------------------------- what the kit admits ----- */
ok('the pack carries the SCHEMATIC provenance word and says what schematic costs it',
  /^SCHEMATIC: /.test(reg.honesty.status)
  && /not a measurement of one/.test(reg.honesty.status)
  && /no standard is\s+referenced/.test(reg.honesty.status));
ok('it states the limit with the capability: nothing here is a construction detail',
  /nobody should\s+build anything from it/.test(reg.honesty.not_a_construction_detail)
  && /no fixing centres/.test(reg.honesty.not_a_construction_detail)
  && /no loads/.test(reg.honesty.not_a_construction_detail));
/* The second clause of this check used to require the sentence "Nothing
   here has been drawn yet". It is drawn now, so that clause was asserting
   something false and had to go. The first and third clauses did not: the
   whole-campus figure is STILL a prediction of what the placement rules
   would cost, and it must still name the campus it was reckoned against.
   What replaces the stale clause is the thing that makes the prediction
   answerable — the page's own probe, which reports what was really built
   beside what was predicted here. */
ok('the whole-campus arithmetic admits it is a PREDICTION, names the one '
  + 'campus it was reckoned against, and names the probe that can now '
  + 'check it against the drawing',
  /PREDICTION, not a measurement/.test(reg.honesty.budget_limit)
  && /__tc3dKit\(\)/.test(reg.honesty.budget_limit)
  && /kitDress\(\)/.test(reg.honesty.budget_limit)
  && reg.honesty.budget_limit.includes(reg.budget.budgeted_campus));
ok('the reference figures admit they were measured elsewhere, on files this repo does not contain',
  reg.reference.provenance === 'MEASURED-ELSEWHERE'
  && /outside this repository/.test(reg.reference.how)
  && /quoted, not verified here/.test(reg.reference.how)
  && /is reproduced in this pack/.test(reg.reference.not_vendored));
ok('AI-SYNTHESIZED appears exactly once, in the sentence saying it is orbis\'s word and not this pack\'s',
  (payload.match(/AI-SYNTHESIZED/g) ?? []).length === 1
  && /AI-SYNTHESIZED is orbis\//.test(reg.honesty.provenance));
ok('nothing in the payload is a URL - this kit loads nothing and links nowhere',
  !/https?:\/\//.test(payload));
ok('no third party\'s work is named, and no third party\'s asset is vendored',
  !/grove street|gta|rockstar|san andreas|sketchfab/i.test(payload)
  && /loads no mesh, no texture, no model and no file/.test(reg.honesty.no_assets));

/* ------------------------------------------------------- the page contract --- */
ok('the page contract names every existing function it tells the page to reuse, and each one still exists',
  ['flushParts', 'flushBeacons', 'fabricOf', 'buildCampus', 'building',
    'spinBeacons', 'disposeOf', 'hueMatOf']
    .every((f) => page.includes(`function ${f}(`))
  && ['flushParts', 'flushBeacons', 'fabricOf', 'buildCampus', 'building',
    'spinBeacons', 'disposeOf'].every((f) => payload.includes(f)));
ok('it forbids the duplicates this bundle lints for by name',
  /second STYLE_OF/.test(reg.page_contract.never_duplicate)
  && /second merge helper/.test(reg.page_contract.never_duplicate)
  && /second raycast target/.test(reg.page_contract.never_duplicate)
  && /must never be hoverable/.test(reg.page_contract.never_duplicate));
ok('it says the cylinders still have to go through the same pool, which is the whole point',
  /flushParts is the only door/.test(reg.page_contract.pools)
  && /new draw call per piece/.test(reg.page_contract.cylinders));
ok('it keeps the beacons out of it: the instanced pieces must not borrow the spinning ones\' state',
  /must NOT reuse/.test(reg.page_contract.instances)
  && /beaconInst/.test(reg.page_contract.instances)
  && /spinBeacons/.test(reg.page_contract.instances));
ok('every clause of the contract says something: none is a stub',
  Object.values(reg.page_contract).every((v) => typeof v === 'string' && v.length > 80)
  && Object.keys(reg.page_contract).length >= 9);

/* ------------------------------------------- what was found in the page ----- */
ok('the two findings about web/build_3d.py are recomputed from it, not remembered',
  (() => {
    const styled = new Set([...one(/const STYLE_OF = \{([\s\S]*?)\};/, page)[1]
      .matchAll(/(\w[\w-]*):\s*'([a-z]+)'/g)].map((m) => m[1]));
    const unop = Object.keys(districts).filter((k) => !styled.has(k)).sort();
    // The constant may be GONE - it was, once this finding was acted on -
    // and a findings check whose subject gets fixed must report the fix,
    // not crash. This one did crash: `one()` returned null and the next
    // line read [1] off it, so a repaired page failed the suite with a
    // TypeError instead of a sentence.
    const fb = page.match(/const FABRIC_FALLBACK = \{([\s\S]*?)\};/);
    const present = fb !== null;
    const spec = present
      ? Object.fromEntries([...fb[1].matchAll(/(\w+):\s*'([^']+)'/g)]
          .map((m) => [m[1], m[2]]))
      : null;
    const twins = present
      ? Object.entries(world.fabric)
          .filter(([, f]) => Object.entries(spec).every(([k, v]) => f[k] === v))
          .map(([k]) => k).sort()
      : [];
    if (reg.page_findings.fabric_fallback_present !== present) return false;
    return JSON.stringify(reg.page_findings.unopinionated_districts) === JSON.stringify(unop)
      && reg.page_findings.roofline_fallback_reachable === (unop.length > 0)
      && JSON.stringify(reg.page_findings.fabric_fallback_duplicates) === JSON.stringify(twins);
  })());
ok('and they are reported, not enforced: a defect in somebody else\'s file does not fail this build',
  /reported rather than enforced/.test(reg.page_findings.note)
  && /does not fail on them/.test(reg.page_findings.note));

/* -------------------------------------------------------------- the counts --- */
ok('the counts the registry publishes are the counts it actually holds',
  reg.counts.families === reg.vocabulary.families.length
  && reg.counts.pieces === pieces.length
  && reg.counts.pooled_pieces === pieces.filter(([, p]) => p.merges === 'pooled').length
  && reg.counts.instanced_pieces === pieces.filter(([, p]) => p.merges === 'instanced').length
  && reg.counts.pieces === reg.counts.pooled_pieces + reg.counts.instanced_pieces + reg.counts.own_mesh_pieces
  && reg.counts.boxes === pieces.reduce((a, [, p]) => a + p.primitives.filter((q) => q.shape === 'box').reduce((x, q) => x + q.n, 0), 0)
  && reg.counts.cylinders === pieces.reduce((a, [, p]) => a + p.primitives.filter((q) => q.shape === 'cylinder').reduce((x, q) => x + q.n, 0), 0)
  && reg.counts.primitives === reg.counts.boxes + reg.counts.cylinders);
ok('the triangle statistics are the statistics of the pieces, not a summary typed beside them',
  (() => {
    const b = pieces.map(([, p]) => p.tri_budget).sort((x, y) => x - y);
    const mid = b.length % 2 ? b[(b.length - 1) / 2] : (b[b.length / 2 - 1] + b[b.length / 2]) / 2;
    return reg.counts.tri_budget_min === b[0] && reg.counts.tri_budget_max === b[b.length - 1]
      && reg.counts.tri_budget_median === mid
      && reg.counts.tri_budget_sum === b.reduce((a, v) => a + v, 0);
  })());
ok('the campus counts are the campus budget, and the rule counts are the rules',
  reg.counts.campus_pieces === main.pieces
  && reg.counts.campus_triangles === main.triangles
  && reg.counts.campus_draw_calls === main.draw_calls
  && reg.counts.campus_halls === main.halls
  && reg.counts.campuses_budgeted === budgets.length
  && reg.counts.halls_budgeted === budgets.reduce((a, [, b]) => a + b.halls, 0)
  && reg.counts.districts === Object.keys(districts).length
  && reg.counts.per_hall_count_rules + reg.counts.per_metre_count_rules === pieces.length
  && reg.counts.materials_used === new Set(pieces.map(([, p]) => p.material)).size
  && reg.counts.materials_free === new Set(pieces.map(([, p]) => p.material)
    .filter((m) => reg.vocabulary.already_pooled.includes(m))).size);

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
  const said = reg.reference.how.match(/\b(one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:downloaded\s+)?reference/i);
  ok('the number of reference models this pack names is the number '
    + `assets/REFERENCE.md actually tables (${rows})`,
    rows > 0 && said !== null && NUM[said[1].toLowerCase()] === rows);
}

console.log(`kit/test: ${n} checks passed — ${pieces.length} pieces over `
  + `${reg.counts.families} families (${reg.counts.boxes} boxes, `
  + `${reg.counts.cylinders} cylinders; median ${reg.counts.tri_budget_median} `
  + `triangles against the reference's ${reg.reference.block_median_tris}); `
  + `at ${reg.budget.budgeted_campus}, ${main.halls} halls carry `
  + `${main.pieces.toLocaleString('en-US')} pieces and `
  + `${main.triangles.toLocaleString('en-US')} triangles for `
  + `${main.draw_calls} draw calls — ${reg.counts.pieces_per_draw_call} pieces `
  + `per call, against ceilings of ${reg.budget.draw_call_ceiling} calls and `
  + `${reg.budget.triangle_ceiling.toLocaleString('en-US')} triangles read from web/eval_scene.mjs`);
