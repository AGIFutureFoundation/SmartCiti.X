#!/usr/bin/env python3
"""The verify page: check an exported record in the browser, with the CLI's own code.

WHY THIS FILE EXISTS. A union rep handed a learner's completion record
(`tc-completion/1`, from the progress page) or contribution package
(`tc-contribution/1`, from the contribute page) could only check it by running
`node completion/verify.mjs` or `node contrib/verify.mjs` from a checkout.
This page runs THE SAME RULES in the browser and uploads nothing.

ONE TRUTH, CARRIED - never copied by hand. Three blocks are lifted at build
time and carried into the page byte-for-byte:

  - completion/verify.mjs between `/* COMPLETION_CORE:BEGIN` and
    `/* COMPLETION_CORE:END */` - completionCore(), every completion rule;
  - contrib/verify.mjs between `/* CONTRIB_CORE:BEGIN` and
    `/* CONTRIB_CORE:END */` - contribCore(), every contribution rule;
  - web/trade_craft_signin.html's AUTH-CORE region (from `/* AUTH-CORE:BEGIN`
    up to, not including, `/* AUTH-CORE:END */`) - the same slice
    auth/recover.mjs lifts for node: the page's keccak, secp256k1 and EIP-191
    recovery. The page wraps it in a function and keeps only recoverAddress.

The registries each core reads are embedded verbatim, one
`<script type="application/json" data-registry="<path>">` per file, keyed
by the REGISTRY_FILES map each verify.mjs declares (parsed here, not
retyped). A carried block that holds a network or storage primitive, a
module statement, or a `??` is refused and the build fails by name.

SHA-256. The cores' verify() takes a synchronous sha256; the browser's is
crypto.subtle, which is async. Each core therefore carries verifyAsync(record,
subtle, recover), which computes the one digest the rules ask for with
subtle.digest and then runs the same synchronous verify(). The page calls
verifyAsync with crypto.subtle; web/test_verify.mjs calls it with node's
webcrypto.subtle over every fixture and mutant and holds the result to the
CLI's output line for line.

WHAT THE PAGE WILL NOT DO. It will not send the file anywhere: no fetch, no
XHR, no beacon, no socket, no form. The file is read by FileReader in this
tab and nowhere else. It will not guess a record's kind: the `record` field
names it, and an unknown or unparseable file runs nothing.

No `.get(k, default)` and no `??` in this file or in the page's own script.
`python3 web/build_verify.py --check` fails if the committed page is stale.
"""
import html
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from staleness import emit  # noqa: E402
from seo import apply_seo  # noqa: E402  head tags only


def _root():
    for cand in (HERE, *HERE.parents):
        if (cand / 'completion').is_dir() and (cand / 'contrib').is_dir() and (cand / 'auth').is_dir():
            return cand
    raise RuntimeError('cannot locate the packs from ' + str(HERE))


ROOT = _root()
PAGE_PATH = 'web/trade_craft_verify.html'
SIGNIN_PAGE = 'web/trade_craft_signin.html'
MANIFEST_PATH = 'pack/manifest.json'
AUTH_BEGIN, AUTH_END = '/* AUTH-CORE:BEGIN', '/* AUTH-CORE:END */'

# (verify.mjs, BEGIN marker, END marker, the function the block declares)
CORES = [
    ('completion/verify.mjs', '/* COMPLETION_CORE:BEGIN', '/* COMPLETION_CORE:END */', 'completionCore'),
    ('contrib/verify.mjs', '/* CONTRIB_CORE:BEGIN', '/* CONTRIB_CORE:END */', 'contribCore'),
]
# what a carried block may not hold: every way a page reaches the network or
# the device's storage, module syntax, and the nullish default
BANNED = [
    (re.compile(r'\bfetch\b'), 'fetch'),
    (re.compile(r'XMLHttpRequest'), 'XMLHttpRequest'),
    (re.compile(r'sendBeacon'), 'sendBeacon'),
    (re.compile(r'WebSocket'), 'WebSocket'),
    (re.compile(r'EventSource'), 'EventSource'),
    (re.compile(r'RTCPeerConnection'), 'RTCPeerConnection'),
    (re.compile(r'importScripts'), 'importScripts'),
    (re.compile(r'localStorage'), 'localStorage'),
    (re.compile(r'sessionStorage'), 'sessionStorage'),
    (re.compile(r'indexedDB'), 'indexedDB'),
    (re.compile(r'\bimport\s*\('), 'import('),
    (re.compile(r'^\s*import\b', re.M), 'import statement'),
    (re.compile(r'^\s*export\b', re.M), 'export statement'),
    (re.compile(r'\?\?'), '??'),
]


def need(d, k, where):
    """Read a required field, or fail by name."""
    if not isinstance(d, dict):
        raise TypeError(f'{where}: expected an object to read {k!r} from, got {type(d).__name__}')
    if k not in d:
        raise KeyError(f'{where}: required field {k!r} is missing')
    return d[k]


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def refuse_banned(src, where):
    for rx, name in BANNED:
        if rx.search(src):
            raise AssertionError(f'{where}: the carried block contains {name!r}; it must stay pure')


def lift(rel, begin, end, include_end):
    src = read(rel)
    a, b = src.find(begin), src.find(end)
    if a < 0 or b <= a:
        raise AssertionError(f'{rel}: carries no {begin} ... {end} region to lift')
    if src.find(begin, a + 1) >= 0 or src.find(end, b + 1) >= 0:
        raise AssertionError(f'{rel}: carries its markers more than once')
    return src[a:b + len(end)] if include_end else src[a:b]


def registry_files(rel):
    """The REGISTRY_FILES map a verify.mjs declares: {name: path}."""
    src = read(rel)
    m = re.search(r'export const REGISTRY_FILES = \{\n(.*?)\n\};', src, re.S)
    if not m:
        raise AssertionError(f'{rel}: declares no REGISTRY_FILES map')
    pairs = re.findall(r"^\s*(\w+): '([^']+)',$", m.group(1), re.M)
    if len(pairs) != len(m.group(1).split('\n')) or not pairs:
        raise AssertionError(f'{rel}: REGISTRY_FILES has a line this builder cannot read')
    return dict(pairs)


manifest = json.loads(read(MANIFEST_PATH))
PRODUCT = need(manifest, 'product', MANIFEST_PATH)
PACK_VERSION = need(manifest, 'pack_version', MANIFEST_PATH)
TITLE = PRODUCT.split('(')[0].strip()

# the cores, lifted and checked
CORE_JS = []
KINDS = []           # [{tag, core, files, verifier}] in the order of CORES
ALL_FILES = []       # every registry path, once, in first-use order
for rel, begin, end, fn in CORES:
    block = lift(rel, begin, end, True)
    refuse_banned(block, rel)
    if f'function {fn}(regs) {{' not in block:
        raise AssertionError(f'{rel}: the marked block does not declare {fn}(regs)')
    if '</script' in block.lower():
        raise AssertionError(f'{rel}: the marked block holds a </script and cannot be carried inline')
    files = registry_files(rel)
    own = files[next(iter(files))]
    tag = need(json.loads(read(own)), 'record_tag', own)
    CORE_JS.append(block)
    KINDS.append({'tag': tag, 'core': fn, 'verifier': rel, 'files': files})
    for p in files.values():
        if p not in ALL_FILES:
            ALL_FILES.append(p)
if len({k['tag'] for k in KINDS}) != len(KINDS):
    raise AssertionError('two cores claim the same record tag')

# the recovery, lifted the way auth/recover.mjs lifts it
AUTH_JS = lift(SIGNIN_PAGE, AUTH_BEGIN, AUTH_END, False)
refuse_banned(AUTH_JS, SIGNIN_PAGE + ' AUTH-CORE')
if 'function recoverAddress(' not in AUTH_JS:
    raise AssertionError(f'{SIGNIN_PAGE}: the AUTH-CORE region declares no recoverAddress')
if '</script' in AUTH_JS.lower():
    raise AssertionError(f'{SIGNIN_PAGE}: the AUTH-CORE region holds a </script')

# the registries, verbatim
REG_TAGS = []
for p in ALL_FILES:
    txt = read(p)
    json.loads(txt)
    low = txt.lower()
    if '</script' in low or '<!--' in low:
        raise AssertionError(f'{p}: holds </script or <!-- and cannot be embedded verbatim')
    REG_TAGS.append(f'<script type="application/json" data-registry="{html.escape(p)}">{txt}</script>')

E = lambda s: html.escape(s, quote=False)
KINDS_JSON = json.dumps(KINDS, ensure_ascii=False, separators=(',', ':'))
TAG_LIST = ', '.join(f'<code>{E(k["tag"])}</code>' for k in KINDS)
CLI_LIST = ' and '.join(f'<code>node {E(k["verifier"])}</code>' for k in KINDS)
READS = ''.join(f'<li><code>{E(p)}</code></li>' for p in ALL_FILES)
CARRIES = ''.join(f'<li><code>{E(rel)}</code> between <code>{E(b)}</code> and <code>{E(e)}</code></li>'
                  for rel, b, e, _ in CORES)
CARRIES += (f'<li><code>{E(SIGNIN_PAGE)}</code> between <code>{E(AUTH_BEGIN)}</code> and '
            f'<code>{E(AUTH_END)}</code> — the same region <code>auth/recover.mjs</code> lifts</li>')

# the site nav, declared once in web/sitenav.py; a page built without it would be
# a page a learner cannot leave, so there is no fallback: a missing declaration stops the build
from sitenav import nav_html, labels as nav_labels, NAV_CSS, with_style_memory  # noqa: E402
NAV = nav_html('web/trade_craft_verify.html', nav_labels('en'))
NAV_STATE = 'with'

# The page's own script. It reads the embedded registries, builds one core
# per record kind, and on a file: parse, detect by `record`, run the core's
# verifyAsync with crypto.subtle and the lifted recoverAddress, render.
DETECT_JS = r'''/* detectRecord(text, tags) -> {ok, record, tag} or {ok: false, why}. Pure. */
function detectRecord(text, tags) {
  let record;
  try { record = JSON.parse(text); }
  catch (e) { return { ok: false, why: 'This file is not JSON (' + e.message + '). Nothing was run.' }; }
  if (record === null || typeof record !== 'object' || Array.isArray(record)) {
    return { ok: false, why: 'This file is JSON but not a record object. Nothing was run.' };
  }
  if (!Object.prototype.hasOwnProperty.call(record, 'record')) {
    return { ok: false, why: 'This file has no "record" field, so its kind is unknown. Nothing was run.' };
  }
  if (typeof record.record !== 'string' || tags.indexOf(record.record) < 0) {
    return { ok: false, why: 'This file says record ' + JSON.stringify(record.record) + ', which this page does not verify (it knows '
      + tags.join(', ') + '). Nothing was run.' };
  }
  return { ok: true, record: record, tag: record.record };
}
'''

APP_JS = r'''(function () {
  'use strict';
  const KINDS = JSON.parse(document.getElementById('verify-kinds').textContent);
  const REGS = {};
  for (const el of document.querySelectorAll('script[data-registry]')) REGS[el.getAttribute('data-registry')] = JSON.parse(el.textContent);
  const FACTORIES = { completionCore: completionCore, contribCore: contribCore };
  const CORES = {};
  const TAGS = KINDS.map((k) => k.tag);
  const bootErrors = [];
  for (const k of KINDS) {
    const regs = {};
    for (const name of Object.keys(k.files)) regs[name] = REGS[k.files[name]];
    try { CORES[k.tag] = FACTORIES[k.core](regs); }
    catch (e) { bootErrors.push(k.verifier + ': ' + e.message); }
  }

  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }
  function say(state, text) {
    const s = document.getElementById('status');
    s.setAttribute('data-state', state);
    s.textContent = text;
  }
  function clearOut() {
    for (const id of ['verdict', 'rules', 'signer', 'lines']) document.getElementById(id).replaceChildren();
    document.getElementById('result').hidden = true;
  }

  function render(name, tag, core, result, thrown) {
    const out = document.getElementById('result');
    out.hidden = false;
    out.setAttribute('data-kind', tag);
    const failed = thrown !== null || core.failed(result);
    out.setAttribute('data-verdict', failed ? 'fail' : 'ok');
    const v = document.getElementById('verdict');
    v.append(el('b', failed ? 'bad' : 'good', failed ? 'FAIL' : 'ok'),
      document.createTextNode(' ' + name + ' — ' + tag + ', ' + core.RULES.length + ' rules, the command line’s own code, run in this tab'));
    const tb = document.getElementById('rules');
    if (thrown !== null) {
      const tr = el('tr', 'fail');
      tr.setAttribute('data-rule', 'record.fields');
      const td = el('td', 'msg', core.errorLine(thrown));
      td.colSpan = 3;
      tr.append(td);
      tb.append(tr);
    } else {
      for (const rule of Object.keys(result.tally)) {
        const t = result.tally[rule];
        const tr = el('tr', t.fails.length ? 'fail' : 'pass');
        tr.setAttribute('data-rule', rule);
        tr.append(el('td', 'k', rule), el('td', t.fails.length ? 'bad' : 'good', t.fails.length ? 'FAIL' : 'ok'));
        const td = el('td', 'msg');
        td.append(el('span', 'muted', 'checked ' + t.checked + ', failing ' + t.fails.length));
        for (const f of t.fails) td.append(el('div', 'failmsg', f));
        tr.append(td);
        tb.append(tr);
      }
      const sg = document.getElementById('signer');
      sg.setAttribute('data-signature-state', result.signature.state);
      if (result.signature.state === 'signed') sg.append(el('span', 'k', 'Recovered signer: '), el('code', 'addr', result.signature.recovered));
      else sg.append(el('span', 'muted', result.signature.recovered === null ? 'No signer was recovered.' : 'Recovered ' + result.signature.recovered + ', which is not the address claimed.'));
    }
    const pre = document.getElementById('lines');
    const lines = thrown !== null ? [{ err: true, text: core.errorLine(thrown) }] : core.report(result);
    for (const l of lines) pre.append(el('div', l.err ? 'err' : 'out', l.text));
    document.getElementById('last-line').textContent = core.LAST_LINE;
    say(failed ? 'fail' : 'ok', failed ? 'This file FAILS verification. Every failing rule is named below with the verifier’s own message.'
      : 'This file passes every rule. Read the last line for what a pass does and does not mean.');
  }

  async function check(name, text) {
    clearOut();
    const d = detectRecord(text, TAGS);
    if (!d.ok) { say('unknown', name + ': ' + d.why); return; }
    const core = CORES[d.tag];
    if (core === undefined) { say('unknown', 'The ' + d.tag + ' verifier did not load on this page (' + bootErrors.join('; ') + '). Nothing was run.'); return; }
    if (!window.crypto || !window.crypto.subtle) { say('unknown', 'This browser gives this page no crypto.subtle (it needs a secure context), so the digest cannot be recomputed. Nothing was run.'); return; }
    let result = null, thrown = null;
    try { result = await core.verifyAsync(d.record, window.crypto.subtle, AUTH.recoverAddress); }
    catch (e) { thrown = e; }
    render(name, d.tag, core, result, thrown);
  }

  function take(file) {
    if (!file) return;
    const r = new FileReader();
    r.onload = () => { check(file.name, String(r.result)); };
    r.onerror = () => { clearOut(); say('unknown', file.name + ': this browser could not read the file. Nothing was run.'); };
    r.readAsText(file);
  }

  const input = document.getElementById('file');
  input.addEventListener('change', () => { take(input.files[0]); input.value = ''; });
  const zone = document.getElementById('drop');
  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('over'); });
  zone.addEventListener('dragleave', () => { zone.classList.remove('over'); });
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('over');
    if (e.dataTransfer && e.dataTransfer.files.length) take(e.dataTransfer.files[0]);
  });
  window.addEventListener('dragover', (e) => { e.preventDefault(); });
  window.addEventListener('drop', (e) => { e.preventDefault(); });

  const hon = document.getElementById('honest-lines');
  for (const k of KINDS) {
    if (CORES[k.tag] === undefined) continue;
    const li = el('li');
    li.append(el('code', '', k.tag), document.createTextNode(': '), el('span', 'honest', CORES[k.tag].LAST_LINE));
    li.setAttribute('data-kind', k.tag);
    hon.append(li);
  }
  if (bootErrors.length) say('unknown', 'A verifier did not load: ' + bootErrors.join('; '));
  else say('ready', 'Ready. Choose or drop a file; it is read in this tab and sent nowhere.');
})();
'''

for name, src in (('DETECT_JS', DETECT_JS), ('APP_JS', APP_JS)):
    refuse_banned(src, 'web/build_verify.py ' + name)

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230C1113'/%3E%3Cpath d='M7 21 L16 7 L25 21 Z' fill='none' stroke='%23E8A33D' stroke-width='2.6' stroke-linejoin='round'/%3E%3Cpath d='M11 21 h10' stroke='%2341C4D4' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E">
<title>{E(TITLE)} — verify a record</title>
<style>
:root{{
  --plate:#12181B; --panel:#182023; --sunk:#0C1113; --ink:#E8EDEC; --muted:#93A3A6;
  --rule:#28353A; --mark:#E8A33D; --mark-ink:#12181B; --steel:#41C4D4;
  --good:#5CB584; --crit:#E07C68; --warn:#E8A33D;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--plate);color:var(--ink);
  font:14px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
.wrap{{max-width:1020px;margin:0 auto;padding:0 16px}}
a{{color:var(--steel)}}
header.page{{padding:34px 0 10px;border-bottom:3px solid var(--mark)}}
header.page h1{{font:700 34px/1.1 "Barlow Condensed",system-ui,sans-serif;margin:0}}
header.page h1 .x{{color:var(--mark)}}
header.page .brand{{margin:0 0 2px;font:600 13px/1.3 "IBM Plex Sans",system-ui,sans-serif;color:var(--muted);letter-spacing:.02em}}header.page .brand .x{{color:var(--mark)}}
header.page p{{color:var(--muted);margin:6px 0 14px}}
h2{{font:700 22px/1.2 "Barlow Condensed",system-ui,sans-serif;margin:30px 0 10px;color:var(--mark);letter-spacing:.02em}}
.lead{{background:var(--panel);border:1px solid var(--rule);border-inline-start:4px solid var(--warn);
  border-radius:8px;padding:14px 18px;margin-top:18px}}
.lead ul,.card ul{{margin:8px 0 0;padding-inline-start:20px}}
.lead li,.card li{{margin:6px 0;color:var(--muted)}}
.card{{background:var(--panel);border:1px solid var(--rule);border-radius:10px;padding:14px 16px;margin:12px 0}}
#drop{{border:2px dashed var(--rule);border-radius:10px;padding:26px 16px;text-align:center;background:var(--sunk)}}
#drop.over{{border-color:var(--mark);background:var(--panel)}}
#drop p{{margin:6px 0;color:var(--muted)}}
label.pick{{display:inline-block;background:var(--mark);color:var(--mark-ink);border-radius:7px;padding:8px 14px;
  font-weight:600;cursor:pointer}}
label.pick input{{position:absolute;width:1px;height:1px;opacity:0}}
label.pick:focus-within{{outline:2px solid var(--steel);outline-offset:2px}}
#status{{margin:12px 0 0;color:var(--ink)}}
#status[data-state="fail"],#status[data-state="unknown"]{{color:var(--crit)}}
#status[data-state="ok"]{{color:var(--good)}}
table{{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--rule);border-radius:8px;overflow:hidden;margin:8px 0}}
td,th{{border-top:1px solid var(--rule);padding:8px 10px;vertical-align:top;font-size:13.5px;text-align:start}}
th{{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.05em}}
td.k{{font-weight:600;white-space:nowrap}}
.tscroll{{overflow-x:auto}}
.good{{color:var(--good);font-weight:700}}
.bad{{color:var(--crit);font-weight:700}}
.failmsg{{color:var(--ink);margin-top:4px;overflow-wrap:anywhere}}
.muted{{color:var(--muted);font-size:13px}}
code{{font:13px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted);overflow-wrap:anywhere}}
code.addr{{color:var(--ink)}}
#lines{{background:var(--sunk);border:1px solid var(--rule);border-radius:8px;padding:10px 12px;
  font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;overflow-x:auto;white-space:pre-wrap;overflow-wrap:anywhere}}
#lines .err{{color:var(--crit)}}
#lines .out{{color:var(--muted)}}
#last-line,.honest{{color:var(--ink)}}
footer.page{{margin-top:34px;border-top:1px solid var(--rule);padding:14px 0 30px;color:var(--muted);font-size:14px}}
@media (max-width:640px){{td.k{{white-space:normal}}}}
{NAV_CSS}
</style>
</head>
<body>
{NAV}<div class="wrap">

<header class="page">
  <p class="brand">{E(TITLE)}</p>
  <h1>{E(nav_labels('en')['nav.page.verify'])}</h1>
  <p>{E(PRODUCT)} · pack {E(PACK_VERSION)} · check an exported {TAG_LIST} file with the verifiers' own code, in this tab</p>
</header>

<section class="lead" id="limits">
  <p>A learner's completion record or contribution package is a file. This page checks it with exactly the rules
     {CLI_LIST} run — the same code, carried into this page when it was built — and shows every rule's result.</p>
  <ul>
    <li><b>NOTHING IS UPLOADED.</b> The file is read in this tab and sent nowhere: this page makes no network request of any kind.</li>
    <li><b>A KEY, NOT A PERSON.</b> A signed file names the wallet address recovered from its signature. That is the
        identity of a key, not of a person; a key is held, lent and stolen. Nothing is on any chain.</li>
    <li><b>A PASS IS NOT AN ACCREDITATION.</b> A pass means the file is intact since export and every id in it exists in
        this bundle. Read the last line of every result.</li>
  </ul>
</section>

<section id="pick">
  <h2>Choose a file</h2>
  <div id="drop">
    <p><label class="pick">Choose a record or package<input type="file" id="file" accept=".json,application/json"></label></p>
    <p>or drop it here</p>
  </div>
  <p id="status" data-state="booting" role="status" aria-live="polite">Loading the verifiers…</p>
</section>

<section id="result" hidden>
  <h2>Result</h2>
  <p id="verdict"></p>
  <div class="tscroll"><table><thead><tr><th>rule</th><th>result</th><th>checked · the verifier's message</th></tr></thead>
    <tbody id="rules"></tbody></table></div>
  <p id="signer" class="card"></p>
  <p class="muted">What the command line prints for this file, line for line:</p>
  <div id="lines"></div>
  <p class="card" id="last-line"></p>
</section>

<section id="honesty">
  <h2>What a pass means</h2>
  <p class="muted">Each verifier's own last line, verbatim — printed under every result:</p>
  <ul class="card" id="honest-lines"></ul>
</section>

<section id="carried">
  <h2>What this page runs</h2>
  <p class="muted">Carried byte-for-byte when the page was built, never copied by hand:</p>
  <ul class="muted">{CARRIES}</ul>
  <p class="muted">Registries embedded verbatim:</p>
  <ul class="muted">{READS}</ul>
  <p class="muted">SHA-256 is the browser's <code>crypto.subtle</code>; the rules are the verifiers'. Run the same check
     from a checkout with {CLI_LIST}.</p>
</section>

<footer class="page">
  <a href="trade_craft_progress.html">learner progression</a>
  <a href="trade_craft_contribute.html">contribute training data</a>
  <a href="trade_craft_signin.html">who this device says you are</a>
</footer>
</div>
{chr(10).join(REG_TAGS)}
<script type="application/json" id="verify-kinds">{KINDS_JSON}</script>
<script id="auth-core">
const AUTH = (function () {{
{AUTH_JS}
return {{ recoverAddress: recoverAddress }};
}})();
</script>
<script id="completion-core">
{CORE_JS[0]}
</script>
<script id="contrib-core">
{CORE_JS[1]}
</script>
<script id="verify-detect">
{DETECT_JS}</script>
<script id="verify-app">
{APP_JS}</script>
</body>
</html>
'''

page = apply_seo(page, 'web/trade_craft_verify.html', 'SmartCiti.X : Trade Craft Academy \u2014 verify a record',
    'Check a learner\'s exported training record against its own rules, and read plainly what such a record proves and what it does not.', 'page',
    canonical_link=False, jsonld=False)
# AUDIT row 12: follow the reader's saved style (sitenav.with_style_memory, UX)
page = with_style_memory(page)
emit(HERE / 'trade_craft_verify.html', page,
     f'{len(KINDS)} record kinds, {len(ALL_FILES)} registries embedded, cores carried from '
     + ', '.join(c[0] for c in CORES) + f', {NAV_STATE} the site nav, uploads nothing')
