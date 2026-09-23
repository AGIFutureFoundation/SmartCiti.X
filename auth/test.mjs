/* auth/test.mjs — the sign-in pack, checked. Browser-free, network-free.
 *
 * The rule this suite follows is the bundle's: recompute, never re-read.
 * Every count the registry publishes is recounted here from the records it
 * publishes, and every claim the PAGE makes is read out of the built page
 * rather than out of the pack that generated it.
 *
 * Two families matter more than the rest.
 *
 *   FAIL CLOSED. The three federated issuer adapters are off. This suite
 *   does not read the source and reason about it: it LIFTS the page's own
 *   identity writer out of web/trade_craft_signin.html, hands it a stub
 *   store, asks it to sign in with Google, Microsoft and email, and
 *   requires a throw and an empty store every time. Mutate any one of
 *   those adapters to set an identity and these checks are what fails.
 *
 *   VERIFIED MEANS VERIFIED. The page claims to recover the signer of an
 *   EIP-4361 signature. That claim is only worth the oracle behind it, so
 *   the page's Keccak-f[1600] is driven in SHA3-256 mode and held against
 *   node's own sha3-256, its secp256k1 recovery is held against signatures
 *   node produced with its own secp256k1, and the published addresses of
 *   the private keys 1, 2 and 3 are reproduced end to end. A stub that
 *   returned the address it was handed is caught by the tamper check.
 */
import { readFileSync } from 'node:fs';
import { createHash, generateKeyPairSync, sign as nodeSign, createPrivateKey, randomBytes } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok ' + m); }
                       else { fail++; console.log('  FAIL ' + m); } };
const read = (p) => readFileSync(join(ROOT, p), 'utf8');
const J = (p) => JSON.parse(read(p));

const A = J('auth/registry/auth.json');
const M = A.methods;
const IDS = Object.keys(M).sort();
const PAGE = read('web/trade_craft_signin.html');

console.log('auth/test.mjs');

/* ---- the page's own code, lifted and run here ---------------------- */
const CORE_A = PAGE.indexOf('/* AUTH-CORE:BEGIN');
const CORE_B = PAGE.indexOf('/* AUTH-CORE:END */');
const CORE = CORE_A >= 0 && CORE_B > CORE_A ? PAGE.slice(CORE_A, CORE_B) : null;
let P = null, coreErr = null;
try {
  P = new Function(CORE + '\nreturn { ID_KEY, sponge, keccak256, te, hex, unhex, '
    + 'toChecksumAddress, personalHash, recoverAddress, verifySiwe, siweMessage, '
    + 'siweNonce, writeIdentity, readIdentity, clearIdentity, identityGuard, '
    + 'ptMul, SECP_G, addressOfPubkey, be32, recoverPubkey, splitSig };')();
} catch (e) { coreErr = e.message; }
ok(CORE !== null && P !== null,
   'the page carries a marked AUTH-CORE region and it evaluates on its own — '
   + 'the crypto and the identity writer are the page\'s, run here, not a '
   + `second copy kept in this suite${coreErr ? ' [' + coreErr + ']' : ''}`);
if (P === null) { console.log(`\n${pass} ok, ${fail} failed`); process.exit(1); }

const store = () => {
  const m = new Map();
  return { m, getItem: (k) => (m.has(k) ? m.get(k) : null),
           setItem: (k, v) => m.set(k, v), removeItem: (k) => m.delete(k) };
};
const AUTHDATA = JSON.parse(PAGE.slice(
  PAGE.indexOf('id="auth-data">') + 'id="auth-data">'.length,
  PAGE.indexOf('</script>', PAGE.indexOf('id="auth-data">'))));

/* ---- provenance and arithmetic ------------------------------------- */
ok(A.pack === 'auth', 'the registry names its own pack');
{
  const src = readFileSync(join(HERE, 'build.py'));
  ok(createHash('sha256').update(src).digest('hex').slice(0, 16) === A.source_stamp,
     'the registry was built from the current builder (stamp check)');
}
ok(A.pack_version === J('pack/manifest.json').pack_version,
   'one bundle version, read from the manifest rather than typed here');
ok(A.counts.methods === IDS.length
   && A.counts.configured_true === IDS.filter((k) => M[k].configured === true).length
   && A.counts.configured_false === IDS.filter((k) => M[k].configured !== true).length,
   `the method counts are the methods, counted (${IDS.length} = `
   + `${A.counts.configured_true} usable + ${A.counts.configured_false} off)`);
ok(IDS.every((k) => A.provenance_tiers.includes(M[k].provenance))
   && !JSON.stringify(A).includes('AI-SYNTHESIZED'),
   'every method carries a tier this pack declares, and the reserved word '
   + 'AI-SYNTHESIZED appears nowhere — it belongs to orbis/');

/* ---- NOTHING HERE AUTHENTICATES ------------------------------------ */
ok(IDS.every((k) => M[k].authenticates === false && M[k].gates_anything === false)
   && A.counts.methods_that_authenticate === 0 && A.counts.methods_that_gate_anything === 0,
   `all ${IDS.length} methods carry authenticates false and gates_anything `
   + 'false, the wallet one included — a bundle with no server cannot tell '
   + 'anyone apart');
ok(/no server|no backend/i.test(A.honesty.no_backend)
   && /worse than no sign-in|invites reliance/i.test(A.honesty.why_not_a_button_anyway),
   'and the honesty block says WHY a browser-only issuer button was not '
   + 'shipped instead: it would invite reliance on nothing');

/* ---- the three adapters, as records -------------------------------- */
const OFF = IDS.filter((k) => M[k].configured !== true);
ok(OFF.length === 3 && OFF.join(',') === 'email-link,google-oidc,microsoft-entra',
   `the three federated issuers are the off ones: ${OFF.join(', ')}`);
ok(OFF.every((k) => M[k].sets_identity === false && M[k].disabled === true),
   'every unconfigured method carries sets_identity false AND disabled true '
   + '— the two flags that would have to disagree for a click to write '
   + 'anything');
ok(OFF.every((k) => Array.isArray(M[k].missing_server_side)
     && M[k].missing_server_side.length >= 3
     && M[k].missing_server_side.every((s) => s.length > 40))
   && A.counts.missing_server_side_items
      === OFF.reduce((a, k) => a + M[k].missing_server_side.length, 0),
   `each off adapter names the server-side pieces it is missing `
   + `(${A.counts.missing_server_side_items} across the three), in sentences `
   + 'rather than a word');
ok(OFF.every((k) => /server/i.test(M[k].disabled_label)
     && /so it is off/.test(M[k].disabled_label)),
   'each off adapter\'s label says what is missing and that it is therefore '
   + 'off — the text a reader sees on the control itself');
ok(OFF.every((k) => /configuration change/.test(M[k].becomes_available_when)
     && /not something the page can do to itself/.test(M[k].becomes_available_when)),
   'and each says the day a backend exists this is a configuration change, '
   + 'and not something the page can do to itself');
ok(IDS.filter((k) => M[k].configured === true).every((k) => M[k].sets_identity === true),
   'the two methods that do work are the two that may set an identity — the '
   + 'flags are not merely all-off');

/* ================= THE GUARD, DRIVEN =================================
   The most important checks in this pack. Not a reading of the source:
   the page's own writeIdentity, called here, against a stub store. */
for (const k of OFF) {
  const s = store();
  let threw = null;
  try { P.writeIdentity(s, AUTHDATA, k, { label: 'mallory', set_at: new Date().toISOString() }); }
  catch (e) { threw = e.message; }
  ok(threw !== null && s.m.size === 0 && threw.includes(M[k].disabled_label),
     `the page's own identity writer REFUSES "${k}" and stores nothing — it `
     + `throws with the adapter's own reason${threw === null ? ' [IT WROTE AN IDENTITY]' : ''}`);
}
{
  const s = store();
  let threw = null;
  try { P.writeIdentity(s, AUTHDATA, 'no-such-issuer', { label: 'x', set_at: 'now' }); }
  catch (e) { threw = e.message; }
  ok(threw !== null && /is not a method/.test(threw) && s.m.size === 0,
     'an unknown method id is refused by name rather than defaulted to '
     + 'something — a default here would be a policy decision');
}
{
  const s = store();
  let rec = null, back = null;
  try {
    rec = P.writeIdentity(s, AUTHDATA, 'local-identity',
      { label: '  Dale Okafor  ', set_at: '2026-09-23T00:00:00.000Z' });
    back = P.readIdentity(s);
  } catch (e) { rec = { error: e.message }; }
  ok(s.m.size === 1 && rec !== null && rec.authenticates === false
     && back !== null && back.label === 'Dale Okafor'
     && back.method === 'local-identity' && s.m.has(A.storage.identity_key),
     `a local identity DOES write, under ${A.storage.identity_key}, and the `
     + 'record it writes says authenticates false in its own body');
}
{
  const s = store();
  let a = null, b = null;
  try { P.writeIdentity(s, AUTHDATA, 'local-identity', { label: '   ', set_at: 'x' }); } catch (e) { a = e.message; }
  try { P.writeIdentity(s, AUTHDATA, 'local-identity', { label: 'x' }); } catch (e) { b = e.message; }
  ok(a !== null && b !== null && /not an identity/.test(a) && /set_at/.test(b) && s.m.size === 0,
     'an empty name and a missing set_at are both refused by name — no field '
     + 'on an identity record gets a default');
}
{
  const s = store();
  let a = null, b = null;
  try {
    P.writeIdentity(s, AUTHDATA, 'siwe-ethereum', { label: 'w', set_at: 'now',
      address: '0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf', recovered: '0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf', verified: false });
  } catch (e) { a = e.message; }
  try {
    P.writeIdentity(s, AUTHDATA, 'siwe-ethereum', { label: 'w', set_at: 'now',
      address: '0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf', recovered: '0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF', verified: true });
  } catch (e) { b = e.message; }
  ok(a !== null && b !== null && /not verified/.test(a)
     && /does not match the address claimed/.test(b) && s.m.size === 0,
     'a wallet identity is refused unless the signature was verified AND the '
     + 'recovered signer is the address claimed — an unverified signature '
     + 'cannot become an identity');
}
{
  /* the refusal is data-driven, not a blocklist of names: the day a backend
     exists, flipping the flag is all it takes. Done on a COPY. */
  const s = store();
  const copy = JSON.parse(JSON.stringify(AUTHDATA));
  copy.methods['google-oidc'].configured = true;
  copy.methods['google-oidc'].sets_identity = true;
  let rec = null;
  try { rec = P.writeIdentity(s, copy, 'google-oidc', { label: 'g', set_at: 'now' }); }
  catch (e) { rec = { error: e.message }; }
  ok(s.m.size === 1 && rec.method === 'google-oidc' && rec.authenticates === false,
     'and the refusal reads the registry rather than hard-coding three '
     + 'names: with configured flipped true on a COPY of the data the same '
     + 'writer accepts it, which is what makes this a configuration change '
     + 'the day a server exists');
}
ok(A.methods['google-oidc'].configured === false
   && A.methods['microsoft-entra'].configured === false
   && A.methods['email-link'].configured === false,
   'and in the registry that actually ships, all three are false');

/* ---- one writer, one key ------------------------------------------- */
{
  const writes = (PAGE.match(/setItem\(ID_KEY/g) || []).length;
  const localWrites = (PAGE.match(/localStorage\.setItem/g) || []).length;
  const w = PAGE.indexOf('function writeIdentity');
  const at = PAGE.indexOf('setItem(ID_KEY');
  ok(writes === 1 && localWrites === 1 && at > w && at < PAGE.indexOf('function readIdentity'),
     'exactly one line in the whole page writes the identity record, and it '
     + 'is inside writeIdentity, below the guard — there is no second door');
}
ok(P.ID_KEY === A.storage.identity_key
   && AUTHDATA.storage.identity_key === A.storage.identity_key,
   `the page's code, the page's embedded data and the registry all name the `
   + `same storage key (${A.storage.identity_key})`);
ok(P.readIdentity(store()) === null,
   'an empty store reads back as no identity — the page does not invent one');

/* ---- the page says what the registry says -------------------------- */
ok(JSON.stringify(AUTHDATA.methods) === JSON.stringify(M),
   'the data the page runs on is the registry itself, not a summary of it '
   + 'retyped into the generator');
{
  const figs = [...PAGE.matchAll(/<div class="fig"><b>(\d+)<\/b><span>([^<]+)</g)]
    .map((m) => [Number(m[1]), m[2]]);
  const want = [[A.counts.methods, 'sign-in methods described'],
                [A.counts.configured_true, 'that work here'],
                [A.counts.configured_false, 'issuer adapters OFF'],
                [A.counts.methods_that_authenticate, 'that authenticate anybody'],
                [A.counts.missing_server_side_items, 'missing server-side pieces, named']];
  ok(JSON.stringify(figs) === JSON.stringify(want),
     `the five figures on the page are the registry's counts (${want.map((w) => w[0]).join(', ')}) `
     + '— including the zero that says nobody is authenticated');
}
const MARKUP = PAGE.slice(0, PAGE.indexOf('<script type="application/json"'));
/* the generator's own escaping, mirrored: & < > " and nothing else */
const esc = (t) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;')
  .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
ok(MARKUP.length > 1000
   && OFF.every((k) => MARKUP.includes(esc(M[k].disabled_label))
     && M[k].missing_server_side.every((s) => MARKUP.includes('<li>' + esc(s) + '</li>'))),
   'every off adapter\'s reason and every missing server-side piece is '
   + 'printed on the page, not merely recorded in the pack');
{
  /* the fault a browser found once: the page read a registry section the
     generator had not embedded, and threw on load. Every section the page's
     script reaches for must be in the blob it is handed. */
  const want = [...new Set([...PAGE.matchAll(/\bAUTH\.([A-Za-z_$][\w$]*)/g)].map((m) => m[1]))];
  const missing = want.filter((k) => !(k in AUTHDATA));
  ok(want.length >= 4 && missing.length === 0,
     `every registry section the page's script reads (${want.sort().join(', ')}) `
     + `is in the blob the page is handed${missing.length ? ' — missing: ' + missing.join(', ') : ''}`);
}
ok(!/(signed|logged) in with (google|microsoft|email)/i.test(PAGE)
   && !/you are (now )?authenticated/i.test(PAGE)
   && OFF.every((k) => !new RegExp('signed in[^.]{0,40}' + M[k].issuer, 'i').test(PAGE)),
   'THE ONE THAT MATTERS: nowhere in the built page is a person told they '
   + 'are signed in or authenticated by an issuer whose configured is false');
{
  const off = OFF.map((k) => new RegExp('data-method="' + k + '"'));
  ok(off.every((re) => re.test(PAGE))
     && (PAGE.match(/class="off-btn" aria-disabled="true"/g) || []).length === OFF.length,
     `each off adapter is rendered as a disabled control (${OFF.length} of `
     + 'them, aria-disabled), carrying its own method id so the click can '
     + 'run the real writer and show the real refusal');
}

/* ================= THE CRYPTO, AGAINST OUTSIDE ORACLES ================ */
{
  let same = 0;
  const inputs = ['', 'abc', 'the quick brown fox', 'x'.repeat(200), 'Chain ID: 1'];
  for (const s of inputs) {
    const mine = P.hex(P.sponge(P.te(s), 0x06, 32));
    if (mine === createHash('sha3-256').update(s).digest('hex')) same++;
  }
  ok(same === inputs.length,
     `the page's Keccak-f[1600] is correct: driven in SHA3-256 mode (the same `
     + `sponge, pad 0x06) it reproduces node's own sha3-256 on ${inputs.length} `
     + 'inputs — an implementation this pack did not write');
}
ok(P.hex(P.keccak256(P.te('')))
   === 'c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470',
   'and in keccak-256 mode (pad 0x01) it reproduces the published '
   + 'keccak256("") — the hash Ethereum carries as the empty code hash');
{
  const want = ['0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf',
                '0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF',
                '0x6813Eb9362372EEF6200f3b1dbC3f819671cBA69'];
  const got = [1n, 2n, 3n].map((k) => P.addressOfPubkey(P.ptMul(k, P.SECP_G)));
  ok(JSON.stringify(got) === JSON.stringify(want),
     'the page derives the published addresses of the private keys 1, 2 and '
     + '3, checksum casing included — curve, keccak and EIP-55 all at once, '
     + 'against numbers this pack did not choose');
}
const b64u = (u) => Buffer.from(u).toString('base64url');
const SECP_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141n;
const h32 = (v) => v.toString(16).padStart(64, '0');
const beI = (u) => BigInt('0x' + Buffer.from(u).toString('hex'));
/* a modular inverse written here rather than borrowed from the page, so the
   test-side signer below shares as little with the code under test as it can */
function invN(a) {
  let o = ((a % SECP_N) + SECP_N) % SECP_N, r = SECP_N, x = 1n, y = 0n;
  while (r !== 0n) { const q = o / r; [o, r] = [r, o - q * r]; [x, y] = [y, x - q * y]; }
  return ((x % SECP_N) + SECP_N) % SECP_N;
}
function keyFor(d) {
  const Q = P.ptMul(d, P.SECP_G);
  return createPrivateKey({ format: 'jwk', key: { kty: 'EC', crv: 'secp256k1',
    d: b64u(P.be32(d)), x: b64u(P.be32(Q[0])), y: b64u(P.be32(Q[1])) } });
}
function derRS(der) {
  const rl = der[3], r = der.slice(4, 4 + rl);
  const sl = der[5 + rl], s = der.slice(6 + rl, 6 + rl + sl);
  return [beI(r), beI(s)];
}

/* ---- the curve math, against node's own secp256k1 ------------------
   node will not sign a digest it did not compute (crypto.sign hashes with
   SHA-256 whatever algorithm you name), so the oracle is applied one level
   down: node signs, and the PAGE recovers node's exact public key from the
   signature. That is the part no test could fake. */
{
  const N = 8;
  let hits = 0;
  for (let i = 0; i < N; i++) {
    const { privateKey, publicKey } = generateKeyPairSync('ec', { namedCurve: 'secp256k1' });
    const jwk = publicKey.export({ format: 'jwk' });
    const px = beI(Buffer.from(jwk.x, 'base64url')), py = beI(Buffer.from(jwk.y, 'base64url'));
    const data = randomBytes(40);
    const digest = createHash('sha256').update(data).digest();
    const [r, s] = derRS(nodeSign('sha256', data, { key: privateKey, dsaEncoding: 'der' }));
    const got = [0, 1].map((v) => { try { return P.recoverPubkey(digest, r, s, v); } catch (e) { return null; } });
    if (got.some((Q) => Q !== null && Q[0] === px && Q[1] === py)) hits++;
  }
  ok(hits === N,
     `the page's secp256k1 recovery reconstructs the exact public key node `
     + `generated, from ${N} signatures node made with its own secp256k1 over `
     + 'random keys — the curve arithmetic is checked against an '
     + 'implementation this pack did not write');
}

/* a signer written here, over the page's EIP-191 preimage, so the whole
   personal_sign path can be driven end to end. It shares only the point
   arithmetic with the page, and that is what the check above certified. */
function signPersonal(d, message) {
  /* the EIP-191 preimage, assembled here rather than taken from the page, so
     that the page's personalHash is under test and not merely reused */
  const body = Buffer.from(message, 'utf8');
  const pre = Buffer.concat([Buffer.from('\x19Ethereum Signed Message:\n' + body.length, 'utf8'), body]);
  const z = beI(P.keccak256(new Uint8Array(pre))) % SECP_N;
  for (;;) {
    const k = (beI(randomBytes(32)) % (SECP_N - 1n)) + 1n;
    const R = P.ptMul(k, P.SECP_G);
    const r = R[0] % SECP_N;
    if (r === 0n) continue;
    let s = (invN(k) * (z + r * d)) % SECP_N;
    if (s === 0n) continue;
    let rec = Number(R[1] & 1n);
    if (s > SECP_N / 2n) { s = SECP_N - s; rec ^= 1; }
    return '0x' + h32(r) + h32(s) + (27 + rec).toString(16).padStart(2, '0');
  }
}
{
  const d = 1n, msg = 'I am naming this account.';
  const want = '0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf';
  const sig = signPersonal(d, msg);
  let tampered = null;
  try { tampered = P.recoverAddress(msg + '!', sig); } catch (e) { tampered = 'threw'; }
  ok(P.recoverAddress(msg, sig) === want && tampered !== want,
     'end to end: a personal_sign signature over an EIP-191 preimage by the '
     + 'private key 1 recovers to its published address, and changing one '
     + 'character of the message recovers a DIFFERENT address — a stub that '
     + 'echoed back the address it was handed would fail here');
}
{
  let n = 0;
  for (let i = 0; i < 6; i++) {
    const d = (beI(randomBytes(31)) % (SECP_N - 1n)) + 1n;
    const msg = 'nonce ' + randomBytes(8).toString('hex');
    if (P.recoverAddress(msg, signPersonal(d, msg)) === P.addressOfPubkey(P.ptMul(d, P.SECP_G))) n++;
  }
  ok(n === 6,
     'and the same holds for 6 random keys and messages, so the one fixed '
     + 'vector above is not a coincidence of that key');
}
{
  let a = null, b = null, c = null;
  try { P.recoverAddress('m', '0xdead'); } catch (e) { a = e.message; }
  try { P.recoverAddress('m', '0x' + '00'.repeat(65)); } catch (e) { b = e.message; }
  try { P.recoverAddress('m', '0x' + 'ab'.repeat(64) + '05'); } catch (e) { c = e.message; }
  ok(a !== null && b !== null && c !== null && /65 bytes/.test(a)
     && /out of range/.test(b) && /not 27, 28, 0 or 1/.test(c),
     'a short signature, an all-zero one and one with a nonsense recovery '
     + 'byte each throw with what is wrong — none of them returns an address');
}
{
  const msg = 'who signed this';
  const d1 = 11n, d2 = 22n;
  const claimed = P.addressOfPubkey(P.ptMul(d1, P.SECP_G));
  const mine = P.verifySiwe(msg, signPersonal(d1, msg), claimed);
  const other = P.verifySiwe(msg, signPersonal(d2, msg), claimed);
  ok(mine.verified === true && mine.recovered === claimed && other.verified === false,
     'verifySiwe says verified only when the recovered signer IS the address '
     + 'claimed: a signature by a different key over the same message comes '
     + 'back verified false, never true');
}
ok(P.toChecksumAddress('0x7e5f4552091a69125d5dfcb7b8c2659029395bdf')
   === '0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf',
   'EIP-55 checksum casing is derived rather than copied: the lowercase form '
   + 'comes back in the published mixed case');

/* ---- the EIP-4361 message ------------------------------------------ */
{
  const f = { domain: 'example.test', address: '0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf',
    statement: A.siwe.statement, uri: 'https://example.test/x', version: A.siwe.version,
    chainId: String(A.siwe.chain_id), nonce: 'abc123', issuedAt: '2026-09-23T00:00:00.000Z' };
  const msg = P.siweMessage(f);
  const L = msg.split('\n');
  ok(L[0] === 'example.test wants you to sign in with your Ethereum account:'
     && L[1] === f.address && L[2] === '' && L[3] === f.statement && L[4] === ''
     && L[5] === 'URI: ' + f.uri && L[6] === 'Version: 1' && L[7] === 'Chain ID: 1'
     && L[8] === 'Nonce: abc123' && L[9] === 'Issued At: ' + f.issuedAt && L.length === 10,
     'the EIP-4361 message is built in the field order this pack records: '
     + A.siwe.fields.join(', '));
  ok(A.siwe.fields.length === A.counts.siwe_fields
     && A.siwe.fields.every((k) => k in A.siwe.field_notes),
     `all ${A.counts.siwe_fields} EIP-4361 fields the pack names carry a note `
     + 'saying what each is for');
  ok(/AUTHORED FROM RECOLLECTION/.test(M['siwe-ethereum'].spec_provenance)
     && PAGE.includes(M['siwe-ethereum'].spec_provenance),
     'and the page itself says the field order is AUTHORED FROM RECOLLECTION '
     + 'with no network to check it against — a wallet that mis-renders the '
     + 'message is the signal, not a passing test here');
  let missing = null;
  try { P.siweMessage({ ...f, nonce: '' }); } catch (e) { missing = e.message; }
  ok(missing !== null && missing.includes('"nonce"') && /never agreed to/.test(missing),
     'a missing field in that message throws naming the field — a default '
     + 'here would put a sentence in front of a person they never agreed to');
}
{
  const a = P.siweNonce(A.siwe.nonce_bytes), b = P.siweNonce(A.siwe.nonce_bytes);
  ok(a.length === A.siwe.nonce_bytes * 2 && a !== b && /^[0-9a-f]+$/.test(a),
     `the nonce is ${A.siwe.nonce_bytes} fresh random bytes per attempt, so a `
     + 'captured signature cannot be replayed into a later one');
}

/* ---- the verification claim is the checked one --------------------- */
ok(A.siwe.verification.implemented === true
   && A.siwe.verification.oracles.length >= 3
   && /node:crypto/.test(JSON.stringify(A.siwe.verification.oracles))
   && PAGE.includes(A.siwe.verification.method),
   'the registry claims in-page verification IS implemented, names the '
   + `outside oracles that hold it to that (${A.siwe.verification.oracles.length}), `
   + 'and the page prints the method it uses');
ok(/An unverified signature presented as verified/.test(A.siwe.verification.if_this_were_false),
   'and it records what it would have said instead had recovery not been '
   + 'implemented, so the honest alternative is on the record rather than '
   + 'only in a commit message');

/* ---- the records a name attaches to are real ----------------------- */
{
  const tr = J('training/registry/training.json');
  const walk = read('web/trade_craft_3d.html');
  ok(A.records_named.training_key === tr.storage.key
     && walk.includes("'" + A.records_named.progress_key + "'"),
     'the two records a name attaches to are the ones that exist: the '
     + `training key is training/'s own (${tr.storage.key}) and the progress `
     + `key (${A.records_named.progress_key}) is the key the walkable page `
     + 'actually uses');
  ok(A.storage.identity_key !== tr.storage.key
     && A.storage.identity_key !== A.records_named.progress_key,
     'and the identity is kept under its own key, so naming a record can '
     + 'never overwrite one');
}

console.log(`\n${pass} ok, ${fail} failed`);
process.exit(fail ? 1 : 0);
