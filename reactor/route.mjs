/* reactor/route.mjs - POST /api/reactor/token: mint a short-lived, scoped Reactor JWT.
 *
 * NOT LIVE: nothing here has been deployed, and api.reactor.inc is unreachable from the
 * environment that wrote it - tested only against a mocked fetch (reactor/test.mjs).
 *
 * The API key is env.REACTOR_API_KEY: a Worker secret (`wrangler secret put REACTOR_API_KEY`) or,
 * for `wrangler dev`, cloudflare/worker/.dev.vars (gitignored). It is sent only to the upstream
 * token endpoint in the Reactor-API-Key header and never appears in a reply, a log or an error.
 * The browser gets back only {jwt}: a token scoped (authorization_details) to ONE model, a small
 * number of sessions and a short session length, all AUTHORED in reactor/registry/reactor.json.
 *
 * Fails closed: a missing key, origin, rate-limit setting or KV binding is a 503 naming it.
 * Rate-limited per HMAC(RATE_LIMIT_SALT, client IP) with the payments token bucket, passed in by
 * the Worker as deps.limiter (no import of payments/worker.mjs here, so no import cycle).
 * Nothing is logged.
 */
import CONFIG from './config.mjs';

const JSON_BASE = { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' };

function makeReply(apiHeaders) {
  const headers = { ...JSON_BASE };
  for (const h of apiHeaders) headers[h.key.toLowerCase()] = h.value;
  return (status, body, extra) => new Response(JSON.stringify(body), { status, headers: { ...headers, ...(extra || {}) } });
}

export const NOT_CONFIGURED = 'reactor: not configured - set ' + CONFIG.token.secret_env;

export function tokenRequestBody(cfg) {
  return {
    authorization_details: [{
      type: 'session',
      resources: { models: { match: [cfg.model] } },
      constraints: {
        max_sessions: cfg.token.constraints.max_sessions,
        max_session_duration_seconds: cfg.token.constraints.max_session_duration_seconds,
      },
    }],
  };
}

const JWT_RE = /^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*$/;

export async function handleReactorToken(request, env, deps) {
  const cfg = deps.reactor;
  const reply = makeReply(deps.api_headers);
  const refuse = (status, code, detail, extra) => reply(status, { ok: false, error: code, detail }, extra);
  if (request.method !== 'POST') return refuse(405, 'method', 'POST only');
  const key = env[cfg.token.secret_env];
  if (typeof key !== 'string' || key.length < 16 || key.length > 512 || /\s/.test(key))
    return refuse(503, 'not_configured', NOT_CONFIGURED);
  const site = env[cfg.token.origin_env];
  let siteOrigin = null;
  try { siteOrigin = typeof site === 'string' ? new URL(site).origin : null; } catch { siteOrigin = null; }
  if (!siteOrigin || siteOrigin !== site || !siteOrigin.startsWith('https://'))
    return refuse(503, 'not_configured', 'reactor: not configured - ' + cfg.token.origin_env + ' is not an https origin');
  if (request.headers.get('origin') !== siteOrigin) return refuse(403, 'origin', 'cross-origin request refused');
  const len = request.headers.get('content-length');
  if (len !== null && Number(len) > cfg.token.body_max_bytes) return refuse(413, 'too_large', 'request body too large');
  const raw = await request.text();
  if (new TextEncoder().encode(raw).length > cfg.token.body_max_bytes) return refuse(413, 'too_large', 'request body too large');
  const rl = cfg.rate_limit;
  const rlc = deps.limiter.rateLimitConfig(env, rl);
  if (!rlc) return refuse(503, 'not_configured', 'reactor: rate limit is not configured (' + rl.max_env + ', ' + rl.window_env + ', ' + rl.salt_env + ')');
  const kv = env[rl.kv_binding];
  if (!kv || typeof kv.get !== 'function' || typeof kv.put !== 'function')
    return refuse(503, 'not_configured', 'reactor: ' + rl.kv_binding + ' binding is missing - cannot rate-limit');
  const ip = request.headers.get(rl.ip_header);
  if (typeof ip !== 'string' || ip.length < 2 || ip.length > 64) return refuse(400, 'client_ip', 'no client address');
  const bucket = 'rl:reactor:' + await deps.limiter.clientKey(ip, rlc.salt, deps.subtle);
  const tk = await deps.limiter.takeToken(kv, bucket, rlc, deps.now());
  if (!tk.ok) return refuse(429, 'rate_limited', 'too many token requests', { 'retry-after': String(tk.retry) });

  let res;
  try {
    res = await deps.fetch(cfg.token.upstream, {
      method: 'POST',
      headers: { [cfg.token.key_header]: key, 'content-type': 'application/json' },
      body: JSON.stringify(tokenRequestBody(cfg)),
    });
  } catch {
    return refuse(502, 'reactor_unreachable', 'Reactor could not be reached');
  }
  if (!res.ok) return refuse(502, 'reactor_refused', 'Reactor refused the token request (' + res.status + ')');
  let out;
  try { out = await res.json(); } catch { return refuse(502, 'reactor_bad_reply', 'Reactor reply was not JSON'); }
  const jwt = out && out.jwt;
  if (typeof jwt !== 'string' || jwt.length > cfg.token.jwt_max_chars || !JWT_RE.test(jwt))
    return refuse(502, 'reactor_bad_reply', 'reply carried no JWT');
  return reply(200, { jwt });
}

export const REACTOR_ENDPOINT = CONFIG.token.endpoint;
export { CONFIG as REACTOR_CONFIG };
