/* web/test_packs.mjs - the holodeck packs catalogue, checked from the BUILT page against
 * holodeck/registry/packs.json. Network-free. The page's own locale code (PACKS-CORE) is lifted
 * out and run against a stub DOM. Prints `  ok ` per check, FAIL at column 0. */
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok ' + m); } else { fail++; console.log('FAIL ' + m); } };
const read = (p) => readFileSync(join(ROOT, p), 'utf8');
console.log('web/test_packs.mjs');
const P = read('web/trade_craft_packs.html');
const REG = JSON.parse(read('holodeck/registry/packs.json'));
const EN = JSON.parse(read('i18n/locales/en.json')).strings;
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
const SERIES = 'SmartCiti.X Powered by AGI Corp';

/* ---- page must-haves ---- */
ok((P.match(/<h1\b/g) || []).length === 1, 'exactly one <h1>');
ok(/<link rel="icon" href="data:image\/svg\+xml,/.test(P), 'inline brand icon');
ok(/<body class="tc-theme">/.test(P) && P.includes('id="tc-css"'), "doc theme: theme('doc') + body.tc-theme");
const firstStyle = P.indexOf('<style'), shj = P.indexOf('id="style-head-js"');
ok(shj > 0 && shj < firstStyle, 'STYLE_HEAD_JS before the first <style> (5 styles remembered)');
ok(P.includes('id="style-js"') && /name="tc-style"/.test(P), 'STYLE_JS + nav Style menu present');
ok(P.includes('data-sitenav') && P.includes('id="tc-main"'), 'site nav and #tc-main skip target');
ok(/<meta name="description" content="[^"]+">/.test(P) && (P.match(/<title>/g) || []).length === 1, 'one <title> and a description');
ok(/\('web\/trade_craft_packs\.html', 'nav\.page\.packs'\)/.test(read('web/sitenav.py')), 'sitenav declares web/trade_craft_packs.html as nav.page.packs');
const cur = P.match(/<a[^>]*href="([^"]+)"[^>]*aria-current="page"/);
ok(cur && cur[1] === 'trade_craft_packs.html' && (P.match(/<a[^>]*aria-current="page"/g) || []).length === 1, 'nav marks this page, and only this page, as current');
ok(/<link rel="canonical" href="trade_craft_packs\.html">/.test(P), 'canonical link to this page (apply_seo head)');
const BUILD = read('web/build_packs.py');
ok(/if PAGE not in sitenav\.PAGES:\s*\n\s*raise /.test(BUILD), 'builder fails closed on an undeclared page');
const own = P.slice(P.lastIndexOf('<style>'), P.indexOf('</style>', P.lastIndexOf('<style>')));
ok(/<html lang="en">/.test(P) && !/--(panel|ink|muted|line|link|accent)\)/.test(own) && (own.match(/var\(--tc-/g) || []).length >= 10,
  'light/dark follow the reader\'s scheme (no forced data-theme); colours from --tc-* tokens the 5 styles set');
ok(own.length > 50 && !/#[0-9a-fA-F]{3,8}\b/.test(own.replace(/#pk-k-[a-z0-9]+/g, '')), 'page CSS colours only from theme var(--...) (no hex)');

/* ---- one card per pack, figures = registry ---- */
ok(REG.series === SERIES && P.includes(`data-series>`) && P.includes(esc(SERIES)), `series shown exactly: "${SERIES}"`);
const cards = [...P.matchAll(/<article class="tc-card pk" id="pk-([^"]+)" data-pack="([^"]+)" data-kind="([^"]+)" data-status="([^"]+)">([\s\S]*?)<\/article>/g)];
ok(JSON.stringify(cards.map((m) => m[2])) === JSON.stringify(REG.packs.map((p) => p.id)), `one card per registry pack, in order (${REG.packs.length})`);
const byId = Object.fromEntries(cards.map((m) => [m[2], { kind: m[3], status: m[4], body: m[5] }]));
let countsOk = true, badgeOk = true, linkOk = true, titleOk = true, srcOk = true;
for (const p of REG.packs) {
  const c = byId[p.id];
  if (!c || c.kind !== p.kind || c.status !== p.status) { badgeOk = false; continue; }
  if (!new RegExp(`<span class="tc-badge tc-badge-(ok|warn)" data-badge>${p.status}</span>`).test(c.body)) badgeOk = false;
  const shown = Object.fromEntries([...c.body.matchAll(/<dd data-count="([^"]+)">(\d+)<\/dd>/g)].map((m) => [m[1], Number(m[2])]));
  if (JSON.stringify(Object.keys(shown).sort()) !== JSON.stringify(Object.keys(p.contents).sort())
    || Object.entries(p.contents).some(([k, v]) => shown[k] !== v)) countsOk = false;
  const go = c.body.match(/<a class="tc-btn tc-btn-primary go" href="([^"]+)" data-open="([^"]+)">/);
  if (p.open === null ? (go || !c.body.includes('data-i18n="packs.noopen"')) : (!go || go[2] !== p.open || !existsSync(join(HERE, go[1])))) linkOk = false;
  if (p.kind === 'union' || p.kind === 'k12' ? !c.body.includes(`<h2><span>${esc(p.title)}</span></h2>`) : !c.body.includes(`data-i18n="${p.title_key}"`)) titleOk = false;
  if (!p.sources.every((s) => c.body.includes(`<code>${esc(s.path)}</code> <span class="sha">${s.sha256}</span>`))) srcOk = false;
}
ok(badgeOk, 'every card: kind and SHIPPING/PROPOSED badge = registry');
ok(countsOk, 'every card: each count shown = registry contents (keys and values)');
ok(linkOk, '"Open in world" only where the registry names a page, and it resolves to a file; else the no-page note');
ok(titleOk, 'titles: union / K-12 names quoted from registries, the rest from packs.* keys');
ok(srcOk, 'every card names its source registries with sha256[:16]');
ok(REG.packs.filter((p) => p.status === 'PROPOSED').every((p) => !/class="tc-btn[^"]*go"/.test(byId[p.id].body)), 'no PROPOSED card deep-links');
const stat = (k) => Number((P.match(new RegExp(`data-stat="${k}">(\\d+)<`)) || [])[1]);
ok(stat('packs') === REG.packs.length && stat('shipping') === REG.packs.filter((p) => p.status === 'SHIPPING').length
  && stat('proposed') === REG.packs.filter((p) => p.status === 'PROPOSED').length, 'stat row = recount of the registry');

/* ---- filters by kind (radios + CSS :has, no script needed) ---- */
const KINDS = ['union', 'k12', 'path', 'world', 'system'];
ok(['all', ...KINDS].every((k) => P.includes(`name="pk-kind" value="${k}" id="pk-k-${k}"`)), 'kind filter: all + union / K-12 / path / world / system');
ok(KINDS.every((k) => own.includes(`.cat:has(#pk-k-${k}:checked) .pk:not([data-kind="${k}"]){display:none}`)), 'each filter hides the other kinds by CSS');

/* ---- honesty ---- */
ok(['counted', 'status', 'price', 'cert', 'k12', 'un', 'play', 'names'].every((k) => P.includes(`data-i18n="packs.honest.${k}">${esc(EN['packs.honest.' + k])}<`)), 'honesty footer: counted, status, no price, no certification, K-12 PROPOSED, UN not affiliated, play, quoted names');
const W11_HONEST = { 'tradesquest-stations': 'tq', 'materials-colour': 'colour', 'robotics-lab': 'robotics', 'data-commons': 'data' };
ok(Object.entries(W11_HONEST).every(([id, k]) => REG.packs.some((p) => p.id === id)
  === P.includes(`data-i18n="packs.honest.${k}">${esc(EN['packs.honest.' + k])}<`)), 'wave-11 honesty lines (TradesQuest stations are ported play; robotics: nothing trained) shown exactly when their module is present');
const w11 = REG.packs.filter((p) => p.wave === 11);
ok(w11.every((p) => byId[p.id] && byId[p.id].body.includes(`data-i18n="packs.pack.${p.id}"`) && p.sources.length > 0),
  `wave-11 shared modules each have a card titled from packs.pack.<id> and a source registry (${w11.map((p) => p.id).join(', ')})`);
ok(!byId['robotics-lab'] || !/\btrained\b(?! on them)/i.test(byId['robotics-lab'].body.replace(/<[^>]+>/g, ' ')), 'robotics-lab card claims nothing was trained');
const visible = P.replace(/<script[\s\S]*?<\/script>/g, '').replace(/<style[\s\S]*?<\/style>/g, '').replace(/<[^>]+>/g, ' ');
ok(!/[$€£¥₹]\s?\d|\d\s?(usd|eur|gbp)\b|\/\s?(mo|month|yr|year)\b|\bper (month|year)\b|% off|\bfree trial\b|\bbuy\b|\bpurchase\b|\bdownload\b|add to cart/i.test(visible), 'no price, currency, purchase or download on the page');
ok(!/accredited|certified|official partner|endorsed by(?! the United Nations)/i.test(visible.replace(EN['packs.honest.un'], '')), 'no accreditation, certification or partner claim outside the honesty notes');
ok(!/<form\b/i.test(P), 'no form');
const hrefs = [...P.matchAll(/\s(?:href|src)="([^"]+)"/g)].map((m) => m[1]);
ok(hrefs.every((h) => !/^(https?:)?\/\//.test(h)), 'no remote href/src');

/* ---- i18n: 8 locales, RTL, every data-i18n key in every locale ---- */
const I = JSON.parse(P.match(/<script type="application\/json" id="packs-i18n">([\s\S]*?)<\/script>/)[1]);
const used = [...new Set([...P.matchAll(/data-i18n="([^"]+)"/g)].map((m) => m[1]))];
ok(Object.keys(I).sort().join() === 'ar,de,en,es,fr,hi,pt,zh' && I.ar.dir === 'rtl', '8 locales embedded, Arabic right-to-left');
ok(used.length >= 40 && Object.values(I).every((c) => used.every((k) => typeof c.strings[k] === 'string' && c.strings[k].trim())), `every data-i18n key (${used.length}) present in all 8 locales`);
ok(Object.entries(I).filter(([l]) => l !== 'en').every(([, c]) => used.every((k) => c.strings[k] !== I.en.strings[k])), 'every non-English string is a translation, not an English copy');
ok(used.every((k) => I.en.strings[k] === EN[k]), 'embedded en strings = i18n/locales/en.json');

/* ---- PACKS-CORE, lifted and run ---- */
const A = P.indexOf('/* PACKS-CORE:BEGIN'), B = P.indexOf('/* PACKS-CORE:END */');
const CORE = A > 0 && B > A ? P.slice(A, B) : '';
ok(CORE.length > 0 && !/innerHTML|insertAdjacentHTML|document\.write/.test(CORE), 'PACKS-CORE found; no HTML injection sinks');
function run(search, languages) {
  const els = used.map((k) => ({ k, textContent: EN[k], getAttribute: () => k }));
  const doc = { documentElement: {}, getElementById: () => ({ textContent: JSON.stringify(I) }),
    querySelectorAll: (q) => (q === '[data-i18n]' ? els : new Array(REG.packs.length)) };
  const win = {};
  new Function('document', 'location', 'navigator', 'window', 'URLSearchParams', CORE)(doc, { search }, { languages }, win, URLSearchParams);
  return { doc, els, win };
}
let r = run('?lang=ar', ['en']);
ok(r.doc.documentElement.dir === 'rtl' && r.doc.documentElement.lang === 'ar' && r.els.every((e) => e.textContent === I.ar.strings[e.k]), '?lang=ar: page turns right-to-left, every label Arabic');
r = run('', ['de-DE', 'en']);
ok(r.doc.documentElement.lang === 'de' && r.doc.documentElement.dir === 'ltr' && r.win.__packsState.cards === REG.packs.length, 'browser language de: German, left-to-right; state reports every card');
r = run('?lang=xx', ['xx']);
ok(r.doc.documentElement.lang === 'en', 'unknown locale falls back to en');

console.log(`packs: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
