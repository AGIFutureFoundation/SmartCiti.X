#!/usr/bin/env node
/**
 * Completion record verifier.
 *
 *   node completion/verify.mjs <record.json>
 *
 * Re-checks one exported `tc-completion/1` record against the registries it
 * names. Every rule prints one line, `ok <rule>` or `FAIL <rule>` at column 0
 * (FAIL on stderr), and the process exits 1 on any failure.
 *
 * FAIL CLOSED. Every field is fetched through need(): a missing field is a
 * named failure, never a default. No nullish-coalescing default appears in
 * this file on purpose (spec §23.1: a default is a policy decision nobody made).
 *
 * WHAT A PASS MEANS. The record is internally consistent, its digest
 * recomputes, and every id in it exists in this bundle. It does NOT mean the
 * person named in identity.claimed did any of it: attestation is "this device
 * only" and there is no signing key, so a signature is refused as a forgery.
 * The pass rule per seat is read from sims/registry/sims.json; that registry
 * scores per rubric axis and has no scalar threshold, so `passed` is taken
 * from the record and said so.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

const url = (p) => new URL(p, import.meta.url);
const reg = JSON.parse(readFileSync(url('./registry/completion.json')));
const lessonsReg = JSON.parse(readFileSync(url('../lessons/registry/lessons.json')));
const simsReg = JSON.parse(readFileSync(url('../sims/registry/sims.json')));
const cribsReg = JSON.parse(readFileSync(url('../tools/registry/toolcribs.json')));
const stationsReg = JSON.parse(readFileSync(url('../stations/registry/stations.json')));
const hallsReg = JSON.parse(readFileSync(url('../pack/registry/halls.json')));

class Missing extends Error {}
export function need(obj, key, who) {
  if (obj === null || typeof obj !== 'object' || !Object.prototype.hasOwnProperty.call(obj, key)) {
    throw new Missing(`${who} lacks ${JSON.stringify(key)}`);
  }
  return obj[key];
}

// canonical JSON: keys sorted recursively, no whitespace, UTF-8
export function canonical(v) {
  if (Array.isArray(v)) return '[' + v.map(canonical).join(',') + ']';
  if (v !== null && typeof v === 'object') {
    return '{' + Object.keys(v).sort().map((k) => JSON.stringify(k) + ':' + canonical(v[k])).join(',') + '}';
  }
  return JSON.stringify(v);
}
export function digestOf(record) {
  const body = {};
  for (const k of Object.keys(record)) if (k !== 'digest') body[k] = record[k];
  return createHash('sha256').update(Buffer.from(canonical(body), 'utf8')).digest('hex');
}

const LESSONS = need(lessonsReg, 'lessons', 'lessons.json');
const LADDER = need(need(lessonsReg, 'ladder', 'lessons.json'), 'edges', 'lessons.json#ladder');
const SIMS = need(simsReg, 'sims', 'sims.json');
const CRIBS = need(cribsReg, 'cribs', 'toolcribs.json');
const STATION_IDS = new Set(need(stationsReg, 'stations', 'stations.json').map((s) => need(s, 'station_id', 'station')));
const HALL_SLUGS = new Set(need(hallsReg, 'halls', 'halls.json').map((h) => need(h, 'slug', 'hall')));
const EVIDENCE_RULE = need(reg, 'evidence_rule', 'completion.json');
const SIM_RULES = need(reg, 'sims', 'completion.json');
const RULES = need(need(reg, 'verifier', 'completion.json'), 'rules', 'completion.json#verifier');

export function verify(record) {
  const tally = {};
  for (const r of RULES) tally[r] = { checked: 0, fails: [] };
  const check = (rule, cond, msg) => { tally[rule].checked++; if (!cond) tally[rule].fails.push(msg); };
  const notes = [];

  // record.fields — fail closed on any missing field, anywhere
  const top = ['record', 'product', 'pack_version', 'exported_at', 'identity', 'lessons', 'sims', 'tools',
    'stations', 'honesty', 'digest'];
  for (const k of top) need(record, k, 'record');
  check('record.fields', need(record, 'record', 'record') === need(reg, 'record_tag', 'completion.json'),
    `record is ${JSON.stringify(record.record)}, not ${reg.record_tag}`);
  check('record.fields', need(record, 'pack_version', 'record') === need(reg, 'pack_version', 'completion.json'),
    `pack_version ${record.pack_version} is not this bundle's ${reg.pack_version}`);
  check('record.fields', typeof need(record, 'exported_at', 'record') === 'string', 'exported_at is not a string');
  const ident = need(record, 'identity', 'record');
  need(ident, 'claimed', 'identity');
  check('record.fields', need(ident, 'attested_by', 'identity') === 'this device only',
    'identity.attested_by is not "this device only"');
  const dig = need(record, 'digest', 'record');
  check('record.fields', need(dig, 'alg', 'digest') === 'SHA-256', 'digest.alg is not SHA-256');
  need(dig, 'over', 'digest');
  const hon = need(record, 'honesty', 'record');
  check('record.fields', Array.isArray(need(hon, 'proves', 'honesty')) && Array.isArray(need(hon, 'does_not_prove', 'honesty')),
    'honesty.proves / does_not_prove are not lists');

  // digest — integrity since export, not identity
  const hex = need(dig, 'hex', 'digest');
  check('digest', /^[0-9a-f]{64}$/.test(hex), 'digest.hex is not 64 hex chars');
  check('digest', digestOf(record) === hex, 'digest does not recompute over the canonical record');

  // identity.signature — this bundle cannot sign
  check('identity.signature', need(ident, 'signature', 'identity') === null,
    'this bundle cannot sign; a signature here would be a forgery');

  // ids — every id resolves in the registry that owns it
  const simsBlock = need(record, 'sims', 'record');
  for (const [sid, s] of Object.entries(simsBlock)) {
    check('ids.sim', sid in SIMS, `sim ${sid} is not in sims.json`);
    need(s, 'passed', `sims.${sid}`); need(s, 'score', `sims.${sid}`); need(s, 'attempts', `sims.${sid}`);
  }
  const toolsBlock = need(record, 'tools', 'record');
  for (const [dk, t] of Object.entries(toolsBlock)) {
    check('ids.district', dk in CRIBS, `district ${dk} is not in toolcribs.json`);
    need(t, 'passed', `tools.${dk}`);
  }
  const stationsBlock = need(record, 'stations', 'record');
  check('ids.station', Array.isArray(stationsBlock), 'stations is not a list');
  for (const st of stationsBlock) check('ids.station', STATION_IDS.has(st), `station ${st} is not in stations.json`);

  const lessons = need(record, 'lessons', 'record');
  const complete = new Map();
  const seen = new Set();
  let nComplete = 0, nFullyBacked = 0, nEpisode = 0, nDeviceMark = 0, nSelfReported = 0;
  for (const L of lessons) {
    const lid = need(L, 'lesson', 'lesson entry');
    check('ids.lesson', lid in LESSONS && !seen.has(lid), `lesson ${lid} is not in lessons.json or is listed twice`);
    seen.add(lid);
    const known = lid in LESSONS ? LESSONS[lid] : null;
    const hall = need(L, 'hall', lid);
    check('ids.hall', HALL_SLUGS.has(hall) && (!known || known.hall === hall), `${lid}: hall ${hall} does not resolve or is not the lesson's hall`);
    const isComplete = need(L, 'complete', lid);
    complete.set(lid, isComplete === true);
    const steps = need(L, 'steps', lid);
    let allDone = steps.length > 0, selfHere = 0, epHere = 0, dmHere = 0;
    const stepSeen = new Set();
    for (const S of steps) {
      const n = need(S, 'step', `${lid} step`);
      const kind = need(S, 'kind', `${lid} step ${n}`);
      const done = need(S, 'done', `${lid} step ${n}`);
      const ev = need(S, 'evidence', `${lid} step ${n}`);
      const known_step = known ? known.steps.find((k) => k.n === n) : undefined;
      check('ids.step', known_step !== undefined && known_step.kind === kind && !stepSeen.has(n),
        `${lid} step ${n} (${kind}) is not that step of that lesson`);
      stepSeen.add(n);
      check('ids.step', kind in EVIDENCE_RULE, `${lid} step ${n}: unknown step kind ${kind}`);
      if (done !== true) allDone = false;
      if (!(kind in EVIDENCE_RULE) || !known_step) continue;
      const rule = EVIDENCE_RULE[kind];
      if (rule.class === 'episode-backed') {
        if (done === true) epHere++;
        check('step.recording-evidence', done !== true || (ev !== null && typeof ev === 'object'),
          `${lid} step ${n} (${kind}): a recording step claimed done without its episode`);
        if (done === true && ev !== null && typeof ev === 'object' && kind === 'sim') {
          const es = need(ev, 'sim', `${lid} step ${n} evidence`);
          const esc = need(ev, 'scenario', `${lid} step ${n} evidence`);
          need(ev, 'score', `${lid} step ${n} evidence`); need(ev, 'passed', `${lid} step ${n} evidence`);
          check('ids.sim', es === known_step.sim && es in SIMS && es in simsBlock,
            `${lid} step ${n}: evidence sim ${es} is not the step's seat, or is missing from the sims block`);
          check('ids.scenario', esc === known_step.scenario && es in SIM_RULES && SIM_RULES[es].scenarios.includes(esc),
            `${lid} step ${n}: scenario ${esc} is not the step's scenario of seat ${es}`);
        }
        if (done === true && ev !== null && typeof ev === 'object' && kind !== 'sim') {
          const epk = need(ev, 'episode', `${lid} step ${n} evidence`);
          check('step.episode-evidence', epk === kind, `${lid} step ${n}: evidence episode ${epk} is not a ${kind} episode`);
          const t = need(ev, 't', `${lid} step ${n} evidence`);
          check('step.episode-evidence', typeof t === 'number' && Number.isFinite(t), `${lid} step ${n}: episode t is not a finite number`);
          for (const f of need(rule, 'checkable', `evidence_rule.${kind}`)) {
            const want = f === 'hall' ? known.hall : need(known_step, f, `${lid} step ${n}`);
            const got = need(ev, f, `${lid} step ${n} evidence`);
            check('step.episode-evidence', got === want, `${lid} step ${n}: episode ${f} ${JSON.stringify(got)} is not the step's ${JSON.stringify(want)}`);
          }
        }
      } else if (rule.class === 'device-mark' && done === true && ev !== null) {
        dmHere++;
        if (kind === 'station') {
          const st = need(ev, 'station', `${lid} step ${n} evidence`);
          check('ids.station', st === known_step.station && stationsBlock.includes(st),
            `${lid} step ${n}: station ${st} is not the step's station in the stations list`);
        } else if (kind === 'crib') {
          const dk = need(ev, 'crib', `${lid} step ${n} evidence`);
          need(ev, 'passed', `${lid} step ${n} evidence`);
          check('ids.district', dk === known_step.crib && dk in toolsBlock,
            `${lid} step ${n}: district ${dk} is not the step's crib in the tools block`);
        }
      } else if (rule.class === 'self-reported' && done === true) {
        selfHere++;
      }
    }
    check('lesson.complete-all-steps', isComplete !== true || (allDone && known !== null && steps.length === known.steps.length),
      `${lid}: complete with a step not done (or steps missing)`);
    if (isComplete === true) { nComplete++; nEpisode += epHere; nDeviceMark += dmHere; nSelfReported += selfHere; if (selfHere === 0 && dmHere === 0) nFullyBacked++; }
  }

  // sim.threshold — only when the registry states one
  for (const [sid, s] of Object.entries(simsBlock)) {
    if (!(sid in SIM_RULES)) continue;
    const thr = need(SIM_RULES[sid], 'threshold', `completion.json sims.${sid}`);
    if (thr === null) {
      tally['sim.threshold'].checked++;
      notes.push(`sim.threshold: ${sid} has no scalar threshold in sims.json; passed=${s.passed} is taken from the record and not re-derived`);
    } else {
      check('sim.threshold', s.passed !== true || s.score >= thr, `${sid}: passed with score ${s.score} below threshold ${thr}`);
    }
  }

  // ladder.prerequisite — a lesson complete ahead of its prerequisite
  for (const e of LADDER) {
    const lid = need(e, 'lesson', 'ladder edge'), needs = need(e, 'needs', 'ladder edge');
    if (!complete.has(lid)) continue;
    check('ladder.prerequisite', complete.get(lid) !== true || complete.get(needs) === true,
      `${lid} is complete but its prerequisite ${needs} is not`);
  }

  return { tally, notes, summary: { nComplete, nFullyBacked, nEpisode, nDeviceMark, nSelfReported } };
}

const isMain = process.argv[1] && new URL(`file://${process.argv[1]}`).pathname === new URL(import.meta.url).pathname;
if (isMain) {
  const path = process.argv[2];
  if (!path) { console.error('FAIL usage: node completion/verify.mjs <record.json>'); process.exit(1); }
  let failed = false;
  try {
    const record = JSON.parse(readFileSync(path, 'utf8'));
    const { tally, notes, summary } = verify(record);
    for (const [rule, t] of Object.entries(tally)) {
      const line = `${rule}: checked ${t.checked}, failing ${t.fails.length}`;
      if (t.fails.length) { failed = true; console.error(`FAIL ${line}`); for (const f of t.fails) console.error(`     ${f}`); }
      else console.log(`ok ${line}`);
    }
    for (const n of notes) console.log(`note ${n}`);
    console.log(`summary: ${summary.nComplete} lessons complete, of which ${summary.nFullyBacked} fully evidence-backed `
      + `(every step episode-backed); across them ${summary.nEpisode} episode-backed steps, `
      + `${summary.nDeviceMark} device-mark steps (station/crib: a device-local mark, not a recorded episode), `
      + `${summary.nSelfReported} self-reported steps counted as done`);
    console.log('this verifies integrity since export and resolution against the bundle; it attests no identity and is no accreditation');
  } catch (e) {
    failed = true;
    if (e instanceof Missing) console.error(`FAIL record.fields: ${e.message}`);
    else console.error(`FAIL verify: ${e.message}`);
  }
  process.exit(failed ? 1 : 0);
}
