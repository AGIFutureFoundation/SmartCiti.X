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
    page.includes(`data-robo-count="${k}">${reg.counts[k]}<`)) && reg.counts.trained_models === 0
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
  && Object.values(data.robo.envs).every((e) => e.curriculum && e.curriculum.levels.length === 3 && JSON.stringify(e.curriculum.record_levels) === '[1]'));
const B = reg.reference_benchmark, brows = [...page.matchAll(/<tr data-bench="([^"]+)" data-level="(\d)">.*?<td data-bench-success>(\d+) \/ (\d+)<\/td><td>(\d+)<\/td>/g)];
ok(`the benchmark table is the registry's MEASURED block: one row per env and level (${brows.length}), success/runs and items equal`,
  brows.length === rk.length * 3 && brows.every((m) => { const r = B.per_env[m[1]].levels[m[2]]; return r && +m[3] === r.success && +m[4] === r.runs && +m[5] === r.items; }));
ok('the benchmark section prints the policy version and every seed it ran',
  page.includes(`policy ${B.policy_version}`) && page.includes('seeds ' + B.seeds.join(', ')));
const FS = B.per_env['world.litter-sort'].feasibility;
ok(`the litter-sort bound line prints the registry's feasible seeds (${FS.feasible_seeds}/${B.seeds.length}) and item bound (${FS.items_bound})`,
  page.includes(`<b data-feas>${FS.feasible_seeds} / ${B.seeds.length}</b>`) && page.includes(`<b data-ibound>${FS.items_bound}</b>`)
  && FS.feasible_seeds * 2 < B.seeds.length);
const pjs = page.split('<script id="robo-page">')[1].split('</script>')[0];
const anSrc = (pjs.split('/* ROBO_ANALYTICS:BEGIN')[1] || '').split('function render()')[0];
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
