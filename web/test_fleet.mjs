/**
 * The fleet showroom page (web/trade_craft_fleet.html, built by
 * web/build_fleet.py). Static checks always; with --browser=<base url> it also
 * drives the page in Chromium (run under flock $SP/chromium.lock).
 *
 *   node web/test_fleet.mjs [--root=/copy] [--browser=http://127.0.0.1:PORT]
 */
import { readFileSync, existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const HERE = dirname(fileURLToPath(import.meta.url));
const arg = (k) => { const h = process.argv.slice(2).find((a) => a.startsWith(`--${k}=`)); return h ? h.slice(k.length + 3) : null; };
const ROOT = resolve(arg('root') || join(HERE, '..'));
let n = 0, bad = 0;
const ok = (m, c, ev = []) => {
  if (c) { n++; console.log('  ok  ' + m); return; }
  bad++; console.log('FAIL  ' + m); for (const e of ev.slice(0, 6)) console.log('      ' + e);
};
const page = readFileSync(join(ROOT, 'web/trade_craft_fleet.html'), 'utf8');
const reg = JSON.parse(readFileSync(join(ROOT, 'fleet/registry/fleet.json'), 'utf8'));
const block = (id) => { const m = page.match(new RegExp(`<script type="application/json" id="${id}">([\\s\\S]*?)</script>`)); return m ? JSON.parse(m[1]) : null; };

// freshness: the builder regenerates exactly this file
let fresh = true, why = '';
try { execFileSync('python3', [join(ROOT, 'web/build_fleet.py'), '--check'], { stdio: 'pipe' }); } catch (e) { fresh = false; why = String(e.stdout || '') + String(e.stderr || ''); }
ok('the page is what web/build_fleet.py builds now (not hand-edited, not stale)', fresh, [why.slice(0, 300)]);
const bsrc = readFileSync(join(ROOT, 'web/build_fleet.py'), 'utf8');
ok('the builder fails closed when the page is undeclared in sitenav.PAGES (no in-process registration, no borrowed header)',
  /if PAGE not in sitenav\.PAGES:\n\s+raise SystemExit/.test(bsrc) && !/sitenav\.PAGES\[/.test(bsrc) && !/nav_html\('web\/trade_craft_(?!fleet)/.test(bsrc)
  && page.includes('href="trade_craft_fleet.html" aria-current="page"'));
const emb = block('fleet-registry');
ok('the registry is embedded verbatim', emb && JSON.stringify(emb) === JSON.stringify(reg));
ok('the page embeds exactly 50 land + 20 water', emb && emb.fleet.filter((e) => e.medium === 'land').length === 50 && emb.fleet.filter((e) => e.medium === 'water').length === 20);
const kit = execFileSync('python3', ['-c', 'import sys; sys.path.insert(0, sys.argv[1]); import fleetkit; sys.stdout.write(fleetkit.fleet_inline())', join(ROOT, 'web')]).toString();
ok('the page carries web/fleetkit.py byte-for-byte between its FLEET_KIT markers', page.includes(kit) && page.split('/* FLEET_KIT:BEGIN').length === 2);
ok('exactly one <h1>', (page.match(/<h1[\s>]/g) || []).length === 1);
ok('apply_seo head tags: description, canonical, og:title', /<meta name="description"/.test(page) && /<link rel="canonical"/.test(page) && /property="og:title"/.test(page));
ok('brand icon link', /<link rel="icon" href="data:image\/svg\+xml/.test(page));
ok('site nav with skip target', page.includes('data-sitenav') && page.includes('id="tc-main"'));
const head = page.slice(0, page.indexOf('</head>'));
ok('style switcher: STYLE_HEAD_JS runs before any <style>', head.indexOf("localStorage.getItem('tc-style')") > -1 && head.indexOf("localStorage.getItem('tc-style')") < head.indexOf('<style'));
ok('style switcher: STYLE_JS after the page scripts, radios for all 5 styles', page.lastIndexOf('<script>') > page.indexOf('<script type="module">')
  && ['enterprise', 'midnight', 'blueprint', 'hivis', 'studio'].every((s) => page.includes(`name="tc-style" value="${s}"`)));
ok('canvas theme layer: body.tc-theme-canvas + data-tc-theme="canvas" styles', page.includes('<body class="tc-theme-canvas"') && page.includes('data-tc-theme="canvas"'));
const own = head.slice(head.indexOf('<style>'), head.indexOf('</style>'));
const hex = own.match(/#[0-9a-fA-F]{3,8}\b/g) || [];
ok('the page CSS colours only from theme tokens (no hex literal)', hex.length === 0 && /var\(--tc-panel\)/.test(own), hex);
ok('no remote URL in the page (vendor three.js, inline data)', !/(src|href)="https?:/.test(page) && page.includes('"three":"./vendor/three.module.min.js"')
  && existsSync(join(ROOT, 'web/vendor/three.module.min.js')) && existsSync(join(ROOT, 'web/vendor/addons/controls/OrbitControls.js')));
const cat = block('fleet-i18n');
const used = [...new Set([...page.matchAll(/data-i18n(?:-aria)?="(fleet\.[^"]+)"/g)].map((m) => m[1]))];
const missing = [];
if (cat) for (const [loc, c] of Object.entries(cat)) for (const k of used) if (!c.strings[k]) missing.push(`${loc} ${k}`);
ok(`fleet.* i18n catalogue: 8 locales, every used key (${used.length}) in each`, cat && Object.keys(cat).length === 8 && missing.length === 0, missing);
const copies = cat ? Object.entries(cat).filter(([l]) => l !== 'en').flatMap(([l, c]) => Object.entries(c.strings)
  .filter(([k, v]) => v === cat.en.strings[k] && !['fleet.authored'].includes(k) && v.length > 6).map(([k]) => `${l} ${k}`)) : ['no catalogue'];
ok('non-English fleet strings are translations, not English copies (AUTHORED is a provenance token)', copies.length === 0, copies);
ok('an rtl locale is present (ar)', cat && cat.ar && cat.ar.dir === 'rtl');
ok('the honesty lines are on the page: generic types, AUTHORED, driving is play', page.includes('no makes, models, brands or logos') && page.includes('Driving here is play, not training'));
ok('seat links on the page are only the registry\'s', (() => {
  const want = new Set(reg.fleet.filter((e) => e.sim_seat).map((e) => e.sim_seat.id));
  return want.size === 3 && [...want].every((s) => page.includes(`sim=${s}`));
})());

ok('phone driving: the page builds the kit\'s touch controls with all six translated labels and toggles them with enter/exit',
  /fleetTouchControls\(document, \$\('\.fl-stage'\)/.test(page) && ['group', 'stick', 'throttle', 'brake', 'enter', 'exit'].every((k) => page.includes(`${k}: tr('touch.${k}')`))
  && /touch\.setAboard\(true\)/.test(page) && /touch\.setAboard\(false\)/.test(page) && /const t = touch\.input\(\)/.test(page));
// ---------------------------------------------------------------- browser ---
const base = arg('browser');
if (base) {
  const { chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs');
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1280, height: 860 } });
  const errs = [];
  p.on('pageerror', (e) => errs.push(e.message));
  p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto(`${base}/web/trade_craft_fleet.html`);
  await p.waitForFunction(() => document.documentElement.dataset.fleetReady === '1', null, { timeout: 30000 });
  await p.waitForTimeout(400);
  const F = (fn, a) => p.evaluate(fn, a);
  ok('browser: all 70 shown on the turntable at load', (await F(() => window.__fleet.shown().length)) === 70);
  ok('browser: land filter shows 50, water 20', (await F(() => window.__fleet.filter('land', 'all'))) === 50 && (await F(() => window.__fleet.filter('water', 'all'))) === 20);
  const fams = reg.families.map((f) => f.id);
  const per = await F((fs) => fs.map((f) => { const n = window.__fleet.filter('all', f); return [f, n]; }), fams);
  ok('browser: every family filter shows exactly its registry count', per.every(([f, c]) => c === reg.families.find((x) => x.id === f).count), per.filter(([f, c]) => c !== reg.families.find((x) => x.id === f).count).map(String));
  const frame = () => p.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => r(window.__fleet.stats())))));
  await F(() => window.__fleet.filter('all', 'bus'));
  const one = await frame();
  await F(() => window.__fleet.filter('all', 'all'));
  const all = await frame();
  ok(`browser: draw calls grow by one per family, not per vehicle (1 family ${one.drawCalls}, 34 families/70 vehicles ${all.drawCalls})`,
    all.drawCalls - one.drawCalls === reg.families.length - 1 && all.instances === 70, [JSON.stringify({ one, all })]);
  const land = await F(() => { window.__fleet.select('box-truck.medium-box-truck'); window.__fleet.drive(); const P = window.__fleet.pond;
    // aim at the pond and floor it for 60 s
    return window.__fleet.steps(3600, { throttle: 1, steer: 0.08, brake: 0 }); });
  ok(`browser: a land vehicle driven for a minute never enters the pond (refused ${land.refused}x)`, land.wet === false && land.y === 0);
  const boat = await F(() => { window.__fleet.exit(); window.__fleet.select('airboat.airboat'); window.__fleet.drive(); return window.__fleet.steps(3600, { throttle: 1, steer: 0.05, brake: 0 }); });
  ok(`browser: a boat driven for a minute never leaves the pond (refused ${boat.refused}x)`, boat.wet === true && boat.refused > 0);
  ok('browser: exit returns to the turntable', (await F(() => window.__fleet.exit())) === 'turntable');
  const seat = await F(() => { window.__fleet.select('forklift.counterbalance-forklift'); const a = document.querySelector('#spec-seat a'); return a ? a.getAttribute('href') : null; });
  ok('browser: a linked entry offers its real training seat', seat === reg.fleet.find((e) => e.id === 'forklift.counterbalance-forklift').sim_seat.href.replace(/^web\//, ''));
  const noSeat = await F(() => { window.__fleet.select('bus.school-bus'); return document.querySelector('#spec-seat a') === null; });
  ok('browser: an unlinked entry offers no seat', noSeat);
  const spec = await F(() => { window.__fleet.select('tug.harbor-tug'); return document.querySelector('#spec-list').textContent; });
  ok('browser: specs are read from the registry', spec.includes('26') && spec.includes('450'));
  const cam = await F(() => { window.__fleet.select('pickup.crew-cab-pickup'); window.__fleet.drive(); window.__fleet.steps(60, { throttle: 1, steer: 0.5, brake: 0 });
    window.__fleet.cam('driver'); const s = window.__fleet.steps(1, { throttle: 0, steer: 0, brake: 0 }); const e = window.__fleet.eye();
    const r = { d: Math.hypot(e.x - s.x, e.z - s.z), up: e.y - s.y, wheels: window.__fleet.wheels() }; window.__fleet.cam('chase'); window.__fleet.exit(); return r; });
  ok(`browser: driver view puts the eye inside the cab (${cam.d.toFixed(2)} m from centre, ${cam.up.toFixed(2)} m up); wheels drawn`, cam.d < 3 && cam.up > 1 && cam.up < 2.2 && cam.wheels);
  const tr = await F(() => window.__fleet.traffic(true, 900));
  ok(`browser: ambient traffic ${tr.agents} agents, ${tr.drawCalls} draw calls, ${tr.avgMs.toFixed(2)} ms/update; land never wet (${tr.wet}), boats never ashore (${tr.dry})`,
    tr.agents > 10 && tr.wet === 0 && tr.dry === 0 && tr.drawCalls <= 11 && tr.avgMs < 1.5, [JSON.stringify(tr)]);
  await F(() => window.__fleet.traffic(false, 0));
  const shots = arg('shots');
  if (shots) {   // driver view with the cab interior, then braking lamps in the chase view
    await F(() => { window.__fleet.select('pickup.crew-cab-pickup'); window.__fleet.drive(); window.__fleet.steps(40, { throttle: 1, steer: 0, brake: 0 }); window.__fleet.cam('driver'); });
    await p.waitForTimeout(300); await p.screenshot({ path: `${shots}/FLEET-w6-cab.png` });
    await F(() => window.__fleet.cam('chase')); await p.focus('#fleet-canvas'); await p.keyboard.down('Space'); await p.waitForTimeout(500);
    await p.screenshot({ path: `${shots}/FLEET-w6-brake.png` }); await p.keyboard.up('Space'); await F(() => window.__fleet.exit());
  }
  // phone: a coarse pointer shows the touch controls; the stick, throttle, brake and get in/out drive the test pad
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, deviceScaleFactor: 2 });
  const q = await ctx.newPage();
  q.on('pageerror', (e) => errs.push('phone: ' + e.message));
  await q.goto(`${base}/web/trade_craft_fleet.html#pickup.crew-cab-pickup`);
  await q.waitForFunction(() => document.documentElement.dataset.fleetReady === '1', null, { timeout: 30000 });
  const G = (fn, a) => q.evaluate(fn, a);
  const vis = await G(() => { const el = document.querySelector('.fleet-touch'), t = document.querySelector('.fleet-toggle');
    return { shown: getComputedStyle(el).display === 'flex', label: el.getAttribute('aria-label'), toggle: t.textContent, h: t.getBoundingClientRect().height, role: el.getAttribute('role') }; });
  ok(`browser phone: touch controls show on a coarse pointer as a labelled group (${vis.label}); get-in button ${vis.h.toFixed(0)} px`, vis.shown && vis.role === 'group' && vis.label === 'Touch driving controls' && vis.toggle === 'Get in' && vis.h >= 48, [JSON.stringify(vis)]);
  await q.tap('.fleet-toggle');
  const box = async (sel) => q.locator(sel).boundingBox();
  const inDrive = await G(() => ({ mode: window.__fleet.mode(), label: document.querySelector('.fleet-toggle').textContent, stick: !document.querySelector('.fleet-stick').hidden }));
  const x0 = await G(() => window.__fleet.steps(0, {}));
  const tb = await box('.fleet-throttle');
  await q.mouse.move(tb.x + tb.width / 2, tb.y + tb.height / 2); await q.mouse.down(); await q.waitForTimeout(900);
  const held = await G(() => ({ inp: window.__fleet.input(), st: window.__fleet.steps(0, {}) })); await q.mouse.up();
  ok(`browser phone: get in, then holding Throttle drives forward (${Math.hypot(held.st.x - x0.x, held.st.z - x0.z).toFixed(1)} m)`,
    inDrive.mode === 'drive' && inDrive.label === 'Get out' && inDrive.stick && held.inp.throttle === 1 && held.st.v > 0.5 && Math.hypot(held.st.x - x0.x, held.st.z - x0.z) > 0.1, [JSON.stringify({ inDrive, held })]);
  const sb = await box('.fleet-stick');
  await q.mouse.move(sb.x + sb.width / 2, sb.y + sb.height / 2); await q.mouse.down(); await q.mouse.move(sb.x + 4, sb.y + sb.height / 2 - 20, { steps: 4 });
  const stick = await G(() => window.__fleet.input());
  if (shots) await q.screenshot({ path: `${shots}/FLEET-w6-phone.png` });
  await q.mouse.up();
  const rel = await G(() => window.__fleet.input());
  ok(`browser phone: dragging the stick left steers left (steer ${stick.steer.toFixed(2)}, throttle ${stick.throttle.toFixed(2)}); release centres it`, stick.steer > 0.8 && stick.throttle > 0 && rel.steer === 0 && rel.throttle === 0, [JSON.stringify({ stick, rel })]);
  const bb = await box('.fleet-brake');
  await q.mouse.move(bb.x + bb.width / 2, bb.y + bb.height / 2); await q.mouse.down(); await q.waitForTimeout(300);
  const brk = await G(() => ({ lamp: window.__fleet.brake(), pressed: document.querySelector('.fleet-brake').getAttribute('aria-pressed') })); await q.mouse.up();
  ok('browser phone: holding Brake lights this vehicle\'s brake lamps (per instance) and reports aria-pressed', brk.lamp === 1 && brk.pressed === 'true', [JSON.stringify(brk)]);
  await q.tap('.fleet-toggle');
  ok('browser phone: Get out returns to the turntable and hides the stick', await G(() => window.__fleet.mode() === 'turntable' && document.querySelector('.fleet-stick').hidden && document.querySelector('.fleet-toggle').textContent === 'Get in'));
  await ctx.close();
  await p.goto(`${base}/web/trade_craft_fleet.html?lang=ar#ferry.vehicle-ferry`);
  await p.waitForFunction(() => document.documentElement.dataset.fleetReady === '1', null, { timeout: 30000 });
  ok('browser: ?lang=ar renders rtl Arabic chrome and the #id deep link selects', await F(() => document.documentElement.dir === 'rtl'
    && document.querySelector('h1').textContent.includes('الأسطول') && window.__fleet.selected() === 'ferry.vehicle-ferry'));
  ok('browser: zero page errors', errs.length === 0, errs);
  await b.close();
}
console.log(bad ? `FAIL  test_fleet: ${bad} of ${n + bad} checks failed` : `test_fleet: all ${n} checks passed`);
process.exit(bad ? 1 : 0);
