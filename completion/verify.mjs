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
 * person named in identity.claimed did any of it. Unsigned, attestation is
 * "this device only" and nothing checks the name. Signed, identity.signature
 * is an EIP-191 personal_sign signature by a wallet over this record's digest,
 * and the signer is RECOVERED here - with the sign-in page's own keccak and
 * secp256k1, imported from auth/recover.mjs, never a second copy - and must be
 * the address claimed. That proves the holder of a key signed this digest at
 * export: the identity of a key, not of a person. Nothing is on any chain.
 * The pass rule per seat is read from sims/registry/sims.json; that registry
 * scores per rubric axis and has no scalar threshold, so `passed` is taken
 * from the record and said so.
 *
 * THIS FILE ONLY RECOVERS. There is no signing routine in it and none is
 * imported: a verifier that could sign could forge.
 *
 * ONE CORE, TWO SHELLS. Every rule lives in completionCore(), between the
 * COMPLETION_CORE markers below. It is pure: it reads no file, no clock, no
 * storage and no network, and it is handed everything it needs - the parsed
 * registries (REGISTRY_FILES names them), a sha256 function and the
 * recoverAddress function. This file is the node shell: it reads the files,
 * supplies node's createHash and auth/recover.mjs's recoverAddress, and
 * prints. web/build_verify.py carries the marked block byte-for-byte into
 * web/trade_craft_verify.html, which supplies the same recovery (lifted from
 * the sign-in page) and the browser's crypto.subtle, so the page and this CLI
 * run the same rules. SHA-256 in a browser is async (crypto.subtle), so the
 * core's verify() takes a SYNCHRONOUS sha256 (string -> lowercase hex) and the
 * core also carries verifyAsync(record, subtle, recover), which computes the
 * one digest the rules ask for with subtle.digest first and then runs the
 * same synchronous verify(). node keeps a synchronous verify() for every
 * module that imports it.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { recoverAddress } from '../auth/recover.mjs';

const url = (p) => new URL(p, import.meta.url);
/* the registries the core reads, by the name the core asks for them */
export const REGISTRY_FILES = {
  completion: 'completion/registry/completion.json',
  lessons: 'lessons/registry/lessons.json',
  sims: 'sims/registry/sims.json',
  toolcribs: 'tools/registry/toolcribs.json',
  stations: 'stations/registry/stations.json',
  halls: 'pack/registry/halls.json',
  auth: 'auth/registry/auth.json',
};
const REGS = {};
for (const [k, rel] of Object.entries(REGISTRY_FILES)) REGS[k] = JSON.parse(readFileSync(url('../' + rel)));

/* COMPLETION_CORE:BEGIN - completionCore(regs) -> the verifier's rules, pure.
   regs: { completion, lessons, sims, toolcribs, stations, halls, auth } parsed
   from the files REGISTRY_FILES names. Throws at once if the registries
   disagree with each other. Returns { verify(record, sha256hex, recover),
   verifyAsync(record, subtle, recover), report(result), errorLine(e), ... }.
   sha256hex: (utf-8 string) -> 64 lowercase hex chars, synchronous.
   recover  : (message, 0x-hex sig) -> the signer's address; throws on a
              malformed signature. This block recovers; it never signs.
   No file, clock, storage, DOM or network is touched in here. */
function completionCore(regs) {
class Missing extends Error {}
function need(obj, key, who) {
  if (obj === null || typeof obj !== 'object' || !Object.prototype.hasOwnProperty.call(obj, key)) {
    throw new Missing(`${who} lacks ${JSON.stringify(key)}`);
  }
  return obj[key];
}

// canonical JSON: keys sorted recursively, no whitespace, UTF-8
function canonical(v) {
  if (Array.isArray(v)) return '[' + v.map(canonical).join(',') + ']';
  if (v !== null && typeof v === 'object') {
    return '{' + Object.keys(v).sort().map((k) => JSON.stringify(k) + ':' + canonical(v[k])).join(',') + '}';
  }
  return JSON.stringify(v);
}
// the digest input: every top-level field except digest, with
// identity.signature forced to null - the signature is made OVER the digest,
// after it, so it cannot be inside it. The exporter (web/build_progress.py)
// canonicalises the same way; completion.json#digest.over says so.
function digestBody(record) {
  const body = {};
  for (const k of Object.keys(record)) if (k !== 'digest') body[k] = record[k];
  if (body.identity !== null && typeof body.identity === 'object' && 'signature' in body.identity) {
    body.identity = { ...body.identity, signature: null };
  }
  return body;
}

// the exact string a wallet signs, fixed by structure: auth/'s own statement
// line, then this record's digest, then its export time. Rebuilt here from the
// record, never taken from it, so a signature over any other text is refused.
const reg = need(regs, 'completion', 'registries');
const lessonsReg = need(regs, 'lessons', 'registries');
const simsReg = need(regs, 'sims', 'registries');
const cribsReg = need(regs, 'toolcribs', 'registries');
const stationsReg = need(regs, 'stations', 'registries');
const hallsReg = need(regs, 'halls', 'registries');
const authReg = need(regs, 'auth', 'registries');
const SIG_RULE = need(reg, 'signature', 'completion.json');
const SIWE_STATEMENT = need(need(authReg, 'siwe', 'auth.json'), 'statement', 'auth.json#siwe');
if (need(need(SIG_RULE, 'message', 'completion.json#signature'), 'statement', 'completion.json#signature.message') !== SIWE_STATEMENT) {
  throw new Error('completion.json#signature.message.statement is not auth.json#siwe.statement; rebuild completion/');
}
const SIGNATURE_SCHEME = need(SIG_RULE, 'scheme', 'completion.json#signature');
const SIGNED_ATTESTATION = 'wallet signature over the digest';
const UNSIGNED_ATTESTATION = 'this device only';
function signatureMessage(digestHex, exportedAt) {
  if (typeof digestHex !== 'string' || typeof exportedAt !== 'string') throw new Missing('signatureMessage needs digest.hex and exported_at as strings');
  return SIWE_STATEMENT + '\ndigest: ' + digestHex + '\nexported_at: ' + exportedAt;
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

function verify(record, sha256hex, recoverAddress) {
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
  const attested = need(ident, 'attested_by', 'identity');
  check('record.fields', attested === UNSIGNED_ATTESTATION || attested === SIGNED_ATTESTATION,
    `identity.attested_by is neither "${UNSIGNED_ATTESTATION}" nor "${SIGNED_ATTESTATION}"`);
  const dig = need(record, 'digest', 'record');
  check('record.fields', need(dig, 'alg', 'digest') === 'SHA-256', 'digest.alg is not SHA-256');
  need(dig, 'over', 'digest');
  const hon = need(record, 'honesty', 'record');
  check('record.fields', Array.isArray(need(hon, 'proves', 'honesty')) && Array.isArray(need(hon, 'does_not_prove', 'honesty')),
    'honesty.proves / does_not_prove are not lists');

  // digest — integrity since export, not identity
  const hex = need(dig, 'hex', 'digest');
  check('digest', /^[0-9a-f]{64}$/.test(hex), 'digest.hex is not 64 hex chars');
  check('digest', sha256hex(canonical(digestBody(record))) === hex, 'digest does not recompute over the canonical record');

  // identity.signature — null is unsigned (this device only); an object is a
  // wallet's EIP-191 signature over THIS digest, and the signer is recovered
  // here rather than believed. The identity of a key, not of a person.
  const sig = need(ident, 'signature', 'identity');
  const signature = { state: 'unsigned', recovered: null, address: null, line: 'unsigned: ' + UNSIGNED_ATTESTATION };
  if (sig === null) {
    check('identity.signature', attested === UNSIGNED_ATTESTATION,
      `unsigned, so identity.attested_by must be "${UNSIGNED_ATTESTATION}", not ${JSON.stringify(attested)}`);
    if (attested !== UNSIGNED_ATTESTATION) { signature.state = 'invalid'; signature.line = 'unsigned, yet identity.attested_by claims a wallet signature: refused'; }
  } else if (sig === undefined || typeof sig !== 'object' || Array.isArray(sig)) {
    signature.state = 'invalid';
    signature.line = 'signature is not null and not an object: refused as a forgery';
    check('identity.signature', false, 'identity.signature is neither null nor a signature object; refused as a forgery');
  } else {
    signature.state = 'invalid';
    const scheme = need(sig, 'scheme', 'identity.signature');
    const address = need(sig, 'address', 'identity.signature');
    const message = need(sig, 'message', 'identity.signature');
    const sigHex = need(sig, 'sig', 'identity.signature');
    signature.address = address;
    check('identity.signature', scheme === SIGNATURE_SCHEME,
      `signature.scheme ${JSON.stringify(scheme)} is not ${SIGNATURE_SCHEME}; no other scheme is verified here`);
    check('identity.signature', attested === SIGNED_ATTESTATION,
      `signed, so identity.attested_by must be "${SIGNED_ATTESTATION}", not ${JSON.stringify(attested)}`);
    const wantMsg = signatureMessage(hex, need(record, 'exported_at', 'record'));
    check('identity.signature', message === wantMsg,
      'signature.message is not the structured message for THIS record (statement, digest.hex, exported_at); a signature over other text proves nothing about this record');
    check('identity.signature', typeof address === 'string' && /^0x[0-9a-fA-F]{40}$/.test(address),
      'signature.address is not 0x + 40 hex');
    check('identity.signature', typeof sigHex === 'string' && /^0x[0-9a-fA-F]{130}$/.test(sigHex),
      'signature.sig is not 0x + 65 bytes (r | s | v)');
    const claimed = need(ident, 'claimed', 'identity');
    check('identity.signature', typeof claimed === 'string' && typeof address === 'string' && claimed.toLowerCase() === address.toLowerCase(),
      `identity.claimed ${JSON.stringify(claimed)} is not signature.address ${JSON.stringify(address)} (compared as lowercase hex)`);
    if (scheme === SIGNATURE_SCHEME && typeof message === 'string' && typeof sigHex === 'string') {
      let recovered = null, why = null;
      try { recovered = recoverAddress(message, sigHex); } catch (e) { why = e.message; }
      signature.recovered = recovered;
      const match = recovered !== null && typeof address === 'string' && recovered.toLowerCase() === address.toLowerCase();
      check('identity.signature', match,
        recovered === null ? `the signature does not recover to any address: ${why}`
          : `the signature recovers to ${recovered}, not to the address claimed ${address} (compared as lowercase hex)`);
      if (match && tally['identity.signature'].fails.length === 0) {
        signature.state = 'signed';
        signature.line = `signed: ${SIGNATURE_SCHEME} by ${recovered}, recovered here from the signature over this digest - the identity of a key, not of a person; nothing is on any chain`;
      } else {
        signature.line = `signature refused: recovered ${recovered === null ? 'nothing' : recovered}, claimed ${address}`;
      }
    } else {
      signature.line = 'signature refused: not a ' + SIGNATURE_SCHEME + ' signature object';
    }
  }

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
        if (done === true && kind !== 'sim') {
          check('step.episode-evidence', need(rule, 'evidenceable', `evidence_rule.${kind}`) === true,
            `${lid} step ${n}: ${need(rule, 'evidenceable_why', `evidence_rule.${kind}`)}`);
        }
        if (done === true && ev !== null && typeof ev === 'object' && kind !== 'sim' && rule.evidenceable === true) {
          const epk = need(ev, 'episode', `${lid} step ${n} evidence`);
          check('step.episode-evidence', epk === kind, `${lid} step ${n}: evidence episode ${epk} is not a ${kind} episode`);
          const t = need(ev, 't', `${lid} step ${n} evidence`);
          check('step.episode-evidence', typeof t === 'string' && Number.isFinite(Date.parse(t)), `${lid} step ${n}: episode t ${JSON.stringify(t)} is not a parseable ISO-8601 string`);
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

  return { tally, notes, signature, summary: { nComplete, nFullyBacked, nEpisode, nDeviceMark, nSelfReported } };
}

// the browser's sha256 is async: compute the one digest verify() asks for
// with subtle.digest first, then run the same synchronous rules over it
async function verifyAsync(record, subtle, recoverAddress) {
  let body = null, digestHex = null;
  if (record !== null && typeof record === 'object') {
    body = canonical(digestBody(record));
    const bytes = new Uint8Array(await subtle.digest('SHA-256', new TextEncoder().encode(body)));
    digestHex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
  }
  return verify(record, (s) => {
    if (s !== body) throw new Error('verifyAsync: a digest was asked of a body it did not compute');
    return digestHex;
  }, recoverAddress);
}

const LAST_LINE = 'this verifies integrity since export and resolution against the bundle; a wallet signature, if any, proves '
  + 'that the holder of a key signed this digest at export - a key, not a person; nothing is written to any chain, '
  + 'nothing is anchored, and this is no accreditation';

// the lines the CLI prints for one result, in order; err marks stderr
function report(result) {
  const { tally, notes, signature, summary } = result;
  const lines = [];
  for (const [rule, t] of Object.entries(tally)) {
    const line = `${rule}: checked ${t.checked}, failing ${t.fails.length}`;
    if (t.fails.length) { lines.push({ err: true, text: `FAIL ${line}` }); for (const f of t.fails) lines.push({ err: true, text: `     ${f}` }); }
    else lines.push({ err: false, text: `ok ${line}` });
  }
  for (const n of notes) lines.push({ err: false, text: `note ${n}` });
  lines.push({ err: false, text: `signature: ${signature.line}` });
  lines.push({ err: false, text: `summary: ${summary.nComplete} lessons complete, of which ${summary.nFullyBacked} fully evidence-backed `
    + `(every step episode-backed); across them ${summary.nEpisode} episode-backed steps, `
    + `${summary.nDeviceMark} device-mark steps (station/crib: a device-local mark, not a recorded episode), `
    + `${summary.nSelfReported} self-reported steps counted as done` });
  lines.push({ err: false, text: LAST_LINE });
  return lines;
}
function failed(result) { return Object.values(result.tally).some((t) => t.fails.length > 0); }
// a thrown error, as the CLI names it: a missing field is record.fields
function errorLine(e) { return e instanceof Missing ? `FAIL record.fields: ${e.message}` : `FAIL verify: ${e.message}`; }

return { Missing, need, canonical, digestBody, signatureMessage, SIGNATURE_SCHEME, SIGNED_ATTESTATION, UNSIGNED_ATTESTATION,
  RULES, LAST_LINE, verify, verifyAsync, report, failed, errorLine };
}
/* COMPLETION_CORE:END */

const CORE = completionCore(REGS);
const sha256hex = (s) => createHash('sha256').update(Buffer.from(s, 'utf8')).digest('hex');
export const need = CORE.need;
export const canonical = CORE.canonical;
export const digestBody = CORE.digestBody;
export function digestOf(record) { return sha256hex(canonical(digestBody(record))); }
export const SIGNATURE_SCHEME = CORE.SIGNATURE_SCHEME;
export const SIGNED_ATTESTATION = CORE.SIGNED_ATTESTATION;
export const UNSIGNED_ATTESTATION = CORE.UNSIGNED_ATTESTATION;
export const signatureMessage = CORE.signatureMessage;
export const LAST_LINE = CORE.LAST_LINE;
export { completionCore };
/** the rules over one record, synchronous, with node's sha256 and the sign-in page's recovery */
export function verify(record) { return CORE.verify(record, sha256hex, recoverAddress); }

const isMain = process.argv[1] && new URL(`file://${process.argv[1]}`).pathname === new URL(import.meta.url).pathname;
if (isMain) {
  const path = process.argv[2];
  if (!path) { console.error('FAIL usage: node completion/verify.mjs <record.json>'); process.exit(1); }
  let failed = false;
  try {
    const record = JSON.parse(readFileSync(path, 'utf8'));
    const result = verify(record);
    failed = CORE.failed(result);
    for (const l of CORE.report(result)) (l.err ? console.error : console.log)(l.text);
  } catch (e) {
    failed = true;
    console.error(CORE.errorLine(e));
  }
  process.exit(failed ? 1 : 0);
}
