/**
 * Compliance pack verification.
 *
 * The claim: the ledger is derived from its stamped inputs (per-hall hazards
 * and PPE recompute from surfaces; sign-off recomputes through
 * pack/hall_signoff.mjs and is 0 of every hall; the placard rule is located
 * in web/build_3d.py by structure; evidence classes are completion's;
 * rollups sum), no jurisdiction is named except inside the marked verbatim
 * ROADMAP quote, no count is typed, the fixture report re-derives, and every
 * mutant fails by the rule the builder names.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { REG, ROOT, RULES, checkLedger, report, locateAll, PLACARD_PATTERNS, sha16 } from './verify.mjs';
import { need } from '../completion/verify.mjs';
import { claimsHallSignoff, HALL_CONTENT_STATUSES } from '../pack/hall_signoff.mjs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };
const readJ = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));
const clone = (v) => JSON.parse(JSON.stringify(v));
const PATHS = need(REG, 'stamped_paths', 'compliance.json');

// first sentence: not a code reference, cites no jurisdiction
ok('registry says in its first sentence that it is not a code reference and cites no jurisdiction',
  need(REG, 'what_this_is', 'reg').split('.')[0].includes('not a code reference') && REG.what_this_is.split('.')[0].includes('cites no jurisdiction'));
ok('jurisdiction.named is null', need(need(REG, 'jurisdiction', 'reg'), 'named', 'jurisdiction') === null);

// stamps
for (const [k, rel] of Object.entries(PATHS)) ok(`stamp ${k} = ${rel} (${REG.stamps[k]})`, need(REG.stamps, k, 'stamps') === sha16(rel));
ok('stamp self = compliance/build.py', REG.stamps.self === sha16('compliance/build.py') && REG.source_stamp === REG.stamps.self);
ok('pack_version is the manifest\'s', REG.pack_version === need(readJ('pack/manifest.json'), 'pack_version', 'manifest'));

// the ledger re-derives on every rule
const tally = checkLedger(REG, null);
for (const r of RULES.filter((x) => x.startsWith('ledger.'))) ok(`${r}: checked ${tally[r].checked}, failing ${tally[r].fails.length}`, tally[r].checked > 0 && tally[r].fails.length === 0);

// per-hall hazards / PPE: recomputed here from surfaces, independently of checkLedger
const fin = readJ(PATHS.finishes), base = fin.base_conditions, hz = fin.hazard_conditions;
let roomsChecked = 0, hazardRooms = 0;
for (const [slug, H] of Object.entries(REG.halls)) {
  const F = need(fin.halls, slug, 'finishes.halls');
  if (JSON.stringify(H.hazards) !== JSON.stringify(F.hazards)) { console.error('FAIL', `${slug} hazards`); process.exit(1); }
  for (const strand of Object.keys(base)) {
    const gov = F.conditions[strand].hazards;
    const ppe = new Set(base[strand].ppe); for (const k of gov) for (const p of hz[k].ppe) ppe.add(p);
    if (JSON.stringify([...ppe].sort()) !== JSON.stringify(H.rooms[strand].ppe)) { console.error('FAIL', `${slug}.${strand} PPE`); process.exit(1); }
    roomsChecked++; if (gov.length) hazardRooms++;
  }
}
ok(`per-hall hazards equal finishes.json for ${Object.keys(REG.halls).length} halls; per-room PPE recomputed from base ∪ governing hazards for ${roomsChecked} rooms; ${hazardRooms} hazard rooms`, roomsChecked === REG.rollups.rooms && hazardRooms === REG.rollups.hazard_rooms);
ok('every hazard governing a room is one rules.hazard_rooms names for that strand',
  Object.entries(fin.halls).every(([, F]) => Object.entries(F.conditions).every(([s, c]) => c.hazards.every((k) => s in fin.rules.hazard_rooms[k]))));

// sign-off: through hall_signoff.mjs, never by string
const halls = readJ(PATHS.halls).halls;
const signed = halls.filter((h) => claimsHallSignoff(h.content_status)).length;
ok(`sign-off recomputed through pack/hall_signoff.mjs: ${signed} of ${halls.length} halls claim sign-off, ledger rollup agrees`, signed === 0 && REG.rollups.halls_signed_off === signed && halls.length === REG.rollups.halls);
ok('every hall\'s ledger sign-off status is what hall_signoff.mjs reads', halls.every((h) => REG.halls[h.slug].signoff.claims_signoff === claimsHallSignoff(h.content_status)));
ok('closed status set is hall_signoff.mjs\'s', JSON.stringify(REG.signoff_statuses.closed_set) === JSON.stringify(HALL_CONTENT_STATUSES));

// placard coverage: the same structural read of web/build_3d.py
const b3d = readFileSync(join(ROOT, PATHS.build_3d), 'utf8');
const loc = locateAll(b3d);
for (const k of Object.keys(PLACARD_PATTERNS)) ok(`placard rule ${k} located at web/build_3d.py:${loc[k]} = registry`, loc[k] !== null && loc[k] === REG.placard_rule[k].line);
let hung = 0;
for (const [slug, F] of Object.entries(fin.halls)) for (const s of Object.keys(base)) {
  const rc = F.conditions[s].hazards.length ? F.conditions[s] : base[s];
  if ((rc.ppe.length > 0) !== REG.halls[slug].rooms[s].placard.hung) { console.error('FAIL placard', slug, s); process.exit(1); }
  if (rc.ppe.length > 0) hung++;
}
ok(`placards recomputed by the 3D layer's rule: ${hung} rooms hung, rollup agrees`, hung === REG.rollups.rooms_with_placard);

// evidence classes equal completion's
const comp = readJ(PATHS.completion);
ok('evidence_classes equal completion.json\'s', JSON.stringify(REG.evidence_classes) === JSON.stringify(comp.evidence_classes));
for (const [k, r] of Object.entries(comp.evidence_rule)) {
  const e = need(REG.step_kind_evidence, k, 'step_kind_evidence');
  const exp = r.class === 'self-reported' ? 'self-reported' : r.class === 'device-mark' ? 'evidenceable' : (r.evidenceable ? 'evidenceable' : 'not-recordable');
  ok(`step kind ${k}: completion class ${r.class} -> ledger ${exp}`, e.completion_class === r.class && e.ledger_class === exp);
}
ok('walk and placard are self-reported; the registry says they cannot be evidenced', REG.step_kind_evidence.walk.ledger_class === 'self-reported' && REG.step_kind_evidence.placard.ledger_class === 'self-reported' && REG.honesty.self_reported.includes('cannot be evidenced'));

// seats: every axis carries sims.json's rule; gating axes counted
const sims = readJ(PATHS.sims).sims;
ok(`seats: ${REG.rollups.seats} = sims.json`, REG.rollups.seats === Object.keys(sims).length);
ok(`seats with every axis gating: ${REG.rollups.seats_every_axis_gates}; with an informational axis: ${REG.rollups.seats_with_an_informational_axis}`,
  REG.rollups.seats_every_axis_gates === Object.values(sims).filter((s) => s.rubric.every((a) => a.pass !== 'informational')).length);

// lesson gaps are named, not defaulted
const gapLessons = Object.values(REG.halls).flatMap((h) => h.lessons.filter((l) => l.hazard_rooms_walked_without_placard_step.length).map((l) => l.lesson));
ok(`lessons walking a hazard room without a placard step are named: ${gapLessons.join(', ')}`, gapLessons.length === REG.rollups.lessons_with_a_hazard_room_walked_without_placard_step);

// rollups: items sum
const c = REG.rollups.items_by_ledger_class;
ok('items_by_ledger_class sums to items', c.evidenceable + c['self-reported'] + c['not-recordable'] === REG.rollups.items);

// no jurisdiction named anywhere but the marked verbatim ROADMAP quote
const JUR = /OSHA|Title 24|ANSI|NFPA|ASTM|CFR/;
const quote = REG.jurisdiction.roadmap_status_verbatim;
const roadmap = readFileSync(join(ROOT, PATHS.roadmap), 'utf8');
ok('the ROADMAP quote is verbatim from ROADMAP.md and marked', roadmap.includes(quote) && REG.jurisdiction.quote_marker.startsWith('VERBATIM-ROADMAP-QUOTE'));
const stripped = clone(REG); stripped.jurisdiction.roadmap_status_verbatim = '';
ok('no jurisdiction or standard named in the registry outside the marked quote', !JUR.test(JSON.stringify(stripped)));
for (const f of ['compliance/build.py', 'compliance/verify.mjs']) {
  const src = readFileSync(join(ROOT, f), 'utf8');
  ok(`${f} names no jurisdiction`, !JUR.test(src));
  const code = src.replace(/#.*|\/\/.*|\/\*[\s\S]*?\*\/|"""[\s\S]*?"""/g, '').replace(/\?\{2\}/g, '');
  ok(`${f} has no .get(k, default) and no bare ?? in code`, !/\.get\([^)]*,/.test(code) && !/[^\\?]\?\?[^?]/.test(code));
}

// no typed count: the ledger's own totals never appear as literals in the builder or verifier
const counts = [...new Set(Object.values(REG.rollups).filter((v) => typeof v === 'number' && v > 1).concat(Object.values(c)))];
for (const f of ['compliance/build.py', 'compliance/verify.mjs']) {
  const src = readFileSync(join(ROOT, f), 'utf8').replace(/#.*|\/\/.*|\/\*[\s\S]*?\*\/|"""[\s\S]*?"""/g, '');
  const typed = counts.filter((v) => new RegExp(`(?<![\\w.])${v}(?![\\w.])`).test(src));
  ok(`${f} types none of the ledger's counts (${counts.length} checked)`, typed.length === 0);
}

// fixture: completion's own record, re-used; the report re-derives byte for byte
const good = readJ('compliance/fixture/good.json');
ok('fixture/good.json is completion/fixture/good.json', JSON.stringify(good) === JSON.stringify(readJ(PATHS.completion_fixture)));
const rep = report(good);
ok(`fixture report: ${rep.fails.length} fails, ${rep.halls.length} halls touched`, rep.fails.length === 0 && rep.halls.length > 0);
ok('fixture/report.txt is the report re-derived', readFileSync(join(ROOT, 'compliance/fixture/report.txt'), 'utf8') === rep.lines.join('\n') + '\n');
ok('report prints that each touched hall is unsigned, 0 of N', rep.halls.every((h) => rep.lines.some((l) => l.startsWith(`hall ${h} `))) && rep.lines.filter((l) => l.includes('UNSIGNED')).length === rep.halls.length && rep.lines.some((l) => l.includes(`${signed} of ${halls.length} halls signed off`)));
ok('report says the axes are the seat\'s rule, not the record\'s evidence', rep.lines.some((l) => l.includes('the axes are the seat\'s rule in sims.json, not the record\'s evidence')));
ok('report\'s last line is the honest one', rep.lines[rep.lines.length - 1] === 'this report is against the bundle\'s own rules, not any jurisdiction\'s; a signed record attests a key, not a person; nothing here is a certification or an inspection');
for (const [file, rule] of Object.entries(REG.fixture.mutants)) {
  const r = report(readJ('compliance/' + file));
  ok(`mutant ${file} fails ${rule}`, r.fails.some((f) => f.startsWith(rule + ':')) && r.lines.length === 0);
}

// registry mutants: each fails the named rule through checkLedger
const mut = {};
let m = clone(REG);
{ // a PPE item typed into a room whose finishes derive none
  const [slug, H] = Object.entries(m.halls).find(([, h]) => Object.values(h.rooms).some((r) => r.ppe.length === 0));
  const strand = Object.keys(H.rooms).find((s) => H.rooms[s].ppe.length === 0);
  H.rooms[strand].ppe = ['respirator'];
  mut['ppe-typed-for-room-without'] = ['ledger.ppe-derived', m, `${slug}.${strand}`];
}
m = clone(REG); m.halls[Object.keys(m.halls)[0]].signoff.claims_signoff = true; mut['hall-marked-signed-off'] = ['ledger.signoff', m, Object.keys(m.halls)[0]];
m = clone(REG); { const sid = Object.keys(m.seats)[0]; m.seats[sid].axes[0].pass = '>= 50'; mut['rubric-axis-invented-pass'] = ['ledger.rubric', m, sid]; }
m = clone(REG); m.stamps.finishes = '0000000000000000'; mut['stale-stamp'] = ['ledger.stamps', m, 'finishes'];
m = clone(REG); m.rollups.halls_signed_off = 1; mut['rollup-typed'] = ['ledger.rollups', m, 'halls_signed_off'];
for (const [name, [rule, reg, where]] of Object.entries(mut)) {
  const t = checkLedger(reg, null);
  ok(`registry mutant ${name} (${where}) fails ${rule}: ${t[rule].fails[0]}`, t[rule].fails.length > 0);
}
ok('registry_mutants_in_test names each registry mutant the test runs', REG.fixture.registry_mutants_in_test.every((k) => k in mut));

console.log(`compliance: ${n} checks passed — ${REG.rollups.halls} halls, ${REG.rollups.halls_with_hazards} with hazards, ${REG.rollups.hazard_rooms} hazard rooms, ${REG.rollups.halls_signed_off} signed off, ${REG.rollups.items} ledger items (${JSON.stringify(c)})`);
