/**
 * World training modules - registry verification (wave 19).
 *
 * Every module is re-read here against the registries that own its parts: each step is one of the EXISTING step kinds
 * (lessons.json step_kinds plus training.json world_episode_kinds), each id resolves where it lives, every brief quote
 * is found verbatim at the path it cites, every greeter is an Omega Hive agent speaking one of its own lines, and
 * nothing the pack authors claims a certificate or a duration. Prints `  ok <name>` per check and `FAIL` at column 0.
 */
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const J = (p) => JSON.parse(readFileSync(path.join(ROOT, p), 'utf8'));
let fails = 0, oks = 0;
const check = (name, cond, why = '') => {
  if (cond) { oks++; console.log(`  ok ${name}`); } else { fails++; console.log(`FAIL ${name}${why ? ' - ' + why : ''}`); }
};

const REG = J('modules/registry/modules.json');
const M = REG.modules;
const LJ = J('lessons/registry/lessons.json');
const LESSONS = LJ.lessons;
const TRAINING = J('training/registry/training.json');
const CREWS = J('agents/registry/crews.json').crews;
const SIMS = J('sims/registry/sims.json').sims;
const STATIONS = Object.fromEntries(J('stations/registry/stations.json').stations.map((s) => [s.station_id, s]));
const HIVE = Object.fromEntries(J('hive/registry/hive.json').agents.map((a) => [a.id, a]));
const ROBO = J('robotics/registry/robotics.json');
const RESTO = J('restoration/registry/restoration.json').sites;
const WILDS = J('wilds/registry/wilds.json').worlds;
const DISTRICTS = J('unions/registry/districts.json').districts;
const SUPS = J('courses/registry/courses.json').supplements;

// [stamp] the source stamp covers the builder and every source registry, byte for byte
{
  const h = createHash('sha256');
  h.update(readFileSync(path.join(ROOT, 'modules/build.py')));
  for (const p of REG.sources) h.update(readFileSync(path.join(ROOT, p)));
  check('[stamp] source_stamp is sha256 of modules/build.py and its sources', h.digest('hex') === REG.source_stamp);
}
let fresh = true;
try { execFileSync('python3', [path.join(ROOT, 'modules/build.py'), '--check'], { stdio: 'pipe' }); } catch { fresh = false; }
check('[stamp] python3 modules/build.py --check passes (registry is current)', fresh);

// [kinds] the closed set is the existing one, nothing added
const LK = Object.keys(LJ.step_kinds).sort(), WK = Object.keys(TRAINING.world_episode_kinds).sort();
check('[kinds] step_kinds = lessons step_kinds + training world_episode_kinds', JSON.stringify(REG.step_kinds) === JSON.stringify([...LK, ...WK]));
const allSteps = M.flatMap((m) => m.steps.map((s) => [m, s]));
check('[kinds] every step is one of the existing kinds', allSteps.every(([, s]) => REG.step_kinds.includes(s.kind)),
  allSteps.filter(([, s]) => !REG.step_kinds.includes(s.kind)).map(([m, s]) => `${m.id}:${s.kind}`).join(' '));
check('[kinds] steps are numbered 1..n in order', M.every((m) => m.steps.every((s, i) => s.n === i + 1)));
check('[kinds] a lesson-kind step records exactly what its kind records',
  allSteps.every(([, s]) => !(s.kind in LJ.step_kinds) || s.records === LJ.step_kinds[s.kind].records));
check('[kinds] world-teleop: the human drive records world-teleop, the watched reference records nothing',
  allSteps.filter(([, s]) => s.kind === 'world-teleop').every(([, s]) => (s.actor === 'human' ? s.records === 'world-teleop' : s.records === null)));
const ACT = JSON.stringify(TRAINING.actors);
check('[kinds] every world-teleop actor is a training actor', allSteps.filter(([, s]) => s.kind === 'world-teleop').every(([, s]) => ACT.includes(s.actor)));

// [resolve] every id resolves in the registry that owns it
const bad = [];
for (const [m, s] of allSteps) {
  const tag = `${m.id}#${s.n}`;
  if (s.lesson) {
    const L = LESSONS[s.lesson];
    const src = L && L.steps[s.lesson_step - 1];
    if (!src) { bad.push(`${tag} lesson`); continue; }
    for (const k of Object.keys(src)) if (k !== 'n' && JSON.stringify(src[k]) !== JSON.stringify(s[k])) bad.push(`${tag} ${k} not verbatim`);
    if (s.hall !== L.hall) bad.push(`${tag} hall`);
    continue;
  }
  if (s.kind === 'crew') {
    const t = CREWS[s.crew]?.roles?.[s.role]?.topics?.find((x) => x.id === s.topic);
    if (!t || t.ask !== s.ask) bad.push(`${tag} crew topic`);
  } else if (s.kind === 'walkaround') {
    const p = SIMS[s.sim]?.walkaround?.find((x) => x.id === s.point);
    if (!p || p.check !== s.check || p.point !== s.label) bad.push(`${tag} walkaround`);
  } else if (s.kind === 'sim') {
    const sc = SIMS[s.sim]?.scenarios?.find((x) => x.id === s.scenario);
    if (!sc || sc.name !== s.scenario_name || SIMS[s.sim].name !== s.seat_name) bad.push(`${tag} sim`);
  } else if (s.kind === 'station') {
    if (STATIONS[s.station]?.name !== s.station_name) bad.push(`${tag} station`);
  } else if (s.kind === 'world-teleop') {
    const env = ROBO.envs[s.env];
    if (!env || !env.embodiments.includes(s.embodiment) || !env.world.pages.includes(s.page) || !existsSync(path.join(ROOT, s.page))) bad.push(`${tag} env`);
    if (s.policy && env?.reference_policy?.id !== s.policy) bad.push(`${tag} policy`);
  } else bad.push(`${tag} unresolvable ${s.kind}`);
}
check('[resolve] every step id resolves; lesson steps are copied verbatim', bad.length === 0, bad.slice(0, 6).join('; '));
check('[resolve] worksite steps cite a real hand-off evidence path', allSteps.filter(([, s]) => s.worksite).every(([, s]) => {
  const mm = /^worksites\/registry\/worksites\.json#sites\[(\d+)\]\.handoffs\[(\d+)\]\.(from|to)_evidence$/.exec(s.from);
  if (!mm) return false;
  const ws = J('worksites/registry/worksites.json').sites[+mm[1]];
  const ev = ws?.handoffs[+mm[2]]?.[`${mm[3]}_evidence`];
  return ws.id === s.worksite && ev && ev.kind === s.kind;
}));

// [brief] every quote is found verbatim at the path it cites
const getPath = (src) => {
  const [file, ptr] = src.split('#');
  let o = J(file);
  for (const tok of ptr.match(/[A-Za-z_][\w-]*|\[\d+\]|\["[^"]+"\]/g)) {
    if (tok.startsWith('["')) o = o?.[tok.slice(2, -2)];
    else if (tok.startsWith('[')) o = o?.[+tok.slice(1, -1)];
    else o = o?.[tok];
  }
  return o;
};
const briefs = M.flatMap((m) => m.brief.map((b) => [m, b]));
const badB = briefs.filter(([, b]) => getPath(b.source) !== b.text);
check('[brief] every brief line is verbatim at its cited source', badB.length === 0, badB.slice(0, 3).map(([m, b]) => `${m.id}:${b.source}`).join(' '));
check('[brief] restoration briefs quote only scenarios.json', M.filter((m) => m.family === 'restoration-site').every((m) => m.brief.every((b) => b.source.startsWith('restoration/registry/scenarios.json#'))));
check('[brief] restoration runner links are the staged tasks\' own launch hrefs', M.filter((m) => m.family === 'restoration-site').every((m) =>
  m.runners.length > 0 && m.runners.every((r) => J('restoration/registry/scenarios.json').staged_tasks.find((t) => t.id === r.task)?.launch.href === r.href)));

// [cover] one module per source the rule can compose, a printed reason otherwise
const fam = (f) => M.filter((m) => m.family === f);
const walkable = RESTO.filter((s) => s.walkable).map((s) => s.id);
check('[cover] one restoration module per walkable site', JSON.stringify(fam('restoration-site').map((m) => m.site)) === JSON.stringify(walkable));
check('[cover] each non-walkable site is refused with its walkable_reason verbatim',
  RESTO.filter((s) => !s.walkable).every((s) => REG.refused[`restoration:${s.id}`] === s.walkable_reason));
const withWalks = WILDS.filter((w) => w.sites.some((s) => Object.values(LESSONS).some((L) => L.arc === 'site' && L.site.id === s.id))).map((w) => `wilds:${w.id}`);
check('[cover] one wilds module per world with site walks', JSON.stringify(fam('wilds-world').map((m) => m.world)) === JSON.stringify(withWalks) && withWalks.length === WILDS.length);
check('[cover] every site walk lesson is inside its world module', Object.values(LESSONS).filter((L) => L.arc === 'site').every((L) =>
  fam('wilds-world').find((m) => m.world === `wilds:${L.site.world}`)?.lessons.includes(L.id)));
check('[cover] every union district has a worksite module or a printed refusal',
  Object.keys(DISTRICTS).every((d) => fam('worksite-district').some((m) => m.district === d) !== (`worksite-district:${d}` in REG.refused)));
check('[cover] every worksite stands in exactly one district module', (() => {
  const ids = fam('worksite-district').flatMap((m) => m.places.map((p) => p.worksite));
  return ids.length === J('worksites/registry/worksites.json').sites.length && new Set(ids).size === ids.length;
})());
check('[cover] exactly one robot-yard module: watch the SCRIPTED reference, then drive in the Robotics lab', (() => {
  const r = fam('robot-yard');
  if (r.length !== 1) return false;
  const [a, b] = r[0].steps;
  return r[0].steps.length === 2 && a.actor === 'scripted-reference' && b.actor === 'human' && a.env === b.env &&
    ROBO.envs[a.env].reference_policy.provenance === 'SCRIPTED' && b.page === 'web/trade_craft_robotics.html';
})());
check('[cover] module ids are unique', new Set(M.map((m) => m.id)).size === M.length);

// [greeter] an Omega Hive agent speaking one of its own lines
check('[greeter] every greeter is a Hive agent', M.every((m) => HIVE[m.greeter.agent]));
check('[greeter] every greeter line is that agent\'s own line, with its source', M.every((m) => HIVE[m.greeter.agent]?.lines.some((l) => l.text === m.greeter.line && l.source === m.greeter.line_source)));
check('[greeter] greeters are SCRIPTED with no AI model; voice on a click', M.every((m) => m.greeter.provenance === 'SCRIPTED' && /no AI model/.test(m.greeter.voice) && /on a click/.test(m.greeter.voice)));
check('[greeter] the restoration greeter is the union-path advisor of the first needed trade', fam('restoration-site').every((m) => {
  const site = RESTO.find((s) => s.id === m.site);
  return J('unionpaths/registry/union_paths.json').halls.find((h) => h.hall === site.trade_needs[0]).advisor.id === m.greeter.agent;
}));

// [supp] supplements resolve in courses.json
check('[supp] every supplement is a courses.json supplement', M.every((m) => m.supplements.every((l) => SUPS[l])));
check('[supp] a module\'s own lessons lead its supplements', M.every((m) => JSON.stringify(m.supplements.slice(0, m.lessons.length)) === JSON.stringify(m.lessons)));

// [honest] limits: unverified, certifies nobody, no durations, no credentials
const CERT = /\b(certif(?:y|ies|ied|ying|icate|icates|ication|ications)|qualif(?:y|ies|ied|ication|ications)|licen[cs](?:e|es|ed|ing)|accredit\w*|diploma\w*|credential\w*)\b/i;
const DUR = /\b\d+\s*(?:min|mins|minutes?|hours?|hrs?|days?|weeks?)\b|\bseat[- ]time\b/i;
const authored = M.map((m) => [m.title, m.greeter.rule, ...m.steps.filter((s) => !s.lesson && !s.worksite).map((s) => s.note || '')].join(' ')).join(' ');
check('[honest] authored words claim no certificate, qualification or licence', !CERT.test(authored));
check('[honest] authored words state no duration', !DUR.test(authored));
check('[honest] honesty says unverified general practice and certifies nobody', /unverified general practice/.test(REG.honesty.standing) && /certifies, qualifies or licenses anybody/.test(REG.honesty.standing));
check('[honest] every module carries its standing and AUTHORED-by-rule provenance', M.every((m) => m.standing === 'unverified general practice; certifies nobody' && m.provenance === 'AUTHORED by rule'));
check('[honest] counts declare certifies 0, durations 0, trained_models 0', REG.counts.certifies === 0 && REG.counts.durations === 0 && REG.counts.trained_models === 0);
check('[honest] no module carries a duration or credential field', !/"(duration|hours|minutes|credential|certificate)"\s*:/.test(JSON.stringify(M)));
const raw = readFileSync(path.join(ROOT, 'modules/registry/modules.json'), 'utf8');
check('[honest] no internal path or model identifier in the registry', !/\/tmp\/|scratchpad|memory\/|claude-|gpt-/i.test(raw));

// [counts] recounted
const byK = {}; for (const [, s] of allSteps) byK[s.kind] = (byK[s.kind] || 0) + 1;
const byF = {}; for (const m of M) byF[m.family] = (byF[m.family] || 0) + 1;
check('[counts] modules, steps and brief quotes recount', REG.counts.modules === M.length && REG.counts.steps === allSteps.length && REG.counts.brief_quotes === briefs.length);
check('[counts] steps_by_kind and by_family recount', JSON.stringify(REG.counts.steps_by_kind) === JSON.stringify(Object.fromEntries(Object.entries(byK).sort())) &&
  JSON.stringify(REG.counts.by_family) === JSON.stringify(byF));
check('[counts] refused count recounts', REG.counts.refused === Object.keys(REG.refused).length);

console.log(`modules: ${oks} ok, ${fails} failing; ${M.length} modules, ${allSteps.length} steps`);
process.exit(fails ? 1 : 0);
