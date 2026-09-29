// reactor/test.mjs - the Reactor pack: registry, token route (mocked fetch only - api.reactor.inc is
// unreachable from here), vendored SDK, the panel kit, and the secret scan.
// Prints `  ok <check>` per check; `FAIL <check>` at column 0 and exit 1 on any failure.
import { readFileSync, existsSync, statSync, readdirSync } from 'node:fs';
import { execFileSync, spawnSync } from 'node:child_process';
import { createHash, webcrypto } from 'node:crypto';
import { register } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const P = (p) => path.join(ROOT, p);
let fails = 0, n = 0;
function ok(cond, name) { n++; if (cond) console.log('  ok ' + name); else { fails++; console.log('FAIL ' + name); } }

const FAKE_KEY = 'rk_test_FAKE_not_a_real_key';   // obviously fake; never a real key in a test
const REG = JSON.parse(readFileSync(P('reactor/registry/reactor.json'), 'utf8'));
const { default: CONFIG } = await import(pathToFileURL(P('reactor/config.mjs')).href);
const HEADERS = JSON.parse(readFileSync(P('security/headers.json'), 'utf8'));
const route = await import(pathToFileURL(P('reactor/route.mjs')).href);
const pay = await import(pathToFileURL(P('payments/worker.mjs')).href);

/* ------------------------------------------------------------ registry */
{
  const { source_stamp, ...rest } = REG;
  const sortKeys = (v) => Array.isArray(v) ? v.map(sortKeys) : (v && typeof v === 'object')
    ? Object.fromEntries(Object.keys(v).sort().map((k) => [k, sortKeys(v[k])])) : v;
  // python json.dumps(indent=1, sort_keys=True, ensure_ascii=False)
  const py = (v, ind) => {
    const pad = ' '.repeat(ind + 1), end = ' '.repeat(ind);
    if (Array.isArray(v)) return v.length ? '[\n' + v.map((x) => pad + py(x, ind + 1)).join(',\n') + '\n' + end + ']' : '[]';
    if (v && typeof v === 'object') { const ks = Object.keys(v); return ks.length ? '{\n' + ks.map((k) => pad + JSON.stringify(k) + ': ' + py(v[k], ind + 1)).join(',\n') + '\n' + end + '}' : '{}'; }
    return JSON.stringify(v);
  };
  ok(createHash('sha256').update(py(sortKeys(rest), 0)).digest('hex') === source_stamp, 'registry: source_stamp recomputes');
  ok(JSON.stringify(CONFIG) === JSON.stringify(REG), 'registry: config.mjs is the same object as reactor.json');
  ok(REG.models.some((m) => m.model_name === REG.model), 'registry: the configured model is one of the recorded npm models');
  const CAT = JSON.parse(readFileSync(P('reactor/catalogue_npm.json'), 'utf8'));
  const fromCat = CAT.packages.flatMap((p) => p.model_names.map((mn) => mn + '|' + p.npm_package + '@' + p.npm_version + '|' + p.npm_license + '|' + p.npm_integrity));
  ok(JSON.stringify(REG.models.map((m) => m.model_name + '|' + m.npm_package + '@' + m.npm_version + '|' + m.npm_license + '|' + m.npm_integrity)) === JSON.stringify(fromCat)
    && CAT.packages.length >= 12 && CAT.packages.every((p) => /^@reactor-models\/[a-z0-9-]+$/.test(p.npm_package) && /^sha512-/.test(p.npm_integrity)),
    'registry: models are exactly the npm @reactor-models snapshot (name, package, version, licence, integrity)');
  ok(REG.default_model === 'reactor/lingbot-world-2' && REG.models.some((m) => m.model_name === REG.default_model) && /REACTOR_MODEL=/.test(REG.model_select),
    'registry: operator-selectable model with a catalogue default');
  ok(REG.models.find((m) => m.model_name === REG.model).bridge_ready === true
    && REG.models.every((m) => m.bridge_ready === m.wire_commands.includes('set_prompt')), 'registry: the selected model is bridge_ready (sends set_prompt)');
  ok(REG.notes.includes('minimax: not found in the @reactor-models catalogue (npm, ' + CAT.fetched + ')') && !REG.models.some((m) => /minimax/i.test(m.model_name + m.npm_package)),
    'registry: minimax recorded as a not-found note, never as a model');
  const ORB = JSON.parse(readFileSync(P('orbis/registry/orbis.json'), 'utf8'));
  ok(ORB.runners.every((r) => REG.models.some((m) => m.model_name === r.model && m.orbis_runner === r.path && existsSync(P(r.path))))
    && REG.models.filter((m) => m.orbis_runner).length === ORB.runners.length && REG.models.find((m) => m.model_name === 'reactor/visko-orbis-dynamic').orbis_runner === null,
    'registry: orbis/ runners linked where model ids line up (helios, visko-orbis-stable); dynamic has none');
  ok(REG.operator.some((l) => /Credits are spent only by the DEPLOYED Worker/.test(l) && /blocked/.test(l)), 'registry: operator steps say credits are spent only via the deployed Worker');
  const c = REG.token.constraints;
  ok(Number.isInteger(c.max_sessions) && c.max_sessions >= 1 && c.max_sessions <= 5
    && Number.isInteger(c.max_session_duration_seconds) && c.max_session_duration_seconds >= 30 && c.max_session_duration_seconds <= 900,
    'registry: token scope is small (<=5 sessions, <=900 s)');
  ok(REG.session.max_seconds === c.max_session_duration_seconds && REG.session.one_at_a_time === true && REG.session.disconnect_on_hidden === true,
    'registry: client session cap equals the token constraint; one at a time; disconnect on hide');
  const mdl = REG.models.find((m) => m.model_name === REG.model);
  ok(Object.values(REG.bridge.commands).every((b) => mdl.wire_commands.includes(b.command)) && Object.keys(REG.bridge.commands).length > 0,
    'registry: every bridge command is a wire command of the selected model');
  ok(REG.live === false && /not real footage/.test(REG.honesty.model_output) && /not live/i.test(REG.honesty.not_live)
    && /unreachable/.test(REG.honesty.untested), 'registry: honesty says model output / not live / untested');
  const PC = (await import(pathToFileURL(P('payments/catalog.mjs')).href)).default.rate_limit;
  ok(REG.rate_limit.ip_header === PC.ip_header && REG.rate_limit.salt_env === PC.salt_env && REG.rate_limit.kv_binding === PC.kv_binding
    && REG.rate_limit.max_env !== PC.max_env && REG.rate_limit.window_env !== PC.window_env, 'registry: rate limit reuses the payments salt, KV and IP header with its own max/window');
}

/* ------------------------------------------------------------- route */
function kvMem() {
  const m = new Map();
  return { m, async get(k) { return m.has(k) ? m.get(k) : null; }, async put(k, v) { m.set(k, v); } };
}
const GOOD_ENV = () => ({ REACTOR_API_KEY: FAKE_KEY, SITE_ORIGIN: 'https://example.test', RATE_LIMIT_REACTOR_MAX: '2',
  RATE_LIMIT_REACTOR_WINDOW_S: '60', RATE_LIMIT_SALT: 'salt-salt-salt-salt', PAYMENTS_KV: kvMem() });
const JWT = 'eyJhbGciOiJFUzI1NiJ9.eyJzdWIiOiJ4In0.c2ln';
function deps(fetchImpl) {
  const calls = [];
  return { calls, d: { reactor: CONFIG, api_headers: HEADERS.api, subtle: webcrypto.subtle, now: () => 1_000_000,
    limiter: { rateLimitConfig: pay.rateLimitConfig, clientKey: pay.clientKey, takeToken: pay.takeToken },
    fetch: async (u, i) => { calls.push({ u, i }); return fetchImpl(u, i); } } };
}
const upstreamOK = async () => new Response(JSON.stringify({ jwt: JWT, extra: 'account-detail' }), { status: 200 });
function req(opts = {}) {
  const h = { origin: 'https://example.test', 'content-type': 'application/json', 'cf-connecting-ip': '203.0.113.9', ...(opts.headers || {}) };
  return new Request('https://example.test/api/reactor/token', { method: opts.method || 'POST', headers: h,
    body: (opts.method || 'POST') === 'POST' ? (opts.body === undefined ? '{}' : opts.body) : undefined });
}
// a thrown error is a result too (status 0), so a crashing route FAILs the named check instead of aborting the suite
const call = async (env, r, f = upstreamOK) => {
  const x = deps(f);
  try { const res = await route.handleReactorToken(r, env, x.d); const t = await res.text(); return { res, t, calls: x.calls, j: JSON.parse(t) }; }
  catch (e) { return { res: { status: 0, headers: new Headers() }, t: String(e), calls: x.calls, j: {} }; }
};

{
  const env = GOOD_ENV(); delete env.REACTOR_API_KEY;
  const r = await call(env, req());
  ok(r.res.status === 503 && r.j.detail === 'reactor: not configured - set REACTOR_API_KEY' && r.calls.length === 0, 'route: no key -> 503 "reactor: not configured - set REACTOR_API_KEY", no upstream call');
}
{ const r = await call(GOOD_ENV(), req({ method: 'GET' })); ok(r.res.status === 405 && r.calls.length === 0, 'route: GET -> 405'); }
{ const r = await call(GOOD_ENV(), req({ headers: { origin: 'https://evil.test' } })); ok(r.res.status === 403 && r.calls.length === 0, 'route: foreign Origin -> 403, no upstream call'); }
{ const env = GOOD_ENV(); env.SITE_ORIGIN = 'http://example.test'; const r = await call(env, req()); ok(r.res.status === 503 && r.calls.length === 0, 'route: non-https SITE_ORIGIN -> 503'); }
{ const env = GOOD_ENV(); delete env.RATE_LIMIT_REACTOR_MAX; const r = await call(env, req()); ok(r.res.status === 503 && /RATE_LIMIT_REACTOR_MAX/.test(r.j.detail) && r.calls.length === 0, 'route: missing rate-limit env -> 503 naming it'); }
{ const env = GOOD_ENV(); delete env.PAYMENTS_KV; const r = await call(env, req()); ok(r.res.status === 503 && /PAYMENTS_KV/.test(r.j.detail) && r.calls.length === 0, 'route: missing KV binding -> 503'); }
{ const r = await call(GOOD_ENV(), req({ body: 'x'.repeat(400) })); ok(r.res.status === 413 && r.calls.length === 0, 'route: oversized body -> 413'); }
{
  const env = GOOD_ENV();
  const r = await call(env, req());
  const c = r.calls[0];
  const body = c ? JSON.parse(c.i.body) : null;
  const ad = body && body.authorization_details && body.authorization_details[0];
  ok(r.res.status === 200 && JSON.stringify(Object.keys(r.j)) === '["jwt"]' && r.j.jwt === JWT, 'route: happy path returns only {jwt} (upstream extras dropped)');
  ok(r.calls.length === 1 && c.u === 'https://api.reactor.inc/tokens' && c.i.method === 'POST' && c.i.headers['Reactor-API-Key'] === FAKE_KEY,
    'route: upstream is POST api.reactor.inc/tokens with the Reactor-API-Key header');
  ok(ad && ad.type === 'session' && JSON.stringify(ad.resources.models.match) === JSON.stringify([REG.model])
    && ad.constraints.max_sessions === REG.token.constraints.max_sessions
    && ad.constraints.max_session_duration_seconds === REG.token.constraints.max_session_duration_seconds && body.authorization_details.length === 1,
    'route: token is scoped to the one registry model with the registry constraints');
  ok(!r.t.includes(FAKE_KEY) && ![...r.res.headers.values()].some((v) => v.includes(FAKE_KEY)), 'route: the key never appears in the reply body or headers');
  const csp = HEADERS.api.find((h) => h.key === 'Content-Security-Policy').value;
  ok(r.res.headers.get('content-security-policy') === csp && r.res.headers.get('cache-control') === 'no-store', 'route: reply carries security/headers.json api CSP + no-store');
  ok([...env.PAYMENTS_KV.m.keys()].every((k) => k.startsWith('rl:reactor:') && !k.includes('203.0.113.9')), 'route: rate-limit bucket keyed by hashed IP, raw IP never stored');
}
{
  const env = GOOD_ENV();
  const a = await call(env, req()), b = await call(env, req()), c = await call(env, req());
  ok(a.res.status === 200 && b.res.status === 200 && c.res.status === 429 && Number(c.res.headers.get('retry-after')) >= 1 && c.calls.length === 0,
    'route: third request inside the window -> 429 with retry-after, no upstream call');
}
{ const r = await call(GOOD_ENV(), req(), async () => new Response(JSON.stringify({ error: 'bad key ' + FAKE_KEY }), { status: 401 }));
  ok(r.res.status === 502 && !r.t.includes(FAKE_KEY) && !r.t.includes('bad key'), 'route: upstream 401 -> 502, upstream text and key not echoed'); }
{ const r = await call(GOOD_ENV(), req(), async () => { throw new Error('blocked'); }); ok(r.res.status === 502 && r.j.error === 'reactor_unreachable', 'route: upstream unreachable -> 502'); }
{ const r = await call(GOOD_ENV(), req(), async () => new Response(JSON.stringify({ jwt: 'not a jwt <script>' }), { status: 200 })); ok(r.res.status === 502, 'route: malformed jwt -> 502'); }
{
  const w = readFileSync(P('payments/worker.mjs'), 'utf8');
  const wired = /reactor\/route\.mjs/.test(w);
  if (wired) {
    const worker = pay.makeWorker({ catalog: (await import(pathToFileURL(P('payments/catalog.mjs')).href)).default, fetch: upstreamOK,
      subtle: webcrypto.subtle, uuid: () => 'x', now: () => 1_000_000 });
    const env = GOOD_ENV(); delete env.REACTOR_API_KEY;
    const res = await worker.fetch(req(), env); const j = await res.json();
    ok(res.status === 503 && j.detail === route.NOT_CONFIGURED, 'worker: /api/reactor/token routed to reactor/route.mjs and fails closed');
  } else console.log('  -- worker wiring pending (payments/worker.mjs not yet routed; NEEDS after 7A LANDED)');
}

/* ------------------------------------------------------------- vendor */
{
  const r = spawnSync('python3', [P('reactor/fetch_reactor.py'), '--check'], { encoding: 'utf8' });
  ok(r.status === 0 && /^ok /.test(r.stdout), 'vendor: fetch_reactor.py --check (every file sha512 matches manifest; integrity = registry pin)');
  const man = JSON.parse(readFileSync(P('web/vendor/reactor/manifest.json'), 'utf8'));
  ok(man.integrity === REG.sdk.integrity && man.license === 'Apache-2.0' && man.files['index.js'].provenance === 'UPSTREAM'
    && Object.values(REG.sdk.import_map).every((s) => man.files[s] && man.files[s].provenance === 'AUTHORED'), 'vendor: manifest pins the SDK integrity; shims are marked AUTHORED');
}
{
  // Load the vendored SDK exactly as the import map resolves it, in Node: proves every bare import is mapped
  // and the module evaluates with the shims (no network: nothing connects).
  const base = pathToFileURL(P('web/vendor/reactor/')).href;
  const map = Object.fromEntries(Object.entries(REG.sdk.import_map).map(([k, v]) => [k, new URL(v, base).href]));
  const hook = `const M=${JSON.stringify(map)};export async function resolve(s,c,n){if(Object.hasOwn(M,s))return{url:M[s],shortCircuit:true};return n(s,c);}`;
  register('data:text/javascript,' + encodeURIComponent(hook));
  let good = false, why = '';
  try {
    const sdk = await import(new URL('index.js', base).href);
    const r = new sdk.Reactor({ modelName: REG.model });
    good = typeof r.connect === 'function' && typeof r.sendCommand === 'function' && typeof r.getSchema === 'function'
      && typeof r.uploadFile === 'function' && r.getStatus() === 'disconnected';
  } catch (e) { why = String(e && e.message || e); }
  ok(good, 'vendor: SDK module loads through the import map + shims and constructs a disconnected Reactor' + (why ? ' (' + why + ')' : ''));
}

/* ---------------------------------------------------------------- kit */
{
  const html = execFileSync('python3', ['-c', 'import sys; sys.path.insert(0,"web"); import reactorkit as r; print(r.reactor_panel("./")); print("@@"); print(r.reactor_import_entries("./"))'], { cwd: ROOT, encoding: 'utf8' });
  const [panel, entries] = html.split('@@');
  ok((panel.match(/id="rk-panel"/g) || []).length === 1 && panel.includes('Holodeck live view (Reactor)'), 'kit: one panel titled "Holodeck live view (Reactor)"');
  ok(!/<input|<textarea|contenteditable|prompt\(/i.test(panel) && !/api[_ -]?key['"]?\s*:/i.test(panel), 'kit: no field that could take a key');
  ok(!/type="module"|modulepreload|localStorage|sessionStorage|indexedDB/.test(panel), 'kit: no module script, preload or storage at load (SDK loads only on Connect)');
  ok(/aria-expanded="false"/.test(panel) && /class="rk-card" id="rk-card" hidden/.test(panel), 'kit: off by default (card hidden)');
  ok(panel.includes('Reactor: off - no token endpoint configured') && /res\.status === 404 \|\| !j/.test(panel), 'kit: shows "Reactor: off - no token endpoint configured" when the endpoint is absent');
  ok(Object.values(REG.honesty).every((t) => panel.includes(t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'))), 'kit: every honesty line is on the panel');
  ok(panel.includes('REACTOR_API_KEY') && panel.includes('.dev.vars'), 'kit: tells the reader where the key goes (Worker secret / .dev.vars)');
  ok(/declares\(c\.command\)/.test(panel) && /getCapabilities\(\)/.test(panel) && /getSchema\(\)/.test(panel), 'kit: commands are gated on the runtime schema/capabilities');
  ok(/visibilitychange/.test(panel) && /max_seconds \* 1000/.test(panel) && /if \(reactor \|\| st === 'connecting'\) return/.test(panel), 'kit: disconnect on hide, session cap, one session at a time');
  ok(Object.keys(REG.sdk.import_map).every((k) => entries.includes(JSON.stringify(k) + ':')), 'kit: import-map entries cover every bare SDK import');
}

/* ------------------------------------------- kit behaviour (node:vm, fake DOM + fake SDK) */
async function runKit(fetchImpl, caps) {
  const { default: vm } = await import('node:vm');
  const html = execFileSync('python3', ['-c', 'import sys; sys.path.insert(0,"web"); import reactorkit as r; print(r.reactor_panel("./"))'], { cwd: ROOT, encoding: 'utf8' });
  const js = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>')).replace('import(CFG.sdk)', '__import(CFG.sdk)');
  const els = {}, listeners = {}, winL = {}, events = [], made = [], imports = [];
  const el = (id) => els[id] || (els[id] = { id, textContent: '', className: '', hidden: id === 'rk-card', disabled: false, classList: { remove() {} },
    setAttribute() {}, addEventListener(t, f) { listeners[id + ':' + t] = f; }, play: () => Promise.resolve(), appendChild() {} });
  class FakeReactor {
    constructor(o) { this.o = o; this.h = {}; this.sent = []; this.disc = 0; made.push(this); }
    on(e, f) { this.h[e] = f; } connect() { setTimeout(() => this.h.statusChanged('ready'), 0); return Promise.resolve(); }
    disconnect() { this.disc++; return Promise.resolve(); } getCapabilities() { return { commands: caps.map((name) => ({ name })) }; }
    getSchema() { return undefined; } sendCommand(c, d) { this.sent.push([c, d]); return Promise.resolve(); } uploadFile() { return Promise.resolve({}); }
  }
  const doc = { hidden: false, getElementById: el, addEventListener(t, f) { listeners['doc:' + t] = f; } };
  const ctx = { document: doc, window: null, fetch: fetchImpl, setTimeout, clearTimeout, Promise, JSON, String, Math, Object, Array, isFinite,
    MediaStream: class {}, CustomEvent: class { constructor(n, o) { this.type = n; this.detail = o.detail; } },
    __import: (u) => { imports.push(u); return Promise.resolve({ Reactor: FakeReactor }); } };
  ctx.window = { dispatchEvent: (e) => events.push([e.type, e.detail]), addEventListener(t, f) { winL[t] = f; } };
  vm.createContext(ctx); vm.runInContext(js, ctx);
  const tick = () => new Promise((r) => setTimeout(r, 5));
  return { els, listeners, events, made, imports, kit: ctx.window.ReactorKit, doc, tick };
}
const jsonRes = (status, body) => ({ status, ok: status >= 200 && status < 300, headers: { get: () => '7' }, text: async () => typeof body === 'string' ? body : JSON.stringify(body) });
{
  const k = await runKit(async () => jsonRes(404, '<html>not found</html>'), []);
  k.listeners['rk-connect:click'](); for (let i = 0; i < 4; i++) await k.tick();
  ok(k.els['rk-status'].textContent === 'Reactor: off - no token endpoint configured' && k.kit.status() === 'off' && k.imports.length === 0,
    'kit: no endpoint -> "Reactor: off - no token endpoint configured", status off, SDK never imported');
}
{
  const k = await runKit(async () => jsonRes(503, { ok: false, error: 'not_configured', detail: 'reactor: not configured - set REACTOR_API_KEY' }), []);
  k.listeners['rk-connect:click'](); for (let i = 0; i < 4; i++) await k.tick();
  ok(/reactor: not configured - set REACTOR_API_KEY/.test(k.els['rk-status'].textContent) && k.kit.status() === 'error' && k.imports.length === 0,
    'kit: Worker 503 shows its detail and imports nothing');
}
{
  const k = await runKit(async (u, i) => { k0.req = [u, i]; return jsonRes(200, { jwt: 'a.b.c' }); }, ['set_prompt', 'start']);
  var k0 = k;
  k.kit.setContext({ place: 'Orleans Parish', time_of_day: 'noon', path: 'Electrical', lesson: 'x'.repeat(200) });
  k.listeners['rk-connect:click'](); k.listeners['rk-connect:click']();
  for (let i = 0; i < 8; i++) await k.tick();
  const r = k.made[0];
  ok(k.made.length === 1 && r.o.modelName === REG.model && r.o.jwt === 'a.b.c' && k.imports.length === 1 && k.imports[0] === './vendor/reactor/index.js',
    'kit: Connect imports the vendored SDK once and builds one Reactor for the registry model with the minted jwt');
  ok(k0.req[0] === './../api/reactor/token' && k0.req[1].method === 'POST' && !/key/i.test(JSON.stringify(k0.req[1])), 'kit: token request is a same-site POST that carries no key');
  const prompt = r.sent.find((x) => x[0] === 'set_prompt');
  ok(prompt && prompt[1].prompt === 'A walk through Orleans Parish, seen by an apprentice on the Electrical path studying ' + 'x'.repeat(80) + '.',
    'kit: bridge prompt from typed context (bad enum dropped, lesson capped at 80)');
  ok(r.sent.some((x) => x[0] === 'start') && !r.sent.some((x) => x[0] === 'set_image'), 'kit: start sent; set_image not sent without a reference image');
  k.kit.move('forward', true);
  await k.tick();
  ok(!r.sent.some((x) => x[0] === 'set_move_longitudinal'), 'kit: an undeclared command (set_move_longitudinal) is never sent');
  k.doc.hidden = true; k.listeners['doc:visibilitychange'](); await k.tick();
  ok(r.disc === 1 && k.kit.status() === 'disconnected', 'kit: hiding the tab disconnects');
  ok(k.events.some((e) => e[0] === 'reactorkit:commands') && k.events.some((e) => e[0] === 'reactorkit:status'), 'kit: emits reactorkit:status and reactorkit:commands');
}

/* ------------------------------------------------------ mounted pages */
for (const page of ['web/trade_craft_parishes.html']) {
  if (!existsSync(P(page)) || !readFileSync(P(page), 'utf8').includes('id="rk-panel"')) { console.log('  -- ' + page + ': reactor panel not mounted'); continue; }
  const h = readFileSync(P(page), 'utf8');
  const maps = h.match(/<script type="importmap">([\s\S]*?)<\/script>/g) || [];
  let imports = {};
  try { imports = JSON.parse(maps[0].replace(/<\/?script[^>]*>/g, '')).imports; } catch { imports = {}; }
  ok(maps.length === 1 && (h.match(/id="rk-panel"/g) || []).length === 1
    && Object.entries(REG.sdk.import_map).every(([k, v]) => imports[k] === './vendor/reactor/' + v),
    `${page}: one panel, and the page's single import map resolves every SDK bare import to the vendored shims`);
  ok(/data-rk-bridge/.test(h) && /ReactorKit\.setContext\(\{place:/.test(h) && !/rk_[A-Za-z0-9]{20,}/.test(h), `${page}: world bridge sends the shown place; no key on the page`);
}

/* -------------------------------------------------------- secret scan */
const KEY_RE = /rk_[A-Za-z0-9]{32,}/;
// an assignment with a real-looking value: 20+ key characters that are not a documented placeholder
const ASSIGN_RE = /REACTOR_API_KEY\s*[=:]\s*["']?(?![^"'\s]*(?:your|here|example|FAKE|placeholder|xxxx))[A-Za-z0-9_\-]{20,}/i;
export function scanFiles(root, files) {
  const hits = [];
  for (const f of files) {
    const p = path.join(root, f);
    if (!existsSync(p) || !statSync(p).isFile()) continue;
    const b = readFileSync(p);
    if (b.includes(0)) continue;          // binary (fonts, wasm, images)
    const t = b.toString('utf8');
    if (KEY_RE.test(t)) hits.push(f + ' (rk_ key pattern)');
    if (ASSIGN_RE.test(t)) hits.push(f + ' (REACTOR_API_KEY assignment)');
  }
  return hits;
}
{
  const git = (...a) => execFileSync('git', a, { cwd: ROOT, encoding: 'utf8' });
  // In a git checkout: every tracked or committable file. Outside one (a git archive, where
  // there is nothing to ask git): EVERY file in the tree - stricter, since nothing is ignored.
  const inGit = spawnSync('git', ['rev-parse', '--is-inside-work-tree'], { cwd: ROOT, encoding: 'utf8' }).stdout.trim() === 'true';
  const walk = (d, out = []) => { for (const e of readdirSync(path.join(ROOT, d), { withFileTypes: true })) { const r = d ? d + '/' + e.name : e.name; if (e.name === '.git') continue; if (e.isDirectory()) walk(r, out); else if (e.isFile()) out.push(r); } return out; };
  const files = inGit ? [...git('ls-files', '-z').split('\0'), ...git('ls-files', '-z', '--others', '--exclude-standard').split('\0')].filter(Boolean) : walk('');
  const hits = scanFiles(ROOT, files);
  ok(hits.length === 0, 'secrets: no tracked or committable file holds an rk_ key or a REACTOR_API_KEY assignment' + (hits.length ? ': ' + hits.join(', ') : ''));
  ok(!files.some((f) => path.basename(f) === '.dev.vars'), 'secrets: no .dev.vars is tracked or committable');
  const ig = inGit ? spawnSync('git', ['check-ignore', '-q', 'cloudflare/worker/.dev.vars'], { cwd: ROOT }).status === 0
    : readFileSync(P('.gitignore'), 'utf8').split('\n').map((l) => l.trim()).includes('**/.dev.vars');
  ok(ig, 'secrets: cloudflare/worker/.dev.vars is gitignored');
  const sh = readFileSync(P('.github/assemble_site.sh'), 'utf8');
  const cps = sh.split('\n').filter((l) => /^\s*(cp|rsync)\b/.test(l));
  ok(cps.length > 0 && cps.every((l) => !/cloudflare|\.dev\.vars|\s\.\/?\s|\s\.\/?$/.test(l)) && !/\.dev\.vars/.test(sh),
    'secrets: assemble_site copies nothing from cloudflare/ or the repo root wholesale (never ships .dev.vars)');
  // the scanner itself must catch a planted key (self-test; the planted value is built at run time)
  const planted = 'rk_' + 'A1b2C3d4'.repeat(5);
  ok(KEY_RE.test('x=' + planted) && ASSIGN_RE.test('REACTOR_API_KEY=' + planted) && !ASSIGN_RE.test('REACTOR_API_KEY=...') && !ASSIGN_RE.test('REACTOR_API_KEY=rk_your_api_key_here'), 'secrets: scanner catches a planted key and an assignment, ignores the docs placeholder');
}

console.log(fails ? `FAIL reactor: ${fails} of ${n} checks failed` : `reactor: all ${n} checks passed`);
process.exit(fails ? 1 : 0);
