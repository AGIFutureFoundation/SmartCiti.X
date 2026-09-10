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
ok('seven simulators ship: lifting and earthmoving machines, a driving seat, four process benches',
  Object.keys(sims).length === 7
  && Object.values(sims).filter((s) => s.kind === 'machine').length === 2
  && Object.values(sims).filter((s) => s.kind === 'driving').length === 1
  && Object.values(sims).filter((s) => s.kind === 'process').length === 4);
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
  && sims['load-chart'].view_modes.includes('chart'));

const campusKeys = new Set(Object.keys(JSON.parse(readFileSync(
  new URL('../unions/registry/campuses.json', import.meta.url))).campuses));
ok('every sim trains regionally: one scenario per campus, unique ids, real briefs',
  Object.values(sims).every((s) => s.scenarios?.length === 3
    && new Set(s.scenarios.map((x) => x.campus)).size === 3
    && s.scenarios.every((x) => campusKeys.has(x.campus)
        && x.id && x.name && x.brief.length > 30
        && typeof x.params === 'object'))
  && new Set(Object.values(sims).flatMap((s) => s.scenarios.map((x) => x.id)))
      .size === 21);
ok('scenarios vary the environment, never the rubric: no scenario carries pass rules',
  Object.values(sims).every((s) =>
    s.scenarios.every((x) => !('rubric' in x.params) && !('pass' in x.params))));
ok('the trench scenarios keep at least one flagged utility each, at a shallow stop',
  sims['excavator-trench'].scenarios.every((x) =>
    x.params.cells.some((c) => c.util && c.d <= 0.5)));

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`sims/test: ${n} checks passed — ${Object.keys(sims).length} simulators, `
  + `${Object.keys(reg.hall_bindings).length} halls bound`);
