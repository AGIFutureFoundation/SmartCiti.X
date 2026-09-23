#!/usr/bin/env python3
"""The sign-in page: two things that work, three that say why they cannot.

Every word of policy on this page comes out of auth/registry/auth.json. The
page types no count and no claim of its own: the method table, the counts,
the disabled labels and the list of missing server-side pieces are all
rendered from the registry, so the page cannot drift away from the pack.

The cryptography is in the page, between the AUTH-CORE markers, and it is
the page's own code rather than a vendored library: a Keccak-f[1600]
sponge, secp256k1 public-key recovery and EIP-55 address derivation,
roughly 120 lines together. auth/test.mjs lifts that exact region out of
this built file and runs it in node against oracles this pack did not
write (node's sha3-256 over the same permutation, node's secp256k1
signatures), so "the page verifies the signature" is a checked claim and
not a decorative one.

One function writes the identity record, and it refuses any method whose
`configured` is not exactly true. That is the whole safety property of this
page, and the suite drives it directly rather than reading the source.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402


def _pack_root():
    for cand in (HERE, *HERE.parents):
        if (cand / 'pack').is_dir() and (cand / 'auth').is_dir():
            return cand
    raise RuntimeError('cannot locate the packs from ' + str(HERE))


ROOT = _pack_root()
A = json.loads((ROOT / 'auth' / 'registry' / 'auth.json').read_text())
M = A['methods']
C = A['counts']
H = A['honesty']
S = A['siwe']

ORDER = ['local-identity', 'siwe-ethereum'] + sorted(
    k for k, m in M.items() if m['configured'] is not True)
for k in M:
    if k not in ORDER:
        raise KeyError('web/build_auth.py: method %r is in the registry but '
                       'not in this page\'s order - a method the page does '
                       'not render is a method nobody can read about' % k)

# The data the page's own script reads. It is the registry, not a copy of
# parts of it retyped here: auth/test.mjs compares this blob with the file.
EMBED = json.dumps({
    'storage': A['storage'],
    'records_named': A['records_named'],
    'siwe': S,
    'counts': C,
    'methods': M,
}, sort_keys=True, separators=(',', ':'))
assert '</' not in EMBED and '<!' not in EMBED, \
    'web/build_auth.py: the registry carries markup that would close the ' \
    'script element early'


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def li(items):
    return ''.join('<li>%s</li>' % esc(i) for i in items)


# --------------------------------------------------------------- markup ---

rows = ''.join(
    '<tr class="%s"><td class="m">%s</td><td>%s</td><td class="f %s">%s</td>'
    '<td class="f no">no</td><td class="f no">no</td></tr>'
    % ('on' if M[k]['configured'] is True else 'off',
       esc(M[k]['label']), esc(M[k]['flow']),
       'yes' if M[k]['configured'] is True else 'no',
       'yes' if M[k]['configured'] is True else 'no')
    for k in ORDER)

issuers = ''.join(
    '<div class="issuer">'
    '<button class="off-btn" aria-disabled="true" data-method="%s">%s</button>'
    '<p class="why">%s</p>'
    '<details><summary>what is missing (%d)</summary><ul>%s</ul>'
    '<p class="when">%s</p></details>'
    '</div>'
    % (esc(k), esc(M[k]['label']), esc(M[k]['disabled_label']),
       len(M[k]['missing_server_side']), li(M[k]['missing_server_side']),
       esc(M[k]['becomes_available_when']))
    for k in ORDER if M[k]['configured'] is not True)

siwe_note = ('This page checks the signature itself: %s'
             % S['verification']['method']) if \
    S['verification']['implemented'] is True else \
    ('This page CANNOT check the signature: %s'
     % S['verification']['if_this_were_false'])

# ------------------------------------------------------------------ JS ---
# No `??`, no silent defaults: a missing field throws with its own path.

JS_CORE = r'''
/* AUTH-CORE:BEGIN — lifted verbatim by auth/test.mjs and run in node. It
   touches no DOM and no globals beyond TextEncoder and crypto, so the
   suite can drive every branch of it without a browser. */
'use strict';
var ID_KEY = 'tc-identity';

function te(s) { return new TextEncoder().encode(s); }
function hex(u) {
  var s = '', i;
  for (i = 0; i < u.length; i++) { s += u[i].toString(16).padStart(2, '0'); }
  return s;
}
function unhex(s) {
  var t = s.indexOf('0x') === 0 ? s.slice(2) : s, i;
  if (t.length % 2 !== 0) { throw new Error('auth: odd-length hex'); }
  var u = new Uint8Array(t.length / 2);
  for (i = 0; i < u.length; i++) {
    var b = parseInt(t.substr(i * 2, 2), 16);
    if (Number.isNaN(b)) { throw new Error('auth: not hex at byte ' + i); }
    u[i] = b;
  }
  return u;
}

/* ---- Keccak-f[1600]. The sponge takes its pad byte, so the same
   permutation this page uses for keccak-256 (0x01) can be driven in
   SHA3-256 mode (0x06) by the suite and compared against node's own
   sha3-256 — an implementation this pack did not write. ---------------- */
var KECCAK_RC = [
  0x0000000000000001n, 0x0000000000008082n, 0x800000000000808an,
  0x8000000080008000n, 0x000000000000808bn, 0x0000000080000001n,
  0x8000000080008081n, 0x8000000000008009n, 0x000000000000008an,
  0x0000000000000088n, 0x0000000080008009n, 0x000000008000000an,
  0x000000008000808bn, 0x800000000000008bn, 0x8000000000008089n,
  0x8000000000008003n, 0x8000000000008002n, 0x8000000000000080n,
  0x000000000000800an, 0x800000008000000an, 0x8000000080008081n,
  0x8000000000008080n, 0x0000000080000001n, 0x8000000080008008n];
var KECCAK_ROT = [[0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61],
                  [28, 55, 25, 21, 56], [27, 20, 39, 8, 14]];
var MASK64 = (1n << 64n) - 1n;
function rol(x, n) { return n === 0n ? x : ((x << n) | (x >> (64n - n))) & MASK64; }
function lanes() {
  var a = [], x, y;
  for (x = 0; x < 5; x++) { a.push([]); for (y = 0; y < 5; y++) { a[x].push(0n); } }
  return a;
}
function keccakF(A) {
  var r, x, y, C, D, B;
  for (r = 0; r < 24; r++) {
    C = [0n, 0n, 0n, 0n, 0n];
    for (x = 0; x < 5; x++) { C[x] = A[x][0] ^ A[x][1] ^ A[x][2] ^ A[x][3] ^ A[x][4]; }
    D = [0n, 0n, 0n, 0n, 0n];
    for (x = 0; x < 5; x++) { D[x] = C[(x + 4) % 5] ^ rol(C[(x + 1) % 5], 1n); }
    for (x = 0; x < 5; x++) { for (y = 0; y < 5; y++) { A[x][y] ^= D[x]; } }
    B = lanes();
    for (x = 0; x < 5; x++) {
      for (y = 0; y < 5; y++) { B[y][(2 * x + 3 * y) % 5] = rol(A[x][y], BigInt(KECCAK_ROT[x][y])); }
    }
    for (x = 0; x < 5; x++) {
      for (y = 0; y < 5; y++) { A[x][y] = B[x][y] ^ ((~B[(x + 1) % 5][y] & MASK64) & B[(x + 2) % 5][y]); }
    }
    A[0][0] ^= KECCAK_RC[r];
  }
  return A;
}
function sponge(bytes, pad, outLen) {
  var rate = 136, A = lanes(), n = bytes.length, off, i, b, lane;
  var padded = new Uint8Array((Math.floor(n / rate) + 1) * rate);
  padded.set(bytes);
  padded[n] = pad;
  padded[padded.length - 1] |= 0x80;
  for (off = 0; off < padded.length; off += rate) {
    for (i = 0; i < rate / 8; i++) {
      lane = 0n;
      for (b = 7; b >= 0; b--) { lane = (lane << 8n) | BigInt(padded[off + i * 8 + b]); }
      A[i % 5][Math.floor(i / 5)] ^= lane;
    }
    keccakF(A);
  }
  var out = new Uint8Array(outLen);
  for (i = 0; i < outLen; i++) {
    var L = Math.floor(i / 8);
    out[i] = Number((A[L % 5][Math.floor(L / 5)] >> BigInt(8 * (i % 8))) & 0xffn);
  }
  return out;
}
function keccak256(bytes) { return sponge(bytes, 0x01, 32); }

/* ---- secp256k1: public-key recovery from (r, s, v) ------------------ */
var SECP_P = (1n << 256n) - (1n << 32n) - 977n;
var SECP_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141n;
var SECP_G = [0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798n,
              0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8n];
function fmod(a, m) { var v = a % m; return v < 0n ? v + m : v; }
function finv(a, m) {
  var o = fmod(a, m), r = m, x = 1n, y = 0n, q, t;
  while (r !== 0n) { q = o / r; t = o - q * r; o = r; r = t; t = x - q * y; x = y; y = t; }
  if (o !== 1n) { throw new Error('auth: value has no inverse in the field'); }
  return fmod(x, m);
}
function ptDouble(P) {
  if (P === null) { return null; }
  if (P[1] === 0n) { return null; }
  var l = fmod(3n * P[0] * P[0] * finv(2n * P[1], SECP_P), SECP_P);
  var x = fmod(l * l - 2n * P[0], SECP_P);
  return [x, fmod(l * (P[0] - x) - P[1], SECP_P)];
}
function ptAdd(A, B) {
  if (A === null) { return B; }
  if (B === null) { return A; }
  if (A[0] === B[0]) { return fmod(A[1] + B[1], SECP_P) === 0n ? null : ptDouble(A); }
  var l = fmod((B[1] - A[1]) * finv(fmod(B[0] - A[0], SECP_P), SECP_P), SECP_P);
  var x = fmod(l * l - A[0] - B[0], SECP_P);
  return [x, fmod(l * (A[0] - x) - A[1], SECP_P)];
}
function ptMul(k, P) {
  var R = null, A = P, n = fmod(k, SECP_N);
  while (n > 0n) {
    if ((n & 1n) === 1n) { R = ptAdd(R, A); }
    A = ptDouble(A);
    n >>= 1n;
  }
  return R;
}
function fpow(b, e) {
  var r = 1n, x = fmod(b, SECP_P), n = e;
  while (n > 0n) { if ((n & 1n) === 1n) { r = fmod(r * x, SECP_P); } x = fmod(x * x, SECP_P); n >>= 1n; }
  return r;
}
function beInt(u) { var v = 0n, i; for (i = 0; i < u.length; i++) { v = (v << 8n) | BigInt(u[i]); } return v; }
function be32(v) {
  var u = new Uint8Array(32), x = v, i;
  for (i = 31; i >= 0; i--) { u[i] = Number(x & 0xffn); x >>= 8n; }
  return u;
}
/* the 65-byte signature a wallet returns: r | s | v */
function splitSig(sigHex) {
  var u = unhex(sigHex);
  if (u.length !== 65) {
    throw new Error('auth: a personal_sign signature is 65 bytes; this one is ' + u.length);
  }
  var v = u[64];
  if (v === 27 || v === 28) { v -= 27; }
  if (v !== 0 && v !== 1) {
    throw new Error('auth: recovery byte ' + u[64] + ' is not 27, 28, 0 or 1');
  }
  return { r: beInt(u.slice(0, 32)), s: beInt(u.slice(32, 64)), recid: v };
}
function recoverPubkey(hash32, r, s, recid) {
  if (r <= 0n || r >= SECP_N || s <= 0n || s >= SECP_N) {
    throw new Error('auth: signature scalar out of range — not a signature this curve made');
  }
  var x = r;
  if (x >= SECP_P) { throw new Error('auth: r is not an x-coordinate on secp256k1'); }
  var y = fpow(fmod(x * x * x + 7n, SECP_P), (SECP_P + 1n) / 4n);
  if (fmod(y * y, SECP_P) !== fmod(x * x * x + 7n, SECP_P)) {
    throw new Error('auth: r is not an x-coordinate on secp256k1');
  }
  if ((y & 1n) !== BigInt(recid & 1)) { y = SECP_P - y; }
  var e = fmod(beInt(hash32), SECP_N);
  var Q = ptMul(finv(r, SECP_N), ptAdd(ptMul(s, [x, y]), ptMul(SECP_N - e, SECP_G)));
  if (Q === null) { throw new Error('auth: recovery produced the point at infinity'); }
  return Q;
}
function addressOfPubkey(Q) {
  var raw = new Uint8Array(64);
  raw.set(be32(Q[0]), 0);
  raw.set(be32(Q[1]), 32);
  return toChecksumAddress('0x' + hex(keccak256(raw).slice(12)));
}
function toChecksumAddress(addr) {
  var lower = (addr.indexOf('0x') === 0 ? addr.slice(2) : addr).toLowerCase();
  if (lower.length !== 40) { throw new Error('auth: an address is 20 bytes; this one is ' + (lower.length / 2)); }
  var h = hex(keccak256(te(lower))), out = '0x', i;
  for (i = 0; i < 40; i++) {
    out += parseInt(h[i], 16) >= 8 ? lower[i].toUpperCase() : lower[i];
  }
  return out;
}
/* EIP-191 personal_sign preimage */
function personalHash(message) {
  var body = te(message);
  var prefix = te('\x19Ethereum Signed Message:\n' + body.length);
  var all = new Uint8Array(prefix.length + body.length);
  all.set(prefix, 0);
  all.set(body, prefix.length);
  return keccak256(all);
}
function recoverAddress(message, sigHex) {
  var p = splitSig(sigHex);
  return addressOfPubkey(recoverPubkey(personalHash(message), p.r, p.s, p.recid));
}
/* The ONLY place a signature is called verified. Equality of the recovered
   address with the one the wallet reported, compared as lowercase hex —
   there is no other branch that returns verified true. */
function verifySiwe(message, sigHex, claimedAddress) {
  if (typeof claimedAddress !== 'string' || claimedAddress === '') {
    throw new Error('auth: verifySiwe needs the address the wallet reported; there is nothing to compare against');
  }
  var recovered = recoverAddress(message, sigHex);
  return {
    recovered: recovered,
    claimed: toChecksumAddress(claimedAddress),
    verified: recovered.toLowerCase() === toChecksumAddress(claimedAddress).toLowerCase()
  };
}

/* ---- EIP-4361. Field order is AUTHORED from recollection of the spec;
   this build had no network. A wallet that mis-renders it is the signal. */
function siweMessage(f) {
  var need = ['domain', 'address', 'statement', 'uri', 'version', 'chainId', 'nonce', 'issuedAt'], i;
  for (i = 0; i < need.length; i++) {
    if (typeof f[need[i]] !== 'string' || f[need[i]] === '') {
      throw new Error('auth: siweMessage: field "' + need[i] + '" is missing. A default here would put a sentence in front of a person that they never agreed to.');
    }
  }
  return [f.domain + ' wants you to sign in with your Ethereum account:',
          f.address, '', f.statement, '',
          'URI: ' + f.uri,
          'Version: ' + f.version,
          'Chain ID: ' + f.chainId,
          'Nonce: ' + f.nonce,
          'Issued At: ' + f.issuedAt].join('\n');
}
function siweNonce(nBytes) {
  var u = new Uint8Array(nBytes);
  crypto.getRandomValues(u);
  return hex(u);
}

/* ---- the identity record. One writer, one guard. ------------------- */
function methodOf(AUTH, id) {
  if (!Object.prototype.hasOwnProperty.call(AUTH.methods, id)) {
    throw new Error('auth: "' + id + '" is not a method in auth/registry/auth.json#methods');
  }
  return AUTH.methods[id];
}
function identityGuard(AUTH, id) {
  var m = methodOf(AUTH, id);
  if (m.configured !== true) {
    throw new Error('auth: refused to sign in with "' + id + '": ' + m.disabled_label);
  }
  if (m.sets_identity !== true) {
    throw new Error('auth: refused to sign in with "' + id + '": this method does not set an identity');
  }
  if (m.authenticates !== false) {
    throw new Error('auth: "' + id + '" claims to authenticate. Nothing in this bundle can; the record is wrong, not the page.');
  }
  return m;
}
function writeIdentity(store, AUTH, id, record) {
  var m = identityGuard(AUTH, id);
  if (typeof record.label !== 'string' || record.label.trim() === '') {
    throw new Error('auth: an identity with no name is not an identity');
  }
  if (typeof record.set_at !== 'string' || record.set_at === '') {
    throw new Error('auth: record.set_at is missing; when a record was named is part of the record');
  }
  var out = { v: 1, method: id, label: record.label.trim(), set_at: record.set_at, authenticates: false };
  if (m.requires_verified_signature === true) {
    if (record.verified !== true) {
      throw new Error('auth: "' + id + '" requires a verified signature and this one was not verified');
    }
    if (typeof record.address !== 'string' || typeof record.recovered !== 'string'
        || record.address.toLowerCase() !== record.recovered.toLowerCase()) {
      throw new Error('auth: the recovered signer does not match the address claimed; no identity written');
    }
    out.address = record.address;
    out.recovered = record.recovered;
    out.verified = true;
    out.chain_id = AUTH.siwe.chain_id;
  }
  store.setItem(ID_KEY, JSON.stringify(out));
  return out;
}
function readIdentity(store) {
  var raw = store.getItem(ID_KEY);
  if (raw === null || raw === undefined || raw === '') { return null; }
  var v = JSON.parse(raw);
  if (v === null || typeof v !== 'object' || typeof v.method !== 'string') {
    throw new Error('auth: the record under ' + ID_KEY + ' is not an identity this page wrote');
  }
  return v;
}
function clearIdentity(store) { store.removeItem(ID_KEY); }
/* AUTH-CORE:END */
'''

JS_DOM = r'''
/* The page, wired to the core above. Nothing below decides policy: every
   refusal comes back out of writeIdentity, which reads the registry. */
var AUTH = JSON.parse(document.getElementById('auth-data').textContent);
if (AUTH.storage.identity_key !== ID_KEY) {
  throw new Error('auth: the page stores under ' + ID_KEY + ' but the registry says ' + AUTH.storage.identity_key);
}
var store = {
  ok: true,
  getItem: function (k) { try { return localStorage.getItem(k); } catch (e) { this.ok = false; return null; } },
  setItem: function (k, v) { try { localStorage.setItem(k, v); } catch (e) { this.ok = false; throw new Error('auth: this browser is not letting the page store anything, so nothing was saved'); } },
  removeItem: function (k) { try { localStorage.removeItem(k); } catch (e) { this.ok = false; } }
};
var elName = document.getElementById('ident-name');
var elNow = document.getElementById('ident-now');
var elMsg = document.getElementById('ident-msg');
var elSiweStatus = document.getElementById('siwe-status');
var elSiweOut = document.getElementById('siwe-out');
var elSiweBtn = document.getElementById('siwe-btn');
var elOffMsg = document.getElementById('off-msg');

function say(el, text, kind) {
  el.textContent = text;
  el.className = 'msg ' + kind;
}
function show() {
  var id = null, err = null;
  try { id = readIdentity(store); } catch (e) { err = e.message; }
  if (err !== null) {
    elNow.textContent = err + ' — clear it and name it again.';
    return;
  }
  if (id === null) {
    elNow.textContent = 'No name is set on this device yet. A name would '
      + 'attach to ' + AUTH.records_named.what_a_name_attaches_to + '.';
    return;
  }
  var line = id.label + ' — set on ' + id.set_at + ', by: ' + AUTH.methods[id.method].label + '.';
  if (id.method === 'siwe-ethereum') {
    line += ' Wallet ' + id.address + ', signature verified in this page. This is not a login.';
  } else {
    line += ' This is a label on this device, not a login: nothing was verified.';
  }
  elNow.textContent = line;
}

document.getElementById('ident-save').addEventListener('click', function () {
  try {
    writeIdentity(store, AUTH, 'local-identity', {
      label: elName.value, set_at: new Date().toISOString()
    });
    say(elMsg, 'Saved on this device. Nothing was sent anywhere and nothing was verified.', 'good');
    show();
  } catch (e) { say(elMsg, e.message, 'bad'); }
});
document.getElementById('ident-clear').addEventListener('click', function () {
  clearIdentity(store);
  say(elMsg, 'Cleared from this device.', 'good');
  show();
});

/* ---- the three adapters that are off. The handler makes the real call
   and shows what comes back, so the refusal is demonstrated rather than
   described. It can never write: writeIdentity reads configured. ------ */
var offBtns = document.querySelectorAll('.off-btn');
for (var i = 0; i < offBtns.length; i++) {
  offBtns[i].addEventListener('click', function (ev) {
    var id = ev.currentTarget.getAttribute('data-method');
    try {
      writeIdentity(store, AUTH, id, { label: 'should never happen', set_at: new Date().toISOString() });
      say(elOffMsg, 'THIS PAGE IS BROKEN: ' + id + ' wrote an identity. Report it.', 'bad');
    } catch (e) {
      say(elOffMsg, e.message, 'bad');
    }
    show();
  });
}

/* ---- the wallet ----------------------------------------------------- */
var wallet = (typeof window.ethereum === 'undefined') ? null : window.ethereum;
if (wallet === null) {
  elSiweBtn.setAttribute('aria-disabled', 'true');
  say(elSiweStatus, AUTH.siwe.no_wallet, 'note');
} else {
  say(elSiweStatus, 'A wallet is present in this browser. Signing proves consent; it does not log you in.', 'note');
}
elSiweBtn.addEventListener('click', function () {
  if (wallet === null) {
    say(elSiweStatus, AUTH.siwe.no_wallet, 'bad');
    return;
  }
  say(elSiweStatus, 'Asking the wallet…', 'note');
  wallet.request({ method: 'eth_requestAccounts' }).then(function (accounts) {
    if (!Array.isArray(accounts) || accounts.length === 0) {
      throw new Error('auth: the wallet returned no account');
    }
    var address = toChecksumAddress(accounts[0]);
    var message = siweMessage({
      domain: location.host === '' ? 'local file' : location.host,
      address: address,
      statement: AUTH.siwe.statement,
      uri: location.href,
      version: AUTH.siwe.version,
      chainId: String(AUTH.siwe.chain_id),
      nonce: siweNonce(AUTH.siwe.nonce_bytes),
      issuedAt: new Date().toISOString()
    });
    return wallet.request({ method: 'personal_sign', params: [message, accounts[0]] })
      .then(function (sig) {
        var v = verifySiwe(message, sig, address);
        elSiweOut.textContent = message + '\n\nsignature: ' + sig
          + '\nrecovered: ' + v.recovered + '\nverified:  ' + v.verified;
        if (v.verified !== true) {
          say(elSiweStatus, 'The signature did NOT recover to ' + address + '. No identity was written.', 'bad');
          return;
        }
        writeIdentity(store, AUTH, 'siwe-ethereum', {
          label: v.recovered, set_at: new Date().toISOString(),
          address: address, recovered: v.recovered, verified: true
        });
        say(elSiweStatus, 'Signature verified in this page: it recovers to ' + v.recovered + '. That is consent, not a login, and it gates nothing.', 'good');
        show();
      });
  }).catch(function (e) { say(elSiweStatus, String(e.message === undefined ? e : e.message), 'bad'); });
});

show();
'''

CSS = '''
:root{
  --plate:#12181B; --panel:#182023; --sunk:#0C1113; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --mark-ink:#12181B; --steel:#41C4D4; --stop:#D2705B;
}
*{box-sizing:border-box}
body{margin:0;background:var(--plate);color:var(--ink);
  font:16px/1.6 "IBM Plex Sans",system-ui,sans-serif;padding:0 16px 56px}
.wrap{max-width:900px;margin:0 auto}
header{padding:40px 0 8px;border-bottom:3px solid var(--mark)}
header h1{font:700 34px/1.1 "Barlow Condensed",system-ui,sans-serif;margin:0}
header h1 .x{color:var(--mark)}
header p{color:var(--muted);margin:6px 0 14px}
h2{font:600 22px/1.2 "Barlow Condensed",system-ui,sans-serif;margin:34px 0 8px;
  text-transform:uppercase;letter-spacing:.04em}
.lede{background:var(--sunk);border-inline-start:3px solid var(--stop);border-radius:6px;
  padding:16px 22px;margin:22px 0}
.lede p{margin:8px 0}
.lede b{color:var(--mark)}
.card{background:var(--panel);border:1px solid var(--rule);border-radius:8px;
  padding:18px 20px;margin:14px 0}
.card h3{margin:0 0 6px;font:600 18px/1.3 "Barlow Condensed",system-ui,sans-serif;
  text-transform:uppercase;letter-spacing:.03em}
.claim{color:var(--muted);font-size:14px;margin:6px 0}
.claim.not{color:var(--stop)}
input[type=text]{background:var(--sunk);color:var(--ink);border:1px solid var(--rule);
  border-radius:6px;padding:9px 12px;font:inherit;min-width:16rem}
button{background:var(--mark);color:var(--mark-ink);border:1px solid var(--mark);
  padding:9px 16px;border-radius:6px;cursor:pointer;font:inherit;font-weight:600}
button.ghost{background:transparent;color:var(--ink);border-color:var(--rule);font-weight:400}
button.off-btn{background:var(--sunk);color:var(--muted);border:1px dashed var(--stop);
  cursor:not-allowed;font-weight:400;text-decoration:line-through}
button[aria-disabled=true]{opacity:.65}
.row{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:10px 0}
.msg{font-size:14px;margin:8px 0;min-height:1.4em}
.msg.good{color:var(--steel)}
.msg.bad{color:var(--stop)}
.msg.note{color:var(--muted)}
.now{background:var(--sunk);border:1px solid var(--rule);border-radius:6px;
  padding:10px 14px;font-size:14px;color:var(--ink);margin:8px 0}
pre{background:var(--sunk);border:1px solid var(--rule);border-radius:6px;
  padding:12px 14px;overflow:auto;font-size:12.5px;color:var(--muted);white-space:pre-wrap;
  word-break:break-all}
.issuer{border-top:1px solid var(--rule);padding:14px 0}
.issuer .why{color:var(--stop);font-size:14px;margin:8px 0}
.issuer .when{color:var(--muted);font-size:13px;margin:8px 0 0}
details summary{cursor:pointer;color:var(--muted);font-size:13px}
details ul{color:var(--muted);font-size:13px;margin:8px 0 0}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px}
th,td{border-top:1px solid var(--rule);padding:8px 10px;text-align:start;vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:12.5px;text-transform:uppercase;letter-spacing:.04em}
td.m{font-weight:600;white-space:nowrap}
td.f{text-align:center;font-variant-numeric:tabular-nums}
td.f.yes{color:var(--steel)}
td.f.no{color:var(--stop)}
tr.off td.m{color:var(--muted)}
.figs{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0}
.fig{background:var(--panel);border:1px solid var(--rule);border-radius:8px;padding:12px 18px;min-width:150px}
.fig b{display:block;font:600 26px/1.2 "Barlow Condensed",system-ui,sans-serif;color:var(--mark)}
.fig span{color:var(--muted);font-size:13px}
footer{color:var(--muted);font-size:13px;margin-top:34px;border-top:1px solid var(--rule);padding-top:14px}
'''

ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
        "viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' "
        "fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' "
        "stroke='%23E8A33D' stroke-width='2.6' stroke-linejoin='round'/%3E"
        "%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' "
        "stroke-linecap='round'/%3E%3C/svg%3E")

page = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="''' + ICON + '''">
<title>SmartCiti.X : Trade Craft Academy &mdash; sign in</title>
<style>''' + CSS + '''</style>
</head>
<body><div class="wrap">
<header>
  <h1>SmartCiti<span class="x">.X</span> : Trade Craft Academy</h1>
  <p>powered by AGI Corp &mdash; sign in</p>
</header>

<div class="lede">
<p><b>Read this before you use anything on this page.</b> ''' + esc(H['no_backend']) + '''</p>
<p>''' + esc(H['nothing_here_authenticates']) + '''</p>
<p>''' + esc(H['why_not_a_button_anyway']) + '''</p>
</div>

<div class="figs">
  <div class="fig"><b>''' + str(C['methods']) + '''</b><span>sign-in methods described</span></div>
  <div class="fig"><b>''' + str(C['configured_true']) + '''</b><span>that work here</span></div>
  <div class="fig"><b>''' + str(C['configured_false']) + '''</b><span>issuer adapters OFF</span></div>
  <div class="fig"><b>''' + str(C['methods_that_authenticate']) + '''</b><span>that authenticate anybody</span></div>
  <div class="fig"><b>''' + str(C['missing_server_side_items']) + '''</b><span>missing server-side pieces, named</span></div>
</div>

<h2>1 &mdash; Name this device&rsquo;s training record</h2>
<div class="card">
  <h3>''' + esc(M['local-identity']['label']) + '''</h3>
  <p class="claim">''' + esc(M['local-identity']['what_it_claims']) + '''</p>
  <p class="claim not"><b>What this is not.</b> ''' + esc(M['local-identity']['what_it_does_not_claim']) + '''</p>
  <div class="row">
    <input type="text" id="ident-name" placeholder="a name for this record" autocomplete="off">
    <button id="ident-save">Save on this device</button>
    <button id="ident-clear" class="ghost">Clear</button>
  </div>
  <p class="msg note" id="ident-msg"></p>
  <p class="now" id="ident-now"></p>
  <p class="claim">Stored under <code>''' + esc(A['storage']['identity_key']) + '''</code>. ''' + esc(A['storage']['scope']) + ''' ''' + esc(A['storage']['never_leaves_the_device']) + '''</p>
</div>

<h2>2 &mdash; Sign a statement with an Ethereum wallet</h2>
<div class="card">
  <h3>''' + esc(M['siwe-ethereum']['label']) + '''</h3>
  <p class="claim">''' + esc(M['siwe-ethereum']['what_it_claims']) + '''</p>
  <p class="claim not"><b>What this is not.</b> ''' + esc(M['siwe-ethereum']['what_it_does_not_claim']) + '''</p>
  <p class="claim">''' + esc(siwe_note) + '''</p>
  <p class="claim">''' + esc(M['siwe-ethereum']['spec_provenance']) + '''</p>
  <div class="row"><button id="siwe-btn">''' + esc(M['siwe-ethereum']['label']) + '''</button></div>
  <p class="msg note" id="siwe-status"></p>
  <pre id="siwe-out"></pre>
</div>

<h2>3 &mdash; ''' + str(C['configured_false']) + ''' issuer adapters that are off</h2>
<div class="card">
  <p class="claim not">''' + esc(H['issuers_fail_closed']) + '''</p>
  ''' + issuers + '''
  <p class="msg bad" id="off-msg"></p>
  <p class="claim">These controls still answer a click, on purpose: the click runs the page&rsquo;s real identity writer and shows you what it refuses with. Nothing is stored.</p>
</div>

<h2>Every method, and what it claims</h2>
<table>
<thead><tr><th>method</th><th>the flow it uses</th><th>works here</th><th>authenticates</th><th>gates anything</th></tr></thead>
<tbody>''' + rows + '''</tbody>
</table>
<p class="claim">''' + esc(H['what_would_make_this_real']) + '''</p>

<footer>
<p>''' + esc(H['status']) + '''</p>
<p>Rendered from <code>auth/registry/auth.json</code> at pack version ''' + esc(A['pack_version']) + '''; every count above is read from that file rather than typed here.</p>
</footer>

<script type="application/json" id="auth-data">''' + EMBED + '''</script>
<script>''' + JS_CORE + JS_DOM + '''</script>
</div></body>
</html>
'''

out = HERE / 'trade_craft_signin.html'
emit(out, page,
     '%d methods, %d off, %d missing pieces named'
     % (C['methods'], C['configured_false'], C['missing_server_side_items']))
