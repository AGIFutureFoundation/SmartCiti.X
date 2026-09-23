/* venue/test.mjs — the measurements taken off a real venue, checked.
 *
 * Three jobs, in order of what would hurt most if it broke:
 *
 *   1. THE LICENCE. CC-BY-4.0 asks for the author, a link to the work, a
 *      link to the licence and an indication of changes. Those are four
 *      fields in the registry and four checks here, and a blank one fails
 *      the suite. Attribution that nothing verifies is attribution that
 *      quietly disappears in the next refactor.
 *   2. THE TIERS. RECORDED is what the file states about itself. Everything
 *      with a dimension on it is DERIVED, because a bounding box computed
 *      from a scan is not a surveyed room. This suite refuses a registry
 *      that promotes one to the other.
 *   3. THE ARITHMETIC. Every ratio, share and total is recomputed here from
 *      its parts rather than read back. Recompute, never re-read.
 *
 * Browser-free and network-free. The source model is NOT in this repository
 * and is not needed to run this: the suite verifies the committed
 * measurement. When the source IS on the machine, one check hashes it
 * against the digest the registry recorded; when it is not, that is printed
 * in full rather than passed over.
 */
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join, extname } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok ' + m); }
                       else { fail++; console.log('  FAIL ' + m); } };
const J = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));

/* Fail closed. A missing field is a broken registry, not a zero. */
const at = (obj, path) => path.split('.').reduce((o, k) => {
  if (o === null || typeof o !== 'object' || !(k in o)) {
    throw new Error(`venue/test.mjs: venue.json is missing ${path} (stopped at "${k}")`);
  }
  return o[k];
}, obj);
/* Every figure in the registry is rounded before it is written, so a
 * recomputation agrees to within the rounding and not closer. The tolerance
 * is relative to the magnitude for that reason, with a floor for the small
 * ones. A tighter eps here would fail on arithmetic that is correct. */
const near = (a, b, eps = 2e-3) =>
  Math.abs(a - b) <= Math.max(eps, Math.abs(b) * eps);

const V = J('venue/registry/venue.json');
const MU = at(V, 'unit.symbol');

console.log('venue/test.mjs');

/* ---- 1. the licence obligation -------------------------------------- */
{
  const A = at(V, 'attribution');
  const nonEmpty = (k) => typeof A[k] === 'string' && A[k].trim().length > 0;

  ok(nonEmpty('author'),
     'CC-BY: the author is named, and named non-empty — "'
     + String(A.author) + '"');
  ok(nonEmpty('source_url') && /^https:\/\/sketchfab\.com\/3d-models\/\S+$/.test(A.source_url),
     'CC-BY: a link to the work itself, not to a search page or a mirror');
  ok(nonEmpty('license_url')
     && /^https?:\/\/creativecommons\.org\/licenses\/by\/4\.0\/?$/.test(A.license_url),
     'CC-BY: a link to the licence deed, and it is the by/4.0 deed the file '
     + 'names rather than a different Creative Commons licence');
  ok(nonEmpty('license_id') && A.license_id === 'CC-BY-4.0',
     'CC-BY: the licence is identified as CC-BY-4.0');
  ok(A.changes_made === true && nonEmpty('changes_indication'),
     'CC-BY: changes are indicated — the fourth thing the licence asks for, '
     + 'and the one most often left out');
  ok(/NOT redistributed|no part of the file is copied/i.test(A.changes_indication)
     && /derived|measurement/i.test(A.changes_indication),
     'and the indication says what was actually done: measurement derived '
     + 'from the work, with the work itself not redistributed');
  ok(nonEmpty('author_profile_url') && /^https:\/\/\S+$/.test(A.author_profile_url)
     && nonEmpty('title') && nonEmpty('license_name'),
     'the supporting fields — author profile, work title, licence name — '
     + 'are present and non-empty too');
  ok(A.tier === 'RECORDED' && /asset\.extras/.test(at(A, 'measured_by')),
     'the attribution is RECORDED, because it is what the file literally '
     + 'says about itself, and it names where in the file it was read from');
}

/* ---- 2. the geometry is not in this repository ---------------------- */
{
  ok(at(V, 'source.in_repository') === false,
     'the registry states that the source model is not in the tree');
  const heavy = [];
  const walk = (d) => {
    for (const e of readdirSync(d, { withFileTypes: true })) {
      if (['node_modules', '.git', '__pycache__', 'dist'].includes(e.name)) continue;
      const p = join(d, e.name);
      if (e.isDirectory()) walk(p);
      else if (['.glb', '.gltf', '.fbx'].includes(extname(e.name).toLowerCase())) heavy.push(p);
    }
  };
  walk(ROOT);
  ok(heavy.length === 0,
     'and the tree is walked to prove it: no .glb, .gltf or .fbx anywhere in '
     + 'the bundle. A 1,008-mesh model against a 196-draw-call ceiling is a '
     + 'measurement, not an asset');
  ok(/draw call/i.test(at(V, 'source.why_not_in_repository')),
     'and the registry says WHY it is measured rather than imported, in the '
     + 'frame-budget terms that actually decided it');
}

/* ---- 3. tiers: what is RECORDED and what is only DERIVED ------------ */
{
  const recorded = [];
  const derived = [];
  (function walk(o, path) {
    if (o === null || typeof o !== 'object') return;
    if (Array.isArray(o)) { o.forEach((v, i) => walk(v, `${path}[${i}]`)); return; }
    if (o.tier === 'RECORDED') recorded.push(path);
    if (o.tier === 'DERIVED') derived.push(path);
    for (const [k, v] of Object.entries(o)) walk(v, path ? `${path}.${k}` : k);
  }(V, ''));

  ok(recorded.length > 0 && derived.length > recorded.length,
     `${recorded.length} records are RECORDED and ${derived.length} are `
     + 'DERIVED — the file states far less than this pack computes, and the '
     + 'registry is shaped that way round');
  ok(recorded.every((p) => ['attribution', 'recorded', 'source'].includes(p)),
     'RECORDED is claimed by exactly three records — the attribution block, '
     + 'the file\'s own counts, and where the file is. Nothing with a '
     + 'dimension on it claims to be recorded: '
     + recorded.join(', '));
  const dims = [];
  (function walk(o) {
    if (o === null || typeof o !== 'object') return;
    if (Array.isArray(o)) { o.forEach(walk); return; }
    for (const [k, v] of Object.entries(o)) {
      if (typeof v === 'number' && /_(?:m|metres|meters)$/.test(k)) dims.push(k);
      walk(v);
    }
  }(V));
  ok(dims.length === 0,
     'not one numeric field in the registry is named in metres — the unit is '
     + 'unresolved and the field names say so rather than hoping the reader '
     + 'reads the caveat');
  ok(!JSON.stringify(V).includes('AI-SYNTHESIZED'),
     'the reserved provenance word does not appear — it belongs to orbis/');
  const boxy = [at(V, 'building'), ...at(V, 'contents_clusters.clusters')];
  ok(boxy.every((b) => /bounding box|BOUNDING BOX/.test(at(b, 'measured_by'))
                    && /not a (?:surveyed|room|wall-to-wall)|NOT a room/i.test(at(b, 'measured_by'))),
     'every record whose numbers are a bounding box says so in its own '
     + 'measured_by, and says in the same breath that a box is not a room');
  ok(derived.every((p) => {
       const rec = p.split(/[.[]/).filter(Boolean).map((s) => s.replace(']', ''))
         .reduce((o, k) => o[k], V);
       return typeof rec.measured_by === 'string' && rec.measured_by.length > 40;
     }),
     'and every DERIVED record carries a measured_by saying how the number '
     + 'was arrived at — a figure with no method is a figure nobody can argue '
     + 'with');
}

/* ---- 4. the unit question, and that it stayed open ------------------ */
{
  const U = at(V, 'unit_scale');
  ok(MU === 'mu' && /NOT a metre/i.test(at(V, 'unit.means')),
     'the published unit is the model unit, and the unit block says outright '
     + 'that it is not a metre');
  ok(at(U, 'resolution') === 'UNRESOLVED',
     'the scale question is recorded as UNRESOLVED rather than settled by '
     + 'assertion');
  const ext = at(V, 'building.extent_' + MU);
  const s = at(U, 'declared_conversion.uniform_scale');
  const honoured = at(U, 'what_honouring_it_gives_if_read_as_metres.building_extent');
  ok(near(honoured[0], ext.x * s, 1e-4) && near(honoured[2], ext.z * s, 1e-4),
     'the "what if we honoured the exporter\'s own 0.01" figure is the '
     + 'extent times that scale, recomputed here — and it is 0.19 across, '
     + 'which is the argument');
  const storey = at(V, 'clear_heights.modal_clear_storey_' + MU);
  ok(at(U, 'conclusion').includes(String(Math.round((ext.x / storey) * 10) / 10)),
     'the conclusion quotes the plan-to-storey ratio this build actually '
     + `computed (${Math.round((ext.x / storey) * 10) / 10}), which is the `
     + 'evidence that no reading of this file is in metres');
  ok(/ESTIMATE|not a measurement/.test(at(U, 'if_someone_wants_metres'))
     && /assumption/.test(at(U, 'if_someone_wants_metres')),
     'the one place a metre figure appears at all is flagged as an estimate '
     + 'resting on an assumption, and says nothing in the registry is '
     + 'computed from it');
  ok(!JSON.stringify({ b: at(V, 'building'), l: at(V, 'levels'),
                       c: at(V, 'clear_heights'), r: at(V, 'ratios') })
      .includes('metre'),
     'and no measurement record mentions metres at all — the word is '
     + 'confined to the block that explains why it cannot be used');
}

/* ---- 5. the arithmetic, recomputed ---------------------------------- */
{
  const B = at(V, 'building');
  const ext = at(B, 'extent_' + MU);
  const lo = at(B, 'min_' + MU), hi = at(B, 'max_' + MU);
  ok(near(ext.x, hi[0] - lo[0]) && near(ext.y, hi[1] - lo[1])
     && near(ext.z, hi[2] - lo[2]),
     'the building extent is its own bounds subtracted, recomputed here '
     + `(${ext.x} x ${ext.y} x ${ext.z} ${MU})`);
  ok(near(at(B, 'plan_footprint_' + MU + '2'), ext.x * ext.z)
     && near(at(B, 'plan_aspect'), Math.max(ext.x, ext.z) / Math.min(ext.x, ext.z)),
     'the plan footprint and aspect are that extent, multiplied and divided');
  ok(at(B, 'fabric_meshes').length + at(B, 'contents_meshes')
     === at(V, 'recorded.counts.meshes'),
     `the fabric/contents split partitions all ${at(V, 'recorded.counts.meshes')} `
     + 'meshes — nothing dropped, nothing counted twice');
  const fs = at(B, 'fabric_split');
  ok(at(fs, 'largest_below') < at(fs, 'threshold_' + MU + '2')
     && at(fs, 'threshold_' + MU + '2') < at(fs, 'smallest_above'),
     `the fabric threshold sits in an empty band (${at(fs, 'largest_below')} `
     + `→ ${at(fs, 'smallest_above')}), so the split is not a knife-edge `
     + 'judgement dressed as a measurement');

  const C = at(V, 'clear_heights');
  const dist = at(C, 'distribution_' + MU);
  const total = dist.reduce((a, [, n]) => a + n, 0);
  ok(total === at(C, 'cells_measured'),
     `the clear-height distribution sums to the ${total} cells it says it `
     + 'measured');
  const top = dist.reduce((a, b) => (b[1] > a[1] ? b : a));
  ok(top[0] === at(C, 'modal_clear_storey_' + MU)
     && near(at(C, 'modal_share'), top[1] / total, 1e-3),
     `the modal storey (${top[0]} ${MU}) and its share are the distribution's `
     + 'own maximum, recomputed');
  ok(at(C, 'modal_share') > 0.9,
     'and that mode carries over nine tenths of the measured cells — a '
     + 'narrow distribution is the only reason this pack is willing to call '
     + 'it a storey height rather than a spread');

  const levels = at(V, 'levels');
  const plates = levels.flatMap((l) => at(l, 'floor_plates'));
  ok(plates.length === at(V, 'counts.floor_plates')
     && levels.length === at(V, 'counts.floor_datum_levels'),
     `${plates.length} floor plates across ${levels.length} datum levels, `
     + 'counted from the records rather than read off the headline');
  ok(plates.every((p) => {
       const w = at(p, 'bbox_width_' + MU), d = at(p, 'bbox_depth_' + MU);
       return near(at(p, 'bbox_fill'), at(p, 'plan_area_' + MU + '2') / (w * d))
         && near(at(p, 'aspect'), Math.max(w, d) / Math.min(w, d));
     }),
     'every floor plate\'s fill and aspect recompute from its own area and '
     + 'box — a plate that fills 0.82 of its bounding box is the measure of '
     + 'how much that box is lying');
  ok(plates.every((p) => at(p, 'clear_height_modes_' + MU)
       .reduce((a, [, n]) => a + n, 0) === at(p, 'clear_height_cells_measured')),
     'and each plate\'s own height tally sums to the cells it measured');

  const K = at(V, 'circulation');
  ok(at(K, 'cells_occupied') + at(K, 'cells_clear') === at(K, 'floor_cells')
     && near(at(K, 'occupancy'), at(K, 'cells_occupied') / at(K, 'floor_cells'), 1e-3),
     'the circulation cells partition the floor plate and the occupancy is '
     + 'that division, recomputed');
  ok(/not a corridor/.test(at(K, 'caveat')),
     'and the record says a clear run is not a corridor — this model has no '
     + 'walled corridors, so nothing here claims to have measured one');

  const O = at(V, 'openings');
  const w = at(O, 'widths_' + MU);
  ok(w.length === at(O, 'members')
     && at(O, 'width_min_' + MU) === w[0]
     && at(O, 'width_max_' + MU) === w[w.length - 1]
     && at(O, 'width_median_' + MU) === w[Math.floor(w.length / 2)],
     `the opening family's ${w.length} widths, and the min, median and max `
     + 'taken from them here rather than trusted');
  ok(at(O, 'identification') === 'INFERRED FROM SHAPE, NOT LABELLED IN THE FILE',
     'the opening family is labelled an inference in capitals, because the '
     + 'file names nothing and a width called a door width is a claim');
  const fams = at(O, 'all_panel_families');
  const chosenShare = at(O, 'floor_on_both_sides') / at(O, 'members');
  const mine = fams.filter((f) => at(f, 'height_' + MU) === at(O, 'family_height_' + MU)
                              && at(f, 'thickness_' + MU) === at(O, 'family_thickness_' + MU));
  ok(mine.length === 1
     && fams.every((f) => at(f, 'both_sides_share') <= chosenShare)
     && fams.some((f) => at(f, 'both_sides_share') < chosenShare)
     && fams.some((f) => at(f, 'members') > at(O, 'members')),
     `all ${fams.length} panel families are published, REJECTED ONES `
     + 'INCLUDED: the chosen set is in the list, nothing in the list beats '
     + 'its floor-on-both-sides score, and the list still holds a family '
     + 'that scores lower and a family that is larger. A selection that '
     + 'hides what it rejected is not a selection anyone can check');
  ok(fams.every((f) => near(at(f, 'both_sides_share'),
                            at(f, 'floor_on_both_sides') / at(f, 'members'), 1e-3)),
     'and every family\'s score is its own count divided by its own size');
  ok(/does not prove it|would pass the same test/.test(at(O, 'what_that_test_means')),
     'and the test\'s own limit is stated beside its result: a glazed bay '
     + 'between two furnished areas would pass it too');

  const CL = at(V, 'contents_clusters');
  const cl = at(CL, 'clusters');
  ok(cl.length === at(V, 'counts.contents_clusters')
     && cl.every((c) => at(c, 'members') >= at(CL, 'min_members')),
     `${cl.length} contents clusters, each at or above the ${at(CL, 'min_members')}-`
     + 'member floor the pack declares');
  ok(cl.every((c) => {
       const cw = at(c, 'bbox_width_' + MU), cd = at(c, 'bbox_depth_' + MU);
       return near(at(c, 'plan_area_' + MU + '2'), cw * cd)
         && near(at(c, 'aspect'), Math.max(cw, cd) / Math.min(cw, cd));
     }),
     'every cluster\'s plan area and aspect recompute from its own box');
  ok(cl.reduce((a, c) => a + at(c, 'members'), 0) <= at(V, 'building.contents_meshes'),
     'the clustered meshes never exceed the contents meshes there are');
  const sens = at(CL, 'gap_sensitivity');
  ok(sens.length > 2
     && sens.every((s, i) => i === 0 || s.clusters <= sens[i - 1].clusters),
     'the gap sensitivity table is published and monotone — a wider gap '
     + `never makes more clusters (${sens[0].clusters} at the tightest gap `
     + `down to ${sens[sens.length - 1].clusters} at the widest)`);
  ok(sens.some((s) => at(s, 'gap_' + MU) === at(CL, 'gap_' + MU)),
     'and the gap the published clusters actually used is one of the rows, '
     + 'so a reader can see what the choice cost');
}

/* ---- 6. the ratios, which are the part that transfers --------------- */
{
  const R = at(V, 'ratios');
  const ext = at(V, 'building.extent_' + MU);
  const storey = at(V, 'clear_heights.modal_clear_storey_' + MU);
  const plate = at(at(V, 'levels')[0], 'floor_plates')[0];
  const shortSide = Math.min(at(plate, 'bbox_width_' + MU), at(plate, 'bbox_depth_' + MU));
  const O = at(V, 'openings');
  const K = at(V, 'circulation');

  ok(near(at(R, 'building_plan_aspect'),
          Math.max(ext.x, ext.z) / Math.min(ext.x, ext.z), 1e-3)
     && near(at(R, 'clear_storey_over_building_short_side'),
             storey / Math.min(ext.x, ext.z), 1e-3),
     'the building proportions recompute from the extent and the storey');
  ok(near(at(R, 'clear_storey_over_largest_plate_short_side'), storey / shortSide, 1e-3)
     && at(R, 'largest_floor_plate_aspect') === at(plate, 'aspect'),
     'the largest floor plate\'s proportions recompute from that plate');
  ok(near(at(R, 'opening_width_over_clear_storey'),
          at(O, 'width_median_' + MU) / storey, 1e-3)
     && near(at(R, 'opening_height_over_clear_storey'),
             at(O, 'family_height_' + MU) / storey, 1e-3),
     'the opening proportions recompute from the opening family and the storey');
  ok(near(at(R, 'furniture_occupancy_of_floor_plate'), at(K, 'occupancy'), 1e-3)
     && near(at(R, 'clear_run_median_over_clear_storey'),
             at(K, 'clear_run_median_' + MU) / storey, 1e-3),
     'and the circulation proportions recompute from the circulation record');
  ok(Object.entries(R).filter(([, v]) => typeof v === 'number')
      .every(([, v]) => v > 0 && v < 100),
     'every published ratio is a positive number of sane magnitude — a ratio '
     + 'that came out as a raw dimension would show up here');
  ok(/does not care what the unit is/.test(at(R, 'why_these_are_the_useful_ones')),
     'and the record says why the ratios are the useful part: they survive a '
     + 'unit this file never established');
}

/* ---- 7. the prose agrees with the arithmetic ------------------------ */
{
  const H = at(V, 'honesty');
  ok(at(H, 'the_unit_is_not_metres') === at(V, 'unit_scale.conclusion'),
     'the honesty block quotes the unit conclusion verbatim rather than '
     + 'paraphrasing it into something weaker');
  ok(at(H, 'the_model_is_partial').includes(String(at(V, 'clear_heights.cells_measured')))
     && at(H, 'the_model_is_partial').includes(String(at(V, 'circulation.floor_cells'))),
     'the note that the model is only partly roofed quotes both cell counts '
     + 'this build produced, so the sentence cannot drift from the table');
  ok(at(H, 'the_clusters_depend_on_a_threshold')
       .includes(String(at(V, 'contents_clusters.gap_sensitivity')[0].clusters)),
     'and the note about clustering quotes the sensitivity table it is '
     + 'describing');
  ok(at(H, 'the_openings_are_an_inference') === at(V, 'openings.identification'),
     'and the note about the openings is the openings record\'s own label');
}

/* ---- 8. stamp, version, and the source itself ----------------------- */
{
  const src = readFileSync(join(HERE, 'build.py'));
  ok(createHash('sha256').update(src).digest('hex').slice(0, 16)
     === at(V, 'source_stamp'),
     'the registry was built from the current builder (stamp check)');
  ok(at(V, 'pack') === 'venue'
     && at(V, 'pack_version') === J('pack/manifest.json').pack_version,
     'one bundle version, read from the manifest rather than typed here');

  const P = at(V, 'source.path');
  const here = existsSync(P);
  const digest = here ? createHash('sha256').update(readFileSync(P)).digest('hex') : null;
  if (!here) {
    console.log('  ---- SOURCE NOT ON THIS MACHINE ----');
    console.log('  ' + P);
    console.log('  Nothing below was re-measured. The committed registry is');
    console.log('  the measurement, and its recorded digest could not be');
    console.log('  checked against the file in this run.');
    console.log('  ------------------------------------');
  }
  ok(!here || digest === at(V, 'recorded.file_sha256'),
     here
       ? 'the source model on this machine hashes to the digest the registry '
         + 'recorded, so these measurements are of THIS file'
       : 'the source model is not on this machine — the digest check was '
         + 'skipped and said so above, loudly, rather than passing quietly');
  ok(!here || statSync(P).size === at(V, 'recorded.file_bytes'),
     here
       ? `and its byte length is the recorded ${at(V, 'recorded.file_bytes')}`
       : 'and the byte-length check was skipped with it');
  const c = at(V, 'recorded.counts');
  ok(c.meshes > 0 && c.nodes > c.meshes && c.materials > 0 && c.accessors > 0,
     `the recorded counts are a coherent glTF: ${c.meshes} meshes under `
     + `${c.nodes} nodes with ${c.materials} materials and ${c.accessors} `
     + 'accessors');
}

if (fail) {
  console.log(`\n${pass} ok, ${fail} failed`);
  process.exit(1);
}
console.log(`\nvenue: ${pass} checks passed - the four CC-BY fields are `
  + `present and non-blank, ${at(V, 'recorded.counts.meshes')} meshes stayed `
  + `out of the tree, the unit is published UNRESOLVED in ${MU} rather than `
  + `asserted in metres, and every dimension, share and ratio recomputed `
  + `from its parts.`);
process.exit(0);
