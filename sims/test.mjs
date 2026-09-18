/**
 * Simulator registry verification.
 *
 * A simulator is a curriculum claim: it names halls, a skill per hall, and
 * a rubric a machine can grade. Every claim is checked against the packs
 * that own those truths, and the scoring contract — deterministic, nothing
 * narrative — is asserted in the record rather than assumed.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const reg = JSON.parse(readFileSync(new URL('./registry/sims.json', import.meta.url)));
const unions = JSON.parse(readFileSync(new URL('../unions/registry/unions.json', import.meta.url)));
const skills = new Set(JSON.parse(readFileSync(
  new URL('../pack/registry/skills.json', import.meta.url))).skills.map((s) => s.skill_id));
const slugs = new Set(unions.unions.map((u) => u.slug));

const sims = reg.sims;
ok('eleven simulators ship: four lifting, aerial and earthmoving machines, a driving seat, six process benches',
  Object.keys(sims).length === 11
  && Object.values(sims).filter((s) => s.kind === 'machine').length === 4
  && Object.values(sims).filter((s) => s.kind === 'driving').length === 1
  && Object.values(sims).filter((s) => s.kind === 'process').length === 6);
ok('every sim carries a task, controls with keys and actions, and 3+ rubric axes',
  Object.values(sims).every((s) => s.task.length > 20
    && s.controls.length >= 3 && s.controls.every((c) => c.keys && c.action)
    && s.rubric.length >= 3 && s.rubric.every((r) => r.axis && r.measure && r.pass)));
ok('every rubric measures state, and at least one axis is pass-gated per sim',
  Object.values(sims).every((s) =>
    s.rubric.some((r) => r.pass !== 'informational')));
ok('every bound hall exists in the union roster',
  Object.values(sims).every((s) => s.halls.every((h) => slugs.has(h))));
ok('every hall binding resolves to a real skill in the graph',
  Object.entries(reg.hall_bindings).every(([hall, list]) =>
    list.every((b) => skills.has(b.skill_id)
      && b.skill_id.startsWith(hall + '.'))));
ok('the bindings table is exactly the sims\' hall lists, inverted',
  (() => {
    const want = {};
    for (const [id, s] of Object.entries(sims))
      for (const h of s.halls) (want[h] ??= []).push(id);
    return JSON.stringify(Object.keys(want).sort())
      === JSON.stringify(Object.keys(reg.hall_bindings).sort())
      && Object.entries(want).every(([h, ids]) =>
          JSON.stringify(ids.sort()) === JSON.stringify(
            reg.hall_bindings[h].map((b) => b.sim).sort()));
  })());
ok('the operator seats train where they belong: crane hall lifts, teamsters drive, shoring digs, welders weld',
  sims['crane-lift'].halls.includes('crane-ops')
  && sims['forklift-run'].halls.includes('teamsters')
  && sims['excavator-trench'].halls.includes('shoring')
  && sims['weld-bead'].halls.includes('welders'));
ok('the bead task teaches heat discipline: a pass demands zero burn-throughs, in band',
  /burns through/.test(sims['weld-bead'].task)
  && sims['weld-bead'].rubric.some((r) => r.axis === 'burns' && r.pass === '== 0')
  && sims['weld-bead'].rubric.some((r) => r.axis === 'band' && r.pass === '>= 90'));
ok('the bay task teaches sequence discipline: scaffold hall builds it, zero refusals to pass',
  sims['scaffold-bay'].halls.includes('scaffold')
  && /legal order/.test(sims['scaffold-bay'].task)
  && sims['scaffold-bay'].rubric.some((r) =>
      r.axis === 'sequence' && r.pass === '== 0'));
ok('the signal call pairs the crew: riggers call the crane hall\'s machine, stop ends every card',
  sims['rigging-signals'].halls.includes('riggers')
  && sims['rigging-signals'].halls.includes('crane-ops')
  && sims['rigging-signals'].rubric.some((r) => r.axis === 'wrong' && r.pass === '== 0')
  && sims['rigging-signals'].scenarios.every((x) =>
      x.params.seq[x.params.seq.length - 1] === 'stop'));
ok('the chart is honest and the pick lists respect it: capacity falls with radius, every pick radius on the chart, every list carries an overload to refuse',
  (() => {
    const c = sims['load-chart'].chart;
    const cap = Object.fromEntries(c);
    return c.every(([r, t], i) => i === 0
        || (r > c[i - 1][0] && t < c[i - 1][1]))
      && sims['load-chart'].scenarios.every((x) =>
          x.params.picks.every((p) => p.r in cap)
          && x.params.picks.some((p) => p.w > cap[p.r]))
      && sims['load-chart'].rubric.some((r) =>
          r.axis === 'overloads' && r.pass === '== 0');
  })());
ok('every seat carries its five-point walkaround, and the walkaround is honestly NOT a gate',
  Object.values(sims).every((s) => s.walkaround?.length === 5
    && new Set(s.walkaround.map((w) => w.id)).size === 5
    && s.walkaround.every((w) => w.point && w.check.length > 15))
  && /not a gate/.test(reg.honesty.walkaround)
  && /changes no score/.test(reg.honesty.walkaround)
  && /not an equipment inspection record/.test(reg.honesty.walkaround));
ok('the pressure washer teaches containment-first discipline: painters/laborers/hazmat train it, coverage demands 95%, damage and containment are pass-gated',
  sims['pressure-washer'].halls.includes('painters')
  && sims['pressure-washer'].halls.includes('laborers')
  && sims['pressure-washer'].halls.includes('hazmat')
  && /containment berm/.test(sims['pressure-washer'].task)
  && sims['pressure-washer'].rubric.some((r) =>
      r.axis === 'coverage' && r.pass === '>= 95')
  && sims['pressure-washer'].rubric.some((r) =>
      r.axis === 'damage' && r.pass === '== 0')
  && sims['pressure-washer'].rubric.some((r) =>
      r.axis === 'containment' && r.pass === 'required'));
ok('the airless sprayer teaches finish-coat discipline: painters/laborers train it, runs/holidays/overspray are all pass-gated at zero',
  sims['airless-sprayer'].halls.includes('painters')
  && sims['airless-sprayer'].halls.includes('laborers')
  && /masked line/.test(sims['airless-sprayer'].task)
  && sims['airless-sprayer'].rubric.some((r) =>
      r.axis === 'coverage' && r.pass === '>= 95')
  && sims['airless-sprayer'].rubric.some((r) =>
      r.axis === 'runs' && r.pass === '== 0')
  && sims['airless-sprayer'].rubric.some((r) =>
      r.axis === 'holidays' && r.pass === '== 0')
  && sims['airless-sprayer'].rubric.some((r) =>
      r.axis === 'overspray' && r.pass === '== 0'));
ok('the trench task teaches utility discipline: a pass demands zero strikes',
  /utility/.test(sims['excavator-trench'].task)
  && sims['excavator-trench'].rubric.some((r) =>
      r.axis === 'utility' && r.pass === '== 0'));
ok('the scoring contract is deterministic, stated in the record',
  /deterministic/.test(reg.scoring_contract)
  && /nothing narrative/.test(reg.scoring_contract));
ok('the honesty note refuses certification claims',
  /Not equipment certification/i.test(reg.honesty.status)
  && /unaided verification/.test(reg.honesty.status));
ok('every sim carries a data-driven dash: unique gauge ids with labels',
  Object.values(sims).every((s) => s.dash?.length >= 5
    && new Set(s.dash.map((g) => g.id)).size === s.dash.length
    && s.dash.every((g) => g.label !== undefined && g.unit !== undefined)));
ok('audio is declared honestly: a named engine, alerts, and the synthesized note',
  Object.values(sims).every((s) => s.audio?.engine && s.audio.alerts?.length >= 2
    && /synthesized/.test(s.audio.note) && /no recordings/.test(s.audio.note)));
ok('every sim offers an operator-seat view mode alongside the external one',
  Object.values(sims).every((s) => s.view_modes?.length >= 2)
  && sims['crane-lift'].view_modes.includes('cab')
  && sims['excavator-trench'].view_modes.includes('cab')
  && sims['forklift-run'].view_modes.includes('driver')
  && sims['weld-bead'].view_modes.includes('visor')
  && sims['scaffold-bay'].view_modes.includes('deck')
  && sims['rigging-signals'].view_modes.includes('signal')
  && sims['load-chart'].view_modes.includes('chart')
  && sims['boom-lift'].view_modes.includes('basket')
  && sims['overhead-crane'].view_modes.includes('pendant'));

const campusKeys = new Set(Object.keys(JSON.parse(readFileSync(
  new URL('../unions/registry/campuses.json', import.meta.url))).campuses));
ok('every sim trains regionally: one scenario per campus, unique ids, real briefs',
  Object.values(sims).every((s) => s.scenarios?.length === 3
    && new Set(s.scenarios.map((x) => x.campus)).size === 3
    && s.scenarios.every((x) => campusKeys.has(x.campus)
        && x.id && x.name && x.brief.length > 30
        && typeof x.params === 'object'))
  && new Set(Object.values(sims).flatMap((s) => s.scenarios.map((x) => x.id)))
      .size === 33);
ok('scenarios vary the environment, never the rubric: no scenario carries pass rules',
  Object.values(sims).every((s) =>
    s.scenarios.every((x) => !('rubric' in x.params) && !('pass' in x.params))));
ok('the trench scenarios keep at least one flagged utility each, at a shallow stop',
  sims['excavator-trench'].scenarios.every((x) =>
    x.params.cells.some((c) => c.util && c.d <= 0.5)));
ok('the boom lift teaches tie-off and envelope discipline: aerial-platform trades train it, tie-off and stabilizers are required, envelope and strikes pass at zero, every yard\'s points sit inside the rated envelope',
  (() => {
    const s = sims['boom-lift'], L = s.layout;
    const maxOut = L.rated_moment / L.load_kg;
    return ['electricians', 'glaziers', 'painters', 'ironworkers'].every((h) => s.halls.includes(h))
      && /harness/.test(s.task)
      && s.rubric.some((r) => r.axis === 'tie-off' && r.pass === 'required')
      && s.rubric.some((r) => r.axis === 'slope' && r.pass === 'required')
      && s.rubric.some((r) => r.axis === 'envelope' && r.pass === '== 0')
      && s.rubric.some((r) => r.axis === 'strikes' && r.pass === '== 0')
      && s.scenarios.every((x) => x.params.points.length >= 4
        && x.params.points.every(([px, py, pz]) => {
          const d = Math.hypot(px, pz), len = Math.hypot(d, py - L.pivot_y);
          return d < maxOut && len >= L.boom_min && len <= L.boom_max;
        }))
      // the transit elevation keeps a fully extended boom inside the envelope
      && Math.cos(L.transit_elev_deg * Math.PI / 180) * L.boom_max < maxOut
      && s.scenarios.filter((x) => x.params.line).length >= 2;
  })());
ok('the overhead crane teaches route and sway discipline: the crane hall and the shop trades train it, path and limits pass at zero, clearance is required, every yard keeps its pickup and target off the aisle and workstation',
  (() => {
    const s = sims['overhead-crane'], L = s.layout;
    const inRect = ([x, z], r) => x >= r.x[0] && x <= r.x[1] && z >= r.z[0] && z <= r.z[1];
    return ['crane-ops', 'millwrights', 'riggers', 'foundry'].every((h) => s.halls.includes(h))
      && s.halls[0] === 'crane-ops'
      && /pedestrian aisle/.test(s.task)
      && s.rubric.some((r) => r.axis === 'path' && r.pass === '== 0')
      && s.rubric.some((r) => r.axis === 'limits' && r.pass === '== 0')
      && s.rubric.some((r) => r.axis === 'clear' && r.pass === 'required')
      && s.rubric.some((r) => r.axis === 'sway' && r.pass === '<= 0.6')
      && s.scenarios.every((x) => !inRect(x.params.pickup, L.aisle)
        && !inRect(x.params.target, L.aisle)
        && !inRect(x.params.pickup, x.params.workstation)
        && !inRect(x.params.target, x.params.workstation)
        && x.params.obstacles.length >= 1
        && x.params.obstacles.every((o) => o.h + L.clearance < L.carry_h - L.hang)
        && x.params.load_t > 0 && x.params.load_t <= L.capacity_t)
      && L.carry_h < L.hook_max;
  })());
ok('every seat carries its in-headset control mapping, declared once: thumbsticks, trigger, grip, the two face buttons, and a machine-readable grip key only where the seat has a secondary edge key',
  Object.values(sims).every((s) => s.xr
    && ['left_stick', 'right_stick', 'trigger', 'grip', 'primary', 'secondary']
      .every((k) => typeof s.xr[k] === 'string' && s.xr[k].length > 10)
    && (s.xr.grip_key === null || /^Key[CXR]$/.test(s.xr.grip_key))
    && (s.xr.grip_key === null) === !s.controls.some((c) => /^[CXR]$/.test(c.keys))
    && /Space/.test(s.xr.trigger))
  && sims['pressure-washer'].xr.grip_key === 'KeyC'
  && sims['load-chart'].xr.grip_key === 'KeyX'
  && sims['scaffold-bay'].xr.grip_key === 'KeyR'
  && sims['boom-lift'].xr.grip_key === 'KeyC'
  && sims['crane-lift'].xr.grip_key === null
  && /mocked WebXR session/.test(reg.honesty.xr)
  && /no physical\s+headset/.test(reg.honesty.xr));

/* --------------------------------------- the scripted reference operator --- */
const page = readFileSync(new URL('../web/trade_craft_3d.html', import.meta.url), 'utf8');
const levels = Object.keys(reg.operator_levels);
ok('one closed level set is declared, optimal first, each level explained as what it honestly is',
  levels[0] === 'optimal' && levels.length >= 3
  && /passes every pass-gated rubric axis/.test(reg.operator_levels.optimal)
  && levels.slice(1).every((l) => reg.operator_levels[l].length > 40));
ok('every seat carries a scripted reference operator at exactly that level set',
  Object.values(sims).every((s) => s.operator
    && JSON.stringify(s.operator.levels) === JSON.stringify(levels)));
ok('every operator guarantees exactly the seat\'s pass-gated rubric axes at optimal - no axis quietly left out',
  Object.values(sims).every((s) => JSON.stringify(s.operator.guarantees)
    === JSON.stringify(s.rubric.filter((r) => r.pass !== 'informational').map((r) => r.axis))));
ok('every operator carries an ordered procedure of distinct, actionable steps',
  Object.values(sims).every((s) => s.operator.procedure.length >= 2
    && new Set(s.operator.procedure.map((p) => p.id)).size === s.operator.procedure.length
    && s.operator.procedure.every((p) => /^[a-z-]+$/.test(p.id) && p.step.length >= 12)));
ok('the operator\'s provenance word is SCRIPTED, stated as not learned, not real equipment, not a physical robot - and never AI-SYNTHESIZED',
  /^SCRIPTED:/.test(reg.honesty.operator)
  && /Not a learned policy, not real equipment/.test(reg.honesty.operator)
  && /not a claim about any physical robot/.test(reg.honesty.operator)
  && !/AI-SYNTHESIZED/.test(reg.honesty.operator));
ok('the yard geometry a seat shares with its operator is declared once, here, and the page reads it rather than retyping it',
  ['crane-lift', 'excavator-trench', 'forklift-run', 'pressure-washer', 'airless-sprayer',
    'boom-lift', 'overhead-crane']
    .every((id) => sims[id].layout && page.includes(`D.sims.sims['${id}'].layout`)));
ok('the seats an operator has to see expose what it steers by on the dash itself: excavator slew, forklift pose, bench position',
  sims['excavator-trench'].dash.some((g) => g.id === 'slew')
  && ['heading', 'x', 'z'].every((k) => sims['forklift-run'].dash.some((g) => g.id === k))
  && ['u', 'v'].every((k) => sims['pressure-washer'].dash.some((g) => g.id === k)
    && sims['airless-sprayer'].dash.some((g) => g.id === k)));
// the policy table sliced per seat: a seat's own block, plus the shared bench
// policy when the block delegates to it. Added after the whole-table check
// was found to pass for the wrong reason: a step id two seats share ('settle',
// 'hook', 'lower') was satisfied by ANOTHER seat's policy, so a seat could
// drop a declared step and nothing would notice. A check that reads the
// wrong scope is a check that cannot fail.
const opBlocks = (() => {
  const all = page.split('const OPERATORS = {')[1]?.split('function opAttach(')[0] ?? '';
  const [table, bench = ''] = all.split('function opBench(');
  const starts = Object.keys(sims).map((id) => [id, table.indexOf(`'${id}': {`)])
    .filter(([, i]) => i >= 0).sort((a, b) => a[1] - b[1]);
  return Object.fromEntries(starts.map(([id, i], k) => {
    const blk = table.slice(i, k + 1 < starts.length ? starts[k + 1][1] : undefined);
    return [id, blk + (/opBench\(/.test(blk) ? bench : '')];
  }));
})();
ok('the page builds a policy for every seat, written as a switch over that seat\'s OWN procedure ids - each id found in that seat\'s block (or the bench policy it delegates to), never satisfied by another seat\'s',
  Object.entries(sims).every(([id, s]) => opBlocks[id]?.length > 200
    && s.operator.procedure.every((p) => opBlocks[id].includes(`'${p.id}'`)))
  && levels.every((l) => Object.values(opBlocks).every((b) => b.includes(`${l}:`)))
  // the bench seats delegate, so their block carries the bench's raster
  // step; a machine seat's block does not
  && opBlocks['pressure-washer'].includes("case 'raster'")
  && !opBlocks['crane-lift'].includes("case 'raster'"));
ok('a single headless run hands the launching view back exactly as the sweep does - one mark, one restore, called by both, never a view left reading sim with no seat in it',
  page.includes('function opViewMark()') && page.includes('function opViewRestore(before)')
  && /run\(simId, scenarioId, o = \{\}\) \{[\s\S]{0,400}finally \{ opViewRestore\(before\); \}/.test(page)
  && /async function opSweep\([\s\S]{0,1200}opViewRestore\(before\);[\s\S]{0,120}return \{ recorded: trainingOn, rows \}/.test(page));

/* ---------------------------------------------------- the interactive map --- */
// The interactive map used to show a hall's toolroom crib but not its
// bound simulator seat, even though the 3D app's own hall header offers
// the seat via its simBtn toolbar button. Every bound hall gets a badge
// naming its first bound seat (the same "hall's own" rule build_3d.py's
// seatOf() uses); an unbound hall gets none.
const pageInteractive = readFileSync(
  new URL('../web/trade_craft_interactive.html', import.meta.url), 'utf8');
ok('every bound hall carries its first seat\'s id and real name on the interactive map, no more and no fewer',
  Object.entries(reg.hall_bindings).every(([hall, bl]) =>
    pageInteractive.includes(`"slug":"${hall}"`)
    && pageInteractive.includes(`"sim":{"id":"${bl[0].sim}","name":"${sims[bl[0].sim].name}"}`))
  && (pageInteractive.match(/"sim":\{"id"/g) || []).length === Object.keys(reg.hall_bindings).length);
ok('the interactive map renders a simulator badge only for a hall that has a bound seat, deep-linked to the 3D app',
  pageInteractive.includes('h.sim') && pageInteractive.includes('simChip')
  && pageInteractive.includes('trade_craft_3d.html?hall=${h.slug}'));

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`sims/test: ${n} checks passed — ${Object.keys(sims).length} simulators, `
  + `${Object.keys(reg.hall_bindings).length} halls bound`);
