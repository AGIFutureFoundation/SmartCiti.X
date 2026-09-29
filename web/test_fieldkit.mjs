/* web/test_fieldkit.mjs - seasons & harvest kit (web/fieldkit.py), checked.
 *   node web/test_fieldkit.mjs              core + both built pages (no browser)
 *   node web/test_fieldkit.mjs --browser    also plant -> harvest in Chromium on the parish and Bay pages
 *                                           (run under flock $SP/chromium.lock; serves the repo on 127.0.0.1)
 * Prints `  ok ` per check, FAIL at column 0; exits non-zero on failure.
 */
import { readFileSync } from 'node:fs';
import { execFileSync, spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m); } };
const read = (p) => readFileSync(join(ROOT, p), 'utf8');
const REG = JSON.parse(read('seasons/registry/seasons.json'));
const PY = read('web/fieldkit.py');
console.log('web/test_fieldkit.mjs');

/* ---- the pure core, carried byte-for-byte from the kit ---- */
const JS = execFileSync('python3', [join(HERE, 'fieldkit.py'), '--emit'], { encoding: 'utf8' });
const core = JS.slice(JS.indexOf('/* FIELDS_CORE:BEGIN'), JS.indexOf('/* FIELDS_CORE:END */'));
ok(core.length > 1000, 'core: FIELDS_CORE block found in the kit');
const FieldCore = new Function(core + '\nreturn FieldCore;')();
const dataFor = (region) => ({
  clock: REG.game_clock, calendar: REG.calendar[region], safety: REG.safety,
  tasks: REG.tasks.filter((t) => t.region === region),
});
const LA = dataFor('louisiana'), BA = dataFor('bay');

{ const ck = FieldCore.clock(LA); FieldCore.setMonth(ck, 12); FieldCore.setSpeed(ck, '16x');
  const sp = REG.game_clock.speeds.find((s) => s.id === '16x').s_per_day;
  FieldCore.tick(ck, REG.game_clock.days_per_month * sp + 0.001);
  ok(ck.month === 1, 'clock: a full game month at 16x wraps December to January');
  FieldCore.setSpeed(ck, 'pause'); const t0 = ck.t; FieldCore.tick(ck, 100);
  ok(ck.t === t0, 'clock: pause stops game time');
  let threw = false; try { FieldCore.setSpeed(ck, '99x'); } catch (e) { threw = /unknown speed/.test(e.message); }
  ok(threw, 'clock: an unknown speed throws by name (fail closed)'); }

ok([...Array(12)].every((_, i) => FieldCore.inSeason(LA, i + 1).map((t) => t.id).join() === REG.calendar.louisiana.months[i].in_season.join()),
   'board: in-season lists equal the registry calendar for all 12 game months');

/* play the rice task through with the window midpoints; then an early press and a late press */
function playThrough(data, taskId, month, plot) {
  const ck = FieldCore.clock(data); FieldCore.setMonth(ck, month);
  const r = FieldCore.start(data, ck, plot, taskId); if (!r.ok) return r;
  const st = r.st, t = FieldCore.task(data, taskId), log = [];
  for (const s of t.stages) { const [lo, hi] = s.window_days; ck.t = st.last + (lo + hi) / 2; const a = FieldCore.act(data, st, ck); log.push(a); }
  return { ok: true, log, st };
}
{ const a = playThrough(LA, 'rice', 4, 'plot-22071-1'), b = playThrough(LA, 'rice', 4, 'plot-22071-1');
  ok(a.ok && a.log.length === 6 && a.log.slice(0, 5).every((x) => x.ok && !x.done) && a.log[5].done === true,
     'rice: six stages, each done inside its window, the last one harvests');
  ok(JSON.stringify(a.log) === JSON.stringify(b.log) && a.log[5].points === 18, `rice: deterministic - same play, same log (${a.log[5].points} play points at the window midpoints)`); }
{ const ck = FieldCore.clock(LA); FieldCore.setMonth(ck, 4);
  const st = FieldCore.start(LA, ck, 'plot-22071-1', 'rice').st, RS = REG.tasks.find((t) => t.id === 'rice').stages;
  for (const s of RS.slice(0, 2)) { ck.t = st.last + (s.window_days[0] + s.window_days[1]) / 2; FieldCore.act(LA, st, ck); }
  const at = st.i; ck.t = st.last + RS[2].window_days[1] + 5; const late = FieldCore.act(LA, st, ck);
  ok(at === 2 && !late.ok && late.why === 'late' && st.i === 0 && st.points === 0, 'window: too late (at stage 3) restarts the task from its first stage');
  const st2 = FieldCore.start(LA, ck, 'plot-22071-1', 'rice').st; FieldCore.act(LA, st2, ck);   // stage 1 opens at 0
  const early = FieldCore.act(LA, st2, ck);
  ok(!early.ok && early.why === 'early' && st2.i === 1, 'window: too early waits and keeps the stage'); }
{ const ck = FieldCore.clock(LA); FieldCore.setMonth(ck, 1);
  ok(FieldCore.start(LA, ck, 'plot-22071-1', 'rice').why === 'off_season', 'season: rice cannot start in a game month it is not in season');
  FieldCore.setMonth(ck, 7);
  ok(FieldCore.start(LA, ck, null, 'rice').why === 'no_plot' && FieldCore.start(LA, ck, null, 'storm-drill').ok, 'plots: crops need a plot; events run anywhere'); }
ok(FieldCore.tip(LA, 7, 4, 'plot-22071-1', 'rice') === FieldCore.tip(LA, 7, 4, 'plot-22071-1', 'rice')
   && Object.values(REG.safety).includes(FieldCore.tip(LA, 7, 4, 'plot-22071-1', 'rice')), 'seeded: the same seed, month and plot show the same safety tip');
ok(playThrough(BA, 'orchard', 7, 'plot-06001-1').log.at(-1).done === true, 'bay: the orchard task plays through to harvest');
ok(FieldCore.questId(REG.tasks.find((t) => t.id === 'rice')) === 'treasure-fields-harvest-rice'
   && FieldCore.questId(REG.tasks.find((t) => t.id === 'storm-drill')) === 'treasure-fields-event-storm-drill', 'quests: task -> treasure id per GAMES_CONTRACT naming');

/* ---- kit source rules ---- */
ok(!/\?\?/.test(PY) && !/\.get\([^()]*,/.test(PY), 'fail closed: no ?? and no .get(k, default) anywhere in fieldkit.py (kit, scene mount, Python)');
ok(/tc-fields-v1/.test(PY) && !/setItem\(['"]tc-quests/.test(JS) && /T\.find\(id\)/.test(JS), 'storage: own key tc-fields-v1; reports through TCQuests.find, never writes tc-quests');
{ const Q = JSON.parse(read('quests/source/fields.json'));
  const ids = new Set(Q.entries.map((e) => e.id)), want = REG.tasks.map((t) => FieldCore.questId(t));
  ok(Q.from === 'FIELDS' && want.every((w) => ids.has(w)), `quests: fields.json carries a treasure for every task (${want.length})`);
  ok(Q.entries.every((e) => /^(treasure|egg|side)-fields-/.test(e.id) && e.reward.badge === 'badge-' + e.id && e.reveal.length >= 20
     && ['parishes', 'bay'].includes(e.world) && !/\d/.test(e.reveal)), 'quests: owner prefix, badge ids, number-free reveal lines, kit-fired worlds'); }

/* ---- both built pages ---- */
for (const [page, world, region] of [['web/trade_craft_parishes.html', 'parishes', 'louisiana'], ['web/trade_craft_bay.html', 'bay', 'bay']]) {
  const html = read(page), tag = `[${world}]`;
  const m = html.match(/<script type="application\/json" id="fields-data">([\s\S]*?)<\/script>/);
  const D = m ? JSON.parse(m[1]) : null;
  ok(D && D.world === world && D.region === region && D.stamp === REG.source_stamp, `${tag} page embeds the ${region} data at the current registry stamp`);
  ok(D && D.tasks.every((t) => t.region === region) && Object.values(REG.plots).filter((w) => w.region === region).length === Object.keys(D.plots).length,
     `${tag} only this region's tasks and plots are embedded`);
  ok((html.match(/<section class="fk" id="fields"/g) || []).length === 1 && (html.match(/id="fields-kit"/g) || []).length === 1, `${tag} one section, one kit`);
  const main = (html.match(/<script type="module" id="parishes-main">([\s\S]*?)<\/script>/) || [])[1] || '';
  ok((main.match(/new THREE\.InstancedMesh\(new THREE\.BoxGeometry\(1, 1, 1\)/g) || []).length === 1 && /fkMesh\.visible = on && n > 0/.test(main),
     `${tag} the plots are ONE InstancedMesh, visible only while shown (0 draw calls hidden)`);
  const stage = html.slice(html.indexOf('<div id="stage"'), html.indexOf('{DEEP_PANEL}') > 0 ? html.indexOf('{DEEP_PANEL}') : html.indexOf('<p class="help" id="maplabel"'));
  ok(stage.includes('id="fk-board"') && /&quot;id&quot;: &quot;fields&quot;/.test(html), `${tag} the season board sits in the stage and is registered with the HUD layout manager`);
  ok(html.includes('approximate, game calendar') && html.includes('never a completion record') && html.includes('Louisiana Department of Wildlife and Fisheries'),
     `${tag} game-calendar label, play line and state-rules line are on the page`);
  const cat = JSON.parse(html.match(/<script type="application\/json" id="fields-i18n">([\s\S]*?)<\/script>/)[1]);
  const keys = Object.keys(cat.en.strings);
  ok(Object.keys(cat).length === 8 && Object.values(cat).every((c) => keys.every((k) => c.strings[k] && c.strings[k].trim())),
     `${tag} fields.* catalogue: 8 locales x ${keys.length} keys, none empty`);
  ok(Object.entries(cat).filter(([l]) => l !== 'en').every(([, c]) => keys.filter((k) => c.strings[k] === cat.en.strings[k]).length <= 1),
     `${tag} non-English fields.* values are translations (at most one shared token)`);
}

/* ---- browser: plant -> harvest, both pages ---- */
if (process.argv.includes('--browser')) {
  const { chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs');
  const port = 8700 + Math.floor(Math.random() * 200);
  const srv = spawn('python3', ['-m', 'http.server', String(port), '--bind', '127.0.0.1'], { cwd: ROOT, stdio: 'ignore' });
  await new Promise((r) => setTimeout(r, 700));
  const shots = process.env.FK_SHOTS || '';
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  try {
    for (const [page, world, task, month] of [['web/trade_craft_parishes.html', 'parishes', 'rice', 4], ['web/trade_craft_bay.html', 'bay', 'orchard', 7]]) {
      const tag = `[browser ${world}]`, pg = await browser.newPage({ viewport: { width: 1280, height: 800 } }), errs = [];
      pg.on('pageerror', (e) => errs.push(String(e)));
      await pg.goto(`http://127.0.0.1:${port}/${page}`, { waitUntil: 'load' });
      await pg.waitForFunction(() => document.documentElement.dataset.parishesReady === '1' && window.TCFields && window.__fields, null, { timeout: 60000 });
      const hidden = await pg.evaluate(() => ({ calls: window.__fields.drawCalls(), st: window.__fields.stats() }));
      ok(hidden.calls === 0 && !hidden.st.visible, `${tag} plots hidden: the kit adds ${hidden.calls} draw calls`);
      const plots = await pg.evaluate(() => window.__fields.plots());
      ok(plots.length > 0 && plots.every((p) => p.land === p.fips), `${tag} all ${plots.length} plots stand on land of the parish/county they name (parishAt)`);
      const run = await pg.evaluate(async ([task, month, plot]) => {
        const F = window.TCFields, sel = document.getElementById('fk-month'); sel.value = String(month); sel.dispatchEvent(new Event('change'));
        document.querySelector('#fk-speeds [data-speed="pause"]').click();
        const go = window.__fields.goto(plot); F.select(plot, task); document.getElementById('fk-start').click();
        const steps = [];
        for (let i = 0; i < 12 && F.state().run; i++) {
          const btn = document.getElementById('fk-step'), s = F.state().run, w = JSON.parse(JSON.stringify(s));
          const T = JSON.parse(document.getElementById('fields-data').textContent).tasks.find((x) => x.id === task);
          const [lo, hi] = T.stages[w.i].window_days; F.advance((lo + hi) / 2);
          await new Promise((r) => requestAnimationFrame(r)); btn.click(); steps.push(document.getElementById('fk-msg').textContent);
        }
        await new Promise((r) => setTimeout(r, 400));
        return { go, steps, log: F.state().log, shown: F.shown(), stats: window.__fields.stats(), calls: window.__fields.drawCalls(),
                 li: document.querySelectorAll('#fk-log li[data-log]').length, board: document.querySelectorAll('#fk-board-list li').length };
      }, [task, month, plots[0].id]);
      ok(run.log.length === 1 && run.log[0].task === task && run.li === 1, `${tag} ${task}: planted and harvested on ${plots[0].id}; one harvest-log row (${run.log[0] && run.log[0].points} play points)`);
      ok(run.shown && run.stats.visible && run.stats.instances >= 2 && run.calls === 1, `${tag} plots shown: ${run.stats.instances} instances, ${run.calls} draw call (instancing, measured)`);
      ok(run.board > 0, `${tag} the season board lists ${run.board} in-season tasks`);
      if (shots) {
        await pg.evaluate(() => document.getElementById('stage').scrollIntoView());
        await pg.screenshot({ path: `${shots}/FIELDS-${world}-stage.png` });
        await pg.evaluate(() => document.getElementById('fields').scrollIntoView());
        await pg.screenshot({ path: `${shots}/FIELDS-${world}-panel.png` });
      }
      const ov = await pg.evaluate(() => (window.__hud ? window.__hud.overlaps() : ['no hud']).filter((x) => x.includes('fields')));
      ok(ov.length === 0, `${tag} 1280x800: the season board overlaps no other HUD panel${ov.length ? ': ' + ov.join(', ') : ''}`);
      await pg.setViewportSize({ width: 390, height: 844 }); await pg.waitForTimeout(400);
      const ovp = await pg.evaluate(() => ({ o: window.__hud.overlaps().filter((x) => x.includes('fields')), compact: window.__hud.compact,
        list: getComputedStyle(document.getElementById('fk-board-list')).display, tap: Math.min(...[...document.querySelectorAll('#fields button, #fields select')].map((e) => e.getBoundingClientRect().height)) }));
      ok(ovp.o.length === 0 && ovp.list === 'none' && ovp.tap >= 44, `${tag} 390x844: board folds its list (${ovp.list}), no overlap, tap targets >= 44 px (min ${ovp.tap})`);
      if (shots) { await pg.evaluate(() => document.getElementById('stage').scrollIntoView()); await pg.screenshot({ path: `${shots}/FIELDS-${world}-phone.png` }); }
      ok(errs.length === 0, `${tag} zero page errors${errs.length ? ': ' + errs.slice(0, 2).join(' | ') : ''}`);
      await pg.close();
    }
  } finally { await browser.close(); srv.kill(); }
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
