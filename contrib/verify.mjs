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
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { recoverAddress } from '../auth/recover.mjs';

const url = (p) => new URL(p, import.meta.url);
const reg = JSON.parse(readFileSync(url('./registry/contrib.json')));
const trainingReg = JSON.parse(readFileSync(url('../training/registry/training.json')));
const simsReg = JSON.parse(readFileSync(url('../sims/registry/sims.json')));
const hallsReg = JSON.parse(readFileSync(url('../pack/registry/halls.json')));
const campusesReg = JSON.parse(readFileSync(url('../unions/registry/campuses.json')));
const authReg = JSON.parse(readFileSync(url('../auth/registry/auth.json')));

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
// the digest input: every top-level field except digest, with
// contributor.signature forced to null - the signature is made OVER the
// digest, after it, so it cannot be inside it (contrib.json#digest.over)
export function digestBody(record) {
  const body = {};
  for (const k of Object.keys(record)) if (k !== 'digest') body[k] = record[k];
  if (body.contributor !== null && typeof body.contributor === 'object' && 'signature' in body.contributor) {
    body.contributor = { ...body.contributor, signature: null };
  }
  return body;
}
export function digestOf(record) {
  return createHash('sha256').update(Buffer.from(canonical(digestBody(record)), 'utf8')).digest('hex');
}

// the exact string a wallet signs, fixed by structure: auth/'s own statement
// line, this package's digest, its export time, its consent scope. Rebuilt
// here from the package, never taken from it.
const SIG_RULE = need(reg, 'signature', 'contrib.json');
const SIWE_STATEMENT = need(need(authReg, 'siwe', 'auth.json'), 'statement', 'auth.json#siwe');
if (need(need(SIG_RULE, 'message', 'contrib.json#signature'), 'statement', 'contrib.json#signature.message') !== SIWE_STATEMENT) {
  throw new Error('contrib.json#signature.message.statement is not auth.json#siwe.statement; rebuild contrib/');
}
export const SIGNATURE_SCHEME = need(SIG_RULE, 'scheme', 'contrib.json#signature');
export const SIGNED_ATTESTATION = 'wallet signature over the digest';
export const UNSIGNED_ATTESTATION = 'this device only';
export function signatureMessage(digestHex, exportedAt, scope) {
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
export const LAST_LINE = need(need(reg, 'verifier', 'contrib.json'), 'last_line', 'contrib.json#verifier');

export function verify(record) {
  const tally = {};
  for (const r of RULES) tally[r] = { checked: 0, fails: [] };
  const check = (rule, cond, msg) => { tally[rule].checked++; if (!cond) tally[rule].fails.push(msg); };
  const notes = [];

  // record.fields - fail closed on any missing field, anywhere
  const top = ['record', 'product', 'pack_version', 'exported_at', 'contributor', 'consent', 'dataset', 'honesty', 'digest'];
  for (const k of top) need(record, k, 'package');
  check('record.fields', need(record, 'record', 'package') === need(reg, 'record_tag', 'contrib.json'),
    `record is ${JSON.stringify(record.record)}, not ${reg.record_tag}`);
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
  check('digest', digestOf(record) === hex, 'digest does not recompute over the canonical package');

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
  const byKind = {}, sims = new Set();
  let traces = 0, samples = 0;
  for (const [i, ep] of (Array.isArray(episodes) ? episodes : []).entries()) {
    const w = `episode ${i}`;
    const kind = need(ep, 'kind', w);
    check('episode.kind', kind in EPISODE_KINDS, `${w}: kind ${JSON.stringify(kind)} is not in training.json#episode_kinds`);
    byKind[kind] = (kind in byKind ? byKind[kind] : 0) + 1;
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

const isMain = process.argv[1] && new URL(`file://${process.argv[1]}`).pathname === new URL(import.meta.url).pathname;
if (isMain) {
  const path = process.argv[2];
  if (!path) { console.error('FAIL usage: node contrib/verify.mjs <package.json>'); process.exit(1); }
  let failed = false;
  try {
    const record = JSON.parse(readFileSync(path, 'utf8'));
    const { tally, notes, signature, summary } = verify(record);
    for (const [rule, t] of Object.entries(tally)) {
      const line = `${rule}: checked ${t.checked}, failing ${t.fails.length}`;
      if (t.fails.length) { failed = true; console.error(`FAIL ${line}`); for (const f of t.fails) console.error(`     ${f}`); }
      else console.log(`ok ${line}`);
    }
    for (const n of notes) console.log(`note ${n}`);
    console.log(`signature: ${signature.line}`);
    const kinds = Object.keys(summary.byKind).sort().map((k) => `${k} ${summary.byKind[k]}`).join(', ');
    console.log(`summary: ${summary.episodes} episodes (${kinds === '' ? 'none' : kinds}), ${summary.traces} trace(s) attached `
      + `holding ${summary.samples} samples, ${summary.sims.length} sim(s) covered${summary.sims.length ? ' (' + summary.sims.join(', ') + ')' : ''}`);
    console.log(LAST_LINE);
  } catch (e) {
    failed = true;
    if (e instanceof Missing) console.error(`FAIL record.fields: ${e.message}`);
    else console.error(`FAIL verify: ${e.message}`);
  }
  process.exit(failed ? 1 : 0);
}
