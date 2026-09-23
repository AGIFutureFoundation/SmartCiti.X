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
const skillRows = JSON.parse(readFileSync(
  new URL('../pack/registry/skills.json', import.meta.url))).skills;
const skills = new Set(skillRows.map((s) => s.skill_id));
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
ok('every seat carries its five-point walkaround - each point a look AND the stop it is for - and the walkaround is honestly NOT a gate',
  Object.values(sims).every((s) => s.walkaround?.length === 5
    && new Set(s.walkaround.map((w) => w.id)).size === 5
    && new Set(s.walkaround.map((w) => w.on_fault)).size === 5
    && s.walkaround.every((w) => w.point && w.check.length > 15
        && w.on_fault?.length > 40))
  && /not a gate/.test(reg.honesty.walkaround)
  && /changes no score/.test(reg.honesty.walkaround)
  && /not an equipment inspection record/.test(reg.honesty.walkaround)
  // the fault action is practice, not a permission the seat hands out
  && /not a release anybody can sign from here/.test(reg.honesty.walkaround));
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
/* Whose name is on the curriculum is the first thing a training coordinator
   asks, and the honest answer is nobody's yet. A record that does not say so
   reads as a claim rather than a draft. */
ok('the record says who has NOT vouched for it: unverified general practice, pending journey-level authoring, citing no jurisdiction, standard or authority',
  /unverified general practice/.test(reg.honesty.authoring)
  && /journey-level practitioners/.test(reg.honesty.authoring)
  && /Nothing here cites a jurisdiction, a standard or an authority/.test(reg.honesty.authoring)
  && /no rubric line, walkaround point or fault action is an instruction/
      .test(reg.honesty.authoring));
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
/* A PASS GATE IS ONLY A GATE IF A RUN CAN FAIL IT. The rubric now has to say
   how, in a sentence, for every gated axis - and an informational axis has to
   stay silent, because it has no failure to describe. Writing those sentences
   is what found the gates no run could fail; the register below carries what
   is left of them. */
ok('every pass gate names the failure it is a gate against, in a sentence, and no two gates on a seat fail the same way',
  Object.values(sims).every((s) => {
    const gated = s.rubric.filter((r) => r.pass !== 'informational');
    return gated.length >= 1
      && gated.every((r) => typeof r.fails_when === 'string' && r.fails_when.length > 40)
      && new Set(gated.map((r) => r.fails_when)).size === gated.length
      && s.rubric.every((r) => ('fails_when' in r) === (r.pass !== 'informational'));
  }));
ok('the scaffold bay no longer gates an axis its own finish condition guarantees: sequence is the gate, completeness is reported',
  sims['scaffold-bay'].rubric.find((r) => r.axis === 'complete').pass === 'informational'
  && sims['scaffold-bay'].rubric.filter((r) => r.pass !== 'informational')
      .map((r) => r.axis).join() === 'sequence'
  && JSON.stringify(sims['scaffold-bay'].operator.guarantees) === '["sequence"]');
ok('every scenario declares the whole of its seat\'s param set, with nothing null and nothing the page would have to default',
  Object.values(sims).every((s) => {
    const want = [...new Set(s.scenarios.flatMap((x) => Object.keys(x.params)))].sort();
    return want.length > 0
      && JSON.stringify(s.scenario_params) === JSON.stringify(want)
      && s.scenarios.every((x) =>
          JSON.stringify(Object.keys(x.params).sort()) === JSON.stringify(want)
          && Object.values(x.params).every((v) => v !== null && v !== undefined));
  }));
ok('every yard says what it demands that its sibling yards do not - a scenario that cannot is a skin',
  Object.values(sims).every((s) =>
    s.scenarios.every((x) => typeof x.teaches === 'string' && x.teaches.length > 30)
    && new Set(s.scenarios.map((x) => x.teaches)).size === s.scenarios.length)
  && new Set(Object.values(sims).flatMap((s) => s.scenarios.map((x) => x.teaches)))
      .size === 33);
/* The boom lift's route, recomputed from the registry the page reads: the
   operator raises to the declared transit elevation before it swings or
   extends, holds it across every bearing and boom length the yard uses, and
   lowers onto a point along that point's own bearing. If a yard's overhead
   line were drawn across that route, the scripted operator would strike it on
   every run - which the builder asserts and this re-derives, with the margin
   read out of the builder rather than typed here a second time. */
ok('every boom-lift yard\'s overhead zone sits clear of the transit route the scripted operator flies',
  (() => {
    const s = sims['boom-lift'], L = s.layout, R = Math.PI / 180;
    const margin = parseFloat(
      /CLEAR_MARGIN = ([\d.]+)/.exec(readFileSync(new URL('./build.py', import.meta.url), 'utf8'))[1]);
    const basket = (sw, el, len) => [L.pivot_y + Math.sin(el * R) * len,
                                     Math.sin(sw * R) * Math.cos(el * R) * len];
    return margin > 0 && s.scenarios.every((x) => {
      const line = x.params.line;
      const solved = x.params.points.map(([px, py, pz]) => {
        const d = Math.hypot(px, pz), dy = py - L.pivot_y;
        return [Math.atan2(pz, px) / R, Math.hypot(d, dy), Math.atan2(dy, d) / R];
      });
      const poses = [];
      for (let e = 0; e <= L.transit_elev_deg * 2; e++) poses.push([0, e / 2, L.boom_min]);
      const hi = Math.max(...solved.map((q) => q[1]));
      for (let b = 0; b < 360; b += 2)
        for (let len = L.boom_min; len <= hi + .25; len += .25)
          poses.push([b, L.transit_elev_deg, Math.min(len, hi)]);
      for (const [bearing, len, elPt] of solved)
        for (let i = 0; i <= 60; i++)
          poses.push([bearing, elPt + (L.transit_elev_deg - elPt) * i / 60, len]);
      return poses.every(([sw, el, len]) => {
        const [y, z] = basket(sw, el, len);
        return Math.hypot(y - line.y, z - line.z) - line.r >= margin;
      });
    });
  })());
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
      // one yard used to declare no overhead line at all, which left
      // `strikes` a pass gate nothing in that yard could reach and the
      // walkaround's overhead scan with nothing to find
      && s.scenarios.every((x) => x.params.line && x.params.line.r > 0);
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

/* ------------------------------------------- gates the seat cannot fail --- */
/* Four pass gates were found grading their own run's terminating condition:
   the seat stops at exactly the state the axis demands, so no episode can
   score them anything but a pass. The rubric lines are right and stay gates;
   the seats are what is wrong, so the register declares each gap with the
   seat change that closes it AND the page marker it lives at. These two
   checks are a ratchet in both directions: a gap that names a non-gate or an
   axis that does not exist fails, and so does a gap whose marker has gone -
   which is what closing it looks like, and the signal to delete the entry. */
/* The register may be EMPTY, and empty is the win: it means every gap
   found has been closed in the page. Requiring at least one entry would
   make the suite demand that a known defect stay open, which is the
   opposite of a ratchet. What is held is the SHAPE of any entry present,
   and that each one is still open. */
ok('every declared gate gap names a real pass gate on a real seat and says what would close it',
  Array.isArray(reg.gate_gaps)
  && reg.gate_gaps.every((g) => sims[g.sim]
    && sims[g.sim].rubric.some((r) => r.axis === g.axis && r.pass !== 'informational')
    && g.why.length > 40 && g.fix.length > 60 && g.page_marker.length > 20)
  && new Set(reg.gate_gaps.map((g) => g.page_marker)).size === reg.gate_gaps.length);
ok('every declared gate gap is still open in the page it was declared against - close one and this says so',
  reg.gate_gaps.every((g) => page.includes(g.page_marker)));
/* And the four that WERE open are closed, held by the shape that closed
   them rather than by their absence - so a revert puts the fake gate back
   and this says so. Each of these is an axis that could not fail before. */
ok('a stop signal ends the card from anywhere, so the calls gate can fail',
  /if \(sig === 'stop'\) \{ if \(sig === SEQ\[st\.i\]\) st\.i\+\+; return finish\(\); \}/
    .test(page));
ok('a run is a defect and not coverage, so the sprayer\'s coverage and '
  + 'holidays gates can fail',
  /cell\.run = true; st\.runs\+\+; paint\(cell\);/.test(page)
  && /cells\.every\(\(c\) => c\.coated \|\| c\.run\)/.test(page)
  && /cells\.filter\(\(c\) => c\.coated && !c\.run\)/.test(page));
ok('a basket that comes down early ends the run, so the reach gate can fail',
  /if \(st\.lifted && bp\.y <= LAY\.stow_h\) finish\(\);/.test(page));
ok('and the one tautology is informational rather than a green tick on an '
  + 'ungraded axis',
  /\{ axis: 'complete', value: parts\.length \+ '\/' \+ parts\.length, ok: null \}/
    .test(page));
/* The washer bench is the pattern the sprayer's coverage gap is measured
   against, so it is pinned here: a gouged cell ENDS the pass without counting
   as cleaned, which is exactly what keeps that seat's coverage gate reachable.
   The sprayer marks a run cell coated instead, which is the gap above. */
ok('the washer bench keeps its coverage gate reachable: a gouged cell ends the pass without counting as cleaned',
  page.includes('cell.damaged = true; cell.clean = false;')
  && page.includes('cells.every((c) => c.clean || c.damaged)')
  && !reg.gate_gaps.some((g) => g.sim === 'pressure-washer'));

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

/* ------------------------------------------------------------- the yard --- */
/* A seat is a place, and a place has a floor. Every yard used to be a fence
   and four masts standing on the page's global ground plane, so the welder,
   the excavator and the pressure washer worked on the same nothing. The
   surface is cross-checked against the pack that OWNS the finishes rather
   than described a second time here, which is the whole point of naming it
   by id. */
const finishes = JSON.parse(readFileSync(
  new URL('../surfaces/registry/finishes.json', import.meta.url)));
ok('every seat declares the floor its yard is laid with, with a reason',
  Object.values(reg.sims).every((s2) => s2.yard?.surface && s2.yard.why?.length > 20));
ok('every yard surface is a finish the surfaces catalogue actually holds, '
  + 'named the same way there',
  Object.values(reg.sims).every((s2) =>
    finishes.catalogue[s2.yard.surface]
    && finishes.catalogue[s2.yard.surface].name === s2.yard.name));
ok('the yards differ: the seats do not all stand on one floor',
  new Set(Object.values(reg.sims).map((s2) => s2.yard.surface)).size >= 4);
/* The welding bay's floor is the one place this pack and the hazard rules in
   surfaces/ have to agree out loud: hot work goes on bare slab because there
   must be nothing underfoot to carry a spark, and that is the same sentence
   in both packs. If someone changes one, this fails. */
ok('the welding seat stands on the floor the hot-work hazard puts it on',
  reg.sims['weld-bead'].yard.surface === 'bare-slab'
  && Object.values(finishes.halls).some((h) =>
      h.rooms.procedure.placed_by === 'hazard'
      && h.rooms.procedure.hazard === 'hot-work'
      && h.rooms.procedure.surface === 'bare-slab'));

/* ------------------------------------------ what the seats do not reach --- */
/* `coverage` is the only block in this registry that exists to say the
   product is thin, so it is the one block a future edit is most tempted to
   improve by typing a better number into the JSON. These checks make that
   impossible: every figure is RECOMPUTED here from pack/registry/skills.json
   and from hall_bindings, and compared. Editing the block without moving the
   seats fails; adding seats moves both sides together and passes. */
const byId = new Map(skillRows.map((s2) => [s2.skill_id, s2]));
const seatCells = new Map();
for (const list of Object.values(reg.hall_bindings)) {
  for (const b of list) seatCells.set(b.skill_id, (seatCells.get(b.skill_id) || 0) + 1);
}
const closure = (cell) => {
  const seen = new Set(); const stack = [cell];
  while (stack.length) {
    const here = stack.pop();
    const row = byId.get(here);
    if (!row) return null;            // dangling prerequisite: fail closed
    for (const r of row.requires) if (!seen.has(r)) { seen.add(r); stack.push(r); }
  }
  return seen;
};
const cov = reg.coverage;
/* Deleting the block is the cheapest way to stop it saying this, and a
   deleted block would take every check below it out with a TypeError rather
   than a named failure. So its presence and shape is held first, by name. */
ok('the registry carries the seat-coverage block at all - deleting it is not a way to stop it saying this',
  cov && ['halls', 'strands', 'cells', 'seats'].every((k) => cov[k]
    && Object.values(cov[k]).every((v) => Number.isInteger(v) && v >= 0))
  && Array.isArray(cov.unreachable_seat_cells));
ok('the seat-coverage block recomputes: every count in it is the pack counted again, not a number typed into the registry',
  cov.halls.total === slugs.size
  && cov.halls.with_a_seat === Object.keys(reg.hall_bindings).length
  && cov.cells.total === skillRows.length
  && cov.cells.with_a_seat === seatCells.size
  && cov.seats.bound === Object.values(reg.hall_bindings).reduce((a, l) => a + l.length, 0)
  && cov.strands.total === new Set(skillRows.map((s2) => s2.union + '.' + s2.strand)).size
  && cov.strands.with_a_seat === new Set([...seatCells.keys()]
      .map((c) => byId.get(c).union + '.' + byId.get(c).strand)).size);
ok('seats pile up, and the pile-ups are counted rather than left to flatter the coverage: a cell with four seats is one covered cell',
  cov.cells.carrying_more_than_one_seat === [...seatCells.values()].filter((v) => v > 1).length
  && cov.cells.seats_absorbed_by_those_cells === [...seatCells.values()].filter((v) => v > 1).reduce((a, v) => a + v, 0)
  && cov.cells.with_a_seat < cov.seats.bound);
ok('the unreachable list is exactly the bound cells whose whole prerequisite chain carries no seat - recomputed, and it is every one of them',
  (() => {
    const want = [...seatCells.keys()].filter((c) => {
      const pre = closure(c);
      return pre !== null && pre.size > 0 && ![...pre].some((p) => seatCells.has(p));
    }).sort();
    return JSON.stringify(want) === JSON.stringify(cov.unreachable_seat_cells);
  })());
ok('no prerequisite dangles: every cell a seat cell requires is a cell the pack declares',
  [...seatCells.keys()].every((c) => closure(c) !== null));
ok('the block says plainly what it measures and what it means, in more than a label’s worth of words',
  cov.means.length > 120 && cov.honest.length > 120
  && cov.means.includes('none of them is typed'));

console.log(`sims/test: ${n} checks passed — ${Object.keys(sims).length} simulators, `
  + `${Object.keys(reg.hall_bindings).length} halls bound`);
