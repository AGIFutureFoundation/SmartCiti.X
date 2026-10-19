/* protocols/test.mjs — the protocol roster, checked. Browser-free, network-free.
 *
 * The rule this suite follows is the bundle's: recompute, never re-read.
 * Every count the registry publishes is recounted from the entries it
 * publishes; the probe is re-read from the stamped file the build read;
 * the one supported wallet rail is re-derived from auth/registry/auth.json
 * rather than believed; and the builder's own source is scanned for a
 * typed count.
 *
 * The family that matters most: NOTHING HERE IS ON. Every entry must carry
 * configured false, integrated false and validated_against_spec false, and
 * every probe record must say the spec was NOT fetched with the code, the
 * curl exit and the date that back it. Flip any of those and this is what
 * fails, by name.
 */
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok  ' + m); }
                       else { fail++; console.log('FAIL  ' + m); } };
const read = (p) => readFileSync(join(ROOT, p), 'utf8');
const J = (p) => JSON.parse(read(p));

const R = J('protocols/registry/protocols.json');
const P = R.protocols;
const IDS = Object.keys(P).sort();
const PROBE = J('protocols/authored/probe.json');
const SRC = readFileSync(join(HERE, 'build.py'), 'utf8');

console.log('protocols/test.mjs');

/* ---- provenance and arithmetic ------------------------------------- */
ok(R.pack === 'protocols', 'the registry names its own pack');
ok(createHash('sha256').update(SRC).digest('hex').slice(0, 16) === R.source_stamp,
   'the registry was built from the current builder (stamp check)');
ok(R.pack_version === J('pack/manifest.json').pack_version,
   'one bundle version, read from the manifest rather than typed here');
ok(Array.isArray(R.provenance_tiers) && IDS.every((k) => R.provenance_tiers.includes(P[k].provenance))
   && !JSON.stringify(R).toUpperCase().includes('AI-SYNTHESIZED'),
   'every entry carries a tier this pack declares, and the reserved word '
   + 'AI-SYNTHESIZED appears nowhere — it belongs to orbis/');

/* ---- the roster the user asked for --------------------------------- */
const ASKED = ['virtuals-protocol', 'virtual-ventures', 'singularitynet', 'fetch-ai-asi',
               'olas', 'bittensor', 'ocean-protocol', 'cloudflare-wallets'].sort();
ok(IDS.join(',') === ASKED.join(','),
   `the roster is exactly the names the user asked for, as ids (${IDS.length}): ${IDS.join(', ')}`);
const UNID = IDS.filter((k) => P[k].unidentified === true);
ok(UNID.join(',') === 'cloudflare-wallets,virtual-ventures',
   `the two names that could not be identified with confidence are recorded `
   + `unidentified rather than mapped to a product: ${UNID.join(', ')}`);

/* ---- every field, every entry -------------------------------------- */
const FIELDS = ['id', 'name', 'url', 'url_status', 'unidentified', 'what_it_is', 'unit',
                'contribution_would_become', 'this_bundle_would_need', 'server_side_missing',
                'configured', 'integrated', 'validated_against_spec', 'why_off',
                'spec_fetched', 'description_provenance', 'provenance'];
{
  const missing = [];
  for (const k of IDS) for (const f of FIELDS) if (!(f in P[k])) missing.push(`${k}.${f}`);
  ok(missing.length === 0 && IDS.every((k) => P[k].id === k),
     `every entry has every one of the ${FIELDS.length} fields and its id matches its key`
     + (missing.length ? ` [missing: ${missing.join(', ')}]` : ''));
}
ok(IDS.every((k) => typeof P[k].what_it_is === 'string' && P[k].what_it_is.length > 60
     && typeof P[k].unit === 'string' && typeof P[k].contribution_would_become === 'string'),
   'each entry says in a sentence what it is, what its unit is and what a '
   + 'contribution would have to become');
ok(IDS.every((k) => Array.isArray(P[k].this_bundle_would_need) && P[k].this_bundle_would_need.length >= 1
     && P[k].this_bundle_would_need.every((s) => s.length > 30)
     && Array.isArray(P[k].server_side_missing) && P[k].server_side_missing.length >= 1),
   'each entry names what this bundle would need to hold (a key, an SDK, a '
   + 'contract address, an RPC) and the server-side piece that is missing, in sentences');
ok(IDS.every((k) => /AUTHORED/.test(P[k].description_provenance) && /general knowledge/.test(P[k].description_provenance)
     && P[k].provenance === 'AUTHORED'),
   'every description says on the entry that it is AUTHORED from general knowledge');
ok(IDS.every((k) => (P[k].url === null && P[k].url_status === 'none given')
     || (typeof P[k].url === 'string' && P[k].url.startsWith('https://') && /NOT fetched/.test(P[k].url_status))),
   'every URL is marked NOT fetched (none of the probes answered 2xx), or is honestly absent');

/* ---- NOTHING HERE IS ON -------------------------------------------- */
{
  const on = IDS.filter((k) => P[k].configured !== false || P[k].integrated !== false
                               || P[k].validated_against_spec !== false);
  ok(on.length === 0,
     `all ${IDS.length} entries carry configured false, integrated false and `
     + `validated_against_spec false — nothing integrates, sends, mints, registers or lists`
     + (on.length ? ` [ON: ${on.join(', ')}]` : ''));
}
ok(IDS.every((k) => /no server/.test(P[k].why_off) && /lie/.test(P[k].why_off)),
   'each entry says why it is off: no server, no key, no SDK, no address, no '
   + 'RPC, no spec read — and that flipping the flag would be a lie');

/* ---- the probe: RECORDED, and re-read from the stamped file --------- */
ok(/^\d{4}-\d{2}-\d{2}$/.test(PROBE.date) && R.reachability_probe.date === PROBE.date
   && R.reachability_probe.file === 'protocols/authored/probe.json',
   `the probe date is read from the stamped file, not from the clock (${PROBE.date})`);
const canon = (o) => JSON.stringify(Object.keys(o).sort().map((k) => [k, o[k]]));
ok(JSON.stringify([...PROBE.tried].sort((a, b) => a.host < b.host ? -1 : 1).map(canon))
   === JSON.stringify(R.reachability_probe.tried.map(canon)),
   `the probe records in the registry are the stamped file's, sorted by host, unchanged (${PROBE.tried.length} URLs)`);
ok(PROBE.tried.every((t) => /^[0-9]{3}$/.test(t.http_code) && Number.isInteger(t.curl_exit)
     && t.url.startsWith('https://'))
   && R.reachability_probe.provenance.startsWith('RECORDED'),
   'every stamped probe row has a 3-digit http code, an integer curl exit and an https URL, '
   + 'and the block is tiered RECORDED');
{
  const bad = [];
  for (const k of IDS) {
    const s = P[k].spec_fetched;
    if (!s || s.fetched !== false || s.provenance !== 'RECORDED') { bad.push(`${k}: not a fetched-false RECORDED record`); continue; }
    if (s.date !== PROBE.date) { bad.push(`${k}: date ${s.date}`); continue; }
    if (s.url_tried === null) {
      if (P[k].unidentified !== true || !/not probed/.test(s.how)) bad.push(`${k}: unprobed but identified or silent`);
      continue;
    }
    if (!/^[0-9]{3}$/.test(s.http_code)) { bad.push(`${k}: http_code ${JSON.stringify(s.http_code)}`); continue; }
    if (!Number.isInteger(s.curl_exit)) { bad.push(`${k}: curl_exit ${JSON.stringify(s.curl_exit)}`); continue; }
    const row = PROBE.tried.find((t) => t.url === s.url_tried);
    if (!row || row.http_code !== s.http_code || row.curl_exit !== s.curl_exit) bad.push(`${k}: code differs from the stamped file`);
  }
  ok(bad.length === 0,
     'every spec_fetched record says fetched false with the http code, the curl exit and '
     + 'the date that back it, copied from the stamped file; an entry with no URL says it '
     + `was not probed and is unidentified${bad.length ? ' [' + bad.join('; ') + ']' : ''}`);
}
ok(IDS.every((k) => P[k].spec_fetched.url_tried === null
     || (typeof P[k].spec_fetched.http_code === 'string' && !P[k].spec_fetched.http_code.startsWith('2')))
   && R.reachability_probe.answered_2xx === PROBE.tried.filter((t) => t.http_code.startsWith('2')).length,
   'no probe answered 2xx, recounted — the day one does, the description must be '
   + 'rewritten with the text open, not left as recollection');

/* ---- unidentified entries carry a why ------------------------------ */
ok(UNID.every((k) => typeof P[k].unidentified_why === 'string' && P[k].unidentified_why.length > 60
     && /invent/.test(P[k].unidentified_why))
   && IDS.filter((k) => !P[k].unidentified).every((k) => !('unidentified_why' in P[k])),
   'each unidentified entry says why it could not be identified and that a guess '
   + 'would invent a product; identified entries carry no such field');
ok(P['cloudflare-wallets'].nearest_real_offering
   && P['cloudflare-wallets'].nearest_real_offering.is_a_wallet === false
   && /gateway/i.test(P['cloudflare-wallets'].nearest_real_offering.name)
   && /AUTHORED/.test(P['cloudflare-wallets'].nearest_real_offering.caveat),
   'the Cloudflare entry names the nearest real offering (its Web3 gateways) '
   + 'and says it is not a wallet, with an AUTHORED caveat');
ok(P['virtual-ventures'].url === null && P['virtual-ventures'].spec_fetched.url_tried === null,
   'Virtual Ventures carries no URL and no probe — nothing was asked because '
   + 'nothing could be named');

/* ---- the wallets block: read from auth/, not restated -------------- */
const A = J('auth/registry/auth.json');
const W = R.wallets;
{
  const authRails = Object.keys(A.methods)
    .filter((k) => A.methods[k].kind === 'wallet-signature' && A.methods[k].configured === true).sort();
  const sup = W.supported.map((r) => r.id).sort();
  ok(sup.join(',') === authRails.join(',') && sup.length === 1,
     `the supported rails are exactly auth/'s configured wallet-signature methods: ${sup.join(', ')}`);
}
{
  const s = W.supported[0];
  const m = A.methods[s.id];
  ok(s.configured === true && s.authenticates === m.authenticates && s.gates_anything === m.gates_anything
     && s.chain_id === A.siwe.chain_id && s.signing_method === A.siwe.signing_method
     && s.verified_in_page === A.siwe.verification.implemented
     && /EIP-1193/.test(s.provider) && /EIP-4361/.test(s.name),
     'the SIWE rail restates auth.json verbatim — EIP-4361 over any EIP-1193 '
     + 'provider, chain id, signing method, verification, authenticates and gates flags');
  ok(/^no/.test(s.could_it_hand_a_contribution_to_a_protocol) && /none is built here/.test(W.none_sends_anything),
     'and says it cannot hand a contribution to any protocol: it signs a sentence, not a transaction');
}
{
  const c = W.candidates;
  const cids = c.map((r) => r.id);
  ok(c.every((r) => r.configured === false && r.integrated === false
       && Array.isArray(r.would_take) && r.would_take.length >= 1 && typeof r.reaches === 'string'),
     `every candidate rail is OFF and says what adding it would take (${cids.join(', ')})`);
  const cf = c.find((r) => r.id === 'cloudflare-wallets');
  ok(cf && cf.unidentified === true && typeof cf.unidentified_why === 'string' && cf.unidentified_why.length > 40,
     'the Cloudflare rail is recorded unidentified with a why, matching its roster entry');
}

/* ---- the contribution package -------------------------------------- */
{
  const c = R.contribution_package;
  const f = join(ROOT, 'contrib/registry/contrib.json');
  const present = existsSync(f);
  const idOk = present ? c.id === JSON.parse(readFileSync(f, 'utf8')).record_tag && /read from/.test(c.source)
                       : c.id === 'tc-contribution/1' && /not present/.test(c.source);
  ok(idOk && /not sent anywhere/.test(c.what_it_is_not),
     `the contribution package id is ${present ? 'read from contrib/registry/contrib.json#record_tag' : 'the brief\'s, and says contrib.json was not present'}: ${c.id}`);
}

/* ---- counts, recomputed -------------------------------------------- */
{
  const C = R.counts;
  const want = {
    protocols: IDS.length,
    identified: IDS.filter((k) => P[k].unidentified === false).length,
    unidentified: UNID.length,
    configured: IDS.filter((k) => P[k].configured === true).length,
    integrated: IDS.filter((k) => P[k].integrated === true).length,
    validated_against_spec: IDS.filter((k) => P[k].validated_against_spec === true).length,
    specs_fetched: IDS.filter((k) => P[k].spec_fetched.fetched === true).length,
    roster_entries_probed: IDS.filter((k) => P[k].spec_fetched.url_tried !== null).length,
    probe_urls_tried: PROBE.tried.length,
    probe_answered_2xx: PROBE.tried.filter((t) => t.http_code.startsWith('2')).length,
    wallet_rails_supported: W.supported.length,
    wallet_rails_candidate: W.candidates.length,
    wallet_rails_configured: [...W.supported, ...W.candidates].filter((r) => r.configured === true).length,
  };
  const off = Object.keys(want).filter((k) => C[k] !== want[k]);
  ok(off.length === 0 && Object.keys(C).sort().join(',') === Object.keys(want).sort().join(','),
     `every published count is recomputed from the entries (${want.protocols} protocols = `
     + `${want.identified} identified + ${want.unidentified} unidentified; ${want.configured} configured, `
     + `${want.integrated} integrated, ${want.specs_fetched} specs fetched)`
     + (off.length ? ` [off: ${off.map((k) => `${k} says ${C[k]} is ${want[k]}`).join(', ')}]` : ''));
  ok(C.configured === 0 && C.integrated === 0 && C.validated_against_spec === 0 && C.specs_fetched === 0,
     'and the four that must be zero are zero');
}
{
  // A typed count in the builder is a claim nobody recomputes. The counts
  // block in build.py may hold names and expressions, never a digit literal.
  const a = SRC.indexOf("'counts': {");
  const b = SRC.indexOf('}', a);
  const block = a >= 0 && b > a ? SRC.slice(a, b) : '';
  const typed = block.match(/'[a-z_0-9]+':\s*-?\d/g);
  ok(block.length > 0 && typed === null,
     'no count is typed in the builder — the counts block holds expressions only'
     + (typed ? ` [typed: ${typed.join(', ')}]` : ''));
}
ok(!/\.get\(/.test(SRC), 'the builder reads every key by name and never .get()s a default');

/* ---- honesty block ------------------------------------------------- */
ok(new RegExp(`all ${IDS.length} entries carry configured false`).test(R.honesty.nothing_integrates)
   && /no SDK is vendored, no key is held/.test(R.honesty.nothing_integrates)
   && R.honesty.descriptions_may_be_wrong.includes(PROBE.date)
   && UNID.every((k) => R.honesty.unidentified_are_unidentified.includes(k))
   && /configuration change after real work/.test(R.honesty.what_would_make_one_real),
   'the honesty block counts what is off, dates what was not read, names the '
   + 'unidentified, and says what would make one real');

console.log(`protocols/test: ${pass} checks passed${fail ? `, ${fail} FAILED` : ''}`);
process.exit(fail ? 1 : 0);
