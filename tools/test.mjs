/**
 * Toolroom registry verification.
 *
 * A crib is a curriculum claim: a district's twelve tools, each with a
 * render shape the 3D toolroom owns and a use line the drill asks. The
 * drill is derived from the crib, so the derivation is re-run here and
 * must match; every hall binding is proven against the roster, the
 * district table and the skill graph; and the honesty note — schematic
 * aid, no brands, not certification — is asserted, not assumed.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const reg = JSON.parse(readFileSync(new URL('./registry/toolcribs.json', import.meta.url)));
const districts = JSON.parse(readFileSync(
  new URL('../unions/registry/districts.json', import.meta.url))).districts;
const unions = JSON.parse(readFileSync(
  new URL('../unions/registry/unions.json', import.meta.url))).unions;
const skills = new Set(JSON.parse(readFileSync(
  new URL('../pack/registry/skills.json', import.meta.url))).skills.map((s) => s.skill_id));

const SHAPES = new Set(['bar', 'wrench', 'blade', 'meter', 'cyl', 'coil',
  'hook', 'case', 'cone']);

ok('one crib per district, exactly - no district tools up from an empty room',
  JSON.stringify(Object.keys(reg.cribs).sort())
    === JSON.stringify(Object.keys(districts).sort()));
ok('every crib hangs twelve tools with unique ids',
  Object.values(reg.cribs).every((c) => c.tools.length === 12
    && new Set(c.tools.map((t) => t.id)).size === 12));
ok('every tool can render and can teach: named, a glyph, a known shape, a hue, a use line',
  Object.values(reg.cribs).every((c) => c.tools.every((t) =>
    t.name && t.glyph && SHAPES.has(t.shape)
    && t.hue >= 0 && t.hue <= 360 && t.use.length > 15)));
ok('no manufacturer sneaks onto the board: tool names are generic',
  Object.values(reg.cribs).every((c) => c.tools.every((t) =>
    !/\b(DeWalt|Milwaukee|Makita|Bosch|Klein|Snap-on|Hilti|Stanley|Ridgid|Fluke)\b/i
      .test(t.name + ' ' + t.use))));
ok('the safety tools are where the doctrine needs them: dead-test, gas watch, fall arrest',
  reg.cribs.systems.tools.some((t) => /dead/.test(t.use))
  && reg.cribs.control.tools.some((t) => /four killers|air/.test(t.use))
  && reg.cribs.control.tools.some((t) => /arrests a fall/.test(t.use)));

/* -------------------------------------------------------------- drills --- */
ok('every district carries a drill of five picks, all answers in its own crib',
  Object.entries(reg.drills).every(([dk, tasks]) => tasks.length === reg.drill.picks
    && tasks.every((x) => reg.cribs[dk].tools.some((t) => t.id === x.tool))));
ok('each drill samples five DIFFERENT tools, and the ask is the tool\'s own use line',
  Object.entries(reg.drills).every(([dk, tasks]) =>
    new Set(tasks.map((x) => x.tool)).size === reg.drill.picks
    && tasks.every((x) => x.ask === 'Pick the tool that '
        + reg.cribs[dk].tools.find((t) => t.id === x.tool).use)));
ok('the drill derivation is deterministic: re-running it here reproduces the record',
  Object.entries(reg.drills).every(([dk, tasks]) => {
    const tools = reg.cribs[dk].tools;
    return tasks.every((x, i) => x.tool === tools[(i * 5 + 2) % tools.length].id);
  }));
ok('the drill contract is stated: deterministic, index arithmetic, nothing narrative',
  /deterministic/.test(reg.drill.contract)
  && /index arithmetic/.test(reg.drill.contract)
  && /nothing narrative/.test(reg.drill.contract));

/* ------------------------------------------------------------ bindings --- */
ok('every hall on the roster is bound to its own district\'s crib',
  Object.keys(reg.hall_bindings).length === unions.length
  && unions.every((u) => {
    const b = reg.hall_bindings[u.slug];
    return b && b.district === u.district
      && districts[b.district].halls.includes(u.slug);
  }));
ok('every binding lands on a real applied tools skill in the graph',
  Object.entries(reg.hall_bindings).every(([slug, b]) =>
    b.skill_id === slug + '.tools.applied' && skills.has(b.skill_id)));

/* ------------------------------------------------------------- honesty --- */
ok('the honesty note refuses what this is not: real inventory, certification, brands',
  /schematic/.test(reg.honesty.status)
  && /not an inventory of any real toolroom/.test(reg.honesty.status)
  && /not tool competency certification/.test(reg.honesty.status)
  && /no manufacturer or brand/.test(reg.honesty.status));

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

const nt = Object.values(reg.cribs).reduce((a, c) => a + c.tools.length, 0);
console.log(`tools/test: ${n} checks passed — ${Object.keys(reg.cribs).length} cribs, `
  + `${nt} tools, ${Object.keys(reg.hall_bindings).length} halls bound`);
