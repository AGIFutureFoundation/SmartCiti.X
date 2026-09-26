#!/usr/bin/env python3
"""The contribute page: share this device's training log as a package, on purpose.

WHY THIS FILE EXISTS. The 3D page records episodes under `tc-training`
(opt-in) and, with TRACE on, a coarse gauge sample of a running sim; the
progress page carries a completion record off the device. Nothing let a
learner SHARE the training log as training data for agents or robots with a
consent they ticked, a scope, a fixed licence, a digest and - only when the
sign-in page holds a wallet - a signature, in a file `contrib/verify.mjs`
can check. This page does that and nothing more.

WHAT THE PAGE WILL NOT DO, which is the point of it.

  - It will not upload anything. There is no endpoint, no fetch, no form
    action. The export is a download to the learner's own machine; the
    learner keeps the file and hands it on, or does not.
  - It will not name a destination this bundle cannot reach. The section
    "Where this could go" lists whatever `protocols/registry/protocols.json`
    names at build time - nothing when it is absent - and says on every row:
    not integrated, not validated, nothing sent by this bundle. No platform
    name is typed here.
  - It will not fabricate consent, a licence or a signature. The statement
    and the licence are the contrib registry's, once; the scope is what the
    learner ticked; the signature is what a wallet returned, or null.
  - It will not claim an agent or robot learned anything. training/ says so
    and the package carries that sentence.

ONE TRUTH PER FACT. Every constant is read from the registry that owns it;
a missing field fails the build by name through `need()`; there is no
`.get(k, default)` and no `??` in this file.
"""
import html
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402


def _root():
    for cand in (HERE, *HERE.parents):
        if (cand / 'pack').is_dir() and (cand / 'contrib').is_dir() and (cand / 'auth').is_dir():
            return cand
    raise RuntimeError('cannot locate the packs from ' + str(HERE))


ROOT = _root()

CONTRIB_PATH = 'contrib/registry/contrib.json'
TRAINING_PATH = 'training/registry/training.json'
AUTH_PATH = 'auth/registry/auth.json'
MANIFEST_PATH = 'pack/manifest.json'
PROTOCOLS_PATH = 'protocols/registry/protocols.json'


def need(d, k, where):
    """Read a required field, or fail by name."""
    if not isinstance(d, dict):
        raise TypeError(f'{where}: expected an object to read {k!r} from, got {type(d).__name__}')
    if k not in d:
        raise KeyError(f'{where}: required field {k!r} is missing')
    return d[k]


def load(rel):
    return json.load(open(ROOT / rel))


contrib_reg = load(CONTRIB_PATH)
training_reg = load(TRAINING_PATH)
auth_reg = load(AUTH_PATH)
manifest = load(MANIFEST_PATH)

PACK_VERSION = need(manifest, 'pack_version', MANIFEST_PATH)
PRODUCT = need(manifest, 'product', MANIFEST_PATH)
for rel, reg in ((CONTRIB_PATH, contrib_reg), (TRAINING_PATH, training_reg), (AUTH_PATH, auth_reg)):
    if need(reg, 'pack_version', rel) != PACK_VERSION:
        raise AssertionError(f'{rel}: pack_version disagrees with {MANIFEST_PATH}')
if need(contrib_reg, 'product', CONTRIB_PATH) != PRODUCT:
    raise AssertionError(f'{CONTRIB_PATH}: product disagrees with {MANIFEST_PATH}')
BUILT = need(contrib_reg, 'built', CONTRIB_PATH)
TITLE = PRODUCT.split('(')[0].strip()

RECORD_TAG = need(contrib_reg, 'record_tag', CONTRIB_PATH)
CONSENT = need(contrib_reg, 'consent', CONTRIB_PATH)
CONSENT_STATEMENT = need(CONSENT, 'statement', CONTRIB_PATH + '#consent')
SCOPES = need(CONSENT, 'scopes', CONTRIB_PATH + '#consent')
LICENSE = need(CONSENT, 'license', CONTRIB_PATH + '#consent')
LICENSE_SPDX = need(LICENSE, 'spdx', CONTRIB_PATH + '#consent.license')
LICENSE_NAME = need(LICENSE, 'name', CONTRIB_PATH + '#consent.license')
LICENSE_WHY = need(LICENSE, 'why', CONTRIB_PATH + '#consent.license')
REVOCABLE_MEANS = need(CONSENT, 'revocable_means', CONTRIB_PATH + '#consent')
if need(CONSENT, 'revocable', CONTRIB_PATH + '#consent') is not True:
    raise AssertionError(f'{CONTRIB_PATH}#consent.revocable is not true; this page has no irrevocable form')
EPISODE_KINDS = need(contrib_reg, 'episode_kinds', CONTRIB_PATH)
TRAINING_KINDS = need(training_reg, 'episode_kinds', TRAINING_PATH)
for k in TRAINING_KINDS:
    if need(need(EPISODE_KINDS, k, CONTRIB_PATH + '#episode_kinds'), 'fields', f'{CONTRIB_PATH}#episode_kinds.{k}') \
            != need(TRAINING_KINDS[k], 'fields', f'{TRAINING_PATH}#episode_kinds.{k}'):
        raise AssertionError(f'{CONTRIB_PATH}#episode_kinds.{k}.fields drifted from {TRAINING_PATH}; run python3 contrib/build.py')
FIELDS_BY_KIND = {k: need(EPISODE_KINDS[k], 'fields', k) for k in EPISODE_KINDS}
TRACE_RULE = need(contrib_reg, 'trace', CONTRIB_PATH)
TRACE_MAX = need(TRACE_RULE, 'max_samples', CONTRIB_PATH + '#trace')
if TRACE_MAX != need(need(training_reg, 'trace', TRAINING_PATH), 'max_samples', TRAINING_PATH + '#trace'):
    raise AssertionError(f'{CONTRIB_PATH}#trace.max_samples drifted from {TRAINING_PATH}')
HONESTY = need(contrib_reg, 'honesty', CONTRIB_PATH)
DIGEST_RULE = need(contrib_reg, 'digest', CONTRIB_PATH)
SIG_RULE = need(contrib_reg, 'signature', CONTRIB_PATH)
SIGNATURE_SCHEME = need(SIG_RULE, 'scheme', CONTRIB_PATH + '#signature')
TRAINING_SOURCE = need(contrib_reg, 'training_source', CONTRIB_PATH)
TRAINING_KEY = need(TRAINING_SOURCE, 'key', CONTRIB_PATH + '#training_source')
NO_AGENT = need(HONESTY, 'no_agent_trained', CONTRIB_PATH + '#honesty')
NOTHING_SENT = need(HONESTY, 'nothing_sent', CONTRIB_PATH + '#honesty')
VERIFIER = need(contrib_reg, 'verifier', CONTRIB_PATH)
LAST_LINE = need(VERIFIER, 'last_line', CONTRIB_PATH + '#verifier')
DESTINATIONS_RULE = need(contrib_reg, 'destinations', CONTRIB_PATH)

# auth/: the identity key, the wallet method and the statement a wallet signs
AUTH_STORAGE = need(auth_reg, 'storage', AUTH_PATH)
IDENTITY_KEY = need(AUTH_STORAGE, 'identity_key', AUTH_PATH + '#storage')
AUTH_RECORDS = need(auth_reg, 'records_named', AUTH_PATH)
if need(AUTH_RECORDS, 'training_key', AUTH_PATH + '#records_named') != TRAINING_KEY:
    raise AssertionError(f'{AUTH_PATH}#records_named.training_key is not {TRAINING_KEY}')
if need(need(training_reg, 'storage', TRAINING_PATH), 'key', TRAINING_PATH + '#storage') != TRAINING_KEY:
    raise AssertionError(f'{TRAINING_PATH}#storage.key is not {TRAINING_KEY}')
SIWE_STATEMENT = need(need(auth_reg, 'siwe', AUTH_PATH), 'statement', AUTH_PATH + '#siwe')
if need(need(SIG_RULE, 'message', CONTRIB_PATH + '#signature'), 'statement', CONTRIB_PATH + '#signature.message') != SIWE_STATEMENT:
    raise AssertionError(f'{CONTRIB_PATH}#signature.message.statement is not {AUTH_PATH}#siwe.statement')
AUTH_METHODS = need(auth_reg, 'methods', AUTH_PATH)
WALLET_METHOD = 'siwe-ethereum'
if WALLET_METHOD not in AUTH_METHODS:
    raise KeyError(f'{AUTH_PATH}#methods does not name {WALLET_METHOD!r}; this page cannot offer a wallet signature')
if 'address' not in need(AUTH_STORAGE, 'record_shape', AUTH_PATH + '#storage'):
    raise AssertionError(f'{AUTH_PATH}#storage.record_shape stores no address for a wallet identity')
WALLET_LABEL = need(AUTH_METHODS[WALLET_METHOD], 'label', f'{AUTH_PATH}#methods.{WALLET_METHOD}')
IDENTITY_RULE = need(need(auth_reg, 'honesty', AUTH_PATH), 'local_identity_is_a_label', AUTH_PATH + '#honesty')
SIGNING = {
    'scheme': SIGNATURE_SCHEME,
    'statement': SIWE_STATEMENT,
    'attested_signed': 'wallet signature over the digest',
    'attested_unsigned': 'this device only',
    'wallet_method': WALLET_METHOD,
}


# ------------------------------------------------------------ destinations
# The agent-protocol destinations another pack names, if it exists at build
# time. Read, never typed: with no registry the list is empty and the page
# says no destination is configured. Every row carries the same three words
# whatever the registry says about it, because this bundle reaches none.
def destinations_from(path):
    if not (ROOT / path).is_file():
        return [], 'absent'
    reg = json.load(open(ROOT / path))
    rows = []
    listing = None
    for key in ('destinations', 'protocols'):
        if key in reg:
            listing = reg[key]
            break
    if listing is None:
        return [], 'present but names no destinations or protocols list this builder reads'
    entries = listing.items() if isinstance(listing, dict) else [(None, e) for e in listing]
    for k, entry in entries:
        if not isinstance(entry, dict):
            continue
        pid = entry['id'] if 'id' in entry and isinstance(entry['id'], str) else k
        if not isinstance(pid, str):
            continue
        name = entry['name'] if 'name' in entry and isinstance(entry['name'], str) else pid
        what = ''
        for wk in ('what_it_is', 'what'):
            if wk in entry and isinstance(entry[wk], str):
                what = entry[wk]
                break
        # a registry row that claimed integration would make this page's three
        # words a lie; the build stops by name rather than print them
        for flag in ('integrated', 'validated_against_spec', 'configured'):
            if flag in entry and entry[flag] is True:
                raise AssertionError(f'{path}#{pid}.{flag} is true, but this page reaches no destination; '
                                     'a contribution page that named an integrated destination would have to send, and this one does not')
        rows.append({'id': pid, 'name': name, 'what': what})
    return rows, 'present'


DESTINATIONS, PROTOCOLS_STATE = destinations_from(PROTOCOLS_PATH)
NOT_REACHED = ('not integrated', 'not validated', 'nothing sent by this bundle')

E = html.escape
F = lambda x: f'{x:,}'

PAYLOAD = json.dumps({
    'product': PRODUCT,
    'pack_version': PACK_VERSION,
    'record_tag': RECORD_TAG,
    'keys': {'training': TRAINING_KEY, 'identity': IDENTITY_KEY},
    'consent': {'statement': CONSENT_STATEMENT, 'scopes': sorted(SCOPES.keys()), 'license': LICENSE_SPDX,
                'revocable': True},
    'fields_by_kind': FIELDS_BY_KIND,
    'trace_max_samples': TRACE_MAX,
    'digest_over': need(DIGEST_RULE, 'over', CONTRIB_PATH + '#digest'),
    'honesty': {'proves': need(HONESTY, 'proves', CONTRIB_PATH + '#honesty'),
                'does_not_prove': need(HONESTY, 'does_not_prove', CONTRIB_PATH + '#honesty'),
                'nothing_sent': NOTHING_SENT, 'no_agent_trained': NO_AGENT},
    'signing': SIGNING,
    'destinations': DESTINATIONS,
    'protocols_state': PROTOCOLS_STATE,
}, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')

# ----------------------------------------------------- the package builder
# One pure function builds the package a learner can carry off this device.
# It is a classic script in its own <script id="contrib-js"> block so that
# web/test_contribute.mjs can lift it out of the built page and run it in
# node over a synthetic training log. Nothing in it reads the DOM or storage.
CONTRIB_JS = r"""
/* CONTRIB:BEGIN - buildContribution(training, identity, consent, meta, now)
   training : the parsed tc-training array, verbatim (an array of objects, or the build refuses)
   identity : the parsed tc-identity record, or null when absent/blocked/unreadable
   consent  : { scope: [scopes ticked], granted_at: ISO string }
   meta     : { product, pack_version, record_tag, consent: {statement, scopes, license}, fields_by_kind,
                honesty: {proves, does_not_prove, nothing_sent, no_agent_trained}, wallet? }
              wallet: the address a wallet will sign with; then contributor.claimed is that address,
              attested_by names the wallet, and the package is NOT valid until attachSignature fills
              contributor.signature with what the wallet returned
   now      : a Date
   Returns a Promise of the package, digest stamped. Pure: same inputs, same bytes. */
const SIGNED_ATTESTATION = 'wallet signature over the digest';
const UNSIGNED_ATTESTATION = 'this device only';

function canonicalJSON(v) {
  if (v === null || typeof v === 'number' || typeof v === 'boolean' || typeof v === 'string') {
    if (typeof v === 'number' && !isFinite(v)) throw new Error('contrib: a non-finite number cannot be canonical');
    return JSON.stringify(v);
  }
  if (Array.isArray(v)) return '[' + v.map(canonicalJSON).join(',') + ']';
  if (typeof v === 'object') {
    return '{' + Object.keys(v).sort().map((k) => JSON.stringify(k) + ':' + canonicalJSON(v[k])).join(',') + '}';
  }
  throw new Error('contrib: a ' + typeof v + ' cannot be canonical');
}
/* the digest input: every top-level field except digest, with
   contributor.signature forced to null - the signature is made OVER the
   digest, after it, so it cannot be inside it (contrib/registry/contrib.json#digest) */
function digestBody(record) {
  const body = {};
  for (const k of Object.keys(record)) if (k !== 'digest') body[k] = record[k];
  if (body.contributor && typeof body.contributor === 'object') body.contributor = { ...body.contributor, signature: null };
  return body;
}
/* the exact string a wallet signs, fixed by structure: auth/'s statement line,
   this package's digest, its export time, its consent scope. contrib/verify.mjs rebuilds it. */
function signatureMessage(record, statement) {
  if (typeof statement !== 'string' || statement === '') throw new Error('contrib: no statement to sign; auth/registry/auth.json#siwe.statement is the one');
  if (!record || !record.digest || typeof record.digest.hex !== 'string' || typeof record.exported_at !== 'string'
      || !record.consent || !Array.isArray(record.consent.scope)) throw new Error('contrib: a package must carry digest.hex, exported_at and consent.scope before it can be signed');
  return statement + '\ndigest: ' + record.digest.hex + '\nexported_at: ' + record.exported_at + '\nconsent: ' + record.consent.scope.join(',');
}
/* fills contributor.signature with what a wallet RETURNED. It checks shape and
   that the package was built for this address; it computes nothing and it
   never invents a signature: with no wallet there is nothing to call it with. */
function attachSignature(record, address, sig, signing) {
  if (!signing || typeof signing.scheme !== 'string' || typeof signing.statement !== 'string') throw new Error('contrib: attachSignature needs the signing contract (scheme, statement)');
  if (typeof address !== 'string' || !/^0x[0-9a-fA-F]{40}$/.test(address)) throw new Error('contrib: not an address: ' + String(address));
  if (typeof sig !== 'string' || !/^0x[0-9a-fA-F]{130}$/.test(sig)) throw new Error('contrib: the wallet did not return a 65-byte signature; nothing attached');
  if (!record || !record.contributor || record.contributor.signature !== null) throw new Error('contrib: the package already carries a signature, or has no contributor');
  if (record.contributor.attested_by !== SIGNED_ATTESTATION || typeof record.contributor.claimed !== 'string'
      || record.contributor.claimed.toLowerCase() !== address.toLowerCase()) {
    throw new Error('contrib: the package was not built for the wallet ' + address + '; build it with meta.wallet first so the digest covers the claim');
  }
  return { ...record, contributor: { ...record.contributor,
    signature: { scheme: signing.scheme, address, message: signatureMessage(record, signing.statement), sig } } };
}

/* the counts a package states about itself, recomputed from its episodes -
   the verifier recomputes them the same way and refuses a drift */
function countEpisodes(episodes) {
  const byKind = {}, sims = new Set();
  let traces = 0, samples = 0;
  for (const ep of episodes) {
    const k = typeof ep.kind === 'string' ? ep.kind : '(no kind)';
    byKind[k] = (k in byKind ? byKind[k] : 0) + 1;
    if (typeof ep.sim === 'string') sims.add(ep.sim);
    if (ep.kind === 'sim' && ep.outcome && typeof ep.outcome === 'object' && Array.isArray(ep.outcome.trace)) { traces++; samples += ep.outcome.trace.length; }
  }
  const sorted = {};
  for (const k of Object.keys(byKind).sort()) sorted[k] = byKind[k];
  return { episode_counts_by_kind: sorted, traces_attached: traces, sims_covered: [...sims].sort(), samples };
}

async function buildContribution(training, identity, consent, meta, now) {
  if (!Array.isArray(training) || !training.every((e) => e !== null && typeof e === 'object' && !Array.isArray(e)))
    throw new Error('contrib: the training log must be an array of episode objects; nothing is exported from a record that cannot be read');
  if (!meta || typeof meta.product !== 'string' || typeof meta.pack_version !== 'string' || typeof meta.record_tag !== 'string'
      || !meta.consent || typeof meta.consent.statement !== 'string' || !Array.isArray(meta.consent.scopes) || typeof meta.consent.license !== 'string'
      || !meta.fields_by_kind || !meta.honesty) throw new Error('contrib: meta must carry product, pack_version, record_tag, consent (statement, scopes, license), fields_by_kind and honesty');
  if (!consent || !Array.isArray(consent.scope) || consent.scope.length === 0)
    throw new Error('contrib: no scope ticked, no consent, no package');
  for (const s of consent.scope) if (!meta.consent.scopes.includes(s)) throw new Error('contrib: scope ' + JSON.stringify(s) + ' is not one this registry declares; nothing is exported under it');
  if (new Set(consent.scope).size !== consent.scope.length) throw new Error('contrib: a scope is ticked twice');
  if (typeof consent.granted_at !== 'string' || !isFinite(Date.parse(consent.granted_at))) throw new Error('contrib: consent.granted_at must be an ISO-8601 string');
  if (meta.wallet !== undefined && meta.wallet !== null && (typeof meta.wallet !== 'string' || !/^0x[0-9a-fA-F]{40}$/.test(meta.wallet)))
    throw new Error('contrib: meta.wallet must be an address or absent; a package is never attested to a wallet it cannot name');
  const wallet = typeof meta.wallet === 'string' ? meta.wallet : null;
  const label = (identity && typeof identity === 'object' && typeof identity.label === 'string') ? identity.label : null;
  const c = countEpisodes(training);
  const record = {
    record: meta.record_tag,
    product: meta.product,
    pack_version: meta.pack_version,
    exported_at: now.toISOString(),
    contributor: wallet === null
      ? { claimed: label, attested_by: UNSIGNED_ATTESTATION, signature: null }
      : { claimed: wallet, attested_by: SIGNED_ATTESTATION, signature: null },
    consent: {
      statement: meta.consent.statement,
      granted_at: consent.granted_at,
      scope: meta.consent.scopes.filter((s) => consent.scope.includes(s)),
      revocable: true,
      license: meta.consent.license,
    },
    dataset: {
      episodes: training,
      traces_attached: c.traces_attached,
      episode_counts_by_kind: c.episode_counts_by_kind,
      sims_covered: c.sims_covered,
      fields_by_kind: meta.fields_by_kind,
    },
    honesty: {
      proves: meta.honesty.proves,
      does_not_prove: meta.honesty.does_not_prove,
      nothing_sent: meta.honesty.nothing_sent,
      no_agent_trained: meta.honesty.no_agent_trained,
      contributor: wallet === null
        ? 'the contributor label is what this device stores under its identity key, or null; nobody has verified it and the signature is null'
        : 'contributor.signature, when filled, is an EIP-191 personal_sign by the wallet ' + wallet + ' over this digest and consent scope: the holder of that key signed at export - the identity of a key, not of a person',
    },
  };
  const bytes = new TextEncoder().encode(canonicalJSON(digestBody(record)));
  const buf = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  const hex = [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
  record.digest = { alg: 'SHA-256', over: meta.digest_over, hex };
  return record;
}

/* the on-page figures, computed from a package and never typed */
function summarizePackage(record) {
  const c = countEpisodes(record.dataset.episodes);
  return {
    episodes: record.dataset.episodes.length,
    by_kind: c.episode_counts_by_kind,
    traces: c.traces_attached,
    samples: c.samples,
    sims: c.sims_covered,
    scope: record.consent.scope,
    license: record.consent.license,
    attested_by: record.contributor.attested_by,
    claimed: record.contributor.claimed,
    digest: record.digest.hex,
  };
}
/* CONTRIB:END */
"""

SCRIPT = r'''
const D = JSON.parse(document.getElementById('tcdata').textContent);
const KEYS = D.keys;
const elem = (tag, opts = {}) => {
  const e = document.createElement(tag);
  if (opts.text !== undefined) e.textContent = opts.text;
  if (opts.cls) e.className = opts.cls;
  if (opts.attrs) for (const [k, v] of Object.entries(opts.attrs)) e.setAttribute(k, v);
  return e;
};

/* ------------------------------------------------------- the device record */
/* Absent, blocked and unreadable are three different answers and the panel
   says which one it got. A record that cannot be read is NOT an empty record. */
function readRaw(key) {
  try { return { ok: true, raw: localStorage.getItem(key) }; }
  catch (e) { return { ok: false, raw: null, note: String((e && e.message) || e) }; }
}
function readJson(key) {
  const r = readRaw(key);
  if (!r.ok) return { state: 'blocked', value: null, note: r.note };
  if (r.raw === null) return { state: 'absent', value: null, note: '' };
  try { return { state: 'present', value: JSON.parse(r.raw), note: '', bytes: r.raw.length }; }
  catch (e) { return { state: 'unreadable', value: null, note: String((e && e.message) || e) }; }
}
const rec = { training: readJson(KEYS.training), identity: readJson(KEYS.identity) };

function paintDevice() {
  const box = document.getElementById('device');
  box.textContent = '';
  box.setAttribute('data-training-state', rec.training.state);
  box.setAttribute('data-identity-state', rec.identity.state);
  const t = rec.training;
  const nEp = t.state === 'present' && Array.isArray(t.value) ? t.value.length : 0;
  box.appendChild(elem('p', { text: 'Training log under ' + KEYS.training + ': ' + t.state
    + (t.state === 'present' ? (Array.isArray(t.value) ? ', ' + nEp + ' episode(s)' : ', but not an array - nothing is exported from it') : '')
    + (t.note ? ' (' + t.note + ')' : '') + '.' }));
  const idv = rec.identity.value;
  const label = (idv && typeof idv === 'object' && typeof idv.label === 'string') ? idv.label : null;
  box.appendChild(elem('p', { text: 'Identity under ' + KEYS.identity + ': ' + rec.identity.state
    + (label === null ? ' - no label, so contributor.claimed will be null' : ' - label "' + label + '", a label this device stores and nobody has verified')
    + '.' }));
}

/* ----------------------------------------------------------- the consent panel */
const boxes = [...document.querySelectorAll('input[data-scope]')];
const ticked = () => boxes.filter((b) => b.checked).map((b) => b.getAttribute('data-scope'));
const btn = document.getElementById('expPackage');
const sbtn = document.getElementById('signPackage');
const sst = document.getElementById('signStatus');
const est = document.getElementById('expStatus');
const sayS = (t, state) => { sst.textContent = t; sst.setAttribute('data-sign-state', state); };
const sayE = (t, state) => { est.textContent = t; est.setAttribute('data-export-state', state); };

const idv = rec.identity.value;
/* a wallet identity is the one the sign-in page wrote with method siwe-ethereum
   AND an address; a label alone is not a wallet and gets no signature */
const walletAddress = (idv && typeof idv === 'object' && idv.method === D.signing.wallet_method
  && typeof idv.address === 'string' && /^0x[0-9a-fA-F]{40}$/.test(idv.address)) ? idv.address : null;
const wallet = (typeof window.ethereum === 'undefined') ? null : window.ethereum;
const canExport = () => rec.training.state === 'present' && Array.isArray(rec.training.value) && ticked().length > 0;
const meta = { product: D.product, pack_version: D.pack_version, record_tag: D.record_tag, consent: D.consent,
  fields_by_kind: D.fields_by_kind, honesty: D.honesty, digest_over: D.digest_over };

function refresh() {
  const ok = canExport();
  btn.disabled = !ok;
  if (rec.training.state !== 'present') sayE('Nothing to export: the training log is ' + rec.training.state + '.', 'no-log');
  else if (!Array.isArray(rec.training.value)) sayE('Nothing to export: the training log is not an array.', 'no-log');
  else if (ticked().length === 0) sayE('Tick at least one scope to build a package. No scope, no consent, no package.', 'no-scope');
  else sayE('Ready: ' + rec.training.value.length + ' episode(s) under scope ' + ticked().join(', ') + '. The file is downloaded to this device and sent nowhere.', 'ready');
  if (walletAddress === null) {
    sbtn.hidden = true; sbtn.disabled = true;
    sayS('No wallet identity is stored under ' + KEYS.identity + ' on this device, so no signature is offered: a package exported here stays unsigned and says so.', 'no-wallet-identity');
  } else if (wallet === null) {
    sbtn.hidden = false; sbtn.disabled = true;
    sayS('This device names the wallet ' + walletAddress + ', but no wallet is present in this browser (there is no window.ethereum), so nothing can sign. The package stays unsigned.', 'no-provider');
  } else {
    sbtn.hidden = false; sbtn.disabled = !ok;
    sayS('This device names the wallet ' + walletAddress + '. Signing asks that wallet for a personal_sign over this package\'s digest and consent scope. It proves the holder of that key signed now - a key, not a person. Nothing is written to any chain and nothing is sent anywhere.', 'ready');
  }
}
for (const b of boxes) b.addEventListener('change', refresh);

async function paintSummary(pkg) {
  const box = document.getElementById('summary');
  box.textContent = '';
  const S = summarizePackage(pkg);
  const figs = [
    ['episodes', S.episodes, 'episodes'],
    ['by kind', Object.keys(S.by_kind).map((k) => k + ' ' + S.by_kind[k]).join(', ') || 'none', 'by-kind'],
    ['traces attached / samples', S.traces + ' / ' + S.samples, 'traces'],
    ['sims covered', S.sims.length ? S.sims.join(', ') : 'none', 'sims'],
    ['consent scope', S.scope.join(', '), 'scope'],
    ['licence', S.license, 'license'],
    ['contributor', (S.claimed === null ? 'no label' : S.claimed) + ' - ' + S.attested_by, 'contributor'],
    ['digest', S.digest.slice(0, 16) + '…', 'digest'],
  ];
  const tb = elem('table'); const body = elem('tbody');
  for (const [k, v, key] of figs) {
    const tr = elem('tr'); tr.appendChild(elem('th', { text: k }));
    const td = elem('td', { text: String(v) }); td.setAttribute('data-contrib-fig', key); tr.appendChild(td);
    body.appendChild(tr);
  }
  tb.appendChild(body); box.appendChild(tb);
}

const download = (fresh, suffix) => {
  const blob = new Blob([JSON.stringify(fresh, null, 1)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'tc-contribution-' + fresh.exported_at.slice(0, 19).replace(/[:T]/g, '-') + suffix + '.json';
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
};
const consentNow = () => ({ scope: ticked(), granted_at: new Date().toISOString() });

btn.onclick = async () => {
  try {
    const pkg = await buildContribution(rec.training.value, rec.identity.value, consentNow(), meta, new Date());
    await paintSummary(pkg);
    download(pkg, '');
    sayE('Exported ' + pkg.dataset.episodes.length + ' episode(s), unsigned, attested by this device only. Digest ' + pkg.digest.hex.slice(0, 16) + '…. Verify with node contrib/verify.mjs on the file. Nothing was sent anywhere.', 'exported');
  } catch (e) {
    sayE('Not exported: ' + String(e && e.message !== undefined ? e.message : e), 'refused');
  }
};

/* ---- the wallet signature. Offered ONLY when the sign-in page stored a
   wallet identity with an address, and only a real window.ethereum can
   produce one: the page never fabricates a signature. */
sbtn.onclick = async () => {
  try {
    sayS('Building the package and asking the wallet…', 'asking');
    const fresh = await buildContribution(rec.training.value, rec.identity.value, consentNow(), { ...meta, wallet: walletAddress }, new Date());
    const message = signatureMessage(fresh, D.signing.statement);
    const accounts = await wallet.request({ method: 'eth_requestAccounts' });
    const account = (Array.isArray(accounts) ? accounts : []).find((a) => typeof a === 'string' && a.toLowerCase() === walletAddress.toLowerCase());
    if (account === undefined) throw new Error('the connected wallet does not hold ' + walletAddress + ', the address this device named; nothing was signed');
    const sig = await wallet.request({ method: 'personal_sign', params: [message, account] });
    const signed = attachSignature(fresh, walletAddress, sig, D.signing);
    await paintSummary(signed);
    sayS('Signed by the wallet ' + walletAddress + ' over digest ' + signed.digest.hex.slice(0, 16) + '… and scope ' + signed.consent.scope.join(', ') + '. Not verified in this page: run node contrib/verify.mjs on the file to recover the signer. A key signed, not a person; nothing is on any chain; nothing was sent.', 'signed');
    download(signed, '-signed');
  } catch (e) {
    sayS('Not signed: ' + String(e && e.message !== undefined ? e.message : e) + '. Nothing was downloaded.', 'refused');
  }
};

paintDevice();
refresh();
'''

SCOPE_ROWS = ''.join(
    f'<label class="scope"><input type="checkbox" data-scope="{E(s)}"> <b>{E(s)}</b> — {E(SCOPES[s])}</label>\n'
    for s in sorted(SCOPES))
KIND_ROWS = ''.join(
    f'<tr><td class="k">{E(k)}</td><td>{E(", ".join(FIELDS_BY_KIND[k]))}</td>'
    f'<td class="muted">{E(need(EPISODE_KINDS[k], "what", k))}</td></tr>\n' for k in FIELDS_BY_KIND)
PROVES = ''.join(f'<li>{E(x)}</li>' for x in need(HONESTY, 'proves', CONTRIB_PATH))
NOT_PROVES = ''.join(f'<li>{E(x)}</li>' for x in need(HONESTY, 'does_not_prove', CONTRIB_PATH))
if DESTINATIONS:
    DEST_ROWS = ''.join(
        f'<tr data-destination="{E(d["id"])}"><td class="k">{E(d["name"])}</td><td class="muted">{E(d["what"])}</td>'
        f'<td class="num" data-reach="none">{E(" · ".join(NOT_REACHED))}</td></tr>\n' for d in DESTINATIONS)
    DEST_TABLE = (f'<div class="tscroll"><table id="destinations" data-destinations="{len(DESTINATIONS)}"><tbody>'
                  f'<tr><th>destination named by {E(PROTOCOLS_PATH)}</th><th>what it says</th><th>reached by this bundle</th></tr>'
                  f'{DEST_ROWS}</tbody></table></div>')
    DEST_NOTE = (f'{F(len(DESTINATIONS))} destination(s) are named by <code>{E(PROTOCOLS_PATH)}</code> at build time. '
                 f'Every one of them is {E(", ".join(NOT_REACHED))}: this page writes a file and stops.')
else:
    DEST_TABLE = f'<div class="nonebox" id="destinations" data-destinations="0">No destination is configured.</div>'
    DEST_NOTE = (f'<code>{E(PROTOCOLS_PATH)}</code> is {E(PROTOCOLS_STATE)} at build time, so this list is empty and no '
                 f'destination is configured. When that registry names agent-protocol destinations they appear here, '
                 f'each marked {E(", ".join(NOT_REACHED))}: naming a place is not reaching it.')
READS = ''.join(f'<li><code>{E(p)}</code></li>' for p in (CONTRIB_PATH, TRAINING_PATH, AUTH_PATH, MANIFEST_PATH))
READS += f'<li><code>{E(PROTOCOLS_PATH)}</code> — {E(PROTOCOLS_STATE)}</li>'

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' stroke='%23E8A33D' stroke-width='2.6' stroke-linejoin='round'/%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E">
<title>{E(TITLE)} — contribute training data</title>
<style>
:root{{
  --plate:#12181B; --panel:#182023; --sunk:#0C1113; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --mark-ink:#12181B; --steel:#41C4D4;
  --good:#5CB584; --crit:#E07C68; --warn:#E8A33D;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--plate);color:var(--ink);
  font:14px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;padding:0 18px}}
.wrap{{max-width:1020px;margin:0 auto}}
a{{color:var(--steel)}}
header.page{{padding:40px 0 10px;border-bottom:3px solid var(--mark)}}
header.page h1{{font:700 34px/1.1 "Barlow Condensed",system-ui,sans-serif;margin:0}}
header.page h1 .x{{color:var(--mark)}}
header.page p{{color:var(--muted);margin:6px 0 14px}}
h2{{font:700 22px/1.2 "Barlow Condensed",system-ui,sans-serif;margin:34px 0 10px;
  color:var(--mark);letter-spacing:.02em}}
section{{margin:0 0 10px}}
.lead{{background:var(--panel);border:1px solid var(--rule);border-left:4px solid var(--warn);
  border-radius:8px;padding:14px 18px}}
.lead ul,.card ul{{margin:8px 0 0;padding-inline-start:20px}}
.lead li,.card li{{margin:6px 0;color:var(--muted)}}
table{{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--rule);
  border-radius:8px;overflow:hidden;margin:8px 0}}
td,th{{border-top:1px solid var(--rule);padding:8px 10px;vertical-align:top;font-size:13.5px;
  text-align:start}}
th{{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;
  letter-spacing:.05em}}
tr:first-child td,tr:first-child th{{border-top:0}}
td.k{{color:var(--ink);font-weight:600;white-space:nowrap}}
td.num{{font:13px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--crit);white-space:nowrap}}
td.muted{{color:var(--muted)}}
.tscroll{{overflow-x:auto}}
@media (max-width:640px){{td.k,td.num{{white-space:normal}}}}
code{{font:13px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted)}}
.why{{color:var(--ink);font-size:14px}}
.muted{{color:var(--muted);font-size:13px}}
.card{{background:var(--panel);border:1px solid var(--rule);border-radius:10px;
  padding:14px 16px;margin:12px 0}}
.nonebox{{background:var(--sunk);border:1px solid var(--crit);border-radius:8px;
  padding:12px 14px;color:var(--ink)}}
.statement{{background:var(--sunk);border:1px solid var(--rule);border-radius:6px;padding:10px 12px;
  color:var(--ink);font-size:14px}}
label.scope{{display:block;margin:8px 0;color:var(--muted)}}
label.scope b{{color:var(--ink)}}
label.scope input{{margin-inline-end:8px;accent-color:var(--mark)}}
button{{background:var(--mark);color:var(--mark-ink);border:0;border-radius:7px;padding:8px 14px;font:inherit;font-weight:600;cursor:pointer}}
button:disabled{{background:var(--rule);color:var(--muted);cursor:not-allowed}}
footer.page{{margin-top:34px;border-top:1px solid var(--rule);padding:14px 0 30px;
  color:var(--muted);font-size:14px}}
footer.page a{{margin-inline-end:10px}}
</style>
</head>
<body>
<div class="wrap">

<header class="page">
  <h1>{E(TITLE)} — <span class="x">contribute training data</span></h1>
  <p>{E(PRODUCT)} · pack {E(PACK_VERSION)} · built {E(BUILT)} · share what this device recorded, on purpose,
     in a file <code>contrib/verify.mjs</code> can check</p>
</header>

<section class="lead" id="limits">
  <h2>What this page is, and what it is not</h2>
  <p class="why">The 3D environment records your episodes under <code>{E(TRAINING_KEY)}</code> when you leave the
     recorder on, and a coarse gauge trace of a running seat when you turn TRACE on. This page builds a
     <code>{E(RECORD_TAG)}</code> package from that log and from nothing else: your episodes verbatim, the scope you tick,
     a fixed consent statement, one fixed licence, a digest so an edit is detectable, and — only if this device names
     a wallet — a signature. <b>It uploads nothing.</b> The file lands in your downloads and this page stops.</p>
  <ul>
    <li><b>NOTHING SENT.</b> {E(NOTHING_SENT)}</li>
    <li><b>NO AGENT TRAINED.</b> {E(NO_AGENT)}</li>
    <li><b>A KEY, NOT A PERSON.</b> A wallet signature, if any, proves the holder of a key signed this digest and scope at
        export. It is not who you are; a key is held, lent and stolen. Nothing is written to any chain.</li>
    <li><b>YOU KEEP THE FILE.</b> {E(REVOCABLE_MEANS)}</li>
  </ul>
</section>

<section id="consent">
  <h2>Consent</h2>
  <p class="why">Tick what you are sharing this for. The statement and the licence are fixed by
     <code>{E(CONTRIB_PATH)}</code>, once, and never chosen per file; a package under any other text or licence is
     refused by the verifier. {E(need(CONSENT, 'recorder_consent', CONTRIB_PATH + '#consent'))}</p>
  <div class="card" id="consent-panel">
    {SCOPE_ROWS}
    <p class="muted">Statement carried in the file, verbatim:</p>
    <p class="statement" id="consent-statement">{E(CONSENT_STATEMENT)}</p>
    <p class="muted" id="consent-license" data-license="{E(LICENSE_SPDX)}">Licence: <b>{E(LICENSE_SPDX)}</b> ({E(LICENSE_NAME)}). {E(LICENSE_WHY)}</p>
    <p class="muted" id="consent-revocable" data-revocable="true">Revocable: you keep the file; nothing is uploaded by this page.</p>
  </div>
</section>

<section id="device-section">
  <h2>What this device holds</h2>
  <div class="card" id="device" data-training-state="unpainted" data-identity-state="unpainted"></div>
  <p class="muted">{E(IDENTITY_RULE)}</p>
</section>

<section id="export">
  <h2>Build the package</h2>
  <p><button id="expPackage" type="button" disabled>Export contribution package</button>
     <button id="signPackage" type="button" disabled hidden>Sign this package with the connected wallet</button></p>
  <p class="why" id="expStatus" data-export-state="unpainted"></p>
  <p class="why" id="signStatus" data-sign-state="unpainted"></p>
  <p class="why" id="signHonesty" data-sign-honesty="1">What a wallet signature is: proof that the holder of that key
     signed this digest and consent scope at export — the identity of a key, not of a person; a key is held, lent and
     stolen. What it is not: nothing is written to any chain, nothing is anchored, no transaction exists, and no agent
     or robot has learned anything from it. The page never fabricates a signature: no wallet, no signature, and the
     package says <code>{E(SIGNING['attested_unsigned'])}</code>. It is offered only when the sign-in page stored
     <code>{E(WALLET_LABEL)}</code> under <code>{E(IDENTITY_KEY)}</code>. Verify a file with
     <code>node contrib/verify.mjs &lt;package.json&gt;</code>, which recovers the signer with the sign-in page's own code.</p>
  <div class="card" id="summary"><p class="muted">The summary of the last package built appears here, computed from the
     package itself.</p></div>
</section>

<section id="shape">
  <h2>What an episode carries</h2>
  <p class="why">Read from <code>{E(TRAINING_PATH)}</code> through <code>{E(CONTRIB_PATH)}</code>. The verifier holds every
     episode to exactly these fields for its kind; a trace on a sim episode may hold at most
     {E(F(TRACE_MAX))} samples of <code>{{t, gauges}}</code>, and nothing inside <code>gauges</code> is checked because
     the registry enumerates no gauge field.</p>
  <div class="tscroll"><table id="kinds"><tbody>
    <tr><th>kind</th><th>fields</th><th>what</th></tr>
    {KIND_ROWS}
  </tbody></table></div>
</section>

<section id="proves">
  <h2>What a package proves, and does not</h2>
  <div class="card"><p class="why">Proves</p><ul id="proves-list">{PROVES}</ul>
  <p class="why">Does not prove</p><ul id="not-proves-list">{NOT_PROVES}</ul></div>
</section>

<section id="where">
  <h2>Where this could go</h2>
  <p class="why">{DEST_NOTE}</p>
  {DEST_TABLE}
</section>

<section>
  <h2>What this page read</h2>
  <ul class="muted">{READS}</ul>
  <p class="muted">Every figure on this page is read from those files at build time or computed in this page from
     the package it built. None is typed. {E(LAST_LINE)}</p>
</section>

<footer class="page">
  <a href="trade_craft_progress.html">learner progression</a>
  <a href="trade_craft_3d.html">3D environment</a>
  <a href="trade_craft_signin.html">who this device says you are</a>
  <a href="trade_craft_landing.html">landing</a>
</footer>
</div>
<script type="application/json" id="tcdata">{PAYLOAD}</script>
<script id="contrib-js">
{CONTRIB_JS}</script>
<script type="module">
{SCRIPT}</script>
</body>
</html>
'''

out = HERE / 'trade_craft_contribute.html'
emit(out, page, f'{len(SCOPES)} scopes, {len(FIELDS_BY_KIND)} episode kinds, {len(DESTINATIONS)} destinations '
                f'({PROTOCOLS_STATE}), uploads nothing')
