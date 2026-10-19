/**
 * SmartCiti.X : Trade Craft Academy (powered by AGI Corp) - Cohort Dashboard v1.
 *
 * Pure functions: raw session log lines in, dashboard figures out. Nothing here
 * reads a file, a clock or a random source, so the same log always yields the
 * same figures (cohort/build.mjs does the I/O; cohort/test.mjs recomputes every
 * figure independently and reconciles).
 *
 * Input shapes are the repository's own:
 *   - telemetry rows: the ACP-01 envelope from bus/telemetry.mjs envelope()
 *     (event_id, ts, learner_id, session_id, context{module_id, skill_ids,..},
 *     verb, payload). Deduped on event_id - transport is at-least-once.
 *   - audit rows: safety_gate.allow / safety_gate.deny rows in the
 *     bus/audit.mjs AuditLog shape (learner, skill = the simulator target).
 *   - courses: courses_roadmap/registry/courses.json; skills: pack/registry/skills.json.
 *
 * Privacy (security/privacy.mjs): every row is filtered through NEVER_EXPORT
 * and NEVER_STORE key checks before use, so an affect field in a log can never
 * reach a figure. Cohort cells are CLASS.AGGREGATE; privacy.mjs defines no
 * small-group threshold, so this module declares MIN_CELL_N = 5 and suppresses
 * any aggregate over fewer distinct learners (shown as "n<5").
 */
import { NEVER_EXPORT, NEVER_STORE, CLASS } from '../security/privacy.mjs';
import { creditFor } from '../control/hints.mjs';

export const MIN_CELL_N = 5;
export const SUPPRESSED = 'n<5';
export const NO_MAPPING = 'no skill-graph mapping';
export const STAGES = Object.freeze(['home', 'class', 'floor', 'gate']);
export const CELL_CLASS = CLASS.AGGREGATE;

const BANNED = [...NEVER_EXPORT, ...NEVER_STORE];

/** True when any key at any depth names an affect or raw-stream field. */
export function hasBannedKey(v) {
  if (Array.isArray(v)) return v.some(hasBannedKey);
  if (v && typeof v === 'object') {
    return Object.entries(v).some(([k, x]) =>
      BANNED.some((b) => k.toLowerCase().includes(b)) || hasBannedKey(x));
  }
  return false;
}

/** Split JSONL text into header + rows. */
export function parseLog(text) {
  const lines = text.split('\n').filter((l) => l.trim());
  const header = JSON.parse(lines[0]);
  const rows = lines.slice(1).map((l) => JSON.parse(l));
  return { header, rows };
}

/** A cohort cell: value plus the distinct-learner n it rests on. */
function cell(value, n) {
  return n < MIN_CELL_N ? { n, suppressed: true, value: null } : { n, suppressed: false, value };
}

const sum = (a) => a.reduce((x, y) => x + y, 0);
const mean = (a) => (a.length ? sum(a) / a.length : null);

/**
 * Collapse telemetry into attempts keyed by payload.attempt_id.
 * An attempt: {learner, course, module, stage, skill_ids, outcome, latency_ms, rungs[]}.
 */
function attemptsOf(telemetry) {
  const byId = new Map();
  for (const e of telemetry) {
    const p = e.payload ?? {};
    const id = p.attempt_id;
    if (!id) continue;
    if (!byId.has(id)) {
      byId.set(id, { id, learner: e.learner_id, course: p.course, module: p.module, stage: p.stage,
        skill_ids: e.context?.skill_ids ?? [], outcome: null, latency_ms: 0, rungs: [] });
    }
    const a = byId.get(id);
    if (e.verb === 'hint_requested') a.rungs.push(p.rung ?? 1);
    if (e.verb === 'completed' || e.verb === 'failed') {
      a.outcome = e.verb;
      a.latency_ms = Number.isFinite(p.latency_ms) ? p.latency_ms : 0;
    }
  }
  return [...byId.values()].sort((x, y) => (x.id < y.id ? -1 : x.id > y.id ? 1 : 0));
}

/**
 * Compute the full dashboard.
 * @param {{header:object, rows:object[]}} log  parsed session log
 * @param {{courses:object, skills:object}} reg courses.json and skills.json
 */
export function computeDashboard(log, { courses, skills }) {
  const seen = new Set();
  const telemetry = [];
  const audit = [];
  let droppedBanned = 0;
  for (const r of log.rows) {
    if (hasBannedKey(r)) { droppedBanned++; continue; }
    if (r.stream === 'telemetry') {
      if (seen.has(r.event_id)) continue;
      seen.add(r.event_id);
      telemetry.push(r);
    } else if (r.stream === 'audit') audit.push(r);
  }

  const courseList = courses.courses;
  const courseBy = new Map(courseList.map((c) => [c.code, c]));
  const skillIds = new Set(skills.skills.map((s) => s.skill_id));
  const simCourse = new Map();
  for (const c of courseList) for (const s of c.floor_sims) {
    if (simCourse.has(s)) throw new Error(`simulator ${s} is on two courses; refusals cannot be attributed`);
    simCourse.set(s, c.code);
  }

  const attempts = attemptsOf(telemetry).filter((a) => a.outcome);
  const learners = [...new Set(telemetry.map((e) => e.learner_id))].sort();

  // ---- per learner x course -------------------------------------------------
  const lc = new Map();   // `${learner}|${course}` -> state
  const key = (l, c) => `${l}|${c}`;
  for (const a of attempts) {
    const k = key(a.learner, a.course);
    if (!lc.has(k)) lc.set(k, { learner: a.learner, course: a.course, done: new Set(), stageDone: {},
      stageTried: new Set(), gateTries: 0, gatePasses: 0, ms: 0, hints: 0, rungSum: 0, nonGate: 0 });
    const s = lc.get(k);
    const stageKey = `${a.module}.${a.stage}`;
    s.stageTried.add(a.stage);
    if (a.outcome === 'completed') s.done.add(stageKey);
    if (a.stage === 'gate') { s.gateTries++; if (a.outcome === 'completed') s.gatePasses++; }
    else s.nonGate++;
    s.ms += a.latency_ms;
    s.hints += a.rungs.length;
    s.rungSum += sum(a.rungs);
  }
  const stagesTotal = (code) => courseBy.get(code).modules.length * STAGES.length;
  const stageDoneCount = (s, stage) => [...s.done].filter((d) => d.endsWith(`.${stage}`)).length;

  const learnerRows = learners.map((l) => {
    const mine = [...lc.values()].filter((s) => s.learner === l)
      .sort((a, b) => (a.course < b.course ? -1 : 1));
    const done = sum(mine.map((s) => s.done.size));
    const total = sum(mine.map((s) => stagesTotal(s.course)));
    const gT = sum(mine.map((s) => s.gateTries));
    const gP = sum(mine.map((s) => s.gatePasses));
    const hints = sum(mine.map((s) => s.hints));
    return {
      learner: l, courses: mine.map((s) => s.course),
      stages_done: done, stages_total: total, completion: total ? done / total : 0,
      gate_attempts: gT, gate_passes: gP, gate_pass_rate: gT ? gP / gT : null,
      minutes: sum(mine.map((s) => s.ms)) / 60000,
      hints, mean_rung: hints ? sum(mine.map((s) => s.rungSum)) / hints : null,
      refusals: audit.filter((r) => r.learner === l && r.action === 'safety_gate.deny').length,
    };
  });

  // ---- per course (cohort cells) ---------------------------------------------
  const courseRows = courseList.map((c) => {
    const states = [...lc.values()].filter((s) => s.course === c.code);
    const n = states.length;
    const T = stagesTotal(c.code);
    const gT = sum(states.map((s) => s.gateTries));
    const gP = sum(states.map((s) => s.gatePasses));
    const hints = sum(states.map((s) => s.hints));
    const nonGate = sum(states.map((s) => s.nonGate));
    const enrolled = new Set(states.map((s) => s.learner));
    const deny = audit.filter((r) => simCourse.get(r.skill) === c.code && r.action === 'safety_gate.deny'
      && enrolled.has(r.learner));
    const checks = audit.filter((r) => simCourse.get(r.skill) === c.code && enrolled.has(r.learner));
    const byStage = {};
    for (const st of STAGES) {
      byStage[st] = cell(sum(states.map((s) => stageDoneCount(s, st))) / (n * c.modules.length || 1), n);
    }
    return {
      code: c.code, title: c.title, level: c.level, halls: c.halls, n,
      suppressed: n < MIN_CELL_N,
      cells: {
        completion: cell(n ? sum(states.map((s) => s.done.size)) / (n * T) : 0, n),
        gate_pass_rate: cell(gT ? gP / gT : 0, n),
        minutes_per_learner: cell(n ? sum(states.map((s) => s.ms)) / 60000 / n : 0, n),
        hints_per_attempt: cell(nonGate ? hints / nonGate : 0, n),
        mean_rung: cell(hints ? sum(states.map((s) => s.rungSum)) / hints : 0, n),
        refusals: cell(c.floor_sims.length ? deny.length : null, n),
        refusal_rate: cell(checks.length ? deny.length / checks.length : null, n),
      },
      by_stage: byStage,
    };
  });

  // ---- hint-rung usage (cohort) -----------------------------------------------
  const rungCounts = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
  const rungLearners = { 1: new Set(), 2: new Set(), 3: new Set(), 4: new Set(), 5: new Set() };
  for (const a of attempts) for (const r of a.rungs) { rungCounts[r]++; rungLearners[r].add(a.learner); }
  const hintRungs = Object.fromEntries(Object.keys(rungCounts).map((r) =>
    [r, cell(rungCounts[r], rungLearners[r].size)]));

  // ---- safety gate (cohort) -----------------------------------------------------
  const allow = audit.filter((r) => r.action === 'safety_gate.allow').length;
  const deny = audit.filter((r) => r.action === 'safety_gate.deny').length;
  const safetyN = new Set(audit.map((r) => r.learner)).size;
  const safety = { checks: cell(allow + deny, safetyN), refusals: cell(deny, safetyN),
    refusal_rate: cell(allow + deny ? deny / (allow + deny) : 0, safetyN) };

  // ---- skill map: skill_id -> mastery estimate -----------------------------------
  // Per learner per skill: mean over outcomes of (passed ? creditFor(max rung) : 0),
  // the hint credit table from control/hints.mjs - a co-completed pass is not
  // an unaided pass. Cohort value: mean over learners with evidence; cell n is
  // that learner count.
  const perSkill = new Map();   // skill -> Map(learner -> scores[])
  for (const a of attempts) {
    const score = a.outcome === 'completed' ? creditFor(a.rungs.length ? Math.max(...a.rungs) : 0) : 0;
    for (const sid of a.skill_ids) {
      if (!perSkill.has(sid)) perSkill.set(sid, new Map());
      const m = perSkill.get(sid);
      if (!m.has(a.learner)) m.set(a.learner, []);
      m.get(a.learner).push(score);
    }
  }
  const skillCells = {};
  for (const sid of [...perSkill.keys()].sort()) {
    const m = perSkill.get(sid);
    const per = [...m.values()].map(mean);
    skillCells[sid] = { ...cell(mean(per), per.length), resolves: skillIds.has(sid) };
  }
  const skillRows = courseList.map((c) => {
    if (!c.halls.length) return { code: c.code, title: c.title, halls: [], mapping: NO_MAPPING, skills: [] };
    const sk = Object.keys(skillCells).filter((sid) => c.halls.includes(sid.split('.')[0])
      && attempts.some((a) => a.course === c.code && a.skill_ids.includes(sid))).sort();
    return { code: c.code, title: c.title, halls: c.halls, mapping: 'hall skill graph', skills: sk };
  });

  // ---- suppression accounting ------------------------------------------------------
  const allCells = [
    ...courseRows.flatMap((r) => [...Object.values(r.cells), ...Object.values(r.by_stage)]),
    ...Object.values(hintRungs), ...Object.values(safety), ...Object.values(skillCells),
  ];
  return {
    header: log.header,
    synthetic: log.header?.synthetic === true,
    min_cell_n: MIN_CELL_N,
    counts: { telemetry: telemetry.length, audit: audit.length, attempts: attempts.length,
      learners: learners.length, dropped_banned: droppedBanned },
    learners: learnerRows,
    courses: courseRows,
    hint_rungs: hintRungs,
    safety,
    skill_map: { cells: skillCells, rows: skillRows },
    suppressed_cells: allCells.filter((c) => c.suppressed).length,
    total_cells: allCells.length,
  };
}
