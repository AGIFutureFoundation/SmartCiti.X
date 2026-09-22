/* ei/test.mjs — the emotional-intelligence layer, checked.
 *
 * The rule this suite follows is the bundle's: never confirm a number by
 * reading it. Every count the registry publishes is recomputed here from the
 * records it publishes, and every figure the registry borrowed from another
 * file is re-extracted here from that file — the spec's affect labels, the
 * spec's turn ceiling, the bus's topic owners, fabric's over-help thresholds
 * and measured lift, the advisor registry's own ids and names.
 *
 * Two families of check matter more than the rest, because a failure in
 * either is a failure that reaches a person having a bad day:
 *
 *   STRUCTURE — every response carries a scope, an observable stop
 *   condition, a bounded turn count and a rung of a ladder of humans; every
 *   red line carries the action that replaces the thing it forbids.
 *
 *   CONTAINMENT — no telephone number, emergency number, web address, email
 *   or named organisation appears anywhere in the payload, and no field
 *   reads like a line of scripted speech. Those are regexed over every
 *   string value in the file, not spot-checked.
 */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok ' + m); }
                       else { fail++; console.log('  FAIL ' + m); } };

const read = (p) => readFileSync(join(ROOT, p), 'utf8');
const J = (p) => JSON.parse(read(p));

/* Exactly one match or the suite has lost the thing it was checking. */
const one = (p, re, what) => {
  const m = read(p).match(new RegExp(re.source, re.flags.replace('g', '')));
  const all = read(p).match(new RegExp(re.source, re.flags + (re.flags.includes('g') ? '' : 'g')));
  if (!m || !all || all.length !== 1) {
    throw new Error(`${what}: ${re} matched ${all ? all.length : 0} times in ${p}`);
  }
  return m;
};

const E = J('ei/registry/ei.json');
const ADV = J('agents/registry/advisors.json');
const MAN = J('pack/manifest.json');
const HALLS = J('pack/registry/halls.json');

const byId = (xs) => Object.fromEntries(xs.map((x) => [x.id, x]));
const SIG = byId(E.signals);
const ST = byId(E.states);
const RESP = byId(E.responses);
const RL = byId(E.red_lines);
const DBM = byId(E.debrief_moves);
const RUNG = byId(E.handoff_ladder);
const FW = byId(E.frameworks);
const C = E.counts;

console.log('ei/test.mjs');

/* ---- provenance ----------------------------------------------------- */
ok(E.pack === 'ei', 'the registry names its own pack');
ok(E.honesty.status.startsWith('AUTHORED:'),
   'the honesty block opens with the provenance tier, and it is AUTHORED — '
   + 'no clinician wrote this and it does not pretend a tier it has not '
   + 'earned');
ok(['RECORDED', 'DERIVED', 'SCHEMATIC', 'AUTHORED', 'SCRIPTED']
   .includes(E.honesty.status.split(':')[0]),
   'and that tier is one of the five the repo recognises');
ok(!JSON.stringify(E).includes('AI-SYNTHESIZED'),
   'the reserved provenance word does not appear here — it belongs to orbis/');
ok(E.pack_version === MAN.pack_version,
   'the pack version is the manifest\'s, not a second opinion about it');
{
  const src = readFileSync(join(HERE, 'build.py'));
  ok(createHash('sha256').update(src).digest('hex').slice(0, 16)
     === E.source_stamp,
     'the registry was built from the builder now on disk (stamp check)');
}
ok(E.contract.includes('agents/registry/advisors.json'),
   'the contract names the registry an agent binding has to resolve against');

/* ---- what this pack borrowed, re-extracted from the files it borrowed
 * from rather than read back out of the registry --------------------- */
{
  const spec = read('SmartCitiX_TradeCraft_Academy_Spec.md');
  const sec = spec.split('## 7. ACP-07')[1].split('## 8.')[0];
  const labels = [...new Set([...sec.matchAll(/\| `([A-Z]+)` \|/g)]
    .map((m) => m[1]))].sort();
  ok(labels.length === 4
     && labels.join() === [...E.read_values.affect_labels].sort().join(),
     'the four ACP-07 affect labels in the registry are the four the spec\'s '
     + 'own table lists (' + labels.join('/') + ')');

  const ceil = Number(one('SmartCitiX_TradeCraft_Academy_Spec.md',
    /bounded dialogue \(. (\d+) turns\)/, 'the turn ceiling')[1]);
  ok(ceil === E.read_values.turn_ceiling && ceil === C.max_turns_ceiling,
     `the turn ceiling (${ceil}) is the spec's own bound on an agent `
     + 'dialogue, not a looser one invented for a harder conversation');

  const nodiag = one('SmartCitiX_TradeCraft_Academy_Spec.md',
    /(No diagnostic inference from telemetry, ever\.)/,
    'the governance sentence')[1];
  ok(nodiag === E.read_values.no_diagnostic_inference,
     'the no-diagnosis sentence is quoted from ACP-08 verbatim, not '
     + 'paraphrased into something softer');

  const days = Number(one('SmartCitiX_TradeCraft_Academy_Spec.md',
    /after . (\d+) days away/, 'the re-entry threshold')[1]);
  ok(days === E.read_values.reentry_days,
     `the re-entry threshold (${days} days) is the spec's`);
}
{
  const ev = read('fabric/evals.mjs');
  const maxOh = Number(ev.match(/rungDisciplineMax:\s*([\d.]+)/)[1]);
  const nonInf = Number(ev.match(/outcomeNonInferiority:\s*(-?[\d.]+)/)[1]);
  const lift = read('fabric/README.md')
    .match(/lift .(0\.\d+) against a .(0\.\d+) threshold/);
  ok(maxOh === E.read_values.over_help_rate_max
     && nonInf === E.read_values.outcome_non_inferiority,
     'the over-help ceiling and the gate-5 threshold are fabric/evals.mjs\'s '
     + 'own constants');
  ok(-Number(lift[1]) === E.read_values.over_helper_observed_lift,
     `the over-helper's measured lift (${E.read_values.over_helper_observed_lift}) `
     + 'is the figure fabric/README.md reports, not a number typed here');
  ok(-Number(lift[2]) === nonInf,
     'and fabric\'s prose and fabric\'s code still agree about the threshold, '
     + 'which is why this pack could read either');
}
{
  const topics = [...new Set([...read('bus/bus.mjs')
    .matchAll(/'([a-z_]+\.[a-z_]+)':\s+'/g)].map((m) => m[1]))].sort();
  ok(topics.join() === [...E.read_values.bus_topics].sort().join(),
     'the bus topics a signal may name are the topics bus/bus.mjs actually '
     + 'declares an owner for');
}

/* ---- responses: the structure that makes the hard limit hard -------- */
{
  let noScope = 0, noStop = 0, badRung = 0, noDoes = 0, noDoesNot = 0;
  let badState = 0, badFw = 0, badNotice = 0, badTurns = 0, raises = 0;
  for (const r of E.responses) {
    if (typeof r.scope !== 'string' || r.scope.trim().length < 20) noScope++;
    if (typeof r.stop_condition !== 'string'
        || r.stop_condition.trim().length < 20) noStop++;
    if (!(r.handoff in RUNG)) badRung++;
    if (!Array.isArray(r.does) || !r.does.length) noDoes++;
    if (!Array.isArray(r.does_not) || !r.does_not.length) noDoesNot++;
    if (!(r.state in ST)) badState++;
    if (!(r.framework in FW)) badFw++;
    if (r.notices.some((n) => !(n in SIG))) badNotice++;
    if (!(Number.isInteger(r.max_turns) && r.max_turns >= 1
          && r.max_turns <= C.max_turns_ceiling)) badTurns++;
    if (r.rung_effect.raises_served_rung !== false) raises++;
  }
  ok(noScope === 0,
     `all ${E.responses.length} responses carry a scope that says what they `
     + 'cover');
  ok(noStop === 0,
     `all ${E.responses.length} responses carry an observable stop_condition `
     + '— the point at which the agent stops coaching');
  ok(badRung === 0,
     'every response hands off to a rung that exists on the ladder');
  ok(noDoes === 0 && noDoesNot === 0,
     'every response says both what it does and what it does NOT do — the '
     + 'second list is the one that keeps an agent out of therapy');
  ok(badState === 0, 'every response answers a state that exists');
  ok(badFw === 0, 'every response names a declared framework');
  ok(badNotice === 0, 'every signal a response claims to notice exists');
  ok(badTurns === 0,
     'every response bounds its own exchange at or under the spec ceiling of '
     + C.max_turns_ceiling + ' turns');
  ok(raises === 0 && C.responses_that_raise_the_rung === 0,
     'no response raises the served hint rung: fabric measured an '
     + `over-helper at a cohort lift of ${E.read_values.over_helper_observed_lift} `
     + `against ${E.read_values.outcome_non_inferiority}, and sympathy is not `
     + 'an exemption from that finding');
  ok(E.responses.some((r) => r.rung_effect.dial_may_step_down === true)
     && E.responses.some((r) => r.rung_effect.dial_may_step_down === false),
     'the dial stepping difficulty down and an agent raising the hint rung '
     + 'are kept as different acts, and both answers appear');
}
{
  const covered = new Set(E.responses.map((r) => r.state));
  const missing = E.states.filter((s) => !covered.has(s.id)).map((s) => s.id);
  ok(missing.length === 0,
     `every one of the ${E.states.length} states has at least one response — `
     + 'a state named and left unanswered is worse than one never named');
}
{
  const handoffOnly = E.states.filter((s) => s.agent_may === 'hand-off-only');
  ok(handoffOnly.length === C.states_handoff_only && handoffOnly.length >= 1,
     `${handoffOnly.length} state is handed off rather than answered, so the `
     + 'pack has not quietly decided it can handle everything');
  for (const s of handoffOnly) {
    const rs = E.responses.filter((r) => r.state === s.id);
    ok(rs.length === 1 && rs[0].max_turns === 1 && rs[0].universal === true,
       `the ${s.id} response is one turn, universal to every agent, and is `
       + 'the whole of what an agent may do with it');
    ok(rs[0].does_not.some((d) => /does not ask what happened/i.test(d)),
       'and it is forbidden from asking what happened — an app that collects '
       + 'the story of a bad call has made the learner tell it twice for '
       + 'nothing');
    const tech = /breath|ground|technique|exercise/i;
    ok(rs[0].does.length >= 3 && !rs[0].does.some((d) => tech.test(d))
       && rs[0].does_not.some((d) => tech.test(d)),
       'and it offers no breathing, grounding or other technique — it is '
       + 'forbidden from offering one, because it is not qualified to');
  }
}

/* ---- the ladder ----------------------------------------------------- */
{
  const ranks = E.handoff_ladder.map((r) => r.rank);
  ok(ranks.join() === ranks.map((_, i) => i + 1).join(),
     `the ladder is ${ranks.length} contiguous rungs from 1 — a ladder with a `
     + 'gap is not a ladder');
  ok(E.handoff_ladder.every((r) => r.resource_type && r.reached_how
     && r.agent_does && r.agent_must_not && r.latency
     && r.why_no_contact_detail),
     'every rung says what type of resource it is, how it is reached, what '
     + 'the agent does, what the agent must not do, and why it carries no '
     + 'contact detail');
  const top = E.handoff_ladder[E.handoff_ladder.length - 1];
  ok(top.id === 'emergency-services' && top.rank === ranks.length,
     'the top rung is emergency services');
  ok(/dial/i.test(top.agent_must_not) && /number/i.test(top.agent_must_not),
     'and at that rung the agent is forbidden from dialling anything itself '
     + 'and from printing a number — it cannot know which country the '
     + 'learner is in');
  ok(E.handoff_ladder.some((r) => /member-assistance|assistance programme/i
     .test(r.resource_type)),
     'the union member-assistance / employer EAP rung is on the ladder as a '
     + 'TYPE of programme');
  const instance = /\b[A-Z][a-z]+ (?:Foundation|Society|Association|Trust|Line|Programme|Program|Services)\b/;
  ok(E.handoff_ladder.every((r) => !instance.test(JSON.stringify(r))),
     'and no rung names an instance of anything — no Foundation, Society, '
     + 'Association, Trust, Line or Programme with a capital letter on it');
}

/* ---- red lines ------------------------------------------------------ */
{
  let noAction = 0, badHandoff = 0, unexplained = 0;
  for (const r of E.red_lines) {
    if (typeof r.required_action !== 'string'
        || r.required_action.trim().length < 20) noAction++;
    if (r.handoff === null) {
      if (!r.no_handoff_because) unexplained++;
    } else if (!(r.handoff in RUNG)) badHandoff++;
  }
  ok(noAction === 0,
     `all ${E.red_lines.length} red lines carry the action that replaces the `
     + 'thing they forbid — a prohibition with no instead is an agent left '
     + 'improvising');
  ok(badHandoff === 0, 'every red line that hands off names a real rung');
  ok(unexplained === 0,
     'and every red line that hands off nowhere says why not, rather than '
     + 'leaving a null for a reader to interpret');
  ok(E.red_lines.filter((r) => r.handoff !== null).length
     === C.red_lines_ending_in_a_handoff,
     'the count of red lines ending in a handoff is the red lines ending in '
     + 'a handoff, counted');
}
{
  const want = ['no-diagnosis', 'no-medication', 'no-confidentiality-promise',
    'no-coaching-through-self-harm',
    'no-coaching-through-substance-dependence',
    'no-coaching-through-domestic-violence',
    'no-coaching-through-workplace-abuse'];
  const missing = want.filter((w) => !(w in RL));
  ok(missing.length === 0,
     'the named red lines are all present: diagnosis, medication, promised '
     + 'confidentiality, and coaching through self-harm, substance '
     + 'dependence, domestic violence or workplace abuse');
  ok(RL['no-coaching-through-self-harm'].handoff === 'emergency-services',
     'a disclosure of self-harm reaches the top of the ladder rather than a '
     + 'gentler rung');
  ok(/stop/i.test(RL['no-coaching-through-self-harm'].required_action)
     && /same turn/i.test(RL['no-coaching-through-self-harm'].required_action),
     'and the coaching stops in the same turn, not after one more helpful '
     + 'question');
  ok(/log|visible|instructor|record/i
     .test(RL['no-confidentiality-promise'].why),
     'the confidentiality red line gives the concrete reason the promise '
     + 'would be a lie here — the affect labels an instructor can see and '
     + 'the override log');
  ok('no-affect-in-a-score' in RL && RL['no-affect-in-a-score'].handoff === null,
     'and there is a red line keeping every one of these paths out of the '
     + 'grading route');
}

/* ---- signals are observations, not diagnoses ------------------------ */
{
  let noConfound = 0, noNote = 0, calibrated = 0, badTopic = 0, badState = 0;
  let body = 0;
  for (const s of E.signals) {
    if (!s.confound || s.confound.length < 20) noConfound++;
    if (!s.not_a_diagnosis || !/not a (diagnosis|statement)/i
      .test(s.not_a_diagnosis)) noNote++;
    if (s.threshold.value !== null) calibrated++;
    if (!E.read_values.bus_topics.includes(s.bus_topic)) badTopic++;
    if (s.may_mean.some((m) => !(m in ST))) badState++;
    if (s.reads_body) body++;
  }
  ok(noNote === 0,
     `all ${E.signals.length} signals carry their own note that a signal is `
     + 'not a diagnosis — it is per-record, so it cannot be skipped by a '
     + 'reader who started in the middle');
  ok(noConfound === 0,
     'and every one carries the innocent explanation that is at least as '
     + 'likely — the shift worker whose 3am session is just an evening');
  ok(calibrated === 0 && C.signals_with_calibrated_threshold === 0,
     `${calibrated} of ${E.signals.length} thresholds are fitted to a real `
     + 'cohort, and the nulls say so rather than carrying a guess');
  ok(E.signals.every((s) => s.threshold.why && s.threshold.why.length > 40),
     'each null threshold explains itself');
  ok(badTopic === 0, 'every signal names a bus topic the bus really owns');
  ok(badState === 0, 'every state a signal points at exists');
  ok(body === 0,
     'no signal reads a body: there is no camera, microphone or wearable in '
     + 'this bundle\'s input contract, and inferring affect from a person '
     + 'rather than from their actions is the line the governance draws');
  ok(E.signals.filter((s) => s.observable_today).length
     === C.signals_observable_today
     && C.signals_observable_today < E.signals.length,
     `${C.signals_observable_today} of ${E.signals.length} signals could be `
     + 'emitted today, and the shortfall is published rather than smoothed '
     + 'over');
}

/* ---- states --------------------------------------------------------- */
{
  const labels = E.read_values.affect_labels;
  ok(E.states.every((s) => s.acp07_nearest === null
     || labels.includes(s.acp07_nearest)),
     'every state maps onto an ACP-07 label the classifier actually emits, '
     + 'or onto null — it never invents a fifth');
  ok(E.states.some((s) => s.acp07_nearest === null),
     'and at least one state has no classifier label, because being frozen '
     + 'out by a crew is not a thing a flow classifier can see');
  ok(E.states.every((s) => s.typical_signals.every((x) => x in SIG)),
     'every signal a state lists exists');
  ok(E.states.every((s) => ['routine', 'elevated', 'hand-off-only']
     .includes(s.urgency)),
     'every state carries one of the three declared urgencies');
  ok(E.states.every((s) => s.is_not && s.is_not.length > 30),
     'every state says what it is NOT, which is where the diagnosis would '
     + 'otherwise creep in');
  ok(E.states.every((s) => s.first_suspect && s.first_suspect.length > 20),
     'and every state names its first suspect — for most of them the '
     + 'content or the sequence, not the learner');
  const wanted = ['frustration', 'shame-after-error', 'fear-of-machine',
    'overwhelm', 'disengagement', 'burnout', 'exclusion-or-hazing',
    'post-incident-distress'];
  ok(wanted.every((w) => w in ST) && E.states.length === wanted.length,
     'the eight states are the eight the brief named, and there is no ninth '
     + 'smuggled in');
}

/* ---- debrief moves -------------------------------------------------- */
{
  ok(E.debrief_moves.every((d) => d.forbidden_variant
     && d.forbidden_variant.length > 30),
     'every debrief move names the flattering version of itself that must '
     + 'not be used — "good effort" is the one this bundle bans everywhere '
     + 'else');
  ok(E.debrief_moves.every((d) => d.available_today || d.unavailable_because),
     'a move that cannot run today says why');
  ok(E.debrief_moves.filter((d) => d.available_today).length
     === C.debrief_moves_available_today
     && C.debrief_moves_available_today < E.debrief_moves.length,
     `${C.debrief_moves_available_today} of ${E.debrief_moves.length} moves `
     + 'can run today; the one that is off needs a cohort failure rate that '
     + 'does not exist, and it stays off rather than guessing');
  ok(E.debrief_moves.some((d) => d.separates_person_from_mistake)
     && E.debrief_moves.some((d) => d.names_next_attempt),
     'the debrief separates the person from the mistake and leaves a named '
     + 'next attempt — the two things that decide whether a learner comes '
     + 'back');
  ok(/normalise/i.test(JSON.stringify(DBM['normalise-with-a-rate']))
     && DBM['normalise-with-a-rate'].available_today === false,
     'normalising an error is written to require a measured rate, and is '
     + 'switched off until there is one — "everyone finds this hard" is the '
     + 'guess it exists to replace');
}

/* ---- agent bindings resolve against the real advisor registry ------- */
{
  const ids = Object.keys(ADV.advisors).sort();
  const bound = E.agent_bindings.map((b) => b.agent).sort();
  ok(bound.join() === ids.join(),
     `all ${ids.length} advisors in agents/registry/advisors.json are bound, `
     + 'and nothing is bound that is not an advisor');
  ok(E.agent_bindings.every((b) => b.agent in ADV.advisors
     && b.agent_name === ADV.advisors[b.agent].name
     && b.agent_role === ADV.advisors[b.agent].role),
     'every binding carries the advisor\'s own name and role from that '
     + 'registry, so a rename there cannot leave a stale copy here');
  ok(E.agent_bindings.every((b) => b.responses.every((r) => r in RESP)),
     'every response id a binding lists exists');
  ok(E.agent_bindings.every((b) => b.debrief_moves.every((d) => d in DBM)),
     'every debrief move a binding lists exists');
  ok(E.agent_bindings.every((b) => b.states_out_of_scope.every((s) => s in ST)),
     'every state a binding declares out of scope exists');
  const allRl = Object.keys(RL).sort().join();
  ok(E.agent_bindings.every((b) => b.red_lines.slice().sort().join() === allRl),
     'every agent carries every red line — there is no agent in this bundle '
     + 'that holds only some of them');
  const universal = E.responses.filter((r) => r.universal).map((r) => r.id);
  ok(universal.length === C.universal_responses && universal.length >= 1
     && E.agent_bindings.every((b) => universal
       .every((u) => b.responses.includes(u))),
     'and every agent carries the universal response, because any agent can '
     + 'be the one a learner tells');
  ok(E.agent_bindings.every((b) => b.scope_note && b.scope_note.length > 40),
     'every binding says why that agent gets that set rather than another');
  ok(E.agent_bindings.some((b) => b.responses.length === universal.length),
     'at least one advisor carries nothing but the universal response and '
     + 'the red lines — the records clerk is not given a bedside manner it '
     + 'has no business having');
}

/* ---- CONTAINMENT: no number, no organisation, no speech ------------- */
{
  const strings = [];
  const badKeys = [];
  const walk = (n, p) => {
    if (Array.isArray(n)) n.forEach((v, i) => walk(v, `${p}[${i}]`));
    else if (n && typeof n === 'object') {
      for (const [k, v] of Object.entries(n)) {
        if (['say', 'says', 'script', 'line', 'dialogue', 'utterance',
             'speech'].includes(k)) badKeys.push(`${p}.${k}`);
        walk(v, `${p}.${k}`);
      }
    } else if (typeof n === 'string') strings.push([p, n]);
  };
  walk(E, 'ei');

  const hits = (re) => strings.filter(([, s]) => re.test(s))
    .map(([p, s]) => `${p}: ${s.match(re)[0]}`);

  /* 111 is this bundle's hall count and appears in the payload as one, so it
   * is deliberately not in this list; the four that are cannot be confused
   * with a number this bundle publishes about itself. */
  const phone = hits(/\+?\d[\d ().-]{6,}\d/);
  ok(phone.length === 0,
     'no string in the payload is shaped like a telephone number ('
     + strings.length + ' strings scanned)');
  ok(hits(/\b9-?1-?1\b|\b9-?9-?9\b|\b9-?8-?8\b|\b1-?1-?2\b/).length === 0,
     'no emergency or crisis-line number appears — a wrong number in a '
     + 'crisis is worse than none, and this build has no network with which '
     + 'to check one');
  ok(hits(/\b(?:call|dial|text|ring|phone)\s+(?:the\s+|a\s+)?\d/i).length === 0,
     'and nothing instructs anyone to dial digits');
  ok(hits(/https?:\/\/|www\.|\S+@\S+\.\w/).length === 0,
     'no web address and no email address');
  ok(hits(/\b(?:SAMHSA|Samaritans|Lifeline|Befrienders|Shout|Trevor|MIND|NHS|OSHA|NIOSH|ICISF|Red Cross|Alcoholics Anonymous|Narcotics Anonymous|Crisis Text Line|Suicide Prevention)\b/).length === 0,
     'no organisation, helpline or service is named anywhere: the ladder '
     + 'names five TYPES of resource and no instance of any of them');
  ok(badKeys.length === 0,
     'no record carries a say/script/line/dialogue field — this pack writes '
     + 'structure, and a scripted line here would be simulated therapy with '
     + 'a registry\'s authority behind it');
  ok(strings.every(([, s]) => !(/^["'“]/.test(s)
     && /["'”]\s*$/.test(s))),
     'and no field is a quoted utterance');
  ok(strings.length > 400,
     `the containment scan covered every string in the payload (${strings.length})`);
}

/* ---- the honesty block quotes its own numbers ----------------------- */
{
  const h = E.honesty;
  ok(h.not_reviewed.includes(`${C.clinician_reviewed_records} of ${C.records}`),
     `the honesty block publishes the sign-off gap as a number — `
     + `${C.clinician_reviewed_records} of ${C.records} records reviewed by a `
     + 'clinician — rather than describing it');
  ok(C.clinician_reviewed_records === 0,
     'and that number is zero, which is the true one');
  ok(/clinician|counsellor|psychologist|social worker/i.test(h.not_reviewed),
     'and it names the kinds of professional who have not read it');
  ok(h.not_a_therapist.includes(String(C.responses))
     && h.not_a_therapist.includes(String(C.longest_response_turns))
     && h.not_a_therapist.includes(String(C.max_turns_ceiling)),
     'the not-a-therapist note quotes the response count, the longest '
     + 'exchange and the ceiling it is measured against');
  ok(/not a therapist/i.test(h.not_a_therapist)
     && /not a crisis line/i.test(h.not_a_therapist),
     'and says the words outright');
  ok(h.no_contact_details.includes(String(C.handoff_rungs)),
     'the no-contact-details note quotes the number of rungs it names types '
     + 'for');
  ok(h.no_comfort_over_help.includes(
    E.read_values.over_helper_observed_lift.toFixed(3))
     && h.no_comfort_over_help.includes(
       E.read_values.outcome_non_inferiority.toFixed(2))
     && h.no_comfort_over_help.includes(
       `${C.responses_that_raise_the_rung} of the ${C.responses}`),
     'the over-help note quotes fabric\'s measured lift, fabric\'s threshold '
     + 'and this pack\'s own count of responses that raise the rung');
  ok(h.signals_are_not_diagnoses.includes(
    E.read_values.no_diagnostic_inference),
     'the signals note quotes ACP-08\'s own sentence rather than a softer '
     + 'paraphrase of it');
  ok(h.signals_are_not_diagnoses.includes(String(C.signals)),
     'and the signal count it is talking about');
  ok(h.the_dial_is_not_this_pack.includes(
    E.read_values.acp07_anxiety_response),
     'and the dial note quotes ACP-07\'s declared response verbatim, so this '
     + 'pack cannot be read as authorising the dial to do something else');
  ok(h.ladder_is_untested.includes(
    `${C.handoff_rungs_ever_exercised} of the ${C.handoff_rungs}`),
     'the ladder note publishes how many rungs have ever carried a person');
  ok(h.responder_series_is_unbuilt.includes(
    `${C.halls_that_are_a_responder_service} of ${C.halls_in_roster}`)
     && h.responder_series_is_unbuilt
       .includes(String(C.halls_that_are_rescue_disciplines))
     && h.responder_series_is_unbuilt
       .includes(String(C.halls_matching_responder_words)),
     'and the responder note publishes all three hall counts, including the '
     + 'keyword count a careless reader would have taken');
  ok(Object.values(h).every((v) => !/proud|excellent|world-class|best-in-class|robust/i.test(v)),
     'nothing in the honesty block congratulates the pack on itself');
}

/* ---- gaps are numbers ----------------------------------------------- */
{
  ok(E.gaps.length >= 5, `the pack publishes ${E.gaps.length} gaps`);
  ok(E.gaps.every((g) => Number.isInteger(g.have) && Number.isInteger(g.of)
     && g.of > 0 && g.have <= g.of),
     'every gap is a have over an of, both integers');
  ok(E.gaps.every((g) => g.share
     === Math.round((g.have / g.of) * 1e4) / 1e4),
     'every published share is its own have over its own of, to the same '
     + 'four places the builder rounds to');
  ok(E.gaps.every((g) => g.how_counted && g.how_counted.length > 40
     && g.standing && g.standing.length > 40),
     'every gap says how it was counted and what it means for the reader');
  ok(new Set(E.gaps.map((g) => g.id)).size === E.gaps.length,
     'gap ids are unique');
  const clin = E.gaps.find((g) => g.id === 'ei.clinician_reviewed');
  ok(clin && clin.have === 0 && clin.of === C.records,
     `the sign-off gap is 0 of ${C.records}, the same denominator the counts `
     + 'block publishes');
  ok(E.gaps.filter((g) => g.have === 0).length >= 3,
     'and at least three gaps are flat zero — the pack does not round its '
     + 'emptiness up');
}

/* ---- counts, recomputed --------------------------------------------- */
{
  const recomputed = E.signals.length + E.states.length + E.responses.length
    + E.red_lines.length + E.debrief_moves.length + E.agent_bindings.length;
  ok(C.records === recomputed,
     `counts.records is the six collections added up (${recomputed})`);
  ok(C.signals === E.signals.length && C.states === E.states.length
     && C.responses === E.responses.length && C.red_lines === E.red_lines.length
     && C.debrief_moves === E.debrief_moves.length
     && C.agent_bindings === E.agent_bindings.length
     && C.frameworks === E.frameworks.length
     && C.handoff_rungs === E.handoff_ladder.length,
     'every collection count is that collection, counted');
  ok(C.advisors_in_registry === Object.keys(ADV.advisors).length,
     'counts.advisors_in_registry is the advisor registry\'s own length');
  ok(C.states_the_agent_may_respond_to + C.states_handoff_only
     === E.states.length,
     'the answered and handed-off states partition the set — no state is '
     + 'both and none is neither');
  ok(C.longest_response_turns
     === Math.max(...E.responses.map((r) => r.max_turns)),
     'counts.longest_response_turns is the longest response, measured');
  ok(C.universal_responses === E.responses.filter((r) => r.universal).length,
     'counts.universal_responses is the universal responses, counted');
  ok(C.halls_in_roster === HALLS.halls.length,
     'counts.halls_in_roster is the roster\'s own length');
  const words = /fire|rescue|medic|ambulance|emergency|responder|hazmat|paramedic/i;
  const kw = HALLS.halls.filter((h) => words
    .test(`${h.slug} ${h.name} ${h.focus}`));
  ok(kw.length === C.halls_matching_responder_words,
     `${kw.length} halls match a responder keyword, recomputed from the `
     + 'roster');
  ok(C.halls_that_are_a_responder_service === 0
     && C.halls_that_are_rescue_disciplines < kw.length,
     'and the three counts genuinely differ: the keyword count would have '
     + 'said this bundle already serves responders, and it does not — fire '
     + 'sprinkler fitters install sprinklers');
  ok(E.read_values.rescue_halls.every((r) => {
    const h = HALLS.halls.find((x) => x.slug === r.slug);
    return h && h.name === r.name && h.focus === r.focus;
  }), 'the two rescue halls carry the roster\'s own name and focus, not a '
     + 'retyped description of them');
}

console.log(`\n${pass} ok, ${fail} failed`);
process.exit(fail ? 1 : 0);
