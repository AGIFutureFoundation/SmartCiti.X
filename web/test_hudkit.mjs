/* web/test_hudkit.mjs — the world-UI layout manager (web/hudkit.py) as adopted by the parish page and, through
 * web/build_bayworld.py, the Bay page. Prints "  ok " per check, "FAIL" at column 0, exits non-zero on failure.
 *
 *   node web/test_hudkit.mjs                     static checks (no browser)
 *   HUD_BASE=http://127.0.0.1:<port>/web/ flock $SP/chromium.lock node web/test_hudkit.mjs --browser [--shots=<dir>]
 *        the measured row: no two registered panels overlap and the canvas centre stays free, at 390x844 and
 *        1440x900, on both pages; RTL mirrors the corners. HUD_BEFORE=<dir> also measures the pages saved there
 *        (same selectors, no pass/fail) so a before/after count can be quoted.
 */
import { readFileSync, readdirSync, mkdirSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

let fails = 0, oks = 0;
const check = (name, cond, extra = '') => { if (cond) { oks++; console.log(`  ok ${name}`); } else { fails++; console.log(`FAIL ${name}${extra ? ' :: ' + extra : ''}`); } };
const R = new URL('..', import.meta.url).pathname;
const read = (p) => readFileSync(R + p, 'utf8');
const kit = read('web/hudkit.py');
const PAGES = { parishes: 'web/trade_craft_parishes.html', bay: 'web/trade_craft_bay.html', wilds: 'web/trade_craft_wilds.html' };
// what the brief requires each page to register (the Bay page has no NPC guides - its NPC kit is a named stub)
const REQUIRED = { parishes: ['mode', 'minimap', 'class', 'reactor', 'deep', 'npc', 'paths', 'city', 'legend'],
                   bay: ['mode', 'minimap', 'class', 'reactor', 'deep', 'paths', 'city', 'legend'],
                   wilds: ['mode', 'minimap', 'class', 'site', 'legend'] };  // wilds: no Reactor/Dive/NPC/econ kits on that page
const SLOTS = ['ts', 't', 'te', 'bs', 'b', 'be'];
const unesc = (s) => s.replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&amp;/g, '&');

// ---- the kit itself ----
const css = (kit.match(/HUD_CSS = f"""([\s\S]*?)"""/) || [])[1] || '';
const js = (kit.match(/HUD_JS = r"""([\s\S]*?)"""/) || [])[1] || '';
check('[kit] the grid keeps an empty centre track (area c) with a floor, no slot is placed in it',
  /grid-template-areas:"ts t te" "\. c \." "bs b be"/.test(css) && /minmax\(\{HUD_CENTRE_MIN_W\},1fr\)/.test(css)
  && /minmax\(\{HUD_CENTRE_MIN_H\},1fr\)/.test(css) && !/grid-area:c\b/.test(css)
  && /HUD_CENTRE_MIN_W = '(\d+)%'/.test(kit) && Number(kit.match(/HUD_CENTRE_MIN_W = '(\d+)%'/)[1]) >= 20
  && /\.hud\[data-hud-compact\]\{\{grid-template-columns:minmax\(0,1fr\) minmax\(\{HUD_CENTRE_MIN_W_COMPACT\},max-content\)/.test(css)
  && Number((kit.match(/HUD_CENTRE_MIN_W_COMPACT = '(\d+)%'/) || [0, 0])[1]) >= 10);
check('[kit] RTL: slots and launchers use logical/grid placement only (no physical left/right/margin-left/right)',
  !/(^|[;{\s])(left|right|margin-left|margin-right|padding-left|padding-right|float)\s*:/m.test(css));
check('[kit] safe-area insets pad the layer on all four sides',
  ['top', 'right', 'bottom', 'left'].every((s) => css.includes(`env(safe-area-inset-${s})`)));
check('[kit] compact mode is decided by STAGE width under 600 px (not the viewport)', /HUD_COMPACT_PX = 600\b/.test(kit)
  && /stage\.clientWidth < PX/.test(js) && /ResizeObserver\(setCompact\)\.observe\(stage\)/.test(js));
check('[kit] launchers and dock chips are >= 44 px targets with a visible focus ring',
  /\.hud-launch,\.hud-chip\{\{pointer-events:auto;min-block-size:44px;min-inline-size:44px/.test(css) && /\.hud-launch:focus-visible,\.hud-chip:focus-visible\{\{outline:3px/.test(css));
check('[kit] icon launchers report aria-expanded; the script never positions a kit by coordinates',
  /setAttribute\('aria-expanded'/.test(js) && !/\.style\.(left|right|top|bottom|inset|transform)\b/.test(js));
check('[kit] late panels are watched on their parents only (no subtree observer: per-frame label churn costs nothing)',
  /observe\(host, \{ childList: true \}\)/.test(js) && !/subtree:\s*true/.test(js));
check('[kit] a bad registration stops the build by name (slot, compact policy, duplicate id, flow anchor)', (() => {
  const py = `import sys; sys.path.insert(0, ${JSON.stringify(R + 'web')})
import hudkit
bad = [[{'id':'a','kind':'panel','sel':'.x','slot':'mid','order':0,'compact':'none'}],
       [{'id':'a','kind':'panel','sel':'.x','slot':'ts','order':0,'compact':'fold'}],
       [{'id':'a','kind':'panel','sel':'.x','slot':'ts','order':0,'compact':'none'}]*2,
       [{'id':'a','kind':'panel','sel':'.x','slot':'ts','order':0,'compact':'icon'}]]
n = 0
for b in bad:
    try: hudkit.check_panels(b)
    except hudkit.HudError: n += 1
try: hudkit.flow_anchors_present([{'id':'f','kind':'flow','goto':'#q','icon':'info','label':'hud.region','anchor':'id="q"'}], '<p>')
except hudkit.HudError: n += 1
print(n)`;
  try { return execFileSync('python3', ['-c', py], { encoding: 'utf8' }).trim() === '5'; } catch { return false; }
})());

// ---- the i18n keys: all 8 locales, real translations ----
const keys = [...kit.matchAll(/'(hud\.[a-z.]+)'/g)].map((m) => m[1]).filter((k, i, a) => a.indexOf(k) === i);
const locs = readdirSync(R + 'i18n/locales').filter((f) => f.endsWith('.json'));
const L = Object.fromEntries(locs.map((f) => [f.slice(0, -5), JSON.parse(read('i18n/locales/' + f)).strings]));
check('[i18n] the hud.* keys the kit names exist in all 8 locales', keys.length >= 5 && locs.length === 8
  && keys.every((k) => locs.every((f) => typeof L[f.slice(0, -5)][k] === 'string' && L[f.slice(0, -5)][k].trim())), keys.join(','));
check('[i18n] non-English hud.* values are translations, not English copies',
  keys.every((k) => Object.entries(L).every(([loc, s]) => loc === 'en' || s[k] !== L.en[k])));

// ---- each page ----
for (const [name, path] of Object.entries(PAGES)) {
  const html = read(path);
  const stage = (html.match(/<div id="stage"[\s\S]*?\n<\/div>\n/) || [''])[0];
  const layer = stage.match(/<div class="hud" data-hud [^>]*data-hud-panels="([^"]+)"/);
  check(`[${name}] exactly one HUD layer, inside #stage`, (html.match(/data-hud /g) || []).length === 1 && !!layer);
  let reg = [];
  try { reg = JSON.parse(unesc(layer ? layer[1] : '[]')); } catch { reg = []; }
  const ids = reg.map((p) => p.id);
  check(`[${name}] registers its required panels: ${REQUIRED[name].join(', ')}`,
    REQUIRED[name].every((id) => ids.includes(id)), `missing ${REQUIRED[name].filter((id) => !ids.includes(id))}`);
  check(`[${name}] registrations are well formed (unique ids, known slots, flow targets on the page exactly once)`,
    new Set(ids).size === ids.length && reg.every((p) => (p.kind === 'panel' && SLOTS.includes(p.slot) && p.sel)
      || (p.kind === 'flow' && p.goto && (p.goto.startsWith('#') ? (html.match(new RegExp(`id="${p.goto.slice(1)}"`, 'g')) || []).length === 1
        : html.includes(p.goto.replace(/^\[|\]$/g, ''))))));
  check(`[${name}] every static panel selector resolves in the markup (the rest are kit-mounted late: class HUD, Dive HUD, NPC dialog)`,
    reg.filter((p) => p.kind === 'panel' && !['class', 'deep', 'npc'].includes(p.id)).every((p) =>
      p.sel.startsWith('#') ? html.includes(`id="${p.sel.slice(1)}"`) : html.includes(`class="${p.sel.slice(1)}"`)));
  check(`[${name}] launchers + dock chips carry translated aria labels (hud.* data-i18n-aria)`,
    [...stage.matchAll(/<button type="button" class="hud-(?:launch|chip)"[^>]*>/g)].length >= (name === 'wilds' ? 1 : 3)
    && [...stage.matchAll(/<button type="button" class="hud-(?:launch|chip)"[^>]*>/g)].every((m) => /aria-label="[^"]+" data-i18n-aria="hud\./.test(m[0])));
  check(`[${name}] the kit CSS and script ship once; the script runs after the kits it adopts`,
    (html.match(/<style id="hud-css">/g) || []).length === 1 && (html.match(/<script id="hud-kit">/g) || []).length === 1
    && html.indexOf('<script id="hud-kit">') > html.indexOf('id="class-kit"') && html.indexOf('<script id="hud-kit">') > html.indexOf('id="rk-panel"')
    && html.indexOf('<script id="hud-kit">') > html.indexOf('id="stage"'));
  const cat = JSON.parse((html.match(/<script type="application\/json" id="(?:parishes|wilds)-i18n">([\s\S]*?)<\/script>/) || ['', '{}'])[1].replace(/<\\\//g, '</'));
  check(`[${name}] the run-time catalogue carries the hud.* labels in all 8 locales`,
    Object.keys(cat).length === 8 && ['hud.region', 'hud.open.legend'].every((k) => Object.values(cat).every((c) => c.strings[k])));
}

// ---- the measured row (browser) ----
if (process.argv.includes('--browser')) {
  const { chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs');
  const BASE = process.env.HUD_BASE;
  if (!BASE) { console.log('FAIL [browser] HUD_BASE is not set'); process.exit(1); }
  const BEFORE = process.env.HUD_BEFORE || null;
  const shotArg = process.argv.find((a) => a.startsWith('--shots='));
  const SHOTS = shotArg ? shotArg.slice(8) : null;
  if (SHOTS) mkdirSync(SHOTS, { recursive: true });
  const watchdog = setTimeout(() => { console.log('FAIL [browser] watchdog: the run passed 85 s'); process.exit(1); }, 85_000);
  const SEL = { mode: '.ctl', minimap: '#minimap', satellite: '#satbox', toast: '#toast', class: '.tcc-hud', reactor: '#rk-panel',
                deep: '#deep-hud', npc: '.npc-panel', dock: '.hud-dock' };
  // the same selector metric for the before and after pages: visible registered panels, pairwise intersections,
  // with the stage aligned to the top and to the bottom of the viewport (viewport-fixed panels move against it)
  const metric = (sel) => {
    const st = document.getElementById('stage'), out = { pairs: [], centre: [] };
    for (const align of ['start', 'end']) {
      st.scrollIntoView({ block: align });
      const rs = [];
      for (const [id, s] of Object.entries(sel)) {
        const el = document.querySelector(s);
        if (!el || el.closest('[hidden]') || !el.getClientRects().length) continue;
        const r = el.getBoundingClientRect(); if (r.width > 0 && r.height > 0) rs.push([id, r]);
      }
      for (let i = 0; i < rs.length; i++) for (let j = i + 1; j < rs.length; j++) {
        const a = rs[i][1], b = rs[j][1];
        if (Math.min(a.right, b.right) - Math.max(a.left, b.left) > 0.5 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 0.5) {
          const k = rs[i][0] + '|' + rs[j][0]; if (!out.pairs.includes(k)) out.pairs.push(k);
        }
      }
      const s = st.getBoundingClientRect(), cx = s.left + s.width / 2, cy = s.top + s.height / 2;
      for (const [id, r] of rs) if (cx >= r.left && cx <= r.right && cy >= r.top && cy <= r.bottom && !out.centre.includes(id)) out.centre.push(id);
    }
    return out;
  };
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const VIEWS = [[390, 844], [1440, 900]];
  const errors = [];
  const ONLY = process.env.HUD_PAGES ? process.env.HUD_PAGES.split(',') : null;   // e.g. a mutation run on one page
  for (const [name, path] of Object.entries(PAGES)) {
    if (ONLY && !ONLY.includes(name)) continue;
    const file = path.slice(4);
    for (const [w, h] of VIEWS) {
      for (const when of BEFORE && existsSync(`${BEFORE}/${file}`) ? ['before', 'after'] : ['after']) {
        const page = await browser.newPage({ viewport: { width: w, height: h } });
        if (when === 'after') page.on('pageerror', (e) => errors.push(`${name} ${w}: ${e.message}`));
        if (when === 'before') await page.route('**/' + file, (r) => r.fulfill({ contentType: 'text/html', body: readFileSync(`${BEFORE}/${file}`, 'utf8') }));
        await page.goto(BASE + file, { waitUntil: 'load', timeout: 30_000 });
        await page.waitForTimeout(1200);
        const m = await page.evaluate(metric, SEL);
        if (when === 'before') { console.log(`  .. [measure] ${name} ${w}x${h} BEFORE: ${m.pairs.length} overlapping pairs [${m.pairs}] centre covered by [${m.centre}]`); await page.close(); continue; }
        const hud = await page.evaluate(() => { document.getElementById('stage').scrollIntoView({ block: 'start' });
          return { ov: window.__hud.overlaps(), centre: window.__hud.centreFree(), compact: window.__hud.compact, pending: window.__hud.pending(),
                   n: window.__hud.panels().length, ctlH: document.querySelector('.ctl').getBoundingClientRect().height,
                   firstIsBtn: (() => { const c = document.querySelector('.ctl'); const kids = [...c.children].filter((k) => k.getClientRects().length); kids.sort((x, y) => x.getBoundingClientRect().left - y.getBoundingClientRect().left); return document.documentElement.dir === 'rtl' || (kids[0] && kids[0].tagName === 'BUTTON'); })(),
                   btnsSeen: (() => { const c = document.querySelector('.ctl').getBoundingClientRect(); return [...document.querySelectorAll('.ctl button')].filter((b) => { const r = b.getBoundingClientRect(); return r.width > 0 && r.left >= c.left - 0.5 && r.right <= c.right + 0.5; }).length; })() }; });
        console.log(`  .. [measure] ${name} ${w}x${h} AFTER: ${m.pairs.length} overlapping pairs [${m.pairs}] centre covered by [${m.centre}]; hud ${hud.n} panels, compact ${hud.compact}, not yet mounted [${hud.pending}]`);
        check(`[browser] ${name} ${w}x${h}: no two registered panels overlap (kit and selector metric) and the canvas centre is free`,
          m.pairs.length === 0 && hud.ov.length === 0 && hud.centre && m.centre.length === 0, JSON.stringify({ m, ov: hud.ov }));
        check(`[browser] ${name} ${w}x${h}: compact mode ${w < 600 ? 'on' : 'off'} (stage width), mode buttons ${w < 600 ? 'one scrolling row' : 'inline'}`,
          hud.compact === (w < 600) && (w >= 600 || (hud.ctlH <= 60 && hud.btnsSeen >= 1 && hud.firstIsBtn)), `ctl height ${hud.ctlH}, buttons fully visible ${hud.btnsSeen}`);
        if (SHOTS) await page.screenshot({ path: `${SHOTS}/UX-${name}-${w}.png` });
        if (w < 600 && name === 'parishes') {
          const rtl = await page.evaluate(() => { const s = document.getElementById('stage').getBoundingClientRect(), mid = s.left + s.width / 2;
            const ltr = document.getElementById('minimap').getBoundingClientRect().left > mid;
            document.documentElement.dir = 'rtl';
            const r = { ltr, rtl: document.getElementById('minimap').getBoundingClientRect().right < mid, ov: window.__hud.overlaps() };
            return r; });
          check('[browser] RTL mirrors the corners: the minimap moves from the end (right) to the end (left), still no overlap', rtl.ltr && rtl.rtl && rtl.ov.length === 0, JSON.stringify(rtl));
          if (SHOTS) await page.screenshot({ path: `${SHOTS}/UX-${name}-${w}-rtl.png` });
          const tap = await page.evaluate(() => { const b = document.querySelector('[data-hud-launch="reactor"]'); const card = document.getElementById('rk-panel');
            const before = card.getClientRects().length; b.click(); return { before, after: card.getClientRects().length, exp: b.getAttribute('aria-expanded') }; });
          check('[browser] the folded Reactor panel opens from its 44 px icon (aria-expanded true)', tap.before === 0 && tap.after > 0 && tap.exp === 'true', JSON.stringify(tap));
        }
        await page.close();
      }
    }
  }
  check('[browser] zero page errors on the adopted pages', errors.length === 0, errors.join(' / '));
  clearTimeout(watchdog);
  await browser.close();
}

console.log(fails ? `\n${oks} ok, ${fails} FAIL` : `\ntest_hudkit: ${oks} ok`);
process.exit(fails ? 1 : 0);
