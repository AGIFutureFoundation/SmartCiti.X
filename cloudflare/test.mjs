/* cloudflare/test.mjs - the Cloudflare deploy config, checked. Network-free; nothing is deployed.
 * Recompute, never re-read: headers are held to vercel.json, routes to the payments Worker's
 * own ROUTES, file hashes to the bytes on disk. Prints `  ok ` per check, FAIL at column 0. */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join, relative } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok ' + m); } else { fail++; console.log('FAIL ' + m); } };
globalThis.fetch = async () => { throw new Error('network is forbidden in cloudflare/test.mjs'); };
const read = (p) => readFileSync(join(HERE, p), 'utf8');
console.log('cloudflare/test.mjs');

/* ---- config parses (python tomllib: a real TOML parser, not ours) ---- */
const toml = (p) => JSON.parse(execFileSync('python3', ['-c',
  'import sys,json,tomllib;print(json.dumps(tomllib.load(open(sys.argv[1],"rb"))))', join(HERE, p)], { encoding: 'utf8' }));
let PG = null, WK = null;
try { PG = toml('wrangler.toml'); } catch { PG = null; }
try { WK = toml('worker/wrangler.toml'); } catch { WK = null; }
ok(PG !== null, 'wrangler.toml (Pages) parses as TOML');
ok(WK !== null, 'worker/wrangler.toml parses as TOML');
ok(PG && PG.pages_build_output_dir === '../_site' && PG.name === 'smartcitix', 'Pages serves ../_site (assemble_site.sh output)');
ok(WK && WK.main === '../../payments/worker.mjs' && statSync(join(HERE, 'worker', WK.main)).isFile(), 'Worker main resolves to payments/worker.mjs');
ok(WK && WK.workers_dev === false, 'Worker not exposed on workers.dev');
ok(PG && Array.isArray(PG.services) && PG.services.length === 1 && PG.services[0].binding === 'PAYMENTS' && PG.services[0].service === WK.name,
  'Pages service binding PAYMENTS names the Worker');
const REG = JSON.parse(read('registry/cloudflare.json'));
ok(WK && Array.isArray(WK.kv_namespaces) && WK.kv_namespaces.length === 1 && WK.kv_namespaces[0].binding === REG.kv_binding, 'KV binding named');
ok(REG.deployed === false && /nothing is deployed/.test(REG.status), 'registry says nothing is deployed');

/* ---- no secrets or ids committed ---- */
const files = [];
const walk = (d) => { for (const f of readdirSync(d)) { const p = join(d, f); if (statSync(p).isDirectory()) walk(p); else files.push(p); } };
walk(HERE);
const ALL = files.filter((p) => !p.endsWith('test.mjs')).map((p) => [relative(HERE, p), readFileSync(p, 'utf8')]);
const allText = ALL.map((x) => x[1]).join('\n');
const tomlCode = ALL.filter(([p]) => p.endsWith('.toml')).map(([, t]) => t.split('\n').filter((l) => !l.trim().startsWith('#')).join('\n')).join('\n');
ok(tomlCode.length > 0 && !/\b(id|preview_id|account_id|zone_id|database_id)\s*=/.test(tomlCode), 'no namespace, account, zone or database id in any toml');
ok(!/\b[0-9a-f]{32}\b/.test(allText), 'no 32-hex Cloudflare-style id anywhere');
ok(!/(sk|rk)_(live|test)_[A-Za-z0-9]{6,}|whsec_[A-Za-z0-9+/=]{6,}|price_[A-Za-z0-9]{6,}/.test(allText), 'no Stripe key, webhook secret or price id');
ok(!/^\s*\[vars\]/m.test(allText) && !/api_token|CLOUDFLARE_API_TOKEN\s*=/.test(allText), 'no [vars] values and no API token');
ok(!/\bzone_name\b|\bpattern\s*=/.test(allText), 'no route pattern tied to a domain');
for (const s of REG.secrets) ok(read('worker/wrangler.toml').includes(s) && read('README.md').includes('wrangler secret put ' + s), `secret ${s} named, set by wrangler secret put (README)`);

/* ---- headers equal the committed deploy's ---- */
const V = JSON.parse(readFileSync(join(ROOT, 'vercel.json'), 'utf8'));
const want = V.headers.flatMap((r) => r.headers.map((h) => [h.key, h.value]));
const H = read('_headers');
const blocks = {};
let cur = null;
for (const line of H.split('\n')) {
  if (!line.trim() || line.startsWith('#')) continue;
  if (!/^\s/.test(line)) { cur = line.trim(); blocks[cur] = []; continue; }
  const i = line.indexOf(':');
  blocks[cur].push([line.slice(0, i).trim(), line.slice(i + 1).trim()]);
}
const site = blocks['/*'] || [];
ok(want.length > 0 && want.every(([k, v]) => site.some(([a, b]) => a === k && b === v)), `every vercel.json header (${want.length}) is on /* with the same value`);
ok(site.filter(([k]) => k !== 'Content-Security-Policy').length === want.length, '/* carries no header beyond vercel.json\'s except the CSP');
ok(site.some(([k, v]) => k === 'Content-Security-Policy' && v === REG.baseline_csp), 'baseline CSP on /* equals the registry');
const csp = (REG.baseline_csp || '').split(';').map((s) => s.trim().split(/\s+/)[0]);
ok(JSON.stringify(csp) === JSON.stringify(['frame-ancestors', 'base-uri', 'object-src', 'form-action']), 'baseline CSP restricts only framing, base, plugins and form targets (cannot break inline page scripts)');
const pages = readdirSync(join(ROOT, 'web')).filter((f) => f.endsWith('.html')).map((f) => readFileSync(join(ROOT, 'web', f), 'utf8'));
pages.push(readFileSync(join(ROOT, 'index.html'), 'utf8'));
ok(!pages.some((p) => /<iframe|<object|<embed|<base\s/i.test(p)), 'no page uses iframe/object/embed/base (baseline CSP breaks nothing)');
ok(!pages.some((p) => /<form\b(?![^>]*method="dialog")[^>]*action="https?:/i.test(p)), 'no page posts a form off-site (form-action self holds)');
const api = blocks['/api/*'] || [];
ok(api.some(([k, v]) => k === 'Content-Security-Policy' && v === "default-src 'none'; frame-ancestors 'none'") && api.some(([k, v]) => k === 'Cache-Control' && v === 'no-store'), '/api/* is deny-all CSP and no-store');
ok(JSON.stringify(REG.site_headers.map((h) => [h.key, h.value])) === JSON.stringify(want), 'registry records the derived headers');

/* ---- routes map to the Worker ---- */
const R = JSON.parse(read('_routes.json'));
ok(R.version === 1 && JSON.stringify(R.include) === '["/api/*"]' && R.exclude.length === 0, '_routes.json: Functions run for /api/* only');
const { ROUTES } = await import('../payments/worker.mjs');
ok(ROUTES.length === 2 && ROUTES.every((r) => r.startsWith('/api/')), 'every Worker route is under /api/* (reached through _routes.json)');
ok(JSON.stringify(REG.api_routes) === JSON.stringify(ROUTES), 'registry api_routes equal the Worker ROUTES');
const FN = read('functions/api/[[path]].js');
ok(/env\.PAYMENTS\.fetch\(request\)/.test(FN) && /status: 503/.test(FN), 'Pages Function forwards /api/* to the PAYMENTS binding, 503 without it');
const fnMod = await import('data:text/javascript,' + encodeURIComponent(FN));
let fwd = null;
const fr = await fnMod.onRequest({ request: new Request('https://x.example/api/checkout', { method: 'POST' }), env: { PAYMENTS: { fetch: async (q) => { fwd = q; return new Response('ok'); } } } });
ok(fwd && new URL(fwd.url).pathname === '/api/checkout' && (await fr.text()) === 'ok', 'the Function hands the request to the Worker unchanged');
ok((await fnMod.onRequest({ request: new Request('https://x.example/api/checkout'), env: {} })).status === 503, 'no binding: fail closed 503');
const RD = read('_redirects').split('\n').filter((l) => l.trim() && !l.startsWith('#')).map((l) => l.trim().split(/\s+/));
ok(RD.every((r) => r.length === 3 && r[0].startsWith('/') && r[1].startsWith('/') && !r[1].startsWith('//') && ['301', '302'].includes(r[2])), '_redirects: same-site targets only');
ok(RD.every((r) => !r[0].startsWith('/api')), '_redirects never shadows /api/*');
ok(RD.every((r) => statSync(join(ROOT, r[1].split('?')[0].slice(1)), { throwIfNoEntry: false })), '_redirects targets exist in the tree');

/* ---- generated files are what build.py says ---- */
for (const [k, h] of Object.entries(REG.files))
  ok(h === 'sha256:' + createHash('sha256').update(read(k)).digest('hex'), `${k} matches its recorded hash`);
ok(REG.source_stamp === 'sha256:' + createHash('sha256').update(readFileSync(join(HERE, 'build.py'))).digest('hex'), 'source_stamp is build.py');

console.log(`cloudflare: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
