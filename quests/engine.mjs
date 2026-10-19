/* quests/engine.mjs - the quest engine's pure core, as a node module.

   web/questkit.py lifts the block between the QUEST_CORE markers out of this
   file and carries it byte-for-byte into every page that carries quests;
   the page glue (web/questkit.py GLUE_JS) supplies storage, DOM and toasts.
   quests/test.mjs imports this module and runs the core over synthetic
   progress records. */
/* QUEST_CORE:BEGIN - the pure quest core. No DOM, no storage, no clock: the
   page glue hands it what it read and what time it is. Carried byte-for-byte
   into every page that carries quests; quests/test.mjs holds it identical.
   The evidence functions below are a verbatim copy of the ones in
   web/build_progress.py's COMPLETION_JS, so a lesson counts here from exactly
   the evidence the progress page counts; quests/test.mjs holds the copy. */
const QUEST_STORE = 'tc-quests';
const QUEST_KINDS_FINDABLE = ['treasure', 'egg'];
const QUEST_KONAMI = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'];
const EVIDENCED_KINDS = ['sim', 'station', 'crib'];
/* the reference a step of an episode kind carries, as lessons.json spells it;
   a training episode must equal every one of these AND the lesson's hall */
const REF_FIELDS = { walkaround: ['sim', 'point'], advisor: ['advisor', 'topic', 'answer_kind'],
  crew: ['crew', 'role', 'topic', 'answer_kind', 'seat', 'muster'] };
/* an episode kind whose recorded fields do not cover the step's reference can
   never mark a step done; the missing fields are named, not skipped */
function unmatchableKinds(episodeKinds) {
  const out = {};
  for (const k of Object.keys(REF_FIELDS)) {
    const fields = episodeKinds && episodeKinds[k] && Array.isArray(episodeKinds[k].fields) ? episodeKinds[k].fields : [];
    const missing = REF_FIELDS[k].filter((f) => !fields.includes(f));
    if (!fields.includes('hall')) missing.push('hall');
    if (missing.length) out[k] = missing;
  }
  return out;
}
/* the app stamps t as new Date().toISOString() (web/build_3d.py, recordEpisode);
   an episode whose t is not a string that parses to a finite time is no match */
function episodeTimeOk(ep) { return typeof ep.t === 'string' && isFinite(Date.parse(ep.t)); }
function episodeEvidence(step, hall, training, meta, skipped) {
  if (!(step.kind in REF_FIELDS) || !Array.isArray(training)) return null;
  if (step.kind in unmatchableKinds(meta.episode_kinds)) return null;
  for (const ep of training) {
    if (!ep || typeof ep !== 'object' || ep.kind !== step.kind || ep.hall !== hall) continue;
    if (!episodeTimeOk(ep)) { if (skipped) skipped.add(ep); continue; }
    if (ep.actor !== undefined && ep.actor !== meta.human_actor) continue;
    if (!REF_FIELDS[step.kind].every((f) => step[f] !== undefined && ep[f] === step[f])) continue;
    const ev = { episode: step.kind, t: ep.t, hall };
    for (const f of REF_FIELDS[step.kind]) ev[f] = step[f];
    return ev;
  }
  return null;
}

function stepEvidence(step, prog, hall, training, meta, skipped) {
  if (step.kind in REF_FIELDS) return episodeEvidence(step, hall, training, meta, skipped);
  const sims = (prog && typeof prog.sims === 'object' && prog.sims) ? prog.sims : {};
  const tools = (prog && typeof prog.tools === 'object' && prog.tools) ? prog.tools : {};
  const stations = (prog && Array.isArray(prog.stations)) ? prog.stations : [];
  if (step.kind === 'sim') {
    const rec = Object.prototype.hasOwnProperty.call(sims, step.sim) ? sims[step.sim] : null;
    if (!rec || typeof rec !== 'object') return null;
    /* the app keeps one record per seat; a record that names scenarios is
       held to the scenario the step names, one that does not is held to the seat */
    let src = rec;
    if (rec.scenarios && typeof rec.scenarios === 'object') {
      if (!Object.prototype.hasOwnProperty.call(rec.scenarios, step.scenario)) return null;
      src = rec.scenarios[step.scenario];
      if (!src || typeof src !== 'object') return null;
    }
    if (src.passed !== true) return null;
    return { sim: step.sim, scenario: step.scenario,
      score: typeof src.score === 'number' ? src.score : null, passed: true };
  }
  if (step.kind === 'station') {
    return stations.includes(step.station) ? { station: step.station } : null;
  }
  if (step.kind === 'crib') {
    const rec = Object.prototype.hasOwnProperty.call(tools, step.crib) ? tools[step.crib] : null;
    if (!rec || typeof rec !== 'object' || rec.passed !== true) return null;
    return { crib: step.crib, passed: true };
  }
  /* walk and placard record nothing anywhere; walkaround, advisor and crew
     write episodes to the training log, which is not the record this is
     built from, and the seat-level walkaround tally names no point */
  return null;
}

/* A lesson counts as done for play when every step of it that this device CAN
   record carries evidence under the progress page's own rule, and there is at
   least one such step. Silent kinds (records null and not device-marked: walk,
   placard) and episode kinds whose fields cannot match (unmatchableKinds) are
   recorded by nothing, so no lesson could ever count if they were required;
   this is the line the progress page's continue point draws, not its
   "complete", and it never enters any record. */
function questLessonsDone(prog, training, D) {
  if (!D || !D.lessons || !D.meta || !D.meta.step_kinds || !D.meta.episode_kinds) throw new Error('quests: lesson data missing');
  const unmatch = unmatchableKinds(D.meta.episode_kinds);
  const sk = D.meta.step_kinds;
  const silent = Object.keys(sk).filter((k) => sk[k].records === null && !EVIDENCED_KINDS.includes(k));
  const p = (prog && typeof prog === 'object' && !Array.isArray(prog)) ? prog : {};
  const t = Array.isArray(training) ? training : null;
  const out = new Set();
  for (const id of Object.keys(D.lessons)) {
    const L = D.lessons[id];
    const rec = L.steps.filter((s) => !silent.includes(s.kind) && !(s.kind in unmatch));
    if (!rec.length) continue;
    if (rec.every((s) => stepEvidence(s, p, L.hall, t, D.meta, null) !== null)) out.add(id);
  }
  return out;
}
function questEmptyState() { return { found: {}, done: {}, badges: [] }; }
function questParseState(raw) {
  const st = questEmptyState();
  let v = null;
  try { v = raw ? JSON.parse(raw) : null; } catch (e) { v = null; }
  if (!v || typeof v !== 'object' || Array.isArray(v)) return st;
  for (const k of ['found', 'done']) {
    if (v[k] && typeof v[k] === 'object' && !Array.isArray(v[k])) {
      for (const id of Object.keys(v[k])) if (typeof v[k][id] === 'string') st[k][id] = v[k][id];
    }
  }
  if (Array.isArray(v.badges)) st.badges = v.badges.filter((b) => typeof b === 'string');
  return st;
}
function questCheck(q, st, lessonsDone, T) {
  if (!q || !q.requires) throw new Error('quests: no such quest');
  const missing = [];
  for (const id of q.requires.lessons) if (!lessonsDone.has(id)) missing.push({ kind: 'lesson', id, title: T.lessons[id] });
  for (const h of q.requires.halls) {
    let any = false;
    for (const l of lessonsDone) if (T.lesson_hall[l] === h) any = true;
    if (!any) missing.push({ kind: 'hall', id: h, title: T.halls[h] });
  }
  for (const id of q.requires.quests) if (!(id in st.done) && !(id in st.found)) missing.push({ kind: 'quest', id, title: T.quests[id] });
  return { ok: missing.length === 0, missing };
}
/* records a find (treasure/egg) or a completion (everything else); returns a
   new state and whether anything changed. Never records a locked entry. */
function questRecord(st, q, iso, check) {
  if (!check.ok) return { state: st, changed: false };
  const slot = QUEST_KINDS_FINDABLE.includes(q.kind) ? 'found' : 'done';
  if (q.id in st[slot]) return { state: st, changed: false };
  const next = { found: { ...st.found }, done: { ...st.done }, badges: st.badges.slice() };
  next[slot][q.id] = iso;
  if (!next.badges.includes(q.reward.badge)) next.badges.push(q.reward.badge);
  return { state: next, changed: true };
}
/* one keystroke into a rolling buffer; returns the triggers it completes */
function questKeys(buf, key, words) {
  const b = buf.concat([key]).slice(-24);
  const hits = [];
  const tail = b.slice(-QUEST_KONAMI.length).map((k) => (k.length === 1 ? k.toLowerCase() : k));
  if (tail.length === QUEST_KONAMI.length && tail.every((k, i) => k === QUEST_KONAMI[i])) hits.push('konami');
  const typed = b.filter((k) => k.length === 1).join('').toLowerCase();
  for (const w of words) if (typed.endsWith(w)) hits.push('typed:' + w);
  return { buf: b, hits };
}
/* QUEST_CORE:END */

export { QUEST_STORE, QUEST_KONAMI, EVIDENCED_KINDS, REF_FIELDS, unmatchableKinds, stepEvidence, questLessonsDone, questEmptyState, questParseState, questCheck, questRecord, questKeys };
