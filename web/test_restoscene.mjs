// web/test_restoscene.mjs - the habitat scenes, site crews and site panels at the Bay restoration sites
// (web/restoscene.py, mounted on web/trade_craft_bay.html by the RESTORE block of web/build_bayworld.py).
// Headless: the pure core (rsPlan) runs on synthetic ground; the page data is held to the registries verbatim.
// Prints "  ok " per check, FAIL at column 0, exits non-zero on failure.
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

let n = 0, bad = 0;
const ok = (m, c, d) => { if (c) { n++; console.log('  ok ', m); } else { bad++; console.log('FAIL', m, d === undefined ? '' : JSON.stringify(d).slice(0, 400)); } };
const ROOT = new URL('../', import.meta.url);
const rd = (p) => readFileSync(new URL(p, ROOT), 'utf8');
const html = rd('web/trade_craft_bay.html');
const kit = rd('web/restoscene.py');
const builder = rd('web/build_bayworld.py');
const REST = JSON.parse(rd('restoration/registry/restoration.json'));
const SC = JSON.parse(rd('restoration/registry/scenarios.json'));
const HIVE = JSON.parse(rd('hive/registry/hive.json'));
const COURSES = JSON.parse(rd('courses/registry/courses.json')).courses;
const LESSONS = rd('web/trade_craft_lessons.html');
const LOC = ['ar', 'de', 'en', 'es', 'fr', 'hi', 'pt', 'zh'];
const json = (id) => { const m = html.match(new RegExp(`<script type="application/json" id="${id}">([\\s\\S]*?)</script>`)); return m ? JSON.parse(m[1].replace(/<\\\//g, '</')) : null; };
const D = json('resto-site-data') || { sites: [], col: {} };
const VOICE = json('site-crew-voice') || { agents: [] };
const CAT = json('parishes-i18n') || {};
const byId = Object.fromEntries(REST.sites.map((s) => [s.id, s]));
const walk = D.sites.filter((s) => s.walkable);

// ---- the build ------------------------------------------------------------------------------------------------------
const chk = spawnSync('python3', ['web/build_bayworld.py', '--check'], { cwd: new URL('.', ROOT).pathname, encoding: 'utf8' });
ok('[build] the Bay page is current (python3 web/build_bayworld.py --check)', chk.status === 0, chk.stdout + chk.stderr);
ok('[build] the RESTORE block in web/build_bayworld.py is anchored once and wraps the world target finish()',
  (builder.match(/^# RESTORE BEGIN/gm) || []).length === 1 && (builder.match(/^# RESTORE END/gm) || []).length === 1
  && /_finish_w17 = T\.finish[\s\S]*T\.finish = _finish_restore\n# RESTORE END/.test(builder));
ok('[build] every page anchor the kit uses must occur exactly once (RestoSceneError otherwise)',
  /if page\.count\(a\) != 1:\s*\n\s*raise RestoSceneError/.test(kit) && /'frame': '  streetKitFrame\(over\);/.test(kit));

// ---- the core -------------------------------------------------------------------------------------------------------
const core = (html.match(/\/\* HABITAT-SCENE CORE BEGIN \*\/([\s\S]*?)\/\* HABITAT-SCENE CORE END \*\//) || [, ''])[1];
let api = null;
try { api = new Function(core + '\nreturn { rsPlan, rsWaterDir, RS_CAP, RS_TRIS, RS_LAND, RS_WET, RS_CLEAR };')(); } catch (e) { api = null; }
ok('[core] the HABITAT-SCENE core is on the page once, parses and defines rsPlan / rsWaterDir', !!api && (html.match(/HABITAT-SCENE CORE BEGIN/g) || []).length === 1);
const hash = (a, b, k) => { let h = (a * 374761393 + b * 668265263 + k * 2147483647) >>> 0; h = Math.imul(h ^ (h >>> 13), 1274126177) >>> 0; return ((h ^ (h >>> 16)) >>> 0) / 4294967296; };
// synthetic ground: water beyond a shore line 20 m from the point (normal 0.6, 0.8), a street strip 4 m wide 25 m east
const envFor = (s) => ({ col: D.col, hash, ground: () => 0,
  probe: (x, z) => { const v = (x - s.x) * 0.6 + (z - s.z) * 0.8; if (v > 20) return 'water'; if (Math.abs(x - s.x - 25) < 4) return 'road'; return 'land'; } });
const plans = api ? Object.fromEntries(walk.map((s) => [s.id, api.rsPlan({ ...s, crewN: s.crew.length }, envFor(s))])) : {};
const rule = [];
for (const s of walk) {
  const P = plans[s.id], env = envFor(s);
  if (!P) { rule.push(s.id + ': no plan'); continue; }
  for (const [f, L] of Object.entries(P.fam)) {
    if (L.length > api.RS_CAP[f]) rule.push(`${s.id} ${f} over cap`);
    for (const b of L) {
      const d = Math.hypot(b[0] - s.x, b[2] - s.z), p = env.probe(b[0], b[2]);
      if (p === 'road') rule.push(`${s.id} ${f} on a street`);
      if (d < api.RS_CLEAR - 0.05) rule.push(`${s.id} ${f} inside the landmark clearing`);
      if (p === 'land' ? d > api.RS_LAND + 0.05 : d > api.RS_WET + 0.05) rule.push(`${s.id} ${f} beyond its radius (${p}, ${d.toFixed(1)})`);
    }
  }
}
ok('[core] every kept instance obeys the radius rule (dry land <= RS_LAND, water <= RS_WET, never inside RS_CLEAR, never on a street) and every family stays within its cap',
  !!api && walk.length === 8 && rule.length === 0, rule.slice(0, 5));
ok('[core] the scene faces the nearest AUTHORED water (synthetic shore normal 0.6, 0.8 found within 5 degrees at every site)',
  !!api && walk.every((s) => plans[s.id] && plans[s.id].water.wx * 0.6 + plans[s.id].water.wz * 0.8 > Math.cos(5 * Math.PI / 180)));
// a second ground: a street disc over the first crew spot (13 m landward of the point) - the crew must step off it
const envRoad = (s) => { const e = envFor(s), cx = s.x - 13 * 0.6, cz = s.z - 13 * 0.8; return { ...e, probe: (x, z, w) => (Math.hypot(x - cx, z - cz) < 6 ? 'road' : e.probe(x, z, w)) }; };
ok('[core] the crew stand on dry land, one spot per crew member, at every walkable site (also with a street over the first spot)',
  !!api && walk.every((s) => { const P2 = api.rsPlan({ ...s, crewN: s.crew.length }, envRoad(s));
    return plans[s.id] && plans[s.id].crew.length === s.crew.length && plans[s.id].crew.every((c) => envFor(s).probe(c.x, c.z) === 'land')
      && P2.crew.length === s.crew.length && P2.crew.every((c) => envRoad(s).probe(c.x, c.z) === 'land'); }));
const again = api ? walk.every((s) => JSON.stringify(api.rsPlan({ ...s, crewN: s.crew.length }, envFor(s))) === JSON.stringify(plans[s.id])) : false;
ok('[core] the plan is deterministic (same site, same ground, same plan)', again);
const fam = (id, f) => (plans[id] ? plans[id].fam[f].length : 0);
const famBy = (id, f, cols) => (plans[id] ? plans[id].fam[f].filter((b) => cols.includes(b[7])).length : 0);
const SP = (core.match(/const RS_SP = \{([\s\S]*?)\};/) || [, ''])[1];
const spCols = (k) => ((SP.match(new RegExp(k + ': \\[\\[([^\\]]*)\\]')) || [, ''])[1].split(',').map((x) => Number(x.trim())));
ok('[habitat] tidal marsh sites carry pickleweed AND cordgrass bands and channel pads; mudflat pads where the recorded ground is marsh / mudflat / levee',
  walk.filter((s) => s.layers.some((l) => l.layer === 'tidal-marsh')).every((s) => famBy(s.id, 'tuft', spCols('pickle')) > 20 && famBy(s.id, 'tuft', spCols('cord')) > 20
    && plans[s.id].fam.pad.some((b) => b[7] === D.col.water) && plans[s.id].fam.pad.some((b) => b[7] !== D.col.water)));
ok('[habitat] the salt-pond site has levee berms walling its cells (>= 35 segments) and pond / mudflat pads; shoreline sites carry riprap or a rock sill and coir logs',
  fam('south-bay-salt-ponds', 'berm') >= 35 && fam('south-bay-salt-ponds', 'pad') >= 20
  && ['herons-head', 'candlestick-point', 'east-oakland-youth'].every((id) => fam(id, 'rock') >= 40 && famBy(id, 'box', [0x6b5232]) >= 6));
const maxTris = api ? Object.keys(api.RS_CAP).reduce((a, f) => a + api.RS_CAP[f] * api.RS_TRIS[f], 0) : Infinity;
ok(`[budget] the scene adds at most 5 draw calls and ${maxTris} triangles (Bay 06075 origin measured 17 calls / 76,991 tris against ceilings 45 / 122,020)`,
  !!api && Object.keys(api.RS_CAP).length === 5 && maxTris <= 16_000 && 76_991 + maxTris <= 122_020);
const frameHook = html.indexOf('  streetKitFrame(over);   // STREET-KIT\n  habitatSceneFrame(over);   // HABITAT-SCENE\n');
ok('[overview] the scene is driven from frame() right after the street kit and is hidden in the overview and beyond RS_VIEW',
  frameHook > 0 && /const n = RS\.on && !over \? rsNearest\(\) : null, show = !!\(n && n\.d < RS_VIEW\);/.test(html)
  && /RS_MESH\[f\]\.visible = show && /.test(html));
ok('[tex] pads and berms take the WORLD-TEX ground detail by device tier (base tier unchanged), through the page\'s own hook',
  /if \(\(f === 'pad' \|\| f === 'berm'\) && typeof worldTexHook === 'function'\) worldTexHook\(mat, 'ground'\);/.test(html));

// ---- the page data --------------------------------------------------------------------------------------------------
const lmSites = [...html.matchAll(/<li data-landmark="([0-9]+-lm[0-9]+)">/g)].length;
ok('[sites] the page carries one site row for every restoration-site landmark (9 placed + 1 offshore pin) and every walkable site with a recorded point',
  D.sites.length === 10 && new Set(D.sites.map((s) => s.id)).size === 10 && lmSites > 0
  && REST.sites.filter((s) => s.walkable && s.lat !== null).every((s) => walk.some((w) => w.id === s.id)));
const nw = D.sites.filter((s) => !s.walkable);
ok('[nonwalk] Hunters Point and Treasure Island stay non-walkable: no layers, no crew, no scene, walkable_reason verbatim from restoration.json',
  nw.length === 2 && ['hunters-point-shipyard', 'treasure-island-nsti'].every((id) => nw.some((s) => s.id === id))
  && nw.every((s) => !('layers' in s) && !('crew' in s) && s.walkable_reason === byId[s.id].walkable_reason && byId[s.id].walkable === false));
ok('[sites] every site row is at the RECORDED point of its own landmark and quotes its habitat and source verbatim',
  D.sites.every((s) => byId[s.id] && s.habitat === byId[s.id].habitat && s.source_url === byId[s.id].source_url && s.org === byId[s.id].org && s.name === byId[s.id].name));
const PD = json('parishes-data');
const lmAt = PD ? Object.fromEntries(PD.parishes.flatMap((p) => p.landmarks.map((l) => [l.id, l]))) : {};
ok('[sites] every site row stands exactly on its landmark in the page frame (x, z of parishes-data; z = -north)',
  !!PD && D.sites.every((s) => lmAt[s.lm] && lmAt[s.lm].x === s.x && lmAt[s.lm].z === s.z));
ok('[layers] every layer is chosen by a word of the site\'s OWN recorded text (the quote is a substring of the field it names)',
  walk.every((s) => s.layers.length > 0 && s.layers.every((l) => {
    const r = byId[s.id], t = l.field === 'habitat+ground' ? r.habitat + '|' + r.ground : r[l.field];
    return typeof t === 'string' && t.includes(l.quote) && typeof D.layer_title[l.layer] === 'string'; })));
const digits = [D.scene_label, D.crew_label, ...Object.values(D.layer_title)].filter((t) => /\d/.test(t));
ok('[numbers] the AUTHORED labels carry no number (no acreage, species count, length or funding is written by the kit)', digits.length === 0, digits);
ok('[label] the habitat scene says AUTHORED and not a survey; the crew label says SCRIPTED and no AI model',
  /AUTHORED/.test(D.scene_label) && /not a survey/.test(D.scene_label) && /SCRIPTED/.test(D.crew_label) && /no AI model/.test(D.crew_label));

// ---- verbatim quotes ------------------------------------------------------------------------------------------------
const at = (path) => {   // restoration/registry/scenarios.json#scenarios[3].steps[1].text -> value
  const [file, ptr] = path.split('#'); if (file !== 'restoration/registry/scenarios.json') return undefined;
  let v = SC; for (const m of ptr.matchAll(/([a-z_]+)(?:\[(\d+)\])?/g)) { v = v && v[m[1]]; if (m[2] !== undefined) v = v && v[Number(m[2])]; } return v;
};
const lines = walk.flatMap((s) => s.crew.flatMap((c) => c.lines));
ok(`[verbatim] every crew line (${lines.length}) equals the scenarios.json text at the path printed beside it`,
  lines.length > 50 && lines.every(([t, p]) => at(p) === t), lines.filter(([t, p]) => at(p) !== t).slice(0, 3));
ok('[verbatim] every scenario on a site row equals its registry steps, gates, title and label; every staged task its title, brief and launch',
  D.sites.every((s) => s.scenarios.every((x) => { const r = at(x.src); return r && r.title === x.title && r.label === x.label
    && JSON.stringify(r.steps.map((q) => q.text)) === JSON.stringify(x.steps) && JSON.stringify(r.safety_gates.map((q) => q.text)) === JSON.stringify(x.gates); })
    && s.tasks.every((t) => { const r = at(t.src); return r && r.title === t.title && r.brief === t.brief && r.launch.href === t.href; })
    && s.scenarios.length === SC.scenarios.filter((x) => x.site === s.id).length && s.tasks.length === SC.staged_tasks.filter((t) => t.place.id === s.id).length));
ok('[funding] the funding context and the rubric are the registry objects verbatim, with their source paths',
  JSON.stringify(D.funding) === JSON.stringify(SC.funding_context) && JSON.stringify(D.rubric) === JSON.stringify(SC.rubric)
  && D.funding_src === 'restoration/registry/scenarios.json#funding_context' && D.rubric_src === 'restoration/registry/scenarios.json#rubric');

// ---- the crew -------------------------------------------------------------------------------------------------------
const agent = Object.fromEntries(HIVE.agents.map((a) => [a.id, a]));
ok('[crew] every crew member is a roster agent (name and name source from hive.json) wearing its own AVATAR proxy colours',
  walk.every((s) => s.crew.length > 0 && s.crew.every((c) => { const a = agent[c.agent]; return a && a.name === c.name && a.name_source === c.name_src
    && ['torso', 'legs', 'head', 'hat', 'vest'].every((k) => parseInt(a.avatar.proxy[k].hex.slice(1), 16) === c.col[k]) && a.voice.pitch === c.voice.pitch && a.voice.rate === c.voice.rate; })));
ok('[crew] one crew member per crew role of the site\'s scenarios, each a world-guide mentor of that role\'s trade district, no agent twice on a site',
  walk.every((s) => { const roles = [...new Set(s.scenarios.flatMap((x) => x.crew.map((r) => r[0])))];
    return roles.length === s.crew.length && s.crew.every((c) => { const a = agent[c.agent]; return a.kind === 'npc' && a.role === 'mentor' && a.family === COURSES['trade.' + c.trade].district; })
      && new Set(s.crew.map((c) => c.agent)).size === s.crew.length; }));
ok('[voice] the crew voice block holds exactly the crew agents with their hive pitch and rate; the Bay page carries no NPC hive block',
  JSON.stringify(VOICE.agents.map((a) => a.id).sort()) === JSON.stringify([...new Set(walk.flatMap((s) => s.crew.map((c) => c.agent)))].sort())
  && VOICE.agents.every((a) => a.pitch === agent[a.id].voice.pitch && a.rate === agent[a.id].voice.rate)
  && !html.includes('id="hive-voice"') && (html.match(/id="site-crew-kit"/g) || []).length === 1);
const panelJs = (kit.match(/PANEL_JS = r"""([\s\S]*?)"""/) || [, ''])[1];
ok('[voice] speech happens only from the panel click handler (one HiveVoice.speak, inside panel.addEventListener(\'click\'), and a Mute that calls setMuted)',
  (panelJs.match(/HiveVoice\.speak\(/g) || []).length === 1 && /panel\.addEventListener\('click', \(e\) => \{[\s\S]*HiveVoice\.speak\(c\.lines\.map/.test(panelJs)
  && /HiveVoice\.setMuted\(!HiveVoice\.muted\(\)\)/.test(panelJs) && !/speechSynthesis/.test(panelJs));
ok('[panel] a staged-task link on a site with a scenario runner carries data-resto-run, so the runner opens in place on this page; a task with no launch link is shown as text',
  panelJs.includes('${s.runner ? ` data-resto-run="${esc(s.id)}"` : \'\'}>${esc(t.title)}</a>')
  && panelJs.includes('${t.href === null ? esc(t.title) :')
  && D.sites.every((s) => s.tasks.every((t) => t.href === 'web/trade_craft_bay.html#resto=' + s.id || (t.href === null && !s.runner))));
// the panel script itself, run against a stub document: every site's panel renders, quotes and links as recorded
const runPanel = () => {
  const el = () => { const e = { hidden: true, dataset: {}, innerHTML: '', textContent: '', attrs: {}, isConnected: true, focus() {}, scrollIntoView() {},
    setAttribute(k, v) { this.attrs[k] = v; }, getAttribute(k) { return this.attrs[k]; }, addEventListener() {}, querySelector(q) { return (this.kids[q] = this.kids[q] || el()); },
    querySelectorAll() { return []; }, kids: {} }; return e; };
  const panel = el(), byId = { 'resto-site': panel, 'resto-site-data': { textContent: JSON.stringify(D) }, 'parishes-i18n': { textContent: JSON.stringify(CAT) } };
  const win = {}, doc = { documentElement: { lang: 'en' }, getElementById: (id) => byId[id] || null, addEventListener() {}, querySelectorAll: () => [] };
  new Function('window', 'document', 'location', 'addEventListener', panelJs)(win, doc, { hash: '' }, () => {});
  return D.sites.map((s) => { win.__restoSite.open(s.id); return { s, h: panel.kids['[data-rs-host]'].innerHTML, open: !panel.hidden }; });
};
let rendered = [];
try { rendered = runPanel(); } catch (e) { rendered = [{ err: String(e) }]; }
ok('[panel] the site panel renders for all 10 sites: walkable ones with the AUTHORED scene label and their crew, non-walkable ones with walkable_reason and no crew; each quotes the funding headline and links its lessons',
  rendered.length === 10 && rendered.every(({ s, h, open }) => open && h.includes(s.name.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;'))
    && h.includes('data-rs-funding') && h.includes(SC.funding_context.headline) && s.courses.every((c) => c.lessons.every((l) => h.includes(`href="${l.href}"`)))
    && (s.walkable ? h.includes('data-rs-scene') && (h.match(/data-rs-crew="/g) || []).length === s.crew.length && !h.includes('data-rs-notwalk')
      : h.includes('data-rs-notwalk') && !h.includes('data-rs-crew="') && !h.includes('data-rs-scene'))), rendered.filter((r) => r.err).slice(0, 1));
ok('[play] the panel stores and fetches nothing', !/localStorage|sessionStorage|indexedDB|fetch\(|XMLHttpRequest/.test(panelJs));

// ---- links ----------------------------------------------------------------------------------------------------------
ok('[links] every site lists the course of each crew trade and that course\'s lessons, each with a lesson card on the lessons page',
  D.sites.every((s) => s.courses.length > 0 && s.courses.every((c) => COURSES[c.id] && c.id === 'trade.' + c.trade && c.title === COURSES[c.id].title
    && JSON.stringify(c.lessons.map((l) => l.id)) === JSON.stringify(COURSES[c.id].lessons) && c.lessons.every((l) => LESSONS.includes(`id="lesson-${l.id}"`)))));
const runs = [...html.matchAll(/<li data-landmark="([0-9]+-lm[0-9]+)"><button type="button" class="rk-open" data-resto-run="([a-z0-9-]+)">[^<]*<\/button> <button type="button" class="rk-open" data-site-open="([a-z0-9-]+)">/g)];
ok('[panel] each placed site landmark row carries its scenario runner and then one site-panel action for the same site; the offshore pin carries none',
  runs.length === 9 && runs.every((m) => m[2] === m[3]) && (html.match(/data-site-open="/g) || []).length === 9
  && !html.includes('data-site-open="treasure-island-nsti"'));
ok('[i18n] the panel words are existing catalogue keys present in all 8 locales on the page (no English copies added)',
  LOC.every((l) => CAT[l] && ['resto.crew', 'tasks.title', 'course.s.courses', 'course.s.lessons', 'hive.speak', 'hive.v.mute', 'course.sup.source'].every((k) => typeof CAT[l].strings[k] === 'string'))
  && LOC.filter((l) => l !== 'en').every((l) => CAT[l].strings['tasks.title'] !== CAT.en.strings['tasks.title']));
ok('[markers] page markers are neutral (HABITAT-SCENE, RESTORE-SITE, SITE-CREW); no team codename, kit file name or wave tag reaches the page',
  html.includes('HABITAT-SCENE BEGIN') && html.includes('RESTORE-SITE') && !/RESTORE·|RESTORE BEGIN|restoscene|wave 18|Deep Bay Restoration/.test(html));

if (bad) { console.log(`web/test_restoscene: ${bad} FAILED, ${n} passed`); process.exit(1); }
console.log(`web/test_restoscene: ${n} checks passed`);
