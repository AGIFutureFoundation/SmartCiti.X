/**
 * web/test_verify.mjs — the verify page runs the command line's own rules.
 *
 *   node web/test_verify.mjs
 *
 * Static and node-executed, no browser, no network. Holds:
 *   - the page's two cores are completion/verify.mjs's and contrib/verify.mjs's
 *     marked blocks, byte for byte;
 *   - the recovery block is the AUTH-CORE region auth/recover.mjs lifts;
 *   - every embedded registry is its file verbatim, and the set is exactly the
 *     REGISTRY_FILES the two verifiers declare;
 *   - the page's cores, lifted out of the page and run in node with node's
 *     webcrypto.subtle as the sha256, give over EVERY fixture and mutant of
 *     both packs (and over a wallet-signed record of each, signed here with a
 *     throwaway key) the same exit, the same failing rule names and the same
 *     printed lines as the CLI; each mutant fails by exactly the rule its
 *     registry names;
 *   - the page reaches no network: no fetch, XHR, beacon, socket, worker,
 *     form or remote resource;
 *   - the honest last lines are the verifiers' verbatim.
 * Prints "  ok  <text>" per check; FAIL at column 0 and exit 1 on the first
 * failure.
 */
import { readFileSync, readdirSync, writeFileSync, mkdtempSync, rmSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { webcrypto } from 'node:crypto';

const ROOT = fileURLToPath(new URL('..', import.meta.url));
const PAGE_PATH = 'web/trade_craft_verify.html';
const R = (p) => readFileSync(join(ROOT, p), 'utf8');
let n = 0;
function ok(text, cond, detail) {
  if (!cond) {
    console.error('FAIL ' + text);
    if (detail !== undefined) console.error('     ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)));
    process.exit(1);
  }
  n++;
  console.log('  ok  ' + text);
}

const page = R(PAGE_PATH);
const PACKS = [
  { pack: 'completion', file: 'completion/verify.mjs', begin: '/* COMPLETION_CORE:BEGIN', end: '/* COMPLETION_CORE:END */', fn: 'completionCore', scriptId: 'completion-core' },
  { pack: 'contrib', file: 'contrib/verify.mjs', begin: '/* CONTRIB_CORE:BEGIN', end: '/* CONTRIB_CORE:END */', fn: 'contribCore', scriptId: 'contrib-core' },
];
function marked(src, begin, end) {
  const a = src.indexOf(begin), b = src.indexOf(end);
  if (a < 0 || b <= a || src.indexOf(begin, a + 1) >= 0) return null;
  return src.slice(a, b + end.length);
}
function scriptById(id) {
  const m = page.match(new RegExp('<script id="' + id + '">\\n([\\s\\S]*?)</script>'));
  return m ? m[1] : null;
}

/* ------------------------------------------------ the cores, byte for byte */
const CORE_SRC = {};
for (const P of PACKS) {
  const cli = marked(R(P.file), P.begin, P.end);
  const inPage = scriptById(P.scriptId);
  CORE_SRC[P.pack] = inPage === null ? null : inPage.replace(/\n$/, '');
  ok(`the page's ${P.pack} core is ${P.file}'s ${P.begin.slice(3)} ... END block byte for byte (${cli === null ? 0 : cli.length} chars)`,
    cli !== null && CORE_SRC[P.pack] === cli && cli.includes(`function ${P.fn}(regs) {`));
}

/* ----------------------------------------------------- the recovery block */
const { CORE_SOURCE } = await import(new URL('../auth/recover.mjs', import.meta.url));
const authScript = scriptById('auth-core');
{
  const pre = 'const AUTH = (function () {\n', post = '\nreturn { recoverAddress: recoverAddress };\n})();\n';
  ok('the page\'s recovery is exactly the AUTH-CORE region auth/recover.mjs lifts from the sign-in page, wrapped to expose recoverAddress alone',
    authScript !== null && authScript === pre + CORE_SOURCE + post);
}

/* ------------------------------------------------------ the registries */
const embedded = {};
for (const m of page.matchAll(/<script type="application\/json" data-registry="([^"]+)">([\s\S]*?)<\/script>/g)) embedded[m[1]] = m[2];
const KINDS = JSON.parse(page.match(/<script type="application\/json" id="verify-kinds">([\s\S]*?)<\/script>/)[1]);
const declared = {};
for (const P of PACKS) declared[P.pack] = (await import(new URL('../' + P.file, import.meta.url))).REGISTRY_FILES;
{
  const want = [...new Set(PACKS.flatMap((P) => Object.values(declared[P.pack])))].sort();
  ok(`the page embeds exactly the ${want.length} registries the two verifiers declare in REGISTRY_FILES`,
    JSON.stringify(Object.keys(embedded).sort()) === JSON.stringify(want), Object.keys(embedded));
  const drift = Object.keys(embedded).filter((p) => embedded[p] !== R(p));
  ok('every embedded registry is its file verbatim', drift.length === 0, drift);
  ok('the page\'s kind map names each core, its REGISTRY_FILES and the record_tag its own registry declares',
    KINDS.length === 2 && PACKS.every((P, i) => KINDS[i].core === P.fn && KINDS[i].verifier === P.file
      && JSON.stringify(KINDS[i].files) === JSON.stringify(declared[P.pack])
      && KINDS[i].tag === JSON.parse(R(Object.values(declared[P.pack])[0])).record_tag)
    && KINDS.map((k) => k.tag).join() === 'tc-completion/1,tc-contribution/1', KINDS.map((k) => k.tag));
}

/* ---------------------------------------------- no network, no storage */
const scripts = [...page.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)];
// The site style scripts (design_kit STYLE_HEAD_JS, sitenav STYLE_JS; AUDIT row 12) are the one carve-out, the
// same narrow one lessons/test.mjs and web/test_schools.mjs carry: they may touch localStorage['tc-style'] only,
// get/set only, each access inside try/catch - held just below. Every other script is scanned in full.
const STYLE_IDS = /\bid="style-(?:head-)?js"/;
const styleScripts = scripts.filter((m) => STYLE_IDS.test(m[1]));
const code = scripts.filter((m) => !/type="application\/json"/.test(m[1]) && !STYLE_IDS.test(m[1])).map((m) => m[2]).join('\n');
{
  const bad = [];
  for (const [, , s] of styleScripts) {
    if (/sessionStorage|indexedDB|document\.cookie|fetch|XMLHttpRequest|removeItem|localStorage\.clear|localStorage\[|localStorage\.key\(/.test(s)) bad.push('an API other than localStorage get/set');
    const calls = [...s.matchAll(/localStorage\.(getItem|setItem)\(([^,)]+)/g)];
    for (const c of calls) {
      const k = c[2].trim();
      if (k !== "'tc-style'" && !(k === 'K' && /var K='tc-style'[,;]/.test(s))) bad.push(`storage key ${k} is not 'tc-style'`);
    }
    const guarded = (s.match(/try\{(?:var \w+=|\w+=)?localStorage\.(?:getItem|setItem)\(/g) || []).length;
    if (guarded !== calls.length) bad.push(`${calls.length - guarded} storage access(es) outside try/catch`);
  }
  ok('the saved site style applies here (style-head-js in <head>, style-js before </body>), and those two scripts touch only localStorage[\'tc-style\'], get/set, inside try/catch',
    styleScripts.length === 2 && page.indexOf('id="style-head-js"') < page.indexOf('</head>') && bad.length === 0, bad);
}
const markup = page.replace(/<script[^>]*>[\s\S]*?<\/script>/g, '').replace(/<style>[\s\S]*?<\/style>/g, '');
{
  const NET = [/\bfetch\b/, /XMLHttpRequest/, /sendBeacon/, /WebSocket/, /EventSource/, /RTCPeerConnection/, /importScripts/,
    /\bimport\s*\(/, /new\s+(Shared)?Worker\b/, /serviceWorker/, /\.src\s*=/, /\bwindow\.open\b/, /location\s*(\.href)?\s*=/,
    /localStorage/, /sessionStorage/, /indexedDB/, /document\.cookie/];
  const hits = NET.filter((rx) => rx.test(code)).map(String);
  ok('no script on the page holds a network or storage primitive (fetch, XHR, beacon, socket, worker, dynamic import, navigation, storage)',
    hits.length === 0, hits);
  const MARK = [/<form\b/i, /\baction=/i, /formaction/i, /<iframe\b/i, /<img\b/i, /<object\b/i, /<embed\b/i, /\bping=/i,
    /<script[^>]*\bsrc=/i, /<link\b(?![^>]*rel="icon"[^>]*href="data:)/i, /\bsrc="https?:/i, /href="https?:/i];
  const mh = MARK.filter((rx) => rx.test(markup)).map(String);
  ok('the markup has no form, no form action, no frame, no remote image, script, stylesheet or link out: nothing it could send to',
    mh.length === 0 && !/<script[^>]*\bsrc=/i.test(page), mh);
  ok('no script on the page names a remote origin', !/https?:\/\/(?!www\.w3\.org\/2000\/svg)/.test(code), (code.match(/https?:\/\/\S+/g) || []).slice(0, 3));
  ok('the page\'s scripts carry no nullish-coalescing default (??) and the builder no .get(k, default)',
    !code.includes('??') && !/[\w)\]]\.get\(/.test(R('web/build_verify.py')));
  ok('the page has one file input and a drop zone, read through FileReader in the tab',
    (page.match(/type="file"/g) || []).length === 1 && /id="drop"/.test(page)
    && /addEventListener\('drop'/.test(code) && /new FileReader\(\)/.test(code) && /readAsText\(file\)/.test(code));
}

/* ------------------------------------------------ the page's own glue */
const appJs = scriptById('verify-app');
{
  ok('the page dispatches on the record field to the core for that tag, and runs it with crypto.subtle and the lifted recoverAddress',
    appJs !== null && /const core = CORES\[d\.tag\];/.test(appJs)
    && appJs.includes('core.verifyAsync(d.record, window.crypto.subtle, AUTH.recoverAddress)')
    && appJs.includes('FACTORIES[k.core](regs)') && appJs.includes('completionCore: completionCore, contribCore: contribCore'));
  ok('the page renders one row per rule from the core\'s tally with its messages, the recovered signer, the core\'s own report lines and its last line',
    appJs.includes('for (const rule of Object.keys(result.tally))') && appJs.includes('for (const f of t.fails)')
    && appJs.includes('result.signature.recovered') && appJs.includes('core.report(result)')
    && appJs.includes("document.getElementById('last-line').textContent = core.LAST_LINE;")
    && appJs.includes('CORES[k.tag].LAST_LINE') && appJs.includes('core.errorLine(thrown)'));
  const detect = new Function(scriptById('verify-detect') + '\nreturn detectRecord;')();
  const tags = KINDS.map((k) => k.tag);
  const cases = [['{nope', /not JSON/], ['null', /not a record object/], ['[]', /not a record object/], ['{}', /no "record" field/],
    ['{"record":"tc-other/1"}', /"tc-other\/1".*does not verify/], ['{"record":7}', /record 7/]];
  ok('an unknown or unparseable file is named and nothing runs: ' + cases.map((c) => c[0]).join('  '),
    cases.every(([t, rx]) => { const d = detect(t, tags); return d.ok === false && rx.test(d.why) && /Nothing was run\./.test(d.why); })
    && appJs.includes("if (!d.ok) { say('unknown', name + ': ' + d.why); return; }"));
  ok('a record is detected by its record field alone',
    detect(R('completion/fixture/good.json'), tags).tag === 'tc-completion/1' && detect(R('contrib/fixture/good.json'), tags).tag === 'tc-contribution/1');
}

/* ------------------------- the page's cores, run in node, against the CLI */
const recover = new Function(authScript + '\nreturn AUTH;')().recoverAddress;
const REGS = Object.fromEntries(Object.entries(embedded).map(([p, t]) => [p, JSON.parse(t)]));
const CORE = {};
for (const [i, P] of PACKS.entries()) {
  const regs = Object.fromEntries(Object.entries(KINDS[i].files).map(([k, p]) => [k, REGS[p]]));
  CORE[P.pack] = new Function(CORE_SRC[P.pack] + '\nreturn ' + P.fn + ';')()(regs);
}
async function pageRun(core, text) {
  let rec, res = null, thrown = null;
  try { rec = JSON.parse(text); res = await core.verifyAsync(rec, webcrypto.subtle, recover); } catch (e) { thrown = e; }
  if (thrown !== null) {
    const line = core.errorLine(thrown);
    return { status: 1, fails: [line.replace(/^FAIL ([^:]+):[\s\S]*$/, '$1')], out: '', err: line + '\n', res };
  }
  const lines = core.report(res);
  const txt = (err) => lines.filter((l) => l.err === err).map((l) => l.text + '\n').join('');
  return { status: core.failed(res) ? 1 : 0, fails: Object.keys(res.tally).filter((r) => res.tally[r].fails.length), out: txt(false), err: txt(true), res };
}
function cliRun(file, path) {
  const r = spawnSync(process.execPath, [join(ROOT, file), path], { encoding: 'utf8' });
  return { status: r.status, fails: [...r.stderr.matchAll(/^FAIL ([^:\s]+):/gm)].map((m) => m[1]), out: r.stdout, err: r.stderr };
}
const same = (a, b) => a.status === b.status && a.fails.join() === b.fails.join() && a.out === b.out && a.err === b.err;

const expected = {
  completion: (() => { const m = JSON.parse(R('completion/registry/completion.json')).fixture.mutants; return Object.fromEntries(Object.entries(m).map(([f, r]) => [f.replace('fixture/', ''), r])); })(),
  contrib: (() => { const m = JSON.parse(R('contrib/registry/contrib.json')).fixture.mutants; return Object.fromEntries(Object.values(m).map((x) => [x.file.replace('fixture/', ''), x.fails])); })(),
};
for (const P of PACKS) {
  const dir = join(ROOT, P.pack, 'fixture');
  const files = readdirSync(dir).filter((f) => f.endsWith('.json')).sort();
  ok(`[${P.pack}] every mutant on disk is one the registry names with the rule it breaks (${files.length - 1} mutants + good.json)`,
    // wave 11: contrib gained schema-v2 fixtures (good-v2.json, v2-mutant-*.json); every mutant file, of any
    // version prefix, must still be one the registry names
    files.filter((f) => /(^|-)mutant-/.test(f)).every((f) => f in expected[P.pack]) && files.includes('good.json')
    && Object.keys(expected[P.pack]).every((f) => files.includes(f)));
  for (const f of files) {
    const text = readFileSync(join(dir, f), 'utf8');
    const pg = await pageRun(CORE[P.pack], text);
    const cli = cliRun(P.file, join(dir, f));
    const want = /^good(-v\d+)?\.json$/.test(f) ? [] : [expected[P.pack][f]];
    ok(`[${P.pack}] ${f}: the page's core, in node over webcrypto.subtle, prints what the CLI prints `
      + `(exit ${cli.status}, ${cli.fails.length ? 'FAIL ' + cli.fails.join(', ') : 'every rule ok'}) and fails by exactly the registry's rule`,
      same(pg, cli) && pg.fails.join() === want.join(), { page: pg.fails, cli: cli.fails, want, outSame: pg.out === cli.out, errSame: pg.err === cli.err });
  }
}

/* ----------------------------------------- signed, with a throwaway key */
{
  const CT = await import(new URL('../completion/test.mjs', import.meta.url));
  const KV = await import(new URL('../contrib/verify.mjs', import.meta.url));
  const key = CT.throwawayKey();
  const cSigned = CT.signRecord(JSON.parse(R('completion/fixture/good.json')), key);
  const kSigned = (() => {
    const out = JSON.parse(R('contrib/fixture/good.json'));
    out.contributor.claimed = key.address; out.contributor.attested_by = KV.SIGNED_ATTESTATION; out.contributor.signature = null;
    out.digest = { ...out.digest, hex: KV.digestOf(out) };
    const message = KV.signatureMessage(out.digest.hex, out.exported_at, out.consent.scope);
    out.contributor.signature = { scheme: KV.SIGNATURE_SCHEME, address: key.address, message, sig: CT.signPersonal(key.d, message) };
    return out;
  })();
  const flip = (rec, who) => { const r = JSON.parse(JSON.stringify(rec)); const u = Buffer.from(r[who].signature.sig.slice(2), 'hex'); u[40] ^= 1; r[who].signature.sig = '0x' + u.toString('hex'); return r; };
  const tmp = mkdtempSync(join(tmpdir(), 'tc-verify-page-'));
  try {
    for (const [P, rec, who, rule] of [[PACKS[0], cSigned, 'identity', 'identity.signature'], [PACKS[1], kSigned, 'contributor', 'contributor.signature']]) {
      const good = join(tmp, P.pack + '-signed.json'), bad = join(tmp, P.pack + '-signed-bitflip.json');
      writeFileSync(good, JSON.stringify(rec)); writeFileSync(bad, JSON.stringify(flip(rec, who)));
      const pg = await pageRun(CORE[P.pack], readFileSync(good, 'utf8')), cli = cliRun(P.file, good);
      ok(`[${P.pack}] signed with a throwaway key: the page's core recovers exactly that address through the lifted recovery, and prints what the CLI prints`,
        same(pg, cli) && pg.status === 0 && pg.res.signature.state === 'signed' && pg.res.signature.recovered === key.address
        && cli.out.includes('by ' + key.address), { page: pg.fails, sig: pg.res && pg.res.signature.line });
      const pb = await pageRun(CORE[P.pack], readFileSync(bad, 'utf8')), cb = cliRun(P.file, bad);
      ok(`[${P.pack}] one bit of that signature flipped: page and CLI both FAIL ${rule} alone, with the same lines`,
        same(pb, cb) && pb.fails.join() === rule, { page: pb.fails, cli: cb.fails });
    }
  } finally { rmSync(tmp, { recursive: true, force: true }); }
}

/* ------------------------------------------------ the honest last lines */
{
  const contribLine = JSON.parse(R('contrib/registry/contrib.json')).verifier.last_line;
  const cliC = cliRun('completion/verify.mjs', join(ROOT, 'completion/fixture/good.json'));
  const cliK = cliRun('contrib/verify.mjs', join(ROOT, 'contrib/fixture/good.json'));
  ok('the contribution honest line on the page is contrib.json#verifier.last_line verbatim, and the CLI\'s last line',
    CORE.contrib.LAST_LINE === contribLine && cliK.out.trimEnd().split('\n').pop() === contribLine);
  ok('the completion honest line on the page is the one completion/verify.mjs prints last (completion.json carries no last_line; the core holds it)',
    CORE.completion.LAST_LINE === cliC.out.trimEnd().split('\n').pop()
    && /a key, not a person; nothing is written to any chain, nothing is anchored, and this is no accreditation$/.test(CORE.completion.LAST_LINE));
}

/* ------------------------------------------------------ the site nav */
if (existsSync(join(ROOT, 'web/sitenav.py'))) {
  ok('the shared site nav (web/sitenav.py) is on the page with this page marked current',
    /<nav class="sitenav" data-sitenav/.test(page) && /href="trade_craft_verify\.html" aria-current="page"/.test(page));
}

/* ----------------------------- build state: last, so drift names itself */
{
  const r = spawnSync('python3', [join(ROOT, 'web/build_verify.py'), '--check'], { encoding: 'utf8', cwd: ROOT });
  ok('the page is what web/build_verify.py builds now (--check is current)', r.status === 0, r.stdout + r.stderr);
}

console.log(`web/test_verify: ${n} checks passed`);
