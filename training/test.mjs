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
  kinds.map(([k]) => k).sort().join(',') === 'advisor,crew,placard,sim,walk,walkaround'
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

/* wave 20: the fields a kind DECLARES are the fields the page WRITES. The call literal of the three
   flat kinds is read out of the page and its keys must equal the declared fields (minus the stamp `t`
   recordEpisode adds itself); a declared field the page never writes, or a field written and never
   declared, fails by the kind's name. The sim literal nests objects and a spread, so it is held by the
   outcome/actor checks below instead. */
const callKeys = (kk) => {
  const at0 = page.indexOf(`recordEpisode({ kind: '${kk}'`);
  if (at0 < 0) return null;
  const body = page.slice(at0, page.indexOf('});', at0)).replace(/^recordEpisode\(\{/, '');
  return [...body.matchAll(/(?:^|[\s,{])([a-z_]+):\s/g)].map((m) => m[1]).sort();
};
for (const kk of ['advisor', 'crew', 'walkaround', 'walk', 'placard']) {
  ok(`the page writes exactly the declared fields of a ${kk} episode (the stamp t is added by recordEpisode)`,
    JSON.stringify(callKeys(kk)) === JSON.stringify(reg.episode_kinds[kk].fields.filter((f) => f !== 't').sort()),
    [JSON.stringify(callKeys(kk)), JSON.stringify(reg.episode_kinds[kk].fields)]);
}
ok('a crew episode records the crew\'s own seat and muster, copied from the crews registry entry the page already holds',
  reg.episode_kinds.crew.fields.includes('seat') && reg.episode_kinds.crew.fields.includes('muster')
  && /CREW-EPISODE BEGIN[\s\S]*?seat: crew\.seat, muster: crew\.muster[\s\S]*?CREW-EPISODE END/.test(page)
  && /const crew = a\.inCrew \? CREW_TABLE\[a\.inCrew\] : null;/.test(page));

/* wave 20: walk and placard. Each is declared with the fields the page writes, recorded inside balanced anchored
   STEP-EPISODE blocks, the dwell is read from the embedded registry, and a probe-driven walker records nothing. */
ok('walk and placard episodes declare where (the strand id a lesson step carries) and room, and a placard also its measured dwell_ms',
  ['walk', 'placard'].every((k) => reg.episode_kinds[k].fields.includes('where') && reg.episode_kinds[k].fields.includes('room')
    && reg.episode_kinds[k].fields.includes('hall') && reg.episode_kinds[k].outcome_shape === null)
  && reg.episode_kinds.placard.fields.includes('dwell_ms') && !reg.episode_kinds.walk.fields.includes('dwell_ms'));
ok('the declared dwell is a real number, with its reason, and the honesty says what a walk or placard episode does not prove',
  Number.isInteger(reg.step_episodes.placard.dwell_ms) && reg.step_episodes.placard.dwell_ms >= 1000
  && reg.step_episodes.placard.dwell_ms === reg.episode_kinds.placard.at_least.dwell_ms && reg.episode_kinds.walk.at_least === undefined
  && /floor on\s+open time, not a measure of reading/.test(reg.step_episodes.placard.dwell_why)
  && /competence, attention, comprehension/.test(reg.step_episodes.does_not_prove) && /certifies nobody/.test(reg.step_episodes.does_not_prove)
  && /never for\s+every room/.test(reg.step_episodes.walk.recorded_for) && /one episode per \(kind, hall, where\)/.test(reg.step_episodes.dedupe));
ok('the page records both inside balanced STEP-EPISODE blocks and reads the dwell from the embedded registry, never retyped',
  (page.match(/\/\* STEP-EPISODE BEGIN/g) || []).length >= 4
  && (page.match(/\/\* STEP-EPISODE BEGIN/g) || []).length === (page.match(/\/\* STEP-EPISODE END/g) || []).length
  && page.includes('D.training.step_episodes.placard.dwell_ms') && page.includes(`"dwell_ms":${reg.step_episodes.placard.dwell_ms}`)
  && !/PLACARD_DWELL_MS\s*=\s*\d/.test(page));
ok('a probe-driven walker (wkSilent) records no walk episode, and only a lesson-target room is recorded, never twice',
  /function stepWalkEntered\(room\) \{\s*if \(wkSilent\) return;[\s\S]*?stepTargetStrands\('walk'\)\.has\(room\.strand\)[\s\S]*?stepLogged\('walk', room\.strand\)/.test(page));

/* wave 20: BEHAVIOUR of the page's STEP-EPISODE recorder, not just its text. The block is cut out of the built page and run
   in a vm with stub scene state, over the real lessons registry, and driven the way the page drives it. */
{
  const lessonsReg = JSON.parse(readFileSync(new URL('../lessons/registry/lessons.json', import.meta.url)));
  const i0 = page.indexOf('/* STEP-EPISODE BEGIN (wave 20)');
  const blockSrc = page.slice(i0, page.indexOf('/* STEP-EPISODE END */', i0));
  const L0 = Object.values(lessonsReg.lessons).find((l) => l.steps.some((st) => st.kind === 'walk') && l.steps.some((st) => st.kind === 'placard'));
  const HALL = L0.hall;
  const walkS = new Set(), placS = new Set();
  for (const l of Object.values(lessonsReg.lessons)) if (l.hall === HALL) for (const st of l.steps) {
    if (st.kind === 'walk') walkS.add(st.where); if (st.kind === 'placard') placS.add(st.where);
  }
  const TARGET = [...placS].find((x) => walkS.has(x));
  const OTHER = ['safety', 'procedure', 'machines', 'tools', 'layout', 'inspection', 'materials', 'documentation', 'coordination', 'troubleshooting', 'leadership']
    .find((x) => !walkS.has(x) && !placS.has(x));
  const DWELL = reg.step_episodes.placard.dwell_ms, RANGE = 20;
  const mk = () => {
    const src = `
      let wkSilent = false, view = 'hall', curRoom = null, placardBoards = [], placardOpen = null, walkActive = false, sim = null;
      const slug = ${JSON.stringify(HALL)}, campusKey = 'c', loc = 'en';
      const trainingLog = [];
      const D = { lessons: { lessons: LESSONS }, training: { step_episodes: { placard: { dwell_ms: ${DWELL} }, proves: 'P.', does_not_prove: 'N.' } },
        i18n: { en: { strands: new Proxy({}, { get: (t, k) => String(k) }) } } };
      const LKIND = { placard: { hide_beyond_m: ${RANGE} } };
      const xrRig = { position: { x: 0, z: 0 } }, _wp = { x: 0, z: 0 };
      const plc = { isLocked: false, unlock() {} };
      const window = {}; let roomRects = []; function walkStep() {}   // the harness hook at the end of the block needs these names
      const condOf = () => ({ ppe: ['hi-vis', 'boots'] }), condLine = () => 'cond';
      function recordEpisode(ep) { trainingLog.push({ t: 'T', ...ep }); }
      ${blockSrc}
      return { log: trainingLog, listeners, setRoom: (r) => { curRoom = r; }, setSilent: (v) => { wkSilent = v; }, setView: (v) => { view = v; },
        addBoard: (b) => placardBoards.push(b), clearBoards: () => { placardBoards = []; }, setWalk: (v) => { walkActive = v; },
        entered: stepWalkEntered, open: openPlacard, tick: stepEpisodeTick, hint: stepPlacardHint, state: () => placardOpen, rig: xrRig };`;
    const pb = { innerHTML: '' }, cls = new Set(), listeners = [];
    const document = {
      getElementById: () => pb,
      querySelector: (q) => { const m = q.match(/data-placard="([^"]+)"/); return m && pb.innerHTML.includes('data-placard="' + m[1] + '"') ? {} : null; },
      body: { classList: { contains: (x) => cls.has(x), add: (x) => cls.add(x), remove: (x) => cls.delete(x) } },
      addEventListener: (t, f) => listeners.push([t, f]),
    };
    const h = new Function('LESSONS', 'document', 'listeners', src)(lessonsReg.lessons, document, listeners);
    return { ...h, pb, cls, document };
  };
  const room = (strand) => ({ strand, label: 'Room ' + strand });
  const board = (strand, x) => ({ userData: { placardStrand: strand }, getWorldPosition: (v) => { v.x = x; v.z = 0; } });
  const run = (h, secs, dt = 0.1) => { for (let i = 0; i < Math.round(secs / dt); i++) h.tick(dt); };

  let h = mk();
  h.entered(room(TARGET));
  ok('a walk episode is recorded when the walker enters a room a lesson names as a walk target: kind, campus, hall, where (the strand) and the room label, nothing else',
    h.log.length === 1 && JSON.stringify(Object.keys(h.log[0]).sort()) === JSON.stringify(['campus', 'hall', 'kind', 'room', 't', 'where'])
    && h.log[0].kind === 'walk' && h.log[0].hall === HALL && h.log[0].where === TARGET && h.log[0].room === 'Room ' + TARGET);
  h.entered(room(TARGET));
  ok('entering the same room again adds nothing while the first is in the log', h.log.length === 1);
  h.entered(room(OTHER));
  ok('a room no lesson names as a walk target records nothing', h.log.length === 1 && OTHER !== undefined);
  h = mk(); h.setSilent(true); h.entered(room(TARGET));
  ok('a probe-driven walker (wkSilent) records no walk episode', h.log.length === 0);

  // placard
  h = mk(); h.addBoard(board(TARGET, 5)); h.setRoom(room(OTHER));
  ok('a placard cannot be opened from outside its room', h.open(TARGET) === false && h.state() === null && !h.cls.has('open'));
  h.setRoom(room(TARGET)); h.rig.position.x = 5 + RANGE + 1;
  ok('a placard cannot be opened from beyond the label registry\'s read distance, read from the registry', h.open(TARGET) === false);
  h.rig.position.x = 3;
  ok('opened from inside its room and in range, the panel shows the room\'s own placard and opens the panel', h.open(TARGET) === true && h.cls.has('open') && /data-placard/.test(h.pb.innerHTML) && h.state().strand === TARGET);
  run(h, DWELL / 1000 - 0.3);
  ok('nothing is recorded before the declared dwell has passed', h.log.length === 0 && h.state() !== null);
  run(h, 0.6);
  const pe = h.log[0];
  ok('after the dwell a placard episode is recorded: kind, campus, hall, where, room and the measured dwell_ms, at or above the declared floor',
    h.log.length === 1 && pe.kind === 'placard' && pe.hall === HALL && pe.where === TARGET && pe.room === 'Room ' + TARGET && pe.dwell_ms >= DWELL
    && JSON.stringify(Object.keys(pe).sort()) === JSON.stringify(['campus', 'dwell_ms', 'hall', 'kind', 'room', 't', 'where']));
  run(h, 5);
  ok('one panel, one episode: staying longer adds nothing, and re-opening while it is in the log adds nothing', h.log.length === 1 && (h.open(TARGET), run(h, DWELL / 1000 + 1), h.log.length === 1));

  h = mk(); h.addBoard(board(TARGET, 5)); h.setRoom(room(TARGET)); h.open(TARGET); run(h, 3);
  h.setRoom(room(OTHER)); run(h, 0.1);
  ok('walking out of the room resets the dwell: the panel is no longer a placard being read', h.state() === null);
  h.setRoom(room(TARGET)); run(h, DWELL / 1000 - 0.5);
  ok('and nothing carries over: the time before leaving does not count towards a later open', h.log.length === 0);

  h = mk(); h.addBoard(board(TARGET, 5)); h.setRoom(room(TARGET)); h.open(TARGET); run(h, 2);
  h.pb.innerHTML = '<h2>another panel</h2>'; run(h, 0.1);
  ok('another panel replacing the placard resets the dwell', h.state() === null);
  h = mk(); h.addBoard(board(TARGET, 5)); h.setRoom(room(TARGET)); h.open(TARGET); run(h, 2);
  h.cls.delete('open'); run(h, 0.1);
  ok('closing the panel resets the dwell', h.state() === null);
  h = mk(); h.addBoard(board(TARGET, 5)); h.setRoom(room(TARGET)); h.open(TARGET); for (let i = 0; i < 40; i++) h.tick(30);
  ok('a stalled frame or hidden tab is not reading time: a 30 s frame counts one second at most, so a few of them never reach the dwell and the recorded dwell never exceeds one second per frame',
    h.log.length === 0 || h.log[0].dwell_ms <= 40 * 1000 + 1);
  h = mk(); h.addBoard(board(TARGET, 5)); h.setRoom(room(TARGET)); h.open(TARGET); for (let i = 0; i < Math.floor(DWELL / 1000) - 1; i++) h.tick(30);
  ok('three 30 s frames (under the dwell once clamped) record nothing: stalls are not reading time', h.log.length === 0);
  h = mk(); h.addBoard(board(TARGET, 5)); h.setRoom(room(TARGET)); h.open(TARGET); for (let i = 0; i < Math.ceil(DWELL / 1000) + 1; i++) h.tick(1);
  ok('a device rendering one frame a second still accrues the dwell: every frame it does render counts in full', h.log.length === 1 && h.log[0].dwell_ms >= DWELL);
  h = mk(); h.addBoard(board(TARGET, 5)); h.setRoom(room(TARGET)); h.open(TARGET); h.tick(100);
  ok('a single 100 s frame advances the dwell by one second only', Math.abs(h.state().ms - 1000) < 1e-6);
  h = mk(); h.addBoard(board(OTHER, 5)); h.setRoom(room(OTHER)); h.open(OTHER); run(h, DWELL / 1000 + 1);
  ok('a placard of a room no lesson names records nothing, however long it is open', h.log.length === 0);
  h = mk(); h.addBoard(board(TARGET, 5)); h.setRoom(room(TARGET)); h.setView('campus');
  ok('a placard cannot be opened outside the hall view', h.open(TARGET) === false);
  ok('the board hint is shown only for a room that has a board', mk().hint(TARGET) === '' && (() => { const g = mk(); g.addBoard(board(TARGET, 1)); return g.hint(TARGET) !== '' && g.hint(OTHER) === ''; })());
  h = mk(); h.addBoard(board(TARGET, 5)); h.setRoom(room(TARGET)); h.setWalk(true);
  const kd = h.listeners.find(([t]) => t === 'keydown')[1];
  kd({ code: 'KeyQ' }); const q = h.state();
  kd({ code: 'KeyE' });
  ok('E in a room with a board opens it (walking, hall view, no panel open); other keys do not', q === null && h.state() !== null && h.state().strand === TARGET);
}

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

/* ---------------------------------------- ROBOLAB (wave 11): world kinds --- */
/* The world teleop kind extends this recorder (same key, toggle, cap, export) and
   is a roster of its own: the 3D page's four kinds above are untouched. */
const wk = reg.world_episode_kinds, wt = reg.world_teleop;
ok('the world episode kinds are the declared roster (world-teleop) and never reuse a 3D-page kind id',
  Object.keys(wk).join(',') === 'world-teleop'
  && Object.keys(wk).every((k) => !(k in reg.episode_kinds)));
ok('world-teleop carries exactly the contract v1 field list, with its own kind version',
  wk['world-teleop'].fields.join(',') === 't,kind,v,env,embodiment,world,actor,seed,hz,dt_s,steps,samples,outcome'
  && wk['world-teleop'].v === 1);
ok('a world sample is pose, velocity, nearby AUTHORED ids and the control inputs - env-local, never lat/lon',
  Object.keys(wk['world-teleop'].sample_shape).join(',') === 'i,pose,vel,near,a'
  && /never lat\/lon/.test(wk['world-teleop'].sample_shape.pose));
ok('no world-teleop field names personal data (name, email, text, audio, camera, lat/lon, device)',
  wk['world-teleop'].fields.every((f) => !/name|email|text|audio|camera|lat|lon|device/.test(f)));
ok('world teleop samples at a fixed low rate with a hard cap of 60 s of samples',
  wt.sample_hz === 5 && wt.dt_s === 0.1 && wt.max_samples === 300 && /hard cap/.test(wt.max_samples_policy));
ok('world teleop is opt-in per episode, honours the base toggle, and is not offered in classroom mode',
  /pressed Record/.test(wt.opt_in) && /base recorder toggle/.test(wt.opt_in) && /not offered/.test(wt.classroom));
const robo = readFileSync(new URL('../web/robokit.py', import.meta.url), 'utf8');
ok('robokit records world-teleop into the SAME storage key, toggle and rolling cap this registry declares',
  robo.includes('TR_KEY_W = D_TRAIN.storage.key') && robo.includes('D_TRAIN.storage.toggle_key')
  && robo.includes('D_TRAIN.storage.cap') && robo.includes("kind: 'world-teleop'")
  && robo.includes("localStorage.getItem(TR_ON) !== '0'"));
ok('robokit reads the sample rate and cap from this registry (one truth) and is deterministic',
  robo.includes('D_TRAIN.world_teleop.sample_hz') && robo.includes('D_TRAIN.world_teleop.max_samples')
  && !robo.includes('Math.random'));
ok('robokit keeps nothing in classroom mode and nothing unless Record was pressed',
  /if \(classroom \|\| !baseOn\(\)\) return false;/.test(robo)
  && (robo.match(/if \(rec\) \{ const ok = keep\(ep\)/g) || []).length === 2 && (robo.match(/const ok = keep\(ep\)/g) || []).length === 2);

const src = readFileSync(new URL('./build.py', import.meta.url));
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(src).digest('hex').slice(0, 16));

console.log(`training/test: ${n} checks passed — ${kinds.length} episode kinds, `
  + `cap ${reg.storage.cap}`);
