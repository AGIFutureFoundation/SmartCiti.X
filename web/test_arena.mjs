/* web/test_arena.mjs - the model arena on the Robotics lab page (web/trade_craft_robotics.html, section #model-arena).
 * Headless: the page carries the measured policy block verbatim, the pinned BC weights, the registry's leaderboard and
 * a card for every policy; the arena script stores and sends nothing; and the page's own code (SIM_CORE + the policy
 * block, lifted from the built page) reproduces the harness's measured rows. --browser (or --browser=<base url>) also
 * drives the page in Chromium (serving web/ itself on 127.0.0.1 when no url is given). Run it under flock $SP/chromium.lock. */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url)), ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (m, c, extra) => { let v = false; try { v = typeof c === 'function' ? c() : c; } catch (e) { m += ' [threw: ' + e.message + ']'; }
  if (v) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m + (extra ? ' ' + JSON.stringify(extra).slice(0, 300) : '')); } };
const J = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));
const page = readFileSync(join(HERE, 'trade_craft_robotics.html'), 'utf8');
const AR = J('robotics/arena/registry/arena.json'), MD = J('robotics/arena/registry/models.json'), reg = J('robotics/registry/robotics.json');
const between = (s, a, b) => { const i = s.indexOf(a), j = s.indexOf(b, i); return i < 0 || j < 0 ? '' : s.slice(i, j + b.length); };
const pol = readFileSync(join(ROOT, 'robotics/arena/policies.js'), 'utf8');
const POLBLOCK = between(pol, '/* MODEL_ARENA_POLICIES:BEGIN', '/* MODEL_ARENA_POLICIES:END */');
const sec = between(page, '<section class="box" aria-labelledby="robo-h-arena"', '</section>');
const ajs = between(page, '/* MODEL_ARENA:BEGIN', '/* MODEL_ARENA:END */');
const adata = JSON.parse((page.match(/<script type="application\/json" id="model-arena-data">([\s\S]*?)<\/script>/) || [, 'null'])[1]);

ok('the page carries the model-arena section, its data and its script (neutral marker MODEL_ARENA)',
  sec.includes('id="model-arena" data-model-arena') && ajs.length > 2000 && adata && /<script id="model-arena-js">/.test(page) && (page.match(/id="model-arena"/g) || []).length === 1);
ok('the policy block on the page is robotics/arena/policies.js verbatim (the code the harness measured)',
  POLBLOCK.length > 3000 && page.includes(POLBLOCK) && between(page, '/* MODEL_ARENA_POLICIES:BEGIN', '/* MODEL_ARENA_POLICIES:END */') === POLBLOCK);
ok('the BC weights on the page, one set per model (bc and bcg), are the model registry\'s, and match their sha256 pins', () =>
  MD.models.length === 2 && JSON.stringify(Object.keys(adata.models).sort()) === JSON.stringify(MD.models.map((m) => m.policy).sort())
  && MD.models.every((m) => JSON.stringify(adata.models[m.policy]) === JSON.stringify(m.weights) && adata.models_sha256[m.policy] === m.weights_sha256
    && createHash('sha256').update(JSON.stringify(adata.models[m.policy])).digest('hex') === m.weights_sha256));
ok('the leaderboard is the registry\'s measured table, row for row (rank, policy, success rate, win rate), and says which seeds', () => {
  const rows = [...sec.matchAll(/data-arena-rank="(\d+)" data-arena-policy="([a-z]+)"[\s\S]*?data-arena-success="([0-9.]+)"[\s\S]*?data-arena-win="([0-9.]+)"/g)];
  return rows.length === AR.leaderboard.rows.length && rows.every((r, i) => { const b = AR.leaderboard.rows[i];
    return +r[1] === b.rank && r[2] === b.policy && +r[3] === b.success_rate.mean && +r[4] === b.win_vs_ref.rate; })
    && sec.includes('seeds ' + AR.leaderboard.seeds.join(', ')) && AR.leaderboard.table === 'held_out'; });
ok('every policy that plays has a card on the page; each BC card is the exact honest sentence (both models)', () =>
  adata.policies.every((p) => sec.includes(`data-arena-card="${p}"`) && adata.cards[p] && adata.cards[p].kind)
  && MD.models.every((m) => sec.includes(m.card.what.replace(/'/g, '&#x27;'))) && JSON.stringify(adata.policies) === JSON.stringify(AR.tables.held_out.policies));
ok('the page prints the litter-sort items-binned table of the held-out seeds, one row per policy, numbers copied from the registry (the second policy included, whatever its number is)', () => {
  const rows = [...sec.matchAll(/data-arena-binned-policy="([a-z]+)"><td>[^<]*<\/td><td data-arena-binned="(\d+)">(\d+) \/ (\d+)<\/td><td data-arena-binned-mean="([0-9.]+)">/g)], S = AR.tables.held_out.sort.summary;
  return rows.length === AR.tables.held_out.policies.length && rows.length === 5 && rows.every((r) => S[r[1]] && +r[2] === S[r[1]].items_binned && +r[3] === S[r[1]].items_binned && +r[4] === S[r[1]].items_total && +r[5] === S[r[1]].binned_per_episode.mean)
    && rows.some((r) => r[1] === 'bcg') && sec.includes('id="arena-binned"'); });
ok('beside the board the page says the second learned policy matches its teacher and does not beat it, and the registry still bears that out (overlapping success intervals, equal items binned)', () => {
  const r = Object.fromEntries(AR.leaderboard.rows.map((x) => [x.policy, x.success_rate])), S = AR.tables.held_out.sort.summary;
  const ov = r.bcg && r.scripted && r.bcg.ci95[0] <= r.scripted.ci95[1] && r.scripted.ci95[0] <= r.bcg.ci95[1];
  const p = ((sec.match(/<p class="muted" data-arena-vs-teacher>([\s\S]*?)<\/p>/) || [])[1] || '').replace(/<[^>]+>/g, '');
  return ov && S.bcg.items_binned === S.scripted.items_binned && /does not beat it/.test(p) && /overlaps/.test(p); });
ok('the arena script stores and sends nothing (no storage, no network APIs)', !/localStorage|sessionStorage|indexedDB|fetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket/.test(ajs + POLBLOCK));
ok('no language-model claim in the arena section (only "None is a language model" / "not a language model" may name one)',
  !/language model|\bLLM\b|\bGPT\b|chatbot/i.test(sec.replace(/None is a language model|not a language model/g, '')));
ok('no team codename in the page: "ARENA" appears only inside the neutral MODEL_ARENA markers (never as a bare word), no CLAW',
  !/\bARENA\b/.test(page) && !/\bCLAW\b/.test(page) && !/\$SP|\/tmp\//.test(sec + ajs));
ok('the 17 arena chrome keys exist in all 8 locales and ride with the page\'s i18n block', () => {
  const I = JSON.parse(page.match(/<script type="application\/json" id="robo-i18n">([\s\S]*?)<\/script>/)[1]);
  const keys = [...new Set([...sec.matchAll(/data-i18n="(robo\.(?:h\.arena|arena\.[a-z]+))"/g)].map((m) => m[1]))];
  return keys.length >= 15 && Object.keys(I).length === 8 && Object.values(I).every((L) => keys.concat(['robo.arena.resume']).every((k) => typeof L.strings[k] === 'string' && L.strings[k].length > 0)); });
// the page's own code, lifted from the built page and run here: every seeded match reproduces the harness's measured rows
const core = between(page, '/* SIM_CORE:BEGIN', '/* SIM_CORE:END */');
const RC = new Function(core + '\nreturn RoboCore;')(), AP = new Function(between(page, '/* MODEL_ARENA_POLICIES:BEGIN', '/* MODEL_ARENA_POLICIES:END */') + '\nreturn ArenaPolicies;')();   // lifted from the page, not the source
const dec = (w) => { const d = (a) => a.map((x) => x / w.scale); return { in: w.in, hidden: w.hidden, out: w.out, W1: d(w.W1), b1: d(w.b1), W2: d(w.W2), b2: d(w.b2) }; };
const sched = (m) => { const r = AP.mulberry32(AP.hash('model-arena|' + m)), tk = adata.tasks[Math.floor(r() * adata.tasks.length)];
  return { env: tk[0], level: tk[1], seed: adata.seeds[Math.floor(r() * adata.seeds.length)] }; };
ok('the arena schedule matches the page script (same seeded formula) and covers several tasks in 12 matches', () =>
  ajs.includes("ArenaPolicies.mulberry32(ArenaPolicies.hash('model-arena|' + m))") && new Set([...Array(12).keys()].map((m) => sched(m).env)).size >= 3);
{
  const rows = new Map(Object.values(AR.tables).flatMap((t) => t.runs).map((r) => [r.slice(0, 4).join('|'), r]));
  let cmp = 0, same = 0;
  for (let m = 0; m < 12; m++) { const s = sched(m), env = reg.envs[s.env], emb = reg.embodiments[env.embodiments[0]];
    for (const p of adata.policies) { const r = rows.get([p, s.env, s.level, s.seed].join('|')); if (!r) continue;
      const act = AP.make(p, { RoboCore: RC, env, seed: s.seed, level: s.level, model: adata.models[p] ? dec(adata.models[p]) : null }), st = RC.reset(env, emb, s.seed, s.level);
      while (!st.done) RC.step(st, act(st));
      cmp++; if ((st.done !== 'cap' ? 1 : 0) === r[4] && st.step === r[5] && Math.abs(st.ret - r[8]) < 0.0006) same++; } }
  ok(`the page's code reproduces the harness's measured row for every match policy with a row (${same}/${cmp} over the first 12 matches)`, cmp >= 30 && same === cmp);
}

/* ---- browser (opt-in) ---- */
const barg = process.argv.find((a) => a === '--browser' || a.startsWith('--browser='));
if (barg) {
  const { spawn } = await import('node:child_process');
  let base = barg.includes('=') ? barg.split('=').slice(1).join('=') : null, srv = null;
  if (!base) { const port = 18900 + (process.pid % 90); srv = spawn('python3', ['-m', 'http.server', String(port), '--bind', '127.0.0.1'], { cwd: HERE, stdio: 'ignore' });
    base = `http://127.0.0.1:${port}`; await new Promise((r) => setTimeout(r, 900)); }
  const { chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs');
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const errs = [];
  try {
    for (const vp of [{ width: 1440, height: 900, n: 'desktop' }, { width: 390, height: 844, n: 'phone' }]) {
      const ctx = await b.newContext({ viewport: { width: vp.width, height: vp.height } }), pg = await ctx.newPage();
      pg.on('pageerror', (e) => errs.push(vp.n + ': ' + e.message)); pg.on('console', (m) => { if (m.type() === 'error') errs.push(vp.n + ' console: ' + m.text()); });
      const reqs = []; pg.on('request', (r) => { if (!r.url().startsWith(base)) reqs.push(r.url()); });
      await pg.goto(base + '/trade_craft_robotics.html', { waitUntil: 'load' }); await pg.waitForFunction(() => window.__modelArena);
      const t0 = await pg.evaluate(() => ({ m: window.__modelArena.match(), st: window.__modelArena.states().map((s) => s.steps), store: Object.keys(localStorage).sort() }));
      await pg.waitForTimeout(1500);
      const t1 = await pg.evaluate(() => ({ m: window.__modelArena.match(), st: window.__modelArena.states().map((s) => s.steps), rows: document.querySelectorAll('#arena-score tbody tr').length,
        task: document.getElementById('arena-task').textContent, playing: window.__modelArena.playing() }));
      ok(`browser ${vp.n}: the arena runs by itself - every policy steps in one shared match (${t0.st} -> ${t1.st}), ${t1.rows} scoreboard rows, task "${t1.task}"`,
        t1.playing && t1.st.every((x, i) => x > t0.st[i] || t1.m > t0.m) && t1.rows === AR.tables.held_out.policies.length && t1.task.length > 5);
      const run = await pg.evaluate(() => { const a = window.__modelArena; a.pause(); const m0 = a.match(); let ends = 0; for (let k = 0; k < 60 && ends < 3; k++) ends += a.step(100);
        return { m0, m: a.match(), tally: a.tally(), board: document.querySelectorAll('#arena-board tbody tr').length, store: Object.keys(localStorage).sort() }; });
      const played = Object.values(run.tally).map((x) => x.played);
      ok(`browser ${vp.n}: matches keep coming (${run.m0} -> ${run.m}); every policy plays every match and the tally adds up`,
        run.m >= run.m0 + 3 && played.every((x) => x === run.m) && Object.values(run.tally).reduce((a, x) => a + x.wins, 0) <= run.m);
      ok(`browser ${vp.n}: the leaderboard shows the registry's ${run.board} measured rows; the arena stored nothing (storage keys unchanged)`,
        run.board === AR.leaderboard.rows.length && JSON.stringify(run.store) === JSON.stringify(t0.store));
      const fin = await pg.evaluate(() => { const a = window.__modelArena, m = a.match(); let g = 0; while (a.match() === m && g++ < 700) a.step(1); return a.last(); });
      const rowOf = (p) => Object.values(AR.tables).flatMap((t) => t.runs).find((r) => r[0] === p && r[1] === fin.task.env && r[2] === fin.task.level && r[3] === fin.task.seed);
      const withRow = fin ? fin.states.filter((x) => rowOf(x.policy)) : [];
      ok(`browser ${vp.n}: a whole live match in the page equals the harness's measured rows (${fin && fin.task.env} L${fin && fin.task.level} seed ${fin && fin.task.seed}, ${withRow.length} policies with a row)`,
        withRow.length >= 3 && withRow.every((x) => { const r = rowOf(x.policy); return (x.success ? 1 : 0) === r[4] && x.steps === r[5] && Math.abs(x.ret - r[8]) < 0.0006; }), fin);
      const px = await pg.evaluate(() => { const c = document.getElementById('arena-world'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0;
        const C = [[0x39, 0x87, 0xe5], [0xd9, 0x59, 0x26], [0x19, 0x9e, 0x70], [0xb0, 0x7c, 0xf0]];   // scripted, greedy, bc, bcg (robots share the spawn at a match start)
        for (let i = 0; i < d.length; i += 4) if (C.some((c) => d[i] === c[0] && d[i + 1] === c[1] && d[i + 2] === c[2])) n++; return n; });
      ok(`browser ${vp.n}: the shared world is drawn with the policies' robots in it (${px} px of their colours)`, px > 20);
      ok(`browser ${vp.n}: no request leaves the page's origin (${reqs.length})`, reqs.filter((u) => !/fonts\.(googleapis|gstatic)\.com/.test(u)).length === 0, reqs);
      const ov = await pg.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      ok(`browser ${vp.n}: no horizontal scroll with the arena on the page (${ov} px)`, ov <= 0);
      await ctx.close();
    }
    const ctx = await b.newContext({ viewport: { width: 390, height: 844 } }), pg = await ctx.newPage();
    pg.on('pageerror', (e) => errs.push('classroom: ' + e.message));
    await pg.goto(base + '/trade_craft_robotics.html?classroom=1', { waitUntil: 'load' }); await pg.waitForFunction(() => window.__modelArena);
    const cl = await pg.evaluate(() => { const before = Object.keys(localStorage).length; window.__modelArena.step(800);
      return { note: !document.getElementById('arena-class').hidden, m: window.__modelArena.match(), after: Object.keys(localStorage).length, before }; });
    ok(`browser classroom: the arena plays (${cl.m} matches), shows the play-only note and records nothing`, cl.note && cl.m >= 1 && cl.after === cl.before);
    await ctx.close();
  } finally { await b.close(); if (srv) srv.kill(); }
  ok('browser: zero page errors', errs.length === 0, errs);
}
console.log(`test_arena: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
