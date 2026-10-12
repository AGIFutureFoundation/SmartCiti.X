/* web/test_hive.mjs - the Omega Hive page (web/trade_craft_hive.html), checked against hive/registry/hive.json.
 * Browser-free by default. The voice kit and the council router are run headless here in a vm with a stub
 * speechSynthesis: no autoplay, on-device voices only, mute, classroom volume / rate caps, and a council that is the
 * same every time and quotes only registry text.
 * --browser (or --browser=<base url>) also drives the page in Chromium; --worlds drives the parish world and the 3D campus
 * instead (a guide and an advisor speak on a click). Without a url it serves the bundle itself on
 * 127.0.0.1 and stops only the server it started. Run it under flock $SP/chromium.lock. */
import { readFileSync, existsSync, readdirSync } from 'node:fs';
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
    && (c3d.match(/HiveVoice\.speak\(/g) || []).length === (KIT.match(/HiveVoice\.speak\(/g) || []).length + 2   // + the council point's one call (AVATAR w17; held by its own check)
    && /document\.addEventListener\('click', \(e\) => \{\s*const b = e\.target\.closest\('#pbody \[data-hive\]'\)/.test(c3d));
  const wjs = (par.split('/* Omega Hive voice for the world guides')[1] || '').split('window.__hiveWorld')[0] + (c3d.split('/* Omega Hive voice for the hall advisors')[1] || '').split('window.__hiveCampus')[0];
  ok('worlds: neither mount speaks from a timer, on load or over the network', wjs.length > 1000 && !/setTimeout|setInterval|requestAnimationFrame|fetch\(|XMLHttpRequest|WebSocket|sendBeacon/.test(wjs));
  ok('worlds: both mounts honour classroom mode (?classroom / ?class): muted at start, play-safe figures and unheld lines only',
    (wjs.match(/qs\.has\('classroom'\) \|\| qs\.has\('class'\)/g) || []).length === 2 && (wjs.match(/HiveVoice\.init\(HV, \{ k12/g) || []).length === 2
    && (wjs.match(/k12 && \(!c(ur)?\.agent\.k12 \|\| !c(ur)?\.line\.safe\)/g) || []).length === 2);
}

let avatarRule = null;   // AVATAR (wave 17): the trait rule, recomputed below, for the browser rows
/* AVATAR BEGIN (wave 17): agents embodied - each figure wears its own roster outfit, opens its dialogue with the line its
   AUTHORED traits pick, and makes one idle gesture. The rule is recomputed here from the AUTHORED table in web/hivekit.py. */
{
  const KITPY = readFileSync(join(HERE, 'hivekit.py'), 'utf8');
  const tbl = (KITPY.split('TRAIT_GESTURE_AUTHORED = {')[1] || '').split('\n}\n')[0];
  const CLS = {};
  let dup = 0;
  for (const m of tbl.matchAll(/'(wave|nod|point)': \[([^\]]*)\]/g)) for (const t of m[2].matchAll(/'([^']+)'/g)) { if (CLS[t[1]]) dup++; CLS[t[1]] = m[1]; }
  const G = ['wave', 'nod', 'point'];
  const OK_KINDS = { advisor: ['greeting', 'say'], 'crew-role': ['greeting', 'say'], npc: ['knowledge'] };
  const rule = (a) => { const c = a.personality.traits.map((t) => CLS[t]);
    const cands = a.lines.map((l, i) => [l, i]).filter(([l]) => OK_KINDS[a.kind].includes(l.kind)).map(([, i]) => i);
    const j = c.reduce((s, x) => s + G.indexOf(x), 0) % cands.length;
    let j12 = cands[j]; for (let k = 0; k < cands.length; k++) { const i = cands[(j + k) % cands.length]; if (a.lines[i].k12) { j12 = i; break; } }
    return { g: c[0], o: cands[j], o12: j12 }; };
  const traits = [...new Set(reg.agents.flatMap((a) => a.personality.traits))];
  ok(`avatar rule: every one of the roster's ${traits.length} AUTHORED traits has exactly one gesture class (wave / nod / point)`,
    traits.length > 0 && dup === 0 && traits.every((t) => G.includes(CLS[t])), traits.filter((t) => !CLS[t]));
  const R = Object.fromEntries(reg.agents.map((a) => [a.id, rule(a)]));
  avatarRule = rule;
  const badRow = D.agents.filter((r) => r.g !== R[r.id].g || r.o !== R[r.id].o || r.o12 !== R[r.id].o12).map((r) => r.id);
  ok(`avatar rule: each of the ${D.agents.length} agents' gesture is its first trait's class and its opener is candidates[sum of classes mod n] (Hive page data)`, badRow.length === 0, badRow.slice(0, 3));
  const badCardB = reg.agents.filter((a) => { const c = cardOf(a.id); return !c || !c.includes(`data-gesture="${R[a.id].g}"`) || !c.includes(`data-line="${R[a.id].o}"`); }).map((a) => a.id);
  ok('avatar rule: every Hive card names its gesture and its Speak button says the opener line', badCardB.length === 0, badCardB.slice(0, 3));
  ok('avatar rule: an opener is always a quoted line of a kind that can open a talk (greeting / say, a guide\'s knowledge line)',
    reg.agents.every((a, i) => a.lines[D.agents[i].o] && a.lines[D.agents[i].o12] && OK_KINDS[a.kind].includes(a.lines[D.agents[i].o].kind) && OK_KINDS[a.kind].includes(a.lines[D.agents[i].o12].kind)));
  ok('avatar rule: all three gestures are in use, and a wholly warm figure opens with its first line',
    G.every((g) => D.agents.some((r) => r.g === g)) && reg.agents.filter((a) => a.personality.traits.every((t) => CLS[t] === 'wave')).every((a) => D.agents.find((r) => r.id === a.id).o === a.lines.findIndex((l) => OK_KINDS[a.kind].includes(l.kind))));
  const c3 = readFileSync(join(HERE, 'trade_craft_3d.html'), 'utf8');
  const AVs = c3.split('<script type="application/json" id="agent-avatar">')[1];
  const AV = AVs ? JSON.parse(AVs.split('</script>')[0]) : null;
  const regBy = Object.fromEntries(reg.agents.map((a) => [a.id, a]));
  const want = reg.agents.filter((a) => a.kind !== 'npc');
  const badAv = AV ? AV.agents.filter((r) => { const a = regBy[r.id];
    return !a || JSON.stringify(r.cfg) !== JSON.stringify(a.avatar.cfg) || r.character !== a.avatar.character
      || Object.entries(a.avatar.proxy).some(([k, v]) => r.px[k] !== (v ? v.hex : null)) || r.g !== R[r.id].g
      || r.oid !== a.lines[R[r.id].o].id || r.oid12 !== a.lines[R[r.id].o12].id || r.key !== r.id.split(':').slice(1).join(':'); }).map((r) => r.id) : ['no block'];
  ok(`avatar 3D: every hall advisor and crew role (${AV ? AV.agents.length : 0}) carries its roster outfit (locker cfg, character, proxy colours), gesture and opener`,
    !!AV && AV.stamp === reg.source_stamp && JSON.stringify(AV.agents.map((r) => r.id)) === JSON.stringify(want.map((a) => a.id)) && badAv.length === 0, badAv.slice(0, 3));
  ok('avatar 3D: a figure is dressed from its roster cfg (keeping the hall\'s crew mark), built with that cfg as the rig\'s colour source, and the learner\'s look is handed back',
    c3.includes('  const own = agentOutfit(aid);\n  if (own) return { ...own.cfg, crew: crewSlug || own.cfg.crew };')
    && c3.includes('  const body = agentBody(advisorCfg(aid, crewSlug));\n  const proxy = agentProxy(aid) ?? proxyFigure();')
    && /function agentBody\(cfg\) \{\s*const keep = avatarCfg;\s*avatarCfg = cfg;\s*let g;\s*try \{ g = buildAvatarMesh\(cfg\); \} finally \{ avatarCfg = keep; \}/.test(c3));
  ok('avatar 3D: the far stand-in keeps proxyFigure()\'s three boxes, in the figure\'s own proxy colours',
    /function agentProxy\(aid\) \{[\s\S]*?M\(r\.px\.torso\)[\s\S]*?M\(r\.px\.legs\)[\s\S]*?M\(r\.px\.hat \|\| r\.px\.head\)[\s\S]*?g\.add\(torso, legs, head\);/.test(c3));
  ok('avatar 3D: with no topic asked, the panel opens with the opener (a quote; a say opener carries its source), and classroom mode takes the play-safe opener',
    c3.includes("  const answer = !t ? agentOpener(aid, a, esc)\n") && /function agentOpenId\(aid\) \{[^}]*agentAv\(\)\.k12 \? r\.oid12 : r\.oid/.test(c3)
    && /esc\(tp\.say\) \+ '<\/p><p class="src">written in '\s*\+ esc\(tp\.cites\)/.test(c3));
  ok('avatar 3D: the idle gesture runs only on a near, rigged body, honours reduced motion, and is a transform on the rig\'s own bones',
    c3.includes('    if (near) idleBreath(m.userData.body, t + m.position.x, dt);\n    if (near) agentGesture(m, t);\n')
    && /function agentGesture\(m, t\) \{[\s\S]*?if \(!r \|\| !b \|\| reduced\) return;[\s\S]*?rightUpperArm[\s\S]*?\.neck/.test(c3));
  ok('avatar 3D: the walkTo / walkAway hooks resolve crew-role and roster keys through agentHookKey (crew "<crew>:<role>[:<topic>]", "advisor:<id>", "crew:<crew>:<role>")',
    c3.includes("    const m = advisorMeshes.find((x) => x.userData.advisor === agentHookKey(arg));\n") && /function agentHookKey\(arg\) \{\s*const s = String\(arg\)\.replace\(\/\^\(advisor\|crew\):\/, ''\);\s*return advisorHookArgs\(s\)\[0\];/.test(c3));
  const avjs = (c3.split('/* AGENT-AVATAR: each hall advisor')[1] || '').split('window.__agentAvatars')[0];
  ok('avatar 3D: the figure layer speaks nothing, fetches nothing, and ships no team marker (neutral AGENT-AVATAR only)',
    avjs.length > 1000 && !/speak\(|speechSynthesis|fetch\(|XMLHttpRequest|WebSocket/.test(avjs) && !/AVATAR BEGIN|AVATAR END|AVATAR·|\bAVATAR w17/.test(c3));
  /* AVATAR (wave 17 B): the world guides in the parish world */
  const par = readFileSync(join(HERE, 'trade_craft_parishes.html'), 'utf8'), bay2 = readFileSync(join(HERE, 'trade_craft_bay.html'), 'utf8');
  const pj = (id) => { const x = par.split(`<script type="application/json" id="${id}">`)[1]; return x ? JSON.parse(x.split('</script>')[0]) : null; };
  const AG = pj('agent-avatar-guides'), PN2 = pj('parish-npcs');
  const badG = (AG && PN2) ? PN2.npcs.filter((n) => { const a = regBy['npc:' + n.id], r = AG.rows.find((x) => x.k === n.id), px = a && a.avatar.proxy;
    if (!a || !r) return true;
    const ru = R[a.id], kn = a.lines.filter((l) => l.kind === 'knowledge');
    return r.g !== ru.g || kn[r.o] !== a.lines[ru.o] || kn[r.o12] !== a.lines[ru.o12] || r.h !== (px.hair ? px.hair.hex : null) || r.hat !== (px.hat ? 1 : 0)
      || r.t !== px.torso.hex || r.s !== px.head.hex || r.b !== (a.avatar.cfg.tools === 'none' ? 0 : 1); }).map((n) => n.id) : ['no block'];
  ok(`avatar parish: every guide placed on the map (${PN2 ? PN2.npcs.length : 0}) carries its roster hair, sleeve, skin and belt, its gesture and its opener (a knowledge-line index)`,
    !!AG && AG.stamp === reg.source_stamp && AG.rows.length === PN2.npcs.length && badG.length === 0, badG.slice(0, 3));
  const badPx = PN2 ? PN2.npcs.filter((n) => Object.entries(n.appearance.proxy).some(([k, v]) => { const h = regBy['npc:' + n.id].avatar.proxy[k]; return (v ? v.hex : null) !== (h ? h.hex : null); })).map((n) => n.id) : ['none'];
  ok('avatar parish: the kit\'s body colours (npcs.json proxy hexes) are each guide\'s roster outfit colours', badPx.length === 0, badPx.slice(0, 3));
  ok('avatar parish: the guide dialogue opens on the rule\'s line - the kit takes openAt, the page passes agentGuideOpen (clamped to the guide\'s lines; classroom takes the play-safe opener)',
    par.includes('    talking = a; lineIdx = opt.openAt ? opt.openAt(a.npc) : 0; a.follow = null;') && par.includes('    labels: labelsFrom(tr),\n    openAt: agentGuideOpen,')
    && /function agentGuideOpen\(n\) \{[^}]*agentGuideRows\.k12 \? r\.o12 : r\.o;\s*return Math\.max\(0, Math\.min\(n\.knowledge\.length - 1, i\)\);/.test(par));
  ok('avatar parish: hair, sleeves and belt are three pooled InstancedMeshes (the 24 nearest guides within 90 m hold a slot) tagged as NPC parts (hidden in the overview with the kit\'s own), written only outside the overview',
    /m\.count = cap; m\.frustumCulled = false; m\.userData\.npcPart = name;/.test(par) && /mk\('hair', [^;]*CAP\), arms = mk\('arms', [^;]*2 \* CAP\),\s*belt = mk\('belt'[^;]*CAP\);/.test(par)
    && /const CAP = 24, DRAW = 90;/.test(par) && /if \(d > DRAW \|\| k >= CAP\) continue;/.test(par) && par.includes('    hair.count = k; belt.count = k; arms.count = 2 * k;')
    && par.includes('  if (agentGuides && !over) agentGuides.frame(dt, eye.x, eye.z);') && (par.match(/new THREE\.InstancedMesh\(geo, new THREE\.MeshStandardMaterial/g) || []).length === 1);
  const gjs = (par.split('/* AGENT-AVATAR: the world guides wear')[1] || '').split('window.__agentGuides')[0];
  ok('avatar parish: the gesture honours reduced motion and plays on greet / talk or within 40 m; the layer speaks nothing, fetches nothing and ships no team marker',
    gjs.length > 1000 && /const e = still \|\| u < 0 \? 0 :/.test(gjs) && /a\.state === 'greet' \|\| a\.state === 'talk'/.test(gjs) && /const DUR = 1\.6, EVERY = 9, NEAR = 40;/.test(gjs)
    && !/speak\(|speechSynthesis|fetch\(|XMLHttpRequest|WebSocket/.test(gjs) && !/AVATAR BEGIN|AVATAR END|AVATAR·|\bAVATAR w17/.test(par));
  ok('avatar parish: the Bay page (NPC guides off) carries no guide outfit block', !bay2.includes('id="agent-avatar-guides"') && !bay2.includes('agentGuides'));
  /* AVATAR (wave 17 C): the Hive council point on the flagship campus plaza, and the device-tier portraits */
  const CDs = c3.split('<script type="application/json" id="agent-council">')[1];
  const CD = CDs ? JSON.parse(CDs.split('</script>')[0]) : null;
  ok(`avatar council: the 3D campus carries the whole roster's council data - the same ${D.agents.length} agents and ${D.texts.length} quoted lines as the Hive page`,
    !!CD && CD.stamp === D.stamp && JSON.stringify(CD.agents) === JSON.stringify(D.agents) && JSON.stringify(CD.texts) === JSON.stringify(D.texts) && CD.flagship === 'treasure-island');
  ok(`avatar council: its ${CD ? CD.asks.length : 0} suggested asks are the Hive page's, in order (registry asks)`,
    !!CD && JSON.stringify(CD.asks) === JSON.stringify(TRYM));
  const locs = readdirSync(join(ROOT, 'i18n/locales')).filter((f) => f.endsWith('.json')).map((f) => JSON.parse(readFileSync(join(ROOT, 'i18n/locales', f), 'utf8')));
  ok('avatar council: its words are the hive.* catalogue values in all 8 locales (council, ask, convene, play, mute, the SCRIPTED / no-model / on-device-voice notes, the classroom note)',
    !!CD && Object.keys(CD.labels).length === 8 && locs.every((c) => CD.labels[c.locale] && CD.labels[c.locale].council === c.strings['hive.h.council']
      && CD.labels[c.locale].is2 === c.strings['hive.is.2'] && CD.labels[c.locale].k12 === c.strings['hive.k12.note'] && CD.labels[c.locale].mute === c.strings['hive.v.mute']));
  const same = CD ? TRY.every((q) => JSON.stringify(HiveCore.council(CD, q, {})) === JSON.stringify(HiveCore.council(D, q, {}))
    && JSON.stringify(HiveCore.council(CD, q, { k12: true })) === JSON.stringify(HiveCore.council(D, q, { k12: true }))) : false;
  ok('avatar council: run headless, the plaza council seats exactly the Hive page\'s council for every suggested ask, in full and in classroom mode', same);
  const cjs = (c3.split('/* AGENT-AVATAR council point')[1] || '').split('window.__agentCouncil')[0];
  ok('avatar council: the point stands only on the flagship plaza, is spawned with the campus advisors and picked first in the campus view',
    /if \(!C \|\| key !== C\.flagship \|\| !campusGroup\) return null;/.test(cjs) && c3.includes('  spawnCampusAdvisors();\n  agentCouncilPoint(key);')
    && c3.includes("  if (view === 'campus' && agentCouncilPick(ray)) return;") && /agentCouncilData\.hits = \[plinth, post\];/.test(cjs));
  ok('avatar council: it speaks only from its click handler (Play or a row\'s Speak), honours Mute and classroom mode, and uses no timer or network',
    cjs.length > 1000 && (cjs.match(/HiveVoice\.speak\(/g) || []).length === 1 && (cjs.match(/agentCouncilSay\(/g) || []).length === 3
    && /document\.addEventListener\('click', \(e\) => \{[\s\S]*?agentCouncilSay\(r\.members\.map\(pair\)\)[\s\S]*?agentCouncilSay\(\[pair\(m\)\]\)/.test(cjs)
    && /HiveCore\.council\(C, question, \{ k12: agentCouncilData\.k12 \}\)/.test(cjs) && /data-council="mute"/.test(cjs)
    && !/setTimeout|setInterval|requestAnimationFrame|fetch\(|XMLHttpRequest|WebSocket|sendBeacon/.test(cjs));
  const PJ = page.split('<script id="hive-portraits">')[1];
  const pjs = PJ ? PJ.split('</script>')[0] : '';
  ok('avatar portraits: the Hive page repaints each SVG face on a device-tier canvas (2x backing store; the base size under 4 GB, 4 cores or Save-Data; ?tex overrides), CSS size unchanged',
    page.indexOf('<script id="hive-portraits">') > 0 && page.indexOf('<script id="hive-portraits">') < page.indexOf('<script id="hive-page">')
    && /return \(mem < 4 \|\| cores < 4 \|\| save\) \? 1 : 2;/.test(pjs) && /if \(q === 'base'\) return 1;/.test(pjs)
    && /c\.width = Math\.round\(w \* S\); c\.height = Math\.round\(h \* S\);\s*c\.style\.width = w \+ 'px'; c\.style\.height = h \+ 'px';/.test(pjs)
    && faces.length === reg.agents.length && !/fetch\(|XMLHttpRequest|new Image|setTimeout/.test(pjs));
  ok('avatar portraits: a council row copies the canvas\'s pixels (a cloned canvas is blank)',
    page.includes('if (face) li.appendChild(window.HivePortrait ? HivePortrait.clone(face) : face.cloneNode(true));') && /g\.drawImage\(face, 0, 0\)/.test(pjs));
}
/* AVATAR END */

/* ---- browser (opt-in) ---- */
const barg = process.argv.find((a) => a === '--browser' || a.startsWith('--browser=') || a === '--worlds' || a.startsWith('--worlds='));
const WORLDS = !!barg && barg.startsWith('--worlds');
const regById0 = Object.fromEntries(reg.agents.map((a) => [a.id, a]));   // AVATAR (wave 17)
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
        /* AVATAR (wave 17): the dialogue opens on the guide's opener, which may be its last line - step to a neighbour */
        const step = panel.querySelector('[data-npc="next"]').disabled ? 'prev' : 'next';
        panel.querySelector('[data-npc="' + step + '"]').click(); await tick(); panel.querySelector('[data-hive="speak"]').click(); const two = window.__spoken.slice();
        panel.querySelector('[data-hive="mute"]').click(); panel.querySelector('[data-hive="speak"]').click(); const three = window.__spoken.length;
        panel.querySelector('[data-hive="mute"]').click();
        return { before, t, one, two, three, id: cur && cur.agent.id, mu: !!mu, step }; });
      const pa = reg.agents.find((a) => a.id === pw.id), pn = pa && pa.lines.filter((l) => l.kind === 'knowledge');
      const po = pa ? pn.indexOf(pa.lines[avatarRule(pa).o]) : -1, pn2 = po + (pw.step === 'next' ? 1 : -1);   // AVATAR (wave 17)
      ok(`browser worlds: a parish guide speaks only when Speak is pressed (${pw.before} before), its dialogue line at its own pitch ${pa && pa.voice.pitch} / rate ${pa && pa.voice.rate}`,
        pw.before === 0 && pw.mu && pw.one.length === 1 && pa && pw.one[0].text === pw.t.line && po >= 0 && pw.one[0].text === pn[po].text && pw.one[0].pitch === pa.voice.pitch && pw.one[0].rate === pa.voice.rate && pw.one[0].local === true);
      ok('browser worlds: Next (Prev at the last line) then Speak says the guide\'s neighbouring registry line; Mute silences it', pw.two.length === 2 && pw.two[1].text === pn[pn2].text && pw.three === 2);
      ok(`browser worlds: the parish map makes no request off its origin for the voice (${reqs.filter((u) => /speech|tts|voice/i.test(u)).length})`, reqs.filter((u) => /speech|tts|voice/i.test(u)).length === 0, reqs);
      /* AVATAR BEGIN (wave 17 B): the parish guides wear their roster outfit and gesture as they start to talk */
      {
        const gv = await pg.evaluate(async () => { const G = window.__agentGuides, wait = (ms) => new Promise((r) => setTimeout(r, ms));
          if (!G) return null;
          const placed = JSON.parse(document.getElementById('parish-npcs').textContent).npcs.length;
          const t = window.__parishes.talkIn('22071'); await wait(700);
          const kc = window.__parishes.kitCost(1);   // one render per kit group: the guides' share of this walk frame
          return { placed, rows: G.rows, parts: G.parts.map((m) => ({ inst: !!m.isInstancedMesh, part: m.userData.npcPart, vis: m.visible })), id: t.id, line: t.line,
            colour: G.colourOf(t.id), played: G.played(), last: G.last()[t.id] || null, writes: G.writes(), slotted: G.slotted(), cap: G.cap,
            npc: (kc.groups || {}).npc || null, all: kc.all }; });
        const ga = gv && reg.agents.find((a) => a.id === 'npc:' + gv.id), gr = ga && avatarRule(ga), gpx = ga && ga.avatar.proxy;
        ok(`browser worlds: every placed guide (${gv && gv.rows}) wears its roster outfit - three instanced parts (hair, sleeves, belt) drawn in the walk view, the talking guide's sleeves ${gv && gv.colour && gv.colour.arm}, hair ${gv && gv.colour && gv.colour.hair}`,
          !!gv && gv.rows === gv.placed && gv.parts.length === 3 && gv.parts.every((p) => p.inst && p.vis) && JSON.stringify(gv.parts.map((p) => p.part)) === '["hair","arms","belt"]'
          && gv.colour.arm === gpx.torso.hex && gv.colour.hair === (gpx.hair ? gpx.hair.hex : gpx.head.hex) && gv.colour.belt === '#26262a', gv);
        ok(`browser worlds: the guides' parts are a pool - ${gv && gv.slotted} of ${gv && gv.rows} guides hold a slot (cap ${gv && gv.cap}); the guide kit draws ${gv && gv.npc && gv.npc.calls} calls / ${gv && gv.npc && gv.npc.tris} triangles (kit 5 / 10,080 + at most 24 x 4 boxes) of the walk frame's ${gv && gv.all && gv.all.calls} / ${gv && gv.all && gv.all.tris}`,
          !!gv && gv.slotted >= 1 && gv.slotted <= gv.cap && gv.cap === 24 && !!gv.npc && gv.npc.calls <= 8 && gv.npc.tris <= 10080 + 24 * 4 * 12, gv && { npc: gv.npc, slotted: gv.slotted });
        ok(`browser worlds: the Orleans guide's dialogue opens on its rule line (${gr && ga.lines[gr.o].id}) and it makes its '${gr && gr.g}' gesture as it starts to talk (envelope ${gv && gv.last && gv.last.env})`,
          !!gv && !!gr && gv.line === ga.lines[gr.o].text && gv.played >= 1 && !!gv.last && gv.last.g === gr.g && gv.last.env > 0, gv && { line: gv.line, last: gv.last, played: gv.played });
      }
      /* AVATAR END */
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
      /* AVATAR BEGIN (wave 17): the hall figures wear their roster outfits, open on the rule's line and gesture */
      {
        const av = await p2.evaluate(async () => { const A = window.__agentAvatars, wait = (ms) => new Promise((r) => setTimeout(r, ms));
          const learner = JSON.stringify(A.learnerCfg());
          window.__tc3dDo('view', 'hall:' + (new URLSearchParams(location.search).get('hall') || 'ironworkers')); await wait(400);
          const here = A.here(), figs = here.map((k) => ({ k, f: A.figure(k), o: A.outfit(k) }));
          window.__tc3dDo('advisor', 'layout-hand'); const open = document.querySelector('#pbody [data-agent-open]');
          const openId = open && open.dataset.agentOpen, openText = open && open.textContent;
          const before = window.__spoken.length; const sp = document.querySelector('#pbody [data-hive="speak"]'); if (sp) sp.click();
          const said = window.__spoken.slice(before);
          const m = window.__tc3dScene().getObjectByProperty ? null : null;
          let lh = null; window.__tc3dScene().traverse((o) => { if (o.userData && o.userData.advisor === 'layout-hand') lh = o; });
          let gest = null;
          if (lh) { const p = lh.getWorldPosition(lh.position.clone());
            window.__tc3dDo('cam', `${p.x + 1.6},${p.y + 1.6},${p.z + 1.6}|${p.x},${p.y + 1.2},${p.z}`);
            window.__tc3dDo('advisor', 'layout-hand'); const t0 = A.t0('layout-hand');
            /* the first frame after the dialogue opened (a software-rendered hall frame can take over a second) */
            for (let i = 0; i < 40; i++) { await wait(100); const l = A.last()['layout-hand']; if (l && l.t > t0) { gest = l; break; } } }
          window.__tc3dDo('view', 'sim:crane-lift'); await wait(400);
          const crew = A.figure('crew:crane-lift-crew:lift-director:plan'), crewO = A.outfit('crane-lift-crew:lift-director');
          return { learner, after: JSON.stringify(A.learnerCfg()), figs, openId, openText, said, gest, crew, crewO, built: A.built() }; });
        const bad = av.figs.filter(({ f, o }) => !f || !o || JSON.stringify({ ...f.cfg, crew: 0 }) !== JSON.stringify({ ...o.cfg, crew: 0 })
          || !f.body.includes(o.px.head) || JSON.stringify(f.proxy) !== JSON.stringify([o.px.torso, o.px.legs, o.px.hat || o.px.head])).map((x) => x.k);
        ok(`browser worlds: each of the ${av.figs.length} figures standing in the hall wears its roster outfit (cfg, skin colour on the rig, stand-in in its proxy colours), and the learner's own look is untouched`,
          av.figs.length >= 3 && bad.length === 0 && av.learner === av.after, { bad, n: av.figs.length });
        const lh = reg.agents.find((a) => a.id === 'advisor:layout-hand'), lhR = av.figs.find((x) => x.k === 'layout-hand');
        const lhLine = lh.lines.find((l) => l.id === (lhR && lhR.o.oid));
        ok(`browser worlds: the layout hand's dialogue opens on its rule line '${lhR && lhR.o.oid}' (a registry quote) and Speak says that line`,
          !!lhLine && av.openId === lhR.o.oid && av.openText === lhLine.text && av.said.length === 1 && av.said[0].text === lhLine.text, { openId: av.openId, said: av.said });
        ok(`browser worlds: the layout hand makes its '${lhR && lhR.o.g}' gesture as its dialogue opens (envelope ${av.gest && av.gest.env})`,
          !!av.gest && av.gest.g === (lhR && lhR.o.g) && av.gest.env > 0, av.gest);
        ok('browser worlds: a crew role in its yard is found by a roster key with a topic ("crew:<crew>:<role>:<topic>") and wears its own outfit, crew mark included',
          !!av.crew && av.crew.key === 'crane-lift-crew:lift-director' && JSON.stringify(av.crew.cfg) === JSON.stringify(av.crewO.cfg), av.crew);
      }
      /* AVATAR END */
      /* AVATAR BEGIN (wave 17 C): the Hive council point on the flagship plaza - picked by a click, the Hive page's council, voice on a click */
      {
        const cq = TRY[0], want = HiveCore.council(D, cq, {}).members.map((m) => [D.agents[m.agent].id, D.texts[D.agents[m.agent].lines[m.line].t][0]]);
        const cv0 = await p2.evaluate(async () => { const wait = (ms) => new Promise((r) => setTimeout(r, ms)), C = window.__agentCouncil;
          window.__tc3dDo('view', 'campus:treasure-island'); await wait(500);
          const point = C.point();
          document.body.classList.remove('open');   // the advisor panel opened above would sit over the view
          window.__tc3dDo('cam', '-3,2.2,14|-9,1.3,8'); await wait(250);
          /* the closed panel slides out on a CSS transition; wait (up to 2.5 s) until it has left the middle of the view */
          let at = document.elementFromPoint(innerWidth / 2, innerHeight / 2);
          for (let i = 0; i < 25 && (!at || at.tagName !== 'CANVAS'); i++) { await wait(100); at = document.elementFromPoint(innerWidth / 2, innerHeight / 2); }
          return { point, onCanvas: !!at && at.tagName === 'CANVAS' }; });
        /* a real click at the middle of the view, where the camera is aimed at the council post */
        const vp = p2.viewportSize(); await p2.mouse.click(Math.round(vp.width / 2), Math.round(vp.height / 2)); await p2.waitForTimeout(150);
        const cv = { ...cv0, ...await p2.evaluate(async () => {
          const h2 = (document.querySelector('#pbody h2') || {}).textContent || '';
          const before = window.__spoken.length;
          const ask = document.querySelector('#pbody [data-council-ask]'); if (ask) ask.click();
          const rows = [...document.querySelectorAll('#agentCouncilOut li')].map((li) => [li.dataset.agent, li.querySelector('p').textContent]);
          const mid = window.__spoken.length, play = document.querySelector('#pbody [data-council="play"]');
          if (play) play.click(); const played = window.__spoken.length - mid;
          const mu = document.querySelector('#pbody [data-council="mute"]'); if (mu) mu.click(); if (play) play.click();
          const mutedSaid = window.__spoken.length - mid - played; if (mu) mu.click();
          const one = document.querySelector('#agentCouncilOut [data-council-speak]'); const b2 = window.__spoken.length; if (one) one.click();
          return { h2, asked: mid - before, rows, played, mutedSaid, one: window.__spoken.length - b2, honest: !!document.querySelector('#pbody [data-council-honest]') }; }) };
        ok(`browser worlds: a click on the council point on the flagship plaza opens the Hive council (${cv.h2.slice(0, 20)}), with its SCRIPTED / no-model / device-voice note`,
          cv.point === 2 && cv.onCanvas && cv.h2.startsWith('\u2B21') && cv.honest, cv);
        ok(`browser worlds: a suggested ask seats the Hive page's own council there (${cv.rows.length} agents, same lines, same order) and nothing speaks until Play (${cv.asked})`,
          cv.asked === 0 && JSON.stringify(cv.rows) === JSON.stringify(want), { got: cv.rows, want });
        ok(`browser worlds: Play speaks each member once (${cv.played}), Mute silences it (${cv.mutedSaid}), a row's Speak says that one line (${cv.one})`,
          cv.played === want.length && cv.mutedSaid === 0 && cv.one === 1);
        await c2.close();
        const c3c = await b.newContext({ viewport: { width: 390, height: 844 } }); const p3 = await c3c.newPage();
        await p3.addInitScript(STUB); p3.on('pageerror', (e) => errs.push('campus classroom: ' + e.message));
        await p3.goto(base + '/trade_craft_3d.html?classroom=1', { waitUntil: 'load' });
        await p3.waitForFunction(() => window.__tc3d && window.__agentCouncil, null, { timeout: 60000 });
        const kc = await p3.evaluate((q) => { window.__agentCouncil.open(q);
          const muted = (document.querySelector('#pbody [data-council="mute"]') || {}).getAttribute?.('aria-pressed');
          document.querySelector('#pbody [data-council="play"]').click();
          return { muted, said: window.__spoken.length, k12: window.__agentCouncil.k12(), note: !!document.querySelector('#pbody [data-council-k12]'),
            rows: [...document.querySelectorAll('#agentCouncilOut li')].map((li) => li.dataset.agent) }; }, cq);
        const wantK = HiveCore.council(D, cq, { k12: true }).members.map((m) => D.agents[m.agent].id);
        ok(`browser worlds: in classroom mode the plaza council seats only play-safe agents (${kc.rows.length}, the Hive page's classroom council) and starts muted`,
          kc.k12 && kc.note && kc.muted === 'true' && kc.said === 0 && JSON.stringify(kc.rows) === JSON.stringify(wantK) && kc.rows.every((id) => regById0[id] && regById0[id].k12), kc);
        await c3c.close();
      }
      /* AVATAR END */
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
    /* AVATAR BEGIN (wave 17 C): the roster portraits on a device-tier canvas */
    {
      const shot = async (q) => { const cx = await b.newContext({ viewport: { width: 390, height: 844 } }); const pp = await cx.newPage();
        await pp.addInitScript(STUB); pp.on('pageerror', (e) => errs.push('portraits: ' + e.message));
        await pp.goto(base + '/trade_craft_hive.html' + q, { waitUntil: 'load' }); await pp.waitForFunction(() => window.__hivePage && window.__hivePortraits);
        const r = await pp.evaluate(() => { const cs = [...document.querySelectorAll('.hv-card canvas.hv-face')];
          const px = (c, x, y) => { const d = c.getContext('2d').getImageData(x, y, 1, 1).data; return '#' + [0, 1, 2].map((i) => d[i].toString(16).padStart(2, '0')).join(''); };
          const c0 = cs[0]; const s = window.__hivePortraits.scale;
          document.querySelector('.hv-try').click();
          const row = document.querySelector('#hive-council-out li canvas.hv-face');
          return { n: cs.length, svg: document.querySelectorAll('.hv-card svg.hv-face').length, scale: s, w: c0 && c0.width, h: c0 && c0.height, cssW: c0 && c0.getBoundingClientRect().width,
            head: c0 && px(c0, Math.round(32 * s), Math.round(24 * s)), torso: c0 && px(c0, Math.round(32 * s), Math.round(40 * s)),
            row: row ? px(row, Math.round(32 * s), Math.round(24 * s)) : null, rowW: row && row.width }; });
        await cx.close(); return r; };
      const hi = await shot(''), lo = await shot('?tex=base');
      const a0 = reg.agents[0], hp = a0.avatar.proxy;
      ok(`browser portraits: every card's face (${hi.n}) is a canvas at ${hi.scale}x (${hi.w}x${hi.h} px backing, ${hi.cssW} px wide on the page), painted in the roster's colours`,
        hi.n === reg.agents.length && hi.svg === 0 && hi.scale === 2 && hi.w === 128 && hi.h === 144 && Math.round(hi.cssW) === 64
        && hi.head === (hp.hat ? hp.head.hex : hp.head.hex) && hi.torso === hp.torso.hex, hi);
      ok(`browser portraits: on a low-tier device (?tex=base) the canvas keeps the base size (${lo.w}x${lo.h}), and a council row carries a painted copy, not a blank canvas`,
        lo.n === reg.agents.length && lo.scale === 1 && lo.w === 64 && lo.h === 72 && Math.round(lo.cssW) === 64 && !!hi.row && hi.row !== '#000000' && hi.rowW === hi.w, { lo, row: hi.row });
    }
    /* AVATAR END */
    }
  } finally { await b.close(); if (srv) srv.close(); }
  ok('browser: zero page errors', errs.length === 0, errs);
}

console.log(`web/test_hive: ${pass} checks passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
