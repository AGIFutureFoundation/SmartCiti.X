/**
 * Training-data registry verification.
 *
 * The claim this pack makes is narrow and structural: three episode
 * kinds, each a fact this bundle already produces rather than something
 * invented for the recorder; device-local storage under its own key,
 * never the progress key; a rolling cap; a visible on/off toggle that
 * never touches episodes already kept; and - the property that actually
 * matters - the recorder is strictly downstream of a score already
 * final, never upstream of one. The suite holds the page to the same
 * shape.
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
ok('there are exactly three episode kinds, each explaining itself and its fields',
  kinds.length === 3
  && kinds.every(([, k]) => k.what.length > 10 && k.fields.includes('t')
    && k.fields.includes('kind')));
ok('every kind\'s fields are facts this bundle already produces, not new invented state',
  reg.episode_kinds.sim.fields.includes('outcome')
  && reg.episode_kinds.advisor.fields.includes('topic')
  && reg.episode_kinds.advisor.fields.includes('answer_kind')
  && reg.episode_kinds.walkaround.fields.includes('point'));
ok('the sim kind is honestly episode-level, not a claim of a frame-by-frame trajectory',
  /episode-level/.test(reg.episode_kinds.sim.granularity)
  && /not a\s+per-tick trajectory/.test(reg.episode_kinds.sim.granularity));

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
ok('the granularity gap is stated plainly rather than implied away',
  /not built yet/.test(reg.honesty.granularity));

/* --------------------------------------------------------------- the page --- */
ok('the page builds the recorder, the toggle, the exporter and the clearer',
  ['function recordEpisode(', 'function trainingToggle(',
    'function exportTraining(', 'function clearTraining(']
    .every((f) => page.includes(f)));
ok('the page embeds the declared storage key and the declared cap',
  page.includes('"tc-training"') && page.includes(`"cap":${reg.storage.cap}`));
ok('every declared episode kind is actually recorded by the page, by name',
  kinds.every(([kk]) => page.includes(`kind: '${kk}'`)));
ok('recordEpisode is called from exactly the three declared integration points',
  (page.match(/recordEpisode\(\{/g) || []).length === kinds.length);

/* -------------------------------------------- downstream of a final score --- */
ok('every sim\'s pass/fail expression is computed first, with no reference to training state',
  [...page.matchAll(/simResults\('[a-z-]+', rows,\s*([^)]*)\)/g)]
    .length === 7
  && [...page.matchAll(/simResults\('[a-z-]+', rows,\s*([^)]*)\)/g)]
    .every((m) => !/train/i.test(m[1])));
ok('the recorder in simResults receives passed as a parameter - it cannot compute its own outcome',
  /function simResults\(simId, rows, passed\)/.test(page)
  && page.split('function simResults(simId, rows, passed)')[1]
      ?.slice(0, 400).includes("recordEpisode({ kind: 'sim'"));

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`training/test: ${n} checks passed — ${kinds.length} episode kinds, `
  + `cap ${reg.storage.cap}`);
