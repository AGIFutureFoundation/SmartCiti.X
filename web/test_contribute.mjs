/**
 * The contribute page, held to the contribution contract it claims to build.
 *
 * `web/build_contribute.py` writes `web/trade_craft_contribute.html`: a
 * consent panel, an export button, an optional wallet signature and a list of
 * destinations this bundle does NOT reach. Every claim on it is a claim about
 * a registry or about the pure function the page ships, and this suite
 * recomputes each from the file that owns it.
 *
 *   node web/test_contribute.mjs
 *   node web/test_contribute.mjs --page=/tmp/broken.html --root=/tmp/broken-root
 *   node web/test_contribute.mjs --sample=/path/to/contrib_sample.json
 *
 * `--page` and `--root` exist for the mutation tests. `--sample` writes the
 * unsigned package the page's own function builds, so the CLI verifier can
 * be run on it. No browser, no network.
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const arg = (name) => { const hit = args.find((a) => a.startsWith(`--${name}=`)); return hit === undefined ? null : hit.slice(name.length + 3); };
const ROOT = resolve(arg('root') !== null ? arg('root') : join(HERE, '..'));
const PAGE = resolve(arg('page') !== null ? arg('page') : join(HERE, 'trade_craft_contribute.html'));

let n = 0, bad = 0;
const ok = (m, c, evidence = []) => {
  if (c) { n++; console.log('  ok  ' + m); return; }
  bad++; console.log('FAIL  ' + m); for (const e of evidence) console.log('      ' + e);
};
const readText = (rel) => readFileSync(join(ROOT, rel), 'utf8');
const readJSON = (rel) => JSON.parse(readText(rel));
const M = (rel) => pathToFileURL(join(ROOT, rel)).href;

const CONTRIB_PATH = 'contrib/registry/contrib.json';
const TRAINING_PATH = 'training/registry/training.json';
const AUTH_PATH = 'auth/registry/auth.json';
const PROTOCOLS_PATH = 'protocols/registry/protocols.json';
const contribReg = readJSON(CONTRIB_PATH);
const trainingReg = readJSON(TRAINING_PATH);
const authReg = readJSON(AUTH_PATH);
const simsReg = readJSON('sims/registry/sims.json');
const manifest = readJSON('pack/manifest.json');
const html = readFileSync(PAGE, 'utf8');
const data = JSON.parse(html.match(/<script type="application\/json" id="tcdata">([\s\S]*?)<\/script>/)[1]);
const mod = html.slice(html.indexOf('<script type="module">'), html.lastIndexOf('</script>'));

/* ------------------------------------------------------------- [shipped] static */
ok('[shipped] the page carries the product, pack version, record tag, storage keys, consent contract and episode fields of the registries, verbatim',
  data.product === manifest.product && data.pack_version === manifest.pack_version && data.record_tag === contribReg.record_tag
  && data.keys.training === trainingReg.storage.key && data.keys.identity === authReg.storage.identity_key
  && data.consent.statement === contribReg.consent.statement && JSON.stringify(data.consent.scopes) === JSON.stringify(Object.keys(contribReg.consent.scopes).sort())
  && data.consent.license === contribReg.consent.license.spdx && data.trace_max_samples === trainingReg.trace.max_samples
  && Object.keys(trainingReg.episode_kinds).every((k) => JSON.stringify(data.fields_by_kind[k]) === JSON.stringify(trainingReg.episode_kinds[k].fields))
  && data.digest_over === contribReg.digest.over && data.signing.statement === authReg.siwe.statement && data.signing.scheme === contribReg.signature.scheme
  && data.honesty.no_agent_trained === trainingReg.export_format.no_agent_trained);
const scopeInputs = [...html.matchAll(/<input type="checkbox" data-scope="([^"]+)">/g)].map((m) => m[1]);
ok('[shipped] the consent panel has one unchecked checkbox per declared scope, the fixed statement verbatim, the licence, and the revocable line',
  JSON.stringify(scopeInputs) === JSON.stringify(Object.keys(contribReg.consent.scopes).sort()) && !/data-scope="[^"]+" checked/.test(html)
  && html.includes('<p class="statement" id="consent-statement">' + contribReg.consent.statement.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;') + '</p>')
  && html.includes(`data-license="${contribReg.consent.license.spdx}"`)
  && /id="consent-revocable" data-revocable="true">Revocable: you keep the file; nothing is uploaded by this page\./.test(html));
ok('[shipped] the export button starts disabled, the sign button disabled and hidden, and every status line unpainted',
  /<button id="expPackage" type="button" disabled>/.test(html) && /<button id="signPackage" type="button" disabled hidden>/.test(html)
  && /id="expStatus" data-export-state="unpainted"/.test(html) && /id="signStatus" data-sign-state="unpainted"/.test(html)
  && /id="device" data-training-state="unpainted" data-identity-state="unpainted"/.test(html));
ok('[shipped] the page uploads nothing: no fetch, no XMLHttpRequest, no form action, no WebSocket, no sendBeacon in any script',
  !/\bfetch\s*\(/.test(mod) && !/XMLHttpRequest/.test(html) && !/<form/.test(html) && !/WebSocket/.test(html) && !/sendBeacon/.test(html)
  && (mod.match(/URL\.createObjectURL/g) || []).length === 1);
const hon = html.slice(html.indexOf('id="signHonesty"'), html.indexOf('</p>', html.indexOf('id="signHonesty"')));
ok('[shipped] the page says next to the button: a key, not a person; nothing on any chain; no agent or robot learned; no wallet, no signature; never fabricates',
  /identity of a key, not of a person/.test(hon) && /nothing is written to any chain/.test(hon) && /no agent\s+or robot has learned/.test(hon)
  && /no wallet, no signature/.test(hon) && /never fabricates a signature/.test(hon));
const lead = html.slice(html.indexOf('id="limits"'), html.indexOf('</section>', html.indexOf('id="limits"')));
ok('[shipped] the lead says nothing is sent, no agent is trained (training.json\'s own sentence), a key is not a person, and the learner keeps the file',
  /NOTHING SENT/.test(lead) && lead.includes(contribReg.honesty.nothing_sent.replace(/'/g, '&#x27;')) && /NO AGENT TRAINED/.test(lead)
  && /A KEY, NOT A PERSON/.test(lead) && /YOU KEEP THE FILE/.test(lead) && /It uploads nothing/.test(lead));
const iSign = mod.indexOf('personal_sign'), iAttach = mod.indexOf('attachSignature(');
ok('[shipped] the module reads window.ethereum, offers signing only for a siwe-ethereum identity with an address, asks eth_requestAccounts then personal_sign, and attachSignature is called once, after personal_sign',
  /typeof window\.ethereum === 'undefined'/.test(mod) && /idv\.method === D\.signing\.wallet_method/.test(mod) && /typeof idv\.address === 'string'/.test(mod)
  && /method: 'eth_requestAccounts'/.test(mod) && iSign > 0 && iAttach > iSign && (mod.match(/attachSignature\(/g) || []).length === 1);
ok('[shipped] the module reads the training log and the identity through one guarded reader that tells absent, blocked and unreadable apart',
  /function readJson\(key\)/.test(mod) && /state: 'blocked'/.test(mod) && /state: 'absent'/.test(mod) && /state: 'unreadable'/.test(mod)
  && /readJson\(KEYS\.training\)/.test(mod) && /readJson\(KEYS\.identity\)/.test(mod));
ok('[shipped] the export is refused with no scope ticked (no scope, no consent, no package) and the summary is computed by summarizePackage, never typed',
  /ticked\(\)\.length > 0/.test(mod) && /No scope, no consent, no package/.test(mod) && /summarizePackage\(pkg\)/.test(mod) && /data-contrib-fig/.test(mod));
ok('[shipped] the episode-kind table lists every kind with training.json\'s field list',
  Object.keys(trainingReg.episode_kinds).every((k) => html.includes(`<td class="k">${k}</td><td>${trainingReg.episode_kinds[k].fields.join(', ')}</td>`)));
ok('[shipped] no `??` in the page\'s scripts and no default is decided for a missing field', !/\?\?/.test(html.slice(html.indexOf('<script id="contrib-js">'))));

/* ------------------------------------------------------------ destinations */
{
  const present = existsSync(join(ROOT, PROTOCOLS_PATH));
  let want = [];
  if (present) {
    const reg = readJSON(PROTOCOLS_PATH);
    const listing = 'destinations' in reg ? reg.destinations : ('protocols' in reg ? reg.protocols : null);
    if (listing !== null) {
      const entries = Array.isArray(listing) ? listing.map((e) => [null, e]) : Object.entries(listing);
      want = entries.filter(([, e]) => e && typeof e === 'object').map(([k, e]) => (typeof e.id === 'string' ? e.id : k)).filter((x) => typeof x === 'string');
    }
  }
  const rows = [...html.matchAll(/<tr data-destination="([^"]+)">([\s\S]*?)<\/tr>/g)];
  const where = html.slice(html.indexOf('id="where"'), html.indexOf('</section>', html.indexOf('id="where"')));
  ok(`[shipped] "Where this could go" lists exactly the ${want.length} destination(s) ${PROTOCOLS_PATH} names (${present ? 'present' : 'absent'}) and no other; the page types no platform name`,
    JSON.stringify(rows.map((r) => r[1])) === JSON.stringify(want) && html.includes(`data-destinations="${want.length}"`)
    && JSON.stringify(data.destinations.map((d) => d.id)) === JSON.stringify(want) && data.protocols_state === (present ? 'present' : 'absent'),
    [rows.map((r) => r[1]).join(), want.join()]);
  ok('[shipped] every destination row says: not integrated, not validated, nothing sent by this bundle - and with none, the page says no destination is configured',
    (want.length === 0
      ? /No destination is configured\./.test(where) && /no\s+destination is configured/.test(where)
      : rows.every((r) => /not integrated · not validated · nothing sent by this bundle/.test(r[2]) && /data-reach="none"/.test(r[2])))
    && /naming a place is not reaching it|this page writes a file and stops/.test(where));
  if (present) {
    const reg = readJSON(PROTOCOLS_PATH);
    const listing = 'destinations' in reg ? reg.destinations : reg.protocols;
    const entries = Array.isArray(listing) ? listing : Object.values(listing);
    ok(`[registry] ${PROTOCOLS_PATH} itself marks no destination integrated, validated or configured - otherwise the page's three words would be a lie and the build refuses`,
      entries.every((e) => e.integrated !== true && e.validated_against_spec !== true && e.configured !== true));
  }
}

/* ------------------------------------------- the package, in node, and verified */
const m = html.match(/<script id="contrib-js">([\s\S]*?)<\/script>/);
ok('[shipped] the page carries a <script id="contrib-js"> classic script naming buildContribution(training, identity, consent, meta, now), canonicalJSON, digestBody, signatureMessage, attachSignature, summarizePackage',
  m !== null && /async function buildContribution\(training, identity, consent, meta, now\)/.test(m[1]) && /function canonicalJSON\(/.test(m[1])
  && /function digestBody\(/.test(m[1]) && /function signatureMessage\(/.test(m[1]) && /function attachSignature\(/.test(m[1]) && /function summarizePackage\(/.test(m[1]));
const C = m === null ? null : new Function(m[1] + '\nreturn { buildContribution, canonicalJSON, digestBody, signatureMessage, attachSignature, summarizePackage, countEpisodes };')();
if (C !== null) {
  if (!globalThis.crypto || !globalThis.crypto.subtle) globalThis.crypto = (await import('node:crypto')).webcrypto;
  const V = await import(M('contrib/verify.mjs'));
  const T = await import(M('completion/test.mjs'));
  const failsBy = (r) => { try { return Object.entries(V.verify(r).tally).filter(([, t]) => t.fails.length).map(([k]) => k); } catch (e) { return ['record.fields:' + e.message]; } };
  const meta = { product: data.product, pack_version: data.pack_version, record_tag: data.record_tag, consent: data.consent,
    fields_by_kind: data.fields_by_kind, honesty: data.honesty, digest_over: data.digest_over };
  const NOW = new Date('2026-09-26T12:00:00.000Z');
  const consent = { scope: ['agent-training', 'robot-training'], granted_at: '2026-09-26T11:59:00.000Z' };
  /* a synthetic log shaped as the 3D page writes it and training.json declares it:
     the field ORDER is the registry's, the ids are sims.json's */
  const F = trainingReg.episode_kinds;
  const simId = Object.keys(simsReg.sims).sort()[2];
  const sim = simsReg.sims[simId];
  const hall = sim.halls[0];
  const scenario = sim.scenarios[0];
  const controls = sim.controls.map((c) => c.action);
  const shape = (kind, vals) => { const e = {}; for (const f of F[kind].fields) if (f in vals) e[f] = vals[f]; return e; };
  const training = [
    shape('walkaround', { t: '2026-09-26T10:00:00.000Z', kind: 'walkaround', campus: scenario.campus, hall, sim: simId, point: sim.walkaround[0].point }),
    shape('sim', { t: '2026-09-26T10:01:00.000Z', kind: 'sim', campus: scenario.campus, hall, sim: simId, scenario: scenario.id, controls, actor: 'human',
      outcome: { passed: true, rows: sim.rubric.map((a) => ({ axis: a.axis, value: 1, ok: true })), trace: [0, 1, 2].map((i) => ({ t: i * 1000, gauges: { load_pct: 10 + i, mode: 'test' } })) } }),
    shape('sim', { t: '2026-09-26T10:02:00.000Z', kind: 'sim', campus: scenario.campus, hall, sim: simId, scenario: null, controls, actor: 'human', outcome: { passed: false, rows: [] } }),
    shape('advisor', { t: '2026-09-26T10:03:00.000Z', kind: 'advisor', campus: scenario.campus, hall, advisor: 'test-advisor', topic: 'test-topic', answer_kind: 'record' }),
    shape('crew', { t: '2026-09-26T10:04:00.000Z', kind: 'crew', campus: scenario.campus, hall, crew: 'test-crew', role: 'test-role', topic: 'test-topic', answer_kind: 'registry' }),
  ];
  const identity = { v: 1, method: 'local-label', label: 'test label', set_at: '2026-09-26T09:00:00.000Z', authenticates: false };
  const pkg = await C.buildContribution(training, identity, consent, meta, NOW);
  const run = V.verify(pkg);
  ok('[shipped] the unsigned package the page builds verifies against contrib/verify.mjs on every rule, is "this device only", carries the episodes verbatim, and its digest recomputes with the verifier\'s own digestOf',
    failsBy(pkg).length === 0 && run.signature.state === 'unsigned' && pkg.contributor.attested_by === 'this device only' && pkg.contributor.signature === null
    && pkg.contributor.claimed === 'test label' && JSON.stringify(pkg.dataset.episodes) === JSON.stringify(training) && V.digestOf(pkg) === pkg.digest.hex
    && pkg.record === 'tc-contribution/1' && pkg.consent.license === contribReg.consent.license.spdx && pkg.consent.statement === contribReg.consent.statement,
    [failsBy(pkg).join()]);
  ok('[shipped] the counts the package states recompute: 5 episodes (advisor 1, crew 1, sim 2, walkaround 1), 1 trace with 3 samples, 1 sim covered - and summarizePackage says the same',
    JSON.stringify(pkg.dataset.episode_counts_by_kind) === JSON.stringify({ advisor: 1, crew: 1, sim: 2, walkaround: 1 }) && pkg.dataset.traces_attached === 1
    && JSON.stringify(pkg.dataset.sims_covered) === JSON.stringify([simId]) && run.summary.samples === 3
    && C.summarizePackage(pkg).samples === 3 && C.summarizePackage(pkg).episodes === 5 && C.summarizePackage(pkg).digest === pkg.digest.hex);
  ok('[shipped] the package is deterministic: same inputs, same bytes',
    C.canonicalJSON(await C.buildContribution(training, identity, consent, meta, NOW)) === C.canonicalJSON(pkg));
  const partial = await C.buildContribution(training, identity, { ...consent, scope: ['robot-training'] }, meta, NOW);
  ok('[shipped] the scope in the package is what was ticked, ordered as the registry declares, and a partial scope verifies too',
    failsBy(partial).length === 0 && JSON.stringify(partial.consent.scope) === JSON.stringify(['robot-training']), [failsBy(partial).join()]);
  const refuses = async (f) => { try { await f(); return null; } catch (e) { return e.message; } };
  ok('[shipped] the function refuses: an empty scope, a scope the registry does not declare, an unparseable granted_at, a log that is not an array, and a meta.wallet that is not an address',
    /no scope ticked/.test(await refuses(() => C.buildContribution(training, identity, { ...consent, scope: [] }, meta, NOW)))
    && /not one this registry declares/.test(await refuses(() => C.buildContribution(training, identity, { ...consent, scope: ['marketing'] }, meta, NOW)))
    && /granted_at/.test(await refuses(() => C.buildContribution(training, identity, { ...consent, granted_at: 'yesterday' }, meta, NOW)))
    && /array of episode objects/.test(await refuses(() => C.buildContribution({ a: 1 }, identity, consent, meta, NOW)))
    && /meta\.wallet must be an address/.test(await refuses(() => C.buildContribution(training, identity, consent, { ...meta, wallet: 'nope' }, NOW))));
  const empty = await C.buildContribution([], null, consent, meta, NOW);
  ok('[shipped] an empty log with no identity builds a package of zero episodes, claimed null, that still verifies (a package proves what a device recorded, even nothing)',
    failsBy(empty).length === 0 && empty.dataset.episodes.length === 0 && empty.contributor.claimed === null && empty.dataset.traces_attached === 0);
  const sample = arg('sample');
  if (sample !== null) { mkdirSync(dirname(sample), { recursive: true }); writeFileSync(sample, JSON.stringify(pkg, null, 1) + '\n'); }
  if (sample !== null) {
    const r = spawnSync(process.execPath, [join(ROOT, 'contrib/verify.mjs'), sample], { encoding: 'utf8' });
    ok('[shipped] the CLI verifier passes the page\'s own package (written to --sample) and prints the honest last line',
      r.status === 0 && r.stdout.trim().split('\n').pop() === V.LAST_LINE, [r.stderr.split('\n').slice(0, 3).join(' | ')]);
  }

  /* ---- signed path: the signer is completion/test.mjs's throwaway key, never the page's */
  const key = T.throwawayKey(), other = T.throwawayKey();
  const forWallet = await C.buildContribution(training, identity, consent, { ...meta, wallet: key.address }, NOW);
  ok('[shipped] built with meta.wallet the package claims the address, is attested "wallet signature over the digest", carries signature null, and is REFUSED by the verifier until signed',
    forWallet.contributor.claimed === key.address && forWallet.contributor.attested_by === 'wallet signature over the digest' && forWallet.contributor.signature === null
    && failsBy(forWallet).join() === 'contributor.signature' && /identity of a key, not of a person/.test(forWallet.honesty.contributor));
  const message = C.signatureMessage(forWallet, data.signing.statement);
  ok('[shipped] the page\'s signatureMessage is the verifier\'s structured message: auth/\'s statement, digest, exported_at, consent scope',
    message === V.signatureMessage(forWallet.digest.hex, forWallet.exported_at, forWallet.consent.scope) && /\nconsent: agent-training,robot-training$/.test(message));
  const signed = C.attachSignature(forWallet, key.address, T.signPersonal(key.d, message), data.signing);
  const srun = V.verify(signed);
  ok('[shipped] signed in the test with a throwaway key, the package verifies on every rule, the verifier recovers exactly that address, and the digest is unchanged',
    failsBy(signed).length === 0 && srun.signature.state === 'signed' && srun.signature.recovered === key.address && signed.digest.hex === forWallet.digest.hex
    && C.canonicalJSON(C.digestBody(signed)) === V.canonical(V.digestBody(signed)), [failsBy(signed).join(), srun.signature.line]);
  const bitFlip = JSON.parse(JSON.stringify(signed));
  { const u = Buffer.from(bitFlip.contributor.signature.sig.slice(2), 'hex'); u[40] ^= 1; bitFlip.contributor.signature.sig = '0x' + u.toString('hex'); }
  const otherKey = JSON.parse(JSON.stringify(signed)); otherKey.contributor.signature.sig = T.signPersonal(other.d, message);
  const badMsg = C.attachSignature(forWallet, key.address, T.signPersonal(key.d, message + ' '), data.signing);
  const widened = JSON.parse(JSON.stringify(signed)); widened.consent.scope = ['agent-training']; widened.digest.hex = V.digestOf(widened);
  ok('[shipped] and it is rejected by name when tampered: one bit flipped, another key, another message, or the scope changed after signing - each fails contributor.signature alone',
    [bitFlip, otherKey, badMsg, widened].every((r) => failsBy(r).join() === 'contributor.signature'), [bitFlip, otherKey, badMsg, widened].map((r) => failsBy(r).join()));
  const edited = JSON.parse(JSON.stringify(signed)); edited.dataset.episodes[0].point = 'somewhere else';
  ok('[shipped] an episode edited under a valid signature fails digest', failsBy(edited).join() === 'digest', [failsBy(edited).join()]);
  const r = async (f) => { try { f(); return null; } catch (e) { return e.message; } };
  ok('[shipped] attachSignature fabricates nothing: it refuses a malformed signature, a package built without the wallet, one built for another address, and one already signed',
    /65-byte/.test(await r(() => C.attachSignature(forWallet, key.address, '0xdead', data.signing)))
    && /not built for the wallet/.test(await r(() => C.attachSignature(pkg, key.address, signed.contributor.signature.sig, data.signing)))
    && /not built for the wallet/.test(await r(() => C.attachSignature(forWallet, other.address, signed.contributor.signature.sig, data.signing)))
    && /already carries a signature/.test(await r(() => C.attachSignature(signed, key.address, signed.contributor.signature.sig, data.signing))));
}


/* ---------------------------------------------------------- copy joins -- */
// Registry sentences are set into the builder's own copy. A join must never
// start a sentence lowercase ("...the file. no lesson here...") nor run two
// sentences together with no terminal punctuation ("...counted instead The
// last column..."). Read every rendered paragraph of the sections that join.
{
  const JOIN_SECTIONS = ['consent'];
  const START = /[a-z0-9)\]]\s+(The|This|That|These|It|Its|A|An|Every|Each|Nothing|No|Read|Tick|What|When|Where|Seat|Sim)\s/;
  const joinBad = [];
  for (const id of JOIN_SECTIONS) {
    const at = html.indexOf(`<section id="${id}"`);
    if (at < 0) { joinBad.push(`#${id}: no such section`); continue; }
    const sec = html.slice(at, html.indexOf('</section>', at));
    for (const pm of sec.matchAll(/<p\b[^>]*>([\s\S]*?)<\/p>/g)) {
      const text = pm[1].replace(/<[^>]+>/g, '').replace(/&[a-z]+;|&#\d+;/g, (e) => ({ '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&mdash;': '—' }[e] || ' ')).replace(/\s+/g, ' ').trim();
      const low = text.match(/[.!?]\s+[a-z][a-z]/);
      const run = text.match(START);
      if (low) joinBad.push(`#${id}: lowercase sentence start: ...${text.slice(Math.max(0, low.index - 40), low.index + 40)}...`);
      if (run) joinBad.push(`#${id}: sentences joined with no terminal punctuation: ...${text.slice(Math.max(0, run.index - 40), run.index + 40)}...`);
    }
  }
  ok(`[shipped] every paragraph in ${JOIN_SECTIONS.map((s) => '#' + s).join(', ')} starts each sentence uppercase and closes each before the next`, joinBad.length === 0, joinBad);
}

/* ---------------------------------------------- Share data (wave 11, DATASHARE) */
{
  const between = (src, b, e, incl = true) => { const i = src.indexOf(b), j = i < 0 ? -1 : src.indexOf(e, i); return i < 0 || j <= i ? null : src.slice(i, j + (incl ? e.length : 0)); };
  const cores = between(html, '<script id="ds-cores">', '</script>', false);
  const vsrc = readText('contrib/verify.mjs'), dsrc = readText('datashare/core.mjs'), signin = readText('web/trade_craft_signin.html');
  const CB = between(vsrc, '/* CONTRIB_CORE:BEGIN', '/* CONTRIB_CORE:END */'), DB = between(dsrc, '/* DATASHARE_CORE:BEGIN', '/* DATASHARE_CORE:END */');
  const AB = between(signin, '/* AUTH-CORE:BEGIN', '/* AUTH-CORE:END */', false);
  ok('[share] the page carries contrib/verify.mjs\'s CONTRIB_CORE, the sign-in AUTH-CORE and datashare/core.mjs\'s DATASHARE_CORE byte-for-byte (one set of rules, no second copy)',
    cores !== null && CB !== null && DB !== null && AB !== null && cores.includes(CB) && cores.includes(DB) && cores.includes(AB));
  const ds = JSON.parse(between(html, '<script type="application/json" id="ds-data">', '</script>', false).slice('<script type="application/json" id="ds-data">'.length).replace(/<\\\//g, '</'));
  const { REGISTRY_FILES } = await import(M('contrib/verify.mjs'));
  ok('[share] the page\'s registries are the files the verifier names, verbatim, and its datashare config is datashare.json',
    Object.entries(REGISTRY_FILES).every(([k, rel]) => JSON.stringify(ds.regs[k]) === JSON.stringify(readJSON(rel)))
    && JSON.stringify(ds.cfg) === JSON.stringify(readJSON('datashare/registry/datashare.json')) && ds.tag_v2 === 'tc-contribution/2');
  const LOCS = ['en', 'es', 'fr', 'de', 'pt', 'zh', 'hi', 'ar'];
  ok('[share] the section\'s words come from the 8 locales (datashare.* keys), verbatim, with each locale\'s direction',
    LOCS.every((l) => { const d = readJSON(`i18n/locales/${l}.json`); return ds.i18n[l].dir === d.dir
      && ['title', 'lede', 'classroom', 'load', 'import', 'export', 'analyse', 'dataset'].every((k) => ds.i18n[l].strings[k] === d.strings['datashare.' + k]); }));
  const share = html.slice(html.indexOf('<section id="share"'), html.indexOf('</section>', html.indexOf('<section id="share"')));
  const shareMod = html.slice(html.indexOf("const S = JSON.parse(document.getElementById('ds-data')"));
  ok('[share] K-12 / classroom mode offers nothing: a class plan on the device, ?plan or ?classroom, or unreadable storage hides the tools and shows the locale\'s classroom sentence',
    /S\.classroom\.plan_key/.test(shareMod) && JSON.stringify(ds.classroom) === JSON.stringify({ plan_key: 'tc-class-plan', params: ['plan', 'classroom'] })
    && /document\.getElementById\('shareTools'\)\.hidden = true/.test(shareMod) && /return 'storage-blocked'/.test(shareMod) && /T\('classroom'\)/.test(shareMod)
    && /not offered/.test(ds.i18n.en.strings.classroom));
  ok('[share] the store is IndexedDB opened inside try/catch with a named in-memory fallback, and the page says which one it got',
    /try \{\s*const r = indexedDB\.open/.test(shareMod) && /catch \(e\) \{ res\(null\); \}/.test(shareMod) && /IndexedDB is unavailable here/.test(shareMod) && /data-store="unpainted"/.test(share));
  ok('[share] per-package opt-in: one unticked scope box per declared scope, the fixed statement verbatim, and the boxes are cleared after every export',
    (share.match(/data-share-scope="/g) || []).length === Object.keys(contribReg.consent.scopes).length && !/data-share-scope="[^"]+" checked/.test(share)
    && share.includes('>' + contribReg.consent.statement.replace(/'/g, '&#x27;') + '<') && /for \(const b of scopeBoxes\) b\.checked = false/.test(shareMod)
    && /id="shareExport" type="button" disabled/.test(share));
  ok('[share] the Share data scripts send nothing (no fetch, XMLHttpRequest, WebSocket or sendBeacon) and download by data: URL',
    !/\bfetch\s*\(|XMLHttpRequest|WebSocket|sendBeacon/.test(shareMod.slice(0, shareMod.indexOf('</script>'))) && /'data:' \+ type/.test(shareMod));
  ok('[share] every enforced practice the datashare registry lists is shown with the file that enforces it, and the page says nothing was trained',
    readJSON('datashare/registry/datashare.json').best_practices.every((b) => share.includes(b.practice.replace(/'/g, '&#x27;')) && share.includes(b.enforced_by.file))
    && /NOTHING HAS BEEN TRAINED/.test(share));
  // the page's own buildPackageV2, lifted and run in node over the v2 fixture's episodes
  const V = await import(M('contrib/verify.mjs'));
  const ctx = {};
  const classic = between(html, '<script id="contrib-js">', '</script>', false).slice('<script id="contrib-js">'.length) + '\n' + cores.slice('<script id="ds-cores">'.length);
  new Function('ctx', classic + '\nctx.buildPackageV2 = buildPackageV2; ctx.contribCore = contribCore; ctx.datashareCore = datashareCore;')(ctx);
  const regs = Object.fromEntries(Object.entries(REGISTRY_FILES).map(([k, rel]) => [k, readJSON(rel)]));
  const CC = ctx.contribCore(regs);
  const g2 = readJSON('contrib/fixture/v2/good.json');
  const meta = { tag_v2: ds.tag_v2, product: contribReg.product, pack_version: contribReg.pack_version, fields_v2: ds.fields_v2,
    consent: { statement: contribReg.consent.statement, scopes: Object.keys(contribReg.consent.scopes).sort(), license: contribReg.consent.license.spdx },
    honesty: contribReg.honesty, digest_over: contribReg.digest.over };
  const now = new Date('2026-09-29T02:00:00.000Z');
  const pkg = await ctx.buildPackageV2(g2.dataset.episodes, ['robot-training'], meta, now, CC);
  const vr = V.verify(pkg);
  const fails = Object.entries(vr.tally).filter(([, t]) => t.fails.length).map(([k, t]) => k + ': ' + t.fails[0]);
  ok('[share] the page\'s tc-contribution/2 package verifies with node contrib/verify.mjs on every rule: episodes verbatim, claimed null, origin.classroom_mode false, the ticked scope only',
    fails.length === 0 && pkg.record === 'tc-contribution/2' && pkg.contributor.claimed === null && pkg.origin.classroom_mode === false
    && JSON.stringify(pkg.consent.scope) === '["robot-training"]' && JSON.stringify(pkg.dataset.episodes) === JSON.stringify(g2.dataset.episodes), fails);
  const refusedBy = async (eps, scope) => { try { await ctx.buildPackageV2(eps, scope, meta, now, CC); return ''; } catch (e) { return e.message; } };
  ok('[share] buildPackageV2 refuses: no scope ticked, an undeclared scope, no episodes, an episode of a kind no package carries',
    /no scope ticked/.test(await refusedBy(g2.dataset.episodes, [])) && /not declared/.test(await refusedBy(g2.dataset.episodes, ['marketing']))
    && /no episodes/.test(await refusedBy([], ['robot-training'])) && /cannot be shared/.test(await refusedBy([{ kind: 'joystick' }], ['robot-training'])));
  const DC = ctx.datashareCore(ds.cfg, async (s) => (await import('node:crypto')).createHash('sha256').update(s).digest('hex'));
  const A = DC.analyse(g2.dataset.episodes.map((episode) => ({ episode })));
  ok('[share] the page\'s analysis core runs over the same episodes and reports counts, rates and coverage gaps',
    A.episodes === g2.dataset.episodes.length && A.by_kind['world-teleop'] === 2 && A.gaps.length > 0);
  ok('[share] the /1 exporter no longer builds a package it cannot verify: a log holding world episodes is sent to Share data (needs-v2)',
    /'needs-v2'/.test(mod) && /e\.kind in D\.fields_by_kind\)/.test(mod));
}

console.log(`\ncontribute: ${n} checks, ${bad} failure${bad === 1 ? '' : 's'}`);
process.exit(bad ? 1 : 0);
