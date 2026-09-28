/* payments/test.mjs - the catalogue and the Worker, checked. Network-free: globalThis.fetch is
 * replaced by a trap before the Worker loads, and every Stripe call goes to a recording mock.
 * Signatures are made here with node:crypto's HMAC (an oracle that is not the Worker's code)
 * and checked by the Worker through WebCrypto. Prints `  ok ` per check, FAIL at column 0. */
import { readFileSync } from 'node:fs';
import { createHmac, createHash, webcrypto } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok ' + m); } else { fail++; console.log('FAIL ' + m); } };
let netCalls = 0;
globalThis.fetch = async () => { netCalls++; throw new Error('network is forbidden in payments/test.mjs'); };

console.log('payments/test.mjs');
const CAT = JSON.parse(readFileSync(join(HERE, 'registry/catalog.json'), 'utf8'));
const MOD = (await import('./catalog.mjs')).default;
const W = await import('./worker.mjs');

/* ---- catalogue honesty ---- */
ok(JSON.stringify(MOD) === JSON.stringify(CAT), 'catalog.mjs is the same object as registry/catalog.json');
ok(CAT.source_stamp === 'sha256:' + createHash('sha256').update(readFileSync(join(HERE, 'build.py'))).digest('hex'),
  'source_stamp is the sha256 of payments/build.py');
ok(CAT.live === false && /not live: no Stripe account is connected/.test(CAT.status), 'catalogue says payments are not live');
const IDS = CAT.plans.map((p) => p.id);
for (const want of ['individual-learner', 'union-hall', 'school-district'])
  ok(IDS.includes(want), `plan ${want} present`);
const COMM = ['price', 'price_id', 'currency', 'interval', 'trial', 'discount', 'tax'];
ok(CAT.plans.every((p) => COMM.every((k) => k in p && p[k] === null)), 'no plan carries a price, currency, interval, trial, discount or tax');
ok(CAT.plans.every((p) => p.commercial_terms === 'set by the operator in Stripe'), 'every plan: terms set by the operator in Stripe');
ok(!/\d+[.,]\d\d\b|[$€£¥]|\busd\b|\beur\b/i.test(JSON.stringify(CAT.plans)), 'no money figure or currency anywhere in the plans');
ok(CAT.plans.every((p) => /^STRIPE_PRICE_[A-Z_]+$/.test(p.price_env) && /^STRIPE_MODE_[A-Z_]+$/.test(p.mode_env)), 'price and mode come from named env vars');
ok(CAT.checkout.success_path.startsWith('/') && CAT.checkout.cancel_path.startsWith('/') &&
  !CAT.checkout.success_path.startsWith('//') && !CAT.checkout.cancel_path.startsWith('//'), 'success/cancel are same-site paths');
const SRC = readFileSync(join(HERE, 'worker.mjs'), 'utf8');
ok(!/console\.(log|info|warn|error|debug)/.test(SRC), 'worker logs nothing');
ok(!/sk_(live|test)_[A-Za-z0-9]{8,}|whsec_[A-Za-z0-9]{8,}|price_[A-Za-z0-9]{8,}/.test(SRC + JSON.stringify(CAT)), 'no key, webhook secret or price id committed');
ok(!/card|cvc|pan\b/i.test(SRC.replace(/Card data never touches this code/g, '')), 'worker never names card fields');

/* ---- harness ---- */
const SECRET = 'sk_test_' + 'FAKEFAKEFAKE';
const WHSEC = 'whsec_' + 'dGVzdHNlY3JldA==';
const SITE = 'https://academy.example';
const baseEnv = () => ({ STRIPE_SECRET_KEY: SECRET, SITE_ORIGIN: SITE, STRIPE_WEBHOOK_SECRET: WHSEC,
  STRIPE_PRICE_INDIVIDUAL_LEARNER: 'price_' + 'TESTONLY', STRIPE_MODE_INDIVIDUAL_LEARNER: 'subscription',
  PAYMENTS_KV: kvMock() });
function kvMock() { const m = new Map(); return { m, get: async (k) => (m.has(k) ? m.get(k) : null), put: async (k, v) => { m.set(k, v); } }; }
let calls = [];
const stripeMock = async (url, init) => { calls.push({ url, init }); return new Response(JSON.stringify({ id: 'cs_test_1', url: 'https://checkout.stripe.com/c/pay/cs_test_1' }), { status: 200 }); };
let subtleCalls = 0;
const subtle = { importKey: (...a) => { subtleCalls++; return webcrypto.subtle.importKey(...a); }, sign: (...a) => webcrypto.subtle.sign(...a) };
const NOW = 1_800_000_000_000;
const deps = (over) => ({ catalog: CAT, fetch: stripeMock, subtle, uuid: () => 'uuid-0000-0000-0000-0001', now: () => NOW, ...(over || {}) });
const worker = (over) => W.makeWorker(deps(over));
const co = (body, headers) => new Request(SITE + '/api/checkout', { method: 'POST',
  headers: { origin: SITE, 'content-type': 'application/json', ...(headers || {}) }, body: JSON.stringify(body) });
const J = async (r) => ({ s: r.status, b: await r.json() });

/* ---- checkout ---- */
calls = [];
let r = await J(await worker().fetch(co({ plan: 'individual-learner', idempotency_key: 'abcdef0123456789' }), baseEnv()));
ok(r.s === 200 && r.b.url === 'https://checkout.stripe.com/c/pay/cs_test_1', 'checkout happy path returns the hosted Checkout URL');
const c0 = calls[0];
ok(calls.length === 1 && c0.url === 'https://api.stripe.com/v1/checkout/sessions' && c0.init.method === 'POST', 'one POST to api.stripe.com checkout sessions');
ok(c0 && c0.init.headers.authorization === 'Bearer ' + SECRET, 'secret from env sent as Bearer');
ok(c0 && c0.init.headers['content-type'] === 'application/x-www-form-urlencoded', 'request is form-encoded');
const F = new URLSearchParams(c0 ? c0.init.body : '');
ok(F.get('line_items[0][price]') === 'price_TESTONLY' && F.get('mode') === 'subscription' && F.get('line_items[0][quantity]') === '1', 'price id and mode from env');
ok(F.get('success_url') === SITE + CAT.checkout.success_path + '&session_id={CHECKOUT_SESSION_ID}' && F.get('cancel_url') === SITE + CAT.checkout.cancel_path, 'success/cancel URLs from config');
ok(F.get('metadata[plan]') === 'individual-learner' && ![...F.keys()].some((k) => /email|customer|name/.test(k)), 'only the plan id travels as metadata');
ok(c0 && c0.init.headers['idempotency-key'] === 'checkout-individual-learner-abcdef0123456789', 'idempotency key sent to Stripe');
calls = [];
await worker().fetch(co({ plan: 'individual-learner', idempotency_key: 'abcdef0123456789' }), baseEnv());
await worker().fetch(co({ plan: 'individual-learner', idempotency_key: 'abcdef0123456789' }), baseEnv());
ok(calls.length === 2 && calls[0].init.headers['idempotency-key'] === calls[1].init.headers['idempotency-key'], 'a repeated click reuses the same idempotency key');
calls = [];
await worker().fetch(co({ plan: 'individual-learner' }), baseEnv());
ok(calls[0] && calls[0].init.headers['idempotency-key'] === 'checkout-individual-learner-uuid-0000-0000-0000-0001', 'no client key: a fresh uuid is used');
calls = [];
r = await J(await worker().fetch(co({ plan: 'individual-learner', success_url: 'https://evil.example/' }), baseEnv()));
ok(r.s === 200 && new URLSearchParams(calls[0].init.body).get('success_url').startsWith(SITE + '/'), 'a success_url in the request is ignored (no open redirect)');

const refusal = async (name, env, req, status, code, over) => {
  calls = [];
  const x = await J(await worker(over).fetch(req, env));
  ok(x.s === status && x.b.error === code && calls.length === 0, `${name}: ${status} ${code}, Stripe not called`);
};
let e = baseEnv(); delete e.STRIPE_SECRET_KEY;
await refusal('missing secret', e, co({ plan: 'individual-learner' }), 503, 'not_configured');
e = baseEnv(); e.STRIPE_SECRET_KEY = 'pk_test_' + 'X';
await refusal('publishable key as secret', e, co({ plan: 'individual-learner' }), 503, 'not_configured');
e = baseEnv(); delete e.STRIPE_PRICE_INDIVIDUAL_LEARNER;
await refusal('missing price id', e, co({ plan: 'individual-learner' }), 503, 'not_configured');
e = baseEnv(); delete e.STRIPE_MODE_INDIVIDUAL_LEARNER;
await refusal('missing mode', e, co({ plan: 'individual-learner' }), 503, 'not_configured');
e = baseEnv(); delete e.SITE_ORIGIN;
await refusal('missing SITE_ORIGIN', e, co({ plan: 'individual-learner' }), 503, 'not_configured');
e = baseEnv(); e.SITE_ORIGIN = 'http://academy.example';
await refusal('non-https SITE_ORIGIN', e, co({ plan: 'individual-learner' }), 503, 'not_configured');
await refusal('unknown plan', baseEnv(), co({ plan: 'gold-forever' }), 404, 'unknown_plan');
await refusal('plan as prototype key', baseEnv(), co({ plan: '__proto__' }), 404, 'unknown_plan');
await refusal('cross-origin (CSRF)', baseEnv(), co({ plan: 'individual-learner' }, { origin: 'https://evil.example' }), 403, 'origin');
await refusal('no Origin header', baseEnv(), new Request(SITE + '/api/checkout', { method: 'POST', headers: { 'content-type': 'application/json' }, body: '{"plan":"individual-learner"}' }), 403, 'origin');
await refusal('form post (CSRF simple request)', baseEnv(), co({ plan: 'individual-learner' }, { 'content-type': 'application/x-www-form-urlencoded' }), 415, 'content_type');
await refusal('bad idempotency key', baseEnv(), co({ plan: 'individual-learner', idempotency_key: 'a b' }), 400, 'idempotency_key');
await refusal('oversized body', baseEnv(), co({ plan: 'individual-learner', pad: 'x'.repeat(4000) }), 413, 'too_large');
await refusal('GET', baseEnv(), new Request(SITE + '/api/checkout', { method: 'GET' }), 405, 'method');
calls = [];
r = await J(await worker({ fetch: async () => new Response(JSON.stringify({ url: 'https://evil.example/pay' }), { status: 200 }) }).fetch(co({ plan: 'individual-learner' }), baseEnv()));
ok(r.s === 502 && r.b.error === 'stripe_bad_reply', 'a reply URL off checkout.stripe.com is refused');
r = await J(await worker({ fetch: async () => new Response('{}', { status: 402 }) }).fetch(co({ plan: 'individual-learner' }), baseEnv()));
ok(r.s === 502 && r.b.error === 'stripe_refused' && !JSON.stringify(r.b).includes(SECRET), 'a Stripe error is a 502 that never echoes the secret');
r = await worker().fetch(co({ plan: 'individual-learner' }), baseEnv());
ok(r.headers.get('cache-control') === 'no-store' && r.headers.get('x-content-type-options') === 'nosniff', 'API replies are no-store, nosniff');

/* ---- webhook ---- */
const sign = (payload, t, secret) => `t=${t},v1=${createHmac('sha256', secret || WHSEC).update(`${t}.${payload}`).digest('hex')}`;
const T = Math.floor(NOW / 1000);
const evt = (id, type, obj) => JSON.stringify({ id, type, data: { object: obj } });
const done = evt('evt_1', 'checkout.session.completed', { id: 'cs_test_1', mode: 'subscription', payment_status: 'paid', livemode: false,
  metadata: { plan: 'union-hall' }, customer_details: { email: 'someone@example.org', name: 'A Person' }, amount_total: 1 });
const wh = (payload, sig) => new Request(SITE + '/api/stripe-webhook', { method: 'POST', headers: sig === undefined ? {} : { 'stripe-signature': sig }, body: payload });
e = baseEnv();
subtleCalls = 0;
r = await J(await worker().fetch(wh(done, sign(done, T)), e));
ok(r.s === 200 && r.b.ok === true && subtleCalls === 1, 'webhook happy path verified through WebCrypto');
const stored = e.PAYMENTS_KV.m.get('session:cs_test_1');
ok(stored && JSON.stringify(Object.keys(JSON.parse(stored)).sort()) === JSON.stringify([...CAT.webhook.stored_fields].sort()), 'session record holds only the declared fields');
ok(stored && !/someone@|A Person|amount/.test(stored), 'no email, name or amount stored');
ok(e.PAYMENTS_KV.m.get('evt:evt_1') === '1', 'event id recorded for de-duplication');
e.PAYMENTS_KV.m.set('session:cs_test_1', 'SENTINEL');
r = await J(await worker().fetch(wh(done, sign(done, T + 5)), e));
ok(r.s === 200 && r.b.duplicate === true && e.PAYMENTS_KV.m.get('session:cs_test_1') === 'SENTINEL', 'a redelivered event is acknowledged and not re-applied (idempotent)');
e = baseEnv();
r = await J(await worker().fetch(wh(done, sign(done, T, 'whsec_' + 'b3RoZXI=')), e));
ok(r.s === 400 && r.b.error === 'signature_mismatch' && e.PAYMENTS_KV.m.size === 0, 'bad signature refused, nothing stored');
r = await J(await worker().fetch(wh(done.replace('union-hall', 'school-district'), sign(done, T)), e));
ok(r.s === 400 && r.b.error === 'signature_mismatch' && e.PAYMENTS_KV.m.size === 0, 'tampered payload refused');
r = await J(await worker().fetch(wh(done, sign(done, T - 301)), e));
ok(r.s === 400 && r.b.error === 'timestamp_outside_tolerance' && e.PAYMENTS_KV.m.size === 0, 'replay of an old signed event refused (tolerance 300 s)');
r = await J(await worker().fetch(wh(done, sign(done, T + 301)), e));
ok(r.s === 400 && r.b.error === 'timestamp_outside_tolerance', 'future-dated signature refused');
r = await J(await worker().fetch(wh(done), e));
ok(r.s === 400 && r.b.error === 'bad_signature_header', 'missing Stripe-Signature refused');
r = await J(await worker().fetch(wh(done, `t=${T},v0=${'0'.repeat(64)}`), e));
ok(r.s === 400 && r.b.error === 'bad_signature_header', 'only v1 signatures accepted');
const good = sign(done, T).split('v1=')[1];
r = await J(await worker().fetch(wh(done, `t=${T},v1=${'0'.repeat(64)},v1=${good}`), e));
ok(r.s === 200, 'any matching v1 among several is accepted (secret rotation)');
e = baseEnv(); delete e.STRIPE_WEBHOOK_SECRET;
r = await J(await worker().fetch(wh(done, sign(done, T)), e));
ok(r.s === 503 && r.b.error === 'not_configured', 'missing webhook secret: fail closed');
e = baseEnv(); delete e.PAYMENTS_KV;
r = await J(await worker().fetch(wh(done, sign(done, T)), e));
ok(r.s === 503 && r.b.error === 'not_configured', 'missing KV binding: fail closed (cannot de-duplicate)');
e = baseEnv();
const unk = evt('evt_2', 'checkout.session.completed', { id: 'cs_test_2', metadata: { plan: 'nope' } });
r = await J(await worker().fetch(wh(unk, sign(unk, T)), e));
ok(r.s === 400 && r.b.error === 'unknown_plan' && e.PAYMENTS_KV.m.size === 0, 'webhook for an unknown plan refused');
const other = evt('evt_3', 'invoice.paid', { id: 'in_1', customer_email: 'x@example.org' });
r = await J(await worker().fetch(wh(other, sign(other, T)), e));
ok(r.s === 200 && e.PAYMENTS_KV.m.size === 1 && e.PAYMENTS_KV.m.get('evt:evt_3') === '1', 'unhandled event types: only the event id is kept');
ok(W.timingSafeEqualHex('ab', 'ab') && !W.timingSafeEqualHex('ab', 'ac') && !W.timingSafeEqualHex('ab', 'abc'), 'constant-time compare: equal, differ, length');
ok(/d \|= a\.charCodeAt\(i\) \^ b\.charCodeAt\(i\)/.test(SRC) && !/mac === v|v === mac/.test(SRC), 'signature compare is xor-accumulate, not ===');

/* ---- routing ---- */
r = await J(await worker().fetch(new Request(SITE + '/api/other', { method: 'POST' }), baseEnv()));
ok(r.s === 404, 'unknown route 404');
ok(JSON.stringify(W.ROUTES) === JSON.stringify(['/api/checkout', '/api/stripe-webhook']), 'ROUTES = checkout + webhook');
ok(netCalls === 0, 'no test touched the network');

console.log(`payments: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
