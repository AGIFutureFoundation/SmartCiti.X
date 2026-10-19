#!/usr/bin/env node
/**
 * SmartCiti.X : Trade Craft Academy (powered by AGI Corp) - Cohort Dashboard v1 page.
 *
 * Reads the synthetic session log and the registries, computes the dashboard
 * with cohort/dashboard.mjs, and writes cohort/dashboard.html: one static,
 * self-contained page (inline CSS, no script, no external fetch, no clock).
 * Rebuilding from the same log writes the same bytes.
 *
 *   node cohort/build.mjs           writes cohort/dashboard.html
 *   node cohort/build.mjs --stdout  prints the same bytes, writes nothing
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { parseLog, computeDashboard, MIN_CELL_N, SUPPRESSED, STAGES } from './dashboard.mjs';

const at = (p) => fileURLToPath(new URL(p, import.meta.url));
const readJson = (p) => JSON.parse(readFileSync(at(p), 'utf8'));

export const BANNER = 'Synthetic data — not real learners';

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const pct = (v) => `${(v * 100).toFixed(1)}%`;
const num = (v, d = 1) => v.toFixed(d);

function show(c, fmt) {
  if (c.suppressed) return `<td class="sup" title="fewer than ${MIN_CELL_N} learners">${esc(SUPPRESSED)}</td>`;
  if (c.value === null) return '<td class="na">—</td>';
  return `<td>${fmt(c.value)}</td>`;
}

function heat(v) {
  // 0..1 -> a single-hue ramp; text stays dark on light cells and vice versa.
  const l = Math.round(94 - v * 52);
  return `background:hsl(196 62% ${l}%);color:${l < 60 ? '#fff' : '#10202a'}`;
}

export function renderPage(d, { packVersion }) {
  const courseRows = d.courses.map((c) => `<tr><th scope="row">${esc(c.code)}</th><td class="t">${esc(c.title)}</td>`
    + `<td>${c.n}</td>${show(c.cells.completion, pct)}${show(c.cells.gate_pass_rate, pct)}`
    + `${show(c.cells.minutes_per_learner, (v) => num(v, 0))}${show(c.cells.hints_per_attempt, (v) => num(v, 2))}`
    + `${show(c.cells.mean_rung, (v) => num(v, 2))}${show(c.cells.refusals, (v) => String(v))}`
    + `${show(c.cells.refusal_rate, pct)}</tr>`).join('\n');

  const stageRows = d.courses.map((c) => `<tr><th scope="row">${esc(c.code)}</th>`
    + STAGES.map((s) => show(c.by_stage[s], pct)).join('') + '</tr>').join('\n');

  const learnerRows = d.learners.map((l) => `<tr><th scope="row">${esc(l.learner)}</th>`
    + `<td class="t">${l.courses.map(esc).join(', ')}</td><td>${l.stages_done}/${l.stages_total}</td>`
    + `<td>${pct(l.completion)}</td><td>${l.gate_passes}/${l.gate_attempts}</td>`
    + `<td>${l.gate_pass_rate === null ? '—' : pct(l.gate_pass_rate)}</td><td>${num(l.minutes, 0)}</td>`
    + `<td>${l.hints}</td><td>${l.mean_rung === null ? '—' : num(l.mean_rung, 2)}</td><td>${l.refusals}</td></tr>`).join('\n');

  const rungRow = Object.entries(d.hint_rungs).map(([r, c]) => `<tr><th scope="row">rung ${r}</th>${show(c, String)}<td>${c.n}</td></tr>`).join('\n');

  const skillBlocks = d.skill_map.rows.map((r) => {
    if (!r.skills.length) {
      return `<section class="sk"><h3>${esc(r.code)} <span>${esc(r.title)}</span></h3><p class="nomap">${esc(r.mapping)}</p></section>`;
    }
    const tiles = r.skills.map((sid) => {
      const c = d.skill_map.cells[sid];
      const [hall, strand, tier] = sid.split('.');
      const body = c.suppressed ? `<b>${esc(SUPPRESSED)}</b>` : `<b>${pct(c.value)}</b>`;
      const style = c.suppressed ? 'class="tile sup"' : `class="tile" style="${heat(c.value)}"`;
      return `<div ${style} title="${esc(sid)} (n=${c.n})"><code>${esc(hall)}</code><span>${esc(strand)} · ${esc(tier)}</span>${body}</div>`;
    }).join('');
    return `<section class="sk"><h3>${esc(r.code)} <span>${esc(r.title)}</span></h3><div class="grid">${tiles}</div></section>`;
  }).join('\n');

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cohort Dashboard</title>
<style>
:root{--bg:#f6f8fa;--fg:#10202a;--mut:#5a6b76;--card:#fff;--line:#d8e0e6;--warn:#8a3b00;--warnbg:#fff1e0;--sup:#eceff2}
@media (prefers-color-scheme:dark){:root{--bg:#0e161c;--fg:#e6edf2;--mut:#93a4b0;--card:#16212a;--line:#2a3843;--warn:#ffcf99;--warnbg:#3a2410;--sup:#22303a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header,main,footer{max-width:1100px;margin:0 auto;padding:16px}
.banner{background:var(--warnbg);color:var(--warn);border:2px solid currentColor;border-radius:8px;padding:10px 14px;font-weight:700;font-size:16px;text-align:center}
h1{font-size:22px;margin:14px 0 2px}h2{font-size:17px;margin:28px 0 8px}h3{font-size:14px;margin:0 0 6px}h3 span{font-weight:400;color:var(--mut)}
.sub,.note{color:var(--mut)}.note{font-size:12.5px}
.wrap{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{padding:6px 9px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th[scope=row],.t{text-align:left}td.t{white-space:normal;min-width:180px}thead th{font-size:12px;color:var(--mut);text-align:right}thead th:first-child{text-align:left}
td.sup{background:var(--sup);color:var(--mut);font-style:italic}td.na{color:var(--mut)}
.sk{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin:8px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:6px}
.tile{border-radius:6px;padding:6px 8px;display:flex;flex-direction:column;gap:1px;font-size:12px}.tile b{font-size:15px}
.tile.sup{background:var(--sup);color:var(--mut)}.nomap{margin:0;color:var(--mut);font-style:italic}
</style>
</head>
<body>
<header>
<div class="banner" role="note">${BANNER}</div>
<h1>Cohort Dashboard v1</h1>
<div class="sub">SmartCiti.X : Trade Craft Academy — powered by AGI Corp · pack ${esc(packVersion)}</div>
<p class="note">Computed from <code>cohort/fixtures/session_log.jsonl</code>, a generated log (${d.counts.learners} fictional pseudonyms, ${d.counts.attempts} attempts, ${d.counts.audit} safety-gate checks). Learner ids are pseudonyms with no identity behind them. Affect data is never read or shown. Any cohort cell resting on fewer than ${MIN_CELL_N} learners is suppressed and shown as “${esc(SUPPRESSED)}” (${d.suppressed_cells} of ${d.total_cells} cells).</p>
</header>
<main>
<h2>Courses</h2>
<div class="wrap"><table>
<thead><tr><th>Course</th><th class="t">Title</th><th>Learners</th><th>Stage completion</th><th>Gate pass rate</th><th>Minutes / learner</th><th>Hints / attempt</th><th>Mean hint rung</th><th>Safety-gate refusals</th><th>Refusal rate</th></tr></thead>
<tbody>
${courseRows}
</tbody></table></div>
<p class="note">Gate pass rate = passed verify-stage attempts / all verify-stage attempts. Hints per attempt counts non-gate attempts only (the gate stage is hint-free). Refusals are <code>safety_gate.deny</code> rows on the course's floor simulators; “—” means the course has no simulator seat.</p>

<h2>Stage completion by course</h2>
<div class="wrap"><table>
<thead><tr><th>Course</th>${STAGES.map((s) => `<th>${s}</th>`).join('')}</tr></thead>
<tbody>
${stageRows}
</tbody></table></div>

<h2>Hint-rung usage</h2>
<div class="wrap"><table>
<thead><tr><th>Rung</th><th>Requests</th><th>Learners</th></tr></thead>
<tbody>
${rungRow}
</tbody></table></div>

<h2>Safety gate</h2>
<div class="wrap"><table>
<thead><tr><th>Measure</th><th>Value</th></tr></thead>
<tbody>
<tr><th scope="row">checks</th>${show(d.safety.checks, String)}</tr>
<tr><th scope="row">refusals</th>${show(d.safety.refusals, String)}</tr>
<tr><th scope="row">refusal rate</th>${show(d.safety.refusal_rate, pct)}</tr>
</tbody></table></div>

<h2>Skill map</h2>
<p class="note">Mastery estimate per skill id (<code>hall.strand.tier</code> from the pack skill graph): mean over learners of each learner's mean attempt score, where a pass scores the hint credit of its deepest rung (control/hints.mjs) and a fail scores 0. The module-to-strand mapping is synthetic (declared in the log header); the registry does not assign strands to course modules.</p>
${skillBlocks}

<h2>Learners</h2>
<div class="wrap"><table>
<thead><tr><th>Learner</th><th class="t">Courses</th><th>Stages</th><th>Completion</th><th>Gate passes</th><th>Gate pass rate</th><th>Minutes</th><th>Hints</th><th>Mean rung</th><th>Refusals</th></tr></thead>
<tbody>
${learnerRows}
</tbody></table></div>
</main>
<footer class="note">${BANNER}. Generated by cohort/build.mjs; reconciled against an independent recomputation by cohort/test.mjs.</footer>
</body>
</html>
`;
}

export function buildPage() {
  const log = parseLog(readFileSync(at('./fixtures/session_log.jsonl'), 'utf8'));
  const d = computeDashboard(log, { courses: readJson('../courses/registry/courses.json'),
    skills: readJson('../pack/registry/skills.json') });
  return { dashboard: d, html: renderPage(d, { packVersion: readJson('../pack/manifest.json').pack_version }) };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const { html, dashboard } = buildPage();
  if (process.argv.includes('--stdout')) process.stdout.write(html);
  else {
    writeFileSync(at('./dashboard.html'), html);
    console.log(`cohort: wrote cohort/dashboard.html (${dashboard.suppressed_cells}/${dashboard.total_cells} cells suppressed)`);
  }
}
