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
ok('two simulators ship: one machine, one driving',
  Object.keys(sims).length === 2
  && Object.values(sims).some((s) => s.kind === 'machine')
  && Object.values(sims).some((s) => s.kind === 'driving'));
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
ok('the operator seats train where they belong: crane hall lifts, teamsters drive',
  sims['crane-lift'].halls.includes('crane-ops')
  && sims['forklift-run'].halls.includes('teamsters'));
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
  && sims['forklift-run'].view_modes.includes('driver'));

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`sims/test: ${n} checks passed — ${Object.keys(sims).length} simulators, `
  + `${Object.keys(reg.hall_bindings).length} halls bound`);
