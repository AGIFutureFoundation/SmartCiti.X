/**
 * Cohort Dashboard v1 verification (Sprint S4 gate).
 *
 * The gate: every figure on the dashboard reconciles, within 1%, with a
 * recomputation done HERE from the raw log by a separate route. The
 * recomputation below does not import cohort/dashboard.mjs's aggregation:
 * it reads raw JSON lines, groups hints with the outcome that follows them in
 * the same session (not by attempt_id), and uses its own copy of the hint
 * credit rule (1 - 0.15 x rung) - which also cross-checks control/hints.mjs.
 */
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { computeDashboard, parseLog, MIN_CELL_N } from './dashboard.mjs';
import { buildPage, renderPage, BANNER } from './build.mjs';
import { NEVER_EXPORT } from '../security/privacy.mjs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok', m); };
const at = (p) => fileURLToPath(new URL(p, import.meta.url));
const read = (p) => readFileSync(at(p), 'utf8');
const json = (p) => JSON.parse(read(p));

const logText = read('./fixtures/session_log.jsonl');
const pageText = read('./dashboard.html');
const coursesReg = json('../courses/registry/courses.json');
const skillsReg = json('../pack/registry/skills.json');
const sims = json('../sims/registry/sims.json');
const manifest = json('../pack/manifest.json');
const { dashboard: D } = buildPage();

// ---------------------------------------------------------------------------
// 1. Independent recomputation from raw lines
// ---------------------------------------------------------------------------
const raw = logText.trimEnd().split('\n');
const head = JSON.parse(raw[0]);
const events = [];
const gate = [];
const ids = new Set();
for (const line of raw.slice(1)) {
  const r = JSON.parse(line);
  if (r.stream === 'audit') { gate.push(r); continue; }
  if (ids.has(r.event_id)) continue;
  ids.add(r.event_id);
  events.push(r);
}
const credit = (rung) => 1 - 0.15 * rung;
const modulesOf = Object.fromEntries(coursesReg.courses.map((c) => [c.code, c.modules.length]));
const simOwner = {};
coursesReg.courses.forEach((c) => c.floor_sims.forEach((s) => { simOwner[s] = c.code; }));

// group by session, order by event_id sequence, pair hints with the next outcome
const sessions = {};
for (const e of events) (sessions[e.session_id] ??= []).push(e);
const outcomes = [];   // {learner, course, module, stage, pass, ms, rungs[], skills[]}
for (const sid of Object.keys(sessions)) {
  const evs = sessions[sid].slice().sort((a, b) => a.event_id.localeCompare(b.event_id));
  let pending = [];
  for (const e of evs) {
    if (e.verb === 'hint_requested') pending.push(e.payload.rung);
    else if (e.verb === 'completed' || e.verb === 'failed') {
      outcomes.push({ learner: e.learner_id, course: e.payload.course, module: e.payload.module,
        stage: e.payload.stage, pass: e.verb === 'completed', ms: e.payload.latency_ms,
        rungs: pending, skills: e.context.skill_ids });
      pending = [];
    }
  }
}
const R = { course: {}, learner: {}, rung: {}, skill: {} };
const bump = (o, k, f) => { o[k] ??= f(); return o[k]; };
for (const o of outcomes) {
  const c = bump(R.course, o.course, () => ({ L: new Set(), passKeys: new Set(), stagePass: {}, gT: 0, gP: 0, ms: 0, h: 0, hr: 0, ng: 0 }));
  const l = bump(R.learner, o.learner, () => ({ C: new Set(), passKeys: new Set(), gT: 0, gP: 0, ms: 0, h: 0, hr: 0 }));
  c.L.add(o.learner); l.C.add(o.course);
  const k = `${o.learner}/${o.course}/${o.module}/${o.stage}`;
  if (o.pass) { c.passKeys.add(k); l.passKeys.add(k); }
  if (o.stage === 'gate') { c.gT++; l.gT++; if (o.pass) { c.gP++; l.gP++; } } else c.ng++;
  c.ms += o.ms; l.ms += o.ms;
  c.h += o.rungs.length; l.h += o.rungs.length;
  for (const r of o.rungs) { c.hr += r; l.hr += r; const rr = bump(R.rung, r, () => ({ k: 0, L: new Set() })); rr.k++; rr.L.add(o.learner); }
  const sc = o.pass ? credit(o.rungs.length ? Math.max(...o.rungs) : 0) : 0;
  for (const s of o.skills) bump(bump(R.skill, s, () => ({})), o.learner, () => []).push(sc);
}
for (const [code, c] of Object.entries(R.course)) {
  for (const k of c.passKeys) { const st = k.split('/')[3]; c.stagePass[st] = (c.stagePass[st] ?? 0) + 1; }
  c.deny = gate.filter((g) => simOwner[g.skill] === code && c.L.has(g.learner) && g.action.endsWith('.deny')).length;
  c.checks = gate.filter((g) => simOwner[g.skill] === code && c.L.has(g.learner)).length;
}

// ---------------------------------------------------------------------------
// 2. Reconcile every figure
// ---------------------------------------------------------------------------
let maxErr = 0;
let compared = 0;
const worst = [];
function rec(label, dash, indep) {
  if (dash === null || dash === undefined) return;
  const err = Math.abs(dash - indep) / Math.max(Math.abs(indep), 1e-9);
  const e = indep === 0 && dash === 0 ? 0 : err;
  compared++;
  if (e > maxErr) maxErr = e;
  if (e > 0.01) worst.push(`${label}: dashboard ${dash} vs recomputed ${indep}`);
}
let suppressionOk = true;
const checkCell = (label, cell, nIndep, vIndep) => {
  if (cell.n !== nIndep) { suppressionOk = false; worst.push(`${label}: n ${cell.n} vs ${nIndep}`); }
  if (cell.suppressed !== (nIndep < 5) || (cell.suppressed && cell.value !== null)) suppressionOk = false;
  if (!cell.suppressed) rec(label, cell.value, vIndep);
};

for (const row of D.courses) {
  const c = R.course[row.code];
  const nL = c ? c.L.size : 0;
  const M = modulesOf[row.code];
  checkCell(`${row.code} completion`, row.cells.completion, nL, c ? c.passKeys.size / (nL * M * 4) : 0);
  checkCell(`${row.code} gate pass`, row.cells.gate_pass_rate, nL, c && c.gT ? c.gP / c.gT : 0);
  checkCell(`${row.code} minutes`, row.cells.minutes_per_learner, nL, c ? c.ms / 60000 / nL : 0);
  checkCell(`${row.code} hints/attempt`, row.cells.hints_per_attempt, nL, c && c.ng ? c.h / c.ng : 0);
  checkCell(`${row.code} mean rung`, row.cells.mean_rung, nL, c && c.h ? c.hr / c.h : 0);
  if (row.cells.refusals.value !== null) checkCell(`${row.code} refusals`, row.cells.refusals, nL, c.deny);
  if (row.cells.refusal_rate.value !== null) checkCell(`${row.code} refusal rate`, row.cells.refusal_rate, nL, c.deny / c.checks);
  for (const st of ['home', 'class', 'floor', 'gate']) {
    checkCell(`${row.code} ${st}`, row.by_stage[st], nL, c ? (c.stagePass[st] ?? 0) / (nL * M) : 0);
  }
}
for (const row of D.learners) {
  const l = R.learner[row.learner];
  const total = [...l.C].reduce((s, code) => s + modulesOf[code] * 4, 0);
  rec(`${row.learner} completion`, row.completion, l.passKeys.size / total);
  rec(`${row.learner} stages`, row.stages_done, l.passKeys.size);
  rec(`${row.learner} gate`, row.gate_pass_rate, l.gT ? l.gP / l.gT : null);
  rec(`${row.learner} minutes`, row.minutes, l.ms / 60000);
  rec(`${row.learner} hints`, row.hints, l.h);
  rec(`${row.learner} mean rung`, row.mean_rung, l.h ? l.hr / l.h : null);
  rec(`${row.learner} refusals`, row.refusals, gate.filter((g) => g.learner === row.learner && g.action.endsWith('.deny')).length);
}
for (const [r, cell] of Object.entries(D.hint_rungs)) {
  const x = R.rung[r] ?? { k: 0, L: new Set() };
  checkCell(`rung ${r}`, cell, x.L.size, x.k);
}
const gN = new Set(gate.map((g) => g.learner)).size;
const gDeny = gate.filter((g) => g.action === 'safety_gate.deny').length;
checkCell('safety checks', D.safety.checks, gN, gate.length);
checkCell('safety refusals', D.safety.refusals, gN, gDeny);
checkCell('safety refusal rate', D.safety.refusal_rate, gN, gDeny / gate.length);
for (const [sid, per] of Object.entries(R.skill)) {
  const means = Object.values(per).map((a) => a.reduce((x, y) => x + y, 0) / a.length);
  const cell = D.skill_map.cells[sid];
  if (!cell) { suppressionOk = false; worst.push(`skill ${sid} missing from dashboard`); continue; }
  checkCell(`skill ${sid}`, cell, means.length, means.reduce((x, y) => x + y, 0) / means.length);
}

ok(`the log header declares itself synthetic ("${head.note}")`,
  head.synthetic === true && head.note === 'generated test data; no real learner' && D.synthetic === true);
ok('the log header carries the pack_version from pack/manifest.json', head.pack_version === manifest.pack_version);
ok(`S4 gate: ${compared} dashboard figures reconcile with the independent recomputation within 1% (max error ${(maxErr * 100).toFixed(4)}%)`,
  compared > 300 && maxErr <= 0.01 && worst.length === 0 || (console.error(worst.slice(0, 10).join('\n')), false));
ok('every skill id and every course in the recomputation appears on the dashboard with the same learner n',
  suppressionOk && Object.keys(R.skill).length === Object.keys(D.skill_map.cells).length);
ok(`small-group suppression: every cell with n<${MIN_CELL_N} is suppressed and carries no value (${D.suppressed_cells} of ${D.total_cells} cells)`,
  MIN_CELL_N === 5 && suppressionOk && D.suppressed_cells > 0);
const small = D.courses.filter((c) => c.n < 5);
ok(`courses under 5 learners (${small.map((c) => `${c.code} n=${c.n}`).join(', ')}) show only "n<5" for every figure`,
  small.length >= 2 && small.every((c) => [...Object.values(c.cells), ...Object.values(c.by_stage)].every((x) => x.suppressed && x.value === null)));

// ---------------------------------------------------------------------------
// 3. The page shows what was computed, and suppressed cells stay suppressed
// ---------------------------------------------------------------------------
const rowOf = (code) => pageText.split('\n').find((l) => l.startsWith(`<tr><th scope="row">${code}</th><td class="t">`)) ?? '';
ok('each course row on the page prints the computed completion and gate pass rate (1 dp)',
  D.courses.filter((c) => !c.suppressed).every((c) => rowOf(c.code).includes(`<td>${(c.cells.completion.value * 100).toFixed(1)}%</td>`)
    && rowOf(c.code).includes(`<td>${(c.cells.gate_pass_rate.value * 100).toFixed(1)}%</td>`)));
ok('suppressed course rows on the page print "n<5" and no percentage',
  small.every((c) => { const r = rowOf(c.code); return r.includes('n&lt;5') && !/\d%</.test(r); }));
ok('the skill-map grid draws one tile per skill id on the dashboard',
  (pageText.match(/class="tile/g) ?? []).length === D.skill_map.rows.reduce((s, r) => s + r.skills.length, 0));

// ---------------------------------------------------------------------------
// 4. Privacy: no affect anywhere, and a planted affect field never surfaces
// ---------------------------------------------------------------------------
const affectRe = new RegExp(`"[^"]*(${NEVER_EXPORT.join('|')})[^"]*"\\s*:`, 'i');
ok('no affect key appears anywhere in the session log', !affectRe.test(logText));
ok('no affect word (affect, anxiety, boredom, flow state) appears on the page',
  !/\b(affect|anxiety|anxious|boredom|bored|flow state)\b/i.test(pageText.replace('Affect data is never read or shown', '')));
const planted = parseLog(logText);
const victim = planted.rows.find((r) => r.stream === 'telemetry' && r.verb === 'completed');
planted.rows.push({ ...victim, event_id: 'planted:1', payload: { ...victim.payload, affect_state: 'ANXIETY', anxiety: 0.9 } });
planted.rows.push({ ...victim });   // an at-least-once duplicate
const P = computeDashboard(planted, { courses: coursesReg, skills: skillsReg });
const Pjson = JSON.stringify(P);
ok('a row carrying affect fields is dropped before aggregation and a duplicate event_id is deduped',
  P.counts.dropped_banned === 1 && P.counts.attempts === D.counts.attempts && !/anxiety|affect_state/i.test(Pjson)
  && !/ANXIETY/.test(renderPage(P, { packVersion: manifest.pack_version })));
ok('learner ids are bare pseudonyms L01..L24: no name, email or device field in the log',
  D.learners.every((l) => /^L\d{2}$/.test(l.learner)) && D.learners.length === 24
  && !/"(name|email|device_id|ip)"\s*:/.test(logText) && !/@/.test(logText));

// ---------------------------------------------------------------------------
// 5. The page is static, self-contained and labelled
// ---------------------------------------------------------------------------
ok(`the page carries the banner "${BANNER}" at the top and in the footer`,
  pageText.indexOf(BANNER) > 0 && pageText.indexOf(BANNER) < pageText.indexOf('<h1>')
  && pageText.lastIndexOf(BANNER) > pageText.indexOf('<footer'));
ok('the page has no external URL, script, fetch, link or import',
  !/https?:\/\/|\/\/[a-z0-9-]+\.[a-z]/i.test(pageText) && !/<script|<link|fetch\(|@import|src=/i.test(pageText));
ok('the page names the product "SmartCiti.X : Trade Craft Academy" powered by AGI Corp and the pack version',
  pageText.includes('SmartCiti.X : Trade Craft Academy') && pageText.includes('powered by AGI Corp')
  && pageText.includes(`pack ${manifest.pack_version}`));

// ---------------------------------------------------------------------------
// 6. Determinism
// ---------------------------------------------------------------------------
const regen = execFileSync('python3', [at('./synth_log.py'), '--stdout'], { encoding: 'utf8', maxBuffer: 64 << 20 });
ok('rebuilding the synthetic log is byte-identical to the committed fixture', regen === logText);
const rebuilt = execFileSync(process.execPath, [at('./build.mjs'), '--stdout'], { encoding: 'utf8', maxBuffer: 64 << 20 });
ok('rebuilding the page is byte-identical to cohort/dashboard.html', rebuilt === pageText);

// ---------------------------------------------------------------------------
// 7. Every id resolves in its registry
// ---------------------------------------------------------------------------
const codes = new Set(coursesReg.courses.map((c) => c.code));
const skillSet = new Set(skillsReg.skills.map((s) => s.skill_id));
const halls = new Set(skillsReg.skills.map((s) => s.skill_id.split('.')[0]));
ok(`every course code in the log resolves in courses/registry/courses.json, and all ${codes.size} courses are covered`,
  events.every((e) => codes.has(e.payload.course)) && new Set(events.map((e) => e.payload.course)).size === codes.size);
ok(`every skill id in the log and on the dashboard (${Object.keys(D.skill_map.cells).length}) resolves in pack/registry/skills.json`,
  events.every((e) => e.context.skill_ids.every((s) => skillSet.has(s)))
  && Object.entries(D.skill_map.cells).every(([s, c]) => skillSet.has(s) && c.resolves));
ok('every module id and stage resolves: module n exists on its course, stage is one of the registry stage_map',
  events.every((e) => {
    const c = coursesReg.courses.find((x) => x.code === e.payload.course);
    return c.modules.some((m) => m.n === e.payload.module)
      && coursesReg.stage_map.some((s) => s.stage === e.payload.stage)
      && e.context.module_id === `${e.payload.course}.m${e.payload.module}.${e.payload.stage}`;
  }));
ok('every safety-gate row targets a simulator in sims/registry/sims.json that is one of its course floor_sims',
  gate.length > 0 && gate.every((g) => g.skill in sims.sims && simOwner[g.skill]
    && g.action.startsWith('safety_gate.') && /^L\d{2}$/.test(g.learner)));
const noHall = coursesReg.courses.filter((c) => !c.halls.length).map((c) => c.code);
ok(`courses with no hall (${noHall.join(', ')}) say "no skill-graph mapping" and carry no skill ids`,
  noHall.length > 0 && D.skill_map.rows.filter((r) => noHall.includes(r.code)).every((r) => r.mapping === 'no skill-graph mapping' && !r.skills.length)
  && events.filter((e) => noHall.includes(e.payload.course)).every((e) => e.context.skill_ids.length === 0)
  && (pageText.match(/no skill-graph mapping/g) ?? []).length === noHall.length);
ok('every mapped course\'s skill ids sit in that course\'s own halls',
  D.skill_map.rows.every((r) => r.skills.every((s) => r.halls.includes(s.split('.')[0]) && halls.has(s.split('.')[0]))));
ok('every telemetry verb is an ACP-01 verb and every envelope carries the bus/telemetry.mjs fields',
  events.every((e) => ['attempted', 'hint_requested', 'completed', 'failed'].includes(e.verb)
    && ['event_id', 'ts', 'clock_skew_ms', 'ts_source', 'learner_id', 'session_id', 'context', 'verb', 'payload'].every((k) => k in e)
    && ['module_id', 'skill_ids', 'difficulty', 'modality', 'device_tier', 'scaffold_level'].every((k) => k in e.context)));
ok('the gate (verify) stage is hint-free in the log, as control/hints.mjs requires of a verification run',
  outcomes.filter((o) => o.stage === 'gate').every((o) => o.rungs.length === 0)
  && outcomes.every((o) => o.rungs.every((r) => r >= 1 && r <= 5)));

console.log(`cohort: ${n} checks passed; reconciliation max error ${(maxErr * 100).toFixed(4)}% over ${compared} figures; ${D.suppressed_cells}/${D.total_cells} cells suppressed`);
