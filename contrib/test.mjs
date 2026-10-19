/**
 * Contribution pack verification.
 *
 * The claim is small: the registry documents the package contract and is
 * DERIVED from training/ (episode shapes, trace cap) and auth/ (the signed
 * statement); the verifier passes the scripted fixture and fails every
 * mutant by exactly the rule the builder said it breaks; the signed path is
 * driven with a throwaway key (completion/test.mjs's signer, never the
 * verifier's) and tampered; and no default is ever taken (`??` and
 * `.get(k, default)` are forbidden in the verifier and the builder).
 *
 *   node contrib/test.mjs
 */
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { verify, digestOf, canonical, digestBody, signatureMessage, SIGNATURE_SCHEME, SIGNED_ATTESTATION, UNSIGNED_ATTESTATION, LAST_LINE } from './verify.mjs';
import { throwawayKey, signPersonal } from '../completion/test.mjs';

let n = 0;
const ok = (m, c, evidence = []) => {
  if (!c) { console.error('FAIL', m); for (const e of evidence) console.error('      ' + e); process.exit(1); }
  n++; console.log('  ok ', m);
};
const url = (p) => new URL(p, import.meta.url);
const read = (p) => JSON.parse(readFileSync(url(p), 'utf8'));

const reg = read('./registry/contrib.json');
const manifest = read('../pack/manifest.json');
const trainingReg = read('../training/registry/training.json');
const authReg = read('../auth/registry/auth.json');
const simsReg = read('../sims/registry/sims.json');
const hallsReg = read('../pack/registry/halls.json');
const campusesReg = read('../unions/registry/campuses.json');
const buildSrc = readFileSync(url('./build.py'), 'utf8');
const verifySrc = readFileSync(url('./verify.mjs'), 'utf8');

/* ------------------------------------------------------------- registry */
ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(readFileSync(fileURLToPath(url('./build.py')))).digest('hex').slice(0, 16));
ok('the registry names the product and pack version of the manifest, read not retyped',
  reg.product === manifest.product && reg.pack_version === manifest.pack_version && reg.record_tag === 'tc-contribution/1');
ok('the registry is DERIVED and says the fixture is scripted, not a learner',
  reg.provenance === 'DERIVED' && /SCRIPTED/.test(reg.provenance_note) && /not a learner/.test(reg.provenance_note)
  && reg.fixture.label === 'fixture - not a learner');
ok('episode_kinds: every kind and its field list is training.json#episode_kinds verbatim, and no kind is invented',
  JSON.stringify(Object.keys(reg.episode_kinds)) === JSON.stringify(Object.keys(trainingReg.episode_kinds))
  && Object.keys(trainingReg.episode_kinds).every((k) => JSON.stringify(reg.episode_kinds[k].fields) === JSON.stringify(trainingReg.episode_kinds[k].fields)));
ok('the one conditional field (sim.operator) is derived from training.json\'s own sentence, not typed: present only when actor is scripted-reference',
  JSON.stringify(Object.keys(reg.episode_kinds.sim.conditional_fields)) === JSON.stringify(['operator'])
  && reg.episode_kinds.sim.conditional_fields.operator.present_only_when.actor === 'scripted-reference'
  && reg.episode_kinds.sim.conditional_fields.operator.why === trainingReg.episode_kinds.sim.operator
  && /present ONLY when actor is scripted-reference/.test(trainingReg.episode_kinds.sim.operator)
  && Object.keys(reg.episode_kinds).filter((k) => k !== 'sim').every((k) => Object.keys(reg.episode_kinds[k].conditional_fields).length === 0));
ok('trace: max_samples and the sample keys are training.json\'s (the [{t, gauges}] shape parsed from outcome_shape.trace), '
  + 'and the registry says gauge fields are NOT enumerated so only count and keys are held',
  reg.trace.max_samples === trainingReg.trace.max_samples && JSON.stringify(reg.trace.sample_keys) === JSON.stringify(['t', 'gauges'])
  && trainingReg.episode_kinds.sim.outcome_shape.trace.startsWith('[{t, gauges}]')
  && reg.trace.gauge_fields_enumerated === false && /count/i.test(reg.trace.gauge_fields_why) && /nothing inside gauges/.test(reg.trace.gauge_fields_why)
  && JSON.stringify(reg.trace.outcome_keys_always) === JSON.stringify(Object.keys(trainingReg.episode_kinds.sim.outcome_shape).filter((k) => k !== 'trace')));
ok('the training source is training.json#storage.key, its cap, and the export_format it wraps - read, with no_agent_trained carried into honesty',
  reg.training_source.key === trainingReg.storage.key && reg.training_source.cap === trainingReg.storage.cap
  && JSON.stringify(reg.training_source.export_format_this_wraps) === JSON.stringify(trainingReg.export_format)
  && reg.honesty.no_agent_trained === trainingReg.export_format.no_agent_trained
  && reg.honesty.anonymous === trainingReg.honesty.anonymous);
ok('consent: a fixed statement, exactly two declared scopes (agent-training, robot-training), ONE licence with an SPDX id and a why, revocable true with what that means',
  typeof reg.consent.statement === 'string' && reg.consent.statement.length > 80
  && JSON.stringify(Object.keys(reg.consent.scopes).sort()) === JSON.stringify(['agent-training', 'robot-training'])
  && /^[A-Za-z0-9.-]+$/.test(reg.consent.license.spdx) && reg.consent.license.why.length > 80 && /never per record/.test(reg.consent.license.why)
  && reg.consent.revocable === true && /keeps the file/.test(reg.consent.revocable_means) && /Nothing here is uploaded/.test(reg.consent.revocable_means)
  && reg.consent.recorder_consent === trainingReg.honesty.consent);
ok('the digest rule is SHA-256 over canonical JSON of every field except digest, with contributor.signature forced to null, and says why',
  reg.digest.alg === 'SHA-256' && /keys sorted recursively, no whitespace, UTF-8/.test(reg.digest.over)
  && /contributor\.signature forced to null/.test(reg.digest.over) && /OVER the digest, made after it/.test(reg.digest.excludes_signature_why)
  && digestOf({ a: 1, contributor: { claimed: 'x', signature: { sig: 'y' } }, digest: {} })
    === digestOf({ a: 1, contributor: { claimed: 'x', signature: null }, digest: {} }));
ok('the signature rule: scheme eip191-personal_sign, the message structure with auth/\'s own statement PLUS the consent scope, '
  + 'recovery through auth/recover.mjs, the identity key from auth.json, and what it proves and does not',
  reg.signature.scheme === 'eip191-personal_sign' && reg.signature.message.statement === authReg.siwe.statement
  && reg.signature.signing_method === authReg.siwe.signing_method
  && /digest: <digest\.hex>/.test(reg.signature.message.structure) && /exported_at: <exported_at>/.test(reg.signature.message.structure)
  && /consent: <consent\.scope joined by comma>/.test(reg.signature.message.structure)
  && /auth\/recover\.mjs/.test(reg.signature.recovery) && /No second keccak and no second curve/.test(reg.signature.recovery)
  && /identity of a key, not of a person/.test(reg.signature.proves)
  && reg.signature.does_not_prove.some((s) => /nothing is written to any chain/.test(s))
  && reg.signature.does_not_prove.some((s) => /any agent or robot learned/.test(s))
  && reg.signature.where_the_wallet_comes_from.includes(authReg.storage.identity_key) && /never fabricated/.test(reg.signature.where_the_wallet_comes_from));
ok('the honesty block says: digest is integrity not identity; signature is a key not a person; nothing sent; no agent trained; nothing on any chain; gauges unchecked',
  /integrity since export, not identity/.test(reg.honesty.digest) && /identity of a key, not of a person/.test(reg.honesty.signature)
  && /Nothing is written to any chain/.test(reg.honesty.signature) && /no platform is integrated/i.test(reg.honesty.nothing_sent)
  && /no upload exists/.test(reg.honesty.nothing_sent)
  && reg.honesty.does_not_prove.some((s) => /any agent or robot learned/.test(s))
  && reg.honesty.does_not_prove.some((s) => /nothing is written to any chain/.test(s))
  && reg.honesty.does_not_prove.some((s) => /gauges inside a trace sample/.test(s))
  && reg.honesty.does_not_prove.some((s) => /learner keeps the file/.test(s)));
ok('the id sources name sims.json, halls.json and campuses.json with counts read from them, allow scenario null with a reason, and list what is NOT resolved',
  reg.id_sources.sim.count === Object.keys(simsReg.sims).length && reg.id_sources.hall.count === hallsReg.halls.length
  && reg.id_sources.campus.count === Object.keys(campusesReg.campuses).length && reg.id_sources.scenario.null_allowed === true
  && reg.id_sources.not_resolved.fields.includes('advisor') && reg.id_sources.not_resolved.fields.includes('point'));
ok('the destinations rule reads protocols/registry/protocols.json at page build time, renders empty without it, and types no platform name',
  /protocols\/registry\/protocols\.json/.test(reg.destinations.source) && /not integrated, not validated, nothing sent/.test(reg.destinations.rule)
  && /empty list/.test(reg.destinations.rule) && /No platform name is typed/.test(reg.destinations.rule));
ok('the verifier\'s last line is the registry\'s: a device recorded, a key vouched, not who, no agent or robot learned, nothing sent',
  LAST_LINE === reg.verifier.last_line && /not who/.test(LAST_LINE) && /any agent or robot learned/.test(LAST_LINE) && /nothing is sent anywhere/.test(LAST_LINE));
ok('the verifier imports recovery from auth/recover.mjs and carries no keccak, no curve arithmetic and no signing routine of its own',
  /from '\.\.\/auth\/recover\.mjs'/.test(verifySrc) && !/keccak/i.test(verifySrc.replace(/\/\*[\s\S]*?\*\/|\/\/.*$/gm, ''))
  && !/ptMul|SECP_G|signPersonal|generateKeyPair/.test(verifySrc));
ok('no default is ever taken: no `??` and no `.get(k, default)` in the verifier or the builder',
  !/\?\?/.test(verifySrc) && !/\.get\([^)]*,/.test(buildSrc) && !/\?\?/.test(buildSrc));
ok('the registry counts recompute: episode kinds, scopes, rules, mutants, sims, halls, campuses',
  reg.counts.episode_kinds === Object.keys(trainingReg.episode_kinds).length && reg.counts.scopes === Object.keys(reg.consent.scopes).length
  && reg.counts.rules === reg.verifier.rules.length && reg.counts.mutants === Object.keys(reg.fixture.mutants).length
  && reg.counts.sims === Object.keys(simsReg.sims).length && reg.counts.halls === hallsReg.halls.length
  && reg.counts.campuses === Object.keys(campusesReg.campuses).length && reg.counts.mutants >= 8);

/* -------------------------------------------------------------- fixture */
const good = read('./fixture/good.json');
const failsBy = (r) => { try { return Object.entries(verify(r).tally).filter(([, t]) => t.fails.length).map(([k]) => k); } catch (e) { return ['record.fields:' + e.message]; } };
const run = verify(good);
ok('the scripted fixture verifies on every rule, unsigned, "this device only", digest recomputed in node',
  failsBy(good).length === 0 && run.signature.state === 'unsigned' && good.contributor.attested_by === UNSIGNED_ATTESTATION
  && digestOf(good) === good.digest.hex && good.contributor.claimed === 'fixture - not a learner', [failsBy(good).join()]);
ok('the fixture holds one episode of every kind training.json declares, shaped by its field list, plus one human trace and one scripted-reference run with operator',
  Object.keys(trainingReg.episode_kinds).every((k) => run.summary.byKind[k] >= 1)
  && good.dataset.episodes.every((e) => {
    const want = trainingReg.episode_kinds[e.kind].fields;
    return Object.keys(e).every((f) => want.includes(f)) && want.every((f) => f in e || (f === 'operator' && e.actor === 'human'));
  })
  && good.dataset.episodes.some((e) => e.kind === 'sim' && e.actor === 'scripted-reference' && 'operator' in e)
  && good.dataset.episodes.some((e) => e.kind === 'sim' && e.actor === 'human' && !('operator' in e) && Array.isArray(e.outcome.trace)));
ok('the fixture\'s counts are what the verifier recomputes: episodes by kind, traces attached, sims covered, samples',
  JSON.stringify(good.dataset.episode_counts_by_kind) === JSON.stringify(Object.fromEntries(Object.keys(run.summary.byKind).sort().map((k) => [k, run.summary.byKind[k]])))
  && good.dataset.traces_attached === run.summary.traces && JSON.stringify(good.dataset.sims_covered) === JSON.stringify(run.summary.sims)
  && run.summary.samples === good.dataset.episodes.filter((e) => e.kind === 'sim' && e.outcome.trace).reduce((s, e) => s + e.outcome.trace.length, 0)
  && JSON.stringify(reg.fixture.episodes) === JSON.stringify(good.dataset.episode_counts_by_kind));
ok('the fixture\'s consent is the registry\'s: statement verbatim, both scopes, the one licence, revocable, a granted_at that parses',
  good.consent.statement === reg.consent.statement && JSON.stringify(good.consent.scope) === JSON.stringify(Object.keys(reg.consent.scopes).sort())
  && good.consent.license === reg.consent.license.spdx && good.consent.revocable === true && Number.isFinite(Date.parse(good.consent.granted_at)));
ok('every sim, scenario, hall and campus the fixture names resolves in sims.json, halls.json and campuses.json',
  good.dataset.episodes.every((e) => (!('sim' in e) || e.sim in simsReg.sims) && (!('hall' in e) || hallsReg.halls.some((h) => h.slug === e.hall))
    && (!('campus' in e) || e.campus in campusesReg.campuses)
    && (!('scenario' in e) || e.scenario === null || simsReg.sims[e.sim].scenarios.some((s) => s.id === e.scenario))));
ok('the verifier notes that gauges are unchecked when a trace is present', run.notes.some((x) => /nothing inside gauges is checked/.test(x)));

const files = readdirSync(fileURLToPath(url('./fixture'))).filter((f) => f.startsWith('mutant-')).sort();
ok('every mutant the registry names exists on disk and every mutant on disk is named (' + files.length + ')',
  files.length === Object.keys(reg.fixture.mutants).length && files.every((f) => Object.values(reg.fixture.mutants).some((m) => m.file === 'fixture/' + f)));
const REQUIRED = ['bad-digest', 'foreign-field-on-episode', 'unknown-sim', 'empty-scope', 'wrong-license', 'trace-over-max-samples',
  'forged-signature', 'consent-granted-at-unparseable'];
ok('the eight mutants the contract calls for are present: ' + REQUIRED.join(', '), REQUIRED.every((m) => m in reg.fixture.mutants));
for (const [name, m] of Object.entries(reg.fixture.mutants)) {
  const rec = read('./' + m.file);
  const fails = failsBy(rec);
  const one = fails.length === 1 && (fails[0] === m.fails || fails[0].startsWith(m.fails + ':'));
  ok(`mutant ${name} fails by exactly one rule, ${m.fails}, and no other`, one, [fails.join(' | ')]);
}
ok('mutant bad-digest is refused by the digest rule before anything else is believed (the CLI exits 1 and prints FAIL digest)',
  (() => { const r = spawnSync(process.execPath, [fileURLToPath(url('./verify.mjs')), fileURLToPath(url('./fixture/mutant-bad-digest.json'))], { encoding: 'utf8' });
    return r.status === 1 && /^FAIL digest:/m.test(r.stderr); })());
{
  const r = spawnSync(process.execPath, [fileURLToPath(url('./verify.mjs')), fileURLToPath(url('./fixture/good.json'))], { encoding: 'utf8' });
  ok('the CLI on the fixture exits 0, prints counts (episodes by kind, traces, samples, sims covered) and the honest last line',
    r.status === 0 && /^summary: 6 episodes \(advisor 1, crew 1, sim 3, walkaround 1\), 1 trace\(s\) attached holding 4 samples, 2 sim\(s\) covered/m.test(r.stdout)
    && r.stdout.trim().split('\n').pop() === LAST_LINE, [r.stdout.split('\n').slice(-3).join(' | ')]);
}

/* --------------------------------------------------------- signed path */
/* the signer is completion/test.mjs's throwaway key over auth/'s own curve;
   this pack has no signing routine and the verifier imports none */
function signPackage(record, key) {
  const out = JSON.parse(JSON.stringify(record));
  out.contributor.claimed = key.address;
  out.contributor.attested_by = SIGNED_ATTESTATION;
  out.contributor.signature = null;
  out.digest = { ...out.digest, hex: digestOf(out) };
  const message = signatureMessage(out.digest.hex, out.exported_at, out.consent.scope);
  out.contributor.signature = { scheme: SIGNATURE_SCHEME, address: key.address, message, sig: signPersonal(key.d, message) };
  return out;
}
const key = throwawayKey(), other = throwawayKey();
const signed = signPackage(good, key);
const sr = verify(signed);
ok('signed with a throwaway key, the fixture verifies on every rule and the verifier recovers exactly that address; the digest is unchanged by attaching the signature',
  failsBy(signed).length === 0 && sr.signature.state === 'signed' && sr.signature.recovered === key.address
  && digestOf(signed) === signed.digest.hex && canonical(digestBody(signed)) === canonical(digestBody({ ...signed, contributor: { ...signed.contributor, signature: null } }))
  && /identity of a key, not of a person/.test(sr.signature.line), [failsBy(signed).join(), sr.signature.line]);
ok('the signed message carries the consent scope: statement, digest, exported_at, consent line',
  signed.contributor.signature.message === authReg.siwe.statement + '\ndigest: ' + signed.digest.hex + '\nexported_at: ' + signed.exported_at
    + '\nconsent: ' + good.consent.scope.join(','));
const bitFlip = JSON.parse(JSON.stringify(signed));
{ const u = Buffer.from(bitFlip.contributor.signature.sig.slice(2), 'hex'); u[40] ^= 1; bitFlip.contributor.signature.sig = '0x' + u.toString('hex'); }
const otherKey = JSON.parse(JSON.stringify(signed)); otherKey.contributor.signature.sig = signPersonal(other.d, signed.contributor.signature.message);
const badMsg = JSON.parse(JSON.stringify(signed)); badMsg.contributor.signature.message += ' '; badMsg.contributor.signature.sig = signPersonal(key.d, badMsg.contributor.signature.message);
const swapped = JSON.parse(JSON.stringify(signed)); swapped.contributor.signature.address = other.address; swapped.contributor.claimed = other.address; swapped.digest.hex = digestOf(swapped);
const wrongScheme = JSON.parse(JSON.stringify(signed)); wrongScheme.contributor.signature.scheme = 'eip712-typed-data';
const scopeAfter = JSON.parse(JSON.stringify(signed)); scopeAfter.consent.scope = ['agent-training']; scopeAfter.digest.hex = digestOf(scopeAfter);
ok('and it is refused by name when tampered: one bit flipped, another key, another message, the address swapped, the wrong scheme - each fails contributor.signature alone',
  [bitFlip, otherKey, badMsg, swapped, wrongScheme].every((r) => failsBy(r).join() === 'contributor.signature'),
  [bitFlip, otherKey, badMsg, swapped, wrongScheme].map((r) => failsBy(r).join()));
ok('a consent scope narrowed AFTER signing (digest restamped) fails contributor.signature: the scope is inside the signed message',
  failsBy(scopeAfter).join() === 'contributor.signature', [failsBy(scopeAfter).join()]);
const edited = JSON.parse(JSON.stringify(signed)); edited.dataset.traces_attached = 0; edited.dataset.episodes[1].outcome = { passed: true, rows: [] };
const restamped = JSON.parse(JSON.stringify(edited)); restamped.digest.hex = digestOf(restamped);
ok('an episode edited under a valid signature fails digest (the bytes moved); restamping the digest to hide it moves the failure to contributor.signature (the signed message names the old digest)',
  failsBy(edited).join() === 'digest' && failsBy(restamped).join() === 'contributor.signature', [failsBy(edited).join(), failsBy(restamped).join()]);


/* ---- one core, two shells: the rules the verify page carries ---- */
{
  const V = await import('./verify.mjs');
  const { webcrypto } = await import('node:crypto');
  const { recoverAddress } = await import('../auth/recover.mjs');
  const src = readFileSync(url('./verify.mjs'), 'utf8');
  const a = src.indexOf('/* CONTRIB_CORE:BEGIN'), b = src.indexOf('/* CONTRIB_CORE:END */');
  const block = a >= 0 && b > a ? src.slice(a, b) : '';
  const pure = block.includes('function contribCore(regs) {') && !/\bfetch\b|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|indexedDB|readFileSync|createHash|\bimport\s*\(|^\s*(import|export)\b|\?\?/m.test(block);
  const regs = Object.fromEntries(Object.entries(V.REGISTRY_FILES).map(([k, p]) => [k, JSON.parse(readFileSync(url('../' + p), 'utf8'))]));
  const core = V.contribCore(regs);
  const failsOf = async (rec, useAsync) => {
    try {
      const r = useAsync ? await core.verifyAsync(rec, webcrypto.subtle, recoverAddress) : V.verify(rec);
      return Object.keys(r.tally).filter((k) => r.tally[k].fails.length).join();
    } catch (e) { return 'threw: ' + e.message; }
  };
  const inputs = ['fixture/good.json', ...Object.values(reg.fixture.mutants).map((m) => m.file)];
  const diverge = [];
  for (const f of inputs) { const rec = read('./' + f); const s = await failsOf(rec, false), x = await failsOf(rec, true); if (s !== x) diverge.push(f + ': ' + s + ' vs ' + x); }
  ok('the rules live in one pure core between the CONTRIB_CORE markers (no file, network, storage, module statement or ??) that web/build_verify.py carries into the verify page, '
    + 'and its verifyAsync over webcrypto.subtle - the browser path - fails the fixture and every mutant exactly as verify() does (' + inputs.length + ' files)',
    pure && diverge.length === 0 && core.LAST_LINE === V.LAST_LINE, diverge);
}

/* ------------------------------------------- tc-contribution/2 (wave 11, DATASHARE) */
{
  const roboticsReg = read('../robotics/registry/robotics.json');
  const g2 = read('./fixture/v2/good.json');
  const r2 = verify(g2);
  ok('[v2] the registry names both record tags: tc-contribution/1 (unchanged, still verified) and tc-contribution/2 (current), and the v2-only rules',
    reg.record_tag === 'tc-contribution/1' && reg.record_tag_current === 'tc-contribution/2'
    && JSON.stringify(Object.keys(reg.record_tags).sort()) === JSON.stringify(['tc-contribution/1', 'tc-contribution/2'])
    && JSON.stringify(reg.record_tags['tc-contribution/1'].kinds) === JSON.stringify(Object.keys(trainingReg.episode_kinds).sort())
    && JSON.stringify(reg.record_tags['tc-contribution/2'].rules_only_v2) === JSON.stringify(['origin.classroom', 'privacy', 'ids.env', 'world.samples', 'world.outcome'])
    && reg.record_tags['tc-contribution/2'].rules_only_v2.every((r) => reg.verifier.rules.includes(r)));
  ok('[v2] world_episode_kinds are training.json#world_episode_kinds verbatim (fields, sample and outcome keys, cap, hz, dt) - read, not typed',
    JSON.stringify(Object.keys(reg.world_episode_kinds)) === JSON.stringify(Object.keys(trainingReg.world_episode_kinds))
    && Object.entries(reg.world_episode_kinds).every(([k, w]) => JSON.stringify(w.fields) === JSON.stringify(trainingReg.world_episode_kinds[k].fields)
      && JSON.stringify(w.sample_keys) === JSON.stringify(Object.keys(trainingReg.world_episode_kinds[k].sample_shape))
      && JSON.stringify(w.outcome_keys) === JSON.stringify(Object.keys(trainingReg.world_episode_kinds[k].outcome_shape))
      && w.max_samples === trainingReg.world_teleop.max_samples && w.sample_hz === trainingReg.world_teleop.sample_hz && w.dt_s === trainingReg.world_teleop.dt_s));
  const robokit = Object.keys(roboticsReg.envs).filter((e) => roboticsReg.envs[e].runner === 'robokit').sort();
  ok('[v2] world_envs are exactly the robokit envs of robotics.json with their embodiments, action fields, termination ids and reward terms, read',
    JSON.stringify(Object.keys(reg.world_envs.envs).sort()) === JSON.stringify(robokit)
    && robokit.every((e) => { const a = reg.world_envs.envs[e], b = roboticsReg.envs[e];
      return JSON.stringify(a.embodiments) === JSON.stringify(b.embodiments) && JSON.stringify(a.action_fields) === JSON.stringify(b.action.fields.map((f) => f.name))
        && JSON.stringify(a.termination) === JSON.stringify(b.termination.map((t) => t.id)) && JSON.stringify(a.reward_terms) === JSON.stringify(b.reward.map((r) => r.term))
        && a.cap_steps === b.episode_cap.steps; }));
  ok('[v2] the privacy rule lists person, free-text, precise-location and media/biometric keys, says the list is partial, caps strings, and the origin rule quotes training.json\'s classroom sentence',
    ['person', 'free_text', 'precise_location', 'media_biometric'].every((c) => Array.isArray(reg.privacy.forbidden_keys[c]) && reg.privacy.forbidden_keys[c].length > 3)
    && ['name', 'email', 'lat', 'lon', 'audio', 'camera', 'biometric', 'text'].every((k) => Object.values(reg.privacy.forbidden_keys).flat().includes(k))
    && /partial list/.test(reg.privacy.forbidden_keys_note) && Number.isInteger(reg.privacy.free_text_max)
    && reg.origin.classroom_from === trainingReg.world_teleop.classroom && /not offered/.test(reg.origin.classroom_from));
  ok('[v2] the v2 fixture verifies on every rule, unsigned with claimed null, origin.classroom_mode false, and carries every /1 kind plus world episodes by a human and the scripted reference',
    Object.values(r2.tally).every((t) => t.fails.length === 0) && g2.record === 'tc-contribution/2' && g2.contributor.claimed === null
    && g2.origin.classroom_mode === false && [...Object.keys(trainingReg.episode_kinds), ...Object.keys(trainingReg.world_episode_kinds)].every((k) => r2.summary.byKind[k] >= 1)
    && g2.dataset.episodes.some((e) => e.kind === 'world-teleop' && e.actor === 'human') && g2.dataset.episodes.some((e) => e.kind === 'world-teleop' && e.actor === 'scripted-reference')
    && r2.tally['ids.env'].checked > 0 && r2.tally['world.samples'].checked > 0 && r2.tally['world.outcome'].checked > 0 && r2.tally.privacy.checked > 0,
    [Object.entries(r2.tally).filter(([, t]) => t.fails.length).map(([k, t]) => k + ': ' + t.fails[0]).join(' | ')]);
  ok('[v2] the /1 fixture still verifies unchanged, and the v2-only rules check nothing on it (a /1 package is verified exactly as before)',
    failsBy(good).length === 0 && ['origin.classroom', 'privacy', 'ids.env', 'world.samples', 'world.outcome'].every((r) => run.tally[r].checked === 0));
  const v2files = readdirSync(fileURLToPath(url('./fixture/v2'))).filter((f) => f.startsWith('mutant-')).sort();
  ok('[v2] every v2 mutant the registry names exists on disk and every one on disk is named (' + v2files.length + ')',
    v2files.length === Object.keys(reg.fixture_v2.mutants).length && v2files.length >= 12
    && v2files.every((f) => Object.values(reg.fixture_v2.mutants).some((m) => m.file === 'fixture/v2/' + f)));
  for (const [name, m] of Object.entries(reg.fixture_v2.mutants)) {
    const fails = failsBy(read('./' + m.file));
    ok(`[v2] mutant ${name} fails by exactly one rule, ${m.fails}, and no other`, fails.length === 1 && (fails[0] === m.fails || fails[0].startsWith(m.fails + ':')), [fails.join(' | ')]);
  }
  ok('[v2] a /2 package that says record tc-contribution/1 (no restamp of meaning) is refused: a /1 package holds no world episode',
    (() => { const x = JSON.parse(JSON.stringify(g2)); x.record = 'tc-contribution/1'; delete x.origin; x.digest.hex = digestOf(x); return failsBy(x).includes('episode.kind'); })());
  ok('[v2] a /2 package verifies through verifyAsync (the browser and Worker path) exactly as through verify()',
    await (async () => { const { webcrypto } = await import('node:crypto'); const V = await import('./verify.mjs');
      const core = V.contribCore(Object.fromEntries(Object.entries(V.REGISTRY_FILES).map(([k, rel]) => [k, JSON.parse(readFileSync(url('../' + rel), 'utf8'))])));
      const { recoverAddress } = await import('../auth/recover.mjs');
      const a = await core.verifyAsync(g2, webcrypto.subtle, recoverAddress);
      return Object.values(a.tally).every((t) => t.fails.length === 0); })());
}

console.log(`\ncontrib: ${n} checks, 0 failures`);
