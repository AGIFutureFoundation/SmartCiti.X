/* web/test_hive.mjs - the Omega Hive page (web/trade_craft_hive.html), checked against hive/registry/hive.json.
 * Browser-free by default. The voice kit and the council router are run headless here in a vm with a stub
 * speechSynthesis: no autoplay, on-device voices only, mute, classroom volume / rate caps, and a council that is the
 * same every time and quotes only registry text.
 * --browser (or --browser=<base url>) also drives the page in Chromium; --worlds drives the parish world and the 3D campus
 * instead (a guide and an advisor speak on a click). Without a url it serves the bundle itself on
 * 127.0.0.1 and stops only the server it started. Run it under flock $SP/chromium.lock. */
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
let pass = 0, fail = 0;
const ok = (m, c, why) => { if (c) { pass++; console.log('  ok  ' + m); } else { fail++; console.log('FAIL  ' + m + (why ? ' :: ' + JSON.stringify(why).slice(0, 400) : '')); } };
const page = readFileSync(join(HERE, 'trade_craft_hive.html'), 'utf8');
const reg = JSON.parse(readFileSync(join(ROOT, 'hive/registry/hive.json'), 'utf8'));
const blob = (id) => JSON.parse(page.split(`<script type="application/json" id="${id}">`)[1].split('</script>')[0]);
const script = (id) => page.split(`<script id="${id}">`)[1].split('</script>')[0];
const D = blob('hive-data'), I = blob('hive-i18n');
const KIT = script('hive-kit'), PJS = script('hive-page');

/* ---- page structure */
ok('exactly one <h1>, and it is the translated page title', (page.match(/<h1[\s>]/g) || []).length === 1 && /<h1 class="tc-page-title" data-i18n="hive.title">/.test(page));
ok('the site nav is present and marks this page current', /href="trade_craft_hive.html" aria-current="page"/.test(page));
ok('the saved-style head script runs before paint', page.indexOf('id="style-head-js"') > 0 && page.indexOf('id="style-head-js"') < page.indexOf('</head>'));
ok('the embedded data is the registry: same stamp, every agent in registry order', D.stamp === reg.source_stamp
  && JSON.stringify(D.agents.map((a) => a.id)) === JSON.stringify(reg.agents.map((a) => a.id)));
const badTxt = [];
reg.agents.forEach((a, i) => a.lines.forEach((l, j) => { const r = D.agents[i].lines[j], t = D.texts[r.t];
  if (!t || t[0] !== l.text || t[1] !== l.source || r.k !== l.kind || r.safe !== (l.k12 ? 1 : 0) || (r.ask ?? null) !== (l.ask ?? null)) badTxt.push(a.id + ' ' + l.id); }));
ok(`every embedded line (${reg.counts.lines}) is the registry quote with its source path, kind, ask and K-12 flag`, badTxt.length === 0, badTxt.slice(0, 3));
ok('every embedded voice is the registry voice (pitch, rate)', reg.agents.every((a, i) => D.agents[i].pitch === a.voice.pitch && D.agents[i].rate === a.voice.rate && D.agents[i].k12 === (a.k12 ? 1 : 0)));
ok('the figures are recounted from the registry, and AI models prints 0',
  ['agents', 'advisors', 'crew_roles', 'npcs', 'lines', 'models'].every((k) => page.includes(`data-hive-count="${k}">${reg.counts[k]}<`)) && reg.counts.models === 0);
const cardOf = (id) => { const s = page.split(`<article class="hv-card" data-agent="${id}"`)[1]; return s ? s.split('</article>')[0] : null; };
const badCard = reg.agents.filter((a) => { const c = cardOf(a.id); const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
  return !c || !c.includes(`data-k12="${a.k12 ? 1 : 0}"`) || !c.includes(`data-pitch>${a.voice.pitch.toFixed(2)}<`) || !c.includes(`data-rate>${a.voice.rate.toFixed(2)}<`)
    || !c.includes(`<span data-traits>${esc(a.personality.traits.join(', '))}</span>`) || !c.includes(`<span data-style>${esc(a.personality.style)}</span>`)
    || !c.includes(`<code>${esc(a.avatar.character)}</code>`) || !c.includes(`data-nlines>${a.lines.length}<`) || !c.includes(`data-lines-for="${a.id}"`); });
ok(`every agent (${reg.agents.length}) has a roster card with its portrait, personality, locker character, voice and line count`, badCard.length === 0, badCard.map((a) => a.id).slice(0, 3));
const faces = page.match(/<svg class="hv-face"[\s\S]*?<\/svg>/g) || [];
ok(`every card has a portrait (${faces.length}), decorative (aria-hidden) with no <title> or <text>`, faces.length === reg.agents.length
  && faces.every((f) => /aria-hidden="true"/.test(f) && !/<title|<text/.test(f)));
ok('every registry honesty line is printed verbatim, and the four plain statements are on the page', Object.keys(reg.honesty).every((k) => page.includes(`data-honesty="${k}"`))
  && [1, 2, 3, 4].every((i) => page.includes(`data-i18n="hive.is.${i}"`)));
ok('the English statements say SCRIPTED, no AI model, the device\'s speech synthesis and AUTHORED personalities',
  /SCRIPTED/.test(I.en.strings['hive.is.1']) && /No AI model/.test(I.en.strings['hive.is.2']) && /speech synthesis/.test(I.en.strings['hive.is.3']) && /AUTHORED/.test(I.en.strings['hive.is.4']));
const keys = [...new Set([...page.matchAll(/data-i18n(?:-aria)?="([^"]+)"/g)].map((m) => m[1]))];
const jsKeys = [...new Set([...PJS.matchAll(/t\('(hive\.[a-z0-9.]+[a-z0-9])'\)/g)].map((m) => m[1]))];
ok(`every chrome key (${keys.length} in markup, ${jsKeys.length} in script) exists, non-empty, in all 8 locales; Arabic is right-to-left`,
  Object.keys(I).length === 8 && [...keys, ...jsKeys].every((k) => Object.values(I).every((L) => typeof L.strings[k] === 'string' && L.strings[k].trim())) && I.ar.dir === 'rtl');
const states = ['muted', 'nosynth', 'novoice', 'refused', 'speaking', 'done', 'stopped', 'ready'];
ok('every voice state the kit can report has a key in all 8 locales', states.every((s) => Object.values(I).every((L) => typeof L.strings['hive.v.' + s] === 'string')));
ok('every line kind and agent kind has a key in all 8 locales', [...new Set(D.agents.flatMap((a) => a.lines.map((l) => 'hive.k.' + l.k))), ...new Set(D.agents.map((a) => 'hive.kind.' + a.kind))]
  .every((k) => Object.values(I).every((L) => typeof L.strings[k] === 'string')));
ok('the non-English chrome is translated, not copied (under 10% identical to English)', Object.entries(I).filter(([l]) => l !== 'en').every(([, L]) =>
  Object.keys(L.strings).filter((k) => L.strings[k] === I.en.strings[k]).length < Object.keys(L.strings).length * 0.1));
ok('links to the 3D campus and the parish world, each a real file', ['trade_craft_3d.html', 'trade_craft_parishes.html'].every((f) => page.includes(`href="${f}"`) && existsSync(join(HERE, f))));
ok('touch controls are at least 44 px', /\.hv-btn\{min-block-size:44px;min-inline-size:44px/.test(page));

/* ---- no autoplay, no network: static */
const scripts = [...page.matchAll(/<script(?![^>]*application\/json)[^>]*>([\s\S]*?)<\/script>/g)].map((m) => m[1]).join('\n');
ok('the page has no <audio>, <video>, autoplay attribute, or remote script', !/<audio|<video|autoplay/i.test(page.replace(/<script[\s\S]*?<\/script>/g, '')) && !/<script[^>]+src=/i.test(page));
ok('no script on the page reaches the network (no fetch, XMLHttpRequest, WebSocket, EventSource or sendBeacon)', !/\bfetch\(|XMLHttpRequest|WebSocket|EventSource|sendBeacon/.test(KIT + PJS));
ok('speech is started only from click handlers: HiveVoice.speak appears exactly twice in the page script, each inside a click listener',
  (PJS.match(/HiveVoice\.speak\(/g) || []).length === 2 && PJS.split('HiveVoice.speak(').slice(0, -1).every((pre) => /addEventListener\('click', function \([^)]*\) \{(?:(?!addEventListener)[\s\S])*$/.test(pre)));
ok('nothing in the kit or page speaks from a timer or on load (no setTimeout / setInterval / requestAnimationFrame / onload)', !/setTimeout|setInterval|requestAnimationFrame|onload|DOMContentLoaded/.test(KIT + PJS));

/* ---- the voice kit, headless */
function kit({ voices = [{ name: 'Local', lang: 'en-US', localService: true }], store = {}, blocked = false } = {}) {
  const spoken = [];
  const synth = { getVoices: () => voices, speak: (u) => spoken.push(u), cancel: () => { synth.cancelled = (synth.cancelled || 0) + 1; } };
  const localStorage = { getItem: (k) => { if (blocked) throw new Error('blocked'); return k in store ? store[k] : null; }, setItem: (k, v) => { if (blocked) throw new Error('blocked'); store[k] = String(v); } };
  const ctx = { window: { speechSynthesis: synth }, SpeechSynthesisUtterance: function (t) { this.text = t; }, localStorage, String, Math, JSON };
  vm.createContext(ctx); vm.runInContext(KIT + ';this.HiveVoice = HiveVoice; this.HiveCore = HiveCore;', ctx);
  return { ...ctx, spoken, synth, store };
}
const ag = D.agents[0], txt = D.texts[ag.lines[0].t][0];
{ const k = kit(); const states = []; k.HiveVoice.init(D, { onstate: (s) => states.push(s) });
  ok('voice: nothing is spoken when the kit starts (no autoplay)', k.spoken.length === 0 && !k.HiveVoice.muted());
  const r = k.HiveVoice.speak([[ag, txt]]);
  ok(`voice: one Speak speaks the quoted line once, with the agent's AUTHORED pitch ${ag.pitch} and rate ${ag.rate}, full volume, an on-device English voice`,
    r && k.spoken.length === 1 && k.spoken[0].text === txt && k.spoken[0].pitch === ag.pitch && k.spoken[0].rate === ag.rate && k.spoken[0].volume === 1 && k.spoken[0].voice.localService === true && states.at(-1) === 'speaking');
  k.HiveVoice.setMuted(true);
  ok('voice: Mute silences (nothing more is spoken, the queue is cancelled) and is remembered on this device', !k.HiveVoice.speak([[ag, txt]]) && k.spoken.length === 1 && k.synth.cancelled >= 2 && k.store['tc.hive.muted'] === '1' && states.at(-1) === 'muted');
  const k2 = kit({ store: k.store }); k2.HiveVoice.init(D, {});
  ok('voice: a reload remembers Mute', k2.HiveVoice.muted() && !k2.HiveVoice.speak([[ag, txt]]) && k2.spoken.length === 0); }
{ const k = kit({ voices: [{ name: 'Net', lang: 'en-US', localService: false }, { name: 'Local fr', lang: 'fr-FR', localService: true }] }); const st = [];
  k.HiveVoice.init(D, { onstate: (s) => st.push(s) });
  ok('voice: a network voice is never used - with no on-device English voice nothing is spoken and the page says so', !k.HiveVoice.speak([[ag, txt]]) && k.spoken.length === 0 && st.at(-1) === 'novoice'); }
{ const k = kit({ voices: [] }); k.window.speechSynthesis = null; }
{ const k = kit(); const fast = D.agents.find((a) => a.k12 && a.rate > D.k12_rate_max) || { ...D.agents.find((a) => a.k12), rate: 1.08 };
  k.HiveVoice.init(D, { k12: true });
  ok('classroom: the voice starts muted and speaks nothing until the class turns it on', k.HiveVoice.muted() && !k.HiveVoice.speak([[fast, txt]]) && k.spoken.length === 0);
  k.HiveVoice.setMuted(false); k.HiveVoice.speak([[fast, txt]]);
  ok(`classroom: unmuted, speech is capped at volume ${D.k12_volume} and rate ${D.k12_rate_max}`, k.spoken.length === 1 && k.spoken[0].volume === D.k12_volume && k.spoken[0].rate <= D.k12_rate_max); }
{ const k = kit({ blocked: true }); k.HiveVoice.init(D, { k12: true });
  ok('classroom with blocked storage still starts muted (fails to silent)', k.HiveVoice.muted()); }

/* ---- the council, headless */
const { HiveCore } = kit();
const unesc = (s) => s.replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&');
const TRYM = [...page.matchAll(/class="hv-btn hv-try" data-ask-of="([^"]+)" data-ask="([^"]+)"/g)].map((m) => [m[1], unesc(m[2])]);
const TRY = TRYM.map((m) => m[1]);
ok(`the council's suggested questions (${TRY.length}) are each the registry ask of the agent and topic named beside it`, TRY.length >= 3 && TRYM.every(([ref, q]) => {
  const i = ref.lastIndexOf(':'), a = reg.agents.find((x) => x.id === ref.slice(0, i)); const l = a && a.lines.find((x) => x.id === ref.slice(i + 1));
  return l && l.ask_provenance === 'REGISTRY' && l.ask === q; }));
const runs = TRY.map((q) => [q, HiveCore.council(D, q, {})]);
ok(`every suggested question convenes 3 to 5 agents (${runs.map(([, r]) => r.members.length).join(', ')})`, runs.every(([, r]) => r.members.length >= 3 && r.members.length <= 5 && !r.short && !r.none), runs.map(([q, r]) => [q, r.members.length]));
ok('the council is deterministic: the same question gives the same members, lines and order', runs.every(([q, r]) => JSON.stringify(HiveCore.council(D, q, {})) === JSON.stringify(r)));
ok('every council answer is a quoted registry line of the agent that says it, and no line is said twice in one council',
  runs.every(([, r]) => r.members.every((m) => { const a = reg.agents[m.agent]; return a.lines[m.line].text === D.texts[D.agents[m.agent].lines[m.line].t][0]; })
    && new Set(r.members.map((m) => D.agents[m.agent].lines[m.line].t)).size === r.members.length));
ok('the council ranks by shared words, then by agent id, and every member shares a word with the question', runs.every(([q, r]) => {
  const qw = new Set(HiveCore.words(q));
  return r.members.every((m, i) => m.hits > 0 && HiveCore.words(D.texts[D.agents[m.agent].lines[m.line].t][0] + ' ' + (D.agents[m.agent].lines[m.line].ask || '')).some((w) => qw.has(w))
    && (i === 0 || r.members[i - 1].score > m.score || (r.members[i - 1].score === m.score && D.agents[r.members[i - 1].agent].id < D.agents[m.agent].id)));
}));
const crane = HiveCore.council(D, 'Who signals the crane during a lift?', {});
ok(`a crane question seats two of the crane lift crew, and no kind of agent takes more than two seats (${crane.members.map((m) => D.agents[m.agent].id.split(':').pop()).join(', ')})`,
  crane.members.length >= 3 && crane.members.filter((m) => D.agents[m.agent].id.startsWith('crew:crane-lift-crew:')).length === 2
  && ['advisor', 'crew-role', 'npc'].every((k) => crane.members.filter((m) => D.agents[m.agent].kind === k).length <= 2));
const nonsense = HiveCore.council(D, 'zxqv blorf quantum pineapple', {}), empty = HiveCore.council(D, '   ', {});
ok('a question no line shares words with gets no council and is refused by name, not guessed', nonsense.none && nonsense.members.length === 0 && empty.none);
const kc = TRY.map((q) => HiveCore.council(D, q, { k12: true }));
ok(`classroom council: every suggested question still seats at least three, and only play-safe agents and lines answer (${kc.map((r) => r.members.length).join(', ')})`,
  kc.every((r) => r.members.length >= 3 && r.members.every((m) => D.agents[m.agent].k12 === 1 && D.agents[m.agent].lines[m.line].safe === 1)));
const casualty = HiveCore.council(D, 'Why does the attendant never go in to help a casualty?', { k12: true });
ok('classroom council: a held line (the attendant\'s casualty line) is never offered', casualty.members.every((m) => !/casualt/i.test(D.texts[D.agents[m.agent].lines[m.line].t][0])));

/* ---- classroom mode on the page, and no internal references */
ok('classroom / K-12 mode (?classroom or ?class) hides non-play-safe cards, draws no held line and starts muted', PJS.includes("q.has('classroom') || q.has('class')")
  && PJS.includes(".hv-card[data-k12=\"0\"]") && PJS.includes('if (k12 && !ln.safe) return;') && PJS.includes('HiveVoice.init(D, { k12: k12'));
const visible = page.replace(/<script[\s\S]*?<\/script>/g, '');
ok('no internal reference on the page (no scratch path, no memory or console notes, no agent codename)',
  !/\/tmp\/|scratchpad|memory\/|\bconsole\b|\bHIVE\b|\b(ROBO|GROUND|COURSE|BUILD|EVAL)\b/.test(visible) && !/\/tmp\/|scratchpad|\bHIVE\b/.test(page));


/* ---- the worlds (wave 16 H2): the parish guides and the hall advisors / crew roles speak, on a click only */
{
  const par = readFileSync(join(HERE, 'trade_craft_parishes.html'), 'utf8'), bay = readFileSync(join(HERE, 'trade_craft_bay.html'), 'utf8');
  const c3d = readFileSync(join(HERE, 'trade_craft_3d.html'), 'utf8');
  const wblob = (pg, id) => { const s = pg.split(`<script type="application/json" id="${id}">`)[1]; return s ? JSON.parse(s.split('</script>')[0]) : null; };
  const wkit = (pg) => { const s = pg.split('<script id="hive-kit">')[1]; return s ? s.split('</script>')[0] : null; };
  const PV = wblob(par, 'hive-voice'), PN = wblob(par, 'parish-npcs'), CV = wblob(c3d, 'hive-voice');
  const regById = Object.fromEntries(reg.agents.map((a) => [a.id, a]));
  ok('worlds: the parish page and the 3D campus carry the same voice kit as this page, byte for byte', wkit(par) === KIT && wkit(c3d) === KIT);
  ok(`worlds: every guide placed on the parish map (${PN ? PN.npcs.length : 0}) has its hive voice there, and no other agent does`,
    !!PV && !!PN && PN.npcs.length > 0 && JSON.stringify(PV.agents.map((a) => a.id).sort()) === JSON.stringify(PN.npcs.map((n) => 'npc:' + n.id).sort()));
  ok('worlds: each parish voice is the registry voice (pitch, rate, play-safe flag) and holds exactly the registry\'s held lines', PV && PV.agents.every((a) => {
    const r = regById[a.id]; return r && a.pitch === r.voice.pitch && a.rate === r.voice.rate && a.k12 === (r.k12 ? 1 : 0)
      && JSON.stringify(a.held) === JSON.stringify(r.lines.filter((l) => !l.k12).map((l) => l.id)) && a.name === r.name; }));
  ok('worlds: the parish block carries no line text of its own - the dialogue line is the page\'s npcs.json quote', PV && !('texts' in PV) && PV.agents.every((a) => !('lines' in a)));
  ok('worlds: the parish guides\' Speak / Mute / state words are the hive.* catalogue values in all 8 locales', PV && Object.keys(PV.labels).length === 8
    && Object.entries(PV.labels).every(([l, L]) => L.speak === I[l].strings['hive.speak'] && L.mute === I[l].strings['hive.v.mute'] && L.novoice === I[l].strings['hive.v.novoice']));
  ok('worlds: the parish mount adds Speak and Mute to the NPC dialogue and speaks only from its click handler',
    /new MutationObserver\(decorate\)\.observe\(panel/.test(par) && (par.match(/HiveVoice\.speak\(/g) || []).length === (KIT.match(/HiveVoice\.speak\(/g) || []).length + 1
    && /panel\.addEventListener\('click', \(e\) => \{[^}]*const b = e\.target\.closest\('\[data-hive\]'\)/.test(par) && par.includes('window.__hiveWorld = hiveWorld;'));
  ok('worlds: the Bay page (NPC guides off) carries no hive block and no kit', !bay.includes('id="hive-voice"') && !bay.includes('id="hive-kit"'));
  const want3d = reg.agents.filter((a) => a.kind !== 'npc').map((a) => a.id);
  ok(`worlds: every hall advisor and crew role (${want3d.length}) has its hive voice and lines on the 3D campus`, !!CV
    && JSON.stringify(CV.agents.map((a) => a.id)) === JSON.stringify(want3d)
    && CV.agents.every((a) => a.lines.every((l) => CV.texts[l.t][0] === regById[a.id].lines.find((x) => x.id === l.id && x.kind === l.k).text)));
  ok('worlds: the 3D campus decorates the advisor panel at the end of openAdvisor() and speaks only from its click handler',
    c3d.includes('  questAdvisorEgg(aid, topicId);\n  if (hiveCampus) hiveCampus.decorate(aid, topicId);\n}') && c3d.includes('window.__hiveCampus = hiveCampus;')
    && (c3d.match(/HiveVoice\.speak\(/g) || []).length === (KIT.match(/HiveVoice\.speak\(/g) || []).length + 1
    && /document\.addEventListener\('click', \(e\) => \{\s*const b = e\.target\.closest\('#pbody \[data-hive\]'\)/.test(c3d));
  const wjs = (par.split('/* Omega Hive voice for the world guides')[1] || '').split('window.__hiveWorld')[0] + (c3d.split('/* Omega Hive voice for the hall advisors')[1] || '').split('window.__hiveCampus')[0];
  ok('worlds: neither mount speaks from a timer, on load or over the network', wjs.length > 1000 && !/setTimeout|setInterval|requestAnimationFrame|fetch\(|XMLHttpRequest|WebSocket|sendBeacon/.test(wjs));
  ok('worlds: both mounts honour classroom mode (?classroom / ?class): muted at start, play-safe figures and unheld lines only',
    (wjs.match(/qs\.has\('classroom'\) \|\| qs\.has\('class'\)/g) || []).length === 2 && (wjs.match(/HiveVoice\.init\(HV, \{ k12/g) || []).length === 2
    && (wjs.match(/k12 && \(!c(ur)?\.agent\.k12 \|\| !c(ur)?\.line\.safe\)/g) || []).length === 2);
}

/* ---- browser (opt-in) ---- */
const barg = process.argv.find((a) => a === '--browser' || a.startsWith('--browser=') || a === '--worlds' || a.startsWith('--worlds='));
const WORLDS = !!barg && barg.startsWith('--worlds');
if (barg) {
  let base = barg.includes('=') ? barg.split('=')[1] : null, srv = null;
  if (!base) {
    const http = await import('node:http'), { extname } = await import('node:path');
    const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.woff2': 'font/woff2' };
    srv = http.createServer((req, res) => { const p = join(ROOT, decodeURIComponent(req.url.split('?')[0]));
      if (!p.startsWith(ROOT) || !existsSync(p)) { res.writeHead(404); res.end(); return; }
      res.writeHead(200, { 'content-type': TYPES[extname(p)] || 'application/octet-stream' }); res.end(readFileSync(p)); });
    await new Promise((r) => srv.listen(0, '127.0.0.1', r));
    base = `http://127.0.0.1:${srv.address().port}/web`;
  }
  const { chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs');
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const errs = [];
  // a stub synthesiser with one on-device English voice that records every utterance - the page cannot tell it apart
  const STUB = () => { window.__spoken = []; const v = { name: 'Stub local', lang: 'en-US', localService: true, default: true };
    const s = { getVoices: () => [v], speak: (u) => window.__spoken.push({ text: u.text, pitch: u.pitch, rate: u.rate, volume: u.volume, local: u.voice && u.voice.localService }), cancel: () => {}, pending: false, speaking: false };
    Object.defineProperty(window, 'speechSynthesis', { value: s, configurable: true });
    window.SpeechSynthesisUtterance = function (t) { this.text = t; }; };
  try {
    if (WORLDS) {
      /* --worlds: the parish guides and a hall advisor speak on a click, never on their own (one 390 px viewport each) */
      const ctx = await b.newContext({ viewport: { width: 390, height: 844 } }); const pg = await ctx.newPage(); const reqs = [];
      await pg.addInitScript(STUB); pg.on('pageerror', (e) => errs.push('parishes: ' + e.message));
      pg.on('request', (r) => { if (!r.url().startsWith(base.split('/web')[0])) reqs.push(r.url()); });
      await pg.goto(base + '/trade_craft_parishes.html', { waitUntil: 'load' });
      await pg.waitForFunction(() => window.__parishes && window.__hiveWorld, null, { timeout: 45000 });
      const pw = await pg.evaluate(async () => { const tick = () => new Promise((r) => setTimeout(r, 30));
        const before = window.__spoken.length; const t = window.__parishes.talkIn('22005'); await tick();   /* the buttons join on the dialogue's next render */
        const panel = document.querySelector('.npc-panel'), sp = panel.querySelector('[data-hive="speak"]'), mu = panel.querySelector('[data-hive="mute"]');
        sp.click(); const one = window.__spoken.slice(); const cur = window.__hiveWorld.current();
        panel.querySelector('[data-npc="next"]').click(); await tick(); panel.querySelector('[data-hive="speak"]').click(); const two = window.__spoken.slice();
        panel.querySelector('[data-hive="mute"]').click(); panel.querySelector('[data-hive="speak"]').click(); const three = window.__spoken.length;
        panel.querySelector('[data-hive="mute"]').click();
        return { before, t, one, two, three, id: cur && cur.agent.id, mu: !!mu }; });
      const pa = reg.agents.find((a) => a.id === pw.id), pn = pa && pa.lines.filter((l) => l.kind === 'knowledge');
      ok(`browser worlds: a parish guide speaks only when Speak is pressed (${pw.before} before), its dialogue line at its own pitch ${pa && pa.voice.pitch} / rate ${pa && pa.voice.rate}`,
        pw.before === 0 && pw.mu && pw.one.length === 1 && pa && pw.one[0].text === pw.t.line && pw.one[0].text === pn[0].text && pw.one[0].pitch === pa.voice.pitch && pw.one[0].rate === pa.voice.rate && pw.one[0].local === true);
      ok('browser worlds: Next then Speak says the guide\'s next registry line; Mute silences it', pw.two.length === 2 && pw.two[1].text === pn[1].text && pw.three === 2);
      ok(`browser worlds: the parish map makes no request off its origin for the voice (${reqs.filter((u) => /speech|tts|voice/i.test(u)).length})`, reqs.filter((u) => /speech|tts|voice/i.test(u)).length === 0, reqs);
      await ctx.close();
      const c2 = await b.newContext({ viewport: { width: 390, height: 844 } }); const p2 = await c2.newPage();
      await p2.addInitScript(STUB); p2.on('pageerror', (e) => errs.push('campus: ' + e.message));
      await p2.goto(base + '/trade_craft_3d.html', { waitUntil: 'load' });
      await p2.waitForFunction(() => window.__tc3d && window.__hiveCampus, null, { timeout: 60000 });
      const cw = await p2.evaluate(() => { const before = window.__spoken.length; window.__tc3dDo('advisor', 'guide:start');
        const b = document.querySelector('#pbody [data-hive="speak"]'); b.click(); const one = window.__spoken.slice();
        window.__tc3dDo('advisor', 'safety-steward'); document.querySelector('#pbody [data-hive="speak"]').click(); return { before, one, two: window.__spoken.slice() }; });
      const g = reg.agents.find((a) => a.id === 'advisor:guide'), ss = reg.agents.find((a) => a.id === 'advisor:safety-steward');
      ok(`browser worlds: on the 3D campus the orientation guide speaks its 'start' line on Speak only (${cw.before} before), at pitch ${g.voice.pitch}`,
        cw.before === 0 && cw.one.length === 1 && cw.one[0].text === g.lines.find((l) => l.id === 'start').text && cw.one[0].pitch === g.voice.pitch);
      ok('browser worlds: with no say topic open, the safety steward speaks its greeting, in its own voice', cw.two.length === 2 && cw.two[1].text === ss.lines[0].text && cw.two[1].rate === ss.voice.rate);
      await c2.close();
    } else
    for (const vp of [{ n: '390', w: 390, h: 844 }, { n: '1440', w: 1440, h: 900 }]) {
      const ctx = await b.newContext({ viewport: { width: vp.w, height: vp.h } });
      const pg = await ctx.newPage(); const reqs = [];
      await pg.addInitScript(STUB);
      pg.on('pageerror', (e) => errs.push(vp.n + ': ' + e.message)); pg.on('request', (r) => { if (!r.url().startsWith(base.split('/web')[0])) reqs.push(r.url()); });
      await pg.goto(base + '/trade_craft_hive.html', { waitUntil: 'load' }); await pg.waitForFunction(() => window.__hivePage);
      await pg.waitForTimeout(800);
      const boot = await pg.evaluate(() => ({ spoken: window.__spoken.length, shown: window.__hivePage.shown(), mute: document.getElementById('hive-mute').getAttribute('aria-pressed') }));
      ok(`browser ${vp.n}: nothing speaks on load (${boot.spoken} utterances after 0.8 s), every card is shown (${boot.shown}), not muted`, boot.spoken === 0 && boot.shown === reg.agents.length && boot.mute === 'false');
      const one = await pg.evaluate(() => { document.querySelector('.hv-card .hv-vc .hv-say').click(); return window.__spoken.slice(); });
      const a0 = reg.agents[0];
      ok(`browser ${vp.n}: Speak on the first card speaks its greeting once, at pitch ${a0.voice.pitch} rate ${a0.voice.rate}, on the on-device voice`,
        one.length === 1 && one[0].text === a0.lines[0].text && one[0].pitch === a0.voice.pitch && one[0].rate === a0.voice.rate && one[0].local === true);
      const muted = await pg.evaluate(() => { document.getElementById('hive-mute').click(); document.querySelector('.hv-card .hv-vc .hv-say').click();
        const r = { n: window.__spoken.length, st: document.getElementById('hive-status').textContent, p: document.getElementById('hive-mute').getAttribute('aria-pressed') };
        document.getElementById('hive-mute').click(); return r; });
      ok(`browser ${vp.n}: Mute stops speech (still ${muted.n}) and the status says muted`, muted.n === 1 && muted.p === 'true' && muted.st.length > 0);
      const lines = await pg.evaluate(() => { const d = document.querySelector('details[data-lines-for="crew:confined-space-crew:attendant"]'); d.open = true;
        return new Promise((r) => setTimeout(() => r({ n: d.querySelectorAll('li').length, src: d.querySelector('li code').textContent }), 50)); });
      const att = reg.agents.find((a) => a.id === 'crew:confined-space-crew:attendant');
      ok(`browser ${vp.n}: opening a card draws every line it can say with its source (${lines.n})`, lines.n === att.lines.length && lines.src === att.lines[0].source);
      const cn = await pg.evaluate(() => { document.querySelector('.hv-try').click(); const n = document.querySelectorAll('#hive-council-out li').length;
        const before = window.__spoken.length; document.getElementById('hive-play').click(); return { n, said: window.__spoken.length - before, texts: [...document.querySelectorAll('#hive-council-out li p')].map((p) => p.textContent) }; });
      ok(`browser ${vp.n}: a suggested question convenes ${cn.n} agents and Play council speaks each in turn (${cn.said})`, cn.n >= 3 && cn.n <= 5 && cn.said === cn.n
        && cn.texts.every((t) => reg.agents.some((a) => a.lines.some((l) => l.text === t))));
      const filt = await pg.evaluate(() => { document.querySelector('[data-filter="crew-role"]').click(); const n = window.__hivePage.shown(); document.querySelector('[data-filter="all"]').click(); return n; });
      ok(`browser ${vp.n}: the Crew roles filter shows the ${filt} crew roles`, filt === reg.counts.crew_roles);
      ok(`browser ${vp.n}: no request leaves the page's origin (${reqs.length})`, reqs.filter((u) => !/fonts\.(googleapis|gstatic)\.com/.test(u)).length === 0, reqs);
      const ov = await pg.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      ok(`browser ${vp.n}: no horizontal scroll (${ov} px)`, ov <= 0);
      await ctx.close();
    }
    if (!WORLDS) {
    const ctx = await b.newContext({ viewport: { width: 390, height: 844 } }); const pg = await ctx.newPage();
    await pg.addInitScript(STUB); pg.on('pageerror', (e) => errs.push('classroom: ' + e.message));
    await pg.goto(base + '/trade_craft_hive.html?classroom=1', { waitUntil: 'load' }); await pg.waitForFunction(() => window.__hivePage);
    const cl = await pg.evaluate(() => { const n = window.__hivePage.shown(); const muted = document.getElementById('hive-mute').getAttribute('aria-pressed');
      document.querySelector('.hv-card:not([hidden]) .hv-vc .hv-say').click(); const a = window.__spoken.length;
      document.getElementById('hive-mute').click(); document.querySelector('.hv-card:not([hidden]) .hv-vc .hv-say').click();
      const crew = document.querySelectorAll('.hv-card[data-kind="crew-role"]:not([hidden])').length;
      return { n, muted, a, b: window.__spoken.slice(), crew, note: !document.getElementById('hive-k12-note').hidden }; });
    ok(`browser classroom: only the ${cl.n} play-safe agents show (no crew role), the voice starts muted, and once unmuted it speaks at volume ${cl.b[0] && cl.b[0].volume}`,
      cl.n === reg.counts.k12_agents && cl.crew === 0 && cl.muted === 'true' && cl.a === 0 && cl.b.length === 1 && cl.b[0].volume === reg.bounds.k12_volume && cl.note);
    await ctx.close();
    }
  } finally { await b.close(); if (srv) srv.close(); }
  ok('browser: zero page errors', errs.length === 0, errs);
}

console.log(`web/test_hive: ${pass} checks passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
