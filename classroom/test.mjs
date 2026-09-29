/* classroom/test.mjs - classroom/registry/classroom.json against the registries it quotes.
 * Network-free. Prints `  ok ` per check, FAIL at column 0, exits non-zero on failure. */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok ' + m); } else { fail++; console.log('FAIL ' + m); } };
const raw = (p) => readFileSync(join(ROOT, p));
const J = (p) => JSON.parse(raw(p).toString('utf8'));
console.log('classroom/test.mjs');
const C = J('classroom/registry/classroom.json');
const S = J('schools/registry/schools.json'), L = J('lessons/registry/lessons.json').lessons;
const LY = J('layers/registry/layers.json'), PA = J('layers/registry/paths.json');
const W = J('wilds/registry/wilds.json'), SI = J('sims/registry/sims.json');

/* stamp: sha256 over the source registries in sorted id order */
{
  const ids = C.sources.map((s) => s.id).slice().sort();
  const buf = Buffer.concat(ids.map((id) => raw(C.sources.find((s) => s.id === id).path)));
  ok(C.source_stamp === createHash('sha256').update(buf).digest('hex').slice(0, 16)
     && C.sources.every((s) => s.sha256 === createHash('sha256').update(raw(s.path)).digest('hex').slice(0, 16)),
     'source_stamp and per-source sha256 match the registries on disk');
}

/* modules = schools units, verbatim */
const units = S.units;
ok(C.modules.length === units.length && units.every((u, i) => {
  const m = C.modules.find((x) => x.id === 'mod-' + u.hall);
  return m && m.unit_source === `schools/registry/schools.json#units[${i}]`
    && ['home', 'class_drill', 'gate'].every((k) => m.unit[k] === u[k])
    && JSON.stringify(m.unit.floor_sims) === JSON.stringify(u.floor_sims);
}), 'every module id resolves to one schools unit, fields quoted verbatim with source');
ok(C.modules.every((m) => m.lessons.length > 0 && m.lessons.every((id) => L[id] && L[id].hall === m.hall)),
  'every module lesson id resolves in lessons.json and belongs to the module hall');

/* moments quote lessons verbatim; the answer is the lesson's own why */
const MO = new Map(C.moments.map((m) => [m.id, m]));
ok(C.moments.every((m) => L[m.lesson] && m.title === L[m.lesson].title && m.limits === L[m.lesson].limits
  && m.first_do === L[m.lesson].steps[0].do && m.status === 'unverified general practice'),
  'every moment quotes its lesson title, limits and first step verbatim, marked unverified general practice');
ok(C.moments.every((m) => m.choices.length === 3 && m.choices.some((c) => c.lesson === m.answer) && m.answer === m.lesson
  && m.choices.every((c) => L[c.lesson] && c.text === L[c.lesson].why)
  && new Set(m.choices.map((c) => c.lesson)).size === 3),
  'every choice card: 3 distinct verbatim lesson "why" texts, the answer is the lesson\'s own');
ok(C.modules.every((m) => m.moments.every((id) => MO.has(id) && MO.get(id).module === m.id)),
  'every module moment id resolves back to that module');

/* places resolve to real ids */
const PL = new Map(C.places.map((p) => [p.id, p]));
const st = new Map();
for (const p of LY.parishes) for (const s of p.stations) st.set(s.id, { fips: p.fips, s });
const resolve = (p) => {
  const r = p.ref;
  if (p.kind === 'station') return st.has(r.station) && st.get(r.station).fips === r.fips && p.world === 'parishes';
  if (p.kind === 'path-step') {
    const par = PA.parishes.find((x) => x.fips === r.fips);
    const path = par && par.paths.find((x) => x.id === 'k12');
    const step = path && path.steps[r.n - 1];
    return !!step && step.id === r.station && st.has(r.station) && p.world === 'parishes';
  }
  if (p.kind === 'site') {
    const w = W.worlds.find((x) => x.id === r.world);
    return !!w && w.sites.some((s) => s.id === r.site) && p.world === 'wilds';
  }
  if (p.kind === 'hall') return Object.values(L).some((l) => l.hall === r.hall) && p.href === `web/trade_craft_3d.html?hall=${r.hall}`;
  if (p.kind === 'seat') return !!SI.sims[r.sim] && (SI.hall_bindings[r.hall] || []).some((b) => b.sim === r.sim)
    && p.href === `web/trade_craft_3d.html?hall=${r.hall}&sim=${r.sim}`;
  return false;
};
const bad = C.places.filter((p) => !resolve(p)).map((p) => p.id);
ok(bad.length === 0, `every world place resolves to a real registry id (${C.places.length} places; bad: ${bad.slice(0, 3).join(', ')})`);
ok(C.modules.every((m) => m.places.length > 0 && m.places.every((id) => PL.has(id)))
  && C.moments.every((m) => m.places.length > 0 && m.places.every((id) => PL.has(id))),
  'every module and moment place id is declared in places');
ok(C.worlds.every((w) => { try { raw(w.page); return true; } catch (e) { return false; } })
  && C.places.every((p) => C.worlds.some((w) => w.id === p.world)), 'every place world names an existing world page');
ok(C.counts.modules === C.modules.length && C.counts.moments === C.moments.length && C.counts.places === C.places.length
  && Object.entries(C.counts.places_by_world).every(([w, n]) => C.places.filter((p) => p.world === w).length === n),
  'counts are computed from the lists');

/* Cognition.X transfer moments: verbatim blocks, CC-BY-4.0 attribution, places resolve */
{
  const CX = J('cognitionx/registry/cognitionx.json'), X = C.cognitionx;
  const byId = new Map(CX.blocks.map((b) => [b.block_id, b]));
  const COLS = ['block_id', 'pack', 'track', 'code', 'grade', 'level', 'credential', 'theme', 'description', 'transfer_check'];
  ok(X.moments.length > 0 && X.moments.every((m) => { const b = byId.get(m.block.block_id); return b && m.id === 'tx-' + b.block_id && m.kind === 'transfer'
    && COLS.every((k) => m.block[k] === b[k]) && Object.keys(m.block).length === COLS.length && m.statement_field === b.statement_field && m.module === b.module; }),
    `every Cognition.X transfer moment quotes its block's 10 upstream columns verbatim (${X.moments.length} moments)`);
  const cxp = new Map(CX.places.map((p) => [p.id, p]));
  ok(X.moments.every((m) => m.places.length > 0 && m.places.every((id) => PL.has(id) && resolve(PL.get(id))
    && (byId.get(m.block.block_id).places.includes(id) || byId.get(m.block.block_id).places.some((u) => cxp.get(u) && cxp.get(u).kind === 'path-step' && cxp.get(u).ref.station && id.endsWith('/' + cxp.get(u).ref.station))))),
    'every transfer moment place resolves here and is one the block maps to (or the station of its k12 step)');
  ok(X.attribution.license === 'CC-BY-4.0' && ['text', 'license', 'license_url', 'repo', 'commit', 'changes'].every((k) => X.attribution[k] === CX.attribution[k])
    && JSON.stringify(X.honesty) === JSON.stringify(CX.honesty), 'Cognition.X attribution (CC-BY-4.0) and honesty carried unchanged');
  ok(X.modules.every((m) => m.moments.length > 0 && m.moments.every((id) => X.moments.some((x) => x.id === id && x.module === m.id)))
    && X.counts.moments === X.moments.length && X.counts.modules === X.modules.length, 'Cognition.X modules list their own moments; counts computed');
}

/* honesty */
const H = C.honesty;
ok(/unverified general practice/.test(H.lessons) && /PROPOSED/.test(H.districts) && H.districts === S.honesty.districts,
  'lessons stay "unverified general practice"; districts stay PROPOSED (quoted)');
ok(/never enter a completion record/.test(H.play) && /not access control/.test(H.plans) && /No student data leaves/.test(H.data)
  && /No grade-level standards alignment/.test(H.standards), 'honesty: play, plans not access control, no data leaves, no standards claim');
ok(C.rules.provenance === 'AUTHORED' && C.rules.badges.length > 0 && Object.values(C.rules.xp).every((n) => Number.isInteger(n) && n > 0),
  'XP/streak/badge rules are marked AUTHORED');
ok(C.districts.every((d) => /proposed/i.test(d.status)), 'every district record carries its PROPOSED status');

console.log(`${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
