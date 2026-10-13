/**
 * SmartCiti.X : Trade Craft Academy — compliance report over a tc-completion/1 record.
 *
 * This report is against the bundle's own rules, not any jurisdiction's. The
 * record must first pass completion/verify.mjs (imported, never copied);
 * then, for each hall the record touches, every ledger item is printed as
 * evidenced / self-reported / not-evidenced, with the seats passed and the
 * rubric axes the registry says decide them (the axes are the seat's rule,
 * not the record's evidence), and the hall's sign-off status.
 *
 *   node compliance/verify.mjs <record.json>
 *
 * checkLedger() re-derives the ledger from its stamped inputs and fails by
 * rule name, so a ledger edited by hand fails before any report is printed.
 * §23.1: no `.get(k, default)` and no bare `??` here; a missing key fails.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { verify, need } from '../completion/verify.mjs';
import { claimsHallSignoff, validateHallContentStatus, HALL_CONTENT_STATUSES } from '../pack/hall_signoff.mjs';

export const ROOT = fileURLToPath(new URL('..', import.meta.url));
const readJ = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));
export const REG = readJ('compliance/registry/compliance.json');
const PATHS = need(REG, 'stamped_paths', 'compliance.json');
export const RULES = need(need(REG, 'verifier', 'compliance.json'), 'rules', 'compliance.json#verifier');

export function sha16(rel) { return createHash('sha256').update(readFileSync(join(ROOT, rel))).digest('hex').slice(0, 16); }

/* The placard rule, located in web/build_3d.py by the same structural read
   build.py makes. Each pattern returns the 1-based line or null. */
export const PLACARD_PATTERNS = {
  hangs_when: /if \(rc\.ppe\.length\) \{\n\s*const plac = label\(rc\.ppe\.join/,
  rc_is: /const rc = condOf\(h\.slug, r\.strand\);/,
  condOf: /function condOf\(hallSlug, strand\) \{\n\s*return D\.condOver\[hallSlug\]\?\.\[strand\] \?{2} D\.baseCond\[strand\];/,
  condOver: /'condOver': \{sl: \{st: c for st, c in h\['conditions'\]\.items\(\)\n\s*if c\['hazards'\]\}/,
};
export function locateAll(text) {
  const out = {};
  for (const [k, re] of Object.entries(PLACARD_PATTERNS)) {
    const m = text.match(re);
    out[k] = m ? text.slice(0, m.index).split('\n').length : null;
  }
  return out;
}

/* Re-derive every ledger fact from the inputs and compare. `inputs` lets a
   test hand in a mutated registry; the files are always the real ones. */
export function checkLedger(reg, inputs) {
  const fin = inputs && inputs.finishes ? inputs.finishes : readJ(need(PATHS, 'finishes', 'paths'));
  const sims = inputs && inputs.sims ? inputs.sims : readJ(need(PATHS, 'sims', 'paths'));
  const halls = inputs && inputs.halls ? inputs.halls : readJ(need(PATHS, 'halls', 'paths'));
  const b3d = inputs && inputs.build_3d ? inputs.build_3d : readFileSync(join(ROOT, need(PATHS, 'build_3d', 'paths')), 'utf8');
  const tally = {};
  for (const r of RULES) tally[r] = { checked: 0, fails: [] };
  const check = (rule, cond, msg) => { tally[rule].checked++; if (!cond) tally[rule].fails.push(msg); };

  // ledger.stamps — every input the ledger was derived from, plus its own builder
  const stamps = need(reg, 'stamps', 'compliance.json');
  for (const [k, rel] of Object.entries(PATHS)) check('ledger.stamps', need(stamps, k, 'stamps') === sha16(rel), `${k} (${rel}) changed since the ledger was built`);
  check('ledger.stamps', need(stamps, 'self', 'stamps') === sha16('compliance/build.py'), 'compliance/build.py changed since the ledger was built');
  check('ledger.stamps', need(reg, 'source_stamp', 'compliance.json') === stamps.self, 'source_stamp is not the builder stamp');

  // ledger.ppe-derived — per hall, per room: hazards and PPE equal finishes.json's merge of base ∪ governing hazards
  const base = need(fin, 'base_conditions', 'finishes'), hz = need(fin, 'hazard_conditions', 'finishes');
  const fh = need(fin, 'halls', 'finishes'), hazardRoomsRule = need(need(fin, 'rules', 'finishes'), 'hazard_rooms', 'finishes#rules');
  const ledger = need(reg, 'halls', 'compliance.json');
  check('ledger.ppe-derived', Object.keys(ledger).length === Object.keys(fh).length && Object.keys(ledger).every((s) => s in fh), 'ledger hall set is not finishes.json\'s');
  for (const [slug, H] of Object.entries(ledger)) {
    if (!(slug in fh)) continue;
    const F = fh[slug];
    check('ledger.ppe-derived', JSON.stringify(need(H, 'hazards', slug)) === JSON.stringify(need(F, 'hazards', slug)), `${slug}: hazards differ from finishes.json`);
    const rooms = need(H, 'rooms', slug), conds = need(F, 'conditions', slug);
    for (const strand of Object.keys(base)) {
      const r = need(rooms, strand, `${slug} rooms`), c = need(conds, strand, `${slug} conditions`);
      const governing = need(c, 'hazards', `${slug}.${strand}`);
      const ppe = new Set(need(need(base, strand, 'base'), 'ppe', strand));
      for (const k of governing) { for (const p of need(need(hz, k, 'hazard_conditions'), 'ppe', k)) ppe.add(p); }
      const derived = [...ppe].sort();
      check('ledger.ppe-derived', JSON.stringify(need(r, 'ppe', strand)) === JSON.stringify(derived), `${slug}.${strand}: ledger PPE ${JSON.stringify(r.ppe)} is not derived from finishes (${JSON.stringify(derived)})`);
      check('ledger.ppe-derived', JSON.stringify(need(r, 'hazards', strand)) === JSON.stringify(governing), `${slug}.${strand}: governing hazards differ`);
      check('ledger.ppe-derived', need(r, 'hazard_room', strand) === (governing.length > 0), `${slug}.${strand}: hazard_room flag differs`);
      for (const k of governing) check('ledger.ppe-derived', strand in need(hazardRoomsRule, k, 'rules.hazard_rooms'), `${slug}.${strand}: ${k} governs a room rules.hazard_rooms does not name`);
      const basePpe = new Set(base[strand].ppe);
      check('ledger.ppe-derived', JSON.stringify(need(r, 'ppe_from_hazards', strand)) === JSON.stringify(derived.filter((p) => !basePpe.has(p))), `${slug}.${strand}: ppe_from_hazards differs`);
    }
    check('ledger.ppe-derived', JSON.stringify(need(H, 'hazard_rooms', slug)) === JSON.stringify(Object.keys(base).filter((s) => conds[s].hazards.length)), `${slug}: hazard_rooms list differs`);
  }

  // ledger.placard-structural — the rule is in web/build_3d.py where the ledger says, and each room's placard follows it
  const loc = locateAll(b3d), pr = need(reg, 'placard_rule', 'compliance.json');
  for (const k of Object.keys(PLACARD_PATTERNS)) {
    check('ledger.placard-structural', loc[k] !== null, `web/build_3d.py: ${k} is not where the structural read expects`);
    check('ledger.placard-structural', loc[k] === need(need(pr, k, 'placard_rule'), 'line', k), `placard_rule.${k}.line ${pr[k].line} is not the located line ${loc[k]}`);
  }
  for (const [slug, H] of Object.entries(ledger)) {
    if (!(slug in fh)) continue;
    const conds = fh[slug].conditions;
    let hung = 0;
    for (const strand of Object.keys(base)) {
      const c = conds[strand], rc = c.hazards.length ? c : base[strand];
      const p = need(need(H.rooms, strand, slug), 'placard', strand);
      check('ledger.placard-structural', need(p, 'hung', strand) === (rc.ppe.length > 0) && JSON.stringify(need(p, 'items', strand)) === JSON.stringify(rc.ppe), `${slug}.${strand}: placard differs from the 3D layer's rule`);
      if (rc.ppe.length > 0) hung++;
    }
    check('ledger.placard-structural', need(H, 'placards_hung', slug) === hung, `${slug}: placards_hung ${H.placards_hung} != ${hung}`);
    check('ledger.placard-structural', need(H, 'placard_in_every_hazard_room', slug) === H.hazard_rooms.every((s) => conds[s].ppe.length > 0), `${slug}: placard_in_every_hazard_room differs`);
  }

  // ledger.signoff — through pack/hall_signoff.mjs, never by string
  const hallList = need(halls, 'halls', 'halls.json');
  let signed = 0;
  for (const h of hallList) {
    const slug = need(h, 'slug', 'hall'), claims = claimsHallSignoff(h.content_status);
    if (claims) signed++;
    if (!(slug in ledger)) { check('ledger.signoff', false, `${slug}: in halls.json but not in the ledger`); continue; }
    const s = need(ledger[slug], 'signoff', slug);
    check('ledger.signoff', need(s, 'claims_signoff', slug) === claims, `${slug}: ledger says claims_signoff=${s.claims_signoff}, hall_signoff.mjs says ${claims}`);
    check('ledger.signoff', need(s, 'content_status', slug) === ('content_status' in h ? h.content_status : null), `${slug}: content_status differs from halls.json`);
    check('ledger.signoff', JSON.stringify(need(s, 'problems', slug)) === JSON.stringify(validateHallContentStatus(slug, h)), `${slug}: sign-off problems differ`);
  }
  const ss = need(reg, 'signoff_statuses', 'compliance.json');
  check('ledger.signoff', JSON.stringify(need(ss, 'closed_set', 'signoff_statuses')) === JSON.stringify(HALL_CONTENT_STATUSES), 'closed status set differs from hall_signoff.mjs');
  check('ledger.signoff', need(need(reg, 'rollups', 'compliance.json'), 'halls_signed_off', 'rollups') === signed, `rollups.halls_signed_off ${reg.rollups.halls_signed_off} != ${signed} through hall_signoff.mjs`);

  // ledger.rubric — every seat's axes and pass rules are sims.json's, verbatim
  const simMap = need(sims, 'sims', 'sims.json'), seats = need(reg, 'seats', 'compliance.json');
  check('ledger.rubric', JSON.stringify(Object.keys(seats).sort()) === JSON.stringify(Object.keys(simMap).sort()), 'seat set differs from sims.json');
  for (const [sid, S] of Object.entries(seats)) {
    if (!(sid in simMap)) continue;
    const rub = need(simMap[sid], 'rubric', sid), axes = need(S, 'axes', sid);
    check('ledger.rubric', axes.length === rub.length, `${sid}: axis count differs`);
    axes.forEach((a, i) => {
      const r = rub[i];
      check('ledger.rubric', r !== undefined && need(a, 'axis', sid) === need(r, 'axis', sid) && need(a, 'pass', sid) === need(r, 'pass', sid) && need(a, 'gates', sid) === (r.pass !== 'informational'),
        `${sid}: axis ${a.axis} pass rule ${JSON.stringify(a.pass)} is not sims.json's ${JSON.stringify(r === undefined ? null : r.pass)}`);
    });
    check('ledger.rubric', need(S, 'every_axis_gates', sid) === rub.every((r) => r.pass !== 'informational'), `${sid}: every_axis_gates differs`);
    check('ledger.rubric', JSON.stringify(need(S, 'halls', sid)) === JSON.stringify(need(simMap[sid], 'halls', sid)), `${sid}: halls differ`);
  }
  const bindings = need(sims, 'hall_bindings', 'sims.json');
  for (const [slug, H] of Object.entries(ledger)) {
    const b = slug in bindings ? bindings[slug].map((x) => x.sim) : [];
    check('ledger.rubric', JSON.stringify(need(H, 'seats', slug).map((x) => x.sim)) === JSON.stringify(b), `${slug}: bound seats differ from sims.json hall_bindings`);
  }

  // ledger.rollups — every number sums from the rows
  const R = need(reg, 'rollups', 'compliance.json'), rows = Object.values(ledger);
  const exp = {
    halls: rows.length,
    halls_with_hazards: rows.filter((h) => h.hazards.length).length,
    halls_without_hazards: rows.filter((h) => !h.hazards.length).length,
    halls_with_ppe_required: rows.filter((h) => h.ppe_required_anywhere.length).length,
    halls_with_hazard_added_ppe: rows.filter((h) => h.ppe_from_hazards_anywhere.length).length,
    halls_with_placard_in_every_hazard_room: rows.filter((h) => h.hazards.length && h.placard_in_every_hazard_room).length,
    hazard_rooms: rows.reduce((n, h) => n + h.hazard_rooms.length, 0),
    hazard_rooms_with_placard: rows.reduce((n, h) => n + h.hazard_rooms.filter((s) => h.rooms[s].placard.hung).length, 0),
    rooms: rows.reduce((n, h) => n + Object.keys(h.rooms).length, 0),
    rooms_with_placard: rows.reduce((n, h) => n + h.placards_hung, 0),
    halls_signed_off: rows.filter((h) => h.signoff.claims_signoff).length,
    halls_with_signoff_problems: rows.filter((h) => h.signoff.problems.length).length,
    halls_with_a_lesson: rows.filter((h) => h.lessons.length).length,
    halls_with_hazards_and_a_lesson: rows.filter((h) => h.hazards.length && h.lessons.length).length,
    halls_with_a_lesson_covering_every_hazard_room: rows.filter((h) => h.lesson_covers_every_hazard_room === true).length,
    lessons: rows.reduce((n, h) => n + h.lessons.length, 0),
    lessons_with_a_hazard_room_walked_without_placard_step: rows.reduce((n, h) => n + h.lessons.filter((l) => l.hazard_rooms_walked_without_placard_step.length).length, 0),
    halls_with_a_seat: rows.filter((h) => h.seats.length).length,
    seat_bindings: rows.reduce((n, h) => n + h.seats.length, 0),
    seats: Object.keys(seats).length,
    seats_every_axis_gates: Object.values(seats).filter((s) => s.every_axis_gates).length,
    seats_with_an_informational_axis: Object.values(seats).filter((s) => !s.every_axis_gates).length,
    seats_with_scalar_threshold: Object.values(seats).filter((s) => s.threshold !== null).length,
  };
  for (const [k, v] of Object.entries(exp)) check('ledger.rollups', need(R, k, 'rollups') === v, `rollups.${k} is ${R[k]}, recomputed ${v}`);
  const cls = { evidenceable: 0, 'self-reported': 0, 'not-recordable': 0 };
  for (const h of rows) {
    cls['not-recordable'] += Object.keys(h.rooms).length + 1; // rooms + sign-off
    cls.evidenceable += h.seats.length;
    for (const l of h.lessons) for (const s of l.step_kinds) cls[need(s, 'ledger_class', l.lesson)]++;
  }
  check('ledger.rollups', JSON.stringify(need(R, 'items_by_ledger_class', 'rollups')) === JSON.stringify(cls), `rollups.items_by_ledger_class ${JSON.stringify(R.items_by_ledger_class)} != ${JSON.stringify(cls)}`);
  check('ledger.rollups', need(R, 'items', 'rollups') === cls.evidenceable + cls['self-reported'] + cls['not-recordable'], 'rollups.items does not sum');
  return tally;
}

/* The report over one record. */
export function report(record) {
  const lines = [];
  const fails = [];
  const base = verify(record);   // completion's own verifier: imported, never copied
  for (const [rule, t] of Object.entries(base.tally)) for (const f of t.fails) fails.push(`completion ${rule}: ${f}`);
  if (fails.length) return { lines, fails, halls: [] };
  const ledger = need(REG, 'halls', 'compliance.json'), seats = need(REG, 'seats', 'compliance.json');
  const ske = need(REG, 'step_kind_evidence', 'compliance.json');
  const simsBlock = need(record, 'sims', 'record');
  const touched = new Map();
  const touch = (slug, why) => { if (!touched.has(slug)) touched.set(slug, []); touched.get(slug).push(why); };
  for (const L of need(record, 'lessons', 'record')) {
    if (L.steps.some((s) => s.done) || L.complete) touch(need(L, 'hall', 'lesson'), `lesson ${L.lesson}`);
    for (const s of need(L, 'steps', L.lesson)) {
      // evidence.self-reported-carries-none: a self-reported step carries no evidence; one that does is a claim the bundle cannot back
      const cls = need(need(ske, need(s, 'kind', L.lesson), 'step_kind_evidence'), 'ledger_class', s.kind);
      if (cls === 'self-reported' && s.evidence !== null) fails.push(`evidence.self-reported-carries-none: ${L.lesson} step ${s.step} (${s.kind}) carries evidence, but a ${s.kind} step is self-reported and cannot be evidenced`);
    }
  }
  for (const [sid, s] of Object.entries(simsBlock)) {
    if (!(sid in seats)) continue;
    // evidence.seat-passed-in-record: a seat marked passed must be passed in the record's own sims block by a sim step it evidences
    if (s.passed === true) {
      const backed = record.lessons.some((L) => L.steps.some((st) => st.kind === 'sim' && st.done && st.evidence && st.evidence.sim === sid && st.evidence.passed === true));
      if (!backed) fails.push(`evidence.seat-passed-in-record: ${sid} is passed in record.sims but no done sim step evidences it`);
      for (const slug of seats[sid].halls) if (touched.has(slug)) touch(slug, `seat ${sid} passed`);
    }
  }
  if (fails.length) return { lines, fails, halls: [] };
  const R = need(REG, 'rollups', 'compliance.json');
  const nHalls = need(R, 'halls', 'rollups'), nSigned = need(R, 'halls_signed_off', 'rollups');
  lines.push(`compliance report: ${touched.size} hall${touched.size === 1 ? '' : 's'} touched by this record (of ${nHalls}); ledger built ${REG.built}, stamp ${REG.source_stamp}`);
  const stat = { evidenced: 0, 'self-reported': 0, 'not-evidenced': 0 };
  for (const [slug, whys] of touched) {
    const H = ledger[slug];
    lines.push('');
    lines.push(`hall ${slug} (${H.name}) — ${whys.join(', ')}`);
    lines.push(`  hazards: ${H.hazards.length ? H.hazards.join(', ') : 'none derived'}; hazard rooms: ${H.hazard_rooms.length ? H.hazard_rooms.join(', ') : 'none'}`);
    for (const [strand, r] of Object.entries(H.rooms)) {
      if (!r.hazard_room && !r.ppe.length) continue;
      const tag = r.hazard_room ? `hazard ${r.hazards.join('+')}` : 'no hazard';
      lines.push(`  room ${strand} [${tag}] PPE: ${r.ppe.join(', ')} — placard ${r.placard.hung ? 'hung' : 'not hung'} — not-evidenced (a room requirement is the bundle's fact; no record field carries it)`);
      stat['not-evidenced']++;
    }
    const recLessons = record.lessons.filter((L) => L.hall === slug);
    for (const l of H.lessons) {
      const rl = recLessons.find((x) => x.lesson === l.lesson);
      if (!rl) continue;
      lines.push(`  lesson ${l.lesson}: ${rl.complete ? 'complete' : 'in progress'} in the record; placard step in every hazard room: ${l.placard_step_in_every_hazard_room ? 'yes' : 'no'}`
        + (l.hazard_rooms_walked_without_placard_step.length ? `; GAP: walks ${l.hazard_rooms_walked_without_placard_step.join(', ')} without a placard step` : '')
        + (l.hazard_rooms_not_walked.length ? `; hazard rooms not walked: ${l.hazard_rooms_not_walked.join(', ')}` : ''));
      for (const st of rl.steps) {
        const k = l.step_kinds.find((x) => x.n === st.step);
        const cls = need(ske, st.kind, 'step_kind_evidence').ledger_class;
        let verdict;
        if (!st.done) verdict = 'not done';
        else if (cls === 'evidenceable' && st.evidence !== null) verdict = 'evidenced';
        else if (cls === 'self-reported') verdict = 'self-reported (done is the learner\'s word)';
        else verdict = 'not-evidenced';
        if (st.done) stat[verdict.startsWith('evidenced') ? 'evidenced' : verdict.startsWith('self') ? 'self-reported' : 'not-evidenced']++;
        lines.push(`    step ${st.step} ${st.kind} @${k ? k.where : '?'}: ${verdict}`);
      }
    }
    for (const b of H.seats) {
      const s = sid(b.sim);
      if (!s || s.passed !== true) { lines.push(`  seat ${b.sim}: not passed in this record`); continue; }
      const S = seats[b.sim];
      lines.push(`  seat ${b.sim} (${S.name}): passed — evidenced by record.sims and a sim step episode; decided by the seat's rule: `
        + S.axes.map((a) => `${a.axis} ${a.pass}`).join(', ') + ' — the axes are the seat\'s rule in sims.json, not the record\'s evidence; the record carries passed only');
      stat.evidenced++;
    }
    lines.push(`  sign-off: ${H.signoff.claims_signoff ? 'claims practitioner sign-off' : 'UNSIGNED — this hall\'s content is ' + H.signoff.status_read} (${nSigned} of ${nHalls} halls signed off today, read through ${H.signoff.read_through}) — not-evidenced (a hall\'s fact, not the record\'s)`);
    stat['not-evidenced']++;
    function sid(id) { return id in simsBlock ? simsBlock[id] : null; }
  }
  lines.push('');
  lines.push(`totals: ${stat.evidenced} evidenced, ${stat['self-reported']} self-reported, ${stat['not-evidenced']} not-evidenced items across the halls touched`);
  lines.push(`signature: ${base.signature.line}`);
  lines.push('this report is against the bundle\'s own rules, not any jurisdiction\'s; a signed record attests a key, not a person; nothing here is a certification or an inspection');
  return { lines, fails, halls: [...touched.keys()] };
}

const isMain = process.argv[1] && new URL(`file://${process.argv[1]}`).pathname === new URL(import.meta.url).pathname;
if (isMain) {
  const path = process.argv[2];
  if (!path) { console.error('FAIL usage: node compliance/verify.mjs <record.json>'); process.exit(1); }
  let failed = false;
  try {
    const tally = checkLedger(REG, null);
    for (const [rule, t] of Object.entries(tally)) {
      if (t.fails.length) { failed = true; console.error(`FAIL ${rule}: checked ${t.checked}, failing ${t.fails.length}`); for (const f of t.fails) console.error(`     ${f}`); }
    }
    if (failed) { console.error('the ledger itself fails; no report is printed over a ledger that does not re-derive'); process.exit(1); }
    const record = JSON.parse(readFileSync(path, 'utf8'));
    const { lines, fails } = report(record);
    for (const f of fails) console.error(`FAIL ${f}`);
    if (fails.length) failed = true;
    for (const l of lines) console.log(l);
  } catch (e) {
    failed = true;
    console.error(`FAIL verify: ${e.message}`);
  }
  process.exit(failed ? 1 : 0);
}
