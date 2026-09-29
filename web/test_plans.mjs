/* web/test_plans.mjs - the Plans page, checked from the BUILT page. Network-free.
 * The page's own checkout code (PLANS-CORE) is lifted out and run against stub DOM, fetch and
 * location, so what is tested is what ships. Prints `  ok ` per check, FAIL at column 0. */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok ' + m); } else { fail++; console.log('FAIL ' + m); } };
const read = (p) => readFileSync(join(ROOT, p), 'utf8');
console.log('web/test_plans.mjs');
const P = read('web/trade_craft_plans.html');
const CAT = JSON.parse(read('payments/registry/catalog.json'));
const EN = JSON.parse(read('i18n/locales/en.json')).strings;
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');

/* ---- page must-haves ---- */
ok((P.match(/<h1\b/g) || []).length === 1, 'exactly one <h1>');
ok(/<link rel="icon" href="data:image\/svg\+xml,/.test(P), 'inline brand icon');
ok(/<body class="tc-theme">/.test(P) && P.includes('id="tc-css"'), "doc theme: theme('doc') + body.tc-theme");
ok(/<section class="ph" data-ph/.test(P), 'pagehero band present');
const firstStyle = P.indexOf('<style'), shj = P.indexOf('id="style-head-js"');
ok(shj > 0 && shj < firstStyle, 'STYLE_HEAD_JS before the first <style> (5 styles remembered)');
ok(P.includes('id="style-js"') && /name="tc-style"/.test(P), 'STYLE_JS + nav Style menu present');
ok(P.includes('data-sitenav') && P.includes('id="tc-main"'), 'site nav and #tc-main skip target');
ok(/<meta name="description" content="[^"]+">/.test(P) && (P.match(/<title>/g) || []).length === 1, 'one <title> and a description');
const SITENAV = read('web/sitenav.py');
ok(/\('web\/trade_craft_plans\.html', 'nav\.page\.plans'\)/.test(SITENAV), "sitenav declares web/trade_craft_plans.html as nav.page.plans");
const cur = P.match(/<a[^>]*href="([^"]+)"[^>]*aria-current="page"/);
ok(cur && cur[1] === 'trade_craft_plans.html', 'nav marks this page (and only this page) as current');
ok((P.match(/<a[^>]*aria-current="page"/g) || []).length === 1, 'exactly one current-page mark');
ok(/<link rel="canonical" href="trade_craft_plans\.html">/.test(P), 'canonical link to this page (apply_seo head)');
ok(/<meta property="og:url" content="https:\/\/[^"]+\/web\/trade_craft_plans\.html">/.test(P), 'og:url names the canonical URL');
const BUILD = read('web/build_plans.py');
ok(/if PAGE not in sitenav\.PAGES:\s*\n\s*raise /.test(BUILD) && !/replace\(' aria-current="page"', ''\)/.test(BUILD), 'builder fails closed on an undeclared page (no sibling-nav fallback)');
const own = P.slice(P.lastIndexOf('<style>'), P.indexOf('</style>', P.lastIndexOf('<style>')));
ok(own.length > 50 && !/#[0-9a-fA-F]{3,8}\b/.test(own), 'page CSS colours only from theme var(--...) (no hex)');

/* ---- honesty ---- */
const banner = 'Payments are not live: no Stripe account is connected to this deployment';
ok(CAT.status === banner && P.includes(`<strong>${esc(banner)}</strong>`) && EN['plans.banner'] === banner, 'banner states payments are not live (= catalogue status)');
ok(P.includes(esc(EN['plans.gate_note'])), 'says no feature is gated on payment');
ok(P.includes(esc(EN['plans.card_note'])), "says card details go only to Stripe's hosted page");
const visible = P.replace(/<script[\s\S]*?<\/script>/g, '').replace(/<style[\s\S]*?<\/style>/g, '').replace(/<[^>]+>/g, ' ');
ok(!/[$€£¥₹]\s?\d|\d\s?(usd|eur|gbp)\b|\/\s?(mo|month|yr|year)\b|\bper (month|year)\b|% off|\bfree trial\b/i.test(visible), 'no price, currency, discount or trial on the page');
ok(!/<form\b/i.test(P) && !/<input[^>]*(card|cvc|cc-)/i.test(P), 'no form, no card field');
const cards = [...P.matchAll(/<article class="tc-card plan" data-plan="([^"]+)"/g)].map((m) => m[1]);
ok(JSON.stringify(cards) === JSON.stringify(CAT.plans.map((p) => p.id)), 'one card per catalogue plan, in order');
for (const p of CAT.plans) {
  ok(P.includes(`<h2>${esc(EN[p.label_key])}</h2>`) && P.includes(esc(EN[p.desc_key])), `card ${p.id}: title and description from plans.* keys`);
  ok(P.includes(`class="tc-btn tc-btn-primary choose" data-plan="${p.id}"`), `card ${p.id}: Choose button`);
}
ok((P.match(/Price: set by the operator in Stripe/g) || []).length === CAT.plans.length, 'each card: "Price: set by the operator in Stripe"');
ok(/PROPOSED partners; no agreement exists/.test(P), 'school/district stays a PROPOSED partner');
const hrefs = [...P.matchAll(/\s(?:href|src)="([^"]+)"/g)].map((m) => m[1]);
ok(hrefs.every((h) => !/^(https?:)?\/\//.test(h)), 'no remote href/src');

/* ---- i18n: plans.* in 8 locales, real translations ---- */
const LOC = ['ar', 'de', 'en', 'es', 'fr', 'hi', 'pt', 'zh'];
const PK = Object.keys(EN).filter((k) => k.startsWith('plans.'));
ok(PK.length >= 20, `en carries ${PK.length} plans.* keys`);
for (const l of LOC.filter((x) => x !== 'en')) {
  const S = JSON.parse(read(`i18n/locales/${l}.json`)).strings;
  ok(PK.every((k) => typeof S[k] === 'string' && S[k].trim() && S[k] !== EN[k]), `${l}: every plans.* key present and translated`);
}

/* ---- the page's own checkout code, lifted and run ---- */
const A = P.indexOf('/* PLANS-CORE:BEGIN'), B = P.indexOf('/* PLANS-CORE:END */');
const CORE = A > 0 && B > A ? P.slice(A, B) : '';
const CFG = P.match(/<script type="application\/json" id="plans-cfg">([\s\S]*?)<\/script>/);
ok(CORE.length > 0 && CFG, 'PLANS-CORE and plans-cfg found in the page');
const cfg = JSON.parse(CFG[1]);
ok(cfg.endpoint === CAT.checkout.endpoint && cfg.hosted === CAT.checkout.hosted_prefix, 'page posts to the catalogue endpoint, follows only the hosted prefix');
async function run({ protocol = 'https:', search = '', reply }) {
  const msgs = {}, sent = [], assigned = [];
  const buttons = CAT.plans.map((p) => {
    const msg = { textContent: '' }; msgs[p.id] = msg;
    const card = { querySelector: () => msg };
    const b = { disabled: false, h: null, getAttribute: () => p.id, closest: () => card, addEventListener: (_e, f) => { b.h = f; } };
    return b;
  });
  const ret = { textContent: '', hidden: true };
  const document = { getElementById: (id) => (id === 'plans-cfg' ? { textContent: CFG[1] } : ret), querySelectorAll: () => buttons };
  const location = { protocol, search, assign: (u) => assigned.push(u) };
  const fetch = async (u, i) => { sent.push({ u, i }); return reply(); };
  const window = { crypto: { randomUUID: () => 'k-' + sent.length + '-0000000000000000' } };
  new Function('document', 'location', 'fetch', 'window', 'crypto', 'URLSearchParams', CORE)(document, location, fetch, window, window.crypto, URLSearchParams);
  const click = async (i) => { buttons[i].h(); await new Promise((r) => setTimeout(r, 5)); };
  return { msgs, sent, assigned, ret, click };
}
const R = (status, body) => () => ({ ok: status >= 200 && status < 300, status, json: async () => body });
const id0 = CAT.plans[0].id;
let t = await run({ reply: R(200, { ok: true, url: 'https://checkout.stripe.com/c/pay/cs_x' }) });
await t.click(0);
ok(t.sent.length === 1 && t.sent[0].u === '/api/checkout' && t.sent[0].i.method === 'POST', 'Choose POSTs to /api/checkout');
const sb = JSON.parse(t.sent[0].i.body);
ok(sb.plan === id0 && typeof sb.idempotency_key === 'string' && t.sent[0].i.headers['content-type'] === 'application/json', 'body = {plan, idempotency_key}, JSON');
ok(t.assigned.length === 1 && t.assigned[0] === 'https://checkout.stripe.com/c/pay/cs_x', 'a hosted Checkout URL is followed');
await t.click(0);
ok(JSON.parse(t.sent[1].i.body).idempotency_key === sb.idempotency_key, 'a second click reuses the idempotency key');
t = await run({ reply: R(200, { ok: true, url: 'https://evil.example/pay' }) });
await t.click(0);
ok(t.assigned.length === 0 && t.msgs[id0].textContent === EN['plans.err.generic'], 'a URL off checkout.stripe.com is never followed');
t = await run({ reply: () => { throw new TypeError('Failed to fetch'); } });
await t.click(0);
ok(t.msgs[id0].textContent === EN['plans.err.static'], 'no Worker (network error): the button explains why');
t = await run({ reply: R(404, null) });
await t.click(0);
ok(t.msgs[id0].textContent === EN['plans.err.static'], 'static host 404: the button explains why');
t = await run({ reply: R(503, { ok: false, error: 'not_configured' }) });
await t.click(0);
ok(t.msgs[id0].textContent === EN['plans.err.not_configured'], 'Worker without secrets: says not configured');
t = await run({ protocol: 'file:', reply: R(200, {}) });
await t.click(0);
ok(t.sent.length === 0 && t.msgs[id0].textContent === EN['plans.err.static'], 'file:// : no request, explains why');
t = await run({ search: '?checkout=success', reply: R(200, {}) });
ok(!t.ret.hidden && t.ret.textContent === EN['plans.return.success'], 'return from Stripe: success note (changes nothing)');
t = await run({ search: '?checkout=<img>', reply: R(200, {}) });
ok(t.ret.hidden, 'unknown checkout= value shows nothing');
ok(!/innerHTML|insertAdjacentHTML|document\.write/.test(CORE), 'no HTML injection sinks in the checkout code');

// AUDIT row 11 (UX): one scheme for nav and page. The site nav reads --panel/--ink/--rule/--muted/--mark (sitenav
// NAV_CSS, falling back to the OS Canvas colours when a page leaves them unset - which drew a light bar over this dark
// page under a light OS). The page binds each to the theme layer on <body>, and the bound pair holds AA.
{
  const m = P.match(/body\.tc-theme\{(--plate:var\(--tc-plate\);[^}]*)\}/);
  const decl = m ? Object.fromEntries(m[1].split(';').filter(Boolean).map((d) => d.split(':').map((x) => x.trim()))) : {};
  const want = { '--panel': 'var(--tc-panel)', '--ink': 'var(--tc-ink)', '--rule': 'var(--tc-line)', '--line': 'var(--tc-line)', '--muted': 'var(--tc-muted)', '--mark': 'var(--tc-amber)' };
  const dark = P.match(/body\.tc-theme\{[^}]*--tc-panel:(#[0-9A-Fa-f]{6});[^}]*--tc-ink:(#[0-9A-Fa-f]{6});/);
  // measured with the design kit's own contrast function (web/design_kit.py contrast), not a second copy
  const ratio = dark ? Number((await import('node:child_process')).execFileSync('python3', ['-c',
    `import sys; sys.path.insert(0, ${JSON.stringify(join(ROOT, 'web'))}); import design_kit; print(design_kit.contrast(${JSON.stringify(dark[2])}, ${JSON.stringify(dark[1])}))`], { encoding: 'utf8' })) : 0;
  ok(!!m && Object.entries(want).every(([k, v]) => decl[k] === v) && ratio >= 4.5,
    `row 11: the nav's tokens are bound to the page theme on <body> (no OS-colour seam); nav ink/panel ${ratio.toFixed(2)}:1 >= 4.5`);
}

console.log(`plans: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
