/**
 * Training-data registry verification.
 *
 * The claim this pack makes is narrow and structural: one episode
 * kind per interaction, each a fact this bundle already produces rather than something
 * invented for the recorder; device-local storage under its own key,
 * never the progress key; a rolling cap; a visible on/off toggle that
 * never touches episodes already kept; and - the property that actually
 * matters - the recorder is strictly downstream of a score already
 * final, never upstream of one. TRACE, the finer-grained add-on, gets
 * its own narrow claim held separately: off by default, its own toggle,
 * a real declared sample rate and cap the page actually enforces (not a
 * second, silently-drifted pair of numbers), and folded into the SAME
 * sim episode it belongs to rather than recorded as a fourth kind. The
 * suite holds the page to the same shape.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };

const reg = JSON.parse(readFileSync(new URL('./registry/training.json', import.meta.url)));
const page = readFileSync(new URL('../web/trade_craft_3d.html', import.meta.url), 'utf8');
const meta = JSON.parse(readFileSync(
  new URL('../meta/registry/metaverse.json', import.meta.url)));
const kinds = Object.entries(reg.episode_kinds);

/* ------------------------------------------------------------ the shape --- */
/* This used to read `kinds.length === 3`, which guarded against a kind
   growing in quietly but said nothing about WHICH kinds exist - so the
   day a fourth was added deliberately, the check could only be silenced
   by raising a number. Naming the roster is the stronger guard: a new
   kind still cannot arrive unannounced, and the test now says what the
   recorder records. */
ok('the episode kinds are the declared roster, each explaining itself and '
  + 'its fields',
  kinds.map(([k]) => k).sort().join(',') === 'advisor,crew,sim,walkaround'
  && kinds.every(([, k]) => k.what.length > 10 && k.fields.includes('t')
    && k.fields.includes('kind')));
ok('a crew episode keeps which ROLE answered, not just which crew - a '
  + 'signalperson\'s answer and a rigger\'s are different evidence',
  reg.episode_kinds.crew.fields.includes('crew')
  && reg.episode_kinds.crew.fields.includes('role'));
ok('every kind\'s fields are facts this bundle already produces, not new invented state',
  reg.episode_kinds.sim.fields.includes('outcome')
  && reg.episode_kinds.advisor.fields.includes('topic')
  && reg.episode_kinds.advisor.fields.includes('answer_kind')
  && reg.episode_kinds.walkaround.fields.includes('point'));
ok('the sim kind is honestly episode-level by default, and names TRACE rather than implying it',
  /episode-level by default/.test(reg.episode_kinds.sim.granularity)
  && /not a per-tick physics or\s+joint trajectory/.test(reg.episode_kinds.sim.granularity));
ok('the sim outcome shape declares trace as OPTIONAL, gated on TRACE being on',
  /OPTIONAL, present only\s+when TRACE is on/.test(reg.episode_kinds.sim.outcome_shape.trace));

/* ----------------------------------------------------------- storage --- */
ok('training data lives under its own key, never the progress key',
  reg.storage.key === 'tc-training' && reg.storage.key !== 'tc-progress'
  && reg.storage.toggle_key !== reg.storage.key);
ok('the cap is a real number and the policy is a rolling window, oldest first',
  reg.storage.cap > 0 && /oldest episode is dropped/.test(reg.storage.cap_policy)
  && /never the newest/.test(reg.storage.cap_policy));
ok('storage stays this browser only, exactly like the progress record',
  /this browser only/.test(reg.storage.scope)
  && /exactly like tc-progress/.test(reg.storage.scope));

/* ------------------------------------------------------------- export --- */
ok('the export envelope is declared, and named as JSON, not a native demo file',
  /"episodes": \[episode/.test(reg.export_format.shape)
  && /not a native Unity ML-Agents \.demo/.test(reg.export_format.not_a_demo_file));
ok('the ml-agents link is a link this bundle already records, not a new claim invented here',
  reg.export_format.consumer.includes('ml-agents')
  && meta.unity_bridge.repo.includes('ml-agents')
  && meta.unity_bridge.provenance.startsWith('RECORDED'));
ok('exporting the file is stated to train nothing by itself',
  /trains nothing by itself/.test(reg.export_format.no_agent_trained)
  && /no agent exists in this bundle/.test(reg.export_format.no_agent_trained));

/* ------------------------------------------------------------- honesty --- */
ok('every episode is stated to be schematic, not real robot or real machine data',
  /SCHEMATIC physics and\s+deterministic rubrics/.test(reg.honesty.schematic)
  && /not for training a\s+controller that will run on real equipment/
    .test(reg.honesty.schematic));
ok('the record is anonymous: no name, no email, no biometric or device id',
  /no name, no email, no biometric or device-identifying/.test(reg.honesty.anonymous));
ok('and it changes no score, the same guarantee this bundle keeps for advisors',
  /changes no score and is never\s+read by a grader/.test(reg.honesty.not_scored)
  && /the same guarantee this bundle\s+keeps for advisors/.test(reg.honesty.not_scored));
ok('consent is real: on by default, a visible toggle, and clearing is separate from opting out',
  /ships on, with a visible toggle/.test(reg.honesty.consent)
  && /without touching ones already kept/.test(reg.honesty.consent)
  && /clearing them is a separate, deliberate action/.test(reg.honesty.consent));
ok('the granularity note describes what TRACE actually is, not a bare promise of a future feature',
  /episode-level by default/.test(reg.honesty.granularity)
  && /not a\s+per-tick physics or joint trajectory/.test(reg.honesty.granularity)
  && /schematic single-machine simulators,\s+not articulated robots/.test(reg.honesty.granularity));

/* --------------------------------------------------------------- the page --- */
ok('the page builds the recorder, the toggle, the exporter and the clearer',
  ['function recordEpisode(', 'function trainingToggle(',
    'function exportTraining(', 'function clearTraining(', 'function traceToggle(']
    .every((f) => page.includes(f)));
ok('the page embeds the declared storage key and the declared cap',
  page.includes('"tc-training"') && page.includes(`"cap":${reg.storage.cap}`));
ok('every declared episode kind is actually recorded by the page, by name',
  kinds.every(([kk]) => page.includes(`kind: '${kk}'`)));
ok('recordEpisode is called from exactly the declared integration points, one per kind',
  (page.match(/recordEpisode\(\{/g) || []).length === kinds.length);

/* ------------------------------------------------------------------ TRACE --- */
ok('TRACE has its own toggle key, separate from the base recorder\'s, off by default',
  reg.trace.toggle_key !== reg.storage.toggle_key
  && /^off/.test(reg.trace.default));
ok('TRACE declares a real sample rate and a real cap',
  reg.trace.sample_hz > 0 && reg.trace.max_samples > 0);
ok('TRACE is sampled from the sim\'s own existing gauges() output, nothing computed anew',
  /sim's own gauges\(\)\s+function/.test(reg.trace.sampled_from)
  && /computed nowhere new/.test(reg.trace.sampled_from));
ok('the page embeds TRACE\'s own toggle key',
  page.includes(`"${reg.trace.toggle_key}"`));
ok('the page READS its TRACE sample interval and cap from the embedded registry - one declared pair, not a second hand-typed one',
  page.includes('TRACE_MS = Math.round(1000 / D.training.trace.sample_hz)')
  && page.includes('TRACE_MAX = D.training.trace.max_samples')
  && page.includes(`"sample_hz":${reg.trace.sample_hz}`)
  && page.includes(`"max_samples":${reg.trace.max_samples}`));
ok('the trace is folded into the sim episode\'s own outcome, never recorded as a separate episode',
  page.includes('trace: simTicks }')
  && (page.match(/recordEpisode\(\{/g) || []).length === kinds.length);
ok('the trace cap is enforced once, in traceStep - never re-capped at record time',
  !page.includes('simTicks.slice(')
  && /simTicks\.length >= TRACE_MAX\) return/.test(page));
ok('capturing a trace requires the sim to actually be running - gated on the same sim object the gauges come from',
  /function traceStep\(dt\) \{\s*if \(!traceOn \|\| !sim \|\| !sim\.gauges/.test(page));

/* ---------------------------------------------------------- orbis pairing --- */
// the records panel used to say nothing about orbis/ even though the two
// packs are declared as a pair; it now names the fact and links to it.
ok('the registry states the orbis pairing as a real fact, not a bare cross-reference',
  /this log only ever gets an episode once a learner\s+actually trains here/
    .test(reg.honesty.orbis_pairing)
  && /never a substitute for this\s+real one/.test(reg.honesty.orbis_pairing));
ok('the records panel actually renders that pairing fact and links to the Orbis panel',
  page.includes(reg.honesty.orbis_pairing)
  && /trOrbisBtn/.test(page) && /openOrbis/.test(page));

/* -------------------------------------------- downstream of a final score --- */
// every simResults(...) call's third argument - the pass/fail expression -
// read with balanced parentheses, so an inner call such as Math.abs(x) is
// captured whole rather than cut at its first ')'
const passExprs = (src) => {
  const out = [];
  for (let i = src.indexOf("simResults('"); i >= 0; i = src.indexOf("simResults('", i + 1)) {
    const j = src.indexOf('(', i);
    let depth = 0, k = j;
    for (;; k++) {
      if (src[k] === '(') depth++;
      else if (src[k] === ')' && --depth === 0) break;
    }
    out.push(src.slice(j + 1, k).split('rows,').slice(1).join('rows,').trim());
    i = k;
  }
  return out;
};
ok('the pass-expression reader captures a whole third argument, inner parentheses included',
  JSON.stringify(passExprs("simResults('x', rows, Math.abs(a) <= 1 && g(t) === 0);\n"
    + "  simResults('y', rows,\n    f(train) === 0);"))
  === JSON.stringify(['Math.abs(a) <= 1 && g(t) === 0', 'f(train) === 0']));
const exprs = passExprs(page);
ok('every sim\'s pass/fail expression is computed first, with no reference to training or operator state',
  exprs.length === 11 && exprs.every((e) => e && !/train|oprun/i.test(e)));
ok('the recorder in simResults receives passed as a parameter - it cannot compute its own outcome',
  /function simResults\(simId, rows, passed\)/.test(page)
  && page.split('function simResults(simId, rows, passed)')[1]
      ?.slice(0, 400).includes("recordEpisode({ kind: 'sim'"));

/* ------------------------------------------------ the scripted tier --- */
const sims = JSON.parse(readFileSync(
  new URL('../sims/registry/sims.json', import.meta.url)));
ok('two actors are declared - human, and the scripted reference operator - and a human episode is stated to be exactly as it was',
  Object.keys(reg.actors).length === 2 && 'human' in reg.actors
  && 'scripted-reference' in reg.actors
  && /exactly as before/.test(reg.actors.human)
  && /no model, no network/.test(reg.actors['scripted-reference']));
ok('the sim episode names its actor and, scripted only, its replay handle',
  reg.episode_kinds.sim.fields.includes('actor')
  && reg.episode_kinds.sim.fields.includes('operator')
  && /present ONLY when actor is\s+scripted-reference/.test(reg.episode_kinds.sim.operator)
  && /absent on a human episode/.test(reg.episode_kinds.sim.operator));
ok('the SCRIPTED word is stated honestly: a written policy on a schematic sim, not learned, not real equipment, not a physical robot, not AI-SYNTHESIZED',
  /^a SCRIPTED episode/.test(reg.honesty.scripted)
  && /Not a learned policy, not real\s+equipment, and not a claim about any physical robot/.test(reg.honesty.scripted)
  && /not\s+AI-SYNTHESIZED either/.test(reg.honesty.scripted)
  && /never credits the learner/.test(reg.honesty.scripted));
ok('the scripted tier is sims/\'s own declaration, cited here: every seat carries an operator at the one closed level set',
  Object.values(sims.sims).every((s) => s.operator
    && JSON.stringify(s.operator.levels) === JSON.stringify(Object.keys(sims.operator_levels)))
  && /^SCRIPTED/.test(sims.honesty.operator));
ok('the page records the actor from the live operator state, inside the ONE sim recordEpisode call, with the replay handle',
  page.includes("actor: opRun ? 'scripted-reference' : 'human'")
  && /operator: \{ level: opRun\.level, seed: opRun\.seed, scenario: opRun\.scenario,\s+steps: opRun\.step, dt: opRun\.fixedDt \}/.test(page)
  && (page.match(/recordEpisode\(\{/g) || []).length === kinds.length);
ok('a scripted run never writes the learner\'s progress record - the guard is by name, inside simResults',
  (() => {
    const body = page.split('function simResults(simId, rows, passed)')[1]?.slice(0, 1400) ?? '';
    return body.includes('if (!opRun) {') && body.includes('prog.sims[simId] = rec; saveProg()')
      && body.indexOf('if (!opRun) {') < body.indexOf('prog.sims[simId] = rec');
  })());
ok('the page builds one policy per seat, deterministic (no Math.random), each naming every step of its declared procedure',
  (() => {
    const ops = page.split('const OPERATORS = {')[1]?.split('function opAttach(')[0] ?? '';
    return ops.length > 1000 && !ops.includes('Math.random')
      && Object.entries(sims.sims).every(([id, s]) => ops.includes(`'${id}': {`)
        && s.operator.procedure.every((p) => ops.includes(`'${p.id}'`)));
  })());
ok('the driver surface and the headless sweep exist, and the sweep records through the same recorder under the same toggle',
  page.includes('window.__tc3dSim = {') && page.includes('function opRunHeadless(')
  && page.includes('async function opSweep(')
  && /return \{ recorded: trainingOn, rows \}/.test(page)
  && !/opSweep[\s\S]{0,3000}recordEpisode\(/.test(page.split('async function opSweep(')[1]?.slice(0, 3000) ?? ''));
ok('the records panel offers the sweep, off until clicked, and says when the recorder is off',
  page.includes('id="trSweepBtn"') && page.includes('id="trSweepLvl"')
  && /recorder is off/.test(page));

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`training/test: ${n} checks passed — ${kinds.length} episode kinds, `
  + `cap ${reg.storage.cap}`);
