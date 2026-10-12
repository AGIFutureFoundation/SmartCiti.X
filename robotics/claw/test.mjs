/* robotics/claw/test.mjs - the Omega Claw suite. Prints `ok <name>` per check and `FAIL <name>: <detail>` at column 0.
 * Dataset checks are named by their check id (split-leakage, duplicate-trajectory, provenance, revoked,
 * unquoted-instruction, class-balance, referee, card) so a mutation fails by name. Usage: node robotics/claw/test.mjs */
import { readFileSync, mkdtempSync, readdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { C, AUTH, REG, DS_CFG, ROOT, T, RoboCore, POLICY_VERSION, scripted, learner, assemble, indexOf, load } from './node.mjs';
import { exportDataset } from './export.mjs';

let n = 0, bad = 0;
const ok = (name, cond, detail) => { if (cond) { n++; console.log('  ok ' + name); } else { bad++; console.log('FAIL ' + name + ': ' + (detail || 'failed')); } };
const R = JSON.parse(readFileSync(join(ROOT, 'robotics/claw/registry/claw.json'), 'utf8'));
const HIVE = load('hive/registry/hive.json');
const REV = load('datashare/revocations.json');

// ---- registry
const chk = spawnSync('python3', [join(ROOT, 'robotics/claw/build.py'), '--check'], { encoding: 'utf8', cwd: ROOT });
ok('registry current', chk.status === 0, (chk.stderr || chk.stdout).trim().slice(-300));
ok('registry honest: no model behind the agents, nothing trained by this pack, the repo count read not typed', R.counts.models === 0 && R.counts.trained_by_this_pack === 0 && R.counts.repo_trained_models === REG.counts.trained_models
  && /THIS PACK TRAINS NOTHING/.test(R.honesty.trained) && /no LLM, no VLA/.test(R.honesty.trained) && R.honesty.trained.includes('counts ' + REG.counts.trained_models + ' trained model'));

// ---- agents: SCRIPTED, quoted or templated-measured, on-device voice on a click, within the Hive bounds
const roles = R.agents.map((a) => a.role).join();
ok('agents are the five roles', roles === 'scheduler,referee,steward,evaluator,coach', roles);
const unq = [];
for (const a of R.agents) for (const l of a.lines) {
  if (l.kind === 'quoted') { let t = null; try { t = C.quote(l.source); } catch (e) { unq.push(a.role + '.' + l.id + ': ' + e.message); continue; } if (t !== l.text) unq.push(a.role + '.' + l.id + ' is not the text at ' + l.source); }
  else if (l.kind === 'template') { const used = [...l.template.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(); if (used !== Object.keys(l.slots).sort().join() || Object.values(l.slots).some((k) => k !== 'n')) unq.push(a.role + '.' + l.id + ' template slots are not all measured numbers'); }
  else unq.push(a.role + '.' + l.id + ' is neither quoted nor a template');
}
ok('agent lines quoted from registries or templated measured numbers', unq.length === 0, unq.slice(0, 3).join('; '));
const vb = R.agents.filter((a) => !(a.voice.pitch >= HIVE.bounds.pitch[0] && a.voice.pitch <= HIVE.bounds.pitch[1] && a.voice.rate >= HIVE.bounds.rate[0] && a.voice.rate <= HIVE.bounds.rate[1]));
ok('agent voices inside the Omega Hive bounds', vb.length === 0, vb.map((a) => a.role).join());
ok('agents: no model, device speech synthesis on a click only', R.agents.every((a) => a.model === null && a.voice.engine === 'speechSynthesis' && a.voice.on_device_only && a.voice.on_click_only && a.personality.provenance === 'AUTHORED'));
let thrown = ''; try { C.render({ id: 'x', template: 'a {k}', slots: { k: 'n' } }, { k: 'seven' }); } catch (e) { thrown = e.message; }
ok('templates refuse a slot that is not a measured number', /not a measured number/.test(thrown), thrown);

// ---- dataset (rebuilt in memory from the page simulator) and its checks, each by name
const sc = scripted();
const { ds, idx, card, cardIds } = assemble(sc, 0);
const fails = C.validate(ds.samples, AUTH, REV, card, cardIds);
for (const id of C.CHECKS) { const f = fails.filter((x) => x.check === id); ok(id, f.length === 0, f.slice(0, 3).map((x) => x.detail).join('; ')); }
const index = indexOf(ds, idx);
ok('index equals the registry index', JSON.stringify(index) === JSON.stringify(R.dataset), 'rebuild robotics/claw');
ok('dataset covers every robokit task x level x seed', sc.length === Object.values(REG.envs).filter((e) => e.runner === 'robokit').reduce((a, e) => a + e.curriculum.levels.length * e.seeds.length, 0), String(sc.length));
ok('policy version is the registry benchmark version', POLICY_VERSION === REG.reference_benchmark.policy_version && sc.every((s) => s.provenance.policy_version === POLICY_VERSION));
// Referee re-derives every benchmark success count from the task's own rule
const mism = [];
for (const [env, b] of Object.entries(REG.reference_benchmark.per_env)) for (const [lv, row] of Object.entries(b.levels)) {
  const mine = ds.samples.filter((s) => s.task === env && s.level === +lv);
  const sx = mine.filter((s) => s.referee.success).length;
  if (sx !== row.success) mism.push(env + ' L' + lv + ' ' + sx + ' vs ' + row.success);
  for (const [seed, succ, coll, steps] of row.by_seed) { const s = mine.find((x) => x.seed === seed); if (!s || +s.referee.success !== succ || s.n_steps !== steps || s.outcome.collected !== coll) mism.push(env + ' L' + lv + ' s' + seed); }
}
ok('referee: success counts equal the measured reference benchmark per task, level and seed', mism.length === 0, mism.slice(0, 4).join('; '));
ok('instructions quoted from robotics, tasks and lessons registries', ['robotics/registry/robotics.json', 'tasks/registry/tasks.json'].every((f) => ds.samples.some((s) => s.instruction.source.startsWith(f + '#')))
  && ds.samples.some((s) => s.lesson && s.lesson.source.startsWith('lessons/registry/lessons.json#')));
ok('seen-tasks split: every family in every split', ['train', 'val', 'test'].every((sp) => Object.keys(AUTH.families).every((f) => ds.samples.some((s) => s.family === f && s.split['seen-tasks'] === sp))));
ok('card: tc-dataset/1 section ids', JSON.stringify(cardIds) === JSON.stringify(DS_CFG.card.template.map((s) => s.id)) && cardIds.length === 7, cardIds.join());
ok('card states that nothing is trained here', /trains nothing: no LLM, no VLA/.test(card) && card.includes('trained_models: ' + REG.counts.trained_models + ' in the whole repo') && /for training one elsewhere/.test(card));

// ---- learner path: only through the datashare intake rules
const pk = (f) => ({ name: f.split('/').pop(), record: JSON.parse(readFileSync(join(ROOT, f), 'utf8')) });
const L1 = await learner([pk('contrib/fixture/v2/good.json'), pk('datashare/fixture/v2-agent-only.json')], REV);
ok('learner: a robot-training package merges its human episodes with package provenance', L1.samples.length === 1 && L1.samples[0].actor === 'human' && /^[0-9a-f]{64}$/.test(L1.samples[0].provenance.package) && L1.samples[0].provenance.consent_scope === 'robot-training', String(L1.samples.length));
ok('learner: an agent-training-only package is refused by consent scope', L1.manifest.refused.some((r) => r.package === 'v2-agent-only.json' && r.reason === 'consent-scope'));
const revoke = { record: 'tc-revocations/1', packages: [], episodes: [L1.samples[0].provenance.episode_id] };
const L2 = await learner([pk('contrib/fixture/v2/good.json')], revoke);
ok('learner: a revoked episode is excluded', L2.samples.length === 0 && L2.manifest.excluded.revoked_episodes >= 1);
const mixed = assemble(sc.concat(L1.samples), 1);
const f2 = C.validate(mixed.ds.samples, AUTH, revoke, mixed.card, mixed.cardIds).filter((x) => x.check === 'revoked');
ok('revoked: the check names a revoked learner episode that slipped in', f2.length === 1, String(f2.length));
const mixOk = C.validate(mixed.ds.samples, AUTH, REV, mixed.card, mixed.cardIds);
ok('learner merge passes every dataset check', mixOk.length === 0, mixOk.slice(0, 2).map((x) => x.check + ' ' + x.detail).join('; '));

// ---- export: the files a trainer elsewhere would read
const out = mkdtempSync(join(tmpdir(), 'claw-'));
const ex = await exportDataset({ out, learnerFiles: [] });
let lines = 0, ids = new Set(), schemeOk = true;
if (ex.fails.length) schemeOk = false; else for (const scheme of Object.keys(AUTH.splits)) { const seen = new Set();
  for (const sp of ['train', 'val', 'test']) for (const l of readFileSync(join(out, scheme, sp + '.jsonl'), 'utf8').split('\n').filter(Boolean)) {
    const o = JSON.parse(l); lines++; if (seen.has(o.traj_hash)) schemeOk = false; seen.add(o.traj_hash); ids.add(o.id);
    if (o.observations.length !== o.actions.length || !o.instruction.text || o.provenance.seed !== o.seed) schemeOk = false; } }
ok('export writes every sample once per scheme with aligned observations and actions', ex.fails.length === 0 && schemeOk && lines === 2 * ds.samples.length && ids.size === ds.samples.length,
  lines + ' lines, ' + ids.size + ' ids');
ok('export writes the card and manifest', readdirSync(out).sort().join() === 'DATASET_CARD.md,manifest.json,seen-tasks,unseen-tasks', ex.fails.map((f) => f.check).slice(0, 3).join());
rmSync(out, { recursive: true, force: true });

// ---- batch B: the orchestrated tournament on the ARENA harness
const { tournament } = await import('./arena_adapter.mjs');
const TO = tournament();
ok('tournament equals the registry tournament (deterministic)', JSON.stringify(TO) === JSON.stringify(R.tournament), 'rebuild robotics/claw');
const H = await import('../arena/harness.mjs');
const Ptk = H.tasks(REG), Ppol = H.policies(REG);
ok('scheduler: queue = policies x task levels x seeds, each once', TO.queue_size === Ppol.length * Ptk.reduce((a, t) => a + t.levels.length * t.seeds.length, 0)
  && new Set(TO.runs.map((r) => r.slice(0, 4).join('|'))).size === TO.queue_size, String(TO.queue_size));
ok('referee: 0 harness outcomes disagree with the task rules', TO.referee_disagreements === 0, String(TO.referee_disagreements));
ok('referee: the reference policy in the tournament meets the rule exactly as in the dataset', TO.per_policy[TO.reference].success === ds.samples.filter((s) => s.referee.success).length);
const pairOk = Object.entries(TO.paired).every(([k, v]) => { const [a, b] = k.split(' vs '), rs = (id) => TO.runs.filter((r) => r[0] === id).map((r) => ({ env: r[1], level: r[2], seed: r[3], success: !!r[4], return: r[8] }));
  const B = new Map(rs(b).map((r) => [r.env + '|' + r.level + '|' + r.seed, r])); let ao = 0, bo = 0;   // independent join on the full key
  for (const r of rs(a)) { const o = B.get(r.env + '|' + r.level + '|' + r.seed); if (r.success && !o.success) ao++; if (!r.success && o.success) bo++; }
  return JSON.stringify(C.compare(rs(a), rs(b))) === JSON.stringify(v) && v.pairs === TO.per_policy[a].runs && v.a_only === ao && v.b_only === bo; });
ok('evaluator: paired statistics re-derive from the runs on identical (task, level, seed)', pairOk);
ok('evaluator: exact sign test', C.signTest(0, 10) === 2 / 1024 && C.signTest(5, 5) === 1 && C.signTest(0, 0) === 1);
const self = C.compare([{ env: 'e', level: 1, seed: 1, success: true, return: 1 }], [{ env: 'e', level: 1, seed: 1, success: true, return: 1 }]);
ok('evaluator: a policy against itself shows no difference', self.a_only === 0 && self.b_only === 0 && self.p === 1 && self.mean_return_diff === 0);
const AU = (role, id) => AUTH.agents[role].lines.find((l) => l.id === id);
ok('agents say measured tournament numbers through their templates', TO.said.scheduler === C.render(AU('scheduler', 'queue'), { runs: TO.queue_size, policies: Ppol.length, tasks: Ptk.length, levels: Ptk.reduce((a, t) => a + t.levels.length, 0), seeds: Ptk[0].seeds.length })
  && /^\d+ of \d+ runs met the success rule; \d+ reached the step cap; 0 outcomes disagreed with the rule\.$/.test(TO.said.referee));

// ---- batch B: human-training metrics and the Coach
const HOLD = HIVE.k12.hold_words;
const HIVE_B = HIVE.bounds;
function learnerEp(envId, seed, mod, stopAt) {   // a SCRIPTED fixture episode with the learner's shape (actor human) - no person involved
  const env = REG.envs[envId], emb = REG.embodiments[env.embodiments[0]], st = RoboCore.reset(env, emb, seed, 1), every = Math.round(1 / (T.world_teleop.sample_hz * env.episode_cap.dt_s)), S = [];
  while (!st.done && !(stopAt && st.step >= stopAt)) { let a = RoboCore.policy(st); a = mod ? mod(a, st.step) : a; if (st.step % every === 0 && S.length < T.world_teleop.max_samples) S.push(RoboCore.sample(st, a)); RoboCore.step(st, a); }
  return RoboCore.episode(st, 'human', 'lab', S, T);
}
const refEp = (envId, seed) => RoboCore.rollout(REG.envs[envId], REG.embodiments[REG.envs[envId].embodiments[0]], seed, T, 'lab', 1);
const refOf = (envId, seed) => { const row = R.reference_paths[envId].rows.find((r) => r[0] === seed); return { path_m: row[1], time_s: row[2], success: !!row[3] }; };
const rp = Object.entries(R.reference_paths).every(([env, t]) => t.rows.every(([seed, path, time, succ]) => JSON.stringify(C.refSummary(REG.envs[env], refEp(env, seed))) === JSON.stringify({ path_m: path, success: !!succ, time_s: time })));
ok('reference paths in the registry re-derive from the reference policy', rp && Object.keys(R.reference_paths).length === 4);
const mRef = C.metrics(REG.envs['world.gate-drive'], learnerEp('world.gate-drive', 3), refOf('world.gate-drive', 3));
ok('metrics: the reference driven as a learner scores efficiency 1, its own time, 0 contacts', mRef.eff === 1 && mRef.time === mRef.ref_time && mRef.collisions === 0 && mRef.success, JSON.stringify(mRef));
const mJit = C.metrics(REG.envs['world.gate-drive'], learnerEp('world.gate-drive', 3, (a, k) => ({ ...a, w: k % 4 < 2 ? a.w * -0.5 : a.w })), refOf('world.gate-drive', 3));
ok('metrics: jittery steering is less smooth, longer and slower', mJit.smooth > 4 * mRef.smooth && mJit.eff < 1 && mJit.time > mRef.time, JSON.stringify(mJit));
const mStop = C.metrics(REG.envs['world.gate-drive'], learnerEp('world.gate-drive', 3, null, 100), refOf('world.gate-drive', 3));
ok('metrics: a stopped run has no time to success and no efficiency', !mStop.success && mStop.time === -1 && mStop.eff === -1);
const cRef = C.coach(REG, AUTH, 'world.gate-drive', 1, mRef, false, HOLD), cJit = C.coach(REG, AUTH, 'world.gate-drive', 1, mJit, false, HOLD), cStop = C.coach(REG, AUTH, 'world.gate-drive', 1, mStop, false, HOLD);
ok('coach: a clean run moves up to the next declared level', cRef.rule === 'move-up' && cRef.next.env === 'world.gate-drive' && cRef.next.level === 2 && cRef.next.level_name === C.quote(cRef.next.level_source), JSON.stringify(cRef.next));
ok('coach: a run with contacts stays on its level; a stopped run stays too', cJit.rule === 'clean-up' && cJit.next.level === 1 && cStop.rule === 'not-yet' && cStop.next.level === 1, cJit.rule + ' ' + cStop.rule);
const mSort = C.metrics(REG.envs['world.litter-sort'], learnerEp('world.litter-sort', 1), refOf('world.litter-sort', 1));
const cSort = C.coach(REG, AUTH, 'world.litter-sort', 1, mSort, false, HOLD);
const bestSort = Math.max(...Object.values(REG.reference_benchmark.per_env['world.litter-sort'].levels).map((l) => l.success));
ok('coach: where the reference fails too, practise the level the measured reference finishes most', cSort.rule === 'reference-fails-too' && REG.reference_benchmark.per_env['world.litter-sort'].levels[String(cSort.next.level)].success === bestSort, JSON.stringify(cSort.next));
const top = C.coach(REG, AUTH, 'world.litter-pickup', 3, mRef, false, HOLD);
ok('coach: the top level of a task moves along the AUTHORED ladder to an existing task', top.next.env === AUTH.coach.ladder[AUTH.coach.ladder.indexOf('world.litter-pickup') + 1] && top.next.level === 1);
ok('coach: next lesson is quoted from the lessons registry', cRef.next.lesson && cRef.next.lesson.text === C.quote(cRef.next.lesson.source) && cRef.next.lesson.source.startsWith('lessons/registry/lessons.json#'));
ok('coach: classroom mode speaks only play-safe rule lines', AUTH.coach.rules.every((r) => r.k12 && !HOLD.some((w) => new RegExp('\\b' + w + '\\b', 'i').test(r.say))) && cRef.say && C.coach(REG, AUTH, 'world.gate-drive', 1, mRef, true, ['level', 'next', 'step']).say === null);
ok('coach: every rule line is AUTHORED in the claw registry and quoted from it', [cRef, cJit, cStop, cSort].every((c) => c.say.text === C.quote(c.say.source) && c.say.provenance === 'AUTHORED'));

// ---- batch C: the training-operations panel on the Robotics lab page
const PAGE = readFileSync(join(ROOT, 'web/trade_craft_robotics.html'), 'utf8');
const scr = (id) => { const m = PAGE.match(new RegExp('<script[^>]*id="' + id + '"[^>]*>([\\s\\S]*?)</script>')); return m ? m[1] : ''; };
const PD = JSON.parse(scr('train-ops-data') || 'null');
ok('panel: the page carries the section, its data, the lifted core and the panel script once each', PAGE.split('id="train-ops"').length === 2 && PD && scr('train-ops-core').length > 5000 && scr('train-ops-js').length > 2000);
ok('panel: the page data is the current registry (stamp, agents, tournament, dataset)', PD && PD.stamp === R.source_stamp && PD.agents.map((a) => a.id).join() === R.agents.map((a) => a.id).join()
  && JSON.stringify(PD.tournament.per_policy) === JSON.stringify(R.tournament.per_policy) && PD.dataset.samples === R.dataset.samples && PD.trained_by_this_pack === 0 && PD.agent_models === 0, 'rebuild web/build_robotics.py');
const coreSrc = readFileSync(join(ROOT, 'robotics/claw/core.mjs'), 'utf8');
const block = coreSrc.slice(coreSrc.indexOf('/* TRAIN_OPS_CORE:BEGIN */'), coreSrc.indexOf('/* TRAIN_OPS_CORE:END */') + '/* TRAIN_OPS_CORE:END */'.length);
ok('panel: the page core is the node core byte for byte (only export dropped)', scr('train-ops-core') === block.replace('export function trainOpsCore(', 'function trainOpsCore('));
const js = scr('train-ops-js') + scr('train-ops-core');
ok('panel: nothing leaves the device (no network API; the only storage write is the mute switch)', !/\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|EventSource|postMessage|\.submit\s*\(|import\s*\(/.test(js)
  && (js.match(/setItem\(/g) || []).length === 1 && /localStorage\.setItem\(KEY, muted \? '1' : '0'\)/.test(js) && /var KEY = 'tc\.trainops\.muted'/.test(js));
const J = scr('train-ops-js'), clickAt = J.indexOf("b.addEventListener('click', function () {"), muteAt = J.indexOf("document.getElementById('to-mute').addEventListener('click'");
ok('panel: speech only from a click, on-device English voices only, inside the Hive bounds; classroom starts muted', (J.match(/\bspeak\(/g) || []).length === 3 && J.indexOf('= speak(a, texts)') > clickAt && J.indexOf('= speak(a, texts)') < muteAt && clickAt > 0
  && /v\.localService && \/\^en\/i\.test/.test(J) && /muted = classroom \? sv !== '0' : sv === '1'/.test(J) && /classroom \? D\.k12_volume/.test(J) && /classroom \? D\.k12_rate_max/.test(J));
ok('panel: markers are neutral (no team codename token in the built page)', !/\b(CLAW|ARENA|ROBO[A-Z_]*)\b/.test(PAGE) && !/id="claw|class="claw|data-claw/.test(PAGE));
// the page's own core, run headless on the page's embedded data, scores a run exactly as the node core does
const PC = new Function(scr('train-ops-core') + '\nreturn trainOpsCore;')()({ load: (rel) => { if (!PD.files[rel]) throw new Error('not embedded ' + rel); return PD.files[rel]; }, sha256: () => { throw new Error('no hash'); } });
const pages = [['world.gate-drive', 3, null], ['world.gate-drive', 3, (a, k) => ({ ...a, w: k % 4 < 2 ? a.w * -0.5 : a.w })], ['world.litter-sort', 1, null], ['world.rov-survey', 1, null]];
const same = pages.every(([env, seed, mod]) => { const ep = learnerEp(env, seed, mod), row = PD.reference_paths[env].rows.find((r) => r[0] === seed), ref = { path_m: row[1], time_s: row[2], success: !!row[3] };
  const m1 = PC.metrics(PD.files['robotics/registry/robotics.json'].envs[env], ep, ref), m2 = C.metrics(REG.envs[env], ep, refOf(env, seed));
  const c1 = PC.coach(PD.files['robotics/registry/robotics.json'], PD.files['robotics/claw/authored/claw.json'], env, 1, m1, false, PD.hold_words), c2 = C.coach(REG, AUTH, env, 1, m2, false, HOLD);
  return JSON.stringify(m1) === JSON.stringify(m2) && JSON.stringify(c1) === JSON.stringify(c2); });
ok('panel: the page Coach, on its embedded data, gives the node Coach result (4 runs)', same);
const toKeys = (await import('node:child_process')).execFileSync('python3', ['-c', 'import sys; sys.path.insert(0, "robotics/claw"); import panel, json; print(json.dumps(panel.keys()))'], { cwd: ROOT, encoding: 'utf8' });
const LOC = readdirSync(join(ROOT, 'i18n/locales')).filter((f) => f.endsWith('.json')).map((f) => JSON.parse(readFileSync(join(ROOT, 'i18n/locales', f), 'utf8')));
const tk = JSON.parse(toKeys);
ok('panel: every panel key in all 8 locales; headings and notes translated', LOC.length === 8 && LOC.every((l) => tk.every((k) => typeof l.strings[k] === 'string' && l.strings[k].trim()))
  && LOC.filter((l) => l.locale !== 'en').every((l) => ['robo.to.note', 'robo.to.h.coach', 'robo.to.coach.note', 'robo.to.data.note'].every((k) => l.strings[k] !== LOC.find((x) => x.locale === 'en').strings[k])));
ok('panel: the page says nothing here trains a model', /Nothing on this page trains a model/.test(PAGE) && /models behind the agents 0 · models trained by this panel 0/.test(PAGE));

// ---- --browser: the panel in Chromium (desktop, phone, classroom, Arabic), with a mocked on-device voice
if (process.argv.includes('--browser')) {
  const { chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs');
  const br = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const url = 'file://' + join(ROOT, 'web/trade_craft_robotics.html');
  const key = load('training/registry/training.json').storage.key;
  const ep = { t: '2026-10-12T00:00:00.000Z', ...learnerEp('world.gate-drive', 3) };
  const init = ({ key, ep, seed }) => {
    if (seed) try { localStorage.setItem(key, JSON.stringify([ep])); } catch (e) { /* blocked */ }
    const said = []; window.__said = said;
    const synth = { speak: (u) => said.push({ text: u.text, pitch: u.pitch, rate: u.rate, volume: u.volume, local: u.voice && u.voice.localService }), cancel: () => {},
      getVoices: () => [{ name: 'net', lang: 'en-US', localService: false }, { name: 'dev', lang: 'en-GB', localService: true }], addEventListener: () => {}, onvoiceschanged: null };
    Object.defineProperty(window, 'speechSynthesis', { value: synth, configurable: true });
    window.SpeechSynthesisUtterance = function (text) { this.text = text; };
  };
  const open = async (q, vp, seed) => { const pg = await br.newPage({ viewport: vp }); const errs = []; pg.on('pageerror', (e) => errs.push(String(e))); pg.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
    await pg.addInitScript(init, { key, ep, seed }); await pg.goto(url + q); await pg.waitForFunction(() => window.__trainOps); return { pg, errs }; };
  const d = await open('', { width: 1280, height: 900 }, true);
  const st = await d.pg.evaluate(() => ({ runs: __trainOps.runs, rule: __trainOps.last && __trainOps.last.coach.rule, next: document.getElementById('to-next').textContent,
    lesson: document.getElementById('to-lesson').textContent, shown: !document.getElementById('to-coach').hidden, said0: __said.length, steward: document.querySelector('[data-to-lines="claw:steward"]').textContent }));
  ok('browser: the Coach reads the recorded run on the device and suggests the next declared level and lesson', st.runs === 1 && st.rule === 'move-up' && /narrow gates/.test(st.next) && st.lesson === C.quote(AUTH.instructions['world.gate-drive'].lesson) && st.shown, JSON.stringify(st));
  ok('browser: nothing is spoken before a click; agents list quoted and measured lines', st.said0 === 0 && /260 samples kept from 260 seeded episodes/.test(st.steward), JSON.stringify(st).slice(0, 200));
  await d.pg.click('[data-to-speak="claw:coach"]');
  const sp = await d.pg.evaluate(() => __said.slice());
  ok('browser: a click speaks the Coach lines with an on-device voice inside the bounds', sp.length >= 2 && sp.every((u) => u.local && u.pitch >= HIVE_B.pitch[0] && u.pitch <= HIVE_B.pitch[1] && u.rate <= HIVE_B.rate[1]) || false, JSON.stringify(sp).slice(0, 300));
  await d.pg.click('#to-mute'); await d.pg.click('[data-to-speak="claw:referee"]');
  ok('browser: muted, a click speaks nothing', (await d.pg.evaluate(() => __said.length)) === sp.length);
  ok('browser: no page errors (desktop)', d.errs.length === 0, d.errs.slice(0, 2).join(' | '));
  await d.pg.close();
  const ph = await open('', { width: 375, height: 800 }, true);
  const lay = await ph.pg.evaluate(() => { const r = document.getElementById('train-ops'); const small = [...r.querySelectorAll('button,select')].filter((b) => b.getBoundingClientRect().height < 44).length;
    return { over: document.documentElement.scrollWidth - document.documentElement.clientWidth, small, w: r.getBoundingClientRect().width }; });
  ok('browser: phone width - no horizontal scroll, every panel control at least 44 px tall', lay.over <= 1 && lay.small === 0 && ph.errs.length === 0, JSON.stringify(lay) + ph.errs.slice(0, 1));
  await ph.pg.close();
  const cl = await open('?classroom=1', { width: 1280, height: 900 }, true);
  await cl.pg.click('[data-to-speak="claw:coach"]');
  const cs = await cl.pg.evaluate(() => ({ cls: __trainOps.classroom, muted: __trainOps.muted(), runs: __trainOps.runs, note: !document.getElementById('to-class').hidden, said: __said.length }));
  ok('browser: classroom mode reads no runs, starts muted and speaks nothing', cs.cls && cs.muted && cs.runs === 0 && cs.note && cs.said === 0 && cl.errs.length === 0, JSON.stringify(cs));
  await cl.pg.close();
  const ar = await open('?lang=ar', { width: 1280, height: 900 }, false);
  const as = await ar.pg.evaluate(() => ({ h: document.getElementById('to-h').textContent, dir: document.documentElement.dir }));
  ok('browser: Arabic, right to left, panel heading translated', as.h === LOC.find((l) => l.locale === 'ar').strings['robo.to.h'] && as.dir === 'rtl' && ar.errs.length === 0, JSON.stringify(as));
  await ar.pg.close(); await br.close();
}

console.log(`claw: ${n} ok, ${bad} failed`);
process.exit(bad ? 1 : 0);
