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
ok(CAT.source_stamp === 'sha256:' + createHash('sha256').update(Buffer.concat([readFileSync(join(HERE, 'build.py')), readFileSync(join(ROOT, 'security/headers.json'))])).digest('hex'),
  'source_stamp is the sha256 of payments/build.py + security/headers.json');
const POLICY = JSON.parse(readFileSync(join(ROOT, 'security/headers.json'), 'utf8'));
ok(JSON.stringify(CAT.api_headers) === JSON.stringify(POLICY.api.map((h) => ({ key: h.key, value: h.value }))), 'catalogue api_headers = security/headers.json api (derived, not retyped)');
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
  STRIPE_PRICE_UNION_HALL: 'price_' + 'TESTHALL', STRIPE_MODE_UNION_HALL: 'payment',
  RATE_LIMIT_CHECKOUT_MAX: '1000', RATE_LIMIT_CHECKOUT_WINDOW_S: '60', RATE_LIMIT_SALT: 'test-salt-0123456789',
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
  headers: { origin: SITE, 'content-type': 'application/json', 'cf-connecting-ip': '203.0.113.7', ...(headers || {}) }, body: JSON.stringify(body) });
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

/* ---- rate limit (checkout) ---- */
ok(CAT.rate_limit && CAT.rate_limit.limits === 'set by the operator in env; no limit is policy in this repo', 'catalogue: limits are set by the operator, none is policy here');
ok(!/RATE_LIMIT_[A-Z_]+\s*\]?\s*(\?\?|\|\|)/.test(SRC) && !/\b(max|win)\s*=\s*\d/.test(SRC), 'no default limit hard-coded in the worker');
for (const k of ['RATE_LIMIT_CHECKOUT_MAX', 'RATE_LIMIT_CHECKOUT_WINDOW_S', 'RATE_LIMIT_SALT']) {
  e = baseEnv(); delete e[k];
  await refusal(`missing ${k}`, e, co({ plan: 'individual-learner' }), 503, 'not_configured');
}
e = baseEnv(); e.RATE_LIMIT_CHECKOUT_MAX = '0';
await refusal('limit 0', e, co({ plan: 'individual-learner' }), 503, 'not_configured');
e = baseEnv(); e.RATE_LIMIT_CHECKOUT_MAX = 'lots';
await refusal('non-numeric limit', e, co({ plan: 'individual-learner' }), 503, 'not_configured');
e = baseEnv(); e.RATE_LIMIT_SALT = 'short';
await refusal('short salt', e, co({ plan: 'individual-learner' }), 503, 'not_configured');
e = baseEnv(); delete e.PAYMENTS_KV;
await refusal('checkout without KV', e, co({ plan: 'individual-learner' }), 503, 'not_configured');
await refusal('no client IP', baseEnv(), new Request(SITE + '/api/checkout', { method: 'POST', headers: { origin: SITE, 'content-type': 'application/json' }, body: '{"plan":"individual-learner"}' }), 400, 'client_ip');
{
  const env = baseEnv(); env.RATE_LIMIT_CHECKOUT_MAX = '2'; env.RATE_LIMIT_CHECKOUT_WINDOW_S = '60';
  let now = NOW;
  const w = () => worker({ now: () => now });
  calls = [];
  const a1 = await w().fetch(co({ plan: 'individual-learner' }), env);
  const a2 = await w().fetch(co({ plan: 'individual-learner' }), env);
  const a3 = await w().fetch(co({ plan: 'individual-learner' }), env);
  ok(a1.status === 200 && a2.status === 200 && a3.status === 429 && calls.length === 2, 'limit 2: third attempt in the window is 429 and Stripe is not called');
  const b3 = await a3.json();
  ok(b3.error === 'rate_limited' && a3.headers.get('retry-after') === '30', '429 carries Retry-After computed from the refill rate');
  ok((await w().fetch(co({ plan: 'union-hall' }), env)).status === 200, 'another plan has its own bucket');
  ok((await w().fetch(co({ plan: 'individual-learner' }, { 'cf-connecting-ip': '198.51.100.9' }), env)).status === 200, 'another client address has its own bucket');
  now += 29_000;
  ok((await w().fetch(co({ plan: 'individual-learner' }), env)).status === 429, 'still limited before a token refills');
  now += 2_000;
  ok((await w().fetch(co({ plan: 'individual-learner' }), env)).status === 200, 'a token refills after window/max seconds');
  const keys = [...env.PAYMENTS_KV.m.keys()], vals = [...env.PAYMENTS_KV.m.values()].join(' ');
  const h = createHmac('sha256', env.RATE_LIMIT_SALT).update('203.0.113.7').digest('hex').slice(0, 32);
  ok(keys.includes('rl:checkout:individual-learner:' + h), 'bucket key = plan + HMAC-SHA256(salt, IP) (node oracle)');
  ok(!(keys.join(' ') + vals).includes('203.0.113.7') && !(keys.join(' ') + vals).includes('198.51.100.9'), 'the raw client IP is never stored');
}

{
  const env = baseEnv();
  env.PAYMENTS_KV = { get: async () => null, put: async () => { throw new Error('KV PUT failed: 429 Too Many Requests'); } };
  calls = [];
  const r1 = await worker().fetch(co({ plan: 'individual-learner' }), env);
  ok(r1.status === 429 && calls.length === 0, 'a refused KV write is a 429, never a free pass to Stripe');
}

/* ---- review wave 6 (REVIEW_FINDINGS 2, 3): the bucket fails closed and ignores future stamps ---- */
{
  const cfg = { max: 5, win: 60, salt: 'x'.repeat(16) };
  const kvThrowGet = { m: new Map(), get: async () => { throw new Error('KV unavailable'); }, put: async (k, v) => { kvThrowGet.m.set(k, v); } };
  let oks = 0;
  for (let i = 0; i < 50; i++) if ((await W.takeToken(kvThrowGet, 'b', cfg, NOW + i)).ok) oks++;
  ok(oks === 0, `a failing kv.get grants no token (${oks}/50; was 50/50 fail-open)`);
  const env = baseEnv();
  env.PAYMENTS_KV = { get: async () => { throw new Error('KV unavailable'); }, put: async () => {} };
  calls = [];
  const r1 = await worker().fetch(co({ plan: 'individual-learner' }), env);
  ok(r1.status === 429 && calls.length === 0, 'checkout with a failing kv.get is refused and Stripe is not called');
  const kv = kvMock();
  kv.m.set('b', JSON.stringify({ t: 0, at: NOW / 1000 + 0.5 }));
  const f = await W.takeToken(kv, 'b', cfg, NOW);
  ok(f.ok === false && JSON.parse(kv.m.get('b')).t === 0, 'an empty bucket stamped in the future stays empty (no refill to max)');
  kv.m.set('c', JSON.stringify({ t: 2, at: NOW / 1000 + 30 }));
  const g = await W.takeToken(kv, 'c', cfg, NOW);
  ok(g.ok === true && JSON.parse(kv.m.get('c')).t === 1, 'a future-stamped bucket keeps its own count (2 -> 1), not max');
  kv.m.set('d', '{not json');
  ok((await W.takeToken(kv, 'd', cfg, NOW)).ok === true && JSON.parse(kv.m.get('d')).t === cfg.max - 1, 'a corrupt bucket value starts a fresh bucket');
}

/* ---- review wave 6 (REVIEW_FINDINGS 1): every Worker reply carries the policy's api headers ---- */
{
  const want = POLICY.api.map((h) => [h.key.toLowerCase(), h.value]);
  const cases = [
    ['GET checkout', worker().fetch(new Request(SITE + '/api/checkout', { method: 'GET' }), {})],
    ['checkout happy path', worker().fetch(co({ plan: 'individual-learner' }), baseEnv())],
    ['checkout not configured', worker().fetch(co({ plan: 'individual-learner' }), {})],
    ['webhook not configured', worker().fetch(new Request(SITE + '/api/stripe-webhook', { method: 'POST', body: '{}' }), {})],
    ['unknown route', worker().fetch(new Request(SITE + '/api/nope'), {})],
  ];
  for (const [name, p] of cases) {
    const r = await p;
    ok(want.length > 0 && want.every(([k, v]) => r.headers.get(k) === v), `${name} (${r.status}) carries every headers.json api header`);
  }
}

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
/* ---- the Reactor token route shares this Worker (reactor/route.mjs; reactor/test.mjs holds its full suite) ---- */
{
  const RK = 'rk_test_' + 'FAKE_not_a_real_key';
  const rq = (h) => new Request(SITE + '/api/reactor/token', { method: 'POST', headers: { origin: SITE, 'content-type': 'application/json', 'cf-connecting-ip': '203.0.113.8', ...(h || {}) }, body: '{}' });
  const rkEnv = () => ({ ...baseEnv(), REACTOR_API_KEY: RK, RATE_LIMIT_REACTOR_MAX: '5', RATE_LIMIT_REACTOR_WINDOW_S: '60' });
  let up = [];
  const rkFetch = async (u, i) => { up.push({ u, i }); return new Response(JSON.stringify({ jwt: 'aaa.bbb.ccc' }), { status: 200 }); };
  const e0 = rkEnv(); delete e0.REACTOR_API_KEY;
  r = await J(await worker({ fetch: rkFetch }).fetch(rq(), e0));
  ok(r.s === 503 && r.b.detail === 'reactor: not configured - set REACTOR_API_KEY' && up.length === 0, 'reactor route: no REACTOR_API_KEY -> 503, no upstream call');
  const e1 = rkEnv(); delete e1.RATE_LIMIT_REACTOR_MAX;
  r = await J(await worker({ fetch: rkFetch }).fetch(rq(), e1));
  ok(r.s === 503 && /RATE_LIMIT_REACTOR_MAX/.test(r.b.detail) && up.length === 0, 'reactor route: rate limit not configured -> 503');
  const res = await worker({ fetch: rkFetch }).fetch(rq(), rkEnv());
  const body = await res.text();
  ok(res.status === 200 && body === JSON.stringify({ jwt: 'aaa.bbb.ccc' }) && up.length === 1 && up[0].i.headers['Reactor-API-Key'] === RK && !body.includes(RK),
    'reactor route: returns only {jwt}; key goes upstream in Reactor-API-Key and never back');
  ok(res.headers.get('content-security-policy') === CAT.api_headers.find((h) => h.key === 'Content-Security-Policy').value, 'reactor route: api CSP from the catalogue');
  ok(JSON.stringify(W.ALL_ROUTES) === JSON.stringify([...W.ROUTES, '/api/reactor/token']), 'ALL_ROUTES = ROUTES + /api/reactor/token');
}
ok(netCalls === 0, 'no test touched the network');

console.log(`payments: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
