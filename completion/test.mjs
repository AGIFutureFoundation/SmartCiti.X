/**
 * Completion pack verification.
 *
 * The claim is small: the registry documents the record contract and is
 * derived from the registries it names; the verifier passes the scripted
 * fixture and fails every mutant by the rule the builder said it breaks; no
 * learner count is typed; and no default is ever taken (`??` is forbidden in
 * the verifier and the builder, spec §23.1).
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { verify, digestOf, need } from './verify.mjs';

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
ok('the honesty block says signature is null because there is no signing key and no server',
  /no signing key and no server/.test(reg.honesty.signature) && /forgery/.test(reg.honesty.signature));
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
ok('station and crib are device-mark, walk and placard self-reported, and neither is called evidence-backed',
  reg.evidence_rule.station.class === 'device-mark' && reg.evidence_rule.crib.class === 'device-mark'
  && reg.evidence_rule.walk.class === 'self-reported' && reg.evidence_rule.placard.class === 'self-reported'
  && /not a recorded episode/.test(reg.evidence_classes['device-mark'])
  && /only this class is called evidence-backed/.test(reg.evidence_classes['episode-backed']));
ok('honesty says a station or crib mark is a device-local mark, not a recorded episode',
  reg.honesty.does_not_prove.includes('a station or crib mark is a device-local mark, not a recorded episode'));
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

const mutants = Object.entries(reg.fixture.mutants);
ok('the builder wrote at least six mutants, each naming the rule it must fail', mutants.length >= 6
  && mutants.every(([, rule]) => reg.verifier.rules.includes(rule)));
const REQUIRED = ['step.episode-evidence', 'digest', 'identity.signature', 'step.recording-evidence', 'lesson.complete-all-steps', 'ids.sim', 'ladder.prerequisite'];
ok('the required mutations are among them, including episode-wrong-kind and episode-wrong-point',
  REQUIRED.every((r) => mutants.some(([, rule]) => rule === r))
  && ['fixture/mutant-episode-wrong-kind.json', 'fixture/mutant-episode-wrong-point.json', 'fixture/mutant-crew-done-unrecordable.json', 'fixture/mutant-episode-t-unparseable.json'].every((f) => reg.fixture.mutants[f] === 'step.episode-evidence'));
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
  }) && reg.evidence_rule.crew.evidenceable === false && /no muster and no seat|no seat and no muster/.test(reg.evidence_rule.crew.evidenceable_why)
  && ['advisor', 'walkaround', 'sim'].every((k) => reg.evidence_rule[k].evidenceable === true));
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
for (const [file, rule] of mutants) {
  const m = read('./' + file);
  let failedRules;
  try { const r = verify(m); failedRules = Object.entries(r.tally).filter(([, t]) => t.fails.length).map(([k]) => k); }
  catch (e) { failedRules = ['record.fields']; }
  ok(`mutant ${file.replace('fixture/mutant-', '').replace('.json', '')} fails by ${rule} and by nothing else`,
    failedRules.length === 1 && failedRules[0] === rule);
}

// no typed learner counts, no defaults
ok('no learner count is typed: every count in the registry is derived from the registries it reads',
  reg.counts.lessons === Object.keys(lessonsReg.lessons).length && reg.counts.sims === Object.keys(simsReg.sims).length
  && reg.counts.ladder_edges === lessonsReg.ladder.edges.length && reg.counts.fixture_mutants === mutants.length);
ok('the registry counts episode-backed steps as exactly lessons.json\'s recording steps',
  reg.counts.episode_backed_steps === lessonsReg.counts.recording_steps
  && reg.counts.episode_backed_steps + reg.counts.device_mark_steps + reg.counts.self_reported_steps
    === lessonsReg.counts.recording_steps + lessonsReg.counts.silent_steps);
ok('the verifier and the builder take no defaults: no ?? and no .get(k, default)',
  !/\?\?/.test(verifySrc) && !/\?\?/.test(buildSrc) && !/\.get\([^)]*,/.test(buildSrc));
ok('the verifier fails closed through need()', typeof need === 'function' && (verifySrc.match(/need\(/g) || []).length > 30);
let threw = false;
try { need({}, 'x', 'probe'); } catch (e) { threw = /probe lacks "x"/.test(e.message); }
ok('need() names the field it could not find', threw);

console.log(`completion/test: ${n} checks passed — ${reg.counts.lessons} lessons documented, `
  + `${reg.counts.recording_steps} recording / ${reg.counts.silent_steps} silent steps, `
  + `${mutants.length} mutants each failing by name`);
