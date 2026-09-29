#!/usr/bin/env node
/**
 * Contribution package verifier.
 *
 *   node contrib/verify.mjs <package.json>
 *
 * Re-checks one exported `tc-contribution/1` package against the registries
 * it names. Every rule prints one line, `ok <rule>` or `FAIL <rule>` at
 * column 0 (FAIL on stderr), and the process exits 1 on any failure.
 *
 * FAIL CLOSED. Every field is fetched through need(): a missing field is a
 * named failure, never a default. No nullish-coalescing default appears in
 * this file on purpose.
 *
 * TWO RECORD TAGS (wave 11). tc-contribution/1 is verified exactly as before.
 * tc-contribution/2 may also carry training.json#world_episode_kinds (the
 * robotics `world-teleop` samples, held to robotics/registry/robotics.json by
 * ids.env, world.samples and world.outcome), must state origin.classroom_mode
 * false (K-12 / classroom mode shares nothing), and passes the privacy rule:
 * no person, free-text, precise-location, audio, camera or biometric key at any
 * depth of any episode, no email-shaped or over-long string, and
 * contributor.claimed null or the signing wallet - never a typed label.
 *
 * WHAT A PASS MEANS. The package is internally consistent, its digest
 * recomputes, every episode has exactly the fields training/ declares for its
 * kind, every seat, scenario, hall and campus it names exists in this bundle,
 * a trace is within the cap, the consent scope is a non-empty subset of the
 * declared scopes under the one declared licence and statement, and the
 * counts it states about itself recompute. It does NOT mean the person named
 * in contributor.claimed recorded any of it. Unsigned, attestation is "this
 * device only" and nothing checks the label. Signed, contributor.signature is
 * an EIP-191 personal_sign by a wallet over this package's digest and consent
 * scope, and the signer is RECOVERED here - with the sign-in page's own
 * keccak and secp256k1, imported from auth/recover.mjs, never a second copy -
 * and must be the address claimed. That is the identity of a key, not of a
 * person. Nothing is on any chain, nothing was sent anywhere, and no agent or
 * robot learned from the package.
 *
 * THIS FILE ONLY RECOVERS. There is no signing routine in it and none is
 * imported: a verifier that could sign could forge.
 *
 * ONE CORE, TWO SHELLS. Every rule lives in contribCore(), between the
 * CONTRIB_CORE markers below: pure, handed the parsed registries
 * (REGISTRY_FILES names them), a synchronous sha256 and recoverAddress. This
 * file is the node shell (node's createHash, auth/recover.mjs's recovery,
 * console output). web/build_verify.py carries the marked block byte-for-byte
 * into web/trade_craft_verify.html, which passes crypto.subtle to the core's
 * verifyAsync() - it computes the one digest the rules ask for first, then
 * runs the same synchronous verify() - so the page and this CLI run the same
 * rules and print the same lines.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { recoverAddress } from '../auth/recover.mjs';

const url = (p) => new URL(p, import.meta.url);
/* the registries the core reads, by the name the core asks for them */
export const REGISTRY_FILES = {
  contrib: 'contrib/registry/contrib.json',
  training: 'training/registry/training.json',
  sims: 'sims/registry/sims.json',
  halls: 'pack/registry/halls.json',
  campuses: 'unions/registry/campuses.json',
  auth: 'auth/registry/auth.json',
  robotics: 'robotics/registry/robotics.json',
};
const REGS = {};
for (const [k, rel] of Object.entries(REGISTRY_FILES)) REGS[k] = JSON.parse(readFileSync(url('../' + rel)));

/* CONTRIB_CORE:BEGIN - contribCore(regs) -> the verifier's rules, pure.
   regs: { contrib, training, sims, halls, campuses, auth } parsed from the
   files REGISTRY_FILES names. Throws at once if contrib.json has drifted from
   training.json or auth.json. Returns { verify(record, sha256hex, recover),
   verifyAsync(record, subtle, recover), report(result), errorLine(e), ... }.
   sha256hex: (utf-8 string) -> 64 lowercase hex chars, synchronous.
   recover  : (message, 0x-hex sig) -> the signer's address; throws on a
              malformed signature. This block recovers; it never signs.
   No file, clock, storage, DOM or network is touched in here. */
function contribCore(regs) {
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
// contributor.signature forced to null - the signature is made OVER the
// digest, after it, so it cannot be inside it (contrib.json#digest.over)
function digestBody(record) {
  const body = {};
  for (const k of Object.keys(record)) if (k !== 'digest') body[k] = record[k];
  if (body.contributor !== null && typeof body.contributor === 'object' && 'signature' in body.contributor) {
    body.contributor = { ...body.contributor, signature: null };
  }
  return body;
}

// the exact string a wallet signs, fixed by structure: auth/'s own statement
// line, this package's digest, its export time, its consent scope. Rebuilt
// here from the package, never taken from it.
const reg = need(regs, 'contrib', 'registries');
const trainingReg = need(regs, 'training', 'registries');
const simsReg = need(regs, 'sims', 'registries');
const hallsReg = need(regs, 'halls', 'registries');
const campusesReg = need(regs, 'campuses', 'registries');
const authReg = need(regs, 'auth', 'registries');
const roboticsReg = need(regs, 'robotics', 'registries');
const SIG_RULE = need(reg, 'signature', 'contrib.json');
const SIWE_STATEMENT = need(need(authReg, 'siwe', 'auth.json'), 'statement', 'auth.json#siwe');
if (need(need(SIG_RULE, 'message', 'contrib.json#signature'), 'statement', 'contrib.json#signature.message') !== SIWE_STATEMENT) {
  throw new Error('contrib.json#signature.message.statement is not auth.json#siwe.statement; rebuild contrib/');
}
const SIGNATURE_SCHEME = need(SIG_RULE, 'scheme', 'contrib.json#signature');
const SIGNED_ATTESTATION = 'wallet signature over the digest';
const UNSIGNED_ATTESTATION = 'this device only';
function signatureMessage(digestHex, exportedAt, scope) {
  if (typeof digestHex !== 'string' || typeof exportedAt !== 'string' || !Array.isArray(scope)) {
    throw new Missing('signatureMessage needs digest.hex and exported_at as strings and consent.scope as a list');
  }
  return SIWE_STATEMENT + '\ndigest: ' + digestHex + '\nexported_at: ' + exportedAt + '\nconsent: ' + scope.join(',');
}

// the registries, read: the contract is DERIVED from training/ and the
// registry's copy is held to the source here, so a stale contrib.json fails
// loudly rather than verifying against an old shape
const EPISODE_KINDS = need(trainingReg, 'episode_kinds', 'training.json');
const REG_KINDS = need(reg, 'episode_kinds', 'contrib.json');
for (const k of Object.keys(EPISODE_KINDS)) {
  const want = JSON.stringify(need(EPISODE_KINDS[k], 'fields', `training.json#episode_kinds.${k}`));
  if (JSON.stringify(need(need(REG_KINDS, k, 'contrib.json#episode_kinds'), 'fields', `contrib.json#episode_kinds.${k}`)) !== want) {
    throw new Error(`contrib.json#episode_kinds.${k}.fields is not training.json's; rebuild contrib/`);
  }
}
const TRACE_RULE = need(reg, 'trace', 'contrib.json');
const TRACE_MAX = need(need(trainingReg, 'trace', 'training.json'), 'max_samples', 'training.json#trace');
if (need(TRACE_RULE, 'max_samples', 'contrib.json#trace') !== TRACE_MAX) throw new Error('contrib.json#trace.max_samples is not training.json\'s; rebuild contrib/');
const TRACE_SAMPLE_KEYS = need(TRACE_RULE, 'sample_keys', 'contrib.json#trace');
const OUTCOME_KEYS = need(TRACE_RULE, 'outcome_keys_always', 'contrib.json#trace');
const GAUGES_ENUMERATED = need(TRACE_RULE, 'gauge_fields_enumerated', 'contrib.json#trace');
const CONSENT_RULE = need(reg, 'consent', 'contrib.json');
const CONSENT_STATEMENT = need(CONSENT_RULE, 'statement', 'contrib.json#consent');
const SCOPES = Object.keys(need(CONSENT_RULE, 'scopes', 'contrib.json#consent'));
const LICENSE = need(need(CONSENT_RULE, 'license', 'contrib.json#consent'), 'spdx', 'contrib.json#consent.license');
const SIMS = need(simsReg, 'sims', 'sims.json');
const HALL_SLUGS = new Set(need(hallsReg, 'halls', 'halls.json').map((h) => need(h, 'slug', 'hall')));
const CAMPUS_IDS = new Set(Object.keys(need(campusesReg, 'campuses', 'campuses.json')));
const RULES = need(need(reg, 'verifier', 'contrib.json'), 'rules', 'contrib.json#verifier');
const LAST_LINE = need(need(reg, 'verifier', 'contrib.json'), 'last_line', 'contrib.json#verifier');
// tc-contribution/2: the world kinds, their envs, origin and privacy - the
// registry's copy is held to training.json and robotics.json here
const TAG_V1 = need(reg, 'record_tag', 'contrib.json');
const TAG_V2 = need(reg, 'record_tag_current', 'contrib.json');
if (!(TAG_V1 in need(reg, 'record_tags', 'contrib.json')) || !(TAG_V2 in reg.record_tags) || TAG_V1 === TAG_V2) throw new Error('contrib.json#record_tags does not name both record tags; rebuild contrib/');
const WORLD_KINDS = need(trainingReg, 'world_episode_kinds', 'training.json');
const REG_WORLD = need(reg, 'world_episode_kinds', 'contrib.json');
for (const k of Object.keys(WORLD_KINDS)) {
  if (JSON.stringify(need(need(REG_WORLD, k, 'contrib.json#world_episode_kinds'), 'fields', `contrib.json#world_episode_kinds.${k}`)) !== JSON.stringify(need(WORLD_KINDS[k], 'fields', `training.json#world_episode_kinds.${k}`))) {
    throw new Error(`contrib.json#world_episode_kinds.${k}.fields is not training.json's; rebuild contrib/`);
  }
}
if (Object.keys(REG_WORLD).length !== Object.keys(WORLD_KINDS).length) throw new Error('contrib.json#world_episode_kinds names a kind training.json does not; rebuild contrib/');
const WORLD_ENV_RULE = need(reg, 'world_envs', 'contrib.json');
const WORLD_ENVS = need(WORLD_ENV_RULE, 'envs', 'contrib.json#world_envs');
const POSE_LEN = need(WORLD_ENV_RULE, 'pose_len_by_medium', 'contrib.json#world_envs');
const ROBO_ENVS = need(roboticsReg, 'envs', 'robotics.json');
for (const e of Object.keys(WORLD_ENVS)) {
  const src = need(ROBO_ENVS, e, 'robotics.json#envs');
  if (JSON.stringify(need(src, 'embodiments', e)) !== JSON.stringify(need(WORLD_ENVS[e], 'embodiments', e))
      || JSON.stringify(need(src, 'action', e).fields.map((a) => a.name)) !== JSON.stringify(need(WORLD_ENVS[e], 'action_fields', e))) {
    throw new Error(`contrib.json#world_envs.${e} is not robotics.json's; rebuild contrib/`);
  }
}
const PRIV = need(reg, 'privacy', 'contrib.json');
const FORBIDDEN = new Map();
for (const [cls, keys] of Object.entries(need(PRIV, 'forbidden_keys', 'contrib.json#privacy'))) for (const k of keys) FORBIDDEN.set(k.toLowerCase(), cls);
const EMAIL_RE = new RegExp(need(PRIV, 'email_pattern', 'contrib.json#privacy'));
const FREE_TEXT_MAX = need(PRIV, 'free_text_max', 'contrib.json#privacy');
const FIELDS_V2 = {};
for (const k of Object.keys(EPISODE_KINDS)) FIELDS_V2[k] = EPISODE_KINDS[k].fields;
for (const k of Object.keys(WORLD_KINDS)) FIELDS_V2[k] = WORLD_KINDS[k].fields;
const isNum = (x) => typeof x === 'number' && Number.isFinite(x);
const isInt = (x) => Number.isInteger(x);
const ID_RE = /^[A-Za-z0-9][A-Za-z0-9._:\/-]{0,63}$/;
// every key and string at every depth of v: [path, key|null, value]
function walk(v, path, out) {
  if (Array.isArray(v)) { v.forEach((x, i) => walk(x, path + '[' + i + ']', out)); return out; }
  if (v !== null && typeof v === 'object') { for (const k of Object.keys(v)) { out.push([path + '.' + k, k, v[k]]); walk(v[k], path + '.' + k, out); } return out; }
  out.push([path, null, v]);
  return out;
}
// the privacy findings for one episode (a list of messages; empty is clean)
function privacyFindings(ep, w) {
  const found = [];
  for (const [path, key, val] of walk(ep, w, [])) {
    if (key !== null && FORBIDDEN.has(key.toLowerCase())) found.push(`${path}: key ${JSON.stringify(key)} is a ${FORBIDDEN.get(key.toLowerCase())} field; no such field is shared`);
    if (key !== null) continue;   // the value itself is visited once more, as a leaf
    if (typeof val === 'string' && EMAIL_RE.test(val)) found.push(`${path}: an email-shaped string; no such value is shared`);
    if (typeof val === 'string' && val.length > FREE_TEXT_MAX) found.push(`${path}: a ${val.length}-character string is free text (max ${FREE_TEXT_MAX}); no such value is shared`);
  }
  return found;
}

// one world episode (tc-contribution/2), held to training.json's field list
// and to the robokit env it names in robotics.json
function worldEpisode(ep, kind, w, check) {
  const want = need(WORLD_KINDS[kind], 'fields', kind);
  const spec = need(REG_WORLD, kind, 'contrib.json#world_episode_kinds');
  const have = Object.keys(ep);
  for (const f of have) check('episode.fields', want.includes(f), `${w} (${kind}): carries ${JSON.stringify(f)}, which a ${kind} episode does not record`);
  for (const f of want) check('episode.fields', have.includes(f), `${w} (${kind}): lacks ${JSON.stringify(f)}`);
  const t = need(ep, 't', w);
  check('episode.t', typeof t === 'string' && Number.isFinite(Date.parse(t)), `${w}: t ${JSON.stringify(t)} is not a parseable ISO-8601 string`);
  check('episode.fields', need(ep, 'v', w) === need(spec, 'v', kind), `${w}: v ${JSON.stringify(ep.v)} is not ${kind} version ${spec.v}`);
  check('episode.fields', need(ep, 'actor', w) in need(trainingReg, 'actors', 'training.json'), `${w}: actor ${JSON.stringify(ep.actor)} is not in training.json#actors`);
  const world = need(ep, 'world', w);
  check('episode.fields', typeof world === 'string' && ID_RE.test(world), `${w}: world ${JSON.stringify(world)} is not an id`);
  const envId = need(ep, 'env', w);
  const env = typeof envId === 'string' && Object.prototype.hasOwnProperty.call(WORLD_ENVS, envId) ? WORLD_ENVS[envId] : null;
  check('ids.env', env !== null, `${w}: env ${JSON.stringify(envId)} is not a robokit env in robotics.json`);
  const emb = need(ep, 'embodiment', w);
  if (env !== null) check('ids.env', env.embodiments.includes(emb), `${w}: embodiment ${JSON.stringify(emb)} is not one env ${envId} declares (${env.embodiments.join(', ')})`);
  const seed = need(ep, 'seed', w);
  check('world.samples', isInt(seed) && (env === null || env.seeds.includes(seed)), `${w}: seed ${JSON.stringify(seed)} is not one of the env's seeds${env !== null ? ' (' + env.seeds.join(', ') + ')' : ''}`);
  check('world.samples', need(ep, 'hz', w) === need(spec, 'sample_hz', kind) && need(ep, 'dt_s', w) === need(spec, 'dt_s', kind),
    `${w}: hz ${ep.hz} / dt_s ${ep.dt_s} are not training.json#world_teleop's ${spec.sample_hz} / ${spec.dt_s}`);
  const steps = need(ep, 'steps', w);
  check('world.samples', isInt(steps) && steps >= 0 && (env === null || env.cap_steps === null || steps <= env.cap_steps),
    `${w}: steps ${JSON.stringify(steps)} is not an integer within the env cap${env !== null ? ' ' + env.cap_steps : ''}`);
  const samples = need(ep, 'samples', w);
  const max = need(spec, 'max_samples', kind);
  check('world.samples', Array.isArray(samples) && samples.length <= max, `${w}: ${Array.isArray(samples) ? samples.length : 'no'} samples; training.json caps a ${kind} episode at ${max}`);
  const skeys = JSON.stringify([...need(spec, 'sample_keys', kind)].sort());
  const plen = env !== null ? need(POSE_LEN, env.medium, 'pose_len_by_medium') : null;
  let lastI = -1;
  for (const [j, s] of (Array.isArray(samples) ? samples : []).entries()) {
    const ks = s !== null && typeof s === 'object' && !Array.isArray(s) ? JSON.stringify(Object.keys(s).sort()) : null;
    check('world.samples', ks === skeys, `${w}: sample ${j} has keys ${ks}, not ${skeys}`);
    if (ks !== skeys) continue;
    check('world.samples', isInt(s.i) && s.i > lastI && (!isInt(steps) || s.i <= steps), `${w}: sample ${j} index ${JSON.stringify(s.i)} is not an increasing step index within steps`);
    lastI = isInt(s.i) ? s.i : lastI;
    check('world.samples', Array.isArray(s.pose) && s.pose.every(isNum) && (plen === null || s.pose.length === plen),
      `${w}: sample ${j} pose is not ${plen} finite numbers (env-local metres and radians)`);
    check('world.samples', Array.isArray(s.vel) && s.vel.length === 2 && s.vel.every(isNum), `${w}: sample ${j} vel is not [v, w] finite numbers`);
    check('world.samples', Array.isArray(s.near) && s.near.length <= 4 && s.near.every((x) => typeof x === 'string' && ID_RE.test(x)), `${w}: sample ${j} near is not at most 4 object ids`);
    check('world.samples', Array.isArray(s.a) && s.a.every(isNum) && (env === null || s.a.length === env.action_fields.length),
      `${w}: sample ${j} a is not ${env !== null ? env.action_fields.length : 'the env\'s'} finite action values (${env !== null ? env.action_fields.join(', ') : '?'})`);
  }
  const out = need(ep, 'outcome', w);
  const okeys = JSON.stringify([...need(spec, 'outcome_keys', kind)].sort());
  const oks = out !== null && typeof out === 'object' && !Array.isArray(out) ? JSON.stringify(Object.keys(out).sort()) : null;
  check('world.outcome', oks === okeys, `${w}: outcome keys ${oks} are not ${okeys}`);
  if (oks === okeys) {
    if (env !== null) check('world.outcome', env.termination.includes(out.done), `${w}: outcome.done ${JSON.stringify(out.done)} is not a termination id of ${envId} (${env.termination.join(', ')})`);
    check('world.outcome', typeof out.success === 'boolean' && isNum(out.return) && isInt(out.collected) && out.collected >= 0,
      `${w}: outcome success/return/collected are not bool / finite number / non-negative integer`);
    const terms = out.terms;
    check('world.outcome', terms !== null && typeof terms === 'object' && !Array.isArray(terms) && Object.values(terms).every(isNum)
      && (env === null || Object.keys(terms).every((k) => env.reward_terms.includes(k))),
      `${w}: outcome.terms ${JSON.stringify(terms)} names a term the env does not declare or a non-finite value`);
  }
}

function verify(record, sha256hex, recoverAddress) {
  const tally = {};
  for (const r of RULES) tally[r] = { checked: 0, fails: [] };
  const check = (rule, cond, msg) => { tally[rule].checked++; if (!cond) tally[rule].fails.push(msg); };
  const notes = [];

  // record.fields - fail closed on any missing field, anywhere
  const top = ['record', 'product', 'pack_version', 'exported_at', 'contributor', 'consent', 'dataset', 'honesty', 'digest'];
  for (const k of top) need(record, k, 'package');
  const tag = need(record, 'record', 'package');
  const v2 = tag === TAG_V2;
  check('record.fields', tag === TAG_V1 || v2,
    `record is ${JSON.stringify(record.record)}, not ${TAG_V1} or ${TAG_V2}`);
  if (v2) {
    // origin.classroom - K-12 / classroom mode shares nothing; /2 says which mode exported it
    const origin = need(record, 'origin', 'package');
    check('origin.classroom', origin !== null && typeof origin === 'object' && !Array.isArray(origin)
      && JSON.stringify(Object.keys(origin)) === '["classroom_mode"]' && need(origin, 'classroom_mode', 'origin') === false,
      `origin must be exactly {classroom_mode: false}: K-12 / classroom mode offers no sharing (got ${JSON.stringify(origin)})`);
  }
  check('record.fields', need(record, 'pack_version', 'package') === need(reg, 'pack_version', 'contrib.json'),
    `pack_version ${record.pack_version} is not this bundle's ${reg.pack_version}`);
  check('record.fields', need(record, 'product', 'package') === need(reg, 'product', 'contrib.json'),
    `product ${JSON.stringify(record.product)} is not this bundle's`);
  check('record.fields', typeof need(record, 'exported_at', 'package') === 'string', 'exported_at is not a string');
  const who = need(record, 'contributor', 'package');
  need(who, 'claimed', 'contributor');
  const attested = need(who, 'attested_by', 'contributor');
  check('record.fields', attested === UNSIGNED_ATTESTATION || attested === SIGNED_ATTESTATION,
    `contributor.attested_by is neither "${UNSIGNED_ATTESTATION}" nor "${SIGNED_ATTESTATION}"`);
  if (v2) {
    const cl = need(who, 'claimed', 'contributor');
    check('privacy', attested === UNSIGNED_ATTESTATION ? cl === null : (typeof cl === 'string' && /^0x[0-9a-fA-F]{40}$/.test(cl)),
      `contributor.claimed ${JSON.stringify(cl)} is a typed label; in ${TAG_V2} it is null (unsigned) or the signing wallet address, never a name`);
  }
  const dig = need(record, 'digest', 'package');
  check('record.fields', need(dig, 'alg', 'digest') === 'SHA-256', 'digest.alg is not SHA-256');
  need(dig, 'over', 'digest');
  const hon = need(record, 'honesty', 'package');
  check('record.fields', Array.isArray(need(hon, 'proves', 'honesty')) && Array.isArray(need(hon, 'does_not_prove', 'honesty')),
    'honesty.proves / does_not_prove are not lists');
  need(hon, 'nothing_sent', 'honesty'); need(hon, 'no_agent_trained', 'honesty');

  // digest - integrity since export, not identity
  const hex = need(dig, 'hex', 'digest');
  check('digest', /^[0-9a-f]{64}$/.test(hex), 'digest.hex is not 64 hex chars');
  check('digest', sha256hex(canonical(digestBody(record))) === hex, 'digest does not recompute over the canonical package');

  // consent - the fixed text, the one licence, a real subset of the scopes
  const consent = need(record, 'consent', 'package');
  check('consent.statement', need(consent, 'statement', 'consent') === CONSENT_STATEMENT,
    'consent.statement is not the registry\'s fixed statement; no other text is consent under this contract');
  const scope = need(consent, 'scope', 'consent');
  check('consent.scope', Array.isArray(scope) && scope.length > 0, 'consent.scope is empty or not a list: no scope, no consent');
  if (Array.isArray(scope)) {
    for (const s of scope) check('consent.scope', SCOPES.includes(s), `consent.scope names ${JSON.stringify(s)}, which this registry does not declare (${SCOPES.join(', ')})`);
    check('consent.scope', new Set(scope).size === scope.length, 'consent.scope lists a scope twice');
  }
  check('consent.license', need(consent, 'license', 'consent') === LICENSE,
    `consent.license ${JSON.stringify(consent.license)} is not the registry's ${LICENSE}; a licence is chosen once, never per package`);
  const granted = need(consent, 'granted_at', 'consent');
  check('consent.granted_at', typeof granted === 'string' && Number.isFinite(Date.parse(granted)),
    `consent.granted_at ${JSON.stringify(granted)} is not a parseable ISO-8601 string`);
  check('record.fields', need(consent, 'revocable', 'consent') === true, 'consent.revocable is not true; this contract has no irrevocable form');

  // contributor.signature - null is unsigned (this device only); an object is
  // a wallet's EIP-191 signature over THIS digest and scope, and the signer is
  // recovered here rather than believed. The identity of a key, not of a person.
  const sig = need(who, 'signature', 'contributor');
  const signature = { state: 'unsigned', recovered: null, address: null, line: 'unsigned: ' + UNSIGNED_ATTESTATION };
  if (sig === null) {
    check('contributor.signature', attested === UNSIGNED_ATTESTATION,
      `unsigned, so contributor.attested_by must be "${UNSIGNED_ATTESTATION}", not ${JSON.stringify(attested)}`);
    if (attested !== UNSIGNED_ATTESTATION) { signature.state = 'invalid'; signature.line = 'unsigned, yet contributor.attested_by claims a wallet signature: refused'; }
  } else if (typeof sig !== 'object' || Array.isArray(sig)) {
    signature.state = 'invalid';
    signature.line = 'signature is not null and not an object: refused as a forgery';
    check('contributor.signature', false, 'contributor.signature is neither null nor a signature object; refused as a forgery');
  } else {
    signature.state = 'invalid';
    const scheme = need(sig, 'scheme', 'contributor.signature');
    const address = need(sig, 'address', 'contributor.signature');
    const message = need(sig, 'message', 'contributor.signature');
    const sigHex = need(sig, 'sig', 'contributor.signature');
    signature.address = address;
    check('contributor.signature', scheme === SIGNATURE_SCHEME,
      `signature.scheme ${JSON.stringify(scheme)} is not ${SIGNATURE_SCHEME}; no other scheme is verified here`);
    check('contributor.signature', attested === SIGNED_ATTESTATION,
      `signed, so contributor.attested_by must be "${SIGNED_ATTESTATION}", not ${JSON.stringify(attested)}`);
    const wantMsg = Array.isArray(scope) ? signatureMessage(hex, need(record, 'exported_at', 'package'), scope) : null;
    check('contributor.signature', message === wantMsg,
      'signature.message is not the structured message for THIS package (statement, digest.hex, exported_at, consent scope); a signature over other text proves nothing about this package');
    check('contributor.signature', typeof address === 'string' && /^0x[0-9a-fA-F]{40}$/.test(address), 'signature.address is not 0x + 40 hex');
    check('contributor.signature', typeof sigHex === 'string' && /^0x[0-9a-fA-F]{130}$/.test(sigHex), 'signature.sig is not 0x + 65 bytes (r | s | v)');
    const claimed = need(who, 'claimed', 'contributor');
    check('contributor.signature', typeof claimed === 'string' && typeof address === 'string' && claimed.toLowerCase() === address.toLowerCase(),
      `contributor.claimed ${JSON.stringify(claimed)} is not signature.address ${JSON.stringify(address)} (compared as lowercase hex)`);
    if (scheme === SIGNATURE_SCHEME && typeof message === 'string' && typeof sigHex === 'string') {
      let recovered = null, why = null;
      try { recovered = recoverAddress(message, sigHex); } catch (e) { why = e.message; }
      signature.recovered = recovered;
      const match = recovered !== null && typeof address === 'string' && recovered.toLowerCase() === address.toLowerCase();
      check('contributor.signature', match,
        recovered === null ? `the signature does not recover to any address: ${why}`
          : `the signature recovers to ${recovered}, not to the address claimed ${address} (compared as lowercase hex)`);
      if (match && tally['contributor.signature'].fails.length === 0) {
        signature.state = 'signed';
        signature.line = `signed: ${SIGNATURE_SCHEME} by ${recovered}, recovered here from the signature over this digest and consent scope - the identity of a key, not of a person; nothing is on any chain`;
      } else {
        signature.line = `signature refused: recovered ${recovered === null ? 'nothing' : recovered}, claimed ${address}`;
      }
    } else {
      signature.line = 'signature refused: not a ' + SIGNATURE_SCHEME + ' signature object';
    }
  }

  // dataset - every episode held to training/'s shape and to the bundle's ids
  const ds = need(record, 'dataset', 'package');
  const episodes = need(ds, 'episodes', 'dataset');
  check('record.fields', Array.isArray(episodes), 'dataset.episodes is not a list');
  const fieldsByKind = need(ds, 'fields_by_kind', 'dataset');
  for (const k of Object.keys(EPISODE_KINDS)) {
    check('episode.fields', JSON.stringify(need(fieldsByKind, k, 'dataset.fields_by_kind')) === JSON.stringify(EPISODE_KINDS[k].fields),
      `dataset.fields_by_kind.${k} is not training.json#episode_kinds.${k}.fields`);
  }
  if (v2) {
    check('episode.fields', JSON.stringify(Object.keys(fieldsByKind).sort()) === JSON.stringify(Object.keys(FIELDS_V2).sort())
      && Object.keys(WORLD_KINDS).every((k) => JSON.stringify(fieldsByKind[k]) === JSON.stringify(FIELDS_V2[k])),
      `dataset.fields_by_kind names ${JSON.stringify(Object.keys(fieldsByKind).sort())}; a ${TAG_V2} package lists every kind of training.json#episode_kinds and #world_episode_kinds with its fields`);
  }
  const byKind = {}, sims = new Set();
  let traces = 0, samples = 0;
  for (const [i, ep] of (Array.isArray(episodes) ? episodes : []).entries()) {
    const w = `episode ${i}`;
    const kind = need(ep, 'kind', w);
    const isWorld = v2 && typeof kind === 'string' && kind in WORLD_KINDS;
    check('episode.kind', kind in EPISODE_KINDS || isWorld, `${w}: kind ${JSON.stringify(kind)} is not in training.json#episode_kinds${v2 ? ' or #world_episode_kinds' : ''}`);
    byKind[kind] = (kind in byKind ? byKind[kind] : 0) + 1;
    if (v2) for (const f of privacyFindings(ep, w)) check('privacy', false, f);
    if (isWorld) { worldEpisode(ep, kind, w, check); continue; }
    if (!(kind in EPISODE_KINDS)) continue;
    const want = EPISODE_KINDS[kind].fields;
    const conditional = need(REG_KINDS[kind], 'conditional_fields', `contrib.json#episode_kinds.${kind}`);
    const have = Object.keys(ep);
    for (const f of have) check('episode.fields', want.includes(f), `${w} (${kind}): carries ${JSON.stringify(f)}, which a ${kind} episode does not record`);
    for (const f of want) {
      if (f in conditional) {
        const onlyActor = need(need(conditional[f], 'present_only_when', `conditional ${f}`), 'actor', `conditional ${f}`);
        const actor = 'actor' in ep ? ep.actor : null;
        check('episode.fields', (actor === onlyActor) === have.includes(f),
          `${w} (${kind}): ${JSON.stringify(f)} must be present exactly when actor is ${onlyActor} (actor is ${JSON.stringify(actor)}, field ${have.includes(f) ? 'present' : 'absent'})`);
      } else {
        check('episode.fields', have.includes(f), `${w} (${kind}): lacks ${JSON.stringify(f)}`);
      }
    }
    const t = need(ep, 't', w);
    check('episode.t', typeof t === 'string' && Number.isFinite(Date.parse(t)), `${w}: t ${JSON.stringify(t)} is not a parseable ISO-8601 string`);
    if (want.includes('campus')) { const c = need(ep, 'campus', w); check('ids.campus', CAMPUS_IDS.has(c), `${w}: campus ${JSON.stringify(c)} is not in campuses.json`); }
    if (want.includes('hall')) { const h = need(ep, 'hall', w); check('ids.hall', HALL_SLUGS.has(h), `${w}: hall ${JSON.stringify(h)} is not in halls.json`); }
    if (want.includes('sim')) {
      const s = need(ep, 'sim', w);
      check('ids.sim', typeof s === 'string' && s in SIMS, `${w}: sim ${JSON.stringify(s)} is not in sims.json`);
      if (typeof s === 'string') sims.add(s);
      if (want.includes('scenario') && typeof s === 'string' && s in SIMS) {
        const sc = need(ep, 'scenario', w);
        check('ids.scenario', sc === null || SIMS[s].scenarios.some((x) => x.id === sc),
          `${w}: scenario ${JSON.stringify(sc)} is not a scenario of seat ${s} (null is allowed: no scenario chosen)`);
      }
    }
    if (kind === 'sim') {
      const actor = need(ep, 'actor', w);
      check('episode.fields', actor in need(trainingReg, 'actors', 'training.json'), `${w}: actor ${JSON.stringify(actor)} is not in training.json#actors`);
      const outcome = need(ep, 'outcome', w);
      for (const k of OUTCOME_KEYS) need(outcome, k, `${w} outcome`);
      if ('trace' in outcome) {
        traces++;
        const tr = outcome.trace;
        check('trace', Array.isArray(tr) && tr.length <= TRACE_MAX, `${w}: trace has ${Array.isArray(tr) ? tr.length : 'no'} samples; training.json caps it at ${TRACE_MAX}`);
        if (Array.isArray(tr)) {
          samples += tr.length;
          for (const [j, smp] of tr.entries()) {
            const keys = smp !== null && typeof smp === 'object' ? Object.keys(smp).sort() : null;
            check('trace', keys !== null && JSON.stringify(keys) === JSON.stringify([...TRACE_SAMPLE_KEYS].sort()),
              `${w}: trace sample ${j} has keys ${JSON.stringify(keys)}, not ${JSON.stringify(TRACE_SAMPLE_KEYS)}`);
          }
        }
      }
    }
  }
  if (GAUGES_ENUMERATED !== true && traces > 0) {
    notes.push('trace: training.json enumerates no gauge field names (gauges() is described, not listed), so each trace is held to its sample count and sample keys only; nothing inside gauges is checked');
  }
  // dataset.counts - what the package says about itself recomputes
  check('dataset.counts', need(ds, 'traces_attached', 'dataset') === traces, `dataset.traces_attached is ${ds.traces_attached}, recomputed ${traces}`);
  check('dataset.counts', JSON.stringify(need(ds, 'episode_counts_by_kind', 'dataset')) === JSON.stringify(Object.fromEntries(Object.keys(byKind).sort().map((k) => [k, byKind[k]]))),
    `dataset.episode_counts_by_kind ${JSON.stringify(ds.episode_counts_by_kind)} does not recompute (${JSON.stringify(byKind)})`);
  check('dataset.counts', JSON.stringify(need(ds, 'sims_covered', 'dataset')) === JSON.stringify([...sims].sort()),
    `dataset.sims_covered ${JSON.stringify(ds.sims_covered)} does not recompute (${JSON.stringify([...sims].sort())})`);

  return { tally, notes, signature, summary: { byKind, traces, sims: [...sims].sort(), samples, episodes: Array.isArray(episodes) ? episodes.length : 0 } };
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
  const kinds = Object.keys(summary.byKind).sort().map((k) => `${k} ${summary.byKind[k]}`).join(', ');
  lines.push({ err: false, text: `summary: ${summary.episodes} episodes (${kinds === '' ? 'none' : kinds}), ${summary.traces} trace(s) attached `
    + `holding ${summary.samples} samples, ${summary.sims.length} sim(s) covered${summary.sims.length ? ' (' + summary.sims.join(', ') + ')' : ''}` });
  lines.push({ err: false, text: LAST_LINE });
  return lines;
}
function failed(result) { return Object.values(result.tally).some((t) => t.fails.length > 0); }
// a thrown error, as the CLI names it: a missing field is record.fields
function errorLine(e) { return e instanceof Missing ? `FAIL record.fields: ${e.message}` : `FAIL verify: ${e.message}`; }

return { Missing, need, canonical, digestBody, signatureMessage, SIGNATURE_SCHEME, SIGNED_ATTESTATION, UNSIGNED_ATTESTATION,
  RULES, LAST_LINE, verify, verifyAsync, report, failed, errorLine };
}
/* CONTRIB_CORE:END */

const CORE = contribCore(REGS);
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
export { contribCore };
/** the rules over one package, synchronous, with node's sha256 and the sign-in page's recovery */
export function verify(record) { return CORE.verify(record, sha256hex, recoverAddress); }

const isMain = process.argv[1] && new URL(`file://${process.argv[1]}`).pathname === new URL(import.meta.url).pathname;
if (isMain) {
  const path = process.argv[2];
  if (!path) { console.error('FAIL usage: node contrib/verify.mjs <package.json>'); process.exit(1); }
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
