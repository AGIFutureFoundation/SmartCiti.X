/* payments/worker.mjs - the one Cloudflare Worker: Stripe-hosted Checkout and its signed webhook.
 *
 * NOT LIVE. No Stripe account is connected to this deployment and nothing here has been
 * deployed. Every route FAILS CLOSED: a missing secret, price id, mode, origin or storage
 * binding is a refusal naming what is missing, never a default.
 *
 * Card data never touches this code: /api/checkout asks Stripe for a hosted Checkout
 * Session and returns only its checkout.stripe.com URL; the learner pays on Stripe's page.
 *
 *   POST /api/checkout        {plan, idempotency_key?} -> {url}
 *     - Origin must equal env.SITE_ORIGIN (CSRF); JSON only; body <= 2 KB
 *     - plan must be in the catalogue; price id from the catalogue or env[plan.price_env]
 *     - success/cancel URLs are SITE_ORIGIN + fixed catalogue paths (never from the request)
 *     - Idempotency-Key sent to Stripe (client key validated, else a random UUID)
 *     - rate limited per (HMAC-SHA256(RATE_LIMIT_SALT, client IP), plan): a token bucket in KV
 *       holding RATE_LIMIT_CHECKOUT_MAX tokens refilled over RATE_LIMIT_CHECKOUT_WINDOW_S; any of
 *       the three missing -> 503. The raw IP is never stored. KV is eventually consistent, so
 *       the limit is approximate across Cloudflare locations (a brake, not an exact quota).
 *   POST /api/stripe-webhook  Stripe-Signature: t=..,v1=..
 *     - HMAC-SHA256 over `${t}.${rawBody}` with STRIPE_WEBHOOK_SECRET (WebCrypto),
 *       constant-time compare, |now - t| <= tolerance, event id de-duplicated in KV
 *     - checkout.session.completed stores only {plan, payment_status, mode, livemode, at}
 *
 * Nothing is logged: no body, no header, no secret, no customer detail.
 */
import CATALOG from './catalog.mjs';

const JSON_HEADERS = {
  'content-type': 'application/json; charset=utf-8',
  'cache-control': 'no-store',
  'x-content-type-options': 'nosniff',
};
const CHECKOUT_MAX = 2048;
const WEBHOOK_MAX = 1 << 20;
const EVENT_TTL_S = 60 * 60 * 24 * 30;

function reply(status, body, extra) {
  return new Response(JSON.stringify(body), { status, headers: { ...JSON_HEADERS, ...(extra || {}) } });
}
const refuse = (status, code, detail, extra) => reply(status, { ok: false, error: code, detail }, extra);

async function readCapped(request, max) {
  const len = request.headers.get('content-length');
  if (len !== null && Number(len) > max) return null;
  const text = await request.text();
  if (new TextEncoder().encode(text).length > max) return null;
  return text;
}

function planById(catalog, id) {
  if (typeof id !== 'string') return null;
  for (const p of catalog.plans) if (p.id === id) return p;
  return null;
}

/* ---------------------------------------------------------- rate limit */
const hex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');

export function rateLimitConfig(env, rl) {
  const max = Number(env[rl.max_env]), win = Number(env[rl.window_env]), salt = env[rl.salt_env];
  if (!Number.isInteger(max) || max < 1 || max > 1000000) return null;
  if (!Number.isInteger(win) || win < 1 || win > 86400 * 30) return null;
  if (typeof salt !== 'string' || salt.length < 16) return null;
  return { max, win, salt };
}

export async function clientKey(ip, salt, subtle) {
  const enc = new TextEncoder();
  const key = await subtle.importKey('raw', enc.encode(salt), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return hex(await subtle.sign('HMAC', key, enc.encode(ip))).slice(0, 32);
}

/* A token bucket: capacity max, refilled at max/win tokens per second. Returns
   {ok:true} after taking one token, or {ok:false, retry} in whole seconds. */
export async function takeToken(kv, key, cfg, nowMs) {
  const rate = cfg.max / cfg.win;
  let st = null;
  try { st = JSON.parse(await kv.get(key)); } catch { st = null; }
  const now = nowMs / 1000;
  let tokens = cfg.max;
  if (st && Number.isFinite(st.t) && Number.isFinite(st.at) && st.at <= now)
    tokens = Math.min(cfg.max, st.t + (now - st.at) * rate);
  if (tokens < 1) return { ok: false, retry: Math.max(1, Math.ceil((1 - tokens) / rate)) };
  // KV refuses more than about one write per second to a key; a refused write is a refusal here
  // too (fail closed), never a free pass.
  try {
    await kv.put(key, JSON.stringify({ t: tokens - 1, at: now }), { expirationTtl: Math.max(60, Math.ceil(cfg.win * 2)) });
  } catch {
    return { ok: false, retry: 1 };
  }
  return { ok: true };
}

/* ------------------------------------------------------------ checkout */
export async function handleCheckout(request, env, deps) {
  const cat = deps.catalog;
  if (request.method !== 'POST') return refuse(405, 'method', 'POST only');
  const secret = env.STRIPE_SECRET_KEY;
  if (typeof secret !== 'string' || !/^(sk|rk)_(test|live)_[A-Za-z0-9]+$/.test(secret))
    return refuse(503, 'not_configured', 'STRIPE_SECRET_KEY is not set - payments are not live');
  const site = env.SITE_ORIGIN;
  let siteOrigin = null;
  try { siteOrigin = typeof site === 'string' ? new URL(site).origin : null; } catch { siteOrigin = null; }
  if (!siteOrigin || siteOrigin !== site || !siteOrigin.startsWith('https://'))
    return refuse(503, 'not_configured', 'SITE_ORIGIN is not an https origin');
  const origin = request.headers.get('origin');
  if (origin !== siteOrigin) return refuse(403, 'origin', 'cross-origin request refused');
  const ctype = (request.headers.get('content-type') || '').split(';')[0].trim().toLowerCase();
  if (ctype !== 'application/json') return refuse(415, 'content_type', 'application/json only');
  const raw = await readCapped(request, CHECKOUT_MAX);
  if (raw === null) return refuse(413, 'too_large', 'request body too large');
  let body;
  try { body = JSON.parse(raw); } catch { return refuse(400, 'bad_json', 'body is not JSON'); }
  if (!body || typeof body !== 'object' || Array.isArray(body)) return refuse(400, 'bad_json', 'body is not an object');
  const plan = planById(cat, body.plan);
  if (!plan) return refuse(404, 'unknown_plan', 'no such plan in the catalogue');
  const price = plan.price_id !== null ? plan.price_id : env[plan.price_env];
  if (typeof price !== 'string' || !/^price_[A-Za-z0-9]+$/.test(price))
    return refuse(503, 'not_configured', `${plan.price_env} is not set - ${cat.commercial_terms}`);
  const mode = env[plan.mode_env];
  if (mode !== 'payment' && mode !== 'subscription')
    return refuse(503, 'not_configured', `${plan.mode_env} must be payment or subscription`);
  const rlc = rateLimitConfig(env, cat.rate_limit);
  if (!rlc) return refuse(503, 'not_configured', 'rate limit is not configured (' + cat.rate_limit.max_env + ', '
    + cat.rate_limit.window_env + ', ' + cat.rate_limit.salt_env + ')');
  const kv = env[cat.rate_limit.kv_binding];
  if (!kv || typeof kv.get !== 'function' || typeof kv.put !== 'function')
    return refuse(503, 'not_configured', cat.rate_limit.kv_binding + ' binding is missing - cannot rate-limit');
  const ip = request.headers.get(cat.rate_limit.ip_header);
  if (typeof ip !== 'string' || ip.length < 2 || ip.length > 64) return refuse(400, 'client_ip', 'no client address');
  let key = body.idempotency_key;
  if (key === undefined) key = deps.uuid();
  if (typeof key !== 'string' || !/^[A-Za-z0-9-]{16,64}$/.test(key))
    return refuse(400, 'idempotency_key', 'idempotency_key must be 16-64 of [A-Za-z0-9-]');

  const bucket = 'rl:checkout:' + plan.id + ':' + await clientKey(ip, rlc.salt, deps.subtle);
  const tk = await takeToken(kv, bucket, rlc, deps.now());
  if (!tk.ok) return refuse(429, 'rate_limited', 'too many checkout attempts', { 'retry-after': String(tk.retry) });

  const form = new URLSearchParams();
  form.set('mode', mode);
  form.set('line_items[0][price]', price);
  form.set('line_items[0][quantity]', '1');
  form.set('success_url', siteOrigin + cat.checkout.success_path + '&session_id={CHECKOUT_SESSION_ID}');
  form.set('cancel_url', siteOrigin + cat.checkout.cancel_path);
  form.set('metadata[plan]', plan.id);
  let res;
  try {
    res = await deps.fetch(cat.checkout.stripe_api, {
      method: 'POST',
      headers: {
        authorization: 'Bearer ' + secret,
        'content-type': 'application/x-www-form-urlencoded',
        'idempotency-key': 'checkout-' + plan.id + '-' + key,
      },
      body: form.toString(),
    });
  } catch {
    return refuse(502, 'stripe_unreachable', 'Stripe could not be reached');
  }
  if (!res.ok) return refuse(502, 'stripe_refused', 'Stripe refused the session');
  let session;
  try { session = await res.json(); } catch { return refuse(502, 'stripe_bad_reply', 'Stripe reply was not JSON'); }
  const url = session && session.url;
  if (typeof url !== 'string' || !url.startsWith(cat.checkout.hosted_prefix))
    return refuse(502, 'stripe_bad_reply', 'reply carried no hosted Checkout URL');
  return reply(200, { ok: true, url });
}

/* ------------------------------------------------------------- webhook */

export function timingSafeEqualHex(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}

export function parseSignatureHeader(h) {
  if (typeof h !== 'string' || h.length > 4096) return null;
  let t = null;
  const v1 = [];
  for (const part of h.split(',')) {
    const i = part.indexOf('=');
    if (i < 0) continue;
    const k = part.slice(0, i).trim(), v = part.slice(i + 1).trim();
    if (k === 't' && /^\d{1,12}$/.test(v)) t = Number(v);
    if (k === 'v1' && /^[0-9a-f]{64}$/.test(v)) v1.push(v);
  }
  return t === null || v1.length === 0 ? null : { t, v1 };
}

export async function verifyStripeSignature(payload, header, secret, nowS, toleranceS, subtle) {
  const sig = parseSignatureHeader(header);
  if (!sig) return { ok: false, reason: 'bad_signature_header' };
  if (Math.abs(nowS - sig.t) > toleranceS) return { ok: false, reason: 'timestamp_outside_tolerance' };
  const enc = new TextEncoder();
  const key = await subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const mac = hex(await subtle.sign('HMAC', key, enc.encode(sig.t + '.' + payload)));
  let match = false;
  for (const v of sig.v1) if (timingSafeEqualHex(mac, v)) match = true;
  return match ? { ok: true, t: sig.t } : { ok: false, reason: 'signature_mismatch' };
}

export async function handleWebhook(request, env, deps) {
  const cat = deps.catalog;
  if (request.method !== 'POST') return refuse(405, 'method', 'POST only');
  const secret = env.STRIPE_WEBHOOK_SECRET;
  if (typeof secret !== 'string' || !/^whsec_[A-Za-z0-9+/=]+$/.test(secret))
    return refuse(503, 'not_configured', 'STRIPE_WEBHOOK_SECRET is not set - payments are not live');
  const kv = env[cat.webhook.kv_binding];
  if (!kv || typeof kv.get !== 'function' || typeof kv.put !== 'function')
    return refuse(503, 'not_configured', cat.webhook.kv_binding + ' binding is missing - cannot de-duplicate');
  const raw = await readCapped(request, WEBHOOK_MAX);
  if (raw === null) return refuse(413, 'too_large', 'payload too large');
  const v = await verifyStripeSignature(raw, request.headers.get('stripe-signature'), secret,
    Math.floor(deps.now() / 1000), cat.webhook.tolerance_s, deps.subtle);
  if (!v.ok) return refuse(400, v.reason, 'signature not verified');
  let ev;
  try { ev = JSON.parse(raw); } catch { return refuse(400, 'bad_json', 'payload is not JSON'); }
  if (!ev || typeof ev.id !== 'string' || !/^evt_[A-Za-z0-9]+$/.test(ev.id) || typeof ev.type !== 'string')
    return refuse(400, 'bad_event', 'event has no id or type');
  const evKey = 'evt:' + ev.id;
  if ((await kv.get(evKey)) !== null) return reply(200, { ok: true, duplicate: true });
  if (cat.webhook.handled.includes(ev.type)) {
    const s = ev.data && ev.data.object;
    if (!s || typeof s.id !== 'string' || !/^cs_[A-Za-z0-9_]+$/.test(s.id))
      return refuse(400, 'bad_event', 'session has no id');
    const plan = planById(cat, s.metadata && s.metadata.plan);
    if (!plan) return refuse(400, 'unknown_plan', 'session names no catalogue plan');
    const rec = { plan: plan.id, payment_status: String(s.payment_status), mode: String(s.mode),
      livemode: s.livemode === true, at: v.t };
    await kv.put('session:' + s.id, JSON.stringify(rec));
  }
  await kv.put(evKey, '1', { expirationTtl: EVENT_TTL_S });
  return reply(200, { ok: true });
}

/* -------------------------------------------------------------- router */
export function makeWorker(deps) {
  return {
    async fetch(request, env) {
      const path = new URL(request.url).pathname;
      if (path === deps.catalog.checkout.endpoint) return handleCheckout(request, env, deps);
      if (path === deps.catalog.webhook.endpoint) return handleWebhook(request, env, deps);
      return refuse(404, 'not_found', 'no such route');
    },
  };
}

export const ROUTES = [CATALOG.checkout.endpoint, CATALOG.webhook.endpoint];

export default makeWorker({
  catalog: CATALOG,
  fetch: (u, i) => fetch(u, i),
  subtle: globalThis.crypto && globalThis.crypto.subtle,
  uuid: () => crypto.randomUUID(),
  now: () => Date.now(),
});
