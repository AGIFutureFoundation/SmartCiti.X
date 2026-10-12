/* web/test_robotics.mjs - the Robotics lab page (web/trade_craft_robotics.html), checked against the registries it is
 * built from. Browser-free. Recompute, never re-read: counts are recounted from robotics.json, the embedded data is
 * compared to the registry, and every chrome key is looked up in all 8 locales.
 * Wave 15: curriculum levels, the MEASURED reference benchmark table and the local dataset-analytics panel (its
 * analytics() is run here headless on scripted episodes and recounted).
 * --browser (or --browser=<base url>) also drives the page in Chromium; without a url it serves web/ itself on
 * 127.0.0.1 and stops only the server it started. Run it under flock $SP/chromium.lock. */
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (m, c, why) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m + (why ? ' :: ' + JSON.stringify(why).slice(0, 400) : '')); } };
const page = readFileSync(join(HERE, 'trade_craft_robotics.html'), 'utf8');
const reg = JSON.parse(readFileSync(join(ROOT, 'robotics/registry/robotics.json'), 'utf8'));
const tr = JSON.parse(readFileSync(join(ROOT, 'training/registry/training.json'), 'utf8'));
const blob = (id) => JSON.parse(page.split(`<script type="application/json" id="${id}">`)[1].split('</script>')[0]);
const data = blob('robo-data'), I = blob('robo-i18n');
const rk = Object.values(reg.envs).filter((e) => e.runner === 'robokit');

ok('exactly one <h1>, and it is the translated page title', (page.match(/<h1[\s>]/g) || []).length === 1
  && /<h1 class="tc-page-title" data-i18n="robo.title">/.test(page));
ok('the site nav is present and marks this page current', page.includes('aria-current="page"')
  && /href="trade_craft_robotics.html" aria-current="page"/.test(page));
ok('the saved-style head script runs before paint', page.indexOf('id="style-head-js"') > 0
  && page.indexOf('id="style-head-js"') < page.indexOf('</head>'));
ok('the embedded data is the registry: same stamp, same robokit env ids, same embodiments',
  data.robo.stamp === reg.source_stamp && Object.keys(data.robo.envs).join() === rk.map((e) => e.id).join()
  && Object.keys(data.robo.embodiments).join() === Object.keys(reg.embodiments).join());
ok('the embedded training data is training/ (same key, toggle, cap, world teleop rate and cap)',
  JSON.stringify(data.train.storage) === JSON.stringify(tr.storage)
  && JSON.stringify(data.train.world_teleop) === JSON.stringify(tr.world_teleop));
ok('the figures are recounted from the registry, and trained models prints 0',
  ['envs', 'robokit_envs', 'sim_seat_envs', 'embodiments', 'trained_models'].every((k) =>
    page.includes(`data-robo-count="${k}">${reg.counts[k]}<`))
  /* ARENA BEGIN (wave 18) */ && reg.counts.trained_models === JSON.parse(readFileSync(join(ROOT, 'robotics/arena/registry/models.json'), 'utf8')).models.filter((m) => m.provenance === 'TRAINED').length /* ARENA END */
  && Object.values(reg.envs).length === reg.counts.envs);
ok('every env in the registry has a catalogue entry, every embodiment a card',
  Object.keys(reg.envs).every((id) => page.includes(`data-env="${id}"`))
  && Object.keys(reg.embodiments).every((id) => page.includes(`data-emb="${id}"`)));
ok('every registry honesty line is printed verbatim', Object.keys(reg.honesty).every((k) => page.includes(`data-honesty="${k}"`)));
ok('the page says what is and is not trained (three of each)', (page.split('id="robo-is"')[1] || '').split('</ul>')[0].split('<li>').length === 4
  && (page.split('id="robo-not"')[1] || '').split('</ul>')[0].split('<li>').length === 4);
ok('links to the parish world, the Bay world, the training seats and the Contribute page, each a real file',
  ['trade_craft_parishes.html', 'trade_craft_bay.html', 'trade_craft_3d.html', 'trade_craft_contribute.html'].every((f) =>
    page.includes(`href="${f}"`) && existsSync(join(HERE, f))));
const keys = [...new Set([...page.matchAll(/data-i18n="([^"]+)"/g)].map((m) => m[1]))];
ok(`every chrome key (${keys.length}) exists, non-empty, in all 8 locales; Arabic is right-to-left`,
  Object.keys(I).length === 8 && keys.every((k) => Object.values(I).every((L) => typeof L.strings[k] === 'string' && L.strings[k].trim()))
  && I.ar.dir === 'rtl');
ok('the non-English chrome is translated, not copied (under 10% identical to English)', Object.entries(I).filter(([l]) => l !== 'en').every(([, L]) =>
  Object.keys(L.strings).filter((k) => L.strings[k] === I.en.strings[k]).length < Object.keys(L.strings).length * 0.1));
ok('the touch pad keys (every teleop touch label) are in the catalogue',
  Object.values(reg.teleop).every((t) => t.touch.every((b) => typeof I.en.strings[b.label_key] === 'string')));
ok('the sandbox panel is mounted with its controls (env, seed, reset, record, reference, export, canvas, pad)',
  ['robo-env', 'robo-seed', 'robo-reset', 'robo-rec', 'robo-ref', 'robo-export', 'robo-canvas', 'robo-pad', 'robo-cmp'].every((id) => page.includes(`id="${id}"`)));
ok('touch controls are at least 44 px', /\.robo-row select,\.robo-row button,\.robo-pad button\{min-block-size:44px;min-inline-size:44px/.test(page));
ok('classroom / K-12 mode disables recording and export', page.includes("q.has('classroom') || q.has('class')")
  && page.includes("$('#robo-rec').disabled = true; $('#robo-export').disabled = true;"));
ok('the reference-results table is computed in the page from the core, nothing typed in',
  page.includes('RoboCore.rollout(env, emb, s, data.train') && !/data-refrun-fixed/.test(page));
ok('no Math.random anywhere in the page scripts', !page.includes('Math.random'));
ok('no upload: the page makes no network request (no fetch, no XHR, no sendBeacon)', !/fetch\(|XMLHttpRequest|sendBeacon/.test(
  page.split('<script id="robo-kit">')[1].split('</script>')[0] + page.split('<script id="robo-page">')[1].split('</script>')[0]));

/* ---- wave 15: curriculum, benchmark table, local dataset analytics ---- */
ok('the sandbox offers a curriculum level selector and says recording is level 1 only (robo.level, robo.level.note)',
  page.includes('id="robo-level"') && page.includes('id="robo-lvlnote"') && ['robo.level', 'robo.level.note'].every((k) => Object.values(I).every((L) => L.strings[k]))
  && Object.values(data.robo.envs).every((e) => e.curriculum && e.curriculum.levels.length === (e.id === 'world.litter-sort' ? 4 : 3) && JSON.stringify(e.curriculum.record_levels) === '[1]'));
const B = reg.reference_benchmark, brows = [...page.matchAll(/<tr data-bench="([^"]+)" data-level="(\d)">.*?<td data-bench-success>(\d+) \/ (\d+)<\/td><td>(\d+)<\/td>/g)];
ok(`the benchmark table is the registry's MEASURED block: one row per env and level (${brows.length}), success/runs and items equal`,
  brows.length === rk.reduce((a, e) => a + e.curriculum.levels.length, 0) && brows.every((m) => { const r = B.per_env[m[1]].levels[m[2]]; return r && +m[3] === r.success && +m[4] === r.runs && +m[5] === r.items; }));
ok('the benchmark section prints the policy version and every seed it ran',
  page.includes(`policy ${B.policy_version}`) && page.includes('seeds ' + B.seeds.join(', ')));
const FS = B.per_env['world.litter-sort'].feasibility;
ok(`the litter-sort bound line prints the registry's feasible seeds (${FS.feasible_seeds}/${B.seeds.length}) and item bound (${FS.items_bound})`,
  page.includes(`<b data-feas>${FS.feasible_seeds} / ${B.seeds.length}</b>`) && page.includes(`<b data-ibound>${FS.items_bound}</b>`)
  && FS.feasible_seeds * 2 < B.seeds.length);
const pjs = page.split('<script id="robo-page">')[1].split('</script>')[0];
const anSrc = (pjs.split('/* ANALYTICS_PANEL:BEGIN')[1] || '').split('function render()')[0];
ok('the analytics panel is mounted (count, steps, success, duration, histogram, tc-dataset/1 card preview) and says nothing is uploaded',
  ['count', 'steps', 'success', 'duration'].every((k) => page.includes(`data-an="${k}"`)) && page.includes('id="robo-an-hist"')
  && page.includes('id="robo-an-card"') && /Nothing is uploaded/.test(I.en.strings['robo.an.note']) && anSrc.length > 200);
const kitSrc = page.split('<script id="robo-kit">')[1].split('</script>')[0];
const PC = new Function(kitSrc.split('function roboMount')[0] + '\nreturn RoboCore;')();
const eps = rk.map((e) => ({ t: '2026-10-06T00:00:00Z', ...PC.rollout(e, data.robo.embodiments[e.embodiments[0]], e.seeds[0], data.train, 'lab', 1) }));
const A = new Function('window', 'R', anSrc.split('var an = { count: 0 };')[1] + '\nreturn analytics();')({ __robokit: { episodes: () => eps } }, data.robo);
const nS = eps.reduce((a, x) => a + x.samples.length, 0);
ok(`analytics() recounts ${eps.length} scripted episodes: count, steps, success, duration and per-sample histogram (${A.samples} samples)`,
  A.count === eps.length && A.steps === eps.reduce((a, x) => a + x.steps, 0) && A.success === eps.filter((x) => x.outcome.success).length
  && Math.abs(A.duration_s - eps.reduce((a, x) => a + x.steps * x.dt_s, 0)) < 1e-9 && A.samples === nS
  && A.hist.forward + A.hist.stop + A.hist.reverse === nS && A.hist.left + A.hist.straight + A.hist.right === nS
  && A.hist.grip > 0 && A.hist.dive + A.hist.rise > 0);
ok('every histogram bin label is a robo.an.b.* key, present in all 8 locales (the bars are not English-only)',
  pjs.includes("lab.textContent = t('robo.an.b.' + k)") && Object.keys(A.hist).every((k) => Object.values(I).every((L) => typeof L.strings['robo.an.b.' + k] === 'string' && L.strings['robo.an.b.' + k].trim())));
ok('the card preview names tc-dataset/1, the world-teleop kind version and trained_models 0, and points to datashare/ for the real manifest',
  /schema: 'tc-dataset\/1', preview: true/.test(pjs) && pjs.includes("'world-teleop/' + data.train.kind.v") && /trained_models: 0/.test(pjs) && /built by datashare\//.test(pjs));
ok('the robot is drawn where it is: translate/rotate run as code, not inside a comment', /\n\s*g\.save\(\); g\.translate\(X\(st\.e\), Y\(st\.n\)\); g\.rotate\(-st\.yaw\);/.test(kitSrc)
  && !/\/\/[^\n]*g\.translate\(X\(st\.e\)/.test(kitSrc));

/* ---- wave 16: the benchmark chart (A2) and the episode replay viewer (A1) ---- */
const chartSrc = (page.split('id="robo-chart"')[1] || '').split('</figure>')[0];
const crows = [...chartSrc.matchAll(/<div class="bc-env" data-chart-env="([^"]+)">(.*?)(?=<div class="bc-env"|<p class="bc-total"|$)/gs)]
  .flatMap((m) => [...m[2].matchAll(/data-chart-level="(\d+)" data-chart-success="(\d+)" data-chart-runs="(\d+)">.*?inline-size:(\d+)%.*?<span class="bc-num">(\d+) \/ (\d+)<\/span>/g)]
    .map((r) => ({ env: m[1], level: r[1], s: +r[2], n: +r[3], pct: +r[4], ts: +r[5], tn: +r[6] })));
const nLevels = rk.reduce((a, e) => a + Object.keys(B.per_env[e.id].levels).length, 0);
ok(`chart: one bar per env and curriculum level (${crows.length} of ${nLevels}), each success / runs equal to the registry's MEASURED block`,
  crows.length === nLevels && crows.every((c) => { const r = B.per_env[c.env] && B.per_env[c.env].levels[c.level];
    return r && c.s === r.success && c.n === r.runs && c.ts === r.success && c.tn === r.runs; }));
ok('chart: every bar length is round(100 x success / runs) - drawn from the numbers, not typed',
  crows.length > 0 && crows.every((c) => c.pct === Math.round(100 * c.s / c.n)));
ok(`chart: the level-1 total is the registry totals (${B.totals.success} / ${B.totals.runs}), and the chart has a caption key in all 8 locales`,
  chartSrc.includes(`data-chart-total="${B.totals.success}/${B.totals.runs}"`) && chartSrc.includes(`<b>${B.totals.success} / ${B.totals.runs}</b>`)
  && ['robo.h.chart', 'robo.chart.note', 'robo.chart.total'].every((k) => Object.values(I).every((L) => typeof L.strings[k] === 'string' && L.strings[k].trim())));
const rpSrc = page.split('<script id="robo-replay">')[1].split('</script>')[0];
const rpCore = (rpSrc.split('/* REPLAY_CORE:BEGIN')[1] || '').split('/* REPLAY_CORE:END */')[0];
ok('replay: the viewer is mounted (source, env, seed, level, load, play, scrubber, readout, arena, actions and return charts)',
  ['robo-rp-src', 'robo-rp-env', 'robo-rp-seed', 'robo-rp-level', 'robo-rp-load', 'robo-rp-play', 'robo-rp-k', 'robo-rp-read', 'robo-rp-arena', 'robo-rp-act', 'robo-rp-ret']
    .every((id) => page.includes(`id="${id}"`)) && pjs.includes('rpMount(data, t);') && rpCore.length > 500);
ok('replay: no network and no randomness in the viewer (no fetch, XHR, sendBeacon, Math.random); the 14 replay keys are in all 8 locales',
  !/fetch\(|XMLHttpRequest|sendBeacon|Math\.random/.test(rpSrc) && ['robo.h.replay', 'robo.rp.note', 'robo.rp.src', 'robo.rp.ref', 'robo.rp.mine', 'robo.rp.load',
    'robo.rp.play', 'robo.rp.pause', 'robo.rp.scrub', 'robo.rp.actions', 'robo.rp.reward', 'robo.rp.exact', 'robo.rp.held', 'robo.rp.none']
    .every((k) => Object.values(I).every((L) => typeof L.strings[k] === 'string' && L.strings[k].trim())));
const rpTrace = new Function('RoboCore', rpCore.replace(/^[^\n]*\n/, '') + '\nreturn rpTrace;')(PC);
const RD = data.robo;
let rpRef = 0, rpBad = [];
for (const e of rk) for (const lv of Object.keys(B.per_env[e.id].levels)) for (const s of e.seeds) {
  const tr = rpTrace(RD, data.train, { kind: 'ref', env: e.id, seed: s, level: +lv }), bs = B.per_env[e.id].levels[lv].by_seed.find((x) => x[0] === s);
  rpRef++;
  if (!(bs && bs[1] === (tr.success ? 1 : 0) && bs[2] === tr.collected && bs[3] === tr.steps && Math.abs(bs[4] - tr.ret) < 0.006
    && tr.frames.length === tr.steps + 1 && tr.mode === 'policy')) rpBad.push([e.id, lv, s]);
}
ok(`replay: a reference trace re-run step by step equals the registry's MEASURED per-seed row on every env, level and seed (${rpRef} traces: success, items, steps, return)`,
  rpRef === B.totals.runs * nLevels / rk.length && rpBad.length === 0, rpBad.slice(0, 5));
const rpCmp = rk.map((e) => { const emb = RD.embodiments[e.embodiments[0]], ep = PC.rollout(e, emb, e.seeds[2], data.train, 'lab', 1),
  tr = rpTrace(RD, data.train, { kind: 'ref', env: e.id, seed: e.seeds[2], level: 1 });
  return JSON.stringify(tr.samples) === JSON.stringify(ep.samples) && tr.ret === ep.outcome.return && tr.steps === ep.steps
    && ep.samples.every((x) => { const f = tr.frames[x.i]; return Math.round(f.e * 1000) / 1000 === x.pose[0] && Math.round(f.n * 1000) / 1000 === x.pose[1]; }); });
ok('replay: the frames the viewer scrubs are the rollout: every stored sample pose sits on its frame, samples byte-identical, same return and steps (4 envs)',
  rpCmp.every(Boolean), rpCmp);
const keptRef = { t: '2026-10-12T00:00:00Z', ...PC.rollout(rk[1], RD.embodiments[rk[1].embodiments[0]], 3, data.train, 'lab', 1) };
const rKept = rpTrace(RD, data.train, { kind: 'ep', ep: keptRef });
ok(`replay: a recorded scripted episode read back from the store replays exactly (mode ${rKept.mode}, gap ${rKept.drift} m, return ${rKept.ret})`,
  rKept.mode === 'policy' && rKept.exact && rKept.drift === 0 && rKept.ret === keptRef.outcome.return);
/* a human-style episode: constant keys held for 37 steps then Stop, sampled the way the UI samples it */
const hEnv = rk[0], hEmb = RD.embodiments[hEnv.embodiments[0]], hst = PC.reset(hEnv, hEmb, 4, 1), hs = [];
for (let i = 0; i < 37; i++) { const a = { v: hEmb.limits.v_max_ms, w: i < 20 ? 0.6 : -0.4 }; if (hst.step % 2 === 0) hs.push(PC.sample(hst, a)); PC.step(hst, a); }
const hum = { t: '2026-10-12T00:00:00Z', ...PC.episode(hst, 'human', 'lab', hs, data.train) }, rH = rpTrace(RD, data.train, { kind: 'ep', ep: hum });
ok(`replay: a recorded human episode (held keys, stopped at ${hum.steps} steps) is re-simulated from its samples with every pose reproduced (mode ${rH.mode}, gap ${rH.drift} m)`,
  rH.mode === 'held' && rH.steps === hum.steps && rH.exact && rH.done === 'stopped' && rH.frames.length === hum.steps + 1);
const humX = JSON.parse(JSON.stringify(hum)); humX.samples[5].pose[0] += 0.5;
const rX = rpTrace(RD, data.train, { kind: 'ep', ep: humX });
ok(`replay: a recording whose poses disagree with its actions is reported, not hidden (gap ${rX.drift.toFixed(3)} m, not exact)`, !rX.exact && rX.drift >= 0.499);

/* ---- wave 16 batch B: the ADDED litter-sort level 4 'reachable' on the page ---- */
{ const S4 = B.per_env['world.litter-sort'].levels['4'], F4 = S4 && S4.feasibility;
  ok(`level 4 reachable: the page prints its own bound and result from the registry (feasible ${F4 && F4.feasible_seeds}/${B.seeds.length}, item bound ${F4 && F4.items_bound}, success ${S4 && S4.success}/${S4 && S4.runs}, items ${S4 && S4.items})`,
    S4 && S4.name === 'reachable' && page.includes(`<b data-reach-feas>${F4.feasible_seeds} / ${B.seeds.length}</b>`) && page.includes(`<b data-reach-ibound>${F4.items_bound}</b>`)
    && page.includes(`<b data-reach-success>${S4.success} / ${S4.runs}</b>`) && page.includes(`<b data-reach-items>${S4.items}</b>`)
    && Object.values(I).every((L) => typeof L.strings['robo.bench.reach'] === 'string' && L.strings['robo.bench.reach'].trim()));
  ok('level 4 reachable: it has a table row and a chart bar, the sandbox offers it as practice (Record off), and the replay viewer re-runs it to the stored row',
    page.includes('data-bench="world.litter-sort" data-level="4"') && chartSrc.includes('data-chart-level="4" data-chart-success="' + S4.success + '"')
    && data.robo.envs['world.litter-sort'].curriculum.levels[3].name === 'reachable' && !data.robo.envs['world.litter-sort'].curriculum.record_levels.includes(4)
    && S4.by_seed.every((b) => { const tr = rpTrace(RD, data.train, { kind: 'ref', env: 'world.litter-sort', seed: b[0], level: 4 });
      return tr.success === (b[1] === 1) && tr.collected === b[2] && tr.steps === b[3]; })); }

/* ---- wave 16 batch C: no team codename ships in a public page ---- */
{ const CODENAME = /\bROBO[A-Z_]*/g, pages = ['trade_craft_robotics.html', 'trade_craft_parishes.html', 'trade_craft_bay.html', 'trade_craft_contribute.html', 'trade_craft_verify.html'];
  const hits = pages.flatMap((f) => (existsSync(join(HERE, f)) ? [...new Set(readFileSync(join(HERE, f), 'utf8').match(CODENAME) || [])].map((m) => f + ': ' + m) : [f + ': missing']));
  ok(`no "ROBO" codename token (markers, ids, comments) in the built robotics, parish, Bay, contribute and verify pages (${pages.length} pages)`, hits.length === 0, hits); }

/* ---- browser (opt-in) ---- */
const barg = process.argv.find((a) => a === '--browser' || a.startsWith('--browser='));
if (barg) {
  const { spawn } = await import('node:child_process');
  let base = barg.includes('=') ? barg.split('=').slice(1).join('=') : null, srv = null;
  if (!base) { const port = 18700 + (process.pid % 200); srv = spawn('python3', ['-m', 'http.server', String(port), '--bind', '127.0.0.1'], { cwd: HERE, stdio: 'ignore' });
    base = `http://127.0.0.1:${port}`; await new Promise((r) => setTimeout(r, 900)); }
  const { chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs');
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const errs = [];
  try {
    for (const vp of [{ width: 1440, height: 900, n: 'desktop' }, { width: 390, height: 844, n: 'phone' }]) {
      const ctx = await b.newContext({ viewport: { width: vp.width, height: vp.height } }), pg = await ctx.newPage();
      pg.on('pageerror', (e) => errs.push(vp.n + ': ' + e.message)); pg.on('console', (m) => { if (m.type() === 'error') errs.push(vp.n + ' console: ' + m.text()); });
      const reqs = []; pg.on('request', (r) => { if (!r.url().startsWith(base)) reqs.push(r.url()); });
      await pg.goto(base + '/trade_craft_robotics.html', { waitUntil: 'load' }); await pg.waitForFunction(() => window.__robokit && window.__roboPage);
      const before = await pg.evaluate(() => ({ n: document.querySelector('[data-an="count"]').textContent, empty: document.getElementById('robo-an-empty').hidden }));
      const px = await pg.evaluate(() => { const c = document.getElementById('robo-canvas'), d = c.getContext('2d').getImageData(c.width / 2, c.height / 2, 1, 1).data; return [d[0], d[1], d[2]]; });
      ok(`browser ${vp.n}: the robot is drawn at the spawn (canvas centre pixel ${px})`, px[0] > 150);
      const run = await pg.evaluate(async () => { const k = window.__robokit; k.reset('world.litter-sort', 1, 1); k.record(true); const ep = k.runRef();
        await new Promise((r) => setTimeout(r, 1700)); const q = (s) => document.querySelector(s).textContent;
        return { steps: ep.steps, ok: ep.outcome.success, n: q('[data-an="count"]'), st: q('[data-an="steps"]'), su: q('[data-an="success"]'), empty: document.getElementById('robo-an-empty').hidden,
          bins: document.querySelectorAll('#robo-an-hist .an-row').length, card: JSON.parse(q('#robo-an-card')), kept: k.episodes().length }; });
      ok(`browser ${vp.n}: an empty device shows the empty note, then one recorded reference episode fills the panel (${run.n} episode, ${run.st} steps, card ${run.card.episodes})`,
        before.n === '0' && before.empty === false && run.kept === 1 && run.n === '1' && run.st === String(run.steps) && run.su === (run.ok ? '1' : '0') + ' / 1'
        && run.empty === true && run.bins === 9 && run.card.schema === 'tc-dataset/1' && run.card.episodes === 1 && run.card.provenance.trained_models === 0);
      const lv = await pg.evaluate(() => { const k = window.__robokit; k.reset('world.gate-drive', 2, 2); const a = { level: k.state().level, rec: document.getElementById('robo-rec').disabled, note: !document.getElementById('robo-lvlnote').hidden, can: k.canRecord() };
        k.reset('world.gate-drive', 2, 1); return { ...a, rec1: document.getElementById('robo-rec').disabled }; });
      ok(`browser ${vp.n}: level 2 is practice (Record disabled, note shown); level 1 records again`, lv.level === 2 && lv.rec && lv.note && !lv.can && !lv.rec1);
      /* wave 16 B2: the episode replay viewer, driven in the page */
      const rp0 = await pg.evaluate(() => { const tr = window.__roboReplay.trace(); return { env: tr.env.id, seed: tr.seed, level: tr.level, steps: tr.steps, ret: tr.ret,
        max: document.getElementById('robo-rp-k').max, read: document.getElementById('robo-rp-read').textContent }; });
      const b0 = B.per_env[rp0.env].levels[String(rp0.level)].by_seed.find((x) => x[0] === rp0.seed);
      ok(`browser ${vp.n}: replay opens on a reference run equal to the registry row (${rp0.env} seed ${rp0.seed} L${rp0.level}: ${rp0.steps} steps, scrubber 0..${rp0.max})`,
        b0 && rp0.steps === b0[3] && Math.abs(rp0.ret - b0[4]) < 0.006 && rp0.max === String(rp0.steps) && rp0.read.includes(' 0 / ' + rp0.steps));
      const rp1 = await pg.evaluate(() => { const R = window.__roboReplay, tr = R.loadRef('world.litter-sort', 3, 4), f = R.seek(120), cv = document.getElementById('robo-rp-arena');
        const W = cv.width, s = W / (2 * tr.env.world.arena_half_m), px = cv.getContext('2d').getImageData(Math.round(W / 2 + f.e * s), Math.round(W / 2 - f.n * s), 1, 1).data;
        const rng = document.getElementById('robo-rp-k'); rng.value = '60'; rng.dispatchEvent(new Event('input', { bubbles: true }));
        const ac = document.getElementById('robo-rp-act'), d = ac.getContext('2d').getImageData(0, 0, ac.width, ac.height).data; let blue = 0;
        for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i] - 0x39) < 12 && Math.abs(d[i + 1] - 0x87) < 12 && Math.abs(d[i + 2] - 0xe5) < 12) blue++;
        return { steps: tr.steps, ok: tr.success, got: tr.collected, px: [px[0], px[1], px[2]], k: R.k(), rk: document.getElementById('robo-rp-read').dataset.k, blue,
          read: document.getElementById('robo-rp-read').textContent, lvl: document.getElementById('robo-rp-level').value }; });
      const b4 = B.per_env['world.litter-sort'].levels['4'].by_seed.find((x) => x[0] === 3);
      ok(`browser ${vp.n}: replay of litter-sort level 4 seed 3 equals the stored row (${rp1.steps} steps, ${rp1.got} items); the robot is drawn at the scrubbed frame (pixel ${rp1.px})`,
        rp1.steps === b4[3] && rp1.got === b4[2] && rp1.ok === (b4[1] === 1) && rp1.px[0] > 180 && rp1.px[1] < 140 && rp1.lvl === '4');
      ok(`browser ${vp.n}: the scrubber moves the replay (input -> step ${rp1.k}), the readout follows, and the actions chart is drawn (${rp1.blue} px of the v series)`,
        rp1.k === 60 && rp1.rk === '60' && rp1.read.includes(' 60 / ' + rp1.steps) && rp1.blue > 50);
      const rp2 = await pg.evaluate(async () => { const R = window.__roboReplay, b = document.getElementById('robo-rp-play'); R.seek(0); b.click();
        await new Promise((r) => setTimeout(r, 400)); const mid = { k: R.k(), on: b.getAttribute('aria-pressed') }; b.click(); const k2 = R.k();
        await new Promise((r) => setTimeout(r, 200)); return { ...mid, off: b.getAttribute('aria-pressed'), still: R.k() === k2 }; });
      ok(`browser ${vp.n}: Play advances the replay (${rp2.k} steps in 0.4 s) and Pause holds it`, rp2.k > 0 && rp2.on === 'true' && rp2.off === 'false' && rp2.still);
      const rp3 = await pg.evaluate(() => { const k = window.__robokit, R = window.__roboReplay; k.reset('world.gate-drive', 2, 1); k.record(true);
        k.drive({ v: 1.5, w: 0.3 }, 41); const ep = k.stop(), n = R.list(), tr = R.loadMine(n - 1), opt = document.getElementById('robo-rp-src');
        const ref = R.loadMine(0);
        return { n, kept: k.episodes().length, actor: tr.mode, exact: tr.exact, drift: tr.drift, steps: tr.steps, epSteps: ep && ep.steps, opts: opt.options.length,
          mode: document.getElementById('robo-rp-mode').textContent, rmode: ref.mode, rexact: ref.exact, none: document.getElementById('robo-rp-none').hidden }; });
      ok(`browser ${vp.n}: recorded episodes on this device are listed (${rp3.n}); a human run replays from its samples (mode ${rp3.actor}, gap ${rp3.drift} m) and a kept reference run re-runs exactly`,
        rp3.n === rp3.kept && rp3.n >= 2 && rp3.opts === rp3.n + 1 && rp3.actor === 'held' && rp3.exact && rp3.drift === 0 && rp3.steps === rp3.epSteps
        && rp3.rmode === 'policy' && rp3.rexact && rp3.none === true && rp3.mode.length > 10);
      ok(`browser ${vp.n}: no request leaves the page's origin (${reqs.length})`, reqs.filter((u) => !/fonts\.(googleapis|gstatic)\.com/.test(u)).length === 0, reqs);
      const ov = await pg.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      ok(`browser ${vp.n}: no horizontal scroll (${ov} px)`, ov <= 0);
      await ctx.close();
    }
    const ctx = await b.newContext({ viewport: { width: 390, height: 844 } }), pg = await ctx.newPage();
    pg.on('pageerror', (e) => errs.push('classroom: ' + e.message));
    await pg.goto(base + '/trade_craft_robotics.html?classroom=1', { waitUntil: 'load' }); await pg.waitForFunction(() => window.__robokit);
    const cl = await pg.evaluate(() => { const k = window.__robokit; k.record(true); k.runRef(); return { rec: document.getElementById('robo-rec').disabled, exp: document.getElementById('robo-export').disabled, kept: k.episodes().length }; });
    ok('browser classroom: Record and Export are disabled and a reference run keeps nothing', cl.rec && cl.exp && cl.kept === 0);
    await ctx.close();
  } finally { await b.close(); if (srv) srv.kill(); }
  ok('browser: zero page errors', errs.length === 0, errs);
}

console.log(`test_robotics: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
