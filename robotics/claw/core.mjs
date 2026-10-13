/* robotics/claw/core.mjs - the Omega Claw core: SCRIPTED orchestration agents (no AI model) and the trainable
 * instruction-conditioned datasets built from the SCRIPTED reference episodes of web/robokit.py (SIM_CORE).
 *
 * Pure: no file, network, storage, DOM or clock. Callers inject the registries, the env core (RoboCore), a sync
 * sha256 (hex) and, for learner data, the datashare core. NOTHING HERE TRAINS A MODEL - not an LLM, not a VLA,
 * not a controller. It assembles data that someone could train one with elsewhere, and it measures numbers.
 *
 * Fail closed: a missing registry field, an unresolvable source pointer or a line that is not character-for-
 * character its source stops the build by name. Every check returns failures named by the check id. */

/* TRAIN_OPS_CORE:BEGIN */
export function trainOpsCore(opt) {
  const { load, sha256 } = opt;
  if (typeof load !== 'function' || typeof sha256 !== 'function') throw new Error('claw: load(rel) and sha256(str) are required');
  const need = (cond, msg) => { if (!cond) throw new Error('claw: ' + msg); };
  const has = (o, k) => o !== null && typeof o === 'object' && Object.prototype.hasOwnProperty.call(o, k);
  const get = (o, k, who) => { need(has(o, k), who + ' lacks ' + JSON.stringify(k)); return o[k]; };

  /* ---- source pointers: "<file>#a.b[3]["dotted.key"][id=value].c" (the hive/ syntax plus a [field=value] select) */
  const TOK = /^(?:\.?([A-Za-z0-9_\-]+)|\[(\d+)\]|\["([^"]+)"\]|\[([A-Za-z_]+)=([^\]]+)\])/;
  function resolve(ref) {
    need(typeof ref === 'string' && ref.includes('#'), 'source ' + JSON.stringify(ref) + ' names no path');
    const [rel, path] = [ref.slice(0, ref.indexOf('#')), ref.slice(ref.indexOf('#') + 1)];
    let node = load(rel), rest = path;
    while (rest.length) {
      const m = TOK.exec(rest); need(m && m[0].length, 'bad source path ' + ref);
      if (m[2] !== undefined) { need(Array.isArray(node) && +m[2] < node.length, 'source path ' + ref + ': no index ' + m[2]); node = node[+m[2]]; }
      else if (m[4] !== undefined) {
        need(Array.isArray(node), 'source path ' + ref + ': [' + m[4] + '=..] on a non-list');
        const hit = node.filter((x) => x && String(x[m[4]]) === m[5]);
        need(hit.length === 1, 'source path ' + ref + ': ' + hit.length + ' entries with ' + m[4] + '=' + m[5]); node = hit[0];
      } else { const k = m[3] !== undefined ? m[3] : m[1]; need(has(node, k), 'source path ' + ref + ': no key ' + k); node = node[k]; }
      rest = rest.slice(m[0].length);
    }
    return node;
  }
  function quote(ref) { const t = resolve(ref); need(typeof t === 'string' && t.trim().length, ref + ' is not a non-empty string'); return t; }

  function canonical(v) {
    if (v === null || typeof v === 'boolean' || typeof v === 'string') return JSON.stringify(v);
    if (typeof v === 'number') { need(Number.isFinite(v), 'a non-finite number cannot be canonical'); return JSON.stringify(v); }
    if (Array.isArray(v)) return '[' + v.map(canonical).join(',') + ']';
    if (typeof v === 'object') return '{' + Object.keys(v).sort().map((k) => JSON.stringify(k) + ':' + canonical(v[k])).join(',') + '}';
    throw new Error('claw: a ' + typeof v + ' cannot be canonical');
  }
  const r3 = (x) => Math.round(x * 1000) / 1000;

  /* ---- templates: AUTHORED words, every slot a MEASURED number */
  function render(line, values) {
    need(typeof line.template === 'string', 'line ' + line.id + ' is not a template');
    const slots = get(line, 'slots', 'template ' + line.id);
    return line.template.replace(/\{(\w+)\}/g, (_, k) => {
      need(has(slots, k), 'template ' + line.id + ' uses an undeclared slot ' + k);
      need(has(values, k), 'template ' + line.id + ' has no measured value for ' + k);
      const v = values[k]; need(typeof v === 'number' && Number.isFinite(v), 'template ' + line.id + ' slot ' + k + ' is not a measured number');
      return String(v);
    });
  }

  /* ---- Referee: the task's own termination and success rules, applied to an episode */
  function referee(env, ep) {
    const term = get(env, 'termination', env.id), succ = term[0].id, cap = get(env, 'episode_cap', env.id).steps;
    const ids = term.map((t) => t.id);
    const total = env.objects.gates || env.objects.litter || env.objects.targets;
    const done = ep.outcome.done;
    let expect;
    if (ep.outcome.collected >= total) expect = succ; else if (ep.steps >= cap) expect = 'cap'; else expect = 'stopped';
    const success = expect === succ;
    return { rule: expect, rule_source: 'robotics/registry/robotics.json#envs["' + env.id + '"].termination[' + ids.indexOf(expect) + '].when',
      success, agrees: done === expect && !!ep.outcome.success === success && ids.includes(done) };
  }

  /* ---- the instruction-conditioned dataset from the seeded SCRIPTED episodes */
  function buildScripted({ reg, RoboCore, T, policyVersion, authored, regStamp }) {
    const A = authored, fam = get(A, 'families', 'claw.json'), ins = get(A, 'instructions', 'claw.json');
    const famOf = {}; for (const [f, envs] of Object.entries(fam)) for (const e of envs) { need(!famOf[e], e + ' is in two families'); famOf[e] = f; }
    const rk = Object.values(reg.envs).filter((e) => e.runner === 'robokit');
    need(rk.length === reg.counts.robokit_envs, 'robokit env count drifted from robotics.json#counts');
    const samples = [];
    for (const env of rk) {
      need(famOf[env.id], env.id + ' has no task family'); const b = get(ins, env.id, 'claw.json#instructions');
      const emb = reg.embodiments[env.embodiments[0]];
      for (const lv of env.curriculum.levels) for (const seed of env.seeds) {
        const ep = RoboCore.rollout(env, emb, seed, T, 'lab', lv.level);
        const isrc = b.instructions[(seed - 1) % b.instructions.length];
        const L = RoboCore.layout(env, seed, lv.level);
        samples.push(sampleOf({ env, ep, level: lv.level, level_name: lv.name, family: famOf[env.id], isrc, ctx: b.context, lesson: b.lesson, L,
          prov: { registry: 'robotics/registry/robotics.json#envs["' + env.id + '"]', registry_stamp: regStamp, policy: env.reference_policy.id,
            policy_version: policyVersion, actor: ep.actor, seed, level: lv.level, instruction_source: isrc, generator: 'robotics/claw/core.mjs#buildScripted' } }));
      }
    }
    return samples;
  }
  function sceneOf(L) {
    const p = (x, ks) => Object.fromEntries(ks.filter((k) => has(x, k)).map((k) => [k, typeof x[k] === 'number' ? r3(x[k]) : x[k]]));
    return { obstacles: L.obst.map((x) => p(x, ['id', 'e', 'n', 'r'])), items: L.items.map((x) => p(x, ['id', 'e', 'n', 'type'])),
      gates: L.gates.map((x) => p(x, ['id', 'e', 'n'])), targets: L.targets.map((x) => p(x, ['id', 'e', 'n', 'd'])), bin: L.bin ? p(L.bin, ['id', 'e', 'n']) : null };
  }
  function sampleOf({ env, ep, level, level_name, family, isrc, ctx, lesson, L, prov }) {
    const steps = ep.samples.map((s) => ({ i: s.i, pose: s.pose, vel: s.vel, near: s.near, a: s.a }));
    const traj_hash = sha256(canonical(steps.map((s) => [s.pose, s.vel, s.near, s.a])));
    const ref = referee(env, ep);
    return { id: 'claw-' + traj_hash.slice(0, 16), task: env.id, family, level, level_name, seed: ep.seed, actor: ep.actor,
      instruction: { text: quote(isrc), source: isrc }, context: ctx.map((c) => ({ text: quote(c), source: c })),
      lesson: lesson ? { text: quote(lesson), source: lesson } : null,
      action_names: env.action.fields.map((f) => f.name), scene: sceneOf(L), steps, traj_hash,
      outcome: ep.outcome, n_steps: ep.steps, dt_s: ep.dt_s, hz: ep.hz, referee: ref, provenance: prov };
  }

  /* learner episodes: ONLY those the datashare core admits for the robot-training scope, after revocations.
     ds = datashareCore instance; packages = [{name, record, verdict}] (verdict from contrib/verify.mjs). */
  async function mergeLearner({ ds, packages, revocations, built_at, reg, RoboCore, T, authored, scope }) {
    need(scope === 'robot-training', 'learner data merges only under the robot-training consent scope');
    const { manifest, items } = await ds.buildDataset({ packages, scope, built_at, revocations });
    const famOf = {}; for (const [f, envs] of Object.entries(authored.families)) for (const e of envs) famOf[e] = f;
    const out = [];
    for (const it of items) {
      const ep = it.episode; if (ep.kind !== 'world-teleop' || ep.actor !== 'human') continue;
      const env = get(reg.envs, ep.env, 'robotics.json#envs'), b = get(authored.instructions, env.id, 'claw.json#instructions');
      const row = manifest.episodes.find((r) => r.id === it.id);
      const level = env.curriculum.record_levels[0];
      const isrc = b.instructions[(ep.seed - 1) % b.instructions.length];
      out.push(sampleOf({ env, ep, level, level_name: env.curriculum.levels.find((l) => l.level === level).name, family: famOf[env.id], isrc,
        ctx: b.context, lesson: b.lesson, L: RoboCore.layout(env, ep.seed, level),
        prov: { registry: 'contribution package ' + row.provenance.package.slice(0, 16), registry_stamp: row.provenance.package, policy: 'human-teleop',
          policy_version: 'not applicable (human)', actor: 'human', seed: ep.seed, level, instruction_source: isrc, generator: 'robotics/claw/core.mjs#mergeLearner',
          episode_id: it.id, package: row.provenance.package, consent_scope: scope } }));
    }
    return { samples: out, manifest };
  }

  /* dedupe by trajectory hash (first kept), splits, class-balance weights */
  function finalize(samples, authored) {
    const seen = new Map(), kept = []; let duplicates = 0;
    for (const s of samples) { if (seen.has(s.traj_hash)) { duplicates++; continue; } seen.set(s.traj_hash, s); kept.push(s); }
    const SP = get(authored, 'splits', 'claw.json');
    for (const s of kept) {
      s.split = {};
      for (const [scheme, def] of Object.entries(SP)) {
        const key = def.by === 'seed' ? s.seed : s.family;
        const hit = ['train', 'val', 'test'].filter((k) => def[k].includes(key));
        need(hit.length === 1, 'split ' + scheme + ': ' + JSON.stringify(key) + ' falls in ' + hit.length + ' splits');
        s.split[scheme] = hit[0];
      }
    }
    const tasks = [...new Set(kept.map((s) => s.task))].sort(), n = kept.length;
    const per = Object.fromEntries(tasks.map((t) => [t, kept.filter((s) => s.task === t).length]));
    for (const s of kept) s.weight = r3(n / (tasks.length * per[s.task]));
    return { samples: kept, duplicates, per_task: per };
  }

  /* ---- the checks; each failure is named by its check id */
  const CHECKS = ['split-leakage', 'duplicate-trajectory', 'provenance', 'revoked', 'unquoted-instruction', 'class-balance', 'referee', 'card'];
  function validate(samples, authored, revocations, card, cardTemplateIds) {
    const fails = []; const F = (check, detail) => fails.push({ check, detail });
    const SP = authored.splits;
    // split-leakage
    for (const [scheme, def] of Object.entries(SP)) {
      const by = {}; for (const s of samples) { const k = def.by === 'seed' ? 'seed:' + s.seed : 'family:' + s.family; (by[k] = by[k] || new Set()).add(s.split[scheme]); }
      for (const [k, set] of Object.entries(by)) if (set.size > 1) F('split-leakage', scheme + ': ' + k + ' is in ' + [...set].sort().join('+'));
      const h = {}; for (const s of samples) { (h[s.traj_hash] = h[s.traj_hash] || new Set()).add(s.split[scheme]); }
      for (const [k, set] of Object.entries(h)) if (set.size > 1) F('split-leakage', scheme + ': trajectory ' + k.slice(0, 12) + ' is in ' + [...set].sort().join('+'));
      if (def.by === 'family') { const t = {}; for (const s of samples) (t[s.instruction.text] = t[s.instruction.text] || new Set()).add(s.split[scheme]);
        for (const [k, set] of Object.entries(t)) if (set.size > 1) F('split-leakage', scheme + ': instruction "' + k.slice(0, 40) + '" is in ' + [...set].sort().join('+')); }
      for (const sp of ['train', 'val', 'test']) if (!samples.some((s) => s.split[scheme] === sp)) F('split-leakage', scheme + ': split ' + sp + ' is empty');
    }
    // duplicate-trajectory
    const hs = new Set(); for (const s of samples) { if (hs.has(s.traj_hash)) F('duplicate-trajectory', s.id + ' repeats trajectory ' + s.traj_hash.slice(0, 12)); hs.add(s.traj_hash);
      if (s.traj_hash !== sha256(canonical(s.steps.map((x) => [x.pose, x.vel, x.near, x.a])))) F('duplicate-trajectory', s.id + ' carries a trajectory hash that is not its own'); }
    // provenance
    for (const s of samples) for (const k of authored.provenance_fields) {
      const v = s.provenance ? s.provenance[k] : undefined;
      if (v === undefined || v === null || v === '') F('provenance', s.id + ' lacks provenance.' + k);
    }
    // revoked
    const rp = new Set(revocations.packages), re = new Set(revocations.episodes);
    for (const s of samples) { if (s.provenance && re.has(s.provenance.episode_id)) F('revoked', s.id + ' is revoked episode ' + String(s.provenance.episode_id).slice(0, 16));
      if (s.provenance && rp.has(s.provenance.package)) F('revoked', s.id + ' comes from revoked package ' + String(s.provenance.package).slice(0, 16));
      if (s.actor === 'human' && s.provenance && s.provenance.consent_scope !== 'robot-training') F('revoked', s.id + ' is a learner episode without the robot-training consent scope'); }
    // unquoted-instruction
    for (const s of samples) for (const q of [s.instruction, ...s.context, ...(s.lesson ? [s.lesson] : [])]) {
      let t = null; try { t = quote(q.source); } catch (e) { F('unquoted-instruction', s.id + ': ' + e.message); continue; }
      if (t !== q.text) F('unquoted-instruction', s.id + ': "' + String(q.text).slice(0, 40) + '" is not the text at ' + q.source);
    }
    // class-balance
    const per = {}; for (const s of samples) per[s.task] = (per[s.task] || 0) + 1;
    const c = Object.values(per); if (c.length && Math.max(...c) / Math.min(...c) > authored.balance.max_ratio) F('class-balance', 'task counts ' + JSON.stringify(per) + ' exceed max_ratio ' + authored.balance.max_ratio);
    const wsum = {}; for (const s of samples) wsum[s.task] = (wsum[s.task] || 0) + s.weight;
    const w = Object.values(wsum); if (w.length && Math.max(...w) - Math.min(...w) > 0.01 * samples.length / w.length) F('class-balance', 'task weights ' + JSON.stringify(wsum) + ' are not equal');
    // referee
    for (const s of samples) if (!s.referee.agrees) F('referee', s.id + ': outcome ' + s.outcome.done + ' disagrees with the task rule ' + s.referee.rule);
    // card
    if (card !== undefined) {
      for (const id of cardTemplateIds) if (!card.includes('<!-- section:' + id + ' -->')) F('card', 'dataset card lacks the tc-dataset/1 section ' + id);
      if (/\{\{\w+\}\}/.test(card)) F('card', 'dataset card has an unfilled slot');
      for (const w of ['Intended use', 'Limits', 'trains nothing']) if (!card.includes(w)) F('card', 'dataset card does not state ' + w);
    }
    return fails;
  }

  /* ---- the dataset card: the tc-dataset/1 section ids (datashare.json#card.template), AUTHORED words, MEASURED numbers */
  function renderCard(ds, idx, cardTemplate) {
    const by = (k) => { const o = {}; for (const s of ds.samples) o[s[k]] = (o[s[k]] || 0) + 1; return Object.entries(o).map(([a, b]) => a + ' ' + b).join(', '); };
    const sp = (scheme) => ['train', 'val', 'test'].map((k) => k + ' ' + ds.samples.filter((s) => s.split[scheme] === k).length).join(', ');
    const succ = ds.samples.filter((s) => s.referee.success).length;
    const body = {
      motivation: ['Instruction-conditioned observation/action trajectories from the four AUTHORED robotics-lab tasks, for someone to train or evaluate a robot-learning model (a language-conditioned policy or a vision-language-action model) ELSEWHERE.',
        'This pack trains nothing: no LLM, no VLA, no controller is trained by robotics/claw, and no language model is trained or used. The samples are data for training one elsewhere. The robotics registry counts trained_models: ' + idx.repo_trained_models + ' in the whole repo (models trained by other packs, never by this one).'],
      composition: [ds.samples.length + ' samples (' + idx.episodes + ' seeded episodes, ' + ds.duplicates + ' duplicate trajectories removed). By task: ' + by('task') + '. By family: ' + by('family') + '.',
        'By actor: ' + by('actor') + '. ' + succ + ' samples met their task success rule (Referee); the rest are kept and labelled, not filtered.',
        'Each sample: one instruction quoted from a registry (with its source pointer), registry context lines, the seeded scene layout, 5 Hz steps {pose, vel, near, a} and the outcome.',
        'Splits, scheme seen-tasks (by seed: ' + JSON.stringify(idx.splits_def['seen-tasks']) + '): ' + sp('seen-tasks') + '.',
        'Splits, scheme unseen-tasks (by task family: ' + JSON.stringify(idx.splits_def['unseen-tasks']) + '): ' + sp('unseen-tasks') + '.'],
      collection: ['Episodes are produced headless by the SCRIPTED reference policy of the page simulator (policy version ' + idx.policy_version + '), one per task x curriculum level x declared seed. Deterministic: the same build reproduces every trajectory hash.',
        'Learner episodes enter only as contribution packages the datashare intake admits for the robot-training consent scope, minus the revocation list; ' + idx.learner + ' are merged in this build. Nothing is collected by this pack.'],
      preprocessing: ['Deduplicated by trajectory hash (SHA-256 of the canonical step sequence). Class balance: largest/smallest task count ' + idx.balance_ratio + ' (bound ' + idx.balance_max + '); per-sample weights equalise tasks.',
        'Every check is enforced by robotics/claw/test.mjs: split leakage, duplicate trajectory, provenance fields, revoked episodes, instructions quoted from registries, class balance, Referee agreement, this card.'],
      uses: ['Intended use: exercising a robot-learning pipeline (data loading, instruction conditioning, in-distribution and held-out-task evaluation) on schematic data.',
        'Limits: the arenas and robots are AUTHORED and SCHEMATIC (unicycle kinematics, no sensors beyond pose and nearby ids, no images); the demonstrations are one hand-written policy, so they carry its habits and its failures. Not for training a controller for real equipment or a real robot. Shaped after common episode formats; not an RLDS, LeRobot or ML-Agents file.'],
      distribution: ['Licence of learner-contributed samples: the datashare licence they were given under; scripted samples are generated from this repository. Nothing is uploaded: robotics/claw/export.mjs writes the files where it is run.'],
      maintenance: ['Revocation: a learner episode or package on datashare/revocations.json is excluded at the next build, by name. Index digest: ' + idx.digest + '.'],
    };
    const ids = cardTemplate.map((s) => s.id);
    const out = ['# Omega Claw robot-learning dataset (tc-dataset/1 card sections)'];
    for (const s of cardTemplate) { out.push('', '<!-- section:' + s.id + ' -->', '## ' + s.title); for (const l of get(body, s.id, 'card body')) out.push('- ' + l); }
    return { card: out.join('\n'), ids };
  }

  /* ---- human-training metrics for a learner's episode, against the SCRIPTED reference on the same env/seed/level */
  function pathLen(samples) { let d = 0; for (let i = 1; i < samples.length; i++) d += Math.hypot(samples[i].pose[0] - samples[i - 1].pose[0], samples[i].pose[1] - samples[i - 1].pose[1]); return d; }
  /* the reference summary a learner is measured against: {path_m, success, time_s} (the registry's reference_paths rows) */
  function refSummary(env, refEp) { const ok = referee(env, refEp).success; return { path_m: r3(pathLen(refEp.samples)), success: ok, time_s: ok ? r3(refEp.steps * refEp.dt_s) : -1 }; }
  function metrics(env, ep, ref) {
    const f = env.action.fields, S = ep.samples; let sm = 0, k = 0;
    for (let i = 1; i < S.length; i++) { let a = 0; f.forEach((x, j) => { a += Math.abs((S[i].a[j] || 0) - (S[i - 1].a[j] || 0)) / (x.high - x.low); }); sm += a / f.length; k++; }
    const w = env.reward.find((r) => r.term === 'collision');
    const lp = pathLen(S), rp = get(ref, 'path_m', 'reference summary');
    const success = referee(env, ep).success, ref_success = get(ref, 'success', 'reference summary');
    return { smooth: r3(k ? sm / k : 0), eff: success && ref_success && lp > 0 ? r3(rp / lp) : -1, collisions: w ? Math.round((ep.outcome.terms.collision || 0) / w.weight) : 0,
      time: success ? r3(ep.steps * ep.dt_s) : -1, success, ref_success, ref_time: get(ref, 'time_s', 'reference summary'), path_m: r3(lp), ref_path_m: r3(rp) };
  }
  /* Coach: AUTHORED rules (first match wins) -> a next step in the EXISTING curriculum (env levels, the AUTHORED ladder) */
  function cond(when, m, bounds) {
    return when.split('&&').map((x) => x.trim()).every((atom) => {
      const bo = /^(!?)(success|ref_success)$/.exec(atom); if (bo) return bo[1] ? !get(m, bo[2], 'metrics') : !!get(m, bo[2], 'metrics');
      const mm = /^(\w+) (>=|>|<|<=) (\w+|[\d.]+)$/.exec(atom); need(mm, 'coach: cannot read condition ' + atom);
      const L = get(m, mm[1], 'metrics'), R = /^[\d.]+$/.test(mm[3]) ? +mm[3] : get(bounds, mm[3], 'coach bounds');
      return mm[2] === '>=' ? L >= R : mm[2] === '>' ? L > R : mm[2] === '<' ? L < R : L <= R;
    });
  }
  function coach(reg, authored, envId, level, m, classroom, holdWords) {
    const C = authored.coach, rules = C.rules;
    const i = rules.findIndex((r) => cond(r.when, m, C.bounds)); need(i >= 0, 'coach: no rule matched');
    const r = rules[i], env = reg.envs[envId];
    let next = { env: envId, level };
    if (r.next === 'practice') {   // the declared level where the MEASURED reference benchmark finishes most often (ties: lowest)
      const lv = reg.reference_benchmark.per_env[envId].levels; let best = level, bs = -1;
      for (const l of env.curriculum.levels) { const s = lv[String(l.level)].success; if (s > bs) { bs = s; best = l.level; } }
      next = { env: envId, level: best };
    }
    if (r.next === 'up') {
      if (env.curriculum.levels.some((l) => l.level === level + 1)) next = { env: envId, level: level + 1 };
      else { const j = C.ladder.indexOf(envId); next = j >= 0 && j + 1 < C.ladder.length ? { env: C.ladder[j + 1], level: 1 } : { env: envId, level }; }
    }
    const ne = reg.envs[next.env], lv = ne.curriculum.levels.find((l) => l.level === next.level);
    const b = authored.instructions[next.env];
    let say = { text: r.say, source: 'robotics/claw/authored/claw.json#coach.rules[' + i + '].say', provenance: 'AUTHORED' };
    if (classroom && (!r.k12 || holdWords.some((w) => new RegExp('\\b' + w + '\\b', 'i').test(r.say)))) say = null;
    return { rule: r.id, say, next: { env: next.env, env_name: ne.name, env_source: 'robotics/registry/robotics.json#envs["' + next.env + '"].name',
      level: next.level, level_name: lv.name, level_source: 'robotics/registry/robotics.json#envs["' + next.env + '"].curriculum.levels[' + ne.curriculum.levels.indexOf(lv) + '].name',
      lesson: b && b.lesson ? { text: quote(b.lesson), source: b.lesson } : null } };
  }

  /* ---- Scheduler: the queue policies x tasks x levels x seeds, in a fixed order */
  function schedule(policies, tasks) {
    const q = [];
    for (const p of policies) for (const t of tasks) for (const level of t.levels) for (const seed of t.seeds) q.push({ policy: p.id, env: t.env, level, seed });
    return q;
  }
  /* ---- Evaluator: paired statistics on (env, level, seed) */
  function binom(n, k) { let r = 1; for (let i = 1; i <= k; i++) r = r * (n - k + i) / i; return r; }
  function signTest(b, c) { const n = b + c; if (!n) return 1; const k = Math.min(b, c); let s = 0; for (let i = 0; i <= k; i++) s += binom(n, i); return Math.min(1, 2 * s / Math.pow(2, n)); }
  function compare(runsA, runsB) {
    const key = (r) => r.env + '|' + r.level + '|' + r.seed, mb = new Map(runsB.map((r) => [key(r), r]));
    let pairs = 0, a_only = 0, b_only = 0, both = 0, neither = 0, dsum = 0, dpos = 0, dneg = 0; const d = [];
    for (const a of runsA) { const b = mb.get(key(a)); if (!b) continue; pairs++;
      if (a.success && !b.success) a_only++; else if (!a.success && b.success) b_only++; else if (a.success) both++; else neither++;
      const x = a.return - b.return; d.push(x); dsum += x; if (x > 1e-9) dpos++; else if (x < -1e-9) dneg++; }
    // seeded bootstrap of the mean paired return difference (mulberry32, seed 1; 2000 resamples) - deterministic
    let s = 1; const rnd = () => { s |= 0; s = s + 0x6D2B79F5 | 0; let t = Math.imul(s ^ s >>> 15, 1 | s); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
    const means = []; if (d.length) for (let b = 0; b < 2000; b++) { let m = 0; for (let i = 0; i < d.length; i++) m += d[Math.floor(rnd() * d.length)]; means.push(m / d.length); }
    means.sort((x, y) => x - y);
    const g3 = (x) => Number(x.toPrecision(3));
    return { pairs, a_only, b_only, both, neither, p: g3(signTest(a_only, b_only)), mean_return_diff: pairs ? r3(dsum / pairs) : 0,
      return_wins: [dpos, dneg], p_return: g3(signTest(dpos, dneg)), ci95: means.length ? [r3(means[49]), r3(means[1949])] : [0, 0] };
  }

  return { resolve, quote, canonical, render, referee, refSummary, buildScripted, mergeLearner, finalize, validate, renderCard, metrics, coach, schedule, compare, signTest, CHECKS, pathLen };
}
/* TRAIN_OPS_CORE:END */
