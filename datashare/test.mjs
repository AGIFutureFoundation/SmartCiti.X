/**
 * datashare/test.mjs - the data commons, checked. Network-free (globalThis.fetch is a trap), R2 is a mock.
 * Prints `  ok ` per check and FAIL at column 0; exits 1 on any failure.
 *
 *   node datashare/test.mjs
 */
import { createHash, webcrypto } from 'node:crypto';
import { readFileSync, mkdtempSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

let pass = 0, fail = 0;
const ok = (c, m, ev) => { if (c) { pass++; console.log('  ok ' + m); } else { fail++; console.log('FAIL ' + m); if (ev) console.log('     ' + JSON.stringify(ev).slice(0, 400)); } };
let netCalls = 0;
globalThis.fetch = async () => { netCalls++; throw new Error('network is forbidden in datashare/test.mjs'); };
const P = (p) => fileURLToPath(new URL('../' + p, import.meta.url));
const R = (p) => readFileSync(P(p), 'utf8');
const J = (p) => JSON.parse(R(p));
console.log('datashare/test.mjs');

const CFG = J('datashare/registry/datashare.json');
const CONTRIB = J('contrib/registry/contrib.json');
const ROBOTICS = J('robotics/registry/robotics.json');
const TRAINING = J('training/registry/training.json');
const { CORE, verdictOf, sha256hex } = await import('./node_shell.mjs');
const { digestOf } = await import('../contrib/verify.mjs');

/* ---------------------------------------------------------------- registry */
ok(CFG.source_stamp === createHash('sha256').update(readFileSync(P('datashare/build.py'))).digest('hex').slice(0, 16), 'registry: built from the current datashare/build.py (stamp)');
ok(CFG.dataset_tag === 'tc-dataset/1' && JSON.stringify(CFG.accepts.package_tags) === JSON.stringify([CONTRIB.record_tag, CONTRIB.record_tag_current])
  && CFG.accepts.intake_tag === 'tc-contribution/2' && CFG.accepts.contrib_source_stamp === CONTRIB.source_stamp
  && CFG.accepts.robotics_schema === ROBOTICS.schema, 'registry: dataset tag tc-dataset/1; package tags, contrib stamp and robotics schema read from their registries');
ok(JSON.stringify(CFG.privacy) === JSON.stringify(CONTRIB.privacy) && CFG.licence.dataset_licence === CONTRIB.consent.license.spdx
  && JSON.stringify(CFG.licence.compatible) === JSON.stringify([CONTRIB.consent.license.spdx])
  && JSON.stringify(CFG.consent_scope.scopes) === JSON.stringify(Object.keys(CONTRIB.consent.scopes).sort()),
  'registry: privacy rule, licence and scopes are contrib.json\'s, verbatim');
const robokit = Object.keys(ROBOTICS.envs).filter((e) => ROBOTICS.envs[e].runner === 'robokit').sort();
ok(JSON.stringify(Object.keys(CFG.envs).sort()) === JSON.stringify(robokit) && robokit.every((e) => {
  const o = Object.fromEntries(ROBOTICS.envs[e].observation.map((x) => [x.name, [x.low, x.high]]));
  const E = CFG.envs[e];
  return JSON.stringify(E.vel) === JSON.stringify([o.v, o.w]) && JSON.stringify(E.pose.slice(0, 3)) === JSON.stringify([o.pose_e, o.pose_n, o.yaw])
    && JSON.stringify(E.a) === JSON.stringify(ROBOTICS.envs[e].action.fields.map((a) => [a.low, a.high])) && JSON.stringify(E.seeds) === JSON.stringify(ROBOTICS.envs[e].seeds);
}), 'registry: per-env ranges (pose, velocity, action) and seeds are robotics.json\'s, read not typed');
ok(JSON.stringify(CFG.sim_seat_envs) === JSON.stringify(Object.keys(ROBOTICS.envs).filter((e) => ROBOTICS.envs[e].runner === 'sim-seat').sort()),
  'registry: the sim-seat envs a coverage report lists are robotics.json\'s');
ok(CFG.honesty.trained === ROBOTICS.honesty.trained && /NOTHING HAS BEEN TRAINED/.test(CFG.honesty.trained) && CFG.counts.trained_models === 0
  && CFG.honesty.no_agent_trained === TRAINING.export_format.no_agent_trained, 'honesty: nothing trained, in robotics.json\'s and training.json\'s own words');
{
  const txt = JSON.stringify(CFG);
  const claims = [...txt.matchAll(/[^.]*\b(RLDS|LeRobot|ML-Agents)\b[^.]*/g)].map((m) => m[0]);
  ok(claims.length > 0 && claims.every((c) => /no (compatibility|round-trip)|not an|shaped after|no external format/i.test(c)),
    'honesty: RLDS / LeRobot / ML-Agents are named only to say no compatibility is claimed (no round-trip test)', claims.filter((c) => !/no (compatibility|round-trip)|not an|shaped after/i.test(c)));
}
{
  const bad = CFG.best_practices.filter((b) => !existsSync(P(b.enforced_by.file)) || !R(b.enforced_by.file).includes(b.enforced_by.marker));
  ok(CFG.best_practices.length >= 12 && bad.length === 0, 'best practices: every practice names a file and code marker that exists in it - nothing listed that the code does not enforce', bad.map((b) => b.practice));
  const need = ['schema versioning', 'integrity digests', 'dedupe by digest', 'deterministic split by hashed id', 'provenance per episode', 'consent scope',
    'licence compatibility', 'revocation honoured', 'no personal data', 'dataset card'];
  ok(need.every((n) => CFG.best_practices.some((b) => b.practice === n)), 'best practices: versioning, digests, dedupe, split, provenance, consent, licence, revocation, privacy and card are each listed');
}
ok(JSON.stringify(CFG.card.template.map((s) => s.id)) === JSON.stringify(['motivation', 'composition', 'collection', 'preprocessing', 'uses', 'distribution', 'maintenance']),
  'card: datasheet-style sections motivation, composition, collection, preprocessing, uses, distribution, maintenance');
ok(CFG.intake.deployed === false && CFG.intake.flag_env === 'DATASHARE_INTAKE' && /OFF by default/.test(CFG.intake.status) && CFG.intake.accepts === 'tc-contribution/2',
  'intake: declared not deployed, off by default behind DATASHARE_INTAKE, /2 only');
ok(['core.mjs', 'build_dataset.mjs', 'analyse.mjs', 'intake.mjs', 'node_shell.mjs'].every((f) => !/\?\?/.test(R('datashare/' + f))) && !/\.get\([^)]*,/.test(R('datashare/build.py')),
  'fail closed: no `??` in the datashare modules and no `.get(k, default)` in the builder');

/* ------------------------------------------------------ core: ids and splits */
const ep = J('contrib/fixture/v2/good.json').dataset.episodes[0];
const id1 = await CORE.episodeId(ep), id2 = await CORE.episodeId(JSON.parse(JSON.stringify(ep)));
ok(/^[0-9a-f]{64}$/.test(id1) && id1 === id2 && id1 === createHash('sha256').update(CORE.canonical(ep)).digest('hex'), 'episode id: SHA-256 of the canonical episode, same bytes same id');
{
  const counts = { train: 0, val: 0, test: 0 };
  for (let i = 0; i < 2000; i++) counts[await CORE.splitOf(createHash('sha256').update('x' + i).digest('hex'))]++;
  const again = await CORE.splitOf(id1) === await CORE.splitOf(id1);
  ok(again && counts.train > 1500 && counts.train < 1700 && counts.val > 140 && counts.val < 260 && counts.test > 140 && counts.test < 260,
    'split: deterministic per id and near 80/10/10 over 2000 ids (' + JSON.stringify(counts) + ')');
}

/* --------------------------------------------------- build_dataset CLI + core */
const tmp = mkdtempSync(join(tmpdir(), 'datashare-'));
const cli = (args) => spawnSync(process.execPath, [P('datashare/build_dataset.mjs'), ...args], { encoding: 'utf8' });
const FIX = ['contrib/fixture/good.json', 'contrib/fixture/v2/good.json', 'contrib/fixture/v2/mutant-classroom-mode.json', 'contrib/fixture/v2/mutant-email-in-gauges.json',
  'contrib/fixture/mutant-wrong-license.json', 'datashare/fixture/v1-email.json', 'datashare/fixture/v2-agent-only.json', 'datashare/fixture/v2-reexport.json'].map(P);
const run1 = cli(['--scope', 'robot-training', '--built-at', '2026-09-29T00:00:00Z', '--out', join(tmp, 'a'), ...FIX]);
const M = JSON.parse(readFileSync(join(tmp, 'a', 'manifest.json'), 'utf8'));
const refusedAs = (f) => { const r = M.refused.find((x) => x.package === f); return r ? r.reason : null; };
ok(run1.status === 0 && /3 package\(s\) admitted, 5 refused/.test(run1.stdout), 'build_dataset: 8 packages in, 3 admitted, 5 refused, exit 0 without --strict', run1.stdout + run1.stderr);
ok(refusedAs('mutant-classroom-mode.json') === 'verifier' && /origin\.classroom/.test(M.refused.find((x) => x.package === 'mutant-classroom-mode.json').detail)
  && /^REFUSED mutant-classroom-mode\.json: verifier - contrib\/verify\.mjs fails origin\.classroom/m.test(run1.stderr),
  'refused by name: a classroom-mode package (the verifier\'s origin.classroom, printed REFUSED <file>)');
ok(refusedAs('mutant-email-in-gauges.json') === 'verifier' && refusedAs('mutant-wrong-license.json') === 'verifier',
  'refused by name: any package the verifier rejects (privacy in /2, a foreign licence)');
ok(refusedAs('v1-email.json') === 'privacy' && verdictOf(J('datashare/fixture/v1-email.json')).ok === true,
  'refused by name: a /1 package the /1 verifier passes but that carries an email field (the dataset privacy scan)');
ok(refusedAs('v2-agent-only.json') === 'consent-scope', 'refused by name: a package whose consent scope does not include the dataset scope');
ok(M.packages.map((p) => p.record).sort().join() === 'tc-contribution/1,tc-contribution/2,tc-contribution/2' && M.refused.length === 5,
  'admitted: the /1 fixture (old packages still build) and two /2 packages');
ok(M.excluded.duplicate_episodes >= J('datashare/fixture/v2-reexport.json').dataset.episodes.length
  && M.packages.find((p) => p.digest === J('datashare/fixture/v2-reexport.json').digest.hex).admitted_episodes === 0
  && M.episodes.some((e) => e.also_in.includes(J('datashare/fixture/v2-reexport.json').digest.hex)),
  'dedupe: a re-exported package adds no episode; each duplicate is recorded against the episode it repeats');
ok(M.episodes.every((e) => /^[0-9a-f]{64}$/.test(e.id) && M.packages.some((p) => p.digest === e.provenance.package) && Number.isInteger(e.provenance.index)
  && typeof e.provenance.t === 'string' && ['train', 'val', 'test'].includes(e.split)) && M.splits.train + M.splits.val + M.splits.test === M.episodes.length,
  'provenance: every episode names its id, split, source package digest, index and time; splits add up');
ok(M.packages.every((p) => /^unsigned package [0-9a-f]{16}$|^wallet 0x/.test(p.attribution)) && !JSON.stringify(M).includes('fixture - not a learner'),
  'attribution: by package digest or wallet; contributor.claimed labels are never copied into a dataset');
ok(M.digest.hex === await CORE.digestOf(M) && M.schema_versions.package_tags.join() === 'tc-contribution/1,tc-contribution/2'
  && JSON.stringify(M.schema_versions.world_kind_versions) === JSON.stringify({ 'world-teleop': TRAINING.world_episode_kinds['world-teleop'].v }),
  'manifest: digest recomputes; schema versions name the package tags admitted and the world kind version');
{
  const lines = ['train', 'val', 'test'].flatMap((s) => readFileSync(join(tmp, 'a', s + '.jsonl'), 'utf8').split('\n').filter(Boolean).map((l) => ({ s, r: JSON.parse(l) })));
  ok(lines.length === M.episodes.length && lines.every(({ s, r }) => M.episodes.find((e) => e.id === r.id).split === s), 'split files: every episode is in the file of its split, once');
  const run2 = cli(['--scope', 'robot-training', '--built-at', '2026-09-29T00:00:00Z', '--out', join(tmp, 'b'), ...[...FIX].reverse()]);
  ok(run2.status === 0 && readFileSync(join(tmp, 'b', 'manifest.json'), 'utf8') === readFileSync(join(tmp, 'a', 'manifest.json'), 'utf8'),
    'deterministic: the same packages in another order build the same manifest bytes');
  const card = readFileSync(join(tmp, 'a', 'DATASET_CARD.md'), 'utf8');
  ok(CFG.card.template.every((s) => card.includes('## ' + s.title)) && !card.includes('{{') && card.includes(M.digest.hex) && card.includes(CFG.honesty.trained),
    'card: written with the dataset, every section present, every slot filled, naming the manifest digest and that nothing was trained');
}
{
  const run3 = cli(['--scope', 'robot-training', '--built-at', '2026-09-29T00:00:00Z', '--out', join(tmp, 'c'), '--revocations', P('datashare/fixture/revocations.json'), '--strict', ...FIX]);
  const M3 = JSON.parse(readFileSync(join(tmp, 'c', 'manifest.json'), 'utf8'));
  const rev = CFG.fixture_revocations.revokes_episode;
  ok(run3.status === 1 && M3.refused.find((x) => x.package === 'v1-email.json').reason === 'revoked' && M3.excluded.revoked_episodes >= 1
    && !M3.episodes.some((e) => e.id === rev), 'revocation: a revoked package is refused by name, a revoked episode id is excluded, and --strict exits 1 on any refusal');
  const run4 = cli(['--scope', 'robot-training', '--out', join(tmp, 'd'), ...FIX]);
  ok(run4.status === 1 && /FAIL build_dataset: --built-at is required/.test(run4.stderr), 'no clock is read: --built-at is required');
}
{
  const g2 = J('contrib/fixture/v2/good.json');
  const r = await CORE.buildDataset({ packages: [{ name: 'forced.json', record: { ...g2, consent: { ...g2.consent, license: 'CC0-1.0' } }, verdict: { ok: true, rule: null, detail: '' } }],
    scope: 'robot-training', built_at: '2026-09-29T00:00:00Z', revocations: { record: 'tc-revocations/1', packages: [], episodes: [] } });
  ok(r.manifest.refused.length === 1 && r.manifest.refused[0].reason === 'licence', 'licence: even a package handed in as verified is refused by name under a licence other than the dataset\'s');
  let threw = '';
  try { await CORE.buildDataset({ packages: [], scope: 'marketing', built_at: '2026-09-29T00:00:00Z', revocations: { record: 'tc-revocations/1', packages: [], episodes: [] } }); } catch (e) { threw = e.message; }
  ok(/scope "marketing" is not one contrib\.json declares/.test(threw), 'scope: a dataset can only be built for a scope contrib.json declares');
}

/* ------------------------------------------------------------------ analyse */
{
  const { itemsFrom, report } = await import('./analyse.mjs');
  const A = CORE.analyse(itemsFrom([join(tmp, 'a')]));
  ok(A.episodes === M.episodes.length && A.by_kind['world-teleop'] >= 1 && Object.values(A.by_where).every((v) => v.rate === null || (v.rate >= 0 && v.rate <= 1)),
    'analyse: counts per kind and per env/seat, success rates in [0, 1]');
  ok(A.gaps.some((g) => g.gap === 'no episodes') && A.gaps.some((g) => /^seeds with no episode/.test(g.gap)) && A.range[Object.keys(A.range)[0]].checked > 0,
    'analyse: coverage gaps (envs and seats with no episode, seeds never run) and range checks over every world sample');
  const w = JSON.parse(JSON.stringify(J('contrib/fixture/v2/good.json').dataset.episodes.find((e) => e.kind === 'world-teleop')));
  w.samples[0].pose[0] = 999; w.samples[0].vel[0] = 50;
  const miss = JSON.parse(JSON.stringify(w)); delete miss.outcome;
  const five = [0, 1, 2, 3, 4, 5].map((i) => { const x = JSON.parse(JSON.stringify(J('contrib/fixture/v2/good.json').dataset.episodes.find((e) => e.kind === 'world-teleop'))); x.outcome.return = i === 5 ? 500 : i * 0.1; x.seed = i; return { episode: x }; });
  const B = CORE.analyse([{ episode: w }, { episode: miss }, ...five]);
  ok(B.flags.some((f) => f.flag === 'range' && /pose_e 2/.test(f.detail) && /v 2/.test(f.detail)), 'analyse: a pose or velocity outside the env ranges is flagged by field', B.flags);
  ok(B.flags.some((f) => f.flag === 'missing' && /outcome/.test(f.detail)), 'analyse: a missing field is flagged by name');
  ok(B.flags.some((f) => f.flag === 'outlier' && /^return 500/.test(f.detail)) && B.flags.filter((f) => f.flag === 'outlier').length === 1, 'analyse: a return far from the env median is flagged by the robust-z rule, and only it');
  ok(CORE.analyse([{ episode: w }]).outlier_notes.some((n) => /fewer than 5 - outlier rule skipped/.test(n)), 'analyse: with fewer than 5 episodes the outlier rule says it was skipped');
  const out = spawnSync(process.execPath, [P('datashare/analyse.mjs'), join(tmp, 'a')], { encoding: 'utf8' });
  ok(out.status === 0 && /^gap world\./m.test(out.stdout) && report(A).length > 5, 'analyse CLI: prints the table, flags and gaps, exit 0');
}
rmSync(tmp, { recursive: true, force: true });

/* ---------------------------------------------------- intake core carried */
{
  const core = R('datashare/intake_core.mjs'), vsrc = R('contrib/verify.mjs'), signin = R('web/trade_craft_signin.html');
  const block = vsrc.slice(vsrc.indexOf('/* CONTRIB_CORE:BEGIN'), vsrc.indexOf('/* CONTRIB_CORE:END */') + '/* CONTRIB_CORE:END */'.length);
  const auth = signin.slice(signin.indexOf('/* AUTH-CORE:BEGIN'), signin.indexOf('/* AUTH-CORE:END */'));
  ok(block.length > 1000 && core.includes(block), 'intake core: carries contrib/verify.mjs\'s CONTRIB_CORE block byte-for-byte');
  ok(auth.length > 1000 && core.includes(auth), 'intake core: carries the sign-in page\'s AUTH-CORE recovery byte-for-byte (no second copy of the crypto)');
  const IC = await import('./intake_core.mjs');
  const { REGISTRY_FILES } = await import('../contrib/verify.mjs');
  ok(JSON.stringify(IC.REGISTRY_FILES) === JSON.stringify(REGISTRY_FILES) && Object.entries(REGISTRY_FILES).every(([k, rel]) => JSON.stringify(IC.REGISTRIES[k]) === JSON.stringify(J(rel))),
    'intake core: every registry it carries is its file verbatim');
  ok(!/readFileSync|from ['"]node:|\bimport\(|require\(|new Function|\beval\(|fetch\(/.test(core.replace(block, '').replace(auth, '')) && !/console\./.test(R('datashare/intake.mjs')),
    'intake core and route: no file read, node import, eval or fetch outside the carried blocks; the route logs nothing');
}

/* ------------------------------------------------------------ intake route */
{
  const { handleIntake, INTAKE_ENDPOINT } = await import('./intake.mjs');
  const API = J('payments/registry/catalog.json').api_headers;
  const r2 = () => { const m = new Map(); return { m, puts: 0, head: async (k) => (m.has(k) ? { key: k } : null), async put(k, v) { this.puts++; m.set(k, v); } }; };
  const ON = () => ({ DATASHARE_INTAKE: 'on', DATASHARE_R2: r2() });
  const req = (body, over) => new Request('https://academy.example' + INTAKE_ENDPOINT, { method: 'POST', headers: { 'content-type': 'application/json', ...((over && over.headers) || {}) },
    body: typeof body === 'string' ? body : JSON.stringify(body), ...(over && over.method ? { method: over.method, body: undefined } : {}) });
  const call = async (env, r) => { const res = await handleIntake(r, env, { api_headers: API, subtle: webcrypto.subtle }); return { status: res.status, j: await res.json(), res }; };
  const g2 = J('contrib/fixture/v2/good.json');
  const restamp = (x) => { x.digest.hex = digestOf(x); return x; };
  ok(INTAKE_ENDPOINT === '/api/datashare/intake' && INTAKE_ENDPOINT === CFG.intake.endpoint, 'route: /api/datashare/intake, from datashare.json');
  let r = await call({ DATASHARE_R2: r2() }, req(g2)); ok(r.status === 404 && r.j.error === 'not_found', 'route: flag unset -> 404, as if no route existed (off by default)');
  r = await call({ DATASHARE_INTAKE: 'yes', DATASHARE_R2: r2() }, req(g2)); ok(r.status === 404, 'route: any flag value but "on" -> 404');
  r = await call(ON(), req(g2, { method: 'GET' })); ok(r.status === 405, 'route: GET -> 405');
  r = await call({ DATASHARE_INTAKE: 'on' }, req(g2)); ok(r.status === 503 && /DATASHARE_R2/.test(r.j.detail), 'route: no R2 binding -> 503 naming it');
  r = await call(ON(), req(g2, { headers: { 'content-type': 'text/plain' } })); ok(r.status === 415 && r.j.error === 'content_type', 'route: wrong content-type -> 415');
  r = await call(ON(), req('{"pad":"' + 'x'.repeat(CFG.intake.max_bytes) + '"}')); ok(r.status === 413 && r.j.error === 'too_large', 'route: oversize body -> 413');
  r = await call(ON(), req(g2, { headers: { 'content-length': String(CFG.intake.max_bytes + 1) } })); ok(r.status === 413, 'route: oversize content-length -> 413 before reading');
  r = await call(ON(), req('{not json')); ok(r.status === 400 && r.j.error === 'bad_json', 'route: not JSON -> 400');
  r = await call(ON(), req(J('contrib/fixture/good.json'))); ok(r.status === 422 && r.j.error === 'record' && /origin\.classroom_mode/.test(r.j.detail), 'route: a /1 package -> 422 (it cannot state classroom mode)');
  const noScope = restamp(JSON.parse(JSON.stringify(g2))); noScope.consent.scope = []; restamp(noScope);
  r = await call(ON(), req(noScope)); ok(r.status === 422 && r.j.error === 'unconsented' && /^consent\.scope/.test(r.j.detail), 'route: an empty consent scope -> 422 unconsented');
  const badStmt = JSON.parse(JSON.stringify(g2)); badStmt.consent.statement = 'I agree to everything.'; restamp(badStmt);
  r = await call(ON(), req(badStmt)); ok(r.status === 422 && r.j.error === 'unconsented', 'route: a statement other than the fixed one -> 422 unconsented');
  r = await call(ON(), req(J('contrib/fixture/v2/mutant-classroom-mode.json'))); ok(r.status === 422 && r.j.error === 'classroom' && /^origin\.classroom/.test(r.j.detail), 'route: a K-12 / classroom-mode package -> 422 classroom');
  r = await call(ON(), req(J('contrib/fixture/v2/mutant-latitude-in-gauges.json'))); ok(r.status === 422 && r.j.error === 'invalid' && /^privacy/.test(r.j.detail), 'route: a package with a location field -> 422 invalid, naming privacy');
  const tampered = JSON.parse(JSON.stringify(g2)); tampered.dataset.episodes[0].t = '2020-01-01T00:00:00Z';
  r = await call(ON(), req(tampered)); ok(r.status === 422 && /^digest/.test(r.j.detail), 'route: a package edited after export -> 422 naming digest');
  const env = ON();
  r = await call(env, req(g2));
  ok(r.status === 200 && r.j.stored === true && r.j.key === CFG.intake.key_prefix + g2.digest.hex + '.json' && env.DATASHARE_R2.m.get(r.j.key) === JSON.stringify(g2),
    'route: a valid /2 package -> 200, stored in R2 under packages/sha256/<digest>.json (content-addressed)');
  r = await call(env, req(g2)); ok(r.status === 200 && r.j.duplicate === true && env.DATASHARE_R2.puts === 1, 'route: the same package again -> stored once (duplicate by digest)');
  ok(r.res.headers.get('cache-control') === 'no-store' && API.every((h) => r.res.headers.get(h.key) === h.value), 'route: replies carry no-store and the security api headers');
  // a wallet-signed /2 package is recovered with the carried AUTH-CORE, as the CLI recovers it
  const { throwawayKey, signPersonal } = await import('../completion/test.mjs');
  const key = throwawayKey(7);
  const s = JSON.parse(JSON.stringify(g2)); s.contributor = { claimed: key.address, attested_by: 'wallet signature over the digest', signature: null }; restamp(s);
  const { signatureMessage } = await import('../contrib/verify.mjs');
  const msg = signatureMessage(s.digest.hex, s.exported_at, s.consent.scope);
  s.contributor.signature = { scheme: 'eip191-personal_sign', address: key.address, message: msg, sig: signPersonal(key.d, msg) };
  r = await call(ON(), req(s)); ok(r.status === 200 && r.j.stored === true, 'route: a wallet-signed /2 package verifies in the Worker path (signer recovered) and is stored');
  s.contributor.signature.sig = s.contributor.signature.sig.slice(0, -4) + (s.contributor.signature.sig.endsWith('1b') ? '001c' : '001b');
  r = await call(ON(), req(s)); ok(r.status === 422 && /^contributor\.signature/.test(r.j.detail), 'route: a tampered signature -> 422 naming contributor.signature');
}

/* ------------------------------------------------------------ worker mount */
{
  const W = await import('../payments/worker.mjs');
  const src = R('payments/worker.mjs');
  ok((src.match(/BEGIN DATASHARE/g) || []).length === 3 && (src.match(/END DATASHARE/g) || []).length === 3 && src.includes("from '../datashare/intake.mjs'"),
    'worker: mounted in three small anchored BEGIN/END DATASHARE blocks');
  ok(!W.ALL_ROUTES.includes(CFG.intake.endpoint) && W.FLAGGED_ROUTES.length === 1 && W.FLAGGED_ROUTES[0].path === CFG.intake.endpoint && W.FLAGGED_ROUTES[0].flag_env === 'DATASHARE_INTAKE',
    'worker: the intake is not in ALL_ROUTES (off by default) and is listed in FLAGGED_ROUTES with its flag');
  const catalog = J('payments/registry/catalog.json');
  const worker = W.makeWorker({ catalog, fetch: async () => { throw new Error('no'); }, subtle: webcrypto.subtle, uuid: () => 'x', now: () => 0 });
  const g2 = J('contrib/fixture/v2/good.json');
  const mk = () => new Request('https://academy.example' + CFG.intake.endpoint, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(g2) });
  const off = await worker.fetch(mk(), {}); const offJ = await off.json();
  const unk = await worker.fetch(new Request('https://academy.example/api/nope', { method: 'POST' }), {}); const unkJ = await unk.json();
  ok(off.status === 404 && JSON.stringify(offJ) === JSON.stringify(unkJ), 'worker: with the flag off the intake answers exactly like an unknown route');
  const m = new Map();
  const on = await worker.fetch(mk(), { DATASHARE_INTAKE: 'on', DATASHARE_R2: { head: async (k) => (m.has(k) ? {} : null), put: async (k, v) => { m.set(k, v); } } });
  ok(on.status === 200 && m.size === 1, 'worker: with the flag on and a (mock) bucket the routed intake stores the package');
}

ok(netCalls === 0, 'no test touched the network');
console.log(`\ndatashare: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
