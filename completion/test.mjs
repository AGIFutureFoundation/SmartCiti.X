/**
 * Completion pack verification.
 *
 * The claim is small: the registry documents the record contract and is
 * derived from the registries it names; the verifier passes the scripted
 * fixture and fails every mutant by the rule the builder said it breaks; no
 * learner count is typed; and no default is ever taken (`??` is forbidden in
 * the verifier and the builder, spec §23.1).
 */
import { createHash, generateKeyPairSync, randomBytes } from 'node:crypto';
import { readFileSync, writeFileSync, mkdtempSync, rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { verify, digestOf, need, signatureMessage, SIGNATURE_SCHEME, SIGNED_ATTESTATION } from './verify.mjs';
import { keccak256, te, ptMul, SECP_G, SECP_N, addressOfPubkey } from '../auth/recover.mjs';

/* ---- SIGNING LIVES HERE, in the test, and nowhere in the verifier ----------
   A throwaway secp256k1 key from node:crypto and an EIP-191 personal_sign
   signer written over the sign-in page's own point arithmetic (imported from
   auth/recover.mjs - the arithmetic auth/test.mjs holds against node's own
   secp256k1). Exported so web/test_progress.mjs can sign the page's record
   with the same routine; importing this file runs no checks (see isMain). */
const beI = (u) => BigInt('0x' + Buffer.from(u).toString('hex'));
const h32 = (v) => v.toString(16).padStart(64, '0');
function invN(a) {
  let o = ((a % SECP_N) + SECP_N) % SECP_N, r = SECP_N, x = 1n, y = 0n;
  while (r !== 0n) { const q = o / r; [o, r] = [r, o - q * r]; [x, y] = [y, x - q * y]; }
  return ((x % SECP_N) + SECP_N) % SECP_N;
}
export function throwawayKey() {
  const { privateKey } = generateKeyPairSync('ec', { namedCurve: 'secp256k1' });
  const jwk = privateKey.export({ format: 'jwk' });
  const d = beI(Buffer.from(jwk.d, 'base64url'));
  const Q = ptMul(d, SECP_G);
  const fromNode = [beI(Buffer.from(jwk.x, 'base64url')), beI(Buffer.from(jwk.y, 'base64url'))];
  if (Q[0] !== fromNode[0] || Q[1] !== fromNode[1]) throw new Error('the page\'s curve and node\'s disagree on this key\'s public point');
  return { d, address: addressOfPubkey(Q) };
}
export function signPersonal(d, message) {
  const body = Buffer.from(message, 'utf8');
  const pre = Buffer.concat([Buffer.from('\x19Ethereum Signed Message:\n' + body.length, 'utf8'), body]);
  const z = beI(keccak256(new Uint8Array(pre))) % SECP_N;
  for (;;) {
    const k = (beI(randomBytes(32)) % (SECP_N - 1n)) + 1n;
    const R = ptMul(k, SECP_G);
    const r = R[0] % SECP_N;
    if (r === 0n) continue;
    let s = (invN(k) * (z + r * d)) % SECP_N;
    if (s === 0n) continue;
    let rec = Number(R[1] & 1n);
    if (s > SECP_N / 2n) { s = SECP_N - s; rec ^= 1; }
    return '0x' + h32(r) + h32(s) + (27 + rec).toString(16).padStart(2, '0');
  }
}
/* re-attest a record to a wallet and sign its digest: claimed and attested_by
   are INSIDE the digest, so they are set first and the digest restamped; the
   signature is made over that digest and sits outside it */
export function signRecord(record, key) {
  const out = JSON.parse(JSON.stringify(record));
  out.identity.claimed = key.address;
  out.identity.attested_by = SIGNED_ATTESTATION;
  out.identity.signature = null;
  out.digest = { ...out.digest, hex: digestOf(out) };
  const message = signatureMessage(out.digest.hex, out.exported_at);
  out.identity.signature = { scheme: SIGNATURE_SCHEME, address: key.address, message, sig: signPersonal(key.d, message) };
  return out;
}

const isMain = process.argv[1] && new URL(`file://${process.argv[1]}`).pathname === new URL(import.meta.url).pathname;
if (isMain) {
let n = 0;
const ok = (m, c) => { if (!c) { console.error('FAIL', m); process.exit(1); } n++; console.log('  ok ', m); };
const url = (p) => new URL(p, import.meta.url);
const read = (p) => JSON.parse(readFileSync(url(p), 'utf8'));

const reg = read('./registry/completion.json');
const manifest = read('../pack/manifest.json');
const lessonsReg = read('../lessons/registry/lessons.json');
const simsReg = read('../sims/registry/sims.json');
const buildSrc = readFileSync(url('./build.py'), 'utf8');
const verifySrc = readFileSync(url('./verify.mjs'), 'utf8');

ok('the registry was built from the current builder source (stamp check)',
  reg.source_stamp === createHash('sha256').update(readFileSync(fileURLToPath(url('./build.py')))).digest('hex').slice(0, 16));
ok('the registry names the product and pack version of the manifest, read not retyped',
  reg.product === manifest.product && reg.pack_version === manifest.pack_version);
ok('the registry is DERIVED and says the fixture is scripted, not a learner',
  reg.provenance === 'DERIVED' && /SCRIPTED/.test(reg.provenance_note) && /not a learner/.test(reg.provenance_note));

const FIELDS = ['record', 'product', 'pack_version', 'exported_at', 'identity', 'lessons', 'sims', 'tools', 'stations', 'honesty', 'digest'];
ok('the contract documents every top-level record field with what it proves',
  FIELDS.every((f) => f in reg.contract && ('proves' in reg.contract[f] || f === 'digest')));
ok('the digest rule is SHA-256 over canonical JSON of every field except digest',
  reg.digest.alg === 'SHA-256' && /keys sorted recursively, no whitespace, UTF-8/.test(reg.digest.over));

ok('the honesty block says a digest proves integrity since export, not identity',
  /integrity since export, not identity/.test(reg.honesty.digest));
ok('the honesty block says signature is null unless a wallet signed, that this bundle has no key of its own and no server, '
  + 'that a wallet signature is the identity of a key and not of a person, that nothing is on any chain, and that a mismatch is a forgery',
  /null unless a wallet signed/.test(reg.honesty.signature) && /no key of its own and no server/.test(reg.honesty.signature)
  && /identity of a key, not of a person/.test(reg.honesty.signature) && /forgery/.test(reg.honesty.signature)
  && /Nothing is written to any chain/.test(reg.honesty.signature) && /nothing is anchored/.test(reg.honesty.signature)
  && reg.honesty.does_not_prove.some((s) => /nothing is written to any chain/.test(s)));
ok('the digest rule excludes identity.signature by forcing it to null, and says why (the signature is over the digest)',
  /identity\.signature forced to null/.test(reg.digest.over) && /OVER the digest, made after it/.test(reg.digest.excludes_signature_why)
  && digestOf({ a: 1, identity: { claimed: 'x', signature: { sig: 'y' } }, digest: {} })
    === digestOf({ a: 1, identity: { claimed: 'x', signature: null }, digest: {} }));
ok('the signature rule is recorded: scheme eip191-personal_sign, the message structure with auth/\'s own statement, '
  + 'recovery through auth/recover.mjs (no second keccak), and what it proves and does not (a key, not a person; no chain)',
  reg.signature.scheme === 'eip191-personal_sign' && reg.signature.message.statement === read('../auth/registry/auth.json').siwe.statement
  && /digest: <digest\.hex>/.test(reg.signature.message.structure) && /exported_at: <exported_at>/.test(reg.signature.message.structure)
  && /auth\/recover\.mjs/.test(reg.signature.recovery) && /No second keccak and no second curve/.test(reg.signature.recovery)
  && /identity of a key, not of a person/.test(reg.signature.proves) && reg.signature.does_not_prove.some((s) => /nothing is written to any chain/.test(s))
  && reg.signature.does_not_prove.some((s) => /accreditation/.test(s)) && reg.signature.when_signed.includes('lowercase hex')
  && reg.signature.where_the_wallet_comes_from.includes(read('../auth/registry/auth.json').storage.identity_key)
  && /never fabricated/.test(reg.signature.where_the_wallet_comes_from));
ok('the verifier imports recovery from auth/recover.mjs and carries no keccak, no curve arithmetic and no signing routine of its own',
  /from '\.\.\/auth\/recover\.mjs'/.test(verifySrc)
  && !/function (keccak|sponge|ptMul|ptAdd|recoverPubkey|sign)\b|SECP_|randomBytes|generateKeyPair|0x1n << 256n/.test(verifySrc)
  && !/function (keccak|sponge|ptMul|ptAdd|recoverPubkey)/.test(readFileSync(url('../auth/recover.mjs'), 'utf8')));
ok('the honesty block says nothing here is an accreditation',
  reg.honesty.accreditation === 'nothing here is an accreditation'
  && reg.honesty.does_not_prove.some((s) => /accreditation/.test(s)));
ok('no duration and no price is claimed',
  reg.honesty.does_not_prove.some((s) => /duration/.test(s) && /price/.test(s)));
ok('the word AI-SYNTHESIZED appears nowhere in this pack',
  !/AI.SYNTHESIZED/.test(buildSrc) && !/AI.SYNTHESIZED/.test(verifySrc) && !/AI.SYNTHESIZED/.test(JSON.stringify(reg)));

// evidence rule per kind, read from lessons.json
const kinds = Object.keys(lessonsReg.step_kinds);
ok('the evidence rule covers every step kind of lessons.json and no other',
  kinds.every((k) => k in reg.evidence_rule) && Object.keys(reg.evidence_rule).length === kinds.length);
ok('a kind is a recording kind exactly when lessons.json says it records an episode',
  kinds.every((k) => (lessonsReg.step_kinds[k].records !== null) === (reg.evidence_rule[k].class === 'episode-backed'))
  && reg.recording_kinds.every((k) => lessonsReg.step_kinds[k].records !== null));
ok('every silent kind carries the reason lessons.json gives for writing nothing',
  reg.silent_kinds.every((k) => reg.evidence_rule[k].why_no_episode === lessonsReg.step_kinds[k].why_no_episode));
ok('the recording / silent step counts equal those of lessons.json',
  reg.counts.recording_steps === lessonsReg.counts.recording_steps && reg.counts.silent_steps === lessonsReg.counts.silent_steps);
const trainingReg0 = read('../training/registry/training.json');
ok('walk and placard are episode-backed since wave 20, station and crib since wave 21: every kind is episode-backed, none is a device mark or self-reported, and both classes stay declared (inert) so a kind added with only a mark cannot be called evidence-backed',
  ['walk', 'placard', 'station', 'crib'].every((k) => reg.evidence_rule[k].class === 'episode-backed' && reg.evidence_rule[k].records === k)
  && reg.silent_kinds.length === 0 && reg.counts.silent_steps === 0 && reg.counts.device_mark_steps === 0
  && !Object.values(reg.evidence_rule).some((r) => r.class === 'self-reported' || r.class === 'device-mark')
  && /no step kind today/.test(reg.evidence_classes['self-reported'])
  && /no step kind today/.test(reg.evidence_classes['device-mark']) && /not a recorded episode/.test(reg.evidence_classes['device-mark'])
  && /inert/.test(reg.evidence_classes['device-mark'])
  && /only this class is called evidence-backed/.test(reg.evidence_classes['episode-backed']));
ok('a walk or placard step is matched on the hall and the step\'s own where (the strand, so one room), read from training.json: both episodes record where and room, and the rule says so',
  ['walk', 'placard'].every((k) => trainingReg0.episode_kinds[k].fields.includes('where') && trainingReg0.episode_kinds[k].fields.includes('room')
    && reg.evidence_rule[k].checkable.includes('where') && reg.evidence_rule[k].checkable.includes('hall')
    && reg.evidence_rule[k].names_read_field === 'room' && reg.evidence_rule[k].not_checkable.length === 0 && reg.evidence_rule[k].evidenceable === true)
  && /room is one of the step's names_read/.test(reg.evidence_rule.walk.rule));
ok('a placard step is held to the declared dwell: at_least.dwell_ms is training.json#episode_kinds.placard.at_least.dwell_ms, the one truth step_episodes also reads (read, not typed) and walk is held to no floor',
  reg.evidence_rule.placard.at_least.dwell_ms === trainingReg0.episode_kinds.placard.at_least.dwell_ms && trainingReg0.episode_kinds.placard.at_least.dwell_ms === trainingReg0.step_episodes.placard.dwell_ms && trainingReg0.step_episodes.placard.dwell_ms > 0
  && Object.keys(reg.evidence_rule.walk.at_least).length === 0
  && ['advisor', 'crew', 'sim', 'walkaround'].every((k) => reg.evidence_rule[k].names_read_field === null && Object.keys(reg.evidence_rule[k].at_least).length === 0));
ok('every walk and placard step of every lesson carries a where that names a strand, and every one has exactly one name in names_read (the room)',
  Object.values(lessonsReg.lessons).flatMap((L) => L.steps).filter((s) => s.kind === 'walk' || s.kind === 'placard')
    .every((s) => typeof s.where === 'string' && Array.isArray(s.names_read) && s.names_read.length === 1));
ok('honesty says what a station or crib episode does not mean, and that the tc-progress marks are device-local and feed no step',
  reg.honesty.does_not_prove.some((x) => /station or crib episode means more than it says/.test(x) && /not that the checklist was read/.test(x)
    && /found by trying every option/.test(x) && /feed no step/.test(x)));
ok('a station step is matched on the hall, the step\'s where (the strand of its bench) and its station id, a crib step on the hall, where (tools) and its district, both read from training.json; names are one of names_read; the crib is floored at the declared picks',
  trainingReg0.episode_kinds.station.fields.includes('station') && trainingReg0.episode_kinds.crib.fields.includes('crib')
  && ['station', 'crib'].every((k) => ['hall', 'where', k].every((f) => reg.evidence_rule[k].checkable.includes(f))
    && reg.evidence_rule[k].not_checkable.length === 0 && reg.evidence_rule[k].evidenceable === true)
  && reg.evidence_rule.station.names_read_field === 'station_name' && reg.evidence_rule.crib.names_read_field === 'crib_name'
  && Object.keys(reg.evidence_rule.station.at_least).length === 0
  && reg.evidence_rule.crib.at_least.picks === trainingReg0.episode_kinds.crib.at_least.picks
  && trainingReg0.episode_kinds.crib.at_least.picks === read('../tools/registry/toolcribs.json').drill.picks);
ok('every station and crib step of every lesson carries the ids its episode records and names_read holds the display name its episode records first',
  Object.values(lessonsReg.lessons).flatMap((L) => L.steps).filter((s) => s.kind === 'station' || s.kind === 'crib')
    .every((s) => typeof s.where === 'string' && (s.kind === 'station' ? typeof s.station === 'string' : s.where === 'tools' && typeof s.crib === 'string')
      && Array.isArray(s.names_read) && s.names_read.length >= 2));
ok('per lesson, the episode-backed, device-mark and self-reported counts sum to the lesson\'s steps',
  Object.entries(reg.lessons).every(([lid, p]) => p.episode_backed_steps + p.device_mark_steps + p.self_reported_steps === p.steps
    && p.recording_steps === p.episode_backed_steps
    && p.steps === lessonsReg.lessons[lid].steps.length && p.hall === lessonsReg.lessons[lid].hall));
ok('every lesson of lessons.json is in the registry and none other',
  Object.keys(reg.lessons).length === Object.keys(lessonsReg.lessons).length
  && Object.keys(lessonsReg.lessons).every((l) => l in reg.lessons));

// per sim: threshold read, never invented
ok('every seat of sims.json has a pass rule entry and its scenarios are read from there',
  Object.keys(simsReg.sims).every((s) => s in reg.sims
    && JSON.stringify(reg.sims[s].scenarios) === JSON.stringify(simsReg.sims[s].scenarios.map((x) => x.id))));
ok('no scalar threshold exists in sims.json, so every seat says threshold null and why',
  !JSON.stringify(simsReg).includes('"threshold"')
  && Object.values(reg.sims).every((s) => s.threshold === null && /no scalar score threshold/.test(s.why))
  && reg.counts.sims_with_threshold === 0);
ok('the rubric axes per seat are the ones sims.json states, with their pass rules',
  Object.entries(reg.sims).every(([sid, s]) => JSON.stringify(s.rubric_axes)
    === JSON.stringify(simsReg.sims[sid].rubric.map((a) => ({ axis: a.axis, pass: a.pass })))));

ok('the ladder prerequisites are lessons.json\'s edges, verbatim',
  JSON.stringify(reg.ladder) === JSON.stringify(lessonsReg.ladder.edges)
  && Object.entries(reg.lessons).every(([lid, p]) => JSON.stringify(p.needs)
    === JSON.stringify(lessonsReg.ladder.edges.filter((e) => e.lesson === lid).map((e) => e.needs).sort())));

// the fixture
const good = read('./fixture/good.json');
ok('the fixture is labelled as not a learner and carries no signature',
  good.identity.claimed === 'fixture — not a learner' && good.identity.signature === null);
ok('the fixture carries every contract field', FIELDS.every((f) => f in good));
ok('the fixture digest recomputes in JavaScript over the Python-written record', digestOf(good) === good.digest.hex);
const goodRun = verify(good);
ok('the verifier passes the fixture on every rule',
  Object.values(goodRun.tally).every((t) => t.fails.length === 0)
  && Object.keys(goodRun.tally).length === reg.verifier.rules.length);
ok('the verifier reports passing as taken from the record when no threshold exists',
  goodRun.notes.some((s) => /taken from the record and not re-derived/.test(s)));
const doneIn = (cls) => good.lessons.filter((l) => l.complete).flatMap((l) => l.steps)
  .filter((s) => s.done && reg.evidence_rule[s.kind].class === cls).length;
ok('the honest summary prints all three counts: episode-backed, device-mark and self-reported',
  goodRun.summary.nComplete === good.lessons.filter((l) => l.complete).length
  && goodRun.summary.nEpisode === doneIn('episode-backed') && goodRun.summary.nDeviceMark === doneIn('device-mark')
  && goodRun.summary.nSelfReported === good.lessons.filter((l) => l.complete)
    .flatMap((l) => l.steps).filter((s) => s.done && reg.evidence_rule[s.kind].class === 'self-reported').length);

// ---- evidence strength by kind (HONEST): declared in the registry, reported next to every total, read by no rule ----
const VV = await import('./verify.mjs');
const STR = reg.evidence_strength;
const recKinds = Object.keys(lessonsReg.step_kinds).filter((k) => lessonsReg.step_kinds[k].records !== null);
ok('every episode-backed step kind declares exactly one strength (strong, act or presence) with a reason, and no other kind does',
  JSON.stringify(Object.keys(STR.by_kind).sort()) === JSON.stringify(recKinds.slice().sort())
  && Object.keys(STR.levels).sort().join() === 'act,presence,strong'
  && Object.values(STR.by_kind).every((d) => d.strength in STR.levels && typeof d.why === 'string' && d.why.length > 20)
  && recKinds.every((k) => reg.evidence_rule[k].strength === STR.by_kind[k].strength && reg.evidence_rule[k].strength_why === STR.by_kind[k].why)
  && JSON.stringify(Object.values(STR.kinds).flat().sort()) === JSON.stringify(recKinds.slice().sort()));
ok('walk and placard are presence and never strong; sim, station and crib are strong because the page grades them; advisor, crew and walkaround are act (nothing graded)',
  STR.by_kind.walk.strength === 'presence' && STR.by_kind.placard.strength === 'presence'
  && ['sim', 'station', 'crib'].every((k) => STR.by_kind[k].strength === 'strong')
  && ['advisor', 'crew', 'walkaround'].every((k) => STR.by_kind[k].strength === 'act')
  && /trying every option/.test(STR.by_kind.station.why) && /retries/.test(STR.by_kind.crib.why) && /not a score and not a gate/.test(STR.by_kind.walkaround.why));
const stepsOf = (L) => lessonsReg.lessons[L].steps;
ok('per lesson, strong + act + presence steps sum to the lesson\'s steps and strongest / every_step_strong recompute from lessons.json',
  Object.entries(reg.lessons).every(([lid, p]) => {
    const c = { strong: 0, act: 0, presence: 0 };
    for (const st of stepsOf(lid)) c[STR.by_kind[st.kind].strength]++;
    return p.strong_steps === c.strong && p.act_steps === c.act && p.presence_steps === c.presence
      && c.strong + c.act + c.presence === p.steps
      && p.strongest === (c.strong ? 'strong' : c.act ? 'act' : 'presence')
      && p.every_step_strong === (c.strong === p.steps);
  }));
ok('the registry counts steps by strength and lessons by strongest step, recomputed from the lessons, and they sum to the recording steps and the lessons',
  reg.counts.steps_strong + reg.counts.steps_act + reg.counts.steps_presence === reg.counts.recording_steps
  && reg.counts.steps_strong === Object.values(reg.lessons).reduce((a, p) => a + p.strong_steps, 0)
  && reg.counts.lessons_with_a_strong_step === Object.values(reg.lessons).filter((p) => p.strong_steps > 0).length
  && reg.counts.lessons_every_step_strong === Object.values(reg.lessons).filter((p) => p.strong_steps === p.steps).length
  && reg.counts.lessons_with_a_strong_step + reg.counts.lessons_strongest_act + reg.counts.lessons_presence_only === reg.counts.lessons);
{
  const doneBy = (lvl) => good.lessons.filter((l) => l.complete).flatMap((l) => l.steps)
    .filter((s) => s.done && reg.evidence_rule[s.kind].strength === lvl).length;
  const sm = goodRun.summary;
  ok('the verifier summary splits the episode-backed steps by strength, the split sums to the total, and it matches a recount of the fixture',
    sm.byStrength.strong === doneBy('strong') && sm.byStrength.act === doneBy('act') && sm.byStrength.presence === doneBy('presence')
    && sm.byStrength.strong + sm.byStrength.act + sm.byStrength.presence === sm.nEpisode
    && sm.nLessonsStrong === good.lessons.filter((l) => l.complete && l.steps.some((s) => reg.evidence_rule[s.kind].strength === 'strong')).length);
  const line = VV.completionCore(Object.fromEntries(Object.entries(VV.REGISTRY_FILES).map(([k, p]) => [k, read('../' + p)]))).report(goodRun)
    .map((l) => l.text).find((t) => t.startsWith('summary:'));
  ok('the summary line a rep reads first prints the split next to the total: strong (graded), act (nothing graded) and presence, each with the kinds the registry lists, and the lessons holding a strong step',
    new RegExp(`${sm.nEpisode} episode-backed steps, of which ${sm.byStrength.strong} strong \\(graded: crib, sim, station\\), ${sm.byStrength.act} act \\(.*advisor, crew, walkaround\\) and ${sm.byStrength.presence} presence \\(.*placard, walk\\)`).test(line)
    && line.includes(`${sm.nLessonsStrong} of those lessons hold at least one strong step`));
  // the strength is REPORTED, never decided: a registry that omits it or names an unknown level stops the verifier, and a
  // reclassified kind moves only the summary split, never a rule result
  const regsOf = () => Object.fromEntries(Object.entries(VV.REGISTRY_FILES).map(([k, p]) => [k, read('../' + p)]));
  const runWith = (edit) => { const r = regsOf(); edit(r.completion); try { return { res: VV.completionCore(r).verify(good, (x) => createHash('sha256').update(Buffer.from(x, 'utf8')).digest('hex'), () => null) }; } catch (e) { return { err: e.message }; } };
  const noStrength = runWith((c) => { delete c.evidence_rule.walk.strength; });
  ok('a registry whose walk rule lost its strength stops the verifier by name (fail closed: no default strength)',
    noStrength.err !== undefined && /evidence_rule\.walk lacks "strength"/.test(noStrength.err));
  const badLevel = runWith((c) => { c.evidence_rule.walk.strength = 'strongest'; });
  ok('a registry that gives a kind an unknown strength level stops the verifier by name',
    badLevel.err !== undefined && /is not strong, act or presence/.test(badLevel.err));
  const base = runWith(() => {});
  const moved = runWith((c) => { c.evidence_rule.walk.strength = 'strong'; });
  const walkDone = good.lessons.filter((l) => l.complete).flatMap((l) => l.steps).filter((s) => s.done && s.kind === 'walk').length;
  const fails = (r) => Object.entries(r.res.tally).map(([k, t]) => k + ':' + t.fails.length).join();
  ok('reclassifying a kind changes the reported split and nothing a rule decides: the tally is identical, only byStrength moves',
    base.res !== undefined && moved.res !== undefined && fails(base) === fails(moved)
    && moved.res.summary.byStrength.strong === base.res.summary.byStrength.strong + walkDone
    && moved.res.summary.byStrength.presence === base.res.summary.byStrength.presence - walkDone && walkDone > 0);
}

const mutants = Object.entries(reg.fixture.mutants);
ok('the builder wrote at least six mutants, each naming the rule it must fail', mutants.length >= 6
  && mutants.every(([, rule]) => reg.verifier.rules.includes(rule)));
const REQUIRED = ['step.episode-evidence', 'digest', 'identity.signature', 'step.recording-evidence', 'lesson.complete-all-steps', 'ids.sim', 'ladder.prerequisite'];
ok('the on-disk signature mutants are there: a typed-in string, a wrong scheme, and a wallet attestation with no signature',
  ['fixture/mutant-forged-signature.json', 'fixture/mutant-signature-wrong-scheme.json', 'fixture/mutant-attested-by-wallet-unsigned.json']
    .every((f) => reg.fixture.mutants[f] === 'identity.signature'));
ok('the required mutations are among them, including episode-wrong-kind and episode-wrong-point',
  REQUIRED.every((r) => mutants.some(([, rule]) => rule === r))
  && ['fixture/mutant-episode-wrong-kind.json', 'fixture/mutant-episode-wrong-point.json', 'fixture/mutant-crew-done-wrong-seat.json', 'fixture/mutant-crew-done-wrong-muster.json', 'fixture/mutant-episode-t-unparseable.json'].every((f) => reg.fixture.mutants[f] === 'step.episode-evidence')
  && ['fixture/mutant-crew-done-no-seat.json', 'fixture/mutant-crew-done-no-muster.json'].every((f) => reg.fixture.mutants[f] === 'record.fields'));
ok('the walk and placard mutants are among them, each naming the rule it must fail',
  ['walk-done-wrong-room', 'walk-done-wrong-room-label', 'walk-done-as-placard', 'placard-done-dwell-too-short', 'placard-done-dwell-not-a-number', 'placard-done-wrong-hall']
    .every((n) => reg.fixture.mutants[`fixture/mutant-${n}.json`] === 'step.episode-evidence')
  && ['walk-done-no-where', 'placard-done-no-dwell'].every((n) => reg.fixture.mutants[`fixture/mutant-${n}.json`] === 'record.fields')
  && reg.fixture.mutants['fixture/mutant-placard-done-without-evidence.json'] === 'step.recording-evidence');
const trainingReg = read('../training/registry/training.json');
ok('per recording kind, checkable and not-checkable step references are read from training.json episode fields',
  reg.recording_kinds.every((k) => {
    const r = reg.evidence_rule[k], ep = trainingReg.episode_kinds[r.records].fields;
    return JSON.stringify(r.episode_fields) === JSON.stringify(ep) && r.checkable.every((f) => ep.includes(f))
      && r.not_checkable.every((f) => !ep.includes(f)) && r.checkable.includes('hall') && /never records these/.test(r.not_checkable_why);
  }));
const STEP_META = new Set(['n', 'kind', 'records', 'stage', 'reads', 'note', 'do', 'names_read', 'where', 'label_kind']);
ok('evidenceable per recording kind recomputes from lessons.json step references and training.json episode fields',
  reg.recording_kinds.every((k) => {
    const refs = new Set(['hall']);
    for (const L of Object.values(lessonsReg.lessons)) for (const st of L.steps) if (st.kind === k) for (const f of Object.keys(st)) if (!STEP_META.has(f)) refs.add(f);
    const ep = trainingReg.episode_kinds[lessonsReg.step_kinds[k].records].fields;
    return [...refs].every((f) => ep.includes(f)) === reg.evidence_rule[k].evidenceable;
  }) && ['advisor', 'walkaround', 'sim', 'crew'].every((k) => reg.evidence_rule[k].evidenceable === true));
ok('a crew step is evidenceable and held to seat and muster: both are fields of the crew episode, both are checkable, none is not-checkable',
  trainingReg.episode_kinds.crew.fields.includes('seat') && trainingReg.episode_kinds.crew.fields.includes('muster')
  && reg.evidence_rule.crew.checkable.includes('seat') && reg.evidence_rule.crew.checkable.includes('muster')
  && reg.evidence_rule.crew.not_checkable.length === 0
  && reg.evidence_rule.crew.evidence_shape.seat && reg.evidence_rule.crew.evidence_shape.muster
  && Object.values(lessonsReg.lessons).flatMap((L) => L.steps).filter((s) => s.kind === 'crew')
    .every((s) => reg.evidence_rule.crew.checkable.every((f) => f === 'hall' || f in s)));
ok('every lesson is completable now and none is blocked: the count is derived from the evidence rule, and no step kind is non-evidenceable',
  reg.counts.lessons_completable === reg.counts.lessons && reg.counts.lessons_not_completable === 0
  && Object.values(reg.lessons).every((p) => p.completable && p.not_completable_why === null)
  && reg.recording_kinds.every((k) => reg.evidence_rule[k].evidenceable === true));
ok('the fixture has a crew step done with an episode carrying the step\'s own crew, role, topic, answer_kind, seat and muster',
  good.lessons.some((l) => l.complete && l.steps.some((s) => {
    const st = lessonsReg.lessons[l.lesson].steps.find((k) => k.n === s.step);
    return s.kind === 'crew' && s.done && s.evidence.episode === 'crew' && s.evidence.hall === l.hall
      && ['crew', 'role', 'topic', 'answer_kind', 'seat', 'muster'].every((f) => st[f] !== undefined && s.evidence[f] === st[f]);
  })));
ok('a lesson is completable exactly when none of its steps is of a non-evidenceable kind, and the count is derived',
  Object.entries(reg.lessons).every(([lid, p]) => p.completable
    === lessonsReg.lessons[lid].steps.every((st) => reg.evidence_rule[st.kind].class !== 'episode-backed' || reg.evidence_rule[st.kind].evidenceable))
  && reg.counts.lessons_completable + reg.counts.lessons_not_completable === reg.counts.lessons
  && reg.counts.lessons_not_completable === Object.values(reg.lessons).filter((p) => !p.completable).length);
ok('the fixture completes only completable lessons',
  good.lessons.filter((l) => l.complete).every((l) => reg.lessons[l.lesson].completable));
ok('the fixture has a walkaround step done with a matching episode (kind, ISO-8601 t, hall, sim, point)',
  good.lessons.some((l) => l.steps.some((s) => s.kind === 'walkaround' && s.done && s.evidence.episode === 'walkaround'
    && typeof s.evidence.t === 'string' && Number.isFinite(Date.parse(s.evidence.t)) && s.evidence.hall === l.hall
    && s.evidence.point === lessonsReg.lessons[l.lesson].steps.find((k) => k.n === s.step).point)));
ok('the fixture completes a lesson with a walk step and a lesson with a placard step, each done with its episode: where, room from names_read, and for a placard a dwell at the floor or above',
  ['walk', 'placard'].every((k) => good.lessons.some((l) => l.complete && l.steps.some((s) => {
    const st = lessonsReg.lessons[l.lesson].steps.find((q) => q.n === s.step);
    return s.kind === k && s.done && s.evidence.episode === k && s.evidence.hall === l.hall && s.evidence.where === st.where
      && st.names_read.includes(s.evidence.room) && (k === 'walk' || s.evidence.dwell_ms >= reg.evidence_rule.placard.at_least.dwell_ms);
  }))));
ok('the fixture completes a lesson with a station step and a lesson with a crib step, each done with its episode: where, id, the name from names_read, and for a crib every pick right',
  ['station', 'crib'].every((k) => good.lessons.some((l) => l.complete && l.steps.some((s) => {
    const st = lessonsReg.lessons[l.lesson].steps.find((q) => q.n === s.step);
    return s.kind === k && s.done && s.evidence.episode === k && s.evidence.hall === l.hall && s.evidence.where === st.where && s.evidence[k] === st[k]
      && st.names_read.includes(s.evidence[k + '_name']) && (k === 'station' || s.evidence.picks >= reg.evidence_rule.crib.at_least.picks);
  }))));
for (const [file, rule] of mutants) {
  const m = read('./' + file);
  let failedRules;
  try { const r = verify(m); failedRules = Object.entries(r.tally).filter(([, t]) => t.fails.length).map(([k]) => k); }
  catch (e) { failedRules = ['record.fields']; }
  ok(`mutant ${file.replace('fixture/mutant-', '').replace('.json', '')} fails by ${rule} and by nothing else`,
    failedRules.length === 1 && failedRules[0] === rule);
}

// ---- the signed fixture: built here with a throwaway key, never on disk ----
{
  const key = throwawayKey(), other = throwawayKey();
  ok('a throwaway secp256k1 key from node:crypto yields a checksummed address through the page\'s own curve and keccak',
    /^0x[0-9a-fA-F]{40}$/.test(key.address) && key.address !== other.address);
  const signed = signRecord(good, key);
  const run = verify(signed);
  const failing = Object.entries(run.tally).filter(([, t]) => t.fails.length).map(([k]) => k);
  ok('the fixture re-attested to the wallet and signed over its digest verifies on every rule, the digest still recomputes '
    + 'with the signature outside it, and the verifier prints the recovered address (a key, not a person; no chain)',
    failing.length === 0 && digestOf(signed) === signed.digest.hex && run.signature.state === 'signed'
    && run.signature.recovered === key.address && signed.identity.claimed === key.address
    && signed.identity.attested_by === SIGNED_ATTESTATION && run.signature.line.includes(key.address)
    && /identity of a key, not of a person/.test(run.signature.line) && /nothing is on any chain/.test(run.signature.line));
  ok('the signed message is the structure the registry states: statement, digest line, exported_at line, nothing else',
    signed.identity.signature.message === reg.signature.message.statement + '\ndigest: ' + signed.digest.hex + '\nexported_at: ' + signed.exported_at
    && signed.identity.signature.message.split('\n').length === 3);
  ok('the good fixture, unsigned, is reported "unsigned: this device only"',
    verify(good).signature.state === 'unsigned' && verify(good).signature.line === 'unsigned: this device only');
  const failsBy = (m) => { try { const r = verify(m); return Object.entries(r.tally).filter(([, t]) => t.fails.length).map(([k]) => k); } catch (e) { return ['record.fields']; } };
  const tamperSig = (h) => { const u = Buffer.from(h.slice(2), 'hex'); u[40] ^= 0x01; return '0x' + u.toString('hex'); };
  const mutants = {
    'signed-sig-tampered': (() => { const m = JSON.parse(JSON.stringify(signed)); m.identity.signature.sig = tamperSig(m.identity.signature.sig); return m; })(),
    'signed-message-tampered': (() => { const m = JSON.parse(JSON.stringify(signed)); m.identity.signature.message = m.identity.signature.message.replace('digest: ', 'digest:  '); return m; })(),
    'signed-address-swapped': (() => { const m = JSON.parse(JSON.stringify(signed)); m.identity.claimed = other.address; m.identity.signature.address = other.address; m.digest.hex = digestOf(m); m.identity.signature.message = signatureMessage(m.digest.hex, m.exported_at); return m; })(),
    'signed-wrong-scheme': (() => { const m = JSON.parse(JSON.stringify(signed)); m.identity.signature.scheme = 'eip712-typed-data'; return m; })(),
    /* a valid signature by the key named in signature.address, under a DIFFERENT identity.claimed */
    'signed-claimed-not-the-signer': (() => { const m = JSON.parse(JSON.stringify(signed)); m.identity.claimed = other.address; m.digest.hex = digestOf(m); m.identity.signature.message = signatureMessage(m.digest.hex, m.exported_at); m.identity.signature.sig = signPersonal(key.d, m.identity.signature.message); return m; })(),
  };
  for (const [name, m] of Object.entries(mutants)) {
    const f = failsBy(m);
    ok(`signed mutant ${name} fails by ${reg.fixture.signed.mutants[name]} and by nothing else`,
      f.length === 1 && f[0] === reg.fixture.signed.mutants[name]);
  }
  ok('a signature by another key over the same message recovers to a different address and is refused',
    (() => { const m = JSON.parse(JSON.stringify(signed)); m.identity.signature.sig = signPersonal(other.d, m.identity.signature.message); const r = verify(m); return failsBy(m).join() === 'identity.signature' && r.signature.recovered === other.address; })());
  ok('EIP-55 casing is not a mismatch: the same signature with the address and claimed lowercased still verifies',
    (() => { const m = JSON.parse(JSON.stringify(signed)); m.identity.signature.address = m.identity.signature.address.toLowerCase(); m.identity.claimed = m.identity.claimed.toLowerCase(); m.digest.hex = digestOf(m); m.identity.signature.message = signatureMessage(m.digest.hex, m.exported_at); m.identity.signature.sig = signPersonal(key.d, m.identity.signature.message); return failsBy(m).length === 0; })());
  {
    const m = JSON.parse(JSON.stringify(signed)); m.digest.hex = '0'.repeat(64);
    const f = failsBy(m);
    ok('a tampered digest under a valid signature fails digest FIRST, and the signature no longer names this record',
      f[0] === 'digest' && f.includes('identity.signature') && f.length === 2);
  }
  ok('the signed mutants the registry lists are the ones driven here', Object.keys(reg.fixture.signed.mutants).sort().join()
    === [...Object.keys(mutants), 'signed-digest-tampered'].sort().join() && /throwaway/.test(reg.fixture.signed.why_not_on_disk)
    && /ONLY in the test/.test(reg.fixture.signed.why_not_on_disk));
  /* the CLI, on a temp file: what a union clerk would actually run */
  const dir = mkdtempSync(join(tmpdir(), 'tc-completion-signed-'));
  try {
    const sp = join(dir, 'signed.json'); writeFileSync(sp, JSON.stringify(signed, null, 1));
    const cli = spawnSync(process.execPath, [fileURLToPath(url('./verify.mjs')), sp], { encoding: 'utf8' });
    const bp = join(dir, 'signed-bad-sig.json'); writeFileSync(bp, JSON.stringify(mutants['signed-sig-tampered'], null, 1));
    const bad = spawnSync(process.execPath, [fileURLToPath(url('./verify.mjs')), bp], { encoding: 'utf8' });
    ok('node completion/verify.mjs on the signed record exits 0, prints "signature: signed: eip191-personal_sign by <recovered address>" '
      + 'and ends with the no-chain, no-accreditation line; on the sig-tampered copy it exits 1 with FAIL identity.signature',
      cli.status === 0 && cli.stdout.includes('signature: signed: eip191-personal_sign by ' + key.address)
      && /nothing is written to any chain/.test(cli.stdout) && /no accreditation/.test(cli.stdout)
      && bad.status === 1 && /^FAIL identity\.signature/m.test(bad.stderr) && !/^FAIL digest/m.test(bad.stderr));
  } finally { rmSync(dir, { recursive: true, force: true }); }
}

// no typed learner counts, no defaults
ok('no learner count is typed: every count in the registry is derived from the registries it reads',
  reg.counts.lessons === Object.keys(lessonsReg.lessons).length && reg.counts.sims === Object.keys(simsReg.sims).length
  && reg.counts.ladder_edges === lessonsReg.ladder.edges.length && reg.counts.fixture_mutants === mutants.length);
ok('the registry counts episode-backed steps as exactly lessons.json\'s recording steps',
  reg.counts.episode_backed_steps === lessonsReg.counts.recording_steps
  && reg.counts.episode_backed_steps + reg.counts.device_mark_steps + reg.counts.self_reported_steps
    === lessonsReg.counts.recording_steps + lessonsReg.counts.silent_steps);
ok('the verifier, the builder and the recovery loader take no defaults: no ?? and no .get(k, default)',
  !/\?\?/.test(verifySrc) && !/\?\?/.test(buildSrc) && !/\.get\([^)]*,/.test(buildSrc)
  && !/\?\?/.test(readFileSync(url('../auth/recover.mjs'), 'utf8')));
ok('the verifier fails closed through need()', typeof need === 'function' && (verifySrc.match(/need\(/g) || []).length > 30);
let threw = false;
try { need({}, 'x', 'probe'); } catch (e) { threw = /probe lacks "x"/.test(e.message); }
ok('need() names the field it could not find', threw);


/* ---- one core, two shells: the rules the verify page carries ---- */
{
  const V = await import('./verify.mjs');
  const { webcrypto } = await import('node:crypto');
  const { recoverAddress } = await import('../auth/recover.mjs');
  const src = readFileSync(url('./verify.mjs'), 'utf8');
  const a = src.indexOf('/* COMPLETION_CORE:BEGIN'), b = src.indexOf('/* COMPLETION_CORE:END */');
  const block = a >= 0 && b > a ? src.slice(a, b) : '';
  const pure = block.includes('function completionCore(regs) {') && !/\bfetch\b|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|indexedDB|readFileSync|createHash|\bimport\s*\(|^\s*(import|export)\b|\?\?/m.test(block);
  const regs = Object.fromEntries(Object.entries(V.REGISTRY_FILES).map(([k, p]) => [k, JSON.parse(readFileSync(url('../' + p), 'utf8'))]));
  const core = V.completionCore(regs);
  const failsOf = async (rec, useAsync) => {
    try {
      const r = useAsync ? await core.verifyAsync(rec, webcrypto.subtle, recoverAddress) : V.verify(rec);
      return Object.keys(r.tally).filter((k) => r.tally[k].fails.length).join();
    } catch (e) { return 'threw: ' + e.message; }
  };
  const inputs = ['fixture/good.json', ...mutants.map(([f]) => f)];
  const diverge = [];
  for (const f of inputs) { const rec = read('./' + f); const s = await failsOf(rec, false), x = await failsOf(rec, true); if (s !== x) diverge.push(f + ': ' + s + ' vs ' + x); }
  ok('the rules live in one pure core between the COMPLETION_CORE markers (no file, network, storage, module statement or ??) that web/build_verify.py carries into the verify page, '
    + 'and its verifyAsync over webcrypto.subtle - the browser path - fails the fixture and every mutant exactly as verify() does (' + inputs.length + ' files)',
    pure && diverge.length === 0 && core.LAST_LINE === V.LAST_LINE, diverge);
}

console.log(`completion/test: ${n} checks passed — ${reg.counts.lessons} lessons documented, `
  + `${reg.counts.recording_steps} recording / ${reg.counts.silent_steps} silent steps, `
  + `${mutants.length} mutants each failing by name, ${Object.keys(reg.fixture.signed.mutants).length} signed mutants driven in memory`);
}
