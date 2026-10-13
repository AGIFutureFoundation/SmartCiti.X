/**
 * The world training modules on the Courses page (web/trade_craft_courses.html, section #course-modules), wave 19.
 *
 * Re-read against modules/registry/modules.json: one card per module in registry order, every step in order with
 * the registry's own words, every brief line verbatim, the Omega Hive greeter speaking its own line ONLY from its
 * button's click (the page script is run headless here against a stub voice), every link landing on a page that
 * exists, every supplement on this page's own viewer, every chrome word in all 8 locales, the honesty labels, and
 * neutral page markers. Prints `  ok <name>` per check and `FAIL` at column 0.
 */
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import vm from 'node:vm';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const J = (p) => JSON.parse(readFileSync(path.join(ROOT, p), 'utf8'));
let fails = 0, oks = 0;
const check = (name, cond, why = '') => {
  if (cond) { oks++; console.log(`  ok ${name}`); } else { fails++; console.log(`FAIL ${name}${why ? ' - ' + why : ''}`); }
};
const PAGE = readFileSync(path.join(ROOT, 'web/trade_craft_courses.html'), 'utf8');
const REG = J('modules/registry/modules.json');
const M = REG.modules;
const dec = (s) => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#x27;/g, "'").replace(/&mdash;/g, '—').replace(/&amp;/g, '&');
const strip = (s) => dec(s.replace(/<[^>]+>/g, ''));
const script = (id) => { const m = new RegExp(`<script[^>]*id="${id}"[^>]*>([\\s\\S]*?)</script>`).exec(PAGE); return m ? m[1] : null; };

// [section] placement and cards
const sStart = PAGE.indexOf('<section class="box" id="course-modules"');
const sEnd = PAGE.indexOf('</section>', PAGE.lastIndexOf('class="wmod-refused"'));
const SEC = sStart >= 0 && sEnd > sStart ? PAGE.slice(sStart, sEnd) : '';
check('[section] the world modules section is on the page once', PAGE.split('id="course-modules"').length === 2 && SEC.length > 0);
check('[section] it sits before the rules box', sStart >= 0 && sStart < PAGE.indexOf('id="course-rules"'));
const cards = [...SEC.matchAll(/<details class="wmod" id="([^"]+)" data-wmod="([^"]+)" data-wmod-family="([^"]+)">([\s\S]*?)<\/details>/g)];
check('[section] one card per module, in registry order', JSON.stringify(cards.map((c) => c[2])) === JSON.stringify(M.map((m) => m.id)));
const C = Object.fromEntries(cards.map((c) => [c[2], { fam: c[3], body: c[4] }]));
check('[section] each card names its family word', M.every((m) => C[m.id]?.fam === m.family && C[m.id].body.includes(`data-i18n="wmod.fam.${m.family}"`)));

// [steps] in order, registry words
const words = (s) => s.do ?? (s.kind === 'crew' ? `${s.role}: "${s.ask}"` : s.kind === 'walkaround' ? `${s.label}: ${s.check}` :
  s.kind === 'sim' ? `${s.seat_name} · ${s.scenario_name}` : s.kind === 'station' ? s.station_name : s.note);
const badSteps = [];
for (const m of M) {
  const ol = /<ol class="wmod-steps">([\s\S]*?)<\/ol>/.exec(C[m.id]?.body || '');
  const lis = ol ? [...ol[1].matchAll(/<li data-kind="([^"]+)">[\s\S]*?<span lang="en">([\s\S]*?)<\/span><\/li>/g)] : [];
  if (lis.length !== m.steps.length) { badSteps.push(`${m.id} count`); continue; }
  m.steps.forEach((s, i) => { if (lis[i][1] !== s.kind || dec(lis[i][2]) !== words(s)) badSteps.push(`${m.id}#${s.n}`); });
}
check('[steps] every step is shown in order with its kind and the registry\'s own words', badSteps.length === 0, badSteps.slice(0, 4).join(' '));
check('[steps] every step kind has its word', REG.step_kinds.every((k) => PAGE.includes(`data-i18n="wmod.k.${k}"`) || !M.some((m) => m.steps.some((s) => s.kind === k))));

// [brief] verbatim, in order
const badBrief = M.filter((m) => {
  const ul = /<ul class="wmod-brief">([\s\S]*?)<\/ul>/.exec(C[m.id]?.body || '');
  const got = ul ? [...ul[1].matchAll(/<li><span lang="en">([\s\S]*?)<\/span> <code class="wmod-src">([\s\S]*?)<\/code><\/li>/g)].map((x) => [dec(x[1]), dec(x[2])]) : [];
  return JSON.stringify(got) !== JSON.stringify(m.brief.map((b) => [b.text, b.source]));
}).map((m) => m.id);
check('[brief] every brief line and its source are shown verbatim, in order', badBrief.length === 0, badBrief.join(' '));

// [greeter] the Hive agent and its own line; the voice data matches
check('[greeter] each card shows its greeter, its line verbatim and a link to the Hive page', M.every((m) => {
  const b = C[m.id]?.body || '';
  const q = /<q lang="en" data-wmod-line>([\s\S]*?)<\/q>/.exec(b);
  return b.includes(`data-wmod-agent="${m.greeter.agent}"`) && q && dec(q[1]) === m.greeter.line &&
    b.includes(`href="trade_craft_hive.html?agent=${m.greeter.agent}"`) && b.includes(`data-wmod-speak="${m.id}"`);
}));
const VD = JSON.parse(script('wmod-voice') || '{}');
check('[greeter] the voice data carries exactly the greeters, each speaking its registry line', VD.voices &&
  JSON.stringify(VD.voices.agents.map((a) => a.id).sort()) === JSON.stringify([...new Set(M.map((m) => m.greeter.agent))].sort()) &&
  M.every((m) => JSON.stringify(VD.lines[m.id]) === JSON.stringify([m.greeter.agent, m.greeter.line])));
check('[greeter] the Hive kit is embedded for the voice', /var HiveVoice = \(function/.test(script('wmod-kit') || ''));

// [voice] run the page script headless: nothing speaks on load; a click speaks the card's greeter line once
const JS = script('wmod-js') || '';
check('[voice] the module script carries the neutral WORLD-PRACTICE markers', /WORLD-PRACTICE BEGIN/.test(JS) && /WORLD-PRACTICE END/.test(JS));
check('[voice] the script calls speak only once, from the click listener', (JS.match(/HiveVoice\.speak\(/g) || []).length === 1 &&
  /addEventListener\('click', function \(ev\) \{[\s\S]*HiveVoice\.speak\(/.test(JS) && !/setTimeout|setInterval|autoplay|onload/.test(JS));
{
  const spoken = [], handlers = {};
  const el = (attrs = {}) => ({ attrs, textContent: '', setAttribute(k, v) { this.attrs[k] = v; }, getAttribute(k) { return this.attrs[k]; },
    addEventListener(t, f) { (handlers[t] = handlers[t] || []).push(f); }, querySelector: () => el(), closest() { return null; } });
  const box = el(); const muteBtn = el(); const stateEl = el();
  box.querySelector = (s) => (s === '[data-wmod-mute]' ? muteBtn : stateEl);
  const I18N = JSON.parse(script('course-i18n'));
  const ctx = { window: {}, location: { hash: '' }, JSON, Object,
    document: { documentElement: { lang: 'en' }, getElementById: (id) => (id === 'course-modules' ? box : id === 'wmod-voice' ? { textContent: script('wmod-voice') } : id === 'course-i18n' ? { textContent: JSON.stringify(I18N) } : null) },
    HiveVoice: { init: () => false, setMuted: (on) => on, muted: () => false, speak: (q) => { spoken.push(q); return true; } } };
  ctx.window.HiveVoice = ctx.HiveVoice;
  let ran = true;
  try { vm.runInNewContext(JS, ctx); } catch (e) { ran = false; }
  check('[voice] on load the script runs and speaks nothing', ran && spoken.length === 0);
  const m = M[M.length - 1];
  const btn = { getAttribute: (k) => (k === 'data-wmod-speak' ? m.id : null) };
  (handlers.click || []).forEach((h) => h({ target: { closest: (s) => (s === '[data-wmod-speak]' ? btn : null) } }));
  check('[voice] a click on a greeter button speaks that greeter\'s registry line once', spoken.length === 1 &&
    spoken[0][0][0].id === m.greeter.agent && spoken[0][0][1] === m.greeter.line);
  check('[voice] the mute switch is present, pressed state exposed, state line polite', /data-wmod-mute aria-pressed="(true|false)"/.test(SEC) && /data-wmod-state aria-live="polite"/.test(SEC));
}

// [links] every target exists; restoration runners are the staged tasks' own; wilds sites exist
const goBad = [];
for (const m of M) for (const a of (C[m.id]?.body || '').matchAll(/<a href="([^"]+)" data-wmod-go="([^"]+)"/g)) {
  const href = dec(a[1]);
  if (!existsSync(path.join(ROOT, 'web', href.split('#')[0]))) goBad.push(href);
}
check('[links] every "where to practise" link lands on a page that exists', goBad.length === 0, goBad.join(' '));
const ST = J('restoration/registry/scenarios.json').staged_tasks;
check('[links] each restoration card links its staged tasks\' own runners', M.filter((m) => m.family === 'restoration-site').every((m) =>
  ST.filter((t) => t.place.id === m.site).every((t) => C[m.id].body.includes(`href="${t.launch.href.replace(/^web\//, '')}" data-wmod-go="wmod.go.runner"`))));
const W = J('wilds/registry/wilds.json').worlds;
check('[links] each wilds card links its world\'s sites by the wilds page hash', M.filter((m) => m.family === 'wilds-world').every((m) => {
  const w = W.find((x) => `wilds:${x.id}` === m.world);
  return m.places.every((p) => w.sites.some((s) => s.id === p.wilds_site) && C[m.id].body.includes(`href="trade_craft_wilds.html#${w.id}/${p.wilds_site}"`));
}));
check('[links] the robot-yard card links the world to watch, then the Robotics lab to drive', (() => {
  const b = C['module-robot-yard']?.body || '';
  const i = b.indexOf('href="trade_craft_parishes.html" data-wmod-go="wmod.go.watch"'), j = b.indexOf('href="trade_craft_robotics.html" data-wmod-go="wmod.go.drive"');
  return i >= 0 && j > i;
})());
check('[links] each worksite card links its worksites on the worksites page', M.filter((m) => m.family === 'worksite-district').every((m) =>
  m.places.every((p) => C[m.id].body.includes(`href="trade_craft_worksites.html#site-${p.worksite}"`))));

// [supp] supplements open this page's own viewer
const DATA = JSON.parse(script('course-data'));
check('[supp] each card lists its supplements, in order, on this page\'s viewer', M.every((m) => {
  const got = [...(C[m.id]?.body || '').matchAll(/<a href="\?lesson=([^"#]+)#course-sup" data-sup="([^"]+)">/g)].map((x) => x[2]);
  return JSON.stringify(got) === JSON.stringify(m.supplements) && got.every((l) => DATA.supplements[l]);
}));
check('[supp] a module with no lesson says so in words', M.filter((m) => !m.supplements.length).every((m) => C[m.id].body.includes('data-i18n="wmod.nosupp"')));

// [i18n] every word in all 8 locales
const I18 = JSON.parse(script('course-i18n'));
const keys = [...new Set([...SEC.matchAll(/data-i18n="([^"]+)"/g)].map((x) => x[1]))];
const LOCS = Object.keys(I18);
check('[i18n] eight locales are carried', LOCS.length === 8);
check('[i18n] every word the section uses is non-empty in every locale', keys.length > 20 && LOCS.every((l) => keys.every((k) => typeof I18[l].strings[k] === 'string' && I18[l].strings[k].trim())));
check('[i18n] the catalogue words equal the locale files', LOCS.every((l) => {
  const f = J(`i18n/locales/${l}.json`).strings;
  return keys.every((k) => f[k] === I18[l].strings[k]);
}));
check('[i18n] the voice-state words are the Hive\'s own keys', ['hive.v.muted', 'hive.v.nosynth', 'hive.v.novoice', 'hive.speak', 'hive.v.mute'].every((k) => LOCS.every((l) => I18[l].strings[k])));

const shown = (k) => { const m = new RegExp(`data-i18n="${k.replace(/\./g, '\\.')}">([^<]*)<`).exec(SEC); return m ? dec(m[1]) : null; };
check('[i18n] every worded element shows its English catalogue text', keys.every((k) => [...SEC.matchAll(new RegExp(`data-i18n="${k.replace(/\./g, '\\.')}">([^<]*)<`, 'g'))].every((x) => dec(x[1]) === I18.en.strings[k])));

// [honest] labels and markers: the words shown AND the catalogue words
const en = I18.en.strings;
const both = (k, re) => re.test(en[k] || '') && re.test(shown(k) || '');
check('[honest] unverified general practice; certifies nobody; no duration or credential',
  both('wmod.unv', /Unverified general practice/) && both('wmod.unv', /certifies anybody/) && both('wmod.unv', /no duration or credential/));
check('[honest] the Omega Hive label: SCRIPTED, no AI model, on a click', both('wmod.hive', /SCRIPTED, no AI model/) && both('wmod.hive', /on a click/));
check('[honest] the refused list recounts the registry', (SEC.split('class="wmod-refused"')[1] || '').split('<li>').length - 1 === Object.keys(REG.refused).length);
check('[honest] the stamp shown is the registry stamp', SEC.includes(`<code data-wmod-stamp>${REG.source_stamp}</code>`));
check('[honest] page markers are neutral: no team codename, no internal path', !/\bMODULES\b/.test(PAGE) && !/\/tmp\/|scratchpad|memory\//.test(PAGE));
check('[honest] no certificate or duration claim in the section\'s own words', !/\b(certificate|certified|qualifies|licensed|accredited)\b/i.test(keys.map((k) => en[k]).join(' ')) &&
  !/\b\d+\s*(minutes?|hours?|weeks?)\b/i.test(keys.map((k) => en[k]).join(' ')));

// [builder] the shared builder carries one anchored block
const BC = readFileSync(path.join(ROOT, 'web/build_courses.py'), 'utf8');
check('[builder] build_courses.py carries one anchored MODULES block calling worldmodules', BC.split('# MODULES BEGIN').length === 2 && BC.split('# MODULES END').length === 2 &&
  /# MODULES BEGIN[\s\S]*worldmodules\.prepare[\s\S]*worldmodules\.inject[\s\S]*# MODULES END/.test(BC));

console.log(`test_worldmodules: ${oks} passed, ${fails} failed`);
process.exit(fails ? 1 : 0);
