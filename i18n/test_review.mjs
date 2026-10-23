// i18n/test_review.mjs - the native-speaker review loop cannot drift or over-claim.
//
// Builds the real review sheets (python3 i18n/build_review.py --out <tmp>) and holds them to the
// catalogs: every key in exactly one row, priority derived by the rule file, BOM, header and glossary,
// RTL page for Arabic, "appears in" backed by the built pages. Then runs the return path
// (python3 i18n/ingest_review.py) on a small fixture: a round trip, every refusal, all-or-nothing,
// and the status/ledger agreement that keeps translation_status honest. Prints `  ok <name>` per
// check and `FAIL <name>` at column 0; exits non-zero on any failure.
import { readFileSync, writeFileSync, mkdirSync, mkdtempSync, rmSync, cpSync, existsSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { LOCALES, load, validateCatalog, isKnownStatus, PARTIAL_STATUS_RE } from './catalog.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let fails = 0, oks = 0;
const check = (cond, m) => { if (cond) { oks++; console.log('  ok ' + m); } else { fails++; console.log('FAIL ' + m); } };
const py = (args, cwd = ROOT) => spawnSync('python3', args, { cwd, encoding: 'utf8', maxBuffer: 1 << 28 });
const rules = JSON.parse(readFileSync(join(HERE, 'review_rules.json'), 'utf8'));
const NON_EN = LOCALES.filter((l) => l !== 'en');
const COLUMNS = ['key', 'english', 'draft', 'appears_in', 'priority', 'why', 'status', 'verdict', 'corrected', 'notes'];
const PENDING = 'machine-drafted, pending native review';

// ---------------------------------------------------------------- helpers ---
const META = new Set(['locale', 'language', 'english_name', 'dir', 'translation_status', 'reviewer', 'reviewed_at']);
function flatten(cat) {            // an independent walk: id -> text, in catalog order
  const out = new Map();
  const walk = (node, id) => {
    if (typeof node === 'string') out.set(id, node);
    else if (Array.isArray(node)) node.forEach((v, i) => walk(v, `${id}.${i}`));
    else for (const [k, v] of Object.entries(node)) walk(v, id ? `${id}.${k}` : k);
  };
  for (const [k, v] of Object.entries(cat)) {
    if (META.has(k)) continue;
    if (k === 'strings') for (const [s, t] of Object.entries(v)) out.set(`strings.${s}`, t);
    else walk(v, k);
  }
  return out;
}
function parseCsv(text) {          // RFC 4180, CRLF or LF, BOM tolerated
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
  const rows = []; let row = [], cell = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) { if (c === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += c; }
    else if (c === '"') q = true;
    else if (c === ',') { row.push(cell); cell = ''; }
    else if (c === '\n' || c === '\r') { if (c === '\r' && text[i + 1] === '\n') i++; row.push(cell); rows.push(row); row = []; cell = ''; }
    else cell += c;
  }
  if (cell !== '' || row.length) { row.push(cell); rows.push(row); }
  return rows;
}
const csvCell = (c) => (/[",\r\n]/.test(c) ? `"${c.replace(/"/g, '""')}"` : c);
const toCsv = (rows) => '\ufeff' + rows.map((r) => r.map(csvCell).join(',')).join('\r\n') + '\r\n';
function sheetRows(text) {
  const all = parseCsv(text);
  const h = all.findIndex((r) => r[0] === 'key');
  return { head: all.slice(0, h), header: all[h], rows: all.slice(h + 1).map((r) => Object.fromEntries(all[h].map((c, i) => [c, r[i] ?? '']))) };
}
const sha = (s) => createHash('sha256').update(s.normalize('NFC'), 'utf8').digest('hex');
const words = (s) => (s.replace(/<[^>]+>/g, ' ').match(/\S+/g) ?? []).length;
// the rule, written again from the rule file's own words (not a copy of the Python)
function priorityOf(id, english) {
  const segs = id.split('.'), n = words(english);
  if (rules.p2_sections.includes(segs[0])) return 2;
  for (const s of segs) {
    if (rules.p1_key_segments.includes(s)) return 1;
    if (rules.p1_key_segments_sentences_only.includes(s) && n >= rules.p1_key_sentence_min_words) return 1;
  }
  for (const r of rules.p1_text_rules) if (n >= r.min_words && new RegExp(r.pattern, r.flags).test(english)) return 1;
  if (segs[0] === 'strings' && rules.p2_prefixes.includes(segs[1])) return 2;
  if (n <= rules.p2_short_label_max_words && !new RegExp(rules.p2_sentence_punctuation).test(english)) return 2;
  return 3;
}
function statusFor(cur, total, s1, p1) {
  return cur <= 0 ? PENDING : cur >= total ? 'reviewed'
    : `machine-drafted; ${cur} of ${total} keys checked by a native speaker, ${s1} of ${p1} safety and honesty lines`;
}
function ledgerOf(root, l) {
  const p = join(root, 'i18n', 'review', `${l}.ledger.json`);
  return existsSync(p) ? JSON.parse(readFileSync(p, 'utf8')) : { entries: {} };
}
// the status a catalog MUST carry, recomputed from its ledger with the English source (JS side of the contract)
function expectedStatus(en, cat, ledger) {
  const E = flatten(en), C = flatten(cat);
  let cur = 0, s1 = 0, p1 = 0; const names = new Set(), dates = [];
  for (const [id, t] of E) {
    const e = ledger.entries[id], safety = priorityOf(id, t) === 1;
    if (safety) p1++;
    if (e && e.en_sha === sha(t) && e.text_sha === sha(C.get(id))) { cur++; if (safety) s1++; names.add(e.reviewed_by); dates.push(e.reviewed_at); }
  }
  return { cur, s1, p1, total: E.size, status: statusFor(cur, E.size, s1, p1), reviewer: [...names].sort().join(', '), at: dates.sort().at(-1) };
}

// ============================================================ real sheets ===
const OUT = mkdtempSync(join(tmpdir(), 'review-sheets-'));
const built = py(['i18n/build_review.py', '--out', OUT, '--no-summary']);
check(built.status === 0, `build_review.py builds the sheets (exit ${built.status}${built.status ? ': ' + built.stderr.slice(0, 200) : ''})`);
check(NON_EN.length === 7 && ['ar', 'de', 'es', 'fr', 'hi', 'pt', 'zh'].every((l) => NON_EN.includes(l)),
  'seven non-source locales get a sheet: ar, de, es, fr, hi, pt, zh');
const en = load('en');
const EN = flatten(en);
const sheets = {};
for (const l of NON_EN) {
  const bytes = existsSync(join(OUT, `${l}.csv`)) ? readFileSync(join(OUT, `${l}.csv`)) : Buffer.alloc(0);
  sheets[l] = { bytes, ...sheetRows(bytes.toString('utf8')) };
}
for (const l of NON_EN) {
  const S = sheets[l], C = flatten(load(l));
  check(S.bytes[0] === 0xef && S.bytes[1] === 0xbb && S.bytes[2] === 0xbf, `${l}.csv starts with a UTF-8 byte-order mark so spreadsheets open it`);
  check(JSON.stringify(S.header) === JSON.stringify(COLUMNS), `${l}.csv header is exactly ${COLUMNS.join(', ')}`);
  const keys = S.rows.map((r) => r.key);
  const once = new Map(); for (const k of keys) once.set(k, (once.get(k) ?? 0) + 1);
  check(keys.length === EN.size && once.size === EN.size && [...EN.keys()].every((k) => once.get(k) === 1),
    `${l}: every one of the ${EN.size} catalog keys appears in exactly one row, no extra rows (${keys.length} rows)`);
  check(S.rows.every((r) => r.english === EN.get(r.key) && r.draft === C.get(r.key)),
    `${l}: the english and draft columns equal the catalogs, character for character (quotes, markup, accents)`);
  check(S.rows.every((r) => String(priorityOf(r.key, EN.get(r.key))) === r.priority),
    `${l}: every priority equals the rule in review_rules.json applied to the key and its English text`);
  check(S.rows.every((r, i) => i === 0 || Number(S.rows[i - 1].priority) <= Number(r.priority)),
    `${l}: priority 1 rows come first, then 2, then 3`);
  check(S.rows.every((r) => r.verdict === '' && r.corrected === '' && r.notes === ''),
    `${l}: verdict, corrected and notes are blank in a fresh sheet`);
  check(S.rows.every((r) => r.appears_in.trim().length > 0 && (/^(pages|code): /.test(r.appears_in) || r.appears_in.startsWith('not found in any built page'))),
    `${l}: appears_in is a derived list of pages and code, or says in words that none was found`);
  check(S.head[0][0] === `#locale=${l}` && S.head.every((r) => r[0].startsWith('#')),
    `${l}.csv leads with #locale=${l} and comment rows only above the header`);
  const headText = S.head.map((r) => r[0]).join('\n');
  check(rules.glossary.every((g) => headText.includes(g.term)) && /stay in English/i.test(headText) && /verdict/.test(headText),
    `${l}.csv instructions carry the glossary (${rules.glossary.map((g) => g.term).join(', ')}) and say they stay in English`);
}
{
  const P1 = (l) => new Set(sheets[l].rows.filter((r) => r.priority === '1').map((r) => r.key));
  const p1 = P1('de');
  const sentinels = Object.entries(en.strings).filter(([k, v]) => /^honesty\./.test(k) || k === 'sim.slowNotice' || k === 'landing.footer.disclaimer'
    || /not a language model/i.test(v) || /certif(y|ies) nothing/i.test(v) || /no AI model/i.test(v) || /kept on this device only/i.test(v)).map(([k]) => `strings.${k}`);
  check(sentinels.length >= 12 && sentinels.every((k) => p1.has(k)),
    `safety and honesty lines are priority 1 (${sentinels.length} sentinels: honesty.*, the seat notice, the landing disclaimer, "not a language model", "certifies nothing", "no AI model", device-only lines)`);
  check(!p1.has('strings.nav.campus') && !p1.has('strings.nav.group.play') && !p1.has('strings.hive.cn.play') && sheets.de.rows.find((r) => r.key === 'tracks.3').priority === '2',
    'interface chrome and vocabulary are not priority 1: nav labels, the one-word "Play" labels, the track names');
  check(NON_EN.every((l) => JSON.stringify([...P1(l)]) === JSON.stringify([...p1])),
    'the same keys are priority 1 in every locale (the rule reads the key and the English, never the draft)');
  check(p1.size > 100 && p1.size < EN.size / 2, `priority 1 is a focused subset (${p1.size} of ${EN.size} keys)`);
}
{
  const gloss = rules.glossary.map((g) => g.term);
  check(['SCRIPTED', 'AUTHORED', 'RECORDED', 'DERIVED', 'MOCKED', 'PROPOSED'].every((t) => gloss.includes(t)) && rules.glossary.every((g) => g.stays_english === true && g.meaning.length > 20),
    'the glossary names SCRIPTED, AUTHORED, RECORDED, DERIVED, MOCKED, PROPOSED, each with a meaning, each staying in English');
}
// ---------------------------------------------------------------- where ---
{
  const label2file = (p) => (existsSync(join(ROOT, `web/trade_craft_${p}.html`)) ? `web/trade_craft_${p}.html` : `${p}.html`);
  const dec = (s) => s.replace(/&ldquo;|&rdquo;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;|&rsquo;/g, "'").replace(/\s+/g, ' ');
  const cache = new Map(); const page = (f) => { if (!cache.has(f)) cache.set(f, readFileSync(join(ROOT, f), 'utf8')); return cache.get(f); };
  const rows = sheets.de.rows.filter((_, i) => i % 23 === 0);
  const bad = [];
  let pagesChecked = 0;
  for (const r of rows) {
    const m = /^pages: ([^|]*?)(?: \+\d+ more)?(?: \| |$)/.exec(r.appears_in);
    if (!m) continue;
    const tok = r.key.startsWith('strings.') ? r.key.slice(8) : null;
    const en0 = dec(r.english).replace(/\{\w+\}/g, '\u0000').split('\u0000').sort((a, b) => b.length - a.length)[0];
    for (const p of m[1].split(', ')) {
      const f = label2file(p.trim()); pagesChecked++;
      if (!existsSync(join(ROOT, f))) { bad.push(`${r.key}: page ${p} is not a file`); continue; }
      const raw = page(f);
      const hit = (tok && (raw.includes(`"${tok}"`) || raw.includes(`'${tok}'`))) || dec(raw).includes(en0) || dec(raw.replace(/\\u2019/g, "'").replace(/\\'/g, "'")).includes(en0);
      if (!hit) bad.push(`${r.key} not in ${f}`);
    }
    for (const c of [...r.appears_in.matchAll(/code: ([^|]*)/g)].flatMap((x) => x[1].replace(/ \+\d+ more/, '').split(', '))) {
      if (/\(dynamic\)/.test(c) || !tok) continue;
      const f = c.trim();
      if (!existsSync(join(ROOT, f)) || !(page(f).includes(`'${tok}'`) || page(f).includes(`"${tok}"`))) bad.push(`${r.key}: code file ${f} does not name the key`);
    }
  }
  check(bad.length === 0 && pagesChecked > 20, `appears_in is backed by the files: every listed page and code file of ${rows.length} sampled keys contains the key or its text (${pagesChecked} page links checked${bad.length ? '; ' + bad.slice(0, 3).join('; ') : ''})`);
  const row = (k) => sheets.de.rows.find((r) => r.key === k);
  check(/pages: .*\b3d\b/.test(row('strings.sim.slowNotice').appears_in) && /pages: .*\blanding\b/.test(row('strings.landing.footer.disclaimer').appears_in)
    && /web\/build_landing\.py/.test(row('strings.landing.footer.disclaimer').appears_in),
    'known lines are located: the seat notice on the 3D campus page, the landing disclaimer on the landing page and in its builder');
  const none = sheets.de.rows.filter((r) => r.appears_in.startsWith('not found')).length;
  const sum = JSON.parse(readFileSync(join(HERE, 'review/summary.json'), 'utf8'));
  check(none === sum.keys_with_no_derived_location && none < 100, `${none} keys have no derivable location and say so rather than guess (summary.json agrees)`);
}
// ----------------------------------------------------------------- html ---
for (const l of NON_EN) {
  const h = readFileSync(join(OUT, `${l}.html`), 'utf8');
  const rtl = load(l).dir === 'rtl';
  check(h.startsWith('<!doctype html>') && h.includes(`<html lang="${l}" dir="${rtl ? 'rtl' : 'ltr'}">`), `${l}.html declares lang="${l}" dir="${rtl ? 'rtl' : 'ltr'}"`);
  check((h.match(/<tr data-key="/g) ?? []).length === EN.size, `${l}.html carries one table row per key (${EN.size})`);
  check(rules.glossary.every((g) => h.includes(`<dt>${g.term}</dt>`)) && !/<script[^>]+src=|<link[^>]+href=|https?:\/\//.test(h),
    `${l}.html shows the glossary and is self-contained (no external script, stylesheet or link)`);
}
{
  const h = readFileSync(join(OUT, 'de.html'), 'utf8');
  check(h.includes('&lt;b&gt;') && !/<td class="en"[^>]*><b>/.test(h), 'html: markup in a source string is shown as text for the reviewer, never run as markup');
  check((() => { try { new Function(/<script>([\s\S]*?)<\/script>/.exec(h)[1]); return true; } catch { return false; } })(),
    'html: the page script compiles (the fill, filter and download code is valid JavaScript)');
  const ar = readFileSync(join(OUT, 'ar.html'), 'utf8');
  check(/class="dr" lang="ar" dir="rtl"/.test(ar) && /<textarea lang="ar" dir="rtl"/.test(ar) && /<td class="en" lang="en" dir="ltr">/.test(ar),
    'ar.html: draft and correction boxes are right-to-left, the English column stays left-to-right');
}
// -------------------------------------------------- summary and --check ---
{
  const sum = JSON.parse(readFileSync(join(HERE, 'review/summary.json'), 'utf8'));
  check(NON_EN.every((l) => sum.locales[l]?.keys === EN.size && sum.locales[l].p1 === sheets[l].rows.filter((r) => r.priority === '1').length
    && sum.locales[l].p1 + sum.locales[l].p2 + sum.locales[l].p3 === EN.size), 'summary.json counts equal the sheets: keys and priority 1/2/3 per locale');
  check(NON_EN.every((l) => sum.locales[l].p1_checked_by_native === expectedStatus(en, load(l), ledgerOf(ROOT, l)).s1 && sum.locales[l].checked_by_native === expectedStatus(en, load(l), ledgerOf(ROOT, l)).cur),
    'summary.json records how many keys and how many safety and honesty (priority 1) keys have a current verdict, equal to the ledgers');
  check(/^[0-9a-f]{64}$/.test(sum.source_stamp) && sum.files_read > 200, `summary.json carries a sha256 source_stamp over every file the build read (${sum.files_read} files)`);
  const c = py(['i18n/build_review.py', '--check']);
  check(c.status === 0, `build_review.py --check is current (${(c.status ? c.stderr : c.stdout).trim().slice(0, 140)})`);
  check(/^\/dist\/$/m.test(readFileSync(join(ROOT, '.gitignore'), 'utf8')) && !existsSync(join(ROOT, 'dist/review/__tracked__')),
    'sheets are build outputs: written to dist/ (gitignored), not committed; the verdicts live in i18n/review/*.ledger.json');
}

// ======================================== status honest against the ledger ===
for (const l of NON_EN) {
  const cat = load(l), led = ledgerOf(ROOT, l), want = expectedStatus(en, cat, led);
  const stale = Object.keys(led.entries).filter((k) => !EN.has(k));
  check(cat.translation_status === want.status && stale.length === 0
    && (want.cur === 0 ? cat.reviewer === undefined && cat.reviewed_at === undefined : cat.reviewer === want.reviewer && cat.reviewed_at === want.at),
    `${l}: translation_status "${cat.translation_status}" is exactly what its ledger supports (${want.cur} of ${want.total} keys with a current verdict)`);
  check(Object.values(led.entries).every((e) => ['ok', 'fix'].includes(e.verdict) && e.reviewed_by?.trim() && /^\d{4}-\d{2}-\d{2}$/.test(e.reviewed_at) && !/@/.test(e.reviewed_by)),
    `${l}: every ledger entry has a verdict (ok/fix), a reviewer name and a date, and no email address`);
  check(validateCatalog(l, cat).length === 0 && isKnownStatus(cat.translation_status),
    `${l}: the catalog validates (a part-checked status names a reviewer and a date)`);
}
check(NON_EN.every((l) => !/^reviewed$/.test(load(l).translation_status) || expectedStatus(en, load(l), ledgerOf(ROOT, l)).cur === EN.size),
  'no catalog reads "reviewed" unless every key has a current verdict');

// ============================================================== fixture ===
const FIX_EN = {
  locale: 'en', language: 'English', english_name: 'English', dir: 'ltr', translation_status: 'source language',
  strings: {
    'honesty.demo': 'Nothing here is SCRIPTED by a model and nothing certifies anybody.',
    'nav.home': 'Home',
    'demo.count': '{n} halls open',
    'demo.rich': 'Read <b>this</b> first, please.',
    'demo.long': 'A longer sentence of ordinary page copy with no special words in it.',
    'demo.term': 'AUTHORED by rule, for play.',
  },
  districts: { alpha: { name: 'Alpha', tagline: 'The first one' } },
  tracks: ['One', 'Two'],
};
const FIX_DE = {
  locale: 'de', language: 'Deutsch', english_name: 'German', dir: 'ltr', translation_status: PENDING,
  strings: {
    'honesty.demo': 'Nichts hier wird von einem Modell SCRIPTED und nichts zertifiziert jemanden.',
    'nav.home': 'Startseite',
    'demo.count': '{n} Hallen offen',
    'demo.rich': 'Lies <b>dies</b> zuerst, bitte.',
    'demo.long': 'Ein längerer Satz gewöhnlicher Seitentexte ohne besondere Wörter darin.',
    'demo.term': 'AUTHORED nach Regel, zum Spielen.',
  },
  districts: { alpha: { name: 'Alfa', tagline: 'Der erste' } },
  tracks: ['Eins', 'Zwei'],
};
const dump = (o) => JSON.stringify(o, null, 1) + '\n';
const SBX = mkdtempSync(join(tmpdir(), 'review-fixture-'));
const base = join(SBX, 'base');
mkdirSync(join(base, 'i18n', 'locales'), { recursive: true });
for (const f of ['build_review.py', 'review_lib.py', 'ingest_review.py', 'review_rules.json']) cpSync(join(HERE, f), join(base, 'i18n', f));
writeFileSync(join(base, 'i18n/locales/en.json'), dump(FIX_EN));
writeFileSync(join(base, 'i18n/locales/de.json'), dump(FIX_DE));
const copy = (n) => { const d = join(SBX, n); cpSync(base, d, { recursive: true }); return d; };
const read = (d, rel) => readFileSync(join(d, rel), 'utf8');
const buildFix = (d) => { const o = join(d, 'out'); const r = py(['i18n/build_review.py', '--root', d, '--out', o, '--no-summary'], d); return { r, text: existsSync(join(o, 'de.csv')) ? readFileSync(join(o, 'de.csv'), 'utf8') : '' }; };
function fill(text, edits, who) {          // edits: { key: [verdict, corrected, notes] } -> filled CSV text
  const all = parseCsv(text); const h = all.findIndex((r) => r[0] === 'key'); const H = all[h];
  const out = all.slice(0, h).map((r) => r.slice());
  if (who) out.push([`# reviewer: ${who}`]);
  out.push(H);
  for (const r of all.slice(h + 1)) {
    const e = edits[r[0]]; const c = r.slice();
    if (e) { c[H.indexOf('verdict')] = e[0]; c[H.indexOf('corrected')] = e[1] ?? ''; c[H.indexOf('notes')] = e[2] ?? ''; }
    out.push(c);
  }
  return toCsv(out);
}
const ingest = (d, sheetText, extra = ['--reviewer', 'T.R.', '--date', '2026-10-01']) => {
  const f = join(d, 'filled.csv'); writeFileSync(f, sheetText);
  return py(['i18n/ingest_review.py', f, '--root', d, ...extra], d);
};

const fx = copy('rt');
const b1 = buildFix(fx);
check(b1.r.status === 0 && sheetRows(b1.text).rows.length === 10, `fixture: the builder works on a small catalog pair outside the repository (10 rows; exit ${b1.r.status})`);
const rows1 = sheetRows(b1.text).rows;
check(rows1.find((r) => r.key === 'strings.honesty.demo').priority === '1' && rows1.find((r) => r.key === 'strings.nav.home').priority === '2'
  && rows1.find((r) => r.key === 'strings.demo.long').priority === '3' && rows1.find((r) => r.key === 'strings.demo.term').priority === '1',
  'fixture: priorities 1 (honesty key, AUTHORED label), 2 (nav label) and 3 (page copy) are assigned');
check(rows1[0].priority === '1' && rows1.at(-1).priority !== '1' && rows1.every((r) => r.appears_in.startsWith('not found')), 'fixture: ordered by priority; with no page or code naming a key the sheet says so');

const FIXED = 'Startseite der Hallen';
let r = ingest(fx, fill(b1.text, {
  'strings.honesty.demo': ['ok'],
  'strings.nav.home': ['fix', FIXED, 'shorter in German'],
}));
const after = read(fx, 'i18n/locales/de.json');
const deAfter = JSON.parse(after);
check(r.status === 0, `round trip: a sheet with one ok and one fix is ingested (exit ${r.status} ${r.stderr.slice(0, 150)})`);
check(deAfter.strings['nav.home'] === FIXED && deAfter.strings['honesty.demo'] === FIX_DE.strings['honesty.demo']
  && Object.keys(deAfter.strings).filter((k) => k !== 'nav.home').every((k) => deAfter.strings[k] === FIX_DE.strings[k]) && deAfter.districts.alpha.name === 'Alfa',
  'round trip: only the corrected key changed in the catalog; every other value is untouched');
const led = JSON.parse(read(fx, 'i18n/review/de.ledger.json'));
check(Object.keys(led.entries).sort().join() === 'strings.honesty.demo,strings.nav.home'
  && led.entries['strings.nav.home'].verdict === 'fix' && led.entries['strings.nav.home'].was === 'Startseite'
  && led.entries['strings.honesty.demo'].verdict === 'ok' && led.entries['strings.honesty.demo'].reviewed_by === 'T.R.' && led.entries['strings.honesty.demo'].reviewed_at === '2026-10-01',
  'round trip: the ledger records exactly the two keys given a verdict, with reviewer, date, verdict and the replaced draft');
check(deAfter.translation_status === 'machine-drafted; 2 of 10 keys checked by a native speaker, 1 of 2 safety and honesty lines' && deAfter.reviewer === 'T.R.' && deAfter.reviewed_at === '2026-10-01'
  && validateCatalog('de', deAfter).length === 0 && PARTIAL_STATUS_RE.test(deAfter.translation_status),
  'round trip: translation_status is "machine-drafted; 2 of 10 keys checked by a native speaker, 1 of 2 safety and honesty lines" with reviewer and date, and catalog.mjs validates it');
{
  const want = expectedStatus(FIX_EN, deAfter, led);
  check(want.cur === 2 && want.status === deAfter.translation_status, 'round trip: the JavaScript recount of the ledger (sha256 of English and text) agrees with the Python status');
}
const b2 = buildFix(fx);
const rows2 = sheetRows(b2.text).rows;
check(rows2.find((x) => x.key === 'strings.nav.home').status === 'fix by T.R. on 2026-10-01' && rows2.find((x) => x.key === 'strings.nav.home').draft === FIXED
  && rows2.find((x) => x.key === 'strings.demo.long').status === 'not reviewed' && rows2.filter((x) => x.status === 'not reviewed').length === 8,
  'round trip: a rebuilt sheet shows the corrected text as the draft and who checked which key; the other 8 stay "not reviewed"');
// stale: the English moves, the verdict stops counting
{
  const st = copy('stale');
  cpSync(fx, st, { recursive: true });
  const enc = JSON.parse(read(st, 'i18n/locales/en.json')); enc.strings['honesty.demo'] += ' Changed.';
  writeFileSync(join(st, 'i18n/locales/en.json'), dump(enc));
  const dec = JSON.parse(read(st, 'i18n/locales/de.json')); dec.strings['honesty.demo'] += ' Geändert.';
  writeFileSync(join(st, 'i18n/locales/de.json'), dump(dec));
  const s = py(['i18n/ingest_review.py', '--sync', 'de', '--root', st], st);
  const after2 = JSON.parse(read(st, 'i18n/locales/de.json'));
  check(s.status === 0 && after2.translation_status === 'machine-drafted; 1 of 10 keys checked by a native speaker, 0 of 2 safety and honesty lines',
    'staleness: when the English or the text changes after a verdict, that verdict stops counting (2 -> 1 of 10, the safety line 1 -> 0 of 2) and --sync restates the status');
  const bs = buildFix(st);
  check(sheetRows(bs.text).rows.find((x) => x.key === 'strings.honesty.demo').status.startsWith('review out of date'), 'staleness: the rebuilt sheet marks that row "review out of date"');
}
// the English alone moves (the draft is untouched): that verdict stops counting too
{
  const st = copy('stale2'); cpSync(fx, st, { recursive: true });
  const enc = JSON.parse(read(st, 'i18n/locales/en.json')); enc.strings['nav.home'] = 'Home page';
  writeFileSync(join(st, 'i18n/locales/en.json'), dump(enc));
  const s = py(['i18n/ingest_review.py', '--sync', 'de', '--root', st], st);
  check(s.status === 0 && JSON.parse(read(st, 'i18n/locales/de.json')).translation_status === 'machine-drafted; 1 of 10 keys checked by a native speaker, 1 of 2 safety and honesty lines',
    'staleness: when only the English source changes, the verdict on that key stops counting (2 -> 1 of 10)');
}
// nine of ten is still not "reviewed"
{
  const nine = copy('nine'); cpSync(fx, nine, { recursive: true });
  const todo = rows2.filter((x) => x.status === 'not reviewed').slice(0, -1);
  const e9 = Object.fromEntries(todo.map((x) => [x.key, ['ok']]));
  const r9 = ingest(nine, fill(b2.text, e9), ['--reviewer', 'Q.Z.', '--date', '2026-10-02']);
  const d9 = JSON.parse(read(nine, 'i18n/locales/de.json'));
  check(r9.status === 0 && d9.translation_status === 'machine-drafted; 9 of 10 keys checked by a native speaker, 2 of 2 safety and honesty lines' && d9.reviewer === 'Q.Z., T.R.',
    'nine of ten keys with a verdict is "machine-drafted; 9 of 10 keys checked by a native speaker, 2 of 2 safety and honesty lines", not "reviewed"');
}
// checking only interface labels leaves the safety and honesty lines at zero, and the status says so
{
  const ui = copy('uionly'); cpSync(base, ui, { recursive: true });
  const r0 = ingest(ui, fill(buildFix(ui).text, { 'strings.nav.home': ['ok'], 'tracks.0': ['ok'] }));
  const d0 = JSON.parse(read(ui, 'i18n/locales/de.json'));
  check(r0.status === 0 && d0.translation_status === 'machine-drafted; 2 of 10 keys checked by a native speaker, 0 of 2 safety and honesty lines' && !/reviewed/.test(d0.translation_status),
    'checking only interface labels reads "2 of 10 keys, 0 of 2 safety and honesty lines", and the part-checked wording never contains "reviewed"');
}
check([
  ['machine-drafted; 3 of 10 keys checked by a native speaker, 4 of 2 safety and honesty lines'],
  ['machine-drafted; 1 of 10 keys checked by a native speaker, 2 of 2 safety and honesty lines'],
  ['machine-drafted; 9 of 10 keys checked by a native speaker, 0 of 3 safety and honesty lines'],
  ['machine-drafted; 3 of 10 keys checked by a native speaker'],
].every(([st]) => validateCatalog('x', { translation_status: st, reviewer: 'AB', reviewed_at: '2026-10-01' }).length > 0)
  && validateCatalog('x', { translation_status: 'machine-drafted; 3 of 10 keys checked by a native speaker, 1 of 2 safety and honesty lines', reviewer: 'AB', reviewed_at: '2026-10-01' }).length === 0,
  'catalog.mjs refuses impossible safety-and-honesty counts (more than the keys checked, more than the lines, too few non-safety keys) and the old wording without them');
// finishing every key makes the catalog "reviewed", with every reviewer named
{
  const edits = {};
  for (const x of rows2) if (x.status === 'not reviewed') edits[x.key] = ['ok'];
  const rf = ingest(fx, fill(b2.text, edits, 'J. Alvarez'), ['--date', '2026-10-02', '--strict']);
  const fin = JSON.parse(read(fx, 'i18n/locales/de.json'));
  check(rf.status === 0 && fin.translation_status === 'reviewed' && fin.reviewer === 'J. Alvarez, T.R.' && fin.reviewed_at === '2026-10-02' && validateCatalog('de', fin).length === 0,
    `round trip: when all 10 keys hold a current verdict the status is "reviewed" with both reviewers named, the later date, and the reviewer taken from the sheet's own row (exit ${rf.status})`);
}

// refusals: each in a fresh copy of the original; the catalog is byte-identical and no ledger appears
const refusals = [
  ['an unknown key', { 'strings.no.such.key': ['ok'] }, /unknown key/, 'strings.no.such.key,Home,Startseite,x,2,short_label,not reviewed,ok,,\r\n'],
  ['a blank verdict with corrected text', { 'strings.nav.home': ['', 'Startseite neu'] }, /verdict is blank/],
  ['a blank verdict with only notes', { 'strings.nav.home': ['', '', 'looks odd'] }, /verdict is blank/],
  ['a verdict that is neither ok nor fix', { 'strings.nav.home': ['maybe'] }, /not ok or fix/],
  ['ok with corrected text', { 'strings.nav.home': ['ok', 'Startseite neu'] }, /verdict ok but corrected/],
  ['fix with no corrected text', { 'strings.nav.home': ['fix'] }, /no corrected text/],
  ['fix identical to the English source', { 'strings.nav.home': ['fix', 'Home'] }, /identical to the English/],
  ['fix identical to the draft', { 'strings.nav.home': ['fix', 'Startseite'] }, /same as the draft/],
  ['fix that loses a {placeholder}', { 'strings.demo.count': ['fix', 'Hallen offen'] }, /placeholders differ/],
  ['fix that changes the markup', { 'strings.demo.rich': ['fix', 'Lies dies zuerst, bitte.'] }, /markup differs/],
  ['fix that drops a glossary label', { 'strings.demo.term': ['fix', 'VERFASST nach Regel, zum Spielen.'] }, /glossary label AUTHORED/],
  ...[['=', 'equals'], ['+', 'plus'], ['-', 'minus'], ['@', 'at sign'], ['\t', 'tab'], ['\r', 'carriage return']].map(([ch, nm]) =>
    [`a fix whose text starts with a ${nm} (a spreadsheet formula leader)`, { 'strings.nav.home': ['fix', `${ch}Startseite neu`] }, /starts with a character a spreadsheet would run as a formula/]),
  ['an email address in the notes', { 'strings.nav.home': ['ok', '', 'mail me at a.b@example.org'] }, /email address/],
];
for (const [name, edits, re, extraRow] of refusals) {
  const d = copy('ref'); const bt = buildFix(d).text;
  const res = ingest(d, fill(bt, edits) + (extraRow ?? ''));
  check(res.status === 1 && re.test(res.stderr) && read(d, 'i18n/locales/de.json') === read(base, 'i18n/locales/de.json') && !existsSync(join(d, 'i18n/review/de.ledger.json')),
    `refused, nothing written: ${name} (exit ${res.status}; ${re})`);
  rmSync(d, { recursive: true, force: true });
}
{
  const d = copy('ref2'); const bt = buildFix(d).text;
  const stale = bt.replace('Startseite', 'Heimseite');
  const res = ingest(d, fill(stale, { 'strings.nav.home': ['ok'] }));
  check(res.status === 1 && /draft column no longer matches/.test(res.stderr) && !existsSync(join(d, 'i18n/review/de.ledger.json')),
    'refused: a sheet whose draft column no longer matches the catalog is out of date (rebuild it)');
  const dup = ingest(d, fill(bt, { 'strings.nav.home': ['ok'] }) + 'strings.nav.home,Home,Startseite,x,2,short_label,not reviewed,ok,,\r\n');
  check(dup.status === 1 && /more than once/.test(dup.stderr), 'refused: the same key twice in one sheet');
  const mixed = ingest(d, fill(bt, { 'strings.honesty.demo': ['ok'], 'strings.nav.home': ['fix', 'Home'] }));
  check(mixed.status === 1 && !existsSync(join(d, 'i18n/review/de.ledger.json')) && read(d, 'i18n/locales/de.json') === read(base, 'i18n/locales/de.json'),
    'all or nothing: one valid ok plus one refused fix writes neither the ok nor the fix');
  const none = ingest(d, fill(bt, {}));
  check(none.status === 1 && /no row carries a verdict/.test(none.stderr) && !existsSync(join(d, 'i18n/review/de.ledger.json')),
    'a returned sheet with no verdict anywhere marks nothing reviewed (refused, nothing written)');
  const strict = ingest(d, fill(bt, { 'strings.nav.home': ['ok'] }), ['--reviewer', 'T.R.', '--date', '2026-10-01', '--strict']);
  check(strict.status === 1 && /--strict: 9 key/.test(strict.stderr), '--strict refuses a whole-sheet return in which keys have no verdict (9 of 10 missing)');
  const dry = ingest(d, fill(bt, { 'strings.nav.home': ['ok'] }), ['--reviewer', 'T.R.', '--date', '2026-10-01', '--dry-run']);
  check(dry.status === 0 && !existsSync(join(d, 'i18n/review/de.ledger.json')) && read(d, 'i18n/locales/de.json') === read(base, 'i18n/locales/de.json'), '--dry-run reports and writes nothing');
  for (const [name, args, re] of [
    ['a reviewer with an email address', ['--reviewer', 'a.b@example.org', '--date', '2026-10-01'], /not an email/],
    ['no reviewer at all', ['--date', '2026-10-01'], /reviewer name or initials is required/],
    ['a date in the future', ['--reviewer', 'T.R.', '--date', '2999-01-01'], /future/],
    ['a date that is not a date', ['--reviewer', 'T.R.', '--date', '2026-13-45'], /real calendar date/],
  ]) {
    const x = ingest(d, fill(bt, { 'strings.nav.home': ['ok'] }), args);
    check(x.status === 1 && re.test(x.stderr) && !existsSync(join(d, 'i18n/review/de.ledger.json')), `refused, nothing written: ${name}`);
  }
}
// the HTML page's download path produces a sheet the ingest accepts
{
  const html = readFileSync(join(OUT, 'de.html'), 'utf8');
  const js = /<script>([\s\S]*?)<\/script>/.exec(html)[1];
  const fn = /function esc\([\s\S]*?window\.__reviewToCsv=toCsv;/.exec(js)[0];
  const sandbox = { window: {} };
  new Function('window', `var COLS=${JSON.stringify(COLUMNS)}, LOC="de"; ${fn}`)(sandbox.window);
  const d = copy('html'); const bt = buildFix(d).text;
  const row = sheetRows(bt).rows.find((x) => x.key === 'strings.nav.home');
  const csv = sandbox.window.__reviewToCsv([{ ...row, verdict: 'fix', corrected: 'Start, "Halle"\nzwei Zeilen?', notes: 'quote, comma' }], 'Ana B.');
  const parsed = parseCsv(csv);
  check(csv.startsWith('\ufeff#locale=de') && parsed.find((p) => p[0] === 'strings.nav.home')[8] === 'Start, "Halle"\nzwei Zeilen?', 'html download: the page builds a BOM-prefixed CSV with the #locale row and quotes commas, quotes and newlines correctly');
  const clean = { ...row, verdict: 'fix', corrected: 'Startseite der Halle', notes: 'quote, comma' };
  const ok2 = ingest(d, sandbox.window.__reviewToCsv([clean], 'Ana B.'), ['--date', '2026-10-01']);
  check(ok2.status === 0 && JSON.parse(read(d, 'i18n/locales/de.json')).strings['nav.home'] === 'Startseite der Halle'
    && JSON.parse(read(d, 'i18n/review/de.ledger.json')).entries['strings.nav.home'].reviewed_by === 'Ana B.',
    `html download: a file the page produced is ingested with no flags; the reviewer name comes from the sheet (exit ${ok2.status} ${ok2.stderr.slice(0, 120)})`);
}
// spreadsheets save what their locale says: semicolons, tabs, or UTF-16 "Unicode text"; all are read
{
  const d = copy('sheetfmt'); const bt = buildFix(d).text;
  const filled = fill(bt, { 'strings.nav.home': ['fix', 'Startseite der Halle', 'Semikolon, Komma'], 'strings.honesty.demo': ['ok'] });
  const grid = parseCsv(filled);
  const semi = '\ufeff' + grid.map((r) => r.map((c) => (/[";\r\n]/.test(c) ? `"${c.replace(/"/g, '""')}"` : c)).join(';')).join('\r\n') + '\r\n';
  const rs = ingest(d, semi);
  check(rs.status === 0 && JSON.parse(read(d, 'i18n/locales/de.json')).strings['nav.home'] === 'Startseite der Halle', `a semicolon-separated sheet (what a spreadsheet in a decimal-comma locale saves) is ingested (exit ${rs.status})`);
  const d2 = copy('sheetfmt2'); const f2 = join(d2, 'u16.csv');
  const tab = grid.map((r) => r.map((c) => (/["\t\r\n]/.test(c) ? `"${c.replace(/"/g, '""')}"` : c)).join('\t')).join('\r\n') + '\r\n';
  writeFileSync(f2, Buffer.concat([Buffer.from([0xff, 0xfe]), Buffer.from(tab, 'utf16le')]));
  const r16 = py(['i18n/ingest_review.py', f2, '--root', d2, '--reviewer', 'T.R.', '--date', '2026-10-01'], d2);
  check(r16.status === 0 && JSON.parse(read(d2, 'i18n/locales/de.json')).strings['nav.home'] === 'Startseite der Halle', `a UTF-16 tab-separated "Unicode text" sheet is ingested (exit ${r16.status})`);
  writeFileSync(f2, Buffer.from([0x53, 0xe4, 0x68]));
  const rl = py(['i18n/ingest_review.py', f2, '--root', d2, '--reviewer', 'T.R.'], d2);
  check(rl.status === 2 && /not UTF-8/.test(rl.stderr), 'a file that is not UTF-8 is refused with the instruction to save as CSV UTF-8');
}
rmSync(OUT, { recursive: true, force: true });
rmSync(SBX, { recursive: true, force: true });
console.log(`i18n/test_review: ${oks} checks passed${fails ? `, ${fails} FAILED` : ''}`);
process.exit(fails ? 1 : 0);
